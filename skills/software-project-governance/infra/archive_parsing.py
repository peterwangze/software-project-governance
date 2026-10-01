#!/usr/bin/env python3
"""
Pure parsing / classification support for archive.py — FIX-417 minimal
cohesive split of the 28o architecture-health findings.

This module is the READ-ONLY judgment face of the governance archive
engine: version parsing, task-status / writer-state determination,
priority / decision / risk row classification, row-family line parsing,
ref-verdict typing, version-roadmap parsing, and the migrate_by_version
pure stage helpers. (Archive-file extraction, damage labeling, and the
index/integrity faces live in the sibling archive_indexing.py, which
imports the shared judgment primitives from here — one-way, no cycle.)
Every function here is a PURE function of its inputs:

  * none reads the module-level ROOT / PLUGIN_ROOT / HOST_PROJECT_ROOT seam,
    so ``patch.object(archive, "ROOT", ...)`` semantics (FIX-187 / FIX-242
    dual-root model) cannot be affected by the move;
  * none is in the tests' function-level patch surface (the patched helpers
    — _migration_write_batch / _atomic_write_text / _migration_write_journal
    / _decision_authority_state / _window_end_release_date — stay in
    archive.py together with their callers);
  * none calls back into archive.py (the moved set is closure-complete).

archive.py re-imports every name below, so ``archive.<name>`` keeps working
(tests address these private helpers directly) and the isolated
spec_from_file_location loader for archive.py resolves this module through
the same sys.path entries (infra/ is sys.path[0] under script execution and
is explicitly injected by the test suite).

FIX-417 moved 44 functions + 17 constants verbatim from archive.py into
this split and added 10 newly-extracted pure stage helpers (no behavior
change — see the FIX-417 evidence for the dependency-closure proof).
Final inventory: 54 top-level functions + 18 constants across the two
companions (archive_parsing: 31 functions + 17 constants;
archive_indexing: 23 functions + 1 constant).
"""

import re
import unicodedata
from datetime import datetime

def _parse_version_from_title(title_line):
    """Extract version string from a section title.

    Supports diverse formats:
      - '### v0.11.0 — Foo'           (with em-dash separator)
      - '## 0.24.0 - Bar'             (with hyphen separator)
      - '### 0.11.0（已完成）'        (Chinese parentheses, no separator)
      - '### 0.11.0 交付清单'        (description text, no separator)
      - '### 0.32.0'                  (bare version, no description)
      - '### 1.0.0 依赖链'            (Chinese text following version)

    Returns (version_str, description) or (None, None).
    """
    # Separator and description group made optional (?:...)?
    m = re.match(
        r"^#{1,6}\s+(?:v)?(\d+\.\d+\.\d+)(?:\s*[—\-]?\s*(.*?))?$",
        title_line.strip()
    )
    if m:
        desc = m.group(2)
        return m.group(1), desc.strip() if desc else ""
    return None, None

def _version_to_tuple(version_str):
    """Convert '0.11.0' to (0, 11, 0) for comparison.

    FIX-162: defensive against non-semver strings (e.g. '未规划版本',
    '1.0.0', empty). Returns None for non-parseable input so callers can
    treat it as out-of-range.
    """
    if not version_str:
        return None
    # Extract the first x.y.z token if the string has extra text
    m = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", version_str)
    if not m:
        return None
    return tuple(int(p) for p in m.groups())

def _version_in_range(version_str, start, end):
    """Check if version_str is in [start, end] inclusive.

    FIX-162: returns False for non-parseable version_str (None tuple) so
    tasks/decisions with placeholder versions (e.g. '未规划版本') are never
    matched into an archive range.
    """
    vt = _version_to_tuple(version_str)
    if vt is None:
        return False
    st = _version_to_tuple(start)
    et = _version_to_tuple(end)
    if st is None or et is None:
        return False
    return st <= vt <= et

def _find_version_sections(content):
    """Parse plan-tracker content into version sections.

    Returns list of dicts: {version, title, start_line, end_line, task_lines}
    where task_lines are the table row lines for tasks.
    """
    lines = content.split("\n")
    sections = []
    current_section = None

    for i, line in enumerate(lines):
        # Detect version section headers
        v, desc = _parse_version_from_title(line)
        if v is not None:
            if current_section:
                current_section["end_line"] = i - 1
                sections.append(current_section)

            current_section = {
                "version": v,
                "title": line.strip(),
                "start_line": i,
                "end_line": len(lines) - 1,
                "task_lines": [],
                "table_started": False,
                "header_line": None,
                "separator_line": None,
            }
            continue

        # Close current section on non-version headings
        if current_section is not None:
            stripped = line.strip()
            if (stripped.startswith("### ") or stripped.startswith("## ")):
                v_test, _ = _parse_version_from_title(line)
                if v_test is None:
                    current_section["end_line"] = i - 1
                    sections.append(current_section)
                    current_section = None
                    continue

        if current_section:
            stripped = line.strip()
            # Detect table separator row: | --- | --- | or | :--- | :---: | etc.
            # The format is "|" followed by hyphens (optional colons) separated by "|"
            if stripped.startswith("|") and re.match(r"^\|[\s\-:|\t]+\|$", stripped):
                current_section["separator_line"] = i
                # FIX-158: capture the header row (line before separator) so we
                # can locate the 状态 column dynamically (not hardcoded to col 10).
                if i > 0 and current_section["header_line"] is None:
                    prev = lines[i - 1].strip()
                    if prev.startswith("|"):
                        current_section["header_line"] = lines[i - 1]
                continue
            if stripped.startswith("|") and current_section["separator_line"] is not None:
                # This is a table row - check if it's a task row
                m = re.match(r"\|\s*([A-Z]+-\d+)\s*\|", stripped)
                if m:
                    current_section["task_lines"].append((i, line, m.group(1)))
            elif stripped.startswith("- [") and "**" in stripped:
                # Checklist format: - [x] **TASK_ID**: description
                m = re.match(r"-\s*\[(x| )\]\s*\*\*([A-Z]+-\d+)\*\*[^:]*:", stripped)
                if m:
                    task_id = m.group(2)
                    status = "已完成" if m.group(1) == "x" else "进行中"
                    synthetic_line = f"| {task_id} | ... | ... | ... | ... | ... | ... | ... | ... | {status} |"
                    current_section["task_lines"].append((i, synthetic_line, task_id))

    if current_section:
        current_section["end_line"] = len(lines) - 1
        sections.append(current_section)

    # ── 样例跟踪表 detection ──────────────────────────────────────
    # Plan-tracker may contain a "## 样例跟踪表" section with a large table
    # of historical tasks (20-column format).  These tasks live outside of
    # version sections and were previously invisible to the archive engine.
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == '## 样例跟踪表':
            header_seen = False
            table_started = False
            sample_tasks = []
            sample_header_line = None  # FIX-158: capture header for status column

            for j in range(i + 1, len(lines)):
                sl = lines[j].strip()

                # Stop at next ## heading (parent section boundary)
                if sl.startswith('## ') and '样例跟踪表' not in sl:
                    break

                # ### sub-heading: reset table state, continue scanning next table
                if sl.startswith('### '):
                    header_seen = False
                    table_started = False
                    sample_header_line = None
                    continue

                if not table_started:
                    if sl.startswith('|') and 'ID' in sl and '状态' in sl:
                        header_seen = True
                        sample_header_line = lines[j]  # FIX-158: capture header row
                        continue
                    if header_seen and sl.startswith('|') and '---' in sl:
                        table_started = True
                        continue
                    continue

                if table_started:
                    if not sl.startswith('|'):
                        # End of current sub-table, keep scanning for next sub-table.
                        # FIX-158: do NOT reset sample_header_line here — the
                        # captured header is still needed for status parsing of
                        # already-collected tasks.
                        table_started = False
                        header_seen = False
                        continue
                    # Check if it's a task row (ID column with TASKID-NNN format)
                    m = re.match(r"\|\s*([A-Z]+-\d+)\s*\|", sl)
                    if m:
                        task_id = m.group(1)
                        sample_tasks.append((j, lines[j], task_id))

            if sample_tasks:
                # Use the earliest published version from the roadmap so it
                # falls inside the archive range [earliest, second-latest].
                roadmap_versions = _parse_version_roadmap(content)
                published = [
                    v for v, s in roadmap_versions if s == '已发布'
                ]
                if published:
                    earliest_version = sorted(
                        published, key=_version_to_tuple
                    )[0]
                else:
                    earliest_version = '0.1.0'

                sections.append({
                    "version": earliest_version,
                    "title": "## 样例跟踪表",
                    "start_line": i,
                    "end_line": i,
                    "task_lines": sample_tasks,
                    "table_started": True,
                    "header_line": sample_header_line,  # FIX-158
                    "separator_line": None,
                    "sample_table": True,
                })
            break  # Only process the first 样例跟踪表 section

    return sections, lines

def _find_status_column(header_line):
    """FIX-158: find the column index of the 状态 (status) cell in a table header.

    Returns the 0-based index among data cells, or None if not found.
    Handles all three table layouts:
      - 7-col priority table: '| 优先级 | ID | ... | 状态 |' → status last
      - 10-col version section: '| 任务ID | 描述 | ... | 状态 |' → col 9
      - 20-col sample table: '| ID | 阶段 | ... | 状态 | ... |' → col 9
    """
    if not header_line or not header_line.strip().startswith("|"):
        return None
    parts = [p.strip() for p in header_line.split("|")]
    data_cells = parts[1:-1] if len(parts) >= 2 else parts
    for idx, cell in enumerate(data_cells):
        if cell == "状态":
            return idx
    return None

def _parse_task_status(line, status_col=None):
    """Extract status from a task table row.

    FIX-158: status column is no longer hardcoded to parts[10]. Real plan-tracker
    uses a 7-column table (| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |)
    where status is the last data column. Legacy version-section tables use a
    10-column format and the 20-column sample table puts 状态 in column 10.

    Args:
        line: the markdown table row
        status_col: optional explicit column index (0-based among data cells).
                    If None, defaults to the last data column (safe for 7-col
                    priority tables; callers that know the table is 10/20-col
                    should pass status_col explicitly or use _find_status_column).

    Strips leading/trailing emoji, symbols, spaces, and format characters
    to handle patterns like "✅ 已完成", "⏳ 进行中", "🚧 阻塞中",
    "已完成 ✅". Preserves all text characters (CJK, Latin, Cyrillic, etc).
    """
    parts = [p.strip() for p in line.split("|")]
    # parts[0] and parts[-1] are empty (leading/trailing |). Data cells are parts[1:-1].
    data_parts = parts[1:-1] if len(parts) >= 2 else parts
    if len(data_parts) < 2:
        return None

    if status_col is None:
        # Default: last data column (7-col priority table puts status last)
        status = data_parts[-1]
    elif status_col < len(data_parts):
        status = data_parts[status_col]
    else:
        # Fallback to last column if requested col out of range
        status = data_parts[-1]
    # Strip leading emoji/symbol/space/format characters only
    # (not all non-CJK — preserve Latin/Cyrillic/etc text)
    while status:
        cat = unicodedata.category(status[0])
        # So=Symbol_Other (emoji, etc), Sk=Modifier_Symbol, Sc=Currency_Symbol,
        # Sm=Math_Symbol, Zs=Space_Separator, Cf=Format
        if cat in ('So', 'Sk', 'Sc', 'Sm', 'Zs', 'Cf'):
            status = status[1:].strip()
        else:
            break
    # Also strip trailing emoji/symbols
    while status:
        cat = unicodedata.category(status[-1])
        if cat in ('So', 'Sk', 'Sc', 'Sm', 'Zs', 'Cf'):
            status = status[:-1].strip()
        else:
            break
    return status

# FIX-393 — writer-terminal recognition (0.89.0). Local mirror of the
# governed writer's status vocabulary (task_row_update._STATE_MARKER_CHAIN —
# byte-pinned by tests/test_fix393_writer_terminal_states.py; this module
# keeps no peer import so it stays standalone-runnable). Terminal ⟺ chain
# first-hit is ``committed`` (contracts.TASK_TRANSITIONS' only terminal
# state) AND the ops receipt anchor 〔op-<32hex>〕 is present — display-prefix
# text is never an authoritative status source. Search-anywhere anchor: live
# cells may carry narrative brackets after the anchor (FEAT-061).
_WRITER_STATE_MARKER_CHAIN = (
    ("completed", re.compile(r"✅\s*完成")),
    ("blocked", re.compile(r"⛔|BLOCKED")),
    ("dev", re.compile(r"🔄|进行中")),
    ("committed", re.compile(r"\bcommitted\b|已提交")),
    ("approved", re.compile(r"\bapproved\b|已审查")),
    ("review", re.compile(r"\breview\b|待审查|审查中")),
    ("triaged", re.compile(r"\btriaged\b|已\s*triage")),
)
_WRITER_OP_ANCHOR_RE = re.compile(r"〔op-[0-9a-f]{32}〕")

def _writer_chain_state(status):
    """First hit of the writer's ordered marker chain, or None (unknown)."""
    for state, pattern in _WRITER_STATE_MARKER_CHAIN:
        if pattern.search(status):
            return state
    return None

def _task_status_is_writer_committed(status):
    """True when a status cell is a writer-committed TERMINAL row (FIX-393).

    The governed writer (task_row_update) is the only sanctioned write path
    for task rows; its committed flip always appends the ops receipt anchor
    〔op-<32hex>〕. A cell displaying the word 「committed」 WITHOUT the
    anchor was not writer-written and is never guessed terminal.
    """
    s = str(status or "")
    if not _WRITER_OP_ANCHOR_RE.search(s):
        return False
    return _writer_chain_state(s) == "committed"

def _task_status_is_archivable(status):
    """FIX-158: determine whether a task status means the task is completed/archivable.

    Real plan-tracker uses many ✅-variants beyond strict "已完成":
    已发布, 保守闭环, 完成候选, 发布候选完成, 已交付, 调查完成, 诊断完成,
    设计完成, 实现完成, 发布完成, 已撤回/失效, 调研归档, 审视归档, etc.
    All of these indicate the task is closed and can be archived.
    Open states (进行中, 待启动, 停滞, 阻塞, 待) must NOT be archived.
    FIX-393: writer-committed terminal rows (ops receipt anchor + the
    writer's committed token) are archivable too — the 0.88.0 delivered
    batch (「committed 已 lock 待派发 …〔op-…〕」) matches no legacy
    closed word-form and was invisible to the archiver. A committed-token
    cell WITHOUT the anchor fails closed: it is never guessed terminal from
    its display prefix and stays un-archivable.
    """
    if not status:
        return False
    # Open/pending markers — never archive
    open_markers = ("进行中", "待启动", "停滞", "阻塞", "待决", "待定", "未完成", "TO_BE")
    if any(m in status for m in open_markers):
        return False
    # FIX-393: writer-committed terminal rows — the governed writer's ops
    # receipt anchor + its own marker chain are the closed signal.
    if _task_status_is_writer_committed(status):
        return True
    # FIX-393: a committed-token cell WITHOUT the anchor was not written by
    # the governed writer — its display prefix is never guessed terminal, so
    # it is judged ONLY by the explicit closed-marker scan below (which it
    # must fail: 「committed 审查中」/「已提交 (…)」 match no closed marker;
    # a narrative 已发布/已完成 word-form after the committed prefix would
    # otherwise be misread by that scan).
    if _writer_chain_state(status) == "committed":
        return False
    # Closed/delivered markers — archivable
    closed_markers = (
        "✅", "已完成", "已交付", "已发布", "保守闭环", "完成候选",
        "发布候选完成", "调查完成", "诊断完成", "设计完成", "实现完成",
        "发布完成", "已撤回", "失效", "调研归档", "审视归档", "归档",
    )
    return any(m in status for m in closed_markers)

def _parse_priority_table_tasks(content, anomalies_out=None):
    """FIX-158: parse the '### 优先级一览' / '### 最近完成' priority tables.

    Real plan-tracker stores ALL tasks in non-version sections like
    '### 优先级一览' with a 7-column format:
        | 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
        | **P0** | FIX-084 | ... | ... | 0.38.0 | ... | ✅ 已完成 |
    ID is in column 2 (index 1), target version in column 5 (index 4),
    status in the last column. This format was invisible to the original
    archive engine (which required ID in column 1 and version section headers).

    FIX-301 (AUDIT-150 / REFACTOR-archive-recognition-fix): the real table
    interleaves blank lines, prose and blockquote notes BETWEEN priority
    groups. The old scan reset on ANY non-table line, so only the FIRST
    group was ever seen (32 of 208 real rows) while 88 in-range completed
    rows were invisible — the "触发器满足但无可归档数据" black box. Scan
    semantics now match the sibling evidence mapper
    ``_parse_completed_task_versions`` (FIX-235): blank lines / prose /
    blockquote notes do NOT terminate the scan; only headings do. The two
    parsers must stay in sync.

    Rows whose pipe layout deviates from the 7-column form (unescaped pipe
    count != 8) are skipped conservatively — their column alignment cannot be
    trusted for PHYSICAL migration (the hot row is deleted after archiving) —
    and reported through ``anomalies_out`` (list receiving ``(task_id,
    line_index, pipe_count)`` tuples) for the auditable unknown-structure
    list; they are never deleted.

    FEAT-074 (DEC-278 unit one item 6): the count and the split are UNESCAPED-
    pipe-aware. A row may legitimately embed ``\\|`` inside a cell (rendered
    as a literal pipe — the FEAT-047 row carried ``block\\|advisory`` and was
    misjudged as 9-column anomalous even though it has exactly 7 real
    columns); raw-pipe counting made such completed hot rows invisible to
    both the task migration and the completed-hot version mapping. Splitting
    on unescaped pipes keeps the escape sequence inside its cell
    (content-preserving — the row text is never rewritten).

    Returns list of (line_index, original_line, task_id, target_version, status).
    """
    lines = content.split("\n")
    tasks = []
    in_priority_table = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Detect priority table header: first data cell is 优先级, second is ID
        if stripped.startswith("|"):
            cells = [c.strip() for c in _split_table_row_escaped_aware(stripped)]
            data_cells = cells[1:-1] if len(cells) >= 2 else cells
            if (len(data_cells) >= 2
                    and data_cells[0] == "优先级"
                    and data_cells[1] == "ID"):
                in_priority_table = True
                continue
        # Reset ONLY on section headings. Blank lines / prose / blockquote
        # notes between priority groups no longer terminate the scan
        # (FIX-301; parity with _parse_completed_task_versions / FIX-235).
        if stripped.startswith("###") or stripped.startswith("##"):
            in_priority_table = False
            continue
        if not in_priority_table:
            continue
        if not stripped.startswith("|"):
            # Inside the table region but not a table row — keep scanning.
            continue
        # Skip separator row
        if re.match(r"^\|[\s\-:|\t]+\|$", stripped):
            continue
        parts = [p.strip() for p in _split_table_row_escaped_aware(line)]
        data_parts = parts[1:-1] if len(parts) >= 2 else parts
        # Need at least: priority, ID, ... , status (7 cols typical)
        if len(data_parts) < 3:
            continue
        # ID is in column 2 (data_parts[1]); strip markdown bold
        raw_id = data_parts[1]
        task_id = re.sub(r"[`*]", "", raw_id).strip()
        if not re.match(r"^[A-Z]+-\d+$", task_id):
            continue
        # FIX-301/FEAT-074: unescaped-pipe-count guard — anomalous layout
        # (extra REAL pipes inside cells, shifted columns) means column
        # alignment cannot be trusted for physical migration. Skip
        # conservatively, report for audit.
        if _count_unescaped_pipes(stripped) != 8:
            if anomalies_out is not None:
                anomalies_out.append((task_id, i, _count_unescaped_pipes(stripped)))
            continue
        # Target version in column 5 (data_parts[4]) if present
        target_version = ""
        if len(data_parts) >= 5:
            target_version = re.sub(r"[`*]", "", data_parts[4]).strip()
        # Status is last data column
        status = data_parts[-1]
        tasks.append((i, line, task_id, target_version, status))
    return tasks

def _parse_completed_task_versions(content):
    """FIX-235: map COMPLETED hot plan-tracker tasks to their target version.

    plan-tracker keeps every task row in the priority table for full
    traceability (EVD-854) instead of physically archiving them; evidence rows
    referencing those tasks could therefore never migrate (task_versions was
    built only from archive/tasks/ files). This helper scans the priority
    tables tolerantly — blank lines / blockquote notes inside a table no
    longer terminate the scan, matching the real plan-tracker layout — and
    returns {task_id: target_version} for archivable-status tasks with a
    parseable target version. Rows whose pipe count deviates from the 7-column
    layout are skipped (column alignment cannot be trusted).

    Used ONLY for evidence migration (decisions/risks keep the archive-only
    mapping, whose contract requires the related task to be physically
    archived).
    """
    result = {}
    lines = content.split("\n")
    in_priority_table = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("###") or stripped.startswith("##"):
            in_priority_table = False
            continue
        if not stripped.startswith("|"):
            # Blank lines / prose / blockquote notes inside a table region do
            # NOT terminate the scan (the real plan-tracker interleaves them
            # between priority groups).
            continue
        cells = [c.strip() for c in _split_table_row_escaped_aware(stripped)]
        data_cells = cells[1:-1] if len(cells) >= 2 else cells
        if (len(data_cells) >= 2
                and data_cells[0] == "优先级"
                and data_cells[1] == "ID"):
            in_priority_table = True
            continue
        if not in_priority_table:
            continue
        if re.match(r"^\|[\s\-:|\t]+\|$", stripped):
            continue
        # FEAT-074: unescaped-pipe guard (parity with
        # _parse_priority_table_tasks — escaped "\|" inside a cell is NOT a
        # column separator; the FEAT-047 row is a well-formed 7-column row).
        if _count_unescaped_pipes(stripped) != 8:
            # Anomalous layout (extra REAL pipes inside cells, shifted
            # columns) — column alignment cannot be trusted, skip
            # conservatively.
            continue
        if len(data_cells) < 5:
            continue
        raw_id = re.sub(r"[`*]", "", data_cells[1]).strip()
        if not re.match(r"^[A-Z]+-\d+$", raw_id):
            continue
        target_version = re.sub(r"[`*]", "", data_cells[4]).strip()
        if not _version_to_tuple(target_version):
            continue
        status = data_cells[-1]
        if not _task_status_is_archivable(status):
            continue
        result.setdefault(raw_id, target_version)
    return result


_DECISION_RELATED_COLUMN_HEADER = "关联任务"

# Canonical decision-log schema length (编号/日期/主题/背景/决策内容/备选方案/
# 选择原因/影响范围/决策人/关联任务/后续动作). FIX-342 (review-FIX-341-312-
# CODE-R0 P2-2): the headerless fallback may trust the second-to-last cell
# ONLY when the row has exactly this many columns — a shorter row's [-2] cell
# is not the 关联任务 column (a title/ctx archived ref there would be misread
# as a governing ref).
_DECISION_SCHEMA_COLUMNS = 11

# Governing-ref extraction uses the SAME negative-lookbehind discipline as
# task_priority._ID_TOKEN_RE: REVIEW-FIX-310 is ONE cross-entity review
# record, not the FIX-310 task — a plain \b regex would extract the inner
# task ID from the hyphen boundary.
_DECISION_ID_TOKEN_RE = re.compile(r"(?<![-A-Z])([A-Z]+)-(\d+)\b")

def _decision_related_column_index(lines):
    """FIX-312: locate the 关联任务 data-cell index from the decision-log header.

    FIX-342 (review-FIX-341-312-CODE-R0 P3-2): the scan is limited to the
    HEADER AREA — table rows before the FIRST separator row. A narrative
    table further down the body can no longer shadow the real header (the
    previous whole-file scan let any later table carrying an exact 「关联任务」
    cell hijack the column index). Returns the 0-based data-cell index, or
    None when the header area declares no such cell or the file has no
    separator row (the caller then falls back to the canonical second-to-last
    cell — 关联任务 | 后续动作 are the last two columns of the 11-column
    decision schema).
    """
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if re.match(r"^\|[\s\-:|\t]+\|$", stripped):
            # First separator row: the header area ends here — a later
            # table (body narrative / appendix) is never consulted.
            break
        parts = [p.strip() for p in stripped.split("|")]
        data_cells = parts[1:-1] if len(parts) >= 2 else parts
        for idx, cell in enumerate(data_cells):
            if cell == _DECISION_RELATED_COLUMN_HEADER:
                return idx
    return None

def _decision_archive_version(line, related_idx, task_versions):
    """FIX-312: decide a decision row's archival attribution from its GOVERNING refs.

    Governing refs = the task-family IDs in the 关联任务 (related tasks)
    column ONLY. Prose mentions in 背景/决策内容 are context, never governing
    refs — the whole-line any-hit scan is exactly what mis-attributed DEC-187
    to FEAT-010@v0.77.0 while its governing FIX-310/307/308/309 were still hot
    (R2 F-R2-01 family).

    Migration gate (conservative): the row migrates ONLY when EVERY
    task-family governing ref is archived (present in ``task_versions`` — a
    ref missing from the mapping is an active/unarchived task or unknown,
    either of which keeps the decision hot); the attributed version is the
    NEWEST archived governing version (max semver, not the first whole-line
    hit). Anything unprovable (no related column cell, structurally short
    row, no task-family refs) is retained fail-closed.

    Args:
        line: the raw ``| DEC-… |`` row.
        related_idx: 0-based data-cell index of the 关联任务 column
            (:func:`_decision_related_column_index`), or None for the
            canonical second-to-last-cell fallback (trusted only for
            canonical-length rows — FIX-342 fail-closed).
        task_versions: ``{task_id: version}`` for archived tasks (this run +
            already-archived historical tasks).

    Returns:
        ``(version_or_None, reason, detail)`` — version is the attribution
        when the gate passes, else None. ``reason`` ∈ would_archive /
        retained_active_task_ref / no_task_family_ref / decision_row_too_short.
    """
    parts = [p.strip() for p in line.split("|")]
    data_cells = parts[1:-1] if len(parts) >= 2 else parts
    if related_idx is not None:
        if related_idx >= len(data_cells):
            return None, "decision_row_too_short", ""
        related_cell = data_cells[related_idx]
    else:
        # FIX-342 (review-FIX-341-312-CODE-R0 P2-2): the headerless fallback
        # trusts the second-to-last cell ONLY at the canonical schema length.
        # A shorter row's [-2] cell is NOT the 关联任务 column — fail closed
        # like any other structurally untrusted row.
        if len(data_cells) != _DECISION_SCHEMA_COLUMNS:
            return None, "decision_row_too_short", ""
        related_cell = data_cells[-2]
    refs = []
    for m in _DECISION_ID_TOKEN_RE.finditer(related_cell):
        tid = "{0}-{1}".format(m.group(1), m.group(2))
        if _is_task_family_id(tid) and tid not in refs:
            refs.append(tid)
    if not refs:
        return None, "no_task_family_ref", ""
    unarchived = [t for t in refs if t not in task_versions]
    if unarchived:
        return (None, "retained_active_task_ref",
                "active/unarchived refs: " + ", ".join(unarchived))
    best = max(refs, key=lambda t: _version_to_tuple(task_versions.get(t))
               or (0, 0, 0))
    return task_versions[best], "would_archive", "v{0}".format(
        task_versions[best])

def _decision_narrative_title(parts):
    """FIX-407 (EXC-003 终局票): display title for a narrative decision row.

    The hand-era compact form is 编号/日期/决策人/决策内容/理由 — the first
    content-bearing cell after the id/date prefix (决策内容, falling back to
    the owner cell), truncated for the archive header. The full original row
    is preserved verbatim below the header regardless (FIX-162 P2-1), and a
    non-``DEC-\\d+``-clean id (e.g. ``DEC-194 补记``) simply falls to the
    FIX-384 entry-less archive registration — both index calibers stay
    single-sourced on the strict extractor regex.
    """
    for cell in parts[4:6]:
        if cell:
            return cell[:80]
    return (parts[3] if len(parts) > 3 else "") or "（narrative 行）"

# Closed/done status markers — a risk is migratable ONLY if its status cell
# contains one of these substrings. Keep conservative: an unknown status is
# treated as open and stays in the hot risk-log.
_RISK_CLOSED_MARKERS = (
    "已关闭", "关闭", "closed", "Close",
)
# Active/open status markers — any of these in the status cell forces the row
# to stay in the hot risk-log regardless of version-range membership.
_RISK_OPEN_MARKERS = (
    "打开", "缓解中", "缓解完成", "活跃", "active", "Open", "进行中", "待",
)

def _risk_log_status_column(header_line):
    """FIX-170: find the column index of the risk status cell.

    The risk-log header uses '当前状态' (not bare '状态'), so
    _find_status_column() — which matches the cell exactly == '状态' — misses it
    and returns None. This helper matches any header cell containing '状态'
    (e.g. '当前状态', '状态'), returning the 0-based data-cell index, or None.
    """
    if not header_line or not header_line.strip().startswith("|"):
        return None
    parts = [p.strip() for p in header_line.split("|")]
    data_cells = parts[1:-1] if len(parts) >= 2 else parts
    for idx, cell in enumerate(data_cells):
        if cell == "状态" or "状态" in cell:
            return idx
    return None

def _find_risk_log_header(lines):
    """FIX-170: return the risk-log table header line (the row containing
    '当前状态' or '状态' that precedes the '| RISK-' data rows).

    Scans for the markdown table header row of the risk-log table. Returns the
    header line string, or None if not found. Used by _is_risk_closed() to
    locate the status column dynamically.
    """
    candidate = None
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if re.match(r"^\|[\s\-:|\t]+\|$", stripped):
            # separator row; the header is the line just before it — we'll
            # have captured it as `candidate` on the previous iteration if it
            # contained 状态.
            continue
        if "状态" in stripped and "编号" in stripped:
            candidate = line
            continue
        # First data row | RISK-... : stop; candidate holds the header.
        if stripped.startswith("| RISK-"):
            break
    return candidate

def _is_risk_closed(row, header_line):
    """FIX-170: a risk-log row is migratable only if its status indicates closure.

    The status cell is located dynamically via the risk-log header (the real
    risk-log uses a '当前状态' column; risk_id is in column 1). This is
    COLUMN-AWARE on purpose: a whole-row substring scan would false-positive,
    because the mitigation ('缓解动作') and notes ('备注') cells of OPEN risks
    routinely contain words like '关闭标准', '不关闭本风险', '关闭标准不变'.

    Conservative default: if the status column cannot be located, or the status
    cell is blank/ambiguous, the row is treated as NOT closed (kept hot).
    """
    status_col = _risk_log_status_column(header_line)
    parts = [p.strip() for p in row.split("|")]
    data_parts = parts[1:-1] if len(parts) >= 2 else parts
    if status_col is not None and status_col < len(data_parts):
        status = data_parts[status_col]
    else:
        # No reliable status column → cannot prove closure → keep hot.
        return False
    if not status:
        return False
    # Open markers take precedence (an '已关闭' string containing no open
    # marker still matches closed below; but a cell like '打开' must never
    # migrate even if '关闭' appears elsewhere — it never does in the cell).
    if any(m in status for m in _RISK_OPEN_MARKERS):
        return False
    return any(m in status for m in _RISK_CLOSED_MARKERS)

# FIX-171: task-family ID prefixes — these are the only prefixes that can appear
# as Task IDs in plan-tracker (and therefore as keys in task_versions). The
# evidence-log's 关联 Task cell routinely mixes task-family IDs (e.g. FIX-084,
# REL-013) with CROSS-ENTITY reference IDs (e.g. RISK-036, DEC-072, REQ-082)
# that are descriptive context, not tasks. The old _migrate_evidence subset gate
# required ALL referenced IDs to be in task_versions, which is structurally
# impossible for cross-entity refs → 129 in-range EVD rows were blocked forever
# (AUDIT-126 root cause B). This classification lets the gate consider only
# task-family refs.
#
# Conservative selection rationale: when uncertain whether a prefix is
# task-family, INCLUDE it. A non-task ID that happens to be in this set simply
# won't match anything in task_versions (no false migration). The prefixes that
# must NOT be here — because they are NEVER task IDs and WOULD wrongly gate —
# are listed explicitly in _CROSS_ENTITY_PREFIXES for documentation; the
# task-family set is the positive allow-list and everything else is treated as
# cross-entity by _is_task_family_id.
#
# The set below was derived from the real governance data: prefixes that appear
# as Task IDs in plan-tracker table rows OR in archive/tasks/ files
# (FIX, REL, AUDIT, REQ, SYSGAP, TD, MAINT, FMT, DIAG, DESIGN, VAL, CLEANUP,
# PRINCIPLE, ...). REQ is included even though it also names a requirement
# entity (REQ-082), because REQ-NNN rows can legitimately be tasks too.
_TASK_FAMILY_PREFIXES = frozenset({
    "FIX", "REL", "AUDIT", "REQ", "FMT", "DIAG", "MAINT", "SYSGAP", "TD",
    "DESIGN", "VAL", "CLEANUP", "PRINCIPLE", "TASK", "RESEARCH", "ACCEPT",
    "INIT", "PLAN", "FEAT",
})

# Cross-entity prefixes — these are NEVER task IDs and must never gate evidence
# migration (AUDIT-126 root cause B). Kept for documentation / clarity; the
# allow-list above is authoritative and everything not in it is cross-entity.
_CROSS_ENTITY_PREFIXES = frozenset({
    "RISK", "DEC", "REVIEW", "EVD", "TIER", "CONSTRAINT", "TOOL", "ADR",
})

# FEAT-074 (DEC-278 unit one): prefixes typed as registered non-task entities
# ("other entity: DEC/RISK/DOC etc." per the ruling). DOC follows the DEC-278
# five-state enumeration even though task_priority.py routes DOC governance ids
# to plan-tracker.md — for EVIDENCE migration gating DOC stays non-gating
# (pre-fix behavior), and the divergence is recorded in the FEAT-074 report.
_OTHER_ENTITY_REF_PREFIXES = frozenset(_CROSS_ENTITY_PREFIXES | {"DOC"})

# FEAT-074 (DEC-278 unit one item 3): per-ID verified FX→task mappings. Every
# entry was verified INDIVIDUALLY against the archived task-version mapping
# (.governance/archive/tasks — each id resolves to the version noted) and git
# history (--all -S pickaxe first-mention commits); the full evidence table is
# archived in docs/architecture/feat-074-classification-diff-20260928.md.
# Wildcard admission of the "FX" prefix is explicitly FORBIDDEN (DEC-278 §3.1
# unit one: "FX 逐 ID 核验映射，不许通配替换"); any UNLISTED FX-N (or other
# unverified task-shaped prefix) stays unresolved and classifies "ambiguous"
# (fail-closed, with an explainable reason).
_VERIFIED_TASK_ID_ALIASES = {
    # FX id -> resolved task id (identity: each verified FX id IS the archived
    # task; resolution then flows through the normal task_versions mapping).
    "FX-130": "FX-130",  # v0.64.0 — entry resolver chain (AUDIT-129/DEC-096; first mention 77df046)
    "FX-131": "FX-131",  # v0.64.0 — entry resolver chain (AUDIT-129/DEC-096; first mention 77df046)
    "FX-175": "FX-175",  # v0.63.0 — tag-backfill batch (first mention 20bdc53)
    "FX-177": "FX-177",  # v0.63.1 — docs/release backfill (DOC-001; first mention 7792b4e)
    "FX-179": "FX-179",  # v0.63.2 — docs/release backfill (DOC-001; first mention 7792b4e)
    "FX-181": "FX-181",  # v0.63.3 — docs/release backfill (DOC-001; first mention 7792b4e)
    "FX-183": "FX-183",  # v0.63.4 — docs/release backfill (DOC-001; first mention 7792b4e)
    "FX-188": "FX-188",  # v0.65.0 — loop-engineering Slice 1: registry layer + loader (999f69d)
    "FX-189": "FX-189",  # v0.65.0 — loop-engineering Slice 2: loop_engine core (999f69d)
    "FX-190": "FX-190",  # v0.65.0 — loop-engineering Slice 3: flow_unit_derive (999f69d)
    "FX-191": "FX-191",  # v0.65.0 — loop-engineering Slice 4: loop_migration apply/rollback (999f69d)
    "FX-192": "FX-192",  # v0.65.0 — loop-engineering Slice 5: loop_health Check (999f69d)
    "FX-193": "FX-193",  # v0.65.0 — loop-engineering Slice 6: rollup view (999f69d)
    "FX-194": "FX-194",  # v0.65.0 — loop-engineering Slice 7: Gate re-labeling (999f69d)
}

# FEAT-074 (DEC-278 unit one item 6): markdown table rows may carry ESCAPED
# pipes ("\|") inside cells — rendered as literal pipes, never column
# separators. Counting raw "|" characters misjudges such rows as anomalous
# layout (the FEAT-047 row: 9 raw pipes = 8 real columns) and a raw split
# shifts every downstream column. Split on UNESCAPED pipes only.
_UNESCAPED_PIPE_SPLIT_RE = re.compile(r"(?<!\\)\|")

def _split_table_row_escaped_aware(line):
    """FEAT-074: split a markdown table row on UNESCAPED pipes only.

    Returns the same shape as line.split("|") — leading/trailing empty strings
    around the outer pipes — except escaped "\\|" sequences stay inside their
    cell (content-preserving: the row text is never rewritten).
    """
    return _UNESCAPED_PIPE_SPLIT_RE.split(line)

def _count_unescaped_pipes(line):
    """FEAT-074: the number of REAL column separators in a table row."""
    return len(_UNESCAPED_PIPE_SPLIT_RE.findall(line))

def _is_task_family_id(task_id):
    """FIX-171 (AUDIT-126): return True if task_id's prefix is a task-family prefix.

    A task-family ID is one that can appear as a Task ID in plan-tracker and
    therefore can resolve to a version in task_versions (FIX-/REL-/AUDIT-/FEAT-/
    REQ-/SYSGAP-/TD-/MAINT-/FMT-/DIAG-/...). Cross-entity refs (RISK-/DEC-/
    REVIEW-/EVD-/TIER-/CONSTRAINT-/TOOL-/ADR-) are descriptive context in an
    evidence row's 关联 Task cell, never tasks, and must NOT gate evidence
    migration.

    FEAT-074 (DEC-278 unit one item 2): FEAT- is a task family (see
    _TASK_FAMILY_PREFIXES). REQ- stays task-family too — a REQ reference is
    re-typed against the requirement registry at CLASSIFICATION time
    (_requirement_registry_ids + the five-state logic in
    _classify_evidence_rows), not by this prefix predicate: a registry REQ is
    a requirement entity (non-gating, DEC-278 Q2=c) while a task-side REQ is
    judged by the task lifecycle. Alias-verified historical ids (FX-..., see
    _VERIFIED_TASK_ID_ALIASES) are admitted per-ID by the classifier even
    though their prefix is not in this set.

    Args:
        task_id: an ID string of the form PREFIX-NNN (caller pre-validates the
                 shape; this function only inspects the prefix).

    Returns:
        True if the prefix is in _TASK_FAMILY_PREFIXES, False otherwise.
    """
    prefix = task_id.split("-", 1)[0]
    return prefix in _TASK_FAMILY_PREFIXES

def _requirement_registry_ids(content):
    """FEAT-074 (DEC-278 Q2=c): REQ-N ids registered in the requirement registry.

    plan-tracker keeps a requirement registry (需求跟踪矩阵) whose header's
    first data cell starts with 需求ID and whose rows put the REQ id in the
    FIRST data column. Those REQ entities are REQUIREMENTS, not tasks: they
    never have a task version and must not be required to resolve into
    task_versions. Scan semantics mirror the priority-table parsers — blank
    lines / prose inside the table do not terminate the scan; only headings
    do; rows keep their first-data-cell REQ-\\d+ id.

    Returns a set of REQ ids (empty when the registry is absent).
    """
    ids = set()
    in_registry = False
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("###") or stripped.startswith("##"):
            in_registry = False
            continue
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in _split_table_row_escaped_aware(stripped)]
        data_cells = cells[1:-1] if len(cells) >= 2 else cells
        if data_cells and data_cells[0].startswith("需求ID"):
            in_registry = True
            continue
        if not in_registry or not data_cells:
            continue
        first = re.sub(r"[`*]", "", data_cells[0]).strip()
        if re.match(r"^REQ-\d+$", first):
            ids.add(first)
    return ids

# FIX-301: evidence row IDs come in two REAL shapes — plain sequential
# (EVD-969) and compound task-keyed (EVD-FIX-247, "the evidence row of
# FIX-247", in hot use since 2026-08). The old plain `EVD-\d+` shape check
# rejected every compound row as unknown, making 52 real rows invisible to
# migration AND to the archive index. Shared by _migrate_evidence (gate) and
# _extract_evidence_from_archive_file (index extraction) so the migration
# side and the index side can never drift; verify_archive_integrity's Check 3
# index-row counter accepts the same multi-segment prefix shape.
_EVD_ID_SHAPE_RE = re.compile(r"^EVD-(?:[A-Z]+-)?\d+$")

# FIX-385: the evidence archive table header, single-sourced so the one-shot
# path (_migrate_evidence) and the resumable big-table commit compose
# byte-identical archive files (index compatibility by construction).
_EVIDENCE_ARCHIVE_TABLE_HEADER = (
    "| 证据ID | 关联Task | 摘要 | 日期 | 类型 | 产出 | 负责人 | 审查人 | 审查结果 | 备注 |",
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
)

# FEAT-076 (0.93.0): archive table headers for the three non-EVD row
# families. Migrated rows are preserved VERBATIM (byte-identical to their
# hot-file form, same fidelity discipline as EVD) — these headers document
# the observed hot-file schemas at migration time and are descriptive, not
# load-bearing: extraction/rollback key on the row-id prefix
# (_ROW_FAMILY_LINE_PREFIXES), never on the header.
_ROW_FAMILY_ARCHIVE_TABLE_HEADERS = {
    "REVIEW": (
        "| 审查ID | 关联任务 | 阶段 | 审查类型 | 结论纪要 | 事实依据 | 审查人 | 日期 | Gate | 状态 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ),
    "TRIAGE": (
        "| Triage ID | 关联任务 | 阶段 | 摘要 | 事实依据 | 产出 | 负责人 | 日期 | Gate | 状态 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ),
    "RECO": (
        "| 建议ID | 关联任务 | 阶段 | 摘要 | 事实依据 | 产出 | 负责人 | 日期 | Gate | 状态 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ),
}

def _row_family_archive_table_header(row_family):
    """FEAT-076: the archive file table header for one family (EVD keeps
    the FIX-385 single-sourced header; others use the documented family
    schema above)."""
    if row_family == "EVD":
        return _EVIDENCE_ARCHIVE_TABLE_HEADER
    return _ROW_FAMILY_ARCHIVE_TABLE_HEADERS[row_family]

def _make_ref_verdict(task_versions, context):
    """FEAT-075 (DEC-278 unit two): the shared five-state ref typer + task
    lifecycle gate — extracted VERBATIM from ``_classify_evidence_rows``'s
    closure (unit one's semantics, single source) so the four-family
    read-only scanners REUSE it instead of growing a parallel
    implementation (DEC-278 §3.1 单元二: 共用分类语义).

    Returns the ``_ref_verdict(tid) -> (entity_state, verdict, payload)``
    function; see ``_classify_evidence_rows`` docstring for the state and
    verdict vocabulary.
    """
    hot_tasks = context["hot_tasks"]
    hot_anomalies = context["hot_anomalies"]
    requirement_ids = context["requirement_ids"]

    def _ref_verdict(tid):
        """Type ONE referenced id and judge it against the task conditions.

        Returns (entity_state, verdict, payload):
          entity_state — one of the five _EVIDENCE_REF_ENTITY_TYPES states.
          verdict      — "pass" (task resolved; payload = version),
                         "nongate" (descriptive context; payload = None),
                         "fail" (payload = failure substate:
                         active / missing / layout_anomaly /
                         version_unparseable / ambiguous_*).
        """
        alias_target = _VERIFIED_TASK_ID_ALIASES.get(tid)
        gate_id = None
        prefix = tid.split("-", 1)[0]
        if prefix == "REQ":
            # FEAT-074 item 4 (Q2=c): the entity-registration source decides
            # a REQ reference's semantics BEFORE the task-family allow-list
            # (REQ- is in _TASK_FAMILY_PREFIXES for genuine task-side REQs).
            task_side = tid in task_versions or tid in hot_tasks
            if tid in requirement_ids and task_side:
                return "ambiguous", "fail", "ambiguous_dual_registration"
            if tid in requirement_ids:
                return "requirement", "nongate", None
            if task_side:
                gate_id = tid  # a genuine task-side REQ id
            else:
                return "missing", "fail", "missing"
        elif alias_target is not None:
            # FEAT-074 item 3: per-ID verified alias (FX→archived task);
            # wildcard family admission is forbidden, unlisted ids fall
            # through to the unverified-family branch below.
            gate_id = alias_target
        elif _is_task_family_id(tid):
            gate_id = tid
        else:
            if prefix in _OTHER_ENTITY_REF_PREFIXES:
                return "other_entity", "nongate", None
            # Task-shaped but not a known family and not per-ID verified
            # (e.g. an unlisted FX-N): identity cannot be confirmed —
            # DEC-278: keep unresolved, never wildcard-resolve.
            return "ambiguous", "fail", "ambiguous_unverified_family"
        # task-side gate on gate_id (alias-resolved where applicable)
        if gate_id in task_versions:
            return "task", "pass", task_versions[gate_id]
        if gate_id in hot_anomalies:
            # Locatable hot row whose layout is anomalous — columns cannot
            # be trusted, so lifecycle closure can never be proven from it.
            return "task", "fail", "layout_anomaly"
        if gate_id in hot_tasks:
            info = hot_tasks[gate_id]
            if not _task_status_is_archivable(info["status"]):
                return "task", "fail", "active"
            if not _version_to_tuple(info["version"]):
                # Terminal but non-semver target (未规划版本 / G9/G11):
                # owning release cycle cannot be proven closed.
                return "task", "fail", "version_unparseable"
            # Terminal + parseable but invisible to the sanctioned completed-
            # hot mapping — the version cannot be pinned through the mapping
            # this gate trusts; fail closed rather than re-derive it.
            return "task", "fail", "version_unparseable"
        return "missing", "fail", "missing"

    return _ref_verdict

#: Row-value prefix each family's hot rows carry (archive extraction,
#: rollback restoration, and the unified read layer all key on this).
_ROW_FAMILY_LINE_PREFIXES = {
    "EVD": "| EVD-",
    "REVIEW": "| REVIEW-",
    "TRIAGE": "| TRIAGE-",
    "RECO": "| RECO-",
}

# Per-family id shapes (2026-09-28 live-data verification: 633 REVIEW rows —
# 404 plain REVIEW-{TASK}-R{n}, 42 with a scope token (CODE/RELEASE/...),
# multi-segment scopes (DESIGN-IMPL), legacy no-round ids (REVIEW-FIX-170),
# and 4 historical malformed shapes (REVIEW-FIX-155a,
# REVIEW-0.45-0.46-FINAL …) counted explicitly as unknown; 199 TRIAGE /
# 159 RECO rows all match TRIAGE-{TASK} / RECO-{TASK}). Group(1) is the
# family's EMBEDDED governing task id.
_ROW_FAMILY_ID_RES = {
    "REVIEW": re.compile(r"^REVIEW-([A-Z]+-\d+)(?:-[A-Z0-9]+)*(?:-R\d+)?$"),
    "TRIAGE": re.compile(r"^TRIAGE-([A-Z]+-\d+)$"),
    "RECO": re.compile(r"^RECO-([A-Z]+-\d+)$"),
}

def _split_ref_ids(cell):
    """FEAT-075: comma-separated governance-id refs from one table cell
    (same token grammar as the EVD 关联Task column: PREFIX-N)."""
    refs = set()
    for token in (cell or "").split(","):
        token = token.strip()
        if token and re.match(r"[A-Z]+-\d+", token):
            refs.add(token)
    return refs

def _parse_family_row(family, line):
    """FEAT-075: parse ONE non-EVD family row against its OWN schema.

    Returns (row_id, governing_refs, ref_column_value) or None when the row
    does not satisfy the family schema (malformed → the scanner counts it
    as unknown_row_id_shape — explicitly reported, never silently skipped).
    Governing refs = the id-EMBEDDED task ∪ the 关联任务 column (fail-closed
    union: a divergence between the two can only retain the row, never
    release it).
    """
    parts = [p.strip() for p in line.split("|")]
    row_id = parts[1] if len(parts) > 1 else ""
    match = _ROW_FAMILY_ID_RES[family].match(row_id) if row_id else None
    if match is None or len(parts) < 3:
        return None
    embedded_task = match.group(1)
    ref_column = parts[2]
    refs = {embedded_task} | _split_ref_ids(ref_column)
    return row_id, refs, ref_column


def _parse_version_roadmap(content):
    """Parse version roadmap table from plan-tracker content.

    Three strategies, tried in order:
    1. Find '### 版本路线图' section and extract version/status from table
    2. Fallback: search for any heading containing '版本路线图'
    3. Fallback: extract versions from section titles (all treated as '已发布')

    Returns list of (version, status) tuples.
    """
    lines = content.split("\n")

    # Strategy 1: Find "### 版本路线图" section
    in_roadmap = False
    header_seen = False
    table_started = False
    versions = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        if stripped == "### 版本路线图":
            in_roadmap = True
            header_seen = False
            table_started = False
            versions = []
            continue

        if in_roadmap:
            # End on next heading (### or ##)
            if (stripped.startswith("### ") or stripped.startswith("## ")) and "版本路线图" not in stripped:
                if table_started:
                    break
                continue

            # Detect table header row
            if stripped.startswith("|") and "版本" in stripped and "状态" in stripped:
                header_seen = True
                continue

            # Detect separator row
            if header_seen and stripped.startswith("|") and "---" in stripped:
                table_started = True
                continue

            # Parse data rows
            if table_started and stripped.startswith("|"):
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    version = parts[1].strip("*")
                    status = parts[2].strip("*")
                    if re.match(r"\d+\.\d+\.\d+", version):
                        versions.append((version, status))

    if versions:
        return versions

    # Strategy 2: Search for any heading containing "版本路线图"
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") and "版本路线图" in stripped:
            in_roadmap = True
            header_seen = False
            table_started = False
            versions = []
            for j in range(i + 1, len(lines)):
                subline = lines[j].strip()
                if subline.startswith("#") and "版本路线图" not in subline:
                    break
                if "版本" in subline and "状态" in subline and subline.startswith("|"):
                    header_seen = True
                    continue
                if header_seen and "---" in subline and subline.startswith("|"):
                    table_started = True
                    continue
                if table_started and subline.startswith("|"):
                    parts = [p.strip() for p in lines[j].split("|")]
                    if len(parts) >= 3:
                        version = parts[1].strip("*")
                        status = parts[2].strip("*")
                        if re.match(r"\d+\.\d+\.\d+", version):
                            versions.append((version, status))
            if versions:
                return versions

    # Strategy 3: Extract from version section titles
    for line in lines:
        v, _ = _parse_version_from_title(line)
        if v and not any(pair[0] == v for pair in versions):
            versions.append((v, "已发布"))

    return versions

def _parse_version_roadmap_entries(content):
    """Parse roadmap rows into dicts with version, status, and optional date."""
    entries = []
    lines = content.split("\n")
    in_roadmap = False
    header_seen = False
    table_started = False

    for line in lines:
        stripped = line.strip()
        if stripped == "### 版本路线图":
            in_roadmap = True
            header_seen = False
            table_started = False
            continue

        if in_roadmap:
            if (stripped.startswith("### ") or stripped.startswith("## ")) and "版本路线图" not in stripped:
                if table_started:
                    break
                continue
            if stripped.startswith("|") and "版本" in stripped and "状态" in stripped:
                header_seen = True
                continue
            if header_seen and stripped.startswith("|") and "---" in stripped:
                table_started = True
                continue
            if table_started and stripped.startswith("|"):
                parts = [p.strip().strip("*") for p in line.split("|")]
                if len(parts) >= 4 and re.match(r"\d+\.\d+\.\d+", parts[1]):
                    entries.append({
                        "version": parts[1],
                        "status": parts[2],
                        "date": parts[3],
                    })

    if entries:
        return entries

    return [
        {"version": version, "status": status, "date": ""}
        for version, status in _parse_version_roadmap(content)
    ]

def _parse_iso_date(value):
    """Parse YYYY-MM-DD from a roadmap cell; return None when absent."""
    if not value:
        return None
    m = re.search(r"\d{4}-\d{2}-\d{2}", value)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(0), "%Y-%m-%d").date()
    except ValueError:
        return None




# ── FIX-417: migrate_by_version pure stage helpers ──────────────────────

def collect_archivable_task_rows(content, sections, version_start,
                                 version_end, already_archived_tasks):
    """FIX-417 (moved verbatim from migrate_by_version): dual-scan the
    version sections AND the priority table (### 优先级一览) for archivable
    task rows in the version range.

    FIX-158 root cause: the priority table holds ALL tasks in the real
    plan-tracker, grouped by the row's 目标版本 column — the section-only
    scan was the AUDIT-125 "无可归档数据" blind spot. FIX-301: the scan is
    group-break tolerant and pipe-anomaly rows are reported through
    anomalies for the unknown-structure list instead of being silently
    invisible.

    Returns (archived_task_lines, archive_body_lines, tasks_remaining,
    notes) — archived_task_lines entries are (line_index, original_line,
    task_id, version); notes entries are {"id","reason","detail"} rows for
    the FIX-301 auditable explanation.
    """
    archived_task_lines = []  # (line_index, original_line, task_id, version)
    archived_tasks = set()
    archive_body_lines = []
    notes = []
    tasks_remaining = 0

    def _note(task_id, reason, detail=""):
        notes.append({"id": task_id, "reason": reason, "detail": detail[:60]})

    for section in sections:
        # FIX-158: locate 状态 column from this section's header row (dynamic,
        # not hardcoded). Falls back to last column if header not captured.
        sec_status_col = _find_status_column(section.get("header_line") or "")
        if _version_in_range(section["version"], version_start, version_end):
            # Check each task in this section
            for line_idx, line, task_id in section["task_lines"]:
                status = _parse_task_status(line, status_col=sec_status_col)
                if _task_status_is_archivable(status):
                    if task_id in already_archived_tasks:
                        _note(task_id, "already_archived")
                        continue
                    archived_task_lines.append((line_idx, line, task_id, section["version"]))
                    archived_tasks.add(task_id)
                    archive_body_lines.append((section["version"], line))
                    _note(task_id, "would_archive", f"v{section['version']}")
                else:
                    tasks_remaining += 1
                    _note(task_id, "status_not_archivable", status)
        else:
            # Tasks in non-matching sections remain in hot file
            for _line_idx, _line, task_id in section["task_lines"]:
                tasks_remaining += 1
                _note(task_id, "out_of_range_version", f"v{section['version']}")

    priority_anomalies = []
    priority_tasks = _parse_priority_table_tasks(
        content, anomalies_out=priority_anomalies
    )
    for task_id, _line_idx, pipe_count in priority_anomalies:
        _note(task_id, "pipe_layout_anomaly", f"pipe count {pipe_count} != 8")
    for line_idx, line, task_id, target_version, status in priority_tasks:
        if task_id in already_archived_tasks or task_id in archived_tasks:
            _note(task_id, "already_archived")
            continue
        # Only consider tasks whose target version is in range (matching the
        # version-section behavior). Out-of-range tasks are left alone and not
        # counted as remaining (they belong to other version ranges).
        if not target_version:
            _note(task_id, "no_target_version", "no semver target version")
            continue
        if not _version_in_range(target_version, version_start, version_end):
            _note(task_id, "out_of_range_version", f"v{target_version}")
            continue
        if not _task_status_is_archivable(status):
            tasks_remaining += 1
            _note(task_id, "status_not_archivable", status)
            continue
        archived_task_lines.append((line_idx, line, task_id, target_version))
        archived_tasks.add(task_id)
        archive_body_lines.append((target_version, line))
        _note(task_id, "would_archive", f"v{target_version}")

    return archived_task_lines, archive_body_lines, tasks_remaining, notes


def compose_task_archive_lines(sections, archive_body_lines):
    """FIX-417 (moved verbatim from migrate_by_version): group archived
    tasks by version and compose the archive file body lines.

    FIX-172 (DATA-LOSS bug): the body write MUST be UNCONDITIONAL — every
    task in `archive_body_lines` has to land in the archive file.
    `archive_body_lines` is populated from TWO sources (see
    collect_archivable_task_rows): (1) version-section tasks, whose version
    matches a section header, and (2) priority-table tasks found via
    `_parse_priority_table_tasks`, whose target_version (e.g. '0.61.0')
    does NOT match any version-section header in the real plan-tracker
    (which only has a `### 1.0.0 依赖链` section). The previous
    implementation gated the whole block on `if section:` — so for every
    priority-table task `section` was None, the task lines were NEVER
    appended to `archive_lines`, yet the deletion step removed them from
    plan-tracker unconditionally. Result: an archive file with only a
    header and zero task rows = DATA LOSS (production incident on
    `archive.py migrate --auto` -> v0.1.0~v0.61.2.md, 346 bytes, 10 task
    rows vanished). This was a FIX-158 regression: FIX-158 added the
    priority-table scan but did not update this write path. The fix makes
    the write unconditional; `section` only decides whether to emit the
    original section title or a synthesized one, never whether to persist
    data.
    """
    tasks_by_version = {}
    for version, line in archive_body_lines:
        tasks_by_version.setdefault(version, []).append(line)

    # Sort key: parseable semver tuples sort ascending; non-parseable
    # versions (—, 未规划版本, unknown, empty) sort LAST under a single
    # catch-all bucket so they are never dropped. `_version_to_tuple`
    # returns None for those; we map None to a sentinel that compares
    # greater than any real (major, minor, patch) so Python's sort never
    # tries to order None against tuples (TypeError).
    _ARCHIVE_SORT_SENTINEL = (float("inf"), 0, 0)

    def _archive_sort_key(version):
        vt = _version_to_tuple(version)
        return vt if vt is not None else _ARCHIVE_SORT_SENTINEL

    archive_lines = []
    for version in sorted(tasks_by_version.keys(), key=_archive_sort_key):
        # Find the original section title (version-section tasks only).
        section = next((s for s in sections if s["version"] == version), None)
        if section:
            title = section["title"]
        elif _version_to_tuple(version) is not None:
            # Priority-table task whose version has no matching section
            # header. Emit a synthesized, human-readable title so the
            # archive stays grouped without dropping the rows (the
            # data-loss root cause).
            title = f"### v{version}（优先级表归档）"
        else:
            # Non-parseable version (—, 未规划版本, unknown, empty). Group
            # all of them under one catch-all bucket at the end so real
            # archived tasks are never silently dropped.
            title = "### 未版本化归档任务"
        archive_lines.append("")
        archive_lines.append(title)
        # Use a standard table header
        archive_lines.append("| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |")
        archive_lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for line in tasks_by_version[version]:
            archive_lines.append(line)
        archive_lines.append("")
    return archive_lines


def rewrite_hot_tracker_lines(lines, archived_task_lines, sections,
                              version_start, version_end):
    """FIX-417 (moved verbatim from migrate_by_version): remove the archived
    task lines from the hot plan-tracker text and mark in-range version
    section headers as [已归档].

    Sample-table section rows are interleaved with non-task text — deleting
    them would destroy table structure, so they are excluded from removal.
    """
    sample_table_line_indices = set()
    for section in sections:
        if section.get("sample_table", False):
            for line_idx, _, _ in section["task_lines"]:
                sample_table_line_indices.add(line_idx)

    # Remove archived task lines from plan-tracker content
    lines_to_remove = {
        idx for idx, _, _, _ in archived_task_lines
        if idx not in sample_table_line_indices
    }
    new_lines = []
    for i, line in enumerate(lines):
        if i in lines_to_remove:
            continue
        new_lines.append(line)

    # Update version section headers to mark as archived
    final_lines = []
    for i, line in enumerate(new_lines):
        v, desc = _parse_version_from_title(line)
        if v and _version_in_range(v, version_start, version_end):
            # Add archived marker to version title
            if "[已归档]" not in line:
                line = line.rstrip() + " [已归档]"
        final_lines.append(line)
    return final_lines
