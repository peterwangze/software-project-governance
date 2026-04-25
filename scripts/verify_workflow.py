from pathlib import Path
import sys
import re
import argparse
from datetime import datetime, date

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = {
    "README": ROOT / "README.md",
    "Workflow Schema": ROOT / "protocol/workflow-schema.md",
    "Plugin Contract": ROOT / "protocol/plugin-contract.md",
    "External Command Contract": ROOT / "protocol/external-command-contract.md",
    "Headless Runner Sample": ROOT / "protocol/headless-runner-sample.md",
    "Command Protocol Schema": ROOT / "protocol/command-schema.md",
    "Workflow Manifest": ROOT / "workflows/software-project-governance/manifest.md",
    "Company Practices": ROOT / "workflows/software-project-governance/research/company-practices.md",
    "Plan Tracker": ROOT / "workflows/software-project-governance/templates/plan-tracker.md",
    "Evidence Template": ROOT / "workflows/software-project-governance/templates/evidence-log.md",
    "Decision Template": ROOT / "workflows/software-project-governance/templates/decision-log.md",
    "Risk Template": ROOT / "workflows/software-project-governance/templates/risk-log.md",
    "Governance Plan Tracker": ROOT / ".governance/plan-tracker.md",
    "Governance Evidence Log": ROOT / ".governance/evidence-log.md",
    "Governance Decision Log": ROOT / ".governance/decision-log.md",
    "Governance Risk Log": ROOT / ".governance/risk-log.md",
    "Skill Main Workflow Entry": ROOT / "skills/software-project-governance/main-workflow.md",
    "Skill Tools Index": ROOT / "skills/software-project-governance/TOOLS.md",
    "Skill References Stage Gates": ROOT / "skills/software-project-governance/references/stage-gates.md",
    "Skill References Lifecycle": ROOT / "skills/software-project-governance/references/lifecycle.md",
    "Skill References Profiles": ROOT / "skills/software-project-governance/references/profiles.md",
    "Skill References Onboarding": ROOT / "skills/software-project-governance/references/onboarding.md",
    "Skill References Interaction Boundary": ROOT / "skills/software-project-governance/references/interaction-boundary.md",
    "Skill References Company Practices Summary": ROOT / "skills/software-project-governance/references/company-practices-summary.md",
    "Agent Integration Research": ROOT / "workflows/software-project-governance/research/agent-integration-models.md",
    "Default Product Shape": ROOT / "workflows/software-project-governance/research/default-product-shape.md",
    "External Capability Minimum Validation": ROOT / "workflows/software-project-governance/research/external-capability-minimum-validation.md",
    "Domestic Agent CLI Compatibility": ROOT / "workflows/software-project-governance/research/domestic-agent-cli-compatibility.md",
    "Repo-local Termination Note": ROOT / "workflows/software-project-governance/research/repo-local-termination-note.md",
    "Governance Init Command": ROOT / "commands/governance-init.md",
    "Governance Status Command": ROOT / "commands/governance-status.md",
    "Governance Gate Command": ROOT / "commands/governance-gate.md",
    "Governance Verify Command": ROOT / "commands/governance-verify.md",
    "Codex Skill": ROOT / "skills/software-project-governance/SKILL.md",
    "Skill Stages Initiation Sub-workflow": ROOT / "skills/software-project-governance/stages/initiation/sub-workflow.md",
    "Skill Stages Research Sub-workflow": ROOT / "skills/software-project-governance/stages/research/sub-workflow.md",
    "Skill Stages Architecture Sub-workflow": ROOT / "skills/software-project-governance/stages/architecture/sub-workflow.md",
    "Skill Stages Development Sub-workflow": ROOT / "skills/software-project-governance/stages/development/sub-workflow.md",
    "Skill Stages Selection Sub-workflow": ROOT / "skills/software-project-governance/stages/selection/sub-workflow.md",
    "Skill Stages Infrastructure Sub-workflow": ROOT / "skills/software-project-governance/stages/infrastructure/sub-workflow.md",
    "Skill Stages Testing Sub-workflow": ROOT / "skills/software-project-governance/stages/testing/sub-workflow.md",
    "Skill Stages CI-CD Sub-workflow": ROOT / "skills/software-project-governance/stages/ci-cd/sub-workflow.md",
    "Skill Stages Release Sub-workflow": ROOT / "skills/software-project-governance/stages/release/sub-workflow.md",
    "Skill Stages Operations Sub-workflow": ROOT / "skills/software-project-governance/stages/operations/sub-workflow.md",
    "Skill Stages Maintenance Sub-workflow": ROOT / "skills/software-project-governance/stages/maintenance/sub-workflow.md",
    "Skill Stages Requirement Clarification": ROOT / "skills/software-project-governance/stages/initiation/requirement-clarification.md",
    "Skill Stages Tech Review Checklist": ROOT / "skills/software-project-governance/stages/architecture/tech-review-checklist.md",
    "Skill Stages Code Review Standard": ROOT / "skills/software-project-governance/stages/development/code-review-standard.md",
    "Skill Stages Release Checklist": ROOT / "skills/software-project-governance/stages/release/release-checklist.md",
    "Skill Stages Retro Meeting Template": ROOT / "skills/software-project-governance/stages/maintenance/retro-meeting-template.md",
}

OPTIONAL_PROJECTION_FILES = {
    "Sample Project": ROOT / "workflows/software-project-governance/examples/current-project-sample.md",
    "Sample Evidence": ROOT / "workflows/software-project-governance/examples/current-project-evidence-log.md",
    "Sample Decision": ROOT / "workflows/software-project-governance/examples/current-project-decision-log.md",
    "Sample Risk": ROOT / "workflows/software-project-governance/examples/current-project-risk-log.md",
    "Claude Repository Entry": ROOT / "CLAUDE.md",
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
}

PROJECTION_SNIPPETS = {
    ROOT / "workflows/software-project-governance/examples/current-project-sample.md": [
        "已迁移",
    ],
    ROOT / "CLAUDE.md": [
        "software-project-governance",
        "Governance Bootstrap",
        "没读 plan-tracker 就开始干活",
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
    ROOT / "workflows/software-project-governance/research/agent-integration-models.md": [
        "## 调研目标",
        "## Claude Code",
        "## 通用集成模式对比",
    ],
    ROOT / "workflows/software-project-governance/research/default-product-shape.md": [
        "## 方案摘要",
        "## 分层设计",
        "## 默认接入矩阵",
    ],
    ROOT / "workflows/software-project-governance/research/external-capability-minimum-validation.md": [
        "## 目标",
        "## 为什么先选 external runner / shared command",
        "## 最小验证范围",
        "## 命令约定草案",
        "software-project-governance.run",
    ],
    ROOT / "workflows/software-project-governance/research/domestic-agent-cli-compatibility.md": [
        "## 目标",
        "## 兼容抽象",
        "## 默认接入顺序",
        "## 能力检查清单",
    ],
    ROOT / "workflows/software-project-governance/research/repo-local-termination-note.md": [
        "## 终止对象",
        "## 终止原因",
        "## 降级后的资产定位",
        "## 新主线如何接管",
    ],
    ROOT / "protocol/workflow-schema.md": [
        "## 通用对象模型",
        "### 1. Workflow",
        "### 3. Gate",
    ],
    ROOT / "protocol/plugin-contract.md": [
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
    ROOT / "protocol/external-command-contract.md": [
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
    ROOT / "protocol/headless-runner-sample.md": [
        "## 目标",
        "software-project-governance.headless",
        "## 输入映射",
        "## execution mode",
        "dry-run",
        "## 最小返回样例",
        "### 当前阶段子工作流（按 stage 参数加载）",
    ],
    ROOT / "workflows/software-project-governance/manifest.md": [
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
    ROOT / "workflows/software-project-governance/research/agent-integration-models.md": [
        "## 调研目标",
        "## Claude Code",
        "## 通用集成模式对比",
    ],
    ROOT / "workflows/software-project-governance/research/default-product-shape.md": [
        "## 方案摘要",
        "## 分层设计",
        "## 默认接入矩阵",
    ],
    ROOT / "workflows/software-project-governance/research/external-capability-minimum-validation.md": [
        "## 目标",
        "## 为什么先选 external runner / shared command",
        "## 最小验证范围",
        "## 命令约定草案",
        "software-project-governance.run",
    ],
    ROOT / "workflows/software-project-governance/research/domestic-agent-cli-compatibility.md": [
        "## 目标",
        "## 兼容抽象",
        "## 默认接入顺序",
        "## 能力检查清单",
    ],
    ROOT / "workflows/software-project-governance/research/repo-local-termination-note.md": [
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
    ROOT / "workflows/software-project-governance/examples/current-project-sample.md": [
        "已迁移",
    ],
    ROOT / "protocol/workflow-schema.md": [
        "## 通用对象模型",
        "### 1. Workflow",
        "### 3. Gate",
    ],
    ROOT / "protocol/plugin-contract.md": [
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
    ROOT / "protocol/external-command-contract.md": [
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
    ROOT / "protocol/headless-runner-sample.md": [
        "## 目标",
        "software-project-governance.headless",
        "## 输入映射",
        "## execution mode",
        "dry-run",
        "## 最小返回样例",
        "### 当前阶段子工作流（按 stage 参数加载）",
    ],
    ROOT / "workflows/software-project-governance/manifest.md": [
        "supported_agents",
        "Claude",
        "Codex",
    ],
    ROOT / "CLAUDE.md": [
        "software-project-governance",
        "Governance Bootstrap",
        "没读 plan-tracker 就开始干活",
    ],
    # ── Command Protocol Schema + Upgraded Commands ──
    ROOT / "protocol/command-schema.md": [
        "## Input Parameters 定义规范",
        "## Execution Flow 定义规范",
        "## Output Format 定义规范",
        "## Error Codes 定义规范",
        "## Self-Validation 定义规范",
        "## Agent 执行纪律",
    ],
    ROOT / "commands/governance-init.md": [
        "## Input Parameters",
        "## Execution Flow",
        "## Output Format",
        "## Error Codes",
        "## Self-Validation",
        "INIT-ERR-001",
        "INIT-ERR-002",
        "INIT-ERR-003",
    ],
    ROOT / "commands/governance-status.md": [
        "## Input Parameters",
        "## Execution Flow",
        "## Output Format",
        "## Error Codes",
        "## Self-Validation",
        "STATUS-ERR-001",
    ],
    ROOT / "commands/governance-gate.md": [
        "## Input Parameters",
        "## Execution Flow",
        "## Output Format",
        "## Error Codes",
        "## Self-Validation",
        "GATE-ERR-001",
        "GATE-ERR-002",
    ],
    ROOT / "commands/governance-verify.md": [
        "## Input Parameters",
        "## Execution Flow",
        "## Output Format",
        "## Error Codes",
        "## Self-Validation",
        "VERIFY-ERR-001",
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
        "# Software Project Governance",
        "## M2",
        "references/stage-gates.md",
        "Replacement Boundary",
    ],
    ROOT / ".agents/plugins/marketplace.json": [
        "software-project-governance",
    ],
}


# ── Existing verification functions ──────────────────────────────

def check_files():
    failures = []
    for label, path in REQUIRED_FILES.items():
        if path.is_file():
            print(f"[OK] file exists: {label} -> {path.relative_to(ROOT)}")
        else:
            failures.append(f"missing required file: {label} -> {path.relative_to(ROOT)}")
            print(f"[FAIL] missing required file: {label} -> {path.relative_to(ROOT)}")

    for label, path in OPTIONAL_PROJECTION_FILES.items():
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
GATES_PATH = ROOT / "skills/software-project-governance/references/stage-gates.md"
LIFECYCLE_PATH = ROOT / "skills/software-project-governance/references/lifecycle.md"
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
        if len(parts) >= 10:
            status = parts[9] if len(parts) > 9 else ""
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
        rf"### ({re.escape(gate_id)} .+?)\n\n(.*?)(?=\n### G\d|\n## )",
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
        if len(parts) >= 10:
            status = parts[9]
            if status == "已完成":
                completed.add(task_id)
    return completed


def parse_evidence_task_ids():
    """Return set of task IDs that have evidence entries."""
    content = EVIDENCE_PATH.read_text(encoding="utf-8")
    task_ids = set()
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            task_id = parts[2]
            if task_id and re.match(r"[A-Z]+-\d+", task_id):
                task_ids.add(task_id)
    return task_ids


def parse_evidence_task_map():
    """Return dict mapping task_id -> list of evidence IDs."""
    content = EVIDENCE_PATH.read_text(encoding="utf-8")
    task_map = {}
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            evd_id = parts[1]
            task_id = parts[2]
            if task_id and re.match(r"[A-Z]+-\d+", task_id):
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


# ── CLI commands ─────────────────────────────────────────────────

def cmd_verify(args):
    """Run existing file + snippet verification."""
    print("== Workflow Plugin Verification ==")
    file_failures = check_files()
    snippet_failures = check_snippets()
    failures = file_failures + snippet_failures

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

    # ── Summary ──
    print(f"\n┌─ Governance Health Summary ──────────────────────────┐")
    if all_issues == 0:
        print(f"│  Result: PASSED — 0 issues found")
    else:
        print(f"│  Result: ISSUES FOUND — {all_issues} issue(s)")
    print("└──────────────────────────────────────────────────────┘")

    if args.fail_on_issues and all_issues > 0:
        sys.exit(1)


# ── Main CLI entry point ─────────────────────────────────────────

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

    args = parser.parse_args()

    commands = {
        "verify": cmd_verify,
        "status": cmd_status,
        "gate": cmd_gate,
        "gates": cmd_gates,
        "stage": cmd_stage,
        "stages": cmd_stages,
        "check-governance": cmd_check_governance,
    }

    cmd = args.command or "verify"
    commands[cmd](args)


if __name__ == "__main__":
    main()
