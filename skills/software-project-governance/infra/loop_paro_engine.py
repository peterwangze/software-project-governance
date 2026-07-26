#!/usr/bin/env python3
"""Persistent Plan-Act-Observe-Reflect (PARO) state machine + CAS writer.

FEAT-005 (ADR-014 §3, 0.68.0). Product code, authorized by Design Review
APPROVED_WITH_NOTES/0 (EVD-841).

This module is the **executable PARO state machine**: it constrains
``loop_state.agent_phase`` transitions to the legal set defined in ADR-014 §3.2,
and persists every transition to ``flow-unit-runtime.json`` under a per-unit
monotonic **CAS version** (``loop_state.cas_version``, the additive field
introduced by FEAT-005) using optimistic concurrency control.

**Scope (FEAT-005 ONLY):**

  - The pure transition validator (:func:`validate_transition`) — the §3.2 table
    encoded as an executable predicate.
  - The CAS-guarded transition writer (:func:`apply_transition`) — read →
    validate → compute → atomic write with conflict detection.
  - Activation (:func:`activate_unit`) — the ``(entry) → plan`` transition that
    assigns the initial ``cas_version = 0``.
  - Restart recovery (:func:`recover_state`) — read-based (not replay-based);
    the event-log consistency hook is present but a no-op when the log is
    ``None`` (FEAT-007 provides the log).

**Out of scope (NOT implemented here):**

  - FEAT-006 (gate processor / fuse production wiring). This module exposes the
    state machine the gate processor will drive; it does not itself consume
    production gate events.
  - FEAT-007 (event log JSONL). The ``event_log`` parameters are hooks: when
    ``None`` (the only value FEAT-005 passes), the consistency/replay checks are
    skipped per §3.5 ("state file alone is sufficient").

**Constraints honored:**

  - The 0.67.0 v2 validator (``checks.flow_unit_runtime_v2
    .validate_flow_unit_runtime_payload_v2``) is byte-frozen; this module does
    NOT modify it. The additive transition/CAS validation pass lives in a
    SEPARATE function (``validate_loop_runtime_v2_with_transitions``) added to
    that module.
  - ``loop_engine.py``'s pure functions (``derive_round`` / ``fuse_decision`` /
    ``escalation_payload`` / ``activate_loop_state``) are NOT modified. This
    module's fuse boundary deliberately matches ``fuse_decision`` exactly
    (``escalate if loop_count > max_rounds else iterate``) so the two never
    diverge.
  - The contract ``schema_version`` stays ``"2.0"``; ``cas_version`` is a
    per-unit additive field.
  - RISK-037 / RISK-042 remain open.

**CAS protocol (ADR-014 §3.3), implemented in :func:`apply_transition`:**

    1. READ    unit = load runtime_file → flow_units[id]
                expected_version = unit.loop_state.cas_version
                from_phase       = unit.loop_state.agent_phase
    2. VALIDATE transition (from_phase, to_phase, event) is legal; else FAIL
    3. COMPUTE new_unit = apply §3.2 side effects
                new_unit.loop_state.cas_version = expected_version + 1
    4. WRITE   (atomic, lock-guarded critical section):
                re-read on-disk; if on-disk cas_version != expected_version
                  → CONFLICT (another writer advanced this unit; no write)
                else: temp-file + os.replace (atomic rename)
    5. RETURN  TransitionResult(success/conflict/illegal, new cas_version)

The per-file ``threading.Lock`` guards ONLY the re-read-check-replace critical
section (step 4), NEVER the compute (step 3) — this is the §3.3 "optimistic
locking without holding a lock across the compute step" discipline, and it is
what makes the threading test deterministic: N writers that all read version V
produce exactly one commit at V+1 and N-1 CONFLICT results (no lost updates).

Usage:
    from loop_paro_engine import (
        validate_transition, apply_transition, activate_unit, recover_state,
        TransitionResult, RecoveryResult,
    )

    # Pure legality check (no I/O):
    legal, reason = validate_transition("plan", "act", {})

    # CAS-guarded write:
    result = apply_transition(
        "shitu.story.Skeleton", "act",
        event={"reason": "plan accepted"},
        runtime_file=path_to_flow_unit_runtime_json,
    )
    if result.status == "success":
        ...  # result.new_cas_version is the committed version
"""

import json
import os
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════
# Phase vocabulary + transition status constants
# ═══════════════════════════════════════════════════════════════════════════

# The four PARO phases declared by the v2 contract's allowed_agent_phases.
PLAN = "plan"
ACT = "act"
OBSERVE = "observe"
REFLECT = "reflect"

# Terminal pseudo-phases. The first four are the contract's allowed phases; the
# terminal outcomes (exit / escalate / withdrawn) are encoded as the writer's
# to_phase targets. On a terminal transition the unit's runtime_status and
# gate_state are updated per §3.2 (agent_phase itself is left at "reflect" or
# set per the contract — the terminal marker lives on runtime_status).
EXIT = "exit"
ESCALATE = "escalate"
WITHDRAWN = "withdrawn"

# Sentinel for the implicit pre-activation phase (the §3.2 "(entry)" node).
# validate_transition accepts from_phase=None or the strings "(entry)"/"entry"
# to denote activation.
ENTRY = None

# The non-terminal forward phases in order (for adjacency checks).
_FORWARD_ORDER = (PLAN, ACT, OBSERVE, REFLECT)

# Transition-result status strings.
STATUS_SUCCESS = "success"
STATUS_CONFLICT = "conflict"
STATUS_ILLEGAL = "illegal"
STATUS_ERROR = "error"

# Recovery-result classification.
RECOVERY_OK = "ok"
RECOVERY_CONFLICT = "recovery_conflict"

# Gate-result normalization. A gate/review result is mapped to a boolean
# "passed" for the reflect→{exit, plan, escalate} branch decision (§3.2 rule 1:
# APPROVED/passed is terminal; NEEDS_CHANGE/failed is non-terminal; BLOCKED is
# terminal only via fuse trip). Anything not in the PASSED set counts as a
# failure driving iterate-vs-escalate.
_GATE_PASSED_RESULTS = frozenset({
    "APPROVED",
    "APPROVED_WITH_NOTES",
    "APPROVED-WITH-NOTES",
    "passed",
    "pass",
    "PASS",
    "ok",
    "OK",
    "lgtm",
    "LGTM",
})


def _gate_passed(gate_result):
    """Return True iff ``gate_result`` denotes a passing gate (§3.2 rule 1).

    None / unknown / failure results return False. A None gate_result is NOT a
    pass (it means no result was recorded); the caller must supply a real
    result for gate-driven transitions.
    """
    if gate_result is None:
        return False
    if isinstance(gate_result, bool):
        return gate_result
    if isinstance(gate_result, str):
        return gate_result.strip() in _GATE_PASSED_RESULTS
    return False


def _is_int(value):
    """True iff ``value`` is an int and NOT a bool (mirrors the v2 validator)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _normalize_from_phase(from_phase):
    """Normalize the from_phase argument.

    Accepts None (the canonical ENTRY sentinel) and the strings "(entry)" /
    "entry" / "" as activation sources; returns None for all of those. Any
    other value is returned as-is (string phases).
    """
    if from_phase is None:
        return None
    if isinstance(from_phase, str):
        lowered = from_phase.strip().lower()
        if lowered in ("", "(entry)", "entry"):
            return None
        return from_phase
    return from_phase


# ═══════════════════════════════════════════════════════════════════════════
# Pure transition validator (ADR-014 §3.2)
# ═══════════════════════════════════════════════════════════════════════════


def validate_transition(from_phase, to_phase, event=None):
    """Return ``(legal, reason)`` for a proposed PARO phase transition.

    Pure: no I/O, no module state. Encodes the §3.2 transition table:

      - (entry)→plan            : unit activated (always legal)
      - plan→act                : plan accepted
      - act→observe             : action complete
      - observe→reflect         : review result recorded
      - reflect→plan            : gate FAILED AND loop_count <= max_rounds
                                  (iterate / back-edge; §3.3 rule 2: round ==
                                  max is STILL iterate, matching fuse_decision)
      - reflect→exit            : gate PASSED (terminal)
      - reflect→escalate        : gate FAILED AND loop_count >  max_rounds
                                  (fuse trip; terminal)
      - *→withdrawn             : operator withdraw (terminal)

    Every other (from, to) pair is illegal and is rejected (the caller does not
    mutate state).

    The ``event`` dict carries the contextual facts the table needs:

      - ``gate_result`` (str) or ``gate_passed`` (bool): the review/gate result
        driving the reflect→{exit, plan, escalate} branch. Required for those
        three transitions.
      - ``loop_count`` (int): the unit's current loop_count, BEFORE the
        transition. Required for reflect→plan and reflect→escalate (the fuse
        boundary).
      - ``max_rounds`` (int): the tier fuse's max_rounds. Required for
        reflect→plan and reflect→escalate.

    When a required fact is absent the validator rejects the transition
    (fail-closed: it never guesses the fuse boundary).

    Args:
        from_phase: The current ``agent_phase`` (``plan|act|observe|reflect``),
            or None / "(entry)" / "entry" for the activation source.
        to_phase: The target phase (``plan|act|observe|reflect|exit|escalate|
            withdrawn``).
        event: Optional dict of contextual facts (see above).

    Returns:
        (legal: bool, reason: str). ``reason`` is a short human-readable
        explanation (an event-type label on success, a diagnostic on rejection).
        Never raises — a non-dict event is treated as empty.
    """
    if not isinstance(event, dict):
        event = {}
    frm = _normalize_from_phase(from_phase)

    # ── Terminal: operator withdraw is legal from any non-terminal phase. ────
    if to_phase == WITHDRAWN:
        # Withdrawn is itself terminal; cannot withdraw from an already-terminal
        # pseudo-phase. From the four PARO phases (and entry) it is legal.
        if frm in _FORWARD_ORDER or frm is None:
            return True, "unit_withdrawn"
        return False, "cannot withdraw from terminal phase {0!r}".format(frm)

    # ── (entry) → plan : activation. ─────────────────────────────────────────
    if frm is None:
        if to_phase == PLAN:
            return True, "phase_enter"
        return False, "activation must target 'plan', not {0!r}".format(to_phase)

    # Beyond here, frm is one of the four PARO phases (a non-terminal phase).
    if frm not in _FORWARD_ORDER:
        return False, "unknown from_phase {0!r}".format(frm)

    if to_phase not in (PLAN, ACT, OBSERVE, REFLECT, EXIT, ESCALATE):
        return False, "unknown to_phase {0!r}".format(to_phase)

    # ── reflect → {exit, plan, escalate}: the gate-driven branches. ──────────
    # These take PRECEDENCE over the forward-adjacency check, because
    # reflect→plan is a back-edge (plan is reachable from reflect via iterate,
    # NOT via the plan→act→observe→reflect forward chain). Checking forward
    # adjacency first would mis-classify the back-edge as an illegal reverse
    # jump. All three branches require a gate result (passed vs failed); the
    # iterate/escalate branches additionally require the fuse boundary facts.
    if frm == REFLECT and to_phase in (EXIT, PLAN, ESCALATE):
        gate_passed = event.get("gate_passed")
        if gate_passed is None:
            gate_result = event.get("gate_result")
            gate_passed = _gate_passed(gate_result)
        else:
            gate_passed = bool(gate_passed)

        if to_phase == EXIT:
            if not gate_passed:
                return False, (
                    "reflect→exit requires a PASSED gate result "
                    "(gate_result={0!r})".format(event.get("gate_result"))
                )
            return True, "gate_result+loop_exit"

        # to_phase in (PLAN, ESCALATE): gate must have FAILED.
        if gate_passed:
            return False, (
                "reflect→{0} requires a FAILED gate result, but the gate "
                "passed (use reflect→exit instead)".format(to_phase)
            )

        # Fuse boundary (§3.3 rule 2, matching loop_engine.fuse_decision):
        #   loop_count <= max_rounds → iterate (reflect→plan)
        #   loop_count >  max_rounds → escalate (reflect→escalate)
        loop_count = event.get("loop_count")
        max_rounds = event.get("max_rounds")
        if not (_is_int(loop_count) and _is_int(max_rounds)):
            return False, (
                "reflect→{0} requires integer event['loop_count'] and "
                "event['max_rounds'] for the fuse boundary decision "
                "(got loop_count={1!r}, max_rounds={2!r})".format(
                    to_phase, loop_count, max_rounds,
                )
            )
        over_budget = loop_count > max_rounds
        if to_phase == PLAN:
            if over_budget:
                return False, (
                    "reflect→plan (iterate) illegal: loop_count ({0}) > "
                    "max_rounds ({1}) — fuse exhausted; use reflect→escalate".format(
                        loop_count, max_rounds,
                    )
                )
            return True, "back_edge+gate_result"
        # to_phase == ESCALATE
        if not over_budget:
            return False, (
                "reflect→escalate (fuse trip) illegal: loop_count ({0}) <= "
                "max_rounds ({1}) — fuse not exhausted; use reflect→plan".format(
                    loop_count, max_rounds,
                )
            )
        return True, "fuse_trip+gate_result"

    # ── Forward adjacency: plan→act→observe→reflect (the only legal forward
    # chain among the four phases, now that the reflect back-edge and terminals
    # are handled above). ────────────────────────────────────────────────────
    if frm in _FORWARD_ORDER and to_phase in _FORWARD_ORDER:
        # Same-phase "transition" is a no-op, not a legal transition.
        if frm == to_phase:
            return False, "same-phase transition {0!r}→{1!r} is a no-op".format(frm, to_phase)
        expected = _next_phase(frm)
        if to_phase != expected:
            return False, (
                "illegal forward jump {0!r}→{1!r} (must be {0!r}→{2!r}); "
                "no phase may be skipped".format(frm, to_phase, expected)
            )
        if to_phase == REFLECT:
            # observe→reflect: the review result is recorded here. No gate_result
            # requirement at validation time (the result is *recorded* on this
            # transition; the branch decision happens at reflect→{exit,plan,
            # escalate}). Emit the combined event-type label per §3.2.
            return True, "phase_transition+gate_result"
        return True, "phase_transition"

    # Any other reflect→* (e.g. reflect→observe reverse) or non-adjacent combo.
    return False, "illegal transition {0!r}→{1!r}".format(frm, to_phase)


def _next_phase(phase):
    """Return the legally-adjacent next phase in the forward chain, or None."""
    if phase not in _FORWARD_ORDER:
        return None
    idx = _FORWARD_ORDER.index(phase)
    if idx + 1 >= len(_FORWARD_ORDER):
        return None
    return _FORWARD_ORDER[idx + 1]


# ═══════════════════════════════════════════════════════════════════════════
# Result dataclasses
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class TransitionResult:
    """Outcome of :func:`apply_transition` / :func:`activate_unit`.

    Attributes:
        status: one of ``STATUS_SUCCESS`` / ``STATUS_CONFLICT`` /
            ``STATUS_ILLEGAL`` / ``STATUS_ERROR``.
        unit_id: the flow_unit_id the transition targeted.
        to_phase: the requested target phase.
        from_phase: the phase the unit was in (None on a failed read).
        from_cas_version: the cas_version the writer observed (None if the unit
            had none, e.g. a dormant unit at activation).
        new_cas_version: the committed cas_version on SUCCESS; None otherwise.
        event_type: the §3.2 recorded-event-type label on success (e.g.
            ``"phase_transition"``, ``"back_edge+gate_result"``); the rejection
            reason otherwise.
        reason: short diagnostic (always populated).
        unit: the committed unit dict on SUCCESS; None otherwise.
    """
    status: str
    unit_id: object = None
    to_phase: object = None
    from_phase: object = None
    from_cas_version: object = None
    new_cas_version: object = None
    event_type: str = ""
    reason: str = ""
    unit: dict = None

    @property
    def success(self):
        return self.status == STATUS_SUCCESS


@dataclass
class RecoveryResult:
    """Outcome of :func:`recover_state`.

    Attributes:
        runtime_found: False when the runtime file is missing/corrupt.
        units: dict ``{flow_unit_id: recovered_state_dict}`` for active units.
            Each recovered_state_dict carries ``agent_phase``, ``loop_count``,
            ``max_rounds``, ``fuse_tripped``, ``cas_version``, ``runtime_status``.
        conflicts: list of unit_ids that were fail-closed to ``blocked`` with a
            ``recovery_conflict`` classification (event-log ahead of state — the
            dangerous case; only possible when ``event_log`` is supplied).
        synthetic_events: list of ``phase_recovery`` events that FEAT-007 would
            append when the on-disk state is ahead of the last logged event.
            Populated only when ``event_log`` is supplied; FEAT-005 does not
            write the log itself.
        issues: list of non-fatal diagnostics (e.g. unreadable units).
    """
    runtime_found: bool = False
    units: dict = field(default_factory=dict)
    conflicts: list = field(default_factory=list)
    synthetic_events: list = field(default_factory=list)
    issues: list = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# Runtime file I/O (atomic write + load helpers)
# ═══════════════════════════════════════════════════════════════════════════


def _atomic_replace_bytes(path, content):
    """Replace ``path`` atomically with prebuilt bytes.

    Mirrors ``loop_migration._atomic_replace_bytes`` (the 0.66.1 transaction
    discipline): temp-file in the same directory (so the rename is atomic on
    POSIX and Windows), fsync the temp before rename, ``os.replace`` for the
    atomic commit, cleanup on any failure. A reader therefore never observes a
    half-written file — on a crash it sees either the pre- or post-transition
    bytes.

    On Windows, ``os.replace`` to a destination that another thread/process has
    momentarily open for reading can raise ``PermissionError [WinError 5]``.
    This is a transient collision (the reader's handle closes within
    microseconds), not a real permission failure. We retry the rename with a
    short backoff — the same discipline pip/setuptools use for atomic writes on
    Windows. The CAS critical section is held across this call, so the retry
    does not weaken correctness; it only smooths the Windows file-handle race.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        _replace_with_retry(temp_name, str(path))
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def _replace_with_retry(src, dst, *, attempts=12, base_delay=0.004):
    """``os.replace`` with a bounded retry on transient Windows handle races.

    On POSIX ``os.replace`` is uninterruptible atomic. On Windows, if another
    handle has the destination open for read, the replace raises
    ``PermissionError``; the standard remedy (pip, setuptools, pathlib) is to
    retry briefly. We retry on ``PermissionError`` and ``OSError``-with-WinError
    5 / 32 (access-denied / sharing-violation); any other error propagates.
    """
    import time
    last_exc = None
    for attempt in range(attempts):
        try:
            os.replace(src, dst)
            return
        except (PermissionError, OSError) as exc:
            last_exc = exc
            # Only retry on the transient Windows sharing/access errors.
            errno = getattr(exc, "winerror", None) or getattr(exc, "errno", None)
            transient = (
                getattr(exc, "winerror", None) in (5, 32)
                or isinstance(exc, PermissionError)
            )
            if not transient or attempt == attempts - 1:
                raise
            time.sleep(base_delay * (2 ** attempt))
    if last_exc:  # pragma: no cover - defensive (loop always returns or raises)
        raise last_exc


def _load_runtime(runtime_file):
    """Load the runtime payload from ``runtime_file``.

    Returns the parsed dict, or None if the file is missing/corrupt/unreadable.
    Never raises — callers rely on a graceful "no data" response.
    """
    path = Path(runtime_file) if not isinstance(runtime_file, Path) else runtime_file
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None


def _serialize(payload):
    """Serialize the payload to deterministic UTF-8 bytes.

    Stable key ordering makes the on-disk file diff-friendly and makes
    "file is either old or new, never partial" inspectable in tests.
    """
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")


# Per-file locks guarding the CAS critical section (re-read → check → replace).
# The dict access itself is guarded by _FILE_LOCKS_GUARD. Locks are held ONLY
# across the re-read-check-replace, never across the compute step (§3.3).
_FILE_LOCKS = {}
_FILE_LOCKS_GUARD = threading.Lock()


def _file_lock(path_str):
    """Return (creating if necessary) the threading.Lock for a file path."""
    with _FILE_LOCKS_GUARD:
        lock = _FILE_LOCKS.get(path_str)
        if lock is None:
            lock = threading.Lock()
            _FILE_LOCKS[path_str] = lock
        return lock


def _find_unit(payload, unit_id):
    """Return the unit dict for ``unit_id`` or None (fail-closed)."""
    if not isinstance(payload, dict):
        return None
    flow_units = payload.get("flow_units")
    if not isinstance(flow_units, list):
        return None
    for unit in flow_units:
        if isinstance(unit, dict) and unit.get("flow_unit_id") == unit_id:
            return unit
    return None


def _loop_state_of(unit):
    """Return the unit's loop_state dict (empty dict if absent/non-dict)."""
    ls = unit.get("loop_state")
    return ls if isinstance(ls, dict) else {}


def _gate_state_of(unit):
    gs = unit.get("gate_state")
    return gs if isinstance(gs, dict) else {}


def _cas_version_of(unit):
    """Return the unit's cas_version, or None if absent/not-yet-activated."""
    ls = _loop_state_of(unit)
    cv = ls.get("cas_version")
    return cv if _is_int(cv) else None


# ═══════════════════════════════════════════════════════════════════════════
# Side-effect computation (§3.2) — pure: given an old unit + event, new unit
# ═══════════════════════════════════════════════════════════════════════════


def _sync_gate_result(new_unit, value):
    """Set both loop_state.last_gate_result and gate_state.last_result.

    This preserves the 0.67.0 unification invariant on every write (§3.6). The
    two fields are ALWAYS written together; FEAT-005 never writes one without
    the other.
    """
    ls = _loop_state_of(new_unit)
    gs = _gate_state_of(new_unit)
    ls["last_gate_result"] = value
    gs["last_result"] = value
    return new_unit


def _apply_side_effects(unit, to_phase, event, *, is_activation, loop_count,
                        max_rounds, gate_result):
    """Return a NEW unit dict with the §3.2 side effects applied.

    Does NOT mutate the input. The caller assigns cas_version separately (0 for
    activation, expected+1 otherwise) because that is part of the CAS protocol,
    not the logical side effect.

    Args:
        unit: the current unit dict (read from disk).
        to_phase: the legal target phase.
        event: the transition event dict.
        is_activation: True for the (entry)→plan transition.
        loop_count: the current loop_count (before transition).
        max_rounds: the fuse max_rounds.
        gate_result: the gate_result string (or None) from the event.
    """
    # Shallow-copy the unit and deep-ish-copy the nested state dicts so we never
    # mutate the caller's in-memory object.
    new_unit = dict(unit)
    ls = dict(_loop_state_of(unit))
    fuse = dict(ls.get("fuse") if isinstance(ls.get("fuse"), dict) else {})
    gs = dict(_gate_state_of(unit))
    new_unit["loop_state"] = ls
    new_unit["gate_state"] = gs
    ls["fuse"] = fuse

    if is_activation:
        # (entry)→plan: agent_phase=plan, loop_count=0, fuse.tripped=false.
        ls["agent_phase"] = PLAN
        ls["loop_count"] = 0
        ls["active_loop"] = True
        fuse["tripped"] = False
        return new_unit

    if to_phase == ACT:
        ls["agent_phase"] = ACT
        return new_unit

    if to_phase == OBSERVE:
        ls["agent_phase"] = OBSERVE
        return new_unit

    if to_phase == REFLECT:
        # observe→reflect: review result recorded (gate_state.last_result set,
        # last_gate_result synced). The event may carry the recorded result.
        ls["agent_phase"] = REFLECT
        if gate_result is not None:
            _sync_gate_result(new_unit, gate_result)
        return new_unit

    if to_phase == PLAN:
        # reflect→plan: back-edge. loop_count += 1, last result = failed result.
        ls["agent_phase"] = PLAN
        ls["loop_count"] = int(loop_count) + 1
        _sync_gate_result(new_unit, gate_result if gate_result is not None else "NEEDS_CHANGE")
        return new_unit

    if to_phase == EXIT:
        # reflect→exit: gate passed. gate_state.status=passed; agent_phase left
        # at reflect (terminal marker is the passed status).
        gs["status"] = "passed"
        _sync_gate_result(new_unit, gate_result if gate_result is not None else "APPROVED")
        return new_unit

    if to_phase == ESCALATE:
        # reflect→escalate: fuse trip. fuse.tripped=true, runtime_status=blocked.
        fuse["tripped"] = True
        new_unit["runtime_status"] = "blocked"
        gs["status"] = "blocked"
        _sync_gate_result(new_unit, gate_result if gate_result is not None else "NEEDS_CHANGE")
        return new_unit

    if to_phase == WITHDRAWN:
        new_unit["runtime_status"] = "withdrawn"
        gs["status"] = "withdrawn"
        return new_unit

    # Defensive: unknown to_phase should have been rejected by validate_transition.
    return new_unit


# ═══════════════════════════════════════════════════════════════════════════
# CAS-guarded transition writer (ADR-014 §3.3)
# ═══════════════════════════════════════════════════════════════════════════


def apply_transition(unit_id, to_phase, event=None, *, runtime_file,
                     side_effects=None, max_retries=0):
    """Apply a CAS-guarded PARO phase transition for ``unit_id``.

    Implements the §3.3 CAS protocol: READ → VALIDATE → COMPUTE → atomic WRITE
    with conflict detection. On success the unit's ``loop_state.cas_version``
    is incremented by exactly 1 and the file is replaced atomically (a reader
    never sees a torn state). On conflict (another writer committed a transition
    for this unit between our read and our write) the writer returns
    ``STATUS_CONFLICT`` and writes nothing — fail-closed, no lost updates.

    The ``side_effects`` callable, if supplied, is invoked as
    ``side_effects(new_unit, event)`` AFTER the canonical §3.2 side effects are
    applied and BEFORE the cas_version bump; it may augment the new unit (e.g.
    FEAT-006 adding evidence_refs / pause points) and must return the (possibly
    mutated) unit dict. It is the extension hook for the gate processor.

    Args:
        unit_id: The flow_unit_id to transition.
        to_phase: The target phase (``plan|act|observe|reflect|exit|escalate|
            withdrawn``). Activation ((entry)→plan) uses :func:`activate_unit`.
        event: The transition event dict (passed to :func:`validate_transition`
            and to ``side_effects``).
        runtime_file: Path to ``flow-unit-runtime.json``.
        side_effects: Optional ``(new_unit, event) -> new_unit`` callable.
        max_retries: On CONFLICT, retry the whole read-validate-compute-write
            cycle this many times (re-reading fresh state each time) before
            returning STATUS_CONFLICT. Default 0 = fail-closed on the first
            conflict. Retries re-validate against the fresh on-disk version, so
            a retried transition commits at a higher cas_version only if it is
            still legal from the new state.

    Returns:
        TransitionResult. Never raises on transition/CAS outcomes — unexpected
        I/O errors surface as ``STATUS_ERROR`` with the exception message.
    """
    if not isinstance(event, dict):
        event = {}

    runtime_path = Path(runtime_file) if not isinstance(runtime_file, Path) else runtime_file
    path_str = str(runtime_path.resolve() if runtime_path.exists() else runtime_path)
    lock = _file_lock(path_str)

    attempt = 0
    while True:
        attempt += 1
        # ── Step 1: READ (unlocked — the compute runs outside the critical
        # section per §3.3). ─────────────────────────────────────────────────
        payload = _load_runtime(runtime_path)
        if not isinstance(payload, dict):
            return TransitionResult(
                status=STATUS_ERROR, unit_id=unit_id, to_phase=to_phase,
                reason="runtime file missing or corrupt: {0}".format(runtime_path),
            )
        unit = _find_unit(payload, unit_id)
        if unit is None:
            return TransitionResult(
                status=STATUS_ERROR, unit_id=unit_id, to_phase=to_phase,
                reason="flow_unit_id {0!r} not found in runtime file".format(unit_id),
            )

        ls = _loop_state_of(unit)
        from_phase = ls.get("agent_phase")
        expected_version = _cas_version_of(unit)
        if expected_version is None:
            return TransitionResult(
                status=STATUS_ILLEGAL, unit_id=unit_id, to_phase=to_phase,
                from_phase=from_phase, from_cas_version=None,
                reason=(
                    "unit {0!r} has no cas_version (not activated); use "
                    "activate_unit() for the (entry)→plan transition".format(unit_id)
                ),
            )
        loop_count = ls.get("loop_count", 0)
        fuse = ls.get("fuse") if isinstance(ls.get("fuse"), dict) else {}
        max_rounds = fuse.get("max_rounds")

        # Enrich the event with the fuse-boundary facts the validator needs for
        # the reflect→{plan,escalate} decision. Caller-supplied values win.
        eval_event = dict(event)
        eval_event.setdefault("loop_count", loop_count)
        eval_event.setdefault("max_rounds", max_rounds)

        # ── Step 2: VALIDATE (pure). ────────────────────────────────────────
        legal, event_type = validate_transition(from_phase, to_phase, eval_event)
        if not legal:
            return TransitionResult(
                status=STATUS_ILLEGAL, unit_id=unit_id, to_phase=to_phase,
                from_phase=from_phase, from_cas_version=expected_version,
                reason=event_type,
            )

        # ── Step 3: COMPUTE (unlocked). ─────────────────────────────────────
        gate_result = event.get("gate_result")
        new_unit = _apply_side_effects(
            unit, to_phase, event, is_activation=False,
            loop_count=loop_count, max_rounds=max_rounds,
            gate_result=gate_result,
        )
        if callable(side_effects):
            try:
                new_unit = side_effects(new_unit, event)
            except Exception as exc:  # fail-closed: a side-effect error aborts.
                return TransitionResult(
                    status=STATUS_ERROR, unit_id=unit_id, to_phase=to_phase,
                    from_phase=from_phase, from_cas_version=expected_version,
                    reason="side_effects callback raised: {0}: {1}".format(
                        type(exc).__name__, exc),
                )
            if not isinstance(new_unit, dict):
                return TransitionResult(
                    status=STATUS_ERROR, unit_id=unit_id, to_phase=to_phase,
                    from_phase=from_phase, from_cas_version=expected_version,
                    reason="side_effects callback did not return a dict",
                )
        new_unit_cas = expected_version + 1
        _loop_state_of(new_unit)["cas_version"] = new_unit_cas

        # Build the new payload (replace this unit in-place, preserve order).
        new_payload = dict(payload)
        new_units = []
        for u in payload.get("flow_units", []):
            if isinstance(u, dict) and u.get("flow_unit_id") == unit_id:
                new_units.append(new_unit)
            else:
                new_units.append(u)
        new_payload["flow_units"] = new_units
        new_bytes = _serialize(new_payload)

        # ── Step 4: WRITE — atomic, lock-guarded CAS critical section. ──────
        # The lock is held ONLY across re-read-check-replace. The compute above
        # ran unlocked, so two writers that both read version V reach here
        # concurrently; the lock serializes them so exactly one commits V+1 and
        # the other observes the bumped version → CONFLICT (no lost updates).
        with lock:
            on_disk = _load_runtime(runtime_path)
            if not isinstance(on_disk, dict):
                return TransitionResult(
                    status=STATUS_ERROR, unit_id=unit_id, to_phase=to_phase,
                    from_phase=from_phase, from_cas_version=expected_version,
                    reason="runtime file became unreadable before commit",
                )
            on_disk_unit = _find_unit(on_disk, unit_id)
            if on_disk_unit is None:
                return TransitionResult(
                    status=STATUS_ERROR, unit_id=unit_id, to_phase=to_phase,
                    from_phase=from_phase, from_cas_version=expected_version,
                    reason="flow_unit_id {0!r} disappeared before commit".format(unit_id),
                )
            on_disk_version = _cas_version_of(on_disk_unit)
            if on_disk_version != expected_version:
                # CONFLICT: another writer committed a transition for this unit
                # between our read and our write. Fail-closed (or retry).
                if attempt <= max_retries:
                    continue  # re-read fresh state and retry the whole cycle.
                return TransitionResult(
                    status=STATUS_CONFLICT, unit_id=unit_id, to_phase=to_phase,
                    from_phase=from_phase, from_cas_version=expected_version,
                    reason=(
                        "CAS conflict: on-disk cas_version={0} != expected={1} "
                        "(another writer advanced this unit)".format(
                            on_disk_version, expected_version)
                    ),
                )
            _atomic_replace_bytes(runtime_path, new_bytes)

        return TransitionResult(
            status=STATUS_SUCCESS, unit_id=unit_id, to_phase=to_phase,
            from_phase=from_phase, from_cas_version=expected_version,
            new_cas_version=new_unit_cas, event_type=event_type,
            reason="transition committed", unit=new_unit,
        )


# ═══════════════════════════════════════════════════════════════════════════
# Activation — the (entry)→plan transition (cas_version = 0)
# ═══════════════════════════════════════════════════════════════════════════


def activate_unit(unit_id, *, runtime_file, tier, fuse_max_rounds,
                  side_effects=None, max_retries=0):
    """Activate a dormant flow unit: the ``(entry) → plan`` transition.

    Sets ``agent_phase = plan``, ``loop_count = 0``, ``fuse.tripped = false``,
    ``active_loop = true``, ``active_loop_tier = tier``, ``runtime_status =
    active``, ``fuse.max_rounds = fuse_max_rounds``, and assigns the INITIAL
    ``cas_version = 0`` (the §3.3 "0 at activation" rule). This is the only
    transition that writes cas_version = 0; every subsequent transition via
    :func:`apply_transition` increments it.

    The conflict check for activation compares against the unit's PRE-activation
    state (no cas_version / dormant): if another writer already activated this
    unit (cas_version present on disk), the writer returns STATUS_CONFLICT and
    does not double-activate.

    Args:
        unit_id: The dormant flow_unit_id to activate.
        runtime_file: Path to ``flow-unit-runtime.json``.
        tier: Loop tier (``setup|inner|middle|outer``) — written to
            ``active_loop_tier``.
        fuse_max_rounds: Integer written to ``fuse.max_rounds``.
        side_effects: Optional ``(new_unit, event) -> new_unit`` callable.
        max_retries: CAS retry budget on conflict (default 0).

    Returns:
        TransitionResult (status SUCCESS / CONFLICT / ERROR). On success
        ``new_cas_version`` is 0.
    """
    runtime_path = Path(runtime_file) if not isinstance(runtime_file, Path) else runtime_file
    path_str = str(runtime_path.resolve() if runtime_path.exists() else runtime_path)
    lock = _file_lock(path_str)

    attempt = 0
    while True:
        attempt += 1
        payload = _load_runtime(runtime_path)
        if not isinstance(payload, dict):
            return TransitionResult(
                status=STATUS_ERROR, unit_id=unit_id, to_phase=PLAN,
                reason="runtime file missing or corrupt: {0}".format(runtime_path),
            )
        unit = _find_unit(payload, unit_id)
        if unit is None:
            return TransitionResult(
                status=STATUS_ERROR, unit_id=unit_id, to_phase=PLAN,
                reason="flow_unit_id {0!r} not found in runtime file".format(unit_id),
            )

        existing_cas = _cas_version_of(unit)
        if existing_cas is not None:
            # Already activated. This is a conflict (cannot activate twice).
            if attempt <= max_retries:
                # The unit is already activated; retrying cannot un-activate it.
                # Fail-closed immediately rather than spin.
                pass
            return TransitionResult(
                status=STATUS_CONFLICT, unit_id=unit_id, to_phase=PLAN,
                from_cas_version=existing_cas,
                reason=(
                    "unit {0!r} already activated (cas_version={1}); cannot "
                    "re-activate".format(unit_id, existing_cas)
                ),
            )

        # Compute the activated unit (canonical §3.2 side effects for entry→plan).
        new_unit = dict(unit)
        ls = dict(_loop_state_of(unit))
        fuse = dict(ls.get("fuse") if isinstance(ls.get("fuse"), dict) else {})
        gs = dict(_gate_state_of(unit))
        new_unit["loop_state"] = ls
        new_unit["gate_state"] = gs
        ls["fuse"] = fuse
        ls["agent_phase"] = PLAN
        ls["loop_count"] = 0
        ls["active_loop"] = True
        ls["active_loop_tier"] = tier
        fuse["tripped"] = False
        fuse["max_rounds"] = fuse_max_rounds
        new_unit["runtime_status"] = "active"
        # cas_version = 0 at activation (§3.3).
        ls["cas_version"] = 0

        if callable(side_effects):
            try:
                new_unit = side_effects(new_unit, {"event": "phase_enter"})
            except Exception as exc:
                return TransitionResult(
                    status=STATUS_ERROR, unit_id=unit_id, to_phase=PLAN,
                    reason="side_effects callback raised: {0}: {1}".format(
                        type(exc).__name__, exc),
                )
            if not isinstance(new_unit, dict):
                return TransitionResult(
                    status=STATUS_ERROR, unit_id=unit_id, to_phase=PLAN,
                    reason="side_effects callback did not return a dict",
                )
            _loop_state_of(new_unit)["cas_version"] = 0  # enforce the invariant

        new_payload = dict(payload)
        new_units = []
        for u in payload.get("flow_units", []):
            if isinstance(u, dict) and u.get("flow_unit_id") == unit_id:
                new_units.append(new_unit)
            else:
                new_units.append(u)
        new_payload["flow_units"] = new_units
        new_bytes = _serialize(new_payload)

        with lock:
            on_disk = _load_runtime(runtime_path)
            if not isinstance(on_disk, dict):
                return TransitionResult(
                    status=STATUS_ERROR, unit_id=unit_id, to_phase=PLAN,
                    reason="runtime file became unreadable before commit",
                )
            on_disk_unit = _find_unit(on_disk, unit_id)
            if on_disk_unit is None:
                return TransitionResult(
                    status=STATUS_ERROR, unit_id=unit_id, to_phase=PLAN,
                    reason="flow_unit_id {0!r} disappeared before commit".format(unit_id),
                )
            on_disk_cas = _cas_version_of(on_disk_unit)
            if on_disk_cas is not None:
                # Another writer activated this unit between our read and write.
                if attempt <= max_retries:
                    continue
                return TransitionResult(
                    status=STATUS_CONFLICT, unit_id=unit_id, to_phase=PLAN,
                    from_cas_version=on_disk_cas,
                    reason=(
                        "CAS conflict on activation: on-disk cas_version={0} "
                        "(another writer activated this unit first)".format(on_disk_cas)
                    ),
                )
            _atomic_replace_bytes(runtime_path, new_bytes)

        return TransitionResult(
            status=STATUS_SUCCESS, unit_id=unit_id, to_phase=PLAN,
            from_phase=None, from_cas_version=None, new_cas_version=0,
            event_type="phase_enter", reason="unit activated", unit=new_unit,
        )


# ═══════════════════════════════════════════════════════════════════════════
# Restart recovery (ADR-014 §3.5)
# ═══════════════════════════════════════════════════════════════════════════


def _recovered_state_for(unit):
    """Extract the recovered-state view dict for one unit (active or otherwise)."""
    ls = _loop_state_of(unit)
    gs = _gate_state_of(unit)
    fuse = ls.get("fuse") if isinstance(ls.get("fuse"), dict) else {}
    return {
        "flow_unit_id": unit.get("flow_unit_id"),
        "runtime_status": unit.get("runtime_status"),
        "agent_phase": ls.get("agent_phase"),
        "loop_count": ls.get("loop_count"),
        "active_loop_tier": ls.get("active_loop_tier"),
        "max_rounds": fuse.get("max_rounds"),
        "fuse_tripped": bool(fuse.get("tripped", False)),
        "cas_version": _cas_version_of(unit),
        "last_gate_result": ls.get("last_gate_result"),
        "gate_status": gs.get("status"),
    }


def recover_state(runtime_file, event_log=None):
    """Recover the PARO state map after a process restart (ADR-014 §3.5).

    Restart recovery is **read-based, not replay-based**: the current-state file
    IS the recovered state. For each ``active`` unit, ``agent_phase``,
    ``loop_count``, ``fuse``, and ``cas_version`` are read directly. No event
    replay is performed.

    When ``event_log`` is supplied (the FEAT-007 hook), consistency is verified:

      - **On-disk ahead of log** (a state write committed but the event append
        was lost — the defensive case): the state file is trusted and a
        synthetic ``phase_recovery`` event is recorded in
        :attr:`RecoveryResult.synthetic_events` for FEAT-007 to append.
      - **Log ahead of on-disk** (a state write was lost — the DANGEROUS case):
        the unit is fail-closed to ``runtime_status = blocked`` with a
        ``recovery_conflict`` classification. The engine does NOT silently
        replay, because replaying a transition whose side effects (e.g. an
        external action) may have partially occurred is unsafe.

    When ``event_log`` is None (the only value FEAT-005 passes — the event log
    is FEAT-007), the consistency check is SKIPPED per §3.5 ("state file alone
    is sufficient"). FEAT-005's recovery is complete without the log.

    Args:
        runtime_file: Path to ``flow-unit-runtime.json``.
        event_log: Optional event log. Accepts:
            - None (skip consistency check — FEAT-005 default);
            - a list of event dicts (each carrying ``unit_id`` and
              ``cas_version``);
            - a path (str/Path) to a JSONL event log file (one event per line).

    Returns:
        RecoveryResult. ``runtime_found`` is False when the file is
        missing/corrupt. Never raises.
    """
    runtime_path = Path(runtime_file) if not isinstance(runtime_file, Path) else runtime_file
    payload = _load_runtime(runtime_path)
    if not isinstance(payload, dict):
        return RecoveryResult(
            runtime_found=False,
            issues=["runtime file missing or corrupt: {0}".format(runtime_path)],
        )

    flow_units = payload.get("flow_units")
    if not isinstance(flow_units, list):
        return RecoveryResult(
            runtime_found=True,
            issues=["runtime payload has no flow_units list"],
        )

    # Build the recovered state map for every unit (active units carry full
    # PARO state; dormant/withdrawn units are included for visibility but have
    # no active phase/cas_version to recover).
    state_map = {}
    for unit in flow_units:
        if not isinstance(unit, dict):
            continue
        uid = unit.get("flow_unit_id")
        if not isinstance(uid, str):
            continue
        state_map[uid] = _recovered_state_for(unit)

    result = RecoveryResult(runtime_found=True, units=state_map)

    # ── Event-log consistency hook (FEAT-007). ──────────────────────────────
    # FEAT-005 passes event_log=None, so this branch is not exercised in
    # FEAT-005 tests except the no-log path. The logic is here so FEAT-007 can
    # drop in a real log without changing this function's signature.
    events_by_unit = _load_event_log(event_log) if event_log is not None else None
    if events_by_unit is not None:
        for uid, state in state_map.items():
            on_disk_cas = state.get("cas_version")
            log_events = events_by_unit.get(uid, [])
            last_log_cas = None
            for ev in log_events:
                cv = ev.get("cas_version") if isinstance(ev, dict) else None
                if _is_int(cv):
                    last_log_cas = cv
            if on_disk_cas is None and last_log_cas is None:
                continue  # dormant unit, nothing to verify.
            if last_log_cas is None:
                # State ahead of (empty) log: trust state, synthesize recovery.
                result.synthetic_events.append({
                    "unit_id": uid,
                    "event_type": "phase_recovery",
                    "cas_version": on_disk_cas,
                    "reason": "on-disk state ahead of event log",
                })
                continue
            if on_disk_cas is None:
                # Log ahead of state (state write lost) but unit is dormant —
                # not the dangerous case; trust the dormant state.
                continue
            if last_log_cas > on_disk_cas:
                # The DANGEROUS case: log is ahead of on-disk state. Fail-close
                # this unit to blocked; do NOT silently replay.
                state["recovery_status"] = RECOVERY_CONFLICT
                state["runtime_status"] = "blocked"
                result.conflicts.append(uid)
            elif last_log_cas < on_disk_cas:
                # State ahead of log: trust state, synthesize recovery event.
                result.synthetic_events.append({
                    "unit_id": uid,
                    "event_type": "phase_recovery",
                    "cas_version": on_disk_cas,
                    "reason": "on-disk state ahead of event log",
                })

    return result


def _load_event_log(event_log):
    """Normalize an event_log argument to ``{unit_id: [events]}``.

    Accepts a list of event dicts or a path to a JSONL file. Returns None if
    the argument is None (skip consistency check). Never raises.
    """
    events = []
    if isinstance(event_log, (list, tuple)):
        events = [e for e in event_log if isinstance(e, dict)]
    elif isinstance(event_log, (str, Path)):
        try:
            path = Path(event_log)
            if path.is_file():
                for line in path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            events = []
    else:
        return None
    by_unit = {}
    for ev in events:
        uid = ev.get("unit_id") if isinstance(ev, dict) else None
        if isinstance(uid, str):
            by_unit.setdefault(uid, []).append(ev)
    return by_unit


# ═══════════════════════════════════════════════════════════════════════════
# Convenience: drive a unit through the full forward chain (test/CLI helper)
# ═══════════════════════════════════════════════════════════════════════════


def forward_chain_events():
    """Return the list of ``(from, to, event)`` for one plan→act→observe→reflect pass.

    A small convenience for tests and (future) CLI smoke runs: the four forward
    transitions with minimal legal events. The reflect→{exit,plan,escalate}
    branch is NOT included (it requires a gate result + fuse facts the caller
    must supply).
    """
    return [
        (PLAN, ACT, {"reason": "plan accepted"}),
        (ACT, OBSERVE, {"reason": "action complete"}),
        (OBSERVE, REFLECT, {"reason": "review recorded", "gate_result": "NEEDS_CHANGE"}),
    ]


__all__ = [
    "PLAN", "ACT", "OBSERVE", "REFLECT", "EXIT", "ESCALATE", "WITHDRAWN",
    "STATUS_SUCCESS", "STATUS_CONFLICT", "STATUS_ILLEGAL", "STATUS_ERROR",
    "RECOVERY_OK", "RECOVERY_CONFLICT",
    "validate_transition",
    "apply_transition",
    "activate_unit",
    "recover_state",
    "TransitionResult",
    "RecoveryResult",
    "forward_chain_events",
]


if __name__ == "__main__":  # pragma: no cover - manual smoke
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    # Tiny self-test of the pure validator (no I/O).
    cases = [
        (None, PLAN, {}),
        (PLAN, ACT, {}),
        (ACT, OBSERVE, {}),
        (OBSERVE, REFLECT, {}),
        (REFLECT, PLAN, {"gate_result": "NEEDS_CHANGE", "loop_count": 1, "max_rounds": 3}),
        (REFLECT, ESCALATE, {"gate_result": "NEEDS_CHANGE", "loop_count": 6, "max_rounds": 5}),
        (REFLECT, EXIT, {"gate_result": "APPROVED"}),
        (PLAN, WITHDRAWN, {}),
        # illegal:
        (PLAN, OBSERVE, {}),
        (ACT, PLAN, {}),
    ]
    for frm, to, ev in cases:
        legal, reason = validate_transition(frm, to, ev)
        print("{0!r:>10} -> {1!r:<10} : {2:<5} {3}".format(frm, to, legal, reason))
