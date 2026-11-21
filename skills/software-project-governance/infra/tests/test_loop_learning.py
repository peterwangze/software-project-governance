"""Verified observations and opportunities stay scoped to their originating work."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

INFRA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INFRA))

import loop_learning
import loop_event_log
import loop_paro_engine
import loop_workflow
from checks.flow_unit_runtime_v2 import validate_native_loop_payload


class LearningTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.file = self.root / "readout.txt"
        self.file.write_text("4 of 6 testers had to reopen their invoice.\n", encoding="utf-8")
        self.path = loop_workflow.runtime_path(self.root)
        self.start("invoice")

    def start(self, unit_id, **kwargs):
        return loop_workflow.start(self.root, unit_id=unit_id, tier="inner", goal="Read invoice total",
                                   acceptance="The receipt displays USD 31.", **kwargs)

    def state(self):
        return json.loads(self.path.read_bytes())

    def record(self, learning_id="r1", **kwargs):
        args = dict(unit_id="invoice", kind="opportunity", observation="Four testers reopened the invoice.",
                    action="Show the total on the receipt.", validation="The receipt displays USD 31.",
                    evidence=self.file.name)
        args.update(kwargs)
        return loop_learning.record(self.root, learning_id=learning_id, **args)

    def test_retry_conflict_and_unit_scoping(self):
        self.start("another")
        original = self.state()["flow_units"][0]
        entry = self.record()
        before = self.path.read_bytes()
        self.assertEqual(entry, self.record())
        self.assertEqual(before, self.path.read_bytes())
        with self.assertRaises(ValueError):
            self.record(action="A different direction")
        self.assertEqual(before, self.path.read_bytes())
        unit, other = self.state()["flow_units"]
        self.assertEqual(original, {k: v for k, v in unit.items() if k != "learning"})
        self.assertEqual(entry, loop_learning.opportunity(self.root, unit, "r1"))
        with self.assertRaises(ValueError):
            loop_learning.opportunity(self.root, other, "r1")
        self.record(kind="decision", unit_id="another")
        other = self.state()["flow_units"][1]
        with self.assertRaises(ValueError):
            loop_learning.opportunity(self.root, other, "r1")

    def test_feedback_after_delivery_and_expired_evidence(self):
        self.start("sum", check_command=[sys.executable, "-c", "print(31)"], expect_output="31")
        earlier = self.record("route", unit_id="sum", kind="decision")
        self.assertEqual(("G6", 0), (earlier["gate"], earlier["attempt"]))
        loop_workflow.verify_command(self.root, "sum")
        feedback = self.record(unit_id="sum")
        self.assertEqual(1, feedback["attempt"])
        self.assertEqual(earlier, self.record("route", unit_id="sum", kind="decision"))
        unit = loop_workflow._unit(self.state(), "sum")
        self.assertEqual("completed", unit["runtime_status"])
        entry = unit["learning"][-1]
        self.assertIsNone(loop_learning.learning_evidence_issue(self.root, entry))
        self.file.write_text("A new experiment", encoding="utf-8")
        before = self.path.read_bytes()
        self.assertIsNotNone(loop_learning.learning_evidence_issue(self.root, entry))
        with self.assertRaises(ValueError):
            loop_learning.opportunity(self.root, unit, "r1")
        with self.assertRaises(ValueError):
            self.record(unit_id="sum")
        self.file.unlink()
        self.assertIsNotNone(loop_learning.learning_evidence_issue(self.root, entry))
        self.assertEqual(before, self.path.read_bytes())

    def test_invalid_inputs_preserve_state(self):
        before = self.path.read_bytes()
        (self.root / "empty.txt").touch()
        for overrides in ({"learning_id": "../take"}, {"action": "  "}, {"validation": ""},
                          {"kind": "APPROVED"}, {"evidence": "../readout.txt"},
                          {"evidence": "empty.txt"}, {"evidence": self.file.as_posix()},
                          {"evidence": ".governance/flow-unit-runtime.json"}, {"evidence": "absent.txt"}):
            with self.subTest(overrides=overrides), self.assertRaises((ValueError, OSError)):
                self.record(**overrides)
            self.assertEqual(before, self.path.read_bytes())
        alias = self.root / "hardlink"
        try:
            os.link(self.file, alias)
        except OSError:
            return
        with self.assertRaises(ValueError):
            self.record(evidence="hardlink")
        self.assertEqual(before, self.path.read_bytes())

    def test_invalid_runtime_is_diagnosed_without_rewriting(self):
        entry = self.record()
        state = self.state()
        unit = state["flow_units"][0]
        for bad in (None, [None], [dict(entry, unit="unrelated")], [dict(entry, sha256=123)],
                    [dict(entry, evidence="../bad")], [dict(entry, gate="approval")],
                    [dict(entry, attempt=False)], [dict(entry, iteration=-1)], [entry, entry]):
            with self.subTest(bad=bad):
                unit["learning"] = bad
                self.assertTrue(validate_native_loop_payload(state))
                before = json.dumps(state).encode()
                self.path.write_bytes(before)
                with self.assertRaises(ValueError):
                    self.record(learning_id="fresh")
                self.assertEqual(before, self.path.read_bytes())

    def test_concurrent_retries_and_independent_decisions(self):
        ids = ["trial-1", "trial-2", "trial-1", "trial-2"]
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda key: self.record(key, kind="decision"), ids))
        self.assertEqual(results[0], results[2])
        self.assertEqual(results[1], results[3])
        entries = self.state()["flow_units"][0]["learning"]
        self.assertCountEqual(["trial-1", "trial-2"], [e["id"] for e in entries])

    def test_feedback_during_phase_computation_survives_cas_commit(self):
        def before_commit(unit, event):
            self.record("triage", kind="decision")
            return unit

        result = loop_paro_engine.apply_transition("invoice", "act", runtime_file=self.path,
                                                  side_effects=before_commit)
        self.assertTrue(result.success, result.reason)
        self.assertEqual("triage", result.unit["learning"][0]["id"])
        self.assertEqual(result.unit, self.state()["flow_units"][0])

    @unittest.skipUnless(os.name == "nt", "Windows lock contention")
    def test_windows_state_lock_timeout_preserves_state(self):
        from unittest.mock import patch
        from functools import partial

        before = self.path.read_bytes()
        one_try = partial(loop_event_log._acquire_win_lock, attempts=1)
        with loop_event_log._cross_process_lock(self.path):
            with patch.object(loop_event_log, "_acquire_win_lock", one_try):
                with self.assertRaises(TimeoutError):
                    self.record("contended")
                with loop_event_log._cross_process_lock(self.path, best_effort=True):
                    pass
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual("contended", self.record("contended")["id"])

    def test_bad_intent_and_source_binding_have_diagnostics(self):
        entry = self.record()
        self.start("next")
        state = self.state()
        source, following = state["flow_units"]
        for bad_intent in (None, {"basis": [], "source": {}, "prior_art": None},
                           {"basis": "receipt", "source": "user", "prior_art": [" "]}):
            source["intent"] = bad_intent
            self.assertTrue(any("intent" in err for err in validate_native_loop_payload(state)))
        del source["intent"]
        following.update(previous_unit_id="invoice", source_learning=entry["id"], goal=entry["action"],
                         acceptance=entry["validation"])
        self.assertFalse(any("source_learning" in err for err in validate_native_loop_payload(state)))
        for changes in ({"goal": "different"}, {"acceptance": "different"}, {"previous_unit_id": "other"},
                        {"source_learning": "other"}, {"source_learning": []}):
            with self.subTest(changes=changes):
                state["flow_units"][1] = dict(following, **changes)
                self.assertTrue(any("source_learning" in err for err in validate_native_loop_payload(state)))


if __name__ == "__main__":
    unittest.main()
