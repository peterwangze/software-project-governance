#!/usr/bin/env python3
"""
Deterministic `/governance` entry resolver — FX-130 / DEC-096 / AUDIT-129.

Replaces LLM-driven path/version/scenario discovery at the `/governance`
entry with one self-locating script call that emits a structured JSON
envelope. The LLM only consumes the result for semantic routing.

**Dual-root model (the hard constraint from DEC-080 / RISK-038):**

  PLUGIN_HOME       = Path(__file__).resolve().parent.parent
                      (= skills/software-project-governance/, where SKILL.md lives)
                      Used ONLY to: locate executables + read SKILL.md frontmatter
                      `metadata.version` (historically `version`).

  HOST_PROJECT_ROOT = resolved from --project-root -> os.getcwd().
                      Used to read `.governance/` facts.
                      NEVER derived from __file__.

  FAIL-CLOSED: if HOST_PROJECT_ROOT cannot be confidently determined
  (explicit path missing / cwd unusable), emit a diagnostic envelope with
  resolved_root_ok=false and REFUSE to present governance state. We never
  fall back to PLUGIN_HOME/.governance/ — that is the 0.54.2/0.54.3
  regression.

This module is pure stdlib (pathlib/json/os/sys/argparse/re/datetime) and
MUST NOT import verify_workflow.py: it runs BEFORE verify_workflow can be
located.

Usage:
    python resolve_entry.py [--project-root PATH] [--json]
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ─── Fixed anchors ─────────────────────────────────────────────
# PLUGIN_HOME is derived from __file__ ONLY to locate the plugin's own
# executables and SKILL.md frontmatter. It is NEVER used as the facts root.
PLUGIN_HOME = Path(__file__).resolve().parent.parent

# Snapshot is fresh if its session_date is within this many hours of now.
SNAPSHOT_FRESH_HOURS = 24

# Regexes mirror the proven patterns in verify_workflow.py
# (FIX_105_SNAPSHOT_VERSION_RE / FIX_105_SNAPSHOT_DATE_RE / plan-tracker
# workflow version) so the two scripts agree on what a version/date is.
_FRONTMATTER = re.compile(r"\A---[ \t]*\n(.*?)^---[ \t]*(?:\n|\Z)", re.MULTILINE | re.DOTALL)
_VERSION_VALUE = re.compile(r"""(["']?)([0-9]+(?:\.[0-9]+){1,3})\1(?:[ \t]+\#.*)?""")
_PLAN_TRACKER_VERSION_RE = re.compile(
    r"工作流版本[**:\s]+(\d+\.\d+\.\d+)"
)
_SNAPSHOT_DATE_RE = re.compile(
    r"\*\*session_date\*\*:\s*(\d{4}-\d{2}-\d{2})"
)
_SNAPSHOT_ID_RE = re.compile(
    r"\*\*session_id\*\*:\s*(\d{4})-?(\d{2})-?(\d{2})[^\d]*"
)

# Files whose absence indicates an anomaly when .governance/ otherwise exists.
_CORE_GOVERNANCE_FILES = ("plan-tracker.md", "evidence-log.md")

HOOK_NAMES = ("pre-commit", "commit-msg", "post-commit")


# ─── Helpers ───────────────────────────────────────────────────
def _read_text_safe(path):
    """Read a file as UTF-8, returning '' on any error (never raise)."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def read_skill_version(path, *, allow_active_version=False):
    """Read metadata.version or the historical top-level version from a SKILL.md.

    The shipped header uses unindented top-level keys and block mappings.
    The dotted numeric value may be plain, single- or double-quoted.
    Metadata siblings, comments, BOM and CRLF are supported. A flow-style
    metadata mapping cannot corroborate a legacy value.
    """
    try:
        header = _FRONTMATTER.match(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError):
        return None
    if not header:
        return None
    versions = {}
    in_metadata = seen_metadata = False
    child_indent = None
    version_indent = None
    for line in header[1].splitlines():
        stripped = line.lstrip(" ")
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(stripped)
        if stripped.startswith("\t") or (version_indent is not None and indent > version_indent):
            return None
        version_indent = None
        key, sep, raw = stripped.partition(":")
        if sep and raw and not raw.startswith((" ", "\t")):
            sep = ""  # YAML requires a separator after a block mapping key.
        key = key.strip()
        if len(key) >= 2 and key[0] == key[-1] and key[0] in "\"'":
            key = key[1:-1]
        if indent == 0:
            if key in ("metadata", "version") and not sep:
                return None
            in_metadata = key == "metadata"
            if in_metadata:
                if seen_metadata or (raw.strip() and not raw.lstrip().startswith("#")):
                    return None
                seen_metadata = True
                child_indent = None
                continue
        elif in_metadata:
            if child_indent is None:
                child_indent = indent
            if indent < child_indent:
                return None
            if indent > child_indent:
                continue
            if not sep or key.startswith(("- ", "? ")):
                return None
        else:
            continue
        if not sep or not (key == "version" or (allow_active_version and not indent and key == "active_version")):
            continue
        field = "metadata.version" if indent else key
        value = _VERSION_VALUE.fullmatch(raw.strip())
        if not value or field in versions:
            return None
        versions[field] = value[2]
        version_indent = indent
    values = set(versions.values())
    return values.pop() if len(values) == 1 else None


def read_active_version(plugin_home=None):
    """Read the installed skill's version, resolving PLUGIN_HOME at call time."""
    return read_skill_version((PLUGIN_HOME if plugin_home is None else plugin_home) / "SKILL.md")


def read_release_version(path):
    """Release projections, pins and archives require an X.Y.Z version."""
    version = read_skill_version(path)
    return version if version and version.count(".") == 2 else None


def _parse_snapshot_date(snapshot_path):
    """Return a datetime for the snapshot's date, or None.

    Prefer ``**session_date**: YYYY-MM-DD``; fall back to ``session_id``
    YYYYMMDD so a snapshot missing the explicit date line still yields a
    usable freshness signal.
    """
    if not snapshot_path.is_file():
        return None
    text = _read_text_safe(snapshot_path)
    m = _SNAPSHOT_DATE_RE.search(text)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d")
        except ValueError:
            pass
    m = _SNAPSHOT_ID_RE.search(text)
    if m:
        try:
            return datetime.strptime(
                "".join(m.groups()), "%Y%m%d"
            )
        except ValueError:
            pass
    return None


def _plan_tracker_workflow_version(plan_tracker_path):
    """Return the host plan-tracker workflow version string, or None."""
    if not plan_tracker_path.is_file():
        return None
    m = _PLAN_TRACKER_VERSION_RE.search(_read_text_safe(plan_tracker_path))
    return m.group(1) if m else None


def _version_tuple(v):
    """Best-effort semantic tuple for comparison; short tuples pad with 0."""
    try:
        parts = [int(p) for p in v.split(".")]
    except (AttributeError, ValueError):
        return None
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def _version_lt(a, b):
    """Return True if version a < b, tolerating non-parseable operands."""
    ta, tb = _version_tuple(a), _version_tuple(b)
    if ta is None or tb is None:
        return False
    return ta < tb


def _detect_anomaly(gov_dir, plan_tracker_path):
    """Basic anomaly check for scenario E.

    True when .governance/ exists but a core file is missing or the
    plan-tracker is unreadable/empty (corrupt). Intentionally conservative:
    we only flag what we can determine deterministically from the
    filesystem.
    """
    if not gov_dir.is_dir():
        return False
    for name in _CORE_GOVERNANCE_FILES:
        f = gov_dir / name
        if not f.is_file():
            return True
        if name == "plan-tracker.md" and f.stat().st_size == 0:
            return True
    return False


def _project_has_files(host_root):
    """True if host_root contains any non-hidden file/dir at top level
    (used to distinguish A=empty new project from B=mid-project onboarding)."""
    try:
        for entry in host_root.iterdir():
            if not entry.name.startswith("."):
                return True
    except OSError:
        return False
    return False


def detect_scenario(
    host_root, gov_dir, plan_tracker_path, snapshot_path,
    snapshot_fresh, active_version,
):
    """Deterministically compute the A-F scenario hint.

    Mirrors the former governance.md decision tree as pure functions:
      A — .governance/ absent + project empty-ish (new project init)
      B — .governance/ absent + project has files (mid-project onboarding)
      C — .governance/ exists + host workflow version < active (upgrade)
      D — .governance/ exists + snapshot fresh (session recovery)
      E — .governance/ exists + anomaly (anomaly recovery)
      F — .governance/ exists + all good (status display)
    """
    gov_exists = gov_dir.is_dir()
    if not gov_exists:
        return "B" if _project_has_files(host_root) else "A"

    # Order matters: anomaly (E) before version (C) before freshness (D)
    # so a corrupt store never gets routed to a benign branch.
    if _detect_anomaly(gov_dir, plan_tracker_path):
        return "E"

    if active_version:
        host_v = _plan_tracker_workflow_version(plan_tracker_path)
        if host_v and _version_lt(host_v, active_version):
            return "C"

    if snapshot_path.is_file() and snapshot_fresh is True:
        return "D"

    return "F"


def git_hooks_dir(host_root):
    """Resolve Git's active hooks for this host only, including linked worktrees."""
    import subprocess

    root = Path(host_root).absolute()
    marker = root / ".git"
    if not marker.is_file() and not os.path.lexists(marker / "HEAD"):
        # An uninitialized host may stage hook files before git init. Never
        # ask Git to discover a containing repository on behalf of this root.
        return marker / "hooks"
    try:
        result = subprocess.run(
            ["git", "--git-dir", str(marker), "--work-tree", str(root), "rev-parse",
             "--path-format=absolute", "--git-path", "hooks"],
            cwd=root, env=os.environ.copy(), stdin=subprocess.DEVNULL,
            capture_output=True, timeout=2, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"could not resolve Git hooks for {root}: {exc}") from exc
    directory = Path(os.fsdecode(result.stdout).rstrip("\r\n"))
    if result.returncode or not directory.is_absolute():
        reason = os.fsdecode(result.stderr).strip() or "Git returned no absolute hook directory"
        raise ValueError(f"could not resolve Git hooks for {root}: {reason}")
    return directory


def resolve(host_root=None):
    """Build the resolution envelope dict for the given host root.

    ``host_root`` already-validated Path, or None to trigger fail-closed.
    Returns the full envelope dict (never raises).

    Reads PLUGIN_HOME (module attribute) at call time so tests can patch it.
    """
    active_version = read_active_version(PLUGIN_HOME)

    if host_root is None:
        return {
            "plugin_home": str(PLUGIN_HOME),
            "host_project_root": None,
            "active_version": active_version,
            "version_source": "skill_frontmatter",
            "root_divergence": None,
            "governance_initialized": False,
            "snapshot_exists": False,
            "snapshot_fresh": None,
            "hooks_installed": {h: False for h in HOOK_NAMES},
            "scenario_hint": None,
            "resolved_root_ok": False,
            "diagnostic": (
                "HOST_PROJECT_ROOT could not be confidently resolved "
                "(--project-root missing/unusable and cwd unavailable). "
                "Refusing to present governance state — no fallback to "
                "plugin home. (DEC-080 / RISK-038 fail-closed.)"
            ),
        }

    gov_dir = host_root / ".governance"
    plan_tracker_path = gov_dir / "plan-tracker.md"
    snapshot_path = gov_dir / "session-snapshot.md"

    governance_initialized = plan_tracker_path.is_file()
    snapshot_dt = _parse_snapshot_date(snapshot_path)
    snapshot_exists = snapshot_path.is_file()
    if snapshot_dt is None:
        snapshot_fresh = None if not snapshot_exists else False
    else:
        snapshot_fresh = datetime.now() - snapshot_dt <= timedelta(
            hours=SNAPSHOT_FRESH_HOURS
        )

    diagnostic = None
    try:
        hooks_dir = git_hooks_dir(host_root)
        hooks_installed = {h: (hooks_dir / h).is_file() for h in HOOK_NAMES}
    except (OSError, ValueError) as exc:
        diagnostic = str(exc)
        hooks_installed = dict.fromkeys(HOOK_NAMES, False)

    scenario_hint = detect_scenario(
        host_root, gov_dir, plan_tracker_path, snapshot_path,
        snapshot_fresh, active_version,
    )

    return {
        "plugin_home": str(PLUGIN_HOME),
        "host_project_root": str(host_root),
        "active_version": active_version,
        "version_source": "skill_frontmatter",
        "root_divergence": str(PLUGIN_HOME) != str(host_root),
        "governance_initialized": governance_initialized,
        "snapshot_exists": snapshot_exists,
        "snapshot_fresh": snapshot_fresh,
        "hooks_installed": hooks_installed,
        "scenario_hint": scenario_hint,
        "resolved_root_ok": True,
        "diagnostic": diagnostic,
    }


def extract_project_root_arg(argv):
    """Extract the explicit host root from either side of a workflow subcommand."""
    filtered = []
    project_root = None
    iterator = iter(range(len(argv)))
    for index in iterator:
        value = argv[index]
        if value == "--project-root":
            try:
                project_root = argv[index + 1]
            except IndexError:
                raise ValueError("--project-root requires a path")
            next(iterator, None)
        elif value.startswith("--project-root="):
            project_root = value.split("=", 1)[1]
        else:
            filtered.append(value)
    return project_root, filtered


def validate_project_root(project_root):
    """Validate an explicit --project-root value (fail-closed, FIX-245).

    Returns ``(host_root, error)``: the resolved absolute directory Path
    plus ``None`` for a valid root; ``(None, reason)`` for an empty,
    nonexistent, or non-directory path.
    """
    if not project_root:
        return None, "path is empty"
    candidate = Path(project_root).expanduser()
    try:
        candidate = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        return None, "path does not exist"
    if not candidate.is_dir():
        return None, "not a directory"
    return candidate, None


def resolve_host_root(project_root_arg):
    """Resolve HOST_PROJECT_ROOT with fail-closed semantics.

    Priority: explicit --project-root -> os.getcwd().
    An explicit path that does not exist is a hard error (fail-closed);
    we never silently rewrite it to PLUGIN_HOME.
    """
    if project_root_arg is not None:
        # The standalone resolver historically accepts an empty spelling as cwd.
        return validate_project_root(Path(project_root_arg))[0]

    try:
        cwd = Path(os.getcwd())
    except (OSError, FileNotFoundError):
        return None
    try:
        return cwd.resolve(strict=True)
    except (OSError, RuntimeError):
        return None


# The CLI root can be rebound by --project-root or a caller between checks.
# Standalone consumers can resolve their host without loading the CLI.
_host_root_reader = None
_snapshot_paths_reader = None
_triage_roots_reader = None


def bind_host_root(reader, *, snapshot_paths=None, triage_roots=None):
    global _host_root_reader, _snapshot_paths_reader, _triage_roots_reader
    _host_root_reader = reader
    _snapshot_paths_reader = snapshot_paths
    _triage_roots_reader = triage_roots


def snapshot_paths(root):
    governance = Path(root) / ".governance"
    return root, governance / "session-snapshot.md", governance / "plan-tracker.md", governance / "evidence-log.md"


def current_snapshot_paths():
    if _snapshot_paths_reader is not None:
        return _snapshot_paths_reader()
    return snapshot_paths(current_host_root())


def current_triage_roots():
    if _triage_roots_reader is not None:
        return _triage_roots_reader()
    return PLUGIN_HOME.parent.parent, Path(current_host_root()) / ".governance"


def package_context_file(root, relative_path):
    """An explicit context wins. The historical context default is the installed package root."""
    return (Path(root) if root is not None else PLUGIN_HOME.parent.parent) / relative_path


def current_host_root():
    if _host_root_reader is not None:
        return _host_root_reader()
    return resolve_host_root(None) or PLUGIN_HOME.parent.parent


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Deterministic /governance entry resolver (FX-130). "
            "Emits a structured JSON envelope with dual-root separation."
        )
    )
    parser.add_argument(
        "--project-root",
        default=None,
        help="Explicit host project root. If absent, use os.getcwd().",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit JSON (default; flag kept for explicit invocation).",
    )
    args = parser.parse_args(argv)

    host_root = resolve_host_root(args.project_root)
    envelope = resolve(host_root)
    payload = json.dumps(envelope, indent=2, ensure_ascii=False)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    print(payload)
    return 0


def _dispatch_bootstrap_if_selected(argv):
    """Dispatch the standalone bootstrap handler before loading the workflow engine.
    Unrecognized arguments stay with the full parser, which owns global usage.
    """
    try:
        explicit, remaining = extract_project_root_arg(argv)
    except ValueError:
        return  # main renders the historical extraction error
    if remaining[:1] != ["governance-bootstrap"]:
        return
    import argparse
    import registry
    from bootstrap_aggregate import add_arguments
    parser = argparse.ArgumentParser(prog="verify_workflow governance-bootstrap")
    add_arguments(parser)
    args, unknown = parser.parse_known_args(remaining[1:])
    if unknown:
        return
    args.command = remaining[0]
    args.project_root = explicit
    if explicit is not None:
        host, error = validate_project_root(explicit)
        if error is not None:
            display = str(explicit) if explicit else "<empty>"
            print(f"verify_workflow: error: invalid-project-root — {display} ({error})", file=sys.stderr)
            sys.exit(2)
        args._validated_host_root = host
    sys.exit(registry.load_handler(args.command, parsed_args=True)(args))


if __name__ == "__main__":
    sys.exit(main())
