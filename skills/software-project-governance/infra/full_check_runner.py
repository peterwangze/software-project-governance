"""Run full-health sections in order and render the combined issue count."""


def run_full_checks(section_results):
    """Consuming one result at a time preserves output and stops on the original exception."""
    all_issues = sum(section_results)
    print(f"\n┌─ Governance Health Summary ──────────────────────────┐")
    if all_issues == 0:
        print(f"│  Result: PASSED — 0 issues found")
    else:
        print(f"│  Result: ISSUES FOUND — {all_issues} issue(s)")
    print("└──────────────────────────────────────────────────────┘")

    return all_issues
