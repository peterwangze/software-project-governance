#!/usr/bin/env python3
"""Production telemetry — honest flow/DORA metrics from the loop event log.

FEAT-008 (ADR-015, 0.69.0). Product code, authorized by Design Review
APPROVED_WITH_NOTES/0.

This module is the **honest telemetry layer** for the Loop Engine: it computes
flow metrics (cycle time, lead time, iteration-count distribution, back-edge
frequency) and DORA-style metrics (deployment/unit-completion frequency, lead
time for changes, change failure rate, time to restore/escalate) **purely from
the 0.68.0 event log** (``loop-event-log.jsonl`` as read by
:func:`loop_event_log.read_events`).

The single load-bearing property (AUDIT-133 / EVD-707): **every metric is
either a real number measured from defined events, or ``unknown`` with a reason
— never a proxy, never a fabricated zero.** Concretely:

  - Zero completed units → ``status="unknown"`` (NOT ``0``).
  - Unresolved fuse trips → reported as an ``open_fuse_trips`` count (NOT
    imputed as MTTR=0).
  - Deployment frequency counts ``loop_exit`` (unit completion), NOT release
    passes — and is labeled "unit-completion frequency" so it is not mistaken
    for whole-project release cadence.
  - Change failure rate's denominator is **completed units**, NOT total loops
    (the ``fuse_trips/total_loops`` proxy is the exact substitution
    ``loop_health._compute_dora_metrics`` performs and this module replaces).

**Purity (load-bearing, ADR-015 §6.2):** :func:`compute_metrics` is a pure
function — no file I/O, no ``datetime.now()``, no module-level mutable state.
The only time reference is the events' own timestamps; windowing is relative to
the *latest event timestamp* in the input, so a fixed event fixture always
yields the same report regardless of when the test runs. The CLI wrapper
(``cmd_loop_telemetry`` in verify_workflow.py) is the only place that reads the
file; this module is input→output.

Scope (no overclaim): the metrics describe the loop unit lifecycle only (a
unit's path from phase_enter to loop_exit or unit_withdrawn). They are not a
whole-software-project DORA report and do not claim the loop engine is
production-ready. RISK-037/RISK-042 remain open (external validation is
VAL-008/009).

This module imports only stdlib at module top level. It depends on
``loop_event_log`` solely for the *event shape* (it never calls its functions in
the pure path). It does NOT import ``loop_paro_engine`` /
``loop_gate_processor`` (ADR-015 §6.4) — telemetry is a *consumer* of the event
log, not a peer of the engine.

Usage::

    from loop_event_log import read_events
    from loop_telemetry import compute_metrics
    events = read_events(log_path=path)
    report = compute_metrics(events, window="30d")
    for name, mv in report.dora.items():
        print(name, mv.status, mv.value, mv.reason)
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta


__version__ = "0.69.0"

# The no-overclaim boundary carried on every report (ADR-015 §6.1 scope_note).
SCOPE_NOTE = (
    "Loop-unit-lifecycle metrics computed from loop-event-log.jsonl. "
    "Deployment frequency = unit-completion (loop_exit) count, NOT software-"
    "project release cadence. Change failure rate is over completed units, not "
    "total loops. Metrics describe what the event log records; they do NOT "
    "claim the loop engine is production-ready or that these are whole-project "
    "DORA numbers. RISK-037/042 remain open."
)

# Phases a unit can be "in" mid-loop (the forward chain). Used only to interpret
# the round-start/round-end anchors for cycle-time; never re-derived from the
# registry (telemetry reads event payloads only).
_FORWARD_PHASES = frozenset({"plan", "act", "observe", "reflect"})

# Terminal event types — the unit has left the active forward chain. The LAST
# terminal event in a unit's history decides its classification (ADR-015 §4.3 /
# Design Review P1-2).
_TERMINAL_EVENTS = ("loop_exit", "fuse_trip", "unit_withdrawn")
_SUCCESS_TERMINAL = "loop_exit"
_FAILURE_TERMINALS = ("fuse_trip", "unit_withdrawn")


# ═══════════════════════════════════════════════════════════════════════════
# Public dataclasses (frozen — pure values)
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class MetricValue:
    """One metric's result. Carries its own honesty status.

    ``status="unknown"`` is structurally distinct from a measured ``0``: the
    JSON shape is ``{"status":"unknown","value":null}`` vs
    ``{"status":"measured","value":0.0}``. A reader MUST check ``status``
    before interpreting ``value`` (ADR-015 §9.5 risk 2).

    Attributes:
        name: the metric identifier (e.g. ``"lead_time_for_changes"``).
        status: ``"measured"`` when a real number was computed from sufficient
            events; ``"unknown"`` when the data was insufficient.
        value: the numeric value when measured (a float, int, or for some
            distributions a dict of summary stats); ``None`` when unknown.
        unit: the unit of measurement (``"seconds"``, ``"count"``,
            ``"ratio"``, ``"per_unit_per_window"``).
        sample_size: how many events/units contributed to the value. Carried
            alongside the value so a reader can judge its weight.
        reason: empty when measured; a short human-readable string explaining
            *what data was missing* when unknown.
        window: the window label this value was computed over (mirrors the
            report's window).
        percentiles: optional distribution summary (``{"median":..,"p90":..}``)
            where applicable. Empty when the metric is not a distribution.
    """

    name: str
    status: str  # "measured" | "unknown"
    value: object = None
    unit: str = ""
    sample_size: int = 0
    reason: str = ""
    window: str = None
    percentiles: dict = field(default_factory=dict)


@dataclass(frozen=True)
class MetricsReport:
    """The full telemetry report over a (windowed) event set.

    Attributes:
        window: the window label (``"all"`` / ``"7d"`` / ``"30d"`` /
            ``"2026-07-01..2026-07-23"`` for an explicit range).
        computed_at: ISO-8601 UTC — the latest event timestamp in the windowed
            input (NOT ``datetime.now()``; this keeps the report deterministic).
        flow: ``{metric_name: MetricValue}`` for the 4 flow metrics.
        dora: ``{metric_name: MetricValue}`` for the 4 DORA-style metrics.
        units_considered: distinct ``unit_id`` values in the windowed events.
        event_count: number of events in the windowed set (after windowing +
            malformed-timestamp skipping).
        diagnostics: ``{"malformed_timestamps": n,
                        "open_fuse_trips": n,
                        "window": ...}`` — counts that help a reader judge
            data quality but are NOT metrics themselves.
        scope_note: the no-overclaim boundary string (ADR-015 §6.1).
    """

    window: str
    computed_at: str
    flow: dict
    dora: dict
    units_considered: int
    event_count: int
    diagnostics: dict
    scope_note: str


# Backwards-compatible aliases the ADR §6.1 sketch uses (flow_metrics /
# dora_metrics / generated_at). Kept as attribute-friendly aliases — the frozen
# dataclass fields above are the authoritative names; these are convenience
# accessors for callers that read the ADR's naming.
def _report_flow_metrics(self):
    return self.flow


def _report_dora_metrics(self):
    return self.dora


MetricsReport.flow_metrics = property(_report_flow_metrics)  # type: ignore[attr-defined]
MetricsReport.dora_metrics = property(_report_dora_metrics)  # type: ignore[attr-defined]
MetricsReport.generated_at = property(lambda self: self.computed_at)  # type: ignore[attr-defined]


__all__ = [
    "MetricValue",
    "MetricsReport",
    "compute_metrics",
    "SCOPE_NOTE",
]


# ═══════════════════════════════════════════════════════════════════════════
# Pure helpers — no I/O, no module state, no datetime.now()
# ═══════════════════════════════════════════════════════════════════════════


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
        return kept, latest

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


def _dist(values):
    """Return a distribution summary dict for a non-empty numeric list."""
    s = sorted(values)
    n = len(s)
    mean = sum(float(v) for v in s) / n
    return {
        "median": _median(s),
        "p90": _percentile(s, 90),
        "mean": mean,
        "min": float(s[0]),
        "max": float(s[-1]),
        "sample_size": n,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Flow metric helpers — each returns a MetricValue with its own status/reason
# ═══════════════════════════════════════════════════════════════════════════


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


def _cycle_time_metric(by_unit, window):
    """Flow metric: cycle time — median per-iteration duration (seconds)."""
    samples = []
    for uid, evs in by_unit.items():
        if not uid:
            continue
        for dur in _cycle_times_for_unit(evs):
            samples.append(dur)
    if not samples:
        return MetricValue(
            name="cycle_time", status="unknown", value=None, unit="seconds",
            sample_size=0, window=window,
            reason="no completed iterations with parseable round-start/round-end "
                   "timestamps in window",
        )
    dist = _dist(samples)
    return MetricValue(
        name="cycle_time", status="measured", value=dist["median"],
        unit="seconds", sample_size=len(samples), window=window,
        percentiles={"median": dist["median"], "p90": dist["p90"]},
    )


def _lead_time_flow_metric(by_unit, window):
    """Flow metric: lead time — first phase_enter → loop_exit per exited unit.

    Note this is distinct from the DORA "lead time for changes" — the flow
    lead time reports a single median; the DORA metric reports median+p90. Both
    are anchored on the same per-unit pairs but exposed under separate names so
    a reader can distinguish the flow signal from the DORA signal (ADR-015
    §3.2).
    """
    samples = []
    for uid, evs in by_unit.items():
        if not uid:
            continue
        first_enter = None
        exit_ts = None
        for ev in evs:
            if ev.get("event_type") == "phase_enter":
                ts = _parse_ts(ev.get("timestamp"))
                if ts is not None and first_enter is None:
                    first_enter = ts
            elif ev.get("event_type") == "loop_exit":
                ts = _parse_ts(ev.get("timestamp"))
                if ts is not None:
                    exit_ts = ts  # take the last loop_exit if multiple
        if first_enter is not None and exit_ts is not None and exit_ts >= first_enter:
            samples.append((exit_ts - first_enter).total_seconds())
    if not samples:
        return MetricValue(
            name="lead_time", status="unknown", value=None, unit="seconds",
            sample_size=0, window=window,
            reason="no units reached loop_exit (gate passed) in window",
        )
    dist = _dist(samples)
    return MetricValue(
        name="lead_time", status="measured", value=dist["median"],
        unit="seconds", sample_size=len(samples), window=window,
        percentiles={"median": dist["median"], "p90": dist["p90"]},
    )


def _iteration_count_metric(by_unit, window):
    """Flow metric: iteration-count distribution — loop_count per terminal unit.

    ``loop_count`` is read from the terminal event's payload/top-level; when
    absent, it is inferred from the count of ``back_edge`` events for that unit
    (each back_edge = one completed iteration beyond the first). Units that did
    not reach a terminal event contribute no sample.
    """
    samples = []
    for uid, evs in by_unit.items():
        if not uid:
            continue
        terminal = _terminal_event_for_unit(evs)
        if terminal is None:
            continue
        lc = _loop_count_of(terminal)
        if lc is None:
            # Infer from back_edge count.
            lc = sum(1 for ev in evs if ev.get("event_type") == "back_edge")
        samples.append(int(lc))
    if not samples:
        return MetricValue(
            name="iteration_count_distribution", status="unknown", value=None,
            unit="count", sample_size=0, window=window,
            reason="no units reached a terminal event in window",
        )
    dist = _dist(samples)
    return MetricValue(
        name="iteration_count_distribution", status="measured", value=dist,
        unit="count", sample_size=len(samples), window=window,
        percentiles={"median": dist["median"], "p90": dist["p90"]},
    )


def _back_edge_frequency_metric(events, by_unit, window):
    """Flow metric: back_edge events per unit per window.

    Distinct from the other metrics' insufficiency rule: a NON-EMPTY window
    with zero back-edges is a REAL value of ``0`` (no iteration is happening),
    not "unknown". Only a window with zero units (no events at all for any
    unit) is unknown. The sample_size is the number of distinct units, so a
    reader can see "0 back-edges across 12 units" vs "0 back-edges, 0 units".
    """
    unit_count = sum(1 for uid in by_unit if uid)
    if unit_count == 0:
        return MetricValue(
            name="back_edge_frequency", status="unknown", value=None,
            unit="per_unit_per_window", sample_size=0, window=window,
            reason="empty window (no units with events)",
        )
    back_edges = sum(1 for ev in events if ev.get("event_type") == "back_edge")
    return MetricValue(
        name="back_edge_frequency", status="measured",
        value=(back_edges / unit_count) if unit_count else 0.0,
        unit="per_unit_per_window", sample_size=back_edges, window=window,
    )


# ═══════════════════════════════════════════════════════════════════════════
# DORA metric helpers — each carries status/reason (honesty at the point of
# computation, ADR-015 §4.5).
# ═══════════════════════════════════════════════════════════════════════════


def _deployment_frequency_metric(events, window):
    """DORA metric: deployment frequency = loop_exit count (unit completion).

    CRITICAL honesty rule (ADR-015 §4.1): this is unit-completion frequency,
    NOT release frequency. We count ``loop_exit`` events only; release-gate
    passes / phase_enter count / commit count are forbidden proxies
    (AUDIT-133). The report's scope_note makes the scoping explicit.
    """
    exits = sum(1 for ev in events if ev.get("event_type") == "loop_exit")
    if exits == 0:
        return MetricValue(
            name="deployment_frequency", status="unknown", value=None,
            unit="count", sample_size=0, window=window,
            reason="no units reached loop_exit in window "
                   "(unit-completion frequency; NOT release frequency)",
        )
    return MetricValue(
        name="deployment_frequency", status="measured", value=exits,
        unit="count", sample_size=exits, window=window,
    )


def _lead_time_for_changes_metric(by_unit, window):
    """DORA metric: lead time for changes — median/p90 of phase_enter→loop_exit."""
    samples = []
    for uid, evs in by_unit.items():
        if not uid:
            continue
        first_enter = None
        exit_ts = None
        for ev in evs:
            if ev.get("event_type") == "phase_enter":
                ts = _parse_ts(ev.get("timestamp"))
                if ts is not None and first_enter is None:
                    first_enter = ts
            elif ev.get("event_type") == "loop_exit":
                ts = _parse_ts(ev.get("timestamp"))
                if ts is not None:
                    exit_ts = ts
        if first_enter is not None and exit_ts is not None and exit_ts >= first_enter:
            samples.append((exit_ts - first_enter).total_seconds())
    if not samples:
        return MetricValue(
            name="lead_time_for_changes", status="unknown", value=None,
            unit="seconds", sample_size=0, window=window,
            reason="insufficient completed-unit samples "
                   "(need >=1 phase_enter->loop_exit pair)",
        )
    dist = _dist(samples)
    return MetricValue(
        name="lead_time_for_changes", status="measured", value=dist["median"],
        unit="seconds", sample_size=len(samples), window=window,
        percentiles={"median": dist["median"], "p90": dist["p90"]},
    )


def _change_failure_rate_metric(by_unit, window):
    """DORA metric: change failure rate = (fuse_trip + unit_withdrawn) / terminal units.

    CRITICAL anti-proxy (ADR-015 §4.3, AUDIT-133): the denominator is
    COMPLETED UNITS, not total loops. A unit that iterated 5 times then exited
    successfully is ONE success, not 5. Counting iterations in the denominator
    would conflate "lots of healthy iteration" with "failure" — this is the
    exact ``fuse_trips/total_loops`` defect ``loop_health._compute_dora_metrics``
    performs and that FEAT-008 replaces. The terminal-event precedence
    (§4.3 / Design Review P1-2): a unit counts once, classified by its LAST
    terminal event. Zero terminal events → ``unknown`` (NOT 0.0): zero failures
    over zero completions is undefined, not zero.
    """
    successes = 0
    failures = 0
    for uid, evs in by_unit.items():
        if not uid:
            continue
        terminal = _terminal_event_for_unit(evs)
        if terminal is None:
            continue
        et = terminal.get("event_type")
        if et == _SUCCESS_TERMINAL:
            successes += 1
        elif et in _FAILURE_TERMINALS:
            failures += 1
    denominator = successes + failures
    if denominator == 0:
        return MetricValue(
            name="change_failure_rate", status="unknown", value=None,
            unit="ratio", sample_size=0, window=window,
            reason="no completed units in window",
        )
    return MetricValue(
        name="change_failure_rate", status="measured",
        value=round(failures / denominator, 6),
        unit="ratio", sample_size=denominator, window=window,
        percentiles={"successes": successes, "failures": failures},
    )


def _time_to_restore_metric(by_unit, window):
    """DORA metric: time to restore/escalate — median/p90 of fuse_trip→escalation_resolved.

    CRITICAL honesty rule (ADR-015 §4.4): UNRESOLVED fuse trips (tripped but no
    subsequent ``escalation_resolved``) do NOT contribute a restore-time sample
    and do NOT let us claim MTTR=0. They are reported separately as
    ``open_fuse_trips`` in the report diagnostics. Zero resolved fuses →
    ``unknown``. The metric is labeled "time to restore/escalate" because in
    loop engineering the analog of a production-incident restore is fuse →
    escalation-resolution (human arbitration / split / degraded / withdraw); it
    is NOT a production-incident MTTR.
    """
    samples = []
    open_trips = 0
    for uid, evs in by_unit.items():
        if not uid:
            continue
        # Walk this unit's events in order; pair each fuse_trip with the first
        # subsequent escalation_resolved strictly after it. A fuse_trip with no
        # later resolution is an open trip.
        pending_trips = []
        resolved_pairs = []
        for ev in evs:
            et = ev.get("event_type")
            ts = _parse_ts(ev.get("timestamp"))
            if ts is None:
                continue
            if et == "fuse_trip":
                pending_trips.append(ts)
            elif et == "escalation_resolved":
                # Resolve the earliest still-open trip (FIFO).
                if pending_trips:
                    trip_ts = pending_trips.pop(0)
                    if ts > trip_ts:
                        resolved_pairs.append((trip_ts, ts))
        open_trips += len(pending_trips)
        for trip_ts, res_ts in resolved_pairs:
            samples.append((res_ts - trip_ts).total_seconds())
    if not samples:
        return MetricValue(
            name="time_to_restore", status="unknown", value=None,
            unit="seconds", sample_size=0, window=window,
            reason="no resolved fuse trips in window",
        ), open_trips
    dist = _dist(samples)
    return MetricValue(
        name="time_to_restore", status="measured", value=dist["median"],
        unit="seconds", sample_size=len(samples), window=window,
        percentiles={"median": dist["median"], "p90": dist["p90"]},
    ), open_trips


# ═══════════════════════════════════════════════════════════════════════════
# Terminal-event precedence + payload extraction (Design Review P1-1/P1-2)
# ═══════════════════════════════════════════════════════════════════════════


def _terminal_event_for_unit(unit_events):
    """Return the LAST terminal event for a unit, or ``None`` if it has none.

    Terminal-event precedence (Design Review P1-2): when a unit has multiple
    terminal events, classify by the LAST one. A unit that fuse-tripped then
    was withdrawn → counted as withdrawn (the final state). A unit that
    fuse-tripped then resolved then exited → counted as exit (passed). The
    events are already sorted by (timestamp, cas_version) upstream.
    """
    terminal = None
    for ev in unit_events:
        if ev.get("event_type") in _TERMINAL_EVENTS:
            terminal = ev
    return terminal


def _loop_count_of(event):
    """Return the integer loop_count carried on an event, or ``None``.

    The loop_count may be at the top level or nested under ``payload`` (both
    shapes appear in the 0.68.0 wiring). Returns ``None`` when absent or
    non-integer so the caller can fall back to counting back_edges.
    """
    lc = event.get("loop_count")
    if lc is None:
        payload = event.get("payload")
        if isinstance(payload, dict):
            lc = payload.get("loop_count")
    if isinstance(lc, int) and not isinstance(lc, bool):
        return lc
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Public entry — composes the helpers into one report
# ═══════════════════════════════════════════════════════════════════════════


def compute_metrics(events, *, window=None):
    """PURE: compute flow + DORA metrics over a list of event dicts.

    Args:
        events: list[dict] of event envelopes (as returned by
            :func:`loop_event_log.read_events`). Any iterable of dicts; this
            function does NOT read files.
        window: ``None`` (all-time) | ``"7d"``/``"30d"``/``"90d"`` (trailing,
            relative to the latest event timestamp) | ``(start_iso, end_iso)``
            explicit ``[start, end)`` date window.

    Returns:
        :class:`MetricsReport`. Never raises — malformed events are counted in
        diagnostics and skipped. Every metric carries its own ``status``; no
        metric fabricates a value (unknown-when-insufficient, ADR-015 §3.4/§4).

    Purity contract (ADR-015 §6.2): no file I/O, no network, no
    ``datetime.now()``, no module-level mutable state. The same ``events`` +
    ``window`` always yield a structurally equal report.
    """
    # Materialize once (the caller may pass a generator).
    events_list = list(events)
    events_list = [ev for ev in events_list if isinstance(ev, dict)]

    # Count malformed timestamps (before windowing) for diagnostics.
    malformed = 0
    for ev in events_list:
        if _parse_ts(ev.get("timestamp")) is None:
            malformed += 1

    # Window the events (ADR-015 §5). _filter_window drops malformed-timestamp
    # events from the kept set (they have no parseable timestamp to compare).
    kept, latest = _filter_window(events_list, window)
    window_lbl = _window_label(window)

    by_unit = _by_unit(kept)
    unit_count = sum(1 for uid in by_unit if uid)

    # ── Flow metrics (4) ───────────────────────────────────────────────────
    flow = {
        "cycle_time": _cycle_time_metric(by_unit, window_lbl),
        "lead_time": _lead_time_flow_metric(by_unit, window_lbl),
        "iteration_count_distribution": _iteration_count_metric(by_unit, window_lbl),
        "back_edge_frequency": _back_edge_frequency_metric(kept, by_unit, window_lbl),
    }

    # ── DORA metrics (4) ───────────────────────────────────────────────────
    dora = {
        "deployment_frequency": _deployment_frequency_metric(kept, window_lbl),
        "lead_time_for_changes": _lead_time_for_changes_metric(by_unit, window_lbl),
        "change_failure_rate": _change_failure_rate_metric(by_unit, window_lbl),
    }
    ttr, open_trips = _time_to_restore_metric(by_unit, window_lbl)
    dora["time_to_restore"] = ttr

    computed_at = latest.strftime(_TS_FORMAT) if latest is not None else "1970-01-01T00:00:00Z"

    diagnostics = {
        "malformed_timestamps": malformed,
        "open_fuse_trips": open_trips,
        "window": window_lbl,
        "units_considered": unit_count,
        "events_considered": len(kept),
    }

    return MetricsReport(
        window=window_lbl,
        computed_at=computed_at,
        flow=flow,
        dora=dora,
        units_considered=unit_count,
        event_count=len(kept),
        diagnostics=diagnostics,
        scope_note=SCOPE_NOTE,
    )


if __name__ == "__main__":  # pragma: no cover - manual smoke
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    # Smoke: a tiny in-memory fixture → report.
    sample = [
        {
            "event_id": "e1", "timestamp": "2026-07-23T00:00:00Z",
            "unit_id": "u.A", "event_type": "phase_enter",
            "cas_version": 0, "from_version": None,
            "from_phase": None, "to_phase": "plan", "actor": "smoke",
        },
        {
            "event_id": "e2", "timestamp": "2026-07-23T01:00:00Z",
            "unit_id": "u.A", "event_type": "loop_exit",
            "cas_version": 1, "from_version": 0,
            "from_phase": "reflect", "to_phase": "exit", "actor": "smoke",
        },
    ]
    rep = compute_metrics(sample)
    print("window:", rep.window, "units:", rep.units_considered,
          "events:", rep.event_count)
    for name, mv in rep.flow.items():
        print("flow", name, mv.status, mv.value, mv.sample_size)
    for name, mv in rep.dora.items():
        print("dora", name, mv.status, mv.value, mv.sample_size)
