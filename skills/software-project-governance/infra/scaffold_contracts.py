"""Validate and render deterministic delivery scaffold templates."""

import re
from typing import NamedTuple
from pathlib import Path


from contracts import QUALITY_BUDGET_DIMENSIONS


DETERMINISTIC_SCAFFOLD_REQUIRED_SECTIONS = (
    "## Product Success Contract",
    "## PRD-lite",
    "## Executable Acceptance",
    "## Quality Budget",
    "## Vertical Slice",
    "## Demo Checklist",
    "## Tooling",
)

DETERMINISTIC_SCAFFOLD_REQUIRED_QUALITY_DIMENSIONS = QUALITY_BUDGET_DIMENSIONS

DETERMINISTIC_SCAFFOLD_COMMAND_RE = re.compile(
    r"(?m)^\s*-\s*`(?:(?:python|pytest|node|npm|pnpm|yarn|uv|bash|sh|make|go|cargo|npx|powershell|pwsh)\b|"
    r"(?:\./|\.\\|skills/|skills\\|scripts/|scripts\\).+)",
    re.IGNORECASE,
)

DETERMINISTIC_SCAFFOLD_SIGNAL_RE = re.compile(
    r"(?:persona|jtbd|job to be done|non-goal|success metric|acceptance|quality budget|demo checklist|"
    r"vertical slice|rollback|PRD-lite|用户|验收|质量预算|演示|切片)",
    re.IGNORECASE,
)

DETERMINISTIC_SCAFFOLD_WEAK_RE = re.compile(
    r"(?:review says|review passed|reviewer approved|approved.*prose|looks good|manual review only|"
    r"ship it|whatever|\bTODO\b|\bTBD\b|\bTO_BE_DEFINED\b|待补|待定|占位)",
    re.IGNORECASE,
)

DETERMINISTIC_SCAFFOLD_BROAD_SCOPE_RE = re.compile(
    r"(?:entire repository|whole repository|whole repo|full repo|entire repo|"
    r"entire project|whole project|whole codebase|all files|everything|\*|全仓|整个项目|所有文件|全部重构|无边界)",
    re.IGNORECASE,
)

DETERMINISTIC_SCAFFOLD_SECTION_SIGNALS = {
    "## Product Success Contract": (
        r"(?:persona|用户|使用者)",
        r"(?:jtbd|job to be done|desired outcome|用户任务)",
        r"(?:non-goal|out of scope|非目标)",
        r"(?:success metric|metric|成功指标)",
    ),
    "## PRD-lite": (
        r"(?:problem|问题)",
        r"(?:workflow|scenario|user-visible|用户可见|流程|场景)",
    ),
    "## Executable Acceptance": (
        r"(?:expected output|exit code|pass|通过|预期输出)",
        r"(?:demo evidence|evidence|artifact|证据)",
    ),
    "## Quality Budget": tuple(DETERMINISTIC_SCAFFOLD_REQUIRED_QUALITY_DIMENSIONS),
    "## Vertical Slice": (
        r"(?:user-visible slice|user can|用户可见|用户)",
        r"(?:demo path|demo|smoke|command|演示)",
        r"(?:scope guard|scope|范围)",
        r"(?:rollback|回滚)",
    ),
    "## Demo Checklist": (
        r"(?:command|demo|evidence|exit code|artifact|演示|证据)",
        r"(?:expected|visible|invalid|failure|result|预期|结果)",
    ),
    "## Tooling": (
        r"(?:check-product-success-contracts|check-acceptance-contracts|check-quality-budget|check-vertical-slices|check-deterministic-scaffolds)",
    ),
}


class ScaffoldPolicy(NamedTuple):
    types: tuple
    sections: tuple
    quality_dimensions: tuple
    command: re.Pattern
    signal: re.Pattern
    weak: re.Pattern
    broad_scope: re.Pattern
    section_signals: dict


def _scaffold_dir(override, default):
    return Path(override) if override is not None else default


def render_deterministic_scaffold(scaffold_type, scaffold_dir, types, *, default_dir):
    """FIX-092: render a deterministic scaffold template by type."""
    if scaffold_type not in types:
        valid = ", ".join(types)
        raise ValueError(f"unknown scaffold type '{scaffold_type}'. Valid types: {valid}")
    path = _scaffold_dir(scaffold_dir, default_dir) / f"{scaffold_type}.md"
    if not path.exists():
        raise FileNotFoundError(f"missing scaffold template: {path}")
    return path.read_text(encoding="utf-8")


def _extract_markdown_section_body(text, heading):
    pattern = re.compile(rf"(?ms)^{re.escape(heading)}\s*\n(.*?)(?=^## |\Z)")
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _validate_deterministic_scaffold_text(scaffold_type, text, policy: ScaffoldPolicy):
    issues = []
    if not isinstance(text, str) or len(text.strip()) < 800:
        return [f"{scaffold_type}: scaffold template must be substantial and non-empty"]
    if policy.weak.search(text):
        issues.append(f"{scaffold_type}: scaffold must not contain placeholders or review/prose-only language")
    for section in policy.sections:
        if section not in text:
            issues.append(f"{scaffold_type}: missing section {section}")
            continue
        body = _extract_markdown_section_body(text, section)
        bullets = re.findall(r"(?m)^\s*-\s+\S", body)
        if len(body) < 120 or len(bullets) < 2:
            issues.append(f"{scaffold_type}: section {section} must contain substantive scaffold bullets")
        for signal in policy.section_signals.get(section, ()):
            if not re.search(signal, body, re.IGNORECASE):
                issues.append(f"{scaffold_type}: section {section} missing required signal {signal}")
    if not policy.command.search(text):
        issues.append(f"{scaffold_type}: missing runnable command bullet in backticks")
    if not policy.signal.search(text):
        issues.append(f"{scaffold_type}: missing product success, acceptance, quality, demo, or slice signals")
    lower_text = text.lower()
    for dimension in policy.quality_dimensions:
        if dimension not in lower_text:
            issues.append(f"{scaffold_type}: missing quality dimension {dimension}")
    if policy.broad_scope.search(text):
        issues.append(f"{scaffold_type}: scaffold scope guard must not allow whole-project/all-files delivery")
    return issues


def check_deterministic_scaffolds(scaffold_dir, policy: ScaffoldPolicy, *, default_dir):
    """FIX-092: verify weak-LLM deterministic scaffold templates and generator index."""
    base = _scaffold_dir(scaffold_dir, default_dir)
    result = {
        "required_types": list(policy.types),
        "entries": [],
        "issues": [],
        "pass": True,
    }
    index_path = base / "index.md"
    if not base.exists():
        result["pass"] = False
        result["issues"].append(f"missing scaffold directory: {base}")
        return result
    if not index_path.exists():
        result["pass"] = False
        result["issues"].append(f"missing scaffold index: {index_path}")
        index_text = ""
    else:
        index_text = index_path.read_text(encoding="utf-8")
        if "generate-deterministic-scaffold" not in index_text:
            result["pass"] = False
            result["issues"].append("scaffold index must document generate-deterministic-scaffold")
        for scaffold_type in policy.types:
            if f"{scaffold_type}.md" not in index_text:
                result["pass"] = False
                result["issues"].append(f"scaffold index missing {scaffold_type}.md")

    for scaffold_type in policy.types:
        # The index uses the selected asset directly. Each template lookup
        # historically received that base as an explicit filesystem path.
        path = Path(base) / f"{scaffold_type}.md"
        if not path.exists():
            issues = [f"missing scaffold template: {path}"]
        else:
            issues = _validate_deterministic_scaffold_text(scaffold_type, path.read_text(encoding="utf-8"), policy)
        status = "PASS" if not issues else "FAIL"
        if issues:
            result["pass"] = False
        result["entries"].append({"scaffold_type": scaffold_type, "path": str(path), "status": status, "issues": issues})
    return result
