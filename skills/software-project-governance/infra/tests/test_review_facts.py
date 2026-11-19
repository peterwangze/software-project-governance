"""Review reuse against real Git trees and review-record ledger transactions."""

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_record import derive_review_facts, verify_review_trust, write_review_record


class ReviewFactsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "dev@example.org")
        self.git("config", "user.name", "Developer")
        self.git("config", "core.hooksPath", "disabled")
        self.git("config", "core.autocrlf", "false")
        (self.root / ".gitignore").write_text(".governance/\nreport*.md\n")
        (self.root / ".gitattributes").write_text("*.txt text eol=lf\n")
        (self.root / "first.txt").write_bytes(b"baseline\n")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD")
        (self.root / "first.txt").write_bytes(b"reviewed\r\n")
        self.git("add", "first.txt")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True,
                              text=True, check=True).stdout.strip()

    def sign(self, n, *paths, verdict="APPROVED"):
        report = f"report{n}.md"
        (self.root / report).write_text(f"review finding for round {n}\n")
        args = {"abort_reason": "reviewer terminated"} if verdict in ("ABORTED", "UNKNOWN") else {}
        result = write_review_record(task_id="FIX-301", round_n=n, result=verdict,
                                     reviewer=f"Auditor {n}", report_path=report,
                                     root=self.root, bind_files=paths, **args)
        self.assertNotIn("error", result, result)
        return result["review_id"]

    def derive(self, *refs, **args):
        return derive_review_facts(self.root, "FIX-301", refs, **args)

    def test_union_and_exact_target_including_clean_filtered_bytes(self):
        r0 = self.sign(0, "first.txt", verdict="APPROVED_WITH_NOTES")
        (self.root / "第二 = 文件.txt").write_bytes(b"new\n")
        self.git("add", "第二 = 文件.txt")
        r1 = self.sign(1, "第二 = 文件.txt")
        with self.assertRaisesRegex(ValueError, "unreviewed"):
            self.derive(r1)
        # Review objects match the index even if the live working bytes change.
        (self.root / "first.txt").write_bytes(b"later work\n")
        staged = self.derive(r1, r0)
        self.assertEqual(staged["files_changed"], ["first.txt", "第二 = 文件.txt"])
        self.assertEqual(staged["review"]["conclusion"], "APPROVED_WITH_NOTES")
        self.assertEqual(len(staged["review"]["records"][0]["report_sha256"]), 64)
        self.git("commit", "-qm", "delivery")
        sha = self.git("rev-parse", "HEAD")
        committed = self.derive(r0, r1, commit=sha)
        self.assertEqual(committed["git"], {"base": self.base, "commit": sha, "tree": staged["git"]["tree"]})
        self.git("add", "first.txt")
        self.assertEqual(self.derive(r0, r1, commit=sha), committed)
        with self.assertRaisesRegex(ValueError, "no changed files"):
            self.derive(r0, r1, base="HEAD", commit=sha)

    def test_post_review_edit_new_path_and_tampered_original_refuse_without_writes(self):
        ref = self.sign(0, "first.txt")
        (self.root / "first.txt").write_bytes(b"substituted\n")
        self.git("add", "first.txt")
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with self.assertRaisesRegex(ValueError, "differs"):
            self.derive(ref)
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        (self.root / "report0.md").write_text("substitution")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            self.derive(ref)
        (self.root / "report0.md").unlink()
        with self.assertRaises(ValueError):
            self.derive(ref)
        with self.assertRaises(ValueError):
            self.derive("REVIEW-FIX-999-R0")

    def test_new_round_can_re_review_same_file_and_staged_deletion(self):
        r0 = self.sign(0, "first.txt", verdict="NEEDS_CHANGE")
        self.assertEqual(self.derive(r0)["review"]["conclusion"], "NEEDS_CHANGE")
        self.git("rm", "-f", "first.txt")
        r1 = self.sign(1, "first.txt")
        result = self.derive(r0, r1)
        self.assertEqual(result["review"]["conclusion"], "APPROVED")
        self.assertIn("1 file changed", result["diff_summary"])
        self.git("commit", "-qm", "removed")
        self.assertEqual(verify_review_trust(self.root / ".governance/review-FIX-301-R1.md",
                                             repo_root=self.root)["verdict"], "CLEAN")

    def test_reviewed_mode_or_link_must_match_the_delivered_object(self):
        ref = self.sign(0, "first.txt")
        self.git("update-index", "--chmod=+x", "first.txt")
        with self.assertRaisesRegex(ValueError, "mode differs"):
            self.derive(ref)
        self.git("config", "core.symlinks", "false")
        target = self.git("hash-object", "first.txt")
        self.git("update-index", "--cacheinfo", f"120000,{target},first.txt")
        with self.assertRaisesRegex(ValueError, "mode differs"):
            self.derive(ref)
        new = self.sign(1, "first.txt")
        self.assertEqual(self.derive(new)["review"]["conclusion"], "APPROVED")

    def test_source_report_link_cannot_stand_in_for_a_project_original(self):
        source = self.root / "reports"
        real = self.root / "originals"
        source.mkdir()
        (source / "report.md").write_text("original report")
        result = write_review_record(task_id="FIX-301", round_n=0, result="APPROVED", reviewer="Auditor",
                                     report_path=r"reports\report.md", bind_files=["first.txt"], root=self.root)
        ref = result["review_id"]
        self.assertEqual(self.derive(ref)["review"]["records"][0]["report"], "reports/report.md")
        source.rename(real)
        if os.name == "nt":
            subprocess.run(["cmd", "/d", "/c", "mklink", "/J", str(source), str(real)],
                           capture_output=True, check=True)
        else:
            source.symlink_to(real, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink|reparse"):
            self.derive(ref)

    def test_open_or_supervisor_outcomes_are_never_upgraded(self):
        first = self.sign(0, "first.txt")
        for n, result in enumerate(("BLOCKED", "ABORTED", "UNKNOWN"), 1):
            ref = self.sign(n, "first.txt", verdict=result)
            self.assertEqual(self.derive(ref)["review"]["conclusion"], result)
            with self.assertRaisesRegex(ValueError, "unaccounted"):
                self.derive(first)

    def test_disjoint_later_approval_does_not_hide_an_omitted_rejection(self):
        r0 = self.sign(0, "first.txt")
        r1 = self.sign(1, "first.txt", verdict="NEEDS_CHANGE")
        (self.root / "second.txt").write_bytes(b"another revision\n")
        self.git("add", "second.txt")
        r2 = self.sign(2, "second.txt")
        with self.assertRaisesRegex(ValueError, r1):
            self.derive(r0, r2)
        self.assertEqual(self.derive(r0, r1, r2)["review"]["conclusion"], "NEEDS_CHANGE")
        r3 = self.sign(3, "first.txt")
        self.assertEqual(self.derive(r2, r3)["review"]["conclusion"], "APPROVED")

    def test_absolute_report_inside_host_works_external_report_refuses(self):
        with tempfile.TemporaryDirectory() as other:
            for n, directory in enumerate((self.root, Path(other))):
                path = directory / "report-absolute.md"
                path.write_bytes(b"checked")
                result = write_review_record(task_id="FIX-301", round_n=n, result="APPROVED",
                                             reviewer="Reviewer", report_path=str(path),
                                             root=self.root, bind_files=["first.txt"])
                self.assertNotIn("error", result)
                if directory == self.root:
                    self.assertEqual(self.derive(result["review_id"])["review"]["conclusion"], "APPROVED")
                else:
                    with self.assertRaises(ValueError):
                        self.derive(result["review_id"])

    def test_record_pins_cannot_be_modified_or_replaced_by_unpinned_legacy(self):
        ref = self.sign(0, "first.txt")
        record = self.root / ".governance" / "review-FIX-301-R0.md"
        original = record.read_text(encoding="utf-8")
        record.write_text(original.replace("snapshot_bind: first.txt=", "snapshot_bind: forged="), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "bindings"):
            self.derive(ref)
        record.write_text("# historical note\nAPPROVED", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.derive(ref)
