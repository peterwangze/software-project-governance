"""FIX-261 — pre-commit/commit-msg review-evidence regex alignment tests.

The hook's ``has_approved_review_evidence()`` must accept BOTH pass forms:

  (a) legacy end-column — ``| APPROVED_WITH_NOTES |`` as the final column;
  (b) review-record machine row — 11-column row ending
      ``| APPROVED_WITH_NOTES | unresolved_blockers=0 |``
      (infra/review_record.py ``_evidence_row``; FIX-193 four-state protocol).

The function lives as an identical copy in BOTH hooks (pre-commit Step 7 and
commit-msg); these tests extract each copy from the hook SOURCE and execute
it in bash, so the assertion pins the actual shipped regex, not a re-typed
one, and pins the two copies staying in sync.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_pre_commit_review_evidence.py -v
"""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

_INFRA_DIR = Path(__file__).resolve().parent.parent
_HOOKS_DIR = _INFRA_DIR / "hooks"
_REPO_ROOT = _INFRA_DIR.parent.parent.parent  # <repo>/skills/<skill>/infra → <repo>

_PRE_COMMIT = _HOOKS_DIR / "pre-commit"
_COMMIT_MSG = _HOOKS_DIR / "commit-msg"
_EVIDENCE = _REPO_ROOT / ".governance" / "evidence-log.md"

_FN_RE = re.compile(
    r"^has_approved_review_evidence\(\) \{.*?^\}", re.MULTILINE | re.DOTALL)


def _extract_function(hook_path):
    text = hook_path.read_text(encoding="utf-8")
    m = _FN_RE.search(text)
    if not m:
        raise AssertionError(
            "has_approved_review_evidence() not found in {0}".format(hook_path))
    return m.group(0)


# Machine 11-column row shape mirrors review_record._evidence_row exactly.
# ``tail_cols`` carries the columns AFTER the conclusion column, pipes
# included ("" would leave the row unclosed): " |" = plain 10-column row;
# " | unresolved_blockers=0 |" = the APPROVED_WITH_NOTES 11-column form.
MACHINE_ROW = (
    "| REVIEW-{task}-R0 | {task} | 治理记录 | review-record CLI 机器写入 review 结论记录"
    "（round 0） | 事实依据：review-record 输出摘要（机器写入） | report.md; "
    "review-{task}-R0.md | Code Reviewer | 2026-08-22 | G11 | {result}{tail_cols}"
)
LEGACY_ROW = (
    "| REVIEW-{task}-CODE-R0 | {task} | 产品代码 | Code Review R0（独立 Reviewer，"
    "2026-08-22）：{result}（unresolved_blockers=0） | 事实依据：diff 逐行 | "
    "r0.patch | Code Reviewer | 2026-08-22 | G11 | {result} |"
)


def _row(form, task="FIX-261", result="APPROVED_WITH_NOTES", tail_cols=" |"):
    if form == "machine":
        return MACHINE_ROW.format(
            task=task, result=result, tail_cols=tail_cols)
    return LEGACY_ROW.format(task=task, result=result)


def _win_to_msys_or_wsl(path_text):
    """``C:/Users/x`` → ``/mnt/c/Users/x`` (WSL form; git-bash /c/ form is
    produced by cygpath at runtime when the /mnt form does not exist)."""
    m = re.match(r"^([A-Za-z]):/(.*)$", path_text)
    if not m:
        return path_text
    return "/mnt/{0}/{1}".format(m.group(1).lower(), m.group(2))


def _run_hook_function(hook_path, task_id, evidence_text, repo_root=None):
    """Extract the function from hook source and execute it in bash.

    Harness notes (all discovered the hard way on Windows):
      * The script is fed to ``bash -s`` as raw UTF-8 BYTES via stdin — in
        text mode Python's newline translation rewrites every ``\\n`` to
        ``\\r\\n`` (os.linesep), which breaks bash parsing.
      * ``\\r`` is stripped from the extracted function text (hook sources
        may carry CRLF endings).
      * The repo root is probed as a WSL ``/mnt/<drive>/...`` path first,
        then via ``cygpath -u`` (git-bash), then the raw forward-slash
        Win32 path — covering WSL bash, git-bash, and native bash alike.
    Returns True/False (hit/miss)."""
    fn = _extract_function(hook_path)
    with tempfile.TemporaryDirectory() as td:
        root = Path(repo_root) if repo_root else Path(td)
        if repo_root is None:
            gov = root / ".governance"
            gov.mkdir(exist_ok=True)
            (gov / "evidence-log.md").write_text(
                evidence_text, encoding="utf-8")
        root_posix = str(root).replace("\\", "/")
        root_wsl = _win_to_msys_or_wsl(root_posix)
        script = (
            "REPO_ROOT={0!r}\n"
            "[ -d \"$REPO_ROOT\" ] || REPO_ROOT=$(cygpath -u {1!r} 2>/dev/null || echo {1!r})\n"
            "{2}\n"
            'if has_approved_review_evidence "{3}"; then echo HIT; else echo MISS; fi\n'
        ).format(root_wsl, root_posix, fn, task_id)
        script = script.replace("\r\n", "\n").replace("\r", "\n")
        proc = subprocess.run(
            ["bash", "-s"], input=script.encode("utf-8"),
            capture_output=True, timeout=30,
        )
        out = proc.stdout.decode("utf-8", "replace").strip()
        if out not in ("HIT", "MISS"):
            raise AssertionError(
                "hook function run failed: rc={0} stdout={1!r} stderr={2!r}".format(
                    proc.returncode, proc.stdout, proc.stderr[:400]))
        return out == "HIT"


@unittest.skipUnless(shutil.which("bash"), "bash unavailable (hooks are bash)")
class ReviewEvidenceRegexTests(unittest.TestCase):
    """FIX-261 four-form fixtures, run against BOTH hook copies."""

    def _self_and_commit_msg(self):
        """Run the same assertion against pre-commit AND its commit-msg twin."""
        return ((_PRE_COMMIT, "pre-commit"), (_COMMIT_MSG, "commit-msg"))

    def test_a_legacy_end_column_hits(self):
        """Form (a): legacy end-column APPROVED_WITH_NOTES → HIT (compat)."""
        for hook, name in self._self_and_commit_msg():
            with self.subTest(hook=name):
                self.assertTrue(
                    _run_hook_function(hook, "FIX-261", _row("legacy") + "\n"))

    def test_b_machine_row_with_zero_blockers_hits(self):
        """Form (b): machine 11-col + tail unresolved_blockers=0 → HIT.

        Red before FIX-261: the old end-column regex missed this row and
        blocked FIX-260's own commit (the C8 dogfood incident)."""
        for hook, name in self._self_and_commit_msg():
            with self.subTest(hook=name):
                self.assertTrue(_run_hook_function(
                    hook, "FIX-261",
                    _row("machine",
                         tail_cols=" | unresolved_blockers=0 |") + "\n"))

    def test_c_machine_row_with_nonzero_blockers_misses(self):
        """Form (c): APPROVED_WITH_NOTES + unresolved_blockers=1 → MISS."""
        for hook, name in self._self_and_commit_msg():
            with self.subTest(hook=name):
                self.assertFalse(_run_hook_function(
                    hook, "FIX-261",
                    _row("machine",
                         tail_cols=" | unresolved_blockers=1 |") + "\n"))

    def test_d_needs_change_misses_both_forms(self):
        """Form (d): NEEDS_CHANGE never passes — legacy or machine shape."""
        for hook, name in self._self_and_commit_msg():
            with self.subTest(hook=name, form="legacy"):
                self.assertFalse(_run_hook_function(
                    hook, "FIX-261",
                    _row("legacy", result="NEEDS_CHANGE") + "\n"))
            with self.subTest(hook=name, form="machine"):
                self.assertFalse(_run_hook_function(
                    hook, "FIX-261",
                    _row("machine", result="NEEDS_CHANGE") + "\n"))

    def test_blocked_never_passes(self):
        """BLOCKED is not an approval — machine shape must MISS."""
        for hook, name in self._self_and_commit_msg():
            with self.subTest(hook=name):
                self.assertFalse(_run_hook_function(
                    hook, "FIX-261",
                    _row("machine", result="BLOCKED") + "\n"))

    def test_machine_plain_approved_still_hits(self):
        """Machine APPROVED row (no blockers tail, 10 cols) → HIT via (a)."""
        for hook, name in self._self_and_commit_msg():
            with self.subTest(hook=name):
                self.assertTrue(_run_hook_function(
                    hook, "FIX-261", _row("machine", result="APPROVED") + "\n"))

    def test_blockers_tail_must_be_exactly_zero(self):
        """unresolved_blockers=01 / =0;extra must not smuggle through."""
        for tail_cols in (" | unresolved_blockers=01 |",
                          " | unresolved_blockers=0 extra |"):
            for hook, name in self._self_and_commit_msg():
                with self.subTest(hook=name, tail_cols=tail_cols):
                    self.assertFalse(_run_hook_function(
                        hook, "FIX-261",
                        _row("machine", tail_cols=tail_cols) + "\n"))

    def test_plain_approved_with_blockers_tail_misses(self):
        """Only APPROVED_WITH_NOTES may take form (b): APPROVED + tail → MISS."""
        for hook, name in self._self_and_commit_msg():
            with self.subTest(hook=name):
                self.assertFalse(_run_hook_function(
                    hook, "FIX-261",
                    _row("machine", result="APPROVED",
                         tail_cols=" | unresolved_blockers=0 |") + "\n"))

    def test_other_task_machine_row_does_not_hit(self):
        """Prefix binding: a machine row for FIX-999 must not unblock FIX-261."""
        for hook, name in self._self_and_commit_msg():
            with self.subTest(hook=name):
                self.assertFalse(_run_hook_function(
                    hook, "FIX-261",
                    _row("machine", task="FIX-999",
                         tail_cols=" | unresolved_blockers=0 |") + "\n"))

    def test_hook_copies_stay_identical(self):
        """The pre-commit and commit-msg copies must remain byte-identical."""
        self.assertEqual(_extract_function(_PRE_COMMIT),
                         _extract_function(_COMMIT_MSG))

    def test_replay_real_evidence_log_fix260(self):
        """FIX-261 acceptance replay: the REAL evidence-log machine row for
        FIX-260 (R0 APPROVED_WITH_NOTES/0, written via review-record CLI)
        must HIT the updated hook function."""
        if not _EVIDENCE.is_file():
            self.skipTest("live evidence-log unavailable")
        for hook, name in self._self_and_commit_msg():
            with self.subTest(hook=name):
                self.assertTrue(_run_hook_function(
                    hook, "FIX-260", "", repo_root=_REPO_ROOT))


if __name__ == "__main__":
    unittest.main()
