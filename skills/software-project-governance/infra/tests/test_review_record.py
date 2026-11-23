"""Tests for infra/review_record.py — Wiring A thin CLI (FIX-236.1, ADR-017 §3).

Covers: machine review-record persistence (review-{id}-R{n}.md + evidence-log
row), Check 30 parseability of machine-written rows, the review→unit/gate
registry mapping (missing → WARN skip, explicit → wired), best-effort
degradation when process_gate_result fails, and the NEEDS_CHANGE "复审必达"
structured fields (next_round=R{n+1}).

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_review_record.py -v
"""

import hashlib
import io
import os
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import review_record  # noqa: E402
import verify_workflow as vw  # noqa: E402


def _prepare_review_repository(root):
    """Real FEAT-094 report bytes and Git revision, wholly inside the fixture.

    Verdict selection belongs to each test; this source report contains the
    reviewed object's findings without an unrelated preselected verdict.
    No trust-chain reader/writer or Git response is mocked.
    """
    root = Path(root)
    (root / ".governance").mkdir(exist_ok=True)
    empty_hooks = root / ".fixture-hooks"
    empty_hooks.mkdir()
    (root / ".gitignore").write_text(
        ".governance/\n.fixture-hooks/\nreport*.md\nreview-*.md\n", encoding="utf-8")
    (root / "subject.txt").write_text("Reviewed fixture revision.\n", encoding="utf-8")
    git = ["git", "-C", str(root), "-c", "core.hooksPath=" + str(empty_hooks),
           "-c", "user.name=Review Fixture", "-c", "user.email=fixture@example.invalid",
           "-c", "commit.gpgsign=false"]
    for args in (("init", "--quiet"), ("add", "subject.txt", ".gitignore"),
                 ("commit", "--quiet", "-m", "Create reviewed fixture revision")):
        subprocess.run([*git, *args], check=True, capture_output=True)
    for name in ("report.md", "report-r1.md", "review-FIX-236-CODE-R0.md"):
        (root / name).write_text(
            "# Review source\n\nReviewed subject.txt at the fixture Git revision.\n"
            "The verdict-specific persistence and wiring are exercised by the caller.\n",
            encoding="utf-8")
    return subprocess.check_output([*git, "rev-parse", "HEAD"], text=True).strip()




class PublishedObjectVerificationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.commit = _prepare_review_repository(self.root)
        self.tree = self.git("rev-parse", "HEAD^{tree}")
        self.report = self.root / "report.md"
        self.pinned = hashlib.sha256(self.report.read_bytes()).hexdigest()
        self.record = self.root / "review.md"

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True).strip()

    def write_tree_review(self, tree, files, *, round_n=0, **options):
        self.report.write_text(f"Reviewed tree {tree}.\n**APPROVED**\n", encoding="utf-8")
        return review_record.write_review_record(
            root=self.root, task_id="FIX-523", round_n=round_n, result="APPROVED",
            report_path=self.report.name, reviewer="Code Reviewer", bind_files=files,
            bind_tree=tree, **options,
        )

    def test_conflicting_tree_and_file_refused_before_native_review_writes(self):
        from loop_workflow import start

        start(self.root, unit_id="FIX-523", tier="inner", goal="Check review assembly",
              acceptance="The approved staged tree can be consumed")
        (self.root / "subject.txt").write_bytes(b"staged revision\n")
        self.git("add", "--", "subject.txt")
        candidate = self.git("write-tree")
        (self.root / "subject.txt").write_bytes(b"later work in the same file\n")
        previous = self.write_tree_review(candidate, [], unit_id="FIX-523",
                                          record_only=True, require_loop=True)
        self.assertNotIn("error", previous)

        def governance_bytes():
            gov = self.root / ".governance"
            return {p.relative_to(gov): p.read_bytes() for p in gov.rglob("*")
                    if p.is_file() and not p.name.endswith(".lock")}

        before = governance_bytes()
        result = self.write_tree_review(candidate, ["subject.txt"], round_n=1, unit_id="FIX-523",
                                        gate_id="G6", require_loop=True)
        self.assertEqual(result.get("code"), "tree_binding", result)
        self.assertIn("file pin disagrees with reviewed tree at subject.txt", result["error"])
        self.assertEqual(governance_bytes(), before)
        self.assertEqual(self.git("write-tree"), candidate)

    def test_tree_and_matching_file_can_include_independent_evidence(self):
        tracked = "交付 [v1].txt"
        (self.root / tracked).write_bytes(b"reviewed\n")
        self.git("add", "--", tracked)
        candidate = self.git("write-tree")
        private = ".governance/observation.md"
        (self.root / private).write_bytes(b"private observation\n")
        (self.root / "notes.md").write_bytes(b"untracked observation\n")
        result = self.write_tree_review(candidate, [tracked, private, "notes.md"])
        self.assertNotIn("error", result)
        pins = {p["path"]: p["hash"] for p in result["trust"]["bindings"]}
        for name in (tracked, private, "notes.md"):
            self.assertEqual(pins[name], self.git("hash-object", "--", name))
        consumed = review_record.derive_review_facts(self.root, "FIX-523", [result["review_id"]])
        self.assertEqual(consumed["files_changed"], [tracked])
        self.assertEqual(consumed["review"]["conclusion"], "APPROVED")

    def test_conflicting_pins_leave_eligible_unit_dormant_then_valid_pins_admit_it(self):
        from loop_workflow import runtime_path, start
        from commit_review import check

        dependency, task = "FIX-701", "FIX-523"
        for unit, dependencies in ((dependency, []), (task, [dependency])):
            start(self.root, unit_id=unit, tier="inner", goal="Review " + unit,
                  acceptance="Reviewed code matches the candidate", dependencies=dependencies)
        predecessor_report = self.root / "predecessor.md"
        predecessor_report.write_text("Verified prerequisite. **APPROVED**", encoding="utf-8")
        completed = review_record.write_review_record(
            root=self.root, task_id=dependency, unit_id=dependency, gate_id="G6", round_n=0,
            require_loop=True, result="APPROVED", report_path=predecessor_report.name,
            reviewer="Code Reviewer",
        )
        self.assertNotIn("error", completed)
        runtime = runtime_path(self.root)

        def states():
            units = json.loads(runtime.read_text(encoding="utf-8"))["flow_units"]
            return {u["flow_unit_id"]: u["runtime_status"] for u in units}

        def governance_bytes():
            return {p.relative_to(runtime.parent): p.read_bytes() for p in runtime.parent.rglob("*")
                    if p.is_file() and not p.name.endswith(".lock")}

        self.assertEqual(states(), {dependency: "completed", task: "dormant"})
        subject = self.root / "subject.txt"
        subject.write_bytes(b"candidate\n")
        self.git("add", "--", subject.name)
        tree = self.git("write-tree")
        subject.write_bytes(b"other working revision\n")
        before = governance_bytes()
        options = {"unit_id": task, "gate_id": "G6", "require_loop": True}
        refused = self.write_tree_review(tree, [subject.name], **options)
        self.assertEqual(refused.get("code"), "tree_binding", refused)
        self.assertEqual(governance_bytes(), before)

        subject.write_bytes(b"candidate\n")
        aliases = [subject.name, subject.name, "./subject.txt", str(subject)]
        admitted = self.write_tree_review(tree, aliases, **options)
        self.assertNotIn("error", admitted)
        self.assertEqual(states()[task], "completed")
        self.assertEqual([pin["path"] for pin in admitted["trust"]["bindings"]], [subject.name])
        self.assertTrue(check(self.root, task))

    def test_file_only_duplicate_aliases_share_one_git_snapshot_and_receipt(self):
        subject = self.root / "subject.txt"
        subject.write_bytes(b"candidate\n")
        self.git("add", "--", subject.name)
        aliases = [subject.name, "./subject.txt", str(subject)]
        with mock.patch.object(review_record, "_file_binding", wraps=review_record._file_binding) as pin:
            result = review_record.write_review_record(
                root=self.root, task_id="FIX-523", round_n=0, result="APPROVED",
                report_path=self.report.name, reviewer="Code Reviewer", bind_files=aliases,
            )
        self.assertNotIn("error", result)
        pin.assert_called_once_with(self.root.resolve(), subject.name)
        facts = review_record.derive_review_facts(self.root, "FIX-523", [result["review_id"]])
        self.assertEqual(facts["review"]["conclusion"], "APPROVED")

    def test_existing_case_alias_uses_git_path_for_comparison_and_consumption(self):
        name = "Gültig/Src/Ångström.txt"
        alias = "GÜLTIG/SRC/ÅNGSTRÖM.TXT"
        subject = self.root / name
        subject.parent.mkdir(parents=True)
        subject.write_bytes(b"reviewed\n")
        if not (self.root / alias).exists():
            self.skipTest("the temporary host uses case-sensitive lookup")
        self.git("add", "--", name)
        tree = self.git("write-tree")
        # The working directory's preserved case can differ from Git's index.
        renamed = subject.with_name("ÅNGSTRÖM.txt")
        subject.rename(renamed)
        subject.write_bytes(b"later work\n")
        result = self.write_tree_review(tree, [alias])
        self.assertEqual(result.get("code"), "tree_binding", result)
        self.assertIn(name, result["error"])
        subject.write_bytes(b"reviewed\n")
        mixed = self.write_tree_review(tree, [name, alias])
        self.assertNotIn("error", mixed)
        self.assertEqual([p["path"] for p in mixed["trust"]["bindings"]], [name])
        file_only = review_record.write_review_record(
            root=self.root, task_id="FIX-523", round_n=1, result="APPROVED", reviewer="Code Reviewer",
            report_path=self.report.name, bind_files=[alias],
        )
        self.assertNotIn("error", file_only)
        for result in (mixed, file_only):
            facts = review_record.derive_review_facts(self.root, "FIX-523", [result["review_id"]])
            self.assertEqual(facts["files_changed"], [name])

    def test_case_sensitive_entries_and_hardlinks_keep_distinct_git_names(self):
        directory = self.root / "sensitive"
        directory.mkdir()
        first = directory / "Alpha.txt"
        second = directory / "ALPHA.TXT"
        first.write_bytes(b"first\n")
        if second.exists() and os.name == "nt":
            first.unlink()  # NTFS enables case-sensitive lookup on an empty directory.
            subprocess.run(["fsutil", "file", "setCaseSensitiveInfo", str(directory), "enable"],
                           capture_output=True, timeout=10)
            first.write_bytes(b"first\n")
        if second.exists():
            self.skipTest("the temporary host cannot create case-distinct entries")
        second.write_bytes(b"second\n")
        linked = directory / "alpha.TXT"
        os.link(first, linked)
        private = directory / "aLPHA.txt"
        os.link(first, private)
        self.git("config", "core.ignorecase", "false")
        names = [p.relative_to(self.root).as_posix() for p in (first, second, linked, private)]
        self.git("add", "--", *names[:3])
        tree = self.git("write-tree")
        reviewed = self.write_tree_review(tree, names)
        self.assertNotIn("error", reviewed)
        pins = {p["path"]: p["hash"] for p in reviewed["trust"]["bindings"]}
        self.assertEqual(list(pins), names)
        self.assertEqual(pins[names[0]], pins[names[2]])
        self.assertNotEqual(pins[names[0]], pins[names[1]])
        self.assertEqual(pins[names[0]], pins[names[3]])
        facts = review_record.derive_review_facts(self.root, "FIX-523", [reviewed["review_id"]])
        self.assertEqual(set(facts["files_changed"]), set(names[:3]))
        self.git("-c", "user.name=Review Fixture", "-c", "user.email=fixture@example.invalid",
                 "-c", "core.hooksPath=" + str(self.root / ".fixture-hooks"), "commit", "-qm", "case-distinct files")
        self.git("rm", "--cached", "--", names[0])
        deleted = self.git("write-tree")
        independent = self.write_tree_review(deleted, [names[3]], round_n=1)
        self.assertNotIn("error", independent)
        self.assertEqual(independent["trust"]["bindings"][0]["path"], names[3])
        facts = review_record.derive_review_facts(self.root, "FIX-523", [independent["review_id"]])
        self.assertEqual(facts["files_changed"], [names[0]])

    def test_tree_file_mode_conflict_and_deletion_semantics(self):
        self.git("config", "core.filemode", "false")
        self.git("update-index", "--chmod=+x", "--", "subject.txt")
        executable = self.git("write-tree")
        self.git("update-index", "--chmod=-x", "--", "subject.txt")
        mode_conflict = self.write_tree_review(executable, ["subject.txt"])
        self.assertEqual(mode_conflict.get("code"), "tree_binding", mode_conflict)

        self.git("rm", "--cached", "--", "subject.txt")
        deleted = self.git("write-tree")
        retained_bytes = self.write_tree_review(deleted, ["subject.txt"])
        self.assertEqual(retained_bytes.get("code"), "tree_binding", retained_bytes)
        (self.root / "subject.txt").unlink()
        misspelled = self.write_tree_review(deleted, ["SUBJECT.TXT"])
        self.assertEqual(misspelled.get("code"), "tree_binding", misspelled)
        self.assertIn("exact Git path", misspelled["error"])
        matched = self.write_tree_review(deleted, ["subject.txt"])
        self.assertNotIn("error", matched)
        self.assertEqual(matched["trust"]["bindings"], [
            {"path": "subject.txt", "mode": "000000", "hash": "0" * len(deleted)},
        ])

    def test_retained_case_variant_of_deletion_and_candidate_case_rename(self):
        tracked = self.root / "subject.txt"
        renamed = self.root / "SUBJECT.TXT"
        if not renamed.exists():
            self.skipTest("the temporary host uses case-sensitive lookup")
        self.git("config", "core.ignorecase", "false")
        self.git("rm", "--cached", "--", tracked.name)
        deleted = self.git("write-tree")
        tracked.rename(renamed)
        for spelling in (tracked.name, renamed.name):
            result = self.write_tree_review(deleted, [spelling])
            self.assertEqual(result.get("code"), "tree_binding", result)
            self.assertIn("file pin disagrees with reviewed tree at subject.txt", result["error"])
        self.git("add", "--", renamed.name)
        # An index-only match must not displace the frozen tree's deletion.
        self.assertIn("file pin disagrees", self.write_tree_review(deleted, [renamed.name])["error"])
        # The new candidate actually contains the rename and takes precedence over HEAD.
        new_tree = self.git("write-tree")
        accepted = self.write_tree_review(new_tree, [tracked.name, renamed.name])
        self.assertNotIn("error", accepted)
        self.assertEqual([p["path"] for p in accepted["trust"]["bindings"]], [renamed.name])
        facts = review_record.derive_review_facts(self.root, "FIX-523", [accepted["review_id"]])
        self.assertEqual(facts["review"]["conclusion"], "APPROVED")

    def test_ownership_read_errors_are_distinct_from_an_empty_lookup(self):
        from loop_workflow import start

        task = "FIX-523"
        start(self.root, unit_id=task, tier="inner", goal="Verify receipt",
              acceptance="Failed lookups do not change the receipt or gate")
        subject = self.root / "subject.txt"
        subject.write_bytes(b"candidate\n")
        self.git("add", "--", subject.name)
        tree = self.git("write-tree")
        gov = self.root / ".governance"
        index = self.root / ".git" / "index"
        original_index = index.read_bytes()

        def governance_bytes():
            return {p.relative_to(gov): p.read_bytes() for p in gov.rglob("*")
                    if p.is_file() and not p.name.endswith(".lock")}

        before = governance_bytes()
        options = {"unit_id": task, "gate_id": "G6", "require_loop": True}
        damaged_index = b"invalid disposable test index"
        index.write_bytes(damaged_index)
        result = self.write_tree_review(tree, [subject.name], **options)
        self.assertEqual(result.get("code"), "tree_binding", result)
        self.assertIn("Git could not read binding names", result["error"])
        self.assertEqual(index.read_bytes(), damaged_index)
        self.assertEqual(governance_bytes(), before)

        index.write_bytes(original_index)
        real_listdir = os.listdir

        def deny_enumeration(path):
            if Path(path) == self.root:
                raise PermissionError("directory listing denied")
            return real_listdir(path)

        with mock.patch.object(os, "listdir", side_effect=deny_enumeration):
            result = self.write_tree_review(tree, [subject.name], **options)
        self.assertEqual(result.get("code"), "tree_binding", result)
        self.assertIn("directory listing denied", result["error"])
        self.assertEqual(governance_bytes(), before)
        self.assertEqual(index.read_bytes(), original_index)
        untracked = self.root / "untracked-note.md"
        untracked.write_bytes(b"independent evidence")
        accepted = self.write_tree_review(tree, [subject.name, untracked.name], **options)
        self.assertNotIn("error", accepted)
        self.assertTrue(accepted["wiring"]["wired"])

    def test_snapshot_outside_git_keeps_unavailable_revision_and_local_file_pin(self):
        with tempfile.TemporaryDirectory() as folder:
            host = Path(folder)
            (host / "note.txt").write_bytes(b"local evidence")
            snapshot = review_record.snapshot_binding(host, ["note.txt", "./note.txt"])
            self.assertEqual(snapshot["commit"], "git:unavailable")
            self.assertEqual(snapshot["worktree"], "unavailable")
            self.assertEqual([v["path"] for v in snapshot["bindings"]], ["note.txt"])
            self.assertEqual(snapshot["bindings"][0]["hash"], self.git("hash-object", str(host / "note.txt")))

    def record_pins(self, commit, tree, report_hash):
        lines = ["# Test review", "- report: report.md"]
        for key, value in (("report_sha256", report_hash), ("snapshot_commit", commit),
                           ("snapshot_tree", tree)):
            if value is not None:
                lines.append(f"- {key}: {value}")
        self.record.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return [{"commit": commit, "tree": tree}]

    def assert_face(self, objects, verdict):
        individual = review_record.verify_review_trust(self.record, self.root, current_worktree=False)
        self.assertEqual(individual["verdict"], verdict)
        self.assertEqual(objects.verify(self.record, self.root), individual)

    def test_seven_original_controls_keep_the_full_trust_result(self):
        for name, commit, tree, report_hash, expected in [
            ("valid", self.commit, self.tree, self.pinned, "CLEAN"),
            ("missing commit", "f"*40, self.tree, self.pinned, "CONFLICT"),
            ("Git unavailable", self.commit, self.tree, self.pinned, "UNKNOWN"),
            ("report changed", self.commit, self.tree, "0"*64, "CONFLICT"),
            ("commit used as tree", self.commit, self.commit, self.pinned, "CONFLICT"),
            ("missing tree", self.commit, "f"*40, self.pinned, "UNKNOWN"),
            ("legacy unpinned", None, None, None, "UNPINNED"),
        ]:
            with self.subTest(name=name):
                original_path = os.environ["PATH"]
                try:
                    if name == "Git unavailable":
                        os.environ["PATH"] = str(self.root)
                    pins = self.record_pins(commit, tree, report_hash)
                    self.assert_face(review_record.PublishedReviewObjects(self.root, pins), expected)
                finally:
                    os.environ["PATH"] = original_path

    def test_native_loop_state_queries_objects_once_and_reopens_changed_evidence(self):
        import governance_readers
        import loop_workflow

        reports = []
        for task in ("FIX-701", "FIX-702"):
            loop_workflow.start(self.root, unit_id=task, tier="inner", goal="Review " + task,
                                acceptance="The stored report matches the reviewed revision.")
            path = self.root / (task + ".md")
            path.write_text(f"Inspected tree {self.tree}.\n**审查结论**: **APPROVED**\n", encoding="utf-8")
            reports.append(path)
            result = review_record.write_review_record(
                task_id=task, round_n=0, result="APPROVED", report_path=path.name,
                bind_tree=self.tree, reviewer="independent QA", root=self.root, require_loop=True)
            self.assertNotIn("error", result)
        with mock.patch.object(review_record, "_git_output", wraps=review_record._git_output) as git:
            valid = governance_readers.loop_state(self.root)
        self.assertEqual(valid["state"], "ready", valid.get("issues"))
        self.assertEqual([call.args[1] for call in git.call_args_list], ["cat-file"])
        self.assertEqual(set(git.call_args.kwargs["input_bytes"].decode().splitlines()),
                         {self.tree, self.commit + "^{commit}"})
        reports[0].write_bytes(b"changed after publication")
        second = governance_readers.loop_state(self.root)
        self.assertEqual(second["state"], "invalid")
        self.assertEqual([row["gate_status"] for row in second["units"]], ["unverified", "passed"])

    def test_missing_commit_probes_current_head_and_valid_reports_are_reread(self):
        pins = self.record_pins("f"*40, self.tree, self.pinned)
        objects = review_record.PublishedReviewObjects(self.root, pins)
        self.assert_face(objects, "CONFLICT")
        self.git("symbolic-ref", "HEAD", "refs/heads/new-unborn-branch")
        self.assert_face(objects, "UNKNOWN")
        pins = self.record_pins(self.commit, self.tree, self.pinned)
        objects = review_record.PublishedReviewObjects(self.root, pins)
        self.assert_face(objects, "CLEAN")
        self.report.write_bytes(b"rewritten after the first read")
        self.assert_face(objects, "CONFLICT")

    def test_tag_peeling_and_incomplete_batch_use_individual_git_checks(self):
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "-c", "tag.gpgSign=false", "tag", "-a", "review-tag", "-m", "annotated pin")
        tag = self.git("rev-parse", "refs/tags/review-tag")
        pins = self.record_pins(tag, self.tree, self.pinned)
        self.assert_face(review_record.PublishedReviewObjects(self.root, pins), "CONFLICT")
        pins = self.record_pins(self.commit, self.tree, self.pinned)
        with mock.patch.object(review_record, "_git_output", return_value="truncated"):
            objects = review_record.PublishedReviewObjects(self.root, pins)
        self.assert_face(objects, "CLEAN")

    def test_bulk_read_is_scoped_to_its_repo_and_untracked_bindings_remain_live(self):
        pins = self.record_pins(self.commit, self.tree, self.pinned)
        with mock.patch.object(review_record, "_git_output", wraps=review_record._git_output) as git:
            objects = review_record.PublishedReviewObjects(self.root, pins * 3)
            self.assertEqual(objects.verify(self.record, self.root)["verdict"], "CLEAN")
            self.assertEqual(git.call_count, 1)
            self.assertEqual(set(git.call_args.kwargs["input_bytes"].decode().splitlines()),
                             {self.commit + "^{commit}", self.tree})
        with tempfile.TemporaryDirectory() as other:
            root = Path(other)
            (root / "report.md").write_bytes(self.report.read_bytes())
            subprocess.run(["git", "-C", str(root), "init", "--quiet"], check=True)
            individual = review_record.verify_review_trust(self.record, root, current_worktree=False)
            self.assertEqual(individual["verdict"], "UNKNOWN")
            self.assertEqual(objects.verify(self.record, root), individual)
        subject = self.root / "untracked-subject"
        subject.write_bytes(b"observed")
        blob = self.git("hash-object", "--", subject.name)
        with self.record.open("a", encoding="utf-8") as out:
            out.write(f"- snapshot_bind: {subject.name}={blob}\n")
        self.assertEqual(review_record.verify_review_trust(self.record, self.root)["verdict"], "CLEAN")
        subject.write_bytes(b"new revision")
        self.assertEqual(review_record.verify_review_trust(self.record, self.root)["verdict"], "CONFLICT")
        self.assert_face(objects, "CLEAN")


class ReviewRecordPersistenceTests(unittest.TestCase):
    """Machine-written review records: file + evidence row + Check 30 parseability."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="rr_")
        self.root = Path(self.tmpdir)
        (self.root / ".governance").mkdir()
        self.reviewed_commit = _prepare_review_repository(self.root)

    def _write(self, **overrides):
        kwargs = {
            "task_id": "FIX-236",
            "round_n": 0,
            "result": "APPROVED",
            "report_path": str(self.root / "report.md"),
            "reviewer": "Code Reviewer Noether",
            "root": self.root,
        }
        kwargs.update(overrides)
        return review_record.write_review_record(**kwargs)

    def test_approved_writes_file_and_evidence_row(self):
        summary = self._write()
        self.assertFalse(summary.get("error"))
        review_file = self.root / ".governance" / "review-FIX-236-R0.md"
        self.assertTrue(review_file.is_file())
        content = review_file.read_text(encoding="utf-8")
        self.assertIn("**审查结论**: **APPROVED**", content)
        ev = (self.root / ".governance" / "evidence-log.md").read_text(encoding="utf-8")
        self.assertIn("REVIEW-FIX-236-R0", ev)
        self.assertIn("| FIX-236 |", ev)
        self.assertIn("APPROVED", ev)
        self.assertEqual(summary["trust"]["commit"], self.reviewed_commit)
        with mock.patch.object(review_record, "_git_output", wraps=review_record._git_output) as git:
            self.assertEqual(review_record.verify_review_trust(
                review_file, repo_root=self.root)["verdict"], "CLEAN")
        pinned = mock.call(self.root, "rev-parse", "--verify", "--quiet", self.reviewed_commit + "^{commit}")
        self.assertIn(pinned, git.call_args_list)
        self.assertNotIn(mock.call(self.root, "rev-parse", "--verify", "--quiet", "HEAD"), git.call_args_list)

    def test_approved_with_notes_writes_blocker_token(self):
        # Legacy source reports with no field can still be recorded.
        summary = self._write(result="APPROVED_WITH_NOTES")
        self.assertFalse(summary.get("error"))
        ev = (self.root / ".governance" / "evidence-log.md").read_text(encoding="utf-8")
        self.assertIn("unresolved_blockers=0", ev)
        self.assertEqual(summary["review_id"], "REVIEW-FIX-236-R0")

    def test_notes_accept_zero_and_ignore_markdown_examples(self):
        report = self.root / "report.md"
        report.write_text(
            "**APPROVED_WITH_NOTES**\n\nThe guide illustrates `unresolved_blockers=8`.\n"
            "> unresolved_blockers=7\n    unresolved_blockers=6\n"
            "````markdown\n```\nunresolved_blockers=5\n```\n````\n"
            "- ~~~text\n  unresolved_blockers=4\n  ~~~\n"
            "1. ```yaml\n   unresolved_blockers=2\n   ```\n"
            "<!-- Previous round\nunresolved_blockers=3\n-->\n"
            "\n- **unresolved_blockers=0**\n1. unresolved_blocks=0\n"
            "- **unresolved_blockers**: 0\n- unresolved_blockers：0\n", encoding="utf-8")
        summary = self._write(result="APPROVED_WITH_NOTES")
        self.assertFalse(summary.get("error"), summary)

    def test_notes_refuse_invalid_declared_fields_before_any_record_is_written(self):
        report = self.root / "report.md"
        gov = self.root / ".governance"
        for field in ("unresolved_blockers=1", "- **unresolved_blockers = 12**",
                      "`unresolved_blockers=001`", "unresolved_blockers=0\nunresolved_blockers=2",
                      "unresolved_blockers=0\nunresolved_blockers=pending", "unresolved_blockers=-1",
                      "1. UNRESOLVED_BLOCKERS=2", "| unresolved_blockers=2 |", "unresolved_blockers=",
                      "- **unresolved_blockers**: 2", "unresolved_blockers：pending",
                      "unresolved_blockers=2 (pending sign-off)", "unresolved_blockers=not yet measured",
                      "12. ```yaml\n    unresolved_blockers=0\n    ```\n\nunresolved_blockers=2",
                      "The markup guide uses `<!--` for comments.\nunresolved_blockers=3",
                      "unresolved_blocks=2", "unresolved_blockers=" + "1" * 4500):
            with self.subTest(field=field):
                report.write_text("**APPROVED_WITH_NOTES**\n" + field + "\n", encoding="utf-8")
                summary = self._write(result="APPROVED_WITH_NOTES")
                self.assertEqual(summary["code"], "conflict_report_vs_record")
                self.assertTrue(summary["conflict"]["report_fields"])
                self.assertEqual(list(gov.iterdir()), [])

    def test_refused_notes_do_not_initialize_governance(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = root / "report.md"
            report.write_text("unresolved_blockers=1\n", encoding="utf-8")
            result = self._write(result="APPROVED_WITH_NOTES", report_path=str(report), root=root)
            self.assertEqual(result["code"], "conflict_report_vs_record")
            self.assertEqual(list(root.iterdir()), [report])

    def test_needs_change_emits_revisit_required_fields(self):
        summary = self._write(result="NEEDS_CHANGE")
        self.assertTrue(summary["revisit_required"])
        self.assertEqual(summary["next_round"], "REVIEW-FIX-236-R1")
        self.assertEqual(summary["prev_report"], str(self.root / "report.md"))
        content = (self.root / ".governance" / "review-FIX-236-R0.md").read_text(
            encoding="utf-8")
        self.assertIn("复审必达", content)
        self.assertIn("next_round", content)

    def test_check30_live_scan_passes_on_machine_row(self):
        self._write()
        gov = self.root / ".governance"
        with mock.patch.object(vw, "SAMPLE_PATH", gov / "plan-tracker.md"), \
             mock.patch.object(vw, "EVIDENCE_PATH", gov / "evidence-log.md"), \
             mock.patch.object(vw, "GOVERNANCE_DIR", gov):
            result = vw.check_review_closure()
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["violations"], [])

    def test_invalid_result_fails_closed(self):
        summary = self._write(result="MAYBE")
        self.assertIn("error", summary)
        self.assertFalse((self.root / ".governance" / "review-FIX-236-R0.md").exists())

    def test_round_continuity_r0_then_r1_passes_check30(self):
        self._write(result="NEEDS_CHANGE")
        self._write(task_id="FIX-236", round_n=1, result="APPROVED")
        gov = self.root / ".governance"
        (gov / "plan-tracker.md").write_text(
            "# 项目配置\n\n### 优先级一览\n"
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| P1 | FIX-236 | review-record fixture | — | 0.73.0 | ✅ 完成 |\n",
            encoding="utf-8",
        )
        with mock.patch.object(vw, "SAMPLE_PATH", gov / "plan-tracker.md"), \
             mock.patch.object(vw, "EVIDENCE_PATH", gov / "evidence-log.md"), \
             mock.patch.object(vw, "GOVERNANCE_DIR", gov):
            result = vw.check_review_closure()
        self.assertEqual(result["verdict"], "PASS", result["reason"])


class ReviewRecordScopeTests(unittest.TestCase):
    """FEAT-091: delta-revisit injection-scope recording.

    ``--scope full|delta`` (+ ``--delta-base`` anchor) records WHICH
    injection face the review ran against — the delta revisit contract
    (M7.4 T1 R2 注入面) made machine-persistable. Default ``full`` keeps
    every pre-FEAT-091 caller byte-compatible; illegal combos fail closed
    before anything is written.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="rrs_")
        self.root = Path(self.tmpdir)
        (self.root / ".governance").mkdir()
        _prepare_review_repository(self.root)

    def _write(self, **overrides):
        kwargs = {
            "task_id": "FIX-236",
            "round_n": 1,
            "result": "NEEDS_CHANGE",
            "report_path": str(self.root / "report-r1.md"),
            "reviewer": "Code Reviewer Noether",
            "root": self.root,
        }
        kwargs.update(overrides)
        return review_record.write_review_record(**kwargs)

    def test_default_scope_is_full_and_carries_field_line(self):
        summary = self._write()
        self.assertFalse(summary.get("error"))
        self.assertEqual(summary["scope"], "full")
        content = (self.root / ".governance" / "review-FIX-236-R1.md"
                   ).read_text(encoding="utf-8")
        self.assertIn("- scope: full", content)
        self.assertNotIn("delta_base", content)

    def test_delta_scope_records_delta_base_field(self):
        prev = str(self.root / "review-FIX-236-R0.md")
        summary = self._write(scope="delta", delta_base=prev)
        self.assertFalse(summary.get("error"))
        self.assertEqual(summary["scope"], "delta")
        self.assertEqual(summary["delta_base"], prev)
        content = (self.root / ".governance" / "review-FIX-236-R1.md"
                   ).read_text(encoding="utf-8")
        self.assertIn("- scope: delta", content)
        self.assertIn("- delta_base: {0}".format(prev), content)
        # the revisit fields coexist with the scope face
        self.assertIn("next_round", content)

    def test_illegal_scope_fails_closed_without_write(self):
        summary = self._write(scope="partial")
        self.assertIn("error", summary)
        self.assertIn("scope", summary["error"])
        self.assertFalse(
            (self.root / ".governance" / "review-FIX-236-R1.md").exists())

    def test_delta_base_with_full_scope_fails_closed(self):
        summary = self._write(scope="full", delta_base="some-anchor")
        self.assertIn("error", summary)
        self.assertIn("delta", summary["error"])
        self.assertFalse(
            (self.root / ".governance" / "review-FIX-236-R1.md").exists())

    def test_cli_wires_scope_and_delta_base_into_writer(self):
        """The verify_workflow thin entry forwards the new flags (FEAT-091);
        --scope choices are argparse-enforced (exit 2 on illegal value)."""
        buf = io.StringIO()
        args = SimpleNamespace(
            task="FIX-236", round=1, result="APPROVED",
            report=str(self.root / "report.md"), reviewer="CLI Reviewer",
            unit=None, gate=None, scope="delta",
            delta_base=str(self.root / "prev.md"))
        with mock.patch("review_record.write_review_record",
                        return_value={"ok": True}) as writer, \
             redirect_stdout(buf):
            vw.cmd_review_record(args)
        writer.assert_called_once()
        _, call_kwargs = writer.call_args
        self.assertEqual(call_kwargs["scope"], "delta")
        self.assertEqual(call_kwargs["delta_base"], str(self.root / "prev.md"))


class ReviewRecordWiringTests(unittest.TestCase):
    """Wiring A: mapping resolution, explicit unit/gate wiring, best-effort degrade."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="rrw_")
        self.root = Path(self.tmpdir)
        (self.root / ".governance").mkdir()
        _prepare_review_repository(self.root)

    def test_independent_observations_never_derive_a_gate_from_report_names(self):
        for rnd, name in enumerate(("report.md", "review-FIX-236-CODE-R0.md")):
            summary = review_record.write_review_record(
                task_id="FIX-236", round_n=rnd, result="APPROVED", report_path=self.root / name, root=self.root)
            self.assertFalse(summary["wiring"]["wired"])
            self.assertEqual(summary["wiring"]["decision"], "recorded")
            self.assertTrue((self.root / ".governance" / f"review-FIX-236-R{rnd}.md").is_file())
        self.assertFalse((self.root / ".governance" / "flow-unit-runtime.json").exists())

    def test_explicit_unit_gate_wires_approved_to_exit(self):
        unit_id = "shitu.story.Skeleton"
        from loop_workflow import start, runtime_path as state_file
        start(self.root, unit_id=unit_id, task="FIX-236", goal="Deliver repair", tier="inner",
              acceptance="The observed behavior satisfies the acceptance test")
        runtime_path = state_file(self.root)
        (self.root / "report.md").write_text("**审查结论**: **APPROVED**", encoding="utf-8")
        summary = review_record.write_review_record(
            task_id="FIX-236", round_n=0, result="APPROVED",
            report_path=str(self.root / "report.md"), root=self.root,
            unit_id=unit_id, gate_id="G6", reviewer="Code Reviewer", require_loop=True,
        )
        wiring = summary["wiring"]
        self.assertTrue(wiring["wired"])
        self.assertEqual(wiring["decision"], "exit")
        self.assertEqual(wiring["status"], "success")
        payload = json.loads(runtime_path.read_text(encoding="utf-8"))
        unit = [u for u in payload["flow_units"] if u["flow_unit_id"] == unit_id][0]
        self.assertEqual(unit["gate_state"]["status"], "passed")

    def test_explicit_unit_gate_needs_change_drives_iterate(self):
        unit_id = "shitu.story.Skeleton"
        from loop_workflow import start, runtime_path as state_file
        start(self.root, unit_id=unit_id, task="FIX-236", goal="Deliver repair", tier="inner",
              acceptance="The observed behavior satisfies the acceptance test")
        runtime_path = state_file(self.root)
        (self.root / "report.md").write_text("**审查结论**: **NEEDS_CHANGE**", encoding="utf-8")
        summary = review_record.write_review_record(
            task_id="FIX-236", round_n=0, result="NEEDS_CHANGE",
            report_path=str(self.root / "report.md"), root=self.root,
            unit_id=unit_id, gate_id="G6", reviewer="Code Reviewer", require_loop=True,
        )
        wiring = summary["wiring"]
        self.assertTrue(wiring["wired"])
        self.assertEqual(wiring["decision"], "iterate")
        self.assertEqual(wiring["status"], "success")

    def test_missing_foreign_and_misdirected_scopes_cannot_record_a_verdict(self):
        runtime = self.root / ".governance" / "flow-unit-runtime.json"
        for label in ("missing", "historical", "elsewhere"):
            with self.subTest(label=label):
                if label == "historical":
                    runtime.write_bytes(b'{"schema_version":"1.0"}')
                summary = review_record.write_review_record(
                    task_id="FIX-236", round_n=0, result="APPROVED", reviewer="Code Reviewer",
                    report_path=self.root / "report.md", root=self.root,
                    unit_id="missing", gate_id="G6",
                    runtime_file=self.root / "other.json" if label == "elsewhere" else runtime)
                self.assertEqual(summary["code"], "loop_binding", summary)
                self.assertFalse((self.root / ".governance" / "review-FIX-236-R0.md").exists())
                if label != "missing":
                    self.assertEqual(runtime.read_bytes(), b'{"schema_version":"1.0"}')


class ReviewRecordCliTests(unittest.TestCase):
    """CLI integration: verify_workflow review-record (thin entry)."""

    def test_cli_writes_record_in_fixture_project_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".governance").mkdir()
            report = root / "report.md"
            report.write_text("# report\n**审查结论**: **APPROVED**\n", encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(_INFRA_DIR / "verify_workflow.py"),
                 "review-record", "--project-root", str(root),
                 "--task", "FIX-236", "--round", "0", "--result", "APPROVED",
                 "--report", str(report), "--reviewer", "Code Reviewer Noether"],
                capture_output=True, text=True, encoding="utf-8", timeout=60,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertFalse(payload["wiring"]["wired"])
            self.assertFalse((root / ".governance" / "flow-unit-runtime.json").exists())
            self.assertEqual(payload["review_id"], "REVIEW-FIX-236-R0")
            self.assertTrue((root / ".governance" / "review-FIX-236-R0.md").is_file())
            self.assertIn(
                "REVIEW-FIX-236-R0",
                (root / ".governance" / "evidence-log.md").read_text(encoding="utf-8"),
            )


class ReviewRecordOverwriteGuardTests(unittest.TestCase):
    """FIX-289⑤ — 同 task+round 记录存在性守卫（P7 数据破坏防护）.

    Bug contract (FIX-281⑤ defect, REL-073 same-number overwrite near-miss):
    ``write_review_record`` used to overwrite an existing
    ``review-{task}-R{n}.md`` silently. Guard contract:

    - default → reject with an error dict (fail-closed: no file overwrite,
      no evidence row appended, existing record byte-identical);
    - ``force=True`` → deliberate overwrite WITH an audit trail: the previous
      record is backed up beside the record
      (``review-{task}-R{n}.pre-<ts>.md``), the new record carries a
      ``force_overwrite`` marker naming the backup, and the summary reports
      both.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="rro_")
        self.root = Path(self.tmpdir)
        (self.root / ".governance").mkdir()
        _prepare_review_repository(self.root)
        self.gov = self.root / ".governance"
        self.review_file = self.gov / "review-FIX-236-R0.md"
        self.evidence_log = self.gov / "evidence-log.md"

    def _write(self, **overrides):
        kwargs = {
            "task_id": "FIX-236",
            "round_n": 0,
            "result": "APPROVED",
            "report_path": str(self.root / "report.md"),
            "reviewer": "Code Reviewer Noether",
            "root": self.root,
        }
        kwargs.update(overrides)
        return review_record.write_review_record(**kwargs)

    def _review_row_count(self):
        return self.evidence_log.read_text(encoding="utf-8").count(
            "| REVIEW-FIX-236-R0 |")

    def test_duplicate_task_round_rejected_by_default_without_overwrite(self):
        first = self._write()
        self.assertFalse(first.get("error"))
        original = self.review_file.read_text(encoding="utf-8")
        self.assertIn("**审查结论**: **APPROVED**", original)
        # Same task+round again — must NOT silently replace the record.
        second = self._write(result="NEEDS_CHANGE")
        self.assertIn("error", second)
        self.assertEqual(
            self.review_file.read_text(encoding="utf-8"), original,
            "existing task+round record was overwritten")
        self.assertIn("APPROVED", original)
        # The rejected write must not leak a duplicate evidence row.
        self.assertEqual(self._review_row_count(), 1)

    def test_rejection_error_names_record_and_force_escape_hatch(self):
        self._write()
        second = self._write()
        self.assertIn("error", second)
        self.assertIn(str(self.review_file), second["error"])
        self.assertIn("force", second["error"])

    def test_force_overwrites_with_backup_and_marker(self):
        self._write()
        original = self.review_file.read_text(encoding="utf-8")
        summary = self._write(result="NEEDS_CHANGE", force=True)
        self.assertFalse(summary.get("error"))
        self.assertTrue(summary["force_overwrite"])
        backup = Path(summary["previous_record_backup"])
        self.assertTrue(backup.is_file())
        # 留痕 1: the previous record is preserved byte-for-byte.
        self.assertEqual(backup.read_text(encoding="utf-8"), original)
        new_text = self.review_file.read_text(encoding="utf-8")
        self.assertIn("**审查结论**: **NEEDS_CHANGE**", new_text)
        # 留痕 2: the new record marks the overwrite and names the backup.
        self.assertIn("force_overwrite", new_text)
        self.assertIn(backup.name, new_text)

    def test_force_chain_preserves_every_previous_record(self):
        self._write()
        v1 = self.review_file.read_text(encoding="utf-8")
        first = self._write(result="NEEDS_CHANGE", force=True)
        self.assertFalse(first.get("error"))
        v2 = self.review_file.read_text(encoding="utf-8")
        second = self._write(result="APPROVED", force=True)
        self.assertFalse(second.get("error"))
        backups = sorted(self.gov.glob("review-FIX-236-R0.pre-*.md"))
        self.assertEqual(len(backups), 2)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), v1)
        self.assertEqual(backups[1].read_text(encoding="utf-8"), v2)
        self.assertIn("**审查结论**: **APPROVED**",
                      self.review_file.read_text(encoding="utf-8"))

    def test_force_on_fresh_record_is_plain_write(self):
        summary = self._write(force=True)
        self.assertFalse(summary.get("error"))
        self.assertNotIn("force_overwrite", summary)
        self.assertNotIn("force_overwrite",
                         self.review_file.read_text(encoding="utf-8"))
        self.assertEqual(
            len(list(self.gov.glob("review-FIX-236-R0.pre-*.md"))), 0)

    def test_cli_duplicate_round_fails_closed_exit_2(self):
        # The review-record thin entry never passes force — a duplicate
        # task+round must exit 2 (fail-closed) without touching the record.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / ".governance").mkdir()
            report = root / "report.md"
            report.write_text("# report\n", encoding="utf-8")
            base_cmd = [sys.executable, str(_INFRA_DIR / "verify_workflow.py"),
                        "review-record", "--project-root", str(root),
                        "--task", "FIX-236", "--round", "0",
                        "--report", str(report)]
            first = subprocess.run(base_cmd + ["--result", "APPROVED"],
                                   capture_output=True, text=True,
                                   encoding="utf-8", timeout=60)
            self.assertEqual(first.returncode, 0, first.stderr)
            before = (root / ".governance" / "review-FIX-236-R0.md").read_text(
                encoding="utf-8")
            second = subprocess.run(base_cmd + ["--result", "NEEDS_CHANGE"],
                                    capture_output=True, text=True,
                                    encoding="utf-8", timeout=60)
            self.assertEqual(second.returncode, 2)
            self.assertIn("error", second.stdout)
            self.assertEqual(
                (root / ".governance" / "review-FIX-236-R0.md").read_text(
                    encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
