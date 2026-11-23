"""Read plan tables, terminal status chains, recent decisions and next steps."""

import re
from datetime import date
from pathlib import Path


_W7_TERMINAL_MARKERS = (
    "✅", "已发布", "已关闭", "已终止", "已撤回", "失效", "不可信", "取消", "废弃",
)

_W7_ACTIVE_MARKERS = ("进行中", "待执行", "推进中", "⏳", "🔄")

_W7_TERMINAL_DATE_RE = re.compile(r"^[（(]\s*\d{4}-\d{2}-\d{2}")

_WRITER_OP_ANCHOR_RE = re.compile(r"〔op-[0-9a-f]{32}〕")


def _extract_section(content, heading, stop_headings=None):
    """Extract lines between a ## heading and the next ## heading."""
    lines = content.split("\n")
    capture = False
    result = []
    for line in lines:
        if line.strip() == heading or line.startswith(heading + "\n"):
            capture = True
            continue
        if capture:
            if stop_headings and any(line.startswith(sh) for sh in stop_headings):
                break
            if line.startswith("## ") and not line.strip() == heading:
                break
            result.append(line)
    return "\n".join(result)


def _normalize_task_status(status_text):
    """Map decorated plan-tracker status text to canonical task statuses."""
    status_text = (status_text or "").strip()
    for status in ("已完成", "进行中", "未开始", "已终止"):
        if status in status_text:
            return status
    return None


def _status_col_name(raw):
    """Normalize a header cell into a stable column key."""
    name = str(raw or "").strip().strip("`").strip("*").strip()
    return name.lower()


def _status_clean_cell(value):
    """Strip markdown/backtick decoration from a cell value."""
    return str(value or "").strip().strip("`").replace("**", "").strip()


def _status_iso_date(value):
    """First ISO date (YYYY-MM-DD) inside a cell, or None."""
    m = re.search(r"\d{4}-\d{2}-\d{2}", str(value or ""))
    return m.group(0) if m else None


def _last_marker_pos(text, markers):
    """Last (rightmost) occurrence position of any marker in ``text``, or -1."""
    best = -1
    for marker in markers:
        pos = text.rfind(marker)
        if pos > best:
            best = pos
    return best


def _status_table_stream(content):
    """Yield (header_cells, rows) for every markdown table in ``content``.

    Line-based: each table starts at a ``|`` row whose following non-blank
    row is the ``---`` separator. Blank lines are tolerated inside tables
    (live plan-tracker inserts them between sub-groups); a non-table line
    ends the table. Returns normalized (unwrapped, no leading/trailing
    empties) cell lists.
    """
    lines = content.split("\n")
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].strip()
        if not line.startswith("|"):
            i += 1
            continue
        header = [c.strip() for c in line.split("|")[1:-1]]
        j = i + 1
        while j < n and not lines[j].strip():
            j += 1
        if j >= n or not re.match(r"^\|[\s:\-|]+\|$", lines[j].strip()):
            i += 1
            continue
        k = j + 1
        rows = []
        while k < n:
            r = lines[k].strip()
            if not r:
                k += 1
                continue
            if not r.startswith("|"):
                break
            if re.match(r"^\|[\s:\-|]+\|$", r):
                k += 1
                continue
            rows.append([c.strip() for c in r.split("|")[1:-1]])
            k += 1
        yield header, rows
        i = k


def _status_priority_rank(priority):
    """P0 < P1 < P2; anything else sorts last."""
    m = re.match(r"\s*P([012])\b", str(priority or ""))
    return int(m.group(1)) if m else 9


def _status_project_name(config, overview):
    name = config.get("项目名称", "") or overview.get("project", "")
    return _status_clean_cell(name) if name else "N/A"


def parse_project_config(path=None, *, plan_path):
    from governance_readers import project_config
    return project_config((Path(path) if path is not None else plan_path).read_text(encoding="utf-8"))


def parse_overview(*, plan_path):
    from governance_readers import overview
    return overview(plan_path.read_text(encoding="utf-8"))


def parse_task_stats(*, plan_path):
    """Count task statuses from sample tracking table."""
    content = plan_path.read_text(encoding="utf-8")
    stats = {"已完成": 0, "进行中": 0, "未开始": 0, "已终止": 0}
    status_index = None
    for line in content.split("\n"):
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if not parts:
            continue
        if "状态" in parts:
            status_index = parts.index("状态")
            continue
        if all(set(p.strip()) <= {"-", " "} for p in parts):
            continue
        candidate_indices = []
        if status_index is not None:
            candidate_indices.append(status_index)
        if len(parts) >= 10:
            candidate_indices.append(9)
        if len(parts) >= 7:
            candidate_indices.append(6)
        for candidate_index in candidate_indices:
            status = _normalize_task_status(parts[candidate_index]) if candidate_index < len(parts) else None
            if status in stats:
                stats[status] += 1
                break
    return stats


def parse_task_table_rows(plan_content=None, *, plan_path):
    """Parse task-genre tables (header carries both ``ID`` and ``状态``).

    Every table whose header contains ``ID`` + ``状态`` contributes rows;
    a task ID appearing in several tables (active-items mirror + tracking
    table) is de-duplicated keeping the RICHEST row (most columns), so
    mirror duplicates never double-count statistics. Returns a list of
    dicts (``id`` / ``priority`` / ``status`` / ``actual_completion`` /
    ``_order`` / ``_width`` / ``_columns``).

    Status/priority/title resolution is header-indexed on clean rows and
    ID-anchored (dogfood convention) on over-split rows — prose containing
    pipe characters (e.g. ``无 ``| RISK-`` 行``) inflates the middle cells and
    the true status stays the LAST non-empty cell in that shape (the
    task_priority precedent), while host-style wide tables stay
    header-indexed (their status column is NOT the last cell).
    """
    content = plan_content if plan_content is not None else plan_path.read_text(encoding="utf-8")
    by_id = {}
    order = 0
    for header, rows in _status_table_stream(content):
        idx = {}
        for pos, name in enumerate(header):
            key = _status_col_name(name)
            if key and key in ("id", "状态", "优先级", "任务项", "事项", "依赖",
                               "目标版本", "实际完成", "gate", "证据", "任务名称"):
                idx.setdefault(key, pos)
        if "id" not in idx or "状态" not in idx:
            continue
        width = len(header)
        for cells in rows:
            if len(cells) <= max(idx.values()):
                continue
            # ID anchor (first bare-PREFIX-NNN cell) — invariant to duplicate
            # leading priority cells.
            id_pos = None
            tid = ""
            for pos, c in enumerate(cells):
                cand = _status_clean_cell(c)
                if re.match(r"^[A-Z]+-\d+$", cand):
                    id_pos = pos
                    tid = cand
                    break
            if not tid:
                continue
            clean = len(cells) == width

            def cell(key):
                pos = idx.get(key)
                if pos is None or pos >= len(cells):
                    return ""
                return _status_clean_cell(cells[pos])

            if clean:
                status = cell("状态")
                priority = cell("优先级")
                title = cell("任务项") or cell("事项") or cell("任务名称")
                deps = cell("依赖")
                target_version = cell("目标版本")
                actual_completion = _status_iso_date(cell("实际完成"))
                gate = cell("gate")
                evidence = cell("证据")
            else:
                # Over-split (prose pipes): dogfood shape — status is the LAST
                # non-empty cell; priority/title are ID-anchored.
                status = ""
                for c in reversed(cells):
                    if _status_clean_cell(c):
                        status = _status_clean_cell(c)
                        break
                priority = _status_clean_cell(cells[id_pos - 1]) if id_pos >= 1 else ""
                title = _status_clean_cell(cells[id_pos + 1]) if id_pos + 1 < len(cells) else ""
                deps = _status_clean_cell(cells[id_pos + 2]) if id_pos + 2 < len(cells) else ""
                target_version = _status_clean_cell(cells[id_pos + 3]) if id_pos + 3 < len(cells) else ""
                actual_completion = _status_iso_date(cell("实际完成"))
                gate = ""
                evidence = ""
            rec = {
                "id": tid,
                "priority": priority,
                "title": title,
                "status": status,
                "deps": deps,
                "target_version": target_version,
                "actual_completion": actual_completion,
                "gate": gate,
                "evidence": evidence,
                "_order": order,
                "_width": width,
                "_columns": cells,
            }
            order += 1
            prev = by_id.get(tid)
            if prev is None or rec["_width"] > prev["_width"]:
                by_id[tid] = rec
    return sorted(by_id.values(), key=lambda r: r["_order"])


def _status_plugin_freshness(plan_content=None, *, plan_path):
    """Advisory freshness: resolve_entry active_version vs plan-tracker record.

    NOT authoritative (DEC-096): the authoritative active version comes from
    ``resolve_entry.py``; this is the host-side driver signal only. The
    plan-tracker version is extracted permissively (``工作流版本: X.Y.Z`` in
    both the ``**key**:`` and ``**key**: value**`` shapes used live).
    """
    plan_version = ""
    if plan_content is None:
        plan_content = plan_path.read_text(encoding="utf-8") if plan_path.is_file() else ""
    m = re.search(r"工作流版本\s*[:：]?\s*([0-9]+\.[0-9]+\.[0-9]+)", plan_content) or \
        re.search(r"\b([0-9]+\.[0-9]+\.[0-9]+)\b", plan_content[:2000])
    if m:
        plan_version = m.group(1)
    active_version = ""
    try:
        from resolve_entry import read_active_version
        active_version = read_active_version() or ""
    except Exception:
        active_version = ""
    if not plan_version or not active_version:
        return {
            "status": "UNKNOWN", "active_version": active_version or "unknown",
            "plan_version": plan_version or "unknown",
        }
    try:
        active_tuple = tuple(int(part) for part in active_version.split("."))
        plan_tuple = tuple(int(part) for part in plan_version.split("."))
        is_ahead = active_tuple > plan_tuple
    except (TypeError, ValueError):
        is_ahead = False
    if active_version == plan_version:
        status = "UP TO DATE"
    elif is_ahead:
        status = "OUTDATED"
    else:
        status = "AHEAD"
    return {
        "status": status, "active_version": active_version,
        "plan_version": plan_version,
    }


def parse_recent_decisions(n=5, decision_content=None, *, governance_dir):
    """Last ``n`` decision-log rows ordered by (date, id) descending.

    FIX-270 R0 F2: live decision-log is a mixed-order file (newer entries
    interleaved with older ones), so document order is NOT time order.
    Rows are ranked by their ``日期`` cell (ISO date) and then by the
    numeric ID suffix. A row whose date is missing/unparseable is treated as
    the oldest (date.min + id -inf): it cannot masquerade as "recent" and is
    only returned when the file holds fewer than ``n`` dated rows — an
    honest fallback for legacy/ragged records, never a reordering.
    """
    content = decision_content if decision_content is not None else (
        (governance_dir / "decision-log.md").read_text(encoding="utf-8")
        if (governance_dir / "decision-log.md").is_file() else ""
    )
    rows = []
    for header, table_rows in _status_table_stream(content):
        idx = {}
        for pos, name in enumerate(header):
            key = _status_col_name(name)
            if key in ("编号", "日期", "主题", "决策内容"):
                idx.setdefault(key, pos)
        if "编号" not in idx:
            continue
        for cells in table_rows:
            if len(cells) <= max(idx.values()):
                continue
            def cell(key):
                pos = idx.get(key)
                return _status_clean_cell(cells[pos]) if pos is not None and pos < len(cells) else ""
            rid = cell("编号")
            if not re.match(r"^[A-Z]+-\d+$", rid):
                continue
            rows.append({
                "id": rid,
                "date": cell("日期"),
                "topic": (cell("主题") or cell("决策内容"))[:60],
            })

    def _sort_key(rec):
        parsed = None
        if rec["date"] and rec["date"] != "—":
            try:
                parsed = date.fromisoformat(rec["date"][:10])
            except ValueError:
                parsed = None
        id_num = 0
        m = re.match(r"^[A-Z]+-(\d+)$", rec["id"])
        if m:
            id_num = int(m.group(1))
        if parsed is None:
            return (False, date.min, -1)   # 无日期 → 视为最旧（兜底，不可冒充"最近"）
        return (True, parsed, id_num)

    rows.sort(key=_sort_key, reverse=True)
    return rows[:n]


def _w7_terminal_assertion_positions(text, *, markers=_W7_TERMINAL_MARKERS, terminal_date=_W7_TERMINAL_DATE_RE):
    """Positions of terminal-state ASSERTIONS in a mixed status cell.

    R1 (segment-scope tightening, CODE-R0 P2-1 / DESIGN-R0 P2-3): a
    VOCABULARY marker (已发布/已关闭/…) is an assertion only when it is the
    state word of a transition segment — segment-start (cell start / after
    → / — / ——, with only whitespace, an optional ✅ qualification and/or
    the perfective prefix 「已」 before it) AND immediately followed by a
    date annotation （(YYYY-MM-DD…） or the cell end. Narrative mentions
    (subject-prefixed 「方案A已撤回」, version contexts 「0.78.1 已发布」,
    comma continuations without a date) are NOT assertions.

    R2 (DESIGN-R1 P1-R1): the ✅ GLYPH is an unambiguous state glyph — not a
    narrative word — so it keeps its assertion status under the looser
    segment rule: ✅ at a segment start + a date annotation ANYWHERE in the
    same segment (up to the next transition boundary or cell end) asserts
    the terminal state. This restores the pre-existing completed
    classification of 「⏳ 审计中 (…) → ✅ 分析完成+规划落地 (…)——…」
    (live AUDIT-143, P0) that the R1 tightening regressed to ACTIVE; the
    position comparison in ``_status_is_completed_cell`` still keeps any
    later active marker (reopened) ACTIVE.
    """
    positions = []
    for marker in markers:
        start = 0
        while True:
            pos = text.find(marker, start)
            if pos < 0:
                break
            start = pos + len(marker)
            # (a) segment start: nothing but whitespace / an optional ✅
            # qualification / the perfective 「已」 prefix between the
            # transition boundary (or cell start) and the marker.
            head = text[:pos].rstrip()
            while head.endswith(("✅", "已")):
                head = head[:-1].rstrip()
            if head and not head.endswith(("→", "—")):
                continue  # narrative mention (subject/version prefix precedes)
            if marker == "✅":
                # R2: ✅ state glyph — a date annotation anywhere in the SAME
                # segment (before the next transition boundary) asserts.
                seg_end = len(text)
                for boundary in ("→", "—"):
                    bpos = text.find(boundary, pos + len(marker))
                    if bpos != -1 and bpos < seg_end:
                        seg_end = bpos
                segment = text[pos:seg_end]
                if re.search(r"[（(]\s*\d{4}-\d{2}-\d{2}", segment):
                    positions.append(pos)
                continue
            # (b) vocabulary marker: terminal date annotation (or cell end)
            # immediately after the marker.
            rest = text[pos + len(marker):].lstrip()
            if rest and not terminal_date.match(rest):
                continue  # comma continuation / trailing prose, not a state
            positions.append(pos)
    return positions


_DEFAULT_STATE_CHAIN = object()


def _status_is_writer_committed_cell(text, *, operation_anchor=_WRITER_OP_ANCHOR_RE, state_chain=_DEFAULT_STATE_CHAIN):
    """True when an already-cleaned status cell is a writer-committed
    TERMINAL row (FIX-393): the writer chain's first hit is ``committed``
    AND the ops receipt anchor 〔op-<32hex>〕 is present. The anchor is the
    writer's machine provenance mark; a cell that merely displays the word
    「committed」 without it was not written by the governed writer (the
    B-1 hand-edit class) and is never guessed terminal.
    """
    if state_chain is _DEFAULT_STATE_CHAIN:
        from task_row_update import _STATE_MARKER_CHAIN as state_chain
    if not operation_anchor.search(text):
        return False
    for state, pattern in state_chain:
        if pattern.search(text):
            return state == "committed"
    return False


def _status_is_completed_cell(cell, *, active_markers=_W7_ACTIVE_MARKERS,
                              writer_committed=_status_is_writer_committed_cell,
                              terminal_positions=_w7_terminal_assertion_positions):
    """Completed status test for task rows (dogfood ✅ conventions + host text-only).

    - Any cell with "未完成"/"待完成" is NOT completed.
    - "已完成" → completed (host text-only style).
    - FIX-393: a writer-committed terminal cell (:func:
      `writer_committed` — ops receipt anchor + the writer
      chain's committed token, never the display prefix) → completed. The
      未完成/待完成 veto below outranks it (conservative narrative guard).
    - Leading ``✅`` (dogfood) → completed unless the cell carries an explicit
      active marker (未完成/待完成/进行中/待执行, plus the ⏳/🔄 emoji per
      FIX-291 W-7 — a mixed chain is judged by its trailing state below).
    - Bare ``完成`` followed by a bracket or end-of-cell (e.g. "✅ 完成 (…)"
      / "完成（…)") → completed.
    - W-7/BC-7 (FIX-291, R1 assertion scope + R2 ✅ glyph rule): a terminal
      ASSERTION (:func:`terminal_positions` — the state word
      of a transition segment with a terminal date; for the ✅ glyph the
      date may appear anywhere in the same segment, R2/DESIGN-R1 P1-R1)
      that appears after the last active marker makes the cell's trailing
      (true) state terminal → completed. Narrative terminal-word mentions,
      version contexts and active-trailing cells (e.g.
      「✅ 已发布 → 🔄 reopened」) keep the ACTIVE verdict (conservative: no
      aggressive downgrade).
    """
    text = _status_clean_cell(cell)
    if "未完成" in text or "待完成" in text:
        return False
    if "已完成" in text:
        return True
    # FIX-393: writer-committed terminal rows — governed-writer authority
    # (the ops receipt anchor + the writer's own marker chain by identity),
    # never the display-prefix text.
    if writer_committed(text):
        return True
    # Dogfood cells may carry a transition chain ("⏳ 等待 → ✅ 完成"): any ✅
    # in the status cell marks a delivered endpoint — UNLESS an active marker
    # (text wording or the ⏳/🔄 emoji, FIX-291 W-7) makes the cell a mixed
    # chain, in which case the trailing-state rule below decides.
    if "✅" in text and not any(m in text for m in (
            "未完成", "待完成", "进行中", "待执行", "⏳", "🔄")):
        return True
    # W-7/BC-7 (R1): trailing terminal ASSERTION wins in a mixed chain.
    assertions = terminal_positions(text)
    if assertions:
        active_pos = _last_marker_pos(text, active_markers)
        if max(assertions) > active_pos:
            return True
    return bool(re.search(r"完成\s*(?:[（(]|$)", text))


def _status_is_terminal_cell(cell, *, decorations, is_completed):
    """True when a plan-table status cell is a TERMINAL state (FIX-479).

    Terminal ⟺ the canonical completed predicate
    (:func:`is_completed`) fires on the cell AS WRITTEN or
    after stripping a leading decoration-emoji run (「⏳ ✅ committed」:
    the leading ⏳/🔄/📋/🆕/⏸ is a display decoration, not a state).
    Genuine active cells stay non-terminal — stripping their decoration
    leaves an active cell (「🔄 进行中」→「进行中」,「📋 规划中」→「规划中」)
    and the completed predicate keeps returning False, so the overdue
    and DRI semantics for active rows are unchanged.
    """
    text = _status_clean_cell(cell)
    if is_completed(text):
        return True
    stripped = text
    while stripped[:1] in decorations:
        stripped = stripped[1:].lstrip()
    if stripped != text:
        return is_completed(stripped)
    return False


def _status_raw_dependency_ids(rec, *, task_id_pattern):
    """Task-family IDs referenced by a task row (the 依赖 cell when present,
    else a whole-row scan for host-style tables without a 依赖 column).
    The row's own ID and cross-entity prefixes (RISK/DEC/…) are excluded at
    the caller via the status map (unknown prefixes never block)."""
    text = rec.get("deps") or ""
    if not text and rec.get("_columns"):
        text = " ".join(str(c) for c in rec["_columns"])
    ids = set()
    for m in task_id_pattern.finditer(str(text)):
        tid = f"{m.group(1)}-{m.group(2)}"
        if tid != rec.get("id"):
            ids.add(tid)
    return ids


def _status_next_steps(plan_content, max_results=3, *, read_rows, is_completed, dependency_ids):
    """建议下一步线索：轻量派生（header-driven 任务行 + 依赖状态检查）。

    只在 plan-tracker 文本上做确定性分析，绝不运行 check-governance。
    完成判定用 ``is_completed``（同时识别 ✅ 前缀 dogfood 惯例与
    宿主 text-only 状态），依赖引用未知 ID 不阻断（推荐线索非门禁；
    权威 fail-closed 依赖分析仍由 task-priority-analysis 承载）。
    fail-safe：任何异常返回 []。
    """
    try:
        rows = read_rows(plan_content)
        status_map = {r["id"]: is_completed(r["status"]) for r in rows}
        candidates = []
        for r in rows:
            if status_map.get(r["id"]):
                continue
            unresolved = [
                d for d in dependency_ids(r)
                if d in status_map and not status_map[d]
            ]
            if unresolved:
                continue
            candidates.append(r)
        candidates.sort(
            key=lambda r: (
                _status_priority_rank(r["priority"]),
                0 if "进行中" in r["status"] else 1,
                r["_order"],
            )
        )
        return [
            {
                "task_id": r["id"],
                "priority": r["priority"],
                "status": _status_clean_cell(r["status"]),
                "target_version": r["target_version"],
            }
            for r in candidates[:max_results]
        ]
    except Exception:
        return []


def parse_recent_completed_tasks(rows, n=5, *, is_completed):
    """Last ``n`` completed tasks, by completion date desc (fallback: row order)."""
    done = [r for r in rows if is_completed(r["status"])]

    def _completion_date(rec):
        d = rec.get("actual_completion") or _status_iso_date(rec["status"])
        return d if d else "0000-00-00"

    done.sort(
        key=lambda r: (_completion_date(r), r["_order"]),
        reverse=True,
    )
    return done[:n]


def _status_task_stats(rows, *, is_completed):
    """Aggregate deduped task-table rows into per-status counts + P0 pending."""
    stats = {"已完成": 0, "进行中": 0, "未开始": 0, "已终止": 0}
    p0_pending = 0
    for r in rows:
        status = _normalize_task_status(r["status"] or "")
        if status:
            stats[status] += 1
        if r["priority"].strip() == "P0" and not is_completed(r["status"]):
            p0_pending += 1
    return stats, p0_pending
