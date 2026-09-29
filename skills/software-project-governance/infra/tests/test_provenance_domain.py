"""Unit tests for infra/checks/provenance_domain.py — FEAT-077 / ADR-021 B2.

Covers the three UNWIRED pure judgement pieces of the M1/M2 priority
enforcement bottom layer (ADR-021 §4 B2 — delivery without verify_workflow.py
wiring; the 反倒挂判定 box / release-readiness sub-check / 闭环率指标面
wiring are B3/B4, locked by FIX-404 per ADR-021 F10; check-box numbers 随
ADR 返工重编，不在此写死):

  - :func:`provenance_domain.check_priority_inversion` — ADR-021 §2.2.3
    反倒挂判定 (Priority Inversion Guard): INV-1 (a machine-signal item
    ranked above an OPEN user-named item in the recommended pool), INV-2 (an
    unblocked-eligible user-named item parked in non_executable while the
    recommended pool is non-empty and ALL machine-signal), staged fail-closed
    (coverage 0 → SKIP + WARN, BC-2), conflict rows → FAIL (data consistency
    over ordering judgement).
  - :func:`provenance_domain.check_release_admission` — ADR-021 §2.2.4
    发布门判定 (provenance release gate): a release version carrying open
    machine-signal work while user-named items remain open → FAIL; explicit
    deferral (target_version strictly ABOVE the release version) exempts; a
    payload task with no declared provenance → FAIL (未申报 fail-closed).
  - :func:`provenance_domain.session_closure_rate` — ADR-021 §3.2.3 闭环率
    指标 (M2 effectiveness criterion): closed/raised per session with the
    deferred-registration zeroing precondition
    (``rate == 1.0 ∧ deferred_detections == 0`` machine form).

Row contract (shared by the two task-row judgements, mirrors the
:class:`task_priority.PriorityReport` bucket vocabulary so B3 wiring maps a
report to rows mechanically):

    {
        "task_id": str,                       # e.g. "FIX-226"
        "demand_source": str,                 # user-named|active-defect|machine-signal|legacy|conflict
        "bucket": str,                        # recommended|non_executable|blocked|completed
        "priority": str, optional,            # informational
        "target_version": str, optional,      # release-admission payload matching
    }

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_provenance_domain.py -v
"""

import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

from checks import provenance_domain as pd  # noqa: E402


def _row(task_id, demand_source, bucket="recommended", priority="P1",
         target_version=""):
    return {
        "task_id": task_id,
        "demand_source": demand_source,
        "bucket": bucket,
        "priority": priority,
        "target_version": target_version,
    }


# ─── check_priority_inversion — ADR-021 §2.2.3 反倒挂判定 ────────────────────


class CheckPriorityInversionInv1Tests(unittest.TestCase):
    """INV-1 — machine-signal ranked above an OPEN user-named item."""

    def test_machine_signal_above_open_user_named_fails(self):
        rows = [
            _row("FIX-001", "machine-signal"),
            _row("FIX-002", "user-named"),
        ]
        result = pd.check_priority_inversion(rows)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any(
            "FIX-001" in i and "FIX-002" in i for i in result["issues"]),
            result["issues"])
        self.assertTrue(any("排位高于" in i for i in result["issues"]))

    def test_user_named_above_machine_signal_passes(self):
        rows = [
            _row("FIX-002", "user-named"),
            _row("FIX-001", "machine-signal"),
        ]
        result = pd.check_priority_inversion(rows)
        self.assertEqual(result["status"], "PASS", result["issues"])
        self.assertEqual(result["issues"], [])

    def test_completed_user_named_is_not_open(self):
        # A completed user-named row is not an OPEN demand — a machine-signal
        # row ranked above it is NOT an inversion (ADR-021 §2.2.3 INV-1
        # qualifies U as open; the completed bucket is excluded).
        rows = [
            _row("FIX-001", "machine-signal"),
            _row("FIX-002", "user-named", bucket="completed"),
        ]
        result = pd.check_priority_inversion(rows)
        self.assertEqual(result["status"], "PASS", result["issues"])

    def test_inversion_judged_within_recommended_pool_only(self):
        # A non_executable machine-signal row sitting earlier in the input
        # list is not part of the recommended pool — no INV-1 issue.
        rows = [
            _row("FIX-003", "machine-signal", bucket="non_executable"),
            _row("FIX-002", "user-named"),
        ]
        result = pd.check_priority_inversion(rows)
        self.assertEqual(result["status"], "PASS", result["issues"])

    def test_cross_level_inversion_is_flagged(self):
        # ADR-021 §2.2.3 INV-1 has NO priority qualifier: even a P0
        # machine-signal item ahead of a P1 user-named item in the
        # recommended pool is flagged — cross-level inversion is exactly
        # what the 反倒挂判定 兜底 (D1 keeps the SORT from crossing P levels;
        # the CHECK still surfaces the structural deferral).
        rows = [
            _row("FIX-001", "machine-signal", priority="P0"),
            _row("FIX-002", "user-named", priority="P1"),
        ]
        result = pd.check_priority_inversion(rows)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("FIX-002" in i for i in result["issues"]))


class CheckPriorityInversionInv2Tests(unittest.TestCase):
    """INV-2 — parked user-named while machine-signal fills the board."""

    def test_parked_user_named_with_all_machine_recommendations_fails(self):
        rows = [
            _row("FIX-001", "machine-signal"),
            _row("FIX-002", "machine-signal"),
            _row("FIX-003", "user-named", bucket="non_executable"),
        ]
        result = pd.check_priority_inversion(rows)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any(
            "FIX-003" in i and "INV-2" in i for i in result["issues"]),
            result["issues"])

    def test_no_inv2_when_recommendations_mixed(self):
        # The recommended pool contains a user-named item → the user is not
        # parked out of the board (ADR-021 §2.2.3 INV-2 requires recommended
        # non-empty AND all machine-signal). The user-named recommendation
        # leads the pool, so INV-1 does not fire either.
        rows = [
            _row("FIX-004", "user-named"),
            _row("FIX-001", "machine-signal"),
            _row("FIX-003", "user-named", bucket="non_executable"),
        ]
        result = pd.check_priority_inversion(rows)
        self.assertEqual(result["status"], "PASS", result["issues"])

    def test_no_inv2_when_recommendations_empty(self):
        rows = [_row("FIX-003", "user-named", bucket="non_executable")]
        result = pd.check_priority_inversion(rows)
        self.assertEqual(result["status"], "PASS", result["issues"])

    def test_blocked_user_named_is_not_parked_by_status(self):
        # A dependency-BLOCKED user-named row is not "non_executable by
        # status marking" — blocking is a dependency fact, not a parking
        # decision (INV-2 targets the status-filter bucket only).
        rows = [
            _row("FIX-001", "machine-signal"),
            _row("FIX-003", "user-named", bucket="blocked"),
        ]
        result = pd.check_priority_inversion(rows)
        self.assertEqual(result["status"], "PASS", result["issues"])


class CheckPriorityInversionStagedTests(unittest.TestCase):
    """Staged fail-closed — coverage 0 / conflict / empty (ADR §2.2.3, BC-2)."""

    def test_all_legacy_coverage_zero_skips_with_warning(self):
        rows = [
            _row("FIX-001", "legacy"),
            _row("FIX-002", "legacy"),
        ]
        result = pd.check_priority_inversion(rows)
        self.assertEqual(result["status"], "SKIP")
        self.assertEqual(result["issues"], [])
        self.assertTrue(result["warnings"])
        self.assertTrue(any("覆盖率" in w for w in result["warnings"]))

    def test_conflict_rows_fail_even_at_zero_coverage(self):
        # conflict 数据存在 → FAIL（数据一致性优先于排序判断）— regardless
        # of the staged coverage skip (ADR-021 §2.2.3).
        rows = [_row("FIX-001", "conflict")]
        result = pd.check_priority_inversion(rows)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("conflict" in i.lower() for i in result["issues"]))

    def test_conflict_fails_alongside_inversion_issues(self):
        rows = [
            _row("FIX-001", "machine-signal"),
            _row("FIX-002", "conflict"),
            _row("FIX-003", "user-named"),
        ]
        result = pd.check_priority_inversion(rows)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("FIX-002" in i and "conflict" in i.lower()
                            for i in result["issues"]))
        self.assertTrue(any("FIX-001" in i and "FIX-003" in i
                            for i in result["issues"]))

    def test_empty_rows_skip(self):
        result = pd.check_priority_inversion([])
        self.assertEqual(result["status"], "SKIP")
        self.assertEqual(result["issues"], [])
        self.assertTrue(result["warnings"])

    def test_coverage_counts_labeled_rows(self):
        rows = [
            _row("FIX-001", "machine-signal"),
            _row("FIX-002", "legacy"),
            _row("FIX-003", "user-named"),
        ]
        result = pd.check_priority_inversion(rows)
        self.assertEqual(result["coverage"]["labeled"], 2)
        self.assertEqual(result["coverage"]["total"], 3)
        self.assertAlmostEqual(result["coverage"]["ratio"], 2 / 3)

    def test_mixed_legacy_and_labeled_board_enforced(self):
        # 覆盖率 > 0 → INV-1/INV-2 命中即 FAIL（分阶段 fail-closed）.
        rows = [
            _row("FIX-001", "machine-signal"),
            _row("FIX-009", "legacy"),
            _row("FIX-003", "user-named"),
        ]
        result = pd.check_priority_inversion(rows)
        self.assertEqual(result["status"], "FAIL")


# ─── check_release_admission — ADR-021 §2.2.4 (provenance release gate) ──────


class CheckReleaseAdmissionTests(unittest.TestCase):
    """Release admission — machine-signal payload vs open user-named."""

    _PAYLOAD = {"version": "0.92.0"}

    def test_payload_machine_signal_with_open_user_named_fails(self):
        rows = [
            _row("FIX-001", "machine-signal", target_version="0.92.0"),
            _row("FIX-002", "user-named", target_version="0.91.0"),
        ]
        result = pd.check_release_admission(rows, self._PAYLOAD)
        self.assertEqual(result["status"], "FAIL", result["issues"])
        self.assertTrue(any(
            "FIX-001" in i and "FIX-002" in i and "未闭合" in i
            for i in result["issues"]), result["issues"])

    def test_all_user_named_closed_passes(self):
        rows = [
            _row("FIX-001", "machine-signal", target_version="0.92.0"),
            _row("FIX-002", "user-named", target_version="0.91.0",
                 bucket="completed"),
        ]
        result = pd.check_release_admission(rows, self._PAYLOAD)
        self.assertEqual(result["status"], "PASS", result["issues"])

    def test_explicit_deferral_above_release_exempts(self):
        # UN 项 target_version 明确 > release_version（用户已知悉的显式改期，
        # DEC-286(7)「或显式请用户改期」）→ 不计入 UN.
        rows = [
            _row("FIX-001", "machine-signal", target_version="0.92.0"),
            _row("FIX-002", "user-named", target_version="0.93.0"),
        ]
        result = pd.check_release_admission(rows, self._PAYLOAD)
        self.assertEqual(result["status"], "PASS", result["issues"])
        self.assertIn("FIX-002", result["deferred_user_named"])

    def test_user_named_without_version_counts_open(self):
        # 无 target_version 的 user-named 项不得因版本边界隐形顺延
        # (ADR-021 §2.2.4: UN 不限版本).
        rows = [
            _row("FIX-001", "machine-signal", target_version="0.92.0"),
            _row("FIX-002", "user-named", target_version=""),
        ]
        result = pd.check_release_admission(rows, self._PAYLOAD)
        self.assertEqual(result["status"], "FAIL")

    def test_machine_signal_outside_payload_is_not_ms(self):
        # MS 只看本版本载荷（target_version == release_version 且未完成）.
        rows = [
            _row("FIX-001", "machine-signal", target_version="0.93.0"),
            _row("FIX-002", "user-named", target_version="0.91.0"),
        ]
        result = pd.check_release_admission(rows, self._PAYLOAD)
        self.assertEqual(result["status"], "PASS", result["issues"])

    def test_payload_task_without_provenance_fails_closed(self):
        # 版本载荷任务无 demand_source 申报（无 triage 记录 / 未标）→ FAIL
        # (ADR-021 §2.2.4: 版本载荷的 provenance 不完整即拒绝发布).
        rows = [
            _row("FIX-001", "legacy", target_version="0.92.0"),
        ]
        result = pd.check_release_admission(rows, self._PAYLOAD)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("FIX-001" in i for i in result["issues"]))
        self.assertIn("FIX-001", result["undeclared_payload"])

    def test_legacy_task_outside_payload_not_flagged_undeclared(self):
        # 存量不在发布门作用域 (BC-2): a legacy row targeting a DIFFERENT
        # version is not part of this release payload.
        rows = [
            _row("FIX-009", "legacy", target_version="0.90.0"),
            _row("FIX-002", "user-named", target_version="0.91.0",
                 bucket="completed"),
        ]
        result = pd.check_release_admission(rows, self._PAYLOAD)
        self.assertEqual(result["status"], "PASS", result["issues"])

    def test_dec287_scenario_c_level_softwareization(self):
        # DEC-287(1) 场景回归：C 级软件化（user-named）未闭合时，任何载
        # machine-signal 工作的版本无法过发布门.
        rows = [
            _row("REL-090", "machine-signal", target_version="0.92.0"),
            _row("FEAT-091", "user-named", target_version="未规划版本"),
        ]
        result = pd.check_release_admission(rows, self._PAYLOAD)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("FEAT-091" in i for i in result["issues"]))

    def test_empty_rows_pass(self):
        result = pd.check_release_admission([], self._PAYLOAD)
        self.assertEqual(result["status"], "PASS", result["issues"])

    def test_missing_release_version_skips_with_warning(self):
        result = pd.check_release_admission(
            [_row("FIX-001", "machine-signal")], {"version": ""})
        self.assertEqual(result["status"], "SKIP")
        self.assertTrue(result["warnings"])


# ─── session_closure_rate — ADR-021 §3.2.3 (M2 effectiveness criterion) ──────


class SessionClosureRateTests(unittest.TestCase):
    """Session closure rate — closed/raised with deferred zeroing."""

    def test_full_closure_is_compliant(self):
        events = [
            {"id": "EVD-901", "kind": "problem"},
            {"id": "EVD-902", "kind": "problem"},
            {"id": "EVD-903", "kind": "problem"},
            {"id": "EVD-901", "kind": "closure"},
            {"id": "EVD-902", "kind": "closure"},
            {"id": "EVD-903", "kind": "closure"},
        ]
        result = pd.session_closure_rate(events)
        self.assertEqual(result["problems_raised"], 3)
        self.assertEqual(result["closed"], 3)
        self.assertEqual(result["session_closure_rate"], 1.0)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["deferred_detections"], 0)

    def test_partial_closure_below_one(self):
        events = [
            {"id": "EVD-901", "kind": "problem"},
            {"id": "EVD-902", "kind": "problem"},
            {"id": "EVD-903", "kind": "problem"},
            {"id": "EVD-901", "kind": "closure"},
            {"id": "EVD-902", "kind": "closure"},
        ]
        result = pd.session_closure_rate(events)
        self.assertAlmostEqual(result["session_closure_rate"], 2 / 3)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["unclosed_ids"], ["EVD-903"])

    def test_deferred_registration_zeroes_rate(self):
        # 违规前置：deferred_detections > 0 → 直接 0%——「登记待以后」行为
        # 本身即未闭环的极端形态 (ADR-021 §3.2.3).
        events = [
            {"id": "EVD-901", "kind": "problem"},
            {"id": "EVD-901", "kind": "closure"},
            {"id": "EVD-902", "kind": "deferred_registration"},
        ]
        result = pd.session_closure_rate(events)
        self.assertEqual(result["deferred_detections"], 1)
        self.assertEqual(result["session_closure_rate"], 0.0)
        self.assertFalse(result["compliant"])

    def test_zero_problems_no_deferred_is_trivially_compliant(self):
        result = pd.session_closure_rate([])
        self.assertEqual(result["problems_raised"], 0)
        self.assertEqual(result["session_closure_rate"], 1.0)
        self.assertTrue(result["compliant"])

    def test_deferred_alone_zeroes_even_without_problems(self):
        result = pd.session_closure_rate(
            [{"id": "EVD-901", "kind": "deferred_registration"}])
        self.assertEqual(result["session_closure_rate"], 0.0)
        self.assertFalse(result["compliant"])

    def test_unclosed_problem_without_matching_closure(self):
        # 未配对即计入未闭环（保守计数：宁可多计不可漏计，ADR §3.2.2）.
        events = [
            {"id": "RISK-041", "kind": "problem"},
            {"id": "RISK-042", "kind": "closure"},  # different id — no pair
        ]
        result = pd.session_closure_rate(events)
        self.assertEqual(result["problems_raised"], 1)
        self.assertEqual(result["closed"], 0)
        self.assertEqual(result["unclosed_ids"], ["RISK-041"])
        self.assertEqual(result["session_closure_rate"], 0.0)

    def test_unknown_kinds_and_malformed_events_ignored(self):
        events = [
            {"id": "EVD-901", "kind": "problem"},
            {"id": "EVD-901", "kind": "closure"},
            {"id": "EVD-909", "kind": "note"},          # unknown kind
            "not-a-dict",                                # malformed row
            {"id": "EVD-910"},                           # missing kind
        ]
        result = pd.session_closure_rate(events)
        self.assertEqual(result["problems_raised"], 1)
        self.assertEqual(result["session_closure_rate"], 1.0)
        self.assertTrue(result["compliant"])


# ─── task-priority integration (ADR-021 §2.2.3 测试计划) ──────────────────────


class TaskPriorityIntegrationTests(unittest.TestCase):
    """Real plan-tracker text fixture → tpa report → 反倒挂判定 rows.

    ADR-021 §2.2.3 test plan: 与 task-priority 集成（真实 plan-tracker 文本
    fixture）。The demand-weighted sort must produce a recommended pool whose
    inversion judgement is PASS (the sort layer prevents same-P inversion;
    the 反倒挂判定 catches what the sort cannot express).
    """

    _TABLE = """\
# Plan Tracker

### 优先级一览

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| **P1** | FIX-970 | machine demand | — | 0.1.0 | open | ⏳ 待执行 〔机器信号〕 |
| **P1** | FIX-971 | user demand | — | 0.2.0 | open | ⏳ 待执行 〔用户点名〕 |
| **P1** | FIX-972 | unlabeled legacy demand | — | 0.3.0 | open | ⏳ 待执行 |
| **P2** | FIX-973 | low machine demand | — | 0.1.0 | open | ⏳ 待执行 〔机器信号〕 |
"""

    def test_report_rows_judged_by_inversion_guard(self):
        from task_priority import compute_unblocked_tasks, parse_task_dependencies

        report = compute_unblocked_tasks(
            parse_task_dependencies(self._TABLE))
        # Same-P tie-break (ADR-021 §2.2.2 D1): within P1, user-named and
        # legacy rank ahead of machine-signal — legacy v0.3 after user v0.2.
        self.assertEqual(
            [t.task_id for t in report.recommended_next],
            ["FIX-971", "FIX-972", "FIX-970", "FIX-973"])
        # Map the report to 反倒挂判定 rows (exactly what B3 wiring will do).
        rows = []
        for t in report.recommended_next:
            rows.append(_row(t.task_id, t.demand_source, bucket="recommended",
                             priority=t.priority,
                             target_version=t.target_version))
        result = pd.check_priority_inversion(rows)
        self.assertEqual(result["status"], "PASS", result["issues"])
        self.assertEqual(result["coverage"]["labeled"], 3)


if __name__ == "__main__":
    unittest.main()
