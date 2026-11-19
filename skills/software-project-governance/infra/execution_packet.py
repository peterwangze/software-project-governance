"""Build a task's execution packet from its plan, intake, and maintained contract."""

import json
from datetime import datetime

from contracts import QUALITY_BUDGET_DIMENSIONS


def build_execution_packet(task):
    scope = task.get("closure_path") or task.get("title") or task["task_id"]
    task_label = f"{task['task_id']} {task.get('title', '').strip()}".strip()
    return {
        "task_id": task["task_id"],
        "priority": task.get("priority", ""),
        "status": task.get("status", ""),
        "goal": task_label,
        "product_success_contract": {
            "user": f"TO_BE_DEFINED: impacted persona for {task_label}",
            "job_to_be_done": f"TO_BE_DEFINED: user job and desired outcome for {task_label}",
            "non_goals": [
                "TO_BE_DEFINED: explicit non-goal that protects the task from scope drift.",
                "TO_BE_DEFINED: explicit non-goal that prevents process evidence from replacing product value.",
            ],
            "success_metrics": [
                "TO_BE_DEFINED: user-visible outcome or acceptance scenario for this task.",
                "TO_BE_DEFINED: runnable E2E, test, or command that proves the outcome.",
            ],
            "competitive_baseline": "TO_BE_DEFINED: mature-team or competing-product baseline this task must match.",
            "done_definition": [
                "TO_BE_DEFINED: product success evidence is recorded with concrete facts.",
                "TO_BE_DEFINED: independent review confirms the user outcome is not replaced by process completion.",
            ],
        },
        "acceptance_contract": {
            "scenario": f"TO_BE_DEFINED: user-visible acceptance scenario for {task_label}",
            "command": "TO_BE_DEFINED: runnable E2E, smoke, unit, or validation command",
            "expected_output": "TO_BE_DEFINED: concrete pass output, assertion, or observable demo result",
            "last_run": {
                "status": "TO_BE_DEFINED",
                "exit_code": None,
                "summary": "TO_BE_DEFINED: last run output summary with evidence location",
            },
            "demo_evidence": "TO_BE_DEFINED: demo, CLI output, or artifact proving the scenario",
        },
        "quality_budget": {
            "dimensions": {
                dimension: {
                    "threshold": f"TO_BE_DEFINED: minimum acceptable {dimension} threshold for {task_label}",
                    "validation": f"TO_BE_DEFINED: command, check, metric source, or quality signal for {dimension}",
                    "status": "TO_BE_DEFINED",
                    "evidence": f"TO_BE_DEFINED: latest {dimension} result or planned evidence location",
                    "exception": "",
                }
                for dimension in QUALITY_BUDGET_DIMENSIONS
            }
        },
        "vertical_slice": {
            "user_visible_slice": f"TO_BE_DEFINED: smallest user-visible slice for {task_label}",
            "demo_path": "TO_BE_DEFINED: runnable demo, smoke test, URL, screenshot, or command proving the slice",
            "scope_guard": f"TO_BE_DEFINED: files and behavior in scope for this slice only ({scope})",
            "rollback_plan": "TO_BE_DEFINED: how to revert or disable the slice if validation fails",
            "status": "TO_BE_DEFINED",
            "evidence": "TO_BE_DEFINED: latest demo proof or planned evidence location",
        },
        "interruption_policy": {
            "mode": "critical-only: default execute routine reversible work and record assumptions when needed",
            "critical_triggers": [
                "Ask the user when product intent is unclear.",
                "Ask the user when acceptance standard or done criteria are unclear.",
                "Ask the user before irreversible, release, risk acceptance, external dependency, or mode change decisions.",
            ],
            "auto_execute": [
                "Run routine execution, local validation, focused code edits, and governance record updates when scope is known and reversible.",
                "Commit and push normal single-task changes when validation, evidence, and review gates are satisfied.",
            ],
            "assumption_record": {
                "assumption": "TO_BE_DEFINED: default choice used for a reversible non-critical ambiguity",
                "basis": "TO_BE_DEFINED: fact source or repository pattern supporting the default",
                "reversibility": "TO_BE_DEFINED: why the choice can be changed without product damage",
                "validation": "TO_BE_DEFINED: command or demo that will verify the assumption",
                "rollback": "TO_BE_DEFINED: how to revert if the assumption is wrong",
            },
            "interruption_budget": "At most one user interruption per work unit unless a new critical trigger appears.",
        },
        "allowed_change_scope": [
            f"Only change files required by this task row: {scope}",
            "Keep unrelated refactors, release version bumps, and fixture sync out of this task unless listed in the task scope.",
        ],
        "required_evidence": [
            "evidence-log entry with 事实依据, 目标对齐, 用户影响, and 结构化事实 JSON",
            "validation commands with exit_code and concise output summary",
            "independent review evidence or explicit degraded review evidence that does not claim full separation",
        ],
        "next_commands": [
            "Use acceptance_contract.command once it specifies the host project's runnable check.",
        ],
        "done_definition": [
            task.get("closure_path") or "Task closure path from plan-tracker is satisfied.",
            "Code Reviewer or matching Reviewer has APPROVED the product-code change.",
            "Commit and push are completed for this single task.",
        ],
        "source": "plan-tracker.md##当前活跃事项",
    }


def merge_intake_contract(scaffold, existing, plan_acceptance, governance_dir):
    """Seed the two contract fields only when absent or still the stock template."""
    from change_triage import DEMAND_REVISION_SUFFIX, TRIAGE_SCHEMA_VERSION, TRIAGE_SUBDIR

    packet = {**scaffold, **existing}
    task_id = scaffold["task_id"]
    ref = f"{TRIAGE_SUBDIR}/{task_id}.json"
    path = governance_dir / ref
    criteria = ""
    try:
        with path.open(encoding="utf-8") as stream:
            record = json.load(stream)
    except FileNotFoundError:
        intake = existing.get("intake")
        if isinstance(intake, dict) and intake.get("record") == ref:
            raise ValueError(f"{path}: previously referenced triage record is missing")
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from exc
    else:
        if (not isinstance(record, dict) or record.get("task_id") != task_id
                or type(record.get("schema_version")) is not int
                or record["schema_version"] != TRIAGE_SCHEMA_VERSION):
            raise ValueError(f"{path}: incompatible triage record for {task_id}")
        files = record.get("files")
        if not isinstance(files, list) or not all(isinstance(f, str) and f.strip() for f in files):
            raise ValueError(f"{path}: files must be a list of paths")
        if files and packet["allowed_change_scope"] == scaffold["allowed_change_scope"]:
            packet["allowed_change_scope"] = files
        criteria = record.get("acceptance", "")
        if not isinstance(criteria, str):
            raise ValueError(f"{path}: acceptance must be text")
        intake = {"record": ref}
        revisions = path.with_name(task_id + DEMAND_REVISION_SUFFIX)
        if revisions.is_file():
            intake["demand_revisions"] = revisions.relative_to(governance_dir).as_posix()
        packet["intake"] = intake

    contract = packet["acceptance_contract"]
    if isinstance(contract, dict):
        placeholder = scaffold["acceptance_contract"]["expected_output"]
        current = contract.get("expected_output", placeholder)
        contract = dict(contract)
        # Only a value we last copied from the mutable plan can follow its revisions.
        previous_plan = contract.pop("expected_output_from_plan", None)
        if current == placeholder or (previous_plan is not None and current == previous_plan):
            if criteria.strip():
                contract["expected_output"] = criteria
            elif plan_acceptance:
                contract["expected_output"] = contract["expected_output_from_plan"] = plan_acceptance
            elif previous_plan is not None:
                contract["expected_output"] = placeholder
        packet["acceptance_contract"] = contract
    return packet


def generate_packet_document(tasks, *, task_ids, existing, governance_dir, build_packet):
    packets = {}
    for task in tasks:
        task_id = task["task_id"]
        if task_ids is not None and task_id not in task_ids:
            continue
        packet = merge_intake_contract(build_packet(task), existing.get(task_id, {}),
                                       task.get("acceptance", ""), governance_dir)
        packet["task_id"] = task_id
        for field in ("priority", "status"):
            if field in task:
                packet[field] = task[field]
        packets[task_id] = packet
    return {
        "version": 1,
        "generated_at": datetime.now().replace(microsecond=0).isoformat(),
        "packets": packets,
    }
