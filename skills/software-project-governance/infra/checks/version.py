"""Phase 6 version extraction and consistency checks."""

import json
from pathlib import Path
import re
from typing import Dict, List, Optional


VERSION_PATHS = {
    "SKILL.md (source of truth)": ("skills/software-project-governance/SKILL.md", "frontmatter"),
    "manifest.json": ("skills/software-project-governance/core/manifest.json", "/version"),
    ".claude-plugin/plugin.json": (".claude-plugin/plugin.json", "/version"),
    ".claude-plugin/marketplace.json": (".claude-plugin/marketplace.json", "/plugins/0/version"),
    ".codex-plugin/plugin.json": (".codex-plugin/plugin.json", "/version"),
    ".zcode-plugin/plugin.json": (".zcode-plugin/plugin.json", "/version"),
    ".chrys-plugin/plugin.json": (".chrys-plugin/plugin.json", "/version"),
}


def extract_skill_version(path: Path) -> str:
    match = re.search(r"^version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else ""


def _pointer(payload: object, pointer: str) -> object:
    current = payload
    for part in pointer[1:].split("/"):
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current


def version_facts(root: Path) -> Dict[str, str]:
    facts = {}
    for label, (relative, selector) in VERSION_PATHS.items():
        path = root / relative
        if selector == "frontmatter":
            facts[label] = extract_skill_version(path) if path.is_file() else ""
        else:
            try:
                facts[label] = str(_pointer(json.loads(path.read_text(encoding="utf-8")), selector))
            except (OSError, ValueError, KeyError, IndexError, json.JSONDecodeError):
                facts[label] = ""
    return facts


def check_version_consistency(root: Path, host_root: Optional[Path] = None) -> List[str]:
    facts = version_facts(root)
    source = facts.get("SKILL.md (source of truth)", "")
    issues = []
    if not source:
        return ["[FAIL] Cannot determine source version from SKILL.md"]
    for label, version in facts.items():
        if label != "SKILL.md (source of truth)" and version != source:
            issues.append(f"[FAIL] {label}: version={version or 'NOT FOUND'}, expected={source}")
    verifier = root / "skills/software-project-governance/infra/verify_workflow.py"
    if verifier.is_file():
        content = verifier.read_text(encoding="utf-8")
        block = re.search(r"REQUIRED_SNIPPETS\s*=\s*\{(?P<body>.*?)\n\}\n{2,}# ── Manifest", content, re.S)
        if not block:
            issues.append("[FAIL] verify_workflow.py snippet: REQUIRED_SNIPPETS block not found")
        else:
            versions = set()
            for line in block.group("body").splitlines():
                if not line.strip().startswith("#"):
                    versions.update(re.findall(r'"([0-9]+\.[0-9]+\.[0-9]+)"', line))
            if any(version != source for version in versions):
                issues.append("[FAIL] verify_workflow.py snippet: hardcoded version mismatch")
    hooks = root / "skills/software-project-governance/infra/hooks"
    for name in ("pre-commit", "commit-msg", "post-commit", "prepare-commit-msg"):
        path = hooks / name
        match = re.search(r"@version:\s*([0-9]+\.[0-9]+\.[0-9]+)", path.read_text(encoding="utf-8")) if path.is_file() else None
        if not match or match.group(1) != source:
            issues.append(f"[FAIL] hooks/{name}: @version={match.group(1) if match else 'NOT FOUND'}, expected={source}")
    changelog = root / "project/CHANGELOG.md"
    if changelog.is_file():
        match = re.search(r"^## \[([0-9]+\.[0-9]+\.[0-9]+)\]", changelog.read_text(encoding="utf-8"), re.MULTILINE)
        if not match or match.group(1) != source:
            issues.append(f"[FAIL] CHANGELOG latest version={match.group(1) if match else 'NOT FOUND'}, expected={source}")
    host_root = host_root or root
    plan = host_root / ".governance/plan-tracker.md"
    if plan.is_file():
        match = re.search(r"工作流版本[^0-9]*([0-9]+\.[0-9]+\.[0-9]+)", plan.read_text(encoding="utf-8"))
        if match and match.group(1) != source:
            issues.append(f"[WARN] plan-tracker workflow version={match.group(1)}, expected={source}")
    return issues
