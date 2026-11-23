"""Compose collaboration locks, reviews, recommendations and governed writes."""

import workflow_project_roots as paths
import workflow_policy_bindings as policies

from checks import review_domain as _review_checks
from checks.review_domain import REVIEW_MACHINE_ROW_MARKER
from datetime import date, datetime
from enforcement import cmd_enforcement_check
from execution_isolation import (
    cmd_isolation_capability, cmd_isolation_lease_reclaim, cmd_isolation_snapshot,
    cmd_isolation_status, cmd_isolation_write,
)
from goal_bridge import cmd_goal_bridge
from hot_governance_facts import _TASK_ID_CELL_RE, _TASK_ID_IN_REF_RE
import json
import pin_ledger
import premise_tracker
import re
import sys


def _review_input(name):
    from workflow_public_api import read_public
    return read_public(name)


def _review_reader(name):
    return property(lambda self: _review_input(name))


class _LegacyReviewSources(_review_checks.ReviewSources):
    """Bind only the individual published paths and callbacks the review rules read."""

    def product_root(self):
        return _review_input("ROOT")

    def governance_dir(self):
        return _review_input("GOVERNANCE_DIR")

    def plan_path(self):
        return _review_input("SAMPLE_PATH")

    def evidence_path(self):
        return _review_input("EVIDENCE_PATH")

    archive_reader = _review_reader("GovernanceDataSource")
    expand_task_ids = _review_reader("expand_task_ids")
    completed_task_ids = _review_reader("parse_completed_task_ids")
    is_plugin_path = _review_reader("_is_plugin_path")
    is_audit_or_review_type = _review_reader("_is_audit_or_review_type")
    task_priority = _review_reader("_task_priority_from_table_parts")
    parse_date = _review_reader("_parse_iso_date")
    task_type_index = _review_reader("_evidence_task_type_index")
    is_completed = _review_reader("_status_is_completed_cell")


def check_agent_locks_format():
    from collaboration_checks import check_agent_locks_format as read
    return read(governance_dir=paths.GOVERNANCE_DIR)


def check_agent_lock_consistency():
    import release_check_bindings as release_checks

    from collaboration_checks import check_agent_lock_consistency as read
    return read(
        current_governance_dir=lambda: paths.GOVERNANCE_DIR, check_agent_locks_format=lambda: check_agent_locks_format(),
        lock_issue_is_blocking=lambda issue: release_checks.lock_issue_is_blocking(issue),
    )


def _legacy_parse_index_refs(index_lines):
    from governance_archive_data import _legacy_parse_index_refs as read
    return read(index_lines)


def check_archive_integrity():
    import governance_check_bindings as governance_checks

    from governance_archive_data import check_archive_integrity as read
    return read(
        plan_path=paths.SAMPLE_PATH,
        governance_dir=paths.GOVERNANCE_DIR,
        plan_directory=paths._governance_dir,
        load_archive=governance_checks._load_archive_module)


def cmd_check_agent_locks(_args):
    import release_check_bindings as release_checks

    from collaboration_checks import cmd_check_agent_locks as run
    return run(
        _args, check_agent_lock_consistency=lambda: check_agent_lock_consistency(),
        lock_issue_is_blocking=lambda issue: release_checks.lock_issue_is_blocking(issue),
    )


def cmd_check_archive_integrity(_args):
    from status_cli import cmd_check_archive_integrity as read
    return read(_args, check_integrity=check_archive_integrity)


def cmd_check_plugin_freshness(_args):
    from workspace_checks import cmd_check_plugin_freshness as run
    return run(_args)


class _CompletionRecommendationInputs:
    """Read Check 34 facts only when its current row or snapshot branch needs them."""

    evidence_path = property(lambda self: paths.EVIDENCE_PATH)
    snapshot_path = property(lambda self: paths.SESSION_SNAPSHOT_PATH)
    effective_date = property(lambda self: policies._host_policy("REQ108_RECOMMENDATION_DATE"))
    machine_marker = property(lambda self: policies._host_policy("RECO_ROW_MARKER"))
    legacy_marker = property(lambda self: policies._host_policy("_LEGACY_SNAPSHOT_MARKER"))
    snapshot_pattern = property(lambda self: policies._host_policy("_SNAPSHOT_REF_RE"))
    task_id_pattern = property(lambda self: _TASK_ID_IN_REF_RE)
    match = property(lambda self: re.match)
    parse_date = property(lambda self: date.fromisoformat)


class _RecommendationCommandInputs:
    """Keep the original command bindings live across reads, refreshes and writes."""

    evidence_path = property(lambda self: paths.EVIDENCE_PATH)
    governance_dir = property(lambda self: paths.GOVERNANCE_DIR)
    plan_path = property(lambda self: paths.SAMPLE_PATH)
    host_root = property(lambda self: paths.HOST_PROJECT_ROOT)
    premise_tracker = property(lambda self: premise_tracker)
    stdout = property(lambda self: sys.stdout)
    exit = property(lambda self: sys.exit)
    dumps = property(lambda self: json.dumps)

    @property
    def load_execution_packets(self):
        from delivery_check_bindings import current_execution_packet_reader
        return current_execution_packet_reader()


_completion_recommendation_inputs = _CompletionRecommendationInputs()
_recommendation_command_inputs = _RecommendationCommandInputs()


def _recommendation_snapshot_row_text(task_id, report, date_str):
    from recommendation_checks import _recommendation_snapshot_row_text as read
    return read(task_id, report, date_str)


def _write_recommendation_snapshot(task_id, report, evidence_path=None):
    from recommendation_checks import _write_recommendation_snapshot as read
    return read(task_id, report, evidence_path, inputs=_recommendation_command_inputs)


def check_completion_recommendation(evidence_rows=None, snapshot_text=None):
    from recommendation_checks import check_completion_recommendation as read
    return read(evidence_rows, snapshot_text, inputs=_completion_recommendation_inputs)


def cmd_task_priority_analysis(args):
    from recommendation_checks import cmd_task_priority_analysis as run
    return run(args, inputs=_recommendation_command_inputs)


def cmd_review_record(args):
    from review_record import cmd_review_record as run
    return run(args, host_root=paths.HOST_PROJECT_ROOT)


def cmd_next_candidates(args):
    from recommendation_checks import cmd_next_candidates as run
    return run(args, inputs=_recommendation_command_inputs)


def _triage_write_structure_guard(evidence_path, record_path, record_id=None):
    from write_guard_records import _triage_write_structure_guard as inspect
    return inspect(evidence_path, record_path, record_id)


def _plan_tracker_task_row_issues(content):
    import delivery_check_bindings as delivery_checks

    from write_guard_records import _plan_tracker_task_row_issues as inspect_rows
    return inspect_rows(
        content,
        expected_shape=policies._product_policy("_PLAN_TRACKER_ROW_EXPECTED_SHAPE"),
        task_id_pattern=_TASK_ID_CELL_RE,
        normalize_priority=delivery_checks._normalize_priority,
    )


def _evidence_machine_row_issues(content):
    from write_guard_records import _evidence_machine_row_issues as inspect_rows
    return inspect_rows(content, machine_families=policies._product_policy("_EVIDENCE_MACHINE_ROW_FAMILIES"))


def _row_has_governance_store_machine_credential(raw_line):
    from write_guard_records import _row_has_governance_store_machine_credential as has_receipt
    return has_receipt(raw_line, receipt_pattern=policies._host_policy("_EVIDENCE_MACHINE_CREDENTIAL_RE"))


def _write_guard_row_digest(text):
    from write_guard_records import _write_guard_row_digest as digest
    return digest(text)


def _extract_managed_row_records(surface, content):
    from write_guard_records import _extract_managed_row_records as extract_rows
    return extract_rows(surface, content, task_id_pattern=_TASK_ID_CELL_RE)


def _extract_ops_ledger_records(content):
    from write_guard_records import _extract_ops_ledger_records as extract_receipts
    return extract_receipts(content)


def _row_family_credential_ok(surface, row_key, row_text):
    from write_guard_records import _row_family_credential_ok as has_receipt
    return has_receipt(
        surface, row_key, row_text,
        review_marker=REVIEW_MACHINE_ROW_MARKER,
        store_prefix=policies._host_policy("_GOVERNANCE_STORE_MARKER_PREFIX"),
        operation_anchor=policies._product_policy("_OPS_LEDGER_RECEIPT_ANCHOR"),
    )


def _load_write_guard_state(governance_dir):
    from write_guard_state import _load_write_guard_state as load_state
    return load_state(
        governance_dir,
        filename=policies._product_policy("_WRITE_GUARD_STATE_FILENAME"),
        version=policies._product_policy("_WRITE_GUARD_STATE_SCHEMA_VERSION"),
        tool=policies._product_policy("_WRITE_GUARD_STATE_TOOL"),
    )


def _stamp_deferred_observation(observation):
    from write_guard_reconciliation import _stamp_deferred_observation as stamp
    return stamp(observation)


def _reconcile_row_families(governance_dir, persist_state=False, detections_out=None, records_index_out=None, deferred_out=None):
    from write_guard_reconciliation import RowInspection, _reconcile_row_families as reconcile
    return reconcile(
        governance_dir, persist_state, detections_out, records_index_out, deferred_out,
        inspect=RowInspection(_extract_managed_row_records, _credential_index, _judge_row_delta),
        load_baseline=_load_write_guard_state, baseline_exists=state_path_seen,
        surfaces=policies._product_policy("_ROW_FAMILY_TEXT_SURFACES"), schema_version=policies._product_policy("_WRITE_GUARD_STATE_SCHEMA_VERSION"),
        tool=policies._product_policy("_WRITE_GUARD_STATE_TOOL"), now=datetime.now,
    )


def state_path_seen(governance_dir):
    """True when the reconciliation state file exists (surface seen even
    with all managed files gone — the state must shrink, not vanish)."""
    return (governance_dir / policies._product_policy("_WRITE_GUARD_STATE_FILENAME")).is_file()


def _write_guard_state_json(baseline_state):
    """THE serialization of the reconciliation baseline state file —
    delegated to ``write_guard_state.state_json_text`` (single serializer:
    the FEAT-060 consumption transaction's resume sha256 comparisons judge
    these exact bytes, so a second serializer here would be a FIX-292-class
    second shape source)."""
    import write_guard_state
    return write_guard_state.state_json_text(baseline_state)


def _rows_snapshot(records):
    from write_guard_reconciliation import _rows_snapshot as snapshot
    return snapshot(records)


def _credential_index(surface, records, surface_kind='text'):
    from write_guard_reconciliation import _credential_index as index
    return index(surface, records, surface_kind, has_receipt=_row_family_credential_ok)


def _judge_row_delta(surface, rel, records, baseline_rows, issues, surface_kind='text', detections_out=None, family_postures=None, honored_families=frozenset(), deferred_out=None, observation=None):
    from write_guard_reconciliation import _judge_row_delta as judge
    return judge(surface, rel, records, baseline_rows, issues, surface_kind, detections_out, family_postures, honored_families, deferred_out, observation, has_receipt=_row_family_credential_ok)


def _build_violation_detection(surface, surface_kind, rel, record, before_hash=None):
    from write_guard_reconciliation import _build_violation_detection as build_detection
    return build_detection(surface, surface_kind, rel, record, before_hash)


def check_governance_write_shapes(*, persist_state=False, session_id=None, deferred_ledger=False):
    import delivery_check_bindings as delivery_checks

    from governance_write_shapes import StructureChecks, check_governance_write_shapes as inspect
    checks = StructureChecks(
        _plan_tracker_task_row_issues, _evidence_machine_row_issues, check_agent_locks_format,
        delivery_checks._load_execution_packets, delivery_checks._execution_packet_field_issues,
    )
    return inspect(
        paths.GOVERNANCE_DIR, paths.SAMPLE_PATH, paths.ROOT, checks=checks, pin_ledger=pin_ledger,
        reconcile=_reconcile_row_families, state_filename=policies._product_policy("_WRITE_GUARD_STATE_FILENAME"),
        deferred_filename=policies._product_policy("_DEFERRED_LEDGER_FILENAME"), encode_baseline=_write_guard_state_json,
        persist_state=persist_state, session_id=session_id, deferred_ledger=deferred_ledger,
    )


def cmd_change_triage(args):
    import workflow_context_bindings as context_checks
    import workflow_runtime_bindings as runtime_checks

    from change_triage import cmd_change_triage as run
    return run(
        args,
        host_root=paths.HOST_PROJECT_ROOT,
        governance_dir=paths.GOVERNANCE_DIR,
        plan_path=paths.SAMPLE_PATH,
        read_task_rows=context_checks.parse_task_table_rows,
        check_write=_triage_write_structure_guard,
        output_json=runtime_checks.write_cli_json,
    )


def cmd_demand_source_revise(args):
    from change_triage import cmd_demand_source_revise as run
    return run(args, governance_dir=paths.GOVERNANCE_DIR)


def cmd_agent_locks_acquire(args):
    from collaboration_checks import cmd_agent_locks_acquire as run
    return run(
        args, governance_dir=paths.GOVERNANCE_DIR, host_root=paths.HOST_PROJECT_ROOT,
        check_agent_locks_format=check_agent_locks_format,
    )


def cmd_isolation_write_engine(args):
    """Thin entry — isolation-write CLI (FEAT-096 ① write slot)."""

    return cmd_isolation_write(
        args, governance_dir=paths.GOVERNANCE_DIR, repo_root=paths.HOST_PROJECT_ROOT)


def cmd_isolation_snapshot_engine(args):
    """Thin entry — isolation-snapshot CLI (FEAT-096 ②③ review snapshot)."""

    return cmd_isolation_snapshot(
        args, governance_dir=paths.GOVERNANCE_DIR, repo_root=paths.HOST_PROJECT_ROOT)


def cmd_isolation_lease_reclaim_engine(args):
    """Thin entry — isolation-lease-reclaim CLI (FEAT-096 ④ 失权回收)."""

    return cmd_isolation_lease_reclaim(
        args, governance_dir=paths.GOVERNANCE_DIR, repo_root=paths.HOST_PROJECT_ROOT)


def cmd_isolation_status_engine(args):
    """Thin entry — isolation-status CLI (machine-readable world)."""

    return cmd_isolation_status(
        args, governance_dir=paths.GOVERNANCE_DIR, repo_root=paths.HOST_PROJECT_ROOT)


def cmd_isolation_capability_engine(args):
    """Thin entry — isolation-capability CLI (honesty disclosure)."""

    return cmd_isolation_capability(
        args, governance_dir=paths.GOVERNANCE_DIR, repo_root=paths.HOST_PROJECT_ROOT)


def cmd_goal_bridge_engine(args):
    """Thin entry — goal-bridge CLI (all actions)."""

    return cmd_goal_bridge(args, governance_dir=paths.GOVERNANCE_DIR)


def cmd_enforcement_check_engine(args):
    """Thin entry — enforcement-check CLI (FEAT-095 six boundaries)."""

    return cmd_enforcement_check(
        args, governance_dir=paths.GOVERNANCE_DIR, repo_root=paths.HOST_PROJECT_ROOT)


def cmd_governance_write_guard(args):
    from write_guard_cli import cmd_governance_write_guard as run
    return run(args, governance_dir=paths.GOVERNANCE_DIR, check_shapes=check_governance_write_shapes)


_BOOTSTRAP_CHECK_TOOL = "governance-write-guard/release-bootstrap-check"


def check_release_bootstrap_world():
    from release_bootstrap import check_release_bootstrap_world as inspect_world
    return inspect_world(
        governance_dir=paths.GOVERNANCE_DIR,
        tool=_BOOTSTRAP_CHECK_TOOL,
        baseline_filename=policies._product_policy("_WRITE_GUARD_STATE_FILENAME"),
        load_baseline=_load_write_guard_state,
        reconcile=_reconcile_row_families)


def run_release_bootstrap_converge():
    from release_bootstrap import run_release_bootstrap_converge as converge
    return converge(check_shapes=check_governance_write_shapes, check_world=check_release_bootstrap_world)


def cmd_write_guard_bootstrap(args):
    from release_bootstrap import cmd_write_guard_bootstrap as run
    return run(args, check_world=check_release_bootstrap_world, converge=run_release_bootstrap_converge)
