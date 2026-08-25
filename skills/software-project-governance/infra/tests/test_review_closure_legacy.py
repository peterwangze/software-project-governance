"""FIX-278 G2 — legacy baseline 静默：Check 30/37 legacy 判定规则（TDD 红→绿）。
Audit 证据（隔离 fixture 的数据来源 — audit-148 §3.1 + router
``.governance/plan-tracker.md`` 行取证，2026-08-22~23 只读）：

  · ARCH-001「已完成——R1 NEEDS_CHANGE → 返工 → R2 APPROVED_WITH_NOTES
    (unresolved_blockers=0；review-ARCH-001-R2.md)」——无 R0 review 记录
    → 现行 Check 30 V2 "missing R[0]" FAIL（接入治理前旧任务无旧轮 review）。
  · ARCH-002「已完成——审查 APPROVED_WITH_NOTES（review-ARCH-002.md：
    unresolved_blockers=0…）」——审查报告文件为旧格式，机器 token 缺失/异形
    → 现行 V5 "got invalid" FAIL（旧 review 格式 un迁移）。
  · DEV-002「已完成（终态）——Test Reviewer R1 APPROVED_WITH_NOTES/0
    （REVIEW-DEV-002-R1，2026-08-22）」——无 R0 → V2 "missing R[0]" FAIL。
  · 当前工作基准（FIX-006 P0 待实施 / 已完成但当前相关任务）：无违规。
    违规仍须 FAIL 的边界：ACTIVE（未完成）任务的中缝缺轮、已完成任务
    的真实 unresolved_blockers≠0。

判定规则（显式化，proposed DEC 由 Developer 返回 Coordinator）：
  L-A  V2 前导缺口（missing = {0..k-1}，链从 R{k} 起）+ 任务处于终态
       （completed）→ WARN（legacy 前导缺轮：闭任务后开始记录的 review 链）。
       中缝缺口或 ACTIVE 任务 → 保持 FAIL。
  L-B  V5 记录携带 legacy 格式键（``unresolved_blocks=``，无机器 token）
       + 任务终态 → WARN（旧 review 格式未迁移——格式化残留，非真实未解决
       blocker）。非 legacy 拼写 / 真实 nonzero 值 / ACTIVE 任务 → 保持 FAIL。
  L-C  Check 37：发布 tag 版本在 roadmap 状态列为终态发布（已发布/已撤回/
       失效/不可信）→ G-s1/G-s2 按 released mode WARN 披露（DEC-153 ②），
       不 retroactive FAIL（router v0.2.1 vs G4 pending——接入前发布旁路）。
       未发布（规划中/进行中）→ 保持 candidate FAIL。

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_review_closure_legacy.py -v
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw  # noqa: E402
from checks import review_domain as rd  # noqa: E402


# ── Router-derived legacy fixture (audit-148 §3.1) ─────────────────────

def _router_legacy_sequences():
    """Review evidence entries reconstructed from router archives.

    Each entry mirrors the evidence-log / review-file shape the live scan
    produces: ``{"id", "task_ref", "conclusion", "unresolved_blockers_fields"}``.
    """
    return [
        # ARCH-001: R1 NEEDS_CHANGE → R2 APPROVED_WITH_NOTES（无 R0）。
        {"id": "REVIEW-ARCH-001-R1", "task_ref": "ARCH-001",
         "conclusion": "NEEDS_CHANGE"},
        {"id": "REVIEW-ARCH-001-R2", "task_ref": "ARCH-001",
         "conclusion": "APPROVED_WITH_NOTES",
         "unresolved_blockers_fields": ["unresolved_blockers=0"]},
        # DEV-002: R1 APPROVED_WITH_NOTES（无 R0）。
        {"id": "REVIEW-DEV-002-R1", "task_ref": "DEV-002",
         "conclusion": "APPROVED_WITH_NOTES",
         "unresolved_blockers_fields": ["unresolved_blockers=0"]},
        # ARCH-002: 旧格式审查报告（unresolved_blocks= 拼写）。
        {"id": "REVIEW-ARCH-002", "task_ref": "ARCH-002",
         "conclusion": "APPROVED_WITH_NOTES",
         "unresolved_blockers_fields": ["unresolved_blocks=0"]},
    ]


_ROUTER_COMPLETED = {"ARCH-001": True, "ARCH-002": True, "DEV-002": True}


class LegacyLeadingGapRuleTests(unittest.TestCase):
    """L-A: V2 前导缺口 + 终态任务 → WARN（legacy）；边界保持 FAIL。"""

    def test_router_arch001_missing_r0_downgraded_to_warn(self):
        """ARCH-001 (R1→R2, 无 R0, 已完成) → 不再 FAIL——legacy 前导缺轮。"""
        r = vw.check_review_closure(
            review_sequence=_router_legacy_sequences(),
            plan_tracker_completed=_ROUTER_COMPLETED)
        v2 = [w for w in r["warnings"] if w["rule"] == "V2"
              and w["task_id"] == "ARCH-001"]
        self.assertTrue(v2, r["warnings"])
        self.assertIn("legacy leading round gap", v2[0]["reason"])
        self.assertEqual(
            [v for v in r["violations"] if v.get("task_id") == "ARCH-001"], [])

    def test_router_dev002_missing_r0_downgraded_to_warn(self):
        """DEV-002 (R1 终态, 无 R0, 已完成) → WARN。"""
        r = vw.check_review_closure(
            review_sequence=_router_legacy_sequences(),
            plan_tracker_completed=_ROUTER_COMPLETED)
        v2 = [w for w in r["warnings"] if w["rule"] == "V2"
              and w["task_id"] == "DEV-002"]
        self.assertTrue(v2, r["warnings"])

    def test_midchain_gap_on_active_task_stays_fail(self):
        """当前工作基准（FIX-006 类——ACTIVE 未完成）：R0→R2 中缝缺 R1
        → 仍 FAIL（不是 legacy 前导缺口）。"""
        seq = [
            {"id": "REVIEW-FIX-006-R0", "task_ref": "FIX-006",
             "conclusion": "NEEDS_CHANGE"},
            {"id": "REVIEW-FIX-006-R2", "task_ref": "FIX-006",
             "conclusion": "APPROVED_WITH_NOTES",
             "unresolved_blockers_fields": ["unresolved_blockers=0"]},
        ]
        r = vw.check_review_closure(
            review_sequence=seq, plan_tracker_completed={})
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn(
            "FIX-006",
            [v["task_id"] for v in r["violations"]
             if v["rule"] == "V2"])

    def test_leading_gap_on_noncompleted_task_stays_fail(self):
        """L-A fail-closed 边界：ACTIVE 任务链从 R1 起（缺 R0）→ 保持 FAIL
        —— 当前工作的记录缺口不是历史遗留。"""
        seq = [
            {"id": "REVIEW-FIX-007-R1", "task_ref": "FIX-007",
             "conclusion": "APPROVED_WITH_NOTES",
             "unresolved_blockers_fields": ["unresolved_blockers=0"]},
        ]
        r = vw.check_review_closure(
            review_sequence=seq, plan_tracker_completed={})
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("FIX-007",
                      [v["task_id"] for v in r["violations"]
                       if v["rule"] == "V2"])


class LegacyFormatTokenRuleTests(unittest.TestCase):
    """L-B: V5 legacy 格式键 + 终态任务 → WARN；真实 nonzero / 非 legacy → FAIL。"""

    def test_router_arch002_legacy_format_downgraded_to_warn(self):
        """ARCH-002（旧格式 unresolved_blocks=，已完成）→ V5 WARN（旧格式
        未迁移），不再是 "got invalid" FAIL。"""
        r = vw.check_review_closure(
            review_sequence=_router_legacy_sequences(),
            plan_tracker_completed=_ROUTER_COMPLETED)
        v5 = [w for w in r["warnings"] if w["rule"] == "V5"
              and w["task_id"] == "ARCH-002"]
        self.assertTrue(v5, r["warnings"])
        self.assertIn("unresolved_blocks", v5[0]["reason"])
        self.assertEqual(
            [v for v in r["violations"] if v.get("task_id") == "ARCH-002"], [])

    def test_completed_task_real_nonzero_blockers_stays_fail(self):
        """终态任务 + 真实 unresolved_blockers=2 → 仍 FAIL（L-B 不掩盖
        真实未解决 blocker）。"""
        seq = [
            {"id": "REVIEW-FIX-004-R0", "task_ref": "FIX-004",
             "conclusion": "APPROVED_WITH_NOTES",
             "unresolved_blockers_fields": ["unresolved_blockers=2"]},
        ]
        r = vw.check_review_closure(
            review_sequence=seq, plan_tracker_completed={"FIX-004": True})
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("FIX-004",
                      [v["task_id"] for v in r["violations"]
                       if v["rule"] == "V5"])

    def test_active_task_legacy_format_stays_fail(self):
        """L-B fail-closed 边界：ACTIVE 任务携带旧格式键 → 仍 FAIL（当前
        工作必须迁移到机器格式）。"""
        seq = [
            {"id": "REVIEW-FIX-008-R0", "task_ref": "FIX-008",
             "conclusion": "APPROVED_WITH_NOTES",
             "unresolved_blockers_fields": ["unresolved_blocks=0"]},
        ]
        r = vw.check_review_closure(
            review_sequence=seq, plan_tracker_completed={})
        self.assertEqual(r["verdict"], "FAIL")

    def test_legacy_nonzero_value_stays_fail(self):
        """P2-1（L-B fail-closed 边界）：legacy 拼写携带真实非零值
        （unresolved_blocks=2）→ 保持 FAIL——值必须解析，真实未解决
        blocker 不被降级 WARN。"""
        seq = [
            {"id": "REVIEW-FIX-009-R0", "task_ref": "FIX-009",
             "conclusion": "APPROVED_WITH_NOTES",
             "unresolved_blockers_fields": ["unresolved_blocks=2"]},
        ]
        r = vw.check_review_closure(
            review_sequence=seq, plan_tracker_completed={"FIX-009": True})
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("FIX-009",
                      [v["task_id"] for v in r["violations"]
                       if v["rule"] == "V5"])

    def test_canonical_invalid_with_legacy_key_stays_fail(self):
        """P2-1（invalid 不被 legacy 掩盖）：canonical 畸形 token
        （unresolved_blockers= 无值 → invalid）与 legacy 键并存 → 保持 FAIL，
        不得因 legacy 签名降级 WARN。"""
        seq = [
            {"id": "REVIEW-FIX-010-R0", "task_ref": "FIX-010",
             "conclusion": "APPROVED_WITH_NOTES",
             "unresolved_blockers_fields": [
                 "unresolved_blockers=", "unresolved_blocks=0"]},
        ]
        r = vw.check_review_closure(
            review_sequence=seq, plan_tracker_completed={"FIX-010": True})
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("FIX-010",
                      [v["task_id"] for v in r["violations"]
                       if v["rule"] == "V5"])

    def test_legacy_zero_value_still_downgrades_to_warn(self):
        """P2-1 回归确认：real legacy 空值（unresolved_blocks=0）+ 终态任务
        → 仍 WARN（旧 review 格式 un迁移，非真实未解决 blocker）。"""
        seq = [
            {"id": "REVIEW-FIX-011-R0", "task_ref": "FIX-011",
             "conclusion": "APPROVED_WITH_NOTES",
             "unresolved_blockers_fields": ["unresolved_blocks=0"]},
        ]
        r = vw.check_review_closure(
            review_sequence=seq, plan_tracker_completed={"FIX-011": True})
        self.assertEqual(r["verdict"], "WARN")
        self.assertTrue(
            [w for w in r["warnings"] if w["rule"] == "V5"
             and w["task_id"] == "FIX-011"], r["warnings"])

    def test_parser_annotates_legacy_key_without_matching_canonical(self):
        """解析器：legacy 键被标注 legacy_keys，且 canonical 拼写不误匹配
        （unresolved_blockers=0 不带 legacy 标注）。"""
        legacy = rd._parse_unresolved_blockers_fields(["unresolved_blocks=0"])
        self.assertEqual(legacy["status"], "missing")
        self.assertEqual(legacy["legacy_keys"], ["unresolved_blocks"])
        self.assertEqual(legacy.get("legacy_values"), [0])
        canonical = rd._parse_unresolved_blockers_fields(
            ["unresolved_blockers=0"])
        self.assertEqual(canonical["status"], "valid")
        self.assertEqual(canonical["legacy_keys"], [])

    def test_parser_annotates_legacy_nonzero_and_unparseable(self):
        """解析器（P2-1）：legacy 值被解析——非零和无法解析的 legacy 值
        分别标注（legacy_values / legacy_invalid_tokens），供 V5 规则判
        nonzero→FAIL。"""
        ev = rd._parse_unresolved_blockers_fields(
            ["unresolved_blocks=2, unresolved_blocks=abc"])
        self.assertEqual(ev["legacy_values"], [2])
        self.assertTrue(ev["legacy_invalid_tokens"])
        self.assertEqual(ev["status"], "missing")


class LegacyFixtureAggregateTests(unittest.TestCase):
    """审查器级断言：router legacy fixture 复跑 = 零违规（WARN 全部降级）；"
    "当前工作组合 fixture = FAIL 保留。"""

    def test_router_fixture_verdict_warn_zero_violations(self):
        """隔离 fixture（router legacy 行）复跑：verdict WARN、violations 空
        —— legacy 类全部降级（audit-148 §3.1 的 12 条 closure 违规不再 FAIL）。"""
        r = vw.check_review_closure(
            review_sequence=_router_legacy_sequences(),
            plan_tracker_completed=_ROUTER_COMPLETED)
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["violations"], [])
        self.assertGreaterEqual(len(r["warnings"]), 3)

    def test_current_work_mixed_fixture_keeps_fail(self):
        """混合 fixture（legacy 3 行 + 当前工作中缝缺口/真实 nonzero）：
        legacy 降级为 WARN，当前工作违规保持 FAIL。"""
        seq = _router_legacy_sequences() + [
            {"id": "REVIEW-FIX-006-R0", "task_ref": "FIX-006",
             "conclusion": "NEEDS_CHANGE"},
            {"id": "REVIEW-FIX-006-R2", "task_ref": "FIX-006",
             "conclusion": "APPROVED_WITH_NOTES",
             "unresolved_blockers_fields": ["unresolved_blockers=0"]},
        ]
        completed = dict(_ROUTER_COMPLETED)
        # FIX-006 是当前活跃（P0 待实施）——不在 completed。
        r = vw.check_review_closure(
            review_sequence=seq, plan_tracker_completed=completed)
        self.assertEqual(r["verdict"], "FAIL")
        legacy_fail = [v for v in r["violations"]
                       if v.get("task_id") in _ROUTER_COMPLETED]
        current_fail = [v for v in r["violations"]
                        if v.get("task_id") == "FIX-006"]
        self.assertEqual(legacy_fail, [])
        self.assertTrue(current_fail, r["violations"])


class LatestCandidateTagIgnoredTest(unittest.TestCase):
    """P2-3 隔离修正：L-C 检查针对 roadmap 中不存在的 tag（未发布版本）→
    candidate FAIL 保持（read 隔离于 tempdir，不读活数据）。"""

    _ROADMAP_NO_TARGET = (
        "## 版本规划\n\n"
        "| 版本 | 状态 | 预计日期 |\n"
        "| --- | --- | --- |\n"
        "| 0.77.0 | 已发布 | 2026-08-25 |\n"
    )

    def test_no_roadmap_candidate_still_fails(self):
        """P2-3：隔离 fixture（roadmap 无 v9.9.9）→ candidate FAIL 保持——
        released_history_exempt=False（不依赖活数据；不读本仓真实
        plan-tracker）。"""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tracker = Path(td) / "plan-tracker.md"
            tracker.write_text(self._ROADMAP_NO_TARGET, encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", tracker):
                r = vw.check_gate_sequence_for_release(
                    gates=_gates(), published_tags=[{"tag": "v9.9.9",
                                                     "date": "2026-08-22"}])
        self.assertEqual(r["verdict"], "FAIL")
        self.assertEqual(r["violations"][0]["rule"], "G-s2")
        self.assertEqual(r["stats"]["released_history_exempt"], False)


def _gates():
    """router 风格 lightweight gate 表（G4 pending，G5 发布）。"""
    return [
        {"gate": "G1", "transition": "立项→调研", "status": "passed-on-entry",
         "date": "2026-08-18", "evidence": "EV-001"},
        {"gate": "G2", "transition": "调研+选型→设计", "status": "passed-on-entry",
         "date": "2026-08-18", "evidence": "EV-001"},
        {"gate": "G3", "transition": "设计→开发", "status": "passed-on-entry",
         "date": "2026-08-18", "evidence": "EV-001"},
        {"gate": "G4", "transition": "开发+测试→CI", "status": "pending",
         "date": "", "evidence": ""},
        {"gate": "G5", "transition": "CI→发布", "status": "pending",
         "date": "", "evidence": ""},
        {"gate": "G6", "transition": "发布→运营", "status": "pending",
         "date": "", "evidence": ""},
        {"gate": "G7", "transition": "运营→维护", "status": "pending",
         "date": "", "evidence": ""},
    ]


# ── F-1/F-3（DESIGN R0）：live 路径状态列终态谓词 ──────────────────────

def _evidence_review_row(evd_id, task_ref, conclusion, tail=""):
    """Evidence-log REVIEW row（live 收集所需 ≥8 列形状）。"""
    cells = [evd_id, task_ref, "治理记录", "review-record CLI 机器写入 "
             "review 结论记录（{0}）".format(conclusion), "事实依据：机器写入",
             "review-{0}.md".format(evd_id.lower()), "Code Reviewer",
             "2026-08-26", "G11", conclusion]
    if tail:
        cells.append(tail)
    return "| " + " | ".join(cells) + " |\n"


class LiveCompletedPredicateShapeTests(unittest.TestCase):
    """F-1/F-3（DESIGN R0 BLOCKING）：live 路径（不传 plan_tracker_completed）
    按状态列 cell 终态判定，禁止整行子串扫描。

    形态覆盖：
      · 「✅ 完成 (date)」状态格行（本仓 FIX-162/169/... 语料形态）→ 终态
        ——legacy 型 V2 缺口降级 WARN（旧谓词漏识别 → 保持 FAIL，违反 G2 目标）；
      · 描述含「已完成」但状态=进行中的 ACTIVE 行 → 非终态——缺轮违规保持
        FAIL（旧谓词误识别 → WARN 掩盖当前工作缺口，违反 ACTIVE 恒 FAIL）。
    """

    _PLAN = (
        "# 计划\n\n"
        "### 优先级一览\n\n"
        "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
        "|--------|----|------|------|---------|---------|------|\n"
        "| **P1** | ARCH-001 | 旧架构任务 | — | 0.2.0 | closed | ✅ 完成 (2026-08-23) |\n"
        "| **P1** | FIX-006 | 已完成描述但活跃任务（P0 待实施） | — | 0.3.0 | open | ⏳ 待实施 |\n"
    )
    _EVIDENCE = (
        _evidence_review_row("REVIEW-ARCH-001-R1", "ARCH-001", "NEEDS_CHANGE")
        # ARCH-001 无 R0：R1→R2 链（legacy 前导缺口候选）
        + _evidence_review_row("REVIEW-ARCH-001-R2", "ARCH-001",
                               "APPROVED_WITH_NOTES", "unresolved_blockers=0")
        # FIX-006：R0→R2 中缝缺 R1（ACTIVE 违规候选）
        + _evidence_review_row("REVIEW-FIX-006-R0", "FIX-006", "NEEDS_CHANGE")
        + _evidence_review_row("REVIEW-FIX-006-R2", "FIX-006",
                               "APPROVED_WITH_NOTES", "unresolved_blockers=0")
    )

    def _live_run(self, plan=None, evidence=None):
        import tempfile
        plan = plan if plan is not None else self._PLAN
        evidence = evidence if evidence is not None else self._EVIDENCE
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            gov.mkdir()
            plan_path = gov / "plan-tracker.md"
            plan_path.write_text(plan, encoding="utf-8")
            evidence_path = gov / "evidence-log.md"
            evidence_path.write_text(evidence, encoding="utf-8")
            # live 路径（无参数）——completed 谓词经真实 plan-tracker 解析。
            with mock.patch.object(vw, "SAMPLE_PATH", plan_path), \
                 mock.patch.object(vw, "EVIDENCE_PATH", evidence_path), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov):
                r = vw.check_review_closure()
        return r

    def test_completed_cell_date_form_downgrades_legacy_chain(self):
        """「✅ 完成 (date)」状态格 → 终态：ARCH-001 R1→R2 缺 R0 → V2 WARN
        （旧谓词整行扫描漏识别「完成 (」形态 → 保持 FAIL——本用例锁住修复）。"""
        plan = (
            "# 计划\n\n"
            "### 优先级一览\n\n"
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
            "|--------|----|------|------|---------|---------|------|\n"
            "| **P1** | ARCH-001 | 旧架构任务 | — | 0.2.0 | closed | ✅ 完成 (2026-08-23) |\n"
        )
        evidence = (
            _evidence_review_row("REVIEW-ARCH-001-R1", "ARCH-001", "NEEDS_CHANGE")
            + _evidence_review_row("REVIEW-ARCH-001-R2", "ARCH-001",
                                   "APPROVED_WITH_NOTES", "unresolved_blockers=0")
        )
        r = self._live_run(plan=plan, evidence=evidence)
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["violations"], [])
        arch_v2 = [w for w in r["warnings"] if w["rule"] == "V2"
                   and w["task_id"] == "ARCH-001"]
        self.assertTrue(arch_v2, r["warnings"])
        self.assertIn("legacy leading round gap", arch_v2[0]["reason"])

    def test_active_row_with_completed_in_description_stays_fail(self):
        """描述含「已完成」但状态=待实施 → 非终态：FIX-006 中缝缺 R1 →
        FAIL 保持（老谓词子串扫描误识别 → WARN 掩盖——本用例锁住修复）。"""
        plan = (
            "# 计划\n\n"
            "### 优先级一览\n\n"
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
            "|--------|----|------|------|---------|---------|------|\n"
            "| **P1** | FIX-006 | 已完成描述但活跃任务（P0 待实施） | — | 0.3.0 | open | ⏳ 待实施 |\n"
        )
        evidence = (
            _evidence_review_row("REVIEW-FIX-006-R0", "FIX-006", "NEEDS_CHANGE")
            + _evidence_review_row("REVIEW-FIX-006-R2", "FIX-006",
                                   "APPROVED_WITH_NOTES", "unresolved_blockers=0")
        )
        r = self._live_run(plan=plan, evidence=evidence)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("FIX-006",
                      [v["task_id"] for v in r["violations"]
                       if v["rule"] == "V2"])


class MergePriorityTests(unittest.TestCase):
    """F-2（DESIGN R0 BLOCKING）：重复证据合并——valid 优先（canonical 值
    胜出），仅当两侧均无 valid token 时保留 legacy 标注。"""

    def test_valid_nonzero_beats_legacy_zero_left_missing(self):
        """left=legacy(0) right=canonical(2) → 合并后 valid value=2（真实
        nonzero 不被降级——F-2 红→绿）。"""
        left = rd._parse_unresolved_blockers_fields(["unresolved_blocks=0"])
        right = rd._parse_unresolved_blockers_fields(["unresolved_blockers=2"])
        merged = rd._merge_unresolved_blocker_evidence(left, right)
        self.assertEqual(merged["status"], "valid")
        self.assertEqual(merged["value"], 2)
        self.assertTrue(merged["legacy_keys"])  # 标注保留（透明）

    def test_valid_nonzero_beats_legacy_zero_right_missing(self):
        """反向：right=legacy(0) left=canonical(2) → 合并后 valid value=2。"""
        left = rd._parse_unresolved_blockers_fields(["unresolved_blockers=2"])
        right = rd._parse_unresolved_blockers_fields(["unresolved_blocks=0"])
        merged = rd._merge_unresolved_blocker_evidence(left, right)
        self.assertEqual(merged["status"], "valid")
        self.assertEqual(merged["value"], 2)

    def test_valid_zero_preserved_over_legacy(self):
        """合法 canonical 0 + 旧拼写 → 合并后 valid 0（满足机器契约的记录
        不被误降级——「无机器 token」前置条件保持）。"""
        left = rd._parse_unresolved_blockers_fields(["unresolved_blocks=0"])
        right = rd._parse_unresolved_blockers_fields(["unresolved_blockers=0"])
        merged = rd._merge_unresolved_blocker_evidence(left, right)
        self.assertEqual(merged["status"], "valid")
        self.assertEqual(merged["value"], 0)

    def test_both_missing_legacy_only_kept(self):
        """两侧均无 valid token（legacy-only）→ 合并保留 legacy 标注（L-B
        检测窗口保持——现有语义回归确认）。"""
        left = rd._parse_unresolved_blockers_fields(["unresolved_blocks=0"])
        right = rd._parse_unresolved_blockers_fields([])
        merged = rd._merge_unresolved_blocker_evidence(left, right)
        self.assertEqual(merged["status"], "missing")
        self.assertTrue(merged["legacy_keys"])


if __name__ == "__main__":
    unittest.main()
