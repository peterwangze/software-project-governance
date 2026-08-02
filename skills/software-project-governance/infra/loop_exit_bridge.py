"""loop_exit → next-unit 推荐桥 (FIX-236.3 / ADR-017 §3.4).

Consumes ``loop_exit`` events (produced by :func:`loop_gate_processor.
process_gate_result` on a passed gate) and turns them into **next-unit
candidates**: it calls the task-priority pure read
(:func:`task_priority.compute_unblocked_tasks`) and emits a top-N
recommendation with dependency-resolution reasons. The snapshot is persisted
as ``.governance/loop-exit-candidates.json``; the read end is the
``next-candidates`` thin CLI (verify_workflow.py, P3-5).

Constraints (ADR-017 §5 / §8):

  - Pure read over task_priority — no mutation of plan-tracker, no writes
    outside the candidate snapshot.
  - Cycle tolerance: a dependency cycle is a WARNING, never an ERROR (the
    report is best-effort, FIX-237.2/237.3 semantics).
  - Missing plan-tracker / event log → an empty report (skipped), never a
    raise — the bridge must not break the review-record path that calls it.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from task_priority import (
    compute_unblocked_tasks,
    parse_task_dependencies,
)


CANDIDATES_FILENAME = "loop-exit-candidates.json"
DEFAULT_TOP_N = 3


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dependency_reasons(task, status_map):
    """Human-readable dependency-resolution reason for one candidate.

    Reports each dependency class by ACTUAL status (P2-3, Code Review R1):
    satisfied (completed), pending (present but not completed), or unknown
    (task-family id not present in the status map at all). The old
    "dependencies satisfied (none pending)" fallback was misleading for
    dependencies whose status could not be resolved (filtered / cyclic /
    missing rows).
    """
    if not task.dependencies:
        return "no blocking dependencies"
    satisfied = [d for d in task.dependencies if status_map.get(d, False)]
    pending = [
        d for d in task.dependencies
        if d in status_map and not status_map.get(d, False)
    ]
    unknown = [d for d in task.dependencies if d not in status_map]
    parts = []
    if satisfied:
        parts.append("dependencies satisfied: {0}".format(", ".join(sorted(satisfied))))
    if pending:
        parts.append("dependencies pending: {0}".format(", ".join(sorted(pending))))
    if unknown:
        parts.append(
            "dependencies with unknown status: {0}".format(", ".join(sorted(unknown))))
    return "; ".join(parts) if parts else "no blocking dependencies"


def build_candidates(plan_tracker_text, events, top_n=DEFAULT_TOP_N):
    """Build the next-unit candidate report from loop_exit events.

    Args:
        plan_tracker_text: raw plan-tracker markdown text (or path-like).
        events: iterable of loop event dicts (loop-event-log.jsonl shape).
        top_n: number of recommended candidates to emit.

    Returns:
        dict: ``{"generated_at", "exit_events_consumed", "total",
        "unblocked", "recommended_top_n", "cycles", "cycle_warning",
        "non_executable"}``. Never raises.
    """
    exit_events = [
        ev for ev in (events or [])
        if isinstance(ev, dict) and ev.get("event_type") == "loop_exit"
    ]
    try:
        report = compute_unblocked_tasks(parse_task_dependencies(plan_tracker_text))
    except Exception as exc:  # noqa: BLE001 — bridge must never raise
        return {
            "generated_at": _now_iso(),
            "exit_events_consumed": len(exit_events),
            "total": 0,
            "unblocked": [],
            "recommended_top_n": [],
            "cycles": [],
            "cycle_warning": False,
            "non_executable": [],
            "parse_error": str(exc),
        }

    status_map = {t.task_id: t.is_completed() for t in report.completed}
    status_map.update({t.task_id: t.is_completed() for t in report.unblocked})
    status_map.update({t.task_id: t.is_completed() for t in report.non_executable})
    for b in report.blocked:
        status_map[b.task.task_id] = b.task.is_completed()

    unblocked = [
        {"task_id": t.task_id, "priority": t.priority, "status": t.status}
        for t in report.unblocked
    ]
    top = [
        {
            "task_id": t.task_id,
            "priority": t.priority,
            "version": t.target_version or "",
            "reason": _dependency_reasons(t, status_map),
        }
        for t in report.recommended_next[: max(0, int(top_n))]
    ]
    return {
        "generated_at": _now_iso(),
        "exit_events_consumed": len(exit_events),
        "total": report.total,
        "unblocked": unblocked,
        "recommended_top_n": top,
        "cycles": list(report.cycles or []),
        "cycle_warning": bool(report.cycle_warning),
        "non_executable": [t.task_id for t in report.non_executable],
    }


def write_candidates(report, path):
    """Atomically persist the candidate snapshot JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def read_candidates(path):
    """Read a candidate snapshot JSON; None when missing/unreadable."""
    path = Path(path)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def refresh_candidates(root, top_n=DEFAULT_TOP_N, candidate_path=None):
    """Refresh the next-unit snapshot for a host root (best-effort, never raises).

    Reads ``<root>/.governance/plan-tracker.md`` + the loop event log, builds
    the candidate report, and persists it to
    ``<root>/.governance/loop-exit-candidates.json`` (or ``candidate_path``).
    Missing plan-tracker → a skipped/empty report without writing.
    """
    if root is None:
        return {"skipped": True, "reason": "no host root"}
    root = Path(root)
    gov = root / ".governance"
    pt = gov / "plan-tracker.md"
    if not pt.is_file():
        return {"skipped": True, "reason": "plan-tracker.md not found"}
    try:
        text = pt.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return {"skipped": True, "reason": "plan-tracker unreadable: {0}".format(exc)}

    events = []
    try:
        from loop_event_log import read_events  # deferred (FEAT-007 peer)
        events = read_events(log_path=gov / "loop-event-log.jsonl")
    except Exception:  # noqa: BLE001 — event log is optional for the bridge
        events = []

    report = build_candidates(text, events, top_n=top_n)
    target = Path(candidate_path) if candidate_path else gov / CANDIDATES_FILENAME
    try:
        write_candidates(report, target)
        report["snapshot"] = str(target)
    except OSError as exc:
        report["snapshot_error"] = str(exc)
    return report


__all__ = [
    "CANDIDATES_FILENAME",
    "DEFAULT_TOP_N",
    "build_candidates",
    "write_candidates",
    "read_candidates",
    "refresh_candidates",
]
