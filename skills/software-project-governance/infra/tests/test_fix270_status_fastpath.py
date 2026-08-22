"""FIX-270 / 交付 A — `status` 秒级状态快路径测试（red→green）。

Deliverable under test (FIX-270 交付 A):

1. `status` 子命令在宿主项目（HOST_PROJECT_ROOT）上 <2s 输出 Scenario F 面板所需
   全部结构化数据：项目配置 / Gate 状态（G1-G11 与日期、证据引用）/ 任务统计
   （总数/已完成/阻塞中/P0 待处理）/ 活跃风险（≤3 天升级线标记）/ 最近活动
   （最近 5 个已完成任务 + 最近 5 个决策）/ 插件版本新鲜度 / 建议下一步线索。
2. 实现约束：行级解析 .governance 热文件；不读全量 evidence-log 大文件；
   可选 `--json` 输出机器格式。
3. 回归保护：既有 status 输出（Project Overview / Delivery Trust Snapshot /
   Task Status / Gate Status、permission_mode、合法 permission mode 值）
   保持存在（e2e validators 依赖这些字符串）。

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_fix270_status_fastpath.py -v
"""

import io
import json
import sys
import types
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw  # noqa: E402


def _task_table_rows():
    """A host-style 任务跟踪表 with completion dates + duplicate board table."""
    return (
        "## 任务跟踪表\n"
        "| 优先级 | ID | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | "
        "Escalation | 状态 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | "
        "风险/偏差 | 纠偏动作 | 备注 | 审查状态 |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | "
        "--- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| P0 | TASK-001 | 首个 P0 任务 | 目标 | 输入 | 输出 | Dev | QA | — | 已完成 | "
        "2026-08-01 | 2026-08-02 | 2026-08-03 | G6 | 验收 | EVD-001 | — | — | — | 已审查 |\n"
        "| P1 | TASK-002 | 第二个 P1 任务 | 目标 | 输入 | 输出 | Dev | QA | — | 进行中 | "
        "2026-08-10 | — | — | G6 | 验收 | — | — | — | — | 未审查 |\n"
        "| P1 | TASK-003 | 第三个任务 | 目标 | 输入 | 输出 | Dev | QA | — | 未开始 | "
        "— | — | — | G6 | 验收 | — | — | — | — | 未审查 |\n"
        "## 当前活跃事项\n\n"
        "| 优先级 | ID | 任务项 | 依赖 | 目标版本 | 状态 |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| P0 | TASK-001 | 首个 P0 任务（当前活跃事项镜像） | — | 1.6.0 | 已完成 |\n"
        "| P1 | TASK-002 | 第二个 P1 任务（镜像） | — | 1.6.0 | 进行中 |\n"
        "## 使用规则\n"
    )


def _plan_tracker_text(workflow_version="0.75.0", stage="开发 (6/11)"):
    return (
        "# 测试项目计划\n\n"
        "## 项目配置\n\n"
        "- **项目名称**: 云视TV 测试项目\n"
        "- **Profile**: standard\n"
        "- **触发模式**: always-on\n"
        "- **操作权限模式**: maximum-autonomy\n"
        f"- **工作流版本**: {workflow_version}\n"
        f"- **当前阶段**: {stage}\n\n"
        "## 项目总览\n\n"
        "| 项目 | 当前阶段 | 总任务数 | 已完成 | 阻塞中 | 关键风险数 | 最近 Gate 结论 | 最近复盘日期 |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
        f"| 云视TV | {stage} | 3 | 1 | 0 | 1 | G5 通过 | — |\n\n"
        "## Gate 状态跟踪\n\n"
        "| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| G1 | → 调研 | passed-on-entry | 2026-08-19 | DEC-001 |\n"
        "| G2 | → 技术选型 | passed-on-entry | 2026-08-19 | DEC-002 |\n"
        "| G3 | → 环境搭建 | passed-on-entry | 2026-08-19 | DEC-003 |\n"
        "| G4 | → 架构设计 | passed-on-entry | 2026-08-19 | DEC-004 |\n"
        "| G5 | → 开发实现 | passed-on-entry | 2026-08-19 | DEC-005 |\n"
        "| G6 | → 测试 | passed-on-entry | 2026-08-19 | DEC-006 |\n"
        "| G7 | → 防护网与CI/CD | passed-on-entry | 2026-08-19 | DEC-007 |\n"
        "| G8 | → 版本发布 | passed-on-entry | 2026-08-19 | DEC-008 |\n"
        "| G9 | → 运营 | passed-on-entry | 2026-08-19 | DEC-009 |\n"
        "| G10 | → 维护 | passed-on-entry | 2026-08-19 | DEC-010 |\n"
        "| G11 | → 下一轮 | passed | 2026-08-19 | 复盘完成 |\n\n"
        "## 版本规划\n\n"
        "| 版本 | 状态 | 预计日期 | 核心范围 | 包含任务 | 关键交付物 |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| 1.6.0 | 已发布 | 2026-08-21 | 优化 | TASK-001 | — |\n\n"
        + _task_table_rows()
    )


def _risk_log_text(today=None):
    today = today or date.today()
    soon = (today + timedelta(days=2)).isoformat()
    far = (today + timedelta(days=30)).isoformat()
    # FIX-270 R0 F3：活跃 = 风险域 canonical "打开" 语义（与 Check 2/8 同源）；
    # 缓解完成/已关闭/resolved 均非活跃（不为风险域状态机另起标记集）。
    return (
        "# 风险记录\n\n"
        "| 编号 | 日期 | 风险/阻塞描述 | 所属阶段 | 触发条件 | 影响 | 严重级别 | Owner | "
        "当前状态 | 缓解动作 | 截止日期 | 关联任务 | 备注 |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        f"| RISK-001 | 2026-08-19 | 近线风险（打开） | 开发 (6) | 触发 | 影响 | 高 | Dev | 打开 | 缓解 | {soon} | TASK-001 | — |\n"
        f"| RISK-002 | 2026-08-19 | 缓解完成风险 | 开发 (6) | 触发 | 影响 | 高 | Dev | 缓解完成 | 缓解 | {far} | TASK-002 | — |\n"
        f"| RISK-003 | 2026-08-19 | 已关闭风险 | 开发 (6) | 触发 | 影响 | 高 | Dev | 已关闭 | 缓解 | {soon} | TASK-001 | — |\n"
        f"| RISK-004 | 2026-08-19 | resolved 风险 | 开发 (6) | 触发 | 影响 | 高 | Dev | resolved | 缓解 | {soon} | TASK-002 | — |\n"
        f"| RISK-005 | 2026-08-19 | 远期风险（打开） | 开发 (6) | 触发 | 影响 | 高 | Dev | 打开 | 缓解 | {far} | TASK-002 | — |\n"
        "\n## 使用规则\n\n- 阻塞项必须同步登记为风险。\n"
    )


def _decision_log_text():
    # FIX-270 R0 F2：live decision-log 为混合序（新在前混序）——按（日期, ID）降序取前 n，
    # 不得依赖文档顺序。含无日期行（兜底视为最旧）。
    return (
        "# 决策记录\n\n"
        "| 编号 | 日期 | 主题 | 背景 | 决策内容 | 备选方案 | 选择原因 | 影响范围 | 决策人 | "
        "关联任务 | 后续动作 |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| DEC-150 | 2026-08-23 | 最新决策主题 | 背景 | 决策内容 | 备选 | 原因 | 影响范围 | 决策人 | 关联任务 | 后续动作 |\n"
        "| DEC-011 | 2026-06-01 | 旧决策（混在中间） | 背景 | 决策内容 | 备选 | 原因 | 影响范围 | 决策人 | 关联任务 | 后续动作 |\n"
        "| DEC-149 | 2026-08-22 | 次新决策主题 | 背景 | 决策内容 | 备选 | 原因 | 影响范围 | 决策人 | 关联任务 | 后续动作 |\n"
        "| DEC-001 | 2026-04-10 | 最旧决策 | 背景 | 决策内容 | 备选 | 原因 | 影响范围 | 决策人 | 关联任务 | 后续动作 |\n"
        "| DEC-144 | 2026-08-21 | 决策主题 4 | 背景 | 决策内容 | 备选 | 原因 | 影响范围 | 决策人 | 关联任务 | 后续动作 |\n"
        "| DEC-143 | 2026-08-17 | 决策主题 3 | 背景 | 决策内容 | 备选 | 原因 | 影响范围 | 决策人 | 关联任务 | 后续动作 |\n"
        "| DEC-900 | — | 无日期决策（旧兜底） | 背景 | 决策内容 | 备选 | 原因 | 影响范围 | 决策人 | 关联任务 | 后续动作 |\n"
        "| DEC-002 | 2026-04-11 | 次旧决策 | 背景 | 决策内容 | 备选 | 原因 | 影响范围 | 决策人 | 关联任务 | 后续动作 |\n"
        "| DEC-140 | 2026-08-16 | 决策主题 2 | 背景 | 决策内容 | 备选 | 原因 | 影响范围 | 决策人 | 关联任务 | 后续动作 |\n"
    )


def _evidence_log_text():
    # FIX-270 R0 F1：fixture 必须创建含多行的 evidence-log（只有缺失早退分支是空洞守卫）。
    # 备注列含"进行中"/"待处理"（GOVERNANCE_CONTEXT_EVIDENCE_UNFINISHED_MARKERS）→ 若发现器
    # 全量读取该文件，守卫测试的整读断言必触发；修复后该路径被绕过。
    return (
        "# 证据记录\n\n"
        "| 编号 | 对应任务 ID | 阶段 | 证据类型 | 证据说明 | 证据位置 | 提交人 | 提交日期 | 关联 Gate | 备注 |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| EVD-001 | TASK-001 | 开发 (6) | 文档 | 完成证据 | .governance/plan-tracker.md | Dev | 2026-08-03 | G6 | 已完成 |\n"
        "| EVD-002 | TASK-002 | 开发 (6) | 文档 | 进行中证据 | research/ | Dev | 2026-08-10 | G6 | 进行中 |\n"
        "| EVD-003 | TASK-003 | 开发 (6) | 文档 | 待处理证据 | research/ | Dev | 2026-08-11 | G6 | 待处理 |\n"
        "| EVD-004 | TASK-001 | 开发 (6) | 审查 | 复审证据 | review/ | Reviewer | 2026-08-12 | G6 | 已完成 |\n"
    )


def _snapshot_text():
    return (
        "# 会话快照 — 2026-08-22\n\n"
        "- **session_id**: 20260822-100000\n"
        "- **session_date**: 2026-08-22\n"
        "- **agent**: test\n\n"
        "## 当前状态\n"
        "- **current_stage**: 6\n"
        "- **workflow_version**: 0.75.0\n\n"
        "## 遗留任务\n"
        "| 任务 ID | 描述 | 完成百分比 | 阻塞原因 | 优先级 |\n"
        "|---------|-------------|------------|-----------|----------|\n"
        "| TASK-002 | 进行中任务 | 50% | 无 | P1 |\n"
    )


def _install_fixture(td):
    """Write fixture .governance files and patch status-reader globals."""
    gov = Path(td) / ".governance"
    gov.mkdir(parents=True, exist_ok=True)
    plan_path = gov / "plan-tracker.md"
    plan_path.write_text(_plan_tracker_text(), encoding="utf-8")
    (gov / "risk-log.md").write_text(_risk_log_text(), encoding="utf-8")
    (gov / "decision-log.md").write_text(_decision_log_text(), encoding="utf-8")
    (gov / "evidence-log.md").write_text(_evidence_log_text(), encoding="utf-8")
    (gov / "session-snapshot.md").write_text(_snapshot_text(), encoding="utf-8")
    patchers = [
        mock.patch.object(vw, "SAMPLE_PATH", plan_path),
        mock.patch.object(vw, "SESSION_SNAPSHOT_PATH", gov / "session-snapshot.md"),
        mock.patch.object(vw, "EVIDENCE_PATH", gov / "evidence-log.md"),
        mock.patch.object(vw, "RISK_PATH", gov / "risk-log.md"),
        mock.patch.object(vw, "GOVERNANCE_DIR", gov),
    ]
    for p in patchers:
        p.start()
    return plan_path, patchers


def _args(json_mode=False):
    return types.SimpleNamespace(json=json_mode)


class StatusFastPathParsersTests(unittest.TestCase):
    """Red→green: new status parsers (task-table rows, risks, decisions, freshness)."""

    def test_task_table_rows_dedupe_and_recent_completed(self):
        with mock.patch("tempfile.tempdir", None):
            import tempfile
            with tempfile.TemporaryDirectory() as td:
                plan_path, patchers = _install_fixture(td)
                try:
                    rows = vw.parse_task_table_rows()
                    ids = [r["id"] for r in rows]
                    # TASK-001 appears twice (tracking table + active-items mirror) → 1 row
                    self.assertEqual(ids.count("TASK-001"), 1)
                    self.assertIn("TASK-002", ids)
                    self.assertIn("TASK-003", ids)
                    done = [r for r in rows if r["status"] == "已完成"]
                    self.assertEqual([r["id"] for r in done], ["TASK-001"])
                    recent = vw.parse_recent_completed_tasks(rows, 5)
                    self.assertEqual([r["id"] for r in recent], ["TASK-001"])
                finally:
                    for p in patchers:
                        p.stop()

    def test_active_risks_escalation_within_3_days(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            _, patchers = _install_fixture(td)
            try:
                risks = vw.parse_active_risks()
                ids = [r["id"] for r in risks]
                # F3：活跃 = 风险域 "打开" 语义（与 Check 2/8 同源）；
                # 缓解完成 / 已关闭 / resolved 一律非活跃。
                self.assertEqual(ids, ["RISK-001", "RISK-005"])
                by_id = {r["id"]: r for r in risks}
                self.assertTrue(by_id["RISK-001"]["escalation_soon"])
                self.assertFalse(by_id["RISK-001"]["escalation_overdue"])
                self.assertFalse(by_id["RISK-005"]["escalation_soon"])
                self.assertNotIn("RISK-002", by_id)  # 缓解完成 → excluded
                self.assertNotIn("RISK-003", by_id)  # 已关闭 → excluded
                self.assertNotIn("RISK-004", by_id)  # resolved → excluded
            finally:
                for p in patchers:
                    p.stop()

    def test_recent_decisions_last_five(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            _, patchers = _install_fixture(td)
            try:
                decisions = vw.parse_recent_decisions(5)
                self.assertEqual(len(decisions), 5)
                # F2：按（日期, ID）降序取前 5——不得依赖文档顺序（混合序 fixture）
                self.assertEqual(
                    [d["id"] for d in decisions],
                    ["DEC-150", "DEC-149", "DEC-144", "DEC-143", "DEC-140"],
                )
                # 旧日期条目与无日期兜底行不得进入最近 5
                self.assertNotIn("DEC-001", [d["id"] for d in decisions])
                self.assertNotIn("DEC-002", [d["id"] for d in decisions])
                self.assertNotIn("DEC-011", [d["id"] for d in decisions])
                self.assertNotIn("DEC-900", [d["id"] for d in decisions])
            finally:
                for p in patchers:
                    p.stop()

    def test_plugin_freshness_compares_active_version(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            _, patchers = _install_fixture(td, )
            try:
                fresh = vw._status_plugin_freshness()
                self.assertIn("status", fresh)
                self.assertEqual(fresh["plan_version"], "0.75.0")
                self.assertIn(fresh["status"], ("UP TO DATE", "OUTDATED", "UNKNOWN"))
            finally:
                for p in patchers:
                    p.stop()


class StatusCommandTests(unittest.TestCase):
    """Red→green: cmd_status output sections + --json machine format."""

    def _run_status(self, td, json_mode=False):
        plan_path, patchers = _install_fixture(td)
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                vw.cmd_status(_args(json_mode=json_mode))
            return buf.getvalue()
        finally:
            for p in patchers:
                p.stop()

    def test_status_text_sections_present(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            output = self._run_status(td)
            # Legacy strings preserved (e2e validators depend on them)
            for token in (
                "Project Config",
                "Project Overview",
                "Delivery Trust Snapshot",
                "Task Status",
                "Gate Status",
            ):
                self.assertIn(token, output, f"legacy section {token} missing")
            self.assertIn("maximum-autonomy", output)
            # 新增 Scenario F sections
            for token in (
                "Active Risks",
                "Recent Activity",
                "Plugin Freshness",
                "Next step",
            ):
                self.assertIn(token, output, f"new section {token} missing")
            # Gate 表修复：G1-G11 全部打印（现状 bug 只打印最后一行）
            for g in range(1, 12):
                self.assertIn(f" G{g} ", output)

    def test_status_json_contract(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            output = self._run_status(td, json_mode=True).strip()
            data = json.loads(output)
            self.assertEqual(
                data["project_config"]["profile"].strip().split()[0], "standard"
            )
            self.assertIn("trigger_mode", data["project_config"])
            self.assertIn("permission_mode", data["project_config"])
            self.assertIn("workflow_version", data["project_config"])
            gates = data["gates"]
            self.assertGreaterEqual(len(gates), 11)
            self.assertEqual(gates[0]["gate"], "G1")
            self.assertIn("date", gates[0])
            self.assertIn("evidence", gates[0])
            stats = data["stats"]
            self.assertEqual(stats["total"], 3)
            self.assertEqual(stats["completed"], 1)
            self.assertEqual(stats["blocked"], 0)
            self.assertIn("p0_pending", stats)
            risks = data["risks"]
            self.assertEqual(len(risks), 2)  # F3：仅"打开"语义两条活跃风险
            self.assertIn("escalation_soon", risks[0])
            recent = data["recent_activity"]
            self.assertEqual(len(recent["completed_tasks"]), 1)
            self.assertEqual(len(recent["decisions"]), 5)
            self.assertIn("status", data["plugin_freshness"])
            self.assertIn("next_steps", data)
            self.assertIn("delivery_trust_snapshot", data)

    def test_status_does_not_read_evidence_log(self):
        # F1（R0）：fixture 含多行 evidence-log（活跃行 EVD-002/003 备注=进行中/待处理），
        # 若 discover_governance_context 链路全量读取该文件，此处必然触发断言（先红后绿）。
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            _, patchers = _install_fixture(td)
            try:
                orig_read = Path.read_text

                def fake_read(self, *args, **kwargs):
                    if self.name == "evidence-log.md":
                        raise AssertionError(
                            "status must not read evidence-log.md (FIX-270 全量读大文件禁令)"
                        )
                    return orig_read(self, *args, **kwargs)

                Path.read_text = fake_read
                try:
                    vw.cmd_status(_args(json_mode=False))
                finally:
                    Path.read_text = orig_read
            finally:
                for p in patchers:
                    p.stop()


class StatusNextStepTests(unittest.TestCase):
    """Red→green: 建议下一步线索 = 轻量派生（unblocked P0/P1，不运行 check-governance）。"""

    def test_next_steps_prefers_unblocked_p0(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            plan_path, patchers = _install_fixture(td)
            try:
                plan_content = plan_path.read_text(encoding="utf-8")
                steps = vw._status_next_steps(plan_content)
                self.assertIsInstance(steps, list)
                ids = [s["task_id"] for s in steps]
                # 已完成 TASK-001 不得出现；未完成且无未完成依赖(P1)的 TASK-002/003 应被推荐
                self.assertNotIn("TASK-001", ids)
                self.assertIn("TASK-002", ids)
                self.assertIn("TASK-003", ids)
            finally:
                for p in patchers:
                    p.stop()


if __name__ == "__main__":
    unittest.main()
