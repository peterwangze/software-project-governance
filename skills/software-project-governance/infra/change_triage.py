#!/usr/bin/env python3
"""Change-control triage engine + machine record writer — FIX-237.4 / ADR-017 §4.4.

FEAT-013 / RISK-046 adds the dispatch-lock write API
(:func:`acquire_dispatch_locks` + :func:`agent_locks_acquire_cli`): the
Coordinator's ``agent-locks.json`` acquisition is machine-validated at
write time — pre-write path existence (a lock may not target a
nonexistent file unless declared ``expected_new``), and a same-day
change-triage ``files`` cross-check (mismatch = disclosed WARN, never
blocking). Hand-assembling dispatch locks is the RISK-046 drift root
cause; the write API is the root-cause fix.

The ``change-triage`` CLI (verify_workflow.py thin entry) delegates here. A
new **product-code** task MUST complete the mandatory five-step triage before
it is created in plan-tracker:

  a. **dependency analysis** — runs task-priority-analysis
     (:mod:`task_priority` parse + compute) and snapshots the full tool
     output (rendered text + JSON report) into the triage record;
  b. **priority determination** — P0/P1/P2 with in-flight task counts and
     the version-chain context from the plan-tracker roadmap;
  c. **conflict check** — same-file overlap with in-flight tasks (the
     existing triage records are the machine registry of in-flight file
     sets; completed tasks never conflict);
  d. **version adaptation** — target version validated against the project's
     current version (the plan-tracker roadmap's highest released row;
     FIX-288 two-layer semantics — never the workflow/plugin version) and
     the planned-next version in the roadmap;
  e. **execution side-effect declaration** (FIX-271 / AUDIT-146 §7.2 R2) —
     any outside-repo side effect implied by the task's ``files`` /
     rationale / acceptance (installer execution, real profile writes,
     network publishing) MUST be declared (``declared_side_effects``:
     side-effect surface + blast radius); a user-real-environment touch
     auto-attaches the R1 (one-of-three) review condition; an undeclared
     detectable side effect records a WARN issue (advisory — never
     silent, never blocking). The step lands in the record as the purely
     additive ``analysis.side_effect`` field.

Behavior contract (ADR-017 §4.4 / FIX-237.4 / DEC-139):

  - **Fail-closed intake**: an unknown task-family dependency, a priority
    outside P0/P1/P2, an empty ``files`` list, a target version lower than
    the current version, a new-task dependency cycle, or a malformed task id
    produces NO record and a non-zero CLI exit — the task cannot be created
    without a triage record. Step-e WARN issues are advisory (exit 0) —
    the WARN lives in the CLI output and the machine record.
  - **Machine record**: ``.governance/change-triage/{TASK_ID}.json`` holds
    the five-step analysis + the ``task-priority-analysis`` snapshot
    (``report_json`` + ``report_text``); an evidence-log row (id
    ``TRIAGE-{TASK_ID}``) is appended at the same time. The evidence-log
    call snapshot contract = the JSON command output stored in the record
    (FIX-237.5).
  - **Schema stability (FIX-271)**: ``TRIAGE_SCHEMA_VERSION`` stays 1 —
    step e is a purely additive optional field (``analysis.side_effect``)
    appended after the four existing step keys; no reader (Check 32
    validates the four required steps only) rejects unknown analysis
    fields, so existing records and consumers stay byte/shape compatible.
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
    :func:`load_triage_records` / :func:`acquire_dispatch_locks` /
    :func:`agent_locks_acquire_cli` (FEAT-013 dispatch-lock writer — the
    same machine-write discipline as the triage record). The module
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
import sys
from datetime import date, datetime
from pathlib import Path

import task_priority
from task_priority import (
    compute_unblocked_tasks,
    format_report,
    parse_task_dependencies,
)


__version__ = "0.77.0"

# Record layout (relative to .governance/).
TRIAGE_SUBDIR = "change-triage"
TRIAGE_SCHEMA_VERSION = 1
PRIORITIES = ("P0", "P1", "P2")
UNVERSIONED_MARKERS = ("未规划版本", "未定版本", "—", "-", "")

# FEAT-013 / RISK-046 — dispatch-lock write API constants.
LOCK_FILE_NAME = "agent-locks.json"
DEFAULT_LOCK_TTL_SECONDS = 14400  # 4h — matches the live M7.6a practice

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


# Release/planned roadmap status tokens (FIX-288 ⑨). A roadmap row counts as
# RELEASED when its status cell contains 「已发布」 (live variants: 已发布 /
# 已发布（tag 缺失待修）/ 已发布——origin/master=...; NOT 已撤回/失效 nor 发布事故 /
# 不可信发布). Planned-next candidates keep the FIX-237.4 keyword set.
_RELEASED_STATUS_TOKEN = "已发布"
_PLANNED_STATUS_KEYWORDS = ("规划", "未发布", "进行中")


def derive_project_current_version(plan_tracker_text: str) -> str:
    """Step-d fact source (FIX-288 ⑨): the PROJECT's current version.

    Two-layer version semantics: the WORKFLOW version (the plugin's own
    SKILL.md frontmatter) is NOT the project's current version. A host
    project may be arbitrarily older — or have no version roadmap at all —
    and validating its new tasks against the workflow version
    fail-closed-rejected legal target versions (router REL-002 live
    recurrence after EVO-004/EV-038). The project current version is the
    HIGHEST 「已发布」 row of the host plan-tracker version roadmap.

    Pure: parses the passed text, performs no I/O.

    Returns:
        The highest released semver row (e.g. ``"0.78.0"``), or ``""`` when
        the roadmap has no released row (or no roadmap) —
        :func:`validate_version` then skips the lower-bound comparison, so a
        no-version-planning host can triage normally.
    """
    released = []
    for row in parse_version_chain(plan_tracker_text):
        if _RELEASED_STATUS_TOKEN in str(row.get("status", "")):
            vt = _version_tuple(row.get("version", ""))
            if vt is not None:
                released.append((vt, str(row["version"])))
    if not released:
        return ""
    return max(released, key=lambda item: item[0])[1]


def _planned_next_version(version_chain: list, current_version: str):
    """Planned-next roadmap version for step d (FIX-288 ⑨ selection fix).

    The pre-fix selector returned the FIRST row (in roadmap row order) whose
    status contained a planned keyword — on the live roadmap the stale
    「0.66.2 补偿发布规划中」 row precedes the released 0.73.0-0.78.0 block, so
    every triage recorded ``planned_next="0.66.2"`` and emitted a false
    mismatch WARN. Correct selection: among planned-keyword rows, the LOWEST
    version STRICTLY ABOVE the project current version; when the current
    version is unknown, the lowest planned version overall; when every
    planned row sits at-or-below the current version, ``None`` (no advisory
    WARN — there is no next planned version to mismatch).

    Args:
        version_chain: roadmap rows (``{"version", "status"}``) from
            :func:`parse_version_chain`.
        current_version: the project's current version (may be empty).

    Returns:
        The planned-next version string, or None.
    """
    cur = _version_tuple(current_version)
    candidates = []
    for row in version_chain or []:
        status = str(row.get("status", ""))
        if not any(k in status for k in _PLANNED_STATUS_KEYWORDS):
            continue
        vt = _version_tuple(row.get("version", ""))
        if vt is not None:
            candidates.append((vt, str(row["version"])))
    if not candidates:
        return None
    if cur is not None:
        above = [v for vt, v in candidates if vt > cur]
        if above:
            return min(above, key=_version_tuple)
        return None
    return min((v for vt, v in candidates), key=_version_tuple)


def validate_version(target_version: str, current_version: str,
                     version_chain: list) -> dict:
    """Step d — version adaptation: validate the target version.

    Rules (FIX-288 two-layer semantics):
      - ``current_version`` is the PROJECT's current version — the highest
        released row of the plan-tracker roadmap
        (:func:`derive_project_current_version`), never the workflow/plugin
        version;
      - unversioned markers (``未规划版本`` / ``—`` / ...) are allowed;
      - otherwise the target MUST be semver;
      - a semver target LOWER than ``current_version`` is an ERROR;
      - a semver target different from the planned-next roadmap version is a
        WARN issue (advisory — the Coordinator may still choose it). The
        planned-next pick is the lowest planned row above the current
        version (:func:`_planned_next_version` — FIX-288 selection fix).

    Returns:
        dict ``{"target", "current", "planned_next", "issues", "ok"}``.
        ``ok`` is False only when an ERROR issue exists.
    """
    target = str(target_version or "").strip()
    issues = []
    normalized = re.sub(r"[*`]", "", target).strip()
    if normalized in UNVERSIONED_MARKERS:
        planned = _planned_next_version(version_chain, current_version)
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
    planned = _planned_next_version(version_chain, current_version)
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


# ─── Step e (FIX-271 / AUDIT-146 §7.2 R2) ──────────────────────────────────
#
# Execution side-effect signals. D2 root cause: the four legacy steps saw
# only repo-internal file sets, so a task whose acceptance/verification
# executes effects OUTSIDE the repository (installer runs, real profile
# writes, network publishing) was invisible to governance.

# Outside-repo FILE shapes: absolute POSIX root, Windows drive, UNC /
# single-backslash root (drive-relative root), home shorthand,
# environment-variable redirection, parent-directory escape.
_OUTSIDE_REPO_FILE_RE = re.compile(
    r"^(?:[A-Za-z]:[\\/]|\\|~|/|\$|%[^%]*%|\.\.)")

# User-real-environment FILE markers (home directory trees / env-var
# redirected targets under the user's profile).
_REAL_ENV_FILE_RE = re.compile(
    r"(?:^~|/Users/|/home/|\$DSH_HOME|\$HOME|%USERPROFILE%|%APPDATA%)",
    re.IGNORECASE)

# R5-banned unqualified wording (AUDIT-146 D1): the exact phrasings that
# made FEAT-010's acceptance run inside the real ~/.dsh with no isolation.
# IGNORECASE mirrors the file-side ``_REAL_ENV_FILE_RE`` (FIX-273 P3-2):
# Windows env-var names are case-insensitive, so lowercase variants
# (``%userprofile%`` / ``$home``) must not slip through.
#
# **Context-blindness limitation (FIX-273 P2-2)**: this wording detector is
# substring-based and does NOT parse negation or quotation context — the
# banned substrings trigger conservatively in ANY context (e.g. 「不要修改
# %USERPROFILE%」 or quoting R5 rule text still scores as a real-env touch).
# That is an ADVISORY over-trigger (never a silent miss), the behavior is
# intentionally unchanged; a negation-window / quote-aware pass is a future
# iteration.
_REAL_ENV_TEXT_RE = re.compile(
    r"(真实安装|真实环境|真机|用户\s*HOME|HOME\s*下|用户真实环境|"
    r"\$DSH_HOME|\$HOME|%USERPROFILE%|%APPDATA%|~/[^\s，。；)）])",
    re.IGNORECASE)

# Outside-repo effect wording — the R2 enumeration: installer execution /
# real profile write / network publishing. The R5-standard wording
# 「隔离环境安装冒烟（环境变量重定向至临时目录）」matches here as an
# outside-repo effect (installer execution, declaration duty) but contains
# no real-env banned wording, so R1 is NOT triggered — isolation
# qualifiers never neutralize the banned words themselves (R5's point is
# to use the standard wording, not qualified real-env wording).
_OUTSIDE_REPO_TEXT_RE = re.compile(
    r"(安装冒烟|安装器|installer|profile\s*写入|网络发布|npm\s+publish)",
    re.IGNORECASE)

# R1 review condition auto-attached to every user-real-environment touch.
_R1_REVIEW_CONDITION = (
    "须满足 R1（三选一：隔离环境重定向 / 事先完整备份+一致性校验 / "
    "用户 ask_user_question 逐项授权）并留痕"
    "（behavior-protocol.md M7.7 / AUDIT-146 / FIX-271）")


def analyze_side_effects(files, reason="", acceptance="", declared=""):
    """Step e — execution side-effect declaration analysis (pure, no I/O).

    Scans the triage inputs (``files`` / rationale / acceptance wording)
    for outside-repo side-effect signals:

      - a file outside the repository (absolute path, UNC /
        single-backslash root, ``~``, ``$VAR``, ``%VAR%``, parent escape)
        is an outside-repo side effect — BOTH the raw string and its
        normalized (backslash → slash) form participate in this judgement
        (FIX-273 P2-1), so no rendering of the same path escapes
        classification. Home-tree / env-var targets additionally count as
        a user REAL-environment touch;
      - R5-banned unqualified wording（真实安装/真实环境/真机/...）in the
        rationale or acceptance is a user REAL-environment touch;
      - installer / network-publish / profile-write wording is an
        outside-repo side effect even when properly isolated (R5 standard
        wording「隔离环境安装冒烟…临时目录…」stays NON-real-env).

    **Wording-detection limitation (FIX-273 P2-2)** — the wording signal is
    context-blind by design: it does NOT parse negation or quotation, so a
    banned-word substring triggers in ANY context (e.g. 「禁止修改
    %USERPROFILE%」, or quoting R5 rule text, still classifies as a
    real-env touch). This is an ADVISORY over-trigger (never a silent
    miss), it adds R1 condition noise but never blocks; the behavior is
    intentionally unchanged and a negation-window / quote-aware pass is a
    future iteration. **File-side detection** (absolute/UNC/``~``/escape
    shapes) is NOT affected by this limitation — it is shape-based, not
    wording-based.

    Args:
        files: product files the task will modify.
        reason: triage rationale text.
        acceptance: acceptance-criteria text (R5 wording detection input).
        declared: the task's side-effect declaration (surface + blast
            radius). Non-empty satisfies the declaration duty.

    Returns:
        dict ``{"detected", "touches_real_env", "requires_r1",
        "declared", "blast_radius", "review_conditions", "issues"}``.
        ``issues`` holds WARN strings (advisory — WARN 起步，不得静默);
        a real-env touch always carries the R1 review condition.
    """
    files = [str(f) for f in (files or []) if str(f).strip()]
    declared = str(declared or "").strip()

    blast_radius = []
    real_env = False
    outside_repo = False

    for f in files:
        normalized = f.replace("\\", "/")
        # Both the raw string AND the normalized form participate in the
        # outside-repo judgement (FIX-273 P2-1): backslash-rooted forms
        # (UNC `\\server\share`, single-backslash roots `\Users\...`) match
        # the ``\\`` branch raw, `/`-rooted forms match after normalization
        # — the dual check mirrors the real-env dual search below so no
        # rendering of the same path escapes classification.
        if _OUTSIDE_REPO_FILE_RE.match(f) or _OUTSIDE_REPO_FILE_RE.match(
                normalized):
            outside_repo = True
            if _REAL_ENV_FILE_RE.search(f) or _REAL_ENV_FILE_RE.search(
                    normalized):
                real_env = True
                blast_radius.append(
                    "用户真实环境文件目标（HOME/环境变量重定向）：{0}".format(f))
            else:
                blast_radius.append(
                    "仓库外文件目标（绝对路径/父目录逃逸）：{0}".format(f))

    blob = "{0} {1}".format(str(reason or ""), str(acceptance or ""))
    matched_real = sorted({m.group(0) for m in
                           _REAL_ENV_TEXT_RE.finditer(blob)})
    matched_outside = sorted({m.group(0) for m in
                              _OUTSIDE_REPO_TEXT_RE.finditer(blob)})

    if matched_real:
        real_env = True
        outside_repo = True
        blast_radius.append(
            "输入含真实环境操作措辞（R5 禁令词）：{0}".format(
                "、".join(matched_real)))
    if matched_outside:
        outside_repo = True
        blast_radius.append(
            "输入含仓库外副作用措辞（安装器/发布/profile 写入）：{0}".format(
                "、".join(matched_outside)))

    issues = []
    if outside_repo and not declared:
        issues.append(
            "WARN: R2 执行副作用声明缺失——triage 输入检测到仓库外副作用"
            "信号（{0}）但未声明副作用面与爆炸半径（--side-effects；"
            "AUDIT-146 / FIX-271）".format("；".join(blast_radius)))
    if real_env and not declared:
        issues.append(
            "WARN: 触及用户真实环境——未声明且须满足 R1（三选一）方可执行"
            "（AUDIT-146 / FIX-271 / behavior-protocol.md M7.7）")

    review_conditions = [_R1_REVIEW_CONDITION] if real_env else []

    return {
        "detected": outside_repo,
        "touches_real_env": real_env,
        "requires_r1": real_env,
        "declared": declared,
        "blast_radius": blast_radius,
        "review_conditions": review_conditions,
        "issues": issues,
    }


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


# ─── FEAT-013 (RISK-046 root-cause fix) — dispatch-lock write API ───────────


def _normalize_lock_path(path) -> str:
    """Repo-relative lock key: backslash → slash, trimmed."""
    return str(path or "").replace("\\", "/").strip()


def cross_check_triage_files(task_id, lock_files, records, today):
    """FEAT-013 face 2 (pure) — same-day change-triage files cross-check.

    RISK-046 ②: the hand-assembled lock file set could drift from the
    same-day triage record's ``files`` declaration with no detection.
    When a change-triage record exists for ``task_id`` AND its
    ``created_at`` equals ``today`` (同期=当日), the declared file sets
    are compared (case-insensitive, slash-normalized).

    Args:
        task_id: the dispatch-lock task id.
        lock_files: the lock file set about to be written.
        records: triage records (list of dicts,
            :func:`load_triage_records` shape).
        today: ISO date string the lock write happens on.

    Returns:
        None when there is no same-day record for the task (silent —
        nothing to cross-check), else a dict with ``triage_created_at``,
        ``triage_files``, ``lock_files``, ``lock_only``, ``triage_only``
        and ``matches``.
    """
    def _norm(path):
        return _normalize_lock_path(path).lower()

    record = None
    for candidate in records or []:
        if str(candidate.get("task_id", "")) == str(task_id):
            record = candidate
            break
    if record is None:
        return None
    created_at = str(record.get("created_at", ""))
    if created_at != str(today):
        return None
    triage_files = sorted({
        _norm(f) for f in (record.get("files") or [])
        if _normalize_lock_path(f)})
    lock_set = sorted({
        _norm(f) for f in (lock_files or []) if _normalize_lock_path(f)})
    lock_only = sorted(set(lock_set) - set(triage_files))
    triage_only = sorted(set(triage_files) - set(lock_set))
    return {
        "task_id": str(task_id),
        "triage_created_at": created_at,
        "triage_files": triage_files,
        "lock_files": lock_set,
        "lock_only": lock_only,
        "triage_only": triage_only,
        "matches": not lock_only and not triage_only,
    }


def acquire_dispatch_locks(*, task_id, files, expected_new=None,
                           agent_role="Developer", coordinator_session="",
                           description="",
                           ttl_seconds=DEFAULT_LOCK_TTL_SECONDS,
                           ttl_reason="", governance_dir, repo_root=None,
                           now=None, locks_path=None) -> dict:
    """FEAT-013 — machine dispatch-lock acquisition with write-time checks.

    RISK-046 root cause: the Coordinator hand-assembled
    ``agent-locks.json`` with no write-time validation, so a typo'd /
    placeholder / not-yet-created path entered ``file_locks`` directly
    (a lock on a nonexistent file protects nothing once the real file
    appears), and the lock set could drift from the same-day triage
    record's ``files``. This API is the only sanctioned acquisition path
    (CLI ``agent-locks-acquire``; the dispatch template forbids
    hand-writing the lock file).

    Validation order (fail-closed — NOTHING is written on any error):

      1. task id shape (``PREFIX-NNN``), non-empty file list,
         ``expected_new`` ⊆ ``files``, positive integer TTL;
      2. the existing lock file must be structurally sane (valid JSON,
         dict ``active_tasks`` / ``file_locks``) — a corrupt file is
         never merged into;
      3. duplicate-task guard — the task must not already hold an
         active lock (release first, M7.6a);
      4. cross-task conflict guard — a target already locked by another
         active task is refused (the writer never creates the
         ``multi_lock_conflict`` Check 26 flags as BLOCKING);
      5. **face 1** path existence — every target must be an existing
         file under ``repo_root`` unless declared in ``expected_new``
         (the pre-created-file exemption, persisted as
         ``expected_new: true`` on that lock entry);
      6. **face 2** same-day cross-check — a ``files`` mismatch against
         the same-day triage record is a WARN in the returned summary
         (disclosed by the CLI on stderr; NEVER blocking: triage
         precedes the lock and the lock may legitimately carry
         dispatch-preauthorized extensions — the drift must be SEEN).

    Args:
        task_id: dispatch task id (PREFIX-NNN).
        files: repo-relative lock targets (backslashes normalized).
        expected_new: subset of ``files`` the task will create (not on
            disk yet) — the RISK-046 ① exemption channel.
        agent_role / coordinator_session / description: active_tasks
            entry metadata (Check 26 required fields included).
        ttl_seconds / ttl_reason: file_locks TTL fields.
        governance_dir: ``.governance`` directory (locks + triage
            records live under it).
        repo_root: base for existence checks (default: cwd).
        now: injectable clock (tests); default ``datetime.now()``.
        locks_path: explicit lock-file override (tests).

    Returns:
        dict summary (``locks_path`` / ``lock_files`` / ``expected_new``
        / ``cross_check`` / ``warnings`` / ``written``); ``error`` key
        present on fail-closed input. Never raises.
    """
    task_id = str(task_id or "").strip()
    if not _TASK_ID_RE.match(task_id):
        return {"error": "task_id must match PREFIX-NNN (e.g. FIX-210)"}

    lock_files = [_normalize_lock_path(f) for f in (files or [])]
    lock_files = [f for f in lock_files if f]
    if not lock_files:
        return {"error": "files is required and must be non-empty — a "
                         "dispatch lock without targets is RISK-046 drift"}
    new_files = {_normalize_lock_path(f) for f in (expected_new or [])}
    new_files.discard("")
    unknown = sorted(new_files - set(lock_files))
    if unknown:
        return {"error": "expected_new must be a subset of files — "
                         "undeclared target(s): {0}".format(
                             ", ".join(unknown))}

    try:
        ttl_seconds = int(ttl_seconds)
    except (TypeError, ValueError):
        return {"error": "ttl_seconds must be an integer"}
    if ttl_seconds <= 0:
        return {"error": "ttl_seconds must be positive (got {0})".format(
            ttl_seconds)}

    if locks_path is None:
        locks_path = Path(governance_dir) / LOCK_FILE_NAME
    locks_path = Path(locks_path)

    data = {"active_tasks": {}, "file_locks": {}}
    if locks_path.is_file():
        try:
            loaded = json.loads(locks_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return {"error": "agent-locks.json is unreadable ({0}) — "
                             "refusing to merge fail-closed; fix or remove "
                             "the file first".format(exc)}
        if not isinstance(loaded, dict):
            return {"error": "agent-locks.json root must be a JSON object "
                             "— refusing to merge fail-closed"}
        for key in ("active_tasks", "file_locks"):
            value = loaded.get(key, {})
            if not isinstance(value, dict):
                return {"error": "agent-locks.json '{0}' must be a JSON "
                                 "object — refusing to merge "
                                 "fail-closed".format(key)}
            data[key] = dict(value)

    if task_id in data["active_tasks"]:
        return {"error": "task {0} already holds an active dispatch lock "
                         "— release it before re-acquiring (M7.6a)".format(
                             task_id)}

    held = []
    for f in lock_files:
        entry = data["file_locks"].get(f)
        if (isinstance(entry, dict)
                and entry.get("locked_by")
                and entry.get("locked_by") != task_id):
            held.append("{0} (locked_by {1})".format(
                f, entry.get("locked_by")))
    if held:
        return {"error": "file lock conflict — target(s) already locked by "
                         "another active task: {0}; serialize or isolate "
                         "(worktree) per M7.6".format("; ".join(held))}

    # Face 1 — pre-write path existence validation (RISK-046 ①).
    repo_root = Path(repo_root) if repo_root is not None else Path.cwd()
    missing = [f for f in lock_files
               if f not in new_files and not (repo_root / f).is_file()]
    if missing:
        return {"error": "lock target(s) do not exist as files — {0}. "
                         "先创建文件或修正路径；若该文件是本任务将新建的预创建"
                         "目标，须显式声明 expected_new（CLI --expected-new，"
                         "锁条目落 expected_new: true）——FEAT-013 / RISK-046 "
                         "写前校验：拒绝锁定不存在的路径".format(
                             "; ".join(missing))}

    # Face 2 — same-day change-triage files cross-check (RISK-046 ②).
    moment = now if now is not None else datetime.now()
    today = moment.date().isoformat()
    cross = cross_check_triage_files(
        task_id, lock_files, load_triage_records(governance_dir), today)
    warnings = []
    if cross is not None and not cross["matches"]:
        warnings.append(
            "WARN: 派发锁 files 与同期 change-triage 记录（change-triage/"
            "{0}.json，created_at {1}）不一致——锁独有: {2}；triage 独有: "
            "{3}（advisory 不阻断：triage 先于锁且锁可含派发预授权扩展，"
            "差异需人看见——RISK-046 / FEAT-013）".format(
                task_id, cross["triage_created_at"],
                ", ".join(cross["lock_only"]) or "—",
                ", ".join(cross["triage_only"]) or "—"))

    timestamp = moment.replace(microsecond=0).isoformat()
    data["active_tasks"][task_id] = {
        "agent_role": str(agent_role or ""),
        "spawned_at": timestamp,
        "coordinator_session": str(coordinator_session or ""),
        "target_files": list(lock_files),
        "description": str(description or ""),
        "acquired": timestamp,
        "files": list(lock_files),
    }
    for f in lock_files:
        entry = {
            "locked_by": task_id,
            "locked_at": timestamp,
            "ttl_seconds": ttl_seconds,
            "ttl_reason": str(ttl_reason or ""),
        }
        if f in new_files:
            entry["expected_new"] = True
        data["file_locks"][f] = entry

    try:
        locks_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=4) + "\n",
            encoding="utf-8")
    except OSError as exc:
        return {"error": "cannot write agent-locks.json: {0}".format(exc)}

    return {
        "task_id": task_id,
        "locks_path": str(locks_path),
        "lock_files": list(lock_files),
        "expected_new": sorted(new_files),
        "active_task_count": len(data["active_tasks"]),
        "file_lock_count": len(data["file_locks"]),
        "cross_check": cross,
        "warnings": warnings,
        "written": True,
    }


def agent_locks_acquire_cli(args, *, governance_dir, repo_root,
                            post_write_check=None):
    """FEAT-013 thin-entry glue — the ``agent-locks-acquire`` CLI body.

    All validation/writing lives in :func:`acquire_dispatch_locks`; this
    glue parses the comma lists, prints the JSON summary, discloses WARNs
    on stderr (WARN 起步，不得静默 — never silent, never blocking) and
    exits 2 fail-closed on any error. ``post_write_check`` (injected by
    the engine wrapper = ``verify_workflow.check_agent_locks_format``,
    Check 26) re-validates the just-written file — the writer proves its
    own output against the SAME schema the FEAT-011 guard consumes (no
    second schema definition); a post-write violation also exits 2.
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    def _split(raw):
        return [f for f in str(raw or "").replace(";", ",").split(",")
                if f.strip()]

    summary = acquire_dispatch_locks(
        task_id=getattr(args, "task", ""),
        files=_split(getattr(args, "files", "")),
        expected_new=_split(getattr(args, "expected_new", "")),
        agent_role=getattr(args, "role", "") or "Developer",
        coordinator_session=getattr(args, "session", "") or "",
        description=getattr(args, "description", "") or "",
        ttl_seconds=getattr(args, "ttl", DEFAULT_LOCK_TTL_SECONDS),
        ttl_reason=getattr(args, "ttl_reason", "") or "",
        governance_dir=governance_dir,
        repo_root=repo_root,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary.get("error"):
        sys.exit(2)
    for warning in summary.get("warnings", []):
        print(warning, file=sys.stderr)
    if post_write_check is not None:
        issues = post_write_check()
        if issues:
            for issue in issues:
                print("agent-locks-acquire write guard: {0}".format(
                    issue.get("detail", issue)), file=sys.stderr)
            print("agent-locks-acquire write guard: the just-written "
                  "agent-locks.json violates the Check 26 schema — fix the "
                  "input and re-run; nothing else was written",
                  file=sys.stderr)
            sys.exit(2)


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
        "change-triage CLI 机器写入 triage 记录（依赖/优先级/冲突/版本/执行副作用五步分析）",
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
               acceptance: str = "", declared_side_effects: str = "",
               plan_tracker_text: str, current_version: str = "",
               governance_dir, existing_records=None, records_dir=None,
               evidence_path=None) -> dict:
    """Run the mandatory five-step triage and write the machine record.

    Fail-closed: any step-ERROR (unknown dependency, invalid priority, empty
    files, stale target version, new-task cycle, malformed task id) returns
    ``{"error": ...}`` and writes NOTHING — no record, no evidence row.
    Step-e (side-effect) issues are WARN (advisory): they land in the
    record and the summary but never block (WARN 起步，不得静默).

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
        acceptance: acceptance-criteria text — step-e input for R5 wording
            detection (FIX-271 / AUDIT-146 §7.2 R2/R5).
        declared_side_effects: side-effect declaration (surface + blast
            radius) — satisfies the step-e declaration duty for
            outside-repo side effects (R2).
        plan_tracker_text: raw plan-tracker markdown.
        current_version: the PROJECT's current version — the plan-tracker
            roadmap's highest released row
            (:func:`derive_project_current_version`; FIX-288 two-layer
            semantics — not the workflow/plugin version).
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

    # Step e (FIX-271 / AUDIT-146 §7.2 R2): execution side-effect
    # declaration — purely additive analysis appended AFTER the four
    # legacy step keys (backward-compat hard constraint: the four-step
    # serialized prefix stays byte-identical).
    side_effect = analyze_side_effects(
        files, reason=reason, acceptance=acceptance,
        declared=declared_side_effects)

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
            "side_effect": side_effect,
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
    "LOCK_FILE_NAME",
    "DEFAULT_LOCK_TTL_SECONDS",
    "split_dep_ids",
    "run_dependency_analysis",
    "parse_version_chain",
    "derive_project_current_version",
    "analyze_priority_context",
    "validate_version",
    "check_conflicts",
    "analyze_side_effects",
    "load_triage_records",
    "cross_check_triage_files",
    "acquire_dispatch_locks",
    "agent_locks_acquire_cli",
    "run_triage",
]
