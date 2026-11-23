"""Compose project context, capability discovery and status views."""

import workflow_project_roots as paths
import workflow_policy_bindings as policies

from checks.capability_registry import _line_has_scoped_claim_negation, check_capability_registry
from contracts import _is_valid_string_list
from pathlib import Path
from plan_impact import PRODUCT_CODE_PATTERNS
import re
import task_row_update


GOVERNANCE_CONTEXT_REQUIRED_FIELDS = [
    "status",
    "detected_item",
    "source_facts",
    "blocker_state",
    "next_action",
    "auto_continue",
    "interrupt_boundary",
]


GOVERNANCE_CONTEXT_SNAPSHOT_SECTIONS = {
    "遗留任务",
    "Carry-over tasks",
    "Carry over tasks",
    "Unfinished / deferred",
    "未完成 / 已延期",
    "下次会话优先级",
    "Next priorities",
    "Next session priorities",
}


GOVERNANCE_CONTEXT_BLOCKED_MARKERS = ("blocked", "阻塞", "卡住", "等待", "待确认")


CAPABILITY_CONTEXT_REQUIRED_FIELDS = [
    "scenario",
    "host_id",
    "available_capabilities",
    "selected_capability",
    "source_facts",
    "rejected_alternatives",
    "degradation",
    "side_effect_boundary",
    "validation_command",
    "review_requirement",
    "no_overclaim_boundary",
]


CAPABILITY_CONTEXT_ALLOWED_STATUSES = {
    "AVAILABLE",
    "BLOCKED",
    "DEGRADED",
    "NOT_SUPPORTED",
    "NOT_FOUND",
    "RESEARCH_ONLY",
}


CAPABILITY_CONTEXT_DEGRADED_STATUSES = {"BLOCKED", "DEGRADED", "NOT_SUPPORTED", "NOT_FOUND"}


CAPABILITY_CONTEXT_DOC_PATH = Path("docs/requirements/capability-discovery-orchestration-0.45.0.md")


CAPABILITY_CONTEXT_TOOLS_PATH = Path("skills/software-project-governance/infra/TOOLS.md")


CAPABILITY_CONTEXT_NO_OVERCLAIM_TOKENS = [
    "automatic global best-tool selection",
    "catalog entry",
    "runtime PASS",
    "diagnostic selection trace",
]


HOST_CAPABILITY_CONTEXT_REQUIRED_FIELDS = [
    "scenario",
    "host_id",
    "benchmark_kind",
    "source_facts",
    "restricted_scenarios",
    "side_effect_boundary",
    "validation_command",
    "review_requirement",
    "no_overclaim_boundary",
]


HOST_CAPABILITY_CONTEXT_SCENARIOS = {
    "no_network",
    "no_plugin_install",
    "no_mcp",
    "no_browser",
    "no_sub_agent",
    "local_skill_only",
    "codex_cli_blocked",
    "gemini_auth_blocked",
}


HOST_CAPABILITY_CONTEXT_REQUIRED_SCENARIO_FIELDS = [
    "scenario_id",
    "constraint",
    "preferred_capability",
    "selected_capability",
    "degradation_boundary",
    "validation_command",
    "source_facts",
    "no_overclaim_boundary",
]


HOST_CAPABILITY_CONTEXT_ALLOWED_STATUSES = {
    "PASS",
    "AVAILABLE",
    "BLOCKED",
    "DEGRADED",
    "NOT_SUPPORTED",
    "NOT_FOUND",
    "RESEARCH_ONLY",
}


HOST_CAPABILITY_CONTEXT_UNAVAILABLE_STATUSES = {
    "BLOCKED",
    "DEGRADED",
    "NOT_SUPPORTED",
    "NOT_FOUND",
    "RESEARCH_ONLY",
}


HOST_CAPABILITY_CONTEXT_BOUNDARY_TOKENS = [
    "benchmark/diagnostic",
    "not external execution",
    "not Desktop marketplace E2E PASS",
    "blocked capability is not runtime PASS",
    "catalog fact is not runtime PASS",
    "Do not claim automatic best-tool selection.",
    "Do not claim universal plugin availability.",
]


HOST_CAPABILITY_CONTEXT_FORBIDDEN_OVERCLAIMS = [
    "blocked capability runtime pass",
    "blocked capability is runtime pass",
    "blocked capability is available",
    "degraded capability runtime pass",
    "catalog fact runtime pass",
    "catalog fact is runtime pass",
    "codex desktop marketplace-management e2e pass",
    "desktop marketplace e2e pass",
    "officially approved",
    "official approval granted",
    "marketplace approved",
    "marketplace approval granted",
    "external execution",
    "successful external execution",
    "automatic best-tool selection",
    "automatically selects the best tool",
    "universal plugin availability",
    "universal plugin available",
    "universal plugins available",
    "1.0.0 production-ready",
]


HOST_CAPABILITY_CONTEXT_REQUIRED_BLOCKED_FACTS = {
    "codex_cli_blocked": "restricted benchmark scenario: Codex CLI blocked",
    "gemini_auth_blocked": "restricted benchmark scenario: Gemini auth blocked",
}


def _extract_section(content, heading, stop_headings=None):
    from plan_status import _extract_section as read
    return read(content, heading, stop_headings)


def parse_project_config(path=None):
    from plan_status import parse_project_config as read
    return read(path, plan_path=paths.SAMPLE_PATH)


def parse_overview():
    from plan_status import parse_overview as read
    return read(plan_path=paths.SAMPLE_PATH)


def _normalize_task_status(status_text):
    from plan_status import _normalize_task_status as read
    return read(status_text)


def parse_task_stats():
    from plan_status import parse_task_stats as read
    return read(plan_path=paths.SAMPLE_PATH)


def _context_root(root=None):
    return Path(root) if root is not None else paths.ROOT


def _context_file(root, relative_path):
    return _context_root(root) / relative_path


def _empty_governance_context(root=None):
    from project_context import _empty_governance_context as read
    return read(_context_root(root))


def _capability_context_path(root, relative_path):
    return _context_root(root) / relative_path


def _capability_file_fact(root, relative_path, label):
    from capability_context import _capability_file_fact as read
    return read(_context_root(root), relative_path, label)


def _capability_text_contains(root, relative_path, token):
    from capability_context import _capability_text_contains as read
    return read(_context_root(root), relative_path, token)


def _capability_cli_registration_fact(root, relative_path):
    from capability_context import _capability_cli_registration_fact as read
    return read(_context_root(root), relative_path)


def _capability_host_id(root):
    from capability_context import _capability_host_id as read
    return read(_context_root(root))


def discover_capability_context(root=None):
    from capability_context import discover_capability_context as read
    return read(
        _context_root(root),
        requirements_path=CAPABILITY_CONTEXT_DOC_PATH,
        tools_path=CAPABILITY_CONTEXT_TOOLS_PATH,
        check_registry=check_capability_registry,
    )


def _host_capability_source_fact(root, relative_path, present_label, missing_label):
    from capability_context import _host_capability_source_fact as read
    return read(_context_root(root), relative_path, present_label, missing_label)


def _host_context_registry_capabilities(root):
    from capability_context import _host_context_registry_capabilities as read
    return read(_context_root(root), display_path=paths._display_path)


def _host_context_capability(capabilities, kind=None, capability_id=None):
    from capability_context import _host_context_capability as read
    return read(capabilities, kind, capability_id)


def _host_context_fact_contains(root, relative_path, tokens):
    from capability_context import _host_context_fact_contains as read
    return read(_context_root(root), relative_path, tokens)


def _host_restricted_scenario(scenario_id, constraint, preferred, selected, status, reason, source_facts, validation_command):
    from capability_context import _host_restricted_scenario as read
    return read(scenario_id, constraint, preferred, selected, status, reason, source_facts, validation_command)


def discover_host_capability_context(root=None):
    from capability_context import discover_host_capability_context as read
    return read(_context_root(root), registry_capabilities=_host_context_registry_capabilities)


def _host_context_values(value):
    from capability_context import _host_context_values as read
    return read(value)


def check_host_capability_context(root=None, *, sampled_context=None):
    from capability_context import RestrictedHostPolicy, check_host_capability_context as validate
    root = _context_root(root)
    context = discover_host_capability_context(root) if sampled_context is None else sampled_context
    policy = RestrictedHostPolicy(
        required_fields=HOST_CAPABILITY_CONTEXT_REQUIRED_FIELDS,
        allowed_statuses=HOST_CAPABILITY_CONTEXT_ALLOWED_STATUSES,
        scenario_fields=HOST_CAPABILITY_CONTEXT_REQUIRED_SCENARIO_FIELDS,
        scenarios=HOST_CAPABILITY_CONTEXT_SCENARIOS,
        unavailable_statuses=HOST_CAPABILITY_CONTEXT_UNAVAILABLE_STATUSES,
        boundary_tokens=HOST_CAPABILITY_CONTEXT_BOUNDARY_TOKENS,
        forbidden_claims=HOST_CAPABILITY_CONTEXT_FORBIDDEN_OVERCLAIMS,
        blocked_facts=HOST_CAPABILITY_CONTEXT_REQUIRED_BLOCKED_FACTS,
    )
    return validate(
        root, context, policy=policy, requirements_path=CAPABILITY_CONTEXT_DOC_PATH,
        tools_path=CAPABILITY_CONTEXT_TOOLS_PATH, display_path=paths._display_path,
        valid_string_list=_is_valid_string_list,
        has_scoped_negation=_line_has_scoped_claim_negation,
    )


def _context_task(item_id, title, status, source, raw_line, priority='', kind='task'):
    from project_context import _context_task as read
    return read(item_id, title, status, source, raw_line, priority, kind)


def _extract_task_title_from_line(line, task_id):
    from project_context import _extract_task_title_from_line as read
    return read(line, task_id)


def _parse_plan_context_tasks(root):
    import delivery_check_bindings as delivery_checks
    import governance_check_bindings as governance_checks

    from project_context import _parse_plan_context_tasks as read
    return read(
        _context_root(root), is_incomplete=governance_checks._is_incomplete_task_status,
        normalize_priority=delivery_checks._normalize_priority,
    )


def _parse_snapshot_context_tasks(root):
    import delivery_check_bindings as delivery_checks
    import governance_check_bindings as governance_checks

    from project_context import _parse_snapshot_context_tasks as read
    return read(
        _context_root(root),
        is_incomplete=governance_checks._is_incomplete_task_status,
        normalize_priority=delivery_checks._normalize_priority,
        sections=GOVERNANCE_CONTEXT_SNAPSHOT_SECTIONS,
    )


def _context_git_toplevel(root):
    from project_context import _context_git_toplevel as read
    return read(root)


def _is_context_git_repo_root(root):
    from project_context import _is_context_git_repo_root as read
    return read(root)


def _run_context_git(root, args):
    from project_context import _run_context_git as read
    return read(root, args)


def _is_context_product_file(path):
    from project_context import _is_context_product_file as read
    return read(path, entry_files=policies._product_policy("PLATFORM_ENTRY_FILES"), product_patterns=PRODUCT_CODE_PATTERNS)


def _parse_git_status_context_tasks(root):
    from project_context import _parse_git_status_context_tasks as read
    return read(root, is_product_file=_is_context_product_file)


def _parse_recent_commit_context_facts(root, limit=5):
    from project_context import _parse_recent_commit_context_facts as read
    return read(root, limit)


def _dedupe_context_items(items):
    from project_context import _dedupe_context_items as read
    return read(items)


def discover_governance_context(root=None, skip_evidence_log=False):
    from project_context import discover_governance_context as read
    return read(_context_root(root), skip_evidence_log)


def check_governance_context(root=None):
    from project_context import check_governance_context as read
    return read(
        _context_root(root),
        discover=discover_governance_context,
        display_path=paths._display_path,
        read_text=paths._read_text_normalized,
    )


def check_capability_context(root=None, *, sampled_context=None):
    from capability_context import SelectionPolicy, check_capability_context as validate
    root = _context_root(root)
    context = discover_capability_context(root) if sampled_context is None else sampled_context
    policy = SelectionPolicy(
        required_fields=CAPABILITY_CONTEXT_REQUIRED_FIELDS,
        allowed_statuses=CAPABILITY_CONTEXT_ALLOWED_STATUSES,
        degraded_statuses=CAPABILITY_CONTEXT_DEGRADED_STATUSES,
        boundary_tokens=CAPABILITY_CONTEXT_NO_OVERCLAIM_TOKENS,
    )
    return validate(
        root, context, policy=policy, requirements_path=CAPABILITY_CONTEXT_DOC_PATH,
        tools_path=CAPABILITY_CONTEXT_TOOLS_PATH, display_path=paths._display_path,
    )


def parse_session_snapshot_carry_over_tasks(snapshot_path=None):
    import delivery_check_bindings as delivery_checks
    import governance_check_bindings as governance_checks

    from governance_views import parse_session_snapshot_carry_over_tasks as read
    path = Path(snapshot_path) if snapshot_path is not None else paths.SESSION_SNAPSHOT_PATH
    return read(path, is_incomplete=governance_checks._is_incomplete_task_status, normalize_priority=delivery_checks._normalize_priority)


def build_delivery_trust_snapshot(project_root=None, unit_id=None):
    from governance_views import build_delivery_trust_snapshot as read
    return read(project_root if project_root is not None else paths.GOVERNANCE_DIR.parent, unit_id)


def _status_col_name(raw):
    from plan_status import _status_col_name as read
    return read(raw)


def _status_clean_cell(value):
    from plan_status import _status_clean_cell as read
    return read(value)


def _status_iso_date(value):
    from plan_status import _status_iso_date as read
    return read(value)


def _last_marker_pos(text, markers):
    from plan_status import _last_marker_pos as read
    return read(text, markers)


def _w7_terminal_assertion_positions(text):
    from plan_status import _w7_terminal_assertion_positions as read
    return read(text, markers=policies._host_policy("_W7_TERMINAL_MARKERS"), terminal_date=policies._host_policy("_W7_TERMINAL_DATE_RE"))


_WRITER_STATE_MARKER_CHAIN = task_row_update._STATE_MARKER_CHAIN


def _status_is_writer_committed_cell(text):
    from plan_status import _status_is_writer_committed_cell as read
    return read(text, operation_anchor=policies._host_policy("_WRITER_OP_ANCHOR_RE"), state_chain=_WRITER_STATE_MARKER_CHAIN)


def _status_is_completed_cell(cell):
    from plan_status import _status_is_completed_cell as read
    return read(
        cell,
        active_markers=policies._host_policy("_W7_ACTIVE_MARKERS"),
        writer_committed=_status_is_writer_committed_cell,
        terminal_positions=_w7_terminal_assertion_positions,
    )


_TERMINAL_CELL_DECORATIONS = ("⏳", "🔄", "📋", "🆕", "⏸")


def _status_is_terminal_cell(cell):
    from plan_status import _status_is_terminal_cell as read
    return read(cell, decorations=_TERMINAL_CELL_DECORATIONS, is_completed=_status_is_completed_cell)


def _status_table_stream(content):
    from plan_status import _status_table_stream as read
    return read(content)


def parse_task_table_rows(plan_content=None):
    from plan_status import parse_task_table_rows as read
    return read(plan_content, plan_path=paths.SAMPLE_PATH)


def parse_recent_completed_tasks(rows, n=5):
    from plan_status import parse_recent_completed_tasks as read
    return read(rows, n, is_completed=_status_is_completed_cell)


def parse_recent_decisions(n=5, decision_content=None):
    from plan_status import parse_recent_decisions as read
    return read(n, decision_content, governance_dir=paths.GOVERNANCE_DIR)


def _status_plugin_freshness(plan_content=None):
    from plan_status import _status_plugin_freshness as read
    return read(plan_content, plan_path=paths.SAMPLE_PATH)


_STATUS_ID_TOKEN_RE = re.compile(r"(?<![-A-Z])([A-Z]+)-(\d+)\b")


def _status_priority_rank(priority):
    from plan_status import _status_priority_rank as read
    return read(priority)


def _status_raw_dependency_ids(rec):
    from plan_status import _status_raw_dependency_ids as read
    return read(rec, task_id_pattern=_STATUS_ID_TOKEN_RE)


def _status_next_steps(plan_content, max_results=3):
    from plan_status import _status_next_steps as read
    return read(
        plan_content, max_results,
        read_rows=parse_task_table_rows,
        is_completed=_status_is_completed_cell,
        dependency_ids=_status_raw_dependency_ids,
    )


def _status_task_stats(rows):
    from plan_status import _status_task_stats as read
    return read(rows, is_completed=_status_is_completed_cell)


def cmd_status(args):
    from status_cli import cmd_status as read
    return read(args, host_root=paths.HOST_PROJECT_ROOT)


def _status_project_name(config, overview):
    from plan_status import _status_project_name as read
    return read(config, overview)


def cmd_governance_context(args):
    from status_cli import cmd_governance_context as read
    return read(args, host_root=paths.HOST_PROJECT_ROOT)


def cmd_capability_context(args):
    from status_cli import cmd_capability_context as read
    return read(
        args,
        plugin_root=paths.ROOT,
        discover=discover_capability_context,
        validate=check_capability_context,
        display_path=paths._display_path,
    )


def cmd_check_host_capability_context(args):
    from status_cli import cmd_check_host_capability_context as read
    return read(
        args,
        plugin_root=paths.ROOT,
        discover=discover_host_capability_context,
        validate=check_host_capability_context,
        display_path=paths._display_path,
    )
