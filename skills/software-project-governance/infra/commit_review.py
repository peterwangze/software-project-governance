"""Authorize the actual staged product change against the named unit's current evidence."""
from pathlib import Path
import sys

from authority_ledger import LedgerWriter
from checks.loop_receipts import verify_attempt
from loop_engine import reviewer_gates
from loop_workflow import _payload, runtime_path
from review_facts import _git, derive_review_facts


def delivery_path(path):
    """Every staged host artifact can belong to the user's delivery, regardless of project layout."""
    return bool(path) and path.split("/", 1)[0] != ".governance"


def check(root, task):
    staged = _git(root, "diff", "--cached", "--name-only", "--no-renames", "-z").split("\0")
    if not any(delivery_path(p) for p in staged):
        return True
    path = runtime_path(root)
    if not path.is_file():
        raise ValueError(f"{task}: native work-unit state is missing; restore its state or use loop start for new work")
    state = _payload(path)
    units = [u for u in state["flow_units"] if task in (u["task_id"], u["flow_unit_id"])]
    if not units:
        raise ValueError(f"no registered unit for {task!r}; use loop start with the goal and acceptance criteria")
    ledger = LedgerWriter(root / ".governance")
    if not ledger.integrity["ok"]:
        raise ValueError("review ledger integrity failure")
    reviews = ledger.state["reviews"]
    last_error = f"{task}: no current code-review receipt for the staged product change"
    eligible = {}
    for unit in units:
        history = unit.get("gate_history", [])
        if unit["runtime_status"] not in ("active", "completed"):
            continue
        if history:
            verify_attempt(root, unit, history[-1], len(history) - 1, ledger=ledger)
        selected = set()
        for index in range(len(history) - 1, -1, -1):
            item = history[index]
            if item["decision"] in ("iterate", "escalate"):
                break
            if item["gate"] == "G6" and item["evidence_ref"].startswith("review-"):
                verify_attempt(root, unit, item, index, ledger=ledger)
                selected.add(index)
        ids = eligible.setdefault(unit["task_id"], set())
        for event in reviews:
            if event["task_id"] != unit["task_id"] or reviewer_gates(event["reviewer"]) != ["G6"]:
                continue
            binding = event.get("loop_binding")
            if binding:
                if binding.get("unit") != unit["flow_unit_id"] or binding.get("attempt") not in selected:
                    continue
            else:
                observed = event.get("observed_loop")
                current = {"unit": unit["flow_unit_id"], "attempt": len(history),
                           "cas_version": unit["loop_state"].get("cas_version")}
                if observed != current:
                    continue
            if event["verdict"] in ("APPROVED", "APPROVED_WITH_NOTES"):
                ids.add(event["review_id"])
    for task_id, ids in eligible.items():
        if not ids:
            continue
        try:
            facts = derive_review_facts(root, task_id, ids, path_filter=delivery_path)
        except ValueError as exc:
            last_error = str(exc)
            continue
        if facts["review"]["conclusion"] in ("APPROVED", "APPROVED_WITH_NOTES"):
            return True
    raise ValueError(last_error)


def main():
    try:
        check(Path(sys.argv[1]).resolve(), sys.argv[2])
        return 0
    except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
        print(f"M7.4 BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
