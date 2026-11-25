"""Build a task's execution packet from its plan, intake, and maintained contract."""

import json
from datetime import datetime



def read_goal_packets(governance_dir):
    """Bound the documents consumed by the native host before parsing their bytes."""
    import stat
    from delivery_acceptance import _json_object, _plain_stat

    path = governance_dir / "execution-packets.json"
    try:
        info = _plain_stat(path)
    except FileNotFoundError:
        return {}, "missing execution packets"
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("expected a regular execution packet record")
    limit = 4 * 1024 * 1024
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("execution packets are too large")
    data = json.loads(raw.decode("utf-8"), object_pairs_hook=_json_object)
    packets = data.get("packets", data) if isinstance(data, dict) else None
    if not isinstance(packets, dict):
        raise ValueError("invalid execution packets")
    return packets, ""


def has_native_unit_identity(key, packet):
    from loop_workflow import UNIT_ID

    if not UNIT_ID.fullmatch(key) or not isinstance(packet, dict) or packet.get("task_id") != key:
        return False
    units = packet.get("work_units")
    return isinstance(units, list) and any(
        isinstance(unit, dict) and key in (unit.get("flow_unit_id"), unit.get("task_id")) for unit in units
    )


def build_execution_packet(task, *, contracts=(), quality_dimensions=()):
    scope = task.get("closure_path") or task.get("title") or task["task_id"]
    task_label = f"{task['task_id']} {task.get('title', '').strip()}".strip()
    scaffold = {
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
                for dimension in quality_dimensions
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
                "Commit or publish only within the authorization recorded for this delivery.",
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
        "required_evidence": ["The observed result of the receiver's acceptance operation, with the command and exit status."],
        "next_commands": ["Run the host's acceptance_contract.command and compare the observed output."],
        "done_definition": [task.get("acceptance") or scope],
        "source": "plan-tracker.md##当前活跃事项",
    }

    for name in OPTIONAL_CONTRACTS:
        if name not in contracts:
            scaffold.pop(name)
    if contracts:
        scaffold["required_contracts"] = sorted(contracts)
    if quality_dimensions:
        scaffold["quality_budget"]["required_dimensions"] = list(quality_dimensions)
    return scaffold


OPTIONAL_CONTRACTS = ("product_success_contract", "quality_budget", "vertical_slice", "interruption_policy")


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

    if scaffold.get("required_contracts"):
        required = existing.get("required_contracts", [])
        if not isinstance(required, list) or not all(isinstance(name, str) for name in required):
            raise ValueError(f"{task_id}: malformed required_contracts")
        packet["required_contracts"] = sorted(set(required) | set(scaffold["required_contracts"]))
    if "quality_budget" in scaffold and "quality_budget" in existing:
        spec = scaffold["quality_budget"]
        maintained = existing["quality_budget"]
        if (not isinstance(maintained, dict) or not isinstance(maintained.get("dimensions"), dict)
                or not isinstance(maintained.get("required_dimensions", []), list)
                or not all(isinstance(name, str) for name in maintained.get("required_dimensions", []))):
            raise ValueError(f"{task_id}: cannot merge new dimensions into a malformed quality budget")
        packet["quality_budget"] = {**maintained, "dimensions": {**spec["dimensions"], **maintained["dimensions"]},
                                    "required_dimensions": sorted(set(spec.get("required_dimensions", [])) |
                                                                  set(maintained.get("required_dimensions", [])))}
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
    from governance_readers import loop_state

    view = loop_state(governance_dir.parent, latest_learning_only=True)
    if view["state"] == "invalid":
        raise ValueError(view["message"])
    units_by_task = {}
    tasks_by_id = {task["task_id"]: task for task in tasks}
    for unit in view["units"]:
        task_id = unit["task_id"] or unit["flow_unit_id"]
        if task_ids is not None and task_id not in task_ids and unit["flow_unit_id"] in task_ids:
            task_id = unit["flow_unit_id"]
        if unit["runtime_status"] == "completed" and task_id not in tasks_by_id and not (task_ids and task_id in task_ids):
            continue
        units_by_task.setdefault(task_id, []).append(unit)
        tasks_by_id.setdefault(task_id, {"task_id": task_id, "title": unit["goal"],
                                          "status": unit["runtime_status"]})

    packets = {}
    for task_id, task in tasks_by_id.items():
        if task_ids is not None and task_id not in task_ids:
            continue
        scaffold = build_packet(task)
        packet = merge_intake_contract(scaffold, existing.get(task_id, {}),
                                       task.get("acceptance", ""), governance_dir)
        units = units_by_task.get(task_id, [])
        if units:
            packet["work_units"] = []
            for unit in units:
                summary = {field: unit[field] for field in (
                    "flow_unit_id", "parent_unit_id", "task_id", "goal", "acceptance",
                    "active_loop_tier", "gate_id", "loop_count", "next_action",
                )}
                for field in ("intent", "root_contract", "criterion_scope", "previous_unit_id", "source_learning", "learning_count", "learning"):
                    if unit.get(field) is not None:
                        summary[field] = unit[field]
                if "learning_count" in summary:
                    summary["learning_history"] = f"loop materials --unit {unit['flow_unit_id']} --query <terms>"
                packet["work_units"].append(summary)
            if len(units) == 1:
                packet["goal"] = units[0]["goal"]
                if packet["done_definition"] == scaffold["done_definition"]:
                    packet["done_definition"] = [units[0]["acceptance"]]
                acceptance_contract = packet["acceptance_contract"]
                if isinstance(acceptance_contract, dict):
                    expected = acceptance_contract.get("expected_output")
                    if expected in (None, scaffold["acceptance_contract"]["expected_output"]):
                        acceptance_contract["expected_output"] = units[0]["acceptance"]
        elif packet.get("work_units"):
            raise ValueError(f"{task_id}: the recorded work unit is missing")
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
