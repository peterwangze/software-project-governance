"""Read models shared by the CLI, session bootstrap and local dashboard."""

import json
import re
from collections import defaultdict
from pathlib import Path


def _learning_view(root, unit, *, latest_only, owner=None):
    fields = {key: unit[key] for key in ("intent", "source_learning") if unit.get(key)}
    entries = unit.get("learning") or []
    if entries:
        from loop_learning import learning_evidence_issue

        fields["learning_count"] = len(entries)
        if latest_only:
            # Keep the latest choice and the latest opportunity, in recorded order.
            last = {entry["kind"]: index for index, entry in enumerate(entries)}
            entries = [entries[index] for index in sorted(last.values())]
        projected = []
        for entry in entries:
            issue = learning_evidence_issue(root, entry)
            detail = dict(entry, evidence_issue=issue)
            if entry.get("candidate"):
                from loop_revalidation import decision_view
                detail["revalidation"] = decision_view(root, unit, owner or unit, entry)
            projected.append(detail)
        fields["learning"] = projected
    return fields


def loop_state(root, *, latest_learning_only=False):
    """Read and validate one committed snapshot for every unit in this project."""
    from checks.flow_unit_runtime_v2 import missing_runtime_issue, validate_native_loop_payload

    root = Path(root)
    path = root / ".governance" / "flow-unit-runtime.json"
    summary = {"total_units": 0, "active_loops": 0,
               "by_tier": dict.fromkeys(("setup", "inner", "middle", "outer"), 0)}
    view = {"state": "empty", "runtime_found": False, "no_global_stage": True,
            "units": [], "summary": summary}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if issue := missing_runtime_issue(path):
            return dict(view, state="invalid", message=issue, issues=[issue])
        view["message"] = "No work units recorded. Start a unit with loop start."
        return view
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        return dict(view, state="invalid", runtime_found=True, message=f"Cannot read {path.name}: {exc}")

    view["runtime_found"] = True
    try:
        issues = validate_native_loop_payload(state, display=path.name)
    except (TypeError, ValueError, KeyError, RecursionError) as exc:
        issues = [f"Invalid loop runtime: {exc}"]
    if issues:
        return dict(view, state="invalid", message=issues[0], issues=issues)

    units = state["flow_units"]
    from loop_alignment import root_unit, scope_successors, acceptance_successors, view as contract_view
    from loop_revalidation import exit_issue
    by_id = {unit["flow_unit_id"]: unit for unit in units}
    successors = scope_successors(units)
    historical = acceptance_successors(units)
    issues_by_id = {}
    receipts = {}
    ledger = None
    for unit in units:
        history = unit.get("gate_history") or []
        if not history:
            continue
        key, latest = unit["flow_unit_id"], history[-1]
        receipts[key] = latest
        from checks.loop_receipts import verify_attempt
        try:
            if ledger is None and latest["evidence_ref"].startswith("review-"):
                from authority_ledger import LedgerWriter
                ledger = LedgerWriter(path.parent)
            verify_attempt(root, unit, latest, len(history) - 1, ledger=ledger)
            if unit["runtime_status"] == "completed" and key not in historical:
                if issue := exit_issue(root, unit, root_unit(unit, by_id)):
                    issues_by_id[key] = f"{key}: {issue}. Reopen the stale exit with loop recheck --unit {key}."
        except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
            issues_by_id[key] = f"{key}: restore or verify {latest['evidence_ref']} ({exc})"
    if issues_by_id:
        # An exit consumes the exit receipts of its dependencies and children.
        # Propagate missing trust through those links without rereading receipts.
        consumers = defaultdict(set)
        completed = {u["flow_unit_id"] for u in units if u["runtime_status"] == "completed"}
        for unit in units:
            key, parent = unit["flow_unit_id"], unit.get("parent_unit_id")
            if parent in completed:
                consumers[key].add(parent)
            if key in completed:
                for dependency in unit["dependencies"]:
                    if dependency != unit.get("continues_contract"):
                        consumers[dependency].add(key)
        pending = [(key, key) for key in issues_by_id]
        while pending:
            key, original = pending.pop()
            for dependent in consumers[key]:
                if dependent not in issues_by_id:
                    issues_by_id[dependent] = f"{dependent}: prerequisite evidence is unverified. {issues_by_id[original]}"
                    pending.append((dependent, original))
    unfinished = {unit["flow_unit_id"] for unit in units if unit["runtime_status"] != "completed"} | set(issues_by_id)
    children = defaultdict(list)
    selected = {(unit.get("previous_unit_id"), unit["source_learning"])
                for unit in units if unit.get("source_learning")}
    for unit in units:
        if unit.get("parent_unit_id") and unit["flow_unit_id"] in unfinished:
            children[unit["parent_unit_id"]].append(unit["flow_unit_id"])

    for unit in units:
        loop = unit["loop_state"]
        gate = unit["gate_state"]
        tier = loop["active_loop_tier"]
        active = loop["active_loop"]
        if active:
            summary["active_loops"] += 1
            summary["by_tier"][tier] += 1
        waiting = [key for key in unit["dependencies"] if key in unfinished and not (
            key == unit.get("continues_contract") and by_id[key]["runtime_status"] == "completed")]
        open_children = children[unit["flow_unit_id"]]
        returns = loop.get("return_to") or []
        unit_id = unit["flow_unit_id"]
        previous = unit.get("previous_unit_id")
        issue = issues_by_id.get(unit_id)
        receipt = receipts.get(unit_id)
        return_to = returns[-1] if returns else None
        owner = root_unit(unit, by_id)
        learning = _learning_view(root, unit, latest_only=latest_learning_only, owner=owner)
        if contract := contract_view(owner):
            learning["root_contract"] = contract
            if unit.get("criterion_scope"):
                learning["criterion_scope"] = unit["criterion_scope"]
        else:
            learning["root_provenance"] = "legacy: original root contract not recorded; historical goal and receipts retained"
        next_action = issue or _unit_action(unit, waiting, open_children, return_to)
        if not issue and unit_id in successors:
            learning["scope_successors"] = successors[unit_id]
            next_action = "Historical scoped exit. Continue with " + ", ".join(successors[unit_id]) + "."
        elif not issue and not waiting and not open_children:
            from loop_revalidation import recovery
            gaps, next_action = recovery(root, unit, owner, learning, next_action)
            if gaps:
                learning["criterion_gaps"] = gaps
        if not issue and unit["runtime_status"] == "completed":
            opportunity = next((entry for entry in reversed(learning.get("learning", []))
                                if entry["kind"] == "opportunity"), None)
            if (opportunity and not opportunity["evidence_issue"]
                    and (unit_id, opportunity["id"]) not in selected):
                next_action += f" Optional next step: review opportunity {opportunity['id']}."
        view["units"].append({
            "flow_unit_id": unit_id, "title": unit.get("title") or unit["goal"],
            "task_id": unit.get("task_id"), "unit_type": unit.get("unit_type", "work-unit"),
            "previous_unit_id": previous, "previous_review": receipts.get(previous) if previous not in issues_by_id else None,
            "release_version": unit.get("release_version"),
            "delivery_goal": unit.get("delivery_goal"),
            "entry_tier": unit.get("entry_tier"), "has_acceptance_command": bool(unit.get("acceptance_command")),
            "parent_unit_id": unit.get("parent_unit_id"), "goal": unit.get("goal"),
            "acceptance": unit.get("acceptance"), "runtime_status": "unverified" if issue else unit["runtime_status"],
            "active_loop": active, "active_loop_tier": tier,
            "loop_count": loop["loop_count"], "agent_phase": loop["agent_phase"],
            "fuse_tripped": loop["fuse"]["tripped"], "gate_id": gate["gate_id"],
            "gate_status": "unverified" if issue else gate["status"], "last_gate_result": loop["last_gate_result"],
            "last_review": receipt, "return_to": return_to,
            "evidence_refs": gate["evidence_refs"], "blockers": unit["blockers"],
            "dependencies": unit["dependencies"], "waiting_on": waiting,
            "open_children": open_children,
            "next_action": next_action,
            **learning,
            **({"state": "invalid", "recorded_runtime_status": unit["runtime_status"],
                "recorded_gate_status": gate["status"]} if issue else {}),
        })
    summary["total_units"] = len(view["units"])
    view["state"] = "ready" if view["units"] else "empty"
    if issues_by_id:
        view.update(state="invalid", issues=list(issues_by_id.values()), message="One or more work units have unverifiable evidence.")
    if not view["units"]:
        view["message"] = "No work units recorded. Start a unit with loop start."
    return view


def _unit_action(unit, waiting, open_children, return_to):
    loop, gate = unit["loop_state"], unit["gate_state"]
    if loop["fuse"]["tripped"] or gate["status"] == "escalated":
        return "Resolve the escalation before continuing this unit."
    if unit["blockers"] or unit["runtime_status"] == "blocked" or gate["status"] == "blocked":
        return "Resolve the blocker and record the evidence."
    if unit["runtime_status"] == "withdrawn":
        return "Withdrawn."
    if unit["runtime_status"] == "completed":
        return "Work unit complete."
    if waiting:
        return "Resume after verifying dependencies: " + ", ".join(waiting) + "."
    if open_children:
        from loop_engine import gate_requires_children
        if gate_requires_children(gate["gate_id"]):
            return f"Wait for child work before {gate['gate_id']}: " + ", ".join(open_children) + "."
    if not loop["active_loop"]:
        if unit.get("contract_revisions"):
            return "Recheck the affected root criteria against the recorded revision and original sample."
        return "Activate the unit when its prerequisites are met."
    if unit.get("delivery_goal") and gate["gate_id"] == "G9":
        return "Verify the delivered product on the user’s path. Have the host check its independent acceptance receipt and open work."
    if unit.get("release_version") and gate["gate_id"] == "G9":
        return f"Obtain independent release review and authorization for {unit['release_version']}."
    if unit.get("acceptance_command"):
        return f"Run loop verify --unit {unit['flow_unit_id']} against its acceptance command."
    actions = {
        "plan": "Plan this iteration against the acceptance criteria.",
        "act": "Carry out the planned change.",
        "observe": "Check the result and collect acceptance evidence.",
        "reflect": "Review the evidence against this unit’s gate.",
    }
    if (gate["status"] == "failed" or return_to) and loop["agent_phase"] == "plan":
        return "Rework the recorded finding and repeat its acceptance check."
    return actions[loop["agent_phase"]]


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


def project_name(plan, config, root):
    title = re.search(r"^#\s+(.+?)\s*$", plan, re.MULTILINE)
    for name in (config.get("项目名称"), title and title.group(1)):
        if name and not re.fullmatch(r"<[^>]+>", name):
            return name
    return Path(root).name


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
