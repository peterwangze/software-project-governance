"""Installed plugin freshness and the governed Git workspace's untracked files."""
from pathlib import Path

from resolve_entry import current_host_root


def _product_root():
    from project_paths import package_root
    return package_root()


def _platform_entries():
    from plugin_assets import PLATFORM_ENTRY_FILES
    return PLATFORM_ENTRY_FILES


def effective_entry(name, native):
    return native


def check_plugin_freshness():
    """Compare the installed plugin record with the version of this package."""
    import json
    import re
    import subprocess
    from resolve_entry import read_release_version

    def plugin_record(path, *, allow_list=False):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {}
        if isinstance(data, dict):
            data = data.get("plugins")
        elif not allow_list:
            return {}
        if isinstance(data, list):
            for plugin in data:
                if isinstance(plugin, dict) and plugin.get("name") == "software-project-governance":
                    return plugin
        return {}

    def registry_version(record):
        version = record.get("version")
        if isinstance(version, str) and re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}", version):
            return version
        return "unknown"

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
    installed_json = _product_root() / ".claude-plugin" / "installed_plugins.json"
    if not installed_json.exists():
        # Try Claude's global installed_plugins.json
        installed_json = Path.home() / ".claude" / "installed_plugins.json"

    installed = plugin_record(installed_json, allow_list=True)
    result["installed_version"] = registry_version(installed)
    commit, date = installed.get("gitCommitSha"), installed.get("installedAt")
    if isinstance(commit, str) and commit:
        result["installed_commit"] = commit[:7]
    if isinstance(date, str) and date:
        result["installed_date"] = date[:10]

    skill = _product_root() / "skills/software-project-governance/SKILL.md"
    if skill.exists():
        result["source_version"] = read_release_version(skill) or "unknown"
    else:
        marketplace = _product_root() / ".claude-plugin" / "marketplace.json"
        result["source_version"] = registry_version(plugin_record(marketplace))

    # Get source HEAD commit
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True,
            cwd=str(_product_root()), timeout=5
        )
        if r.returncode == 0:
            result["source_commit"] = r.stdout.strip()[:7]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # Determine status
    if result["installed_version"] == "unknown":
        result["status"] = "UNKNOWN (plugin not installed via marketplace?)"
        result["action"] = ("Check the plugin installation and its registered version."
                            if installed_json.exists() else "Run /plugin marketplace add <path> to install.")
    elif result["source_version"] == "unknown":
        result["status"] = "UNKNOWN (source version unavailable)"
        result["action"] = "Check the package SKILL.md version or the legacy marketplace version."
    elif result["installed_version"] == result["source_version"]:
        result["status"] = "UP TO DATE"
        result["action"] = "No action needed."
    else:
        result["status"] = "OUTDATED"
        result["action"] = "Run /plugin update software-project-governance  or  /reload-plugins"

    return result


def cmd_check_plugin_freshness(_args):
    """Check if installed plugin is up to date with the source repository."""
    from workspace_check_cli import report_plugin_freshness
    check = effective_entry("check_plugin_freshness", check_plugin_freshness)
    result = check()
    return report_plugin_freshness(result, _product_root)


def check_untracked_files():
    """Check for untracked files in the working directory (FIX-057 Phase 2).

    Runs ``git ls-files --others --exclude-standard`` and reports any
    untracked files with heuristic classification suggestions.  Ordinary
    scratch files are non-blocking; unignored root platform entry files are
    actionable because they can change agent behavior outside versioned review.

    FIX-270 (mixed-root): the git fact source is the HOST project root
    (HOST_PROJECT_ROOT) — the project being governed — never the plugin
    package root. In dogfood mode (host == plugin) this is unchanged.
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
            cwd=str(current_host_root()), timeout=10
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
            if "/" not in f and f in _platform_entries():
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
