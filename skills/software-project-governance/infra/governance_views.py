"""Project delivery evidence, the local first-run example and lifecycle stage assets."""

import json
from pathlib import Path
import re
import sys

from governance_readers import governance_table_cells


def parse_session_snapshot_carry_over_tasks(snapshot_path, *, is_incomplete, normalize_priority):
    """Parse carry-over tasks from session-snapshot when active plan rows are absent."""
    if not snapshot_path.is_file():
        return []

    content = snapshot_path.read_text(encoding="utf-8")
    tasks = []
    in_carry_section = False
    header = []
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            section_title = stripped.lstrip("#").strip()
            in_carry_section = section_title in {
                "遗留任务",
                "Carry-over tasks",
                "Carry over tasks",
                "Unfinished / deferred",
                "未完成 / 已延期",
            }
            header = []
            continue
        if not in_carry_section:
            continue
        if stripped.startswith("|") and "---" not in stripped:
            cells = governance_table_cells(stripped)
            if not cells:
                continue
            if any("任务" in cell or "Task" in cell for cell in cells):
                header = cells
                continue
            task_idx = next(
                (idx for idx, cell in enumerate(cells)
                 if re.search(r"\b[A-Z]+-\d+\b", cell.strip("* "))),
                None,
            )
            if task_idx is None:
                continue
            task_id = re.search(r"\b[A-Z]+-\d+\b", cells[task_idx]).group(0)
            status = ""
            if header:
                status_idx = next(
                    (idx for idx, cell in enumerate(header)
                     if "状态" in cell or "status" in cell.lower()),
                    None,
                )
                if status_idx is not None and status_idx < len(cells):
                    status = cells[status_idx]
            elif len(cells) > task_idx + 2:
                status = cells[-1]
            if not is_incomplete(status):
                continue
            priority = ""
            for cell in cells:
                normalized = normalize_priority(cell)
                if normalized:
                    priority = normalized
                    break
            title = cells[task_idx + 1].strip() if task_idx + 1 < len(cells) else ""
            tasks.append({
                "task_id": task_id,
                "priority": priority,
                "title": title,
                "dependency": "",
                "target_version": "",
                "closure_path": "session-snapshot.md",
                "status": status or "carry-over",
                "raw_line": stripped,
            })
            continue
        if stripped.startswith("-"):
            task_match = re.search(r"\b([A-Z]+-\d+)\b", stripped)
            if task_match and is_incomplete(stripped):
                tasks.append({
                    "task_id": task_match.group(1),
                    "priority": normalize_priority(stripped) or "",
                    "title": stripped.lstrip("- ").strip(),
                    "dependency": "",
                    "target_version": "",
                    "closure_path": "session-snapshot.md",
                    "status": "carry-over",
                    "raw_line": stripped,
                })
    return tasks


def build_delivery_trust_snapshot(project_root, unit_id=None):
    """Project only the actual work units and evidence present in the requested host."""
    from governance_readers import loop_state

    view = loop_state(Path(project_root))
    if view["state"] == "invalid":
        raise ValueError(view["message"])
    units = [unit for unit in view["units"] if unit_id is None or unit["flow_unit_id"] == unit_id]
    if unit_id and not units:
        raise ValueError(f"Unknown work unit: {unit_id}")
    return {
        "Work units": [{key: unit.get(key) for key in
                        ("flow_unit_id", "parent_unit_id", "goal", "acceptance", "active_loop_tier",
                         "gate_id", "gate_status", "evidence_refs", "blockers", "next_action")}
                       for unit in units],
        "State": view["state"],
        "Next action": units[0]["next_action"] if len(units) == 1 else (
            "Resume the relevant unit by its ID." if units else "Record the first goal and its acceptance condition."),
    }


def assert_first_run_demo_snapshot(snapshot, rendered_text=None, *, required_fields, required_markers, render):
    """Return missing field/marker diagnostics for the local first-run demo."""
    rendered_text = rendered_text if rendered_text is not None else render(snapshot)
    missing_fields = [field for field in required_fields if not snapshot.get(field)]
    missing_markers = [marker for marker in required_markers if marker not in rendered_text]
    return missing_fields + missing_markers


def parse_gate_detail(gate_id, *, gates_path):
    """Parse a specific Gate's details from stage-gates.md."""
    gate_id = gate_id.upper()
    if not gate_id.startswith("G"):
        gate_id = "G" + gate_id

    content = gates_path.read_text(encoding="utf-8")

    pattern = re.compile(
        rf"## ({re.escape(gate_id)} .+?)\n\n(.*?)(?=\n## G\d|\n## Gate 执行原则|\Z)",
        re.DOTALL,
    )
    m = pattern.search(content)
    if not m:
        return None

    title = m.group(1).strip()
    body = m.group(2).strip()

    detail = {"title": title, "raw": body}

    # Extract transition
    tm = re.search(r"\*\*阶段转换\*\*[：:]\s*(.+)", body)
    detail["transition"] = tm.group(1).strip() if tm else ""

    # Extract required materials
    mm = re.search(r"\*\*必审材料\*\*[：:]\s*(.+)", body)
    detail["materials"] = mm.group(1).strip() if mm else ""

    # Extract check items
    checks = re.findall(r"^\s+\d+\.\s+(.+)$", body, re.MULTILINE)
    detail["checks"] = checks

    # Extract pass criteria
    pm = re.search(r"\*\*通过标准\*\*[：:]\s*(.+)", body)
    detail["pass_criteria"] = pm.group(1).strip() if pm else ""

    # Extract auto-judgment criteria
    auto_checks = re.findall(r"^\s+- 检查项\d+[：:]\s*(.+)$", body, re.MULTILINE)
    detail["auto_criteria"] = auto_checks

    # Extract conditional pass info
    cm = re.search(r"\*\*有条件通过\*\*[：:]\s*(.+?)(?:\n\n|\n- \*\*|$)", body, re.DOTALL)
    detail["conditional"] = cm.group(1).strip() if cm else ""

    return detail


def normalize_stage_name(stage_name, *, aliases):
    """Normalize CLI stage names to lifecycle stage identifiers."""
    normalized = stage_name.strip().lower()
    if normalized.startswith("stage-"):
        normalized = normalized[len("stage-"):]
    return aliases.get(normalized, normalized)


def stage_skill_dir_name(stage_name, *, directories, normalize):
    """Return the canonical skill directory name for a lifecycle stage."""
    stage = normalize(stage_name)
    return directories.get(stage, f"stage-{stage}")


def stage_skill_path(stage_name, *, stages_root, directory_name):
    """Return the canonical stage workflow SKILL.md path."""
    return stages_root / directory_name(stage_name) / "SKILL.md"


def _stage_name_from_skill_dir(dirname, *, directories, normalize):
    """Map a stage skill directory back to the lifecycle stage identifier."""
    for stage, mapped_dir in directories.items():
        if dirname == mapped_dir:
            return stage
    if dirname.startswith("stage-"):
        return normalize(dirname[len("stage-"):])
    return dirname


def list_available_stages(*, stage_order, stages_root, skill_path, stage_name):
    """List all available lifecycle stages backed by stage SKILL.md files."""
    if not stages_root.is_dir():
        return []
    stages = {
        stage for stage in stage_order
        if skill_path(stage).is_file()
    }
    for skill_md in stages_root.glob("stage-*/SKILL.md"):
        stages.add(stage_name(skill_md.parent.name))
    return sorted(
        stages,
        key=lambda x: stage_order.index(x) if x in stage_order else 99,
    )


def render_delivery_trust_snapshot(snapshot):
    lines = ["Delivery Trust Snapshot", f"State: {snapshot.get('State', '')}", "Work units:"]
    for unit in snapshot.get("Work units", []):
        parent = f" (child of {unit['parent_unit_id']})" if unit["parent_unit_id"] else ""
        lines.extend([
            f"- {unit['flow_unit_id']}{parent}: {unit['goal']}",
            f"  Acceptance: {unit['acceptance']}",
            f"  {unit['active_loop_tier']} loop | {unit['gate_id']} {unit['gate_status']} | {unit['next_action']}",
        ])
        if unit["evidence_refs"]:
            lines.append("  Evidence: " + ", ".join(unit["evidence_refs"]))
        if unit["blockers"]:
            lines.append("  Blockers: " + ", ".join(unit["blockers"]))
    lines.append("Next action: " + snapshot.get("Next action", ""))
    if "Verification" in snapshot:
        lines.append("Verification: " + snapshot["Verification"])
    return "\n".join(lines)


def build_first_run_demo_snapshot(build_snapshot=build_delivery_trust_snapshot):
    """Exercise a disposable delivery and a bounded, locally verified child."""
    import tempfile
    import loop_workflow

    with tempfile.TemporaryDirectory() as demo:
        root = Path(demo)
        (root / ".governance").mkdir()
        loop_workflow.start(root, unit_id="demo-delivery", goal="Deliver a ledger export",
                            acceptance="Exported amounts match the ledger", tier="middle", gate=None)
        (root / "ledger.csv").write_text("amount\n3\n4\n", encoding="utf-8")
        check = [sys.executable, "-c", "import csv; from pathlib import Path; "
                 "total=sum(int(r['amount']) for r in csv.DictReader(Path('ledger.csv').read_text().splitlines())); "
                 "print('totals match' if total == 7 else 'mismatch')"]
        loop_workflow.start(root, unit_id="demo-export", parent="demo-delivery", goal="Check the exported amounts",
                            acceptance="CSV rows total seven", tier="inner", gate=None,
                            check_command=check, expect_output="totals match")
        outcome = loop_workflow.verify_command(root, "demo-export")
        if outcome["decision"] != "exit":
            raise ValueError(f"demo-export failed its declared acceptance: {outcome['decision']}")
        snapshot = build_snapshot(root)
        child = next(unit for unit in snapshot["Work units"] if unit["flow_unit_id"] == "demo-export")
        receipt = json.loads((root / ".governance" / child["evidence_refs"][-1]).read_bytes())
        snapshot["Verification"] = "local/demo-only: " + receipt["stdout"].strip()
        return snapshot
