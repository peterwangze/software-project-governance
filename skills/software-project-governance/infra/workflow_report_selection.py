"""Choose full-check reports and product gates in their execution order."""

from checks.capability_registry import check_capability_registry
from checks.ci_domain import check_ci_evidence
from checks.evidence_domain import (
    check_evidence_completeness, check_evidence_quality, check_fact_grounding,
    check_structured_evidence, emit_evidence_completeness, emit_evidence_quality,
    render_rb2_goal_contract_block,
)
from checks.gate_domain import release_unit_issues
from checks.manifest import check_manifest_consistency
from checks.review_domain import (
    DEGRADED_FUSE_THRESHOLD, check_agent_team_review,
    check_governance_review_fallback_policy, check_loop_wiring_call_sites,
    check_m5_compliance_with_record_scope, check_m5_runtime_triggers,
    check_review_closure, check_review_coverage, check_review_debt,
    check_review_machine_provenance,
)
from checks.risk_domain import (
    emit_risk_escalation, emit_risk_mitigation_closure, emit_risk_staleness,
)
from workspace_checks import check_untracked_files
import os
import workflow_policy_bindings as policies



_PLUGIN_PRODUCT_CHECK_IDS = frozenset({
    # 插件 git 作为事实源（-C ROOT 而非宿主仓库）
    "Check 7",    # Commit-Task Traceability
    "Check 15",   # Commit Scope Verification
    # 插件包本体文件作为事实源
    "Check 10",   # M5 AskUserQuestion Compliance（插件 source 扫描）
    "Check 11",   # Manifest Consistency
    "Check 12",   # Cross-Reference Checking
    "Check 24",   # Version Consistency（插件版本资产）
    "Check 28b",  # Projection Sync Guard（source/fixtures/native entries）
    "Check 28d",  # Runtime Readiness Matrix（插件 docs）
    "Check 28e",  # First-Session Measurement（插件 docs）
    "Check 28f",  # Governance Pack Registry（插件 core JSON）
    "Check 28h",  # README Pack Guidance
    "Check 28i",  # Governance Pack Status Boundary
    "Check 28k",  # Capability Registry（插件 core JSON）
    "Check 28n",  # Mainstream Agent Loading（插件 docs）
    # ArchGuard 插件树扫描
    "Check 28o",  # Architecture Health
    "Check 28p",  # Duplicate Code
    "Check 28q",  # Technical Debt
    "Check 28r",  # Complexity
    "Check 28t",  # README Claim→Evidence Levels（插件包本体 README）
    "Check 28u",  # DSH Preset Session Smoke（插件包本体 launch.py + presets/）
    "Check 28v",  # DSH Preset Schema Compat（插件 presets/ + adapters/dsh 组合 ↔ 安装态 dsh schema）
    "Check 28w",  # DSH Dependency Boundary（契约 K-1~K-13：模板/令牌/hooks/patch/证据/覆盖/演练基线）
    "Check 30b",  # Loop wiring call sites（插件 infra AST 扫描）
    "Check 33",   # Injection Contract（插件 persona/SKILL/AGENTS 锚点）
})


def _host_plugin_roots_divergent():
    """True when the host project root differs from the plugin package root.

    FIX-270 mixed-root watchdog: every check's fact-source root must equal the
    project it is governed against. When the roots diverge (host scenario),
    plugin-package-rooted checks are product self-checks and are skipped by
    default (--product-gates re-enables); when they coincide (dogfood) all
    checks run.
    """
    import workflow_project_roots as paths

    try:
        host = os.path.normcase(os.path.abspath(os.fspath(paths.HOST_PROJECT_ROOT)))
        plugin = os.path.normcase(os.path.abspath(os.fspath(paths.PLUGIN_ROOT)))
        return host != plugin
    except Exception:
        return False


def _product_gate_active(args):
    """Whether PLUGIN_PRODUCT checks run in this invocation.

    dogfood（host==plugin）→ always; host mode → only with ``--product-gates``;
    ``--quick``（FX-195 Slice-2）→ never: the quick face is *defined* by the
    FEAT-025 registry as "everything except the not-quick exclusion set", and
    that exclusion set is machine-checked equal to this very product-gate set
    (the registry side asserts the identity), so quick reuses the existing
    ``[SKIP]`` machinery instead of introducing a second, parallel selection
    path in the monolith (§255 carrier discipline).
    """
    if getattr(args, "quick", False):
        return False
    if not _host_plugin_roots_divergent():
        return True
    return bool(getattr(args, "product_gates", False))


_PRODUCT_GATE_LABELS = {
    "Check 7": "Commit-Task Traceability",
    "Check 10": "M5 AskUserQuestion Compliance",
    "Check 11": "Manifest Consistency",
    "Check 12": "Cross-Reference Checking",
    "Check 15": "Commit Scope Verification",
    "Check 24": "Version Consistency",
    "Check 28b": "Projection Sync Guard",
    "Check 28d": "Runtime Readiness Matrix Guard",
    "Check 28e": "First-Session Measurement Guard",
    "Check 28f": "Governance Pack Registry",
    "Check 28h": "README Pack Guidance",
    "Check 28i": "Governance Pack Status Boundary",
    "Check 28k": "Capability Registry",
    "Check 28n": "Mainstream Agent Loading",
    "Check 28o": "Architecture Health (ArchGuard/REQ-101)",
    "Check 28p": "Duplicate Code (ArchGuard/REQ-101)",
    "Check 28q": "Technical Debt (ArchGuard/REQ-101)",
    "Check 28r": "Complexity (ArchGuard/REQ-101)",
    "Check 28t": "README Claim→Evidence Levels (FEAT-014)",
    "Check 28u": "DSH Preset Session Smoke (FEAT-015)",
    "Check 28v": "DSH Preset Schema Compat",
    "Check 28w": "DSH Dependency Boundary (FEAT-031)",
    "Check 30b": "Loop wiring call sites",
    "Check 33": "Injection Contract",
}


def _print_product_gate_skipped(check_id):
    """Print the standard SKIP banner for a plugin-product check in host mode."""
    label = _PRODUCT_GATE_LABELS.get(check_id, "")
    title = f"{check_id}: {label}" if label else check_id
    print(f"\n┌─ {title} {'─' * max(1, 60 - len(title))}┐")
    print("│  [SKIP] product self-check — plugin-package fact source; "
          "host/plugin roots diverge. Run with --product-gates to enable.")
    print("└──────────────────────────────────────────────────────┘")


def _full_check_results(args):
    """Bind each report to its current checks only when the full scan reaches it."""
    import delivery_check_bindings as delivery_checks
    import governance_check_bindings as governance_checks
    import host_check_bindings as host_checks
    import release_check_bindings as release_checks
    import workflow_context_bindings as context_checks
    import workflow_guard_bindings as guard_checks
    import workflow_project_roots as paths

    import health_governance_sections as governance
    import health_delivery_sections as delivery
    import health_review_sections as review
    import health_product_sections as product

    def product_gate_active():
        return _product_gate_active(args)

    yield governance.section_1_evidence_completeness(
        emit_evidence_completeness, check_evidence_completeness,
    )
    yield governance.section_2_risk_staleness(emit_risk_staleness, governance_checks.check_risk_staleness)
    yield governance.section_2b_decision_premises(governance_checks.check_decision_premise)
    yield governance.section_3_gate_consistency(governance_checks.check_gate_consistency)
    yield governance.section_4_evidence_quality(emit_evidence_quality, check_evidence_quality)
    yield governance.section_5_protocol_compliance(governance_checks.check_protocol_compliance)
    yield governance.section_6_tier_audits(governance_checks.check_tier_audit_completeness)
    yield product.section_7_commit_traceability(
        product_gate_active, governance_checks.check_commit_task_references,
        _print_product_gate_skipped,
    )
    yield governance.section_8_risk_escalation(emit_risk_escalation, governance_checks.check_risk_escalation)
    yield governance.section_9_task_deadlines(governance_checks.check_task_deadline)
    yield review.section_10_user_questions(
        product_gate_active, check_m5_compliance_with_record_scope,
        _print_product_gate_skipped,
    )
    yield product.section_11_manifest(
        product_gate_active, check_manifest_consistency, _print_product_gate_skipped,
    )
    yield governance.section_12_cross_references(
        product_gate_active, governance_checks.check_cross_references,
        host_checks.check_exploration_sample_advisories, _print_product_gate_skipped,
    )
    yield governance.section_13_sequential_ids(governance_checks.check_sequential_ids, governance_checks._print_sequential_id_check)
    yield governance.section_14_structural_validity(
        governance_checks.check_structural_validity, release_checks.blocking_structural_issues,
    )
    yield product.section_15_commit_scope(
        product_gate_active, delivery_checks.check_commit_scope, _print_product_gate_skipped,
    )
    yield delivery.section_16_goal_alignment(delivery_checks.check_goal_alignment)
    yield delivery.section_17_user_impact(delivery_checks.check_user_impact)
    yield delivery.section_18_fact_grounding(check_fact_grounding)
    yield delivery.section_18b_structured_evidence(check_structured_evidence)
    yield delivery.section_18c_execution_packets(delivery_checks.check_execution_packets)
    yield delivery.section_18d_product_outcomes(
        delivery_checks.check_product_success_contracts, render_rb2_goal_contract_block,
    )
    yield delivery.section_18e_acceptance(delivery_checks.check_acceptance_contracts)
    yield delivery.section_18f_quality_budget(delivery_checks.check_quality_budget)
    yield delivery.section_18g_vertical_slices(delivery_checks.check_vertical_slices)
    yield delivery.section_18h_scaffolds(delivery_checks.check_deterministic_scaffolds)
    yield delivery.section_18i_interruption_policy(delivery_checks.check_interruption_policy)
    yield review.section_19_team_review(check_agent_team_review)
    yield review.section_20_agent_activation(host_checks.check_agent_activation)
    yield review.section_21_review_debt(check_review_debt, DEGRADED_FUSE_THRESHOLD)
    yield review.section_22_review_coverage(check_review_coverage)
    yield review.section_23_profile(host_checks.check_profile_consistency)
    yield product.section_24_version(
        product_gate_active, governance_checks.check_version_consistency, _print_product_gate_skipped,
    )
    yield governance.section_25_untracked_files(check_untracked_files)
    yield governance.section_26_locks(guard_checks.check_agent_lock_consistency, release_checks.lock_issue_is_blocking)
    yield governance.section_27_archives(guard_checks.check_archive_integrity)
    yield review.section_28_review_fallback(check_governance_review_fallback_policy)
    yield product.section_28b_projection_sync(
        product_gate_active, release_checks.check_projection_sync, _print_product_gate_skipped,
    )
    yield governance.section_28c_hot_facts(
        governance_checks.check_hot_fact_source_consistency, _host_plugin_roots_divergent,
    )
    yield product.section_28d_runtime_matrix(
        product_gate_active, host_checks.check_runtime_readiness_matrix,
        _print_product_gate_skipped,
    )
    yield product.section_28e_first_session(
        product_gate_active, host_checks.check_first_session_measurement,
        _print_product_gate_skipped,
    )
    yield product.section_28f_governance_packs(
        product_gate_active, host_checks.check_governance_packs, _print_product_gate_skipped,
    )
    yield governance.section_28g_governance_context(context_checks.check_governance_context)
    yield product.section_28h_readme_guidance(
        product_gate_active, host_checks.check_readme_pack_guidance, _print_product_gate_skipped,
    )
    yield product.section_28i_pack_status(
        product_gate_active, host_checks.check_governance_pack_status,
        _print_product_gate_skipped,
    )
    yield product.section_28j_capability_context(context_checks.check_capability_context)
    yield product.section_28k_capability_registry(
        product_gate_active, check_capability_registry, _print_product_gate_skipped,
    )
    yield product.section_28l_host_capabilities(context_checks.check_host_capability_context)
    yield product.section_28n_agent_loading(
        product_gate_active, host_checks.check_mainstream_agent_loading,
        _print_product_gate_skipped,
    )
    yield product.section_28o_architecture_health(
        product_gate_active, release_checks.check_architecture_health, _print_product_gate_skipped,
    )
    yield product.section_28p_duplicate_code(
        product_gate_active, release_checks.check_duplicate_code, _print_product_gate_skipped,
    )
    yield product.section_28q_technical_debt(
        product_gate_active, release_checks.check_technical_debt, _print_product_gate_skipped,
    )
    yield product.section_28r_complexity(
        product_gate_active, release_checks.check_complexity, _print_product_gate_skipped,
    )
    yield governance.section_28s_data_size(
        release_checks.check_governance_data_size, release_checks._exception_registry_error_note, release_checks._exception_note,
    )
    yield product.section_28t_readme_evidence(
        product_gate_active, release_checks.check_readme_claim_evidence_levels,
        _print_product_gate_skipped,
    )
    yield review.section_29_runtime_triggers(check_m5_runtime_triggers)
    yield review.section_30_review_closure(check_review_closure)
    yield review.section_30c_review_provenance(check_review_machine_provenance)
    yield review.section_30b_loop_wiring(product_gate_active, check_loop_wiring_call_sites)
    yield delivery.section_32_change_triage(governance_checks.check_change_triage)
    yield product.section_33_injection_contract(
        product_gate_active, release_checks.check_injection_contract, release_checks.emit_injection_budget_section,
        _print_product_gate_skipped,
    )
    yield delivery.section_34_completion_recommendations(guard_checks.check_completion_recommendation)
    yield governance.section_35_snapshot_freshness(governance_checks.check_snapshot_freshness)
    yield governance.section_36_risk_mitigation(
        emit_risk_mitigation_closure, governance_checks.check_risk_mitigation_closure_with_archive,
    )
    yield delivery.section_37_release_gates(release_unit_issues, paths.HOST_PROJECT_ROOT)
    yield delivery.section_38_ci_evidence(check_ci_evidence)
    yield review.section_39_completion_gate(governance_checks.check_r1_completion_gate)
    yield review.section_41_priority_inversion(release_checks._provenance_rows_for_governance)
    yield review.section_42_discovery_closure(
        release_checks._collect_session_closure_events, policies._product_policy("_DEFERRED_LEDGER_FILENAME"),
    )
    yield product.section_28u_dsh_smoke(
        product_gate_active, release_checks.check_dsh_preset_smoke, _print_product_gate_skipped,
    )
    yield product.section_28v_dsh_schema(product_gate_active, _print_product_gate_skipped)
    yield product.section_28w_dsh_boundary(product_gate_active, _print_product_gate_skipped)
