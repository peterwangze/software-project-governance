"""FIX-282 / DEC-171 — commit-msg Step 3 plan-tracker task-row matcher tests.

The hook's ``task_in_plan_tracker()`` must accept BOTH markdown conventions
present in ``.governance/plan-tracker.md``:

  (a) bold priority + bold task ID  (``| **P1** | **REL-071** |`` — the
      DEC-171 evidenced shape; the pre-FIX-282 literal ``| TASK_ID |`` grep
      never matched it, so REL-071's M-5 transition commit (afb959d) had to
      take the ``--no-verify`` emergency bypass);
  (b) bold priority + plain task ID (``| **P2** | FIX-282 |`` — current);
  (c) legacy plain row              (``| P2 | FIX-282 |`` — compat).

M7.5 semantics preserved: an absent task row must MISS, so a typo'd or
unplanned ID still FAILS Step 3 (no false pass).

Binding strategy (no unbound copy): the matcher is ONE literal ERE string
inside the shipped hook source. The tests extract the function AND that
pattern literal from the hook file, assert the pattern stays inside the
grep-ERE / Python-re equivalence subset (documented in the hook comment),
then exercise the literal pattern against constructed plan-tracker
fragments (fully offline). When a functional bash is available
(git-for-windows / WSL / native), the extracted function is additionally
executed in bash and the verdicts are asserted to agree (dual-engine
parity). The Step 3 integration is pinned too: the hook must call the
matcher, and the old literal grep must not regress in.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_hooks.py -v
    python skills/software-project-governance/infra/tests/test_hooks.py
"""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

_INFRA_DIR = Path(__file__).resolve().parent.parent
_HOOKS_DIR = _INFRA_DIR / "hooks"
_REPO_ROOT = _INFRA_DIR.parent.parent.parent  # <repo>/skills/<skill>/infra -> <repo>
_COMMIT_MSG = _HOOKS_DIR / "commit-msg"
_PLAN = _REPO_ROOT / ".governance" / "plan-tracker.md"

_FN_RE = re.compile(r"(?ms)^task_in_plan_tracker\(\) \{.*?^\}")
_PATTERN_RE = re.compile(r'grep -Eq "([^"]+)"')


def _extract_function(hook_path):
    text = hook_path.read_text(encoding="utf-8")
    m = _FN_RE.search(text)
    if not m:
        raise AssertionError(
            "task_in_plan_tracker() not found in {0}".format(hook_path))
    return m.group(0)


def _extract_pattern(fn_text):
    m = _PATTERN_RE.search(fn_text)
    if not m:
        raise AssertionError(
            "ERE pattern literal (grep -Eq \"...\") not found in "
            "task_in_plan_tracker()")
    return m.group(1)


def _pattern_for(task_id):
    return _extract_pattern(_extract_function(_COMMIT_MSG)).replace(
        "${task_id}", task_id)


# Equivalence-subset guard (FIX-282): the hook pattern may only use
# constructs whose grep-ERE and Python-re meanings are provably identical —
# single-char literal classes ([|], [*], [0-9]), '*', '+', '{0,2}', '^' and
# plain literals. Backslash escapes and ':' (POSIX [:class:] markers) are
# forbidden so the test can drive the exact shipped pattern. Any future edit
# that introduces e.g. '[[:space:]]' or '\t' FAILS this guard loudly.
_EQUIV_SUBSET_CHARS = re.compile(r"^[0-9A-Za-z ^#${}\[\]|*,.+()?%_-]+$")


def _assert_equivalence_subset(pattern):
    if not _EQUIV_SUBSET_CHARS.match(pattern):
        raise AssertionError(
            "hook matcher pattern left the grep-ERE/Python-re equivalence "
            "subset: {0!r}. Keep single-char literal classes, quantifiers "
            "'*' '+' '{n,m}', '^' and literals only (no backslash escapes, "
            "no POSIX [:classes:]...). See test_hooks.py docs.".format(pattern))


def _matches_line(pattern, line):
    return re.match(pattern, line) is not None


def _run_pattern(task_id, plan_text):
    """Drive the literal hook pattern (Python re) over a plan fragment."""
    pattern = _pattern_for(task_id)
    _assert_equivalence_subset(
        _extract_pattern(_extract_function(_COMMIT_MSG)))
    return any(_matches_line(pattern, line) for line in plan_text.splitlines())


def _fragment(*rows):
    """A realistic plan-tracker fragment (header + blank-line separators)."""
    header = (
        "## 活跃任务表\n\n"
        "| 优先级 | 任务 ID | 任务描述 | 依赖 | 版本 |\n"
        "|---|---|---|---|---|\n"
    )
    return header + "\n".join(rows) + "\n"


def _find_bash():
    """Return a FUNCTIONAL bash executable, or None (WSL stub excluded)."""
    candidates = []
    which = shutil.which("bash")
    if which:
        candidates.append(which)
    for p in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ):
        if Path(p).is_file():
            candidates.append(p)
    for cand in candidates:
        try:
            proc = subprocess.run(
                [cand, "-c", ":"], capture_output=True, timeout=10,
                check=False, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if proc.returncode == 0:
            return cand
    return None


_BASH = _find_bash()


def _run_bash_function(bash_path, task_id, plan_text):
    """Execute the extracted hook function in bash over a temp plan fragment.

    Returns True/False (HIT/MISS); raises AssertionError on unexpected output
    (e.g. the WSL-no-distro stub getting through) — never a silent False.
    """
    fn = _extract_function(_COMMIT_MSG)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        gov = root / ".governance"
        gov.mkdir(exist_ok=True)
        (gov / "plan-tracker.md").write_text(plan_text, encoding="utf-8")
        root_posix = str(root).replace("\\", "/")
        script = (
            "REPO_ROOT={0!r}\n"
            'if ! [ -d "$REPO_ROOT" ]; then\n'
            "  REPO_ROOT=$(cygpath -u {1!r} 2>/dev/null || printf '%s\\n' {1!r})\n"
            "fi\n"
            "{2}\n"
            'if task_in_plan_tracker "{3}"; then echo HIT; else echo MISS; fi\n'
        ).format(root_posix, root_posix, fn, task_id)
        script = script.replace("\r\n", "\n").replace("\r", "\n")
        proc = subprocess.run(
            [bash_path, "-s"], input=script.encode("utf-8"),
            capture_output=True, timeout=30, check=False,
        )
        out = proc.stdout.decode("utf-8", "replace").strip()
        if out not in ("HIT", "MISS"):
            raise AssertionError(
                "hook function run failed: rc={0} stdout={1!r} stderr={2!r}".format(
                    proc.returncode, proc.stdout, proc.stderr[:400]))
        return out == "HIT"


class PlanTrackerMatcherTests(unittest.TestCase):
    """FIX-282 matcher semantics, driven by the literal hook pattern."""

    def test_pattern_extracted_from_hook_source(self):
        """Binding: function + pattern literal must exist in the hook source
        and the pattern must carry the ${task_id} placeholder."""
        fn = _extract_function(_COMMIT_MSG)
        pattern = _extract_pattern(fn)
        self.assertIn("${task_id}", pattern)
        self.assertIn("grep -Eq", fn)

    def test_pattern_stays_in_equivalence_subset(self):
        """Guard: pattern may not drift into engine-divergent constructs."""
        _assert_equivalence_subset(_extract_pattern(_extract_function(_COMMIT_MSG)))

    def test_bold_priority_bold_task_id_hits(self):
        """(a) DEC-171 shape: | **P1** | **REL-071** | → HIT."""
        plan = _fragment(
            "| **P1** | **REL-071** | 发布 0.78.0——加粗 ID 形态（DEC-171 实证） | FIX-278 | 0.78.0 |")
        self.assertTrue(_run_pattern("REL-071", plan))

    def test_bold_priority_plain_task_id_hits(self):
        """(b) Current shape: | **P2** | FIX-282 | → HIT."""
        plan = _fragment(
            "| **P2** | FIX-282 | DEC-171 commit-msg Step 3 匹配缺陷修复 | DEC-171 | 0.78.1 |")
        self.assertTrue(_run_pattern("FIX-282", plan))

    def test_legacy_plain_row_hits(self):
        """(c) Legacy shape: | P2 | FIX-283 | → HIT (no bold anywhere)."""
        plan = _fragment("| P2 | FIX-283 | 非加粗旧格式兼容行 | DEC-172 | 0.78.1 |")
        self.assertTrue(_run_pattern("FIX-283", plan))

    def test_mixed_table_all_rows_hit(self):
        """Real-world mixed table: every present task row must HIT."""
        plan = _fragment(
            "| **P1** | REL-073 | 发布 0.78.1（规划段） | DEC-172 | 0.78.1 |",
            "| **P1** | **REL-072** | 出槽队列 triage | REL-071 | — |",
            "| **P2** | FIX-283 | N-P2 卫生批 | FIX-278 | 0.78.1 |")
        for task_id in ("REL-073", "REL-072", "FIX-283"):
            with self.subTest(task_id=task_id):
                self.assertTrue(_run_pattern(task_id, plan))

    def test_absent_task_misses(self):
        """Semantics preserved: an ID that is not in the table must MISS."""
        plan = _fragment(
            "| **P1** | REL-070 | 发布 0.78.0 | — | 0.78.0 |",
            "| **P2** | FIX-283 | N-P2 卫生批 | FIX-278 | 0.78.1 |")
        self.assertFalse(_run_pattern("FIX-9999", plan))

    def test_mention_in_description_cell_misses(self):
        """No false pass: TASK_ID appearing inside the description cell of a
        DIFFERENT task row must not count as the task existing."""
        plan = _fragment(
            "| **P1** | FIX-284 | 关联 FIX-282（描述列提及） | FIX-279 | 0.78.1 |")
        self.assertFalse(_run_pattern("FIX-282", plan))

    def test_id_in_third_column_misses(self):
        """No false pass: TASK_ID as a bare cell in column 3+ must not count."""
        plan = _fragment(
            "| **P1** | REL-073 | FIX-282 | DEC-172 | 0.78.1 |")
        self.assertFalse(_run_pattern("FIX-282", plan))

    def test_non_task_table_row_misses(self):
        """No false pass: first cell must be a priority (P{n}); rows of other
        tables (e.g. gate tracking '| G1 | ...') must not satisfy existence."""
        plan = _fragment(
            "| G1 | FIX-282 | 门禁记录表 | — | — |",
            "| **P2** | FIX-283 | N-P2 卫生批 | FIX-278 | 0.78.1 |")
        self.assertFalse(_run_pattern("FIX-282", plan))

    def test_req_matrix_row_misses(self):
        """P2-1 MISS anchor: 需求跟踪矩阵 rows lead with REQ-xxx (requirement
        ID first cell, not a priority cell) — a requirement ID must not
        satisfy task existence. The pre-FIX-282 literal grep DID match these
        rows ('| REQ-002 | ...', verified 1 hit on the real plan-tracker),
        the anchored matcher must MISS (semantic tightening locked against
        regressions)."""
        plan = _fragment(
            "| REQ-002 | 用户能在 5 分钟内完成初始化 | PR/FAQ | P0 | MAINT-012 | ⚠️ 部分 | — |")
        self.assertFalse(_run_pattern("REQ-002", plan))
        self.assertFalse(_run_pattern("REQ-107", plan))

    def test_archive_pointer_row_misses(self):
        """P2-1 MISS anchor: archived-task pointer rows lead with '—'
        (em-dash placeholder first cell, not a priority): '| — | FIX-082 |'. 
        The pre-FIX-282 literal grep matched them (verified 1 hit on the real
        plan-tracker — an archived task could satisfy 'exists'), the anchored
        matcher must MISS so archived rows cannot resurrect a task row."""
        plan = _fragment(
            "| — | FIX-082 | Runtime capability contract（0.38.0 发布链） | AUDIT-102 | 0.38.0 | ✅ 已交付 |")
        self.assertFalse(_run_pattern("FIX-082", plan))
        self.assertFalse(_run_pattern("FIX-083", plan))

    def test_step3_uses_matcher_not_literal_grep(self):
        """Integration pin: Step 3 must call task_in_plan_tracker and the
        old literal '| $TASK_ID |' grep must not regress into the hook."""
        text = _COMMIT_MSG.read_text(encoding="utf-8")
        self.assertIn("if ! task_in_plan_tracker \"$TASK_ID\"; then", text)
        self.assertNotIn('grep -q "| $TASK_ID |"', text)

    def test_replay_real_plan_tracker_hits(self):
        """Live replay (skipped offline): the REAL plan-tracker rows — bold
        IDs (REL-071/REL-072), plain IDs (FIX-282/REL-073/FIX-283/FIX-288)
        — must HIT the matcher; an absent ID must MISS."""
        if not _PLAN.is_file():
            self.skipTest("live .governance/plan-tracker.md unavailable")
        plan_text = _PLAN.read_text(encoding="utf-8")
        for task_id in ("REL-071", "REL-072", "FIX-282", "REL-073",
                        "FIX-283", "FIX-288"):
            with self.subTest(task_id=task_id):
                self.assertTrue(_run_pattern(task_id, plan_text))
        self.assertFalse(_run_pattern("FIX-9999", plan_text))


@unittest.skipUnless(_BASH, "no functional bash (git-bash/WSL/native)")
class BashParityTests(unittest.TestCase):
    """Dual-engine parity: bash execution of the extracted function must
    agree with the Python-re verdicts (FIX-282 binding guarantee)."""

    def test_bash_hits_bold_and_plain_rows(self):
        plan = _fragment(
            "| **P1** | **REL-071** | 加粗 ID 行（DEC-171 实证） | — | 0.78.0 |",
            "| **P2** | FIX-282 | 普通 ID 行 | DEC-171 | 0.78.1 |")
        for task_id in ("REL-071", "FIX-282"):
            with self.subTest(task_id=task_id):
                self.assertTrue(_run_bash_function(_BASH, task_id, plan))
                self.assertTrue(_run_pattern(task_id, plan))

    def test_bash_misses_absent_task(self):
        plan = _fragment(
            "| **P2** | FIX-283 | N-P2 卫生批 | FIX-278 | 0.78.1 |")
        self.assertFalse(_run_bash_function(_BASH, "FIX-9999", plan))
        self.assertFalse(_run_pattern("FIX-9999", plan))

    def test_bash_misses_description_mention(self):
        plan = _fragment(
            "| **P1** | FIX-284 | 关联 FIX-282（描述列） | FIX-279 | 0.78.1 |")
        self.assertFalse(_run_bash_function(_BASH, "FIX-282", plan))


if __name__ == "__main__":
    unittest.main()
