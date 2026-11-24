"""Read-only verification of the evidence consumed by native work units."""

import hashlib
import json
import re

from loop_workflow import _payload, _review_receipt, runtime_path


def command_observation_passes(observation):
    """Compare the complete decoded stdout, tolerating only the terminal line ending."""
    actual, expected = observation.get("stdout"), observation.get("expected_output")
    if (type(observation.get("returncode")) is not int or observation["returncode"] != 0
            or "error" in observation or not isinstance(actual, str) or not isinstance(expected, str)):
        return False
    return actual.replace("\r\n", "\n").removesuffix("\n") == expected.replace("\r\n", "\n").removesuffix("\n")


def _observation_result(root, unit, history, attempt):
    from delivery_acceptance import _project_path

    ref = history["evidence_ref"]
    match = re.fullmatch(r"loop-evidence/([0-9a-f]{64})\.json", ref)
    if not match:
        raise ValueError("unexpected observation reference")
    path = _project_path(root, ".governance/" + ref)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != match.group(1):
        raise ValueError("observation bytes changed")
    data = json.loads(raw)
    if (data["unit"], data["gate"], data["iteration"], data["attempt"]) != (
        unit["flow_unit_id"], history["gate"], history["iteration"], attempt
    ):
        raise ValueError("observation belongs to another unit, gate or attempt")
    if history["actor"] == "delivery-acceptance":
        if (data.get("contract_sha256") != (unit.get("product_contract_sha256") or unit.get("delivery_contract_sha256"))
                or data.get("receipt_verdict") not in {"PASS", "FAIL"}
                or not re.fullmatch("[0-9a-f]{64}", data.get("receipt_sha256", ""))):
            raise ValueError("product acceptance disagrees with the frozen contract")
        return "APPROVED" if data["receipt_verdict"] == "PASS" else "NEEDS_CHANGE"
    if (history["actor"] != "acceptance-command" or data.get("command") != unit.get("acceptance_command")
            or data.get("expected_output") != unit.get("expected_output")):
        raise ValueError("observation disagrees with the declared acceptance operation")
    return "APPROVED" if command_observation_passes(data) else "NEEDS_CHANGE"


def review_id_from_ref(ref):
    if not isinstance(ref, str):
        return None
    match = re.fullmatch(r"review-(.+-R\d+)(-[a-z0-9-]+)?\.md", ref)
    return "REVIEW-" + match[1] + (match[2] or "").upper() if match else None


class PublishedReceiptScan:
    """Confirm the immutable Git pins used by this scan after a review passes its ledger checks."""

    def __init__(self, evidence_refs):
        self.evidence_refs = evidence_refs
        self.objects = None

    def objects_for(self, root, ledger):
        if self.evidence_refs is not None:
            from review_record import PublishedReviewObjects
            selected = {review_id_from_ref(ref) for ref in self.evidence_refs}
            self.evidence_refs = None
            try:
                self.objects = PublishedReviewObjects(root, (
                    row for row in ledger.state["reviews"] if isinstance(row, dict)
                    and isinstance(row.get("review_id"), str) and row["review_id"] in selected))
            except (OSError, RuntimeError):
                # Resolving the Git root may fail. The individual reader still judges the receipt.
                pass
        return self.objects


def verify_attempt(root, unit, item, attempt, *, ledger=None, review_objects=None, published_scan=None):
    """Verify the frozen receipt bound to this gate, unit and attempt."""
    ref = item["evidence_ref"]
    if ref.startswith("review-"):
        review_id = review_id_from_ref(ref)
        if not review_id:
            raise ValueError("invalid review receipt name")
        name, binding, receipt = _review_receipt(root, unit, item["gate"], review_id,
                                                published=True, ledger=ledger, review_objects=review_objects,
                                                published_scan=published_scan)
        if name != ref or (binding.get("iteration"), binding.get("attempt")) != (item["iteration"], attempt):
            raise ValueError("review belongs to another attempt")
        result = receipt["verdict"]
    else:
        result = _observation_result(root, unit, item, attempt)
    if result != item["result"]:
        raise ValueError("gate result differs from its evidence")


def receipt_issues(root):
    """Check each receipt in its own historical attempt, without executing host operations."""
    try:
        units = _payload(runtime_path(root))["flow_units"]
    except (OSError, UnicodeError, ValueError) as exc:
        return [str(exc)]
    from authority_ledger import LedgerWriter

    issues = []
    ledger = None
    published_scan = PublishedReceiptScan(
        item["evidence_ref"] for unit in units for item in unit.get("gate_history", []))
    for unit in units:
        history = unit.get("gate_history", [])
        if unit["runtime_status"] == "completed" and (not history or history[-1]["decision"] != "exit"):
            issues.append(f"{unit['flow_unit_id']}: missing completion receipt")
        for attempt, item in enumerate(history):
            try:
                if ledger is None and str(item.get("evidence_ref")).startswith("review-"):
                    ledger = LedgerWriter(runtime_path(root).parent)
                verify_attempt(root, unit, item, attempt, ledger=ledger, published_scan=published_scan)
            except (AttributeError, KeyError, TypeError, OSError, UnicodeError, ValueError) as exc:
                issues.append(f"{unit['flow_unit_id']} {item.get('gate')} #{attempt}: {exc}")
    return issues


def require_task_exit(root, task):
    """Authorize closing a registered task only after all its units have verifiable exits."""
    from loop_workflow import _unfinished

    path = runtime_path(root)
    state = _payload(path)
    units = [unit for unit in state["flow_units"] if unit["task_id"] == task]
    if not units:
        raise ValueError(f"{task}: no registered work unit owns this ticket; "
                         f"use loop start --unit {task} to register its goal and acceptance")
    for unit in units:
        history = unit.get("gate_history", [])
        if unit["runtime_status"] != "completed" or not history or history[-1]["decision"] != "exit":
            raise ValueError(f"{task}: work unit {unit['flow_unit_id']} has no certified exit")
        verify_attempt(root, unit, history[-1], len(history) - 1)
        from loop_revalidation import exit_issue, owner_for
        if issue := exit_issue(root, unit, owner_for(state, unit)):
            raise ValueError(f"{task}: {issue}")
        if waiting := _unfinished(root, state, unit, children=True):
            raise ValueError(f"{task}: unresolved work units {', '.join(waiting)}")
