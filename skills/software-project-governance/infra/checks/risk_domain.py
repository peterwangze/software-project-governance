"""Risk-domain checks — extracted from verify_workflow.py in 0.70.0.

Scope (DEC-083 Phase 5b / ADR-016 / FEAT-009): the risk-staleness check
(Check 2) and risk-escalation check (Check 8), plus their risk-only parsing
helpers (`parse_open_risks`, `_parse_context_open_risks`), and the
REQ-145.3 / FIX-265 mitigation-closure watchdog
(`check_risk_mitigation_closure`, Check 36).

This module owns the risk check domain. Shared helpers and constants still
defined in verify_workflow.py (`RISK_PATH`, `_context_file`, `_context_task`,
`_governance_table_cells`) are reached through a deferred module reference
rather than a top-level import, so verify_workflow.py can import this module
at module load time without an import cycle.

Functions with cross-domain callers (`_risk_status_is_closed` is used by the
release-blockers check; `_check_risk_has_closed` is used by gate auto-judge)
STAY in verify_workflow.py and are reached via the deferred accessor — they
are not duplicated here (ADR-016 §3.2 / §4.3 KEEP rule).

See docs/architecture/ADR-016-verify-phase5-extraction-0.70.0.md for the
design and the line-number baseline used during extraction.
"""

import re
from datetime import date, datetime

# Peer, pure module (stdlib only) — no import cycle: verify_workflow.py
# imports this domain at module load, and task_priority never imports back.
from task_priority import compute_unblocked_tasks, parse_task_dependencies

# ── Shared-helper access (deferred to avoid import cycle) ──────────
# Same deferred-_vw() pattern as checks.manifest (Phase 1) and
# checks.capability_registry (Phase 2). The shared names are resolved lazily
# on the first call into this module (after verify_workflow has finished
# loading) and cached in this module's globals for subsequent calls, so the
# moved function bodies can reference them by bare name unchanged.

_VW_CACHE = None


def _vw():
    """Return the verify_workflow module (imported lazily, cached).

    Cached so repeated calls reuse the same module reference (REVIEW-FIX-153
    P2, same pattern as checks.manifest / checks.capability_registry).
    """
    global _VW_CACHE
    if _VW_CACHE is None:
        import verify_workflow  # noqa: WPS433 (deferred import on purpose)
        _VW_CACHE = verify_workflow
    return _VW_CACHE


# Shared names this domain reaches back into verify_workflow for. Refreshed
# on every call into `_resolve_shared()` (NOT cached) so test-time monkey-
# patching of verify_workflow attributes propagates, and so the moved
# function bodies can reference them by bare name (byte-identical bodies,
# per ADR-016 §5.3 "no behavioral change").
_SHARED_NAMES = (
    "RISK_PATH",
    "_context_file",
    "_context_task",
    "_governance_table_cells",
    "SAMPLE_PATH",  # REQ-145.3: plan-tracker (host facts), live map build
    "_TASK_ID_IN_REF_RE",  # REQ-145.3: task-id reference regex (prose scan)
)


def _resolve_shared():
    """Refresh this module's globals with shared names from verify_workflow.

    Re-fetches on EVERY call (not cached) so test-time monkey-patching of
    verify_workflow attributes (e.g. `patch.object(vw, "RISK_PATH", ...)`)
    propagates into this module's bare-name lookups. The cost is negligible:
    these checks run once per CLI invocation, not in a hot loop, and `getattr`
    on a cached module reference is cheap. This mirrors how checks.manifest
    re-resolves `ROOT = _root()` inside each function body (Phase 1 precedent).
    """
    vw = _vw()
    g = globals()
    for _name in _SHARED_NAMES:
        g[_name] = getattr(vw, _name)


# ── Domain constants and functions (moved verbatim from verify_workflow.py) ──

# Canonical "open risk" predicate for the risk domain (FIX-270 R0 F3).
# The whole domain (parse_open_risks / check_risk_staleness / check_risk_escalation
# — and the status fast path's parse_active_risks) shares ONE judgement: a risk
# is active/open iff its 当前状态 cell is exactly ``打开``. Non-open states
# (缓解完成 / 已关闭 / resolved / 降级 / 已接受…) are the risk state-machine's
# closed or in-flight terminal states and MUST NOT be counted as open — no
# parallel marker sets.
def is_risk_status_open(status):
    """Return True iff the risk status cell is the domain-canonical ``打开``."""
    return (status or "").strip() == "打开"


def _parse_context_open_risks(root):
    _resolve_shared()
    risk_path = _context_file(root, ".governance/risk-log.md")
    if not risk_path.is_file():
        return []
    risks = []
    for line in risk_path.read_text(encoding="utf-8").split("\n"):
        stripped = line.strip()
        if not stripped.startswith("| RISK-"):
            continue
        cells = _governance_table_cells(stripped)
        if len(cells) < 9:
            continue
        status = cells[8]
        if not is_risk_status_open(status):
            continue
        risks.append(_context_task(
            cells[0],
            cells[2] if len(cells) > 2 else cells[0],
            status,
            ".governance/risk-log.md",
            stripped,
            kind="risk",
        ))
    return risks


def parse_open_risks():
    """Return list of (risk_id, date_str) for open risks."""
    _resolve_shared()
    if not RISK_PATH.is_file():
        return []
    content = RISK_PATH.read_text(encoding="utf-8")
    risks = []
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| RISK-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 10:
            risk_id = parts[1]
            date_str = parts[2]
            status = parts[9]
            if is_risk_status_open(status):
                risks.append((risk_id, date_str))
    return risks


def check_risk_staleness():
    """Check for open risks older than 7 days."""
    _resolve_shared()
    risks = parse_open_risks()
    today = date.today()
    stale = []
    fresh = []
    for risk_id, date_str in risks:
        try:
            risk_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            age = (today - risk_date).days
            if age > 7:
                stale.append((risk_id, date_str, age))
            else:
                fresh.append((risk_id, date_str, age))
        except ValueError:
            stale.append((risk_id, date_str, -1))
    return {
        "total_open": len(risks),
        "stale": stale,
        "fresh": fresh,
    }


def check_risk_escalation():
    """Check for open risks whose escalation deadline has passed.

    Per AUDIT-045: risk-log defines Owner + escalation deadline + mitigation action,
    but when the deadline passes, nothing enforces the escalation.
    This function detects open risks with passed deadlines — the external validation
    counterpart to the risk escalation MUST rule.

    Returns: dict with escalated risks list and summary stats.
    """
    _resolve_shared()
    if not RISK_PATH.is_file():
        return {
            "escalated": [],
            "total_open": 0,
        }

    content = RISK_PATH.read_text(encoding="utf-8")
    today = date.today()
    escalated = []
    all_open = []

    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| RISK-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 13:
            continue

        risk_id = parts[1]
        date_str = parts[2]          # 日期
        status = parts[9]            # 当前状态
        deadline_str = parts[11]     # 截止日期

        if not is_risk_status_open(status):
            continue

        all_open.append(risk_id)

        if not deadline_str or deadline_str == "":
            continue

        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            if today > deadline:
                escalated.append({
                    "risk_id": risk_id,
                    "created": date_str,
                    "deadline": deadline_str,
                    "days_overdue": (today - deadline).days,
                })
        except ValueError:
            continue

    return {
        "escalated": escalated,
        "total_open": len(all_open),
        "escalation_count": len(escalated),
    }


# ── REQ-145.3 / FIX-265: risk mitigation closure (Check 36) ────────────────
# Watchdog for the AUDIT-145 "write a mitigation action and call it done"
# blind spot: the time-dimension checks (2/8) only see status == 打开, so
# router RISK-003 (缓解中) / tv RISK-001 (打开) passed even with mitigation
# not landed. The closure watchdog is a CONTENT-dimension assertion: every
# risk that is NOT 已关闭 must reference tasks in the plan-tracker, and
# those tasks must be completed (or the risk carries an exemption marker).
# DEC-146 gradual path: WARN start; FAIL only on R1 + (deadline passed OR
# high severity). Fail-safe: undecidable rows / unavailable task-priority
# never produce a false FAIL.

_RISK_CLOSED_STATUS = "已关闭"
_RISK_EXEMPTION_MARKERS = ("[无任务引用]", "[跨实体]", "[流程动作]")
# Placeholder-only 关联任务 cells: treat as "no explicit reference" so the
# 缓解动作 prose fallback (secondary source) may still resolve a task id.
_RISK_NO_REF_PLACEHOLDERS = ("", "—", "-", "无")


def is_risk_status_closed(status):
    """Return True iff the risk status cell marks the risk closed (``已关闭``).

    REQ-145.3 owns its own closure predicate, deliberately SEPARATE from
    :func:`is_risk_status_open` (the canonical active set predicate for
    Check 2/8 and the FIX-270 status fast path). The closure watchdog must
    catch intermediate states (缓解中 / 缓解完成 / …) that the open
    predicate classifies as non-active, so it asks a different question:
    "is the risk terminal-closed?" — only ``已关闭`` answers yes.
    """
    return (status or "").strip() == _RISK_CLOSED_STATUS


def _task_status_is_completed(cell):
    """Return True iff a task status cell marks the task completed (✅).

    Mirrors ``task_priority._status_is_completed`` — the ✅ leading-emoji
    rule is the single reliable completion signal; the map is rebuilt from
    the same raw status cells task-priority classifies with, so one task
    never carries two statuses.
    """
    return "✅" in (cell or "")


def _severity_is_high(severity):
    """Return True iff the 严重级别 cell is 高 or 严重 (R2 upgrade signal)."""
    sev = (severity or "").strip()
    return "严重" in sev or "高" in sev


def _mitigation_deadline_overdue(deadline_str, today):
    """Return True iff the 截止日期 cell is before today (R2 upgrade signal).

    Unparseable / empty cell → False (fail-safe: never escalate to FAIL on
    a date the check cannot read).
    """
    try:
        deadline = datetime.strptime((deadline_str or "").strip(),
                                     "%Y-%m-%d").date()
    except ValueError:
        return False
    return today > deadline


def _default_task_status_map():
    """Build ``{task_id: raw status cell}`` from task_priority (FIX-265 / F11).

    ``compute_unblocked_tasks`` keeps its internal ``status_map`` private
    (:1351), so the map is REBUILT from the returned ``PriorityReport``:
    every parsed task lands in exactly one of the completed / blocked /
    unblocked / non_executable buckets, and each TaskDep carries its raw
    ``.status`` cell. Returns None when task-priority cannot run (missing
    plan-tracker, unreadable, parse failure) — the caller then fails-safe
    the affected risks to WARN instead of guessing.
    """
    try:
        tasks = parse_task_dependencies(SAMPLE_PATH)
        report = compute_unblocked_tasks(tasks)
    except Exception:  # noqa: BLE001 — fail-safe: any parse failure = unavailable
        return None
    status_map = {}
    for bucket in (report.completed, report.blocked, report.unblocked,
                   report.non_executable):
        for entry in bucket:
            dep = entry.task if hasattr(entry, "task") else entry
            status_map[dep.task_id] = dep.status
    return status_map


def _mitigation_result(result, verdict, reason):
    result["stats"]["warn_count"] = len(result["warnings"])
    result["stats"]["violation_count"] = len(result["violations"])
    result["verdict"] = verdict
    result["reason"] = reason
    return result


def check_risk_mitigation_closure(risk_content=None, task_status_map=None):
    """FIX-265 / REQ-145.3 (design §3.3): Check 36 — risk mitigation closure.

    Every risk whose status is NOT ``已关闭`` must be provably closed by
    the plan-tracker: the referenced task(s) must be completed — or the row
    must carry an exemption marker.

    Signals:
      R1  WARN — non-closed risk references ≥1 task whose status is not
          completed (gradual start; DEC-146).
      R2  FAIL — R1 AND (截止日期 passed OR 严重级别 高/严重) (progressive).
      R3  WARN — referenced task id is absent from the task-status map
          (cross-entity / archived); never upgraded to FAIL.
      R4  WARN — non-closed risk with NO machine-resolvable task reference
          and NO exemption marker — content-level disclosure (router
          RISK-003 pattern), never a silent no-verdict.
      R5  skip / no-verdict — closed risk, exemption marker, ragged row,
          missing status, or undecidable.

    Parser lock (F6): risk rows are read with raw ``line.split("|")``
    parts indexes, identical to the domain's Check 2/8 (:177-189) —
    parts[9]=当前状态, parts[10]=缓解动作, parts[11]=截止日期,
    parts[12]=关联任务. ``_governance_table_cells`` is deliberately NOT
    used (it strips the leading/trailing empty cells — off-by-one).

    Task-reference resolution: 关联任务列 (parts[12]) is the primary,
    machine-written source; when it yields no task id (empty/placeholder),
    the 缓解动作列 (parts[10]) prose is scanned with ``_TASK_ID_IN_REF_RE``
    (secondary), and the union is de-duplicated.

    ``task_status_map`` is an injectable ``{task_id: raw status cell}``;
    the default (``None``) rebuilds it from task-priority over the host
    plan-tracker. Unavailable task-priority → fail-safe WARN, never FAIL.

    Returns ``{verdict, reason, violations, warnings, stats}``; verdict ∈
    PASS / WARN / FAIL / no-verdict. Never raises.
    """
    result = {
        "verdict": "no-verdict",
        "reason": "",
        "violations": [],
        "warnings": [],
        "stats": {
            "risks_scanned": 0,
            "closed_skipped": 0,
            "exempted_skipped": 0,
            "ragged_skipped": 0,
            "judged": 0,
            "pass": 0,
            "warn_count": 0,
            "violation_count": 0,
        },
    }
    _resolve_shared()

    content = risk_content
    if content is None:
        if not RISK_PATH.is_file():
            return _mitigation_result(
                result, "no-verdict", "risk-log.md not found — nothing to judge")
        try:
            content = RISK_PATH.read_text(encoding="utf-8")
        except (IOError, OSError):
            return _mitigation_result(
                result, "no-verdict", "risk-log.md unreadable — nothing to judge")

    if task_status_map is None:
        task_status_map = _default_task_status_map()

    today = date.today()
    for line in (content or "").split("\n"):
        line = line.strip()
        if not line.startswith("| RISK-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        # Same minimum width the domain's Check 8 requires (:190-191):
        # missing columns → undecidable row (R5), never a false judgement.
        if len(parts) < 13:
            result["stats"]["ragged_skipped"] += 1
            continue
        result["stats"]["risks_scanned"] += 1
        risk_id = parts[1]
        status = parts[9]
        mitigation = parts[10]
        deadline_str = parts[11]
        ref_cell = parts[12]
        note_cell = parts[13] if len(parts) > 13 else ""
        severity = parts[7]

        # R5: closed → skip (no residue in the advisory set).
        if is_risk_status_closed(status):
            result["stats"]["closed_skipped"] += 1
            continue
        # R5: missing/empty status → undecidable (fail-safe).
        if not (status or "").strip():
            result["stats"]["ragged_skipped"] += 1
            continue
        # R5: exemption marker → skip (no false positive on [无任务引用]/
        # [跨实体]/[流程动作] rows).
        if any(marker in mitigation or marker in ref_cell or marker in note_cell
               for marker in _RISK_EXEMPTION_MARKERS):
            result["stats"]["exempted_skipped"] += 1
            continue

        result["stats"]["judged"] += 1

        # Task references: 关联任务列 primary; 缓解动作列 prose secondary
        # (only when the primary column yields no task id). Union + dedupe.
        refs = set()
        if (ref_cell or "").strip() not in _RISK_NO_REF_PLACEHOLDERS:
            refs = set(_TASK_ID_IN_REF_RE.findall(ref_cell))
        if not refs:
            refs = set(_TASK_ID_IN_REF_RE.findall(mitigation or ""))

        if not refs:
            # R4 content-level disclosure (a non-closed risk whose mitigation
            # has no machine-resolvable task landing point).
            result["warnings"].append({
                "rule": "R4",
                "risk_id": risk_id,
                "task_refs": [],
                "reason": (
                    "risk {0} is not closed ('{1}') but its mitigation has no "
                    "machine-resolvable task reference (关联任务列 empty and no "
                    "FIX-/DEV- id in 缓解动作列) and no exemption marker "
                    "[无任务引用]/[跨实体]/[流程动作] — content-level disclosure, "
                    "the mitigation is not provably landed ({2})".format(
                        risk_id, status, mitigation[:80])),
            })
            continue

        # Fail-safe: task-priority unavailable → cannot verify statuses.
        if task_status_map is None:
            result["warnings"].append({
                "rule": "R1",
                "risk_id": risk_id,
                "task_refs": sorted(refs),
                "reason": (
                    "task_status_map 无法验证 — task-priority unavailable "
                    "(missing/unparseable plan-tracker); referenced task(s) "
                    "{0} cannot be confirmed completed, fail-safe WARN (never "
                    "FAIL)".format(", ".join(sorted(refs)))),
            })
            continue

        uncompleted = sorted(
            r for r in refs if r in task_status_map
            and not _task_status_is_completed(task_status_map[r]))
        absent = sorted(r for r in refs if r not in task_status_map)
        if uncompleted:
            overdue = _mitigation_deadline_overdue(deadline_str, today)
            high = _severity_is_high(severity)
            detail = ("[FAIL] risk {0} mitigation references task(s) {1} that "
                      "are not completed (status: {2})".format(
                          risk_id, ", ".join(uncompleted),
                          "; ".join("{0}={1}".format(r, task_status_map[r])
                                    for r in uncompleted)))
            if absent:
                detail += " (extra refs not found: {0})".format(", ".join(absent))
            if overdue or high:
                result["violations"].append({
                    "rule": "R2",
                    "risk_id": risk_id,
                    "task_refs": sorted(refs),
                    "deadline": deadline_str,
                    "severity": severity,
                    "reason": detail + (
                        " — deadline {0} passed AND/OR severity '{1}' — "
                        "mitigation closure overdue (progressive FAIL, "
                        "DEC-146)".format(deadline_str, severity)),
                })
            else:
                result["warnings"].append({
                    "rule": "R1",
                    "risk_id": risk_id,
                    "task_refs": sorted(refs),
                    "reason": detail + (
                        " — WARN (gradual start: no deadline/severity "
                        "escalation yet)"),
                })
        elif absent:
            # R3 cross-entity / archived reference — never upgraded to FAIL.
            result["warnings"].append({
                "rule": "R3",
                "risk_id": risk_id,
                "task_refs": absent,
                "reason": (
                    "risk {0} references task(s) {1} not found in the "
                    "task status map (cross-entity/archived) — WARN, not "
                    "FAIL (design R3)".format(risk_id, ", ".join(absent))),
            })
        else:
            result["stats"]["pass"] += 1

    if result["violations"]:
        return _mitigation_result(
            result, "FAIL",
            "{0} risk(s) with overdue/high-severity mitigation closure "
            "violation(s)".format(len(result["violations"])))
    if result["warnings"]:
        return _mitigation_result(
            result, "WARN",
            "{0} mitigation-closure warning(s), {1} judged, {2} passed".format(
                len(result["warnings"]), result["stats"]["judged"],
                result["stats"]["pass"]))
    if result["stats"]["judged"] and result["stats"]["pass"]:
        return _mitigation_result(
            result, "PASS",
            "{0} non-closed risk(s) all carry completed task "
            "references".format(result["stats"]["pass"]))
    return _mitigation_result(
        result, "no-verdict",
        "no non-closed risk with a resolvable task reference — nothing "
        "to judge")


