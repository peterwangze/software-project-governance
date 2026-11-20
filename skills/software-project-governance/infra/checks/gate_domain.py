"""Certification of actual release units, including their bound candidate version."""
from pathlib import Path


def release_unit_issues(root=None):
    from governance_readers import loop_state
    from loop_workflow import release_issues

    root = Path(root) if root is not None else Path.cwd()
    view = loop_state(root)
    if view["state"] == "invalid":
        return [view["message"]]
    issues = []
    for unit in view["units"]:
        if unit["runtime_status"] == "completed" and unit.get("release_version"):
            issues.extend(release_issues(root, unit["flow_unit_id"], unit["release_version"]))
    return issues
