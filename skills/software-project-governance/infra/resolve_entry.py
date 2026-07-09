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
                      `version` — the AUTHORITATIVE active version source.

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
_FRONTMATTER_VERSION_RE = re.compile(
    r"^version:\s*([0-9]+(?:\.[0-9]+){1,3})\s*$",
    re.MULTILINE,
)
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


def read_active_version(plugin_home=None):
    """Return active_version from PLUGIN_HOME/SKILL.md frontmatter.

    Returns None if SKILL.md is missing or has no parseable ``version:``
    field in its YAML frontmatter. This is the AUTHORITATIVE active
    version source — replaces installed_plugins.json archaeology.

    Reads PLUGIN_HOME (module attribute) at call time when no arg is
    passed, so tests can patch it. Binds the default lazily instead of
    capturing the import-time object (avoids the default-arg footgun
    where a post-patch call with no arg would read the pre-patch path).
    """
    if plugin_home is None:
        plugin_home = PLUGIN_HOME
    skill_md = plugin_home / "SKILL.md"
    if not skill_md.is_file():
        return None
    text = _read_text_safe(skill_md)
    # Restrict to the leading YAML frontmatter block (between the first
    # two `---` fences) so a stray `version:` in prose can't win.
    if text.startswith("---"):
        end = text.find("\n---", 3)
        frontmatter = text[: end] if end != -1 else text[:400]
    else:
        frontmatter = text[:400]
    m = _FRONTMATTER_VERSION_RE.search(frontmatter)
    return m.group(1) if m else None


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
    hooks_dir = host_root / ".git" / "hooks"

    governance_initialized = plan_tracker_path.is_file()
    snapshot_dt = _parse_snapshot_date(snapshot_path)
    snapshot_exists = snapshot_path.is_file()
    if snapshot_dt is None:
        snapshot_fresh = None if not snapshot_exists else False
    else:
        snapshot_fresh = datetime.now() - snapshot_dt <= timedelta(
            hours=SNAPSHOT_FRESH_HOURS
        )

    hooks_installed = {
        h: (hooks_dir / h).is_file() for h in HOOK_NAMES
    }

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
        "diagnostic": None,
    }


def resolve_host_root(project_root_arg):
    """Resolve HOST_PROJECT_ROOT with fail-closed semantics.

    Priority: explicit --project-root -> os.getcwd().
    An explicit path that does not exist is a hard error (fail-closed);
    we never silently rewrite it to PLUGIN_HOME.
    """
    if project_root_arg is not None:
        candidate = Path(project_root_arg).expanduser()
        try:
            candidate = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            return None
        if not candidate.is_dir():
            return None
        return candidate

    try:
        cwd = Path(os.getcwd())
    except (OSError, FileNotFoundError):
        return None
    try:
        return cwd.resolve(strict=True)
    except (OSError, RuntimeError):
        return None


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


if __name__ == "__main__":
    sys.exit(main())
