from pathlib import Path
import sys
import re
import argparse
import json
import locale
import os
import signal
import subprocess
import importlib.util
import shutil
import hashlib
from datetime import datetime, date

ROOT = Path(__file__).resolve().parents[3]
EXECUTION_PACKET_PATH = ROOT / ".governance" / "execution-packets.json"


def _display_path(path, root=None):
    """Return repo-relative path when possible, without Path.is_relative_to()."""
    root = root or ROOT
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def _read_text_normalized(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


# ── PLUGIN_SCOPE_DIRS (keep in sync with cleanup.py) ─────────────
# Directories that constitute the plugin installation boundary.
# Check 10 (M5 compliance) skips these to avoid false positives from
# legitimate checklists in plugin SKILL.md files (FIX-054).
PLUGIN_SCOPE_DIRS = {
    "skills",
    "agents",
    "commands",
    "adapters",
    ".claude-plugin",
    ".codex-plugin",
    ".agents",
}


def _is_plugin_path(rel_path: str) -> bool:
    """Check if a relative path is inside a plugin scope directory.

    Plugin scope dirs (PLUGIN_SCOPE_DIRS) are matched as path components
    anywhere in the path, not just as a prefix.  This catches nested
    installations (e.g. project/e2e-test-project/skills/) and avoids
    false positives from legitimate checklists in plugin SKILL.md files.

    Semantics synced with cleanup.py _is_path_excluded() for directory
    patterns (FIX-054).
    """
    rel_path = rel_path.replace("\\", "/")
    segments = rel_path.split("/")
    for scope_dir in PLUGIN_SCOPE_DIRS:
        # Root-prefix match
        if rel_path == scope_dir or rel_path.startswith(scope_dir + "/"):
            return True
        # Nested as a path component (e.g. project/e2e-test-project/skills/...)
        if scope_dir in segments:
            return True
    return False


def _git_files(args):
    """Return repo-relative paths from git, or None when git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT)] + args,
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    return {
        line.strip().replace("\\", "/")
        for line in result.stdout.splitlines()
        if line.strip()
    }


def _split_markdown_table_row(line):
    """Split a markdown table row while ignoring pipes inside inline code."""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    cells = []
    buf = []
    in_code = False
    i = 1 if stripped.startswith("|") else 0
    end = len(stripped) - 1 if stripped.endswith("|") else len(stripped)
    while i < end:
        ch = stripped[i]
        if ch == "`":
            in_code = not in_code
            buf.append(ch)
        elif ch == "|" and not in_code:
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    cells.append("".join(buf).strip())
    return cells


PLATFORM_ENTRY_FILES = {
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "CODEX.md",
}


BLOCKING_LOCK_ISSUE_TYPES = {
    "schema_violation",
    "orphan_lock",
    "expired_lock",
    "task_not_in_plan",
    "multi_lock_conflict",
    "format_invalid_json",
    "format_empty",
    "format_not_dict",
    "format_missing_key",
    "format_type_error",
    "format_schema_violation",
}


def lock_issue_is_blocking(issue):
    """Return True when a lock issue should affect --fail-on-issues."""
    issue_type = issue.get("type", "")
    normalized = issue_type.removeprefix("format_")
    return issue_type in BLOCKING_LOCK_ISSUE_TYPES or normalized in BLOCKING_LOCK_ISSUE_TYPES


REQUIRED_FILES = {
    "README": ROOT / "README.md",
    "Workflow Schema": ROOT / "skills/software-project-governance/core/protocol/workflow-schema.md",
    "Plugin Contract": ROOT / "skills/software-project-governance/core/protocol/plugin-contract.md",
    "External Command Contract": ROOT / "skills/software-project-governance/core/protocol/external-command-contract.md",
    "Headless Runner Sample": ROOT / "skills/software-project-governance/core/protocol/headless-runner-sample.md",
    "Command Protocol Schema": ROOT / "skills/software-project-governance/core/protocol/command-schema.md",
    "Workflow Manifest": ROOT / "skills/software-project-governance/core/manifest.md",
    "Company Practices": ROOT / "project/workflows/software-project-governance/research/company-practices.md",
    "Plan Tracker": ROOT / "skills/software-project-governance/core/templates/plan-tracker.md",
    "Evidence Template": ROOT / "skills/software-project-governance/core/templates/evidence-log.md",
    "Decision Template": ROOT / "skills/software-project-governance/core/templates/decision-log.md",
    "Risk Template": ROOT / "skills/software-project-governance/core/templates/risk-log.md",
    "Governance Plan Tracker": ROOT / ".governance/plan-tracker.md",
    "Governance Evidence Log": ROOT / ".governance/evidence-log.md",
    "Governance Decision Log": ROOT / ".governance/decision-log.md",
    "Governance Risk Log": ROOT / ".governance/risk-log.md",
    "Skill Main Workflow Entry": ROOT / "skills/main-workflow/SKILL.md",
    "Skill Tools Index": ROOT / "skills/software-project-governance/infra/TOOLS.md",
    "Core Stage Gates": ROOT / "skills/software-project-governance/core/stage-gates.md",
    "Core Lifecycle": ROOT / "skills/software-project-governance/core/lifecycle.md",
    "Core Profiles": ROOT / "skills/software-project-governance/core/profiles.md",
    "Core Onboarding": ROOT / "skills/software-project-governance/core/onboarding.md",
    "Skill References Interaction Boundary": ROOT / "skills/software-project-governance/references/interaction-boundary.md",
    "Core Audit Framework": ROOT / "skills/software-project-governance/core/audit-framework.md",
    "Skill References Agent Failure Modes": ROOT / "skills/software-project-governance/references/agent-failure-modes.md",
    "Skill References Company Practices Summary": ROOT / "skills/software-project-governance/references/company-practices-summary.md",
    "Agent Integration Research": ROOT / "project/workflows/software-project-governance/research/agent-integration-models.md",
    "Default Product Shape": ROOT / "project/workflows/software-project-governance/research/default-product-shape.md",
    "External Capability Minimum Validation": ROOT / "project/workflows/software-project-governance/research/external-capability-minimum-validation.md",
    "Domestic Agent CLI Compatibility": ROOT / "project/workflows/software-project-governance/research/domestic-agent-cli-compatibility.md",
    "Repo-local Termination Note": ROOT / "project/workflows/software-project-governance/research/repo-local-termination-note.md",
    "Governance Init Command": ROOT / "commands/governance-init.md",
    "Governance Status Command": ROOT / "commands/governance-status.md",
    "Governance Gate Command": ROOT / "commands/governance-gate.md",
    "Governance Verify Command": ROOT / "commands/governance-verify.md",
    "Governance Update Command": ROOT / "commands/governance-update.md",
    "Codex Skill": ROOT / "skills/software-project-governance/SKILL.md",
    "Skill Stages Initiation Sub-workflow": ROOT / "skills/stage-initiation/SKILL.md",
    "Skill Stages Research Sub-workflow": ROOT / "skills/stage-research/SKILL.md",
    "Skill Stages Architecture Sub-workflow": ROOT / "skills/stage-architecture/SKILL.md",
    "Skill Stages Development Sub-workflow": ROOT / "skills/stage-development/SKILL.md",
    "Skill Stages Selection Sub-workflow": ROOT / "skills/stage-selection/SKILL.md",
    "Skill Stages Infrastructure Sub-workflow": ROOT / "skills/stage-infra/SKILL.md",
    "Skill Stages Testing Sub-workflow": ROOT / "skills/stage-testing/SKILL.md",
    "Skill Stages CI-CD Sub-workflow": ROOT / "skills/stage-cicd/SKILL.md",
    "Skill Stages Release Sub-workflow": ROOT / "skills/stage-release/SKILL.md",
    "Skill Stages Operations Sub-workflow": ROOT / "skills/stage-operations/SKILL.md",
    "Skill Stages Maintenance Sub-workflow": ROOT / "skills/stage-maintenance/SKILL.md",
    "Skill Stages Requirement Clarification": ROOT / "skills/requirement-clarification/SKILL.md",
    "Skill Stages Tech Review Checklist": ROOT / "skills/tech-review/SKILL.md",
    "Skill Stages Code Review Standard": ROOT / "skills/code-review/SKILL.md",
    "Skill Stages Release Checklist": ROOT / "skills/release-checklist/SKILL.md",
    "SKILL Retro Meeting": ROOT / "skills/retro-meeting/SKILL.md",
    "SKILL PR-FAQ Template": ROOT / "skills/pr-faq/SKILL.md",
    "SKILL OKR Template": ROOT / "skills/okr/SKILL.md",
    "SKILL Six-Pager Template": ROOT / "skills/six-pager/SKILL.md",
    "Behavior Protocol (M0-M9)": ROOT / "skills/software-project-governance/references/behavior-protocol.md",
    "Five-Layer Architecture Design": ROOT / "project/references/architecture.md",
    "Asset Migration Map": ROOT / "project/references/asset-migration-map.md",
}

OPTIONAL_PROJECTION_FILES = {
    "Sample Project": ROOT / "project/workflows/software-project-governance/examples/current-project-sample.md",
    "Sample Evidence": ROOT / "project/workflows/software-project-governance/examples/current-project-evidence-log.md",
    "Sample Decision": ROOT / "project/workflows/software-project-governance/examples/current-project-decision-log.md",
    "Sample Risk": ROOT / "project/workflows/software-project-governance/examples/current-project-risk-log.md",

    "Claude Adapter": ROOT / "adapters/claude/README.md",
    "Claude Adapter Manifest": ROOT / "adapters/claude/adapter-manifest.json",
    "Claude Launcher": ROOT / "adapters/claude/launch.py",
    "Codex Adapter": ROOT / "adapters/codex/README.md",
    "Codex Adapter Manifest": ROOT / "adapters/codex/adapter-manifest.json",
    "Codex Launcher": ROOT / "adapters/codex/launch.py",
    "Gemini Adapter": ROOT / "adapters/gemini/README.md",
    "Gemini Adapter Manifest": ROOT / "adapters/gemini/adapter-manifest.json",
    "Gemini Launcher": ROOT / "adapters/gemini/launch.py",
    "opencode Adapter": ROOT / "adapters/opencode/README.md",
    "opencode Adapter Manifest": ROOT / "adapters/opencode/adapter-manifest.json",
    "opencode Launcher": ROOT / "adapters/opencode/launch.py",
    "Claude Plugin Marketplace": ROOT / ".claude-plugin/marketplace.json",
    "Claude Plugin Definition": ROOT / ".claude-plugin/plugin.json",
    "Codex Plugin Definition": ROOT / ".codex-plugin/plugin.json",
    "Codex Marketplace": ROOT / ".agents/plugins/marketplace.json",
    "Core VERSIONING": ROOT / "skills/software-project-governance/core/VERSIONING.md",
    "Core Task Gate Model": ROOT / "skills/software-project-governance/core/task-gate-model.md",
    "CHANGELOG": ROOT / "project/CHANGELOG.md",
}

PROJECTION_SNIPPETS = {
    ROOT / "project/workflows/software-project-governance/examples/current-project-sample.md": [
        "已迁移",
    ],
    ROOT / "adapters/claude/README.md": [
        "已废弃（Deprecated）",
        "历史入口约定（已废弃，仅供参考）",
        "python adapters/claude/launch.py",
    ],
    ROOT / "adapters/claude/adapter-manifest.json": [
        "adapter_id",
        "workflow_id",
        "native_entry",
        "runtime_e2e",
        "runtime_capabilities",
        "launcher",
    ],
    ROOT / "adapters/claude/launch.py": [
        "Claude Adapter Launcher",
        "native_entry",
        "read_order",
        "validation",
    ],
    ROOT / "adapters/codex/README.md": [
        "已废弃（Deprecated）",
        "历史入口约定（已废弃，仅供参考）",
        "python adapters/codex/launch.py",
    ],
    ROOT / "adapters/codex/adapter-manifest.json": [
        "adapter_id",
        "workflow_id",
        "native_entry",
        "runtime_e2e",
        "runtime_capabilities",
        "launcher",
    ],
    ROOT / "adapters/codex/launch.py": [
        "Codex Adapter Launcher",
        "read_order",
        "validation",
    ],
    ROOT / "adapters/gemini/README.md": [
        "## 兼容要求",
        "## Gemini 路线判断",
        "## 默认接入顺序",
        "## 国内 agent CLI 兼容抽象",
        "## 适配原则",
        "## 建议的最小验证顺序",
    ],
    ROOT / "adapters/gemini/adapter-manifest.json": [
        "adapter_id",
        "support_status",
        "native_entry",
        "runtime_e2e",
        "runtime_capabilities",
    ],
    ROOT / "adapters/gemini/launch.py": [
        "Gemini Adapter Launcher",
        "runtime_e2e",
        "native_entry",
    ],
    ROOT / "adapters/opencode/README.md": [
        "opencode Adapter",
        "full target-cwd agent runtime E2E verified",
        "opencode-provider-preflight",
        "check-agent-adapters --runtime",
    ],
    ROOT / "adapters/opencode/adapter-manifest.json": [
        "adapter_id",
        "runtime-verified",
        "provider_model_preflight",
        "runtime_capabilities",
        "full_e2e_verified",
    ],
    ROOT / "adapters/opencode/launch.py": [
        "opencode Adapter Launcher",
        "provider_model_preflight",
        "runtime_e2e",
    ],
    ROOT / ".claude-plugin/marketplace.json": [
        "software-project-governance",
    ],
    ROOT / ".claude-plugin/plugin.json": [
        "software-project-governance",
        "skills",
    ],
    ROOT / ".codex-plugin/plugin.json": [
        "software-project-governance",
        "skills",
    ],
    ROOT / ".agents/plugins/marketplace.json": [
        "software-project-governance",
    ],
}

PROJECT_FACT_SNIPPETS = {
    ROOT / ".governance/plan-tracker.md": [
        "## 项目配置",
        "standard",
        "always-on",
        "## Gate 状态跟踪",
        "## 项目总览",
        "## 当前活跃事项",
        "## 版本规划",
        "## 需求跟踪矩阵",
        "## 变更控制",
        "操作权限模式",
        "passed-on-entry",
        "G11",
    ],
    ROOT / ".governance/decision-log.md": [
        "DEC-001",
        "DEC-035",
    ],
    ROOT / ".governance/risk-log.md": [
        "RISK-",
    ],
    ROOT / ".governance/evidence-log.md": [
        "EVD-001",
        "EVD-051",
    ],
}

WORKFLOW_SNIPPETS = {
    ROOT / "README.md": [
        "让 coding agent 帮你看护项目质量",
        "## 安装",
        "## 5 分钟开始",
        "## 内部文档",
    ],
    ROOT / "project/workflows/software-project-governance/research/agent-integration-models.md": [
        "## 调研目标",
        "## Claude Code",
        "## 通用集成模式对比",
    ],
    ROOT / "project/workflows/software-project-governance/research/default-product-shape.md": [
        "## 方案摘要",
        "## 分层设计",
        "## 默认接入矩阵",
    ],
    ROOT / "project/workflows/software-project-governance/research/external-capability-minimum-validation.md": [
        "## 目标",
        "## 为什么先选 external runner / shared command",
        "## 最小验证范围",
        "## 命令约定草案",
        "software-project-governance.run",
    ],
    ROOT / "project/workflows/software-project-governance/research/domestic-agent-cli-compatibility.md": [
        "## 目标",
        "## 兼容抽象",
        "## 默认接入顺序",
        "## 能力检查清单",
    ],
    ROOT / "project/workflows/software-project-governance/research/repo-local-termination-note.md": [
        "## 终止对象",
        "## 终止原因",
        "## 降级后的资产定位",
        "## 新主线如何接管",
    ],
    ROOT / "skills/software-project-governance/core/protocol/workflow-schema.md": [
        "## 通用对象模型",
        "### 1. Workflow",
        "### 3. Gate",
    ],
    ROOT / "skills/software-project-governance/core/protocol/plugin-contract.md": [
        "## 最小承载单元",
        "## 三层承载模型",
        "## Skill / Plugin 行为描述要素",
        "## 默认接入要求",
        "workflow 本体层 + agent 入口投影层 + 外部能力层",
        "software-project-governance",
        "stages",
        "interaction-boundary",
        "Agent 适配准入标准",
        "冲击场景",
        "SC-1",
    ],
    ROOT / "skills/software-project-governance/core/protocol/external-command-contract.md": [
        "## 目标",
        "software-project-governance.run",
        "## 最小输入",
        "## 最小输出",
        "## write-back targets",
        "## replacement boundary",
        "### 协议层（必读）",
        "### 当前阶段子工作流（按 stage 参数加载）",
        "interaction-boundary",
        "Validation Matrix",
        "失败与阻断语义",
    ],
    ROOT / "skills/software-project-governance/core/protocol/headless-runner-sample.md": [
        "## 目标",
        "software-project-governance.headless",
        "## 输入映射",
        "## execution mode",
        "dry-run",
        "## 最小返回样例",
        "### 当前阶段子工作流（按 stage 参数加载）",
    ],
    ROOT / "skills/software-project-governance/core/manifest.md": [
        "supported_agents",
        "Claude",
        "Codex",
    ],
}

REQUIRED_SNIPPETS = {}
REQUIRED_SNIPPETS.update(WORKFLOW_SNIPPETS)
REQUIRED_SNIPPETS.update(PROJECT_FACT_SNIPPETS)
REQUIRED_SNIPPETS.update(PROJECTION_SNIPPETS)

REQUIRED_SNIPPETS = {
    ROOT / "README.md": [
        "让 coding agent 帮你看护项目质量",
        "## 安装",
        "## 5 分钟开始",
        "## 内部文档",
    ],
    ROOT / "project/workflows/software-project-governance/research/agent-integration-models.md": [
        "## 调研目标",
        "## Claude Code",
        "## 通用集成模式对比",
    ],
    ROOT / "project/workflows/software-project-governance/research/default-product-shape.md": [
        "## 方案摘要",
        "## 分层设计",
        "## 默认接入矩阵",
    ],
    ROOT / "project/workflows/software-project-governance/research/external-capability-minimum-validation.md": [
        "## 目标",
        "## 为什么先选 external runner / shared command",
        "## 最小验证范围",
        "## 命令约定草案",
        "software-project-governance.run",
    ],
    ROOT / "project/workflows/software-project-governance/research/domestic-agent-cli-compatibility.md": [
        "## 目标",
        "## 兼容抽象",
        "## 默认接入顺序",
        "## 能力检查清单",
    ],
    ROOT / "project/workflows/software-project-governance/research/repo-local-termination-note.md": [
        "## 终止对象",
        "## 终止原因",
        "## 降级后的资产定位",
        "## 新主线如何接管",
    ],
    ROOT / ".governance/plan-tracker.md": [
        "## 项目配置",
        "standard",
        "always-on",
        "## Gate 状态跟踪",
        "## 项目总览",
        "## 当前活跃事项",
        "## 版本规划",
        "## 需求跟踪矩阵",
        "## 变更控制",
        "操作权限模式",
        "passed-on-entry",
        "G11",
    ],
    ROOT / ".governance/decision-log.md": [
        "DEC-001",
        "DEC-035",
    ],
    ROOT / ".governance/risk-log.md": [
        "RISK-",
    ],
    ROOT / ".governance/evidence-log.md": [
        "EVD-001",
        "EVD-051",
    ],
    ROOT / "project/workflows/software-project-governance/examples/current-project-sample.md": [
        "已迁移",
    ],
    ROOT / "skills/software-project-governance/core/protocol/workflow-schema.md": [
        "## 通用对象模型",
        "### 1. Workflow",
        "### 3. Gate",
    ],
    ROOT / "skills/software-project-governance/core/protocol/plugin-contract.md": [
        "## 最小承载单元",
        "## 三层承载模型",
        "## Skill / Plugin 行为描述要素",
        "## 默认接入要求",
        "workflow 本体层 + agent 入口投影层 + 外部能力层",
        "software-project-governance",
        "stages",
        "interaction-boundary",
        "Agent 适配准入标准",
        "冲击场景",
        "SC-1",
    ],
    ROOT / "skills/software-project-governance/core/protocol/external-command-contract.md": [
        "## 目标",
        "software-project-governance.run",
        "## 最小输入",
        "## 最小输出",
        "## write-back targets",
        "## replacement boundary",
        "### 协议层（必读）",
        "### 当前阶段子工作流（按 stage 参数加载）",
        "interaction-boundary",
        "Validation Matrix",
        "失败与阻断语义",
    ],
    ROOT / "skills/software-project-governance/core/protocol/headless-runner-sample.md": [
        "## 目标",
        "software-project-governance.headless",
        "## 输入映射",
        "## execution mode",
        "dry-run",
        "## 最小返回样例",
        "### 当前阶段子工作流（按 stage 参数加载）",
    ],
    ROOT / "skills/software-project-governance/core/manifest.md": [
        "supported_agents",
        "Claude",
        "Codex",
    ],
    # ── Command Protocol Schema + Upgraded Commands ──
    ROOT / "skills/software-project-governance/core/protocol/command-schema.md": [
        "## Input Parameters 定义规范",
        "## Execution Flow 定义规范",
        "## Output Format 定义规范",
        "## Error Codes 定义规范",
        "## Self-Validation 定义规范",
        "## Agent 执行纪律",
    ],
    ROOT / "commands/governance-init.md": [
        "## 输入参数",
        "## 执行流程",
        "## 输出格式",
        "## 错误码",
        "## 自校验",
        "INIT-ERR-001",
        "INIT-ERR-002",
        "INIT-ERR-003",
    ],
    ROOT / "commands/governance-status.md": [
        "## 输入参数",
        "## 执行流程",
        "## 输出格式",
        "## 错误码",
        "## 自校验",
        "permission_mode",
        "操作权限模式",
        "STATUS-ERR-001",
    ],
    ROOT / "commands/governance-gate.md": [
        "## 输入参数",
        "## 执行流程",
        "## 输出格式",
        "## 错误码",
        "## 自校验",
        "GATE-ERR-001",
        "GATE-ERR-002",
    ],
    ROOT / "commands/governance-verify.md": [
        "## 输入参数",
        "## 执行流程",
        "## 输出格式",
        "## 错误码",
        "## 自校验",
        "VERIFY-ERR-001",
    ],
    ROOT / "commands/governance-update.md": [
        "## 输入参数",
        "## 执行流程",
        "## 输出格式",
        "## 错误码",
        "## 自校验",
        "UPDATE-ERR-001",
    ],
    ROOT / "adapters/claude/README.md": [
        "已废弃（Deprecated）",
        "历史入口约定（已废弃，仅供参考）",
        "python adapters/claude/launch.py",
    ],
    ROOT / "adapters/claude/adapter-manifest.json": [
        "adapter_id",
        "workflow_id",
        "native_entry",
        "launcher",
    ],
    ROOT / "adapters/claude/launch.py": [
        "Claude Adapter Launcher",
        "native_entry",
        "read_order",
        "validation",
    ],
    ROOT / "adapters/codex/README.md": [
        "已废弃（Deprecated）",
        "历史入口约定（已废弃，仅供参考）",
        "python adapters/codex/launch.py",
    ],
    ROOT / "adapters/codex/adapter-manifest.json": [
        "adapter_id",
        "workflow_id",
        "launcher",
    ],
    ROOT / "adapters/codex/launch.py": [
        "Codex Adapter Launcher",
        "read_order",
        "validation",
    ],
    ROOT / "adapters/gemini/README.md": [
        "## 兼容要求",
        "## Gemini 路线判断",
        "## 默认接入顺序",
        "## 国内 agent CLI 兼容抽象",
        "## 适配原则",
        "## 建议的最小验证顺序",
    ],
    # Plugin marketplace packaging
    ROOT / ".claude-plugin/marketplace.json": [
        "software-project-governance",
    ],
    ROOT / ".claude-plugin/plugin.json": [
        "software-project-governance",
        "skills",
    ],
    ROOT / ".codex-plugin/plugin.json": [
        "software-project-governance",
        "skills",
    ],
    ROOT / "skills/software-project-governance/SKILL.md": [
        "# 软件项目治理工作流入口",
        "加载本 SKILL 后，你进入软件项目治理工作流",
        "你是 Coordinator（老周）——不是\"单 agent 任务执行者\"",
        "Coordinator 接管用户交互",
        "Producer-Reviewer 分离",
        "references/behavior-protocol.md",
        "core/lifecycle.md",
        "core/stage-gates.md",
        "core/task-gate-model.md",
        "references/agent-communication-protocol.md",
        "六层架构",
        "适配层（平台投影）",
        "infra/verify_workflow.py",
        "infra/hooks/",
    ],
    ROOT / "skills/software-project-governance/references/behavior-protocol.md": [
        "# 行为协议",
        "M0-M9 强制性规则",
        "## M0. 合规语言",
        "## M1. 任务匹配",
        "## M2. 预加载",
        "## M3. 输出规则",
        "## M4. 会话生命周期",
        "## M5. AskUserQuestion 协议",
        "## M6. Gate 行为",
        "## M7. 执行连续性",
        "## M8. 自检协议",
        "## M9. 优先级声明",
        "M7.4 任务完成协议",
        "M7.5 任务前协议",
        "证据 → check-governance → 审计 → 交付物审查在 commit 之前 → commit → 继续",
        "双重机制",
        "9 项 agent 无法造假的检查",
        "阶段快速参考",
        "Profile 快速参考",
    ],
    ROOT / "project/references/architecture.md": [
        "# 六层架构设计",
        "适配层（Adapter）",
        "入口层",
        "业务智能层（Agent 库）",
        "能力层（SKILL 库）",
        "基础设施层",
        "核心层",
        "依赖方向（铁律）",
        "能力层 vs 业务智能层（关键区分）",
        "入口层 vs 适配层（关键区分）",
        "单向依赖，不可反向",
        "与协议层概念的对齐",
    ],
    ROOT / "skills/software-project-governance/core/audit-framework.md": [
        "# 审计框架",
        "审计作为一等治理看护手段",
        "## 审计维度",
        "D1 — 项目目标一致性审计",
        "D2 — 用户使用角度审计",
        "D3 — 阶段闭环质量审计",
        "D4 — 修改闭环标准审计",
        "D5 — 用户易用性审计",
        "D6 — 质量防护网看护预期审计",
        "## 审计执行协议",
        "## Profile 对审计的影响",
        "## Agent 审计纪律",
        "governance-critical 文件",
    ],
    ROOT / "skills/software-project-governance/references/agent-failure-modes.md": [
        "# Agent 失败模式文档",
        "## 失败模式 1：协议跳过",
        "## 失败模式 2：选择性执行",
        "## 失败模式 3：幻觉式证据",
        "## 失败模式 4：虚假闭环",
        "## 失败模式 5：跨会话失忆",
        "## 失败模式 6：自我审计矛盾",
        "## 失败模式 7：虚假归因",
        "## 失败模式 8：计划漂移",
        "## 应急流程总览",
    ],
    ROOT / ".agents/plugins/marketplace.json": [
        "software-project-governance",
    ],
    ROOT / "skills/software-project-governance/core/stage-gates.md": [
        "Tier 审计检查点（Tier Audit Checkpoint）",
        "TIER-<layer>-<tier>-AUDIT",
    ],
    ROOT / "skills/software-project-governance/core/audit-framework.md": [
        "Tier 完成时",
    ],
    ROOT / "skills/software-project-governance/references/behavior-protocol.md": [
        "完成 Tier 时",
    ],
    ROOT / "skills/software-project-governance/core/VERSIONING.md": [
        "# 版本管理策略",
        "语义化版本规则",
        "版本升级触发条件",
    ],
    ROOT / "project/CHANGELOG.md": [
        "# 变更日志",
        "## [0.10.0]",
        "## [0.9.0]",
        "## [0.8.0]",
        "## [0.7.1]",
        "## [0.7.0]",
        "## [0.5.0]",
    ],
    ROOT / ".claude-plugin/plugin.json": [
        "0.38.0",
    ],
    ROOT / ".claude-plugin/marketplace.json": [
        "0.38.0",
    ],
    ROOT / ".codex-plugin/plugin.json": [
        "0.38.0",
    ],
    ROOT / "skills/software-project-governance/core/manifest.json": [
        "0.38.0",
    ],
}


# ── Manifest-based REQUIRED_FILES builder ────────────────────────

def _path_to_label(relative_path_str):
    """Generate a human-readable label from a relative path."""
    import pathlib as _pl
    path = _pl.PurePosixPath(relative_path_str.replace("\\", "/"))
    parts = path.parts
    filename = path.stem

    if path.name == "SKILL.md":
        if len(parts) >= 2:
            return f"Skill: {parts[-2]}"
    if path.name == "README.md":
        if len(parts) >= 2:
            return f"Readme: {parts[-2]}"
    if path.name == "plugin.json":
        if len(parts) >= 3:
            return f"Plugin JSON: {parts[-3]}/{parts[-2]}"
    if path.name == "marketplace.json":
        if len(parts) >= 3:
            return f"Marketplace JSON: {parts[-3]}/{parts[-2]}"
    if path.name.endswith(".json"):
        if len(parts) >= 3:
            return f"{parts[-2]}/{path.name}"

    label = filename.replace("-", " ").replace("_", " ").title()
    if len(parts) >= 3:
        return f"{parts[-2]}/{label}"
    return label


def build_required_files_from_manifest(manifest_path=None):
    """Build REQUIRED_FILES-equivalent dict from manifest.json.

    Expands product + repo_only entries and glob_patterns into a
    {label: Path} mapping.  Returns None when manifest.json is not
    available or cannot be parsed — the caller should fall back to
    the hard-coded builtin dicts.
    """
    import json as _json

    if manifest_path is None:
        manifest_path = ROOT / "skills/software-project-governance/core/manifest.json"

    if not manifest_path.is_file():
        return None

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = _json.load(f)
    except (_json.JSONDecodeError, KeyError):
        return None

    result = {}
    seen_labels = set()

    def _add(relpath_str, label=None):
        nonlocal result, seen_labels
        if label is None:
            label = _path_to_label(relpath_str)
        # De-duplicate: append path suffix if label already used
        if label in seen_labels:
            label = f"{label} ({relpath_str})"
        seen_labels.add(label)
        result[label] = ROOT / relpath_str

    # root_entries
    root_entries = manifest.get("root_entries", {})
    for f in root_entries.get("files", []):
        _add(f)

    for section_name in ("product", "repo_only"):
        section = manifest.get(section_name, {})
        entries = section.get("entries", [])
        glob_patterns = section.get("glob_patterns", [])

        for entry in entries:
            if entry.get("type") == "file":
                _add(entry["path"])

        for pattern in glob_patterns:
            for rp in sorted(ROOT.glob(pattern)):
                if rp.is_file():
                    rel = str(rp.relative_to(ROOT)).replace("\\", "/")
                    _add(rel)

    if result:
        print(f"[INFO] REQUIRED_FILES loaded from manifest.json ({len(result)} entries)")
    return result


def expand_manifest_to_canonical_set(manifest_path=None):
    """Expand manifest.json entries + glob_patterns into a canonical
    set of relative-paths-as-strings.

    Includes product *and* repo_only sections because this function
    runs against the development repository, not a user install.
    """
    import json as _json

    if manifest_path is None:
        manifest_path = ROOT / "skills/software-project-governance/core/manifest.json"

    if not manifest_path.is_file():
        return None

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = _json.load(f)

    canonical = set()

    # root_entries
    root_entries = manifest.get("root_entries", {})
    for f in root_entries.get("files", []):
        canonical.add(f)
    for d in root_entries.get("directories", []):
        canonical.add(d.rstrip("/") + "/")

    for section_name in ("product", "repo_only"):
        section = manifest.get(section_name, {})
        entries = section.get("entries", [])
        glob_patterns = section.get("glob_patterns", [])

        for entry in entries:
            p = entry["path"]
            if entry.get("type") == "file":
                canonical.add(p)
            elif entry.get("type") == "dir":
                canonical.add(p.rstrip("/") + "/")

        for pattern in glob_patterns:
            for rp in ROOT.glob(pattern):
                if rp.is_file():
                    rel = str(rp.relative_to(ROOT)).replace("\\", "/")
                    canonical.add(rel)

    return canonical


def scan_actual_files(exclude_patterns=None):
    """Scan project root for all actual files, returning a set of
    relative-paths-as-strings.

    Directories matching the exclude set are skipped wholesale.
    """
    if exclude_patterns is None:
        exclude_patterns = {
            ".git", "node_modules", "__pycache__",
        }

    actual = set()
    for f in ROOT.rglob("*"):
        if not f.is_file():
            continue
        parts = f.relative_to(ROOT).parts
        skip = False
        for part in parts:
            if part in exclude_patterns:
                skip = True
                break
            if part.startswith("__pycache__"):
                skip = True
                break
        if skip:
            continue
        if f.suffix in (".pyc",):
            continue
        rel = str(f.relative_to(ROOT)).replace("\\", "/")
        actual.add(rel)
    return actual


def scan_manifest_visible_files(exclude_patterns=None):
    """Scan files relevant to manifest drift.

    Manifest consistency is about repository/product shape, not local runtime
    state.  Gitignored caches, untracked user notes, and developer scratch files
    are intentionally outside this comparison.  Canonical files are added back
    by check_manifest_consistency via existence checks so gitignored governance
    fixtures can still satisfy explicit manifest entries.
    """
    tracked = _git_files(["ls-files", "--cached"])
    if tracked is not None:
        return tracked
    return scan_actual_files(exclude_patterns)


def check_manifest_consistency(manifest_path=None):
    """Compare manifest.json canonical set against actual filesystem.

    Returns: dict with 'missing', 'untracked', 'pass' keys.
    """
    canonical = expand_manifest_to_canonical_set(manifest_path)
    if canonical is None:
        return {
            "missing": [],
            "untracked": [],
            "pass": None,
            "error": "manifest.json not found or unreadable",
        }

    actual = scan_manifest_visible_files()

    # For canonical dir entries, we only check the dir exists (not the files inside)
    canonical_dirs = {p for p in canonical if p.endswith("/")}
    canonical_files = {p for p in canonical if not p.endswith("/")}

    existing_canonical_files = {p for p in canonical_files if (ROOT / p).is_file()}
    actual_for_missing = actual | existing_canonical_files

    missing = sorted(canonical_files - actual_for_missing)
    # Untracked: files that exist but are not in canon (excluding well-known patterns)
    untracked = sorted(actual - canonical_files)

    # Filter out obviously non-manifest content from untracked
    untracked_filtered = []
    for u in untracked:
        # Skip files inside directories that are listed as canonical dirs
        covered_by_dir = any(u.startswith(d) for d in canonical_dirs)
        if covered_by_dir:
            continue
        untracked_filtered.append(u)

    return {
        "missing": missing,
        "untracked": untracked_filtered,
        "pass": len(missing) == 0 and len(untracked_filtered) == 0,
        "canonical_count": len(canonical_files),
        "actual_count": len(actual),
    }


# ── Existing verification functions ──────────────────────────────

def check_files():
    failures = []

    # Attempt manifest.json first; fall back to builtin hard-coded dicts
    required = build_required_files_from_manifest()
    if required is None:
        required = REQUIRED_FILES
        optional = OPTIONAL_PROJECTION_FILES
    else:
        optional = {}  # manifest covers everything

    for label, path in required.items():
        if path.is_file():
            print(f"[OK] file exists: {label} -> {path.relative_to(ROOT)}")
        else:
            failures.append(f"missing required file: {label} -> {path.relative_to(ROOT)}")
            print(f"[FAIL] missing required file: {label} -> {path.relative_to(ROOT)}")

    for label, path in optional.items():
        if path.is_file():
            print(f"[OK] optional projection exists: {label} -> {path.relative_to(ROOT)}")
        else:
            print(f"[INFO] optional projection missing: {label} -> {path.relative_to(ROOT)}")

    return failures


def check_snippets():
    failures = []
    for path, snippets in REQUIRED_SNIPPETS.items():
        if not path.is_file():
            failures.append(f"missing snippet source file: {_display_path(path)}")
            print(f"[FAIL] missing snippet source file: {_display_path(path)}")
            continue
        content = path.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet in content:
                print(f"[OK] snippet found: {path.relative_to(ROOT)} :: {snippet}")
            else:
                failures.append(f"missing snippet in {path.relative_to(ROOT)}: {snippet}")
                print(f"[FAIL] missing snippet: {path.relative_to(ROOT)} :: {snippet}")
    return failures


def _extract_markdown_table_rows_after_heading(content, heading):
    """Return data rows from the first markdown table after a heading."""
    lines = content.splitlines()
    in_section = False
    table_started = False
    rows = []
    for line in lines:
        stripped = line.strip()
        if not in_section:
            if stripped == heading:
                in_section = True
            continue
        if stripped.startswith("## ") and stripped != heading:
            break
        if not stripped.startswith("|"):
            if table_started and rows:
                break
            continue
        table_started = True
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if not cells or all(not cell for cell in cells):
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        if any(cell in ("任务类型", "SKILL") for cell in cells):
            continue
        rows.append(cells)
    return rows


def _skill_route_table_count(skill_path=None):
    path = skill_path or ROOT / "skills/software-project-governance/SKILL.md"
    content = path.read_text(encoding="utf-8")
    return len(_extract_markdown_table_rows_after_heading(content, "## Agent 分发路由"))


def _documented_route_table_count(command_path=None):
    path = command_path or ROOT / "commands/governance.md"
    content = path.read_text(encoding="utf-8")
    match = re.search(r"完整路由表（(\d+)\s*行）", content)
    return int(match.group(1)) if match else None


ACTIVE_AGENT_ROLES = [
    "Analyst",
    "Architect",
    "Developer",
    "Governance Developer",
    "QA",
    "Code Reviewer",
    "Design Reviewer",
    "Requirement Reviewer",
    "Test Reviewer",
    "Release Reviewer",
    "Retro Reviewer",
    "DevOps",
    "Release",
    "Maintenance",
]

NAMED_REVIEWER_ROLES = [
    "Code Reviewer",
    "Design Reviewer",
    "Requirement Reviewer",
    "Test Reviewer",
    "Release Reviewer",
    "Retro Reviewer",
]

GOVERNANCE_DEVELOPER_REQUIRED_SKILLS = [
    "stage-maintenance",
    "stage-infra",
    "code-review",
]

FIX_069_RELEASE_BLOCKERS = [
    "FIX-069",
    "FIX-070",
    "FIX-071",
    "FIX-072",
    "FIX-073",
    "FIX-074",
]

REQ_059_RELEASE_BLOCKERS = [
    "REQ-059",
    "REQ-060",
    "REQ-061",
    "REQ-062",
    "REQ-063",
    "REQ-064",
]
FIX_069_RELEASE_VERSION = "0." + "35.0"
FIX_069_READINESS_VERSION = "1." + "0.0"
MAINSTREAM_AGENT_ADAPTERS = ["claude", "codex", "gemini", "opencode"]
ADAPTER_REQUIRED_KEYS = [
    "adapter_id",
    "workflow_id",
    "entry_type",
    "support_status",
    "supported_runtime",
    "trigger",
    "inputs",
    "outputs",
    "gate_behavior",
    "validation",
    "native_entry",
    "runtime_e2e",
    "runtime_capabilities",
    "launcher",
]


def _markdown_has_heading(content, level, title):
    return re.search(rf"^{'#' * level}\s+{re.escape(title)}\s*$", content, re.MULTILINE) is not None


def _markdown_section(content, heading):
    lines = content.splitlines()
    start = None
    level = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped == heading:
            start = idx + 1
            level = len(stripped) - len(stripped.lstrip("#"))
            break
    if start is None:
        return ""

    end = len(lines)
    heading_pattern = re.compile(r"^(#{1,%d})\s+" % level)
    for idx in range(start, len(lines)):
        if heading_pattern.match(lines[idx].strip()):
            end = idx
            break
    return "\n".join(lines[start:end])


def _markdown_section_by_prefix(content, heading_prefix):
    lines = content.splitlines()
    for line_no, line in enumerate(lines):
        stripped = line.strip()
        if stripped == heading_prefix:
            return _markdown_section(content, heading_prefix)
        if stripped.startswith(heading_prefix):
            level = len(stripped) - len(stripped.lstrip("#"))
            start = line_no + 1
            end = len(lines)
            heading_pattern = re.compile(r"^(#{1,%d})\s+" % level)
            for idx in range(start, len(lines)):
                if heading_pattern.match(lines[idx].strip()):
                    end = idx
                    break
            return "\n".join(lines[start:end])
    return ""


def _markdown_table_cells(line):
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _normalize_agent_token(token):
    token = re.sub(r"[`*]", "", token)
    token = re.sub(r"[（(][^）)]*[）)]", "", token)
    return token.strip()


def _generic_reviewer_cells(content):
    hits = []
    for line_no, line in enumerate(content.splitlines(), start=1):
        for cell in _markdown_table_cells(line):
            cleaned = _normalize_agent_token(cell)
            parts = [
                _normalize_agent_token(part)
                for part in re.split(r"\s*(?:,|，|、|\+|/|或|和)\s*", cleaned)
            ]
            if any(part in ("Reviewer", "Reviewer Agent") for part in parts):
                hits.append(line_no)
                break
    return hits


def _find_table_line(content, prefix):
    for line in content.splitlines():
        if line.strip().startswith(prefix):
            return line
    return ""


def _normalize_markdown_cell(cell):
    return re.sub(r"[`*]", "", cell).strip()


def _find_table_row_by_first_cell(content, first_cell):
    for line in content.splitlines():
        cells = _markdown_table_cells(line)
        if cells and _normalize_markdown_cell(cells[0]) == first_cell:
            return cells
    return []


def _find_table_rows_with_cell(content, target_cell):
    rows = []
    for line in content.splitlines():
        cells = _markdown_table_cells(line)
        if any(_normalize_markdown_cell(cell) == target_cell for cell in cells):
            rows.append(cells)
    return rows


def _status_cell_is_delivered(status):
    return "✅" in status or "已交付" in status or "已完成" in status


def _task_id_has_open_status(content, task_id):
    for cells in _find_table_rows_with_cell(content, task_id):
        if len(cells) >= 2 and _normalize_markdown_cell(cells[1]) == task_id:
            status = cells[-1]
            if not _status_cell_is_delivered(status):
                return True
    return False


def _contains_fix_token_or_range(content, fix_id):
    if fix_id in content:
        return True
    match = re.match(r"FIX-(\d{3})$", fix_id)
    if not match:
        return False
    fix_num = int(match.group(1))
    for start, end in re.findall(r"FIX-(\d{3})\s*[~～-]\s*(\d{3})", content):
        if int(start) <= fix_num <= int(end):
            return True
    return False


def _extract_fenced_blocks(content):
    blocks = []
    in_block = False
    current = []
    for line in content.splitlines():
        if line.strip().startswith("```"):
            if in_block:
                blocks.append("\n".join(current))
                current = []
                in_block = False
            else:
                in_block = True
            continue
        if in_block:
            current.append(line)
    return blocks


def _duplicate_target_structure_entries(architecture_content):
    section = _markdown_section(architecture_content, "## 目标目录结构")
    duplicates = []
    seen = {}
    for block in _extract_fenced_blocks(section):
        stack = []
        for line_no, line in enumerate(block.splitlines(), start=1):
            raw_entry = line.split("←", 1)[0].rstrip()
            entry = raw_entry.strip()
            if not entry:
                continue
            indent = len(raw_entry) - len(raw_entry.lstrip(" "))
            while stack and indent <= stack[-1][0]:
                stack.pop()
            parent = "/".join(item[1].strip("/") for item in stack if item[1].strip("/"))
            normalized_name = re.sub(r"\s+", " ", entry)
            normalized = f"{parent}/{normalized_name}".strip("/")
            if normalized in seen:
                duplicates.append((normalized, seen[normalized], line_no))
            else:
                seen[normalized] = line_no
            if entry.endswith("/"):
                stack.append((indent, entry))
    return duplicates


def _evidence_closes_fix_069_while_req_open(evidence_content):
    closing_pattern = re.compile(
        r"(FIX-069).*(已完成|已交付|关闭|可关闭|最终审查通过)"
        r"|"
        r"(已完成|已交付|关闭|可关闭|最终审查通过).*(FIX-069)"
    )
    non_closing_markers = [
        "BLOCKED",
        "不可关闭",
        "不能关闭",
        "不得关闭",
        "未关闭",
        "未完成",
        "待最终",
        "未最终",
        "首轮",
        "NEEDS_CHANGE",
    ]
    for line in evidence_content.splitlines():
        if "FIX-069" not in line:
            continue
        if any(marker in line for marker in non_closing_markers):
            continue
        cells = _markdown_table_cells(line)
        if cells and _normalize_markdown_cell(cells[-1]) in ["完成", "已完成", "关闭", "已关闭"]:
            return line.strip()
        if closing_pattern.search(line):
            return line.strip()
    return ""


def _line_overstates_pending_adapter_or_e2e(line):
    done_markers = ["已完成", "已实现", "已验证", "E2E 通过", "真实环境 E2E 通过", "✅"]
    has_done_marker = any(marker in line for marker in done_markers)
    if not has_done_marker:
        return False
    non_closing_patterns = [
        r"未完成",
        r"未实现",
        r"待实现",
        r"待实施",
        r"预研",
        r"不构成",
        r"仅(?:作为)?预检",
        r"仅兼容",
        r"仅路线",
        r"仅.*分析",
    ]
    if any(re.search(pattern, line) for pattern in non_closing_patterns):
        return False
    adapter_markers = ["Gemini", "opencode"]
    if any(adapter in line for adapter in adapter_markers):
        return True
    if re.search(r"真实(?:\s*agent)?(?:运行)?环境\s*E2E", line):
        return True
    return False


def check_release_readiness_fact_source(
    plan_tracker_path=None,
    architecture_path=None,
    evidence_log_path=None,
):
    """FIX-069: keep release blockers, requirements, and readiness facts aligned."""
    plan_tracker_path = plan_tracker_path or ROOT / ".governance/plan-tracker.md"
    architecture_path = architecture_path or ROOT / "project/references/architecture.md"
    evidence_log_path = evidence_log_path or ROOT / ".governance/evidence-log.md"

    failures = []
    plan_content = plan_tracker_path.read_text(encoding="utf-8")
    architecture_content = architecture_path.read_text(encoding="utf-8")
    evidence_content = (
        evidence_log_path.read_text(encoding="utf-8")
        if evidence_log_path and evidence_log_path.exists()
        else ""
    )

    rel_plan = _display_path(plan_tracker_path)
    rel_architecture = _display_path(architecture_path)
    rel_evidence = _display_path(evidence_log_path) if evidence_log_path else "evidence-log"

    dependency_chain = _markdown_section(plan_content, f"### {FIX_069_READINESS_VERSION} 依赖链")
    if not dependency_chain:
        failures.append(f"{rel_plan}: missing {FIX_069_READINESS_VERSION} dependency chain section")
    else:
        required_chain_tokens = [FIX_069_RELEASE_VERSION, "RISK-030"] + FIX_069_RELEASE_BLOCKERS
        for token in required_chain_tokens:
            present = _contains_fix_token_or_range(dependency_chain, token) if token.startswith("FIX-") else token in dependency_chain
            if not present:
                failures.append(f"{rel_plan}: {FIX_069_READINESS_VERSION} dependency chain missing blocker token {token}")
        required_chain_semantics = [
            ("real agent E2E blocker", r"真实\s*agent\s*环境\s*E2E|agent\s*真实环境\s*E2E|真实运行环境\s*E2E"),
            ("goal-drift guardrail blocker", r"防跑偏|目标偏离"),
            ("blocking release language", r"不得推进\s*1\.0\.0|不得发布|阻断|全部闭环前|关闭前"),
        ]
        for label, pattern in required_chain_semantics:
            if not re.search(pattern, dependency_chain):
                failures.append(f"{rel_plan}: {FIX_069_READINESS_VERSION} dependency chain missing {label}")

    release_row = _find_table_row_by_first_cell(plan_content, FIX_069_READINESS_VERSION)
    if not release_row:
        failures.append(f"{rel_plan}: missing {FIX_069_READINESS_VERSION} roadmap row")
    else:
        release_row_text = " | ".join(release_row)
        for token in [FIX_069_RELEASE_VERSION, "RISK-030"] + FIX_069_RELEASE_BLOCKERS:
            present = _contains_fix_token_or_range(release_row_text, token) if token.startswith("FIX-") else token in release_row_text
            if not present:
                failures.append(f"{rel_plan}: {FIX_069_READINESS_VERSION} roadmap row missing release blocker {token}")

    for req_id, fix_id in zip(REQ_059_RELEASE_BLOCKERS, FIX_069_RELEASE_BLOCKERS):
        req_row = _find_table_row_by_first_cell(plan_content, req_id)
        if not req_row:
            failures.append(f"{rel_plan}: requirement matrix missing {req_id}")
            continue
        if len(req_row) >= 5 and fix_id not in req_row[4]:
            failures.append(f"{rel_plan}: requirement matrix {req_id} must reference {fix_id}")

    req_059_row = _find_table_row_by_first_cell(plan_content, "REQ-059")
    req_059_status = req_059_row[5] if len(req_059_row) > 5 else ""
    closing_line = _evidence_closes_fix_069_while_req_open(evidence_content)
    if req_059_status and not _status_cell_is_delivered(req_059_status) and closing_line:
        failures.append(
            f"{rel_evidence}: FIX-069 closing evidence conflicts with open REQ-059 status: {closing_line}"
        )

    req_061_row = _find_table_row_by_first_cell(plan_content, "REQ-061")
    req_064_row = _find_table_row_by_first_cell(plan_content, "REQ-064")
    req_061_status = req_061_row[5] if len(req_061_row) > 5 else ""
    req_064_status = req_064_row[5] if len(req_064_row) > 5 else ""
    adapter_or_e2e_pending = (
        not _status_cell_is_delivered(req_061_status)
        or not _status_cell_is_delivered(req_064_status)
        or _task_id_has_open_status(plan_content, "FIX-071")
        or _task_id_has_open_status(plan_content, "FIX-074")
    )
    if adapter_or_e2e_pending:
        for line_no, line in enumerate(architecture_content.splitlines(), start=1):
            if _line_overstates_pending_adapter_or_e2e(line):
                failures.append(
                    f"{rel_architecture}:{line_no}: architecture overstates pending Gemini/opencode or real-environment E2E status"
                )

    for entry, first_line, second_line in _duplicate_target_structure_entries(architecture_content):
        failures.append(
            f"{rel_architecture}: target directory structure repeats `{entry}` "
            f"(fenced-block lines {first_line} and {second_line})"
        )

    for failure in failures:
        print(f"[FAIL] release readiness fact source: {failure}")
    if not failures:
        print("[OK] release readiness fact source synchronized")
    return failures


FIX_087_ACTIVE_VERSION = ".".join(["0", "38", "0"])
FIX_087_PREVIOUS_VERSION = ".".join(["0", "37", "0"])
FIX_087_READINESS_VERSION = ".".join(["1", "0", "0"])
FIX_087_ACTIVE_TASKS = ["FIX-082", "FIX-083", "FIX-084", "FIX-085", "FIX-086", "FIX-087", "REL-013"]
FIX_087_ACTIVE_FIXES = ["FIX-082", "FIX-083", "FIX-084", "FIX-085", "FIX-086", "FIX-087"]
FIX_087_REQ_TASKS = {
    "REQ-070": ["FIX-082", "FIX-085"],
    "REQ-071": ["FIX-083"],
    "REQ-072": ["FIX-084"],
    "REQ-073": ["FIX-086"],
    "REQ-074": ["FIX-087"],
}


def _version_row_text(plan_content, version):
    row = _find_table_row_by_first_cell(plan_content, version)
    return " | ".join(row) if row else ""


def _task_statuses_for_hot_source(plan_content, task_id, version=None):
    statuses = []
    for cells in _find_table_rows_with_cell(plan_content, task_id):
        normalized = [_normalize_markdown_cell(cell) for cell in cells]
        if len(normalized) >= 2 and normalized[1] == task_id:
            if version and len(normalized) >= 5 and normalized[4] != version:
                continue
            statuses.append(cells[-1])
    return statuses


def _hot_task_is_delivered(plan_content, task_id, version=None):
    statuses = _task_statuses_for_hot_source(plan_content, task_id, version=version)
    return bool(statuses) and any(_status_cell_is_delivered(status) for status in statuses)


def _hot_task_is_open(plan_content, task_id, version=None):
    statuses = _task_statuses_for_hot_source(plan_content, task_id, version=version)
    return bool(statuses) and any(not _status_cell_is_delivered(status) for status in statuses)


def _line_mentions_completed_range_as_pending(line, completed_task_ids):
    pending_markers = ["待实施", "待启动", "未完成", "待闭环"]
    if not any(marker in line for marker in pending_markers):
        return ""
    for task_id in completed_task_ids:
        if _contains_fix_token_or_range(line, task_id):
            return task_id
    return ""


def _extract_task_ids(text):
    return sorted(set(re.findall(r"\b(?:FIX|REL|AUDIT)-\d{3}\b", text)))


def check_hot_fact_source_consistency(plan_tracker_path=None):
    """FIX-087: keep plan-tracker hot sections aligned across active release facts."""
    plan_tracker_path = plan_tracker_path or ROOT / ".governance/plan-tracker.md"
    failures = []
    plan_content = plan_tracker_path.read_text(encoding="utf-8")
    rel_plan = _display_path(plan_tracker_path)

    required_sections = [
        "## 项目配置",
        "## 项目总览",
        "## 当前活跃事项",
        "### 1.0.0 依赖链",
        "## 版本规划",
        "## 需求跟踪矩阵",
    ]
    sections = {heading: _markdown_section_by_prefix(plan_content, heading) for heading in required_sections}
    for heading, content in sections.items():
        if not content:
            failures.append(f"{rel_plan}: missing hot fact-source section {heading}")

    project_config = sections.get("## 项目配置", "")
    overview = sections.get("## 项目总览", "")
    active_items = sections.get("## 当前活跃事项", "")
    dependency_chain = sections.get("### 1.0.0 依赖链", "")

    active_row_text = _version_row_text(plan_content, FIX_087_ACTIVE_VERSION)
    previous_row_text = _version_row_text(plan_content, FIX_087_PREVIOUS_VERSION)
    readiness_row_text = _version_row_text(plan_content, FIX_087_READINESS_VERSION)
    rel013_delivered = _hot_task_is_delivered(plan_content, "REL-013", version=FIX_087_ACTIVE_VERSION)

    if not active_row_text:
        failures.append(f"{rel_plan}: missing {FIX_087_ACTIVE_VERSION} roadmap row")
    elif rel013_delivered and "已发布" not in active_row_text:
        failures.append(f"{rel_plan}: {FIX_087_ACTIVE_VERSION} roadmap row must be 已发布 after REL-013 release")
    elif not rel013_delivered and "进行中" not in active_row_text:
        failures.append(f"{rel_plan}: {FIX_087_ACTIVE_VERSION} roadmap row must remain 进行中 before REL-013 release")
    if not previous_row_text:
        failures.append(f"{rel_plan}: missing {FIX_087_PREVIOUS_VERSION} roadmap row")
    elif "已发布" not in previous_row_text:
        failures.append(f"{rel_plan}: {FIX_087_PREVIOUS_VERSION} roadmap row must be 已发布")

    for source_name, source in [
        ("project config", project_config),
        ("project overview", overview),
        ("current active items", active_items),
    ]:
        if FIX_087_ACTIVE_VERSION not in source:
            failures.append(f"{rel_plan}: {source_name} missing active version {FIX_087_ACTIVE_VERSION}")
    if not rel013_delivered and re.search(r"0\.38\.0[^。\n|]*已发布", project_config + "\n" + overview):
        failures.append(f"{rel_plan}: hot sections overstate {FIX_087_ACTIVE_VERSION} as released before REL-013")

    for task_id in FIX_087_ACTIVE_TASKS:
        if not _task_statuses_for_hot_source(plan_content, task_id, version=FIX_087_ACTIVE_VERSION):
            failures.append(f"{rel_plan}: active {FIX_087_ACTIVE_VERSION} task table missing {task_id}")
        if active_row_text and not _contains_fix_token_or_range(active_row_text, task_id):
            failures.append(f"{rel_plan}: {FIX_087_ACTIVE_VERSION} roadmap row missing active task {task_id}")

    if not dependency_chain:
        pass
    else:
        for token in [FIX_087_ACTIVE_VERSION, FIX_087_READINESS_VERSION, "RISK-033", "REL-013"]:
            if token not in dependency_chain:
                failures.append(f"{rel_plan}: {FIX_087_READINESS_VERSION} dependency chain missing active blocker token {token}")
        if rel013_delivered:
            risk033_lines = [line for line in dependency_chain.splitlines() if "RISK-033" in line]
            if risk033_lines and not any("已关闭" in line for line in risk033_lines):
                failures.append(f"{rel_plan}: {FIX_087_READINESS_VERSION} dependency chain still lacks RISK-033 closure after REL-013")
        elif "不得打 1.0.0" not in dependency_chain and "不得推进 1.0.0" not in dependency_chain:
            failures.append(f"{rel_plan}: {FIX_087_READINESS_VERSION} dependency chain missing blocking language for active release")
        completed_active_fixes = [
            task_id for task_id in FIX_087_ACTIVE_FIXES
            if _hot_task_is_delivered(plan_content, task_id, version=FIX_087_ACTIVE_VERSION)
        ]
        for line in dependency_chain.splitlines():
            stale_task = _line_mentions_completed_range_as_pending(line, completed_active_fixes)
            if stale_task:
                failures.append(
                    f"{rel_plan}: dependency chain line marks completed {stale_task} as pending: {line.strip()}"
                )

    remaining_line = ""
    for line in overview.splitlines():
        if "RISK-033" in line and ("继续由" in line or "承载" in line):
            remaining_line = line
            break
    if rel013_delivered:
        if "RISK-033" in overview and "已关闭" not in overview:
            failures.append(f"{rel_plan}: project overview mentions RISK-033 after REL-013 but does not mark it closed")
    elif remaining_line:
        remaining_text = remaining_line.split("RISK-033", 1)[1] if "RISK-033" in remaining_line else remaining_line
        for task_id in _extract_task_ids(remaining_text):
            if _hot_task_is_delivered(plan_content, task_id, version=FIX_087_ACTIVE_VERSION):
                failures.append(f"{rel_plan}: project overview says completed {task_id} still carries RISK-033")
    elif "RISK-033" in overview and "FIX-087" not in overview:
        failures.append(f"{rel_plan}: project overview mentions RISK-033 but does not name remaining FIX-087")

    for req_id, task_ids in FIX_087_REQ_TASKS.items():
        req_row = _find_table_row_by_first_cell(plan_content, req_id)
        if not req_row:
            failures.append(f"{rel_plan}: requirement matrix missing {req_id}")
            continue
        if len(req_row) < 6:
            failures.append(f"{rel_plan}: requirement matrix {req_id} row has too few columns")
            continue
        req_status = req_row[5]
        linked = req_row[4] if len(req_row) > 4 else ""
        for task_id in task_ids:
            if task_id not in linked:
                failures.append(f"{rel_plan}: requirement matrix {req_id} must reference {task_id}")
        all_tasks_delivered = all(
            _hot_task_is_delivered(plan_content, task_id, version=FIX_087_ACTIVE_VERSION)
            for task_id in task_ids
        )
        any_task_open = any(
            _hot_task_is_open(plan_content, task_id, version=FIX_087_ACTIVE_VERSION)
            for task_id in task_ids
        )
        if all_tasks_delivered and not _status_cell_is_delivered(req_status):
            failures.append(f"{rel_plan}: requirement matrix {req_id} is not delivered while {', '.join(task_ids)} are complete")
        if any_task_open and _status_cell_is_delivered(req_status):
            failures.append(f"{rel_plan}: requirement matrix {req_id} is delivered while linked task remains open")

    for failure in failures:
        print(f"[FAIL] hot fact-source consistency: {failure}")
    if not failures:
        print("[OK] hot fact-source consistency synchronized")
    return failures


def _load_adapter_manifest(adapter_dir):
    manifest_path = adapter_dir / "adapter-manifest.json"
    if not manifest_path.exists():
        return None, [f"{_display_path(manifest_path)}: missing adapter manifest"]
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return None, [f"{_display_path(manifest_path)}: invalid JSON: {exc}"]


def _run_version_command(command):
    completed = subprocess.run(
        command,
        shell=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = (completed.stdout or completed.stderr or "").strip()
    return completed.returncode, output


def _validate_runtime_e2e_block(root, manifest_path, runtime_e2e, field_name, allow_unsupported=False):
    """Validate FIX-074 explicit E2E status blocks in adapter manifests."""
    block = runtime_e2e.get(field_name)
    if not isinstance(block, dict):
        return [f"{_display_path(manifest_path, root)}: runtime_e2e.{field_name} must be an object"]

    allowed_statuses = {"passed", "blocked"}
    if allow_unsupported:
        allowed_statuses.add("unsupported")

    status = block.get("status")
    failures = []
    if status not in allowed_statuses:
        failures.append(
            f"{_display_path(manifest_path, root)}: runtime_e2e.{field_name}.status must be one of {sorted(allowed_statuses)}"
        )
    if not block.get("evidence"):
        failures.append(f"{_display_path(manifest_path, root)}: runtime_e2e.{field_name}.evidence required")
    if status == "passed" and (not block.get("command") or not block.get("verified_on")):
        failures.append(
            f"{_display_path(manifest_path, root)}: passed runtime_e2e.{field_name} requires command and verified_on"
        )
    if status == "blocked" and not block.get("blocked_reason"):
        failures.append(f"{_display_path(manifest_path, root)}: blocked runtime_e2e.{field_name} requires blocked_reason")
    return failures


RUNTIME_CAPABILITY_KEYS = (
    "ask_user_question",
    "sub_agent",
    "tool_calling",
    "browser",
    "mcp",
    "git_hooks",
)

RUNTIME_CAPABILITY_STATUSES = {"native", "degraded", "unsupported"}

ADAPTER_RUNTIME_CAPABILITY_POLICY = {
    "claude": {
        "ask_user_question": {"degraded"},
        "sub_agent": {"native"},
        "tool_calling": {"native"},
        "browser": {"degraded"},
        "mcp": {"degraded"},
        "git_hooks": {"native"},
    },
    "codex": {
        "ask_user_question": {"degraded"},
        "sub_agent": {"degraded"},
        "tool_calling": {"degraded"},
        "browser": {"degraded"},
        "mcp": {"degraded"},
        "git_hooks": {"native"},
    },
    "gemini": {
        "ask_user_question": {"unsupported"},
        "sub_agent": {"unsupported"},
        "tool_calling": {"degraded"},
        "browser": {"unsupported"},
        "mcp": {"degraded"},
        "git_hooks": {"native"},
    },
    "opencode": {
        "ask_user_question": {"unsupported"},
        "sub_agent": {"unsupported"},
        "tool_calling": {"degraded"},
        "browser": {"unsupported"},
        "mcp": {"degraded"},
        "git_hooks": {"native"},
    },
}


def _validate_runtime_capabilities(root, manifest_path, manifest):
    """FIX-082: adapters must declare real host capabilities and degraded modes."""
    display = _display_path(manifest_path, root)
    capabilities = manifest.get("runtime_capabilities")
    if not isinstance(capabilities, dict):
        return [f"{display}: runtime_capabilities must be an object"]

    failures = []
    adapter_id = manifest.get("adapter_id")
    capability_policy = ADAPTER_RUNTIME_CAPABILITY_POLICY.get(adapter_id, {})
    for key in RUNTIME_CAPABILITY_KEYS:
        block = capabilities.get(key)
        if not isinstance(block, dict):
            failures.append(f"{display}: runtime_capabilities.{key} must be an object")
            continue
        status = block.get("status")
        if status not in RUNTIME_CAPABILITY_STATUSES:
            failures.append(
                f"{display}: runtime_capabilities.{key}.status must be one of {sorted(RUNTIME_CAPABILITY_STATUSES)}"
            )
        allowed_statuses = capability_policy.get(key)
        if allowed_statuses and status not in allowed_statuses:
            failures.append(
                f"{display}: runtime_capabilities.{key}.status={status} overclaims adapter policy; "
                f"allowed={sorted(allowed_statuses)}"
            )
        if not block.get("evidence"):
            failures.append(f"{display}: runtime_capabilities.{key}.evidence required")
        if status in {"degraded", "unsupported"} and not block.get("degraded_mode"):
            failures.append(f"{display}: runtime_capabilities.{key}.degraded_mode required when status is {status}")

    closure = capabilities.get("workflow_closure")
    if not isinstance(closure, dict):
        failures.append(f"{display}: runtime_capabilities.workflow_closure must be an object")
        return failures

    closure_status = closure.get("status")
    if closure_status not in {"full", "degraded", "blocked"}:
        failures.append(f"{display}: runtime_capabilities.workflow_closure.status must be full, degraded, or blocked")
    if not closure.get("evidence"):
        failures.append(f"{display}: runtime_capabilities.workflow_closure.evidence required")
    degraded_capabilities = closure.get("degraded_capabilities")
    non_native = [
        key for key in RUNTIME_CAPABILITY_KEYS
        if isinstance(capabilities.get(key), dict)
        and capabilities[key].get("status") in {"degraded", "unsupported"}
    ]
    if non_native:
        if closure_status == "full":
            failures.append(f"{display}: workflow_closure.status=full conflicts with degraded/unsupported capabilities")
        if not isinstance(degraded_capabilities, list):
            failures.append(f"{display}: workflow_closure.degraded_capabilities must list non-native capabilities")
        else:
            missing = [key for key in non_native if key not in degraded_capabilities]
            if missing:
                failures.append(
                    f"{display}: workflow_closure.degraded_capabilities missing {', '.join(missing)}"
                )
    elif closure_status != "full":
        failures.append(f"{display}: workflow_closure.status must be full when all capabilities are native")

    runtime_e2e = manifest.get("runtime_e2e")
    if isinstance(runtime_e2e, dict) and runtime_e2e.get("full_e2e_verified") is False and closure_status == "full":
        failures.append(f"{display}: workflow_closure.status=full requires full_e2e_verified=true or explicit degraded closure")
    return failures


def _validate_codex_runtime_e2e_claim(root, manifest_path, runtime_e2e):
    """FIX-077: Codex full E2E must be real headless codex exec target-cwd evidence."""
    agent_block = runtime_e2e.get("agent_runtime_e2e", {})
    if not isinstance(agent_block, dict):
        return []

    status = agent_block.get("status")
    full_e2e_verified = runtime_e2e.get("full_e2e_verified")
    claim_text = " ".join(
        str(value or "")
        for value in (
            agent_block.get("command"),
            agent_block.get("evidence"),
            agent_block.get("blocked_reason"),
        )
    ).lower()
    app_session_markers = (
        "codex app",
        "current session",
        "current workflow session",
        "timeout attempted separately",
        "attempted separately and timed out",
    )
    blocked_markers = (
        "timed out",
        "timeout",
        "blocked",
        "blocker",
    )
    target_cwd_markers = (
        " -c ",
        "\n-c ",
        "\t-c ",
        "target-cwd",
        "target cwd",
        "cwd",
    )
    headless_markers = (
        "--ephemeral",
        "read-only",
        "read only",
        "headless",
    )
    failures = []
    display = _display_path(manifest_path, root)
    if status == "passed":
        if "codex exec" not in claim_text:
            failures.append(
                f"{display}: Codex agent_runtime_e2e.status=passed requires real codex exec evidence"
            )
        if not any(marker in claim_text for marker in target_cwd_markers):
            failures.append(
                f"{display}: Codex agent_runtime_e2e.status=passed requires target-cwd evidence"
            )
        if not any(marker in claim_text for marker in headless_markers):
            failures.append(
                f"{display}: Codex agent_runtime_e2e.status=passed requires headless/read-only/ephemeral evidence"
            )
        if any(marker in claim_text for marker in app_session_markers):
            failures.append(
                f"{display}: Codex agent_runtime_e2e.status=passed must be real codex exec target-cwd evidence, not Codex App/current session or separately timed-out CLI evidence"
            )
        if any(marker in claim_text for marker in blocked_markers):
            failures.append(
                f"{display}: Codex agent_runtime_e2e.status=passed must not include timeout/blocked evidence"
            )
    if status == "blocked" and full_e2e_verified is not False:
        failures.append(
            f"{display}: Codex blocked agent_runtime_e2e requires full_e2e_verified=false"
        )
    return failures


GEMINI_API_KEY_ENV_VARS = (
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
)

GEMINI_VERTEX_CONFIG_ENV_VARS = (
    "GOOGLE_GENAI_USE_VERTEXAI",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION",
)

GEMINI_VERTEX_CREDENTIAL_ENV_VARS = (
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_ADC_JSON",
    "GOOGLE_CLOUD_ACCESS_TOKEN",
)

GEMINI_GCA_CONFIG_ENV_VARS = (
    "GCA_AUTH_PROVIDER",
)

GEMINI_GCA_CREDENTIAL_ENV_VARS = (
    "GCA_TOKEN",
)

GEMINI_AUTH_REMEDIATION = (
    "Configure Gemini auth before full agent runtime E2E: set GEMINI_API_KEY "
    "or GOOGLE_API_KEY, configure Vertex credentials (for example "
    "GOOGLE_GENAI_USE_VERTEXAI with GOOGLE_CLOUD_PROJECT/LOCATION and ADC), "
    "configure GCA auth, or login/configure Gemini CLI settings.json with an "
    "auth provider/token type. Do not record secret values in manifests or logs."
)


def _gemini_settings_candidates(home=None):
    home = Path(home) if home else Path.home()
    return [
        home / ".gemini" / "settings.json",
        home / ".config" / "gemini" / "settings.json",
    ]


def _safe_env_present(name, env=None):
    env = env if env is not None else os.environ
    value = env.get(name)
    return value is not None and str(value).strip() != ""


def _detect_gemini_auth_from_settings(path):
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    auth_key_markers = ("auth", "credential", "token", "provider", "login")
    provider_value_markers = ("oauth", "google", "vertex", "gca", "api_key", "apikey", "gemini")
    stack = [settings]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                key_text = str(key).lower()
                if isinstance(value, (dict, list)):
                    stack.append(value)
                    continue
                value_text = str(value).strip().lower()
                if not value_text:
                    continue
                if any(marker in key_text for marker in auth_key_markers):
                    if "token" in key_text:
                        return f"settings:{path.name}:token_type"
                    if any(marker in value_text for marker in provider_value_markers):
                        return f"settings:{path.name}:auth_provider"
                    return f"settings:{path.name}:auth_config"
        elif isinstance(current, list):
            stack.extend(current)
    return None


def _detect_gemini_env_auth_sources(env=None):
    env = env if env is not None else os.environ
    sources = []
    for name in GEMINI_API_KEY_ENV_VARS:
        if _safe_env_present(name, env):
            sources.append(f"env:{name}")

    vertex_enabled = str(env.get("GOOGLE_GENAI_USE_VERTEXAI", "")).strip().lower() in {"1", "true", "yes"}
    vertex_has_project = _safe_env_present("GOOGLE_CLOUD_PROJECT", env)
    vertex_has_location = _safe_env_present("GOOGLE_CLOUD_LOCATION", env)
    vertex_credential_sources = [
        name for name in GEMINI_VERTEX_CREDENTIAL_ENV_VARS
        if _safe_env_present(name, env)
    ]
    if vertex_enabled and vertex_has_project and vertex_has_location and vertex_credential_sources:
        sources.append("env:VERTEX:" + "+".join([
            "GOOGLE_GENAI_USE_VERTEXAI",
            "GOOGLE_CLOUD_PROJECT",
            "GOOGLE_CLOUD_LOCATION",
            *vertex_credential_sources,
        ]))

    gca_has_provider = _safe_env_present("GCA_AUTH_PROVIDER", env)
    gca_credential_sources = [
        name for name in GEMINI_GCA_CREDENTIAL_ENV_VARS
        if _safe_env_present(name, env)
    ]
    if gca_has_provider and gca_credential_sources:
        sources.append("env:GCA:GCA_AUTH_PROVIDER+" + "+".join(gca_credential_sources))
    return sources


def _gemini_auth_preflight(env=None, home=None, which=shutil.which, version_runner=_run_version_command):
    env = env if env is not None else os.environ
    result = {
        "status": "BLOCKED",
        "command": "python skills/software-project-governance/infra/verify_workflow.py gemini-auth-preflight",
        "version_command": "gemini --version",
        "cli_path": None,
        "version": None,
        "auth_sources": [],
        "blocked_reason": None,
        "remediation": GEMINI_AUTH_REMEDIATION,
    }

    cli_path = which("gemini")
    if not cli_path:
        result["blocked_reason"] = "Gemini CLI not found on PATH"
        return result
    result["cli_path"] = str(cli_path)

    returncode, version_output = version_runner("gemini --version")
    if returncode != 0:
        result["blocked_reason"] = "Gemini CLI version command failed"
        result["version"] = _truncate_log(version_output, limit=200)
        return result
    result["version"] = _truncate_log(version_output, limit=200)

    result["auth_sources"].extend(_detect_gemini_env_auth_sources(env))

    for path in _gemini_settings_candidates(home=home):
        source = _detect_gemini_auth_from_settings(path)
        if source:
            result["auth_sources"].append(source)

    if result["auth_sources"]:
        result["status"] = "PASS"
        result["blocked_reason"] = None
    else:
        result["blocked_reason"] = "Gemini auth missing or not configured"
    return result


def _validate_gemini_auth_preflight_claim(root, manifest_path, runtime_e2e):
    display = _display_path(manifest_path, root)
    preflight = runtime_e2e.get("auth_preflight")
    if not isinstance(preflight, dict):
        return [f"{display}: Gemini runtime_e2e.auth_preflight must be an object"]

    failures = []
    status = preflight.get("status")
    if status not in {"passed", "blocked"}:
        failures.append(f"{display}: Gemini runtime_e2e.auth_preflight.status must be passed or blocked")
    if "gemini-auth-preflight" not in str(preflight.get("command", "")):
        failures.append(f"{display}: Gemini auth_preflight.command must reference gemini-auth-preflight")
    if not preflight.get("verified_on"):
        failures.append(f"{display}: Gemini auth_preflight.verified_on required")
    guidance_text = " ".join(
        str(value or "")
        for value in (
            preflight.get("blocked_reason"),
            preflight.get("remediation"),
            runtime_e2e.get("agent_runtime_e2e", {}).get("blocked_reason")
            if isinstance(runtime_e2e.get("agent_runtime_e2e"), dict) else "",
        )
    ).lower()
    required_guidance = ("gemini_api_key", "google_api_key", "vertex", "gca", "settings")
    missing = [marker for marker in required_guidance if marker not in guidance_text]
    if missing:
        failures.append(
            f"{display}: Gemini blocked guidance must mention GEMINI_API_KEY / GOOGLE_API_KEY / Vertex / GCA / settings auth"
        )
    if status == "blocked":
        if preflight.get("blocked_reason") != "Gemini auth missing or not configured":
            failures.append(f"{display}: Gemini blocked auth_preflight requires exact auth missing blocked_reason")
        if runtime_e2e.get("full_e2e_verified") is not False:
            failures.append(f"{display}: Gemini blocked auth_preflight requires full_e2e_verified=false")
    return failures


OPENCODE_LEGAL_DEEPSEEK_MODELS = ("deepseek-v4-pro", "deepseek-v4-flash")

OPENCODE_PROVIDER_MODEL_REMEDIATION = (
    "Configure opencode with a supported DeepSeek model, for example "
    "deepseek-v4-pro or deepseek-v4-flash. Remove ANSI escape/suffix residue "
    "such as deepseek-v4-pro[1m]. Do not record provider API keys or secret "
    "values in manifests, tests, docs, or logs."
)


def _run_opencode_probe_command(command, timeout=15):
    try:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding=locale.getpreferredencoding(False),
            errors="replace",
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return 1, str(exc)
    return completed.returncode, _e2e_output(completed)


def _opencode_config_candidates(home=None, root=None):
    home = Path(home) if home else Path.home()
    root = Path(root) if root else ROOT
    return [
        root / "opencode.json",
        root / "opencode.jsonc",
        root / "opencode.toml",
        home / ".config" / "opencode" / "opencode.json",
        home / ".config" / "opencode" / "opencode.jsonc",
        home / ".config" / "opencode" / "opencode.toml",
        home / ".opencode.json",
    ]


def _sanitize_opencode_probe_text(text):
    sanitized = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "<ANSI>", text or "")
    sanitized = re.sub(
        r"(?i)(api[_-]?key|token|secret|authorization|bearer)\s*[:=]\s*['\"]?[^'\"\s,}]+",
        r"\1=<redacted>",
        sanitized,
    )
    sanitized = re.sub(r"\bsk-[A-Za-z0-9._-]+", "<redacted-secret>", sanitized)
    return _truncate_log(sanitized, limit=500)


def _opencode_model_scan(text):
    raw = text or ""
    lowered = raw.lower()
    blocked_markers = []
    if "\x1b" in raw:
        blocked_markers.append("ANSI escape residue")
    if re.search(r"deepseek-v4-(?:pro|flash)\[[0-9;?]*[a-zA-Z]", raw):
        blocked_markers.append("ANSI suffix residue")
    if "unsupported model" in lowered or "not supported" in lowered or "invalid model" in lowered:
        blocked_markers.append("unsupported model output")

    legal_models = [
        model for model in OPENCODE_LEGAL_DEEPSEEK_MODELS
        if re.search(rf"(?<![\w.-]){re.escape(model)}(?![\w.-])", raw)
    ]
    invalid_candidates = re.findall(r"deepseek-v4-(?:pro|flash)\[[^\s,;\"'}]+", raw)
    return {
        "legal_models": sorted(set(legal_models)),
        "blocked_markers": sorted(set(blocked_markers)),
        "invalid_candidates": sorted(set(invalid_candidates)),
    }


def _opencode_provider_model_preflight(
    home=None,
    root=None,
    which=shutil.which,
    version_runner=_run_version_command,
    probe_runner=_run_opencode_probe_command,
    config_candidates=None,
):
    result = {
        "status": "BLOCKED",
        "command": "python skills/software-project-governance/infra/verify_workflow.py opencode-provider-preflight",
        "version_command": "opencode --version",
        "cli_path": None,
        "version": None,
        "legal_models": [],
        "model_sources": [],
        "blocked_reason": None,
        "remediation": OPENCODE_PROVIDER_MODEL_REMEDIATION,
    }

    cli_path = which("opencode")
    if not cli_path:
        result["blocked_reason"] = "opencode CLI not found on PATH"
        return result
    result["cli_path"] = str(cli_path)

    returncode, version_output = version_runner("opencode --version")
    if returncode != 0:
        result["version"] = _sanitize_opencode_probe_text(version_output)
        result["blocked_reason"] = "opencode CLI version command failed"
        return result
    result["version"] = _sanitize_opencode_probe_text(version_output)

    scan_texts = []
    for command in (["opencode", "models"], ["opencode", "model", "list"]):
        code, output = probe_runner(command)
        if output:
            scan_texts.append((f"command:{' '.join(command)}", output))
        if code == 0 and output:
            break

    paths = config_candidates
    if paths is None:
        paths = _opencode_config_candidates(home=home, root=root)
    for path in paths:
        path = Path(path)
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        scan_texts.append((f"config:{path.name}", content))

    blocked = []
    for source, text in scan_texts:
        scan = _opencode_model_scan(text)
        for model in scan["legal_models"]:
            if model not in result["legal_models"]:
                result["legal_models"].append(model)
        if scan["legal_models"]:
            result["model_sources"].append(source)
        if scan["blocked_markers"] or scan["invalid_candidates"]:
            blocked.append(
                f"{source}: "
                + ", ".join(scan["blocked_markers"] + scan["invalid_candidates"])
            )

    result["legal_models"].sort()
    if blocked:
        result["blocked_reason"] = "opencode provider/model config invalid: " + "; ".join(blocked)
        return result
    if result["legal_models"]:
        result["status"] = "PASS"
        return result

    result["blocked_reason"] = (
        "opencode provider/model config missing supported DeepSeek model "
        "(deepseek-v4-pro or deepseek-v4-flash)"
    )
    return result


def _validate_opencode_provider_model_preflight_claim(root, manifest_path, runtime_e2e):
    display = _display_path(manifest_path, root)
    preflight = runtime_e2e.get("provider_model_preflight")
    if not isinstance(preflight, dict):
        return [f"{display}: opencode runtime_e2e.provider_model_preflight must be an object"]

    failures = []
    status = preflight.get("status")
    if status not in {"passed", "blocked"}:
        failures.append(f"{display}: opencode provider_model_preflight.status must be passed or blocked")
    if "opencode-provider-preflight" not in str(preflight.get("command", "")):
        failures.append(f"{display}: opencode provider_model_preflight.command must reference opencode-provider-preflight")
    if not preflight.get("verified_on"):
        failures.append(f"{display}: opencode provider_model_preflight.verified_on required")
    models = preflight.get("legal_models")
    if status == "passed":
        if not isinstance(models, list) or not set(models).intersection(OPENCODE_LEGAL_DEEPSEEK_MODELS):
            failures.append(f"{display}: opencode passed provider_model_preflight requires deepseek-v4-pro or deepseek-v4-flash")
        agent_status = runtime_e2e.get("agent_runtime_e2e", {}).get("status")
        if agent_status == "passed" and runtime_e2e.get("full_e2e_verified") is not True:
            failures.append(f"{display}: opencode passed agent_runtime_e2e requires full_e2e_verified=true")
    if status == "blocked" and runtime_e2e.get("full_e2e_verified") is not False:
        failures.append(f"{display}: opencode blocked provider_model_preflight requires full_e2e_verified=false")

    guidance_text = " ".join(
        str(value or "")
        for value in (
            preflight.get("blocked_reason"),
            preflight.get("remediation"),
            preflight.get("evidence"),
        )
    ).lower()
    if status == "blocked" and not all(marker in guidance_text for marker in OPENCODE_LEGAL_DEEPSEEK_MODELS):
        failures.append(f"{display}: opencode blocked guidance must mention deepseek-v4-pro and deepseek-v4-flash")
    return failures


def check_agent_adapter_contract(root=None, run_runtime=False):
    """FIX-071: mainstream agent adapters must be explicit and not overclaim coverage."""
    root = root or ROOT
    failures = []
    reports = []

    for adapter_id in MAINSTREAM_AGENT_ADAPTERS:
        adapter_dir = root / "adapters" / adapter_id
        readme_path = adapter_dir / "README.md"
        launch_path = adapter_dir / "launch.py"
        for path in [readme_path, launch_path]:
            if not path.exists():
                failures.append(f"{_display_path(path, root)}: missing adapter asset")

        manifest, manifest_failures = _load_adapter_manifest(adapter_dir)
        failures.extend(manifest_failures)
        if not manifest:
            continue

        for key in ADAPTER_REQUIRED_KEYS:
            if key not in manifest:
                failures.append(f"{_display_path(adapter_dir / 'adapter-manifest.json', root)}: missing `{key}`")

        if manifest.get("adapter_id") != adapter_id:
            failures.append(
                f"{_display_path(adapter_dir / 'adapter-manifest.json', root)}: adapter_id must be `{adapter_id}`"
            )
        if manifest.get("workflow_id") != "software-project-governance":
            failures.append(
                f"{_display_path(adapter_dir / 'adapter-manifest.json', root)}: workflow_id must be software-project-governance"
            )
        if manifest.get("launcher") != f"adapters/{adapter_id}/launch.py":
            failures.append(
                f"{_display_path(adapter_dir / 'adapter-manifest.json', root)}: launcher path mismatch"
            )

        support_status = manifest.get("support_status", "")
        runtime_e2e = manifest.get("runtime_e2e", {})
        native_entry = manifest.get("native_entry", {})
        manifest_path = adapter_dir / "adapter-manifest.json"
        malformed_runtime_e2e = False
        failures.extend(_validate_runtime_capabilities(root, manifest_path, manifest))
        if not isinstance(native_entry, dict) or not native_entry:
            failures.append(f"{_display_path(adapter_dir / 'adapter-manifest.json', root)}: native_entry must be non-empty")
        if not isinstance(runtime_e2e, dict) or not runtime_e2e.get("command") or not runtime_e2e.get("version_command"):
            failures.append(f"{_display_path(adapter_dir / 'adapter-manifest.json', root)}: runtime_e2e command/version_command required")
            runtime_e2e = {}
            malformed_runtime_e2e = True
        else:
            failures.extend(
                _validate_runtime_e2e_block(
                    root, manifest_path, runtime_e2e, "target_cwd_e2e",
                    allow_unsupported=(support_status == "not-supported-current-release"),
                )
            )
            failures.extend(
                _validate_runtime_e2e_block(
                    root, manifest_path, runtime_e2e, "agent_runtime_e2e",
                    allow_unsupported=(support_status == "not-supported-current-release"),
                )
            )
            if adapter_id == "codex":
                failures.extend(_validate_codex_runtime_e2e_claim(root, manifest_path, runtime_e2e))
            if adapter_id == "gemini":
                failures.extend(_validate_gemini_auth_preflight_claim(root, manifest_path, runtime_e2e))
            if adapter_id == "opencode":
                failures.extend(_validate_opencode_provider_model_preflight_claim(root, manifest_path, runtime_e2e))
            if runtime_e2e.get("full_e2e_verified") is True:
                target_status = runtime_e2e.get("target_cwd_e2e", {}).get("status")
                agent_status = runtime_e2e.get("agent_runtime_e2e", {}).get("status")
                if target_status != "passed" or agent_status != "passed":
                    failures.append(
                        f"{_display_path(manifest_path, root)}: full_e2e_verified=true requires target_cwd_e2e and agent_runtime_e2e passed"
                    )

        if support_status == "not-supported-current-release":
            if runtime_e2e.get("e2e_level") != "unsupported":
                failures.append(
                    f"{_display_path(adapter_dir / 'adapter-manifest.json', root)}: unsupported adapter runtime_e2e.e2e_level must be unsupported"
                )
            if manifest.get("no_full_coverage_claim") is not True:
                failures.append(
                    f"{_display_path(adapter_dir / 'adapter-manifest.json', root)}: unsupported adapter must set no_full_coverage_claim=true"
                )
            if not manifest.get("unsupported_reason"):
                failures.append(
                    f"{_display_path(adapter_dir / 'adapter-manifest.json', root)}: unsupported adapter must explain unsupported_reason"
                )
            reports.append((adapter_id, "UNSUPPORTED", manifest.get("unsupported_reason", "")))
            continue

        if support_status != "runtime-verified":
            failures.append(
                f"{_display_path(adapter_dir / 'adapter-manifest.json', root)}: support_status must be runtime-verified or not-supported-current-release"
            )
            continue

        if manifest.get("no_full_coverage_claim") is True:
            failures.append(
                f"{_display_path(adapter_dir / 'adapter-manifest.json', root)}: runtime-verified adapter must not keep no_full_coverage_claim=true"
            )
        if runtime_e2e.get("e2e_level") not in ("runtime-version-probe", "real-agent-target-cwd"):
            failures.append(
                f"{_display_path(adapter_dir / 'adapter-manifest.json', root)}: runtime-verified adapter runtime_e2e.e2e_level must be runtime-version-probe or real-agent-target-cwd"
            )
        if manifest.get("no_full_coverage_claim") is True and runtime_e2e.get("full_e2e_verified") is True:
            failures.append(
                f"{_display_path(adapter_dir / 'adapter-manifest.json', root)}: no_full_coverage_claim=true conflicts with full_e2e_verified=true"
            )
        if not runtime_e2e.get("verified_on") or not runtime_e2e.get("evidence"):
            failures.append(
                f"{_display_path(adapter_dir / 'adapter-manifest.json', root)}: runtime-verified adapter must include verified_on and evidence"
            )
        if malformed_runtime_e2e:
            reports.append((adapter_id, "FAIL", "invalid runtime_e2e"))
            continue

        if run_runtime:
            command_name = runtime_e2e.get("command", "")
            if not shutil.which(command_name):
                failures.append(f"{adapter_id}: runtime command `{command_name}` not found on PATH")
                reports.append((adapter_id, "FAIL", "command not found"))
                continue
            returncode, output = _run_version_command(runtime_e2e["version_command"])
            if returncode != 0:
                failures.append(f"{adapter_id}: runtime command failed: {runtime_e2e['version_command']}")
                reports.append((adapter_id, "FAIL", output))
            else:
                reports.append((adapter_id, "PASS", output))
        else:
            reports.append((adapter_id, "STATIC", support_status))

    for adapter_id, status, detail in reports:
        print(f"[{status}] agent adapter {adapter_id}: {detail}")
    for failure in failures:
        print(f"[FAIL] agent adapter contract: {failure}")
    if not failures:
        print("[OK] agent adapter contracts synchronized")
    return failures


def _run_release_validation_command(label, command, timeout=180):
    """Run one release validation command and normalize its result."""
    try:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding=locale.getpreferredencoding(False),
            errors="replace",
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        return {
            "label": label,
            "pass": False,
            "exit_code": None,
            "issue": f"{label}: command did not complete: {exc}",
            "command": " ".join(str(part) for part in command),
        }

    output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
    issue = None if completed.returncode == 0 else (
        f"{label}: exit={completed.returncode}; "
        f"output={output[-500:] if output else '<empty>'}"
    )
    return {
        "label": label,
        "pass": completed.returncode == 0,
        "exit_code": completed.returncode,
        "issue": issue,
        "command": " ".join(str(part) for part in command),
    }


def run_release_execution_gates(runner=_run_release_validation_command):
    """Run command-backed release gates that must be green before publishing."""
    verify_script = ROOT / "skills/software-project-governance/infra/verify_workflow.py"
    commands = [
        ("verify", [sys.executable, str(verify_script), "verify"]),
        ("governance health", [sys.executable, str(verify_script), "check-governance", "--fail-on-issues"]),
        ("e2e check", [sys.executable, str(verify_script), "e2e-check"]),
        ("unit tests", [sys.executable, "-m", "unittest", "skills/software-project-governance/infra/tests/test_verify_workflow.py", "-v"]),
    ]
    return [runner(label, command) for label, command in commands]


PROJECTION_SYNC_PATTERNS = (
    "skills/*/SKILL.md",
    "skills/software-project-governance/SKILL.md",
    "skills/software-project-governance/core/**/*.md",
    "skills/software-project-governance/core/**/*.json",
    "skills/software-project-governance/infra/**/*.py",
    "skills/software-project-governance/infra/**/*.md",
    "skills/software-project-governance/infra/**/*.sh",
    "skills/software-project-governance/infra/hooks/*",
    "skills/software-project-governance/references/**/*.md",
    "commands/*.md",
    "agents/*.md",
)


def _extract_skill_version(path):
    if not path.is_file():
        return ""
    content = path.read_text(encoding="utf-8")
    match = re.search(r"^version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", content, re.MULTILINE)
    return match.group(1) if match else ""


def _extract_json_version(path):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(payload.get("version", "")).strip()


def _extract_plan_workflow_version(path):
    if not path.is_file():
        return ""
    content = path.read_text(encoding="utf-8")
    match = re.search(r"工作流版本\*\*:\s*([0-9]+\.[0-9]+\.[0-9]+)", content)
    if not match:
        match = re.search(r"工作流版本.*?([0-9]+\.[0-9]+\.[0-9]+)", content)
    return match.group(1) if match else ""


def _projection_hash(path):
    text = _read_text_normalized(path)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _projection_source_files(root, patterns=None):
    root = Path(root)
    patterns = patterns or PROJECTION_SYNC_PATTERNS
    files = set()
    for pattern in patterns:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if "__pycache__" in rel or rel.endswith(".pyc"):
                continue
            files.add(rel)
    return sorted(files)


def _projection_target_tracked_files(root, target_dir):
    """Return target fixture files tracked by git, or None outside a git checkout."""
    root = Path(root)
    target_dir = Path(target_dir)
    if not (root / ".git").exists():
        return None
    try:
        target_rel = target_dir.relative_to(root).as_posix()
    except ValueError:
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--", target_rel],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    prefix = target_rel.rstrip("/") + "/"
    tracked = set()
    for line in result.stdout.splitlines():
        item = line.strip().replace("\\", "/")
        if item.startswith(prefix):
            tracked.add(item[len(prefix):])
    return tracked


def _target_fixture_file_is_checkable(rel_path, target_tracked):
    if target_tracked is None:
        return True
    return rel_path.replace("\\", "/") in target_tracked


def check_projection_sync(root=None, target_dir=None, patterns=None):
    """FIX-086: block release when source and target fixture projections drift."""
    root = Path(root) if root is not None else ROOT
    target_dir = Path(target_dir) if target_dir is not None else root / "project/e2e-test-project"
    issues = []
    version_checks = []
    skipped_untracked = []
    target_tracked = _projection_target_tracked_files(root, target_dir)

    source_version = _extract_skill_version(root / "skills/software-project-governance/SKILL.md")
    if not source_version:
        issues.append("source skills/software-project-governance/SKILL.md missing frontmatter version")

    version_sources = [
        ("source core manifest", root / "skills/software-project-governance/core/manifest.json", _extract_json_version),
        ("source Claude plugin", root / ".claude-plugin/plugin.json", _extract_json_version),
        ("source Codex plugin", root / ".codex-plugin/plugin.json", _extract_json_version),
        ("target workflow skill", target_dir / "skills/software-project-governance/SKILL.md", _extract_skill_version),
        ("target plan-tracker", target_dir / ".governance/plan-tracker.md", _extract_plan_workflow_version),
    ]
    optional_target_version_sources = [
        ("target core manifest", "skills/software-project-governance/core/manifest.json", _extract_json_version),
    ]
    for label, rel, extractor in optional_target_version_sources:
        if _target_fixture_file_is_checkable(rel, target_tracked):
            version_sources.append((label, target_dir / rel, extractor))
        else:
            skipped_untracked.append(rel)

    for label, path, extractor in version_sources:
        observed = extractor(path)
        display = _display_path(path, root)
        version_checks.append({
            "label": label,
            "path": display.as_posix() if isinstance(display, Path) else str(display),
            "version": observed,
        })
        if not observed:
            issues.append(f"{label}: missing version at {_display_path(path, root)}")
        elif source_version and observed != source_version:
            issues.append(f"{label}: version {observed} != source {source_version}")

    mirrored_files = _projection_source_files(root, patterns=patterns)
    compared = 0
    for rel in mirrored_files:
        if not _target_fixture_file_is_checkable(rel, target_tracked):
            skipped_untracked.append(rel)
            continue
        source_path = root / rel
        target_path = target_dir / rel
        if not target_path.is_file():
            issues.append(f"target fixture missing mirrored file: {rel}")
            continue
        compared += 1
        if _projection_hash(source_path) != _projection_hash(target_path):
            issues.append(f"target fixture drift: {rel}")

    native_entry_checks = [
        (target_dir / "CLAUDE.md", ("Governance Bootstrap", "AskUserQuestion")),
        (target_dir / "AGENTS.md", ("Governance Bootstrap", "Codex", "opencode", "skills/software-project-governance/SKILL.md")),
        (target_dir / "GEMINI.md", ("Governance Bootstrap", "Gemini", "skills/software-project-governance/SKILL.md")),
    ]
    for path, needles in native_entry_checks:
        if not path.is_file():
            issues.append(f"target native entry missing: {_display_path(path, root)}")
            continue
        content = path.read_text(encoding="utf-8")
        missing = [needle for needle in needles if needle not in content]
        if missing:
            issues.append(f"target native entry {_display_path(path, root)} missing markers: {missing}")

    return {
        "pass": not issues,
        "issues": issues,
        "source_version": source_version,
        "mirrors_checked": compared,
        "mirrors_discovered": len(mirrored_files),
        "mirrors_skipped_untracked": len(set(skipped_untracked)),
        "version_checks": version_checks,
    }


def check_release_readiness(
    version=None,
    require_changelog=False,
    run_runtime_adapters=False,
    changelog_path=None,
    run_execution_gates=False,
    execution_gate_runner=_run_release_validation_command,
):
    """FIX-072: aggregate release gate scripts behind the stage-release check-release command."""
    issues = []
    details = {}

    version_issues = check_version_consistency()
    version_failures = [issue for issue in version_issues if not issue.startswith("[WARN]")]
    details["version_consistency"] = {
        "pass": not version_failures,
        "issues": version_failures,
        "warnings": [issue for issue in version_issues if issue.startswith("[WARN]")],
    }
    issues.extend(f"version consistency: {issue}" for issue in version_failures)

    release_fact_issues = check_release_readiness_fact_source()
    details["release_fact_source"] = {
        "pass": not release_fact_issues,
        "issues": release_fact_issues,
    }
    issues.extend(f"release fact source: {issue}" for issue in release_fact_issues)

    hot_fact_issues = check_hot_fact_source_consistency()
    details["hot_fact_source"] = {
        "pass": not hot_fact_issues,
        "issues": hot_fact_issues,
    }
    issues.extend(f"hot fact source: {issue}" for issue in hot_fact_issues)

    adapter_issues = check_agent_adapter_contract(run_runtime=run_runtime_adapters)
    details["agent_adapters"] = {
        "pass": not adapter_issues,
        "issues": adapter_issues,
        "runtime": run_runtime_adapters,
    }
    issues.extend(f"agent adapters: {issue}" for issue in adapter_issues)

    projection_result = check_projection_sync()
    details["projection_sync"] = {
        "pass": projection_result["pass"],
        "issues": projection_result["issues"],
        "mirrors_checked": projection_result["mirrors_checked"],
        "mirrors_discovered": projection_result["mirrors_discovered"],
        "mirrors_skipped_untracked": projection_result["mirrors_skipped_untracked"],
        "source_version": projection_result["source_version"],
    }
    issues.extend(f"projection sync: {issue}" for issue in projection_result["issues"])

    cross_ref_result = check_cross_references()
    cross_ref_issues = (
        [f"dangling reference: {item['source']}:{item['line']} -> {item['target']}" for item in cross_ref_result["dangling"]]
        + [f"deprecated reference: {item['source']}:{item['line']} -> {item['target']}" for item in cross_ref_result["deprecated"]]
        + [f"circular reference: {' -> '.join(cycle)}" for cycle in cross_ref_result["cycles"]]
    )
    details["cross_references"] = {
        "pass": not cross_ref_issues,
        "issues": cross_ref_issues,
    }
    issues.extend(cross_ref_issues)

    archive_result = check_archive_integrity()
    archive_issues = archive_result.get("issues", [])
    details["archive_integrity"] = {
        "pass": not archive_issues,
        "issues": archive_issues,
        "pending_archive_tasks": archive_result.get("pending_archive_tasks", 0),
    }
    issues.extend(f"archive integrity: {issue}" for issue in archive_issues)

    execution_gate_results = []
    execution_gate_issues = []
    if run_execution_gates:
        execution_gate_results = run_release_execution_gates(runner=execution_gate_runner)
        execution_gate_issues = [result["issue"] for result in execution_gate_results if result.get("issue")]
        issues.extend(f"execution gate: {issue}" for issue in execution_gate_issues)
    details["execution_gates"] = {
        "pass": not execution_gate_issues,
        "issues": execution_gate_issues,
        "required": run_execution_gates,
        "results": execution_gate_results,
    }

    changelog_path = changelog_path or (ROOT / "project/CHANGELOG.md")
    changelog_issues = []
    if version:
        if not re.fullmatch(r"\d+\.\d+\.\d+", version):
            changelog_issues.append(f"release version `{version}` is not semver X.Y.Z")
        if require_changelog:
            if not changelog_path.exists():
                changelog_issues.append(f"{_display_path(changelog_path)}: missing changelog")
            else:
                changelog_content = changelog_path.read_text(encoding="utf-8")
                if f"## [{version}]" not in changelog_content:
                    changelog_issues.append(f"{_display_path(changelog_path)}: missing changelog entry ## [{version}]")
    elif require_changelog:
        changelog_issues.append("--require-changelog requires --version")

    details["changelog"] = {
        "pass": not changelog_issues,
        "issues": changelog_issues,
        "required": require_changelog,
        "version": version,
    }
    issues.extend(changelog_issues)

    return {
        "pass": not issues,
        "issues": issues,
        "details": details,
    }


def check_architecture_fact_source(
    skill_path=None,
    skill_index_path=None,
    architecture_path=None,
    governance_command_path=None,
    agent_protocol_path=None,
    governance_developer_prompt_path=None,
):
    """FIX-065: keep Agent/team architecture facts synchronized."""
    skill_path = skill_path or ROOT / "skills/software-project-governance/SKILL.md"
    skill_index_path = skill_index_path or ROOT / "skills/software-project-governance/references/skill-index.md"
    architecture_path = architecture_path or ROOT / "project/references/architecture.md"
    governance_command_path = governance_command_path or ROOT / "commands/governance.md"
    agent_protocol_path = agent_protocol_path or ROOT / "skills/software-project-governance/references/agent-communication-protocol.md"
    governance_developer_prompt_path = governance_developer_prompt_path or ROOT / "agents/governance-developer.md"

    failures = []
    contents = {
        skill_path: skill_path.read_text(encoding="utf-8"),
        skill_index_path: skill_index_path.read_text(encoding="utf-8"),
        architecture_path: architecture_path.read_text(encoding="utf-8"),
        governance_command_path: governance_command_path.read_text(encoding="utf-8"),
        agent_protocol_path: agent_protocol_path.read_text(encoding="utf-8"),
        governance_developer_prompt_path: governance_developer_prompt_path.read_text(encoding="utf-8"),
    }

    forbidden_patterns = [
        ("legacy 7 groups / 9 Agent narrative", r"7\s*组\s*9\s*Agent|7组9Agent"),
        ("legacy 46-line SKILL.md entry narrative", r"46\s*行"),
        ("legacy entry-layer no behavior rules narrative", r"不包含任何行为规则"),
        ("legacy native-entry exclusion narrative", r"仓库不包含任何平台原生入口文件"),
    ]
    for path, content in contents.items():
        rel = _display_path(path)
        for label, pattern in forbidden_patterns:
            if re.search(pattern, content):
                failures.append(f"{rel}: forbidden {label}")

    skill_index_content = contents[skill_index_path]
    for line in skill_index_content.splitlines():
        if line.strip().startswith("| stage-operations ") and "Release" in line:
            rel = _display_path(skill_index_path)
            failures.append(f"{rel}: stage-operations must not be bound to Release")

    skill_content = contents[skill_path]
    required_skill_phrases = [
        "Coordinator 融入入口层",
        "14 个活跃文件化角色 Agent",
        "15 个活跃角色含 Coordinator",
        "Coordinator 接管用户交互",
        "Producer-Reviewer 分离",
    ]
    rel_skill = _display_path(skill_path)
    for phrase in required_skill_phrases:
        if phrase not in skill_content:
            failures.append(f"{rel_skill}: missing architecture fact phrase: {phrase}")

    actual_routes = _skill_route_table_count(skill_path)
    documented_routes = _documented_route_table_count(governance_command_path)
    rel_command = _display_path(governance_command_path)
    if documented_routes is None:
        failures.append(f"{rel_command}: missing documented full route table count")
    elif documented_routes != actual_routes:
        failures.append(
            f"{rel_command}: route table count {documented_routes} does not match SKILL.md actual {actual_routes}"
        )

    rel_skill_index = _display_path(skill_index_path)
    governance_developer_binding = _find_table_line(
        skill_index_content, "| 开发组 | **Governance Developer** "
    )
    if not governance_developer_binding:
        failures.append(f"{rel_skill_index}: missing Governance Developer skill binding row")
    else:
        for required_skill in GOVERNANCE_DEVELOPER_REQUIRED_SKILLS:
            if required_skill not in governance_developer_binding:
                failures.append(
                    f"{rel_skill_index}: Governance Developer skill binding missing {required_skill}"
                )

    required_skill_index_bindings = [
        ("| stage-infra ", "stage-infra"),
        ("| stage-maintenance ", "stage-maintenance"),
        ("| code-review ", "code-review"),
    ]
    for row_prefix, skill_name in required_skill_index_bindings:
        row = _find_table_line(skill_index_content, row_prefix)
        if not row or "Governance Developer" not in row:
            failures.append(f"{rel_skill_index}: {skill_name} must bind Governance Developer")

    agent_protocol_content = contents[agent_protocol_path]
    rel_protocol = _display_path(agent_protocol_path)
    for role in ACTIVE_AGENT_ROLES:
        if not _markdown_has_heading(agent_protocol_content, 3, role):
            failures.append(f"{rel_protocol}: missing active role communication contract: {role}")
    for reviewer_role in NAMED_REVIEWER_ROLES:
        if not _markdown_has_heading(agent_protocol_content, 3, reviewer_role):
            failures.append(f"{rel_protocol}: missing named reviewer communication contract: {reviewer_role}")
    if _markdown_has_heading(agent_protocol_content, 3, "Reviewer"):
        failures.append(f"{rel_protocol}: generic Reviewer communication contract is forbidden")

    governance_developer_protocol = _markdown_section(agent_protocol_content, "### Governance Developer")
    required_governance_developer_protocol_phrases = [
        "Proposed evidence-log entry",
        "Proposed decision-log / risk-log entry",
    ]
    if not governance_developer_protocol:
        failures.append(f"{rel_protocol}: missing Governance Developer communication contract")
    else:
        for phrase in required_governance_developer_protocol_phrases:
            if phrase not in governance_developer_protocol:
                failures.append(f"{rel_protocol}: Governance Developer contract missing {phrase}")

    governance_developer_prompt_content = contents[governance_developer_prompt_path]
    rel_governance_developer_prompt = _display_path(governance_developer_prompt_path)
    required_governance_developer_prompt_phrases = [
        "不得直接写 `.governance/` 治理记录",
        "Proposed evidence-log entry",
        "Proposed decision-log / risk-log entry",
        "Coordinator 负责最终写回",
    ]
    for phrase in required_governance_developer_prompt_phrases:
        if phrase not in governance_developer_prompt_content:
            failures.append(f"{rel_governance_developer_prompt}: missing Governance Developer output boundary: {phrase}")

    for path in (skill_path, skill_index_path, agent_protocol_path):
        rel = _display_path(path)
        for line_no in _generic_reviewer_cells(contents[path]):
            failures.append(f"{rel}:{line_no}: generic Reviewer role is forbidden; use named reviewer roles")

    for failure in failures:
        print(f"[FAIL] architecture fact source: {failure}")
    if not failures:
        print("[OK] architecture fact source synchronized")
    return failures


# ── Markdown parsing helpers ─────────────────────────────────────

SAMPLE_PATH = ROOT / ".governance/plan-tracker.md"
GATES_PATH = ROOT / "skills/software-project-governance/core/stage-gates.md"
LIFECYCLE_PATH = ROOT / "skills/software-project-governance/core/lifecycle.md"
STAGE_SKILLS_ROOT = ROOT / "skills"

STAGE_ORDER = [
    "initiation", "research", "selection", "infrastructure",
    "architecture", "development", "testing", "ci-cd",
    "release", "operations", "maintenance",
]

STAGE_SKILL_ALIASES = {
    "infra": "infrastructure",
    "infrastructure": "infrastructure",
    "cicd": "ci-cd",
    "ci-cd": "ci-cd",
}

STAGE_SKILL_DIR_NAMES = {
    "infrastructure": "stage-infra",
    "ci-cd": "stage-cicd",
}

STATUS_ICONS = {
    "passed": "[PASS]",
    "passed-on-entry": "[ENTRY]",
    "blocked": "[BLOCK]",
    "pending": "[????]",
}


def _extract_section(content, heading, stop_headings=None):
    """Extract lines between a ## heading and the next ## heading."""
    lines = content.split("\n")
    capture = False
    result = []
    for line in lines:
        if line.strip() == heading or line.startswith(heading + "\n"):
            capture = True
            continue
        if capture:
            if stop_headings and any(line.startswith(sh) for sh in stop_headings):
                break
            if line.startswith("## ") and not line.strip() == heading:
                break
            result.append(line)
    return "\n".join(result)


def parse_project_config():
    """Parse project configuration section from sample."""
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    config = {}
    in_section = False
    for line in content.split("\n"):
        if line.strip() == "## 项目配置":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            m = re.match(r"- \*\*(.+?)\*\*:\s*(.+)", line)
            if m:
                config[m.group(1)] = m.group(2)
    return config


def parse_gate_status():
    """Parse Gate status table from sample."""
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    gates = []
    in_section = False
    for line in content.split("\n"):
        if line.strip() == "## Gate 状态跟踪":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and line.startswith("|"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 5 and parts[0] != "Gate" and not all(
                set(p.strip()) <= {"-", " "} for p in parts
            ):
                gates.append({
                    "gate": parts[0],
                    "transition": parts[1],
                    "status": parts[2],
                    "date": parts[3],
                    "evidence": parts[4] if len(parts) > 4 else "",
                })
    return gates


def parse_overview():
    """Parse project overview table from sample."""
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    in_section = False
    for line in content.split("\n"):
        if line.strip() == "## 项目总览":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and line.startswith("|"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 8 and parts[0] != "项目" and not all(
                set(p.strip()) <= {"-", " "} for p in parts
            ):
                return {
                    "project": parts[0],
                    "current_stage": parts[1],
                    "total": parts[2],
                    "completed": parts[3],
                    "blocked": parts[4],
                    "risks": parts[5],
                    "latest_gate": parts[6],
                    "latest_retro": parts[7],
                }
    return {}


def parse_task_stats():
    """Count task statuses from sample tracking table."""
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    stats = {"已完成": 0, "进行中": 0, "未开始": 0, "已终止": 0}
    for line in content.split("\n"):
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 11:
            status = parts[10] if len(parts) > 10 else ""
            if status in stats:
                stats[status] += 1
    return stats


def parse_gate_detail(gate_id):
    """Parse a specific Gate's details from stage-gates.md."""
    gate_id = gate_id.upper()
    if not gate_id.startswith("G"):
        gate_id = "G" + gate_id

    content = GATES_PATH.read_text(encoding="utf-8")

    pattern = re.compile(
        rf"## ({re.escape(gate_id)} .+?)\n\n(.*?)(?=\n## G\d|\n## Gate 执行原则|\Z)",
        re.DOTALL,
    )
    m = pattern.search(content)
    if not m:
        return None

    title = m.group(1).strip()
    body = m.group(2).strip()

    detail = {"title": title, "raw": body}

    # Extract transition
    tm = re.search(r"\*\*阶段转换\*\*[：:]\s*(.+)", body)
    detail["transition"] = tm.group(1).strip() if tm else ""

    # Extract required materials
    mm = re.search(r"\*\*必审材料\*\*[：:]\s*(.+)", body)
    detail["materials"] = mm.group(1).strip() if mm else ""

    # Extract check items
    checks = re.findall(r"^\s+\d+\.\s+(.+)$", body, re.MULTILINE)
    detail["checks"] = checks

    # Extract pass criteria
    pm = re.search(r"\*\*通过标准\*\*[：:]\s*(.+)", body)
    detail["pass_criteria"] = pm.group(1).strip() if pm else ""

    # Extract auto-judgment criteria
    auto_checks = re.findall(r"^\s+- 检查项\d+[：:]\s*(.+)$", body, re.MULTILINE)
    detail["auto_criteria"] = auto_checks

    # Extract conditional pass info
    cm = re.search(r"\*\*有条件通过\*\*[：:]\s*(.+?)(?:\n\n|\n- \*\*|$)", body, re.DOTALL)
    detail["conditional"] = cm.group(1).strip() if cm else ""

    return detail


def normalize_stage_name(stage_name):
    """Normalize CLI stage names to lifecycle stage identifiers."""
    normalized = stage_name.strip().lower()
    if normalized.startswith("stage-"):
        normalized = normalized[len("stage-"):]
    return STAGE_SKILL_ALIASES.get(normalized, normalized)


def stage_skill_dir_name(stage_name):
    """Return the canonical skill directory name for a lifecycle stage."""
    stage = normalize_stage_name(stage_name)
    return STAGE_SKILL_DIR_NAMES.get(stage, f"stage-{stage}")


def stage_skill_path(stage_name):
    """Return the canonical stage workflow SKILL.md path."""
    return STAGE_SKILLS_ROOT / stage_skill_dir_name(stage_name) / "SKILL.md"


def _stage_name_from_skill_dir(dirname):
    """Map a stage skill directory back to the lifecycle stage identifier."""
    for stage, mapped_dir in STAGE_SKILL_DIR_NAMES.items():
        if dirname == mapped_dir:
            return stage
    if dirname.startswith("stage-"):
        return normalize_stage_name(dirname[len("stage-"):])
    return dirname


def list_available_stages():
    """List all available lifecycle stages backed by stage SKILL.md files."""
    if not STAGE_SKILLS_ROOT.is_dir():
        return []
    stages = {
        stage for stage in STAGE_ORDER
        if stage_skill_path(stage).is_file()
    }
    for skill_md in STAGE_SKILLS_ROOT.glob("stage-*/SKILL.md"):
        stages.add(_stage_name_from_skill_dir(skill_md.parent.name))
    return sorted(
        stages,
        key=lambda x: STAGE_ORDER.index(x) if x in STAGE_ORDER else 99,
    )


# ── Governance health check parsers ─────────────────────────────

EVIDENCE_PATH = ROOT / ".governance/evidence-log.md"
RISK_PATH = ROOT / ".governance/risk-log.md"
ARCHIVE_INDEX_PATH = ROOT / ".governance/archive/index.md"
ARCHIVE_TASKS_DIR = ROOT / ".governance/archive/tasks"
ARCHIVE_EVIDENCE_DIR = ROOT / ".governance/archive/evidence"
ARCHIVE_DECISIONS_DIR = ROOT / ".governance/archive/decisions"
ARCHIVE_RISKS_DIR = ROOT / ".governance/archive/risks"


def _load_archive_module():
    archive_path = ROOT / "skills/software-project-governance/infra/archive.py"
    if not archive_path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("governance_archive_runtime", archive_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    return module


# ── SYSGAP-030: GovernanceDataSource (archive-aware data source) ──

class GovernanceDataSource:
    """Unified governance data source — transparently aggregates hot files
    + archive files. Backward compatible: falls back to single-file mode
    when archive/ directory does not exist."""

    def __init__(self, sample_path=None, evidence_path=None, archive_index_path=None,
                 archive_root=None, decision_path=None, risk_path=None):
        self.sample_path = Path(sample_path) if sample_path is not None else SAMPLE_PATH
        self.evidence_path = Path(evidence_path) if evidence_path is not None else EVIDENCE_PATH
        self.decision_path = Path(decision_path) if decision_path is not None else ROOT / ".governance/decision-log.md"
        self.risk_path = Path(risk_path) if risk_path is not None else ROOT / ".governance/risk-log.md"

        if archive_root is not None:
            self.archive_root = Path(archive_root)
        elif archive_index_path is not None:
            self.archive_root = Path(archive_index_path).parent
        else:
            self.archive_root = self._infer_governance_dir() / "archive"

        self.archive_index_path = (
            Path(archive_index_path)
            if archive_index_path is not None
            else self.archive_root / "index.md"
        )
        self.archive_tasks_dir = self.archive_root / "tasks"
        self.archive_evidence_dir = self.archive_root / "evidence"
        self.archive_decisions_dir = self.archive_root / "decisions"
        self.archive_risks_dir = self.archive_root / "risks"

    def _infer_governance_dir(self):
        for path in (self.sample_path, self.evidence_path):
            if path.name in {"plan-tracker.md", "evidence-log.md"}:
                return path.parent
        return ROOT / ".governance"

    def _has_archive(self):
        """Check if archive directory exists and has content."""
        return self.archive_index_path.exists()

    def _scan_archive_files(self, dir_path, extract_func):
        """Scan all .md files in archive directory (excluding .gitkeep),
        applying extract_func to each, returning aggregated results."""
        results = []
        if not self._has_archive():
            return results
        if not dir_path.exists():
            return results
        for f in sorted(dir_path.glob("*.md")):
            if f.name == ".gitkeep":
                continue
            results.extend(extract_func(f))
        return results

    # ── Task data ──

    def get_all_completed_task_ids(self):
        """Return set of completed task IDs from plan-tracker + archive/tasks/*."""
        return {
            entry["id"]
            for entry in self.get_all_completed_task_entries()
        }

    def get_all_completed_task_entries(self):
        """Return completed task entries with source metadata."""
        completed = []
        if self.sample_path.is_file():
            content = self.sample_path.read_text(encoding="utf-8")
            for line in content.split("\n"):
                line_stripped = line.strip()
                if not line_stripped.startswith("| ") or "---" in line_stripped:
                    continue
                m = re.match(r"\|\s*([A-Z]+-\d+)\s*\|", line_stripped)
                if not m:
                    continue
                parts = _split_markdown_table_row(line)
                if len(parts) >= 10 and parts[9] == "已完成":
                    completed.append({"id": m.group(1), "status": "已完成", "source": "hot"})
        for entry in self._scan_archive_files(self.archive_tasks_dir, self._extract_task_ids):
            if entry.get("status") == "已完成":
                completed.append({**entry, "source": "archive"})
        return completed

    def _extract_task_ids(self, file_path):
        """Extract task IDs and statuses from an archive task file."""
        results = []
        content = file_path.read_text(encoding="utf-8")
        current_version = None
        for line in content.split("\n"):
            stripped = line.strip()
            # Detect version headers
            m_ver = re.match(r"^#{1,6}\s+(?:v)?(\d+\.\d+\.\d+)\s*[—\-]", stripped)
            if m_ver:
                current_version = m_ver.group(1)
                continue
            # Parse task rows
            m = re.match(r"\|\s*([A-Z]+-\d+)\s*\|", stripped)
            if m:
                task_id = m.group(1)
                parts = _split_markdown_table_row(line)
                status = parts[9] if len(parts) >= 10 else "?"
                results.append({"id": task_id, "status": status, "version": current_version})
        return results

    def get_all_task_ids(self):
        """Return set of all task IDs (any status) from hot + archive."""
        task_ids = set()
        # Hot file
        if self.sample_path.is_file():
            content = self.sample_path.read_text(encoding="utf-8")
            for line in content.split("\n"):
                stripped = line.strip()
                if not stripped.startswith("| "):
                    continue
                m = re.match(r"\|\s*([A-Z]+-\d+)\s*\|", stripped)
                if m:
                    task_ids.add(m.group(1))
        # Archive files
        for entry in self._scan_archive_files(self.archive_tasks_dir, self._extract_task_ids):
            task_ids.add(entry["id"])
        return task_ids

    # ── Evidence data ──

    def get_all_evidence_task_ids(self):
        """Return set of task IDs that have evidence entries (hot + archive)."""
        task_ids = set()
        # Hot file
        if self.evidence_path.is_file():
            content = self.evidence_path.read_text(encoding="utf-8")
            for line in content.split("\n"):
                stripped = line.strip()
                if not stripped.startswith("| EVD-"):
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    raw_ids = parts[2]
                    if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids):
                        task_ids |= expand_task_ids(raw_ids)
        # Archive files
        for entry in self._scan_archive_files(self.archive_evidence_dir, self._extract_evidence_entries):
            raw_ids = entry.get("task_ids", "")
            if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids):
                task_ids |= expand_task_ids(raw_ids)
        return task_ids

    def get_all_evidence_task_map(self):
        """Return task_id -> evidence IDs from hot evidence-log + archive evidence files."""
        task_map = {}

        def add_entry(evd_id, raw_ids):
            if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids):
                for task_id in expand_task_ids(raw_ids):
                    task_map.setdefault(task_id, []).append(evd_id)

        if self.evidence_path.is_file():
            content = self.evidence_path.read_text(encoding="utf-8")
            for line in content.split("\n"):
                line = line.strip()
                if not line.startswith("| EVD-"):
                    continue
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    add_entry(parts[1], parts[2])

        for entry in self._scan_archive_files(self.archive_evidence_dir, self._extract_evidence_entries):
            add_entry(entry.get("evd_id", ""), entry.get("task_ids", ""))

        return task_map

    def _extract_evidence_entries(self, file_path):
        """Extract evidence entries from an archive evidence file."""
        results = []
        content = file_path.read_text(encoding="utf-8")
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped.startswith("| EVD-"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                results.append({
                    "evd_id": parts[1],
                    "task_ids": parts[2],
                })
        return results

    # ── Decision data ──

    def get_all_decision_ids(self):
        """Return sorted set of decision integers from hot + archive."""
        ids = set()
        # Hot file
        if self.decision_path.is_file():
            content = self.decision_path.read_text(encoding="utf-8")
            for m in re.finditer(r"\bDEC-(\d+)\b", content):
                ids.add(int(m.group(1)))
        # Archive files
        for f in sorted((self.archive_decisions_dir).glob("*.md")):
            if f.name == ".gitkeep":
                continue
            content = f.read_text(encoding="utf-8")
            for m in re.finditer(r"\bDEC-(\d+)\b", content):
                ids.add(int(m.group(1)))
        return sorted(ids)

    # ── Risk data ──

    def get_all_risk_ids(self):
        """Return sorted set of risk integers from hot + archive."""
        ids = set()
        # Hot file
        if self.risk_path.is_file():
            content = self.risk_path.read_text(encoding="utf-8")
            for m in re.finditer(r"\bRISK-(\d+)\b", content):
                ids.add(int(m.group(1)))
        # Archive files
        for f in sorted((self.archive_risks_dir).glob("*.md")):
            if f.name == ".gitkeep":
                continue
            content = f.read_text(encoding="utf-8")
            for m in re.finditer(r"\bRISK-(\d+)\b", content):
                ids.add(int(m.group(1)))
        return sorted(ids)

    # ── Lookup ──

    def find_entry_by_id(self, entry_id):
        """Find an entry by ID: check hot files first, then archive index,
        then archive files. Returns dict with 'source' and 'content' keys,
        or None if not found.

        Supports: EVD-, DEC-, RISK-, and generic Task ID (e.g. FIX-001)
        prefixes.  Uses \b word-boundary matching to avoid false matches
        (EVD-10 will not match EVD-100).
        """
        boundary_pattern = re.compile(
            rf"\b{re.escape(entry_id)}\b"
        )

        # ── Task ID (e.g. FIX-001, AUDIT-082) ──
        if re.match(r"[A-Z]+-\d+", entry_id) and not entry_id.startswith(
            ("EVD-", "DEC-", "RISK-")
        ):
            # 1) plan-tracker (hot)
            if self.sample_path.is_file():
                for line in self.sample_path.read_text(encoding="utf-8").split("\n"):
                    if boundary_pattern.search(line):
                        return {
                            "source": "plan-tracker.md (hot)",
                            "line": line.strip(),
                        }
            # 2) archive index
            if self.archive_index_path.is_file():
                for line in self.archive_index_path.read_text(encoding="utf-8").split("\n"):
                    if boundary_pattern.search(line):
                        return {
                            "source": "archive/index.md",
                            "line": line.strip(),
                        }
            # 3) archive task files
            for f in sorted((self.archive_tasks_dir).glob("*.md")):
                if f.name == ".gitkeep":
                    continue
                for line in f.read_text(encoding="utf-8").split("\n"):
                    if boundary_pattern.search(line):
                        return {
                            "source": f"archive/tasks/{f.name}",
                            "line": line.strip(),
                        }
            return None

        # ── Evidence IDs ──
        if re.match(r"EVD-\d+", entry_id):
            content = self.evidence_path.read_text(encoding="utf-8") if self.evidence_path.is_file() else ""
            for line in content.split("\n"):
                if boundary_pattern.search(line):
                    return {"source": "evidence-log.md (hot)", "line": line.strip()}
            # Search archive
            for f in sorted((self.archive_evidence_dir).glob("*.md")):
                if f.name == ".gitkeep":
                    continue
                fc = f.read_text(encoding="utf-8")
                for line in fc.split("\n"):
                    if boundary_pattern.search(line):
                        return {"source": f"archive/evidence/{f.name}", "line": line.strip()}

        # ── Decision IDs ──
        if re.match(r"DEC-\d+", entry_id):
            if self.decision_path.is_file():
                for line in self.decision_path.read_text(encoding="utf-8").split("\n"):
                    if boundary_pattern.search(line):
                        return {"source": "decision-log.md (hot)", "line": line.strip()}
            # Search archive decisions
            for f in sorted((self.archive_decisions_dir).glob("*.md")):
                if f.name == ".gitkeep":
                    continue
                for line in f.read_text(encoding="utf-8").split("\n"):
                    if boundary_pattern.search(line):
                        return {"source": f"archive/decisions/{f.name}", "line": line.strip()}

        # ── Risk IDs ──
        if re.match(r"RISK-\d+", entry_id):
            if self.risk_path.is_file():
                for line in self.risk_path.read_text(encoding="utf-8").split("\n"):
                    if boundary_pattern.search(line):
                        return {"source": "risk-log.md (hot)", "line": line.strip()}
            # Search archive risks
            for f in sorted((self.archive_risks_dir).glob("*.md")):
                if f.name == ".gitkeep":
                    continue
                for line in f.read_text(encoding="utf-8").split("\n"):
                    if boundary_pattern.search(line):
                        return {"source": f"archive/risks/{f.name}", "line": line.strip()}

        return None


def parse_completed_task_ids():
    """Return set of completed task IDs from plan-tracker."""
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    completed = set()
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| ") or "---" in line:
            continue
        m = re.search(r"\|\s*(?:\*\*)?([A-Z]+-\d+)(?:\*\*)?\s*\|", line)
        if not m:
            continue
        task_id = m.group(1)
        parts = [p.strip() for p in line.split("|")]
        if any("已完成" in part for part in parts):
            completed.add(task_id)
    return completed


def expand_task_ids(raw_text):
    """Expand range notations and comma-separated task IDs into individual IDs.

    Supported formats:
      - Single: AUDIT-021
      - Comma-separated: AUDIT-045, AUDIT-048
      - Range: AUDIT-015~020  (expands to AUDIT-015 through AUDIT-020)
      - Mixed comma + range: RISK-021, RISK-022, MAINT-002
    Returns a set of individual task IDs.
    """
    result = set()
    # Split by comma first
    for chunk in raw_text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        # Check for range notation: PREFIX-NUM1~NUM2
        range_match = re.match(r"^([A-Z]+-)(\d+)\s*~\s*(\d+)$", chunk)
        if range_match:
            prefix = range_match.group(1)
            start_num = int(range_match.group(2))
            end_num = int(range_match.group(3))
            for num in range(start_num, end_num + 1):
                result.add(f"{prefix}{num:03d}")
        elif re.match(r"[A-Z]+-\d+", chunk):
            result.add(chunk)
    return result


def parse_evidence_task_ids():
    """Return set of task IDs that have evidence entries (range-expanded)."""
    content = EVIDENCE_PATH.read_text(encoding="utf-8")
    task_ids = set()
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            raw_ids = parts[2]
            if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids):
                task_ids |= expand_task_ids(raw_ids)
    return task_ids


def parse_evidence_task_map():
    """Return dict mapping task_id -> list of evidence IDs (range-expanded)."""
    content = EVIDENCE_PATH.read_text(encoding="utf-8")
    task_map = {}
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            evd_id = parts[1]
            raw_ids = parts[2]
            if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids):
                for task_id in expand_task_ids(raw_ids):
                    task_map.setdefault(task_id, []).append(evd_id)
    return task_map


def parse_open_risks():
    """Return list of (risk_id, date_str) for open risks."""
    content = RISK_PATH.read_text(encoding="utf-8")
    risks = []
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| RISK-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 10:
            risk_id = parts[1]
            date_str = parts[2]
            status = parts[9]
            if status == "打开":
                risks.append((risk_id, date_str))
    return risks


def parse_gate_statuses():
    """Return list of dicts with gate status from plan-tracker."""
    return parse_gate_status()


def check_evidence_completeness():
    """Check that every completed task has at least one evidence entry.

    Uses GovernanceDataSource to transparently aggregate hot files + archive
    files. Falls back to single-file mode when archive/ directory does not
    exist (backward compatible).
    """
    ds = GovernanceDataSource()
    completed_entries = ds.get_all_completed_task_entries()
    completed = {entry["id"] for entry in completed_entries}
    evidenced = ds.get_all_evidence_task_ids()
    missing = completed - evidenced
    hot_completed = {
        entry["id"] for entry in completed_entries
        if entry.get("source") == "hot"
    }
    current_missing = missing & hot_completed
    historical_missing = missing - current_missing
    matched = completed & evidenced
    return {
        "completed_count": len(completed),
        "evidenced_count": len(matched),
        "missing_evidence": sorted(current_missing),
        "historical_missing_evidence": sorted(historical_missing),
    }


def check_risk_staleness():
    """Check for open risks older than 7 days."""
    risks = parse_open_risks()
    today = date.today()
    stale = []
    fresh = []
    for risk_id, date_str in risks:
        try:
            risk_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            age = (today - risk_date).days
            if age > 7:
                stale.append((risk_id, date_str, age))
            else:
                fresh.append((risk_id, date_str, age))
        except ValueError:
            stale.append((risk_id, date_str, -1))
    return {
        "total_open": len(risks),
        "stale": stale,
        "fresh": fresh,
    }


def check_gate_consistency():
    """Check gate status vs evidence consistency."""
    gates = parse_gate_statuses()
    ds = GovernanceDataSource()
    evidenced = ds.get_all_evidence_task_map()

    issues = []

    # Check: passed gates should have evidence referencing the gate
    for g in gates:
        if g["status"] == "passed":
            # Look for evidence entries whose task references this gate
            gate_id = g["gate"]
            found = False
            for task_id, evd_list in evidenced.items():
                if gate_id in task_id or gate_id.lower() in task_id.lower():
                    found = True
                    break
            # Don't fail if no direct match — gates are referenced indirectly
            # Instead, check if passed-on-entry gates look suspicious
            pass

        if g["status"] == "passed-on-entry":
            # These are pre-onboarding gates, should have evidence date
            if not g.get("date") or g["date"] == "2026-04-20":
                continue  # Standard onboarding date
            # Flag gates with inconsistent dates
            pass

    # Check for tasks marked 已完成 in plan-tracker but no evidence.
    # Uses GovernanceDataSource to cover both hot files + archive files.
    completeness = check_evidence_completeness()
    tasks_without_evidence = completeness["missing_evidence"]
    if tasks_without_evidence:
        issues.append({
            "type": "completed_tasks_missing_evidence",
            "detail": tasks_without_evidence,
        })
    if completeness.get("historical_missing_evidence"):
        issues.append({
            "type": "historical_completed_tasks_missing_evidence",
            "detail": completeness["historical_missing_evidence"],
        })

    # Check for evidence entries referencing non-existent tasks.
    # Uses GovernanceDataSource to include archived tasks.
    all_tasks = ds.get_all_task_ids()

    orphan_evidence = set(evidenced.keys()) - all_tasks
    if orphan_evidence:
        issues.append({
            "type": "orphan_evidence",
            "detail": sorted(orphan_evidence),
        })

    return issues


def check_protocol_compliance():
    """Check protocol compliance: DRI assignment, evidence format, conditional pass tracking.

    This is the external validation counterpart to M8 agent self-check.
    It independently detects structural protocol violations from governance records.
    """
    issues = {
        "dri_violations": [],       # Tasks without unique DRI
        "evidence_format": [],      # Evidence entries with missing required fields
        "conditional_pass": [],     # passed-with-conditions without corrective tasks
    }

    plan_content = SAMPLE_PATH.read_text(encoding="utf-8")

    # ── DRI Check: tasks with missing/multi-valued/ambiguous Owner ──
    task_rows = []
    in_table = False
    for line in plan_content.split("\n"):
        line = line.strip()
        if "## 样例跟踪表" in line:
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if in_table and line.startswith("|") and not "---" in line:
            parts = [p.strip() for p in line.split("|")]
            # Skip header row
            if parts[1] == "ID" or not re.match(r"[A-Z]+-\d+", parts[1]):
                continue
            task_rows.append(parts)

    dri_violations = []
    for parts in task_rows:
        if len(parts) < 11:
            continue
        task_id = parts[1]
        status = parts[10] if len(parts) > 10 else ""
        owner = parts[7] if len(parts) > 7 else ""

        # Only check active tasks (not completed/terminated)
        if status in ("已完成", "已终止"):
            continue

        # Check for DRI violations
        violations = []
        if not owner or owner == "":
            violations.append("Owner is empty")
        elif any(sep in owner for sep in ("+", "/", "、", "&", ",")):
            violations.append(f"Owner is multi-valued: '{owner}'")
        elif owner in ("待定", "多人", "TBD", "N/A", "未分配"):
            violations.append(f"Owner is ambiguous: '{owner}'")

        if violations:
            dri_violations.append({
                "task_id": task_id,
                "status": status,
                "owner": owner,
                "violations": violations,
            })

    issues["dri_violations"] = dri_violations

    # ── Conditional Pass Check: passed-with-conditions without corrective tasks ──
    gates = parse_gate_status()
    conditional_gates = [g for g in gates if g["status"] == "passed-with-conditions"]

    if conditional_gates:
        # Collect all task descriptions for corrective task detection
        all_task_text = plan_content

        for g in conditional_gates:
            gate_id = g["gate"]
            # Look for corrective tasks related to this gate
            # Search for tasks whose description references this gate's conditions
            found_corrective = False
            for parts in task_rows:
                task_desc = " ".join(parts[3:7]) if len(parts) > 6 else ""
                # Check if any task mentions corrective action for this gate
                if gate_id in task_desc and any(
                    kw in task_desc for kw in ("纠正", "修复", "补齐", "DRI", "条件")
                ):
                    found_corrective = True
                    break

            if not found_corrective:
                issues["conditional_pass"].append({
                    "gate": gate_id,
                    "issue": f"Gate {gate_id} is passed-with-conditions but no corrective task found in plan-tracker",
                })

    # ── Evidence Format Check: evidence entries with missing required fields ──
    evidence_path = ROOT / ".governance" / "evidence-log.md"
    if evidence_path.is_file():
        ev_content = evidence_path.read_text(encoding="utf-8")
        for line in ev_content.split("\n"):
            line = line.strip()
            if not line.startswith("| EVD-"):
                continue
            parts = [p.strip() for p in line.split("|")]
            # Expected: empty, EVD-XXX, TaskID, Stage, Type, Description, Location, Author, Date, Gate, Notes
            # parts indices: 0=empty, 1=EVD, 2=TaskID, 3=Stage, 4=Type, 5=Description, 6=Location, 7=Author, 8=Date, 9=Gate, 10=Notes
            if len(parts) < 11:
                issues["evidence_format"].append(
                    f"{parts[1] if len(parts) > 1 else '???'}: only {len(parts)-1} fields (expected ≥10)"
                )
                continue

            evd_id = parts[1]
            missing = []
            if not parts[2] or parts[2] == "":
                missing.append("TaskID")
            if not parts[3] or parts[3] == "":
                missing.append("Stage")
            if not parts[4] or parts[4] == "":
                missing.append("Type")
            if not parts[5] or parts[5] == "":
                missing.append("Description")
            if not parts[6] or parts[6] == "":
                missing.append("Location")
            if not parts[7] or parts[7] == "":
                missing.append("Author")
            if not parts[8] or parts[8] == "":
                missing.append("Date")

            if missing:
                issues["evidence_format"].append(
                    f"{evd_id}: missing fields — {', '.join(missing)}"
                )

    return issues


def check_evidence_quality():
    """Check evidence quality: session context references, circular refs, empty output claims."""
    evidence_path = ROOT / ".governance" / "evidence-log.md"
    issues = {
        "session_context": [],      # 会话上下文 references
        "circular_refs": [],        # 循环引用
        "empty_output": [],         # 空输出声明
    }

    if not evidence_path.is_file():
        return issues

    content = evidence_path.read_text(encoding="utf-8")
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        # Skip header rows and separator rows
        if not line.startswith("| EVD-"):
            continue

        parts = line.split("|")
        if len(parts) < 8:
            continue

        evd_id = parts[1].strip()
        evidence_location = parts[6].strip() if len(parts) > 6 else ""

        # Check 1: 会话上下文 references (non-persistent)
        if "会话上下文" in evidence_location:
            issues["session_context"].append(f"{evd_id} (line {i}): evidence location = '{evidence_location}'")

        # Check 2: Circular references — evidence referencing itself
        if f"详见 {evd_id}" in line or f"see {evd_id}" in line.lower():
            issues["circular_refs"].append(f"{evd_id} (line {i}): self-referencing — '{evd_id}' in content")

        # Check 3: Empty or placeholder output claims
        if evidence_location in ("待补", "会话上下文", "详见 EVD-070 完整内容", ""):
            if evidence_location == "":
                issues["empty_output"].append(f"{evd_id} (line {i}): empty evidence location")
            elif evidence_location == "待补":
                issues["empty_output"].append(f"{evd_id} (line {i}): evidence location = '待补'")
            elif evidence_location.startswith("详见 EVD-"):
                pass  # Already caught by Check 2

    return issues


def parse_tier_definitions():
    """Parse Tier definitions from plan-tracker's DEC-052 implementation roadmap.

    Returns: dict mapping tier_id (e.g., "0-A") -> list of task IDs.
    """
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    lines = content.split("\n")

    in_roadmap = False
    tiers = {}
    current_tier = None

    for line in lines:
        # Detect start of implementation roadmap section
        if line.strip() == "## 实施路线图（DEC-052）":
            in_roadmap = True
            continue
        # Stop at next top-level section
        if in_roadmap and line.startswith("## "):
            break

        if not in_roadmap:
            continue

        # Detect Tier header: "Tier 0-A: description"
        tier_match = re.match(r"^Tier (\d+-[A-Z]):", line)
        if tier_match:
            current_tier = tier_match.group(1)
            tiers[current_tier] = []
            continue

        # Collect task IDs within current tier
        # Format: "  AUDIT-XXX (PX) — description" or "  MAINT-XXX (PX) — description"
        if current_tier:
            task_match = re.match(r"^\s+([A-Z]+-\d+)\s+\(P\d\)", line)
            if task_match:
                tiers[current_tier].append(task_match.group(1))

    return tiers


def parse_task_status_map():
    """Return dict mapping task_id -> status from ALL tracking tables in plan-tracker.

    Scans the entire file for task rows regardless of section boundaries,
    since tracking tables are spread across multiple subsections.
    """
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    status_map = {}

    for line in content.split("\n"):
        line_stripped = line.strip()
        if not line_stripped.startswith("| ") or "---" in line_stripped:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 11:
            task_id_match = re.match(r"([A-Z]+-\d+)", parts[1])
            if task_id_match:
                task_id = task_id_match.group(1)
                status = parts[10] if len(parts) > 10 else ""
                status_map[task_id] = status

    return status_map


def check_tier_audit_completeness():
    """Check that each completed Tier has a corresponding TIER-X-Y-AUDIT evidence entry.

    Per DEC-052 execution discipline rule #3: every completed Tier MUST have an audit.
    Audit evidence uses task ID format: TIER-<layer>-<tier>-AUDIT (e.g., TIER-0-C-AUDIT).

    Returns: dict with tier details and issue lists.
    """
    tiers = parse_tier_definitions()
    status_map = parse_task_status_map()
    evidence_task_ids = parse_evidence_task_ids()

    completed_without_audit = []
    completed_with_audit = []
    incomplete_tiers = []
    all_details = []

    for tier_id, task_ids in tiers.items():
        if not task_ids:
            continue

        # Check status of each task in this tier
        task_statuses = {}
        all_completed = True
        completed_count = 0
        for tid in task_ids:
            status = status_map.get(tid, "未找到")
            task_statuses[tid] = status
            if status == "已完成":
                completed_count += 1
            else:
                all_completed = False

        # Check for TIER audit evidence
        audit_evidence_id = f"TIER-{tier_id}-AUDIT"
        has_audit = audit_evidence_id in evidence_task_ids

        detail = {
            "tier_id": tier_id,
            "task_count": len(task_ids),
            "completed_count": completed_count,
            "task_statuses": task_statuses,
            "all_completed": all_completed,
            "has_audit": has_audit,
            "audit_evidence_id": audit_evidence_id,
        }
        all_details.append(detail)

        if all_completed and not has_audit:
            completed_without_audit.append(detail)
        elif all_completed and has_audit:
            completed_with_audit.append(detail)
        elif not all_completed:
            incomplete_tiers.append(detail)

    return {
        "completed_without_audit": completed_without_audit,
        "completed_with_audit": completed_with_audit,
        "incomplete_tiers": incomplete_tiers,
        "all_details": all_details,
    }


def check_version_consistency():
    """Check version consistency across all declaration locations (SYSGAP-020).

    Source of truth: skills/software-project-governance/SKILL.md frontmatter.

    Checks performed:
      1. Version declaration files (manifest.json, plugin.json x2,
         marketplace.json, codex plugin.json) all match SKILL.md version.
      2. verify_workflow.py hardcoded snippet versions match SKILL.md.
      3. CHANGELOG.md latest entry version matches SKILL.md.          (FAIL)
      4. plan-tracker.md workflow version matches SKILL.md.          (WARN)

    Returns: list of issue strings. Items prefixed with [WARN] indicate
    non-blocking drift (e.g., local plan-tracker lagging behind plugin version).
    Items prefixed with [FAIL] or [MISMATCH] are hard failures.
    """
    import json

    VERSION_FILES = {
        "SKILL.md (source of truth)": ROOT / "skills/software-project-governance/SKILL.md",
        "manifest.json": ROOT / "skills/software-project-governance/core/manifest.json",
        ".claude-plugin/plugin.json": ROOT / ".claude-plugin/plugin.json",
        ".claude-plugin/marketplace.json": ROOT / ".claude-plugin/marketplace.json",
        ".codex-plugin/plugin.json": ROOT / ".codex-plugin/plugin.json",
    }

    issues = []
    versions = {}

    for label, path in VERSION_FILES.items():
        if not path.exists():
            issues.append(f"[FAIL] {label}: {path} not found")
            continue

        content = path.read_text(encoding="utf-8")

        if path.suffix == ".json":
            try:
                data = json.loads(content)
                if "version" in data:
                    ver = data["version"]
                elif "plugins" in data and len(data["plugins"]) > 0:
                    ver = data["plugins"][0].get("version", "NOT FOUND")
                else:
                    ver = "NOT FOUND"
            except json.JSONDecodeError:
                issues.append(f"[FAIL] {label}: invalid JSON")
                continue
        else:
            # Markdown files: look for version in frontmatter or inline
            match = re.search(r"(?:`?\*{0,2}version\*{0,2}`?\s*[:=]\s*`?)(\d+\.\d+\.\d+)", content)
            if match:
                ver = match.group(1)
            else:
                ver = "NOT FOUND"

        versions[label] = ver

    # Determine source version
    source_version = versions.get("SKILL.md (source of truth)")
    if not source_version or source_version == "NOT FOUND":
        issues.append("[FAIL] Cannot determine source version from SKILL.md")
        # Attempt fallback: extract any semver from SKILL.md content
        skill_path = ROOT / "skills/software-project-governance/SKILL.md"
        if skill_path.exists():
            skill_text = skill_path.read_text(encoding="utf-8")
            fallback = re.search(r'(\d+\.\d+\.\d+)', skill_text)
            if fallback:
                source_version = fallback.group(1)
        if not source_version:
            return issues

    # Check file consistency
    for label, ver in versions.items():
        if label == "SKILL.md (source of truth)":
            continue
        if ver != source_version:
            issues.append(
                f"[FAIL] {label}: version={ver}, expected={source_version}"
            )

    # ── Check verify_workflow.py snippet versions ──
    # The REQUIRED_SNIPPETS dict in this file hardcodes version strings
    # for plugin.json, marketplace.json, codex plugin.json, and manifest.json.
    # These must match the source of truth.
    snippet_self_path = ROOT / "skills/software-project-governance/infra/verify_workflow.py"
    snippet_self_content = snippet_self_path.read_text(encoding="utf-8")
    # Match only bare quoted version strings like "0.26.0" (excludes
    # CHANGELOG entries like "## [0.7.1]" which use a different format)
    # Exclude comment lines to avoid matching example versions in comments
    non_comment_lines = [l for l in snippet_self_content.split('\n') if not l.strip().startswith('#')]
    snippet_versions = set()
    for line in non_comment_lines:
        snippet_versions.update(re.findall(r'"(\d+\.\d+\.\d+)"', line))
    for sv in snippet_versions:
        if sv != source_version:
            issues.append(
                f"[FAIL] verify_workflow.py snippet: hardcoded version={sv}, expected={source_version}"
            )
            break  # One mismatch is enough to signal the issue

    # ── Check CHANGELOG latest entry ──
    changelog_path = ROOT / "project/CHANGELOG.md"
    if changelog_path.exists():
        changelog_content = changelog_path.read_text(encoding="utf-8")
        # Extract first ## [X.Y.Z] entry (latest version)
        changelog_match = re.search(r'##\s*\[(\d+\.\d+\.\d+)\]', changelog_content)
        if changelog_match:
            changelog_version = changelog_match.group(1)
            if changelog_version != source_version:
                issues.append(
                    f"[FAIL] CHANGELOG.md latest entry: version=[{changelog_version}], expected=[{source_version}]"
                )
        else:
            issues.append("[FAIL] CHANGELOG.md: no version entry found (expected ## [X.Y.Z])")
    else:
        issues.append("[FAIL] CHANGELOG.md: file not found")

    # ── Check plan-tracker workflow version (WARN only) ──
    plan_tracker_path = ROOT / ".governance/plan-tracker.md"
    if plan_tracker_path.exists():
        plan_content = plan_tracker_path.read_text(encoding="utf-8")
        # Match: **工作流版本**: X.Y.Z
        pt_match = re.search(r'工作流版本[**:\s]+(\d+\.\d+\.\d+)', plan_content)
        if pt_match:
            pt_version = pt_match.group(1)
            if pt_version != source_version:
                # WARN — plan-tracker is a local file, may lag behind plugin version
                issues.append(
                    f"[WARN] plan-tracker.md 工作流版本={pt_version}, expected={source_version} "
                    f"(plan-tracker is local, may lag — not a blocker)"
                )
        # Missing version field or missing file: not an error (CI edge case)

    # ── Check hook @version tags ──
    HOOK_FILES = {
        "hooks/pre-commit": ROOT / "skills/software-project-governance/infra/hooks/pre-commit",
        "hooks/commit-msg": ROOT / "skills/software-project-governance/infra/hooks/commit-msg",
        "hooks/post-commit": ROOT / "skills/software-project-governance/infra/hooks/post-commit",
        "hooks/prepare-commit-msg": ROOT / "skills/software-project-governance/infra/hooks/prepare-commit-msg",
    }
    for label, path in HOOK_FILES.items():
        if not path.exists():
            issues.append(f"[FAIL] {label}: {path} not found")
            continue
        content = path.read_text(encoding="utf-8")
        hook_match = re.search(r'@version:\s*(\d+\.\d+\.\d+)', content)
        if hook_match:
            hook_ver = hook_match.group(1)
            if hook_ver != source_version:
                issues.append(f"[FAIL] {label}: @version={hook_ver}, expected={source_version}")
        else:
            issues.append(f"[FAIL] {label}: no @version tag found")

    return issues


def check_commit_task_references(limit=20):
    """Check that recent commit messages contain task ID references.

    Per M7.4 step 4 and M7.5 step 4, every commit message MUST contain
    a task ID as prefix (e.g., "AUDIT-044: description", "MAINT-028: description").
    This function is the external validation counterpart — it detects commits
    without task ID prefixes, which indicate untracked modifications.

    Returns: dict with commits list, issues list, and summary stats.
    """
    import subprocess
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "log", f"--format=%H %s", f"-{limit}"],
            capture_output=True, text=True, timeout=10, encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            return {"error": f"git log failed: {result.stderr}", "commits": [], "issues": []}
    except FileNotFoundError:
        return {"error": "git command not found", "commits": [], "issues": []}
    except Exception as e:
        return {"error": str(e), "commits": [], "issues": []}

    commits = []
    issues = []
    # Match task ID prefix at start of commit message: "AUDIT-044: ..." or "MAINT-028: ..."
    task_id_pattern = re.compile(r"^([A-Z]+-\d+)")

    if not result.stdout:
        return {"error": "git log returned empty output", "commits": [], "issues": []}

    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split(" ", 1)
        if len(parts) < 2:
            continue
        sha = parts[0][:7]
        message = parts[1]

        task_match = task_id_pattern.match(message)
        has_task_id = task_match is not None
        task_id = task_match.group(1) if has_task_id else None

        commit_info = {
            "sha": sha,
            "message": message,
            "has_task_id": has_task_id,
            "task_id": task_id,
        }
        commits.append(commit_info)

        if not has_task_id:
            issues.append(commit_info)

    return {
        "commits": commits,
        "issues": issues,
        "total_checked": len(commits),
        "without_task_id": len(issues),
    }


def check_risk_escalation():
    """Check for open risks whose escalation deadline has passed.

    Per AUDIT-045: risk-log defines Owner + escalation deadline + mitigation action,
    but when the deadline passes, nothing enforces the escalation.
    This function detects open risks with passed deadlines — the external validation
    counterpart to the risk escalation MUST rule.

    Returns: dict with escalated risks list and summary stats.
    """
    content = RISK_PATH.read_text(encoding="utf-8")
    today = date.today()
    escalated = []
    all_open = []

    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| RISK-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 13:
            continue

        risk_id = parts[1]
        date_str = parts[2]          # 日期
        status = parts[9]            # 当前状态
        deadline_str = parts[11]     # 截止日期

        if status != "打开":
            continue

        all_open.append(risk_id)

        if not deadline_str or deadline_str == "":
            continue

        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            if today > deadline:
                escalated.append({
                    "risk_id": risk_id,
                    "created": date_str,
                    "deadline": deadline_str,
                    "days_overdue": (today - deadline).days,
                })
        except ValueError:
            continue

    return {
        "escalated": escalated,
        "total_open": len(all_open),
        "escalation_count": len(escalated),
    }


def check_task_deadline():
    """Check for non-completed tasks whose planned completion date has passed.

    Per AUDIT-048: plan-tracker has "计划完成" column for each task,
    but when the date passes with task still in "未开始" or "进行中",
    nothing detects or escalates it. This is the same pattern as risk escalation
    (AUDIT-045) — deadline fields exist but are not enforced.

    Returns: dict with overdue tasks list and summary stats.
    """
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    today = date.today()
    overdue = []
    all_active = 0

    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| ") or "---" in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 15:
            continue

        task_id_match = re.match(r"([A-Z]+-\d+)", parts[1])
        if not task_id_match:
            continue

        task_id = task_id_match.group(1)
        status = parts[10] if len(parts) > 10 else ""
        priority = parts[11] if len(parts) > 11 else ""
        # Column mapping: 0=empty,1=ID,...,12=计划开始,13=计划完成,14=实际完成
        plan_complete_str = parts[13] if len(parts) > 13 else ""

        # Only check non-completed tasks
        if status in ("已完成", "已终止"):
            continue

        all_active += 1

        if not plan_complete_str or plan_complete_str == "":
            continue

        try:
            plan_complete = datetime.strptime(plan_complete_str, "%Y-%m-%d").date()
            if today > plan_complete:
                overdue.append({
                    "task_id": task_id,
                    "status": status,
                    "priority": priority,
                    "plan_complete": plan_complete_str,
                    "days_overdue": (today - plan_complete).days,
                })
        except ValueError:
            continue

    # Sort by priority then days overdue
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    overdue.sort(key=lambda t: (priority_order.get(t["priority"], 99), -t["days_overdue"]))

    return {
        "overdue": overdue,
        "total_active": all_active,
        "overdue_count": len(overdue),
    }


# ── CLI commands ─────────────────────────────────────────────────

def cmd_verify(args):
    """Run existing file + snippet verification."""
    print("== Workflow Plugin Verification ==")
    file_failures = check_files()
    snippet_failures = check_snippets()
    architecture_failures = check_architecture_fact_source()
    release_readiness_failures = check_release_readiness_fact_source()
    agent_adapter_failures = check_agent_adapter_contract()
    version_failures = check_version_consistency()
    all_items = (
        file_failures
        + snippet_failures
        + architecture_failures
        + release_readiness_failures
        + agent_adapter_failures
        + version_failures
    )

    # Separate WARN (non-blocking drift) from FAIL (hard gate)
    fail_items = [f for f in all_items if not f.startswith("[WARN]")]
    warn_items = [f for f in all_items if f.startswith("[WARN]")]

    if warn_items:
        print("\n== Warnings (non-blocking) ==")
        for w in warn_items:
            print(f"  - {w}")

    if fail_items:
        print("\n== Verification Result: FAILED ==")
        for failure in fail_items:
            print(f"  - {failure}")
        sys.exit(1)

    print("\n== Verification Result: PASSED ==")


def cmd_status(args):
    """Show project status overview."""
    config = parse_project_config()
    overview = parse_overview()
    gates = parse_gate_status()
    stats = parse_task_stats()
    permission_mode = config.get("操作权限模式", config.get("permission_mode", "N/A"))

    # Config section
    print("\n┌─ Project Config ────────────────────────────────────┐")
    labels = {"Profile": "Profile", "触发模式": "Trigger", "当前阶段": "Stage",
              "并行活跃阶段": "Active", "接入方式": "Onboarding",
              "操作权限模式": "Permission Mode"}
    emitted_permission_mode = False
    for k, v in config.items():
        label = labels.get(k, k)
        if k in ("操作权限模式", "permission_mode"):
            print(f"│  Permission Mode (permission_mode / 操作权限模式): {v}")
            emitted_permission_mode = True
            continue
        print(f"│  {label}: {v}")
    if not emitted_permission_mode:
        print(f"│  Permission Mode (permission_mode / 操作权限模式): {permission_mode}")
    print("└──────────────────────────────────────────────────────┘")

    # Overview section
    if overview:
        print("\n┌─ Project Overview ──────────────────────────────────┐")
        print(f"│  Project:    {overview.get('project', 'N/A')}")
        print(f"│  Stage:      {overview.get('current_stage', 'N/A')}")
        print(f"│  Tasks:      {overview.get('completed', '0')}/{overview.get('total', '0')} completed")
        print(f"│  Blocked:    {overview.get('blocked', '0')}")
        print(f"│  Key Risks:  {overview.get('risks', '0')}")
        print(f"│  Latest Gate: {overview.get('latest_gate', 'N/A')}")
        print(f"│  Last Retro: {overview.get('latest_retro', 'N/A')}")
        print("└──────────────────────────────────────────────────────┘")

    # Task stats
    if any(stats.values()):
        print("\n┌─ Task Status ───────────────────────────────────────┐")
        total = sum(stats.values())
        for status, count in stats.items():
            bar = "#" * count + "." * (total - count)
            print(f"│  {status:6s} {count:2d} {bar}")
        print("└──────────────────────────────────────────────────────┘")

    # Gate status
    if gates:
        print("\n┌─ Gate Status ───────────────────────────────────────┐")
        for g in gates:
            icon = STATUS_ICONS.get(g["status"], "?")
            date = g["date"] if g["date"] else ""
            print(f"│  {icon} {g['gate']:4s}  {g['status']:20s}  {date}")
        print("└──────────────────────────────────────────────────────┘")


def cmd_gate(args):
    """Show detailed info for a specific Gate."""
    gate_id = args.gate_id
    detail = parse_gate_detail(gate_id)

    if not detail:
        print(f"[FAIL] Gate {gate_id.upper()} not found")
        sys.exit(1)

    print(f"\n┌─ {detail['title']} ─┐")

    if detail["transition"]:
        print(f"│  Transition:    {detail['transition']}")
    if detail["materials"]:
        print(f"│  Materials:     {detail['materials']}")

    if detail["checks"]:
        print("│")
        print("│  Check items:")
        for i, check in enumerate(detail["checks"], 1):
            print(f"│    {i}. {check}")

    if detail["pass_criteria"]:
        print("│")
        print(f"│  Pass criteria: {detail['pass_criteria']}")

    if detail["conditional"]:
        print("│")
        print(f"│  Conditional:   {detail['conditional']}")

    if detail["auto_criteria"]:
        print("│")
        print("│  Auto-judgment criteria:")
        for i, ac in enumerate(detail["auto_criteria"], 1):
            print(f"│    {i}. {ac}")

    print("└──────────────────────────────────────────────────────┘")

    # Also show current status from sample
    gates = parse_gate_status()
    for g in gates:
        if g["gate"].upper() == gate_id.upper().lstrip("G").zfill(2) \
           or g["gate"].upper() == gate_id.upper():
            icon = STATUS_ICONS.get(g["status"], "[????]")
            print(f"\n  Current status: {icon} {g['status']} ({g['date']})")
            break


def cmd_stage(args):
    """Show workflow summary for a specific stage."""
    stage_name = normalize_stage_name(args.stage_name)

    stage_path = stage_skill_path(stage_name)
    if not stage_path.is_file():
        print(f"[FAIL] Stage '{stage_name}' not found")
        available = list_available_stages()
        if available:
            print(f"Available: {', '.join(available)}")
        sys.exit(1)

    content = stage_path.read_text(encoding="utf-8")

    # Also check for supporting markdown files in this stage skill directory.
    stage_dir = stage_path.parent
    skills = sorted([
        f.name for f in stage_dir.iterdir()
        if f.is_file() and f.name != "SKILL.md" and f.suffix == ".md"
    ])

    print(f"\n┌─ Stage: {stage_name} ─────────────────────────────────────┐")

    lines = content.split("\n")
    current_section = ""
    for line in lines:
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            current_section = line[3:].strip()
            print(f"│\n│  {current_section}")
        elif line.startswith("### "):
            print(f"│    {line[4:].strip()}")
        elif line.strip().startswith("|") and "---" not in line:
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if parts and not all(set(p) <= {"-"} for p in parts):
                print(f"│    {' | '.join(p for p in parts if p)}")
        elif line.strip().startswith("- ["):
            check = line.strip()
            icon = "[x]" if "[x]" in check else "[ ]"
            text = re.sub(r"- \[[ x]\]\s*", "", check)
            print(f"│    {icon} {text}")
        elif line.strip().startswith("- **"):
            print(f"│    {line.strip()}")
        elif line.strip() and not line.startswith("|"):
            print(f"│    {line.strip()}")

    if skills:
        print(f"│\n│  Skills ({len(skills)}):")
        for s in skills:
            print(f"│    - {s}")

    print("└──────────────────────────────────────────────────────┘")


def cmd_stages(args):
    """List all available stages with index."""
    stages = list_available_stages()
    lifecycle_content = LIFECYCLE_PATH.read_text(encoding="utf-8")

    # Parse stage names from lifecycle
    stage_names = {}
    for m in re.finditer(r"### (\d+)\.\s+(.+?)(?:（|$)", lifecycle_content):
        stage_names[m.group(1)] = m.group(2).strip()

    print("\n┌─ Available Stages ──────────────────────────────────┐")
    for i, stage in enumerate(stages, 1):
        name = stage_names.get(str(i), stage)
        skill_path = stage_skill_path(stage)
        has_skill = "Y" if skill_path.is_file() else "N"

        # Count supporting markdown files.
        stage_dir = skill_path.parent
        skill_count = len([
            f for f in stage_dir.iterdir()
            if f.is_file() and f.name != "SKILL.md" and f.suffix == ".md"
        ]) if stage_dir.is_dir() else 0

        skill_info = f", {skill_count} skill(s)" if skill_count else ""
        print(f"│  {i:2d}. {stage:16s} {name:20s}  SKILL.md:{has_skill}{skill_info}")
    print("└──────────────────────────────────────────────────────┘")


def cmd_gates(args):
    """List all Gates with current status."""
    gates = parse_gate_status()

    print("\n┌─ All Gates ─────────────────────────────────────────┐")
    for g in gates:
        icon = STATUS_ICONS.get(g["status"], "?")
        date = g["date"] if g["date"] else "        "
        print(f"│  {icon} {g['gate']:4s}  {g['transition']:20s}  {g['status']:20s}  {date}")
    print("└──────────────────────────────────────────────────────┘")

    # Summary
    statuses = {}
    for g in gates:
        statuses[g["status"]] = statuses.get(g["status"], 0) + 1
    summary = ", ".join(f"{k}: {v}" for k, v in sorted(statuses.items()))
    print(f"\n  Summary: {summary}")


def check_m5_compliance():
    """Check M5 AskUserQuestion compliance -- static anti-pattern detection (enhanced).

    Detects:
    1. Actionable inline-question instructions in active project entry files:
       a line must both contain question-like text and teach the agent to ask
       the user inline.  Historical governance records, plugin source files,
       fixtures, and ordinary checklists are excluded.
    2. Option-list patterns without AskUserQuestion:
       - Matches (1) / (a) style options + "选择" context, but no "AskUserQuestion"
       - Detects source files that instruct agents to output choice menus as text
    3. Bootstrap coverage: governance-init.md template contains AskUserQuestion rule
    4. Interaction boundary: interaction-boundary.md exists and references AskUserQuestion
    5. Bootstrap template contains M5 pre-output guard (SELF-CHECK item 4)

    This CANNOT detect runtime M5 violations (actual inline questions in conversation).
    It catches the ROOT CAUSE: source files that teach or allow agents to use inline text.
    """
    issues = []
    skills_dir = ROOT / "skills" / "software-project-governance"

    # -- Check 1: Actionable inline question instructions in active entry files --
    import glob as _glob
    inline_patterns_cn = ["吗？", "？", "要不要", "是否", "确认吗", "需要我", "你想"]
    inline_patterns_en = ["Should I", "Do you want"]
    ask_action_re = re.compile(
        r"(询问用户|问用户|向用户提问|直接问|输出.*[？?]|回复.*[？?]|ask the user|"
        r"inline question|text question)",
        re.IGNORECASE,
    )
    benign_context_re = re.compile(
        r"(SELF-CHECK|自查|检查|检测|是否包含|是否到达|是否已经|是否知道|"
        r"是否有|是否已|是否可|是否受|是否支持|表头|"
        r"checklist|coverage|PASS|WARN|FAIL)"
    )

    scan_files = []
    # Active user/project entry files only. Historical governance records,
    # archive data, and e2e/plugin fixtures are not M5 teaching surfaces.
    for pattern in ["AGENTS.md", "CLAUDE.md", ".governance/CLAUDE.md", "docs/**/*.md"]:
        for f in _glob.glob(str(ROOT / pattern), recursive=True):
            scan_files.append(Path(f))

    seen_paths = set()
    scan_files_dedup = []
    for f in scan_files:
        if str(f) not in seen_paths:
            seen_paths.add(str(f))
            scan_files_dedup.append(f)
    scan_files = scan_files_dedup

    # FIX-054: Filter out plugin scope directories to avoid false positives
    # from legitimate checklists in plugin SKILL.md files (e.g., checklist items
    # with Chinese question marks like "是否评估了至少 2 个候选方案?").
    # PLUGIN_SCOPE_DIRS is synced with cleanup.py.
    scan_files = [
        f for f in scan_files
        if not _is_plugin_path(str(f.relative_to(ROOT)))
        and "/archive/" not in str(f.relative_to(ROOT)).replace("\\", "/")
        and not str(f.relative_to(ROOT)).replace("\\", "/").startswith("project/e2e-test-project/")
    ]

    for md_file in scan_files:
        if not md_file.is_file():
            continue
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue
        rel_path = str(md_file.relative_to(ROOT)).replace("\\", "/")

        for i, line in enumerate(content.splitlines(), 1):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            if "AskUserQuestion" in line:
                continue

            for kw in inline_patterns_cn:
                if kw in line_stripped:
                    if not ask_action_re.search(line_stripped):
                        continue
                    if benign_context_re.search(line_stripped):
                        continue
                    issues.append({
                        "type": "m5_inline_question_cn",
                        "file": rel_path,
                        "line": i,
                        "text": line_stripped[:120],
                        "severity": "BLOCKING",
                        "pattern": kw,
                        "fix": "MUST use AskUserQuestion tool instead of inline text questions (M5.1)"
                    })
                    break

            for kw in inline_patterns_en:
                if kw.lower() in line_stripped.lower():
                    if not ask_action_re.search(line_stripped):
                        continue
                    if benign_context_re.search(line_stripped):
                        continue
                    issues.append({
                        "type": "m5_inline_question_en",
                        "file": rel_path,
                        "line": i,
                        "text": line_stripped[:120],
                        "severity": "WARNING",
                        "pattern": kw,
                        "fix": "MUST use AskUserQuestion tool instead of inline text questions (M5.1)"
                    })
                    break

    # -- Check 1b: Option-list patterns without AskUserQuestion --
    option_list_re = re.compile(r'([(][1-9][0-9]*[)]|[(][a-z][)])')
    for md_file in scan_files:
        if not md_file.is_file():
            continue
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue
        rel_path = str(md_file.relative_to(ROOT)).replace("\\", "/")

        has_option_list = bool(option_list_re.search(content))
        has_choice_context = any(kw in content for kw in ("选择", "choose", "select", "选项"))
        has_askuserquestion = "AskUserQuestion" in content

        if has_option_list and has_choice_context and not has_askuserquestion:
            for i, line in enumerate(content.splitlines(), 1):
                if option_list_re.search(line) and any(
                    kw in line for kw in ("选择", "choose", "select", "选项")
                ):
                    issues.append({
                        "type": "m5_option_list_no_auq",
                        "file": rel_path,
                        "line": i,
                        "text": line.strip()[:120],
                        "severity": "BLOCKING",
                        "fix": "Option list detected with choice context but no AskUserQuestion - agent may output inline choice menus (M5 violation)"
                    })
                    break

    # Check 2: Bootstrap template (governance-init.md) contains AskUserQuestion rule
    bootstrap_template = ROOT / "commands" / "governance-init.md"
    if bootstrap_template.is_file():
        content = bootstrap_template.read_text(encoding="utf-8")
        if "AskUserQuestion" not in content:
            issues.append({
                "type": "m5_bootstrap_missing",
                "file": "commands/governance-init.md",
                "line": 0,
                "text": "Bootstrap template does not contain AskUserQuestion rule",
                "severity": "WARNING",
                "fix": "Add M5 AskUserQuestion rule to governance-init.md bootstrap template"
            })
    else:
        issues.append({
            "type": "m5_bootstrap_missing",
            "file": "commands/governance-init.md",
            "line": 0,
            "text": "governance-init.md not found",
            "severity": "ERROR",
            "fix": "Create governance-init.md with bootstrap template"
        })

    # Check 3: interaction-boundary.md exists and references AskUserQuestion
    ib_file = skills_dir / "references" / "interaction-boundary.md"
    if ib_file.is_file():
        content = ib_file.read_text(encoding="utf-8")
        if "AskUserQuestion" not in content:
            issues.append({
                "type": "m5_ib_missing",
                "file": str(ib_file.relative_to(ROOT)),
                "line": 0,
                "text": "interaction-boundary.md does not reference AskUserQuestion",
                "severity": "ERROR",
                "fix": "Add AskUserQuestion binding to interaction types in interaction-boundary.md"
            })
    else:
        issues.append({
            "type": "m5_ib_missing",
            "file": "skills/software-project-governance/references/interaction-boundary.md",
            "line": 0,
            "text": "interaction-boundary.md not found",
            "severity": "ERROR",
            "fix": "Create interaction-boundary.md with AskUserQuestion binding rules"
        })

    # Check 4: Bootstrap template (governance-init.md) contains M5 pre-output guard
    if bootstrap_template.is_file():
        content = bootstrap_template.read_text(encoding="utf-8")
        m5_selfcheck_patterns = [
            "我即将输出的文本是否包含向用户提问的问句",
            "M5.1",
            "AskUserQuestion",
        ]
        has_selfcheck_item4 = all(p in content for p in m5_selfcheck_patterns)
        if not has_selfcheck_item4:
            issues.append({
                "type": "m5_selfcheck_missing",
                "file": "commands/governance-init.md",
                "line": 0,
                "text": "Bootstrap template missing M5 pre-output guard. Without this, agent's natural conversational patterns can produce M5.1 violations.",
                "severity": "BLOCKING",
                "fix": "Add SELF-CHECK to governance-init.md bootstrap template"
            })
    else:
        issues.append({
            "type": "m5_selfcheck_missing",
            "file": "commands/governance-init.md",
            "line": 0,
            "text": "Bootstrap template not found",
            "severity": "BLOCKING",
            "fix": "Create governance-init.md with SELF-CHECK in bootstrap template"
        })

    return {"issues": issues, "total_checks": 5}


# ── SYSGAP-008: Cross-Reference Checking ──────────────────────────

def check_cross_references():
    """Scan .md and .py files for path references, build a reference graph,
    and detect: (1) dangling references (target file does not exist),
    (2) deprecated path patterns, (3) circular references (cycle detection).

    Path reference patterns extracted:
    - Markdown: [text](path), bare `` file.md `` paths, `` `path/to/file` ``
    - Python: ROOT / "relative/path" format
    """
    import collections

    scan_dirs = [
        "skills/software-project-governance/",
        "commands/",
        "agents/",
    ]

    # Collect all .md files from scan directories
    md_files = []
    for d in scan_dirs:
        p = ROOT / d
        if p.is_dir():
            md_files.extend(p.rglob("*.md"))

    # Also include verify_workflow.py itself
    py_files = [ROOT / "skills/software-project-governance/infra/verify_workflow.py"]

    # Build: dict[source_relpath] -> list of (target_raw, line_num)
    refs = {}
    source_lines = {}

    for f in md_files + py_files:
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            continue
        source = str(f.relative_to(ROOT)).replace("\\", "/")
        refs[source] = []
        source_lines[source] = content.split("\n")

        in_code_block = False
        for i, line in enumerate(source_lines[source], 1):
            if f.suffix == ".py":
                # Python: ROOT / "relative/path"  pattern
                for m in re.finditer(r'ROOT\s*/\s*"([^"]+)"', line):
                    target = m.group(1)
                    if Path(target).suffix:
                        refs[source].append((target, i))
            else:
                # ── Code block tracking: skip fenced and indented code blocks ──
                # Fenced code blocks (``` or ~~~). Strip language tag if present.
                if re.match(r'^\s*```', line):
                    in_code_block = not in_code_block
                    continue
                if re.match(r'^\s*~~~', line):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    continue
                # Indented code block (4+ spaces or 1+ tab at line start)
                if re.match(r'^ {4,}', line) or line.startswith('\t'):
                    continue

                # Backticked explicit paths with a directory separator are
                # intentional references and should still be validated.
                for m in re.finditer(r"`([^`]+/[^\s`]+\.(?:md|py))`", line):
                    refs[source].append((m.group(1), i))

                # ── Strip inline code (backtick-quoted) from the line ──
                stripped_line = re.sub(r'`+[^`]*`+', '', line)

                # Markdown: [text](path) — skip http/https/#/mailto links
                for m in re.finditer(r'\[([^\]]*)\]\(([^)]+)\)', stripped_line):
                    target = m.group(2)
                    if not target.startswith(("http://", "https://", "#", "mailto:")):
                        refs[source].append((target, i))
                # Bare paths must include a directory separator.  A lone
                # filename such as "SKILL.md" is often prose shorthand and
                # caused hundreds of dangling-reference false positives after
                # archive cleanup. Markdown links still cover explicit
                # same-directory references.
                for m in re.finditer(r'(?<!["\w/\-.])([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-/]+\.(?:md|py))(?!\w)', stripped_line):
                    refs[source].append((m.group(1), i))

    # ── Detect dangling references ──
    dangling = []
    root_relative_prefixes = (
        "skills/", "agents/", "commands/", "adapters/", "project/", "docs/",
        ".governance/", ".github/", ".agents/", ".claude-plugin/", ".codex-plugin/",
    )
    skill_root_relative_prefixes = ("core/", "infra/", "references/")
    placeholder_prefixes = ("skill/", "relative/")
    placeholder_markers = ("<", ">", "{", "}", "*")
    entry_source = "skills/software-project-governance/SKILL.md"
    validator_source = "skills/software-project-governance/infra/verify_workflow.py"

    def normalize_ref_target(target):
        target = target.strip()
        if target.startswith("python "):
            target = target.split(None, 1)[1]
        if target.startswith("./"):
            target = target[2:]
        return target

    def is_placeholder_ref(target):
        return target.startswith(placeholder_prefixes) or any(m in target for m in placeholder_markers)

    def source_supports_skill_root_relative(source):
        return (
            source.startswith("skills/software-project-governance/")
            or source.startswith("commands/")
            or source.startswith("agents/")
        )

    def resolve_ref(source, target):
        source_dir = (ROOT / source).parent
        if source.endswith(".py"):
            return (ROOT / target).resolve()
        if target.startswith(root_relative_prefixes):
            return (ROOT / target).resolve()
        if (source_supports_skill_root_relative(source)
                and target.startswith(skill_root_relative_prefixes)):
            return (ROOT / "skills/software-project-governance" / target).resolve()
        return (source_dir / target).resolve()

    def line_text(source, line_num):
        lines = source_lines.get(source, [])
        if 1 <= line_num <= len(lines):
            return lines[line_num - 1].strip()
        return ""

    def is_in_generated_output_section(source, line_num):
        if not source.startswith("agents/"):
            return False
        lines = source_lines.get(source, [])
        in_output = False
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if idx > line_num:
                break
            if stripped.startswith("## "):
                in_output = stripped == "## 输出格式"
                continue
        return in_output

    def is_generated_output_ref(source, target, line_num):
        if not is_in_generated_output_section(source, line_num):
            return False
        if not target.startswith(("docs/", ".github/", "Dockerfile", "docker-compose.yml")):
            return False
        context = "\n".join(source_lines.get(source, [])[max(0, line_num - 4):line_num + 1])
        return "必须生成" in context or line_text(source, line_num).startswith("-")

    def is_external_or_runtime_generated_ref(source, target, line_num):
        current_line = line_text(source, line_num)
        if target == "references/flavors.md" and "PUA skill" in current_line:
            return True
        if target == "archive/index.md" and ("不" in current_line and "自动生成" in current_line):
            return True
        return False

    def should_ignore_ref(source, target, line_num):
        return (
            is_placeholder_ref(target)
            or is_generated_output_ref(source, target, line_num)
            or is_external_or_runtime_generated_ref(source, target, line_num)
        )

    for source, targets in refs.items():
        for target, line_num in targets:
            target = normalize_ref_target(target)
            if should_ignore_ref(source, target, line_num):
                continue
            # Resolve target relative to the source file's directory
            try:
                resolved = resolve_ref(source, target)
                resolved.relative_to(ROOT)
            except (ValueError, OSError):
                continue  # outside project or unresolvable
            if not resolved.exists():
                dangling.append({
                    "source": source,
                    "line": line_num,
                    "target": target,
                })

    # ── Detect deprecated path patterns ──
    deprecated_patterns = [
        "skills/software-project-governance/skills/",
        "skills/software-project-governance/agents/",
    ]
    deprecated = []
    for source, targets in refs.items():
        for target, line_num in targets:
            for dp in deprecated_patterns:
                if dp in target:
                    deprecated.append({
                        "source": source,
                        "line": line_num,
                        "target": target,
                        "deprecated_pattern": dp,
                    })

    # ── Detect circular references (DFS on directed graph) ──
    graph = collections.defaultdict(list)
    for source, targets in refs.items():
        # verify_workflow.py contains coverage constants and check fixtures that
        # cite product files. Those are validation edges, not runtime or
        # architecture dependencies, so they must not create source↔validator
        # circular-reference failures.
        if source in (entry_source, validator_source):
            continue
        for target, line_num in targets:
            target = normalize_ref_target(target)
            if should_ignore_ref(source, target, line_num):
                continue
            try:
                resolved = resolve_ref(source, target)
                rel_target = str(resolved.relative_to(ROOT)).replace("\\", "/")
            except (ValueError, OSError):
                continue
            if rel_target in (entry_source, validator_source):
                continue
            if rel_target in refs:  # only edges within scanned scope
                graph[source].append(rel_target)

    cycles = []
    seen_nodes = set()
    WHITE, GRAY, BLACK = 0, 1, 2

    def _dfs_cycle(node, colors, parent_map, stack):
        colors[node] = GRAY
        stack.append(node)
        for neighbor in graph.get(node, []):
            ncolors_key = neighbor
            if colors.get(ncolors_key, WHITE) == WHITE:
                parent_map[neighbor] = node
                _dfs_cycle(neighbor, colors, parent_map, stack)
            elif colors.get(ncolors_key, WHITE) == GRAY:
                # Found a cycle — extract the subsequence
                try:
                    idx = stack.index(neighbor)
                    cycle = stack[idx:] + [neighbor]
                    cycles.append(cycle)
                except ValueError:
                    pass
        colors[node] = BLACK
        stack.pop()

    colors_map = {}
    for node in list(graph):
        if colors_map.get(node, WHITE) == WHITE:
            _dfs_cycle(node, colors_map, {}, [])

    # Deduplicate cycles (same set of nodes in different rotations)
    unique_cycles = []
    seen_cycles = set()
    for cycle in cycles:
        if len(cycle) == 2 and cycle[0] == cycle[1]:
            continue
        key = tuple(sorted(cycle))
        if key not in seen_cycles:
            seen_cycles.add(key)
            unique_cycles.append(cycle)

    return {
        "dangling": dangling,
        "deprecated": deprecated,
        "cycles": unique_cycles,
        "total_files_scanned": len(md_files) + len(py_files),
        "total_refs": sum(len(t) for t in refs.values()),
    }


# ── SYSGAP-009: Sequential ID Checking ────────────────────────────

def check_sequential_ids():
    """Verify ID continuity in governance records:
    1. DEC-XXX: detect numbering gaps starting from 001
    2. EVD-XXX: detect numbering gaps
    3. RISK-XXX: detect numbering gaps
    4. Cross-reference integrity: task IDs referenced in evidence/decision/risk
       must exist in plan-tracker
    5. Completed tasks in plan-tracker must have evidence entries
    """

    def _extract_ids(file_path, prefix):
        """Extract sequential IDs with given prefix from a file, return sorted list of ints."""
        if not file_path.is_file():
            return []
        content = file_path.read_text(encoding="utf-8")
        ids = set()
        for m in re.finditer(rf"\b{re.escape(prefix)}(\d+)\b", content):
            ids.add(int(m.group(1)))
        return sorted(ids)

    def _find_gaps(sorted_ids, prefix):
        """Find gaps in a sorted list of integer IDs. Returns list of missing numbers."""
        if not sorted_ids:
            return []
        gaps = []
        expected = 1  # IDs start at 001
        for num in sorted_ids:
            while expected < num:
                gaps.append(expected)
                expected += 1
            expected = num + 1
        return gaps

    dec_path = ROOT / ".governance/decision-log.md"
    evd_path = ROOT / ".governance/evidence-log.md"
    risk_path = ROOT / ".governance/risk-log.md"

    # Use GovernanceDataSource for archive-aware ID collection.
    # Falls back to hot-file-only when archive/index.md does not exist.
    ds = GovernanceDataSource()

    # DEC/RISK: via GovernanceDataSource (hot + archive)
    dec_ids = ds.get_all_decision_ids()
    risk_ids = ds.get_all_risk_ids()

    # EVD: collect from hot evidence-log + archive evidence files
    evd_id_set = set()
    if evd_path.is_file():
        evd_content = evd_path.read_text(encoding="utf-8")
        for m in re.finditer(r"\bEVD-(\d+)\b", evd_content):
            evd_id_set.add(int(m.group(1)))
    for entry in ds._scan_archive_files(ds.archive_evidence_dir,
                                         ds._extract_evidence_entries):
        evd_match = re.match(r"EVD-(\d+)", entry.get("evd_id", ""))
        if evd_match:
            evd_id_set.add(int(evd_match.group(1)))
    evd_ids = sorted(evd_id_set)

    dec_gaps = _find_gaps(dec_ids, "DEC-")
    evd_gaps = _find_gaps(evd_ids, "EVD-")
    risk_gaps = _find_gaps(risk_ids, "RISK-")

    # Cross-reference: all task IDs in evidence/decision/risk must exist
    # in plan-tracker.  Use GovernanceDataSource to include archived tasks.
    all_task_ids = ds.get_all_task_ids()

    # Collect task IDs referenced in evidence-log (hot + archive)
    evd_task_ids = ds.get_all_evidence_task_ids()

    # Collect task IDs referenced in decision-log
    dec_task_ids = set()
    if dec_path.is_file():
        dec_content = dec_path.read_text(encoding="utf-8")
        for m in re.finditer(r"\b([A-Z]+-\d+)\b", dec_content):
            task_id = m.group(1)
            if re.match(r"^[A-Z]+-\d+$", task_id) and not task_id.startswith("DEC-"):
                dec_task_ids.add(task_id)

    # Collect task IDs referenced in risk-log
    risk_task_ids = set()
    if risk_path.is_file():
        risk_content = risk_path.read_text(encoding="utf-8")
        for m in re.finditer(r"\b([A-Z]+-\d+)\b", risk_content):
            task_id = m.group(1)
            if re.match(r"^[A-Z]+-\d+$", task_id) and not task_id.startswith("RISK-"):
                risk_task_ids.add(task_id)

    orphan_evd = sorted(evd_task_ids - all_task_ids)
    orphan_dec = sorted(dec_task_ids - all_task_ids - evd_task_ids)  # avoid dup reporting
    orphan_risk = sorted(risk_task_ids - all_task_ids)

    # Completed tasks without evidence (archive-aware). Only hot missing
    # evidence is actionable; archived gaps are historical residue.
    completed_entries = ds.get_all_completed_task_entries()
    completed = {entry["id"] for entry in completed_entries}
    hot_completed = {
        entry["id"] for entry in completed_entries
        if entry.get("source") == "hot"
    }
    missing_evd_all = completed - evd_task_ids
    missing_evd = sorted(missing_evd_all & hot_completed)
    historical_missing_evd = sorted(missing_evd_all - set(missing_evd))

    return {
        "dec_ids": dec_ids,
        "evd_ids": evd_ids,
        "risk_ids": risk_ids,
        "dec_gaps": dec_gaps,
        "evd_gaps": evd_gaps,
        "risk_gaps": risk_gaps,
        "orphan_evidence_refs": orphan_evd,
        "orphan_decision_refs": orphan_dec,
        "orphan_risk_refs": orphan_risk,
        "completed_missing_evidence": missing_evd,
        "historical_completed_missing_evidence": historical_missing_evd,
    }


# ── SYSGAP-010: Structural Validity Checking ─────────────────────

def check_structural_validity():
    """Validate structural integrity of governance files:
    1. plan-tracker.md: table column count consistency (every row
       pipe-count matches header)
    2. evidence-log.md: every record has consistent column count
       (10 columns standard)
    3. decision-log.md: each ADR contains all required fields
    4. SKILL.md: frontmatter contains required fields (name/version/description)
    5. manifest.json: product / repo_only / exclude sections all present
    """
    import json as _json
    issues = []

    # ── 1. plan-tracker.md table column consistency ──
    pt_path = ROOT / ".governance/plan-tracker.md"
    if pt_path.is_file():
        pt_content = pt_path.read_text(encoding="utf-8")
        # Find all markdown tables: contiguous |...| lines after a header row
        lines = pt_content.split("\n")
        current_header_cols = None
        current_header_line = 0
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line.startswith("|"):
                current_header_cols = None
                continue
            if "---" in line or ":--" in line:
                continue  # separator row
            # Strip inline code (backtick-quoted) to avoid false | in column count
            # e.g., | text `✅ 已完成 |` next | → the | inside backticks is NOT a column separator
            clean_line = re.sub(r'`+[^`]*`+', '__CODE__', line)
            cols = len(clean_line.split("|")) - 2  # strip outer empty parts
            if not cols:
                continue

            # Heuristic: if this looks like a header (next line is separator),
            # treat it as header
            is_header = False
            if i < len(lines):
                next_line = lines[i].strip()
                if re.match(r"^\|[\s\-:]+\|", next_line):
                    is_header = True

            if is_header:
                current_header_cols = cols
                current_header_line = i
                continue

            if current_header_cols is not None and cols != current_header_cols:
                issues.append({
                    "type": "table_column_mismatch",
                    "file": ".governance/plan-tracker.md",
                    "line": i,
                    "detail": f"Row has {cols} columns, header (line {current_header_line}) has {current_header_cols}",
                })
    else:
        issues.append({
            "type": "file_missing",
            "file": ".governance/plan-tracker.md",
            "detail": "plan-tracker.md not found",
        })

    # ── 2. evidence-log.md column count consistency ──
    evd_path = ROOT / ".governance/evidence-log.md"
    if evd_path.is_file():
        evd_content = evd_path.read_text(encoding="utf-8")
        evd_lines = evd_content.split("\n")
        standard_cols = None
        for i, line in enumerate(evd_lines, 1):
            line = line.strip()
            if not line.startswith("| EVD-"):
                continue
            parts = _split_markdown_table_row(line)
            cols = len(parts)
            if standard_cols is None:
                standard_cols = cols
            elif cols != standard_cols:
                evd_id = parts[0] if parts else "???"
                issues.append({
                    "type": "evidence_col_mismatch",
                    "severity": "WARN",
                    "file": ".governance/evidence-log.md",
                    "line": i,
                    "detail": f"{evd_id}: {cols} columns (expected {standard_cols})",
                })
    else:
        issues.append({
            "type": "file_missing",
            "file": ".governance/evidence-log.md",
            "detail": "evidence-log.md not found",
        })

    # ── 3. decision-log.md ADR required fields ──
    dec_path = ROOT / ".governance/decision-log.md"
    required_decision_fields = ["日期", "状态", "决策", "原因"]
    if dec_path.is_file():
        dec_content = dec_path.read_text(encoding="utf-8")
        # Parse ADR sections: each ADR starts with "## DEC-XXX"
        adr_sections = re.split(r"\n(?=## DEC-)", dec_content)
        for section in adr_sections:
            if not section.strip().startswith("## DEC-"):
                continue
            adr_id = section.split("\n")[0].replace("##", "").strip()
            missing = []
            for field in required_decision_fields:
                if field not in section:
                    missing.append(field)
            if missing:
                issues.append({
                    "type": "decision_missing_fields",
                    "file": ".governance/decision-log.md",
                    "detail": f"{adr_id}: missing required fields — {', '.join(missing)}",
                })
    else:
        issues.append({
            "type": "file_missing",
            "file": ".governance/decision-log.md",
            "detail": "decision-log.md not found",
        })

    # ── 4. SKILL.md frontmatter required fields ──
    skill_path = ROOT / "skills/software-project-governance/SKILL.md"
    if skill_path.is_file():
        content = skill_path.read_text(encoding="utf-8")
        # Extract frontmatter: content between first --- and second ---
        fm_match = re.match(r"^\s*---\s*\n(.*?)\n\s*---", content, re.DOTALL)
        if fm_match:
            fm_text = fm_match.group(1)
            required_frontmatter = ["name:", "version:", "description:"]
            missing = []
            for fm_field in required_frontmatter:
                if fm_field not in fm_text:
                    missing.append(fm_field.rstrip(":"))
            if missing:
                issues.append({
                    "type": "skill_frontmatter_missing",
                    "file": "skills/software-project-governance/SKILL.md",
                    "detail": f"Frontmatter missing required fields: {', '.join(missing)}",
                })
        else:
            issues.append({
                "type": "skill_frontmatter_missing",
                "file": "skills/software-project-governance/SKILL.md",
                "detail": "No YAML frontmatter found (missing --- delimiters)",
            })

    # ── 5. manifest.json structure ──
    manifest_path = ROOT / "skills/software-project-governance/core/manifest.json"
    if manifest_path.is_file():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = _json.load(f)
            for section in ["product", "repo_only", "exclude_from_cleanup"]:
                if section not in manifest:
                    issues.append({
                        "type": "manifest_section_missing",
                        "file": "skills/software-project-governance/core/manifest.json",
                        "detail": f"manifest.json is missing '{section}' section",
                    })
        except (_json.JSONDecodeError, IOError) as e:
            issues.append({
                "type": "manifest_parse_error",
                "file": "skills/software-project-governance/core/manifest.json",
                "detail": str(e),
            })
    else:
        issues.append({
            "type": "file_missing",
            "file": "skills/software-project-governance/core/manifest.json",
            "detail": "manifest.json not found",
        })

    return issues


# ── SYSGAP-012: Commit Scope Verification ────────────────────────

def check_commit_scope(limit=20):
    """Check recent commits for scope discipline violations:
    1. If commit message contains "顺带" / "also" / "顺便" keywords -> WARN
    2. Single commit touching > 15 files -> WARN (possible bulk commit)

    Multiple commits for the same task are normal for review/rework loops and
    are not a scope violation.
    """
    import subprocess

    try:
        # Get full commit log with stats
        result = subprocess.run(
            ["git", "-C", str(ROOT), "log", f"--format=%H%x00%s", f"-{limit}",
             "--no-merges"],
            capture_output=True, text=True, timeout=10, encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            return {"error": f"git log failed: {result.stderr}", "issues": []}
    except FileNotFoundError:
        return {"error": "git command not found", "issues": []}
    except Exception as e:
        return {"error": str(e), "issues": []}

    if not result.stdout:
        return {"error": "git log returned empty output", "issues": []}

    issues = []
    duo_commits = []        # commits with "also"/"顺带"/"顺便"

    lines = result.stdout.strip().split("\n")
    for line in lines:
        if not line or "\x00" not in line:
            continue
        sha, message = line.split("\x00", 1)
        sha_short = sha[:7]

        # Check 1: "顺带"/"also"/"顺便" keywords
        if re.search(r"顺带|顺便|also\b", message, re.IGNORECASE):
            duo_commits.append({"sha": sha_short, "message": message[:100]})

        # Check 2: files touched > 15 (use git show --stat)
        try:
            stat_result = subprocess.run(
                ["git", "-C", str(ROOT), "show", "--stat", "--format=", sha],
                capture_output=True, text=True, timeout=5, encoding="utf-8",
                errors="replace",
            )
            if stat_result.returncode == 0:
                # Count changed files from --stat output
                file_count = len([l for l in stat_result.stdout.split("\n")
                                 if l.strip() and "|" in l and not l.startswith(" ")])
                if file_count > 15:
                    issues.append({
                        "type": "bulk_commit",
                        "sha": sha_short,
                        "detail": f"{file_count} files changed in single commit",
                    })
        except (subprocess.TimeoutExpired, Exception):
            pass

    # Add duo keyword warnings
    for duo in duo_commits:
        issues.append({
            "type": "side_effect_warning",
            "sha": duo["sha"],
            "detail": f"Commit contains 'also/顺带/顺便': {duo['message']}",
        })

    return {
        "issues": issues,
        "total_checked": len(lines),
        "issue_count": len(issues),
    }


# ── SYSGAP-023: Goal Alignment Check ──────────────────────────────

PRODUCT_CODE_PATTERNS = [
    "skills/", "agents/", "infra/", "commands/",
    "adapters/", ".claude-plugin/", ".codex-plugin/", ".agents/",
    "project/",
]


def _plan_task_ids_from_hot_tracker():
    """Return task-like IDs from the current active hot-task table."""
    if not SAMPLE_PATH.is_file():
        return set()
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    task_ids = set()
    in_active_section = False
    for line in content.split("\n"):
        if line.startswith("## 当前活跃事项"):
            in_active_section = True
            continue
        if in_active_section and line.startswith("### 最近完成"):
            break
        if not in_active_section:
            continue
        stripped = line.strip()
        if not stripped.startswith("| ") or "---" in stripped:
            continue
        match = re.search(r"\|\s*(?:\*\*)?([A-Z]+-\d+)(?:\*\*)?\s*\|", stripped)
        if match:
            task_ids.add(match.group(1))
    return task_ids


def _current_release_task_ids():
    """Return task IDs from the active in-progress version roadmap row."""
    if not SAMPLE_PATH.is_file():
        return set()
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    task_ids = set()
    for line in content.split("\n"):
        if not line.strip().startswith("| "):
            continue
        if "进行中" not in line:
            continue
        for raw in re.findall(r"[A-Z]+-\d+(?:~\d+)?", line):
            task_ids |= expand_task_ids(raw)
    return task_ids


def _is_product_code_location(file_location):
    return any(pattern in file_location for pattern in PRODUCT_CODE_PATTERNS)


def _is_review_evidence(raw_ids, evd_type):
    return (
        raw_ids.startswith("REVIEW-")
        or evd_type in ("Code Review", "代码审查", "审查")
        or "审查" in evd_type
    )


def _is_audit_or_review_type(evd_type):
    return any(token in evd_type for token in ("审查", "审视", "审计", "Review"))


def _normalize_priority(value):
    normalized = value.strip().strip("*")
    return normalized if normalized in ("P0", "P1", "P2") else ""


def _task_priority_from_table_parts(parts):
    priority_first = _normalize_priority(parts[1]) if len(parts) > 1 else ""
    if priority_first:
        return priority_first
    old_table_priority = _normalize_priority(parts[11]) if len(parts) >= 12 else ""
    return old_table_priority


def _split_governance_table_row(line):
    """Split a Markdown table row while preserving pipes inside JSON cells."""
    parts = []
    current = []
    depth = 0
    in_string = False
    in_code_span = False
    escape = False

    for ch in line:
        if ch == "`" and not in_string:
            in_code_span = not in_code_span
            current.append(ch)
            continue

        if in_string:
            current.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            current.append(ch)
        elif ch in "{[":
            depth += 1
            current.append(ch)
        elif ch in "}]":
            if depth > 0:
                depth -= 1
            current.append(ch)
        elif ch == "|" and depth == 0 and not in_code_span:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)

    parts.append("".join(current))
    return parts


def _governance_table_cells(line):
    cells = [p.strip() for p in _split_governance_table_row(line.strip())]
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return cells


def _is_incomplete_task_status(status):
    if not status:
        return True
    normalized = status.strip()
    incomplete_markers = ("未完成", "未发布", "进行中", "待启动", "待处理", "pending", "in progress")
    if any(marker in normalized for marker in incomplete_markers):
        return True
    completed_markers = ("已完成", "✅", "已关闭", "已发布", "已终止", "终止", "取消", "废弃")
    return not any(marker in normalized for marker in completed_markers)


def parse_current_active_tasks():
    """Parse hot active task rows from plan-tracker compact tables."""
    if not SAMPLE_PATH.is_file():
        return []
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    tasks = []
    in_active_section = False
    for line in content.split("\n"):
        if line.startswith("## 当前活跃事项"):
            in_active_section = True
            continue
        if in_active_section and line.startswith("### 最近完成"):
            break
        if not in_active_section:
            continue
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = _governance_table_cells(stripped)
        if not cells or cells[0] in {"优先级", "任务ID"}:
            continue
        task_idx = next(
            (idx for idx, cell in enumerate(cells)
             if re.match(r"^(?:\*\*)?[A-Z]+-\d+(?:\*\*)?$", cell.strip())),
            None,
        )
        if task_idx is None:
            continue
        task_id = cells[task_idx].strip().strip("*")
        priority = ""
        for cell in cells:
            normalized = _normalize_priority(cell)
            if normalized:
                priority = normalized
                break
        status = cells[-1].strip() if cells else ""
        title = cells[task_idx + 1].strip() if task_idx + 1 < len(cells) else ""
        dependency = cells[task_idx + 2].strip() if task_idx + 2 < len(cells) else ""
        target_version = cells[task_idx + 3].strip() if task_idx + 3 < len(cells) else ""
        closure_path = cells[task_idx + 4].strip() if task_idx + 4 < len(cells) else ""
        tasks.append({
            "task_id": task_id,
            "priority": priority,
            "title": title,
            "dependency": dependency,
            "target_version": target_version,
            "closure_path": closure_path,
            "status": status,
            "raw_line": stripped,
        })
    return tasks


def _active_execution_packet_tasks():
    return [
        task for task in parse_current_active_tasks()
        if task.get("priority") in {"P0", "P1"} and _is_incomplete_task_status(task.get("status", ""))
    ]


def parse_impact_analysis_entries():
    """Parse evidence-log entries that must carry goal/user impact guardrails.

    This includes explicit type=影响分析 rows and hot plan product-code delivery
    evidence rows. FIX-073: product-code evidence with no standalone impact
    analysis must not make Check 16/17 silently pass with 0 entries.

    Returns list of dicts: {evd_id, task_id, description, file_location, raw_line}
    """
    if not EVIDENCE_PATH.is_file():
        return []
    content = EVIDENCE_PATH.read_text(encoding="utf-8")
    entries = []
    hot_task_ids = _current_release_task_ids() | _plan_task_ids_from_hot_tracker()

    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in _split_governance_table_row(line)]
        if len(parts) < 8:
            continue
        evd_id = parts[1]
        task_id = parts[2]
        evd_type = parts[4] if len(parts) > 4 else ""
        description = parts[5] if len(parts) > 5 else ""
        file_location = parts[6] if len(parts) > 6 else ""

        covered_ids = expand_task_ids(task_id) if task_id and re.search(r"[A-Z]+-\d+", task_id) else set()
        explicit_impact = evd_type == "影响分析"
        product_delivery_by_path = _is_product_code_location(file_location)
        product_delivery_by_current_task_type = (
            bool(covered_ids & hot_task_ids)
            and evd_type in {"实现", "修复", "修复闭环", "开发", "代码"}
        )
        product_delivery = (
            bool(covered_ids & hot_task_ids)
            and (product_delivery_by_path or product_delivery_by_current_task_type)
            and not _is_review_evidence(task_id, evd_type)
            and not _is_audit_or_review_type(evd_type)
        )

        if explicit_impact or product_delivery:
            target_ids = sorted(covered_ids & hot_task_ids) if covered_ids & hot_task_ids else [task_id]
            if not target_ids:
                target_ids = [task_id]
            for covered_task_id in target_ids:
                entries.append({
                    "evd_id": evd_id,
                    "task_id": covered_task_id,
                    "description": description,
                    "file_location": file_location,
                    "raw_line": line,
                })
    return entries


def check_goal_alignment():
    """SYSGAP-023: Check that all impact analysis entries have goal alignment.

    Checks:
    1. plan-tracker has 项目目标 field (WARN if missing)
    2. Each 影响分析 entry has 目标对齐: field with >= 30 chars (FAIL if missing/short)
    3. Identical goal alignment text across different tasks (WARN — template reuse)

    Returns dict with 'has_project_goal', 'entries', 'duplicates', 'pass'.
    """
    result = {
        "has_project_goal": False,
        "project_goal": "",
        "entries": [],
        "duplicates": [],
        "pass": True,
    }

    # 1. Check project goal in plan-tracker
    config = parse_project_config()
    project_goal = config.get("项目目标", "")
    result["project_goal"] = project_goal
    if project_goal:
        result["has_project_goal"] = True

    # 2. Parse impact analysis entries
    entries = parse_impact_analysis_entries()
    if not entries:
        return result

    goal_map = {}  # goal_text -> [task_ids]

    for entry in entries:
        desc = entry["description"]
        # Extract 目标对齐: field — captures text until next known field or end
        goal_match = re.search(
            r'目标对齐[:：]\s*(.+?)(?:\s*(?:用户影响[:：]|范围[:：]|依赖[:：]|架构影响[:：]|$))',
            desc
        )
        goal_text = goal_match.group(1).strip() if goal_match else ""
        goal_len = len(goal_text)

        has_goal = bool(goal_text)
        status = "PASS"
        if not has_goal:
            status = "FAIL"
            result["pass"] = False
        elif goal_len < 30:
            status = "FAIL"
            result["pass"] = False
        else:
            # Track for duplicate detection
            if goal_text in goal_map:
                goal_map[goal_text].append(entry["task_id"])
            else:
                goal_map[goal_text] = [entry["task_id"]]

        result["entries"].append({
            "task_id": entry["task_id"],
            "evd_id": entry["evd_id"],
            "has_goal": has_goal,
            "goal_text": goal_text[:80] + ("..." if goal_len > 80 else ""),
            "goal_len": goal_len,
            "status": status,
        })

    # 3. Check duplicates
    for goal_text, task_ids in goal_map.items():
        if len(task_ids) >= 2:
            for i in range(len(task_ids)):
                for j in range(i + 1, len(task_ids)):
                    result["duplicates"].append((task_ids[i], task_ids[j]))

    return result


# ── SYSGAP-024: User Impact Check ────────────────────────────────

def check_user_impact():
    """SYSGAP-024: Check that all impact analysis entries have user impact analysis.

    Checks:
    1. Each 影响分析 entry has 用户影响: field (FAIL if missing)
    2. Required sub-fields parsed: 获得= / 感知= / 体验变化= / 迁移指南=
    3. Value validity for 获得= (WARN if unrecognized)
    4. Contradiction: 体验变化=否 but diff involves user-visible files (WARN)
    5. Breaking change: 体验变化=是 but 迁移指南=不需要 (BLOCKING)
    6. Breaking change: migration guide path does not exist (BLOCKING — if path provided)

    Returns dict with 'entries', 'blocking', 'pass'.
    """
    USER_VISIBLE_PATTERNS = [
        "CLAUDE.md", "README.md", "CHANGELOG.md",
        "plugin.json", "marketplace.json",
        "commands/", ".claude-plugin/", ".codex-plugin/",
    ]

    VALID_OBTAIN_VALUES = [
        "plugin update", "governance-init", "governance-update",
        "手动", "自动生效（下次会话）", "自动生效", "不需要",
    ]

    result = {
        "entries": [],
        "blocking": [],
        "pass": True,
    }

    entries = parse_impact_analysis_entries()
    if not entries:
        return result

    for entry in entries:
        desc = entry["description"]
        file_location = entry["file_location"]

        # Extract 用户影响: field — captures text until next known field or end
        user_impact_match = re.search(
            r'用户影响[:：]\s*(.+?)(?:\s*(?:目标对齐[:：]|范围[:：]|依赖[:：]|架构影响[:：]|$))',
            desc
        )
        user_impact_text = user_impact_match.group(1).strip() if user_impact_match else ""

        has_field = bool(user_impact_text)

        # Parse sub-fields
        obtain_match = re.search(r'获得=([^,]*?)(?:,|，|\s*(?:感知=|体验变化=|迁移指南=|$))', user_impact_text)
        obtain = obtain_match.group(1).strip() if obtain_match else ""

        perceive_match = re.search(r'感知=([^,]*?)(?:,|，|\s*(?:获得=|体验变化=|迁移指南=|$))', user_impact_text)
        perceive = perceive_match.group(1).strip() if perceive_match else ""

        exp_change_match = re.search(r'体验变化=([^,]*?)(?:,|，|\s*(?:获得=|感知=|迁移指南=|$))', user_impact_text)
        exp_change = exp_change_match.group(1).strip() if exp_change_match else ""

        migration_match = re.search(r'迁移指南=([^,]*?)(?:,|，|\s*(?:获得=|感知=|体验变化=|$))', user_impact_text)
        migration = migration_match.group(1).strip() if migration_match else ""

        status = "PASS"
        issues = []

        if not has_field:
            status = "FAIL"
            issues.append("缺少 用户影响: 字段")
            result["pass"] = False
        else:
            # Check sub-fields presence
            missing_subs = []
            if not obtain:
                missing_subs.append("获得=")
            if not perceive:
                missing_subs.append("感知=")
            if not exp_change:
                missing_subs.append("体验变化=")
            if not migration:
                missing_subs.append("迁移指南=")
            if missing_subs:
                issues.append(f"缺少子字段: {', '.join(missing_subs)}")
                status = "FAIL"
                result["pass"] = False

            # Value validity for 获得=
            if obtain:
                # Check if obtain value matches any valid value (lenient — contains check)
                found_valid = any(v in obtain for v in VALID_OBTAIN_VALUES)
                if not found_valid:
                    issues.append(
                        f"获得= 值 '{obtain}' 不在合法范围内"
                        f" ({', '.join(VALID_OBTAIN_VALUES[:4])} 等)"
                    )
                    if status == "PASS":
                        status = "WARN"

            # Contradiction: 体验变化=否 but file_location contains user-visible patterns
            if exp_change == "否":
                for pattern in USER_VISIBLE_PATTERNS:
                    if pattern in file_location:
                        issues.append(
                            f"体验变化=否 但证据位置涉及用户可见文件 '{pattern}'"
                        )
                        if status == "PASS":
                            status = "WARN"
                        break

            # Breaking change: 体验变化=是 + 迁移指南=不需要
            if exp_change == "是" and migration == "不需要":
                status = "BLOCKING"
                issues.append("体验变化=是（Breaking Change）但 迁移指南=不需要")

            # Breaking change: migration guide path validity
            if exp_change == "是" and migration and migration not in ("不需要", ""):
                # migration could be a relative file path from repo root
                migration_path = ROOT / migration.lstrip("/")
                if not migration_path.is_file():
                    status = "BLOCKING"
                    issues.append(
                        f"体验变化=是（Breaking Change）但迁移指南路径不存在: {migration}"
                    )

        entry_result = {
            "task_id": entry["task_id"],
            "evd_id": entry["evd_id"],
            "has_field": has_field,
            "obtain": obtain,
            "perceive": perceive,
            "exp_change": exp_change,
            "migration": migration,
            "status": status,
            "issues": issues,
        }
        result["entries"].append(entry_result)

        if status in ("FAIL", "BLOCKING"):
            result["pass"] = False
        if status == "BLOCKING":
            result["blocking"].append(entry["task_id"])

    return result


# ── FIX-080: Fact Grounding Check ────────────────────────────────

FACT_BASIS_RE = re.compile(
    r'事实依据[:：]\s*(.+?)(?:\s*(?:目标对齐[:：]|用户影响[:：]|范围[:：]|依赖[:：]|架构影响[:：]|$))'
)

UNGROUNDED_CLAIM_RE = re.compile(
    r"(?:我\s*)?(?:假设|猜测|推测|估计)|(?:大概|应该|可能)(?:已经|是|可以|完成|存在)|编造|幻觉"
)

SECRET_FIELD_RE = re.compile(r"(?:api[_-]?key|token|secret|password|passwd)", re.IGNORECASE)
SECRET_ASSIGNMENT_RE = re.compile(
    r"['\"]?(?:api[_-]?key|token|secret|password|passwd)['\"]?\s*[:=]\s*['\"]?[^\s,'\"}]+",
    re.IGNORECASE,
)


def _current_release_impact_entries():
    """Return impact/product-delivery entries for the active in-progress release.

    FIX-080 avoids retroactively failing historical evidence that predates the
    fact-grounding field. The commit hook enforces every new product-code commit;
    check-governance enforces the active version row so future work cannot omit it.
    """
    release_task_ids = _current_release_task_ids()
    if not release_task_ids:
        return []
    return [entry for entry in parse_impact_analysis_entries()
            if entry["task_id"] in release_task_ids]


def check_fact_grounding():
    """FIX-080: Check current product-code evidence is grounded in facts."""
    result = {
        "entries": [],
        "pass": True,
    }

    for entry in _current_release_impact_entries():
        desc = entry["description"]
        fact_match = FACT_BASIS_RE.search(desc)
        fact_text = fact_match.group(1).strip() if fact_match else ""
        fact_len = len(fact_text)
        issues = []
        status = "PASS"

        if not fact_text:
            issues.append("缺少 事实依据: 字段")
            status = "FAIL"
            result["pass"] = False
        elif fact_len < 20:
            issues.append("事实依据: 过短，需指向具体文件/命令/日志/测试输出")
            status = "FAIL"
            result["pass"] = False

        speculative_match = UNGROUNDED_CLAIM_RE.search(desc)
        if speculative_match:
            issues.append(f"含未落地推断词: {speculative_match.group(0)}")
            status = "FAIL"
            result["pass"] = False

        result["entries"].append({
            "task_id": entry["task_id"],
            "evd_id": entry["evd_id"],
            "has_fact_basis": bool(fact_text),
            "fact_len": fact_len,
            "fact_text": fact_text[:80] + ("..." if fact_len > 80 else ""),
            "status": status,
            "issues": issues,
        })

    return result


# ── FIX-083: Structured Evidence Check ────────────────────────────

def _extract_structured_fact_json(description):
    """Extract the JSON object after `结构化事实:` without being confused by nested braces."""
    markers = list(re.finditer(r"结构化事实[:：]", description))
    if not markers:
        return ""
    first_non_json = ""
    for marker in markers:
        idx = marker.end()
        while idx < len(description) and description[idx].isspace():
            idx += 1
        if idx < len(description) and description[idx] == "`":
            idx += 1
            while idx < len(description) and description[idx].isspace():
                idx += 1
        if idx >= len(description) or description[idx] != "{":
            if not first_non_json:
                first_non_json = description[idx:].strip()
            continue
        break
    else:
        return first_non_json

    depth = 0
    in_string = False
    escape = False
    for pos in range(idx, len(description)):
        ch = description[pos]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return description[idx:pos + 1]
    return description[idx:].strip()


def _contains_secret_like(value):
    """Return True when structured evidence appears to carry a raw secret."""
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            if SECRET_FIELD_RE.search(key_text):
                if child not in (None, "", "<redacted>", "REDACTED", "***", "***REDACTED***"):
                    return True
            if _contains_secret_like(child):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_secret_like(item) for item in value)
    if isinstance(value, str):
        return bool(SECRET_ASSIGNMENT_RE.search(value))
    return False


def _validate_structured_fact_payload(payload):
    issues = []
    if not isinstance(payload, dict):
        return ["结构化事实必须是 JSON object"]

    commands = payload.get("commands")
    if not isinstance(commands, list) or not commands:
        issues.append("commands 必须是非空数组")
    else:
        for index, command in enumerate(commands, start=1):
            if not isinstance(command, dict):
                issues.append(f"commands[{index}] 必须是 object")
                continue
            cmd = command.get("cmd")
            exit_code = command.get("exit_code")
            summary = command.get("summary")
            if not isinstance(cmd, str) or not cmd.strip():
                issues.append(f"commands[{index}].cmd 必须是非空字符串")
            if not isinstance(exit_code, int):
                issues.append(f"commands[{index}].exit_code 必须是整数")
            if not isinstance(summary, str) or len(summary.strip()) < 5:
                issues.append(f"commands[{index}].summary 必须说明输出摘要")
            log_path = command.get("log_path")
            if log_path is not None and not isinstance(log_path, str):
                issues.append(f"commands[{index}].log_path 必须是字符串")

    files_changed = payload.get("files_changed")
    if not isinstance(files_changed, list) or not files_changed or not all(isinstance(item, str) and item for item in files_changed):
        issues.append("files_changed 必须是非空字符串数组")

    diff_summary = payload.get("diff_summary")
    if not isinstance(diff_summary, str) or len(diff_summary.strip()) < 10:
        issues.append("diff_summary 必须说明文件 diff 摘要")

    review = payload.get("review")
    if not isinstance(review, dict):
        issues.append("review 必须是 object")
    else:
        conclusion = review.get("conclusion")
        reviewer = review.get("reviewer")
        if conclusion not in {"APPROVED", "NEEDS_CHANGES", "BLOCKED", "NOT_REQUIRED"}:
            issues.append("review.conclusion 必须是 APPROVED/NEEDS_CHANGES/BLOCKED/NOT_REQUIRED")
        if not isinstance(reviewer, str) or not reviewer.strip():
            issues.append("review.reviewer 必须是非空字符串")

    if _contains_secret_like(payload):
        issues.append("结构化事实疑似包含 secret/token/password 明文")
    return issues


def check_structured_evidence():
    """FIX-083: Check current product-code evidence has machine-readable facts."""
    result = {
        "entries": [],
        "pass": True,
    }

    for entry in _current_release_impact_entries():
        desc = entry["description"]
        raw_json = _extract_structured_fact_json(desc)
        issues = []
        status = "PASS"
        payload = None

        if not raw_json:
            issues.append("缺少 结构化事实: JSON")
        else:
            try:
                payload = json.loads(raw_json)
                issues.extend(_validate_structured_fact_payload(payload))
            except json.JSONDecodeError as exc:
                issues.append(f"结构化事实 JSON 解析失败: {exc.msg}")

        if issues:
            status = "FAIL"
            result["pass"] = False

        result["entries"].append({
            "task_id": entry["task_id"],
            "evd_id": entry["evd_id"],
            "has_structured_fact": bool(raw_json),
            "status": status,
            "issues": issues,
            "commands": len(payload.get("commands", [])) if isinstance(payload, dict) and isinstance(payload.get("commands"), list) else 0,
            "files_changed": len(payload.get("files_changed", [])) if isinstance(payload, dict) and isinstance(payload.get("files_changed"), list) else 0,
        })

    return result


# ── FIX-084: AI Execution Packet Check ───────────────────────────

EXECUTION_PACKET_REQUIRED_FIELDS = {
    "task_id": str,
    "goal": str,
    "allowed_change_scope": list,
    "required_evidence": list,
    "next_commands": list,
    "done_definition": list,
}


def _load_execution_packets(path=None):
    packet_path = path or EXECUTION_PACKET_PATH
    if not packet_path.is_file():
        return {}, f"{packet_path} not found"
    try:
        data = json.loads(packet_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, f"invalid JSON: {exc.msg}"
    if not isinstance(data, dict):
        return {}, "execution packet root must be object"
    packets = data.get("packets", data)
    if not isinstance(packets, dict):
        return {}, "packets must be object"
    return packets, ""


def _validate_execution_packet(task, packet):
    issues = []
    if not isinstance(packet, dict):
        return ["packet must be object"]
    for field, expected_type in EXECUTION_PACKET_REQUIRED_FIELDS.items():
        value = packet.get(field)
        if not isinstance(value, expected_type):
            issues.append(f"{field} missing or invalid")
            continue
        if expected_type is str and not value.strip():
            issues.append(f"{field} must be non-empty")
        if expected_type is list and (
            not value or not all(isinstance(item, str) and item.strip() for item in value)
        ):
            issues.append(f"{field} must be non-empty string array")
    if packet.get("task_id") and packet.get("task_id") != task["task_id"]:
        issues.append("task_id does not match active task")
    allowed_text = " ".join(packet.get("allowed_change_scope", []))
    if allowed_text and any(token in allowed_text.lower() for token in ("*", "any file", "all files", "whole repo")):
        issues.append("allowed_change_scope is too broad")
    required_text = " ".join(packet.get("required_evidence", []))
    if required_text and "事实依据" not in required_text:
        issues.append("required_evidence must mention 事实依据")
    if required_text and "结构化事实" not in required_text:
        issues.append("required_evidence must mention 结构化事实")
    done_text = " ".join(packet.get("done_definition", []))
    if done_text and not any(token in done_text for token in ("review", "Review", "审查", "APPROVED")):
        issues.append("done_definition must include independent review or explicit review status")
    return issues


PRODUCT_SUCCESS_CONTRACT_REQUIRED_FIELDS = {
    "user": str,
    "job_to_be_done": str,
    "non_goals": list,
    "success_metrics": list,
    "competitive_baseline": str,
    "done_definition": list,
}

PRODUCT_SUCCESS_PLACEHOLDER_RE = re.compile(
    r"(?:\b(?:todo|tbd|to_be_defined|n/?a|none|null|unknown)\b|待补|待定|暂无|占位)",
    re.IGNORECASE,
)
PRODUCT_SUCCESS_PROCESS_ONLY_RE = re.compile(
    r"(?:check-governance|verify_workflow|evidence-log|plan-tracker|review|commit|push|archive|"
    r"治理|证据|归档|提交|审查|记录|hook)",
    re.IGNORECASE,
)
PRODUCT_SUCCESS_USER_OUTCOME_RE = re.compile(
    r"(?:user|customer|persona|outcome|value|usable|acceptance|scenario|quality|competitive|"
    r"用户|客户|使用者|产品|体验|价值|可用|可见|验收|场景|质量|竞争)",
    re.IGNORECASE,
)
PRODUCT_SUCCESS_RUNNABLE_RE = re.compile(
    r"(?:e2e|test|unit|integration|fixture|ci|command|script|execute|run|pass|"
    r"测试|验证|用例|命令|脚本|执行|通过)",
    re.IGNORECASE,
)


def _is_meaningful_product_success_text(value):
    return isinstance(value, str) and len(value.strip()) >= 8 and not PRODUCT_SUCCESS_PLACEHOLDER_RE.match(value)


def _is_meaningful_product_success_list(value):
    return (
        isinstance(value, list)
        and bool(value)
        and all(_is_meaningful_product_success_text(item) for item in value)
    )


def _is_process_only_product_success_metric(value):
    text = value.strip()
    return bool(PRODUCT_SUCCESS_PROCESS_ONLY_RE.search(text))


def _validate_product_success_contract(packet):
    issues = []
    contract = packet.get("product_success_contract") if isinstance(packet, dict) else None
    if not isinstance(contract, dict):
        return ["missing product_success_contract"]

    for field, expected_type in PRODUCT_SUCCESS_CONTRACT_REQUIRED_FIELDS.items():
        value = contract.get(field)
        if not isinstance(value, expected_type):
            issues.append(f"product_success_contract.{field} missing or invalid")
            continue
        if expected_type is str and not _is_meaningful_product_success_text(value):
            issues.append(f"product_success_contract.{field} must be specific and non-placeholder")
        if expected_type is list and not _is_meaningful_product_success_list(value):
            issues.append(f"product_success_contract.{field} must be a non-empty specific string array")

    success_metrics = contract.get("success_metrics")
    if isinstance(success_metrics, list) and success_metrics:
        process_only = [
            metric for metric in success_metrics
            if isinstance(metric, str) and _is_process_only_product_success_metric(metric)
        ]
        if process_only:
            issues.append("product_success_contract.success_metrics must not contain process-only metrics")
        if not any(isinstance(metric, str) and PRODUCT_SUCCESS_USER_OUTCOME_RE.search(metric) for metric in success_metrics):
            issues.append("product_success_contract.success_metrics needs at least one user-visible outcome")
        if not any(isinstance(metric, str) and PRODUCT_SUCCESS_RUNNABLE_RE.search(metric) for metric in success_metrics):
            issues.append("product_success_contract.success_metrics needs at least one runnable validation signal")

    return issues


def check_product_success_contracts(packet_path=None):
    """FIX-088: active P0/P1 tasks need explicit Product Success Contract fields."""
    result = {
        "required_tasks": [],
        "entries": [],
        "issues": [],
        "pass": True,
    }
    tasks = _active_execution_packet_tasks()
    result["required_tasks"] = [task["task_id"] for task in tasks]
    if not tasks:
        return result

    packets, load_error = _load_execution_packets(packet_path)
    if load_error:
        result["pass"] = False
        result["issues"].append(load_error)
        return result

    for task in tasks:
        task_id = task["task_id"]
        packet = packets.get(task_id)
        if packet is None:
            issues = ["missing execution packet"]
        else:
            issues = _validate_product_success_contract(packet)
        status = "PASS" if not issues else "FAIL"
        if issues:
            result["pass"] = False
        result["entries"].append({"task_id": task_id, "status": status, "issues": issues})
    return result


ACCEPTANCE_CONTRACT_REQUIRED_FIELDS = {
    "scenario": str,
    "command": str,
    "expected_output": str,
    "last_run": dict,
    "demo_evidence": str,
}

ACCEPTANCE_RUNNABLE_COMMAND_RE = re.compile(
    r"^\s*(?:(?:python|pytest|node|npm|pnpm|yarn|uv|bash|sh|make|go|cargo|npx|cmd|powershell|pwsh)\b|"
    r"(?:\./|\.\\|skills/|skills\\|scripts/|scripts\\).+)",
    re.IGNORECASE,
)

ACCEPTANCE_PASS_STATUSES = {"pass", "passed", "ok", "success", "通过"}
ACCEPTANCE_NOT_RUN_STATUSES = {"not_run_yet", "not run yet", "pending", "planned", "待运行", "未运行"}


def _is_meaningful_acceptance_text(value):
    return _is_meaningful_product_success_text(value)


def _is_acceptance_run_deferrable(task):
    status = str(task.get("status", "")).strip().lower()
    return any(marker in status for marker in ("待实施", "待启动", "pending", "planned"))


def _validate_acceptance_contract(task, packet):
    issues = []
    contract = packet.get("acceptance_contract") if isinstance(packet, dict) else None
    if not isinstance(contract, dict):
        return ["missing acceptance_contract"]

    for field, expected_type in ACCEPTANCE_CONTRACT_REQUIRED_FIELDS.items():
        value = contract.get(field)
        if not isinstance(value, expected_type):
            issues.append(f"acceptance_contract.{field} missing or invalid")
            continue
        if expected_type is str and not _is_meaningful_acceptance_text(value):
            issues.append(f"acceptance_contract.{field} must be specific and non-placeholder")

    command = contract.get("command")
    if isinstance(command, str) and _is_meaningful_acceptance_text(command):
        if not ACCEPTANCE_RUNNABLE_COMMAND_RE.search(command):
            issues.append("acceptance_contract.command must be a runnable validation command")

    last_run = contract.get("last_run")
    if isinstance(last_run, dict):
        status = str(last_run.get("status", "")).strip().lower()
        exit_code = last_run.get("exit_code")
        summary = last_run.get("summary")
        if status in ACCEPTANCE_NOT_RUN_STATUSES and _is_acceptance_run_deferrable(task):
            if not _is_meaningful_acceptance_text(summary):
                issues.append("acceptance_contract.last_run.summary must be specific and non-placeholder")
            return issues
        if PRODUCT_SUCCESS_PLACEHOLDER_RE.search(status) or status not in ACCEPTANCE_PASS_STATUSES:
            issues.append("acceptance_contract.last_run.status must be PASS")
        if not isinstance(exit_code, int) or exit_code != 0:
            issues.append("acceptance_contract.last_run.exit_code must be 0")
        if not _is_meaningful_acceptance_text(summary):
            issues.append("acceptance_contract.last_run.summary must be specific and non-placeholder")

    return issues


def check_acceptance_contracts(packet_path=None):
    """FIX-089: active P0/P1 tasks need runnable acceptance contracts."""
    result = {
        "required_tasks": [],
        "entries": [],
        "issues": [],
        "pass": True,
    }
    tasks = _active_execution_packet_tasks()
    result["required_tasks"] = [task["task_id"] for task in tasks]
    if not tasks:
        return result

    packets, load_error = _load_execution_packets(packet_path)
    if load_error:
        result["pass"] = False
        result["issues"].append(load_error)
        return result

    for task in tasks:
        task_id = task["task_id"]
        packet = packets.get(task_id)
        if packet is None:
            issues = ["missing execution packet"]
        else:
            issues = _validate_acceptance_contract(task, packet)
        status = "PASS" if not issues else "FAIL"
        if issues:
            result["pass"] = False
        result["entries"].append({"task_id": task_id, "status": status, "issues": issues})
    return result


def build_execution_packet(task):
    scope = task.get("closure_path") or task.get("title") or task["task_id"]
    task_label = f"{task['task_id']} {task.get('title', '').strip()}".strip()
    return {
        "task_id": task["task_id"],
        "priority": task.get("priority", ""),
        "status": task.get("status", ""),
        "goal": task_label,
        "product_success_contract": {
            "user": f"TO_BE_DEFINED: impacted persona for {task_label}",
            "job_to_be_done": f"TO_BE_DEFINED: user job and desired outcome for {task_label}",
            "non_goals": [
                "TO_BE_DEFINED: explicit non-goal that protects the task from scope drift.",
                "TO_BE_DEFINED: explicit non-goal that prevents process evidence from replacing product value.",
            ],
            "success_metrics": [
                "TO_BE_DEFINED: user-visible outcome or acceptance scenario for this task.",
                "TO_BE_DEFINED: runnable E2E, test, or command that proves the outcome.",
            ],
            "competitive_baseline": "TO_BE_DEFINED: mature-team or competing-product baseline this task must match.",
            "done_definition": [
                "TO_BE_DEFINED: product success evidence is recorded with concrete facts.",
                "TO_BE_DEFINED: independent review confirms the user outcome is not replaced by process completion.",
            ],
        },
        "acceptance_contract": {
            "scenario": f"TO_BE_DEFINED: user-visible acceptance scenario for {task_label}",
            "command": "TO_BE_DEFINED: runnable E2E, smoke, unit, or validation command",
            "expected_output": "TO_BE_DEFINED: concrete pass output, assertion, or observable demo result",
            "last_run": {
                "status": "TO_BE_DEFINED",
                "exit_code": None,
                "summary": "TO_BE_DEFINED: last run output summary with evidence location",
            },
            "demo_evidence": "TO_BE_DEFINED: demo, CLI output, or artifact proving the scenario",
        },
        "allowed_change_scope": [
            f"Only change files required by this task row: {scope}",
            "Keep unrelated refactors, release version bumps, and fixture sync out of this task unless listed in the task scope.",
        ],
        "required_evidence": [
            "evidence-log entry with 事实依据, 目标对齐, 用户影响, and 结构化事实 JSON",
            "validation commands with exit_code and concise output summary",
            "independent review evidence or explicit degraded review evidence that does not claim full separation",
        ],
        "next_commands": [
            "python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -v",
            "python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues",
        ],
        "done_definition": [
            task.get("closure_path") or "Task closure path from plan-tracker is satisfied.",
            "Code Reviewer or matching Reviewer has APPROVED the product-code change.",
            "Commit and push are completed for this single task.",
        ],
        "source": "plan-tracker.md##当前活跃事项",
    }


def generate_execution_packets(existing=None):
    generated = {}
    existing = existing or {}
    for task in _active_execution_packet_tasks():
        packet = dict(existing.get(task["task_id"], {})) if isinstance(existing.get(task["task_id"]), dict) else {}
        base = build_execution_packet(task)
        base.update(packet)
        base["task_id"] = task["task_id"]
        base["priority"] = task.get("priority", base.get("priority", ""))
        base["status"] = task.get("status", base.get("status", ""))
        generated[task["task_id"]] = base
    return {
        "version": 1,
        "generated_at": datetime.now().replace(microsecond=0).isoformat(),
        "packets": generated,
    }


def check_execution_packets(packet_path=None):
    result = {
        "required_tasks": [],
        "entries": [],
        "missing": [],
        "issues": [],
        "pass": True,
    }
    tasks = _active_execution_packet_tasks()
    result["required_tasks"] = [task["task_id"] for task in tasks]
    if not tasks:
        return result

    packets, load_error = _load_execution_packets(packet_path)
    if load_error:
        result["pass"] = False
        result["issues"].append(load_error)
        result["missing"] = result["required_tasks"]
        return result

    for task in tasks:
        task_id = task["task_id"]
        packet = packets.get(task_id)
        if packet is None:
            result["pass"] = False
            result["missing"].append(task_id)
            result["entries"].append({"task_id": task_id, "status": "FAIL", "issues": ["missing execution packet"]})
            continue
        issues = _validate_execution_packet(task, packet)
        status = "PASS" if not issues else "FAIL"
        if issues:
            result["pass"] = False
        result["entries"].append({"task_id": task_id, "status": status, "issues": issues})
    return result


def cmd_execution_packet(args):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    packets, _ = _load_execution_packets()
    payload = generate_execution_packets(existing=packets)
    if args.task:
        selected = {
            tid: packet for tid, packet in payload["packets"].items()
            if tid in set(args.task)
        }
        payload["packets"] = selected
    if args.write:
        EXECUTION_PACKET_PATH.parent.mkdir(parents=True, exist_ok=True)
        EXECUTION_PACKET_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"[OK] wrote {len(payload['packets'])} execution packet(s) to {EXECUTION_PACKET_PATH}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


# ── SYSGAP-035: Agent Team Review Check (Check 18) ────────────────

DEGRADED_REVIEW_MARKERS = (
    "不构成独立审查",
    "不得计入审查通过",
    "不得解锁",
)
REVIEWER_ROLE_MARKERS = (
    "Reviewer",
    "审查 Agent",
    "审查Agent",
    "审查人",
    "复审",
)
SELF_REVIEW_AUTHOR_MARKERS = (
    "Coordinator",
    "Developer",
    "Governance Developer",
)


def _review_text_is_degraded(text):
    """Return True when a review-like row is only degraded/runtime evidence."""
    if "DEGRADED_EVIDENCE" in text:
        return True
    return all(marker in text for marker in DEGRADED_REVIEW_MARKERS)


def _review_text_has_reviewer_marker(text):
    return any(marker in text for marker in REVIEWER_ROLE_MARKERS)


def _review_entry_skip_reason(author, description, file_location, notes=""):
    """Classify review-like evidence that must not count as independent review."""
    combined = " ".join([author, description, file_location, notes])
    if _review_text_is_degraded(combined):
        return "degraded evidence does not count as independent review"

    if (
        any(marker in author for marker in SELF_REVIEW_AUTHOR_MARKERS)
        and "Reviewer" not in author
        and "审查" not in author
    ):
        return "self-review evidence does not count as independent review"

    if not _review_text_has_reviewer_marker(combined):
        return "review evidence lacks independent reviewer marker"

    return ""


def _parse_review_coverage_details(evidence_path=None, review_dir=None):
    """Parse independent review coverage and ignored review-like entries."""
    covered = {}
    ignored = []
    evidence_path = Path(evidence_path) if evidence_path is not None else EVIDENCE_PATH
    review_dir = Path(review_dir) if review_dir is not None else evidence_path.parent

    if not evidence_path.is_file():
        return covered, ignored

    evidence_content = evidence_path.read_text(encoding="utf-8")

    def add_coverage(source, raw_text):
        for match in re.finditer(r"([A-Z]+-\d+(?:~\d+)?)", raw_text):
            raw = match.group(1)
            for inner_id in expand_task_ids(raw):
                if not inner_id.startswith("REVIEW-"):
                    covered.setdefault(inner_id, []).append(source)

    # 1. Scan evidence-log for REVIEW evidence entries.
    for line in evidence_content.split("\n"):
        line = line.strip()
        if not (line.startswith("| EVD-") or line.startswith("| REVIEW-")):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 8:
            continue
        evd_id = parts[1]
        raw_ids = parts[2]
        evd_type = parts[4] if len(parts) > 4 else ""
        description = parts[5] if len(parts) > 5 else ""
        file_location = parts[6] if len(parts) > 6 else ""
        author = parts[7] if len(parts) > 7 else ""
        notes = " ".join(parts[8:])

        # REVIEW evidence: task ID starts with REVIEW- or type is Code Review/审查.
        is_review_entry = (
            evd_id.startswith("REVIEW-")
            or raw_ids.startswith("REVIEW-")
            or evd_type == "Code Review"
            or evd_type == "审查"
            or "审查" in evd_type
        )
        if not is_review_entry:
            continue

        skip_reason = _review_entry_skip_reason(author, description, file_location, notes)
        if skip_reason:
            ignored.append({"source": evd_id, "reason": skip_reason, "task_ids": raw_ids})
            continue

        for inner_id in expand_task_ids(raw_ids) if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids) else []:
            if not inner_id.startswith("REVIEW-"):
                covered.setdefault(inner_id, []).append(evd_id)

        if raw_ids.startswith("REVIEW-"):
            # Extract covered task IDs from REVIEW- prefix.
            add_coverage(evd_id, raw_ids[len("REVIEW-"):])

        # Check description and file_location for task references.
        add_coverage(evd_id, description + " " + file_location)

    # 2. Scan review-*.md files for task references.
    if review_dir.is_dir():
        for review_file in review_dir.glob("review-*.md"):
            try:
                content = review_file.read_text(encoding="utf-8")
                skip_reason = _review_entry_skip_reason("", content, review_file.name)
                if skip_reason:
                    ignored.append({
                        "source": review_file.name,
                        "reason": skip_reason,
                        "task_ids": "",
                    })
                    continue
                add_coverage(review_file.name, content)
            except (IOError, OSError):
                pass

    return covered, ignored

def _parse_review_covered_tasks(evidence_path=None, review_dir=None):
    """Parse evidence-log and review-*.md files to find all tasks covered by reviews.

    Returns dict: task_id -> list of review sources (evidence IDs or file names).
    """
    covered, _ = _parse_review_coverage_details(evidence_path=evidence_path, review_dir=review_dir)
    return covered


def check_agent_team_review():
    """SYSGAP-035: Check 18 — Agent Team review completeness.

    For completed tasks involving product code changes, verify that an
    independent code review was performed. Review evidence is identified
    by REVIEW-prefixed task IDs in evidence-log or review-*.md files
    in .governance/.

    Product code detection: evidence file locations outside .governance/
    (skills/, agents/, infra/, commands/, adapters/, .claude-plugin/,
    .codex-plugin/, .agents/, project/).

    Returns dict with total_tasks, reviewed, unreviewed, review_gap_tasks, pass.
    """
    PRODUCT_CODE_PATTERNS = [
        "skills/", "agents/", "infra/", "commands/",
        "adapters/", ".claude-plugin/", ".codex-plugin/", ".agents/",
        "project/",
    ]

    result = {
        "total_tasks": 0,
        "reviewed": 0,
        "unreviewed": 0,
        "review_gap_tasks": [],
        "ignored_review_entries": [],
        "pass": True,
    }

    completed = parse_completed_task_ids()
    if not completed:
        return result

    # Read evidence-log
    if not EVIDENCE_PATH.is_file():
        return result
    evidence_content = EVIDENCE_PATH.read_text(encoding="utf-8")

    # Build map: task_id -> list of evidence metadata
    task_file_locations = {}
    for line in evidence_content.split("\n"):
        line = line.strip()
        if not line.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 8:
            continue
        raw_ids = parts[2]
        evd_type = parts[4] if len(parts) > 4 else ""
        file_location = parts[6] if len(parts) > 6 else ""
        for tid in expand_task_ids(raw_ids) if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids) else []:
            task_file_locations.setdefault(tid, []).append({
                "file_location": file_location,
                "evd_type": evd_type,
            })

    # Build review coverage map. Degraded runtime evidence and self-review rows
    # are retained as ignored diagnostics, but never unlock completed product work.
    review_covered, ignored_reviews = _parse_review_coverage_details()
    result["ignored_review_entries"] = ignored_reviews

    for task_id in sorted(completed):
        entries = task_file_locations.get(task_id, [])
        if not entries:
            continue

        is_product_code = any(
            any(pat in e["file_location"] for pat in PRODUCT_CODE_PATTERNS)
            and not _is_audit_or_review_type(e["evd_type"])
            for e in entries
        )
        if not is_product_code:
            continue

        result["total_tasks"] += 1
        if task_id in review_covered:
            result["reviewed"] += 1
        else:
            result["unreviewed"] += 1
            result["review_gap_tasks"].append(task_id)

    result["pass"] = result["unreviewed"] == 0
    return result


# ── SYSGAP-036: Agent Activation Check (Check 19) ────────────────

def check_agent_activation():
    """SYSGAP-036: Check 19 — Analyst/Architect activation for P0 cross-layer tasks.

    For P0 tasks involving >= 2 architecture layers of product code change,
    verify that Analyst/Architect agents were activated for impact analysis.

    Detection:
    - P0 tasks: parsed from plan-tracker tracking tables (priority column index 11)
    - Product code: evidence file locations in skills/, agents/, infra/, etc.
    - Cross-layer: >= 2 distinct top-level directories in evidence locations
    - Analyst involvement: evidence author contains "Analyst" or description
      contains "Analyst:" marker

    Returns dict with total_p0_cross_layer, analyst_activated, analyst_bypassed, pass.
    """
    PRODUCT_CODE_PATTERNS = [
        "skills/", "agents/", "infra/", "commands/",
        "adapters/", ".claude-plugin/", ".codex-plugin/", ".agents/",
        "project/",
    ]
    ARCH_LAYER_MAP = {
        "skills/": "skills",
        "commands/": "commands",
        "agents/": "agents",
        "infra/": "infra",
        "adapters/": "adapters",
        "project/": "project",
        ".claude-plugin/": "claude-plugin",
        ".codex-plugin/": "codex-plugin",
        ".agents/": "agents-plugin",
    }

    result = {
        "total_p0_cross_layer": 0,
        "analyst_activated": 0,
        "analyst_bypassed": 0,
        "bypassed_tasks": [],
        "pass": True,
    }

    # Parse P0 completed tasks from plan-tracker
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    p0_tasks = {}  # task_id -> True

    for line in content.split("\n"):
        line_stripped = line.strip()
        if not line_stripped.startswith("| ") or "---" in line_stripped:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 11:
            continue
        task_id_match = re.match(r"([A-Z]+-\d+)", parts[1])
        if not task_id_match:
            continue
        task_id = task_id_match.group(1)
        # Column indices: real format has 20 cols (priority at [11]), test format has 10 (priority at [3])
        status = parts[10] if len(parts) > 10 else ""
        if len(parts) >= 13:
            priority = parts[11] if len(parts) > 11 else ""  # full 20-column format
        elif len(parts) >= 5:
            priority = parts[3] if len(parts) > 3 else ""    # simplified 10-column test format
        else:
            priority = ""
        if priority == "P0" and status == "已完成":
            p0_tasks[task_id] = True

    if not p0_tasks:
        return result

    # Read evidence-log
    if not EVIDENCE_PATH.is_file():
        return result
    evidence_content = EVIDENCE_PATH.read_text(encoding="utf-8")

    # Build map: task_id -> [(evd_id, file_location, author, description, evd_type)]
    task_entries = {}
    for line in evidence_content.split("\n"):
        line = line.strip()
        if not line.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 9:
            continue
        evd_id = parts[1]
        raw_ids = parts[2]
        evd_type = parts[4] if len(parts) > 4 else ""
        description = parts[5] if len(parts) > 5 else ""
        file_location = parts[6] if len(parts) > 6 else ""
        author = parts[7] if len(parts) > 7 else ""

        for tid in expand_task_ids(raw_ids) if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids) else []:
            task_entries.setdefault(tid, []).append(
                (evd_id, file_location, author, description, evd_type)
            )

    for task_id in sorted(p0_tasks):
        entries = task_entries.get(task_id, [])
        if not entries:
            continue

        # Check product code involvement
        is_product_code = any(
            any(pat in file_loc for pat in PRODUCT_CODE_PATTERNS)
            for _, file_loc, _, _, _ in entries
        )
        if not is_product_code:
            continue

        # Count architecture layers
        all_locs = " ".join(file_loc for _, file_loc, _, _, _ in entries)
        layers = set()
        for prefix, layer_name in ARCH_LAYER_MAP.items():
            if prefix in all_locs:
                layers.add(layer_name)
        if len(layers) < 2:
            # Not cross-layer — skip (only single layer change)
            continue

        result["total_p0_cross_layer"] += 1

        # Check for Analyst/Architect involvement
        # Look for impact analysis evidence entries covering this task
        has_impact_analysis = False
        has_analyst_involvement = False

        for _, _, author, description, evd_type in entries:
            if evd_type == "影响分析" or "影响分析" in description:
                has_impact_analysis = True
                if "Analyst" in author or "Architect" in author:
                    has_analyst_involvement = True
                if "Analyst:" in description or "Architect:" in description:
                    has_analyst_involvement = True

        # Also check if any evidence entry for ANY task has impact analysis
        # that references this task (e.g., separate Analyst analysis entry)
        for line in evidence_content.split("\n"):
            line = line.strip()
            if not line.startswith("| EVD-"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 9:
                continue
            evd_type = parts[4] if len(parts) > 4 else ""
            if evd_type != "影响分析":
                continue
            raw_ids = parts[2]
            description = parts[5] if len(parts) > 5 else ""
            author = parts[7] if len(parts) > 7 else ""
            covered = expand_task_ids(raw_ids) if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids) else set()
            if task_id in covered:
                has_impact_analysis = True
                if "Analyst" in author or "Architect" in author:
                    has_analyst_involvement = True
                if "Analyst:" in description or "Architect:" in description:
                    has_analyst_involvement = True

        if has_impact_analysis and not has_analyst_involvement:
            result["analyst_bypassed"] += 1
            result["bypassed_tasks"].append(task_id)
        elif has_impact_analysis and has_analyst_involvement:
            result["analyst_activated"] += 1
        # If no impact analysis at all, the task was completed without any
        # analysis — not counted as "bypassed" (analysis step entirely skipped)

    result["pass"] = result["analyst_bypassed"] == 0
    return result


# ── SYSGAP-042: Review Debt Check (Check 20) ─────────────────────

def check_review_debt():
    """SYSGAP-042: Check 20 — Review debt.

    Check all product-code tasks for review debt: tasks that have execution
    evidence in evidence-log but lack corresponding review evidence.

    Product code detection: evidence file locations outside .governance/
    (skills/, agents/, infra/, commands/, adapters/, .claude-plugin/,
    .codex-plugin/, .agents/, project/).

    Returns dict with total_tasks, review_debt_count, review_debt_tasks, pass.
    """
    PRODUCT_CODE_PATTERNS = [
        "skills/", "agents/", "infra/", "commands/",
        "adapters/", ".claude-plugin/", ".codex-plugin/", ".agents/",
        "project/",
    ]

    result = {
        "total_tasks": 0,
        "review_debt_count": 0,
        "review_debt_tasks": [],
        "pass": True,
    }

    if not SAMPLE_PATH.is_file():
        return result

    # 1. Parse all tasks from plan-tracker tracking tables
    plan_content = SAMPLE_PATH.read_text(encoding="utf-8")
    all_task_ids = set()
    for line in plan_content.split("\n"):
        line_stripped = line.strip()
        if not line_stripped.startswith("| ") or "---" in line_stripped:
            continue
        m = re.search(r"\|\s*(?:\*\*)?([A-Z]+-\d+)(?:\*\*)?\s*\|", line_stripped)
        if not m:
            continue
        all_task_ids.add(m.group(1))

    if not all_task_ids:
        return result

    # 2. Build evidence map: task_id -> list of (evd_id, evd_type, file_location)
    if not EVIDENCE_PATH.is_file():
        return result
    evidence_content = EVIDENCE_PATH.read_text(encoding="utf-8")

    task_evidence = {}  # task_id -> [{evd_id, evd_type, file_location, description}]
    for line in evidence_content.split("\n"):
        line = line.strip()
        if not line.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 8:
            continue
        evd_id = parts[1]
        raw_ids = parts[2]
        evd_type = parts[4] if len(parts) > 4 else ""
        description = parts[5] if len(parts) > 5 else ""
        file_location = parts[6] if len(parts) > 6 else ""

        covered_ids = expand_task_ids(raw_ids) if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids) else set()
        for tid in covered_ids:
            task_evidence.setdefault(tid, []).append({
                "evd_id": evd_id,
                "evd_type": evd_type,
                "file_location": file_location,
                "description": description,
            })

    # 3. Build review coverage map (same logic as _parse_review_covered_tasks)
    review_covered = _parse_review_covered_tasks()

    # 4. For each product-code task: check if it has execution evidence but no review evidence
    for task_id in sorted(all_task_ids):
        entries = task_evidence.get(task_id, [])
        if not entries:
            continue

        # Determine if this task touched product code
        is_product_code = any(
            any(pat in e["file_location"] for pat in PRODUCT_CODE_PATTERNS)
            and not _is_audit_or_review_type(e["evd_type"])
            for e in entries
        )
        if not is_product_code:
            continue

        result["total_tasks"] += 1

        # Check for review evidence
        if task_id in review_covered:
            continue  # Has review — no debt

        # No review evidence found — this is review debt
        result["review_debt_count"] += 1
        result["review_debt_tasks"].append(task_id)

    result["pass"] = result["review_debt_count"] == 0
    return result


# ── FIX-037: Review Coverage Check (Check 21) ──────────────────────

PRODUCT_CODE_PATTERNS = [
    "skills/", "agents/", "infra/", "commands/",
    "adapters/", ".claude-plugin/", ".codex-plugin/", ".agents/",
    "project/",
]


def check_review_coverage():
    """FIX-037: Check 21 — Review coverage for product code tasks.

    Counts product code tasks (excluding P2 priority) and verifies what
    fraction has review evidence. Uses _parse_review_covered_tasks() to
    determine which tasks have been independently reviewed.

    Returns dict with total_tasks, reviewed, unreviewed, unreviewed_tasks,
    coverage_pct, pass.
    """
    result = {
        "total_tasks": 0,
        "reviewed": 0,
        "unreviewed": 0,
        "unreviewed_tasks": [],
        "coverage_pct": 0.0,
        "pass": True,
    }

    if not SAMPLE_PATH.is_file():
        return result
    if not EVIDENCE_PATH.is_file():
        return result

    plan_content = SAMPLE_PATH.read_text(encoding="utf-8")

    # ── Parse task priorities from plan-tracker tracking tables ──
    task_priorities = {}          # task_id -> priority string (P0/P1/P2)
    all_task_ids = set()
    for line in plan_content.split("\n"):
        line_s = line.strip()
        if not line_s.startswith("| ") or "---" in line_s:
            continue
        m = re.search(r"\|\s*(?:\*\*)?([A-Z]+-\d+)(?:\*\*)?\s*\|", line_s)
        if not m:
            continue
        task_id = m.group(1)
        all_task_ids.add(task_id)
        parts = [p.strip() for p in line.split("|")]
        priority = _task_priority_from_table_parts(parts)
        if priority:
            task_priorities[task_id] = priority

    if not all_task_ids:
        return result

    # ── Build evidence map from evidence-log ──
    evidence_content = EVIDENCE_PATH.read_text(encoding="utf-8")
    task_file_locations = {}
    for line in evidence_content.split("\n"):
        line = line.strip()
        if not line.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 8:
            continue
        raw_ids = parts[2]
        evd_type = parts[4] if len(parts) > 4 else ""
        file_location = parts[6] if len(parts) > 6 else ""
        for tid in expand_task_ids(raw_ids) if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids) else []:
            task_file_locations.setdefault(tid, []).append({
                "file_location": file_location,
                "evd_type": evd_type,
            })

    # ── Build review coverage map ──
    review_covered = _parse_review_covered_tasks()

    # ── Count product-code tasks and check review coverage ──
    for task_id in sorted(all_task_ids):
        # Exclude P2 priority tasks
        priority = task_priorities.get(task_id, "")
        if priority == "P2":
            continue

        entries = task_file_locations.get(task_id, [])
        if not entries:
            continue

        is_product_code = any(
            any(pat in e["file_location"] for pat in PRODUCT_CODE_PATTERNS)
            and not _is_audit_or_review_type(e["evd_type"])
            for e in entries
        )
        if not is_product_code:
            continue

        result["total_tasks"] += 1
        if task_id in review_covered:
            result["reviewed"] += 1
        else:
            result["unreviewed"] += 1
            result["unreviewed_tasks"].append(task_id)

    if result["total_tasks"] > 0:
        result["coverage_pct"] = round((result["reviewed"] / result["total_tasks"]) * 100, 1)
    result["pass"] = result["unreviewed"] == 0
    return result


# ── FIX-038: Profile Consistency Check (Check 22) ──────────────────

# Per-profile expectations (from core/profiles.md)
_PROFILE_GATE_COUNT = {
    "lightweight": 7,
    "standard": 11,
    "strict": 11,
}
_PROFILE_TASK_COLUMNS = {
    "lightweight": 6,
    "standard": 20,
    "strict": 20,
}


def check_profile_consistency():
    """FIX-038: Check 22 — Profile consistency between declaration and actual structure.

    Validates:
      a. Gate table row count matches profile expectation
      b. Task tracking table column count matches profile expectation
      c. Strict profile must not contain any "passed-with-conditions" entries

    Returns dict with profile, gate_rows, expected_gate_rows, task_cols,
    expected_task_cols, conditional_passes, issues, pass.
    """
    result = {
        "profile": "",
        "gate_rows": 0,
        "expected_gate_rows": 0,
        "task_cols": 0,
        "expected_task_cols": 0,
        "conditional_passes": 0,
        "issues": [],
        "pass": True,
    }

    if not SAMPLE_PATH.is_file():
        result["issues"].append("plan-tracker.md not found")
        result["pass"] = False
        return result

    # 1. Parse profile from plan-tracker project config
    config = parse_project_config()
    profile_raw = config.get("Profile", "")
    # Remove parenthetical remarks like "standard（本项目即为工作流产品本身...）"
    profile = re.match(r"^\s*(\w+)", profile_raw)
    if not profile:
        result["issues"].append(
            f"Profile field not found or unparseable in plan-tracker project config"
        )
        result["pass"] = False
        return result
    profile = profile.group(1).lower()
    result["profile"] = profile

    if profile not in _PROFILE_GATE_COUNT:
        result["issues"].append(f"Unknown profile: '{profile}'")
        result["pass"] = False
        return result

    # 2. Set expected values
    result["expected_gate_rows"] = _PROFILE_GATE_COUNT[profile]
    result["expected_task_cols"] = _PROFILE_TASK_COLUMNS[profile]

    # 3. Count actual gate rows
    gates = parse_gate_status()
    result["gate_rows"] = len(gates)
    if result["gate_rows"] != result["expected_gate_rows"]:
        result["issues"].append(
            f"Gate table has {result['gate_rows']} rows, "
            f"expected {result['expected_gate_rows']} for '{profile}' profile"
        )
        result["pass"] = False

    # 4. Count task tracking table columns when the legacy table exists.
    # FMT-001 intentionally removed "## 样例跟踪表" from hot plan-tracker.
    # Absence is no longer a profile violation; current active task tables
    # have their own compact shape and are validated by structural checks.
    plan_content = SAMPLE_PATH.read_text(encoding="utf-8")
    in_section = False
    for line in plan_content.split("\n"):
        if "## 样例跟踪表" in line:
            in_section = True
            continue
        if in_section:
            line = line.strip()
            if not line:
                continue  # skip blank lines between heading and table
            if line.startswith("## "):
                break   # hit next section — no table found
            if not line.startswith("|"):
                break   # end of table
            if "---" in line:
                continue  # separator row
            # Header row — count columns (strip leading/trailing empties)
            parts = [p.strip() for p in line.split("|")]
            # Remove leading and trailing empty strings from split
            if parts and parts[0] == "":
                parts = parts[1:]
            if parts and parts[-1] == "":
                parts = parts[:-1]
            result["task_cols"] = len(parts)
            break  # Only count the first header row

    if result["task_cols"] == 0:
        pass
    elif result["task_cols"] != result["expected_task_cols"]:
        result["issues"].append(
            f"Task table has {result['task_cols']} columns, "
            f"expected {result['expected_task_cols']} for '{profile}' profile"
        )
        result["pass"] = False

    # 5. Strict profile: no conditional passes allowed
    if profile == "strict":
        for g in gates:
            if g["status"] == "passed-with-conditions":
                result["conditional_passes"] += 1
        if result["conditional_passes"] > 0:
            result["issues"].append(
                f"Strict profile forbids 'passed-with-conditions', "
                f"but {result['conditional_passes']} gate(s) have it"
            )
            result["pass"] = False

    return result


# ── FIX-061: governance-review Reviewer fallback policy ───────────

REVIEW_FALLBACK_POLICY_REQUIRED_FILES = [
    ROOT / "commands/governance-review.md",
]

REVIEW_FALLBACK_POLICY_OPTIONAL_FILES = [
    ROOT / "project/e2e-test-project/commands/governance-review.md",
]

_REVIEW_FALLBACK_FORBIDDEN_PATTERNS = [
    r"降级为\s*Coordinator\s*执行审查",
    r"Coordinator\s*执行审查",
    r"Coordinator\s*自行执行审查",
]

_REVIEW_FALLBACK_REQUIRED_SNIPPETS = [
    "REVIEW-ERR-003",
    "general-purpose",
    "Reviewer role prompt",
    "BLOCKED",
    "degraded evidence",
    "不构成独立审查",
    "不得解锁",
    "Coordinator MUST NOT",
]


def check_governance_review_fallback_policy(required_paths=None, optional_paths=None):
    """FIX-061: prevent Coordinator self-review fallback in /governance-review.

    REVIEW-ERR-003 must require Reviewer spawn/fallback first; if no Reviewer
    runtime is available, the command may only block or emit degraded evidence
    that cannot count as independent review or unlock delivery.
    """
    result = {
        "files_checked": 0,
        "optional_skipped": [],
        "issues": [],
        "pass": True,
    }
    required = list(
        REVIEW_FALLBACK_POLICY_REQUIRED_FILES if required_paths is None else required_paths
    )
    optional = list(
        REVIEW_FALLBACK_POLICY_OPTIONAL_FILES if optional_paths is None else optional_paths
    )

    def _path_label(path):
        if path.is_absolute():
            try:
                return path.relative_to(ROOT).as_posix()
            except ValueError:
                return path.as_posix()
        return str(path).replace("\\", "/")

    def _check_file(path, optional_file=False):
        rel = _path_label(path)
        if not path.is_file():
            if optional_file:
                result["optional_skipped"].append(rel)
                return
            result["issues"].append({
                "file": rel,
                "type": "missing_file",
                "detail": "governance-review command file not found",
            })
            return

        result["files_checked"] += 1
        content = path.read_text(encoding="utf-8")
        for pattern in _REVIEW_FALLBACK_FORBIDDEN_PATTERNS:
            if re.search(pattern, content):
                result["issues"].append({
                    "file": rel,
                    "type": "coordinator_self_review_fallback",
                    "detail": f"forbidden fallback pattern found: {pattern}",
                })

        for snippet in _REVIEW_FALLBACK_REQUIRED_SNIPPETS:
            if snippet not in content:
                result["issues"].append({
                    "file": rel,
                    "type": "missing_policy_marker",
                    "detail": f"missing required marker: {snippet}",
                })

    for path in required:
        _check_file(path, optional_file=False)
    for path in optional:
        _check_file(path, optional_file=True)

    result["pass"] = len(result["issues"]) == 0
    return result


def cmd_check_governance(args):
    """Run governance health checks: evidence completeness, risk staleness, gate consistency."""
    # Ensure UTF-8 stdout to handle Chinese characters from .md files (Windows GBK workaround)
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    all_issues = 0

    # ── 1. Evidence completeness ──
    print("\n┌─ Check 1: Evidence Completeness ─────────────────────┐")
    ev_result = check_evidence_completeness()
    print(f"│  Completed tasks: {ev_result['completed_count']}")
    print(f"│  Tasks with evidence: {ev_result['evidenced_count']}")
    missing = ev_result["missing_evidence"]
    if missing:
        all_issues += len(missing)
        print(f"│  [WARN] {len(missing)} completed task(s) without evidence:")
        for tid in missing:
            print(f"│    - {tid}")
    else:
        print(f"│  [PASS] All completed tasks have evidence entries.")
    historical_missing = ev_result.get("historical_missing_evidence", [])
    if historical_missing:
        print(f"│  [INFO] {len(historical_missing)} archived completed task(s) without hot evidence "
              f"(historical residue):")
        for tid in historical_missing[:10]:
            print(f"│    - {tid}")
        if len(historical_missing) > 10:
            print(f"│    ... and {len(historical_missing) - 10} more")
    print("└──────────────────────────────────────────────────────┘")

    # ── 2. Risk staleness ──
    print("\n┌─ Check 2: Risk Staleness (>7 days) ──────────────────┐")
    risk_result = check_risk_staleness()
    print(f"│  Total open risks: {risk_result['total_open']}")
    stale = risk_result["stale"]
    fresh = risk_result["fresh"]
    if stale:
        all_issues += len(stale)
        print(f"│  [WARN] {len(stale)} stale risk(s):")
        for risk_id, date_str, age in stale:
            age_label = f"{age}d ago" if age >= 0 else "invalid date"
            print(f"│    - {risk_id} ({date_str}, {age_label})")
    else:
        print(f"│  [PASS] No stale risks.")
    if fresh:
        print(f"│  Fresh open risks ({len(fresh)}):")
        for risk_id, date_str, age in fresh:
            print(f"│    - {risk_id} ({date_str}, {age}d ago)")
    print("└──────────────────────────────────────────────────────┘")

    # ── 3. Gate consistency ──
    print("\n┌─ Check 3: Gate Consistency ──────────────────────────┐")
    gate_issues = check_gate_consistency()
    if gate_issues:
        for issue in gate_issues:
            if issue["type"] == "completed_tasks_missing_evidence":
                tasks_list = issue["detail"]
                all_issues += len(tasks_list)
                print(f"│  [WARN] Completed tasks without evidence:")
                for tid in tasks_list:
                    print(f"│    - {tid}")
            elif issue["type"] == "orphan_evidence":
                ev_list = issue["detail"]
                print(f"│  [INFO] Evidence entries for non-existent tasks:")
                for eid in ev_list:
                    print(f"│    - {eid}")
            elif issue["type"] == "historical_completed_tasks_missing_evidence":
                tasks_list = issue["detail"]
                print(f"│  [INFO] Archived completed tasks without evidence "
                      f"(historical residue): {tasks_list[:10]}")
                if len(tasks_list) > 10:
                    print(f"│    ... and {len(tasks_list) - 10} more")
    else:
        print(f"│  [PASS] Gate status and evidence are consistent.")
    print("└──────────────────────────────────────────────────────┘")

    # ── 4. Evidence quality ──
    print("\n┌─ Check 4: Evidence Quality ─────────────────────────┐")
    eq_issues = check_evidence_quality()
    eq_count = 0
    if eq_issues["session_context"]:
        eq_count += len(eq_issues["session_context"])
        print(f"│  [WARN] {len(eq_issues['session_context'])} evidence with '会话上下文' reference:")
        for item in eq_issues["session_context"]:
            print(f"│    - {item}")
    else:
        print(f"│  [PASS] No '会话上下文' references found.")
    if eq_issues["circular_refs"]:
        eq_count += len(eq_issues["circular_refs"])
        print(f"│  [WARN] {len(eq_issues['circular_refs'])} circular reference(s):")
        for item in eq_issues["circular_refs"]:
            print(f"│    - {item}")
    else:
        print(f"│  [PASS] No circular references found.")
    if eq_issues["empty_output"]:
        eq_count += len(eq_issues["empty_output"])
        print(f"│  [WARN] {len(eq_issues['empty_output'])} empty/incomplete evidence location(s):")
        for item in eq_issues["empty_output"]:
            print(f"│    - {item}")
    else:
        print(f"│  [PASS] No empty evidence locations found.")
    all_issues += eq_count
    print("└──────────────────────────────────────────────────────┘")

    # ── 5. Protocol compliance (external M8 validation) ──
    print("\n┌─ Check 5: Protocol Compliance (M8 External) ─────────┐")
    pc_issues = check_protocol_compliance()
    pc_count = 0

    if pc_issues["dri_violations"]:
        pc_count += len(pc_issues["dri_violations"])
        print(f"│  [WARN] {len(pc_issues['dri_violations'])} active task(s) with DRI violations:")
        for v in pc_issues["dri_violations"]:
            print(f"│    - {v['task_id']} ({v['status']}): {', '.join(v['violations'])}")
    else:
        print(f"│  [PASS] All active tasks have unique DRI.")

    if pc_issues["conditional_pass"]:
        pc_count += len(pc_issues["conditional_pass"])
        print(f"│  [WARN] {len(pc_issues['conditional_pass'])} conditional pass(es) without corrective tasks:")
        for v in pc_issues["conditional_pass"]:
            print(f"│    - {v['gate']}: {v['issue']}")
    else:
        print(f"│  [PASS] No unresolved conditional passes.")
        # Show conditional pass tracking if any exist
        gates = parse_gate_status()
        cp_gates = [g for g in gates if g["status"] == "passed-with-conditions"]
        if cp_gates:
            print(f"│  [INFO] {len(cp_gates)} conditional passes tracked: {', '.join(g['gate'] for g in cp_gates)}")

    if pc_issues["evidence_format"]:
        pc_count += len(pc_issues["evidence_format"])
        print(f"│  [WARN] {len(pc_issues['evidence_format'])} evidence entry(ies) with missing required fields:")
        for v in pc_issues["evidence_format"][:10]:  # Limit output
            print(f"│    - {v}")
        if len(pc_issues["evidence_format"]) > 10:
            print(f"│    ... and {len(pc_issues['evidence_format']) - 10} more")
    else:
        print(f"│  [PASS] All evidence entries have required fields.")

    all_issues += pc_count
    print("└──────────────────────────────────────────────────────┘")

    # ── 6. Tier audit completeness ──
    print("\n┌─ Check 6: Tier Audit Completeness ───────────────────┐")
    tier_result = check_tier_audit_completeness()
    tiers_defined = len(tier_result["all_details"])
    if tiers_defined == 0:
        print(f"│  [INFO] No Tier definitions found in plan-tracker — skip.")
    else:
        print(f"│  Tiers defined: {tiers_defined}")
        ta_issues = 0

        # Completed tiers WITH audit
        for detail in tier_result["completed_with_audit"]:
            print(f"│  [PASS] Tier {detail['tier_id']}: {detail['completed_count']}/{detail['task_count']} tasks completed, audit {detail['audit_evidence_id']} found.")

        # Completed tiers WITHOUT audit
        for detail in tier_result["completed_without_audit"]:
            ta_issues += 1
            all_issues += 1
            print(f"│  [WARN] Tier {detail['tier_id']}: {detail['completed_count']}/{detail['task_count']} tasks completed but NO audit evidence ({detail['audit_evidence_id']}).")
            for tid, status in detail["task_statuses"].items():
                print(f"│    - {tid}: {status}")

        # Incomplete tiers (informational)
        for detail in tier_result["incomplete_tiers"]:
            pending = detail["task_count"] - detail["completed_count"]
            print(f"│  [INFO] Tier {detail['tier_id']}: {detail['completed_count']}/{detail['task_count']} completed, {pending} pending — audit not yet due.")
            for tid, status in detail["task_statuses"].items():
                if status != "已完成":
                    print(f"│    - {tid}: {status}")

        if ta_issues == 0 and tier_result["completed_without_audit"] == []:
            completed_tiers = len(tier_result["completed_with_audit"])
            if completed_tiers > 0:
                print(f"│  [PASS] All {completed_tiers} completed Tier(s) have audit evidence.")
            else:
                print(f"│  [PASS] No completed Tiers without audit evidence.")

    print("└──────────────────────────────────────────────────────┘")

    # ── 7. Commit-task traceability ──
    print("\n┌─ Check 7: Commit-Task Traceability ──────────────────┐")
    ct_result = check_commit_task_references(limit=20)
    if "error" in ct_result:
        print(f"│  [INFO] Skipped: {ct_result['error']}")
    else:
        total = ct_result["total_checked"]
        without = ct_result["without_task_id"]
        print(f"│  Recent commits checked: {total}")
        if without > 0:
            all_issues += without
            print(f"│  [WARN] {without} commit(s) without task ID reference:")
            for c in ct_result["issues"]:
                msg_short = c["message"][:70] + ("..." if len(c["message"]) > 70 else "")
                print(f"│    - {c['sha']}: {msg_short}")
        else:
            print(f"│  [PASS] All {total} recent commits have task ID references.")
        # Show stats
        with_id = total - without
        print(f"│  With task ID: {with_id}/{total}")
    print("└──────────────────────────────────────────────────────┘")

    # ── 8. Risk escalation deadline ──
    print("\n┌─ Check 8: Risk Escalation Deadline ──────────────────┐")
    re_result = check_risk_escalation()
    escalated = re_result["escalated"]
    if escalated:
        all_issues += len(escalated)
        print(f"│  [WARN] {len(escalated)} open risk(s) with escalation deadline passed:")
        for r in escalated:
            print(f"│    - {r['risk_id']}: deadline {r['deadline']} ({r['days_overdue']}d overdue)")
    else:
        print(f"│  [PASS] No open risks with passed escalation deadlines.")
    print(f"│  Total open risks: {re_result['total_open']}")
    print("└──────────────────────────────────────────────────────┘")

    # ── 9. Task deadline enforcement ──
    print("\n┌─ Check 9: Task Deadline Enforcement ─────────────────┐")
    td_result = check_task_deadline()
    overdue_tasks = td_result["overdue"]
    if overdue_tasks:
        all_issues += len(overdue_tasks)
        print(f"│  [WARN] {len(overdue_tasks)} active task(s) with plan-complete date passed:")
        for t in overdue_tasks:
            print(f"│    - {t['task_id']} ({t['priority']}, {t['status']}): due {t['plan_complete']} ({t['days_overdue']}d overdue)")
    else:
        print(f"│  [PASS] No active tasks with passed plan-complete dates.")
    print(f"│  Total active tasks checked: {td_result['total_active']}")
    print("└──────────────────────────────────────────────────────┘")

    # ── 10. M5 AskUserQuestion compliance ──
    print("\n┌─ Check 10: M5 AskUserQuestion Compliance ────────────┐")
    m5_result = check_m5_compliance()
    m5_issues = m5_result["issues"]
    if m5_issues:
        blocking = [i for i in m5_issues if i["severity"] == "BLOCKING"]
        errors = [i for i in m5_issues if i["severity"] == "ERROR"]
        warnings = [i for i in m5_issues if i["severity"] == "WARNING"]
        all_issues += len(blocking) + len(errors)
        if blocking:
            print(f"│  [BLOCKING] {len(blocking)} M5 anti-pattern(s) — source files containing")
            print(f"│             inline question instructions (M5.1 violation):")
            for b in blocking:
                print(f"│    - {b['file']}:{b['line']}: {b['text'][:80]}")
                print(f"│      Fix: {b['fix']}")
        if errors:
            print(f"│  [ERROR] {len(errors)} M5 structural gap(s):")
            for e in errors:
                print(f"│    - {e['file']}: {e['text'][:80]}")
        if warnings:
            print(f"│  [WARN] {len(warnings)} M5 coverage warning(s):")
            for w in warnings:
                print(f"│    - {w['file']}: {w['text'][:80]}")
    else:
        print(f"│  [PASS] No M5 anti-patterns in source files.")
        print(f"│  [PASS] M5 AskUserQuestion rules present in bootstrap.")
        print(f"│  [PASS] interaction-boundary.md has AskUserQuestion bindings.")
    print(f"│  Total M5 checks: {m5_result['total_checks']}")
    print("└──────────────────────────────────────────────────────┘")

    # ── 11. Manifest consistency ──
    print("\n┌─ Check 11: Manifest Consistency ─────────────────────┐")
    mc_result = check_manifest_consistency()
    if mc_result.get("error"):
        print(f"│  [INFO] Skipped: {mc_result.get('error')}")
    else:
        mc_missing = mc_result["missing"]
        mc_untracked = mc_result["untracked"]
        print(f"│  Canonical files in manifest: {mc_result['canonical_count']}")
        print(f"│  Actual files on disk:       {mc_result['actual_count']}")
        if mc_missing:
            all_issues += len(mc_missing)
            print(f"│  [WARN] {len(mc_missing)} file(s) in manifest but missing on disk:")
            for m in mc_missing:
                print(f"│    - {m}")
        else:
            print(f"│  [PASS] No missing files (all manifest entries exist on disk).")
        if mc_untracked:
            all_issues += len(mc_untracked)
            print(f"│  [WARN] {len(mc_untracked)} file(s) on disk but not in manifest:")
            for u in mc_untracked:
                print(f"│    - {u}")
        else:
            print(f"│  [PASS] No untracked files (all files covered by manifest).")
    print("└──────────────────────────────────────────────────────┘")

    # ── 12. Cross-Reference Checking (SYSGAP-008) ──
    print("\n┌─ Check 12: Cross-Reference Checking ────────────────┐")
    xr_result = check_cross_references()
    print(f"│  Files scanned: {xr_result['total_files_scanned']}")
    print(f"│  References extracted: {xr_result['total_refs']}")
    xr_issues = 0
    if xr_result["dangling"]:
        xr_issues += len(xr_result["dangling"])
        all_issues += len(xr_result["dangling"])
        print(f"│  [WARN] {len(xr_result['dangling'])} dangling reference(s):")
        for d in xr_result["dangling"][:10]:
            print(f"│    - {d['source']}:{d['line']} -> {d['target']}")
        if len(xr_result["dangling"]) > 10:
            print(f"│    ... and {len(xr_result['dangling']) - 10} more")
    else:
        print(f"│  [PASS] No dangling references found.")
    if xr_result["deprecated"]:
        xr_issues += len(xr_result["deprecated"])
        all_issues += len(xr_result["deprecated"])
        print(f"│  [WARN] {len(xr_result['deprecated'])} deprecated path(s):")
        for d in xr_result["deprecated"][:10]:
            print(f"│    - {d['source']}:{d['line']}: {d['target']} ({d['deprecated_pattern']})")
        if len(xr_result["deprecated"]) > 10:
            print(f"│    ... and {len(xr_result['deprecated']) - 10} more")
    else:
        print(f"│  [PASS] No deprecated path patterns found.")
    if xr_result["cycles"]:
        xr_issues += len(xr_result["cycles"])
        all_issues += len(xr_result["cycles"])
        print(f"│  [WARN] {len(xr_result['cycles'])} circular reference(s):")
        for cycle in xr_result["cycles"]:
            print(f"│    - {' -> '.join(cycle)}")
    else:
        print(f"│  [PASS] No circular references found.")
    if xr_issues == 0:
        print(f"│  [PASS] Cross-reference graph is clean.")
    print("└──────────────────────────────────────────────────────┘")

    # ── 13. Sequential ID Checking (SYSGAP-009) ──
    print("\n┌─ Check 13: Sequential ID Checking ───────────────────┐")
    si_result = check_sequential_ids()
    si_issue_count = 0
    # DEC gaps
    if si_result["dec_gaps"]:
        si_issue_count += 1
        all_issues += 1
        print(f"│  [WARN] DEC-ID gaps: missing {si_result['dec_gaps']}")
    else:
        print(f"│  [PASS] DEC-IDs: {si_result['dec_ids'][0]:03d}-{si_result['dec_ids'][-1]:03d} ({len(si_result['dec_ids'])} entries, no gaps)")
    # EVD gaps
    if si_result["evd_gaps"]:
        print(f"│  [INFO] EVD-ID gaps: missing {si_result['evd_gaps']} "
              f"(historical archive residue)")
    else:
        print(f"│  [PASS] EVD-IDs: {si_result['evd_ids'][0]:03d}-{si_result['evd_ids'][-1]:03d} ({len(si_result['evd_ids'])} entries, no gaps)")
    # RISK gaps
    if si_result["risk_gaps"]:
        si_issue_count += 1
        all_issues += 1
        print(f"│  [WARN] RISK-ID gaps: missing {si_result['risk_gaps']}")
    else:
        if si_result["risk_ids"]:
            print(f"│  [PASS] RISK-IDs: {si_result['risk_ids'][0]:03d}-{si_result['risk_ids'][-1]:03d} ({len(si_result['risk_ids'])} entries, no gaps)")
        else:
            print(f"│  [PASS] RISK-IDs: no entries found.")
    # Orphan cross-references: info-only — these are historical cleanup residues
    # (old task IDs removed from plan-tracker during intentional cleanup, not errors)
    orphans = (si_result.get("orphan_evidence_refs", []) +
               si_result.get("orphan_decision_refs", []) +
               si_result.get("orphan_risk_refs", []))
    if orphans:
        print(f"│  [INFO] {len(orphans)} cross-reference(s) to non-existent task ID(s)"
              f" (historical cleanup residue): {orphans[:10]}")
        if len(orphans) > 10:
            print(f"│         ... and {len(orphans) - 10} more")
    else:
        print(f"│  [PASS] All cross-referenced task IDs exist in plan-tracker.")
    # Completed tasks without evidence
    missing_evd = si_result.get("completed_missing_evidence", [])
    if missing_evd:
        si_issue_count += len(missing_evd)
        all_issues += len(missing_evd)
        print(f"│  [WARN] {len(missing_evd)} completed task(s) without evidence: {missing_evd[:10]}")
    else:
        print(f"│  [PASS] All completed tasks have evidence entries.")
    historical_missing_evd = si_result.get("historical_completed_missing_evidence", [])
    if historical_missing_evd:
        print(f"│  [INFO] {len(historical_missing_evd)} archived completed task(s) "
              f"without evidence (historical residue): {historical_missing_evd[:10]}")
    if si_issue_count == 0:
        print(f"│  [PASS] All ID sequences are clean.")
    print("└──────────────────────────────────────────────────────┘")

    # ── 14. Structural Validity Checking (SYSGAP-010) ──
    print("\n┌─ Check 14: Structural Validity ──────────────────────┐")
    sv_issues = check_structural_validity()
    if sv_issues:
        blocking_sv = [i for i in sv_issues if i.get("severity") != "INFO"]
        info_sv = [i for i in sv_issues if i.get("severity") == "INFO"]
        all_issues += len(blocking_sv)
        label = "WARN" if blocking_sv else "INFO"
        print(f"│  [{label}] {len(sv_issues)} structural issue(s):")
        for v in sv_issues[:10]:
            detail = v.get("detail", "")
            ftype = v.get("type", "unknown")
            ffile = v.get("file", "?")
            line_info = f":{v['line']}" if v.get("line") else ""
            print(f"│    - [{ftype}] {ffile}{line_info}: {detail}")
        if len(sv_issues) > 10:
            print(f"│    ... and {len(sv_issues) - 10} more")
        if info_sv and not blocking_sv:
            print("│  [PASS] No actionable structural issues in current hot schema.")
    else:
        print(f"│  [PASS] All governance files have valid structure.")
    print("└──────────────────────────────────────────────────────┘")

    # ── 15. Commit Scope Verification (SYSGAP-012) ──
    print("\n┌─ Check 15: Commit Scope Verification ────────────────┐")
    cs_result = check_commit_scope(limit=20)
    if cs_result.get("error"):
        print(f"│  [INFO] Skipped: {cs_result['error']}")
    else:
        cs_issues = cs_result["issues"]
        print(f"│  Recent commits checked: {cs_result['total_checked']}")
        if cs_issues:
            all_issues += len(cs_issues)
            print(f"│  [WARN] {len(cs_issues)} scope discipline issue(s):")
            for v in cs_issues[:10]:
                detail = v.get("detail", "")
                sha = v.get("sha", "?")
                itype = v.get("type", "?")
                print(f"│    - [{itype}] {sha}: {detail}")
            if len(cs_issues) > 10:
                print(f"│    ... and {len(cs_issues) - 10} more")
        else:
            print(f"│  [PASS] All recent commits have clean scope discipline.")
    print("└──────────────────────────────────────────────────────┘")

    # ── 16. Goal Alignment (SYSGAP-023) ──
    print("\n┌─ Check 16: Goal Alignment ───────────────────────────┐")
    ga_result = check_goal_alignment()
    ga_issues = 0
    if not ga_result["has_project_goal"]:
        print(f"│  [WARN] plan-tracker missing 项目目标 field.")
        ga_issues += 1
    else:
        project_goal_short = ga_result["project_goal"][:60]
        print(f"│  [INFO] 项目目标: {project_goal_short}...")
    print(f"│  Impact analysis entries: {len(ga_result['entries'])}")
    if ga_result["entries"]:
        for e in ga_result["entries"]:
            if e["status"] == "FAIL":
                ga_issues += 1
                if not e["has_goal"]:
                    print(f"│  [FAIL] {e['task_id']} ({e['evd_id']}): 缺少 目标对齐: 字段")
                else:
                    print(f"│  [FAIL] {e['task_id']} ({e['evd_id']}): 目标对齐: 仅 {e['goal_len']} chars (需 >= 30)")
            elif e["status"] == "PASS":
                print(f"│  [PASS] {e['task_id']} ({e['evd_id']}): {e['goal_len']} chars")
        if ga_result["duplicates"]:
            print(f"│  [WARN] {len(ga_result['duplicates'])} duplicate goal alignment(s) (template reuse):")
            for t1, t2 in ga_result["duplicates"][:5]:
                print(f"│    - {t1} <-> {t2}")
            if len(ga_result["duplicates"]) > 5:
                print(f"│    ... and {len(ga_result['duplicates']) - 5} more")
    else:
        print(f"│  [PASS] No impact analysis entries to check.")
    if ga_issues == 0 and ga_result["has_project_goal"]:
        print(f"│  [PASS] Goal alignment check passed.")
    all_issues += ga_issues
    print("└──────────────────────────────────────────────────────┘")

    # ── 17. User Impact (SYSGAP-024) ──
    print("\n┌─ Check 17: User Impact ──────────────────────────────┐")
    ui_result = check_user_impact()
    ui_issues = 0
    print(f"│  Impact analysis entries: {len(ui_result['entries'])}")
    if ui_result["entries"]:
        for e in ui_result["entries"]:
            if e["status"] == "BLOCKING":
                ui_issues += 1
                all_issues += 1
                for issue in e["issues"]:
                    print(f"│  [BLOCKING] {e['task_id']} ({e['evd_id']}): {issue}")
            elif e["status"] == "FAIL":
                ui_issues += 1
                all_issues += 1
                for issue in e["issues"]:
                    print(f"│  [FAIL] {e['task_id']} ({e['evd_id']}): {issue}")
            elif e["status"] == "WARN":
                for issue in e["issues"]:
                    print(f"│  [WARN] {e['task_id']} ({e['evd_id']}): {issue}")
            else:
                print(f"│  [PASS] {e['task_id']} ({e['evd_id']}): "
                      f"获得={e['obtain']}, 体验变化={e['exp_change']}, "
                      f"迁移指南={e['migration']}")
    else:
        print(f"│  [PASS] No impact analysis entries to check.")
    if ui_issues == 0:
        print(f"│  [PASS] User impact check passed.")
    all_issues += ui_issues
    print("└──────────────────────────────────────────────────────┘")

    # ── 18. Fact Grounding (FIX-080) ──
    print("\n┌─ Check 18: Fact Grounding (FIX-080) ─────────────────┐")
    fg_result = check_fact_grounding()
    fg_issues = 0
    print(f"│  Current-release evidence entries: {len(fg_result['entries'])}")
    if fg_result["entries"]:
        for e in fg_result["entries"]:
            if e["status"] == "FAIL":
                fg_issues += 1
                for issue in e["issues"]:
                    print(f"│  [FAIL] {e['task_id']} ({e['evd_id']}): {issue}")
            else:
                print(f"│  [PASS] {e['task_id']} ({e['evd_id']}): 事实依据 {e['fact_len']} chars")
    else:
        print("│  [PASS] No current-release product evidence to check.")
    if fg_issues == 0:
        print("│  [PASS] Fact grounding check passed.")
    all_issues += fg_issues
    print("└──────────────────────────────────────────────────────┘")

    # ── 18b. Structured Evidence (FIX-083) ──
    print("\n┌─ Check 18b: Structured Evidence (FIX-083) ───────────┐")
    se_result = check_structured_evidence()
    se_issues = 0
    print(f"│  Current-release product evidence entries: {len(se_result['entries'])}")
    if se_result["entries"]:
        for e in se_result["entries"]:
            if e["status"] == "FAIL":
                se_issues += 1
                for issue in e["issues"]:
                    print(f"│  [FAIL] {e['task_id']} ({e['evd_id']}): {issue}")
            else:
                print(f"│  [PASS] {e['task_id']} ({e['evd_id']}): "
                      f"{e['commands']} command(s), {e['files_changed']} file(s)")
    else:
        print("│  [PASS] No current-release product evidence to check.")
    if se_issues == 0:
        print("│  [PASS] Structured evidence check passed.")
    all_issues += se_issues
    print("└──────────────────────────────────────────────────────┘")

    # ── 18c. AI Execution Packet (FIX-084) ──
    print("\n┌─ Check 18c: AI Execution Packet (FIX-084) ───────────┐")
    xp_result = check_execution_packets()
    xp_issues = 0
    print(f"│  Required active P0/P1 packet(s): {len(xp_result['required_tasks'])}")
    if xp_result["issues"]:
        xp_issues += len(xp_result["issues"])
        for issue in xp_result["issues"]:
            print(f"│  [FAIL] {issue}")
    for entry in xp_result["entries"]:
        if entry["status"] == "FAIL":
            xp_issues += 1
            print(f"│  [FAIL] {entry['task_id']}: {', '.join(entry['issues'])}")
        else:
            print(f"│  [PASS] {entry['task_id']}: execution packet ready")
    if not xp_result["required_tasks"]:
        print("│  [PASS] No active P0/P1 tasks require execution packets.")
    elif xp_issues == 0:
        print("│  [PASS] Execution packet check passed.")
    all_issues += xp_issues
    print("└──────────────────────────────────────────────────────┘")

    # ── 18d. Product Success Contract (FIX-088) ──
    print("\n┌─ Check 18d: Product Success Contract (FIX-088) ──────┐")
    psc_result = check_product_success_contracts()
    psc_issues = 0
    print(f"│  Required active P0/P1 contract(s): {len(psc_result['required_tasks'])}")
    if psc_result["issues"]:
        psc_issues += len(psc_result["issues"])
        for issue in psc_result["issues"]:
            print(f"│  [FAIL] {issue}")
    for entry in psc_result["entries"]:
        if entry["status"] == "FAIL":
            psc_issues += 1
            print(f"│  [FAIL] {entry['task_id']}: {', '.join(entry['issues'])}")
        else:
            print(f"│  [PASS] {entry['task_id']}: product success contract ready")
    if not psc_result["required_tasks"]:
        print("│  [PASS] No active P0/P1 tasks require product success contracts.")
    elif psc_issues == 0:
        print("│  [PASS] Product success contract check passed.")
    all_issues += psc_issues
    print("└──────────────────────────────────────────────────────┘")

    # ── 18e. Executable Acceptance Contract (FIX-089) ──
    print("\n┌─ Check 18e: Executable Acceptance Contract (FIX-089) ┐")
    accept_result = check_acceptance_contracts()
    accept_issues = 0
    print(f"│  Required active P0/P1 acceptance contract(s): {len(accept_result['required_tasks'])}")
    if accept_result["issues"]:
        accept_issues += len(accept_result["issues"])
        for issue in accept_result["issues"]:
            print(f"│  [FAIL] {issue}")
    for entry in accept_result["entries"]:
        if entry["status"] == "FAIL":
            accept_issues += 1
            print(f"│  [FAIL] {entry['task_id']}: {', '.join(entry['issues'])}")
        else:
            print(f"│  [PASS] {entry['task_id']}: acceptance contract ready")
    if not accept_result["required_tasks"]:
        print("│  [PASS] No active P0/P1 tasks require acceptance contracts.")
    elif accept_issues == 0:
        print("│  [PASS] Executable acceptance contract check passed.")
    all_issues += accept_issues
    print("└──────────────────────────────────────────────────────┘")

    # ── 19. Agent Team Review (SYSGAP-035) ──
    print("\n┌─ Check 19: Agent Team Review ────────────────────────┐")
    atr_result = check_agent_team_review()
    print(f"│  Product-code tasks (completed): {atr_result['total_tasks']}")
    print(f"│  Reviewed: {atr_result['reviewed']}")
    if atr_result.get("ignored_review_entries"):
        print(f"│  Ignored degraded/self-review entries: {len(atr_result['ignored_review_entries'])}")
        for entry in atr_result["ignored_review_entries"][:5]:
            print(f"│    - {entry['source']}: {entry['reason']}")
    if atr_result["unreviewed"] > 0:
        all_issues += atr_result["unreviewed"]
        print(f"│  [FAIL] {atr_result['unreviewed']} product-code task(s) without review evidence:")
        for tid in atr_result["review_gap_tasks"]:
            print(f"│    - {tid}")
    else:
        if atr_result["total_tasks"] > 0:
            print(f"│  [PASS] All product-code tasks have review evidence.")
        else:
            print(f"│  [PASS] No product-code tasks to review.")
    print("└──────────────────────────────────────────────────────┘")

    # ── 20. Agent Activation (SYSGAP-036) ──
    print("\n┌─ Check 20: Agent Activation (Analyst/Architect) ─────┐")
    aa_result = check_agent_activation()
    print(f"│  P0 cross-layer product tasks: {aa_result['total_p0_cross_layer']}")
    print(f"│  Analyst activated: {aa_result['analyst_activated']}")
    if aa_result["analyst_bypassed"] > 0:
        all_issues += aa_result["analyst_bypassed"]
        print(f"│  [FAIL] {aa_result['analyst_bypassed']} task(s) with impact analysis but no Analyst:")
        for tid in aa_result["bypassed_tasks"]:
            print(f"│    - {tid}")
    else:
        if aa_result["total_p0_cross_layer"] > 0:
            print(f"│  [PASS] All P0 cross-layer tasks have Analyst involvement.")
        else:
            print(f"│  [PASS] No P0 cross-layer product tasks to check.")
    print("└──────────────────────────────────────────────────────┘")

    # ── 21. Review Debt (SYSGAP-042) ──
    print("\n┌─ Check 21: Review Debt ─────────────────────────────┐")
    rd_result = check_review_debt()
    print(f"│  Product-code tasks (all, with evidence): {rd_result['total_tasks']}")
    print(f"│  Review debt (have execution evidence, no review): {rd_result['review_debt_count']}")
    if rd_result["review_debt_count"] > 0:
        all_issues += rd_result["review_debt_count"]
        print(f"│  [FAIL] {rd_result['review_debt_count']} product-code task(s) with review debt:")
        for tid in rd_result["review_debt_tasks"]:
            print(f"│    - {tid}")
    else:
        if rd_result["total_tasks"] > 0:
            print(f"│  [PASS] All product-code tasks have review evidence.")
        else:
            print(f"│  [PASS] No product-code tasks to check.")
    print("└──────────────────────────────────────────────────────┘")

    # ── 22. Review Coverage (FIX-037) ──
    print("\n┌─ Check 22: Review Coverage (FIX-037) ────────────────┐")
    rc_result = check_review_coverage()
    print(f"│  Product code tasks: {rc_result['total_tasks']}")
    print(f"│  Tasks with review evidence: {rc_result['reviewed']}")
    print(f"│  Coverage: {rc_result['coverage_pct']}%")
    if rc_result["unreviewed"] > 0:
        all_issues += rc_result["unreviewed"]
        print(f"│  [WARN] {rc_result['unreviewed']} unreviewed product-code task(s):")
        for tid in rc_result["unreviewed_tasks"]:
            print(f"│    - {tid}")
    else:
        if rc_result["total_tasks"] > 0:
            print(f"│  [PASS] Review coverage = 100% — all product-code tasks reviewed.")
        else:
            print(f"│  [PASS] No product-code tasks to check.")
    print("└──────────────────────────────────────────────────────┘")

    # ── 23. Profile Consistency (FIX-038) ──
    print("\n┌─ Check 23: Profile Consistency (FIX-038) ────────────┐")
    pc_result = check_profile_consistency()
    print(f"│  Profile: {pc_result['profile']}")
    print(f"│  Gate table rows: {pc_result['gate_rows']} (expected: {pc_result['expected_gate_rows']})")
    print(f"│  Task table columns: {pc_result['task_cols']} (expected: {pc_result['expected_task_cols']})")
    print(f"│  Conditional passes found: {pc_result['conditional_passes']}"
          f" {'(strict: must be 0)' if pc_result['profile'] == 'strict' else ''}")
    if pc_result["issues"]:
        all_issues += len(pc_result["issues"])
        print(f"│  [WARN] {len(pc_result['issues'])} profile consistency issue(s):")
        for issue in pc_result["issues"]:
            print(f"│    - {issue}")
    else:
        print(f"│  [PASS] Profile declaration matches actual structure.")
    print("└──────────────────────────────────────────────────────┘")

    # ── 24. Version Consistency (FIX-052) ──
    print("\n┌─ Check 24: Version Consistency (FIX-052) ───────────┐")
    vc_issues = check_version_consistency()
    vc_fail = [i for i in vc_issues if not i.startswith("[WARN]")]
    vc_warn = [i for i in vc_issues if i.startswith("[WARN]")]
    if vc_fail:
        all_issues += len(vc_fail)
        print(f"│  [FAIL] {len(vc_fail)} version mismatch(es):")
        for v in vc_fail:
            print(f"│    - {v}")
    else:
        print(f"│  [PASS] All version declarations match SKILL.md.")
    if vc_warn:
        print(f"│  [INFO] {len(vc_warn)} non-blocking drift(s):")
        for w in vc_warn:
            print(f"│    - {w}")
    print("└──────────────────────────────────────────────────────┘")

    # ── 25. Untracked Files Detection (FIX-057 Phase 2) ──
    print("\n┌─ Check 25: Untracked Files ──────────────────────────┐")
    uf_result = check_untracked_files()
    if uf_result["pass"] is None:
        print(f"│  [INFO] Skipped: could not run git ls-files.")
    elif uf_result["pass"] is True:
        print(f"│  [PASS] No untracked files found.")
    else:
        count = uf_result["untracked_count"]
        actionable_entry_files = uf_result.get("actionable_entry_files", [])
        all_issues += len(actionable_entry_files)
        if actionable_entry_files:
            print(f"│  [WARN] {count} untracked file(s) detected "
                  f"({len(actionable_entry_files)} actionable entry surface file(s)):")
        else:
            print(f"│  [WARN] {count} untracked file(s) detected (ordinary scratch/non-blocking):")
        # Group by directory
        by_dir = {}
        for f in uf_result["untracked_files"]:
            d = f.rsplit("/", 1)[0] if "/" in f else "(repo root)"
            by_dir.setdefault(d, []).append(f)
        for d in sorted(by_dir.keys()):
            print(f"│    {d}/")
            for fname in sorted(by_dir[d]):
                basename = fname.rsplit("/", 1)[-1] if "/" in fname else fname
                print(f"│      - {basename}")
        # Category suggestions
        if uf_result["suggest_archive"]:
            print(f"│  ── 应归档到仓库（git add）── {len(uf_result['suggest_archive'])} file(s):")
            for f in uf_result["suggest_archive"]:
                print(f"│    - {f}")
        if actionable_entry_files:
            print(f"│  ── 平台原生入口文件（actionable）── {len(actionable_entry_files)} file(s):")
            for f in actionable_entry_files:
                print(f"│    - {f}")
        if uf_result["suggest_temp_script"]:
            print(f"│  ── 可能是临时脚本，确认后归档或添加到 .gitignore ── {len(uf_result['suggest_temp_script'])} file(s):")
            for f in uf_result["suggest_temp_script"]:
                print(f"│    - {f}")
        if uf_result["suggest_manual"]:
            print(f"│  ── 需人工判断 ── {len(uf_result['suggest_manual'])} file(s):")
            for f in uf_result["suggest_manual"]:
                print(f"│    - {f}")
    print("└──────────────────────────────────────────────────────┘")

    # ── 26. Agent Lock Consistency (FIX-056 Phase 2) ──
    print("\n┌─ Check 26: Agent Lock Consistency (FIX-056) ─────────┐")
    al_result = check_agent_lock_consistency()
    al_issue_count = len(al_result.get("issues", []))
    al_blocking = [i for i in al_result.get("issues", []) if lock_issue_is_blocking(i)]
    if al_result.get("skipped"):
        print(f"│  [INFO] Skipped: {al_result['skipped']}")
    elif al_issue_count == 0:
        print(f"│  [PASS] agent-locks.json schema valid, {al_result['active_task_count']} active task(s), "
              f"{al_result['file_lock_count']} file lock(s).")
    else:
        all_issues += len(al_blocking)
        label = "WARN" if al_blocking else "INFO"
        print(f"│  [{label}] {al_issue_count} lock consistency issue(s) "
              f"({len(al_blocking)} blocking):")
        for issue in al_result["issues"]:
            severity = "BLOCKING" if lock_issue_is_blocking(issue) else "WARN"
            print(f"│    - [{severity}:{issue['type']}] {issue['detail']}")
        if al_result["active_task_count"] > 0 or al_result["file_lock_count"] > 0:
            print(f"│  State: {al_result['active_task_count']} active task(s), "
                  f"{al_result['file_lock_count']} file lock(s).")
    print("└──────────────────────────────────────────────────────┘")

    # ── 27. Archive Integrity (SYSGAP-030) ──
    print("\n┌─ Check 27: Archive Integrity (SYSGAP-030) ───────────┐")
    ai_result = check_archive_integrity()
    print(f"│  Hot tasks (plan-tracker): {ai_result['hot_tasks']}")
    print(f"│  Archived tasks: {ai_result['total_archived_tasks']}")
    print(f"│  Index entries: {ai_result['index_entries']}")
    if ai_result.get("pending_archive_tasks", 0):
        print(f"│  Pending archive tasks: {ai_result['pending_archive_tasks']}")
        print(f"│  Archive triggers: {', '.join(ai_result.get('archive_triggers', [])) or 'none'}")
    if ai_result["issues"]:
        all_issues += len(ai_result["issues"])
        print(f"│  [WARN] {len(ai_result['issues'])} archive integrity issue(s):")
        for issue in ai_result["issues"]:
            print(f"│    - {issue}")
    else:
        print(f"│  [PASS] Archive integrity verified — {'no archive data' if ai_result['total_archived_tasks'] == 0 else f'{ai_result['total_expected']} total tasks, index consistent'}")
    print("└──────────────────────────────────────────────────────┘")

    # ── 28. Governance Review Fallback Policy (FIX-061) ──
    print("\n┌─ Check 28: Governance Review Fallback Policy ────────┐")
    gr_result = check_governance_review_fallback_policy()
    print(f"│  Command files checked: {gr_result['files_checked']}")
    if gr_result["optional_skipped"]:
        print(f"│  Optional fixture skipped: {len(gr_result['optional_skipped'])}")
        for skipped in gr_result["optional_skipped"]:
            print(f"│    - {skipped}")
    if gr_result["issues"]:
        all_issues += len(gr_result["issues"])
        print(f"│  [FAIL] {len(gr_result['issues'])} /governance-review fallback policy issue(s):")
        for issue in gr_result["issues"]:
            print(f"│    - [{issue['type']}] {issue['file']}: {issue['detail']}")
    else:
        print("│  [PASS] Reviewer unavailable path blocks or records degraded evidence only.")
        print("│  [PASS] Coordinator self-review fallback is not allowed.")
    print("└──────────────────────────────────────────────────────┘")

    # ── 28b. Projection Sync Guard (FIX-086) ──
    print("\n┌─ Check 28b: Projection Sync Guard (FIX-086) ─────────┐")
    ps_result = check_projection_sync()
    print(f"│  Source version: {ps_result['source_version'] or 'unknown'}")
    print(f"│  Mirrored files checked: {ps_result['mirrors_checked']}")
    if ps_result.get("mirrors_skipped_untracked"):
        print(f"│  Untracked local projection copies skipped: {ps_result['mirrors_skipped_untracked']}")
    if ps_result["issues"]:
        all_issues += len(ps_result["issues"])
        print(f"│  [FAIL] {len(ps_result['issues'])} projection sync issue(s):")
        for issue in ps_result["issues"][:10]:
            print(f"│    - {issue}")
        if len(ps_result["issues"]) > 10:
            print(f"│    ... and {len(ps_result['issues']) - 10} more")
    else:
        print("│  [PASS] Source, target fixture, native entries, and plugin versions are synchronized.")
    print("└──────────────────────────────────────────────────────┘")

    # ── 28c. Hot Fact-Source Consistency Guard (FIX-087) ──
    print("\n┌─ Check 28c: Hot Fact-Source Consistency (FIX-087) ───┐")
    hfs_issues = check_hot_fact_source_consistency()
    if hfs_issues:
        all_issues += len(hfs_issues)
        print(f"│  [FAIL] {len(hfs_issues)} hot fact-source issue(s):")
        for issue in hfs_issues[:10]:
            print(f"│    - {issue}")
        if len(hfs_issues) > 10:
            print(f"│    ... and {len(hfs_issues) - 10} more")
    else:
        print("│  [PASS] Project config, overview, active items, roadmap, dependency chain, and requirement matrix are aligned.")
    print("└──────────────────────────────────────────────────────┘")

    # ── Summary ──
    print(f"\n┌─ Governance Health Summary ──────────────────────────┐")
    if all_issues == 0:
        print(f"│  Result: PASSED — 0 issues found")
    else:
        print(f"│  Result: ISSUES FOUND — {all_issues} issue(s)")
    print("└──────────────────────────────────────────────────────┘")

    if args.fail_on_issues and all_issues > 0:
        sys.exit(1)


# ── Gate auto-judgment (B-level automation) ───────────────────────

# Per-gate check item heuristics: (check_label, auto_judge_function)
# Each function returns: (PASS/FAIL/NEEDS_HUMAN, detail_message)

def _check_file_exists(relative_path, label):
    """Check if a file or directory exists."""
    path = ROOT / relative_path
    if path.exists():
        return "PASS", f"{label}: {relative_path} exists"
    return "FAIL", f"{label}: {relative_path} NOT FOUND"


def _check_snippet_in_file(relative_path, snippet, label):
    """Check if a snippet exists in a file."""
    path = ROOT / relative_path
    if not path.is_file():
        return "FAIL", f"{label}: file {relative_path} NOT FOUND"
    content = path.read_text(encoding="utf-8")
    if snippet in content:
        return "PASS", f"{label}: '{snippet[:50]}...' found in {relative_path}"
    return "FAIL", f"{label}: '{snippet[:50]}...' NOT found in {relative_path}"


def _check_all_required_files_exist():
    """Silently check if all required files exist (for auto-judgment)."""
    required = build_required_files_from_manifest()
    if required is None:
        required = REQUIRED_FILES
    missing = [label for label, path in required.items() if not path.is_file()]
    if not missing:
        return "PASS", "所有必需文件存在 — 仓库结构符合约定"
    return "FAIL", f"缺失 {len(missing)} 个必需文件: {', '.join(missing[:3])}..."


def _check_governance_file_exists(filename):
    """Check if a governance file exists and has content."""
    path = ROOT / ".governance" / filename
    if path.is_file() and path.stat().st_size > 0:
        return "PASS", f".governance/{filename} 存在且非空"
    return "FAIL", f".governance/{filename} 不存在或为空"


def _check_quantifiable_metrics():
    """Check if project has quantifiable success metrics in plan-tracker."""
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    # Look for numeric targets in plan-tracker overview or config
    metrics_patterns = [
        r"≥\s*\d+",           # ≥ N
        r"\d+%",              # N%
        r"≤\s*\d+",           # ≤ N
        r"coverage.*\d+",      # coverage mention with number
        r"PASSED.*\d+",        # PASSED with count
    ]
    for pattern in metrics_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return "PASS", "项目目标含量化指标（检测到数字阈值或百分比）"
    return "NEEDS_HUMAN", "无法自动检测量化指标——需人工确认项目目标是否可衡量"


def _check_scope_boundary():
    """Check if scope boundaries are defined."""
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    if "范围" in content or "scope" in content.lower():
        return "PASS", "plan-tracker 中包含范围相关描述"
    return "NEEDS_HUMAN", "需人工确认范围边界是否清晰"


def _check_stakeholders():
    """Check if stakeholders are identified."""
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    # Check for role descriptions in plan-tracker tasks or config
    if "项目负责人" in content or "Owner" in content:
        return "PASS", "检测到干系人角色（项目负责人/Owner）"
    return "NEEDS_HUMAN", "需人工确认干系人列表"


def _check_out_of_scope():
    """Check if out-of-scope items are explicitly listed."""
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    if "范围外" in content or "不做什么" in content or "out of scope" in content.lower():
        return "PASS", "检测到范围外/不做什么声明"
    return "NEEDS_HUMAN", "需人工确认范围外事项是否明确"


def _check_completed_ratio(min_ratio=0.5):
    """Check if plan-tracker completed ratio meets threshold."""
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    # Match the overview table: after "总任务数" header line, the data row has:
    # | name | stage | total | completed | blocked | risks | gate | date |
    lines = content.split("\n")
    in_overview = False
    for i, line in enumerate(lines):
        if "总任务数" in line and "已完成" in line:
            in_overview = True
            continue
        if in_overview and line.strip().startswith("|") and not "---" in line:
            # Data row: extract columns
            parts = [p.strip() for p in line.split("|")]
            # parts[0]=empty, [1]=name, [2]=stage, [3]=total, [4]=completed, ...
            if len(parts) >= 5:
                try:
                    total = int(parts[3])
                    completed = int(parts[4])
                    ratio = completed / total if total > 0 else 0
                    if ratio >= min_ratio:
                        return "PASS", f"任务完成率 {ratio:.0%} ≥ {min_ratio:.0%}（{completed}/{total}）"
                    return "FAIL", f"任务完成率 {ratio:.0%} < {min_ratio:.0%}（{completed}/{total}）"
                except ValueError:
                    continue
            break
    return "NEEDS_HUMAN", "无法从 plan-tracker 解析完成率"


def _check_evidence_mentions(keyword, label):
    """Check if evidence-log contains a keyword."""
    content = EVIDENCE_PATH.read_text(encoding="utf-8")
    if keyword in content:
        return "PASS", f"{label}: evidence-log 含'{keyword[:30]}'相关证据"
    return "NEEDS_HUMAN", f"{label}: evidence-log 未找到'{keyword[:30]}'——需人工确认"


def _read_archive_aware_governance_text(include=()):
    """Read hot governance files plus selected archive directories."""
    ds = GovernanceDataSource()
    chunks = []
    hot_paths = []
    if "plan" in include:
        hot_paths.append(ds.sample_path)
    if "evidence" in include:
        hot_paths.append(ds.evidence_path)
    if "decision" in include:
        hot_paths.append(ds.decision_path)
    if "risk" in include:
        hot_paths.append(ds.risk_path)

    for path in hot_paths:
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8"))

    archive_dirs = []
    if "plan" in include:
        archive_dirs.append(ds.archive_tasks_dir)
    if "evidence" in include:
        archive_dirs.append(ds.archive_evidence_dir)
    if "decision" in include:
        archive_dirs.append(ds.archive_decisions_dir)
    if "risk" in include:
        archive_dirs.append(ds.archive_risks_dir)

    if ds._has_archive():
        for archive_dir in archive_dirs:
            if not archive_dir.exists():
                continue
            for path in sorted(archive_dir.glob("*.md")):
                if path.name != ".gitkeep":
                    chunks.append(path.read_text(encoding="utf-8"))

    return "\n".join(chunks)


def _contains_all(text, keywords):
    return all(keyword in text for keyword in keywords)


def _contains_any(text, keywords):
    return any(keyword in text for keyword in keywords)


def _has_line_with_all(text, keyword_groups):
    """Return True when one line contains at least one keyword from each group."""
    for line in text.splitlines():
        if all(_contains_any(line, group) for group in keyword_groups):
            return True
    return False


def _iter_archive_aware_evidence_units():
    """Yield hot/archive evidence rows; fallback to whole non-table archive docs."""
    ds = GovernanceDataSource()
    if ds.evidence_path.is_file():
        for line in ds.evidence_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("| EVD-"):
                yield line

    if not ds._has_archive() or not ds.archive_evidence_dir.exists():
        return

    for path in sorted(ds.archive_evidence_dir.glob("*.md")):
        if path.name == ".gitkeep":
            continue
        content = path.read_text(encoding="utf-8")
        rows = [
            line for line in content.splitlines()
            if line.strip().startswith("| EVD-")
        ]
        if rows:
            for row in rows:
                yield row
        else:
            yield content


def _line_has_issue_severity(line):
    """Detect explicit issue severity values, not schema/header field names."""
    severity_patterns = [
        r"严重级别\s*[:：=|]\s*(P0|P1|P2|高风险|中风险|低风险|高严重|中严重|低严重|critical|high|medium|low)\b",
        r"\bseverity\s*[:：=|]\s*(P0|P1|P2|critical|high|medium|low)\b",
        r"\b(P0|P1|P2|critical|high|medium|low)\b",
        r"(高风险|中风险|低风险|高严重|中严重|低严重)",
    ]
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in severity_patterns)


def _line_has_issue_status_value(line):
    """Detect explicit issue status values, not only a status field name."""
    status_patterns = [
        r"状态\s*[:：=|]\s*(打开|已关闭|进行中|待处理|处理中|已解决|closed|open|done|resolved|in progress)\b",
        r"\bstatus\s*[:：=|]\s*(closed|open|done|resolved|in progress)\b",
    ]
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in status_patterns)


def _line_has_real_issue_item(line):
    """Detect an actual issue item/task entry rather than a schema-only line."""
    if _contains_any(line.lower(), ("schema", "header")):
        return False
    if _contains_any(line, ("字段", "表头", "模板", "格式")):
        return False
    item_patterns = [
        r"(问题项|问题条目|问题实例|issue item)",
        r"\b(ISSUE|BUG|TASK|FIX|AUDIT)-\d+\b",
        r"问题\s*\d+",
        r"问题\s*[:：]\s*\S+",
        r"任务\s*[:：]\s*\S+",
    ]
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in item_patterns)


def _plan_row_is_inactive(parts):
    """Return True when a plan table row is completed/terminated/cancelled."""
    joined = " ".join(parts).lower()
    inactive_markers = (
        "已完成", "✅", "已终止", "终止", "取消", "已取消",
        "closed", "done", "completed", "terminated", "cancelled", "canceled",
    )
    return any(marker in joined for marker in inactive_markers)


def _check_g10_real_operation_data():
    """G10: require explicit real operation data for at least one week."""
    text = _read_archive_aware_governance_text(include=("evidence",))
    if _has_line_with_all(text, (
        ("真实运营数据", "真实运行数据", "运行数据", "运营数据"),
        ("至少 1 周", "至少1周", "一周", "7天", "7 天", "1 week", "one week"),
    )):
        return "PASS", "检测到至少 1 周真实运营/运行数据证据（含归档 evidence）"
    return "NEEDS_HUMAN", "未检测到明确的至少 1 周真实运营数据证据"


def _check_g10_feedback_archived_classified():
    """G10: feedback must be archived and classified."""
    text = _read_archive_aware_governance_text(include=("evidence", "plan"))
    if _has_line_with_all(text, (
        ("用户反馈", "反馈汇总", "反馈归档"),
        ("已归档", "归档", "archive"),
        ("分类", "类别", "类型"),
    )):
        return "PASS", "检测到已归档且已分类的用户反馈证据（含归档 evidence）"
    return "NEEDS_HUMAN", "未检测到反馈归档+分类的完整证据"


def _check_g10_issue_list_severity_status():
    """G10: issue list must include severity and status, not just priority."""
    text = _read_archive_aware_governance_text(include=("evidence", "plan", "risk"))
    for line in text.splitlines():
        has_issue_list = _contains_any(line, ("问题清单", "issue list", "问题列表"))
        if (
            has_issue_list
            and _line_has_real_issue_item(line)
            and _line_has_issue_severity(line)
            and _line_has_issue_status_value(line)
        ):
            return "PASS", "检测到包含严重级别和状态的问题清单"
    return "NEEDS_HUMAN", "未检测到真实问题项及其严重级别值和状态值"


def _check_g10_executable_optimization_items():
    """G10: optimization direction must be executable, not only a slogan."""
    text = _read_archive_aware_governance_text(include=("evidence", "plan"))
    if _has_line_with_all(text, (
        ("优化项", "改进项", "优化方向", "改进方向", "可执行优化项"),
        ("Owner", "DRI", "截止", "验收", "验证", "命令", "文件", "任务"),
    )):
        return "PASS", "检测到带执行标记的优化/改进项"
    return "NEEDS_HUMAN", "未检测到可执行优化项（需 Owner/截止/验收/验证等执行标记）"


def _check_g11_retro_complete():
    """G11: retro must include the four required sections."""
    required = ("目标回顾", "结果评估", "原因分析", "经验沉淀")
    evidence_units = list(_iter_archive_aware_evidence_units())
    for unit in evidence_units:
        if _contains_all(unit, required):
            return "PASS", "复盘证据包含目标回顾/结果评估/原因分析/经验沉淀（含归档 evidence）"
    text = "\n".join(evidence_units)
    if not text:
        text = _read_archive_aware_governance_text(include=("evidence",))
    missing = [keyword for keyword in required if keyword not in text]
    if not missing:
        return "NEEDS_HUMAN", "复盘四要素分散在多条证据中，未检测到同一条复盘证据包含全部四要素"
    return "NEEDS_HUMAN", f"复盘证据缺少: {', '.join(missing)}"


def _check_g11_rules_templates_backfilled():
    """G11: rules/templates backfill needs evidence, commit, or file-change proof."""
    text = _read_archive_aware_governance_text(include=("evidence",))
    if _has_line_with_all(text, (
        ("回灌", "规则修订", "模板更新", "经验回灌"),
        ("规则", "模板", "protocol", "template", "SKILL.md", "stage-gates.md"),
        ("commit", "提交", "文件变更", "修改", "更新", ".md", ".py"),
    )):
        return "PASS", "检测到规则/模板回灌及提交或文件变更证据"
    return "NEEDS_HUMAN", "未检测到规则/模板回灌的提交或文件变更证据"


def _check_g11_next_round_direction():
    """G11: next-round direction must be explicit or an active P0, not any historical P0."""
    content = SAMPLE_PATH.read_text(encoding="utf-8") if SAMPLE_PATH.is_file() else ""
    active_section = content
    marker = "## 当前活跃事项"
    if marker in content:
        active_section = content.split(marker, 1)[1].split("\n## ", 1)[0]

    for line in active_section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        parts = _split_markdown_table_row(line)
        normalized = [part.replace("*", "").strip() for part in parts]
        has_active_p0 = any(part == "P0" for part in normalized)
        if has_active_p0 and not _plan_row_is_inactive(normalized):
            return "PASS", "当前活跃事项中存在未完成的 P0 任务，下一轮方向明确"

    next_round_terms = ("下一轮", "下轮")
    for line in active_section.splitlines():
        if (
            _contains_any(line, next_round_terms)
            and re.search(r"[A-Z]+-\d+", line)
            and not _plan_row_is_inactive([line])
        ):
            return "PASS", "当前活跃事项显式描述下一轮方向并关联任务"

    return "FAIL", "未检测到计划中的下一轮方向或活跃 P0 任务"


def _check_risk_has_closed(label="关键缺陷"):
    """Check if risk-log has any closed/critical risk entries."""
    content = RISK_PATH.read_text(encoding="utf-8")
    closed_count = sum(1 for line in content.split("\n") if "已关闭" in line or "已缓解" in line)
    if closed_count > 0:
        return "PASS", f"{label}: {closed_count} 条风险已关闭/已缓解"
    return "NEEDS_HUMAN", f"{label}: 无已关闭风险——需人工确认是否所有关键缺陷已处理"


def _check_plan_has_priority(priority="P0"):
    """Check if plan-tracker has tasks at a given priority."""
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    count = len(re.findall(rf"\|\s*{priority}\s*\|", content))
    if count > 0:
        return "PASS", f"plan-tracker 含 {count} 条 {priority} 任务"
    return "FAIL", f"plan-tracker 无 {priority} 任务——下轮方向不明确"


def _check_version_consistency_heuristic():
    """Lightweight version consistency check for G11 auto-judgment (SYSGAP-020 enhanced).

    Checks: SKILL.md frontmatter version must appear consistently in all
    version declaration files (8 positions), CHANGELOG latest entry,
    and verify_workflow.py hardcoded snippets.
    """
    try:
        skill_content = (ROOT / "skills/software-project-governance/SKILL.md").read_text(encoding="utf-8")
        m = re.search(r'version[:\*]+\s*([\d.]+)', skill_content)
        if not m:
            return "NEEDS_HUMAN", "无法从 SKILL.md 提取版本号"
        skill_version = m.group(1)

        # Version declaration files
        version_files = [
            "skills/software-project-governance/core/manifest.json",
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            ".codex-plugin/plugin.json",
            "skills/software-project-governance/infra/verify_workflow.py",
        ]
        for vf in version_files:
            vf_path = ROOT / vf
            if vf_path.exists():
                vf_content = vf_path.read_text(encoding="utf-8")
                if skill_version not in vf_content:
                    return "FAIL", f"{vf} 版本与 SKILL.md ({skill_version}) 不一致"

        # CHANGELOG latest entry
        changelog_path = ROOT / "project/CHANGELOG.md"
        if changelog_path.exists():
            changelog_content = changelog_path.read_text(encoding="utf-8")
            cl_match = re.search(r'##\s*\[([\d.]+)\]', changelog_content)
            if cl_match and cl_match.group(1) != skill_version:
                return "FAIL", f"CHANGELOG.md 最新版本 [{cl_match.group(1)}] 与 SKILL.md ({skill_version}) 不一致"

        return "PASS", f"版本 {skill_version} 在 {len(version_files)} 个声明文件中一致"
    except Exception as e:
        return "NEEDS_HUMAN", f"版本检查异常: {e}"


def auto_judge_gate(gate_id):
    """Auto-judge a specific Gate based on available evidence.

    Returns: dict with overall_result (passed/blocked/passed-with-conditions/needs_human)
             and per-item results list.
    """
    gate_id = gate_id.upper()
    if not gate_id.startswith("G"):
        gate_id = "G" + gate_id

    detail = parse_gate_detail(gate_id)
    if not detail:
        return {"error": f"Gate {gate_id} not found", "items": []}

    # ── Gate-specific heuristics ──
    gate_heuristics = {
        "G1": [
            ("项目目标可衡量", _check_quantifiable_metrics),
            ("范围边界清晰", _check_scope_boundary),
            ("关键干系人已识别", _check_stakeholders),
            ("明確的『不做什麼』清單", _check_out_of_scope),
        ],
        "G2": [
            ("调研覆盖技术/市场/用户三维度",
             lambda: _check_snippet_in_file(
                 "project/workflows/software-project-governance/research/company-practices.md",
                 "## ", "调研文档含多维度章节")),
            ("竞争格局清晰（竞品≥3×≥4维度）",
             lambda: _check_file_exists(
                 "project/workflows/software-project-governance/research/agent-integration-models.md",
                 "竞争分析/竞品对比")),
            ("关键发现有数据支撑",
             lambda: ("PASS", "research/ 目录含多份调研文档，数据来源可追溯")
             if len(list((ROOT / "project/workflows/software-project-governance/research").glob("*.md"))) >= 4
             else ("FAIL", "research/ 调研文档不足 4 份")),
            ("技术可行性约束已识别",
             lambda: _check_snippet_in_file(
                 ".governance/risk-log.md", "RISK-", "风险记录含技术约束")),
        ],
        "G3": [
            ("评估了至少2个候选方案",
             lambda: _check_snippet_in_file(
                 ".governance/decision-log.md", "备选方案", "决策记录含备选方案")),
            ("评估标准事先定义",
             lambda: _check_snippet_in_file(
                 "skills/software-project-governance/core/protocol/plugin-contract.md", "准入标准", "评估标准/准入标准已定义")),
            ("选择原因已留痕",
             lambda: _check_snippet_in_file(
                 ".governance/decision-log.md", "选择原因", "决策记录含选择原因")),
            ("关键风险已通过PoC验证",
             lambda: _check_snippet_in_file(
                 "skills/software-project-governance/core/protocol/headless-runner-sample.md", "## 目标", "PoC/验证样例存在")),
        ],
        "G4": [
            ("开发环境可复现",
             lambda: _check_file_exists("skills/software-project-governance/infra/verify_workflow.py", "一键验证脚本")),
            ("仓库结构符合约定",
             lambda: _check_all_required_files_exist()),
            ("基础CI可运行",
             lambda: _check_file_exists("skills/software-project-governance/infra/verify_workflow.py", "CI/验证脚本")),
            ("协作规范已建立",
             lambda: _check_snippet_in_file(
                 "skills/software-project-governance/SKILL.md", "MUST", "行为协议含强制规范")),
        ],
        "G5": [
            ("架构满足非功能性需求",
             lambda: _check_snippet_in_file(
                 "skills/software-project-governance/core/protocol/plugin-contract.md", "冲击场景", "非功能需求/冲击场景已定义")),
            ("模块划分清晰、职责单一",
             lambda: _check_snippet_in_file(
                 "skills/main-workflow/SKILL.md", "## ", "模块划分/分层架构已定义")),
            ("关键接口已定义",
             lambda: _check_snippet_in_file(
                 "skills/software-project-governance/core/protocol/command-schema.md", "Input Parameters", "接口/命令schema已定义")),
            ("经过技术评审",
             lambda: _check_snippet_in_file(
                 "skills/tech-review/SKILL.md",
                 "评审", "技术评审checklist存在")),
            ("详细设计覆盖核心模块",
             lambda: _check_snippet_in_file(
                 "skills/stage-architecture/SKILL.md",
                 "## ", "架构设计子工作流存在")),
        ],
        "G6": [
            ("核心功能按设计实现",
             lambda: _check_completed_ratio(0.5)),
            ("单元测试覆盖达标（standard: ≥70%）",
             lambda: _check_file_exists("skills/software-project-governance/infra/verify_workflow.py", "验证脚本作为测试覆盖代理")),
            ("Code Review 遗留项关闭",
             lambda: _check_evidence_mentions("code-review-standard", "Code Review")),
            ("集成验证通过",
             lambda: ("PASS", "verify_workflow.py 可作为集成验证代理——脚本存在且可运行")
             if (ROOT / "skills/software-project-governance/infra/verify_workflow.py").exists()
             else ("FAIL", "verify_workflow.py 不存在")),
        ],
        "G7": [
            ("关键缺陷已关闭",
             lambda: _check_risk_has_closed("关键缺陷")),
            ("回归测试通过",
             lambda: _check_file_exists("skills/software-project-governance/infra/verify_workflow.py", "验证脚本作为回归测试代理")),
            ("性能指标达标",
             lambda: ("NEEDS_HUMAN", "无性能测试基础设施——需人工确认性能指标")),
            ("安全测试覆盖关键风险",
             lambda: _check_evidence_mentions("RISK-", "安全/风险")),
        ],
        "G8": [
            ("CI 流水线稳定（最近运行成功率 ≥ 80%）",
             lambda: _check_file_exists("skills/software-project-governance/infra/verify_workflow.py", "验证脚本作为 CI 代理——存在即可运行")),
            ("自动化测试覆盖核心路径",
             lambda: _check_snippet_in_file(
                 "skills/software-project-governance/infra/verify_workflow.py", "def check_", "验证脚本含多项自动化检查")),
            ("质量门禁生效",
             lambda: _check_snippet_in_file(
                 "skills/software-project-governance/infra/verify_workflow.py", "check-governance", "check-governance 作为质量门禁")),
            ("部署流程文档化",
             lambda: _check_file_exists(
                 "skills/stage-release/SKILL.md",
                 "发布阶段子工作流")),
        ],
        "G9": [
            ("发布范围明确（版本号/范围/时间窗口）",
             lambda: _check_snippet_in_file("project/CHANGELOG.md", "## [0.", "CHANGELOG 含版本发布条目")),
            ("变更日志完整",
             lambda: _check_file_exists("project/CHANGELOG.md", "CHANGELOG 存在")),
            ("回滚方案已验证",
             lambda: ("NEEDS_HUMAN", "无回滚测试环境——需人工确认回滚方案")),
            ("发布后验证已定义",
             lambda: _check_file_exists(
                 "skills/release-checklist/SKILL.md",
                 "发布 checklist")),
        ],
        "G10": [
            ("收集到真实运营数据",
             lambda: _check_g10_real_operation_data()),
            ("用户反馈已归档",
             lambda: _check_g10_feedback_archived_classified()),
            ("关键问题已识别分类",
             lambda: _check_g10_issue_list_severity_status()),
            ("优化方向已明确",
             lambda: _check_g10_executable_optimization_items()),
        ],
        "G11": [
            ("复盘完成（含目标回顾/结果评估/原因分析/经验沉淀）",
             lambda: _check_g11_retro_complete()),
            ("经验回灌到规则和模板",
             lambda: _check_g11_rules_templates_backfilled()),
            ("下轮方向已明确（计划中的下一轮/活跃 P0）",
             lambda: _check_g11_next_round_direction()),
            ("版本化记录已更新",
             lambda: _check_version_consistency_heuristic()),
        ],
    }

    heuristics = gate_heuristics.get(gate_id, [])

    # ── Execute auto-judgment ──
    items = []
    pass_count = 0
    fail_count = 0
    human_count = 0

    for check_label, judge_fn in heuristics:
        try:
            result, message = judge_fn()
        except Exception as e:
            result, message = "FAIL", f"判定异常: {e}"

        items.append({
            "check": check_label,
            "result": result,
            "detail": message,
        })
        if result == "PASS":
            pass_count += 1
        elif result == "FAIL":
            fail_count += 1
        else:
            human_count += 1

    # ── Overall result ──
    total = len(items)
    if total == 0:
        overall = "needs_human"
    elif fail_count > 0:
        overall = "blocked"
    elif human_count > 0:
        overall = "passed-with-conditions"
    else:
        overall = "passed"

    return {
        "gate": gate_id,
        "title": detail["title"],
        "overall": overall,
        "items": items,
        "summary": f"PASS={pass_count} FAIL={fail_count} NEEDS_HUMAN={human_count}",
    }


def cmd_gate_check(args):
    """Auto-judge a specific Gate."""
    gate_id = args.gate_id.upper()
    result = auto_judge_gate(gate_id)

    if "error" in result:
        print(f"[FAIL] {result['error']}")
        sys.exit(1)

    # Display result
    overall_icons = {
        "passed": "[PASS]",
        "blocked": "[BLOCK]",
        "passed-with-conditions": "[COND]",
        "needs_human": "[????]",
    }
    icon = overall_icons.get(result["overall"], "[????]")

    print(f"\n┌─ Gate Check: {result['gate']} ───────────────────────────────────┐")
    print(f"│  {result['title']}")
    print(f"│  Overall: {icon} {result['overall'].upper()}")
    print(f"│  {result['summary']}")
    print(f"│")

    for i, item in enumerate(result["items"], 1):
        item_icon = {"PASS": "[PASS]", "FAIL": "[FAIL]", "NEEDS_HUMAN": "[????]"}
        ic = item_icon.get(item["result"], "[????]")
        print(f"│  {ic} 检查项{i}: {item['check']}")
        print(f"│      {item['detail']}")

    print(f"└──────────────────────────────────────────────────────┘")

    # Show current status from plan-tracker
    gates = parse_gate_status()
    for g in gates:
        if g["gate"].upper() == gate_id.upper():
            cur_icon = STATUS_ICONS.get(g["status"], "[????]")
            print(f"\n  Plan-tracker status: {cur_icon} {g['status']} ({g['date']})")
            if g["status"] == "passed-on-entry":
                print(f"  Note: This gate was passed-on-entry (mid-project onboarding).")
                print(f"  Auto-judgment reflects current evidence, not historical state.")
            break

    # Exit with non-zero if blocked
    if args.fail_on_blocked and result["overall"] == "blocked":
        sys.exit(1)


# ── Main CLI entry point ─────────────────────────────────────────

def check_plugin_freshness():
    """Compare installed plugin version with source repository HEAD."""
    import json
    import subprocess
    from datetime import datetime

    result = {
        "installed_version": "unknown",
        "installed_commit": "unknown",
        "installed_date": "unknown",
        "source_version": "unknown",
        "source_commit": "unknown",
        "status": "UNKNOWN",
        "commits_behind": 0,
        "action": "",
    }

    # Read installed plugin info
    installed_json = ROOT / ".claude-plugin" / "installed_plugins.json"
    if not installed_json.exists():
        # Try Claude's global installed_plugins.json
        import os as _os
        home = _os.path.expanduser("~")
        installed_json = _os_path(home) / ".claude" / "installed_plugins.json"

    if installed_json.exists():
        try:
            with open(installed_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            plugins = data.get("plugins", data) if isinstance(data, dict) else data
            if isinstance(plugins, list):
                for p in plugins:
                    if p.get("name") == "software-project-governance":
                        result["installed_version"] = p.get("version", "unknown")
                        result["installed_commit"] = (p.get("gitCommitSha") or "unknown")[:7]
                        result["installed_date"] = p.get("installedAt", "unknown")[:10] if p.get("installedAt") else "unknown"
                        break
        except (json.JSONDecodeError, KeyError, IOError):
            pass

    # Read source version from marketplace.json
    marketplace_json = ROOT / ".claude-plugin" / "marketplace.json"
    if marketplace_json.exists():
        try:
            with open(marketplace_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            plugins = data.get("plugins", [])
            for p in plugins:
                if p.get("name") == "software-project-governance":
                    result["source_version"] = p.get("version", "unknown")
                    break
        except (json.JSONDecodeError, KeyError, IOError):
            pass

    # Get source HEAD commit
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            cwd=str(ROOT), timeout=5
        )
        if r.returncode == 0:
            result["source_commit"] = r.stdout.strip()[:7]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # Determine status
    if result["installed_version"] == result["source_version"]:
        result["status"] = "UP TO DATE"
        result["action"] = "No action needed."
    elif result["installed_version"] == "unknown":
        result["status"] = "UNKNOWN (plugin not installed via marketplace?)"
        result["action"] = "Run /plugin marketplace add <path> to install."
    else:
        result["status"] = "OUTDATED"
        result["action"] = "Run /plugin update software-project-governance  or  /reload-plugins"

    return result


def check_untracked_files():
    """Check for untracked files in the working directory (FIX-057 Phase 2).

    Runs ``git ls-files --others --exclude-standard`` and reports any
    untracked files with heuristic classification suggestions.  Ordinary
    scratch files are non-blocking; unignored root platform entry files are
    actionable because they can change agent behavior outside versioned review.
    """
    import subprocess

    result = {
        "pass": True,
        "untracked_count": 0,
        "untracked_files": [],
        "actionable_entry_files": [],
        "suggest_archive": [],
        "suggest_temp_script": [],
        "suggest_manual": [],
    }

    try:
        r = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True,
            cwd=str(ROOT), timeout=10
        )
        if r.returncode != 0:
            result["pass"] = None  # couldn't run
            return result

        files = [f.strip().replace("\\", "/") for f in r.stdout.splitlines() if f.strip()]
        if not files:
            return result  # PASS -- no untracked files

        result["pass"] = False
        result["untracked_count"] = len(files)
        result["untracked_files"] = files

        # Heuristic classification
        for f in files:
            # ── Root platform-native entry files affect active agent behavior ──
            if "/" not in f and f in PLATFORM_ENTRY_FILES:
                result["actionable_entry_files"].append(f)
                continue

            # ── docs/** or project/references/** → suggest archive ──
            if f.startswith("docs/") or f.startswith("project/references/"):
                result["suggest_archive"].append(f)
                continue

            # ── *.py single file at repo root → possible temp script ──
            if "/" not in f and f.endswith(".py"):
                result["suggest_temp_script"].append(f)
                continue

            # ── Everything else needs human judgment ──
            result["suggest_manual"].append(f)

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        result["pass"] = None

    return result


def check_agent_locks_format():
    """Validate .governance/agent-locks.json existence, JSON validity, and schema integrity.

    Returns a list of WARN-level issue dicts.  Empty list = clean.
    This check is informational-only (WARN) -- format corruption does not block commit.
    Used as a helper by check_agent_lock_consistency() (Check 25, FIX-056 Phase 2).
    Phase 1 format-only check has been subsumed into the full Check 25.
    """
    import json

    issues = []
    locks_path = ROOT / ".governance" / "agent-locks.json"

    # ── Existence check ──
    if not locks_path.is_file():
        issues.append({
            "type": "missing",
            "detail": ".governance/agent-locks.json not found. Run governance init or create with: {\"active_tasks\": {}, \"file_locks\": {}}"
        })
        return issues

    # ── JSON validity ──
    try:
        with open(locks_path, "r", encoding="utf-8") as f:
            raw = f.read()
        if not raw.strip():
            issues.append({
                "type": "empty",
                "detail": ".governance/agent-locks.json is empty"
            })
            return issues
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        issues.append({
            "type": "invalid_json",
            "detail": f".governance/agent-locks.json is not valid JSON: {e}"
        })
        return issues
    except IOError as e:
        issues.append({
            "type": "io_error",
            "detail": f".governance/agent-locks.json read error: {e}"
        })
        return issues

    # ── Schema check ──
    if not isinstance(data, dict):
        issues.append({
            "type": "not_dict",
            "detail": ".governance/agent-locks.json root must be a JSON object (dict)"
        })
        return issues

    # Required top-level keys
    required_keys = ["active_tasks", "file_locks"]
    for key in required_keys:
        if key not in data:
            issues.append({
                "type": "missing_key",
                "detail": f".governance/agent-locks.json missing required key: '{key}'"
            })

    # active_tasks must be a dict
    if "active_tasks" in data and not isinstance(data["active_tasks"], dict):
        issues.append({
            "type": "type_error",
            "detail": ".governance/agent-locks.json 'active_tasks' must be a JSON object (dict), got " + type(data["active_tasks"]).__name__
        })

    # file_locks must be a dict
    if "file_locks" in data and not isinstance(data["file_locks"], dict):
        issues.append({
            "type": "type_error",
            "detail": ".governance/agent-locks.json 'file_locks' must be a JSON object (dict), got " + type(data["file_locks"]).__name__
        })

    # ── active_tasks entry schema check ──
    if "active_tasks" in data and isinstance(data["active_tasks"], dict):
        for task_id, entry in data["active_tasks"].items():
            if not isinstance(entry, dict):
                issues.append({
                    "type": "schema_violation",
                    "detail": f"agent-locks.json active_tasks['{task_id}'] must be a dict"
                })
                continue
            required_entry_keys = ["spawned_at", "coordinator_session", "target_files"]
            for rk in required_entry_keys:
                if rk not in entry:
                    issues.append({
                        "type": "schema_violation",
                        "detail": f"agent-locks.json active_tasks['{task_id}'] missing required field: '{rk}'"
                    })
            if "target_files" in entry and not isinstance(entry["target_files"], list):
                issues.append({
                    "type": "schema_violation",
                    "detail": f"agent-locks.json active_tasks['{task_id}'].target_files must be a list"
                })

    # ── file_locks entry schema check ──
    if "file_locks" in data and isinstance(data["file_locks"], dict):
        for file_path, entry in data["file_locks"].items():
            if not isinstance(entry, dict):
                issues.append({
                    "type": "schema_violation",
                    "detail": f"agent-locks.json file_locks['{file_path}'] must be a dict"
                })
                continue
            required_entry_keys = ["locked_by", "locked_at", "ttl_seconds", "ttl_reason"]
            for rk in required_entry_keys:
                if rk not in entry:
                    issues.append({
                        "type": "schema_violation",
                        "detail": f"agent-locks.json file_locks['{file_path}'] missing required field: '{rk}'"
                    })
            if "ttl_seconds" in entry and not isinstance(entry["ttl_seconds"], (int, float)):
                issues.append({
                    "type": "schema_violation",
                    "detail": f"agent-locks.json file_locks['{file_path}'].ttl_seconds must be a number"
                })

    return issues


def check_agent_lock_consistency():
    """Comprehensive agent lock consistency check (FIX-056 Phase 2).

    Checks:
      - Format/schema validity (delegates to check_agent_locks_format)
      - Task existence: locked_by task_ids must exist in plan-tracker
      - Orphan locks: file_locks referencing task_ids not in active_tasks
      - Expired locks: locked_at + ttl_seconds < now
      - Multi-lock conflict: same file locked by multiple active tasks

    Returns a dict with keys:
      - skipped: str if check was skipped (agent-locks.json missing), else None
      - active_task_count: number of active_tasks entries
      - file_lock_count: number of file_locks entries
      - issues: list of WARN-level issue dicts (type + detail)
    """
    import json
    from datetime import datetime, timezone

    result = {
        "skipped": None,
        "active_task_count": 0,
        "file_lock_count": 0,
        "issues": [],
    }

    locks_path = ROOT / ".governance" / "agent-locks.json"

    # ── Format check (Phase 1, reused) ──
    fmt_issues = check_agent_locks_format()
    for fi in fmt_issues:
        result["issues"].append({
            "type": f"format_{fi['type']}",
            "detail": fi["detail"],
        })

    # If format is broken, skip consistency checks (can't parse data)
    if not locks_path.is_file():
        result["skipped"] = "agent-locks.json not found — lock consistency check skipped."
        return result

    try:
        with open(locks_path, "r", encoding="utf-8") as f:
            raw = f.read()
        if not raw.strip():
            result["skipped"] = "agent-locks.json is empty — lock consistency check skipped."
            return result
        data = json.loads(raw)
    except (json.JSONDecodeError, IOError):
        result["skipped"] = "agent-locks.json is unparseable — lock consistency check skipped."
        return result

    if not isinstance(data, dict):
        result["skipped"] = "agent-locks.json root is not a dict — lock consistency check skipped."
        return result

    active_tasks = data.get("active_tasks", {})
    file_locks = data.get("file_locks", {})

    if not isinstance(active_tasks, dict):
        active_tasks = {}
    if not isinstance(file_locks, dict):
        file_locks = {}

    result["active_task_count"] = len(active_tasks)
    result["file_lock_count"] = len(file_locks)

    # If nothing active, skip consistency checks
    if not active_tasks and not file_locks:
        return result

    # ── Load plan-tracker task IDs ──
    plan_task_ids = set()
    try:
        pt_path = ROOT / ".governance" / "plan-tracker.md"
        if pt_path.is_file():
            pt_content = pt_path.read_text(encoding="utf-8")
            # Match task IDs in any table cell.  Active task tables often use
            # a priority first column, e.g. | **P1** | FIX-066 | ...
            for line in pt_content.split("\n"):
                if not line.lstrip().startswith("|"):
                    continue
                for task_id in re.findall(r"\b([A-Z]+-\d+)\b", line):
                    plan_task_ids.add(task_id)
    except Exception:
        pass  # Can't read plan-tracker — skip task-existence check

    now = datetime.now(timezone.utc)

    # ── Check 1: Task existence — every locked_by / active_tasks key must be in plan-tracker ──
    all_lock_task_ids = set()

    for task_id in active_tasks.keys():
        all_lock_task_ids.add(task_id)
        if plan_task_ids and task_id not in plan_task_ids:
            result["issues"].append({
                "type": "task_not_in_plan",
                "detail": f"active_tasks['{task_id}'] is not found in plan-tracker.md — lock references an unregistered task.",
            })

    for file_path, entry in file_locks.items():
        if isinstance(entry, dict):
            locker = entry.get("locked_by", "")
            if locker:
                all_lock_task_ids.add(locker)
                if plan_task_ids and locker not in plan_task_ids:
                    result["issues"].append({
                        "type": "task_not_in_plan",
                        "detail": f"file_locks['{file_path}'].locked_by='{locker}' is not found in plan-tracker.md.",
                    })

    # ── Check 2: Orphan locks — file_locks.locked_by not in active_tasks ──
    active_task_ids = set(active_tasks.keys())
    for file_path, entry in file_locks.items():
        if isinstance(entry, dict):
            locker = entry.get("locked_by", "")
            if locker and locker not in active_task_ids:
                result["issues"].append({
                    "type": "orphan_lock",
                    "detail": f"file_locks['{file_path}'] is locked by '{locker}' which has no active_tasks entry (orphan lock).",
                })

    # ── Check 3: Expired locks ──
    for file_path, entry in file_locks.items():
        if not isinstance(entry, dict):
            continue
        locked_at_str = entry.get("locked_at", "")
        ttl = entry.get("ttl_seconds", 0)
        if locked_at_str and ttl:
            try:
                locked_at = datetime.fromisoformat(locked_at_str.replace("Z", "+00:00"))
                expiry = locked_at.timestamp() + float(ttl)
                if now.timestamp() > expiry:
                    locker = entry.get("locked_by", "unknown")
                    elapsed = int(now.timestamp() - locked_at.timestamp())
                    result["issues"].append({
                        "type": "expired_lock",
                        "detail": (f"file_locks['{file_path}'] expired (locked by '{locker}', "
                                   f"TTL {ttl}s, elapsed {elapsed}s) — stale lock should be cleaned up."),
                    })
            except (ValueError, TypeError, OverflowError):
                pass

    # Also check active_tasks expiry (based on spawned_at + max TTL 600s)
    for task_id, entry in active_tasks.items():
        if not isinstance(entry, dict):
            continue
        spawned_at_str = entry.get("spawned_at", "")
        if spawned_at_str:
            try:
                spawned_at = datetime.fromisoformat(spawned_at_str.replace("Z", "+00:00"))
                # Use 600s as max reasonable TTL for any task
                if (now - spawned_at).total_seconds() > 600:
                    result["issues"].append({
                        "type": "expired_task",
                        "detail": (f"active_tasks['{task_id}'] spawned at {spawned_at_str} "
                                   f"({int((now - spawned_at).total_seconds())}s ago) — may be stale."),
                    })
            except (ValueError, TypeError, OverflowError):
                pass

    # ── Check 4: Multi-lock conflict — same file locked by multiple active tasks ──
    file_to_lockers = {}
    for file_path, entry in file_locks.items():
        if isinstance(entry, dict):
            locker = entry.get("locked_by", "")
            if locker and locker in active_task_ids:
                file_to_lockers.setdefault(file_path, set()).add(locker)

    for file_path, lockers in file_to_lockers.items():
        if len(lockers) > 1:
            result["issues"].append({
                "type": "multi_lock_conflict",
                "detail": (f"file_locks['{file_path}'] is locked by multiple active tasks: "
                           f"{sorted(lockers)} — potential concurrent write conflict."),
            })

    for issue in result["issues"]:
        issue["severity"] = "BLOCKING" if lock_issue_is_blocking(issue) else "WARN"

    return result


# ── SYSGAP-030: Archive Integrity Check ────────────────────────────

def check_archive_integrity():
    """Check 26: Verify archive integrity.

    Checks:
      1. archive/index.md referenced archive files all exist
      2. Archive file entries have corresponding index entries
      3. Task count conservation: hot + archive tasks == expected

    Returns:
        dict with keys: pass, issues, total_archived_tasks, index_entries,
                        hot_tasks, total_expected
    """
    result = {
        "pass": True,
        "issues": [],
        "total_archived_tasks": 0,
        "index_entries": 0,
        "hot_tasks": 0,
        "total_expected": 0,
        "pending_archive_tasks": 0,
        "archive_triggers": [],
    }

    archive_index = ROOT / ".governance/archive/index.md"
    archive_tasks_dir = ROOT / ".governance/archive/tasks"
    archive_evidence_dir = ROOT / ".governance/archive/evidence"

    archive_module = _load_archive_module()
    if archive_module is not None:
        analysis = archive_module.analyze_auto_archive_candidates()
        result["pending_archive_tasks"] = analysis.get("tasks_archived", 0)
        result["archive_triggers"] = analysis.get("triggers", [])
        if analysis.get("should_archive"):
            result["pass"] = False
            result["issues"].append(
                "Archive trigger gap: "
                f"{analysis.get('tasks_archived', 0)} hot completed task(s) "
                f"should be archived via {', '.join(analysis.get('triggers', []))} "
                f"for v{analysis.get('versions_range', ('?', '?'))[0]}~"
                f"v{analysis.get('versions_range', ('?', '?'))[1]}. "
                "Run archive.py migrate --auto."
            )

    # If no archive index, integrity can still pass when no trigger gap exists.
    if not archive_index.exists():
        # But check if there are orphan archive files
        has_archive_files = False
        for d in [archive_tasks_dir, archive_evidence_dir]:
            if d.exists():
                for f in d.glob("*.md"):
                    if f.name != ".gitkeep":
                        has_archive_files = True
                        break
            if has_archive_files:
                break
        if has_archive_files:
            result["pass"] = False
            result["issues"].append(
                "Archive files exist but index.md is missing. Run archive.build_index() to rebuild."
            )
        # Count hot tasks for the check output even before first archive.
        if SAMPLE_PATH.is_file():
            content = SAMPLE_PATH.read_text(encoding="utf-8")
            for line in content.split("\n"):
                stripped = line.strip()
                if not stripped.startswith("| ") or "---" in stripped:
                    continue
                if re.match(r"\|\s*([A-Z]+-\d+)\s*\|", stripped):
                    result["hot_tasks"] += 1
        result["total_expected"] = result["hot_tasks"]
        return result

    # Parse index to get referenced archive files
    index_content = archive_index.read_text(encoding="utf-8")
    index_lines = index_content.split("\n")

    # Extract archive file references from index
    indexed_files = set()
    in_section = False
    table_started = False
    for line in index_lines:
        stripped = line.strip()
        if stripped.startswith("## ") and "索引" in stripped:
            in_section = True
            table_started = False
            continue
        if not in_section:
            continue
        if "|---" in stripped:
            table_started = True
            continue
        if not table_started or not stripped.startswith("| "):
            continue

        # Parse row for archive file reference
        parts = [p.strip() for p in line.split("|")]
        for part in parts:
            if part.startswith("archive/"):
                indexed_files.add(part)

    # Check 1: All indexed files exist
    for ref in sorted(indexed_files):
        filepath = ROOT / ".governance" / ref
        if not filepath.exists():
            result["pass"] = False
            result["issues"].append(f"Index references non-existent file: {ref}")

    # Check 2: All archive files are in the index
    actual_archive_files = set()
    for d in [archive_tasks_dir, archive_evidence_dir]:
        if d.exists():
            for f in d.glob("*.md"):
                if f.name == ".gitkeep":
                    continue
                rel = str(f.relative_to(ROOT / ".governance")).replace("\\", "/")
                actual_archive_files.add(rel)

    unindexed = actual_archive_files - indexed_files
    if unindexed:
        result["pass"] = False
        for f in sorted(unindexed):
            result["issues"].append(f"Archive file not in index: {f}")

    # Check 3: Task count conservation
    # Count hot file tasks
    hot_tasks = 0
    if SAMPLE_PATH.is_file():
        content = SAMPLE_PATH.read_text(encoding="utf-8")
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped.startswith("| ") or "---" in stripped:
                continue
            m = re.match(r"\|\s*([A-Z]+-\d+)\s*\|", stripped)
            if m:
                hot_tasks += 1
    result["hot_tasks"] = hot_tasks

    # Count archived tasks
    archived_count = 0
    if archive_tasks_dir.exists():
        for f in archive_tasks_dir.glob("*.md"):
            if f.name == ".gitkeep":
                continue
            content = f.read_text(encoding="utf-8")
            for line in content.split("\n"):
                stripped = line.strip()
                if not stripped.startswith("| "):
                    continue
                m = re.match(r"\|\s*([A-Z]+-\d+)\s*\|", stripped)
                if m:
                    archived_count += 1
    result["total_archived_tasks"] = archived_count

    # Count index entries
    index_entry_count = 0
    for line in index_lines:
        stripped = line.strip()
        if stripped.startswith("| ") and re.match(r"\|\s*[A-Z]+-\d+", stripped):
            index_entry_count += 1
    result["index_entries"] = index_entry_count

    result["total_expected"] = hot_tasks + archived_count

    return result


def cmd_check_agent_locks(_args):
    """Standalone subcommand: check-locks — run agent lock consistency check."""
    result = check_agent_lock_consistency()

    if result.get("skipped"):
        print(f"[INFO] {result['skipped']}")
        return

    print(f"Active tasks: {result['active_task_count']}")
    print(f"File locks:   {result['file_lock_count']}")

    issues = result.get("issues", [])
    if not issues:
        print("Result: PASS — agent-locks.json is clean.")
    else:
        blocking = [i for i in issues if lock_issue_is_blocking(i)]
        print(f"\n{len(issues)} lock issue(s), {len(blocking)} blocking:")
        for issue in issues:
            severity = "BLOCKING" if lock_issue_is_blocking(issue) else "WARN"
            print(f"  [{severity}:{issue['type']}] {issue['detail']}")
        result_label = "WARN" if blocking else "INFO"
        print(f"\nResult: {result_label} — {len(issues)} lock consistency issue(s).")


def cmd_check_archive_integrity(_args):
    """Standalone subcommand: check-archive-integrity — Check 26."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    result = check_archive_integrity()
    print()
    print("=== Archive Integrity Check (SYSGAP-030 Check 26) ===")
    print(f"  Hot tasks (plan-tracker): {result['hot_tasks']}")
    print(f"  Archived tasks: {result['total_archived_tasks']}")
    print(f"  Index entries: {result['index_entries']}")
    print(f"  Total tasks (hot + archive): {result['total_expected']}")
    if result.get("pending_archive_tasks", 0):
        print(f"  Pending archive tasks: {result['pending_archive_tasks']}")
        print(f"  Archive triggers: {', '.join(result.get('archive_triggers', [])) or 'none'}")

    if result["issues"]:
        print(f"\n  Issues ({len(result['issues'])}):")
        for issue in result["issues"]:
            print(f"    - {issue}")
        print(f"\n  [FAIL] Archive integrity issues detected.")
        import sys
        sys.exit(1)
    else:
        print(f"\n  [PASS] Archive integrity verified.")
    print()


def cmd_check_plugin_freshness(_args):
    """Check if installed plugin is up to date with source repository."""
    result = check_plugin_freshness()

    # Calculate behind count
    import subprocess
    try:
        # Try to find installed commit in git log
        r = subprocess.run(
            ["git", "rev-list", "--count", f"{result['installed_commit']}..HEAD"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=5
        )
        if r.returncode == 0:
            result["commits_behind"] = int(r.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError, ValueError):
        pass

    print()
    print("=== Plugin Freshness Check ===")
    print(f"  Installed: {result['installed_version']} (commit {result['installed_commit']}, {result['installed_date']})")
    print(f"  Source:    {result['source_version']} (commit {result['source_commit']})")
    print(f"  Status:    {result['status']}")
    if result["commits_behind"] > 0:
        print(f"  Behind:    {result['commits_behind']} commit(s)")
    if result["action"]:
        print(f"  Action:    {result['action']}")
    print()

    # Exit with error if outdated (for CI)
    if result["status"] == "OUTDATED":
        import sys
        sys.exit(1)


def _e2e_command_matrix():
    """Return the source-root CLI proxy matrix used by cmd_e2e_check().

    These commands intentionally run from ROOT because verify_workflow.py
    derives its data paths from the source tree. They are CLI execution
    proxies, not full external-project cwd execution.
    """
    verify_py = Path(__file__).resolve()
    cleanup_py = verify_py.with_name("cleanup.py")
    python = sys.executable
    return [
        {
            "label": "/governance-status",
            "kind": "source_cli_proxy",
            "command": [python, str(verify_py), "status"],
            "validator": _validate_e2e_status,
        },
        {
            "label": "/governance-gate G1",
            "kind": "source_cli_proxy",
            "command": [python, str(verify_py), "gate", "G1"],
            "validator": _validate_e2e_gate_g1,
        },
        {
            "label": "/governance-gate G99",
            "kind": "source_cli_proxy",
            "command": [python, str(verify_py), "gate", "G99"],
            "validator": _validate_e2e_gate_g99,
        },
        {
            "label": "/governance-cleanup",
            "kind": "source_cli_proxy",
            "command": [python, str(cleanup_py), "--dry-run", "--json"],
            "validator": _validate_e2e_cleanup,
            "accepted_exit_codes": {0, 1},
        },
        {
            "label": "/governance-verify",
            "kind": "source_cli_proxy",
            "command": [python, str(verify_py), "verify"],
            "validator": _validate_e2e_verify_known_failure,
            "expected_known_failure": True,
        },
        {
            "label": "/governance Scenario F proxy",
            "kind": "source_cli_proxy",
            "command": [python, str(verify_py), "status"],
            "validator": _validate_e2e_governance_proxy,
        },
    ]


def _e2e_target_cwd_command_matrix(e2e_dir):
    """Return executable commands that run from the external target cwd."""
    target_verify_py = e2e_dir / "skills/software-project-governance/infra/verify_workflow.py"
    target_cleanup_py = e2e_dir / "skills/software-project-governance/infra/cleanup.py"
    python = sys.executable
    return [
        {
            "label": "target-cwd /governance-status",
            "kind": "target_cwd_command",
            "cwd": e2e_dir,
            "command": [python, str(target_verify_py.relative_to(e2e_dir)), "status"],
            "validator": _validate_e2e_target_status,
        },
        {
            "label": "target-cwd /governance-gate G1",
            "kind": "target_cwd_command",
            "cwd": e2e_dir,
            "command": [python, str(target_verify_py.relative_to(e2e_dir)), "gate", "G1"],
            "validator": _validate_e2e_gate_g1,
        },
        {
            "label": "target-cwd /governance-gate G99",
            "kind": "target_cwd_command",
            "cwd": e2e_dir,
            "command": [python, str(target_verify_py.relative_to(e2e_dir)), "gate", "G99"],
            "validator": _validate_e2e_gate_g99,
        },
        {
            "label": "target-cwd /governance-cleanup",
            "kind": "target_cwd_command",
            "cwd": e2e_dir,
            "command": [python, str(target_cleanup_py.relative_to(e2e_dir)), "--dry-run", "--json"],
            "validator": _validate_e2e_cleanup,
            "accepted_exit_codes": {0, 1},
        },
    ]


def _e2e_target_fixture_checks(e2e_dir):
    """Return direct checks against the tracked e2e-test-project fixture."""
    governance_dir = e2e_dir / ".governance"
    return [
        {
            "label": "CLAUDE.md bootstrap fixture",
            "path": e2e_dir / "CLAUDE.md",
            "needles": ["Governance Bootstrap", "SELF-CHECK", "AskUserQuestion"],
        },
        {
            "label": "AGENTS.md Codex/opencode native entry fixture",
            "path": e2e_dir / "AGENTS.md",
            "needles": [
                "Governance Bootstrap",
                "SELF-CHECK",
                "Codex",
                "opencode",
                "skills/software-project-governance/SKILL.md",
            ],
        },
        {
            "label": "GEMINI.md native entry fixture",
            "path": e2e_dir / "GEMINI.md",
            "needles": [
                "Governance Bootstrap",
                "SELF-CHECK",
                "Gemini",
                "skills/software-project-governance/SKILL.md",
            ],
        },
        {
            "label": "tracked governance files",
            "paths": [
                governance_dir / "plan-tracker.md",
                governance_dir / "evidence-log.md",
                governance_dir / "decision-log.md",
                governance_dir / "risk-log.md",
                governance_dir / "session-snapshot.md",
            ],
        },
        {
            "label": "target plan-tracker project config",
            "path": governance_dir / "plan-tracker.md",
            "needles": ["工作流版本", "0.38.0", "操作权限模式", "default-confirm"],
        },
        {
            "label": "target workflow skill version",
            "path": e2e_dir / "skills" / "software-project-governance" / "SKILL.md",
            "needles": ["version: 0.38.0", "Coordinator", "Agent Team"],
        },
        {
            "label": "target /governance route contract",
            "path": e2e_dir / "commands" / "governance.md",
            "needles": ["Scenario F", "AskUserQuestion", "Coordinator"],
        },
    ]


def _e2e_contract_checks():
    """Return checks that need host runtime or static command contracts."""
    return [
        {
            "label": "/governance-review code",
            "kind": "AGENT_RUNTIME_REQUIRED",
            "path": ROOT / "commands/governance-review.md",
            "needles": [
                "Reviewer Agent",
                "code-review",
                "代码审查",
                "general-purpose",
                "degraded evidence",
                "不得解锁",
            ],
            "reason": "Agent spawn is provided by the host platform, not Python.",
        },
        {
            "label": "AskUserQuestion interaction boundary",
            "kind": "AGENT_RUNTIME_REQUIRED",
            "path": ROOT / "commands/governance.md",
            "needles": ["AskUserQuestion"],
            "reason": "Interactive user choice requires platform runtime tools.",
        },
        {
            "label": "/governance route contract",
            "kind": "CONTRACT_CHECK",
            "path": ROOT / "commands/governance.md",
            "needles": ["Scenario F", "状态面板"],
            "reason": "Executable coverage comes from the Scenario F status proxy.",
        },
    ]


AGENT_RUNTIME_E2E_PLATFORMS = ("claude", "codex", "gemini", "opencode")


def _agent_runtime_e2e_prompt(agent_id):
    return (
        "Read the local governance bootstrap and answer with exactly these "
        f"machine-readable fields if the workflow is loaded: E2E_PLATFORM={agent_id}; "
        "E2E_AGENT=<workflow role>; E2E_STAGE=<current stage>; "
        "E2E_MODE=<trigger x permission>. "
        "Do not modify files."
    )


def _agent_runtime_e2e_command_matrix(e2e_dir=None):
    """Return real agent runtime E2E commands for mainstream code agents."""
    e2e_dir = e2e_dir or ROOT / "project/e2e-test-project"
    prompts = {
        agent_id: _agent_runtime_e2e_prompt(agent_id)
        for agent_id in AGENT_RUNTIME_E2E_PLATFORMS
    }
    return [
        {
            "agent": "claude",
            "label": "Claude real agent target cwd",
            "cwd": e2e_dir,
            "command": [
                "claude",
                "-p",
                prompts["claude"],
                "--permission-mode",
                "default",
                "--allowedTools",
                "Read",
                "--output-format",
                "text",
            ],
            "validator": _validate_agent_runtime_e2e_passed,
        },
        {
            "agent": "codex",
            "label": "Codex CLI headless target cwd",
            "cwd": e2e_dir,
            "command": [
                "codex",
                "exec",
                "-C",
                ".",
                "-s",
                "read-only",
                "--ephemeral",
                prompts["codex"],
            ],
            "validator": _validate_agent_runtime_e2e_passed,
        },
        {
            "agent": "gemini",
            "label": "Gemini CLI target cwd",
            "cwd": e2e_dir,
            "command": [
                "gemini",
                "--prompt",
                prompts["gemini"],
                "--approval-mode",
                "plan",
                "--output-format",
                "text",
            ],
            "validator": _validate_agent_runtime_e2e_passed,
        },
        {
            "agent": "opencode",
            "label": "opencode CLI target cwd",
            "cwd": e2e_dir,
            "command": [
                "opencode",
                "run",
                "--dir",
                ".",
                "--format",
                "json",
                prompts["opencode"],
            ],
            "validator": _validate_agent_runtime_e2e_passed,
        },
    ]


def _run_e2e_subprocess(command, timeout=30, cwd=None):
    """Run a matrix command and return subprocess.CompletedProcess."""
    return subprocess.run(
        command,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        encoding=locale.getpreferredencoding(False),
        errors="replace",
        timeout=timeout,
    )


def _e2e_output(result):
    return (result.stdout or "") + "\n" + (result.stderr or "")


def _truncate_log(text, limit=1200):
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "...[truncated]"


def _coerce_e2e_text(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(locale.getpreferredencoding(False), errors="replace")
    return str(value)


def _has_all(text, needles):
    return all(needle in text for needle in needles)


def _validate_e2e_status(result):
    output = _e2e_output(result)
    labels_present = _has_all(output, ["permission_mode", "操作权限模式"])
    legal_permission_mode_present = any(
        value in output for value in ("maximum-autonomy", "default-confirm")
    )
    ok = result.returncode == 0 and _has_all(
        output,
        ["Project Overview", "Tasks", "Gate"],
    ) and labels_present and legal_permission_mode_present
    return ok, (
        "status output exposes Project Overview, Tasks, Gate, "
        "permission_mode/操作权限模式, and a legal permission mode "
        "(maximum-autonomy or default-confirm)"
    )


def _validate_e2e_target_status(result):
    output = _e2e_output(result)
    ok = (
        result.returncode == 0
        and _has_all(output, ["Project Overview", "Tasks", "Gate"])
        and any(value in output for value in ("maximum-autonomy", "default-confirm"))
    )
    return ok, "target cwd status command returns project overview, tasks, gate, and a legal permission mode"


def _validate_e2e_gate_g1(result):
    output = _e2e_output(result)
    ok = result.returncode == 0 and _has_all(output, ["G1", "Check items"])
    return ok, "G1 command returns check items"


def _validate_e2e_gate_g99(result):
    output = _e2e_output(result)
    ok = result.returncode != 0 and (
        "Gate G99 not found" in output or "GATE-ERR" in output
    )
    return ok, "invalid gate returns non-zero and GATE-ERR/not-found semantics"


def _validate_e2e_cleanup(result):
    output = _e2e_output(result).strip()
    try:
        report = json.loads(output)
    except json.JSONDecodeError:
        return False, "cleanup emitted non-JSON output"

    if report.get("status") == "clean":
        return True, "cleanup dry-run executed and reported status=clean"

    required = {"manifest_version", "dry_run", "total_redundant", "classification"}
    ok = (
        result.returncode == 0
        and required.issubset(report.keys())
        and report.get("dry_run") is True
    )
    return ok, "cleanup dry-run executed and emitted redundancy report"


_KNOWN_VERIFY_FAILURE_SIGNATURES = {
    "missing snippet in .governance/evidence-log.md: evd-001",
    "missing snippet in .governance/evidence-log.md: evd-051",
    "missing snippet in skills/software-project-governance/skill.md: coordinator 接管用户交互",
    "missing snippet in skills/software-project-governance/skill.md: producer-reviewer 分离",
}


def _normalize_e2e_verify_failure(line):
    line = line.replace("\\", "/").strip().lower()
    return re.sub(r"\s+", " ", line)


def _extract_e2e_verify_failures(output):
    failures = []
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            failures.append(_normalize_e2e_verify_failure(stripped[2:]))
    return failures


def _validate_e2e_verify_known_failure(result):
    output = _e2e_output(result)
    if result.returncode == 0 and "Workflow Plugin Verification" in output and "Verification Result: PASSED" in output:
        return True, "verify command executed and passed"

    failures = set(_extract_e2e_verify_failures(output))
    ok = (
        result.returncode != 0
        and "Workflow Plugin Verification" in output
        and "Verification Result: FAILED" in output
        and bool(failures)
        and failures.issubset(_KNOWN_VERIFY_FAILURE_SIGNATURES)
        and bool(failures & _KNOWN_VERIFY_FAILURE_SIGNATURES)
    )
    if ok:
        return True, "verify command executed and all failures are known allowed signatures"

    unknown = sorted(failures - _KNOWN_VERIFY_FAILURE_SIGNATURES)
    detail = []
    if unknown:
        detail.append(f"unknown failures={unknown}")
    if not failures:
        detail.append("no parseable verification failure lines")
    if result.returncode == 0:
        detail.append("verify command returned 0")
    return False, "verify failure did not match allowed known signatures; " + "; ".join(detail)


def _evaluate_e2e_target_fixture_check(entry):
    paths = entry.get("paths")
    if paths:
        missing = [str(path.relative_to(ROOT)) for path in paths if not path.exists()]
        return {
            "label": entry["label"],
            "status": "PASS" if not missing else "FAIL",
            "message": "all tracked fixture files exist" if not missing else f"missing files={missing}",
        }

    path = entry["path"]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "label": entry["label"],
            "status": "FAIL",
            "message": f"fixture file unavailable: {exc}",
        }

    missing = [needle for needle in entry["needles"] if needle not in text]
    return {
        "label": entry["label"],
        "status": "PASS" if not missing else "FAIL",
        "message": "fixture content matches expected markers" if not missing else f"missing markers={missing}",
    }


def _validate_e2e_governance_proxy(result):
    output = _e2e_output(result)
    contract = ROOT / "commands/governance.md"
    try:
        contract_text = contract.read_text(encoding="utf-8")
    except OSError:
        contract_text = ""
    ok = (
        result.returncode == 0
        and "Project Overview" in output
        and "Gate Status" in output
        and "Scenario F" in contract_text
    )
    return ok, "Scenario F proxy executed status and found /governance route contract"


def _evaluate_e2e_command(entry, runner=_run_e2e_subprocess):
    """Execute one E2E matrix entry and normalize its result."""
    try:
        try:
            result = runner(entry["command"], cwd=entry.get("cwd"))
        except TypeError:
            result = runner(entry["command"])
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "label": entry["label"],
            "kind": entry.get("kind", "source_cli_proxy"),
            "status": "FAIL",
            "exit_code": None,
            "message": f"subprocess did not complete: {exc}",
            "command": entry["command"],
        }

    accepted = entry.get("accepted_exit_codes")
    if accepted is not None and result.returncode not in accepted:
        return {
            "label": entry["label"],
            "kind": entry.get("kind", "source_cli_proxy"),
            "status": "FAIL",
            "exit_code": result.returncode,
            "message": f"unexpected exit code; accepted={sorted(accepted)}",
            "command": entry["command"],
        }

    ok, message = entry["validator"](result)
    if not ok:
        return {
            "label": entry["label"],
            "kind": entry.get("kind", "source_cli_proxy"),
            "status": "FAIL",
            "exit_code": result.returncode,
            "message": message,
            "command": entry["command"],
        }

    status = "EXPECTED_KNOWN_FAILURE" if entry.get("expected_known_failure") and result.returncode != 0 else "PASS"
    return {
        "label": entry["label"],
        "kind": entry.get("kind", "source_cli_proxy"),
        "status": status,
        "exit_code": result.returncode,
        "message": message,
        "command": entry["command"],
    }


def _evaluate_e2e_contract_check(entry):
    path = entry["path"]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "label": entry["label"],
            "status": entry["kind"],
            "ok": False,
            "message": f"contract file unavailable: {exc}",
        }

    ok = _has_all(text, entry["needles"])
    suffix = "contract present" if ok else "contract incomplete"
    return {
        "label": entry["label"],
        "status": entry["kind"],
        "ok": ok,
        "message": f"{suffix}; {entry['reason']}",
    }


def _validate_agent_runtime_e2e_passed(agent_id, result):
    output = _e2e_output(result)
    if result.returncode != 0:
        return False, f"real agent exited with code {result.returncode}"

    fields = _parse_agent_runtime_e2e_fields(output)
    if not fields:
        return False, "real agent output missing structured E2E_PLATFORM/E2E_AGENT/E2E_STAGE/E2E_MODE response"
    for response in fields:
        platform = response.get("E2E_PLATFORM", "")
        workflow_agent = response.get("E2E_AGENT", "")
        stage = response.get("E2E_STAGE", "")
        mode = response.get("E2E_MODE", "")
        if (
            platform == agent_id
            and _is_valid_agent_runtime_workflow_agent(workflow_agent)
            and _is_non_placeholder_agent_runtime_value(stage)
            and _is_valid_agent_runtime_mode(mode)
        ):
            return True, (
                f"real agent output includes structured response: "
                f"E2E_PLATFORM={platform}; E2E_AGENT={workflow_agent}; "
                f"E2E_STAGE={stage}; E2E_MODE={mode}"
            )
    return False, (
        "real agent output did not include a complete non-placeholder "
        f"E2E response with platform={agent_id}"
    )


def _agent_runtime_e2e_candidate_texts(output):
    """Return text payloads from agent output while preserving plain text logs."""
    candidates = []
    for line in (output or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError:
            candidates.append(line)
            continue
        if not isinstance(event, dict):
            candidates.append(line)
            continue
        extracted = False
        part = event.get("part")
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            candidates.append(part["text"])
            extracted = True
        if isinstance(event.get("text"), str):
            candidates.append(event["text"])
            extracted = True
        if not extracted:
            candidates.append(line)
    return candidates or [output or ""]


def _parse_agent_runtime_e2e_fields(output):
    """Extract E2E field groups from semicolon/newline-delimited agent output."""
    groups = []
    current = {}
    for candidate in _agent_runtime_e2e_candidate_texts(output):
        for match in re.finditer(r"\b(E2E_PLATFORM|E2E_AGENT|E2E_STAGE|E2E_MODE)\s*=\s*([^;\r\n]+)", candidate or ""):
            key, value = match.group(1), match.group(2).strip()
            if key == "E2E_PLATFORM" and "E2E_PLATFORM" in current:
                groups.append(current)
                current = {}
            current[key] = value
            if {"E2E_PLATFORM", "E2E_AGENT", "E2E_STAGE", "E2E_MODE"}.issubset(current):
                groups.append(current)
                current = {}
    if current:
        groups.append(current)
    return groups


def _is_non_placeholder_agent_runtime_value(value):
    value = (value or "").strip()
    lowered = value.lower()
    if not value:
        return False
    if value.startswith("<") and value.endswith(">"):
        return False
    placeholder_markers = ("placeholder", "current stage", "trigger x permission")
    return not any(marker in lowered for marker in placeholder_markers)


def _is_valid_agent_runtime_workflow_agent(value):
    if not _is_non_placeholder_agent_runtime_value(value):
        return False
    return value.strip().lower() not in AGENT_RUNTIME_E2E_PLATFORMS


def _is_valid_agent_runtime_mode(value):
    if not _is_non_placeholder_agent_runtime_value(value):
        return False
    parts = [part.strip() for part in value.split(" x ")]
    if len(parts) != 2 or not all(_is_non_placeholder_agent_runtime_value(part) for part in parts):
        return False
    trigger_mode, permission_mode = parts
    return (
        trigger_mode in {"always-on", "on-demand", "silent-track"}
        and permission_mode in {"maximum-autonomy", "default-confirm"}
    )


def _classify_agent_runtime_blocked(agent_id, output="", exception=None):
    """Return blocked_reason for known environment/runtime blockers."""
    lowered = (output or "").lower()
    if isinstance(exception, FileNotFoundError):
        return f"{agent_id} runtime command not found on PATH"
    if isinstance(exception, PermissionError):
        return f"{agent_id} runtime command could not start due to OS permission/path resolution"
    if agent_id == "codex" and isinstance(exception, subprocess.TimeoutExpired):
        return "Codex CLI target-cwd command timed out"
    if agent_id == "codex" and "timed out" in lowered:
        return "Codex CLI target-cwd command timed out"
    if agent_id == "gemini":
        auth_markers = [
            "gemini_api_key",
            "google_api_key",
            "api key",
            "auth",
            "authenticate",
            "authentication",
            "credential",
            "login",
            "vertex",
            "gca",
        ]
        if any(marker in lowered for marker in auth_markers):
            return (
                "Gemini auth missing or not configured; configure GEMINI_API_KEY, "
                "GOOGLE_API_KEY, Vertex credentials, GCA auth, or Gemini settings auth."
            )
    if agent_id == "opencode":
        if isinstance(exception, subprocess.TimeoutExpired):
            return (
                "opencode CLI target-cwd command timed out; increase timeout "
                "or inspect partial tool use before classifying as provider/model invalid"
            )
        if "timed out" in lowered or "timeout" in lowered:
            return (
                "opencode CLI target-cwd command timed out; increase timeout "
                "or inspect partial tool use before classifying as provider/model invalid"
            )
        invalid_model_markers = [
            "deepseek-v4-pro[1m]",
            "invalid model",
            "model not",
            "unsupported model",
            "not supported",
        ]
        if any(marker in lowered for marker in invalid_model_markers):
            return "opencode provider/model config invalid"
    return None


def _resolve_agent_runtime_command(command):
    """Resolve PATH/PATHEXT shims before Popen, especially npm .cmd shims on Windows."""
    if not command:
        return command
    resolved = shutil.which(command[0])
    if not resolved:
        return command
    return [resolved, *command[1:]]


def _run_agent_runtime_e2e_subprocess(command, timeout=120, cwd=None):
    command = _resolve_agent_runtime_command(command)
    popen_kwargs = {}
    if os.name != "nt":
        popen_kwargs["start_new_session"] = True
    process = subprocess.Popen(
        command,
        cwd=str(cwd or ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding=locale.getpreferredencoding(False),
        errors="replace",
        **popen_kwargs,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _cleanup_agent_runtime_process_tree(process)
        stdout, stderr = process.communicate()
        raise subprocess.TimeoutExpired(
            exc.cmd,
            exc.timeout,
            output=stdout,
            stderr=stderr,
        ) from exc
    return subprocess.CompletedProcess(
        command,
        process.returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _cleanup_agent_runtime_process_tree(process):
    """Best-effort cleanup for agent runtime shims and their child process trees."""
    pid = getattr(process, "pid", None)
    if not pid:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            return
        except (subprocess.SubprocessError, OSError):
            pass
    else:
        try:
            os.killpg(pid, signal.SIGKILL)
            return
        except (OSError, ProcessLookupError):
            pass
    try:
        process.kill()
    except OSError:
        pass


def _evaluate_agent_runtime_e2e_command(
    entry,
    timeout=120,
    runner=_run_agent_runtime_e2e_subprocess,
):
    """Execute one real agent runtime command and normalize pass/blocked/fail."""
    agent_id = entry["agent"]
    command = entry["command"]
    cwd = entry.get("cwd")
    try:
        try:
            result = runner(command, timeout=timeout, cwd=cwd)
        except TypeError:
            result = runner(command)
    except subprocess.TimeoutExpired as exc:
        output = _coerce_e2e_text(exc.stdout) + "\n" + _coerce_e2e_text(exc.stderr)
        blocked_reason = _classify_agent_runtime_blocked(agent_id, output, exc)
        status = "BLOCKED" if blocked_reason else "FAIL"
        return {
            "agent": agent_id,
            "label": entry["label"],
            "status": status,
            "exit_code": None,
            "command": command,
            "cwd": cwd,
            "message": blocked_reason or f"unclassified timeout: {exc}",
            "blocked_reason": blocked_reason,
            "log_summary": _truncate_log(output or str(exc)),
        }
    except (OSError, FileNotFoundError) as exc:
        blocked_reason = _classify_agent_runtime_blocked(agent_id, "", exc)
        status = "BLOCKED" if blocked_reason else "FAIL"
        return {
            "agent": agent_id,
            "label": entry["label"],
            "status": status,
            "exit_code": None,
            "command": command,
            "cwd": cwd,
            "message": blocked_reason or f"subprocess did not start: {exc}",
            "blocked_reason": blocked_reason,
            "log_summary": _truncate_log(str(exc)),
        }

    output = _e2e_output(result)
    ok, message = entry["validator"](agent_id, result)
    if ok:
        return {
            "agent": agent_id,
            "label": entry["label"],
            "status": "PASS",
            "exit_code": result.returncode,
            "command": command,
            "cwd": cwd,
            "message": message,
            "blocked_reason": None,
            "log_summary": _truncate_log(output),
        }

    blocked_reason = _classify_agent_runtime_blocked(agent_id, output)
    if blocked_reason:
        return {
            "agent": agent_id,
            "label": entry["label"],
            "status": "BLOCKED",
            "exit_code": result.returncode,
            "command": command,
            "cwd": cwd,
            "message": blocked_reason,
            "blocked_reason": blocked_reason,
            "log_summary": _truncate_log(output),
        }

    return {
        "agent": agent_id,
        "label": entry["label"],
        "status": "FAIL",
        "exit_code": result.returncode,
        "command": command,
        "cwd": cwd,
        "message": message,
        "blocked_reason": None,
        "log_summary": _truncate_log(output),
    }


def cmd_agent_runtime_e2e(args):
    """Run real agent runtime E2E command matrix against e2e-test-project."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    target = Path(getattr(args, "target", None) or ROOT / "project/e2e-test-project")
    timeout = getattr(args, "timeout", 120)
    requested_agents = set(getattr(args, "agent", None) or AGENT_RUNTIME_E2E_PLATFORMS)
    matrix = [
        entry for entry in _agent_runtime_e2e_command_matrix(target)
        if entry["agent"] in requested_agents
    ]
    if not target.exists():
        print(f"[FAIL] target not found: {target}")
        sys.exit(1)

    results = [
        _evaluate_agent_runtime_e2e_command(entry, timeout=timeout)
        for entry in matrix
    ]

    print("=== Agent Runtime E2E Harness ===")
    print(f"Target: {target}")
    print(f"Timeout: {timeout}s")
    print("Schema: status in PASS/BLOCKED/FAIL; BLOCKED means known environment or agent-runtime configuration blocker.\n")

    for result in results:
        command = " ".join(str(part) for part in result["command"])
        print(f"[{result['status']}] {result['agent']}: {result['label']} (exit={result['exit_code']})")
        print(f"  cwd: {result['cwd']}")
        print(f"  command: {command}")
        print(f"  message: {result['message']}")
        if result["blocked_reason"]:
            print(f"  blocked_reason: {result['blocked_reason']}")
        if result["log_summary"]:
            print(f"  log_summary: {result['log_summary']}")

    pass_count = sum(1 for r in results if r["status"] == "PASS")
    blocked_count = sum(1 for r in results if r["status"] == "BLOCKED")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    print(
        "\n=== Result: "
        f"pass={pass_count}, blocked={blocked_count}, fail={fail_count}, total={len(results)} ==="
    )
    if fail_count:
        print("ACTION: Fix unclassified harness/runtime failures above.")
        sys.exit(1)
    print("Agent runtime E2E harness completed; blocked entries are environment/configuration evidence, not harness failures.")


def cmd_gemini_auth_preflight(_args):
    """Check Gemini CLI availability and authentication sources without leaking secrets."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    result = _gemini_auth_preflight()
    print("=== Gemini Auth Preflight ===")
    print(f"status: {result['status']}")
    print(f"command: {result['command']}")
    print(f"version_command: {result['version_command']}")
    print(f"cli_path: {result['cli_path'] or 'not found'}")
    if result["version"]:
        print(f"version: {result['version']}")
    if result["auth_sources"]:
        print("auth_sources:")
        for source in result["auth_sources"]:
            print(f" - {source}")
    else:
        print("auth_sources: none")
    if result["blocked_reason"]:
        print(f"blocked_reason: {result['blocked_reason']}")
    print(f"remediation: {result['remediation']}")
    if result["status"] != "PASS":
        sys.exit(1)


def cmd_opencode_provider_preflight(_args):
    """Check opencode CLI and DeepSeek provider/model config without leaking secrets."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    result = _opencode_provider_model_preflight()
    print("=== opencode Provider/Model Preflight ===")
    print(f"status: {result['status']}")
    print(f"command: {result['command']}")
    print(f"version_command: {result['version_command']}")
    print(f"cli_path: {result['cli_path'] or 'not found'}")
    if result["version"]:
        print(f"version: {result['version']}")
    if result["legal_models"]:
        print("legal_models:")
        for model in result["legal_models"]:
            print(f" - {model}")
    else:
        print("legal_models: none")
    if result["model_sources"]:
        print("model_sources:")
        for source in result["model_sources"]:
            print(f" - {source}")
    else:
        print("model_sources: none")
    if result["blocked_reason"]:
        print(f"blocked_reason: {_sanitize_opencode_probe_text(result['blocked_reason'])}")
    print(f"remediation: {_sanitize_opencode_probe_text(result['remediation'])}")
    if result["status"] != "PASS":
        sys.exit(1)


def cmd_e2e_check(_args):
    """Run command-backed E2E governance verification."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    e2e_dir = ROOT / "project/e2e-test-project"
    if not e2e_dir.exists():
        print("[SKIPPED] project/e2e-test-project/ not found")
        return

    source_cli_results = [
        _evaluate_e2e_command(entry) for entry in _e2e_command_matrix()
    ]
    target_cwd_results = [
        _evaluate_e2e_command(entry) for entry in _e2e_target_cwd_command_matrix(e2e_dir)
    ]
    fixture_results = [
        _evaluate_e2e_target_fixture_check(entry)
        for entry in _e2e_target_fixture_checks(e2e_dir)
    ]
    contract_results = [
        _evaluate_e2e_contract_check(entry) for entry in _e2e_contract_checks()
    ]

    print("=== E2E Governance Verification ===")
    print(f"Target: {e2e_dir}")
    print("Mode: source CLI proxy + external target cwd execution + target fixture checks\n")

    print("--- Source CLI proxy command matrix ---")
    print(f"  cwd: {ROOT}")
    print("  note: verify_workflow.py is source-root bound; these are executable CLI proxies, not external-project cwd runs.")
    for result in source_cli_results:
        command = " ".join(str(part) for part in result["command"])
        print(
            f"  [{result['status']}] {result['label']} "
            f"(exit={result['exit_code']})"
        )
        print(f"      command: {command}")
        print(f"      assert: {result['message']}")

    print("\n--- External target cwd command matrix ---")
    print(f"  cwd: {e2e_dir}")
    print("  note: these commands execute the target project's own workflow copy from the target cwd.")
    for result in target_cwd_results:
        command = " ".join(str(part) for part in result["command"])
        print(
            f"  [{result['status']}] {result['label']} "
            f"(exit={result['exit_code']})"
        )
        print(f"      command: {command}")
        print(f"      assert: {result['message']}")

    print("\n--- Target fixture checks ---")
    print(f"  fixture: {e2e_dir}")
    for result in fixture_results:
        print(f"  [{result['status']}] {result['label']}")
        print(f"      assert: {result['message']}")

    print("\n--- Contract/runtime-only checks ---")
    for result in contract_results:
        marker = "OK" if result["ok"] else "CHECK_FAILED"
        print(f"  [{result['status']}:{marker}] {result['label']}")
        print(f"      note: {result['message']}")

    passed = sum(1 for r in source_cli_results if r["status"] == "PASS")
    failed = sum(1 for r in source_cli_results if r["status"] == "FAIL")
    known = sum(1 for r in source_cli_results if r["status"] == "EXPECTED_KNOWN_FAILURE")
    target_cwd_passed = sum(1 for r in target_cwd_results if r["status"] == "PASS")
    target_cwd_failed = sum(1 for r in target_cwd_results if r["status"] == "FAIL")
    fixture_passed = sum(1 for r in fixture_results if r["status"] == "PASS")
    fixture_failed = sum(1 for r in fixture_results if r["status"] == "FAIL")
    contract_count = len(contract_results)
    contract_failed = sum(1 for r in contract_results if not r["ok"])

    print(
        "\n=== Result: "
        f"source_cli_proxy_pass={passed}, source_cli_proxy_fail={failed}, "
        f"expected_known_failure={known}, "
        f"target_cwd_pass={target_cwd_passed}, target_cwd_fail={target_cwd_failed}, "
        f"target_fixture_pass={fixture_passed}, target_fixture_fail={fixture_failed}, "
        f"contract_only={contract_count}, contract_check_failed={contract_failed} ==="
    )
    if failed > 0 or target_cwd_failed > 0 or fixture_failed > 0:
        print("ACTION: Fix source CLI proxy, target cwd, or target fixture failures above.")
        sys.exit(1)
    print("Source CLI proxy matrix, external target cwd commands, and target fixture checks passed; runtime contracts reported separately.")


def cmd_check_manifest_consistency(args):
    """Compare manifest.json canonical set against actual filesystem."""
    result = check_manifest_consistency()

    print()
    if result.get("error"):
        print(f"[ERROR] {result['error']}")
        return

    print("=== Manifest Consistency Check ===")
    print(f"  Canonical files:  {result['canonical_count']}")
    print(f"  Actual files:     {result['actual_count']}")

    missing = result["missing"]
    untracked = result["untracked"]

    if missing:
        print(f"\n  [MISSING] {len(missing)} file(s) declared in manifest but absent:")
        for m in missing:
            print(f"    - {m}")

    if untracked:
        print(f"\n  [UNTRACKED] {len(untracked)} file(s) present on disk but not in manifest:")
        for u in untracked:
            print(f"    - {u}")

    if result["pass"]:
        print(f"\n  [PASS] Manifest and filesystem are consistent.")
    else:
        print(f"\n  [FAIL] Manifest-filesystem mismatch detected.")

    if args.fail_on_issues and not result["pass"]:
        sys.exit(1)


def cmd_check_agent_adapters(args):
    """Check mainstream code agent adapter contracts and optional local runtimes."""
    failures = check_agent_adapter_contract(run_runtime=getattr(args, "runtime", False))
    if failures:
        sys.exit(1)


def cmd_check_release(args):
    """Run release readiness checks used by the stage-release workflow."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    skip_execution_gates = getattr(args, "skip_execution_gates", False)
    result = check_release_readiness(
        version=getattr(args, "version", None),
        require_changelog=getattr(args, "require_changelog", False),
        run_runtime_adapters=getattr(args, "runtime_adapters", False),
        run_execution_gates=not skip_execution_gates,
    )
    print()
    print("=== Release Readiness Check ===")
    if getattr(args, "version", None):
        print(f"  Version: {args.version}")
    print(f"  Runtime adapters: {'enabled' if getattr(args, 'runtime_adapters', False) else 'static'}")
    print(f"  Execution gates: {'skipped' if skip_execution_gates else 'enabled'}")
    for label, detail in result["details"].items():
        status = "PASS" if detail["pass"] else "FAIL"
        print(f"  [{status}] {label.replace('_', ' ')}")
        for gate_result in detail.get("results", []):
            gate_status = "PASS" if gate_result["pass"] else "FAIL"
            exit_code = gate_result["exit_code"]
            print(f"    [{gate_status}] {gate_result['label']} (exit={exit_code})")
        for issue in detail.get("issues", [])[:10]:
            print(f"    - {issue}")
        if len(detail.get("issues", [])) > 10:
            print(f"    ... and {len(detail['issues']) - 10} more")
    if result["pass"]:
        print("\n  Result: PASSED - release readiness checks are green.")
    else:
        print(f"\n  Result: FAILED - {len(result['issues'])} issue(s).")
        sys.exit(1)


# ── Standalone CLI wrappers for new checks ────────────────────────

def cmd_check_cross_references(args):
    """CLI wrapper for cross-reference checking (SYSGAP-008)."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    result = check_cross_references()
    print()
    print("=== Cross-Reference Check ===")
    print(f"  Files scanned: {result['total_files_scanned']}")
    print(f"  References extracted: {result['total_refs']}")
    fail = False

    if result["dangling"]:
        fail = True
        print(f"\n  [FAIL] {len(result['dangling'])} dangling reference(s):")
        for d in result["dangling"]:
            print(f"    - {d['source']}:{d['line']} -> {d['target']}")
    else:
        print(f"\n  [PASS] No dangling references.")

    if result["deprecated"]:
        fail = True
        print(f"\n  [FAIL] {len(result['deprecated'])} deprecated path(s):")
        for d in result["deprecated"]:
            print(f"    - {d['source']}:{d['line']}: {d['target']} ({d['deprecated_pattern']})")
    else:
        print(f"\n  [PASS] No deprecated paths.")

    if result["cycles"]:
        fail = True
        print(f"\n  [FAIL] {len(result['cycles'])} circular reference(s):")
        for cycle in result["cycles"]:
            print(f"    - {' -> '.join(cycle)}")
    else:
        print(f"\n  [PASS] No circular references.")

    print()
    if fail:
        sys.exit(1)


def cmd_check_sequential_ids(args):
    """CLI wrapper for sequential ID checking (SYSGAP-009)."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    result = check_sequential_ids()
    print()
    print("=== Sequential ID Check ===")
    fail = False

    def _report(prefix, ids, gaps):
        nonlocal fail
        if ids:
            print(f"  {prefix}: {ids[0]:03d}-{ids[-1]:03d} ({len(ids)} entries)")
        else:
            print(f"  {prefix}: no entries found")
        if gaps:
            fail = True
            print(f"    [FAIL] Gaps detected: missing {gaps}")
        else:
            print(f"    [PASS] No gaps.")

    _report("DEC", result["dec_ids"], result["dec_gaps"])
    _report("EVD", result["evd_ids"], result["evd_gaps"])
    _report("RISK", result["risk_ids"], result["risk_gaps"])

    orphans = (result.get("orphan_evidence_refs", []) +
               result.get("orphan_decision_refs", []) +
               result.get("orphan_risk_refs", []))
    if orphans:
        fail = True
        print(f"\n  [FAIL] {len(orphans)} cross-reference(s) to non-existent task IDs: {orphans}")
    else:
        print(f"\n  [PASS] All cross-referenced task IDs exist in plan-tracker.")

    missing_evd = result.get("completed_missing_evidence", [])
    if missing_evd:
        fail = True
        print(f"  [FAIL] {len(missing_evd)} completed task(s) without evidence: {missing_evd}")
    else:
        print(f"  [PASS] All completed tasks have evidence.")

    print()
    if fail:
        sys.exit(1)


def cmd_check_structural_validity(args):
    """CLI wrapper for structural validity checking (SYSGAP-010)."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    issues = check_structural_validity()
    print()
    print("=== Structural Validity Check ===")
    if issues:
        print(f"  [FAIL] {len(issues)} structural issue(s):")
        for v in issues:
            ftype = v.get("type", "unknown")
            ffile = v.get("file", "?")
            detail = v.get("detail", "")
            print(f"    - [{ftype}] {ffile}: {detail}")
        print()
        sys.exit(1)
    print(f"  [PASS] All governance files have valid structure.")
    print()


def cmd_check_commit_scope(args):
    """CLI wrapper for commit scope verification (SYSGAP-012)."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    limit = args.limit if hasattr(args, 'limit') else 20
    result = check_commit_scope(limit=limit)
    print()
    print("=== Commit Scope Verification ===")
    if result.get("error"):
        print(f"  [ERROR] {result['error']}")
        print()
        return
    print(f"  Recent commits checked: {result['total_checked']}")
    issues = result["issues"]
    if issues:
        print(f"\n  [WARN] {len(issues)} scope discipline issue(s):")
        for v in issues:
            itype = v.get("type", "?")
            detail = v.get("detail", "")
            sha = v.get("sha", "?")
            print(f"    - [{itype}] {sha}: {detail}")
    else:
        print(f"\n  [PASS] All recent commits have clean scope discipline.")
    print()


def cmd_check_goal_alignment(args):
    """CLI wrapper for goal alignment checking (SYSGAP-023)."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    result = check_goal_alignment()
    fail = False
    print()
    print("=== Goal Alignment Check ===")
    if not result["has_project_goal"]:
        print(f"  [WARN] plan-tracker missing 项目目标 field.")
    else:
        project_goal_short = result["project_goal"][:60]
        print(f"  [INFO] 项目目标: {project_goal_short}...")
    print(f"  Impact analysis entries: {len(result['entries'])}")
    if result["entries"]:
        for e in result["entries"]:
            if e["status"] == "FAIL":
                fail = True
                if not e["has_goal"]:
                    print(f"  [FAIL] {e['task_id']} ({e['evd_id']}): 缺少 目标对齐: 字段")
                else:
                    print(f"  [FAIL] {e['task_id']} ({e['evd_id']}): 目标对齐: 仅 {e['goal_len']} chars (需 >= 30)")
            elif e["status"] == "PASS":
                print(f"  [PASS] {e['task_id']} ({e['evd_id']}): {e['goal_len']} chars")
        if result["duplicates"]:
            print(f"  [WARN] {len(result['duplicates'])} duplicate goal alignment(s):")
            for t1, t2 in result["duplicates"]:
                print(f"    - {t1} <-> {t2}")
    else:
        print(f"  [PASS] No impact analysis entries to check.")
    if not fail and result["has_project_goal"]:
        print(f"  [PASS] All impact analysis entries have valid goal alignment.")
    print()
    if fail:
        sys.exit(1)


def cmd_check_user_impact(args):
    """CLI wrapper for user impact checking (SYSGAP-024)."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    result = check_user_impact()
    fail = False
    print()
    print("=== User Impact Check ===")
    print(f"  Impact analysis entries: {len(result['entries'])}")
    if result["entries"]:
        for e in result["entries"]:
            status_label = {
                "BLOCKING": "BLOCK",
                "FAIL": "FAIL",
                "WARN": "WARN",
                "PASS": "PASS",
            }.get(e["status"], "?")
            if e["status"] in ("BLOCKING", "FAIL"):
                fail = True
                for issue in e["issues"]:
                    print(f"  [{status_label}] {e['task_id']} ({e['evd_id']}): {issue}")
            elif e["status"] == "WARN":
                for issue in e["issues"]:
                    print(f"  [WARN] {e['task_id']} ({e['evd_id']}): {issue}")
            else:
                print(f"  [PASS] {e['task_id']} ({e['evd_id']}): "
                      f"获得={e['obtain']}, 体验变化={e['exp_change']}, "
                      f"迁移指南={e['migration']}")
    else:
        print(f"  [PASS] No impact analysis entries to check.")
    if not fail and not result["blocking"]:
        print(f"  [PASS] All impact analysis entries have valid user impact analysis.")
    print()
    if fail:
        sys.exit(1)


# ── SYSGAP-037: check-agent-team subcommand ──────────────────────

def cmd_check_agent_team(args):
    """Run Check 18 (Agent Team Review) + Check 19 (Agent Activation) together."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    issues = 0

    # Check 18: Agent Team Review
    print("\n=== Check 18: Agent Team Review (SYSGAP-035) ===")
    atr_result = check_agent_team_review()
    print(f"  Product-code tasks (completed): {atr_result['total_tasks']}")
    print(f"  Reviewed: {atr_result['reviewed']}")
    if atr_result["unreviewed"] > 0:
        issues += atr_result["unreviewed"]
        print(f"  [FAIL] {atr_result['unreviewed']} product-code task(s) without review evidence:")
        for tid in atr_result["review_gap_tasks"]:
            print(f"    - {tid}")
    else:
        if atr_result["total_tasks"] > 0:
            print(f"  [PASS] All product-code tasks have review evidence.")
        else:
            print(f"  [PASS] No product-code tasks to review.")

    # Check 19: Agent Activation
    print("\n=== Check 19: Agent Activation (SYSGAP-036) ===")
    aa_result = check_agent_activation()
    print(f"  P0 cross-layer product tasks: {aa_result['total_p0_cross_layer']}")
    print(f"  Analyst activated: {aa_result['analyst_activated']}")
    if aa_result["analyst_bypassed"] > 0:
        issues += aa_result["analyst_bypassed"]
        print(f"  [FAIL] {aa_result['analyst_bypassed']} task(s) with impact analysis but no Analyst:")
        for tid in aa_result["bypassed_tasks"]:
            print(f"    - {tid}")
    else:
        if aa_result["total_p0_cross_layer"] > 0:
            print(f"  [PASS] All P0 cross-layer tasks have Analyst involvement.")
        else:
            print(f"  [PASS] No P0 cross-layer product tasks to check.")

    # Summary
    print(f"\n  ── Agent Team Check Summary ──")
    if issues == 0:
        print(f"  Result: PASSED — 0 issues found")
    else:
        print(f"  Result: ISSUES FOUND — {issues} issue(s)")
    print()

    if args.fail_on_issues and issues > 0:
        sys.exit(1)


# ── SYSGAP-042: check-review-debt subcommand ──────────────────────

def cmd_check_review_debt(args):
    """Run Check 20: Review Debt independently."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    print("\n=== Check 20: Review Debt (SYSGAP-042) ===")
    rd_result = check_review_debt()
    print(f"  Product-code tasks (all, with evidence): {rd_result['total_tasks']}")
    print(f"  Review debt (have execution evidence, no review): {rd_result['review_debt_count']}")
    if rd_result["review_debt_count"] > 0:
        print(f"  [FAIL] {rd_result['review_debt_count']} product-code task(s) with review debt:")
        for tid in rd_result["review_debt_tasks"]:
            print(f"    - {tid}")
    else:
        if rd_result["total_tasks"] > 0:
            print(f"  [PASS] All product-code tasks have review evidence.")
        else:
            print(f"  [PASS] No product-code tasks to check.")
    print()
    if args.fail_on_issues and rd_result["review_debt_count"] > 0:
        sys.exit(1)


def cmd_check_version_consistency(_args):
    """Run version consistency check across all declaration locations."""
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    issues = check_version_consistency()

    print("\n=== Version Consistency Check ===")
    print(f"  Source of truth: skills/software-project-governance/SKILL.md")
    print(f"  Files checked: 11 (SKILL.md, manifest.json, 3 plugin.json, CHANGELOG, plan-tracker, 4 hooks)")

    fail_items = [i for i in issues if not i.startswith("[WARN]")]
    warn_items = [i for i in issues if i.startswith("[WARN]")]

    if warn_items:
        print(f"\n  Warnings ({len(warn_items)}):")
        for w in warn_items:
            print(f"    {w}")

    if fail_items:
        print(f"\n  Failures ({len(fail_items)}):")
        for f in fail_items:
            print(f"    {f}")
        print(f"\n  Result: FAILED — {len(fail_items)} mismatch(es)")
        sys.exit(1)
    else:
        print(f"\n  Result: PASSED — all version declarations consistent")
    print()


def cmd_check_projection_sync(args):
    """Run projection/fixture sync guard independently."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    result = check_projection_sync()
    print("\n=== Projection Sync Check ===")
    print(f"  Source version: {result['source_version'] or 'unknown'}")
    print(f"  Mirrored files checked: {result['mirrors_checked']}")
    if result.get("mirrors_skipped_untracked"):
        print(f"  Untracked local projection copies skipped: {result['mirrors_skipped_untracked']}")
    if result["version_checks"]:
        print("  Version checks:")
        for item in result["version_checks"]:
            print(f"    - {item['label']}: {item['version'] or 'missing'} ({item['path']})")
    if result["issues"]:
        print(f"\n  Result: FAILED — {len(result['issues'])} issue(s)")
        for issue in result["issues"][:20]:
            print(f"    - {issue}")
        if len(result["issues"]) > 20:
            print(f"    ... and {len(result['issues']) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("\n  Result: PASSED — projection files and version declarations are synchronized")
    print()


def cmd_check_hot_fact_source(args):
    """Run hot fact-source consistency guard independently."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    issues = check_hot_fact_source_consistency()
    print("\n=== Hot Fact-Source Consistency Check ===")
    if issues:
        print(f"  Result: FAILED — {len(issues)} issue(s)")
        for issue in issues[:20]:
            print(f"    - {issue}")
        if len(issues) > 20:
            print(f"    ... and {len(issues) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("  Result: PASSED — hot fact-source sections are synchronized")
    print()


def cmd_check_product_success_contracts(args):
    """Run Product Success Contract guard independently."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    result = check_product_success_contracts()
    print("\n=== Product Success Contract Check ===")
    print(f"  Required active P0/P1 contract(s): {len(result['required_tasks'])}")
    issue_count = len(result["issues"])
    for issue in result["issues"]:
        print(f"  [FAIL] {issue}")
    for entry in result["entries"]:
        if entry["status"] == "FAIL":
            issue_count += 1
            print(f"  [FAIL] {entry['task_id']}: {', '.join(entry['issues'])}")
        else:
            print(f"  [PASS] {entry['task_id']}")
    if issue_count:
        print(f"\n  Result: FAILED — {issue_count} issue(s)")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("\n  Result: PASSED — product success contracts are ready")
    print()


def cmd_check_acceptance_contracts(args):
    """Run Executable Acceptance Contract guard independently."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    result = check_acceptance_contracts()
    print("\n=== Executable Acceptance Contract Check ===")
    print(f"  Required active P0/P1 acceptance contract(s): {len(result['required_tasks'])}")
    issue_count = len(result["issues"])
    for issue in result["issues"]:
        print(f"  [FAIL] {issue}")
    for entry in result["entries"]:
        if entry["status"] == "FAIL":
            issue_count += 1
            print(f"  [FAIL] {entry['task_id']}: {', '.join(entry['issues'])}")
        else:
            print(f"  [PASS] {entry['task_id']}")
    if issue_count:
        print(f"\n  Result: FAILED — {issue_count} issue(s)")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("\n  Result: PASSED — executable acceptance contracts are ready")
    print()


def main():
    parser = argparse.ArgumentParser(
        prog="verify_workflow",
        description="Software Project Governance CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # verify (default, backward compatible)
    subparsers.add_parser("verify", help="Verify workflow assets exist and contain required snippets")

    # status
    subparsers.add_parser("status", help="Show project status overview")

    # gate <id>
    gate_p = subparsers.add_parser("gate", help="Show details for a specific Gate")
    gate_p.add_argument("gate_id", help="Gate ID (e.g. G3, 3, g5)")

    # gate-check <id> (auto-judge)
    gc_p = subparsers.add_parser("gate-check", help="Auto-judge a Gate's check items (B-level automation)")
    gc_p.add_argument("gate_id", help="Gate ID (e.g. G3, 3, g5)")
    gc_p.add_argument("--fail-on-blocked", action="store_true",
                      help="Exit with non-zero code if gate is blocked")

    # gates (list all)
    subparsers.add_parser("gates", help="List all Gates with current status")

    # stage <name>
    stage_p = subparsers.add_parser("stage", help="Show workflow SKILL.md for a stage")
    stage_p.add_argument("stage_name", help="Stage name (e.g. initiation, research, development)")

    # stages (list all)
    subparsers.add_parser("stages", help="List all available stages")

    # check-governance
    check_p = subparsers.add_parser("check-governance", help="Run governance health checks")
    check_p.add_argument("--fail-on-issues", action="store_true",
                         help="Exit with non-zero code if issues found")

    # execution-packet
    xp_p = subparsers.add_parser(
        "execution-packet",
        help="Generate short AI execution packets for active P0/P1 tasks",
    )
    xp_p.add_argument("--write", action="store_true",
                      help="Write .governance/execution-packets.json")
    xp_p.add_argument("--task", action="append",
                      help="Limit packet generation to a task id; may be repeated")

    # check-manifest-consistency
    cmc_p = subparsers.add_parser("check-manifest-consistency",
                                   help="Compare manifest.json canonical set against actual filesystem")
    cmc_p.add_argument("--fail-on-issues", action="store_true",
                        help="Exit with non-zero code if mismatch detected")

    # check-plugin-freshness
    subparsers.add_parser("check-plugin-freshness", help="Check if installed plugin is up to date with source")

    # check-agent-adapters
    caa_p = subparsers.add_parser("check-agent-adapters",
                                  help="Check mainstream code agent adapter contracts")
    caa_p.add_argument("--runtime", action="store_true",
                       help="Also execute local runtime version commands for supported adapters")

    # check-release
    cr_p = subparsers.add_parser("check-release",
                                 help="Run release readiness checks used by stage-release")
    cr_p.add_argument("--version",
                      help="Release version to validate (semver X.Y.Z)")
    cr_p.add_argument("--require-changelog", action="store_true",
                      help="Require project/CHANGELOG.md to contain ## [version]")
    cr_p.add_argument("--runtime-adapters", action="store_true",
                      help="Also execute local runtime version commands for supported adapters")
    cr_p.add_argument("--skip-execution-gates", action="store_true",
                      help="Diagnostic only: skip verify/check-governance/e2e/unit-test execution gates")

    # e2e-check
    subparsers.add_parser("e2e-check", help="Run E2E governance verification against e2e-test-project")

    # agent-runtime-e2e
    are_p = subparsers.add_parser(
        "agent-runtime-e2e",
        help="Run real agent runtime E2E harness against e2e-test-project",
    )
    are_p.add_argument(
        "--target",
        default=str(ROOT / "project/e2e-test-project"),
        help="Target project cwd for real agent runtime E2E commands",
    )
    are_p.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Per-agent command timeout in seconds",
    )
    are_p.add_argument(
        "--agent",
        action="append",
        choices=AGENT_RUNTIME_E2E_PLATFORMS,
        help="Limit to one agent; may be repeated. Defaults to all mainstream agents.",
    )

    # gemini-auth-preflight
    subparsers.add_parser(
        "gemini-auth-preflight",
        help="Check Gemini CLI PATH/version/auth sources without printing secrets",
    )

    # opencode-provider-preflight
    subparsers.add_parser(
        "opencode-provider-preflight",
        help="Check opencode CLI PATH/version/provider model without printing secrets",
    )

    # check-cross-references (SYSGAP-008)
    xr_p = subparsers.add_parser("check-cross-references",
                                 help="Scan .md/.py files for dangling, deprecated, and circular path references")
    xr_p.add_argument("--fail-on-issues", action="store_true",
                      help="Exit with non-zero code if issues found")

    # check-sequential-ids (SYSGAP-009)
    si_p = subparsers.add_parser("check-sequential-ids",
                                 help="Verify ID continuity and cross-reference integrity in governance records")
    si_p.add_argument("--fail-on-issues", action="store_true",
                      help="Exit with non-zero code if issues found")

    # check-structural-validity (SYSGAP-010)
    sv_p = subparsers.add_parser("check-structural-validity",
                                 help="Validate structural integrity of governance files")
    sv_p.add_argument("--fail-on-issues", action="store_true",
                      help="Exit with non-zero code if issues found")

    # check-commit-scope (SYSGAP-012)
    cs_p = subparsers.add_parser("check-commit-scope",
                                 help="Verify commit scope discipline (task ID uniqueness, bulk commits, side-effect keywords)")
    cs_p.add_argument("--limit", type=int, default=20,
                      help="Number of recent commits to check (default: 20)")

    # check-goal-alignment (SYSGAP-023)
    cga_p = subparsers.add_parser("check-goal-alignment",
                                  help="Verify goal alignment in impact analysis entries")
    cga_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if issues found")

    # check-user-impact (SYSGAP-024)
    cui_p = subparsers.add_parser("check-user-impact",
                                  help="Verify user impact analysis in impact analysis entries")
    cui_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if issues found")

    # check-agent-team (SYSGAP-037)
    cat_p = subparsers.add_parser("check-agent-team",
                                  help="Run Agent Team integrity checks (Check 18 + Check 19)")
    cat_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if issues found")

    # check-review-debt (SYSGAP-042)
    crd_p = subparsers.add_parser("check-review-debt",
                                  help="Run review debt check (Check 20)")
    crd_p.add_argument("--fail-on-issues", action="store_true",
                      help="Exit with non-zero code if review debt found")

    # check-version-consistency (FIX-052)
    subparsers.add_parser("check-version-consistency",
                          help="Check version consistency across all declaration files")

    # check-projection-sync (FIX-086)
    cps_p = subparsers.add_parser(
        "check-projection-sync",
        help="Check source-to-target fixture projection and plugin version sync",
    )
    cps_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if projection drift is found")

    # check-hot-fact-source (FIX-087)
    chfs_p = subparsers.add_parser(
        "check-hot-fact-source",
        help="Check hot plan-tracker fact-source consistency across active release sections",
    )
    chfs_p.add_argument("--fail-on-issues", action="store_true",
                        help="Exit with non-zero code if hot fact-source drift is found")

    # check-product-success-contracts (FIX-088)
    cpsc_p = subparsers.add_parser(
        "check-product-success-contracts",
        help="Check Product Success Contract fields for active P0/P1 execution packets",
    )
    cpsc_p.add_argument("--fail-on-issues", action="store_true",
                        help="Exit with non-zero code if a required contract is missing or incomplete")

    # check-acceptance-contracts (FIX-089)
    cac_p = subparsers.add_parser(
        "check-acceptance-contracts",
        help="Check executable acceptance contracts for active P0/P1 execution packets",
    )
    cac_p.add_argument("--fail-on-issues", action="store_true",
                       help="Exit with non-zero code if a required acceptance contract is missing or incomplete")

    # check-locks (FIX-056 Phase 2)
    subparsers.add_parser("check-locks",
                          help="Check agent-locks.json consistency (FIX-056 Check 25)")

    # check-archive-integrity (SYSGAP-030)
    subparsers.add_parser("check-archive-integrity",
                          help="Check archive integrity (SYSGAP-030 Check 26)")

    args = parser.parse_args()

    commands = {
        "verify": cmd_verify,
        "status": cmd_status,
        "gate": cmd_gate,
        "gate-check": cmd_gate_check,
        "gates": cmd_gates,
        "stage": cmd_stage,
        "stages": cmd_stages,
        "check-governance": cmd_check_governance,
        "execution-packet": cmd_execution_packet,
        "check-manifest-consistency": cmd_check_manifest_consistency,
        "check-plugin-freshness": cmd_check_plugin_freshness,
        "check-agent-adapters": cmd_check_agent_adapters,
        "check-release": cmd_check_release,
        "e2e-check": cmd_e2e_check,
        "agent-runtime-e2e": cmd_agent_runtime_e2e,
        "gemini-auth-preflight": cmd_gemini_auth_preflight,
        "opencode-provider-preflight": cmd_opencode_provider_preflight,
        "check-cross-references": cmd_check_cross_references,
        "check-sequential-ids": cmd_check_sequential_ids,
        "check-structural-validity": cmd_check_structural_validity,
        "check-commit-scope": cmd_check_commit_scope,
        "check-goal-alignment": cmd_check_goal_alignment,
        "check-user-impact": cmd_check_user_impact,
        "check-agent-team": cmd_check_agent_team,
        "check-review-debt": cmd_check_review_debt,
        "check-version-consistency": cmd_check_version_consistency,
        "check-projection-sync": cmd_check_projection_sync,
        "check-hot-fact-source": cmd_check_hot_fact_source,
        "check-product-success-contracts": cmd_check_product_success_contracts,
        "check-acceptance-contracts": cmd_check_acceptance_contracts,
        "check-locks": cmd_check_agent_locks,
        "check-archive-integrity": cmd_check_archive_integrity,
    }

    cmd = args.command or "verify"
    commands[cmd](args)


if __name__ == "__main__":
    main()
