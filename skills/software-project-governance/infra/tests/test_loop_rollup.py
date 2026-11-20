"""Exercise rollup against independent native work units on disposable hosts."""
import sys
import tempfile
import unittest
from pathlib import Path

_INFRA = Path(__file__).resolve().parents[1]
if str(_INFRA) not in sys.path:
    sys.path.insert(0, str(_INFRA))

import loop_engine as le
import loop_workflow


class TestLoopRollup(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def start(self, key, tier, **options):
        loop_workflow.start(self.root, unit_id=key, tier=tier, goal="Deliver " + key,
                            acceptance="The client displays the agreed output.", **options)

    def test_rollup_reports_per_unit_rounds_and_active_tiers(self):
        self.start("product", "outer")
        self.start("release", "middle", parent="product")
        self.start("client", "inner", parent="release", check_command=[sys.executable, "-c", "print('different')"],
                   expect_output="expected")
        self.assertEqual(loop_workflow.verify_command(self.root, "client")["decision"], "iterate")
        result = le.rollup_loop_state(str(self.root))
        self.assertEqual(result["state"], "ready", result)
        self.assertEqual([(u["flow_unit_id"], u["active_loop_tier"], u["loop_count"]) for u in result["units"]],
                         [("product", "outer", 0), ("release", "middle", 0), ("client", "inner", 1)])
        self.assertEqual(result["summary"], {"total_units": 3, "active_loops": 3,
                                             "by_tier": {"setup": 0, "inner": 1, "middle": 1, "outer": 1}})
        self.assertTrue(result["no_global_stage"])
        for record in (result, result["summary"], *result["units"]):
            self.assertTrue({"current_stage", "global_stage", "single_stage", "stage", "current_loop"}.isdisjoint(record))

    def test_dormant_unit_remains_visible_without_counting_as_active(self):
        self.start("client", "inner")
        self.start("integration", "middle", dependencies=["client"])
        view = le.rollup_loop_state(self.root)
        self.assertEqual(view["state"], "ready", view)
        waiting = view["units"][1]
        self.assertEqual((waiting["flow_unit_id"], waiting["runtime_status"], waiting["waiting_on"]),
                         ("integration", "dormant", ["client"]))
        self.assertFalse(waiting["active_loop"])
        self.assertEqual(waiting["loop_count"], 0)
        self.assertEqual(view["summary"]["active_loops"], 1)
        self.assertEqual(view["summary"]["by_tier"]["middle"], 0)

    def test_no_runtime_is_empty(self):
        result = le.rollup_loop_state(self.root)
        self.assertEqual(result["state"], "empty")
        self.assertFalse(result["runtime_found"])
        self.assertTrue(result["no_global_stage"])
        self.assertEqual(result["units"], [])
        self.assertEqual(result["summary"]["active_loops"], 0)
        self.assertIn("loop start", result["message"])
class TestRollupFailClosed(unittest.TestCase):
    """A corrupt runtime.json → safe defaults, never raises."""

    def test_corrupt_runtime_identifies_present_but_invalid_file(self):
        """A damaged file must be distinguishable from a fresh project."""
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            gov.mkdir(parents=True, exist_ok=True)
            (gov / "flow-unit-runtime.json").write_text(
                "{not valid json", encoding="utf-8"
            )
            # Must NOT raise — fail-closed.
            result = le.rollup_loop_state(root=str(Path(td)))

        self.assertTrue(result["runtime_found"])
        self.assertEqual(result["state"], "invalid")
        self.assertEqual(result["units"], [])
        self.assertTrue(result["no_global_stage"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
