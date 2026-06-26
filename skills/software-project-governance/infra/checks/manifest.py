"""Manifest domain checks — extracted from verify_workflow.py in 0.59.0.

Scope (DEC-083 Phase 1 / REQ-102): manifest.json canonical-set consistency,
critical product-artifact guards (FIX-110), and cleanup-scope sync.

This module owns the manifest check domain. Shared helpers that are still
defined in verify_workflow.py (`_display_path`, `_git_files`,
`PLUGIN_SCOPE_DIRS`, `ROOT`) are reached through a deferred module reference
rather than a top-level import, so that verify_workflow.py can import this
module at module load time without creating an import cycle. When the
common-helpers domain is extracted in a later release, these references
will be retargeted to that module.

See docs/requirements/verify-workflow-split-phase1-manifest-domain-0.59.0.md
for the design and the line-number baseline used during extraction.
"""

import sys
import json
from pathlib import Path


# ── Shared-helper access (deferred to avoid import cycle) ──────────
# verify_workflow.py imports this module at load time. Reaching the
# shared helpers via a module reference (instead of `from verify_workflow
# import ...`) keeps the two modules from locking each other during
# initialization. The helpers are module-level attributes of
# verify_workflow.py, so they are available whenever a check here runs.

_VW_CACHE = None


def _vw():
    """Return the verify_workflow module (imported lazily, cached).

    Cached so repeated calls reuse the same module reference instead of
    re-resolving the import on every invocation (REVIEW-FIX-153 P2).
    """
    global _VW_CACHE
    if _VW_CACHE is None:
        import verify_workflow  # noqa: WPS433 (deferred import on purpose)
        _VW_CACHE = verify_workflow
    return _VW_CACHE


def _display_path(path, root=None):
    return _vw()._display_path(path, root)


def _git_files(args):
    return _vw()._git_files(args)


def _root():
    return _vw().ROOT


# ── Manifest-based REQUIRED_FILES builder ─────────────────────────

def _path_to_label(relative_path_str):
    """Generate a human-readable label from a relative path."""
    import pathlib as _pl
    path = _pl.PurePosixPath(relative_path_str.replace("\\", "/"))
    parts = path.parts
    filename = path.stem

    if path.name == "SKILL.md":
        if len(parts) >= 2:
            return f"Skill: {parts[-2]}"
    if path.name == "README.md":
        if len(parts) >= 2:
            return f"Readme: {parts[-2]}"
    if path.name == "plugin.json":
        if len(parts) >= 3:
            return f"Plugin JSON: {parts[-3]}/{parts[-2]}"
    if path.name == "marketplace.json":
        if len(parts) >= 3:
            return f"Marketplace JSON: {parts[-3]}/{parts[-2]}"
    if path.name.endswith(".json"):
        if len(parts) >= 3:
            return f"{parts[-2]}/{path.name}"

    label = filename.replace("-", " ").replace("_", " ").title()
    if len(parts) >= 3:
        return f"{parts[-2]}/{label}"
    return label


def build_required_files_from_manifest(manifest_path=None):
    """Build REQUIRED_FILES-equivalent dict from manifest.json.

    Expands product + repo_only entries and glob_patterns into a
    {label: Path} mapping.  Returns None when manifest.json is not
    available or cannot be parsed — the caller should fall back to
    the hard-coded builtin dicts.
    """
    import json as _json

    ROOT = _root()
    if manifest_path is None:
        manifest_path = ROOT / "skills/software-project-governance/core/manifest.json"

    if not manifest_path.is_file():
        return None

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = _json.load(f)
    except (_json.JSONDecodeError, KeyError):
        return None

    result = {}
    seen_labels = set()

    def _add(relpath_str, label=None):
        nonlocal result, seen_labels
        if label is None:
            label = _path_to_label(relpath_str)
        # De-duplicate: append path suffix if label already used
        if label in seen_labels:
            label = f"{label} ({relpath_str})"
        seen_labels.add(label)
        result[label] = ROOT / relpath_str

    # root_entries
    root_entries = manifest.get("root_entries", {})
    for f in root_entries.get("files", []):
        _add(f)

    for section_name in ("product", "repo_only"):
        section = manifest.get(section_name, {})
        entries = section.get("entries", [])
        glob_patterns = section.get("glob_patterns", [])

        for entry in entries:
            if entry.get("type") == "file":
                _add(entry["path"])

        for pattern in glob_patterns:
            for rp in sorted(ROOT.glob(pattern)):
                if rp.is_file():
                    rel = str(rp.relative_to(ROOT)).replace("\\", "/")
                    _add(rel)

    for artifact in manifest.get("canonical_product_artifacts", {}).get("entries", []):
        if artifact.get("type") == "file" and artifact.get("path"):
            _add(artifact["path"], label=f"Canonical artifact: {artifact.get('id', artifact['path'])}")

    if result:
        print(f"[INFO] REQUIRED_FILES loaded from manifest.json ({len(result)} entries)")
    return result


def expand_manifest_to_canonical_set(manifest_path=None):
    """Expand manifest.json entries + glob_patterns into a canonical
    set of relative-paths-as-strings.

    Includes product *and* repo_only sections because this function
    runs against the development repository, not a user install.
    """
    import json as _json

    ROOT = _root()
    if manifest_path is None:
        manifest_path = ROOT / "skills/software-project-governance/core/manifest.json"

    if not manifest_path.is_file():
        return None

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = _json.load(f)

    canonical = set()

    # root_entries
    root_entries = manifest.get("root_entries", {})
    for f in root_entries.get("files", []):
        canonical.add(f)
    for d in root_entries.get("directories", []):
        canonical.add(d.rstrip("/") + "/")

    for section_name in ("product", "repo_only"):
        section = manifest.get(section_name, {})
        entries = section.get("entries", [])
        glob_patterns = section.get("glob_patterns", [])

        for entry in entries:
            p = entry["path"]
            if entry.get("type") == "file":
                canonical.add(p)
            elif entry.get("type") == "dir":
                canonical.add(p.rstrip("/") + "/")

        for pattern in glob_patterns:
            for rp in ROOT.glob(pattern):
                if rp.is_file():
                    rel = str(rp.relative_to(ROOT)).replace("\\", "/")
                    canonical.add(rel)

    for artifact in manifest.get("canonical_product_artifacts", {}).get("entries", []):
        artifact_path = artifact.get("path")
        if artifact.get("type") == "file" and artifact_path:
            canonical.add(artifact_path)

    return canonical


def _manifest_product_file_entries(manifest):
    return {
        entry.get("path")
        for entry in manifest.get("product", {}).get("entries", [])
        if entry.get("type") == "file" and entry.get("path")
    }


def _manifest_artifact_entries(manifest):
    entries = manifest.get("canonical_product_artifacts", {}).get("entries")
    return entries if isinstance(entries, list) else []


def check_manifest_canonical_product_artifacts(manifest, manifest_path=None):
    """FIX-110: critical product artifacts must be explicit, tracked, and validated."""
    ROOT = _root()
    manifest_path = manifest_path or ROOT / "skills/software-project-governance/core/manifest.json"
    display = _display_path(manifest_path)
    failures = []

    section = manifest.get("canonical_product_artifacts")
    if not isinstance(section, dict):
        return [f"{display}: missing canonical_product_artifacts section"]

    entries = _manifest_artifact_entries(manifest)
    if not entries:
        return [f"{display}: canonical_product_artifacts.entries must be a non-empty list"]

    product_file_entries = _manifest_product_file_entries(manifest)
    tracked_files = _git_files(["ls-files", "--cached"])
    artifact_by_id = {entry.get("id"): entry for entry in entries if isinstance(entry, dict)}

    registry_entry = artifact_by_id.get("governance-pack-registry")
    if not registry_entry:
        failures.append(f"{display}: canonical product artifact `governance-pack-registry` is required")
    capability_registry_entry = artifact_by_id.get("capability-registry")
    if not capability_registry_entry:
        failures.append(f"{display}: canonical product artifact `capability-registry` is required")
    lifecycle_registry_entry = artifact_by_id.get("lifecycle-registry")
    if not lifecycle_registry_entry:
        failures.append(f"{display}: canonical product artifact `lifecycle-registry` is required")

    for entry in entries:
        if not isinstance(entry, dict):
            failures.append(f"{display}: canonical product artifact entries must be objects")
            continue
        artifact_id = entry.get("id")
        artifact_path = entry.get("path")
        artifact_label = f"{display}: canonical product artifact `{artifact_id or '<missing>'}`"

        for field in ("id", "path", "type", "required", "artifact_role", "validation_commands"):
            if field not in entry:
                failures.append(f"{artifact_label}: missing `{field}`")

        if entry.get("type") != "file":
            failures.append(f"{artifact_label}: type must be file")

        if not isinstance(artifact_path, str) or not artifact_path.strip():
            failures.append(f"{artifact_label}: path must be a non-empty string")
            continue
        artifact_path = artifact_path.replace("\\", "/")

        if artifact_path.startswith(".governance/"):
            failures.append(f"{artifact_label}: governance runtime files cannot be canonical product artifacts")

        if artifact_path not in product_file_entries:
            failures.append(f"{artifact_label}: path `{artifact_path}` must be an explicit product file entry")

        if entry.get("required") is not True:
            failures.append(f"{artifact_label}: required must be true")

        if not (ROOT / artifact_path).is_file():
            failures.append(f"{artifact_label}: path `{artifact_path}` is missing on disk")

        if tracked_files is not None and artifact_path not in tracked_files:
            failures.append(f"{artifact_label}: path `{artifact_path}` must be tracked by git")

        commands = entry.get("validation_commands")
        if not isinstance(commands, list) or not all(isinstance(cmd, str) and cmd.strip() for cmd in commands):
            failures.append(f"{artifact_label}: validation_commands must be a non-empty string list")
            continue

        if artifact_id == "governance-pack-registry":
            required_commands = ("check-governance-packs", "check-manifest-consistency")
            for command_token in required_commands:
                if not any(command_token in command for command in commands):
                    failures.append(f"{artifact_label}: validation_commands must include `{command_token}`")
        if artifact_id == "capability-registry":
            required_commands = ("check-capability-registry", "check-manifest-consistency")
            for command_token in required_commands:
                if not any(command_token in command for command in commands):
                    failures.append(f"{artifact_label}: validation_commands must include `{command_token}`")
        if artifact_id == "lifecycle-registry":
            required_commands = ("check-lifecycle-registry", "check-manifest-consistency")
            for command_token in required_commands:
                if not any(command_token in command for command in commands):
                    failures.append(f"{artifact_label}: validation_commands must include `{command_token}`")

    return failures


def check_manifest_cleanup_scope(manifest, manifest_path=None):
    """FIX-110: cleanup.py scan scope must be manifest-declared and verifier-synced."""
    ROOT = _root()
    manifest_path = manifest_path or ROOT / "skills/software-project-governance/core/manifest.json"
    display = _display_path(manifest_path)
    section = manifest.get("cleanup_scope")
    if not isinstance(section, dict):
        return [f"{display}: missing cleanup_scope section"]

    directories = section.get("directories")
    if not isinstance(directories, list) or not all(isinstance(item, str) and item.strip() for item in directories):
        return [f"{display}: cleanup_scope.directories must be a non-empty string list"]

    normalized = {item.strip().replace("\\", "/") for item in directories}
    PLUGIN_SCOPE_DIRS = _vw().PLUGIN_SCOPE_DIRS
    if normalized != PLUGIN_SCOPE_DIRS:
        return [
            f"{display}: cleanup_scope.directories must match verifier plugin scope "
            f"{sorted(PLUGIN_SCOPE_DIRS)}, got {sorted(normalized)}"
        ]
    return []


def _manifest_requires_product_artifact_guards(manifest, manifest_path=None):
    """Return whether FIX-110 manifest guards apply to this manifest.

    Generic test fixtures may use a tiny manifest to exercise tracked-scope
    behavior.  The product artifact and cleanup-scope guards are mandatory for
    the real software-project-governance manifest, and for fixtures that
    explicitly include either FIX-110 section.
    """
    ROOT = _root()
    manifest_path = manifest_path or ROOT / "skills/software-project-governance/core/manifest.json"
    try:
        is_real_manifest = (
            Path(manifest_path).resolve()
            == (ROOT / "skills/software-project-governance/core/manifest.json").resolve()
        )
    except OSError:
        is_real_manifest = False
    return (
        is_real_manifest
        or manifest.get("workflow") == "software-project-governance"
        or "canonical_product_artifacts" in manifest
        or "cleanup_scope" in manifest
    )


def scan_actual_files(exclude_patterns=None):
    """Scan project root for all actual files, returning a set of
    relative-paths-as-strings.

    Directories matching the exclude set are skipped wholesale.
    """
    ROOT = _root()
    if exclude_patterns is None:
        exclude_patterns = {
            ".git", "node_modules", "__pycache__",
        }

    actual = set()
    for f in ROOT.rglob("*"):
        if not f.is_file():
            continue
        parts = f.relative_to(ROOT).parts
        skip = False
        for part in parts:
            if part in exclude_patterns:
                skip = True
                break
            if part.startswith("__pycache__"):
                skip = True
                break
        if skip:
            continue
        if f.suffix in (".pyc",):
            continue
        rel = str(f.relative_to(ROOT)).replace("\\", "/")
        actual.add(rel)
    return actual


def scan_manifest_visible_files(exclude_patterns=None):
    """Scan files relevant to manifest drift.

    Manifest consistency is about repository/product shape, not local runtime
    state.  Gitignored caches, untracked user notes, and developer scratch files
    are intentionally outside this comparison.  Canonical files are added back
    by check_manifest_consistency via existence checks so gitignored governance
    fixtures can still satisfy explicit manifest entries.
    """
    tracked = _git_files(["ls-files", "--cached"])
    if tracked is not None:
        return tracked
    return scan_actual_files(exclude_patterns)


def check_manifest_consistency(manifest_path=None):
    """Compare manifest.json canonical set against actual filesystem.

    Returns: dict with 'missing', 'untracked', 'pass' keys.
    """
    ROOT = _root()
    canonical = expand_manifest_to_canonical_set(manifest_path)
    if canonical is None:
        return {
            "missing": [],
            "untracked": [],
            "artifact_issues": [],
            "cleanup_scope_issues": [],
            "pass": None,
            "error": "manifest.json not found or unreadable",
        }

    if manifest_path is None:
        manifest_path = ROOT / "skills/software-project-governance/core/manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    actual = scan_manifest_visible_files()

    # For canonical dir entries, we only check the dir exists (not the files inside)
    canonical_dirs = {p for p in canonical if p.endswith("/")}
    canonical_files = {p for p in canonical if not p.endswith("/")}

    existing_canonical_files = {p for p in canonical_files if (ROOT / p).is_file()}
    actual_for_missing = actual | existing_canonical_files

    missing = sorted(canonical_files - actual_for_missing)
    # Untracked: files that exist but are not in canon (excluding well-known patterns)
    untracked = sorted(actual - canonical_files)

    # Filter out obviously non-manifest content from untracked
    untracked_filtered = []
    for u in untracked:
        # Skip files inside directories that are listed as canonical dirs
        covered_by_dir = any(u.startswith(d) for d in canonical_dirs)
        if covered_by_dir:
            continue
        untracked_filtered.append(u)

    if _manifest_requires_product_artifact_guards(manifest, manifest_path):
        artifact_issues = check_manifest_canonical_product_artifacts(manifest, manifest_path)
        cleanup_scope_issues = check_manifest_cleanup_scope(manifest, manifest_path)
    else:
        artifact_issues = []
        cleanup_scope_issues = []

    return {
        "missing": missing,
        "untracked": untracked_filtered,
        "artifact_issues": artifact_issues,
        "cleanup_scope_issues": cleanup_scope_issues,
        "pass": (
            len(missing) == 0
            and len(untracked_filtered) == 0
            and len(artifact_issues) == 0
            and len(cleanup_scope_issues) == 0
        ),
        "canonical_count": len(canonical_files),
        "actual_count": len(actual),
    }


def cmd_check_manifest_consistency(args):
    """Compare manifest.json canonical set against actual filesystem."""
    result = check_manifest_consistency()

    print()
    if result.get("error"):
        print(f"[ERROR] {result['error']}")
        return

    print("=== Manifest Consistency Check ===")
    print(f"  Canonical files:  {result['canonical_count']}")
    print(f"  Actual files:     {result['actual_count']}")

    missing = result["missing"]
    untracked = result["untracked"]
    artifact_issues = result.get("artifact_issues", [])
    cleanup_scope_issues = result.get("cleanup_scope_issues", [])

    if missing:
        print(f"\n  [MISSING] {len(missing)} file(s) declared in manifest but absent:")
        for m in missing:
            print(f"    - {m}")

    if untracked:
        print(f"\n  [UNTRACKED] {len(untracked)} file(s) present on disk but not in manifest:")
        for u in untracked:
            print(f"    - {u}")

    if artifact_issues:
        print(f"\n  [CANONICAL ARTIFACT] {len(artifact_issues)} issue(s):")
        for issue in artifact_issues:
            print(f"    - {issue}")

    if cleanup_scope_issues:
        print(f"\n  [CLEANUP SCOPE] {len(cleanup_scope_issues)} issue(s):")
        for issue in cleanup_scope_issues:
            print(f"    - {issue}")

    if result["pass"]:
        print(f"\n  [PASS] Manifest and filesystem are consistent.")
    else:
        print(f"\n  [FAIL] Manifest-filesystem mismatch detected.")

    if args.fail_on_issues and not result["pass"]:
        sys.exit(1)
