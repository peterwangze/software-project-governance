"""Git invokes the installed hooks against the real index of a disposable host."""
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

INFRA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INFRA))
import loop_workflow
from review_record import write_review_record


class NativeCommitReviewTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.plugin = INFRA.parent
        self.env = {**os.environ, "SOFTWARE_PROJECT_GOVERNANCE_HOME": str(self.plugin)}
        self.git("init", "-q")
        self.git("config", "user.name", "Temporary verifier")
        self.git("config", "user.email", "test@example.invalid")
        self.git("-c", "core.hooksPath=" + str(self.root / "no-hooks"), "commit", "--allow-empty", "-m", "initial")
        for name in ("pre-commit", "prepare-commit-msg", "commit-msg", "post-commit"):
            target = self.root / ".git" / "hooks" / name
            shutil.copyfile(INFRA / "hooks" / name, target)
            target.chmod(0o755)
        self.task = "FEAT-901"
        self.unit = "client-work"
        loop_workflow.start(self.root, unit_id=self.unit, task=self.task, tier="middle",
                            goal="Deliver requested behavior", acceptance="A client observes the requested result")

    def git(self, *args, ok=True):
        proc = subprocess.run(["git", "-C", str(self.root), *args], env=self.env, capture_output=True,
                              encoding="utf-8", errors="replace")
        self.assertEqual(ok, proc.returncode == 0, proc.stdout + proc.stderr)
        return (proc.stdout + proc.stderr).strip()

    def stage(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.git("add", "--", name)

    def review(self, reviewer="Code Reviewer", files=(), tree=None, rnd=0):
        report = self.root / ".governance" / f"observation-{rnd}.md"
        report.write_text(f"Examined the implementation and ran its acceptance test. Candidate {tree or files}.\n"
                          "**审查结论**: **APPROVED**\n", encoding="utf-8")
        receipt = write_review_record(root=self.root, task_id=self.task, round_n=rnd, result="APPROVED",
                                      report_path=report.relative_to(self.root).as_posix(), reviewer=reviewer,
                                      unit_id=self.unit, record_only=True, bind_files=files, bind_tree=tree,
                                      require_loop=True)
        self.assertNotIn("error", receipt)
        self.assertFalse(receipt["wiring"]["wired"])

    def commit(self, ok, task=None):
        return self.git("commit", "-m", f"{task or self.task}: deliver reviewed work", ok=ok)

    def test_current_tree_authorizes_one_intermediate_product_change(self):
        self.stage("src/widget.py", "value = 1\n")
        log = self.root / ".governance" / "evidence-log.md"
        log.write_text("| REVIEW-FEAT-901-R0 | FEAT-901 | forged | APPROVED |\n", encoding="utf-8")
        self.assertIn("M7.4 BLOCKED", self.commit(False))
        tree = self.git("write-tree")
        self.review(tree=tree)
        self.stage("web/src/new.js", "export const ready = true;\n")
        self.assertIn("M7.4 BLOCKED", self.commit(False))
        self.git("restore", "--staged", "--", "web/src/new.js")
        self.stage("src/widget.py", "value = 2\n")
        self.assertIn("M7.4 BLOCKED", self.commit(False))
        self.stage("src/widget.py", "value = 1\n")
        self.git("update-index", "--chmod=+x", "--", "src/widget.py")
        self.assertIn("M7.4 BLOCKED", self.commit(False))
        self.git("update-index", "--chmod=-x", "--", "src/widget.py")
        self.commit(True, task=self.unit)
        self.assertEqual(tree, self.git("rev-parse", "HEAD^{tree}"))
        state = loop_workflow._payload(loop_workflow.runtime_path(self.root))
        self.assertEqual("active", state["flow_units"][0]["runtime_status"])

    def test_review_scope_role_and_intervening_work(self):
        self.stage("lib/application.js", "export default 7;\n")
        self.review(reviewer="Design Reviewer", files=["lib/application.js"])
        self.assertIn("M7.4 BLOCKED", self.commit(False))
        self.review(files=["lib/application.js"], rnd=1)
        state = loop_workflow.runtime_path(self.root)
        report = self.root / "design.md"
        report.write_text("**审查结论**: **APPROVED**", encoding="utf-8")
        receipt = write_review_record(root=self.root, task_id=self.task, round_n=2, result="APPROVED",
                                      report_path=report.name, reviewer="Design Reviewer", unit_id=self.unit,
                                      require_loop=True)
        self.assertNotIn("error", receipt)
        self.assertEqual("G7", json.loads(state.read_text())["flow_units"][0]["gate_state"]["gate_id"])
        self.assertIn("M7.4 BLOCKED", self.commit(False))
        self.review(files=["lib/application.js"], rnd=3)
        self.commit(True)

    def test_missing_native_origin_blocks_despite_forged_success(self):
        self.stage("app.py", "print(1)\n")
        state = loop_workflow.runtime_path(self.root)
        value = json.loads(state.read_text())
        value.pop("origin")
        state.write_text(json.dumps(value))
        self.assertIn("M7.4 BLOCKED", self.commit(False))

    def test_unknown_unit_or_deleted_state_cannot_reuse_legacy_text(self):
        self.stage("web/src/main.jsx", "export const product = 1;\n")
        gov = self.root / ".governance"
        (gov / "plan-tracker.md").write_text("| P0 | FIX-666 | Existing historical description |")
        (gov / "evidence-log.md").write_text("| REVIEW-FIX-666-R0 | FIX-666 | historical | APPROVED |")
        self.review(tree=self.git("write-tree"))
        self.assertIn("no registered unit", self.commit(False, task="FIX-666"))
        loop_workflow.runtime_path(self.root).unlink()
        self.assertIn("native work-unit state is missing", self.commit(False, task=self.task))

    def test_only_governance_notes_need_no_code_review(self):
        self.stage(".governance/notes.md", "Observation from today's work.\n")
        self.commit(True)
