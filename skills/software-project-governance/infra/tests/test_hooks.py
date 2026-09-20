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

FEAT-017 extension: post-commit Step 4b governance-write-guard panel
wiring. The wiring block is ONE contiguous section in the shipped
post-commit source; these tests bind to the literal section (same
no-unbound-copy strategy as the FIX-282 matcher tests): static pins prove
the invocation contract, verdict-line gate, timeout protection, set -e
safety and the documented rollback path; when a functional bash exists the
extracted section is executed end-to-end over a stub verify_workflow.py and
the four observable states (PASS / FAIL / SKIP / UNAVAILABLE) are asserted —
including that a crashed guard (rc=1 WITHOUT a ``Result: FAIL`` line) is
disclosed as UNAVAILABLE, never rendered as a false FAIL verdict.
"""

import os
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
_POST_COMMIT = _HOOKS_DIR / "post-commit"
_PLAN = _REPO_ROOT / ".governance" / "plan-tracker.md"

_WG_SECTION_RE = re.compile(
    r"(?ms)^# --- Step 4b: governance-write-guard panel wiring.*?"
    r"(?=^# --- Step 5:)")

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


_TASK_ID_RE = re.compile(r"[A-Z]+-[0-9]+")


def _live_task_ids(plan_text):
    """Independent live-row parse (FIX-359 replay re-anchor): the task-ID
    cell of every P{n}-first table row, bold markers stripped. Deliberately
    string-split + fullmatch — NOT the hook ERE — so agreement between this
    parse and the matcher is a real cross-engine check on live data."""
    ids = set()
    for line in plan_text.splitlines():
        cells = line.split("|")
        if len(cells) < 4:
            continue
        priority = cells[1].strip().strip("*").strip()
        task_cell = cells[2].strip().strip("*").strip()
        if (re.fullmatch(r"P[0-9]+", priority)
                and _TASK_ID_RE.fullmatch(task_cell)):
            ids.add(task_cell)
    return ids


def _wg_section():
    """Extract the shipped post-commit Step 4b write-guard wiring block."""
    text = _POST_COMMIT.read_text(encoding="utf-8")
    m = _WG_SECTION_RE.search(text)
    if not m:
        raise AssertionError(
            "post-commit Step 4b write-guard wiring (FEAT-017) not found "
            "in {0}".format(_POST_COMMIT))
    return m.group(0)


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
        """Live replay (skipped offline): every live task row in the REAL
        plan-tracker must HIT the matcher; an absent ID must MISS.

        FIX-359 re-anchor (RISK-056): this replay previously pinned six
        0.78.x-era IDs (REL-071/REL-072/FIX-282/REL-073/FIX-283/FIX-288);
        their task rows have since been archived out of the live
        plan-tracker (live-data growth), so the static pins drifted and the
        matcher — correctly — stopped hitting them. The positive set is now
        derived from the authoritative source at run time (FIX-352/353
        dynamic-pin precedent) via the independent parse in
        ``_live_task_ids``; matcher semantics stay pinned by the offline
        constructed-fragment tests plus the absent-ID MISS below.
        """
        if not _PLAN.is_file():
            self.skipTest("live .governance/plan-tracker.md unavailable")
        plan_text = _PLAN.read_text(encoding="utf-8")
        live_ids = _live_task_ids(plan_text)
        self.assertTrue(
            live_ids,
            "no live task rows parsed from the real plan-tracker — table "
            "format drifted past the independent parse; re-inspect")
        for task_id in sorted(live_ids):
            with self.subTest(task_id=task_id):
                self.assertTrue(_run_pattern(task_id, plan_text))
        absent = "FIX-9999"
        self.assertNotIn(absent, live_ids)
        self.assertFalse(_run_pattern(absent, plan_text))


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


class PostCommitWriteGuardWiringTests(unittest.TestCase):
    """FEAT-017 static binding pins over the literal shipped Step 4b block."""

    def test_section_extraction_works(self):
        """Binding: the wiring block must exist in the shipped post-commit."""
        section = _wg_section()
        self.assertIn("FEAT-017", section)

    def test_invocation_contract(self):
        """The guard subcommand is invoked with an explicit project root so
        the verdict always targets THIS repo's .governance (cwd-independent),
        reusing the hook's already-resolved VERIFY_WORKFLOW path."""
        section = _wg_section()
        self.assertIn("governance-write-guard", section)
        self.assertIn('--project-root "$REPO_ROOT"', section)
        self.assertIn('"$VERIFY_WORKFLOW"', section)

    def test_verdict_line_gate_present(self):
        """Honesty gate: rc alone must not render a verdict — both PASS and
        FAIL branches require the CLI's authoritative Result line (an
        uncaught python exception also exits rc=1; rendering that as FAIL
        would be a false verdict)."""
        section = _wg_section()
        self.assertIn("grep -q '^Result: PASS'", section)
        self.assertIn("grep -q '^Result: FAIL'", section)

    def test_panel_markers(self):
        """Panel vocabulary: PASS one-liner / FAIL box / SKIP + UNAVAILABLE
        single-line disclosures (existing hook idiom — no ANSI codes)."""
        section = _wg_section()
        self.assertIn("✅ GOVERNANCE: write-guard PASS", section)
        self.assertIn("${SPG_WG_ELAPSED}", section)  # elapsed-time placeholder
        self.assertIn("WRITE-GUARD FAIL", section)
        self.assertIn("SKIPPED — no .governance", section)
        self.assertIn("SKIPPED — verify_workflow.py not found", section)
        self.assertIn("SKIPPED — no python interpreter", section)
        self.assertIn("UNAVAILABLE", section)

    def test_timeout_protection_present(self):
        """The guard call is wrapped by a VERIFIED GNU coreutils timeout
        (System32 timeout.exe is a pause command and must never wrap it);
        without GNU timeout the call degrades to unwrapped, never mis-wrapped."""
        section = _wg_section()
        self.assertIn('timeout "$SPG_WG_TIMEOUT_SECONDS"', section)
        self.assertIn("GNU coreutils", section)
        self.assertIn("SPG_WG_TIMEOUT_SECONDS=30", section)

    def test_set_e_safe_rc_capture(self):
        """rc capture uses the || capture idiom so a FAIL verdict (rc=1)
        cannot abort the hook under `set -e`."""
        self.assertIn("|| SPG_WG_RC=$?", _wg_section())

    def test_rollback_documented(self):
        """FEAT-017 acceptance 3: deleting the block restores the FIX-297
        scheme-2 pure protocol-rule posture — documented in the section."""
        section = _wg_section()
        self.assertIn("ROLLBACK", section)
        self.assertIn("FIX-297", section)

    def test_section_never_blocks(self):
        """post-commit stays advisory: the wiring must contain no exit-1 /
        exit-2 statement of its own (comments deliberately use rc= forms)."""
        section = _wg_section()
        self.assertNotIn("exit 1", section)
        self.assertNotIn("exit 2", section)

    def test_section_self_contained(self):
        """The block only reads REPO_ROOT + VERIFY_WORKFLOW (both set by
        Step 4 and earlier) plus its own SPG_WG_* locals — no hidden
        coupling to Step 5 state (LOCKS_FILE) or resolution internals."""
        section = _wg_section()
        self.assertNotIn("SPG_RESOLVED_HOME", section)
        self.assertNotIn("TASK_ID", section)
        self.assertNotIn("LOCKS_FILE", section)

    def test_warn_count_line_present(self):
        """FEAT-057 R0 P2-1: WARN-class face-5 issues leave the exit code at
        0, so the hook panel must surface their count from the guard's
        Result line — the main automation surface's only trace of a
        hand-edited row (the hook run consumes the reconciliation window)."""
        section = _wg_section()
        self.assertIn("0 FAIL issue(s)", section)
        self.assertIn("run governance-write-guard for details", section)
        # the disclosure is WARN-gated: zero WARNs → no extra line
        self.assertIn('-gt 0', section)


# Stub verify_workflow.py stand-in for behavioral runs: emits the REAL CLI's
# output shapes (issue lines "    - ...", authoritative Result line) with a
# configurable verdict, and touches a marker file when actually invoked so
# SKIP-path tests can prove the guard was NOT called (test fixture, not a
# production mock — the shipped hook always resolves the real script).
_WG_STUB = """\
import os
import sys

# The REAL CLI reconfigures stdout to UTF-8 (cmd_governance_write_guard);
# the stub must match that posture or its em-dash Result lines reach the
# hook's sed as GBK bytes and stop matching (Windows piped-stdout default).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

marker = os.environ.get("WG_STUB_MARKER", "")
if marker:
    open(marker, "w").close()
mode = os.environ.get("WG_STUB_MODE", "pass")
print("=== Governance Write Guard (stub) ===")
if mode == "fail":
    print("  [FAIL] evidence_log 机器行族 TRIAGE/RECO — 2 issue(s)")
    print("    - L42 TRIAGE-FEAT017: 列数 7 ≠ 行族标准 6")
    print("    - L57 RECO-999: writer ID 格式破坏")
    print()
    print("Result: FAIL — 2 issue(s)。守卫只检不改。")
    sys.exit(1)
if mode == "crash":
    sys.exit(1)
if mode == "warn":
    print("  [PASS] 受管行族对账（FEAT-057） — 2 issue(s)")
    print("    - L2 EVD-9001: unattributed row change — use governance_store")
    print("    - L3 FIX-100: unattributed row change — use task_row_update")
    print()
    print("Result: PASS — 0 FAIL issue(s), 2 WARN(s)（响亮披露不阻断）。")
    sys.exit(0)
print("  [PASS] plan_tracker — 0 issue(s)")
print()
print("Result: PASS — 0 issue(s)（SKIPPED = 产物缺席，非缺陷）。")
sys.exit(0)
"""


def _find_python_for_bash(bash_path):
    """Return 'python'/'python3' as resolvable INSIDE the bash env, or None."""
    if not bash_path:
        return None
    try:
        proc = subprocess.run(
            [bash_path, "-c",
             'command -v python >/dev/null 2>&1 && echo python || '
             '{ command -v python3 >/dev/null 2>&1 && echo python3; }'],
            capture_output=True, timeout=15, check=False,
            stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return None
    out = proc.stdout.decode("utf-8", "replace").strip()
    return out if out in ("python", "python3") else None


_BASH_PYTHON = _find_python_for_bash(_BASH)


@unittest.skipUnless(_BASH, "no functional bash (git-bash/WSL/native)")
@unittest.skipUnless(_BASH_PYTHON, "no python interpreter inside bash env")
class PostCommitWriteGuardPanelTests(unittest.TestCase):
    """FEAT-017 behavioral runs: the literal shipped Step 4b section is
    executed under `set -e` over a stub verify_workflow.py; every state must
    render its panel line AND let the script continue (no abort)."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        root = Path(self._td.name)
        self.repo = root / "repo"
        (self.repo / ".governance").mkdir(parents=True)
        (self.repo / ".governance" / "plan-tracker.md").write_text(
            "# plan\n\n| **P1** | FIX-001 | demo | — | 0.80.0 |\n",
            encoding="utf-8")
        self.stub = root / "guard_stub.py"
        self.stub.write_text(_WG_STUB, encoding="utf-8")
        self.marker = root / "stub_invoked.marker"

    def tearDown(self):
        self._td.cleanup()

    def _run_section(self, repo_root, verify_workflow, mode):
        script = (
            "set -e\n"
            "REPO_ROOT={0!r}\n"
            "VERIFY_WORKFLOW={1!r}\n"
            "{2}\n"
            "echo '__WG_DONE__'\n"
        ).format(
            str(repo_root).replace("\\", "/"),
            str(verify_workflow).replace("\\", "/"),
            _wg_section())
        script = script.replace("\r\n", "\n").replace("\r", "\n")
        env = dict(os.environ)
        env["WG_STUB_MODE"] = mode
        env["WG_STUB_MARKER"] = str(self.marker).replace("\\", "/")
        proc = subprocess.run(
            [_BASH, "-s"], input=script.encode("utf-8"),
            capture_output=True, timeout=60, check=False, env=env)
        return (proc.stdout.decode("utf-8", "replace"),
                proc.returncode, proc.stderr.decode("utf-8", "replace"))

    def test_pass_state_renders_pass_line(self):
        out, rc, err = self._run_section(self.repo, self.stub, "pass")
        self.assertIn("GOVERNANCE: write-guard PASS", out)
        self.assertIn("结构检查通过", out)
        # zero-WARN PASS renders NO warn-count disclosure line
        self.assertNotIn("run governance-write-guard for details", out)
        self.assertNotIn("UNAVAILABLE", out)
        self.assertNotIn("SKIPPED", out)
        self.assertIn("__WG_DONE__", out)  # set -e survival
        self.assertTrue(self.marker.exists())  # guard actually invoked

    def test_warn_state_renders_warn_count_line(self):
        """FEAT-057 R0 P2-1: a WARN-class PASS (face-5 row-family
        reconciliation) keeps rc=0 but its count surfaces on the hook
        panel — the window consumed by this run is not silent."""
        out, rc, err = self._run_section(self.repo, self.stub, "warn")
        self.assertIn("GOVERNANCE: write-guard PASS", out)
        self.assertIn("write-guard: 2 WARN(s)", out)
        self.assertIn("run governance-write-guard for details", out)
        self.assertIn("__WG_DONE__", out)  # set -e survival
        self.assertTrue(self.marker.exists())

    def test_fail_state_renders_panel_and_continues(self):
        out, rc, err = self._run_section(self.repo, self.stub, "fail")
        self.assertIn("WRITE-GUARD FAIL", out)
        self.assertIn("L42 TRIAGE-FEAT017", out)  # first-N issue passthrough
        self.assertIn("L57 RECO-999", out)
        self.assertIn("governance-write-guard", out)  # rerun command hint
        self.assertIn("__WG_DONE__", out)  # FAIL verdict must not abort
        self.assertTrue(self.marker.exists())

    def test_crash_rc1_without_verdict_is_unavailable_not_fail(self):
        out, rc, err = self._run_section(self.repo, self.stub, "crash")
        self.assertIn("UNAVAILABLE", out)
        self.assertNotIn("WRITE-GUARD FAIL", out)  # no false verdict
        self.assertIn("__WG_DONE__", out)

    def test_skip_when_no_governance_dir(self):
        plain = Path(self._td.name) / "plain"
        plain.mkdir()
        out, rc, err = self._run_section(plain, self.stub, "pass")
        self.assertIn("SKIPPED — no .governance", out)
        self.assertFalse(self.marker.exists())  # guard NOT invoked
        self.assertIn("__WG_DONE__", out)

    def test_skip_when_no_verify_workflow(self):
        out, rc, err = self._run_section(self.repo, "", "pass")
        self.assertIn("SKIPPED — verify_workflow.py not found", out)
        self.assertFalse(self.marker.exists())
        self.assertIn("__WG_DONE__", out)


if __name__ == "__main__":
    unittest.main()
