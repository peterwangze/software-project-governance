"""Unit tests for verify_workflow.py — SYSGAP-016.

Column format constraints (mandatory—must match parser expectations):
  - parse_completed_task_ids: >= 11 parts, status at parts[10]
  - parse_task_stats: status column resolved from table header, with historical fallbacks
  - parse_evidence_task_ids:  | EVD-xxx | <TASK-ID-column> | ..., parts[2]
  - parse_open_risks:         >= 10 parts, status at parts[9]
  - parse_gate_status:        >= 5 parts (split[1:-1]), [0]=gate [2]=status

Run:
    python -m unittest discover -s skills/software-project-governance/infra/tests -v
"""

import json
import io
import os
import argparse
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw
import cleanup as cleanup_mod


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


class CleanCheckoutBoundaryTests(unittest.TestCase):
    """CI clean checkout must not require local runtime governance state."""

    def test_verify_workflow_compiles_under_ci_interpreter(self):
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(Path(vw.__file__))],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_canonical_manifest_does_not_require_root_claude_or_governance_runtime(self):
        manifest_path = vw.ROOT / "skills/software-project-governance/core/manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertNotIn("CLAUDE.md", manifest["root_entries"]["files"])
        self.assertFalse(
            any(entry.get("path") == ".governance/" for entry in manifest["repo_only"]["entries"])
        )
        self.assertNotIn(".governance/*.md", manifest["repo_only"]["glob_patterns"])

    def test_canonical_manifest_declares_pack_registry_product_artifact(self):
        manifest_path = vw.ROOT / "skills/software-project-governance/core/manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifact_entries = manifest["canonical_product_artifacts"]["entries"]

        registry_artifact = [
            entry for entry in artifact_entries
            if entry.get("id") == "governance-pack-registry"
        ]
        self.assertEqual(len(registry_artifact), 1)
        self.assertEqual(
            registry_artifact[0]["path"],
            "skills/software-project-governance/core/governance-packs.json",
        )
        self.assertTrue(registry_artifact[0]["required"])
        self.assertIn(
            "check-governance-packs",
            " ".join(registry_artifact[0]["validation_commands"]),
        )

    def test_canonical_manifest_declares_lifecycle_registry_product_artifact(self):
        manifest_path = vw.ROOT / "skills/software-project-governance/core/manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifact_entries = manifest["canonical_product_artifacts"]["entries"]

        registry_artifact = [
            entry for entry in artifact_entries
            if entry.get("id") == "lifecycle-registry"
        ]
        self.assertEqual(len(registry_artifact), 1)
        self.assertEqual(
            registry_artifact[0]["path"],
            "skills/software-project-governance/core/lifecycle-registry.json",
        )
        self.assertTrue(registry_artifact[0]["required"])
        commands = " ".join(registry_artifact[0]["validation_commands"])
        self.assertIn("check-lifecycle-registry", commands)
        self.assertIn("check-manifest-consistency", commands)

    def test_canonical_manifest_declares_cleanup_scope(self):
        manifest_path = vw.ROOT / "skills/software-project-governance/core/manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(set(manifest["cleanup_scope"]["directories"]), vw.PLUGIN_SCOPE_DIRS)

    def test_default_snippets_do_not_require_local_governance_files(self):
        governance_snippet_paths = [
            str(path.relative_to(vw.ROOT)).replace("\\", "/")
            for path in vw.REQUIRED_SNIPPETS
            if str(path.relative_to(vw.ROOT)).replace("\\", "/").startswith(".governance/")
        ]
        self.assertEqual(governance_snippet_paths, [])

    def test_claude_codex_adapter_snippets_require_tier1_loading_guides(self):
        expected = {
            "adapters/claude/README.md": [
                "Tier 1",
                "## Load",
                "## Verify",
                "## Boundary",
                "skills/software-project-governance/SKILL.md",
                "python adapters/claude/launch.py",
                "check-agent-adapters",
                "check-agent-adapters --runtime",
            ],
            "adapters/codex/README.md": [
                "Tier 1",
                "## Load",
                "## Verify",
                "## Boundary",
                "skills/software-project-governance/SKILL.md",
                ".codex-plugin/plugin.json",
                ".agents/plugins/marketplace.json",
                "python adapters/codex/launch.py",
                "check-agent-adapters",
                "agent-runtime-e2e --agent codex",
            ],
        }

        for rel_path, tokens in expected.items():
            path = vw.ROOT / rel_path
            for snippet_block in (vw.PROJECTION_SNIPPETS, vw.REQUIRED_SNIPPETS):
                snippets = snippet_block[path]
                self.assertNotIn("已废弃（Deprecated）", snippets)
                self.assertNotIn("历史入口约定（已废弃，仅供参考）", snippets)
                for token in tokens:
                    self.assertIn(token, snippets)

    def test_version_consistency_fails_when_required_snippets_block_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "skills/software-project-governance/infra").mkdir(parents=True)
            (root / "skills/software-project-governance/core").mkdir(parents=True)
            (root / ".claude-plugin").mkdir()
            (root / ".codex-plugin").mkdir()
            (root / "project").mkdir()

            (root / "skills/software-project-governance/SKILL.md").write_text(
                "---\nversion: 9.9.9\n---\n",
                encoding="utf-8",
            )
            (root / "skills/software-project-governance/core/manifest.json").write_text(
                json.dumps({"version": "9.9.9"}),
                encoding="utf-8",
            )
            (root / ".claude-plugin/plugin.json").write_text(
                json.dumps({"version": "9.9.9"}),
                encoding="utf-8",
            )
            (root / ".claude-plugin/marketplace.json").write_text(
                json.dumps({"plugins": [{"version": "9.9.9"}]}),
                encoding="utf-8",
            )
            (root / ".codex-plugin/plugin.json").write_text(
                json.dumps({"version": "9.9.9"}),
                encoding="utf-8",
            )
            (root / "project/CHANGELOG.md").write_text(
                "## [9.9.9]\n",
                encoding="utf-8",
            )
            (root / "skills/software-project-governance/infra/verify_workflow.py").write_text(
                "REQUIRED_SNIPPETS = {'x': ['9.8.7']}\n# sentinel missing\n",
                encoding="utf-8",
            )

            with patch.object(vw, "ROOT", root):
                issues = vw.check_version_consistency()

        self.assertTrue(
            any("REQUIRED_SNIPPETS block not found" in issue for issue in issues),
            issues,
        )

    def test_default_verify_does_not_run_release_fact_source_health_check(self):
        with patch.object(vw, "check_files", return_value=[]), \
             patch.object(vw, "check_snippets", return_value=[]), \
             patch.object(vw, "check_architecture_fact_source", return_value=[]), \
             patch.object(
                 vw,
                 "check_release_readiness_fact_source",
                 side_effect=AssertionError("default verify must stay product-only"),
             ), \
             patch.object(vw, "check_agent_adapter_contract", return_value=[]), \
             patch.object(vw, "check_version_consistency", return_value=[]):
            with redirect_stdout(io.StringIO()):
                vw.cmd_verify(argparse.Namespace())

    def test_missing_local_risk_log_is_empty_for_governance_health(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.object(vw, "ROOT", root), \
                 patch.object(vw, "RISK_PATH", root / ".governance/risk-log.md"):
                self.assertEqual(vw.parse_open_risks(), [])
                self.assertEqual(vw.check_risk_staleness()["total_open"], 0)
                self.assertEqual(vw.check_risk_escalation()["total_open"], 0)

    def test_cross_references_ignore_runtime_governance_paths_when_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            commands = root / "commands"
            commands.mkdir(parents=True)
            (commands / "governance.md").write_text(
                "Read `.governance/plan-tracker.md` and `.governance/evidence-log.md`.\n",
                encoding="utf-8",
            )

            with patch.object(vw, "ROOT", root):
                result = vw.check_cross_references()

        self.assertEqual(result["dangling"], [])

    def test_cross_references_ignore_materialized_e2e_projection_paths_when_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            infra = root / "skills/software-project-governance/infra"
            infra.mkdir(parents=True)
            (infra / "verify_workflow.py").write_text(
                'OPTIONAL = ROOT / "project/e2e-test-project/commands/governance-review.md"\n',
                encoding="utf-8",
            )

            with patch.object(vw, "ROOT", root):
                result = vw.check_cross_references()

        self.assertEqual(result["dangling"], [])


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
    """FIX-065/FIX-070: architecture and Agent Team facts must stay synchronized."""

    def _agent_protocol_content(self):
        role_sections = []
        for role in vw.ACTIVE_AGENT_ROLES:
            output = "- Proposed evidence-log entry\n"
            if role == "Governance Developer":
                output += "- Proposed decision-log / risk-log entry when rule or risk posture changes\n"
            elif "Reviewer" in role:
                output = "- Proposed review evidence entry\n"
            role_sections.append(
                f"### {role}\n\n"
                "**Input**:\n```\nTask: {{task_id}}\n```\n\n"
                "**Output**:\n```\n"
                f"{output}"
                "```\n"
            )
        return (
            "# Agent 通信协议\n\n"
            "## 原则\n\n"
            "Sub-agent 不直接写 `.governance/`；由 Coordinator 写回 proposed entry。\n\n"
            "## 角色 Agent I/O 契约\n\n"
            + "\n".join(role_sections)
        )

    def _governance_developer_prompt_content(self):
        return (
            "# Governance Developer\n\n"
            "不得直接写 `.governance/` 治理记录；必须返回 proposed evidence-log entry；"
            "规则或风险姿态变化时返回 proposed decision-log / risk-log entry；"
            "Coordinator 负责最终写回。\n\n"
            "## 输出格式\n\n"
            "- Proposed evidence-log entry\n"
            "- Proposed decision-log / risk-log entry\n"
        )

    def _write_fact_files(
        self,
        root,
        skill_extra="",
        skill_index_operations_agents="Coordinator, DevOps, Maintenance",
        skill_index_extra="",
        agent_protocol_content=None,
        governance_developer_prompt_content=None,
        architecture_extra="",
        governance_route_count=19,
    ):
        skill = root / "SKILL.md"
        skill.write_text(
            "# 软件项目治理工作流入口\n\n"
            "Coordinator 融入入口层。\n"
            "14 个活跃文件化角色 Agent；15 个活跃角色含 Coordinator。\n"
            "Coordinator 接管用户交互。\n"
            "Producer-Reviewer 分离。\n\n"
            "## Agent 分发路由\n\n"
            "| 任务类型 | 执行 Agent | 后置审查 Agent(s) | 触发条件 | 执行要求与证据 |\n"
            "| --- | --- | --- | --- | --- |\n"
            + "\n".join(
                f"| Route {i:02d} | Agent | Code Reviewer | 自动 | Method |"
                for i in range(1, 20)
            )
            + f"\n{skill_extra}\n\n## Sub-agent 调度\n",
            encoding="utf-8",
        )

        skill_index = root / "skill-index.md"
        skill_index.write_text(
            "# SKILL 分类索引\n\n"
            "| SKILL | 路径 | 用途 | 调用 Agent |\n"
            "| --- | --- | --- | --- |\n"
            "| stage-infra | `skills/stage-infra/SKILL.md` | 基础设施 | Coordinator, Architect, Developer, Governance Developer, DevOps |\n"
            f"| stage-operations | `skills/stage-operations/SKILL.md` | 运营与反馈 | {skill_index_operations_agents} |\n"
            "| stage-maintenance | `skills/stage-maintenance/SKILL.md` | 维护与演进 | Coordinator, Governance Developer, Maintenance |\n"
            "| code-review | `skills/code-review/SKILL.md` | 代码审查 | Developer(自检), Governance Developer(自检), Code Reviewer(正式) |\n\n"
            "## Agent↔SKILL 绑定总表\n\n"
            "| 职能组 | Agent | 可调用 SKILL |\n"
            "| --- | --- | --- |\n"
            "| 开发组 | **Governance Developer** | stage-maintenance, stage-infra, code-review |\n"
            f"{skill_index_extra}\n",
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

        agent_protocol = root / "agent-communication-protocol.md"
        agent_protocol.write_text(
            agent_protocol_content if agent_protocol_content is not None else self._agent_protocol_content(),
            encoding="utf-8",
        )

        governance_developer_prompt = root / "governance-developer.md"
        governance_developer_prompt.write_text(
            (
                governance_developer_prompt_content
                if governance_developer_prompt_content is not None
                else self._governance_developer_prompt_content()
            ),
            encoding="utf-8",
        )
        return skill, skill_index, architecture, governance, agent_protocol, governance_developer_prompt

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
            self.assertTrue(any("route table count 16 does not match SKILL.md actual 19" in issue for issue in issues))

    def test_architecture_fact_source_requires_key_phrases(self):
        with tempfile.TemporaryDirectory() as td:
            paths = self._write_fact_files(
                Path(td),
                skill_extra="\n",
            )
            skill, skill_index, architecture, governance, agent_protocol, governance_developer_prompt = paths
            skill.write_text(skill.read_text(encoding="utf-8").replace("Producer-Reviewer 分离。\n", ""), encoding="utf-8")
            issues = vw.check_architecture_fact_source(
                skill, skill_index, architecture, governance, agent_protocol, governance_developer_prompt
            )
            self.assertTrue(any("Producer-Reviewer 分离" in issue for issue in issues))

    def test_architecture_fact_source_requires_governance_developer_skill_binding(self):
        with tempfile.TemporaryDirectory() as td:
            paths = self._write_fact_files(Path(td))
            skill, skill_index, architecture, governance, agent_protocol, governance_developer_prompt = paths
            skill_index.write_text(
                skill_index.read_text(encoding="utf-8")
                .replace(", Governance Developer", "")
                .replace("Governance Developer(自检), ", "")
                .replace("| 开发组 | **Governance Developer** | stage-maintenance, stage-infra, code-review |\n", ""),
                encoding="utf-8",
            )
            issues = vw.check_architecture_fact_source(
                skill, skill_index, architecture, governance, agent_protocol, governance_developer_prompt
            )
            self.assertTrue(any("missing Governance Developer skill binding row" in issue for issue in issues))
            self.assertTrue(any("stage-infra must bind Governance Developer" in issue for issue in issues))
            self.assertTrue(any("stage-maintenance must bind Governance Developer" in issue for issue in issues))
            self.assertTrue(any("code-review must bind Governance Developer" in issue for issue in issues))

    def test_architecture_fact_source_requires_governance_developer_protocol_entries(self):
        with tempfile.TemporaryDirectory() as td:
            protocol = self._agent_protocol_content().replace(
                "- Proposed decision-log / risk-log entry when rule or risk posture changes\n",
                "",
            )
            paths = self._write_fact_files(Path(td), agent_protocol_content=protocol)
            issues = vw.check_architecture_fact_source(*paths)
            self.assertTrue(any("Governance Developer contract missing Proposed decision-log / risk-log entry" in issue for issue in issues))

    def test_architecture_fact_source_requires_governance_developer_protocol_evidence_entry(self):
        with tempfile.TemporaryDirectory() as td:
            protocol = self._agent_protocol_content().replace(
                "- Proposed evidence-log entry\n",
                "",
            )
            paths = self._write_fact_files(Path(td), agent_protocol_content=protocol)
            issues = vw.check_architecture_fact_source(*paths)
            self.assertTrue(any("Governance Developer contract missing Proposed evidence-log entry" in issue for issue in issues))

    def test_architecture_fact_source_requires_all_active_role_protocol_sections(self):
        with tempfile.TemporaryDirectory() as td:
            protocol = self._agent_protocol_content().replace("### Release Reviewer\n", "### Reviewer\n")
            paths = self._write_fact_files(Path(td), agent_protocol_content=protocol)
            issues = vw.check_architecture_fact_source(*paths)
            self.assertTrue(any("missing active role communication contract: Release Reviewer" in issue for issue in issues))
            self.assertTrue(any("generic Reviewer communication contract is forbidden" in issue for issue in issues))

    def test_architecture_fact_source_rejects_generic_reviewer_skill_binding(self):
        with tempfile.TemporaryDirectory() as td:
            paths = self._write_fact_files(
                Path(td),
                skill_index_extra="| 评审组 | **Reviewer** | requirement-review, design-review, code-review |\n",
            )
            issues = vw.check_architecture_fact_source(*paths)
            self.assertTrue(any("generic Reviewer role is forbidden" in issue for issue in issues))

    def test_architecture_fact_source_requires_governance_developer_prompt_no_direct_write_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            prompt = self._governance_developer_prompt_content().replace(
                "不得直接写 `.governance/` 治理记录；", ""
            )
            paths = self._write_fact_files(Path(td), governance_developer_prompt_content=prompt)
            issues = vw.check_architecture_fact_source(*paths)
            self.assertTrue(any("不得直接写 `.governance/` 治理记录" in issue for issue in issues))

    def test_architecture_fact_source_requires_governance_developer_prompt_evidence_entry(self):
        with tempfile.TemporaryDirectory() as td:
            prompt = self._governance_developer_prompt_content().replace(
                "- Proposed evidence-log entry\n",
                "",
            )
            paths = self._write_fact_files(Path(td), governance_developer_prompt_content=prompt)
            issues = vw.check_architecture_fact_source(*paths)
            self.assertTrue(any("Proposed evidence-log entry" in issue for issue in issues))

    def test_architecture_fact_source_requires_governance_developer_prompt_decision_risk_entry(self):
        with tempfile.TemporaryDirectory() as td:
            prompt = self._governance_developer_prompt_content().replace(
                "- Proposed decision-log / risk-log entry\n",
                "",
            )
            paths = self._write_fact_files(Path(td), governance_developer_prompt_content=prompt)
            issues = vw.check_architecture_fact_source(*paths)
            self.assertTrue(any("Proposed decision-log / risk-log entry" in issue for issue in issues))

    def test_architecture_fact_source_requires_governance_developer_prompt_coordinator_writeback_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            prompt = self._governance_developer_prompt_content().replace(
                "Coordinator 负责最终写回。",
                "",
            )
            paths = self._write_fact_files(Path(td), governance_developer_prompt_content=prompt)
            issues = vw.check_architecture_fact_source(*paths)
            self.assertTrue(any("Coordinator 负责最终写回" in issue for issue in issues))


class ReleaseReadinessFactSourceTests(unittest.TestCase):
    """FIX-069: plan, requirement matrix, 1.0.0 blockers, and architecture facts stay aligned."""

    def _plan_content(self, release_row=None, dependency_chain_extra=None, req_overrides=None, active_rows=""):
        req_overrides = req_overrides or {}
        if release_row is None:
            release_row = (
                "| **1.0.0** | **预留** | **—** | **首次正式发布标签——不承载修改，仅当 "
                "0.35.0 FIX-069~074 全部闭环、RISK-030 关闭、外部验证通过后打 tag** | **—** | "
                "**纯版本标签——production-ready 声明；不得绕过主流 agent 真实环境 E2E 和防跑偏看护收口** |"
            )
        elif release_row is False:
            release_row = ""
        dependency_chain_extra = dependency_chain_extra or (
            "\n    │\n    ▼\n"
            "0.35.0 FIX-069~074 全部闭环 + RISK-030 关闭\n"
            "（含主流 agent 真实环境 E2E、防跑偏看护、工具化收口；全部闭环前不得推进 1.0.0）"
        )
        req_rows = {
            "REQ-059": "| REQ-059 | 架构事实源状态必须一致 | AUDIT-100 | P0 | FIX-069 | 🔄 进行中 | 0.35.0 |",
            "REQ-060": "| REQ-060 | Agent Team 边界覆盖 | AUDIT-100 | P0 | FIX-070 | ✅ 已交付 | 0.35.0 |",
            "REQ-061": "| REQ-061 | 主流 agent 入口状态真实 | AUDIT-100 | P0 | FIX-071 | 📋 待实施 | 0.35.0 |",
            "REQ-062": "| REQ-062 | Skill 工具化归档 | AUDIT-100 | P1 | FIX-072 | 📋 待实施 | 0.35.0 |",
            "REQ-063": "| REQ-063 | 目标偏离看护不空跑 | AUDIT-100 | P1 | FIX-073 | 📋 待实施 | 0.35.0 |",
            "REQ-064": "| REQ-064 | E2E 真实性分层 | AUDIT-100 | P1 | FIX-074 | 📋 待实施 | 0.35.0 |",
        }
        req_rows.update(req_overrides)
        return (
            "# 当前项目样例\n\n"
            f"{active_rows}\n\n"
            "### 1.0.0 依赖链\n\n"
            "```\n"
            "0.11.0 ✅\n"
            "    │\n"
            "    ▼\n"
            "AUDIT-072: 外部验证≥2(P0)"
            f"{dependency_chain_extra}\n"
            "    │\n"
            "    ▼\n"
            "1.0.0 正式发布\n"
            "```\n\n"
            "### 版本路线图\n\n"
            "| 版本 | 状态 | 预计日期 | 核心范围 | 包含 Tier/Layer | 关键交付物 |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            f"{release_row}\n\n"
            "## 需求跟踪矩阵\n\n"
            "| 需求ID | 需求描述 | 来源 | 优先级 | 关联任务 | 当前状态 | 验证方式 |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            + "\n".join(req_rows[req_id] for req_id in sorted(req_rows))
            + "\n"
        )

    def _architecture_content(self, extra=""):
        return (
            "# 六层架构设计\n\n"
            "| 平台 | 状态 |\n"
            "| --- | --- |\n"
            "| Gemini | 未完成（仅兼容分析文档） |\n"
            "| opencode | 未实现（0.35.0 P0 适配缺口） |\n\n"
            "## 目标目录结构\n\n"
            "```\n"
            "skills/software-project-governance/\n"
            "  SKILL.md                        ← 入口层\n"
            "  skills/                         ← 能力层\n"
            "    stage-development/SKILL.md\n"
            "```\n"
            f"{extra}\n"
        )

    def _write_release_fact_files(
        self,
        root,
        plan_content=None,
        architecture_content=None,
        evidence_content="",
    ):
        plan = root / "plan-tracker.md"
        architecture = root / "architecture.md"
        evidence = root / "evidence-log.md"
        plan.write_text(plan_content or self._plan_content(), encoding="utf-8")
        architecture.write_text(architecture_content or self._architecture_content(), encoding="utf-8")
        evidence.write_text(evidence_content, encoding="utf-8")
        return plan, architecture, evidence

    def test_release_readiness_fact_source_accepts_current_facts(self):
        with tempfile.TemporaryDirectory() as td:
            paths = self._write_release_fact_files(Path(td))
            self.assertEqual(vw.check_release_readiness_fact_source(*paths), [])

    def test_release_readiness_fact_source_requires_035_blockers_in_dependency_chain(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self._plan_content(
                dependency_chain_extra="\n    │\n    ▼\n外部验证通过后发布"
            )
            paths = self._write_release_fact_files(Path(td), plan_content=plan)
            issues = vw.check_release_readiness_fact_source(*paths)
            self.assertTrue(any("1.0.0 dependency chain missing blocker token 0.35.0" in issue for issue in issues))
            self.assertTrue(any("1.0.0 dependency chain missing blocker token RISK-030" in issue for issue in issues))
            self.assertTrue(any("1.0.0 dependency chain missing goal-drift guardrail blocker" in issue for issue in issues))

    def test_release_readiness_fact_source_requires_100_row_blockers(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self._plan_content(
                release_row=(
                    "| **1.0.0** | **预留** | **—** | **首次正式发布标签——不承载修改，仅当所有 0.32.0 "
                    "任务完成 + 外部验证通过后打 tag** | **—** | **纯版本标签** |"
                )
            )
            paths = self._write_release_fact_files(Path(td), plan_content=plan)
            issues = vw.check_release_readiness_fact_source(*paths)
            self.assertTrue(any("1.0.0 roadmap row missing release blocker 0.35.0" in issue for issue in issues))
            self.assertTrue(any("1.0.0 roadmap row missing release blocker FIX-069" in issue for issue in issues))

    def test_release_readiness_fact_source_requires_100_roadmap_row(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self._plan_content(release_row=False)
            paths = self._write_release_fact_files(Path(td), plan_content=plan)
            issues = vw.check_release_readiness_fact_source(*paths)
            self.assertTrue(any("missing 1.0.0 roadmap row" in issue for issue in issues))

    def test_release_readiness_fact_source_rejects_req_fix_mapping_drift(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self._plan_content(
                req_overrides={
                    "REQ-063": "| REQ-063 | 目标偏离看护不空跑 | AUDIT-100 | P1 | FIX-072 | 📋 待实施 | 0.35.0 |",
                }
            )
            paths = self._write_release_fact_files(Path(td), plan_content=plan)
            issues = vw.check_release_readiness_fact_source(*paths)
            self.assertTrue(any("requirement matrix REQ-063 must reference FIX-073" in issue for issue in issues))

    def test_release_readiness_fact_source_blocks_closing_fix_069_while_req_open(self):
        with tempfile.TemporaryDirectory() as td:
            evidence = (
                "| EVD-999 | FIX-069 | 维护 | 修复闭环 | FIX-069 已完成，最终审查通过。 | files | Coordinator | 2026-05-15 | G11 | 完成 |\n"
            )
            paths = self._write_release_fact_files(Path(td), evidence_content=evidence)
            issues = vw.check_release_readiness_fact_source(*paths)
            self.assertTrue(any("FIX-069 closing evidence conflicts with open REQ-059" in issue for issue in issues))

    def test_release_readiness_fact_source_blocks_final_status_closure_while_req_open(self):
        with tempfile.TemporaryDirectory() as td:
            evidence = (
                "| EVD-999 | FIX-069 | 维护 | 修复闭环 | 跨事实源检查已补齐。 | files | Coordinator | 2026-05-15 | G11 | 完成 |\n"
            )
            paths = self._write_release_fact_files(Path(td), evidence_content=evidence)
            issues = vw.check_release_readiness_fact_source(*paths)
            self.assertTrue(any("FIX-069 closing evidence conflicts with open REQ-059" in issue for issue in issues))

    def test_release_readiness_fact_source_allows_review_approval_while_req_open(self):
        with tempfile.TemporaryDirectory() as td:
            evidence = (
                "| REVIEW-FIX-069 | FIX-069 | 维护 | 代码审查 | Code Review APPROVED，未关闭任务。 | files | Code Reviewer | 2026-05-15 | G11 | 审查通过 |\n"
            )
            paths = self._write_release_fact_files(Path(td), evidence_content=evidence)
            self.assertEqual(vw.check_release_readiness_fact_source(*paths), [])

    def test_release_readiness_fact_source_rejects_adapter_e2e_overstatement(self):
        with tempfile.TemporaryDirectory() as td:
            architecture = self._architecture_content(extra="| Gemini | ✅ 已完成，真实环境 E2E 通过 |\n")
            paths = self._write_release_fact_files(Path(td), architecture_content=architecture)
            issues = vw.check_release_readiness_fact_source(*paths)
            self.assertTrue(any("architecture overstates pending Gemini/opencode" in issue for issue in issues))

    def test_release_readiness_fact_source_rejects_softened_adapter_overstatement(self):
        with tempfile.TemporaryDirectory() as td:
            architecture = self._architecture_content(
                extra="| opencode | 缺口已完成，仅剩文档，真实环境 E2E 通过 |\n"
            )
            paths = self._write_release_fact_files(Path(td), architecture_content=architecture)
            issues = vw.check_release_readiness_fact_source(*paths)
            self.assertTrue(any("architecture overstates pending Gemini/opencode" in issue for issue in issues))

    def test_release_readiness_fact_source_allows_explicit_adapter_non_closure(self):
        with tempfile.TemporaryDirectory() as td:
            architecture = self._architecture_content(
                extra="| Gemini | 仅作为预检，source proxy PASS 不构成真实环境 E2E 闭环 |\n"
            )
            paths = self._write_release_fact_files(Path(td), architecture_content=architecture)
            self.assertEqual(vw.check_release_readiness_fact_source(*paths), [])

    def test_release_readiness_fact_source_rejects_overstatement_when_req_delivered_but_fix_active(self):
        with tempfile.TemporaryDirectory() as td:
            plan = self._plan_content(
                req_overrides={
                    "REQ-061": "| REQ-061 | 主流 agent 入口状态真实 | AUDIT-100 | P0 | FIX-071 | ✅ 已交付 | 0.35.0 |",
                    "REQ-064": "| REQ-064 | E2E 真实性分层 | AUDIT-100 | P1 | FIX-074 | ✅ 已交付 | 0.35.0 |",
                },
                active_rows=(
                    "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
                    "| --- | --- | --- | --- | --- | --- | --- |\n"
                    "| **P0** | FIX-071 | 主流 code agent 适配闭环 | AUDIT-100 | 0.35.0 | 真实 agent E2E | 🔄 进行中 |"
                ),
            )
            architecture = self._architecture_content(extra="| opencode | ✅ 已完成，真实环境 E2E 通过 |\n")
            paths = self._write_release_fact_files(Path(td), plan_content=plan, architecture_content=architecture)
            issues = vw.check_release_readiness_fact_source(*paths)
            self.assertTrue(any("architecture overstates pending Gemini/opencode" in issue for issue in issues))

    def test_release_readiness_fact_source_rejects_duplicate_target_structure_entry(self):
        with tempfile.TemporaryDirectory() as td:
            architecture = (
                "# 六层架构设计\n\n"
                "## 目标目录结构\n\n"
                "```\n"
                "skills/software-project-governance/\n"
                "  SKILL.md                        ← 入口层\n"
                "  skills/                         ← 能力层\n"
                "  skills/                         ← 能力层\n"
                "```\n"
            )
            paths = self._write_release_fact_files(Path(td), architecture_content=architecture)
            issues = vw.check_release_readiness_fact_source(*paths)
            self.assertTrue(any("target directory structure repeats" in issue for issue in issues))


class HotFactSourceConsistencyTests(unittest.TestCase):
    """FIX-087: plan-tracker hot sections must describe the same active release state."""

    def _plan_content(
        self,
        *,
        dependency_line=None,
        overview_tail=None,
        fix087_status="📋 待启动",
        rel013_status="📋 待启动",
        req074_status="📋 待实施",
        roadmap_status="进行中",
        project_stage=None,
        overview_stage=None,
        active_items_intro=None,
        plan_version=None,
        extra_roadmap_rows="",
    ):
        dependency_line = dependency_line or (
            "0.38.0 FIX-082~086 已闭环，RISK-033 关闭前不得打 1.0.0\n"
            "FIX-087 + REL-013 待闭环"
        )
        overview_tail = overview_tail or "RISK-033 继续由 FIX-087 承载"
        project_stage = project_stage or "维护与演进 — 0.37.0 发布完成，0.38.0 AI 执行底座推进中，完成后再进入 1.0.0 外部验证准备"
        overview_stage = overview_stage or "维护（0.37.0 已发布，0.38.0 AI 执行底座推进中）"
        active_items_intro = active_items_intro or "0.38.0 AI 执行底座推进中。"
        plan_version_line = f"- **工作流版本**: {plan_version}\n\n" if plan_version else ""
        rows = [
            "| **P0** | FIX-082 | Runtime capability contract | AUDIT-102 | 0.38.0 | done | ✅ 已完成 (2026-05-23) |",
            "| **P0** | FIX-083 | Structured evidence schema | AUDIT-102 | 0.38.0 | done | ✅ 已完成 (2026-05-23) |",
            "| **P0** | FIX-084 | AI execution packet | AUDIT-102 | 0.38.0 | done | ✅ 已完成 (2026-05-23) |",
            "| **P0** | FIX-085 | Agent Team degraded mode | AUDIT-102 | 0.38.0 | done | ✅ 已完成 (2026-05-25) |",
            "| **P1** | FIX-086 | Projection sync guard | AUDIT-102 | 0.38.0 | done | ✅ 已完成 (2026-05-25) |",
            f"| **P1** | FIX-087 | Hot fact-source consistency guard | AUDIT-102 | 0.38.0 | pending | {fix087_status} |",
            f"| **P0** | REL-013 | Release 0.38.0 | FIX-082~087 | 0.38.0 | pending | {rel013_status} |",
        ]
        return (
            "# 当前项目样例\n\n"
            "## 项目配置\n\n"
            f"- **当前阶段**: {project_stage}\n\n"
            f"{plan_version_line}"
            "## 项目总览\n\n"
            "| 项目 | 当前阶段 | 总任务数 | 已完成 | 阻塞中 | 关键风险数 | 最近 Gate 结论 | 最近复盘日期 |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
            f"| 项目管理工作流插件 | {overview_stage} | 204 | 190 | 0 | 1 | {overview_tail} | 2026-05-26 |\n\n"
            "## 当前活跃事项\n\n"
            f"{active_items_intro}\n\n"
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            + "\n".join(rows)
            + "\n\n"
            "### 1.0.0 依赖链\n\n"
            "```\n"
            "0.37.0 FIX-080~081 + REL-012 全部闭环，RISK-032 已关闭\n"
            "    │\n"
            "    ▼\n"
            f"{dependency_line}\n"
            "    │\n"
            "    ▼\n"
            "1.0.0 正式发布\n"
            "```\n\n"
            "## 版本规划\n\n"
            "| 版本 | 状态 | 预计日期 | 核心范围 | 包含 Tier/Layer | 关键交付物 |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| **0.37.0** | **已发布** | **2026-05-22** | **事实依据看护** | **FIX-080(P0), FIX-081(P0), REL-012(P0)** | **tag v0.37.0** |\n"
            f"| **0.38.0** | **{roadmap_status}** | **2026-05-23** | **AI 执行底座** | **AUDIT-102(P0), FIX-082~085(P0), FIX-086~087(P1), REL-013(P0)** | **能力契约、结构化证据、执行包、降级模式、投影同步、热区事实源一致性** |\n"
            f"{extra_roadmap_rows}"
            "| **1.0.0** | **预留** | **—** | **首次正式发布标签——仅当 0.38.0 FIX-082~087 全部闭环、RISK-033 关闭、外部验证通过后打 tag** | **—** | **不得绕过 AI 执行底座收口** |\n\n"
            "## 需求跟踪矩阵\n\n"
            "| 需求ID | 需求描述 | 来源 | 优先级 | 关联任务 | 当前状态 | 验证方式 |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            "| REQ-070 | 真实运行时能力 | AUDIT-102 | P0 | FIX-082, FIX-085 | ✅ 已交付 | 0.38.0 |\n"
            "| REQ-071 | 结构化证据 | AUDIT-102 | P0 | FIX-083 | ✅ 已交付 | 0.38.0 |\n"
            "| REQ-072 | AI execution packet | AUDIT-102 | P0 | FIX-084 | ✅ 已交付 | 0.38.0 |\n"
            "| REQ-073 | projection sync | AUDIT-102 | P1 | FIX-086 | ✅ 已交付 | 0.38.0 |\n"
            f"| REQ-074 | hot fact-source consistency | AUDIT-102 | P1 | FIX-087 | {req074_status} | 0.38.0 |\n"
        )

    def _write_plan(self, root, content):
        path = Path(root) / "plan-tracker.md"
        path.write_text(content, encoding="utf-8")
        return path

    def _write_snapshot(self, root, *, version="0.42.0", session_date="2026-06-04", body="0.42.0 已发布"):
        path = Path(root) / "session-snapshot.md"
        path.write_text(
            "# 会话快照\n\n"
            f"- **session_date**: {session_date}\n"
            f"- **工作流版本**: {version}\n\n"
            f"{body}\n",
            encoding="utf-8",
        )
        return path

    def test_hot_fact_source_accepts_current_active_release_facts(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(td, self._plan_content())
            self.assertEqual(vw.check_hot_fact_source_consistency(path), [])

    def test_hot_fact_source_accepts_published_release_after_rel013(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(
                td,
                self._plan_content(
                    dependency_line="0.38.0 FIX-082~087 + REL-013 全部闭环，RISK-033 已关闭",
                    overview_tail="RISK-033 已关闭，REL-013 已完成",
                    fix087_status="✅ 已完成 (2026-05-28)",
                    rel013_status="✅ 已完成 (2026-05-28)",
                    req074_status="✅ 已交付",
                    roadmap_status="已发布",
                    project_stage="维护与演进 — 0.38.0 已发布，进入 1.0.0 外部验证准备",
                    overview_stage="维护（0.38.0 已发布，1.0.0 外部验证准备）",
                    active_items_intro="0.38.0 发布闭环完成，进入 1.0.0 外部验证准备。",
                ),
            )
            self.assertEqual(vw.check_hot_fact_source_consistency(path), [])

    def test_hot_fact_source_rejects_unclosed_risk_after_rel013(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(
                td,
                self._plan_content(
                    dependency_line="0.38.0 FIX-082~087 + REL-013 全部闭环，RISK-033 仍打开",
                    overview_tail="RISK-033 仍打开，REL-013 已完成",
                    fix087_status="✅ 已完成 (2026-05-28)",
                    rel013_status="✅ 已完成 (2026-05-28)",
                    req074_status="✅ 已交付",
                    roadmap_status="已发布",
                ),
            )
            issues = vw.check_hot_fact_source_consistency(path)
            self.assertTrue(any("dependency chain still lacks RISK-033 closure" in issue for issue in issues))

    def test_hot_fact_source_rejects_stale_dependency_pending_range(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(
                td,
                self._plan_content(
                    dependency_line="0.38.0 FIX-082~087 + REL-013 待实施，RISK-033 关闭前不得打 1.0.0"
                ),
            )
            issues = vw.check_hot_fact_source_consistency(path)
            self.assertTrue(any("dependency chain line marks completed FIX-082 as pending" in issue for issue in issues))

    def test_hot_fact_source_rejects_requirement_delivered_while_task_open(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(td, self._plan_content(req074_status="✅ 已交付"))
            issues = vw.check_hot_fact_source_consistency(path)
            self.assertTrue(any("REQ-074 is delivered while linked task remains open" in issue for issue in issues))

    def test_hot_fact_source_rejects_requirement_open_while_task_complete(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(
                td,
                self._plan_content(fix087_status="✅ 已完成 (2026-05-26)", req074_status="📋 待实施"),
            )
            issues = vw.check_hot_fact_source_consistency(path)
            self.assertTrue(any("REQ-074 is not delivered while FIX-087 are complete" in issue for issue in issues))

    def test_hot_fact_source_rejects_overview_remaining_completed_task(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(td, self._plan_content(overview_tail="RISK-033 继续由 FIX-086 承载"))
            issues = vw.check_hot_fact_source_consistency(path)
            self.assertTrue(any("project overview says completed FIX-086 still carries RISK-033" in issue for issue in issues))

    def test_hot_fact_source_requires_active_blocker_in_dependency_chain(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(
                td,
                self._plan_content(dependency_line="0.38.0 FIX-087 + REL-013 待闭环，完成后进入 1.0.0"),
            )
            issues = vw.check_hot_fact_source_consistency(path)
            self.assertTrue(any("dependency chain missing active blocker token RISK-033" in issue for issue in issues))
            self.assertTrue(any("dependency chain missing blocking language" in issue for issue in issues))

    def test_hot_fact_source_requires_release_blocker_in_dependency_chain(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(
                td,
                self._plan_content(dependency_line="0.38.0 FIX-087 待闭环，RISK-033 关闭前不得打 1.0.0"),
            )
            issues = vw.check_hot_fact_source_consistency(path)
            self.assertTrue(any("dependency chain missing active blocker token REL-013" in issue for issue in issues))

    def test_hot_fact_source_rejects_stale_session_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(
                td,
                self._plan_content(
                    plan_version="0.42.0",
                    dependency_line="0.38.0 FIX-082~087 + REL-013 全部闭环，RISK-033 已关闭\nREL-018 与 REL-019 关闭前不得推进 1.0.0",
                    extra_roadmap_rows=(
                        "| **0.42.0** | **已发布** | **2026-06-04** | **5 分钟成功路径** | **REL-018(P0)** | **已发布** |\n"
                        "| **0.43.0** | **规划** | **—** | **Cross-Harness E2E Closure** | **FIX-105(P1), REL-019(P0)** | **规划** |\n"
                    ),
                ),
            )
            self._write_snapshot(td, version="0.39.0", session_date="2026-05-29", body="0.39.0 已发布")
            issues = vw.check_hot_fact_source_consistency(path)
            self.assertTrue(any("session snapshot workflow version 0.39.0 does not match plan-tracker 0.42.0" in issue for issue in issues))
            self.assertTrue(any("session snapshot date 2026-05-29 is older than latest published release 0.42.0" in issue for issue in issues))
            self.assertTrue(any("session snapshot missing latest published release 0.42.0" in issue for issue in issues))

    def test_hot_fact_source_accepts_current_session_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(
                td,
                self._plan_content(
                    plan_version="0.42.0",
                    dependency_line="0.38.0 FIX-082~087 + REL-013 全部闭环，RISK-033 已关闭\nREL-018 与 REL-019 关闭前不得推进 1.0.0",
                    extra_roadmap_rows=(
                        "| **0.42.0** | **已发布** | **2026-06-04** | **5 分钟成功路径** | **REL-018(P0)** | **已发布** |\n"
                        "| **0.43.0** | **规划** | **—** | **Cross-Harness E2E Closure** | **FIX-105(P1), REL-019(P0)** | **规划** |\n"
                    ),
                ),
            )
            self._write_snapshot(td, version="0.42.0", session_date="2026-06-04", body="0.42.0 已发布；0.43.0 planned")
            self.assertEqual(vw.check_hot_fact_source_consistency(path), [])

    def test_hot_fact_source_requires_readiness_release_blockers_in_dependency_chain(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(
                td,
                self._plan_content(
                    dependency_line="0.38.0 FIX-082~087 + REL-013 全部闭环，RISK-033 已关闭\n0.43.0 关闭前不得推进 1.0.0",
                    extra_roadmap_rows=(
                        "| **0.42.0** | **已发布** | **2026-06-04** | **5 分钟成功路径** | **REL-018(P0)** | **已发布** |\n"
                        "| **0.43.0** | **规划** | **—** | **Cross-Harness E2E Closure** | **FIX-105(P1), REL-019(P0)** | **规划** |\n"
                    ),
                ),
            )
            issues = vw.check_hot_fact_source_consistency(path)
            self.assertTrue(any("dependency chain missing readiness release blocker token REL-018" in issue for issue in issues))
            self.assertTrue(any("dependency chain missing readiness release blocker token REL-019" in issue for issue in issues))


class AgentAdapterContractTests(unittest.TestCase):
    """FIX-071: mainstream code agent adapters must be explicit and runtime-aware."""

    def _write_adapter(self, root, adapter_id, support_status="runtime-verified", extra=None):
        adapter_dir = root / "adapters" / adapter_id
        adapter_dir.mkdir(parents=True, exist_ok=True)
        (adapter_dir / "README.md").write_text(f"# {adapter_id} Adapter\n", encoding="utf-8")
        (adapter_dir / "launch.py").write_text(
            f"print('== {adapter_id} Adapter Launcher ==')\n",
            encoding="utf-8",
        )
        manifest = {
            "adapter_id": adapter_id,
            "workflow_id": "software-project-governance",
            "entry_type": "thin-projection",
            "support_status": support_status,
            "supported_runtime": [adapter_id],
            "trigger": ["before governance work"],
            "inputs": ["skills/software-project-governance/SKILL.md"],
            "outputs": [".governance/plan-tracker.md"],
            "gate_behavior": {"on_fail": "block-next-stage", "required_action": "update-risk-or-decision-log"},
            "validation": {"command": "python skills/software-project-governance/infra/verify_workflow.py", "required": True},
            "native_entry": {"project_instruction_file": "AGENTS.md"},
            "runtime_capabilities": {
                "ask_user_question": {
                    "status": "degraded",
                    "evidence": "fixture has no native AskUserQuestion tool",
                    "degraded_mode": "use platform interaction fallback and record degraded evidence",
                },
                "sub_agent": {
                    "status": "degraded",
                    "evidence": "fixture does not spawn real sub-agents",
                    "degraded_mode": "use delegated reviewer evidence when available; otherwise block closure",
                },
                "tool_calling": {
                    "status": "degraded",
                    "evidence": "fixture command runner is host-mode dependent",
                    "degraded_mode": "use local validation commands and do not claim native tool closure",
                },
                "browser": {
                    "status": "degraded",
                    "evidence": "browser availability is host/plugin dependent",
                    "degraded_mode": "mark browser validation blocked when host browser tool is unavailable",
                },
                "mcp": {
                    "status": "degraded",
                    "evidence": "MCP availability is host configuration dependent",
                    "degraded_mode": "use local scripts and record MCP unavailable when not configured",
                },
                "git_hooks": {
                    "status": "native",
                    "evidence": "fixture validates git hook files and hook behavior",
                },
                "workflow_closure": {
                    "status": "degraded",
                    "evidence": "fixture intentionally models non-native governance capabilities",
                    "degraded_capabilities": ["ask_user_question", "sub_agent", "tool_calling", "browser", "mcp"],
                },
            },
            "runtime_e2e": {
                "e2e_level": "runtime-version-probe",
                "command": adapter_id,
                "version_command": f"{adapter_id} --version",
                "verified_on": "2026-05-19",
                "evidence": "runtime probe passed",
                "target_cwd_e2e": {
                    "status": "passed",
                    "command": "python skills/software-project-governance/infra/verify_workflow.py status",
                    "verified_on": "2026-05-20",
                    "evidence": "target cwd status command passed",
                },
                "agent_runtime_e2e": {
                    "status": "blocked",
                    "blocked_reason": "real agent not invoked in this fixture",
                    "evidence": "fixture documents blocked real agent E2E",
                },
                "full_e2e_verified": False,
            },
            "launcher": f"adapters/{adapter_id}/launch.py",
        }
        if adapter_id == "gemini":
            manifest["runtime_capabilities"]["ask_user_question"]["status"] = "unsupported"
            manifest["runtime_capabilities"]["ask_user_question"]["degraded_mode"] = (
                "route interaction through the outer host conversation"
            )
            manifest["runtime_capabilities"]["sub_agent"]["status"] = "unsupported"
            manifest["runtime_capabilities"]["sub_agent"]["degraded_mode"] = (
                "require external reviewer evidence"
            )
            manifest["runtime_capabilities"]["browser"]["status"] = "unsupported"
            manifest["runtime_capabilities"]["browser"]["degraded_mode"] = (
                "mark browser validation blocked"
            )
            manifest["runtime_e2e"]["auth_preflight"] = {
                "status": "blocked",
                "command": "python skills/software-project-governance/infra/verify_workflow.py gemini-auth-preflight",
                "verified_on": "2026-05-21",
                "blocked_reason": "Gemini auth missing or not configured",
                "evidence": "Gemini CLI present but no GEMINI_API_KEY, GOOGLE_API_KEY, Vertex, GCA, or settings auth source is configured.",
                "remediation": "Set GEMINI_API_KEY or GOOGLE_API_KEY, configure Vertex credentials, configure GCA auth, or configure Gemini settings auth.",
            }
            manifest["runtime_e2e"]["agent_runtime_e2e"]["blocked_reason"] = (
                "Gemini auth missing or not configured; configure GEMINI_API_KEY, "
                "GOOGLE_API_KEY, Vertex credentials, GCA auth, or Gemini settings auth."
            )
        if adapter_id == "claude":
            manifest["runtime_capabilities"]["sub_agent"] = {
                "status": "native",
                "evidence": "Claude Code supports Agent-style delegation used by the workflow.",
            }
            manifest["runtime_capabilities"]["tool_calling"] = {
                "status": "native",
                "evidence": "Claude Code runtime exposes filesystem/read tools and validation command execution.",
            }
            manifest["runtime_capabilities"]["workflow_closure"]["degraded_capabilities"] = [
                "ask_user_question", "browser", "mcp"
            ]
        if adapter_id == "opencode":
            manifest["runtime_capabilities"]["ask_user_question"]["status"] = "unsupported"
            manifest["runtime_capabilities"]["ask_user_question"]["degraded_mode"] = (
                "route interaction through the outer host conversation"
            )
            manifest["runtime_capabilities"]["sub_agent"]["status"] = "unsupported"
            manifest["runtime_capabilities"]["sub_agent"]["degraded_mode"] = (
                "require external reviewer evidence"
            )
            manifest["runtime_capabilities"]["browser"]["status"] = "unsupported"
            manifest["runtime_capabilities"]["browser"]["degraded_mode"] = (
                "mark browser validation blocked"
            )
            manifest["runtime_e2e"] = {
                "e2e_level": "real-agent-target-cwd",
                "command": "opencode",
                "version_command": "opencode --version",
                "verified_on": "2026-05-21",
                "evidence": "Local opencode command returned version 1.15.5.",
                "target_cwd_e2e": {
                    "status": "passed",
                    "command": "python skills/software-project-governance/infra/verify_workflow.py status",
                    "verified_on": "2026-05-20",
                    "evidence": "target cwd status command passed",
                },
                "provider_model_preflight": {
                    "status": "passed",
                    "command": "python skills/software-project-governance/infra/verify_workflow.py opencode-provider-preflight",
                    "verified_on": "2026-05-21",
                    "legal_models": ["deepseek-v4-pro", "deepseek-v4-flash"],
                    "evidence": "opencode provider/model preflight found supported DeepSeek models.",
                    "remediation": "Use deepseek-v4-pro or deepseek-v4-flash; remove ANSI suffix residue.",
                },
                "agent_runtime_e2e": {
                    "status": "passed",
                    "command": "python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent opencode --timeout 90; opencode run --dir . --format json ...",
                    "verified_on": "2026-05-21",
                    "evidence": "opencode run target-cwd PASS after reading .governance/plan-tracker.md and returning E2E_PLATFORM=opencode; E2E_AGENT=Coordinator; E2E_MODE=always-on x default-confirm.",
                },
                "full_e2e_verified": True,
            }
        if support_status == "not-supported-current-release":
            manifest["unsupported_reason"] = "runtime unavailable"
            manifest["no_full_coverage_claim"] = True
            manifest["runtime_e2e"]["e2e_level"] = "unsupported"
            manifest["runtime_e2e"]["verified_on"] = None
            manifest["runtime_e2e"]["evidence"] = "not verified"
            manifest["runtime_e2e"]["target_cwd_e2e"] = {
                "status": "unsupported",
                "evidence": "not verified",
            }
            manifest["runtime_e2e"]["agent_runtime_e2e"] = {
                "status": "unsupported",
                "evidence": "not verified",
            }
        if extra:
            manifest.update(extra)
        (adapter_dir / "adapter-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def _write_all_adapters(self, root):
        for adapter_id in ["claude", "codex", "gemini", "opencode"]:
            self._write_adapter(root, adapter_id)

    def test_agent_adapter_contract_accepts_verified_and_explicit_unsupported(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            self.assertEqual(vw.check_agent_adapter_contract(root=root), [])

    def test_agent_adapter_contract_rejects_missing_opencode_assets(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for adapter_id in ["claude", "codex", "gemini"]:
                self._write_adapter(root, adapter_id)
            issues = vw.check_agent_adapter_contract(root=root)
            normalized = [issue.replace("\\", "/") for issue in issues]
            self.assertTrue(any("adapters/opencode/README.md" in issue for issue in normalized))

    def test_agent_adapter_contract_rejects_unsupported_without_no_full_coverage_claim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            self._write_adapter(
                root,
                "opencode",
                support_status="not-supported-current-release",
                extra={"no_full_coverage_claim": False},
            )
            issues = vw.check_agent_adapter_contract(root=root)
            self.assertTrue(any("no_full_coverage_claim=true" in issue for issue in issues))

    def test_agent_adapter_contract_rejects_malformed_runtime_e2e_without_crashing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            self._write_adapter(root, "gemini", extra={"runtime_e2e": "bad"})
            issues = vw.check_agent_adapter_contract(root=root, run_runtime=True)
            self.assertTrue(any("runtime_e2e command/version_command required" in issue for issue in issues))

    def test_agent_adapter_contract_requires_runtime_capabilities(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            self._write_adapter(root, "codex", extra={"runtime_capabilities": {}})
            issues = vw.check_agent_adapter_contract(root=root)
            self.assertTrue(any("runtime_capabilities.ask_user_question must be an object" in issue for issue in issues))
            self.assertTrue(any("runtime_capabilities.workflow_closure must be an object" in issue for issue in issues))

    def test_agent_adapter_contract_rejects_full_closure_with_degraded_capability(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            capabilities = {
                "ask_user_question": {"status": "degraded", "evidence": "no native tool", "degraded_mode": "fallback"},
                "sub_agent": {"status": "native", "evidence": "agent tool available"},
                "tool_calling": {"status": "native", "evidence": "tools available"},
                "browser": {"status": "native", "evidence": "browser available"},
                "mcp": {"status": "native", "evidence": "mcp configured"},
                "git_hooks": {"status": "native", "evidence": "hooks installed"},
                "workflow_closure": {
                    "status": "full",
                    "evidence": "incorrect full claim",
                    "degraded_capabilities": ["ask_user_question"],
                },
            }
            self._write_adapter(root, "claude", extra={"runtime_capabilities": capabilities})
            issues = vw.check_agent_adapter_contract(root=root)
            self.assertTrue(any("workflow_closure.status=full conflicts" in issue for issue in issues))

    def test_agent_adapter_contract_requires_degraded_mode_for_non_native_capability(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            capabilities = {
                "ask_user_question": {"status": "unsupported", "evidence": "not exposed"},
                "sub_agent": {"status": "native", "evidence": "agent tool available"},
                "tool_calling": {"status": "native", "evidence": "tools available"},
                "browser": {"status": "native", "evidence": "browser available"},
                "mcp": {"status": "native", "evidence": "mcp configured"},
                "git_hooks": {"status": "native", "evidence": "hooks installed"},
                "workflow_closure": {
                    "status": "degraded",
                    "evidence": "ask_user_question missing",
                    "degraded_capabilities": ["ask_user_question"],
                },
            }
            self._write_adapter(root, "gemini", extra={"runtime_capabilities": capabilities})
            issues = vw.check_agent_adapter_contract(root=root)
            self.assertTrue(any("runtime_capabilities.ask_user_question.degraded_mode required" in issue for issue in issues))

    def test_agent_adapter_contract_rejects_codex_cli_tool_calling_overclaim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            capabilities = json.loads(
                (root / "adapters" / "codex" / "adapter-manifest.json").read_text(encoding="utf-8")
            )["runtime_capabilities"]
            capabilities["tool_calling"] = {
                "status": "native",
                "evidence": "Codex App exposes shell and patch tools",
            }
            self._write_adapter(root, "codex", extra={"runtime_capabilities": capabilities})
            issues = vw.check_agent_adapter_contract(root=root)
            self.assertTrue(any("runtime_capabilities.tool_calling.status=native overclaims" in issue for issue in issues))

    def test_agent_adapter_contract_rejects_opencode_read_e2e_as_native_tool_calling(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            capabilities = json.loads(
                (root / "adapters" / "opencode" / "adapter-manifest.json").read_text(encoding="utf-8")
            )["runtime_capabilities"]
            capabilities["tool_calling"] = {
                "status": "native",
                "evidence": "opencode read plan-tracker in target cwd",
            }
            self._write_adapter(root, "opencode", extra={"runtime_capabilities": capabilities})
            issues = vw.check_agent_adapter_contract(root=root)
            self.assertTrue(any("runtime_capabilities.tool_calling.status=native overclaims" in issue for issue in issues))

    def test_agent_adapter_contract_requires_explicit_real_e2e_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            self._write_adapter(
                root,
                "gemini",
                extra={
                    "runtime_e2e": {
                        "e2e_level": "runtime-version-probe",
                        "command": "gemini",
                        "version_command": "gemini --version",
                        "verified_on": "2026-05-20",
                        "evidence": "version probe passed",
                    }
                },
            )
            issues = vw.check_agent_adapter_contract(root=root)
            self.assertTrue(any("target_cwd_e2e must be an object" in issue for issue in issues))
            self.assertTrue(any("agent_runtime_e2e must be an object" in issue for issue in issues))

    def test_agent_adapter_contract_rejects_full_e2e_claim_without_passed_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            self._write_adapter(
                root,
                "codex",
                extra={"runtime_e2e": {
                    "e2e_level": "runtime-version-probe",
                    "command": "codex",
                    "version_command": "codex --version",
                    "verified_on": "2026-05-20",
                    "evidence": "version probe passed",
                    "target_cwd_e2e": {
                        "status": "passed",
                        "command": "python skills/software-project-governance/infra/verify_workflow.py status",
                        "verified_on": "2026-05-20",
                        "evidence": "target cwd passed",
                    },
                    "agent_runtime_e2e": {
                        "status": "blocked",
                        "blocked_reason": "timeout",
                        "evidence": "codex exec timed out",
                    },
                    "full_e2e_verified": True,
                }},
            )
            issues = vw.check_agent_adapter_contract(root=root)
            self.assertTrue(any("full_e2e_verified=true requires" in issue for issue in issues))

    def test_agent_adapter_contract_rejects_codex_app_session_as_passed_agent_e2e(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            self._write_adapter(
                root,
                "codex",
                extra={"runtime_e2e": {
                    "e2e_level": "real-agent-target-cwd",
                    "command": "codex",
                    "version_command": "codex --version",
                    "verified_on": "2026-05-21",
                    "evidence": "version probe passed",
                    "target_cwd_e2e": {
                        "status": "passed",
                        "command": "python skills/software-project-governance/infra/verify_workflow.py status",
                        "verified_on": "2026-05-20",
                        "evidence": "target cwd passed",
                    },
                    "agent_runtime_e2e": {
                        "status": "passed",
                        "command": "Codex App current session using AGENTS.md bootstrap; codex exec attempted separately and timed out in this host.",
                        "verified_on": "2026-05-20",
                        "evidence": "Current real Codex App session loaded AGENTS.md and closed workflow tasks.",
                    },
                    "full_e2e_verified": True,
                }},
            )
            issues = vw.check_agent_adapter_contract(root=root)
            self.assertTrue(any("must be real codex exec target-cwd evidence" in issue for issue in issues))

    def test_agent_adapter_contract_rejects_generic_codex_agent_runtime_e2e_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            self._write_adapter(
                root,
                "codex",
                extra={"runtime_e2e": {
                    "e2e_level": "real-agent-target-cwd",
                    "command": "codex",
                    "version_command": "codex --version",
                    "verified_on": "2026-05-21",
                    "evidence": "version probe passed",
                    "target_cwd_e2e": {
                        "status": "passed",
                        "command": "python skills/software-project-governance/infra/verify_workflow.py status",
                        "verified_on": "2026-05-21",
                        "evidence": "target cwd passed",
                    },
                    "agent_runtime_e2e": {
                        "status": "passed",
                        "command": "python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent codex",
                        "verified_on": "2026-05-21",
                        "evidence": "agent-runtime-e2e passed",
                    },
                    "full_e2e_verified": True,
                }},
            )
            issues = vw.check_agent_adapter_contract(root=root)
            self.assertTrue(any("requires real codex exec evidence" in issue for issue in issues))

    def test_agent_adapter_contract_rejects_codex_exec_pass_with_blocked_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            self._write_adapter(
                root,
                "codex",
                extra={"runtime_e2e": {
                    "e2e_level": "real-agent-target-cwd",
                    "command": "codex",
                    "version_command": "codex --version",
                    "verified_on": "2026-05-21",
                    "evidence": "version probe passed",
                    "target_cwd_e2e": {
                        "status": "passed",
                        "command": "python skills/software-project-governance/infra/verify_workflow.py status",
                        "verified_on": "2026-05-21",
                        "evidence": "target cwd passed",
                    },
                    "agent_runtime_e2e": {
                        "status": "passed",
                        "command": "codex exec -C . -s read-only --ephemeral \"report governance status\"",
                        "verified_on": "2026-05-21",
                        "evidence": "codex exec target-cwd timed out before later being marked blocked",
                    },
                    "full_e2e_verified": True,
                }},
            )
            issues = vw.check_agent_adapter_contract(root=root)
            self.assertTrue(any("must not include timeout/blocked evidence" in issue for issue in issues))

    def test_agent_adapter_contract_accepts_codex_exec_pass_with_agents_bootstrap_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            self._write_adapter(
                root,
                "codex",
                extra={"runtime_e2e": {
                    "e2e_level": "real-agent-target-cwd",
                    "command": "codex",
                    "version_command": "codex --version",
                    "verified_on": "2026-05-21",
                    "evidence": "version probe passed",
                    "target_cwd_e2e": {
                        "status": "passed",
                        "command": "python skills/software-project-governance/infra/verify_workflow.py status",
                        "verified_on": "2026-05-21",
                        "evidence": "target cwd passed",
                    },
                    "agent_runtime_e2e": {
                        "status": "passed",
                        "command": "codex exec -C project/e2e-test-project -s read-only --ephemeral \"report governance status\"",
                        "verified_on": "2026-05-21",
                        "evidence": "real codex exec target-cwd PASS after reading AGENTS.md bootstrap",
                    },
                    "full_e2e_verified": True,
                }},
            )
            self.assertEqual(vw.check_agent_adapter_contract(root=root), [])

    def test_agent_adapter_contract_accepts_codex_blocked_cli_e2e_without_full_claim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            self._write_adapter(
                root,
                "codex",
                extra={"runtime_e2e": {
                    "e2e_level": "real-agent-target-cwd",
                    "command": "codex",
                    "version_command": "codex --version",
                    "verified_on": "2026-05-21",
                    "evidence": "version probe passed",
                    "target_cwd_e2e": {
                        "status": "passed",
                        "command": "python skills/software-project-governance/infra/verify_workflow.py status",
                        "verified_on": "2026-05-20",
                        "evidence": "target cwd passed",
                    },
                    "agent_runtime_e2e": {
                        "status": "blocked",
                        "command": "python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent codex --timeout 90; codex exec -C . -s read-only --ephemeral ...",
                        "verified_on": "2026-05-21",
                        "blocked_reason": "Codex CLI target-cwd timeout",
                        "evidence": "real Codex CLI headless target-cwd command timed out",
                    },
                    "full_e2e_verified": False,
                }},
            )
            self.assertEqual(vw.check_agent_adapter_contract(root=root), [])

    def test_agent_adapter_contract_accepts_opencode_real_runtime_passed_full_claim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)

            self.assertEqual(vw.check_agent_adapter_contract(root=root), [])

    def test_agent_adapter_contract_rejects_opencode_passed_without_provider_preflight(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            runtime_e2e = {
                "e2e_level": "real-agent-target-cwd",
                "command": "opencode",
                "version_command": "opencode --version",
                "verified_on": "2026-05-21",
                "evidence": "version probe passed",
                "target_cwd_e2e": {
                    "status": "passed",
                    "command": "python skills/software-project-governance/infra/verify_workflow.py status",
                    "verified_on": "2026-05-20",
                    "evidence": "target cwd passed",
                },
                "agent_runtime_e2e": {
                    "status": "passed",
                    "command": "python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent opencode --timeout 90; opencode run --dir . --format json ...",
                    "verified_on": "2026-05-21",
                    "evidence": "opencode run target-cwd PASS after reading AGENTS.md bootstrap",
                },
                "full_e2e_verified": True,
            }
            self._write_adapter(root, "opencode", extra={"runtime_e2e": runtime_e2e})

            issues = vw.check_agent_adapter_contract(root=root)

            self.assertTrue(any("provider_model_preflight must be an object" in issue for issue in issues))

    def test_agent_adapter_contract_rejects_old_opencode_blocked_no_full_coverage_claim_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            runtime_e2e = {
                "e2e_level": "real-agent-target-cwd",
                "command": "opencode",
                "version_command": "opencode --version",
                "verified_on": "2026-05-20",
                "evidence": "Local opencode command returned version 1.15.5.",
                "target_cwd_e2e": {
                    "status": "passed",
                    "command": "python skills/software-project-governance/infra/verify_workflow.py status",
                    "verified_on": "2026-05-20",
                    "evidence": "target cwd passed",
                },
                "provider_model_preflight": {
                    "status": "blocked",
                    "command": "python skills/software-project-governance/infra/verify_workflow.py opencode-provider-preflight",
                    "verified_on": "2026-05-21",
                    "blocked_reason": "opencode provider/model config invalid: deepseek-v4-pro[1m]",
                    "evidence": "Supported names are deepseek-v4-pro and deepseek-v4-flash.",
                    "remediation": "Use deepseek-v4-pro or deepseek-v4-flash.",
                },
                "agent_runtime_e2e": {
                    "status": "blocked",
                    "command": "opencode run --dir . --format json ...",
                    "verified_on": "2026-05-20",
                    "blocked_reason": "opencode provider/model config invalid",
                    "evidence": "old blocked fixture",
                },
                "full_e2e_verified": False,
            }
            self._write_adapter(
                root,
                "opencode",
                extra={"runtime_e2e": runtime_e2e, "no_full_coverage_claim": True},
            )

            issues = vw.check_agent_adapter_contract(root=root)

            self.assertTrue(any("no_full_coverage_claim" in issue for issue in issues))

    def test_agent_adapter_contract_rejects_gemini_manifest_missing_auth_preflight(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            runtime_e2e = {
                "e2e_level": "real-agent-target-cwd",
                "command": "gemini",
                "version_command": "gemini --version",
                "verified_on": "2026-05-21",
                "evidence": "version probe passed",
                "target_cwd_e2e": {
                    "status": "passed",
                    "command": "python skills/software-project-governance/infra/verify_workflow.py status",
                    "verified_on": "2026-05-20",
                    "evidence": "target cwd passed",
                },
                "agent_runtime_e2e": {
                    "status": "blocked",
                    "blocked_reason": "Gemini auth missing or not configured; configure GEMINI_API_KEY, GOOGLE_API_KEY, Vertex, GCA, or settings auth.",
                    "evidence": "auth missing",
                },
                "full_e2e_verified": False,
            }
            self._write_adapter(root, "gemini", extra={"runtime_e2e": runtime_e2e})

            issues = vw.check_agent_adapter_contract(root=root)

            self.assertTrue(any("auth_preflight must be an object" in issue for issue in issues))

    def test_agent_adapter_contract_rejects_gemini_blocked_guidance_without_auth_sources(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            self._write_adapter(
                root,
                "gemini",
                extra={"runtime_e2e": {
                    "e2e_level": "real-agent-target-cwd",
                    "command": "gemini",
                    "version_command": "gemini --version",
                    "verified_on": "2026-05-21",
                    "evidence": "version probe passed",
                    "target_cwd_e2e": {
                        "status": "passed",
                        "command": "python skills/software-project-governance/infra/verify_workflow.py status",
                        "verified_on": "2026-05-20",
                        "evidence": "target cwd passed",
                    },
                    "agent_runtime_e2e": {
                        "status": "blocked",
                        "blocked_reason": "Gemini auth missing or not configured",
                        "evidence": "auth missing",
                    },
                    "auth_preflight": {
                        "status": "blocked",
                        "command": "python skills/software-project-governance/infra/verify_workflow.py gemini-auth-preflight",
                        "verified_on": "2026-05-21",
                        "blocked_reason": "Gemini auth missing or not configured",
                        "evidence": "auth missing",
                        "remediation": "login first",
                    },
                    "full_e2e_verified": False,
                }},
            )

            issues = vw.check_agent_adapter_contract(root=root)

            self.assertTrue(any("Gemini blocked guidance must mention" in issue for issue in issues))

    def test_agent_adapter_contract_allows_gemini_static_auth_blocked_when_runtime_e2e_passed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            self._write_adapter(
                root,
                "gemini",
                extra={"runtime_e2e": {
                    "e2e_level": "real-agent-target-cwd",
                    "command": "gemini",
                    "version_command": "gemini --version",
                    "verified_on": "2026-06-11",
                    "evidence": "version probe passed",
                    "target_cwd_e2e": {
                        "status": "passed",
                        "command": "python skills/software-project-governance/infra/verify_workflow.py status",
                        "verified_on": "2026-05-20",
                        "evidence": "target cwd passed",
                    },
                    "agent_runtime_e2e": {
                        "status": "passed",
                        "command": "GEMINI_CLI_TRUST_WORKSPACE=true python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent gemini --timeout 180",
                        "verified_on": "2026-06-11",
                        "evidence": "Real Gemini CLI target-cwd read E2E passed with GEMINI_CLI_TRUST_WORKSPACE=true.",
                    },
                    "auth_preflight": {
                        "status": "blocked",
                        "command": "python skills/software-project-governance/infra/verify_workflow.py gemini-auth-preflight",
                        "verified_on": "2026-06-11",
                        "blocked_reason": "Gemini auth missing or not configured",
                        "evidence": "Static secret-safe source probing did not find GEMINI_API_KEY, GOOGLE_API_KEY, Vertex, GCA, or settings auth; runtime E2E used host-managed auth without recording secret values.",
                        "remediation": "Set GEMINI_API_KEY or GOOGLE_API_KEY, configure Vertex credentials, configure GCA auth, or configure Gemini settings auth.",
                    },
                    "full_e2e_verified": True,
                }},
            )

            issues = vw.check_agent_adapter_contract(root=root)

            self.assertEqual([], issues)

    def test_agent_adapter_contract_rejects_gemini_static_auth_blocked_runtime_pass_without_secret_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            self._write_adapter(
                root,
                "gemini",
                extra={"runtime_e2e": {
                    "e2e_level": "real-agent-target-cwd",
                    "command": "gemini",
                    "version_command": "gemini --version",
                    "verified_on": "2026-06-11",
                    "evidence": "version probe passed",
                    "target_cwd_e2e": {
                        "status": "passed",
                        "command": "python skills/software-project-governance/infra/verify_workflow.py status",
                        "verified_on": "2026-05-20",
                        "evidence": "target cwd passed",
                    },
                    "agent_runtime_e2e": {
                        "status": "passed",
                        "command": "gemini --prompt ...",
                        "verified_on": "2026-06-11",
                        "evidence": "runtime passed",
                    },
                    "auth_preflight": {
                        "status": "blocked",
                        "command": "python skills/software-project-governance/infra/verify_workflow.py gemini-auth-preflight",
                        "verified_on": "2026-06-11",
                        "blocked_reason": "Gemini auth missing or not configured",
                        "evidence": "Static auth source missing; runtime passed.",
                        "remediation": "Set GEMINI_API_KEY or GOOGLE_API_KEY, configure Vertex credentials, configure GCA auth, or configure Gemini settings auth.",
                    },
                    "full_e2e_verified": True,
                }},
            )

            issues = vw.check_agent_adapter_contract(root=root)

            self.assertTrue(any("workspace trust and secret-safe boundary" in issue for issue in issues))

    def test_agent_adapter_runtime_checks_supported_commands_only(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)
            with patch.object(vw.shutil, "which", return_value="fake"), patch.object(
                vw, "_run_version_command", return_value=(0, "ok")
            ):
                self.assertEqual(vw.check_agent_adapter_contract(root=root, run_runtime=True), [])

    def test_agent_adapter_runtime_rejects_missing_supported_command(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)

            def fake_which(command):
                return None if command == "gemini" else "fake"

            with patch.object(vw.shutil, "which", side_effect=fake_which), patch.object(
                vw, "_run_version_command", return_value=(0, "ok")
            ):
                issues = vw.check_agent_adapter_contract(root=root, run_runtime=True)
            self.assertTrue(any("gemini: runtime command `gemini` not found" in issue for issue in issues))

    def test_agent_adapter_runtime_rejects_failed_version_command(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_all_adapters(root)

            def fake_version_command(command):
                return (1, "boom") if command == "gemini --version" else (0, "ok")

            with patch.object(vw.shutil, "which", return_value="fake"), patch.object(
                vw, "_run_version_command", side_effect=fake_version_command
            ):
                issues = vw.check_agent_adapter_contract(root=root, run_runtime=True)
            self.assertTrue(any("gemini: runtime command failed: gemini --version" in issue for issue in issues))


class RuntimeReadinessMatrixTests(unittest.TestCase):
    """FIX-106: public runtime/readiness matrix must match adapter facts."""

    def _copy_adapters(self, root):
        shutil.copytree(vw.ROOT / "adapters", root / "adapters")

    def _write_matrix(
        self,
        root,
        *,
        codex_status="PASS",
        gemini_status="PASS",
        cursor_status="RESEARCH_ONLY",
        include_boundary=True,
        include_runtime_result_table=False,
    ):
        docs_dir = root / "docs" / "requirements"
        docs_dir.mkdir(parents=True, exist_ok=True)
        boundary = (
            "\nNo official approval. No marketplace approval. No universal/full runtime support. "
            "RISK-036 remains open.\n"
            if include_boundary
            else "\nRISK-036 remains open.\n"
        )
        runtime_table = (
            "\n## Current Real Runtime Result\n\n"
            "| Agent | Real runtime result | Blocking or degraded reason |\n"
            "| --- | --- | --- |\n"
            "| codex | PASS | Codex CLI target-cwd read E2E passed. |\n"
            if include_runtime_result_table
            else ""
        )
        content = (
            "# Runtime Readiness Matrix 0.43.0\n\n"
            "## Summary\n\n"
            "| Agent | Public status | Workflow closure | Version command | Evidence and boundary |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| claude | PASS | DEGRADED | claude --version | full_e2e_verified=true; agent_runtime_e2e passed; Claude Code real target cwd E2E passed. |\n"
            f"| codex | {codex_status} | DEGRADED | codex --version | full_e2e_verified=true; real codex exec target-cwd read E2E passed. |\n"
            f"| gemini | {gemini_status} | DEGRADED | gemini --version | full_e2e_verified=true; Gemini target-cwd read E2E passed with headless workspace trust. |\n"
            "| opencode | PASS | DEGRADED | opencode --version | full_e2e_verified=true; agent_runtime_e2e passed; opencode real target cwd E2E passed. |\n"
            f"| cursor | {cursor_status} | NOT_RUNTIME_VERIFIED | manual research | Cursor entry is research-only; no adapter manifest or real target-cwd E2E evidence. |\n"
            "| copilot | RESEARCH_ONLY | NOT_RUNTIME_VERIFIED | manual research | Copilot entry is research-only; no adapter manifest or real target-cwd E2E evidence. |\n"
            f"{runtime_table}"
            f"{boundary}"
        )
        (docs_dir / "runtime-readiness-matrix-0.43.0.md").write_text(content, encoding="utf-8")

    def test_runtime_readiness_matrix_accepts_current_adapter_facts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._copy_adapters(root)
            self._write_matrix(root)
            self.assertEqual(vw.check_runtime_readiness_matrix(root), [])

    def test_runtime_readiness_matrix_rejects_stale_codex_blocked_status(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._copy_adapters(root)
            self._write_matrix(root, codex_status="BLOCKED")
            issues = vw.check_runtime_readiness_matrix(root)
            self.assertTrue(any("codex row must contain PASS" in issue for issue in issues))

    def test_runtime_readiness_matrix_rejects_stale_gemini_blocked_status(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._copy_adapters(root)
            self._write_matrix(root, gemini_status="BLOCKED")
            issues = vw.check_runtime_readiness_matrix(root)
            self.assertTrue(any("gemini row must contain PASS" in issue for issue in issues))

    def test_runtime_readiness_matrix_summary_overclaim_not_masked_by_later_table(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._copy_adapters(root)
            self._write_matrix(root, codex_status="BLOCKED", include_runtime_result_table=True)
            issues = vw.check_runtime_readiness_matrix(root)
            self.assertTrue(any("codex row must contain PASS" in issue for issue in issues))

    def test_runtime_readiness_matrix_rejects_research_only_runtime_claim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._copy_adapters(root)
            self._write_matrix(root, cursor_status="PASS")
            issues = vw.check_runtime_readiness_matrix(root)
            self.assertTrue(any("cursor row must be RESEARCH_ONLY and NOT_RUNTIME_VERIFIED" in issue for issue in issues))

    def test_runtime_readiness_matrix_requires_no_overclaim_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._copy_adapters(root)
            self._write_matrix(root, include_boundary=False)
            issues = vw.check_runtime_readiness_matrix(root)
            self.assertTrue(any("missing no-overclaim boundary token `No official approval`" in issue for issue in issues))


class MainstreamAgentLoadingTests(unittest.TestCase):
    """FIX-122: mainstream agent loading docs must stay synchronized and no-overclaim safe."""

    def _copy_current_docs(self, root):
        for rel_path in vw.MAINSTREAM_AGENT_LOADING_REQUIRED_DOCS:
            source = vw.ROOT / rel_path
            target = root / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    def _mutate_file(self, root, rel_path, mutate):
        path = root / rel_path
        path.write_text(mutate(path.read_text(encoding="utf-8")), encoding="utf-8")

    def test_mainstream_agent_loading_accepts_current_docs(self):
        self.assertEqual(vw.check_mainstream_agent_loading(vw.ROOT), [])

    def test_mainstream_agent_loading_accepts_copied_current_docs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._copy_current_docs(root)
            self.assertEqual(vw.check_mainstream_agent_loading(root), [])

    def test_mainstream_agent_loading_rejects_missing_tier1_adapter_doc(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._copy_current_docs(root)
            (root / "adapters/gemini/README.md").unlink()

            issues = vw.check_mainstream_agent_loading(root)

        self.assertTrue(any("adapters\\gemini\\README.md: missing mainstream agent loading artifact" in issue or
                            "adapters/gemini/README.md: missing mainstream agent loading artifact" in issue
                            for issue in issues))

    def test_mainstream_agent_loading_rejects_missing_source_citation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._copy_current_docs(root)
            self._mutate_file(
                root,
                "docs/requirements/mainstream-agent-loading-0.47.0.md",
                lambda text: text.replace("https://cursor.com/docs/rules", "Cursor rules docs"),
            )

            issues = vw.check_mainstream_agent_loading(root)

        self.assertTrue(any("Cursor row missing source citation URL" in issue for issue in issues))

    def test_mainstream_agent_loading_rejects_tier2_runtime_pass_claim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._copy_current_docs(root)
            self._mutate_file(
                root,
                "README.md",
                lambda text: text.replace(
                    "Compatibility reference only; no adapter manifest or runtime PASS.",
                    "Compatibility reference only; runtime PASS verified.",
                    1,
                ),
            )

            issues = vw.check_mainstream_agent_loading(root)

        self.assertTrue(any("Tier 2 row must not claim runtime PASS" in issue for issue in issues))

    def test_mainstream_agent_loading_rejects_unrelated_negation_masking_direct_claim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._copy_current_docs(root)
            self._mutate_file(
                root,
                "README.md",
                lambda text: text + "\nNo official approval, marketplace approved for all hosts.\n",
            )

            issues = vw.check_mainstream_agent_loading(root)

        self.assertTrue(any("marketplace approved" in issue for issue in issues))

    def test_mainstream_agent_loading_rejects_comma_split_claim_term_after_no_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._copy_current_docs(root)
            self._mutate_file(
                root,
                "README.md",
                lambda text: text + "\nNo official approval, marketplace approval exists for all hosts.\n",
            )

            issues = vw.check_mainstream_agent_loading(root)

        self.assertTrue(any("marketplace approval" in issue for issue in issues))

    def test_mainstream_agent_loading_rejects_positive_approval_support_claims(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._copy_current_docs(root)
            self._mutate_file(
                root,
                "README.md",
                lambda text: text + (
                    "\nThis project has official approval, received marketplace approval, "
                    "and provides universal/full runtime support.\n"
                ),
            )

            issues = vw.check_mainstream_agent_loading(root)

        self.assertTrue(any("official approval" in issue for issue in issues))
        self.assertTrue(any("marketplace approval" in issue for issue in issues))
        self.assertTrue(any("universal/full runtime support" in issue for issue in issues))

    def test_mainstream_agent_loading_rejects_positive_desktop_e2e_claim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._copy_current_docs(root)
            self._mutate_file(
                root,
                "README.md",
                lambda text: text + "\nCodex Desktop marketplace-management E2E PASS is available.\n",
            )

            issues = vw.check_mainstream_agent_loading(root)

        self.assertTrue(any("codex desktop marketplace-management e2e pass" in issue.lower() for issue in issues))

    def test_mainstream_agent_loading_rejects_unrelated_chinese_negation_masking(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._copy_current_docs(root)
            self._mutate_file(
                root,
                "README.md",
                lambda text: text + "\n不要看旧文档；this project has official approval.\n",
            )

            issues = vw.check_mainstream_agent_loading(root)

        self.assertTrue(any("official approval" in issue for issue in issues))

    def test_mainstream_agent_loading_rejects_unrelated_english_negation_masking(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._copy_current_docs(root)
            self._mutate_file(
                root,
                "README.md",
                lambda text: text + "\nNo official approval in old notes; this project has marketplace approval.\n",
            )

            issues = vw.check_mainstream_agent_loading(root)

        self.assertTrue(any("marketplace approval" in issue for issue in issues))

    def test_mainstream_agent_loading_cli_is_registered(self):
        self.assertIs(vw.cmd_check_mainstream_agent_loading, vw.cmd_check_mainstream_agent_loading)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._copy_current_docs(root)
            with patch.object(vw, "ROOT", root), redirect_stdout(io.StringIO()) as stdout:
                vw.cmd_check_mainstream_agent_loading(argparse.Namespace(fail_on_issues=True))
        self.assertIn("Result: PASSED", stdout.getvalue())


class FirstSessionMeasurementTests(unittest.TestCase):
    """FIX-107: local demo proof must stay separate from external pilot measurement."""

    def _write_measurement(
        self,
        root,
        *,
        external_status="NOT_MEASURED",
        external_result=None,
        external_boundary="Do not convert local demo PASS into external pilot PASS.",
        footer="",
        include_boundary=True,
    ):
        docs_dir = root / "docs" / "requirements"
        docs_dir.mkdir(parents=True, exist_ok=True)
        if external_result is None:
            external_result = (
                "0/5 external pilot users measured for 0.43.0 at this time. "
                "Target remains 4/5 users completing setup or resume and naming one trust signal within 5 minutes."
            )
        boundary = (
            "No official approval. No marketplace approval. No universal/full runtime support. RISK-036 remains open."
            if include_boundary
            else "RISK-036 remains open."
        )
        content = (
            "# First-Session Measurement Evidence 0.43.0\n\n"
            "## Measurement Status\n\n"
            "| Signal | Status | Evidence scope | Current result | Boundary |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| local_demo | PASS | LOCAL_DEMO_ONLY | `python skills/software-project-governance/infra/verify_workflow.py first-run-demo --assert-snapshot` passes locally and asserts Delivery Trust Snapshot fields. | Local demo-only proof; no external user success claim. |\n"
            f"| external_pilot | {external_status} | EXTERNAL_PILOT_REQUIRED | {external_result} | {external_boundary} |\n"
            f"| release_note_boundary | PASS | TEXT_GUARD | 0.43.0 release notes must publish local_demo=PASS and external_pilot=NOT_MEASURED unless timed pilot evidence is added before release. | {boundary} |\n"
            f"{footer}\n"
        )
        (docs_dir / "first-session-measurement-0.43.0.md").write_text(content, encoding="utf-8")

    def test_first_session_measurement_accepts_current_file(self):
        self.assertEqual(vw.check_first_session_measurement(vw.ROOT), [])

    def test_first_session_measurement_accepts_not_measured_external_pilot(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_measurement(root)
            self.assertEqual(vw.check_first_session_measurement(root), [])

    def test_first_session_measurement_rejects_external_pass_from_local_demo(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_measurement(
                root,
                external_status="PASS",
                external_result="4/5 from local demo `first-run-demo --assert-snapshot` output.",
            )
            issues = vw.check_first_session_measurement(root)
            self.assertTrue(any("external_pilot PASS cannot use local demo evidence" in issue for issue in issues))

    def test_first_session_measurement_accepts_real_external_pass_semantics(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_measurement(
                root,
                external_status="PASS",
                external_result=(
                    "4/5 external pilot users completed setup or resume, reached the Delivery Trust Snapshot "
                    "within 5 minutes, named one trust signal, and attached evidence at docs/pilot/run-001.md."
                ),
                external_boundary="External pilot evidence only.",
                footer="Do not convert local demo PASS into external pilot PASS.",
            )
            self.assertEqual(vw.check_first_session_measurement(root), [])

    def test_first_session_measurement_rejects_external_pass_over_five_minutes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_measurement(
                root,
                external_status="PASS",
                external_result=(
                    "4/5 external pilot users completed setup and named one trust signal after 12 minutes; "
                    "evidence at docs/pilot/run-001.md."
                ),
                external_boundary="External pilot evidence only.",
                footer="Do not convert local demo PASS into external pilot PASS.",
            )
            issues = vw.check_first_session_measurement(root)
            self.assertTrue(any("external_pilot PASS requires Delivery Trust Snapshot reached" in issue for issue in issues))
            self.assertTrue(any("external_pilot PASS requires within 5 minutes" in issue for issue in issues))
            self.assertTrue(any("external_pilot PASS exceeds five-minute limit: 12 minutes" in issue for issue in issues))

    def test_first_session_measurement_rejects_external_pass_without_trust_signal(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_measurement(
                root,
                external_status="PASS",
                external_result=(
                    "4/5 external pilot users completed setup, reached the Delivery Trust Snapshot "
                    "within 5 minutes, and attached evidence at docs/pilot/run-001.md."
                ),
                external_boundary="External pilot evidence only.",
                footer="Do not convert local demo PASS into external pilot PASS.",
            )
            issues = vw.check_first_session_measurement(root)
            self.assertTrue(any("external_pilot PASS requires trust signal named" in issue for issue in issues))

    def test_first_session_measurement_requires_no_overclaim_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_measurement(root, include_boundary=False)
            issues = vw.check_first_session_measurement(root)
            self.assertTrue(any("missing first-session boundary token `No official approval`" in issue for issue in issues))


class GovernancePackTests(unittest.TestCase):
    """FIX-108: governance packs must be registry-backed and machine-checkable."""

    def _write_pack_manifest(self, root, mutate=None):
        manifest_path = root / "skills/software-project-governance/core/manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "root_entries": {"files": [], "directories": []},
            "product": {
                "entries": [
                    {
                        "path": "skills/software-project-governance/core/governance-packs.json",
                        "type": "file",
                    }
                ],
                "glob_patterns": [],
            },
            "repo_only": {"entries": [], "glob_patterns": []},
            "canonical_product_artifacts": {
                "entries": [
                    {
                        "id": "governance-pack-registry",
                        "path": "skills/software-project-governance/core/governance-packs.json",
                        "type": "file",
                        "required": True,
                        "artifact_role": "pack-registry",
                        "validation_commands": [
                            "python skills/software-project-governance/infra/verify_workflow.py check-governance-packs --fail-on-issues",
                            "python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues",
                        ],
                    }
                ]
            },
            "cleanup_scope": {"directories": sorted(vw.PLUGIN_SCOPE_DIRS)},
        }
        if mutate:
            mutate(data)
        manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return manifest_path

    def _write_registry(self, root, mutate=None, manifest_mutate=None):
        registry_path = root / "skills/software-project-governance/core/governance-packs.json"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_pack_manifest(root, mutate=manifest_mutate)
        shared_file = root / "skills/software-project-governance/SKILL.md"
        shared_file.parent.mkdir(parents=True, exist_ok=True)
        shared_file.write_text("# Governance Skill\n", encoding="utf-8")
        docs_file = root / "docs/requirements/composable-governance-packs-0.44.0.md"
        docs_file.parent.mkdir(parents=True, exist_ok=True)
        docs_file.write_text("# Packs\n", encoding="utf-8")

        packs = []
        for pack_id in vw.GOVERNANCE_PACK_IDS:
            packs.append({
                "id": pack_id,
                "title": pack_id.replace("-", " ").title(),
                "description": f"{pack_id} pack description.",
                "default_profiles": ["standard"],
                "capabilities": [f"{pack_id}_capability"],
                "user_value": [f"{pack_id} user-visible value."],
                "files": [
                    {"path": "skills/software-project-governance/SKILL.md", "required": True},
                    {"path": "docs/requirements/composable-governance-packs-0.44.0.md", "required": True},
                ],
                "checks": ["check-governance-packs"],
                "validation_commands": [
                    "python skills/software-project-governance/infra/verify_workflow.py check-governance-packs --fail-on-issues"
                ],
                "no_overclaim_boundary": [
                    "Pack enabled does not mean release passed."
                ],
            })

        data = {
            "$schema": "https://example.com/software-project-governance/governance-packs-v1.json",
            "schema_version": "1.0",
            "workflow": "software-project-governance",
            "workflow_version": "0.44.1",
            "source_of_truth": True,
            "pack_mode": "registry-first-no-physical-split",
            "required_pack_ids": vw.GOVERNANCE_PACK_IDS,
            "no_overclaim_boundary": [
                "No official approval",
                "No marketplace approval",
                "No universal or full runtime support",
                "RISK-036 remains open",
            ],
            "packs": packs,
        }
        if mutate:
            mutate(data, root)
        registry_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return registry_path

    def test_governance_pack_registry_accepts_current_file(self):
        self.assertEqual(vw.check_governance_packs(vw.ROOT), [])

    def test_governance_pack_registry_accepts_minimal_valid_registry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_registry(root)
            self.assertEqual(vw.check_governance_packs(root), [])

    def test_governance_pack_registry_rejects_missing_required_pack(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data, _root):
                data["packs"] = [p for p in data["packs"] if p["id"] != "enterprise"]

            self._write_registry(root, mutate=mutate)
            issues = vw.check_governance_packs(root)
            self.assertTrue(any("missing required pack id(s): enterprise" in issue for issue in issues))

    def test_governance_pack_registry_rejects_unknown_pack_id(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data, _root):
                data["packs"][0]["id"] = "growth-hacking"

            self._write_registry(root, mutate=mutate)
            issues = vw.check_governance_packs(root)
            self.assertTrue(any("unknown pack id" in issue for issue in issues))

    def test_governance_pack_registry_rejects_missing_referenced_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data, _root):
                data["packs"][0]["files"].append({
                    "path": "skills/software-project-governance/core/missing-pack-file.md",
                    "required": True,
                })

            self._write_registry(root, mutate=mutate)
            issues = vw.check_governance_packs(root)
            self.assertTrue(any("referenced file `skills/software-project-governance/core/missing-pack-file.md` does not exist" in issue for issue in issues))

    def test_governance_pack_registry_rejects_missing_optional_referenced_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data, _root):
                data["packs"][0]["files"].append({
                    "path": "docs/requirements/optional-but-still-referenced.md",
                    "required": False,
                })

            self._write_registry(root, mutate=mutate)
            issues = vw.check_governance_packs(root)
            self.assertTrue(any("referenced file `docs/requirements/optional-but-still-referenced.md` does not exist" in issue for issue in issues))

    def test_governance_pack_registry_rejects_missing_required_field(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data, _root):
                del data["packs"][0]["capabilities"]

            self._write_registry(root, mutate=mutate)
            issues = vw.check_governance_packs(root)
            self.assertTrue(any("missing required field `capabilities`" in issue for issue in issues))

    def test_governance_pack_registry_rejects_duplicate_pack_id(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data, _root):
                data["packs"][1]["id"] = data["packs"][0]["id"]

            self._write_registry(root, mutate=mutate)
            issues = vw.check_governance_packs(root)
            self.assertTrue(any("duplicate pack id `governance-core`" in issue for issue in issues))

    def test_governance_pack_registry_rejects_unknown_check(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data, _root):
                data["packs"][0]["checks"].append("check-imaginary-pack-state")

            self._write_registry(root, mutate=mutate)
            issues = vw.check_governance_packs(root)
            self.assertTrue(any("unknown referenced check `check-imaginary-pack-state`" in issue for issue in issues))

    def test_governance_pack_registry_rejects_overclaim_wording(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data, _root):
                data["packs"][0]["description"] = "This pack is officially approved."

            self._write_registry(root, mutate=mutate)
            issues = vw.check_governance_packs(root)
            self.assertTrue(any("forbidden overclaim wording `officially approved`" in issue for issue in issues))

    def test_governance_pack_registry_rejects_unrelated_negation_masking_direct_claim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data, _root):
                data["packs"][0]["description"] = "No official approval, marketplace approved."

            self._write_registry(root, mutate=mutate)
            issues = vw.check_governance_packs(root)
            self.assertTrue(any("forbidden overclaim wording `marketplace approved`" in issue for issue in issues))

    def test_governance_pack_registry_accepts_scoped_boundary_negations(self):
        self.assertTrue(vw._line_has_scoped_claim_negation(
            "No official approval, marketplace approval, universal/full runtime support, or 1.0.0 production-ready claim",
            "marketplace approval",
        ))
        self.assertTrue(vw._line_has_scoped_claim_negation(
            "No official approval. No marketplace approval.",
            "marketplace approval",
        ))
        self.assertTrue(vw._line_has_scoped_claim_negation(
            "do not claim marketplace approval",
            "marketplace approval",
        ))
        self.assertFalse(vw._line_has_scoped_claim_negation(
            "No official approval, marketplace approved.",
            "marketplace approved",
        ))

    def test_governance_pack_registry_rejects_missing_manifest_artifact_binding(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def manifest_mutate(data):
                data["canonical_product_artifacts"]["entries"] = []

            self._write_registry(root, manifest_mutate=manifest_mutate)
            issues = vw.check_governance_packs(root)
            self.assertTrue(any("must declare governance-pack-registry" in issue for issue in issues))


class ReadmePackGuidanceTests(unittest.TestCase):
    """FIX-109: README must map first-run profiles to governance packs without replacing profiles."""

    def _write_readme(self, root, content):
        readme = root / "README.md"
        readme.write_text(content, encoding="utf-8")
        return readme

    def test_readme_pack_guidance_accepts_current_file(self):
        self.assertEqual(vw.check_readme_pack_guidance(vw.ROOT), [])

    def test_readme_pack_guidance_rejects_missing_profile_pack_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_readme(root, "\n".join([
                "# Demo",
                "First-run preset guidance:",
                "| Preset | Default packs to start with |",
                "| **lite** | `governance-core` |",
                "| **standard** | `governance-core`, `quality-gates`, `release-governance`, `agent-team` |",
                "| **strict** | `governance-core`, `quality-gates`, `release-governance`, `agent-team`, `enterprise` |",
            ]))

            issues = vw.check_readme_pack_guidance(root)
            self.assertTrue(any("Packs are capability modules" in issue for issue in issues))

    def test_readme_pack_guidance_rejects_pack_enabled_overclaim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            current = (vw.ROOT / "README.md").read_text(encoding="utf-8")
            self._write_readme(root, current + "\npack enabled means release passed\n")

            issues = vw.check_readme_pack_guidance(root)
            self.assertTrue(any("forbidden README pack overclaim `pack enabled means release passed`" in issue for issue in issues))

    def test_readme_pack_guidance_rejects_direct_approval_and_runtime_overclaims(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            current = (vw.ROOT / "README.md").read_text(encoding="utf-8")
            self._write_readme(
                root,
                current + "\nThis workflow is officially approved, marketplace approved, "
                "universal runtime support is verified, and 1.0.0 production-ready.\n",
            )

            issues = vw.check_readme_pack_guidance(root)
            self.assertTrue(any("forbidden README pack overclaim `officially approved`" in issue for issue in issues))
            self.assertTrue(any("forbidden README pack overclaim `marketplace approved`" in issue for issue in issues))
            self.assertTrue(any("forbidden README pack overclaim `universal runtime support is verified`" in issue for issue in issues))
            self.assertTrue(any("forbidden README pack overclaim `1.0.0 production-ready`" in issue for issue in issues))

    def test_readme_pack_guidance_rejects_unrelated_negation_masking_direct_claim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            current = (vw.ROOT / "README.md").read_text(encoding="utf-8")
            self._write_readme(root, current + "\nNo official approval, marketplace approved.\n")

            issues = vw.check_readme_pack_guidance(root)
            self.assertTrue(any("forbidden README pack overclaim `marketplace approved`" in issue for issue in issues))


class GovernancePackStatusTests(unittest.TestCase):
    """FIX-111: status and release surfaces must expose pack boundaries without overclaim."""

    def _write_valid_pack_status_project(self, root):
        root = Path(root)
        status_text = "\n".join([
            "# governance-status",
            "",
            "Delivery Trust Snapshot",
            "Pack summary: Packs are capability modules; profiles are governance intensity presets.",
            "Default packs: lite -> `governance-core`; standard -> `governance-core`, `quality-gates`, `release-governance`, `agent-team`; strict -> `governance-core`, `quality-gates`, `release-governance`, `agent-team`, `enterprise`.",
            "Enabled packs: derive from the selected profile or explicit pack registry facts; show unknown when not configured.",
            "Pack boundary: pack membership and `pack enabled` are not task evidence, independent review, quality gates, release gates, official approval, marketplace approval, universal/full runtime support, or 1.0.0 production-ready proof.",
        ])
        governance_text = status_text + "\nScenario F uses the same Pack summary fields.\n"
        for rel_path, content in {
            "commands/governance-status.md": status_text,
            "commands/governance.md": governance_text,
            "project/e2e-test-project/commands/governance-status.md": status_text,
            "project/e2e-test-project/commands/governance.md": governance_text,
        }.items():
            path = root / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        release_doc = root / "docs/requirements/composable-governance-packs-0.44.0.md"
        release_doc.parent.mkdir(parents=True, exist_ok=True)
        release_doc.write_text("\n".join([
            "# Pack release boundary",
            "",
            "## Pack boundary/no-overclaim detail",
            "",
            "Pack membership is not task evidence.",
            "`pack enabled` does not mean task evidence exists.",
            "`pack enabled` does not mean independent review passed.",
            "`pack enabled` does not mean quality gates passed.",
            "`pack enabled` does not mean release gates passed.",
            "`pack enabled` does not mean official approval was granted.",
            "`pack enabled` does not mean marketplace approval was granted.",
            "`pack enabled` does not mean universal/full runtime support is verified.",
            "`pack enabled` does not mean 1.0.0 production-ready.",
        ]), encoding="utf-8")

    def test_governance_pack_status_accepts_current_files(self):
        self.assertEqual(vw.check_governance_pack_status(vw.ROOT), [])

    def test_governance_pack_status_rejects_missing_status_pack_field(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_valid_pack_status_project(root)
            status_path = root / "commands/governance-status.md"
            status_path.write_text(
                status_path.read_text(encoding="utf-8").replace("Pack summary", "Capability summary"),
                encoding="utf-8",
            )

            issues = vw.check_governance_pack_status(root)
            self.assertTrue(any("missing pack-aware status token `Pack summary`" in issue for issue in issues))

    def test_governance_pack_status_rejects_pack_enabled_overclaim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_valid_pack_status_project(root)
            path = root / "docs/requirements/composable-governance-packs-0.44.0.md"
            path.write_text(
                path.read_text(encoding="utf-8") + "\npack enabled means release gates passed\n",
                encoding="utf-8",
            )

            issues = vw.check_governance_pack_status(root)
            self.assertTrue(any("forbidden pack status overclaim `pack enabled means release gates passed`" in issue for issue in issues))

    def test_governance_pack_status_rejects_unrelated_negation_masking_direct_claim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_valid_pack_status_project(root)
            path = root / "docs/requirements/composable-governance-packs-0.44.0.md"
            path.write_text(
                path.read_text(encoding="utf-8") + "\nNo official approval, marketplace approved.\n",
                encoding="utf-8",
            )

            issues = vw.check_governance_pack_status(root)
            self.assertTrue(any("forbidden pack status overclaim `marketplace approved`" in issue for issue in issues))

    def test_governance_pack_status_rejects_weakened_status_boundary_even_when_release_doc_is_strong(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_valid_pack_status_project(root)
            strong_boundary = (
                "Pack boundary: pack membership and `pack enabled` are not task evidence, independent review, "
                "quality gates, release gates, official approval, marketplace approval, "
                "universal/full runtime support, or 1.0.0 production-ready proof."
            )
            weak_boundary = "Pack boundary: pack membership is not completion evidence."
            for rel_path in vw.GOVERNANCE_PACK_STATUS_DOC_PATHS:
                path = root / rel_path
                path.write_text(path.read_text(encoding="utf-8").replace(strong_boundary, weak_boundary), encoding="utf-8")

            issues = vw.check_governance_pack_status(root)
            self.assertTrue(any("status pack boundary line 1 missing token `task evidence`" in issue for issue in issues))
            self.assertTrue(any("status pack boundary line 1 missing token `independent review`" in issue for issue in issues))
            self.assertTrue(any("status pack boundary line 1 missing token `quality gates`" in issue for issue in issues))
            self.assertTrue(any("status pack boundary line 1 missing token `release gates`" in issue for issue in issues))
            self.assertTrue(any("status pack boundary line 1 missing token `official approval`" in issue for issue in issues))
            self.assertTrue(any("status pack boundary line 1 missing token `marketplace approval`" in issue for issue in issues))
            self.assertTrue(any("status pack boundary line 1 missing token `universal/full runtime support`" in issue for issue in issues))
            self.assertTrue(any("status pack boundary line 1 missing token `1.0.0 production-ready`" in issue for issue in issues))

    def test_governance_pack_status_rejects_weak_template_boundary_even_with_strong_contract_line(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_valid_pack_status_project(root)
            strong_boundary = (
                "Pack boundary: pack membership and `pack enabled` are not task evidence, independent review, "
                "quality gates, release gates, official approval, marketplace approval, "
                "universal/full runtime support, or 1.0.0 production-ready proof."
            )
            weak_template_boundary = "Pack boundary: pack membership is not completion evidence."
            for rel_path in vw.GOVERNANCE_PACK_STATUS_DOC_PATHS:
                path = root / rel_path
                content = path.read_text(encoding="utf-8")
                path.write_text(
                    "\n".join([content, strong_boundary, weak_template_boundary]),
                    encoding="utf-8",
                )

            issues = vw.check_governance_pack_status(root)
            self.assertTrue(any("status pack boundary line 3 missing token `pack enabled`" in issue for issue in issues))
            self.assertTrue(any("status pack boundary line 3 missing token `task evidence`" in issue for issue in issues))
            self.assertTrue(any("status pack boundary line 3 missing token `independent review`" in issue for issue in issues))
            self.assertTrue(any("status pack boundary line 3 missing token `quality gates`" in issue for issue in issues))
            self.assertTrue(any("status pack boundary line 3 missing token `release gates`" in issue for issue in issues))
            self.assertTrue(any("status pack boundary line 3 missing token `official approval`" in issue for issue in issues))
            self.assertTrue(any("status pack boundary line 3 missing token `marketplace approval`" in issue for issue in issues))
            self.assertTrue(any("status pack boundary line 3 missing token `universal/full runtime support`" in issue for issue in issues))
            self.assertTrue(any("status pack boundary line 3 missing token `1.0.0 production-ready`" in issue for issue in issues))

    def test_governance_pack_status_rejects_missing_release_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_valid_pack_status_project(root)
            path = root / "docs/requirements/composable-governance-packs-0.44.0.md"
            path.write_text(path.read_text(encoding="utf-8").replace("`pack enabled` does not mean release gates passed.", ""), encoding="utf-8")

            issues = vw.check_governance_pack_status(root)
            self.assertTrue(any("missing release pack boundary token ``pack enabled` does not mean release gates passed.`" in issue for issue in issues))


class GovernanceContextDiscoveryTests(unittest.TestCase):
    """FIX-112: governance resume handoff must be fact-based and not-found safe."""

    def _write_project(self, root, plan=None, snapshot=None, risk=None, evidence=None, docs=True):
        gov = root / ".governance"
        gov.mkdir(parents=True, exist_ok=True)
        (gov / "plan-tracker.md").write_text(plan or "\n".join([
            "# Plan",
            "",
            "## 项目配置",
            "- **项目目标**: context test",
            "- **操作权限模式**: maximum-autonomy",
            "",
            "## 项目总览",
            "| 项目 | 当前阶段 | 总任务数 | 已完成 | 阻塞中 | 关键风险数 | 最近 Gate 结论 | 最近复盘日期 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
            "| Demo | 维护 | 1 | 0 | 0 | 0 | G11 passed | 2026-06-05 |",
        ]), encoding="utf-8")
        (gov / "session-snapshot.md").write_text(snapshot or "\n".join([
            "# Session Snapshot",
            "",
            "## Carry-over Tasks",
            "None",
        ]), encoding="utf-8")
        (gov / "evidence-log.md").write_text(evidence or "# Evidence log\n", encoding="utf-8")
        (gov / "risk-log.md").write_text(risk or "# Risk log\n", encoding="utf-8")
        if docs:
            commands = root / "commands"
            commands.mkdir(parents=True, exist_ok=True)
            contract = (
                "Delivery Trust Snapshot\n"
                "Unfinished work\n"
                "Source facts\n"
                "Blocker state\n"
                "Auto-continue\n"
                "Interrupt boundary\n"
                "not found\n"
                "do not invent\n"
                "governance-context\n"
            )
            (commands / "governance.md").write_text(contract, encoding="utf-8")
            (commands / "governance-status.md").write_text(contract, encoding="utf-8")

    def test_discovers_next_priority_from_session_snapshot(self):
        snapshot = "\n".join([
            "# Session Snapshot",
            "",
            "## 下次会话优先级",
            "1. 启动 FIX-112：Context-aware governance resume，继续从事实源承接。",
        ])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_project(root, snapshot=snapshot)

            context = vw.discover_governance_context(root)

        self.assertEqual(context["status"], "FOUND")
        self.assertIn("FIX-112", context["detected_item"])
        self.assertTrue(any("session-snapshot.md" in fact for fact in context["source_facts"]))
        self.assertEqual(context["blocker_state"], "no blocker recorded in checked facts")
        self.assertTrue(context["auto_continue"])

    def test_no_facts_returns_not_found_without_invention(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_project(root)

            context = vw.discover_governance_context(root)

        self.assertEqual(context["status"], "NOT_FOUND")
        self.assertIn("not found", context["detected_item"])
        self.assertTrue(any("no unfinished user work facts found" in fact for fact in context["source_facts"]))
        self.assertFalse(context["auto_continue"])
        self.assertIn("AskUserQuestion", context["interrupt_boundary"])

    def test_discovers_evidence_log_only_unfinished_fact(self):
        evidence = "\n".join([
            "# Evidence log",
            "| 编号 | 对应任务 ID | 阶段 | 证据类型 | 证据说明 | 证据位置 | 提交人 | 提交日期 | 关联 Gate | 备注 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "| EVD-999 | FIX-314 | 维护 | carry-over | FIX-314 next action: resume parser coverage; 未完成 | local evidence | Developer | 2026-06-07 | G11 | 进行中 |",
        ])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_project(root, evidence=evidence)

            context = vw.discover_governance_context(root)

        self.assertEqual(context["status"], "FOUND")
        self.assertIn("FIX-314", context["detected_item"])
        self.assertEqual(context["_items"][0]["task_id"], "FIX-314")
        self.assertTrue(any("evidence-log.md" in fact for fact in context["source_facts"]))
        self.assertTrue(context["auto_continue"])

    def test_completed_evidence_with_historical_blocked_pending_words_is_not_unfinished(self):
        evidence = "\n".join([
            "# Evidence log",
            "| 编号 | 对应任务 ID | 阶段 | 证据类型 | 证据说明 | 证据位置 | 提交人 | 提交日期 | 关联 Gate | 备注 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "| EVD-997 | FIX-316 | 维护 | 修复闭环 | FIX-316 completed: blocked then resolved; pending issue fixed; next action no longer needed | local evidence | Developer | 2026-06-07 | G11 | 完成 / APPROVED / closed |",
        ])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_project(root, evidence=evidence)

            context = vw.discover_governance_context(root)

        self.assertEqual(context["status"], "NOT_FOUND")
        self.assertNotIn("FIX-316", context["detected_item"])

    def test_discovers_git_status_product_file_uncommitted_work(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_project(root)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            product_file = root / "skills" / "demo" / "tool.py"
            product_file.parent.mkdir(parents=True, exist_ok=True)
            product_file.write_text("print('work')\n", encoding="utf-8")

            context = vw.discover_governance_context(root)

        self.assertEqual(context["status"], "FOUND")
        self.assertIn("GIT-WORKTREE", context["detected_item"])
        self.assertTrue(any("git status --short" in fact for fact in context["source_facts"]))
        self.assertIn("skills/demo/tool.py", " ".join(context["source_facts"]))
        self.assertTrue(context["auto_continue"])

    def test_git_status_does_not_walk_up_to_parent_repo_for_child_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            subprocess.run(["git", "init"], cwd=parent, check=True, capture_output=True, text=True)
            child = parent / "fixture"
            self._write_project(child)
            product_file = parent / "skills" / "demo" / "dirty.py"
            product_file.parent.mkdir(parents=True, exist_ok=True)
            product_file.write_text("print('parent dirty')\n", encoding="utf-8")

            context = vw.discover_governance_context(child)

        self.assertEqual(context["status"], "NOT_FOUND")
        self.assertNotIn("GIT-WORKTREE", context["detected_item"])

    def test_clean_recent_commit_without_unfinished_facts_stays_not_found(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_project(root)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            subprocess.run(["git", "add", ".governance", "commands"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-m", "FIX-000: clean baseline"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )

            context = vw.discover_governance_context(root)

        self.assertEqual(context["status"], "NOT_FOUND")
        self.assertTrue(any("git log --oneline -5" in fact for fact in context["source_facts"]))
        self.assertFalse(context["auto_continue"])

    def test_blocked_fact_disables_auto_continue(self):
        snapshot = "\n".join([
            "# Session Snapshot",
            "",
            "## Carry-over tasks",
            "| Task ID | Description | Status | Priority |",
            "| --- | --- | --- | --- |",
            "| FIX-200 | blocked handoff | blocked waiting for user decision | P0 |",
        ])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_project(root, snapshot=snapshot)

            context = vw.discover_governance_context(root)

        self.assertEqual(context["status"], "FOUND")
        self.assertIn("FIX-200", context["detected_item"])
        self.assertIn("blocked fact", context["blocker_state"])
        self.assertFalse(context["auto_continue"])
        self.assertIn("AskUserQuestion", context["interrupt_boundary"])

    def test_open_risk_with_found_item_disables_auto_continue(self):
        evidence = "\n".join([
            "# Evidence log",
            "| EVD-998 | FIX-315 | 维护 | carry-over | FIX-315 next action: resume source facts | local evidence | Developer | 2026-06-07 | G11 | 进行中 |",
        ])
        risk = "\n".join([
            "# Risk log",
            "| 编号 | 日期 | 风险/阻塞描述 | 所属阶段 | 触发条件 | 影响 | 严重级别 | Owner | 当前状态 | 缓解动作 | 截止日期 | 关联任务 | 备注 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "| RISK-999 | 2026-06-07 | open guard | 维护 | trigger | impact | 高 | Coordinator | 打开 | mitigate | 2026-06-15 | FIX-315 | note |",
        ])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_project(root, evidence=evidence, risk=risk)

            context = vw.discover_governance_context(root)

        self.assertEqual(context["status"], "FOUND")
        self.assertIn("FIX-315", context["detected_item"])
        self.assertIn("open risk guard", context["blocker_state"])
        self.assertFalse(context["auto_continue"])

    def test_check_requires_source_facts_for_found_context(self):
        broken_context = {
            "status": "FOUND",
            "detected_item": "FIX-999",
            "source_facts": [],
            "blocker_state": "no blocker recorded in checked facts",
            "next_action": "resume FIX-999",
            "auto_continue": True,
            "interrupt_boundary": "continue automatically",
        }
        with patch.object(vw, "discover_governance_context", return_value=broken_context):
            issues = vw.check_governance_context(vw.ROOT)

        self.assertTrue(any("FOUND requires source facts" in issue for issue in issues))

    def test_check_rejects_auto_continue_when_open_risk_guard_present(self):
        broken_context = {
            "status": "FOUND",
            "detected_item": "FIX-999",
            "source_facts": [".governance/risk-log.md: RISK-036"],
            "blocker_state": "open risk guard present: RISK-036",
            "next_action": "resume FIX-999",
            "auto_continue": True,
            "interrupt_boundary": "continue automatically",
        }
        with patch.object(vw, "discover_governance_context", return_value=broken_context):
            issues = vw.check_governance_context(vw.ROOT)

        self.assertTrue(any("open risk must disable auto-continue" in issue for issue in issues))

    def test_governance_context_command_accepts_target_fixture_not_found(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_project(root)
            args = argparse.Namespace(fixture=str(root), fail_on_issues=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                vw.cmd_governance_context(args)

        output = buf.getvalue()
        self.assertIn("Governance Context Discovery", output)
        self.assertIn("Status: NOT_FOUND", output)
        self.assertIn("Unfinished work: not found", output)
        self.assertIn("do not invent", output)
        self.assertIn("Governance Context Result: PASSED", output)


class CapabilityContextTests(unittest.TestCase):
    """FIX-115: capability context trace must be fact-backed and degraded-safe."""

    def _write_project(self, root, command_registered=True, tool_registered=True, future_registry=False, comment_only=False, example_only=False):
        verify_path = root / "skills/software-project-governance/infra/verify_workflow.py"
        verify_path.parent.mkdir(parents=True, exist_ok=True)
        if command_registered:
            verify_text = "\n".join([
                "import argparse",
                "",
                "def cmd_capability_context(args):",
                "    pass",
                "",
                "def main():",
                "    parser = argparse.ArgumentParser()",
                "    subparsers = parser.add_subparsers(dest='command')",
                "    subparsers.add_parser('capability-context', help='trace')",
                "    commands = {'capability-context': cmd_capability_context}",
                "    return commands",
                "",
            ])
        elif example_only:
            verify_text = "\n".join([
                "import argparse",
                "",
                "def cmd_capability_context(args):",
                "    pass",
                "",
                "def example_only():",
                "    parser = argparse.ArgumentParser()",
                "    subparsers = parser.add_subparsers(dest='command')",
                "    subparsers.add_parser('capability-context', help='trace')",
                "    commands = {'capability-context': cmd_capability_context}",
                "    return commands",
                "",
                "def main():",
                "    return None",
                "",
            ])
        elif comment_only:
            verify_text = "def main():\n    pass\n\n# capability-context mentioned in docs only\n"
        else:
            verify_text = "def main():\n    pass\n"
        verify_path.write_text(verify_text, encoding="utf-8")

        skill_path = root / "skills/software-project-governance/SKILL.md"
        skill_path.write_text("---\nname: software-project-governance\n---\n", encoding="utf-8")

        packs_path = root / "skills/software-project-governance/core/governance-packs.json"
        packs_path.parent.mkdir(parents=True, exist_ok=True)
        packs_path.write_text('{"packs":[]}\n', encoding="utf-8")

        runtime_path = root / "docs/requirements/runtime-readiness-matrix-0.43.0.md"
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
        runtime_path.write_text("# Runtime matrix\n", encoding="utf-8")

        marketplace_path = root / "docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md"
        marketplace_path.write_text("# Marketplace E2E\n", encoding="utf-8")

        req_path = root / "docs/requirements/capability-discovery-orchestration-0.45.0.md"
        req_path.write_text("\n".join([
            "# Capability Discovery",
            "capability-context",
            "source_facts",
            "rejected_alternatives",
            "degradation",
            "side_effect_boundary",
            "validation_command",
            "review_requirement",
            "no_overclaim_boundary",
        ]), encoding="utf-8")

        tools_path = root / "skills/software-project-governance/infra/TOOLS.md"
        tools_text = "\n".join([
            "# Tools",
            "TOOL-031" if tool_registered else "TOOL-030",
            "capability-context",
            "source_facts",
            "rejected_alternatives",
            "degradation",
            "side_effect_boundary",
            "validation_command",
            "review_requirement",
            "no_overclaim_boundary",
        ])
        tools_path.write_text(tools_text, encoding="utf-8")

        if future_registry:
            future_path = root / "skills/software-project-governance/core/capability-registry.json"
            future_path.write_text('{"capabilities":[]}\n', encoding="utf-8")

    def test_current_repository_capability_context_passes(self):
        issues = vw.check_capability_context(vw.ROOT)
        self.assertEqual([], issues)

    def test_discovers_degraded_local_fallback_when_registry_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_project(root)

            context = vw.discover_capability_context(root)

        self.assertEqual(context["scenario"], "capability-context")
        self.assertEqual(context["selected_capability"]["capability_id"], "local.capability-context.cli")
        self.assertEqual(context["degradation"]["status"], "DEGRADED")
        self.assertTrue(any("capability-registry.json" in fact and "missing" in fact for fact in context["source_facts"]))
        self.assertTrue(any(item["status"] == "NOT_FOUND" for item in context["rejected_alternatives"]))
        self.assertIn("read-only", context["side_effect_boundary"].lower())

    def test_comment_only_capability_context_does_not_register_cli(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_project(root, command_registered=False, comment_only=True)

            context = vw.discover_capability_context(root)
            issues = vw.check_capability_context(root)
            args = argparse.Namespace(fixture=str(root), fail_on_issues=True)

            self.assertNotEqual(context["selected_capability"]["capability_id"], "local.capability-context.cli")
            self.assertEqual(context["selected_capability"]["status"], "DEGRADED")
            self.assertTrue(any("main_subparser=no" in fact and "main_dispatch=no" in fact for fact in context["source_facts"]))
            self.assertTrue(any("missing actual capability-context CLI registration facts" in issue for issue in issues))
            with self.assertRaises(SystemExit) as raised:
                with redirect_stdout(io.StringIO()):
                    vw.cmd_capability_context(args)
            self.assertNotEqual(0, raised.exception.code)

    def test_unused_example_only_registration_does_not_register_cli(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_project(root, command_registered=False, example_only=True)

            context = vw.discover_capability_context(root)
            issues = vw.check_capability_context(root)
            args = argparse.Namespace(fixture=str(root), fail_on_issues=True)

            self.assertNotEqual(context["selected_capability"]["capability_id"], "local.capability-context.cli")
            self.assertEqual(context["selected_capability"]["status"], "DEGRADED")
            self.assertTrue(any("top_level_handler=yes" in fact and "main_subparser=no" in fact for fact in context["source_facts"]))
            self.assertTrue(any("main_dispatch=no" in fact for fact in context["source_facts"]))
            self.assertTrue(any("missing actual capability-context CLI registration facts" in issue for issue in issues))
            with self.assertRaises(SystemExit) as raised:
                with redirect_stdout(io.StringIO()):
                    vw.cmd_capability_context(args)
            self.assertNotEqual(0, raised.exception.code)

    def test_check_rejects_catalog_or_runtime_available_overclaim(self):
        broken_context = {
            "scenario": "capability-context",
            "host_id": "fixture",
            "available_capabilities": [{
                "capability_id": "internal.governance-packs.catalog",
                "kind": "fallback",
                "status": "AVAILABLE",
                "source_facts": ["core/governance-packs.json present"],
                "availability_scope": "catalog-only; not runtime PASS",
            }],
            "selected_capability": {
                "capability_id": "internal.governance-packs.catalog",
                "kind": "fallback",
                "status": "AVAILABLE",
                "source_facts": ["core/governance-packs.json present"],
            },
            "source_facts": ["fact"],
            "rejected_alternatives": [{
                "capability_id": "host.automatic-best-tool-selection",
                "status": "NOT_SUPPORTED",
                "rejection_reason": "automatic best-tool selection overclaim",
            }],
            "degradation": {"status": "AVAILABLE", "reason": "none"},
            "side_effect_boundary": "read-only",
            "validation_command": "python verify_workflow.py capability-context --fail-on-issues",
            "review_requirement": "requires independent Code Reviewer approval",
            "no_overclaim_boundary": [
                "automatic global best-tool selection",
                "catalog entry",
                "runtime PASS",
                "diagnostic selection trace",
            ],
        }
        with patch.object(vw, "discover_capability_context", return_value=broken_context):
            issues = vw.check_capability_context(vw.ROOT)

        self.assertTrue(any("catalog or runtime fact-source cannot be selected as AVAILABLE runtime PASS" in issue for issue in issues))
        self.assertTrue(any("treats catalog/runtime facts as AVAILABLE" in issue for issue in issues))


class CapabilityRegistryTests(unittest.TestCase):
    """FIX-116: external capability catalog must be factual and separate from governance packs."""

    def _write_manifest(self, root, mutate=None):
        manifest_path = root / "skills/software-project-governance/core/manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "workflow": "software-project-governance",
            "root_entries": {"files": [], "directories": []},
            "product": {
                "entries": [
                    {
                        "path": "skills/software-project-governance/core/capability-registry.json",
                        "type": "file",
                    }
                ],
                "glob_patterns": [],
            },
            "repo_only": {"entries": [], "glob_patterns": []},
            "canonical_product_artifacts": {
                "entries": [
                    {
                        "id": "governance-pack-registry",
                        "path": "skills/software-project-governance/core/governance-packs.json",
                        "type": "file",
                        "required": True,
                        "artifact_role": "pack-registry",
                        "validation_commands": [
                            "python skills/software-project-governance/infra/verify_workflow.py check-governance-packs --fail-on-issues",
                            "python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues",
                        ],
                    },
                    {
                        "id": "capability-registry",
                        "path": "skills/software-project-governance/core/capability-registry.json",
                        "type": "file",
                        "required": True,
                        "artifact_role": "external-capability-registry",
                        "validation_commands": [
                            "python skills/software-project-governance/infra/verify_workflow.py check-capability-registry --fail-on-issues",
                            "python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues",
                        ],
                    },
                ]
            },
            "cleanup_scope": {"directories": sorted(vw.PLUGIN_SCOPE_DIRS)},
        }
        if mutate:
            mutate(data)
        manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return manifest_path

    def _capability(self, capability_id, kind, status="DEGRADED"):
        return {
            "capability_id": capability_id,
            "kind": kind,
            "host_surface": f"{kind} host",
            "scenarios": [f"{kind} scenario"],
            "status": status,
            "source_facts": [f"{kind} source fact"],
            "validation_command": (
                "python skills/software-project-governance/infra/verify_workflow.py "
                "check-capability-registry --fail-on-issues"
            ),
            "side_effect_boundary": "Read-only registry validation; no external side effects.",
            "no_overclaim_boundary": [
                "Catalog entry does not mean runtime PASS.",
                "Catalog entry does not mean external capability available.",
            ],
        }

    def _write_registry(self, root, mutate=None, manifest_mutate=None):
        registry_path = root / "skills/software-project-governance/core/capability-registry.json"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_manifest(root, mutate=manifest_mutate)
        capabilities = [
            self._capability("fixture.plugin", "plugin", status="DEGRADED"),
            self._capability("fixture.skill", "skill", status="AVAILABLE"),
            self._capability("fixture.tool", "tool", status="AVAILABLE"),
            self._capability("fixture.mcp", "mcp", status="RESEARCH_ONLY"),
            self._capability("fixture.browser", "browser", status="NOT_SUPPORTED"),
            self._capability("fixture.sub-agent", "sub_agent", status="DEGRADED"),
            self._capability("fixture.script", "script", status="AVAILABLE"),
            self._capability("fixture.fallback", "fallback", status="AVAILABLE"),
        ]
        data = {
            "$schema": "https://example.com/software-project-governance/capability-registry-v1.json",
            "schema_version": "1.0",
            "workflow": "software-project-governance",
            "workflow_version": "0.44.1",
            "source_of_truth": True,
            "registry_mode": "registry-first-no-physical-plugin-split",
            "allowed_kinds": sorted(vw.CAPABILITY_REGISTRY_ALLOWED_KINDS),
            "allowed_statuses": sorted(vw.CAPABILITY_REGISTRY_ALLOWED_STATUSES),
            "no_overclaim_boundary": [
                "Catalog entry does not mean runtime PASS.",
                "Catalog entry does not mean external capability available.",
                "Governance packs are internal capability modules, not external plugins, skills, tools, MCP servers, browser tools, sub-agents, scripts, or fallbacks.",
                "Do not claim automatic best-tool selection.",
                "Do not claim universal plugin/skill/tool availability.",
                "Do not claim official approval.",
                "Do not claim marketplace approval.",
                "Do not claim 1.0.0 production-ready.",
            ],
            "capabilities": capabilities,
        }
        if mutate:
            mutate(data)
        registry_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return registry_path

    def test_capability_registry_accepts_current_file(self):
        self.assertEqual(vw.check_capability_registry(vw.ROOT), [])

    def test_capability_registry_accepts_minimal_valid_registry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_registry(root)
            self.assertEqual(vw.check_capability_registry(root), [])

    def test_capability_registry_rejects_missing_source_facts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["capabilities"][0]["source_facts"] = []

            self._write_registry(root, mutate=mutate)
            issues = vw.check_capability_registry(root)
            self.assertTrue(any("`source_facts` must be a non-empty string list" in issue for issue in issues))

    def test_capability_registry_rejects_unknown_kind(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["capabilities"][0]["kind"] = "governance_pack"

            self._write_registry(root, mutate=mutate)
            issues = vw.check_capability_registry(root)
            self.assertTrue(any("unknown kind `governance_pack`" in issue for issue in issues))

    def test_capability_registry_rejects_missing_validation_command(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["capabilities"][0]["validation_command"] = ""

            self._write_registry(root, mutate=mutate)
            issues = vw.check_capability_registry(root)
            self.assertTrue(any("`validation_command` must be a non-empty string" in issue for issue in issues))

    def test_capability_registry_rejects_catalog_runtime_pass_overclaim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["capabilities"][0]["status"] = "AVAILABLE"
                data["capabilities"][0]["source_facts"].append("Catalog entry means runtime PASS.")

            self._write_registry(root, mutate=mutate)
            issues = vw.check_capability_registry(root)
            self.assertTrue(any("forbidden capability overclaim `catalog entry means runtime pass`" in issue for issue in issues))

    def test_capability_registry_rejects_governance_pack_confusion(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["capabilities"][0]["source_facts"].append("governance pack is external capability")

            self._write_registry(root, mutate=mutate)
            issues = vw.check_capability_registry(root)
            self.assertTrue(any("forbidden capability overclaim `governance pack is external capability`" in issue for issue in issues))


class LifecycleRegistryTests(unittest.TestCase):
    """FIX-135: dynamic lifecycle registry is schema-only and classic-compatible."""

    def _write_manifest(self, root, mutate=None):
        manifest_path = root / "skills/software-project-governance/core/manifest.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "workflow": "software-project-governance",
            "root_entries": {"files": [], "directories": []},
            "product": {
                "entries": [
                    {
                        "path": "skills/software-project-governance/core/lifecycle-registry.json",
                        "type": "file",
                    }
                ],
                "glob_patterns": [],
            },
            "repo_only": {"entries": [], "glob_patterns": []},
            "canonical_product_artifacts": {
                "entries": [
                    {
                        "id": "governance-pack-registry",
                        "path": "skills/software-project-governance/core/governance-packs.json",
                        "type": "file",
                        "required": True,
                        "artifact_role": "pack-registry",
                        "validation_commands": [
                            "python skills/software-project-governance/infra/verify_workflow.py check-governance-packs --fail-on-issues",
                            "python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues",
                        ],
                    },
                    {
                        "id": "capability-registry",
                        "path": "skills/software-project-governance/core/capability-registry.json",
                        "type": "file",
                        "required": True,
                        "artifact_role": "external-capability-registry",
                        "validation_commands": [
                            "python skills/software-project-governance/infra/verify_workflow.py check-capability-registry --fail-on-issues",
                            "python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues",
                        ],
                    },
                    {
                        "id": "lifecycle-registry",
                        "path": "skills/software-project-governance/core/lifecycle-registry.json",
                        "type": "file",
                        "required": True,
                        "artifact_role": "dynamic-lifecycle-registry",
                        "validation_commands": [
                            "python skills/software-project-governance/infra/verify_workflow.py check-lifecycle-registry --fail-on-issues",
                            "python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues",
                        ],
                    },
                ]
            },
            "cleanup_scope": {"directories": sorted(vw.PLUGIN_SCOPE_DIRS)},
        }
        if mutate:
            mutate(data)
        manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return manifest_path

    def _write_registry(self, root, mutate=None, manifest_mutate=None):
        registry_path = root / "skills/software-project-governance/core/lifecycle-registry.json"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_manifest(root, mutate=manifest_mutate)
        data = json.loads(vw.LIFECYCLE_REGISTRY_PATH.read_text(encoding="utf-8"))
        if mutate:
            mutate(data)
        registry_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return registry_path

    def test_lifecycle_registry_accepts_current_file(self):
        self.assertEqual(vw.check_lifecycle_registry(vw.ROOT), [])

    def test_lifecycle_registry_accepts_minimal_copied_valid_registry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_registry(root)
            self.assertEqual(vw.check_lifecycle_registry(root), [])

    def test_command_reports_active_classic_phase_gate(self):
        args = argparse.Namespace(fail_on_issues=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            vw.cmd_check_lifecycle_registry(args)

        output = buf.getvalue()
        self.assertIn("Lifecycle Registry Check", output)
        self.assertIn("Active lifecycle mode: classic-phase-gate", output)
        self.assertIn("Default lifecycle mode: classic-phase-gate", output)
        self.assertIn("Result: PASSED", output)

    def test_lifecycle_registry_rejects_runtime_activation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["runtime_activation"]["flow_unit_status_runtime"] = True

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("runtime_activation.flow_unit_status_runtime must be false" in issue for issue in issues))

    def test_lifecycle_registry_rejects_dynamic_mode_as_active(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["active_lifecycle_mode"] = "dynamic-flow-gate"
                data["lifecycle_modes"][0]["active"] = False
                data["lifecycle_modes"][1]["active"] = True

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("active_lifecycle_mode must be classic-phase-gate" in issue for issue in issues))
            self.assertTrue(any("dynamic-flow-gate.active must be false" in issue for issue in issues))

    def test_lifecycle_registry_rejects_missing_classic_gate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["lifecycle_modes"][0]["gate_sequence"].remove("G11")

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("classic-phase-gate.gate_sequence must preserve G1-G11 order" in issue for issue in issues))

    def test_lifecycle_registry_rejects_missing_flow_unit_schema_field(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["flow_unit_schema"]["required_fields"].remove("gate_references")

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("flow_unit_schema.required_fields missing `gate_references`" in issue for issue in issues))

    def test_lifecycle_registry_rejects_missing_project_type_hook(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                del data["project_type_hooks"]["game"]

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("missing project_type_hooks for game" in issue for issue in issues))

    def test_lifecycle_registry_accepts_project_type_gate_presets(self):
        data = json.loads(vw.LIFECYCLE_REGISTRY_PATH.read_text(encoding="utf-8"))
        presets = data["project_type_gate_presets"]

        self.assertEqual(set(presets), vw.LIFECYCLE_REGISTRY_REQUIRED_PROJECT_TYPES)
        self.assertEqual(presets["game"]["default_flow_unit_type"], "chapter")
        self.assertEqual(presets["library"]["default_flow_unit_type"], "module")
        self.assertIn("playability", {item["standard_id"] for item in presets["game"]["gate_standards"]})
        self.assertIn("downstream-tests", {item["standard_id"] for item in presets["library"]["gate_standards"]})

    def test_lifecycle_registry_accepts_gate_execution_registry_contract(self):
        data = json.loads(vw.LIFECYCLE_REGISTRY_PATH.read_text(encoding="utf-8"))
        runtime_activation = data["runtime_activation"]
        registry = data["gate_execution_registry"]

        self.assertFalse(runtime_activation["declarative_gate_engine"])
        self.assertTrue(runtime_activation["classic_registry_execution"])
        self.assertTrue(registry["classic_registry_execution"])
        self.assertEqual(registry["execution_scope"], "classic-g1-g11-only")
        self.assertTrue(registry["automation_commands_are_metadata_only"])
        self.assertFalse(registry["project_migration"])
        self.assertFalse(registry["dynamic_flow_gate_default"])
        self.assertEqual([item["gate_id"] for item in registry["gate_checks"]], vw.LIFECYCLE_REGISTRY_GATES)
        for gate_entry in registry["gate_checks"]:
            for field in (
                "required_artifacts",
                "checks",
                "evidence_query",
                "automation_command",
                "human_confirmation_policy",
                "severity",
                "project_type_overrides",
            ):
                self.assertIn(field, gate_entry)

    def test_lifecycle_registry_preserves_classic_gate_check_contract_parity(self):
        data = json.loads(vw.LIFECYCLE_REGISTRY_PATH.read_text(encoding="utf-8"))
        behavior_keys = (
            "label",
            "executor",
            "function",
            "path",
            "snippet",
            "min_ratio",
            "min_count",
            "keyword",
            "result",
            "message",
            "failure_message",
        )
        contract_by_gate = {
            gate["gate_id"]: [
                {key: check[key] for key in behavior_keys if key in check}
                for check in gate["checks"]
            ]
            for gate in data["gate_execution_registry"]["gate_checks"]
        }

        self.assertEqual(contract_by_gate, {
            "G1": [
                {"label": "项目目标可衡量", "executor": "function", "function": "check_quantifiable_metrics"},
                {"label": "范围边界清晰", "executor": "function", "function": "check_scope_boundary"},
                {"label": "关键干系人已识别", "executor": "function", "function": "check_stakeholders"},
                {"label": "明確的『不做什麼』清單", "executor": "function", "function": "check_out_of_scope"},
            ],
            "G2": [
                {
                    "label": "调研覆盖技术/市场/用户三维度",
                    "executor": "snippet_in_file",
                    "path": "project/workflows/software-project-governance/research/company-practices.md",
                    "snippet": "## ",
                },
                {
                    "label": "竞争格局清晰（竞品≥3×≥4维度）",
                    "executor": "file_exists",
                    "path": "project/workflows/software-project-governance/research/agent-integration-models.md",
                },
                {
                    "label": "关键发现有数据支撑",
                    "executor": "research_doc_count",
                    "path": "project/workflows/software-project-governance/research",
                    "min_count": 4,
                    "message": "research/ 目录含多份调研文档，数据来源可追溯",
                    "failure_message": "research/ 调研文档不足 4 份",
                },
                {
                    "label": "技术可行性约束已识别",
                    "executor": "snippet_in_file",
                    "path": ".governance/risk-log.md",
                    "snippet": "RISK-",
                },
            ],
            "G3": [
                {"label": "评估了至少2个候选方案", "executor": "snippet_in_file", "path": ".governance/decision-log.md", "snippet": "备选方案"},
                {
                    "label": "评估标准事先定义",
                    "executor": "snippet_in_file",
                    "path": "skills/software-project-governance/core/protocol/plugin-contract.md",
                    "snippet": "准入标准",
                },
                {"label": "选择原因已留痕", "executor": "snippet_in_file", "path": ".governance/decision-log.md", "snippet": "选择原因"},
                {
                    "label": "关键风险已通过PoC验证",
                    "executor": "snippet_in_file",
                    "path": "skills/software-project-governance/core/protocol/headless-runner-sample.md",
                    "snippet": "## 目标",
                },
            ],
            "G4": [
                {
                    "label": "开发环境可复现",
                    "executor": "file_exists",
                    "path": "skills/software-project-governance/infra/verify_workflow.py",
                },
                {"label": "仓库结构符合约定", "executor": "function", "function": "check_all_required_files_exist"},
                {
                    "label": "基础CI可运行",
                    "executor": "file_exists",
                    "path": "skills/software-project-governance/infra/verify_workflow.py",
                },
                {
                    "label": "协作规范已建立",
                    "executor": "snippet_in_file",
                    "path": "skills/software-project-governance/SKILL.md",
                    "snippet": "MUST",
                },
            ],
            "G5": [
                {
                    "label": "架构满足非功能性需求",
                    "executor": "snippet_in_file",
                    "path": "skills/software-project-governance/core/protocol/plugin-contract.md",
                    "snippet": "冲击场景",
                },
                {"label": "模块划分清晰、职责单一", "executor": "snippet_in_file", "path": "skills/main-workflow/SKILL.md", "snippet": "## "},
                {
                    "label": "关键接口已定义",
                    "executor": "snippet_in_file",
                    "path": "skills/software-project-governance/core/protocol/command-schema.md",
                    "snippet": "Input Parameters",
                },
                {"label": "经过技术评审", "executor": "snippet_in_file", "path": "skills/tech-review/SKILL.md", "snippet": "评审"},
                {"label": "详细设计覆盖核心模块", "executor": "snippet_in_file", "path": "skills/stage-architecture/SKILL.md", "snippet": "## "},
            ],
            "G6": [
                {"label": "核心功能按设计实现", "executor": "completed_ratio", "min_ratio": 0.5},
                {
                    "label": "单元测试覆盖达标（standard: ≥70%）",
                    "executor": "file_exists",
                    "path": "skills/software-project-governance/infra/verify_workflow.py",
                },
                {"label": "Code Review 遗留项关闭", "executor": "evidence_mentions", "keyword": "code-review-standard"},
                {
                    "label": "集成验证通过",
                    "executor": "file_exists",
                    "path": "skills/software-project-governance/infra/verify_workflow.py",
                },
            ],
            "G7": [
                {"label": "关键缺陷已关闭", "executor": "function", "function": "check_risk_has_closed"},
                {
                    "label": "回归测试通过",
                    "executor": "file_exists",
                    "path": "skills/software-project-governance/infra/verify_workflow.py",
                },
                {
                    "label": "性能指标达标",
                    "executor": "constant_result",
                    "result": "NEEDS_HUMAN",
                    "message": "无性能测试基础设施——需人工确认性能指标",
                },
                {"label": "安全测试覆盖关键风险", "executor": "evidence_mentions", "keyword": "RISK-"},
            ],
            "G8": [
                {
                    "label": "CI 流水线稳定（最近运行成功率 ≥ 80%）",
                    "executor": "file_exists",
                    "path": "skills/software-project-governance/infra/verify_workflow.py",
                },
                {
                    "label": "自动化测试覆盖核心路径",
                    "executor": "snippet_in_file",
                    "path": "skills/software-project-governance/infra/verify_workflow.py",
                    "snippet": "def check_",
                },
                {
                    "label": "质量门禁生效",
                    "executor": "snippet_in_file",
                    "path": "skills/software-project-governance/infra/verify_workflow.py",
                    "snippet": "check-governance",
                },
                {"label": "部署流程文档化", "executor": "file_exists", "path": "skills/stage-release/SKILL.md"},
            ],
            "G9": [
                {"label": "发布范围明确（版本号/范围/时间窗口）", "executor": "snippet_in_file", "path": "project/CHANGELOG.md", "snippet": "## [0."},
                {"label": "变更日志完整", "executor": "file_exists", "path": "project/CHANGELOG.md"},
                {
                    "label": "回滚方案已验证",
                    "executor": "constant_result",
                    "result": "NEEDS_HUMAN",
                    "message": "无回滚测试环境——需人工确认回滚方案",
                },
                {"label": "发布后验证已定义", "executor": "file_exists", "path": "skills/release-checklist/SKILL.md"},
            ],
            "G10": [
                {"label": "收集到真实运营数据", "executor": "function", "function": "check_g10_real_operation_data"},
                {"label": "用户反馈已归档", "executor": "function", "function": "check_g10_feedback_archived_classified"},
                {"label": "关键问题已识别分类", "executor": "function", "function": "check_g10_issue_list_severity_status"},
                {"label": "优化方向已明确", "executor": "function", "function": "check_g10_executable_optimization_items"},
            ],
            "G11": [
                {"label": "复盘完成（含目标回顾/结果评估/原因分析/经验沉淀）", "executor": "function", "function": "check_g11_retro_complete"},
                {"label": "经验回灌到规则和模板", "executor": "function", "function": "check_g11_rules_templates_backfilled"},
                {
                    "label": "下轮方向已明确（计划中的下一轮/活跃 P0）",
                    "executor": "function",
                    "function": "check_g11_next_round_direction",
                },
                {"label": "版本化记录已更新", "executor": "function", "function": "check_version_consistency_heuristic"},
            ],
        })

    def test_lifecycle_registry_rejects_gate_execution_registry_boundary_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["runtime_activation"]["classic_registry_execution"] = False
                data["gate_execution_registry"]["classic_registry_execution"] = False
                data["gate_execution_registry"]["dynamic_flow_gate_default"] = True
                data["gate_execution_registry"]["project_migration"] = True

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("runtime_activation.classic_registry_execution must be true" in issue for issue in issues))
            self.assertTrue(any("gate_execution_registry.classic_registry_execution must be true" in issue for issue in issues))
            self.assertTrue(any("gate_execution_registry.dynamic_flow_gate_default must be false" in issue for issue in issues))
            self.assertTrue(any("gate_execution_registry.project_migration must be false" in issue for issue in issues))

    def test_lifecycle_registry_rejects_unknown_project_type_override(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["gate_execution_registry"]["gate_checks"][0]["project_type_overrides"]["unknown-type"] = {
                    "severity_override": "high"
                }

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("project_type_overrides unknown project type `unknown-type`" in issue for issue in issues))

    def test_lifecycle_registry_rejects_malformed_project_type_override_check(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["gate_execution_registry"]["gate_checks"][0]["project_type_overrides"]["game"]["additional_checks"] = [
                    {
                        "check_id": "bad_override_check",
                        "label": "Bad override check",
                        "executor": "shell",
                        "severity": "urgent",
                    }
                ]

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("additional_checks.bad_override_check.executor has unknown value `shell`" in issue for issue in issues))
            self.assertTrue(any("additional_checks.bad_override_check.severity must be one of" in issue for issue in issues))

    def test_lifecycle_registry_rejects_missing_project_type_gate_preset(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                del data["project_type_gate_presets"]["game"]

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("missing project_type_gate_presets for game" in issue for issue in issues))
            self.assertTrue(any("project_type_gate_presets keys must match project_type_hooks keys" in issue for issue in issues))

    def test_lifecycle_registry_rejects_preset_without_hook_counterpart(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                del data["project_type_hooks"]["library"]

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("missing project_type_hooks for library" in issue for issue in issues))
            self.assertTrue(any("project_type_gate_presets keys must match project_type_hooks keys" in issue for issue in issues))

    def test_lifecycle_registry_rejects_missing_preset_required_field(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                del data["project_type_gate_presets"]["web-app"]["quality_budget"]

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("project_type_gate_presets.web-app: missing required field `quality_budget`" in issue for issue in issues))

    def test_lifecycle_registry_rejects_profile_boundary_without_orthogonal(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["project_type_gate_presets"]["mobile-app"]["profile_intensity_boundary"] = (
                    "Mobile projects use strict profile presets."
                )

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("profile_intensity_boundary must state project type and profile are orthogonal" in issue for issue in issues))

    def test_lifecycle_registry_rejects_undeclared_project_type_unit_template(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["flow_unit_schema"]["allowed_unit_types"].remove("screen")

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any(
                "project_type_hooks.mobile-app.unit_templates includes undeclared unit type `screen`" in issue
                for issue in issues
            ))

    def test_lifecycle_registry_rejects_preset_default_not_in_hook_templates(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["project_type_gate_presets"]["cli-tool"]["unit_templates"] = ["module", "release-candidate"]

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any(
                "project_type_gate_presets.cli-tool.unit_templates must match project_type_hooks.cli-tool.unit_templates" in issue
                for issue in issues
            ))
            self.assertTrue(any(
                "project_type_gate_presets.cli-tool.default_flow_unit_type must be included in unit_templates" in issue
                for issue in issues
            ))

    def test_lifecycle_registry_rejects_project_type_default_not_in_unit_templates(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["project_type_hooks"]["ai-agent-plugin"]["default_flow_unit_type"] = "module"

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any(
                "project_type_hooks.ai-agent-plugin.default_flow_unit_type must be included in unit_templates" in issue
                for issue in issues
            ))

    def test_lifecycle_registry_rejects_project_type_default_not_allowed_unit_type(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["project_type_hooks"]["internal-script"]["unit_templates"].append("task")
                data["project_type_hooks"]["internal-script"]["default_flow_unit_type"] = "task"

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any(
                "project_type_hooks.internal-script.default_flow_unit_type must be declared in flow_unit_schema.allowed_unit_types" in issue
                for issue in issues
            ))

    def test_lifecycle_registry_rejects_game_missing_required_gate_standard(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["project_type_gate_presets"]["game"]["gate_standards"] = [
                    item for item in data["project_type_gate_presets"]["game"]["gate_standards"]
                    if item["standard_id"] != "playability"
                ]

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("gate_standards missing game standards: playability" in issue for issue in issues))

    def test_lifecycle_registry_rejects_library_missing_required_gate_standard(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["project_type_gate_presets"]["library"]["gate_standards"] = [
                    item for item in data["project_type_gate_presets"]["library"]["gate_standards"]
                    if item["standard_id"] != "downstream-tests"
                ]

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("gate_standards missing library standards: downstream-tests" in issue for issue in issues))

    def test_lifecycle_registry_rejects_gate_standard_unknown_gate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["project_type_gate_presets"]["library"]["gate_standards"][0]["gate_references"].append("G12")

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("unknown gate reference `G12`" in issue for issue in issues))

    def test_lifecycle_registry_reports_non_object_root_as_schema_issue(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            registry_path = root / "skills/software-project-governance/core/lifecycle-registry.json"
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_manifest(root)
            registry_path.write_text(json.dumps([]), encoding="utf-8")

            issues = vw.check_lifecycle_registry(root)

            self.assertEqual(len(issues), 1)
            self.assertTrue(issues[0].endswith("lifecycle registry root must be an object"))

    def test_lifecycle_registry_rejects_python_game_missing_chapter(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["examples"][0]["flow_units"] = data["examples"][0]["flow_units"][:-1]

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("must define game.chapter.01 through game.chapter.10" in issue for issue in issues))

    def test_lifecycle_registry_rejects_python_game_wrong_lane(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["examples"][0]["flow_units"][2]["gate_lane"] = "testing"

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("chapter 3 development" in issue for issue in issues))

    def test_lifecycle_registry_rejects_missing_manifest_artifact_binding(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def manifest_mutate(data):
                data["canonical_product_artifacts"]["entries"] = [
                    entry for entry in data["canonical_product_artifacts"]["entries"]
                    if entry["id"] != "lifecycle-registry"
                ]

            self._write_registry(root, manifest_mutate=manifest_mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("must declare lifecycle-registry" in issue for issue in issues))

    def test_lifecycle_registry_rejects_readiness_overclaim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["examples"][0]["rollup_summary"] += " RISK-037 closed and 1.0.0 production-ready."

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("forbidden lifecycle overclaim `risk-037 closed`" in issue for issue in issues))
            self.assertTrue(any("forbidden lifecycle overclaim `1.0.0 production-ready`" in issue for issue in issues))

    def test_lifecycle_registry_rejects_preset_no_overclaim_variants(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["project_type_gate_presets"]["ai-agent-plugin"]["release_checks"].append(
                    "declarative gate engine active; dynamic-flow-gate default; RISK-036 closure achieved."
                )
                data["runtime_activation"]["project_migration"] = True

            self._write_registry(root, mutate=mutate)
            issues = vw.check_lifecycle_registry(root)
            self.assertTrue(any("runtime_activation.project_migration must be false" in issue for issue in issues))
            self.assertTrue(any("forbidden lifecycle overclaim `declarative gate engine active`" in issue for issue in issues))
            self.assertTrue(any("forbidden lifecycle overclaim `dynamic-flow-gate default`" in issue for issue in issues))
            self.assertTrue(any("forbidden lifecycle overclaim `risk-036 closure achieved`" in issue for issue in issues))

    def test_lifecycle_registry_rejects_lifecycle_overclaim_regex_variants(self):
        cases = [
            ("declarative gate engine is active", "declarative gate engine active"),
            ("declarative gate engine activated", "declarative gate engine active"),
            ("activates the declarative gate engine", "declarative gate engine active"),
            ("dynamic-flow-gate is the default lifecycle mode", "dynamic-flow-gate default"),
            ("dynamic-flow-gate is now default", "dynamic-flow-gate default"),
        ]
        for wording, label in cases:
            with self.subTest(wording=wording):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)

                    def mutate(data):
                        data["project_type_gate_presets"]["ai-agent-plugin"]["release_checks"].append(wording)

                    self._write_registry(root, mutate=mutate)
                    issues = vw.check_lifecycle_registry(root)
                    self.assertTrue(any(f"forbidden lifecycle overclaim `{label}`" in issue for issue in issues))

    def test_lifecycle_registry_preserves_scoped_lifecycle_overclaim_negation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["project_type_gate_presets"]["ai-agent-plugin"]["release_checks"].extend([
                    "This does not mean the declarative gate engine is active.",
                    "This does not make dynamic-flow-gate the default lifecycle mode.",
                    "The declarative gate engine activated claim is not verified.",
                    "This does not mean dynamic-flow-gate is now default.",
                ])

            self._write_registry(root, mutate=mutate)
            self.assertEqual(vw.check_lifecycle_registry(root), [])


class FlowUnitRuntimeTests(unittest.TestCase):
    """FIX-136: optional flow-unit runtime hot state is visibility-only."""

    def _unit(self, idx, lane, stage, *, deps=None, blockers=None, loop_count=0, gate_status=None):
        return {
            "flow_unit_id": f"game.chapter.{idx:02d}",
            "title": f"Chapter {idx}",
            "unit_type": "chapter",
            "project_type": "game",
            "lifecycle_mode": "dynamic-flow-gate",
            "current_stage": stage,
            "current_subphase": "backlog" if lane == "backlog" else lane,
            "gate_lane": lane,
            "gate_references": ["G5"] if lane == "backlog" else ["G6", "G7"],
            "allowed_next_transitions": ["classic-G5"],
            "dependencies": deps or [],
            "blockers": blockers or [],
            "evidence_refs": [],
            "loop_state": {
                "active_loop": loop_count > 0,
                "loop_count": loop_count,
                "last_loop_type": "defect-rework" if loop_count else None,
            },
            "runtime_status_source": "hot-project-state",
            "gate_state": {"status": gate_status or lane},
        }

    def _runtime(self, mutate=None):
        units = [
            self._unit(1, "released", "operations", gate_status="released"),
            self._unit(2, "testing", "testing", deps=["game.chapter.01"], loop_count=1, gate_status="testing"),
            self._unit(3, "development", "development", deps=["game.chapter.02"], gate_status="in-progress"),
        ]
        for idx in range(4, 11):
            units.append(self._unit(idx, "backlog", "architecture", deps=[f"game.chapter.{idx - 1:02d}"], gate_status="backlog"))
        data = {
            "schema_version": "1.0",
            "workflow_model": "dynamic-flow-gate",
            "default_lifecycle_mode": "classic-phase-gate",
            "runtime_scope": "runtime-visibility-only",
            "runtime_status_source": "hot-project-state",
            "declarative_gate_engine": False,
            "project_migration": False,
            "active_lanes": {
                "released": ["game.chapter.01"],
                "testing": ["game.chapter.02"],
                "development": ["game.chapter.03"],
                "backlog": [f"game.chapter.{idx:02d}" for idx in range(4, 11)],
            },
            "blocked_downstream_units": [],
            "rollup_status": "chapter 1 released; chapter 2 testing; chapter 3 development; chapter 4-10 backlog",
            "flow_units": units,
            "no_overclaim_boundary": [
                "Flow-unit runtime is runtime visibility only.",
                "Flow-unit runtime does not activate declarative gate engine.",
                "Flow-unit runtime does not migrate projects.",
                "Classic G1-G11 remains compatible.",
                "Flow-unit runtime does not close RISK-036.",
                "Flow-unit runtime does not close RISK-037.",
                "Flow-unit runtime does not claim 1.0.0 production-ready.",
            ],
        }
        if mutate:
            mutate(data)
        return data

    def _write_runtime(self, root, mutate=None, raw=None):
        path = root / ".governance/flow-unit-runtime.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        if raw is not None:
            path.write_text(raw, encoding="utf-8")
        else:
            path.write_text(json.dumps(self._runtime(mutate), indent=2), encoding="utf-8")
        return path

    def test_flow_unit_runtime_missing_file_is_safe(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.assertEqual(vw.check_flow_unit_runtime(root), [])
            context = vw.discover_flow_unit_runtime_context(root)
            self.assertEqual(context["status"], "NOT_FOUND")

    def test_flow_unit_runtime_accepts_python_game_distribution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_runtime(root)
            self.assertEqual(vw.check_flow_unit_runtime(root), [])
            context = vw.discover_flow_unit_runtime_context(root)
            self.assertEqual(context["workflow_model"], "dynamic-flow-gate")
            self.assertEqual(context["active_lanes"]["released"], ["game.chapter.01"])
            self.assertEqual(context["active_lanes"]["testing"], ["game.chapter.02"])
            self.assertEqual(context["active_lanes"]["development"], ["game.chapter.03"])
            self.assertEqual(context["active_lanes"]["backlog"], [f"game.chapter.{idx:02d}" for idx in range(4, 11)])
            self.assertIn("chapter 1 released", context["rollup_status"])

    def test_flow_unit_runtime_dependency_blocking_only_downstream(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["flow_units"][2]["blockers"] = ["missing implementation evidence"]
                data["flow_units"][2]["gate_state"]["status"] = "blocked"
                data["blocked_downstream_units"] = ["game.chapter.04"]

            self._write_runtime(root, mutate=mutate)
            self.assertEqual(vw.check_flow_unit_runtime(root), [])
            context = vw.discover_flow_unit_runtime_context(root)
            self.assertEqual(context["blocked_downstream_units"], ["game.chapter.04"])
            self.assertNotIn("game.chapter.02", context["blocked_downstream_units"])

    def test_flow_unit_runtime_rejects_sibling_completion_implied_by_bad_blocking(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["flow_units"][2]["blockers"] = ["blocked"]
                data["flow_units"][2]["gate_state"]["status"] = "blocked"
                data["blocked_downstream_units"] = ["game.chapter.02", "game.chapter.04"]

            self._write_runtime(root, mutate=mutate)
            issues = vw.check_flow_unit_runtime(root)
            self.assertTrue(any("only declared downstream dependents" in issue for issue in issues))

    def test_flow_unit_runtime_loop_counters_are_reported_and_validated(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_runtime(root)
            context = vw.discover_flow_unit_runtime_context(root)
            self.assertEqual(context["loop_counters"]["game.chapter.02"], 1)

            def mutate(data):
                data["flow_units"][1]["loop_state"]["loop_count"] = -1

            self._write_runtime(root, mutate=mutate)
            issues = vw.check_flow_unit_runtime(root)
            self.assertTrue(any("loop_state.loop_count must be a non-negative integer" in issue for issue in issues))

    def test_flow_unit_runtime_malformed_nested_state_fails_closed_without_discovery_crash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["flow_units"][1]["gate_state"] = "testing"
                data["flow_units"][2]["loop_state"]["loop_count"] = "many"

            self._write_runtime(root, mutate=mutate)
            context = vw.discover_flow_unit_runtime_context(root)
            self.assertEqual(context["status"], "FOUND")
            self.assertEqual(context["loop_counters"]["game.chapter.03"], 0)
            issues = vw.check_flow_unit_runtime(root)
            self.assertTrue(any("gate_state must be an object" in issue for issue in issues))
            self.assertTrue(any("loop_state.loop_count must be a non-negative integer" in issue for issue in issues))

    def test_flow_unit_runtime_preserves_classic_and_no_overclaim_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["default_lifecycle_mode"] = "dynamic-flow-gate"
                data["declarative_gate_engine"] = True
                data["no_overclaim_boundary"].append("RISK-037 closed and 1.0.0 production-ready.")

            self._write_runtime(root, mutate=mutate)
            issues = vw.check_flow_unit_runtime(root)
            self.assertTrue(any("default_lifecycle_mode must preserve classic-phase-gate" in issue for issue in issues))
            self.assertTrue(any("declarative_gate_engine must be false" in issue for issue in issues))
            self.assertTrue(any("forbidden flow-unit runtime overclaim `risk-037 closed`" in issue for issue in issues))
            self.assertTrue(any("forbidden flow-unit runtime overclaim `1.0.0 production-ready`" in issue for issue in issues))

    def test_flow_unit_runtime_rejects_equivalent_risk_closure_overclaims(self):
        variants = [
            ("RISK-037 is closed.", "risk-037 closed"),
            ("Closed RISK-037 after runtime work.", "risk-037 closed"),
            ("RISK-037 closure achieved.", "risk-037 closure achieved"),
            ("RISK-036 is closed.", "risk-036 closed"),
            ("Closed RISK-036 after external validation.", "risk-036 closed"),
            ("RISK-036 closure achieved.", "risk-036 closure achieved"),
        ]
        for wording, expected in variants:
            with self.subTest(wording=wording):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)

                    def mutate(data, wording=wording):
                        data["rollup_status"] = wording

                    self._write_runtime(root, mutate=mutate)
                    issues = vw.check_flow_unit_runtime(root)
                    self.assertTrue(
                        any(f"forbidden flow-unit runtime overclaim `{expected}`" in issue for issue in issues),
                        issues,
                    )

    def test_flow_unit_runtime_preserves_scoped_risk_closure_negation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["rollup_status"] = (
                    "Flow-unit runtime does not claim RISK-037 is closed; "
                    "it does not claim closed RISK-036 evidence."
                )

            self._write_runtime(root, mutate=mutate)
            issues = vw.check_flow_unit_runtime(root)
            self.assertFalse(any("forbidden flow-unit runtime overclaim `risk-037" in issue for issue in issues))
            self.assertFalse(any("forbidden flow-unit runtime overclaim `risk-036" in issue for issue in issues))

    def test_flow_unit_runtime_invalid_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_runtime(root, raw=json.dumps([]))
            issues = vw.check_flow_unit_runtime(root)
            self.assertEqual(len(issues), 1)
            self.assertTrue(issues[0].endswith("flow-unit runtime root must be an object"))
            context = vw.discover_flow_unit_runtime_context(root)
            self.assertEqual(context["status"], "INVALID")
            self.assertIn("root must be an object", " ".join(context["source_facts"]))

    def test_flow_unit_runtime_command_fails_closed_for_non_object_root_without_crash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_runtime(root, raw=json.dumps([]))
            args = argparse.Namespace(fixture=str(root), fail_on_issues=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    vw.cmd_check_flow_unit_runtime(args)
            self.assertEqual(cm.exception.code, 1)
            output = buf.getvalue()
            self.assertIn("Runtime state: INVALID", output)
            self.assertIn("flow-unit runtime root must be an object", output)

    def test_flow_unit_runtime_command_fails_closed_for_non_string_boundary_item_without_crash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["no_overclaim_boundary"].append({"bad": "state"})

            self._write_runtime(root, mutate=mutate)
            args = argparse.Namespace(fixture=str(root), fail_on_issues=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    vw.cmd_check_flow_unit_runtime(args)
            self.assertEqual(cm.exception.code, 1)
            output = buf.getvalue()
            self.assertIn("Runtime state: FOUND", output)
            self.assertIn("no_overclaim_boundary must be a non-empty string list", output)

    def test_governance_context_ignores_malformed_flow_runtime_without_crash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_runtime(root, raw=json.dumps([]))
            context = vw.discover_governance_context(root)
            self.assertIn(context["status"], {"FOUND", "NOT_FOUND"})
            self.assertIsNone(context.get("flow_unit_runtime"))

    def test_governance_context_keeps_malformed_boundary_runtime_visible_without_crash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def mutate(data):
                data["no_overclaim_boundary"].append(42)

            self._write_runtime(root, mutate=mutate)
            context = vw.discover_governance_context(root)
            self.assertIn(context["status"], {"FOUND", "NOT_FOUND"})
            flow_context = context.get("flow_unit_runtime")
            self.assertIsNotNone(flow_context)
            self.assertEqual(flow_context["status"], "FOUND")
            self.assertIn("runtime visibility only", flow_context["no_overclaim_boundary"])
            issues = vw.check_flow_unit_runtime(root)
            self.assertTrue(any("no_overclaim_boundary must be a non-empty string list" in issue for issue in issues))

    def test_flow_unit_runtime_command_reports_context(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_runtime(root)
            args = argparse.Namespace(fixture=str(root), fail_on_issues=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                vw.cmd_check_flow_unit_runtime(args)
            output = buf.getvalue()
            self.assertIn("Flow Unit Runtime Check", output)
            self.assertIn("Workflow model: dynamic-flow-gate", output)
            self.assertIn("Result: PASSED", output)


class DynamicLifecycleMigrationTests(unittest.TestCase):
    """FIX-139: migration preview is read-only, structured, and conservative."""

    def _unit(self, idx, lane, stage, *, deps=None, gate_status=None):
        return {
            "flow_unit_id": f"game.chapter.{idx:02d}",
            "title": f"Chapter {idx}",
            "unit_type": "chapter",
            "project_type": "game",
            "lifecycle_mode": "dynamic-flow-gate",
            "current_stage": stage,
            "current_subphase": "backlog" if lane == "backlog" else lane,
            "gate_lane": lane,
            "gate_references": ["G5"] if lane == "backlog" else ["G6", "G7"],
            "allowed_next_transitions": ["classic-G5"],
            "dependencies": deps or [],
            "blockers": [],
            "evidence_refs": ["EVD-001"],
            "loop_state": {
                "active_loop": False,
                "loop_count": 0,
                "last_loop_type": None,
            },
            "runtime_status_source": "hot-project-state",
            "gate_state": {"status": gate_status or lane},
        }

    def _runtime(self, mutate=None):
        units = [
            self._unit(1, "released", "operations", gate_status="released"),
            self._unit(2, "testing", "testing", deps=["game.chapter.01"], gate_status="testing"),
            self._unit(3, "development", "development", deps=["game.chapter.02"], gate_status="in-progress"),
        ]
        for idx in range(4, 11):
            units.append(self._unit(idx, "backlog", "architecture", deps=[f"game.chapter.{idx - 1:02d}"], gate_status="backlog"))
        data = {
            "schema_version": "1.0",
            "workflow_model": "dynamic-flow-gate",
            "default_lifecycle_mode": "classic-phase-gate",
            "runtime_scope": "runtime-visibility-only",
            "runtime_status_source": "hot-project-state",
            "declarative_gate_engine": False,
            "project_migration": False,
            "active_lanes": {
                "released": ["game.chapter.01"],
                "testing": ["game.chapter.02"],
                "development": ["game.chapter.03"],
                "backlog": [f"game.chapter.{idx:02d}" for idx in range(4, 11)],
            },
            "blocked_downstream_units": [],
            "rollup_status": "chapter 1 released; chapter 2 testing; chapter 3 development; chapter 4-10 backlog",
            "flow_units": units,
            "no_overclaim_boundary": [
                "Flow-unit runtime is runtime visibility only.",
                "Flow-unit runtime does not activate declarative gate engine.",
                "Flow-unit runtime does not migrate projects.",
                "Classic G1-G11 remains compatible.",
                "Flow-unit runtime does not close RISK-036.",
                "Flow-unit runtime does not close RISK-037.",
                "Flow-unit runtime does not claim 1.0.0 production-ready.",
            ],
        }
        if mutate:
            mutate(data)
        return data

    def _write_target(self, root, *, runtime=True, evidence=True, plan_extra="", evidence_text=None):
        gov = root / ".governance"
        gov.mkdir(parents=True, exist_ok=True)
        (gov / "plan-tracker.md").write_text(
            "\n".join([
                "# Plan",
                "## 项目配置",
                "- workflow_model: classic-phase-gate",
                "## Gate 状态跟踪",
                "| Gate | 阶段转换 | 状态 |",
                "| --- | --- | --- |",
                "| G11 | next | passed |",
                plan_extra,
            ]),
            encoding="utf-8",
        )
        if evidence:
            (gov / "evidence-log.md").write_text(
                evidence_text or "| EVD-001 | FIX-139 | preview evidence |",
                encoding="utf-8",
            )
        if runtime:
            (gov / "flow-unit-runtime.json").write_text(
                json.dumps(self._runtime(), indent=2),
                encoding="utf-8",
            )

    def test_python_game_chapter_fixture_preview(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_target(root)

            preview = vw.build_dynamic_lifecycle_migration_preview(root)

        self.assertEqual(preview["status"], "READY_FOR_REVIEW")
        self.assertTrue(preview["dry_run"])
        self.assertEqual(preview["workflow_model"]["target"], "dynamic-flow-gate")
        self.assertEqual(preview["workflow_model"]["active_default_remains"], "classic-phase-gate")
        self.assertEqual(preview["flow_units"]["count"], 10)
        self.assertEqual(preview["flow_units"]["active_lanes"]["released"], ["game.chapter.01"])
        self.assertEqual(preview["flow_units"]["active_lanes"]["testing"], ["game.chapter.02"])
        self.assertEqual(preview["flow_units"]["active_lanes"]["development"], ["game.chapter.03"])
        self.assertEqual(preview["flow_units"]["active_lanes"]["backlog"], [f"game.chapter.{idx:02d}" for idx in range(4, 11)])
        self.assertEqual(preview["blocked_checks"], [])

    def test_classic_only_valid_project_uses_registry_example_preview(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_target(root, runtime=False)

            preview = vw.build_dynamic_lifecycle_migration_preview(root)

        self.assertEqual(preview["status"], "READY_FOR_REVIEW")
        self.assertEqual(preview["workflow_model"]["current"], "classic-phase-gate")
        self.assertEqual(preview["flow_units"]["source"], "lifecycle-registry example python_game_10_chapters")
        self.assertEqual(preview["flow_units"]["count"], 10)
        self.assertTrue(preview["evidence_preservation"]["plan_tracker"]["preserved"])
        self.assertTrue(preview["evidence_preservation"]["evidence_log"]["preserved"])

    def test_history_mentions_dynamic_but_explicit_classic_keeps_current_classic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_target(
                root,
                plan_extra="\n".join([
                    "0.55.0 Dynamic Lifecycle + Flow-Gate migration/external validation 规划已入账。",
                    "- workflow_model: classic-phase-gate",
                    "- history mentions dynamic-flow-gate but it is only planning text",
                ]),
            )

            preview = vw.build_dynamic_lifecycle_migration_preview(root)

        self.assertEqual(preview["workflow_model"]["current"], "classic-phase-gate")
        self.assertNotEqual(preview["workflow_model"]["current"], "dynamic-flow-gate")

    def test_same_explicit_model_line_dynamic_opt_in_keeps_current_classic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_target(root)
            plan_path = root / ".governance/plan-tracker.md"
            plan_text = plan_path.read_text(encoding="utf-8")
            plan_path.write_text(
                plan_text.replace(
                    "- workflow_model: classic-phase-gate",
                    "- workflow_model: classic-phase-gate; dynamic-flow-gate is opt-in",
                ),
                encoding="utf-8",
            )

            preview = vw.build_dynamic_lifecycle_migration_preview(root)

        self.assertEqual(preview["workflow_model"]["current"], "classic-phase-gate")
        self.assertNotEqual(preview["workflow_model"]["current"], "dynamic-flow-gate")

    def test_gate_status_tracking_without_explicit_dynamic_keeps_current_classic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_target(
                root,
                plan_extra="\n".join([
                    "0.55.0 Dynamic Lifecycle + Flow-Gate migration/external validation 规划已入账。",
                    "Gate 状态跟踪: G11 passed; classic-phase-gate remains active/default.",
                ]),
            )

            preview = vw.build_dynamic_lifecycle_migration_preview(root)

        self.assertEqual(preview["workflow_model"]["current"], "classic-phase-gate")
        self.assertNotEqual(preview["workflow_model"]["current"], "dynamic-flow-gate")

    def test_missing_evidence_log_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_target(root, evidence=False)

            preview = vw.build_dynamic_lifecycle_migration_preview(root)
            issues = vw.check_dynamic_lifecycle_migration_preview(root)

        self.assertEqual(preview["status"], "BLOCKED")
        self.assertTrue(any("missing .governance/evidence-log.md" in issue for issue in preview["blocked_checks"]))
        self.assertTrue(any("missing .governance/evidence-log.md" in issue for issue in issues))

    def test_dry_run_command_does_not_write_target(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_target(root)
            before = {
                str(path.relative_to(root)): (path.stat().st_mtime_ns, path.read_bytes())
                for path in root.rglob("*")
                if path.is_file()
            }
            args = argparse.Namespace(target=str(root), dry_run=True, apply=False, fail_on_issues=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                vw.cmd_dynamic_lifecycle_migration(args)
            after = {
                str(path.relative_to(root)): (path.stat().st_mtime_ns, path.read_bytes())
                for path in root.rglob("*")
                if path.is_file()
            }

        output = json.loads(buf.getvalue())
        self.assertEqual(output["status"], "READY_FOR_REVIEW")
        self.assertEqual(before, after)
        self.assertEqual(output["write_operations"], [])

    def test_missing_dry_run_flag_exits_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_target(root)
            args = argparse.Namespace(target=str(root), dry_run=False, apply=False, fail_on_issues=True)
            buf = io.StringIO()

            with redirect_stdout(buf), self.assertRaises(SystemExit) as ctx:
                vw.cmd_dynamic_lifecycle_migration(args)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("requires explicit --dry-run", buf.getvalue())

    def test_apply_flag_remains_blocked_even_with_dry_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_target(root)
            args = argparse.Namespace(target=str(root), dry_run=True, apply=True, fail_on_issues=True)
            buf = io.StringIO()

            with redirect_stdout(buf), self.assertRaises(SystemExit) as ctx:
                vw.cmd_dynamic_lifecycle_migration(args)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("--apply is blocked", buf.getvalue())

    def test_dynamic_default_overclaim_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_target(root, plan_extra="dynamic-flow-gate is now default")

            issues = vw.check_dynamic_lifecycle_migration_preview(root)

        self.assertTrue(any("dynamic-flow-gate default" in issue for issue in issues))

    def test_migration_specific_no_overclaim_blocks_validation_approval_and_lifecycle_pass(self):
        cases = [
            ("external validation full PASS", "external validation full PASS"),
            ("official approval", "official approval"),
            ("marketplace approval", "marketplace approval"),
            ("Codex Desktop lifecycle PASS", "Codex Desktop lifecycle PASS"),
        ]
        for label, phrase in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    self._write_target(root, plan_extra=phrase)

                    issues = vw.check_dynamic_lifecycle_migration_preview(root)

                self.assertTrue(
                    any(label in issue for issue in issues),
                    f"missing migration no-overclaim issue for {label}: {issues}",
                )

    def test_mixed_clause_positive_claim_is_blocked_in_plan_and_evidence(self):
        cases = [
            (
                "plan-tracker",
                {"plan_extra": "No official approval; external validation full PASS"},
            ),
            (
                "evidence-log",
                {"evidence_text": "| EVD-001 | FIX-139 | No official approval; external validation full PASS |"},
            ),
        ]
        for label, kwargs in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    self._write_target(root, **kwargs)

                    preview = vw.build_dynamic_lifecycle_migration_preview(root)
                    issues = vw.check_dynamic_lifecycle_migration_preview(root)

                self.assertEqual(preview["status"], "BLOCKED")
                self.assertTrue(
                    any("external validation full PASS" in issue for issue in preview["blocked_checks"]),
                    f"missing blocked preview issue for mixed clause {label}: {preview['blocked_checks']}",
                )
                self.assertTrue(
                    any("external validation full PASS" in issue for issue in issues),
                    f"missing validation issue for mixed clause {label}: {issues}",
                )

    def test_realistic_conservative_boundary_wording_is_not_blocked(self):
        cases = [
            (
                "plan-tracker",
                {
                    "plan_extra": "\n".join([
                        "仍需 external validation full PASS、官方提交结果/批准证据、Codex Desktop lifecycle PASS 或明确保守处置，以及 RISK-036/RISK-037 关闭后再发布正式标签。",
                        "该事项不声明 official approval、marketplace approval、external validation full PASS、Codex Desktop lifecycle PASS 或 1.0.0 readiness。",
                    ]),
                },
            ),
            (
                "evidence-log",
                {
                    "evidence_text": "\n".join([
                        "| EVD-001 | FIX-139 | 仍需 external validation full PASS、官方提交结果/批准证据、Codex Desktop lifecycle PASS 或明确保守处置。 |",
                        "| EVD-002 | FIX-139 | 不声明 official approval、marketplace approval、external validation full PASS、Codex Desktop lifecycle PASS 或 1.0.0 readiness。 |",
                    ]),
                },
            ),
        ]
        for label, kwargs in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    self._write_target(root, **kwargs)

                    preview = vw.build_dynamic_lifecycle_migration_preview(root)
                    issues = vw.check_dynamic_lifecycle_migration_preview(root)

                self.assertEqual(preview["status"], "READY_FOR_REVIEW")
                self.assertEqual(issues, [])

    def test_mixed_clause_negation_does_not_protect_followup_overclaim(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_target(root, plan_extra="No official approval; external validation full PASS")

            preview = vw.build_dynamic_lifecycle_migration_preview(root)
            issues = vw.check_dynamic_lifecycle_migration_preview(root)

        self.assertEqual(preview["status"], "BLOCKED")
        self.assertTrue(any("external validation full PASS" in issue for issue in preview["blocked_checks"]))
        self.assertTrue(any("external validation full PASS" in issue for issue in issues))

    def test_negation_does_not_protect_independent_followup_claim(self):
        cases = [
            (
                "plan-tracker",
                {"plan_extra": "No official approval; external validation full PASS"},
            ),
            (
                "evidence-log",
                {"evidence_text": "| EVD-001 | FIX-139 | No official approval; external validation full PASS |"},
            ),
        ]
        for label, kwargs in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    self._write_target(root, **kwargs)

                    issues = vw.check_dynamic_lifecycle_migration_preview(root)

                self.assertTrue(
                    any("external validation full PASS" in issue for issue in issues),
                    f"mixed clause follow-up claim should be blocked for {label}: {issues}",
                )

    def test_current_root_docs_are_readable_for_migration_preview(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_target(root)
            registry_src = vw.ROOT / "skills/software-project-governance/core/lifecycle-registry.json"
            registry_dst = root / "skills/software-project-governance/core/lifecycle-registry.json"
            registry_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(registry_src, registry_dst)
            guide_src = vw.ROOT / "docs/migration/dynamic-flow-gate-migration-0.55.0.md"
            guide_dst = root / "docs/migration/dynamic-flow-gate-migration-0.55.0.md"
            guide_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(guide_src, guide_dst)

            with patch.object(vw, "ROOT", root), \
                 patch.object(vw, "LIFECYCLE_REGISTRY_PATH", registry_dst):
                preview = vw.build_dynamic_lifecycle_migration_preview(root)
                issues = vw.check_dynamic_lifecycle_migration_preview(root)

        self.assertEqual(preview["status"], "READY_FOR_REVIEW")
        self.assertEqual(issues, [])

    def test_migration_preview_allows_review_and_fail_closed_history_language(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_target(
                root,
                plan_extra="\n".join([
                    "review confirmed blocked/not_supported Desktop lifecycle matrix and no-overclaim guard.",
                    "Code Reviewer approved the fail-closed example and variant regressions.",
                ]),
                evidence_text="\n".join([
                    "| EVD-001 | FIX-139 | review confirmed blocked/not_supported Desktop lifecycle matrix and no-overclaim guard. |",
                    "| EVD-002 | FIX-139 | Code Reviewer approved the fail-closed example and variant regressions. |",
                ]),
            )

            preview = vw.build_dynamic_lifecycle_migration_preview(root)
            issues = vw.check_dynamic_lifecycle_migration_preview(root)

        self.assertEqual(preview["status"], "READY_FOR_REVIEW")
        self.assertEqual(issues, [])

    def test_migration_preview_allows_review_documentation_hits_in_root_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_target(
                root,
                plan_extra="review confirms blocked marketplace approval wording is only historical evidence.",
                evidence_text="| EVD-001 | FIX-139 | review confirms blocked marketplace approval wording is only historical evidence. |",
            )

            preview = vw.build_dynamic_lifecycle_migration_preview(root)
            issues = vw.check_dynamic_lifecycle_migration_preview(root)

        self.assertEqual(preview["status"], "READY_FOR_REVIEW")
        self.assertEqual(issues, [])

    def test_migration_preview_command_requires_explicit_dry_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_target(root)
            args = argparse.Namespace(target=str(root), dry_run=False, apply=False, fail_on_issues=True)
            buf = io.StringIO()

            with redirect_stdout(buf), self.assertRaises(SystemExit) as ctx:
                vw.cmd_dynamic_lifecycle_migration(args)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("requires explicit --dry-run", buf.getvalue())

    def test_evidence_log_overclaims_block_migration_preview(self):
        cases = [
            ("external validation full PASS", "external validation full PASS"),
            ("official approval", "official approval"),
            ("marketplace approval", "marketplace approval"),
            ("Codex Desktop lifecycle PASS", "Codex Desktop lifecycle PASS"),
        ]
        for label, phrase in cases:
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    self._write_target(
                        root,
                        evidence_text=f"| EVD-001 | FIX-139 | {phrase} |",
                    )

                    preview = vw.build_dynamic_lifecycle_migration_preview(root)
                    issues = vw.check_dynamic_lifecycle_migration_preview(root)

                self.assertEqual(preview["status"], "BLOCKED")
                self.assertTrue(
                    any("evidence-log forbidden migration" in issue and label in issue for issue in preview["blocked_checks"]),
                    f"missing evidence-log blocked check for {label}: {preview['blocked_checks']}",
                )
                self.assertTrue(
                    any("evidence-log forbidden migration" in issue and label in issue for issue in issues),
                    f"missing evidence-log validation issue for {label}: {issues}",
                )

    def test_migration_specific_no_overclaim_allows_blocker_boundary_wording(self):
        blocker_line = (
            "当前结论仍为 1.0.0 不可发布：RISK-036 继续打开，"
            "两个真实外部项目 full PASS、Codex Desktop lifecycle PASS/保守处置、"
            "official approval 与 marketplace approval 仍不可用。"
        )

        issues = vw._dynamic_migration_forbidden_text_issues(blocker_line, "migration preview forbidden")

        self.assertEqual(issues, [])

    def test_evidence_log_scoped_negation_and_blocker_wording_do_not_block_preview(self):
        evidence_text = (
            "| EVD-001 | FIX-139 | No external validation full PASS, no official approval, "
            "no marketplace approval, and no Codex Desktop lifecycle PASS. |\n"
            "| EVD-002 | FIX-139 | 当前结论仍为 1.0.0 不可发布：两个真实外部项目 full PASS、"
            "Codex Desktop lifecycle PASS/保守处置、official approval 与 marketplace approval 仍不可用。 |\n"
            "| EVD-003 | FIX-139 | validator 阻断 official approval、marketplace approval 与 "
            "1.0.0 production-ready 等过度声明。 |\n"
            "| EVD-004 | FIX-139 | 未发现 official approval、marketplace approval、"
            "1.0.0 production-ready、RISK-036 resolved/closed 等肯定式过度声明。 |"
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_target(root, evidence_text=evidence_text)

            preview = vw.build_dynamic_lifecycle_migration_preview(root)
            issues = vw.check_dynamic_lifecycle_migration_preview(root)

        self.assertEqual(preview["status"], "READY_FOR_REVIEW")
        self.assertFalse(any("evidence-log forbidden migration" in issue for issue in preview["blocked_checks"]))
        self.assertFalse(any("evidence-log forbidden migration" in issue for issue in issues))


class CapabilitySelectionTests(unittest.TestCase):
    """FIX-117: restricted host capability selection must degrade honestly."""

    def _write_project(self, root, mutate_docs=None, runtime_blocked=True):
        verify_path = root / "skills/software-project-governance/infra/verify_workflow.py"
        verify_path.parent.mkdir(parents=True, exist_ok=True)
        verify_path.write_text("def main():\n    pass\n", encoding="utf-8")

        skill_path = root / "skills/software-project-governance/SKILL.md"
        skill_path.write_text("---\nname: software-project-governance\n---\n", encoding="utf-8")

        tools_path = root / "skills/software-project-governance/infra/TOOLS.md"
        tools_text = "\n".join([
            "# Tools",
            "TOOL-033",
            "check-host-capability-context",
            "FIX-117",
            "benchmark/diagnostic",
            "not external execution",
            "not Desktop marketplace E2E PASS",
            "no network",
            "no plugin install",
            "no MCP",
            "no browser",
            "no sub-agent",
            "local skill only",
            "restricted benchmark scenario: Codex CLI blocked",
            "restricted benchmark scenario: Gemini auth blocked",
        ])
        tools_path.write_text(tools_text, encoding="utf-8")

        req_path = root / "docs/requirements/capability-discovery-orchestration-0.45.0.md"
        req_path.parent.mkdir(parents=True, exist_ok=True)
        req_text = "\n".join([
            "# Capability Discovery",
            "FIX-117",
            "TOOL-033",
            "check-host-capability-context",
            "benchmark/diagnostic",
            "not external execution",
            "not Desktop marketplace E2E PASS",
            "no network",
            "no plugin install",
            "no MCP",
            "no browser",
            "no sub-agent",
            "local skill only",
            "restricted benchmark scenario: Codex CLI blocked",
            "restricted benchmark scenario: Gemini auth blocked",
        ])
        if mutate_docs:
            req_text, tools_text = mutate_docs(req_text, tools_text)
            req_path.write_text(req_text, encoding="utf-8")
            tools_path.write_text(tools_text, encoding="utf-8")
        else:
            req_path.write_text(req_text, encoding="utf-8")

        if runtime_blocked:
            runtime_path = root / "docs/requirements/runtime-readiness-matrix-0.43.0.md"
            runtime_path.write_text(
                "| codex | BLOCKED | Codex CLI blocked timeout |\n"
                "| gemini | BLOCKED | Gemini auth blocked missing/401 |\n",
                encoding="utf-8",
            )

        registry_path = root / "skills/software-project-governance/core/capability-registry.json"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry = {
            "capabilities": [
                {"capability_id": "fallback.local-diagnostic-readonly", "kind": "fallback"},
                {"capability_id": "software-project-governance.skill-entry", "kind": "skill"},
                {"capability_id": "verify-workflow.capability-context-tool", "kind": "tool"},
                {"capability_id": "host.mcp.connectors", "kind": "mcp"},
                {"capability_id": "browser.in-app-or-chrome-control", "kind": "browser"},
                {"capability_id": "agent-team.governance-developer", "kind": "sub_agent"},
                {"capability_id": "codex.desktop.plugin-manifest", "kind": "plugin"},
            ]
        }
        registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    def test_current_repository_host_capability_context_passes(self):
        self.assertEqual(vw.check_host_capability_context(vw.ROOT), [])

    def test_restricted_fixture_covers_required_degradation_scenarios(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_project(root)

            context = vw.discover_host_capability_context(root)
            issues = vw.check_host_capability_context(root)

        self.assertEqual([], issues)
        scenarios = {item["scenario_id"]: item for item in context["restricted_scenarios"]}
        for scenario_id in vw.HOST_CAPABILITY_CONTEXT_SCENARIOS:
            self.assertIn(scenario_id, scenarios)
        self.assertEqual("DEGRADED", scenarios["no_network"]["status"])
        self.assertEqual("DEGRADED", scenarios["no_plugin_install"]["status"])
        self.assertEqual("NOT_SUPPORTED", scenarios["no_mcp"]["status"])
        self.assertEqual("NOT_SUPPORTED", scenarios["no_browser"]["status"])
        self.assertEqual("DEGRADED", scenarios["no_sub_agent"]["status"])
        self.assertEqual("PASS", scenarios["local_skill_only"]["status"])
        self.assertEqual("BLOCKED", scenarios["codex_cli_blocked"]["status"])
        self.assertEqual("BLOCKED", scenarios["gemini_auth_blocked"]["status"])
        self.assertTrue(all("check-host-capability-context" in item["validation_command"] for item in scenarios.values()))
        self.assertIn("not external execution", " ".join(context["no_overclaim_boundary"]))

    def test_command_accepts_restricted_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_project(root)
            args = argparse.Namespace(fixture=str(root), fail_on_issues=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                vw.cmd_check_host_capability_context(args)

        output = buf.getvalue()
        self.assertIn("Host Capability Context Check", output)
        self.assertIn("no_network: DEGRADED", output)
        self.assertIn("codex_cli_blocked: BLOCKED", output)
        self.assertIn("gemini_auth_blocked: BLOCKED", output)
        self.assertIn("Result: PASSED", output)

    def test_restricted_blocked_scenarios_no_longer_depend_on_live_runtime_matrix(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_project(root, runtime_blocked=False)

            context = vw.discover_host_capability_context(root)
            issues = vw.check_host_capability_context(root)

        self.assertEqual([], issues)
        self.assertIn(
            "restricted benchmark scenario: Codex CLI blocked",
            context["source_facts"],
        )
        self.assertIn(
            "restricted benchmark scenario: Gemini auth blocked",
            context["source_facts"],
        )

    def test_rejects_blocked_capability_declared_runtime_pass(self):
        broken_context = {
            "scenario": "restricted-environment-capability-selection",
            "host_id": "fixture",
            "benchmark_kind": "benchmark/diagnostic fixture; not external execution",
            "source_facts": ["restricted benchmark scenario: Codex CLI blocked", "restricted benchmark scenario: Gemini auth blocked"],
            "restricted_scenarios": [{
                "scenario_id": "codex_cli_blocked",
                "constraint": "Codex CLI blocked",
                "preferred_capability": "codex.cli.headless-runtime",
                "selected_capability": "codex.cli.headless-runtime",
                "status": "PASS",
                "degradation_boundary": "blocked capability runtime PASS",
                "validation_command": "python skills/software-project-governance/infra/verify_workflow.py check-host-capability-context --fail-on-issues",
                "source_facts": ["Codex CLI blocked"],
                "no_overclaim_boundary": ["runtime PASS"],
            }],
            "side_effect_boundary": "read-only no network plugin install MCP browser sub-agent",
            "validation_command": "python skills/software-project-governance/infra/verify_workflow.py check-host-capability-context --fail-on-issues",
            "review_requirement": "requires independent Code Reviewer approval",
            "no_overclaim_boundary": [
                "benchmark/diagnostic",
                "not external execution",
                "not Desktop marketplace E2E PASS",
                "blocked capability is not runtime PASS",
                "catalog fact is not runtime PASS",
                "Do not claim automatic best-tool selection.",
                "Do not claim universal plugin availability.",
            ],
        }
        with patch.object(vw, "discover_host_capability_context", return_value=broken_context):
            issues = vw.check_host_capability_context(vw.ROOT)

        self.assertTrue(any("restricted scenario must be blocked/degraded" in issue for issue in issues))
        self.assertTrue(any("forbidden overclaim `blocked capability runtime pass`" in issue for issue in issues))

    def test_rejects_missing_degradation_boundary(self):
        context = vw.discover_host_capability_context(vw.ROOT)
        context["restricted_scenarios"] = [dict(item) for item in context["restricted_scenarios"]]
        del context["restricted_scenarios"][0]["degradation_boundary"]
        with patch.object(vw, "discover_host_capability_context", return_value=context):
            issues = vw.check_host_capability_context(vw.ROOT)

        self.assertTrue(any("missing `degradation_boundary`" in issue for issue in issues))

    def test_rejects_missing_validation_command(self):
        context = vw.discover_host_capability_context(vw.ROOT)
        context["restricted_scenarios"] = [dict(item) for item in context["restricted_scenarios"]]
        context["restricted_scenarios"][0]["validation_command"] = ""
        context["validation_command"] = ""
        with patch.object(vw, "discover_host_capability_context", return_value=context):
            issues = vw.check_host_capability_context(vw.ROOT)

        self.assertTrue(any("validation_command must name check-host-capability-context" in issue for issue in issues))

    def test_rejects_automatic_best_tool_selection_claim(self):
        context = vw.discover_host_capability_context(vw.ROOT)
        context["restricted_scenarios"] = [dict(item) for item in context["restricted_scenarios"]]
        context["restricted_scenarios"][0]["degradation_boundary"] = "automatically selects the best tool"
        with patch.object(vw, "discover_host_capability_context", return_value=context):
            issues = vw.check_host_capability_context(vw.ROOT)

        self.assertTrue(any("forbidden overclaim `automatically selects the best tool`" in issue for issue in issues))

    def test_rejects_universal_plugin_availability_claim(self):
        context = vw.discover_host_capability_context(vw.ROOT)
        context["restricted_scenarios"] = [dict(item) for item in context["restricted_scenarios"]]
        context["restricted_scenarios"][0]["source_facts"] = ["universal plugin availability"]
        with patch.object(vw, "discover_host_capability_context", return_value=context):
            issues = vw.check_host_capability_context(vw.ROOT)

        self.assertTrue(any("forbidden overclaim `universal plugin availability`" in issue for issue in issues))

    def test_rejects_fix117_forbidden_positive_overclaims(self):
        context = vw.discover_host_capability_context(vw.ROOT)
        context["restricted_scenarios"] = [dict(item) for item in context["restricted_scenarios"]]
        context["restricted_scenarios"][0]["source_facts"] = [
            "Codex Desktop marketplace-management E2E PASS",
            "official approval granted",
            "officially approved",
            "marketplace approval granted",
            "marketplace approved",
            "successful external execution",
            "1.0.0 production-ready",
        ]
        with patch.object(vw, "discover_host_capability_context", return_value=context):
            issues = vw.check_host_capability_context(vw.ROOT)

        expected = [
            "codex desktop marketplace-management e2e pass",
            "official approval granted",
            "officially approved",
            "marketplace approval granted",
            "marketplace approved",
            "successful external execution",
            "external execution",
            "1.0.0 production-ready",
        ]
        for phrase in expected:
            self.assertTrue(
                any(f"forbidden overclaim `{phrase}`" in issue for issue in issues),
                f"missing overclaim issue for {phrase}: {issues}",
            )

    def test_allows_negated_fix117_boundary_phrasing(self):
        context = vw.discover_host_capability_context(vw.ROOT)
        context["restricted_scenarios"] = [dict(item) for item in context["restricted_scenarios"]]
        context["restricted_scenarios"][0]["source_facts"] = [
            "not external execution",
            "not Desktop marketplace E2E PASS",
        ]
        with patch.object(vw, "discover_host_capability_context", return_value=context):
            issues = vw.check_host_capability_context(vw.ROOT)

        self.assertFalse(any("forbidden overclaim `external execution`" in issue for issue in issues))
        self.assertFalse(any("forbidden overclaim `desktop marketplace e2e pass`" in issue for issue in issues))


class ReleaseReadinessCommandTests(unittest.TestCase):
    """FIX-072: stage-release check-release must be backed by a real CLI command."""

    def _clean_release_patches(self):
        return [
            patch.object(vw, "check_version_consistency", return_value=[]),
            patch.object(vw, "check_release_readiness_fact_source", return_value=[]),
            patch.object(vw, "check_hot_fact_source_consistency", return_value=[]),
            patch.object(vw, "check_runtime_readiness_matrix", return_value=[]),
            patch.object(vw, "check_first_session_measurement", return_value=[]),
            patch.object(vw, "check_governance_pack_status", return_value=[]),
            patch.object(vw, "check_agent_adapter_contract", return_value=[]),
            patch.object(vw, "check_projection_sync", return_value={
                "pass": True,
                "issues": [],
                "mirrors_checked": 3,
                "mirrors_discovered": 3,
                "mirrors_skipped_untracked": 0,
                "source_version": "0.35.0",
            }),
            patch.object(vw, "check_cross_references", return_value={
                "dangling": [],
                "deprecated": [],
                "cycles": [],
                "total_files_scanned": 1,
                "total_refs": 0,
            }),
            patch.object(vw, "check_archive_integrity", return_value={
                "pass": True,
                "issues": [],
                "hot_tasks": 0,
                "total_archived_tasks": 0,
                "index_entries": 0,
                "total_expected": 0,
                "pending_archive_tasks": 0,
            }),
            patch.object(vw, "check_release_docs_coverage", return_value=[]),
        ]

    def _apply_release_patches(self, patches):
        stack = ExitStack()
        mocks = [stack.enter_context(patch_item) for patch_item in patches]
        return stack, mocks

    def _write_one_dot_zero_fact_sources(
        self,
        root,
        *,
        risk_status="打开",
        external_full_pass=False,
        official_approved=False,
        desktop_disposition=True,
        risk_log_text=None,
        external_text=None,
        desktop_text=None,
    ):
        root = Path(root)
        governance_dir = root / ".governance"
        governance_dir.mkdir(parents=True)
        (governance_dir / "risk-log.md").write_text(
            risk_log_text
            if risk_log_text is not None
            else (
                "| 编号 | 日期 | 风险/阻塞描述 | 所属阶段 | 触发条件 | 影响 | 严重级别 | Owner | 当前状态 | 缓解动作 |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
                f"| RISK-036 | 2026-06-09 | adoption risk | 维护 | trigger | impact | 高 | Coordinator | {risk_status} | mitigation |\n"
            ),
            encoding="utf-8",
        )

        requirements_dir = root / "docs/requirements"
        requirements_dir.mkdir(parents=True)
        external_text = external_text if external_text is not None else (
            "# External Project Validation Report - 1.0.0\n"
            "External project validation full PASS. Two external project validations full PASS.\n"
            if external_full_pass
            else "# External Project Validation Report - 0.49.0\n"
            "VAL-001 is not a full PASS. No external project validation PASS.\n"
        )
        (requirements_dir / "external-project-validation-0.49.0.md").write_text(
            external_text,
            encoding="utf-8",
        )

        official_text = (
            "# Official Submission Result - 1.0.0\n"
            "Official submission result: APPROVED. Official approval granted.\n"
            if official_approved
            else "# Official Submission Final Bundle Review - 0.49.0\n"
            "This review does not report any official response. No official approval. "
            "Official result is NOT_AVAILABLE.\n"
        )
        (requirements_dir / "official-submission-final-bundle-review-0.49.0.md").write_text(
            official_text,
            encoding="utf-8",
        )

        desktop_text = desktop_text if desktop_text is not None else (
            "# Codex Desktop Marketplace Lifecycle Review - 0.49.0\n"
            "VAL-002 is not a Codex Desktop marketplace-management E2E PASS. "
            "This report keeps RISK-036 open and keeps 1.0.0 blocked; "
            "it must carry forward the Desktop lifecycle blocker unless direct evidence exists.\n"
            if desktop_disposition
            else "# Codex Desktop Marketplace Lifecycle Review - 0.49.0\n"
            "CLI marketplace source sync only.\n"
        )
        (requirements_dir / "codex-desktop-marketplace-lifecycle-0.49.0.md").write_text(
            desktop_text,
            encoding="utf-8",
        )

    def test_check_release_readiness_passes_when_all_underlying_checks_pass(self):
        with tempfile.TemporaryDirectory() as td:
            changelog = Path(td) / "CHANGELOG.md"
            changelog.write_text("# Changelog\n\n## [0.35.0]\n", encoding="utf-8")
            patches = self._clean_release_patches()
            stack, mocks = self._apply_release_patches(patches)
            with stack:
                result = vw.check_release_readiness(
                    version="0.35.0",
                    require_changelog=True,
                    run_runtime_adapters=True,
                    changelog_path=changelog,
                )
            self.assertTrue(result["pass"])
            adapter_mock = mocks[6]
            adapter_mock.assert_called_once_with(run_runtime=True)
            self.assertIn("governance_pack_status", result["details"])
            self.assertIn("pack enabled", result["details"]["governance_pack_status"]["boundary"])
            self.assertFalse(result["details"]["one_dot_zero_blockers"]["required"])

    def test_check_release_readiness_requires_changelog_version_when_requested(self):
        with tempfile.TemporaryDirectory() as td:
            changelog = Path(td) / "CHANGELOG.md"
            changelog.write_text("# Changelog\n\n## [0.34.0]\n", encoding="utf-8")
            patches = self._clean_release_patches()
            stack, _mocks = self._apply_release_patches(patches)
            with stack:
                result = vw.check_release_readiness(
                    version="0.35.0",
                    require_changelog=True,
                    changelog_path=changelog,
                )
            self.assertFalse(result["pass"])
            self.assertTrue(any("missing changelog entry ## [0.35.0]" in issue for issue in result["issues"]))

    def test_check_release_readiness_fails_one_dot_zero_on_blockers_even_when_release_docs_pass(self):
        with tempfile.TemporaryDirectory() as td:
            changelog = Path(td) / "CHANGELOG.md"
            changelog.write_text("# Changelog\n\n## [1.0.0]\n", encoding="utf-8")
            patches = self._clean_release_patches()
            patches.append(patch.object(
                vw,
                "check_one_dot_zero_release_blockers",
                return_value=[
                    "RISK-036 is open; 1.0.0 release is blocked until the risk is closed",
                    "external validation full PASS is missing",
                    "official submission result or approval evidence is missing",
                ],
            ))
            stack, _mocks = self._apply_release_patches(patches)
            with stack:
                result = vw.check_release_readiness(
                    version="1.0.0",
                    require_changelog=True,
                    changelog_path=changelog,
                )

        self.assertFalse(result["pass"])
        self.assertTrue(result["details"]["release_docs"]["pass"])
        self.assertFalse(result["details"]["one_dot_zero_blockers"]["pass"])
        self.assertTrue(result["details"]["one_dot_zero_blockers"]["required"])
        self.assertTrue(any("1.0.0 blocker: RISK-036 is open" in issue for issue in result["issues"]))

    def test_check_release_readiness_does_not_apply_one_dot_zero_blockers_to_patch_releases(self):
        for version in ("0.50.0", "0.50.1"):
            with self.subTest(version=version):
                with tempfile.TemporaryDirectory() as td:
                    changelog = Path(td) / "CHANGELOG.md"
                    changelog.write_text(f"# Changelog\n\n## [{version}]\n", encoding="utf-8")
                    patches = self._clean_release_patches()
                    stack, _mocks = self._apply_release_patches(patches)
                    with stack:
                        result = vw.check_release_readiness(
                            version=version,
                            require_changelog=True,
                            changelog_path=changelog,
                        )

                self.assertTrue(result["pass"])
                self.assertFalse(result["details"]["one_dot_zero_blockers"]["required"])
                self.assertTrue(result["details"]["one_dot_zero_blockers"]["pass"])

    def test_one_dot_zero_blocker_helper_reports_current_conservative_blockers(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_one_dot_zero_fact_sources(root)
            issues = vw.check_one_dot_zero_release_blockers(root=root)

        self.assertTrue(any("RISK-036 is not explicitly closed" in issue for issue in issues))
        self.assertTrue(any("external validation full PASS is missing" in issue for issue in issues))
        self.assertTrue(any("official submission result or approval evidence is missing" in issue for issue in issues))
        self.assertFalse(any("Codex Desktop lifecycle PASS or explicit conservative disposition" in issue for issue in issues))

    def test_one_dot_zero_external_validation_rejects_negated_full_pass_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_one_dot_zero_fact_sources(
                root,
                risk_status="已关闭",
                official_approved=True,
                desktop_disposition=True,
                external_text=(
                    "# External Project Validation Report - 1.0.0\n"
                    "No external project validation full PASS evidence is available.\n"
                ),
            )
            issues = vw.check_one_dot_zero_release_blockers(root=root)

        self.assertTrue(any("external validation full PASS" in issue for issue in issues))

    def test_one_dot_zero_desktop_lifecycle_rejects_missing_pass_without_disposition(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_one_dot_zero_fact_sources(
                root,
                risk_status="已关闭",
                external_full_pass=True,
                official_approved=True,
                desktop_disposition=False,
                desktop_text=(
                    "# Codex Desktop Marketplace Lifecycle Review - 1.0.0\n"
                    "Desktop lifecycle PASS is missing.\n"
                ),
            )
            issues = vw.check_one_dot_zero_release_blockers(root=root)

        self.assertTrue(any("Codex Desktop lifecycle PASS or explicit conservative disposition" in issue for issue in issues))

    def test_one_dot_zero_external_validation_rejects_structured_negative_pass_values(self):
        variants = (
            "External project validation full PASS: NO.\n",
            "External project validation full PASS = false.\n",
            "External project validation full PASS: fail.\n",
            "External project validation full PASS: failed.\n",
            "External project validation full PASS: blocked.\n",
            "External project validation full PASS: not_run.\n",
            "External project validation full PASS: missing.\n",
            "External project validation full PASS: unavailable.\n",
        )
        for external_line in variants:
            with self.subTest(external_line=external_line.strip()):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    self._write_one_dot_zero_fact_sources(
                        root,
                        risk_status="已关闭",
                        official_approved=True,
                        desktop_disposition=True,
                        external_text=(
                            "# External Project Validation Report - 1.0.0\n"
                            f"{external_line}"
                        ),
                    )
                    issues = vw.check_one_dot_zero_release_blockers(root=root)

                self.assertTrue(any("external validation full PASS" in issue for issue in issues))

    def test_one_dot_zero_desktop_lifecycle_rejects_structured_negative_pass_values(self):
        variants = (
            "Desktop lifecycle PASS: NO.\n",
            "Desktop lifecycle PASS = false.\n",
            "Desktop lifecycle PASS: fail.\n",
            "Desktop lifecycle PASS: failed.\n",
            "Desktop lifecycle PASS: blocked.\n",
            "Desktop lifecycle PASS: not_run.\n",
            "Desktop lifecycle PASS: missing.\n",
            "Desktop lifecycle PASS: unavailable.\n",
        )
        for desktop_line in variants:
            with self.subTest(desktop_line=desktop_line.strip()):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    self._write_one_dot_zero_fact_sources(
                        root,
                        risk_status="已关闭",
                        external_full_pass=True,
                        official_approved=True,
                        desktop_disposition=False,
                        desktop_text=(
                            "# Codex Desktop Marketplace Lifecycle Review - 1.0.0\n"
                            f"{desktop_line}"
                        ),
                    )
                    issues = vw.check_one_dot_zero_release_blockers(root=root)

                self.assertTrue(any("Codex Desktop lifecycle PASS or explicit conservative disposition" in issue for issue in issues))

    def test_one_dot_zero_risk_status_must_be_explicitly_closed(self):
        fixtures = {
            "missing_status_column": (
                "| 编号 | 当前状态 |\n"
                "| --- | --- |\n"
                "| RISK-036 | 打开 |\n"
            ),
            "unknown_status": (
                "| 编号 | 日期 | 风险/阻塞描述 | 所属阶段 | 触发条件 | 影响 | 严重级别 | Owner | 当前状态 | 缓解动作 |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| RISK-036 | 2026-06-09 | adoption risk | 维护 | trigger | impact | 高 | Coordinator | pending review | mitigation |\n"
            ),
            "blocking_status": (
                "| 编号 | 日期 | 风险/阻塞描述 | 所属阶段 | 触发条件 | 影响 | 严重级别 | Owner | 当前状态 | 缓解动作 |\n"
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
                "| RISK-036 | 2026-06-09 | adoption risk | 维护 | trigger | impact | 高 | Coordinator | blocking | mitigation |\n"
            ),
        }
        for name, risk_log_text in fixtures.items():
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    self._write_one_dot_zero_fact_sources(
                        root,
                        external_full_pass=True,
                        official_approved=True,
                        desktop_disposition=True,
                        risk_log_text=risk_log_text,
                    )
                    issues = vw.check_one_dot_zero_release_blockers(root=root)

                self.assertTrue(any("RISK-036 is not explicitly closed" in issue for issue in issues))

    def test_one_dot_zero_blocker_helper_accepts_satisfied_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_one_dot_zero_fact_sources(
                root,
                risk_status="已关闭",
                external_full_pass=True,
                official_approved=True,
                desktop_disposition=True,
            )
            issues = vw.check_one_dot_zero_release_blockers(root=root)

        self.assertEqual([], issues)

    def test_release_docs_coverage_requires_versioned_docs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_dir = root / "skills/software-project-governance/core"
            manifest_dir.mkdir(parents=True)
            (manifest_dir / "manifest.json").write_text(
                json.dumps({
                    "root_entries": {"files": [], "directories": []},
                    "product": {"entries": [], "glob_patterns": []},
                    "repo_only": {"entries": [], "glob_patterns": []},
                }),
                encoding="utf-8",
            )
            with patch.object(vw, "_git_files", return_value=set()):
                issues = vw.check_release_docs_coverage("0.44.1", root=root)

        self.assertTrue(any("release-checklist-0.44.1.md" in issue for issue in issues))
        self.assertTrue(any("feature-flags-0.44.1.md" in issue for issue in issues))
        self.assertTrue(any("rollback-plan-0.44.1.md" in issue for issue in issues))

    def test_release_docs_coverage_requires_tracked_and_boundary_docs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_dir = root / "skills/software-project-governance/core"
            manifest_dir.mkdir(parents=True)
            release_dir = root / "docs/release"
            release_dir.mkdir(parents=True)
            doc_names = [
                "release-checklist-0.44.1.md",
                "feature-flags-0.44.1.md",
                "rollback-plan-0.44.1.md",
            ]
            for doc_name in doc_names:
                (release_dir / doc_name).write_text(
                    "0.44.1\n"
                    "No official approval, marketplace approval, universal/full runtime support, "
                    "external first-session pilot success. RISK-036 remains open.\n",
                    encoding="utf-8",
                )
            (manifest_dir / "manifest.json").write_text(
                json.dumps({
                    "root_entries": {"files": [], "directories": []},
                    "product": {
                        "entries": [
                            {"path": f"docs/release/{doc_name}", "type": "file"}
                            for doc_name in doc_names
                        ],
                        "glob_patterns": [],
                    },
                    "repo_only": {"entries": [], "glob_patterns": []},
                }),
                encoding="utf-8",
            )
            with patch.object(vw, "_git_files", return_value=set()):
                issues = vw.check_release_docs_coverage("0.44.1", root=root)

        self.assertTrue(any("must be tracked by git" in issue for issue in issues))

    def test_release_docs_coverage_does_not_accept_untracked_other_candidates(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_dir = root / "skills/software-project-governance/core"
            manifest_dir.mkdir(parents=True)
            release_dir = root / "docs/release"
            release_dir.mkdir(parents=True)
            doc_names = [
                "release-checklist-0.44.1.md",
                "feature-flags-0.44.1.md",
                "rollback-plan-0.44.1.md",
            ]
            for doc_name in doc_names:
                (release_dir / doc_name).write_text(
                    "0.44.1\n"
                    "No official approval, marketplace approval, universal/full runtime support, "
                    "external first-session pilot success. RISK-036 remains open.\n",
                    encoding="utf-8",
                )
            (manifest_dir / "manifest.json").write_text(
                json.dumps({
                    "root_entries": {"files": [], "directories": []},
                    "product": {
                        "entries": [
                            {"path": f"docs/release/{doc_name}", "type": "file"}
                            for doc_name in doc_names
                        ],
                        "glob_patterns": [],
                    },
                    "repo_only": {"entries": [], "glob_patterns": []},
                }),
                encoding="utf-8",
            )

            def fake_git_files(args):
                self.assertNotIn("--others", args)
                return set()

            with patch.object(vw, "_git_files", side_effect=fake_git_files):
                issues = vw.check_release_docs_coverage("0.44.1", root=root)

        self.assertTrue(any("must be tracked by git" in issue for issue in issues))

    def test_release_docs_coverage_rejects_positive_overclaim_wording(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_dir = root / "skills/software-project-governance/core"
            manifest_dir.mkdir(parents=True)
            release_dir = root / "docs/release"
            release_dir.mkdir(parents=True)
            doc_names = [
                "release-checklist-0.44.1.md",
                "feature-flags-0.44.1.md",
                "rollback-plan-0.44.1.md",
            ]
            overclaim_lines = [
                "Official approval granted for 0.44.1.",
                "Marketplace approval approved for 0.44.1.",
                "Universal runtime support is verified and full runtime support is supported.",
                "Universal/full runtime support verified.",
                "Universal/full runtime support supported.",
                "Universal runtime support verified.",
                "Universal runtime support supported.",
                "Full runtime support verified.",
                "Full runtime support supported.",
                "External first-session pilot success passed.",
                "Codex Desktop marketplace-management E2E PASS.",
                "Automatic best-tool selection PASS.",
                "Automatic best-tool selection is passed.",
                "Automatic best-tool selection passed.",
                "Automatic best-tool selection is available.",
                "Automatic best-tool selection available.",
                "Automatic best-tool selection is verified.",
                "Automatic best-tool selection verified.",
                "Universal plugin/skill/tool availability PASS.",
                "Universal plugin/skill/tool availability is passed.",
                "Universal plugin/skill/tool availability passed.",
                "Universal plugin/skill/tool availability is available.",
                "Universal plugin/skill/tool availability available.",
                "Universal plugin/skill/tool availability is verified.",
                "Universal plugin/skill/tool availability verified.",
                "Catalog entry runtime PASS.",
                "Catalog entry runtime is passed.",
                "Catalog entry runtime passed.",
                "Catalog entry runtime is available.",
                "Catalog entry runtime available.",
                "Catalog entry runtime is verified.",
                "Catalog entry runtime verified.",
                "1.0.0 production-ready.",
                "RISK-036 closed.",
            ]
            for doc_name in doc_names:
                (release_dir / doc_name).write_text(
                    "0.44.1\n"
                    "No-overclaim boundary: no official approval, marketplace approval, "
                    "universal/full runtime support, external first-session pilot success. "
                    "RISK-036 remains open.\n"
                    + "\n".join(overclaim_lines)
                    + "\n",
                    encoding="utf-8",
                )
            (manifest_dir / "manifest.json").write_text(
                json.dumps({
                    "root_entries": {"files": [], "directories": []},
                    "product": {
                        "entries": [
                            {"path": f"docs/release/{doc_name}", "type": "file"}
                            for doc_name in doc_names
                        ],
                        "glob_patterns": [],
                    },
                    "repo_only": {"entries": [], "glob_patterns": []},
                }),
                encoding="utf-8",
            )
            tracked = {f"docs/release/{doc_name}" for doc_name in doc_names}
            with patch.object(vw, "_git_files", return_value=tracked):
                issues = vw.check_release_docs_coverage("0.44.1", root=root)

        for phrase in (
            "official approval granted",
            "marketplace approval approved",
            "universal runtime support is verified",
            "full runtime support is supported",
            "universal/full runtime support verified",
            "universal/full runtime support supported",
            "universal runtime support verified",
            "universal runtime support supported",
            "full runtime support verified",
            "full runtime support supported",
            "external first-session pilot success",
            "codex desktop marketplace-management e2e pass",
            "automatic best-tool selection pass",
            "automatic best-tool selection is passed",
            "automatic best-tool selection passed",
            "automatic best-tool selection is available",
            "automatic best-tool selection available",
            "automatic best-tool selection is verified",
            "automatic best-tool selection verified",
            "universal plugin/skill/tool availability pass",
            "universal plugin/skill/tool availability is passed",
            "universal plugin/skill/tool availability passed",
            "universal plugin/skill/tool availability is available",
            "universal plugin/skill/tool availability available",
            "universal plugin/skill/tool availability is verified",
            "universal plugin/skill/tool availability verified",
            "catalog entry runtime pass",
            "catalog entry runtime is passed",
            "catalog entry runtime passed",
            "catalog entry runtime is available",
            "catalog entry runtime available",
            "catalog entry runtime is verified",
            "catalog entry runtime verified",
            "1.0.0 production-ready",
            "risk-036 closed",
        ):
            self.assertTrue(
                any(f"forbidden release docs overclaim `{phrase}`" in issue for issue in issues),
                phrase,
            )

    def test_release_docs_coverage_rejects_positive_claim_with_unrelated_status_negation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_dir = root / "skills/software-project-governance/core"
            manifest_dir.mkdir(parents=True)
            release_dir = root / "docs/release"
            release_dir.mkdir(parents=True)
            doc_names = [
                "release-checklist-0.44.1.md",
                "feature-flags-0.44.1.md",
                "rollback-plan-0.44.1.md",
            ]
            for doc_name in doc_names:
                (release_dir / doc_name).write_text(
                    "0.44.1\n"
                    "No-overclaim boundary: no official approval, marketplace approval, "
                    "universal/full runtime support, external first-session pilot success. "
                    "RISK-036 remains open.\n"
                    "Official approval granted but Desktop lifecycle blocked.\n"
                    "Marketplace approval granted but external validation missing.\n",
                    encoding="utf-8",
                )
            (manifest_dir / "manifest.json").write_text(
                json.dumps({
                    "root_entries": {"files": [], "directories": []},
                    "product": {
                        "entries": [
                            {"path": f"docs/release/{doc_name}", "type": "file"}
                            for doc_name in doc_names
                        ],
                        "glob_patterns": [],
                    },
                    "repo_only": {"entries": [], "glob_patterns": []},
                }),
                encoding="utf-8",
            )
            tracked = {f"docs/release/{doc_name}" for doc_name in doc_names}
            with patch.object(vw, "_git_files", return_value=tracked):
                issues = vw.check_release_docs_coverage("0.44.1", root=root)

        self.assertTrue(
            any("forbidden release docs overclaim `official approval granted`" in issue for issue in issues)
        )
        self.assertTrue(
            any("forbidden release docs overclaim `marketplace approval granted`" in issue for issue in issues)
        )
        self.assertFalse(vw._line_has_scoped_claim_negation(
            "Official approval granted but Desktop lifecycle blocked.",
            "official approval granted",
        ))
        self.assertFalse(vw._line_has_scoped_claim_negation(
            "Marketplace approval granted but external validation missing.",
            "marketplace approval granted",
        ))

    def test_release_docs_coverage_allows_no_overclaim_boundary_wording(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_dir = root / "skills/software-project-governance/core"
            manifest_dir.mkdir(parents=True)
            release_dir = root / "docs/release"
            release_dir.mkdir(parents=True)
            doc_names = [
                "release-checklist-0.44.1.md",
                "feature-flags-0.44.1.md",
                "rollback-plan-0.44.1.md",
            ]
            for doc_name in doc_names:
                (release_dir / doc_name).write_text(
                    "0.44.1\n"
                    "No-overclaim boundary: no official approval, marketplace approval, "
                    "universal/full runtime support, external first-session pilot success, "
                    "Codex Desktop marketplace-management E2E PASS, automatic best-tool selection, "
                    "universal plugin/skill/tool availability, catalog entry runtime PASS, "
                    "or 1.0.0 production-ready claim. "
                    "RISK-036 remains open.\n",
                    encoding="utf-8",
                )
            (manifest_dir / "manifest.json").write_text(
                json.dumps({
                    "root_entries": {"files": [], "directories": []},
                    "product": {
                        "entries": [
                            {"path": f"docs/release/{doc_name}", "type": "file"}
                            for doc_name in doc_names
                        ],
                        "glob_patterns": [],
                    },
                    "repo_only": {"entries": [], "glob_patterns": []},
                }),
                encoding="utf-8",
            )
            tracked = {f"docs/release/{doc_name}" for doc_name in doc_names}
            with patch.object(vw, "_git_files", return_value=tracked):
                issues = vw.check_release_docs_coverage("0.44.1", root=root)

        self.assertEqual([], issues)

    def test_release_docs_coverage_allows_rollback_guard_wording(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_dir = root / "skills/software-project-governance/core"
            manifest_dir.mkdir(parents=True)
            release_dir = root / "docs/release"
            release_dir.mkdir(parents=True)
            docs = {
                "release-checklist-0.44.1.md": (
                    "0.44.1\n"
                    "No official approval, marketplace approval, universal/full runtime support, "
                    "external first-session pilot success. RISK-036 remains open.\n"
                ),
                "feature-flags-0.44.1.md": (
                    "0.44.1\n"
                    "No official approval, marketplace approval, universal/full runtime support, "
                    "external first-session pilot success. RISK-036 remains open.\n"
                ),
                "rollback-plan-0.44.1.md": (
                    "0.44.1\n"
                    "No official approval, marketplace approval, universal/full runtime support, "
                    "external first-session pilot success. RISK-036 remains open.\n"
                    "- 0.44.1 release docs or CHANGELOG 声明 official approval, marketplace approval, "
                    "universal/full runtime support, external first-session pilot success, "
                    "Codex Desktop marketplace-management E2E PASS, or 1.0.0 production-ready.\n"
                    "- 发布提交混入 Codex Desktop marketplace-management E2E PASS 或 1.0.0 changes.\n"
                ),
            }
            for doc_name, content in docs.items():
                (release_dir / doc_name).write_text(content, encoding="utf-8")
            (manifest_dir / "manifest.json").write_text(
                json.dumps({
                    "root_entries": {"files": [], "directories": []},
                    "product": {
                        "entries": [
                            {"path": f"docs/release/{doc_name}", "type": "file"}
                            for doc_name in docs
                        ],
                        "glob_patterns": [],
                    },
                    "repo_only": {"entries": [], "glob_patterns": []},
                }),
                encoding="utf-8",
            )
            tracked = {f"docs/release/{doc_name}" for doc_name in docs}
            with patch.object(vw, "_git_files", return_value=tracked):
                issues = vw.check_release_docs_coverage("0.44.1", root=root)

        self.assertEqual([], issues)

    def test_codex_desktop_marketplace_report_requires_blocked_matrix(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = root / "docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md"
            report.parent.mkdir(parents=True)
            report.write_text(
                "# Codex Desktop Marketplace-Management E2E Report\n"
                "## Result Matrix\n"
                "| Lifecycle step | 0.45.0 result | Evidence status | Exact missing Desktop evidence |\n"
                "| --- | --- | --- | --- |\n"
                "| Codex Desktop version and environment capture | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Marketplace add | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Plugin install | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Plugin enable | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Plugin visibility with display name, description, icon, and preview | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Skill discovery | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Governance status | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Upgrade or reinstall | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Disable, uninstall, or rollback | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "No official approval. No marketplace approval. No universal/full runtime support. "
                "No external first-session pilot success. "
                "No Codex Desktop marketplace-management E2E PASS. "
                "No 1.0.0 production-ready.\n",
                encoding="utf-8",
            )

            issues = vw.check_codex_desktop_marketplace_e2e_report(root=root)

        self.assertEqual([], issues)

    def test_codex_desktop_marketplace_report_accepts_expanded_blocked_matrix(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = root / "docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md"
            report.parent.mkdir(parents=True)
            report.write_text(
                "# Codex Desktop Marketplace-Management E2E Report\n"
                "## Result Matrix\n"
                "| Lifecycle step | 0.45.0 result | Evidence status | Exact missing Desktop evidence |\n"
                "| --- | --- | --- | --- |\n"
                "| Codex Desktop version and environment capture | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Marketplace add or local marketplace registration | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Plugin install from Codex Desktop | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Plugin enable from Codex Desktop | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Plugin visibility with display name, description, icon, and preview | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Skill discovery or invocation | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Governance status or Delivery Trust Snapshot from a real project | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Upgrade or reinstall after manifest version change | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Disable, uninstall, or rollback | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Official/public marketplace approval | BLOCKED | NOT_SUPPORTED | No approval evidence. |\n"
                "No official approval. No marketplace approval. No universal/full runtime support. "
                "No external first-session pilot success. "
                "No Codex Desktop marketplace-management E2E PASS. "
                "No 1.0.0 production-ready.\n",
                encoding="utf-8",
            )

            issues = vw.check_codex_desktop_marketplace_e2e_report(root=root)

        self.assertEqual([], issues)

    def test_codex_desktop_marketplace_report_current_real_report_passes(self):
        report = vw.ROOT / "docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md"
        if not report.is_file():
            self.skipTest("0.45.0 Codex Desktop marketplace report is not present")

        issues = vw.check_codex_desktop_marketplace_e2e_report(root=vw.ROOT)

        self.assertEqual([], issues)

    def test_codex_desktop_marketplace_report_rejects_lifecycle_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = root / "docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md"
            report.parent.mkdir(parents=True)
            report.write_text(
                "# Codex Desktop Marketplace-Management E2E Report\n"
                "## Result Matrix\n"
                "| Lifecycle step | 0.45.0 result | Evidence status | Exact missing Desktop evidence |\n"
                "| --- | --- | --- | --- |\n"
                "| Marketplace add | PASS | NOT_RUN | Manifest exists. |\n"
                "| Plugin install | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Plugin enable | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Skill discovery | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Governance status | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Upgrade or reinstall | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Disable, uninstall, or rollback | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "No official approval. No marketplace approval. No universal/full runtime support. "
                "No external first-session pilot success. "
                "No Codex Desktop marketplace-management E2E PASS. "
                "No 1.0.0 production-ready.\n",
                encoding="utf-8",
            )

            issues = vw.check_codex_desktop_marketplace_e2e_report(root=root)

        self.assertTrue(any("must not be PASS" in issue for issue in issues))

    def test_codex_desktop_marketplace_report_rejects_allowlist_marker_pass_abuse(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = root / "docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md"
            report.parent.mkdir(parents=True)
            report.write_text(
                "# Codex Desktop Marketplace-Management E2E Report\n"
                "## Result Matrix\n"
                "| Lifecycle step | 0.45.0 result | Evidence status | Exact missing Desktop evidence |\n"
                "| --- | --- | --- | --- |\n"
                "| Marketplace add | PASS | NOT_RUN | CDX-DESKTOP-002 manifest exists. |\n"
                "| Plugin install | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Plugin enable | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Skill discovery | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Governance status | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Upgrade or reinstall | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Disable, uninstall, or rollback | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "No official approval. No marketplace approval. No universal/full runtime support. "
                "No external first-session pilot success. "
                "No Codex Desktop marketplace-management E2E PASS. "
                "No 1.0.0 production-ready.\n",
                encoding="utf-8",
            )

            issues = vw.check_codex_desktop_marketplace_e2e_report(root=root)

        self.assertTrue(any("marketplace add" in issue and "must be BLOCKED" in issue for issue in issues))

    def test_codex_desktop_marketplace_report_rejects_expanded_ready_status(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = root / "docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md"
            report.parent.mkdir(parents=True)
            report.write_text(
                "# Codex Desktop Marketplace-Management E2E Report\n"
                "## Result Matrix\n"
                "| Lifecycle step | 0.45.0 result | Evidence status | Exact missing Desktop evidence |\n"
                "| --- | --- | --- | --- |\n"
                "| Codex Desktop version and environment capture | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Marketplace add or local marketplace registration | READY | NOT_RUN | No Desktop evidence. |\n"
                "| Plugin install from Codex Desktop | BLOCKED | READY | No Desktop evidence. |\n"
                "| Plugin enable from Codex Desktop | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Plugin visibility with display name, description, icon, and preview | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Skill discovery or invocation | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Governance status or Delivery Trust Snapshot from a real project | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Upgrade or reinstall after manifest version change | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Disable, uninstall, or rollback | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Official/public marketplace approval | BLOCKED | NOT_SUPPORTED | No approval evidence. |\n"
                "No official approval. No marketplace approval. No universal/full runtime support. "
                "No external first-session pilot success. "
                "No Codex Desktop marketplace-management E2E PASS. "
                "No 1.0.0 production-ready.\n",
                encoding="utf-8",
            )

            issues = vw.check_codex_desktop_marketplace_e2e_report(root=root)

        self.assertTrue(any("marketplace add or local marketplace registration" in issue and "must be BLOCKED" in issue for issue in issues))
        self.assertTrue(any("plugin install from codex desktop" in issue and "must be NOT_RUN" in issue for issue in issues))

    def test_codex_desktop_marketplace_report_rejects_positive_non_pass_status(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = root / "docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md"
            report.parent.mkdir(parents=True)
            report.write_text(
                "# Codex Desktop Marketplace-Management E2E Report\n"
                "## Result Matrix\n"
                "| Lifecycle step | 0.45.0 result | Evidence status | Exact missing Desktop evidence |\n"
                "| --- | --- | --- | --- |\n"
                "| Marketplace add | READY | NOT_RUN | No Desktop evidence. |\n"
                "| Plugin install | SUPPORTED | NOT_RUN | No Desktop evidence. |\n"
                "| Plugin enable | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Skill discovery | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Governance status | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Upgrade or reinstall | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Disable, uninstall, or rollback | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "## Acceptance Criteria\n"
                "- Future PASS requires real Desktop lifecycle evidence.\n"
                "No official approval. No marketplace approval. No universal/full runtime support. "
                "No external first-session pilot success. "
                "No Codex Desktop marketplace-management E2E PASS. "
                "No 1.0.0 production-ready.\n",
                encoding="utf-8",
            )

            issues = vw.check_codex_desktop_marketplace_e2e_report(root=root)

        self.assertTrue(any("marketplace add" in issue and "must be BLOCKED" in issue for issue in issues))
        self.assertTrue(any("plugin install" in issue and "must be BLOCKED" in issue for issue in issues))
        self.assertTrue(any("PASS/READY/SUPPORTED" in issue for issue in issues))

    def test_codex_desktop_marketplace_report_rejects_missing_not_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = root / "docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md"
            report.parent.mkdir(parents=True)
            report.write_text(
                "# Codex Desktop Marketplace-Management E2E Report\n"
                "## Result Matrix\n"
                "| Lifecycle step | 0.45.0 result | Evidence status | Exact missing Desktop evidence |\n"
                "| --- | --- | --- | --- |\n"
                "| Marketplace add | BLOCKED | READY | No Desktop evidence. |\n"
                "| Plugin install | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Plugin enable | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Skill discovery | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Governance status | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Upgrade or reinstall | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "| Disable, uninstall, or rollback | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
                "No official approval. No marketplace approval. No universal/full runtime support. "
                "No external first-session pilot success. "
                "No Codex Desktop marketplace-management E2E PASS. "
                "No 1.0.0 production-ready.\n",
                encoding="utf-8",
            )

            issues = vw.check_codex_desktop_marketplace_e2e_report(root=root)

        self.assertTrue(any("marketplace add" in issue and "must be NOT_RUN" in issue for issue in issues))

    def _write_fix118_docs(self, root, *, mutate=None):
        root = Path(root)
        docs = {
            "docs/marketplace/official-submission-0.46.0.md": (
                "# Official Submission Ecosystem Positioning - 0.46.0\n"
                "This package positions the workflow as a governance trust layer that "
                "orchestrates external capabilities. It does not replace Superpowers, "
                "Agent Skills, MCP servers, browser tools, or host-native plugins.\n"
                "FIX-115 capability-context --fail-on-issues. "
                "FIX-116 capability-registry.json and check-capability-registry --fail-on-issues. "
                "FIX-117 check-host-capability-context --fail-on-issues. "
                "docs/requirements/capability-discovery-orchestration-0.45.0.md. "
                "docs/requirements/governance-eval-benchmark-0.45.0.md. "
                "Codex Desktop marketplace-management remains BLOCKED / NOT_RUN via "
                "docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md. "
                "check-release --version 0.46.0 --require-changelog --runtime-adapters.\n"
                "No official approval. No marketplace approval. No universal/full runtime support. "
                "No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. "
                "No automatic best-tool selection. No universal plugin/skill/tool availability. "
                "No catalog entry runtime PASS. No 1.0.0 production-ready.\n"
            ),
            "docs/marketplace/ecosystem-positioning-0.46.0.md": (
                "# Ecosystem Positioning - 0.46.0\n"
                "The governance trust layer orchestrates external capabilities and complements "
                "Superpowers, Agent Skills, MCP, browser tools, and host-native plugins. "
                "FIX-115, FIX-116, FIX-117, docs/requirements/capability-discovery-orchestration-0.45.0.md, "
                "docs/requirements/governance-eval-benchmark-0.45.0.md, and BLOCKED / NOT_RUN Desktop facts.\n"
                "No official approval. No marketplace approval. No universal/full runtime support. "
                "No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. "
                "No automatic best-tool selection. No universal plugin/skill/tool availability. "
                "No catalog entry runtime PASS. No 1.0.0 production-ready.\n"
            ),
            "docs/marketplace/comparison-0.46.0.md": (
                "# Ecosystem Comparison - 0.46.0\n"
                "Superpowers, Agent Skills, MCP, browser tools, host-native plugins, scripts, and fallbacks "
                "are complementary external capabilities. The governance trust layer orchestrates external "
                "capabilities without replacing them. FIX-115, FIX-116, FIX-117, "
                "docs/requirements/capability-discovery-orchestration-0.45.0.md, "
                "docs/requirements/governance-eval-benchmark-0.45.0.md, and BLOCKED / NOT_RUN Desktop facts are preserved.\n"
                "No official approval. No marketplace approval. No universal/full runtime support. "
                "No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. "
                "No automatic best-tool selection. No universal plugin/skill/tool availability. "
                "No catalog entry runtime PASS. No 1.0.0 production-ready.\n"
            ),
            "docs/marketplace/migration-guide-0.46.0.md": (
                "# Migration Guide - 0.46.0\n"
                "Keep Superpowers, Agent Skills, MCP servers, browser tools, and host-native plugins. "
                "Add this governance trust layer to orchestrates external capabilities through evidence, "
                "side-effect boundaries, validation, and review. FIX-115, FIX-116, FIX-117, "
                "docs/requirements/capability-discovery-orchestration-0.45.0.md, "
                "docs/requirements/governance-eval-benchmark-0.45.0.md, and BLOCKED / NOT_RUN.\n"
                "No official approval. No marketplace approval. No universal/full runtime support. "
                "No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. "
                "No automatic best-tool selection. No universal plugin/skill/tool availability. "
                "No catalog entry runtime PASS. No 1.0.0 production-ready.\n"
            ),
            "docs/marketplace/examples-0.46.0.md": (
                "# Ecosystem Examples - 0.46.0\n"
                "Examples consume FIX-115, FIX-116, FIX-117, capability-registry.json, "
                "docs/requirements/capability-discovery-orchestration-0.45.0.md, "
                "docs/requirements/governance-eval-benchmark-0.45.0.md, "
                "and Codex Desktop marketplace-management BLOCKED / NOT_RUN facts. "
                "They show the governance trust layer orchestrates external capabilities.\n"
                "No official approval. No marketplace approval. No universal/full runtime support. "
                "No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. "
                "No automatic best-tool selection. No universal plugin/skill/tool availability. "
                "No catalog entry runtime PASS. No 1.0.0 production-ready.\n"
            ),
            "docs/release/release-checklist-0.46.0.md": (
                "# Release Checklist - 0.46.0\n"
                "FIX-118 official submission ecosystem docs consume FIX-115, FIX-116, FIX-117, "
                "capability-context --fail-on-issues, check-capability-registry --fail-on-issues, "
                "check-host-capability-context --fail-on-issues, "
                "docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md, "
                "docs/requirements/capability-discovery-orchestration-0.45.0.md, "
                "docs/requirements/governance-eval-benchmark-0.45.0.md, and "
                "check-release --version 0.46.0 --require-changelog --runtime-adapters. "
                "The governance trust layer orchestrates external capabilities.\n"
                "No official approval. No marketplace approval. No universal/full runtime support. "
                "No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. "
                "No automatic best-tool selection. No universal plugin/skill/tool availability. "
                "No catalog entry runtime PASS. No 1.0.0 production-ready. RISK-036 remains open.\n"
            ),
            "docs/release/feature-flags-0.46.0.md": (
                "# Feature Flags - 0.46.0\n"
                "Documentation guard only for governance trust layer positioning that orchestrates external capabilities. "
                "FIX-115, FIX-116, FIX-117, docs/requirements/capability-discovery-orchestration-0.45.0.md, "
                "docs/requirements/governance-eval-benchmark-0.45.0.md, and BLOCKED / NOT_RUN.\n"
                "No official approval. No marketplace approval. No universal/full runtime support. "
                "No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. "
                "No automatic best-tool selection. No universal plugin/skill/tool availability. "
                "No catalog entry runtime PASS. No 1.0.0 production-ready. RISK-036 remains open.\n"
            ),
            "docs/release/rollback-plan-0.46.0.md": (
                "# Rollback Plan - 0.46.0\n"
                "Rollback if release docs, requirement reports, or CHANGELOG claim official approval, "
                "marketplace approval, universal/full runtime support, external first-session pilot success, "
                "Codex Desktop marketplace-management E2E PASS, automatic best-tool selection, "
                "universal plugin/skill/tool availability, catalog entry runtime PASS, or 1.0.0 production-ready. "
                "The governance trust layer orchestrates external capabilities. FIX-115, FIX-116, FIX-117, "
                "docs/requirements/capability-discovery-orchestration-0.45.0.md, "
                "docs/requirements/governance-eval-benchmark-0.45.0.md, and BLOCKED / NOT_RUN.\n"
                "No official approval. No marketplace approval. No universal/full runtime support. "
                "No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. "
                "No automatic best-tool selection. No universal plugin/skill/tool availability. "
                "No catalog entry runtime PASS. No 1.0.0 production-ready. RISK-036 remains open.\n"
            ),
        }
        if mutate:
            docs = mutate(docs)
        for rel_path, content in docs.items():
            path = root / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        report = root / "docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            "# Codex Desktop Marketplace-Management E2E Report\n"
            "## Result Matrix\n"
            "| Lifecycle step | 0.45.0 result | Evidence status | Exact missing Desktop evidence |\n"
            "| --- | --- | --- | --- |\n"
            "| Codex Desktop version and environment capture | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
            "| Marketplace add or local marketplace registration | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
            "| Plugin install from Codex Desktop | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
            "| Plugin enable from Codex Desktop | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
            "| Plugin visibility with display name, description, icon, and preview | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
            "| Skill discovery or invocation | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
            "| Governance status or Delivery Trust Snapshot from a real project | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
            "| Upgrade or reinstall after manifest version change | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
            "| Disable, uninstall, or rollback | BLOCKED | NOT_RUN | No Desktop evidence. |\n"
            "| Official/public marketplace approval | BLOCKED | NOT_SUPPORTED | No approval evidence. |\n"
            "No official approval. No marketplace approval. No universal/full runtime support. "
            "No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. "
            "No 1.0.0 production-ready.\n",
            encoding="utf-8",
        )
        manifest = root / "skills/software-project-governance/core/manifest.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            json.dumps({
                "root_entries": {"files": [], "directories": []},
                "product": {
                    "entries": [{"path": rel_path, "type": "file"} for rel_path in docs],
                    "glob_patterns": [],
                },
                "repo_only": {"entries": [], "glob_patterns": []},
            }),
            encoding="utf-8",
        )
        return set(docs)

    def test_official_submission_ecosystem_current_docs_pass(self):
        tracked = set(vw._git_files(["ls-files", "--cached"]) or set())
        tracked.update(vw.OFFICIAL_SUBMISSION_DOC_PATHS)
        tracked.update(vw.OFFICIAL_SUBMISSION_RELEASE_DOC_PATHS)
        with patch.object(vw, "_git_files", return_value=tracked):
            issues = vw.check_official_submission_ecosystem(root=vw.ROOT)

        self.assertEqual([], issues)

    def test_official_submission_ecosystem_accepts_bounded_docs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tracked = self._write_fix118_docs(root)
            with patch.object(vw, "_git_files", return_value=tracked):
                issues = vw.check_official_submission_ecosystem(root=root)

        self.assertEqual([], issues)

    def test_official_submission_ecosystem_allows_legal_marketplace_boundary(self):
        def mutate(docs):
            docs["docs/marketplace/comparison-0.46.0.md"] += "\nNo marketplace approval.\n"
            return docs

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tracked = self._write_fix118_docs(root, mutate=mutate)
            with patch.object(vw, "_git_files", return_value=tracked):
                issues = vw.check_official_submission_ecosystem(root=root)

        self.assertEqual([], issues)

    def test_official_submission_ecosystem_rejects_same_line_negation_masking(self):
        def mutate(docs):
            docs["docs/marketplace/comparison-0.46.0.md"] += (
                "\nNo marketplace approved for local catalog; marketplace approved for all hosts.\n"
            )
            return docs

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tracked = self._write_fix118_docs(root, mutate=mutate)
            with patch.object(vw, "_git_files", return_value=tracked):
                issues = vw.check_official_submission_ecosystem(root=root)

        self.assertTrue(any("marketplace approved" in issue for issue in issues))

    def test_official_submission_ecosystem_rejects_release_docs_claim_in_marketplace_doc(self):
        def mutate(docs):
            docs["docs/marketplace/comparison-0.46.0.md"] += (
                "\nThe release docs claim marketplace approved for all hosts.\n"
            )
            return docs

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tracked = self._write_fix118_docs(root, mutate=mutate)
            with patch.object(vw, "_git_files", return_value=tracked):
                issues = vw.check_official_submission_ecosystem(root=root)

        self.assertTrue(any("marketplace approved" in issue for issue in issues))

    def test_official_submission_ecosystem_allows_legal_catalog_boundary(self):
        self.assertTrue(
            vw._official_submission_line_has_safe_negation(
                "No catalog entry runtime PASS.",
                "catalog entry runtime pass",
            )
        )

    def test_official_submission_ecosystem_requires_045_evidence_consumption(self):
        def mutate(docs):
            return {path: content.replace("FIX-117", "restricted benchmark") for path, content in docs.items()}

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tracked = self._write_fix118_docs(root, mutate=mutate)
            with patch.object(vw, "_git_files", return_value=tracked):
                issues = vw.check_official_submission_ecosystem(root=root)

        self.assertTrue(any("FIX-117" in issue for issue in issues))

    def test_official_submission_ecosystem_rejects_positive_overclaim(self):
        def mutate(docs):
            docs["docs/marketplace/comparison-0.46.0.md"] += (
                "\nNo official approval, marketplace approved for all hosts.\n"
            )
            return docs

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tracked = self._write_fix118_docs(root, mutate=mutate)
            with patch.object(vw, "_git_files", return_value=tracked):
                issues = vw.check_official_submission_ecosystem(root=root)

        self.assertTrue(any("marketplace approved" in issue for issue in issues))

    def test_official_submission_ecosystem_rejects_replacement_positioning(self):
        def mutate(docs):
            docs["docs/marketplace/migration-guide-0.46.0.md"] += "\nThis replaces Superpowers and Agent Skills.\n"
            return docs

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tracked = self._write_fix118_docs(root, mutate=mutate)
            with patch.object(vw, "_git_files", return_value=tracked):
                issues = vw.check_official_submission_ecosystem(root=root)

        self.assertTrue(any("replaces superpowers" in issue for issue in issues))

    def test_check_release_docs_coverage_046_runs_official_submission_guard(self):
        with patch.object(vw, "check_official_submission_ecosystem", return_value=["missing ecosystem boundary"]):
            issues = vw.check_release_docs_coverage("0.46.0", root=vw.ROOT)

        self.assertTrue(any("missing ecosystem boundary" in issue for issue in issues))

    def test_check_release_docs_coverage_047_runs_mainstream_loading_guard(self):
        with patch.object(vw, "check_mainstream_agent_loading", return_value=["missing mainstream loading boundary"]):
            issues = vw.check_release_docs_coverage("0.47.0", root=vw.ROOT)

        self.assertTrue(any("missing mainstream loading boundary" in issue for issue in issues))

    def test_check_release_readiness_fails_on_cross_reference_issues(self):
        patches = self._clean_release_patches()
        cross_ref_result = {
            "dangling": [{"source": "skills/example.md", "line": 3, "target": "missing.md"}],
            "deprecated": [],
            "cycles": [],
            "total_files_scanned": 1,
            "total_refs": 1,
        }
        patches[8] = patch.object(vw, "check_cross_references", return_value=cross_ref_result)
        stack, _mocks = self._apply_release_patches(patches)
        with stack:
            result = vw.check_release_readiness()
        self.assertFalse(result["pass"])
        self.assertTrue(any("dangling reference" in issue for issue in result["issues"]))

    def test_check_release_readiness_runs_execution_gates_when_requested(self):
        patches = self._clean_release_patches()
        calls = []

        def fake_runner(label, command):
            calls.append((label, command))
            return {
                "label": label,
                "pass": True,
                "exit_code": 0,
                "issue": None,
                "command": " ".join(str(part) for part in command),
            }

        stack, _mocks = self._apply_release_patches(patches)
        with stack:
            result = vw.check_release_readiness(
                run_execution_gates=True,
                execution_gate_runner=fake_runner,
            )

        self.assertTrue(result["pass"])
        self.assertEqual(["verify", "governance health", "e2e check", "unit tests"], [call[0] for call in calls])
        self.assertEqual(4, len(result["details"]["execution_gates"]["results"]))

    def test_check_release_readiness_fails_when_execution_gate_fails(self):
        patches = self._clean_release_patches()

        def fake_runner(label, command):
            return {
                "label": label,
                "pass": label != "unit tests",
                "exit_code": 1 if label == "unit tests" else 0,
                "issue": "unit tests: exit=1; output=FAILED" if label == "unit tests" else None,
                "command": " ".join(str(part) for part in command),
            }

        stack, _mocks = self._apply_release_patches(patches)
        with stack:
            result = vw.check_release_readiness(
                run_execution_gates=True,
                execution_gate_runner=fake_runner,
            )

        self.assertFalse(result["pass"])
        self.assertTrue(any("execution gate: unit tests" in issue for issue in result["issues"]))


class ProjectionSyncTests(unittest.TestCase):
    """FIX-086: source, target fixture, native entries, and plugin versions stay synchronized."""

    def _write_projection_fixture(self, root, *, version="0.37.0", drift=False):
        root = Path(root)
        target = root / "project/e2e-test-project"
        source_skill = root / "skills/software-project-governance"
        target_skill = target / "skills/software-project-governance"

        for path in [
            source_skill,
            target_skill,
            root / "commands",
            target / "commands",
            root / "agents",
            target / "agents",
            root / ".claude-plugin",
            root / ".codex-plugin",
            target / ".governance",
        ]:
            path.mkdir(parents=True, exist_ok=True)

        skill_text = f"---\nname: software-project-governance\nversion: {version}\n---\nCoordinator\n"
        (source_skill / "SKILL.md").write_text(skill_text, encoding="utf-8")
        (target_skill / "SKILL.md").write_text(
            skill_text + ("drift\n" if drift else ""),
            encoding="utf-8",
        )

        manifest = {"workflow": "software-project-governance", "version": version}
        (source_skill / "core").mkdir(parents=True)
        (target_skill / "core").mkdir(parents=True)
        (source_skill / "core/manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (target_skill / "core/manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (root / ".claude-plugin/plugin.json").write_text(json.dumps({"version": version}), encoding="utf-8")
        (root / ".codex-plugin/plugin.json").write_text(json.dumps({"version": version}), encoding="utf-8")

        command_text = "# governance\nScenario F\n"
        (root / "commands/governance.md").write_text(command_text, encoding="utf-8")
        (target / "commands/governance.md").write_text(command_text, encoding="utf-8")
        agent_text = "# Developer\n"
        (root / "agents/developer.md").write_text(agent_text, encoding="utf-8")
        (target / "agents/developer.md").write_text(agent_text, encoding="utf-8")

        (target / ".governance/plan-tracker.md").write_text(
            f"- **工作流版本**: {version}\n",
            encoding="utf-8",
        )
        (target / "CLAUDE.md").write_text(
            "Governance Bootstrap\nAskUserQuestion\n",
            encoding="utf-8",
        )
        (target / "AGENTS.md").write_text(
            "Governance Bootstrap\nCodex\nopencode\nskills/software-project-governance/SKILL.md\n",
            encoding="utf-8",
        )
        (target / "GEMINI.md").write_text(
            "Governance Bootstrap\nGemini\nskills/software-project-governance/SKILL.md\n",
            encoding="utf-8",
        )
        return target

    def test_projection_sync_passes_for_synced_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_projection_fixture(root)
            result = vw.check_projection_sync(
                root=root,
                patterns=[
                    "skills/software-project-governance/SKILL.md",
                    "commands/*.md",
                    "agents/*.md",
                ],
            )
        self.assertTrue(result["pass"], result["issues"])
        self.assertEqual(result["mirrors_checked"], 3)

    def test_projection_sync_rejects_fixture_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_projection_fixture(root, drift=True)
            result = vw.check_projection_sync(
                root=root,
                patterns=["skills/software-project-governance/SKILL.md"],
            )
        self.assertFalse(result["pass"])
        self.assertTrue(any("target fixture drift" in issue for issue in result["issues"]))

    def test_projection_sync_rejects_plugin_version_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_projection_fixture(root, version="0.37.0")
            (root / ".codex-plugin/plugin.json").write_text(
                json.dumps({"version": "0.36.0"}),
                encoding="utf-8",
            )
            result = vw.check_projection_sync(
                root=root,
                patterns=["skills/software-project-governance/SKILL.md"],
            )
        self.assertFalse(result["pass"])
        self.assertTrue(any("source Codex plugin" in issue for issue in result["issues"]))

    def test_projection_sync_uses_tracked_target_scope_in_git_checkout(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._write_projection_fixture(root, version="0.37.0")
            shutil.rmtree(root / "project/e2e-test-project/agents")
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(
                [
                    "git",
                    "add",
                    "project/e2e-test-project/skills/software-project-governance/SKILL.md",
                    "project/e2e-test-project/commands/governance.md",
                    "project/e2e-test-project/.governance/plan-tracker.md",
                    "project/e2e-test-project/CLAUDE.md",
                    "project/e2e-test-project/AGENTS.md",
                    "project/e2e-test-project/GEMINI.md",
                ],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            result = vw.check_projection_sync(
                root=root,
                patterns=[
                    "skills/software-project-governance/SKILL.md",
                    "commands/*.md",
                    "agents/*.md",
                ],
            )
        self.assertTrue(result["pass"], result["issues"])
        self.assertEqual(result["mirrors_checked"], 2)
        self.assertGreaterEqual(result["mirrors_skipped_untracked"], 1)


class E2ECommandMatrixTests(unittest.TestCase):
    """FIX-060: e2e-check must execute real command proxies."""

    def _status_stdout(self, permission_mode="maximum-autonomy"):
        return "\n".join([
            "Project Overview",
            "Tasks",
            "Gate",
            f"Permission Mode (permission_mode / 操作权限模式): {permission_mode}",
            "Delivery Trust Snapshot",
            "Resume state: Existing governance state detected",
            "Carry-over: 1 active task(s)",
            "Open risks: 1 open risk(s); RISK-036 opened 2026-06-01",
            "Unfinished work: FIX-112 - Context-aware governance resume",
            "Source facts: .governance/session-snapshot.md ## 下次会话优先级: FIX-112",
            "Blocker state: no blocker recorded in checked facts",
            "Auto-continue: yes",
            "Interrupt boundary: continue automatically until critical decision, blocker, review, or release boundary",
            "Hooks: installed (pre-commit, commit-msg, post-commit)",
            "Goal: test",
            "Stage: 维护",
            "Gate/setup status: G11 passed",
            "Risk: no open risks yet",
            "Evidence: no delivery evidence yet",
            "Next action: continue the active task and attach evidence before completion",
            "Preset guidance: lite is the recommended first-run default; standard is for team delivery; strict is for regulated/high-risk work",
            "Question budget: ask no more than 3 non-critical questions before snapshot; record deferred non-critical fields as assumptions",
            "Verification signal: python skills/software-project-governance/infra/verify_workflow.py status",
            (
                "No-overclaim boundary: local snapshot only; no official approval, "
                "marketplace approval, universal/full runtime support, or "
                "1.0.0 production-ready claim"
            ),
            "",
        ])

    def test_e2e_matrix_entry_invokes_subprocess(self):
        entry = vw._e2e_command_matrix()[0]
        completed = subprocess.CompletedProcess(
            entry["command"],
            0,
            stdout=self._status_stdout(),
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
            stdout=self._status_stdout("default-confirm"),
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
        fake_target_cwd_results = [
            {
                "label": "target-cwd /governance-status",
                "kind": "target_cwd_command",
                "status": "PASS",
                "exit_code": 0,
                "message": "target cwd status executed",
                "command": ["python", "skills/software-project-governance/infra/verify_workflow.py", "status"],
            }
        ]
        fake_fixture_results = [
            {
                "label": "target plan-tracker project config",
                "status": "PASS",
                "message": "fixture content matches expected markers",
            }
        ]

        with patch.object(vw, "_e2e_command_matrix", return_value=fake_entries), \
             patch.object(vw, "_evaluate_e2e_command", side_effect=fake_results + fake_target_cwd_results), \
             patch.object(vw, "_e2e_target_cwd_command_matrix", return_value=[{"label": "target"}]), \
             patch.object(vw, "_e2e_target_fixture_checks", return_value=[{"label": "fixture"}]), \
             patch.object(vw, "_evaluate_e2e_target_fixture_check", side_effect=fake_fixture_results), \
             patch.object(vw, "_e2e_contract_checks", return_value=[]):
            output = io.StringIO()
            with redirect_stdout(output):
                vw.cmd_e2e_check(None)

        text = output.getvalue()
        self.assertIn("Source CLI proxy command matrix", text)
        self.assertIn("External target cwd command matrix", text)
        self.assertIn("Target fixture checks", text)
        self.assertIn("source_cli_proxy_pass=1", text)
        self.assertIn("expected_known_failure=1", text)
        self.assertIn("target_cwd_pass=1", text)
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
             patch.object(vw, "_e2e_target_cwd_command_matrix", return_value=[]), \
             patch.object(vw, "_e2e_target_fixture_checks", return_value=[{"label": "fixture"}]), \
             patch.object(vw, "_evaluate_e2e_target_fixture_check", return_value=fake_fixture), \
             patch.object(vw, "_e2e_contract_checks", return_value=[]):
            output = io.StringIO()
            with self.assertRaises(SystemExit) as cm, redirect_stdout(output):
                vw.cmd_e2e_check(None)

        self.assertEqual(cm.exception.code, 1)
        self.assertIn("target_fixture_fail=1", output.getvalue())

    def test_target_fixture_checks_require_all_native_entries_and_current_version(self):
        with tempfile.TemporaryDirectory() as td:
            e2e_dir = Path(td)
            governance_dir = e2e_dir / ".governance"
            governance_dir.mkdir(parents=True)
            (e2e_dir / "commands").mkdir()
            skill_dir = e2e_dir / "skills" / "software-project-governance"
            skill_dir.mkdir(parents=True)

            (e2e_dir / "CLAUDE.md").write_text(
                "Governance Bootstrap\nSELF-CHECK\nAskUserQuestion\n",
                encoding="utf-8",
            )
            (e2e_dir / "AGENTS.md").write_text(
                "Governance Bootstrap\nSELF-CHECK\nCodex\nopencode\n"
                "skills/software-project-governance/SKILL.md\n",
                encoding="utf-8",
            )
            (e2e_dir / "GEMINI.md").write_text(
                "Governance Bootstrap\nSELF-CHECK\nGemini\n"
                "skills/software-project-governance/SKILL.md\n",
                encoding="utf-8",
            )
            for name in ("evidence-log.md", "decision-log.md", "risk-log.md", "session-snapshot.md"):
                (governance_dir / name).write_text("# fixture\n", encoding="utf-8")
            (governance_dir / "plan-tracker.md").write_text(
                "- **工作流版本**: 0.45.0\n"
                "- **操作权限模式**: default-confirm\n",
                encoding="utf-8",
            )
            (skill_dir / "SKILL.md").write_text(
                "---\nversion: 0.45.0\n---\nCoordinator\nAgent Team\n",
                encoding="utf-8",
            )
            trust_snapshot_contract = (
                "Delivery Trust Snapshot\n"
                "Resume state\n"
                "Existing governance state detected\n"
                "Carry-over\n"
                "Open risks\n"
                "Unfinished work\n"
                "Source facts\n"
                "Blocker state\n"
                "Auto-continue\n"
                "Interrupt boundary\n"
                "Hooks\n"
                "Goal\n"
                "Stage\n"
                "Gate/setup status\n"
                "Risk\n"
                "Evidence\n"
                "Next action\n"
                "Preset guidance\n"
                "lite is the recommended first-run default\n"
                "standard is for team delivery\n"
                "strict is for regulated/high-risk work\n"
                "Question budget\n"
                "no more than 3 non-critical questions before snapshot\n"
                "deferred non-critical fields\n"
                "assumptions\n"
                "Verification signal\n"
                "No-overclaim boundary\n"
            )
            (e2e_dir / "commands" / "governance.md").write_text(
                "Scenario F\nAskUserQuestion\nCoordinator\n" + trust_snapshot_contract,
                encoding="utf-8",
            )
            (e2e_dir / "commands" / "governance-status.md").write_text(
                trust_snapshot_contract,
                encoding="utf-8",
            )

            results = [
                vw._evaluate_e2e_target_fixture_check(entry)
                for entry in vw._e2e_target_fixture_checks(e2e_dir)
            ]

        self.assertTrue(all(result["status"] == "PASS" for result in results), results)
        labels = {result["label"] for result in results}
        self.assertIn("AGENTS.md Codex/opencode native entry fixture", labels)
        self.assertIn("GEMINI.md native entry fixture", labels)
        self.assertIn("target workflow skill version", labels)


class GeminiAuthPreflightTests(unittest.TestCase):
    """FIX-078: Gemini auth preflight is reproducible and secret-safe."""

    def test_gemini_auth_preflight_blocks_when_cli_missing(self):
        result = vw._gemini_auth_preflight(
            env={},
            home=Path("missing-home"),
            which=lambda command: None,
            version_runner=lambda command: (0, "0.35.3"),
        )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["blocked_reason"], "Gemini CLI not found on PATH")

    def test_gemini_auth_preflight_blocks_when_auth_missing_after_version_pass(self):
        with tempfile.TemporaryDirectory() as td:
            result = vw._gemini_auth_preflight(
                env={},
                home=Path(td),
                which=lambda command: "gemini",
                version_runner=lambda command: (0, "0.35.3"),
            )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["blocked_reason"], "Gemini auth missing or not configured")
        self.assertIn("GEMINI_API_KEY", result["remediation"])
        self.assertIn("GOOGLE_API_KEY", result["remediation"])
        self.assertIn("Vertex", result["remediation"])
        self.assertIn("GCA", result["remediation"])

    def test_gemini_auth_preflight_passes_with_env_auth_without_secret_leak(self):
        secret = "sk-super-secret-value"
        result = vw._gemini_auth_preflight(
            env={"GEMINI_API_KEY": secret},
            home=Path("missing-home"),
            which=lambda command: "gemini",
            version_runner=lambda command: (0, "0.35.3"),
        )

        self.assertEqual(result["status"], "PASS")
        self.assertIn("env:GEMINI_API_KEY", result["auth_sources"])
        serialized = json.dumps(result)
        self.assertNotIn(secret, serialized)

    def test_gemini_auth_preflight_blocks_with_vertex_config_without_credentials(self):
        config_only_envs = [
            {"GOOGLE_CLOUD_PROJECT": "demo-project"},
            {"GOOGLE_GENAI_USE_VERTEXAI": "true"},
            {"GOOGLE_CLOUD_LOCATION": "us-central1"},
            {
                "GOOGLE_GENAI_USE_VERTEXAI": "true",
                "GOOGLE_CLOUD_PROJECT": "demo-project",
                "GOOGLE_CLOUD_LOCATION": "us-central1",
            },
        ]

        for env in config_only_envs:
            with self.subTest(env=env):
                result = vw._gemini_auth_preflight(
                    env=env,
                    home=Path("missing-home"),
                    which=lambda command: "gemini",
                    version_runner=lambda command: (0, "0.35.3"),
                )

                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual(result["blocked_reason"], "Gemini auth missing or not configured")
                self.assertEqual(result["auth_sources"], [])

    def test_gemini_auth_preflight_passes_with_complete_vertex_credentials_without_secret_leak(self):
        secret = "ya29.secret-token"
        result = vw._gemini_auth_preflight(
            env={
                "GOOGLE_GENAI_USE_VERTEXAI": "true",
                "GOOGLE_CLOUD_PROJECT": "demo-project",
                "GOOGLE_CLOUD_LOCATION": "us-central1",
                "GOOGLE_CLOUD_ACCESS_TOKEN": secret,
            },
            home=Path("missing-home"),
            which=lambda command: "gemini",
            version_runner=lambda command: (0, "0.35.3"),
        )

        self.assertEqual(result["status"], "PASS")
        self.assertIn(
            "env:VERTEX:GOOGLE_GENAI_USE_VERTEXAI+GOOGLE_CLOUD_PROJECT+GOOGLE_CLOUD_LOCATION+GOOGLE_CLOUD_ACCESS_TOKEN",
            result["auth_sources"],
        )
        self.assertNotIn(secret, json.dumps(result))

    def test_gemini_auth_preflight_blocks_with_gca_provider_without_token(self):
        result = vw._gemini_auth_preflight(
            env={"GCA_AUTH_PROVIDER": "google"},
            home=Path("missing-home"),
            which=lambda command: "gemini",
            version_runner=lambda command: (0, "0.35.3"),
        )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["auth_sources"], [])

    def test_gemini_auth_preflight_passes_with_complete_gca_credentials_without_secret_leak(self):
        secret = "gca-secret-token"
        result = vw._gemini_auth_preflight(
            env={"GCA_AUTH_PROVIDER": "google", "GCA_TOKEN": secret},
            home=Path("missing-home"),
            which=lambda command: "gemini",
            version_runner=lambda command: (0, "0.35.3"),
        )

        self.assertEqual(result["status"], "PASS")
        self.assertIn("env:GCA:GCA_AUTH_PROVIDER+GCA_TOKEN", result["auth_sources"])
        self.assertNotIn(secret, json.dumps(result))

    def test_gemini_auth_preflight_passes_with_settings_auth_provider(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            settings_dir = home / ".gemini"
            settings_dir.mkdir()
            (settings_dir / "settings.json").write_text(
                json.dumps({"auth": {"provider": "oauth"}}),
                encoding="utf-8",
            )

            result = vw._gemini_auth_preflight(
                env={},
                home=home,
                which=lambda command: "gemini",
                version_runner=lambda command: (0, "0.35.3"),
            )

        self.assertEqual(result["status"], "PASS")
        self.assertIn("settings:settings.json:auth_provider", result["auth_sources"])

    def test_gemini_auth_preflight_cli_output_does_not_print_secret(self):
        secret = "secret-google-api-key"
        with patch.object(vw, "_gemini_auth_preflight", return_value={
            "status": "PASS",
            "command": "python skills/software-project-governance/infra/verify_workflow.py gemini-auth-preflight",
            "version_command": "gemini --version",
            "cli_path": "gemini",
            "version": "0.35.3",
            "auth_sources": ["env:GOOGLE_API_KEY"],
            "blocked_reason": None,
            "remediation": "Set GOOGLE_API_KEY; do not print secret values.",
        }):
            output = io.StringIO()
            with redirect_stdout(output):
                vw.cmd_gemini_auth_preflight(argparse.Namespace())

        text = output.getvalue()
        self.assertIn("status: PASS", text)
        self.assertIn("env:GOOGLE_API_KEY", text)
        self.assertNotIn(secret, text)


class OpencodeProviderPreflightTests(unittest.TestCase):
    """FIX-079: opencode provider/model preflight is reproducible and secret-safe."""

    def test_opencode_provider_preflight_passes_with_legal_models(self):
        result = vw._opencode_provider_model_preflight(
            home=Path("missing-home"),
            root=Path("missing-root"),
            which=lambda command: "opencode",
            version_runner=lambda command: (0, "1.15.5"),
            probe_runner=lambda command: (
                0,
                "deepseek/deepseek-v4-pro\ndeepseek/deepseek-v4-flash\n",
            ),
            config_candidates=[],
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["legal_models"], ["deepseek-v4-flash", "deepseek-v4-pro"])
        self.assertIn("command:opencode models", result["model_sources"])

    def test_opencode_provider_preflight_blocks_invalid_ansi_suffix(self):
        result = vw._opencode_provider_model_preflight(
            home=Path("missing-home"),
            root=Path("missing-root"),
            which=lambda command: "opencode",
            version_runner=lambda command: (0, "1.15.5"),
            probe_runner=lambda command: (0, "configured model: deepseek-v4-pro[1m]"),
            config_candidates=[],
        )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("opencode provider/model config invalid", result["blocked_reason"])
        self.assertIn("deepseek-v4-pro[1m]", result["blocked_reason"])

    def test_opencode_provider_preflight_blocks_unsupported_model_output(self):
        result = vw._opencode_provider_model_preflight(
            home=Path("missing-home"),
            root=Path("missing-root"),
            which=lambda command: "opencode",
            version_runner=lambda command: (0, "1.15.5"),
            probe_runner=lambda command: (1, "unsupported model: deepseek-v4-pro[1m]"),
            config_candidates=[],
        )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("unsupported model output", result["blocked_reason"])

    def test_opencode_provider_preflight_does_not_leak_secret_values(self):
        secret = "local-provider-secret-value"
        result = vw._opencode_provider_model_preflight(
            home=Path("missing-home"),
            root=Path("missing-root"),
            which=lambda command: "opencode",
            version_runner=lambda command: (0, "1.15.5"),
            probe_runner=lambda command: (
                0,
                f"api_key={secret}\nmodel=deepseek-v4-pro\n",
            ),
            config_candidates=[],
        )

        self.assertEqual(result["status"], "PASS")
        self.assertNotIn(secret, json.dumps(result))

    def test_opencode_provider_preflight_cli_output_does_not_print_secret(self):
        secret = "local-output-secret-value"
        with patch.object(vw, "_opencode_provider_model_preflight", return_value={
            "status": "PASS",
            "command": "python skills/software-project-governance/infra/verify_workflow.py opencode-provider-preflight",
            "version_command": "opencode --version",
            "cli_path": "opencode",
            "version": "1.15.5",
            "legal_models": ["deepseek-v4-pro"],
            "model_sources": ["command:opencode models"],
            "blocked_reason": None,
            "remediation": f"Do not print secret={secret}.",
        }):
            output = io.StringIO()
            with redirect_stdout(output):
                vw.cmd_opencode_provider_preflight(argparse.Namespace())

        text = output.getvalue()
        self.assertIn("status: PASS", text)
        self.assertIn("deepseek-v4-pro", text)
        self.assertNotIn(secret, text)


class AgentRuntimeE2EHarnessTests(unittest.TestCase):
    """FIX-076: real agent runtime E2E harness command matrix and schema."""

    def test_agent_runtime_e2e_matrix_contains_four_platforms(self):
        with tempfile.TemporaryDirectory() as td:
            matrix = vw._agent_runtime_e2e_command_matrix(Path(td))

        agents = {entry["agent"] for entry in matrix}
        self.assertEqual(agents, {"claude", "codex", "gemini", "opencode"})
        for entry in matrix:
            self.assertIn("command", entry)
            self.assertIn("validator", entry)
            self.assertEqual(entry["cwd"], Path(td))

    def test_agent_runtime_passed_validator_requires_complete_structured_response(self):
        result = subprocess.CompletedProcess(
            ["claude"],
            0,
            stdout="E2E_PLATFORM=claude; E2E_AGENT=coordinator; E2E_STAGE=维护; E2E_MODE=always-on x default-confirm\n",
            stderr="",
        )

        ok, message = vw._validate_agent_runtime_e2e_passed("claude", result)

        self.assertTrue(ok)
        self.assertIn("E2E_PLATFORM=claude", message)
        self.assertIn("E2E_AGENT=coordinator", message)
        self.assertIn("E2E_STAGE=维护", message)
        self.assertIn("E2E_MODE=always-on x default-confirm", message)

    def test_agent_runtime_passed_validator_rejects_agent_as_legacy_platform_field(self):
        result = subprocess.CompletedProcess(
            ["claude"],
            0,
            stdout="E2E_AGENT=claude; E2E_STAGE=维护; E2E_MODE=always-on x default-confirm\n",
            stderr="",
        )

        ok, message = vw._validate_agent_runtime_e2e_passed("claude", result)

        self.assertFalse(ok)
        self.assertIn("platform=claude", message)

    def test_agent_runtime_passed_validator_accepts_fields_in_any_order(self):
        result = subprocess.CompletedProcess(
            ["claude"],
            0,
            stdout="E2E_AGENT=coordinator; E2E_PLATFORM=claude; E2E_MODE=silent-track x maximum-autonomy; E2E_STAGE=维护\n",
            stderr="",
        )

        ok, message = vw._validate_agent_runtime_e2e_passed("claude", result)

        self.assertTrue(ok)
        self.assertIn("E2E_PLATFORM=claude", message)
        self.assertIn("E2E_AGENT=coordinator", message)

    def test_agent_runtime_passed_validator_accepts_opencode_json_text_event(self):
        result = subprocess.CompletedProcess(
            ["opencode"],
            0,
            stdout=(
                '{"type":"text","part":{"text":"E2E_PLATFORM=opencode; '
                'E2E_AGENT=Coordinator; E2E_STAGE=立项与目标定义; '
                'E2E_MODE=always-on x default-confirm","time":123}}\n'
            ),
            stderr="",
        )

        ok, message = vw._validate_agent_runtime_e2e_passed("opencode", result)

        self.assertTrue(ok)
        self.assertIn("E2E_PLATFORM=opencode", message)
        self.assertIn("E2E_AGENT=Coordinator", message)
        self.assertIn("E2E_STAGE=立项与目标定义", message)
        self.assertIn("E2E_MODE=always-on x default-confirm", message)
        self.assertNotIn('","time"', message)

    def test_agent_runtime_passed_validator_rejects_invalid_mode_values(self):
        result = subprocess.CompletedProcess(
            ["claude"],
            0,
            stdout="E2E_PLATFORM=claude; E2E_AGENT=coordinator; E2E_STAGE=维护; E2E_MODE=manual x default-confirm\n",
            stderr="",
        )

        ok, message = vw._validate_agent_runtime_e2e_passed("claude", result)

        self.assertFalse(ok)
        self.assertIn("complete non-placeholder", message)

    def test_agent_runtime_passed_validator_rejects_prompt_echo(self):
        prompt_echo = vw._agent_runtime_e2e_prompt("codex")
        result = subprocess.CompletedProcess(
            ["codex"],
            0,
            stdout=prompt_echo,
            stderr="",
        )

        ok, message = vw._validate_agent_runtime_e2e_passed("codex", result)

        self.assertFalse(ok)
        self.assertIn("non-placeholder", message)

    def test_agent_runtime_passed_validator_rejects_agent_only_marker(self):
        result = subprocess.CompletedProcess(
            ["claude"],
            0,
            stdout="E2E_PLATFORM=claude; E2E_AGENT=coordinator\n",
            stderr="",
        )

        ok, message = vw._validate_agent_runtime_e2e_passed("claude", result)

        self.assertFalse(ok)
        self.assertIn("complete non-placeholder", message)

    def test_agent_runtime_e2e_classifies_gemini_auth_missing_as_blocked(self):
        entry = next(
            item for item in vw._agent_runtime_e2e_command_matrix(Path("."))
            if item["agent"] == "gemini"
        )
        completed = subprocess.CompletedProcess(
            entry["command"],
            1,
            stdout="",
            stderr="GEMINI_API_KEY is not configured; please authenticate with Vertex or GCA",
        )

        result = vw._evaluate_agent_runtime_e2e_command(
            entry,
            runner=lambda command, timeout=120, cwd=None: completed,
        )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("Gemini auth missing", result["blocked_reason"])

    def test_agent_runtime_e2e_classifies_opencode_invalid_deepseek_model_as_blocked(self):
        entry = next(
            item for item in vw._agent_runtime_e2e_command_matrix(Path("."))
            if item["agent"] == "opencode"
        )
        completed = subprocess.CompletedProcess(
            entry["command"],
            1,
            stdout='{"error":"model deepseek-v4-pro[1m] is not supported"}',
            stderr="DeepSeek 400 invalid model",
        )

        result = vw._evaluate_agent_runtime_e2e_command(
            entry,
            runner=lambda command, timeout=120, cwd=None: completed,
        )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("opencode provider/model config invalid", result["blocked_reason"])

    def test_agent_runtime_e2e_classifies_codex_timeout_as_blocked(self):
        entry = next(
            item for item in vw._agent_runtime_e2e_command_matrix(Path("."))
            if item["agent"] == "codex"
        )

        def timeout_runner(command, timeout=120, cwd=None):
            raise subprocess.TimeoutExpired(command, timeout, output="", stderr="timed out")

        result = vw._evaluate_agent_runtime_e2e_command(
            entry,
            timeout=3,
            runner=timeout_runner,
        )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("timed out", result["blocked_reason"])

    def test_agent_runtime_e2e_classifies_permission_error_as_blocked(self):
        entry = next(
            item for item in vw._agent_runtime_e2e_command_matrix(Path("."))
            if item["agent"] == "codex"
        )

        def permission_runner(command, timeout=120, cwd=None):
            raise PermissionError("access denied")

        result = vw._evaluate_agent_runtime_e2e_command(
            entry,
            runner=permission_runner,
        )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("permission/path resolution", result["blocked_reason"])

    def test_agent_runtime_command_resolves_path_shims(self):
        with patch.object(vw.shutil, "which", return_value=r"C:\tools\gemini.cmd"):
            command = vw._resolve_agent_runtime_command(["gemini", "--version"])

        self.assertEqual(command, [r"C:\tools\gemini.cmd", "--version"])

    def test_agent_runtime_subprocess_timeout_calls_process_tree_cleanup(self):
        class FakeProcess:
            pid = 4242
            returncode = None

            def __init__(self):
                self.calls = 0

            def communicate(self, timeout=None):
                self.calls += 1
                if self.calls == 1:
                    raise subprocess.TimeoutExpired(["codex"], timeout)
                return "partial stdout", "partial stderr"

        fake_process = FakeProcess()
        with patch.object(vw, "_resolve_agent_runtime_command", side_effect=lambda command: command), patch.object(
            vw.subprocess,
            "Popen",
            return_value=fake_process,
        ), patch.object(vw, "_cleanup_agent_runtime_process_tree") as cleanup:
            with self.assertRaises(subprocess.TimeoutExpired) as cm:
                vw._run_agent_runtime_e2e_subprocess(["codex"], timeout=1, cwd=Path("."))

        cleanup.assert_called_once_with(fake_process)
        self.assertEqual(cm.exception.output, "partial stdout")
        self.assertEqual(cm.exception.stderr, "partial stderr")

    def test_agent_runtime_e2e_cli_summary_counts(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            fake_results = [
                {
                    "agent": "claude",
                    "label": "Claude",
                    "status": "PASS",
                    "exit_code": 0,
                    "command": ["claude"],
                    "cwd": target,
                    "message": "ok",
                    "blocked_reason": None,
                    "log_summary": "E2E_PLATFORM=claude; E2E_AGENT=coordinator",
                },
                {
                    "agent": "gemini",
                    "label": "Gemini",
                    "status": "BLOCKED",
                    "exit_code": 1,
                    "command": ["gemini"],
                    "cwd": target,
                    "message": "Gemini auth missing or not configured",
                    "blocked_reason": "Gemini auth missing or not configured",
                    "log_summary": "GEMINI_API_KEY missing",
                },
            ]
            args = argparse.Namespace(
                target=str(target),
                timeout=9,
                agent=None,
            )
            with patch.object(vw, "_agent_runtime_e2e_command_matrix", return_value=[
                {"agent": "claude", "label": "Claude"},
                {"agent": "gemini", "label": "Gemini"},
            ]), patch.object(
                vw,
                "_evaluate_agent_runtime_e2e_command",
                side_effect=fake_results,
            ):
                output = io.StringIO()
                with redirect_stdout(output):
                    vw.cmd_agent_runtime_e2e(args)

        text = output.getvalue()
        self.assertIn("Agent Runtime E2E Harness", text)
        self.assertIn("[PASS] claude", text)
        self.assertIn("[BLOCKED] gemini", text)
        self.assertIn("pass=1, blocked=1, fail=0, total=2", text)


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
            root = Path(td)
            gov = root / ".governance"
            gov.mkdir()
            sample = gov / "plan-tracker.md"
            risk_path = gov / "risk-log.md"
            sample.write_text(plan, encoding="utf-8")
            risk_path.write_text("# 当前项目风险记录\n", encoding="utf-8")
            with patch.object(vw, "ROOT", root), \
                 patch.object(vw, "SAMPLE_PATH", sample), \
                 patch.object(vw, "RISK_PATH", risk_path):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    vw.cmd_status(None)

        output = buf.getvalue()
        self.assertIn("Permission Mode (permission_mode / 操作权限模式): maximum-autonomy", output)
        self.assertIn("Project Overview", output)
        self.assertIn("Delivery Trust Snapshot", output)
        self.assertIn("Resume state: Existing governance state detected", output)
        self.assertIn("Carry-over: 0 active task(s)", output)
        self.assertIn("Open risks: 0 open risk(s); none", output)
        self.assertIn("Unfinished work: not found", output)
        self.assertIn("Source facts:", output)
        self.assertIn("Blocker state: not found", output)
        self.assertIn("Auto-continue: no", output)
        self.assertIn("Interrupt boundary: AskUserQuestion required", output)
        self.assertIn("Goal: test", output)
        self.assertIn("Stage: 维护", output)
        self.assertIn("Gate/setup status: G11 通过", output)
        self.assertIn("Risk: no open risks yet", output)
        self.assertIn("Evidence: 1/1 task(s) completed; verify evidence before closing work", output)
        self.assertIn("Preset guidance: lite is the recommended first-run default", output)
        self.assertIn("standard is for team delivery", output)
        self.assertIn("strict is for regulated/high-risk work", output)
        self.assertIn("Question budget: ask no more than 3 non-critical questions before snapshot", output)
        self.assertIn("record deferred non-critical fields as assumptions", output)
        self.assertIn(
            "Verification signal: python skills/software-project-governance/infra/verify_workflow.py status",
            output,
        )
        self.assertIn("No-overclaim boundary:", output)
        self.assertIn("no official approval", output)
        self.assertIn("marketplace approval", output)
        self.assertIn("universal/full runtime support", output)
        self.assertIn("1.0.0 production-ready", output)

    def test_cmd_status_counts_active_seven_column_task_row(self):
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
            "| Demo | 维护 | 1 | 0 | 0 | 1 | G11 通过 | 2026-05-13 |",
            "",
            "## 当前活跃事项",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "| **P0** | FIX-100 | First-run Delivery Trust Snapshot vertical slice | AUDIT-106 | 0.42.0 | status snapshot | 🚧 进行中 |",
        ])
        with tempfile.TemporaryDirectory() as td:
            sample = Path(td) / "plan-tracker.md"
            sample.write_text(plan, encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sample):
                stats = vw.parse_task_stats()
                buf = io.StringIO()
                with redirect_stdout(buf):
                    vw.cmd_status(None)

        output = buf.getvalue()
        self.assertEqual(stats["进行中"], 1)
        self.assertIn("Carry-over: 1 active task(s)", output)
        self.assertIn("Unfinished work: FIX-100", output)
        self.assertIn("Source facts:", output)
        self.assertIn("Next action: resume FIX-100 and attach evidence before completion", output)

    def test_cmd_status_outputs_existing_project_resume_markers(self):
        plan = "\n".join([
            "# 计划跟踪",
            "",
            "## 项目配置",
            "- **项目目标**: resume happy path",
            "- **Profile**: standard",
            "- **触发模式**: always-on",
            "- **操作权限模式**: default-confirm",
            "- **当前阶段**: 维护",
            "",
            "## Gate 状态跟踪",
            "| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |",
            "| --- | --- | --- | --- | --- |",
            "| G11 | → 下一轮 | passed | 2026-06-03 | done |",
            "",
            "## 项目总览",
            "| 项目 | 当前阶段 | 总任务数 | 已完成 | 阻塞中 | 关键风险数 | 最近 Gate 结论 | 最近复盘日期 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
            "| Demo | 维护 | 2 | 1 | 0 | 1 | G11 通过 | 2026-06-03 |",
            "",
            "## 当前活跃事项",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "| **P0** | FIX-101 | Existing-project resume happy path | AUDIT-106 | 0.42.0 | status resume | 📋 待实施 |",
        ])
        risk = "\n".join([
            "# 当前项目风险记录",
            "| 编号 | 日期 | 风险/阻塞描述 | 所属阶段 | 触发条件 | 影响 | 严重级别 | Owner | 当前状态 | 缓解动作 | 截止日期 | 关联任务 | 备注 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "| RISK-036 | 2026-06-01 | adoption risk | 维护 | trigger | impact | 高 | Coordinator | 打开 | mitigate | 2026-06-15 | FIX-101 | note |",
        ])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / ".governance"
            gov.mkdir()
            sample = gov / "plan-tracker.md"
            risk_path = gov / "risk-log.md"
            sample.write_text(plan, encoding="utf-8")
            risk_path.write_text(risk, encoding="utf-8")
            for hook in ("pre-commit", "commit-msg", "post-commit"):
                hook_path = root / ".git" / "hooks" / hook
                hook_path.parent.mkdir(parents=True, exist_ok=True)
                hook_path.write_text("#!/bin/sh\n", encoding="utf-8")

            with patch.object(vw, "ROOT", root), \
                 patch.object(vw, "SAMPLE_PATH", sample), \
                 patch.object(vw, "RISK_PATH", risk_path):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    vw.cmd_status(None)

        output = buf.getvalue()
        self.assertIn("Resume state: Existing governance state detected", output)
        self.assertIn("Carry-over: 1 active task(s)", output)
        self.assertIn("Open risks: 1 open risk(s); RISK-036 opened 2026-06-01", output)
        self.assertIn("Unfinished work: FIX-101", output)
        self.assertIn("Source facts:", output)
        self.assertIn("Blocker state: open risk guard present: RISK-036", output)
        self.assertIn("Auto-continue: no", output)
        self.assertIn("Hooks: installed (pre-commit, commit-msg, post-commit)", output)
        self.assertIn("Next action: resume FIX-101 and attach evidence before completion", output)
        self.assertNotIn("governance-init", output)
        self.assertNotIn("reinitialize", output.lower())

    def test_cmd_status_counts_session_snapshot_carry_over_when_active_rows_absent(self):
        plan = "\n".join([
            "# 计划跟踪",
            "",
            "## 项目配置",
            "- **项目目标**: snapshot resume",
            "- **Profile**: standard",
            "- **触发模式**: always-on",
            "- **操作权限模式**: maximum-autonomy",
            "- **当前阶段**: 维护",
            "",
            "## Gate 状态跟踪",
            "| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |",
            "| --- | --- | --- | --- | --- |",
            "| G11 | → 下一轮 | passed | 2026-06-03 | done |",
            "",
            "## 项目总览",
            "| 项目 | 当前阶段 | 总任务数 | 已完成 | 阻塞中 | 关键风险数 | 最近 Gate 结论 | 最近复盘日期 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
            "| Demo | 维护 | 2 | 1 | 0 | 0 | G11 通过 | 2026-06-03 |",
            "",
            "## 当前活跃事项",
            "",
            "暂无活跃事项。",
        ])
        snapshot = "\n".join([
            "# 会话快照 — 2026-06-03",
            "",
            "## 遗留任务",
            "| 任务 ID | 描述 | 完成百分比 | 阻塞原因 | 优先级 |",
            "|---------|------|------------|----------|--------|",
            "| FIX-101 | Existing-project resume happy path | 40% | reviewer findings | P0 |",
            "",
            "## 本轮已完成",
            "- none",
        ])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / ".governance"
            gov.mkdir()
            sample = gov / "plan-tracker.md"
            risk_path = gov / "risk-log.md"
            snapshot_path = gov / "session-snapshot.md"
            sample.write_text(plan, encoding="utf-8")
            risk_path.write_text("# 当前项目风险记录\n", encoding="utf-8")
            snapshot_path.write_text(snapshot, encoding="utf-8")
            with patch.object(vw, "ROOT", root), \
                 patch.object(vw, "SAMPLE_PATH", sample), \
                 patch.object(vw, "RISK_PATH", risk_path), \
                 patch.object(vw, "SESSION_SNAPSHOT_PATH", snapshot_path):
                resume = vw.parse_resume_state()
                buf = io.StringIO()
                with redirect_stdout(buf):
                    vw.cmd_status(None)

        output = buf.getvalue()
        self.assertEqual(resume["carry_over_count"], 1)
        self.assertIn("Carry-over: 1 active task(s)", output)
        self.assertIn("Unfinished work: FIX-101", output)
        self.assertIn("Source facts:", output)
        self.assertIn("Next action: resume FIX-101 and attach evidence before completion", output)

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

    def test_governance_status_docs_require_delivery_trust_snapshot_contract(self):
        status_text = (vw.ROOT / "commands" / "governance-status.md").read_text(encoding="utf-8")
        governance_text = (vw.ROOT / "commands" / "governance.md").read_text(encoding="utf-8")
        fixture_status = (
            vw.ROOT / "project" / "e2e-test-project" / "commands" / "governance-status.md"
        ).read_text(encoding="utf-8")
        fixture_governance = (
            vw.ROOT / "project" / "e2e-test-project" / "commands" / "governance.md"
        ).read_text(encoding="utf-8")

        required = [
            "Delivery Trust Snapshot",
            "Resume state",
            "Existing governance state detected",
            "Carry-over",
            "Open risks",
            "Unfinished work",
            "Source facts",
            "Blocker state",
            "Auto-continue",
            "Interrupt boundary",
            "Hooks",
            "Goal",
            "Stage",
            "Gate/setup status",
            "Risk",
            "Evidence",
            "Next action",
            "Preset guidance",
            "lite is the recommended first-run default",
            "standard is for team delivery",
            "strict is for regulated/high-risk work",
            "Question budget",
            "no more than 3 non-critical questions before snapshot",
            "deferred non-critical fields",
            "assumptions",
            "Verification signal",
            "No-overclaim boundary",
            "official approval",
            "marketplace approval",
            "universal/full runtime support",
            "1.0.0 production-ready",
            "first-run-demo --assert-snapshot",
            "governance-context",
            "not found",
            "do not invent",
            "demo/local-only",
            "external credentials",
        ]
        for label, text in {
            "commands/governance-status.md": status_text,
            "commands/governance.md": governance_text,
            "project/e2e-test-project/commands/governance-status.md": fixture_status,
            "project/e2e-test-project/commands/governance.md": fixture_governance,
        }.items():
            with self.subTest(label=label):
                self.assertEqual([needle for needle in required if needle not in text], [])

    def test_target_status_validator_requires_no_overclaim_denial_content(self):
        base_output = (
            "Project Overview\n"
            "Tasks\n"
            "Gate\n"
            "Permission Mode (permission_mode / 操作权限模式): maximum-autonomy\n"
            "Delivery Trust Snapshot\n"
            "Resume state: Existing governance state detected\n"
            "Carry-over: 0 active task(s)\n"
            "Open risks: 0 open risk(s); none\n"
            "Unfinished work: not found\n"
            "Source facts: checked .governance/plan-tracker.md; no unfinished user work facts found\n"
            "Blocker state: not found\n"
            "Auto-continue: no\n"
            "Interrupt boundary: AskUserQuestion required before creating new work from assumptions\n"
            "Hooks: installed (pre-commit, commit-msg, post-commit)\n"
            "Goal: test\n"
            "Stage: 维护\n"
            "Gate/setup status: G11 passed\n"
            "Risk: no open risks yet\n"
            "Evidence: no delivery evidence yet\n"
            "Next action: continue the active task and attach evidence before completion\n"
            "Preset guidance: lite is the recommended first-run default; standard is for team delivery; strict is for regulated/high-risk work\n"
            "Question budget: no more than 3 non-critical questions before snapshot; deferred non-critical fields become assumptions\n"
            "Verification signal: python skills/software-project-governance/infra/verify_workflow.py status\n"
            "No-overclaim boundary: local snapshot only\n"
        )
        missing_denials = subprocess.CompletedProcess(args=[], returncode=0, stdout=base_output, stderr="")
        ok, _ = vw._validate_e2e_target_status(missing_denials)
        self.assertFalse(ok)

        full_output = (
            base_output
            + "no official approval, marketplace approval, universal/full runtime support, "
            + "or 1.0.0 production-ready claim\n"
        )
        with_denials = subprocess.CompletedProcess(args=[], returncode=0, stdout=full_output, stderr="")
        ok, _ = vw._validate_e2e_target_status(with_denials)
        self.assertTrue(ok)

    def test_target_status_validator_requires_resume_markers(self):
        output = (
            "Project Overview\n"
            "Tasks\n"
            "Gate\n"
            "Permission Mode (permission_mode / 操作权限模式): maximum-autonomy\n"
            "Delivery Trust Snapshot\n"
            "Goal: test\n"
            "Stage: 维护\n"
            "Gate/setup status: G11 passed\n"
            "Risk: no open risks yet\n"
            "Evidence: no delivery evidence yet\n"
            "Next action: continue the active task and attach evidence before completion\n"
            "Preset guidance: lite is the recommended first-run default; standard is for team delivery; strict is for regulated/high-risk work\n"
            "Question budget: no more than 3 non-critical questions before snapshot; deferred non-critical fields become assumptions\n"
            "Verification signal: python skills/software-project-governance/infra/verify_workflow.py status\n"
            "No-overclaim boundary: local snapshot only; no official approval, marketplace approval, "
            "universal/full runtime support, or 1.0.0 production-ready claim\n"
        )
        result = subprocess.CompletedProcess(args=[], returncode=0, stdout=output, stderr="")
        ok, _ = vw._validate_e2e_target_status(result)
        self.assertFalse(ok)

    def test_governance_scenario_c_matches_continuous_archive_step_e(self):
        governance = (vw.ROOT / "commands" / "governance.md").read_text(encoding="utf-8")
        init = (vw.ROOT / "commands" / "governance-init.md").read_text(encoding="utf-8")

        required = [
            "持续归档触发检测与执行",
            "WORKFLOW_HOME",
            '`python "$WORKFLOW_HOME/infra/archive.py" migrate --auto --dry-run`',
            '`python "$WORKFLOW_HOME/infra/archive.py" migrate --auto`',
            '`python "$WORKFLOW_HOME/infra/verify_workflow.py" check-archive-integrity`',
            "发布/版本 bump 收尾场景 MUST 阻断完成",
            "无可归档数据",
        ]
        self.assertEqual([needle for needle in required if needle not in governance], [])
        self.assertEqual([needle for needle in required if needle not in init], [])
        forbidden = [
            "python skills/software-project-governance/infra/archive.py",
            "python skills/software-project-governance/infra/verify_workflow.py check-archive-integrity",
        ]
        self.assertEqual([needle for needle in forbidden if needle in governance], [])
        self.assertEqual([needle for needle in forbidden if needle in init], [])


class FirstRunDemoTests(unittest.TestCase):
    """FIX-103: local demo harness asserts first happy path snapshot fields."""

    def test_readme_first_success_path_mentions_demo_snapshot_and_boundaries(self):
        readme = (vw.ROOT / "README.md").read_text(encoding="utf-8")

        english_required = [
            "## 5-Minute Start",
            "The first success path is intentionally small",
            "Delivery Trust Snapshot",
            "python skills/software-project-governance/infra/verify_workflow.py first-run-demo --assert-snapshot",
            "local demo-only check that needs no external credentials",
            "The snapshot is the first trust signal",
            "official approval",
            "marketplace approval",
            "universal/full runtime support",
            "1.0.0 production-ready",
            "**lite**",
            "**standard**",
            "**strict**",
        ]
        chinese_required = [
            "## 5 分钟开始",
            "先拿到一个本地信任信号",
            "Delivery Trust Snapshot",
            "first-run-demo --assert-snapshot",
            "demo path 不需要 external credentials",
            "第一个 trust signal",
            "官方批准",
            "marketplace approval",
            "universal/full runtime support",
            "1.0.0 production-ready",
            "**lite**",
            "**standard**",
            "**strict**",
        ]

        self.assertEqual([needle for needle in english_required if needle not in readme], [])
        self.assertEqual([needle for needle in chinese_required if needle not in readme], [])

    def test_first_run_demo_assert_snapshot_passes(self):
        args = argparse.Namespace(assert_snapshot=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            vw.cmd_first_run_demo(args)

        output = buf.getvalue()
        self.assertIn("First-Run Demo Harness", output)
        self.assertIn("First-Run Demo Result: PASSED", output)
        for marker in [
            "Delivery Trust Snapshot",
            "Unfinished work:",
            "Source facts:",
            "Blocker state:",
            "Auto-continue:",
            "Interrupt boundary:",
            "not found",
            "Goal:",
            "Stage:",
            "Gate/setup status:",
            "Risk:",
            "Evidence:",
            "Next action:",
            "Preset guidance:",
            "Question budget:",
            "Verification signal:",
            "No-overclaim boundary:",
            "local/demo-only",
            "no external credentials",
            "no official approval",
            "marketplace approval",
            "universal/full runtime support",
            "1.0.0 production-ready",
        ]:
            self.assertIn(marker, output)

    def test_first_run_demo_assertion_reports_missing_field(self):
        snapshot = vw.build_first_run_demo_snapshot()
        snapshot.pop("Evidence")

        missing = vw.assert_first_run_demo_snapshot(snapshot)

        self.assertIn("Evidence", missing)
        self.assertIn("Evidence:", missing)


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

    def test_parse_completed_task_ids_accepts_priority_first_rows(self):
        plan = "\n".join([
            "# 计划跟踪",
            "",
            "## 当前活跃事项",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            "| **P1** | FIX-072 | release tooling | AUDIT-100 | 0.35.0 | tests | ✅ 已完成 (2026-05-20) |",
            "| **P1** | FIX-073 | guardrails | AUDIT-100 | 0.35.0 | tests | ⬜ 待实施 |",
        ])
        with tempfile.TemporaryDirectory() as td:
            sp = self._write(Path(td), plan)
            with patch.object(vw, "SAMPLE_PATH", sp):
                completed = vw.parse_completed_task_ids()
                self.assertEqual(completed, {"FIX-072"})

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

    def test_check_governance_check13_empty_governance_logs_do_not_crash(self):
        """FIX-128: Check 13 tolerates newly initialized projects with empty logs."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / ".governance"
            gov.mkdir(parents=True)
            (gov / "plan-tracker.md").write_text("# Plan tracker\n", encoding="utf-8")
            (gov / "decision-log.md").write_text("# Decision log\n", encoding="utf-8")
            (gov / "evidence-log.md").write_text("# Evidence log\n", encoding="utf-8")
            (gov / "risk-log.md").write_text("# Risk log\n", encoding="utf-8")

            with patch.object(vw, "ROOT", root), \
                 patch.object(vw, "SAMPLE_PATH", gov / "plan-tracker.md"), \
                 patch.object(vw, "EVIDENCE_PATH", gov / "evidence-log.md"), \
                 patch.object(vw, "RISK_PATH", gov / "risk-log.md"):
                result = vw.check_sequential_ids()
                output = io.StringIO()
                with redirect_stdout(output):
                    issue_count = vw._print_sequential_id_check(result)

        self.assertEqual(result["dec_ids"], [])
        self.assertEqual(result["evd_ids"], [])
        self.assertEqual(result["risk_ids"], [])
        self.assertEqual(issue_count, 0)
        text = output.getvalue()
        self.assertIn("DEC-IDs: no entries found.", text)
        self.assertIn("EVD-IDs: no entries found.", text)
        self.assertIn("RISK-IDs: no entries found.", text)


class ExternalProjectValidationHarnessTests(unittest.TestCase):
    """FIX-131: external validation runs in a temporary workspace with conservative boundaries."""

    def _target_file_snapshot(self, root):
        snapshot = {}
        for path in sorted(Path(root).rglob("*")):
            if path.is_file():
                snapshot[path.relative_to(root).as_posix()] = path.read_bytes()
        return snapshot

    def _patch_external_validation_commands(self):
        def fake_copy(workspace):
            (workspace / "README.md").write_text("surface\n", encoding="utf-8")
            return ["README.md"]

        def fake_run(workspace, args, timeout=120):
            return {"args": list(args), "exit_code": 0, "stdout_tail": "ok", "stderr_tail": ""}

        return fake_copy, fake_run

    def test_external_validation_rejects_missing_or_empty_target(self):
        with tempfile.TemporaryDirectory() as td:
            empty = Path(td) / "empty"
            empty.mkdir()
            result = vw.run_external_project_validation(empty)

        self.assertFalse(result["pass"])
        self.assertEqual(result["surface_files"], 0)
        self.assertIn("target must be an existing directory", result["issues"][0])
        self.assertIn("No official approval", result["no_overclaim_boundary"])
        self.assertIn("No 1.0.0 production-ready", result["no_overclaim_boundary"])

    def test_external_validation_rejects_workspace_parent_inside_target(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "target"
            nested = target / "nested"
            nested.mkdir(parents=True)
            (target / "app.py").write_text("print('external')\n", encoding="utf-8")

            result_same = vw.run_external_project_validation(target, workspace_parent=target)
            result_nested = vw.run_external_project_validation(target, workspace_parent=nested)

        self.assertFalse(result_same["pass"])
        self.assertFalse(result_nested["pass"])
        self.assertIn("must not be the target directory", result_same["issues"][0])
        self.assertIn("must not be the target directory", result_nested["issues"][0])

    def test_external_validation_runs_expected_command_matrix_without_mutating_target(self):
        calls = []
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            marker = target / "app.py"
            marker.write_text("print('external')\n", encoding="utf-8")

            def fake_copy(workspace):
                (workspace / "README.md").write_text("surface\n", encoding="utf-8")
                return ["README.md"]

            def fake_prepare(workspace):
                calls.append(("prepare", workspace.exists()))

            def fake_run(workspace, args, timeout=120):
                calls.append(("run", tuple(args), timeout, workspace.exists()))
                return {"args": list(args), "exit_code": 0, "stdout_tail": "ok", "stderr_tail": ""}

            with patch.object(vw, "_copy_external_validation_surface", side_effect=fake_copy), \
                 patch.object(vw, "_prepare_external_validation_git", side_effect=fake_prepare), \
                 patch.object(vw, "_run_external_validation_command", side_effect=fake_run), \
                 patch.object(vw, "_extract_skill_version", return_value="0.50.1"):
                result = vw.run_external_project_validation(target, timeout=7)

            self.assertTrue(result["pass"])
            self.assertEqual(result["surface_files"], 1)
            self.assertEqual(marker.read_text(encoding="utf-8"), "print('external')\n")
            self.assertEqual(
                [call[1] for call in calls if call[0] == "run"],
                [tuple(args) for _label, args in vw.EXTERNAL_PROJECT_VALIDATION_COMMANDS],
            )
            self.assertTrue(all(call[2] == 7 for call in calls if call[0] == "run"))
            self.assertIn("No external validation full PASS", result["no_overclaim_boundary"])
            self.assertIn("No RISK-036 closure", result["no_overclaim_boundary"])

    def test_external_validation_writes_minimal_governance_records(self):
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            facts = {
                "target": "C:/external/project",
                "exists": True,
                "is_dir": True,
                "file_count": 1,
                "sample_files": ["src/app.py"],
            }
            with patch.object(vw, "_extract_skill_version", return_value="0.50.1"):
                vw._write_external_validation_governance(workspace, facts)

            plan = (workspace / ".governance/plan-tracker.md").read_text(encoding="utf-8")
            target_json = json.loads(
                (workspace / ".governance/external-validation-target.json").read_text(encoding="utf-8")
            )

        self.assertIn("## 项目配置", plan)
        self.assertIn("## Gate 状态跟踪", plan)
        self.assertIn("工作流版本**: 0.50.1", plan)
        self.assertEqual(target_json["sample_files"], ["src/app.py"])

    def test_external_validation_profile_skips_product_hot_fact_history(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / ".governance"
            gov.mkdir()
            plan = gov / "plan-tracker.md"
            plan.write_text(vw._external_validation_plan_tracker("0.50.1"), encoding="utf-8")
            (gov / "external-validation-target.json").write_text("{}", encoding="utf-8")
            output = io.StringIO()
            with patch.object(vw, "ROOT", root), redirect_stdout(output):
                issues = vw.check_hot_fact_source_consistency(plan)

        self.assertEqual(issues, [])
        self.assertIn("external validation temporary workspace", output.getvalue())

    def test_hot_fact_skip_requires_external_validation_sentinel(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / ".governance"
            gov.mkdir()
            plan = gov / "plan-tracker.md"
            plan.write_text(vw._external_validation_plan_tracker("0.50.1"), encoding="utf-8")
            output = io.StringIO()
            with patch.object(vw, "ROOT", root), redirect_stdout(output):
                issues = vw.check_hot_fact_source_consistency(plan)

        self.assertNotEqual(issues, [])
        self.assertNotIn("skipped for external validation", output.getvalue())

    def test_external_validation_command_timeout_is_structured_failure(self):
        timeout = subprocess.TimeoutExpired(["python", "x.py"], timeout=3, output="partial\n", stderr="slow\n")
        with tempfile.TemporaryDirectory() as td, \
             patch.object(vw.subprocess, "run", side_effect=timeout):
            result = vw._run_external_validation_command(Path(td), ["check-governance"], timeout=3)

        self.assertEqual(result["exit_code"], 124)
        self.assertIn("partial", result["stdout_tail"])
        self.assertIn("timed out", result["stderr_tail"])

    def test_external_validation_reports_target_native_diagnostics_without_mutating_target(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True, text=True)
            (target / "AGENTS.md").write_text(
                "Run python skills/software-project-governance/infra/verify_workflow.py verify\n"
                "Install with cp skills/software-project-governance/infra/hooks/pre-commit .git/hooks/pre-commit\n",
                encoding="utf-8",
            )
            (target / ".git/hooks/pre-commit").write_text(
                "#!/bin/bash\n"
                "# @version: 0.1.0\n"
                "SOURCE_HOOK=\"$REPO_ROOT/skills/software-project-governance/infra/hooks/pre-commit\"\n"
                "COMMIT_MSG=$(cat \"$REPO_ROOT/.git/COMMIT_EDITMSG\")\n"
                "BRIDGE=$(cat \"$REPO_ROOT/.git/GOV_COMMIT_MSG\")\n",
                encoding="utf-8",
            )
            before = self._target_file_snapshot(target)

            fake_copy, fake_run = self._patch_external_validation_commands()
            with patch.object(vw, "_copy_external_validation_surface", side_effect=fake_copy), \
                 patch.object(vw, "_prepare_external_validation_git"), \
                 patch.object(vw, "_run_external_validation_command", side_effect=fake_run), \
                 patch.object(vw, "_extract_skill_version", return_value="0.50.2"):
                result = vw.run_external_project_validation(target, timeout=5)

            after = self._target_file_snapshot(target)
            issue_text = "\n".join(result["issues"])
            diagnostics = result["target_diagnostics"]

        self.assertEqual(after, before)
        self.assertFalse(result["pass"])
        self.assertTrue(any(d["category"] == "target-native-entry" and d["path"] == "AGENTS.md" for d in diagnostics))
        self.assertIn("target-native-entry AGENTS.md", issue_text)
        self.assertIn(".git/hooks/commit-msg", issue_text)
        self.assertIn(".git/hooks/post-commit", issue_text)
        self.assertIn("installed hook @version=0.1.0", issue_text)
        self.assertIn("legacy pre-commit uses COMMIT_EDITMSG or GOV_COMMIT_MSG", issue_text)
        self.assertIn("pre-commit self-upgrade source hardcodes repo-local", issue_text)

    def test_external_validation_accepts_current_target_hooks_and_safe_native_entries(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            subprocess.run(["git", "init"], cwd=target, check=True, capture_output=True, text=True)
            (target / "AGENTS.md").write_text(
                "Use WORKFLOW_HOME to locate the installed governance runtime.\n",
                encoding="utf-8",
            )
            for hook_name in vw.EXTERNAL_PROJECT_REQUIRED_INSTALLED_HOOKS:
                shutil.copyfile(_INFRA_DIR / "hooks" / hook_name, target / ".git/hooks" / hook_name)
            before = self._target_file_snapshot(target)

            fake_copy, fake_run = self._patch_external_validation_commands()
            with patch.object(vw, "_copy_external_validation_surface", side_effect=fake_copy), \
                 patch.object(vw, "_prepare_external_validation_git"), \
                 patch.object(vw, "_run_external_validation_command", side_effect=fake_run), \
                 patch.object(vw, "_extract_skill_version", return_value="0.50.2"):
                result = vw.run_external_project_validation(target, timeout=5)

            after = self._target_file_snapshot(target)

        self.assertEqual(after, before)
        self.assertTrue(result["pass"])
        self.assertEqual(result["issues"], [])
        self.assertFalse([item for item in result["target_diagnostics"] if item["status"] == "FAIL"])
        self.assertTrue(any(item["path"] == ".git/hooks/pre-commit" for item in result["target_diagnostics"]))


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

    def test_manifest_rejects_missing_canonical_pack_registry_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            registry = root / "skills/software-project-governance/core/governance-packs.json"
            registry.parent.mkdir(parents=True)
            registry.write_text("{}", encoding="utf-8")
            manifest = {
                "root_entries": {"files": [], "directories": []},
                "product": {
                    "entries": [
                        {
                            "path": "skills/software-project-governance/core/governance-packs.json",
                            "type": "file",
                        }
                    ],
                    "glob_patterns": [],
                },
                "repo_only": {"entries": [], "glob_patterns": []},
                "canonical_product_artifacts": {"entries": []},
                "cleanup_scope": {"directories": sorted(vw.PLUGIN_SCOPE_DIRS)},
            }
            mp = root / "manifest.json"
            mp.write_text(json.dumps(manifest), encoding="utf-8")

            with patch.object(vw, "ROOT", root), \
                 patch.object(vw, "_git_files", return_value={
                     "skills/software-project-governance/core/governance-packs.json"
                 }):
                result = vw.check_manifest_consistency(mp)

        self.assertFalse(result["pass"])
        self.assertTrue(any("canonical_product_artifacts.entries" in issue for issue in result["artifact_issues"]))

    def test_manifest_rejects_canonical_artifact_not_tracked_by_git(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            registry = root / "skills/software-project-governance/core/governance-packs.json"
            registry.parent.mkdir(parents=True)
            registry.write_text("{}", encoding="utf-8")
            manifest = {
                "root_entries": {"files": [], "directories": []},
                "product": {
                    "entries": [
                        {
                            "path": "skills/software-project-governance/core/governance-packs.json",
                            "type": "file",
                        }
                    ],
                    "glob_patterns": [],
                },
                "repo_only": {"entries": [], "glob_patterns": []},
                "canonical_product_artifacts": {
                    "entries": [
                        {
                            "id": "governance-pack-registry",
                            "path": "skills/software-project-governance/core/governance-packs.json",
                            "type": "file",
                            "required": True,
                            "artifact_role": "pack-registry",
                            "validation_commands": [
                                "python skills/software-project-governance/infra/verify_workflow.py check-governance-packs --fail-on-issues",
                                "python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues",
                            ],
                        }
                    ]
                },
                "cleanup_scope": {"directories": sorted(vw.PLUGIN_SCOPE_DIRS)},
            }
            mp = root / "manifest.json"
            mp.write_text(json.dumps(manifest), encoding="utf-8")

            with patch.object(vw, "ROOT", root), \
                 patch.object(vw, "_git_files", return_value=set()):
                result = vw.check_manifest_consistency(mp)

        self.assertFalse(result["pass"])
        self.assertTrue(any("must be tracked by git" in issue for issue in result["artifact_issues"]))

    def test_manifest_rejects_canonical_artifact_not_explicit_product_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            registry = root / "skills/software-project-governance/core/governance-packs.json"
            registry.parent.mkdir(parents=True)
            registry.write_text("{}", encoding="utf-8")
            manifest = {
                "root_entries": {"files": [], "directories": []},
                "product": {"entries": [], "glob_patterns": []},
                "repo_only": {"entries": [], "glob_patterns": []},
                "canonical_product_artifacts": {
                    "entries": [
                        {
                            "id": "governance-pack-registry",
                            "path": "skills/software-project-governance/core/governance-packs.json",
                            "type": "file",
                            "required": True,
                            "artifact_role": "pack-registry",
                            "validation_commands": [
                                "python skills/software-project-governance/infra/verify_workflow.py check-governance-packs --fail-on-issues",
                                "python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues",
                            ],
                        }
                    ]
                },
                "cleanup_scope": {"directories": sorted(vw.PLUGIN_SCOPE_DIRS)},
            }
            mp = root / "manifest.json"
            mp.write_text(json.dumps(manifest), encoding="utf-8")

            with patch.object(vw, "ROOT", root), \
                 patch.object(vw, "_git_files", return_value={
                     "skills/software-project-governance/core/governance-packs.json"
                 }):
                result = vw.check_manifest_consistency(mp)

        self.assertFalse(result["pass"])
        self.assertTrue(any("must be an explicit product file entry" in issue for issue in result["artifact_issues"]))

    def test_manifest_rejects_pack_registry_artifact_missing_validation_command(self):
        for missing_command in ("check-governance-packs", "check-manifest-consistency"):
            with self.subTest(missing_command=missing_command):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    registry = root / "skills/software-project-governance/core/governance-packs.json"
                    registry.parent.mkdir(parents=True)
                    registry.write_text("{}", encoding="utf-8")
                    commands = [
                        "python skills/software-project-governance/infra/verify_workflow.py check-governance-packs --fail-on-issues",
                        "python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues",
                    ]
                    commands = [command for command in commands if missing_command not in command]
                    manifest = {
                        "root_entries": {"files": [], "directories": []},
                        "product": {
                            "entries": [
                                {
                                    "path": "skills/software-project-governance/core/governance-packs.json",
                                    "type": "file",
                                }
                            ],
                            "glob_patterns": [],
                        },
                        "repo_only": {"entries": [], "glob_patterns": []},
                        "canonical_product_artifacts": {
                            "entries": [
                                {
                                    "id": "governance-pack-registry",
                                    "path": "skills/software-project-governance/core/governance-packs.json",
                                    "type": "file",
                                    "required": True,
                                    "artifact_role": "pack-registry",
                                    "validation_commands": commands,
                                }
                            ]
                        },
                        "cleanup_scope": {"directories": sorted(vw.PLUGIN_SCOPE_DIRS)},
                    }
                    mp = root / "manifest.json"
                    mp.write_text(json.dumps(manifest), encoding="utf-8")

                    with patch.object(vw, "ROOT", root), \
                         patch.object(vw, "_git_files", return_value={
                             "skills/software-project-governance/core/governance-packs.json"
                         }):
                        result = vw.check_manifest_consistency(mp)

                self.assertFalse(result["pass"])
                self.assertTrue(
                    any(
                        f"validation_commands must include `{missing_command}`" in issue
                        for issue in result["artifact_issues"]
                    )
                )

    def _write_cleanup_manifest(self, root, scope_dirs):
        manifest = {
            "version": "test",
            "root_entries": {"files": [], "directories": []},
            "product": {"entries": [], "glob_patterns": []},
            "repo_only": {"entries": [], "glob_patterns": []},
            "cleanup_scope": {"directories": scope_dirs},
            "exclude_from_cleanup": {"entries": [], "user_data_dirs": []},
        }
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest_path

    def test_Cleanup_scope_rejects_invalid_dirs_before_scanning(self):
        invalid_scopes = [
            ["."],
            [".."],
            [""],
            [str(Path(tempfile.gettempdir()).resolve())],
            ["skills/../docs"],
            ["docs"],
        ]
        for scope_dirs in invalid_scopes:
            with self.subTest(scope_dirs=scope_dirs):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    manifest_path = self._write_cleanup_manifest(root, scope_dirs)
                    (root / "docs").mkdir()
                    (root / "docs" / "user-file.md").write_text("must not scan", encoding="utf-8")

                    with patch.object(
                        cleanup_mod,
                        "scan_actual",
                        side_effect=AssertionError("scan_actual must not run for invalid cleanup scope"),
                    ):
                        with self.assertRaises(SystemExit) as cm:
                            cleanup_mod.compute_redundant(manifest_path, root)

                self.assertEqual(cm.exception.code, cleanup_mod.ERR_INVALID_CLEANUP_SCOPE)

    def test_Cleanup_scope_accepts_allowed_subset(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_path = self._write_cleanup_manifest(root, ["skills"])
            skills = root / "skills"
            skills.mkdir()
            (skills / "extra.md").write_text("redundant", encoding="utf-8")

            result = cleanup_mod.compute_redundant(manifest_path, root)

        self.assertEqual(result["cleanup_scope_dirs"], ["skills"])
        self.assertEqual(result["redundant_files"], ["skills/extra.md"])

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
                "本文只定义可执行路由，不注入人格、昵称、风格标签或口号。\n",
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

    def test_warn_only_structural_issues_do_not_block_governance_health(self):
        issues = [
            {
                "type": "evidence_col_mismatch",
                "severity": "WARN",
                "file": ".governance/evidence-log.md",
                "line": 2,
                "detail": "EVD-002: 11 columns (expected 10)",
            },
            {
                "type": "historical_archive_residue",
                "severity": "INFO",
                "file": ".governance/archive/index.md",
                "detail": "archived residue",
            },
        ]

        self.assertEqual(vw.blocking_structural_issues(issues), [])

    def test_error_structural_issues_block_governance_health(self):
        error_issue = {
            "type": "file_missing",
            "file": ".governance/decision-log.md",
            "detail": "decision-log.md not found",
        }
        warn_issue = {
            "type": "evidence_col_mismatch",
            "severity": "WARN",
            "file": ".governance/evidence-log.md",
            "line": 2,
            "detail": "EVD-002: 11 columns (expected 10)",
        }

        self.assertEqual(vw.blocking_structural_issues([warn_issue, error_issue]), [error_issue])

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


def _dated_impact_evidence_row(evd_id, task_id, description, file_location="skills/test.md"):
    return f"| {evd_id} | 2026-06-16 | {task_id} | 架构 | 影响分析 | {description} | {file_location} | Developer | G11 | PASS |"


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

    def test_check_goal_alignment_product_code_delivery_without_impact_type_fails(self):
        """FIX-073: product-code delivery evidence must not no-op when type != 影响分析."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / ".governance"; gov.mkdir(parents=True, exist_ok=True)
            sp = gov / "plan-tracker.md"
            ep = gov / "evidence-log.md"
            sp.write_text("\n".join([
                "# 计划跟踪",
                "## 项目配置",
                "- **项目目标**: 提供一套完整的软件项目治理工作流插件",
                "## 当前活跃事项",
                "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
                "|--------|----|------|------|---------|---------|------|",
                "| **P1** | FIX-073 | guardrails | AUDIT-100 | 0.35.0 | tests | ✅ 已完成 |",
            ]), encoding="utf-8")
            ep.write_text(_evidence_row_generic(
                "EVD-073",
                "FIX-073",
                evd_type="实现",
                description="实现完成但没有目标字段",
                file_location="skills/software-project-governance/infra/verify_workflow.py",
            ), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_goal_alignment()
            self.assertFalse(r["pass"])
            self.assertEqual(len(r["entries"]), 1)
            self.assertEqual(r["entries"][0]["task_id"], "FIX-073")
            self.assertFalse(r["entries"][0]["has_goal"])

    def test_check_goal_alignment_uses_active_hot_tasks_beyond_release_row(self):
        """FIX-073: active hot tasks outside the roadmap row are still guarded."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / ".governance"; gov.mkdir(parents=True, exist_ok=True)
            sp = gov / "plan-tracker.md"
            ep = gov / "evidence-log.md"
            sp.write_text("\n".join([
                "# 计划跟踪",
                "## 项目配置",
                "- **项目目标**: 提供一套完整的软件项目治理工作流插件",
                "## 当前活跃事项",
                "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
                "|--------|----|------|------|---------|---------|------|",
                "| **P1** | FIX-999 | active hot guardrail | AUDIT-100 | 0.35.0 | tests | ✅ 已完成 |",
                "### 最近完成",
                "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
                "| **P1** | FIX-998 | old | AUDIT-100 | 0.34.0 | tests | ✅ 已完成 |",
                "## 版本规划",
                "| 版本 | 状态 | 预计日期 | 核心范围 | 包含 Tier/Layer | 关键交付物 |",
                "| 0.35.0 | 进行中 | 2026-05-14 | scope | FIX-073~074 | delivery |",
            ]), encoding="utf-8")
            ep.write_text(_evidence_row_generic(
                "EVD-999",
                "FIX-999",
                evd_type="实现",
                description="实现完成但没有目标字段",
                file_location="skills/software-project-governance/infra/verify_workflow.py",
            ), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_goal_alignment()
            self.assertFalse(r["pass"])
            self.assertEqual(len(r["entries"]), 1)
            self.assertEqual(r["entries"][0]["task_id"], "FIX-999")

    def test_check_goal_alignment_accepts_fullwidth_colon(self):
        with tempfile.TemporaryDirectory() as td:
            evidence_rows = [
                _impact_evidence_row("EVD-005", "TASK-005",
                                     f"目标对齐：{self.GOAL_TEXT} 用户影响：获得=自动生效, 感知=无, 体验变化=否, 迁移指南=不需要"),
            ]
            sp, ep = self._setup(td, evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_goal_alignment()
            self.assertTrue(r["pass"])
            self.assertEqual(r["entries"][0]["status"], "PASS")


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

    def test_check_user_impact_product_code_delivery_without_impact_type_fails(self):
        """FIX-073: product-code delivery evidence must carry 用户影响 even when type != 影响分析."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / ".governance"; gov.mkdir(parents=True, exist_ok=True)
            sp = gov / "plan-tracker.md"
            ep = gov / "evidence-log.md"
            sp.write_text("\n".join([
                "# 计划跟踪",
                "## 当前活跃事项",
                "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
                "|--------|----|------|------|---------|---------|------|",
                "| **P1** | FIX-073 | guardrails | AUDIT-100 | 0.35.0 | tests | ✅ 已完成 |",
            ]), encoding="utf-8")
            ep.write_text(_evidence_row_generic(
                "EVD-073",
                "FIX-073",
                evd_type="实现",
                description="目标对齐: enough target alignment text for this product code change",
                file_location="skills/software-project-governance/infra/verify_workflow.py",
            ), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_user_impact()
            self.assertFalse(r["pass"])
            self.assertEqual(len(r["entries"]), 1)
            self.assertEqual(r["entries"][0]["status"], "FAIL")
            self.assertIn("缺少 用户影响", r["entries"][0]["issues"][0])

    def test_check_user_impact_uses_active_hot_tasks_beyond_release_row(self):
        """FIX-073: user-impact guardrail covers active hot tasks outside roadmap row."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / ".governance"; gov.mkdir(parents=True, exist_ok=True)
            sp = gov / "plan-tracker.md"
            ep = gov / "evidence-log.md"
            sp.write_text("\n".join([
                "# 计划跟踪",
                "## 当前活跃事项",
                "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
                "|--------|----|------|------|---------|---------|------|",
                "| **P1** | FIX-999 | active hot guardrail | AUDIT-100 | 0.35.0 | tests | ✅ 已完成 |",
                "### 最近完成",
                "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
                "| **P1** | FIX-998 | old | AUDIT-100 | 0.34.0 | tests | ✅ 已完成 |",
                "## 版本规划",
                "| 版本 | 状态 | 预计日期 | 核心范围 | 包含 Tier/Layer | 关键交付物 |",
                "| 0.35.0 | 进行中 | 2026-05-14 | scope | FIX-073~074 | delivery |",
            ]), encoding="utf-8")
            ep.write_text(_evidence_row_generic(
                "EVD-999",
                "FIX-999",
                evd_type="实现",
                description="目标对齐: enough target alignment text for this product code change",
                file_location="skills/software-project-governance/infra/verify_workflow.py",
            ), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_user_impact()
            self.assertFalse(r["pass"])
            self.assertEqual(len(r["entries"]), 1)
            self.assertEqual(r["entries"][0]["task_id"], "FIX-999")
            self.assertEqual(r["entries"][0]["status"], "FAIL")


class FactGroundingTests(unittest.TestCase):
    """FIX-080: current product-code evidence must carry fact grounding."""

    def _setup(self, tmpdir, evidence_lines):
        root = Path(tmpdir)
        gov = root / ".governance"; gov.mkdir(parents=True, exist_ok=True)
        sp = gov / "plan-tracker.md"
        ep = gov / "evidence-log.md"
        sp.write_text("\n".join([
            "# 计划跟踪",
            "## 项目配置",
            "- **项目目标**: 提供一套完整的软件项目治理工作流插件",
            "## 当前活跃事项",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            "| **P0** | FIX-080 | fact guard | 用户反馈 | 0.37.0 | tests | 🔄 进行中 |",
            "## 版本规划",
            "| 版本 | 状态 | 预计日期 | 核心范围 | 包含 Tier/Layer | 关键交付物 |",
            "| 0.37.0 | 进行中 | 2026-05-22 | fact guard | FIX-080 | delivery |",
        ]), encoding="utf-8")
        ep.write_text("\n".join(evidence_lines), encoding="utf-8")
        return sp, ep

    def test_check_fact_grounding_requires_fact_basis(self):
        with tempfile.TemporaryDirectory() as td:
            sp, ep = self._setup(td, [
                _impact_evidence_row(
                    "EVD-080", "FIX-080",
                    "目标对齐: 提升治理工作流证据可信度，避免无事实闭环。 "
                    "用户影响: 获得=plugin update, 感知=CHANGELOG, 体验变化=否, 迁移指南=不需要",
                    "skills/software-project-governance/infra/verify_workflow.py",
                )
            ])
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_fact_grounding()
            self.assertFalse(r["pass"])
            self.assertEqual(r["entries"][0]["status"], "FAIL")
            self.assertIn("缺少 事实依据", r["entries"][0]["issues"][0])

    def test_check_fact_grounding_accepts_specific_facts(self):
        with tempfile.TemporaryDirectory() as td:
            sp, ep = self._setup(td, [
                _impact_evidence_row(
                    "EVD-081", "FIX-080",
                    "事实依据: verify_workflow.py check_fact_grounding implementation and FactGroundingTests PASS. "
                    "目标对齐: 提升治理工作流证据可信度，避免无事实闭环。 "
                    "用户影响: 获得=plugin update, 感知=CHANGELOG, 体验变化=否, 迁移指南=不需要",
                    "skills/software-project-governance/infra/verify_workflow.py",
                )
            ])
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_fact_grounding()
            self.assertTrue(r["pass"])
            self.assertEqual(r["entries"][0]["status"], "PASS")
            self.assertTrue(r["entries"][0]["has_fact_basis"])

    def test_check_fact_grounding_rejects_speculation_terms(self):
        with tempfile.TemporaryDirectory() as td:
            sp, ep = self._setup(td, [
                _impact_evidence_row(
                    "EVD-082", "FIX-080",
                    "事实依据: verify_workflow.py changed and targeted tests were run. "
                    "我猜测这个已经完成。目标对齐: 提升治理工作流证据可信度，避免无事实闭环。 "
                    "用户影响: 获得=plugin update, 感知=CHANGELOG, 体验变化=否, 迁移指南=不需要",
                    "skills/software-project-governance/infra/verify_workflow.py",
                )
            ])
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_fact_grounding()
            self.assertFalse(r["pass"])
            self.assertIn("含未落地推断词", r["entries"][0]["issues"][0])


class StructuredEvidenceTests(unittest.TestCase):
    """FIX-083: current product-code evidence must carry machine-readable facts."""

    def _setup(self, tmpdir, evidence_lines):
        root = Path(tmpdir)
        gov = root / ".governance"; gov.mkdir(parents=True, exist_ok=True)
        sp = gov / "plan-tracker.md"
        ep = gov / "evidence-log.md"
        sp.write_text("\n".join([
            "# 计划跟踪",
            "## 项目配置",
            "- **项目目标**: 提供一套完整的软件项目治理工作流插件",
            "## 当前活跃事项",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            "| **P0** | FIX-083 | structured evidence | 用户反馈 | 0.38.0 | tests | 🔄 进行中 |",
            "## 版本规划",
            "| 版本 | 状态 | 预计日期 | 核心范围 | 包含 Tier/Layer | 关键交付物 |",
            "| 0.38.0 | 进行中 | 2026-05-23 | structured evidence | FIX-083 | delivery |",
        ]), encoding="utf-8")
        ep.write_text("\n".join(evidence_lines), encoding="utf-8")
        return sp, ep

    def _payload(self, **overrides):
        payload = {
            "commands": [
                {
                    "cmd": "python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues",
                    "exit_code": 0,
                    "summary": "Governance health passed with zero issues.",
                    "log_path": "terminal output",
                }
            ],
            "files_changed": [
                "skills/software-project-governance/infra/verify_workflow.py",
                "skills/software-project-governance/infra/tests/test_verify_workflow.py",
            ],
            "diff_summary": "Added structured evidence parsing and guardrail tests.",
            "review": {"conclusion": "APPROVED", "reviewer": "Code Reviewer"},
        }
        payload.update(overrides)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def _row(self, structured_fact):
        return _impact_evidence_row(
            "EVD-083",
            "FIX-083",
            f"事实依据: structured evidence validation was implemented and tested. "
            f"结构化事实: {structured_fact} "
            f"目标对齐: 结构化证据让治理闭环从自然语言叙述变成可机器检查的事实链。 "
            f"用户影响: 获得=plugin update, 感知=check-governance, 体验变化=正向, 迁移指南=不需要",
            "skills/software-project-governance/infra/verify_workflow.py",
        )

    def _delivery_row(self, description, file_location="validation commands"):
        return (
            f"| EVD-085 | FIX-083 | 维护 | 修复闭环 | {description} | {file_location} | "
            f"Developer | 2026-05-23 | G11 | 完成 |"
        )

    def test_structured_evidence_accepts_valid_payload(self):
        with tempfile.TemporaryDirectory() as td:
            sp, ep = self._setup(td, [self._row(self._payload())])
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_structured_evidence()
            self.assertTrue(r["pass"])
            self.assertEqual(r["entries"][0]["status"], "PASS")
            self.assertEqual(r["entries"][0]["commands"], 1)

    def test_structured_evidence_requires_payload(self):
        with tempfile.TemporaryDirectory() as td:
            sp, ep = self._setup(td, [_impact_evidence_row(
                "EVD-084",
                "FIX-083",
                "事实依据: files and tests. 目标对齐: 结构化证据让治理闭环更可信。 "
                "用户影响: 获得=plugin update, 感知=check-governance, 体验变化=正向, 迁移指南=不需要",
                "skills/software-project-governance/infra/verify_workflow.py",
            )])
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_structured_evidence()
            self.assertFalse(r["pass"])
            self.assertIn("缺少 结构化事实", r["entries"][0]["issues"][0])

    def test_structured_evidence_rejects_missing_exit_code(self):
        with tempfile.TemporaryDirectory() as td:
            payload = json.loads(self._payload())
            payload["commands"][0].pop("exit_code")
            sp, ep = self._setup(td, [self._row(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))])
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_structured_evidence()
            self.assertFalse(r["pass"])
            self.assertTrue(any("exit_code" in issue for issue in r["entries"][0]["issues"]))

    def test_structured_evidence_rejects_secret_like_values(self):
        with tempfile.TemporaryDirectory() as td:
            payload = json.loads(self._payload())
            payload["secret"] = "abc123"
            payload["commands"] = [{
                "cmd": "curl https://example.test",
                "exit_code": 0,
                "summary": "token=abc123 was printed",
            }]
            sp, ep = self._setup(td, [self._row(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))])
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_structured_evidence()
            self.assertFalse(r["pass"])
            self.assertTrue(any("secret/token/password" in issue for issue in r["entries"][0]["issues"]))

    def test_structured_evidence_checks_current_release_delivery_without_path_location(self):
        with tempfile.TemporaryDirectory() as td:
            description = (
                f"事实依据: product-code delivery evidence used generic locations. "
                f"结构化事实: {self._payload()} "
                f"目标对齐: 结构化证据让当前版本产品代码闭环不能因证据位置笼统而空跑。 "
                f"用户影响: 获得=plugin update, 感知=check-governance, 体验变化=正向, 迁移指南=不需要"
            )
            sp, ep = self._setup(td, [self._delivery_row(description)])
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_structured_evidence()
            self.assertTrue(r["pass"])
            self.assertEqual(len(r["entries"]), 1)
            self.assertEqual(r["entries"][0]["task_id"], "FIX-083")

    def test_structured_evidence_rejects_current_release_delivery_without_payload_even_when_location_is_generic(self):
        with tempfile.TemporaryDirectory() as td:
            description = (
                "事实依据: product-code delivery evidence used generic locations. "
                "目标对齐: 结构化证据让当前版本产品代码闭环不能因证据位置笼统而空跑。 "
                "用户影响: 获得=plugin update, 感知=check-governance, 体验变化=正向, 迁移指南=不需要"
            )
            sp, ep = self._setup(td, [self._delivery_row(description)])
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_structured_evidence()
            self.assertFalse(r["pass"])
            self.assertIn("缺少 结构化事实", r["entries"][0]["issues"][0])

    def test_structured_evidence_allows_shell_pipeline_inside_json_command(self):
        with tempfile.TemporaryDirectory() as td:
            payload = json.loads(self._payload())
            payload["commands"][0]["cmd"] = "git diff --name-only | rg verify_workflow"
            sp, ep = self._setup(td, [self._row(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))])
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_structured_evidence()
            self.assertTrue(r["pass"])
            self.assertEqual(r["entries"][0]["commands"], 1)

    def test_structured_evidence_allows_markdown_code_pipe_before_json(self):
        with tempfile.TemporaryDirectory() as td:
            description = (
                f"事实依据: reviewer covered Markdown inline `|` before structured JSON. "
                f"结构化事实: {self._payload()} "
                f"目标对齐: 结构化证据解析不能被证据说明里的 inline pipe 干扰。 "
                f"用户影响: 获得=plugin update, 感知=check-governance, 体验变化=正向, 迁移指南=不需要"
            )
            sp, ep = self._setup(td, [self._delivery_row(description)])
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_structured_evidence()
            self.assertTrue(r["pass"])
            self.assertEqual(r["entries"][0]["commands"], 1)

    def test_structured_evidence_extracts_nested_json_and_braces_in_strings(self):
        with tempfile.TemporaryDirectory() as td:
            payload = json.loads(self._payload())
            payload["commands"][0]["summary"] = "Rendered output contained literal braces {ok} and nested metadata."
            payload["metadata"] = {"nested": {"result": "passed"}}
            sp, ep = self._setup(td, [self._row(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))])
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_structured_evidence()
            self.assertTrue(r["pass"])

    def test_structured_evidence_skips_inline_field_name_before_payload(self):
        with tempfile.TemporaryDirectory() as td:
            description = (
                f"事实依据: docs mention `结构化事实:` before the payload. "
                f"结构化事实: {self._payload()} "
                f"目标对齐: 结构化证据解析应跳过说明文字中的字段名并读取真实 JSON。 "
                f"用户影响: 获得=plugin update, 感知=check-governance, 体验变化=正向, 迁移指南=不需要"
            )
            sp, ep = self._setup(td, [self._delivery_row(description)])
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_structured_evidence()
            self.assertTrue(r["pass"])


class ExecutionPacketTests(unittest.TestCase):
    """FIX-084: active P0/P1 tasks need short AI execution packets."""

    def _setup_plan(self, tmpdir, rows):
        root = Path(tmpdir)
        gov = root / ".governance"; gov.mkdir(parents=True, exist_ok=True)
        sp = gov / "plan-tracker.md"
        sp.write_text("\n".join([
            "# 计划跟踪",
            "## 当前活跃事项",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            *rows,
            "### 最近完成（本会话提交窗口）",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "| **P0** | FIX-000 | old | x | 0.1.0 | done | ✅ 已完成 |",
        ]), encoding="utf-8")
        return root, sp, gov / "execution-packets.json"

    def test_execution_packet_missing_file_fails_for_active_p0_p1(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-084 | AI packet | DEC-068 | 0.38.0 | packet command | 📋 待启动 |",
                "| **P2** | FIX-999 | optional | DEC-068 | 0.38.0 | optional | 📋 待启动 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_execution_packets(packet_path)
            self.assertFalse(r["pass"])
            self.assertEqual(r["required_tasks"], ["FIX-084"])
            self.assertEqual(r["missing"], ["FIX-084"])

    def test_execution_packet_generated_payload_passes(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-084 | AI packet | DEC-068 | 0.38.0 | packet command | 📋 待启动 |",
                "| **P1** | FIX-086 | projection sync | DEC-068 | 0.38.0 | sync guard | 🔄 进行中 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_execution_packets(packet_path)
            self.assertTrue(r["pass"])
            self.assertEqual(r["required_tasks"], ["FIX-084", "FIX-086"])
            self.assertEqual([e["status"] for e in r["entries"]], ["PASS", "PASS"])

    def test_execution_packet_invalid_schema_fails(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-084 | AI packet | DEC-068 | 0.38.0 | packet command | 📋 待启动 |",
            ])
            packet_path.write_text(json.dumps({
                "version": 1,
                "packets": {
                    "FIX-084": {
                        "task_id": "FIX-084",
                        "goal": "implement packet check",
                        "allowed_change_scope": ["any file"],
                        "required_evidence": ["validation output only"],
                        "next_commands": ["python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -v"],
                        "done_definition": ["tests passed"],
                    }
                },
            }), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_execution_packets(packet_path)
            self.assertFalse(r["pass"])
            issues = " ".join(r["entries"][0]["issues"])
            self.assertIn("too broad", issues)
            self.assertIn("事实依据", issues)
            self.assertIn("independent review", issues)

    def test_completed_tasks_do_not_require_execution_packet(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-084 | AI packet | DEC-068 | 0.38.0 | packet command | ✅ 已完成 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_execution_packets(packet_path)
            self.assertTrue(r["pass"])
            self.assertEqual(r["required_tasks"], [])

    def test_unfinished_status_still_requires_execution_packet(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-084 | AI packet | DEC-068 | 0.38.0 | packet command | 未完成 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_execution_packets(packet_path)
            self.assertFalse(r["pass"])
            self.assertEqual(r["required_tasks"], ["FIX-084"])
            self.assertEqual(r["missing"], ["FIX-084"])

    def test_execution_packet_cli_reconfigures_stdout_for_unicode(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-084 | AI packet | DEC-068 | 0.38.0 | packet command | 📋 待启动 |",
            ])
            class FakeStdout(io.StringIO):
                def __init__(self):
                    super().__init__()
                    self.reconfigured = False

                def reconfigure(self, **kwargs):
                    self.reconfigured = True
                    self.kwargs = kwargs

            fake_stdout = FakeStdout()
            args = argparse.Namespace(write=False, task=["FIX-084"])
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EXECUTION_PACKET_PATH", packet_path), \
                 patch.object(vw.sys, "stdout", fake_stdout):
                vw.cmd_execution_packet(args)
            self.assertTrue(fake_stdout.reconfigured)
            self.assertEqual(fake_stdout.kwargs["encoding"], "utf-8")
            self.assertIn("FIX-084", fake_stdout.getvalue())


class ProductSuccessContractTests(unittest.TestCase):
    """FIX-088: active P0/P1 tasks need Product Success Contracts."""

    def _setup_plan(self, tmpdir, rows):
        root = Path(tmpdir)
        gov = root / ".governance"; gov.mkdir(parents=True, exist_ok=True)
        sp = gov / "plan-tracker.md"
        sp.write_text("\n".join([
            "# 计划跟踪",
            "## 当前活跃事项",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            *rows,
            "### 最近完成（本会话提交窗口）",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "| **P0** | FIX-000 | old | x | 0.1.0 | done | ✅ 已完成 |",
        ]), encoding="utf-8")
        return root, sp, gov / "execution-packets.json"

    def _valid_contract(self):
        return {
            "user": "AI-assisted product owner using the governance workflow for release planning",
            "job_to_be_done": "Keep AI coding work tied to explicit user outcomes before implementation starts",
            "non_goals": [
                "Do not expand the task into unrelated release automation changes",
                "Do not treat evidence-log updates as a substitute for user-visible quality",
            ],
            "success_metrics": [
                "User-visible acceptance scenario is captured for the active task before code changes continue",
                "Runnable E2E validation command passes and proves the acceptance scenario is still satisfied",
            ],
            "competitive_baseline": "Mature software teams require explicit acceptance criteria and validation before implementation closure",
            "done_definition": [
                "Product success evidence is recorded with concrete facts",
                "Independent review confirms the user outcome is not replaced by process completion",
            ],
        }

    def test_generated_execution_packet_contains_failing_product_success_scaffold(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-088 | Product Success Contract | DEC-069 | 0.39.0 | template and check | 📋 待启动 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_product_success_contracts(packet_path)
            self.assertFalse(r["pass"])
            contract = payload["packets"]["FIX-088"]["product_success_contract"]
            self.assertIn("user", contract)
            self.assertIn("success_metrics", contract)
            self.assertTrue(any("non-placeholder" in issue for issue in r["entries"][0]["issues"]))

    def test_explicit_product_success_contract_passes(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-088 | Product Success Contract | DEC-069 | 0.39.0 | template and check | 📋 待启动 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            payload["packets"]["FIX-088"]["product_success_contract"] = self._valid_contract()
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_product_success_contracts(packet_path)
            self.assertTrue(r["pass"])

    def test_missing_product_success_contract_fails(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-088 | Product Success Contract | DEC-069 | 0.39.0 | template and check | 📋 待启动 |",
            ])
            packet_path.write_text(json.dumps({
                "version": 1,
                "packets": {
                    "FIX-088": {
                        "task_id": "FIX-088",
                        "goal": "implement product success contract",
                        "allowed_change_scope": ["limited scope"],
                        "required_evidence": ["事实依据 and 结构化事实"],
                        "next_commands": ["python test.py"],
                        "done_definition": ["Review APPROVED"],
                    }
                },
            }), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_product_success_contracts(packet_path)
            self.assertFalse(r["pass"])
            self.assertIn("missing product_success_contract", r["entries"][0]["issues"])

    def test_product_success_contract_rejects_empty_metrics(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-088 | Product Success Contract | DEC-069 | 0.39.0 | template and check | 📋 待启动 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            payload["packets"]["FIX-088"]["product_success_contract"] = self._valid_contract()
            payload["packets"]["FIX-088"]["product_success_contract"]["success_metrics"] = []
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_product_success_contracts(packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("success_metrics" in issue for issue in r["entries"][0]["issues"]))

    def test_product_success_contract_rejects_placeholders(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-088 | Product Success Contract | DEC-069 | 0.39.0 | template and check | 📋 待启动 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            payload["packets"]["FIX-088"]["product_success_contract"] = self._valid_contract()
            payload["packets"]["FIX-088"]["product_success_contract"]["user"] = "TBD"
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_product_success_contracts(packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("user" in issue for issue in r["entries"][0]["issues"]))

    def test_product_success_contract_rejects_process_only_metrics(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-088 | Product Success Contract | DEC-069 | 0.39.0 | template and check | 📋 待启动 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            payload["packets"]["FIX-088"]["product_success_contract"] = self._valid_contract()
            payload["packets"]["FIX-088"]["product_success_contract"]["success_metrics"] = [
                "check-governance --fail-on-issues passes",
                "evidence-log includes review evidence",
            ]
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_product_success_contracts(packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("process-only" in issue for issue in r["entries"][0]["issues"]))


class ExecutableAcceptanceContractTests(unittest.TestCase):
    """FIX-089: active P0/P1 tasks need runnable acceptance contracts."""

    def _setup_plan(self, tmpdir, rows):
        root = Path(tmpdir)
        gov = root / ".governance"; gov.mkdir(parents=True, exist_ok=True)
        sp = gov / "plan-tracker.md"
        sp.write_text("\n".join([
            "# 计划跟踪",
            "## 当前活跃事项",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            *rows,
            "### 最近完成（本会话提交窗口）",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "| **P0** | FIX-000 | old | x | 0.1.0 | done | ✅ 已完成 |",
        ]), encoding="utf-8")
        return root, sp, gov / "execution-packets.json"

    def _valid_acceptance_contract(self):
        return {
            "scenario": "User-visible acceptance scenario proves an active task cannot close without runnable validation",
            "command": "python skills/software-project-governance/infra/verify_workflow.py check-acceptance-contracts --fail-on-issues",
            "expected_output": "Result: PASSED and active acceptance contracts are ready",
            "last_run": {
                "status": "PASS",
                "exit_code": 0,
                "summary": "Acceptance command passed for the active task fixture",
            },
            "demo_evidence": "CLI output shows PASS for the active task acceptance contract",
        }

    def test_generated_execution_packet_contains_failing_acceptance_scaffold(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-089 | Executable Acceptance Contract | FIX-088 | 0.39.0 | acceptance map | 📋 待启动 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_acceptance_contracts(packet_path)
            self.assertFalse(r["pass"])
            self.assertIn("acceptance_contract", payload["packets"]["FIX-089"])
            self.assertTrue(any("non-placeholder" in issue for issue in r["entries"][0]["issues"]))

    def test_explicit_acceptance_contract_passes(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-089 | Executable Acceptance Contract | FIX-088 | 0.39.0 | acceptance map | 📋 待启动 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            payload["packets"]["FIX-089"]["acceptance_contract"] = self._valid_acceptance_contract()
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_acceptance_contracts(packet_path)
            self.assertTrue(r["pass"])

    def test_missing_acceptance_contract_fails(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-089 | Executable Acceptance Contract | FIX-088 | 0.39.0 | acceptance map | 📋 待启动 |",
            ])
            packet_path.write_text(json.dumps({
                "version": 1,
                "packets": {"FIX-089": {"task_id": "FIX-089", "goal": "acceptance contract"}},
            }), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_acceptance_contracts(packet_path)
            self.assertFalse(r["pass"])
            self.assertIn("missing acceptance_contract", r["entries"][0]["issues"])

    def test_acceptance_contract_rejects_non_runnable_command(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-089 | Executable Acceptance Contract | FIX-088 | 0.39.0 | acceptance map | 📋 待启动 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            payload["packets"]["FIX-089"]["acceptance_contract"] = self._valid_acceptance_contract()
            payload["packets"]["FIX-089"]["acceptance_contract"]["command"] = "manual reviewer looks at the prose"
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_acceptance_contracts(packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("runnable validation command" in issue for issue in r["entries"][0]["issues"]))

    def test_acceptance_contract_rejects_review_check_keyword_bypass(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-089 | Executable Acceptance Contract | FIX-088 | 0.39.0 | acceptance map | 📋 待启动 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            payload["packets"]["FIX-089"]["acceptance_contract"] = self._valid_acceptance_contract()
            payload["packets"]["FIX-089"]["acceptance_contract"]["command"] = "review check passed in prose, no runnable command"
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_acceptance_contracts(packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("runnable validation command" in issue for issue in r["entries"][0]["issues"]))

    def test_acceptance_contract_rejects_failed_last_run(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-089 | Executable Acceptance Contract | FIX-088 | 0.39.0 | acceptance map | 📋 待启动 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            payload["packets"]["FIX-089"]["acceptance_contract"] = self._valid_acceptance_contract()
            payload["packets"]["FIX-089"]["acceptance_contract"]["last_run"] = {
                "status": "FAIL",
                "exit_code": 1,
                "summary": "Command failed",
            }
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_acceptance_contracts(packet_path)
            self.assertFalse(r["pass"])
            issues = " ".join(r["entries"][0]["issues"])
            self.assertIn("status must be PASS", issues)
            self.assertIn("exit_code must be 0", issues)

    def test_pending_acceptance_contract_allows_not_run_yet(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-090 | Quality Budget Gate | FIX-088 | 0.39.0 | quality budget | 📋 待实施 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            contract = self._valid_acceptance_contract()
            contract["last_run"] = {
                "status": "NOT_RUN_YET",
                "exit_code": None,
                "summary": "Planned task has a concrete acceptance command but is not implemented yet",
            }
            payload["packets"]["FIX-090"]["acceptance_contract"] = contract
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_acceptance_contracts(packet_path)
            self.assertTrue(r["pass"])


class QualityBudgetTests(unittest.TestCase):
    """FIX-090: active P0/P1 tasks need measurable quality budgets."""

    def _setup_plan(self, tmpdir, rows):
        root = Path(tmpdir)
        gov = root / ".governance"; gov.mkdir(parents=True, exist_ok=True)
        sp = gov / "plan-tracker.md"
        sp.write_text("\n".join([
            "# 计划跟踪",
            "## 当前活跃事项",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            *rows,
            "### 最近完成（本会话提交窗口）",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "| **P0** | FIX-000 | old | x | 0.1.0 | done | ✅ 已完成 |",
        ]), encoding="utf-8")
        return root, sp, gov / "execution-packets.json"

    def _valid_quality_budget(self, status="PASS"):
        return {
            "dimensions": {
                dimension: {
                    "threshold": f"{dimension} threshold protects the affected user outcome",
                    "validation": "python skills/software-project-governance/infra/verify_workflow.py check-quality-budget --fail-on-issues",
                    "status": status,
                    "evidence": f"{dimension} evidence summary is recorded with a concrete result",
                    "exception": "",
                }
                for dimension in vw.QUALITY_BUDGET_DIMENSIONS
            }
        }

    def test_generated_execution_packet_contains_failing_quality_budget_scaffold(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-090 | Quality Budget Gate | FIX-088 | 0.39.0 | quality budget | 📋 待启动 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_quality_budget(packet_path)
            self.assertFalse(r["pass"])
            self.assertIn("quality_budget", payload["packets"]["FIX-090"])
            self.assertTrue(any("non-placeholder" in issue or "status" in issue for issue in r["entries"][0]["issues"]))

    def test_explicit_quality_budget_passes(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-090 | Quality Budget Gate | FIX-088 | 0.39.0 | quality budget | 📋 待启动 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            payload["packets"]["FIX-090"]["quality_budget"] = self._valid_quality_budget()
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_quality_budget(packet_path)
            self.assertTrue(r["pass"])

    def test_missing_quality_budget_fails(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-090 | Quality Budget Gate | FIX-088 | 0.39.0 | quality budget | 📋 待启动 |",
            ])
            packet_path.write_text(json.dumps({
                "version": 1,
                "packets": {"FIX-090": {"task_id": "FIX-090", "goal": "quality budget"}},
            }), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_quality_budget(packet_path)
            self.assertFalse(r["pass"])
            self.assertIn("missing quality_budget", r["entries"][0]["issues"])

    def test_quality_budget_rejects_missing_dimension(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-090 | Quality Budget Gate | FIX-088 | 0.39.0 | quality budget | 📋 待启动 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            budget = self._valid_quality_budget()
            del budget["dimensions"]["security"]
            payload["packets"]["FIX-090"]["quality_budget"] = budget
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_quality_budget(packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("missing dimension" in issue and "security" in issue for issue in r["entries"][0]["issues"]))

    def test_quality_budget_rejects_invalid_dimension(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-090 | Quality Budget Gate | FIX-088 | 0.39.0 | quality budget | 📋 待启动 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            budget = self._valid_quality_budget()
            budget["dimensions"]["delight"] = {
                "threshold": "Delight is not one of the required quality budget dimensions",
                "validation": "python skills/software-project-governance/infra/verify_workflow.py check-quality-budget --fail-on-issues",
                "status": "PASS",
                "evidence": "Invalid dimension evidence should not be accepted",
                "exception": "",
            }
            payload["packets"]["FIX-090"]["quality_budget"] = budget
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_quality_budget(packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("dimension invalid" in issue and "delight" in issue for issue in r["entries"][0]["issues"]))

    def test_quality_budget_list_form_passes(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-090 | Quality Budget Gate | FIX-088 | 0.39.0 | quality budget | 📋 待启动 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            budget = self._valid_quality_budget()
            budget["dimensions"] = [
                {"dimension": dimension, **payload}
                for dimension, payload in budget["dimensions"].items()
            ]
            payload["packets"]["FIX-090"]["quality_budget"] = budget
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_quality_budget(packet_path)
            self.assertTrue(r["pass"])

    def test_quality_budget_rejects_failed_dimension_status(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-090 | Quality Budget Gate | FIX-088 | 0.39.0 | quality budget | 🔄 进行中 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            budget = self._valid_quality_budget()
            budget["dimensions"]["performance"]["status"] = "FAIL"
            payload["packets"]["FIX-090"]["quality_budget"] = budget
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_quality_budget(packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("performance.status" in issue for issue in r["entries"][0]["issues"]))

    def test_quality_budget_exemption_requires_exception(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-090 | Quality Budget Gate | FIX-088 | 0.39.0 | quality budget | 🔄 进行中 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            budget = self._valid_quality_budget()
            budget["dimensions"]["accessibility"]["status"] = "EXEMPT"
            payload["packets"]["FIX-090"]["quality_budget"] = budget
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_quality_budget(packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("accessibility.exception" in issue for issue in r["entries"][0]["issues"]))

    def test_in_progress_quality_budget_rejects_not_run_yet(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-090 | Quality Budget Gate | FIX-088 | 0.39.0 | quality budget | 🔄 进行中 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            payload["packets"]["FIX-090"]["quality_budget"] = self._valid_quality_budget(status="NOT_RUN_YET")
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_quality_budget(packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("status must be PASS" in issue for issue in r["entries"][0]["issues"]))

    def test_waiting_to_start_quality_budget_rejects_not_run_yet(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-090 | Quality Budget Gate | FIX-088 | 0.39.0 | quality budget | 📋 待启动 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            payload["packets"]["FIX-090"]["quality_budget"] = self._valid_quality_budget(status="NOT_RUN_YET")
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_quality_budget(packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("status must be PASS" in issue for issue in r["entries"][0]["issues"]))

    def test_quality_budget_rejects_review_prose_only_budget(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P0** | FIX-090 | Quality Budget Gate | FIX-088 | 0.39.0 | quality budget | 🔄 进行中 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            budget = self._valid_quality_budget()
            for dimension in vw.QUALITY_BUDGET_DIMENSIONS:
                budget["dimensions"][dimension]["threshold"] = "quality is okay"
                budget["dimensions"][dimension]["validation"] = "review artifact says okay"
                budget["dimensions"][dimension]["evidence"] = "review says good"
            payload["packets"]["FIX-090"]["quality_budget"] = budget
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_quality_budget(packet_path)
            self.assertFalse(r["pass"])
            issues = " ".join(r["entries"][0]["issues"])
            self.assertIn("review/prose-only", issues)
            self.assertIn("validation must include", issues)

    def test_pending_quality_budget_allows_not_run_yet(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P1** | FIX-091 | Vertical Slice Delivery Packets | FIX-090 | 0.39.0 | slices | 📋 待实施 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            payload["packets"]["FIX-091"]["quality_budget"] = self._valid_quality_budget(status="NOT_RUN_YET")
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_quality_budget(packet_path)
            self.assertTrue(r["pass"])


class VerticalSliceTests(unittest.TestCase):
    """FIX-091: active P0/P1 tasks need user-visible vertical slices."""

    def _setup_plan(self, tmpdir, rows):
        root = Path(tmpdir)
        gov = root / ".governance"; gov.mkdir(parents=True, exist_ok=True)
        sp = gov / "plan-tracker.md"
        sp.write_text("\n".join([
            "# 计划跟踪",
            "## 当前活跃事项",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            *rows,
            "### 最近完成（本会话提交窗口）",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "| **P0** | FIX-000 | old | x | 0.1.0 | done | ✅ 已完成 |",
        ]), encoding="utf-8")
        return root, sp, gov / "execution-packets.json"

    def _valid_vertical_slice(self, status="PASS"):
        return {
            "user_visible_slice": "User can run the check-vertical-slices command and observe PASS for demo path, scope guard, and rollback plan",
            "demo_path": "python skills/software-project-governance/infra/verify_workflow.py check-vertical-slices --fail-on-issues",
            "scope_guard": "Only execution packet vertical_slice fields, Check 18g, CLI command, template docs, and regression tests are in scope",
            "rollback_plan": "Revert the FIX-091 commit or remove Check 18g and the vertical_slice packet fields if validation fails",
            "status": status,
            "evidence": "VerticalSliceTests and check-vertical-slices output provide the demo proof",
        }

    def test_generated_execution_packet_contains_failing_vertical_slice_scaffold(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P1** | FIX-091 | Vertical Slice Delivery Packets | FIX-090 | 0.39.0 | slices | 📋 待实施 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_vertical_slices(packet_path)
            self.assertFalse(r["pass"])
            self.assertIn("vertical_slice", payload["packets"]["FIX-091"])
            self.assertTrue(any("non-placeholder" in issue for issue in r["entries"][0]["issues"]))

    def test_explicit_vertical_slice_passes(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P1** | FIX-091 | Vertical Slice Delivery Packets | FIX-090 | 0.39.0 | slices | 🔄 进行中 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            payload["packets"]["FIX-091"]["vertical_slice"] = self._valid_vertical_slice()
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_vertical_slices(packet_path)
            self.assertTrue(r["pass"])

    def test_missing_vertical_slice_fails(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P1** | FIX-091 | Vertical Slice Delivery Packets | FIX-090 | 0.39.0 | slices | 🔄 进行中 |",
            ])
            packet_path.write_text(json.dumps({
                "version": 1,
                "packets": {"FIX-091": {"task_id": "FIX-091", "goal": "slice guard"}},
            }), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_vertical_slices(packet_path)
            self.assertFalse(r["pass"])
            self.assertIn("missing vertical_slice", r["entries"][0]["issues"])

    def test_vertical_slice_rejects_technical_layer_only_slice(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P1** | FIX-091 | Vertical Slice Delivery Packets | FIX-090 | 0.39.0 | slices | 🔄 进行中 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            contract = self._valid_vertical_slice()
            contract["user_visible_slice"] = "Refactor internal repository abstraction and service layer"
            payload["packets"]["FIX-091"]["vertical_slice"] = contract
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_vertical_slices(packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("user-observable" in issue for issue in r["entries"][0]["issues"]))

    def test_vertical_slice_rejects_user_named_technical_layer_slice(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P1** | FIX-091 | Vertical Slice Delivery Packets | FIX-090 | 0.39.0 | slices | 🔄 进行中 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            contract = self._valid_vertical_slice()
            contract["user_visible_slice"] = "UserService repository abstraction and internal service layer refactor"
            payload["packets"]["FIX-091"]["vertical_slice"] = contract
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_vertical_slices(packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("technical-layer" in issue for issue in r["entries"][0]["issues"]))

    def test_vertical_slice_rejects_non_runnable_demo_path(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P1** | FIX-091 | Vertical Slice Delivery Packets | FIX-090 | 0.39.0 | slices | 🔄 进行中 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            contract = self._valid_vertical_slice()
            contract["demo_path"] = "Stakeholder will be told that the slice is good"
            payload["packets"]["FIX-091"]["vertical_slice"] = contract
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_vertical_slices(packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("demo_path" in issue for issue in r["entries"][0]["issues"]))

    def test_vertical_slice_rejects_broad_scope_guard(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P1** | FIX-091 | Vertical Slice Delivery Packets | FIX-090 | 0.39.0 | slices | 🔄 进行中 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            contract = self._valid_vertical_slice()
            contract["scope_guard"] = "All files and the whole codebase are in scope"
            payload["packets"]["FIX-091"]["vertical_slice"] = contract
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_vertical_slices(packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("whole project/codebase" in issue for issue in r["entries"][0]["issues"]))

    def test_in_progress_vertical_slice_rejects_not_run_yet(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P1** | FIX-091 | Vertical Slice Delivery Packets | FIX-090 | 0.39.0 | slices | 🔄 进行中 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            payload["packets"]["FIX-091"]["vertical_slice"] = self._valid_vertical_slice(status="NOT_RUN_YET")
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_vertical_slices(packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("status must be PASS" in issue for issue in r["entries"][0]["issues"]))

    def test_pending_vertical_slice_allows_not_run_yet(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P1** | FIX-092 | Weak-LLM Deterministic Scaffolds | FIX-091 | 0.39.0 | scaffolds | 📋 待实施 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            payload["packets"]["FIX-092"]["vertical_slice"] = self._valid_vertical_slice(status="NOT_RUN_YET")
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_vertical_slices(packet_path)
            self.assertTrue(r["pass"])

    def test_vertical_slice_rejects_review_prose_only_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            _, sp, packet_path = self._setup_plan(td, [
                "| **P1** | FIX-091 | Vertical Slice Delivery Packets | FIX-090 | 0.39.0 | slices | 🔄 进行中 |",
            ])
            with patch.object(vw, "SAMPLE_PATH", sp):
                payload = vw.generate_execution_packets()
            contract = self._valid_vertical_slice()
            contract["demo_path"] = "review artifact says looks good"
            contract["evidence"] = "review says the demo is fine"
            payload["packets"]["FIX-091"]["vertical_slice"] = contract
            packet_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", sp):
                r = vw.check_vertical_slices(packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("review/prose-only" in issue for issue in r["entries"][0]["issues"]))


class DeterministicScaffoldTests(unittest.TestCase):
    """FIX-092: weak-LLM deterministic scaffolds need templates, generator, and checks."""

    def _write_valid_scaffold_set(self, base):
        base.mkdir(parents=True, exist_ok=True)
        (base / "index.md").write_text("\n".join([
            "# Weak-LLM Deterministic Scaffolds",
            "Use generate-deterministic-scaffold to render templates.",
            "- web-app.md",
            "- cli-tool.md",
            "- workflow-plugin.md",
        ]), encoding="utf-8")
        template = "\n".join([
            "# Deterministic Scaffold: {name}",
            "This substantial template helps a persona deliver a user visible scenario with acceptance, quality budget, demo checklist, and vertical slice evidence.",
            "## Product Success Contract",
            "- Persona: user who needs the governed workflow.",
            "- JTBD: complete one scenario with a visible result and a reliable command output.",
            "- Non-goal: process records are not product success.",
            "- Success metric: user can run a command and observe the expected result without relying on a review note.",
            "## PRD-lite",
            "- Problem: weak models need paved paths that state the user problem before implementation starts.",
            "- Workflow: run a fixture, inspect output, and record evidence for a user-visible scenario.",
            "## Executable Acceptance",
            "- `python skills/software-project-governance/infra/verify_workflow.py check-deterministic-scaffolds --fail-on-issues` validates the scaffold.",
            "- Expected output: the command reports pass and demo evidence includes command, exit code, and artifact path.",
            "## Quality Budget",
            "- performance: bounded command runtime.",
            "- reliability: positive and negative fixture tests.",
            "- security: no secret output.",
            "- accessibility: readable command output.",
            "- ux: clear next action and stable labels.",
            "- maintainability: focused files and tests.",
            "## Vertical Slice",
            "- User-visible slice: user runs the command and observes PASS.",
            "- Demo path: runnable command output.",
            "- Scope guard: one template, one fixture, and focused tests.",
            "- Rollback plan: remove the template and command registration.",
            "## Demo Checklist",
            "- Command exits zero for valid fixture.",
            "- Invalid fixture reports field names.",
            "- Evidence includes command and exit code.",
            "## Tooling",
            "- `python skills/software-project-governance/infra/verify_workflow.py check-product-success-contracts --fail-on-issues`",
            "- `python skills/software-project-governance/infra/verify_workflow.py check-acceptance-contracts --fail-on-issues`",
            "- `python skills/software-project-governance/infra/verify_workflow.py check-quality-budget --fail-on-issues`",
            "- `python skills/software-project-governance/infra/verify_workflow.py check-vertical-slices --fail-on-issues`",
        ])
        for scaffold_type in vw.DETERMINISTIC_SCAFFOLD_TYPES:
            (base / f"{scaffold_type}.md").write_text(template.format(name=scaffold_type), encoding="utf-8")

    def test_real_deterministic_scaffolds_pass(self):
        r = vw.check_deterministic_scaffolds()
        self.assertTrue(r["pass"], r)
        self.assertEqual(len(r["entries"]), len(vw.DETERMINISTIC_SCAFFOLD_TYPES))

    def test_missing_scaffold_directory_fails(self):
        with tempfile.TemporaryDirectory() as td:
            r = vw.check_deterministic_scaffolds(Path(td) / "missing")
            self.assertFalse(r["pass"])
            self.assertTrue(any("missing scaffold directory" in issue for issue in r["issues"]))

    def test_missing_scaffold_file_fails(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "scaffolds"
            self._write_valid_scaffold_set(base)
            (base / "cli-tool.md").unlink()
            r = vw.check_deterministic_scaffolds(base)
            self.assertFalse(r["pass"])
            self.assertTrue(any(entry["scaffold_type"] == "cli-tool" and entry["status"] == "FAIL" for entry in r["entries"]))

    def test_scaffold_missing_required_section_fails(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "scaffolds"
            self._write_valid_scaffold_set(base)
            path = base / "web-app.md"
            path.write_text(path.read_text(encoding="utf-8").replace("## Demo Checklist", "## Demo Notes"), encoding="utf-8")
            r = vw.check_deterministic_scaffolds(base)
            self.assertFalse(r["pass"])
            web_entry = next(entry for entry in r["entries"] if entry["scaffold_type"] == "web-app")
            self.assertTrue(any("Demo Checklist" in issue for issue in web_entry["issues"]))

    def test_scaffold_rejects_review_prose_placeholders(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "scaffolds"
            self._write_valid_scaffold_set(base)
            path = base / "workflow-plugin.md"
            path.write_text(path.read_text(encoding="utf-8") + "\nreview says looks good\n", encoding="utf-8")
            r = vw.check_deterministic_scaffolds(base)
            self.assertFalse(r["pass"])
            plugin_entry = next(entry for entry in r["entries"] if entry["scaffold_type"] == "workflow-plugin")
            self.assertTrue(any("placeholders or review/prose-only" in issue for issue in plugin_entry["issues"]))

    def test_scaffold_rejects_empty_heading_shell(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "scaffolds"
            self._write_valid_scaffold_set(base)
            hollow = "\n".join([
                "# Deterministic Scaffold: hollow",
                "This file has many words but avoids real section content. " * 30,
                "## Product Success Contract",
                "## PRD-lite",
                "## Executable Acceptance",
                "- `python skills/software-project-governance/infra/verify_workflow.py check-deterministic-scaffolds --fail-on-issues`",
                "## Quality Budget",
                "performance reliability security accessibility ux maintainability",
                "## Vertical Slice",
                "## Demo Checklist",
                "## Tooling",
            ])
            (base / "web-app.md").write_text(hollow, encoding="utf-8")
            r = vw.check_deterministic_scaffolds(base)
            self.assertFalse(r["pass"])
            web_entry = next(entry for entry in r["entries"] if entry["scaffold_type"] == "web-app")
            self.assertTrue(any("substantive scaffold bullets" in issue for issue in web_entry["issues"]))

    def test_scaffold_rejects_reviewer_approved_prose_bypass(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "scaffolds"
            self._write_valid_scaffold_set(base)
            path = base / "cli-tool.md"
            path.write_text(path.read_text(encoding="utf-8") + "\nDemo Checklist: review passed and reviewer approved the scaffold prose.\n", encoding="utf-8")
            r = vw.check_deterministic_scaffolds(base)
            self.assertFalse(r["pass"])
            cli_entry = next(entry for entry in r["entries"] if entry["scaffold_type"] == "cli-tool")
            self.assertTrue(any("placeholders or review/prose-only" in issue for issue in cli_entry["issues"]))

    def test_scaffold_rejects_entire_repository_scope(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "scaffolds"
            self._write_valid_scaffold_set(base)
            path = base / "workflow-plugin.md"
            path.write_text(path.read_text(encoding="utf-8") + "\nScope guard: the entire repository is in scope for broad changes.\n", encoding="utf-8")
            r = vw.check_deterministic_scaffolds(base)
            self.assertFalse(r["pass"])
            plugin_entry = next(entry for entry in r["entries"] if entry["scaffold_type"] == "workflow-plugin")
            self.assertTrue(any("whole-project/all-files" in issue for issue in plugin_entry["issues"]))

    def test_generator_renders_known_scaffold(self):
        content = vw.render_deterministic_scaffold("web-app")
        self.assertIn("## Product Success Contract", content)
        self.assertIn("## Demo Checklist", content)

    def test_generator_rejects_unknown_scaffold_type(self):
        with self.assertRaises(ValueError):
            vw.render_deterministic_scaffold("space-elevator")


class InterruptionPolicyTests(unittest.TestCase):
    """FIX-093: user interruption policy must be deterministic and packet-backed."""

    def _valid_policy(self):
        return {
            "mode": "critical-only: default execute routine reversible work and record assumptions when needed",
            "critical_triggers": [
                "Ask the user when product intent is unclear.",
                "Ask the user when acceptance standard or done criteria are unclear.",
                "Ask the user before irreversible, release, risk acceptance, external dependency, or mode change decisions.",
            ],
            "auto_execute": [
                "Run routine execution, local validation, focused code edits, and governance record updates when scope is known and reversible.",
                "Commit and push normal single-task changes when validation, evidence, and review gates are satisfied.",
            ],
            "assumption_record": {
                "assumption": "Use the repository's existing interaction boundary vocabulary for reversible policy wording.",
                "basis": "The nearby interaction-boundary rules already define maximum-autonomy and default-confirm behavior.",
                "reversibility": "The wording is isolated to one policy field and can be adjusted in a focused follow-up.",
                "validation": "Run check-interruption-policy with fail-on-issues to classify examples and packet fields.",
                "rollback": "Revert the focused policy field if validation or review finds the assumption wrong.",
            },
            "interruption_budget": "At most one user interruption per work unit unless a new critical trigger appears.",
        }

    def _write_fixture(self, td, policy=None):
        root = Path(td)
        boundary = root / "interaction-boundary.md"
        boundary.write_text("\n".join([
            "# 用户交互边界规则",
            "## User Interruption Policy v2",
            "critical-only policy protects product intent, acceptance standard, irreversible choices, record_assumption, and interruption_budget.",
        ]), encoding="utf-8")
        template = root / "user-interruption-policy.md"
        template.write_text("\n".join([
            "interruption_policy:",
            "critical_triggers:",
            "auto_execute:",
            "assumption_record:",
            "interruption_budget:",
        ]), encoding="utf-8")
        plan = root / "plan-tracker.md"
        plan.write_text("\n".join([
            "# Plan",
            "## 当前活跃事项",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            "| **P1** | FIX-093 | User Interruption Policy v2 | FIX-092 | 0.39.0 | policy checker | 🔄 进行中 |",
        ]), encoding="utf-8")
        packet_path = root / "execution-packets.json"
        packet_path.write_text(json.dumps({
            "version": 1,
            "packets": {
                "FIX-093": {
                    "task_id": "FIX-093",
                    "interruption_policy": policy or self._valid_policy(),
                }
            },
        }, ensure_ascii=False), encoding="utf-8")
        return boundary, template, plan, packet_path

    def test_real_interruption_policy_passes(self):
        r = vw.check_interruption_policy()
        self.assertTrue(r["pass"], r)

    def test_missing_interaction_boundary_fails(self):
        with tempfile.TemporaryDirectory() as td:
            boundary, template, plan, packet_path = self._write_fixture(td)
            with patch.object(vw, "SAMPLE_PATH", plan):
                r = vw.check_interruption_policy(boundary.with_name("missing.md"), template, packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("missing interaction boundary" in issue for issue in r["issues"]))

    def test_missing_v2_phrase_fails(self):
        with tempfile.TemporaryDirectory() as td:
            boundary, template, plan, packet_path = self._write_fixture(td)
            boundary.write_text("# 用户交互边界规则\ncritical-only only\n", encoding="utf-8")
            with patch.object(vw, "SAMPLE_PATH", plan):
                r = vw.check_interruption_policy(boundary, template, packet_path)
            self.assertFalse(r["pass"])
            self.assertTrue(any("User Interruption Policy v2" in issue for issue in r["issues"]))

    def test_critical_product_intent_asks_user(self):
        action = vw.classify_user_interruption({"product_intent_unclear": True, "reversible": True})
        self.assertEqual(action, "ask_user")

    def test_routine_scoped_execution_auto_executes(self):
        action = vw.classify_user_interruption({"routine_execution": True, "known_scope": True, "reversible": True})
        self.assertEqual(action, "auto_execute")

    def test_reversible_unknown_scope_records_assumption(self):
        action = vw.classify_user_interruption({"routine_execution": True, "known_scope": False, "reversible": True})
        self.assertEqual(action, "record_assumption")

    def test_examples_detect_misclassified_critical_decision(self):
        examples = list(vw.INTERRUPTION_POLICY_DEFAULT_EXAMPLES)
        bad = dict(examples[0])
        bad["expected_action"] = "auto_execute"
        examples[0] = bad
        issues = vw._validate_interruption_policy_examples(examples)
        self.assertTrue(any("product-intent-ambiguity" in issue and "expected auto_execute" in issue for issue in issues))

    def test_packet_rejects_placeholder_assumption_record(self):
        with tempfile.TemporaryDirectory() as td:
            policy = self._valid_policy()
            policy["assumption_record"] = dict(policy["assumption_record"])
            policy["assumption_record"]["basis"] = "TO_BE_DEFINED: later"
            boundary, template, plan, packet_path = self._write_fixture(td, policy)
            with patch.object(vw, "SAMPLE_PATH", plan):
                r = vw.check_interruption_policy(boundary, template, packet_path)
            self.assertFalse(r["pass"])
            entry = r["entries"][0]
            self.assertTrue(any("placeholder" in issue for issue in entry["issues"]))

    def test_packet_requires_release_risk_external_and_mode_triggers(self):
        with tempfile.TemporaryDirectory() as td:
            policy = self._valid_policy()
            policy["critical_triggers"] = [
                "Ask the user when product intent is unclear.",
                "Ask the user when acceptance standard or done criteria are unclear.",
                "Ask the user before irreversible destructive decisions.",
            ]
            boundary, template, plan, packet_path = self._write_fixture(td, policy)
            with patch.object(vw, "SAMPLE_PATH", plan):
                r = vw.check_interruption_policy(boundary, template, packet_path)
            self.assertFalse(r["pass"])
            issues = r["entries"][0]["issues"]
            for token in ("release", "risk acceptance", "external dependency", "mode change"):
                self.assertTrue(any(token in issue for issue in issues), issues)


class CommitMsgFactGroundingHookTests(unittest.TestCase):
    """FIX-080: commit-msg hook must block product commits without fact basis."""

    def _bash(self):
        if os.name == "nt":
            candidates = [
                Path(os.environ.get("ProgramFiles", "")) / "Git" / "bin" / "bash.exe",
                Path(os.environ.get("ProgramFiles(x86)", "")) / "Git" / "bin" / "bash.exe",
            ]
            for candidate in candidates:
                if candidate.exists():
                    return str(candidate)
        return shutil.which("bash") or "bash"

    def _run_hook(self, evidence_text=None, staged_path="skills/test/file.txt"):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)

            gov = root / ".governance"
            gov.mkdir(parents=True, exist_ok=True)
            (gov / "plan-tracker.md").write_text("\n".join([
                "# 计划跟踪",
                "## 项目配置",
                "- **项目目标**: 提供一套完整的软件项目治理工作流插件",
                "## 当前活跃事项",
                "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
                "|--------|----|------|------|---------|---------|------|",
                "| **P0** | FIX-080 | fact guard | 用户反馈 | 0.37.0 | tests | 🔄 进行中 |",
            ]), encoding="utf-8")
            if evidence_text is not None:
                (gov / "evidence-log.md").write_text(evidence_text, encoding="utf-8")

            product_file = root / staged_path
            product_file.parent.mkdir(parents=True, exist_ok=True)
            product_file.write_text("product change\n", encoding="utf-8")
            subprocess.run(["git", "add", staged_path], cwd=root, check=True)

            msg = root / "COMMIT_EDITMSG"
            msg.write_text("FIX-080: test fact grounding hook\n", encoding="utf-8")
            hook = _INFRA_DIR / "hooks" / "commit-msg"
            return subprocess.run(
                [self._bash(), hook.as_posix(), msg.as_posix()],
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

    def test_commit_msg_blocks_missing_evidence_log_for_product_code(self):
        result = self._run_hook(evidence_text=None)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("evidence-log.md is missing", result.stdout)

    def test_commit_msg_blocks_missing_fact_basis(self):
        evidence = _impact_evidence_row(
            "EVD-080", "FIX-080",
            "目标对齐: 提升治理工作流证据可信度，避免无事实闭环。 "
            "用户影响: 获得=plugin update, 感知=CHANGELOG, 体验变化=否, 迁移指南=不需要",
            "skills/test/file.txt",
        )
        result = self._run_hook(evidence_text=evidence)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("has NO", result.stdout)
        self.assertIn("事实依据", result.stdout)

    def test_commit_msg_accepts_fact_basis(self):
        evidence = "\n".join([
            _impact_evidence_row(
                "EVD-081", "FIX-080",
                "事实依据: commit-msg hook fixture staged skills/test/file.txt and evidence-log row. "
                "目标对齐: 提升治理工作流证据可信度，避免无事实闭环。 "
                "用户影响: 获得=plugin update, 感知=CHANGELOG, 体验变化=否, 迁移指南=不需要",
                "skills/test/file.txt",
            ),
            "| REVIEW-FIX-080 | FIX-080 | 审查 | 代码审查 | "
            "Code Reviewer approved fact grounding hook fixture. | "
            "skills/test/file.txt | Code Reviewer | 2026-05-02 | G11 | APPROVED |",
        ])
        result = self._run_hook(evidence_text=evidence)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_commit_msg_accepts_nested_product_path_with_dated_evidence_row(self):
        evidence = "\n".join([
            _dated_impact_evidence_row(
                "EVD-140", "FIX-080",
                "事实依据: commit-msg hook fixture staged writing-workflow/skills/software-project-governance/SKILL.md. "
                "目标对齐: nested plugin product paths receive the same governance protection as root product paths. "
                "用户影响: 获得=plugin update, 感知=nested hook guard works, 体验变化=否, 迁移指南=不需要",
                "writing-workflow/skills/software-project-governance/SKILL.md",
            ),
            "| REVIEW-FIX-080 | FIX-080 | 审查 | 代码审查 | "
            "Code Reviewer approved nested product path hook fixture. | "
            "writing-workflow/skills/software-project-governance/SKILL.md | Code Reviewer | 2026-06-16 | G11 | APPROVED |",
        ])
        result = self._run_hook(
            evidence_text=evidence,
            staged_path="writing-workflow/skills/software-project-governance/SKILL.md",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_commit_msg_blocks_nested_product_path_with_missing_goal_alignment(self):
        evidence = "\n".join([
            _dated_impact_evidence_row(
                "EVD-141", "FIX-080",
                "事实依据: commit-msg hook fixture staged writing-workflow/.claude-plugin/marketplace.json. "
                "用户影响: 获得=plugin update, 感知=nested hook guard works, 体验变化=否, 迁移指南=不需要",
                "writing-workflow/.claude-plugin/marketplace.json",
            ),
            "| REVIEW-FIX-080 | FIX-080 | 审查 | 代码审查 | "
            "Code Reviewer approved nested product path hook fixture. | "
            "writing-workflow/.claude-plugin/marketplace.json | Code Reviewer | 2026-06-16 | G11 | APPROVED |",
        ])
        result = self._run_hook(
            evidence_text=evidence,
            staged_path="writing-workflow/.claude-plugin/marketplace.json",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("GOAL ALIGNMENT BLOCKED", result.stdout)

    def test_commit_msg_blocks_nested_product_path_with_missing_user_impact(self):
        evidence = "\n".join([
            _dated_impact_evidence_row(
                "EVD-142", "FIX-080",
                "事实依据: commit-msg hook fixture staged some-plugin/agents/developer.md. "
                "目标对齐: nested plugin agent prompts are product files and remain governed.",
                "some-plugin/agents/developer.md",
            ),
            "| REVIEW-FIX-080 | FIX-080 | 审查 | 代码审查 | "
            "Code Reviewer approved nested product path hook fixture. | "
            "some-plugin/agents/developer.md | Code Reviewer | 2026-06-16 | G11 | APPROVED |",
        ])
        result = self._run_hook(
            evidence_text=evidence,
            staged_path="some-plugin/agents/developer.md",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("USER IMPACT BLOCKED", result.stdout)

    def test_commit_msg_blocks_dated_evidence_row_with_missing_fact_basis(self):
        evidence = "\n".join([
            _dated_impact_evidence_row(
                "EVD-143", "FIX-080",
                "目标对齐: dated evidence rows must still satisfy the same product-code gate fields. "
                "用户影响: 获得=plugin update, 感知=nested hook guard works, 体验变化=否, 迁移指南=不需要",
                "writing-workflow/skills/software-project-governance/SKILL.md",
            ),
            "| REVIEW-FIX-080 | FIX-080 | 审查 | 代码审查 | "
            "Code Reviewer approved dated evidence row fixture. | "
            "writing-workflow/skills/software-project-governance/SKILL.md | Code Reviewer | 2026-06-16 | G11 | APPROVED |",
        ])
        result = self._run_hook(
            evidence_text=evidence,
            staged_path="writing-workflow/skills/software-project-governance/SKILL.md",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("事实依据", result.stdout)

    def test_commit_msg_blocks_ungrounded_language(self):
        evidence = _impact_evidence_row(
            "EVD-082", "FIX-080",
            "事实依据: commit-msg hook fixture staged skills/test/file.txt and evidence-log row. "
            "我猜测这个已经完成。目标对齐: 提升治理工作流证据可信度，避免无事实闭环。 "
            "用户影响: 获得=plugin update, 感知=CHANGELOG, 体验变化=否, 迁移指南=不需要",
            "skills/test/file.txt",
        )
        result = self._run_hook(evidence_text=evidence)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ungrounded speculation language", result.stdout)


class CommitMessageSourceHardeningTests(unittest.TestCase):
    """FIX-133: stale message files must not drive strong hook semantics."""

    def _bash(self):
        if os.name == "nt":
            candidates = [
                Path(os.environ.get("ProgramFiles", "")) / "Git" / "bin" / "bash.exe",
                Path(os.environ.get("ProgramFiles(x86)", "")) / "Git" / "bin" / "bash.exe",
            ]
            for candidate in candidates:
                if candidate.exists():
                    return str(candidate)
        return shutil.which("bash") or "bash"

    def _env(self):
        env = os.environ.copy()
        env["SOFTWARE_PROJECT_GOVERNANCE_HOME"] = _INFRA_DIR.parent.as_posix()
        return env

    def _git_path(self, root: Path, name: str) -> Path:
        result = subprocess.run(
            ["git", "rev-parse", "--git-path", name],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        return root / result.stdout.strip()

    def _init_repo(self, root: Path, *, with_evidence=True, review_status=None,
                   evidence_row_builder=_impact_evidence_row,
                   evidence_file_location="skills/test/file.txt"):
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)

        gov = root / ".governance"
        gov.mkdir(parents=True, exist_ok=True)
        (gov / "plan-tracker.md").write_text("\n".join([
            "# 计划跟踪",
            "## 项目配置",
            "- **项目目标**: 提供一套完整的软件项目治理工作流插件",
            "## 当前活跃事项",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            "| **P0** | FIX-133 | hook message source hardening | RISK-036 | 0.50.3 | tests | 🔄 进行中 |",
            "| **P0** | FIX-999 | stale previous task | RISK-036 | 0.50.3 | tests | 🔄 进行中 |",
        ]), encoding="utf-8")
        evidence_rows = []
        if with_evidence:
            evidence_rows.append(evidence_row_builder(
                "EVD-133",
                "FIX-133",
                f"事实依据: hook fixture staged {evidence_file_location} and ran commit-msg from the actual message file. "
                "目标对齐: 修复 git commit -m 下 stale commit message source 导致治理 hook 误判的问题。 "
                "用户影响: 获得=plugin update, 感知=commit hook no stale block, 体验变化=否, 迁移指南=不需要",
                evidence_file_location,
            ))
        if review_status is not None:
            evidence_rows.append(
                "| REVIEW-FIX-133 | FIX-133 | 审查 | 代码审查 | "
                f"Code Reviewer returned {review_status} for FIX-133 hook message source hardening. | "
                f"skills/test/file.txt | Code Reviewer | 2026-06-14 | G11 | {review_status} |"
            )
        if evidence_rows:
            (gov / "evidence-log.md").write_text("\n".join(evidence_rows), encoding="utf-8")

    def _stage_product_change(self, root: Path, content="product change\n",
                              staged_path="skills/test/file.txt"):
        product_file = root / staged_path
        product_file.parent.mkdir(parents=True, exist_ok=True)
        product_file.write_text(content, encoding="utf-8")
        subprocess.run(["git", "add", staged_path], cwd=root, check=True)

    def _install_hook(self, root: Path, hook_name: str):
        target = root / ".git" / "hooks" / hook_name
        shutil.copyfile(_INFRA_DIR / "hooks" / hook_name, target)
        target.chmod(0o755)
        return target

    def _install_hooks(self, root: Path):
        for hook_name in ("pre-commit", "prepare-commit-msg", "commit-msg", "post-commit"):
            self._install_hook(root, hook_name)

    def test_pre_commit_ignores_stale_commit_editmsg_for_review_blocking(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_repo(root, with_evidence=False)
            self._stage_product_change(root)
            self._git_path(root, "COMMIT_EDITMSG").write_text(
                "FIX-999: stale message should not require review\n",
                encoding="utf-8",
            )
            self._git_path(root, "GOV_COMMIT_MSG").write_text(
                "FIX-999: stale bridge message should be cleared\n",
                encoding="utf-8",
            )

            hook = _INFRA_DIR / "hooks" / "pre-commit"
            result = subprocess.run(
                [self._bash(), hook.as_posix()],
                cwd=root,
                env=self._env(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("M7.4 BLOCKED", result.stdout)
            self.assertFalse(self._git_path(root, "GOV_COMMIT_MSG").exists())

    def test_pre_commit_treats_nested_product_path_as_product_code_when_message_is_direct(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_repo(root, with_evidence=True, review_status=None)
            self._stage_product_change(
                root,
                staged_path="writing-workflow/skills/software-project-governance/SKILL.md",
            )
            actual_msg = root / "message.txt"
            actual_msg.write_text("FIX-133: direct message fixture\n", encoding="utf-8")

            hook = _INFRA_DIR / "hooks" / "pre-commit"
            result = subprocess.run(
                [self._bash(), hook.as_posix(), actual_msg.as_posix()],
                cwd=root,
                env=self._env(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("M7.4 BLOCKED", result.stdout)

    def test_pre_commit_keeps_governance_record_path_non_product_when_message_is_direct(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_repo(root, with_evidence=False)
            record_file = root / ".governance" / "notes.md"
            record_file.write_text("governance note\n", encoding="utf-8")
            subprocess.run(["git", "add", ".governance/notes.md"], cwd=root, check=True)
            actual_msg = root / "message.txt"
            actual_msg.write_text("FIX-133: direct message fixture\n", encoding="utf-8")

            hook = _INFRA_DIR / "hooks" / "pre-commit"
            result = subprocess.run(
                [self._bash(), hook.as_posix(), actual_msg.as_posix()],
                cwd=root,
                env=self._env(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("M7.4 BLOCKED", result.stdout)

    def test_git_commit_m_requires_review_evidence_for_product_code(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_repo(root)
            self._install_hooks(root)
            self._stage_product_change(root)
            self._git_path(root, "COMMIT_EDITMSG").write_text(
                "FIX-999: stale old task must not be the commit-msg source\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                ["git", "commit", "-m", "FIX-133: harden commit message source"],
                cwd=root,
                env=self._env(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertNotEqual(result.returncode, 0)
            output = result.stdout + result.stderr
            self.assertIn("M7.4 BLOCKED", output)
            self.assertIn("FIX-133", output)
            self.assertFalse(self._git_path(root, "GOV_COMMIT_MSG").exists())

    def test_git_commit_m_rejects_failed_review_evidence_for_product_code(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_repo(root, review_status="NEEDS_CHANGE")
            self._install_hooks(root)
            self._stage_product_change(root)
            self._git_path(root, "COMMIT_EDITMSG").write_text(
                "FIX-999: stale approved-looking message must not help\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                ["git", "commit", "-m", "FIX-133: harden commit message source"],
                cwd=root,
                env=self._env(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertNotEqual(result.returncode, 0)
            output = result.stdout + result.stderr
            self.assertIn("M7.4 BLOCKED", output)
            self.assertIn("FIX-133", output)

    def test_git_commit_m_uses_current_message_when_commit_editmsg_is_stale(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_repo(root, review_status="APPROVED")
            self._install_hooks(root)
            self._stage_product_change(root)
            self._git_path(root, "COMMIT_EDITMSG").write_text(
                "FIX-999: stale message should not drive this commit\n",
                encoding="utf-8",
            )
            self._git_path(root, "GOV_COMMIT_MSG").write_text(
                "FIX-999: stale bridge message should be cleared\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                ["git", "commit", "-m", "FIX-133: harden commit message source"],
                cwd=root,
                env=self._env(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            subject = subprocess.run(
                ["git", "log", "-1", "--format=%s"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(subject, "FIX-133: harden commit message source")
            self.assertFalse(self._git_path(root, "GOV_COMMIT_MSG").exists())

    def test_git_commit_m_treats_nested_skills_path_as_product_code(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            nested_path = "writing-workflow/skills/software-project-governance/SKILL.md"
            self._init_repo(
                root,
                review_status="APPROVED",
                evidence_row_builder=_dated_impact_evidence_row,
                evidence_file_location=nested_path,
            )
            self._install_hooks(root)
            self._stage_product_change(root, staged_path=nested_path)

            result = subprocess.run(
                ["git", "commit", "-m", "FIX-133: harden commit message source"],
                cwd=root,
                env=self._env(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_git_commit_m_treats_nested_agent_path_as_product_code_without_review(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            nested_path = "some-plugin/agents/developer.md"
            self._init_repo(
                root,
                review_status=None,
                evidence_file_location=nested_path,
            )
            self._install_hooks(root)
            self._stage_product_change(root, staged_path=nested_path)

            result = subprocess.run(
                ["git", "commit", "-m", "FIX-133: harden commit message source"],
                cwd=root,
                env=self._env(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertNotEqual(result.returncode, 0)
            output = result.stdout + result.stderr
            self.assertIn("M7.4 BLOCKED", output)

    def test_git_commit_m_keeps_governance_record_path_non_product(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_repo(root, with_evidence=False)
            self._install_hooks(root)
            record_file = root / ".governance" / "notes.md"
            record_file.write_text("governance note\n", encoding="utf-8")
            subprocess.run(["git", "add", ".governance/notes.md"], cwd=root, check=True)

            result = subprocess.run(
                ["git", "commit", "-m", "FIX-133: harden commit message source"],
                cwd=root,
                env=self._env(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_commit_msg_uses_only_actual_message_file_not_stale_commit_editmsg(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_repo(root)
            self._stage_product_change(root)
            self._git_path(root, "COMMIT_EDITMSG").write_text(
                "FIX-133: stale approved-looking message\n",
                encoding="utf-8",
            )
            self._git_path(root, "GOV_COMMIT_MSG").write_text(
                "FIX-133: stale bridge message\n",
                encoding="utf-8",
            )
            actual_msg = root / "actual-message.txt"
            actual_msg.write_text("missing task id despite stale files\n", encoding="utf-8")

            hook = _INFRA_DIR / "hooks" / "commit-msg"
            result = subprocess.run(
                [self._bash(), hook.as_posix(), actual_msg.as_posix()],
                cwd=root,
                env=self._env(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("NO task ID", result.stdout)
            self.assertFalse(self._git_path(root, "GOV_COMMIT_MSG").exists())

    def test_prepare_commit_msg_does_not_persist_gov_commit_msg_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_repo(root)
            stale_bridge = self._git_path(root, "GOV_COMMIT_MSG")
            stale_bridge.write_text("FIX-999: stale bridge\n", encoding="utf-8")
            actual_msg = root / "message.txt"
            actual_msg.write_text("FIX-133: current prepared message\n", encoding="utf-8")

            hook = _INFRA_DIR / "hooks" / "prepare-commit-msg"
            result = subprocess.run(
                [self._bash(), hook.as_posix(), actual_msg.as_posix(), "message"],
                cwd=root,
                env=self._env(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(stale_bridge.exists())

    def test_post_commit_removes_legacy_gov_commit_msg_bridge(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._init_repo(root)
            subprocess.run(
                ["git", "commit", "--allow-empty", "-m", "FIX-133: baseline", "--no-verify"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            )
            stale_bridge = self._git_path(root, "GOV_COMMIT_MSG")
            stale_bridge.write_text("FIX-999: stale bridge\n", encoding="utf-8")

            hook = _INFRA_DIR / "hooks" / "post-commit"
            result = subprocess.run(
                [self._bash(), hook.as_posix()],
                cwd=root,
                env=self._env(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(stale_bridge.exists())


class PreCommitClaudeBootstrapUpgradeHookTests(unittest.TestCase):
    """FIX-081: pre-commit allows legitimate CLAUDE.md bootstrap self-upgrade."""

    def _bash(self):
        if os.name == "nt":
            candidates = [
                Path(os.environ.get("ProgramFiles", "")) / "Git" / "bin" / "bash.exe",
                Path(os.environ.get("ProgramFiles(x86)", "")) / "Git" / "bin" / "bash.exe",
            ]
            for candidate in candidates:
                if candidate.exists():
                    return str(candidate)
        return shutil.which("bash") or "bash"

    def _run_hook(self, *, plan_version="0.37.0", initial_version="0.35.0",
                  stage_plan=True, change_outside_bootstrap=False):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)

            skill = root / "skills" / "software-project-governance" / "SKILL.md"
            skill.parent.mkdir(parents=True, exist_ok=True)
            skill.write_text("---\nversion: 0.37.0\n---\n", encoding="utf-8")

            claude = root / "CLAUDE.md"
            claude.write_text(
                "# Project\n\n"
                "## Governance Bootstrap\n\n"
                "old bootstrap\n\n"
                "## 当前项目治理状态快速入口\n\n"
                "- stable local content\n",
                encoding="utf-8",
            )

            gov = root / ".governance"
            gov.mkdir(parents=True, exist_ok=True)
            (gov / "plan-tracker.md").write_text(
                f"## 项目配置\n- **工作流版本**: {initial_version}\n",
                encoding="utf-8",
            )

            subprocess.run(["git", "add", "CLAUDE.md", ".governance/plan-tracker.md",
                            "skills/software-project-governance/SKILL.md"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "INIT-001: baseline"], cwd=root,
                           check=True, capture_output=True, text=True)

            if change_outside_bootstrap:
                claude.write_text(
                    "# Project changed directly\n\n"
                    "## Governance Bootstrap\n\n"
                    "updated bootstrap\n\n"
                    "## 当前项目治理状态快速入口\n\n"
                    "- stable local content\n",
                    encoding="utf-8",
                )
            else:
                claude.write_text(
                    "# Project\n\n"
                    "## Governance Bootstrap\n\n"
                    "updated bootstrap\n\n"
                    "## 当前项目治理状态快速入口\n\n"
                    "- stable local content\n",
                    encoding="utf-8",
                )
            (gov / "plan-tracker.md").write_text(
                f"## 项目配置\n- **工作流版本**: {plan_version}\n- note: staged\n",
                encoding="utf-8",
            )

            subprocess.run(["git", "add", "CLAUDE.md"], cwd=root, check=True)
            if stage_plan:
                subprocess.run(["git", "add", ".governance/plan-tracker.md"], cwd=root, check=True)

            hook = _INFRA_DIR / "hooks" / "pre-commit"
            return subprocess.run(
                [self._bash(), hook.as_posix()],
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

    def test_pre_commit_allows_claude_bootstrap_self_upgrade(self):
        result = self._run_hook(plan_version="0.37.0", initial_version="0.35.0", stage_plan=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("bootstrap self-upgrade detected", result.stdout)

    def test_pre_commit_blocks_direct_claude_change_without_plan_version(self):
        result = self._run_hook(stage_plan=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BOOTSTRAP DISCIPLINE", result.stdout)

    def test_pre_commit_blocks_claude_upgrade_with_version_mismatch(self):
        result = self._run_hook(plan_version="0.35.0", initial_version="0.34.0", stage_plan=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BOOTSTRAP DISCIPLINE", result.stdout)

    def test_pre_commit_blocks_same_version_claude_change_with_plan_staged(self):
        result = self._run_hook(plan_version="0.37.0", initial_version="0.37.0", stage_plan=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BOOTSTRAP DISCIPLINE", result.stdout)

    def test_pre_commit_blocks_non_bootstrap_claude_change_during_upgrade(self):
        result = self._run_hook(
            plan_version="0.37.0",
            initial_version="0.35.0",
            stage_plan=True,
            change_outside_bootstrap=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("BOOTSTRAP DISCIPLINE", result.stdout)


class ExternalInstalledRuntimePathResolverTests(unittest.TestCase):
    """FIX-132: hooks and native commands must work without repo-local skills/."""

    def _bash(self):
        if os.name == "nt":
            candidates = [
                Path(os.environ.get("ProgramFiles", "")) / "Git" / "bin" / "bash.exe",
                Path(os.environ.get("ProgramFiles(x86)", "")) / "Git" / "bin" / "bash.exe",
            ]
            for candidate in candidates:
                if candidate.exists():
                    return str(candidate)
        return shutil.which("bash") or "bash"

    def _init_target_repo(self, root: Path) -> None:
        root.mkdir()
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True, text=True)
        gov = root / ".governance"
        gov.mkdir(parents=True)
        (gov / "plan-tracker.md").write_text("## 项目配置\n- **工作流版本**: 0.50.2\n", encoding="utf-8")

    def _write_source_home(self, source_home: Path, hook_name: str = "pre-commit") -> Path:
        source_hooks = source_home / "infra" / "hooks"
        source_hooks.mkdir(parents=True)
        (source_home / "SKILL.md").write_text("---\nversion: 0.50.2\n---\n", encoding="utf-8")
        shutil.copyfile(_INFRA_DIR / "hooks" / hook_name, source_hooks / hook_name)
        return source_hooks / hook_name

    def test_pre_commit_self_upgrade_uses_explicit_installed_workflow_home(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "target"
            self._init_target_repo(root)

            source_home = Path(td) / "installed" / "skills" / "software-project-governance"
            source_hook = self._write_source_home(source_home)

            installed_hook = root / ".git" / "hooks" / "pre-commit"
            shutil.copyfile(_INFRA_DIR / "hooks" / "pre-commit", installed_hook)
            installed_hook.write_text(
                installed_hook.read_text(encoding="utf-8") + "\n# stale installed copy\n",
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["SOFTWARE_PROJECT_GOVERNANCE_HOME"] = source_home.as_posix()
            result = subprocess.run(
                [self._bash(), installed_hook.as_posix()],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("self-upgraded", result.stdout)
            self.assertFalse((root / "skills" / "software-project-governance").exists())
            self.assertEqual(
                installed_hook.read_text(encoding="utf-8"),
                source_hook.read_text(encoding="utf-8"),
            )

    def test_pre_commit_self_upgrade_discovers_plugin_cache_without_repo_local_skills(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "target"
            self._init_target_repo(root)

            fake_home = Path(td) / "home"
            source_home = (
                fake_home
                / ".claude"
                / "plugins"
                / "cache"
                / "openai-bundled"
                / "software-project-governance"
                / "0.50.2"
                / "skills"
                / "software-project-governance"
            )
            source_hook = self._write_source_home(source_home)

            installed_hook = root / ".git" / "hooks" / "pre-commit"
            shutil.copyfile(_INFRA_DIR / "hooks" / "pre-commit", installed_hook)
            installed_hook.write_text(
                installed_hook.read_text(encoding="utf-8") + "\n# stale cache-discovered copy\n",
                encoding="utf-8",
            )

            env = os.environ.copy()
            env.pop("SOFTWARE_PROJECT_GOVERNANCE_HOME", None)
            env.pop("SPG_HOME", None)
            env.pop("XDG_CACHE_HOME", None)
            env["HOME"] = fake_home.as_posix()
            result = subprocess.run(
                [self._bash(), installed_hook.as_posix()],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("self-upgraded", result.stdout)
            self.assertFalse((root / "skills" / "software-project-governance").exists())
            self.assertEqual(installed_hook.read_text(encoding="utf-8"), source_hook.read_text(encoding="utf-8"))

    def test_pre_commit_source_hook_run_by_relative_path_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "target"
            self._init_target_repo(root)

            project_source_home = root / "skills" / "software-project-governance"
            project_source_hook = self._write_source_home(project_source_home)
            marker = "\n# local source hook marker must remain\n"
            project_source_hook.write_text(project_source_hook.read_text(encoding="utf-8") + marker, encoding="utf-8")

            external_source_home = Path(td) / "external" / "skills" / "software-project-governance"
            external_source_hook = self._write_source_home(external_source_home)
            external_source_hook.write_text(
                external_source_hook.read_text(encoding="utf-8") + "\n# external source hook marker\n",
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["SOFTWARE_PROJECT_GOVERNANCE_HOME"] = external_source_home.as_posix()
            result = subprocess.run(
                [self._bash(), "skills/software-project-governance/infra/hooks/pre-commit"],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("self-upgraded", result.stdout)
            self.assertIn(marker.strip(), project_source_hook.read_text(encoding="utf-8"))
            self.assertNotEqual(
                project_source_hook.read_text(encoding="utf-8"),
                external_source_hook.read_text(encoding="utf-8"),
            )

    def test_hooks_contain_external_runtime_resolver(self):
        for hook_name in ("pre-commit", "commit-msg", "post-commit"):
            text = (_INFRA_DIR / "hooks" / hook_name).read_text(encoding="utf-8")
            self.assertIn("SOFTWARE_PROJECT_GOVERNANCE_HOME", text, hook_name)
            self.assertIn("SPG_HOME", text, hook_name)
            self.assertIn(".claude/plugins/cache", text, hook_name)
            self.assertIn("SPG_RESOLVED_HOME/infra/hooks", text, hook_name)
            self.assertIn("git rev-parse --git-path", text, hook_name)
            self.assertNotIn("IS_SOURCE_HOOK", text, hook_name)

    def test_governance_commands_do_not_emit_repo_local_hook_install_only(self):
        for rel in (
            "commands/governance-init.md",
            "commands/governance.md",
            "commands/governance-status.md",
            "commands/governance-verify.md",
        ):
            text = (vw.ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("WORKFLOW_HOME", text, rel)
            self.assertNotIn("cp skills/software-project-governance/infra/hooks", text, rel)
            self.assertNotIn("python skills/software-project-governance/infra/verify_workflow.py", text, rel)


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


class GateAutoJudgmentEvidenceQualityTests(unittest.TestCase):
    """FIX-067: G10/G11 should use real evidence, not weak proxy keywords."""

    def _setup(self, tmpdir, plan="", evidence="", risk=""):
        root = Path(tmpdir)
        gov = root / ".governance"
        gov.mkdir(parents=True, exist_ok=True)
        sp = gov / "plan-tracker.md"
        ep = gov / "evidence-log.md"
        rp = gov / "risk-log.md"
        sp.write_text(plan, encoding="utf-8")
        ep.write_text(evidence, encoding="utf-8")
        rp.write_text(risk, encoding="utf-8")
        return sp, ep, rp, gov

    def _patch_governance_paths(self, sp, ep, rp):
        return patch.multiple(vw, SAMPLE_PATH=sp, EVIDENCE_PATH=ep, RISK_PATH=rp)

    def test_auto_judge_gate_reads_registry_check_definitions(self):
        """FIX-138: gate judgment is registry-backed for classic G1-G11."""
        data = json.loads(vw.LIFECYCLE_REGISTRY_PATH.read_text(encoding="utf-8"))
        data["gate_execution_registry"]["gate_checks"][0]["checks"] = [
            {
                "check_id": "registry_sentinel",
                "label": "Registry sentinel check",
                "executor": "constant_result",
                "severity": "low",
                "result": "PASS",
                "message": "registry path executed",
            }
        ]
        data["gate_execution_registry"]["gate_checks"][0]["automation_command"]["command"] = (
            "python -c \"raise SystemExit(99)\""
        )

        with patch.object(vw, "_load_lifecycle_registry", return_value=(data, [])):
            result = vw.auto_judge_gate("G1")

        self.assertEqual(result["overall"], "passed")
        self.assertEqual(result["items"], [{
            "check": "Registry sentinel check",
            "result": "PASS",
            "detail": "registry path executed",
        }])

    def test_auto_judge_gate_blocks_malformed_registry_checks_before_execution(self):
        """FIX-138 review rework: runtime path validates registry contract fail-closed."""
        cases = [
            ("non-list checks", {"not": "a list"}, "checks must be a non-empty list"),
            ("malformed check entry", ["bad-check"], "checks entries must be objects"),
        ]
        for label, checks_value, expected_detail in cases:
            with self.subTest(label=label):
                data = json.loads(vw.LIFECYCLE_REGISTRY_PATH.read_text(encoding="utf-8"))
                data["gate_execution_registry"]["gate_checks"][0]["checks"] = checks_value

                with patch.object(vw, "_load_lifecycle_registry", return_value=(data, [])):
                    result = vw.auto_judge_gate("G1")

                self.assertEqual(result["overall"], "blocked")
                self.assertEqual(result["items"][0]["check"], "Gate execution registry contract")
                self.assertEqual(result["items"][0]["result"], "FAIL")
                self.assertIn(expected_detail, result["items"][0]["detail"])
                self.assertIn("registry validation failed", result["summary"])

    def test_g10_weak_proxies_do_not_pass(self):
        """复盘/DEC/P0 alone are not credible G10 operation evidence."""
        with tempfile.TemporaryDirectory() as td:
            plan = "\n".join([
                "# 计划跟踪",
                "## 当前活跃事项",
                "| 优先级 | ID | 事项 | 状态 |",
                "| --- | --- | --- | --- |",
                "| **P0** | FIX-001 | 下轮方向 | 进行中 |",
            ])
            evidence = _evidence_row_generic(
                "EVD-001", "FIX-001",
                description="复盘完成，但没有运营数据、反馈分类、问题清单或可执行优化项",
                gate="G10",
            )
            risk = "| RISK-001 | 2026-05-01 | 问题 | 维护 | x | x | 高 | Owner | 打开 | x | x | x |"
            sp, ep, rp, _ = self._setup(td, plan=plan, evidence=evidence, risk=risk)

            with self._patch_governance_paths(sp, ep, rp):
                result = vw.auto_judge_gate("G10")

            self.assertNotEqual(result["overall"], "passed")
            self.assertTrue(any(item["result"] == "NEEDS_HUMAN" for item in result["items"]))

    def test_g10_archive_evidence_can_pass(self):
        """Archived evidence participates in G10 PASS judgment."""
        with tempfile.TemporaryDirectory() as td:
            sp, ep, rp, gov = self._setup(td, plan="# 计划跟踪\n")
            archive = gov / "archive"
            evidence_dir = archive / "evidence"
            evidence_dir.mkdir(parents=True)
            (archive / "index.md").write_text("index", encoding="utf-8")
            archived_evidence = _evidence_row_generic(
                "EVD-777", "OPS-001",
                description=(
                    "真实运营数据：至少 1 周真实运行数据；用户反馈已归档并按类别分类；"
                    "问题清单：问题项 ISSUE-001 登录失败，严重级别=高风险，状态=打开；"
                    "可执行优化项含 Owner、截止和验证命令"
                ),
                gate="G10",
            )
            (evidence_dir / "v0.1.0.md").write_text(archived_evidence, encoding="utf-8")

            with self._patch_governance_paths(sp, ep, rp):
                result = vw.auto_judge_gate("G10")

            self.assertEqual(result["overall"], "passed")
            self.assertTrue(all(item["result"] == "PASS" for item in result["items"]))

    def test_g11_weak_proxies_do_not_pass(self):
        """Any retro keyword + any P0 must not pass G11."""
        with tempfile.TemporaryDirectory() as td:
            plan = "\n".join([
                "# 计划跟踪",
                "## 当前活跃事项",
                "| 优先级 | ID | 事项 | 状态 |",
                "| --- | --- | --- | --- |",
                "| **P0** | FIX-001 | 普通优先级代理 | 进行中 |",
            ])
            evidence = _evidence_row_generic(
                "EVD-001", "FIX-001",
                description="复盘 已完成；behavior-protocol.md 含 MUST",
                gate="G11",
            )
            sp, ep, rp, _ = self._setup(td, plan=plan, evidence=evidence)

            with self._patch_governance_paths(sp, ep, rp), \
                 patch.object(vw, "_check_version_consistency_heuristic",
                              return_value=("PASS", "version ok")):
                result = vw.auto_judge_gate("G11")

            self.assertNotEqual(result["overall"], "passed")
            self.assertTrue(any(item["result"] == "NEEDS_HUMAN" for item in result["items"]))

    def test_g11_archive_evidence_can_pass_with_active_p0(self):
        """Archived retro/backfill evidence can satisfy G11."""
        with tempfile.TemporaryDirectory() as td:
            plan = "\n".join([
                "# 计划跟踪",
                "## 当前活跃事项",
                "| 优先级 | ID | 事项 | 状态 |",
                "| --- | --- | --- | --- |",
                "| **P0** | NEXT-001 | 下一轮核心方向 | 进行中 |",
            ])
            sp, ep, rp, gov = self._setup(td, plan=plan)
            archive = gov / "archive"
            evidence_dir = archive / "evidence"
            evidence_dir.mkdir(parents=True)
            (archive / "index.md").write_text("index", encoding="utf-8")
            archived_evidence = _evidence_row_generic(
                "EVD-778", "RETRO-001",
                description=(
                    "复盘文档包含目标回顾、结果评估、原因分析、经验沉淀；"
                    "经验回灌到规则和模板，提交 commit abc123，文件变更 stage-gates.md"
                ),
                gate="G11",
            )
            (evidence_dir / "v0.1.0.md").write_text(archived_evidence, encoding="utf-8")

            with self._patch_governance_paths(sp, ep, rp), \
                 patch.object(vw, "_check_version_consistency_heuristic",
                              return_value=("PASS", "version ok")):
                result = vw.auto_judge_gate("G11")

            self.assertEqual(result["overall"], "passed")
            self.assertTrue(all(item["result"] == "PASS" for item in result["items"]))

    def test_g11_missing_next_round_direction_fails(self):
        """Missing next-round plan remains a blocking G11 failure."""
        with tempfile.TemporaryDirectory() as td:
            evidence = _evidence_row_generic(
                "EVD-001", "RETRO-001",
                description=(
                    "目标回顾、结果评估、原因分析、经验沉淀；"
                    "经验回灌到规则和模板，提交 commit abc123，文件变更 template.md"
                ),
                gate="G11",
            )
            sp, ep, rp, _ = self._setup(td, plan="# 计划跟踪\n## 当前活跃事项\n", evidence=evidence)

            with self._patch_governance_paths(sp, ep, rp), \
                 patch.object(vw, "_check_version_consistency_heuristic",
                              return_value=("PASS", "version ok")):
                result = vw.auto_judge_gate("G11")

            self.assertEqual(result["overall"], "blocked")
            details = "\n".join(item["detail"] for item in result["items"])
            self.assertIn("未检测到计划中的下一轮方向", details)

    def test_g11_completed_or_terminated_p0_is_not_active_direction(self):
        """Completed/terminated P0 rows do not satisfy next-round direction."""
        with tempfile.TemporaryDirectory() as td:
            plan = "\n".join([
                "# 计划跟踪",
                "## 当前活跃事项",
                "| 优先级 | ID | 事项 | 状态 |",
                "| --- | --- | --- | --- |",
                "| **P0** | OLD-001 | 下一轮旧方向 | 已完成 |",
                "| **P0** | OLD-002 | 下一轮终止方向 | 已终止 |",
            ])
            evidence = _evidence_row_generic(
                "EVD-001", "RETRO-001",
                description=(
                    "目标回顾、结果评估、原因分析、经验沉淀；"
                    "经验回灌到规则和模板，提交 commit abc123，文件变更 template.md"
                ),
                gate="G11",
            )
            sp, ep, rp, _ = self._setup(td, plan=plan, evidence=evidence)

            with self._patch_governance_paths(sp, ep, rp), \
                 patch.object(vw, "_check_version_consistency_heuristic",
                              return_value=("PASS", "version ok")):
                result = vw.auto_judge_gate("G11")

            self.assertEqual(result["overall"], "blocked")
            details = "\n".join(item["detail"] for item in result["items"])
            self.assertIn("未检测到计划中的下一轮方向", details)

    def test_g11_retro_keywords_split_across_rows_do_not_pass(self):
        """Retro four elements must be present in one evidence unit."""
        with tempfile.TemporaryDirectory() as td:
            plan = "\n".join([
                "# 计划跟踪",
                "## 当前活跃事项",
                "| 优先级 | ID | 事项 | 状态 |",
                "| --- | --- | --- | --- |",
                "| **P0** | NEXT-001 | 下一轮核心方向 | 进行中 |",
            ])
            evidence = "\n".join([
                _evidence_row_generic("EVD-001", "RETRO-001", description="目标回顾", gate="G11"),
                _evidence_row_generic("EVD-002", "RETRO-001", description="结果评估", gate="G11"),
                _evidence_row_generic("EVD-003", "RETRO-001", description="原因分析", gate="G11"),
                _evidence_row_generic("EVD-004", "RETRO-001", description="经验沉淀", gate="G11"),
                _evidence_row_generic(
                    "EVD-005", "RETRO-001",
                    description="经验回灌到规则和模板，提交 commit abc123，文件变更 template.md",
                    gate="G11",
                ),
            ])
            sp, ep, rp, _ = self._setup(td, plan=plan, evidence=evidence)

            with self._patch_governance_paths(sp, ep, rp), \
                 patch.object(vw, "_check_version_consistency_heuristic",
                              return_value=("PASS", "version ok")):
                result = vw.auto_judge_gate("G11")

            self.assertEqual(result["overall"], "passed-with-conditions")
            details = "\n".join(item["detail"] for item in result["items"])
            self.assertIn("分散在多条证据", details)

    def test_g10_in_progress_status_is_not_severity_signal(self):
        """进行中 must not satisfy issue severity by its 中 character."""
        with tempfile.TemporaryDirectory() as td:
            evidence = _evidence_row_generic(
                "EVD-001", "OPS-001",
                description=(
                    "真实运营数据：至少 1 周真实运行数据；用户反馈已归档并按类别分类；"
                    "问题清单包含状态：进行中；可执行优化项含 Owner、截止和验证命令"
                ),
                gate="G10",
            )
            sp, ep, rp, _ = self._setup(td, plan="# 计划跟踪\n", evidence=evidence)

            with self._patch_governance_paths(sp, ep, rp):
                result = vw.auto_judge_gate("G10")

            self.assertEqual(result["overall"], "passed-with-conditions")
            issue_item = next(item for item in result["items"] if "关键问题" in item["check"])
            self.assertEqual(issue_item["result"], "NEEDS_HUMAN")

    def test_g10_issue_schema_only_line_does_not_pass(self):
        """Schema/header-only issue-list fields are not real classified issues."""
        with tempfile.TemporaryDirectory() as td:
            evidence = _evidence_row_generic(
                "EVD-001", "OPS-001",
                description=(
                    "真实运营数据：至少 1 周真实运行数据；用户反馈已归档并按类别分类；"
                    "问题清单字段：严重级别、状态；可执行优化项含 Owner、截止和验证命令"
                ),
                gate="G10",
            )
            sp, ep, rp, _ = self._setup(td, plan="# 计划跟踪\n", evidence=evidence)

            with self._patch_governance_paths(sp, ep, rp):
                result = vw.auto_judge_gate("G10")

            self.assertEqual(result["overall"], "passed-with-conditions")
            issue_item = next(item for item in result["items"] if "关键问题" in item["check"])
            self.assertEqual(issue_item["result"], "NEEDS_HUMAN")

    def test_g10_real_issue_item_with_severity_and_status_passes(self):
        """A real issue item with severity value and status value satisfies G10."""
        with tempfile.TemporaryDirectory() as td:
            evidence = _evidence_row_generic(
                "EVD-001", "OPS-001",
                description=(
                    "真实运营数据：至少 1 周真实运行数据；用户反馈已归档并按类别分类；"
                    "问题清单：问题项 ISSUE-001 初始化失败，严重级别=high，状态=closed；"
                    "可执行优化项含 Owner、截止和验证命令"
                ),
                gate="G10",
            )
            sp, ep, rp, _ = self._setup(td, plan="# 计划跟踪\n", evidence=evidence)

            with self._patch_governance_paths(sp, ep, rp):
                result = vw.auto_judge_gate("G10")

            self.assertEqual(result["overall"], "passed")
            issue_item = next(item for item in result["items"] if "关键问题" in item["check"])
            self.assertEqual(issue_item["result"], "PASS")


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

    def test_check_agent_team_review_accepts_review_prefixed_hot_rows(self):
        """FIX-073: human-readable REVIEW-* rows count as review coverage."""
        with tempfile.TemporaryDirectory() as td:
            plan = "\n".join([
                "# 计划跟踪",
                "",
                "## 当前活跃事项",
                "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
                "|--------|----|------|------|---------|---------|------|",
                "| **P1** | FIX-073 | guardrails | AUDIT-100 | 0.35.0 | tests | ✅ 已完成 |",
            ])
            evidence_rows = [
                _evidence_row_generic(
                    "EVD-073", "FIX-073",
                    evd_type="实现",
                    file_location="skills/software-project-governance/infra/verify_workflow.py",
                ),
                "| REVIEW-FIX-073 | FIX-073 | 维护 | 代码审查 | Code Reviewer APPROVED for FIX-073 | transcript | Code Reviewer | 2026-05-20 | G11 | APPROVED |",
            ]
            sp, ep = self._setup(td, plan_lines=[plan], evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_agent_team_review()
            self.assertTrue(r["pass"])
            self.assertEqual(r["total_tasks"], 1)
            self.assertEqual(r["reviewed"], 1)

    def test_check_agent_team_review_ignores_degraded_review_evidence(self):
        """FIX-085: degraded runtime evidence must not unlock product-code closure."""
        with tempfile.TemporaryDirectory() as td:
            plan = "\n".join([
                "# 计划跟踪",
                "",
                "## 当前活跃事项",
                "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
                "|--------|----|------|------|---------|---------|------|",
                "| **P0** | FIX-085 | degraded review guard | DEC-068 | 0.38.0 | tests | ✅ 已完成 |",
            ])
            evidence_rows = [
                _evidence_row_generic(
                    "EVD-085", "FIX-085",
                    evd_type="实现",
                    file_location="skills/software-project-governance/infra/verify_workflow.py",
                ),
                "| REVIEW-FIX-085 | FIX-085 | 维护 | 代码审查 | "
                "Reviewer runtime 不可用，DEGRADED_EVIDENCE；"
                "不构成独立审查，不得计入审查通过，不得解锁产品代码交付 | "
                "runtime fallback | Coordinator | 2026-05-23 | G11 | DEGRADED_EVIDENCE |",
            ]
            sp, ep = self._setup(td, plan_lines=[plan], evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_agent_team_review()
                coverage = vw._parse_review_covered_tasks()
            self.assertFalse(r["pass"])
            self.assertEqual(r["reviewed"], 0)
            self.assertEqual(r["unreviewed"], 1)
            self.assertIn("FIX-085", r["review_gap_tasks"])
            self.assertEqual(coverage, {})
            self.assertEqual(len(r["ignored_review_entries"]), 1)
            self.assertIn("degraded", r["ignored_review_entries"][0]["reason"])

    def test_check_agent_team_review_ignores_coordinator_self_review(self):
        """FIX-085: Coordinator-authored REVIEW rows are not independent review."""
        with tempfile.TemporaryDirectory() as td:
            plan = "\n".join([
                "# 计划跟踪",
                "",
                "## 当前活跃事项",
                "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
                "|--------|----|------|------|---------|---------|------|",
                "| **P0** | FIX-086 | self review guard | DEC-068 | 0.38.0 | tests | ✅ 已完成 |",
            ])
            evidence_rows = [
                _evidence_row_generic(
                    "EVD-086", "FIX-086",
                    evd_type="实现",
                    file_location="skills/software-project-governance/infra/verify_workflow.py",
                ),
                "| REVIEW-FIX-086 | FIX-086 | 维护 | 代码审查 | "
                "Coordinator self-review APPROVED for FIX-086 | transcript | "
                "Coordinator | 2026-05-23 | G11 | APPROVED |",
            ]
            sp, ep = self._setup(td, plan_lines=[plan], evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_agent_team_review()
            self.assertFalse(r["pass"])
            self.assertEqual(r["reviewed"], 0)
            self.assertEqual(r["unreviewed"], 1)
            self.assertIn("FIX-086", r["review_gap_tasks"])
            self.assertIn("self-review", r["ignored_review_entries"][0]["reason"])

    def test_check_agent_team_review_does_not_count_audit_evidence_as_product_delivery(self):
        """FIX-073: audit/review evidence mentioning product files is not implementation debt."""
        with tempfile.TemporaryDirectory() as td:
            plan = "\n".join([
                "# 计划跟踪",
                "",
                "## 当前活跃事项",
                "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
                "|--------|----|------|------|---------|---------|------|",
                "| **P0** | AUDIT-100 | audit | 用户请求 | 0.35.0 | review | ✅ 已完成 |",
            ])
            evidence_rows = [
                _evidence_row_generic(
                    "EVD-100", "AUDIT-100",
                    evd_type="八维度审查",
                    file_location="skills/software-project-governance/infra/verify_workflow.py",
                ),
            ]
            sp, ep = self._setup(td, plan_lines=[plan], evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_agent_team_review()
            self.assertTrue(r["pass"])
            self.assertEqual(r["total_tasks"], 0)

    def test_check_review_coverage_excludes_priority_first_p2_rows(self):
        """FIX-073: Check 21 keeps P2 exclusion for priority-first hot tables."""
        with tempfile.TemporaryDirectory() as td:
            plan = "\n".join([
                "# 计划跟踪",
                "",
                "## 当前活跃事项",
                "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
                "|--------|----|------|------|---------|---------|------|",
                "| **P2** | FIX-222 | optional cleanup | AUDIT-100 | 0.35.0 | tests | ✅ 已完成 |",
            ])
            evidence_rows = [
                _evidence_row_generic(
                    "EVD-222", "FIX-222",
                    evd_type="实现",
                    file_location="skills/software-project-governance/infra/verify_workflow.py",
                ),
            ]
            sp, ep = self._setup(td, plan_lines=[plan], evidence_lines=evidence_rows)
            with patch.object(vw, "SAMPLE_PATH", sp), \
                 patch.object(vw, "EVIDENCE_PATH", ep):
                r = vw.check_review_coverage()
            self.assertTrue(r["pass"])
            self.assertEqual(r["total_tasks"], 0)


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
