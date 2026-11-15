"""Read-only goal-scoped recommendations from the current governance facts."""

from __future__ import annotations

import json
import math
from pathlib import Path

from delivery_acceptance import evaluate_delivery_acceptance
from goal_bridge import bridge_disabled, goal_status
from governance_store import LOCKS_FILE_NAME, StoreError, locks_load
from task_priority import (
    DEMAND_SOURCE_CONFLICT,
    _priority_sort_key,
    _resolve_row_demand_sources,
    compute_unblocked_tasks,
    parse_task_dependencies,
    read_archive_index_completed_ids,
)


def _read_locks(governance_dir: Path) -> dict:
    try:
        (governance_dir / LOCKS_FILE_NAME).lstat()
    except FileNotFoundError:
        return {}
    _, data = locks_load(governance_dir)
    return data["active_tasks"]


def _goal_link(packet: object, goal_id: str, contract_sha256: str, required_criteria: set) -> tuple | None:
    if packet is None:
        return None
    if not isinstance(packet, dict):
        raise ValueError("malformed execution packet")
    if "goal_link" not in packet:
        return None
    link = packet["goal_link"]
    fields = {"goal_id", "contract_sha256", "criteria", "action"}
    if not isinstance(link, dict) or not fields <= link.keys() <= fields | {"estimated_rounds"}:
        raise ValueError("malformed goal_link")
    if link["goal_id"] != goal_id or link["contract_sha256"] != contract_sha256:
        raise ValueError("goal_link does not match this goal and frozen contract")
    criteria = link["criteria"]
    if (not isinstance(criteria, list) or not criteria
            or not all(isinstance(item, str) and item in required_criteria for item in criteria)
            or len(set(criteria)) != len(criteria)):
        raise ValueError("goal_link criteria must be distinct IDs in the delivery contract")
    action = link["action"]
    if action not in ("repair", "verify"):
        raise ValueError("goal_link action must be repair or verify")
    estimate = link.get("estimated_rounds")
    if "estimated_rounds" in link and (type(estimate) is not int or estimate <= 0):
        raise ValueError("estimated_rounds must be a positive integer")
    return action, set(criteria), estimate


def _budget_state(zones: dict) -> str:
    if not isinstance(zones, dict):
        raise ValueError("budget zones must be a mapping")
    if not zones:
        return "UNMEASURED"
    labels = set()
    for dimension, data in zones.items():
        if dimension not in ("rounds", "tokens", "wall_clock", "cost"):
            raise ValueError("unknown budget dimension")
        if not isinstance(data, dict) or data.get("zone") not in ("safe", "warning", "danger"):
            raise ValueError("invalid budget zone")
        used, limit = data.get("used"), data.get("limit")
        if (not all(type(value) in (int, float) and math.isfinite(value) for value in (used, limit))
                or used < 0 or limit <= 0):
            raise ValueError("invalid budget consumption or limit")
        remaining = data.get("remaining_until_danger")
        if remaining is not None and (
            type(remaining) not in (int, float) or not math.isfinite(remaining) or remaining < 0
        ):
            raise ValueError("invalid remaining budget")
        labels.add(data["zone"])
    if "danger" in labels:
        return "DANGER"
    return "WARNING" if "warning" in labels else "SAFE"


def _gap_report(acceptance: dict) -> dict:
    verified = acceptance.get("criteria_results", {})
    gaps = {key: "repair" if verified.get(key, {}).get("status") == "FAIL" else "verify"
            for key in acceptance["required_criteria"]
            if verified.get(key, {}).get("status") != "PASS"}
    if not gaps:
        # Every criterion passed, yet the receipt itself was rejected (for
        # example it contains an unexpected criterion). Reverify the receipt.
        return dict.fromkeys(acceptance["required_criteria"], "verify")
    return gaps


def _recommendations(report, packets, active, goal, gaps, remaining_rounds, warning):
    ranked, in_flight, diagnostics = [], [], []
    required = set(goal["required_criteria"])

    def linked_task(task_id):
        try:
            return _goal_link(packets.get(task_id), goal["goal_id"], goal["contract_sha256"], required)
        except ValueError as exc:
            diagnostics.append(f"{task_id}: {exc}")
            return None

    current_tasks = {task.task_id for task in report.unblocked + report.non_executable}
    current_tasks.update(item.task.task_id for item in report.blocked)
    owned_gaps = set()
    for task_id in sorted(current_tasks.intersection(active)):
        link = linked_task(task_id)
        coverage = link[1].intersection(gaps) if link else set()
        if coverage:
            in_flight.append(task_id)
            owned_gaps.update(coverage)

    for task in report.recommended_next:
        task_id = task.task_id
        if task_id in active:
            continue
        link = linked_task(task_id)
        if link is None:
            continue
        action, criteria, estimate = link
        matched = sorted(key for key in criteria if gaps.get(key) == action)
        if not matched:
            continue
        if criteria & owned_gaps:
            diagnostics.append(f"{task_id}: linked criterion is already in flight")
            continue
        if task.demand_source == DEMAND_SOURCE_CONFLICT:
            diagnostics.append(f"{task_id}: conflicting demand source")
            continue
        if warning and (estimate is None or remaining_rounds is None):
            diagnostics.append(f"{task_id}: budget warning requires an estimate and measured round limit")
            continue
        if estimate is not None and remaining_rounds is not None and estimate >= remaining_rounds:
            diagnostics.append(f"{task_id}: estimated rounds can reach the collection boundary")
            continue
        mode = "resume" if task_id == goal["task_ref"] else "new"
        candidate = {
            "task_id": task_id, "priority": task.priority, "demand_source": task.demand_source,
            "version": task.target_version or "", "action": action, "criteria": matched,
            "estimated_rounds": estimate, "mode": mode,
            "reason": "verified criterion failure" if action == "repair" else "criterion evidence must be verified",
        }
        priority, source, *legacy_tiebreak = _priority_sort_key(task)
        ranked.append(((priority, source, estimate if warning else 0, action != "repair",
                        mode != "resume", -len(matched), *legacy_tiebreak), candidate))
    for blocked in report.blocked:
        packet = packets.get(blocked.task.task_id)
        if isinstance(packet, dict) and isinstance(packet.get("goal_link"), dict):
            if packet["goal_link"].get("goal_id") == goal["goal_id"]:
                diagnostics.append(f"{blocked.task.task_id}: blocked by {', '.join(blocked.blocking_dependencies)}")
    return [candidate for _, candidate in sorted(ranked, key=lambda item: item[0])], in_flight, diagnostics


def _recommend_work_packages(packages, packets, active, goal, gaps, remaining_rounds, warning):
    if packets is None and active:
        # Missing packet associations prevent a reliable overlap check.
        return [], []
    owned_gaps, linked_active = set(), []
    for task_id in sorted(active):
        try:
            link = _goal_link(packets.get(task_id), goal["goal_id"], goal["contract_sha256"],
                              goal["required_criteria"])
        except ValueError:
            continue
        if link is not None and (covered := link[1].intersection(gaps)):
            linked_active.append(task_id)
            owned_gaps.update(covered)

    recommended = []
    for package in packages:
        matched = [key for key in package["criteria"] if gaps.get(key) == package["action"]]
        if not matched or owned_gaps.intersection(matched):
            continue
        if remaining_rounds is None:
            if warning:
                continue
        elif package["estimated_rounds"] >= remaining_rounds:
            continue
        recommended.append({**package, "criteria": matched})
    return recommended, linked_active


def plan_goal_candidates(project_root: Path, goal_id: str, *, load_packets, top_n: int = 3,
                         work_packages=()) -> dict:
    """Build only a recommendation. No task, checkpoint, or snapshot is written."""
    root = Path(project_root)
    gov = root / ".governance"
    output = {"goal_id": goal_id, "recommended_top_n": [], "in_flight": [], "diagnostics": []}
    if work_packages:
        output["work_packages"] = []
    try:
        goal = goal_status(goal_id, governance_dir=gov)
        if goal.get("error"):
            return dict(output, state="ERROR", diagnostics=[goal.get("detail", "goal state is unreadable")])
        zones = goal["zones"]
        budget = _budget_state(zones)
    except (ValueError, TypeError, OverflowError, OSError) as exc:
        return dict(output, state="ERROR", diagnostics=[f"invalid goal state: {exc}"])
    output.update(
        original_intent=goal.get("original_intent"), intent_sha256=goal.get("intent_sha256"),
        contract_sha256=goal.get("contract_sha256"), goal_state=goal["state"],
        revision=goal["revision"], task_ref=goal["task_ref"],
        obligations=goal.get("obligations", []), scope_ruling=goal["scope_ruling"],
        checkpoint_materialized=goal.get("checkpoint_materialized"),
        budget_state=budget, budget_signal=goal.get("budget_signal", "unknown"), zones=zones,
        unmeasured_dimensions=goal.get("unmeasured_dimensions", []),
    )
    if bridge_disabled():
        return dict(output, state="HOLD", diagnostics=[
            "the goal bridge is disabled, so no current budget authority is available",
        ])
    if goal["state"] != "RUNNING" or budget == "DANGER":
        next_step = {
            "DRAINING": "finish only in-flight work, then save the goal-bridge checkpoint",
            "CHECKPOINTED": "await an authorized scope ruling" if goal.get("checkpoint_materialized")
                            else "materialize the goal-bridge checkpoint before requesting a scope ruling",
            "BLOCKED": "obtain an authorized resume ruling before starting work",
        }.get(goal["state"], "the recorded budget reached its collection boundary; save a goal-bridge checkpoint")
        return dict(output, state="HOLD", diagnostics=[next_step])
    if not goal.get("original_intent") or not goal.get("contract_sha256"):
        return dict(output, state="AWAIT_INTENT", diagnostics=["bind the original user intent and delivery contract"])
    if budget == "UNMEASURED":
        return dict(output, state="AWAIT_BUDGET", diagnostics=["record the observed budget with goal-bridge"])

    acceptance = evaluate_delivery_acceptance(root, goal_id=goal_id)
    if not acceptance.get("contract_sha256"):
        return dict(output, state="AWAIT_CONTRACT", diagnostics=acceptance["issues"])
    if acceptance["contract_sha256"] != goal["contract_sha256"]:
        return dict(
            output, state="CONTRACT_CHANGED", current_contract_sha256=acceptance["contract_sha256"],
            diagnostics=["current contract differs from the frozen goal contract"],
        )
    output["acceptance_state"] = acceptance["state"]
    if acceptance["pass"]:
        return dict(output, state="CHECK_COMPLETION", diagnostics=[
            "delivery passed; reconcile recovered obligations, active locks and existing authorization, then run "
            "goal-bridge --action check-completion before completing the goal",
        ])

    output["criterion_gaps"] = gaps = _gap_report(acceptance)
    packets = None
    legacy_error = None
    try:
        active = _read_locks(gov) if work_packages else None
    except (OSError, ValueError, StoreError, RecursionError) as exc:
        return dict(output, state="ERROR", diagnostics=[str(exc)])
    try:
        packet_data, packet_error = load_packets()
        if packet_error:
            raise ValueError(packet_error)
        packets = packet_data
        tasks, demand_warnings = _resolve_row_demand_sources(
            parse_task_dependencies((gov / "plan-tracker.md").read_text(encoding="utf-8")), gov,
        )
        report = compute_unblocked_tasks(tasks, archive_completed_ids=read_archive_index_completed_ids(gov))
        if active is None:
            active = _read_locks(gov)
    except (OSError, ValueError, StoreError, RecursionError) as exc:
        if not work_packages:
            return dict(output, state="ERROR", diagnostics=[str(exc)])
        legacy_error = str(exc)

    rounds = zones.get("rounds")
    remaining = rounds.get("remaining_until_danger") if rounds else None
    warning = budget == "WARNING"
    goal["required_criteria"] = set(acceptance["required_criteria"])
    if legacy_error is None:
        eligible, in_flight, exclusions = _recommendations(report, packets, active, goal, gaps, remaining, warning)
        diagnostics = acceptance["issues"] + demand_warnings + exclusions
    else:
        eligible, in_flight = [], []
        diagnostics = acceptance["issues"] + [legacy_error]
    scoped_packages = []
    if work_packages:
        scoped_packages, linked_active = _recommend_work_packages(work_packages, packets, active, goal, gaps,
                                                                   remaining, warning)
        output["work_packages"] = scoped_packages[:max(0, top_n)]
        in_flight = sorted(set(in_flight).union(linked_active))
    if eligible or scoped_packages:
        state = "READY"
    elif in_flight:
        state = "WAIT_ACTIVE"
    elif legacy_error is not None:
        state = "ERROR"
    else:
        state = "NO_ELIGIBLE_TASK"
        diagnostics.append("no executable task is linked to the current acceptance gaps")
    return dict(
        output, state=state,
        recommended_top_n=eligible[:max(0, top_n)], in_flight=in_flight, diagnostics=diagnostics,
    )


def run_goal_candidates(args, *, project_root: Path, load_packets) -> int:
    if args.write or args.refresh:
        result = {"goal_id": args.goal, "state": "ERROR", "recommended_top_n": [],
                  "diagnostics": ["--write and --refresh select legacy snapshots, not goal mode"]}
    else:
        result = plan_goal_candidates(project_root, args.goal, load_packets=load_packets, top_n=args.top_n)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["state"] == "ERROR" else 0
