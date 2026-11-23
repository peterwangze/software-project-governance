"""Compose lifecycle inventory, stage gates and registered judgment callbacks."""

import workflow_policy_bindings as policies

from checks.capability_registry import _line_has_scoped_claim_negation
from checks.manifest import _manifest_artifact_entries, build_required_files_from_manifest
from contracts import _is_valid_string_list
from pathlib import Path
import workflow_project_roots as paths


LIFECYCLE_REGISTRY_PATH = paths.ROOT / "skills/software-project-governance/core/lifecycle-registry.json"


FLOW_UNIT_RUNTIME_STATE_REL = Path(".governance/flow-unit-runtime.json")


class _LifecycleRegistryInputs:
    """Read each published lifecycle setting or callback at its original use site."""

    product_root = property(lambda self: paths.ROOT)
    gates = property(lambda self: policies._product_policy("LIFECYCLE_REGISTRY_GATES"))
    required_project_types = property(lambda self: policies._product_policy("LIFECYCLE_REGISTRY_REQUIRED_PROJECT_TYPES"))
    required_preset_fields = property(lambda self: policies._product_policy("LIFECYCLE_REGISTRY_REQUIRED_PRESET_FIELDS"))
    gate_policy_required_fields = property(lambda self: policies._product_policy("LIFECYCLE_REGISTRY_GATE_POLICY_REQUIRED_FIELDS"))
    required_game_standards = property(lambda self: policies._product_policy("LIFECYCLE_REGISTRY_REQUIRED_GAME_STANDARDS"))
    required_library_standards = property(lambda self: policies._product_policy("LIFECYCLE_REGISTRY_REQUIRED_LIBRARY_STANDARDS"))
    forbidden_overclaims = property(lambda self: policies._product_policy("LIFECYCLE_REGISTRY_FORBIDDEN_OVERCLAIMS"))
    risk_claims = property(lambda self: policies._product_policy("LIFECYCLE_REGISTRY_RISK_CLAIMS"))
    display_path = property(lambda self: paths._display_path)
    load_lifecycle_registry = property(lambda self: _load_lifecycle_registry)
    lifecycle_registry_manifest_issues = property(lambda self: _lifecycle_registry_manifest_issues)
    manifest_artifact_entries = property(lambda self: _manifest_artifact_entries)
    is_valid_string_list = property(lambda self: _is_valid_string_list)
    read_text_normalized = property(lambda self: paths._read_text_normalized)
    check_gate_execution_registry = property(lambda self: _check_gate_execution_registry)
    lifecycle_registry_text_values = property(lambda self: _lifecycle_registry_text_values)
    line_has_scoped_claim_negation = property(lambda self: _line_has_scoped_claim_negation)


_lifecycle_registry_inputs = _LifecycleRegistryInputs()


class _GateDefinitionInputs:
    """Read the policies and checkers used to validate a gate definition."""

    allowed_executors = property(lambda self: policies._product_policy("GATE_EXECUTION_ALLOWED_EXECUTORS"))
    allowed_functions = property(lambda self: policies._product_policy("GATE_EXECUTION_ALLOWED_FUNCTIONS"))
    allowed_severities = property(lambda self: policies._product_policy("GATE_EXECUTION_ALLOWED_SEVERITIES"))
    check_required_fields = property(lambda self: policies._product_policy("GATE_EXECUTION_CHECK_REQUIRED_FIELDS"))
    registry_required_fields = property(lambda self: policies._product_policy("GATE_EXECUTION_REGISTRY_REQUIRED_FIELDS"))
    required_fields = property(lambda self: policies._product_policy("GATE_EXECUTION_REQUIRED_FIELDS"))
    is_valid_string_list = property(lambda self: _is_valid_string_list)
    gate_execution_check_definition_issues = property(lambda self: _gate_execution_check_definition_issues)
    check_gate_execution_registry = property(lambda self: _check_gate_execution_registry)


_gate_definition_inputs = _GateDefinitionInputs()


def _lifecycle_registry_text_values(value):
    from lifecycle_rules import _lifecycle_registry_text_values as read
    return read(value, inputs=_lifecycle_registry_inputs)


def _load_lifecycle_registry(root=None):
    from lifecycle_rules import _load_lifecycle_registry as read
    return read(root, inputs=_lifecycle_registry_inputs)


def _lifecycle_registry_manifest_issues(root, registry_path, display):
    from lifecycle_rules import _lifecycle_registry_manifest_issues as read
    return read(root, registry_path, display, inputs=_lifecycle_registry_inputs)


def _gate_execution_check_definition_issues(check, check_label):
    from gate_consistency import _gate_execution_check_definition_issues as read
    return read(check, check_label, inputs=_gate_definition_inputs)


def _check_gate_execution_registry(registry, display, gate_id_set, project_type_hooks):
    from gate_consistency import _check_gate_execution_registry as read
    return read(registry, display, gate_id_set, project_type_hooks, inputs=_gate_definition_inputs)


def _gate_execution_registry_contract_issues(registry, display):
    from gate_consistency import _gate_execution_registry_contract_issues as read
    return read(registry, display, inputs=_gate_definition_inputs)


def check_lifecycle_registry(root=None, registry=None):
    from lifecycle_rules import check_lifecycle_registry as read
    return read(root, registry, inputs=_lifecycle_registry_inputs)


def _flow_unit_runtime_path(root=None):
    return (root or paths.HOST_PROJECT_ROOT) / FLOW_UNIT_RUNTIME_STATE_REL


GATES_PATH = paths.PLUGIN_ROOT / "skills" / "software-project-governance" / "core" / "stage-gates.md"


LIFECYCLE_PATH = paths.PLUGIN_ROOT / "skills" / "software-project-governance" / "core" / "lifecycle.md"


STAGE_SKILLS_ROOT = paths.PLUGIN_ROOT / "skills"


STAGE_ORDER = [
    "initiation", "research", "selection", "infrastructure",
    "architecture", "development", "testing", "ci-cd",
    "release", "operations", "maintenance",
]


STAGE_SKILL_ALIASES = {
    "infra": "infrastructure",
    "infrastructure": "infrastructure",
    "cicd": "ci-cd",
    "ci-cd": "ci-cd",
}


STAGE_SKILL_DIR_NAMES = {
    "infrastructure": "stage-infra",
    "ci-cd": "stage-cicd",
}


STATUS_ICONS = {
    "passed": "[PASS]",
    "passed-on-entry": "[ENTRY]",
    "blocked": "[BLOCK]",
    "pending": "[????]",
}


def parse_gate_detail(gate_id):
    from governance_views import parse_gate_detail as read
    return read(gate_id, gates_path=GATES_PATH)


def normalize_stage_name(stage_name):
    from governance_views import normalize_stage_name as read
    return read(stage_name, aliases=STAGE_SKILL_ALIASES)


def stage_skill_dir_name(stage_name):
    from governance_views import stage_skill_dir_name as read
    return read(stage_name, directories=STAGE_SKILL_DIR_NAMES, normalize=normalize_stage_name)


def stage_skill_path(stage_name):
    from governance_views import stage_skill_path as read
    return read(stage_name, stages_root=STAGE_SKILLS_ROOT, directory_name=stage_skill_dir_name)


def _stage_name_from_skill_dir(dirname):
    from governance_views import _stage_name_from_skill_dir as read
    return read(dirname, directories=STAGE_SKILL_DIR_NAMES, normalize=normalize_stage_name)


def list_available_stages():
    from governance_views import list_available_stages as read
    return read(
        stage_order=STAGE_ORDER,
        stages_root=STAGE_SKILLS_ROOT,
        skill_path=stage_skill_path,
        stage_name=_stage_name_from_skill_dir)


def cmd_gate(args):
    """Inspect the scoped gate and its evidence, without granting authorization."""
    return cmd_gates(args)


def cmd_gates(args):
    from status_cli import cmd_gates as read
    return read(args, host_root=paths.HOST_PROJECT_ROOT)


def cmd_stage(args):
    from status_cli import cmd_stage as read
    return read(args, normalize=normalize_stage_name, skill_path=stage_skill_path)


def cmd_stages(args):
    from status_cli import cmd_stages as read
    return read(args, stages=list_available_stages)


def _check_file_exists(relative_path, label):
    from gate_judgment import _check_file_exists as run
    return run(relative_path, label, product_root=paths.ROOT)


def _check_snippet_in_file(relative_path, snippet, label):
    from gate_judgment import _check_snippet_in_file as run
    return run(relative_path, snippet, label, product_root=paths.ROOT)


def _check_all_required_files_exist():
    from gate_judgment import _check_all_required_files_exist as run
    return run(required_files=lambda: policies._product_policy("REQUIRED_FILES"),
               build_required_files_from_manifest=build_required_files_from_manifest)


def _check_governance_file_exists(filename):
    from gate_judgment import _check_governance_file_exists as run
    return run(filename, governance_dir=paths.GOVERNANCE_DIR)


def _check_quantifiable_metrics():
    from gate_judgment import _check_quantifiable_metrics as run
    return run(plan_path=paths.SAMPLE_PATH)


def _check_scope_boundary():
    from gate_judgment import _check_scope_boundary as run
    return run(plan_path=paths.SAMPLE_PATH)


def _check_stakeholders():
    from gate_judgment import _check_stakeholders as run
    return run(plan_path=paths.SAMPLE_PATH)


def _check_out_of_scope():
    from gate_judgment import _check_out_of_scope as run
    return run(plan_path=paths.SAMPLE_PATH)


def _check_completed_ratio(min_ratio=0.5):
    from gate_judgment import _check_completed_ratio as run
    return run(min_ratio, plan_path=paths.SAMPLE_PATH)


def _check_evidence_mentions(keyword, label):
    from gate_judgment import _check_evidence_mentions as run
    return run(keyword, label, evidence_path=paths.EVIDENCE_PATH)


def _read_archive_aware_governance_text(include=()):
    import governance_check_bindings as governance_checks

    from gate_judgment import _read_archive_aware_governance_text as run
    return run(include, data_source=governance_checks._archive_reader)


def _contains_all(text, keywords):
    from gate_judgment import _contains_all as run
    return run(text, keywords)


def _contains_any(text, keywords):
    from gate_judgment import _contains_any as run
    return run(text, keywords)


def _has_line_with_all(text, keyword_groups):
    from gate_judgment import _has_line_with_all as run
    return run(text, keyword_groups)


def _iter_archive_aware_evidence_units():
    import governance_check_bindings as governance_checks

    from gate_judgment import _iter_archive_aware_evidence_units as run
    return run(data_source=governance_checks._archive_reader)


def _line_has_issue_severity(line):
    from gate_judgment import _line_has_issue_severity as run
    return run(line)


def _line_has_issue_status_value(line):
    from gate_judgment import _line_has_issue_status_value as run
    return run(line)


def _line_has_real_issue_item(line):
    from gate_judgment import _line_has_real_issue_item as run
    return run(line)


def _plan_row_is_inactive(parts):
    from gate_judgment import _plan_row_is_inactive as run
    return run(parts)


def _check_g10_real_operation_data():
    import governance_check_bindings as governance_checks

    from gate_judgment import _check_g10_real_operation_data as run
    return run(data_source=governance_checks._archive_reader)


def _check_g10_feedback_archived_classified():
    import governance_check_bindings as governance_checks

    from gate_judgment import _check_g10_feedback_archived_classified as run
    return run(data_source=governance_checks._archive_reader)


def _check_g10_issue_list_severity_status():
    import governance_check_bindings as governance_checks

    from gate_judgment import _check_g10_issue_list_severity_status as run
    return run(data_source=governance_checks._archive_reader)


def _check_g10_executable_optimization_items():
    import governance_check_bindings as governance_checks

    from gate_judgment import _check_g10_executable_optimization_items as run
    return run(data_source=governance_checks._archive_reader)


def _check_g11_retro_complete():
    import governance_check_bindings as governance_checks

    from gate_judgment import _check_g11_retro_complete as run
    return run(data_source=governance_checks._archive_reader)


def _check_g11_rules_templates_backfilled():
    import governance_check_bindings as governance_checks

    from gate_judgment import _check_g11_rules_templates_backfilled as run
    return run(data_source=governance_checks._archive_reader)


def _check_g11_next_round_direction():
    from gate_judgment import _check_g11_next_round_direction as run
    return run(plan_path=paths.SAMPLE_PATH, split_markdown_table_row=paths._split_markdown_table_row)


def _check_risk_has_closed(label='关键缺陷'):
    from gate_judgment import _check_risk_has_closed as run
    return run(label, risk_path=paths.RISK_PATH)


def _check_plan_has_priority(priority='P0'):
    from gate_judgment import _check_plan_has_priority as run
    return run(priority, plan_path=paths.SAMPLE_PATH)


def _check_version_consistency_heuristic():
    import release_check_bindings as release_checks

    from gate_judgment import _check_version_consistency_heuristic as check
    return check(product_root=paths.ROOT, extract_skill_version=release_checks._extract_skill_version,
                 skill_file=lambda: paths.ROOT / "skills/software-project-governance/SKILL.md",
                 changelog_file=lambda: paths.ROOT / "project/CHANGELOG.md")


_GATE_CHECK_BINDINGS = {
    'check_quantifiable_metrics': lambda: _check_quantifiable_metrics,
    'check_scope_boundary': lambda: _check_scope_boundary,
    'check_stakeholders': lambda: _check_stakeholders,
    'check_out_of_scope': lambda: _check_out_of_scope,
    'check_all_required_files_exist': lambda: _check_all_required_files_exist,
    'check_g10_real_operation_data': lambda: _check_g10_real_operation_data,
    'check_g10_feedback_archived_classified': lambda: _check_g10_feedback_archived_classified,
    'check_g10_issue_list_severity_status': lambda: _check_g10_issue_list_severity_status,
    'check_g10_executable_optimization_items': lambda: _check_g10_executable_optimization_items,
    'check_g11_retro_complete': lambda: _check_g11_retro_complete,
    'check_g11_rules_templates_backfilled': lambda: _check_g11_rules_templates_backfilled,
    'check_g11_next_round_direction': lambda: _check_g11_next_round_direction,
    'check_risk_has_closed': lambda: _check_risk_has_closed,
    'check_version_consistency_heuristic': lambda: _check_version_consistency_heuristic,
}


def _registered_gate_function(name):
    binding = _GATE_CHECK_BINDINGS.get(name)
    try:
        return binding() if binding is not None else None
    except NameError:
        return None


def _gate_check_result_from_definition(check_definition):
    from gate_judgment import _gate_check_result_from_definition as run
    return run(check_definition, evidence_path=paths.EVIDENCE_PATH, product_root=paths.ROOT, plan_path=paths.SAMPLE_PATH,
               registered_gate_function=_registered_gate_function)


def auto_judge_gate(gate_id, unit_id=None):
    from gate_judgment import auto_judge_gate as run

    def validate_registry(registry):
        path = paths._display_path(LIFECYCLE_REGISTRY_PATH, paths.ROOT)
        return _gate_execution_registry_contract_issues(registry, path)

    return run(gate_id, unit_id, parse_gate_detail=parse_gate_detail,
               load_lifecycle_registry=lambda: _load_lifecycle_registry(), validate_registry=validate_registry,
               gate_check_result_from_definition=lambda definition: _gate_check_result_from_definition(definition))


def cmd_gate_check(args):
    from governance_fact_cli import cmd_gate_check as run
    return run(args)


def cmd_check_lifecycle_registry(args):
    from lifecycle_rules import cmd_check_lifecycle_registry as run
    return run(
        args, load_lifecycle_registry=lambda: _load_lifecycle_registry(),
        check_lifecycle_registry=lambda registry: check_lifecycle_registry(registry=registry),
    )
