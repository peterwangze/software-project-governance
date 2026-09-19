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


class HistoricalFileShapeTests(unittest.TestCase):
    """FIX-291 / FIX-281①（router EV-066：V2×9 + V5×2）：Check 30 对
    pre-FIX-174 文件式 review 记录的历史形状分类。

    形状定义：文件名匹配现行 review-{id}[-R{n}].md 约定，但内容为接入前
    手写报告（无 ``machine-written by review-record`` 首行标记、无机器
    ``- date:`` 字段）——本仓 29 个同形状实例（review-REL-007.md 等，
    2026-09-09 实测盘点）。此类记录进入轮次状态机后：

      · V2 轮次连续性——历史手写链的缺轮（含中缝缺口——L-A 仅覆盖前导）
        → 历史形状 WARN；
      · V5 APPROVED_WITH_NOTES 无机器 token / prose 附着零值
        （``unresolved_blockers=0，P0=0/…`` 全角逗号 artifact——router
        ARCH-002「got invalid」同型）→ 历史形状 WARN。

    边界锁定（不可破）：ACTIVE 任务恒 FAIL；真实 nonzero 恒 FAIL；
    现行机器格式（marker 完整）违规不得放宽。
    """

    @staticmethod
    def _handwritten_file(conclusion, extra_lines=()):
        """Pre-FIX-174 手写审查报告形状（无机器 marker / 无 - date: 字段）。"""
        lines = [
            "# 审查报告",
            "",
            "审查对象：目标产物直读；事实依据逐项核验。",
            "",
            "审查结论：**{0}**".format(conclusion),
            "",
        ]
        lines.extend(extra_lines)
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _machine_file(task, round_n, conclusion, extra_lines=()):
        """现行 review-record CLI 机器格式（marker + 结构字段齐全）。"""
        lines = [
            "# Review Record (machine-written by review-record)",
            "",
            "- task: {0}".format(task),
            "- round: R{0}".format(round_n),
            "- date: 2026-09-01",
            "- reviewer: rv",
            "- report: r.md",
            "- wiring: pending",
            "",
            "**审查结论**: **{0}**".format(conclusion),
        ]
        if conclusion == "APPROVED_WITH_NOTES":
            lines += ["", "unresolved_blockers=0"]
        lines.extend(extra_lines)
        lines.append("")
        return "\n".join(lines)

    _PLAN_HEADER = (
        "# 计划\n\n"
        "### 优先级一览\n\n"
        "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
        "|--------|----|------|------|---------|---------|------|\n"
    )

    def _live_run(self, plan_rows, files):
        """live 路径（temp .governance + 真实文件扫描——分类只发生在 live
        文件通道，fixture 注入路径无法覆盖 source_format 分类）。"""
        import tempfile
        plan = self._PLAN_HEADER + "".join(plan_rows)
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            gov.mkdir()
            (gov / "plan-tracker.md").write_text(plan, encoding="utf-8")
            (gov / "evidence-log.md").write_text("", encoding="utf-8")
            for name, text in files.items():
                (gov / name).write_text(text, encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", gov / "plan-tracker.md"), \
                 mock.patch.object(vw, "EVIDENCE_PATH", gov / "evidence-log.md"), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov):
                r = vw.check_review_closure()
        return r

    # ── V2：历史文件链缺轮 → WARN ─────────────────────────────────────

    def test_historical_file_midchain_gap_downgrades_to_warn(self):
        """历史手写链中缝缺轮（R0+R2，缺 R1——L-A 仅覆盖前导）+ 终态任务
        → V2 WARN（红→绿：现行判 FAIL）。"""
        r = self._live_run(
            ["| **P1** | ARCH-101 | 旧任务 | — | 0.2.0 | closed | "
             "✅ 完成 (2026-08-01) |\n"],
            {
                "review-ARCH-101-R0.md": self._handwritten_file("NEEDS_CHANGE"),
                "review-ARCH-101-R2.md": self._handwritten_file(
                    "APPROVED_WITH_NOTES"),
            })
        self.assertEqual(r["verdict"], "WARN", r["violations"])
        v2 = [w for w in r["warnings"] if w["rule"] == "V2"
              and w["task_id"] == "ARCH-101"]
        self.assertTrue(v2, r["warnings"])
        self.assertIn("historical", v2[0]["reason"])
        self.assertEqual(
            [v for v in r["violations"] if v.get("task_id") == "ARCH-101"], [])

    def test_historical_file_leading_gap_on_mixed_terminal_status_warns(self):
        """router V2×9 等效复合形态：W-7 混合终态格（「🔄 进行中 → ✅ 已发布」
        ——旧谓词判 ACTIVE）+ 历史手写链前导缺轮 → WARN（红→绿：
        W-7 与历史形状分类两修复共同生效）。

        归因注记（CODE-R0 P3-4）：本用例**有意耦合两个修复**（W-7 谓词
        flip 使任务进 completed 集 + A 子项历史形状门降级）——router 复合
        形态等效是其目的；单独回归定位时见
        W7TerminalSegmentScopeTests（谓词面）与
        test_historical_file_midchain_gap_downgrades_to_warn（分类面）。"""
        r = self._live_run(
            ["| **P1** | ARCH-103 | 发布任务 | — | 0.2.0 | closed | "
             "🔄 进行中 (2026-08-23)——已派发 → **✅ 已发布 (2026-08-23)** |\n"],
            {
                "review-ARCH-103-R1.md": self._handwritten_file("NEEDS_CHANGE"),
                "review-ARCH-103-R2.md": self._handwritten_file(
                    "APPROVED_WITH_NOTES"),
            })
        self.assertEqual(r["verdict"], "WARN", r["violations"])
        v2 = [w for w in r["warnings"] if w["rule"] == "V2"
              and w["task_id"] == "ARCH-103"]
        self.assertTrue(v2, r["warnings"])
        self.assertEqual(r["violations"], [])

    # ── V5：历史文件无机器 token / prose 附着零值 → WARN ──────────────

    def test_historical_file_v5_missing_token_downgrades_to_warn(self):
        """历史手写文件 APPROVED_WITH_NOTES 无任何 blocker token（无日期
        字段——FIX-233 日期豁免无法生效）+ 终态任务 → V5 WARN（红→绿）。"""
        r = self._live_run(
            ["| **P1** | ARCH-102 | 旧任务 | — | 0.2.0 | closed | "
             "✅ 完成 (2026-08-01) |\n"],
            {"review-ARCH-102.md": self._handwritten_file("APPROVED_WITH_NOTES")})
        self.assertEqual(r["verdict"], "WARN", r["violations"])
        v5 = [w for w in r["warnings"] if w["rule"] == "V5"
              and w["task_id"] == "ARCH-102"]
        self.assertTrue(v5, r["warnings"])
        self.assertIn("historical", v5[0]["reason"])

    def test_historical_file_v5_prose_attached_zero_downgrades_to_warn(self):
        """router ARCH-002 同型「got invalid」：历史手写文件携带
        ``unresolved_blockers=0，P0=0/…``（全角逗号 prose 附着——解析器
        判 invalid）→ 可证零值 → V5 WARN（红→绿）。"""
        r = self._live_run(
            ["| **P1** | ARCH-104 | 旧任务 | — | 0.2.0 | closed | "
             "✅ 完成 (2026-08-01) |\n"],
            {"review-ARCH-104.md": self._handwritten_file(
                "APPROVED_WITH_NOTES",
                ["（unresolved_blockers=0，P0=0/P1=0/P2×1）——备注 prose"])}
        )
        self.assertEqual(r["verdict"], "WARN", r["violations"])
        v5 = [w for w in r["warnings"] if w["rule"] == "V5"
              and w["task_id"] == "ARCH-104"]
        self.assertTrue(v5, r["warnings"])

    # ── 边界锁定：ACTIVE / 真实 nonzero / 现行机器格式恒 FAIL ─────────

    def test_historical_file_gap_on_active_task_stays_fail(self):
        """边界：ACTIVE（⏳ 待执行）任务的历史形状链缺轮 → 恒 FAIL。"""
        r = self._live_run(
            ["| **P1** | ARCH-105 | 活跃任务 | — | 0.3.0 | open | "
             "⏳ 待执行 |\n"],
            {
                "review-ARCH-105-R1.md": self._handwritten_file("NEEDS_CHANGE"),
                "review-ARCH-105-R2.md": self._handwritten_file(
                    "APPROVED_WITH_NOTES"),
            })
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("ARCH-105",
                      [v["task_id"] for v in r["violations"] if v["rule"] == "V2"])

    def test_historical_file_v5_nonzero_stays_fail(self):
        """边界：历史文件携带真实 nonzero（unresolved_blockers=2）→ 恒 FAIL。"""
        r = self._live_run(
            ["| **P1** | ARCH-106 | 旧任务 | — | 0.2.0 | closed | "
             "✅ 完成 (2026-08-01) |\n"],
            {"review-ARCH-106.md": self._handwritten_file(
                "APPROVED_WITH_NOTES", ["unresolved_blockers=2"])})
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("ARCH-106",
                      [v["task_id"] for v in r["violations"] if v["rule"] == "V5"])

    def test_machine_file_gap_stays_fail(self):
        """边界：现行机器格式（marker + date 字段齐全）链缺轮 → 不得因
        历史形状逻辑放宽——恒 FAIL。"""
        r = self._live_run(
            ["| **P1** | ARCH-107 | 新任务 | — | 0.4.0 | open | "
             "✅ 完成 (2026-09-02) |\n"],
            {
                "review-ARCH-107-R0.md": self._machine_file(
                    "ARCH-107", 0, "APPROVED"),
                "review-ARCH-107-R2.md": self._machine_file(
                    "ARCH-107", 2, "APPROVED_WITH_NOTES"),
            })
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("ARCH-107",
                      [v["task_id"] for v in r["violations"] if v["rule"] == "V2"])

    def test_router_ev066_equivalent_aggregate_warns(self):
        """router EV-066 等效聚合 fixture：V2（前导缺轮）+ V2（中缝缺轮）
        + V5（无 token）+ V5（prose 零值）四形态 → 全 WARN、零违规。"""
        r = self._live_run(
            [
                "| **P1** | ARCH-110 | 旧任务A | — | 0.2.0 | closed | "
                "✅ 完成 (2026-08-01) |\n",
                "| **P1** | ARCH-111 | 旧任务B | — | 0.2.0 | closed | "
                "✅ 完成 (2026-08-01) |\n",
                "| **P1** | ARCH-112 | 旧任务C | — | 0.2.0 | closed | "
                "✅ 已关闭 (2026-08-01) |\n",
                "| **P1** | ARCH-113 | 旧任务D | — | 0.2.0 | closed | "
                "✅ 完成 (2026-08-01) |\n",
            ],
            {
                "review-ARCH-110-R1.md": self._handwritten_file("NEEDS_CHANGE"),
                "review-ARCH-110-R2.md": self._handwritten_file(
                    "APPROVED_WITH_NOTES"),
                "review-ARCH-111-R0.md": self._handwritten_file("NEEDS_CHANGE"),
                "review-ARCH-111-R2.md": self._handwritten_file(
                    "APPROVED_WITH_NOTES"),
                "review-ARCH-112.md": self._handwritten_file(
                    "APPROVED_WITH_NOTES"),
                "review-ARCH-113.md": self._handwritten_file(
                    "APPROVED_WITH_NOTES",
                    ["（unresolved_blockers=0，P0=0/P2×1）prose 附着"]),
            })
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["violations"], [])
        downgraded = {w["task_id"] for w in r["warnings"]}
        self.assertTrue({"ARCH-110", "ARCH-111", "ARCH-112", "ARCH-113"}
                        <= downgraded, r["warnings"])


class ReworkR1BoundaryTests(unittest.TestCase):
    """FIX-291 R1 返工（review-FIX-291-DESIGN-R0 P1-1/P2-1/P3-1 + CODE-R0
    P2-2/P3-1 交叉印证）：provably-zero 证明标准收窄 + 行通道 source_format
    分类 + 歧义值边界锚定。

    P1-1（Design blocker）：``_PROVABLY_ZERO_TOKEN_RE`` 只证前导数字为 0、
    不证附着细目无 blocker——``unresolved_blockers=0，P1×1``（本仓 FIX-254
    live evidence 行同形状：结构 token 报 0、细目报 P1 nonzero——自相矛盾）
    若处于 historical 文件形状 + completed 任务会被降级 WARN，违背 L-B
    「可证为空」标准与「真实 nonzero 恒 FAIL」锁定字面。修复 = 负向前瞻：
    附着细目含 nonzero P0/P1 计数即拒绝（P2/P3 nonzero 不影响——非阻塞级）。
    """

    @staticmethod
    def _handwritten_file(conclusion, extra_lines=()):
        lines = [
            "# 审查报告",
            "",
            "审查对象：目标产物直读；事实依据逐项核验。",
            "",
            "审查结论：**{0}**".format(conclusion),
            "",
        ]
        lines.extend(extra_lines)
        lines.append("")
        return "\n".join(lines)

    _PLAN_HEADER = (
        "# 计划\n\n"
        "### 优先级一览\n\n"
        "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
        "|--------|----|------|------|---------|---------|------|\n"
    )

    def _live_run(self, plan_rows, files):
        import tempfile
        plan = self._PLAN_HEADER + "".join(plan_rows)
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            gov.mkdir()
            (gov / "plan-tracker.md").write_text(plan, encoding="utf-8")
            (gov / "evidence-log.md").write_text("", encoding="utf-8")
            for name, text in files.items():
                (gov / name).write_text(text, encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", gov / "plan-tracker.md"), \
                 mock.patch.object(vw, "EVIDENCE_PATH", gov / "evidence-log.md"), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov):
                r = vw.check_review_closure()
        return r

    # ── P1-1：nonzero P0/P1 细目拒绝 provably-zero（红→绿） ───────────

    def test_historical_file_v5_p1_nonzero_detail_stays_fail(self):
        """红字面配置（MUST）：FIX-254 live 形状
        ``unresolved_blockers=0，P0=0/P1×1/P2×3/P3×5`` ——结构 token 报 0
        而细目报 P1 nonzero（自相矛盾）→ 不可证为空 → 恒 FAIL。"""
        r = self._live_run(
            ["| **P1** | ARCH-120 | 旧任务 | — | 0.2.0 | closed | "
             "✅ 完成 (2026-08-01) |\n"],
            {"review-ARCH-120.md": self._handwritten_file(
                "APPROVED_WITH_NOTES",
                ["（unresolved_blockers=0，P0=0/P1×1/P2×3/P3×5，共 9 发现）"])}
        )
        self.assertEqual(r["verdict"], "FAIL", r["warnings"])
        self.assertIn("ARCH-120",
                      [v["task_id"] for v in r["violations"]
                       if v["rule"] == "V5"])

    def test_historical_file_v5_p0_nonzero_detail_stays_fail(self):
        """P1-1 同型：``P0=1`` nonzero 细目 → 恒 FAIL。"""
        r = self._live_run(
            ["| **P1** | ARCH-121 | 旧任务 | — | 0.2.0 | closed | "
             "✅ 完成 (2026-08-01) |\n"],
            {"review-ARCH-121.md": self._handwritten_file(
                "APPROVED_WITH_NOTES",
                ["（unresolved_blockers=0，P0=1/P1=0）说明 prose"])}
        )
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("ARCH-121",
                      [v["task_id"] for v in r["violations"]
                       if v["rule"] == "V5"])

    def test_historical_file_v5_all_zero_with_p2_nonzero_still_warns(self):
        """绿字面配置（回归锚定）：全零 P0/P1 + P2 nonzero（非阻塞级）
        ``unresolved_blockers=0，P0=0/P1=0/P2=3`` → 继续降级 WARN。"""
        r = self._live_run(
            ["| **P1** | ARCH-122 | 旧任务 | — | 0.2.0 | closed | "
             "✅ 完成 (2026-08-01) |\n"],
            {"review-ARCH-122.md": self._handwritten_file(
                "APPROVED_WITH_NOTES",
                ["（unresolved_blockers=0，P0=0/P1=0/P2=3/P3=2）"])}
        )
        self.assertEqual(r["verdict"], "WARN", r["violations"])
        v5 = [w for w in r["warnings"] if w["rule"] == "V5"
              and w["task_id"] == "ARCH-122"]
        self.assertTrue(v5, r["warnings"])

    def test_parser_p1_nonzero_detail_not_provably_zero(self):
        """解析器直测：``=0，P1×1`` / ``=0，P0=1`` 附着 → 非 provably-zero。"""
        for field in ("unresolved_blockers=0，P1×1",
                      "unresolved_blockers=0，P0=1/P1=0",
                      "unresolved_blockers=0，P0 = 2 后续"):
            ev = rd._parse_unresolved_blockers_fields([field])
            self.assertEqual(ev["status"], "invalid", field)
            self.assertFalse(
                rd._blocker_evidence_provably_zero(ev), field)

    # ── P3-1（Design 测试缺口 + Code 边界收窄）── 歧义值 fail-closed ──

    def test_parser_ambiguous_values_not_provably_zero(self):
        """歧义 prose 值 fail-closed 锚定（Design P3-1 补 2 例）：
        ``10，``（前导非 0）/ ``02，``（0 后随数字）→ 恒非 provably-zero。"""
        for field in ("unresolved_blockers=10，P0=0", "unresolved_blockers=02，x"):
            ev = rd._parse_unresolved_blockers_fields([field])
            self.assertFalse(
                rd._blocker_evidence_provably_zero(ev), field)

    def test_parser_ascii_letter_attachment_not_provably_zero(self):
        """Code P3-1 收窄：``0abc`` 类 ASCII 字母附着（token 边界锚定）
        → 非 provably-zero；CJK 附着（0件）与全角逗号附着保持可证零。"""
        ev = rd._parse_unresolved_blockers_fields(
            ["unresolved_blockers=0abc"])
        self.assertEqual(ev["status"], "invalid")
        self.assertFalse(rd._blocker_evidence_provably_zero(ev))
        for ok_field in ("unresolved_blockers=0件", "unresolved_blockers=0，P0=0"):
            ev_ok = rd._parse_unresolved_blockers_fields([ok_field])
            if ev_ok["status"] == "invalid":
                self.assertTrue(
                    rd._blocker_evidence_provably_zero(ev_ok), ok_field)

    # ── P2-1(Design)≡P2-2(Code)：机录行击穿历史分类（红→绿） ─────────

    def test_machine_row_contribution_breaks_historical_classification(self):
        """同轮「review-record 机录行 + historical 手写文件」→ 该轮
        machine（rank 2），全轮 historical 不成立 → 中缝缺口恒 FAIL
        （现行格式贡献 MUST 击穿 provably-historical 分类——R0 行通道
        缺省 unknown(0) 不设防，本用例锁住修复）。"""
        machine_row = (
            "| REVIEW-ARCH-123-R0 | ARCH-123 | 治理记录 | review-record CLI "
            "机器写入 review 结论记录（round 0） | 事实依据：review-record "
            "输出摘要（机器写入） | r.md; review-ARCH-123-R0.md | rv | "
            "2026-09-01 | G11 | NEEDS_CHANGE |"
        )
        import tempfile
        plan = (self._PLAN_HEADER +
                "| **P1** | ARCH-123 | 任务 | — | 0.4.0 | open | "
                "✅ 完成 (2026-09-02) |\n")
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            gov.mkdir()
            (gov / "plan-tracker.md").write_text(plan, encoding="utf-8")
            (gov / "evidence-log.md").write_text(machine_row + "\n",
                                                 encoding="utf-8")
            (gov / "review-ARCH-123-R0.md").write_text(
                self._handwritten_file("NEEDS_CHANGE"), encoding="utf-8")
            (gov / "review-ARCH-123-R2.md").write_text(
                self._handwritten_file("APPROVED_WITH_NOTES"),
                encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", gov / "plan-tracker.md"), \
                 mock.patch.object(vw, "EVIDENCE_PATH", gov / "evidence-log.md"), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov):
                r = vw.check_review_closure()
        self.assertEqual(r["verdict"], "FAIL", r["warnings"])
        self.assertIn("ARCH-123",
                      [v["task_id"] for v in r["violations"]
                       if v["rule"] == "V2"])


# ── FIX-355：归档感知终态门（REL-080 发布阻塞：Check 30 V2×2） ────────────

class ArchiveAwareTerminalGateTests(unittest.TestCase):
    """FIX-355：Check 30 终态豁免门合并归档 Task 索引。

    缺陷（REL-080 发布阻塞）：``completed`` 仅从活体 plan-tracker 派生——
    任务行被 ``archive.py`` 迁移出热文件后，任务从 tracker 消失而审查链仍留
    在 evidence-log，于是真实已闭环任务的历史前导缺口重新判 FAIL
    （REL-078「missing R[0]」在 0.83.0 归档迁移移走其任务行后复发）。

    归档语义 = 完结入册（不是「从未存在」），故归档索引是终态的第二来源。
    边界（不可破）：
      · 豁免仅限「归档行状态格证明终态」——索引缺行/状态非终态 → 保持 FAIL；
      · 活体行权威——tracker 仍显示 ACTIVE 的任务不得被陈旧归档行豁免
        （沿用 FIX-341 归档索引解析序「热表行权威」）；
      · V1 破链面（「非终态但任务已标记完成」）不进归档集——它断言的是
        **当前工作**的闭环缺口，喂入归档历史会造出 7 个新 FAIL（实测：
        Check 30 2→8 violations，历史遗留 UNKNOWN 轮结论全部翻红）。

    零回归：archive/index.md 不存在/不可读 → 归档集为空 → 与 FIX-355 前
    完全同判（既有 LiveCompletedPredicateShapeTests 全部在无 archive 的
    temp .governance 下运行，即该路径的持续看护）。
    """

    _PLAN_HEADER = (
        "# 计划\n\n"
        "### 优先级一览\n\n"
        "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
        "|--------|----|------|------|---------|---------|------|\n"
    )

    #: 真实 ``archive/index.md`` 行形态（REL-078 语料逐字同型）：状态格以
    #: 「完成 (date)」断言开头，正文含「候选」——该词此处指**候选提交**
    #: （candidate commit），不是非终态状态。这正是 FIX-341 的保守谓词
    #: （``_ARCHIVE_NON_COMPLETED_MARKERS`` 含「候选」）会误判 False、
    #: 而 ``_status_is_completed_cell`` 正确判 True 的形态。
    _ARCHIVE_INDEX = (
        "# 归档索引\n\n"
        "## Task 索引\n\n"
        "| Task ID | 状态 | 版本 | 归档文件 |\n"
        "|---------|------|------|---------|\n"
        "| REL-178 | 完成 (2026-09-17)——**M-1~M-8 全链闭环**（日期勘误："
        "taggerdate 权威）：候选 `3f4c534`（M-1 冻结 + M-3 双半面 R0→R1 全 "
        "APPROVED_WITH_NOTES/0，机录 REVIEW-REL-178-R1~R4）→ M-5 transition "
        "`b63584c`（candidate→released + tag `v0.82.0`）→ M-7 push → M-8 归档"
        "迁移（22 项 evidence，integrity PASS）。EVD-1060/1061/1062 | "
        "0.82.0 | archive/tasks/v0.1.0~v0.82.0.md |\n"
    )

    _ARCHIVED_PLAN_ROW = (
        "| **P1** | REL-178 | 发布任务（行已归档迁移出热文件） | — | 0.82.0 | "
        "closed | ⏳ 待执行 |\n"
    )

    def _live_run(self, plan_rows, evidence, archive_index=None):
        """live 路径：temp ``.governance`` + 真实文件扫描（``completed`` 与归档
        索引均经真实 I/O 派生——fixture 注入路径无法覆盖归档合并）。"""
        import tempfile
        plan = self._PLAN_HEADER + "".join(plan_rows)
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            gov.mkdir()
            (gov / "plan-tracker.md").write_text(plan, encoding="utf-8")
            (gov / "evidence-log.md").write_text(evidence, encoding="utf-8")
            if archive_index is not None:
                (gov / "archive").mkdir()
                (gov / "archive" / "index.md").write_text(
                    archive_index, encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", gov / "plan-tracker.md"), \
                 mock.patch.object(vw, "EVIDENCE_PATH", gov / "evidence-log.md"), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov):
                r = vw.check_review_closure()
        return r

    @staticmethod
    def _leading_gap_evidence(task_id="REL-178"):
        """链从 R1 起（无 R0）——LEADING gap，L-A 豁免候选形态。"""
        return _evidence_review_row(
            "REVIEW-{0}-R1".format(task_id), task_id,
            "APPROVED_WITH_NOTES", "unresolved_blockers=0")

    def _v2(self, result, task_id="REL-178", bucket="warnings"):
        return [x for x in result[bucket]
                if x["rule"] == "V2" and x["task_id"] == task_id]

    # ── 核心验收：归档终态任务的前导缺口 → WARN（红→绿） ───────────────

    def test_archived_closed_task_leading_gap_downgrades_to_warn(self):
        """归档索引「完成」行 + tracker 无该任务行 + 链从 R1 起 → WARN
        （REL-078 形态；修复前 FAIL——本用例锁住修复）。"""
        r = self._live_run([], self._leading_gap_evidence(),
                           archive_index=self._ARCHIVE_INDEX)
        self.assertEqual(r["violations"], [], r["violations"])
        self.assertEqual(r["verdict"], "WARN")
        v2 = self._v2(r)
        self.assertTrue(v2, r["warnings"])
        self.assertIn("legacy leading round gap", v2[0]["reason"])
        self.assertIn("closed task", v2[0]["reason"])

    def test_archived_closed_task_leading_gap_ignores_unrelated_live_rows(self):
        """归档合并与活体行解析共存：另一 ACTIVE 任务行在场（live_active 非
        空）时，归档任务的豁免照常生效。"""
        r = self._live_run(
            ["| **P1** | FIX-900 | 无关活跃任务 | — | 0.4.0 | open | "
             "⏳ 待实施 |\n"],
            self._leading_gap_evidence(),
            archive_index=self._ARCHIVE_INDEX)
        self.assertEqual(r["violations"], [], r["violations"])
        self.assertTrue(self._v2(r), r["warnings"])

    # ── 零回归：索引缺失 → 与 FIX-355 前同判 ──────────────────────────

    def test_missing_archive_index_keeps_leading_gap_fail(self):
        """零回归路径：``archive/index.md`` 不存在 → 归档集为空 → 既非活体
        终态亦非归档终态的任务前导缺口保持 FAIL（FIX-355 前行为逐字不变）。"""
        r = self._live_run([], self._leading_gap_evidence())
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("REL-178",
                      [v["task_id"] for v in r["violations"]
                       if v["rule"] == "V2"])

    def test_archive_row_without_terminal_assertion_stays_fail(self):
        """fail-closed：归档行存在但状态格未证明终态（候选/进行中）→
        不豁免 → 保持 FAIL（豁免依据是逐任务终态断言，不是「行存在」）。"""
        index = (
            "# 归档索引\n\n"
            "## Task 索引\n\n"
            "| Task ID | 状态 | 版本 | 归档文件 |\n"
            "|---------|------|------|---------|\n"
            "| REL-178 | 候选（未发布）——M-1 冻结中 | 0.82.0 | a.md |\n"
        )
        r = self._live_run([], self._leading_gap_evidence(),
                          archive_index=index)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("REL-178",
                      [v["task_id"] for v in r["violations"]
                       if v["rule"] == "V2"])

    # ── fail-closed 边界：ACTIVE 恒 FAIL（活体行权威） ────────────────

    def test_live_active_row_outranks_stale_archive_row(self):
        """活体行权威：tracker 仍显示 ⏳ 待执行的任务，即使归档索引有「完成」
        行（陈旧/重开形态）也不得豁免 → 前导缺口保持 FAIL（沿用 FIX-341
        「热表行权威」解析序；FIX-355 前该形态同样 FAIL——零回归）。"""
        r = self._live_run([self._ARCHIVED_PLAN_ROW],
                           self._leading_gap_evidence(),
                           archive_index=self._ARCHIVE_INDEX)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("REL-178",
                      [v["task_id"] for v in r["violations"]
                       if v["rule"] == "V2"])

    def test_archive_index_rows_are_not_a_live_completed_source(self):
        """归档集不进 V1 破链面：归档终态任务 + 链终态 NEEDS_CHANGE（R0 在，
        非前导缺口）→ V1 WARN（非 FAIL）。锁住实测回归——把归档集喂进 V1 会
        让历史遗留轮结论（AUDIT-112/FIX-065/…/FIX-120 同型）全部翻红，
        Check 30 由 2 涨到 8 violations。"""
        r = self._live_run(
            [],
            _evidence_review_row("REVIEW-REL-178-R0", "REL-178",
                                 "NEEDS_CHANGE"),
            archive_index=self._ARCHIVE_INDEX)
        self.assertEqual([v for v in r["violations"] if v["rule"] == "V1"], [],
                         r["violations"])
        v1 = [w for w in r["warnings"]
              if w["rule"] == "V1" and w["task_id"] == "REL-178"]
        self.assertTrue(v1, r["warnings"])
        self.assertIn("not yet completed", v1[0]["reason"])

    # ── 索引节边界（load-bearing） ────────────────────────────────────

    def test_archive_section_boundary_ignores_other_index_sections(self):
        """只认 ``## Task 索引`` 节：Evidence 索引节里形态完全合格的行
        （``REL-903 | 已完成``）不得进入 completed 集。"""
        index = (
            "# 归档索引\n\n"
            "## Task 索引\n\n"
            "| Task ID | 状态 | 版本 | 归档文件 |\n"
            "|---------|------|------|---------|\n"
            "| FIX-901 | 已完成 (2026-01-01) | 0.1.0 | a.md |\n"
            "| FIX-902 | ⏳ 待执行 | 0.1.0 | a.md |\n\n"
            "## Evidence 索引\n\n"
            "| EVD-ID | Task | 归档文件 |\n"
            "|--------|------|---------|\n"
            "| EVD-901 | FIX-903 | b.md |\n"
            "| REL-903 | 已完成 (2026-01-01) | b.md |\n"
        )
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            (gov / "archive").mkdir(parents=True)
            (gov / "archive" / "index.md").write_text(index, encoding="utf-8")
            with mock.patch.object(vw, "GOVERNANCE_DIR", gov):
                ids = rd._archived_completed_task_ids()
        self.assertEqual(ids, {"FIX-901"})

    def test_archive_predicate_beats_fix341_conservative_veto(self):
        """谓词口径锁定：FIX-341 的 ``parse_archive_index_completed_ids``
        因「候选」否决词判 False，而 Check 30 的终态判定用
        ``_status_is_completed_cell`` 判 True——两者回答不同问题
        （依赖是否满足 vs 任务是否终态），本修复取后者。"""
        from task_priority import parse_archive_index_completed_ids
        self.assertFalse(
            parse_archive_index_completed_ids(self._ARCHIVE_INDEX) >= {"REL-178"}
            and "REL-178" in parse_archive_index_completed_ids(
                self._ARCHIVE_INDEX))
        self.assertTrue(
            vw._status_is_completed_cell(
                "完成 (2026-09-17)——候选 `3f4c534`（M-5 transition）"))


class TerminalExemptionCauseSplitTests(unittest.TestCase):
    """FIX-357：Check 30 终态豁免行因果断言按来源分流。

    缺陷（review-FIX-355-CODE-R0 C-01，源判 P1）：4 个终态豁免门（V2 L-A /
    V2 historical-shape / V5 legacy-key / V5 historical-shape）都以
    ``task_id in closed`` 触发，但 ``closed`` 有两个因果来源——
      · 归档依据豁免：id 仅经归档 Task 索引进入 ``closed``（FIX-355 合并：
        closed = completed ∪ (archived − live_active)，DEC-214②）——
        tracker 行已迁移，归档终态行即完结证据；
      · 活体行终态恢复豁免：活体 plan-tracker 行自身断言终态
        （id ∈ completed）——EVD-892 在案登记修复，非补造。
    修复前两类豁免行共用同一措辞模板，读者无法区分「任务已归档故豁免」
    与「活体行终态恢复故豁免」（披露失真）。

    修复边界（不可破）：判定逻辑零改动（closed 集派生 / 4 门结构 / V1~V5
    口径不变）；分流集中单一模板映射函数
    ``_terminal_exemption_cause_clause``，不与判定逻辑耦合；
    fail-safe 路径（fixture / tracker 不可读 / 索引缺失，closed == completed）
    一律归类 live——无归档贡献就不得声称归档依据。
    """

    _PLAN_HEADER = (
        "# 计划\n\n"
        "### 优先级一览\n\n"
        "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
        "|--------|----|------|------|---------|---------|------|\n"
    )

    #: 真实归档索引行形态（与 FIX-355 用例同型——「完成 (date)」终态断言）。
    _ARCHIVE_INDEX = (
        "# 归档索引\n\n"
        "## Task 索引\n\n"
        "| Task ID | 状态 | 版本 | 归档文件 |\n"
        "|---------|------|------|---------|\n"
        "| REL-178 | 完成 (2026-09-17)——**M-1~M-8 全链闭环**（日期勘误："
        "taggerdate 权威）：候选 `3f4c534`（M-1 冻结 + M-3 双半面 R0→R1 全 "
        "APPROVED_WITH_NOTES/0，机录 REVIEW-REL-178-R1~R4）→ M-5 transition "
        "`b63584c`（candidate→released + tag `v0.82.0`）→ M-7 push → M-8 归档"
        "迁移（22 项 evidence，integrity PASS）。EVD-1060/1061/1062 | "
        "0.82.0 | archive/tasks/v0.1.0~v0.82.0.md |\n"
    )

    #: 活体终态行（tracker 仍持行、状态格断言完成——EVD-892 活体恢复形态）。
    _LIVE_COMPLETED_ROW = (
        "| **P1** | REL-178 | 已闭环（活体行终态恢复） | — | 0.4.0 | "
        "closed | ✅ 完成 (2026-08-20) |\n"
    )

    def _live_run(self, plan_rows, evidence, archive_index=None):
        """live 路径：temp ``.governance`` + 真实文件扫描（与 FIX-355 用例
        同构——``completed``/``closed`` 均经真实 I/O 派生）。"""
        import tempfile
        plan = self._PLAN_HEADER + "".join(plan_rows)
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            gov.mkdir()
            (gov / "plan-tracker.md").write_text(plan, encoding="utf-8")
            (gov / "evidence-log.md").write_text(evidence, encoding="utf-8")
            if archive_index is not None:
                (gov / "archive").mkdir()
                (gov / "archive" / "index.md").write_text(
                    archive_index, encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", gov / "plan-tracker.md"), \
                 mock.patch.object(vw, "EVIDENCE_PATH", gov / "evidence-log.md"), \
                 mock.patch.object(vw, "GOVERNANCE_DIR", gov):
                r = vw.check_review_closure()
        return r

    @staticmethod
    def _leading_gap_evidence(task_id="REL-178"):
        """链从 R1 起（无 R0）——V2 L-A 豁免门候选形态。"""
        return _evidence_review_row(
            "REVIEW-{0}-R1".format(task_id), task_id,
            "APPROVED_WITH_NOTES", "unresolved_blockers=0")

    @staticmethod
    def _legacy_token_evidence(task_id="REL-178"):
        """R0 终态 APPROVED_WITH_NOTES + 旧格式 ``unresolved_blocks=0``
        token——V5 legacy-key 豁免门候选形态（canonical 拼写不匹配 →
        status=missing + legacy_keys 非空）。"""
        return _evidence_review_row(
            "REVIEW-{0}".format(task_id), task_id,
            "APPROVED_WITH_NOTES", "unresolved_blocks=0")

    # ── 单元面：来源分类器 + 模板映射（单一可单测函数） ────────────────

    def test_classifier_archive_basis(self):
        """仅经归档侧进入门集（closed 有、completed 无）→ "archive"。"""
        self.assertEqual(
            rd._terminal_exemption_source("REL-178", {"REL-178"}, set()),
            "archive")

    def test_classifier_live_basis(self):
        """活体行自身断言终态（completed ⊆ closed）→ "live"。"""
        self.assertEqual(
            rd._terminal_exemption_source(
                "REL-178", {"REL-178"}, {"REL-178"}),
            "live")

    def test_classifier_merged_set_mixed_membership(self):
        """真实合并门集形态：同一 ``closed`` 内两类来源共存且互不误判。"""
        closed = {"REL-178", "FIX-900"}
        completed = {"FIX-900"}
        self.assertEqual(
            rd._terminal_exemption_source("REL-178", closed, completed),
            "archive")
        self.assertEqual(
            rd._terminal_exemption_source("FIX-900", closed, completed),
            "live")

    def test_classifier_id_outside_both_sets_defaults_live(self):
        """域外边界：不在任何集合的 id 取 fail-safe "live" 缺省（分类函数
        只在豁免门触发后被调用；门未触发的输入不产生归档声称）。"""
        self.assertEqual(
            rd._terminal_exemption_source(
                "NOPE-1", {"REL-178"}, {"REL-178"}),
            "live")

    def test_cause_clause_templates_mutually_distinguishable(self):
        """两类措辞模板互异且各带来源锚（DEC-214② / EVD-892）——读者一眼
        可辨「归档依据」vs「活体恢复」。"""
        archive_clause = rd._terminal_exemption_cause_clause(
            "REL-178", {"REL-178"}, set())
        live_clause = rd._terminal_exemption_cause_clause(
            "REL-178", {"REL-178"}, {"REL-178"})
        self.assertNotEqual(archive_clause, live_clause)
        self.assertIn("archived task", archive_clause)
        self.assertIn("archive Task index", archive_clause)
        self.assertIn("DEC-214②", archive_clause)
        self.assertIn("live plan-tracker", live_clause)
        self.assertIn("EVD-892", live_clause)

    # ── 行为面：V2 L-A 门（前导缺口）两类来源分流正例 ──────────────────

    def test_v2_leading_gap_archive_source_discloses_archive_basis(self):
        """归档依据豁免正例：归档终态行 + 前导缺口 → V2 WARN 因果措辞指
        归档（DEC-214②），且不含活体措辞。"""
        r = self._live_run([], self._leading_gap_evidence(),
                           archive_index=self._ARCHIVE_INDEX)
        self.assertEqual(r["verdict"], "WARN")
        v2 = [x for x in r["warnings"]
              if x["rule"] == "V2" and x["task_id"] == "REL-178"]
        self.assertTrue(v2, r["warnings"])
        self.assertIn("closure basis: archived task", v2[0]["reason"])
        self.assertIn("DEC-214②", v2[0]["reason"])
        self.assertNotIn("closure basis: live", v2[0]["reason"])

    def test_v2_leading_gap_live_source_discloses_live_basis(self):
        """活体恢复豁免正例：tracker「✅ 完成」行 + 前导缺口 → 同一门、同一
        WARN，但因果措辞指活体行（EVD-892），且不含归档措辞。"""
        r = self._live_run([self._LIVE_COMPLETED_ROW],
                           self._leading_gap_evidence())
        self.assertEqual(r["verdict"], "WARN")
        v2 = [x for x in r["warnings"]
              if x["rule"] == "V2" and x["task_id"] == "REL-178"]
        self.assertTrue(v2, r["warnings"])
        self.assertIn("closure basis: live plan-tracker terminal row",
                      v2[0]["reason"])
        self.assertIn("EVD-892", v2[0]["reason"])
        self.assertNotIn("closure basis: archived", v2[0]["reason"])

    # ── 行为面：V5 legacy-key 门同样分流（第二豁免门抽样） ─────────────

    def test_v5_legacy_key_archive_source_discloses_archive_basis(self):
        """V5 门归档来源正例：归档终态任务 + 旧格式 token → WARN 带归档
        因果措辞。"""
        r = self._live_run([], self._legacy_token_evidence(),
                           archive_index=self._ARCHIVE_INDEX)
        v5 = [x for x in r["warnings"]
              if x["rule"] == "V5" and x["task_id"] == "REL-178"]
        self.assertTrue(v5, r["warnings"])
        self.assertIn("closure basis: archived task", v5[0]["reason"])
        self.assertIn("DEC-214②", v5[0]["reason"])
        self.assertNotIn("closure basis: live", v5[0]["reason"])

    def test_v5_legacy_key_live_source_discloses_live_basis(self):
        """V5 门活体来源正例：tracker 终态行 + 旧格式 token → WARN 带活体
        因果措辞（同一门、不同来源、措辞可辨）。"""
        r = self._live_run([self._LIVE_COMPLETED_ROW],
                           self._legacy_token_evidence())
        v5 = [x for x in r["warnings"]
              if x["rule"] == "V5" and x["task_id"] == "REL-178"]
        self.assertTrue(v5, r["warnings"])
        self.assertIn("closure basis: live plan-tracker terminal row",
                      v5[0]["reason"])
        self.assertIn("EVD-892", v5[0]["reason"])
        self.assertNotIn("closure basis: archived", v5[0]["reason"])

    # ── 边界：fail-safe 路径（closed == completed）永不声称归档依据 ────

    def test_fixture_path_rows_carry_live_clause_never_archive(self):
        """fixture 路径（closed == completed，无归档贡献）：豁免行措辞只能
        指活体行——分类器 fail-safe 缺省的端到端看护。"""
        r = vw.check_review_closure(
            review_sequence=_router_legacy_sequences(),
            plan_tracker_completed=_ROUTER_COMPLETED)
        v2 = [w for w in r["warnings"] if w["rule"] == "V2"
              and w["task_id"] == "ARCH-001"]
        self.assertTrue(v2, r["warnings"])
        self.assertIn("closure basis: live plan-tracker terminal row",
                      v2[0]["reason"])
        self.assertNotIn("closure basis: archived", v2[0]["reason"])


if __name__ == "__main__":
    unittest.main()
