"""Recover the user's request, a tested choice and feedback via installed CLI entry points."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CLI = Path(__file__).resolve().parents[1] / "verify_workflow.py"


class LoopLearningJourneyTest(unittest.TestCase):
    def setUp(self):
        host = tempfile.TemporaryDirectory(prefix="invoice host ")
        self.addCleanup(host.cleanup)
        self.root = Path(host.name)

    def cli(self, *args, success=True):
        run = subprocess.run([sys.executable, "-X", "utf8", str(CLI),
                              "--project-root", str(self.root), *args],
                             cwd=self.root, capture_output=True, encoding="utf-8")
        self.assertEqual(run.returncode == 0, success, run.stdout + run.stderr)
        if args[0] == "governance-bootstrap":
            self.assertLessEqual(len(run.stdout.encode("utf-8")), 8192)
        return json.loads(run.stdout)

    def test_reconcile_export_then_select_user_feedback(self):
        quote = "I need to reconcile my statement by reopening the invoice export."
        total = "USD 19.99"
        (self.root / "statement.csv").write_text("item,amount\nbook,15.00\ncard,4.99\n", encoding="utf-8")
        exporter = self.root / "export.py"
        exporter.write_text("from pathlib import Path\n"
                            "rows = Path('statement.csv').read_text().splitlines()\n"
                            "Path('invoice.csv').write_text('\\n'.join(rows[:2]))\n", encoding="utf-8")
        (self.root / "reconcile.py").write_text(
            "import csv, subprocess, sys\nfrom decimal import Decimal\n"
            "subprocess.run([sys.executable, sys.argv[1] if len(sys.argv) > 1 else 'export.py'], check=True)\n"
            "with open('invoice.csv', newline='') as stream:\n"
            "    total = sum(Decimal(row['amount']) for row in csv.DictReader(stream))\n"
            "print(f'USD {total:.2f}')\n", encoding="utf-8")
        criterion = "The total in the reopened CSV matches the statement."
        self.cli("loop", "start", "--unit", "invoice", "--tier", "inner", "--intent", quote,
                 "--goal", "Export all invoice rows", "--acceptance", criterion,
                 "--check-command", json.dumps([sys.executable, "reconcile.py"]), "--expect-output", total)
        self.assertEqual(self.cli("loop", "verify", "--unit", "invoice", success=False)["decision"], "iterate")
        failed = self.cli("loop", "status", "--unit", "invoice", "--json")
        prior_run = ".governance/" + failed["last_review"]["evidence_ref"]
        evidence = json.loads((self.root / prior_run).read_text(encoding="utf-8"))
        self.assertEqual(evidence["stdout"].strip(), "USD 15.00")
        candidate = self.root / "export_all.py"
        candidate.write_text("from shutil import copyfile\ncopyfile('statement.csv', 'invoice.csv')\n",
                             encoding="utf-8")
        trial = subprocess.run([sys.executable, "reconcile.py", candidate.name], cwd=self.root,
                               check=True, capture_output=True, encoding="utf-8")
        self.assertEqual(trial.stdout.strip(), total)
        (self.root / "comparison.txt").write_text(
            f"First export ({prior_run}): {evidence['stdout']}\nAll rows: {trial.stdout}", encoding="utf-8")
        self.cli("loop", "learn", "--unit", "invoice", "--id", "all-rows", "--kind", "decision",
                 "--observation", "Reopening the first export yields 15.00. Exporting all rows yields 19.99.",
                 "--action", "Use the complete source rows in the export.",
                 "--validation", criterion, "--evidence", "comparison.txt")
        retry = self.cli("governance-bootstrap", "--format", "json")["loops"]["units"][0]
        self.assertEqual(retry["intent"]["basis"], quote)
        self.assertEqual(retry["learning"][-1]["id"], "all-rows")
        self.assertEqual(retry["gate_status"], "failed")
        self.assertEqual(retry["acceptance"], criterion)
        exporter.write_bytes(candidate.read_bytes())
        self.assertEqual(self.cli("loop", "verify", "--unit", "invoice")["decision"], "exit")

        feedback = self.root / "feedback.txt"
        feedback.write_text("The book buyer needs to reconcile refunds as well.", encoding="utf-8")
        next_goal = "Show refunds as negative rows in the export."
        next_check = "Reopening an invoice after a 2.00 refund yields USD 17.99."
        self.cli("loop", "learn", "--unit", "invoice", "--id", "refunds", "--kind", "opportunity",
                 "--observation", feedback.read_text(encoding="utf-8"), "--action", next_goal,
                 "--validation", next_check, "--evidence", "feedback.txt")
        report = self.cli("loop", "status")
        self.assertEqual(len(report["units"]), 1)
        delivery = report["units"][0]
        self.assertEqual(delivery["runtime_status"], "completed")
        self.assertIn("Optional next step: review opportunity refunds", delivery["next_action"])
        self.assertEqual(delivery["acceptance"], criterion)
        self.assertEqual([entry["id"] for entry in delivery["learning"]], ["all-rows", "refunds"])
        self.assertIsNone(delivery["learning"][1]["evidence_issue"])
        original_feedback = feedback.read_bytes()
        feedback.write_text("Unrelated report.", encoding="utf-8")
        unverified = self.cli("loop", "status", "--unit", "invoice", "--json")
        self.assertNotIn("Optional next step", unverified["next_action"])
        feedback.write_bytes(original_feedback)
        successor = self.cli("loop", "start", "--unit", "refund-export", "--tier", "inner",
                             "--after", "invoice", "--from-learning", "refunds")
        self.assertEqual((successor["goal"], successor["acceptance"]), (next_goal, next_check))
        recovered = self.cli("loop", "status", "--unit", "refund-export", "--json")
        self.assertEqual((recovered["source_learning"], recovered["previous_unit_id"]), ("refunds", "invoice"))
        self.assertEqual(recovered["intent"]["basis"], quote)
        selected = self.cli("loop", "status", "--unit", "invoice", "--json")
        self.assertNotIn("Optional next step", selected["next_action"])
        feedback.write_text("A different statement from another user.", encoding="utf-8")
        stale = self.cli("loop", "status", "--unit", "invoice", "--json")
        self.assertTrue(stale["learning"][1]["evidence_issue"])
        self.assertEqual((stale["runtime_status"], stale["gate_status"]), ("completed", "passed"))
        self.assertNotIn("Optional next step", stale["next_action"])
        self.cli("loop", "start", "--unit", "second-copy", "--tier", "inner", "--after", "invoice",
                 "--from-learning", "refunds", success=False)

    def test_bootstrap_retains_latest_decision_and_opportunity_with_long_evidence(self):
        quote = "核对账单导出的结果。" * 480
        self.cli("loop", "start", "--unit", "long-history", "--intent", quote, "--tier", "inner",
                 "--goal", "导出账单", "--acceptance", "重新打开文件，合计与账单一致")
        (self.root / "comparison.txt").write_text("A comparison of the two exports.", encoding="utf-8")
        for record_id, kind in (("first", "decision"), ("feedback", "opportunity"), ("latest", "decision")):
            self.cli("loop", "learn", "--unit", "long-history", "--id", record_id, "--kind", kind,
                     "--observation", "用户重开文件做了核对。" * 200, "--action", "导出全部行。" * 200,
                     "--validation", "核对原始行数。" * 200, "--evidence", "comparison.txt")
        unit = self.cli("governance-bootstrap", "--format", "json")["loops"]["units"][0]
        self.assertEqual(unit["flow_unit_id"], "long-history")
        self.assertEqual(unit["learning_count"], 3)
        self.assertEqual([item["id"] for item in unit["learning"]], ["feedback", "latest"])
        full = self.cli("loop", "status", "--unit", "long-history", "--json")
        self.assertEqual(full["intent"]["basis"], quote)
        self.assertEqual([item["id"] for item in full["learning"]], ["first", "feedback", "latest"])

    def test_opportunity_must_meet_registered_task_acceptance(self):
        self.cli("loop", "start", "--unit", "invoice", "--tier", "inner", "--goal", "Export totals",
                 "--acceptance", "Export opens", "--intent", "Help me reconcile the statement",
                 "--check-command", json.dumps([sys.executable, "-c", "print(19.99)"]), "--expect-output", "19.99")
        self.cli("loop", "verify", "--unit", "invoice")
        (self.root / "feedback.txt").write_text("Buyers need a separate fee row.", encoding="utf-8")
        goal, check = "Export fees", "The reopened CSV shows each fee separately"
        self.cli("loop", "learn", "--unit", "invoice", "--kind", "opportunity", "--id", "fees",
                 "--observation", "Buyers need a separate fee row.", "--action", goal,
                 "--validation", check, "--evidence", "feedback.txt")
        for task, title, criterion in (("FIX-801", "Restore email", "The recovery email arrives"),
                                       ("FIX-802", goal, check)):
            self.cli("change-triage", "--task", task, "--title", title, "--acceptance", criterion,
                     "--priority", "P1", "--files", f"{task}.py", "--demand-source", "user-named",
                     "--demand-basis", f"User requested {title}")
        args = ("loop", "start", "--tier", "inner", "--after", "invoice", "--from-learning", "fees")
        runtime = self.root / ".governance/flow-unit-runtime.json"
        before = runtime.read_bytes()
        for overrides in ((), ("--acceptance", check), ("--intent", "Help me reconcile the statement",
                                                      "--goal", goal, "--acceptance", check)):
            with self.subTest(overrides=overrides):
                self.cli(*args, "--unit", "email-as-fees", "--task", "FIX-801", *overrides, success=False)
                self.assertEqual(runtime.read_bytes(), before)
        adopted = self.cli(*args, "--unit", "fee-export", "--task", "FIX-802")
        self.assertEqual((adopted["goal"], adopted["acceptance"], adopted["source_learning"]), (goal, check, "fees"))

    def test_intent_only_uses_valid_task_and_schema_from_triage_record(self):
        directory = self.root / ".governance/change-triage"
        directory.mkdir(parents=True)
        path = directory / "FIX-801.json"
        metadata = {"demand_source": "user-named", "demand_basis": "User requested email recovery",
                    "prior_art": ["Previous email trial"], "acceptance": "Recovery email arrives"}
        for binding in ({}, {"schema_version": 1}, {"task_id": "FIX-801"},
                        {"task_id": "FIX-802", "schema_version": 1},
                        {"task_id": "FIX-801", "schema_version": 2},
                        {"task_id": "FIX-801", "schema_version": True},
                        {"task_id": "FIX-801", "schema_version": 1, "demand_source": "unrecognized"},
                        {"task_id": "FIX-801", "schema_version": 1, "demand_basis": "  "}):
            with self.subTest(binding=binding):
                raw = json.dumps({**metadata, **binding}).encode("utf-8")
                path.write_bytes(raw)
                self.cli("loop", "start", "--unit", "mail", "--task", "FIX-801", "--tier", "inner",
                         "--goal", "Restore email", success=False)
                self.assertFalse((directory.parent / "flow-unit-runtime.json").exists())
                self.assertEqual(path.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
