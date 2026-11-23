"""Render loop health, rollup, telemetry and operations for the selected host."""

import json
import sys
from pathlib import Path


def cmd_check_loop_health(args, *, host_root):
    """Thin entry — delegates to infra/loop_health.py (0.65.0 loop-engineering)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from loop_health import check_loop_health
    result = check_loop_health(getattr(args, "target", None) or host_root)
    print("\n=== Loop Health Check (pause-point declarations) ===")
    findings = result.get("findings", [])
    for f in findings[:25]:
        print(f"  [{f.get('severity','?')}] {f.get('pause_point','')}: {f.get('message','')}")
    blocking = [f for f in findings if f.get("severity") == "FAIL"]
    print(f"\n  Result: {len(blocking)} BLOCKING, {len(findings)-len(blocking)} advisory")
    telemetry = result["telemetry"]
    print(f"  Loop observations: {telemetry['status']} (loop-telemetry --json)")
    if blocking and getattr(args, "fail_on_issues", False):
        sys.exit(1)


def _format_rollup(result):
    from bootstrap_aggregate import format_loop_lines

    print("\n".join(format_loop_lines(result)))


def _format_telemetry(report, json_out=False, *, write_json):
    from dataclasses import asdict
    if json_out:
        write_json(asdict(report), indent=2)
        return
    print(f"Loop Telemetry ({report.window}): {report.units_considered} units, "
          f"{report.event_count} events")
    for name, metric in report.flow.items():
        value = f"{metric.value} {metric.unit}" if metric.status == "measured" else f"unknown ({metric.reason})"
        print(f"  {name}: {value}")
    for observation in report.observations:
        if "resolved_at" in observation and observation["resolved_at"] is None:
            print(f"  Waiting: {observation['unit_id']} since {observation['timestamp']}")
    print(report.scope_note)


def cmd_loop_rollup(args, *, host_root, format_rollup):
    """Thin entry — delegates to loop_engine.rollup_loop_state (FX-193)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from loop_engine import rollup_loop_state
    view = rollup_loop_state(getattr(args, "target", None) or host_root)
    format_rollup(view)
    if view.get("state") == "invalid":
        sys.exit(2)


def write_cli_json(payload, *, indent=None):
    """Write one JSON response from a governance command."""
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=indent)
    sys.stdout.write("\n")


def cmd_loop(args, *, host_root, write_json):
    from loop_workflow import run
    try:
        result = run(host_root, args)
    except (OSError, ValueError) as exc:
        write_json({"error": str(exc)})
        sys.exit(2)
    write_json(result, indent=2)
    if result.get("state") == "invalid" or (args.action in ("verify", "accept") and result["decision"] in ("iterate", "escalate")):
        sys.exit(2)


def cmd_loop_telemetry(args, *, host_root, format_telemetry):
    """Thin entry — delegates to infra/loop_telemetry.py (0.69.0 telemetry).

    Reads the event log via loop_event_log.read_events (RISK-040 HOST_PROJECT_ROOT,
    never PLUGIN_HOME) and delegates to loop_telemetry.compute_metrics. All logic
    lives in the pure module; this entry is argparse glue + 2 delegated calls
    (RISK-039 thin-entry discipline).
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from loop_event_log import read_events
    from loop_telemetry import compute_metrics
    root = getattr(args, "target", None) or host_root
    log_path = Path(root) / ".governance" / "loop-event-log.jsonl" if root else None
    events = read_events(log_path=log_path) if log_path else []
    win = getattr(args, "window", None)
    # "all" maps to None (all-time) for the pure compute_metrics API.
    window = None if win in (None, "all") else win
    report = compute_metrics(events, window=window)
    format_telemetry(report, json_out=getattr(args, "json", False))


def cmd_check_flow_unit_runtime(args, *, host_root, product_root):
    """Validate the same project snapshot consumed by the session and dashboard."""
    from governance_readers import loop_state
    fixture = getattr(args, "fixture", None)
    root = (product_root / Path(fixture)) if fixture else host_root
    report = loop_state(root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["state"] == "invalid":
        sys.exit(2)
