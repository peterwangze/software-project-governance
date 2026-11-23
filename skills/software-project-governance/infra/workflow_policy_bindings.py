"""Resolve historical public policy names from their declared owners."""





_HOST_POLICY_OWNERS = {
    **dict.fromkeys((
        'REQ108_RECOMMENDATION_DATE', 'RECO_ROW_MARKER', '_LEGACY_SNAPSHOT_MARKER',
        '_RECO_TASK_ID_RE', '_SNAPSHOT_REF_RE',
    ), 'recommendation_checks'),
    **dict.fromkeys(('_MARKDOWN_BOLD_SPAN_RE', '_TOO_BROAD_SCOPE_PHRASE_RE'), 'execution_packet_checks'),
    **dict.fromkeys(('_COMPLETED_STATUS_PREFIX', '_HOT_STATUS_STATE_COMMITTED', '_HOT_STATUS_STATE_LEGACY',
                     '_NONACTIVE_SUBSECTION_MARKERS'), 'plan_task_selection'),
    **dict.fromkeys((
        'GOVERNANCE_CONTEXT_EVIDENCE_UNFINISHED_MARKERS',
        'GOVERNANCE_CONTEXT_EVIDENCE_CLOSED_MARKERS',
        'GOVERNANCE_CONTEXT_EVIDENCE_TASK_HEADERS',
        'GOVERNANCE_CONTEXT_EVIDENCE_STATE_HEADERS',
    ), 'checks.evidence_domain'),
    **dict.fromkeys((
        '_GOVERNANCE_STORE_MARKER_PREFIX',
        '_EVIDENCE_MACHINE_CREDENTIAL_RE',
    ), 'write_guard_records'),
    **dict.fromkeys((
        'PRODUCT_SUCCESS_CONTRACT_REQUIRED_FIELDS',
        'PRODUCT_SUCCESS_PLACEHOLDER_RE',
        'PRODUCT_SUCCESS_PROCESS_ONLY_RE',
        'PRODUCT_SUCCESS_USER_OUTCOME_RE',
        'PRODUCT_SUCCESS_RUNNABLE_RE',
    ), 'delivery_contract_checks'),
    **dict.fromkeys((
        '_W7_TERMINAL_MARKERS',
        '_W7_ACTIVE_MARKERS',
        '_W7_TERMINAL_DATE_RE',
        '_WRITER_OP_ANCHOR_RE',
    ), 'plan_status'),
    **dict.fromkeys((
        'EXTERNAL_PROJECT_NATIVE_ENTRY_FILES', 'EXTERNAL_PROJECT_NATIVE_ENTRY_PATTERNS',
        'EXTERNAL_PROJECT_REQUIRED_INSTALLED_HOOKS', 'EXTERNAL_PROJECT_VALIDATION_BOUNDARY',
        'EXTERNAL_PROJECT_VALIDATION_COMMANDS',
    ), 'external_project_policy'),
    **dict.fromkeys((
        'ADAPTER_REQUIRED_KEYS', 'ADAPTER_RUNTIME_CAPABILITY_POLICY', 'MAINSTREAM_AGENT_ADAPTERS',
        'RUNTIME_CAPABILITY_KEYS', 'RUNTIME_CAPABILITY_STATUSES',
    ), 'adapter_contracts'),
    **dict.fromkeys((
        'FIRST_SESSION_MEASUREMENT_ALLOWED_STATUSES', 'FIRST_SESSION_MEASUREMENT_PATH',
        'RUNTIME_MATRIX_AGENT_IDS', 'RUNTIME_MATRIX_RESEARCH_ONLY_IDS', 'RUNTIME_READINESS_MATRIX_PATH',
    ), 'adapter_readiness'),
    **dict.fromkeys((
        'CHANNEL_ANCHOR_DATE_STRICT_RE', 'CHANNEL_DATE_ANCHOR_ADAPTERS', 'CHANNEL_EVIDENCE_DATE_RE',
        'CHANNEL_EVIDENCE_STALE_DAYS', 'CONSULT_DRAW_MARKER', 'EXPLORATION_CHANNEL_KEYS',
        'EXPLORATION_CHANNEL_STATUSES', 'EXPLORATION_SAMPLE_REPORTS', 'QUOTE_SYNC_ADAPTER_MANIFESTS',
    ), 'exploration_evidence'),
    **dict.fromkeys((
        'GOVERNANCE_PACKS_PATH', 'GOVERNANCE_PACK_BOUNDARY_TOKENS', 'GOVERNANCE_PACK_FORBIDDEN_OVERCLAIMS',
        'GOVERNANCE_PACK_IDS', 'GOVERNANCE_PACK_KNOWN_CHECKS', 'GOVERNANCE_PACK_PROFILE_IDS',
        'GOVERNANCE_PACK_RELEASE_BOUNDARY_PATH', 'GOVERNANCE_PACK_RELEASE_BOUNDARY_TOKENS',
        'GOVERNANCE_PACK_REQUIRED_FIELDS', 'GOVERNANCE_PACK_STATUS_BOUNDARY_TOKENS',
        'GOVERNANCE_PACK_STATUS_DOC_PATHS', 'GOVERNANCE_PACK_STATUS_FORBIDDEN_OVERCLAIMS',
        'README_PACK_GUIDANCE_REQUIRED_TOKENS',
    ), 'host_governance_packs'),
    **dict.fromkeys((
        'DSH_SMOKE_ATTRIBUTED_CONCURRENT_WRITES_RE', 'DSH_SMOKE_REAL_HOME_WRITES_RE',
        'DSH_SMOKE_RESULT_PASS_RE', 'DSH_UPGRADE_REGRESSION_LABEL',
    ), 'host_loader_probes'),
    **dict.fromkeys((
        'ADAPTER_CLAIM_REGISTRY', 'EVIDENCE_LEVEL_MARKER_RE', 'MAINSTREAM_AGENT_LOADING_ADAPTERS',
        'MAINSTREAM_AGENT_LOADING_BOUNDARY_TOKENS', 'MAINSTREAM_AGENT_LOADING_DOC_PATH',
        'MAINSTREAM_AGENT_LOADING_FORBIDDEN_CLAIM_TERMS', 'MAINSTREAM_AGENT_LOADING_FORBIDDEN_OVERCLAIMS',
        'MAINSTREAM_AGENT_LOADING_README_TOKENS', 'MAINSTREAM_AGENT_LOADING_REQUIRED_DOCS',
        'MAINSTREAM_AGENT_LOADING_REQUIREMENTS_TOKENS', 'MAINSTREAM_AGENT_LOADING_TIER1',
        'MAINSTREAM_AGENT_LOADING_TIER2',
    ), 'host_loading_claims'),
    **dict.fromkeys((
        '_KNOWN_VERIFY_FAILURE_SIGNATURES',
    ), 'product_fixture_validation'),
    **dict.fromkeys((
        'GEMINI_API_KEY_ENV_VARS', 'GEMINI_AUTH_REMEDIATION', 'GEMINI_GCA_CONFIG_ENV_VARS',
        'GEMINI_GCA_CREDENTIAL_ENV_VARS', 'GEMINI_VERTEX_CONFIG_ENV_VARS',
        'GEMINI_VERTEX_CREDENTIAL_ENV_VARS', 'OPENCODE_LEGAL_DEEPSEEK_MODELS',
        'OPENCODE_PROVIDER_MODEL_REMEDIATION',
    ), 'runtime_preflight'),
    **dict.fromkeys((
        'ACTIVE_AGENT_ROLES', 'LOOP_ROLE_SKILL_CONTRACTS', 'NAMED_REVIEWER_ROLES',
    ), 'team_activation'),
}


_PRODUCT_POLICY_OWNERS = {
    **dict.fromkeys((
        "ACCEPTANCE_CONTRACT_REQUIRED_FIELDS", "ACCEPTANCE_RUNNABLE_COMMAND_RE", "ACCEPTANCE_PASS_STATUSES",
        "ACCEPTANCE_NOT_RUN_STATUSES", "QUALITY_BUDGET_PASS_STATUSES", "QUALITY_BUDGET_PENDING_STATUSES",
        "QUALITY_BUDGET_EXEMPT_STATUSES", "QUALITY_BUDGET_VALIDATION_SIGNAL_RE", "QUALITY_BUDGET_WEAK_PROSE_RE",
        "TASK_PENDING_STATUS_MARKERS", "VERTICAL_SLICE_REQUIRED_FIELDS", "VERTICAL_SLICE_PASS_STATUSES",
        "VERTICAL_SLICE_PENDING_STATUSES", "VERTICAL_SLICE_DEMO_SIGNAL_RE", "VERTICAL_SLICE_USER_SIGNAL_RE",
        "VERTICAL_SLICE_BEHAVIOR_SIGNAL_RE", "VERTICAL_SLICE_TECH_LAYER_RE", "VERTICAL_SLICE_BROAD_SCOPE_RE",
        "VERTICAL_SLICE_WEAK_PROSE_RE",
    ), "delivery_contract_checks"),
    **dict.fromkeys((
        "DETERMINISTIC_SCAFFOLD_REQUIRED_SECTIONS", "DETERMINISTIC_SCAFFOLD_REQUIRED_QUALITY_DIMENSIONS",
        "DETERMINISTIC_SCAFFOLD_COMMAND_RE", "DETERMINISTIC_SCAFFOLD_SIGNAL_RE",
        "DETERMINISTIC_SCAFFOLD_WEAK_RE", "DETERMINISTIC_SCAFFOLD_BROAD_SCOPE_RE",
        "DETERMINISTIC_SCAFFOLD_SECTION_SIGNALS",
    ), "scaffold_contracts"),
    **dict.fromkeys((
        "INTERRUPTION_POLICY_REQUIRED_PHRASES", "INTERRUPTION_POLICY_REQUIRED_TEMPLATE_PHRASES",
        "INTERRUPTION_POLICY_REQUIRED_ASSUMPTION_FIELDS", "INTERRUPTION_POLICY_PLACEHOLDER_RE",
        "INTERRUPTION_POLICY_CRITICAL_TRIGGER_KEYS", "INTERRUPTION_POLICY_PACKET_CRITICAL_SIGNALS",
        "INTERRUPTION_POLICY_DEFAULT_EXAMPLES",
    ), "interruption_contracts"),
    **dict.fromkeys((
        "_DEFERRED_LEDGER_FILENAME", "_EVIDENCE_MACHINE_ROW_FAMILIES", "_OPS_LEDGER_RECEIPT_ANCHOR",
        "_PLAN_TRACKER_ROW_EXPECTED_SHAPE", "_ROW_FAMILY_TEXT_SURFACES", "_WRITE_GUARD_STATE_FILENAME",
        "_WRITE_GUARD_STATE_SCHEMA_VERSION", "_WRITE_GUARD_STATE_TOOL",
    ), "write_guard_contracts"),
    **dict.fromkeys((
        "LIFECYCLE_REGISTRY_ACTIVE_MODE", "LIFECYCLE_REGISTRY_DYNAMIC_MODE",
        "LIFECYCLE_REGISTRY_GATES", "LIFECYCLE_REGISTRY_STAGE_IDS",
        "LIFECYCLE_REGISTRY_REQUIRED_PROJECT_TYPES", "LIFECYCLE_REGISTRY_REQUIRED_PRESET_FIELDS",
        "LIFECYCLE_REGISTRY_GATE_POLICY_REQUIRED_FIELDS",
        "LIFECYCLE_REGISTRY_REQUIRED_GAME_STANDARDS",
        "LIFECYCLE_REGISTRY_REQUIRED_LIBRARY_STANDARDS", "LIFECYCLE_REGISTRY_RISK_CLAIMS",
        "LIFECYCLE_REGISTRY_FORBIDDEN_OVERCLAIMS",
    ), "lifecycle_rules"),
    **dict.fromkeys((
        "GATE_EXECUTION_REGISTRY_REQUIRED_FIELDS", "GATE_EXECUTION_REQUIRED_FIELDS",
        "GATE_EXECUTION_CHECK_REQUIRED_FIELDS", "GATE_EXECUTION_ALLOWED_SEVERITIES",
        "GATE_EXECUTION_ALLOWED_EXECUTORS", "GATE_EXECUTION_ALLOWED_FUNCTIONS",
    ), "gate_consistency"),
    "probe_quality_tools": "release.quality",
    "ARCHGUARD_DEFAULT_ROOT_RESIDUE": "architecture_diagnostics",
    "ARCHGUARD_HOOKS_REL": "architecture_diagnostics",
    "ARCHGUARD_LEDGER_REL": "architecture_diagnostics",
    "ARCHGUARD_SCHEMA_REL": "architecture_diagnostics",
    "BLOCKING_LOCK_ISSUE_TYPES": "plugin_assets",
    "GIT_LINEAGE_TIMEOUT_SECONDS": "release_provenance",
    "GIT_REMOTE_NAME_RE": "release_provenance",
    "INJECTION_CONTRACT_ANCHORS": "repository_projection",
    "INJECTION_CONTRACT_STAGED_ANCHORS": "repository_projection",
    "OPTIONAL_PROJECTION_FILES": "plugin_assets",
    "PLATFORM_ENTRY_FILES": "plugin_assets",
    "PROJECTION_SNIPPETS": "plugin_assets",
    "PROJECTION_SYNC_PATTERNS": "repository_projection",
    "REQUIRED_FILES": "plugin_assets",
    "REQUIRED_SNIPPETS": "plugin_assets",
    "VERSION_LINE_ANCHOR": "repository_projection",
    "WORKFLOW_SNIPPETS": "plugin_assets",
    "_RELEASE_GATE_TIMEOUT_DEFAULT": "release_execution",
    "_RELEASE_GATE_TIMEOUT_ENV": "release_execution",
}


_LAZY_PUBLIC_NAMES = _HOST_POLICY_OWNERS.keys() | _PRODUCT_POLICY_OWNERS.keys() | {"urllib"}


_DELETED_POLICIES = set()


def _host_policy(name):
    if name in _DELETED_POLICIES:
        raise NameError(f"name '{name}' is not defined", name=name) from None
    return read_policy(name)


_product_policy = _host_policy


_values = {}


def read_policy(name):
    if name in _DELETED_POLICIES:
        raise AttributeError(f"module 'verify_workflow' has no attribute {name!r}")
    if name not in _values:
        if name == "urllib":
            import urllib.request
            value = urllib
        else:
            from importlib import import_module
            owner = _HOST_POLICY_OWNERS.get(name) or _PRODUCT_POLICY_OWNERS[name]
            value = getattr(import_module(owner), name)
            if name == "REQUIRED_FILES":
                import workflow_project_roots as paths
                value = dict(value)
                value.update(paths._asset_host_files(paths._asset_governance_dir))
        _values[name] = value
    return _values[name]


def update_host_inventory(governance_dir):
    if "REQUIRED_FILES" in _values:
        from workflow_project_roots import _asset_host_files
        _values["REQUIRED_FILES"].update(_asset_host_files(governance_dir))


def set_policy(name, value):
    _DELETED_POLICIES.discard(name)
    _values[name] = value


def delete_policy(name):
    if name in _DELETED_POLICIES:
        raise AttributeError(name)
    _values.pop(name, None)
    _DELETED_POLICIES.add(name)


def loaded_names():
    return _values.keys()
