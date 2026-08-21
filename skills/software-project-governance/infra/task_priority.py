#!/usr/bin/env python3
"""Task dependency / priority analysis — FIX-226 (0.71.0).

This module is the **pure dependency-analysis layer** for the governance
plan-tracker. It parses the ``优先级一览`` priority tables in
``plan-tracker.md`` — including the headerless ``### 最近完成（本会话提交窗口）``
window table (FIX-251) — builds a directed acyclic graph (DAG) from the ``依赖``
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

**Empty-recommendation fallback (FIX-254 / REQ-110):** when no task is
unblocked (``recommended_next == []`` — the live-data norm: total > 0 with
unblocked = 0), the report never degrades to a bare empty list (the
AUDIT-143 data-layer root cause of the "mechanically enumerate an
unfinished item" degradation). :func:`compute_unblocked_tasks` walks the
blocked dependency graph and attaches either (a) an
:class:`UnblockRecommendation` — the head node of the highest-value blocked
chain (the root blocker whose resolution reopens the most downstream
tasks), with a dependency reason — and/or (b) a structured
``empty_reason`` (``all_blocked`` / ``all_non_executable`` /
``no_active_tasks``) with the nearest actionable step.
:func:`format_report` renders both; downstream consumers
(loop_exit_bridge.py / the next-candidates CLI) forward them as machine
fields.

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
from pathlib import Path


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

# Status marker emojis that LEAD a plan-tracker ``状态`` cell. Mirrors the
# markers the module already classifies (✅ completed + the active hints + 📋
# queued). Used by :func:`_is_headerless_task_row` to tell a task data row
# apart from any other markdown table row.
_STATUS_CELL_MARKERS = frozenset(
    {_COMPLETED_EMOJI} | set(_ACTIVE_STATUS_HINTS) | {"📋"}
)


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


def _is_headerless_task_row(cells: list) -> bool:
    """True if a ``|`` row has the shape of a headerless task-table row.

    FIX-251: the live plan-tracker's ``### 最近完成（本会话提交窗口）``
    sub-section is a full 优先级|ID|事项|依赖|目标版本|闭环路径|状态 task table that
    lacks the header row and separator row — the first ``|`` line after the
    heading is already a data row. Such a row is recognized by carrying both:

      - a bare task ID cell (``^[A-Z]+-\\d+$`` — the same first-bare-ID anchor
        the row parser uses, so a duplicated leading priority cell does not
        confuse the detection), and
      - a status-semantic cell (a cell whose text begins with a plan-tracker
        status marker emoji).

    Conservative on purpose: the caller additionally gates this on the row
    DIRECTLY following a heading (``after_heading`` — only blank lines may sit
    between heading and table), so prose-separated tables (``需求跟踪矩阵`` and
    the like) are never misread as headerless task tables. The
    ``len(cells) >= 5`` sanity bound mirrors the canonical 7-col task table
    (and its malformed variants keep ≥5 cells) while excluding small
    non-task tables.
    """
    if len(cells) < 5:
        return False
    has_id = False
    has_status = False
    for c in cells:
        cand = _strip_markdown(c)
        if _ID_CELL_RE.match(cand):
            has_id = True
        elif cand.startswith(tuple(_STATUS_CELL_MARKERS)):
            has_status = True
    return has_id and has_status


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
class UnblockRecommendation:
    """REQ-110 / FIX-254 — the head node of the highest-value blocked chain.

    Built only when ``recommended_next`` is empty AND at least one task is
    dependency-blocked (there is a chain to unlock). The recommendation is
    the ROOT blocker whose resolution reopens the most downstream blocked
    tasks — value = downstream count, tie-broken by the root's priority,
    target version, then ID (deterministic).

    Attributes:
        root_task_id: the chain head to unlock — either an in-table task ID
            or an unknown task-family ID (a dependency with no row).
        root_kind: why the chain is stopped — ``"non_executable_status"``
            (in-table, dependency-satisfied, held by a terminal status
            marker), ``"unknown_dependency"`` (task-family ID missing from
            the table — fail-closed block), or ``"cycle"`` (the chain bottoms
            out in a dependency cycle).
        root_priority: the root's priority label (``P9`` for unknown IDs).
        root_status: compact status display of the root (``""`` when unknown).
        downstream_task_ids: the blocked task IDs transitively unlocked by
            resolving the root, priority-ordered (may include the root itself
            when it sits on a cycle).
        downstream_count: ``len(downstream_task_ids)`` (cached for consumers).
        reason: human-readable dependency reason (why this root, what to do).
    """

    root_task_id: str
    root_kind: str
    root_priority: str = _NO_PRIORITY_SENTINEL
    root_status: str = ""
    downstream_task_ids: tuple = ()
    downstream_count: int = 0
    reason: str = ""


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
        unblock_recommendation: :class:`UnblockRecommendation` or None — the
            REQ-110 / FIX-254 empty-recommendation fallback. Set only when
            ``recommended_next`` is empty AND at least one task is blocked
            (the head of the highest-value blocked chain + reason). None on
            the normal (non-empty) path and when there is no chain to unlock.
        empty_reason: structured dict or None — set whenever
            ``recommended_next`` is empty (REQ-110 forbids a bare empty
            list). Shape: ``{"kind": "all_blocked" | "all_non_executable" |
            "no_active_tasks", "total", "completed", "blocked",
            "non_executable", "message", "nearest_action"}``. None on the
            normal path.
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
    unblock_recommendation: "UnblockRecommendation | None" = None
    empty_reason: "dict | None" = None


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

    **str path/text disambiguation (FIX-252 O1):** a ``str`` is ambiguous — it
    may be document text OR a str-form path. If the str *looks like a path*
    (names an existing file, has a drive prefix, or ends in ``.md``/``.txt``
    with a path separator — see :func:`_looks_like_str_path`) it is read from
    disk; a path-like str naming a non-existent file raises
    :class:`ValueError` (never a silent ``total 0``). Ordinary markdown text
    stays on the text channel.

    Scans every priority task table in the document — both the header-driven
    ``| 优先级 | ID | ... |`` tables (``### 优先级一览`` and ``### 已归档版本
    task``) and the headerless window table directly under ``### 最近完成
    （本会话提交窗口）`` (a 7-col task table with NO header row; FIX-251).
    Duplicate task IDs across tables are de-duplicated keeping the
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
      - Headerless window table (FIX-251): a ``|`` row that DIRECTLY follows
        a heading and carries both a bare task ID cell and a status cell
        enters a headerless task table whose column layout is inferred from
        the canonical 7-col shape. Prose between the heading and the table
        disarms this, so non-task tables (``需求跟踪矩阵`` etc.) are never
        misread.
      - Separator rows and non-table lines are skipped.

    Args:
        plan_tracker_text_or_path: markdown text (str/bytes) or a path to the
            plan-tracker.md file. A path may be a Path-like object or a
            str-form path (auto-detected by :func:`_looks_like_str_path`).

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
    # True when the last significant line was a heading (only blank lines may
    # have passed since). Gates the headerless task-table recognition
    # (FIX-251): only a table that DIRECTLY follows a heading may be read as
    # a headerless task table, so prose-separated tables (需求跟踪矩阵 etc.)
    # are never mis-detected.
    after_heading = False

    for line in lines:
        stripped = line.strip()

        # Any heading ends a table and arms the headerless recognition for
        # the lines that follow it (FIX-251).
        if stripped.startswith("#"):
            in_table = False
            col_index = {}
            header_width = 0
            after_heading = True
            continue

        # Blank lines are tolerated WITHIN a table (the live plan-tracker
        # inserts a blank line between the priority table and the trailing
        # summary rows, and again between sub-groups). A blank line does NOT
        # end the table; only a heading or a non-blank non-table paragraph
        # does. A blank right after a heading does NOT disarm the headerless
        # recognition either (a headerless window table may be separated from
        # its heading by a blank line).
        if not stripped:
            continue

        if not stripped.startswith("|"):
            # A non-blank line that is not a table row ends the table (it is a
            # paragraph / prose block / fenced code boundary) and disarms the
            # headerless recognition (the table no longer directly follows a
            # heading).
            in_table = False
            col_index = {}
            header_width = 0
            after_heading = False
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
            after_heading = False
            continue

        # Headerless task table (FIX-251): a row that DIRECTLY follows a
        # heading and carries both a bare task ID cell and a status cell.
        # The live ``### 最近完成（本会话提交窗口）`` sub-section is a 7-col task
        # table WITHOUT a header row; without this branch its rows never enter
        # ``in_table`` and the window's task IDs stay invisible to dependency
        # analysis (change-triage reported them as unknown-dep, fail-closed).
        # The column layout is inferred from the canonical 优先级|ID|依赖|目标版本|
        # 状态 shape — the row parser is ID-anchored, so no header index map is
        # needed.
        if (not in_table and after_heading
                and _is_headerless_task_row(cells)):
            in_table = True
            col_index = {}
            header_width = 0
            after_heading = False

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


_STR_PATH_SUFFIXES = (".md", ".txt")


def _truncate_repr(value: str, limit: int = 120) -> str:
    """Return a bounded ``repr`` of a str for error messages (FIX-252 R0 P2-1).

    Embedding a full ``!r`` of a large mis-detected input would dump the entire
    text into the traceback. Cap the rendered representation and append a
    length annotation so the diagnostic stays actionable without flooding.
    """
    rendered = repr(value)
    if len(rendered) <= limit:
        return rendered
    return rendered[:limit] + f"...<len={len(value)}>"


def _looks_like_str_path(value: str) -> bool:
    """Return True when a ``str`` input should be read as a path, not text.

    FIX-252 O1 (a)+(b) disambiguation for :func:`_coerce_text`. A ``str`` is
    naturally ambiguous — it may be document text OR a str-form path (e.g.
    ``parse_task_dependencies('D:\\\\...\\\\plan-tracker.md')``), and the pre-fix
    code returned ANY ``str`` as text, silently producing ``total 0`` for a
    str-path caller.

    A str is treated as a path when ANY of:
      - ``Path(value).exists()`` is True (an actually-existing file — the only
        unambiguous signal; we read its text),
      - it has a Windows drive-letter prefix (``C:\\...`` / ``C:/...``),
      - it ends in a document suffix (``.md``/``.txt``) AND contains a path
        separator (``\\`` or ``/``) — covers absolute, relative and nested
        str-form paths.

    Plain document text is NOT mis-detected: everyday markdown prose frequently
    contains ``/`` (URLs, dates, inline code) but does not *end* in ``.md``/``.txt``
    nor carry a drive prefix, and it almost never names a real file. The rare
    text-string that happens to end in ``.md`` is accepted as a path
    (documented ambiguity — prefer path interpretation).
    """
    try:
        if Path(value).exists():
            return True
    except (OSError, ValueError, OverflowError):
        # Over-long / invalid path string (e.g. a huge prose blob) — not a path.
        pass
    if re.match(r"^[A-Za-z]:[\\/]", value):
        return True
    lowered = value.lower()
    if lowered.endswith(_STR_PATH_SUFFIXES) and ("\\" in value or "/" in value):
        return True
    return False


def _coerce_text(plan_tracker_text_or_path) -> str:
    """Coerce the input to markdown text, disambiguating str path vs text.

    A ``str`` is ambiguous: it can be document text OR a str-form path. Before
    FIX-252 O1, ANY ``str`` was returned as text, so a caller passing a str-form
    path (``parse_task_dependencies('D:\\\\...\\\\plan-tracker.md')``) got a
    silent ``total 0`` — the string was parsed as doc text and no table matched
    (the pre-fix bug). Now a str that *looks like a path*
    (:func:`_looks_like_str_path`) is read from disk; a path-like str that does
    NOT name an existing file raises an explicit :class:`ValueError` (never a
    silent total 0 — approach (a)+(b) combo). Ordinary text that merely contains
    ``/`` stays on the text channel (zero regression for the existing str-text
    callers: verify_workflow passes ``SAMPLE_PATH.read_text(...)`` and
    change_triage passes ``plan_tracker_text`` — both plain markdown).

    **Empty / multi-line guard (FIX-252 R0 P1-1):** a real path is never empty
    and can never contain a newline. An empty str (``Path("")`` normalizes to
    ``Path(".")``) or any multi-line value is by definition document text and is
    returned as text WITHOUT entering the path heuristic — closing the
    ``open(Path(""))`` → ``open(".")`` IsADirectoryError/PermissionError gap
    (empty plan-tracker crashing uncategorized) and the spurious ValueError on a
    multi-line str whose first line looks like a path. This also spares real
    document blobs from the ``exists()`` stat.
    """
    if isinstance(plan_tracker_text_or_path, bytes):
        return plan_tracker_text_or_path.decode("utf-8", errors="replace")
    if isinstance(plan_tracker_text_or_path, str):
        value = plan_tracker_text_or_path
        # Empty / multi-line → text channel (FIX-252 R0 P1-1), never a path.
        if not value or "\n" in value:
            return value
        if _looks_like_str_path(value):
            target = Path(value)
            if not target.exists():
                raise ValueError(
                    "input is neither text with tables nor an existing path: "
                    f"{_truncate_repr(value)} — pass a Path object or "
                    "document text as str"
                )
            with open(target, "r", encoding="utf-8") as f:
                return f.read()
        return value
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


# ─────────────────────────────────────────────────────────────────────────────
# Empty-recommendation fallback (REQ-110 / FIX-254)
# ─────────────────────────────────────────────────────────────────────────────
#
# Root-cause kinds for a blocked chain (why the chain is stopped):
_ROOT_KIND_STATUS = "non_executable_status"
_ROOT_KIND_UNKNOWN = "unknown_dependency"
_ROOT_KIND_CYCLE = "cycle"

# Degenerate-chain guard: a blocker walk deeper than this is treated as a
# cycle-style unresolvable chain (defensive — real governance chains are
# single-digit deep; this only bounds recursion on adversarial input).
_MAX_ROOT_WALK_DEPTH = 200


def _walk_blocker_roots(origin_id: str, blocked_map: dict, task_index: dict,
                        roots: dict) -> None:
    """Attribute one blocked task to the ROOT blockers of its chain (FIX-254).

    Starting from ``origin_id``'s blocking dependencies, walk each in-table
    blocker's own blockers until the walk bottoms out at a ROOT — a blocker
    that is itself not blocked by anything actionable:

      - ``unknown_dependency`` — a task-family ID with no row in the table
        (fail-closed: it cannot be proven complete);
      - ``non_executable_status`` — an in-table, not-completed,
        dependency-satisfied row (its terminal status marker is what stops
        the chain — e.g. a ⛔/⏸ row like the live FIX-155 停滞链);
      - ``cycle`` — a blocker already on the current walk path (the chain
        bottoms out in a dependency cycle).

    Every origin reachable from a root is attributed to that root as
    downstream (``roots[(root_id, kind)].add(origin_id)``). The per-branch
    ``path`` set makes diamond shapes attribute to the shared root instead of
    being misread as cycles; only a TRUE back-edge (a repeat on the SAME
    branch) classifies as a cycle. Depth-capped for termination.

    Args:
        origin_id: the blocked task ID whose chain is walked.
        blocked_map: ``{task_id: (blocking_dependency_ids, ...)}`` for every
            blocked task.
        task_index: ``{task_id: TaskDep}`` for every non-completed in-table
            task (blocked + non-executable members).
        roots: accumulator mutated in place — ``{(root_id, kind): set(origin)}``.
    """

    def _visit(dep: str, path: set, depth: int) -> None:
        if dep in path or depth > _MAX_ROOT_WALK_DEPTH:
            roots.setdefault((dep, _ROOT_KIND_CYCLE), set()).add(origin_id)
            return
        blocker = task_index.get(dep)
        if blocker is None:
            roots.setdefault((dep, _ROOT_KIND_UNKNOWN), set()).add(origin_id)
            return
        if blocker.is_completed():
            # Defensive: completed deps never appear in blocking_dependencies
            # by construction; a hand-built report input cannot block via one.
            return
        if dep in blocked_map:
            # In-table, itself blocked → extend the chain through its blockers.
            extended = path | {dep}
            for d in blocked_map[dep]:
                _visit(d, extended, depth + 1)
            return
        # In-table, not completed, not blocked → dependency-satisfied stop.
        # (On the empty-unblocked path such a row is non-executable by
        # definition — its status marker is the chain's root cause.)
        roots.setdefault((dep, _ROOT_KIND_STATUS), set()).add(origin_id)

    for d in blocked_map.get(origin_id, ()):
        _visit(d, {origin_id}, 0)


def _unblock_reason(root_id: str, kind: str, root_task) -> str:
    """Human-readable dependency reason for one unblock recommendation."""
    status = _clean_status_for_display(root_task.status) if root_task is not None else ""
    if kind == _ROOT_KIND_UNKNOWN:
        return (
            f"data gap: `{root_id}` is a task-family dependency with no row in "
            f"the plan-tracker (fail-closed — it cannot be proven complete); "
            f"verify or record its completion to reopen the chain"
        )
    if kind == _ROOT_KIND_CYCLE:
        return (
            f"dependency cycle: `{root_id}` sits on a blocker cycle; resolve "
            f"the cycle (re-point or complete a member) to reopen the chain"
        )
    return (
        f"status stop: `{root_id}` is dependency-satisfied but held by "
        f"terminal status '{status or 'non-executable marker'}' — re-evaluate "
        f"or resume `{root_id}` to reopen the chain"
    )


def _build_empty_recommendation_fallback(blocked: list, non_executable: list,
                                         completed: list, total: int) -> tuple:
    """Build the REQ-110 / FIX-254 fallback for an empty ``recommended_next``.

    Returns ``(unblock_recommendation, empty_reason)``:

      - ``unblock_recommendation`` — :class:`UnblockRecommendation` for the
        head of the highest-value blocked chain (value = downstream blocked
        task count, tie-broken by root priority → version → ID), or None when
        no task is dependency-blocked (no chain to unlock).
      - ``empty_reason`` — structured dict with kind ``all_blocked`` /
        ``all_non_executable`` / ``no_active_tasks`` + counts + message +
        ``nearest_action`` (最近可行动作). Always non-None on this path.

    A bare empty recommendation is forbidden (AUDIT-143 data-layer root
    cause): the caller gets either a chain recommendation, a structured
    reason, or both.
    """
    blocked_map = {bt.task.task_id: tuple(bt.blocking_dependencies) for bt in blocked}
    task_index: dict = {t.task_id: t for t in non_executable}
    for bt in blocked:
        task_index[bt.task.task_id] = bt.task

    roots: dict = {}
    for bt in blocked:
        _walk_blocker_roots(bt.task.task_id, blocked_map, task_index, roots)

    recommendation = None
    if roots:
        dep_index = {bt.task.task_id: bt for bt in blocked}

        def _root_key(item: tuple) -> tuple:
            (root_id, _kind), downstream = item
            root_task = task_index.get(root_id)
            if root_task is None:
                return (-len(downstream), _NO_PRIORITY_SENTINEL,
                        (float("inf"), 0, 0), root_id)
            return (-len(downstream), root_task.priority,
                    _version_tuple(root_task.target_version), root_id)

        (root_id, kind), downstream_ids = min(roots.items(), key=_root_key)
        root_task = task_index.get(root_id)
        ordered = tuple(sorted(
            downstream_ids,
            key=lambda tid: _priority_sort_key(dep_index[tid].task)),
        ) if downstream_ids else ()
        recommendation = UnblockRecommendation(
            root_task_id=root_id,
            root_kind=kind,
            root_priority=(root_task.priority if root_task is not None
                           else _NO_PRIORITY_SENTINEL),
            root_status=(_clean_status_for_display(root_task.status)
                         if root_task is not None else ""),
            downstream_task_ids=ordered,
            downstream_count=len(ordered),
            reason=_unblock_reason(root_id, kind, root_task),
        )

    if blocked:
        kind_label = "all_blocked"
        held_clause = (
            f"; {len(non_executable)} dependency-satisfied row(s) additionally "
            f"held by non-executable status markers"
        ) if non_executable else ""
        message = (
            f"no executable candidate: {len(blocked)} active task(s) are all "
            f"blocked by unresolved task-family dependencies{held_clause}")
        if recommendation is not None:
            nearest_action = (
                f"unblock `{recommendation.root_task_id}` "
                f"({recommendation.root_kind}) — highest-value chain, "
                f"{recommendation.downstream_count} downstream blocked task(s)")
        else:  # defensive — roots are non-empty whenever blocked is
            nearest_action = "resolve the root blockers listed under Blocked"
    elif non_executable:
        kind_label = "all_non_executable"
        message = (
            f"no executable candidate: all {len(non_executable)} active row(s) "
            f"are dependency-satisfied but held by non-executable status "
            f"markers (⛔/⏸/🔴/🚧/🛑/📋)")
        top_held = sorted(non_executable, key=_priority_sort_key)[0]
        nearest_action = (
            f"re-evaluate `{top_held.task_id}` [{top_held.priority}] — its "
            f"dependencies are satisfied; only its status marker holds it back")
    else:
        kind_label = "no_active_tasks"
        if total:
            message = (
                f"no active tasks: all {total} parsed task(s) are completed — "
                f"nothing pending, blocked or held")
        else:
            message = "no active tasks: plan-tracker contains no task rows"
        nearest_action = (
            "plan the next work batch — append rows to the 优先级一览 table")

    empty_reason = {
        "kind": kind_label,
        "total": total,
        "completed": len(completed),
        "blocked": len(blocked),
        "non_executable": len(non_executable),
        "message": message,
        "nearest_action": nearest_action,
    }
    return recommendation, empty_reason


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
      7. **Empty-recommendation fallback (REQ-110 / FIX-254):** when
         ``recommended_next`` is empty (the live-data norm: total>0 with
         unblocked=0), analyze the blocked dependency graph and attach
         ``unblock_recommendation`` (head of the highest-value blocked chain
         + dependency reason) and/or a structured ``empty_reason``
         (all_blocked / all_non_executable / no_active_tasks + nearest
         actionable step). A bare empty recommendation is forbidden — it is
         the AUDIT-143 data-layer root cause of the机械枚举 degradation.

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

    unblock_recommendation = None
    empty_reason = None
    if not recommended:
        # REQ-110 / FIX-254 empty-recommendation fallback: never a bare empty
        # list — blocked-chain unblock pick and/or a structured empty reason.
        unblock_recommendation, empty_reason = _build_empty_recommendation_fallback(
            blocked=blocked,
            non_executable=non_executable,
            completed=completed,
            total=len(tasks),
        )

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
        unblock_recommendation=unblock_recommendation,
        empty_reason=empty_reason,
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
         the answer to "what should I work on next?". When empty, the REQ-110 /
         FIX-254 fallback renders instead: the blocked-chain ``Unblock pick``
         (root + reason + downstream) and/or the structured empty reason with
         the nearest actionable step — never the pre-FIX-254 bare empty note.
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
    elif report.unblock_recommendation is not None:
        # REQ-110 / FIX-254 fallback (a): blocked-chain unblock recommendation.
        rec = report.unblock_recommendation
        lines.append(
            "_No unblocked tasks — REQ-110 fallback: blocked-chain unblock "
            "recommendation (FIX-254)._")
        lines.append("")
        status_clause = f" status='{rec.root_status}'" if rec.root_status else ""
        lines.append(
            f"**Unblock pick: `{rec.root_task_id}` [{rec.root_priority}] "
            f"({rec.root_kind}{status_clause})**")
        lines.append("")
        lines.append(f"- reason: {rec.reason}")
        if rec.downstream_task_ids:
            shown = ", ".join(f"`{i}`" for i in rec.downstream_task_ids[:12])
            more = (f" (+{len(rec.downstream_task_ids) - 12} more)"
                    if len(rec.downstream_task_ids) > 12 else "")
            lines.append(
                f"- unlocks {rec.downstream_count} downstream blocked "
                f"task(s): {shown}{more}")
        if report.empty_reason:
            lines.append(
                f"- empty reason: {report.empty_reason.get('kind')} — "
                f"{report.empty_reason.get('message')}")
            lines.append(
                f"- nearest action: {report.empty_reason.get('nearest_action')}")
    elif report.empty_reason:
        # REQ-110 / FIX-254 fallback (b): structured empty reason + nearest
        # actionable step — the bare pre-FIX-254 note is forbidden.
        er = report.empty_reason
        lines.append(
            "_No unblocked tasks — structured empty reason "
            "(REQ-110 / FIX-254)._")
        lines.append("")
        lines.append(f"- kind: {er.get('kind')}")
        lines.append(
            f"- counts: total={er.get('total')} "
            f"completed={er.get('completed')} blocked={er.get('blocked')} "
            f"non-executable={er.get('non_executable')}")
        lines.append(f"- {er.get('message')}")
        lines.append(f"- nearest action: {er.get('nearest_action')}")
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
    "UnblockRecommendation",
    "PriorityReport",
    "parse_task_dependencies",
    "compute_unblocked_tasks",
    "format_report",
]
