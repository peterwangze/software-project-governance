#!/usr/bin/env python3
"""
Governance Data Archive Script — SYSGAP-030

Implements version-based archiving of governance data (plan-tracker tasks,
evidence-log entries, etc.) with a light-weight Markdown index.

FIX-435 (C2 split continuation): this file is the ENTRY SHELL of the archive
engine family — the dual-root seam (FIX-242 / DEC-080 / RISK-038), the
ROOT-bound path helpers, the same-signature wrappers for every moved
path-bound / patch-surface helper, the core orchestrators
(migrate_by_version / migrate_auto / build_index / verify_archive_integrity
/ rebuild_index / rollback_last_migration), and the CLI main(). The domains
live in the sibling modules:

  archive_parsing / archive_indexing      (FIX-417 — pure parsing / index
                                           extraction faces)
  archive_verdicts                        (FIX-435 — classification /
                                           verdict / explain renderers)
  archive_migration_engine                (FIX-435 — resumable big-table
                                           migration + four-family scan)
  archive_entity_migration                (FIX-435 — decision/risk/evidence
                                           legs + rollback recovery)
  archive_cli                             (FIX-435 — argparse face +
                                           subcommand handlers)

Every ``archive.<name>`` keeps resolving (tests and verify_workflow address
these names directly): pure unchanged-signature names are re-imported;
path-bound names keep same-signature WRAPPERS that resolve their paths from
THIS module's globals at call time, so the FIX-187/FIX-242 ROOT rebind seam
and the tests' function-level patch surface (crash injection /
concurrent-cutover) behave exactly as in the pre-split single module. The
moved impls receive ``host=globals()`` (this module's live namespace) and
read every seam attribute through it at call time — see each sibling
module's docstring.

Core entry points (unchanged faces):
  - migrate_by_version: archive tasks+evidence for a version range
  - migrate_evidence_resumable: batched/journaled RESUMABLE migration
  - scan_row_families: READ-ONLY dry-run scan of the four families
  - build_index / rebuild_index: index build & loss-recovery
  - verify_archive_integrity: index-archive consistency
  - rollback_last_migration: undo most recent migration

Design: ADR-006 (docs/architecture/ADR-006-governance-data-scalability.md)
"""


import json
import os
import re
import sys
from datetime import date
from pathlib import Path


# ── Dual-root model (FIX-242 / DEC-080 / RISK-038; mirrors verify_workflow.py FIX-187) ──
# The plugin installs under a per-version cache dir (e.g.
# .../software-project-governance/0.73.0/) whose copy of this repo ships a
# PHANTOM .governance/ tree. Deriving the governance-facts root from __file__
# (the legacy ``ROOT = parents[3]``) made ``archive.py migrate`` archive cache
# data instead of the host project (FIX-242: python_game dry-run reported 134
# phantom evidence rows from the cache copy).
#
#   PLUGIN_ROOT        — where the plugin's OWN assets live (SKILL.md / core/
#                        manifest.json). Used for the version read
#                        (_latest_released_version). NEVER for host facts.
#
#   ROOT / HOST_PROJECT_ROOT — the project being governed; where the real
#                        .governance/ facts live (plan-tracker.md,
#                        evidence-log.md, ...). Defaults to resolve_entry's
#                        cwd-first host root (FIX-187 semantics), never to
#                        the plugin cache. ``ROOT`` stays the overridable
#                        seam: verify_workflow._load_archive_module rebinds
#                        ``module.ROOT`` / ``module.HOST_PROJECT_ROOT``
#                        (FIX-187 / FIX-242 P3-3), tests patch it, and
#                        archive's own --project-root rebinds it. Paths are
#                        lazy so the rebind is observed at call time.
_LEGACY_ROOT = Path(__file__).resolve().parents[3]


def _resolve_plugin_root():
    """Deferred resolve of PLUGIN_ROOT via resolve_entry.PLUGIN_HOME.

    Falls back to the legacy ``parents[3]`` root (the plugin package root in
    both the dev-repo and the versioned-cache layouts) when resolve_entry
    cannot be imported (e.g. minimal packaging).
    """
    try:
        from resolve_entry import PLUGIN_HOME  # peer import (no cycle)
        # two parents above PLUGIN_HOME (== script parents[3])
        return Path(PLUGIN_HOME).parent.parent
    except Exception:
        return _LEGACY_ROOT


def _resolve_host_root():
    """Deferred resolve of the host project root via resolve_entry.

    resolve_entry.resolve_host_root(None) prefers os.getcwd(). On any failure
    (resolve_entry missing, cwd unusable) fall back to the legacy
    ``parents[3]`` root so dogfood mode (plugin-root == host-root) keeps
    working — the backward-compat path, not a security decision here
    (resolve_entry itself is fail-closed for the /governance entry).
    """
    try:
        from resolve_entry import resolve_host_root  # peer import (no cycle)
        host = resolve_host_root(None)
        if host is not None:
            return Path(host)
    except Exception:
        pass
    return _LEGACY_ROOT


PLUGIN_ROOT = _resolve_plugin_root()
HOST_PROJECT_ROOT = _resolve_host_root()
# ROOT is the HOST-facts seam: verify_workflow.py rebinds it after loading
# this module (FIX-187), tests patch it, --project-root rebinds it. Its
# default is the cwd-derived host root — never the plugin cache.
ROOT = HOST_PROJECT_ROOT


FIRST_MIGRATION_PLAN_SIZE_THRESHOLD = 80 * 1024
TASK_INCREMENTAL_THRESHOLD = 20
FALLBACK_ARCHIVE_DAYS = 90


# ── FIX-435: C2 split domains — re-export + wrapper discipline ──────
# Same discipline as the FIX-417 blocks above: pure unchanged-signature
# names are re-imported so every archive.<name> keeps resolving; path-bound
# and test-patchable names keep same-signature WRAPPERS below (the ROOT
# seam and the mock.patch surface stay at THIS module — see the wrappers
# section). Dependency direction is one-way: archive → cli/engine/entity/
# verdicts/parsing/indexing; no sibling imports archive (that would mint a
# second, un-rebound instance under the isolated spec_from_file_location
# load — verify_workflow._load_archive_module).
import archive_cli as _archive_cli
import archive_entity_migration as _entity
import archive_migration_engine as _engine
import archive_verdicts as _verdicts

from archive_verdicts import (
    _EVIDENCE_KEEP_MARKERS,
    _EVIDENCE_REF_ENTITY_TYPES,
    _EXPLAIN_UNKNOWN_REASONS,
    _REF_FAILURE_SUBSTATE_ORDER,
    _ROW_DATE_RE,
    _evidence_classification_context_digest,
    _finalize_explain,
    _format_auto_summary,
    _format_explain_report,
    _sha256_text,
)
from archive_migration_engine import (
    BIG_TABLE_MIGRATION_BATCH_SIZE,
    BigTableMigrationError,
    DecisionStoreAuthorityConflict,
    RowFamilyMigrationRejected,
    _BIG_TABLE_MIGRATION_DIRNAME,
    _DECISION_AUTHORITY_MARKER_NAME,
    _MIGRATION_JOURNAL_SCHEMA,
    _ROW_FAMILY_WRITE_MIGRATION_REFUSED,
    _SCAN_ROW_FAMILIES,
    _WRITE_MIGRATION_ROW_FAMILIES,
    _atomic_write_text,
    _big_table_target_lock,
    _build_archive_header,
    _guard_row_family_write_migration,
    _migration_batch_path,
    _migration_load_batch,
    _migration_load_journal,
    _migration_write_batch,
    _migration_write_journal,
    _row_family_journal_category,
    _scan_git_commit_anchor,
    _write_archive_file,
    format_family_scan_summary,
    format_family_scan_tsv,
)
from archive_cli import _build_archive_arg_parser



# ── FIX-417: pure parsing/classification face (archive_parsing) ──
# Re-imported here so every archive.<name> keeps resolving (tests call
# these helpers directly); the definitions themselves are pure functions
# with no ROOT/PLUGIN_ROOT dependency and no function-level patch use,
# so moving them cannot change behavior under the FIX-187/FIX-242
# dual-root patch semantics. See archive_parsing.py's module docstring.
from archive_parsing import (
    _DECISION_ID_TOKEN_RE,
    _DECISION_RELATED_COLUMN_HEADER,
    _DECISION_SCHEMA_COLUMNS,
    _EVD_ID_SHAPE_RE,
    _EVIDENCE_ARCHIVE_TABLE_HEADER,
    _OTHER_ENTITY_REF_PREFIXES,
    _RISK_CLOSED_MARKERS,
    _RISK_OPEN_MARKERS,
    _ROW_FAMILY_ARCHIVE_TABLE_HEADERS,
    _ROW_FAMILY_ID_RES,
    _ROW_FAMILY_LINE_PREFIXES,
    _TASK_FAMILY_PREFIXES,
    _UNESCAPED_PIPE_SPLIT_RE,
    _VERIFIED_TASK_ID_ALIASES,
    _WRITER_OP_ANCHOR_RE,
    _WRITER_STATE_MARKER_CHAIN,
    _count_unescaped_pipes,
    _CROSS_ENTITY_PREFIXES,
    _decision_archive_version,
    _decision_narrative_title,
    _decision_related_column_index,
    _find_risk_log_header,
    _find_status_column,
    _find_version_sections,
    _is_risk_closed,
    _is_task_family_id,
    _make_ref_verdict,
    _parse_completed_task_versions,
    _parse_family_row,
    _parse_iso_date,
    _parse_priority_table_tasks,
    _parse_task_status,
    _parse_version_from_title,
    _parse_version_roadmap,
    _parse_version_roadmap_entries,
    _requirement_registry_ids,
    _risk_log_status_column,
    _row_family_archive_table_header,
    _split_ref_ids,
    _split_table_row_escaped_aware,
    _task_status_is_archivable,
    _task_status_is_writer_committed,
    _version_in_range,
    _version_to_tuple,
    _writer_chain_state,
    collect_archivable_task_rows,
    compose_task_archive_lines,
    rewrite_hot_tracker_lines,
)
from archive_indexing import (
    _UNSTRUCTURED_ARCHIVE_PREFIXES,
    _archive_file_damage,
    _damage_description,
    _damage_kind_label,
    _entry_version_for_archive,
    _extract_decisions_from_archive_file,
    _extract_evidence_from_archive_file,
    _extract_risks_from_archive_file,
    _extract_row_families_from_archive_file,
    _extract_tasks_from_archive_file,
    _is_unstructured_archive_file,
    _make_archive_filename,
    _parse_archive_version_range,
    _unstructured_archive_description,
    _unstructured_archive_kind,
    _version_from_archive_filename,
    collect_decision_index_entries,
    collect_evidence_index_entries,
    collect_risk_index_entries,
    collect_task_index_entries,
    count_archive_file_entries,
    count_index_section_entries,
    parse_index_section,
    render_index_markdown,
)


def _gov_dir():
    # ROOT is the host-facts seam (dual-root model above).
    return ROOT / ".governance"


def _archive_dir():
    return _gov_dir() / "archive"


def _index_path():
    return _archive_dir() / "index.md"


def _plan_tracker():
    return _gov_dir() / "plan-tracker.md"


def _evidence_log():
    return _gov_dir() / "evidence-log.md"


def _decision_log():
    return _gov_dir() / "decision-log.md"


def _risk_log():
    return _gov_dir() / "risk-log.md"


# Path getters are used throughout; module-level references updated below.
# Keep convenience aliases for backward compat (computed lazily via property-like
# accessors — but we replace direct constants with function calls below.)


# ── Archive File Management ────────────────────────────────────────

def _ensure_archive_dirs():
    """Create archive directory structure if it doesn't exist."""
    for d in [_archive_dir(),
              _archive_dir() / "tasks",
              _archive_dir() / "evidence",
              _archive_dir() / "decisions",
              _archive_dir() / "risks"]:
        d.mkdir(parents=True, exist_ok=True)


def _get_existing_archive_files(subdir):
    """Get sorted list of existing archive .md files (excluding .gitkeep)."""
    dir_path = _archive_dir() / subdir
    if not dir_path.exists():
        return []
    files = sorted([f for f in dir_path.glob("*.md") if f.name != ".gitkeep"],
                   key=lambda f: f.name)
    return files




# ── FIX-435 wrappers: path-bound / patch-surface faces ───────────────
# Each wrapper keeps the exact pre-split signature and resolves its paths /
# injectables from THIS module's globals at call time (``globals()`` = the
# loaded instance's live namespace), then delegates to the moved impl.
# Behavior contract: same call order, same lazy reads, same interception
# caliber for patch.object(archive, ...) — see FIX-435 in each impl's
# ``host`` argument.


def _make_incremental_archive_filename(version_start, version_end, category="tasks"):
    return _engine._make_incremental_archive_filename_impl(
        _archive_dir() / category, version_start, version_end, category)


def _next_evidence_archive_filename(version_start, version_end):
    return _engine._next_evidence_archive_filename_impl(
        _archive_dir() / "evidence", version_start, version_end)


def _next_family_archive_filename(version_start, version_end, row_family):
    return _engine._next_family_archive_filename_impl(
        _archive_dir() / "evidence", _next_evidence_archive_filename,
        version_start, version_end, row_family)


def _decision_authority_state():
    return _engine._decision_authority_state_impl(_gov_dir())


def _migration_state_dir(category, version_start, version_end):
    return _engine._migration_state_dir_impl(
        _archive_dir(), category, version_start, version_end)


def _migration_journal_path(category, version_start, version_end):
    return _engine._migration_journal_path_impl(
        _migration_state_dir(category, version_start, version_end))


def _build_classification_context(plan_tracker_content=None):
    if plan_tracker_content is None:
        try:
            plan_tracker_content = _plan_tracker().read_text(encoding="utf-8")
        except OSError:
            plan_tracker_content = ""
    return _verdicts._build_classification_context_impl(plan_tracker_content)


def _q6_date_window_fallback(line, version_end):
    end_date = _window_end_release_date(version_end)
    if end_date is None:
        return None
    return _verdicts._q6_date_window_fallback_impl(line, version_end, end_date)


def _decision_narrative_verdict(line, dec_id, anchor_counts, task_versions,
                                ref_verdict, version_end):
    return _verdicts._decision_narrative_verdict(
        line, dec_id, anchor_counts, task_versions, ref_verdict, version_end,
        q6_fallback=_q6_date_window_fallback)


def _classify_evidence_rows(content, task_versions, version_start, version_end,
                            *, context=None):
    if context is None:
        context = _build_classification_context()
    return _verdicts._classify_evidence_rows_impl(
        content, task_versions, version_start, version_end,
        context=context, q6_fallback=_q6_date_window_fallback)


def _classify_rows_for_family(row_family, content, task_versions,
                              version_start, version_end, *, context=None):
    if context is None:
        context = _build_classification_context()
    return _verdicts._classify_rows_for_family_impl(
        row_family, content, task_versions, version_start, version_end,
        context=context, q6_fallback=_q6_date_window_fallback)


def _migrate_decisions(version_start, version_end, task_versions, dry_run=False,
                       explain_out=None):
    return _entity._migrate_decisions_impl(
        version_start, version_end, task_versions, dry_run,
        explain_out=explain_out, host=globals())


def _migrate_risks(version_start, version_end, task_versions, dry_run=False,
                   explain_out=None):
    return _entity._migrate_risks_impl(
        version_start, version_end, task_versions, dry_run,
        explain_out=explain_out, host=globals())


def _migrate_evidence(version_start, version_end, task_versions, dry_run=False,
                      explain_out=None, row_family="EVD"):
    return _entity._migrate_evidence_impl(
        version_start, version_end, task_versions, dry_run,
        explain_out=explain_out, row_family=row_family, host=globals())


def scan_row_families(version_start, version_end, *, families=None,
                      task_versions=None, context=None, content=None,
                      plan_tracker_content=None):
    return _engine.scan_row_families_impl(
        version_start, version_end, families=families,
        task_versions=task_versions, context=context, content=content,
        plan_tracker_content=plan_tracker_content, host=globals())


def write_family_scan_outputs(report, tsv_path=None, json_path=None):
    return _engine.write_family_scan_outputs_impl(
        _gov_dir(), report, tsv_path=tsv_path, json_path=json_path)


def migrate_evidence_resumable(version_start, version_end, *,
                               batch_size=BIG_TABLE_MIGRATION_BATCH_SIZE,
                               dry_run=False, task_versions=None,
                               row_family="EVD"):
    return _engine.migrate_evidence_resumable_impl(
        version_start, version_end, batch_size=batch_size, dry_run=dry_run,
        task_versions=task_versions, row_family=row_family, host=globals())


def _get_migration_archive_group(subdir, archive_file):
    return _entity._get_migration_archive_group_impl(
        subdir, archive_file, host=globals())


def _rollback_task_archive(archive_file):
    return _entity._rollback_task_archive_impl(archive_file, host=globals())


def _rollback_evidence_archive(archive_file):
    return _entity._rollback_evidence_archive_impl(archive_file, host=globals())



def _version_still_covered_by_task_archive(version_str, excluding_file):
    """Return True if another task archive still covers version_str."""
    tasks_dir = _archive_dir() / "tasks"
    if not tasks_dir.exists():
        return False

    for archive_path in tasks_dir.glob("*.md"):
        if archive_path.name == ".gitkeep" or archive_path == excluding_file:
            continue
        parsed_range = _parse_archive_version_range(archive_path.name)
        if not parsed_range:
            continue
        version_start, version_end = parsed_range
        if _version_in_range(version_str, version_start, version_end):
            return True
    return False


def _window_end_release_date(version_end):
    """FEAT-076 (Q6): the release date of the window-end version, from the
    plan-tracker roadmap's published rows (已发布 rows carry the release
    date — FIX-349 taggerdate discipline). None when unresolvable (the
    fallback then refuses to fire — fail-closed, never a guess)."""
    try:
        content = _plan_tracker().read_text(encoding="utf-8")
    except OSError:
        return None
    for entry in _parse_version_roadmap_entries(content):
        if entry.get("version") == version_end and \
                entry.get("status") == "已发布":
            return _parse_iso_date(entry.get("date", ""))
    return None


def _archived_task_versions():
    """FIX-385: task_id → version mapping from already-archived task files.

    Extracted from migrate_by_version's historical-merge loop (single
    source) so the resumable big-table path reuses the same mapping
    discipline. This-run rows keep precedence via setdefault at the caller.
    """
    task_versions = {}
    try:
        for f in sorted((_archive_dir() / "tasks").glob("*.md")):
            if f.name == ".gitkeep":
                continue
            for task_id, _status, version in _extract_tasks_from_archive_file(f):
                if task_id and version and version != "unknown":
                    task_versions.setdefault(task_id, version)
    except Exception:
        pass
    return task_versions


def _evidence_task_versions_standalone():
    """FIX-385: the task_id → version mapping for a STANDALONE (non-
    migrate_by_version) evidence migration: already-archived tasks plus the
    FIX-235 completed-hot mapping from plan-tracker."""
    mapping = _archived_task_versions()
    try:
        content = _plan_tracker().read_text(encoding="utf-8")
    except OSError:
        return mapping
    for task_id, version in _parse_completed_task_versions(content).items():
        mapping.setdefault(task_id, version)
    return mapping


# ── Core Migration ─────────────────────────────────────────────────

def _run_entity_migrations(result, families, version_start, version_end,
                          task_versions, evidence_task_versions,
                          migrate_evidence, dry_run, explain,
                          task_rows_explain):
    """FIX-417 (moved verbatim from migrate_by_version): migrate decision-
    log, risk-log and evidence-log entries whose related tasks have been
    archived, then aggregate the FIX-301 auditable explanation.

    FIX-162 (TD-014) / FIX-164: the migration legs run even when
    tasks_archived==0, as long as historical tasks exist in archive/tasks/
    (or completed hot tasks exist per FIX-235). dry_run only reports
    counts. FIX-301: per-row reasons are collected single-source from the
    same loops (explain_out lists). The legs are not gated on a non-empty
    mapping: with an empty mapping every row classifies as
    no_archived_task_ref / live ref and nothing is written — but the rows
    ARE scanned, so the explanation reports real scanned counts instead of
    a misleading zero. The explain aggregation is unconditional (the tasks
    category aggregates even when migrate_evidence is False — original
    semantics preserved).
    """
    decision_rows_explain = []
    risk_rows_explain = []
    evidence_rows_explain = []
    if migrate_evidence:
        try:
            result["decisions_archived"] = _migrate_decisions(
                version_start, version_end, task_versions, dry_run,
                explain_out=decision_rows_explain
            )
        except DecisionStoreAuthorityConflict as exc:
            # FIX-385 衔接面: DEC is store-authoritative — the DECISION
            # category defers to the cutover ticket's store route while the
            # other categories migrate normally. Loud, never silent: the
            # deferral is recorded on the result and in the CLI output (the
            # decision rows stay hot, nothing is dropped or rewritten).
            # REVIEW-FIX-385-R0 F-1: the full refusal payload (including the
            # in_lock recheck marker) flows through.
            result["decision_migration_deferred"] = dict(exc.payload)
        result["risks_archived"] = _migrate_risks(
            version_start, version_end, task_versions, dry_run,
            explain_out=risk_rows_explain
        )
        # FEAT-076: the evidence leg carries every requested family. EVD
        # keeps its legacy result slot (evidence_archived — Check 27 and
        # the CLI print it); each family's count additionally lands in
        # row_families_archived so the ALL pass is fully auditable.
        family_explain = {"EVD": evidence_rows_explain}
        for family in families:
            if family != "EVD":
                family_explain[family] = []
            count = _migrate_evidence(
                version_start, version_end, evidence_task_versions, dry_run,
                explain_out=family_explain[family], row_family=family
            )
            result["row_families_archived"][family] = count
            if family == "EVD":
                result["evidence_archived"] = count
        evidence_rows_explain.extend(
            row for family in ("REVIEW", "TRIAGE", "RECO")
            if family in family_explain for row in family_explain[family]
        )

    # FIX-301: aggregate the auditable explanation (all four categories) so
    # the dry-run report can explain EVERY number it prints — including the
    # zero-archivable case that used to be a black box.
    if explain is not None:
        explain["tasks"] = _finalize_explain(task_rows_explain)
        explain["decisions"] = _finalize_explain(decision_rows_explain)
        explain["risks"] = _finalize_explain(risk_rows_explain)
        explain["evidence"] = _finalize_explain(evidence_rows_explain)
        explain["versions_range"] = (version_start, version_end)


def migrate_by_version(version_start, version_end, dry_run=False, migrate_evidence=True,
                       explain=None, row_family="EVD"):
    """Archive completed tasks (and optionally evidence) for a version range.

    Args:
        version_start: e.g. "0.11.0"
        version_end: e.g. "0.24.0"
        dry_run: if True, report what would be done but don't modify files
        migrate_evidence: if True, also archive evidence entries for archived tasks
        explain: optional dict; when provided it is populated with the
            FIX-301 auditable dry-run explanation — per category
            (tasks/decisions/risks/evidence) the five numbers
            scanned/parsed/would_archive/retained/unknown_structure plus a
            per-row {"id","reason","detail"} list collected single-source
            from the migration loops themselves.
        row_family: FEAT-076 — one of the four admitted families (EVD is
            the backward-compatible default, one EVD leg exactly as
            before), or ``"ALL"`` to carry ALL FOUR families in one pass
            (the 0.93 steady-state M-8 semantics: every closed cycle's
            EVD + REVIEW + TRIAGE + RECO rows migrate together). Family
            counts land in ``row_families_archived``.

    Returns:
        dict with keys: success, dry_run, tasks_archived, tasks_remaining,
                        evidence_archived, archive_files_created, details
    """
    if row_family == "ALL":
        families = ("EVD", "REVIEW", "TRIAGE", "RECO")
    else:
        _guard_row_family_write_migration(row_family)
        families = (row_family,)
    result = {
        "success": False,
        "dry_run": dry_run,
        "tasks_archived": 0,
        "tasks_remaining": 0,
        "evidence_archived": 0,
        "decisions_archived": 0,
        "risks_archived": 0,
        "row_families_archived": {},
        "decision_migration_deferred": None,
        "archive_files_created": [],
        "details": "",
    }

    task_rows_explain = []  # FIX-301: per-row reasons (tasks category)

    if not dry_run:
        _ensure_archive_dirs()

    if not _plan_tracker().exists():
        result["details"] = "plan-tracker.md not found"
        if explain is not None:
            for cat in ("tasks", "decisions", "risks", "evidence"):
                explain[cat] = _finalize_explain([])
        return result

    content = _plan_tracker().read_text(encoding="utf-8")
    sections, lines = _find_version_sections(content)

    # FIX-158 dual scan + FIX-301 per-row notes: pure stage helper (the
    # same classification semantics — see collect_archivable_task_rows).
    already_archived_tasks = _get_archived_task_ids()
    archived_task_lines, archive_body_lines, tasks_remaining, notes = \
        collect_archivable_task_rows(
            content, sections, version_start, version_end,
            already_archived_tasks)
    task_rows_explain.extend(notes)
    result["tasks_remaining"] = tasks_remaining
    result["tasks_archived"] = len({tid for _, _, tid, _ in
                                    archived_task_lines})

    # FIX-162 (TD-014): build task_versions lookup (this-run + already-archived
    # historical tasks) so decision/risk migration can proceed even when the
    # current run archives zero new tasks but historical tasks exist.
    task_versions = {}
    for _idx, _line, _tid, _ver in archived_task_lines:
        task_versions.setdefault(_tid, _ver)
    # Also include already-archived tasks (from prior runs) so decisions/risks
    # referencing fully-historical tasks migrate even on a fresh run.
    # FIX-385: the loop is extracted to _archived_task_versions() (single
    # source — the resumable big-table path reuses the same discipline).
    for _tid, _ver in _archived_task_versions().items():
        task_versions.setdefault(_tid, _ver)

    # FIX-235: the EVIDENCE mapping additionally includes COMPLETED tasks that
    # remain hot in plan-tracker (rows deliberately kept for full traceability
    # per EVD-854). Their 目标版本 resolves in-range evidence rows even though
    # the task row is not physically archived. Decisions/risks keep the
    # archive-only mapping — their contract requires the related task to be
    # archived.
    evidence_task_versions = dict(task_versions)
    for task_id, version in _parse_completed_task_versions(content).items():
        evidence_task_versions.setdefault(task_id, version)

    _run_entity_migrations(result, families, version_start, version_end,
                           task_versions, evidence_task_versions,
                           migrate_evidence, dry_run, explain,
                           task_rows_explain)

    if result["tasks_archived"] == 0:
        result["success"] = True
        result["details"] = f"No completed tasks found in version range v{version_start}~v{version_end}"
        return result

    # Determine archive filename
    archive_filename = _make_incremental_archive_filename(version_start, version_end, "tasks")
    archive_path = _archive_dir() / "tasks" / archive_filename

    # Check existing archive files for prev/next links
    existing_files = _get_existing_archive_files("tasks")
    existing_names = [f.name for f in existing_files]

    prev_file = existing_names[-1] if existing_names else None

    # Build archive body with version sections (FIX-172 unconditional
    # write — pure stage helper, see compose_task_archive_lines).
    archive_lines = compose_task_archive_lines(sections, archive_body_lines)

    # Build header
    header = _build_archive_header(
        version_start, version_end, "tasks",
        result["tasks_archived"],
        prev_file=prev_file,
    )

    if dry_run:
        result["success"] = True
        result["details"] = (f"Dry-run: would archive {result['tasks_archived']} tasks "
                            f"({result['decisions_archived']} decisions, "
                            f"{result['risks_archived']} risks, "
                            f"{result['evidence_archived']} evidence) "
                            f"from v{version_start}~v{version_end} to {archive_filename}")
        result["archive_files_created"] = [archive_filename]
        return result

    _write_archive_file(archive_path, header, archive_lines)
    result["archive_files_created"].append(f"archive/tasks/{archive_filename}")

    # Rewrite the hot plan-tracker (pure stage helper — sample-table rows
    # excluded, in-range version headers marked; see
    # rewrite_hot_tracker_lines).
    final_lines = rewrite_hot_tracker_lines(lines, archived_task_lines,
                                            sections, version_start,
                                            version_end)

    if not dry_run:
        _plan_tracker().write_text("\n".join(final_lines), encoding="utf-8")

    # (FIX-162 decision/risk + FIX-164 evidence migration already executed
    # above, before the tasks_archived==0 early-return, so it runs even with
    # no new tasks.)

    result["success"] = True
    result["details"] = (f"Archived {result['tasks_archived']} tasks "
                        f"from v{version_start}~v{version_end}")
    return result


# ── Index Building ─────────────────────────────────────────────────













# FIX-176: helpers for registering non-structured archive files (free-prose
# archives like narrative-* / recent-completed-* that contain no extractable
# task/evidence/decision/risk rows). Such files must still be referenced by
# the index so verify_archive_integrity Check 2 does not flag them as orphans.









def _get_archived_task_ids():
    """Return task IDs already present in archive task files."""
    archived = set()
    task_dir = _archive_dir() / "tasks"
    if not task_dir.exists():
        return archived
    for f in sorted(task_dir.glob("*.md")):
        if f.name == ".gitkeep":
            continue
        for task_id, _status, _version in _extract_tasks_from_archive_file(f):
            archived.add(task_id)
    return archived


# ── Archive-file damage classification (FIX-384 / B-7a) ────────────
#
# The index-rebuild path must survive a disaster that also damaged the
# ARCHIVE files themselves: the rebuild reads whatever is still readable
# and reports the damage, never crashing and never silently dropping a
# file (which would turn it into a verify Check 2 orphan and make the
# post-rebuild integrity PASS unreachable).







def build_index():
    """Scan all archive files and build/rebuild archive/index.md.

    The index is a Markdown file with tables mapping entry IDs to
    their archive file locations.

    FIX-384 (B-7a): this function IS the rebuild engine for index loss and
    corruption — it regenerates index.md deterministically from the archive
    files (the index is a pure derivative: rebuild restores the view, never
    creates data). Content-level damage in the ARCHIVE files themselves no
    longer crashes the rebuild or silently orphans a file: empty / unreadable
    / row-less files are registered in the 非结构化归档 section with a damage
    label, and every damaged file is reported in ``damaged_files``.

    FIX-417: the per-category collectors and the Markdown renderer are pure
    stage helpers (collect_*_index_entries / render_index_markdown in
    archive_parsing); this function keeps the ROOT-bound glob/write face.

    Returns:
        dict with keys: status, task_entries, evidence_entries,
                        decision_entries, risk_entries, narrative_entries,
                        damaged_files
    """
    result = {
        "status": "created",
        "task_entries": 0,
        "evidence_entries": 0,
        "decision_entries": 0,
        "risk_entries": 0,
        "narrative_entries": 0,
        "damaged_files": [],
    }

    _ensure_archive_dirs()

    def _md_files(subdir):
        return [f for f in sorted((_archive_dir() / subdir).glob("*.md"))
                if f.name != ".gitkeep"]

    task_entries, narrative_entries, damaged_files = \
        collect_task_index_entries(_md_files("tasks"))
    evidence_entries, family_entries, ev_narrative, ev_damaged = \
        collect_evidence_index_entries(_md_files("evidence"))
    narrative_entries.extend(ev_narrative)
    damaged_files.extend(ev_damaged)
    decision_entries, dec_narrative, dec_damaged = \
        collect_decision_index_entries(_md_files("decisions"))
    narrative_entries.extend(dec_narrative)
    damaged_files.extend(dec_damaged)
    risk_entries, risk_narrative, risk_damaged = \
        collect_risk_index_entries(_md_files("risks"))
    narrative_entries.extend(risk_narrative)
    damaged_files.extend(risk_damaged)

    result["task_entries"] = len(task_entries)
    result["evidence_entries"] = len(evidence_entries)
    result["family_entries"] = len(family_entries)
    result["decision_entries"] = len(decision_entries)
    result["risk_entries"] = len(risk_entries)
    result["narrative_entries"] = len(narrative_entries)
    result["damaged_files"] = damaged_files

    index_lines = render_index_markdown(
        task_entries, evidence_entries, family_entries, decision_entries,
        risk_entries, narrative_entries)

    _index_path().write_text("\n".join(index_lines), encoding="utf-8")

    return result


# ── Integrity Verification ─────────────────────────────────────────

def verify_archive_integrity():
    """Verify archive integrity: index-archive consistency.

    Checks:
      1. Every file referenced in index.md exists
      2. Every entry in archive files has a corresponding index entry
      3. No orphan archive files (files exist but not in index)

    FIX-417: the per-section reference parser and the two per-category
    counters are pure stage helpers (parse_index_section /
    count_archive_file_entries / count_index_section_entries in
    archive_parsing); this function keeps the ROOT-bound file faces.

    Returns:
        dict with keys: pass, issues (list of issue strings),
                        total_archived_tasks, total_index_entries
    """
    result = {
        "pass": True,
        "issues": [],
        "total_archived_tasks": 0,
        "total_index_entries": 0,
    }

    _ensure_archive_dirs()

    # If no index and no archive files, pass trivially
    archive_files = []
    for subdir in ["tasks", "evidence", "decisions", "risks"]:
        d = _archive_dir() / subdir
        if d.exists():
            for f in d.glob("*.md"):
                if f.name != ".gitkeep":
                    archive_files.append((subdir, f))

    if not archive_files and not _index_path().exists():
        result["pass"] = True
        return result

    # If there are archive files but no index, that's an issue
    if archive_files and not _index_path().exists():
        result["pass"] = False
        result["issues"].append(
            f"有 {len(archive_files)} 个归档文件但 index.md 不存在。"
            f"运行 build_index() 重建索引。"
        )
        return result

    if not _index_path().exists():
        result["pass"] = True
        return result

    # Parse index
    index_content = _index_path().read_text(encoding="utf-8")
    index_lines = index_content.split("\n")

    # Extract file references from each index section
    index_task_refs = parse_index_section(index_lines, "Task 索引")
    index_evidence_refs = parse_index_section(index_lines, "Evidence 索引")
    index_decision_refs = parse_index_section(index_lines, "Decision 索引")
    index_risk_refs = parse_index_section(index_lines, "Risk 索引")
    # FEAT-076: the unlocked row families' section (file column is
    # parts[4]: | 行ID | 行族 | 关联任务 | 归档文件 |).
    index_family_refs = parse_index_section(
        index_lines, "行族索引（REVIEW/TRIAGE/RECO）")
    # FIX-176: also collect references from the non-structured archive section
    # so free-prose files (narrative-*, etc.) count as "referenced" for Check 2.
    index_narrative_refs = parse_index_section(index_lines, "非结构化归档")

    all_index_refs = (
        index_task_refs | index_evidence_refs | index_decision_refs
        | index_risk_refs | index_family_refs | index_narrative_refs
    )

    # Check 1: Every referenced archive file exists
    for ref in all_index_refs:
        # ROOT is the host-facts seam (FIX-242 dual-root model above).
        filepath = ROOT / ".governance" / ref
        if not filepath.exists():
            result["pass"] = False
            result["issues"].append(f"索引引用的归档文件不存在: {ref}")

    # Check 2: Every archive file is referenced in index
    actual_files = set()
    for subdir, f in archive_files:
        rel = f"archive/{subdir}/{f.name}"
        actual_files.add(rel)

    unreferenced = actual_files - all_index_refs
    if unreferenced:
        result["pass"] = False
        for f in sorted(unreferenced):
            result["issues"].append(f"归档文件未在索引中记录: {f}")

    # Check 3: Extract IDs from archive files and count, per-category
    file_counts = count_archive_file_entries(archive_files)

    result["total_archived_tasks"] = file_counts["tasks"] + file_counts["evidence"]

    # Count index entries per-category. The index has separate sections
    # (## Task 索引 / ## Evidence 索引 / ## Decision 索引 / ## Risk 索引).
    index_counts = count_index_section_entries(index_lines)

    result["total_index_entries"] = sum(index_counts.values())

    # FIX-163 (TD-015): cross-check per-category. Flag any category where
    # file count != index count (drift detection). Per-category avoids the
    # FIX-162 coupling false-positive (decisions/risks counted on both sides).
    for cat in ("tasks", "evidence", "decisions", "risks", "families"):
        if file_counts[cat] != index_counts[cat]:
            result["pass"] = False
            result["issues"].append(
                f"Archive/index count mismatch (Check 3, category={cat}): "
                f"archive files contain {file_counts[cat]} but index.md "
                f"has {index_counts[cat]}. Run `archive.py build-index` to "
                f"rebuild the index, then re-verify."
            )

    return result


# ── Index Rebuild — index-loss / corruption recovery (FIX-384 / B-7a) ──

def rebuild_index():
    """Rebuild archive/index.md from the archive files, then verify integrity.

    FIX-384 (B-7a): the explicit recovery path for a lost or corrupted index.
    The index is a pure DERIVATIVE of the archive files — the rebuild restores
    the view, never creates data. Pipeline:

      1. Snapshot whether the index exists (and its content) for the
         change report.
      2. build_index() — deterministic regeneration; damage-tolerant at
         archive-file granularity (empty / unreadable / row-less files are
         registered in 非结构化归档 and reported in ``damaged_files``).
      3. verify_archive_integrity() — the rebuilt index must PASS against the
         same archive files it was derived from (closes the recovery loop;
         the same PASS that `check-archive-integrity` reports).

    Idempotency: with an already-intact index the regeneration is an
    equivalent no-op — ``changed`` is False and no archive file is touched.

    Returns:
        build_index()'s result dict extended with:
          index_existed  — whether index.md existed before the rebuild
          changed        — whether the rebuild altered the index content
          verify_pass    — archive integrity after the rebuild
          verify_issues  — integrity issues (empty when verify_pass)
    """
    index_existed = _index_path().exists()
    old_content = None
    if index_existed:
        try:
            # An unreadable index counts as missing for comparison purposes
            # (its content cannot participate in an equality check).
            old_content = _index_path().read_text(
                encoding="utf-8", errors="replace"
            )
        except OSError:
            old_content = None

    result = build_index()
    result["index_existed"] = index_existed
    result["changed"] = True
    if index_existed and old_content is not None:
        try:
            new_content = _index_path().read_text(
                encoding="utf-8", errors="replace"
            )
        except OSError:
            new_content = None
        result["changed"] = new_content != old_content

    verify = verify_archive_integrity()
    result["verify_pass"] = verify["pass"]
    result["verify_issues"] = list(verify["issues"])
    return result


def rollback_last_migration():
    """Rollback the most recent migration by:
    1. Finding the most recently modified archive file
    2. Rolling back same-name task/evidence archive files as one migration group
    3. Merging their content back into the hot files and removing archive files
    4. Updating the index

    Returns:
        dict with keys: success, rolled_back_file, rolled_back_files, details
    """
    result = {
        "success": False,
        "rolled_back_file": None,
        "rolled_back_files": [],
        "details": "",
    }

    _ensure_archive_dirs()

    # Find most recently modified archive task file
    recent_files = []
    for subdir in ["tasks", "evidence"]:
        d = _archive_dir() / subdir
        if d.exists():
            for f in d.glob("*.md"):
                if f.name != ".gitkeep":
                    stat_result = f.stat()
                    incremental_priority = 1 if "-incremental-" in f.name else 0
                    recent_files.append(
                        (stat_result.st_mtime_ns, incremental_priority, f.name, subdir, f)
                    )

    if not recent_files:
        result["details"] = "没有找到归档文件，无法回滚。"
        return result

    recent_files.sort(reverse=True)
    _mtime_ns, _incremental_priority, _name, subdir, archive_file = recent_files[0]

    migration_files = _get_migration_archive_group(subdir, archive_file)
    result["rolled_back_files"] = [
        f"archive/{group_subdir}/{group_file.name}"
        for group_subdir, group_file in migration_files
    ]
    result["rolled_back_file"] = ", ".join(result["rolled_back_files"])

    details = []
    for group_subdir, group_file in migration_files:
        if group_subdir == "tasks":
            details.append(_rollback_task_archive(group_file))
        elif group_subdir == "evidence":
            details.append(_rollback_evidence_archive(group_file))

    result["success"] = bool(details)
    if result["success"]:
        result["details"] = "已回滚 " + "; ".join(details)

    # Rebuild index after rollback
    build_index()

    return result


# ── Version Roadmap Parsing ─────────────────────────────────────────



# ── Auto Migration ──────────────────────────────────────────────────





def _days_since_file(path):
    if not path.exists():
        return None
    modified = date.fromtimestamp(path.stat().st_mtime)
    return (date.today() - modified).days


def _latest_released_version():
    """Retained utility (fallback/consumers may use it); not part of the
    --auto endpoint chain (DEC-140).

    FIX-235: return the authoritative current product version.

    Read from the SKILL.md frontmatter (DEC-096: single source of truth for
    the workflow version; kept in sync with manifest.json/plugin.json by
    check-version-consistency). Between releases this equals the latest
    released version. FIX-242: read from PLUGIN_ROOT (plugin assets), never
    from the host root — the host project does not ship the plugin's
    SKILL.md. Returns None when unreadable.
    """
    skill = PLUGIN_ROOT / "skills/software-project-governance/SKILL.md"
    try:
        content = skill.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(
        r"^version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$",
        content,
        re.MULTILINE,
    )
    return match.group(1) if match else None


def _release_ledger_released_versions():
    """FIX-243 (DEC-140 方案 A): released versions from the release ledger.

    Reads ``PLUGIN_ROOT / skills/software-project-governance/core/releases``
    (``*.json``) — the plugin's declarative release ledger, never the host
    root. A manifest counts as released when ``lifecycle_state == "released"``
    (top-level or effective_state) and ``withdrawn`` is not truthy
    (top-level or effective_state — 0.66.1 is withdrawn/untrusted and must
    be excluded). Single-file parse failures are skipped fail-open; returns
    [] when the ledger is unreadable or has no released versions.
    """
    releases_dir = (
        PLUGIN_ROOT / "skills/software-project-governance" / "core" / "releases"
    )
    try:
        paths = sorted(releases_dir.glob("*.json"))
    except OSError:
        return []
    released = []
    for path in paths:
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue  # fail-open: a corrupt manifest never blocks archiving
        if not isinstance(manifest, dict):
            continue
        effective = manifest.get("effective_state")
        if not isinstance(effective, dict):
            effective = {}
        lifecycle = manifest.get("lifecycle_state") or effective.get(
            "lifecycle_state"
        )
        withdrawn = manifest.get("withdrawn") or effective.get("withdrawn")
        if lifecycle != "released" or withdrawn:
            continue
        version = manifest.get("version")
        # Type guard: a non-string version (e.g. a number) would make
        # _version_to_tuple's regex raise TypeError — skip the file so a
        # single malformed manifest never crashes the ledger read (fail-open).
        if not isinstance(version, str) or _version_to_tuple(version) is None:
            continue
        released.append(version)
    released.sort(key=_version_to_tuple)
    return released


def _auto_archive_bounded_endpoint():
    """FIX-243 (DEC-140 方案 A): cooldown-bounded --auto range end.

    Returns the second-newest released ledger version — the newest released
    version's evidence stays hot (≥1 release-period cooldown). Returns None
    when the ledger has fewer than 2 released versions (caller falls back to
    the roadmap-derived endpoint).
    """
    released = _release_ledger_released_versions()
    if len(released) < 2:
        return None
    return released[-2]


def analyze_auto_archive_candidates():
    """Analyze whether continuous auto archive should run.

    This pure analysis is shared by archive.py --auto and verify_workflow.py.
    It covers the FIX-063 trigger loop:
      - first migration threshold
      - release-forced incremental archive when index already exists
      - task-count incremental threshold
      - 90-day fallback
    """
    result = {
        "success": False,
        "should_archive": False,
        "skipped": False,
        "reason": "",
        "triggers": [],
        "versions_archived": [],
        "versions_range": None,
        "tasks_archived": 0,
        "evidence_archived": 0,
        "decisions_archived": 0,
        "risks_archived": 0,
        "plan_tracker_size": 0,
        "published_count": 0,
        "index_exists": False,
        "days_since_archive": None,
    }

    if not _plan_tracker().exists():
        result["skipped"] = True
        result["reason"] = "plan-tracker.md 不存在"
        return result

    result["success"] = True
    result["plan_tracker_size"] = _plan_tracker().stat().st_size
    result["index_exists"] = _index_path().exists()
    result["days_since_archive"] = _days_since_file(_index_path())

    content = _plan_tracker().read_text(encoding="utf-8")
    roadmap_entries = _parse_version_roadmap_entries(content)
    published = [
        entry for entry in roadmap_entries
        if entry.get("status") == "已发布"
    ]
    published.sort(key=lambda entry: _version_to_tuple(entry["version"]))
    result["published_count"] = len(published)

    if len(published) < 2:
        result["skipped"] = True
        result["reason"] = f"已发布版本数不足（{len(published)} < 2），跳过归档"
        return result

    archive_entries = published[:-1]
    version_start = archive_entries[0]["version"]
    version_end = archive_entries[-1]["version"]
    # FIX-243 (DEC-140 方案 A): the --auto endpoint is bounded by the
    # release ledger — the second-newest released version (≥1 release-period
    # cooldown), so the current release window's evidence stays hot. The
    # roadmap 状态 column lags actual releases, so the ledger is the reliable
    # advance source. Advance-only (FIX-235 no-regression): the bounded
    # endpoint is used only when it is at least the roadmap-derived end;
    # otherwise the roadmap end wins (never regress below it).
    bounded_endpoint = _auto_archive_bounded_endpoint()
    bounded_tuple = (
        _version_to_tuple(bounded_endpoint)
        if bounded_endpoint is not None
        else None
    )
    roadmap_end_tuple = _version_to_tuple(version_end)
    if (
        bounded_tuple is not None
        and roadmap_end_tuple is not None
        and bounded_tuple >= roadmap_end_tuple
    ):
        version_end = bounded_endpoint
    result["versions_archived"] = [
        entry["version"] for entry in published
        if (_version_to_tuple(entry["version"]) is not None
            and _version_to_tuple(entry["version"])
            <= _version_to_tuple(version_end))
    ]
    result["versions_range"] = (version_start, version_end)

    # FIX-301: the dry-run pre-check now also collects the auditable
    # per-category explanation (scanned/parsed/would_archive/retained/
    # unknown_structure + per-row reasons), single-sourced from the migration
    # loops. It is attached even when the run is skipped — the "triggers
    # satisfied but nothing archivable" case is exactly the black box this
    # explanation exists to eliminate.
    explain = {}
    pre_check = migrate_by_version(
        version_start, version_end, dry_run=True, explain=explain,
        row_family="ALL"  # FEAT-076: Check 27's face covers all four
                          # families — the steady-state closure caliber.
    )
    result["tasks_archived"] = pre_check.get("tasks_archived", 0)

    # FIX-164: a run is actionable if ANY category has migratable data — not
    # just tasks. All in-range tasks may be pre-archived (tasks_archived==0)
    # while evidence/decisions/risks referencing those historical tasks still
    # need migrating. This was the evidence-log bloat root cause.
    result["evidence_archived"] = pre_check.get("evidence_archived", 0)
    result["decisions_archived"] = pre_check.get("decisions_archived", 0)
    result["risks_archived"] = pre_check.get("risks_archived", 0)
    # FEAT-076: the four-family face feeds the actionable judgment too —
    # any family's candidates make the run actionable (Check 27 closure).
    result["row_families_archived"] = pre_check.get("row_families_archived", {})
    # FIX-385 衔接面: even the dry-run pre-check surfaces the deferral.
    result["decision_migration_deferred"] = pre_check.get(
        "decision_migration_deferred")
    migratable_total = (result["tasks_archived"] + result["evidence_archived"]
                        + result["decisions_archived"] + result["risks_archived"]
                        # non-EVD families only — EVD is already counted in
                        # evidence_archived (no double counting).
                        + sum(v for k, v in result["row_families_archived"].items()
                              if k != "EVD"))

    # FIX-158: do NOT early-return when tasks_archived==0. The original code
    # returned here, which made release_forced / fallback_90d dead code
    # (AUDIT-125 root cause #2). Triggers must be evaluated regardless of
    # task count, because release_forced depends only on index_exists and
    # fallback_90d depends only on dates. We record a note instead of skipping.
    no_archivable_tasks = migratable_total == 0

    if (
        not result["index_exists"]
        and result["plan_tracker_size"] > FIRST_MIGRATION_PLAN_SIZE_THRESHOLD
    ):
        result["triggers"].append("first_migration")

    if result["index_exists"]:
        result["triggers"].append("release_forced")

    if result["tasks_archived"] >= TASK_INCREMENTAL_THRESHOLD:
        result["triggers"].append("task_incremental")

    version_end_entry = archive_entries[-1]
    version_end_date = _parse_iso_date(version_end_entry.get("date", ""))
    if version_end_date and (date.today() - version_end_date).days >= FALLBACK_ARCHIVE_DAYS:
        result["triggers"].append("fallback_90d")
    elif result["days_since_archive"] is not None and result["days_since_archive"] >= FALLBACK_ARCHIVE_DAYS:
        result["triggers"].append("fallback_90d")

    result["triggers"] = sorted(set(result["triggers"]))
    # FIX-158: should_archive requires BOTH a trigger AND archivable tasks.
    # A trigger firing with zero archivable tasks (e.g. all already archived)
    # is NOT an actionable archive signal — reporting it as should_archive=True
    # would make check-archive-integrity perpetually flag a clean state.
    result["should_archive"] = bool(result["triggers"]) and not no_archivable_tasks
    result["explain"] = explain  # FIX-301: auditable explanation for both paths
    if not result["should_archive"]:
        result["skipped"] = True
        if result["triggers"] and no_archivable_tasks:
            result["reason"] = (
                f"归档范围 v{version_start}~v{version_end} 触发器满足（{', '.join(result['triggers'])}）"
                "但无可归档数据——可能已全部归档或格式未被识别"
            )
        else:
            result["reason"] = (
                "归档触发条件未满足"
                f"（tasks={result['tasks_archived']}, evidence={result['evidence_archived']}, "
                f"plan={result['plan_tracker_size']} bytes）"
            )
    return result

def migrate_auto(dry_run=False, row_family="ALL"):
    """Auto-detect version range from plan-tracker roadmap and migrate data.

    FEAT-076 (0.93.0): ``row_family`` defaults to ``"ALL"`` — the steady-
    state M-8 semantics carry all four families (EVD + REVIEW + TRIAGE +
    RECO) in one pass. An explicit single family (e.g. "EVD") restores the
    0.92 behavior for scoped operations.

    Pipeline:
    1. Parse version roadmap → filter published versions
    2. Determine archive range [oldest, bounded end] — the end is the
       second-newest released version from the release ledger (DEC-140 方案 A,
       FIX-243), falling back to the roadmap-derived second-newest published
       row when the ledger has fewer than 2 released versions
    3. Pre-check dry-run → skip if no data
    4. Idempotency: skip if archive/index.md exists
    5. Execute migrate_by_version + build_index + verify
    6. Calculate file size changes
    7. Return structured summary dict

    Args:
        dry_run: if True, preview without modifying files

    Returns:
        dict with keys: success, skipped, reason, versions_archived,
        versions_range, tasks_archived, evidence_archived,
        plan_tracker_before, plan_tracker_after,
        evidence_log_before, evidence_log_after,
        archive_files_created, verify_pass, details
    """
    if row_family == "ALL":
        pass  # the four admitted families, dispatched inside migrate_by_version
    else:
        _guard_row_family_write_migration(row_family)
    result = {
        "success": False,
        "skipped": False,
        "reason": "",
        "versions_archived": [],
        "versions_range": None,
        "tasks_archived": 0,
        "evidence_archived": 0,
        "row_families_archived": {},
        "plan_tracker_before": 0,
        "plan_tracker_after": 0,
        "evidence_log_before": 0,
        "evidence_log_after": 0,
        "archive_files_created": [],
        "verify_pass": False,
        "dry_run": bool(dry_run),
        "triggers": [],
        "decision_migration_deferred": None,
        "details": "",
    }

    if not dry_run:
        _ensure_archive_dirs()

    analysis = analyze_auto_archive_candidates()
    result["versions_archived"] = analysis.get("versions_archived", [])
    result["versions_range"] = analysis.get("versions_range")
    result["tasks_archived"] = analysis.get("tasks_archived", 0)
    result["evidence_archived"] = analysis.get("evidence_archived", 0)
    result["decisions_archived"] = analysis.get("decisions_archived", 0)
    result["risks_archived"] = analysis.get("risks_archived", 0)
    result["triggers"] = analysis.get("triggers", [])
    result["explain"] = analysis.get("explain", {})  # FIX-301
    # FIX-416: propagate the family face to the dry-run result too — it
    # previously stayed {} until the real run, so a dry-run preview read
    # "0 证据" while the ALL-caliber candidates actually lived in the
    # REVIEW/TRIAGE/RECO families (the 54-vs-28 black box).
    result["row_families_archived"] = analysis.get(
        "row_families_archived", {})
    # FIX-385 衔接面: propagate the deferral from the pre-check so the
    # dry-run path reports it too (the real-run copy happens below).
    result["decision_migration_deferred"] = analysis.get(
        "decision_migration_deferred")

    if analysis.get("skipped") or not analysis.get("should_archive"):
        result["success"] = analysis.get("success", False)
        result["skipped"] = True
        result["reason"] = analysis.get("reason", "")
        return result

    version_start, version_end = result["versions_range"]

    # Dry-run mode: report preview and return
    if dry_run:
        result["success"] = True
        # FIX-416: the preview must carry the four-family face — an
        # EVD-only summary next to an ALL-caliber analysis is exactly the
        # "would_archive 54 but only 28 migrated" ambiguity.
        family_face = ", ".join(
            f"{k}={v}" for k, v in sorted(
                (result.get("row_families_archived") or {}).items()) if v
        )
        result["details"] = (
            f"Dry-run: 将归档 {result['tasks_archived']} 个 task, "
            f"{result['evidence_archived']} 条证据, "
            f"{result['decisions_archived']} 条决策, "
            f"{result['risks_archived']} 条风险 "
            + (f"(行家族: {family_face}) " if family_face else "")
            + f"(v{version_start}~v{version_end}); "
            f"triggers={','.join(result['triggers'])}"
        )
        return result

    # Record file sizes before migration
    result["plan_tracker_before"] = (
        _plan_tracker().stat().st_size if _plan_tracker().exists() else 0
    )
    result["evidence_log_before"] = (
        _evidence_log().stat().st_size if _evidence_log().exists() else 0
    )

    # Execute migration
    migrate_result = migrate_by_version(
        version_start, version_end, dry_run=False, migrate_evidence=True,
        row_family=row_family
    )

    if not migrate_result["success"]:
        result["details"] = (
            f"迁移失败: {migrate_result.get('details', 'Unknown error')}"
        )
        return result

    result["tasks_archived"] = migrate_result["tasks_archived"]
    result["evidence_archived"] = migrate_result.get("evidence_archived", 0)
    result["row_families_archived"] = migrate_result.get(
        "row_families_archived", {})
    result["archive_files_created"] = migrate_result.get(
        "archive_files_created", []
    )
    # FIX-385 衔接面: surface a decision-store authority deferral loudly.
    result["decision_migration_deferred"] = migrate_result.get(
        "decision_migration_deferred")

    # Build index
    build_index()

    # Verify integrity
    verify_result = verify_archive_integrity()
    result["verify_pass"] = verify_result["pass"]

    # Record file sizes after migration
    result["plan_tracker_after"] = (
        _plan_tracker().stat().st_size if _plan_tracker().exists() else 0
    )
    result["evidence_log_after"] = (
        _evidence_log().stat().st_size if _evidence_log().exists() else 0
    )

    result["success"] = True
    result["details"] = (
        f"归档完成: {result['tasks_archived']} 个 task, "
        f"{result['evidence_archived']} 条证据 "
        f"(v{version_start}~v{version_end})"
    )
    return result


# ── CLI Entry Point ─────────────────────────────────────────────────

def _extract_project_root_arg(argv):
    """Extract --project-root from argv no matter where the user places it.

    ``argparse`` only accepts global options before the subcommand, but the
    bootstrap entry commonly invokes commands as:

        archive.py migrate --auto --dry-run --project-root <host>

    Keep that spelling backward-compatible by stripping the option before
    subparser parsing and applying the host-root override afterward
    (mirrors verify_workflow.py FIX-187).
    """
    filtered = []
    project_root = None
    iterator = iter(range(len(argv)))
    for index in iterator:
        value = argv[index]
        if value == "--project-root":
            try:
                project_root = argv[index + 1]
            except IndexError:
                raise ValueError("--project-root requires a path")
            next(iterator, None)
        elif value.startswith("--project-root="):
            project_root = value.split("=", 1)[1]
        else:
            filtered.append(value)
    return project_root, filtered


def _validate_project_root(project_root):
    """Validate an explicit --project-root value (fail-closed, FIX-244).

    Returns ``(host_root, error)``: the resolved absolute directory Path
    plus ``None`` for a valid root; ``(None, reason)`` for an empty,
    nonexistent, or non-directory path. Mirrors
    ``resolve_entry.resolve_host_root`` (strict resolve + is_dir).
    """
    if not project_root:
        return None, "path is empty"
    candidate = Path(project_root).expanduser()
    try:
        candidate = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        return None, "path does not exist"
    if not candidate.is_dir():
        return None, "not a directory"
    return candidate, None


def _apply_project_root_override(project_root):
    """Rebind host-governance fact paths to an explicit project root.

    Mirrors verify_workflow.py (FIX-187): only host facts are rebound —
    ``ROOT`` / ``HOST_PROJECT_ROOT`` and everything derived from _gov_dir().
    Plugin assets (``PLUGIN_ROOT`` / ``_latest_released_version``) are never
    moved, so the SKILL.md version read keeps resolving to the plugin
    (FIX-242).

    Fail-closed (FIX-244): an explicit root that is empty, does not exist,
    or is not a directory is a hard error — classified diagnostic on
    stderr + exit 2 (aligns with resolve_entry.resolve_host_root, which
    refuses explicit paths that cannot be resolved). A nonexistent path
    must never silently rebind to a phantom root.
    """
    global ROOT, HOST_PROJECT_ROOT
    host_root, error = _validate_project_root(project_root)
    if error is not None:
        display = "<empty>" if not project_root else str(project_root)
        print(
            f"spg-archive-error: invalid-project-root — {display} ({error})",
            file=sys.stderr,
        )
        sys.exit(2)
    ROOT = host_root
    HOST_PROJECT_ROOT = host_root


def main(argv=None):
    """CLI for archive operations."""
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    try:
        explicit_project_root, parser_argv = _extract_project_root_arg(raw_argv)
    except ValueError as exc:
        print(f"archive: error: {exc}", file=sys.stderr)
        sys.exit(2)

    parser, migrate_parser = _build_archive_arg_parser()

    args = parser.parse_args(parser_argv)
    # --project-root was pre-scanned out of argv (position-independent);
    # apply the explicit host-root override before dispatching (FIX-242).
    if explicit_project_root is not None:
        _apply_project_root_override(explicit_project_root)

    # Ensure stdout supports UTF-8 (Windows consoles default to GBK)
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # FIX-435: the argparse face + handlers live in archive_cli; ``impl`` is
    # this module's live namespace, so every dispatched orchestrator keeps
    # resolving through THIS instance (ROOT seam + patch surface — also under
    # the isolated spec_from_file_location load, where sys.modules carries no
    # entry for this module; globals() is authoritative either way).
    impl = globals()
    if args.command == "migrate":
        _archive_cli._cli_cmd_migrate(args, migrate_parser, impl)
    elif args.command == "migrate-big-table":
        _archive_cli._cli_cmd_migrate_big_table(args, impl)
    elif args.command == "scan-families":
        _archive_cli._cli_cmd_scan_families(args, impl)
    elif args.command == "build-index":
        _archive_cli._cli_cmd_build_index(args, impl)
    elif args.command == "rebuild-index":
        _archive_cli._cli_cmd_rebuild_index(args, impl)
    elif args.command == "verify":
        _archive_cli._cli_cmd_verify(args, impl)
    elif args.command == "rollback":
        _archive_cli._cli_cmd_rollback(args, impl)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
