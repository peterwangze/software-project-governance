"""Render delivery-contract checks and write their deterministic scaffold output."""

from pathlib import Path
import sys


def _configure_stdout():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _print_result(args, issue_count, success):
    if issue_count:
        print(f"\n  Result: FAILED — {issue_count} issue(s)")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print(f"\n  Result: PASSED — {success}")
    print()


def run_contract_check(args, check, *, title, count_label, success,
                       required="required_tasks", entry_key="task_id"):
    _configure_stdout()
    result = check()
    print(f"\n=== {title} ===")
    print(f"  {count_label}: {len(result[required])}")
    issue_count = len(result["issues"])
    for issue in result["issues"]:
        print(f"  [FAIL] {issue}")
    for entry in result["entries"]:
        if entry["status"] == "FAIL":
            issue_count += 1
            print(f"  [FAIL] {entry[entry_key]}: {', '.join(entry['issues'])}")
        else:
            print(f"  [PASS] {entry[entry_key]}")
    _print_result(args, issue_count, success)


def run_interruption_check(args, check):
    """Run User Interruption Policy v2 guard independently."""
    _configure_stdout()
    result = check()
    print("\n=== User Interruption Policy Check ===")
    print(f"  Policy example(s): {len(result['examples'])}")
    print(f"  Active packet policy field(s): {len(result['required_tasks'])}")
    issue_count = len(result["issues"])
    for issue in result["issues"]:
        print(f"  [FAIL] {issue}")
    for example in result["examples"]:
        if example["actual_action"] == example["expected_action"]:
            print(f"  [PASS] {example['id']}: {example['actual_action']}")
        else:
            issue_count += 1
            print(f"  [FAIL] {example['id']}: expected {example['expected_action']}, got {example['actual_action']}")
    for entry in result["entries"]:
        if entry["status"] == "FAIL":
            issue_count += 1
            print(f"  [FAIL] {entry['task_id']}: {', '.join(entry['issues'])}")
        else:
            print(f"  [PASS] {entry['task_id']}: interruption policy ready")
    _print_result(args, issue_count, "user interruption policy is ready")


def generate_scaffold(args, render):
    """Render a deterministic scaffold template to stdout or a file."""
    _configure_stdout()
    try:
        content = render(args.type)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    if getattr(args, "output", None):
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        print(f"Wrote deterministic scaffold: {output_path}")
    else:
        print(content, end="" if content.endswith("\n") else "\n")
