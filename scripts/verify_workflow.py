from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = {
    "README": ROOT / "README.md",
    "Workflow Schema": ROOT / "protocol/workflow-schema.md",
    "Plugin Contract": ROOT / "protocol/plugin-contract.md",
    "External Command Contract": ROOT / "protocol/external-command-contract.md",
    "Headless Runner Sample": ROOT / "protocol/headless-runner-sample.md",
    "Workflow Manifest": ROOT / "workflows/software-project-governance/manifest.md",
    "Company Practices": ROOT / "workflows/software-project-governance/research/company-practices.md",
    "Lifecycle Rules": ROOT / "workflows/software-project-governance/rules/lifecycle.md",
    "Stage Gates": ROOT / "workflows/software-project-governance/rules/stage-gates.md",
    "Profiles": ROOT / "workflows/software-project-governance/rules/profiles.md",
    "Onboarding": ROOT / "workflows/software-project-governance/rules/onboarding.md",
    "Plan Tracker": ROOT / "workflows/software-project-governance/templates/plan-tracker.md",
    "Evidence Template": ROOT / "workflows/software-project-governance/templates/evidence-log.md",
    "Decision Template": ROOT / "workflows/software-project-governance/templates/decision-log.md",
    "Risk Template": ROOT / "workflows/software-project-governance/templates/risk-log.md",
    "Sample Project": ROOT / "workflows/software-project-governance/examples/current-project-sample.md",
    "Sample Evidence": ROOT / "workflows/software-project-governance/examples/current-project-evidence-log.md",
    "Sample Decision": ROOT / "workflows/software-project-governance/examples/current-project-decision-log.md",
    "Sample Risk": ROOT / "workflows/software-project-governance/examples/current-project-risk-log.md",
    "Claude Repository Entry": ROOT / "CLAUDE.md",
    "Claude Skill": ROOT / ".claude/skills/software-project-governance/SKILL.md",
    "Claude Adapter": ROOT / "adapters/claude/README.md",
    "Claude Adapter Manifest": ROOT / "adapters/claude/adapter-manifest.json",
    "Claude Launcher": ROOT / "adapters/claude/launch.py",
    "Codex Adapter": ROOT / "adapters/codex/README.md",
    "Codex Adapter Manifest": ROOT / "adapters/codex/adapter-manifest.json",
    "Codex Launcher": ROOT / "adapters/codex/launch.py",
    "Gemini Adapter": ROOT / "adapters/gemini/README.md",
    "Agent Integration Research": ROOT / "workflows/software-project-governance/research/agent-integration-models.md",
    "Default Product Shape": ROOT / "workflows/software-project-governance/research/default-product-shape.md",
    "External Capability Minimum Validation": ROOT / "workflows/software-project-governance/research/external-capability-minimum-validation.md",
    "Domestic Agent CLI Compatibility": ROOT / "workflows/software-project-governance/research/domestic-agent-cli-compatibility.md",
    "Repo-local Termination Note": ROOT / "workflows/software-project-governance/research/repo-local-termination-note.md",
}

REQUIRED_SNIPPETS = {
    ROOT / "README.md": [
        "## 当前目标",
        "低侵入优先",
        "repo-local 探索性接法",
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
    ROOT / "workflows/software-project-governance/examples/current-project-sample.md": [
        "PLAN-003",
        "default-product-shape.md",
        "OPS-001",
        "已形成 Gemini 兼容路线正式方案",
        "MAINT-003",
        "domestic-agent-cli-compatibility.md",
        "PLAN-004",
        "repo-local-termination-note.md",
        "MAINT-004",
        "external-capability-minimum-validation.md",
        "MAINT-005",
        "external-command-contract.md",
        "MAINT-006",
        "headless-runner-sample.md",
    ],
    ROOT / "workflows/software-project-governance/examples/current-project-decision-log.md": [
        "DEC-008",
        "默认产品形态采用三层结构",
        "DEC-009",
        "Gemini 兼容先走外部能力层",
        "DEC-010",
        "国内 agent CLI 兼容复用统一抽象",
        "DEC-011",
        "repo-local 默认主线正式终止并降级为样例",
        "DEC-015",
        "外部能力层首轮验证先走 shared command",
        "DEC-016",
        "shared command 先固化统一 contract 再映射实现",
        "DEC-017",
        "headless runner 必须严格映射 shared command 契约",
    ],
    ROOT / "workflows/software-project-governance/examples/current-project-risk-log.md": [
        "RISK-009",
        "default-product-shape.md",
        "RISK-002",
        "Gemini 兼容路线正式方案",
        "RISK-010",
        "domestic-agent-cli-compatibility.md",
        "RISK-006",
        "repo-local-termination-note.md",
        "RISK-004",
        "样例台账瘦身",
        "RISK-012",
        "external-capability-minimum-validation.md",
        "RISK-013",
        "external-command-contract.md",
        "RISK-014",
        "headless-runner-sample.md",
    ],
    ROOT / "workflows/software-project-governance/examples/current-project-evidence-log.md": [
        "EVD-018",
        "默认产品形态方案",
        "EVD-019",
        "Gemini 兼容路线正式方案",
        "EVD-020",
        "国内 agent CLI 兼容抽象正式文档",
        "EVD-021",
        "repo-local 默认主线终止说明正式文档",
        "EVD-024",
        "维护阶段首轮治理闭环",
        "EVD-025",
        "external runner / shared command",
        "EVD-026",
        "software-project-governance.run",
        "EVD-027",
        "software-project-governance.headless",
    ],
    ROOT / "workflows/software-project-governance/examples/current-project-sample.md": [
        "RESEARCH-001",
        "已形成正式调研结论文件",
    ],
    ROOT / "workflows/software-project-governance/examples/current-project-decision-log.md": [
        "DEC-007",
        "低侵入集成作为默认产品方向",
    ],
    ROOT / "workflows/software-project-governance/examples/current-project-risk-log.md": [
        "RISK-007",
        "已完成 `RESEARCH-001` 并形成正式调研文档",
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
    ],
    ROOT / "protocol/external-command-contract.md": [
        "## 目标",
        "software-project-governance.run",
        "## 最小输入",
        "## 最小输出",
        "## write-back targets",
        "## replacement boundary",
    ],
    ROOT / "protocol/headless-runner-sample.md": [
        "## 目标",
        "software-project-governance.headless",
        "## 输入映射",
        "## execution mode",
        "dry-run",
        "## 最小返回样例",
    ],
    ROOT / "workflows/software-project-governance/manifest.md": [
        "supported_agents",
        "Claude",
        "Codex",
    ],
    ROOT / "workflows/software-project-governance/rules/lifecycle.md": [
        "## 阶段列表",
        "### 6. 开发实现",
        "## 统一要求",
        "## 触发模式",
    ],
    ROOT / "workflows/software-project-governance/rules/stage-gates.md": [
        "## G1 — 立项完成",
        "## G11 — 维护闭环",
        "## Gate 执行原则",
        "## Gate 裁剪规则",
    ],
    ROOT / "workflows/software-project-governance/rules/profiles.md": [
        "## 预设 Profile",
        "### lightweight",
        "### standard",
        "### strict",
    ],
    ROOT / "workflows/software-project-governance/rules/onboarding.md": [
        "## 接入流程",
        "## 最小接入路径",
        "passed-on-entry",
    ],
    ROOT / "CLAUDE.md": [
        "software-project-governance",
        ".claude/skills/software-project-governance/SKILL.md",
        "仓库级约束尽量保持最小化",
    ],
    ROOT / ".claude/skills/software-project-governance/SKILL.md": [
        "# Software Project Governance",
        "## Required read order",
        "python scripts/verify_workflow.py",
    ],
    ROOT / "adapters/claude/README.md": [
        "## Claude 入口约定",
        "## 原生 skill 入口",
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
        "## Codex 入口约定",
        "## 半可执行入口",
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
    ROOT / "workflows/software-project-governance/examples/current-project-sample.md": [
        "## 项目总览",
        "## 样例跟踪表",
        "Claude",
    ],
}


def check_files():
    failures = []
    for label, path in REQUIRED_FILES.items():
        if path.is_file():
            print(f"[OK] file exists: {label} -> {path.relative_to(ROOT)}")
        else:
            failures.append(f"missing file: {label} -> {path.relative_to(ROOT)}")
            print(f"[FAIL] missing file: {label} -> {path.relative_to(ROOT)}")
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
                print(f"[FAIL] snippet missing: {path.relative_to(ROOT)} :: {snippet}")
    return failures


def main():
    print("== Workflow Plugin Verification ==")
    file_failures = check_files()
    snippet_failures = check_snippets()
    failures = file_failures + snippet_failures

    if failures:
        print("== Verification Result: FAILED ==")
        for failure in failures:
            print(f" - {failure}")
        sys.exit(1)

    print("== Verification Result: PASSED ==")


if __name__ == "__main__":
    main()
