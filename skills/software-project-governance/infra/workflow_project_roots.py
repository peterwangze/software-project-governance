"""Resolve product and host paths and maintain the active host projection."""

from checks import review_domain as _review_checks
from checks.manifest import PLUGIN_SCOPE_DIRS
from pathlib import Path
from resolve_entry import validate_project_root as _validate_project_root
import sys



_publish_paths = None


def bind_public_paths(update):
    global _publish_paths
    _publish_paths = update


def _apply_project_root_override(project_root):
    """Rebind host-governance fact paths to an explicit project root.

    This does not move plugin assets.  ``ROOT`` / ``PLUGIN_ROOT`` continue to
    identify the installed workflow package; only host facts under
    ``<project-root>/.governance`` are rebound.

    Fail-closed (FIX-245): an explicit root that is empty, does not exist,
    or is not a directory is a hard error — classified diagnostic on
    stderr + exit 2 (module CLI convention, same as the argparse/extraction
    errors; mirrors FIX-244 archive alignment). A nonexistent path must
    never silently rebind to a phantom root.
    """
    global HOST_PROJECT_ROOT, GOVERNANCE_DIR, EXECUTION_PACKET_PATH
    global SAMPLE_PATH, SESSION_SNAPSHOT_PATH, EVIDENCE_PATH, RISK_PATH
    global ARCHIVE_INDEX_PATH, ARCHIVE_TASKS_DIR, ARCHIVE_EVIDENCE_DIR
    global ARCHIVE_DECISIONS_DIR, ARCHIVE_RISKS_DIR

    host_root, error = _validate_project_root(project_root)
    if error is not None:
        display = "<empty>" if not project_root else str(project_root)
        print(
            f"verify_workflow: error: invalid-project-root — {display} ({error})",
            file=sys.stderr,
        )
        sys.exit(2)
    HOST_PROJECT_ROOT = host_root
    GOVERNANCE_DIR = HOST_PROJECT_ROOT / ".governance"
    EXECUTION_PACKET_PATH = GOVERNANCE_DIR / "execution-packets.json"

    if "SAMPLE_PATH" in globals():
        SAMPLE_PATH = GOVERNANCE_DIR / "plan-tracker.md"
    if "SESSION_SNAPSHOT_PATH" in globals():
        SESSION_SNAPSHOT_PATH = GOVERNANCE_DIR / "session-snapshot.md"
    if "EVIDENCE_PATH" in globals():
        EVIDENCE_PATH = GOVERNANCE_DIR / "evidence-log.md"
    if "RISK_PATH" in globals():
        RISK_PATH = GOVERNANCE_DIR / "risk-log.md"
    if "ARCHIVE_INDEX_PATH" in globals():
        ARCHIVE_INDEX_PATH = GOVERNANCE_DIR / "archive" / "index.md"
    if "ARCHIVE_TASKS_DIR" in globals():
        ARCHIVE_TASKS_DIR = GOVERNANCE_DIR / "archive" / "tasks"
    if "ARCHIVE_EVIDENCE_DIR" in globals():
        ARCHIVE_EVIDENCE_DIR = GOVERNANCE_DIR / "archive" / "evidence"
    if "ARCHIVE_DECISIONS_DIR" in globals():
        ARCHIVE_DECISIONS_DIR = GOVERNANCE_DIR / "archive" / "decisions"
    if "ARCHIVE_RISKS_DIR" in globals():
        ARCHIVE_RISKS_DIR = GOVERNANCE_DIR / "archive" / "risks"

    global _asset_governance_dir
    _asset_governance_dir = GOVERNANCE_DIR
    from workflow_policy_bindings import update_host_inventory
    update_host_inventory(GOVERNANCE_DIR)
    current = {name: globals()[name] for name in _HOST_PATH_NAMES if name in globals()}
    if _publish_paths is not None:
        _publish_paths(current)


def _asset_host_files(governance_dir):
    return {
        "Governance Plan Tracker": governance_dir / "plan-tracker.md",
        "Governance Evidence Log": governance_dir / "evidence-log.md",
        "Governance Decision Log": governance_dir / "decision-log.md",
        "Governance Risk Log": governance_dir / "risk-log.md",
    }


ROOT = Path(__file__).resolve().parents[3]


INTERACTION_BOUNDARY_PATH = ROOT / "skills/software-project-governance/references/interaction-boundary.md"


USER_INTERRUPTION_POLICY_TEMPLATE_PATH = ROOT / "skills/software-project-governance/core/templates/user-interruption-policy.md"


def _resolve_plugin_root():
    """Deferred resolve of PLUGIN_ROOT via resolve_entry.PLUGIN_HOME.

    Falls back to the legacy ``parents[3]`` plugin root (== ROOT) when
    resolve_entry cannot be imported (e.g. minimal packaging), so the
    plugin always knows where its own assets are.
    """
    try:
        from resolve_entry import PLUGIN_HOME  # peer import (no cycle)
        return Path(PLUGIN_HOME).parent.parent  # parents[2] of infra/
    except Exception:
        return ROOT


def _resolve_host_root():
    """Deferred resolve of HOST_PROJECT_ROOT via resolve_entry.

    Priority mirrors resolve_entry.resolve_host_root: explicit cwd ->
    os.getcwd(). On any failure (resolve_entry missing, cwd unusable)
    we fall back to the legacy ``parents[3]`` so dogfood mode keeps
    working — this is the backward-compat path, not a security decision
    here (resolve_entry itself is fail-closed for the /governance entry).
    """
    try:
        from resolve_entry import resolve_host_root  # peer import (no cycle)
        host = resolve_host_root(None)
        if host is not None:
            return Path(host)
    except Exception:
        pass
    return ROOT


PLUGIN_ROOT = _resolve_plugin_root()


HOST_PROJECT_ROOT = _resolve_host_root()


GOVERNANCE_DIR = HOST_PROJECT_ROOT / ".governance"


_asset_governance_dir = GOVERNANCE_DIR


EXECUTION_PACKET_PATH = GOVERNANCE_DIR / "execution-packets.json"


def _display_path(path, root=None):
    from project_paths import display_path
    return display_path(path, root or ROOT)


def _read_text_normalized(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _is_plugin_path(rel_path: str) -> bool:
    return _review_checks._in_plugin_scope(rel_path, PLUGIN_SCOPE_DIRS)


def _git_files(args):
    from project_paths import git_files
    return git_files(args, ROOT)


def _split_markdown_table_row(line):
    from governance_readers import markdown_table_cells
    return markdown_table_cells(line)


SAMPLE_PATH = HOST_PROJECT_ROOT / ".governance" / "plan-tracker.md"


SESSION_SNAPSHOT_PATH = HOST_PROJECT_ROOT / ".governance" / "session-snapshot.md"


def _governance_dir():
    """Dynamic governance dir — tracks SAMPLE_PATH.parent at call time.

    Tests patch SAMPLE_PATH (e.g. to a tempdir); this helper makes every
    runtime governance-path read follow that patch, so GOVERNANCE_DIR no
    longer needs to be patched separately. Module-level constants derived
    from GOVERNANCE_DIR (EVIDENCE_PATH / RISK_PATH / ARCHIVE_*) are kept
    for backward-compat but runtime code SHOULD call this helper.
    """
    return SAMPLE_PATH.parent


EVIDENCE_PATH = SAMPLE_PATH.parent / "evidence-log.md"


RISK_PATH = SAMPLE_PATH.parent / "risk-log.md"


ARCHIVE_INDEX_PATH = SAMPLE_PATH.parent / "archive" / "index.md"


ARCHIVE_TASKS_DIR = SAMPLE_PATH.parent / "archive" / "tasks"


ARCHIVE_EVIDENCE_DIR = SAMPLE_PATH.parent / "archive" / "evidence"


ARCHIVE_DECISIONS_DIR = SAMPLE_PATH.parent / "archive" / "decisions"


ARCHIVE_RISKS_DIR = SAMPLE_PATH.parent / "archive" / "risks"


_HOST_PATH_NAMES = (
    "HOST_PROJECT_ROOT", "GOVERNANCE_DIR", "_asset_governance_dir", "EXECUTION_PACKET_PATH",
    "SAMPLE_PATH", "SESSION_SNAPSHOT_PATH", "EVIDENCE_PATH", "RISK_PATH", "ARCHIVE_INDEX_PATH",
    "ARCHIVE_TASKS_DIR", "ARCHIVE_EVIDENCE_DIR", "ARCHIVE_DECISIONS_DIR", "ARCHIVE_RISKS_DIR",
)


def __getattr__(name):
    # The old command bodies read these names as Python globals. An explicit
    # deletion is observed by the command only if it reaches that particular read.
    if name in _HOST_PATH_NAMES or name in ("ROOT", "PLUGIN_ROOT", "INTERACTION_BOUNDARY_PATH",
                                            "USER_INTERRUPTION_POLICY_TEMPLATE_PATH"):
        raise NameError(f"name '{name}' is not defined")
    raise AttributeError(name)
