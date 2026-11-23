"""Select active plan rows and evaluate the evidence of goal and user impact."""
import re


PRODUCT_CODE_PATTERNS = [
    "skills/", "agents/", "infra/", "commands/",
    "adapters/", ".claude-plugin/", ".codex-plugin/", ".agents/",
    "project/",
]


def parse_impact_analysis_entries(*, parse_impact_analysis_entries_with_exemptions):
    """Parse evidence-log entries that must carry goal/user impact guardrails.

    This includes explicit type=影响分析 rows and hot plan product-code delivery
    evidence rows. FIX-073: product-code evidence with no standalone impact
    analysis must not make Check 16/17 silently pass with 0 entries.

    FIX-371/DEC-227 路线 b: EVD rows whose task row is terminal-complete in
    the hot tracker (historical hand-written-era ✅ rows; writer-committed
    rows since FIX-390) are exempt from the entry set.
    Backward-compatible wrapper — returns only the non-exempt entries; use
    parse_impact_analysis_entries_with_exemptions() for the disclosure ledger.

    Returns list of dicts: {evd_id, task_id, description, file_location, raw_line}
    """
    entries, _ = parse_impact_analysis_entries_with_exemptions()
    return entries


def parse_impact_analysis_entries_with_exemptions(*, evidence_path, current_release_task_ids,
                                                  hot_status_completion_state,
                                                  plan_hot_tracker_task_statuses, split_governance_table_row,
                                                  expand_task_ids, requires_impact_evidence):
    """parse_impact_analysis_entries + historical-exemption ledger (FIX-371).

    DEC-227 路线 b: an EVD row whose task row is terminal-complete in the hot
    tracker (historical hand-written-era data) is exempt from the Check 16/17
    entry set; every exemption is disclosed in the returned ledger — never
    silent. Rows whose task is active/new or whose terminal status is
    unprovable keep zero exemption (fail-closed).

    FIX-390 (DEC-241 消解): terminal-complete is the three-state structured
    read :func:`_hot_status_completion_state` — writer-committed terminal
    cells (ops anchor, FIX-393 identity) join the legacy ✅ prefix; unknown
    tokens are never guessed. The ✅ face of the ledger is unchanged
    (S_new ⊇ S_old); the expansion is exactly the writer-committed rows and
    stays fully disclosed.

    Returns (entries, historical_exempted); historical_exempted is a list of
    {evd_id, task_id, status} dicts.
    """
    if not evidence_path.is_file():
        return [], []
    content = evidence_path.read_text(encoding="utf-8")
    entries = []
    historical_exempted = []
    hot_task_statuses = plan_hot_tracker_task_statuses()
    completed_hot_task_ids = {
        task_id
        for task_id, status in hot_task_statuses.items()
        if hot_status_completion_state(status)
    }
    hot_task_ids = current_release_task_ids() | set(hot_task_statuses)

    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in split_governance_table_row(line)]
        if len(parts) < 8:
            continue
        evd_id = parts[1]
        task_id = parts[2]
        # FIX-368: LIVE evidence-log column layout is
        # parts[3]=type, parts[4]=description, parts[5]=fact basis,
        # parts[6]=file location (10 data cells -> 12 split parts incl. the
        # leading/trailing empties). The pre-fix parts[4]/parts[5] read was a
        # +1 offset that matched 目标对齐/用户影响 against the fact-basis
        # column — the EVD-1118 false-FAIL root cause in Check 16/17.
        evd_type = parts[3] if len(parts) > 3 else ""
        description = parts[4] if len(parts) > 4 else ""
        file_location = parts[6] if len(parts) > 6 else ""

        covered_ids = expand_task_ids(task_id) if task_id and re.search(r"[A-Z]+-\d+", task_id) else set()
        if requires_impact_evidence(task_id, evd_type, file_location, active=bool(covered_ids & hot_task_ids)):
            hot_covered = covered_ids & hot_task_ids
            target_ids = sorted(hot_covered) if hot_covered else [task_id]
            if not target_ids:
                target_ids = [task_id]
            for covered_task_id in target_ids:
                # FIX-371/DEC-227 路线 b: ✅-terminal hot-tracker task -> exempt
                # with ledger disclosure; anything unproven stays guarded.
                if covered_task_id in completed_hot_task_ids:
                    historical_exempted.append({
                        "evd_id": evd_id,
                        "task_id": covered_task_id,
                        "status": hot_task_statuses.get(covered_task_id, ""),
                    })
                    continue
                entries.append({
                    "evd_id": evd_id,
                    "task_id": covered_task_id,
                    "description": description,
                    # FIX-390: the DEC-168 machine row-family contract lands
                    # the fact basis in the independent basis column
                    # (parts[5], governance_store._build_evidence_row
                    # --basis channel). Surfaced so the Check 18/18b strict
                    # judgment reads the structured column instead of only
                    # the description narrative.
                    "fact_basis": parts[5] if len(parts) > 5 else "",
                    "file_location": file_location,
                    "raw_line": line,
                })
    return entries, historical_exempted


def check_goal_alignment(*, parse_impact_analysis_entries_with_exemptions, parse_project_config):
    """SYSGAP-023: Check that all impact analysis entries have goal alignment.

    Checks:
    1. plan-tracker has 项目目标 field (WARN if missing)
    2. Each 影响分析 entry has 目标对齐: field with >= 30 chars (FAIL if missing/short)
    3. Identical goal alignment text across different EVD rows
       (WARN — template reuse; FIX-349 ③: entries fanned out of ONE EVD row
       share a single description by construction and are never compared)

    Returns dict with 'has_project_goal', 'entries', 'duplicates', 'pass' and
    'historical_exempted' (FIX-371 ledger: terminal-complete hot-tracker rows
    exempted from the entry set — ✅ prefix, and writer-committed cells since
    FIX-390; disclosed, never silent).
    """
    result = {
        "has_project_goal": False,
        "project_goal": "",
        "entries": [],
        "duplicates": [],
        "historical_exempted": [],
        "pass": True,
    }

    # 1. Check project goal in plan-tracker
    config = parse_project_config()
    project_goal = config.get("项目目标", "")
    result["project_goal"] = project_goal
    if project_goal:
        result["has_project_goal"] = True

    # 2. Parse impact analysis entries (FIX-371/DEC-227 路线 b: historical
    # ✅-terminal rows exempted with an explicit ledger)
    entries, historical_exempted = parse_impact_analysis_entries_with_exemptions()
    result["historical_exempted"] = historical_exempted
    if not entries:
        return result

    goal_map = {}  # goal_text -> [(evd_id, task_id)]

    for entry in entries:
        desc = entry["description"]
        # Extract 目标对齐: field — captures text until next known field or end
        goal_match = re.search(
            r'目标对齐[:：]\s*(.+?)(?:\s*(?:用户影响[:：]|范围[:：]|依赖[:：]|架构影响[:：]|$))',
            desc
        )
        goal_text = goal_match.group(1).strip() if goal_match else ""
        goal_len = len(goal_text)

        has_goal = bool(goal_text)
        status = "PASS"
        if not has_goal:
            status = "FAIL"
            result["pass"] = False
        elif goal_len < 30:
            status = "FAIL"
            result["pass"] = False
        else:
            # Track for duplicate detection
            if goal_text in goal_map:
                goal_map[goal_text].append((entry["evd_id"], entry["task_id"]))
            else:
                goal_map[goal_text] = [(entry["evd_id"], entry["task_id"])]

        result["entries"].append({
            "task_id": entry["task_id"],
            "evd_id": entry["evd_id"],
            "has_goal": has_goal,
            "goal_text": goal_text[:80] + ("..." if goal_len > 80 else ""),
            "goal_len": goal_len,
            "status": status,
        })

    # 3. Check duplicates
    # FIX-349 ③: compare only entries from DIFFERENT evd_id rows. One EVD row
    # fanning out to several tasks (expand_task_ids in
    # parse_impact_analysis_entries) shares a single description by
    # construction, so identical goal text inside one row is structural, not
    # template reuse (live false positive: EVD-507 -> REQ-094<->REQ-095).
    # Cross-EVD comparison — the real template-reuse signal — is unchanged.
    for goal_text, evd_tasks in goal_map.items():
        if len(evd_tasks) >= 2:
            for i in range(len(evd_tasks)):
                for j in range(i + 1, len(evd_tasks)):
                    if evd_tasks[i][0] != evd_tasks[j][0]:
                        result["duplicates"].append(
                            (evd_tasks[i][1], evd_tasks[j][1]))

    return result


def check_user_impact(*, product_root, parse_impact_analysis_entries_with_exemptions):
    """SYSGAP-024: Check that all impact analysis entries have user impact analysis.

    Checks:
    1. Each 影响分析 entry has 用户影响: field (FAIL if missing)
    2. Required sub-fields parsed: 获得= / 感知= / 体验变化= / 迁移指南=
    3. Value validity for 获得= (WARN if unrecognized)
    4. Contradiction: 体验变化=否 but diff involves user-visible files (WARN)
    5. Breaking change: 体验变化=是 but 迁移指南=不需要 (BLOCKING)
    6. Breaking change: migration guide path does not exist (BLOCKING — if path provided)

    Returns dict with 'entries', 'blocking', 'pass' and 'historical_exempted'
    (FIX-371 ledger: terminal-complete hot-tracker rows exempted from the
    entry set — ✅ prefix, and writer-committed cells since FIX-390;
    disclosed, never silent).
    """
    USER_VISIBLE_PATTERNS = [
        "CLAUDE.md", "README.md", "CHANGELOG.md",
        "plugin.json", "marketplace.json",
        "commands/", ".claude-plugin/", ".codex-plugin/",
    ]

    # FIX-406 F-2 predicate unification: the closed vocabulary is defined
    # ONCE in the writer domain (governance_store.VALID_OBTAIN_VALUES —
    # the intake mirror and this engine check consume the same constant;
    # the pre-fix local copy is retired so the two faces can never drift).
    from governance_store import VALID_OBTAIN_VALUES

    result = {
        "entries": [],
        "blocking": [],
        "historical_exempted": [],
        "pass": True,
    }

    # FIX-371/DEC-227 路线 b: historical ✅-terminal rows exempted with an
    # explicit ledger — disclosed, never silent.
    entries, historical_exempted = parse_impact_analysis_entries_with_exemptions()
    result["historical_exempted"] = historical_exempted
    if not entries:
        return result

    # FIX-410 read-side latest-wins: per task, ONLY the latest
    # field-carrying (用户影响:) row is judged — a compliant correction
    # row supersedes older malformed rows of the same task (live RCA:
    # EVD-1252 kept Check 17 FAILing forever although a compliant
    # correction row was in place; the write side already prevents NEW
    # bad rows — the intake mirror — but the read side refused to
    # recognize corrections). Superseded rows stay in the log as
    # append-only history and are disclosed via a counter, never silent.
    # A task with NO field-carrying row keeps the original per-entry
    # logic (missing-field FAIL stands — fail-closed).
    _field_re = re.compile(r'用户影响[:：]\s*(.+?)')
    _latest_field_index = {}
    for _index, _entry in enumerate(entries):
        if _field_re.search(_entry["description"]):
            _latest_field_index[_entry["task_id"]] = _index
    _judged_entries = []
    _superseded = 0
    for _index, _entry in enumerate(entries):
        _latest = _latest_field_index.get(_entry["task_id"])
        # P1-1 (FIX-410 R0 review): supersede applies ONLY to field-carrying
        # rows — a LATER fieldless row keeps its original per-row judgment
        # (missing field -> FAIL); the earlier combination seam let such a
        # row be superseded away, swallowing the rule-1 missing-field FAIL.
        if (_latest is None or _index == _latest
                or not _field_re.search(_entry["description"])):
            _judged_entries.append(_entry)
        else:
            _superseded += 1
    result["latest_wins_superseded"] = _superseded
    entries = _judged_entries

    for entry in entries:
        desc = entry["description"]
        file_location = entry["file_location"]

        # Extract 用户影响: field — captures text until next known field or end
        user_impact_match = re.search(
            r'用户影响[:：]\s*(.+?)(?:\s*(?:目标对齐[:：]|范围[:：]|依赖[:：]|架构影响[:：]|$))',
            desc
        )
        user_impact_text = user_impact_match.group(1).strip() if user_impact_match else ""

        has_field = bool(user_impact_text)

        # Parse sub-fields
        obtain_match = re.search(r'获得=([^,]*?)(?:,|，|\s*(?:感知=|体验变化=|迁移指南=|$))', user_impact_text)
        obtain = obtain_match.group(1).strip() if obtain_match else ""

        perceive_match = re.search(r'感知=([^,]*?)(?:,|，|\s*(?:获得=|体验变化=|迁移指南=|$))', user_impact_text)
        perceive = perceive_match.group(1).strip() if perceive_match else ""

        exp_change_match = re.search(r'体验变化=([^,]*?)(?:,|，|\s*(?:获得=|感知=|迁移指南=|$))', user_impact_text)
        exp_change = exp_change_match.group(1).strip() if exp_change_match else ""

        migration_match = re.search(r'迁移指南=([^,]*?)(?:,|，|\s*(?:获得=|感知=|体验变化=|$))', user_impact_text)
        migration = migration_match.group(1).strip() if migration_match else ""

        status = "PASS"
        issues = []

        if not has_field:
            status = "FAIL"
            issues.append("缺少 用户影响: 字段")
            result["pass"] = False
        else:
            # Check sub-fields presence
            missing_subs = []
            if not obtain:
                missing_subs.append("获得=")
            if not perceive:
                missing_subs.append("感知=")
            if not exp_change:
                missing_subs.append("体验变化=")
            if not migration:
                missing_subs.append("迁移指南=")
            if missing_subs:
                issues.append(f"缺少子字段: {', '.join(missing_subs)}")
                status = "FAIL"
                result["pass"] = False

            # Value validity for 获得=
            if obtain:
                # Check if obtain value matches any valid value (lenient — contains check)
                found_valid = any(v in obtain for v in VALID_OBTAIN_VALUES)
                if not found_valid:
                    issues.append(
                        f"获得= 值 '{obtain}' 不在合法范围内"
                        f" ({', '.join(VALID_OBTAIN_VALUES[:4])} 等)"
                    )
                    if status == "PASS":
                        status = "WARN"

            # Contradiction: 体验变化=否 but file_location contains user-visible patterns
            if exp_change == "否":
                for pattern in USER_VISIBLE_PATTERNS:
                    if pattern in file_location:
                        issues.append(
                            f"体验变化=否 但证据位置涉及用户可见文件 '{pattern}'"
                        )
                        if status == "PASS":
                            status = "WARN"
                        break

            # Breaking change: 体验变化=是 + 迁移指南=不需要
            if exp_change == "是" and migration == "不需要":
                status = "BLOCKING"
                issues.append("体验变化=是（Breaking Change）但 迁移指南=不需要")

            # Breaking change: migration guide path validity
            if exp_change == "是" and migration and migration not in ("不需要", ""):
                # migration could be a relative file path from repo root
                migration_path = product_root / migration.lstrip("/")
                if not migration_path.is_file():
                    status = "BLOCKING"
                    issues.append(
                        f"体验变化=是（Breaking Change）但迁移指南路径不存在: {migration}"
                    )

        entry_result = {
            "task_id": entry["task_id"],
            "evd_id": entry["evd_id"],
            "has_field": has_field,
            "obtain": obtain,
            "perceive": perceive,
            "exp_change": exp_change,
            "migration": migration,
            "status": status,
            "issues": issues,
        }
        result["entries"].append(entry_result)

        if status in ("FAIL", "BLOCKING"):
            result["pass"] = False
        if status == "BLOCKING":
            result["blocking"].append(entry["task_id"])

    return result


def _current_release_impact_entries(*, current_release_task_ids,
                                    parse_impact_analysis_entries_with_exemptions):
    """Return impact/product-delivery entries for the active in-progress release.

    FIX-080 avoids retroactively failing historical evidence that predates the
    fact-grounding field. The commit hook enforces every new product-code commit;
    check-governance enforces the active version row so future work cannot omit it.
    """
    release_task_ids = current_release_task_ids()
    if not release_task_ids:
        return []
    return [entry for entry in parse_impact_analysis_entries(
                                   parse_impact_analysis_entries_with_exemptions=parse_impact_analysis_entries_with_exemptions)
            if entry["task_id"] in release_task_ids]


def release_impact_entries_for(governance_dir, requires_impact_evidence):
    """Read the current release's impact from a standalone project's fact files."""
    from governance_archive_data import expand_task_ids
    from plan_status import _status_clean_cell, _status_is_writer_committed_cell
    from plan_task_selection import (_current_release_task_ids, _hot_status_completion_state,
                                     _plan_hot_tracker_task_statuses, _split_governance_table_row)

    plan_path = governance_dir / "plan-tracker.md"

    def release_tasks():
        return _current_release_task_ids(plan_path=plan_path, expand_task_ids=expand_task_ids)

    def hot_status(value):
        return _hot_status_completion_state(value, status_clean_cell=_status_clean_cell,
                                            status_is_writer_committed_cell=_status_is_writer_committed_cell)

    def impact_entries():
        return parse_impact_analysis_entries_with_exemptions(
            evidence_path=governance_dir / "evidence-log.md", current_release_task_ids=release_tasks,
            hot_status_completion_state=hot_status, plan_hot_tracker_task_statuses=lambda: _plan_hot_tracker_task_statuses(
                plan_path=plan_path), split_governance_table_row=_split_governance_table_row,
            expand_task_ids=expand_task_ids, requires_impact_evidence=requires_impact_evidence)

    return _current_release_impact_entries(current_release_task_ids=release_tasks,
                                          parse_impact_analysis_entries_with_exemptions=impact_entries)
