"""Unit tests for verify_workflow.py — SYSGAP-016.

Column format constraints (mandatory—must match parser hard-coded indices):
  - parse_completed_task_ids: >= 11 parts, status at parts[10]
  - parse_evidence_task_ids:  | EVD-xxx | <TASK-ID-column> | ..., parts[2]
  - parse_open_risks:         >= 10 parts, status at parts[9]
  - parse_gate_status:        >= 5 parts (split[1:-1]), [0]=gate [2]=status

Run:
    python -m unittest discover -s skills/software-project-governance/infra/tests -v
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw


# ────────────────────────────────────────────────────────────
# Minimal fixture helpers (matching parse column indices)
# ────────────────────────────────────────────────────────────

# Task table: 10 visible columns, status at parts[10].
# | 任务ID | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | 状态 |
_TASK_COLS = "| 任务ID | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | 状态 |"
_TASK_SEP  = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"

def _task(tid, status="已完成"):
    return f"| {tid} | x | x | x | x | x | x | x | x | {status} |"

# Evidence table: task IDs at parts[2].
# | EVD-xxx | <TASK> | ... |
def _evd_row(eid, task_ids, extra=""):
    return f"| {eid} | {task_ids} | done{extra} |"

# Risk table: 9 visible cols, status at parts[9].
# | 编号 | 日期 | a | b | c | d | e | f | 状态 |
def _risk_row(rid, date_str, status="打开"):
    return f"| {rid} | {date_str} | a | b | c | d | e | f | {status} |"


# ────────────────────────────────────────────────────────────

class ManifestLoadingTests(unittest.TestCase):
    """Test manifest.json loading via build_required_files_from_manifest()."""

    def _make_manifest(self, root, entries=None, root_files=None):
        payload = {
            "$schema": "https://example.com/schema",
            "workflow": "test", "version": "1.0.0",
            "description": "Test.", "source_of_truth": True,
            "root_entries": {"files": root_files or [], "directories": []},
            "product": {"description": "p",
                        "entries": entries or [],
                        "glob_patterns": []},
            "repo_only": {"description": "r", "entries": [], "glob_patterns": []},
        }
        fp = root / "manifest.json"
        fp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return fp

    def test_load_manifest_normal(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mp = self._make_manifest(root, entries=[
                {"path": "README.md", "type": "file"},
                {"path": "skills/SKILL.md", "type": "file"},
            ])
            result = vw.build_required_files_from_manifest(mp)
            self.assertIsNotNone(result)
            self.assertIsInstance(result, dict)
            self.assertGreater(len(result), 0)

    def test_load_manifest_file_not_found(self):
        result = vw.build_required_files_from_manifest(Path("/nonexistent/x.json"))
        self.assertIsNone(result)

    def test_load_manifest_json_error(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "manifest.json"
            bad.write_text("{{{ not json", encoding="utf-8")
            self.assertIsNone(vw.build_required_files_from_manifest(bad))

    def test_load_manifest_empty(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            mp = self._make_manifest(root, entries=[], root_files=[])
            result = vw.build_required_files_from_manifest(mp)
            if result is not None:
                self.assertEqual(len(result), 0)


class CanonicalSetTests(unittest.TestCase):
    """Test expand_manifest_to_canonical_set()."""

    def _make(self, root, entries=None, patterns=None):
        p = {
            "$schema": "x", "workflow": "w", "version": "1",
            "description": "d", "source_of_truth": True,
            "root_entries": {"files": [], "directories": []},
            "product": {"description": "p", "entries": entries or [],
                        "glob_patterns": patterns or []},
            "repo_only": {"description": "r", "entries": [], "glob_patterns": []},
        }
        fp = root / "manifest.json"
        fp.write_text(json.dumps(p), encoding="utf-8")
        return fp

    def test_expand_canonical_entries(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "README.md").write_text("hi")
            skills = root / "skills"; skills.mkdir()
            (skills / "SKILL.md").write_text("s")
            mp = self._make(root, entries=[
                {"path": "README.md", "type": "file"},
                {"path": "skills/", "type": "dir"},
            ])
            with patch.object(vw, "ROOT", root):
                c = vw.expand_manifest_to_canonical_set(mp)
                self.assertIn("README.md", c)
                self.assertIn("skills/", c)

    def test_expand_canonical_glob_patterns(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            s = root / "skills"; s.mkdir()
            (s / "a.md").write_text("a")
            (s / "b.md").write_text("b")
            (s / "x.txt").write_text("x")
            mp = self._make(root, entries=[], patterns=["skills/*.md"])
            with patch.object(vw, "ROOT", root):
                c = vw.expand_manifest_to_canonical_set(mp)
                self.assertIn("skills/a.md", c)
                self.assertIn("skills/b.md", c)
                self.assertNotIn("skills/x.txt", c)

    def test_expand_canonical_file_not_found(self):
        self.assertIsNone(vw.expand_manifest_to_canonical_set(Path("/bad/x.json")))

    def test_expand_canonical_combined_dedup(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            d = root / "docs"; d.mkdir()
            (d / "r.md").write_text("r")
            mp = self._make(root,
                            entries=[{"path": "docs/r.md", "type": "file"}],
                            patterns=["docs/*.md"])
            with patch.object(vw, "ROOT", root):
                c = vw.expand_manifest_to_canonical_set(mp)
                self.assertEqual(sum(1 for p in c if p == "docs/r.md"), 1)


class FileExistenceTests(unittest.TestCase):
    """Test _check_file_exists() logic."""

    def test_file_exists(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "x.txt").write_text("x")
            with patch.object(vw, "ROOT", root):
                s, m = vw._check_file_exists("x.txt", "X")
                self.assertEqual(s, "PASS")
                self.assertIn("exists", m)

    def test_file_not_found(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(vw, "ROOT", Path(td)):
                s, m = vw._check_file_exists("nonexistent.txt", "X")
                self.assertEqual(s, "FAIL")
                self.assertIn("NOT FOUND", m)


class DecisionLogParsingTests(unittest.TestCase):
    """Test decision-log.md parsing."""

    def test_parse_decision_log_normal(self):
        content = """# 决策记录
| 编号 | 日期 | 主题 |
| --- | --- | --- |
| DEC-001 | 2026-04-17 | 测试 |
| DEC-002 | 2026-04-18 | 测试2 |
"""
        with tempfile.TemporaryDirectory() as td:
            dl = Path(td) / "dl.md"
            dl.write_text(content, encoding="utf-8")
            text = dl.read_text(encoding="utf-8")
            decs = {line.strip().split("|")[1].strip()
                    for line in text.split("\n")
                    if line.strip().startswith("| DEC-")}
            self.assertEqual(decs, {"DEC-001", "DEC-002"})

    def test_parse_decision_log_empty(self):
        text = ""
        decs = {line.strip().split("|")[1].strip() for line in text.split("\n")
                if line.strip().startswith("| DEC-")}
        self.assertEqual(len(decs), 0)

    def test_parse_decision_log_no_dec(self):
        text = "# 决策记录\n\n暂无决策。\n"
        decs = {line.strip().split("|")[1].strip() for line in text.split("\n")
                if line.strip().startswith("| DEC-")}
        self.assertEqual(len(decs), 0)


class PlanTrackerParsingTests(unittest.TestCase):
    """Test plan-tracker.md parsing."""

    _PLAN_TASKS = f"""# 计划跟踪

## 任务跟踪

{_TASK_COLS}
{_TASK_SEP}
{_task("TASK-001", "已完成")}
{_task("TASK-002", "进行中")}
{_task("TASK-003", "已完成")}
"""

    _PLAN_GATES = """# 计划跟踪

## Gate 状态跟踪

| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |
| --- | --- | --- | --- | --- |
| G1 | 立项 | passed | 2026-04-01 | EVD-001 |
| G2 | 调研 | passed-on-entry | 2026-04-02 | - |
"""

    def _write(self, tmpdir, content):
        sp = tmpdir / ".governance" / "plan-tracker.md"
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(content, encoding="utf-8")
        return sp

    def test_parse_completed_task_ids(self):
        with tempfile.TemporaryDirectory() as td:
            sp = self._write(Path(td), self._PLAN_TASKS)
            with patch.object(vw, "SAMPLE_PATH", sp):
                completed = vw.parse_completed_task_ids()
                self.assertEqual(completed, {"TASK-001", "TASK-003"})

    def test_parse_gate_status(self):
        with tempfile.TemporaryDirectory() as td:
            sp = self._write(Path(td), self._PLAN_GATES)
            with patch.object(vw, "SAMPLE_PATH", sp):
                gates = vw.parse_gate_status()
                self.assertEqual(len(gates), 2)
                self.assertEqual(gates[0]["gate"], "G1")
                self.assertEqual(gates[0]["status"], "passed")
                self.assertEqual(gates[1]["gate"], "G2")
                self.assertEqual(gates[1]["status"], "passed-on-entry")

    def test_parse_plan_tracker_empty(self):
        with tempfile.TemporaryDirectory() as td:
            sp = self._write(Path(td), "# empty\n")
            with patch.object(vw, "SAMPLE_PATH", sp):
                self.assertEqual(len(vw.parse_completed_task_ids()), 0)
                self.assertEqual(len(vw.parse_gate_status()), 0)

    def test_parse_plan_no_tasks_has_gates(self):
        with tempfile.TemporaryDirectory() as td:
            sp = self._write(Path(td), self._PLAN_GATES)
            with patch.object(vw, "SAMPLE_PATH", sp):
                self.assertEqual(len(vw.parse_completed_task_ids()), 0)
                self.assertEqual(len(vw.parse_gate_status()), 2)


class GovernanceIntegrationTests(unittest.TestCase):
    """Integration: check-governance against temp .governance/."""

    _PLAN = f"""# 计划跟踪

## 项目配置
- **Profile**: standard
- **触发模式**: always-on

## Gate 状态跟踪

| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |
| --- | --- | --- | --- | --- |
| G1 | 立项 | passed | 2026-04-01 | EVD-001 |

## 任务跟踪

{_TASK_COLS}
{_TASK_SEP}
{_task("TASK-001", "已完成")}
"""

    def _setup(self, tmpdir, plan=None, evidence=None, risk=None):
        gov = tmpdir / ".governance"; gov.mkdir(parents=True, exist_ok=True)
        sp = gov / "plan-tracker.md"
        ep = gov / "evidence-log.md"
        rp = gov / "risk-log.md"
        sp.write_text(plan or self._PLAN, encoding="utf-8")
        ep.write_text(evidence or "", encoding="utf-8")
        rp.write_text(risk or "", encoding="utf-8")
        return sp, ep, rp

    def test_evidence_completeness_all_covered(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            evidence = _evd_row("EVD-001", "TASK-001")
            sp, ep, rp = self._setup(root, evidence=evidence)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_evidence_completeness()
                self.assertEqual(r["completed_count"], 1)
                self.assertEqual(len(r["missing_evidence"]), 0)

    def test_evidence_completeness_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            evidence = _evd_row("EVD-999", "TASK-999")
            sp, ep, rp = self._setup(root, evidence=evidence)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_evidence_completeness()
                self.assertIn("TASK-001", r["missing_evidence"])

    def test_risk_staleness_fresh(self):
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            risk = _risk_row("RISK-001", today, "打开")
            sp, ep, rp = self._setup(root, risk=risk)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "RISK_PATH", rp):
                r = vw.check_risk_staleness()
                self.assertEqual(r["total_open"], 1)
                self.assertEqual(len(r["stale"]), 0)

    def test_risk_staleness_stale(self):
        from datetime import date, timedelta
        old = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            risk = _risk_row("RISK-001", old, "打开")
            sp, ep, rp = self._setup(root, risk=risk)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "RISK_PATH", rp):
                r = vw.check_risk_staleness()
                self.assertEqual(r["total_open"], 1)
                self.assertEqual(len(r["stale"]), 1)
                self.assertEqual(r["stale"][0][0], "RISK-001")

    def test_gate_consistency_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            evidence = _evd_row("EVD-001", "TASK-001")
            sp, ep, rp = self._setup(root, evidence=evidence)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep), \
                 patch.object(vw, "RISK_PATH", rp):
                issues = vw.check_gate_consistency()
                missing = [i for i in issues
                           if i.get("type") == "completed_tasks_missing_evidence"]
                self.assertEqual(len(missing), 0)

    def test_check_governance_runs_without_crash(self):
        """Individual governance check functions run without exception."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            evidence = _evd_row("EVD-001", "TASK-001")
            risk = _risk_row("RISK-001", "2026-05-01", "打开")
            sp, ep, rp = self._setup(root, evidence=evidence, risk=risk)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep), \
                 patch.object(vw, "RISK_PATH", rp):
                # Core governance checks exercised individually
                try:
                    r1 = vw.check_evidence_completeness()
                    self.assertEqual(r1["completed_count"], 1)
                except Exception as exc:
                    self.fail(f"check_evidence_completeness raised: {exc}")
                try:
                    r2 = vw.check_risk_staleness()
                    self.assertIsInstance(r2, dict)
                except Exception as exc:
                    self.fail(f"check_risk_staleness raised: {exc}")
                try:
                    r3 = vw.check_gate_consistency()
                    self.assertIsInstance(r3, list)
                except Exception as exc:
                    self.fail(f"check_gate_consistency raised: {exc}")


# ────────────────────────────────────────────────────────────
# SYSGAP-029: Goal Alignment (Check 11) and User Impact (Check 12) regression tests
# ────────────────────────────────────────────────────────────

def _impact_evidence_row(evd_id, task_id, description, file_location="skills/test.md"):
    """Build an evidence-log row with type=影响分析.

    Column layout matching evidence-log.md:
      | EVD-xxx | TASK-xxx | category | type | description | file_loc | author | date | gate | notes |
    parts[1]=evd_id  parts[2]=task_id  parts[3]=cat  parts[4]=type  parts[5]=desc  parts[6]=file
    """
    return f"| {evd_id} | {task_id} | 架构 | 影响分析 | {description} | {file_location} | Developer | 2026-05-02 | G11 | PASS |"


class GoalAlignmentTests(unittest.TestCase):
    """Test check_goal_alignment() — SYSGAP-023 Check 11."""

    GOAL_TEXT = (
        "This change aligns with the project goal of providing a comprehensive "
        "governance workflow for software projects with automated checks and "
        "cross-session state management."
    )

    def _setup(self, tmpdir, plan_config_lines=None, evidence_lines=None):
        """Create plan-tracker and evidence-log in temp dir; return (sp, ep)."""
        root = Path(tmpdir)
        gov = root / ".governance"; gov.mkdir(parents=True, exist_ok=True)
        sp = gov / "plan-tracker.md"
        ep = gov / "evidence-log.md"

        config_lines = plan_config_lines if plan_config_lines is not None else [
            "- **Profile**: standard",
            "- **触发模式**: always-on",
            "- **项目目标**: 提供一套完整的软件项目治理工作流插件",
        ]
        plan = "\n".join([
            "# 计划跟踪",
            "",
            "## 项目配置",
        ] + config_lines + [
            "",
            "## Gate 状态跟踪",
            "",
            "| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |",
            "| --- | --- | --- | --- | --- |",
            "| G1 | 立项 | passed | 2026-04-01 | EVD-001 |",
        ])
        sp.write_text(plan, encoding="utf-8")

        evidence = "\n".join(evidence_lines or [])
        ep.write_text(evidence, encoding="utf-8")
        return sp, ep

    def test_check_goal_alignment_all_pass(self):
        """plan-tracker has 项目目标 + evidence-log has 目标对齐 >= 30 chars -> PASS."""
        with tempfile.TemporaryDirectory() as td:
            evidence_rows = [
                _impact_evidence_row("EVD-001", "TASK-001",
                                     f"目标对齐: {self.GOAL_TEXT}"),
            ]
            sp, ep = self._setup(td, evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_goal_alignment()
                self.assertTrue(r["has_project_goal"])
                self.assertTrue(r["pass"])
                self.assertEqual(len(r["entries"]), 1)
                self.assertEqual(r["entries"][0]["status"], "PASS")
                self.assertTrue(r["entries"][0]["has_goal"])
                self.assertGreaterEqual(r["entries"][0]["goal_len"], 30)

    def test_check_goal_alignment_missing_project_goal(self):
        """plan-tracker has no 项目目标 -> has_project_goal=False (WARN indicator)."""
        with tempfile.TemporaryDirectory() as td:
            evidence_rows = [
                _impact_evidence_row("EVD-001", "TASK-001",
                                     f"目标对齐: {self.GOAL_TEXT}"),
            ]
            sp, ep = self._setup(td,
                                 plan_config_lines=["- **Profile**: standard"],
                                 evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_goal_alignment()
                self.assertFalse(r["has_project_goal"])
                self.assertEqual(r["project_goal"], "")
                # Entry still passes (goal alignment present in evidence)
                self.assertEqual(r["entries"][0]["status"], "PASS")

    def test_check_goal_alignment_missing_field(self):
        """Impact entry has no 目标对齐 field -> FAIL."""
        with tempfile.TemporaryDirectory() as td:
            evidence_rows = [
                _impact_evidence_row("EVD-002", "TASK-002",
                                     "No goal alignment info in this entry"),
            ]
            sp, ep = self._setup(td, evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_goal_alignment()
                self.assertFalse(r["pass"])
                self.assertEqual(len(r["entries"]), 1)
                self.assertFalse(r["entries"][0]["has_goal"])
                self.assertEqual(r["entries"][0]["status"], "FAIL")

    def test_check_goal_alignment_too_short(self):
        """目标对齐 text < 30 chars -> FAIL."""
        with tempfile.TemporaryDirectory() as td:
            evidence_rows = [
                _impact_evidence_row("EVD-003", "TASK-003",
                                     "目标对齐: Too short"),
            ]
            sp, ep = self._setup(td, evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_goal_alignment()
                self.assertFalse(r["pass"])
                self.assertEqual(len(r["entries"]), 1)
                self.assertTrue(r["entries"][0]["has_goal"])
                self.assertLess(r["entries"][0]["goal_len"], 30)
                self.assertEqual(r["entries"][0]["status"], "FAIL")


class UserImpactTests(unittest.TestCase):
    """Test check_user_impact() — SYSGAP-024 Check 12."""

    def _setup(self, tmpdir, evidence_lines=None):
        """Create evidence-log in temp dir. plan-tracker not needed for user_impact."""
        root = Path(tmpdir)
        gov = root / ".governance"; gov.mkdir(parents=True, exist_ok=True)
        plan = "\n".join([
            "# 计划跟踪",
            "",
            "## 项目配置",
            "- **Profile**: standard",
            "",
            "## Gate 状态跟踪",
            "| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |",
            "| --- | --- | --- | --- | --- |",
            "| G1 | 立项 | passed | 2026-04-01 | EVD-001 |",
        ])
        sp = gov / "plan-tracker.md"
        sp.write_text(plan, encoding="utf-8")
        ep = gov / "evidence-log.md"
        ep.write_text("\n".join(evidence_lines or []), encoding="utf-8")
        return sp, ep

    def test_check_user_impact_all_pass(self):
        """用户影响 field complete with valid values -> PASS."""
        with tempfile.TemporaryDirectory() as td:
            desc = (
                "用户影响: 获得=plugin update, 感知=下次会话启动时自动检测, "
                "体验变化=否, 迁移指南=不需要"
            )
            evidence_rows = [
                _impact_evidence_row("EVD-001", "TASK-001", desc),
            ]
            sp, ep = self._setup(td, evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_user_impact()
                self.assertTrue(r["pass"])
                self.assertEqual(len(r["entries"]), 1)
                entry = r["entries"][0]
                self.assertEqual(entry["status"], "PASS")
                self.assertTrue(entry["has_field"])
                self.assertEqual(entry["obtain"], "plugin update")
                self.assertEqual(entry["perceive"], "下次会话启动时自动检测")
                self.assertEqual(entry["exp_change"], "否")
                self.assertEqual(entry["migration"], "不需要")
                self.assertEqual(len(entry["issues"]), 0)

    def test_check_user_impact_missing_field(self):
        """No 用户影响 field -> FAIL."""
        with tempfile.TemporaryDirectory() as td:
            evidence_rows = [
                _impact_evidence_row("EVD-002", "TASK-002",
                                     "No user impact info here"),
            ]
            sp, ep = self._setup(td, evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_user_impact()
                self.assertFalse(r["pass"])
                self.assertEqual(len(r["entries"]), 1)
                entry = r["entries"][0]
                self.assertFalse(entry["has_field"])
                self.assertEqual(entry["status"], "FAIL")
                self.assertIn("缺少 用户影响", entry["issues"][0])

    def test_check_user_impact_invalid_obtain_value(self):
        """获得= value not in valid set -> WARN."""
        with tempfile.TemporaryDirectory() as td:
            desc = (
                "用户影响: 获得=unknown_method, 感知=visible, "
                "体验变化=否, 迁移指南=不需要"
            )
            evidence_rows = [
                _impact_evidence_row("EVD-003", "TASK-003", desc),
            ]
            sp, ep = self._setup(td, evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_user_impact()
                # WARN does NOT set pass=False (only FAIL/BLOCKING do)
                self.assertTrue(r["pass"])
                self.assertEqual(len(r["entries"]), 1)
                entry = r["entries"][0]
                self.assertEqual(entry["status"], "WARN")
                self.assertEqual(entry["obtain"], "unknown_method")
                self.assertEqual(len(entry["issues"]), 1)
                self.assertIn("获得=", entry["issues"][0])
                self.assertIn("unknown_method", entry["issues"][0])

    def test_check_user_impact_breaking_change_no_migration_guide(self):
        """体验变化=是 + 迁移指南=不需要 -> BLOCKING."""
        with tempfile.TemporaryDirectory() as td:
            desc = (
                "用户影响: 获得=plugin update, 感知=需要手动运行迁移命令, "
                "体验变化=是, 迁移指南=不需要"
            )
            evidence_rows = [
                _impact_evidence_row("EVD-004", "TASK-004", desc),
            ]
            sp, ep = self._setup(td, evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_user_impact()
                self.assertFalse(r["pass"])
                self.assertEqual(len(r["entries"]), 1)
                entry = r["entries"][0]
                self.assertEqual(entry["status"], "BLOCKING")
                self.assertEqual(entry["exp_change"], "是")
                self.assertEqual(entry["migration"], "不需要")
                self.assertIn("TASK-004", r["blocking"])
                self.assertIn("迁移指南=不需要", entry["issues"][0])


# ────────────────────────────────────────────────────────────
# SYSGAP-039: Agent Team Review + Agent Activation regression tests
# ────────────────────────────────────────────────────────────

def _evidence_row_generic(evd_id, task_id, category="开发", evd_type="实现",
                           description="test", file_location="skills/test.py",
                           author="Developer", date_str="2026-05-02",
                           gate="G4", notes="PASS"):
    """Build a generic evidence-log row with configurable type and file location.

    Column layout: | EVD-xxx | TASK-xxx | cat | type | desc | file | author | date | gate | notes |
    """
    return (
        f"| {evd_id} | {task_id} | {category} | {evd_type} | {description} | "
        f"{file_location} | {author} | {date_str} | {gate} | {notes} |"
    )


def _task_with_priority(tid, priority="P1", status="已完成"):
    """Build a task row with priority at parts[11] and status at parts[10].

    Column layout matching check_agent_activation() column indices:
    | 任务ID | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | 状态 | 优先级 |
    parts:   1     2    3    4    5    6    7    8    9    10      11
    """
    return f"| {tid} | x | x | x | x | x | x | x | x | {status} | {priority} |"


class AgentTeamReviewTests(unittest.TestCase):
    """Test check_agent_team_review() — SYSGAP-035 (Check 18)."""

    def _setup(self, tmpdir, plan_lines=None, evidence_lines=None):
        """Create plan-tracker and evidence-log in temp dir; return (sp, ep)."""
        root = Path(tmpdir)
        gov = root / ".governance"; gov.mkdir(parents=True, exist_ok=True)
        sp = gov / "plan-tracker.md"
        ep = gov / "evidence-log.md"

        plan = "\n".join(plan_lines or [])
        sp.write_text(plan, encoding="utf-8")
        ep.write_text("\n".join(evidence_lines or []), encoding="utf-8")
        return sp, ep

    def test_check_agent_team_review_all_pass(self):
        """Product code task completed + REVIEW evidence entry (REVIEW- prefix) -> PASS."""
        with tempfile.TemporaryDirectory() as td:
            plan = "\n".join([
                "# 计划跟踪",
                "",
                "## 任务跟踪",
                _TASK_COLS,
                _TASK_SEP,
                _task("TASK-001", "已完成"),
            ])
            # Two evidence entries: product code task + separate REVIEW entry
            evidence_rows = [
                _evidence_row_generic(
                    "EVD-001", "TASK-001",
                    evd_type="实现",
                    file_location="skills/software-project-governance/SKILL.md",
                    author="Developer",
                ),
                _evidence_row_generic(
                    "EVD-002", "REVIEW-TASK-001",
                    category="审查",
                    evd_type="Code Review",
                    description="Reviewed TASK-001",
                    file_location=".governance/review-REVIEW-TASK-001.md",
                    author="Code Reviewer",
                ),
            ]
            sp, ep = self._setup(td, plan_lines=[plan], evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_agent_team_review()
                self.assertTrue(r["pass"])
                self.assertEqual(r["total_tasks"], 1)
                self.assertEqual(r["reviewed"], 1)
                self.assertEqual(r["unreviewed"], 0)
                self.assertEqual(len(r["review_gap_tasks"]), 0)

    def test_check_agent_team_review_missing_evidence(self):
        """Product code task completed but no REVIEW evidence -> FAIL."""
        with tempfile.TemporaryDirectory() as td:
            plan = "\n".join([
                "# 计划跟踪",
                "",
                "## 任务跟踪",
                _TASK_COLS,
                _TASK_SEP,
                _task("TASK-001", "已完成"),
            ])
            evidence_rows = [
                _evidence_row_generic(
                    "EVD-001", "TASK-001",
                    evd_type="实现",
                    file_location="skills/software-project-governance/SKILL.md",
                    author="Developer",
                ),
            ]
            sp, ep = self._setup(td, plan_lines=[plan], evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_agent_team_review()
                self.assertFalse(r["pass"])
                self.assertIn("TASK-001", r["review_gap_tasks"])
                self.assertEqual(r["unreviewed"], 1)
                self.assertEqual(r["reviewed"], 0)

    def test_check_agent_team_review_no_product_code(self):
        """Governance record task no review requirement -> PASS (not counted as product code)."""
        with tempfile.TemporaryDirectory() as td:
            plan = "\n".join([
                "# 计划跟踪",
                "",
                "## 任务跟踪",
                _TASK_COLS,
                _TASK_SEP,
                _task("TASK-001", "已完成"),
            ])
            evidence_rows = [
                _evidence_row_generic(
                    "EVD-001", "TASK-001",
                    evd_type="记录",
                    file_location=".governance/plan-tracker.md",
                    author="Coordinator",
                ),
            ]
            sp, ep = self._setup(td, plan_lines=[plan], evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_agent_team_review()
                self.assertTrue(r["pass"])
                self.assertEqual(r["total_tasks"], 0)
                self.assertEqual(r["reviewed"], 0)
                self.assertEqual(r["unreviewed"], 0)


class AgentActivationTests(unittest.TestCase):
    """Test check_agent_activation() — SYSGAP-036 (Check 19)."""

    def _setup(self, tmpdir, plan_lines=None, evidence_lines=None):
        """Create plan-tracker and evidence-log in temp dir; return (sp, ep)."""
        root = Path(tmpdir)
        gov = root / ".governance"; gov.mkdir(parents=True, exist_ok=True)
        sp = gov / "plan-tracker.md"
        ep = gov / "evidence-log.md"

        plan = "\n".join(plan_lines or [])
        sp.write_text(plan, encoding="utf-8")
        ep.write_text("\n".join(evidence_lines or []), encoding="utf-8")
        return sp, ep

    def test_check_agent_activation_all_pass(self):
        """P0 task + cross-layer product code + Analyst involvement -> PASS."""
        with tempfile.TemporaryDirectory() as td:
            plan = "\n".join([
                "# 计划跟踪",
                "",
                "## 任务跟踪",
                _TASK_COLS,
                _TASK_SEP,
                _task_with_priority("TASK-001", priority="P0", status="已完成"),
            ])
            # Two evidence entries: impact analysis + implementation,
            # touching two architecture layers (skills/ and commands/)
            evidence_rows = [
                _evidence_row_generic(
                    "EVD-001", "TASK-001",
                    category="架构",
                    evd_type="影响分析",
                    description="目标对齐: cross-layer impact analysis",
                    file_location="skills/software-project-governance/SKILL.md",
                    author="Analyst",
                    gate="G11",
                ),
                _evidence_row_generic(
                    "EVD-002", "TASK-001",
                    category="开发",
                    evd_type="实现",
                    description="Implementation",
                    file_location="commands/governance-status.md",
                    author="Developer",
                    gate="G11",
                ),
            ]
            sp, ep = self._setup(td, plan_lines=[plan], evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_agent_activation()
                self.assertTrue(r["pass"])
                self.assertEqual(r["total_p0_cross_layer"], 1)
                self.assertEqual(r["analyst_activated"], 1)
                self.assertEqual(r["analyst_bypassed"], 0)
                self.assertEqual(len(r["bypassed_tasks"]), 0)

    def test_check_agent_activation_no_analyst(self):
        """P0 + cross-layer + Coordinator-only impact analysis -> FAIL."""
        with tempfile.TemporaryDirectory() as td:
            plan = "\n".join([
                "# 计划跟踪",
                "",
                "## 任务跟踪",
                _TASK_COLS,
                _TASK_SEP,
                _task_with_priority("TASK-001", priority="P0", status="已完成"),
            ])
            # Two evidence entries across two layers: skills/ and agents/
            evidence_rows = [
                _evidence_row_generic(
                    "EVD-001", "TASK-001",
                    category="架构",
                    evd_type="影响分析",
                    description="Coordinator performed impact analysis solo",
                    file_location="skills/software-project-governance/SKILL.md",
                    author="Coordinator",
                    gate="G11",
                ),
                _evidence_row_generic(
                    "EVD-002", "TASK-001",
                    category="开发",
                    evd_type="实现",
                    description="Implementation",
                    file_location="agents/developer.md",
                    author="Developer",
                    gate="G11",
                ),
            ]
            sp, ep = self._setup(td, plan_lines=[plan], evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_agent_activation()
                self.assertFalse(r["pass"])
                self.assertEqual(r["total_p0_cross_layer"], 1)
                self.assertEqual(r["analyst_bypassed"], 1)
                self.assertIn("TASK-001", r["bypassed_tasks"])
                self.assertEqual(r["analyst_activated"], 0)

    def test_check_agent_activation_not_p0(self):
        """Non-P0 task skipped -> PASS (no P0 tasks found)."""
        with tempfile.TemporaryDirectory() as td:
            plan = "\n".join([
                "# 计划跟踪",
                "",
                "## 任务跟踪",
                _TASK_COLS,
                _TASK_SEP,
                _task_with_priority("TASK-001", priority="P1", status="已完成"),
            ])
            evidence_rows = [
                _evidence_row_generic(
                    "EVD-001", "TASK-001",
                    evd_type="实现",
                    file_location="skills/test.py",
                    author="Developer",
                ),
            ]
            sp, ep = self._setup(td, plan_lines=[plan], evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_agent_activation()
                self.assertTrue(r["pass"])
                self.assertEqual(r["total_p0_cross_layer"], 0)
                self.assertEqual(r["analyst_activated"], 0)
                self.assertEqual(r["analyst_bypassed"], 0)


if __name__ == "__main__":
    unittest.main()
