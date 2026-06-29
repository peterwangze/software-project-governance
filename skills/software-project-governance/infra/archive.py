#!/usr/bin/env python3
"""
Governance Data Archive Script — SYSGAP-030

Implements version-based archiving of governance data (plan-tracker tasks,
evidence-log entries, etc.) with a light-weight Markdown index.

Core functions:
  - migrate_by_version: archive tasks+evidence for a version range
  - build_index: scan archive files, generate archive/index.md
  - verify_archive_integrity: check index-archive consistency
  - rollback_last_migration: undo most recent migration

Design: ADR-006 (docs/architecture/ADR-006-governance-data-scalability.md)
"""

import re
import shutil
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

# ROOT is overridable for testing; paths are lazy to allow patching
ROOT = Path(__file__).resolve().parents[3]

FIRST_MIGRATION_PLAN_SIZE_THRESHOLD = 80 * 1024
TASK_INCREMENTAL_THRESHOLD = 20
FALLBACK_ARCHIVE_DAYS = 90


def _gov_dir():
    return ROOT / ".governance"


def _archive_dir():
    return _gov_dir() / "archive"


def _index_path():
    return _archive_dir() / "index.md"


def _plan_tracker():
    return _gov_dir() / "plan-tracker.md"


def _evidence_log():
    return _gov_dir() / "evidence-log.md"


def _decision_log():
    return _gov_dir() / "decision-log.md"


def _risk_log():
    return _gov_dir() / "risk-log.md"


# Path getters are used throughout; module-level references updated below.
# Keep convenience aliases for backward compat (computed lazily via property-like
# accessors — but we replace direct constants with function calls below.)


# ── Version Parsing Utilities ──────────────────────────────────────

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
    """Convert '0.11.0' to (0, 11, 0) for comparison."""
    parts = version_str.split(".")
    return tuple(int(p) for p in parts)


def _version_in_range(version_str, start, end):
    """Check if version_str is in [start, end] inclusive."""
    vt = _version_to_tuple(version_str)
    return _version_to_tuple(start) <= vt <= _version_to_tuple(end)


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


def _task_status_is_archivable(status):
    """FIX-158: determine whether a task status means the task is completed/archivable.

    Real plan-tracker uses many ✅-variants beyond strict "已完成":
    已发布, 保守闭环, 完成候选, 发布候选完成, 已交付, 调查完成, 诊断完成,
    设计完成, 实现完成, 发布完成, 已撤回/失效, 调研归档, 审视归档, etc.
    All of these indicate the task is closed and can be archived.
    Open states (进行中, 待启动, 停滞, 阻塞, 待) must NOT be archived.
    """
    if not status:
        return False
    # Open/pending markers — never archive
    open_markers = ("进行中", "待启动", "停滞", "阻塞", "待决", "待定", "未完成", "TO_BE")
    if any(m in status for m in open_markers):
        return False
    # Closed/delivered markers — archivable
    closed_markers = (
        "✅", "已完成", "已交付", "已发布", "保守闭环", "完成候选",
        "发布候选完成", "调查完成", "诊断完成", "设计完成", "实现完成",
        "发布完成", "已撤回", "失效", "调研归档", "审视归档", "归档",
    )
    return any(m in status for m in closed_markers)


def _parse_priority_table_tasks(content):
    """FIX-158: parse the '### 优先级一览' / '### 最近完成' priority tables.

    Real plan-tracker stores ALL tasks in non-version sections like
    '### 优先级一览' with a 7-column format:
        | 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
        | **P0** | FIX-084 | ... | ... | 0.38.0 | ... | ✅ 已完成 |
    ID is in column 2 (index 1), target version in column 5 (index 4),
    status in the last column. This format was invisible to the original
    archive engine (which required ID in column 1 and version section headers).

    Returns list of (line_index, original_line, task_id, target_version, status).
    """
    lines = content.split("\n")
    tasks = []
    # Scan for priority-table-like sections: the real plan-tracker 7-col format
    # '| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |' where 优先级
    # is the FIRST cell and ID is the SECOND cell. We match this specific layout
    # (not the legacy 10-col '| 任务ID | 描述 | 优先级 | ... |' where 优先级 is
    # in the middle) to avoid double-counting version-section tasks.
    in_priority_table = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Detect priority table header: first data cell is 优先级, second is ID
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.split("|")]
            data_cells = cells[1:-1] if len(cells) >= 2 else cells
            if (len(data_cells) >= 2
                    and data_cells[0] == "优先级"
                    and data_cells[1] == "ID"):
                in_priority_table = True
                continue
        # Reset on section heading or non-table line
        if stripped.startswith("###") or stripped.startswith("##"):
            in_priority_table = False
            continue
        if not in_priority_table:
            continue
        # Skip separator row
        if re.match(r"^\|[\s\-:|\t]+\|$", stripped):
            continue
        if not stripped.startswith("|"):
            in_priority_table = False
            continue
        parts = [p.strip() for p in line.split("|")]
        data_parts = parts[1:-1] if len(parts) >= 2 else parts
        # Need at least: priority, ID, ... , status (7 cols typical)
        if len(data_parts) < 3:
            continue
        # ID is in column 2 (data_parts[1]); strip markdown bold
        raw_id = data_parts[1]
        task_id = re.sub(r"[`*]", "", raw_id).strip()
        if not re.match(r"^[A-Z]+-\d+$", task_id):
            continue
        # Target version in column 5 (data_parts[4]) if present
        target_version = ""
        if len(data_parts) >= 5:
            target_version = re.sub(r"[`*]", "", data_parts[4]).strip()
        # Status is last data column
        status = data_parts[-1]
        tasks.append((i, line, task_id, target_version, status))
    return tasks




# ── Archive File Management ────────────────────────────────────────

def _ensure_archive_dirs():
    """Create archive directory structure if it doesn't exist."""
    for d in [_archive_dir(),
              _archive_dir() / "tasks",
              _archive_dir() / "evidence",
              _archive_dir() / "decisions",
              _archive_dir() / "risks"]:
        d.mkdir(parents=True, exist_ok=True)


def _get_existing_archive_files(subdir):
    """Get sorted list of existing archive .md files (excluding .gitkeep)."""
    dir_path = _archive_dir() / subdir
    if not dir_path.exists():
        return []
    files = sorted([f for f in dir_path.glob("*.md") if f.name != ".gitkeep"],
                   key=lambda f: f.name)
    return files


def _make_archive_filename(version_start, version_end, category="tasks"):
    """Generate archive file name: v{start}~v{end}.md"""
    return f"v{version_start}~v{version_end}.md"


def _make_incremental_archive_filename(version_start, version_end, category="tasks"):
    """Generate an independent archive filename for a repeated range.

    Continuous archive must not append to an older archive file because rollback
    operates at file granularity.  A repeated range therefore gets its own
    increment file that can be safely unlinked without deleting history.
    """
    base_name = _make_archive_filename(version_start, version_end, category)
    archive_subdir = _archive_dir() / category
    base_path = archive_subdir / base_name
    if not base_path.exists():
        return base_name

    today = date.today().isoformat().replace("-", "")
    index = 1
    while True:
        candidate = f"v{version_start}~v{version_end}-incremental-{today}-{index}.md"
        if not (archive_subdir / candidate).exists():
            return candidate
        index += 1


def _parse_archive_version_range(filename):
    """Parse archive filename into (version_start, version_end).

    Supports both base archive files (vX~vY.md) and independent incremental
    archive files (vX~vY-incremental-YYYYMMDD-N.md).
    """
    match = re.match(
        r"^v(\d+\.\d+\.\d+)~v(\d+\.\d+\.\d+)"
        r"(?:-incremental-\d{8}-\d+)?\.md$",
        filename,
    )
    if not match:
        return None
    return match.group(1), match.group(2)


def _version_still_covered_by_task_archive(version_str, excluding_file):
    """Return True if another task archive still covers version_str."""
    tasks_dir = _archive_dir() / "tasks"
    if not tasks_dir.exists():
        return False

    for archive_path in tasks_dir.glob("*.md"):
        if archive_path.name == ".gitkeep" or archive_path == excluding_file:
            continue
        parsed_range = _parse_archive_version_range(archive_path.name)
        if not parsed_range:
            continue
        version_start, version_end = parsed_range
        if _version_in_range(version_str, version_start, version_end):
            return True
    return False


def _write_archive_file(filepath, header, body_lines):
    """Write an archive file with standardized header."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n")
        f.write("\n".join(body_lines))
        f.write("\n")


def _build_archive_header(version_start, version_end, category, entry_count,
                          prev_file=None, next_file=None):
    """Build standardized archive file header.

    category: 'tasks', 'evidence', 'decisions', 'risks'
    """
    category_labels = {
        "tasks": ("归档 Task 表", "plan-tracker.md 中"),
        "evidence": ("归档 Evidence 记录", "evidence-log.md 中"),
        "decisions": ("归档 Decision 记录", "decision-log.md 中"),
        "risks": ("归档 Risk 记录", "risk-log.md 中"),
    }
    label, source = category_labels.get(category, (f"归档 {category} 记录", ""))

    lines = [
        f"# {label} — v{version_start} ~ v{version_end}",
        f"- **归档日期**: {date.today().isoformat()}",
        f"- **归档范围**: {source} {version_start}~{version_end} 版本的所有 {category}",
        f"- **条目数**: {entry_count}",
    ]
    if prev_file:
        lines.append(f"- **上一个归档文件**: archive/{category}/{prev_file}")
    else:
        lines.append(f"- **上一个归档文件**: 无")
    if next_file:
        lines.append(f"- **下一个归档文件**: archive/{category}/{next_file}")
    else:
        lines.append(f"- **下一个归档文件**: 无")

    lines.append("")
    lines.append("> 查询方式：通过 `.governance/archive/index.md` 按 ID 定位。")
    lines.append("")

    return "\n".join(lines) + "\n"


# ── Core Migration ─────────────────────────────────────────────────

def migrate_by_version(version_start, version_end, dry_run=False, migrate_evidence=True):
    """Archive completed tasks (and optionally evidence) for a version range.

    Args:
        version_start: e.g. "0.11.0"
        version_end: e.g. "0.24.0"
        dry_run: if True, report what would be done but don't modify files
        migrate_evidence: if True, also archive evidence entries for archived tasks

    Returns:
        dict with keys: success, dry_run, tasks_archived, tasks_remaining,
                        evidence_archived, archive_files_created, details
    """
    result = {
        "success": False,
        "dry_run": dry_run,
        "tasks_archived": 0,
        "tasks_remaining": 0,
        "evidence_archived": 0,
        "archive_files_created": [],
        "details": "",
    }

    if not dry_run:
        _ensure_archive_dirs()

    if not _plan_tracker().exists():
        result["details"] = "plan-tracker.md not found"
        return result

    content = _plan_tracker().read_text(encoding="utf-8")
    sections, lines = _find_version_sections(content)

    # Find sections in version range
    archived_task_lines = []  # (line_index, original_line, task_id, version)
    archived_tasks = set()
    already_archived_tasks = _get_archived_task_ids()
    archive_body_lines = []

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
                        continue
                    archived_task_lines.append((line_idx, line, task_id, section["version"]))
                    archived_tasks.add(task_id)
                    archive_body_lines.append((section["version"], line))
                else:
                    result["tasks_remaining"] += 1
        else:
            # Tasks in non-matching sections remain in hot file
            for _line_idx, _line, task_id in section["task_lines"]:
                result["tasks_remaining"] += 1

    # FIX-158: Also scan the priority table (### 优先级一览) which holds ALL tasks
    # in real plan-tracker, grouped by the row's "目标版本" column rather than by
    # version section headers. This makes the archive engine see tasks that were
    # previously invisible (the root cause of AUDIT-125 "无可归档数据").
    priority_tasks = _parse_priority_table_tasks(content)
    for line_idx, line, task_id, target_version, status in priority_tasks:
        if task_id in already_archived_tasks or task_id in archived_tasks:
            continue
        # Only consider tasks whose target version is in range (matching the
        # version-section behavior). Out-of-range tasks are left alone and not
        # counted as remaining (they belong to other version ranges).
        if not target_version:
            continue
        if not _version_in_range(target_version, version_start, version_end):
            continue
        if not _task_status_is_archivable(status):
            result["tasks_remaining"] += 1
            continue
        archived_task_lines.append((line_idx, line, task_id, target_version))
        archived_tasks.add(task_id)
        archive_body_lines.append((target_version, line))

    result["tasks_archived"] = len(archived_tasks)

    if result["tasks_archived"] == 0:
        result["success"] = True
        result["details"] = f"No completed tasks found in version range v{version_start}~v{version_end}"
        return result

    # Determine archive filename
    archive_filename = _make_incremental_archive_filename(version_start, version_end, "tasks")
    archive_path = _archive_dir() / "tasks" / archive_filename

    # Check existing archive files for prev/next links
    existing_files = _get_existing_archive_files("tasks")
    existing_names = [f.name for f in existing_files]

    prev_file = existing_names[-1] if existing_names else None

    # Build archive body with version sections
    # Group archived tasks by version
    tasks_by_version = {}
    for version, line in archive_body_lines:
        tasks_by_version.setdefault(version, []).append(line)

    archive_lines = []
    for version in sorted(tasks_by_version.keys(),
                          key=lambda v: _version_to_tuple(v)):
        # Find the original section title
        section = next((s for s in sections if s["version"] == version), None)
        if section:
            archive_lines.append("")
            archive_lines.append(section["title"])
            # Use a standard table header
            archive_lines.append("| 任务ID | 描述 | 优先级 | 依赖 | 目标版本 | 负责人 | 审查人 | 审查类型 | 闭环路径 | 状态 |")
            archive_lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
            for line in tasks_by_version[version]:
                archive_lines.append(line)
            archive_lines.append("")

    # Build header
    header = _build_archive_header(
        version_start, version_end, "tasks",
        result["tasks_archived"],
        prev_file=prev_file,
    )

    if dry_run:
        result["success"] = True
        result["details"] = (f"Dry-run: would archive {result['tasks_archived']} tasks "
                            f"from v{version_start}~v{version_end} to {archive_filename}")
        result["archive_files_created"] = [archive_filename]
        return result

    _write_archive_file(archive_path, header, archive_lines)
    result["archive_files_created"].append(f"archive/tasks/{archive_filename}")

    # Collect line indices from sample-table sections — these must NOT be
    # deleted from the hot file (sample-table rows are interleaved with
    # non-task text and deleting them would destroy table structure).
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

    if not dry_run:
        _plan_tracker().write_text("\n".join(final_lines), encoding="utf-8")

    # Migrate evidence if requested
    if migrate_evidence and archived_tasks and _evidence_log().exists():
        ev_content = _evidence_log().read_text(encoding="utf-8")
        ev_lines = ev_content.split("\n")

        ev_archived_lines = []
        ev_archived_count = 0
        ev_kept_lines = []

        for i, line in enumerate(ev_lines):
            stripped = line.strip()
            if not stripped.startswith("| EVD-"):
                ev_kept_lines.append(line)
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                raw_task_ids = parts[2]
                # Check if this evidence is for an archived task
                ev_task_ids = set()
                for tid in raw_task_ids.split(","):
                    tid = tid.strip()
                    if tid and re.match(r"[A-Z]+-\d+", tid):
                        ev_task_ids.add(tid)

                if ev_task_ids and ev_task_ids.issubset(archived_tasks):
                    ev_archived_lines.append(line)
                    ev_archived_count += 1
                    continue

            ev_kept_lines.append(line)

        if ev_archived_count > 0:
            # Create evidence archive file
            ev_archive_filename = archive_filename
            ev_archive_path = _archive_dir() / "evidence" / ev_archive_filename

            ev_archive_body = []
            if ev_archived_lines:
                ev_archive_body.append("| 证据ID | 关联Task | 摘要 | 日期 | 类型 | 产出 | 负责人 | 审查人 | 审查结果 | 备注 |")
                ev_archive_body.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
                ev_archive_body.extend(ev_archived_lines)

            ev_header = _build_archive_header(
                version_start, version_end, "evidence",
                ev_archived_count,
            )

            _write_archive_file(ev_archive_path, ev_header, ev_archive_body)
            result["archive_files_created"].append(f"archive/evidence/{ev_archive_filename}")
            result["evidence_archived"] = ev_archived_count

            # Update evidence-log.md
            _evidence_log().write_text("\n".join(ev_kept_lines), encoding="utf-8")

    result["success"] = True
    result["details"] = (f"Archived {result['tasks_archived']} tasks "
                        f"from v{version_start}~v{version_end}")
    return result


# ── Index Building ─────────────────────────────────────────────────

def _extract_tasks_from_archive_file(filepath):
    """Extract task IDs and statuses from an archive file.

    Returns list of (task_id, status, version_str) tuples.
    """
    if not filepath.exists():
        return []
    content = filepath.read_text(encoding="utf-8")
    results = []
    current_version = None

    for line in content.split("\n"):
        # Detect version section headers
        v, _ = _parse_version_from_title(line)
        if v:
            current_version = v
            continue

        # Parse task table rows
        stripped = line.strip()
        # FIX-158: support two table formats:
        #   (a) legacy 10-col with ID in column 1: "| TASKID-NNN | desc | ..."
        #   (b) 7-col priority table with ID in column 2: "| **P0** | TASKID-NNN | ..."
        # Try col-1 first (legacy), then col-2 (priority table).
        m = re.match(r"\|\s*([A-Z]+-\d+)\s*\|", stripped)
        col_offset = 0
        if not m:
            m = re.match(r"\|\s*\*{0,2}[Pp][0-9]\*{0,2}\s*\|\s*([A-Z]+-\d+)\s*\|", stripped)
            col_offset = 1  # status column shifts by 1 when ID is in col 2
        if m:
            task_id = m.group(1)
            # For the 7-col format, status is the last data column; for 10-col
            # legacy it was parts[10]. _parse_task_status defaults to last column
            # which works for both 7-col archive rows. Pass explicit col only if
            # we detect the legacy 10-col layout (>= 10 data cells).
            parts = [p.strip() for p in stripped.split("|")]
            data_cells = parts[1:-1] if len(parts) >= 2 else parts
            if len(data_cells) >= 10:
                status = _parse_task_status(stripped, status_col=9)
            else:
                status = _parse_task_status(stripped)
            # version may be in the 目标版本 column for 7-col format
            version = current_version or "unknown"
            if col_offset and len(data_cells) >= 5:
                tv = re.sub(r"[`*]", "", data_cells[4]).strip()
                if re.match(r"^\d+\.\d+\.\d+$", tv):
                    version = tv
            results.append((task_id, status, version))

    return results


def _extract_evidence_from_archive_file(filepath):
    """Extract evidence IDs and associated task IDs from an archive file.

    Returns list of (evidence_id, task_ids_str) tuples.
    """
    if not filepath.exists():
        return []
    content = filepath.read_text(encoding="utf-8")
    results = []

    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            evd_id = parts[1]
            task_ids = parts[2]
            if evd_id and re.match(r"EVD-\d+", evd_id):
                results.append((evd_id, task_ids))

    return results


def _get_archived_task_ids():
    """Return task IDs already present in archive task files."""
    archived = set()
    task_dir = _archive_dir() / "tasks"
    if not task_dir.exists():
        return archived
    for f in sorted(task_dir.glob("*.md")):
        if f.name == ".gitkeep":
            continue
        for task_id, _status, _version in _extract_tasks_from_archive_file(f):
            archived.add(task_id)
    return archived


def build_index():
    """Scan all archive files and build/rebuild archive/index.md.

    The index is a Markdown file with tables mapping entry IDs to
    their archive file locations.

    Returns:
        dict with keys: status, task_entries, evidence_entries,
                        decision_entries, risk_entries
    """
    result = {
        "status": "created",
        "task_entries": 0,
        "evidence_entries": 0,
        "decision_entries": 0,
        "risk_entries": 0,
    }

    _ensure_archive_dirs()

    # Collect task entries
    task_entries = []
    for f in sorted((_archive_dir() / "tasks").glob("*.md")):
        if f.name == ".gitkeep":
            continue
        rel_path = f"archive/tasks/{f.name}"
        for task_id, status, version in _extract_tasks_from_archive_file(f):
            task_entries.append({
                "id": task_id,
                "status": status or "?",
                "version": version,
                "file": rel_path,
            })

    # Collect evidence entries
    evidence_entries = []
    for f in sorted((_archive_dir() / "evidence").glob("*.md")):
        if f.name == ".gitkeep":
            continue
        rel_path = f"archive/evidence/{f.name}"
        for evd_id, task_ids in _extract_evidence_from_archive_file(f):
            evidence_entries.append({
                "id": evd_id,
                "task_ids": task_ids,
                "file": rel_path,
            })

    # Collect decision entries
    decision_entries = []
    for f in sorted((_archive_dir() / "decisions").glob("*.md")):
        if f.name == ".gitkeep":
            continue
        rel_path = f"archive/decisions/{f.name}"
        content = f.read_text(encoding="utf-8") if f.exists() else ""
        for m in re.finditer(r"##\s+(DEC-\d+):\s*(.*)", content):
            decision_entries.append({
                "id": m.group(1),
                "title": m.group(2).strip(),
                "file": rel_path,
            })

    # Collect risk entries
    risk_entries = []
    for f in sorted((_archive_dir() / "risks").glob("*.md")):
        if f.name == ".gitkeep":
            continue
        rel_path = f"archive/risks/{f.name}"
        content = f.read_text(encoding="utf-8") if f.exists() else ""
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped.startswith("| RISK-"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                risk_id = parts[1]
                desc = parts[2]
                if risk_id and re.match(r"RISK-\d+", risk_id):
                    risk_entries.append({
                        "id": risk_id,
                        "description": desc,
                        "file": rel_path,
                    })

    result["task_entries"] = len(task_entries)
    result["evidence_entries"] = len(evidence_entries)
    result["decision_entries"] = len(decision_entries)
    result["risk_entries"] = len(risk_entries)

    # Build index.md content
    index_lines = [
        "# 归档索引",
        "",
        "> 自动生成，记录每个治理条目的归档位置。查询路径：条目 ID → 归档文件。",
        "> 维护方式：归档脚本执行时自动更新。可通过 `build_index()` 重建。",
        "",
        "---",
        "",
        "## Task 索引",
        "",
        "| Task ID | 状态 | 版本 | 归档文件 |",
        "|---------|------|------|---------|",
    ]

    for entry in task_entries:
        index_lines.append(
            f"| {entry['id']} | {entry['status']} | {entry['version']} | {entry['file']} |"
        )

    index_lines.extend([
        "",
        "## Evidence 索引",
        "",
        "| Evidence ID | Task ID | 归档文件 |",
        "|-------------|--------|---------|",
    ])

    for entry in evidence_entries:
        index_lines.append(
            f"| {entry['id']} | {entry['task_ids']} | {entry['file']} |"
        )

    index_lines.extend([
        "",
        "## Decision 索引",
        "",
        "| Decision ID | 标题 | 归档文件 |",
        "|-------------|------|---------|",
    ])

    for entry in decision_entries:
        index_lines.append(
            f"| {entry['id']} | {entry['title']} | {entry['file']} |"
        )

    index_lines.extend([
        "",
        "## Risk 索引",
        "",
        "| Risk ID | 描述 | 归档文件 |",
        "|---------|------|---------|",
    ])

    for entry in risk_entries:
        index_lines.append(
            f"| {entry['id']} | {entry['description']} | {entry['file']} |"
        )

    index_lines.append("")

    _index_path().write_text("\n".join(index_lines), encoding="utf-8")

    return result


# ── Integrity Verification ─────────────────────────────────────────

def verify_archive_integrity():
    """Verify archive integrity: index-archive consistency.

    Checks:
      1. Every file referenced in index.md exists
      2. Every entry in archive files has a corresponding index entry
      3. No orphan archive files (files exist but not in index)

    Returns:
        dict with keys: pass, issues (list of issue strings),
                        total_archived_tasks, total_index_entries
    """
    result = {
        "pass": True,
        "issues": [],
        "total_archived_tasks": 0,
        "total_index_entries": 0,
    }

    _ensure_archive_dirs()

    # If no index and no archive files, pass trivially
    archive_files = []
    for subdir in ["tasks", "evidence", "decisions", "risks"]:
        d = _archive_dir() / subdir
        if d.exists():
            for f in d.glob("*.md"):
                if f.name != ".gitkeep":
                    archive_files.append((subdir, f))

    if not archive_files and not _index_path().exists():
        result["pass"] = True
        return result

    # If there are archive files but no index, that's an issue
    if archive_files and not _index_path().exists():
        result["pass"] = False
        result["issues"].append(
            f"有 {len(archive_files)} 个归档文件但 index.md 不存在。"
            f"运行 build_index() 重建索引。"
        )
        return result

    if not _index_path().exists():
        result["pass"] = True
        return result

    # Parse index
    index_content = _index_path().read_text(encoding="utf-8")
    index_lines = index_content.split("\n")

    # Extract file references from each index section
    def _parse_index_section(content_lines, section_name):
        """Extract rows from a specific index section."""
        refs = set()
        in_section = False
        table_started = False

        for line in content_lines:
            if line.strip() == f"## {section_name}":
                in_section = True
                continue
            if in_section and line.strip().startswith("## "):
                in_section = False
                continue
            if not in_section:
                continue
            stripped = line.strip()
            if "|---" in stripped:
                table_started = True
                continue
            if not table_started:
                continue
            if not stripped.startswith("| "):
                continue

            parts = [p.strip() for p in line.split("|")]
            if section_name == "Task 索引":
                if len(parts) >= 5:
                    refs.add(parts[4])  # archive file column
            elif section_name == "Evidence 索引":
                if len(parts) >= 4:
                    refs.add(parts[3])
            elif section_name == "Decision 索引":
                if len(parts) >= 4:
                    refs.add(parts[3])
            elif section_name == "Risk 索引":
                if len(parts) >= 4:
                    refs.add(parts[3])

        return refs

    index_task_refs = _parse_index_section(index_lines, "Task 索引")
    index_evidence_refs = _parse_index_section(index_lines, "Evidence 索引")
    index_decision_refs = _parse_index_section(index_lines, "Decision 索引")
    index_risk_refs = _parse_index_section(index_lines, "Risk 索引")

    all_index_refs = index_task_refs | index_evidence_refs | index_decision_refs | index_risk_refs

    # Check 1: Every referenced archive file exists
    for ref in all_index_refs:
        filepath = ROOT / ".governance" / ref
        if not filepath.exists():
            result["pass"] = False
            result["issues"].append(f"索引引用的归档文件不存在: {ref}")

    # Check 2: Every archive file is referenced in index
    actual_files = set()
    for subdir, f in archive_files:
        rel = f"archive/{subdir}/{f.name}"
        actual_files.add(rel)

    unreferenced = actual_files - all_index_refs
    if unreferenced:
        result["pass"] = False
        for f in sorted(unreferenced):
            result["issues"].append(f"归档文件未在索引中记录: {f}")

    # Check 3: Extract IDs from archive files and count
    total_in_files = 0
    for subdir, f in archive_files:
        if subdir == "tasks":
            total_in_files += len(_extract_tasks_from_archive_file(f))
        elif subdir == "evidence":
            total_in_files += len(_extract_evidence_from_archive_file(f))

    result["total_archived_tasks"] = total_in_files

    # Count index entries
    total_in_index = 0
    for line in index_lines:
        stripped = line.strip()
        if stripped.startswith("| ") and re.match(r"\|\s*[A-Z]+-\d+", stripped):
            total_in_index += 1

    result["total_index_entries"] = total_in_index

    return result


# ── Rollback ────────────────────────────────────────────────────────

def _get_migration_archive_group(subdir, archive_file):
    """Return archive files that belong to the same migration.

    A normal migration writes task and evidence archive files with the same
    filename in sibling directories.  Rollback therefore treats those same-name
    files as one migration unit while still supporting older task-only or
    evidence-only archives.
    """
    group = []
    for candidate_subdir in ["tasks", "evidence"]:
        candidate = _archive_dir() / candidate_subdir / archive_file.name
        if candidate.exists() and candidate.is_file() and candidate.name != ".gitkeep":
            group.append((candidate_subdir, candidate))

    if group:
        return group
    return [(subdir, archive_file)]


def _rollback_task_archive(archive_file):
    """Restore one task archive file into plan-tracker.md and remove it."""
    archive_content = archive_file.read_text(encoding="utf-8")
    pt_content = _plan_tracker().read_text(encoding="utf-8") if _plan_tracker().exists() else ""

    # Find the body after the header section
    body_start = 0
    archive_lines = archive_content.split("\n")
    for i, line in enumerate(archive_lines):
        if line.startswith("#") and "归档" in line:
            continue
        if line.startswith("- **归档日期") or line.startswith("- **归档范围") or \
           line.startswith("- **条目数") or line.startswith("- **上一个") or \
           line.startswith("- **下一个") or line.startswith("> "):
            continue
        if line.startswith("###") or line.startswith("---"):
            body_start = i
            break

    # Append task content back to plan-tracker
    task_body = "\n".join(archive_lines[body_start:])
    new_pt = pt_content.rstrip() + "\n\n" + task_body + "\n"

    # Remove [已归档] markers ONLY from version titles in the archive file's
    # version range (not globally).  Parse the version range from the archive
    # filename first; fall back to extracting versions from archive content.
    filename_range = _parse_archive_version_range(archive_file.name)
    if filename_range:
        version_start, version_end = filename_range
        new_lines = new_pt.split("\n")
        for i, line in enumerate(new_lines):
            v_str, _ = _parse_version_from_title(line)
            if v_str and _version_in_range(v_str, version_start, version_end):
                if "[已归档]" in line and not _version_still_covered_by_task_archive(
                    v_str, archive_file
                ):
                    new_lines[i] = line.replace("[已归档]", "").rstrip()
        new_pt = "\n".join(new_lines)
    else:
        # Fallback: find versions that appear in the archive body
        archive_sections, _ = _find_version_sections(archive_content)
        archived_versions = {
            s["version"] for s in archive_sections if s.get("version")
        }
        if archived_versions:
            new_lines = new_pt.split("\n")
            for i, line in enumerate(new_lines):
                v_str, _ = _parse_version_from_title(line)
                if v_str and v_str in archived_versions:
                    if "[已归档]" in line and not _version_still_covered_by_task_archive(
                        v_str, archive_file
                    ):
                        new_lines[i] = line.replace("[已归档]", "").rstrip()
            new_pt = "\n".join(new_lines)

    _plan_tracker().write_text(new_pt, encoding="utf-8")
    archive_file.unlink()
    return f"{archive_file.name} → plan-tracker.md"


def _rollback_evidence_archive(archive_file):
    """Restore one evidence archive file into evidence-log.md and remove it."""
    archive_content = archive_file.read_text(encoding="utf-8")
    ev_content = _evidence_log().read_text(encoding="utf-8") if _evidence_log().exists() else ""

    # Extract evidence rows from archive
    ev_rows = []
    for line in archive_content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("| EVD-"):
            ev_rows.append(line)

    if ev_rows:
        new_ev = ev_content.rstrip() + "\n" + "\n".join(ev_rows) + "\n"
        _evidence_log().write_text(new_ev, encoding="utf-8")

    archive_file.unlink()
    return f"{archive_file.name} → evidence-log.md"


def rollback_last_migration():
    """Rollback the most recent migration by:
    1. Finding the most recently modified archive file
    2. Rolling back same-name task/evidence archive files as one migration group
    3. Merging their content back into the hot files and removing archive files
    4. Updating the index

    Returns:
        dict with keys: success, rolled_back_file, rolled_back_files, details
    """
    result = {
        "success": False,
        "rolled_back_file": None,
        "rolled_back_files": [],
        "details": "",
    }

    _ensure_archive_dirs()

    # Find most recently modified archive task file
    recent_files = []
    for subdir in ["tasks", "evidence"]:
        d = _archive_dir() / subdir
        if d.exists():
            for f in d.glob("*.md"):
                if f.name != ".gitkeep":
                    stat_result = f.stat()
                    incremental_priority = 1 if "-incremental-" in f.name else 0
                    recent_files.append(
                        (stat_result.st_mtime_ns, incremental_priority, f.name, subdir, f)
                    )

    if not recent_files:
        result["details"] = "没有找到归档文件，无法回滚。"
        return result

    recent_files.sort(reverse=True)
    _mtime_ns, _incremental_priority, _name, subdir, archive_file = recent_files[0]

    migration_files = _get_migration_archive_group(subdir, archive_file)
    result["rolled_back_files"] = [
        f"archive/{group_subdir}/{group_file.name}"
        for group_subdir, group_file in migration_files
    ]
    result["rolled_back_file"] = ", ".join(result["rolled_back_files"])

    details = []
    for group_subdir, group_file in migration_files:
        if group_subdir == "tasks":
            details.append(_rollback_task_archive(group_file))
        elif group_subdir == "evidence":
            details.append(_rollback_evidence_archive(group_file))

    result["success"] = bool(details)
    if result["success"]:
        result["details"] = "已回滚 " + "; ".join(details)

    # Rebuild index after rollback
    build_index()

    return result


# ── Version Roadmap Parsing ─────────────────────────────────────────

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


# ── Auto Migration ──────────────────────────────────────────────────

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


def _days_since_file(path):
    if not path.exists():
        return None
    modified = date.fromtimestamp(path.stat().st_mtime)
    return (date.today() - modified).days


def analyze_auto_archive_candidates():
    """Analyze whether continuous auto archive should run.

    This pure analysis is shared by archive.py --auto and verify_workflow.py.
    It covers the FIX-063 trigger loop:
      - first migration threshold
      - release-forced incremental archive when index already exists
      - task-count incremental threshold
      - 90-day fallback
    """
    result = {
        "success": False,
        "should_archive": False,
        "skipped": False,
        "reason": "",
        "triggers": [],
        "versions_archived": [],
        "versions_range": None,
        "tasks_archived": 0,
        "plan_tracker_size": 0,
        "published_count": 0,
        "index_exists": False,
        "days_since_archive": None,
    }

    if not _plan_tracker().exists():
        result["skipped"] = True
        result["reason"] = "plan-tracker.md 不存在"
        return result

    result["success"] = True
    result["plan_tracker_size"] = _plan_tracker().stat().st_size
    result["index_exists"] = _index_path().exists()
    result["days_since_archive"] = _days_since_file(_index_path())

    content = _plan_tracker().read_text(encoding="utf-8")
    roadmap_entries = _parse_version_roadmap_entries(content)
    published = [
        entry for entry in roadmap_entries
        if entry.get("status") == "已发布"
    ]
    published.sort(key=lambda entry: _version_to_tuple(entry["version"]))
    result["published_count"] = len(published)

    if len(published) < 2:
        result["skipped"] = True
        result["reason"] = f"已发布版本数不足（{len(published)} < 2），跳过归档"
        return result

    archive_entries = published[:-1]
    version_start = archive_entries[0]["version"]
    version_end = archive_entries[-1]["version"]
    result["versions_archived"] = [entry["version"] for entry in archive_entries]
    result["versions_range"] = (version_start, version_end)

    pre_check = migrate_by_version(version_start, version_end, dry_run=True)
    result["tasks_archived"] = pre_check.get("tasks_archived", 0)

    # FIX-158: do NOT early-return when tasks_archived==0. The original code
    # returned here, which made release_forced / fallback_90d dead code
    # (AUDIT-125 root cause #2). Triggers must be evaluated regardless of
    # task count, because release_forced depends only on index_exists and
    # fallback_90d depends only on dates. We record a note instead of skipping.
    no_archivable_tasks = result["tasks_archived"] == 0

    if (
        not result["index_exists"]
        and result["plan_tracker_size"] > FIRST_MIGRATION_PLAN_SIZE_THRESHOLD
    ):
        result["triggers"].append("first_migration")

    if result["index_exists"]:
        result["triggers"].append("release_forced")

    if result["tasks_archived"] >= TASK_INCREMENTAL_THRESHOLD:
        result["triggers"].append("task_incremental")

    version_end_entry = archive_entries[-1]
    version_end_date = _parse_iso_date(version_end_entry.get("date", ""))
    if version_end_date and (date.today() - version_end_date).days >= FALLBACK_ARCHIVE_DAYS:
        result["triggers"].append("fallback_90d")
    elif result["days_since_archive"] is not None and result["days_since_archive"] >= FALLBACK_ARCHIVE_DAYS:
        result["triggers"].append("fallback_90d")

    result["triggers"] = sorted(set(result["triggers"]))
    # FIX-158: should_archive requires BOTH a trigger AND archivable tasks.
    # A trigger firing with zero archivable tasks (e.g. all already archived)
    # is NOT an actionable archive signal — reporting it as should_archive=True
    # would make check-archive-integrity perpetually flag a clean state.
    result["should_archive"] = bool(result["triggers"]) and not no_archivable_tasks
    if not result["should_archive"]:
        result["skipped"] = True
        if result["triggers"] and no_archivable_tasks:
            result["reason"] = (
                f"归档范围 v{version_start}~v{version_end} 触发器满足（{', '.join(result['triggers'])}）"
                "但无可归档数据——可能已全部归档或格式未被识别"
            )
        else:
            result["reason"] = (
                "归档触发条件未满足"
                f"（tasks={result['tasks_archived']}, plan={result['plan_tracker_size']} bytes）"
            )
    return result

def migrate_auto(dry_run=False):
    """Auto-detect version range from plan-tracker roadmap and migrate data.

    Pipeline:
    1. Parse version roadmap → filter published versions
    2. Determine archive range [oldest, second-newest]
    3. Pre-check dry-run → skip if no data
    4. Idempotency: skip if archive/index.md exists
    5. Execute migrate_by_version + build_index + verify
    6. Calculate file size changes
    7. Return structured summary dict

    Args:
        dry_run: if True, preview without modifying files

    Returns:
        dict with keys: success, skipped, reason, versions_archived,
        versions_range, tasks_archived, evidence_archived,
        plan_tracker_before, plan_tracker_after,
        evidence_log_before, evidence_log_after,
        archive_files_created, verify_pass, details
    """
    result = {
        "success": False,
        "skipped": False,
        "reason": "",
        "versions_archived": [],
        "versions_range": None,
        "tasks_archived": 0,
        "evidence_archived": 0,
        "plan_tracker_before": 0,
        "plan_tracker_after": 0,
        "evidence_log_before": 0,
        "evidence_log_after": 0,
        "archive_files_created": [],
        "verify_pass": False,
        "triggers": [],
        "details": "",
    }

    if not dry_run:
        _ensure_archive_dirs()

    analysis = analyze_auto_archive_candidates()
    result["versions_archived"] = analysis.get("versions_archived", [])
    result["versions_range"] = analysis.get("versions_range")
    result["tasks_archived"] = analysis.get("tasks_archived", 0)
    result["triggers"] = analysis.get("triggers", [])

    if analysis.get("skipped") or not analysis.get("should_archive"):
        result["success"] = analysis.get("success", False)
        result["skipped"] = True
        result["reason"] = analysis.get("reason", "")
        return result

    version_start, version_end = result["versions_range"]

    # Dry-run mode: report preview and return
    if dry_run:
        result["success"] = True
        result["details"] = (
            f"Dry-run: 将归档 {result['tasks_archived']} 个 task "
            f"(v{version_start}~v{version_end}); "
            f"triggers={','.join(result['triggers'])}"
        )
        return result

    # Record file sizes before migration
    result["plan_tracker_before"] = (
        _plan_tracker().stat().st_size if _plan_tracker().exists() else 0
    )
    result["evidence_log_before"] = (
        _evidence_log().stat().st_size if _evidence_log().exists() else 0
    )

    # Execute migration
    migrate_result = migrate_by_version(
        version_start, version_end, dry_run=False, migrate_evidence=True
    )

    if not migrate_result["success"]:
        result["details"] = (
            f"迁移失败: {migrate_result.get('details', 'Unknown error')}"
        )
        return result

    result["tasks_archived"] = migrate_result["tasks_archived"]
    result["evidence_archived"] = migrate_result.get("evidence_archived", 0)
    result["archive_files_created"] = migrate_result.get(
        "archive_files_created", []
    )

    # Build index
    build_index()

    # Verify integrity
    verify_result = verify_archive_integrity()
    result["verify_pass"] = verify_result["pass"]

    # Record file sizes after migration
    result["plan_tracker_after"] = (
        _plan_tracker().stat().st_size if _plan_tracker().exists() else 0
    )
    result["evidence_log_after"] = (
        _evidence_log().stat().st_size if _evidence_log().exists() else 0
    )

    result["success"] = True
    result["details"] = (
        f"归档完成: {result['tasks_archived']} 个 task, "
        f"{result['evidence_archived']} 条证据 "
        f"(v{version_start}~v{version_end})"
    )
    return result


def _format_auto_summary(result):
    """Format migrate_auto() result as a human-readable summary string.

    Returns summary suitable for bootstrap output stream.
    """
    if result.get("skipped"):
        return f"📦 治理数据归档: 跳过（无可归档数据——{result.get('reason', '')}）"

    vr = result.get("versions_range")
    if vr:
        range_str = f"v{vr[0]} ~ v{vr[1]}（{len(result['versions_archived'])}个版本）"
    else:
        range_str = "未知"

    lines = [
        "📦 治理数据归档完成:",
        f"  - 归档范围: {range_str}",
    ]

    task_file = next(
        (f for f in result.get("archive_files_created", []) if f.startswith("archive/tasks/")),
        f"archive/tasks/v{result['versions_range'][0]}~v{result['versions_range'][1]}.md",
    )
    lines.append(f"  - 归档 {result['tasks_archived']} 个 task → {task_file}")

    if result.get("evidence_archived", 0) > 0:
        evidence_file = next(
            (f for f in result.get("archive_files_created", []) if f.startswith("archive/evidence/")),
            f"archive/evidence/v{result['versions_range'][0]}~v{result['versions_range'][1]}.md",
        )
        lines.append(f"  - 归档 {result['evidence_archived']} 条证据 → {evidence_file}")

    # File size changes
    pt_before = result.get("plan_tracker_before", 0)
    pt_after = result.get("plan_tracker_after", 0)
    if pt_before > 0 and pt_after > 0:
        pt_kb_before = pt_before / 1024
        pt_kb_after = pt_after / 1024
        pt_pct = int((1 - pt_after / pt_before) * 100)
        lines.append(
            f"  - plan-tracker: {pt_kb_before:.0f}KB → {pt_kb_after:.0f}KB (-{pt_pct}%)"
        )

    ev_before = result.get("evidence_log_before", 0)
    ev_after = result.get("evidence_log_after", 0)
    if ev_before > 0 and ev_after > 0:
        ev_kb_before = ev_before / 1024
        ev_kb_after = ev_after / 1024
        ev_pct = int((1 - ev_after / ev_before) * 100)
        lines.append(
            f"  - evidence-log: {ev_kb_before:.0f}KB → {ev_kb_after:.0f}KB (-{ev_pct}%)"
        )

    lines.append(f"  - 索引: archive/index.md（{result['tasks_archived']} 条目）")
    lines.append(
        f"  - 校验: {'PASS' if result.get('verify_pass') else 'FAILED'}"
    )

    return "\n".join(lines)


# ── CLI Entry Point ─────────────────────────────────────────────────

def main():
    """CLI for archive operations."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="archive",
        description="Governance Data Archive Tool — SYSGAP-030",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # migrate
    migrate_p = subparsers.add_parser("migrate", help="Archive tasks for a version range")
    migrate_p.add_argument("version_start", nargs="?", default=None,
                           help="Start version (e.g. 0.11.0)")
    migrate_p.add_argument("version_end", nargs="?", default=None,
                           help="End version (e.g. 0.24.0)")
    migrate_p.add_argument("--dry-run", action="store_true",
                           help="Report what would be archived without modifying files")
    migrate_p.add_argument("--no-evidence", action="store_true",
                           help="Skip evidence archiving")
    migrate_p.add_argument("--auto", action="store_true",
                           help="Auto-detect version range from plan-tracker roadmap")

    # build-index
    subparsers.add_parser("build-index", help="Rebuild archive/index.md from archive files")

    # verify
    subparsers.add_parser("verify", help="Verify archive integrity")

    # rollback
    subparsers.add_parser("rollback", help="Rollback the most recent migration")

    args = parser.parse_args()

    # Ensure stdout supports UTF-8 (Windows consoles default to GBK)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    if args.command == "migrate":
        if args.auto:
            result = migrate_auto(dry_run=args.dry_run)
            print(_format_auto_summary(result))
            if not result["skipped"] and not result["success"]:
                sys.exit(1)
        elif args.version_start and args.version_end:
            result = migrate_by_version(
                args.version_start,
                args.version_end,
                dry_run=args.dry_run,
                migrate_evidence=not args.no_evidence,
            )
            print(f"  Dry-run: {result['dry_run']}")
            print(f"  Tasks archived: {result['tasks_archived']}")
            print(f"  Tasks remaining: {result['tasks_remaining']}")
            print(f"  Evidence archived: {result.get('evidence_archived', 0)}")
            print(f"  Files created: {result.get('archive_files_created', [])}")
            print(f"  {result['details']}")
            if not result["success"]:
                sys.exit(1)
        else:
            print("Error: Either --auto or both version_start and version_end must be provided.")
            migrate_p.print_usage()
            sys.exit(1)

    elif args.command == "build-index":
        result = build_index()
        print(f"  Status: {result['status']}")
        print(f"  Task entries: {result['task_entries']}")
        print(f"  Evidence entries: {result['evidence_entries']}")
        print(f"  Decision entries: {result['decision_entries']}")
        print(f"  Risk entries: {result['risk_entries']}")

    elif args.command == "verify":
        result = verify_archive_integrity()
        print(f"  Pass: {result['pass']}")
        print(f"  Total archived tasks: {result['total_archived_tasks']}")
        print(f"  Total index entries: {result['total_index_entries']}")
        if result["issues"]:
            print(f"  Issues ({len(result['issues'])}):")
            for issue in result["issues"]:
                print(f"    - {issue}")
        if not result["pass"]:
            sys.exit(1)

    elif args.command == "rollback":
        result = rollback_last_migration()
        print(f"  Success: {result['success']}")
        print(f"  Rolled back: {result['rolled_back_file']}")
        print(f"  {result['details']}")
        if not result["success"]:
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
