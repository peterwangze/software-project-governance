"""Compose governance facts, audit checks and archive readers."""

import workflow_project_roots as paths
import workflow_policy_bindings as policies

from checks import review_domain as _review_checks, risk_domain, version as version_checks
from checks.evidence_domain import (
    check_evidence_completeness, parse_evidence_task_ids, requires_impact_evidence,
)
from functools import cache as _cache
from hot_governance_facts import (
    FIX_087_READINESS_VERSION, FIX_087_REQ_TASKS, FIX_105_PLAN_WORKFLOW_VERSION_RE,
    FIX_105_READINESS_RELEASE_BLOCKERS, FIX_105_SNAPSHOT_DATE_RE,
    FIX_105_SNAPSHOT_RELEASE_VERSION_RE, FIX_105_SNAPSHOT_VERSION_RE, _EVIDENCE_DATE_SHAPE_RE,
    _TASK_ID_IN_REF_RE, _markdown_section_by_prefix,
)
from pathlib import Path
import premise_tracker
import re


def _parse_context_open_risks(root):
    import workflow_context_bindings as context_checks

    return risk_domain._parse_context_open_risks(root, context_file=context_checks._context_file, context_task=context_checks._context_task)


def parse_open_risks():
    return risk_domain.parse_open_risks(risk_path=paths.RISK_PATH)


def parse_active_risks(risk_content=None):
    return risk_domain.parse_active_risks(risk_content, risk_path=paths.RISK_PATH)


def check_risk_staleness():
    return risk_domain.check_risk_staleness(risk_path=paths.RISK_PATH)


def check_risk_escalation():
    return risk_domain.check_risk_escalation(risk_path=paths.RISK_PATH)


def _default_task_status_map():
    return risk_domain._default_task_status_map(paths.SAMPLE_PATH)


def check_risk_mitigation_closure(risk_content=None, task_status_map=None):
    return risk_domain.check_risk_mitigation_closure(risk_content, task_status_map, risk_path=paths.RISK_PATH,
                                                    plan_path=paths.SAMPLE_PATH, task_id_pattern=_TASK_ID_IN_REF_RE)


def check_snapshot_freshness(plan_content=None, snapshot_text=None, evidence_mtime=None, commit_date=None):
    from checks.snapshot_domain import check_snapshot_freshness as check
    return check(plan_content, snapshot_text, evidence_mtime, commit_date, host_root=paths.HOST_PROJECT_ROOT,
                 snapshot_path=paths.SESSION_SNAPSHOT_PATH, plan_path=paths.SAMPLE_PATH, evidence_path=paths.EVIDENCE_PATH,
                 session_date_pattern=FIX_105_SNAPSHOT_DATE_RE)


def check_change_triage(root=None, governance_dir=None, verify_path=None):
    from checks.triage_domain import check_change_triage as check
    return check(paths.ROOT if root is None else root, paths.GOVERNANCE_DIR if governance_dir is None else governance_dir,
                 verify_path)


def check_r1_completion_gate(root=None, governance_dir=None):
    from checks.triage_domain import check_r1_completion_gate as check
    return check(paths.ROOT if root is None else root, paths.GOVERNANCE_DIR if governance_dir is None else governance_dir)


def check_loop_role_skill_consistency(root=None):
    from team_activation import check_loop_role_skill_consistency as run
    return run(
        root, package_root=paths.ROOT, lifecycle_registry_gates=policies._product_policy("LIFECYCLE_REGISTRY_GATES"),
        loop_role_skill_contracts=policies._host_policy('LOOP_ROLE_SKILL_CONTRACTS'), display_path=paths._display_path,
        markdown_section_by_prefix=_markdown_section_by_prefix, read_text_normalized=paths._read_text_normalized,
    )


def _hot_status_cell_is_delivered(status):
    import workflow_context_bindings as context_checks

    from hot_governance_facts import _hot_status_cell_is_delivered as run
    return run(status, status_clean_cell=context_checks._status_clean_cell,
               status_is_writer_committed_cell=context_checks._status_is_writer_committed_cell)


def _hot_task_is_delivered(plan_content, task_id, version=None):
    from hot_governance_facts import _hot_task_is_delivered as run
    return run(plan_content, task_id, version,
               is_delivered=lambda cell: _hot_status_cell_is_delivered(cell))


def _hot_task_is_open(plan_content, task_id, version=None):
    from hot_governance_facts import _hot_task_is_open as run
    return run(plan_content, task_id, version,
               is_delivered=lambda cell: _hot_status_cell_is_delivered(cell))


def _hot_task_ids_for_version(plan_content, version):
    from hot_governance_facts import _hot_task_ids_for_version as run
    return run(plan_content, version,
               is_delivered=lambda cell: _hot_status_cell_is_delivered(cell))


def _latest_published_release_fact(plan_content):
    from hot_governance_facts import _latest_published_release_fact as run
    return run(plan_content, policy=_hot_fact_policy())


def _hot_fact_policy():
    from hot_governance_facts import HotFactPolicy
    return HotFactPolicy(FIX_087_READINESS_VERSION, FIX_087_REQ_TASKS, FIX_105_SNAPSHOT_RELEASE_VERSION_RE,
                         FIX_105_PLAN_WORKFLOW_VERSION_RE, FIX_105_SNAPSHOT_VERSION_RE,
                         FIX_105_SNAPSHOT_DATE_RE, FIX_105_READINESS_RELEASE_BLOCKERS)


def _snapshot_fact_source_issues(plan_content, plan_tracker_path):
    from hot_governance_facts import _snapshot_fact_source_issues as run
    return run(plan_content, plan_tracker_path, policy=_hot_fact_policy(), display_path=paths._display_path)


def _hot_fact_source_plugin_scope():
    import workflow_report_selection as reports

    from hot_governance_facts import _hot_fact_source_plugin_scope as run
    return run(host_plugin_roots_divergent=reports._host_plugin_roots_divergent)


def check_hot_fact_source_consistency(plan_tracker_path=None):
    import workflow_report_selection as reports

    from hot_governance_facts import check_hot_fact_source_consistency as run
    return run(plan_tracker_path, policy=_hot_fact_policy(), display_path=paths._display_path,
               governance_dir=paths._governance_dir, host_plugin_roots_divergent=reports._host_plugin_roots_divergent,
               is_delivered=lambda cell: _hot_status_cell_is_delivered(cell))


def _load_archive_module():
    from governance_archive_data import _load_archive_module as read
    return read(plugin_root=paths.ROOT, host_root=paths.HOST_PROJECT_ROOT)


@_cache
def _archive_reader_class():
    """Build the historical public type once across imports and programmatic overrides."""

    from governance_archive_data import GovernanceDataSource as ArchiveReader

    class GovernanceDataSource(ArchiveReader):
        """Archive reader using the current host and the CLI's configurable fact paths."""

        def __init__(self, sample_path=None, evidence_path=None, archive_index_path=None,
                     archive_root=None, decision_path=None, risk_path=None):
            super().__init__(
                paths.GOVERNANCE_DIR, paths.SAMPLE_PATH if sample_path is None else sample_path,
                paths.EVIDENCE_PATH if evidence_path is None else evidence_path,
                archive_index_path, archive_root, decision_path, risk_path,
            )

        @staticmethod
        def _table_cells(line):
            return paths._split_markdown_table_row(line)

        @staticmethod
        def _expand_task_ids(text):
            return expand_task_ids(text)

    GovernanceDataSource.__qualname__ = "GovernanceDataSource"
    GovernanceDataSource.__module__ = "verify_workflow"
    return globals().setdefault("GovernanceDataSource", GovernanceDataSource)


def _archive_reader(*args, **kwargs):
    from workflow_public_api import read_public
    return read_public("GovernanceDataSource")(*args, **kwargs)


def parse_completed_task_ids():
    from governance_archive_data import parse_completed_task_ids as read
    return read(plan_path=paths.SAMPLE_PATH)


def expand_task_ids(raw_text):
    from governance_archive_data import expand_task_ids as read
    return read(raw_text)


def check_gate_consistency():
    from gate_consistency import check_gate_consistency as read
    return read(
        current_governance_dir=lambda: paths.GOVERNANCE_DIR, archive_reader=lambda: _archive_reader(),
        check_evidence_completeness=lambda: check_evidence_completeness(),
    )


def check_protocol_compliance():
    import workflow_context_bindings as context_checks

    from gate_consistency import check_protocol_compliance as read
    return read(
        governance_dir=paths.GOVERNANCE_DIR, plan_path=paths.SAMPLE_PATH, date_shape=_EVIDENCE_DATE_SHAPE_RE,
        governance_table_cells=_governance_table_cells,
        status_is_terminal_cell=context_checks._status_is_terminal_cell,
    )


def parse_tier_definitions():
    from gate_consistency import parse_tier_definitions as read
    return read(paths.SAMPLE_PATH)


def parse_task_status_map():
    """Return dict mapping task_id -> status from ALL tracking tables in plan-tracker.

    Scans the entire file for task rows regardless of section boundaries,
    since tracking tables are spread across multiple subsections.
    """

    content = paths.SAMPLE_PATH.read_text(encoding="utf-8")
    status_map = {}

    for line in content.split("\n"):
        line_stripped = line.strip()
        if not line_stripped.startswith("| ") or "---" in line_stripped:
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 11:
            task_id_match = re.match(r"([A-Z]+-\d+)", parts[1])
            if task_id_match:
                task_id = task_id_match.group(1)
                status = parts[10] if len(parts) > 10 else ""
                status_map[task_id] = status

    return status_map


def check_tier_audit_completeness():
    from gate_consistency import check_tier_audit_completeness as read
    return read(parse_tier_definitions, parse_task_status_map, parse_evidence_task_ids)


def check_version_consistency():
    """Delegate version consistency checks to the Phase 6 module."""

    return version_checks.check_version_consistency(paths.ROOT, paths.GOVERNANCE_DIR.parent)


def check_commit_task_references(limit=20):
    from checks.commit import check_commit_task_references as run
    return run(limit, product_root=paths.ROOT)


def check_task_deadline():
    import workflow_context_bindings as context_checks

    from checks.commit import check_task_deadline as run
    return run(plan_path=paths.SAMPLE_PATH, status_is_terminal_cell=context_checks._status_is_terminal_cell)


def check_cross_references():
    import host_check_bindings as host_checks

    from ledger_references import check_cross_references as check
    return check(product_root=paths.ROOT, validator_path=paths.ROOT / "skills/software-project-governance/infra/verify_workflow.py",
                 quote_sync_issues=lambda: host_checks._check_quote_sync_issues(),
                 check_exploration_channels=lambda: host_checks.check_exploration_channels())


def check_sequential_ids():
    from ledger_identifiers import check_sequential_ids as run
    return run(governance_dir=paths.GOVERNANCE_DIR, data_source=_archive_reader)


def _format_id_sequence_status(prefix, ids):
    from ledger_identifiers import _format_id_sequence_status as run
    return run(prefix, ids)


def _print_sequential_id_check(si_result):
    from ledger_identifiers import _print_sequential_id_check as run
    return run(si_result)


def _scan_unicode_line_separators():
    from ledger_identifiers import _scan_unicode_line_separators as run
    return run(governance_dir=paths.GOVERNANCE_DIR)


def check_structural_validity():
    import release_check_bindings as release_checks

    from ledger_identifiers import check_structural_validity as check
    return check(governance_dir=paths.GOVERNANCE_DIR, extract_skill_version=release_checks._extract_skill_version,
                 skill_file=lambda: paths.ROOT / "skills/software-project-governance/SKILL.md",
                 manifest_file=lambda: paths.ROOT / "skills/software-project-governance/core/manifest.json",
                 split_markdown_table_row=paths._split_markdown_table_row)


def _split_governance_table_row(line):
    from plan_task_selection import _split_governance_table_row as run
    return run(line)


def _governance_table_cells(line):
    from plan_task_selection import _governance_table_cells as run
    return run(line)


def _is_incomplete_task_status(status):
    import workflow_context_bindings as context_checks

    from plan_task_selection import _is_incomplete_task_status as run
    return run(status, status_is_completed_cell=context_checks._status_is_completed_cell)


def _is_nonactive_subsection(heading):
    from plan_task_selection import _is_nonactive_subsection as run
    return run(heading)


def parse_current_active_tasks():
    from plan_task_selection import parse_current_active_tasks as run
    return run(plan_path=paths.SAMPLE_PATH)


def _active_execution_packet_tasks():
    import workflow_context_bindings as context_checks

    from plan_task_selection import _active_execution_packet_tasks as run
    return run(status_is_completed_cell=context_checks._status_is_completed_cell,
               parse_current_active_tasks=lambda: parse_current_active_tasks())


def _declared_packet_checks(result, packet_path, contract=None):
    import delivery_check_bindings as delivery_checks

    from execution_packet_checks import _declared_packet_checks as run
    return run(result, packet_path, contract, plan_path_now=lambda: paths.SAMPLE_PATH,
               is_incomplete_task_status=lambda status: _is_incomplete_task_status(status),
               parse_current_active_tasks=lambda: parse_current_active_tasks(),
               read_document=lambda path, **options: delivery_checks._read_execution_packet_document(path, **options))


def parse_impact_analysis_entries():
    from plan_impact import parse_impact_analysis_entries as run
    return run(parse_impact_analysis_entries_with_exemptions=lambda: parse_impact_analysis_entries_with_exemptions())


def parse_impact_analysis_entries_with_exemptions():
    import delivery_check_bindings as delivery_checks

    from plan_impact import parse_impact_analysis_entries_with_exemptions as run
    return run(evidence_path=paths.EVIDENCE_PATH, current_release_task_ids=delivery_checks._current_release_task_ids,
               hot_status_completion_state=delivery_checks._hot_status_completion_state,
               plan_hot_tracker_task_statuses=delivery_checks._plan_hot_tracker_task_statuses,
               split_governance_table_row=_split_governance_table_row, expand_task_ids=expand_task_ids,
               requires_impact_evidence=requires_impact_evidence)


def _evidence_task_type_index():
    return _review_checks._read_task_type_index(paths.EVIDENCE_PATH)


def _archive_corpus_files():
    return risk_domain.archive_corpus_files(paths.SAMPLE_PATH.parent)


def _resolve_archive_task_refs(task_ids):
    return risk_domain.resolve_archive_task_refs(
        task_ids, _archive_corpus_files,
        lambda path: paths._display_path(path, paths.SAMPLE_PATH.parent.parent).as_posix())


def check_risk_mitigation_closure_with_archive(risk_content=None, task_status_map=None):
    """Run the archive-aware risk check with the current host configuration."""
    if task_status_map is None:
        task_status_map = _default_task_status_map()
    return risk_domain.check_risk_mitigation_closure_with_archive(
        risk_content, task_status_map, check=check_risk_mitigation_closure,
        resolve_refs=_resolve_archive_task_refs)


def check_decision_premise(governance_dir=None):
    """FIX-463 — collapsed decision-premise verdict (Check 2b core).

    Returns ``{"declarations": {dec_id: premise}, "collapsed": [dec_id],
    "detail": {dec_id: {...}}}``. Registered as the R5 segment-2b loader
    (the segment registry's SegmentSpec table); read-only over
    decision-log.md + premise-events.jsonl, never raises on missing
    inputs (idle face when no premises are declared).
    """

    gov = Path(governance_dir) if governance_dir else paths.GOVERNANCE_DIR
    decision_log = gov / "decision-log.md"
    declarations = premise_tracker.collect_premise_declarations(
        decision_log.read_text(encoding="utf-8")
        if decision_log.is_file() else "")
    events = premise_tracker.load_events(gov)
    status = premise_tracker.premise_status(declarations, events)
    return {"declarations": declarations, **status}


def cmd_check_cross_references(args):
    import host_check_bindings as host_checks

    from governance_fact_cli import cmd_check_cross_references as run
    return run(args, check_cross_references=lambda: check_cross_references(),
               check_exploration_sample_advisories=lambda: host_checks.check_exploration_sample_advisories())


def cmd_check_sequential_ids(args):
    from governance_fact_cli import cmd_check_sequential_ids as run
    return run(args, check_sequential_ids=check_sequential_ids)


def cmd_check_structural_validity(args):
    from governance_fact_cli import cmd_check_structural_validity as run
    return run(args, check_structural_validity=check_structural_validity)


def cmd_check_hot_fact_source(args):
    from governance_fact_cli import cmd_check_hot_fact_source as run
    return run(args,
               check_hot_fact_source_consistency=lambda *a, **kw: check_hot_fact_source_consistency(*a, **kw))
