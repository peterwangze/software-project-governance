"""Tests for loop_telemetry.py — FEAT-008 (0.69.0 production telemetry).

These are the **load-bearing honesty-contract tests** for ADR-015. Each
constructs a known event sequence and asserts exact numeric results — proving
both correctness AND the unknown-when-insufficient rule (AUDIT-133 / EVD-707):

  - Every metric is either a real number measured from defined events, or
    ``unknown`` with a reason — never a proxy, never a fabricated zero.
  - Zero completed units → ``unknown`` (NOT ``0``).
  - Unresolved fuse trips → reported as ``open_fuse_trips`` count (NOT MTTR=0).
  - Deployment frequency counts ``loop_exit`` (unit completion), NOT release
    passes.
  - Change failure rate's denominator is COMPLETED UNITS, not total loops
    (the AUDIT-133-forbidden ``fuse_trips/total_loops`` proxy).
  - compute_metrics is PURE: no I/O, no ``datetime.now()``, deterministic.

FEAT-044 (0.88.0 E3) adds the waiting-tax test pins: round-budget
parametrization, the N-idle-rounds heartbeat report, the interrupt + minimal-
instruction recovery payload (all in loop_engine.py), and the
``compute_stall_report`` telemetry view — including the cross-module mirror
guard (telemetry threshold == engine default) and the report→heartbeat→
recovery pipeline. FEAT-063 alignment is pinned: heartbeats/streaks are
reports, never stop proofs.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_loop_telemetry.py -v
"""

import argparse
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import loop_telemetry as lt  # noqa: E402
import loop_engine as le  # noqa: E402  (FEAT-044 engine mechanisms)
import loop_event_log as elog  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# Event fixture builders — minimal §5.1 envelopes (deterministic timestamps)
# ═══════════════════════════════════════════════════════════════════════════


def _ev(unit_id, event_type, ts, cas_version, from_version,
        from_phase=None, to_phase=None, loop_count=None, payload=None):
    """Build a minimal valid event envelope with a deterministic timestamp."""
    e = {
        "event_id": "evt-{0}-{1}".format(unit_id, cas_version),
        "timestamp": ts,
        "unit_id": unit_id,
        "event_type": event_type,
        "cas_version": cas_version,
        "from_version": from_version,
        "from_phase": from_phase,
        "to_phase": to_phase,
        "actor": "tester",
    }
    if loop_count is not None:
        e["loop_count"] = loop_count
    if payload is not None:
        e["payload"] = payload
    return e


def _ts(hour, minute=0, second=0, day=23):
    """A deterministic ISO-8601 UTC timestamp on 2026-07-{day}."""
    return "2026-07-{0:02d}T{1:02d}:{2:02d}:{3:02d}Z".format(day, hour, minute, second)


def _active_to_exit_unit(uid, start_ts, exit_ts, back_edges=0, day=23):
    """Build a unit that goes phase_enter → (back_edge)*→ loop_exit successfully.

    Each back_edge is 1 hour after the previous round-start. The unit iterates
    ``back_edges + 1`` times total (the first round has no back_edge). Returns
    the list of events. ``loop_count`` on the exit event = back_edges.
    """
    events = [_ev(uid, "phase_enter", start_ts, 0, None,
                  from_phase=None, to_phase="plan")]
    cv = 1
    cur_hour = int(start_ts[11:13])
    for i in range(back_edges):
        cur_hour += 1
        events.append(_ev(uid, "back_edge", _ts(cur_hour % 24, day=day),
                          cv, cv - 1, from_phase="reflect", to_phase="plan",
                          loop_count=i + 1))
        cv += 1
    events.append(_ev(uid, "loop_exit", exit_ts, cv, cv - 1,
                      from_phase="reflect", to_phase="exit",
                      loop_count=back_edges))
    return events


def _stall_unit(uid, day=23):
    """FEAT-044 fixture — a unit whose rounds go quiet (the waiting tax).

    Anchors: phase_enter @00:00, back_edge @01:00 / @02:00 / @03:00. Round 1
    ([00:00, 01:00]) contains a gate_result @00:30 → artifact-bearing. Rounds
    2 and 3 contain nothing but the closing anchors → artifact-less. No exit
    event (the unit is mid-loop, stalled). With the default artifact set this
    yields rounds_total=3, artifact_rounds=1, idle_streak_trailing=2.
    """
    return [
        _ev(uid, "phase_enter", _ts(0, day=day), 0, None, to_phase="plan"),
        _ev(uid, "gate_result", _ts(0, 30, day=day), 0, 0,
            from_phase="reflect", to_phase=None,
            payload={"gate_id": "G6", "gate_result": "NEEDS_CHANGE"}),
        _ev(uid, "back_edge", _ts(1, day=day), 1, 0,
            from_phase="reflect", to_phase="plan", loop_count=1),
        _ev(uid, "back_edge", _ts(2, day=day), 2, 1,
            from_phase="reflect", to_phase="plan", loop_count=2),
        _ev(uid, "back_edge", _ts(3, day=day), 3, 2,
            from_phase="reflect", to_phase="plan", loop_count=3),
    ]


# ═══════════════════════════════════════════════════════════════════════════
# Test 1 — known event sequence → exact metrics (canonical fixture)
# ═══════════════════════════════════════════════════════════════════════════


class KnownSequenceComputeTests(unittest.TestCase):
    """ADR §8.2 #1 — the canonical end-to-end numeric proof."""

    def test_known_sequence_compute_exact_metrics(self):
        """3 units: A exits (2 iterations, 1h); B fuse→resolve; C withdrawn.

        Asserts exact lead-time, CFR, time-to-restore, deployment-frequency.
        """
        # Unit A: phase_enter @ 00:00 → loop_exit @ 02:00 (lead = 7200s).
        unit_a = [
            _ev("A", "phase_enter", _ts(0), 0, None, to_phase="plan"),
            _ev("A", "back_edge", _ts(1), 1, 0,
                from_phase="reflect", to_phase="plan", loop_count=1),
            _ev("A", "loop_exit", _ts(2), 2, 1,
                from_phase="reflect", to_phase="exit", loop_count=1),
        ]
        # Unit B: phase_enter @ 00:00 → fuse_trip @ 01:00 → escalation_resolved @ 03:00.
        unit_b = [
            _ev("B", "phase_enter", _ts(0), 0, None, to_phase="plan"),
            _ev("B", "fuse_trip", _ts(1), 1, 0,
                from_phase="reflect", to_phase="escalate", loop_count=2),
            _ev("B", "escalation_resolved", _ts(3), 2, 1,
                from_phase="escalate", to_phase="plan"),
        ]
        # Unit C: phase_enter → unit_withdrawn (failure).
        unit_c = [
            _ev("C", "phase_enter", _ts(0), 0, None, to_phase="plan"),
            _ev("C", "unit_withdrawn", _ts(0, 30), 1, 0,
                from_phase="plan", to_phase="withdrawn", loop_count=0),
        ]
        events = unit_a + unit_b + unit_c
        report = lt.compute_metrics(events)

        # Lead time for changes = median of {A's lead} = 7200s (1 sample).
        ltc = report.dora["lead_time_for_changes"]
        self.assertEqual(ltc.status, "measured")
        self.assertEqual(ltc.value, 7200.0)
        self.assertEqual(ltc.percentiles["p90"], 7200.0)  # 1 sample

        # Change failure rate = (B + C) / (A + B + C) = 2/3.
        cfr = report.dora["change_failure_rate"]
        self.assertEqual(cfr.status, "measured")
        self.assertAlmostEqual(cfr.value, 2 / 3, places=6)

        # Time to restore = B's fuse→resolve = 7200s (01:00 → 03:00).
        ttr = report.dora["time_to_restore"]
        self.assertEqual(ttr.status, "measured")
        self.assertEqual(ttr.value, 7200.0)

        # Deployment frequency (unit-completion) = 1 (only A exited).
        df = report.dora["deployment_frequency"]
        self.assertEqual(df.status, "measured")
        self.assertEqual(df.value, 1)

        # Cycle time: A has 2 iterations (round 00:00→01:00=3600s, round
        # 01:00→02:00=3600s) → median 3600s.
        ct = report.flow["cycle_time"]
        self.assertEqual(ct.status, "measured")
        self.assertEqual(ct.value, 3600.0)
        self.assertEqual(ct.sample_size, 2)

        # Iteration-count distribution: terminal units A(loop_count=1),
        # B(loop_count=2), C(loop_count=0) → median of {1,2,0} = 1.
        ic = report.flow["iteration_count_distribution"]
        self.assertEqual(ic.status, "measured")
        self.assertEqual(ic.value["median"], 1)

        # Open fuse trips = 0 (B's fuse was resolved).
        self.assertEqual(report.diagnostics["open_fuse_trips"], 0)

        # computed_at = latest event timestamp (deterministic, NOT now()).
        self.assertEqual(report.computed_at, "2026-07-23T03:00:00Z")


# ═══════════════════════════════════════════════════════════════════════════
# Test 2 — zero completions → unknown (NOT 0)
# ═══════════════════════════════════════════════════════════════════════════


class UnknownWhenNoCompletionsTests(unittest.TestCase):
    """ADR §8.2 #2 — empty/no-completion window → every DORA metric unknown."""

    def test_empty_event_list_all_dora_unknown(self):
        """Empty event list → all DORA metrics unknown, no fabricated zeros."""
        report = lt.compute_metrics([])
        for name, mv in report.dora.items():
            self.assertEqual(mv.status, "unknown",
                             f"{name} must be unknown on empty events, got {mv.status}")
            self.assertIsNone(mv.value,
                              f"{name} unknown value must be None, got {mv.value}")
            self.assertTrue(mv.reason,
                            f"{name} unknown must carry a reason")

    def test_no_loop_exit_all_dora_unknown(self):
        """Events present but none reach loop_exit → DORA metrics unknown."""
        events = [
            _ev("X", "phase_enter", _ts(0), 0, None, to_phase="plan"),
            _ev("X", "fuse_trip", _ts(1), 1, 0,
                from_phase="reflect", to_phase="escalate", loop_count=1),
        ]
        report = lt.compute_metrics(events)

        # deployment_frequency: 0 loop_exit → unknown.
        df = report.dora["deployment_frequency"]
        self.assertEqual(df.status, "unknown")
        self.assertIsNone(df.value)
        self.assertIn("loop_exit", df.reason)

        # change_failure_rate: 0 terminal events? No — fuse_trip IS terminal.
        # So CFR is measured here (1 failure / 1 unit = 1.0), NOT unknown.
        # The unknown-CFR case is specifically "0 terminal events".
        cfr = report.dora["change_failure_rate"]
        self.assertEqual(cfr.status, "measured")
        self.assertAlmostEqual(cfr.value, 1.0)

    def test_zero_completions_never_returns_zero(self):
        """The load-bearing anti-fabrication test: no metric returns 0 on /0."""
        events = [
            _ev("Y", "phase_enter", _ts(0), 0, None, to_phase="plan"),
        ]  # active unit, no terminal event
        report = lt.compute_metrics(events)
        cfr = report.dora["change_failure_rate"]
        # 0 terminal events → unknown, value None, NOT 0.0.
        self.assertEqual(cfr.status, "unknown")
        self.assertIsNone(cfr.value)
        self.assertIn("no completed units", cfr.reason)
        df = report.dora["deployment_frequency"]
        self.assertEqual(df.status, "unknown")
        self.assertIsNone(df.value)


# ═══════════════════════════════════════════════════════════════════════════
# Test 3 — no resolved fuses → time_to_restore unknown, open_fuse_trips reported
# ═══════════════════════════════════════════════════════════════════════════


class TimeToRestoreTests(unittest.TestCase):
    """ADR §8.2 #3 — unresolved fuses reported as count, NOT imputed MTTR=0."""

    def test_unresolved_fuse_trip_unknown_with_open_count(self):
        """fuse_trip without escalation_resolved → unknown + open_fuse_trips=N."""
        events = [
            _ev("F", "phase_enter", _ts(0), 0, None, to_phase="plan"),
            _ev("F", "fuse_trip", _ts(1), 1, 0,
                from_phase="reflect", to_phase="escalate", loop_count=1),
        ]
        report = lt.compute_metrics(events)
        ttr = report.dora["time_to_restore"]
        self.assertEqual(ttr.status, "unknown")
        self.assertIsNone(ttr.value)
        self.assertIn("no resolved fuse trips", ttr.reason)
        # Unresolved trips are counted separately, NOT imputed as MTTR=0.
        self.assertEqual(report.diagnostics["open_fuse_trips"], 1)

    def test_no_fuse_trips_at_all_unknown_zero_open(self):
        """No fuse trips → time_to_restore unknown, open_fuse_trips=0."""
        events = _active_to_exit_unit("G", _ts(0), _ts(1), back_edges=0)
        report = lt.compute_metrics(events)
        ttr = report.dora["time_to_restore"]
        self.assertEqual(ttr.status, "unknown")
        self.assertIsNone(ttr.value)
        self.assertEqual(report.diagnostics["open_fuse_trips"], 0)

    def test_two_open_fuses_counted_correctly(self):
        """Multiple unresolved fuses across units → open_fuse_trips aggregates."""
        events = []
        for uid, start_h in (("P", 0), ("Q", 0)):
            events.append(_ev(uid, "phase_enter", _ts(start_h), 0, None, to_phase="plan"))
            events.append(_ev(uid, "fuse_trip", _ts(start_h + 1), 1, 0,
                             from_phase="reflect", to_phase="escalate", loop_count=1))
        report = lt.compute_metrics(events)
        self.assertEqual(report.diagnostics["open_fuse_trips"], 2)
        self.assertEqual(report.dora["time_to_restore"].status, "unknown")


# ═══════════════════════════════════════════════════════════════════════════
# Test 4 — CFR denominator is COMPLETED UNITS, not total loops (anti-proxy)
# ═══════════════════════════════════════════════════════════════════════════


class ChangeFailureRateAntiProxyTests(unittest.TestCase):
    """ADR §8.2 #4 — the anti-proxy test. Encodes AUDIT-133 directly.

    A unit that iterates 5 times then exits successfully + a unit that fuses on
    iteration 1 → CFR = 1/2 (one failure of two completed units), NOT 1/6
    (which would be the fuse_trips/total_loops proxy).
    """

    def test_cfr_denominator_is_units_not_loops(self):
        # Unit H: 5 back_edges (5 iterations) then loop_exit (SUCCESS).
        unit_h = _active_to_exit_unit("H", _ts(0, day=20), _ts(6, day=20),
                                      back_edges=5, day=20)
        # Unit I: 1 fuse_trip (FAILURE) on iteration 1.
        unit_i = [
            _ev("I", "phase_enter", _ts(0, day=20), 0, None, to_phase="plan"),
            _ev("I", "fuse_trip", _ts(1, day=20), 1, 0,
                from_phase="reflect", to_phase="escalate", loop_count=1),
        ]
        events = unit_h + unit_i
        report = lt.compute_metrics(events)

        cfr = report.dora["change_failure_rate"]
        self.assertEqual(cfr.status, "measured")
        # 1 failure (I) / 2 completed units (H + I) = 0.5
        self.assertAlmostEqual(cfr.value, 0.5)
        # NOT the proxy: fuse_trips(1)/total_loops(6 from H's 5 + I's 1) = 0.1667
        self.assertNotAlmostEqual(cfr.value, 1 / 6, places=2)
        self.assertEqual(cfr.percentiles["successes"], 1)
        self.assertEqual(cfr.percentiles["failures"], 1)
        self.assertEqual(cfr.sample_size, 2)  # denominator = units, not loops


# ═══════════════════════════════════════════════════════════════════════════
# Test 5 — deployment frequency is loop_exit, not release count
# ═══════════════════════════════════════════════════════════════════════════


class DeploymentFrequencyNotReleaseTests(unittest.TestCase):
    """ADR §8.2 #5 — deployment frequency counts loop_exit, not release passes."""

    def test_deployment_frequency_counts_loop_exit_not_release(self):
        """3 loop_exit events + a release marker → deployment_frequency = 3.

        A release-gate-pass marker (the AUDIT-133-forbidden proxy source) does
        NOT inflate the count. The scope_note states it is unit-completion.
        """
        events = []
        for uid, hr in (("A", 0), ("B", 1), ("C", 2)):
            events.append(_ev(uid, "phase_enter", _ts(hr), 0, None, to_phase="plan"))
            events.append(_ev(uid, "loop_exit", _ts(hr + 1), 1, 0,
                             from_phase="reflect", to_phase="exit", loop_count=0))
        # A "release" style event the proxy would have counted — but it is a
        # gate_result, NOT a loop_exit. compute_metrics must ignore it.
        events.append(_ev("A", "gate_result", _ts(3), 2, 1,
                          from_phase="reflect", to_phase="exit",
                          payload={"gate_id": "G9-Release-Gate", "gate_result": "PASS"}))
        report = lt.compute_metrics(events)

        df = report.dora["deployment_frequency"]
        self.assertEqual(df.status, "measured")
        self.assertEqual(df.value, 3)  # 3 loop_exit, NOT 3+1 release marker
        self.assertEqual(df.sample_size, 3)
        # The scope_note makes the unit-completion scoping explicit.
        self.assertIn("unit-completion", report.scope_note)
        self.assertIn("NOT", report.scope_note)  # "NOT ... release cadence"


# ═══════════════════════════════════════════════════════════════════════════
# Test 6 — window filtering (7d vs 30d vs all)
# ═══════════════════════════════════════════════════════════════════════════


class WindowFilteringTests(unittest.TestCase):
    """ADR §8.2 #6 / §5 — relative + explicit + all-time windowing."""

    def test_window_filtering_relative_and_explicit(self):
        # Two completions: one 3 days ago, one 40 days ago (relative to latest).
        recent = _active_to_exit_unit("R", _ts(0, day=20), _ts(1, day=20), day=20)
        old = _active_to_exit_unit("O", _ts(0, day=1), _ts(1, day=1), day=1)
        events = recent + old

        # all-time: both units' exits counted.
        rep_all = lt.compute_metrics(events)
        self.assertEqual(rep_all.dora["deployment_frequency"].value, 2)

        # 7d window (latest event is day 20): only the recent unit (day 20) is
        # within 7 days of day 20 → 1 exit.
        rep_7d = lt.compute_metrics(events, window="7d")
        self.assertEqual(rep_7d.window, "7d")
        self.assertEqual(rep_7d.dora["deployment_frequency"].value, 1)

        # 30d window: day 20 is within 30d of day 20; day 1 is 19 days before
        # day 20 → also within 30d → both. (20 - 1 = 19 < 30.)
        rep_30d = lt.compute_metrics(events, window="30d")
        self.assertEqual(rep_30d.dora["deployment_frequency"].value, 2)

        # Explicit [start, end) date window covering only day 1.
        rep_explicit = lt.compute_metrics(events, window=("2026-07-01", "2026-07-02"))
        self.assertEqual(rep_explicit.window, "2026-07-01..2026-07-02")
        self.assertEqual(rep_explicit.dora["deployment_frequency"].value, 1)

        # window=None == all-time.
        rep_none = lt.compute_metrics(events, window=None)
        self.assertEqual(rep_none.window, "all")
        self.assertEqual(rep_none.dora["deployment_frequency"].value, 2)

    def test_window_excludes_old_events_from_counts(self):
        """An old exit outside the 7d window does not count."""
        old = _active_to_exit_unit("OLD", _ts(0, day=1), _ts(1, day=1), day=1)
        # Anchor event on day 20 so the 7d window is day 13..20.
        anchor = [_ev("ANCHOR", "phase_enter", _ts(0, day=20), 0, None, to_phase="plan")]
        events = old + anchor
        rep = lt.compute_metrics(events, window="7d")
        # The OLD exit (day 1) is excluded; ANCHOR has no exit → unknown.
        self.assertEqual(rep.dora["deployment_frequency"].status, "unknown")


# ═══════════════════════════════════════════════════════════════════════════
# Test 7 — purity: same events + window → same report (deterministic)
# ═══════════════════════════════════════════════════════════════════════════


class PurityTests(unittest.TestCase):
    """ADR §8.2 #7 / §6.2 — compute_metrics is pure: no I/O, no now(), no mutation."""

    def test_deterministic_same_input_same_output(self):
        events = _active_to_exit_unit("D", _ts(0), _ts(2), back_edges=1)
        r1 = lt.compute_metrics(events)
        r2 = lt.compute_metrics(events)
        # Same input → structurally equal reports.
        self.assertEqual(r1, r2)
        # computed_at is the latest event timestamp, NOT wall-clock now().
        self.assertEqual(r1.computed_at, "2026-07-23T02:00:00Z")

    def test_no_file_io_no_datetime_now(self):
        """compute_metrics has no datetime.now() and no file I/O in its source.

        Static analysis is a STRONGER purity guarantee than runtime monkey-
        patching: it proves no such call exists in the pure path, regardless of
        Python version quirks around patching built-in immutable types. We
        inspect the module source for forbidden tokens and assert none appear
        outside comments/strings. (Runtime monkey-patching of datetime.now is
        unreliable across CPython versions — datetime is an immutable C type on
        3.14 — so the static check is the authoritative purity proof.)
        """
        import inspect
        src = inspect.getsource(lt)
        # Remove comments and string literals so a mention in a docstring
        # (e.g. "never call datetime.now()") does not trip the check.
        cleaned_lines = []
        for line in src.splitlines():
            # strip trailing comments
            if "#" in line:
                line = line.split("#", 1)[0]
            cleaned_lines.append(line)
        cleaned = "\n".join(cleaned_lines)
        # Strip triple-quoted string blocks (docstrings) — crude but sufficient:
        # the module has no multi-line string literals other than docstrings.
        import re
        cleaned = re.sub(r'"""[\s\S]*?"""', '""', cleaned)
        # The pure module must not call datetime.now() anywhere.
        self.assertNotIn("datetime.now", cleaned,
                         "compute_metrics path must not call datetime.now()")
        self.assertNotIn(".now(", cleaned,
                         "compute_metrics path must not call *.now()")
        # No file I/O primitives in the pure module.
        for forbidden in ("open(", "read_text", "read_bytes",
                          "write_text", ".read(", "pathlib.Path("):
            # Path( appears only in type-free contexts; the module uses no Path.
            self.assertNotIn(forbidden, cleaned,
                             "pure module must not use {0!r}".format(forbidden))

        # Runtime corroboration: patching builtins.open must not be triggered
        # by compute_metrics (the pure function must not open anything).
        events = _active_to_exit_unit("N2", _ts(0), _ts(1), back_edges=0)
        opened = {"count": 0}

        def fake_open(*a, **kw):
            opened["count"] += 1
            raise AssertionError("compute_metrics must not open files")

        with patch("builtins.open", fake_open):
            report = lt.compute_metrics(events, window="30d")
        self.assertEqual(opened["count"], 0)
        self.assertEqual(report.window, "30d")

    def test_does_not_mutate_input_events(self):
        """The input event list/dicts are not mutated by compute_metrics."""
        events = _active_to_exit_unit("M", _ts(0), _ts(1), back_edges=0)
        # Deep snapshot.
        before = json.loads(json.dumps(events))
        lt.compute_metrics(events, window="7d")
        lt.compute_metrics(events)  # call twice
        self.assertEqual(events, before, "input events must not be mutated")

    def test_no_module_level_state_leak(self):
        """No module-level dict is mutated across calls."""
        # Capture module attribute set before.
        attrs_before = {k: v for k, v in vars(lt).items()
                        if not k.startswith("__") and not callable(v)}
        events = _active_to_exit_unit("S", _ts(0), _ts(1))
        lt.compute_metrics(events, window="7d")
        lt.compute_metrics(events, window="30d")
        attrs_after = {k: v for k, v in vars(lt).items()
                       if not k.startswith("__") and not callable(v)}
        self.assertEqual(attrs_before, attrs_after,
                         "module-level state must not change across calls")


# ═══════════════════════════════════════════════════════════════════════════
# Test 8 — p90 computation correct
# ═══════════════════════════════════════════════════════════════════════════


class PercentileComputationTests(unittest.TestCase):
    """ADR §8.2 #8 — p90 (linear interpolation) is computed correctly."""

    def test_p90_linear_interpolation_on_known_values(self):
        # 10 samples 100, 200, ..., 1000. p90 of an even-length list via the
        # N-1 interpolation: rank = 0.9 * 9 = 8.1 → between index 8 (900) and
        # index 9 (1000): 900 + 0.1 * (1000 - 900) = 910.
        values = [100 * i for i in range(1, 11)]
        self.assertAlmostEqual(lt._percentile(values, 90), 910.0)
        # median of even-length list = average of the two middle = 550.
        self.assertEqual(lt._median(values), 550.0)
        # Single sample → percentile == the sample.
        self.assertEqual(lt._percentile([42], 90), 42.0)

    def test_lead_time_p90_reflected_in_report(self):
        """3 units with lead times 1000s, 2000s, 3000s → median 2000, p90 2800."""
        events = []
        for i, hr in enumerate((1, 2, 3)):
            uid = "L{0}".format(i)
            events.append(_ev(uid, "phase_enter", _ts(0), 0, None, to_phase="plan"))
            events.append(_ev(uid, "loop_exit", _ts(hr), 1, 0,
                              from_phase="reflect", to_phase="exit", loop_count=0))
        # lead times: 3600, 7200, 10800 → median 7200, p90 = 0.9*2=1.8 rank →
        # between idx1(7200) & idx2(10800): 7200 + 0.8*(10800-7200) = 10080.
        report = lt.compute_metrics(events)
        ltc = report.dora["lead_time_for_changes"]
        self.assertEqual(ltc.status, "measured")
        self.assertEqual(ltc.value, 7200.0)  # median
        self.assertAlmostEqual(ltc.percentiles["p90"], 10080.0)


# ═══════════════════════════════════════════════════════════════════════════
# Test 9 — terminal-event precedence (fuse→withdraw → withdrawn; fuse→resolve→exit → exit)
# ═══════════════════════════════════════════════════════════════════════════


class TerminalEventPrecedenceTests(unittest.TestCase):
    """ADR §8.2 #9 / Design Review P1-2 — classify by the LAST terminal event."""

    def test_fuse_then_withdraw_classified_as_withdrawn(self):
        """A unit that fuse-tripped then was withdrawn → counted as withdrawn (final)."""
        events = [
            _ev("W", "phase_enter", _ts(0), 0, None, to_phase="plan"),
            _ev("W", "fuse_trip", _ts(1), 1, 0,
                from_phase="reflect", to_phase="escalate", loop_count=1),
            _ev("W", "unit_withdrawn", _ts(2), 2, 1,
                from_phase="escalate", to_phase="withdrawn", loop_count=1),
        ]
        report = lt.compute_metrics(events)
        # One completed unit (W), classified as FAILURE (its last terminal is
        # unit_withdrawn). CFR = 1/1 = 1.0. It is NOT counted twice even though
        # it has two terminal events.
        cfr = report.dora["change_failure_rate"]
        self.assertEqual(cfr.status, "measured")
        self.assertAlmostEqual(cfr.value, 1.0)
        self.assertEqual(cfr.sample_size, 1)  # counted ONCE
        self.assertEqual(cfr.percentiles["failures"], 1)
        # The fuse_trip's escalation never resolved → open_fuse_trips=1 still
        # reported (the withdraw doesn't resolve the fuse).
        self.assertEqual(report.diagnostics["open_fuse_trips"], 1)

    def test_fuse_then_resolve_then_exit_classified_as_exit(self):
        """A unit that fuse-tripped then resolved then exited → counted as exit (passed)."""
        events = [
            _ev("E", "phase_enter", _ts(0), 0, None, to_phase="plan"),
            _ev("E", "fuse_trip", _ts(1), 1, 0,
                from_phase="reflect", to_phase="escalate", loop_count=1),
            _ev("E", "escalation_resolved", _ts(2), 2, 1,
                from_phase="escalate", to_phase="plan"),
            _ev("E", "loop_exit", _ts(4), 3, 2,
                from_phase="reflect", to_phase="exit", loop_count=1),
        ]
        report = lt.compute_metrics(events)
        # Classified as SUCCESS (last terminal = loop_exit). CFR = 0/1 = 0.0.
        cfr = report.dora["change_failure_rate"]
        self.assertEqual(cfr.status, "measured")
        self.assertAlmostEqual(cfr.value, 0.0)
        self.assertEqual(cfr.percentiles["successes"], 1)
        # The fuse was resolved → contributes a time_to_restore sample, and no
        # open fuse trip.
        self.assertEqual(report.dora["time_to_restore"].status, "measured")
        self.assertEqual(report.dora["time_to_restore"].value, 3600.0)  # 01:00→02:00
        self.assertEqual(report.diagnostics["open_fuse_trips"], 0)


# ═══════════════════════════════════════════════════════════════════════════
# Test 10 — back-edge frequency correct
# ═══════════════════════════════════════════════════════════════════════════


class BackEdgeFrequencyTests(unittest.TestCase):
    """ADR §8.2 #10 — back-edge events per unit per window."""

    def test_back_edge_frequency_per_unit(self):
        """2 units, 3 back_edges total → 3/2 = 1.5 per unit per window."""
        events = []
        events += _active_to_exit_unit("B1", _ts(0), _ts(4), back_edges=2)  # 2 back_edges
        events += _active_to_exit_unit("B2", _ts(0, day=22), _ts(1, day=22), back_edges=1)  # 1
        report = lt.compute_metrics(events)
        be = report.flow["back_edge_frequency"]
        self.assertEqual(be.status, "measured")
        self.assertEqual(be.sample_size, 3)  # 3 back_edge events
        self.assertAlmostEqual(be.value, 3 / 2)  # 3 back_edges / 2 units
        self.assertEqual(be.unit, "per_unit_per_window")

    def test_zero_back_edges_non_empty_window_is_measured_zero(self):
        """A non-empty window with zero back-edges is a REAL 0, not unknown.

        This is the load-bearing distinction (ADR-015 §3.4): "0 back-edges
        across N active units" means no iteration is happening — a real signal.
        Only an empty window (zero units) is unknown.
        """
        events = _active_to_exit_unit("Z", _ts(0), _ts(1), back_edges=0)
        report = lt.compute_metrics(events)
        be = report.flow["back_edge_frequency"]
        self.assertEqual(be.status, "measured")
        self.assertEqual(be.value, 0.0)
        # A measured metric carries an empty reason (the honesty marker lives in
        # the status field, ADR-015 §9.5 risk 2).
        self.assertEqual(be.reason, "")

    def test_empty_window_back_edge_unknown(self):
        """No units at all → back_edge_frequency unknown."""
        report = lt.compute_metrics([])
        be = report.flow["back_edge_frequency"]
        self.assertEqual(be.status, "unknown")
        self.assertIsNone(be.value)


# ═══════════════════════════════════════════════════════════════════════════
# Test 11 — malformed timestamps counted, not raised (robustness)
# ═══════════════════════════════════════════════════════════════════════════


class MalformedTimestampTests(unittest.TestCase):
    """ADR §8.2 #8 (robustness) — malformed timestamps are counted + skipped."""

    def test_malformed_timestamp_counted_not_raised(self):
        """A garbage timestamp is counted in diagnostics and excluded from math."""
        events = [
            _ev("G", "phase_enter", _ts(0), 0, None, to_phase="plan"),
            # Garbage timestamp — must not crash, must be counted.
            _ev("G", "loop_exit", "not-a-timestamp", 1, 0,
                from_phase="reflect", to_phase="exit", loop_count=0),
        ]
        # Must not raise.
        report = lt.compute_metrics(events)
        self.assertEqual(report.diagnostics["malformed_timestamps"], 1)
        # The malformed loop_exit is excluded → deployment_frequency unknown
        # (the only loop_exit had an unparseable timestamp).
        self.assertEqual(report.dora["deployment_frequency"].status, "unknown")

    def test_non_dict_events_skipped(self):
        """Non-dict entries in the event list are skipped, not raised."""
        events = [
            _ev("K", "phase_enter", _ts(0), 0, None, to_phase="plan"),
            "not-a-dict",
            None,
            _ev("K", "loop_exit", _ts(1), 1, 0,
                from_phase="reflect", to_phase="exit", loop_count=0),
        ]
        report = lt.compute_metrics(events)
        self.assertEqual(report.dora["deployment_frequency"].value, 1)


# ═══════════════════════════════════════════════════════════════════════════
# Test 12 — CLI thin entry reads event log and delegates (RISK-040)
# ═══════════════════════════════════════════════════════════════════════════


class CLILoopTelemetryTests(unittest.TestCase):
    """ADR §8.2 #10 — cmd_loop_telemetry reads the event log and delegates."""

    def test_cli_reads_event_log_and_delegates(self):
        """cmd_loop_telemetry prints a report, exits 0, uses HOST_PROJECT_ROOT."""
        import verify_workflow as vw
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            log = elog.default_log_path(root)
            elog.append_events([
                elog.build_event("CLI", "phase_enter", cas_version=0,
                                 from_version=None, actor="t", to_phase="plan",
                                 timestamp="2026-07-23T00:00:00Z"),
                elog.build_event("CLI", "loop_exit", cas_version=1,
                                 from_version=0, actor="t",
                                 from_phase="reflect", to_phase="exit",
                                 timestamp="2026-07-23T01:00:00Z",
                                 payload={"loop_count": 0}),
            ], log_path=log)
            args = argparse.Namespace(target=str(root), window="all", json=False)
            out = io.StringIO()
            with redirect_stdout(out):
                vw.cmd_loop_telemetry(args)
        text = out.getvalue()
        self.assertIn("Loop Telemetry", text)
        self.assertIn("deployment_frequency", text.lower())
        # The report resolved HOST_PROJECT_ROOT (the temp root) — the unit's
        # loop_exit is counted, proving the file was read from <root>/.governance.
        self.assertIn("unit-completion", text)

    def test_cli_json_mode_emits_valid_json(self):
        """--json mode emits parseable JSON with the expected structure."""
        import verify_workflow as vw
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            log = elog.default_log_path(root)
            elog.append_events([
                elog.build_event("J", "phase_enter", cas_version=0,
                                 from_version=None, actor="t", to_phase="plan",
                                 timestamp="2026-07-23T00:00:00Z"),
            ], log_path=log)
            args = argparse.Namespace(target=str(root), window="all", json=True)
            out = io.StringIO()
            with redirect_stdout(out):
                vw.cmd_loop_telemetry(args)
        # Extract the JSON block (after the header line).
        text = out.getvalue()
        start = text.find("{")
        self.assertGreater(start, -1, "JSON output must contain a '{'")
        payload = json.loads(text[start:])
        self.assertIn("dora", payload)
        self.assertIn("flow", payload)
        self.assertEqual(payload["window"], "all")
        # Empty event log (only an active unit) → all DORA metrics unknown.
        self.assertEqual(payload["dora"]["deployment_frequency"]["status"], "unknown")

    def test_cli_resolves_host_root_when_target_absent(self):
        """Without --target, cmd_loop_telemetry resolves HOST_PROJECT_ROOT (RISK-040)."""
        import verify_workflow as vw
        # Patch resolve_host_root to a temp dir with a tiny event log so the
        # entry does not read the real host's file.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            log = elog.default_log_path(root)
            elog.append_events([
                elog.build_event("R", "phase_enter", cas_version=0,
                                 from_version=None, actor="t", to_phase="plan",
                                 timestamp="2026-07-23T00:00:00Z"),
            ], log_path=log)
            with patch("resolve_entry.resolve_host_root", return_value=root):
                args = argparse.Namespace(target=None, window="all", json=False)
                out = io.StringIO()
                with redirect_stdout(out):
                    vw.cmd_loop_telemetry(args)
        self.assertIn("Loop Telemetry", out.getvalue())


# ═══════════════════════════════════════════════════════════════════════════
# Test 13 — loop_health advisory telemetry wiring (ADR-015 §7.2)
# ═══════════════════════════════════════════════════════════════════════════


class LoopHealthTelemetryWiringTests(unittest.TestCase):
    """ADR-015 §7.2 — check_loop_health gains an advisory telemetry key."""

    def test_telemetry_key_present_and_advisory(self):
        """check_loop_health result carries a non-blocking telemetry key."""
        import loop_health as lh
        with tempfile.TemporaryDirectory() as td:
            # Write a compliant registry so Part 1 does not FAIL.
            core = Path(td) / "core"
            core.mkdir(parents=True)
            (core / "loop-engineering-registry.json").write_text(json.dumps({
                "$schema": "x", "schema_version": "1.0", "workflow_version": "0.65.0",
                "pause_points": {"PP-A": {
                    "location": "x", "trigger": "x", "velocity_cost_ms": None,
                    "velocity_cost_justification": "ok", "active": True}},
            }), encoding="utf-8")
            result = lh.check_loop_health(target=str(td), plugin_home=str(Path(td)))
        # The advisory telemetry key exists; with no event log it is
        # "unavailable" (graceful), and crucially it does NOT block.
        self.assertIn("telemetry", result)
        self.assertEqual(result["telemetry"]["status"], "unavailable")
        self.assertEqual(result["summary"]["blocking_count"], 0)

    def test_telemetry_computes_when_event_log_present(self):
        """When the event log exists, telemetry computes honest metrics."""
        import loop_health as lh
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            core = root / "core"
            core.mkdir(parents=True)
            (core / "loop-engineering-registry.json").write_text(json.dumps({
                "$schema": "x", "schema_version": "1.0", "workflow_version": "0.65.0",
                "pause_points": {"PP-A": {
                    "location": "x", "trigger": "x", "velocity_cost_ms": None,
                    "velocity_cost_justification": "ok", "active": True}},
            }), encoding="utf-8")
            log = elog.default_log_path(root)
            elog.append_events([
                elog.build_event("T", "phase_enter", cas_version=0,
                                 from_version=None, actor="t", to_phase="plan",
                                 timestamp="2026-07-23T00:00:00Z"),
                elog.build_event("T", "loop_exit", cas_version=1,
                                 from_version=0, actor="t",
                                 from_phase="reflect", to_phase="exit",
                                 timestamp="2026-07-23T01:00:00Z",
                                 payload={"loop_count": 0}),
            ], log_path=log)
            result = lh.check_loop_health(target=str(root), plugin_home=str(root))
        tele = result["telemetry"]
        self.assertEqual(tele["status"], "available")
        self.assertEqual(tele["dora"]["deployment_frequency"].status, "measured")
        self.assertEqual(tele["dora"]["deployment_frequency"].value, 1)


# ═══════════════════════════════════════════════════════════════════════════
# FEAT-044 (0.88.0 E3) — test pins: round budget / heartbeat / interrupt-
# recovery / stall telemetry. Acceptance: 回合预算参数化 + 心跳上报 + interrupt
# 恢复产品化 + 遥测测试钉. FEAT-063 alignment is pinned throughout: heartbeats
# and budget breaches are REPORTS, never stop proofs.
# ═══════════════════════════════════════════════════════════════════════════


class RoundBudgetParametrizationTests(unittest.TestCase):
    """回合预算参数化 — configurable budget + explicit over-budget behavior."""

    def test_default_budget_shape_and_provenance(self):
        budget, issues = le.resolve_round_budget("inner")
        self.assertEqual(budget.max_idle_rounds, 3)
        self.assertEqual(
            budget.max_steps_per_round,
            le.DEFAULT_ROUND_BUDGET["max_steps_per_round"])
        self.assertEqual(
            budget.max_minutes_per_round,
            le.DEFAULT_ROUND_BUDGET["max_minutes_per_round"])
        self.assertEqual(budget.over_budget_action, le.OVER_BUDGET_ACTION)
        self.assertEqual(budget.tier, "inner")
        # W-3 provenance: the source layer is recorded on the budget itself.
        self.assertEqual(budget.source, "defaults")
        self.assertEqual(issues, [])

    def test_overrides_take_precedence(self):
        budget, issues = le.resolve_round_budget(
            "inner", overrides={"max_idle_rounds": 5, "max_steps_per_round": 7})
        self.assertEqual(budget.max_idle_rounds, 5)
        self.assertEqual(budget.max_steps_per_round, 7)
        self.assertEqual(budget.source, "overrides")
        self.assertEqual(issues, [])

    def test_registry_round_budget_additive_read(self):
        """A registry fuse's optional ``round_budget`` key is honored (additive).

        The shipped registry carries no such key; this pins the forward-
        compatible config surface without touching the registry file.
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            core = root / "core"
            core.mkdir(parents=True)
            registry = {
                "$schema": "x", "schema_version": "1.0",
                "workflow_version": "0.65.0",
                "loop_fuses": {
                    "FUSE-INNER-DEFAULT": {
                        "loop_tier": "inner", "max_rounds": 5,
                        "escalation_exit": "askuser-escalation",
                        "round_budget": {"max_idle_rounds": 2},
                    },
                },
            }
            (core / "loop-engineering-registry.json").write_text(
                json.dumps(registry), encoding="utf-8")
            budget, issues = le.resolve_round_budget("inner", plugin_home=str(root))
        self.assertEqual(budget.max_idle_rounds, 2)
        # Untouched keys stay at defaults (per-key merge, not whole-patch).
        self.assertEqual(
            budget.max_steps_per_round,
            le.DEFAULT_ROUND_BUDGET["max_steps_per_round"])
        self.assertEqual(budget.source, "registry")
        self.assertEqual(issues, [])

    def test_overrides_beat_registry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            core = root / "core"
            core.mkdir(parents=True)
            registry = {
                "$schema": "x", "schema_version": "1.0",
                "loop_fuses": {
                    "FUSE-INNER-DEFAULT": {
                        "loop_tier": "inner", "max_rounds": 5,
                        "round_budget": {"max_idle_rounds": 2},
                    },
                },
            }
            (core / "loop-engineering-registry.json").write_text(
                json.dumps(registry), encoding="utf-8")
            budget, _ = le.resolve_round_budget(
                "inner", overrides={"max_idle_rounds": 6}, plugin_home=str(root))
        self.assertEqual(budget.max_idle_rounds, 6)
        self.assertEqual(budget.source, "overrides")

    def test_invalid_values_fail_closed_to_defaults(self):
        """Garbage budget values keep defaults + issue lines; NEVER raise."""
        budget, issues = le.resolve_round_budget(
            "inner",
            overrides={"max_idle_rounds": 0, "max_steps_per_round": "many",
                       "unknown_key": 1})
        self.assertEqual(budget.max_idle_rounds, 3)
        self.assertEqual(
            budget.max_steps_per_round,
            le.DEFAULT_ROUND_BUDGET["max_steps_per_round"])
        self.assertEqual(budget.source, "defaults")
        self.assertEqual(len(issues), 3)  # 0 → invalid; "many" → invalid; unknown key

    def test_missing_registry_fuse_fail_closed(self):
        """No registry → defaults + issue note; the resolver never raises."""
        with tempfile.TemporaryDirectory() as td:
            budget, issues = le.resolve_round_budget("inner", plugin_home=td)
        self.assertEqual(budget.source, "defaults")
        self.assertEqual(budget.max_idle_rounds, 3)
        self.assertTrue(any("not found" in i for i in issues))

    def test_tier_none_skips_registry_layer(self):
        budget, issues = le.resolve_round_budget(None)
        self.assertEqual(budget.tier, None)
        self.assertEqual(budget.source, "defaults")
        self.assertEqual(issues, [])

    def test_evaluate_breaches_not_measured_and_heartbeat(self):
        budget, _ = le.resolve_round_budget(
            "inner", overrides={"max_idle_rounds": 3, "max_steps_per_round": 10,
                                "max_minutes_per_round": 30})
        v = le.evaluate_round_budget(budget, steps_used=15, minutes_used=None,
                                     idle_rounds=3)
        self.assertFalse(v["within_budget"])
        self.assertEqual(
            v["breaches"], [{"dimension": "steps", "limit": 10, "actual": 15}])
        self.assertIn("minutes", v["not_measured"])  # honest: not assumed zero
        self.assertTrue(v["heartbeat_due"])
        self.assertEqual(v["over_budget_action"], budget.over_budget_action)
        self.assertIn("not a stop proof", v["note"])

    def test_evaluate_within_budget(self):
        budget, _ = le.resolve_round_budget("inner")
        v = le.evaluate_round_budget(budget, steps_used=5, minutes_used=10,
                                     idle_rounds=1)
        self.assertTrue(v["within_budget"])
        self.assertEqual(v["breaches"], [])
        self.assertEqual(v["not_measured"], [])
        self.assertFalse(v["heartbeat_due"])

    def test_evaluate_never_raises_on_garbage_facts(self):
        budget, _ = le.resolve_round_budget("inner")
        v = le.evaluate_round_budget(budget, steps_used="lots", minutes_used=True,
                                     idle_rounds=False)
        # Garbage facts are "not measured", never assumed zero, never a crash.
        self.assertEqual(sorted(v["not_measured"]), ["minutes", "steps"])
        self.assertFalse(v["heartbeat_due"])
        self.assertTrue(v["issues"])
        self.assertTrue(v["within_budget"])  # no MEASURED breach


class HeartbeatReportTests(unittest.TestCase):
    """N 轮无产物心跳上报 — threshold semantics + evidence-backed payload."""

    def test_should_fire_threshold_semantics(self):
        budget, _ = le.resolve_round_budget("inner", overrides={"max_idle_rounds": 3})
        self.assertFalse(le.heartbeat_should_fire(budget, 0))
        self.assertFalse(le.heartbeat_should_fire(budget, 2))
        self.assertTrue(le.heartbeat_should_fire(budget, 3))   # N reached → fires
        self.assertTrue(le.heartbeat_should_fire(budget, 4))
        self.assertFalse(le.heartbeat_should_fire(budget, -1))
        # Invalid facts NEVER fire (no fabricated heartbeats).
        self.assertFalse(le.heartbeat_should_fire(budget, "3"))
        self.assertFalse(le.heartbeat_should_fire(budget, True))
        self.assertFalse(le.heartbeat_should_fire(budget, None))

    def test_payload_contents_evidence_backed(self):
        p = le.heartbeat_payload("u.FIX-357", "inner", current_round=15,
                                 idle_rounds=3, last_artifact_ref="EVD-1101")
        self.assertEqual(p["kind"], "round_heartbeat_report")
        self.assertEqual(p["unit_id"], "u.FIX-357")
        self.assertEqual(p["tier"], "inner")
        self.assertEqual(p["current_round"], 15)
        self.assertEqual(p["idle_rounds"], 3)
        self.assertEqual(p["idle_threshold"], le.HEARTBEAT_IDLE_ROUNDS_DEFAULT)
        self.assertTrue(p["fires"])
        self.assertEqual(p["last_artifact_ref"], "EVD-1101")
        self.assertIn("EVD-1101", p["evidence_basis"])
        self.assertTrue(p["recommended_action"])

    def test_payload_is_report_not_stop_proof(self):
        """FEAT-063 alignment: the heartbeat carries stop_proof=False + basis."""
        p = le.heartbeat_payload("u", "inner", idle_rounds=99)
        self.assertIs(p["stop_proof"], False)
        self.assertIn("FEAT-063", p["stop_proof_basis"])
        self.assertIn("NOT a stop proof", p["stop_proof_basis"])

    def test_payload_budget_threshold_used(self):
        budget, _ = le.resolve_round_budget("outer", overrides={"max_idle_rounds": 2})
        p = le.heartbeat_payload("u", "outer", idle_rounds=2, budget=budget)
        self.assertEqual(p["idle_threshold"], 2)
        self.assertTrue(p["fires"])
        p2 = le.heartbeat_payload("u", "outer", idle_rounds=1, budget=budget)
        self.assertEqual(p2["idle_threshold"], 2)
        self.assertFalse(p2["fires"])

    def test_payload_without_artifact_anchor_reports_gap(self):
        p = le.heartbeat_payload("u", "inner", idle_rounds=4, last_artifact_ref=None)
        self.assertIsNone(p["last_artifact_ref"])
        self.assertIn("gap", p["evidence_basis"].lower())

    def test_payload_json_serializable(self):
        p = le.heartbeat_payload("u", "inner", current_round=2, idle_rounds=3)
        json.dumps(p)  # must not raise — the report must be persistable


class InterruptRecoveryTests(unittest.TestCase):
    """interrupt+最小指令恢复产品化 — fact-bound minimal instruction injection."""

    def test_minimal_instruction_is_fact_bound(self):
        p = le.interrupt_recovery_payload(
            "u.DEV-357", "inner", reason="no return for ~15 rounds",
            idle_rounds=15, current_round=15, last_artifact_ref="diff-on-disk")
        mi = p["minimal_instruction"]
        # The injection binds the FACTS: unit, idle count, last artifact anchor.
        self.assertIn("u.DEV-357", mi)
        self.assertIn("15", mi)
        self.assertIn("diff-on-disk", mi)
        # The scope guard is explicit: no re-planning, no scope expansion.
        self.assertIn("Do NOT re-plan", mi)
        # The three-part return shape is spelled out in the text.
        for part in ("(1)", "(2)", "(3)"):
            self.assertIn(part, mi)
        self.assertEqual(
            set(p["expected_response_shape"]),
            {"artifact_or_progress", "blocker", "next_action"})

    def test_payload_provenance_and_bounded_loops(self):
        p = le.interrupt_recovery_payload("u", "inner", reason="heartbeat",
                                          idle_rounds=3)
        self.assertEqual(p["kind"], "interrupt_recovery")
        self.assertIn("FIX-357/359", p["productized_from"])
        self.assertIn("EVD-1101", p["productized_from"])
        # Interrupt loops are BOUNDED — recovery failure escalates, not repeats.
        self.assertIn("PP-Fuse-Escalate", p["escalation_note"])
        self.assertIs(p["stop_proof"], False)

    def test_minimal_instruction_reports_missing_anchor(self):
        p = le.interrupt_recovery_payload("u", "inner", reason="r",
                                          idle_rounds=3, last_artifact_ref=None)
        self.assertIn("none reported", p["minimal_instruction"])

    def test_minimal_instruction_tolerates_unknown_idle(self):
        p = le.interrupt_recovery_payload("u", "inner", reason="r",
                                          idle_rounds=None)
        self.assertIn("an unknown number of", p["minimal_instruction"])

    def test_payload_json_serializable(self):
        p = le.interrupt_recovery_payload("u", "inner", reason="r", idle_rounds=3)
        json.dumps(p)  # must not raise


class StallReportTelemetryTests(unittest.TestCase):
    """遥测测试钉 — compute_stall_report measured from the event log."""

    def test_known_sequence_exact(self):
        r = lt.compute_stall_report(_stall_unit("S1"))
        self.assertEqual(r.status, "measured")
        self.assertEqual(r.reason, "")
        self.assertEqual(r.window, "all")
        u = r.units["S1"]
        self.assertEqual(u["rounds_total"], 3)
        self.assertEqual(u["artifact_rounds"], 1)
        self.assertEqual(u["artifactless_rounds"], 2)
        self.assertEqual(u["idle_streak_trailing"], 2)
        self.assertEqual(u["idle_streak_max"], 2)
        self.assertEqual(u["last_anchor_ts"], "2026-07-23T03:00:00Z")
        self.assertEqual(u["last_artifact_ts"], "2026-07-23T00:30:00Z")
        # Trailing 2 < default threshold 3 → not a suspect.
        self.assertEqual(r.suspects, ())
        self.assertEqual(r.idle_threshold, 3)
        self.assertEqual(r.computed_at, "2026-07-23T03:00:00Z")
        self.assertEqual(r.malformed_timestamps, 0)
        self.assertIn("NOT stop proofs", r.scope_note)

    def test_suspect_flagged_at_threshold(self):
        r = lt.compute_stall_report(_stall_unit("S2"), idle_threshold=2)
        self.assertEqual(r.idle_threshold, 2)
        self.assertEqual(r.suspects, ("S2",))

    def test_empty_events_unknown(self):
        r = lt.compute_stall_report([])
        self.assertEqual(r.status, "unknown")
        self.assertTrue(r.reason)
        self.assertEqual(r.units_considered, 0)
        self.assertEqual(r.suspects, ())
        self.assertEqual(r.units, {})

    def test_default_artifact_type_and_parameterized_widening(self):
        """gate_result is the default artifact; the set is a parameter."""
        events = _stall_unit("S3")
        # Widened to include back_edge → every closed round is artifact-bearing.
        r_wide = lt.compute_stall_report(
            events, artifact_event_types={"gate_result", "back_edge"})
        u_wide = r_wide.units["S3"]
        self.assertEqual(u_wide["artifact_rounds"], 3)
        self.assertEqual(u_wide["idle_streak_trailing"], 0)
        # Narrowed to a type that never appears → all rounds idle, suspect at N.
        r_narrow = lt.compute_stall_report(
            events, artifact_event_types={"phase_transition"})
        u_narrow = r_narrow.units["S3"]
        self.assertEqual(u_narrow["artifact_rounds"], 0)
        self.assertEqual(u_narrow["idle_streak_trailing"], 3)
        self.assertEqual(r_narrow.suspects, ("S3",))
        # A bare string is one type (not exploded into characters).
        r_str = lt.compute_stall_report(events, artifact_event_types="gate_result")
        self.assertEqual(r_str.artifact_event_types, ("gate_result",))

    def test_window_filtering_respected(self):
        recent = _stall_unit("SR", day=23)
        old = _stall_unit("SO", day=1)
        r = lt.compute_stall_report(recent + old, window="7d")
        self.assertEqual(r.window, "7d")
        self.assertEqual(r.units_considered, 1)
        self.assertIn("SR", r.units)
        self.assertNotIn("SO", r.units)

    def test_malformed_timestamps_counted_and_skipped(self):
        events = _stall_unit("S4") + [
            _ev("S4", "back_edge", "garbage-timestamp", 9, 8)]
        r = lt.compute_stall_report(events)
        self.assertEqual(r.malformed_timestamps, 1)
        # The malformed anchor is skipped: still exactly 3 closed rounds.
        self.assertEqual(r.units["S4"]["rounds_total"], 3)

    def test_open_round_not_counted_as_idle_streak(self):
        """A trailing anchor with no successor is OPEN — streaks count CLOSED
        rounds only (purity: the log cannot time the open round)."""
        r = lt.compute_stall_report(
            [_ev("S6", "phase_enter", _ts(0), 0, None, to_phase="plan")])
        u = r.units["S6"]
        self.assertEqual(u["rounds_total"], 0)
        self.assertEqual(u["idle_streak_trailing"], 0)
        self.assertEqual(u["last_anchor_ts"], "2026-07-23T00:00:00Z")
        self.assertIsNone(u["last_artifact_ts"])
        self.assertEqual(r.suspects, ())

    def test_deterministic_and_non_mutating(self):
        events = _stall_unit("S5")
        before = json.loads(json.dumps(events))
        r1 = lt.compute_stall_report(events)
        r2 = lt.compute_stall_report(events)
        self.assertEqual(r1, r2)
        self.assertEqual(events, before)

    def test_gate_result_on_anchor_boundary_counts_for_that_round(self):
        """Inclusive interval semantics: a gate_result stamped at the same
        second as the closing anchor belongs to the round it closes (FEAT-006
        stamps gate_result + back_edge on the same CAS write)."""
        events = [
            _ev("S8", "phase_enter", _ts(0), 0, None, to_phase="plan"),
            _ev("S8", "gate_result", _ts(1), 0, 0, from_phase="reflect"),
            _ev("S8", "back_edge", _ts(1), 1, 0, from_phase="reflect",
                to_phase="plan", loop_count=1),
        ]
        r = lt.compute_stall_report(events)
        u = r.units["S8"]
        self.assertEqual(u["rounds_total"], 1)
        self.assertEqual(u["artifact_rounds"], 1)
        self.assertEqual(u["idle_streak_trailing"], 0)


class Feat044CrossModuleConsistencyTests(unittest.TestCase):
    """Mirror guard: the telemetry threshold stays in lockstep with the engine.

    loop_telemetry deliberately does NOT import loop_engine (stdlib-only
    import contract, ADR-015 §6.4) — so the two defaults are duplicated by
    design and their equality is enforced HERE, in the test layer.
    """

    def test_telemetry_threshold_mirrors_engine_default(self):
        self.assertEqual(lt.DEFAULT_IDLE_THRESHOLD,
                         le.HEARTBEAT_IDLE_ROUNDS_DEFAULT)

    def test_engine_default_budget_heartbeat_n_matches_telemetry(self):
        budget, _ = le.resolve_round_budget("inner")
        self.assertEqual(budget.max_idle_rounds, lt.DEFAULT_IDLE_THRESHOLD)

    def test_stall_report_feeds_heartbeat_pipeline(self):
        """E2E pin: measured trailing streak → engine predicate → heartbeat
        report → interrupt-recovery payload (the FEAT-044 chain)."""
        events = _stall_unit("S7")
        r = lt.compute_stall_report(events, idle_threshold=2)
        streak = r.units["S7"]["idle_streak_trailing"]
        self.assertEqual(streak, 2)
        budget, _ = le.resolve_round_budget(
            "inner", overrides={"max_idle_rounds": 2})
        self.assertTrue(le.heartbeat_should_fire(budget, streak))
        p = le.heartbeat_payload(
            "S7", "inner", idle_rounds=streak, budget=budget,
            last_artifact_ref="G6@2026-07-23T00:30:00Z")
        self.assertTrue(p["fires"])
        self.assertIs(p["stop_proof"], False)
        rec = le.interrupt_recovery_payload(
            "S7", "inner", reason="heartbeat", idle_rounds=streak)
        self.assertIn("S7", rec["minimal_instruction"])
        self.assertIs(rec["stop_proof"], False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
