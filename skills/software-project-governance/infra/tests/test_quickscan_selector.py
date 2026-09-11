"""FEAT-026 Slice-2 tests — quick 选择器 + 四态契约 + shadow 通道（FX-195 §6 L251）。

验收对应（quickscan-evaluation §4.1 / §4.2 / §6 L251 / §9.3 / §2.4）：

1. **S-A/S-B shadow 通道**（§4.1）：选择集 ∪ 排除集 = 70 段无遗漏无重复、每排除段有
   注册表原因代码、C3 四段落表（S-A 机器判定）；quick 与 full 逐段裁决比对（S-B，
   任何不一致 = BLOCKING）。「≥3 会话 / ≥10 commit」累计证明随使用积累——本切片交付
   的是**机制与 harness**，不是累计结论（如实区分）。
2. **四态守卫**（§2.4 硬约束 2 / QR-4）：四态计数必现于汇总行；无计数的汇总行 = 违规；
   NOT_RUN 不得使 N 归零（全部实质段未执行 → ``N=unknown``）。
3. **默认路径字节等价**：不带 ``--quick`` 的输出与现状逐字节一致（对照测试，
   test_summary_only.py 先例）。
4. **FIX-304 消费口径**：注册表守卫 ``ValueError``（重复 CheckID，§4.1 R5 零容忍）
   → 全段 ``UNDETERMINED`` + 回退 full；判别字段是 ``fail_closed``（非
   ``fallback_target``）。
5. **性能**：选择语义 = 复用 FIX-270 product-gate 跳过机制（零段级改动）；墙钟实测
   入档在交付摘要（本文件以机器判定钉住"跳过面恰为 product-gate 声明"这一机制前提）。
6. **TDD**：本文件先于引擎接线落地（红：接线前 dispatch 用例失败），接线后转绿。

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_quickscan_selector.py -v
"""

import ast
import io
import json
import subprocess
import sys
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import quickscan_registry as qr  # noqa: E402
import quickscan_selector as qs  # noqa: E402
import verify_workflow as vw  # noqa: E402

ENGINE = _INFRA_DIR / "verify_workflow.py"
SELECTOR = _INFRA_DIR / "quickscan_selector.py"
SNAPSHOT = _INFRA_DIR / "contract_matrix" / "snapshots.json"

_DASH = "\u2500"
_SKIP_LINE = ("│  [SKIP] product self-check — plugin-package fact source; "
              "host/plugin roots diverge. Run with --product-gates to enable.")


# ── fixtures（真实注册表 + 合成引擎输出文本，非打桩）────────────────────────
def _section(check_id, issue_lines=(), skipped=False):
    out = [f"┌─ Check {check_id}: Synthetic {_DASH * 4}┐"]
    if skipped:
        out.append(_SKIP_LINE)
    out.extend(f"│  {line}" for line in issue_lines)
    if not issue_lines and not skipped:
        out.append("│  (no issues)")
    out.append("└" + _DASH * 20 + "┘")
    return out


def _engine_output(chosen, not_quick, issues=0, issue_map=None, skip_not_quick=True):
    """Captured-engine-output fixture: one section per segment + a Result anchor."""
    issue_map = issue_map or {}
    lines = []
    for check_id in chosen:
        lines.extend(_section(check_id, issue_map.get(check_id, ())))
    for check_id in not_quick:
        lines.extend(_section(check_id, skipped=skip_not_quick))
    if issues > 0:
        lines.append(f"│  Result: ISSUES FOUND — {issues} issue(s)")
    else:
        lines.append("│  Result: PASSED — 0 issues found")
    return "\n".join(lines) + "\n"


def _snapshot_ids():
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    return tuple(data["faces"]["check_segments"]["ids"])


def _not_quick_count():
    """Policy-face size, derived from the registry — never re-spelled.

    The claim these assertions make is structural ("the quick face is exactly
    the complement of the product-gate exclusion set"), so a deliberate
    contract change must not force edits to the numbers that express it.
    """
    return len(qr.excluded_ids())


def _selection():
    return qs.select()


def _fake_engine(stdout_text, count):
    """Stand-in for ``_run_full_engine_checks`` printing text and returning count."""

    def inner(args):
        print(stdout_text, end="")
        return count

    return inner


def _args(**kwargs):
    defaults = dict(summary_only=False, fail_on_issues=False, summary_level="standard",
                    quick=False, shadow=False, quick_requested=False, product_gates=False)
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


# ── ① S-A/S-B shadow 通道（§4.1）──────────────────────────────────────────
class Acceptance1ShadowChannelTests(unittest.TestCase):
    """S-A 机器判定 ①②③ + S-B 逐段裁决等价比对。"""

    def test_selection_covers_every_registry_segment_without_overlap(self):
        selection = _selection()
        chosen, not_quick = set(selection.chosen), set(selection.not_quick)
        self.assertEqual(len(chosen), len(_snapshot_ids()) - _not_quick_count())
        self.assertEqual(len(not_quick), _not_quick_count())
        self.assertEqual(chosen & not_quick, set())
        self.assertEqual(chosen | not_quick, set(_snapshot_ids()))
        self.assertEqual(qs.selection_contract_violations(selection), ())

    def test_every_not_quick_segment_carries_a_registry_reason_code(self):
        selection = _selection()
        for check_id in selection.not_quick:
            self.assertIn(selection.reasons[check_id], qr.EXCLUSION_REASON_CODES, check_id)
            self.assertEqual(qs.declaration_fingerprint(check_id),
                             qs.declaration_fingerprint(check_id))  # deterministic

    def test_c3_adjudicated_segments_are_declared_and_in_the_quick_face(self):
        selection = _selection()
        for check_id in qr.C3_ADJUDICATED_SEGMENTS:
            self.assertIn(check_id, qr.registry_ids(), check_id)
            self.assertIn(check_id, selection.chosen, check_id)

    def test_selection_contract_violations_have_teeth(self):
        """Negative control: overlap / missing reason / unlisted C3 must be caught."""
        good = _selection()
        overlapping = qs.Selection(
            chosen=good.chosen + ("7",), not_quick=good.not_quick, reasons=good.reasons,
            fail_closed=False, undeclared=(), observed=(), untrusted="")
        self.assertTrue(qs.selection_contract_violations(overlapping))
        bad_reason = qs.Selection(
            chosen=good.chosen, not_quick=good.not_quick, reasons={"7": None},
            fail_closed=False, undeclared=(), observed=(), untrusted="")
        self.assertTrue(any("原因代码" in v for v in qs.selection_contract_violations(bad_reason)))

    def test_quick_exclusion_face_is_exactly_the_product_gate_declaration(self):
        """QR-5 正交性 / 性能机制前提：quick 跳过面 ≡ FIX-270 product-gate 声明。"""
        selection = _selection()
        self.assertEqual(set(selection.not_quick), set(qr.discover_product_gate_ids()))

    def test_sb_execution_shadow_passes_when_quick_equals_full(self):
        selection = _selection()
        quick = _engine_output(selection.chosen, selection.not_quick, issues=0)
        full = _engine_output(selection.chosen, selection.not_quick, issues=0)
        shadow = qs.shadow_compare(quick, full, selection.chosen)
        self.assertTrue(shadow.ok, shadow.mismatches)
        self.assertEqual(len(shadow.compared), 45)
        self.assertEqual(shadow.blocking, ())

    def test_sb_execution_shadow_is_blocking_on_a_verdict_mismatch(self):
        """§4.1 S-B：同输入同码——任何不一致 = BLOCKING（隐藏输入依赖）。"""
        selection = _selection()
        quick = _engine_output(selection.chosen, selection.not_quick, issues=0)
        full = _engine_output(selection.chosen, selection.not_quick, issues=1,
                              issue_map={"3": ["[WARN] only visible in full"]})
        shadow = qs.shadow_compare(quick, full, selection.chosen)
        self.assertFalse(shadow.ok)
        self.assertEqual(len(shadow.blocking), 1)
        self.assertIn("3", shadow.blocking[0])
        self.assertTrue(any("BLOCKING" in line for line in qs.shadow_lines(shadow)))

    def test_sb_execution_shadow_flags_a_segment_missing_from_full(self):
        selection = _selection()
        quick = _engine_output(selection.chosen, selection.not_quick, issues=0)
        full = _engine_output([c for c in selection.chosen if c != "5"],
                              selection.not_quick, issues=0)
        shadow = qs.shadow_compare(quick, full, selection.chosen)
        self.assertFalse(shadow.ok)
        self.assertEqual(shadow.missing_full, ("5",))

    def test_sa_dry_run_lines_carry_reasons_and_declaration_fingerprints(self):
        lines = qs.shadow_dry_run_lines(_selection())
        joined = "\n".join(lines)
        self.assertIn("chosen=45", joined)
        self.assertIn(f"not-run={_not_quick_count()}", joined)
        self.assertIn("PLUGIN_GIT_FACT_SOURCE", joined)
        self.assertIn("fingerprints:", joined)


# ── ② 四态契约（§2.4）────────────────────────────────────────────────────
class Acceptance2FourStateGuardTests(unittest.TestCase):
    """四态计数必现 / NOT_RUN 不得使 N 归零 / 逐段状态可判。"""

    def setUp(self):
        self.selection = _selection()

    def _report(self, issues=0, issue_map=None, **kwargs):
        text = _engine_output(self.selection.chosen, self.selection.not_quick,
                              issues=issues, issue_map=issue_map, **kwargs)
        return qs.quick_report(text, selection=self.selection)

    def test_summary_line_carries_all_four_state_counts(self):
        line = qs.summary_line(self._report(issues=2, issue_map={"3": ["[WARN] x"]}))
        self.assertEqual(qs.summary_line_contract_violations(line), ())
        for field in ("passed", "failed", "not-run", "cache-reused", "undetermined"):
            self.assertIn(field, line)
        self.assertIn("(quick)", line)

    def test_summary_line_without_counts_is_a_contract_violation(self):
        """Negative control（QR-4）：缺四态计数的汇总行 = 违规。"""
        violations = qs.summary_line_contract_violations("Governance: 3 issues")
        self.assertTrue(violations)
        self.assertTrue(any("契约" in v for v in violations))
        self.assertTrue(qs.summary_line_contract_violations(""))

    def test_not_run_segments_do_not_zero_or_reduce_the_issue_count(self):
        """§2.4 硬约束 1：25 段 NOT_RUN 而 N 仍为执行面实测值。"""
        report = self._report(issues=4, issue_map={"3": ["[WARN] a"], "19": ["[FAIL] b"]})
        self.assertEqual(report.not_run, _not_quick_count())
        self.assertEqual(report.failed, 2)
        self.assertEqual(report.passed, 43)
        self.assertEqual(report.issues, 4)
        self.assertFalse(report.issues_unknown)

    def test_all_segments_unexecuted_reports_n_unknown_not_zero(self):
        """§2.4 硬约束 1：全部实质段未执行 → ``N=unknown``，禁 0 冒充。"""
        text = _engine_output((), self.selection.chosen + self.selection.not_quick,
                              issues=0)
        report = qs.quick_report(text, selection=self.selection)
        self.assertTrue(report.issues_unknown)
        self.assertIsNone(report.issues)
        self.assertIn("N=unknown", qs.summary_line(report))
        self.assertEqual(report.substantive, 0)

    def test_parse_degraded_output_is_unknown_and_flagged(self):
        text = _engine_output(self.selection.chosen, self.selection.not_quick, issues=0)
        degraded = text.replace("│  Result: PASSED — 0 issues found", "")
        report = qs.quick_report(degraded, selection=self.selection)
        self.assertTrue(report.issues_unknown)
        self.assertTrue(any("parse degraded" in v for v in report.violations))
        self.assertFalse(report.ok)

    def test_per_segment_states_are_exposed_for_every_registry_id(self):
        report = self._report(issues=1, issue_map={"3": ["[WARN] x"]})
        ids = [s.check_id for s in report.segments]
        self.assertEqual(ids, list(qr.registry_ids()))
        tokens = {s.check_id: s.token for s in report.segments}
        self.assertEqual(tokens["3"], qs.STATE_FAILED)
        self.assertEqual(tokens["7"], "NOT_RUN(PLUGIN_GIT_FACT_SOURCE)")
        self.assertEqual(tokens["18h"], qs.STATE_PASSED)

    def test_state_tokens_follow_the_four_state_contract_vocabulary(self):
        report = self._report()
        self.assertEqual(
            set(s.state for s in report.segments),
            {qs.STATE_PASSED, qs.STATE_NOT_RUN},
        )
        for state in (qs.STATE_PASSED, qs.STATE_FAILED, qs.STATE_NOT_RUN,
                      qs.STATE_CACHED, qs.STATE_UNDETERMINED):
            self.assertIn(state, qs.SEGMENT_STATE_TOKENS)

    def test_cached_state_is_counted_and_disclosed(self):
        """缓存复用态在 Slice-2 只声明（Slice-3 交付指纹生产者）——计数必现。"""
        report = qs.quick_report(
            _engine_output(self.selection.chosen, self.selection.not_quick),
            cached_ids=("1",), selection=self.selection)
        self.assertEqual(report.cached, 1)
        self.assertIn("cache-reused", qs.summary_line(report))
        cached = [s for s in report.segments if s.check_id == "1"][0]
        self.assertEqual(cached.state, qs.STATE_CACHED)
        self.assertTrue(cached.token.startswith("CACHED("))

    def test_quick_face_segment_reported_as_skip_is_undetermined(self):
        """fail-safe：选择面内出现 [SKIP] ⇒ 观察与政策不符 ⇒ UNDETERMINED。"""
        text = _engine_output(self.selection.chosen, self.selection.not_quick)
        text = text.replace("│  (no issues)", _SKIP_LINE, 1)
        report = qs.quick_report(text, selection=self.selection)
        undetermined = [s for s in report.segments if s.state == qs.STATE_UNDETERMINED]
        self.assertEqual(len(undetermined), 1)
        self.assertEqual(undetermined[0].reason, qs.REASON_UNEXPECTED_SKIP)
        self.assertEqual(undetermined[0].check_id, self.selection.chosen[0])

    def test_not_quick_segment_that_actually_ran_is_undetermined(self):
        """政策说排除、观察却执行 ⇒ 不可报 NOT_RUN（fail-safe）。"""
        text = _engine_output(self.selection.chosen, self.selection.not_quick,
                              skip_not_quick=False)
        report = qs.quick_report(text, selection=self.selection)
        mismatched = [s for s in report.segments if s.reason == qs.REASON_POLICY_MISMATCH]
        self.assertEqual(len(mismatched), _not_quick_count())
        self.assertEqual(report.not_run, 0)

    def test_missing_section_for_a_quick_face_segment_is_undetermined(self):
        chosen = [c for c in self.selection.chosen if c != "2"]
        text = _engine_output(chosen, self.selection.not_quick)
        report = qs.quick_report(text, selection=self.selection)
        missing = [s for s in report.segments if s.reason == qs.REASON_NO_SECTION]
        self.assertEqual([s.check_id for s in missing], ["2"])
        self.assertEqual(report.not_run, _not_quick_count())

    def test_report_lines_stay_bounded_and_disclose_every_not_run_segment(self):
        report = self._report(issues=1, issue_map={"3": ["[WARN] x"]})
        lines = report.lines()
        self.assertTrue(lines[0].startswith("Governance: "))
        self.assertTrue(any(
            line.startswith(f"[NOT_RUN] {_not_quick_count()} segment(s)")
            for line in lines))
        self.assertLess(len(lines), 12, "quick 输出必须有界（FIX-278 G1 预算）")
        self.assertTrue(any(line.startswith("[WARN] Check 3") for line in lines))

    def test_skip_marker_quoted_in_prose_does_not_skip_a_segment(self):
        """Real-run regression: Check 17 quotes ``[SKIP]`` inside a ``[PASS]`` line.

        Treating a mere substring hit as a skip declaration marked 17 as
        UNDETERMINED(UNEXPECTED_SKIP) on the live tree — a false positive that
        would misreport a healthy segment as "no knowledge".
        """
        text = ("┌─ Check 18h: Synthetic ────┐\n"
                "│  [PASS] FEAT-016 (EVD-970): 感知变化=无（四态前的旧验证）"
                "[SKIP] marker quoted in prose\n"
                "└──────────────────────────┘\n"
                "│  Result: PASSED — 0 issues found\n")
        observation = qs.parse_engine_sections(text)
        section = observation.section("18h")
        self.assertIsNotNone(section)
        self.assertTrue(section.executed)
        self.assertFalse(section.skipped)

    def test_skip_line_naming_another_check_is_attributed_to_that_check(self):
        """Real-run regression: 30b prints no banner — its skip line sits inside 30c.

        Attributing that line to the enclosing section marked the healthy 30c as
        skipped; the named-id rule keeps both segments truthful (30b NOT_RUN by
        policy, 30c by its own verdict).
        """
        text = ("┌─ Check 30c: Synthetic ────┐\n"
                "│  Rows judged: 113\n"
                "│  [SKIP] product self-check — Check 30b loop wiring call sites "
                "(plugin infra AST scan); enable with --product-gates\n"
                "└──────────────────────────┘\n"
                "│  Result: PASSED — 0 issues found\n")
        observation = qs.parse_engine_sections(text)
        self.assertTrue(observation.section("30b").skipped)
        self.assertTrue(observation.section("30c").executed)
        self.assertFalse(observation.section("30c").skipped)


# ── ③ 默认路径字节等价（dispatch 对照）────────────────────────────────────
class Acceptance3DefaultPathTests(unittest.TestCase):
    """不带 --quick 的输出与现状逐字节一致（test_summary_only.py 先例）。"""

    def test_default_path_is_byte_identical_without_quick(self):
        engine_output = (
            "┌─ Check 1: Evidence Completeness ─────────────────────┐\n"
            "│  Result: ISSUES FOUND — 3 issue(s)\n"
            "└──────────────────────────────────────────────────────┘\n")
        with mock.patch.object(vw, "_run_full_engine_checks",
                               side_effect=_fake_engine(engine_output, 3)) as eng:
            buf = io.StringIO()
            with redirect_stdout(buf):
                vw.cmd_check_governance(_args())
            eng.assert_called_once()
            self.assertEqual(buf.getvalue(), engine_output)
            self.assertNotIn("Governance: ", buf.getvalue())

    def test_summary_only_path_is_unchanged_without_quick(self):
        engine_output = (
            "┌─ Check 1: Evidence Completeness ─────────────────────┐\n"
            "│  [FAIL] something\n"
            "│  Result: ISSUES FOUND — 1 issue(s)\n"
            "└──────────────────────────────────────────────────────┘\n")
        with mock.patch.object(vw, "_run_full_engine_checks",
                               side_effect=_fake_engine(engine_output, 1)):
            buf = io.StringIO()
            with redirect_stdout(buf):
                vw.cmd_check_governance(_args(summary_only=True))
            out = buf.getvalue()
            self.assertTrue(out.startswith("Governance: 1 issues"))
            self.assertNotIn("not-run", out)

    def test_quick_flags_are_registered_on_the_cli(self):
        result = subprocess.run(
            [sys.executable, "-B", str(ENGINE), "check-governance", "--help"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=180)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--quick", result.stdout)
        self.assertIn("--shadow", result.stdout)

    def test_quick_implies_the_summary_path_with_the_four_state_line(self):
        selection = _selection()
        quick_output = _engine_output(selection.chosen, selection.not_quick, issues=1,
                                      issue_map={"3": ["[WARN] x"]})
        with mock.patch.object(vw, "_run_full_engine_checks",
                               side_effect=_fake_engine(quick_output, 1)) as eng:
            buf = io.StringIO()
            with redirect_stdout(buf):
                vw.cmd_check_governance(_args(quick=True))
            out = buf.getvalue()
            eng.assert_called_once()
            self.assertIn("1 issues (quick)", out)
            self.assertIn(f"44 passed / 1 failed / {_not_quick_count()} not-run", out)
            self.assertIn("NOT_RUN", out)

    def test_quick_calls_the_engine_with_the_product_gate_disabled(self):
        """性能机制：--quick 复用 FIX-270 跳过机制（零段级改动）。"""
        seen = {}

        def inner(args):
            seen["gate"] = vw._product_gate_active(args)
            seen["quick"] = getattr(args, "quick", None)
            print("│  Result: PASSED — 0 issues found\n", end="")
            return 0

        with mock.patch.object(vw, "_run_full_engine_checks", side_effect=inner):
            with redirect_stdout(io.StringIO()):
                vw.cmd_check_governance(_args(quick=True))
        self.assertFalse(seen["gate"])
        self.assertTrue(seen["quick"])

    def test_default_invocation_keeps_the_product_gate_active(self):
        seen = {}

        def inner(args):
            seen["gate"] = vw._product_gate_active(args)
            print("│  Result: PASSED — 0 issues found\n", end="")
            return 0

        with mock.patch.object(vw, "_run_full_engine_checks", side_effect=inner):
            with redirect_stdout(io.StringIO()):
                vw.cmd_check_governance(_args())
        self.assertTrue(seen["gate"])

    def test_quick_keeps_fail_on_issues_exit_semantics(self):
        selection = _selection()
        quick_output = _engine_output(selection.chosen, selection.not_quick, issues=2,
                                      issue_map={"3": ["[WARN] x"], "19": ["[FAIL] y"]})
        with mock.patch.object(vw, "_run_full_engine_checks",
                               side_effect=_fake_engine(quick_output, 2)):
            with redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as ctx:
                    vw.cmd_check_governance(_args(quick=True, fail_on_issues=True))
        self.assertEqual(ctx.exception.code, 1)

    def test_quick_does_not_exit_when_only_not_run_segments_exist(self):
        """not-run 不触发也不豁免：N=0（执行面无 issues）→ 不 exit。"""
        selection = _selection()
        quick_output = _engine_output(selection.chosen, selection.not_quick, issues=0)
        with mock.patch.object(vw, "_run_full_engine_checks",
                               side_effect=_fake_engine(quick_output, 0)):
            with redirect_stdout(io.StringIO()):
                vw.cmd_check_governance(_args(quick=True, fail_on_issues=True))


# ── ④ FIX-304 消费口径（注册表守卫 → UNDETERMINED → 回退 full）──────────────
class Acceptance4Fix304CaliberTests(unittest.TestCase):
    """FIX-304 F-3/G-1：重复 CheckID 的 ValueError = 观察不可信 → 回退 full。"""

    def test_duplicate_census_observation_is_untrusted_and_disables_quick(self):
        duplicated = _snapshot_ids() + ("29",)
        selection = qs.select(observed_ids=duplicated)
        self.assertTrue(selection.untrusted)
        self.assertIn(qs.REASON_CENSUS_UNTRUSTED, selection.untrusted)
        self.assertFalse(selection.quick_available)
        self.assertFalse(qs.selection_contract_violations(selection))

    def test_undeclared_engine_segment_fails_closed_and_disables_quick(self):
        selection = qs.select(observed_ids=_snapshot_ids() + ("41",))
        self.assertTrue(selection.fail_closed)
        self.assertEqual(selection.undeclared, ("41",))
        self.assertFalse(selection.quick_available)

    def test_fallback_report_reports_what_the_engine_actually_did(self):
        selection = qs.select(observed_ids=_snapshot_ids() + ("41",))
        text = _engine_output(qr.registry_ids(), (), issues=1,
                              issue_map={"3": ["[WARN] x"]})
        report = qs.quick_report(text, selection=selection)
        self.assertEqual(report.mode, "full-fallback")
        self.assertEqual(report.undetermined, 0)   # full run executed every segment
        self.assertEqual(report.failed, 1)
        self.assertEqual(report.issues, 1)
        notice = "\n".join(report.notices)
        self.assertIn("FALLBACK", notice)
        self.assertIn(f"UNDETERMINED({qr.REASON_UNDECLARED_SEGMENT})", notice)
        self.assertIn("undeclared=['41']", notice)

    def test_prepare_quick_args_clears_quick_when_the_guard_fails_closed(self):
        args = _args(quick=True, shadow=True)
        fail_closed = qs.select(observed_ids=_snapshot_ids() + ("41",))
        with mock.patch.object(qs, "select", return_value=fail_closed):
            notice = qs.prepare_quick_args(args)
        self.assertFalse(args.quick)
        self.assertFalse(args.shadow)
        self.assertTrue(args.quick_requested)
        self.assertIn("FALLBACK", notice)
        self.assertIn(qr.REASON_UNDECLARED_SEGMENT, notice)

    def test_prepare_quick_args_fails_closed_on_an_untrusted_census(self):
        args = _args(quick=True)
        untrusted = qs.select(observed_ids=_snapshot_ids() + ("29",))
        with mock.patch.object(qs, "select", return_value=untrusted):
            notice = qs.prepare_quick_args(args)
        self.assertFalse(args.quick)
        self.assertIn(qs.REASON_CENSUS_UNTRUSTED, notice)

    def test_prepare_quick_args_keeps_quick_on_a_healthy_registry(self):
        args = _args(quick=True)
        notice = qs.prepare_quick_args(args)
        self.assertEqual(notice, "")
        self.assertTrue(args.quick)
        self.assertTrue(args.quick_requested)

    def test_fail_closed_discriminant_is_used_not_fallback_target(self):
        """F-5 口径：判别字段 = fail_closed；fallback_target 只是回退目标。"""
        healthy = qs.select()
        self.assertFalse(healthy.fail_closed)
        self.assertTrue(healthy.quick_available)
        self.assertEqual(qr.MODE_FULL_FALLBACK, "full")
        broken = qs.select(observed_ids=_snapshot_ids() + ("41",))
        self.assertTrue(broken.fail_closed)
        self.assertFalse(broken.quick_available)

    def test_registry_guard_duplicate_error_propagates_the_fix_304_contract(self):
        """回归钉：注册表侧的重复入参守卫仍然抛错（消费口径的前提）。"""
        duplicated = _snapshot_ids() + ("29",)
        with self.assertRaises(ValueError):
            qr.guard_completeness(observed_ids=duplicated)
        with self.assertRaises(ValueError):
            qr.reconcile_snapshot(actual_ids=duplicated)


# ── 载体纪律与静态自检 ─────────────────────────────────────────────────────
class CarrierDisciplineTests(unittest.TestCase):
    """FX-195 §255 / §4.1 R4：独立载体、不 import 巨石、零 print、零 I/O。"""

    def test_selector_does_not_import_the_engine(self):
        source = SELECTOR.read_text(encoding="utf-8")
        self.assertNotIn("import verify_workflow", source)
        self.assertNotIn("from verify_workflow", source)
        self.assertNotIn("argparse", source)

    def test_selector_never_prints_and_has_no_import_time_io(self):
        source = SELECTOR.read_text(encoding="utf-8")
        tree = ast.parse(source)
        prints = [n.lineno for n in ast.walk(tree)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                  and n.func.id == "print"]
        self.assertEqual(prints, [], "渲染归 L5（§4.1 R4）：选择器只返回文本")
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                continue
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                    self.assertNotIn(sub.func.attr, ("read_text", "write_text", "open"),
                                     f"line {sub.lineno}")

    def test_engine_imports_the_selector_lazily_inside_the_quick_branch(self):
        """R2/R6 discipline: the selector import stays in-branch (no top-level import)."""
        source = ENGINE.read_text(encoding="utf-8")
        found = [line for line in source.splitlines()
                 if "import quickscan_selector" in line or "from quickscan_selector" in line]
        self.assertTrue(found, "engine must wire the selector")
        for line in found:
            self.assertNotEqual(line, line.lstrip(),
                                "selector import must stay an indented in-branch import")

    def test_engine_source_has_no_second_selection_path(self):
        """ALT-2：quick 复用同一引擎——不得新增平行的选择/编排体。"""
        source = ENGINE.read_text(encoding="utf-8")
        self.assertNotIn("quickscan_selector.render", source.replace(
            "quickscan_selector import render_quick_output", ""))
        self.assertIn('_PLUGIN_PRODUCT_CHECK_IDS', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
