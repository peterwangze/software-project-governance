"""Compose delivery goals, execution packets and contract checks."""

import workflow_policy_bindings as policies

from checks.evidence_domain import render_rb2_goal_contract_block
from contracts import (
    DETERMINISTIC_SCAFFOLD_TYPES, EXECUTION_PACKET_REQUIRED_FIELDS, QUALITY_BUDGET_DIMENSIONS,
)
from pathlib import Path
import workflow_project_roots as paths


FIRST_RUN_DEMO_REQUIRED_FIELDS = ["Work units", "State", "Next action"]


FIRST_RUN_DEMO_REQUIRED_MARKERS = ["Delivery Trust Snapshot", "demo-delivery", "demo-export",
                                   "totals match", "loop-evidence/", "local/demo-only"]


def render_delivery_trust_snapshot(snapshot):
    from governance_views import render_delivery_trust_snapshot as read
    return read(snapshot)


def build_first_run_demo_snapshot():
    import workflow_context_bindings as context_checks

    from governance_views import build_first_run_demo_snapshot as read
    return read(context_checks.build_delivery_trust_snapshot)


def assert_first_run_demo_snapshot(snapshot, rendered_text=None):
    from governance_views import assert_first_run_demo_snapshot as read
    return read(
        snapshot, rendered_text,
        required_fields=FIRST_RUN_DEMO_REQUIRED_FIELDS,
        required_markers=FIRST_RUN_DEMO_REQUIRED_MARKERS,
        render=render_delivery_trust_snapshot,
    )


def cmd_first_run_demo(args):
    from status_cli import cmd_first_run_demo as read
    return read(
        args,
        build_snapshot=build_first_run_demo_snapshot,
        validate_snapshot=assert_first_run_demo_snapshot,
        render=render_delivery_trust_snapshot,
        required_fields=FIRST_RUN_DEMO_REQUIRED_FIELDS,
    )


def check_commit_scope(limit=20):
    from checks.commit import check_commit_scope as run
    return run(limit, product_root=paths.ROOT)


def _plan_hot_tracker_task_statuses():
    from plan_task_selection import _plan_hot_tracker_task_statuses as run
    return run(plan_path=paths.SAMPLE_PATH)


def _hot_status_completion_state(status):
    import workflow_context_bindings as context_checks

    from plan_task_selection import _hot_status_completion_state as run
    return run(status, status_clean_cell=context_checks._status_clean_cell,
               status_is_writer_committed_cell=context_checks._status_is_writer_committed_cell)


def _current_release_task_ids():
    import governance_check_bindings as governance_checks

    from plan_task_selection import _current_release_task_ids as run
    return run(plan_path=paths.SAMPLE_PATH, expand_task_ids=governance_checks.expand_task_ids)


def _normalize_priority(value):
    from plan_task_selection import _normalize_priority as run
    return run(value)


def _task_priority_from_table_parts(parts):
    from plan_task_selection import _task_priority_from_table_parts as run
    return run(parts)


def check_goal_alignment():
    import governance_check_bindings as governance_checks
    import workflow_context_bindings as context_checks

    from plan_impact import check_goal_alignment as run
    return run(parse_impact_analysis_entries_with_exemptions=lambda: governance_checks.parse_impact_analysis_entries_with_exemptions(),
               parse_project_config=context_checks.parse_project_config)


def check_user_impact():
    import governance_check_bindings as governance_checks

    from plan_impact import check_user_impact as run
    return run(product_root=paths.ROOT,
               parse_impact_analysis_entries_with_exemptions=lambda: governance_checks.parse_impact_analysis_entries_with_exemptions())


def _current_release_impact_entries():
    import governance_check_bindings as governance_checks

    from plan_impact import _current_release_impact_entries as run
    return run(current_release_task_ids=_current_release_task_ids,
               parse_impact_analysis_entries_with_exemptions=lambda: governance_checks.parse_impact_analysis_entries_with_exemptions())


def _read_execution_packet_document(path, *, missing_ok=False):
    from execution_packet_checks import _read_execution_packet_document as run
    return run(path, missing_ok=missing_ok)


def current_execution_packet_reader():
    """Resolve the replaceable packet reader only when a goal command asks for it."""
    return _load_execution_packets


def _load_execution_packets(path=None):
    from execution_packet_checks import _load_execution_packets as run
    return run(path, packet_path_now=lambda: paths.EXECUTION_PACKET_PATH, read_document=_read_execution_packet_document)


def _execution_packet_field_issues(packet):
    from execution_packet_checks import _execution_packet_field_issues as run
    return run(packet, required_fields=lambda: EXECUTION_PACKET_REQUIRED_FIELDS)


def _strip_markdown_bold_markers(text):
    from execution_packet_checks import _strip_markdown_bold_markers as run
    return run(text, span_pattern=policies._host_policy("_MARKDOWN_BOLD_SPAN_RE"))


def _is_too_broad_scope_text(text):
    from execution_packet_checks import _is_too_broad_scope_text as run
    return run(text, strip_markers=_strip_markdown_bold_markers,
               phrase_search=lambda value: policies._host_policy("_TOO_BROAD_SCOPE_PHRASE_RE").search(value))


def _validate_execution_packet(task, packet):
    from execution_packet_checks import _validate_execution_packet as run
    return run(task, packet, field_issues=_execution_packet_field_issues,
               broad_scope=lambda value: _is_too_broad_scope_text(value),
               placeholder_search=lambda value: policies._host_policy("PRODUCT_SUCCESS_PLACEHOLDER_RE").search(value))


DETERMINISTIC_SCAFFOLD_DIR = paths.ROOT / "skills/software-project-governance/core/templates/deterministic-scaffolds"


def _product_success_policy():
    from delivery_contract_checks import ProductSuccessPolicy
    return ProductSuccessPolicy(
        required_fields=policies._host_policy("PRODUCT_SUCCESS_CONTRACT_REQUIRED_FIELDS"),
        placeholder=policies._host_policy("PRODUCT_SUCCESS_PLACEHOLDER_RE"),
        process_only_metric=_is_process_only_product_success_metric,
        user_outcome=policies._host_policy("PRODUCT_SUCCESS_USER_OUTCOME_RE"),
        runnable=policies._host_policy("PRODUCT_SUCCESS_RUNNABLE_RE"),
    )


def _acceptance_policy():
    from delivery_contract_checks import AcceptancePolicy
    return AcceptancePolicy(
        required_fields=policies._product_policy("ACCEPTANCE_CONTRACT_REQUIRED_FIELDS"),
        runnable_command=policies._product_policy("ACCEPTANCE_RUNNABLE_COMMAND_RE"),
        pass_statuses=policies._product_policy("ACCEPTANCE_PASS_STATUSES"),
        not_run_statuses=policies._product_policy("ACCEPTANCE_NOT_RUN_STATUSES"),
        placeholder=policies._host_policy("PRODUCT_SUCCESS_PLACEHOLDER_RE"),
    )


def _quality_budget_policy():
    from delivery_contract_checks import QualityBudgetPolicy
    return QualityBudgetPolicy(
        dimensions=QUALITY_BUDGET_DIMENSIONS,
        pass_statuses=policies._product_policy("QUALITY_BUDGET_PASS_STATUSES"),
        pending_statuses=policies._product_policy("QUALITY_BUDGET_PENDING_STATUSES"),
        exempt_statuses=policies._product_policy("QUALITY_BUDGET_EXEMPT_STATUSES"),
        validation_signal=policies._product_policy("QUALITY_BUDGET_VALIDATION_SIGNAL_RE"),
        weak_prose=policies._product_policy("QUALITY_BUDGET_WEAK_PROSE_RE"),
        placeholder=policies._host_policy("PRODUCT_SUCCESS_PLACEHOLDER_RE"),
        pending_task=_is_task_pending_status_allowed,
    )


def _vertical_slice_policy():
    from delivery_contract_checks import VerticalSlicePolicy
    return VerticalSlicePolicy(
        required_fields=policies._product_policy("VERTICAL_SLICE_REQUIRED_FIELDS"),
        pass_statuses=policies._product_policy("VERTICAL_SLICE_PASS_STATUSES"),
        pending_statuses=policies._product_policy("VERTICAL_SLICE_PENDING_STATUSES"),
        demo_signal=policies._product_policy("VERTICAL_SLICE_DEMO_SIGNAL_RE"),
        user_signal=policies._product_policy("VERTICAL_SLICE_USER_SIGNAL_RE"),
        behavior_signal=policies._product_policy("VERTICAL_SLICE_BEHAVIOR_SIGNAL_RE"),
        tech_layer=policies._product_policy("VERTICAL_SLICE_TECH_LAYER_RE"),
        broad_scope=policies._product_policy("VERTICAL_SLICE_BROAD_SCOPE_RE"),
        weak_prose=policies._product_policy("VERTICAL_SLICE_WEAK_PROSE_RE"),
        weak_quality_prose=policies._product_policy("QUALITY_BUDGET_WEAK_PROSE_RE"),
        placeholder=policies._host_policy("PRODUCT_SUCCESS_PLACEHOLDER_RE"),
        pending_task=_is_task_pending_status_allowed,
    )


def _scaffold_policy():
    from scaffold_contracts import ScaffoldPolicy
    return ScaffoldPolicy(
        types=DETERMINISTIC_SCAFFOLD_TYPES,
        sections=policies._product_policy("DETERMINISTIC_SCAFFOLD_REQUIRED_SECTIONS"),
        quality_dimensions=policies._product_policy("DETERMINISTIC_SCAFFOLD_REQUIRED_QUALITY_DIMENSIONS"),
        command=policies._product_policy("DETERMINISTIC_SCAFFOLD_COMMAND_RE"),
        signal=policies._product_policy("DETERMINISTIC_SCAFFOLD_SIGNAL_RE"),
        weak=policies._product_policy("DETERMINISTIC_SCAFFOLD_WEAK_RE"),
        broad_scope=policies._product_policy("DETERMINISTIC_SCAFFOLD_BROAD_SCOPE_RE"),
        section_signals=policies._product_policy("DETERMINISTIC_SCAFFOLD_SECTION_SIGNALS"),
    )


def _interruption_policy():
    from interruption_contracts import InterruptionPolicy
    return InterruptionPolicy(
        required_phrases=policies._product_policy("INTERRUPTION_POLICY_REQUIRED_PHRASES"),
        template_phrases=policies._product_policy("INTERRUPTION_POLICY_REQUIRED_TEMPLATE_PHRASES"),
        assumption_fields=policies._product_policy("INTERRUPTION_POLICY_REQUIRED_ASSUMPTION_FIELDS"),
        placeholder=policies._product_policy("INTERRUPTION_POLICY_PLACEHOLDER_RE"),
        critical_keys=policies._product_policy("INTERRUPTION_POLICY_CRITICAL_TRIGGER_KEYS"),
        packet_signals=policies._product_policy("INTERRUPTION_POLICY_PACKET_CRITICAL_SIGNALS"),
        examples=policies._product_policy("INTERRUPTION_POLICY_DEFAULT_EXAMPLES"),
    )


def _is_process_only_product_success_metric(value):
    from delivery_contract_checks import _is_process_only_product_success_metric as judge
    return judge(value, policies._host_policy("PRODUCT_SUCCESS_PROCESS_ONLY_RE"))


def _is_task_pending_status_allowed(task):
    from delivery_contract_checks import _is_task_pending_status_allowed as judge
    return judge(task, policies._product_policy("TASK_PENDING_STATUS_MARKERS"))


def _validate_product_success_contract(packet):
    from delivery_contract_checks import _validate_product_success_contract as validate
    return validate(packet, _product_success_policy())


def _validate_acceptance_contract(task, packet):
    from delivery_contract_checks import _validate_acceptance_contract as validate
    return validate(task, packet, _acceptance_policy())


def _validate_quality_budget(task, packet):
    from delivery_contract_checks import _validate_quality_budget as validate
    return validate(task, packet, _quality_budget_policy())


def _validate_vertical_slice(task, packet):
    from delivery_contract_checks import _validate_vertical_slice as validate
    return validate(task, packet, _vertical_slice_policy())


def check_product_success_contracts(packet_path=None):
    import governance_check_bindings as governance_checks

    from delivery_contract_checks import check_declared_contracts
    return check_declared_contracts(
        "product_success_contract", packet_path, governance_checks._declared_packet_checks,
        lambda task, packet: _validate_product_success_contract(packet),
    )


def check_acceptance_contracts(packet_path=None):
    import governance_check_bindings as governance_checks

    from delivery_contract_checks import check_declared_contracts
    return check_declared_contracts(
        "acceptance_contract", packet_path, governance_checks._declared_packet_checks,
        _validate_acceptance_contract,
    )


def check_quality_budget(packet_path=None):
    import governance_check_bindings as governance_checks

    from delivery_contract_checks import check_declared_contracts
    return check_declared_contracts(
        "quality_budget", packet_path, governance_checks._declared_packet_checks,
        _validate_quality_budget,
    )


def check_vertical_slices(packet_path=None):
    import governance_check_bindings as governance_checks

    from delivery_contract_checks import check_declared_contracts
    return check_declared_contracts(
        "vertical_slice", packet_path, governance_checks._declared_packet_checks,
        _validate_vertical_slice,
    )


def render_deterministic_scaffold(scaffold_type, scaffold_dir=None):
    from scaffold_contracts import render_deterministic_scaffold as render
    return render(scaffold_type, scaffold_dir, DETERMINISTIC_SCAFFOLD_TYPES, default_dir=DETERMINISTIC_SCAFFOLD_DIR)


def check_deterministic_scaffolds(scaffold_dir=None):
    from scaffold_contracts import check_deterministic_scaffolds as check
    return check(scaffold_dir, _scaffold_policy(), default_dir=DETERMINISTIC_SCAFFOLD_DIR)


def classify_user_interruption(decision):
    from interruption_contracts import classify_user_interruption as classify
    return classify(decision, policies._product_policy("INTERRUPTION_POLICY_CRITICAL_TRIGGER_KEYS"))


def _validate_interruption_policy_examples(examples):
    from interruption_contracts import _validate_interruption_policy_examples as validate
    return validate(examples, _interruption_policy(), classify_user_interruption)


def check_interruption_policy(interaction_boundary_path=None, template_path=None, packet_path=None, examples=None):
    import governance_check_bindings as governance_checks

    from interruption_contracts import check_interruption_policy as check
    return check(
        paths.INTERACTION_BOUNDARY_PATH if interaction_boundary_path is None else Path(interaction_boundary_path),
        paths.USER_INTERRUPTION_POLICY_TEMPLATE_PATH if template_path is None else Path(template_path),
        packet_path, examples, governance_checks._declared_packet_checks, _interruption_policy(),
        classify_user_interruption, _validate_interruption_policy_examples,
    )


def build_execution_packet(task, **options):
    from execution_packet import build_execution_packet as build
    return build(task, **options)


def generate_execution_packets(existing=None, *, task_ids=None, governance_dir=None, contracts=(), quality_dimensions=()):
    import governance_check_bindings as governance_checks

    from execution_packet_checks import generate_execution_packets as run
    return run(existing, task_ids=task_ids, governance_dir=governance_dir, contracts=contracts,
               quality_dimensions=quality_dimensions, plan_path_now=lambda: paths.SAMPLE_PATH,
               active_execution_packet_tasks=lambda: governance_checks._active_execution_packet_tasks(),
               is_incomplete_task_status=governance_checks._is_incomplete_task_status,
               packet_builder=lambda: build_execution_packet,
               parse_current_active_tasks=lambda: governance_checks.parse_current_active_tasks())


def check_execution_packets(packet_path=None):
    import governance_check_bindings as governance_checks

    from execution_packet_checks import check_execution_packets as run
    return run(packet_path, declared_packet_checks=governance_checks._declared_packet_checks,
               validate_packet=lambda task, packet: _validate_execution_packet(task, packet))


def cmd_execution_packet(args):
    from governance_fact_cli import cmd_execution_packet as run
    return run(args, packet_path_now=lambda: paths.EXECUTION_PACKET_PATH,
               read_execution_packet_document=lambda path, **options: _read_execution_packet_document(path, **options),
               generate_execution_packets=lambda **options: generate_execution_packets(**options))


def cmd_check_commit_scope(args):
    from governance_fact_cli import cmd_check_commit_scope as run
    return run(args, check_commit_scope=check_commit_scope)


def cmd_check_goal_alignment(args):
    from governance_fact_cli import cmd_check_goal_alignment as run
    return run(args, check_goal_alignment=check_goal_alignment)


def cmd_check_user_impact(args):
    from governance_fact_cli import cmd_check_user_impact as run
    return run(args, check_user_impact=check_user_impact)


def cmd_check_product_success_contracts(args):
    from delivery_contract_cli import cmd_check_product_success_contracts as run
    return run(args, check_product_success_contracts, lambda: render_rb2_goal_contract_block())


def cmd_check_acceptance_contracts(args):
    from delivery_contract_cli import cmd_check_acceptance_contracts as run
    return run(args, check_acceptance_contracts)


def cmd_check_quality_budget(args):
    from delivery_contract_cli import cmd_check_quality_budget as run
    return run(args, check_quality_budget)


def cmd_check_vertical_slices(args):
    from delivery_contract_cli import cmd_check_vertical_slices as run
    return run(args, check_vertical_slices)


def cmd_check_deterministic_scaffolds(args):
    from delivery_contract_cli import cmd_check_deterministic_scaffolds as run
    return run(args, check_deterministic_scaffolds)


def cmd_check_interruption_policy(args):
    from delivery_contract_cli import run_interruption_check
    run_interruption_check(args, check_interruption_policy)


def cmd_generate_deterministic_scaffold(args):
    from delivery_contract_cli import generate_scaffold
    generate_scaffold(args, render_deterministic_scaffold)
