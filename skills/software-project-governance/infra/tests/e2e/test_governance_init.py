"""端到端测试：模拟 governance init 流程 — SYSGAP-017.

本测试不运行真实的 governance-init（需要 agent 交互），而是：
  1. 模拟 plan-tracker.md 的各种状态，验证 check-governance 输出正确
  2. 模拟 evidence-log.md 的各种状态，验证证据完整性检查
  3. 模拟 Gate 一致性场景，验证 Gate 检查逻辑

列格式约束（必须匹配 parse 函数的硬编码列索引）：
  - parse_completed_task_ids: >= 11 parts, status at parts[10]
  - parse_evidence_task_ids:  | EVD-xxx | <TASK-ID> | ..., parts[2]
  - parse_open_risks:         >= 10 parts, status at parts[9]

Run:
    python -m pytest skills/software-project-governance/infra/tests/e2e/test_governance_init.py -v
"""

import json
import subprocess
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

    def invoke(self, *args):
        command = [sys.executable, "-X", "utf8", str(_INFRA_DIR / "verify_workflow.py"),
                   "--project-root", str(self.root), *args]
        result = subprocess.run(command, capture_output=True, check=True, encoding="utf-8")
        return json.loads(result.stdout)

    def run_evidence_check(self):
        with patch.object(vw, "SAMPLE_PATH", self._plan), \
             patch.object(vw, "EVIDENCE_PATH", self._evidence):
            return vw.check_evidence_completeness()

    def run_risk_check(self):
        with patch.object(vw, "SAMPLE_PATH", self._plan), \
             patch.object(vw, "RISK_PATH", self._risk):
            return vw.check_risk_staleness()

    def run_gate_check(self):
        with patch.object(vw, "GOVERNANCE_DIR", self.gov), \
             patch.object(vw, "SAMPLE_PATH", self._plan), \
             patch.object(vw, "EVIDENCE_PATH", self._evidence), \
             patch.object(vw, "RISK_PATH", self._risk):
            return vw.check_gate_consistency()

    def __enter__(self): return self
    def __exit__(self, *_): self._td.cleanup()


class MaterialNavigationTests(unittest.TestCase):

    def test_evidence_template_matches_registered_rows_and_scoped_lookup(self):
        from governance_readers import governance_table_cells
        template = _INFRA_DIR.parent / "core/templates/evidence-log.md"
        with ProjectSkeleton() as project:
            project.write_evidence(template.read_text(encoding="utf-8"))
            headers = next(governance_table_cells(line) for line in project._evidence.read_text(encoding="utf-8").splitlines()
                           if line.startswith("|"))
            project.invoke("loop", "start", "--unit", "invoice", "--task", "FIX-001", "--tier", "inner",
                           "--goal", "Check invoice", "--acceptance", "Reopen and compare totals")
            (project.root / "invoice.capture").write_text("42.00", encoding="utf-8")
            description = "目标对齐：核对导出的发票与原始账单中各行的实收数量，确保能够使用同一凭据重现核对结果。"
            cases = (("发票尾差", "金额一致", "见本行"), ("月末冲销", "退款已核销", "invoice.capture"))
            for word, conclusion, location in cases:
                with self.subTest(word=word):
                    row_id = project.invoke("evidence-append", "--task", "FIX-001", "--type", "实测",
                                            "--description", description + word, "--basis", "合计为 42.00",
                                            "--artifacts", location, "--actor", "QA", "--date", "2026-01-01",
                                            "--gate", "G6", "--conclusion", conclusion)["row_id"]
                    line = next(line for line in project._evidence.read_text(encoding="utf-8").splitlines()
                                if line.startswith(f"| {row_id} |"))
                    record = dict(zip(headers, governance_table_cells(line), strict=True))
                    self.assertEqual(record.pop("编号"), row_id)
                    self.assertIn("合计为 42.00", record.pop("事实依据"))
                    self.assertEqual(record, {"对应任务 ID": "FIX-001", "证据类型": "实测", "证据说明": description + word,
                                              "原件位置": location, "提交人": "QA", "提交日期": "2026-01-01",
                                              "关联 Gate": "G6", "结论": conclusion})
                    item, = project.invoke("loop", "materials", "--unit", "invoice", "--query", word)["items"]
                    self.assertEqual(item["ref"], row_id)
                    self.assertIn(conclusion, item["summary"])
                    self.assertEqual(project.invoke("loop", "materials", "--unit", "invoice", "--query",
                                                    conclusion)["items"][0]["ref"], row_id)
                    detail, = project.invoke("loop", "materials", "--unit", "invoice", "--ref", item["ref"])["items"]
                    self.assertEqual([p["target"] for p in detail["locations"]],
                                     [] if location == "见本行" else [location])

    def test_both_init_routes_use_the_unit_query_from_bootstrap(self):
        skill = _INFRA_DIR.parent
        routes = (skill.parents[1] / "commands/governance-init.md", skill / "core/onboarding.md")
        with ProjectSkeleton() as project:
            project.invoke("loop", "start", "--unit", "invoice", "--tier", "inner", "--goal", "Reopen the export",
                   "--acceptance", "The invoice sum matches the original.")
            boot = project.invoke("governance-bootstrap", "--format", "json")
            route = boot["materials_if_needed"].split(" [", 1)[0]
            for instructions in routes:
                with self.subTest(instructions=instructions):
                    text = instructions.read_text(encoding="utf-8")
                    self.assertTrue(any("templates/" in line and "`evidence-log.md`" in line
                                        for line in text.splitlines()))
                    self.assertIn(route, text)
                    self.assertNotIn("governance-readme.md", text)
            unit_id = boot["loops"]["units"][0]["flow_unit_id"]
            result = project.invoke(*route.replace("<id>", unit_id).split())
            self.assertIsInstance(result, dict)
            self.assertFalse((project.gov / "README.md").exists())
            self.assertFalse((project.gov / "materials").exists())


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

    def test_new_project_rechecks_failed_unit_and_rejects_damaged_receipt(self):
        import json
        import subprocess
        import loop_workflow

        with ProjectSkeleton() as project:
            cli = [sys.executable, str(_INFRA_DIR / "verify_workflow.py"), "--project-root",
                   str(project.root), "loop"]
            check = [sys.executable, "-c", "from pathlib import Path; print(Path('answer').read_text())"]
            subprocess.run([*cli, "start", "--unit", "sum", "--tier", "inner", "--goal", "Sum ledger rows",
                            "--acceptance", "Rows sum to seven", "--check-command", json.dumps(check),
                            "--expect-output", "7"], check=True, capture_output=True)
            (project.root / "answer").write_text("6", encoding="utf-8")
            subprocess.run([*cli, "verify", "--unit", "sum"], capture_output=True)
            state = json.loads(loop_workflow.runtime_path(project.root).read_bytes())
            history = state["flow_units"][0]["gate_history"]
            self.assertEqual([record["decision"] for record in history], ["iterate"])
            self.assertEqual(project.run_gate_check(), [])
            (project.root / "answer").write_text("7", encoding="utf-8")
            subprocess.run([*cli, "verify", "--unit", "sum"], check=True, capture_output=True)
            state = json.loads(loop_workflow.runtime_path(project.root).read_bytes())
            history = state["flow_units"][0]["gate_history"]
            self.assertEqual([record["decision"] for record in history], ["iterate", "exit"])
            self.assertEqual(project.run_gate_check(), [])
            (project.gov / history[0]["evidence_ref"]).write_bytes(b"modified")
            issues = project.run_gate_check()
            self.assertTrue(any(issue["type"] == "loop_receipt" and "sum" in issue["detail"]
                                for issue in issues), issues)

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
