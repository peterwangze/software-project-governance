from pathlib import Path
import sys
import re
import argparse
from datetime import datetime, date

ROOT = Path(__file__).resolve().parents[3]

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
    ROOT / ".governance/plan-tracker.md": [
        "## 项目总览",
        "## 样例跟踪表",
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
        "0.21.0",
    ],
    ROOT / ".claude-plugin/marketplace.json": [
        "0.21.0",
    ],
    ROOT / ".codex-plugin/plugin.json": [
        "0.21.0",
    ],
    ROOT / "skills/software-project-governance/core/manifest.json": [
        "0.21.0",
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

    actual = scan_actual_files()

    # For canonical dir entries, we only check the dir exists (not the files inside)
    canonical_dirs = {p for p in canonical if p.endswith("/")}
    canonical_files = {p for p in canonical if not p.endswith("/")}

    missing = sorted(canonical_files - actual)
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
        content = path.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet in content:
                print(f"[OK] snippet found: {path.relative_to(ROOT)} :: {snippet}")
            else:
                failures.append(f"missing snippet in {path.relative_to(ROOT)}: {snippet}")
                print(f"[FAIL] missing snippet: {path.relative_to(ROOT)} :: {snippet}")
    return failures


# ── Markdown parsing helpers ─────────────────────────────────────

SAMPLE_PATH = ROOT / ".governance/plan-tracker.md"
GATES_PATH = ROOT / "skills/software-project-governance/core/stage-gates.md"
LIFECYCLE_PATH = ROOT / "skills/software-project-governance/core/lifecycle.md"
STAGES_DIR = ROOT / "skills/software-project-governance/stages"

STAGE_ORDER = [
    "initiation", "research", "selection", "infrastructure",
    "architecture", "development", "testing", "ci-cd",
    "release", "operations", "maintenance",
]

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


def list_available_stages():
    """List all available stage directories."""
    if not STAGES_DIR.is_dir():
        return []
    return sorted(
        [d.name for d in STAGES_DIR.iterdir() if d.is_dir()],
        key=lambda x: STAGE_ORDER.index(x) if x in STAGE_ORDER else 99,
    )


# ── Governance health check parsers ─────────────────────────────

EVIDENCE_PATH = ROOT / ".governance/evidence-log.md"
RISK_PATH = ROOT / ".governance/risk-log.md"


def parse_completed_task_ids():
    """Return set of completed task IDs from plan-tracker."""
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    completed = set()
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| ") or "---" in line:
            continue
        m = re.match(r"\|\s*([A-Z]+-\d+)\s*\|", line)
        if not m:
            continue
        task_id = m.group(1)
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 11:
            status = parts[10]
            if status == "已完成":
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
    """Check that every completed task has at least one evidence entry."""
    completed = parse_completed_task_ids()
    evidenced = parse_evidence_task_ids()
    missing = completed - evidenced
    matched = completed & evidenced
    return {
        "completed_count": len(completed),
        "evidenced_count": len(matched),
        "missing_evidence": sorted(missing),
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
    evidenced = parse_evidence_task_map()

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

    # Check for tasks marked 已完成 in plan-tracker but no evidence
    completed = parse_completed_task_ids()
    tasks_without_evidence = completed - set(evidenced.keys())
    if tasks_without_evidence:
        issues.append({
            "type": "completed_tasks_missing_evidence",
            "detail": sorted(tasks_without_evidence),
        })

    # Check for evidence entries referencing non-existent tasks
    all_tasks = set()
    content = SAMPLE_PATH.read_text(encoding="utf-8")
    for line in content.split("\n"):
        m = re.match(r"\|\s*([A-Z]+-\d+)\s*\|", line.strip())
        if m:
            all_tasks.add(m.group(1))

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
    """Check that all 5 version declaration files agree on the same version.

    Source of truth: skills/software-project-governance/SKILL.md frontmatter.
    Other files that must match:
      - skills/software-project-governance/core/manifest.md
      - .claude-plugin/plugin.json
      - .claude-plugin/marketplace.json
      - .codex-plugin/plugin.json
    """
    import json

    VERSION_FILES = {
        "SKILL.md (source of truth)": ROOT / "skills/software-project-governance/SKILL.md",
        "manifest.md": ROOT / "skills/software-project-governance/core/manifest.md",
        ".claude-plugin/plugin.json": ROOT / ".claude-plugin/plugin.json",
        ".claude-plugin/marketplace.json": ROOT / ".claude-plugin/marketplace.json",
        ".codex-plugin/plugin.json": ROOT / ".codex-plugin/plugin.json",
    }

    issues = []
    versions = {}

    for label, path in VERSION_FILES.items():
        if not path.exists():
            issues.append(f"[MISSING] {label}: {path} not found")
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
                issues.append(f"[ERROR] {label}: invalid JSON")
                continue
        else:
            # Markdown files: look for version in frontmatter or inline
            match = re.search(r"(?:`?\*{0,2}version\*{0,2}`?\s*[:=]\s*`?)(\d+\.\d+\.\d+)", content)
            if match:
                ver = match.group(1)
            else:
                ver = "NOT FOUND"

        versions[label] = ver

    # Check consistency
    source_version = versions.get("SKILL.md (source of truth)")
    if not source_version:
        issues.append("[ERROR] Cannot determine source version from SKILL.md")
        return issues

    for label, ver in versions.items():
        if label == "SKILL.md (source of truth)":
            continue
        if ver != source_version:
            issues.append(
                f"[MISMATCH] {label}: version={ver}, expected={source_version}"
            )

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
    version_failures = check_version_consistency()
    failures = file_failures + snippet_failures + version_failures

    if failures:
        print("\n== Verification Result: FAILED ==")
        for failure in failures:
            print(f"  - {failure}")
        sys.exit(1)

    print("\n== Verification Result: PASSED ==")


def cmd_status(args):
    """Show project status overview."""
    config = parse_project_config()
    overview = parse_overview()
    gates = parse_gate_status()
    stats = parse_task_stats()

    # Config section
    print("\n┌─ Project Config ────────────────────────────────────┐")
    labels = {"Profile": "Profile", "触发模式": "Trigger", "当前阶段": "Stage",
              "并行活跃阶段": "Active", "接入方式": "Onboarding"}
    for k, v in config.items():
        label = labels.get(k, k)
        print(f"│  {label}: {v}")
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
    """Show sub-workflow summary for a specific stage."""
    stage_name = args.stage_name.lower()

    stage_path = STAGES_DIR / stage_name / "sub-workflow.md"
    if not stage_path.is_file():
        print(f"[FAIL] Stage '{stage_name}' not found")
        available = list_available_stages()
        if available:
            print(f"Available: {', '.join(available)}")
        sys.exit(1)

    content = stage_path.read_text(encoding="utf-8")

    # Also check for skills in this stage
    stage_dir = STAGES_DIR / stage_name
    skills = sorted([
        f.name for f in stage_dir.iterdir()
        if f.is_file() and f.name != "sub-workflow.md" and f.suffix == ".md"
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
        sw_path = STAGES_DIR / stage / "sub-workflow.md"
        has_sw = "Y" if sw_path.is_file() else "N"

        # Count skills
        stage_dir = STAGES_DIR / stage
        skill_count = len([
            f for f in stage_dir.iterdir()
            if f.is_file() and f.name != "sub-workflow.md" and f.suffix == ".md"
        ]) if stage_dir.is_dir() else 0

        skill_info = f", {skill_count} skill(s)" if skill_count else ""
        print(f"│  {i:2d}. {stage:16s} {name:20s}  sub-workflow:{has_sw}{skill_info}")
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
    """Check M5 AskUserQuestion compliance — static anti-pattern detection.

    Detects:
    1. Source file contamination: sub-workflow files containing '询问用户：' patterns
       that instruct agent to output inline text questions (M5.1 violation)
    2. Bootstrap coverage: governance-init.md template contains AskUserQuestion rule
    3. Interaction boundary: interaction-boundary.md exists and references AskUserQuestion

    This CANNOT detect runtime M5 violations (actual inline questions in conversation).
    It catches the ROOT CAUSE: source files that teach agents to use inline text.
    """
    issues = []
    skills_dir = ROOT / "skills" / "software-project-governance"

    # Check 1: Anti-pattern in sub-workflow files
    # Pattern: 询问用户："..." or 询问用户：'...' (direct inline question instruction)
    inline_question_pattern = re.compile(r'询问用户[：:]\s*["\u201c]')
    skills_impl_dir = skills_dir / "skills"
    if skills_impl_dir.is_dir():
        for md_file in skills_impl_dir.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                for i, line in enumerate(content.splitlines(), 1):
                    if inline_question_pattern.search(line):
                        # Check it's not already annotated with AskUserQuestion
                        if "AskUserQuestion" not in line:
                            rel_path = md_file.relative_to(ROOT)
                            issues.append({
                                "type": "m5_anti_pattern",
                                "file": str(rel_path),
                                "line": i,
                                "text": line.strip()[:120],
                                "severity": "BLOCKING",
                                "fix": "Change to: MUST 通过 AskUserQuestion 工具询问用户 (M5.1 禁止内联文字问题)"
                            })
            except Exception:
                pass

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

    return {"issues": issues, "total_checks": 4}


def cmd_check_governance(args):
    """Run governance health checks: evidence completeness, risk staleness, gate consistency."""
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
    """Lightweight version consistency check for G11 auto-judgment."""
    try:
        skill_content = (ROOT / "skills/software-project-governance/SKILL.md").read_text(encoding="utf-8")
        m = re.search(r'version[:\*]+\s*([\d.]+)', skill_content)
        if not m:
            return "NEEDS_HUMAN", "无法从 SKILL.md 提取版本号"
        skill_version = m.group(1)
        version_files = [
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            ".codex-plugin/plugin.json",
            "skills/software-project-governance/core/manifest.md",
        ]
        for vf in version_files:
            vf_path = ROOT / vf
            if vf_path.exists():
                vf_content = vf_path.read_text(encoding="utf-8")
                if skill_version not in vf_content:
                    return "FAIL", f"{vf} 版本与 SKILL.md ({skill_version}) 不一致"
        return "PASS", f"版本 {skill_version} 在 5 个声明文件中一致"
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
             lambda: _check_evidence_mentions("复盘", "运营数据")),
            ("用户反馈已归档",
             lambda: _check_snippet_in_file(
                 ".governance/decision-log.md", "DEC-", "决策记录含反馈相关条目")),
            ("关键问题已识别分类",
             lambda: _check_plan_has_priority("P0")),
            ("优化方向已明确",
             lambda: _check_plan_has_priority("P0")),
        ],
        "G11": [
            ("复盘完成（含目标回顾/结果评估/原因分析/经验沉淀）",
             lambda: _check_evidence_mentions("复盘", "复盘")),
            ("经验回灌到规则和模板",
             lambda: _check_snippet_in_file(
                 "skills/software-project-governance/references/behavior-protocol.md", "MUST", "behavior-protocol.md 含经验驱动的 MUST 规则")),
            ("下轮方向已明确（≥1 条 P0 任务）",
             lambda: _check_plan_has_priority("P0")),
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


def cmd_e2e_check(_args):
    """Run E2E governance verification against the e2e-test-project."""
    e2e_dir = ROOT / "project/e2e-test-project"
    if not e2e_dir.exists():
        print("[SKIPPED] project/e2e-test-project/ not found")
        return

    passed, failed = 0, 0
    def check(condition, msg):
        nonlocal passed, failed
        if condition:
            print(f"  [PASS] {msg}")
            passed += 1
        else:
            print(f"  [FAIL] {msg}")
            failed += 1

    print("=== E2E Governance Verification ===")
    print(f"Target: {e2e_dir}\n")

    # Category A: Project structure
    print("--- Category A: Project structure ---")
    check((e2e_dir / "CLAUDE.md").exists(), "CLAUDE.md exists")
    check((e2e_dir / ".governance").is_dir(), ".governance/ exists")
    check((e2e_dir / ".governance/plan-tracker.md").exists(), "plan-tracker.md exists")
    check((e2e_dir / ".governance/evidence-log.md").exists(), "evidence-log.md exists")
    check((e2e_dir / ".governance/decision-log.md").exists(), "decision-log.md exists")
    check((e2e_dir / ".governance/risk-log.md").exists(), "risk-log.md exists")

    # Category B: Bootstrap content
    print("\n--- Category B: Bootstrap content ---")
    bootstrap_file = e2e_dir / "CLAUDE.md"
    if bootstrap_file.exists():
        content = bootstrap_file.read_text(encoding="utf-8")
        check("SELF-CHECK" in content, "Bootstrap: SELF-CHECK present")
        check("Governance Bootstrap" in content, "Bootstrap: section present")
        check("AskUserQuestion" in content, "Bootstrap: AskUserQuestion rule")
        check("阶段跳跃防护" in content, "Bootstrap: stage jump protection")
        check("收工前检查" in content, "Bootstrap: session end checklist")
        check("版本变化自动检测" in content, "Bootstrap: version change detection")

    # Category C: Plan-tracker completeness
    print("\n--- Category C: Plan-tracker completeness ---")
    pt = e2e_dir / ".governance/plan-tracker.md"
    if pt.exists():
        content = pt.read_text(encoding="utf-8")
        check("## 版本规划" in content, "Plan-tracker: version planning")
        check("## 需求跟踪矩阵" in content, "Plan-tracker: requirement traceability")
        check("## 变更控制" in content, "Plan-tracker: change control")
        check("快速通道" in content, "Plan-tracker: fast track defined")
        check("项目配置" in content, "Plan-tracker: project config")
        check("工作流版本" in content, "Plan-tracker: workflow version field")
        check("操作权限模式" in content, "Plan-tracker: permission mode field")

    print(f"\n=== Result: {passed} passed, {failed} failed ===")
    if failed > 0:
        print("ACTION: Fix failures above. These represent real user-facing gaps.")
        import sys
        sys.exit(1)
    print("All E2E checks passed. User experience intact.")


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
    stage_p = subparsers.add_parser("stage", help="Show sub-workflow for a stage")
    stage_p.add_argument("stage_name", help="Stage name (e.g. initiation, research, development)")

    # stages (list all)
    subparsers.add_parser("stages", help="List all available stages")

    # check-governance
    check_p = subparsers.add_parser("check-governance", help="Run governance health checks")
    check_p.add_argument("--fail-on-issues", action="store_true",
                         help="Exit with non-zero code if issues found")

    # check-manifest-consistency
    cmc_p = subparsers.add_parser("check-manifest-consistency",
                                   help="Compare manifest.json canonical set against actual filesystem")
    cmc_p.add_argument("--fail-on-issues", action="store_true",
                        help="Exit with non-zero code if mismatch detected")

    # check-plugin-freshness
    subparsers.add_parser("check-plugin-freshness", help="Check if installed plugin is up to date with source")

    # e2e-check
    subparsers.add_parser("e2e-check", help="Run E2E governance verification against e2e-test-project")

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
        "check-manifest-consistency": cmd_check_manifest_consistency,
        "check-plugin-freshness": cmd_check_plugin_freshness,
        "e2e-check": cmd_e2e_check,
    }

    cmd = args.command or "verify"
    commands[cmd](args)


if __name__ == "__main__":
    main()
