# ADR-015: Loop Telemetry 0.69.0 — Honest Flow/DORA Metrics Computed From the Event Log

- Status: PROPOSED / READY_FOR_DESIGN_REVIEW
- Date: 2026-07-23
- Version scope: 0.69.0
- Tasks: FEAT-008 (production telemetry + honest flow/DORA metrics)
- Release: REL-061 (0.69.0 — Metrics and external proof). FEAT-008 is the product-code (telemetry) part; VAL-008 (dogfood) and VAL-009 (two external project types) are the validation parts, separately scoped.
- Authority: DEC-104 (binding runtime-first roadmap), AUDIT-133 / EVD-707 (the honesty requirement: "缺数据返回 unknown，不以 release count/fuse ratio 冒充完整 DORA"), ADR-014 §5 (the 0.68.0 event log FEAT-008 builds on), ADR-013 (0.67.0 v2 contract), RISK-037 / RISK-042 (open risks; 0.69.0 *delivers telemetry but does not close them* — that requires VAL-008/009 external evidence)
- Review authority required: independent Design Review (REVIEW-FEAT-008-DESIGN-R0 chain or the Coordinator's designated reviewer); this ADR is design-only and does not self-approve FEAT-008
- Reversibility: FEAT-008 is a strictly-additive new module (`infra/loop_telemetry.py`) plus a thin CLI entry and one advisory wiring point; it reads the 0.68.0 event log read-only and writes nothing; the 0.67.0 contract, 0.68.0 engine, and v1 validator are unchanged; RISK-037/RISK-042 remain open until VAL-008/009

> **Design-only ADR.** This document specifies production telemetry for the Loop Engine — flow metrics and DORA-style metrics computed **purely from the 0.68.0 event log** (`loop-event-log.jsonl`), with a hard **unknown-when-insufficient** rule. It is written by the Architect role for Design Reviewer review. It does not implement code, does not dispatch a Developer, and does not authorize a release. FEAT-008 requires its own DEC + Developer + Code Reviewer + QA cycle per the governance workflow. No-overclaim discipline: 0.69.0 delivers *measurement*, not *effectiveness proof* — RISK-037/RISK-042 stay open (external validation is VAL-008/009), and telemetry never claims the loop engine is "production-ready" or that DORA numbers describe the whole software project.

<!-- loop-runtime-target:{"claim_id":"LRC-TELEMETRY-PLANNED-001","target_version":"0.69.0","status":"planned_not_active"} -->
> The telemetry module, `loop-telemetry` CLI command, and metrics report described here are planned-not-active until FEAT-008 is implemented, independently reviewed, and REL-061 passes. This ADR is the design; it measures nothing by being written.

---

## 1. Context

### 1.1 DEC-104 roadmap (the binding plan)

DEC-104 (2026-07-11) adopted a runtime-first repair roadmap for Loop Engineering after AUDIT-133 proved the 0.65.0 implementation was schema-only. The version chain:

- **0.67.0 (released, `b183ca6`)** — canonical Loop Runtime Contract v2 + single shared migration planner + decomposition confirmation (FEAT-002~004). Units written **dormant**.
- **0.68.0 (released, `4208fcf`)** — persistent PARO state machine + production gate back-edge/fuse/escalation + restart-safe event log + dependency blocking + WIP (FEAT-005~007, REL-060). **The execution engine and its audit trail.**
- **0.69.0 (this ADR)** — production telemetry (FEAT-008) + dogfood multi-unit/multi-lane runtime validation (VAL-008) + two external project-type installed-state validation (VAL-009).
- **0.70.0** — verify_workflow Phase 5 extraction (deferred).

0.69.0 is the version that makes Loop Engineering **measurable in production** — computing flow/DORA metrics from the 0.68.0 event log — while VAL-008/009 separately produce the external *effectiveness* evidence. FEAT-008 is the measurement; VAL-008/009 are the proof.

### 1.2 The 0.68.0 event-log foundation (the telemetry data source)

REL-060 delivered (ADR-014) the append-only event log every telemetry metric reads:

- **`infra/loop_event_log.py`** — `append_event` / `read_events` / `last_event_for_unit` / `validate_event` / `check_cas_monotonicity` / `check_phase_legality`. Append-only JSONL at `HOST_ROOT/.governance/loop-event-log.jsonl`. The closed enum of **14 event types**: `phase_enter`, `phase_transition`, `gate_result`, `back_edge`, `loop_exit`, `fuse_trip`, `escalation_resolved`, `unit_blocked`, `unit_withdrawn`, `dependency_block`, `wip_admit`, `wip_deny`, `phase_recovery`, `recovery_conflict`.
- Every event envelope (ADR-014 §5.1) carries: `event_id`, `timestamp` (ISO-8601 UTC), `unit_id`, `event_type`, `cas_version`, `from_version`, `from_phase`, `to_phase`, `actor`, plus optional `gate_id`, `tier`, `evidence_ref`, `payload`. **The `timestamp` + `unit_id` + `event_type` triplet is the load-bearing telemetry input** — every metric below is a pure function of these.
- Multi-process write safety is already solved by the 0.68.0 CAS + atomic-line-append discipline (ADR-014 §5.2). Telemetry reads the log; it never writes it.

FEAT-008 **builds telemetry ON TOP of the event log**. It does not extend the enum, does not add event fields, does not modify the engine. It only *reads and computes*.

### 1.3 The honesty requirement (AUDIT-133) — the problem this ADR solves

AUDIT-133 / EVD-707 (the binding FEAT-008 spec) states verbatim:

> 事件写入 velocity/lead-time/deployment/failure/restore telemetry；按时间窗口和标准定义计算，**缺数据返回 unknown，不以 release count/fuse ratio 冒充完整 DORA**。

The anti-pattern FEAT-008 must correct already exists in the codebase. `infra/loop_health.py::_compute_dora_metrics` (lines 266–322, the existing "DORA bridge") reads a `dora` block from `flow-unit-runtime.json`:

```python
metrics["deployment_frequency"] = release_passes   # release-gate pass count as "deployment frequency"
if total_loops > 0:
    metrics["change_failure_rate"] = round(fuse_trips / total_loops, 4)  # fuse ratio as "CFR"
else:
    metrics["change_failure_rate"] = None
```

This has three honesty defects FEAT-008 must fix:

1. **No producer.** Nothing writes the `dora` block, so `_compute_dora_metrics` always returns `{}` in practice — silent zero rather than honest "unknown".
2. **Proxy overclaim.** `release_gate_passes` is treated as *deployment frequency* and `fuse_trips / total_loops` as *change failure rate*. These are release/fuse bookkeeping, not DORA deployment/lead-time/restore measured from delivery events. AUDIT-133 explicitly forbids this substitution.
3. **No lead time, no restore time, no time-windowing.** The "DORA bridge" reports 2 of 4 metrics, with no window, and admits no insufficiency signal beyond `None` on `/0`.

FEAT-008's job is to compute the real four DORA metrics — plus the four flow metrics — **from the event log**, scoped honestly to the loop-unit lifecycle, returning `"unknown"` (not zero, not `None`-as-zero, not a proxy) whenever the events are insufficient.

### 1.4 The no-overclaim boundary (what telemetry is NOT)

Telemetry reports **what it measures**. It does NOT:

- Claim the loop engine is "production-ready" or "complete". (Runtime activation is a 0.69.0 *external* question — VAL-008/009 — not a telemetry question.)
- Project DORA numbers onto the whole software project. The metrics are scoped to **loop-unit lifecycle** (one unit's `phase_enter → loop_exit`/`unit_withdrawn`), not to release cadence. A whole-software-project DORA report is out of scope and would be overclaim.
- Substitute release counts or fuse ratios for DORA metrics (AUDIT-133 forbids this; §4 below replaces the proxy with event-derived definitions).
- Close RISK-037/RISK-042. Telemetry measures; external validation proves. REL-061's acceptance (§8) requires external evidence + runtime gates, then re-evaluates the risks.

### 1.5 The RISK-039 thin-entry constraint (where logic lives)

`verify_workflow.py` is ~22k lines (RISK-039 God Module; ArchGuard guards its size). DEC-083/ADR-014 §1.6 mandate: **no new logic in `verify_workflow.py`** — only thin `cmd_*` entries (≤20 lines, argparse glue + delegation). All telemetry logic lives in the **new `infra/loop_telemetry.py`** module; `verify_workflow.py` gets only one thin delegating `cmd_loop_telemetry` entry plus one advisory wiring point (§7). This mirrors exactly how `cmd_check_loop_health` and `cmd_loop_rollup` already delegate to `infra/loop_health.py` / `infra/loop_engine.py`.

---

## 2. Decision

Adopt **one strictly-additive new module** plus **one thin CLI entry** plus **one advisory wiring point** for 0.69.0:

1. **FEAT-008 — `infra/loop_telemetry.py`.** A pure metrics module that consumes a list of events (the deserialized output of `loop_event_log.read_events`) and computes:
   - **Flow metrics** (§3): cycle time, lead time, iteration-count distribution, back-edge frequency.
   - **DORA-style metrics** (§4): deployment frequency, lead time for changes, change failure rate, time to restore/escalate — all adapted for loop-unit lifecycle, all with **explicit `unknown` values when the events are insufficient**.
   - A time-windowed entry point `compute_metrics(events, *, window=None) -> MetricsReport` (§5).
   The module is **pure** (no I/O, no module-level mutable state, deterministic given the event list) and takes **events as input** rather than reading the file itself. The CLI wrapper (§7) does the file read.

2. **Thin CLI entry `loop-telemetry`.** `cmd_loop_telemetry` in `verify_workflow.py` reads the event log via `loop_event_log.read_events` (RISK-040 HOST_PROJECT_ROOT resolution, never PLUGIN_HOME) and delegates to `loop_telemetry.compute_metrics`, printing the report. Thin: ≤20 lines.

3. **One advisory wiring point.** `loop_health.check_loop_health` gains an **optional** `telemetry` key in its result envelope, computed by `loop_telemetry.compute_metrics` from the same event log `loop_health` already has access to. This is **advisory** (advisory severity, non-blocking, no gate fails on it). The existing `_compute_dora_metrics` proxy is **deprecated, not deleted** (§7.3) — its output is demoted and clearly labeled as the legacy proxy, and the honest metrics supersede it.

These three make the Loop Engine **measurable from its own recorded events**, with the honesty rule enforced at the metric-definition layer. None closes RISK-037/RISK-042 (external validation is VAL-008/009). None modifies the 0.68.0 engine, the event-log enum/fields, or the v1/v2 contract.

---

## 3. Flow Metrics Spec (per-unit, per-tier)

Flow metrics describe the **shape of iteration** — how a unit moves through the loop. They are computed per-unit and aggregated per-tier and across all units in the window.

### 3.1 Definitions

| Metric | Definition | Event anchors | Unit |
|--------|------------|---------------|------|
| **Cycle time** (one iteration) | Wall-clock duration of one complete loop iteration: `phase_enter` (or the `phase_enter`/`back_edge` that started this round) → the next `loop_exit`/`back_edge` that ends it. | `phase_enter` or `back_edge` (round start) → `loop_exit` or next `back_edge` (round end) | seconds |
| **Lead time** (per unit, to gate-pass) | Wall-clock from the unit's first `phase_enter` (activation) to its `loop_exit` (gate passed; the unit exits its tier). | first `phase_enter` → `loop_exit` | seconds |
| **Iteration count** (distribution) | `loop_count` per unit at terminal event — the number of back-edges a unit took before exit/withdraw. Telemetry reports the **distribution** (min, median, p90, max, mean) across units in the window, not a single number. | `loop_count` carried on `loop_exit`/`fuse_trip`/`unit_withdrawn` payloads; or counted from `back_edge` events | count |
| **Back-edge frequency** | Rate of `back_edge` events per unit per time window. | `back_edge` events | back-edges / unit / window |

### 3.2 Cycle time vs lead time — disambiguation

These two are deliberately distinct and must not be conflated:

- **Cycle time** = one *iteration* (one round trip). A unit that iterates 3 times has 3 cycle-time samples.
- **Lead time** = the *whole* unit lifecycle from activation to gate-passed exit. A unit has exactly one lead-time sample (if it exited) or none (if still active, withdrawn, or fused without resolution).

This maps to the DORA "lead time for changes" only in the *aggregate* sense (§4.2); the per-iteration cycle time is a separate flow signal (it reveals how long each review-fix cycle takes, independent of how many cycles occur).

### 3.3 Per-tier aggregation

Each metric is reported both **overall** and **grouped by `tier`** (the `active_loop_tier`: `setup`/`inner`/`middle`/`outer`). A unit's tier is read from its `phase_enter` event payload (`tier` field, written by `loop_paro_engine.activate_unit`) and carried on subsequent events by the gate processor. Per-tier grouping lets a reader see, e.g., that `inner`-tier units cycle fast but `outer`-tier units have long lead times — information a single aggregate hides.

### 3.4 Insufficiency rules for flow metrics

| Metric | "unknown" when |
|--------|----------------|
| Cycle time | Fewer than **1 completed iteration** in the window has both a round-start and round-end event with parseable timestamps. |
| Lead time | Fewer than **1 unit** in the window reached `loop_exit` (gate passed). Active/withdrawn/fused-without-exit units contribute no lead-time sample. |
| Iteration-count distribution | Fewer than **1 unit** reached a terminal event (`loop_exit`/`unit_withdrawn`/`fuse_trip`) in the window. |
| Back-edge frequency | **Zero `back_edge` events** in the window AND fewer than 1 unit (an empty window). A non-empty window with zero back-edges is a real metric value of `0`, not "unknown". |

The distinction between "0 back-edges observed across 12 active units" (real signal: no iteration is happening) and "no units, no events" (unknown) is load-bearing for honesty. The report carries a `sample_size` alongside every metric so a reader can judge.

---

## 4. DORA-Style Metrics Spec (honest, event-derived, loop-scoped)

The four DORA metrics, adapted for loop engineering. **Each carries an explicit `status` field: `"measured"` or `"unknown"`.** When `status == "unknown"`, the numeric value is `None` and a `reason` string explains what data was missing. Telemetry NEVER returns a fabricated number or a proxy.

### 4.1 Deployment frequency (unit-completion frequency)

- **Definition (loop-scoped):** the count of `loop_exit` events (units that passed their tier gate) per time window, optionally normalized per day/week.
- **Event anchor:** `loop_exit` events in the window.
- **CRITICAL honesty rule — this is NOT release frequency.** `loop_exit` means a *flow unit* completed its tier loop, not that the software project shipped a release. The metric is reported as **"unit-completion frequency"** in the report, with an explicit note that it is a loop-unit-lifecycle signal, not a deployment-to-production signal. Releasing the software project is a separate cadence (the existing release manifest/ledger, FEAT-001) and is out of telemetry scope.
- **Insufficiency → `unknown`:** when there are **zero `loop_exit` events** in the window, `status = "unknown"`, value `None`, reason `"no units reached loop_exit in window"`. We do NOT substitute `phase_enter` count, `wip_admit` count, or release-gate-pass count — those are different signals.

### 4.2 Lead time for changes

- **Definition (loop-scoped):** the `phase_enter → loop_exit` wall-clock duration per unit (the per-unit lead time from §3.1), reported as **median and p90** across units that exited in the window.
- **Event anchor:** pair each unit's first `phase_enter` with its `loop_exit` (matching on `unit_id`), compute the duration, take the distribution.
- **Insufficiency → `unknown`:** when fewer than **1 unit** has a complete `phase_enter → loop_exit` pair in the window, `status = "unknown"`, value `None`, reason `"insufficient completed-unit samples (need ≥1 phase_enter→loop_exit pair)"`. Median/p90 over 1 sample is degenerate but defined; over 0 samples is `unknown`.
- **NOT a proxy for cycle time:** lead time measures end-to-end; cycle time (§3.1) measures per-iteration. Both are reported.

### 4.3 Change failure rate

- **Definition (loop-scoped):** the fraction of *completed units* that terminated in failure rather than success, where:
  - **denominator** = units that reached a terminal event in the window: `loop_exit` (success) + `fuse_trip` (failure) + `unit_withdrawn` (failure).
  - **numerator** = units that reached `fuse_trip` or `unit_withdrawn` (the failure terminations).
  - `change_failure_rate = numerator / denominator`.
- **Event anchors:** `loop_exit`, `fuse_trip`, `unit_withdrawn` events, grouped by `unit_id` (a unit counts once even if it has multiple events; the *terminal* event for each unit in the window decides its classification).
- **This is NOT `fuse_trips / total_loops`** (the AUDIT-133-forbidden proxy in the existing `_compute_dora_metrics`). The denominator here is *completed units*, not *iteration count*; a unit that iterated 5 times then exited successfully is one success, not 5. Counting iterations in the denominator would conflate "lots of healthy iteration" with "failure".
- **Insufficiency → `unknown`:** when the denominator is **0** (no terminal events in the window), `status = "unknown"`, value `None`, reason `"no completed units in window"`. We do NOT report `0.0` — zero failures over zero completions is undefined, not zero.

### 4.4 Time to restore / time to escalate

- **Definition (loop-scoped):** the wall-clock duration from a `fuse_trip` event to its resolving `escalation_resolved` event for the same `unit_id`, reported as **median and p90** across resolved fuses in the window.
- **Event anchors:** pair each `fuse_trip` with the subsequent `escalation_resolved` on the same unit (matching `unit_id`; the resolve must be strictly after the trip in event order).
- **Insufficiency → `unknown`:** when there are **0 resolved fuse trips** in the window (i.e., no `fuse_trip → escalation_resolved` pairs), `status = "unknown"`, value `None`, reason `"no resolved fuse trips in window"`. *Unresolved* fuse trips (tripped but no `escalation_resolved` yet) are reported separately as a count (`open_fuse_trips`) — they are real signal ("there are N unresolved fuses") but they do NOT contribute a restore-time sample, and their absence does not let us claim "MTTR = 0".
- **Honesty note on "restore":** DORA's "time to restore" applies to production incidents. In loop engineering the analog is fuse → escalation-resolution (human arbitration / split / degraded / withdraw). The metric is labeled **"time to restore/escalate"** to make the scoping explicit; it is NOT a production-incident MTTR.

### 4.5 The honesty-rule summary table (for the Design Reviewer)

| Metric | Real signal | Forbidden proxy | unknown when |
|--------|-------------|-----------------|--------------|
| Deployment frequency | `loop_exit` count / window | release-gate passes, `phase_enter` count, commit count | 0 `loop_exit` in window |
| Lead time for changes | median/p90 of `phase_enter→loop_exit` | first-commit-to-merge, fuse round count | <1 completed unit pair |
| Change failure rate | (fuse_trip + unit_withdrawn) / terminal events | fuse_trips / total_loops, fuse_trips / phase_enter | 0 terminal events |
| Time to restore/escalate | median/p90 of `fuse_trip→escalation_resolved` | fuse-trip-to-withdrawn, escalate count | 0 resolved fuses |

Every forbidden proxy in the table is the exact substitution AUDIT-133 prohibits and that `loop_health._compute_dora_metrics` currently performs. FEAT-008 replaces them.

---

## 5. Time-Windowed Computation

### 5.1 The window parameter

`compute_metrics(events, *, window=None) -> MetricsReport`:

- `window=None` → **all-time** (every event in the input list).
- `window="7d"` / `"30d"` / `"90d"` → only events whose `timestamp` falls within the trailing N days relative to the latest event timestamp in the input (relative window, not wall-clock-now). Relative-to-latest-event keeps the computation deterministic and testable (a fixed event fixture always yields the same window regardless of when the test runs).
- `window=("2026-07-01", "2026-07-23")` → explicit `[start, end)` ISO-date window.

Windowing filters events **before** metric computation. A metric computed over a windowed event set applies its own insufficiency rule (§3.4/§4) to the *windowed* data — so a 7-day window with no completions yields `unknown` even if all-time has completions. This is the honest behavior: "in the last 7 days, lead time is unknown (no units completed)" is a true and useful statement, distinct from "all-time lead time is X".

### 5.2 Timestamp parsing and robustness

- Events carry ISO-8601 UTC timestamps (`loop_event_log.now_timestamp()` produces `%Y-%m-%dT%H:%M:%SZ`). Telemetry parses with `datetime.strptime(..., "%Y-%m-%dT%H:%M:%SZ")` and treats unparseable timestamps as **event-level skip** (the event is excluded from duration math but counted in a `malformed_timestamps` diagnostic so the reader knows data was dropped). Never raises.
- Durations are computed in **seconds** (float). The report may render human-readable (e.g. `"3h 12m"`) but the structured value is seconds.
- Clock skew across processes (ADR-014 §5.2 acknowledges concurrent appends can land out of timestamp order) is handled by **sorting each unit's events by `(timestamp, cas_version)`** before pairing — mirroring `loop_event_log._events_in_order`. The monotonic `cas_version` is the tiebreaker and the authoritative ordering within a unit.

### 5.3 What the window does NOT do

- The window does not extrapolate. "7-day window with 3 completed units" reports those 3; it does not annualize or impute.
- The window does not merge across boundaries. Each window is independent; the caller computes multiple windows by calling `compute_metrics` multiple times.

---

## 6. Telemetry Module Spec (`infra/loop_telemetry.py`)

### 6.1 Public API (frozen signature)

```python
# infra/loop_telemetry.py  (FEAT-008, 0.69.0)

from dataclasses import dataclass, field

@dataclass(frozen=True)
class MetricValue:
    """One metric's result. Carries its own honesty status."""
    name: str                       # e.g. "lead_time_for_changes"
    status: str                     # "measured" | "unknown"
    value: object = None            # the number/dict when measured; None when unknown
    unit: str = ""                  # "seconds", "count", "ratio", "per_day"
    sample_size: int = 0            # how many events/units contributed
    reason: str = ""                # why unknown (empty when measured)
    percentiles: dict = field(default_factory=dict)  # {"median":..,"p90":..} where applicable

@dataclass(frozen=True)
class MetricsReport:
    """The full telemetry report over a (windowed) event set."""
    window: str                     # "all" | "7d" | "30d" | explicit range
    generated_at: str               # ISO-8601, latest event timestamp in input
    flow: dict                      # {metric_name: MetricValue}
    dora: dict                      # {metric_name: MetricValue}
    units_considered: int           # distinct unit_ids in the windowed events
    events_considered: int          # event count in the windowed set
    diagnostics: dict               # {"malformed_timestamps": n, "unpaired_events": [...], ...}
    scope_note: str                 # the no-overclaim note (loop-unit lifecycle, NOT whole project)

def compute_metrics(events, *, window=None) -> MetricsReport:
    """PURE: compute flow + DORA metrics over a list of event dicts.

    Args:
        events: list[dict] of event envelopes (as returned by
            loop_event_log.read_events). Any iterable of dicts; this function
            does NOT read files.
        window: None (all-time) | "7d"|"30d"|"90d" (trailing, relative to the
            latest event timestamp) | (start_iso, end_iso) tuple.

    Returns:
        MetricsReport. Never raises — malformed events are counted in
        diagnostics and skipped. Every metric carries its own status; no metric
        fabricates a value (unknown-when-insufficient, §3.4/§4).
    """
```

### 6.2 Purity contract (load-bearing)

`compute_metrics` is **pure**:

- No file I/O, no network, no `datetime.now()`. The only time reference is the events' own timestamps.
- No module-level mutable state. All helpers are inner functions or module-level pure functions.
- Deterministic: the same `events` list + `window` always yields a structurally equal `MetricsReport`.

This purity is what makes the metric functions unit-testable with a fixed event fixture (§8) and what keeps telemetry safe to invoke from any gate/CLI/review context without side effects. The CLI wrapper (§7) is the only place that reads the file; the metric layer is input→output.

Purity is verified by a test that constructs a known event sequence, calls `compute_metrics`, and asserts exact numeric results; a second test asserts that calling it twice on the same input yields equal reports and mutates no global state.

### 6.3 Internal structure (for the implementer)

```
loop_telemetry.py
├── MetricValue / MetricsReport dataclasses (frozen)
├── _parse_ts(timestamp) -> datetime | None        # ISO-8601 UTC; None on malformed
├── _filter_window(events, window) -> list          # relative/explicit windowing (§5)
├── _by_unit(events) -> dict[unit_id, list[event]]  # group + sort by (ts, cas_version)
├── _cycle_times(unit_events) -> list[float]        # §3.1 cycle time samples
├── _lead_times(by_unit) -> list[float]             # §3.1 lead time (phase_enter→loop_exit)
├── _iteration_counts(by_unit) -> list[int]         # §3.1 distribution
├── _back_edge_frequency(events, window) -> MetricValue  # §3.1
├── _deployment_frequency(events) -> MetricValue    # §4.1 (loop_exit count; NOT release)
├── _lead_time_for_changes(by_unit) -> MetricValue  # §4.2 median/p90
├── _change_failure_rate(by_unit) -> MetricValue    # §4.3 (failures / terminal events)
├── _time_to_restore(by_unit) -> MetricValue        # §4.4 fuse_trip→escalation_resolved
├── compute_metrics(events, *, window=None)         # §6.1 entry; composes the above
└── __all__ = ["MetricValue", "MetricsReport", "compute_metrics"]
```

Every `_metric` helper returns a `MetricValue` with its own `status`/`reason` — the insufficiency rule lives at the point of computation, not at the caller. This is what makes the honesty rule locally checkable in code review.

### 6.4 What the module does NOT do

- Does not read `flow-unit-runtime.json`. (The event log is the telemetry source; the runtime file is the 0.68.0 operational truth, not a metrics source.)
- Does not read the registry. (Tier is read from event payloads, not re-derived.)
- Does not write anything. (No `append_event`, no state mutation — telemetry is read-only.)
- Does not import `loop_paro_engine` or `loop_gate_processor`. (Telemetry depends only on `loop_event_log` for the event shape and on stdlib. This keeps the dependency graph clean: telemetry is a *consumer* of the event log, not a peer of the engine.)
- Does not define new event types or extend the enum.

---

## 7. Integration (where telemetry is invoked)

### 7.1 CLI command `loop-telemetry` (primary surface)

A new thin entry in `verify_workflow.py` (mirroring `cmd_check_loop_health` / `cmd_loop_rollup` at lines 21031/21074):

```python
def cmd_loop_telemetry(args):
    """Thin entry — delegates to infra/loop_telemetry.py (0.69.0 telemetry)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from loop_event_log import read_events
    from loop_telemetry import compute_metrics
    from resolve_entry import resolve_host_root   # RISK-040: HOST_PROJECT_ROOT, never PLUGIN_HOME
    root = getattr(args, "target", None) or resolve_host_root()
    log_path = Path(root) / ".governance" / "loop-event-log.jsonl"
    events = read_events(log_path=log_path)
    report = compute_metrics(events, window=getattr(args, "window", None))
    _format_telemetry(report)   # human-readable print; JSON via --json flag
```

Registered in the command dispatch table (`"loop-telemetry": cmd_loop_telemetry`). Thin: argparse glue + 2 delegated calls. **The file read happens here (in the CLI), not in the pure module** — this is the purity/CLI split §6.2 requires.

Flags: `--window {all,7d,30d,90d}` (default `all`), `--json` (machine-readable), `--target <root>` (RISK-040 host root override).

### 7.2 Advisory wiring into `loop_health` (secondary surface)

`loop_health.check_loop_health` gains an **optional** `telemetry` key in its result envelope:

```python
# inside check_loop_health, after the existing Part 1 + Part 2 + DORA compose:
try:
    from loop_telemetry import compute_metrics
    from loop_event_log import read_events
    log_events = read_events(log_path=...)  # same host root runtime_data came from
    report = compute_metrics(log_events, window="30d")
    telemetry = {"flow": report.flow, "dora": report.dora, "scope_note": report.scope_note}
except Exception:
    telemetry = {"status": "unavailable", "reason": "event log absent or unreadable"}
result["telemetry"] = telemetry   # ADVISORY; never blocks; never fails the health check
```

This is **advisory only** — it appears in `check-loop-health` output but has no `FAIL` severity and cannot block a release/gate. The existing `dora_metrics` key (from `_compute_dora_metrics`) is preserved for one release cycle and labeled `"dora_metrics_legacy_proxy"` with a deprecation note pointing at `telemetry.dora`; it is removed in 0.70.0 (§7.3).

### 7.3 Deprecation, not deletion, of the legacy proxy

`loop_health._compute_dora_metrics` is **not deleted in 0.69.0** (deletion would be a behavior change to `check-loop-health` output that downstream readers may parse). Instead:

- Its output key is renamed `dora_metrics` → `dora_metrics_legacy_proxy`.
- A `deprecated` boolean + `deprecation_note` ("replaced by telemetry.dora in 0.69.0; removed in 0.70.0") are added.
- The honest `telemetry.dora` (§4) is the new authoritative DORA surface.

A deprecation test asserts the legacy key is present (with the new name) in 0.69.0 and that `telemetry.dora` supersedes it. FIX/FEAT in 0.70.0 removes `_compute_duse_dora_metrics` entirely. This two-release deprecation is the standard containment discipline (mirrors how v1 validators are frozen across releases).

### 7.4 What is NOT wired (honest scope)

- Telemetry is **not** wired into `check_release_readiness` / Check 28 as a blocking gate. Metrics are observations, not pass/fail criteria. (The fuse *block* is already there from 0.68.0 FEAT-006; that is a state check, not a metric. Telemetry does not add gate logic.)
- Telemetry is **not** auto-emitted on every event append (no hook into `append_event`). It is computed on demand (CLI or `check-loop-health`). Auto-emission would couple write and read paths and re-introduce a side-effect surface.
- Telemetry is **not** projected into release docs or the manifest. It is an operational observability surface, not a release artifact.

---

## 8. REL-061 Acceptance Criteria + Tests

### 8.1 REL-061 acceptance (from plan-tracker row 167)

> MINOR。**仅在外部 evidence 与 runtime gates 全部满足后重新评估 RISK-037/042**；不得以 dogfood 代替外部结论。

FEAT-008 contributes the *telemetry* portion. It **does not** close RISK-037/042: REL-061's acceptance is explicit that closure requires VAL-008 (dogfood) + VAL-009 (two external project types) external evidence AND the runtime gates, after which the risks are *re-evaluated*. FEAT-008 delivers measurement; VAL-008/009 deliver proof. Conflating them is exactly the "以 dogfood 代替外部结论" REL-061 forbids.

### 8.2 Tests that prove FEAT-008 computes correctly (the honesty contract)

The load-bearing tests. Each constructs a **known event sequence** and asserts exact results — proving both correctness AND the unknown-when-insufficient rule.

1. **`test_known_sequence_compute_exact_metrics`** — the canonical fixture test. Construct a deterministic event list (e.g., 3 units: unit A `phase_enter→…→loop_exit` in 2 iterations over 3600s; unit B `phase_enter→…→fuse_trip→escalation_resolved`; unit C `phase_enter→unit_withdrawn`). Assert:
   - Lead time for changes = median of {A's lead time} = A's lead time exactly (1 sample).
   - Change failure rate = (B+C) / (A+B+C) = 2/3.
   - Time to restore = B's `fuse_trip→escalation_resolved` duration exactly (1 sample).
   - Deployment frequency (unit-completion) = 1 (only A exited).
   - Cycle time distribution from A's 2 iterations.
   This is the single end-to-end numeric proof.

2. **`test_unknown_when_no_completed_units`** — empty window / no `loop_exit`. Assert every DORA metric has `status == "unknown"`, `value is None`, and a non-empty `reason`. Assert NO metric returns `0` or `0.0`.

3. **`test_unknown_when_no_resolved_fuses`** — window with `fuse_trip` but no `escalation_resolved`. Assert `time_to_restore.status == "unknown"` AND `diagnostics["open_fuse_trips"] == N` (unresolved trips are reported as a count, not imputed as MTTR=0).

4. **`test_change_failure_rate_denominator_is_units_not_loops`** — the anti-proxy test. Construct a unit that iterates 5 times then exits successfully + a unit that fuses on iteration 1. Assert CFR = 1/2 (one failure of two completed units), NOT 1/6 (which would be the `fuse_trips/total_loops` proxy). This test directly encodes the AUDIT-133 rule.

5. **`test_deployment_frequency_is_loop_exit_not_release`** — assert the metric counts `loop_exit` events, not release-gate passes. Construct events with 3 `loop_exit` and 1 release marker; assert deployment frequency = 3, and the report's `scope_note` states it is unit-completion, not release.

6. **`test_window_filtering_relative_and_explicit`** — `window="7d"` includes only the last-7-days events (relative to latest event ts); explicit `(start, end)` tuple respects boundaries; `window=None` is all-time. Same fixture, three calls, three different results.

7. **`test_purity_no_io_no_mutation`** — call `compute_metrics` twice on the same list; assert equal reports; assert no file is opened (mock/patch `open` and `pathlib.Path.read_text` to raise); assert no module-level dict is mutated.

8. **`test_malformed_timestamps_counted_not_raised`** — inject an event with a garbage timestamp; assert it is counted in `diagnostics["malformed_timestamps"]` and excluded from duration math; assert no exception.

9. **`test_legacy_dora_proxy_deprecated_not_removed`** — `loop_health.check_loop_health` result still has a DORA key (now `dora_metrics_legacy_proxy`, `deprecated=True`) AND a new `telemetry` key whose `dora` supersedes it.

10. **`test_cli_loop_telemetry_reads_event_log_and_delegates`** — invoke `cmd_loop_telemetry` against a temp event-log fixture; assert it prints a report and exits 0; assert it resolves HOST_PROJECT_ROOT (RISK-040), never PLUGIN_HOME.

### 8.3 What does NOT close in 0.69.0 (the no-overclaim boundary)

- **RISK-037 and RISK-042 remain open.** Their closure standards (risk-log: "preview/apply 同 plan hash; apply 前后 runtime validator PASS; production gate failure 持久化 back-edge/round; 重启状态保持; fuse 经生产入口触发; health authority fail-closed; 至少 dogfood+2 外部类型多 unit/multi-lane installed-state PASS; 发布叙事与证据强度一致") require external evidence VAL-008/009 deliver. Telemetry measures the runtime; it does not prove external effectiveness.
- **No claim of 1.0.0 readiness.** 1.0.0 is blocked until RISK-036 AND RISK-037 close.
- **No claim the loop engine is "production-complete".** Telemetry reports what it measures; production-completeness is a VAL-008/009 + runtime-gate conclusion.
- **No whole-software-project DORA.** The metrics are loop-unit-lifecycle-scoped (§4.1, §6.1 `scope_note`).

---

## 9. Risk + Regression Analysis

### 9.1 Existing tests that might break (and how to keep them green)

| Test file | Risk | Mitigation |
|-----------|------|------------|
| `test_loop_health.py` | **LOW-MEDIUM.** `check_loop_health` gains the optional `telemetry` key and the legacy DORA key is renamed. Tests asserting the old `dora_metrics` key name break. | Rename assertion to `dora_metrics_legacy_proxy` (the key is preserved, renamed). Add the deprecation test (§8.2 #9). The health check's blocking behavior is unchanged (telemetry is advisory). |
| `test_loop_engine_round.py` / `test_loop_rollup.py` | **NONE.** Telemetry does not touch `derive_round`, `fuse_decision`, `rollup_loop_state`, or any 0.68.0 engine function. It only reads the event log. | No change. |
| `test_loop_event_log.py` | **NONE.** Telemetry is a *consumer* of `read_events`; it does not modify the event log module, the enum, or the envelope. | No change. |
| `test_loop_runtime_claims.py` / `test_loop_runtime_claim_attestation.py` | **MEDIUM.** `loop_telemetry.py` is a new surface the claim scanner sees. Any affirmative runtime-activation claim must be classified. | The new file uses scoped-negative / planned-target wording at write time (§9.4). It describes *measurement* (true in 0.69.0) — NOT "loop engineering is production-complete" (false until VAL-008/009). The `<!-- loop-runtime-target:... -->` marker is used in this ADR. The claim policy is NOT modified. |
| `test_verify_workflow.py` (release/governance gate) | **LOW.** The `loop-telemetry` thin entry is additive; it is not wired into any blocking check. The command-dispatch table gains one row. | Existing release-gate tests are unaffected (telemetry adds no gate logic). Add the CLI test (§8.2 #10). |
| `test_flow_unit_runtime_v2.py` (0.67.0 validator) | **NONE.** Telemetry does not touch the validator or the contract. | No change. |

### 9.2 Preserving the 0.66.x / 0.67.0 / 0.68.0 containment and contract

The invariants that MUST remain true after 0.69.0:

1. **0.68.0 engine byte-identical in behavior.** `loop_paro_engine`, `loop_gate_processor`, `loop_event_log`, `loop_admission` are invoked by no one in FEAT-008 — telemetry only *reads* the log they produce. **Preserved.**
2. **The v2 contract field set unchanged.** FEAT-008 adds no contract fields, no event types, no event fields. **Preserved.**
3. **The four FX-189 pure functions stay pure.** Telemetry does not touch them. **Preserved.**
4. **Health fails closed on missing/corrupt authority.** `loop_health` FIX-196 discipline preserved; telemetry is advisory and wrapped in try/except that yields `{"status":"unavailable"}`, never a crash. **Preserved.**
5. **RISK-040 dual-root discipline.** `cmd_loop_telemetry` resolves HOST_PROJECT_ROOT via `resolve_entry`, never PLUGIN_HOME. The event log is read from `HOST_ROOT/.governance/loop-event-log.jsonl`. **Preserved.**
6. **RISK-039 thin-entry discipline.** `verify_workflow.py` gets only the thin `cmd_loop_telemetry` entry (≤20 lines). All logic is in `infra/loop_telemetry.py`. ArchGuard's module-size check must pass. **Preserved.**
7. **No-overclaim.** Telemetry never reports a proxy as a DORA metric, never returns 0 for insufficient data, never claims production-completeness. Enforced at the metric-definition layer (§4.5) and by the §8.2 tests. **Preserved.**

A dedicated regression test (`test_066x_0670_0680_containment_preserved`) runs the 0.66.x/0.67.0/0.68.0 scenarios against the 0.69.0 code and asserts the same fail-closed/byte-identical behavior.

### 9.3 Does FEAT-008 touch release-critical assets?

**No.** FEAT-008 does not modify:

- `infra/release/verify_rel063_evidence.py` or any 0.66.x release-critical evidence.
- Any release documents, tags, or manifest transitions.
- The claim scanner policy/authority (`core/loop-runtime-claim-*.json`).
- The 0.68.0 engine modules or the event-log module.

The release-critical path for 0.69.0 is REL-061, a new MINOR release. The one touch to an existing surface is `loop_health.check_loop_health` gaining an *advisory* key — additive, non-blocking, cannot fail an existing health check.

### 9.4 Loop-runtime claim scanner compliance (ADR-011/012 discipline)

All new 0.69.0 surfaces (this ADR, `loop_telemetry.py`) must comply with the claim contract at write time:

- **Scoped-negative / planned-target wording.** The new files describe *measurement* (which 0.69.0 genuinely delivers) but must NOT claim RISK-037/042 closure or 1.0.0 readiness. Wording: "telemetry computes flow/DORA metrics from the event log" (true in 0.69.0) — NOT "loop engineering effectiveness is proven" (false until VAL-008/009).
- **The `<!-- loop-runtime-target:... -->` marker** is used in this ADR (top of document). Its `status: "planned_not_active"` flips to `"active"` only after REL-061 passes and the claim scanner is updated (a separate FIX task, not FEAT-008 scope).
- **The claim policy itself is NOT modified.** Adding telemetry does not change how the scanner classifies claims; it changes what is *measured*. If any new affirmative runtime-activation claim is needed in an audited file, it goes through the existing allowlist/authority amendment process (ADR-011/012), out of scope for this ADR.

### 9.5 The main residual risks

1. **Metric-definition drift (highest risk).** The honesty rules (§4.5) are the load-bearing correctness property. If a future change re-introduces a proxy (e.g., someone "simplifies" CFR back to `fuse_trips/total_loops`), the AUDIT-133 guarantee silently breaks. Mitigation: the §8.2 #4 anti-proxy test is mandatory and fails-closed on the proxy; the §4.5 table is normative in this ADR.
2. **`unknown` vs `0` confusion at consumption.** A reader may treat `value=None` as `0`. Mitigation: every metric carries an explicit `status` field (`"measured"|"unknown"`); the CLI renders `unknown` distinctly from `0`; the JSON shape makes them structurally different (`{"status":"unknown","value":null}` vs `{"status":"measured","value":0.0}`).
3. **Event-log absence in real hosts.** Most hosts today have no `loop-event-log.jsonl` (the engine is newly active in 0.68.0; few units have run). Telemetry will report all-`unknown` for these hosts — which is the *honest* result, not a bug. Mitigation: the CLI prints a clear "no events / all metrics unknown" message; the §8.2 #2 test covers it. (This is also why VAL-008 dogfood is a separate task: it produces the events telemetry then measures.)
4. **Timestamp clock skew.** Mitigated by `(timestamp, cas_version)` sort within a unit (§5.2); cross-unit ordering does not affect any metric (all are per-unit-anchored).

---

## 10. Authorization Boundary

This ADR is **design only.** It:

- Does NOT implement code. FEAT-008 requires:
  1. A separate DEC (task dispatch) from the Coordinator.
  2. A Developer (implementation per this spec).
  3. An independent Code Reviewer (R0, with rounds per Check 30 review-chain fuse).
  4. An independent QA.
  5. For the aggregate, a Release Reviewer for REL-061 (which also covers VAL-008/009).
- Does NOT authorize a release. REL-061 requires its own release docs, version projection, and Release Review per the release workflow, and requires VAL-008 + VAL-009 external evidence.
- Does NOT close RISK-037 or RISK-042. Both remain open until VAL-008 (dogfood) + VAL-009 (two external project types) external evidence AND the runtime gates are satisfied, after which REL-061 re-evaluates them. FEAT-008 delivers measurement, not effectiveness proof.
- Does NOT claim 1.0.0 readiness. 1.0.0 remains blocked until RISK-036 AND RISK-037 close per their recorded standards.
- Does NOT modify the 0.66.x release-critical assets, the v1/v2 contract, the 0.68.0 engine, the event-log enum/fields, or the loop runtime claim scanner policy (ADR-011/012). New surfaces added by FEAT-008 comply with the existing claim contract at write time.
- Does NOT replace the whole-software-project release cadence with loop-unit DORA. The metrics are explicitly loop-unit-lifecycle-scoped (§4.1, §6.1 `scope_note`); conflating them with project release DORA is the overclaim this ADR forbids.
- Does NOT make the four FX-189 pure functions stateful, nor make `compute_metrics` stateful. Telemetry is pure (§6.2).

**Design Review scope:** the Design Reviewer reviews this ADR for (a) metric-definition correctness — do the §3/§4 definitions measure what they claim, anchored on the right events? (b) the honesty rule — does §4.5 + the unknown-when-insufficient rule (§3.4/§4/§5.1) actually prevent every proxy AUDIT-133 forbids? Is "unknown" structurally distinct from "0"? (c) purity — is §6.2's no-IO/no-mutation contract enforceable and tested (§8.2 #7)? (d) windowing correctness — does §5 filter without extrapolation or cross-boundary merge? (e) the deprecation discipline — is the legacy proxy demoted, not deleted (§7.3)? (f) regression risk to 0.66.x/0.67.0/0.68.0 (§9); (g) whether the §8.2 tests actually prove the honesty contract (especially #2, #3, #4, #5 — the anti-proxy and unknown-rule tests). On APPROVAL_WITH_NOTES with `unresolved_blockers=0`, the Coordinator may dispatch FEAT-008 with its own execution packet and review chain.

**Authority:** DEC-104 (binding roadmap), AUDIT-133 / EVD-707 (the honesty requirement this addresses — "缺数据返回 unknown，不以 release count/fuse ratio 冒充完整 DORA"), ADR-014 §5 (the 0.68.0 event log this builds on), ADR-013 (0.67.0 contract foundation), RISK-037 / RISK-042 (open risks; 0.69.0 *delivers telemetry but does not close them*), ADR-011/012 (the claim-correction boundary this must respect).

---

## Appendix A: The honesty contract (quick reference for the Design Reviewer)

The single sentence that FEAT-008 must satisfy: **every metric is either a real number measured from defined events, or `unknown` with a reason — never a proxy, never a fabricated zero.**

| Metric | Real definition (event anchors) | unknown when | Forbidden proxy (AUDIT-133) |
|--------|---------------------------------|--------------|------------------------------|
| Cycle time | round-start → round-end | <1 completed iteration | — |
| Lead time (flow) | first `phase_enter` → `loop_exit` | <1 exited unit | — |
| Iteration count | `loop_count` at terminal | <1 terminal event | — |
| Back-edge frequency | `back_edge` / unit / window | empty window | `phase_enter` count |
| **Deployment frequency** | `loop_exit` / window | 0 `loop_exit` | release-gate passes, commit count |
| **Lead time for changes** | median/p90 `phase_enter→loop_exit` | <1 completed pair | first-commit-to-merge |
| **Change failure rate** | (fuse_trip+withdrawn) / terminal events | 0 terminal events | **fuse_trips / total_loops** |
| **Time to restore/escalate** | median/p90 `fuse_trip→escalation_resolved` | 0 resolved fuses | fuse-to-withdraw, escalate count |

The bolded DORA rows are the four whose forbidden-proxy column is the exact substitution `loop_health._compute_dora_metrics` performs today. FEAT-008 replaces them; §8.2 #4/#5 encode the replacement as fail-closed tests.

## Appendix B: File/store reference (for the implementer)

| Artifact | Path | Role in 0.69.0 |
|----------|------|----------------|
| Event log (telemetry source) | `HOST_ROOT/.governance/loop-event-log.jsonl` | Read-only input. Produced by 0.68.0. The only telemetry data source. |
| Telemetry module | `PLUGIN_HOME/infra/loop_telemetry.py` | **NEW (FEAT-008).** Pure metrics computation. |
| Loop health (existing) | `PLUGIN_HOME/infra/loop_health.py` | Gains advisory `telemetry` key; legacy `_compute_dora_metrics` demoted to `dora_metrics_legacy_proxy`. |
| verify_workflow (thin entry) | `PLUGIN_HOME/infra/verify_workflow.py` | **NEW thin entry** `cmd_loop_telemetry` (≤20 lines) + one dispatch-table row. |
| v2 runtime payload | `HOST_ROOT/.governance/flow-unit-runtime.json` | NOT read by telemetry (event log is the source). |
| 0.68.0 engine modules | `PLUGIN_HOME/infra/loop_paro_engine.py`, `loop_gate_processor.py`, `loop_event_log.py`, `loop_admission.py` | Unchanged. Telemetry depends only on `loop_event_log` (event shape + `read_events`). |

`PLUGIN_HOME = skills/software-project-governance/`. `HOST_ROOT` is resolved via `resolve_entry.resolve_host_root` (RISK-040: never `PLUGIN_HOME`).
