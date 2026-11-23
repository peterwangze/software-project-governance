"""Repository path and Git file access shared by product validators."""

import os
from pathlib import Path
import subprocess


def package_root():
    return Path(__file__).resolve().parents[3]


def default_host_root():
    from resolve_entry import current_host_root
    return current_host_root()


def display_path(path, root):
    """Return repo-relative path when possible, without Path.is_relative_to()."""
    try:
        path_abs = os.path.abspath(os.fspath(path))
        root_abs = os.path.abspath(os.fspath(root))
        common = os.path.commonpath([path_abs, root_abs])
        if os.path.normcase(common) == os.path.normcase(root_abs):
            return Path(os.path.relpath(path_abs, root_abs))
    except (OSError, TypeError, ValueError):
        return path
    return path


def git_files(args, root):
    """Return repo-relative paths from git, or None when git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root)] + args,
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    return {
        line.strip().replace("\\", "/")
        for line in result.stdout.splitlines()
        if line.strip()
    }
