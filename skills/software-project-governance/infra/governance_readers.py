"""Pure Markdown readers shared by the CLI, bootstrap and local dashboard."""

import json
import re


def _section_lines(text, heading, *, prefix=False):
    inside = False
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped == heading or (prefix and stripped.startswith(heading)):
            inside = True
        elif inside and line.startswith("## "):
            break
        elif inside:
            yield line


def config_from_lines(lines):
    config = {}
    for line in lines:
        match = re.match(r"- \*\*(.+?)\*\*:\s*(.+)", line)
        if match:
            config[match.group(1)] = match.group(2)
    return config


def project_config(text):
    return config_from_lines(_section_lines(text, "## 项目配置"))


_PLAN_TOKEN = re.compile(r"`+|[|{\[]")
_JSON_VALUE = json.JSONDecoder()


def plan_table_cells(line):
    """Split bordered plan rows, protecting complete code spans and JSON values.

    Free text may contain unmatched quotes, brackets or backticks. Those
    characters do not hide a later column separator.
    """
    cells = []
    start = 0
    cursor = 0
    while token := _PLAN_TOKEN.search(line, cursor):
        value = token.group()
        cursor = token.end()
        if value == "|":
            cells.append(line[start:token.start()].strip())
            start = cursor
        elif value.startswith("`"):
            close = re.search(rf"(?<!`){value}(?!`)", line[cursor:])
            if close:
                cursor += close.end()
        else:
            try:
                _, cursor = _JSON_VALUE.raw_decode(line, token.start())
            except (ValueError, RecursionError):
                continue  # prose or incomplete JSON; later pipes still delimit columns
    # Each delimiter ends a cell; the first delimiter opens the bordered row.
    return cells[1:]


def _data_rows(lines, first_heading, width):
    for line in lines:
        if line.startswith("|"):
            cells = plan_table_cells(line)
            if (len(cells) >= width and cells[0] != first_heading
                    and not all(set(cell) <= {"-", " "} for cell in cells)):
                yield cells


def gate_status(text):
    lines = _section_lines(text, "## Gate 状态跟踪", prefix=True)
    keys = ("gate", "transition", "status", "date", "evidence")
    return [dict(zip(keys, row)) for row in _data_rows(lines, "Gate", len(keys))]


def overview_from_lines(lines):
    keys = ("project", "current_stage", "total", "completed", "blocked", "risks",
            "latest_gate", "latest_retro")
    for row in _data_rows(lines, "项目", len(keys)):
        return dict(zip(keys, row))
    return {}


def overview(text):
    return overview_from_lines(_section_lines(text, "## 项目总览"))


def is_evidence_id(cell):
    return re.match(r"^(?:EVD-\d+|REVIEW-[A-Z]+-\d+)", cell) is not None


def markdown_table_cells(line):
    """Split a markdown table row while ignoring pipes inside inline code."""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    cells = []
    buf = []
    in_code = False
    i = 1 if stripped.startswith("|") else 0
    end = len(stripped) - 1 if stripped.endswith("|") else len(stripped)
    while i < end:
        ch = stripped[i]
        if ch == "`":
            in_code = not in_code
            buf.append(ch)
        elif ch == "|" and not in_code:
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    cells.append("".join(buf).strip())
    return cells


def count_evidence_rows(evidence_text):
    count = 0
    for line in evidence_text.splitlines():
        cells = markdown_table_cells(line)
        if cells and is_evidence_id(cells[0]):
            count += 1
    return count


def split_governance_table_row(line):
    """Split a Markdown table row while preserving pipes inside JSON cells.

    FIX-373: a ``"`` inside a code span is literal text and must NOT open
    the JSON-string state — an unguarded quote flipped ``in_string`` on,
    which in turn suppressed the code-span backtick toggle (backtick branch
    requires ``not in_string``), pinned the state to end-of-line and folded
    every remaining pipe (live: EVD-248 row folded 10 data cells -> 5).
    """
    parts = []
    current = []
    depth = 0
    in_string = False
    in_code_span = False
    escape = False

    for ch in line:
        if ch == "`" and not in_string:
            in_code_span = not in_code_span
            current.append(ch)
            continue

        if in_string:
            current.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"' and not in_code_span:
            in_string = True
            current.append(ch)
        elif ch in "{[":
            depth += 1
            current.append(ch)
        elif ch in "}]":
            if depth > 0:
                depth -= 1
            current.append(ch)
        elif ch == "|" and depth == 0 and not in_code_span:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)

    parts.append("".join(current))
    return parts


def governance_table_cells(line):
    cells = [p.strip() for p in split_governance_table_row(line.strip())]
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return cells
