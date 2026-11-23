"""Public imports and replaceable bindings for historical Python callers.

Only the CLI compatibility layer uses this finite catalog. Domain implementations
receive explicit roots, policies and callbacks at their existing boundaries.
"""
from importlib import import_module
import sys
from types import ModuleType

import workflow_policy_bindings as policies

_FAMILY_EXPORTS = {
    'delivery_check_bindings': (
        'ACCEPTANCE_CONTRACT_REQUIRED_FIELDS ACCEPTANCE_NOT_RUN_STATUSES ACCEPTANCE_PASS_STATUSES '
        'ACCEPTANCE_RUNNABLE_COMMAND_RE DETERMINISTIC_SCAFFOLD_BROAD_SCOPE_RE '
        'DETERMINISTIC_SCAFFOLD_COMMAND_RE DETERMINISTIC_SCAFFOLD_DIR '
        'DETERMINISTIC_SCAFFOLD_REQUIRED_QUALITY_DIMENSIONS DETERMINISTIC_SCAFFOLD_REQUIRED_SECTIONS '
        'DETERMINISTIC_SCAFFOLD_SECTION_SIGNALS DETERMINISTIC_SCAFFOLD_SIGNAL_RE DETERMINISTIC_SCAFFOLD_TYPES '
        'DETERMINISTIC_SCAFFOLD_WEAK_RE EXECUTION_PACKET_REQUIRED_FIELDS FIRST_RUN_DEMO_REQUIRED_FIELDS '
        'FIRST_RUN_DEMO_REQUIRED_MARKERS INTERRUPTION_POLICY_CRITICAL_TRIGGER_KEYS '
        'INTERRUPTION_POLICY_DEFAULT_EXAMPLES INTERRUPTION_POLICY_PACKET_CRITICAL_SIGNALS '
        'INTERRUPTION_POLICY_PLACEHOLDER_RE INTERRUPTION_POLICY_REQUIRED_ASSUMPTION_FIELDS '
        'INTERRUPTION_POLICY_REQUIRED_PHRASES INTERRUPTION_POLICY_REQUIRED_TEMPLATE_PHRASES Path '
        'QUALITY_BUDGET_DIMENSIONS QUALITY_BUDGET_EXEMPT_STATUSES QUALITY_BUDGET_PASS_STATUSES '
        'QUALITY_BUDGET_PENDING_STATUSES QUALITY_BUDGET_VALIDATION_SIGNAL_RE QUALITY_BUDGET_WEAK_PROSE_RE '
        'TASK_PENDING_STATUS_MARKERS VERTICAL_SLICE_BEHAVIOR_SIGNAL_RE VERTICAL_SLICE_BROAD_SCOPE_RE '
        'VERTICAL_SLICE_DEMO_SIGNAL_RE VERTICAL_SLICE_PASS_STATUSES VERTICAL_SLICE_PENDING_STATUSES '
        'VERTICAL_SLICE_REQUIRED_FIELDS VERTICAL_SLICE_TECH_LAYER_RE VERTICAL_SLICE_USER_SIGNAL_RE '
        'VERTICAL_SLICE_WEAK_PROSE_RE _acceptance_policy _current_release_impact_entries '
        '_current_release_task_ids _execution_packet_field_issues _hot_status_completion_state '
        '_interruption_policy _is_process_only_product_success_metric _is_task_pending_status_allowed '
        '_is_too_broad_scope_text _load_execution_packets _normalize_priority _plan_hot_tracker_task_statuses '
        '_product_success_policy _quality_budget_policy _read_execution_packet_document _scaffold_policy '
        '_strip_markdown_bold_markers _task_priority_from_table_parts _validate_acceptance_contract '
        '_validate_execution_packet _validate_interruption_policy_examples _validate_product_success_contract '
        '_validate_quality_budget _validate_vertical_slice _vertical_slice_policy '
        'assert_first_run_demo_snapshot build_execution_packet build_first_run_demo_snapshot '
        'check_acceptance_contracts check_commit_scope check_deterministic_scaffolds check_execution_packets '
        'check_goal_alignment check_interruption_policy check_product_success_contracts check_quality_budget '
        'check_user_impact check_vertical_slices classify_user_interruption cmd_check_acceptance_contracts '
        'cmd_check_commit_scope cmd_check_deterministic_scaffolds cmd_check_goal_alignment '
        'cmd_check_interruption_policy cmd_check_product_success_contracts cmd_check_quality_budget '
        'cmd_check_user_impact cmd_check_vertical_slices cmd_execution_packet cmd_first_run_demo '
        'cmd_generate_deterministic_scaffold generate_execution_packets render_delivery_trust_snapshot '
        'render_deterministic_scaffold render_rb2_goal_contract_block '
    ).split(),
    'governance_check_bindings': (
        'FIX_087_READINESS_VERSION FIX_087_REQ_TASKS FIX_105_PLAN_WORKFLOW_VERSION_RE '
        'FIX_105_READINESS_RELEASE_BLOCKERS FIX_105_SNAPSHOT_DATE_RE FIX_105_SNAPSHOT_RELEASE_VERSION_RE '
        'FIX_105_SNAPSHOT_VERSION_RE GovernanceDataSource _EVIDENCE_DATE_SHAPE_RE '
        '_TASK_ID_IN_REF_RE _active_execution_packet_tasks _archive_corpus_files _archive_reader '
        '_archive_reader_class _cache _declared_packet_checks _default_task_status_map '
        '_evidence_task_type_index _format_id_sequence_status _governance_table_cells _hot_fact_policy '
        '_hot_fact_source_plugin_scope _hot_status_cell_is_delivered _hot_task_ids_for_version '
        '_hot_task_is_delivered _hot_task_is_open _is_incomplete_task_status _is_nonactive_subsection '
        '_latest_published_release_fact _load_archive_module _markdown_section_by_prefix '
        '_parse_context_open_risks _print_sequential_id_check _resolve_archive_task_refs _review_checks '
        '_scan_unicode_line_separators _snapshot_fact_source_issues _split_governance_table_row '
        'check_change_triage check_commit_task_references check_cross_references check_decision_premise '
        'check_evidence_completeness check_gate_consistency check_hot_fact_source_consistency '
        'check_loop_role_skill_consistency check_protocol_compliance check_r1_completion_gate '
        'check_risk_escalation check_risk_mitigation_closure check_risk_mitigation_closure_with_archive '
        'check_risk_staleness check_sequential_ids check_snapshot_freshness check_structural_validity '
        'check_task_deadline check_tier_audit_completeness check_version_consistency '
        'cmd_check_cross_references cmd_check_hot_fact_source cmd_check_sequential_ids '
        'cmd_check_structural_validity expand_task_ids parse_active_risks parse_completed_task_ids '
        'parse_current_active_tasks parse_evidence_task_ids parse_impact_analysis_entries '
        'parse_impact_analysis_entries_with_exemptions parse_open_risks parse_task_status_map '
        'parse_tier_definitions premise_tracker re requires_impact_evidence risk_domain version_checks '
    ).split(),
    'governance_check_cli': (
        '_aggregate_check_summary _extract_summary_count _ordered_detail_items _print_check_summary '
        '_run_full_engine_checks _summary_detail_cap _summary_detail_char_limit _truncate_summary_detail '
        'cmd_check_governance io redirect_stdout sys '
    ).split(),
    'host_check_bindings': (
        '_anchor_date_or_none _append_mainstream_loading_common_doc_issues '
        '_append_mainstream_loading_overclaim_issues _append_missing_status_boundary_issues '
        '_append_pack_overclaim_issues _check_quote_sync_issues _copy_external_validation_surface '
        '_detect_gemini_auth_from_settings _detect_gemini_env_auth_sources '
        '_external_validation_canonical_hook_text _external_validation_plan_tracker '
        '_external_validation_read_text _external_validation_target_native_diagnostics _gemini_auth_preflight '
        '_gemini_settings_candidates _governance_pack_file_path _governance_pack_text_values '
        '_line_has_scoped_claim_negation _load_adapter_manifest _mainstream_loading_line_has_safe_negation '
        '_manifest_artifact_entries _matrix_status_for_manifest _opencode_config_candidates '
        '_opencode_model_scan _opencode_provider_model_preflight _parse_markdown_table_rows '
        '_prepare_external_validation_git _run_external_validation_command _run_opencode_probe_command '
        '_run_version_command _safe_env_present _sanitize_opencode_probe_text '
        '_validate_codex_runtime_e2e_claim _validate_gemini_auth_preflight_claim '
        '_validate_opencode_provider_model_preflight_claim _validate_runtime_capabilities '
        '_validate_runtime_e2e_block _write_external_validation_governance check_agent_activation '
        'check_agent_adapter_contract check_agent_team_review check_exploration_channels '
        'check_exploration_sample_advisories check_first_session_measurement check_governance_pack_status '
        'check_governance_packs check_mainstream_agent_loading check_profile_consistency '
        'check_readme_pack_guidance check_runtime_readiness_matrix cmd_check_agent_adapters '
        'cmd_check_agent_team cmd_check_dsh_boundary cmd_check_dsh_preset_compat cmd_check_dsh_preset_smoke '
        'cmd_check_exploration_channels cmd_check_first_session_measurement cmd_check_governance_packs '
        'cmd_check_loop_role_skills cmd_check_mainstream_agent_loading cmd_check_runtime_readiness_matrix '
        'cmd_dsh_doctor cmd_external_project_validation date datetime run_external_project_validation shutil '
    ).split(),
    'release_check_bindings': (
        '_archguard_exclusion_match _archguard_load_schema _archguard_normalized_lines '
        '_archguard_print_findings _archguard_severity _archguard_source_projection_pairs '
        '_collect_session_closure_events _contains_unnegated_phrase _exception_note '
        '_exception_registry_error_note _extract_json_version _extract_plan_workflow_version '
        '_extract_skill_version _generic_reviewer_cells _line_has_structured_status_negation '
        '_markdown_has_heading _markdown_section _markdown_table_row_by_first_cell _projection_hash '
        '_projection_source_files _projection_target_tracked_files _provenance_rows_for_governance '
        '_provenance_rows_from_report _release_docs_line_has_guard_context _release_exception_block '
        '_resolve_release_gate_timeout _risk_status_is_closed _run_git_lineage '
        '_run_release_validation_command _specialist_skill_owner_issues _tagged_release_replay_hint '
        '_target_fixture_file_is_checkable _validated_git_remote_name blocking_structural_issues '
        'build_required_files_from_manifest check_architecture_fact_source check_architecture_health '
        'check_ci_evidence check_complexity check_dsh_preset_smoke check_duplicate_code check_files '
        'check_governance_data_size check_injection_budget check_injection_contract '
        'check_manifest_consistency check_one_dot_zero_release_blockers check_projection_sync '
        'check_readme_claim_evidence_levels check_release_docs_coverage check_release_lineage '
        'check_release_readiness check_repository_navigation check_snippets check_technical_debt '
        'cmd_check_architecture_health cmd_check_complexity cmd_check_duplicate_code '
        'cmd_check_entry_bootstrap_sync cmd_check_governance_data_size cmd_check_governance_pack_status '
        'cmd_check_injection_contract cmd_check_projection_sync cmd_check_readme_pack_guidance '
        'cmd_check_release cmd_check_technical_debt cmd_check_version_consistency cmd_quality_tools '
        'cmd_release_ledger cmd_release_projection cmd_verify commit_checks emit_injection_budget_section '
        'injection_budget lock_issue_is_blocking projection_checks run_dsh_upgrade_regression_gates '
        'run_release_execution_gates structural_issue_is_blocking '
    ).split(),
    'workflow_composition': (
        'FACT_BASIS_RE M5_RECORD_DOC_DIRS PLUGIN_SCOPE_DIRS RepositoryContext UNGROUNDED_CLAIM_RE '
        '_ENGINE_COMMAND_DEFAULTS _RELEASE_COMMAND_BINDINGS _bind_ci_facts _bind_gate_command _bind_host_root '
        '_bind_manifest_access _bind_release_commands _bind_workflow_dsh _capability_registry '
        '_effective_engine_command _effective_release_command _evidence_domain _hot_facts '
        '_is_m5_record_doc_path _is_valid_string_list _workspace_checks check_m5_compliance '
        'check_m5_compliance_with_record_scope check_plugin_freshness check_projections check_untracked_files '
        'validate_release_ledger write_projections '
    ).split(),
    'workflow_context_bindings': (
        'CAPABILITY_CONTEXT_ALLOWED_STATUSES CAPABILITY_CONTEXT_DEGRADED_STATUSES CAPABILITY_CONTEXT_DOC_PATH '
        'CAPABILITY_CONTEXT_NO_OVERCLAIM_TOKENS CAPABILITY_CONTEXT_REQUIRED_FIELDS '
        'CAPABILITY_CONTEXT_TOOLS_PATH GOVERNANCE_CONTEXT_BLOCKED_MARKERS GOVERNANCE_CONTEXT_REQUIRED_FIELDS '
        'GOVERNANCE_CONTEXT_SNAPSHOT_SECTIONS HOST_CAPABILITY_CONTEXT_ALLOWED_STATUSES '
        'HOST_CAPABILITY_CONTEXT_BOUNDARY_TOKENS HOST_CAPABILITY_CONTEXT_FORBIDDEN_OVERCLAIMS '
        'HOST_CAPABILITY_CONTEXT_REQUIRED_BLOCKED_FACTS HOST_CAPABILITY_CONTEXT_REQUIRED_FIELDS '
        'HOST_CAPABILITY_CONTEXT_REQUIRED_SCENARIO_FIELDS HOST_CAPABILITY_CONTEXT_SCENARIOS '
        'HOST_CAPABILITY_CONTEXT_UNAVAILABLE_STATUSES PRODUCT_CODE_PATTERNS _STATUS_ID_TOKEN_RE '
        '_TERMINAL_CELL_DECORATIONS _WRITER_STATE_MARKER_CHAIN _capability_cli_registration_fact '
        '_capability_context_path _capability_file_fact _capability_host_id _capability_text_contains '
        '_context_file _context_git_toplevel _context_root _context_task _dedupe_context_items '
        '_empty_governance_context _extract_section _extract_task_title_from_line '
        '_host_capability_source_fact _host_context_capability _host_context_fact_contains '
        '_host_context_registry_capabilities _host_context_values _host_restricted_scenario '
        '_is_context_git_repo_root _is_context_product_file _last_marker_pos _normalize_task_status '
        '_parse_git_status_context_tasks _parse_plan_context_tasks _parse_recent_commit_context_facts '
        '_parse_snapshot_context_tasks _run_context_git _status_clean_cell _status_col_name '
        '_status_is_completed_cell _status_is_terminal_cell _status_is_writer_committed_cell _status_iso_date '
        '_status_next_steps _status_plugin_freshness _status_priority_rank _status_project_name '
        '_status_raw_dependency_ids _status_table_stream _status_task_stats _w7_terminal_assertion_positions '
        'build_delivery_trust_snapshot check_capability_context check_capability_registry '
        'check_governance_context check_host_capability_context cmd_capability_context '
        'cmd_check_host_capability_context cmd_governance_context cmd_status discover_capability_context '
        'discover_governance_context discover_host_capability_context parse_overview parse_project_config '
        'parse_recent_completed_tasks parse_recent_decisions parse_session_snapshot_carry_over_tasks '
        'parse_task_stats parse_task_table_rows task_row_update '
    ).split(),
    'workflow_gate_bindings': (
        'FLOW_UNIT_RUNTIME_STATE_REL GATES_PATH '
        'LIFECYCLE_PATH '
        'LIFECYCLE_REGISTRY_PATH '
        'STAGE_ORDER STAGE_SKILLS_ROOT STAGE_SKILL_ALIASES '
        'STAGE_SKILL_DIR_NAMES STATUS_ICONS _GATE_CHECK_BINDINGS _check_all_required_files_exist '
        '_check_completed_ratio _check_evidence_mentions _check_file_exists '
        '_check_g10_executable_optimization_items _check_g10_feedback_archived_classified '
        '_check_g10_issue_list_severity_status _check_g10_real_operation_data _check_g11_next_round_direction '
        '_check_g11_retro_complete _check_g11_rules_templates_backfilled _check_gate_execution_registry '
        '_check_governance_file_exists _check_out_of_scope _check_plan_has_priority '
        '_check_quantifiable_metrics _check_risk_has_closed _check_scope_boundary _check_snippet_in_file '
        '_check_stakeholders _check_version_consistency_heuristic _contains_all _contains_any '
        '_flow_unit_runtime_path _gate_check_result_from_definition _gate_execution_check_definition_issues '
        '_gate_execution_registry_contract_issues _has_line_with_all _iter_archive_aware_evidence_units '
        '_lifecycle_registry_manifest_issues _lifecycle_registry_text_values _line_has_issue_severity '
        '_line_has_issue_status_value _line_has_real_issue_item _load_lifecycle_registry '
        '_plan_row_is_inactive _read_archive_aware_governance_text _registered_gate_function '
        '_stage_name_from_skill_dir auto_judge_gate check_lifecycle_registry cmd_check_lifecycle_registry '
        'cmd_gate cmd_gate_check cmd_gates cmd_stage cmd_stages list_available_stages normalize_stage_name '
        'parse_gate_detail stage_skill_dir_name stage_skill_path '
    ).split(),
    'workflow_guard_bindings': (
        'REVIEW_MACHINE_ROW_MARKER _BOOTSTRAP_CHECK_TOOL '
        '_DEFERRED_LEDGER_FILENAME _EVIDENCE_MACHINE_ROW_FAMILIES '
        '_CompletionRecommendationInputs _LegacyReviewSources _RecommendationCommandInputs '
        '_completion_recommendation_inputs _recommendation_command_inputs '
        '_OPS_LEDGER_RECEIPT_ANCHOR _PLAN_TRACKER_ROW_EXPECTED_SHAPE '
        '_ROW_FAMILY_TEXT_SURFACES _TASK_ID_CELL_RE _WRITE_GUARD_STATE_FILENAME '
        '_WRITE_GUARD_STATE_SCHEMA_VERSION _WRITE_GUARD_STATE_TOOL _build_violation_detection '
        '_credential_index _evidence_machine_row_issues _extract_managed_row_records '
        '_extract_ops_ledger_records _judge_row_delta _legacy_parse_index_refs _load_write_guard_state '
        '_plan_tracker_task_row_issues _recommendation_snapshot_row_text _reconcile_row_families '
        '_review_input _review_reader _row_family_credential_ok _row_has_governance_store_machine_credential '
        '_rows_snapshot _stamp_deferred_observation _triage_write_structure_guard _write_guard_row_digest '
        '_write_guard_state_json _write_recommendation_snapshot check_agent_lock_consistency '
        'check_agent_locks_format check_archive_integrity check_completion_recommendation '
        'check_governance_write_shapes check_release_bootstrap_world cmd_agent_locks_acquire '
        'cmd_change_triage cmd_check_agent_locks cmd_check_archive_integrity cmd_check_plugin_freshness '
        'cmd_demand_source_revise cmd_enforcement_check cmd_enforcement_check_engine cmd_goal_bridge '
        'cmd_goal_bridge_engine cmd_governance_write_guard cmd_isolation_capability '
        'cmd_isolation_capability_engine cmd_isolation_lease_reclaim cmd_isolation_lease_reclaim_engine '
        'cmd_isolation_snapshot cmd_isolation_snapshot_engine cmd_isolation_status '
        'cmd_isolation_status_engine cmd_isolation_write cmd_isolation_write_engine cmd_next_candidates '
        'cmd_review_record cmd_task_priority_analysis cmd_write_guard_bootstrap pin_ledger '
        'run_release_bootstrap_converge state_path_seen '
    ).split(),
    'workflow_policy_bindings': (
        '_DELETED_POLICIES _HOST_POLICY_OWNERS _LAZY_PUBLIC_NAMES _PRODUCT_POLICY_OWNERS _host_policy '
        '_product_policy '
    ).split(),
    'workflow_project_roots': (
        'ARCHIVE_DECISIONS_DIR ARCHIVE_EVIDENCE_DIR ARCHIVE_INDEX_PATH ARCHIVE_RISKS_DIR ARCHIVE_TASKS_DIR '
        'EVIDENCE_PATH EXECUTION_PACKET_PATH GOVERNANCE_DIR HOST_PROJECT_ROOT INTERACTION_BOUNDARY_PATH '
        'PLUGIN_ROOT RISK_PATH ROOT SAMPLE_PATH SESSION_SNAPSHOT_PATH USER_INTERRUPTION_POLICY_TEMPLATE_PATH '
        '_apply_project_root_override _asset_governance_dir _asset_host_files _display_path _git_files '
        '_governance_dir _is_plugin_path _read_text_normalized _resolve_host_root _resolve_plugin_root '
        '_split_markdown_table_row _validate_project_root '
    ).split(),
    'workflow_report_selection': (
        'DEGRADED_FUSE_THRESHOLD _PLUGIN_PRODUCT_CHECK_IDS _PRODUCT_GATE_LABELS _full_check_results '
        '_host_plugin_roots_divergent _print_product_gate_skipped _product_gate_active check_evidence_quality '
        'check_fact_grounding check_governance_review_fallback_policy check_loop_wiring_call_sites '
        'check_m5_runtime_triggers check_review_closure check_review_coverage check_review_debt '
        'check_review_machine_provenance check_structured_evidence emit_evidence_completeness '
        'emit_evidence_quality emit_risk_escalation emit_risk_mitigation_closure emit_risk_staleness os '
        'release_unit_issues '
    ).split(),
    'workflow_runtime_bindings': (
        'AGENT_RUNTIME_E2E_PLATFORMS _RESOLVE_ENTRY_CANONICAL_MARKER _RESOLVE_ENTRY_REL '
        '_RESOLVE_EXIT_FILE_NOT_FOUND _RESOLVE_EXIT_OTHER _RESOLVE_EXIT_PYTHON_MISSING '
        '_RESOLVE_EXIT_STORE_STUB _RESOLVE_EXIT_TIMEOUT _RESOLVE_TIMEOUT_DEFAULT _RESOLVE_TIMEOUT_ENV '
        '_WEB_INSTALL_TIMEOUT_DEFAULT _WEB_INSTALL_TIMEOUT_ENV _agent_runtime_e2e_candidate_texts '
        '_agent_runtime_e2e_command_matrix _agent_runtime_e2e_prompt _classify_agent_runtime_blocked '
        '_cleanup_agent_runtime_process_tree _coerce_e2e_text _e2e_command_matrix _e2e_contract_checks '
        '_e2e_json_object _e2e_output _e2e_target_cwd_command_matrix _e2e_target_fixture_checks '
        '_evaluate_agent_runtime_e2e_command _evaluate_e2e_command _evaluate_e2e_contract_check '
        '_evaluate_e2e_target_fixture_check _extract_e2e_verify_failures _format_rollup _format_telemetry '
        '_has_all _is_non_placeholder_agent_runtime_value _is_valid_agent_runtime_mode '
        '_is_valid_agent_runtime_workflow_agent _normalize_e2e_verify_failure _parse_agent_runtime_e2e_fields '
        '_resolve_agent_runtime_command _resolve_positive_timeout _resolve_resolve_timeout '
        '_resolve_web_install_timeout _run_agent_runtime_e2e_subprocess _run_e2e_subprocess _truncate_log '
        '_valid_e2e_loop_view _validate_agent_runtime_e2e_passed _validate_e2e_cleanup _validate_e2e_gate_g99 '
        '_validate_e2e_gates _validate_e2e_governance_proxy _validate_e2e_status '
        '_validate_e2e_verify_known_failure _web_console_is_live _web_console_open_url _web_console_paths '
        '_web_console_probe _web_console_url _write_web_console_process cmd_agent_runtime_e2e '
        'cmd_check_flow_unit_runtime cmd_check_loop_health cmd_e2e_check cmd_gemini_auth_preflight cmd_loop '
        'cmd_loop_rollup cmd_loop_telemetry cmd_opencode_provider_preflight cmd_resolve_entry cmd_web_console '
        'webbrowser write_cli_json '
    ).split(),
}

_IMPORTED_EXPORTS = {
    'archguard_ratchet': (
        'cmd_archguard_ratchet '
    ).split(),
    'authority_ledger': (
        'cmd_authority_ledger '
    ).split(),
    'baseline_metadata': (
        'cmd_baseline_evaluate cmd_baseline_register '
    ).split(),
    'bootstrap_aggregate': (
        'cmd_governance_bootstrap '
    ).split(),
    'checks.architecture_health': (
        '_archguard_excluded _archguard_iter_code_files '
    ).split(),
    'checks.capability_registry': (
        'CAPABILITY_REGISTRY_ALLOWED_KINDS CAPABILITY_REGISTRY_ALLOWED_STATUSES '
        'CAPABILITY_REGISTRY_BOUNDARY_TOKENS CAPABILITY_REGISTRY_FORBIDDEN_OVERCLAIMS '
        'CAPABILITY_REGISTRY_PATH CAPABILITY_REGISTRY_REQUIRED_FIELDS CAPABILITY_REGISTRY_REQUIRED_KINDS '
        '_capability_registry_text_values cmd_check_capability_registry '
    ).split(),
    'checks.evidence_domain': (
        'SECRET_ASSIGNMENT_RE SECRET_FIELD_RE _FORENSIC_HEAD_RE _contains_secret_like _evidence_header_index '
        '_evidence_state_cells _extract_evidence_task_id _extract_structured_fact_json '
        '_is_active_evidence_state _is_audit_or_review_type _is_closed_evidence_state '
        '_is_product_code_location _is_review_evidence _parse_evidence_context_tasks '
        '_validate_structured_fact_payload parse_evidence_task_map '
    ).split(),
    'checks.injection_budget': (
        'BUDGET_TIER_POLICY ENTRY_TEMPLATE_MARKERS INJECTION_BUDGET_DEFAULT_PROFILE INJECTION_BUDGET_PROFILES '
        'INJECTION_BUDGET_SURFACES INJECTION_BUDGET_TOKENS INJECTION_SURFACE_SCOPE_FULL_FILE '
        'INJECTION_SURFACE_SCOPE_PERSONA_PREFIX INJECTION_SURFACE_SCOPE_TEMPLATE_BLOCK '
        'check_tool_return_budget cmd_check_injection_budget count_ascii_chars count_cjk_chars '
        'estimate_surface_tokens estimate_surface_tokens_host extract_marked_block '
        'extract_persona_prefix_from_template find_marker_line injection_budget_tier_gate '
        'load_injection_surface normalize_token_budget set_injection_budget_surface_profiles '
        'tokenizer_calibration '
    ).split(),
    'checks.manifest': (
        '_manifest_product_file_entries _manifest_requires_product_artifact_guards _path_to_label '
        'check_manifest_canonical_product_artifacts check_manifest_cleanup_scope '
        'cmd_check_manifest_consistency expand_manifest_to_canonical_set scan_actual_files '
        'scan_manifest_visible_files '
    ).split(),
    'checks.review_domain': (
        'DEGRADED_MARKERS DEGRADED_REVIEW_MARKERS FIX173_NAMING_NORMALIZATION_DATE M5_CHOICE_CONTEXT_WORDS '
        'M5_NOTIFICATION_PREFIXES M5_OPTION_MENU_RE M5_QUESTION_WORDS REQ107_MACHINE_PROVENANCE_DATE '
        'REVIEWER_ROLE_MARKERS REVIEW_FALLBACK_POLICY_OPTIONAL_FILES REVIEW_FALLBACK_POLICY_REQUIRED_FILES '
        'REVIEW_MACHINE_FILE_MARKER REVIEW_MAX_ROUNDS ROUTING_FILE_CANDIDATES SELF_REVIEW_AUTHOR_MARKERS '
        '_LEGACY_REVIEW_FILE_RE _M5_T2_PROXIMITY_LINES _REVIEW_APPROVAL_CONCLUSIONS '
        '_REVIEW_FALLBACK_FORBIDDEN_PATTERNS _REVIEW_FALLBACK_REQUIRED_SNIPPETS _REVIEW_ID_RE '
        '_REVIEW_NON_TERMINAL_ALIASES _REVIEW_TERMINAL_CONCLUSIONS _UNRESOLVED_BLOCKERS_KEY_RE '
        '_build_review_sequence _collect_live_review_sequences _count_degraded_reviews_for_task '
        '_entry_unresolved_blocker_evidence _extract_review_conclusion_from_text _is_post_review_exempt '
        '_merge_unresolved_blocker_evidence _normalize_review_conclusion _normalize_review_round '
        '_parse_review_coverage_details _parse_review_covered_tasks _parse_routing_post_review_table '
        '_parse_unresolved_blockers_fields _review_chain_attribution _review_entry_skip_reason '
        '_review_text_has_reviewer_marker _review_text_is_degraded _routing_post_review_for_task_type '
        '_segment_final_prose _strip_code_fences_and_tables _t2_has_proximate_choice_context '
        '_task_routing_exempt check_review_spawn_gap cmd_check_review_debt '
    ).split(),
    'checks.risk_domain': (
        '_ARCHIVE_FAMILY_RANGE_RE _ARCHIVE_RANGE_SPAN_CAP _ARCHIVE_RESOLVED_STATUS _resolve_shared '
        'is_risk_status_open '
    ).split(),
    'governance_cost': (
        'cmd_governance_cost_report '
    ).split(),
    'governance_store': (
        'cmd_decision_append cmd_evidence_append cmd_locks_amend cmd_locks_extend cmd_locks_release '
    ).split(),
    'hot_governance_facts': (
        '_contains_fix_token_or_range _extract_task_ids _find_table_row_by_first_cell '
        '_find_table_rows_with_cell _line_mentions_completed_range_as_pending _markdown_table_cells '
        '_normalize_agent_token _normalize_markdown_cell _parse_iso_date _status_cell_is_delivered '
        '_task_statuses_for_hot_source _version_row_text '
    ).split(),
    'pin_ledger': (
        'cmd_pins '
    ).split(),
    'premise_tracker': (
        'cmd_premise '
    ).split(),
    'task_row_update': (
        'cmd_task_row_update '
    ).split(),
}

_SHARED_IMPORTS = {
    'governance_check_bindings': (
        'Path '
    ).split(),
    'governance_check_cli': (
        're '
    ).split(),
    'release_check_bindings': (
        'Path _line_has_scoped_claim_negation version_checks '
    ).split(),
    'workflow_cli': (
        'DETERMINISTIC_SCAFFOLD_TYPES QUALITY_BUDGET_DIMENSIONS '
    ).split(),
    'workflow_composition': (
        'FIX_105_SNAPSHOT_DATE_RE _TASK_ID_IN_REF_RE _review_checks risk_domain '
    ).split(),
    'workflow_context_bindings': (
        'Path _is_valid_string_list _line_has_scoped_claim_negation re '
    ).split(),
    'workflow_gate_bindings': (
        'Path _is_valid_string_list _line_has_scoped_claim_negation '
        '_manifest_artifact_entries build_required_files_from_manifest '
    ).split(),
    'workflow_guard_bindings': (
        '_TASK_ID_IN_REF_RE _review_checks date datetime json premise_tracker re sys '
    ).split(),
    'workflow_project_roots': (
        'PLUGIN_SCOPE_DIRS Path _review_checks sys '
    ).split(),
    'workflow_report_selection': (
        '_DEFERRED_LEDGER_FILENAME check_agent_team_review check_capability_registry check_ci_evidence '
        'check_evidence_completeness check_m5_compliance_with_record_scope check_manifest_consistency '
        'check_untracked_files render_rb2_goal_contract_block '
    ).split(),
    'workflow_runtime_bindings': (
        'datetime os '
    ).split(),
}

_IMPORT_ALIASES = {
    '_extract_project_root_arg': 'resolve_entry:extract_project_root_arg',
    'argparse': 'argparse:',
    'ast': 'ast:',
    'authority_ledger': 'authority_ledger:',
    'baseline_metadata': 'baseline_metadata:',
    'bootstrap_aggregate': 'bootstrap_aggregate:',
    'enforcement': 'enforcement:',
    'execution_isolation': 'execution_isolation:',
    'fnmatch': 'fnmatch:',
    'goal_bridge': 'goal_bridge:',
    'governance_cost': 'governance_cost:',
    'governance_store': 'governance_store:',
    'hashlib': 'hashlib:',
    'importlib': 'importlib:',
    'json': 'json:',
    'locale': 'locale:',
    'signal': 'signal:',
    'subprocess': 'subprocess:',
    'tempfile': 'tempfile:',
    'time': 'time:',
}

_OWNERS = {name: module for module, names in _FAMILY_EXPORTS.items() for name in names}
_OWNERS.update(dict.fromkeys(("_LifecycleRegistryInputs", "_GateDefinitionInputs",
                              "_lifecycle_registry_inputs", "_gate_definition_inputs"), "workflow_gate_bindings"))
_IMPORTS = {name: module + ":" + name for module, names in _IMPORTED_EXPORTS.items() for name in names}
for name in ("_ENGINE_COMMAND_DEFAULTS", "_RELEASE_COMMAND_BINDINGS", "_bind_gate_command",
             "_bind_release_commands", "_bind_workflow_dsh"):
    _OWNERS.pop(name, None)
_SHARED_IMPORTS.setdefault("workflow_cli", []).extend(("_extract_project_root_arg", "sys"))
_IMPORTS.update(_IMPORT_ALIASES)
_IMPORTS.update({"_bind_gate_command": "governance_fact_cli:bind_gate_command",
                 "_bind_release_commands": "release_validation_cli:bind_release_commands",
                 "_bind_workflow_dsh": "host_loader_probes:bind_workflow_dsh"})
_IMPORTS.update({"main": "workflow_cli:main", "_build_cli_parser": "workflow_cli:build_runtime_parser",
                 "_dispatch_bootstrap_if_selected": "resolve_entry:_dispatch_bootstrap_if_selected"})
_DELETED = set()
_OVERRIDES = {}
_REGISTERED_OVERRIDES = {
    "cmd_check_dsh_preset_smoke", "cmd_check_dsh_preset_compat", "cmd_check_dsh_boundary",
    "cmd_dsh_doctor", "cmd_gate_check", "check_plugin_freshness", "cmd_check_plugin_freshness",
    "check_untracked_files", "check_m5_compliance_with_record_scope",
    "cmd_release_ledger", "cmd_release_projection", "cmd_quality_tools",
}
_ORIGINAL_COMMANDS = {}
_published_entry = None


class DeferredFamily:
    """A single named assembly module used by startup callbacks on first invocation."""

    def __init__(self, name):
        self.name = name

    def __getattr__(self, key):
        return getattr(import_module(self.name), key)


def names():
    return ((_OWNERS.keys() | _IMPORTS.keys() | policies._LAZY_PUBLIC_NAMES
             | {"_ENGINE_COMMAND_DEFAULTS", "_RELEASE_COMMAND_BINDINGS"})
            - _DELETED - policies._DELETED_POLICIES)


def read_public(name):
    if name in policies._LAZY_PUBLIC_NAMES:
        return policies.read_policy(name)
    if name in ("_ENGINE_COMMAND_DEFAULTS", "_RELEASE_COMMAND_BINDINGS"):
        release = {"cmd_release_ledger", "cmd_release_projection", "cmd_quality_tools"}
        group = release if name == "_RELEASE_COMMAND_BINDINGS" else _REGISTERED_OVERRIDES - release
        return {key: _ORIGINAL_COMMANDS[key] if key in _ORIGINAL_COMMANDS else read_public(key) for key in group}
    if name not in _DELETED:
        if name in _OVERRIDES:
            return _OVERRIDES[name]
        if name == "GovernanceDataSource":
            from governance_check_bindings import _archive_reader_class
            return _archive_reader_class()
        if name in _OWNERS:
            return getattr(import_module(_OWNERS[name]), name)
        if name in _IMPORTS:
            module, _, attr = _IMPORTS[name].partition(":")
            if not attr:
                return import_module(module)
            return getattr(__import__(module, fromlist=[attr]), attr)
    raise AttributeError(f"module 'verify_workflow' has no attribute {name!r}")


def effective_command(name, native):
    if name in _DELETED:
        if name == "check_plugin_freshness":
            raise NameError(f"name '{name}' is not defined", name=name)
        raise AttributeError(name)
    if name in _OVERRIDES and _OVERRIDES[name] is not _ORIGINAL_COMMANDS.get(name):
        return _OVERRIDES[name]
    return native


def public_binding(name):
    """Read the actual published Python binding, including an explicit caller override."""
    entry = _published_entry() if _published_entry is not None else None
    return getattr(entry, name) if entry is not None else read_public(name)


read_legacy_loader = public_binding


def temporary_public_host(root):
    """Scope the five host facts used to exercise public Result constructors."""
    from unittest.mock import patch
    import workflow_project_roots as paths

    entry = _published_entry() if _published_entry is not None else None
    governance = root / ".governance"
    return patch.multiple(entry if entry is not None else paths,
                          HOST_PROJECT_ROOT=root, GOVERNANCE_DIR=governance,
                          SAMPLE_PATH=governance / "plan-tracker.md",
                          EVIDENCE_PATH=governance / "evidence-log.md",
                          RISK_PATH=governance / "risk-log.md")


def _consumers(name):
    if name in _OWNERS:
        yield import_module(_OWNERS[name])
    for module, members in _SHARED_IMPORTS.items():
        if name in members:
            yield import_module(module)


def _assign(name, value):
    if name in policies._LAZY_PUBLIC_NAMES:
        policies.set_policy(name, value)
        return
    if name in _REGISTERED_OVERRIDES and name not in _ORIGINAL_COMMANDS and name not in _DELETED:
        _ORIGINAL_COMMANDS[name] = read_public(name)
    for consumer in _consumers(name):
        setattr(consumer, name, value)
    _DELETED.discard(name)
    if name in _IMPORTS or name in _REGISTERED_OVERRIDES or name == "GovernanceDataSource":
        _OVERRIDES[name] = value


def _remove(name):
    if name in policies._LAZY_PUBLIC_NAMES:
        policies.delete_policy(name)
        return
    value = read_public(name)
    if name in _REGISTERED_OVERRIDES:
        _ORIGINAL_COMMANDS.setdefault(name, value)
    for consumer in _consumers(name):
        if hasattr(consumer, name):
            delattr(consumer, name)
    _OVERRIDES.pop(name, None)
    _DELETED.add(name)


def bind_host_projection(entry):
    """Refresh only the real path attributes already exposed by a loaded shell."""
    global _published_entry
    from weakref import ref
    from workflow_project_roots import bind_public_paths
    current_entry = ref(entry)
    if entry.__name__ in ("verify_workflow", "__main__"):
        _published_entry = current_entry

    def update(paths):
        shell = current_entry()
        if shell is None:
            return
        local = ModuleType.__getattribute__(shell, "__dict__")
        for name, value in paths.items():
            if name in local or name in _DELETED:
                _DELETED.discard(name)
                local[name] = value

    bind_public_paths(update)


class PublicModule(ModuleType):
    """Route writes to the specific L6 readers that own a published name."""

    def __getattribute__(self, name):
        value = super().__getattribute__(name)
        if name != "__dict__":
            return value
        # Reflection asks for real local attributes. Most callers only need one
        # published function and therefore never import the rest of the surface.
        if not value.get("_reflected_exports"):
            value["_reflected_exports"] = True
            eager = names() - policies._LAZY_PUBLIC_NAMES - {"GovernanceDataSource"}
            for key in eager - value.keys():
                try:
                    value[key] = read_public(key)
                except (AttributeError, ImportError):
                    continue  # Optional exports can be absent from an installation.
        # Original policy access, including access from a command, materializes
        # that particular public attribute. Reflect the already loaded values.
        for key in policies.loaded_names() - value.keys():
            value[key] = policies.read_policy(key)
        owner = sys.modules.get("governance_check_bindings")
        if (owner is not None and "GovernanceDataSource" not in value
                and "GovernanceDataSource" not in _DELETED and hasattr(owner, "GovernanceDataSource")):
            value["GovernanceDataSource"] = owner.GovernanceDataSource
        return value

    def __getattr__(self, name):
        value = read_public(name)
        super().__setattr__(name, value)
        return value

    def __dir__(self):
        return sorted(super().__getattribute__("__dict__").keys() | names())

    def __setattr__(self, name, value):
        if name in ("main", "_build_cli_parser"):
            import workflow_cli
            target = "main" if name == "main" else "build_runtime_parser"
            setattr(workflow_cli, target, value)
            _DELETED.discard(name)
            super().__setattr__(name, value)
            return
        if name in _OWNERS or name in _IMPORTS or name in policies._LAZY_PUBLIC_NAMES:
            _assign(name, value)
            super().__setattr__(name, value)
        else:
            super().__setattr__(name, value)

    def __delattr__(self, name):
        if name in ("main", "_build_cli_parser"):
            import workflow_cli
            target = "main" if name == "main" else "build_runtime_parser"
            delattr(workflow_cli, target)
            _DELETED.add(name)
            super().__delattr__(name)
            return
        if name in _OWNERS or name in _IMPORTS or name in policies._LAZY_PUBLIC_NAMES:
            _remove(name)
            if name in super().__getattribute__("__dict__"):
                super().__delattr__(name)
        else:
            super().__delattr__(name)
