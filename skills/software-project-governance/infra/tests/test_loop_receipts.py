"""Verify work-unit evidence, release partitioning and the standard closure entry."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

INFRA = Path(__file__).resolve().parents[1]
if str(INFRA) not in sys.path:
    sys.path.insert(0, str(INFRA))

import closure_chain
import loop_workflow
from checks.gate_domain import release_unit_issues
from checks.loop_receipts import receipt_issues, require_task_exit


class NativeReceiptTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.gov = self.root / ".governance"
        self.gov.mkdir()

    def start(self, unit):
        loop_workflow.start(self.root, unit_id=unit, goal="Verify ledger", acceptance="Rows total seven",
                            tier="inner", gate=None, check_command=[sys.executable, "-c", "print(3+4)"],
                            expect_output="7")

    def test_standard_close_refuses_open_unit_without_starting_journal(self):
        self.start("FIX-901")
        spec = closure_chain.parse_chain_spec(closure_chain.STANDARD_TICKET_CLOSURE)
        with self.assertRaisesRegex(ValueError, "certified exit"):
            closure_chain.run_chain(spec, task="FIX-901", root=self.root, inputs={})
        self.assertFalse(closure_chain.default_event_log_path(self.root).exists())
        self.assertEqual([], receipt_issues(self.root))
        loop_workflow.verify_command(self.root, "FIX-901")
        require_task_exit(self.root, "FIX-901")
        self.assertEqual([], release_unit_issues(self.root))

    def test_tracker_writer_refuses_premature_completion_in_native_project(self):
        from task_row_update import execute_update

        tracker = self.gov / "plan-tracker.md"
        row = "| **P1** | FIX-901 | Export | — | 1.2.0 | deliver | approved |\n"
        tracker.write_text(row, encoding="utf-8")
        self.start("FIX-901")
        args = dict(target=tracker, task_id="FIX-901", from_state="approved",
                    to_state="completed", reason="Accept scoped result")
        result = execute_update(**args)
        self.assertEqual("cross_record_violation", result.code)
        self.assertEqual(row, tracker.read_text(encoding="utf-8"))
        loop_workflow.verify_command(self.root, "FIX-901")
        self.assertEqual("ok", execute_update(**args).code)

    def test_tracker_only_host_refuses_both_closure_modes_without_writes(self):
        from task_row_update import detect_row_state

        row = "| P1 | FIX-901 | Export | — | current | deliver | approved |\n"
        tracker = self.gov / "plan-tracker.md"
        tracker.write_text(row, encoding="utf-8")
        foreign = self.root / "another-host"
        (foreign / ".governance").mkdir(parents=True)
        (foreign / ".governance" / "plan-tracker.md").write_text(row, encoding="utf-8")
        loop_workflow.start(foreign, unit_id="FIX-901", goal="Another host", acceptance="Total seven",
                            tier="inner", check_command=[sys.executable, "-c", "print(7)"], expect_output="7")
        loop_workflow.verify_command(foreign, "FIX-901")
        args = ["--task", "FIX-901", "--from", "approved", "--to", "completed",
                "--reason", "Receive the scoped delivery", "--json"]
        spec = closure_chain.parse_chain_spec(closure_chain.STANDARD_TICKET_CLOSURE)
        for dry_run in (True, False):
            flags = ["--dry-run"] if dry_run else []
            for cli in ([str(INFRA / "verify_workflow.py"), "--project-root", str(self.root), "task-row-update"],
                        [str(INFRA / "task_row_update.py"), "--file", str(tracker)]):
                code = subprocess.run([sys.executable, *cli, *args, *flags], cwd=foreign, capture_output=True)
                self.assertNotEqual(0, code.returncode, code.stdout)
                refusal = json.loads(code.stdout)["refusal" if dry_run else "result"]
                self.assertEqual("cross_record_violation", refusal["code"])
                self.assertIn("loop start", refusal["detail"])
            with self.assertRaisesRegex(ValueError, "loop start"):
                closure_chain.run_chain(spec, task="FIX-901", root=self.root, inputs={}, dry_run=dry_run)
            self.assertEqual([tracker], list(self.gov.iterdir()))
            self.assertEqual(row, tracker.read_text(encoding="utf-8"))
        self.start("FIX-901")
        loop_workflow.verify_command(self.root, "FIX-901")
        for flags in (["--dry-run"], []):
            run = subprocess.run([sys.executable, str(INFRA / "verify_workflow.py"), "--project-root",
                                  str(self.root), "task-row-update", *args, *flags], cwd=foreign, capture_output=True)
            self.assertEqual(0, run.returncode, (run.stdout, run.stderr))
        self.assertEqual("completed", detect_row_state(tracker.read_text(encoding="utf-8").strip()))
        self.assertEqual(row, (foreign / ".governance" / "plan-tracker.md").read_text(encoding="utf-8"))

    def test_unregistered_ticket_cannot_borrow_another_unit_exit(self):
        self.start("FIX-901")
        loop_workflow.verify_command(self.root, "FIX-901")
        spec = closure_chain.parse_chain_spec(closure_chain.STANDARD_TICKET_CLOSURE)
        with self.assertRaisesRegex(ValueError, "no registered work unit"):
            closure_chain.run_chain(spec, task="FIX-902", root=self.root, inputs={})
        self.assertFalse(closure_chain.default_event_log_path(self.root).exists())

    def test_unit_named_like_a_ticket_cannot_close_it_when_the_owner_is_different(self):
        loop_workflow.start(self.root, unit_id="FIX-901", task="FIX-902", goal="Check an export",
                            tier="inner", acceptance="Rows total seven",
                            check_command=[sys.executable, "-c", "print(7)"], expect_output="7")
        loop_workflow.verify_command(self.root, "FIX-901")
        require_task_exit(self.root, "FIX-902")
        with self.assertRaisesRegex(ValueError, "no registered work unit"):
            require_task_exit(self.root, "FIX-901")

    def test_receipt_tampering_refuses_task_exit_and_health_audit(self):
        self.start("FIX-901")
        loop_workflow.verify_command(self.root, "FIX-901")
        self.assertEqual([], receipt_issues(self.root))
        receipt, = (self.gov / "loop-evidence").glob("*.json")
        receipt.write_bytes(receipt.read_bytes() + b" ")
        self.assertIn("observation bytes changed", receipt_issues(self.root)[0])
        with self.assertRaisesRegex(ValueError, "observation bytes changed"):
            require_task_exit(self.root, "FIX-901")

    def test_lost_state_with_retained_events_blocks_closure(self):
        self.start("FIX-901")
        loop_workflow.runtime_path(self.root).unlink()
        with self.assertRaisesRegex(ValueError, "state is missing"):
            require_task_exit(self.root, "FIX-901")
        self.assertTrue(receipt_issues(self.root))

    def test_valid_receipt_cannot_move_to_another_unit(self):
        for key in ("FIX-901", "FIX-902"):
            self.start(key)
            loop_workflow.verify_command(self.root, key)
        state = json.loads(loop_workflow.runtime_path(self.root).read_bytes())
        first, second = state["flow_units"]
        saved = first["gate_history"][0]["evidence_ref"]
        second["gate_history"][0]["evidence_ref"] = saved
        loop_workflow.runtime_path(self.root).write_text(json.dumps(state), encoding="utf-8")
        self.assertTrue(receipt_issues(self.root))
