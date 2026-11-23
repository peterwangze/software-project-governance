"""Read the current release and select active tasks from historical and current plan tables."""
import re

from hot_governance_facts import _TASK_ID_CELL_RE


# FIX-371/DEC-227 路线 b: a hot-tracker status cell leading with ✅ marks the
# terminal (完成) state — the row is historical bookkeeping retained in the
# hot table, not an active task. Only the ✅ prefix exempts; every other
# status (🔄 活跃 / 📋 待启 / plain text / chains not led by ✅) stays fully
# guarded — active/new rows have ZERO exemption (non-weakening red line).
_COMPLETED_STATUS_PREFIX = "✅"


def _plan_hot_tracker_task_statuses(*, plan_path):
    """Return {task_id: status cell} from the current active hot-task table.

    FIX-371: single scan-source for the Check 16/17 entry collection —
    parse_impact_analysis_entries_with_exemptions consumes this statuses
    dict directly (same section boundaries: `## 当前活跃事项` until
    `### 最近完成`), so the exemption set is always a subset of the id set
    the entry collection consumes.

    Status-cell read (FIX-376 F-7 勘正): the compact layout ends with 状态 —
    those rows read the same cell parse_current_active_tasks reads (last
    cell, 同源). The legacy REQ-row layout carries 状态 second-to-last —
    there the ✅ word-prefix read overrides the last-cell read (F-3 分叉
    口径: a deliberate divergence from parse_current_active_tasks, which
    always reads the last cell and cannot see a legacy-row ✅ status).

    FIX-376 F-3 刻意分叉 (conservative; DEC-227 unchanged): the exemption
    predicate stays NARROWER than the FIX-292 authoritative terminal
    predicate ``_status_is_completed_cell`` — a mixed chain 「🔄 … → ✅ 完成」
    is W-7-terminal by that predicate but does not lead with ✅ → stays
    guarded (no exemption — conservative false-FAIL direction). FIX-390
    (DEC-241 消解, 0.89.0) evolves the exemption face to the three-state
    structured read :func:`_hot_status_completion_state` — the writer-era
    terminal (``committed`` + ops anchor, FIX-393 identity) joins the
    hand-era ✅ prefix — while EVERY other shape (mixed chains, triaged/dev
    cells with anchors, anchor-less hand-written 「committed」, unknown
    tokens) keeps the guarded verdict. The F-3 conservative direction is
    preserved for everything outside those two terminal eras.
    """
    if not plan_path.is_file():
        return {}
    content = plan_path.read_text(encoding="utf-8")
    statuses = {}
    in_active_section = False
    for line in content.split("\n"):
        if line.startswith("## 当前活跃事项"):
            in_active_section = True
            continue
        if in_active_section and line.startswith("### 最近完成"):
            break
        if not in_active_section:
            continue
        stripped = line.strip()
        if not stripped.startswith("| ") or "---" in stripped:
            continue
        match = re.search(r"\|\s*(?:\*\*)?([A-Z]+-\d+)(?:\*\*)?\s*\|", stripped)
        if not match:
            continue
        cells = _governance_table_cells(stripped)
        # FIX-371: the hot table mixes shapes — the compact layout ends with
        # 状态 while the legacy REQ-row layout carries 状态 second-to-last.
        # FIX-376 F-3: the ✅ cell is scanned RIGHT-TO-LEFT — the status
        # column is a row-end anchor in both shapes, so the rightmost
        # ✅-led cell is the status-cell candidate. The old left-to-right
        # "first ✅ cell" read let an early ✅-led description/来源 cell
        # outrank the real status cell whenever both lead with ✅. Residual
        # theoretical vector outside this ticket's decided scope: an active
        # row whose real status does not lead with ✅ while an earlier cell
        # does — column-position pinning was R0's alternative and is not
        # adopted. Fallback stays the last cell when no ✅-led cell exists
        # (active rows).
        status = ""
        for cell in reversed(cells):
            if cell.startswith(_COMPLETED_STATUS_PREFIX):
                status = cell.strip()
                break
        if not status and cells:
            status = cells[-1].strip()
        statuses[match.group(1)] = status
    return statuses

# FIX-390 (DEC-241 消解, 0.89.0) — three-state structured completion read for
# the Check 16/17/18/18b exemption face. Display prefixes are no longer the
# only completion authority: the governed writer's own terminal state
# (``committed`` + ops receipt anchor, FIX-393 criterion consumed BY IDENTITY
# via :func:`_status_is_writer_committed_cell`) is the machine-era exact
# analog of the hand-era ✅ prefix (DEC-227 路线 b). States:
#   "committed" — writer-terminal + 〔op-<32hex>〕 anchor → completed/exempt;
#   "legacy"    — ✅-led hand-era terminal → completed/exempt (byte-for-byte
#                 the FIX-371/DEC-227 semantics — S_new ⊇ S_old invariant);
#   ""          — EVERYTHING else (mixed chains not led by ✅, triaged/dev
#                 cells with anchors, hand-written 「committed」 without the
#                 anchor, unknown tokens, empty) → 未知不猜: stays guarded
#                 (fail-closed; the row is judged on its fact merits instead).
_HOT_STATUS_STATE_COMMITTED = "committed"

_HOT_STATUS_STATE_LEGACY = "legacy"


def _hot_status_completion_state(status, *, status_clean_cell, status_is_writer_committed_cell):
    """Classify a hot-tracker status cell into the FIX-390 three states.

    Returns :data:`_HOT_STATUS_STATE_COMMITTED`, :data:
    `_HOT_STATUS_STATE_LEGACY` or ``""`` (unknown — never guessed). The
    committed branch reuses the FIX-393 writer-terminal predicate by
    identity; a cell that merely displays 「committed」 without the ops
    anchor was not written by the governed writer (B-1 hand-edit class) and
    resolves to unknown.
    """
    text = status_clean_cell(status)
    if not text:
        return ""
    if status_is_writer_committed_cell(text):
        return _HOT_STATUS_STATE_COMMITTED
    if text.startswith(_COMPLETED_STATUS_PREFIX):
        return _HOT_STATUS_STATE_LEGACY
    return ""


def _current_release_task_ids(*, plan_path, expand_task_ids):
    """Return task IDs from the active in-progress version roadmap row."""
    if not plan_path.is_file():
        return set()
    content = plan_path.read_text(encoding="utf-8")
    task_ids = set()
    for line in content.split("\n"):
        if not line.strip().startswith("| "):
            continue
        if "进行中" not in line:
            continue
        for raw in re.findall(r"[A-Z]+-\d+(?:~\d+)?", line):
            task_ids |= expand_task_ids(raw)
    return task_ids


def _normalize_priority(value):
    normalized = value.strip().strip("*")
    return normalized if normalized in ("P0", "P1", "P2") else ""


def _task_priority_from_table_parts(parts):
    priority_first = _normalize_priority(parts[1]) if len(parts) > 1 else ""
    if priority_first:
        return priority_first
    old_table_priority = _normalize_priority(parts[11]) if len(parts) >= 12 else ""
    return old_table_priority


def _split_governance_table_row(line):
    from governance_readers import split_governance_table_row
    return split_governance_table_row(line)


def _governance_table_cells(line):
    from governance_readers import governance_table_cells
    return governance_table_cells(line)


def _is_incomplete_task_status(status, *, status_is_completed_cell):
    """Active-task test for plan/snapshot status cells (FIX-292, DEC-181).

    Delegates to the W-7/BC-7 authoritative terminal-chain predicate
    :func:`_status_is_completed_cell` (FIX-291) instead of maintaining a
    second naive marker vocabulary — the authoritative predicate is
    consumed as-is, never rewritten here. Effects (AUDIT-149 §3 域 1):

    - a mixed transition chain whose trailing state is terminal
      (「🔄 进行中 (…) → ✅ 完成 (…)」, live: FIX-253/254/255/266/
      REL-069) is COMPLETED — the old 「进行中」 substring hit hid the
      trailing terminal state (M2; the FIX-274 M2-shaped cell still
      verdicts ACTIVE via the inherited 「未完成」 narrative guard);
    - narrative English tokens (``p0_pending=0``, live: FIX-291) no
      longer hit a ``pending`` substring blacklist (M3);
    - conservative verdicts of the authoritative predicate are inherited
      (reopened trailing-active chains stay ACTIVE; bare 「终止」 is not
      in the W-7 terminal vocabulary → stays ACTIVE — fail-safe side);
    - empty/missing status stays incomplete (fail-closed: completion
      that cannot be proven = active, aligned with the execution-packet
      ``assumption_record``; ragged-row M1 shapes therefore keep their
      conservative ACTIVE verdict — the data-side write guard is
      FEAT-011's domain).
    """
    text = str(status or "").strip()
    if not text:
        return True
    return not status_is_completed_cell(text)

# FIX-287③: subsection headings inside `## 当前活跃事项` that hold completed /
# archived content — collection suspends on them regardless of section order.
_NONACTIVE_SUBSECTION_MARKERS = ("最近完成", "已完成", "已归档", "依赖链")


def _is_nonactive_subsection(heading):
    """Return True for `### ` subsections that terminate active-task collection."""
    return any(marker in heading for marker in _NONACTIVE_SUBSECTION_MARKERS)


def parse_current_active_tasks(*, plan_path):
    """Parse hot active task rows from plan-tracker compact tables.

    FIX-481 (D1 third round): two live header shapes inside 当前活跃事项.
    The compact 优先级-led table keeps the ID-anchored relative-offset
    reads below (unchanged behavior). The 0.54-era ID-first 20-column
    table (任务ID / ``ID`` leading, 状态 at a header-declared offset,
    trailing 备注) is parsed by HEADER SEMANTICS through the same public
    mapping dependency analysis uses — ``task_priority.parse_task_dependencies``
    is fed the table's own header + the single row, so task_id / priority
    / status / target_version come from the SAME header-semantic mapping
    FIX-480 established (P5 single semantic source; no second header-index
    implementation lives here). Host python_game Layer1 probe 2026-11-04:
    the old positional read took the trailing 备注 cell as the status and
    阶段 as the title, so 20 ✅-terminal history rows fed
    ``_active_execution_packet_tasks`` as fake active P0/P1 — host Check
    18c~18i ×20 = 120 fake FAILs (89% of the host's 135 quick issues),
    and ``discover_governance_context``'s active_tasks projection was
    equally polluted.

    Field trade-offs on the ID-first shape (honest not-applicable
    marking): title is read from the header-declared 事项 column when
    present (task_priority's column index deliberately ignores
    display-only columns — the lookup here is by exact header cell name,
    not a second semantic index); dependency carries the task-family IDs
    the header declares (empty on the stock 0.54 template — fail-closed,
    never a neighbouring-column guess); target_version likewise
    header-declared or empty; closure_path stays empty (the 0.54 template
    declares no 闭环路径 column; consumers fall back closure_path →
    title → task_id).
    """
    if not plan_path.is_file():
        return []
    # Deferred peer import (matches the module's TPA call style, e.g. the
    # dependency-analysis entry): the public FIX-480 mapping is the single
    # header-semantics source for ID-first rows.
    from task_priority import parse_task_dependencies  # noqa: WPS433
    content = plan_path.read_text(encoding="utf-8")
    tasks = []
    in_active_section = False
    collecting = True
    # FIX-481: remember the header of the table currently being walked.
    # 优先级-led headers keep the compact positional parser; ID-first
    # headers (任务ID / ID leading — the lead labels task_priority's own
    # header detection accepts) switch data rows to header semantics.
    table_header_line = ""
    table_header_cells = []
    for line in content.split("\n"):
        if line.startswith("## 当前活跃事项"):
            in_active_section = True
            collecting = True
            continue
        if not in_active_section:
            continue
        if line.startswith("## "):
            # FIX-287③: the next top-level section always ends the active section.
            break
        if line.startswith("### "):
            # FIX-287③: order-tolerant subsection boundary — known completed/
            # archived subsections suspend collection; other subsections resume
            # it (host trackers may reorder, e.g. 最近完成 before active tables).
            collecting = not _is_nonactive_subsection(line)
            continue
        if not collecting:
            continue
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = _governance_table_cells(stripped)
        if not cells or cells[0] in {"优先级", "任务ID", "ID"}:
            # Header row: record the current table's shape, never emit
            # (the pre-FIX-481 skip set plus the plain-``ID`` lead FIX-480
            # recognizes).
            table_header_line = stripped
            table_header_cells = cells
            continue
        task_idx = next(
            (idx for idx, cell in enumerate(cells)
             if _TASK_ID_CELL_RE.match(cell.strip())),
            None,
        )
        if task_idx is None:
            continue
        acceptance = next((value for header, value in zip(table_header_cells, cells)
                           if header == "验收要求"), "")
        if table_header_cells and table_header_cells[0] in {"任务ID", "ID"}:
            # FIX-481 header-semantic path — single source: the row is
            # parsed by the same public mapping dependency analysis uses.
            # The micro-document (this table's header + this one row)
            # drives task_priority's own header detection and ID-first
            # dispatch, so the semantic columns land where the header
            # declares them — 状态 never the trailing 备注, 优先级 never
            # a prose scan hit. A row the shared parser cannot resolve
            # (no ID cell) is skipped — same conservative skip the
            # task_idx guard above applies to the compact path.
            dep_rows = parse_task_dependencies(
                table_header_line + "\n" + stripped)
            if not dep_rows:
                continue
            dep = dep_rows[0]
            title_idx = next(
                (idx for idx, cell in enumerate(table_header_cells)
                 if cell.strip() in {"事项", "任务项"}),
                None,
            )
            tasks.append({
                "task_id": dep.task_id,
                "priority": dep.priority,
                "title": (cells[title_idx].strip()
                          if title_idx is not None and title_idx < len(cells)
                          else ""),
                "dependency": ",".join(dep.dependencies),
                "target_version": dep.target_version,
                "closure_path": "",
                "status": dep.status,
                **({"acceptance": acceptance} if acceptance else {}),
                "raw_line": stripped,
            })
            continue
        task_id = cells[task_idx].strip().strip("*")
        priority = ""
        for cell in cells:
            normalized = _normalize_priority(cell)
            if normalized:
                priority = normalized
                break
        status = cells[-1].strip() if cells else ""
        title = cells[task_idx + 1].strip() if task_idx + 1 < len(cells) else ""
        dependency = cells[task_idx + 2].strip() if task_idx + 2 < len(cells) else ""
        target_version = cells[task_idx + 3].strip() if task_idx + 3 < len(cells) else ""
        closure_path = cells[task_idx + 4].strip() if task_idx + 4 < len(cells) else ""
        tasks.append({
            "task_id": task_id,
            "priority": priority,
            "title": title,
            "dependency": dependency,
            "target_version": target_version,
            "closure_path": closure_path,
            "status": status,
            **({"acceptance": acceptance} if acceptance else {}),
            "raw_line": stripped,
        })
    return tasks


def _active_execution_packet_tasks(*, status_is_completed_cell, parse_current_active_tasks):
    """Plan rows available for an explicit bulk handoff."""
    return [
        task for task in parse_current_active_tasks()
        if task.get("priority") in {"P0", "P1"} and _is_incomplete_task_status(task.get("status", ""),
                                                        status_is_completed_cell=status_is_completed_cell)
    ]
