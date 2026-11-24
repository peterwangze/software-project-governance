"""Historical receipt scans still verify each report, ledger binding and live release gate."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import loop_workflow
import review_record
from checks import loop_receipts
from tests.test_review_record import _prepare_review_repository


class PublishedReceiptScanTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        self.commit = _prepare_review_repository(self.root)
        self.tree = subprocess.check_output(
            ["git", "-C", str(self.root), "rev-parse", "HEAD^{tree}"], text=True).strip()

    def start(self, task, tier="inner", **kwargs):
        loop_workflow.start(self.root, unit_id=task, tier=tier, goal=task,
                            acceptance="Verify the signed report.", **kwargs)

    def review(self, task, attempt, verdict, version="", **kwargs):
        path = self.root / f"report-{task}-{attempt}.md"
        path.write_text(f"Checked {version} tree {self.tree}.\n**审查结论**: **{verdict}**\n", encoding="utf-8")
        result = review_record.write_review_record(
            task_id=task, round_n=attempt, result=verdict, report_path=path.name,
            bind_tree=self.tree, root=self.root, require_loop=True, **kwargs)
        self.assertNotIn("error", result, result)
        return path

    def test_rework_and_exit_share_objects_but_reread_each_report(self):
        self.start("FIX-701")
        first = self.review("FIX-701", 0, "NEEDS_CHANGE", reviewer="QA")
        second = self.review("FIX-701", 1, "APPROVED", reviewer="QA")
        with mock.patch.object(review_record, "_git_output", wraps=review_record._git_output) as git:
            self.assertEqual(loop_receipts.receipt_issues(self.root), [])
        self.assertEqual([c.args[1] for c in git.call_args_list], ["cat-file"])
        self.assertEqual(set(git.call_args.kwargs["input_bytes"].decode().splitlines()),
                         {self.tree, self.commit + "^{commit}"})

        verify = review_record.PublishedReviewObjects.verify

        def change_next(objects, review, root):
            result = verify(objects, review, root)
            if review.name.endswith("R0.md"):
                second.write_bytes(b"changed during scan")
            return result

        with mock.patch.object(review_record.PublishedReviewObjects, "verify", change_next):
            issues = loop_receipts.receipt_issues(self.root)
        self.assertEqual(len(issues), 1, issues)
        self.assertIn("FIX-701 G6 #1: review evidence CONFLICT", issues[0])
        first.unlink()
        with mock.patch.object(review_record, "_git_output", wraps=review_record._git_output) as git:
            issues = loop_receipts.receipt_issues(self.root)
        self.assertIn("FIX-701 G6 #0: review evidence UNKNOWN", issues[0])
        self.assertIn("FIX-701 G6 #1: review evidence CONFLICT", issues[1])
        self.assertEqual(git.call_count, 1)

    def test_failed_or_incomplete_batch_uses_individual_verification(self):
        self.start("FIX-702")
        self.review("FIX-702", 0, "APPROVED", reviewer="QA")
        individual = review_record._git_output
        for response in (None, self.tree + " tree", "unexpected\nresponse"):
            with self.subTest(response=response):
                def git(root, *args, **kwargs):
                    if kwargs.get("input_bytes"):
                        return response
                    return individual(root, *args, **kwargs)
                with mock.patch.object(review_record, "_git_output", side_effect=git) as calls:
                    self.assertEqual(loop_receipts.receipt_issues(self.root), [])
                self.assertEqual([c.args[1] for c in calls.call_args_list], ["cat-file", "rev-parse", "cat-file"])
        with mock.patch.object(review_record, "PublishedReviewObjects", side_effect=PermissionError("cannot resolve")):
            self.assertEqual(loop_receipts.receipt_issues(self.root), [])

    def test_release_checks_historical_dependencies_and_live_release_binding(self):
        self.start("FIX-703")
        self.review("FIX-703", 0, "APPROVED", reviewer="QA", bind_files=["subject.txt"])
        self.start("REL-701", tier="middle", gate="G9", dependencies=["FIX-703"], release_version="1.0.0")
        self.review("REL-701", 0, "APPROVED", version="1.0.0", reviewer="Release Reviewer", bind_files=["subject.txt"])
        with mock.patch.object(review_record, "_git_output", wraps=review_record._git_output) as git:
            self.assertEqual(loop_workflow.release_issues(self.root, "REL-701", "1.0.0"), [])
        self.assertEqual(sum(bool(c.kwargs.get("input_bytes")) for c in git.call_args_list), 1)
        (self.root / "subject.txt").write_bytes(b"worktree changed")
        self.assertEqual(loop_receipts.receipt_issues(self.root), [])
        issues = loop_workflow.release_issues(self.root, "REL-701", "1.0.0")
        self.assertTrue(any("CONFLICT" in issue for issue in issues), issues)

    def test_observation_only_scan_does_not_open_a_review_ledger_or_git(self):
        self.start("command", check_command=[sys.executable, "-c", "print('ok')"], expect_output="ok")
        loop_workflow.verify_command(self.root, "command")
        with mock.patch("authority_ledger.LedgerWriter", side_effect=AssertionError), \
             mock.patch.object(review_record, "_git_output", side_effect=AssertionError):
            self.assertEqual(loop_receipts.receipt_issues(self.root), [])
