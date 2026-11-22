"""Bind a proposed route and scoped revisions to observations on the current artifact."""

import json
from pathlib import Path

from delivery_acceptance import _project_path, artifact_sha256, evaluate_delivery_acceptance
from loop_alignment import current_criteria, evidence_issue, root_unit


def owner_for(state, unit):
    return root_unit(unit, {u["flow_unit_id"]: u for u in state["flow_units"]})


def coverage(unit, owner):
    if unit["flow_unit_id"] == owner["flow_unit_id"] or unit.get("continues_contract"):
        return sorted(current_criteria(owner)) if "root_contract" in owner else []
    return unit.get("criterion_scope", [])


def check_scope(unit, owner, criteria):
    if not criteria or not set(criteria) <= set(coverage(unit, owner)):
        raise ValueError("decision must identify criteria within the unit's registered scope")


def command_targets(root, command, candidate):
    for arg in command[1:]:
        try:
            if arg and not arg.startswith("-") and (Path(root) / arg).resolve() == candidate:
                return True
        except (OSError, ValueError):
            continue
    return False


def product_result(root, owner, *, prerequisites=True):
    unit = owner
    if unit.get("product_contract_sha256") is None:
        raise ValueError(f"prepare the product contract and bind the declared criteria with loop bind-product --unit {unit['flow_unit_id']}")
    if owner.get("continues_contract"):
        from loop_workflow import _payload, runtime_path
        owner = owner_for(_payload(runtime_path(root)), unit)
    result = evaluate_delivery_acceptance(Path(root), goal_id=unit["product_goal"], required=True,
                                         acceptance_context=owner, _prerequisites=prerequisites)
    if result.get("contract_sha256") != owner["product_contract_sha256"]:
        raise ValueError("product contract changed since intake")
    return result


def active_decisions(unit):
    entries = unit.get("learning", [])
    retired = {entry["supersedes"] for entry in entries if "supersedes" in entry}
    return [entry for entry in entries if entry.get("candidate") and entry["id"] not in retired]


def selected_candidate_issue(root, unit, *, product_artifact=None, decisions=None):
    from loop_learning import learning_evidence_issue
    for entry in active_decisions(unit) if decisions is None else decisions:
        if product_artifact is not None and entry["candidate"] != product_artifact:
            return f"{unit['flow_unit_id']}/{entry['id']}: product receipt must cover selected candidate {entry['candidate']}"
        if issue := learning_evidence_issue(root, entry):
            return f"{unit['flow_unit_id']}/{entry['id']}: {issue}"
        try:
            digest = artifact_sha256(_project_path(Path(root), entry["candidate"]))
        except (ValueError, OSError) as exc:
            return str(exc)
        if digest != entry["candidate_sha256"]:
            return f"decision {entry['id']}: selected candidate changed; record the replacement with --supersedes"
    return None


def snapshot(root, unit, owner, *, product=None):
    """Built by the actual verifier, never by a caller asserting its own PASS."""
    decisions = active_decisions(unit)
    revisions = owner.get("contract_revisions", [])
    if issue := evidence_issue(root, owner):
        raise ValueError(issue)
    if not (decisions or revisions or product or unit.get("criterion_scope")):
        return None
    from loop_learning import learning_evidence_issue
    pins = {}
    for entry in decisions:
        if issue := learning_evidence_issue(root, entry):
            raise ValueError(issue)
        candidate = entry["candidate"]
        if candidate not in pins:
            pins[candidate] = artifact_sha256(_project_path(Path(root), candidate))
        if pins[candidate] != entry["candidate_sha256"]:
            raise ValueError(f"decision {entry['id']}: selected candidate changed; record the replacement with --supersedes")
        if product and (product.get("artifact") != candidate or product.get("artifact_sha256") != pins[candidate]):
            raise ValueError(f"decision {entry['id']} requires the product receipt for {candidate}")
    result = dict(root=owner["flow_unit_id"], revision=len(revisions), criteria=coverage(unit, owner),
                  candidates=pins, decisions={e["id"]: e["sha256"] for e in decisions})
    if product:
        result["product_receipt"] = product.get("receipt_sha256")
        result["results"] = {k: v["status"] for k, v in product.get("criteria_results", {}).items()}
        result["criterion_evidence"] = {k: v["evidence_sha256"] for k, v in product.get("criteria_results", {}).items()
                                        if v.get("evidence_sha256")}
    if unit.get("scope_artifact"):
        candidate = unit["scope_artifact"]
        if unit.get("acceptance_command") and not command_targets(root, unit["acceptance_command"], (Path(root) / candidate).resolve()):
            raise ValueError("the scoped command must receive the declared candidate path")
        result["scoped_artifact"] = {"path": candidate, "sha256": artifact_sha256(_project_path(Path(root), candidate))}
    elif unit.get("criterion_scope") and owner.get("product_goal"):
        from delivery_acceptance import CONTRACT, _contract
        contract, digest = _contract(_project_path(Path(root), CONTRACT))
        if digest != owner["product_contract_sha256"]:
            raise ValueError("root product contract changed")
        candidate = contract["artifact"]
        result["scoped_artifact"] = {"path": candidate, "sha256": artifact_sha256(_project_path(Path(root), candidate))}
    return result


def _recorded(root, unit, item, index):
    from checks.loop_receipts import verify_attempt
    from loop_workflow import _review_receipt
    verify_attempt(root, unit, item, index)
    ref = item["evidence_ref"]
    if ref.startswith("review-"):
        import re
        match = re.fullmatch(r"review-(.+-R\d+)(-[a-z0-9-]+)?\.md", ref)
        review = "REVIEW-" + match[1] + (match[2] or "").upper()
        _, binding, _ = _review_receipt(root, unit, item["gate"], review, published=True)
        return binding.get("outcome_check")
    raw = _project_path(Path(root), ".governance/" + ref).read_bytes()
    return json.loads(raw).get("outcome_check")


def displaced_evidence(root, unit, criteria, by_id):
    """Retain observations signed anywhere in this product lineage, including archived routes."""
    hashes = {k: set() for k in criteria}
    for member in by_id.values():
        if not member.get("product_goal") or root_unit(member, by_id) is not unit:
            continue
        for index, attempt in enumerate(member.get("gate_history", [])):
            proof = _recorded(root, member, attempt, index) or {}
            for key, fingerprint in proof.get("criterion_evidence", {}).items():
                if key in hashes:
                    hashes[key].add(fingerprint)
    try:
        result = product_result(root, unit)
    except ValueError:
        result = {}  # The registered product may already have been replaced.
    for key, observed in result.get("criteria_results", {}).items():
        if key in hashes and observed.get("evidence_sha256"):
            hashes[key].add(observed["evidence_sha256"])
    return {k: sorted(v) for k, v in hashes.items() if v}


def decision_view(root, unit, owner, entry, *, prerequisites=True):
    candidate = entry["candidate"]
    result = dict(status="pending", criteria=entry["criteria"], candidate=candidate, selected_sha256=entry["candidate_sha256"],
                  evidence_ref=None, reason="Run the scoped acceptance on the selected candidate.")
    try:
        from loop_learning import learning_evidence_issue
        if issue := learning_evidence_issue(root, entry):
            raise ValueError(issue)
        actual = artifact_sha256(_project_path(Path(root), candidate))
        history = unit.get("gate_history", [])
        for index in range(len(history) - 1, entry["attempt"] - 1, -1):
            item = history[index]
            observed = _recorded(root, unit, item, index)
            if not observed or observed.get("decisions", {}).get(entry["id"]) != entry["sha256"]:
                continue
            if item["evidence_ref"].startswith("review-") and item["decision"] == "advance":
                continue
            result["evidence_ref"] = item["evidence_ref"]
            statuses = observed.get("results", {})
            passed = (all(statuses.get(k) == "PASS" for k in entry["criteria"]) if statuses else
                      item["result"] in ("APPROVED", "APPROVED_WITH_NOTES"))
            result.update(recorded_status="passed" if passed else "failed", observed_sha256=observed["candidates"].get(candidate))
            if observed["candidates"].get(candidate) != actual:
                raise ValueError("the reviewed candidate bytes have changed; select replacement bytes with --supersedes")
            if any(set(entry["criteria"]).intersection(event["criteria"])
                   for event in owner.get("contract_revisions", [])[observed["revision"]:]):
                raise ValueError("a later revision requires rechecking these criteria")
            if "product_receipt" in observed:
                product = product_result(root, owner, prerequisites=prerequisites)
                if product.get("receipt_sha256") != observed["product_receipt"]:
                    raise ValueError("the current product evidence differs from the recorded receipt")
            return dict(result, status=result["recorded_status"], reason=item["reason"])
        if actual != entry["candidate_sha256"]:
            raise ValueError("selected candidate bytes changed; register the new candidate with --supersedes")
    except (ValueError, OSError, TypeError, KeyError) as exc:
        return dict(result, status="stale", reason=str(exc))
    return result


def exit_issue(root, unit, owner, *, prerequisites=True):
    """A previously certified exit is reusable only on its confirmed scope and current evidence."""
    if issue := evidence_issue(root, owner):
        return issue
    for entry in active_decisions(unit):
        proven = decision_view(root, unit, owner, entry, prerequisites=prerequisites)
        if proven["status"] != "passed":
            return f"{entry['id']}: {proven['reason']}"
    if unit.get("criterion_scope"):
        history = unit["gate_history"]
        proof = _recorded(root, unit, history[-1], len(history) - 1)
        if not proof or proof["criteria"] != unit["criterion_scope"]:
            return "scoped child needs its own acceptance receipt"
        if pin := proof.get("scoped_artifact"):
            try:
                if artifact_sha256(_project_path(Path(root), pin["path"])) != pin["sha256"]:
                    return f"child candidate changed; run loop recheck --unit {unit['flow_unit_id']}"
            except (OSError, ValueError) as exc:
                return f"restore the scoped candidate {pin['path']}: {exc}"
        if any(set(unit["criterion_scope"]).intersection(event["criteria"])
               for event in owner.get("contract_revisions", [])[proof["revision"]:]):
            return "the affected child criterion needs a new acceptance receipt"
    if unit.get("product_goal"):
        try:
            result = product_result(root, unit, prerequisites=prerequisites)
            if not result["pass"]:
                return ", ".join(result["issues"])
            last = unit["gate_history"][-1]
            proof = _recorded(root, unit, last, len(unit["gate_history"]) - 1)
            if not proof or proof.get("product_receipt") != result.get("receipt_sha256"):
                return "current product receipt differs from the certified exit"
        except (ValueError, OSError, TypeError, KeyError) as exc:
            return str(exc)
    return None


def recovery(root, unit, owner, learning, default_action):
    """Show what the actual next verifier must establish using the same acceptance evaluator."""
    gaps = {}
    if unit.get("product_goal"):
        try:
            result = product_result(root, unit)
            statuses = result.get("criteria_results", {})
            gaps = {k: statuses.get(k, {}).get("status", "NOT_RUN") for k in current_criteria(owner)
                    if statuses.get(k, {}).get("status") != "PASS"}
            if gaps and unit["runtime_status"] != "blocked":
                default_action = ("Recheck " + ", ".join(gaps) + " on the current product at its registered entrypoint. "
                                  + (result["issues"][0] if result["issues"] else "Record independent evidence."))
        except (ValueError, OSError) as exc:
            default_action = str(exc)
    if unit.get("recheck") and unit["runtime_status"] in ("active", "dormant"):
        default_action = "Recheck the original sample from " + unit["recheck"]["evidence"] + ". " + default_action
    unresolved = next((e for e in reversed(learning.get("learning", [])) if e.get("revalidation", {}).get("status")
                       in ("pending", "stale", "failed") and e["id"] in {a["id"] for a in active_decisions(unit)}), None)
    if unresolved:
        proof = unresolved["revalidation"]
        default_action = f"Recheck {', '.join(proof['criteria'])} on {proof['candidate']}. {proof['reason']}"
    return gaps, default_action
