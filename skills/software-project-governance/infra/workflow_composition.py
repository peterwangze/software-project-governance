"""Connect the independent check readers to the installed workflow environment."""

from _thread import RLock

from checks import (
    capability_registry as _capability_registry, evidence_domain as _evidence_domain,
    review_domain as _review_checks, risk_domain,
)
from checks.ci_domain import bind_ci_facts as _bind_ci_facts
from checks.evidence_domain import FACT_BASIS_RE, UNGROUNDED_CLAIM_RE
from checks.manifest import PLUGIN_SCOPE_DIRS, bind_manifest_access as _bind_manifest_access
from checks.review_domain import (
    M5_RECORD_DOC_DIRS, _is_m5_record_doc_path, check_m5_compliance,
    check_m5_compliance_with_record_scope,
)
from contracts import _is_valid_string_list
from hot_governance_facts import FIX_105_SNAPSHOT_DATE_RE, _TASK_ID_IN_REF_RE
from release.context import RepositoryContext
from release.ledger import validate_release_ledger
from release.projection import check_projections, write_projections
from resolve_entry import bind_host_root as _bind_host_root
from workspace_checks import check_plugin_freshness, check_untracked_files
import hot_governance_facts as _hot_facts
import workspace_checks as _workspace_checks
from workflow_public_api import DeferredFamily
import workflow_policy_bindings as policies
import workflow_project_roots as paths


delivery_checks = DeferredFamily("delivery_check_bindings")
governance_checks = DeferredFamily("governance_check_bindings")
host_checks = DeferredFamily("host_check_bindings")
release_checks = DeferredFamily("release_check_bindings")
context_checks = DeferredFamily("workflow_context_bindings")
guard_checks = DeferredFamily("workflow_guard_bindings")


def _effective_engine_command(name, native):
    from workflow_public_api import effective_command
    return effective_command(name, native)


def _effective_release_command(name, native):
    from workflow_public_api import effective_command
    return effective_command(name, native)


def install():
    """Connect the registered commands and the direct readers to the same active paths."""
    _bind_host_root(
        lambda: paths.HOST_PROJECT_ROOT,
        snapshot_paths=lambda: (paths.HOST_PROJECT_ROOT, paths.SESSION_SNAPSHOT_PATH,
                                paths.SAMPLE_PATH, paths.EVIDENCE_PATH),
        triage_roots=lambda: (paths.ROOT, paths.GOVERNANCE_DIR),
    )

    _bind_manifest_access(package_root=lambda: paths.ROOT,
                          display_path=lambda path, root=None: paths._display_path(path, root),
                          git_files=lambda args: paths._git_files(args),
                          scope_dirs=lambda: PLUGIN_SCOPE_DIRS)

    _bind_ci_facts(lambda: (paths.HOST_PROJECT_ROOT, paths.SAMPLE_PATH))

    _review_checks._sources = guard_checks._LegacyReviewSources()

    try:
        from governance_fact_cli import bind_gate_command as _bind_gate_command
    except (ImportError, SyntaxError):
        # Unrelated commands can start. Dispatch reports a broken or missing gate owner.
        pass
    else:
        _bind_gate_command(_effective_engine_command)

    _workspace_checks._product_root = lambda: paths.ROOT
    _workspace_checks._platform_entries = lambda: policies._product_policy("PLATFORM_ENTRY_FILES")
    _workspace_checks.effective_entry = _effective_engine_command

    _review_checks._record_dirs = lambda: M5_RECORD_DOC_DIRS
    _review_checks._scan_for_record_scope = lambda: check_m5_compliance()
    _review_checks._record_path_matches = lambda path: _is_m5_record_doc_path(path)
    _review_checks.effective_m5_entry = _effective_engine_command

    try:
        from host_loader_probes import bind_workflow_dsh as _bind_workflow_dsh
    except ModuleNotFoundError as error:
        if error.name != "host_loader_probes":
            raise
    else:
        _bind_workflow_dsh(
            smoke=lambda **kwargs: release_checks.check_dsh_preset_smoke(**kwargs),
            channels=lambda root: host_checks.check_exploration_channels(root),
            command=_effective_engine_command,
        )

    _capability_registry._root = lambda: paths.ROOT
    _capability_registry._display_path = lambda path, root=None: paths._display_path(path, root)
    _capability_registry._is_valid_string_list = lambda value: _is_valid_string_list(value)

    _evidence_domain._governance_directory = lambda: paths.GOVERNANCE_DIR
    _evidence_domain._task_reference_source = lambda: (paths.EVIDENCE_PATH, governance_checks.expand_task_ids)
    _evidence_domain._evidence_archive_reader = governance_checks._archive_reader
    _evidence_domain._context_projection = lambda: (
        context_checks._context_file, context_checks._context_task, context_checks._extract_task_title_from_line,
        governance_checks._governance_table_cells, delivery_checks._normalize_priority,
        policies._host_policy("GOVERNANCE_CONTEXT_EVIDENCE_TASK_HEADERS"))
    _evidence_domain._state_headers = lambda: policies._host_policy("GOVERNANCE_CONTEXT_EVIDENCE_STATE_HEADERS")
    _evidence_domain._closed_markers = lambda: policies._host_policy("GOVERNANCE_CONTEXT_EVIDENCE_CLOSED_MARKERS")
    _evidence_domain._unfinished_markers = lambda: policies._host_policy("GOVERNANCE_CONTEXT_EVIDENCE_UNFINISHED_MARKERS")

    _evidence_domain._grounding_inputs = lambda: (
        delivery_checks._current_release_impact_entries, FACT_BASIS_RE, UNGROUNDED_CLAIM_RE)
    _evidence_domain._structured_inputs = lambda: (
        delivery_checks._current_release_impact_entries, guard_checks._row_has_governance_store_machine_credential)
    _evidence_domain._goal_inputs = lambda: (
        paths.GOVERNANCE_DIR, governance_checks._active_execution_packet_tasks,
        delivery_checks._load_execution_packets, delivery_checks._validate_product_success_contract)

    _hot_facts.snapshot_date_pattern = lambda: FIX_105_SNAPSHOT_DATE_RE

    risk_domain._risk_path = lambda: paths.RISK_PATH
    risk_domain._plan_path = lambda: paths.SAMPLE_PATH
    risk_domain._task_reference_pattern = lambda: _TASK_ID_IN_REF_RE
    risk_domain._context_readers = lambda: (context_checks._context_file, context_checks._context_task)
    risk_domain._legacy_aliases = lambda: (
        paths.RISK_PATH, paths.SAMPLE_PATH, context_checks._context_file, context_checks._context_task,
        _TASK_ID_IN_REF_RE)

    try:
        from release_validation_cli import bind_release_commands as _bind_release_commands
    except ModuleNotFoundError as error:
        if error.name != "release_validation_cli":
            raise
    else:
        _bind_release_commands(
            ledger=lambda: (paths.HOST_PROJECT_ROOT, lambda: paths.PLUGIN_ROOT, RepositoryContext, validate_release_ledger),
            projection=lambda: (lambda: paths.PLUGIN_ROOT, check_projections, write_projections),
            quality=lambda: policies._product_policy("probe_quality_tools")(),
            command=_effective_release_command,
        )


_install_lock = RLock()
_installed = False


def ensure_installed():
    """Install the public reader callbacks once for this interpreter."""
    global _installed
    with _install_lock:
        if not _installed:
            install()
            _installed = True
