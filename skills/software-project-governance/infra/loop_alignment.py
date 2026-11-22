"""Original task acceptance, local scope and evidenced changes to a root contract."""

import hashlib
import json
import re
from pathlib import Path

from delivery_acceptance import _contract, _hash_file, _json_object, _project_path, CONTRACT


ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}\Z")


def criteria_ok(value):
    return isinstance(value, dict) and bool(value) and all(
        isinstance(key, str) and ID.fullmatch(key) and isinstance(label, str) and label.strip()
        for key, label in value.items())


def root_unit(unit, by_id):
    while source := (unit.get("parent_unit_id") or unit.get("continues_contract")):
        unit = by_id[source]
    return unit


def current_criteria(unit):
    criteria = dict(unit["root_contract"]["criteria"])
    for event in unit.get("contract_revisions", []):
        if event["kind"] == "authorization":
            criteria.update(event["criteria"])
    return criteria


def declaration(root, definition, context, intake, criteria, scope, enclosing, by_id, product_goal, authority, scope_artifact):
    """Freeze a new root or scope a child. Historical declarations are not rewritten."""
    uid = definition["flow_unit_id"]
    if enclosing:
        if criteria is not None or product_goal or authority:
            raise ValueError("declare product criteria on the root and use --criterion on its child")
        owner = root_unit(enclosing, by_id)
        if scope and ("root_contract" not in owner or not set(scope) <= current_criteria(owner).keys()):
            raise ValueError("child scope must name existing root criteria")
        fields = {"criterion_scope": sorted(set(scope))} if scope else {}
        if scope_artifact:
            if not scope:
                raise ValueError("a scoped candidate requires --criterion")
            from delivery_acceptance import _project_path_parts
            _project_path_parts(scope_artifact)
            fields["scope_artifact"] = scope_artifact
        return fields
    if scope or scope_artifact:
        raise ValueError("declare root criteria with --criteria, or set --criterion on a child")
    if product_goal:
        if definition.get("release_version") and definition.get("delivery_goal"):
            raise ValueError("a bound delivery and a release have different exits")
        try:
            contract_path = _project_path(Path(root), CONTRACT)
        except FileNotFoundError:
            if not criteria_ok(criteria):
                raise ValueError(f"create {CONTRACT} or register named criteria with --criteria before binding the product")
            contract_path = None
        contract, digest = (_contract(contract_path) if contract_path is not None else
                            (dict(goal_id=product_goal, release_version=definition.get("release_version"),
                                  criteria=criteria), None))
        if (contract["goal_id"] != product_goal or
                definition.get("release_version") not in (None, contract["release_version"])):
            raise ValueError("product acceptance contract belongs to another goal or release")
        if criteria is not None and criteria != contract["criteria"]:
            raise ValueError("root criteria must match the product's frozen criteria")
        criteria = contract["criteria"]
        if authority and contract.get("authority") and authority != contract["authority"]:
            raise ValueError("revision authority differs from the original product contract")
        authority = authority or contract.get("authority")
    if criteria is not None and not criteria_ok(criteria):
        raise ValueError("criteria must map stable criterion IDs to nonempty acceptance conditions")
    acceptance = intake.get("acceptance") or definition["acceptance"]
    if intake.get("acceptance") and definition["acceptance"] != acceptance:
        raise ValueError("registered root acceptance cannot be replaced by a local check; create a child unit")
    source = context or {"basis": definition["goal"], "source": "unit-goal"}
    fields = {"root_contract": {
        "unit": uid, "intent": source["basis"], "source": source["source"],
        "acceptance": acceptance, "criteria": criteria or {"acceptance": acceptance},
    }}
    if product_goal:
        fields.update(product_goal=product_goal, product_contract_sha256=digest)
    if authority is not None:
        if not isinstance(authority, str) or not authority.strip():
            raise ValueError("revision authority must name the user or project-designated decision maker")
        fields["root_contract"]["authority"] = authority
    return fields


def view(owner):
    frozen = owner.get("root_contract")
    if not frozen:
        return None
    revisions = owner.get("contract_revisions", [])
    return dict(frozen, criteria=current_criteria(owner), original_criteria=frozen["criteria"],
                revision=len(revisions), revisions=revisions, provenance="project-recorded source")


def adopt(root, declaration, previous, intent, source):
    if (previous.get("root_contract") or previous.get("continues_contract") or not source or not intent
            or "root_contract" not in declaration):
        raise ValueError("adoption requires a separate new root, an older unit, explicit user intent and --intent-source")
    path = _project_path(Path(root), source)
    digest = _hash_file(path, nonempty=True)
    if intent not in path.read_text(encoding="utf-8"):
        raise ValueError("the stated intent must occur in the supplied source")
    declaration["root_contract"].update(adopted_from=previous["flow_unit_id"], source_evidence=source,
                                        source_sha256=digest, source="confirmed at adoption")


def product_context(root, goal, digest, artifact, *, release=False, prerequisites=True):
    """Discover amendments to this exact product when a host uses a preflight directly."""
    from loop_workflow import _payload, runtime_path
    path = runtime_path(root)
    if not path.is_file():
        return None
    units = _payload(path)["flow_units"]
    owners = [u for u in units if u.get("product_goal") == goal and u.get("root_contract")]
    matching = [u for u in owners if u.get("product_contract_sha256") == digest]
    if not matching and any(release or u.get("contract_revisions") or u.get("product_contract_sha256") is None
                            for u in owners):
        raise ValueError("current product contract digest differs from the amended root")
    contexts = [u for u in matching if u.get("contract_revisions")]
    if len(contexts) > 1:
        raise ValueError("multiple amended roots claim the current product contract")
    if matching:
        from loop_revalidation import active_decisions, selected_candidate_issue
        from loop_workflow import _unfinished
        by_id = {unit["flow_unit_id"]: unit for unit in units}
        owner_ids = {unit["flow_unit_id"] for unit in matching}
        historical = acceptance_successors(units)
        for uid, following in historical.items():
            if (len(following) > 1 and by_id[uid].get("product_goal")
                    and root_unit(by_id[uid], by_id)["flow_unit_id"] in owner_ids):
                raise ValueError(f"{uid}: ambiguous product continuations")
        for unit in units:
            owner = root_unit(unit, by_id)
            if unit["flow_unit_id"] not in historical and owner["flow_unit_id"] in owner_ids:
                child = bool(unit.get("parent_unit_id"))
                if issue := selected_candidate_issue(root, unit, product_artifact=None if child else artifact):
                    raise ValueError(issue)
                # A continuation replaces a route only through its own explicit
                # selection. Merely opening another unit cannot discard a pin.
                covered = {key for entry in active_decisions(unit) for key in entry["criteria"]}
                predecessor = unit
                while previous := predecessor.get("continues_contract"):
                    predecessor = by_id[previous]
                    inherited = [entry for entry in active_decisions(predecessor)
                                 if not set(entry["criteria"]) <= covered]
                    if issue := selected_candidate_issue(root, predecessor, product_artifact=artifact, decisions=inherited):
                        raise ValueError(issue)
                    covered.update(key for entry in active_decisions(predecessor) for key in entry["criteria"])
                # The same iterative prerequisite walk is used by native acceptance.
                # Only product frontiers start it; their dependencies include history.
                if prerequisites and not child:
                    if waiting := _unfinished(root, {"flow_units": units}, unit, children=True):
                        raise ValueError(f"unresolved work: {', '.join(waiting)}")
    return contexts[0] if contexts else None


def continue_child(previous, *, parent, scope, candidate, tier, gate, acceptance, command, expected):
    """Carry the child's verifier as well as its place within the root delivery."""
    requested = dict(parent_unit_id=parent, criterion_scope=sorted(set(scope)) if scope else None,
                     scope_artifact=candidate, entry_tier=tier, entry_gate=gate, acceptance=acceptance,
                     acceptance_command=command, expected_output=expected)
    if any(value is not None and value != previous.get(key) for key, value in requested.items()):
        raise ValueError("a child continuation must retain its parent, criterion scope, candidate and acceptance operation")
    return (previous["parent_unit_id"], previous.get("criterion_scope", []), previous.get("scope_artifact"),
            previous["entry_gate"], previous["acceptance"], previous.get("acceptance_command"), previous.get("expected_output"))


def scope_successors(units):
    successors = {}
    for unit in units:
        if previous := unit.get("continues_scope"):
            successors.setdefault(previous, []).append(unit["flow_unit_id"])
    return successors


def acceptance_successors(units):
    """Historical observations remain signed; only lineage frontiers select today's route."""
    successors = scope_successors(units)
    for unit in units:
        if previous := unit.get("continues_contract"):
            successors.setdefault(previous, []).append(unit["flow_unit_id"])
    return successors


def _revision_shape(event):
    required = ("id", "kind", "unit", "base_revision", "actor", "reason", "criteria")
    if not isinstance(event, dict) or not all(key in event for key in required):
        return False
    return (isinstance(event["id"], str) and ID.fullmatch(event["id"])
            and event["kind"] in ("authorization", "counterevidence")
            and type(event["base_revision"]) is int and event["base_revision"] >= 0
            and all(isinstance(event[key], str) and event[key].strip() for key in ("actor", "reason", "unit"))
            and criteria_ok(event["criteria"]))


def shape_issue(unit, by_id):
    frozen = unit.get("root_contract")
    scope = unit.get("criterion_scope")
    if "continues_scope" in unit:
        previous = unit["continues_scope"]
        origin = by_id.get(previous) if isinstance(previous, str) else None
        if (not origin or previous != unit.get("previous_unit_id") or not unit.get("parent_unit_id")
                or any(unit.get(k) != origin.get(k) for k in ("parent_unit_id", "criterion_scope", "scope_artifact",
                                                               "acceptance", "acceptance_command", "expected_output"))):
            return "invalid scoped continuation: parent, criterion or acceptance operation changed"
    if ("product_goal" in unit or "product_contract_sha256" in unit) and (
            not isinstance(unit.get("product_goal"), str) or not ID.fullmatch(unit["product_goal"])
            or ("product_contract_sha256" not in unit or (unit["product_contract_sha256"] is not None
                and not re.fullmatch(r"[0-9a-f]{64}", str(unit["product_contract_sha256"]))))
            or unit.get("delivery_goal") not in (None, unit["product_goal"])
            or (not frozen and not unit.get("continues_contract"))):
        return "invalid product goal or frozen contract digest"
    if "continues_contract" in unit and (
            not isinstance(unit["continues_contract"], str) or unit["continues_contract"] not in by_id
            or not unit.get("previous_unit_id") or unit.get("parent_unit_id") or frozen
            or unit["continues_contract"] != unit.get("previous_unit_id")):
        return "invalid continuation of the preceding contract"
    if "recheck" in unit:
        checkpoint = unit["recheck"]
        if (not isinstance(checkpoint, dict) or type(checkpoint.get("attempt")) is not int
                or not isinstance(checkpoint.get("evidence"), str)):
            return "invalid recheck marker"
    if "root_contract" in unit and (not isinstance(frozen, dict) or unit.get("parent_unit_id") or
            frozen.get("unit") != unit["flow_unit_id"] or not criteria_ok(frozen.get("criteria")) or
            any(not isinstance(frozen.get(k), str) or not frozen[k].strip() for k in ("intent", "source", "acceptance"))):
        return "invalid frozen root contract"
    if scope is not None and (not unit.get("parent_unit_id") or not isinstance(scope, list) or not scope
            or any(not isinstance(k, str) or not ID.fullmatch(k) for k in scope)):
        return "invalid child criterion scope"
    if "contract_revisions" not in unit:
        return None
    events = unit["contract_revisions"]
    if not isinstance(events, list) or not frozen:
        return "invalid contract revisions"
    seen = set()
    criteria = dict(frozen["criteria"])
    for n, event in enumerate(events):
        if (not _revision_shape(event) or event["base_revision"] != n or event["id"] in seen
                or event["unit"] != unit["flow_unit_id"] or not isinstance(event.get("evidence"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", str(event.get("sha256", "")))
                or type(event.get("attempt")) is not int or event["attempt"] < 0):
            return "invalid revision identity, evidence or sequence"
        if event["kind"] == "counterevidence" and any(criteria.get(k) != v for k, v in event["criteria"].items()):
            return "counterevidence cannot replace accepted criteria"
        criteria.update(event["criteria"])
        seen.add(event["id"])
    return None


def bind_product(root, unit_id):
    from loop_workflow import _payload, _unit, runtime_path
    import loop_event_log
    import loop_paro_engine

    path = runtime_path(root)
    with loop_event_log._cross_process_lock(path), loop_paro_engine._commit_lock(path):
        state = _payload(path)
        unit = _unit(state, unit_id)
        contract, digest = _contract(_project_path(Path(root), CONTRACT))
        frozen = unit.get("root_contract") or {}
        if (not unit.get("product_goal") or contract["goal_id"] != unit["product_goal"]
                or contract["criteria"] != frozen.get("criteria") or unit.get("release_version") not in (None, contract["release_version"])
                or contract.get("authority") not in (None, frozen.get("authority"))):
            raise ValueError("product must match the originally declared goal, criteria, authority and release")
        if unit.get("product_contract_sha256") == digest:
            return unit
        if unit.get("product_contract_sha256") is not None:
            raise ValueError("the registered product contract has already been bound to different bytes")
        unit["product_contract_sha256"] = digest
        loop_paro_engine._atomic_replace_bytes(path, loop_paro_engine._serialize(state))
        return unit


def _response(root, event):
    response = event.get("response")
    if (not isinstance(response, dict) or set(response) != {"message_id", "source", "sha256", "quote"}
            or not all(isinstance(v, str) and v.strip() for v in response.values())):
        raise ValueError("authorization requires a source message ID, original response file, digest and exact quote")
    path = _project_path(Path(root), response["source"])
    if (_hash_file(path, nonempty=True) != response["sha256"]
            or response["quote"] not in path.read_text(encoding="utf-8")):
        raise ValueError("the original response or quoted authorization differs from its source")


def _authorization(root, owner, event, digest, decision):
    from decision_repository import read_snapshot
    from governance_store import StoreError

    if not isinstance(decision, str) or not re.fullmatch(r"DEC-\d+", decision):
        raise ValueError("an authorized revision requires a registered decision ID")
    if owner["root_contract"].get("authority") != event["actor"]:
        raise ValueError("only the originally designated authority can authorize the revision")
    _response(root, event)
    try:
        snapshot = read_snapshot(Path(root) / ".governance")
    except StoreError as exc:
        raise ValueError(f"cannot verify revision authorization: {exc}") from exc
    matches = [r for r in snapshot["records"] if r["id"] == decision]
    if len(matches) != 1 or matches[0]["decider"] != event["actor"] or digest not in matches[0]["content"]:
        raise ValueError("authorization must match the decision maker and the approved evidence SHA-256")
    return dict(decision=decision, decider=event["actor"], content=matches[0]["content"],
                provenance="project-recorded decision and quoted response", identity_verification="outside local verifier")


def evidence_issue(root, owner):
    frozen = owner.get("root_contract") or {}
    if frozen.get("adopted_from"):
        try:
            if _hash_file(_project_path(Path(root), frozen["source_evidence"]), nonempty=True) != frozen["source_sha256"]:
                return "the newly confirmed intent's source has changed"
        except (KeyError, ValueError, OSError) as exc:
            return f"the adoption source is unavailable: {exc}"
    for event in owner.get("contract_revisions", []):
        try:
            path = _project_path(Path(root), event["evidence"])
            if _hash_file(path, nonempty=True) != event["sha256"]:
                return f"revision {event['id']}: evidence changed"
            original = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_json_object)
            if not isinstance(original, dict) or any(event.get(k) != v for k, v in original.items()):
                return f"revision {event['id']}: state differs from original evidence"
            if event["kind"] == "authorization":
                _response(root, event)
        except (OSError, TypeError, ValueError) as exc:
            return f"revision {event['id']}: {exc}"
    return None


def activate_recheck(path, unit):
    """Reopen an existing exit at its next CAS version, preserving every prior receipt."""
    import loop_event_log
    import loop_paro_engine
    from loop_workflow import _payload, _unit

    with loop_paro_engine._commit_lock(path):
        state = _payload(path)
        unit = _unit(state, unit["flow_unit_id"])
        loop = unit["loop_state"]
        previous = loop["cas_version"]
        loop.update(active_loop=True, agent_phase="plan", cas_version=previous + 1)
        unit["runtime_status"] = "active"
        loop_paro_engine._atomic_replace_bytes(path, loop_paro_engine._serialize(state))
        event = loop_event_log.build_event(unit["flow_unit_id"], "phase_enter", cas_version=previous + 1,
                                           from_version=previous, actor="contract-recheck", to_phase="plan",
                                           evidence_ref=unit["recheck"]["evidence"])
        loop_event_log.append_event(event, log_path=path.with_name("loop-event-log.jsonl"))
        return unit


def _reopen(unit, evidence):
    if unit["runtime_status"] == "completed":
        unit["recheck"] = {"attempt": len(unit["gate_history"]), "evidence": evidence}
        unit["runtime_status"] = "dormant"
        unit["gate_state"]["status"] = "pending"
        unit["loop_state"]["agent_phase"] = "plan"


def recheck(root, unit_id):
    from loop_workflow import _payload, _unit, runtime_path
    from loop_revalidation import exit_issue, owner_for
    from checks.loop_receipts import verify_attempt
    import loop_event_log
    import loop_paro_engine

    path = runtime_path(root)
    with loop_event_log._cross_process_lock(path), loop_paro_engine._commit_lock(path):
        state = _payload(path)
        unit = _unit(state, unit_id)
        if unit.get("recheck") and unit["runtime_status"] in ("active", "dormant"):
            return unit
        if unit["runtime_status"] != "completed":
            raise ValueError("recheck requires a completed unit with stale acceptance evidence")
        history = unit["gate_history"]
        verify_attempt(root, unit, history[-1], len(history) - 1)
        if not exit_issue(root, unit, owner_for(state, unit)):
            raise ValueError("the latest scoped acceptance is still current")
        _reopen(unit, history[-1]["evidence_ref"])
        loop_paro_engine._atomic_replace_bytes(path, loop_paro_engine._serialize(state))
        return unit


def revise(root, unit_id, evidence, decision=None):
    from loop_workflow import _payload, _unit, runtime_path
    import loop_event_log
    import loop_paro_engine

    path = runtime_path(root)
    source = _project_path(Path(root), evidence)
    if source == path:
        raise ValueError("revision evidence must be separate from the runtime")
    _hash_file(source, nonempty=True)
    raw = source.read_bytes()
    event = json.loads(raw.decode("utf-8"), object_pairs_hook=_json_object)
    keys = {"id", "kind", "unit", "base_revision", "actor", "reason", "criteria"}
    if isinstance(event, dict) and event.get("kind") == "authorization":
        keys.add("response")
    if not _revision_shape(event) or set(event) != keys or event["unit"] != unit_id:
        raise ValueError("revision needs a scoped original statement, source identity, affected criteria and base revision")
    digest = hashlib.sha256(raw).hexdigest()
    if event["kind"] == "counterevidence" and decision:
        raise ValueError("counterevidence does not authorize changes to the goal")
    with loop_event_log._cross_process_lock(path), loop_paro_engine._commit_lock(path):
        state = _payload(path)
        unit = _unit(state, unit_id)
        if "root_contract" not in unit:
            raise ValueError("revise the root that owns the original criteria")
        if event["kind"] == "authorization":
            if not isinstance(event["response"], dict) or event["response"].get("source") == evidence:
                raise ValueError("the original user response must be separate from the revision")
            authorization = _authorization(root, unit, event, digest, decision)
        revisions = unit.setdefault("contract_revisions", [])
        record = dict(event, evidence=evidence, sha256=digest, decision=decision)
        if decision:
            record["authorization"] = authorization
        for prior in revisions:
            if prior["id"] == event["id"]:
                if all(prior.get(k) == v for k, v in record.items()):
                    return prior
                raise ValueError("revision id was already consumed")
        if event["base_revision"] != len(revisions):
            raise ValueError("root revision changed; read the current acceptance before revising")
        if event["kind"] == "counterevidence" and any(
                current_criteria(unit).get(k) != v for k, v in event["criteria"].items()):
            raise ValueError("counterevidence must name existing criteria with their current wording")
        if unit.get("acceptance_command") and event["kind"] == "authorization":
            raise ValueError("changing a fixed command requires a newly authorized unit and acceptance operation")
        record["attempt"] = len(unit.get("gate_history", []))
        by_id = {u["flow_unit_id"]: u for u in state["flow_units"]}
        if unit.get("product_contract_sha256"):
            from loop_revalidation import displaced_evidence
            record["prior_evidence"] = displaced_evidence(root, unit, event["criteria"], by_id)
        revisions.append(record)
        historical = acceptance_successors(state["flow_units"])
        for child in state["flow_units"]:
            affected = child is unit or (root_unit(child, by_id) is unit and (
                child.get("continues_contract") or set(child.get("criterion_scope", [])).intersection(event["criteria"])))
            if child["flow_unit_id"] not in historical and affected:
                _reopen(child, evidence)
        loop_paro_engine._atomic_replace_bytes(path, loop_paro_engine._serialize(state))
        return record
