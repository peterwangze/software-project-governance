from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = {
    "README": ROOT / "README.md",
    "Workflow Schema": ROOT / "protocol/workflow-schema.md",
    "Plugin Contract": ROOT / "protocol/plugin-contract.md",
    "Workflow Manifest": ROOT / "workflows/software-project-governance/manifest.md",
    "Company Practices": ROOT / "workflows/software-project-governance/research/company-practices.md",
    "Lifecycle Rules": ROOT / "workflows/software-project-governance/rules/lifecycle.md",
    "Stage Gates": ROOT / "workflows/software-project-governance/rules/stage-gates.md",
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
}

REQUIRED_SNIPPETS = {
    ROOT / "README.md": [
        "## 当前目标",
        "低侵入优先",
        "repo-local 探索性接法",
    ],
    ROOT / "protocol/workflow-schema.md": [
        "## 通用对象模型",
        "### 1. Workflow",
        "### 3. Gate",
    ],
    ROOT / "protocol/plugin-contract.md": [
        "## 最小承载单元",
        "## Skill / Plugin 行为描述要素",
        "software-project-governance",
    ],
    ROOT / "workflows/software-project-governance/manifest.md": [
        "supported_agents",
        "Claude",
        "Codex",
    ],
    ROOT / "workflows/software-project-governance/rules/lifecycle.md": [
        "## 阶段列表",
        "### 开发",
        "## 统一要求",
    ],
    ROOT / "workflows/software-project-governance/rules/stage-gates.md": [
        "## G1 - 立项完成",
        "## G8 - 维护闭环",
        "## Gate 执行原则",
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
        "## 适配原则",
        "## TODO",
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
