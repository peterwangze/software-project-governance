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

import json
import os
import re
import shutil
import subprocess
import sys
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
    """Return a FUNCTIONAL, PATH-COMPATIBLE bash executable, or None.

    FIX-444 (same-session diagnosis): the old probe only ran ``:`` — a
    WSL bash WITH a distro installed is functional under that probe yet
    cannot resolve the Windows-style ``C:/`` fixture paths these tests
    feed it, so every file-based bash verdict silently MISSed/SKIPped
    (BashParity MISSes; write-guard panels "no .governance/").  On
    Windows a candidate must now ALSO prove drive-letter path
    compatibility; non-Windows hosts keep the plain functional probe
    (their tempfile fixtures are already POSIX paths)."""
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
    probe = "test -d 'C:/'" if sys.platform == "win32" else ":"
    for cand in candidates:
        try:
            proc = subprocess.run(
                [cand, "-c", probe], capture_output=True, timeout=10,
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


# ── FIX-444/FIX-445: Step 12 fabrication-term source-verified scan ──────────

_FAB_FN_RE = re.compile(r"(?ms)^has_unnegated_fabrication_terms\(\) \{.*?^\}")
_MASK_FN_RE = re.compile(r"(?ms)^json_region_mask\(\) \{.*?^\}")
_ENGINE_FN_RE = re.compile(r"(?ms)^_fix445_engine_code\(\) \{.*?^\}")
_VERIFY_FN_RE = re.compile(r"(?ms)^_fix445_verify\(\) \{.*?^\}")
_FRAME_FN_RE = re.compile(r"(?ms)^endorsement_frame_check\(\) \{.*?^\}")
_STRIP_FN_RE = re.compile(r"(?ms)^strip_mention_clauses\(\) \{.*?^\}")


def _extract_fn(pattern, name, hook_path=_COMMIT_MSG):
    text = hook_path.read_text(encoding="utf-8")
    m = pattern.search(text)
    if not m:
        raise AssertionError(
            "{0} not found in {1} — FIX-445 source-verification scan "
            "incomplete".format(name, hook_path))
    return m.group(0)


def _extract_fabrication_fn(hook_path=_COMMIT_MSG):
    return _extract_fn(_FAB_FN_RE, "has_unnegated_fabrication_terms()",
                       hook_path)


def _extract_mask_fn(hook_path=_COMMIT_MSG):
    return _extract_fn(_MASK_FN_RE, "json_region_mask()", hook_path)


def _extract_all_scan_fns(hook_path=_COMMIT_MSG):
    """FIX-445: the scan is a six-function pipeline (mask + engine code +
    verifier + framework check + mention-clause strip + orchestration) —
    extracted together so the dual-engine run exercises the real shipped
    pipeline (DEC-371 ③ added the strip leg)."""
    return "\n".join(
        _extract_fn(p, n, hook_path) for p, n in (
            (_MASK_FN_RE, "json_region_mask()"),
            (_ENGINE_FN_RE, "_fix445_engine_code()"),
            (_VERIFY_FN_RE, "_fix445_verify()"),
            (_FRAME_FN_RE, "endorsement_frame_check()"),
            (_STRIP_FN_RE, "strip_mention_clauses()"),
            (_FAB_FN_RE, "has_unnegated_fabrication_terms()"),
        ))


def _run_scan(evd_text, repo_posix=None, task_id=""):
    """Execute the EXTRACTED Step-12 scan pipeline in real bash over an
    evidence-row fragment fed via a quoted heredoc (dual-engine
    discipline).  repo_posix: the repo root the corpus/artifact engine
    resolves against (defaults to this repo for live-artifact cases;
    tests pass a fixture repo for self-contained cases).  Returns
    True=BLOCK / False=PASS; raises on any unexpected output."""
    if _BASH is None:
        raise AssertionError("no functional bash for the scan parity run")
    fns = _extract_all_scan_fns()
    script = (
        "REPO_ROOT={0!r}\n"
        "{1}\n"
        "EVD_TEXT=$(cat <<'FIX445_EVD_EOF'\n"
        "{2}\n"
        "FIX445_EVD_EOF\n"
        ")\n"
        'if has_unnegated_fabrication_terms "$EVD_TEXT" "{3}"; '
        "then echo BLOCK; else echo PASS; fi\n"
    ).format(repo_posix if repo_posix else
             str(_REPO_ROOT).replace("\\", "/"),
             fns, evd_text, task_id)
    proc = subprocess.run(
        [_BASH, "-s"], input=script.encode("utf-8"),
        capture_output=True, timeout=60, check=False)
    out = proc.stdout.decode("utf-8", "replace").strip()
    if out not in ("BLOCK", "PASS"):
        raise AssertionError(
            "FIX-445 scan run failed: rc={0} stdout={1!r} stderr={2!r}".format(
                proc.returncode, proc.stdout, proc.stderr[:400]))
    return out == "BLOCK"


_SYNTH_RECORDS = [
    {"id": "#1 synth replay (defect proof)", "command": "bash synth.sh",
     "utc_start": "2026-10-11T12:27:10.2692827Z",
     "utc_end": "2026-10-11T12:27:10.7367672Z",
     "literal": "OLD_PATTERN='x｜编造｜幻觉'\ncheck \"我编造了测试结果\""
     "\ncheck \"本次幻觉结果已通过\"",
     "result": "3 compliant phrases BLOCK; 2 true positives BLOCK."},
    {"id": "R3-synth-adversarial", "command": "bash adv.sh",
     "utc_start": "2026-10-11T12:40:21.5532478Z",
     "utc_end": "2026-10-11T12:40:23.3957955Z",
     "observed": "PASS｜double-neg(不允许不编造) ; BLOCK｜韩国编造了数据"},
    {"id": "R5-synth-attribution", "command": "bash attr.sh",
     "utc_start": "2026-10-11T12:42:40.537239Z",
     "utc_end": "2026-10-11T12:42:40.7159085Z",
     "observed": "BARE count=4 (citation 编造｜幻觉 pair + check-quoted "
     "我编造了测试结果 / 本次幻觉结果已通过)"},
    {"id": "R6-synth-risk", "command": "bash risk.sh",
     "utc_start": "2026-10-11T12:00:00.0000000Z",
     "utc_end": "2026-10-11T12:00:01.0000000Z",
     "observed": "复测结论：我编造了测试结果"},
]


def _negation_scan_fixture_repo():
    """Self-contained artifact corpus for source-verification cases: a
    temp repo with .governance/incidents/FIX-445-synth-records.json
    holding _SYNTH_RECORDS (real machine-record shapes).  Rows built via
    _synth_row() embed the SAME dicts through json.dumps, so the row-side
    and artifact-side JSON escaping can never drift.  Returns
    (repo_posix, td)."""
    td = tempfile.TemporaryDirectory(prefix="fix445-synth-")
    repo = Path(td.name) / "repo"
    (repo / ".governance" / "incidents").mkdir(parents=True)
    (repo / ".governance" / "incidents" /
     "FIX-445-synth-records.json").write_text(
        json.dumps(_SYNTH_RECORDS, ensure_ascii=False, indent=1),
        encoding="utf-8")
    return str(repo).replace("\\", "/"), td


def _synth_row(record):
    """Wrap a record dict as an evidence-row fragment carrying it as the
    JSON 事实依据 record plus a refs mention of the synthetic artifact
    (deterministic corpus binding)."""
    return ('| EVD-9600 | FIX-445 | synth | 用户影响：无。目标对齐：来源'
            '以记录为证。 事实依据：' +
            json.dumps(record, ensure_ascii=False) +
            ' refs: .governance/incidents/FIX-445-synth-records.json | '
            'dev | 2026-10-11 | G11 | ok |')


class FabricationNegationScanTests(unittest.TestCase):
    """FIX-444 — Step 12's fabrication terms are judged per OCCURRENCE:
    a negation/prohibition directly in front of 编造/幻觉 is a compliant
    safety statement and must PASS; affirmative, mixed, and unknown
    contexts must still BLOCK (fail-closed).  The pre-FIX-444 whole-line
    grep blocked EVD-1450-style rows like "不编造时戳" (replayed in the
    raw FIX-444 evidence log)."""

    def test_step12_binds_negation_scan_and_keeps_original_patterns(self):
        source = _COMMIT_MSG.read_text(encoding="utf-8")
        # the negation-aware scan is wired into Step 12's block condition…
        self.assertIn(
            'has_unnegated_fabrication_terms "$TASK_EVD_LINES"', source)
        # …and the original speculation patterns stay VERBATIM (their
        # semantics are untouched — no negation handling for them):
        self.assertIn(
            'grep -Eq "我[[:space:]]*(假设|猜测|推测|估计)'
            '|(大概|应该|可能)(已经|是|可以|完成|存在)"', source)
        # the old context-free fabrication tail is gone from that grep:
        self.assertNotIn("(大概|应该|可能)(已经|是|可以|完成|存在)|编造|幻觉",
                         source)

    def test_negated_safety_statements_pass(self):
        # the real EVD-1450-style phrases plus the standard prohibition
        # spellings — all compliant safety statements, none may block.
        rows = [
            "| EVD-1450 | 2026-10-11 | FIX-444 | 事实依据: 实测预算输出落盘"
            "（不编造harness真实预算）| 影响分析 | — |",
            "时间戳取自命令回显，不编造时戳。",
            "拒绝产生幻觉的全自动声明",
            "未编造任何数据；全量输出见 raw log。",
            "毫无编造，全程命令可复算。",
            # negated disjunction (EVD-1440..1445 shape): 不 scopes over
            # the 或-coordination — "neither adds scans NOR fabricates".
            "目标对齐：补齐已发现的argv留痕缺口，不追加扫描或编造验收；记录=C1",
        ]
        for row in rows:
            with self.subTest(row=row):
                self.assertFalse(_run_scan(row))

    def test_quoted_affirmative_claim_still_blocks(self):
        # the reference classes are shape-narrow: an affirmative claim in
        # quotes (not stacked, not check/verdict/pattern forms) blocks.
        self.assertTrue(_run_scan("结论“我编造了结果”已入账"))

    def test_affirmative_and_mixed_occurrences_still_block(self):
        # a negation token on the line must NOT whitelist the line: the
        # bare affirmative occurrence still blocks (mixed-sentence rule).
        rows = [
            "我编造了测试结果",                                   # affirmative
            "不编造；我编造了测试结果",                           # mixed
            "不产生幻觉但这次幻觉结果已通过",                     # mixed
            "本次幻觉结果已通过",                                 # affirmative
            "禁止编造；本次编造了数据",                           # mixed
        ]
        for row in rows:
            with self.subTest(row=row):
                self.assertTrue(_run_scan(row))

    def test_reference_marker_attacks_block(self):
        # FIX-444 R1 V3 escape set + boundary variants: a marker/call form
        # in PROSE must never clear a closure affirmative; single-key or
        # unbacked record wraps grant nothing (FIX-445: no artifact
        # identity -> unverified -> the spans stay and BLOCK).
        rows = [
            "事实依据: PASS｜我编造了测试结果; 后续复测通过",
            "BLOCK｜我编造了测试结果",
            "check-quoted 我编造了测试结果; 后续复测通过",
            "我要求你“不允许不编造”并把数据当真实结果",
            '事实依据: check "我编造了测试结果"',
            '引用：check "我编造了测试结果" 但当真实结果',
            'check "我编造了测试结果',          # missing close quote
            'check "fixture" 我编造了结果',     # wrapped second occurrence
            "不编造时戳\nPASS｜我编造了测试结果",  # newline-wrapped mixed
        ]
        for row in rows:
            with self.subTest(row=row):
                self.assertTrue(_run_scan(row))

    def test_wrap_provenance_attacks_block(self):
        # FIX-444 R2 V3N escape set (n1/n7/n8) + key-spelling variants:
        # exemptions require IDENTITY against an in-repo artifact record —
        # a single-key wrap, even RENAMED to literal/raw/observed/result,
        # has no matching record; the prose finding-marker gate requires
        # a reference-predicate tail, so ENDORSEMENT tails reject.
        rows = [
            '事实依据: {"result":"PASS｜我编造了测试结果;"}',       # n1
            '事实依据: {"r":"check-quoted 我编造了; x"}',           # n8
            "事实依据: 我发现“不允许不编造”是要求必须遵守并当真",     # n7
            '事实依据: {"literal":"PASS｜我编造了测试结果;"}',  # renamed key
            '事实依据: {"raw":"check \\"我编造了测试结果\\""}',   # renamed key
            '事实依据: {"observed":"我编造了测试结果"}',         # renamed key
            "我们引用“不允许不编造”是生产中必须遵守的要求",       # endorse var
            '事实依据: {"id":"x","command":"y","observed":"我编造了测试结果"}',
        ]
        for row in rows:
            with self.subTest(row=row):
                self.assertTrue(_run_scan(row))

    def test_finding_marker_references_pass(self):
        # EVD-1472..1477 family: a quoted stacked-negation finding behind
        # a marker + closed reference-predicate tail is a compliant
        # reference (prose layer, no artifact dependency).
        rows = [
            "R0引用建议不是安全风险豁免，双否定“不允许不编造”已实证escape，"
            "必须同票真实修拒",
            'R0 发现“不允许不编造”为边界',
        ]
        for row in rows:
            with self.subTest(row=row[:40]):
                self.assertFalse(_run_scan(row))

    def test_mask_failure_blocks_fail_closed(self):
        # FIX-444 R2 B1 fault-injection finding (reviewer C6): with the
        # mask dependency unavailable, the OLD pipeline flipped a bare
        # affirmative to PASS (FAILOPEN).  The shipped helper must
        # propagate BLOCK when its tools cannot run — verified
        # behaviorally by stripping PATH so awk/python are unresolvable
        # (printf/test/local are bash builtins; no system tool is
        # uninstalled).  FIX-445: the whole five-function pipeline is
        # inlined so the guard exercised is the shipped one.
        if _BASH is None:
            raise AssertionError("no functional bash for the fail-closed run")
        fns = _extract_all_scan_fns()
        script = (
            "PATH=/no-such-dir-fix444fc\n"
            "{0}\n"
            "if has_unnegated_fabrication_terms \"我编造了测试结果，未复测\"; "
            "then echo BLOCK; else echo PASS; fi\n"
            "if has_unnegated_fabrication_terms \"不编造时戳。\"; "
            "then echo BLOCK2; else echo PASS2; fi\n"
        ).format(fns)
        proc = subprocess.run(
            [_BASH, "-s"], input=script.encode("utf-8"),
            capture_output=True, timeout=30, check=False)
        out = proc.stdout.decode("utf-8", "replace").split()
        self.assertEqual(
            ["BLOCK", "BLOCK2"], out,
            "tool failure must propagate BLOCK, got rc={0} stdout={1!r} "
            "stderr={2!r}".format(
                proc.returncode, proc.stdout, proc.stderr[:400]))

    def test_check_reference_mixed_still_blocks(self):
        # the reference context only covers the quoted span: a prose
        # affirmative outside the closing quote still blocks.
        self.assertTrue(_run_scan('check "fixture"；我编造了结果'))

    def test_double_negation_does_not_launder(self):
        # Stacked negation forces the bare token (BLOCK, fail-closed);
        # single negation keeps passing; curly quotes alone grant NOTHING
        # without a marker + closed predicate tail.
        for row in ("不允许不编造", "决不禁止编造", "“不允许不编造”"):
            with self.subTest(row=row):
                self.assertTrue(_run_scan(row))
        self.assertFalse(_run_scan("不再编造"))  # single + filler 再


class EndorsementFrameworkTests(unittest.TestCase):
    """FIX-445 R3 §3: endorsement frameworks (把/将 × 当作/当成/视为/作为
    × value-tails + 当真) BLOCK unless the clause-bounded prefix window
    is a single-layer negation over the dual closed tables (full-window
    consumption, count==1, <=16 chars, no cross-clause borrowing)."""

    def test_endorsement_shapes_block(self):
        rows = [
            "发现“不允许不编造”为边界；请照此要求必须遵守并当真执行",  # P1
            "双否定“不允许不编造”已实证。我要求把结果当作真实数据",    # P2
            "双否定“不允许不编造”已实证。首先我们必须在后续所有流程与"
            "复测环节里，将该结论视为事实",                            # long
            "事实依据: 非常应当把该结果当作真实数据",   # residue 常
            "事实依据: 未来将把该结论视为事实",         # residue 来
            "事实依据: 无论复核与否，把该结果当作真实数据",  # residue 论
            "事实依据: 不是不把该结论当作真实数据",     # count 2
            "事实依据: 并非不将结果视为事实",           # count 2
            "事实依据: 不许忽略复核，把该结果当作真实数据",  # cross-clause
            "事实依据: 我们已经仔细地完整地重新地不把该结论当作真实数据",
        ]
        for row in rows:
            with self.subTest(row=row):
                self.assertTrue(_run_scan(row))

    def test_single_layer_negated_frameworks_pass(self):
        rows = [
            "事实依据: 不允许把该结果当作真实数据",
            "事实依据: 不把估计批戳当成真实戳",
            "事实依据: 未将该结果当作真实数据",
        ]
        for row in rows:
            with self.subTest(row=row):
                self.assertFalse(_run_scan(row))


class SourceVerificationTests(unittest.TestCase):
    """FIX-445: citation spans are exempt only per-instance when the
    carrying record field is source-verified (identity + whole-field
    equality) against an in-repo artifact record.  Self-contained
    fixture artifacts; the C6 typed-span rule strips ONLY the real
    technical-citation payload spans — never a whole field value."""

    def setUp(self):
        self._repo, self._td = _negation_scan_fixture_repo()
        self.addCleanup(self._td.cleanup)
        self.task = "FIX-445"

    def _rec(self, idx):
        return json.loads(json.dumps(_SYNTH_RECORDS[idx],
                                     ensure_ascii=False))

    def test_verified_literal_and_verdict_spans_pass(self):
        # 1463-form (check \"…\" + pair in literal) and 1481-form (verdict
        # spans in observed) with exact identity + whole-value equality.
        for idx in (0, 1):
            with self.subTest(idx=idx):
                self.assertFalse(_run_scan(
                    _synth_row(self._rec(idx)),
                    repo_posix=self._repo, task_id=self.task))

    def test_c6_typed_span_only_strips_citation_payloads(self):
        # 1483-form: pair + check-quoted attribution spans inside an
        # observed value that whole-equals the artifact's observed —
        # ONLY those typed spans go; the rest of the value is scanned.
        self.assertFalse(_run_scan(
            _synth_row(self._rec(2)),
            repo_posix=self._repo, task_id=self.task))

    def test_c6_full_credential_risk_without_span_still_blocks(self):
        # WHOLE-FIELD ROUTE CANCELLED (trigger-point finding): even with
        # identity + whole-value equality, an observed value whose risk
        # content carries NO closed-type span is never stripped.
        self.assertTrue(_run_scan(
            _synth_row(self._rec(3)),
            repo_posix=self._repo, task_id=self.task))

    def test_credential_breakers_block(self):
        base = self._rec(0)
        rows = [
            # F1: cropped identity, no artifact match
            _synth_row({"id": "#1", "command": "x",
                        "literal": 'check "我编造了测试结果"'}),
            # F2: three-key wrap, unrecognized id
            _synth_row({"id": "rec-2", "env": "e", "workdir": "w",
                        "literal": "OLD_PATTERN=x｜编造｜幻觉"}),
            # F3: verdict span in observed without identity
            _synth_row({"id": "r3", "start": "t", "end": "t",
                        "observed": "PASS｜我编造了测试结果;"}),
        ]
        # utc7: 7th fraction digit differs -> instants unequal
        utc7 = self._rec(0)
        utc7["utc_start"] = "2026-10-11T12:27:10.2692828Z"
        utc7["literal"] = 'check "我编造了测试结果"'
        rows.append(_synth_row(utc7))
        # alpha: right identity, span in output_as_captured BUT the
        # field value has extra bytes appended -> whole-value fails
        alpha = self._rec(0)
        alpha["output_as_captured"] = (
            'check "我编造了测试结果" ; 复测通过')
        alpha["result"] = "复测通过"
        del alpha["literal"]
        rows.append(_synth_row(alpha))
        # beta: verdict span moved into result (never an allowed carrier)
        beta = self._rec(1)
        beta["result"] = "BLOCK｜韩国编造了数据"
        del beta["observed"]
        rows.append(_synth_row(beta))
        # field-move: span in affected (never an allowed carrier)
        move = self._rec(0)
        move["affected"] = 'check "我编造了测试结果"'
        del move["literal"]
        rows.append(_synth_row(move))
        # prefix: span embedded with extra prefix bytes in the field
        prefix = self._rec(0)
        prefix["literal"] = '前置字节check "我编造了测试结果"'
        rows.append(_synth_row(prefix))
        # legal payload + added bare affirmative elsewhere in the value:
        # whole-value equality FAILS -> nothing strips -> BLOCK.
        extra = self._rec(2)
        extra["observed"] += " 我编造了额外数据"
        rows.append(_synth_row(extra))
        for row in rows:
            with self.subTest(row=row[:90]):
                self.assertTrue(_run_scan(
                    row, repo_posix=self._repo, task_id=self.task))

    def test_same_literal_second_instance_unverified_blocks(self):
        # per-instance rule: a verified literal span does not clear the
        # SAME bytes appearing again in prose (no credential there).
        row = (_synth_row(self._rec(0)) +
               ' 另一处同字面：check \\"我编造了测试结果\\" 照检 |')
        self.assertTrue(_run_scan(
            row, repo_posix=self._repo, task_id=self.task))


class R5ClosedTableTests(unittest.TestCase):
    """FIX-445 R5 (DEC-337): T-2′ whitelist units (CJK U+4E00..U+9FFF +
    ASCII alnum, symbols EMPTY) + Guard G (7 endorsement operators
    whole-span reject) + integral candidate rejection + overflow-no-
    partial.  All cases run the real extracted pipeline against the
    fixture artifact repo; C6 spans live in observed under full-value
    credential."""

    def setUp(self):
        self._repo, self._td = _negation_scan_fixture_repo()
        self.addCleanup(self._td.cleanup)
        self.task = "FIX-445"

    def _c6row(self, observed):
        rec = {"id": "R5-synth-attribution", "command": "bash attr.sh",
               "utc_start": "2026-10-11T12:42:40.537239Z",
               "utc_end": "2026-10-11T12:42:40.7159085Z",
               "observed": observed}
        return ('| EVD-9601 | FIX-445 | r5 | 用户影响：无。目标对齐：来源以'
                '记录为证。 事实依据：' +
                json.dumps(rec, ensure_ascii=False) +
                ' refs: .governance/incidents/FIX-445-synth-records.json | '
                'dev | 2026-10-11 | G11 | ok |')

    def _forge_case(self, observed):
        """Forged-artifact premise (R5 N-1 chain level): the artifact
        itself carries the endorsement-shaped observed value and the row
        cites it with FULL identity + whole-value equality — the typed
        channel must still reject via Guard G / whitelist grammar."""
        td = tempfile.TemporaryDirectory(prefix="fix445-r5forge-")
        repo = Path(td.name) / "repo"
        inc = repo / ".governance" / "incidents"
        inc.mkdir(parents=True)
        rec = {"id": "R5-forge-case", "command": "bash forge.sh",
               "utc_start": "2026-10-11T13:00:00.0000000Z",
               "utc_end": "2026-10-11T13:00:01.0000000Z",
               "observed": observed}
        (inc / "FIX-445-forge-records.json").write_text(
            json.dumps([rec], ensure_ascii=False, indent=1),
            encoding="utf-8")
        self.addCleanup(td.cleanup)
        row = ('| EVD-9603 | FIX-445 | r5forge | 用户影响：无。目标对齐：'
               '来源以记录为证。 事实依据：' +
               json.dumps(rec, ensure_ascii=False) +
               ' refs: .governance/incidents/FIX-445-forge-records.json | '
               'dev | 2026-10-11 | G11 | ok |')
        return row, str(repo).replace("\\", "/")

    def _forge_blocks(self, observed):
        row, repo = self._forge_case(observed)
        self.assertTrue(_run_scan(row, repo_posix=repo, task_id=self.task))

    def test_guard_no_separator_juxtaposition_blocks(self):
        # Guard G core: CJK juxtaposition is INSIDE the whitelist unit,
        # the 7-operator closed set must reject the whole span even
        # under a fully-matching forged artifact (DEC-336 core).
        for observed in (
            "check-quoted 我编造了测试结果当真",
            "check-quoted 我编造了测试结果当作真实凭据补充",
            "check-quoted 我编造了测试结果将结论定案",
            "check-quoted 我编造了测试结果把结论固化",
            "check-quoted 我编造了测试结果视为定案 / 补充二单元",
            "check-quoted 我编造了测试结果当成事实 / 补充二单元",
            "check-quoted 我编造了测试结果作为依据纳入",
        ):
            with self.subTest(observed=observed[14:34]):
                self._forge_blocks(observed)

    def test_separator_family_blocks(self):
        # any non-whitelisted char terminates the unit; the tail stays
        # visible and M5/term scan see the endorsement (forged artifact
        # premise — R4-A five variants + full-width space + CRLF).
        for tail in (
            "，请当真执行", "、请当真执行", "！请当真执行", "？请当真执行",
            "\t然后当真执行", "　然后当真执行",
            "\\n然后当真执行", "\\r\\n然后当真执行",
        ):
            with self.subTest(tail=tail[:8]):
                self._forge_blocks("check-quoted 我编造了测试结果" + tail)

    def test_unknown_unicode_connector_blocks(self):
        # outside the whitelist (CJK Ext-B U+20000) terminates; the CJK
        # tail after it forces integral rejection (no leading-truncate).
        self._forge_blocks("check-quoted 我编造了测试结果𠀀当真执行")

    def test_control_char_inside_candidate_blocks(self):
        # integral rejection — no leading-segment exemption that would
        # swallow the tail (R5 :17).
        self._forge_blocks("check-quoted 我编造了\u0007测试结果当真")

    def test_fifth_unit_overflow_stays_whole(self):
        # >4 units: syntax mismatch — the overflow unit must NOT be
        # swallowed by a partial span (no truncation laundering).
        self._forge_blocks(
            "check-quoted 我编造了测试结果 / 第二单元数据 / 第三单元结果 / "
            "第四单元通过 / 我编造了溢出单元")

    def test_unit_length_overflow_stays_whole(self):
        # unit >60 chars: grammar mismatch — whole candidate rejected,
        # nothing stripped; the bare term stays in the residual.
        self._forge_blocks("check-quoted " + "长" * 61 + "当真")

    def test_legit_c6_payload_still_passes(self):
        # the real R5 shape: pair + two whitelisted units joined by
        # ' / ', no guard token — PASS.
        self.assertFalse(_run_scan(
            self._c6row("BARE count=4 (citation 编造｜幻觉 pair + "
                        "check-quoted 我编造了测试结果 / 本次幻觉结果已通过)"),
            repo_posix=self._repo, task_id=self.task))

    def test_last_span_in_field_terminates(self):
        # root cause ② regression: the LAST verdict span in an observed
        # value must not overrun the closing quote into row prose.
        rec = {"id": "R3-synth-adversarial", "command": "bash adv.sh",
               "utc_start": "2026-10-11T12:40:21.5532478Z",
               "utc_end": "2026-10-11T12:40:23.3957955Z",
               "observed": "PASS｜double-neg(不允许不编造) ; BLOCK｜韩国编造了数据"}
        row = ('| EVD-9602 | FIX-445 | r5 | 用户影响：无。目标对齐：来源以'
               '记录为证。 事实依据：' +
               json.dumps(rec, ensure_ascii=False) +
               ' refs: .governance/incidents/FIX-445-synth-records.json | '
               'dev | 2026-10-11 | G11 | ok |')
        self.assertFalse(_run_scan(
            row, repo_posix=self._repo, task_id=self.task))

    def test_directory_corpus_entry_is_structural_skip(self):
        # root cause ① regression: a DIRECTORY matching the task glob is
        # a structural non-record (skip, not a read fault) — a verified
        # good row must still PASS with such entries present.
        td = tempfile.TemporaryDirectory(prefix="fix445-dircorp-")
        repo = Path(td.name) / "repo"
        inc = repo / ".governance" / "incidents"
        inc.mkdir(parents=True)
        (inc / "FIX-445-phase-evidence").mkdir()  # directory in the glob
        records = [r for r in _SYNTH_RECORDS
                   if r["id"] == "R5-synth-attribution"]
        (inc / "FIX-445-synth-records.json").write_text(
            json.dumps(records, ensure_ascii=False, indent=1),
            encoding="utf-8")
        self.addCleanup(td.cleanup)
        row = self._c6row(
            "BARE count=4 (citation 编造｜幻觉 pair + check-quoted "
            "我编造了测试结果 / 本次幻觉结果已通过)")
        self.assertFalse(_run_scan(
            row, repo_posix=str(repo).replace("\\", "/"),
            task_id=self.task))

    # ── DEC-371 B1 closed-table delta red tests (FIX-444/445 R1) ─────────
    # Each newly admitted shape carries a still-BLOCKS neighbour: the
    # extensions must exempt ONLY the three evidenced compliant forms,
    # never widen into real fabrication disclosures.

    def test_dec371_disjunction_midclass_clean_and_neighbours_block(self):
        """① closed mid-class disjunction (追加扫描|新增扫描|预算|时间|
        权限|异常隐藏 + optional 事后/先/预先/再/反复/PASS tail): the
        four evidenced false-BLOCK forms pass; a mid-class OUTSIDE the
        closed set still blocks (the negation did not govern 编造).
        Byte-class note: the mid-class is an explicit alternation, not a
        [^punct] class — sed runs byte-mode here and a negated multibyte
        class over-excludes (EVD-1610's 异常 byte BC collides with the
        。-exclusion set), so the closed list is also the
        locale-correct form."""
        for row in (
            "当前健康检查无预算或PASS编造。",       # EVD-1536 live form
            "复测结论：无时间或编造，全部为真实回显。",
            "拒绝异常隐藏或事后编造原命令，保持未通过产品。",  # EVD-1610
            "补齐缺口，不追加扫描或编造验收；记录=C1",
        ):
            self.assertFalse(_run_scan(row), row)
        # neighbour: 成本 is outside the closed mid-class -> 编造 is a
        # live fabrication claim (unnegated) -> BLOCK.
        self.assertTrue(_run_scan("状态：无成本或编造，直接入账"))

    def test_dec371_ascii_prefix_and_dangzhen_tail_clean_and_block(self):
        """② closed ASCII technical-token class + ③ 当真 object-tail
        alignment: the EVD-1587 mention passes; a pure-ASCII prefix
        (cnt==0, no negation) and a real 把编造X当真 attack both stay
        blocked."""
        self.assertFalse(
            _run_scan("M5框架语义：已知no-separator当真不能默当获准。"))
        # neighbour A: ASCII tokens alone never exempt (cnt must be 1).
        self.assertTrue(
            _run_scan("场景：known-sep当真视为真实数据"))
        # neighbour B: the tail requirement must not swallow real attacks.
        self.assertTrue(_run_scan("把编造结果当真提交"))

    def test_dec372_analytic_verb_tail_family_clean_and_block(self):
        """DEC-372 (R7.5): the closed analytic-verb-tail family
        (当真对齐/当真语义/当真分支 — implementation-receipt prose;
        regression sample = the EVD-2157 receipt sentence itself) disarms
        the 当真 trigger; each tail carries a laundering neighbour that
        must still BLOCK via the residual grep (the family never strips
        编造/幻觉 claims — it only disarms the framework arm)."""
        # clean: the three tails + the live receipt sentence shape.
        self.assertFalse(
            _run_scan("B1 闭表提及标记形独立函数 strip_mention_clauses "
                      "三分支当真对齐；tail=object/imperative/modal。"))
        self.assertFalse(_run_scan("回执：当真语义与执行尾的 disarm 分支表"))
        self.assertFalse(_run_scan("白盒说明：当真分支枚举显式无通配"))
        # neighbour 1 (对齐): the fabrication claim is NOT part of the
        # analytic mention — residual grep must catch it.
        self.assertTrue(_run_scan("把编造结果对齐后提交"))
        # neighbour 2 (语义): endorsement laundering in the same clause.
        self.assertTrue(_run_scan("将背书语义混入回执并编造结果"))
        # neighbour 3 (分支): an unbacked claim next to the family word.
        self.assertTrue(_run_scan("走当真分支的编造结果直接入账"))

    def test_dec371_mention_marker_form_clean_and_clause_bounded(self):
        """③ closed mention-marker form (载荷含/算子枚举/闭表内/闭集/
        技术提及): the EVD-1588 operator-enumeration mention passes; the
        exemption is clause-bounded — a fabrication claim AFTER the
        clause terminator stays blocked."""
        self.assertFalse(
            _run_scan("闭表说明：载荷含把将当作当成视为作为当真任token"
                      "整span拒免。"))
        self.assertFalse(
            _run_scan("算子枚举：把/将/当作/视为/作为/当真各token整span"
                      "拒免并计残文。"))
        # neighbour: mention head in one clause cannot launder a claim in
        # the NEXT clause.
        self.assertTrue(_run_scan("载荷含编造。我编造了测试结果"))
        # neighbour: a claim BEFORE the marker is never touched by it.
        self.assertTrue(_run_scan("我编造了载荷含测试结果"))


class ParserPathFaultTests(unittest.TestCase):
    """FIX-445 C-1 five rejections render malformed regions as prose
    (zero exemptions); artifact content faults reduce the corpus; tool
    and IO faults BLOCK the line fail-closed."""

    def _repo_with_artifact(self, artifact_text, name="FIX-445-fault.json"):
        td = tempfile.TemporaryDirectory(prefix="fix445-fault-")
        repo = Path(td.name) / "repo"
        (repo / ".governance" / "incidents").mkdir(parents=True)
        (repo / ".governance" / "incidents" / name).write_text(
            artifact_text, encoding="utf-8")
        self.addCleanup(td.cleanup)
        return str(repo).replace("\\", "/")

    def test_row_side_malformed_records_block(self):
        rows = [
            # duplicate keys -> whole region malformed -> prose
            '事实依据: {"id":"a","literal":"check \\"我编造了测试结果\\"",'
            '"literal":"x"}',
            # NaN constant -> malformed
            '事实依据: {"id":"a","utc_start":NaN,"literal":"check \\"我编造'
            '了测试结果\\""}',
            # partial consumption (trailing bytes) -> malformed
            '事实依据: {"id":"a","literal":"check \\"我编造了测试结果\\""} '
            'trailing-junk',
            # nested rescue prohibition: the span sits in a NESTED object's
            # value — no top-level carrying field -> unverified -> BLOCK
            '事实依据: {"outer":{"id":"a","literal":"check \\"我编造了测试'
            '结果\\""},"result":"x"}',
        ]
        for row in rows:
            with self.subTest(row=row[:60]):
                self.assertTrue(_run_scan(row))

    def test_artifact_content_faults_reduce_corpus(self):
        repo = self._repo_with_artifact(
            '[{"id":"a","id":"a","literal":"check \\"我编造了测试结果\\""}]')
        row = ('事实依据: {"id":"a","literal":"check \\"我编造了测试结果'
               '\\""} refs: .governance/incidents/FIX-445-fault.json')
        self.assertTrue(_run_scan(row, repo_posix=repo, task_id="FIX-445"))

    def test_unreadable_corpus_entry_blocks_fail_closed(self):
        td = tempfile.TemporaryDirectory(prefix="fix445-dird-")
        repo = Path(td.name) / "repo"
        inc = repo / ".governance" / "incidents"
        inc.mkdir(parents=True)
        # non-UTF-8 corpus file: a reader fault (not malformed JSON) —
        # must BLOCK fail-closed, never silently reduce the corpus.
        (inc / "FIX-445-dird-entry").write_bytes(b"\x80\x81\xfe garbage")
        self.addCleanup(td.cleanup)
        repo_posix = str(repo).replace("\\", "/")
        # tool fault must BLOCK even when the row itself carries no risk
        # (the record region forces the corpus/engine leg to run) —
        # fail-closed contract.
        row = ('| EVD-9601 | FIX-445 | fault | 事实依据：{"id":"x",'
               '"command":"y"} refs: .governance/incidents/ | dev | '
               '2026-10-11 | G11 | ok |')
        self.assertTrue(
            _run_scan(row, repo_posix=repo_posix, task_id="FIX-445"))


_EVD_FN_RE = re.compile(r"(?ms)^task_evidence_lines\(\) \{.*?^\}")
_SPECULATION_GREP_RE = re.compile(r'grep -Eq "(我[^"]*)"')


def _extract_evd_fn(hook_path=_COMMIT_MSG):
    text = hook_path.read_text(encoding="utf-8")
    m = _EVD_FN_RE.search(text)
    if not m:
        raise AssertionError(
            "task_evidence_lines() not found in {0}".format(hook_path))
    return m.group(0)


def _extract_speculation_pattern(hook_path=_COMMIT_MSG):
    """The Step-12 speculation grep pattern, EXTRACTED from the shipped
    hook source (binding — tests never copy the regex)."""
    text = hook_path.read_text(encoding="utf-8")
    m = _SPECULATION_GREP_RE.search(text)
    if not m:
        raise AssertionError(
            "Step-12 speculation grep not found in {0}".format(hook_path))
    pattern = m.group(1)
    for anchor in ("假设", "大概", "可能"):
        if anchor not in pattern:
            raise AssertionError(
                "extracted speculation pattern lost an original branch: "
                "{0!r}".format(pattern))
    return pattern


def _step12_replay(repo_posix, task_ids, timeout=300):
    """Run the REAL Step-12 execution path in real bash over a repo root:
    the shipped task_evidence_lines awk extractor plus BOTH Step-12
    branches (the extracted speculation grep and the full extracted
    FIX-445 scan pipeline).  Per TASK, not per row: the hook itself
    feeds all extracted lines to the scan in one call, and batching
    keeps the engine spawn count at one per task (per-row looping made
    the live 4-task replay exceed 180s).  Returns ({task: row_count},
    [hit_lines])."""
    if _BASH is None:
        raise AssertionError("no functional bash for the Step-12 replay")
    script = (
        "REPO_ROOT={0!r}\n"
        "{1}\n"
        "{2}\n"
        "SPEC={3!r}\n"
        "for TID in {4}; do\n"
        '  LINES=$(task_evidence_lines "$TID")\n'
        '  CNT=$(printf \'%s\\n\' "$LINES" | grep -c "^| EVD-")\n'
        '  echo "SEEN|$TID|$CNT"\n'
        '  if printf \'%s\\n\' "$LINES" | grep -Eq "$SPEC"; then '
        'echo "SPEC_HIT|$TID"; fi\n'
        '  if has_unnegated_fabrication_terms "$LINES" "$TID"; then '
        'echo "FAB_HIT|$TID"; fi\n'
        "done\n"
    ).format(
        repo_posix, _extract_evd_fn(), _extract_all_scan_fns(),
        _extract_speculation_pattern(),
        " ".join(task_ids))
    proc = subprocess.run(
        [_BASH, "-s"], input=script.encode("utf-8"),
        capture_output=True, timeout=timeout, check=False)
    out = proc.stdout.decode("utf-8", "replace")
    if proc.returncode != 0 or not out:
        raise AssertionError(
            "Step-12 replay failed: rc={0} stdout={1!r} stderr={2!r}".format(
                proc.returncode, proc.stdout, proc.stderr[:400]))
    seen, hits = {}, []
    for line in out.splitlines():
        if line.startswith("SEEN|"):
            parts = line.split("|")
            task = parts[1]
            count = int(parts[2]) if len(parts) > 2 else 1
            seen[task] = seen.get(task, 0) + count
        elif line.startswith("SPEC_HIT|") or line.startswith("FAB_HIT|"):
            hits.append(line)
    return seen, hits


class SyntheticEvdStep12ReplayTests(unittest.TestCase):
    """FIX-445 universal regression: a SELF-CONTAINED evidence-log fixture
    (temp repo + its own incidents artifact, no dependency on this
    workspace's gitignored .governance data) drives the REAL Step-12
    path — compliant rows (prose negations/disjunction, marker-qualified
    finding names, ARTIFACT-VERIFIED citation records incl. the C6
    typed-span form) pass end-to-end while planted attacks (prose
    markers, unbacked wraps, forged identities, endorsement frameworks)
    BLOCK.  Runs in any clean clone; never skipped."""

    GOOD_TASK = "FIX-9404"
    BAD_TASK = "FIX-9405"

    _BAD_ROWS = [
        "| EVD-9101 | FIX-9405 | 攻击1 | 事实依据: PASS｜我编造了测试结果; "
        "后续复测通过 | — | dev | 2026-10-11 | G11 | bad |",
        "| EVD-9102 | FIX-9405 | 攻击2 | 事实依据: BLOCK｜我编造了测试结果 "
        "| — | dev | 2026-10-11 | G11 | bad |",
        "| EVD-9103 | FIX-9405 | 攻击3 | 事实依据: check-quoted 我编造了"
        "测试结果; 后续复测通过 | — | dev | 2026-10-11 | G11 | bad |",
        "| EVD-9104 | FIX-9405 | 攻击4 | 事实依据: 我要求你“不允许不编造”"
        "并把数据当真实结果 | — | dev | 2026-10-11 | G11 | bad |",
        '| EVD-9105 | FIX-9405 | 攻击5 | 事实依据: check "我编造了测试结果" '
        "| — | dev | 2026-10-11 | G11 | bad |",
        "| EVD-9106 | FIX-9405 | 攻击6（R2 n1） | 事实依据: {\"result\":"
        "\"PASS｜我编造了测试结果;\"} | — | dev | 2026-10-11 | G11 | bad |",
        "| EVD-9107 | FIX-9405 | 攻击7（R2 n8） | 事实依据: {\"r\":"
        "\"check-quoted 我编造了; x\"} | — | dev | 2026-10-11 | G11 | bad |",
        "| EVD-9108 | FIX-9405 | 攻击8（R2 n7） | 事实依据: 我发现"
        "“不允许不编造”是要求必须遵守并当真 | — | dev | 2026-10-11 | G11 "
        "| bad |",
        "| EVD-9109 | FIX-9405 | 攻击9（伪造身份） | 事实依据: {\"id\":"
        "\"#1\",\"command\":\"x\",\"literal\":\"check \\\"我编造了测试结果"
        "\\\"\"} | — | dev | 2026-10-11 | G11 | bad |",
        "| EVD-9110 | FIX-9405 | 攻击10（UTC 第 7 位裁剪） | 事实依据: "
        "{\"id\":\"#1 synth replay (defect proof)\",\"command\":\"c\","
        "\"utc_start\":\"2026-10-11T12:27:10.2692828Z\",\"utc_end\":"
        "\"2026-10-11T12:27:10.7367672Z\",\"literal\":\"check \\\"我编造了"
        "测试结果\\\"\"} | — | dev | 2026-10-11 | G11 | bad |",
        "| EVD-9111 | FIX-9405 | 攻击11（背书框架） | 事实依据: 双否定"
        "“不允许不编造”已实证。我要求把结果当作真实数据 | — | dev | "
        "2026-10-11 | G11 | bad |",
        "| EVD-9112 | FIX-9405 | 攻击12（嵌入字） | 事实依据: 非常应当把"
        "该结果当作真实数据 | — | dev | 2026-10-11 | G11 | bad |",
    ]

    def _srow(self, evd, idx):
        return ("| EVD-{0} | FIX-9404 | 已验证引用 | 用户影响：无。目标对齐："
                "来源以记录为证。 事实依据：{1} | .governance/incidents/"
                "FIX-9404-records.json | dev | 2026-10-11 | G11 | ok |"
                ).format(evd, json.dumps(_SYNTH_RECORDS[idx],
                                         ensure_ascii=False))

    def _replay_repo(self, rows):
        """Build a self-contained mini repo over `rows` and run the REAL
        Step-12 path for BOTH fixture tasks. Returns (seen, hits)."""
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        repo = Path(td.name) / "repo"
        gov = repo / ".governance"
        inc = gov / "incidents"
        inc.mkdir(parents=True)
        (inc / "FIX-9404-records.json").write_text(
            json.dumps(_SYNTH_RECORDS, ensure_ascii=False, indent=1),
            encoding="utf-8")
        (gov / "evidence-log.md").write_text(
            "\n".join(rows) + "\n", encoding="utf-8")
        return _step12_replay(
            str(repo).replace("\\", "/"), [self.GOOD_TASK, self.BAD_TASK])

    def test_compliant_rows_pass_and_attacks_block_end_to_end(self):
        # compliant rows: prose negation/disjunction/finding-marker/
        # framework-negation plus the three artifact-verified record
        # forms (literal spans / verdict spans / C6 typed spans) built
        # from the SAME dicts as the artifact (no escaping drift).
        good_rows = [
            "| EVD-9001 | FIX-9404 | 合规否定 | 用户影响：无。目标对齐：时间"
            "戳取自命令回显，不编造时戳。 | — | dev | 2026-10-11 | G11 | ok |",
            "| EVD-9002 | FIX-9404 | 否定析取 | 用户影响：无。目标对齐：补齐"
            "缺口，不追加扫描或编造验收；记录=C1 | — | dev | 2026-10-11 | G11 "
            "| ok |",
            self._srow(9003, 0),
            "| EVD-9004 | FIX-9404 | 发现名引用（EVD-1472 形，标记+谓语尾） | "
            "用户影响：无。目标对齐：双否定“不允许不编造”已实证escape，必须"
            "同票真实修拒 | — | dev | 2026-10-11 | G11 | ok |",
            self._srow(9005, 1),
            self._srow(9006, 2),
            "| EVD-9007 | FIX-9404 | 合规框架否定 | 用户影响：无。目标对齐："
            "不允许把该结果当作真实数据 | — | dev | 2026-10-11 | G11 | ok |",
        ]
        seen, hits = self._replay_repo(good_rows + self._BAD_ROWS)
        self.assertEqual(
            len(good_rows), seen.get(self.GOOD_TASK, 0),
            "compliant fixture rows must all be extracted")
        self.assertEqual(
            len(self._BAD_ROWS), seen.get(self.BAD_TASK, 0),
            "attack fixture rows must all be extracted")
        self.assertEqual(
            [], [h for h in hits if h.endswith(self.GOOD_TASK)],
            "compliant rows must be CLEAN under the real Step-12 path")
        # FIX-445 B2 restoration (DEC-371): the synthetic attack coverage
        # is asserted PER ROW again — each of the 12 planted attack rows
        # must HIT in its own replay (12 bounded spawns, seconds).  The
        # old batch-any weakening (11 escapes undetectable) is gone; the
        # live four-task gate keeps its per-task batching for latency.
        for row in self._BAD_ROWS:
            row_seen, row_hits = self._replay_repo([row])
            self.assertEqual(
                1, row_seen.get(self.BAD_TASK, 0),
                "attack row must be extracted alone: {0!r}".format(
                    row[:60]))
            self.assertEqual(
                ["FAB_HIT|{0}".format(self.BAD_TASK)], row_hits,
                "each planted attack row must HIT on its own under the "
                "real Step-12 path: {0!r}".format(row[:60]))


class RealEvdStep12ReplayTests(unittest.TestCase):
    """FIX-445 delivery receipt: the CURRENT evidence rows of the
    ticket family re-verified through the REAL Step-12 path over the
    live .governance/evidence-log.md (read-only).

    DEC-371 (FIX-444/445 R1): the task list is now DYNAMIC — it reads
    the active (non-completed) P0/P1 rows from the live plan-tracker
    instead of a hardcoded four-task family.  Root cause 甲 of the
    pre-R1 failure (continuous archiving moves closed tasks' EVD rows
    out of the hot file, so a static "none may be zero" list breaks) is
    dissolved: newly in-triaged tasks legitimately have no EVD rows yet,
    so the contract is (a) the dynamic list is non-empty, (b) at least
    one active task has extractable rows (the replay is not broken),
    (c) ZERO fabrication hits across every active task's rows.  The
    universal regression lives in SyntheticEvdStep12ReplayTests; this
    probe runs wherever the input window exists."""

    def _active_task_ids(self):
        tracker = _REPO_ROOT / ".governance" / "plan-tracker.md"
        if not tracker.is_file():
            return []
        ids = []
        for line in tracker.read_text(encoding="utf-8").splitlines():
            m = re.match(
                r"^\|\s*\**P[01]\**\s*\|\s*\**([A-Z]+-\d+)\**\s*\|", line)
            if m and "✅" not in line:
                ids.append(m.group(1))
        return ids

    def test_current_real_rows_all_clean_under_real_step12(self):
        live = _REPO_ROOT / ".governance" / "evidence-log.md"
        if not live.is_file():
            self.skipTest("live .governance/evidence-log.md unavailable")
        tasks = self._active_task_ids()
        self.assertGreaterEqual(
            len(tasks), 1,
            "dynamic active-task list must be non-empty (plan-tracker "
            "unreadable or no active P0/P1 rows?)")
        seen, hits = _step12_replay(
            str(_REPO_ROOT).replace("\\", "/"), tasks)
        self.assertGreaterEqual(
            sum(1 for t in tasks if seen.get(t, 0) >= 1), 1,
            "replay broken: no active task yielded extractable EVD "
            "rows (seen={0!r})".format(seen))
        self.assertEqual(
            [], hits,
            "real Step-12 execution must be CLEAN on all current rows "
            "of the active ticket set (seen={0!r})".format(seen))


class SelfUpgradeNoBypassTests(unittest.TestCase):
    """FIX-444 acceptance ④ (DEC-371 R1): a NORMAL self-upgrade commit —
    the hook's own pin-bump flow, exactly like FIX-458's 0.98.0→0.99.0
    one-line change — must clear the fact gate WITHOUT --no-verify.  The
    gate runs the REAL extracted pipeline over the evidence prose a
    routine upgrade receipt produces (compliant negations, the DEC-371
    admitted forms, no fabrication claims), so the upgrade path has a
    machine-judged non-bypass route.  Anti-neighbour: a receipt that
    LAUNDERS a fabrication claim through upgrade prose still blocks."""

    def test_upgrade_receipt_clears_gate_without_bypass(self):
        receipt = (
            "用户影响：获得=hook pin 随发布版正常自升级；感知=升级提交本身"
            "走完整事实门；体验变化=正常提交无需 --no-verify 应急通道。"
            "目标对齐：pin 头随发布权威单行对齐（上一版到活跃版，版本字面"
            "不进本测试源——static-version-pin 纪律）；健康检查门禁"
            "无预算或PASS编造；载荷含把将当作视为作为当真各token整span"
            "拒免（闭表枚举说明）。"
        )
        self.assertFalse(_run_scan(receipt, task_id="FIX-458"))

    def test_upgrade_receipt_laundering_still_blocks(self):
        launder = (
            "hook pin 自升级说明：载荷含编造。我编造了测试结果并把它当真"
            "视为真实数据提交。"
        )
        self.assertTrue(_run_scan(launder, task_id="FIX-458"))


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
