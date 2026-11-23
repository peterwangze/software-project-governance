"""Render host status, gate and stage views and capability diagnostics."""

import json
from pathlib import Path
import sys


def cmd_status(args, *, host_root):
    """Use the same work-unit projection for ordinary status and startup."""
    from bootstrap_aggregate import cmd_governance_bootstrap
    args.format = "json" if getattr(args, "json", False) else "text"
    args._status_fast_path = True
    args._validated_host_root = host_root
    return cmd_governance_bootstrap(args)


def cmd_governance_context(args, *, host_root):
    """Recover the unit's actual objective, last decision and next action."""
    from governance_readers import loop_state
    root = Path(getattr(args, "fixture", None) or host_root)
    report = loop_state(root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["state"] == "invalid":
        sys.exit(2)


def cmd_gates(args, *, host_root):
    from governance_readers import loop_state
    unit_id = getattr(args, "unit", None)
    gate = getattr(args, "gate_id", None)
    report = loop_state(host_root)
    units = [unit for unit in report["units"] if (not unit_id or unit.get("flow_unit_id") == unit_id)
             and (not gate or unit.get("gate_id") == gate.upper())]
    print(json.dumps({"state": report["state"], "units": units, "message": report.get("message")}, ensure_ascii=False, indent=2))
    if report["state"] == "invalid" or ((unit_id or gate) and not units):
        sys.exit(2)


def cmd_stage(args, *, normalize, skill_path):
    """Read a specialist playbook; the name selects a skill, never project state."""
    path = skill_path(normalize(args.stage_name))
    if not path.is_file():
        sys.exit(f"Unknown playbook: {args.stage_name}")
    print(path.read_text(encoding="utf-8"))


def cmd_stages(args, *, stages):
    print("Available playbooks: " + ", ".join(stages()))


def cmd_first_run_demo(args, *, build_snapshot, validate_snapshot, render, required_fields):
    """Run the local first happy path demo harness."""
    snapshot = build_snapshot()
    rendered = render(snapshot)

    print("== First-Run Demo Harness ==")
    print("Scope: local/demo-only; no external credentials; no network or agent runtime required.")
    print()
    print(rendered)

    if args.assert_snapshot:
        missing = validate_snapshot(snapshot, rendered)
        if missing:
            print("\n== First-Run Demo Result: FAILED ==")
            for item in missing:
                print(f"  - missing required snapshot field/marker: {item}")
            sys.exit(1)
        print("\n== First-Run Demo Result: PASSED ==")
        print("Checked fields: " + ", ".join(required_fields))


def cmd_capability_context(args, *, plugin_root, discover, validate, display_path):
    """Show fact-backed capability context and selection trace."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    fixture = getattr(args, "fixture", None)
    root = plugin_root
    if fixture:
        fixture_path = Path(fixture)
        root = fixture_path if fixture_path.is_absolute() else plugin_root / fixture_path

    context = discover(root)
    print("== Capability Context Selection Trace ==")
    print(f"Root: {display_path(root, plugin_root)}")
    print(f"scenario: {context['scenario']}")
    print(f"host_id: {context['host_id']}")
    print("available_capabilities:")
    for capability in context["available_capabilities"]:
        print(
            f"  - {capability['capability_id']} "
            f"({capability['kind']}, {capability['status']}): {capability['selection_reason']}"
        )
    selected = context["selected_capability"]
    print("selected_capability:")
    print(f"  capability_id: {selected['capability_id']}")
    print(f"  kind: {selected['kind']}")
    print(f"  host_surface: {selected['host_surface']}")
    print(f"  status: {selected['status']}")
    print(f"  selection_reason: {selected['selection_reason']}")
    print("source_facts:")
    for fact in context["source_facts"]:
        print(f"  - {fact}")
    print("rejected_alternatives:")
    for alternative in context["rejected_alternatives"]:
        print(
            f"  - {alternative['capability_id']} "
            f"({alternative['status']}): {alternative['rejection_reason']}"
        )
    print(f"degradation: {context['degradation']['status']} - {context['degradation']['reason']}")
    print(f"side_effect_boundary: {context['side_effect_boundary']}")
    print(f"validation_command: {context['validation_command']}")
    print(f"review_requirement: {context['review_requirement']}")
    print("no_overclaim_boundary:")
    for boundary in context["no_overclaim_boundary"]:
        print(f"  - {boundary}")

    issues = validate(root, sampled_context=context)
    if issues:
        print("\n== Capability Context Result: FAILED ==")
        for issue in issues:
            print(f"  - {issue}")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("\n== Capability Context Result: PASSED ==")


def cmd_check_host_capability_context(args, *, plugin_root, discover, validate, display_path):
    """Run restricted host capability context benchmark guard."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    fixture = getattr(args, "fixture", None)
    root = plugin_root
    if fixture:
        fixture_path = Path(fixture)
        root = fixture_path if fixture_path.is_absolute() else plugin_root / fixture_path

    context = discover(root)
    issues = validate(root, sampled_context=context)
    print("\n=== Host Capability Context Check ===")
    print(f"  Root: {display_path(root, plugin_root)}")
    print(f"  Scenario: {context['scenario']}")
    print(f"  Benchmark kind: {context['benchmark_kind']}")
    print("  Restricted scenarios:")
    for scenario in context["restricted_scenarios"]:
        print(
            f"    - {scenario['scenario_id']}: {scenario['status']} "
            f"selected={scenario['selected_capability']} "
            f"preferred={scenario['preferred_capability']}"
        )
    print(f"  Side-effect boundary: {context['side_effect_boundary']}")
    print(f"  Validation command: {context['validation_command']}")
    if issues:
        print(f"  Result: FAILED — {len(issues)} issue(s)")
        for issue in issues[:20]:
            print(f"    - {issue}")
        if len(issues) > 20:
            print(f"    ... and {len(issues) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("  Result: PASSED — restricted host capability context is benchmark/diagnostic and no-overclaim safe")
    print()


def cmd_check_archive_integrity(_args, *, check_integrity):
    """Standalone subcommand: check-archive-integrity — Check 27."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    result = check_integrity()
    print()
    print("=== Archive Integrity Check (SYSGAP-030 Check 27) ===")
    print(f"  Hot tasks (plan-tracker): {result['hot_tasks']}")
    print(f"  Archived tasks: {result['total_archived_tasks']}")
    print(f"  Index entries: {result['index_entries']}")
    print(f"  Total tasks (hot + archive): {result['total_expected']}")
    if result.get("pending_archive_tasks", 0):
        print(f"  Pending archive tasks: {result['pending_archive_tasks']}")
        print(f"  Archive triggers: {', '.join(result.get('archive_triggers', [])) or 'none'}")

    if result["issues"]:
        print(f"\n  Issues ({len(result['issues'])}):")
        for issue in result["issues"]:
            print(f"    - {issue}")
        print(f"\n  [FAIL] Archive integrity issues detected.")
        import sys
        sys.exit(1)
    else:
        print(f"\n  [PASS] Archive integrity verified.")
    print()
