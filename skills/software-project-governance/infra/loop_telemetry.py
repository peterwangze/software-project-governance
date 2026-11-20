"""Report observed unit completions, rework and waits from the loop event log."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta


SCOPE_NOTE = "Observed work-unit events from .governance/loop-event-log.jsonl."


@dataclass(frozen=True)
class MetricValue:
    status: str
    value: int | float | None
    unit: str
    sample_size: int
    reason: str = ""
    percentiles: dict = field(default_factory=dict)


@dataclass(frozen=True)
class MetricsReport:
    window: str
    computed_at: str | None
    flow: dict
    units_considered: int
    event_count: int
    diagnostics: dict
    observations: list
    scope_note: str = SCOPE_NOTE


_TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _parse_ts(timestamp):
    """Parse an ISO-8601 UTC timestamp (``...Z``) → ``datetime``; ``None`` on malformed.

    Mirrors ``loop_event_log.now_timestamp()``'s format. Returns ``None`` for
    anything that is not a parseable ``%Y-%m-%dT%H:%M:%SZ`` string so the
    caller can count it as a malformed-timestamp skip (ADR-015 §5.2).
    """
    if not isinstance(timestamp, str):
        return None
    try:
        return datetime.strptime(timestamp, _TS_FORMAT)
    except ValueError:
        return None


def _window_label(window):
    """Return the canonical label string for a window value."""
    if window is None:
        return "all"
    if isinstance(window, tuple):
        return "{0}..{1}".format(window[0], window[1])
    return str(window)


def _filter_window(events, window):
    """Filter ``events`` to those within ``window`` (ADR-015 §5).

    - ``window=None`` → all events (all-time).
    - ``window="7d"``/``"30d"``/``"90d"`` (trailing) → events whose timestamp is
      within the trailing N days relative to the LATEST event timestamp in the
      input. Relative-to-latest keeps the computation deterministic (a fixed
      fixture yields the same window regardless of when the test runs). Note:
      windowing is applied to events with parseable timestamps only; events
      with malformed timestamps are excluded upstream by the caller's malformed
      accounting — but to be safe, this function also drops them silently from
      windowing (they have no parseable timestamp to compare).
    - ``window=(start_iso, end_iso)`` → explicit ``[start, end)`` window on the
      date portion (start inclusive, end exclusive), parsed as dates.

    Returns ``(kept, latest_ts)`` where ``latest_ts`` is the latest parseable
    timestamp among the kept events (a ``datetime`` or ``None`` when empty).
    Never raises.
    """
    # First, parse timestamps and find the latest (the windowing anchor).
    parsed = []
    latest = None
    for ev in events:
        if not isinstance(ev, dict):
            continue
        ts = _parse_ts(ev.get("timestamp"))
        if ts is None:
            continue  # malformed — counted in diagnostics, dropped from windowing
        parsed.append((ev, ts))
        if latest is None or ts > latest:
            latest = ts

    if window is None:
        kept = [ev for ev, _ in parsed]
        return kept, latest

    # Trailing-N-days window relative to the latest event timestamp.
    if isinstance(window, str):
        m = _match_trailing(window)
        if m is not None:
            if latest is None:
                return [], None
            cutoff = latest - timedelta(days=m)
            kept = [ev for ev, ts in parsed if ts >= cutoff]
            return kept, latest
        # Unknown string window → treat as all (defensive; never raises).
        kept = [ev for ev, _ in parsed]
        return kept, latest

    # Explicit (start_iso, end_iso) tuple → [start, end) on date granularity.
    if isinstance(window, (tuple, list)) and len(window) == 2:
        start_d = _parse_date(window[0])
        end_d = _parse_date(window[1])
        if start_d is None or end_d is None:
            kept = [ev for ev, _ in parsed]
            return kept, latest
        kept = []
        for ev, ts in parsed:
            d = ts.date()
            if start_d <= d < end_d:
                kept.append(ev)
        return kept, max((_parse_ts(ev["timestamp"]) for ev in kept), default=None)

    # Fallback: anything else → all events.
    kept = [ev for ev, _ in parsed]
    return kept, latest


def _match_trailing(window):
    """Return the integer day-count for a trailing window like ``"7d"``/``"30d"``.

    Returns ``None`` when the string is not a trailing-days window.
    """
    if not isinstance(window, str) or not window:
        return None
    if not window.endswith("d"):
        return None
    body = window[:-1]
    if body in ("", "+", "-"):
        return None
    try:
        return int(body)
    except ValueError:
        return None


def _parse_date(value):
    """Parse a ``YYYY-MM-DD`` date string → ``date``; ``None`` on malformed."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _sort_key(ev):
    """Sort key mirroring ``loop_event_log._events_in_order``: (timestamp, cas_version)."""
    ts = ev.get("timestamp") or ""
    cv = ev.get("cas_version")
    cv = cv if isinstance(cv, int) and not isinstance(cv, bool) else -1
    return (ts, cv)


def _by_unit(events):
    """Group ``events`` by ``unit_id`` and sort each group by (ts, cas_version).

    Returns ``dict[unit_id, list[event]]``. Events lacking a ``unit_id`` are
    grouped under ``""`` (rare; defensive — they are not useful for per-unit
    metrics but keep totals honest). Each group is a NEW list (the caller's
    events are not mutated).
    """
    groups = {}
    for ev in events:
        if not isinstance(ev, dict):
            continue
        uid = ev.get("unit_id")
        uid = uid if isinstance(uid, str) else ""
        groups.setdefault(uid, []).append(ev)
    for uid in groups:
        groups[uid] = sorted(groups[uid], key=_sort_key)
    return groups


def _median(values):
    """Median of a non-empty numeric list (float)."""
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return float(s[mid])
    return (float(s[mid - 1]) + float(s[mid])) / 2.0


def _percentile(values, pct):
    """Linear-interpolation percentile of a non-empty numeric list.

    ``pct`` in [0, 100]. Returns a float. Uses the "N-1" interpolation that
    matches numpy's default ('linear'): for n samples, the p-th percentile is
    interpolated between the two nearest order statistics.
    """
    s = sorted(values)
    n = len(s)
    if n == 1:
        return float(s[0])
    if pct <= 0:
        return float(s[0])
    if pct >= 100:
        return float(s[-1])
    # Linear interpolation between closest ranks.
    rank = (pct / 100.0) * (n - 1)
    lo = int(rank)
    hi = min(lo + 1, n - 1)
    frac = rank - lo
    return float(s[lo]) + (float(s[hi]) - float(s[lo])) * frac


def _cycle_times_for_unit(unit_events):
    """Yield one cycle-time sample (seconds) per completed iteration.

    A cycle = one round trip from a round-start event (``phase_enter`` OR
    ``back_edge``) to the next round-end event (``loop_exit`` OR the next
    ``back_edge``). ``phase_enter`` starts the FIRST round; each ``back_edge``
    both ends the previous round and starts the next; ``loop_exit`` ends the
    final round. Events whose timestamps are unparseable are skipped (no
    sample); they are counted in diagnostics by the caller.
    """
    round_start_ts = None
    for ev in unit_events:
        et = ev.get("event_type")
        ts = _parse_ts(ev.get("timestamp"))
        if ts is None:
            continue
        if et == "phase_enter":
            round_start_ts = ts
        elif et == "back_edge":
            if round_start_ts is not None:
                dur = (ts - round_start_ts).total_seconds()
                if dur >= 0:
                    yield dur
            # the back_edge also starts the NEXT round.
            round_start_ts = ts
        elif et == "loop_exit":
            if round_start_ts is not None:
                dur = (ts - round_start_ts).total_seconds()
                if dur >= 0:
                    yield dur
            round_start_ts = None



def _count(value, sample_size):
    if not sample_size:
        return MetricValue("unknown", None, "count", 0, "no unit events in window")
    return MetricValue("measured", value, "count", sample_size)


def _duration(samples, missing_reason):
    if not samples:
        return MetricValue("unknown", None, "seconds", 0, missing_reason)
    return MetricValue("measured", _median(samples), "seconds", len(samples),
                       percentiles={"p90": _percentile(samples, 90)})


def compute_metrics(events, *, window=None):
    """Describe events inside the window. Durations require both recorded endpoints."""
    records = [ev for ev in events if isinstance(ev, dict)]
    kept, latest = _filter_window(records, window)
    by_unit = _by_unit(kept)
    by_unit.pop("", None)
    cycles, leads, waits = [], [], []
    closures = set()
    rework_count = 0
    observations = []
    for uid, history in by_unit.items():
        cycles.extend(_cycle_times_for_unit(history))
        first_enter = None
        waiting = None
        for ev in history:
            kind = ev.get("event_type")
            ts = _parse_ts(ev["timestamp"])
            observation = {"unit_id": uid, "event_type": kind, "event_id": ev.get("event_id"),
                           "timestamp": ev["timestamp"],
                           "evidence_ref": ev.get("evidence_ref")}
            if kind == "phase_enter" and ev.get("from_version") is None and first_enter is None:
                first_enter = ts
            if kind in ("unit_blocked", "fuse_trip"):
                if waiting is None:
                    waiting = {**observation, "resolved_at": None, "wait_seconds": None}
                    observations.append(waiting)
            elif kind in ("phase_enter", "escalation_resolved", "unit_withdrawn") and waiting is not None:
                elapsed = (ts - _parse_ts(waiting["timestamp"])).total_seconds()
                waiting.update(resolved_at=ev["timestamp"], wait_seconds=elapsed,
                               resolution_id=ev.get("event_id"),
                               resolution_event=kind, resolution_ref=ev.get("evidence_ref"))
                waits.append(elapsed)
                waiting = None
            if kind == "back_edge":
                rework_count += 1
                observations.append(observation)
            elif kind == "loop_exit":
                closures.add(uid)
                observations.append(observation)
                if first_enter is not None:
                    leads.append((ts - first_enter).total_seconds())
                    first_enter = None

    units = len(by_unit)
    return MetricsReport(
        window=_window_label(window),
        computed_at=latest.strftime(_TS_FORMAT) if latest is not None else None,
        flow={
            "unit_completions": _count(len(closures), units),
            "rework_events": _count(rework_count, units),
            "cycle_time": _duration(cycles, "no paired round start and end in window"),
            "lead_time": _duration(leads, "no paired unit entry and exit in window"),
            "blocked_wait_time": _duration(waits, "no paired block and resolution in window"),
        },
        units_considered=units,
        event_count=len(kept),
        diagnostics={"malformed_timestamps": sum(_parse_ts(ev.get("timestamp")) is None for ev in records)},
        observations=sorted(observations, key=lambda item: (item["timestamp"], item["unit_id"])),
    )


# The default artifact event types: a closed round counts as ARTIFACT-BEARING
# when it contains >=1 event of one of these types. Default = ``gate_result``:
# the only non-terminal substantive outcome type in the closed 14-type event
# enum (a gate judgment ON produced work). Callers may widen/narrow the set —
# it is a parameter, not a hardcode.
DEFAULT_ARTIFACT_EVENT_TYPES = frozenset({"gate_result"})

# Default heartbeat threshold N (trailing artifact-less rounds that flag a
# unit as a stall suspect). Deliberate MIRROR of
# loop_engine.HEARTBEAT_IDLE_ROUNDS_DEFAULT — duplicated, not imported, to
# preserve the telemetry-is-a-consumer, stdlib-only-import contract (ADR-015
# §6.4); the equality is pinned by a test in tests/test_loop_telemetry.py.
# Provenance: FIX-357 (~15-round stall) / FIX-359 (16 rounds) — EVD-1101①.
DEFAULT_IDLE_THRESHOLD = 3

# The no-overclaim boundary carried on every stall report (FEAT-063 aligned).
STALL_SCOPE_NOTE = (
    "Round-stall (waiting-tax) observability computed from "
    "loop-event-log.jsonl. A round is one anchor interval "
    "(phase_enter/back_edge); a CLOSED round is artifact-bearing when it "
    "contains an artifact-type event (default: gate_result). Idle streaks "
    "are ATTENTION signals for heartbeat reporting - they are NOT stop proofs "
    "(FEAT-063) and do NOT claim an execution body is dead: a silent stall "
    "(no new anchors at all) is visible only as last_anchor_ts staleness, "
    "which needs the caller's wall clock to judge. Describes what the event "
    "log records."
)

# Round anchors — the same events _cycle_times_for_unit anchors rounds on.
_STALL_ROUND_ANCHORS = frozenset({"phase_enter", "back_edge"})


@dataclass(frozen=True)
class StallReport:
    """The per-unit round-stall (waiting-tax) report (FEAT-044).

    Attributes:
        window: the window label (mirrors :class:`MetricsReport`).
        computed_at: ISO-8601 UTC — the latest parseable event timestamp in
            the windowed input (deterministic; never wall-clock).
        status: ``"measured"`` when at least one unit contributed; else
            ``"unknown"`` (with ``reason``) — never a fabricated empty truth.
        reason: empty when measured; explains the missing data when unknown.
        idle_threshold: the effective heartbeat threshold N used for
            ``suspects``.
        artifact_event_types: the effective artifact-type set (sorted tuple).
        units: ``{unit_id: {...}}`` per-unit facts — ``rounds_total``,
            ``artifact_rounds``, ``artifactless_rounds``,
            ``idle_streak_max``, ``idle_streak_trailing``,
            ``last_anchor_ts``, ``last_artifact_ts``.
        suspects: sorted unit ids whose ``idle_streak_trailing`` reached the
            threshold — heartbeat-attention candidates, NOT stop proofs.
        units_considered: distinct non-empty unit ids in the windowed set.
        events_considered: number of events in the windowed set.
        malformed_timestamps: events skipped for unparseable timestamps
            (counted pre-window, same convention as :func:`compute_metrics`).
        scope_note: the no-overclaim boundary string.
    """

    window: str
    computed_at: str | None
    status: str  # "measured" | "unknown"
    reason: str
    idle_threshold: int
    artifact_event_types: tuple
    units: dict
    suspects: tuple
    units_considered: int
    events_considered: int
    malformed_timestamps: int
    scope_note: str


def _effective_artifact_types(artifact_event_types):
    """Resolve the caller's artifact-type set (tolerant, never raises).

    ``None`` → :data:`DEFAULT_ARTIFACT_EVENT_TYPES`. A bare string is treated
    as a single type (iterating a raw string would explode it into
    characters). Any other iterable contributes its str members — an
    explicitly empty iterable is honored (nothing counts as an artifact).
    Garbage input falls back to the default.
    """
    if artifact_event_types is None:
        return DEFAULT_ARTIFACT_EVENT_TYPES
    if isinstance(artifact_event_types, str):
        return frozenset({artifact_event_types})
    try:
        members = {item for item in artifact_event_types if isinstance(item, str)}
    except TypeError:
        return DEFAULT_ARTIFACT_EVENT_TYPES
    return frozenset(members)


def _effective_idle_threshold(idle_threshold):
    """Resolve the heartbeat threshold (int >= 1; garbage → default)."""
    if isinstance(idle_threshold, int) and not isinstance(idle_threshold, bool) \
            and idle_threshold >= 1:
        return idle_threshold
    return DEFAULT_IDLE_THRESHOLD


def compute_stall_report(events, *, artifact_event_types=None,
                         idle_threshold=None, window=None):
    """PURE: measure per-unit round-stall (waiting-tax) facts (FEAT-044).

    A unit's rounds are anchored exactly like the cycle-time metric
    (:func:`_cycle_times_for_unit`): ``phase_enter`` starts the first round,
    each ``back_edge`` ends the previous round and starts the next. A CLOSED
    round (a consecutive anchor pair) is artifact-bearing when at least one
    event whose type is in ``artifact_event_types`` has a parseable timestamp
    inside ``[start, end]`` (both ends inclusive — a gate_result stamped in
    the same second as the closing anchor counts for that round). Streaks are
    counted over CLOSED rounds only; a trailing anchor with no successor is
    an OPEN round — the log alone cannot time it (purity: no wall-clock), so
    it is surfaced via ``last_anchor_ts`` for the caller to judge.

    Args:
        events: list of event dicts (as returned by
            :func:`loop_event_log.read_events`). Not read from files here.
        artifact_event_types: ``None`` → :data:`DEFAULT_ARTIFACT_EVENT_TYPES`;
            otherwise a type set (a bare string = one type). Parameterized.
        idle_threshold: heartbeat threshold N; ``None``/garbage →
            :data:`DEFAULT_IDLE_THRESHOLD` (mirrored from loop_engine).
        window: ``None`` | trailing ``"7d"/"30d"/"90d"`` | explicit
            ``(start_iso, end_iso)`` — same semantics as
            :func:`compute_metrics`.

    Returns:
        :class:`StallReport`. Never raises — malformed events are counted in
        ``malformed_timestamps`` and skipped; the same input always yields a
        structurally equal report.
    """
    events_list = [ev for ev in list(events) if isinstance(ev, dict)]

    malformed = 0
    for ev in events_list:
        if _parse_ts(ev.get("timestamp")) is None:
            malformed += 1

    kept, latest = _filter_window(events_list, window)
    window_lbl = _window_label(window)
    types = _effective_artifact_types(artifact_event_types)
    threshold = _effective_idle_threshold(idle_threshold)

    by_unit = _by_unit(kept)
    units = {}
    suspects = []
    unit_count = 0
    for uid, evs in by_unit.items():
        if not uid:
            continue
        unit_count += 1
        anchors = []
        artifact_ts = []
        for ev in evs:
            et = ev.get("event_type")
            ts = _parse_ts(ev.get("timestamp"))
            if ts is None:
                continue
            if et in _STALL_ROUND_ANCHORS:
                anchors.append(ts)
            if et in types:
                artifact_ts.append(ts)
        rounds_total = 0
        artifact_rounds = 0
        streak_running = 0
        streak_max = 0
        for i in range(1, len(anchors)):
            start = anchors[i - 1]
            end = anchors[i]
            rounds_total += 1
            bearing = any(start <= a <= end for a in artifact_ts)
            if bearing:
                artifact_rounds += 1
                streak_running = 0
            else:
                streak_running += 1
                if streak_running > streak_max:
                    streak_max = streak_running
        units[uid] = {
            "rounds_total": rounds_total,
            "artifact_rounds": artifact_rounds,
            "artifactless_rounds": rounds_total - artifact_rounds,
            "idle_streak_max": streak_max,
            "idle_streak_trailing": streak_running,
            "last_anchor_ts": (
                anchors[-1].strftime(_TS_FORMAT) if anchors else None
            ),
            "last_artifact_ts": (
                max(artifact_ts).strftime(_TS_FORMAT) if artifact_ts else None
            ),
        }
        if streak_running >= threshold:
            suspects.append(uid)

    if unit_count >= 1:
        status = "measured"
        reason = ""
    else:
        status = "unknown"
        reason = "no units with events in window"

    computed_at = (
        latest.strftime(_TS_FORMAT) if latest is not None
        else None
    )

    return StallReport(
        window=window_lbl,
        computed_at=computed_at,
        status=status,
        reason=reason,
        idle_threshold=threshold,
        artifact_event_types=tuple(sorted(types)),
        units=units,
        suspects=tuple(sorted(suspects)),
        units_considered=unit_count,
        events_considered=len(kept),
        malformed_timestamps=malformed,
        scope_note=STALL_SCOPE_NOTE,
    )
