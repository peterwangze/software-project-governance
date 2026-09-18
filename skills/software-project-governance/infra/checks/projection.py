"""Phase 6 projection check adapter."""

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Optional

from release.projection import check_projections, write_projections
from .version import extract_skill_version


def _normalized_hash(path: Path) -> str:
    return sha256(path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")).hexdigest()


def _tracked_target_files(root: Path, target_dir: Path) -> Optional[set[str]]:
    if not (root / ".git").exists():
        return None
    import subprocess
    try:
        relative = target_dir.relative_to(root).as_posix()
    except ValueError:
        return None
    result = subprocess.run(["git", "-C", str(root), "ls-files", "--", relative], capture_output=True,
                            text=True, encoding="utf-8", errors="replace", check=False, timeout=15)
    if result.returncode != 0:
        return None
    prefix = relative.rstrip("/") + "/"
    return {line[len(prefix):] for line in result.stdout.splitlines() if line.startswith(prefix)}


def _legacy_projection_sync(root: Path, target_dir: Path, patterns) -> dict:
    issues = []
    skipped = []
    tracked = _tracked_target_files(root, target_dir)
    source_version = extract_skill_version(root / "skills/software-project-governance/SKILL.md")
    version_checks = []
    sources = [
        ("source core manifest", root / "skills/software-project-governance/core/manifest.json", "json"),
        ("source Claude plugin", root / ".claude-plugin/plugin.json", "json"),
        ("source Codex plugin", root / ".codex-plugin/plugin.json", "json"),
        ("source Chrys plugin", root / ".chrys-plugin/plugin.json", "json"),
        ("target workflow skill", target_dir / "skills/software-project-governance/SKILL.md", "skill"),
        ("target plan-tracker", target_dir / ".governance/plan-tracker.md", "plan"),
    ]
    for label, path, kind in sources:
        observed = ""
        try:
            if kind == "json": observed = str(json.loads(path.read_text(encoding="utf-8")).get("version", ""))
            elif kind == "skill": observed = extract_skill_version(path)
            else:
                match = re.search(r"工作流版本.*?([0-9]+\.[0-9]+\.[0-9]+)", path.read_text(encoding="utf-8"))
                observed = match.group(1) if match else ""
        except (OSError, json.JSONDecodeError):
            observed = ""
        version_checks.append({"label": label, "path": str(path), "version": observed})
        if not observed or observed != source_version:
            issues.append(f"{label}: version {observed or 'missing'} != source {source_version}")
    files = set()
    for pattern in patterns:
        files.update(path.relative_to(root).as_posix() for path in root.glob(pattern) if path.is_file())
    compared = 0
    for relative in sorted(files):
        if tracked is not None and relative not in tracked:
            skipped.append(relative); continue
        target = target_dir / relative
        if not target.is_file():
            issues.append(f"target fixture missing mirrored file: {relative}"); continue
        compared += 1
        if _normalized_hash(root / relative) != _normalized_hash(target):
            issues.append(f"target fixture drift: {relative}")
    return {"pass": not issues, "state": "PASS" if not issues else "FAIL", "issues": issues,
            "source_version": source_version, "mirrors_checked": compared, "mirrors_discovered": len(files),
            "mirrors_skipped_untracked": len(set(skipped)), "version_checks": version_checks}


def check_projection_sync(root: Path, target_dir: Optional[Path] = None, patterns=None,
                          config_path: Optional[Path] = None) -> dict:
    if target_dir is not None or patterns is not None:
        return _legacy_projection_sync(root, target_dir or root / "project/e2e-test-project", patterns or ())
    result = check_projections(root, config_path).as_dict()
    return {**result, "mirrors_checked": result.get("projections_checked", 0),
            "mirrors_discovered": result.get("projections_checked", 0), "mirrors_skipped_untracked": 0,
            "version_checks": []}


def write_projection_sync(root: Path, config_path: Optional[Path] = None) -> dict:
    return write_projections(root, config_path).as_dict()


def check_entry_bootstrap_sync(root: Optional[Path] = None) -> dict:
    """FEAT-037: entry-file bootstrap projection guard.

    Validates that every platform-native entry bootstrap section is exactly
    the canonical template projection: the primary entry carries the full
    governance-init.md Step 7 template, the secondary entry carries the
    rendered thin pointer (≤40 lines / ≤3072 bytes, minimal survival checks
    intact), and a dual-full workspace is a FAIL.  Guarded surfaces:
    the dev-repo root (AGENTS.md/CLAUDE.md) and the e2e dual-entry fixture.

    Root resolves to the repository root WITHOUT importing verify_workflow
    (ArchGuard R2 bans new reverse-dependency sites in checks/ modules).
    """
    root = Path(root) if root is not None else Path(__file__).resolve().parents[4]
    from sync_entry_projection import CanonicalSourceError, build_sync_report

    issues: list = []
    targets: list = []
    for label, project_root in (
        ("repo-root", root),
        ("e2e-fixture", root / "project/e2e-test-project"),
    ):
        if not project_root.is_dir():
            issues.append(f"{label}: workspace missing: {project_root}")
            continue
        try:
            report = build_sync_report(project_root, source_root=root)
        except CanonicalSourceError as exc:
            issues.append(f"{label}: canonical source error: {exc}")
            continue
        issues.extend(f"{label}: {issue}" for issue in report["issues"])
        targets.append({
            "label": label,
            "workspace": str(project_root),
            "primary": report["primary"],
            "secondary": report["secondary"],
            "profile": report["profile"],
            "entries": report["entries"],
            "total_section_bytes": report["total_section_bytes"],
        })
    return {"pass": not issues, "issues": issues, "targets": targets}


def print_entry_bootstrap_report(entry_result: dict) -> bool:
    """Render the FEAT-037 entry-bootstrap guard result (always printed)."""
    print("\n=== Entry Bootstrap Sync Check (FEAT-037) ===")
    for target in entry_result["targets"]:
        sizes = ", ".join(
            f"{entry['file']}={entry['bytes']}B/{entry.get('kind', entry['state'])}"
            for entry in target["entries"]
        )
        print(f"  {target['label']}: primary={target['primary']} "
              f"secondary={target['secondary']} profile={target['profile']}")
        print(f"    sections: {sizes}")
    if entry_result["issues"]:
        print(f"\n  Result: FAILED — {len(entry_result['issues'])} issue(s)")
        for issue in entry_result["issues"][:20]:
            print(f"    - {issue}")
        return False
    print("\n  Result: PASSED — entry bootstrap sections synchronized with the canonical templates")
    return True


def cmd_check_entry_bootstrap_sync(args) -> None:
    """Run the FEAT-037 entry-bootstrap projection guard independently."""
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    entry_result = check_entry_bootstrap_sync()
    failed = not print_entry_bootstrap_report(entry_result)
    if failed:
        sys.exit(1)
    print()
