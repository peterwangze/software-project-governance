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


def _version_tuple(version: str) -> tuple:
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return ()


def _tracked_entry_files(root: Path, names) -> set:
    """Return the subset of ``names`` tracked by git in ``root`` (FIX-285).

    Mirrors the ``_tracked_target_files`` git-probe shape of checks/projection.py:
    a non-git directory or an unavailable git yields an empty set, so callers
    treat entry copies as untracked (advisory face) instead of failing.
    """
    if not (root / ".git").exists():
        return set()
    import subprocess

    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--", *names],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip() in names}


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
    # Bootstrap marker face guard (FIX-285 / DEC-173③ / REL-071 F-3).
    # Entry files: AGENTS.md (tracked) + CLAUDE.md (gitignored local sync, FIX-256).
    # Stale tracked marker -> FAIL; stale untracked local copy -> [WARN] advisory
    # (REL-071 F-2/BC-3: the root CLAUDE.md is local-only; FIX-238.2 fail-closed
    # covers its re-sync). A tracked entry file without a marker header is stale
    # per the G-series rule (missing header = pre-0.73.0). Absent files skip.
    entry_names = ("AGENTS.md", "CLAUDE.md")
    tracked = _tracked_entry_files(host_root, entry_names)
    for name in entry_names:
        entry = host_root / name
        if not entry.is_file():
            continue
        match = re.search(r"@bootstrap-version:\s*([0-9]+\.[0-9]+\.[0-9]+)", entry.read_text(encoding="utf-8"))
        if not match:
            if name in tracked:
                issues.append(f"[FAIL] {name}: @bootstrap-version marker NOT FOUND (missing header = stale, expected={source})")
            continue
        if _version_tuple(match.group(1)) < _version_tuple(source):
            if name in tracked:
                issues.append(f"[FAIL] {name}: @bootstrap-version={match.group(1)} is stale (< active_version {source})")
            else:
                issues.append(f"[WARN] {name}: @bootstrap-version={match.group(1)} is stale (< active_version {source}); untracked local copy — advisory (FIX-238.2 fail-closed covers re-sync)")
    return issues
