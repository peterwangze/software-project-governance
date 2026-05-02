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


if __name__ == "__main__":
    unittest.main()
