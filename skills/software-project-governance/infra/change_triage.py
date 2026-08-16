#!/usr/bin/env python3
"""Change-control triage engine + machine record writer — FIX-237.4 / ADR-017 §4.4.

The ``change-triage`` CLI (verify_workflow.py thin entry) delegates here. A
new **product-code** task MUST complete the mandatory four-step triage before
it is created in plan-tracker:

  a. **dependency analysis** — runs task-priority-analysis
     (:mod:`task_priority` parse + compute) and snapshots the full tool
     output (rendered text + JSON report) into the triage record;
  b. **priority determination** — P0/P1/P2 with in-flight task counts and
     the version-chain context from the plan-tracker roadmap;
  c. **conflict check** — same-file overlap with in-flight tasks (the
     existing triage records are the machine registry of in-flight file
     sets; completed tasks never conflict);
  d. **version adaptation** — target version validated against the current
     workflow version and the planned-next version in the roadmap.

Behavior contract (ADR-017 §4.4 / FIX-237.4 / DEC-139):

  - **Fail-closed intake**: an unknown task-family dependency, a priority
    outside P0/P1/P2, an empty ``files`` list, a target version lower than
    the current version, a new-task dependency cycle, or a malformed task id
    produces NO record and a non-zero CLI exit — the task cannot be created
    without a triage record.
  - **Machine record**: ``.governance/change-triage/{TASK_ID}.json`` holds
    the four-step analysis + the ``task-priority-analysis`` snapshot
    (``report_json`` + ``report_text``); an evidence-log row (id
    ``TRIAGE-{TASK_ID}``) is appended at the same time. The evidence-log
    call snapshot contract = the JSON command output stored in the record
    (FIX-237.5).
  - **Single record per task (FIX-247)**: re-triaging an already-recorded
    task id is rejected (fail-closed) — the machine record is immutable and
    a duplicate would self-conflict plus double the evidence row.
  - **Best-effort all-or-nothing (FIX-247)**: the record and its evidence
    row are written record-first, then evidence row. If the evidence append
    fails after the record write, the record is rolled back so no
    half-written triage remains; true cross-file atomicity is not achievable
    without a journal, so a rollback that itself fails leaves the record
    behind (residual risk, reported via the returned ``error``).
  - **Quick lane boundary (FIX-228)**: only ``.governance/`` governance
    record changes may skip triage; any new task touching product code
    (skills/**, agents/**, infra/**, commands/**, ...) MUST run the standard
    path. Check 32 (checks.triage_domain) enforces the record requirement.
  - **Cycle tolerance (FIX-237.2/237.3)**: existing graph cycles are WARN
    (snapshotted, never blocking). A cycle CREATED BY the new task itself is
    fail-closed.
  - **Purity contract**: analysis helpers perform no file I/O and no
    side effects; all I/O lives in :func:`run_triage` /
    :func:`load_triage_records` (mirror of review_record.py). The module
    imports only the standard library + :mod:`task_priority` (peer, pure).

Usage::

    from change_triage import run_triage
    text = Path(".governance/plan-tracker.md").read_text(encoding="utf-8")
    summary = run_triage(
        task_id="FIX-241", title="...", priority="P2",
        target_version="0.73.0", depends_on=["FIX-237"],
        files=["skills/software-project-governance/infra/x.py"],
        reason="...", plan_tracker_text=text,
        current_version="0.72.0", governance_dir=Path(".governance"),
    )
    if summary.get("error"):
        sys.exit(2)
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import task_priority
from task_priority import (
    compute_unblocked_tasks,
    format_report,
    parse_task_dependencies,
)


__version__ = "0.73.0"

# Record layout (relative to .governance/).
TRIAGE_SUBDIR = "change-triage"
TRIAGE_SCHEMA_VERSION = 1
PRIORITIES = ("P0", "P1", "P2")
UNVERSIONED_MARKERS = ("未规划版本", "未定版本", "—", "-", "")

_TASK_ID_RE = re.compile(r"^[A-Z]+-\d+$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
_ID_TOKEN_RE = re.compile(r"(?<![-A-Z])([A-Z]+)-(\d+)\b")

# Task-family prefixes (FIX-171 precedent, mirrored from task_priority.py so
# this module stays a thin analysis layer with no peer import beyond the
# pure task_priority module). Cross-entity refs (RISK/DEC/REVIEW/EVD/...) are
# descriptive context, NEVER dependencies, and are dropped from --depends-on.
_TASK_FAMILY_PREFIXES = frozenset({
    "FIX", "REL", "AUDIT", "REQ", "FMT", "DIAG", "MAINT", "SYSGAP", "TD",
    "DESIGN", "VAL", "CLEANUP", "PRINCIPLE", "TASK", "RESEARCH", "ACCEPT",
    "INIT", "PLAN", "FEAT", "DOC",
})
_CROSS_ENTITY_PREFIXES = frozenset({
    "RISK", "DEC", "REVIEW", "EVD", "TIER", "CONSTRAINT", "TOOL", "ADR",
})


def split_dep_ids(raw: str) -> list:
    """Extract task-family dependency IDs from a raw ``--depends-on`` cell.

    Cross-entity references (RISK-/DEC-/REVIEW-/EVD-/... — FIX-171
    precedent) are descriptive context and are dropped; only task-family IDs
    (FIX/REL/AUDIT/REQ/...) are returned, de-duplicated, in first-seen order.

    Args:
        raw: comma/semicolon/whitespace separated dependency list.

    Returns:
        list of task-family IDs (e.g. ``["FIX-100"]``).
    """
    seen = set()
    result = []
    for m in _ID_TOKEN_RE.finditer(str(raw or "")):
        prefix, number = m.group(1), m.group(2)
        if prefix in _CROSS_ENTITY_PREFIXES:
            continue
        if prefix not in _TASK_FAMILY_PREFIXES:
            continue
        task_id = "{0}-{1}".format(prefix, number)
        if task_id not in seen:
            seen.add(task_id)
            result.append(task_id)
    return result


def _report_to_json(report) -> dict:
    """Serialize a task_priority.PriorityReport to a JSON-safe dict."""
    return {
        "total": report.total,
        "completed": [t.task_id for t in report.completed],
        "blocked": [
            {"task_id": b.task.task_id,
             "blocking_dependencies": list(b.blocking_dependencies)}
            for b in report.blocked
        ],
        "unblocked": [t.task_id for t in report.unblocked],
        "recommended_next": [t.task_id for t in report.recommended_next],
        "non_executable": [t.task_id for t in report.non_executable],
        "cycles": [list(c) for c in report.cycles],
        "cycle_warning": report.cycle_warning,
    }


def _would_create_cycle(task_id: str, depends_on: list, report) -> bool:
    """True when adding ``task_id -> depends_on`` edges closes a cycle.

    The new task is not in the table yet, so a cycle can only form when
    ``task_id`` already exists as a table row (re-triage) and one of its new
    dependencies transitively depends back on it. Existing graph cycles are
    NOT counted here — they are WARN-level (FIX-237.3 tolerance).
    """
    graph = dict(report.dependency_graph or {})
    if task_id not in graph:
        return False
    # Replace the existing edges of task_id with the new dependency edges.
    graph[task_id] = tuple(dep for dep in depends_on if dep != task_id)

    def _reaches(start: str, target: str, seen) -> bool:
        if start == target:
            return True
        if start in seen:
            return False
        seen.add(start)
        return any(_reaches(dep, target, seen) for dep in graph.get(start, ()))

    return any(_reaches(dep, task_id, set()) for dep in depends_on)


def run_dependency_analysis(plan_tracker_text: str, depends_on: list,
                            task_id: str = "") -> dict:
    """Step a — run task-priority-analysis and snapshot its full output.

    Args:
        plan_tracker_text: raw plan-tracker markdown (passed as text so the
            compute path stays I/O-free).
        depends_on: task-family dependency IDs of the new task.
        task_id: the new task id (used only for new-task cycle detection).

    Returns:
        dict with ``unblocked`` / ``blocked`` / ``blocked_by`` /
        ``unknown_deps`` / ``cycles`` / ``cycle_warning`` /
        ``new_task_cycle`` and the ``snapshot`` (``tool``,
        ``module_version``, ``report_json``, ``report_text``). Never raises.
    """
    tasks = parse_task_dependencies(plan_tracker_text)
    report = compute_unblocked_tasks(tasks)
    status_map = {t.task_id: t for t in tasks}

    unknown_deps = []
    blocked_by = []
    for dep in depends_on:
        task = status_map.get(dep)
        if task is None:
            unknown_deps.append(dep)  # fail-closed (FIX-171 conservative)
        elif not task.is_completed():
            blocked_by.append(dep)

    report_json = _report_to_json(report)
    return {
        "unblocked": [t.task_id for t in report.unblocked],
        "blocked": [b.task.task_id for b in report.blocked],
        "blocked_by": blocked_by,
        "unknown_deps": unknown_deps,
        "cycles": [list(c) for c in report.cycles],
        "cycle_warning": report.cycle_warning,
        "new_task_cycle": bool(task_id) and _would_create_cycle(
            task_id, depends_on, report),
        "snapshot": {
            "tool": "task-priority-analysis",
            "module_version": getattr(task_priority, "__version__", "unknown"),
            "report_json": report_json,
            "report_text": format_report(report),
        },
    }


def parse_version_chain(plan_tracker_text: str) -> list:
    """Parse the ``版本路线图`` roadmap table into a version chain.

    Header-driven: the ``版本`` and ``状态`` columns are located by header
    cell text. Markdown emphasis (``**0.73.0**``) is stripped. Parsing stops
    at the first row whose version cell does not match a version shape
    (``\\d+\\.\\d+`` — FIX-250 P3-1 / FIX-248 R0), so trailing tables after the
    roadmap are never appended.

    Returns:
        list of dicts ``{"version": str, "status": str}`` in row order.
    """
    rows = []
    header_idx = {}
    for line in str(plan_tracker_text or "").splitlines():
        line = line.strip()
        if not line.startswith("|") or "---" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if "版本" in cells[0] and "状态" in cells:
            header_idx = {
                name: i for i, name in enumerate(cells)
                if name in ("版本", "状态")
            }
            continue
        if not header_idx or len(cells) <= max(header_idx.values()):
            continue
        version = re.sub(r"[*`]", "", cells[header_idx["版本"]]).strip()
        status = re.sub(r"[*`]", "", cells[header_idx["状态"]]).strip()
        if version:
            if not re.match(r"\d+\.\d+", version):
                break
            rows.append({"version": version, "status": status})
    return rows


def analyze_priority_context(plan_tracker_text: str, priority: str) -> dict:
    """Step b — priority determination context (in-flight + version chain).

    Args:
        plan_tracker_text: raw plan-tracker markdown.
        priority: proposed priority, MUST be P0/P1/P2.

    Returns:
        dict with ``proposed``, ``in_flight`` (per-priority counts of
        non-completed tasks) and ``version_chain``.

    Raises:
        ValueError: priority outside P0/P1/P2.
    """
    priority = str(priority or "").strip().upper()
    if priority not in PRIORITIES:
        raise ValueError(
            "priority must be one of P0/P1/P2 (got {0!r})".format(priority))
    tasks = parse_task_dependencies(plan_tracker_text)
    in_flight = {"P0": 0, "P1": 0, "P2": 0}
    for task in tasks:
        if not task.is_completed() and task.priority in in_flight:
            in_flight[task.priority] += 1
    return {
        "proposed": priority,
        "in_flight": in_flight,
        "version_chain": parse_version_chain(plan_tracker_text),
    }


def _version_tuple(version: str):
    """``(major, minor, patch)`` for a semver string, else None."""
    if not _SEMVER_RE.match(str(version or "")):
        return None
    return tuple(int(part) for part in version.split("."))


def validate_version(target_version: str, current_version: str,
                     version_chain: list) -> dict:
    """Step d — version adaptation: validate the target version.

    Rules:
      - unversioned markers (``未规划版本`` / ``—`` / ...) are allowed;
      - otherwise the target MUST be semver;
      - a semver target LOWER than ``current_version`` is an ERROR;
      - a semver target different from the planned-next roadmap version is a
        WARN issue (advisory — the Coordinator may still choose it).

    Returns:
        dict ``{"target", "current", "planned_next", "issues", "ok"}``.
        ``ok`` is False only when an ERROR issue exists.
    """
    target = str(target_version or "").strip()
    issues = []
    normalized = re.sub(r"[*`]", "", target).strip()
    if normalized in UNVERSIONED_MARKERS:
        planned = next(
            (r["version"] for r in version_chain
             if any(k in str(r["status"]) for k in ("规划", "未发布", "进行中"))),
            None)
        return {
            "target": target, "current": current_version,
            "planned_next": planned, "issues": [], "ok": True,
        }
    if _version_tuple(normalized) is None:
        issues.append(
            "ERROR: 目标版本 {0!r} 不是合法 semver（X.Y.Z）或未规划版本标记"
            .format(target))
        return {
            "target": target, "current": current_version,
            "planned_next": None, "issues": issues, "ok": False,
        }
    if current_version and _version_tuple(current_version) is not None:
        if _version_tuple(normalized) < _version_tuple(current_version):
            issues.append(
                "ERROR: 目标版本 {0} 低于当前版本 {1}".format(
                    normalized, current_version))
    planned = next(
        (r["version"] for r in version_chain
         if any(k in str(r["status"]) for k in ("规划", "未发布", "进行中"))),
        None)
    if planned and normalized != planned:
        issues.append(
            "WARN: 目标版本 {0} 与版本路线图规划的下一个版本 {1} 不一致"
            "（advisory——请确认版本链）".format(
                normalized, planned))
    return {
        "target": target, "current": current_version,
        "planned_next": planned, "issues": issues,
        "ok": not any(i.startswith("ERROR") for i in issues),
    }


def check_conflicts(files: list, records: list, completed_ids: set) -> list:
    """Step c — same-file conflict check against in-flight triage records.

    Args:
        files: product files the new task will modify (normalized to
            forward slashes).
        records: existing triage records (list of dicts).
        completed_ids: task ids that are completed in plan-tracker —
            completed tasks never conflict.

    Returns:
        list of ``{"task_id", "files", "overlap"}`` for each in-flight task
        whose recorded file set intersects the new task's files.
    """
    def _norm(path):
        return str(path).replace("\\", "/").strip().lower()

    new_files = {_norm(f) for f in (files or []) if str(f).strip()}
    conflicts = []
    for record in records or []:
        task_id = record.get("task_id", "")
        if not task_id or task_id in completed_ids:
            continue
        recorded = {
            _norm(f) for f in (record.get("files") or []) if str(f).strip()}
        overlap = sorted(new_files & recorded)
        if overlap:
            conflicts.append({
                "task_id": task_id,
                "files": sorted(recorded),
                "overlap": overlap,
            })
    return conflicts


def load_triage_records(governance_dir) -> list:
    """Load all existing triage records under ``<governance_dir>/change-triage``.

    Returns:
        list of record dicts; malformed JSON files are skipped (Check 32
        flags them separately).
    """
    records = []
    rec_dir = Path(governance_dir) / TRIAGE_SUBDIR
    if not rec_dir.is_dir():
        return records
    for path in sorted(rec_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(payload, dict):
            payload["_record_path"] = str(path)
            records.append(payload)
    return records


def _evidence_row(task_id: str, record_name: str, date_str: str) -> str:
    """Evidence-log row in the machine-write contract (mirrors review_record).

    Column shape: | id | task_ref | type | description | basis | artifacts |
    actor | date | gate | conclusion |. The description carries no ISO date
    and no conclusion token so live collectors land on the real columns.
    """
    cells = [
        "TRIAGE-{0}".format(task_id),
        task_id,
        "变更控制",
        "change-triage CLI 机器写入 triage 记录（依赖/优先级/冲突/版本四步分析）",
        "事实依据：change-triage 输出摘要（机器写入；命令输出 JSON 快照见 "
        "change-triage/{0}.json）".format(task_id),
        record_name,
        "change-triage",
        date_str,
        "G11",
        "TRIAGED",
    ]
    return "| " + " | ".join(cells) + " |\n"


def run_triage(*, task_id: str, title: str = "", priority: str,
               target_version: str, depends_on, files, reason: str = "",
               plan_tracker_text: str, current_version: str = "",
               governance_dir, existing_records=None, records_dir=None,
               evidence_path=None) -> dict:
    """Run the mandatory four-step triage and write the machine record.

    Fail-closed: any step-ERROR (unknown dependency, invalid priority, empty
    files, stale target version, new-task cycle, malformed task id) returns
    ``{"error": ...}`` and writes NOTHING — no record, no evidence row.

    Args:
        task_id: new task id (PREFIX-NNN).
        title: one-line task title.
        priority: proposed priority (P0/P1/P2).
        target_version: target version (semver or unversioned marker).
        depends_on: iterable of task-family dependency IDs.
        files: product files the task will modify (MUST be non-empty for
            product-code tasks; quick-lane .governance/-only work does not
            use this command).
        reason: triage rationale (priority determination context).
        plan_tracker_text: raw plan-tracker markdown.
        current_version: current workflow version (SKILL.md frontmatter).
        governance_dir: ``.governance`` directory (records land under
            ``governance_dir/change-triage/``).
        existing_records: optional pre-loaded triage records (defaults to
            :func:`load_triage_records`).
        records_dir / evidence_path: explicit overrides for tests.

    Returns:
        dict summary (record_path, evidence_row_written, analysis,
        snapshot_ref, wiring-free). ``error`` key present on fail-closed
        input. Never raises.
    """
    task_id = str(task_id or "").strip()
    if not _TASK_ID_RE.match(task_id):
        return {"error": "task_id must match PREFIX-NNN (e.g. FIX-241)"}
    if not files:
        return {"error": "files is required and must be non-empty for a "
                         "product-code task (quick lane covers .governance/ "
                         "records only — FIX-228 boundary)"}

    # FIX-249 P3-3/P3-4: resolve the record path up front and reject a
    # re-triage BEFORE the pure dependency/priority/version analysis. The
    # direct ``.exists()`` check is the authoritative "single record per
    # task" guard (module contract): unlike load_triage_records it also
    # catches malformed records (which Check 32 flags separately), so an
    # unparseable record file is never silently overwritten.
    if records_dir is None:
        records_dir = Path(governance_dir) / TRIAGE_SUBDIR
    records_dir = Path(records_dir)
    record_name = "{0}.json".format(task_id)
    if (records_dir / record_name).exists():
        return {"error": "task {0} already has a triage record — re-triage "
                         "is rejected (the machine record is immutable; use "
                         "a new task id or resolve manually)".format(task_id)}

    depends_on = list(split_dep_ids(depends_on))
    try:
        priority_context = analyze_priority_context(
            plan_tracker_text, priority)
    except ValueError as exc:
        return {"error": str(exc)}

    version_result = validate_version(
        target_version, current_version,
        version_chain=priority_context["version_chain"])
    if not version_result["ok"]:
        return {"error": "version adaptation failed: {0}".format(
            "; ".join(version_result["issues"]))}

    dependency = run_dependency_analysis(
        plan_tracker_text, depends_on, task_id=task_id)
    if dependency["unknown_deps"]:
        return {"error": "dependency analysis failed — unknown task-family "
                         "dependency id(s): {0} (fail-closed, FIX-171 "
                         "conservative default)".format(
                             ", ".join(dependency["unknown_deps"]))}
    if dependency["new_task_cycle"]:
        return {"error": "dependency analysis failed — new task {0} would "
                         "create a dependency cycle".format(task_id)}

    records = existing_records
    if records is None:
        records = load_triage_records(governance_dir)
    tasks = parse_task_dependencies(plan_tracker_text)
    completed_ids = {t.task_id for t in tasks if t.is_completed()}
    conflicts = check_conflicts(files, records, completed_ids)

    # Machine-write the triage record + evidence row.
    if evidence_path is None:
        evidence_path = Path(governance_dir) / "evidence-log.md"
    evidence_path = Path(evidence_path)
    try:
        records_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return {"error": "cannot create triage record dir: {0}".format(exc)}

    today = date.today().isoformat()
    record = {
        "schema_version": TRIAGE_SCHEMA_VERSION,
        "task_id": task_id,
        "title": str(title or ""),
        "priority": priority_context["proposed"],
        "target_version": version_result["target"],
        "depends_on": depends_on,
        "files": [str(f) for f in files],
        "reason": str(reason or ""),
        "created_at": today,
        "tool": "change-triage",
        "tool_version": __version__,
        "analysis": {
            "dependency": {
                "unblocked": dependency["unblocked"],
                "blocked": dependency["blocked"],
                "blocked_by": dependency["blocked_by"],
                "unknown_deps": dependency["unknown_deps"],
                "cycles": dependency["cycles"],
                "cycle_warning": dependency["cycle_warning"],
                "new_task_cycle": dependency["new_task_cycle"],
            },
            "priority_context": {
                "proposed": priority_context["proposed"],
                "in_flight": priority_context["in_flight"],
                "version_chain": priority_context["version_chain"],
            },
            "conflicts": conflicts,
            "version": {
                "target": version_result["target"],
                "current": version_result["current"],
                "planned_next": version_result["planned_next"],
                "issues": version_result["issues"],
            },
        },
        "snapshot": dependency["snapshot"],
    }
    try:
        (records_dir / record_name).write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
    except OSError as exc:
        return {"error": "cannot write triage record: {0}".format(exc)}
    try:
        with evidence_path.open("a", encoding="utf-8") as fh:
            fh.write("\n" + _evidence_row(task_id, record_name, today))
    except OSError as exc:
        # P2-2: the record write above already succeeded, so a failed
        # evidence append would leave a half-written triage (record without
        # its evidence row). Best-effort roll back the record so the two
        # writes stay all-or-nothing. True atomicity across two files is not
        # achievable without a journal; this rollback narrows the window
        # (the residual risk is documented in the module contract).
        try:
            (records_dir / record_name).unlink()
        except OSError:
            pass
        return {"error": "cannot append evidence row: {0}".format(exc)}

    return {
        "task_id": task_id,
        "record_path": str(records_dir / record_name),
        "evidence_row_written": True,
        "record_id": "TRIAGE-{0}".format(task_id),
        "analysis": record["analysis"],
        "snapshot": {
            "tool": dependency["snapshot"]["tool"],
            "module_version": dependency["snapshot"]["module_version"],
            "ref": "{0}/{1}".format(TRIAGE_SUBDIR, record_name),
        },
    }


__all__ = [
    "TRIAGE_SUBDIR",
    "TRIAGE_SCHEMA_VERSION",
    "PRIORITIES",
    "split_dep_ids",
    "run_dependency_analysis",
    "parse_version_chain",
    "analyze_priority_context",
    "validate_version",
    "check_conflicts",
    "load_triage_records",
    "run_triage",
]
