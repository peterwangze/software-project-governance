#!/usr/bin/env python3
"""Task dependency / priority analysis — FIX-226 (0.71.0).

This module is the **pure dependency-analysis layer** for the governance
plan-tracker. It parses the ``优先级一览`` priority tables in
``plan-tracker.md``, builds a directed acyclic graph (DAG) from the ``依赖``
(dependency) column, and computes which tasks are blocked / unblocked / ready
to recommend as the next step.

It exists to close the AUDIT-141 / FIX-223 gap: the ``依赖`` column was
free-text with no machine-parseable graph and no "what's unblocked" computation,
so the behavior protocol could not honor its own rule (analyze dependencies
before recommending next steps). This tool provides that analysis.

**Third-class status filter (FIX-237.2 / ADR-017 §4.4 P1-3):** dependency
satisfaction alone does NOT make a row an executable candidate. Only rows whose
status leading marker is ⏳ (pending/active) — or which have no leading status
marker at all — may enter ``Unblocked`` / ``Recommended next``. Rows with a
terminal / non-executable leading marker (⛔ blocked, ⏸ split/held, 🔴 blocked,
🚧 historical in-progress, 🛑 stopped, 📋 queued, ✅ completed) are excluded
even when dependency-satisfied and reported in a separate ``non_executable``
bucket.

**Cycle tolerance (FIX-237.2):** a dependency cycle is a WARNING, not an ERROR.
The report keeps the cycle list for visibility, sets the ``cycle_warning``
flag, formats a ``CYCLE DETECTED (WARNING)`` banner, and still produces the
best-effort analysis.

**Purity contract (load-bearing):** this module imports ONLY the Python
standard library. The compute functions (:func:`parse_task_dependencies`,
:func:`compute_unblocked_tasks`, :func:`format_report`) perform NO file I/O and
hold NO module-level mutable state. The CLI entry in ``verify_workflow.py`` is
the only place that reads ``plan-tracker.md`` from disk; it passes the file
*text* to :func:`parse_task_dependencies`. This makes the analysis trivially
testable with fixture strings and deterministic across runs.

**Task-family vs cross-entity (FIX-171 precedent):** the ``依赖`` column
routinely mixes task-family IDs (``FIX-162``, ``REL-047``, ``AUDIT-124`` —
things that can appear as Task IDs and therefore have a status) with
cross-entity reference IDs (``RISK-039``, ``DEC-090``, ``REVIEW-FIX-155`` —
descriptive context that is NEVER a task and has no status). Only task-family
dependencies can block a task; a cross-entity ref is descriptive and never
blocks. This mirrors the AUDIT-126 / FIX-171 fix in ``archive.py``.

Usage::

    from task_priority import parse_task_dependencies, compute_unblocked_tasks, format_report
    text = Path(".governance/plan-tracker.md").read_text(encoding="utf-8")
    tasks = parse_task_dependencies(text)
    report = compute_unblocked_tasks(tasks)
    print(format_report(report))
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


__version__ = "0.71.0"

# ─────────────────────────────────────────────────────────────────────────────
# Task-family classification (FIX-171 precedent; mirrored from archive.py)
# ─────────────────────────────────────────────────────────────────────────────
#
# These are the prefixes that can appear as Task IDs in plan-tracker and
# therefore can resolve to a status (completed / active). Everything else in
# the ``依赖`` column is a cross-entity reference (RISK / DEC / REVIEW / EVD /
# TIER / CONSTRAINT / TOOL / ADR) — descriptive context that never blocks.
#
# Kept as a local copy (rather than importing archive.py) so this module stays
# pure-stdlib with no peer coupling, and so the allow-list is self-documenting
# for the priority-analysis use case. Conservative: when uncertain, INCLUDE a
# prefix — a non-task ID in this set simply matches nothing in the status map
# (no false block). The list below was derived from the real governance data
# (prefixes that appear as Task IDs in plan-tracker table rows). ``FEAT`` and
# ``DOC`` are included because the live plan-tracker uses them as task IDs
# (FEAT-001..009, DOC-001); ``VAL`` likewise (VAL-007..009).
_TASK_FAMILY_PREFIXES = frozenset({
    "FIX", "REL", "AUDIT", "REQ", "FMT", "DIAG", "MAINT", "SYSGAP", "TD",
    "DESIGN", "VAL", "CLEANUP", "PRINCIPLE", "TASK", "RESEARCH", "ACCEPT",
    "INIT", "PLAN", "FEAT", "DOC",
})

# Cross-entity prefixes — NEVER task IDs, never block. Documented for clarity;
# the task-family allow-list above is authoritative.
_CROSS_ENTITY_PREFIXES = frozenset({
    "RISK", "DEC", "REVIEW", "EVD", "TIER", "CONSTRAINT", "TOOL", "ADR",
})

# A task-family or cross-entity ID token: PREFIX-NNN (e.g. FIX-226, RISK-039).
# The negative lookbehind ``(?<![-A-Z])`` is load-bearing: without it the regex
# would extract ``FIX-155`` from inside ``REVIEW-FIX-155`` (the ``-`` before
# ``FIX`` is a non-word boundary, so plain ``\b`` would still match). A
# REVIEW-prefixed ref is a single cross-entity record (the review of FIX-155),
# NOT the FIX-155 task itself, and must not be re-counted as a task dependency.
# Forbidding a preceding ``-`` or uppercase letter correctly treats
# ``REVIEW-FIX-155`` as a single token whose prefix is ``REVIEW`` (cross-entity)
# while still matching a standalone ``FIX-155``.
_ID_TOKEN_RE = re.compile(r"(?<![-A-Z])([A-Z]+)-(\d+)\b")
# A bare ID cell value (after stripping markdown), e.g. "FIX-226".
_ID_CELL_RE = re.compile(r"^[A-Z]+-\d+$")


def _is_task_family_id(task_id: str) -> bool:
    """Return True if ``task_id``'s prefix is a task-family prefix.

    A task-family ID is one that can appear as a Task ID in plan-tracker and
    therefore can resolve to a status. Cross-entity refs (RISK-/DEC-/REVIEW-/
    EVD-/TIER-/CONSTRAINT-/TOOL-/ADR-) are descriptive context, never tasks,
    and must NOT block.

    Args:
        task_id: an ID string of the form ``PREFIX-NNN``. The caller
            pre-validates the shape; this function only inspects the prefix.

    Returns:
        True if the prefix is in :data:`_TASK_FAMILY_PREFIXES`, False otherwise.
    """
    prefix = task_id.split("-", 1)[0]
    return prefix in _TASK_FAMILY_PREFIXES


# ─────────────────────────────────────────────────────────────────────────────
# Status parsing
# ─────────────────────────────────────────────────────────────────────────────
#
# The plan-tracker ``状态`` cell is the LAST data column of the 7-col priority
# table. Real cells observed in the live data:
#   "✅ 完成 (2026-06-30)"
#   "✅ 已交付"
#   "✅ 已发布 (2026-07-25)——origin/master=..."
#   "⏸ 停滞待重新评估 (2026-06-27)"
#   "🚧 前向门禁完成，历史处置待 DEC (2026-07-11)"
#   "⛔ BLOCKED_BY FIX-212/FIX-202 (2026-07-17)"
#   "⏳ 待执行"
#   "🔴 ..." (blocked)
#   "⏸ SPLIT_TO FIX-199/FIX-200 (2026-07-13)"
#
# Rule (per FIX-226 spec): ✅ = completed; ANY other status = active (i.e. the
# task is not done, so it counts as a blocker for dependents and as a
# candidate for unblocked/recommended). We match on the leading ✅ emoji
# specifically, NOT a substring scan of the whole cell — because the cell may
# contain ✅ inside a parenthetical (e.g. "FIX-155✅" appears in the DEPENDENCY
# column, not status; but defensive). The status cell is leading-emoji driven.
_COMPLETED_EMOJI = "✅"
# Active (non-completed) markers — informational only; the rule is "not ✅ →
# active". Listed here so the docstring / format output can label sub-states.
_ACTIVE_STATUS_HINTS = {
    "⏳": "pending",
    "🔴": "blocked",
    "🚧": "in_progress",
    "🛑": "stopped",
    "⏸": "paused",
    "⛔": "blocked",
}


def _status_is_completed(status_cell: str) -> bool:
    """Return True if the status cell indicates the task is completed.

    Completed = the cell contains the ✅ emoji. This is the single reliable
    signal across all observed plan-tracker status variants (✅ 完成 / ✅ 已交付 /
    ✅ 已发布 / ✅ 代码完成 / ✅ 设计完成 / ✅ ACCEPTED / etc.). Any cell without ✅
    is treated as active (pending / blocked / in-progress / paused / stopped),
    which means the task still blocks its dependents.
    """
    return _COMPLETED_EMOJI in status_cell


# Third-class status filter (FIX-237.2 / ADR-017 §4.4 P1-3).
#
# A row may enter "Unblocked (ready to work)" / "Recommended next" ONLY when
# its status leading marker is ⏳ (pending/active) or the cell has no leading
# marker. Terminal / non-executable markers are excluded even when the row's
# dependencies are satisfied, because the status records a deliberate stop
# (blocked / split / held / historical in-progress terminal / completed) that
# dependency analysis cannot override.
#
# The marker set reuses the module's existing status classification
# (_ACTIVE_STATUS_HINTS) minus ⏳, plus ✅ (defense-in-depth — completed rows
# are excluded upstream by _status_is_completed and never reach this
# predicate) and 📋 (待启动 queued rows, which are not yet executable).
_NON_CANDIDATE_MARKERS = frozenset(
    {marker for marker in _ACTIVE_STATUS_HINTS if marker != "⏳"}
) | {"✅", "📋"}


def _status_is_candidate_eligible(status_cell: str) -> bool:
    """Return True if the status cell permits the row to be an executable candidate.

    Third-class status filter (FIX-237.2 / ADR-017 §4.4 P1-3): a not-completed
    row whose dependencies are all satisfied may enter the unblocked /
    recommended-next candidate lists ONLY when its status leading marker is ⏳
    (pending/active) or the cell has no leading status marker. Rows whose
    leading marker is terminal / non-executable (⛔ ⏸ 🔴 🚧 🛑 📋 ✅) are
    non-candidates even when dependency-satisfied.

    Completed rows (✅) are excluded upstream by :func:`_status_is_completed`
    and never reach this predicate; the ✅ branch here is defense-in-depth.

    Args:
        status_cell: the RAW status cell text (e.g. ``"⏳ 待执行"``).

    Returns:
        True when the row may be an executable candidate, False otherwise.
    """
    s = status_cell.strip()
    if not s:
        # Empty / no status → no leading marker → eligible (the dependency
        # analysis decides candidacy).
        return True
    if s.startswith("⏳"):
        return True
    return not s.startswith(tuple(_NON_CANDIDATE_MARKERS))


# ─────────────────────────────────────────────────────────────────────────────
# Priority parsing
# ─────────────────────────────────────────────────────────────────────────────
# The priority cell is ``**P0**`` / ``**P1**`` / ``**P2**`` (markdown bold) or
# bare ``P0``/``P1``/``P2``, or ``—`` (no priority, used in the archived-version
# pointer table). Lower rank number = higher priority (P0 < P1 < P2).
_PRIORITY_RE = re.compile(r"\bP([012])\b", re.IGNORECASE)
_NO_PRIORITY_SENTINEL = "P9"  # sorts last (lowest priority)


def _parse_priority(cell: str) -> str:
    """Extract a priority label (``P0`` / ``P1`` / ``P2``) from a cell.

    Returns the canonical uppercase label, or :data:`_NO_PRIORITY_SENTINEL`
    (``P9``) when the cell has no priority (``—`` or empty). ``P9`` is a sentinel
    that sorts after every real priority so unprioritized tasks never preempt
    real P0/P1/P2 work in :func:`_priority_sort_key`.
    """
    m = _PRIORITY_RE.search(cell)
    if m:
        return "P" + m.group(1)
    return _NO_PRIORITY_SENTINEL


# ─────────────────────────────────────────────────────────────────────────────
# Version parsing (for the recommended-next tie-break)
# ─────────────────────────────────────────────────────────────────────────────
_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def _version_tuple(version_str: str) -> tuple:
    """Parse ``"0.71.0"`` → ``(0, 71, 0)`` for sort/comparison.

    Returns ``(inf, 0, 0)`` (sorts last) when the string has no parseable
    semver — covers ``—``, ``未规划版本``, ``未定版本（设计审查后定）``, ``0.66.2（暂定）``
    (the bare parenthetical is handled: we extract the first x.y.z token, so
    ``0.66.2（暂定）`` → ``(0,66,2)``). The sentinel ensures non-versioned tasks
    never preempt versioned work in the recommended-next tie-break.
    """
    if not version_str:
        return (float("inf"), 0, 0)
    m = _VERSION_RE.search(version_str)
    if not m:
        return (float("inf"), 0, 0)
    return tuple(int(p) for p in m.groups())


# ─────────────────────────────────────────────────────────────────────────────
# Table-row parsing
# ─────────────────────────────────────────────────────────────────────────────
# The priority table header is:
#     | 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
# Data rows look like:
#     | **P0** | FIX-225 | plan-tracker 依赖列结构化 + 模板升级 | AUDIT-141✅ | 0.71.0 | 产品代码+治理记录... | ⏳ 待执行 |
#     | — | FIX-082 | Runtime capability contract（0.38.0 发布链）| AUDIT-102 | 0.38.0 | 已归档至 ... | ✅ 已交付 |
# The malformed rows at live lines 174-176 have an extra leading **P0** cell
# (| **P0** | **P0** | FIX-222 | ...). The parser MUST be robust to this: it
# locates columns by the HEADER row, not by hardcoded indices, and it locates
# the ID cell as the first data cell matching the bare-ID pattern as a fallback.

# Separator row: | --- | --- | ... | (possibly with : for alignment).
_SEPARATOR_RE = re.compile(r"^\|[\s\-:|\t]+\|$")


def _split_row(line: str) -> list:
    """Split a markdown table row into trimmed data cells (no leading/trailing empty)."""
    parts = [p.strip() for p in line.split("|")]
    # parts[0] and parts[-1] are empty (the text outside the leading/trailing |).
    if len(parts) >= 2 and parts[0] == "" and parts[-1] == "":
        return parts[1:-1]
    return parts


def _strip_markdown(s: str) -> str:
    """Strip markdown emphasis (`` ` `` and ``*``) from a cell value."""
    return re.sub(r"[`*]", "", s).strip()


def _parse_dependency_cell(cell: str) -> tuple:
    """Parse a ``依赖`` cell into ``(task_family_ids, cross_entity_ids)``.

    The cell may contain:
      - task IDs: ``FIX-162,REL-047`` (task-family, block)
      - cross-entity refs: ``RISK-039,DEC-090`` (descriptive, never block)
      - status markers glued to IDs: ``FIX-155✅`` (the ✅ is a dependency-state
        hint, NOT the dependent's status — we strip it and keep the ID)
      - REVIEW-prefixed refs: ``REVIEW-FIX-155`` (cross-entity per FIX-171;
        REVIEW is a review record, not a task)
      - prose / version strings: ``用户反馈4问题(1/2/3)``, ``v2设计方案``,
        ``DEC-088, DEC-085/086/087(授权沿用)`` — the ID-token regex extracts the
        PREFIX-NNN tokens and ignores the surrounding prose
      - ``—`` (em-dash, no dependencies)

    Returns two de-duplicated tuples preserving first-seen order:
      - task_family_ids: PREFIX-NNN whose prefix is in _TASK_FAMILY_PREFIXES
      - cross_entity_ids: PREFIX-NNN whose prefix is NOT task-family
    """
    task_family = []
    cross_entity = []
    seen = set()
    for m in _ID_TOKEN_RE.finditer(cell):
        tid = f"{m.group(1)}-{m.group(2)}"
        if tid in seen:
            continue
        seen.add(tid)
        if _is_task_family_id(tid):
            task_family.append(tid)
        else:
            cross_entity.append(tid)
    return tuple(task_family), tuple(cross_entity)


@dataclass(frozen=True)
class TaskDep:
    """One task row parsed from the plan-tracker priority table.

    Attributes:
        task_id: the task ID (e.g. ``FIX-226``).
        priority: ``P0`` / ``P1`` / ``P2`` / ``P9`` (P9 = no priority / unprioritized,
            used by the archived-version pointer table; sorts last).
        status: the RAW status cell text (e.g. ``"✅ 完成 (2026-06-30)"`` or
            ``"⏳ 待执行"``). Use :func:`is_completed` to interpret.
        dependencies: TASK-FAMILY IDs this task depends on (only these can
            block). Cross-entity refs (RISK/DEC/REVIEW/...) are filtered out —
            they are descriptive context, never blockers.
        cross_entity_refs: cross-entity IDs found in the ``依赖`` cell (RISK/
            DEC/REVIEW/EVD/...). Carried for reporting only; never blocks.
        target_version: the ``目标版本`` cell text (e.g. ``"0.71.0"`` or ``"—"``).
    """

    task_id: str
    priority: str
    status: str
    dependencies: tuple = ()
    cross_entity_refs: tuple = ()
    target_version: str = ""

    def is_completed(self) -> bool:
        """True if this task's status indicates completion (contains ✅)."""
        return _status_is_completed(self.status)


@dataclass(frozen=True)
class BlockedTask:
    """A task that is blocked by at least one incomplete task-family dependency.

    Attributes:
        task: the blocked :class:`TaskDep`.
        blocking_dependencies: the task-family dependency IDs that are NOT
            completed (these are the specific unresolved blockers, e.g.
            ``["FIX-212", "FIX-202"]``). A dependency that is missing from the
            table entirely (unknown ID) is also listed here — an unknown
            task-family ID cannot be proven complete, so it blocks
            fail-closed (matches the FIX-171 conservative default).
    """

    task: TaskDep
    blocking_dependencies: tuple = ()


@dataclass(frozen=True)
class PriorityReport:
    """The full dependency-analysis result.

    Attributes:
        completed: tasks whose status is ✅.
        blocked: tasks with at least one incomplete task-family dependency.
        unblocked: tasks that are NOT completed AND whose ALL task-family
            dependencies are completed (or have none). These are ready to work.
        recommended_next: the highest-priority ``unblocked`` tasks, sorted by
            priority (P0 > P1 > P2) then target_version (ascending). Typically
            the single best next step is ``recommended_next[0]``.
        total: total number of tasks parsed.
        dependency_graph: ``{task_id: (task_family_dependency_ids, ...)}`` for
            every parsed task. Useful for downstream tooling / visualization.
        non_executable: tasks that are NOT completed, have ALL task-family
            dependencies satisfied (or none), but are excluded from the
            unblocked / recommended-next candidates by the third-class status
            filter (leading marker ⛔/⏸/🔴/🚧/🛑/📋/✅ — FIX-237.2 / ADR-017
            §4.4 P1-3). Reported separately so filtered rows stay visible.
        cycles: list of cycles detected in the dependency graph (each a tuple
            of task IDs forming the cycle, e.g. ``("FIX-A","FIX-B","FIX-A")``).
            Empty when the graph is acyclic. When non-empty, the report is still
            produced and :func:`format_report` flags it as a WARNING (cycle
            tolerance — FIX-237.2).
        cycle_warning: True when the dependency graph contains at least one
            cycle. This is a WARN flag, never an ERROR: the analysis output is
            best-effort and is not blocked by the cycle. Downstream consumers
            (e.g. the CLI exit code) should switch on this flag once they stop
            treating cycles as fatal (verify_workflow.py integration).
    """

    completed: list = field(default_factory=list)
    blocked: list = field(default_factory=list)  # list[BlockedTask]
    unblocked: list = field(default_factory=list)  # list[TaskDep]
    recommended_next: list = field(default_factory=list)  # list[TaskDep]
    total: int = 0
    dependency_graph: dict = field(default_factory=dict)
    cycles: list = field(default_factory=list)  # list[tuple]
    non_executable: list = field(default_factory=list)  # list[TaskDep]
    cycle_warning: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Public API: parse
# ─────────────────────────────────────────────────────────────────────────────


def parse_task_dependencies(plan_tracker_text_or_path) -> list:
    """Parse plan-tracker markdown text into a list of :class:`TaskDep`.

    Accepts either the raw markdown **text** (str/bytes) or a path-like. When
    given a path, the text is read as UTF-8 (this is the ONLY file I/O in the
    module and it exists purely as a convenience for the common case; the CLI
    entry in verify_workflow.py passes text directly so the compute path stays
    I/O-free and trivially testable).

    Scans every ``| 优先级 | ID | ... |`` priority table in the document
    (the live plan-tracker has two: ``### 优先级一览`` and ``### 已归档版本
    task``). Duplicate task IDs across tables are de-duplicated keeping the
    FIRST occurrence (the ``优先级一览`` table is authoritative for active
    tasks; the archived-version pointer table repeats FIX-082..087 only as a
    hot-fact-source proof and would otherwise shadow the active entry — though
    in practice the IDs do not collide across the two tables).

    Robustness:
      - Header-driven column indexing: the ID/依赖/目标版本/状态 columns are
        located by matching the header cell text (``ID`` / ``依赖`` /
        ``目标版本`` / ``状态``), not by hardcoded indices. This survives both
        the 7-col priority table and the archived-pointer variant.
      - Fallback ID detection: if header indexing fails, the ID cell is the
        first data cell matching ``^[A-Z]+-\\d+$`` (handles the malformed
        leading-``**P0**`` rows at live lines 174-176).
      - Separator rows and non-table lines are skipped.

    Args:
        plan_tracker_text_or_path: markdown text (str/bytes) or a path to the
            plan-tracker.md file.

    Returns:
        List of :class:`TaskDep` in document order (de-duplicated by task_id).
    """
    text = _coerce_text(plan_tracker_text_or_path)
    lines = text.split("\n")
    tasks: list = []
    seen_ids: set = set()

    # State machine: we are "in a priority table" between a recognized header
    # row and the next heading / blank-non-table boundary.
    in_table = False
    col_index: dict = {}  # name -> 0-based data-cell index
    header_width = 0  # number of data cells declared by the header row

    for line in lines:
        stripped = line.strip()

        # Any heading ends a table.
        if stripped.startswith("#"):
            in_table = False
            col_index = {}
            header_width = 0
            continue

        # Blank lines are tolerated WITHIN a table (the live plan-tracker
        # inserts a blank line between the priority table and the trailing
        # summary rows, and again between sub-groups). A blank line does NOT
        # end the table; only a heading or a non-blank non-table paragraph does.
        if not stripped:
            continue

        if not stripped.startswith("|"):
            # A non-blank line that is not a table row ends the table (it is a
            # paragraph / prose block / fenced code boundary).
            in_table = False
            col_index = {}
            header_width = 0
            continue

        # Separator row: stay in table, do not parse.
        if _SEPARATOR_RE.match(stripped):
            continue

        cells = _split_row(line)
        if not cells:
            continue

        # Header detection: first cell == "优先级" AND second cell == "ID".
        # This is the canonical priority-table header shape and uniquely
        # identifies the table among all plan-tracker tables (version-section
        # tables put 任务ID/描述 first; risk/decision/evidence logs have
        # different headers).
        if len(cells) >= 2 and cells[0] == "优先级" and cells[1] == "ID":
            in_table = True
            col_index = _build_column_index(cells)
            header_width = len(cells)
            continue

        if not in_table:
            continue

        task = _parse_task_row(cells, col_index, header_width)
        if task is None:
            continue
        if task.task_id in seen_ids:
            continue
        seen_ids.add(task.task_id)
        tasks.append(task)

    return tasks


def _coerce_text(plan_tracker_text_or_path) -> str:
    """Coerce the input to markdown text. Read from path only if not str/bytes."""
    if isinstance(plan_tracker_text_or_path, (str, bytes)):
        if isinstance(plan_tracker_text_or_path, bytes):
            return plan_tracker_text_or_path.decode("utf-8", errors="replace")
        return plan_tracker_text_or_path
    # Path-like: read UTF-8. This is the only file I/O in the module.
    with open(plan_tracker_text_or_path, "r", encoding="utf-8") as f:
        return f.read()


def _build_column_index(header_cells: list) -> dict:
    """Map header cell names to their 0-based data-cell index.

    Recognizes: 优先级, ID, 依赖, 目标版本, 状态. Other columns (事项, 闭环路径,
    负责人, 审查人, ...) are irrelevant to dependency analysis and ignored.
    """
    idx = {}
    for i, cell in enumerate(header_cells):
        # Strip markdown emphasis just in case.
        clean = _strip_markdown(cell)
        if clean == "ID" and "id" not in idx:
            idx["id"] = i
        elif clean == "优先级" and "priority" not in idx:
            idx["priority"] = i
        elif clean == "依赖" and "deps" not in idx:
            idx["deps"] = i
        elif clean == "目标版本" and "version" not in idx:
            idx["version"] = i
        elif clean == "状态" and "status" not in idx:
            idx["status"] = i
    return idx


def _parse_task_row(cells: list, col_index: dict, header_width: int = 0):
    """Parse one priority-table data row into a TaskDep, or None if not a task.

    Returns None for rows that do not yield a valid task ID (e.g. stray
    non-table lines that slipped through, or rows where no cell is a bare ID).

    **Robustness strategy — ID-anchored parsing.** The live plan-tracker has
    two kinds of malformed rows that break naive header-index parsing:

      1. Rows whose 闭环路径 (closure-path) cell contains unescaped ``|``
         (e.g. ``| RISK-`` 行 inside FIX-176's prose). These over-split: a
         7-column row yields 8+ cells, so a fixed ``cells[6]`` status index
         lands inside the prose.
      2. Rows with a duplicated leading priority cell (``| **P0** | **P0** |
         FIX-222 | ... |`` — live lines 174-176). These shift every header
         index by +1 and add a trailing empty cell.

    Both are handled by anchoring on the **ID cell** (the first cell matching
    ``^[A-Z]+-\\d+$``) and reading the other fields by RELATIVE offset from
    that anchor — which is invariant to a duplicated leading cell — and by
    reading the status from the LAST non-empty cell — which is invariant to
    prose pipes in the middle. Specifically, with the ID at index ``k``:

      - priority: cell at ``k-1`` (the cell immediately before the ID; this is
        the ``**P0**`` cell in both the normal and duplicated-priority layouts)
      - dependencies: cell at ``k+2`` (skip the 事项 description at ``k+1``)
      - target version: cell at ``k+3``
      - status: the last NON-empty cell (a trailing ``| |`` yields an empty
        tail cell on the duplicated-priority rows; skipping empties fixes that)
    """
    # Locate the ID cell index (first bare-ID cell). This anchor is invariant
    # to a duplicated leading priority cell.
    id_idx = -1
    task_id = ""
    for i, c in enumerate(cells):
        cand = _strip_markdown(c)
        if _ID_CELL_RE.match(cand):
            id_idx = i
            task_id = cand
            break

    if not task_id:
        return None

    n = len(cells)

    # Priority: cell immediately before the ID. Fall back to a header index or
    # a scan if the cell before the ID is not a priority (defensive).
    priority = _NO_PRIORITY_SENTINEL
    if id_idx - 1 >= 0:
        priority = _parse_priority(cells[id_idx - 1])
    if priority == _NO_PRIORITY_SENTINEL:
        p_idx = col_index.get("priority")
        if p_idx is not None and p_idx < n:
            priority = _parse_priority(cells[p_idx])
    if priority == _NO_PRIORITY_SENTINEL:
        for c in cells[:id_idx + 1]:
            if _PRIORITY_RE.search(c):
                priority = _parse_priority(c)
                break

    # Dependencies: ID+2 (skip the 事项 description at ID+1). The dependency
    # cell is pipe-free in practice (it uses commas), so a single cell holds
    # the whole dependency list.
    deps_cell = ""
    if id_idx + 2 < n:
        deps_cell = cells[id_idx + 2]
    task_family, cross_entity = _parse_dependency_cell(deps_cell)

    # Target version: ID+3.
    target_version = ""
    if id_idx + 3 < n:
        target_version = _strip_markdown(cells[id_idx + 3])

    # Status: last NON-empty cell. A trailing ``| |`` on the duplicated-
    # priority rows yields an empty tail; skipping empties recovers the real
    # status. Prose pipes in 闭环路径 only inflate the MIDDLE cells, so the
    # true status remains the last non-empty cell regardless.
    status = ""
    for c in reversed(cells):
        if c.strip():
            status = c
            break

    return TaskDep(
        task_id=task_id,
        priority=priority,
        status=status,
        dependencies=task_family,
        cross_entity_refs=cross_entity,
        target_version=target_version,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API: compute
# ─────────────────────────────────────────────────────────────────────────────


def _detect_cycles(graph: dict) -> list:
    """Detect cycles in a directed graph via iterative DFS.

    Args:
        graph: ``{node: (successor, ...)}`` where an edge ``node -> successor``
            means ``node`` depends on ``successor`` (i.e. ``successor`` must be
            done first).

    Returns:
        List of cycles, each a tuple of node IDs tracing the cycle, e.g.
        ``("FIX-A", "FIX-B", "FIX-A")``. Each cycle is reported once. Empty list
        when the graph is acyclic.
    """
    cycles: list = []
    # State: 0 = unvisited, 1 = on current stack (in-progress), 2 = fully done.
    state: dict = {n: 0 for n in graph}
    # Track the DFS path so we can extract the cycle when we re-enter a node.
    path: list = []
    # Iterate in sorted order for deterministic output.
    nodes = sorted(graph.keys())

    for start in nodes:
        if state[start] != 0:
            continue
        # Iterative DFS with an explicit stack of (node, successor-iterator).
        stack: list = [(start, iter(sorted(graph.get(start, ()))))]
        state[start] = 1
        path.append(start)
        while stack:
            node, succ_iter = stack[-1]
            advanced = False
            for succ in succ_iter:
                if succ not in graph:
                    # Edge to a node not in the graph (e.g. cross-entity or
                    # missing task). Not a cycle contributor; skip.
                    continue
                if state[succ] == 1:
                    # Found a back-edge: succ is on the current DFS stack.
                    # Extract the cycle from the path: from succ's first
                    # occurrence to the current node, then close back to succ.
                    try:
                        start_idx = path.index(succ)
                    except ValueError:
                        start_idx = 0
                    cycle = tuple(path[start_idx:] + [succ])
                    cycles.append(cycle)
                    # Do not descend into succ (it is on the stack); continue
                    # scanning remaining successors of `node`.
                    continue
                if state[succ] == 0:
                    state[succ] = 1
                    path.append(succ)
                    stack.append((succ, iter(sorted(graph.get(succ, ())))))
                    advanced = True
                    break
                # state == 2: already fully explored; skip.
                continue
            if not advanced:
                # Done with `node`: pop and mark complete.
                state[node] = 2
                if path and path[-1] == node:
                    path.pop()
                stack.pop()
    return cycles


def _priority_sort_key(task: TaskDep) -> tuple:
    """Sort key: priority rank ascending (P0 first), then version ascending."""
    # P0/P1/P2/P9 sort lexicographically because they are zero-padded single
    # digits ("P0" < "P1" < "P2" < "P9").
    return (task.priority, _version_tuple(task.target_version), task.task_id)


def compute_unblocked_tasks(tasks: list) -> PriorityReport:
    """Compute the dependency-based priority report from parsed tasks.

    Algorithm:
      1. Build a status lookup: ``{task_id: is_completed}``.
      2. Build the dependency graph: ``{task_id: task_family_dependencies}``.
      3. Detect cycles (DFS). Cycles are reported on the result but do NOT
         infinite-loop; the rest of the analysis proceeds normally.
      4. Classify each task:
           - ``completed`` — status ✅.
           - ``blocked`` — not completed AND has ≥1 task-family dependency
             that is not provably completed (either the dep is in the table
             with non-✅ status, OR the dep is missing from the table —
             fail-closed: an unknown task-family ID cannot be proven done).
           - ``non_executable`` — not completed, all task-family dependencies
             are completed (or none), but the status leading marker is
             terminal / non-executable (⛔/⏸/🔴/🚧/🛑/📋/✅) — the third-class
             status filter (FIX-237.2 / ADR-017 §4.4 P1-3). Reported separately
             so filtered rows stay visible.
           - ``unblocked`` — not completed, all task-family dependencies are
             completed (or it has none), AND the status leading marker is ⏳
             or absent (status candidate-eligible).
      5. ``recommended_next`` = ``unblocked`` sorted by priority then version.
      6. ``cycle_warning`` = whether any cycle was detected (WARN, not ERROR).

    Cross-entity refs (RISK/DEC/REVIEW/...) are never dependencies in the
    graph and never block (FIX-171 precedent).

    Args:
        tasks: list of :class:`TaskDep` (from :func:`parse_task_dependencies`).

    Returns:
        A :class:`PriorityReport`.
    """
    status_map: dict = {t.task_id: t.is_completed() for t in tasks}
    graph: dict = {t.task_id: tuple(t.dependencies) for t in tasks}
    cycles = _detect_cycles(graph)

    completed: list = []
    blocked: list = []
    unblocked: list = []
    non_executable: list = []

    for t in tasks:
        if t.is_completed():
            completed.append(t)
            continue
        # Not completed: check task-family dependencies.
        blocking = []
        for dep in t.dependencies:
            if status_map.get(dep, False):
                # Dependency is completed → does not block.
                continue
            # Dependency is either incomplete (in table, non-✅) or unknown
            # (missing from table). Either way it blocks fail-closed.
            blocking.append(dep)
        if blocking:
            blocked.append(BlockedTask(task=t, blocking_dependencies=tuple(blocking)))
            continue
        # Dependency-satisfied (or no deps): the third-class status gate
        # decides executable candidacy (FIX-237.2 / ADR-017 §4.4 P1-3).
        if not _status_is_candidate_eligible(t.status):
            non_executable.append(t)
            continue
        unblocked.append(t)

    recommended = sorted(unblocked, key=_priority_sort_key)

    return PriorityReport(
        completed=completed,
        blocked=blocked,
        unblocked=unblocked,
        recommended_next=recommended,
        total=len(tasks),
        dependency_graph=graph,
        cycles=cycles,
        non_executable=non_executable,
        cycle_warning=bool(cycles),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public API: format
# ─────────────────────────────────────────────────────────────────────────────


def _clean_status_for_display(status: str) -> str:
    """Trim a status cell to a compact display string (drop trailing detail).

    Keeps the leading emoji + the first short label, dropping verbose
    parentheticals and evidence cross-refs so the report stays scannable.
    Falls back to the raw cell when no compact form is extracted.
    """
    s = status.strip()
    if not s:
        return s
    # Take everything up to the first " (" or "——" or "；" detail separator.
    for sep in (" (", "（", "——", "；", ";"):
        idx = s.find(sep)
        if idx > 0:
            s = s[:idx].strip()
    return s


def _format_task_line(t: TaskDep) -> str:
    """One-line summary of a task for the report."""
    deps = ", ".join(t.dependencies) if t.dependencies else "—"
    cross = ", ".join(t.cross_entity_refs) if t.cross_entity_refs else ""
    cross_str = f"  [refs: {cross}]" if cross else ""
    version = t.target_version or "—"
    status = _clean_status_for_display(t.status) or "—"
    return f"- `{t.task_id}` [{t.priority}] v={version} status={status} deps=[{deps}]{cross_str}"


def format_report(report: PriorityReport) -> str:
    """Format a :class:`PriorityReport` as readable markdown for CLI output.

    Sections:
      1. Summary counts.
      2. ``Recommended next`` (the highest-priority unblocked task(s)) — this is
         the answer to "what should I work on next?".
      3. ``Unblocked`` (all ready-to-work tasks, priority-ordered).
      4. ``Excluded`` (dependency-satisfied rows filtered out by the third-class
         status filter — ⛔/⏸/🔴/🚧/🛑/📋/✅ leading markers).
      5. ``Blocked`` (tasks with their specific blocking dependencies).
      6. ``Completed`` (already-done tasks — for context; truncated to 20).
      7. ``Cycles`` — WARNING banner (not ERROR) if the dependency graph has a
         cycle (cycle tolerance, FIX-237.2).

    The output is plain markdown (no ANSI color) so it renders identically in a
    terminal, a pipe, or a file.
    """
    lines: list = []
    lines.append("# Task Priority Analysis")
    lines.append("")
    lines.append(
        f"Total: **{report.total}** tasks — "
        f"{len(report.completed)} completed, "
        f"{len(report.unblocked)} unblocked, "
        f"{len(report.blocked)} blocked, "
        f"{len(report.non_executable)} non-executable."
    )
    lines.append("")

    if report.cycles:
        lines.append("## ⚠️ CYCLE DETECTED (WARNING)")
        lines.append("")
        lines.append(
            "The dependency graph contains a cycle. The analysis below is "
            "best-effort; the cycle should be resolved (a task should not "
            "depend, directly or transitively, on itself). This is a WARNING "
            "and does not block the analysis output (FIX-237.2 cycle "
            "tolerance)."
        )
        lines.append("")
        for cyc in report.cycles:
            lines.append("- " + " → ".join(cyc))
        lines.append("")

    lines.append("## Recommended next")
    lines.append("")
    if report.recommended_next:
        top = report.recommended_next[0]
        lines.append(f"**Top pick: `{top.task_id}` [{top.priority}]**")
        lines.append("")
        for t in report.recommended_next:
            lines.append(_format_task_line(t))
    else:
        lines.append("_No unblocked tasks. Every non-completed task is blocked "
                     "or there are no active tasks._")
    lines.append("")

    lines.append("## Unblocked (ready to work)")
    lines.append("")
    if report.unblocked:
        for t in report.unblocked:
            lines.append(_format_task_line(t))
    else:
        lines.append("_None._")
    lines.append("")

    lines.append("## Excluded (non-executable status)")
    lines.append("")
    if report.non_executable:
        lines.append(
            "_Dependency-satisfied rows excluded from Unblocked / Recommended "
            "next: their status leading marker is terminal / non-executable "
            "(⛔/⏸/🔴/🚧/🛑/📋/✅) even though their dependencies are met "
            "(FIX-237.2 / ADR-017 §4.4 P1-3)._"
        )
        lines.append("")
        for t in report.non_executable:
            lines.append(_format_task_line(t))
    else:
        lines.append("_None._")
    lines.append("")

    lines.append("## Blocked")
    lines.append("")
    if report.blocked:
        for bt in report.blocked:
            t = bt.task
            blockers = ", ".join(bt.blocking_dependencies)
            lines.append(
                f"- `{t.task_id}` [{t.priority}] v={t.target_version or '—'} "
                f"status={_clean_status_for_display(t.status) or '—'} "
                f"blocked_by=[{blockers}]"
            )
    else:
        lines.append("_None._")
    lines.append("")

    lines.append("## Completed")
    lines.append("")
    if report.completed:
        # Truncate to keep the report scannable; the full list is recoverable
        # from plan-tracker.md directly.
        shown = report.completed[:20]
        for t in shown:
            lines.append(_format_task_line(t))
        if len(report.completed) > 20:
            lines.append(f"_...and {len(report.completed) - 20} more (see plan-tracker.md)._")
    else:
        lines.append("_None._")
    lines.append("")

    return "\n".join(lines)


__all__ = [
    "TaskDep",
    "BlockedTask",
    "PriorityReport",
    "parse_task_dependencies",
    "compute_unblocked_tasks",
    "format_report",
]
