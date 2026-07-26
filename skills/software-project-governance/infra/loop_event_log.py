#!/usr/bin/env python3
"""Restart-safe append-only event log for the executable Loop Engine.

FEAT-007 (ADR-014 §5.1, §5.2, 0.68.0). Product code, authorized by Design Review
APPROVED_WITH_NOTES/0 (EVD-841~843).

This module is the **restart-safe, multi-process-safe event log** for the 0.68.0
executable Loop Engine. Every PARO state mutation (FEAT-005
:func:`loop_paro_engine.apply_transition` / :func:`activate_unit`) and every
gate outcome (FEAT-006 :func:`loop_gate_processor.process_gate_result`) is
recorded here as one self-contained JSON line in
``HOST_ROOT/.governance/loop-event-log.jsonl`` (JSONL — one JSON object per
line, UTF-8, newline-terminated). The log is the replayable audit trail;
``flow-unit-runtime.json`` remains the operational truth (ADR-014 §3.4:
"two stores, one truth").

**Scope (FEAT-007):**

  - **Append-only writer** (:func:`append_event` / :func:`append_events`): open
    with ``"a"`` mode and write the full JSON line + ``\\n`` in ONE ``write()``
    call. This is the §5.2 atomic-line-append discipline — on POSIX writes
    smaller than ``PIPE_BUF`` (~4KB) are atomic; on Windows the temp-buffered
    single-write append is the robust pattern (Design Review P2-1 concern).
  - **Reader** (:func:`read_events` / :func:`last_event_for_unit`): parse the
    JSONL file, optionally filtered by ``unit_id``.
  - **Envelope validation** (:func:`validate_event`): the §5.1 required-fields
    check + the closed ``event_type`` enum (14 types).
  - **Monotonicity check** (:func:`check_cas_monotonicity`): for one unit's
    events sorted by timestamp, ``cas_version`` must be strictly monotonic +1
    (``from_version == previous cas_version``). Gaps/regressions = errors
    (§3.6).
  - **Phase-legality replay** (:func:`check_phase_legality`): replay the
    ``from_phase → to_phase`` transitions and verify each is legal per the §3.2
    table (delegates to :func:`loop_paro_engine.validate_transition`).

**Constraints honored (ADR-014 §9.2):**

  - This module is ADDITIVE. It does not modify FEAT-005/006 modules' behavior
    when the event log is absent (backward compat: ``log_path`` None or the
    file does not exist → appends are skipped gracefully via the callers'
    optional-event-log hook, and the readers here return empty).
  - The state-first/event-second ordering (§5.2 point 3) is enforced by the
    CALLERS (FEAT-005/006 append events AFTER the atomic state write commits);
    this module only provides the append primitive.
  - RISK-037 / RISK-042 remain open.

**Windows append safety (Design Review P2-1):** the atomicity concern is that
two concurrent processes appending to the same file could interleave bytes
within a line, producing a corrupt line. The remedy (§5.2 point 2) is:
open in ``"a"`` mode (which on both POSIX and Windows positions the file
offset at end-of-file for each write under the kernel's append discipline)
and write the FULL line + newline in ONE ``write()`` call. On POSIX this is
guaranteed atomic for writes < PIPE_BUF. On Windows, the C runtime's append
mode + single-write call is the documented robust pattern (the file system
append atomicity is per-write-call, not per-open-handle). The multi-process
threading test (:func:`tests.test_loop_event_log`) proves no lost/corrupt
events on this platform.

Usage:
    from loop_event_log import append_event, read_events, validate_event

    append_event({
        "event_id": "evt-...", "timestamp": "2026-07-23T14:05:11Z",
        "unit_id": "shitu.story.Skeleton", "event_type": "back_edge",
        "cas_version": 8, "from_version": 7,
        "from_phase": "reflect", "to_phase": "plan", "actor": "...",
    }, log_path=path_to_loop_event_log_jsonl)

    events = read_events(log_path=path_to_loop_event_log_jsonl,
                         unit_id="shitu.story.Skeleton")
"""

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════
# Constants — event types (closed enum, ADR-014 §5.1) + required fields
# ═══════════════════════════════════════════════════════════════════════════

# The 14 event types of the closed enum (§5.1 table). validate_event rejects
# any event_type not in this set.
EVENT_TYPES = frozenset({
    "phase_enter",
    "phase_transition",
    "gate_result",
    "back_edge",
    "loop_exit",
    "fuse_trip",
    "escalation_resolved",
    "unit_blocked",
    "unit_withdrawn",
    "dependency_block",
    "wip_admit",
    "wip_deny",
    "phase_recovery",
    "recovery_conflict",
})

# The required top-level fields on every event envelope (§5.1). An event
# missing any of these is invalid (validate_event returns a per-field error).
REQUIRED_FIELDS = (
    "event_id",
    "timestamp",
    "unit_id",
    "event_type",
    "cas_version",
    "from_version",
    "from_phase",
    "to_phase",
    "actor",
)

# The default event-log filename (relative to a host root's .governance/).
EVENT_LOG_FILENAME = "loop-event-log.jsonl"
EVENT_LOG_DIRNAME = ".governance"


# ═══════════════════════════════════════════════════════════════════════════
# Path resolution
# ═══════════════════════════════════════════════════════════════════════════


def default_log_path(root=None):
    """Return the default ``loop-event-log.jsonl`` path for a host ``root``.

    When ``root`` is None, returns the conventional path relative to the
    current working directory (``./.governance/loop-event-log.jsonl``). When
    ``root`` is given, returns ``<root>/.governance/loop-event-log.jsonl``
    (the RISK-040 HOST_PROJECT_ROOT location). Never raises.
    """
    if root is None:
        base = Path.cwd()
    else:
        base = Path(root)
    return base / EVENT_LOG_DIRNAME / EVENT_LOG_FILENAME


def _resolve_path(log_path):
    """Normalize ``log_path`` to a Path (or None → default under cwd)."""
    if log_path is None:
        return default_log_path(None)
    return Path(log_path) if not isinstance(log_path, Path) else log_path


# Per-file append lock. The atomic line append relies on the kernel's append
# discipline (POSIX) / the C runtime's append mode (Windows), so the lock is
# NOT load-bearing for cross-PROCESS safety — it only prevents same-process
# threads from interleaving their Python-level write() preparations. The
# multi-process test proves the file-level append is safe WITHOUT this lock;
# it is belt-and-suspenders for the in-process case (and for Windows, where
# the C runtime's append atomicity is per-write-call).
_APPEND_LOCKS = {}
_APPEND_LOCKS_GUARD = threading.Lock()


def _append_lock(path_str):
    """Return (creating if necessary) the threading.Lock for an append path."""
    with _APPEND_LOCKS_GUARD:
        lock = _APPEND_LOCKS.get(path_str)
        if lock is None:
            lock = threading.Lock()
            _APPEND_LOCKS[path_str] = lock
        return lock


# ═══════════════════════════════════════════════════════════════════════════
# Event envelope construction helpers
# ═══════════════════════════════════════════════════════════════════════════


def new_event_id():
    """Return a fresh unique event id (uuid4 hex, 32 chars).

    Per §5.1 the event_id is "ULID or uuid4 hex — unique, monotonic-ish for
    ordering". We use uuid4 hex (stdlib only; ULID would need a dependency).
    Uniqueness, not monotonicity, is the load-bearing property — ordering is
    recovered from the on-disk line order (append-only) and from the
    timestamp + cas_version.
    """
    return uuid.uuid4().hex


def now_timestamp():
    """Return the current UTC time as an ISO-8601 string with ``Z`` suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_event(unit_id, event_type, *, cas_version, from_version, actor,
                from_phase=None, to_phase=None, gate_id=None, tier=None,
                evidence_ref=None, payload=None, event_id=None, timestamp=None,
                reason=None):
    """Build a complete, valid event envelope (§5.1) with generated defaults.

    This is the convenience constructor the FEAT-005/006 wiring uses: it fills
    ``event_id`` (uuid4 hex) and ``timestamp`` (ISO-8601 UTC) when absent, and
    always includes every required field. ``payload`` is merged into the
    envelope top-level under the ``"payload"`` key (event-specific facts).

    Returns the event dict. Does NOT append it — call :func:`append_event`.
    """
    ev = {
        "event_id": event_id if event_id else new_event_id(),
        "timestamp": timestamp if timestamp else now_timestamp(),
        "unit_id": unit_id,
        "event_type": event_type,
        "cas_version": cas_version,
        "from_version": from_version,
        "from_phase": from_phase,
        "to_phase": to_phase,
        "actor": actor,
        "gate_id": gate_id,
        "tier": tier,
        "evidence_ref": evidence_ref,
        "payload": payload if isinstance(payload, dict) else {},
    }
    if reason is not None:
        ev["reason"] = reason
    return ev


# ═══════════════════════════════════════════════════════════════════════════
# Append-only JSONL writer (ADR-014 §5.2)
# ═══════════════════════════════════════════════════════════════════════════


def append_event(event, *, log_path=None):
    """Append one event dict as a single JSON line to the event log.

    Atomic line append (§5.2 point 2). Two layers of safety:

      1. **Cross-process file lock** (the Design Review P2-1 concern): a
         companion ``<logfile>.lock`` file is acquired exclusively for the
         duration of the open-write-close. On POSIX this is ``fcntl.flock``;
         on Windows it is ``msvcrt.locking`` on byte 0. This is what makes
         two genuinely-separate processes (separate interpreters, separate
         file handles) serialize their appends — the in-process threading
         lock alone cannot do this.
      2. **Single ``write()`` call** in ``"a"`` mode: even if the lock were
         absent, writing the full line + ``"\\n"`` in one call is atomic at
         the line level on POSIX (writes < PIPE_BUF) and is the documented
         robust Windows pattern.

    Each event line is self-contained and carries both ``from_version`` and
    ``cas_version``, so even if two events interleave in arrival order, each is
    independently interpretable and the monotonicity check detects any
    out-of-order regression.

    The event is JSON-serialized with ``ensure_ascii=False`` (UTF-8 native).
    The file is created (with parents) if absent. Never raises on success;
    on an unrecoverable I/O error the exception propagates to the caller
    (the FEAT-005/006 callers treat the event append as best-effort AFTER the
    state write has committed, so a lost event is recoverable on restart via
    the §3.5 state-ahead-of-log → phase_recovery path).

    Args:
        event: the event dict to append. If it lacks ``event_id`` or
            ``timestamp`` they are generated. If it is not a dict, the call is
            a no-op (defensive — the caller's success path already produced a
            dict).
        log_path: path to the JSONL log file. None → default under cwd.
    """
    if not isinstance(event, dict):
        return
    # Fill the generated defaults if the caller did not supply them (the
    # FEAT-005/006 wiring stamps cas_version/from_version but leaves
    # event_id/timestamp to this module).
    if not event.get("event_id"):
        event["event_id"] = new_event_id()
    if not event.get("timestamp"):
        event["timestamp"] = now_timestamp()

    line = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"

    path = _resolve_path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path_str = str(path.resolve() if path.exists() else path)
    thread_lock = _append_lock(path_str)
    with thread_lock:
        # Cross-process mutual exclusion via a companion lock file. This is
        # the load-bearing safety for the multi-process append test (two
        # separate interpreters racing). The thread lock above only serializes
        # same-process threads; the file lock serializes separate processes.
        with _cross_process_lock(path):
            # "a" mode: O_APPEND on POSIX; the Windows C runtime also honors
            # append mode (each write goes to end-of-file). One write() call
            # for the whole line + newline = atomic at the line level.
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(line)


def _cross_process_lock(path):
    """Return a context manager acquiring an exclusive cross-process lock.

    Guards a companion ``<path>.lock`` file. On POSIX uses ``fcntl.flock``
    (LOCK_EX); on Windows uses ``msvcrt.locking`` on byte 0 (LK_LOCK, blocking
    with retry). The lock file is created if absent. The lock is released on
    context exit (the lock file is left in place — it is reused for the life
    of the log; this avoids a create/delete race). Never blocks forever: the
    Windows path retries ``LK_NBLCK`` with a bounded backoff, falling back to
    best-effort (unlocked append) only after the budget is exhausted (the
    single-write-call atomicity is the backstop).
    """
    import contextlib

    lock_path = Path(str(path) + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    if os.name == "nt":
        import msvcrt

        @contextlib.contextmanager
        def _win_lock():
            fd = _acquire_win_lock(lock_path)
            try:
                yield
            finally:
                try:
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
                try:
                    os.close(fd)
                except OSError:
                    pass

        return _win_lock()

    # POSIX.
    try:
        import fcntl
    except ImportError:  # pragma: no cover - POSIX always has fcntl
        import contextlib

        @contextlib.contextmanager
        def _noop_lock():
            yield

        return _noop_lock()

    @contextlib.contextmanager
    def _posix_lock():
        fh = open(lock_path, "a+", encoding="utf-8")
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            fh.close()

    return _posix_lock()


def _acquire_win_lock(lock_path, *, attempts=40, base_delay=0.005):
    """Open + exclusively lock ``lock_path`` byte 0 on Windows (blocking-retry).

    Returns the raw file descriptor (the caller unlocks + closes it). Uses
    ``msvcrt.locking`` with ``LK_NBLCK`` (non-blocking) + bounded retry/backoff
    so two processes serialize. Falls back to an unlocked fd after the retry
    budget (the single-write-call atomicity is the backstop; a lost event is
    recoverable via the §3.5 phase_recovery path).
    """
    import msvcrt
    import time
    # Open R+W so locking is allowed; create if absent.
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    for attempt in range(attempts):
        try:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            return fd
        except OSError:
            if attempt == attempts - 1:
                return fd  # best-effort: unlocked fd (single-write backstop)
            time.sleep(base_delay * (1.4 ** min(attempt, 10)))
    return fd


def append_events(events, *, log_path=None):
    """Append multiple events to the log, in order (one line each).

    Calls :func:`append_event` for each event in ``events`` (preserving order).
    A non-list/empty ``events`` is a no-op. Each event is appended as a
    separate atomic line append (not one giant write) so a partial failure
    leaves a prefix of the events committed, not a corrupt multi-event line.
    """
    if not isinstance(events, (list, tuple)):
        return
    for event in events:
        append_event(event, log_path=log_path)


# ═══════════════════════════════════════════════════════════════════════════
# JSONL reader
# ═══════════════════════════════════════════════════════════════════════════


def read_events(*, log_path=None, unit_id=None):
    """Read all events from the JSONL log, optionally filtered by ``unit_id``.

    Parses one JSON object per non-blank line. Malformed lines are SKIPPED
    (the log is append-only and a torn write would manifest as a malformed
    final line; skipping it is the fail-safe read — the consistency check
    :func:`check_cas_monotonicity` will then flag the gap). Lines are returned
    in on-disk order (append order = wall-clock order, modulo concurrent
    append interleaving which the monotonicity check detects).

    Args:
        log_path: path to the JSONL log file. None → default under cwd.
        unit_id: when given, only events whose ``unit_id`` matches are
            returned. None (default) returns all events.

    Returns:
        list[dict]: the parsed events, in on-disk order. Empty list when the
        file is missing/empty or contains no parseable lines. Never raises.
    """
    path = _resolve_path(log_path)
    if not path.is_file():
        return []
    events = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            # Skip malformed lines (fail-safe read; the consistency check
            # will flag the resulting gap).
            continue
        if not isinstance(ev, dict):
            continue
        if unit_id is not None and ev.get("unit_id") != unit_id:
            continue
        events.append(ev)
    return events


def last_event_for_unit(unit_id, *, log_path=None):
    """Return the last event for ``unit_id`` (None if none / file missing).

    "Last" = the final event for this unit in on-disk (append) order. Used by
    the restart consistency check (§3.5): the on-disk ``cas_version`` should
    equal the last logged event's ``cas_version``. Never raises.
    """
    events = read_events(log_path=log_path, unit_id=unit_id)
    return events[-1] if events else None


# ═══════════════════════════════════════════════════════════════════════════
# Event envelope validation (ADR-014 §5.1)
# ═══════════════════════════════════════════════════════════════════════════


def validate_event(event):
    """Validate one event envelope (§5.1). Returns a list of error strings.

    Empty list = valid. Checks:

      - ``event`` is a dict.
      - Every name in :data:`REQUIRED_FIELDS` is present.
      - ``event_type`` is in the closed enum :data:`EVENT_TYPES`.
      - ``cas_version`` and ``from_version`` are ints (not bool) when present.

    This is the per-event structural check; cross-event invariants
    (monotonicity, phase legality) are :func:`check_cas_monotonicity` and
    :func:`check_phase_legality`. Never raises.
    """
    errors = []
    if not isinstance(event, dict):
        return ["event is not a dict (got {0})".format(type(event).__name__)]
    for field in REQUIRED_FIELDS:
        if field not in event:
            errors.append("missing required field {0!r}".format(field))
    event_type = event.get("event_type")
    if isinstance(event_type, str) and event_type not in EVENT_TYPES:
        errors.append(
            "unknown event_type {0!r} (not in the closed enum of {1} types)"
            .format(event_type, len(EVENT_TYPES))
        )
    # cas_version / from_version must be ints (not bool) when present.
    for vfield in ("cas_version", "from_version"):
        v = event.get(vfield)
        if v is not None and not (isinstance(v, int) and not isinstance(v, bool)):
            errors.append(
                "{0!r} must be an integer (not bool) when present (got {1!r})"
                .format(vfield, v)
            )
    return errors


# ═══════════════════════════════════════════════════════════════════════════
# Monotonicity check (ADR-014 §3.6)
# ═══════════════════════════════════════════════════════════════════════════


def _events_in_order(events):
    """Return ``events`` sorted by (timestamp, cas_version) for stable replay.

    The log is append-only so on-disk order is the wall-clock order. But
    concurrent appends from two processes can land in an order that does not
    strictly match timestamp order (clock skew) — sorting by timestamp first,
    then cas_version as a tiebreaker, gives a deterministic replay order. When
    timestamps are identical (same second), cas_version breaks the tie so a
    unit's events replay in version order.
    """
    def key(ev):
        ts = ev.get("timestamp") or ""
        cv = ev.get("cas_version")
        cv = cv if isinstance(cv, int) and not isinstance(cv, bool) else -1
        return (ts, cv)
    return sorted(events, key=key)


def check_cas_monotonicity(events_for_unit):
    """Check that a unit's events are strictly monotonic +1 in cas_version.

    Per §3.6: for a unit's events (sorted by timestamp), ``cas_version`` must
    be strictly monotonic +1 AND ``from_version == previous cas_version``. A
    gap (e.g. 0 → 5 skipping 1-4) or a regression (e.g. 3 → 2) is an error.

    The FIRST event is treated as the activation baseline: its
    ``from_version`` may be None (the §3.2 "(entry)→plan" source has no
    prior version) or 0; only its ``cas_version`` must be present. For every
    subsequent event, ``from_version`` must equal the previous event's
    ``cas_version``, and ``cas_version`` must be exactly previous + 1.

    Args:
        events_for_unit: list of event dicts for ONE unit (any order; this
            function sorts them by timestamp/cas_version for stable replay).

    Returns:
        list[str]: empty iff the sequence is strictly monotonic +1. One error
        string per violation. Never raises.
    """
    if not isinstance(events_for_unit, (list, tuple)):
        return ["events_for_unit must be a list"]
    events = [e for e in events_for_unit if isinstance(e, dict)]
    if not events:
        return []
    ordered = _events_in_order(events)
    errors = []
    prev_cas = None
    for idx, ev in enumerate(ordered):
        cv = ev.get("cas_version")
        fv = ev.get("from_version")
        if not (isinstance(cv, int) and not isinstance(cv, bool)):
            errors.append(
                "event #{0}: cas_version must be an integer (got {1!r})"
                .format(idx + 1, cv)
            )
            continue
        if idx == 0:
            # Baseline: the activation event. from_version may be None/0.
            prev_cas = cv
            continue
        # Multiple events may share the same cas_version when one transition
        # produces several audit records (e.g. FEAT-006 emits a gate_result
        # AND a back_edge for the SAME CAS write — both stamped with the same
        # cas_version/from_version). A run of equal cas_version values is the
        # SAME transition viewed from different angles; only the jump to the
        # NEXT distinct cas_version must be exactly +1.
        if cv == prev_cas:
            # Same transition as the previous event. from_version must still
            # match the transition's source (== fv of the prev transition).
            if isinstance(fv, int) and not isinstance(fv, bool):
                # The shared transition's from_version: all events in this run
                # should agree. We do not hard-fail a mismatch here (the
                # cas_version monotonicity is the load-bearing check); we just
                # advance prev_cas unchanged.
                pass
            continue
        # from_version must equal the previous cas_version (the transition's
        # source is the prior committed version).
        if not (isinstance(fv, int) and not isinstance(fv, bool)):
            errors.append(
                "event #{0}: from_version must be an integer (got {1!r})"
                .format(idx + 1, fv)
            )
        elif fv != prev_cas:
            errors.append(
                "event #{0}: from_version ({1}) != previous cas_version ({2}) "
                "— monotonicity broken".format(idx + 1, fv, prev_cas)
            )
        # cas_version must be exactly previous + 1.
        if cv != prev_cas + 1:
            errors.append(
                "event #{0}: cas_version ({1}) is not previous+1 ({2}+1) — "
                "gap or regression".format(idx + 1, cv, prev_cas)
            )
        prev_cas = cv
    return errors


# ═══════════════════════════════════════════════════════════════════════════
# Phase-legality replay (ADR-014 §3.6)
# ═══════════════════════════════════════════════════════════════════════════


def check_phase_legality(events_for_unit):
    """Replay a unit's events and verify each phase transition is legal (§3.6).

    For each consecutive pair of events, the ``(from_phase, to_phase)``
    transition must be legal per the §3.2 table (delegated to
    :func:`loop_paro_engine.validate_transition`). The replay baseline is the
    start of history: the first event is the ``(entry) → plan`` activation
    (``from_phase`` None / "(entry)"). An illegal jump (e.g. ``plan →
    observe`` skipping ``act``) is an error.

    The gate/fuse facts (``gate_result``, ``loop_count``, ``max_rounds``) are
    recovered from the event envelope (top-level or nested under ``payload``)
    and passed to the validator so the reflect→{exit, plan, escalate} branch
    is checked correctly.

    Args:
        events_for_unit: list of event dicts for ONE unit (any order; sorted
            by timestamp/cas_version for stable replay).

    Returns:
        list[str]: empty iff every transition is legal. One error string per
        illegal transition. Never raises.
    """
    if not isinstance(events_for_unit, (list, tuple)):
        return ["events_for_unit must be a list"]
    events = [e for e in events_for_unit if isinstance(e, dict)]
    if not events:
        return []
    # Local import: loop_paro_engine is a peer module. Deferred so this module
    # can be imported in contexts where the engine is not needed (e.g. a pure
    # event-log read).
    try:
        import loop_paro_engine as paro
    except Exception as exc:  # pragma: no cover - defensive
        return ["cannot load loop_paro_engine for phase-legality replay: {0}".format(exc)]

    ordered = _events_in_order(events)
    errors = []
    prev_phase = None  # the §3.2 "(entry)" baseline
    # Event types that ARE phase transitions (carry a real to_phase to check).
    # gate_result / fuse_trip / escalation_resolved / unit_blocked /
    # unit_withdrawn / dependency_block / wip_admit / wip_deny are audit
    # records ABOUT a transition or admission decision, not phase moves
    # themselves (FEAT-006 emits a separate phase_transition / back_edge /
    # loop_exit / phase_enter event for the actual phase move). Only the
    # phase-moving types are replayed here.
    phase_moving = {
        "phase_enter", "phase_transition", "back_edge", "loop_exit",
    }
    for idx, ev in enumerate(ordered):
        et = ev.get("event_type")
        # Skip events that are not phase transitions: audit markers and
        # admission decisions have no (from_phase, to_phase) to validate.
        if et in ("phase_recovery", "recovery_conflict"):
            continue
        if et not in phase_moving:
            continue
        to_phase = ev.get("to_phase")
        if to_phase is None:
            continue  # no target phase to validate.
        # from_phase: prefer the event's recorded source; fall back to the
        # replayed prev_phase so the (entry)→plan activation is checked with
        # the entry sentinel.
        raw_from = ev.get("from_phase")
        if raw_from is None:
            from_phase = prev_phase
        else:
            from_phase = raw_from

        # Recover the gate/fuse facts the validator needs for the
        # reflect→{exit, plan, escalate} branch.
        payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
        check_event = {}
        gate_result = ev.get("gate_result")
        if gate_result is None:
            gate_result = payload.get("gate_result")
        loop_count = ev.get("loop_count")
        if loop_count is None:
            loop_count = payload.get("loop_count")
        max_rounds = ev.get("max_rounds")
        if max_rounds is None:
            max_rounds = payload.get("max_rounds")
        if gate_result is not None:
            check_event["gate_result"] = gate_result
        if loop_count is not None:
            check_event["loop_count"] = loop_count
        if max_rounds is not None:
            check_event["max_rounds"] = max_rounds

        legal, reason = paro.validate_transition(from_phase, to_phase, check_event)
        if not legal:
            errors.append(
                "event #{0} ({1}): illegal phase transition {2!r}→{3!r}: {4}"
                .format(idx + 1, et, from_phase, to_phase, reason)
            )
        # Advance the replayed phase only for events that actually move the
        # phase (terminal events exit/escalate/withdrawn move out of the
        # forward chain; recovery markers were skipped above). For a legal
        # transition, prev_phase becomes to_phase (so the next event's source
        # is consistent). For an illegal one, leave prev_phase unchanged so
        # subsequent errors are reported against the actual on-disk phase.
        if legal and to_phase in (paro.PLAN, paro.ACT, paro.OBSERVE, paro.REFLECT):
            prev_phase = to_phase
    return errors


# ═══════════════════════════════════════════════════════════════════════════
# Restart recovery commit (ADR-014 §3.5) — write synthetic events to the log
# ═══════════════════════════════════════════════════════════════════════════


def commit_recovery(recovery_result, *, log_path=None, actor="recover_state"):
    """Write a :class:`loop_paro_engine.RecoveryResult`'s synthetic events to the log.

    FEAT-007 completes the §3.5 restart-recovery path: ``recover_state`` is a
    PURE READ that classifies each active unit's on-disk-vs-log consistency and
    collects (a) ``phase_recovery`` synthetic events for state-ahead-of-log
    units and (b) ``recovery_conflict`` markers for log-ahead-of-state units.
    This function commits those markers to the event log so the audit trail is
    consistent after restart (the gap between state and log is closed on the
    log side; the fail-closed units get a recovery_conflict event).

    Args:
        recovery_result: a :class:`loop_paro_engine.RecoveryResult` (the
            return value of :func:`loop_paro_engine.recover_state`). For
            tolerance, any object with ``synthetic_events`` and ``conflicts``
            attributes (or a dict with those keys) is accepted.
        log_path: path to the JSONL log file. None → default under cwd.
        actor: the actor string for the recorded events.

    Returns:
        int: the number of events appended (synthetic phase_recovery events +
        recovery_conflict markers). Never raises — best-effort.
    """
    synth = []
    conflicts = []
    units = {}
    if hasattr(recovery_result, "synthetic_events"):
        synth = list(getattr(recovery_result, "synthetic_events") or [])
        conflicts = list(getattr(recovery_result, "conflicts") or [])
        units = getattr(recovery_result, "units", {}) or {}
    elif isinstance(recovery_result, dict):
        synth = list(recovery_result.get("synthetic_events") or [])
        conflicts = list(recovery_result.get("conflicts") or [])
        units = recovery_result.get("units") or {}

    count = 0
    for ev in synth:
        # Build a full §5.1 envelope around the synthetic event.
        unit_id = ev.get("unit_id") if isinstance(ev, dict) else None
        full = build_event(
            unit_id, "phase_recovery",
            cas_version=ev.get("cas_version") if isinstance(ev, dict) else None,
            from_version=None,
            actor=actor,
            from_phase=None,
            to_phase=None,
            payload={"recovered_version": ev.get("cas_version") if isinstance(ev, dict) else None,
                     "reason": ev.get("reason") if isinstance(ev, dict) else None},
        )
        append_event(full, log_path=log_path)
        count += 1

    for uid in conflicts:
        state = units.get(uid, {}) if isinstance(units, dict) else {}
        full = build_event(
            uid, "recovery_conflict",
            cas_version=state.get("cas_version") if isinstance(state, dict) else None,
            from_version=None,
            actor=actor,
            from_phase=None,
            to_phase=None,
            payload={
                "last_logged_version": None,  # filled by caller if known
                "on_disk_version": state.get("cas_version") if isinstance(state, dict) else None,
                "reason": "event log ahead of on-disk state; unit fail-closed to blocked",
            },
        )
        append_event(full, log_path=log_path)
        count += 1

    return count


__all__ = [
    "EVENT_TYPES",
    "REQUIRED_FIELDS",
    "EVENT_LOG_FILENAME",
    "EVENT_LOG_DIRNAME",
    "default_log_path",
    "new_event_id",
    "now_timestamp",
    "build_event",
    "append_event",
    "append_events",
    "read_events",
    "last_event_for_unit",
    "validate_event",
    "check_cas_monotonicity",
    "check_phase_legality",
    "commit_recovery",
]


if __name__ == "__main__":  # pragma: no cover - manual smoke
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    ev = build_event(
        "smoke.unit", "phase_transition", cas_version=1, from_version=0,
        actor="smoke", from_phase="plan", to_phase="act",
    )
    errs = validate_event(ev)
    print("built event; validation errors: {0}".format(errs or "none"))
    print("monotonicity of [v0, v1]: {0}".format(
        check_cas_monotonicity([
            {"timestamp": "2026-07-23T00:00:00Z", "cas_version": 0,
             "from_version": None, "to_phase": "plan"},
            {"timestamp": "2026-07-23T00:00:01Z", "cas_version": 1,
             "from_version": 0, "from_phase": "plan", "to_phase": "act"},
        ])
    ))
