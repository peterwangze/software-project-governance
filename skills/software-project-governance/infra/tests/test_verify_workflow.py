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
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
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


class ArchitectureFactSourceTests(unittest.TestCase):
    """FIX-065: architecture facts must stay synchronized across sources."""

    def _write_fact_files(
        self,
        root,
        skill_extra="",
        skill_index_operations_agents="Coordinator, DevOps, Maintenance",
        architecture_extra="",
        governance_route_count=18,
    ):
        skill = root / "SKILL.md"
        skill.write_text(
            "# 软件项目治理工作流入口\n\n"
            "Coordinator 融入入口层。\n"
            "13 个文件化角色 Agent；14 个角色含 Coordinator。\n"
            "Coordinator 接管用户交互。\n"
            "Producer-Reviewer 分离。\n\n"
            "## Agent 分发路由\n\n"
            "| 任务类型 | 执行 Agent | 后置审查 Agent(s) | 触发条件 | 核心方法论 |\n"
            "| --- | --- | --- | --- | --- |\n"
            + "\n".join(
                f"| Route {i:02d} | Agent | Reviewer | 自动 | Method |"
                for i in range(1, 19)
            )
            + f"\n{skill_extra}\n\n## Sub-agent 调度\n",
            encoding="utf-8",
        )

        skill_index = root / "skill-index.md"
        skill_index.write_text(
            "# SKILL 分类索引\n\n"
            "| SKILL | 路径 | 用途 | 调用 Agent |\n"
            "| --- | --- | --- | --- |\n"
            f"| stage-operations | `skills/stage-operations/SKILL.md` | 运营与反馈 | {skill_index_operations_agents} |\n",
            encoding="utf-8",
        )

        architecture = root / "architecture.md"
        architecture.write_text(
            "# 六层架构设计\n\n"
            "入口层 SKILL.md 内嵌 Coordinator 身份、路由、边界和参考索引。\n"
            "仓库根目录 CLAUDE.md 当前存在但未被 git 跟踪；core/manifest.json root_entries 声明它。\n"
            f"{architecture_extra}\n",
            encoding="utf-8",
        )

        governance = root / "governance.md"
        governance.write_text(
            "# /governance\n\n"
            f"完整路由表（{governance_route_count} 行）见 `skills/software-project-governance/SKILL.md`。\n",
            encoding="utf-8",
        )
        return skill, skill_index, architecture, governance

    def test_architecture_fact_source_accepts_current_facts(self):
        with tempfile.TemporaryDirectory() as td:
            paths = self._write_fact_files(Path(td))
            self.assertEqual(vw.check_architecture_fact_source(*paths), [])

    def test_architecture_fact_source_external_paths_do_not_call_is_relative_to(self):
        with tempfile.TemporaryDirectory() as td:
            paths = self._write_fact_files(Path(td))
            concrete_path_type = type(paths[0])
            with patch.object(
                concrete_path_type,
                "is_relative_to",
                side_effect=AssertionError("Path.is_relative_to must not be called"),
                create=True,
            ):
                self.assertEqual(vw.check_architecture_fact_source(*paths), [])

    def test_architecture_fact_source_rejects_legacy_agent_count(self):
        with tempfile.TemporaryDirectory() as td:
            paths = self._write_fact_files(
                Path(td),
                architecture_extra="Agent 职能分组（7 组 9 Agent，按项目运作职能组织）",
            )
            issues = vw.check_architecture_fact_source(*paths)
            self.assertTrue(any("7 groups / 9 Agent" in issue for issue in issues))

    def test_architecture_fact_source_rejects_release_operations_binding(self):
        with tempfile.TemporaryDirectory() as td:
            paths = self._write_fact_files(
                Path(td),
                skill_index_operations_agents="Coordinator, Release",
            )
            issues = vw.check_architecture_fact_source(*paths)
            self.assertTrue(any("stage-operations must not be bound to Release" in issue for issue in issues))

    def test_architecture_fact_source_rejects_legacy_entry_narratives(self):
        with tempfile.TemporaryDirectory() as td:
            paths = self._write_fact_files(
                Path(td),
                architecture_extra=(
                    "主 SKILL.md 46 行入口。\n"
                    "不包含任何行为规则。\n"
                    "仓库不包含任何平台原生入口文件。"
                ),
            )
            issues = vw.check_architecture_fact_source(*paths)
            self.assertTrue(any("46-line" in issue for issue in issues))
            self.assertTrue(any("no behavior rules" in issue for issue in issues))
            self.assertTrue(any("native-entry exclusion" in issue for issue in issues))

    def test_architecture_fact_source_rejects_route_count_drift(self):
        with tempfile.TemporaryDirectory() as td:
            paths = self._write_fact_files(Path(td), governance_route_count=16)
            issues = vw.check_architecture_fact_source(*paths)
            self.assertTrue(any("route table count 16 does not match SKILL.md actual 18" in issue for issue in issues))

    def test_architecture_fact_source_requires_key_phrases(self):
        with tempfile.TemporaryDirectory() as td:
            paths = self._write_fact_files(
                Path(td),
                skill_extra="\n",
            )
            skill, skill_index, architecture, governance = paths
            skill.write_text(skill.read_text(encoding="utf-8").replace("Producer-Reviewer 分离。\n", ""), encoding="utf-8")
            issues = vw.check_architecture_fact_source(skill, skill_index, architecture, governance)
            self.assertTrue(any("Producer-Reviewer 分离" in issue for issue in issues))


class E2ECommandMatrixTests(unittest.TestCase):
    """FIX-060: e2e-check must execute real command proxies."""

    def test_e2e_matrix_entry_invokes_subprocess(self):
        entry = vw._e2e_command_matrix()[0]
        completed = subprocess.CompletedProcess(
            entry["command"],
            0,
            stdout="Project Overview\nTasks\nGate\npermission_mode\n操作权限模式\nmaximum-autonomy\n",
            stderr="",
        )

        with patch.object(vw.subprocess, "run", return_value=completed) as run:
            result = vw._evaluate_e2e_command(entry)

        self.assertEqual(result["status"], "PASS")
        run.assert_called_once()
        args, kwargs = run.call_args
        self.assertEqual(args[0], entry["command"])
        self.assertTrue(kwargs["capture_output"])
        self.assertEqual(kwargs["cwd"], str(vw.ROOT))

    def test_e2e_status_validator_requires_permission_mode_label(self):
        entry = vw._e2e_command_matrix()[0]
        completed = subprocess.CompletedProcess(
            entry["command"],
            0,
            stdout="Project Overview\nTasks\nGate\nmaximum-autonomy\n",
            stderr="",
        )

        result = vw._evaluate_e2e_command(
            entry,
            runner=lambda command: completed,
        )

        self.assertEqual(result["status"], "FAIL")
        self.assertIn("permission_mode", result["message"])

    def test_e2e_status_validator_accepts_default_confirm_permission_mode(self):
        entry = vw._e2e_command_matrix()[0]
        completed = subprocess.CompletedProcess(
            entry["command"],
            0,
            stdout="Project Overview\nTasks\nGate\npermission_mode\n操作权限模式\ndefault-confirm\n",
            stderr="",
        )

        result = vw._evaluate_e2e_command(
            entry,
            runner=lambda command: completed,
        )

        self.assertEqual(result["status"], "PASS")

    def _known_verify_failure_output(self, extra_failure=None, subset=False):
        if subset:
            lines = [
                "== Workflow Plugin Verification ==",
                "",
                "== Verification Result: FAILED ==",
                "  - missing snippet in skills\\software-project-governance\\SKILL.md: Coordinator 接管用户交互",
                "  - missing snippet in skills/software-project-governance/SKILL.md: Producer-Reviewer 分离",
            ]
        else:
            lines = [
                "== Workflow Plugin Verification ==",
                "",
                "== Verification Result: FAILED ==",
                "  - missing snippet in .governance\\evidence-log.md: EVD-001",
                "  - missing snippet in .governance/evidence-log.md: EVD-051",
                "  - missing snippet in skills\\software-project-governance\\SKILL.md: Coordinator 接管用户交互",
                "  - missing snippet in skills/software-project-governance/SKILL.md: Producer-Reviewer 分离",
            ]
        if extra_failure:
            lines.append(f"  - {extra_failure}")
        return "\n".join(lines)

    def test_expected_known_failure_accepts_full_allowed_set(self):
        entry = {
            "label": "/governance-verify",
            "command": ["python", "verify_workflow.py", "verify"],
            "validator": vw._validate_e2e_verify_known_failure,
            "expected_known_failure": True,
        }

        result = vw._evaluate_e2e_command(
            entry,
            runner=lambda command: subprocess.CompletedProcess(
                command,
                1,
                stdout=self._known_verify_failure_output(),
                stderr="",
            ),
        )

        self.assertEqual(result["status"], "EXPECTED_KNOWN_FAILURE")
        self.assertEqual(result["exit_code"], 1)

    def test_expected_known_failure_entry_accepts_verify_pass(self):
        entry = {
            "label": "/governance-verify",
            "command": ["python", "verify_workflow.py", "verify"],
            "validator": vw._validate_e2e_verify_known_failure,
            "expected_known_failure": True,
        }

        result = vw._evaluate_e2e_command(
            entry,
            runner=lambda command: subprocess.CompletedProcess(
                command,
                0,
                stdout="== Workflow Plugin Verification ==\n\n== Verification Result: PASSED ==\n",
                stderr="",
            ),
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["exit_code"], 0)

    def test_expected_known_failure_accepts_known_signature_subset(self):
        entry = {
            "label": "/governance-verify",
            "command": ["python", "verify_workflow.py", "verify"],
            "validator": vw._validate_e2e_verify_known_failure,
            "expected_known_failure": True,
        }

        result = vw._evaluate_e2e_command(
            entry,
            runner=lambda command: subprocess.CompletedProcess(
                command,
                1,
                stdout=self._known_verify_failure_output(subset=True),
                stderr="",
            ),
        )

        self.assertEqual(result["status"], "EXPECTED_KNOWN_FAILURE")
        self.assertIn("known allowed signatures", result["message"])

    def test_expected_known_failure_rejects_generic_failure(self):
        entry = {
            "label": "/governance-verify",
            "command": ["python", "verify_workflow.py", "verify"],
            "validator": vw._validate_e2e_verify_known_failure,
            "expected_known_failure": True,
        }

        result = vw._evaluate_e2e_command(
            entry,
            runner=lambda command: subprocess.CompletedProcess(
                command,
                1,
                stdout="== Workflow Plugin Verification ==\n== Verification Result: FAILED ==\n  - missing snippet in README.md: NOT FOUND\n",
                stderr="",
            ),
        )

        self.assertEqual(result["status"], "FAIL")
        self.assertIn("did not match allowed known signatures", result["message"])

    def test_expected_known_failure_rejects_extra_unknown_failure(self):
        entry = {
            "label": "/governance-verify",
            "command": ["python", "verify_workflow.py", "verify"],
            "validator": vw._validate_e2e_verify_known_failure,
            "expected_known_failure": True,
        }

        result = vw._evaluate_e2e_command(
            entry,
            runner=lambda command: subprocess.CompletedProcess(
                command,
                1,
                stdout=self._known_verify_failure_output(
                    "missing snippet in commands/governance.md: NEW-REGRESSION"
                ),
                stderr="",
            ),
        )

        self.assertEqual(result["status"], "FAIL")
        self.assertIn("unknown failures", result["message"])

    def test_e2e_check_summary_separates_source_proxy_and_target_fixture(self):
        fake_entries = [{"label": "pass"}, {"label": "known"}]
        fake_results = [
            {
                "label": "/governance-status",
                "kind": "source_cli_proxy",
                "status": "PASS",
                "exit_code": 0,
                "message": "status executed",
                "command": ["python", "verify_workflow.py", "status"],
            },
            {
                "label": "/governance-verify",
                "kind": "source_cli_proxy",
                "status": "EXPECTED_KNOWN_FAILURE",
                "exit_code": 1,
                "message": "known failure observed",
                "command": ["python", "verify_workflow.py", "verify"],
            },
        ]
        fake_fixture_results = [
            {
                "label": "target plan-tracker project config",
                "status": "PASS",
                "message": "fixture content matches expected markers",
            }
        ]

        with patch.object(vw, "_e2e_command_matrix", return_value=fake_entries), \
             patch.object(vw, "_evaluate_e2e_command", side_effect=fake_results), \
             patch.object(vw, "_e2e_target_fixture_checks", return_value=[{"label": "fixture"}]), \
             patch.object(vw, "_evaluate_e2e_target_fixture_check", side_effect=fake_fixture_results), \
             patch.object(vw, "_e2e_contract_checks", return_value=[]):
            output = io.StringIO()
            with redirect_stdout(output):
                vw.cmd_e2e_check(None)

        text = output.getvalue()
        self.assertIn("Source CLI proxy command matrix", text)
        self.assertIn("Target fixture checks", text)
        self.assertIn("source_cli_proxy_pass=1", text)
        self.assertIn("expected_known_failure=1", text)
        self.assertIn("target_fixture_pass=1", text)
        self.assertIn("contract_only=0", text)
        self.assertNotIn("executed_pass=", text)
        self.assertNotIn("19/19", text)
        self.assertNotIn("Category A", text)

    def test_e2e_check_fails_when_target_fixture_fails(self):
        fake_source = {
            "label": "/governance-status",
            "kind": "source_cli_proxy",
            "status": "PASS",
            "exit_code": 0,
            "message": "status executed",
            "command": ["python", "verify_workflow.py", "status"],
        }
        fake_fixture = {
            "label": "target plan-tracker project config",
            "status": "FAIL",
            "message": "missing markers=['操作权限模式']",
        }

        with patch.object(vw, "_e2e_command_matrix", return_value=[{"label": "pass"}]), \
             patch.object(vw, "_evaluate_e2e_command", return_value=fake_source), \
             patch.object(vw, "_e2e_target_fixture_checks", return_value=[{"label": "fixture"}]), \
             patch.object(vw, "_evaluate_e2e_target_fixture_check", return_value=fake_fixture), \
             patch.object(vw, "_e2e_contract_checks", return_value=[]):
            output = io.StringIO()
            with self.assertRaises(SystemExit) as cm, redirect_stdout(output):
                vw.cmd_e2e_check(None)

        self.assertEqual(cm.exception.code, 1)
        self.assertIn("target_fixture_fail=1", output.getvalue())


class GovernanceStatusContractTests(unittest.TestCase):
    """FIX-064: status contracts must expose operation permission mode."""

    def test_cmd_status_outputs_stable_permission_mode_line(self):
        plan = "\n".join([
            "# 计划跟踪",
            "",
            "## 项目配置",
            "- **项目目标**: test",
            "- **Profile**: standard",
            "- **触发模式**: always-on",
            "- **操作权限模式**: maximum-autonomy",
            "- **当前阶段**: 维护",
            "",
            "## Gate 状态跟踪",
            "| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |",
            "| --- | --- | --- | --- | --- |",
            "| G11 | → 下一轮 | passed | 2026-05-13 | done |",
            "",
            "## 项目总览",
            "| 项目 | 当前阶段 | 总任务数 | 已完成 | 阻塞中 | 关键风险数 | 最近 Gate 结论 | 最近复盘日期 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
            "| Demo | 维护 | 1 | 1 | 0 | 0 | G11 通过 | 2026-05-13 |",
            "",
            "## 任务跟踪",
            _TASK_COLS,
            _TASK_SEP,
            _task("FIX-064", status="已完成"),
        ])
        with tempfile.TemporaryDirectory() as td:
            sample = Path(td) / "plan-tracker.md"
            sample.write_text(plan, encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sample):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    vw.cmd_status(None)

        output = buf.getvalue()
        self.assertIn("Permission Mode (permission_mode / 操作权限模式): maximum-autonomy", output)
        self.assertIn("Project Overview", output)

    def test_governance_status_docs_require_permission_mode(self):
        text = (vw.ROOT / "commands" / "governance-status.md").read_text(encoding="utf-8")

        required = [
            "操作权限模式 permission_mode",
            "| permission_mode |",
            "操作权限模式: {permission_mode}",
            "不得只依赖项目配置原始字段顺序偶然展示",
        ]
        missing = [needle for needle in required if needle not in text]
        self.assertEqual(missing, [])

    def test_governance_scenario_c_matches_continuous_archive_step_e(self):
        governance = (vw.ROOT / "commands" / "governance.md").read_text(encoding="utf-8")
        init = (vw.ROOT / "commands" / "governance-init.md").read_text(encoding="utf-8")

        required = [
            "持续归档触发检测与执行",
            "archive.py migrate --auto --dry-run",
            "archive.py migrate --auto",
            "verify_workflow.py check-archive-integrity",
            "发布/版本 bump 收尾场景 MUST 阻断完成",
            "无可归档数据",
        ]
        self.assertEqual([needle for needle in required if needle not in governance], [])
        self.assertEqual([needle for needle in required if needle not in init], [])


class GovernanceReviewFallbackPolicyTests(unittest.TestCase):
    """FIX-061: /governance-review must not allow Coordinator self-review fallback."""

    VALID_COMMAND = """
# governance-review

## 错误码

| 代码 | 条件 | 动作 |
|------|------|------|
| REVIEW-ERR-003 | Reviewer Agent 不可用 | 先尝试平台 Reviewer spawn/fallback（`general-purpose` + Reviewer role prompt + 审查 SKILL）；仍不可用则 `BLOCKED` 或仅写 degraded evidence。Coordinator MUST NOT 自审；degraded evidence 不构成独立审查、不得解锁交付 |
"""

    def test_review_fallback_policy_requires_source_file(self):
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "commands" / "governance-review.md"

            result = vw.check_governance_review_fallback_policy(
                required_paths=[missing],
                optional_paths=[],
            )

        self.assertFalse(result["pass"])
        issue_types = {issue["type"] for issue in result["issues"]}
        self.assertIn("missing_file", issue_types)

    def test_review_fallback_policy_accepts_compliant_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            command = root / "commands" / "governance-review.md"
            command.parent.mkdir(parents=True)
            command.write_text(self.VALID_COMMAND, encoding="utf-8")

            result = vw.check_governance_review_fallback_policy(
                required_paths=[command],
                optional_paths=[],
            )

        self.assertTrue(result["pass"], result["issues"])
        self.assertEqual(result["files_checked"], 1)
        self.assertEqual(result["issues"], [])

    def test_review_fallback_policy_rejects_coordinator_self_review(self):
        with tempfile.TemporaryDirectory() as td:
            command = Path(td) / "governance-review.md"
            command.write_text(
                "| REVIEW-ERR-003 | Reviewer Agent 不可用 | "
                "降级为 Coordinator 执行审查（标注\"非独立审查\"） |",
                encoding="utf-8",
            )

            result = vw.check_governance_review_fallback_policy(
                required_paths=[command],
                optional_paths=[],
            )

        self.assertFalse(result["pass"])
        issue_types = {issue["type"] for issue in result["issues"]}
        self.assertIn("coordinator_self_review_fallback", issue_types)

    def test_review_fallback_policy_skips_missing_optional_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            command = root / "commands" / "governance-review.md"
            fixture = root / "project" / "e2e-test-project" / "commands" / "governance-review.md"
            command.parent.mkdir(parents=True)
            command.write_text(self.VALID_COMMAND, encoding="utf-8")

            result = vw.check_governance_review_fallback_policy(
                required_paths=[command],
                optional_paths=[fixture],
            )

        self.assertTrue(result["pass"], result["issues"])
        self.assertEqual(result["files_checked"], 1)
        self.assertEqual(result["optional_skipped"], [fixture.as_posix()])

    def test_review_fallback_policy_checks_optional_fixture_when_present(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            command = root / "commands" / "governance-review.md"
            fixture = root / "project" / "e2e-test-project" / "commands" / "governance-review.md"
            command.parent.mkdir(parents=True)
            fixture.parent.mkdir(parents=True)
            command.write_text(self.VALID_COMMAND, encoding="utf-8")
            fixture.write_text(
                "| REVIEW-ERR-003 | Reviewer Agent 不可用 | "
                "降级为 Coordinator 执行审查（标注\"非独立审查\"） |",
                encoding="utf-8",
            )

            result = vw.check_governance_review_fallback_policy(
                required_paths=[command],
                optional_paths=[fixture],
            )

        self.assertFalse(result["pass"])
        self.assertEqual(result["files_checked"], 2)
        issue_types = {issue["type"] for issue in result["issues"]}
        self.assertIn("coordinator_self_review_fallback", issue_types)

    def test_repository_governance_review_commands_match_policy(self):
        result = vw.check_governance_review_fallback_policy()

        self.assertTrue(result["pass"], result["issues"])
        self.assertGreaterEqual(result["files_checked"], 1)


class StageSkillPathTests(unittest.TestCase):
    """Test canonical stage workflow SKILL.md path mapping."""

    def test_stage_skill_path_uses_top_level_stage_skill(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.object(vw, "ROOT", root), \
                 patch.object(vw, "STAGE_SKILLS_ROOT", root / "skills"):
                self.assertEqual(
                    vw.stage_skill_path("development"),
                    root / "skills" / "stage-development" / "SKILL.md",
                )

    def test_stage_skill_path_normalizes_infra_and_cicd_aliases(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.object(vw, "ROOT", root), \
                 patch.object(vw, "STAGE_SKILLS_ROOT", root / "skills"):
                self.assertEqual(
                    vw.stage_skill_path("infrastructure"),
                    root / "skills" / "stage-infra" / "SKILL.md",
                )
                self.assertEqual(
                    vw.stage_skill_path("infra"),
                    root / "skills" / "stage-infra" / "SKILL.md",
                )
                self.assertEqual(
                    vw.stage_skill_path("ci-cd"),
                    root / "skills" / "stage-cicd" / "SKILL.md",
                )
                self.assertEqual(
                    vw.stage_skill_path("stage-cicd"),
                    root / "skills" / "stage-cicd" / "SKILL.md",
                )

    def test_list_available_stages_reads_stage_skill_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            skills = root / "skills"
            (skills / "stage-development").mkdir(parents=True)
            (skills / "stage-development" / "SKILL.md").write_text("# dev", encoding="utf-8")
            (skills / "stage-infra").mkdir()
            (skills / "stage-infra" / "SKILL.md").write_text("# infra", encoding="utf-8")

            with patch.object(vw, "ROOT", root), \
                 patch.object(vw, "STAGE_SKILLS_ROOT", skills):
                stages = vw.list_available_stages()
                self.assertIn("development", stages)
                self.assertIn("infrastructure", stages)

    def test_legacy_stages_dir_constant_removed(self):
        self.assertFalse(hasattr(vw, "STAGES" + "_DIR"))

    def test_authorized_files_do_not_reference_legacy_stage_workflows(self):
        files_to_scan = [
            "commands/governance-gate.md",
            "skills/software-project-governance/infra/verify_workflow.py",
            "skills/software-project-governance/infra/tests/test_verify_workflow.py",
            "skills/software-project-governance/core/onboarding.md",
            "skills/software-project-governance/core/protocol/external-command-contract.md",
            "skills/software-project-governance/core/protocol/headless-runner-sample.md",
            "skills/software-project-governance/core/protocol/plugin-contract.md",
            "project/references/agent-team-architecture.md",
            "project/workflows/software-project-governance/research/default-product-shape.md",
        ]
        legacy_patterns = [
            "skills/software-project-governance/" + "stages",
            "stages/" + "*/" + "sub-" + "workflow.md",
            "stages/" + "<current-stage>/" + "sub-" + "workflow.md",
            "sub-" + "workflow.md",
            "STAGES" + "_DIR",
        ]
        bad_templates = [
            "skills/stage-" + "<stage>" + "/SKILL.md",
            "skills/stage-" + "<current-stage>" + "/SKILL.md",
            "skills/stage-" + "{stage}" + "/SKILL.md",
            "skills/" + "stage-" + "infrastructure" + "/SKILL.md",
            "skills/" + "stage-" + "ci-cd" + "/SKILL.md",
        ]

        failures = []
        for rel_path in files_to_scan:
            path = vw.ROOT / rel_path
            content = path.read_text(encoding="utf-8")
            for pattern in legacy_patterns + bad_templates:
                if pattern in content:
                    failures.append(f"{rel_path}: {pattern}")
        self.assertEqual(failures, [])


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

    def test_evidence_completeness_uses_fixture_archive_when_index_exists(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sp, ep, rp = self._setup(root, evidence=_evd_row("EVD-001", "TASK-001"))
            archive = root / ".governance" / "archive"
            tasks_dir = archive / "tasks"
            evidence_dir = archive / "evidence"
            tasks_dir.mkdir(parents=True)
            evidence_dir.mkdir(parents=True)
            (archive / "index.md").write_text(
                "| Task ID | 状态 | 版本 | 归档文件 |\n"
                "|---------|------|------|---------|\n"
                "| TASK-002 | 已完成 | 0.1.0 | archive/tasks/v0.1.0.md |\n"
                "\n"
                "| Evidence ID | Task ID | 归档文件 |\n"
                "|-------------|--------|---------|\n"
                "| EVD-002 | TASK-002 | archive/evidence/v0.1.0.md |\n",
                encoding="utf-8",
            )
            (tasks_dir / "v0.1.0.md").write_text(
                "\n".join([_TASK_COLS, _TASK_SEP, _task("TASK-002", "已完成")]),
                encoding="utf-8",
            )
            (evidence_dir / "v0.1.0.md").write_text(
                _evd_row("EVD-002", "TASK-002"),
                encoding="utf-8",
            )

            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_evidence_completeness()
                self.assertEqual(r["completed_count"], 2)
                self.assertEqual(len(r["missing_evidence"]), 0)

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


class GovernanceSignalNoiseTests(unittest.TestCase):
    """FIX-066: governance checks keep signal while suppressing historical noise."""

    def _minimal_m5_root(self, root, claude_text):
        (root / "CLAUDE.md").write_text(claude_text, encoding="utf-8")
        (root / "commands").mkdir(parents=True)
        (root / "commands" / "governance-init.md").write_text(
            "AskUserQuestion\nM5.1\n我即将输出的文本是否包含向用户提问的问句\n",
            encoding="utf-8",
        )
        ib_dir = root / "skills/software-project-governance/references"
        ib_dir.mkdir(parents=True)
        (ib_dir / "interaction-boundary.md").write_text(
            "Use AskUserQuestion at interaction boundaries.\n",
            encoding="utf-8",
        )

    def test_m5_ignores_checklist_questions_but_catches_inline_ask_instruction(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._minimal_m5_root(
                root,
                "1. 我是否已经读了 plan-tracker？否 -> 去读\n"
                "合法检查清单：这个方案是否覆盖测试？\n"
                "违规：MUST 直接问用户“要不要继续？”\n",
            )
            with patch.object(vw, "ROOT", root):
                result = vw.check_m5_compliance()

        blocking = [i for i in result["issues"] if i["severity"] == "BLOCKING"]
        self.assertEqual(len(blocking), 1)
        self.assertEqual(blocking[0]["type"], "m5_inline_question_cn")
        self.assertIn("直接问用户", blocking[0]["text"])

    def test_m5_scans_root_agents_entry_surface(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._minimal_m5_root(root, "safe\n")
            (root / "AGENTS.md").write_text(
                "违规：MUST 直接问用户“要不要继续？”\n",
                encoding="utf-8",
            )

            with patch.object(vw, "ROOT", root):
                result = vw.check_m5_compliance()

        blocking = [i for i in result["issues"] if i["severity"] == "BLOCKING"]
        self.assertEqual(len(blocking), 1)
        self.assertEqual(blocking[0]["file"], "AGENTS.md")

    def test_manifest_uses_tracked_scope_and_ignores_local_runtime_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = {
                "root_entries": {"files": ["README.md"], "directories": []},
                "product": {"entries": [], "glob_patterns": []},
                "repo_only": {"entries": [], "glob_patterns": []},
            }
            mp = root / "manifest.json"
            mp.write_text(json.dumps(manifest), encoding="utf-8")
            (root / "README.md").write_text("ok", encoding="utf-8")
            (root / "AGENTS.md").write_text("local user note", encoding="utf-8")
            cache = root / ".pytest_cache"
            cache.mkdir()
            (cache / "README.md").write_text("cache", encoding="utf-8")

            with patch.object(vw, "ROOT", root), \
                 patch.object(vw, "_git_files", return_value={"README.md"}):
                result = vw.check_manifest_consistency(mp)

        self.assertTrue(result["pass"])
        self.assertEqual(result["untracked"], [])

    def test_manifest_still_catches_tracked_file_missing_from_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = {
                "root_entries": {"files": ["README.md"], "directories": []},
                "product": {"entries": [], "glob_patterns": []},
                "repo_only": {"entries": [], "glob_patterns": []},
            }
            mp = root / "manifest.json"
            mp.write_text(json.dumps(manifest), encoding="utf-8")
            (root / "README.md").write_text("ok", encoding="utf-8")
            (root / "tracked-extra.md").write_text("real drift", encoding="utf-8")

            with patch.object(vw, "ROOT", root), \
                 patch.object(vw, "_git_files", return_value={"README.md", "tracked-extra.md"}):
                result = vw.check_manifest_consistency(mp)

        self.assertFalse(result["pass"])
        self.assertEqual(result["untracked"], ["tracked-extra.md"])

    def test_archive_completed_missing_evidence_is_info_but_hot_missing_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / ".governance"
            gov.mkdir(parents=True)
            sp = gov / "plan-tracker.md"
            ep = gov / "evidence-log.md"
            sp.write_text(
                "\n".join([_TASK_COLS, _TASK_SEP, _task("HOT-001", "已完成")]),
                encoding="utf-8",
            )
            ep.write_text("", encoding="utf-8")
            archive = gov / "archive"
            tasks_dir = archive / "tasks"
            evidence_dir = archive / "evidence"
            tasks_dir.mkdir(parents=True)
            evidence_dir.mkdir()
            (archive / "index.md").write_text("index", encoding="utf-8")
            (tasks_dir / "v0.1.0.md").write_text(
                "\n".join([_TASK_COLS, _TASK_SEP, _task("OLD-001", "已完成")]),
                encoding="utf-8",
            )
            (evidence_dir / "v0.1.0.md").write_text("", encoding="utf-8")

            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                missing = vw.check_evidence_completeness()
                gate = vw.check_gate_consistency()

        self.assertEqual(missing["missing_evidence"], ["HOT-001"])
        self.assertEqual(missing["historical_missing_evidence"], ["OLD-001"])
        self.assertTrue(any(i["type"] == "completed_tasks_missing_evidence" for i in gate))
        self.assertTrue(any(i["type"] == "historical_completed_tasks_missing_evidence" for i in gate))

    def test_cross_reference_ignores_bare_filenames_but_catches_real_broken_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_dir = root / "skills/software-project-governance"
            source_dir.mkdir(parents=True)
            (source_dir / "SKILL.md").write_text(
                "Bare SKILL.md is prose.\nBroken inline path: `missing/path.md`\n",
                encoding="utf-8",
            )
            with patch.object(vw, "ROOT", root):
                result = vw.check_cross_references()

        self.assertEqual(len(result["dangling"]), 1)
        self.assertEqual(result["dangling"][0]["target"], "missing/path.md")

    def test_cross_reference_resolves_skill_root_paths_from_commands_and_agents(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "commands").mkdir()
            (root / "agents").mkdir()
            skill = root / "skills/software-project-governance"
            (skill / "core").mkdir(parents=True)
            (skill / "infra").mkdir()
            (skill / "references").mkdir()
            (skill / "core/onboarding.md").write_text("ok\n", encoding="utf-8")
            (skill / "infra/verify_workflow.py").write_text("# ok\n", encoding="utf-8")
            (skill / "references/guide.md").write_text("ok\n", encoding="utf-8")
            (root / "commands/governance.md").write_text("See `core/onboarding.md`.\n", encoding="utf-8")
            (root / "agents/governance-developer.md").write_text(
                "Owns `infra/verify_workflow.py` and `references/guide.md`.\n",
                encoding="utf-8",
            )

            with patch.object(vw, "ROOT", root):
                result = vw.check_cross_references()

        self.assertEqual(result["dangling"], [])

    def test_cross_reference_ignores_generated_output_paths_but_not_other_docs_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            agents = root / "agents"
            agents.mkdir()
            (agents / "analyst.md").write_text(
                "## 输出格式\n\n"
                "执行完毕后必须生成：\n"
                "- `docs/requirements/user-profiles.md`（用户画像）\n"
                "\n"
                "## 其他\n"
                "真实引用：`docs/requirements/missing-source.md`\n",
                encoding="utf-8",
            )

            with patch.object(vw, "ROOT", root):
                result = vw.check_cross_references()

        self.assertEqual(len(result["dangling"]), 1)
        self.assertEqual(result["dangling"][0]["target"], "docs/requirements/missing-source.md")

    def test_cross_reference_ignores_external_and_runtime_generated_refs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ref_dir = root / "skills/software-project-governance/references"
            ref_dir.mkdir(parents=True)
            (ref_dir / "methodology-routing.md").write_text(
                "味道指令由 PUA skill 的 `references/flavors.md` 定义。\n",
                encoding="utf-8",
            )
            commands = root / "commands"
            commands.mkdir()
            (commands / "governance-init.md").write_text(
                "- **不**创建 `archive/index.md`——索引在首次归档时由 archive.py 自动生成\n",
                encoding="utf-8",
            )

            with patch.object(vw, "ROOT", root):
                result = vw.check_cross_references()

        self.assertEqual(result["dangling"], [])

    def test_cross_reference_excludes_validator_coverage_edges_from_cycle_graph(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            skill = root / "skills/software-project-governance"
            infra = skill / "infra"
            core = skill / "core/protocol"
            infra.mkdir(parents=True)
            core.mkdir(parents=True)
            (infra / "verify_workflow.py").write_text(
                'REQUIRED_FILES = {"contract": ROOT / "skills/software-project-governance/core/protocol/plugin-contract.md"}\n',
                encoding="utf-8",
            )
            (core / "plugin-contract.md").write_text(
                "Validator: `skills/software-project-governance/infra/verify_workflow.py`\n",
                encoding="utf-8",
            )

            with patch.object(vw, "ROOT", root):
                result = vw.check_cross_references()

        self.assertEqual(result["dangling"], [])
        self.assertEqual(result["cycles"], [])

    def test_cross_reference_excludes_entry_index_edges_from_cycle_graph(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            skill = root / "skills/software-project-governance"
            ref = skill / "references"
            ref.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "| `references/template.md` | Agent dispatch template |\n",
                encoding="utf-8",
            )
            (ref / "template.md").write_text(
                "Coordinator identity is defined in `skills/software-project-governance/SKILL.md`.\n",
                encoding="utf-8",
            )

            with patch.object(vw, "ROOT", root):
                result = vw.check_cross_references()

        self.assertEqual(result["dangling"], [])
        self.assertEqual(result["cycles"], [])

    def test_cross_reference_still_detects_real_doc_cycles(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            docs = root / "skills/software-project-governance/references"
            docs.mkdir(parents=True)
            (docs / "a.md").write_text("See [b](b.md).\n", encoding="utf-8")
            (docs / "b.md").write_text("See [a](a.md).\n", encoding="utf-8")

            with patch.object(vw, "ROOT", root):
                result = vw.check_cross_references()

        self.assertEqual(result["dangling"], [])
        self.assertEqual(len(result["cycles"]), 1)

    def test_hot_evidence_extra_columns_remain_actionable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / ".governance"
            gov.mkdir(parents=True)
            (gov / "plan-tracker.md").write_text("ok\n", encoding="utf-8")
            (gov / "decision-log.md").write_text("", encoding="utf-8")
            (gov / "evidence-log.md").write_text(
                "| EVD-001 | FIX-001 | type | date | actor | action | file | result | notes | status |\n"
                "| EVD-002 | FIX-002 | type | date | actor | action | file | result | notes | status | extra |\n",
                encoding="utf-8",
            )
            manifest = root / "skills/software-project-governance/core/manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                json.dumps({"product": {}, "repo_only": {}, "exclude": {}}),
                encoding="utf-8",
            )

            with patch.object(vw, "ROOT", root):
                issues = vw.check_structural_validity()

        evidence_issues = [i for i in issues if i.get("file") == ".governance/evidence-log.md"]
        self.assertEqual(len(evidence_issues), 1)
        self.assertEqual(evidence_issues[0]["type"], "evidence_col_mismatch")
        self.assertEqual(evidence_issues[0]["severity"], "WARN")

    def test_untracked_root_agents_is_actionable_entry_surface(self):
        completed = subprocess.CompletedProcess(
            args=["git"],
            returncode=0,
            stdout="AGENTS.md\nscratch.txt\n",
            stderr="",
        )
        with patch("subprocess.run", return_value=completed):
            result = vw.check_untracked_files()

        self.assertFalse(result["pass"])
        self.assertEqual(result["actionable_entry_files"], ["AGENTS.md"])
        self.assertEqual(result["suggest_manual"], ["scratch.txt"])

    def test_ignored_root_agents_entry_surface_is_not_reported(self):
        completed = subprocess.CompletedProcess(
            args=["git"],
            returncode=0,
            stdout="scratch.txt\n",
            stderr="",
        )
        with patch("subprocess.run", return_value=completed):
            result = vw.check_untracked_files()

        self.assertFalse(result["pass"])
        self.assertEqual(result["actionable_entry_files"], [])
        self.assertEqual(result["untracked_files"], ["scratch.txt"])
        self.assertEqual(result["suggest_manual"], ["scratch.txt"])

    def test_lock_severity_blocks_invalid_lock_and_parses_task_id_in_any_cell(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / ".governance"
            gov.mkdir(parents=True)
            (gov / "plan-tracker.md").write_text(
                "| 优先级 | ID | 状态 |\n"
                "| --- | --- | --- |\n"
                "| **P1** | FIX-066 | 进行中 |\n",
                encoding="utf-8",
            )
            (gov / "agent-locks.json").write_text(
                json.dumps({
                    "active_tasks": {},
                    "file_locks": {
                        "skills/software-project-governance/infra/verify_workflow.py": {
                            "locked_by": "FIX-066",
                            "locked_at": "2099-01-01T00:00:00Z",
                            "ttl_seconds": 600,
                            "ttl_reason": "test",
                        }
                    },
                }),
                encoding="utf-8",
            )

            with patch.object(vw, "ROOT", root):
                result = vw.check_agent_lock_consistency()

        self.assertFalse(any(i["type"] == "task_not_in_plan" for i in result["issues"]))
        orphan = next(i for i in result["issues"] if i["type"] == "orphan_lock")
        self.assertTrue(vw.lock_issue_is_blocking(orphan))
        self.assertEqual(orphan["severity"], "BLOCKING")

    def test_check_snippets_reports_current_missing_source_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            missing = root / "current.md"
            with patch.object(vw, "ROOT", root), \
                 patch.object(vw, "REQUIRED_SNIPPETS", {missing: ["current fact"]}):
                with redirect_stdout(io.StringIO()):
                    failures = vw.check_snippets()

        self.assertEqual(len(failures), 1)
        self.assertIn("missing snippet source file", failures[0])


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


class ArchiveTriggerGapTests(unittest.TestCase):
    """FIX-063: Check 26 exposes continuous archive trigger gaps."""

    def test_archive_integrity_reports_pending_archive_trigger_gap(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / ".governance"
            gov.mkdir(parents=True)
            (gov / "plan-tracker.md").write_text(
                "# plan\n\n| 任务ID | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | 状态 |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| FIX-001 | x | x | x | x | x | x | x | x | 已完成 |\n",
                encoding="utf-8",
            )

            class FakeArchive:
                @staticmethod
                def analyze_auto_archive_candidates():
                    return {
                        "should_archive": True,
                        "tasks_archived": 1,
                        "triggers": ["release_forced"],
                        "versions_range": ("0.10.0", "0.10.0"),
                    }

            with patch.object(vw, "ROOT", root), \
                 patch.object(vw, "SAMPLE_PATH", gov / "plan-tracker.md"), \
                 patch.object(vw, "_load_archive_module", return_value=FakeArchive):
                result = vw.check_archive_integrity()

            self.assertFalse(result["pass"])
            self.assertEqual(result["pending_archive_tasks"], 1)
            self.assertEqual(result["archive_triggers"], ["release_forced"])
            self.assertTrue(any("Archive trigger gap" in issue for issue in result["issues"]))

    def test_check_archive_integrity_no_archive_dir_is_read_only(self):
        """Check 26 must not create .governance/archive during trigger analysis."""
        import archive

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / ".governance"
            gov.mkdir(parents=True)
            (gov / "plan-tracker.md").write_text(
                "# plan\n\n"
                "## 版本规划\n\n"
                "### 版本路线图\n\n"
                "| 版本 | 状态 | 日期 |\n"
                "| --- | --- | --- |\n"
                "| 0.10.0 | 已发布 | 2026-01-01 |\n"
                "| 0.11.0 | 已发布 | 2026-02-01 |\n\n"
                "### v0.10.0 — Old\n"
                "| 任务ID | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | 状态 |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| FIX-001 | x | x | x | x | x | x | x | x | 已完成 |\n\n"
                "### v0.11.0 — Latest\n"
                "| 任务ID | c2 | c3 | c4 | c5 | c6 | c7 | c8 | c9 | 状态 |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| FIX-002 | x | x | x | x | x | x | x | x | 进行中 |\n",
                encoding="utf-8",
            )
            with patch.object(archive, "ROOT", root), \
                 patch.object(vw, "ROOT", root), \
                 patch.object(vw, "SAMPLE_PATH", gov / "plan-tracker.md"), \
                 patch.object(vw, "_load_archive_module", return_value=archive):
                result = vw.check_archive_integrity()

            self.assertIn("pending_archive_tasks", result)
            self.assertFalse((gov / "archive").exists())


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
