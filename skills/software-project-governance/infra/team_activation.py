"""Check review role skills and team activation against project governance records."""

from pathlib import Path
import re


LOOP_ROLE_SKILL_CONTRACTS = (
    "requirement-review", "design-review", "tech-review", "code-review",
    "test-review", "release-review", "retro-review",
)


def check_loop_role_skill_consistency(
        root, *, package_root, lifecycle_registry_gates, loop_role_skill_contracts, display_path,
        markdown_section_by_prefix, read_text_normalized,
):
    """Each reviewer consumes its named local gates and the shared decision contract."""
    root = Path(root) if root is not None else package_root
    mapping_path = root / "skills/software-project-governance/references/loop-role-mapping.md"
    issues = []
    if not mapping_path.is_file():
        return {"passed": False, "skills_checked": 0,
                "issues": [f"missing shared loop-role mapping: {display_path(mapping_path, root)}"]}
    mapping = read_text_normalized(mapping_path)
    for token in ("`APPROVED`", "`APPROVED_WITH_NOTES`", "unresolved_blockers=0", "`NEEDS_CHANGE`",
                  "`BLOCKED`", "review-record", "loop status --unit"):
        if token not in mapping:
            issues.append(f"shared review contract missing {token}")
    for name in loop_role_skill_contracts:
        rows = re.findall(rf"^\|\s*`{re.escape(name)}`\s*\|([^\n]+)", mapping, re.M)
        if len(rows) != 1:
            issues.append(f"shared review contract must map {name} exactly once")
        expected = set(re.findall(r"\bG\d+\b", rows[0])) if len(rows) == 1 else set()
        if not expected or not expected <= set(lifecycle_registry_gates):
            issues.append(f"shared review contract has missing or unknown gates for {name}")
        path = root / "skills" / name / "SKILL.md"
        if not path.is_file():
            issues.append(f"missing review SKILL: {display_path(path, root)}")
            continue
        section = markdown_section_by_prefix(read_text_normalized(path), "## 循环角色")
        refs = re.findall(r"\[[^\]]+\]\(([^)]+)\)", section)
        if not any((path.parent / ref).resolve() == mapping_path.resolve() for ref in refs):
            issues.append(f"{name}: no resolvable shared loop-role mapping reference")
        actual = set(re.findall(r"\bG\d+\b", section))
        if actual != expected:
            issues.append(f"{name}: consumes {sorted(actual)}, expected {sorted(expected)} from its review contract")
    return {
        "passed": not issues,
        "skills_checked": len(loop_role_skill_contracts),
        "issues": issues,
    }


ACTIVE_AGENT_ROLES = [
    "Analyst",
    "Architect",
    "Developer",
    "Governance Developer",
    "QA",
    "Code Reviewer",
    "Design Reviewer",
    "Requirement Reviewer",
    "Test Reviewer",
    "Release Reviewer",
    "Retro Reviewer",
    "DevOps",
    "Release",
    "Maintenance",
]


NAMED_REVIEWER_ROLES = [
    "Code Reviewer",
    "Design Reviewer",
    "Requirement Reviewer",
    "Test Reviewer",
    "Release Reviewer",
    "Retro Reviewer",
]


def check_agent_activation(*, evidence_path, plan_path, split_governance_table_row, expand_task_ids):
    """SYSGAP-036: Check 20 — Analyst/Architect activation for P0 cross-layer tasks.

    For P0 tasks involving >= 2 architecture layers of product code change,
    verify that Analyst/Architect agents were activated for impact analysis.

    Detection:
    - P0 tasks: parsed from plan-tracker tracking tables (priority column index 11)
    - Product code: evidence file locations in skills/, agents/, infra/, etc.
    - Cross-layer: >= 2 distinct top-level directories in evidence locations
    - Analyst involvement: evidence author contains "Analyst" or description
      contains "Analyst:" marker

    Returns dict with total_p0_cross_layer, analyst_activated, analyst_bypassed, pass.
    """
    PRODUCT_CODE_PATTERNS = [
        "skills/", "agents/", "infra/", "commands/",
        "adapters/", ".claude-plugin/", ".codex-plugin/", ".agents/",
        "project/",
    ]
    ARCH_LAYER_MAP = {
        "skills/": "skills",
        "commands/": "commands",
        "agents/": "agents",
        "infra/": "infra",
        "adapters/": "adapters",
        "project/": "project",
        ".claude-plugin/": "claude-plugin",
        ".codex-plugin/": "codex-plugin",
        ".agents/": "agents-plugin",
    }

    result = {
        "total_p0_cross_layer": 0,
        "analyst_activated": 0,
        "analyst_bypassed": 0,
        "bypassed_tasks": [],
        "pass": True,
    }

    # Parse P0 completed tasks from plan-tracker
    content = plan_path.read_text(encoding="utf-8")
    p0_tasks = {}  # task_id -> True

    for line in content.split("\n"):
        line_stripped = line.strip()
        if not line_stripped.startswith("| ") or "---" in line_stripped:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 11:
            continue
        task_id_match = re.match(r"([A-Z]+-\d+)", parts[1])
        if not task_id_match:
            continue
        task_id = task_id_match.group(1)
        # Column indices: real format has 20 cols (priority at [11]), test format has 10 (priority at [3])
        status = parts[10] if len(parts) > 10 else ""
        if len(parts) >= 13:
            priority = parts[11] if len(parts) > 11 else ""  # full 20-column format
        elif len(parts) >= 5:
            priority = parts[3] if len(parts) > 3 else ""    # simplified 10-column test format
        else:
            priority = ""
        if priority == "P0" and status == "已完成":
            p0_tasks[task_id] = True

    if not p0_tasks:
        return result

    # Read evidence-log
    if not evidence_path.is_file():
        return result
    evidence_content = evidence_path.read_text(encoding="utf-8")

    # Build map: task_id -> [(evd_id, file_location, entry_method, description, evd_type)]
    task_entries = {}
    for line in evidence_content.split("\n"):
        line = line.strip()
        if not line.startswith("| EVD-"):
            continue
        # FIX-372: split via _split_governance_table_row (not raw split) so
        # pipes inside JSON/code-span cells stay intact; the len(parts) < 9
        # guard keeps the same row-shape reachability (parts[0..8]).
        parts = [p.strip() for p in split_governance_table_row(line)]
        if len(parts) < 9:
            continue
        evd_id = parts[1]
        raw_ids = parts[2]
        # FIX-372 (review-FIX-368-CODE-R0 P1-1): LIVE evidence-log column
        # layout is parts[3]=type, parts[4]=description, parts[5]=fact basis,
        # parts[6]=file location (10 data cells -> 12 split parts incl. the
        # leading/trailing empties). The pre-fix parts[4]/parts[5] read was a
        # +1 offset: evd_type read the description column, so
        # evd_type == "影响分析" was always false and the impact scan swept
        # the fact-basis column — Check 20 fail-open (analyst_bypassed
        # systematically under-counted).
        evd_type = parts[3] if len(parts) > 3 else ""
        description = parts[4] if len(parts) > 4 else ""
        file_location = parts[6] if len(parts) > 6 else ""
        # FIX-372 (P3-1): parts[7] is the 录入方式 column in LIVE rows
        # (recorder identity, e.g. "Coordinator 机写"); legacy rows kept the
        # author there — the column position did not drift, only its label.
        # Either way the cell carries the recorder identity, so the
        # Analyst/Architect substring check stays on parts[7]; renamed from
        # `author` to `entry_method` to match the LIVE column semantics.
        entry_method = parts[7] if len(parts) > 7 else ""

        for tid in expand_task_ids(raw_ids) if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids) else []:
            task_entries.setdefault(tid, []).append(
                (evd_id, file_location, entry_method, description, evd_type)
            )

    for task_id in sorted(p0_tasks):
        entries = task_entries.get(task_id, [])
        if not entries:
            continue

        # Check product code involvement
        is_product_code = any(
            any(pat in file_loc for pat in PRODUCT_CODE_PATTERNS)
            for _, file_loc, _, _, _ in entries
        )
        if not is_product_code:
            continue

        # Count architecture layers
        all_locs = " ".join(file_loc for _, file_loc, _, _, _ in entries)
        layers = set()
        for prefix, layer_name in ARCH_LAYER_MAP.items():
            if prefix in all_locs:
                layers.add(layer_name)
        if len(layers) < 2:
            # Not cross-layer — skip (only single layer change)
            continue

        result["total_p0_cross_layer"] += 1

        # Check for Analyst/Architect involvement
        # Look for impact analysis evidence entries covering this task
        has_impact_analysis = False
        has_analyst_involvement = False

        for _, _, entry_method, description, evd_type in entries:
            if evd_type == "影响分析" or "影响分析" in description:
                has_impact_analysis = True
                if "Analyst" in entry_method or "Architect" in entry_method:
                    has_analyst_involvement = True
                if "Analyst:" in description or "Architect:" in description:
                    has_analyst_involvement = True

        # Also check if any evidence entry for ANY task has impact analysis
        # that references this task (e.g., separate Analyst analysis entry)
        for line in evidence_content.split("\n"):
            line = line.strip()
            if not line.startswith("| EVD-"):
                continue
            # FIX-372: same LIVE layout alignment as the main scan above —
            # parts[3]=type gate, parts[4]=description, parts[7]=entry method
            # (P1-1/P3-1). Pre-fix the parts[4] != "影响分析" gate was near
            # always true, leaving this cross-reference path effectively dead.
            parts = [p.strip() for p in split_governance_table_row(line)]
            if len(parts) < 9:
                continue
            evd_type = parts[3] if len(parts) > 3 else ""
            if evd_type != "影响分析":
                continue
            raw_ids = parts[2]
            description = parts[4] if len(parts) > 4 else ""
            entry_method = parts[7] if len(parts) > 7 else ""
            covered = expand_task_ids(raw_ids) if raw_ids and re.search(r"[A-Z]+-\d+", raw_ids) else set()
            if task_id in covered:
                has_impact_analysis = True
                if "Analyst" in entry_method or "Architect" in entry_method:
                    has_analyst_involvement = True
                if "Analyst:" in description or "Architect:" in description:
                    has_analyst_involvement = True

        if has_impact_analysis and not has_analyst_involvement:
            result["analyst_bypassed"] += 1
            result["bypassed_tasks"].append(task_id)
        elif has_impact_analysis and has_analyst_involvement:
            result["analyst_activated"] += 1
        # If no impact analysis at all, the task was completed without any
        # analysis — not counted as "bypassed" (analysis step entirely skipped)

    result["pass"] = result["analyst_bypassed"] == 0
    return result


def check_profile_consistency(*, plan_path):
    """Validate the declared profile and the review behind any closed work unit."""
    from governance_readers import loop_state, project_config

    result = {"profile": None, "issues": [], "pass": True}
    if not plan_path.is_file():
        result["issues"].append("plan-tracker.md not found")
    else:
        config = project_config(plan_path.read_text(encoding="utf-8"))
        declared = re.match(r"^\s*(\w+)", config.get("Profile", ""))
        result["profile"] = declared.group(1).lower() if declared else None
        if result["profile"] not in {"lightweight", "standard", "strict"}:
            result["issues"].append("Profile must be lightweight, standard or strict")
        view = loop_state(plan_path.parent.parent)
        if view["state"] == "invalid":
            result["issues"].append(view["message"])
        for unit in view["units"]:
            if unit["runtime_status"] == "completed" and not unit["last_review"]:
                result["issues"].append(f"{unit['flow_unit_id']}: completed unit has no review evidence")
    result["pass"] = not result["issues"]
    return result
