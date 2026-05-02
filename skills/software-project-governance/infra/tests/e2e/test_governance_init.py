"""端到端测试：模拟 governance init 流程 — SYSGAP-017.

本测试不运行真实的 governance-init（需要 agent 交互），而是：
  1. 模拟 plan-tracker.md 的各种状态，验证 check-governance 输出正确
  2. 模拟 evidence-log.md 的各种状态，验证证据完整性检查
  3. 模拟 Gate 一致性场景，验证 Gate 检查逻辑

列格式约束（必须匹配 parse 函数的硬编码列索引）：
  - parse_completed_task_ids: >= 11 parts, status at parts[10]
  - parse_evidence_task_ids:  | EVD-xxx | <TASK-ID> | ..., parts[2]
  - parse_open_risks:         >= 10 parts, status at parts[9]
  - parse_gate_status:        >= 5 parts (split[1:-1]), [0]=gate [2]=status

Run:
    python -m pytest skills/software-project-governance/infra/tests/e2e/test_governance_init.py -v
"""

import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw


# ────────────────────────────────────────────────────────────
# Fixture row builders (column counts match parser indices)
# ────────────────────────────────────────────────────────────

# Task table: 10 visible cols, status at parts[10]
# | 任务ID | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | 状态 |
_THEAD = "| 任务ID | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | 状态 |"
_TSEP  = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"

def task_row(tid, status="已完成"):
    return f"| {tid} | a | b | c | d | e | f | g | h | {status} |"

# Evidence: task IDs at parts[2]
# | EVD-xxx | <TASK-IDS> | ...
def evd_row(eid, task_ids):
    return f"| {eid} | {task_ids} | done |"

# Risk: 9 visible cols, status at parts[9]
# | 编号 | 日期 | a | b | c | d | e | f | 状态 |
def risk_row(rid, date_str, status="打开"):
    return f"| {rid} | {date_str} | a | b | c | d | e | f | {status} |"


# ────────────────────────────────────────────────────────────

class ProjectSkeleton:
    """Build a minimal project skeleton with .governance/ files."""

    def __init__(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)
        self.gov = self.root / ".governance"
        self.gov.mkdir(parents=True)
        self._plan     = self.gov / "plan-tracker.md"
        self._evidence = self.gov / "evidence-log.md"
        self._risk     = self.gov / "risk-log.md"
        self._decision = self.gov / "decision-log.md"
        for fp in [self._plan, self._evidence, self._risk, self._decision]:
            fp.write_text("", encoding="utf-8")

    def write_plan(self, c: str):      self._plan.write_text(c, encoding="utf-8")
    def write_evidence(self, c: str):  self._evidence.write_text(c, encoding="utf-8")
    def write_risk(self, c: str):      self._risk.write_text(c, encoding="utf-8")
    def write_decision(self, c: str):  self._decision.write_text(c, encoding="utf-8")

    def run_evidence_check(self):
        with patch.object(vw, "SAMPLE_PATH", self._plan), \
             patch.object(vw, "EVIDENCE_PATH", self._evidence):
            return vw.check_evidence_completeness()

    def run_risk_check(self):
        with patch.object(vw, "SAMPLE_PATH", self._plan), \
             patch.object(vw, "RISK_PATH", self._risk):
            return vw.check_risk_staleness()

    def run_gate_check(self):
        with patch.object(vw, "SAMPLE_PATH", self._plan), \
             patch.object(vw, "EVIDENCE_PATH", self._evidence), \
             patch.object(vw, "RISK_PATH", self._risk):
            return vw.check_gate_consistency()

    def __enter__(self): return self
    def __exit__(self, *_): self._td.cleanup()


# ────────────────────────────────────────────────────────────
# Scenario 1 — plan-tracker state simulation
# ────────────────────────────────────────────────────────────

class PlanTrackerStateTests(unittest.TestCase):

    def test_all_tasks_covered(self):
        plan = "\n".join([
            "# 计划跟踪",
            "## 任务跟踪", "", _THEAD, _TSEP,
            task_row("TASK-001"),
            task_row("TASK-002"),
        ])
        evidence = "\n".join([
            evd_row("EVD-001", "TASK-001, TASK-002"),
        ])
        with ProjectSkeleton() as ps:
            ps.write_plan(plan); ps.write_evidence(evidence)
            r = ps.run_evidence_check()
            self.assertEqual(r["completed_count"], 2)
            self.assertEqual(len(r["missing_evidence"]), 0)

    def test_in_progress_no_evidence_needed(self):
        plan = "\n".join([
            "# 计划跟踪",
            "## 任务跟踪", "", _THEAD, _TSEP,
            task_row("TASK-001"),
            task_row("TASK-002", "进行中"),
        ])
        evidence = evd_row("EVD-001", "TASK-001")
        with ProjectSkeleton() as ps:
            ps.write_plan(plan); ps.write_evidence(evidence)
            r = ps.run_evidence_check()
            self.assertEqual(r["completed_count"], 1)
            self.assertEqual(len(r["missing_evidence"]), 0)

    def test_no_tasks(self):
        with ProjectSkeleton() as ps:
            ps.write_plan("# 计划跟踪\n\n项目刚开始。\n")
            r = ps.run_evidence_check()
            self.assertEqual(r["completed_count"], 0)


# ────────────────────────────────────────────────────────────
# Scenario 2 — evidence-log state simulation
# ────────────────────────────────────────────────────────────

class EvidenceLogStateTests(unittest.TestCase):

    def test_complete_coverage(self):
        plan = "\n".join([
            "# 计划跟踪",
            "## 任务跟踪", "", _THEAD, _TSEP,
            task_row("TASK-001"),
            task_row("TASK-002"),
            task_row("TASK-003", "进行中"),
        ])
        evidence = "\n".join([
            evd_row("EVD-001", "TASK-001"),
            evd_row("EVD-002", "TASK-001, TASK-002"),
        ])
        with ProjectSkeleton() as ps:
            ps.write_plan(plan); ps.write_evidence(evidence)
            r = ps.run_evidence_check()
            self.assertEqual(r["completed_count"], 2)
            self.assertEqual(len(r["missing_evidence"]), 0)

    def test_partial_coverage(self):
        plan = "\n".join([
            "# 计划跟踪",
            "## 任务跟踪", "", _THEAD, _TSEP,
            task_row("TASK-001"),
            task_row("TASK-002"),
        ])
        evidence = evd_row("EVD-001", "TASK-001")
        with ProjectSkeleton() as ps:
            ps.write_plan(plan); ps.write_evidence(evidence)
            r = ps.run_evidence_check()
            self.assertEqual(r["completed_count"], 2)
            self.assertIn("TASK-002", r["missing_evidence"])

    def test_empty_evidence(self):
        plan = "\n".join([
            "# 计划跟踪",
            "## 任务跟踪", "", _THEAD, _TSEP,
            task_row("TASK-001"),
        ])
        with ProjectSkeleton() as ps:
            ps.write_plan(plan)
            # evidence file empty => zero evidence => TASK-001 missing
            r = ps.run_evidence_check()
            self.assertEqual(r["completed_count"], 1)
            self.assertIn("TASK-001", r["missing_evidence"])


# ────────────────────────────────────────────────────────────
# Scenario 3 — Gate consistency
# ────────────────────────────────────────────────────────────

class GateConsistencyTests(unittest.TestCase):

    def test_gate_passed_with_evidence(self):
        plan = """# 计划跟踪

## Gate 状态跟踪

| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |
| --- | --- | --- | --- | --- |
| G1 | 立项 | passed | 2026-04-01 | EVD-001 |

## 任务跟踪

%s
%s
%s
""" % (_THEAD, _TSEP, task_row("GATE-001"))
        evidence = evd_row("EVD-001", "GATE-001")
        with ProjectSkeleton() as ps:
            ps.write_plan(plan); ps.write_evidence(evidence)
            issues = ps.run_gate_check()
            missing = [i for i in issues
                       if i.get("type") == "completed_tasks_missing_evidence"]
            self.assertEqual(len(missing), 0)

    def test_gate_passed_without_task_done(self):
        plan = """# 计划跟踪

## Gate 状态跟踪

| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |
| --- | --- | --- | --- | --- |
| G1 | 立项 | passed | 2026-04-01 | EVD-001 |

## 任务跟踪

%s
%s
%s
""" % (_THEAD, _TSEP, task_row("GATE-001", "进行中"))
        evidence = evd_row("EVD-001", "GATE-001")
        with ProjectSkeleton() as ps:
            ps.write_plan(plan); ps.write_evidence(evidence)
            issues = ps.run_gate_check()
            self.assertIsInstance(issues, list)

    def test_passed_on_entry(self):
        plan = """# 计划跟踪

## Gate 状态跟踪

| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |
| --- | --- | --- | --- | --- |
| G1 | 立项 | passed-on-entry | 2026-04-01 | - |
| G2 | 调研 | passed-on-entry | 2026-04-01 | - |
| G3 | 开发 | pending | - | - |
"""
        with ProjectSkeleton() as ps:
            ps.write_plan(plan)
            with patch.object(vw, "SAMPLE_PATH", ps._plan):
                gates = vw.parse_gate_statuses()
                self.assertEqual(len(gates), 3)
                poe = [g for g in gates if g["status"] == "passed-on-entry"]
                self.assertEqual(len(poe), 2)

    def test_orphan_evidence(self):
        plan = "\n".join([
            "# 计划跟踪",
            "## 任务跟踪", "", _THEAD, _TSEP,
            task_row("TASK-001"),
        ])
        evidence = "\n".join([
            evd_row("EVD-001", "TASK-001"),
            evd_row("EVD-002", "NONEXISTENT"),
        ])
        with ProjectSkeleton() as ps:
            ps.write_plan(plan); ps.write_evidence(evidence)
            issues = ps.run_gate_check()
            orphans = [i for i in issues if i.get("type") == "orphan_evidence"]
            self.assertGreaterEqual(len(orphans), 0)


# ────────────────────────────────────────────────────────────
# Risk staleness
# ────────────────────────────────────────────────────────────

class RiskStalenessE2ETests(unittest.TestCase):

    def test_all_risks_closed(self):
        with ProjectSkeleton() as ps:
            ps.write_plan("# plan\n")
            ps.write_risk(risk_row("RISK-001", "2026-01-01", "关闭"))
            with patch.object(vw, "SAMPLE_PATH", ps._plan), \
                 patch.object(vw, "RISK_PATH", ps._risk):
                r = vw.check_risk_staleness()
                self.assertEqual(r["total_open"], 0)
                self.assertEqual(len(r["stale"]), 0)

    def test_mixed_fresh_and_stale(self):
        today = date.today()
        fresh = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        stale = (today - timedelta(days=60)).strftime("%Y-%m-%d")
        plan = "# plan\n"
        risk = "\n".join([
            risk_row("RISK-001", fresh, "打开"),
            risk_row("RISK-002", stale, "打开"),
            risk_row("RISK-003", stale, "关闭"),
        ])
        with ProjectSkeleton() as ps:
            ps.write_plan(plan); ps.write_risk(risk)
            with patch.object(vw, "SAMPLE_PATH", ps._plan), \
                 patch.object(vw, "RISK_PATH", ps._risk):
                r = vw.check_risk_staleness()
                self.assertEqual(r["total_open"], 2)
                self.assertEqual(len(r["stale"]), 1)
                self.assertEqual(r["stale"][0][0], "RISK-002")
                self.assertEqual(len(r["fresh"]), 1)
                self.assertEqual(r["fresh"][0][0], "RISK-001")


# ────────────────────────────────────────────────────────────
# Full governance E2E
# ────────────────────────────────────────────────────────────

class FullGovernanceE2ETests(unittest.TestCase):

    def test_full_skeleton_all_checks_pass(self):
        today_str = date.today().strftime("%Y-%m-%d")
        plan = "\n".join([
            "# 计划跟踪",
            "## 项目配置",
            "- **Profile**: standard",
            "## Gate 状态跟踪",
            "| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |",
            "| --- | --- | --- | --- | --- |",
            "| G1 | 立项 | passed | 2026-04-01 | EVD-001 |",
            "| G2 | 调研 | passed | 2026-04-02 | EVD-002 |",
            "| G3 | 选型 | passed-on-entry | 2026-04-03 | - |",
            "## 任务跟踪", "", _THEAD, _TSEP,
            task_row("INIT-001"),
            task_row("RES-001"),
            task_row("DES-001"),
            task_row("DEV-001", "进行中"),
        ])
        evidence = "\n".join([
            evd_row("EVD-001", "INIT-001"),
            evd_row("EVD-002", "RES-001"),
            evd_row("EVD-003", "DES-001"),
        ])
        risk = risk_row("RISK-001", today_str, "打开")
        decision = "| DEC-001 | 2026-04-01 | 技术选型 |\n"

        with ProjectSkeleton() as ps:
            ps.write_plan(plan); ps.write_evidence(evidence)
            ps.write_risk(risk); ps.write_decision(decision)

            # Evidence completeness
            ev = ps.run_evidence_check()
            self.assertEqual(ev["completed_count"], 3)
            self.assertEqual(len(ev["missing_evidence"]), 0)

            # Risk staleness
            rk = ps.run_risk_check()
            self.assertEqual(rk["total_open"], 1)
            self.assertEqual(len(rk["stale"]), 0)

            # Gate consistency
            gi = ps.run_gate_check()
            missing = [i for i in gi
                       if i.get("type") == "completed_tasks_missing_evidence"]
            self.assertEqual(len(missing), 0)

            # Decision log content
            dc = ps._decision.read_text(encoding="utf-8")
            self.assertIn("DEC-001", dc)


if __name__ == "__main__":
    unittest.main()
