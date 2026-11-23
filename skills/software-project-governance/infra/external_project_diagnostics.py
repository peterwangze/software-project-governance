"""Read-only observations about the target project and its installed governance hooks."""

import hashlib
from pathlib import Path
import re


def target_facts(target):
    target = Path(target).resolve()
    facts = {
        "target": str(target),
        "exists": target.exists(),
        "is_dir": target.is_dir(),
        "file_count": 0,
        "sample_files": [],
    }
    if target.is_dir():
        all_files = []
        for path in target.rglob("*"):
            if not path.is_file():
                continue
            rel_parts = path.relative_to(target).parts
            if any(part in {".git", "node_modules", "__pycache__"} for part in rel_parts):
                continue
            all_files.append(path.relative_to(target).as_posix())
        facts["file_count"] = len(all_files)
        facts["sample_files"] = all_files[:5]
    return facts


def _target_relpath(target, path):
    try:
        return Path(path).resolve().relative_to(Path(target).resolve()).as_posix()
    except (OSError, ValueError):
        return str(path)


def _diagnostic(status, category, path, message, line=None):
    diagnostic = {
        "status": status,
        "category": category,
        "path": path,
        "message": message,
    }
    if line is not None:
        diagnostic["line"] = line
    return diagnostic


def _first_match_line(content, pattern):
    for index, line in enumerate(content.splitlines(), start=1):
        if pattern.search(line):
            return index
    return None


def read_text(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace"), None
    except OSError as exc:
        return None, str(exc)


def _native_entry_paths(target, entry_files):
    target = Path(target).resolve()
    paths = []
    for rel in entry_files:
        path = target / rel
        if path.is_file():
            paths.append(path)
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    paths.append(child)
    return paths


def _native_entry_diagnostics(target, entry_files, entry_patterns, read_text):
    target = Path(target).resolve()
    diagnostics = []
    for path in _native_entry_paths(target, entry_files):
        rel = _target_relpath(target, path)
        content, error = read_text(path)
        if content is None:
            diagnostics.append(_diagnostic(
                "FAIL",
                "target-native-entry",
                rel,
                f"cannot read platform/native entry file: {error}",
            ))
            continue
        matched = False
        for label, pattern, message in entry_patterns:
            line = _first_match_line(content, pattern)
            if line is None:
                continue
            matched = True
            diagnostics.append(_diagnostic(
                "FAIL",
                "target-native-entry",
                rel,
                f"{label}: {message}",
                line=line,
            ))
        if not matched:
            diagnostics.append(_diagnostic(
                "PASS",
                "target-native-entry",
                rel,
                "no repo-local workflow path assumptions detected",
            ))
    if not diagnostics:
        diagnostics.append(_diagnostic(
            "INFO",
            "target-native-entry",
            ".",
            "no platform/native entry files detected",
        ))
    return diagnostics


def _hook_version(content):
    match = re.search(r"@version:\s*([0-9]+\.[0-9]+\.[0-9]+)", content)
    return match.group(1) if match else None


def canonical_hook_text(hook_name, root):
    hook_path = Path(root) / "skills/software-project-governance/infra/hooks" / hook_name
    if not hook_path.is_file():
        return None
    return hook_path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def _hook_sha(content):
    return hashlib.sha256(content.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def _pre_commit_uses_legacy_message_source(content):
    patterns = (
        r"\b(cat|grep|sed|awk|head|tail)\b[^\n]*(COMMIT_EDITMSG|GOV_COMMIT_MSG)",
        r"\b(read)\b[^\n]*(COMMIT_EDITMSG|GOV_COMMIT_MSG)",
        r"(COMMIT_MSG(?!_PATH)|COMMIT_MESSAGE(?!_PATH)|MESSAGE_TEXT|TASK_ID|TASK_PREFIX)[A-Za-z0-9_]*=.*(COMMIT_EDITMSG|GOV_COMMIT_MSG)",
    )
    for pattern in patterns:
        if re.search(pattern, content):
            return True
    return False


def _pre_commit_uses_repo_local_self_upgrade(content):
    has_resolved_home_upgrade = "SPG_RESOLVED_HOME/infra/hooks" in content
    if has_resolved_home_upgrade:
        return False
    return bool(re.search(
        r"(SOURCE_HOOK|cp|HOOK_SOURCE|LATEST_HOOK)[^\n]*skills/software-project-governance/infra/hooks",
        content,
    ))


def _hook_diagnostics(target, required_hooks, read_text, canonical_hook_text):
    target = Path(target).resolve()
    git_dir = target / ".git"
    if not git_dir.is_dir():
        return [_diagnostic(
            "INFO",
            "target-installed-hook",
            ".git/hooks",
            "target is not a git worktree; installed hook checks skipped",
        )]

    diagnostics = []
    hooks_dir = git_dir / "hooks"
    for hook_name in required_hooks:
        rel = f".git/hooks/{hook_name}"
        installed_hook = hooks_dir / hook_name
        if not installed_hook.is_file():
            diagnostics.append(_diagnostic(
                "FAIL",
                "target-installed-hook",
                rel,
                "required governance hook is missing from target .git/hooks",
            ))
            continue

        installed_text, error = read_text(installed_hook)
        if installed_text is None:
            diagnostics.append(_diagnostic(
                "FAIL",
                "target-installed-hook",
                rel,
                f"cannot read installed governance hook: {error}",
            ))
            continue
        installed_text = installed_text.replace("\r\n", "\n")
        source_text = canonical_hook_text(hook_name)
        if source_text is None:
            diagnostics.append(_diagnostic(
                "FAIL",
                "target-installed-hook",
                rel,
                "canonical governance hook source is missing from validation package",
            ))
            continue

        installed_version = _hook_version(installed_text) or "unknown"
        source_version = _hook_version(source_text) or "unknown"
        if installed_version != source_version:
            diagnostics.append(_diagnostic(
                "FAIL",
                "target-installed-hook",
                rel,
                f"installed hook @version={installed_version}, expected={source_version}",
            ))
        elif _hook_sha(installed_text) != _hook_sha(source_text):
            diagnostics.append(_diagnostic(
                "FAIL",
                "target-installed-hook",
                rel,
                "installed hook content differs from canonical governance hook source",
            ))
        else:
            diagnostics.append(_diagnostic(
                "PASS",
                "target-installed-hook",
                rel,
                f"installed hook matches canonical source @version={source_version}",
            ))

        if hook_name == "pre-commit":
            if _pre_commit_uses_legacy_message_source(installed_text):
                diagnostics.append(_diagnostic(
                    "FAIL",
                    "target-installed-hook",
                    rel,
                    "legacy pre-commit uses COMMIT_EDITMSG or GOV_COMMIT_MSG as a semantic message source",
                ))
            if _pre_commit_uses_repo_local_self_upgrade(installed_text):
                diagnostics.append(_diagnostic(
                    "FAIL",
                    "target-installed-hook",
                    rel,
                    "pre-commit self-upgrade source hardcodes repo-local skills/software-project-governance/infra/hooks",
                ))
    return diagnostics


def target_native_diagnostics(target, *, entry_files, entry_patterns, required_hooks,
                              read_text, canonical_hook_text):
    return (
        _native_entry_diagnostics(target, entry_files, entry_patterns, read_text)
        + _hook_diagnostics(target, required_hooks, read_text, canonical_hook_text)
    )


def diagnostic_issues(diagnostics):
    return [
        f"{item['category']} {item['path']}: {item['message']}"
        for item in diagnostics
        if item.get("status") == "FAIL"
    ]
