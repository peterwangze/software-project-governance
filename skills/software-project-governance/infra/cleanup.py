#!/usr/bin/env python3
"""
Declarative cleanup script for software-project-governance plugin.

Computes REDUNDANT = ACTUAL - CANONICAL - EXCLUDE using manifest.json
as the single source of truth, then classifies and optionally removes
redundant files.

Usage:
    python cleanup.py --dry-run
    python cleanup.py --target /path/to/plugin/cache
    python cleanup.py --json --dry-run
    python cleanup.py --categories P0,P1
"""

import argparse
import fnmatch
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set


# ─── Error codes ──────────────────────────────────────────────
ERR_NOTHING_TO_CLEAN  = 1   # CLEANUP-ERR-002
ERR_MANIFEST_NOT_FOUND = 2  # CLEANUP-ERR-003
ERR_TARGET_NOT_FOUND   = 3  # CLEANUP-ERR-001


# ─── Constants ────────────────────────────────────────────────
_HARD_PROTECTED = {
    # Absolute protection: these paths are NEVER deleted, regardless of manifest.
    ".git", ".git/",
    ".governance", ".governance/",
}


# ─── Core functions ───────────────────────────────────────────

def load_manifest(path: Path) -> dict:
    """Load and parse manifest.json.

    Args:
        path: Path to manifest.json.

    Returns:
        Parsed manifest as dict.

    Raises:
        SystemExit(ERR_MANIFEST_NOT_FOUND) if file missing or unparseable.
    """
    if not path.exists():
        print(
            f"[CLEANUP-ERR-003] Manifest not found: {path}\n"
            f"Hint: ensure skills/software-project-governance/core/manifest.json exists.",
            file=sys.stderr,
        )
        sys.exit(ERR_MANIFEST_NOT_FOUND)
    try:
        with open(path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(
            f"[CLEANUP-ERR-003] Failed to parse manifest {path}: {e}",
            file=sys.stderr,
        )
        sys.exit(ERR_MANIFEST_NOT_FOUND)
    return manifest


def _resolve_path(rel: str) -> str:
    """Normalize a relative path to use forward slashes."""
    return rel.replace("\\", "/")


def _is_path_excluded(rel_path: str, excludes: Set[str]) -> bool:
    """Check whether *rel_path* matches any exclude pattern.

    Semantics:
      - Entries ending with ``/`` match **any** occurrence of that directory
        in the path (root-prefix OR nested as a path component).
        E.g. ``.git/`` matches both ``.git/config`` and
        ``e2e-test-project/.git/HEAD``.
      - Entries without ``/`` match the *filename* component only.
        E.g. ``*.pyc`` matches ``foo.pyc`` and ``a/b/c/foo.pyc``.
      - Entries containing ``/`` (but not ending with ``/``) match
        the full relative path via fnmatch.
    """
    p = Path(rel_path)
    segments = rel_path.split("/")
    for exc in excludes:
        exc_clean = exc.rstrip("/").replace("\\", "/")

        # Directory-prefix match: root-prefix OR nested as a path component
        if exc.endswith("/"):
            exc_name = exc_clean.rstrip("/")
            if rel_path == exc_name or rel_path.startswith(exc_name + "/"):
                return True
            # Also match if the directory appears nested anywhere (e.g.
            # "project/e2e-test-project/.git/HEAD" matches ".git/")
            if exc_name in segments:
                return True
            continue

        # Name-only pattern: match against the final component
        if "/" not in exc_clean:
            if fnmatch.fnmatch(p.name, exc_clean):
                return True
            continue

        # Full-path pattern
        if fnmatch.fnmatch(rel_path, exc_clean):
            return True

    return False


def _expand_section(manifest: dict, section_key: str, root: Path) -> Set[str]:
    """Expand one manifest section (product / repo_only / root_entries)
    into a set of relative file paths."""
    result: Set[str] = set()

    section = manifest.get(section_key, {})
    if not section:
        return result

    # ── Explicit entries ──
    for entry in section.get("entries", []):
        path_str = entry["path"]
        if entry["type"] == "file":
            result.add(_resolve_path(path_str))
        elif entry["type"] == "dir":
            result.add(_resolve_path(path_str).rstrip("/") + "/")
            p = root / path_str
            if p.exists() and p.is_dir():
                for f in p.rglob("*"):
                    if f.is_file():
                        result.add(_resolve_path(str(f.relative_to(root))))

    # ── Glob patterns ──
    for pattern in section.get("glob_patterns", []):
        pattern_normalized = pattern.replace("\\", "/")
        for match in root.glob(pattern_normalized):
            rel = _resolve_path(str(match.relative_to(root)))
            if match.is_file():
                result.add(rel)
            elif match.is_dir():
                result.add(rel.rstrip("/") + "/")
                for f in match.rglob("*"):
                    if f.is_file():
                        result.add(_resolve_path(str(f.relative_to(root))))

    return result


def expand_canonical(manifest: dict, root: Path) -> Set[str]:
    """Expand all manifest sections into a set of relative file paths.

    Sections expanded: root_entries, product, repo_only.
    When running in a plugin cache (product-only), repo_only globs
    are harmless no-ops because the directories don't exist.

    All paths use Unix-style ``/`` separators.
    """
    canonical: Set[str] = set()

    # Expand root-level file entries (README.md, CLAUDE.md, etc.)
    for file_entry in manifest.get("root_entries", {}).get("files", []):
        canonical.add(_resolve_path(file_entry))

    for dir_entry in manifest.get("root_entries", {}).get("directories", []):
        canonical.add(_resolve_path(dir_entry).rstrip("/") + "/")
        p = root / dir_entry
        if p.exists() and p.is_dir():
            for f in p.rglob("*"):
                if f.is_file():
                    canonical.add(_resolve_path(str(f.relative_to(root))))

    # Expand product and repo_only sections
    canonical |= _expand_section(manifest, "product", root)
    canonical |= _expand_section(manifest, "repo_only", root)

    return canonical


def scan_actual(root: Path, excludes: Set[str]) -> Set[str]:
    """Recursively scan *root* and return the set of relative file paths.

    Directories are NOT included -- only regular files.  Paths matching
    *excludes* are silently dropped.
    """
    if not root.exists():
        print(
            f"[CLEANUP-ERR-001] Target directory not found: {root}",
            file=sys.stderr,
        )
        sys.exit(ERR_TARGET_NOT_FOUND)

    actual: Set[str] = set()
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        rel = _resolve_path(str(f.relative_to(root)))
        if _is_path_excluded(rel, excludes):
            continue
        actual.add(rel)
    return actual


def compute_redundant(manifest_path: Path, target_root: Path) -> dict:
    """Compute **REDUNDANT = ACTUAL - CANONICAL - EXCLUDE**.

    Returns a dict with keys:
        manifest_version, total_actual, total_canonical,
        redundant_count, redundant_files (sorted list).
    """
    # Check target existence FIRST (before manifest) so the right error
    # code (ERR-001 vs ERR-003) is produced for explicit --target.
    if not target_root.exists():
        print(
            f"[CLEANUP-ERR-001] Target directory not found: {target_root}",
            file=sys.stderr,
        )
        sys.exit(ERR_TARGET_NOT_FOUND)

    manifest = load_manifest(manifest_path)

    # Build exclude set from manifest + hard protections
    exc_entries = set(
        manifest.get("exclude_from_cleanup", {}).get("entries", [])
    )
    exc_user = set(
        manifest.get("exclude_from_cleanup", {}).get("user_data_dirs", [])
    )
    excludes = exc_entries | exc_user

    canonical = expand_canonical(manifest, target_root)
    actual = scan_actual(target_root, excludes)

    # Remove directory entries from canonical for diff purposes
    # (actual only contains files, so dirs in canonical would never match)
    canonical_files = {p for p in canonical if not p.endswith("/")}

    redundant = sorted(actual - canonical_files)

    return {
        "manifest_version": manifest.get("version", "unknown"),
        "total_actual": len(actual),
        "total_canonical": len(canonical_files),
        "redundant_count": len(redundant),
        "redundant_files": redundant,
    }


def classify_redundant(
    redundant_files: List[str], manifest: dict, target_root: Path
) -> Dict[str, List[str]]:
    """Classify each redundant file into P0 / P1 / P2.

    P0 — Must remove:
        * File content contains ``plugin 发现 stub`` (old stub residue).
        * File lives in a directory NOT declared as a ``dir`` entry in
          ``manifest.product.entries`` (structural orphan).

    P1 — Suggest remove:
        * File not in canonical set but its *parent directory IS* declared
          in the manifest (extra file inside a known directory).

    P2 — Caution:
        * Unable to determine source (fallback -- should normally be empty).
    """
    p0: List[str] = []
    p1: List[str] = []
    p2: List[str] = []

    # Collect declared directory paths from manifest
    declared_dirs: Set[str] = set()
    for entry in manifest.get("product", {}).get("entries", []):
        if entry["type"] == "dir":
            declared_dirs.add(entry["path"].rstrip("/").rstrip("\\"))

    for file_path in redundant_files:
        full_path = target_root / file_path

        # ── P0 marker: stub content ──
        is_stub = False
        try:
            if full_path.exists() and full_path.is_file():
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read(4096)
                    if "plugin 发现 stub" in content:
                        is_stub = True
        except (OSError, UnicodeDecodeError):
            pass

        # ── Check parent directory declaration ──
        parent = _resolve_path(str(Path(file_path).parent)).rstrip("/")

        in_declared_dir = any(
            parent == d or parent.startswith(d + "/") for d in declared_dirs
        )

        if is_stub or not in_declared_dir:
            p0.append(file_path)
        elif in_declared_dir:
            p1.append(file_path)
        else:
            p2.append(file_path)

    return {"P0": p0, "P1": p1, "P2": p2}


def _cleanup_empty_dirs(root: Path) -> int:
    """Remove empty directories in *root* (bottom-up traversal).

    Returns the number of directories removed.  Protected directories
    (``.git``, ``.governance``) are always skipped.
    """
    removed = 0
    try:
        for dirpath_str, dirnames, _filenames in os.walk(str(root), topdown=False):
            dirpath = Path(dirpath_str)
            if dirpath == root:
                continue
            rel = _resolve_path(str(dirpath.relative_to(root)))
            rel_normalized = rel.rstrip("/")
            # Never touch protected dirs
            if (
                rel_normalized == ".git"
                or rel_normalized.startswith(".git/")
                or rel_normalized == ".governance"
                or rel_normalized.startswith(".governance/")
            ):
                continue
            try:
                if not any(dirpath.iterdir()):
                    dirpath.rmdir()
                    removed += 1
            except OSError:
                pass
    except OSError:
        pass
    return removed


def _strip_protected(files: List[str]) -> List[str]:
    """Remove any hard-protected paths from the list."""
    result: List[str] = []
    for f in files:
        f_clean = f.rstrip("/")
        if f_clean in _HARD_PROTECTED or any(
            f_clean.startswith(p.rstrip("/") + "/") for p in _HARD_PROTECTED
        ):
            continue
        result.append(f)
    return result


# ─── Main entry ───────────────────────────────────────────────

def run_cleanup(
    manifest_path: Path,
    target_root: Path,
    dry_run: bool = False,
    categories: Optional[List[str]] = None,
    json_output: bool = False,
) -> dict:
    """Main cleanup routine.

    1. Compute redundant files (ACTUAL - CANONICAL - EXCLUDE).
    2. Classify into P0 / P1 / P2.
    3. Print (or JSON-emit) the report.
    4. If not dry-run, delete files in the requested categories.

    Returns the report dict.
    """
    if categories is None:
        categories = ["P0", "P1", "P2"]

    # ── 1. Compute ──
    result = compute_redundant(manifest_path, target_root)
    redundant_files = result["redundant_files"]

    if not redundant_files:
        if json_output:
            print(
                json.dumps(
                    {
                        "status": "clean",
                        "message": "No redundant files found. Plugin installation is clean.",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(
                "[CLEANUP-ERR-002] No redundant files found. "
                "Plugin installation is clean."
            )
        sys.exit(ERR_NOTHING_TO_CLEAN)

    # ── 2. Classify ──
    manifest = load_manifest(manifest_path)
    classified = classify_redundant(redundant_files, manifest, target_root)

    # ── 3. Filter by requested categories ──
    files_to_delete: List[str] = []
    for cat in categories:
        files_to_delete.extend(classified.get(cat, []))
    files_to_delete = sorted(set(files_to_delete))

    # ── 4. Hard safety strip ──
    files_to_delete = _strip_protected(files_to_delete)

    # ── 5. Build report ──
    report = {
        "manifest_version": result["manifest_version"],
        "dry_run": dry_run,
        "total_actual_files": result["total_actual"],
        "total_canonical_files": result["total_canonical"],
        "total_redundant": result["redundant_count"],
        "classification": {
            "P0_must_remove": len(classified.get("P0", [])),
            "P1_suggest_remove": len(classified.get("P1", [])),
            "P2_caution": len(classified.get("P2", [])),
        },
        "files_to_delete": files_to_delete,
        "details": classified,
    }

    if json_output:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return report

    # ── 6a. Human-readable output ──
    print(f"Manifest version : {report['manifest_version']}")
    print(f"Canonical files  : {report['total_canonical_files']}")
    print(f"Actual files     : {report['total_actual_files']}")
    print(f"Redundant files  : {report['total_redundant']}")
    print()

    if not files_to_delete:
        print("No files to delete in selected categories.")
        return report

    # P0
    if "P0" in categories and classified.get("P0"):
        print(f"━━━ P0 — Must remove ({len(classified['P0'])} file(s))")
        print("    (stub residue / undeclared directory)")
        for f in classified["P0"]:
            print(f"  - {f}")
        print()

    # P1
    if "P1" in categories and classified.get("P1"):
        print(
            f"━━━ P1 — Suggest remove ({len(classified['P1'])} file(s))"
        )
        print("    (extra files in declared directories)")
        for f in classified["P1"]:
            print(f"  - {f}")
        print()

    # P2
    if "P2" in categories and classified.get("P2"):
        print(f"━━━ P2 — Caution ({len(classified['P2'])} file(s))")
        print("    (undetermined source)")
        for f in classified["P2"]:
            print(f"  - {f}")
        print()

    # ── 6b. Execute ──
    if dry_run:
        print(
            f"[DRY-RUN] Would delete {len(files_to_delete)} file(s). "
            f"No changes made."
        )
        return report

    deleted = 0
    errors = 0
    for rel_path in files_to_delete:
        full_path = target_root / rel_path
        try:
            if full_path.exists():
                full_path.unlink()
                deleted += 1
        except OSError as e:
            print(f"  ERROR deleting {rel_path}: {e}", file=sys.stderr)
            errors += 1

    # Remove empty directories left behind
    empty_dirs_removed = _cleanup_empty_dirs(target_root)

    print("Cleanup complete:")
    print(f"  Deleted {deleted} file(s)")
    if errors:
        print(f"  {errors} error(s) encountered")
    if empty_dirs_removed:
        print(f"  Removed {empty_dirs_removed} empty director(y/ies)")
    print("  Plugin installation is now clean.")

    return report


# ─── CLI entry point ──────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Declarative cleanup — removes files not declared in "
            "canonical manifest (manifest.json)."
        ),
    )
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help=(
            "Target root directory to scan. "
            "Default: current working directory."
        ),
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default=None,
        help=(
            "Path to manifest.json. "
            "Default: <target>/skills/software-project-governance/core/manifest.json"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON (machine-readable).",
    )
    parser.add_argument(
        "--categories",
        type=str,
        default="P0,P1,P2",
        help=(
            "Comma-separated list of categories to clean. "
            "Default: P0,P1,P2"
        ),
    )

    args = parser.parse_args()

    # Determine target root
    target_root = Path(args.target) if args.target else Path.cwd()
    target_root = target_root.resolve()

    # Determine manifest path
    if args.manifest:
        manifest_path = Path(args.manifest).resolve()
    else:
        manifest_path = (
            target_root
            / "skills"
            / "software-project-governance"
            / "core"
            / "manifest.json"
        )

    categories = [c.strip() for c in args.categories.split(",") if c.strip()]

    run_cleanup(
        manifest_path=manifest_path,
        target_root=target_root,
        dry_run=args.dry_run,
        categories=categories,
        json_output=args.json,
    )


if __name__ == "__main__":
    main()
