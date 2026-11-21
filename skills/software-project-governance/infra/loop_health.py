"""Check pause-point declarations and report advisory work-unit observations."""

from dataclasses import asdict

from loop_engine import load_loop_registry
from loop_event_log import default_log_path, read_events
from loop_telemetry import compute_metrics


def _check_velocity_justification(plugin_home=None):
    """Every active PausePoint needs a non-empty justification.

    Iterates PausePoint declarations from loop-engineering-registry.json. For
    each PausePoint whose ``active`` flag is true, verifies that
    ``velocity_cost_justification`` is a non-empty string. Missing/blank
    justification on an active PP is a protocol violation (DEC-097 part 2).

    Fail-closed: a missing, corrupt, or structurally invalid registry produces
    a blocking authority finding. Optional runtime absence is handled
    separately and does not affect this authority check.

    Args:
        plugin_home: Optional plugin-home override forwarded to the loader.

    Returns:
        list of finding dicts, one per violating PausePoint:
        ``{"severity": "FAIL", "pause_point": pp_id, "message": ...}``.
    """
    findings = []
    data, issues = load_loop_registry(plugin_home)
    for issue in issues:
        if issue:
            findings.append({
                "severity": "FAIL",
                "pause_point": "registry-authority",
                "message": (
                    "Loop registry authority unavailable or invalid: {0}"
                ).format(issue),
            })
    if not isinstance(data, dict):
        if findings:
            return findings
        return [{
            "severity": "FAIL",
            "pause_point": "registry-authority",
            "message": (
                "Loop registry authority unavailable or invalid: "
                "loop-engineering registry root must be an object"
            ),
        }]
    pause_points = data.get("pause_points")
    if not isinstance(pause_points, dict):
        return [{
            "severity": "FAIL",
            "pause_point": "registry-authority",
            "message": (
                "Loop registry authority invalid: pause_points must be an object"
            ),
        }]
    if not pause_points:
        return [{
            "severity": "FAIL",
            "pause_point": "registry-authority",
            "message": (
                "Loop registry authority invalid: pause_points must not be empty"
            ),
        }]
    for pp_id, entry in pause_points.items():
        if not isinstance(entry, dict):
            findings.append({
                "severity": "FAIL",
                "pause_point": "registry-authority",
                "message": (
                    "Loop registry authority invalid: pause_points entry {0} "
                    "must be an object"
                ).format(pp_id),
            })
            continue
        if "active" not in entry or not isinstance(entry.get("active"), bool):
            findings.append({
                "severity": "FAIL",
                "pause_point": "registry-authority",
                "message": (
                    "Loop registry authority invalid: pause_points entry {0} "
                    "must declare active as a boolean"
                ).format(pp_id),
            })
            continue
        # Only ACTIVE PausePoints are subject to the justification rule.
        if not entry["active"]:
            continue
        justification = entry.get("velocity_cost_justification")
        if not isinstance(justification, str) or not justification.strip():
            findings.append({
                "severity": "FAIL",
                "pause_point": pp_id,
                "message": (
                    "PP {0} active but velocity_cost_justification missing — "
                    "protocol violation (DEC-097 part 2)"
                ).format(pp_id),
            })
    return findings


def check_loop_health(target=None, plugin_home=None):
    """Missing pause-point authority blocks. Event telemetry is observational."""
    findings = _check_velocity_justification(plugin_home)
    if target is None:
        from resolve_entry import resolve_host_root
        target = resolve_host_root(None)
    try:
        path = default_log_path(target) if target else None
        events = read_events(log_path=path) if path and path.is_file() else []
        report = compute_metrics(events, window="30d")
        telemetry = {"status": "available" if report.units_considered else "unknown", **asdict(report)}
    except (OSError, ValueError) as exc:
        telemetry = {"status": "unknown", "reason": str(exc)}
    return {
        "findings": findings,
        "telemetry": telemetry,
        "summary": {
            "blocking_count": sum(f["severity"] == "FAIL" for f in findings),
            "advisory_count": sum(f["severity"] != "FAIL" for f in findings),
        },
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target")
    parser.add_argument("--fail-on-issues", action="store_true")
    args = parser.parse_args()
    result = check_loop_health(target=args.target)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.fail_on_issues and result["summary"]["blocking_count"]:
        raise SystemExit(1)
