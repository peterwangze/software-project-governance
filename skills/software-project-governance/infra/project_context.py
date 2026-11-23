"""Read host work units and evidence from project files and Git."""

import re
from pathlib import Path
import subprocess

from governance_readers import governance_table_cells


def _empty_governance_context(root):
    checked = [
        ".governance/plan-tracker.md",
        ".governance/session-snapshot.md",
        ".governance/evidence-log.md",
        ".governance/risk-log.md",
    ]
    if _is_context_git_repo_root(root):
        checked.extend([
            "git status --short",
            "git log --oneline -5",
        ])
    present = [
        path for path in checked
        if path.startswith("git ") or (root / path).is_file()
    ]
    source = (
        "checked " + ", ".join(present)
        if present
        else "checked governance fact sources; no governance files found"
    )
    return {
        "status": "NOT_FOUND",
        "detected_item": "not found",
        "source_facts": [f"{source}; no unfinished user work facts found"],
        "blocker_state": "not found",
        "next_action": "do not invent work; ask only at an interaction boundary or start from recorded plan",
        "auto_continue": False,
        "interrupt_boundary": "AskUserQuestion required before creating new work from assumptions",
        "_items": [],
    }


def discover_governance_context(root, skip_evidence_log=False):
    """Return the same durable work units used by status and bootstrap."""
    from governance_readers import loop_state
    return loop_state(root)


def _parse_plan_context_tasks(root, *, is_incomplete, normalize_priority):
    plan_path = root / ".governance/plan-tracker.md"
    if not plan_path.is_file():
        return []
    tasks = []
    content = plan_path.read_text(encoding="utf-8")
    in_active_section = False
    in_roadmap = False
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## 当前活跃事项"):
            in_active_section = True
            in_roadmap = False
            continue
        if stripped.startswith("### 版本路线图"):
            in_roadmap = True
            in_active_section = False
            continue
        if in_active_section and stripped.startswith("### 最近完成"):
            in_active_section = False
        if in_roadmap and stripped.startswith("### ") and not stripped.startswith("### 版本路线图"):
            in_roadmap = False

        if in_active_section and stripped.startswith("|") and "---" not in stripped:
            cells = governance_table_cells(stripped)
            if not cells or cells[0] in {"优先级", "任务ID"}:
                continue
            task_idx = next(
                (idx for idx, cell in enumerate(cells)
                 if re.match(r"^(?:\*\*)?[A-Z]+-\d+(?:\*\*)?$", cell.strip())),
                None,
            )
            if task_idx is None:
                continue
            status = cells[-1].strip() if cells else ""
            if not is_incomplete(status):
                continue
            task_id = cells[task_idx].strip().strip("*")
            priority = next((normalize_priority(cell) for cell in cells if normalize_priority(cell)), "")
            title = cells[task_idx + 1].strip() if task_idx + 1 < len(cells) else task_id
            tasks.append(_context_task(
                task_id,
                title,
                status,
                ".governance/plan-tracker.md ## 当前活跃事项",
                stripped,
                priority=priority,
            ))
            continue

        if in_roadmap and stripped.startswith("|") and "---" not in stripped:
            cells = governance_table_cells(stripped)
            if len(cells) < 5 or cells[0] in {"版本", "Version"}:
                continue
            row_status = cells[1]
            if not is_incomplete(row_status):
                continue
            task_cell = cells[4]
            for match in re.finditer(r"\b([A-Z]+-\d+)(?:\([^)]*\))?(✅)?", task_cell):
                if match.group(2):
                    continue
                task_id = match.group(1)
                tasks.append(_context_task(
                    task_id,
                    f"{task_id} from active version {cells[0]} roadmap",
                    row_status,
                    ".governance/plan-tracker.md ### 版本路线图",
                    stripped,
                    priority="",
                ))
    return tasks


def _parse_snapshot_context_tasks(root, *, is_incomplete, normalize_priority, sections):
    snapshot_path = root / ".governance/session-snapshot.md"
    if not snapshot_path.is_file():
        return []
    tasks = []
    content = snapshot_path.read_text(encoding="utf-8")
    current_section = ""
    header = []
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            current_section = stripped.lstrip("#").strip()
            header = []
            continue
        if current_section not in sections:
            continue
        if not stripped or stripped.lower() == "none":
            continue
        if stripped.startswith("|") and "---" not in stripped:
            cells = governance_table_cells(stripped)
            if not cells:
                continue
            if any("任务" in cell or "Task" in cell or "优先级" in cell for cell in cells):
                header = cells
                continue
            task_idx = next(
                (idx for idx, cell in enumerate(cells) if re.search(r"\b[A-Z]+-\d+\b", cell)),
                None,
            )
            if task_idx is None:
                continue
            task_id = re.search(r"\b[A-Z]+-\d+\b", cells[task_idx]).group(0)
            status = "carry-over"
            if header:
                status_idx = next(
                    (idx for idx, cell in enumerate(header)
                     if "状态" in cell or "status" in cell.lower() or "阻塞" in cell),
                    None,
                )
                if status_idx is not None and status_idx < len(cells):
                    status = cells[status_idx]
            if not is_incomplete(status):
                continue
            priority = next((normalize_priority(cell) for cell in cells if normalize_priority(cell)), "")
            title = cells[task_idx + 1].strip() if task_idx + 1 < len(cells) else task_id
            tasks.append(_context_task(
                task_id,
                title,
                status,
                f".governance/session-snapshot.md ## {current_section}",
                stripped,
                priority=priority,
            ))
            continue
        task_match = re.search(r"\b([A-Z]+-\d+)\b", stripped)
        if task_match:
            task_id = task_match.group(1)
            tasks.append(_context_task(
                task_id,
                _extract_task_title_from_line(stripped, task_id),
                "carry-over",
                f".governance/session-snapshot.md ## {current_section}",
                stripped,
                priority=normalize_priority(stripped),
            ))
    return tasks


def _is_context_product_file(path, *, entry_files, product_patterns):
    normalized = (path or "").strip().replace("\\", "/")
    if not normalized or normalized.startswith(".governance/"):
        return False
    if "/" not in normalized and normalized in entry_files:
        return True
    return any(normalized == pattern.rstrip("/") or normalized.startswith(pattern) for pattern in product_patterns)


def _parse_git_status_context_tasks(root, *, is_product_file):
    stdout = _run_context_git(root, ["status", "--short", "--untracked-files=all"])
    if stdout is None:
        return []
    product_lines = []
    for raw_line in stdout.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        path_part = line[3:] if len(line) > 3 else line
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1]
        path_part = path_part.strip().strip('"').replace("\\", "/")
        if is_product_file(path_part):
            product_lines.append(line.strip())
    if not product_lines:
        return []
    raw_summary = "; ".join(product_lines[:5])
    return [_context_task(
        "GIT-WORKTREE",
        f"uncommitted product file changes ({len(product_lines)} file(s))",
        "uncommitted product work",
        "git status --short",
        raw_summary,
        kind="git",
    )]


def check_governance_context(root, *, discover, display_path, read_text):
    """Validate the recorded state and the route that resumes it."""
    view = discover(root)
    failures = [view["message"]] if view["state"] == "invalid" else []
    scenario = root / "commands/governance/scenario-f.md"
    status = root / "commands/governance-status.md"
    if not scenario.is_file() or not any(
        (scenario.parent / target).resolve() == status.resolve()
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", read_text(scenario))
    ):
        failures.append(f"{display_path(scenario, root)}: missing reference to the status command")
    content = read_text(status) if status.is_file() else ""
    for command in ("governance-bootstrap --format json", "loop status --unit"):
        if command not in content:
            failures.append(f"{display_path(status, root)}: missing work-unit reader {command}")
    return failures


def _context_task(item_id, title, status, source, raw_line, priority="", kind="task"):
    title = re.sub(r"\s+", " ", (title or "").strip())
    raw_line = re.sub(r"\s+", " ", (raw_line or "").strip())
    return {
        "task_id": item_id,
        "priority": priority,
        "title": title,
        "status": status or "unfinished",
        "source": source,
        "raw_line": raw_line,
        "kind": kind,
    }


def _extract_task_title_from_line(line, task_id):
    cleaned = re.sub(r"^[\s\-\d.、]+", "", line or "")
    cleaned = cleaned.replace("**", "").replace("`", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if task_id in cleaned:
        return cleaned
    return task_id


def _context_git_toplevel(root):
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _is_context_git_repo_root(root):
    toplevel = _context_git_toplevel(root)
    if not toplevel:
        return False
    try:
        return Path(toplevel).resolve() == Path(root).resolve()
    except OSError:
        return False


def _run_context_git(root, args):
    if not _is_context_git_repo_root(root):
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(root)] + args,
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _parse_recent_commit_context_facts(root, limit=5):
    stdout = _run_context_git(root, ["log", "--oneline", f"-{limit}"])
    if stdout is None:
        return []
    facts = []
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped:
            facts.append(stripped)
    return facts


def _dedupe_context_items(items):
    seen = set()
    deduped = []
    for item in items:
        key = (item.get("kind"), item.get("task_id"), item.get("source"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
