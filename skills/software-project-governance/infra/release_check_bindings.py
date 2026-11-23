"""Compose plugin assets, release readiness and projection diagnostics."""

import workflow_project_roots as paths
import workflow_policy_bindings as policies

from checks import (
    commit as commit_checks, injection_budget as injection_budget,
    projection as projection_checks, version as version_checks,
)
from checks.architecture_health import _archguard_exclusion_match, _archguard_severity
from checks.capability_registry import _line_has_scoped_claim_negation
from checks.ci_domain import check_ci_evidence
from checks.manifest import (
    build_required_files_from_manifest, check_manifest_consistency,
    check_repository_navigation,
)
from hot_governance_facts import _generic_reviewer_cells, _markdown_has_heading, _markdown_section
from pathlib import Path


def lock_issue_is_blocking(issue):
    from plugin_assets import lock_issue_is_blocking as run
    return run(issue, blocking_lock_issue_types=policies._product_policy("BLOCKING_LOCK_ISSUE_TYPES"))


def structural_issue_is_blocking(issue):
    from plugin_assets import structural_issue_is_blocking as run
    return run(issue)


def blocking_structural_issues(issues):
    from plugin_assets import blocking_structural_issues as run
    return run(issues, structural_issue_is_blocking=structural_issue_is_blocking)


def _exception_note(check_id, artifact, severity=None, bytes_value=None):
    """FEAT-075 (DEC-278 单元二 item 4): annotation suffix for a finding —
    ``exception accepted (id, ref, expires)`` when an EFFECTIVE governance
    exception matches, empty otherwise (no registry → byte-identical
    pre-FEAT-075 output). Deferred import on purpose: the engine's frozen
    startup-import face (R6) must not grow. Annotation-only — never changes
    a severity, byte count, or summary (原始 FAIL 与真实字节数保留)."""

    from exception_registry import exception_note
    return exception_note(check_id, artifact, severity,
                          root=paths.HOST_PROJECT_ROOT, bytes_value=bytes_value)


def _release_exception_block():
    """FEAT-075: the release-aggregate exception disclosure (None when no
    .governance/exceptions.json exists — inert wiring; the Coordinator
    registers the real exceptions after M-0). Deferred import (R6 face)."""

    from exception_registry import release_disclosure_block
    return release_disclosure_block(root=paths.HOST_PROJECT_ROOT)


def _exception_registry_error_note():
    """FEAT-075 R0 F-2: one-line file-level registry-error disclosure (""
    when clean/absent). Both aggregation render paths attach it ONCE (first
    finding line) — a scope-matching but malformed exception never
    annotates silently. Deferred import (R6 face)."""

    from exception_registry import registry_error_note
    return registry_error_note(root=paths.HOST_PROJECT_ROOT)


def check_files():
    from plugin_assets import check_files as inspect_files
    return inspect_files(package_root_now=lambda: paths.ROOT, build_required_files_from_manifest=build_required_files_from_manifest,
                         fallback_files=lambda: (policies._product_policy("REQUIRED_FILES"),
                                                 policies._product_policy("OPTIONAL_PROJECTION_FILES")))


def check_snippets():
    from plugin_assets import check_snippets as run
    return run(package_root=paths.ROOT, required_snippets=policies._product_policy("REQUIRED_SNIPPETS"), display_path=paths._display_path)


def _resolve_release_gate_timeout(raw):
    from release_execution import _resolve_release_gate_timeout as run
    return run(raw, release_gate_timeout_default=policies._product_policy("_RELEASE_GATE_TIMEOUT_DEFAULT"))


def _run_release_validation_command(label, command, timeout=None):
    from release_execution import _run_release_validation_command as run
    return run(
        label, command, timeout, package_root=paths.ROOT,
        release_gate_timeout_env=policies._product_policy("_RELEASE_GATE_TIMEOUT_ENV"),
        resolve_release_gate_timeout=_resolve_release_gate_timeout,
    )


def run_release_execution_gates(runner=_run_release_validation_command, timeout=None):
    from release_execution import run_release_execution_gates as run
    return run(runner, timeout, package_root=paths.ROOT)


def _release_docs_line_has_guard_context(label, line):
    from product_evidence import _release_docs_line_has_guard_context as run
    return run(label, line)


def _tagged_release_replay_hint(version):
    from product_evidence import _tagged_release_replay_hint as run
    return run(version)


def check_release_docs_coverage(version, root=None):
    from product_evidence import check_release_docs_coverage as run
    return run(
        version, root, package_root=paths.ROOT, display_path=paths._display_path, git_files=paths._git_files,
        line_has_scoped_claim_negation=_line_has_scoped_claim_negation,
        release_docs_line_has_guard_context=_release_docs_line_has_guard_context,
        tagged_release_replay_hint=_tagged_release_replay_hint,
        check_manifest_consistency=check_manifest_consistency,
    )


def _markdown_table_row_by_first_cell(content, first_cell):
    from product_evidence import _markdown_table_row_by_first_cell as run
    return run(content, first_cell, split_markdown_table_row=paths._split_markdown_table_row)


def _contains_unnegated_phrase(content, phrases):
    from product_evidence import _contains_unnegated_phrase as run
    return run(
        content, phrases, line_has_scoped_claim_negation=_line_has_scoped_claim_negation,
        line_has_structured_status_negation=_line_has_structured_status_negation,
    )


def _line_has_structured_status_negation(line, phrase):
    from product_evidence import _line_has_structured_status_negation as run
    return run(line, phrase)


def _risk_status_is_closed(status):
    from product_evidence import _risk_status_is_closed as run
    return run(status)


def check_one_dot_zero_release_blockers(root=None, risk_log_path=None, external_validation_path=None, official_submission_path=None, desktop_lifecycle_path=None):
    from product_evidence import check_one_dot_zero_release_blockers as run
    return run(
        root, risk_log_path, external_validation_path, official_submission_path, desktop_lifecycle_path,
        package_root=paths.ROOT, contains_unnegated_phrase=_contains_unnegated_phrase, display_path=paths._display_path,
        markdown_table_row_by_first_cell=_markdown_table_row_by_first_cell,
        risk_status_is_closed=_risk_status_is_closed,
    )


_extract_skill_version = version_checks.extract_skill_version


def _extract_json_version(path):
    from repository_projection import _extract_json_version as run
    return run(path)


def _extract_plan_workflow_version(path):
    from repository_projection import _extract_plan_workflow_version as run
    return run(path)


def _projection_hash(path):
    from repository_projection import _projection_hash as run
    return run(path, read_text_normalized=paths._read_text_normalized)


def _projection_source_files(root, patterns=None):
    from repository_projection import _projection_source_files as run
    return run(root, patterns, projection_sync_patterns=policies._product_policy("PROJECTION_SYNC_PATTERNS"))


def _projection_target_tracked_files(root, target_dir):
    from repository_projection import _projection_target_tracked_files as run
    return run(root, target_dir)


def _target_fixture_file_is_checkable(rel_path, target_tracked):
    from repository_projection import _target_fixture_file_is_checkable as run
    return run(rel_path, target_tracked)


def check_projection_sync(root=None, target_dir=None, patterns=None):
    """Delegate projection compatibility checks to the Phase 6 module."""

    return projection_checks.check_projection_sync(
        Path(root) if root is not None else paths.ROOT,
        Path(target_dir) if target_dir is not None else None,
        patterns,
    )


def check_injection_contract(root=None):
    from repository_projection import check_injection_contract as run
    return run(
        root, package_root=paths.ROOT, injection_contract_anchors=policies._product_policy("INJECTION_CONTRACT_ANCHORS"),
        injection_contract_staged_anchors=policies._product_policy("INJECTION_CONTRACT_STAGED_ANCHORS"),
        version_line_anchor=policies._product_policy("VERSION_LINE_ANCHOR"),
        extract_skill_version=_extract_skill_version,
    )


def check_injection_budget(root=None, profile=None, budget_tokens=None):
    """Engine entry — the leaf supplies the default root (``ROOT`` is ours)."""

    return injection_budget.check_injection_budget(
        root if root is not None else paths.ROOT, profile, budget_tokens)


def emit_injection_budget_section(indent="  ", result=None):
    """Engine entry — the Check 33 sub-report, framed inside the box."""
    return injection_budget.emit_check_section(indent=indent, result=result)


def check_dsh_preset_smoke(root=None, timeout=120):
    from host_loader_probes import check_dsh_preset_smoke as run, SmokeMarkers
    return run(
        root, timeout, plugin_root=paths.PLUGIN_ROOT,
        markers=SmokeMarkers(
            concurrent_writes=policies._host_policy('DSH_SMOKE_ATTRIBUTED_CONCURRENT_WRITES_RE'),
            home_writes=policies._host_policy('DSH_SMOKE_REAL_HOME_WRITES_RE'),
            passed=policies._host_policy('DSH_SMOKE_RESULT_PASS_RE'),
        ),
    )


def run_dsh_upgrade_regression_gates(smoke_runner=None):
    from host_loader_probes import run_dsh_upgrade_regression_gates as run
    return run(
        smoke_runner, plugin_root=paths.PLUGIN_ROOT,
        dsh_upgrade_regression_label=policies._host_policy('DSH_UPGRADE_REGRESSION_LABEL'),
        release_gate_timeout_env=policies._product_policy("_RELEASE_GATE_TIMEOUT_ENV"),
        resolve_release_gate_timeout=_resolve_release_gate_timeout,
        check_dsh_preset_smoke=check_dsh_preset_smoke,
    )


def _provenance_rows_from_report(report):
    from release_provenance import _provenance_rows_from_report as run
    return run(report)


def _provenance_rows_for_governance(tracker_path=None, governance_dir=None):
    from release_provenance import _provenance_rows_for_governance as run
    return run(
        tracker_path, governance_dir, read_governance_dir=paths.GOVERNANCE_DIR, plan_path=paths.SAMPLE_PATH,
        provenance_rows_from_report=_provenance_rows_from_report,
    )


def _collect_session_closure_events(governance_dir=None, today=None):
    from release_provenance import _collect_session_closure_events as run
    return run(governance_dir, today, read_governance_dir=paths.GOVERNANCE_DIR)


def check_release_readiness(
    version=None,
    require_changelog=False,
    run_runtime_adapters=False,
    changelog_path=None,
    run_execution_gates=False,
    execution_gate_runner=_run_release_validation_command,
    lineage_mode="candidate",
    release_commit=None,
    lineage_remote="origin",
    release_unit=None,
    dsh_upgrade_regression_runner=None,
    require_delivery_evidence=False,
):
    """FIX-072: aggregate release gate scripts behind the stage-release check-release command."""
    import governance_check_bindings as governance_checks
    import host_check_bindings as host_checks
    import workflow_guard_bindings as guard_checks
    import workflow_report_selection as reports

    import release_readiness as gate

    plugin_release = not reports._host_plugin_roots_divergent()
    replay_hint = _tagged_release_replay_hint(version) if plugin_release else None
    if replay_hint:
        return {"pass": False, "issues": [replay_hint],
                "details": {"release_replay": {"pass": False, "issues": [replay_hint]}}}

    details = {}
    issues = []
    if plugin_release:
        gate.version_consistency(details, issues, governance_checks.check_version_consistency())
        gate.pack_status(details, issues, host_checks.check_governance_pack_status())
    if version:
        gate.admission(details, issues, version, _provenance_rows_for_governance())
    gate.security_descriptors(details, issues, paths.HOST_PROJECT_ROOT, paths.PLUGIN_ROOT if plugin_release else None)
    if plugin_release:
        gate.agent_adapters(details, issues, host_checks.check_agent_adapter_contract(run_runtime=run_runtime_adapters),
                            run_runtime_adapters)
        gate.projection_sync(details, issues, check_projection_sync())
        gate.cross_references(details, issues, governance_checks.check_cross_references())
    gate.archive_integrity(details, issues, guard_checks.check_archive_integrity())
    if plugin_release:
        gate.release_docs(details, issues, version, check_release_docs_coverage(version))

    lineage = check_release_lineage(version=version, mode=lineage_mode, release_commit=release_commit,
                                  remote=lineage_remote)
    details["release_lineage"] = lineage
    issues.extend(f"release lineage: {issue}" for issue in lineage["issues"])
    gate.release_delivery(details, issues, lambda: paths.HOST_PROJECT_ROOT, release_unit, version,
                          lineage_mode, require_delivery_evidence)
    if plugin_release:
        gate.release_blockers(details, issues, version, check_one_dot_zero_release_blockers() if version == "1.0.0" else [])
        gate.execution_gates(details, issues, run_execution_gates,
                             run_release_execution_gates(runner=execution_gate_runner) if run_execution_gates else [])
    else:
        gate.project_ci(details, issues, check_ci_evidence(repo_root=paths.HOST_PROJECT_ROOT))
    gate.dsh_upgrade(details, issues, plugin_release, run_execution_gates, lineage_mode,
                     lambda: (dsh_upgrade_regression_runner or run_dsh_upgrade_regression_gates)())
    path = changelog_path or (paths.ROOT / "project/CHANGELOG.md" if plugin_release else paths.HOST_PROJECT_ROOT / "CHANGELOG.md")
    gate.changelog(details, issues, version, require_changelog, path, paths._display_path)
    exceptions = _release_exception_block()
    if exceptions is not None:
        details["governance_exceptions"] = exceptions
    return {"pass": not issues, "issues": issues, "details": details}


def _run_git_lineage(args, root=None):
    from release_provenance import _run_git_lineage as run
    return run(
        args, root, host_project_root=paths.HOST_PROJECT_ROOT,
        git_lineage_timeout_seconds=policies._product_policy("GIT_LINEAGE_TIMEOUT_SECONDS"),
    )


def _validated_git_remote_name(remote):
    from release_provenance import _validated_git_remote_name as run
    return run(remote, git_remote_name_re=policies._product_policy("GIT_REMOTE_NAME_RE"))


def check_release_lineage(version, mode='candidate', release_commit=None, remote='origin', root=None):
    from release_provenance import check_release_lineage as run
    return run(
        version, mode, release_commit, remote, root, host_project_root=paths.HOST_PROJECT_ROOT,
        git_lineage_timeout_seconds=policies._product_policy("GIT_LINEAGE_TIMEOUT_SECONDS"),
        run_git_lineage=_run_git_lineage, inspect_lineage=commit_checks.check_release_lineage,
    )


def _specialist_skill_owner_issues(root, router):
    from product_evidence import _specialist_skill_owner_issues as run
    return run(root, router, active_agent_roles=policies._host_policy("ACTIVE_AGENT_ROLES"))


def check_architecture_fact_source(skill_path=None, skill_index_path=None, architecture_path=None, governance_command_path=None, agent_protocol_path=None, governance_developer_prompt_path=None):
    from product_evidence import check_architecture_fact_source as run
    return run(
        skill_path, skill_index_path, architecture_path, governance_command_path, agent_protocol_path,
        governance_developer_prompt_path, package_root=paths.ROOT, active_agent_roles=policies._host_policy("ACTIVE_AGENT_ROLES"),
        loop_role_skill_contracts=policies._host_policy("LOOP_ROLE_SKILL_CONTRACTS"), named_reviewer_roles=policies._host_policy("NAMED_REVIEWER_ROLES"),
        display_path=paths._display_path, generic_reviewer_cells=_generic_reviewer_cells,
        markdown_has_heading=_markdown_has_heading, markdown_section=_markdown_section,
        specialist_skill_owner_issues=_specialist_skill_owner_issues,
        check_repository_navigation=check_repository_navigation,
    )


def cmd_verify(args):
    import governance_check_bindings as governance_checks
    import host_check_bindings as host_checks

    from plugin_assets import report_verification
    print("== Workflow Plugin Verification ==")
    return report_verification(check_files(), check_snippets(), check_architecture_fact_source(),
                               host_checks.check_agent_adapter_contract(), governance_checks.check_version_consistency(),
                               governance_checks.check_loop_role_skill_consistency())


def _archguard_load_schema(root=None):
    from architecture_diagnostics import _archguard_load_schema as run
    return run(
        root, package_root=paths.ROOT, archguard_schema_rel=policies._product_policy("ARCHGUARD_SCHEMA_REL"),
        display_path=paths._display_path,
    )


def check_architecture_health(root=None, schema=None):
    from architecture_diagnostics import check_architecture_health as run
    return run(root, schema, package_root=paths.ROOT, archguard_load_schema=_archguard_load_schema)


def _archguard_normalized_lines(text, normalize_le=True, ignore_ws=True):
    from architecture_diagnostics import _archguard_normalized_lines as run
    return run(text, normalize_le, ignore_ws)


def _archguard_source_projection_pairs(root):
    from architecture_diagnostics import _archguard_source_projection_pairs as run
    return run(root)


def check_duplicate_code(root=None, schema=None):
    from architecture_diagnostics import check_duplicate_code as run
    return run(
        root, schema, package_root=paths.ROOT, archguard_exclusion_match=_archguard_exclusion_match,
        archguard_load_schema=_archguard_load_schema, archguard_normalized_lines=_archguard_normalized_lines,
        archguard_source_projection_pairs=_archguard_source_projection_pairs,
    )


def check_technical_debt(root=None, schema=None):
    import host_check_bindings as host_checks

    from architecture_diagnostics import check_technical_debt as run
    return run(
        root, schema, package_root=paths.ROOT,
        archguard_default_root_residue=policies._product_policy("ARCHGUARD_DEFAULT_ROOT_RESIDUE"),
        archguard_hooks_rel=policies._product_policy("ARCHGUARD_HOOKS_REL"),
        archguard_ledger_rel=policies._product_policy("ARCHGUARD_LEDGER_REL"),
        archguard_load_schema=_archguard_load_schema,
        external_validation_canonical_hook_text=host_checks._external_validation_canonical_hook_text,
        external_validation_read_text=host_checks._external_validation_read_text,
        parse_markdown_table_rows=host_checks._parse_markdown_table_rows,
    )


def check_complexity(root=None, schema=None):
    from architecture_diagnostics import check_complexity as run
    return run(
        root, schema, package_root=paths.ROOT, archguard_load_schema=_archguard_load_schema,
        archguard_severity=_archguard_severity, check_architecture_health=check_architecture_health,
    )


def check_readme_claim_evidence_levels(readme_path=None):
    from host_loading_claims import check_readme_claim_evidence_levels as run
    return run(
        readme_path, package_root=paths.ROOT, adapter_claim_registry=policies._host_policy('ADAPTER_CLAIM_REGISTRY'),
        evidence_level_marker_re=policies._host_policy('EVIDENCE_LEVEL_MARKER_RE'),
    )


def check_governance_data_size(root=None, schema=None):
    import governance_check_bindings as governance_checks

    from architecture_diagnostics import check_governance_data_size as run
    return run(
        root, schema, host_project_root=paths.HOST_PROJECT_ROOT, package_root=paths.ROOT,
        archguard_load_schema=_archguard_load_schema, archguard_severity=_archguard_severity,
        archive_reader=governance_checks._archive_reader,
    )


def cmd_check_release(args):
    import workflow_runtime_bindings as runtime_checks

    from release_validation_cli import cmd_check_release as run
    return run(args, check_release_readiness=check_release_readiness, write_cli_json=runtime_checks.write_cli_json)


def cmd_check_version_consistency(_args):
    import governance_check_bindings as governance_checks

    from repository_projection import cmd_check_version_consistency as run
    return run(_args, check_version_consistency=governance_checks.check_version_consistency)


def cmd_check_projection_sync(args):
    from repository_projection import cmd_check_projection_sync as run
    return run(
        args, check_projection_sync=check_projection_sync,
        check_entry_bootstrap_sync=lambda: projection_checks.check_entry_bootstrap_sync(),
        print_entry_bootstrap_report=lambda report: projection_checks.print_entry_bootstrap_report(report),
    )


cmd_check_entry_bootstrap_sync = projection_checks.cmd_check_entry_bootstrap_sync


def cmd_check_injection_contract(args):
    from repository_projection import cmd_check_injection_contract as run
    return run(args, check_injection_contract=check_injection_contract)


def cmd_release_ledger(args):
    from release_validation_cli import cmd_release_ledger as run
    return run(args)


def cmd_release_projection(args):
    from release_validation_cli import cmd_release_projection as run
    return run(args)


def cmd_quality_tools(_args):
    from release_validation_cli import cmd_quality_tools as run
    return run(_args)


def _archguard_print_findings(title, result, hint_key='check'):
    from architecture_diagnostics import _archguard_print_findings as run
    return run(
        title, result, hint_key, exception_note=_exception_note,
        exception_registry_error_note=_exception_registry_error_note,
    )


def cmd_check_architecture_health(args):
    from architecture_diagnostics import cmd_check_architecture_health as run
    return run(
        args, host_project_root=paths.HOST_PROJECT_ROOT, plugin_root=paths.PLUGIN_ROOT,
        archguard_schema_rel=policies._product_policy("ARCHGUARD_SCHEMA_REL"),
        archguard_print_findings=_archguard_print_findings,
        check_architecture_health=check_architecture_health,
    )


def cmd_check_duplicate_code(args):
    from architecture_diagnostics import cmd_check_duplicate_code as run
    return run(args, archguard_print_findings=_archguard_print_findings, check_duplicate_code=check_duplicate_code)


def cmd_check_technical_debt(args):
    from architecture_diagnostics import cmd_check_technical_debt as run
    return run(args, archguard_print_findings=_archguard_print_findings, check_technical_debt=check_technical_debt)


def cmd_check_complexity(args):
    from architecture_diagnostics import cmd_check_complexity as run
    return run(args, archguard_print_findings=_archguard_print_findings, check_complexity=check_complexity)


def cmd_check_governance_data_size(args):
    from architecture_diagnostics import cmd_check_governance_data_size as run
    return run(
        args, archguard_print_findings=_archguard_print_findings,
        check_governance_data_size=check_governance_data_size,
    )


def cmd_check_readme_pack_guidance(args):
    import host_check_bindings as host_checks

    from host_validation_cli import cmd_check_readme_pack_guidance as run
    return run(args, check_readme_pack_guidance=host_checks.check_readme_pack_guidance)


def cmd_check_governance_pack_status(args):
    import host_check_bindings as host_checks

    from host_validation_cli import cmd_check_governance_pack_status as run
    return run(args, check_governance_pack_status=host_checks.check_governance_pack_status)
