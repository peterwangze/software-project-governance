"""A governed Git host can authorize a staged delivery only with the current work-unit receipt."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

INFRA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INFRA))


def create_fixture_commit(root):
    subprocess.run(["git", "-c", "core.hooksPath=" + str(root / "no-hooks"),
                    "commit", "--allow-empty", "-m", "fixture baseline"], cwd=root, check=True, capture_output=True)


def record_candidate(root, task, verdict="APPROVED", *, review_round=0, reviewer="Code Reviewer", files=()):
    from loop_workflow import start
    from review_record import write_review_record

    start(root, unit_id=task, tier="inner", goal="Deliver " + task,
          acceptance="The observed staged artifact matches its specification")
    tree = subprocess.check_output(["git", "write-tree"], cwd=root, text=True).strip()
    report = root / ".governance" / f"observation-{reviewer}-{review_round}.md"
    report.write_text(f"Candidate {tree} reviewed.\n**审查结论**: **{verdict}**\n", encoding="utf-8")
    receipt = write_review_record(root=root, task_id=task, round_n=review_round, result=verdict, reviewer=reviewer,
                                  report_path=report.relative_to(root).as_posix(), bind_tree=None if files else tree,
                                  bind_files=files,
                                  unit_id=task, record_only=True, require_loop=True)
    if "error" in receipt:
        raise AssertionError(receipt)
    return receipt


class GovernedHostCommitTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.env = {**os.environ, "SOFTWARE_PROJECT_GOVERNANCE_HOME": str(INFRA.parent)}
        self.git("init", "-q")
        self.git("config", "user.name", "Hook verifier")
        self.git("config", "user.email", "hook@example.invalid")
        for name in ("pre-commit", "prepare-commit-msg", "commit-msg", "post-commit"):
            hook = self.root / ".git" / "hooks" / name
            shutil.copyfile(INFRA / "hooks" / name, hook)
            hook.chmod(0o755)
        self.gov = self.root / ".governance"

    def git(self, *args, ok=True):
        result = subprocess.run(["git", *args], cwd=self.root, env=self.env, capture_output=True,
                                encoding="utf-8", errors="replace")
        self.assertEqual(ok, result.returncode == 0, result.stdout + result.stderr)
        return (result.stdout + result.stderr).strip()

    def stage(self, path):
        file = self.root / path
        file.parent.mkdir(exist_ok=True, parents=True)
        file.write_text("new product\n", encoding="utf-8")
        self.git("add", "--", path)

    def test_same_candidate_requires_unit_even_with_historical_approval(self):
        create_fixture_commit(self.root)
        self.gov.mkdir()
        self.stage("src/invoice.py")
        original = self.git("rev-parse", "HEAD")
        self.assertIn("loop start", self.git("commit", "-m", "FIX-711: invoice", ok=False))
        (self.gov / "plan-tracker.md").write_text("| P1 | FIX-711 | Historical work |")
        self.assertIn("loop start", self.git("commit", "-m", "FIX-711: invoice", ok=False))
        (self.gov / "plan-tracker.md").write_bytes(
            (INFRA / "tests" / "fixtures" / "plan-tracker-id-first-20col.md").read_bytes())
        self.stage("skills/invoice.py")
        legacy = self.gov / "evidence-log.md"
        legacy.write_text("| REVIEW-FIX-711-R0-CODE-REVIEWER | FIX-711 | old work | APPROVED_WITH_NOTES | unresolved_blockers=0 |")
        old = legacy.read_bytes()
        self.assertIn("loop start", self.git("commit", "-m", "FIX-711: invoice", ok=False))
        self.assertEqual(original, self.git("rev-parse", "HEAD"))
        self.assertEqual(old, legacy.read_bytes())
        record_candidate(self.root, "FIX-711")
        self.git("commit", "-m", "FIX-711: invoice")
        self.assertNotEqual(original, self.git("rev-parse", "HEAD"))

    def test_ordinary_unmanaged_git(self):
        self.stage("src/invoice.py")
        self.git("commit", "-m", "Invoice work")

    def test_governance_intake_can_be_committed_before_a_unit_exists(self):
        self.stage(".governance/plan-tracker.md")
        self.git("commit", "-m", "Initialize project notes")

    def test_first_product_commit_requires_the_exact_reviewed_tree(self):
        from review_facts import derive_review_facts

        self.stage("src/invoice.py")
        record_candidate(self.root, "invoice", files=["src/invoice.py"])
        self.assertIn("exact complete Git tree", self.git("commit", "-m", "invoice: first release", ok=False))
        signed = record_candidate(self.root, "invoice", review_round=1)
        reviewed_tree = self.git("write-tree")
        self.stage("app/extra.js")
        self.assertIn("M7.4 BLOCKED", self.git("commit", "-m", "invoice: first release", ok=False))
        self.git("rm", "--cached", "--", "app/extra.js")
        self.git("commit", "-m", "invoice: first release")
        head = self.git("rev-parse", "HEAD")
        self.assertEqual(reviewed_tree, self.git("rev-parse", "HEAD^{tree}"))
        replay = derive_review_facts(self.root, "invoice", [signed["review_id"]], commit=head)
        self.assertTrue(replay["git"]["initial"])
