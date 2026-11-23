"""Validate executable gate definitions and reconcile recorded gates with governance evidence."""

import re


GATE_EXECUTION_REGISTRY_REQUIRED_FIELDS = {
    "status", "execution_scope", "automation_commands_are_metadata_only", "gate_checks",
}
GATE_EXECUTION_REQUIRED_FIELDS = {
    "gate_id",
    "required_artifacts",
    "checks",
    "evidence_query",
    "automation_command",
    "human_confirmation_policy",
    "severity",
    "project_type_overrides",
}
GATE_EXECUTION_CHECK_REQUIRED_FIELDS = {
    "check_id",
    "label",
    "executor",
    "severity",
}
GATE_EXECUTION_ALLOWED_SEVERITIES = {"critical", "high", "medium", "low"}
GATE_EXECUTION_ALLOWED_EXECUTORS = {
    "function",
    "file_exists",
    "snippet_in_file",
    "completed_ratio",
    "research_doc_count",
    "constant_result",
    "evidence_mentions",
}
GATE_EXECUTION_ALLOWED_FUNCTIONS = {
    "check_quantifiable_metrics",
    "check_scope_boundary",
    "check_stakeholders",
    "check_out_of_scope",
    "check_all_required_files_exist",
    "check_g10_real_operation_data",
    "check_g10_feedback_archived_classified",
    "check_g10_issue_list_severity_status",
    "check_g10_executable_optimization_items",
    "check_g11_retro_complete",
    "check_g11_rules_templates_backfilled",
    "check_g11_next_round_direction",
    "check_risk_has_closed",
    "check_version_consistency_heuristic",
}


def _gate_execution_check_definition_issues(check, check_label, *, inputs):
    failures = []
    if not isinstance(check, dict):
        return [f"{check_label} must be an object"]
    missing_check_fields = sorted(inputs.check_required_fields - set(check))
    for field in missing_check_fields:
        failures.append(f"{check_label}: missing required field `{field}`")
    if not isinstance(check.get("check_id"), str) or not check.get("check_id", "").strip():
        failures.append(f"{check_label}.check_id must be a non-empty string")
    if not isinstance(check.get("label"), str) or not check.get("label", "").strip():
        failures.append(f"{check_label}.label must be a non-empty string")
    executor = check.get("executor")
    if executor not in inputs.allowed_executors:
        failures.append(f"{check_label}.executor has unknown value `{executor}`")
    if check.get("severity") not in inputs.allowed_severities:
        failures.append(f"{check_label}.severity must be one of {sorted(inputs.allowed_severities)}")
    if executor == "function" and check.get("function") not in inputs.allowed_functions:
        failures.append(f"{check_label}.function has unknown value `{check.get('function')}`")
    if executor in {"file_exists", "snippet_in_file"} and not isinstance(check.get("path"), str):
        failures.append(f"{check_label}.path must be declared for {executor}")
    if executor == "snippet_in_file" and not isinstance(check.get("snippet"), str):
        failures.append(f"{check_label}.snippet must be declared for snippet_in_file")
    if executor == "completed_ratio" and not isinstance(check.get("min_ratio"), (int, float)):
        failures.append(f"{check_label}.min_ratio must be numeric for completed_ratio")
    if executor == "research_doc_count" and not isinstance(check.get("min_count"), int):
        failures.append(f"{check_label}.min_count must be integer for research_doc_count")
    if executor == "constant_result":
        if check.get("result") not in {"PASS", "FAIL", "NEEDS_HUMAN"}:
            failures.append(f"{check_label}.result must be PASS/FAIL/NEEDS_HUMAN")
        if not isinstance(check.get("message"), str) or not check.get("message", "").strip():
            failures.append(f"{check_label}.message must be a non-empty string")
    if executor == "evidence_mentions" and not isinstance(check.get("keyword"), str):
        failures.append(f"{check_label}.keyword must be declared for evidence_mentions")
    return failures


def _check_gate_execution_registry(registry, display, gate_id_set, project_type_hooks, *, inputs):
    failures = []
    gate_execution_registry = registry.get("gate_execution_registry")
    if not isinstance(gate_execution_registry, dict):
        return [f"{display}: gate_execution_registry must be an object"]

    missing_fields = sorted(inputs.registry_required_fields - set(gate_execution_registry))
    for field in missing_fields:
        failures.append(f"{display}: gate_execution_registry missing required field `{field}`")
    if gate_execution_registry.get("status") != "unit-scoped":
        failures.append(f"{display}: gate_execution_registry.status must be unit-scoped")
    if gate_execution_registry.get("execution_scope") != "flow-unit":
        failures.append(f"{display}: gate_execution_registry.execution_scope must be flow-unit")
    if gate_execution_registry.get("automation_commands_are_metadata_only") is not True:
        failures.append(f"{display}: gate_execution_registry.automation_commands_are_metadata_only must be true")
    gate_checks = gate_execution_registry.get("gate_checks")
    if not isinstance(gate_checks, list):
        failures.append(f"{display}: gate_execution_registry.gate_checks must be a list")
        gate_checks = []
    gate_ids = [item.get("gate_id") for item in gate_checks if isinstance(item, dict)]
    if not all(isinstance(gate, str) for gate in gate_ids) or set(gate_ids) != gate_id_set or len(gate_ids) != len(gate_id_set):
        failures.append(f"{display}: gate_checks must define each referenced gate exactly once")

    project_type_keys = set(project_type_hooks) if isinstance(project_type_hooks, dict) else set()
    for gate_entry in gate_checks:
        if not isinstance(gate_entry, dict):
            failures.append(f"{display}: gate_execution_registry.gate_checks entries must be objects")
            continue
        gate_id = gate_entry.get("gate_id", "<missing>")
        gate_label = f"{display}: gate_execution_registry.{gate_id}"
        missing = sorted(inputs.required_fields - set(gate_entry))
        for field in missing:
            failures.append(f"{gate_label}: missing required field `{field}`")
        if gate_id not in gate_id_set:
            failures.append(f"{gate_label}: gate_id must reference gate_references")
        if not inputs.is_valid_string_list(gate_entry.get("required_artifacts")):
            failures.append(f"{gate_label}.required_artifacts must be a non-empty string list")
        evidence = gate_entry.get("evidence_query")
        if (not isinstance(evidence, dict) or not evidence.get("source")
                or not inputs.is_valid_string_list(evidence.get("fields"))):
            failures.append(f"{gate_label}.evidence_query must declare its source and evidence fields")
        automation_command = gate_entry.get("automation_command")
        if not isinstance(automation_command, dict):
            failures.append(f"{gate_label}.automation_command must be metadata object")
            automation_command = {}
        else:
            command_text = automation_command.get("command")
            if not isinstance(command_text, str) or not command_text.strip():
                failures.append(f"{gate_label}.automation_command.command must be a non-empty metadata string")
            if automation_command.get("execution_policy") != "metadata-only-not-executed-by-gate-judgment":
                failures.append(f"{gate_label}.automation_command.execution_policy must be metadata-only-not-executed-by-gate-judgment")
        human_policy = gate_entry.get("human_confirmation_policy")
        if not isinstance(human_policy, dict):
            failures.append(f"{gate_label}.human_confirmation_policy must be an object")
            human_policy = {}
        else:
            if "needs_human_when" not in human_policy:
                failures.append(f"{gate_label}.human_confirmation_policy missing `needs_human_when`")
            if not isinstance(human_policy.get("confirmation_required_for_override", False), bool):
                failures.append(f"{gate_label}.human_confirmation_policy.confirmation_required_for_override must be boolean")
        if gate_entry.get("severity") not in inputs.allowed_severities:
            failures.append(f"{gate_label}.severity must be one of {sorted(inputs.allowed_severities)}")

        checks = gate_entry.get("checks")
        if not isinstance(checks, list) or not checks:
            failures.append(f"{gate_label}.checks must be a non-empty list")
            checks = []
        seen_check_ids = []
        for check in checks:
            if not isinstance(check, dict):
                failures.append(f"{gate_label}.checks entries must be objects")
                continue
            check_id = check.get("check_id", "<missing>")
            seen_check_ids.append(check_id)
            check_label = f"{gate_label}.checks.{check_id}"
            failures.extend(inputs.gate_execution_check_definition_issues(check, check_label))
        duplicate_checks = sorted({check_id for check_id in seen_check_ids if seen_check_ids.count(check_id) > 1})
        for check_id in duplicate_checks:
            failures.append(f"{gate_label}.checks duplicate check_id `{check_id}`")

        overrides = gate_entry.get("project_type_overrides")
        if not isinstance(overrides, dict):
            failures.append(f"{gate_label}.project_type_overrides must be an object")
            overrides = {}
        unknown_overrides = sorted(set(overrides) - project_type_keys)
        for project_type in unknown_overrides:
            failures.append(f"{gate_label}.project_type_overrides unknown project type `{project_type}`")
        for project_type, override in overrides.items():
            override_label = f"{gate_label}.project_type_overrides.{project_type}"
            if not isinstance(override, dict):
                failures.append(f"{override_label} must be an object")
                continue
            if "additional_required_artifacts" in override and not isinstance(override.get("additional_required_artifacts"), list):
                failures.append(f"{override_label}.additional_required_artifacts must be a string list")
            elif "additional_required_artifacts" in override and not inputs.is_valid_string_list(override.get("additional_required_artifacts")):
                failures.append(f"{override_label}.additional_required_artifacts must be a non-empty string list")
            if "additional_checks" in override:
                additional_checks = override.get("additional_checks")
                if not isinstance(additional_checks, list):
                    failures.append(f"{override_label}.additional_checks must be a list")
                else:
                    for index, check in enumerate(additional_checks):
                        if not isinstance(check, dict):
                            failures.append(f"{override_label}.additional_checks entries must be objects")
                            continue
                        check_id = check.get("check_id", f"index_{index}")
                        failures.extend(inputs.gate_execution_check_definition_issues(
                            check,
                            f"{override_label}.additional_checks.{check_id}",
                        ))
            if "severity_override" in override and override.get("severity_override") not in inputs.allowed_severities:
                failures.append(f"{override_label}.severity_override must be one of {sorted(inputs.allowed_severities)}")

    return failures


def _gate_execution_registry_contract_issues(registry, display, *, inputs):
    gate_references = registry.get("gate_references")
    if isinstance(gate_references, list):
        gate_id_set = {
            gate.get("gate_id")
            for gate in gate_references
            if isinstance(gate, dict) and isinstance(gate.get("gate_id"), str)
        }
    else:
        gate_id_set = set()
    project_type_hooks = registry.get("project_type_hooks")
    if not isinstance(project_type_hooks, dict):
        project_type_hooks = {}
    return inputs.check_gate_execution_registry(registry, display, gate_id_set, project_type_hooks)


def check_gate_consistency(*, current_governance_dir, archive_reader, check_evidence_completeness):
    """Check the evidence actually consumed by each unit, plus task closure references."""
    from checks.loop_receipts import receipt_issues

    ds = archive_reader()
    evidenced = ds.get_all_evidence_task_map()
    issues = [{"type": "loop_receipt", "detail": issue} for issue in receipt_issues(current_governance_dir().parent)]

    # Check for tasks marked 已完成 in plan-tracker but no evidence.
    # Uses GovernanceDataSource to cover both hot files + archive files.
    completeness = check_evidence_completeness()
    tasks_without_evidence = completeness["missing_evidence"]
    if tasks_without_evidence:
        issues.append({
            "type": "completed_tasks_missing_evidence",
            "detail": tasks_without_evidence,
        })
    if completeness.get("historical_missing_evidence"):
        issues.append({
            "type": "historical_completed_tasks_missing_evidence",
            "detail": completeness["historical_missing_evidence"],
        })

    # Check for evidence entries referencing non-existent tasks.
    # Uses GovernanceDataSource to include archived tasks.
    all_tasks = ds.get_all_task_ids()

    orphan_evidence = set(evidenced.keys()) - all_tasks
    if orphan_evidence:
        issues.append({
            "type": "orphan_evidence",
            "detail": sorted(orphan_evidence),
        })

    return issues


def check_protocol_compliance(
    *, governance_dir, plan_path, date_shape, governance_table_cells, status_is_terminal_cell,
):
    """Check protocol compliance: DRI assignment, evidence format, conditional pass tracking.

    This is the external validation counterpart to M8 agent self-check.
    It independently detects structural protocol violations from governance records.
    """
    issues = {
        "dri_violations": [],       # Tasks without unique DRI
        "evidence_format": [],      # Evidence entries with missing required fields
        "conditional_pass": [],     # passed-with-conditions without corrective tasks
    }

    plan_content = plan_path.read_text(encoding="utf-8")

    # ── DRI Check: tasks with missing/multi-valued/ambiguous Owner ──
    task_rows = []
    in_table = False
    for line in plan_content.split("\n"):
        line = line.strip()
        if "## 样例跟踪表" in line:
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if in_table and line.startswith("|") and not "---" in line:
            parts = [p.strip() for p in line.split("|")]
            # Skip header row
            if parts[1] == "ID" or not re.match(r"[A-Z]+-\d+", parts[1]):
                continue
            task_rows.append(parts)

    dri_violations = []
    for parts in task_rows:
        if len(parts) < 11:
            continue
        task_id = parts[1]
        status = parts[10] if len(parts) > 10 else ""
        owner = parts[7] if len(parts) > 7 else ""

        # Only check active tasks — FIX-479: shared terminal predicate
        # (_status_is_terminal_cell; emoji-prefixed terminal shapes like
        # 「✅ 已完成」 are terminal too, same source as Check 9)
        if status_is_terminal_cell(status):
            continue

        # Check for DRI violations
        violations = []
        if not owner or owner == "":
            violations.append("Owner is empty")
        elif any(sep in owner for sep in ("+", "/", "、", "&", ",")):
            violations.append(f"Owner is multi-valued: '{owner}'")
        elif owner in ("待定", "多人", "TBD", "N/A", "未分配"):
            violations.append(f"Owner is ambiguous: '{owner}'")

        if violations:
            dri_violations.append({
                "task_id": task_id,
                "status": status,
                "owner": owner,
                "violations": violations,
            })

    issues["dri_violations"] = dri_violations



    # ── Evidence Format Check: evidence entries with missing required fields ──
    evidence_path = governance_dir / "evidence-log.md"
    if evidence_path.is_file():
        ev_content = evidence_path.read_text(encoding="utf-8")
        for line in ev_content.split("\n"):
            line = line.strip()
            if not line.startswith("| EVD-"):
                continue
            # FIX-372 (review-FIX-368-CODE-R0 P2-1): validate the LIVE
            # evidence-log column layout (FIX-368). _governance_table_cells
            # strips the leading/trailing empties and preserves pipes inside
            # JSON/code-span cells, so cells are pure data cells:
            #   LIVE 10-cell rows: 0=EVD, 1=TaskID, 2=Type, 3=Description,
            #     4=fact basis, 5=Location, 6=EntryMethod(录入方式), 7=Date,
            #     8=Gate, 9=Notes
            #   9-cell historical rows (no separate file column): 0=EVD,
            #     1=TaskID, 2=Type, 3=Description, 4=fact basis, 5=Author,
            #     6=Date, 7=Gate, 8=Notes
            # The pre-fix check validated the legacy Stage-column offsets
            # (3=Stage/4=Type/5=Description), reading the LIVE fact-basis
            # column as Description (false "missing Description" when the
            # fact cell was empty) and flagging 9-cell historical rows as
            # short rows. The Stage requirement is dropped: the LIVE layout
            # has no Stage column. 9-cell rows are validated against their
            # own offsets (Author/Date) instead of being rejected. FIX-374:
            # a date-shaped cells[6] proves the historical Date cell is
            # present; a 9-cell row failing that shape test is a truncated
            # LIVE row (Date cell lost) and is validated against the LIVE
            # offsets with Date reported missing (review-FIX-372-CODE-R0 F-1).
            cells = governance_table_cells(line)
            if len(cells) < 9:
                issues["evidence_format"].append(
                    f"{cells[0] if cells else '???'}: only {len(cells)} data fields (expected ≥9)"
                )
                continue

            evd_id = cells[0]
            missing = []
            if not cells[1]:
                missing.append("TaskID")
            if not cells[2]:
                missing.append("Type")
            if not cells[3]:
                missing.append("Description")
            if len(cells) >= 10:
                # LIVE 10-cell shape
                if not cells[5]:
                    missing.append("Location")
                if not cells[6]:
                    missing.append("EntryMethod")
                if not cells[7]:
                    missing.append("Date")
            else:
                # FIX-374 (review-FIX-372-CODE-R0 F-1): a 9-cell row is
                # ambiguous — either a genuine historical row (Author in
                # cells[5], Date in cells[6]) or a truncated LIVE row that
                # lost its Date cell (the EntryMethod text then sits in
                # cells[6], and the pre-fix branch read Location/
                # EntryMethod as Author/Date, silently passing a genuinely
                # missing Date — fail-blind). Disambiguate by content
                # shape (_EVIDENCE_DATE_SHAPE_RE): a date-shaped cells[6]
                # proves the historical Date cell is present; anything
                # else contradicts the historical Date semantics and is
                # validated as a truncated LIVE row.
                #
                # FIX-382 (review-FIX-374 F-2② combo criterion): within
                # the non-date cells[6] face, a date-shaped cells[7]
                # proves the real Date cell survived at its shifted LIVE
                # offset — the row lost a TRAILING cell (Gate or Notes),
                # not Date, so "missing Date" there was a false positive;
                # report the trailing loss instead. Issue count is
                # unchanged (still flagged, fail-noisy) — only the
                # message becomes accurate. Residual face kept open by
                # decision (explicit no-fix + ledger disclosure): losing
                # a cell BEFORE Date (fact/Location/EntryMethod) is
                # content-indistinguishable from a genuine historical row
                # (identical Date/Gate/Notes tail; free-text middle
                # cells) — criteria extension would false-positive on the
                # historical exemption face.
                if date_shape.match(cells[6]):
                    # Historical shape: the Date cell is date-shaped (and
                    # thus non-empty) by construction.
                    if not cells[5]:
                        missing.append("Author")
                elif date_shape.match(cells[7]):
                    # Truncated LIVE, trailing loss (Gate or Notes): the
                    # Date cell is present at cells[7]; Location/
                    # EntryMethod emptiness stays validated at their
                    # unshifted offsets (an empty cell and a lost trailing
                    # cell can coexist).
                    if not cells[5]:
                        missing.append("Location")
                    if not cells[6]:
                        missing.append("EntryMethod")
                    missing.append(
                        "Gate/Notes (trailing LIVE cell lost"
                        " — Date present at shifted offset)"
                    )
                else:
                    # Truncated LIVE with a genuinely lost Date cell (or a
                    # historical row with an empty/non-separator Date cell
                    # — fail-noisy either way): validate the LIVE columns
                    # at their real offsets and report the lost Date cell.
                    if not cells[5]:
                        missing.append("Location")
                    if not cells[6]:
                        missing.append("EntryMethod")
                    missing.append("Date")

            if missing:
                issues["evidence_format"].append(
                    f"{evd_id}: missing fields — {', '.join(missing)}"
                )

    return issues


def parse_tier_definitions(plan_path):
    """Parse Tier definitions from plan-tracker's DEC-052 implementation roadmap.

    Returns: dict mapping tier_id (e.g., "0-A") -> list of task IDs.
    """
    content = plan_path.read_text(encoding="utf-8")
    lines = content.split("\n")

    in_roadmap = False
    tiers = {}
    current_tier = None

    for line in lines:
        # Detect start of implementation roadmap section
        if line.strip() == "## 实施路线图（DEC-052）":
            in_roadmap = True
            continue
        # Stop at next top-level section
        if in_roadmap and line.startswith("## "):
            break

        if not in_roadmap:
            continue

        # Detect Tier header: "Tier 0-A: description"
        tier_match = re.match(r"^Tier (\d+-[A-Z]):", line)
        if tier_match:
            current_tier = tier_match.group(1)
            tiers[current_tier] = []
            continue

        # Collect task IDs within current tier
        # Format: "  AUDIT-XXX (PX) — description" or "  MAINT-XXX (PX) — description"
        if current_tier:
            task_match = re.match(r"^\s+([A-Z]+-\d+)\s+\(P\d\)", line)
            if task_match:
                tiers[current_tier].append(task_match.group(1))

    return tiers


def check_tier_audit_completeness(read_tiers, read_status, read_evidence_ids):
    """Check that each completed Tier has a corresponding TIER-X-Y-AUDIT evidence entry.

    Per DEC-052 execution discipline rule #3: every completed Tier MUST have an audit.
    Audit evidence uses task ID format: TIER-<layer>-<tier>-AUDIT (e.g., TIER-0-C-AUDIT).

    Returns: dict with tier details and issue lists.
    """
    tiers = read_tiers()
    status_map = read_status()
    evidence_task_ids = read_evidence_ids()

    completed_without_audit = []
    completed_with_audit = []
    incomplete_tiers = []
    all_details = []

    for tier_id, task_ids in tiers.items():
        if not task_ids:
            continue

        # Check status of each task in this tier
        task_statuses = {}
        all_completed = True
        completed_count = 0
        for tid in task_ids:
            status = status_map.get(tid, "未找到")
            task_statuses[tid] = status
            if status == "已完成":
                completed_count += 1
            else:
                all_completed = False

        # Check for TIER audit evidence
        audit_evidence_id = f"TIER-{tier_id}-AUDIT"
        has_audit = audit_evidence_id in evidence_task_ids

        detail = {
            "tier_id": tier_id,
            "task_count": len(task_ids),
            "completed_count": completed_count,
            "task_statuses": task_statuses,
            "all_completed": all_completed,
            "has_audit": has_audit,
            "audit_evidence_id": audit_evidence_id,
        }
        all_details.append(detail)

        if all_completed and not has_audit:
            completed_without_audit.append(detail)
        elif all_completed and has_audit:
            completed_with_audit.append(detail)
        elif not all_completed:
            incomplete_tiers.append(detail)

    return {
        "completed_without_audit": completed_without_audit,
        "completed_with_audit": completed_with_audit,
        "incomplete_tiers": incomplete_tiers,
        "all_details": all_details,
    }
