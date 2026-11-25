"""Required product files, expected static snippets and blocking issue policy."""

from checks.manifest import build_required_files_from_manifest
from pathlib import Path
from project_paths import default_host_root
from project_paths import display_path as _display
import sys


ROOT = Path(__file__).resolve().parents[3]
GOVERNANCE_DIR = default_host_root() / ".governance"


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


def lock_issue_is_blocking(issue, *, blocking_lock_issue_types):
    """Return True when a lock issue should affect --fail-on-issues."""
    issue_type = issue.get("type", "")
    normalized = issue_type.removeprefix("format_")
    return issue_type in blocking_lock_issue_types or normalized in blocking_lock_issue_types


def structural_issue_is_blocking(issue):
    """Return True when a structural validity issue should fail governance health."""
    severity = str(issue.get("severity", "ERROR")).upper()
    return severity not in {"INFO", "WARN", "WARNING"}


def blocking_structural_issues(issues, *, structural_issue_is_blocking):
    return [issue for issue in issues if structural_issue_is_blocking(issue)]


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
    "Governance Plan Tracker": GOVERNANCE_DIR / "plan-tracker.md",
    "Governance Evidence Log": GOVERNANCE_DIR / "evidence-log.md",
    "Governance Decision Log": GOVERNANCE_DIR / "decision-log.md",
    "Governance Risk Log": GOVERNANCE_DIR / "risk-log.md",
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
    "Behavior Protocol (M0-M10)": ROOT / "skills/software-project-governance/references/behavior-protocol.md",
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
    "Pi Adapter": ROOT / "adapters/pi/README.md",
    "Pi Adapter Manifest": ROOT / "adapters/pi/adapter-manifest.json",
    "Pi Launcher": ROOT / "adapters/pi/launch.py",
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
        "Tier 1",
        "## Load",
        "## Verify",
        "## Boundary",
        "skills/software-project-governance/SKILL.md",
        "python adapters/claude/launch.py",
        "check-agent-adapters",
        "check-agent-adapters --runtime",
    ],
    ROOT / "adapters/claude/adapter-manifest.json": [
        "adapter_id", "workflow_id", "native_entry", "runtime_e2e", "runtime_capabilities", "launcher",
    ],
    ROOT / "adapters/claude/launch.py": [
        'MANIFEST_PATH = ROOT / "adapters/claude/adapter-manifest.json"',
        "adapters/manifest_report.py", 'report["print_manifest_report"](MANIFEST_PATH, "Claude")',
    ],
    ROOT / "adapters/manifest_report.py": [
        "{platform} Adapter Launcher", 'print("read_order:")', 'print("native_entry:")',
        'print("runtime_e2e:")', 'print("validation:")',
    ],
    ROOT / "adapters/codex/README.md": [
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
    ROOT / "adapters/codex/adapter-manifest.json": [
        "adapter_id", "workflow_id", "native_entry", "runtime_e2e", "runtime_capabilities", "launcher",
    ],
    ROOT / "adapters/codex/launch.py": [
        'MANIFEST_PATH = ROOT / "adapters/codex/adapter-manifest.json"',
        "adapters/manifest_report.py", 'report["print_manifest_report"](MANIFEST_PATH, "Codex")',
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
    ROOT / "adapters/pi/README.md": [
        "Tier 1",
        "加载模型",
        "能力边界",
        "agent-runtime-e2e --agent pi",
    ],
    ROOT / "adapters/pi/adapter-manifest.json": [
        "ask_user_question",
        "dispatch_agent",
        "生成≠咨询",
        "adapters/pi/extension",
    ],
    ROOT / "adapters/pi/launch.py": [
        "Pi Adapter Launcher",
        "native_entry",
        "read_order",
        "validation",
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
        "governance-bootstrap --format json",
        "loop status --unit",
        "(../lifecycle.md)",
        "(../loop-engineering-registry.json)",
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
    ROOT / "project/workflows/software-project-governance/examples/current-project-sample.md": [
        "已迁移",
    ],
    ROOT / "skills/software-project-governance/core/protocol/workflow-schema.md": [
        "governance-bootstrap --format json",
        "loop status --unit",
        "(../lifecycle.md)",
        "(../loop-engineering-registry.json)",
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
        "governance-bootstrap --format json", "resolve.resolved_root_ok",
        "loop start --unit", "--goal", "--acceptance", "--tier",
    ],
    ROOT / "commands/governance-status.md": [
        "governance-bootstrap --format json", "loop status --unit", "loop status --json",
    ],
    ROOT / "commands/governance-gate.md": [
        "loop status --unit", "loop gate --unit", "--gate", "--review",
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
        "Tier 1",
        "## Load",
        "## Verify",
        "## Boundary",
        "skills/software-project-governance/SKILL.md",
        "python adapters/claude/launch.py",
        "check-agent-adapters",
        "check-agent-adapters --runtime",
    ],
    ROOT / "adapters/claude/adapter-manifest.json": [
        "adapter_id",
        "workflow_id",
        "native_entry",
        "launcher",
    ],
    ROOT / "adapters/claude/launch.py": [
        'MANIFEST_PATH = ROOT / "adapters/claude/adapter-manifest.json"',
        "adapters/manifest_report.py", 'report["print_manifest_report"](MANIFEST_PATH, "Claude")',
    ],
    ROOT / "adapters/manifest_report.py": [
        "{platform} Adapter Launcher", 'print("read_order:")', 'print("native_entry:")',
        'print("runtime_e2e:")', 'print("validation:")',
    ],
    ROOT / "adapters/codex/README.md": [
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
    ROOT / "adapters/codex/adapter-manifest.json": [
        "adapter_id",
        "workflow_id",
        "launcher",
    ],
    ROOT / "adapters/codex/launch.py": [
        'MANIFEST_PATH = ROOT / "adapters/codex/adapter-manifest.json"',
        "adapters/manifest_report.py", 'report["print_manifest_report"](MANIFEST_PATH, "Codex")',
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
        "你是 Coordinator，不是单 agent 任务执行者",
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
        "M0-M10 强制性规则",
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
        "## M10. 主动生态探索协议",
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
        "loop status --unit",
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
    ROOT / "changelog.md": ["](project/CHANGELOG.md)"],
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
        "0.102.0",
    ],
    ROOT / ".claude-plugin/marketplace.json": [
        "0.102.0",
    ],
    ROOT / ".codex-plugin/plugin.json": [
        "0.102.0",
    ],
    ROOT / ".zcode-plugin/plugin.json": [
        "0.102.0",
    ],
    ROOT / "package.json": [
        "0.102.0",
    ],
    ROOT / "skills/software-project-governance/core/manifest.json": [
        "0.102.0",
    ],
}


def check_files(*, package_root_now=lambda: ROOT, build_required_files_from_manifest=build_required_files_from_manifest,
                fallback_files=None):
    failures = []

    # Attempt manifest.json first; fall back to builtin hard-coded dicts
    required = build_required_files_from_manifest()
    if required is None:
        required, optional = ((REQUIRED_FILES, OPTIONAL_PROJECTION_FILES) if fallback_files is None
                              else fallback_files())
    else:
        optional = {}  # manifest covers everything

    for label, path in required.items():
        if path.is_file():
            print(f"[OK] file exists: {label} -> {path.relative_to(package_root_now())}")
        else:
            failures.append(f"missing required file: {label} -> {path.relative_to(package_root_now())}")
            print(f"[FAIL] missing required file: {label} -> {path.relative_to(package_root_now())}")

    for label, path in optional.items():
        if path.is_file():
            print(f"[OK] optional projection exists: {label} -> {path.relative_to(package_root_now())}")
        else:
            print(f"[INFO] optional projection missing: {label} -> {path.relative_to(package_root_now())}")

    return failures


def check_snippets(*, package_root=ROOT, required_snippets=REQUIRED_SNIPPETS, display_path=None):
    if display_path is None:
        def display_path(path):
            return _display(path, package_root)
    failures = []
    for path, snippets in required_snippets.items():
        if not path.is_file():
            failures.append(f"missing snippet source file: {display_path(path)}")
            print(f"[FAIL] missing snippet source file: {display_path(path)}")
            continue
        content = path.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet in content:
                print(f"[OK] snippet found: {path.relative_to(package_root)} :: {snippet}")
            else:
                failures.append(f"missing snippet in {path.relative_to(package_root)}: {snippet}")
                print(f"[FAIL] missing snippet: {path.relative_to(package_root)} :: {snippet}")
    return failures


def report_verification(file_failures, snippet_failures, architecture_failures,
                        agent_adapter_failures, version_failures, loop_role_result):
    """Apply the warning policy to the results of the public verification gates."""
    loop_role_failures = [f"[FAIL] loop-role SKILL consistency: {issue}"
                          for issue in loop_role_result["issues"]]
    all_items = (
        file_failures
        + snippet_failures
        + architecture_failures
        + agent_adapter_failures
        + version_failures
        + loop_role_failures
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
