"""Normal-entry coverage for the opt-in process material reconciliation."""

from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest

INFRA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INFRA))
import loop_learning
import loop_workflow
from loop_material_check import check_materials
from review_record import write_review_record


class MaterialCheckTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.unit = self.start("pricing", "FIX-001")
        self.gov = self.root / ".governance"

    def start(self, unit, task):
        return loop_workflow.start(self.root, unit_id=unit, task=task, goal=unit,
                                   tier="inner", acceptance="The cited original can be reopened.")

    def learn(self, uid, ref, target):
        loop_learning.record(self.root, uid, ref, "note", "sample after recalculation",
                             "keep source", "reopen the original", target)

    def file(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def check(self):
        state = loop_workflow._payload(loop_workflow.runtime_path(self.root))
        return check_materials(self.root, state, loop_workflow._unit(state, "pricing"))

    def cli(self, code):
        proc = subprocess.run([sys.executable, "-X", "utf8", str(INFRA / "verify_workflow.py"),
                               "--project-root", str(self.root), "loop", "materials",
                               "--unit", "pricing", "--check"], cwd=self.root,
                              capture_output=True, encoding="utf-8")
        self.assertEqual(proc.returncode, code, proc.stdout + proc.stderr)
        return json.loads(proc.stdout)

    def test_retained_original_enters_through_real_learning_and_changes_are_detected(self):
        self.assertEqual(self.cli(0)["state"], "ok")
        target = ".governance/materials/pricing/raw/subfolder/sample.capture"
        original = self.file(target, "settlement=71")
        self.assertEqual(self.cli(2)["examples"], [{"kind": "unregistered", "path": target}])
        self.learn("pricing", "settlement", target)
        self.assertEqual(self.cli(0)["examples"], [])
        original.write_text("settlement=72", encoding="utf-8")
        self.assertEqual(self.cli(2)["counts"]["changed"], 1)
        original.unlink()
        self.assertEqual(self.cli(2)["examples"], [
            {"kind": "missing", "path": target, "ref": "learn:settlement"}])

    def test_task_directory_accounts_for_shared_ownership_and_ignores_unrelated_tree(self):
        self.start("second", "FIX-001")
        target = ".governance/materials/FIX-001/shared/sample.bin"
        self.file(target, "shared original")
        self.learn("second", "shared", target)
        self.file(".governance/materials/elsewhere/raw.capture", "unrelated")
        self.assertEqual(self.check()["state"], "ok")
        self.file(".governance/materials/FIX-001/shared/orphan.bin", "retained")
        result = self.check()
        self.assertEqual(result["counts"]["unregistered"], 1)
        self.assertEqual(result["examples"][0]["path"], ".governance/materials/FIX-001/shared/orphan.bin")

    def test_outputs_stay_bounded_and_check_is_read_only(self):
        for i in range(40):
            self.file(f".governance/materials/pricing/file-{i}.xyz", "retained")
        before = sorted(p.name for p in (self.gov / "materials/pricing").iterdir())
        result = self.check()
        self.assertEqual(result["counts"]["unregistered"], 40)
        self.assertEqual(len(result["examples"]), 3)
        self.assertLess(len(json.dumps(result).encode("utf-8")), 4096)
        self.assertEqual(before, sorted(p.name for p in (self.gov / "materials/pricing").iterdir()))

    def test_existing_evidence_row_and_non_path_prose(self):
        target = ".governance/materials/pricing/unusual.original"
        original = self.file(target, "output")
        (self.gov / "evidence-log.md").write_text(
            f"| EVD-1 | FIX-001 | QA | sampling | observed | {target} | QA | 2026-01-01 | G6 | ok |\n"
            "| EVD-2 | FIX-001 | QA | comparison | matched | 现场核对记录见本行 | QA | 2026-01-01 | G6 | ok |\n",
            encoding="utf-8")
        self.assertEqual(self.check()["state"], "ok")
        original.unlink()
        self.assertEqual(self.check()["examples"], [{"kind": "missing", "path": target, "ref": "EVD-1"}])

    def test_record_only_review_registers_the_original_without_a_gate_transition(self):
        target = ".governance/materials/pricing/review.md"
        report = self.file(target, "# Independent audit\n\n**审查结论**: **APPROVED**\n")
        receipt = write_review_record(task_id="FIX-001", round_n=0, result="APPROVED",
                                      report_path=target, root=self.root, unit_id="pricing",
                                      record_only=True, reviewer="Code Reviewer", require_loop=True)
        self.assertNotIn("error", receipt, receipt)
        self.assertEqual(self.cli(0)["state"], "ok")
        report.write_text("new bytes", encoding="utf-8")
        result = self.cli(2)
        self.assertEqual(result["examples"], [
            {"kind": "changed", "path": target, "ref": receipt["review_id"]}])

    def test_git_range_delta_is_not_an_unverifiable_local_original(self):
        self.file("review.md", "**APPROVED**")
        receipt = write_review_record(task_id="FIX-001", round_n=0, result="APPROVED",
                                      report_path="review.md", root=self.root, unit_id="pricing",
                                      record_only=True, scope="delta", delta_base="HEAD~1..HEAD",
                                      reviewer="Code Reviewer", require_loop=True)
        self.assertNotIn("error", receipt, receipt)
        self.assertEqual(self.cli(0)["state"], "ok")

    def test_gate_review_with_missing_receipt_digest_still_checks_authoritative_report(self):
        target = ".governance/materials/pricing/report.md"
        report = self.file(target, "**审查结论**: **APPROVED**")
        result = write_review_record(task_id="FIX-001", round_n=0, result="APPROVED",
                                     report_path=target, root=self.root, unit_id="pricing",
                                     reviewer="Code Reviewer", require_loop=True)
        self.assertNotIn("error", result, result)
        self.assertEqual(self.cli(0)["state"], "ok")
        receipt = self.gov / "review-FIX-001-R0.md"
        lines = receipt.read_text(encoding="utf-8").splitlines(keepends=True)
        self.assertTrue(any(line.startswith("- report_sha256:") for line in lines))
        receipt.write_text("".join(line for line in lines if not line.startswith("- report_sha256:")),
                           encoding="utf-8")
        self.assertGreaterEqual(self.cli(2)["counts"]["unverifiable"], 1)
        report.write_text("replacement report", encoding="utf-8")
        self.assertEqual(self.cli(2)["counts"]["changed"], 1)

    def test_directory_link_is_disclosed_without_descending(self):
        outside = self.file("adjacent/unrelated.capture", "never open this")
        managed = self.gov / "materials/pricing"
        managed.mkdir(parents=True)
        link = managed / "adjacent"
        if os.name == "nt":
            proc = subprocess.run(["cmd", "/d", "/c", "mklink", "/J", str(link), str(outside.parent)],
                                  capture_output=True)
            if proc.returncode:
                self.skipTest("directory junction unavailable")
            self.addCleanup(link.rmdir)
        else:
            link.symlink_to(outside.parent, target_is_directory=True)
            self.addCleanup(link.unlink)
        result = self.cli(2)
        self.assertEqual(result["counts"]["unverifiable"], 1)
        self.assertEqual(result["counts"]["unregistered"], 0)
        self.assertNotIn(outside.name, json.dumps(result))
