"""Render host validation results and dispatch parsed arguments to their owners."""

import json
import sys


def cmd_check_agent_adapters(args, *, check_agent_adapter_contract):
    """Check mainstream code agent adapter contracts and optional local runtimes."""
    failures = check_agent_adapter_contract(run_runtime=getattr(args, "runtime", False))
    if failures:
        sys.exit(1)


def cmd_check_loop_role_skills(_args, *, check_loop_role_skill_consistency):
    """CLI wrapper for the FIX-191 review SKILL loop-role contract."""
    result = check_loop_role_skill_consistency()
    print("=== Review SKILL Loop-Role Consistency Check ===")
    print(f"  Skills checked: {result['skills_checked']}")
    if result["issues"]:
        print(f"  [FAIL] {len(result['issues'])} issue(s):")
        for issue in result["issues"]:
            print(f"    - {issue}")
        sys.exit(1)
    print("  [PASS] All review SKILL loop-role contracts are consistent.")


def cmd_check_agent_team(args, *, check_agent_activation, check_agent_team_review):
    """Run Check 19 (Agent Team Review) + Check 20 (Agent Activation) together."""
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    issues = 0

    # Check 19: Agent Team Review
    print("\n=== Check 19: Agent Team Review (SYSGAP-035) ===")
    atr_result = check_agent_team_review()
    print(f"  Product-code tasks (completed): {atr_result['total_tasks']}")
    print(f"  Reviewed: {atr_result['reviewed']}")
    if atr_result["unreviewed"] > 0:
        issues += atr_result["unreviewed"]
        print(f"  [FAIL] {atr_result['unreviewed']} product-code task(s) without review evidence:")
        for tid in atr_result["review_gap_tasks"]:
            print(f"    - {tid}")
    else:
        if atr_result["total_tasks"] > 0:
            print(f"  [PASS] All product-code tasks have review evidence.")
        else:
            print(f"  [PASS] No product-code tasks to review.")

    # Check 20: Agent Activation
    print("\n=== Check 20: Agent Activation (SYSGAP-036) ===")
    aa_result = check_agent_activation()
    print(f"  P0 cross-layer product tasks: {aa_result['total_p0_cross_layer']}")
    print(f"  Analyst activated: {aa_result['analyst_activated']}")
    if aa_result["analyst_bypassed"] > 0:
        issues += aa_result["analyst_bypassed"]
        print(f"  [FAIL] {aa_result['analyst_bypassed']} task(s) with impact analysis but no Analyst:")
        for tid in aa_result["bypassed_tasks"]:
            print(f"    - {tid}")
    else:
        if aa_result["total_p0_cross_layer"] > 0:
            print(f"  [PASS] All P0 cross-layer tasks have Analyst involvement.")
        else:
            print(f"  [PASS] No P0 cross-layer product tasks to check.")

    # Summary
    print(f"\n  ── Agent Team Check Summary ──")
    if issues == 0:
        print(f"  Result: PASSED — 0 issues found")
    else:
        print(f"  Result: ISSUES FOUND — {issues} issue(s)")
    print()

    if args.fail_on_issues and issues > 0:
        sys.exit(1)


def cmd_dsh_doctor(args):
    """Run the doctor with parsed engine arguments and propagate its exit scale."""
    from dsh_doctor import run_cli

    code = run_cli(args)
    if code:
        sys.exit(code)
    return code


def cmd_check_runtime_readiness_matrix(args, *, check_runtime_readiness_matrix):
    """Run public runtime/readiness matrix consistency guard."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    issues = check_runtime_readiness_matrix()
    print("\n=== Runtime Readiness Matrix Check ===")
    if issues:
        print(f"  Result: FAILED — {len(issues)} issue(s)")
        for issue in issues[:20]:
            print(f"    - {issue}")
        if len(issues) > 20:
            print(f"    ... and {len(issues) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("  Result: PASSED — public runtime/readiness matrix matches adapter facts")
    print()


def cmd_check_first_session_measurement(args, *, check_first_session_measurement):
    """Run first-session measurement consistency guard."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    issues = check_first_session_measurement()
    print("\n=== First-Session Measurement Check ===")
    if issues:
        print(f"  Result: FAILED — {len(issues)} issue(s)")
        for issue in issues[:20]:
            print(f"    - {issue}")
        if len(issues) > 20:
            print(f"    ... and {len(issues) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("  Result: PASSED — local demo proof is separated from external first-session measurement")
    print()


def cmd_check_governance_packs(args, *, check_governance_packs):
    """Run governance pack registry consistency guard."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    issues = check_governance_packs()
    print("\n=== Governance Pack Registry Check ===")
    if issues:
        print(f"  Result: FAILED — {len(issues)} issue(s)")
        for issue in issues[:20]:
            print(f"    - {issue}")
        if len(issues) > 20:
            print(f"    ... and {len(issues) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("  Result: PASSED — governance pack registry is complete and factual")
    print()


def cmd_check_mainstream_agent_loading(args, *, check_mainstream_agent_loading):
    """Run FIX-122 mainstream agent loading guidance guard."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    issues = check_mainstream_agent_loading()
    print("\n=== Mainstream Agent Loading Check ===")
    if issues:
        print(f"  Result: FAILED — {len(issues)} issue(s)")
        for issue in issues[:20]:
            print(f"    - {issue}")
        if len(issues) > 20:
            print(f"    ... and {len(issues) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("  Result: PASSED — mainstream loading guidance is synchronized and no-overclaim safe")
    print()


def cmd_check_readme_pack_guidance(args, *, check_readme_pack_guidance):
    """Run README first-run profile-to-pack guidance guard."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    issues = check_readme_pack_guidance()
    print("\n=== README Pack Guidance Check ===")
    if issues:
        print(f"  Result: FAILED — {len(issues)} issue(s)")
        for issue in issues[:20]:
            print(f"    - {issue}")
        if len(issues) > 20:
            print(f"    ... and {len(issues) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("  Result: PASSED — README maps first-run profiles to packs without overclaim")
    print()


def cmd_check_governance_pack_status(args, *, check_governance_pack_status):
    """Run pack-aware status and release boundary guard."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    issues = check_governance_pack_status()
    print("\n=== Governance Pack Status Boundary Check ===")
    if issues:
        print(f"  Result: FAILED — {len(issues)} issue(s)")
        for issue in issues[:20]:
            print(f"    - {issue}")
        if len(issues) > 20:
            print(f"    ... and {len(issues) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("  Result: PASSED — status and release surfaces expose pack boundaries without overclaim")
    print()


def cmd_check_dsh_boundary(args):
    """Render the DSH dependency boundary and propagate its failure status."""
    from checks.dsh_boundary import check_dsh_boundary, emit_check_section, failed

    report = check_dsh_boundary()
    if getattr(args, "json", False):
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        emit_check_section(report=report)
    if failed(report) and getattr(args, "fail_on_issues", False):
        sys.exit(1)
