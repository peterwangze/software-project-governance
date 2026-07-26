"""Tests for the restart-safe event log + dependency blocking + WIP budget (FEAT-007).

These tests are the load-bearing verification for FEAT-007 (ADR-014 §5, §3.5,
§3.6) — the restart-safe, multi-process-safe event log plus the executable
dependency/WIP admission gates.

Coverage (ADR-014 §8.4 + the FEAT-007 task's required cases):

  - **append_event / read_events**: write events, read them back; JSONL format
    (one JSON object per non-blank line); round-trip preserves all fields.
  - **append atomicity (multi-thread)**: many threads append concurrently; no
    event is lost; every line is well-formed JSON; event_ids are unique.
  - **multi-process append**: two subprocesses append concurrently; no lost
    events; no corrupt lines. (The Windows JSONL atomicity concern, Design
    Review P2-1.)
  - **validate_event**: a valid event passes; a missing required field fails;
    an unknown event_type fails; non-int cas_version fails.
  - **Monotonicity check**: strictly +1 sequence passes; a gap fails; a
    regression fails.
  - **Phase-legality replay**: legal transitions pass; an illegal jump
    (plan→observe) fails.
  - **FEAT-005 wiring (apply_transition + activate_unit)**: with event_log
    enabled, each transition appends an event; state-first/event-second
    ordering; without event_log the behavior is byte-identical (backward
    compat).
  - **FEAT-006 wiring (process_gate_result)**: the gate_result / back_edge /
    fuse_trip events are appended after the CAS write.
  - **Dependency blocking**: a unit with an unpassed dependency → denied; all
    passed → admitted (WIP permitting).
  - **WIP budget**: under budget → admitted; at/over budget → denied.
  - **Restart consistency (state==log → OK; state ahead → phase_recovery;
    log ahead → recovery_conflict fail-close)**.
  - **State-first/event-second crash gap**: a crash between the state write
    and the event append leaves a gap that restart detects and synthesizes a
    phase_recovery event for.
  - **commit_recovery**: the synthetic events are written to the log.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_loop_event_log.py -v
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import loop_admission as admit  # noqa: E402
import loop_event_log as elog  # noqa: E402
import loop_gate_processor as gp  # noqa: E402
import loop_paro_engine as paro  # noqa: E402

# Reuse the FEAT-005 fixture builders so the v2 payload shapes stay in sync
# with the canonical FEAT-005 test suite (single source of truth for the shape).
from tests.test_loop_paro_engine import (  # noqa: E402
    _TEST_MAX_ROUNDS,
    _active_loop_state,
    _valid_gate_state,
    _valid_unit,
    _valid_payload,
    _write_payload,
    _activated_payload,
)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _log_path(tmpdir):
    """Return the event-log path under ``tmpdir/.governance/``."""
    p = Path(tmpdir) / ".governance" / "loop-event-log.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _valid_event(unit_id="shitu.story.Skeleton", event_type="phase_transition",
                 cas_version=1, from_version=0):
    """A valid event envelope (passes validate_event)."""
    return elog.build_event(
        unit_id, event_type, cas_version=cas_version, from_version=from_version,
        actor="test", from_phase="plan", to_phase="act",
    )


def _unit_on_disk(unit_id, runtime_path):
    payload = json.loads(Path(runtime_path).read_text(encoding="utf-8"))
    for u in payload["flow_units"]:
        if u["flow_unit_id"] == unit_id:
            return u
    raise AssertionError("unit {0!r} not on disk".format(unit_id))


def _drive_to_reflect(unit_id, runtime_path, log_path=None):
    """Drive an activated unit plan→act→observe→reflect with event log on."""
    for to_phase, event in [
        ("act", {"reason": "plan accepted"}),
        ("observe", {"reason": "action complete"}),
        ("reflect", {"gate_result": "NEEDS_CHANGE", "reason": "review recorded"}),
    ]:
        r = paro.apply_transition(unit_id, to_phase, event,
                                  runtime_file=runtime_path,
                                  event_log=log_path)
        assert r.success, "forward {0} failed: {1}".format(to_phase, r.reason)


# ═══════════════════════════════════════════════════════════════════════════
# 1. append_event / read_events (round-trip + JSONL format)
# ═══════════════════════════════════════════════════════════════════════════


class AppendReadTests(unittest.TestCase):
    """append_event writes one JSON line; read_events parses them back."""

    def test_append_single_event_round_trip(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_test_")
        lp = _log_path(tmpdir)
        ev = _valid_event()
        elog.append_event(ev, log_path=lp)
        self.assertTrue(lp.is_file())
        read = elog.read_events(log_path=lp)
        self.assertEqual(len(read), 1)
        self.assertEqual(read[0]["unit_id"], "shitu.story.Skeleton")
        self.assertEqual(read[0]["event_type"], "phase_transition")
        # All required fields preserved.
        for field in elog.REQUIRED_FIELDS:
            self.assertIn(field, read[0], "field {0!r} lost in round-trip".format(field))

    def test_jsonl_format_one_object_per_line(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_test_")
        lp = _log_path(tmpdir)
        for i in range(5):
            elog.append_event(_valid_event(cas_version=i + 1, from_version=i),
                              log_path=lp)
        text = lp.read_text(encoding="utf-8")
        lines = [ln for ln in text.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 5)
        # Each non-blank line is valid JSON.
        for ln in lines:
            obj = json.loads(ln)
            self.assertIsInstance(obj, dict)
        # File ends with a newline (each append adds \n).
        self.assertTrue(text.endswith("\n"))

    def test_append_multiple_in_order(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_test_")
        lp = _log_path(tmpdir)
        events = [
            _valid_event(event_type="phase_enter", cas_version=0, from_version=None),
            _valid_event(event_type="phase_transition", cas_version=1, from_version=0),
            _valid_event(event_type="phase_transition", cas_version=2, from_version=1),
        ]
        elog.append_events(events, log_path=lp)
        read = elog.read_events(log_path=lp)
        self.assertEqual([e["event_type"] for e in read],
                         ["phase_enter", "phase_transition", "phase_transition"])
        self.assertEqual([e["cas_version"] for e in read], [0, 1, 2])

    def test_read_filters_by_unit_id(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_test_")
        lp = _log_path(tmpdir)
        elog.append_event(_valid_event(unit_id="a.b.C"), log_path=lp)
        elog.append_event(_valid_event(unit_id="x.y.Z"), log_path=lp)
        elog.append_event(_valid_event(unit_id="a.b.C"), log_path=lp)
        a_events = elog.read_events(log_path=lp, unit_id="a.b.C")
        self.assertEqual(len(a_events), 2)
        self.assertTrue(all(e["unit_id"] == "a.b.C" for e in a_events))

    def test_read_missing_file_returns_empty(self):
        result = elog.read_events(log_path=Path(tempfile.mkdtemp()) / "nope.jsonl")
        self.assertEqual(result, [])

    def test_last_event_for_unit(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_test_")
        lp = _log_path(tmpdir)
        for i in range(3):
            elog.append_event(_valid_event(cas_version=i, from_version=i - 1 if i else None),
                              log_path=lp)
        last = elog.last_event_for_unit("shitu.story.Skeleton", log_path=lp)
        self.assertIsNotNone(last)
        self.assertEqual(last["cas_version"], 2)
        self.assertIsNone(elog.last_event_for_unit("nonexistent", log_path=lp))

    def test_malformed_line_skipped_on_read(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_test_")
        lp = _log_path(tmpdir)
        elog.append_event(_valid_event(), log_path=lp)
        # Append a malformed line (simulating a torn write).
        with open(lp, "a", encoding="utf-8") as h:
            h.write("{this is not valid json\n")
        elog.append_event(_valid_event(cas_version=2, from_version=1), log_path=lp)
        read = elog.read_events(log_path=lp)
        # Malformed line skipped; the two valid events survive.
        self.assertEqual(len(read), 2)

    def test_generated_defaults_filled(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_test_")
        lp = _log_path(tmpdir)
        # Pass an event WITHOUT event_id/timestamp — they should be generated.
        ev = {
            "unit_id": "u", "event_type": "phase_enter", "cas_version": 0,
            "from_version": None, "from_phase": None, "to_phase": "plan",
            "actor": "test",
        }
        elog.append_event(ev, log_path=lp)
        read = elog.read_events(log_path=lp)
        self.assertIn("event_id", read[0])
        self.assertTrue(read[0]["event_id"])
        self.assertIn("timestamp", read[0])
        self.assertTrue(read[0]["timestamp"])


# ═══════════════════════════════════════════════════════════════════════════
# 2. Append atomicity — concurrent threads (LOAD-BEARING, §5.2)
# ═══════════════════════════════════════════════════════════════════════════


class ConcurrentAppendThreadingTests(unittest.TestCase):
    """Many threads append concurrently — no event lost, no line corrupted.

    This is the in-process half of the §5.2 multi-process-safety proof. The
    cross-process half is in :class:`MultiProcessAppendTests` below.
    """

    def test_many_threads_no_lost_events(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_thread_")
        lp = _log_path(tmpdir)
        n_threads = 16
        per_thread = 50
        errors = []

        def worker(tid):
            try:
                for i in range(per_thread):
                    elog.append_event(
                        elog.build_event(
                            "u{0}".format(tid), "phase_transition",
                            cas_version=i, from_version=i - 1 if i else None,
                            actor="t{0}".format(tid),
                            from_phase="plan", to_phase="act",
                        ),
                        log_path=lp,
                    )
            except Exception as exc:  # pragma: no cover - surfaced via errors
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [], "worker errors: {0}".format(errors))

        read = elog.read_events(log_path=lp)
        expected = n_threads * per_thread
        self.assertEqual(len(read), expected,
                         "LOST {0} events (expected {1}, got {2})".format(
                             expected - len(read), expected, len(read)))
        # Every line was well-formed JSON (read_events skips malformed lines,
        # so len(read)==expected proves no corruption).
        # Every event_id unique.
        ids = [e["event_id"] for e in read]
        self.assertEqual(len(set(ids)), len(ids), "duplicate event_ids")

    def test_concurrent_same_unit_appends_interpretable(self):
        """Two threads append events for the SAME unit; each line is self-contained."""
        tmpdir = tempfile.mkdtemp(prefix="elog_thread_")
        lp = _log_path(tmpdir)
        n = 100
        errors = []

        def worker():
            try:
                for i in range(n):
                    elog.append_event(
                        elog.build_event(
                            "shared.unit", "phase_transition",
                            cas_version=i, from_version=i - 1 if i else None,
                            actor="t", from_phase="plan", to_phase="act",
                        ),
                        log_path=lp,
                    )
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start(); t2.start()
        t1.join(); t2.join()
        self.assertEqual(errors, [])
        read = elog.read_events(log_path=lp)
        self.assertEqual(len(read), 2 * n)
        # Each event carries its own cas_version/from_version (self-contained).
        for e in read:
            self.assertIn("cas_version", e)
            self.assertIn("from_version", e)


# ═══════════════════════════════════════════════════════════════════════════
# 3. Multi-PROCESS append (LOAD-BEARING, §5.2, the Windows P2-1 concern)
# ═══════════════════════════════════════════════════════════════════════════


_MULTI_PROCESS_SCRIPT = """
import sys, json
sys.path.insert(0, {infra_dir!r})
import loop_event_log as elog
log_path = {log_path!r}
n = {n!r}
unit_prefix = {unit_prefix!r}
# Each process appends `n` events for its own unit so we can verify per-process
# counts AND the merged total.
import os
pid = os.getpid()
for i in range(n):
    elog.append_event(
        elog.build_event(
            "{unit_prefix}" + str(pid), "phase_transition",
            cas_version=i, from_version=i - 1 if i else None,
            actor="pid-" + str(pid), from_phase="plan", to_phase="act",
        ),
        log_path=log_path,
    )
print("OK", pid, n)
"""


class MultiProcessAppendTests(unittest.TestCase):
    """Two SUBPROCESSES append concurrently — no lost events, no corrupt lines.

    This is the cross-process half of the §5.2 proof (the Design Review P2-1
    Windows atomicity concern). The threading test above covers the in-process
    case; this one exercises a genuine separate interpreter with its own file
    handles, the real-world shape of two loop-engine writers racing.
    """

    def test_two_subprocesses_no_lost_events(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_mp_")
        lp = _log_path(tmpdir)
        n_per = 60
        script = _MULTI_PROCESS_SCRIPT.format(
            infra_dir=str(_INFRA_DIR), log_path=str(lp),
            n=n_per, unit_prefix="mp.unit.",
        )
        # Launch two subprocesses concurrently.
        procs = [
            subprocess.Popen(
                [sys.executable, "-c", script],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            for _ in range(2)
        ]
        for p in procs:
            out, err = p.communicate(timeout=60)
            self.assertEqual(p.returncode, 0,
                             "subprocess failed: {0!r}".format(err.decode("utf-8", "replace")))
        read = elog.read_events(log_path=lp)
        expected = 2 * n_per
        self.assertEqual(len(read), expected,
                         "LOST {0} events in multi-process append (expected {1}, got {2})".format(
                             expected - len(read), expected, len(read)))
        # Distinct unit_ids (one per pid) → 2 distinct units.
        units = {e["unit_id"] for e in read}
        self.assertEqual(len(units), 2)
        # Every event_id unique.
        ids = [e["event_id"] for e in read]
        self.assertEqual(len(set(ids)), len(read), "duplicate event_ids across processes")

    def test_multi_process_lines_all_well_formed(self):
        """No torn/partial JSON lines after concurrent subprocess appends."""
        tmpdir = tempfile.mkdtemp(prefix="elog_mp_")
        lp = _log_path(tmpdir)
        n_per = 40
        script = _MULTI_PROCESS_SCRIPT.format(
            infra_dir=str(_INFRA_DIR), log_path=str(lp),
            n=n_per, unit_prefix="wf.unit.",
        )
        procs = [
            subprocess.Popen([sys.executable, "-c", script])
            for _ in range(3)
        ]
        for p in procs:
            p.communicate(timeout=60)
            self.assertEqual(p.returncode, 0)
        # Read the raw file and assert EVERY non-blank line is valid JSON. This
        # is the stronger check than read_events (which silently skips bad
        # lines) — a corrupt line here would prove the append is not atomic.
        text = lp.read_text(encoding="utf-8")
        bad = []
        for i, line in enumerate(text.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError:
                bad.append((i, line[:60]))
        self.assertEqual(bad, [], "{0} corrupt lines: {1!r}".format(len(bad), bad[:3]))


# ═══════════════════════════════════════════════════════════════════════════
# 4. validate_event
# ═══════════════════════════════════════════════════════════════════════════


class ValidateEventTests(unittest.TestCase):
    """validate_event: valid passes; missing field fails; unknown type fails."""

    def test_valid_event_passes(self):
        for et in elog.EVENT_TYPES:
            ev = _valid_event(event_type=et)
            self.assertEqual(elog.validate_event(ev), [],
                             "event_type {0!r} should be valid".format(et))

    def test_missing_required_field_fails(self):
        for field in elog.REQUIRED_FIELDS:
            ev = _valid_event()
            del ev[field]
            errs = elog.validate_event(ev)
            self.assertTrue(any(field in e and "missing" in e for e in errs),
                            "expected missing-{0} error; got: {1}".format(field, errs))

    def test_unknown_event_type_fails(self):
        ev = _valid_event()
        ev["event_type"] = "not_a_real_type"
        errs = elog.validate_event(ev)
        self.assertTrue(any("unknown event_type" in e for e in errs))

    def test_cas_version_as_bool_fails(self):
        ev = _valid_event()
        ev["cas_version"] = True
        errs = elog.validate_event(ev)
        self.assertTrue(any("cas_version" in e and "integer" in e for e in errs))

    def test_non_dict_event_fails(self):
        errs = elog.validate_event("not a dict")
        self.assertEqual(len(errs), 1)
        self.assertIn("not a dict", errs[0])


# ═══════════════════════════════════════════════════════════════════════════
# 5. Monotonicity check (§3.6)
# ═══════════════════════════════════════════════════════════════════════════


class MonotonicityTests(unittest.TestCase):
    """check_cas_monotonicity: strictly +1 passes; gap fails; regression fails."""

    def _ev(self, ts, cas, fv):
        return {"timestamp": ts, "cas_version": cas, "from_version": fv,
                "to_phase": "act"}

    def test_strictly_plus_one_passes(self):
        events = [
            self._ev("2026-07-23T00:00:00Z", 0, None),
            self._ev("2026-07-23T00:00:01Z", 1, 0),
            self._ev("2026-07-23T00:00:02Z", 2, 1),
            self._ev("2026-07-23T00:00:03Z", 3, 2),
        ]
        self.assertEqual(elog.check_cas_monotonicity(events), [])

    def test_gap_detected(self):
        events = [
            self._ev("2026-07-23T00:00:00Z", 0, None),
            self._ev("2026-07-23T00:00:01Z", 5, 0),  # jumps 0→5
        ]
        errs = elog.check_cas_monotonicity(events)
        # The cas_version jump 0→5 (not 0+1) is the gap violation.
        self.assertTrue(any("not previous+1" in e for e in errs),
                        "expected gap error; got: {0}".format(errs))

    def test_gap_with_wrong_from_version_detected(self):
        events = [
            self._ev("2026-07-23T00:00:00Z", 0, None),
            self._ev("2026-07-23T00:00:01Z", 5, 2),  # gap AND from_version!=prev
        ]
        errs = elog.check_cas_monotonicity(events)
        self.assertTrue(any("not previous+1" in e for e in errs))
        self.assertTrue(any("from_version" in e and "previous cas_version" in e for e in errs))

    def test_regression_detected(self):
        # A genuine regression: cas_version DECREASES (2 → 1).
        events = [
            self._ev("2026-07-23T00:00:00Z", 0, None),
            self._ev("2026-07-23T00:00:01Z", 1, 0),
            self._ev("2026-07-23T00:00:02Z", 2, 1),
            self._ev("2026-07-23T00:00:03Z", 1, 2),  # 2→1 regression
        ]
        errs = elog.check_cas_monotonicity(events)
        self.assertTrue(len(errs) > 0,
                        "expected regression error; got: {0}".format(errs))
        self.assertTrue(any("not previous+1" in e for e in errs))

    def test_from_version_mismatch_detected(self):
        events = [
            self._ev("2026-07-23T00:00:00Z", 0, None),
            self._ev("2026-07-23T00:00:01Z", 1, 99),  # cas ok but from_version wrong
        ]
        errs = elog.check_cas_monotonicity(events)
        self.assertTrue(any("from_version" in e and "!=" in e for e in errs))

    def test_empty_and_single_pass(self):
        self.assertEqual(elog.check_cas_monotonicity([]), [])
        self.assertEqual(elog.check_cas_monotonicity([self._ev("t", 0, None)]), [])


# ═══════════════════════════════════════════════════════════════════════════
# 6. Phase-legality replay (§3.6)
# ═══════════════════════════════════════════════════════════════════════════


class PhaseLegalityTests(unittest.TestCase):
    """check_phase_legality: legal transitions pass; illegal jump fails."""

    def test_legal_forward_chain_passes(self):
        events = [
            {"timestamp": "t0", "event_type": "phase_enter",
             "cas_version": 0, "from_version": None, "to_phase": "plan"},
            {"timestamp": "t1", "event_type": "phase_transition",
             "cas_version": 1, "from_version": 0,
             "from_phase": "plan", "to_phase": "act"},
            {"timestamp": "t2", "event_type": "phase_transition",
             "cas_version": 2, "from_version": 1,
             "from_phase": "act", "to_phase": "observe"},
            {"timestamp": "t3", "event_type": "phase_transition",
             "cas_version": 3, "from_version": 2,
             "from_phase": "observe", "to_phase": "reflect"},
        ]
        self.assertEqual(elog.check_phase_legality(events), [])

    def test_illegal_plan_to_observe_detected(self):
        events = [
            {"timestamp": "t0", "event_type": "phase_enter",
             "cas_version": 0, "from_version": None, "to_phase": "plan"},
            {"timestamp": "t1", "event_type": "phase_transition",
             "cas_version": 1, "from_version": 0,
             "from_phase": "plan", "to_phase": "observe"},  # skip act
        ]
        errs = elog.check_phase_legality(events)
        self.assertTrue(any("illegal phase transition" in e for e in errs))
        self.assertTrue(any("plan" in e and "observe" in e for e in errs))

    def test_back_edge_with_fuse_facts_passes(self):
        events = [
            {"timestamp": "t0", "event_type": "phase_enter",
             "cas_version": 0, "from_version": None, "to_phase": "plan"},
            {"timestamp": "t1", "event_type": "phase_transition",
             "cas_version": 1, "from_version": 0,
             "from_phase": "plan", "to_phase": "act"},
            {"timestamp": "t2", "event_type": "phase_transition",
             "cas_version": 2, "from_version": 1,
             "from_phase": "act", "to_phase": "observe"},
            {"timestamp": "t3", "event_type": "phase_transition",
             "cas_version": 3, "from_version": 2,
             "from_phase": "observe", "to_phase": "reflect"},
            {"timestamp": "t4", "event_type": "back_edge",
             "cas_version": 4, "from_version": 3,
             "from_phase": "reflect", "to_phase": "plan",
             "payload": {"gate_result": "NEEDS_CHANGE", "loop_count": 0,
                         "max_rounds": _TEST_MAX_ROUNDS}},
        ]
        self.assertEqual(elog.check_phase_legality(events), [],
                         "back-edge with fuse facts should be legal")

    def test_recovery_markers_skipped(self):
        # phase_recovery / recovery_conflict are audit markers, not transitions.
        events = [
            {"timestamp": "t0", "event_type": "phase_enter",
             "cas_version": 0, "from_version": None, "to_phase": "plan"},
            {"timestamp": "t1", "event_type": "phase_recovery",
             "cas_version": 0, "from_version": None, "to_phase": None},
        ]
        self.assertEqual(elog.check_phase_legality(events), [])


# ═══════════════════════════════════════════════════════════════════════════
# 7. FEAT-005 wiring — apply_transition / activate_unit append events
# ═══════════════════════════════════════════════════════════════════════════


class Feat005WiringTests(unittest.TestCase):
    """With event_log enabled, FEAT-005 appends events; backward-compat when None."""

    def test_apply_transition_appends_phase_transition_event(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_w5_")
        lp = _log_path(tmpdir)
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"
        r = paro.apply_transition(unit_id, "act", {"reason": "ok"},
                                  runtime_file=runtime_path, event_log=lp)
        self.assertTrue(r.success)
        events = elog.read_events(log_path=lp)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "phase_transition")
        self.assertEqual(events[0]["cas_version"], 1)
        self.assertEqual(events[0]["from_version"], 0)
        self.assertEqual(events[0]["from_phase"], "plan")
        self.assertEqual(events[0]["to_phase"], "act")

    def test_activate_unit_appends_phase_enter(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_w5_")
        lp = _log_path(tmpdir)
        # A dormant payload (no cas_version).
        runtime_path = _write_payload(tmpdir, _valid_payload(units=[_valid_unit()]))
        r = paro.activate_unit("shitu.story.Skeleton", runtime_file=runtime_path,
                               tier="inner", fuse_max_rounds=5, event_log=lp)
        self.assertTrue(r.success)
        events = elog.read_events(log_path=lp)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "phase_enter")
        self.assertEqual(events[0]["cas_version"], 0)
        self.assertIsNone(events[0]["from_version"])

    def test_backward_compat_no_event_log_byte_identical(self):
        """When event_log is None, apply_transition behaves exactly as FEAT-005."""
        tmpdir = tempfile.mkdtemp(prefix="elog_w5_")
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"
        r = paro.apply_transition(unit_id, "act", {}, runtime_file=runtime_path)
        self.assertTrue(r.success)
        self.assertEqual(r.new_cas_version, 1)
        # No event-log file should exist (nothing was written).
        self.assertFalse(_log_path(tmpdir).is_file())

    def test_state_first_event_second_ordering(self):
        """The state file is committed BEFORE the event is appended.

        After a successful transition, both the on-disk state AND the event
        reflect the new cas_version. We verify the ordering invariant by
        checking that the event's cas_version == the on-disk cas_version
        (both reflect the committed transition).
        """
        tmpdir = tempfile.mkdtemp(prefix="elog_w5_")
        lp = _log_path(tmpdir)
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"
        r = paro.apply_transition(unit_id, "act", {}, runtime_file=runtime_path,
                                  event_log=lp)
        self.assertTrue(r.success)
        on_disk_cas = _unit_on_disk(unit_id, runtime_path)["loop_state"]["cas_version"]
        events = elog.read_events(log_path=lp)
        self.assertEqual(events[0]["cas_version"], on_disk_cas)
        self.assertEqual(events[0]["cas_version"], r.new_cas_version)

    def test_full_forward_chain_events_monotonic(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_w5_")
        lp = _log_path(tmpdir)
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"
        _drive_to_reflect(unit_id, runtime_path, log_path=lp)
        events = elog.read_events(log_path=lp, unit_id=unit_id)
        self.assertEqual(len(events), 3)
        self.assertEqual([e["event_type"] for e in events],
                         ["phase_transition", "phase_transition", "phase_transition"])
        # Monotonicity holds.
        self.assertEqual(elog.check_cas_monotonicity(events), [])
        # Phase legality holds.
        self.assertEqual(elog.check_phase_legality(events), [])

    def test_event_log_true_uses_default_path(self):
        """event_log=True resolves to <runtime parent>/.governance/loop-event-log.jsonl."""
        tmpdir = tempfile.mkdtemp(prefix="elog_w5_")
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"
        paro.apply_transition(unit_id, "act", {}, runtime_file=runtime_path,
                              event_log=True)
        expected_log = runtime_path.parent / elog.EVENT_LOG_FILENAME
        self.assertTrue(expected_log.is_file(),
                        "event_log=True should write to {0}".format(expected_log))
        events = elog.read_events(log_path=expected_log)
        self.assertEqual(len(events), 1)


# ═══════════════════════════════════════════════════════════════════════════
# 8. FEAT-006 wiring — process_gate_result appends gate events
# ═══════════════════════════════════════════════════════════════════════════


class Feat006WiringTests(unittest.TestCase):
    """process_gate_result appends gate_result/back_edge/fuse_trip events."""

    def test_gate_fail_appends_back_edge_events(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_w6_")
        lp = _log_path(tmpdir)
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"
        _drive_to_reflect(unit_id, runtime_path)
        outcome = gp.process_gate_result(
            unit_id, "G6", "NEEDS_CHANGE",
            evidence_ref="review-code-Skeleton-R1.md",
            actor="code-reviewer-agent",
            runtime_file=runtime_path, event_log=lp,
        )
        self.assertTrue(outcome.success)
        self.assertEqual(outcome.decision, "iterate")
        events = elog.read_events(log_path=lp)
        types = [e["event_type"] for e in events]
        self.assertIn("gate_result", types)
        self.assertIn("back_edge", types)
        # All events stamped with the committed cas_version.
        for e in events:
            self.assertEqual(e["cas_version"], outcome.cas_version)
            self.assertIsNotNone(e["from_version"])

    def test_gate_fail_events_monotonic_with_prior_transitions(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_w6_")
        lp = _log_path(tmpdir)
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"
        # Drive forward with the log on (3 phase_transition events).
        _drive_to_reflect(unit_id, runtime_path, log_path=lp)
        # Now process a failed gate (appends gate_result + back_edge).
        gp.process_gate_result(
            unit_id, "G6", "NEEDS_CHANGE",
            evidence_ref="rev.md", actor="reviewer",
            runtime_file=runtime_path, event_log=lp,
        )
        events = elog.read_events(log_path=lp, unit_id=unit_id)
        # 3 phase_transitions + gate_result + back_edge = 5
        self.assertEqual(len(events), 5)
        # The full sequence is monotonic.
        self.assertEqual(elog.check_cas_monotonicity(events), [],
                         "events not monotonic: {0}".format(
                             elog.check_cas_monotonicity(events)))

    def test_fuse_trip_events_appended(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_w6_")
        lp = _log_path(tmpdir)
        # A unit already at the fuse boundary (loop_count = max_rounds + 1).
        unit = _valid_unit(
            unit_id="shitu.story.Skeleton", runtime_status="active",
            loop_state=_active_loop_state(
                agent_phase="reflect", loop_count=_TEST_MAX_ROUNDS + 1,
                cas_version=2, last_gate_result="NEEDS_CHANGE",
                tier="inner", max_rounds=_TEST_MAX_ROUNDS),
            gate_state=_valid_gate_state(status="failed", last_result="NEEDS_CHANGE"),
        )
        runtime_path = _write_payload(tmpdir, _valid_payload(units=[unit]))
        outcome = gp.process_gate_result(
            "shitu.story.Skeleton", "G6", "NEEDS_CHANGE",
            evidence_ref="rev.md", actor="reviewer",
            runtime_file=runtime_path, event_log=lp,
        )
        self.assertTrue(outcome.success)
        self.assertTrue(outcome.fuse_tripped)
        events = elog.read_events(log_path=lp)
        types = [e["event_type"] for e in events]
        self.assertIn("fuse_trip", types)
        self.assertIn("gate_result", types)

    def test_process_gate_result_backward_compat_no_log(self):
        """When event_log is None, events are still in outcome but not written."""
        tmpdir = tempfile.mkdtemp(prefix="elog_w6_")
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"
        _drive_to_reflect(unit_id, runtime_path)
        outcome = gp.process_gate_result(
            unit_id, "G6", "NEEDS_CHANGE",
            evidence_ref="rev.md", actor="reviewer",
            runtime_file=runtime_path,
        )
        self.assertTrue(outcome.success)
        self.assertGreater(len(outcome.events), 0)
        # No log file written.
        self.assertFalse(_log_path(tmpdir).is_file())


# ═══════════════════════════════════════════════════════════════════════════
# 9. Dependency blocking (§5.3)
# ═══════════════════════════════════════════════════════════════════════════


class DependencyBlockTests(unittest.TestCase):
    """A unit whose dep has not passed → denied; all passed → admitted."""

    def _payload_with_dep(self, dep_status="failed"):
        """Two units: 'child' depends on 'parent'; parent gate is dep_status."""
        parent = _valid_unit(
            unit_id="a.parent", runtime_status="dormant",
            gate_state=_valid_gate_state(status=dep_status, gate_id="G5",
                                          last_result=None),
        )
        child = _valid_unit(
            unit_id="a.child", runtime_status="dormant",
            loop_state={
                "active_loop": False, "active_loop_tier": "inner",
                "loop_count": 0, "last_loop_type": None, "agent_phase": "plan",
                "iteration_within_inner": 0, "pause_points_active": [],
                "last_gate_result": None,
                "fuse": {"max_rounds": _TEST_MAX_ROUNDS, "tripped": False},
            },
            gate_state=_valid_gate_state(status="pending", gate_id="G6"),
        )
        child["dependencies"] = ["a.parent"]
        return _valid_payload(units=[parent, child])

    def test_unpassed_dependency_denied(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_dep_")
        runtime_path = _write_payload(tmpdir, self._payload_with_dep("failed"))
        lp = _log_path(tmpdir)
        result = admit.check_admission("a.child", runtime_file=runtime_path,
                                       log_path=lp)
        self.assertFalse(result.admitted)
        self.assertEqual(result.blocking_dependencies, ["a.parent"])
        # A dependency_block event was recorded.
        events = elog.read_events(log_path=lp)
        types = [e["event_type"] for e in events]
        self.assertIn("dependency_block", types)

    def test_passed_dependencies_admitted(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_dep_")
        runtime_path = _write_payload(tmpdir, self._payload_with_dep("passed"))
        lp = _log_path(tmpdir)
        result = admit.check_admission("a.child", runtime_file=runtime_path,
                                       log_path=lp)
        self.assertTrue(result.admitted)
        self.assertEqual(result.blocking_dependencies, [])
        # No dependency_block event; a wip_admit event instead.
        events = elog.read_events(log_path=lp)
        types = [e["event_type"] for e in events]
        self.assertIn("wip_admit", types)
        self.assertNotIn("dependency_block", types)

    def test_unknown_dependency_blocks_fail_closed(self):
        """A dependency id that doesn't exist in the runtime blocks (fail-closed)."""
        tmpdir = tempfile.mkdtemp(prefix="elog_dep_")
        child = _valid_unit(unit_id="a.child", runtime_status="dormant")
        child["dependencies"] = ["nonexistent.dep"]
        runtime_path = _write_payload(tmpdir, _valid_payload(units=[child]))
        result = admit.check_admission("a.child", runtime_file=runtime_path)
        self.assertFalse(result.admitted)
        self.assertIn("nonexistent.dep", result.blocking_dependencies)

    def test_missing_unit_denied(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_dep_")
        runtime_path = _write_payload(tmpdir, _valid_payload())
        result = admit.check_admission("no.such.unit", runtime_file=runtime_path)
        self.assertFalse(result.admitted)


# ═══════════════════════════════════════════════════════════════════════════
# 10. WIP budget (§5.4)
# ═══════════════════════════════════════════════════════════════════════════


class WIPBudgetTests(unittest.TestCase):
    """Under budget → admitted; at/over budget → denied."""

    def _active_units(self, n, tier="setup"):
        """n active units in the given tier (setup budget default = 1)."""
        units = []
        for i in range(n):
            units.append(_valid_unit(
                unit_id="u{0}".format(i), runtime_status="active",
                loop_state=_active_loop_state(
                    agent_phase="plan", loop_count=0, cas_version=0, tier=tier),
                gate_state=_valid_gate_state(),
            ))
        return _valid_payload(units=units)

    def test_under_budget_admitted(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_wip_")
        runtime_path = _write_payload(tmpdir, self._active_units(0, tier="setup"))
        lp = _log_path(tmpdir)
        result = admit.check_wip_budget("setup", runtime_file=runtime_path,
                                        log_path=lp, unit_id="new")
        self.assertTrue(result.admitted)
        self.assertEqual(result.budget, 1)
        events = elog.read_events(log_path=lp)
        self.assertEqual(events[-1]["event_type"], "wip_admit")

    def test_at_budget_denied(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_wip_")
        # setup budget = 1; one active unit already → at budget.
        runtime_path = _write_payload(tmpdir, self._active_units(1, tier="setup"))
        lp = _log_path(tmpdir)
        result = admit.check_wip_budget("setup", runtime_file=runtime_path,
                                        log_path=lp, unit_id="new")
        self.assertFalse(result.admitted)
        self.assertEqual(result.budget, 1)
        self.assertEqual(result.active_count, 1)
        events = elog.read_events(log_path=lp)
        self.assertEqual(events[-1]["event_type"], "wip_deny")

    def test_over_budget_denied(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_wip_")
        # inner budget = 5; six active units → over.
        runtime_path = _write_payload(tmpdir, self._active_units(6, tier="inner"))
        result = admit.check_wip_budget("inner", runtime_file=runtime_path)
        self.assertFalse(result.admitted)
        self.assertEqual(result.active_count, 6)
        self.assertEqual(result.budget, 5)

    def test_count_self_excludes_evaluated_unit(self):
        """count_self=True excludes the unit being re-evaluated."""
        tmpdir = tempfile.mkdtemp(prefix="elog_wip_")
        runtime_path = _write_payload(tmpdir, self._active_units(1, tier="setup"))
        result = admit.check_wip_budget(
            "setup", runtime_file=runtime_path, unit_id="u0", count_self=True)
        # u0 excluded → 0 active → under budget.
        self.assertTrue(result.admitted)
        self.assertEqual(result.active_count, 0)

    def test_custom_budget_override(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_wip_")
        runtime_path = _write_payload(tmpdir, self._active_units(2, tier="setup"))
        result = admit.check_wip_budget(
            "setup", runtime_file=runtime_path, budgets={"setup": 5})
        self.assertTrue(result.admitted)
        self.assertEqual(result.budget, 5)

    def test_unknown_tier_denies(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_wip_")
        runtime_path = _write_payload(tmpdir, self._active_units(0, tier="setup"))
        result = admit.check_wip_budget("nonsense", runtime_file=runtime_path)
        self.assertFalse(result.admitted)
        self.assertEqual(result.budget, 0)

    def test_missing_runtime_fail_open(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_wip_")
        result = admit.check_wip_budget(
            "inner", runtime_file=Path(tmpdir) / "nope.json")
        self.assertTrue(result.admitted)  # no active units → trivially satisfied


# ═══════════════════════════════════════════════════════════════════════════
# 11. Restart consistency (state==log / state ahead / log ahead) — LOAD-BEARING
# ═══════════════════════════════════════════════════════════════════════════


class RestartConsistencyTests(unittest.TestCase):
    """recover_state: state==log OK; state ahead → phase_recovery; log ahead → conflict."""

    def test_state_equals_log_no_conflict(self):
        tmpdir = tempfile.mkdtemp(prefix="elog_restart_")
        lp = _log_path(tmpdir)
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"
        # Drive forward with the log on; state and log stay in sync.
        _drive_to_reflect(unit_id, runtime_path, log_path=lp)
        result = paro.recover_state(runtime_path, event_log=lp)
        self.assertEqual(result.conflicts, [])
        self.assertEqual(result.synthetic_events, [])
        self.assertEqual(result.units[unit_id]["cas_version"], 3)

    def test_state_ahead_of_log_synthesizes_phase_recovery(self):
        """Crash between state write and event append → restart synthesizes recovery.

        This is the state-first/event-second crash-gap proof (§5.2 point 3 +
        §3.5): the state committed but the event append was lost. recover_state
        detects on-disk > last-logged and records a phase_recovery event.
        """
        tmpdir = tempfile.mkdtemp(prefix="elog_restart_")
        lp = _log_path(tmpdir)
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"
        # Drive forward WITHOUT the log (state advances, log stays empty).
        paro.apply_transition(unit_id, "act", {}, runtime_file=runtime_path)
        paro.apply_transition(unit_id, "observe", {}, runtime_file=runtime_path)
        # Now the on-disk cas_version is 2 but the log is empty.
        result = paro.recover_state(runtime_path, event_log=lp)
        self.assertEqual(result.conflicts, [])
        synth = [e for e in result.synthetic_events if e["unit_id"] == unit_id]
        self.assertTrue(synth, "state-ahead-of-log should synthesize a recovery event")

    def test_log_ahead_of_state_fail_closes_unit(self):
        """Log ahead of state (dangerous) → unit fail-closed to blocked."""
        tmpdir = tempfile.mkdtemp(prefix="elog_restart_")
        lp = _log_path(tmpdir)
        runtime_path = _write_payload(tmpdir, _activated_payload())  # cas=0
        unit_id = "shitu.story.Skeleton"
        # Manually write events AHEAD of the on-disk state (cas 0,1,2).
        elog.append_events([
            elog.build_event(unit_id, "phase_enter", cas_version=0,
                             from_version=None, actor="t", to_phase="plan"),
            elog.build_event(unit_id, "phase_transition", cas_version=1,
                             from_version=0, actor="t",
                             from_phase="plan", to_phase="act"),
            elog.build_event(unit_id, "phase_transition", cas_version=2,
                             from_version=1, actor="t",
                             from_phase="act", to_phase="observe"),
        ], log_path=lp)
        result = paro.recover_state(runtime_path, event_log=lp)
        self.assertIn(unit_id, result.conflicts)
        self.assertEqual(result.units[unit_id]["runtime_status"], "blocked")
        self.assertEqual(result.units[unit_id]["recovery_status"], paro.RECOVERY_CONFLICT)

    def test_commit_recovery_writes_synthetic_events(self):
        """commit_recovery persists the phase_recovery / recovery_conflict markers."""
        tmpdir = tempfile.mkdtemp(prefix="elog_restart_")
        lp = _log_path(tmpdir)
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"
        paro.apply_transition(unit_id, "act", {}, runtime_file=runtime_path)
        result = paro.recover_state(runtime_path, event_log=lp)
        self.assertTrue(result.synthetic_events)
        before = len(elog.read_events(log_path=lp))
        n = elog.commit_recovery(result, log_path=lp)
        self.assertEqual(n, len(result.synthetic_events))
        after = elog.read_events(log_path=lp)
        self.assertEqual(len(after), before + n)
        types = [e["event_type"] for e in after]
        self.assertIn("phase_recovery", types)

    def test_restart_after_crash_then_continue(self):
        """End-to-end: crash after state-write, restart fills the gap, continue."""
        tmpdir = tempfile.mkdtemp(prefix="elog_restart_")
        lp = _log_path(tmpdir)
        runtime_path = _write_payload(tmpdir, _activated_payload())
        unit_id = "shitu.story.Skeleton"
        # Transition 1: log ON (state and log both advance to cas=1).
        paro.apply_transition(unit_id, "act", {}, runtime_file=runtime_path,
                              event_log=lp)
        # Transition 2: log OFF (state advances to cas=2, log stays at cas=1).
        # This simulates a crash between the state write and the event append.
        paro.apply_transition(unit_id, "observe", {}, runtime_file=runtime_path)
        # Restart: detect the gap and synthesize a phase_recovery event.
        result = paro.recover_state(runtime_path, event_log=lp)
        self.assertEqual(result.conflicts, [])
        self.assertTrue(any(e["unit_id"] == unit_id for e in result.synthetic_events))
        elog.commit_recovery(result, log_path=lp)
        # Now the log's last event for this unit matches the on-disk cas.
        last = elog.last_event_for_unit(unit_id, log_path=lp)
        self.assertEqual(last["cas_version"], 2)
        # A second restart is now consistent (no new synthetic events).
        result2 = paro.recover_state(runtime_path, event_log=lp)
        self.assertEqual(result2.conflicts, [])
        # The previously-synthesized phase_recovery closed the gap; restart 2
        # sees state==log and produces no NEW synthetic event for this unit.
        new_synth = [e for e in result2.synthetic_events if e["unit_id"] == unit_id]
        self.assertEqual(new_synth, [])


if __name__ == "__main__":
    unittest.main()
