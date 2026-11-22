"""Native work-unit intake, execution and evidence-bound gate decisions."""

import hashlib
import json
import subprocess
import re
from pathlib import Path

import loop_admission
import loop_engine
import loop_event_log
import loop_paro_engine
import loop_revalidation
from checks.flow_unit_runtime_v2 import missing_runtime_issue, validate_native_loop_payload
from loop_gate_processor import process_gate_result


UNIT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}\Z")
TASK_ID = re.compile(r"[A-Z]+-\d+\Z")
REVIEW_ID = re.compile(r"REVIEW-([A-Za-z0-9][A-Za-z0-9_.-]*)-R(\d+)(?:-([A-Z0-9-]+))?\Z")
TIERS = ("setup", "inner", "middle", "outer")


def runtime_path(root):
    return Path(root) / ".governance" / "flow-unit-runtime.json"


def _payload(path):
    if not path.exists():
        if issue := missing_runtime_issue(path):
            raise ValueError(issue)
        return {
            "origin": "native-loop", "schema_version": "2.0",
            "runtime_scope": "loop-engineering-runtime", "runtime_contract": "loop-runtime-contract/v2",
            "workflow_model": "loop-engineering", "contract_source": "loop-runtime-contract-v2",
            "flow_units": [],
        }
    state = json.loads(path.read_text(encoding="utf-8"))
    issues = validate_native_loop_payload(state)
    if issues:
        raise ValueError("; ".join(issues))
    return state


def _unit(state, unit_id):
    for unit in state["flow_units"]:
        if unit["flow_unit_id"] == unit_id:
            return unit
    raise ValueError(f"unknown work unit: {unit_id}")


def _assert_open(unit):
    if unit["runtime_status"] != "active" or unit["gate_state"]["status"] == "passed":
        raise ValueError(f"{unit['flow_unit_id']} is {unit['runtime_status']}, gate {unit['gate_state']['status']}")


def _admit(path, unit):
    if unit["runtime_status"] == "dormant":
        waiting = _unfinished(path.parent.parent, _payload(path), unit)
        if waiting:
            raise ValueError(f"unresolved dependencies: {', '.join(waiting)}")
    if unit["runtime_status"] != "dormant":
        return unit
    unit_id = unit["flow_unit_id"]
    decision = loop_admission.check_admission(unit_id, runtime_file=path, log_path=path.with_name("loop-event-log.jsonl"))
    if not decision.admitted:
        raise ValueError(decision.reason)
    if unit.get("recheck") and unit["loop_state"].get("cas_version") is not None:
        from loop_alignment import activate_recheck
        return activate_recheck(path, unit)
    outcome = loop_paro_engine.activate_unit(unit_id, runtime_file=path, tier=unit["entry_tier"],
                                            fuse_max_rounds=unit["loop_state"]["fuse"]["max_rounds"],
                                            event_log=True, actor="admission")
    if not outcome.success:
        raise ValueError(outcome.reason)
    return outcome.unit


def _validate_gate(gate, tier):
    registry, issues = loop_engine.load_loop_registry()
    if issues:
        raise ValueError("; ".join(issues))
    path = registry["iteration_paths"][tier]
    gate = gate or path[0]
    semantics = loop_engine.get_loop_gate_semantics(gate)
    if not semantics or not (
        gate in path or gate in registry["optional_entry_gates"].get(tier, [])
    ):
        raise ValueError(f"{gate} does not belong to the {tier} loop")
    return gate


def _unfinished(root, state, unit, children=False):
    """Check the exit receipts being consumed, including their prerequisites."""
    from checks.loop_receipts import verify_attempt
    from loop_alignment import acceptance_successors
    units = {u["flow_unit_id"]: u for u in state["flow_units"]}
    successors = acceptance_successors(state["flow_units"])
    child_ids = {}
    for u in units.values():
        child_ids.setdefault(u.get("parent_unit_id"), []).append(u["flow_unit_id"])
    pending = list(unit["dependencies"])
    if children:
        pending.extend(child_ids.get(unit["flow_unit_id"], ()))
    seen = set()
    waiting = set()
    while pending:
        uid = pending.pop()
        if uid in seen:
            continue
        seen.add(uid)
        required = units[uid]
        if required["runtime_status"] != "completed":
            waiting.add(uid)
            continue
        history = required["gate_history"]
        try:
            verify_attempt(Path(root), required, history[-1], len(history) - 1)
            historical = uid == unit.get("continues_contract") and unit.get("previous_evidence_ref") == history[-1]["evidence_ref"]
            if uid == unit.get("continues_scope") or uid in successors:
                historical = True
                if uid not in (unit.get("continues_scope"), unit.get("continues_contract")):
                    pending.extend(successors.get(uid, []))
            if not historical and (issue := loop_revalidation.exit_issue(
                    root, required, loop_revalidation.owner_for(state, required), prerequisites=False)):
                raise ValueError(issue)
        except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
            raise ValueError(f"{uid}: completion evidence unavailable: {exc}") from exc
        pending.extend(required["dependencies"])
        pending.extend(child_ids.get(uid, ()))
    return sorted(waiting)


def _triage_intake(root, task):
    """Read the immutable intake belonging to this task, when it has one."""
    if not TASK_ID.fullmatch(task):
        return {}
    from change_triage import DEMAND_SOURCES, TRIAGE_SCHEMA_VERSION
    from delivery_acceptance import _json_object, _project_path, _regular_stat

    try:
        path = _project_path(Path(root), f".governance/change-triage/{task}.json")
    except FileNotFoundError:
        return {}
    _regular_stat(path)
    record = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_json_object)
    if (not isinstance(record, dict) or record.get("task_id") != task
            or type(record.get("schema_version")) is not int or record["schema_version"] != TRIAGE_SCHEMA_VERSION):
        raise ValueError(f"{path}: incompatible triage record for {task}")
    if not isinstance(record.get("acceptance", ""), str):
        raise ValueError(f"{path}: intake acceptance must be text")
    if "demand_source" in record and record["demand_source"] not in DEMAND_SOURCES:
        raise ValueError(f"{path}: unknown intake demand source")
    basis = record.get("demand_basis", "")
    if not isinstance(basis, str) or (record.get("demand_source") == "user-named" and not basis.strip()):
        raise ValueError(f"{path}: invalid basis for the registered demand")
    return record


def _intake_intent(task, intake, explicit, delivery_goal, goal, enclosing, previous):
    prior_art = intake.get("prior_art", [])
    if not isinstance(prior_art, list) or not all(isinstance(s, str) and s.strip() for s in prior_art):
        raise ValueError(f"invalid prior_art in intake for {task}")
    if explicit is not None:
        if not isinstance(explicit, str) or not explicit.strip():
            raise ValueError("intent must contain the original request")
        if delivery_goal and explicit != goal:
            raise ValueError("intent differs from the bound delivery goal")
        if not enclosing and intake.get("demand_basis"):
            if explicit != intake["demand_basis"]:
                raise ValueError("explicit intent differs from the registered root request")
            source = intake.get("demand_source") or "unspecified"
            return {"basis": explicit, "source": f"change-triage/{task}:{source}", "prior_art": prior_art}
        return {"basis": explicit, "source": "user", "prior_art": prior_art}
    if delivery_goal:
        # bind_delivery_unit supplies the original text from the goal bridge.
        return {"basis": goal, "source": "goal-bridge", "prior_art": prior_art}
    if intake.get("demand_basis") or prior_art:
        basis = intake.get("demand_basis") or f".governance/change-triage/{task}.json"
        source = intake.get("demand_source") or "unspecified"
        return {"basis": basis, "source": f"change-triage/{task}:{source}", "prior_art": prior_art}
    parent_intent = enclosing.get("intent")
    prior_intent = previous.get("intent")
    if parent_intent and prior_intent and parent_intent != prior_intent:
        raise ValueError("parent and previous unit have different intent; provide the applicable --intent")
    return parent_intent or prior_intent


def start(root, *, unit_id, goal, tier, gate=None, acceptance=None, parent=None, task=None,
          dependencies=(), release_version=None, release_reviewer=None, after=None, check_command=None,
          expect_output=None, delivery_goal=None, delivery_contract_sha256=None, dry_run=False,
          intent=None, from_learning=None, criteria=None, scope=(), product_goal=None, authority=None, scope_artifact=None,
          adopt_legacy=None, intent_source=None):
    """Declare exactly one unit. Replaying the same declaration preserves its progress."""
    if not UNIT_ID.fullmatch(unit_id) or (task and not UNIT_ID.fullmatch(task)) or tier not in TIERS:
        raise ValueError("invalid unit id or loop tier")
    requested_gate = gate
    gate = _validate_gate(gate, tier)
    task = task or unit_id
    if from_learning is not None and not after:
        raise ValueError("--from-learning requires --after to identify its source unit")
    path = runtime_path(root)
    with loop_event_log._cross_process_lock(path), loop_paro_engine._commit_lock(path):
        state = _payload(path)
        intake = _triage_intake(root, task)
        previous = _unit(state, after) if after else {}
        continuing_child = previous.get("parent_unit_id") and not from_learning
        if continuing_child:
            from loop_alignment import continue_child
            parent, scope, scope_artifact, gate, acceptance, check_command, expect_output = continue_child(
                previous, parent=parent, scope=scope, candidate=scope_artifact, tier=tier, gate=requested_gate,
                acceptance=acceptance or intake.get("acceptance"), command=check_command, expected=expect_output)
        enclosing = _unit(state, parent) if parent else {}
        if after:
            if previous["runtime_status"] != "completed":
                raise ValueError("the previous iteration must have completed with evidence")
            dependencies = [*dependencies, after]
        if from_learning is not None:
            from loop_learning import opportunity
            selected = opportunity(root, previous, from_learning)
            if ((goal is not None and goal != selected["action"]) or
                    (acceptance is not None and acceptance != selected["validation"])):
                raise ValueError("goal and acceptance must match the selected opportunity")
            if intake.get("acceptance") and intake["acceptance"] != selected["validation"]:
                raise ValueError(f"opportunity validation differs from the registered acceptance for {task}")
            goal, acceptance = selected["action"], selected["validation"]
        else:
            goal = goal or previous.get("goal")
            acceptance = acceptance or intake.get("acceptance") or previous.get("acceptance")
        if not isinstance(goal, str) or not goal.strip() or not isinstance(acceptance, str) or not acceptance.strip():
            raise ValueError("a goal and verifiable acceptance condition are required")
        if release_version and (tier != "middle" or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", release_version)):
            raise ValueError("release certification requires a middle unit and X.Y.Z version")
        if release_reviewer and not release_version:
            raise ValueError("a release reviewer requires a versioned release unit")
        if release_version:
            release_reviewer = release_reviewer or "Release Reviewer"
        if check_command is not None or expect_output is not None:
            if (tier != "inner" or gate != "G6" or not isinstance(check_command, list) or not check_command
                    or not all(isinstance(a, str) and a for a in check_command)
                    or not isinstance(expect_output, str) or not expect_output.strip()):
                raise ValueError("command acceptance requires inner/G6, a JSON argument array and expected output")
        delivery_hash = None
        if delivery_goal:
            from delivery_acceptance import contract_for_goal
            if delivery_goal != task or gate != "G9" or release_version:
                raise ValueError("goal acceptance requires its own G9 delivery unit")
            delivery_hash = contract_for_goal(Path(root), delivery_goal)["contract_sha256"]
        if delivery_contract_sha256 and delivery_hash != delivery_contract_sha256:
            raise ValueError("the original goal contract changed during intake")
        definition = {
            "flow_unit_id": unit_id, "goal": goal, "acceptance": acceptance,
            "parent_unit_id": parent, "task_id": task,
            "dependencies": list(dict.fromkeys(dependencies)),
            "release_version": release_version, "release_reviewer": release_reviewer, "previous_unit_id": after,
            "acceptance_command": check_command, "expected_output": expect_output,
            "delivery_goal": delivery_goal, "delivery_contract_sha256": delivery_hash,
        }
        if after:
            definition["previous_evidence_ref"] = previous["gate_history"][-1]["evidence_ref"]
        if continuing_child:
            definition["continues_scope"] = after
        if from_learning is not None:
            definition["source_learning"] = from_learning
        context = _intake_intent(task, intake, intent, delivery_goal, goal, enclosing, previous)
        from loop_alignment import declaration
        if product_goal and (tier != "middle" or (delivery_goal and product_goal != delivery_goal)):
            raise ValueError("a product contract requires its own middle delivery or release")
        if criteria and not (product_goal or delivery_goal):
            product_goal = unit_id
            if tier != "middle":
                raise ValueError("a multi-criterion product requires a middle delivery")
        existing_unit = next((u for u in state["flow_units"] if u["flow_unit_id"] == unit_id), {})
        if previous and not parent and not from_learning and previous.get("product_goal"):
            following = next((u["flow_unit_id"] for u in state["flow_units"]
                              if u.get("continues_contract") == after and u["flow_unit_id"] != unit_id), None)
            if following:
                raise ValueError(f"{after} already continues in {following}; resume that product unit")
            owner = loop_revalidation.owner_for(state, previous)
            frozen = owner["root_contract"]
            if (tier != "middle" or product_goal not in (None, previous["product_goal"])
                    or criteria not in (None, loop_revalidation.current_criteria(owner))
                    or acceptance != previous["acceptance"] or intent not in (None, frozen["intent"])
                    or authority not in (None, frozen.get("authority")) or scope or scope_artifact):
                raise ValueError("continue the frozen product contract or explicitly start a separately authorized goal")
            definition.update(continues_contract=after, product_goal=previous["product_goal"],
                              product_contract_sha256=previous["product_contract_sha256"])
        elif (not existing_unit or any(k in existing_unit for k in ("root_contract", "criterion_scope"))
                or criteria is not None or scope or product_goal or authority or scope_artifact or adopt_legacy or intent_source):
            definition.update(declaration(root, definition, context, intake, criteria, scope, enclosing,
                              {u["flow_unit_id"]: u for u in state["flow_units"]}, product_goal or delivery_goal, authority, scope_artifact))
        if adopt_legacy or intent_source:
            from loop_alignment import adopt
            adopt(root, definition, _unit(state, adopt_legacy), intent, intent_source)
        for existing in state["flow_units"]:
            if existing["flow_unit_id"].casefold() == unit_id.casefold():
                if (any(existing.get(k) != v for k, v in definition.items())
                        or existing.get("source_learning") != from_learning
                        or (("intent" in existing or intent is not None) and existing.get("intent") != context)
                        or existing.get("entry_gate") != gate or existing.get("entry_tier") != tier):
                    raise ValueError(f"unit {unit_id} already exists with a different contract")
                if after:
                    _unfinished(root, state, existing)
                return existing
        if context:
            definition["intent"] = context
        if parent:
            _assert_open(enclosing)
            ranks = {"outer": 2, "middle": 1, "inner": 0}
            parent_tier = enclosing["loop_state"]["active_loop_tier"]
            if (tier != parent_tier and
                    (tier == "setup" or parent_tier == "setup" or ranks[tier] > ranks[parent_tier])):
                raise ValueError(f"{tier} cannot be nested in {parent_tier}")
        if gate == "G1" and (parent or any(u["entry_gate"] == "G1" for u in state["flow_units"])):
            raise ValueError("G1 is the one-time initiation decision")
        for dependency in definition["dependencies"]:
            _unit(state, dependency)
        unit = loop_engine.activate_loop_state({
            **definition, "entry_gate": gate, "entry_tier": tier,
            "blockers": [], "runtime_status": "active",
            "gate_state": {"gate_id": gate, "status": "pending", "last_result": None, "evidence_refs": []},
        }, tier)
        if unit["loop_state"]["fuse"]["tripped"]:
            raise ValueError(f"missing {tier} loop policy")
        budget = loop_admission.check_wip_budget(tier, runtime_file=path, unit_id=unit_id, enclosing_unit=parent)
        waiting = _unfinished(root, state, unit)
        if waiting or not budget.admitted:
            unit["runtime_status"] = "dormant"
            unit["loop_state"]["active_loop"] = False
        else:
            unit["loop_state"]["cas_version"] = 0
        state["flow_units"].append(unit)
        issues = validate_native_loop_payload(state)
        if issues:
            raise ValueError("; ".join(issues))
        if dry_run:
            return unit
        loop_paro_engine._atomic_replace_bytes(path, loop_paro_engine._serialize(state))
        if unit["runtime_status"] == "dormant":
            return unit
        event = loop_event_log.build_event(unit_id, "phase_enter", cas_version=0, from_version=None,
                                          actor="intake", to_phase="plan", tier=tier, gate_id=gate)
        loop_event_log.append_event(event, log_path=path.with_name("loop-event-log.jsonl"))
        return unit


def release_issues(root, unit_id, version):
    try:
        state = _payload(runtime_path(root))
        units = [unit for unit in state["flow_units"] if unit["gate_state"]["gate_id"] == "G9"
                 and unit.get("release_version") == version and version
                 and (not unit_id or unit["flow_unit_id"] == unit_id)]
        if len(units) != 1:
            return ["release requires one G9 work unit bound to this version"]
        unit = units[0]
        if unit["runtime_status"] != "completed" or unit["gate_state"]["status"] != "passed" or not unit["gate_state"]["evidence_refs"]:
            return [f"{unit['flow_unit_id']}: release review for {version} is pending"]
        if waiting := _unfinished(root, state, unit, children=True):
            return [f"unresolved release work: {', '.join(waiting)}"]
        if issue := loop_revalidation.exit_issue(root, unit, loop_revalidation.owner_for(state, unit)):
            return [issue]
        ref = unit["gate_state"]["evidence_refs"][-1]
        rid = "REVIEW-" + ref.removeprefix("review-").removesuffix(".md")
        slug = re.search(r"(-R[0-9]+)-(.+)$", rid)
        if slug:
            rid = rid[:slug.start(2)] + slug.group(2).upper()
        _, binding, receipt = _review_receipt(root, unit, "G9", rid)
        if (binding.get("release_version") != version or receipt["reviewer"] != binding.get("release_reviewer")
                or binding.get("release_reviewer") != unit.get("release_reviewer")):
            return ["release needs its designated reviewer and exact candidate version"]
        if receipt["verdict"] not in ("APPROVED", "APPROVED_WITH_NOTES"):
            return ["release review did not approve this version"]
        return []
    except (ValueError, OSError, TypeError, KeyError) as exc:
        return [str(exc)]


def add_arguments(parser):
    actions = parser.add_subparsers(dest="action", required=True)
    new = actions.add_parser("start", help="Open one goal and its acceptance condition")
    new.add_argument("--unit", required=True)
    new.add_argument("--goal", help="Defaults to the previous unit goal with --after")
    new.add_argument("--intent", help="Exact original user request that this unit serves")
    new.add_argument("--authority", help="Project-designated person authorized to revise the root intent")
    new.add_argument("--adopt-legacy", help="Reference an older unit while opening a separate newly confirmed root")
    new.add_argument("--intent-source", help="Project-relative original response confirming the newly adopted intent")
    new.add_argument("--acceptance", help="Defaults to registered task acceptance")
    new.add_argument("--product-goal", help="Verify this ordinary delivery or release against the named project product contract")
    new.add_argument("--criteria", type=json.loads, help="Frozen product criteria as a JSON map, matching the named product contract")
    new.add_argument("--criterion", dest="scope", action="append", default=[], help="Root criterion served by a child")
    new.add_argument("--candidate", dest="scope_artifact", help="Specific component checked by a scoped child")
    new.add_argument("--tier", required=True, choices=TIERS)
    new.add_argument("--gate", help="Defaults to the entry condition of the selected loop tier")
    new.add_argument("--after", help="Continue from a completed unit and its acceptance")
    new.add_argument("--from-learning", help="Use this opportunity from --after as the new goal and acceptance")
    new.add_argument("--check-command", type=json.loads, help="JSON argument array for a scoped inner-loop acceptance")
    new.add_argument("--expect-output", help="Exact UTF-8 stdout (LF/CRLF equivalent; one final newline optional)")
    new.add_argument("--parent")
    new.add_argument("--task")
    new.add_argument("--depends-on", action="append", default=[])
    new.add_argument("--release-reviewer", help="Identified release signatory (defaults to Release Reviewer)")
    new.add_argument("--release-version", help="Version certified by a release work unit")
    learn = actions.add_parser("learn", help="Record an observed decision or a proposed follow-up")
    learn.add_argument("--unit", required=True)
    learn.add_argument("--id", dest="learning_id", required=True)
    learn.add_argument("--kind", choices=("decision", "opportunity", "note"), required=True)
    learn.add_argument("--observation", required=True, help="What the evidence showed")
    learn.add_argument("--action", dest="action_text", required=True, help="The chosen approach or proposed next goal")
    learn.add_argument("--validation", required=True, help="How to check the result")
    learn.add_argument("--evidence", required=True, help="Project-relative file supporting this observation")
    learn.add_argument("--criterion", action="append", default=[], help="Criterion to recheck against the chosen candidate")
    learn.add_argument("--candidate", help="Project-relative artifact evaluated by the next acceptance receipt")
    learn.add_argument("--supersedes", help="ID of the previous selected candidate for the same criteria")
    revision = actions.add_parser("revise", help="Import scoped counterevidence or a recorded authorization")
    revision.add_argument("--unit", required=True)
    revision.add_argument("--evidence", required=True)
    revision.add_argument("--decision", help="Registered decision approving the exact revision evidence digest")
    recheck = actions.add_parser("recheck", help="Reopen a previously certified unit whose current acceptance is stale")
    recheck.add_argument("--unit", required=True)
    bind = actions.add_parser("bind-product", help="Bind a product whose root criteria were registered before the artifact existed")
    bind.add_argument("--unit", required=True)
    reopen = actions.add_parser("resume", help="Resume rework after a documented blocker resolution")
    reopen.add_argument("--unit", required=True)
    reopen.add_argument("--evidence", required=True, help="Project-relative resolution evidence file")
    reopen.add_argument("--actor", required=True, help="Person or executor recording the resolution")
    verify = actions.add_parser("verify", help="Run the predeclared acceptance check from the project root")
    verify.add_argument("--unit", required=True)
    accept = actions.add_parser("accept", help="Apply the independent product receipt to an ordinary delivery")
    accept.add_argument("--unit", required=True)
    read = actions.add_parser("status", help="Resume from current results and evidence")
    read.add_argument("--unit")
    read.add_argument("--json", action="store_true")
    phase = actions.add_parser("step", help="Record an executor observation")
    phase.add_argument("--unit", required=True)
    phase.add_argument("--phase", required=True, choices=("act", "observe", "reflect"))
    check = actions.add_parser("gate", help="Apply the recorded review to its work unit")
    check.add_argument("--unit", required=True)
    check.add_argument("--gate", required=True)
    check.add_argument("--review", required=True)


def run(root, args):
    if args.action == "start":
        return start(root, unit_id=args.unit, goal=args.goal, tier=args.tier, gate=args.gate,
                     acceptance=args.acceptance, parent=args.parent, task=args.task,
                     dependencies=args.depends_on, release_version=args.release_version, after=args.after,
                     intent=args.intent, from_learning=args.from_learning,
                     criteria=args.criteria, scope=args.scope, product_goal=args.product_goal, authority=args.authority,
                     scope_artifact=args.scope_artifact, adopt_legacy=args.adopt_legacy, intent_source=args.intent_source,
                     check_command=args.check_command, expect_output=args.expect_output, release_reviewer=args.release_reviewer)
    if args.action == "learn":
        from loop_learning import record
        return record(root, args.unit, args.learning_id, args.kind, args.observation,
                      args.action_text, args.validation, args.evidence,
                      criteria=args.criterion, candidate=args.candidate, supersedes=args.supersedes)
    if args.action == "revise":
        from loop_alignment import revise
        return revise(root, args.unit, args.evidence, args.decision)
    if args.action == "recheck":
        from loop_alignment import recheck
        return recheck(root, args.unit)
    if args.action == "bind-product":
        from loop_alignment import bind_product
        return bind_product(root, args.unit)
    if args.action == "resume":
        return resume(root, args.unit, args.evidence, args.actor)
    if args.action == "verify":
        return verify_command(root, args.unit)
    if args.action == "accept":
        return accept_delivery(root, args.unit, ordinary_only=True)
    if args.action == "step":
        return step(root, args.unit, args.phase)
    if args.action == "gate":
        return gate_review(root, args.unit, args.gate, args.review)
    from governance_readers import loop_state
    report = loop_state(root)
    if args.unit:
        for unit in report["units"]:
            if unit["flow_unit_id"] == args.unit:
                return unit
        raise ValueError(report.get("message") or f"unknown work unit: {args.unit}")
    return report


def step(root, unit_id, phase):
    path = runtime_path(root)
    with loop_event_log._cross_process_lock(path):
        state = _payload(path)
        unit = _admit(path, _unit(state, unit_id))
        _assert_open(unit)
        if waiting := _unfinished(root, state, unit):
            raise ValueError(f"unresolved dependencies: {', '.join(waiting)}")
        if unit["loop_state"]["agent_phase"] == phase:
            return unit
        if phase not in ("act", "observe", "reflect"):
            raise ValueError("step requires act, observe or reflect")
        transition = loop_paro_engine.apply_transition(unit_id, phase, runtime_file=path,
                                                       event_log=True, actor="executor")
        if not transition.success:
            raise ValueError(transition.reason)
        return transition.unit


def review_binding(root, task, unit_id=None, gate=None, *, allowed_gates=None):
    """Select a real unit and capture its iteration before recording a review."""
    state = _payload(runtime_path(root))
    candidates = [u for u in state["flow_units"] if u["task_id"] == task
                  and (not unit_id or u["flow_unit_id"] == unit_id)
                  and (not gate or u["gate_state"]["gate_id"] == gate)
                  and (allowed_gates is None or u["gate_state"]["gate_id"] in allowed_gates)
                  and u["runtime_status"] in ("active", "dormant")]
    if len(candidates) != 1:
        raise ValueError(f"{task}: expected one matching open work unit, found {len(candidates)}")
    path = runtime_path(root)
    with loop_event_log._cross_process_lock(path):
        unit = _admit(path, _unit(_payload(path), candidates[0]["flow_unit_id"]))
    _assert_open(unit)
    binding = {"unit": unit["flow_unit_id"], "gate": unit["gate_state"]["gate_id"],
            "iteration": unit["loop_state"]["loop_count"], "attempt": len(unit.get("gate_history", []))}
    if binding["gate"] == "G9" and unit.get("release_version"):
        binding.update(release_version=unit["release_version"], release_reviewer=unit["release_reviewer"])
    if binding["gate"] in ("G6", "G7", "G9", "G11") and (not unit.get("product_goal") or binding["gate"] == "G9"):
        product = (loop_revalidation.product_result(root, unit)
                   if unit.get("product_goal") and binding["gate"] == "G9" else None)
        proof = loop_revalidation.snapshot(root, unit, loop_revalidation.owner_for(state, unit), product=product)
        if proof:
            binding["outcome_check"] = proof
    return binding


def _review_receipt(root, unit, gate, review_id, *, published=False, ledger=None):
    """Match the machine record to its committed review transaction and pinned report."""
    from authority_ledger import LedgerWriter
    from review_record import verify_review_trust
    match = REVIEW_ID.fullmatch(review_id)
    if not match:
        raise ValueError("expected a recorded review id")
    task, rnd, slug = match.groups()
    if task != unit["task_id"]:
        raise ValueError("review does not belong to the requested task")
    name = f"review-{task}-R{rnd}" + (f"-{slug.lower()}" if slug else "") + ".md"
    evidence_dir = runtime_path(root).parent
    review = evidence_dir / name
    text = review.read_text(encoding="utf-8")
    fields = dict(re.findall(r"^- ([a-z_0-9]+): (.+)$", text, re.MULTILINE))
    verdict = re.search(r"^\*\*审查结论\*\*: \*\*([A-Z_]+)\*\*$", text, re.MULTILINE)
    writer = ledger if ledger is not None else LedgerWriter(evidence_dir)
    if not writer.integrity["ok"]:
        raise ValueError("review ledger integrity failure")
    receipts = [r for r in writer.state["reviews"] if r.get("review_id") == review_id]
    if len(receipts) != 1 or not verdict:
        raise ValueError("expected one machine-recorded ledger review and verdict")
    receipt = receipts[0]
    binding = receipt.get("loop_binding", {})
    expected = {"unit": unit["flow_unit_id"], "gate": gate, "task": task, "round": f"R{rnd}",
                "report": receipt["report_path"], "report_sha256": receipt["report_sha256"],
                "snapshot_commit": receipt["commit"], "snapshot_worktree": receipt["worktree"],
                "reviewer": receipt["reviewer"], "iteration": str(binding.get("iteration")),
                "attempt": str(binding.get("attempt"))}
    if (any(fields.get(k) != v for k, v in expected.items()) or
            binding.get("unit") != unit["flow_unit_id"] or binding.get("gate") != gate or
            receipt["verdict"] != verdict.group(1) or receipt["task_id"] != task):
        raise ValueError("review scope, evidence or verdict disagrees with its ledger transaction")
    if fields.get("snapshot_tree") != receipt.get("tree"):
        raise ValueError("review tree differs from its ledger transaction")
    expected_pins = {(b["path"], b["hash"]) for b in receipt.get("bindings", [])}
    actual_pins = set(re.findall(r"^- snapshot_bind: (.+)=([^=\s]+)$", text, re.MULTILINE))
    if actual_pins != expected_pins:
        raise ValueError("review snapshot file bindings disagree with ledger")
    trust = verify_review_trust(review, repo_root=root, current_worktree=not published)
    if trust["verdict"] != "CLEAN":
        raise ValueError(f"review evidence {trust['verdict']}: {trust['reason']}")
    return name, binding, receipt


def gate_review(root, unit_id, gate, review_id):
    """Consume a verified, scoped review once, including after a retry or restart."""
    path = runtime_path(root)
    with loop_event_log._cross_process_lock(path):
        state = _payload(path)
        unit = _unit(state, unit_id)
        name, binding, receipt = _review_receipt(root, unit, gate, review_id)
        history = unit.get("gate_history", [])
        for entry in history:
            if entry["evidence_ref"] == name:
                return {"wired": True, "replayed": True, "review": review_id, "unit": unit_id,
                        "gate": gate, "decision": entry["decision"], "reason": entry.get("reason"),
                        "gate_status": unit["gate_state"]["status"]}
        _assert_open(unit)
        if (gate != unit["gate_state"]["gate_id"] or binding.get("attempt") != len(history) or
                binding.get("iteration") != unit["loop_state"]["loop_count"]):
            raise ValueError("review belongs to another gate or iteration")
        if (unit.get("delivery_goal") and gate == "G9") or unit.get("acceptance_command"):
            raise ValueError("this unit requires its declared acceptance evidence")
        result = receipt["verdict"]
        if result in ("APPROVED", "APPROVED_WITH_NOTES"):
            if waiting := _unfinished(root, state, unit, children=loop_engine.gate_requires_children(gate)):
                raise ValueError(f"unresolved child work or dependency: {', '.join(waiting)}")
            if gate in ("G6", "G7", "G9", "G11") and (not unit.get("product_goal") or gate == "G9"):
                product = loop_revalidation.product_result(root, unit) if gate == "G9" and unit.get("product_goal") else None
                if product and not product["pass"]:
                    raise ValueError("product acceptance requires repair: " + ", ".join(product["issues"]))
                proof = loop_revalidation.snapshot(root, unit, loop_revalidation.owner_for(state, unit), product=product)
                if proof != binding.get("outcome_check"):
                    raise ValueError("the reviewed scope, candidate or current receipt changed; obtain a new review")
                if proof and not product:
                    pins = {pin["path"] for pin in receipt.get("bindings", []) if pin.get("hash") != "unavailable"}
                    required_pins = set(proof["candidates"])
                    if pin := proof.get("scoped_artifact"):
                        required_pins.add(pin["path"])
                    if not required_pins <= pins:
                        raise ValueError("bind the reviewed candidate using review-record --bind-file")
        elif result not in ("NEEDS_CHANGE", "BLOCKED"):
            raise ValueError(f"{result} does not certify a gate decision")
        return _apply_receipt(path, unit, result, name, receipt["reviewer"])


def _apply_receipt(path, unit, result, name, actor):
    unit_id = unit["flow_unit_id"]
    gate = unit["gate_state"]["gate_id"]
    phases = ("plan", "act", "observe", "reflect")
    phase = unit["loop_state"]["agent_phase"]
    for next_phase in phases[phases.index(phase) + 1:]:
        transition = loop_paro_engine.apply_transition(
            unit_id, next_phase, {"evidence_ref": name}, runtime_file=path, event_log=True, actor=actor)
        if not transition.success:
            raise ValueError(transition.reason)
    outcome = process_gate_result(unit_id, gate, result, actor=actor, evidence_ref=name,
                                  runtime_file=path, event_log=True, verified_native_review=True)
    if not outcome.success:
        raise ValueError(outcome.reason)
    return {"wired": True, "unit": unit_id, "gate": gate, "decision": outcome.decision,
            "status": outcome.status, "reason": outcome.reason, "loop_count": outcome.new_loop_count}


def resume(root, unit_id, evidence, actor):
    """Reopen the same gate for rework without certifying its acceptance."""
    from delivery_acceptance import _project_path, _hash_file
    if not actor.strip():
        raise ValueError("a resolution requires an identified actor")
    path = runtime_path(root)
    with loop_event_log._cross_process_lock(path), loop_paro_engine._commit_lock(path):
        state = _payload(path)
        unit = _unit(state, unit_id)
        evidence_path = _project_path(Path(root), evidence)
        digest = _hash_file(evidence_path, nonempty=True)
        resolution = {"evidence": evidence, "sha256": digest, "actor": actor}
        if unit["runtime_status"] != "blocked":
            prior = unit.get("resolution")
            if prior == resolution and unit["runtime_status"] == "active":
                return unit
            raise ValueError("only a blocked unit can resume from a resolution")
        admission = loop_admission.check_admission(unit_id, runtime_file=path)
        if not admission.admitted:
            raise ValueError(admission.reason)
        loop = unit["loop_state"]
        version = loop["cas_version"]
        loop.update(active_loop=True, agent_phase="plan", cas_version=version + 1, loop_count=0)
        loop["fuse"]["tripped"] = False
        unit.update(runtime_status="active", resolution=resolution)
        unit["gate_state"]["status"] = "pending"
        loop_paro_engine._atomic_replace_bytes(path, loop_paro_engine._serialize(state))
        event = loop_event_log.build_event(unit_id, "phase_enter", cas_version=version + 1, from_version=version,
                                          actor=actor, to_phase="plan", evidence_ref=evidence, payload=resolution)
        loop_event_log.append_event(event, log_path=path.with_name("loop-event-log.jsonl"))
        return unit


def _observation(path, unit, data):
    data = {**data, "unit": unit["flow_unit_id"], "gate": unit["gate_state"]["gate_id"],
            "iteration": unit["loop_state"]["loop_count"], "attempt": len(unit.get("gate_history", []))}
    raw = loop_paro_engine._serialize(data)
    digest = hashlib.sha256(raw).hexdigest()
    name = f"loop-evidence/{digest}.json"
    loop_paro_engine._atomic_replace_bytes(path.parent / name, raw)
    return name


def verify_command(root, unit_id):
    from checks.loop_receipts import command_observation_passes

    path = runtime_path(root)
    with loop_event_log._cross_process_lock(path):
        state = _payload(path)
        unit = _admit(path, _unit(state, unit_id))
        _assert_open(unit)
        command = unit.get("acceptance_command")
        if not command:
            raise ValueError("this unit has no declared executable acceptance")
        if waiting := _unfinished(root, state, unit, children=True):
            raise ValueError(f"unresolved work: {', '.join(waiting)}")
        attempt = len(unit.get("gate_history", []))
        proof = loop_revalidation.snapshot(root, unit, loop_revalidation.owner_for(state, unit))
    # Execute outside the project transaction lock; independent units remain usable.
    try:
        run = subprocess.run(command, cwd=root, shell=False, capture_output=True, timeout=120)
        observation = {"command": command, "returncode": run.returncode, "stderr": run.stderr.decode("utf-8", errors="replace")}
        try:
            observation["stdout"] = run.stdout.decode("utf-8")
        except UnicodeDecodeError as exc:
            observation["error"] = f"stdout is not valid UTF-8: {exc}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        observation = {"command": command, "error": str(exc)}
    observation["expected_output"] = unit["expected_output"]
    with loop_event_log._cross_process_lock(path):
        state = _payload(path)
        unit = _admit(path, _unit(state, unit_id))
        _assert_open(unit)
        if attempt != len(unit.get("gate_history", [])) or _unfinished(root, state, unit, children=True):
            raise ValueError("work changed during acceptance; repeat the check on the current attempt")
        if proof != loop_revalidation.snapshot(root, unit, loop_revalidation.owner_for(state, unit)):
            raise ValueError("candidate or scope changed during acceptance; rerun the declared check")
        if proof:
            observation["outcome_check"] = proof
        receipt = _observation(path, unit, observation)
        result = "APPROVED" if command_observation_passes(observation) else "NEEDS_CHANGE"
        return _apply_receipt(path, unit, result, receipt, "acceptance-command")


def accept_delivery(root, unit_id, *, ordinary_only=False):
    """Apply witnessed product acceptance and route failures back to the responsible loop."""
    from checks.loop_receipts import verify_attempt
    from delivery_acceptance import evaluate_delivery_acceptance
    path = runtime_path(root)
    with loop_event_log._cross_process_lock(path):
        while True:
            state = _payload(path)
            unit = _admit(path, _unit(state, unit_id))
            gate = unit["gate_state"]["gate_id"]
            if ordinary_only and unit.get("delivery_goal"):
                raise ValueError("bound goals must use their authorized host acceptance action")
            if not (unit.get("product_goal") or unit.get("delivery_goal")):
                raise ValueError("unit is not bound to a delivery goal")
            if gate not in ("G6", "G7", "G9"):
                raise ValueError(f"{unit_id}: product is registered; complete the current {gate} review first. "
                                 f"Use loop status --unit {unit_id} --json to see the next action.")
            result = (loop_revalidation.product_result(root, unit) if unit.get("product_goal") else
                      evaluate_delivery_acceptance(Path(root), goal_id=unit["delivery_goal"], required=True))
            verdict = result.get("receipt_verdict")
            if unit.get("release_version") and gate == "G9" and verdict == "PASS":
                raise ValueError("a release requires its independent designated review")
            if verdict not in ("PASS", "FAIL") or result.get("contract_sha256") != (
                    unit.get("product_contract_sha256") or unit.get("delivery_contract_sha256")):
                raise ValueError("delivery acceptance: " + ", ".join(result["issues"] or ["goal contract changed"]))
            if proof := loop_revalidation.snapshot(root, unit, loop_revalidation.owner_for(state, unit), product=result):
                result["outcome_check"] = proof
            history = unit.get("gate_history", [])
            for attempt, prior in reversed(list(enumerate(history))):
                if prior["actor"] != "delivery-acceptance":
                    continue
                verify_attempt(Path(root), unit, prior, attempt)
                evidence = json.loads((path.parent / prior["evidence_ref"]).read_bytes())
                if evidence["receipt_sha256"] == result["receipt_sha256"] and (
                    verdict == "FAIL" or unit["runtime_status"] == "completed"
                ):
                    return {"unit": unit_id, "gate": prior["gate"], "decision": prior["decision"], "replayed": True}
            _assert_open(unit)
            if verdict == "PASS" and (waiting := _unfinished(root, state, unit, children=True)):
                raise ValueError(f"unresolved work: {', '.join(waiting)}")
            receipt = _observation(path, unit, result)
            outcome = _apply_receipt(path, unit, "APPROVED" if verdict == "PASS" else "NEEDS_CHANGE",
                                     receipt, "delivery-acceptance")
            if outcome["decision"] != "advance":
                return outcome
            # A verified repair returns to its saved gate. Check the independent
            # product bytes and evidence again in that gate's own scope.
