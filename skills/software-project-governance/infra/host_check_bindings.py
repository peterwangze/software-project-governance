"""Compose adapter, readiness and host-validation checks."""

import workflow_project_roots as paths
import workflow_policy_bindings as policies

from checks.capability_registry import _line_has_scoped_claim_negation
from checks.manifest import _manifest_artifact_entries
from checks.review_domain import check_agent_team_review
from datetime import date, datetime
import shutil


def _load_adapter_manifest(adapter_dir):
    from adapter_readiness import _load_adapter_manifest as run
    return run(adapter_dir, display_path=paths._display_path)


def _run_version_command(command):
    from runtime_preflight import _run_version_command as run
    return run(command, package_root=paths.ROOT)


def _parse_markdown_table_rows(content, section_title=None):
    from adapter_readiness import _parse_markdown_table_rows as run
    return run(content, section_title)


def _matrix_status_for_manifest(manifest):
    from adapter_readiness import _matrix_status_for_manifest as run
    return run(manifest)


def check_runtime_readiness_matrix(root=None):
    from adapter_readiness import check_runtime_readiness_matrix as run, ReadinessPlatforms
    return run(
        root, package_root=paths.ROOT, display_path=paths._display_path, load_adapter_manifest=_load_adapter_manifest,
        matrix_status_for_manifest=_matrix_status_for_manifest,
        parse_markdown_table_rows=_parse_markdown_table_rows,
        platforms=ReadinessPlatforms(
            mainstream_agent_adapters=policies._host_policy('MAINSTREAM_AGENT_ADAPTERS'),
            agent_ids=policies._host_policy('RUNTIME_MATRIX_AGENT_IDS'),
            research_only_ids=policies._host_policy('RUNTIME_MATRIX_RESEARCH_ONLY_IDS'),
        ),
    )


def check_first_session_measurement(root=None):
    from adapter_readiness import check_first_session_measurement as run
    return run(
        root, package_root=paths.ROOT,
        first_session_measurement_allowed_statuses=policies._host_policy('FIRST_SESSION_MEASUREMENT_ALLOWED_STATUSES'),
        display_path=paths._display_path, parse_markdown_table_rows=_parse_markdown_table_rows,
    )


def _governance_pack_text_values(value):
    from host_governance_packs import _governance_pack_text_values as run
    return run(value, governance_pack_text_values=_governance_pack_text_values)


def _governance_pack_file_path(entry):
    from host_governance_packs import _governance_pack_file_path as run
    return run(entry)


def check_governance_packs(root=None):
    from host_governance_packs import check_governance_packs as run, PackRules
    return run(
        root, package_root=paths.ROOT, display_path=paths._display_path,
        governance_pack_file_path=_governance_pack_file_path,
        governance_pack_text_values=_governance_pack_text_values,
        line_has_scoped_claim_negation=_line_has_scoped_claim_negation,
        manifest_artifact_entries=_manifest_artifact_entries,
        packs_rules=PackRules(
            boundary_tokens=policies._host_policy('GOVERNANCE_PACK_BOUNDARY_TOKENS'),
            forbidden_overclaims=policies._host_policy('GOVERNANCE_PACK_FORBIDDEN_OVERCLAIMS'),
            ids=policies._host_policy('GOVERNANCE_PACK_IDS'),
            known_checks=policies._host_policy('GOVERNANCE_PACK_KNOWN_CHECKS'),
            profile_ids=policies._host_policy('GOVERNANCE_PACK_PROFILE_IDS'),
            required_fields=policies._host_policy('GOVERNANCE_PACK_REQUIRED_FIELDS'),
        ),
    )


def check_readme_pack_guidance(root=None):
    from host_governance_packs import check_readme_pack_guidance as run
    return run(
        root, package_root=paths.ROOT, governance_pack_ids=policies._host_policy('GOVERNANCE_PACK_IDS'),
        readme_pack_guidance_required_tokens=policies._host_policy('README_PACK_GUIDANCE_REQUIRED_TOKENS'),
        display_path=paths._display_path, line_has_scoped_claim_negation=_line_has_scoped_claim_negation,
    )


def _mainstream_loading_line_has_safe_negation(lines, index, phrase):
    from host_loading_claims import _mainstream_loading_line_has_safe_negation as run
    return run(
        lines, index, phrase,
        mainstream_agent_loading_forbidden_claim_terms=policies._host_policy('MAINSTREAM_AGENT_LOADING_FORBIDDEN_CLAIM_TERMS'),
        mainstream_agent_loading_forbidden_overclaims=policies._host_policy('MAINSTREAM_AGENT_LOADING_FORBIDDEN_OVERCLAIMS'),
    )


def _append_mainstream_loading_overclaim_issues(failures, path, content, root):
    from host_loading_claims import _append_mainstream_loading_overclaim_issues as run, LoadingClaimBoundaries
    return run(
        failures, path, content, root, display_path=paths._display_path,
        line_has_scoped_claim_negation=_line_has_scoped_claim_negation,
        mainstream_loading_line_has_safe_negation=_mainstream_loading_line_has_safe_negation,
        claims=LoadingClaimBoundaries(
            forbidden_claim_terms=policies._host_policy('MAINSTREAM_AGENT_LOADING_FORBIDDEN_CLAIM_TERMS'),
            forbidden_overclaims=policies._host_policy('MAINSTREAM_AGENT_LOADING_FORBIDDEN_OVERCLAIMS'),
            tier2=policies._host_policy('MAINSTREAM_AGENT_LOADING_TIER2'),
        ),
    )


def _append_mainstream_loading_common_doc_issues(failures, path, content, root, *, require_boundary=True):
    from host_loading_claims import _append_mainstream_loading_common_doc_issues as run
    return run(failures, path, content, root, require_boundary=require_boundary, display_path=paths._display_path)


def check_mainstream_agent_loading(root=None):
    from host_loading_claims import check_mainstream_agent_loading as run, HostLoadingRules
    return run(
        root, package_root=paths.ROOT,
        append_mainstream_loading_common_doc_issues=_append_mainstream_loading_common_doc_issues,
        append_mainstream_loading_overclaim_issues=_append_mainstream_loading_overclaim_issues,
        display_path=paths._display_path, parse_markdown_table_rows=_parse_markdown_table_rows,
        loading=HostLoadingRules(
            adapters=policies._host_policy('MAINSTREAM_AGENT_LOADING_ADAPTERS'),
            readme_tokens=policies._host_policy('MAINSTREAM_AGENT_LOADING_README_TOKENS'),
            required_docs=policies._host_policy('MAINSTREAM_AGENT_LOADING_REQUIRED_DOCS'),
            requirements_tokens=policies._host_policy('MAINSTREAM_AGENT_LOADING_REQUIREMENTS_TOKENS'),
            tier1=policies._host_policy('MAINSTREAM_AGENT_LOADING_TIER1'),
            tier2=policies._host_policy('MAINSTREAM_AGENT_LOADING_TIER2'),
        ),
    )


def _append_pack_overclaim_issues(failures, path, content, root):
    from host_governance_packs import _append_pack_overclaim_issues as run
    return run(
        failures, path, content, root,
        governance_pack_status_forbidden_overclaims=policies._host_policy('GOVERNANCE_PACK_STATUS_FORBIDDEN_OVERCLAIMS'),
        display_path=paths._display_path, line_has_scoped_claim_negation=_line_has_scoped_claim_negation,
    )


def _append_missing_status_boundary_issues(failures, path, content, root):
    from host_governance_packs import _append_missing_status_boundary_issues as run
    return run(
        failures, path, content, root,
        governance_pack_status_boundary_tokens=policies._host_policy('GOVERNANCE_PACK_STATUS_BOUNDARY_TOKENS'),
        display_path=paths._display_path,
    )


def check_governance_pack_status(root=None):
    from host_governance_packs import check_governance_pack_status as run, PackReleaseBoundaries
    return run(
        root, package_root=paths.ROOT,
        append_missing_status_boundary_issues=_append_missing_status_boundary_issues,
        append_pack_overclaim_issues=_append_pack_overclaim_issues, display_path=paths._display_path,
        release=PackReleaseBoundaries(
            release_boundary_path=policies._host_policy('GOVERNANCE_PACK_RELEASE_BOUNDARY_PATH'),
            release_boundary_tokens=policies._host_policy('GOVERNANCE_PACK_RELEASE_BOUNDARY_TOKENS'),
            status_doc_paths=policies._host_policy('GOVERNANCE_PACK_STATUS_DOC_PATHS'),
        ),
    )


def _validate_runtime_e2e_block(root, manifest_path, runtime_e2e, field_name, allow_unsupported=False):
    from adapter_contracts import _validate_runtime_e2e_block as run
    return run(root, manifest_path, runtime_e2e, field_name, allow_unsupported, display_path=paths._display_path)


def _validate_runtime_capabilities(root, manifest_path, manifest):
    from adapter_contracts import _validate_runtime_capabilities as run, CapabilityRules
    return run(
        root, manifest_path, manifest, display_path=paths._display_path,
        capabilities_rules=CapabilityRules(
            policy=policies._host_policy('ADAPTER_RUNTIME_CAPABILITY_POLICY'),
            keys=policies._host_policy('RUNTIME_CAPABILITY_KEYS'),
            statuses=policies._host_policy('RUNTIME_CAPABILITY_STATUSES'),
        ),
    )


def _validate_codex_runtime_e2e_claim(root, manifest_path, runtime_e2e):
    from adapter_contracts import _validate_codex_runtime_e2e_claim as run
    return run(root, manifest_path, runtime_e2e, display_path=paths._display_path)


def _gemini_settings_candidates(home=None):
    from runtime_preflight import _gemini_settings_candidates as run
    return run(home)


def _safe_env_present(name, env=None):
    from runtime_preflight import _safe_env_present as run
    return run(name, env)


def _detect_gemini_auth_from_settings(path):
    from runtime_preflight import _detect_gemini_auth_from_settings as run
    return run(path)


def _detect_gemini_env_auth_sources(env=None):
    from runtime_preflight import _detect_gemini_env_auth_sources as run, CredentialVariables
    return run(
        env, safe_env_present=_safe_env_present,
        variables=CredentialVariables(
            api_key_env_vars=policies._host_policy('GEMINI_API_KEY_ENV_VARS'),
            gca_credential_env_vars=policies._host_policy('GEMINI_GCA_CREDENTIAL_ENV_VARS'),
            vertex_credential_env_vars=policies._host_policy('GEMINI_VERTEX_CREDENTIAL_ENV_VARS'),
        ),
    )


def _gemini_auth_preflight(env=None, home=None, which=shutil.which, version_runner=_run_version_command):
    import workflow_runtime_bindings as runtime_checks

    from runtime_preflight import _gemini_auth_preflight as run
    return run(
        env, home, which, version_runner, gemini_auth_remediation=policies._host_policy('GEMINI_AUTH_REMEDIATION'),
        detect_gemini_auth_from_settings=_detect_gemini_auth_from_settings,
        detect_gemini_env_auth_sources=_detect_gemini_env_auth_sources,
        gemini_settings_candidates=_gemini_settings_candidates, truncate_log=runtime_checks._truncate_log,
    )


def _validate_gemini_auth_preflight_claim(root, manifest_path, runtime_e2e):
    from adapter_contracts import _validate_gemini_auth_preflight_claim as run
    return run(root, manifest_path, runtime_e2e, display_path=paths._display_path)


def _run_opencode_probe_command(command, timeout=15):
    import workflow_runtime_bindings as runtime_checks

    from runtime_preflight import _run_opencode_probe_command as run
    return run(command, timeout, package_root=paths.ROOT, e2e_output=runtime_checks._e2e_output)


def _opencode_config_candidates(home=None, root=None):
    from runtime_preflight import _opencode_config_candidates as run
    return run(home, root, package_root=paths.ROOT)


def _sanitize_opencode_probe_text(text):
    import workflow_runtime_bindings as runtime_checks

    from runtime_preflight import _sanitize_opencode_probe_text as run
    return run(text, truncate_log=runtime_checks._truncate_log)


def _opencode_model_scan(text):
    from runtime_preflight import _opencode_model_scan as run
    return run(text, opencode_legal_deepseek_models=policies._host_policy('OPENCODE_LEGAL_DEEPSEEK_MODELS'))


def _opencode_provider_model_preflight(home=None, root=None, which=shutil.which, version_runner=_run_version_command, probe_runner=_run_opencode_probe_command, config_candidates=None):
    from runtime_preflight import _opencode_provider_model_preflight as run
    return run(
        home, root, which, version_runner, probe_runner, config_candidates,
        opencode_provider_model_remediation=policies._host_policy('OPENCODE_PROVIDER_MODEL_REMEDIATION'),
        opencode_config_candidates=_opencode_config_candidates, opencode_model_scan=_opencode_model_scan,
        sanitize_opencode_probe_text=_sanitize_opencode_probe_text,
    )


def _validate_opencode_provider_model_preflight_claim(root, manifest_path, runtime_e2e):
    from adapter_contracts import _validate_opencode_provider_model_preflight_claim as run
    return run(
        root, manifest_path, runtime_e2e,
        opencode_legal_deepseek_models=policies._host_policy('OPENCODE_LEGAL_DEEPSEEK_MODELS'),
        display_path=paths._display_path,
    )


def check_agent_adapter_contract(root=None, run_runtime=False):
    from adapter_contracts import check_agent_adapter_contract as run
    return run(
        root, run_runtime, package_root=paths.ROOT, adapter_required_keys=policies._host_policy('ADAPTER_REQUIRED_KEYS'),
        mainstream_agent_adapters=policies._host_policy('MAINSTREAM_AGENT_ADAPTERS'), display_path=paths._display_path,
        load_adapter_manifest=_load_adapter_manifest, run_version_command=_run_version_command,
        validate_codex_runtime_e2e_claim=_validate_codex_runtime_e2e_claim,
        validate_gemini_auth_preflight_claim=_validate_gemini_auth_preflight_claim,
        validate_opencode_provider_model_preflight_claim=_validate_opencode_provider_model_preflight_claim,
        validate_runtime_capabilities=_validate_runtime_capabilities,
        validate_runtime_e2e_block=_validate_runtime_e2e_block,
    )


def _check_quote_sync_issues():
    from exploration_evidence import _check_quote_sync_issues as run
    return run(
        package_root=paths.ROOT, consult_draw_marker=policies._host_policy('CONSULT_DRAW_MARKER'),
        quote_sync_adapter_manifests=policies._host_policy('QUOTE_SYNC_ADAPTER_MANIFESTS'),
    )


def _anchor_date_or_none(value):
    from exploration_evidence import _anchor_date_or_none as run
    return run(
        value, channel_anchor_date_strict_re=policies._host_policy('CHANNEL_ANCHOR_DATE_STRICT_RE'),
        timestamp_type=datetime,
    )


def check_exploration_channels(root=None):
    from exploration_evidence import check_exploration_channels as run, ChannelRules
    return run(
        root, package_root=paths.ROOT, anchor_date_or_none=_anchor_date_or_none, calendar_date=date,
        channel_rules=ChannelRules(
            dated_adapters=policies._host_policy('CHANNEL_DATE_ANCHOR_ADAPTERS'),
            evidence_date=policies._host_policy('CHANNEL_EVIDENCE_DATE_RE'),
            stale_days=policies._host_policy('CHANNEL_EVIDENCE_STALE_DAYS'),
            keys=policies._host_policy('EXPLORATION_CHANNEL_KEYS'),
            statuses=policies._host_policy('EXPLORATION_CHANNEL_STATUSES'),
            manifests=policies._host_policy('QUOTE_SYNC_ADAPTER_MANIFESTS'),
        ),
    )


def check_exploration_sample_advisories(root=None):
    from exploration_evidence import check_exploration_sample_advisories as run
    return run(root, package_root=paths.ROOT, exploration_sample_reports=policies._host_policy('EXPLORATION_SAMPLE_REPORTS'))


def check_agent_activation():
    import governance_check_bindings as governance_checks

    from team_activation import check_agent_activation as run
    return run(
        evidence_path=paths.EVIDENCE_PATH, plan_path=paths.SAMPLE_PATH,
        split_governance_table_row=governance_checks._split_governance_table_row, expand_task_ids=governance_checks.expand_task_ids,
    )


def check_profile_consistency():
    from team_activation import check_profile_consistency as run
    return run(plan_path=paths.SAMPLE_PATH)


def _external_validation_read_text(path):
    from external_project_diagnostics import read_text
    return read_text(path)


def _external_validation_canonical_hook_text(hook_name, root=None):
    from external_project_diagnostics import canonical_hook_text
    return canonical_hook_text(hook_name, paths.ROOT if root is None else root)


def _external_validation_plan_tracker(version):
    from external_project_validation import plan_tracker
    return plan_tracker(version)


def _write_external_validation_governance(workspace, target_facts):
    import release_check_bindings as release_checks

    from external_project_validation import write_governance
    version = release_checks._extract_skill_version(paths.ROOT / "skills/software-project-governance/SKILL.md")
    write_governance(workspace, target_facts, version or "unknown", _external_validation_plan_tracker)


def _copy_external_validation_surface(workspace):
    from external_project_validation import copy_surface
    return copy_surface(workspace, paths.ROOT, paths._git_files(["ls-files", "--cached"]))


def _prepare_external_validation_git(workspace):
    from external_project_validation import prepare_git
    return prepare_git(workspace)


def _run_external_validation_command(workspace, args, timeout=120):
    from external_project_validation import run_command
    return run_command(workspace, args, timeout=timeout)


def _external_validation_target_native_diagnostics(target):
    from external_project_diagnostics import target_native_diagnostics
    return target_native_diagnostics(
        target, entry_files=policies._host_policy('EXTERNAL_PROJECT_NATIVE_ENTRY_FILES'),
        entry_patterns=policies._host_policy('EXTERNAL_PROJECT_NATIVE_ENTRY_PATTERNS'),
        required_hooks=policies._host_policy('EXTERNAL_PROJECT_REQUIRED_INSTALLED_HOOKS'),
        read_text=_external_validation_read_text, canonical_hook_text=_external_validation_canonical_hook_text)


def run_external_project_validation(target, keep_workspace=False, workspace_parent=None, timeout=120):
    import external_project_validation as validation
    return validation.validate_project(
        target, keep_workspace, workspace_parent, timeout, inspect_target=_external_validation_target_native_diagnostics,
        copy_surface=_copy_external_validation_surface,
        write_governance=_write_external_validation_governance,
        prepare_git=_prepare_external_validation_git,
        run_command=_run_external_validation_command,
        commands=policies._host_policy('EXTERNAL_PROJECT_VALIDATION_COMMANDS'), boundary=policies._host_policy('EXTERNAL_PROJECT_VALIDATION_BOUNDARY'),
    )


def cmd_external_project_validation(args):
    from external_project_validation import run_cli
    return run_cli(args, run_external_project_validation)


def cmd_check_agent_adapters(args):
    from host_validation_cli import cmd_check_agent_adapters as run
    return run(args, check_agent_adapter_contract=check_agent_adapter_contract)


def cmd_check_exploration_channels(args):
    from exploration_evidence import cmd_check_exploration_channels as run
    return run(args, check_exploration_channels=check_exploration_channels)


def cmd_check_loop_role_skills(_args):
    import governance_check_bindings as governance_checks

    from host_validation_cli import cmd_check_loop_role_skills as run
    return run(_args, check_loop_role_skill_consistency=governance_checks.check_loop_role_skill_consistency)


def cmd_check_agent_team(args):
    from host_validation_cli import cmd_check_agent_team as run
    return run(args, check_agent_activation=check_agent_activation, check_agent_team_review=check_agent_team_review)


def cmd_check_dsh_preset_smoke(args):
    import release_check_bindings as release_checks

    from host_loader_probes import cmd_check_dsh_preset_smoke as run
    return run(args, smoke=release_checks.check_dsh_preset_smoke)


def cmd_check_dsh_preset_compat(args):
    from dsh_compat import cmd_check_dsh_preset_compat as run
    return run(args)


def cmd_check_dsh_boundary(args):
    from host_validation_cli import cmd_check_dsh_boundary as run
    return run(args)


def cmd_dsh_doctor(args):
    from host_validation_cli import cmd_dsh_doctor as run
    return run(args)


def cmd_check_runtime_readiness_matrix(args):
    from host_validation_cli import cmd_check_runtime_readiness_matrix as run
    return run(args, check_runtime_readiness_matrix=check_runtime_readiness_matrix)


def cmd_check_first_session_measurement(args):
    from host_validation_cli import cmd_check_first_session_measurement as run
    return run(args, check_first_session_measurement=check_first_session_measurement)


def cmd_check_governance_packs(args):
    from host_validation_cli import cmd_check_governance_packs as run
    return run(args, check_governance_packs=check_governance_packs)


def cmd_check_mainstream_agent_loading(args):
    from host_validation_cli import cmd_check_mainstream_agent_loading as run
    return run(args, check_mainstream_agent_loading=check_mainstream_agent_loading)
