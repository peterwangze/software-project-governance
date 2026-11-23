"""Risk-log rows shared by bootstrap, status, context and the time-based checks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date


_SEPARATOR_CELL = re.compile(r":?-+:?")
_FENCE = re.compile(r"^(`{3,}|~{3,})")
_RISK_ID = re.compile(r"RISK-[0-9]+")
_ISO_DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_OPEN = ("打开", "缓解中")
_CLOSED = ("已关闭", "关闭", "缓解完成", "已缓解", "已收窄", "降级")
_LEGACY_HEADER = ("编号", "日期", "风险/阻塞描述", "所属阶段", "触发条件", "影响",
                  "严重级别", "owner", "当前状态", "缓解动作", "截止日期", "关联任务", "备注")


def _cells(line):
    """Split at unescaped pipes, preserving original text inside each cell."""
    if "|" not in line:
        return []
    if "\\" in line:
        parts = []
        start = 0
        # Consume escaped pairs together: an even run of backslashes before
        # a pipe leaves the pipe as a delimiter; an odd run makes it literal.
        for token in re.finditer(r"\\.|\|", line):
            if token.group() == "|":
                parts.append(line[start:token.start()])
                start = token.end()
        if not parts:
            return []
        parts.append(line[start:])
    else:
        parts = line.split("|")
    if parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return [part.strip() for part in parts]


def _delimiter_width(line):
    stripped = line.lstrip("|: \t")
    if not stripped.startswith("-"):
        return 0
    cells = _cells(line)
    return len(cells) if cells and all(_SEPARATOR_CELL.fullmatch(c) for c in cells) else 0


def _table_lines(text):
    """Recognize a header only when its following delimiter row has equal width."""
    lines = [line.strip() for line in (text or "").splitlines()]
    header = None
    rows = []
    fence = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        if fence:
            if line.startswith(fence) and not line.strip(fence[0]):
                fence = ""
            continue
        marker = _FENCE.match(line)
        if marker:
            fence = marker.group()
            if header is not None:
                yield header, rows
                header, rows = None, []
            continue
        if not line:
            # Existing project logs use blank lines between groups of rows.
            continue
        cells = _cells(line)
        delimiter = i
        # The historical table reader accepted empty lines before the rule in
        # bordered tables. A valid, equal-width rule is still required.
        if cells and line.startswith("|"):
            while delimiter < len(lines) and not lines[delimiter]:
                delimiter += 1
        if cells and delimiter < len(lines) and _delimiter_width(lines[delimiter]) == len(cells):
            if header is not None:
                yield header, rows
            header, rows = cells, []
            i = delimiter + 1
        elif not cells or _delimiter_width(line):
            if header is not None:
                yield header, rows
                header, rows = None, []
        elif header is not None:
            rows.append((line, cells))
    if header is not None:
        yield header, rows


def iter_positional_tables(text):
    """Compatibility reader for bootstrap and authority-ledger callers."""
    for header, rows in _table_lines(text):
        yield header, [cells for _, cells in rows]


def display_cell(value):
    """Markdown display text, following the existing status API's cell contract."""
    return str(value or "").strip().strip("`").replace("**", "").strip()


def status_bucket(value):
    token = display_cell(value).strip("`*").strip()
    if token.startswith(_OPEN):
        return "open"
    if token.startswith(_CLOSED) or token.lower() in {
            "closed", "resolved", "closed/resolved", "resolved/closed"}:
        return "closed"
    return "unknown"


def _status_position(cells, pos):
    # RISK-052..059 omitted 影响, then supplied an evidence cell near the tail.
    # Only this identifiable layout justifies treating the Owner cell as status.
    # An unrelated "已关闭…" in mitigation or notes cannot close an unknown row.
    if (pos == 8 and len(cells) > pos and status_bucket(cells[pos]) == "unknown"
            and cells[pos].startswith(("缓解：", "缓解:"))
            and re.match(r"^(?:低|中|高|严重)", cells[5])):
        candidate = pos - 1
        if status_bucket(cells[candidate]) == "unknown" or sum(
                status_bucket(cell) != "unknown" for cell in cells) == 1:
            return candidate
    return pos


def resolve_status(cells, status_pos):
    """Legacy bootstrap/authority-ledger two-value interface."""
    index = _status_position(cells, status_pos)
    value = cells[index] if index < len(cells) else ""
    return value, status_bucket(value)


def iso_day(value):
    value = display_cell(value)
    if _ISO_DAY.fullmatch(value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return None


@dataclass(frozen=True)
class RiskRow:
    id: str
    opened_date: str
    description: str
    severity: str
    owner: str
    status: str
    bucket: str
    deadline: str
    deadline_date: date | None
    deadline_kind: str
    raw_line: str

    def days_left(self, today):
        return (self.deadline_date - today).days if self.deadline_date else None


def _risk_tables(text):
    saw_table = False
    for header, rows in _table_lines(text):
        saw_table = True
        aliases = {"风险描述": "风险/阻塞描述", "负责人": "owner"}
        names = [display_cell(cell).strip("`*").strip().lower() for cell in header]
        yield [aliases.get(name, name) for name in names], rows
    if not saw_table:
        # Old Check 2 callers supplied a file containing just canonical risk
        # rows, without Markdown headers. Never rescue ghost rows in a document.
        lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
        rows = [(line, _cells(line)) for line in lines]
        if rows and all(cells and _RISK_ID.fullmatch(display_cell(cells[0])) for _, cells in rows):
            yield _LEGACY_HEADER, rows


def iter_risk_rows(text):
    """Read recorded rows, including closed rows retained for migration."""
    for header, lines in _risk_tables(text):
        if "编号" not in header or "当前状态" not in header:
            continue
        indexes = {key: header.index(key) for key in _LEGACY_HEADER if key in header}
        canonical_layout = tuple(header[:9]) == _LEGACY_HEADER[:9]
        for line, cells in lines:
            def cell(key, offset=0):
                pos = indexes.get(key)
                if pos is None or not 0 <= pos + offset < len(cells):
                    return ""
                return cells[pos + offset]

            rid = display_cell(cell("编号"))
            if not _RISK_ID.fullmatch(rid):
                continue
            status_pos = indexes["当前状态"]
            actual_pos = _status_position(cells, status_pos) if canonical_layout else status_pos
            status = cells[actual_pos] if actual_pos < len(cells) else ""
            bucket = status_bucket(status)
            deadline = cell("截止日期")
            parsed = iso_day(deadline)
            if parsed:
                kind = "dated"
            elif ("截止日期" in indexes and indexes["截止日期"] < len(cells)
                  and display_cell(deadline) in ("", "—", "-", "无")):
                # An existing empty/placeholder cell declares no date. When
                # the column or cell is absent, its value is unjudgeable.
                kind = "none"
            else:
                kind = "invalid"
            offset = actual_pos - status_pos
            yield RiskRow(rid, cell("日期"), cell("风险/阻塞描述"),
                          cell("严重级别", offset), cell("owner", offset), status,
                          bucket, deadline, parsed, kind, line)


def iter_active_risks(text):
    """Unknown statuses stay on the same active face as open and mitigating rows."""
    return (row for row in iter_risk_rows(text) if row.bucket != "closed")
