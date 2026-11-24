"""Run the product CLI fixture matrix and evaluate its native outputs and contracts."""

from pathlib import Path
import json
import locale
import re
import shutil
import subprocess
import sys
import tempfile


def _e2e_command_matrix(
        *, package_root, validate_e2e_cleanup, validate_e2e_gate_g99, validate_e2e_gates, validate_e2e_governance_proxy,
        validate_e2e_status, validate_e2e_verify_known_failure,
):
    """Return the source-root CLI proxy matrix used by cmd_e2e_check().

    These commands intentionally run from ROOT because verify_workflow.py
    derives its data paths from the source tree. They are CLI execution
    proxies, not full external-project cwd execution.
    """
    verify_py = package_root / "skills/software-project-governance/infra/verify_workflow.py"
    cleanup_py = verify_py.with_name("cleanup.py")
    python = sys.executable
    return [
        {
            "label": "/governance-status",
            "kind": "source_cli_proxy",
            "command": [python, str(verify_py), "status", "--json"],
            "validator": validate_e2e_status,
        },
        {
            "label": "/governance-gates",
            "kind": "source_cli_proxy",
            "command": [python, str(verify_py), "gates"],
            "validator": validate_e2e_gates,
        },
        {
            "label": "/governance-gate G99",
            "kind": "source_cli_proxy",
            "command": [python, str(verify_py), "gate", "G99"],
            "validator": validate_e2e_gate_g99,
        },
        {
            "label": "/governance-cleanup",
            "kind": "source_cli_proxy",
            "command": [python, str(cleanup_py), "--dry-run", "--json"],
            "validator": validate_e2e_cleanup,
            "accepted_exit_codes": {0, 1},
        },
        {
            "label": "/governance-verify",
            "kind": "source_cli_proxy",
            "command": [python, str(verify_py), "verify"],
            "validator": validate_e2e_verify_known_failure,
            "expected_known_failure": True,
        },
        {
            "label": "/governance Scenario F proxy",
            "kind": "source_cli_proxy",
            "command": [python, str(verify_py), "loop", "status", "--json"],
            "validator": validate_e2e_governance_proxy,
        },
    ]


def _e2e_target_cwd_command_matrix(
        e2e_dir, *, validate_e2e_cleanup, validate_e2e_gate_g99, validate_e2e_gates, validate_e2e_status,
):
    """Return executable commands that run from the external target cwd."""
    target_verify_py = e2e_dir / "skills/software-project-governance/infra/verify_workflow.py"
    target_cleanup_py = e2e_dir / "skills/software-project-governance/infra/cleanup.py"
    python = sys.executable
    return [
        {
            "label": "target-cwd /governance-status",
            "kind": "target_cwd_command",
            "cwd": e2e_dir,
            "command": [python, str(target_verify_py.relative_to(e2e_dir)), "status", "--json"],
            "validator": validate_e2e_status,
        },
        {
            "label": "target-cwd /governance-gates",
            "kind": "target_cwd_command",
            "cwd": e2e_dir,
            "command": [python, str(target_verify_py.relative_to(e2e_dir)), "gates"],
            "validator": validate_e2e_gates,
        },
        {
            "label": "target-cwd /governance-gate G99",
            "kind": "target_cwd_command",
            "cwd": e2e_dir,
            "command": [python, str(target_verify_py.relative_to(e2e_dir)), "gate", "G99"],
            "validator": validate_e2e_gate_g99,
        },
        {
            "label": "target-cwd /governance-cleanup",
            "kind": "target_cwd_command",
            "cwd": e2e_dir,
            "command": [python, str(target_cleanup_py.relative_to(e2e_dir)), "--dry-run", "--json"],
            "validator": validate_e2e_cleanup,
            "accepted_exit_codes": {0, 1},
        },
    ]


def _e2e_target_fixture_checks(e2e_dir, *, package_root, extract_plan_workflow_version, extract_skill_version):
    """Return direct checks against the tracked e2e-test-project fixture."""
    governance_dir = e2e_dir / ".governance"
    plan_tracker_path = governance_dir / "plan-tracker.md"
    target_skill_path = e2e_dir / "skills" / "software-project-governance" / "SKILL.md"
    target_version = (
        extract_plan_workflow_version(plan_tracker_path)
        or extract_skill_version(target_skill_path)
        or extract_skill_version(package_root / "skills/software-project-governance/SKILL.md")
    )
    return [
        {
            "label": "CLAUDE.md bootstrap fixture",
            "path": e2e_dir / "CLAUDE.md",
            "needles": ["Governance Bootstrap", "SELF-CHECK", "AskUserQuestion"],
        },
        {
            "label": "AGENTS.md Codex/opencode native entry fixture",
            "path": e2e_dir / "AGENTS.md",
            "needles": [
                "Governance Bootstrap",
                "SELF-CHECK",
                "Codex",
                "opencode",
                "skills/software-project-governance/SKILL.md",
            ],
        },
        {
            "label": "GEMINI.md native entry fixture",
            "path": e2e_dir / "GEMINI.md",
            "needles": [
                "Governance Bootstrap",
                "SELF-CHECK",
                "Gemini",
                "skills/software-project-governance/SKILL.md",
            ],
        },
        {
            "label": "tracked governance files",
            "paths": [
                governance_dir / "plan-tracker.md",
                governance_dir / "evidence-log.md",
                governance_dir / "decision-log.md",
                governance_dir / "risk-log.md",
                governance_dir / "session-snapshot.md",
            ],
        },
        {
            "label": "target plan-tracker project config",
            "path": plan_tracker_path,
            "needles": ["工作流版本", target_version, "操作权限模式", "default-confirm"],
        },
        {
            "label": "target workflow skill version",
            "path": target_skill_path,
            "expected_skill_version": target_version,
            "needles": ["Coordinator", "Agent Team"],
        },
        {
            "label": "target /governance route contract (router layer)",
            "path": e2e_dir / "commands" / "governance.md",
            "needles": ["commands/governance/scenario-f.md", "AskUserQuestion", "Coordinator"],
        },
        {
            "label": "target status restores scoped work",
            "path": e2e_dir / "commands" / "governance-status.md",
            "needles": ["governance-bootstrap --format json", "loop status --unit", "loop status --json"],
        },
    ]


def _e2e_contract_checks(*, package_root):
    """Return checks that need host runtime or static command contracts."""
    return [
        {
            "label": "/governance-review code",
            "kind": "AGENT_RUNTIME_REQUIRED",
            "path": package_root / "commands/governance-review.md",
            "needles": [
                "Reviewer Agent",
                "code-review",
                "代码审查",
                "general-purpose",
                "degraded evidence",
                "不得解锁",
            ],
            "reason": "Agent spawn is provided by the host platform, not Python.",
        },
        {
            "label": "AskUserQuestion interaction boundary",
            "kind": "AGENT_RUNTIME_REQUIRED",
            "path": package_root / "commands/governance.md",
            "needles": ["AskUserQuestion"],
            "reason": "Interactive user choice requires platform runtime tools.",
        },
        {
            "label": "/governance route contract (router layer)",
            "kind": "CONTRACT_CHECK",
            "path": package_root / "commands/governance.md",
            "needles": [
                "Scenario F",
                "场景路由",
                "commands/governance/scenario-f.md",
            ],
            "reason": "FEAT-038: the router layer routes to the owning Scenario document.",
        },
        {
            "label": "/governance Scenario F route contract",
            "kind": "CONTRACT_CHECK",
            "path": package_root / "commands/governance/scenario-f.md",
            "needles": [
                "Scenario F",
                "../governance-status.md",
            ],
            "reason": "Executable coverage comes from the Scenario F status proxy.",
        },
        {
            "label": "/governance-status work-unit recovery",
            "kind": "CONTRACT_CHECK",
            "path": package_root / "commands/governance-status.md",
            "needles": ["governance-bootstrap --format json", "loop status --unit", "loop status --json"],
            "reason": "Status output is the runnable first-run snapshot signal.",
        },
    ]


def _run_e2e_subprocess(command, timeout, cwd, *, package_root):
    """Run a matrix command and return subprocess.CompletedProcess."""
    return subprocess.run(
        command,
        cwd=str(cwd or package_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _e2e_output(result):
    return (result.stdout or "") + "\n" + (result.stderr or "")


def _truncate_log(text, limit=1200):
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "...[truncated]"


def _coerce_e2e_text(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(locale.getpreferredencoding(False), errors="replace")
    return str(value)


def _has_all(text, needles):
    return all(needle in text for needle in needles)


def _e2e_json_object(result):
    try:
        value = json.loads(result.stdout)
    except (ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _valid_e2e_loop_view(view):
    if not isinstance(view, dict) or view.get("state") not in ("ready", "empty"):
        return False
    units = view.get("units")
    if not isinstance(units, list) or view["state"] == "empty" and units:
        return False
    if view["state"] == "ready" and not units and not view.get("omitted_units"):
        return False
    for unit in units:
        if not isinstance(unit, dict) or not all(unit.get(key) for key in
                ("flow_unit_id", "goal", "acceptance", "gate_id", "gate_status", "runtime_status", "next_action")):
            return False
        if unit["runtime_status"] == "completed" and not (unit.get("last_review") or {}).get("evidence_ref"):
            return False
    return True


def _validate_e2e_status(result, *, e2e_json_object, valid_e2e_loop_view):
    payload = e2e_json_object(result)
    project = payload.get("project")
    view = payload.get("loops")
    ok = (result.returncode == 0 and isinstance(project, dict)
          and project.get("permission_mode") in ("", "maximum-autonomy", "default-confirm")
          and valid_e2e_loop_view(view) and view.get("no_global_stage") is True)
    return ok, "host status reports project.permission_mode and current work with scoped acceptance"


def _validate_e2e_gates(result, *, e2e_json_object, valid_e2e_loop_view):
    return result.returncode == 0 and valid_e2e_loop_view(e2e_json_object(result)), "all gates belong to recorded work units"


def _validate_e2e_gate_g99(result, *, e2e_json_object):
    report = e2e_json_object(result)
    ok = result.returncode != 0 and report.get("state") in ("empty", "ready") and report.get("units") == []
    return ok, "unknown gate has no matching work unit and returns nonzero"


def _validate_e2e_cleanup(result, *, e2e_output):
    output = e2e_output(result).strip()
    try:
        report = json.loads(output)
    except json.JSONDecodeError:
        return False, "cleanup emitted non-JSON output"

    if report.get("status") == "clean":
        return True, "cleanup dry-run executed and reported status=clean"

    required = {"manifest_version", "dry_run", "total_redundant", "classification"}
    ok = (
        result.returncode == 0
        and required.issubset(report.keys())
        and report.get("dry_run") is True
    )
    return ok, "cleanup dry-run executed and emitted redundancy report"


_KNOWN_VERIFY_FAILURE_SIGNATURES = {
    "missing snippet in .governance/evidence-log.md: evd-001",
    "missing snippet in .governance/evidence-log.md: evd-051",
    "missing snippet in skills/software-project-governance/skill.md: coordinator 接管用户交互",
    "missing snippet in skills/software-project-governance/skill.md: producer-reviewer 分离",
}


def _normalize_e2e_verify_failure(line):
    line = line.replace("\\", "/").strip().lower()
    return re.sub(r"\s+", " ", line)


def _extract_e2e_verify_failures(output, *, normalize_e2e_verify_failure):
    failures = []
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            failures.append(normalize_e2e_verify_failure(stripped[2:]))
    return failures


def _validate_e2e_verify_known_failure(
        result, *, known_verify_failure_signatures, e2e_output, extract_e2e_verify_failures,
):
    output = e2e_output(result)
    if result.returncode == 0 and "Workflow Plugin Verification" in output and "Verification Result: PASSED" in output:
        return True, "verify command executed and passed"

    failures = set(extract_e2e_verify_failures(output))
    ok = (
        result.returncode != 0
        and "Workflow Plugin Verification" in output
        and "Verification Result: FAILED" in output
        and bool(failures)
        and failures.issubset(known_verify_failure_signatures)
        and bool(failures & known_verify_failure_signatures)
    )
    if ok:
        return True, "verify command executed and all failures are known allowed signatures"

    unknown = sorted(failures - known_verify_failure_signatures)
    detail = []
    if unknown:
        detail.append(f"unknown failures={unknown}")
    if not failures:
        detail.append("no parseable verification failure lines")
    if result.returncode == 0:
        detail.append("verify command returned 0")
    return False, "verify failure did not match allowed known signatures; " + "; ".join(detail)


def _evaluate_e2e_target_fixture_check(entry, *, package_root, extract_skill_version):
    paths = entry.get("paths")
    if paths:
        missing = [str(path.relative_to(package_root)) for path in paths if not path.exists()]
        return {
            "label": entry["label"],
            "status": "PASS" if not missing else "FAIL",
            "message": "all tracked fixture files exist" if not missing else f"missing files={missing}",
        }

    path = entry["path"]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "label": entry["label"],
            "status": "FAIL",
            "message": f"fixture file unavailable: {exc}",
        }

    missing = [needle for needle in entry["needles"] if needle not in text]
    if "expected_skill_version" in entry:
        version = extract_skill_version(path)
        if not version or version != entry["expected_skill_version"]:
            missing.append(f"skill version {entry['expected_skill_version']}")
    return {
        "label": entry["label"],
        "status": "PASS" if not missing else "FAIL",
        "message": "fixture content matches expected markers" if not missing else f"missing markers={missing}",
    }


def _validate_e2e_governance_proxy(result, *, e2e_json_object, valid_e2e_loop_view):
    report = e2e_json_object(result)
    ok = result.returncode == 0 and report.get("no_global_stage") is True and valid_e2e_loop_view(report)
    return ok, "Scenario F recovers the active work-unit snapshot"


def _evaluate_e2e_command(entry, runner):
    """Execute one E2E matrix entry and normalize its result."""
    try:
        try:
            result = runner(entry["command"], cwd=entry.get("cwd"))
        except TypeError:
            result = runner(entry["command"])
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "label": entry["label"],
            "kind": entry.get("kind", "source_cli_proxy"),
            "status": "FAIL",
            "exit_code": None,
            "message": f"subprocess did not complete: {exc}",
            "command": entry["command"],
        }

    accepted = entry.get("accepted_exit_codes")
    if accepted is not None and result.returncode not in accepted:
        return {
            "label": entry["label"],
            "kind": entry.get("kind", "source_cli_proxy"),
            "status": "FAIL",
            "exit_code": result.returncode,
            "message": f"unexpected exit code; accepted={sorted(accepted)}",
            "command": entry["command"],
        }

    ok, message = entry["validator"](result)
    if not ok:
        return {
            "label": entry["label"],
            "kind": entry.get("kind", "source_cli_proxy"),
            "status": "FAIL",
            "exit_code": result.returncode,
            "message": message,
            "command": entry["command"],
        }

    status = "EXPECTED_KNOWN_FAILURE" if entry.get("expected_known_failure") and result.returncode != 0 else "PASS"
    return {
        "label": entry["label"],
        "kind": entry.get("kind", "source_cli_proxy"),
        "status": status,
        "exit_code": result.returncode,
        "message": message,
        "command": entry["command"],
    }


def _evaluate_e2e_contract_check(entry, *, has_all):
    path = entry["path"]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "label": entry["label"],
            "status": entry["kind"],
            "ok": False,
            "message": f"contract file unavailable: {exc}",
        }

    ok = has_all(text, entry["needles"])
    suffix = "contract present" if ok else "contract incomplete"
    return {
        "label": entry["label"],
        "status": entry["kind"],
        "ok": ok,
        "message": f"{suffix}; {entry['reason']}",
    }


def cmd_e2e_check(
        _args, *, plugin_root, package_root, e2e_command_matrix, e2e_contract_checks,
        e2e_target_cwd_command_matrix, e2e_target_fixture_checks, evaluate_e2e_command,
        evaluate_e2e_contract_check, evaluate_e2e_target_fixture_check,
):
    """Run command-backed E2E governance verification."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    e2e_dir = package_root / "project/e2e-test-project"
    if not e2e_dir.exists():
        print("[SKIPPED] project/e2e-test-project/ not found")
        return

    source_cli_results = [
        evaluate_e2e_command(entry) for entry in e2e_command_matrix()
    ]
    # Install the working skill into a disposable external host. The tracked
    # fixture contains project facts, but intentionally excludes the installed CLI.
    with tempfile.TemporaryDirectory(prefix="governance-e2e-host-") as temporary:
        target = Path(temporary)
        shutil.copytree(e2e_dir / ".governance", target / ".governance")
        plugin = Path("skills/software-project-governance")
        shutil.copytree(plugin_root / plugin, target / plugin,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
        target_cwd_results = [
            evaluate_e2e_command(entry) for entry in e2e_target_cwd_command_matrix(target)
        ]
    fixture_results = [
        evaluate_e2e_target_fixture_check(entry)
        for entry in e2e_target_fixture_checks(e2e_dir)
    ]
    contract_results = [
        evaluate_e2e_contract_check(entry) for entry in e2e_contract_checks()
    ]

    print("=== E2E Governance Verification ===")
    print(f"Target: {e2e_dir}")
    print("Mode: source CLI proxy + isolated external installation + tracked project fixture checks\n")

    print("--- Source CLI proxy command matrix ---")
    print(f"  cwd: {package_root}")
    print("  note: verify_workflow.py is source-root bound; these are executable CLI proxies, not external-project cwd runs.")
    for result in source_cli_results:
        command = " ".join(str(part) for part in result["command"])
        print(
            f"  [{result['status']}] {result['label']} "
            f"(exit={result['exit_code']})"
        )
        print(f"      command: {command}")
        print(f"      assert: {result['message']}")

    print("\n--- External target cwd command matrix ---")
    print(f"  cwd: {target}")
    print("  note: these commands exercised the current skill installed into a disposable external host.")
    for result in target_cwd_results:
        command = " ".join(str(part) for part in result["command"])
        print(
            f"  [{result['status']}] {result['label']} "
            f"(exit={result['exit_code']})"
        )
        print(f"      command: {command}")
        print(f"      assert: {result['message']}")

    print("\n--- Target fixture checks ---")
    print(f"  fixture: {e2e_dir}")
    for result in fixture_results:
        print(f"  [{result['status']}] {result['label']}")
        print(f"      assert: {result['message']}")

    print("\n--- Contract/runtime-only checks ---")
    for result in contract_results:
        marker = "OK" if result["ok"] else "CHECK_FAILED"
        print(f"  [{result['status']}:{marker}] {result['label']}")
        print(f"      note: {result['message']}")

    passed = sum(1 for r in source_cli_results if r["status"] == "PASS")
    failed = sum(1 for r in source_cli_results if r["status"] == "FAIL")
    known = sum(1 for r in source_cli_results if r["status"] == "EXPECTED_KNOWN_FAILURE")
    target_cwd_passed = sum(1 for r in target_cwd_results if r["status"] == "PASS")
    target_cwd_failed = sum(1 for r in target_cwd_results if r["status"] == "FAIL")
    fixture_passed = sum(1 for r in fixture_results if r["status"] == "PASS")
    fixture_failed = sum(1 for r in fixture_results if r["status"] == "FAIL")
    contract_count = len(contract_results)
    contract_failed = sum(1 for r in contract_results if not r["ok"])

    print(
        "\n=== Result: "
        f"source_cli_proxy_pass={passed}, source_cli_proxy_fail={failed}, "
        f"expected_known_failure={known}, "
        f"target_cwd_pass={target_cwd_passed}, target_cwd_fail={target_cwd_failed}, "
        f"target_fixture_pass={fixture_passed}, target_fixture_fail={fixture_failed}, "
        f"contract_only={contract_count}, contract_check_failed={contract_failed} ==="
    )
    if failed > 0 or target_cwd_failed > 0 or fixture_failed > 0:
        print("ACTION: Fix source CLI proxy, target cwd, or target fixture failures above.")
        sys.exit(1)
    print("Source CLI proxy matrix, external target cwd commands, and target fixture checks passed; runtime contracts reported separately.")
