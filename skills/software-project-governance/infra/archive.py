#!/usr/bin/env python3
"""
Governance Data Archive Script — SYSGAP-030

Implements version-based archiving of governance data (plan-tracker tasks,
evidence-log entries, etc.) with a light-weight Markdown index.

Core functions:
  - migrate_by_version: archive tasks+evidence for a version range
  - migrate_evidence_resumable: batched/journaled RESUMABLE migration of a
      row-heavy governance table (evidence-log) into the archive
      (FIX-385 / B-7b) — journal → staged batches → single commit
      linearization point; resume re-judges the world from digests, never
      from a phase counter (FEAT-060/FEAT-061 pattern)
  - scan_row_families: READ-ONLY dry-run scan of the four governance row
      families (EVD/REVIEW/RECO/TRIAGE) under unit one's six-condition
      classification — zero writes; the REVIEW/RECO/TRIAGE families are
      REFUSED at code level on every write-migration path (FEAT-075 /
      DEC-278 单元二)
  - build_index: scan archive files, generate archive/index.md
  - rebuild_index: index-loss/corruption recovery — rebuild the index from
      the archive files, then verify integrity (FIX-384 / B-7a). The index is
      a pure DERIVATIVE: rebuild restores the view, never creates data.
  - verify_archive_integrity: check index-archive consistency
  - rollback_last_migration: undo most recent migration

Design: ADR-006 (docs/architecture/ADR-006-governance-data-scalability.md)
"""

import contextlib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import date, datetime
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

# ── FIX-385 (B-7b): big-table resumable migration constants ────────
BIG_TABLE_MIGRATION_BATCH_SIZE = 200          # rows per staged batch
_BIG_TABLE_MIGRATION_DIRNAME = ".migration"   # runtime state under archive/
_MIGRATION_JOURNAL_SCHEMA = "archive-big-table-migration/1"
# FEAT-061 decision_repository.AUTHORITY_STATE_FILE — the storage-separation
# authority marker. Name pinned here so the 衔接面 guard can fail closed even
# when the repository module itself is unavailable (minimal packaging).
_DECISION_AUTHORITY_MARKER_NAME = ".decision-store-state.json"


# FEAT-060/FEAT-061 primitive reuse (single lock/atomic-write source
# discipline — the same imports decision_migration.py relies on). Isolated
# loaders (verify_workflow._load_archive_module spec_from_file_location) and
# minimal packaging may lack the peers; local fallbacks keep the same
# durability guarantees instead of silently downgrading.
try:
    from governance_store import _TargetLock, _atomic_write_bytes
    import decision_repository as _decision_repository
except Exception:  # pragma: no cover — fallback path, exercised by layout
    _TargetLock = None
    _atomic_write_bytes = None
    _decision_repository = None


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


# ── Version Parsing Utilities ──────────────────────────────────────



























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




def _make_incremental_archive_filename(version_start, version_end, category="tasks"):
    """Generate an independent archive filename for a repeated range.

    Continuous archive must not append to an older archive file because rollback
    operates at file granularity.  A repeated range therefore gets its own
    increment file that can be safely unlinked without deleting history.

    FIX-385: the resumable big-table path reuses this discipline for the
    category-prefixed evidence family too (evidence-vX-Y.md) — a commit never
    overwrites foreign archive content.
    """
    if category == "tasks":
        base_name = _make_archive_filename(version_start, version_end, category)
    else:
        base_name = f"{category}-v{version_start}-{version_end}.md"
    archive_subdir = _archive_dir() / category
    base_path = archive_subdir / base_name
    if not base_path.exists():
        return base_name

    today = date.today().isoformat().replace("-", "")
    index = 1
    while True:
        if category == "tasks":
            candidate = f"v{version_start}~v{version_end}-incremental-{today}-{index}.md"
        else:
            candidate = (f"{category}-v{version_start}-{version_end}"
                         f"-incremental-{today}-{index}.md")
        if not (archive_subdir / candidate).exists():
            return candidate
        index += 1




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


def _write_archive_file(filepath, header, body_lines):
    """Write an archive file with standardized header."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(header)
        f.write("\n")
        f.write("\n".join(body_lines))
        f.write("\n")


def _build_archive_header(version_start, version_end, category, entry_count,
                          prev_file=None, next_file=None):
    """Build standardized archive file header.

    category: 'tasks', 'evidence', 'decisions', 'risks'
    """
    category_labels = {
        "tasks": ("归档 Task 表", "plan-tracker.md 中"),
        "evidence": ("归档 Evidence 记录", "evidence-log.md 中"),
        "decisions": ("归档 Decision 记录", "decision-log.md 中"),
        "risks": ("归档 Risk 记录", "risk-log.md 中"),
        # FEAT-076: the three unlocked row families live in the same hot
        # table; their archive legs carry family-scoped categories.
        "evidence-review": ("归档 Review 行族记录", "evidence-log.md 中"),
        "evidence-triage": ("归档 Triage 行族记录", "evidence-log.md 中"),
        "evidence-reco": ("归档 Reco 行族记录", "evidence-log.md 中"),
    }
    label, source = category_labels.get(category, (f"归档 {category} 记录", ""))

    lines = [
        f"# {label} — v{version_start} ~ v{version_end}",
        f"- **归档日期**: {date.today().isoformat()}",
        f"- **归档范围**: {source} {version_start}~{version_end} 版本的所有 {category}",
        f"- **条目数**: {entry_count}",
    ]
    if prev_file:
        lines.append(f"- **上一个归档文件**: archive/{category}/{prev_file}")
    else:
        lines.append(f"- **上一个归档文件**: 无")
    if next_file:
        lines.append(f"- **下一个归档文件**: archive/{category}/{next_file}")
    else:
        lines.append(f"- **下一个归档文件**: 无")

    lines.append("")
    lines.append("> 查询方式：通过 `.governance/archive/index.md` 按 ID 定位。")
    lines.append("")

    return "\n".join(lines) + "\n"




# ── Decision attribution (FIX-312 / R2 F-R2-01 family) ──────────────









def _decision_narrative_verdict(line, dec_id, anchor_counts, task_versions,
                                ref_verdict, version_end):
    """FIX-407 (EXC-003 终局票): Q6 date-window verdict for narrative DEC rows.

    Narrative 形态识别 is LINE-LEVEL — a ``| DEC-…`` row that already failed
    the canonical column gate (``decision_row_too_short``: hand-era compact
    rows, typically 5 cells) is recognized by its DEC-NUMBER anchor plus an
    ISO date anchor somewhere in the row; the machine-written format is NOT
    required. The Q6 ruling (DEC-278 单元三 — the same rule the evidence
    family's unlocked families use) then decides: a row migrates ONLY when
    its own date proves closed-cycle membership (row date ≤ the window-end
    version's release date). Fail-closed everywhere:

      - anchor duplicated by ANY other DEC row in the file (machine or
        narrative) → retained (``narrative_duplicate_anchor``);
      - no ISO date in the row → retained (``narrative_undatable``);
      - ANY task-family id token ANYWHERE in the row that the shared ref
        typer cannot PROVE archived (active / missing / ambiguous /
        layout-anomaly) → retained (``narrative_retained_unproven_ref``) —
        the fail-closed union discipline: whole-line prose mentions can
        only retain, never release or re-attribute a row (the FIX-312
        DEC-187 lesson);
      - window-end release date unresolvable, or row date after it →
        retained (``narrative_date_out_of_window`` — undatable-window and
        working-set rows share the fail-closed residue).

    Returns ``(migrate, reason, detail, attribution_version)`` — the
    attribution on success is ALWAYS the window end (never a ref's machine
    version: narrative columns cannot identify a governing ref, so the row's
    own date is the only sanctioned attribution).
    """
    anchor = re.match(r"DEC-(\d+)", dec_id or "")
    if anchor is None:
        return False, "narrative_no_anchor", "", None
    anchor_id = "DEC-{0}".format(anchor.group(1))
    if anchor_counts.get(anchor_id, 0) > 1:
        return False, "narrative_duplicate_anchor", anchor_id, None
    if _ROW_DATE_RE.search(line) is None:
        return False, "narrative_undatable", "", None
    refs = []
    for m in _DECISION_ID_TOKEN_RE.finditer(line):
        tid = "{0}-{1}".format(m.group(1), m.group(2))
        if _is_task_family_id(tid) and tid not in refs:
            refs.append(tid)
    unproven = [t for t in refs if ref_verdict(t)[1] != "pass"]
    if unproven:
        return (False, "narrative_retained_unproven_ref",
                "active/missing/ambiguous refs: " + ", ".join(unproven[:5]),
                None)
    fallback = _q6_date_window_fallback(line, version_end)
    if fallback is None:
        return False, "narrative_date_out_of_window", "", None
    return True, "would_archive_narrative_q6", fallback, version_end


# ── Risk status filtering (FIX-170 / AUDIT-127) ────────────────────









# ── Evidence task-family classification (FIX-171 / AUDIT-126) ───────


# FEAT-074 (DEC-278 unit one item 2): FEAT is a legal task family. FEAT tickets
# are the dominant ticket type since 0.87+; the allow-list was derived from an
# older data snapshot and its absence made every FEAT-referencing evidence row
# structurally un-migratable (90 rows / 223,895 B in no_task_family_ref at the
# 2026-09-28 inventory). task_priority.py's governance-id vocabulary already
# carries FEAT — this aligns the evidence-migration gate with it.

# FEAT-074 (DEC-278 unit one): the five entity-type states a referenced ID can
# classify into. The old classifier collapsed every gating failure into the
# single "live_or_unresolvable_task_ref" bucket; these states replace it.
#   task        — a task-family (or alias-verified) ID gated by task lifecycle
#   requirement — a REQ-N registered in the requirement registry (需求登记表);
#                 a legal requirement entity that is NEVER required to have a
#                 task version (DEC-278 Q2=c) and does not gate migration
#   other_entity— a registered non-task entity family (RISK-/DEC-/DOC-/...)
#   missing     — a task-shaped ID locatable nowhere (no version mapping, no
#                 hot-table row, no archive row)
#   ambiguous   — identity cannot be uniquely determined: dual registration
#                 (REQ in BOTH the requirement registry and the task tables)
#                 or an unverified task-shaped prefix (e.g. an FX-N id that is
#                 NOT in the per-ID verified map below)
_EVIDENCE_REF_ENTITY_TYPES = frozenset({
    "task", "requirement", "other_entity", "missing", "ambiguous",
})

# FEAT-075 (DEC-278 unit two): failure substates, most severe first — the row
# reason reports the most severe blocking cause; detail lists every blocking
# id. Module-level so the EVD classifier and the four-family scanners share
# ONE ordering (no parallel implementation; extracted verbatim from
# _classify_evidence_rows's closure body).
_REF_FAILURE_SUBSTATE_ORDER = (
    ("ambiguous", "ambiguous_ref"),
    ("missing", "missing_task_ref"),
    ("layout_anomaly", "task_layout_anomaly"),
    ("active", "active_task_ref"),
    ("version_unparseable", "task_version_unparseable"),
)


# FEAT-074 (DEC-278 unit one item 5, condition "无显式保留标记"): whole-row keep
# markers. Vocabulary is the 2026-09-28 design-admission inventory's §5 list
# (single source); a row carrying ANY marker is retained hot regardless of how
# migratable its refs look.
_EVIDENCE_KEEP_MARKERS = (
    "保留热", "keep-hot", "热保留", "禁止归档", "禁止迁移", "不迁移",
)











def _build_classification_context(plan_tracker_content=None):
    """FEAT-074 (DEC-278 unit one): the entity-registration context the
    evidence-row classifier needs beyond ``task_versions``.

    Built single-source here so the one-shot path (_migrate_evidence) and the
    resumable big-table path (migrate_evidence_resumable) can never drift
    (same discipline as FIX-385's _classify_evidence_rows extraction):

      hot_tasks        — {task_id: {"status", "version"}} for EVERY well-formed
                         priority-table row (no status/version filtering): the
                         "locatable in the hot table" face used to distinguish
                         an ACTIVE task ref (lifecycle open — retained hot)
                         from a MISSING one (locatable nowhere).
      hot_anomalies    — {task_id: unescaped_pipe_count} for layout-anomalous
                         priority rows: the id is locatable but its columns
                         are untrusted, so lifecycle can NEVER be proven from
                         them (fail-closed, explainable reason).
      requirement_ids  — the requirement-registry REQ ids (see
                         _requirement_registry_ids).

    ``plan_tracker_content`` None → read the live plan-tracker (missing /
    unreadable file degrades to an EMPTY context — classification then simply
    loses the locatable-in-hot-table distinction, never the version-mapping
    gate; fail-soft is safe because every state it feeds is retain-hot).
    """
    if plan_tracker_content is None:
        try:
            plan_tracker_content = _plan_tracker().read_text(encoding="utf-8")
        except OSError:
            plan_tracker_content = ""
    anomalies = []
    hot_tasks = {}
    for _idx, _line, task_id, target_version, status in \
            _parse_priority_table_tasks(plan_tracker_content,
                                        anomalies_out=anomalies):
        hot_tasks.setdefault(task_id,
                             {"status": status, "version": target_version})
    return {
        "hot_tasks": hot_tasks,
        "hot_anomalies": {task_id: pipes for task_id, _i, pipes in anomalies},
        "requirement_ids": frozenset(
            _requirement_registry_ids(plan_tracker_content)),
    }










def _next_family_archive_filename(version_start, version_end, row_family):
    """FEAT-076: the commit's archive target for one family under
    archive/evidence/ — ``evidence-v{range}.md`` for EVD (FIX-385 naming
    discipline preserved via _next_evidence_archive_filename) and
    ``evidence-{family}-v{range}.md`` for the unlocked families, with the
    same never-overwrite-foreign-content incremental suffix discipline."""
    if row_family == "EVD":
        return _next_evidence_archive_filename(version_start, version_end)
    category = f"evidence-{row_family.lower()}"
    subdir = _archive_dir() / "evidence"
    base_name = f"{category}-v{version_start}-{version_end}.md"
    if not (subdir / base_name).exists():
        return base_name
    today = date.today().isoformat().replace("-", "")
    index = 1
    while True:
        candidate = (f"{category}-v{version_start}-{version_end}"
                     f"-incremental-{today}-{index}.md")
        if not (subdir / candidate).exists():
            return candidate
        index += 1


def _classify_rows_for_family(row_family, content, task_versions,
                              version_start, version_end, *, context=None):
    """FEAT-076: single-source row classification dispatch for ALL four
    families' write-migration paths. EVD → _classify_evidence_rows (unit
    one); the three unlocked families → _classify_family_rows on the shared
    _make_ref_verdict typer (the same classification the read-only scanner
    uses — zero drift between scan candidacy and migration candidacy)."""
    if context is None:
        context = _build_classification_context()
    if row_family == "EVD":
        return _classify_evidence_rows(
            content, task_versions, version_start, version_end,
            context=context)
    lines = content.split("\n")
    line_bytes = [len(line.encode("utf-8")) + (0 if i == len(lines) - 1 else 1)
                  for i, line in enumerate(lines)]
    return _classify_family_rows(
        row_family, lines, line_bytes, task_versions,
        version_start, version_end,
        _make_ref_verdict(task_versions, context))


# ── Decision / Risk Migration (FIX-162 / TD-014) ───────────────────


def _migrate_decisions(version_start, version_end, task_versions, dry_run=False,
                       explain_out=None):
    """FIX-162: migrate decision-log rows whose related tasks have been archived.

    Decision-log format: '| DEC-{n} | date | title | context | decision | ... |'
    The 'related' column (关联任务) references governing task IDs. FIX-312: a
    row migrates only when EVERY task-family ref in its related column is
    archived AND the newest archived governing version is in
    [version_start, version_end] — see _decision_archive_version.
    Writes archived rows to archive/decisions/decisions-v{range}.md in the format
    '## DEC-{n}: {title}' that build_index expects. Returns count migrated.

    FIX-385 衔接面 (B-7b): when the decision table's authority has moved to
    the FEAT-061 JSON store (authority state != MD_ACTIVE), decision-log.md
    is a PROJECTION — rewriting it here would corrupt the storage
    architecture. This raises DecisionStoreAuthorityConflict (loud, fail-
    closed); the calling surfaces record the deferral and keep migrating
    the other categories. The store-backed DEC archive read route belongs
    to the cutover ticket.

    FIX-170 note: unlike _migrate_risks, decisions have NO status column — the
    decision-log is an append-only historical record (columns: 编号/日期/主题/
    背景/决策内容/备选/选择原因/影响范围/决策人/关联任务/后续动作). There is no
    accepted/active vs superseded/withdrawn signal to gate on, and a row's text
    routinely contains words like '失效'/'停滞' describing decisions about OTHER
    items, so whole-row marker scanning would be unsafe. The version-range
    membership test (related task already archived) is therefore the only sound
    migration gate for decisions. This is consistent with the AUDIT-127 root
    cause, which was exclusively a risk-log regression (OPEN risks migrated).

    FIX-301: when ``explain_out`` is a list, every scanned decision row appends
    exactly one {"id", "reason", "detail"} record (single source of truth —
    the explanation can never drift from the actual migration behavior).

    FIX-312 attribution semantics: governing refs are read ONLY from the
    关联任务 (related tasks) column (:func:`_decision_related_column_index`,
    with a canonical second-to-last-cell fallback for headerless files), and
    a row migrates ONLY when EVERY task-family governing ref is archived —
    the attributed version being the NEWEST archived governing version
    (:func:`_decision_archive_version`). Reasons: would_archive /
    retained_active_task_ref / no_task_family_ref / decision_row_too_short /
    ref_version_out_of_range.
    """

    # FIX-385 衔接面: judge the decision-store authority BEFORE touching the
    # projection file. Corrupt/unreadable markers refuse too ("unreadable").
    authority_state = _decision_authority_state()
    if authority_state != "MD_ACTIVE":
        raise DecisionStoreAuthorityConflict({
            "code": "decision_store_authority_conflict",
            "authority_state": authority_state,
            "detail": (
                "decision migration refused: decision-store authority state "
                f"is {authority_state!r}, not MD_ACTIVE — decision-log.md is "
                "a projection under the FEAT-061 store architecture and is "
                "never rewritten as authority; the store-backed archive read "
                "route is the cutover ticket's obligation"),
        })

    dlog = _decision_log()
    if not dlog.exists():
        return 0
    content = dlog.read_text(encoding="utf-8")
    lines = content.split("\n")
    related_idx = _decision_related_column_index(lines)
    # FIX-407 (EXC-003 终局票): pre-pass anchor census + shared ref typer for
    # the narrative row-family fallback (see _decision_narrative_verdict).
    anchor_counts = {}
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("| DEC-"):
            continue
        row_parts = [p.strip() for p in line.split("|")]
        anchor_m = re.match(r"DEC-(\d+)", row_parts[1] if len(row_parts) > 1 else "")
        if anchor_m:
            anchor_id = "DEC-" + anchor_m.group(1)
            anchor_counts[anchor_id] = anchor_counts.get(anchor_id, 0) + 1
    try:
        narrative_context = _build_classification_context()
    except (OSError, ValueError):
        narrative_context = {"hot_tasks": {}, "hot_anomalies": {},
                             "requirement_ids": set()}
    narrative_ref_verdict = _make_ref_verdict(task_versions, narrative_context)

    def _note(dec_id, reason, detail=""):
        if explain_out is not None:
            explain_out.append(
                {"id": dec_id, "reason": reason, "detail": detail[:60]}
            )

    kept_lines = []
    archived = []  # (dec_id, title, version, original_line, q6_detail|None)
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("| DEC-"):
            kept_lines.append(line)
            continue
        parts = [p.strip() for p in line.split("|")]
        dec_id = parts[1] if len(parts) > 1 else ""
        title = parts[3] if len(parts) > 3 else ""
        if not (dec_id and re.match(r"DEC-\d+", dec_id)):
            kept_lines.append(line)
            continue
        ver, reason, detail = _decision_archive_version(
            line, related_idx, task_versions)
        if ver and _version_in_range(ver, version_start, version_end):
            archived.append((dec_id, title, ver, line, None))
            _note(dec_id, "would_archive", f"v{ver}")
        else:
            if reason == "decision_row_too_short" and len(parts) == 7:
                # FIX-407: narrative row-family fallback — line-level DEC
                # anchor + ISO date recognition (machine format NOT
                # required), Q6 date-window ruling, fail-closed retention.
                # FIX-411 structure gate (B-group contract ruling: the
                # STRUCTURE judgment precedes the narrative judgment): only
                # the REGULAR narrative shape — exactly 5 data cells
                # (编号/日期/决策人/决策内容/理由, len(parts)==7 incl. the
                # split empties) — enters the narrative verdict; ragged
                # headerless forms (4/6/10/12 cells) keep the FIX-342
                # fail-closed decision_row_too_short reason.
                migrate, n_reason, n_detail, n_ver = _decision_narrative_verdict(
                    line, dec_id, anchor_counts, task_versions,
                    narrative_ref_verdict, version_end)
                if migrate and _version_in_range(n_ver, version_start,
                                                 version_end):
                    archived.append((dec_id, _decision_narrative_title(parts),
                                     n_ver, line, n_detail))
                    _note(dec_id, "would_archive_narrative_q6", n_detail)
                    continue
                reason, detail = n_reason, n_detail
            kept_lines.append(line)
            if ver is None:
                _note(dec_id, reason, detail)
            else:
                _note(dec_id, "ref_version_out_of_range", f"v{ver}")

    if not archived:
        return 0
    if dry_run:
        return len(archived)

    _ensure_archive_dirs()
    archive_body = []
    for dec_id, title, ver, line, q6_detail in archived:
        # build_index expects '## DEC-{n}: {title}' header for indexing.
        archive_body.append(f"## {dec_id}: {title}")
        archive_body.append("")
        if q6_detail:
            # FIX-407: narrative row — Q6 date-window attribution (the row's
            # own date ≤ window-end release date; refs never re-attribute).
            archive_body.append(f"- 归档版本: v{ver}（narrative 行 Q6 日期窗：{q6_detail}）")
        else:
            archive_body.append(f"- 归档版本: v{ver}（关联 task 已归档）")
        archive_body.append("")
        # FIX-162 review P2-1: preserve the full original decision row (9+ cols:
        # 背景/决策内容/备选/原因/影响/决策人/关联任务/后续动作) for fidelity,
        # consistent with how risks preserve their original rows.
        archive_body.append("> 原始决策记录（完整字段）：")
        archive_body.append(f"> {line.strip()}")
        archive_body.append("")
    # Write per-range archive file
    archive_path = _archive_dir() / "decisions" / f"decisions-v{version_start}-{version_end}.md"
    header = _build_archive_header(version_start, version_end, "decisions", len(archived),
                                   prev_file=None, next_file=None)
    # REVIEW-FIX-385-R0 F-1 (衔接面 TOCTOU): the authority was judged at this
    # function's entry, but a concurrent cutover can flip the store authority
    # before the projection rewrite lands. The writes therefore execute inside
    # the decision-log target lock — the SAME `_TargetLock(md_target)` domain
    # the cutover's projection leg (decision_repository
    # .project_store_to_markdown) holds — with an IN-LOCK authority
    # re-judgment first (mirrors REVIEW-FEAT-061-R0 P0-F1's in-lock re-check
    # form): a flipped world refuses via the deferral path with ZERO writes;
    # the projection is never rewritten with authority posture.
    with _big_table_target_lock(dlog):
        authority_state = _decision_authority_state()
        if authority_state != "MD_ACTIVE":
            raise DecisionStoreAuthorityConflict({
                "code": "decision_store_authority_conflict",
                "authority_state": authority_state,
                "recheck": "in_lock",
                "detail": (
                    "decision migration refused at the projection-rewrite "
                    "critical section: decision-store authority state is "
                    f"{authority_state!r}, not MD_ACTIVE — a concurrent "
                    "cutover flipped the authority inside the migration "
                    "window; zero writes performed"),
            })
        _write_archive_file(archive_path, header, archive_body)
        # Rewrite decision-log without migrated rows
        dlog.write_text("\n".join(kept_lines), encoding="utf-8")
    return len(archived)


def _migrate_risks(version_start, version_end, task_versions, dry_run=False,
                   explain_out=None):
    """FIX-162: migrate risk-log rows whose related tasks have been archived.

    Risk-log format: '| RISK-{n} | date | desc | impact | ... |'
    Same related-task logic as decisions. Writes archived rows to
    archive/risks/risks-v{range}.md preserving the table-row format that
    build_index expects ('| RISK-{n} | desc | ... |'). Returns count migrated.

    FIX-170 (AUDIT-127): in-range risk rows are migrated ONLY if their status
    cell indicates closure (已关闭/closed). OPEN/active risks (打开/缓解中/...)
    are NEVER migrated out of the hot risk-log, even when a related task has
    been archived — the hot risk-log is the single source of truth for active
    risks. See _is_risk_closed() for the column-aware status detection.

    FIX-301: when ``explain_out`` is a list, every scanned risk row appends
    exactly one {"id", "reason", "detail"} record. Reasons: would_archive /
    no_archived_task_ref / ref_version_out_of_range / risk_not_closed.
    """
    rlog = _risk_log()
    if not rlog.exists():
        return 0
    content = rlog.read_text(encoding="utf-8")
    lines = content.split("\n")

    def _note(risk_id, reason, detail=""):
        if explain_out is not None:
            explain_out.append(
                {"id": risk_id, "reason": reason, "detail": detail[:60]}
            )

    # FIX-170: capture the table header line so _is_risk_closed can locate the
    # '当前状态' column dynamically (the real risk-log does NOT put 状态 last,
    # and the column position varies across fixtures).
    risk_header = _find_risk_log_header(lines)

    kept_lines = []
    archived = []  # (original_line, version)
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("| RISK-"):
            kept_lines.append(line)
            continue
        parts = [p.strip() for p in line.split("|")]
        risk_id = parts[1] if len(parts) > 1 else ""
        if not (risk_id and re.match(r"RISK-\d+", risk_id)):
            kept_lines.append(line)
            continue
        ver = _entry_version_for_archive(line, task_versions)
        if ver and _version_in_range(ver, version_start, version_end):
            # FIX-170: status gate — only migrate CLOSED risks. OPEN risks
            # stay in the hot file regardless of version-range membership.
            if not _is_risk_closed(line, risk_header):
                kept_lines.append(line)
                _note(risk_id, "risk_not_closed", "status cell not closed")
                continue
            archived.append((line, ver))
            _note(risk_id, "would_archive", f"v{ver}")
        else:
            kept_lines.append(line)
            if ver is None:
                _note(risk_id, "no_archived_task_ref",
                      "no referenced task is archived")
            else:
                _note(risk_id, "ref_version_out_of_range", f"v{ver}")

    if not archived:
        return 0
    if dry_run:
        return len(archived)

    _ensure_archive_dirs()
    archive_body = [line for line, _ver in archived]
    archive_path = _archive_dir() / "risks" / f"risks-v{version_start}-{version_end}.md"
    header = _build_archive_header(version_start, version_end, "risks", len(archived),
                                   prev_file=None, next_file=None)
    _write_archive_file(archive_path, header, archive_body)
    rlog.write_text("\n".join(kept_lines), encoding="utf-8")
    return len(archived)


_ROW_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


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


def _q6_date_window_fallback(line, version_end):
    """FEAT-076 (DEC-278 单元三 Q6 ruling, 0.93-effective): the date-window
    fallback for rows with NO gating task-family refs.

    Returns the migration detail string when the row's own date proves
    closed-cycle membership (row date on/before the window-end version's
    release date), else None (retain hot — undatable rows and rows newer
    than the window end are the working set / fail-closed residue).

    The row date is the FIRST ISO yyyy-mm-dd token in the row — schema-
    drift-tolerant (the date column moved across eras) and unambiguous
    (ids/refs carry no dates)."""
    end_date = _window_end_release_date(version_end)
    if end_date is None:
        return None
    m = _ROW_DATE_RE.search(line)
    if not m:
        return None
    try:
        row_date = datetime.strptime(m.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None
    if row_date > end_date:
        return None
    return (f"row date {row_date.isoformat()} ≤ window-end "
            f"v{version_end} release {end_date.isoformat()} (Q6 fallback)")




def _classify_evidence_rows(content, task_versions, version_start, version_end,
                            *, context=None):
    """FIX-385/FEAT-074: single source of the evidence migration row-
    classification gate — extracted from _migrate_evidence so the one-shot
    path and the resumable big-table path can never drift apart (same
    discipline as the FIX-384 _extract_* single-sourcing).

    The gates are _migrate_evidence's (FIX-164 subset + FIX-171 task-family/
    cross-entity split + FIX-301 compound-ID shape + range membership)
    re-expressed by FEAT-074 (DEC-278 unit one) as the six-condition task
    determination — ALL six must hold for a row to migrate, and every failure
    carries an explainable reason:

      1. 可定位          — every gating ref resolves to a task identity (the
                           task_versions mapping, a verified per-ID alias, or
                           a locatable hot-table row). Nowhere-locatable refs
                           classify "missing" → missing_task_ref.
      2. 生命周期已关闭  — task_versions membership IS the closure proof
                           (physically archived, or a hot row whose STATUS is
                           terminal per _task_status_is_archivable — a
                           released version alone never proves closure).
                           Hot rows with an open status classify "active" →
                           active_task_ref (covers 当前工作集/重开/在途).
      3. 周期封闭+保留窗 — the row's owning cycle is the MAX resolved ref
                           version (保守：最晚引用封闭才算封闭 — inventory §2.1
                           β criterion; matches the FIX-312 decision-domain
                           newest-governing-version precedent) and must fall
                           inside [version_start, version_end]. Terminal hot
                           rows with a non-semver target (未规划版本/G9/G11)
                           cannot prove cycle closure →
                           task_version_unparseable (fail-closed).
      4. 非当前工作集    — active refs (open status) and in-flight versions
                           (outside the window) both retain the row hot.
      5. 无显式保留标记  — the whole row is scanned for the
                           _EVIDENCE_KEEP_MARKERS vocabulary →
                           explicit_keep_marker.
      6. 迁移后可定位    — the EVD id must match _EVD_ID_SHAPE_RE (the shared
                           shape the archive index admits) → else
                           unknown_evd_id_shape; migrated rows are preserved
                           verbatim, so an admitted id stays locatable.
                           Duplicate shape-valid ids inside one input are an
                           ambiguous identity → duplicate_evd_id (fail-closed;
                           never absorbed by a lenient regex, DEC-278 §3.2).

    Referenced ids are typed into the five DEC-278 entity states (see
    _EVIDENCE_REF_ENTITY_TYPES): task / requirement / other_entity / missing
    / ambiguous — replacing the old single live_or_unresolvable_task_ref
    bucket. Requirement-registry REQs (Q2=c) and registered cross-entity
    families are descriptive context and do NOT gate; dual-registered REQs
    and unverified task-shaped prefixes (FX-N outside
    _VERIFIED_TASK_ID_ALIASES) classify "ambiguous" and gate the row shut.

    Args:
        content: the evidence-log.md text.
        task_versions: ``{task_id: version}`` mapping (this-run + archived
            + FIX-235 completed-hot, per the caller's semantics).
        version_start / version_end: the migration range.
        context: optional prebuilt classification context (see
            _build_classification_context). None → built here from the live
            plan-tracker (single-source helper; missing file degrades to an
            empty context).

    Returns one record per scanned EVD row, in scan order:
        {"id", "line_idx", "line", "migrate": bool, "version": str|None,
         "reason": str, "detail": str, "ref_types": {ref_id: entity_state}}
    Non-EVD lines are not candidates and produce no record. ``reason`` /
    ``detail`` carry the same values the FIX-301 explain mechanism reports;
    reasons: would_archive / no_task_family_ref / ref_version_out_of_range /
    unknown_evd_id_shape / duplicate_evd_id / explicit_keep_marker /
    missing_task_ref / active_task_ref / ambiguous_ref /
    task_layout_anomaly / task_version_unparseable.
    """
    if context is None:
        context = _build_classification_context()

    # FEAT-075 (DEC-278 unit two): the ref typer + task gate is single-sourced
    # in _make_ref_verdict (extracted verbatim from this function's closure)
    # so the four-family scanners share unit one's semantics.
    _ref_verdict = _make_ref_verdict(task_versions, context)

    # FEAT-074 (condition 6): duplicate shape-valid EVD ids inside one input
    # are an ambiguous row identity — every copy fails closed (never split
    # across hot/cold by a lucky first-come-first-migrate).
    id_line_counts = {}
    for line_idx, line in enumerate(content.split("\n")):
        stripped = line.strip()
        if not stripped.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        evd_id = parts[1] if len(parts) > 1 else ""
        if evd_id and _EVD_ID_SHAPE_RE.match(evd_id):
            id_line_counts.setdefault(evd_id, []).append(line_idx)

    records = []
    for line_idx, line in enumerate(content.split("\n")):
        stripped = line.strip()
        if not stripped.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        evd_id = parts[1] if len(parts) > 1 else ""
        if not (evd_id and _EVD_ID_SHAPE_RE.match(evd_id)):
            # FIX-301: compound IDs (EVD-FIX-247) are admitted; anything else
            # (corrupted/malformed rows) is reported as unknown structure.
            records.append({"id": evd_id or "?", "line_idx": line_idx,
                            "line": line, "migrate": False, "version": None,
                            "reason": "unknown_evd_id_shape",
                            "detail": "row ID shape not recognized",
                            "ref_types": {}})
            continue
        # parts[2] = 关联 Task column; may be comma-separated multiple IDs that
        # mix task-family (FIX-/REL-/FEAT-/...), requirement-registry REQs,
        # cross-entity (RISK-/DEC-/DOC-/...) and alias-verified (FX-...) refs.
        raw_task_ids = parts[2] if len(parts) > 2 else ""
        ev_task_ids = set()
        for tid in raw_task_ids.split(","):
            tid = tid.strip()
            if tid and re.match(r"[A-Z]+-\d+", tid):
                ev_task_ids.add(tid)

        ref_types = {}
        verdicts = {}
        for tid in sorted(ev_task_ids):
            entity_state, verdict, payload = _ref_verdict(tid)
            ref_types[tid] = entity_state
            verdicts[tid] = (verdict, payload)

        def _record(reason, detail, migrate=False, version=None):
            records.append({"id": evd_id, "line_idx": line_idx, "line": line,
                            "migrate": migrate, "version": version,
                            "reason": reason, "detail": detail,
                            "ref_types": ref_types})

        # FEAT-074 condition 6 (row identity): duplicate shape-valid id.
        if len(id_line_counts.get(evd_id, ())) > 1:
            _record("duplicate_evd_id",
                    f"id appears {len(id_line_counts[evd_id])} times in input")
            continue
        # FEAT-074 condition 5 (explicit keep marker) — whole-row scan.
        if any(marker in line for marker in _EVIDENCE_KEEP_MARKERS):
            _record("explicit_keep_marker",
                    "row carries an explicit keep marker (retained hot)")
            continue

        gating_fails = {tid: payload for tid, (verdict, payload)
                        in verdicts.items() if verdict == "fail"}
        if not ev_task_ids or all(v == "nongate"
                                  for v, _p in verdicts.values()):
            # No gating task ref at all (FIX-171 semantic preserved:
            # descriptive context cannot resolve a version). FEAT-076 (0.93):
            # the DEC-278 单元三 Q6 ruling takes effect — 实体状态优先，
            # 日期窗兜底: a refless row whose OWN DATE falls on/before the
            # window-end version's release date belongs to a closed cycle
            # and migrates; anything undatable or newer stays hot
            # (fail-closed — no date, no migration).
            fallback = _q6_date_window_fallback(line, version_end)
            if fallback is not None:
                _record("would_archive_date_window", fallback,
                        migrate=True, version=None)
            else:
                _record("no_task_family_ref",
                        f"refs: {raw_task_ids[:40] or '(none)'}")
            continue
        if gating_fails:
            for substate, reason in _REF_FAILURE_SUBSTATE_ORDER:
                ids = sorted(t for t, p in gating_fails.items()
                             if p == substate or (
                                 substate == "ambiguous"
                                 and str(p).startswith("ambiguous")))
                if ids:
                    _record(reason, "blocking refs: " + ",".join(ids[:5]))
                    break
            continue
        # FEAT-074 condition 3: owning cycle = MAX resolved ref version
        # (最晚引用封闭才算封闭), must fall inside the retention window.
        resolved_versions = [payload for _t, (verdict, payload)
                             in verdicts.items() if verdict == "pass"]
        owning = max(resolved_versions, key=_version_to_tuple)
        if _version_in_range(owning, version_start, version_end):
            _record("would_archive", f"v{owning} (max ref version)",
                    migrate=True, version=owning)
        else:
            _record("ref_version_out_of_range",
                    f"owning cycle v{owning} outside "
                    f"[{version_start}, {version_end}]")
    return records


def _migrate_evidence(version_start, version_end, task_versions, dry_run=False,
                      explain_out=None, row_family="EVD"):
    """FIX-164: migrate evidence-log rows whose related tasks have been archived.

    FEAT-075 (DEC-278 §3.1 单元二) → FEAT-076 (0.93.0): ``row_family``
    selects the write-migration leg. All FOUR families (EVD/REVIEW/TRIAGE/
    RECO) are admitted — the 0.92 EVD-only boundary was superseded by the
    clearing-round authorization chain (DEC-287 → DEC-292 Wave2 unlock →
    DEC-293 全量执行) with the DEC-282 C-1(b) re-authorization conditions
    delivered in the same version. _guard_row_family_write_migration
    remains the choke point against typos and unadmitted future families;
    ``"ALL"`` resolves to the four families at the migration entries
    (migrate_by_version / migrate_auto). scan_row_families stays the
    read-only surface for zero-write inspection.

    Evidence-log format: '| EVD-{n} | 关联Task | 摘要 | 日期 | 类型 | ... |'
    parts[2] is the 关联 Task column and may contain comma-separated task IDs.
    A row migrates only if ALL its referenced TASK-FAMILY IDs are in
    task_versions (this-run archived + historical archived tasks merged from
    archive/tasks/) AND the resolved version is in [version_start, version_end].
    This mirrors the FIX-162 decision/risk logic and closes the gap where the
    old inline evidence block was gated by the this-run `archived_tasks` set —
    which is empty when all in-range tasks are already pre-archived — and so
    never ran, letting evidence-log.md bloat past the Check 28s ERROR threshold.

    FIX-171 (AUDIT-126 root cause B): the 关联 Task cell routinely mixes
    task-family IDs (FIX-/REL-/AUDIT-/...) with CROSS-ENTITY reference IDs
    (RISK-/DEC-/REVIEW-/REQ-as-requirement/...). The previous gate required
    ALL referenced IDs (including cross-entity) to be in task_versions, which
    is structurally impossible — cross-entity refs are never tasks and never
    appear in task_versions — so any EVD row listing a RISK/DEC reference was
    blocked from migration forever (129 in-range rows per AUDIT-126). The gate
    now considers only task-family IDs via _is_task_family_id(); cross-entity
    refs are descriptive context and do not gate migration.

    Mixed-ref semantics preserved (test_migrate_evidence_preserves_mixed_refs):
    an EVD referencing one archived + one LIVE task-family ID still does NOT
    migrate (the live task-family ID fails the subset). The fix only stops
    CROSS-ENTITY refs from breaking the subset check.

    FIX-301: evidence row IDs come in two real shapes — plain sequential
    (EVD-969) and compound task-keyed (EVD-FIX-247). The old plain
    ``EVD-\\d+`` check rejected every compound row as unknown (52 real rows
    invisible); the shared _EVD_ID_SHAPE_RE now admits both.

    Writes archived rows to archive/evidence/evidence-v{range}.md preserving
    the original table rows verbatim (same fidelity as risks). Returns count
    migrated.

    FIX-301: when ``explain_out`` is a list, every scanned EVD row appends
    exactly one {"id", "reason", "detail"} record. Reasons (FEAT-074 entity-
    aware set): would_archive / no_task_family_ref /
    ref_version_out_of_range / unknown_evd_id_shape / duplicate_evd_id /
    explicit_keep_marker / missing_task_ref / active_task_ref /
    ambiguous_ref / task_layout_anomaly / task_version_unparseable — the old
    single live_or_unresolvable_task_ref bucket is replaced by the typed
    five-state classification (DEC-278 unit one).
    """
    elog = _evidence_log()
    _guard_row_family_write_migration(row_family)
    if not elog.exists():
        return 0
    content = elog.read_text(encoding="utf-8")

    def _note(evd_id, reason, detail=""):
        if explain_out is not None:
            explain_out.append(
                {"id": evd_id, "reason": reason, "detail": detail[:60]}
            )

    # FIX-385: row classification is single-sourced in _classify_evidence_rows
    # (shared with the resumable big-table path) — this function keeps only
    # the apply semantics (kept/archived split + archive write).
    # FEAT-076: the dispatch covers all four families (EVD → unit one's
    # classifier; the three unlocked families → the same _make_ref_verdict
    # semantics the scanner uses — zero drift).
    records = _classify_rows_for_family(
        row_family, content, task_versions, version_start, version_end)
    for r in records:
        _note(r["id"], r["reason"], r["detail"])
    archived = [(r["line"], r["version"]) for r in records if r["migrate"]]

    if not archived:
        return 0
    if dry_run:
        return len(archived)

    migrate_line_idx = {r["line_idx"] for r in records if r["migrate"]}
    kept_lines = [ln for i, ln in enumerate(content.split("\n"))
                  if i not in migrate_line_idx]

    _ensure_archive_dirs()
    archive_body = list(_row_family_archive_table_header(row_family))
    archive_body.extend(line for line, _ver in archived)
    if row_family == "EVD":
        archive_path = _archive_dir() / "evidence" / \
            f"evidence-v{version_start}-{version_end}.md"
    else:
        # FEAT-076: family legs get their own never-overwrite filename.
        archive_path = _archive_dir() / "evidence" / \
            _next_family_archive_filename(version_start, version_end,
                                          row_family)
    header = _build_archive_header(version_start, version_end,
                                   _row_family_journal_category(row_family),
                                   len(archived),
                                   prev_file=None, next_file=None)
    _write_archive_file(archive_path, header, archive_body)
    elog.write_text("\n".join(kept_lines), encoding="utf-8")
    return len(archived)


# ── Big-table resumable migration (FIX-385 / B-7b) ─────────────────
#
# evidence-log (1.6MB+ in the dogfood host) and other row-heavy governance
# tables migrate into the archive through a batched, journaled path: the
# FEAT-060/FEAT-061 pattern (journal → apply → finalize; resume by judging
# the WORLD, never by trusting a phase counter) applied to a table-range
# migration.
#
# Reuse map (复用, not re-invented):
#   - _atomic_write_bytes / _TargetLock — governance_store's durability +
#     mutual-exclusion primitives (single lock/atomic-write source
#     discipline, the same imports decision_migration.py relies on).
#   - Journal phase machine + world judgment — the FEAT-061 activation
#     pattern: the plan pins the input digest; the commit is the single
#     linearization point; every resume RE-DERIVES the world from digests
#     (current == pinned input → continue; current == committed
#     post-image → complete the interrupted leg; anything else → loud
#     refusal, never a guess).
#   - _make_incremental_archive_filename — the existing incremental-*
#     naming discipline guarantees the commit never overwrites foreign
#     archive content.
#
# FEAT-061 衔接面 (storage-separation compatibility): the engine is
# table-agnostic in construction — a table participates through its
# (hot file, row classification via _classify_evidence_rows, archive
# composition) adapter, so the cutover ticket can add a store-routed
# decision adapter without touching the phase machinery. Until that route
# exists, a non-MD_ACTIVE decision-store authority makes DECISION-table
# migration refuse loudly (DecisionStoreAuthorityConflict) instead of
# rewriting the md projection; the evidence path is unaffected.

class BigTableMigrationError(Exception):
    """FIX-385: loud, structured refusal of a resumable big-table migration.

    ``payload`` carries {code, detail, ...} (FEAT-061 fail-closed style);
    the CLI prints it and exits non-zero — refusals are never silent zeros.
    """

    def __init__(self, payload):
        super().__init__(payload.get("detail", str(payload)))
        self.payload = dict(payload)


class DecisionStoreAuthorityConflict(BigTableMigrationError):
    """FIX-385 衔接面: the decision table's authority is NOT the hot md file
    (FEAT-061 decision-store state != MD_ACTIVE) — decision-log.md is a
    projection and must never be rewritten as if it were authority. The
    store-backed DEC archive read route belongs to the cutover ticket."""


def _sha256_text(text):
    """SHA-256 over UTF-8 text bytes — the resumable path pins digests over
    the exact bytes it writes, so line endings are platform-independent."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _atomic_write_text(path, text):
    """Durable same-directory atomic write of UTF-8 text (LF bytes).

    Delegates to governance_store._atomic_write_bytes (FEAT-060 durability
    primitive: temp + fsync + os.replace + dir fsync); the minimal-packaging
    fallback keeps the same guarantees with a local mkstemp+replace.
    """
    data = text.encode("utf-8")
    if _atomic_write_bytes is not None:
        _atomic_write_bytes(Path(path), data)
        return
    path = Path(path)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent),
                                    prefix=path.name + ".", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


@contextlib.contextmanager
def _big_table_target_lock(path):
    """Mutual exclusion over the hot table during the commit linearization
    window (governance_store._TargetLock when available)."""
    if _TargetLock is not None:
        with _TargetLock(Path(path)):
            yield
    else:
        yield


def _decision_authority_state():
    """FIX-385 衔接面 seam — world judgment of the FEAT-061 decision-store
    authority (decision_repository.load_authority on the marker file).

    Returns the marker's state string ("MD_ACTIVE" when the marker is
    absent — the initial md world). A corrupt/unreadable marker returns
    "unreadable" (fail-closed: callers refuse, never assume md). When the
    repository module is unavailable, the marker's mere EXISTENCE fails
    closed — an unvalidatable authority is never silently treated as md.
    """
    if _decision_repository is not None:
        try:
            state = _decision_repository.load_authority(_gov_dir()).get("state")
            return state if state else "unreadable"
        except Exception:
            return "unreadable"
    marker = _gov_dir() / _DECISION_AUTHORITY_MARKER_NAME
    return "MD_ACTIVE" if not marker.exists() else "unreadable"


def _migration_state_dir(category, version_start, version_end):
    """Runtime migration state dir (same artifact class as
    .decision-migration/): under archive/, carries only .json files so
    build_index / verify_archive_integrity / _get_existing_archive_files
    never see it."""
    return _archive_dir() / _BIG_TABLE_MIGRATION_DIRNAME / (
        f"{category}-v{version_start}~v{version_end}")


def _migration_journal_path(category, version_start, version_end):
    return _migration_state_dir(category, version_start, version_end) / \
        "journal.json"


def _migration_batch_path(batches_dir, batch_index):
    return batches_dir / f"batch-{batch_index:06d}.json"


def _migration_write_journal(journal_path, doc):
    doc = dict(doc)
    doc["updated_at"] = datetime.now().replace(microsecond=0).isoformat()
    _atomic_write_text(journal_path,
                       json.dumps(doc, ensure_ascii=False, indent=2) + "\n")


def _migration_load_journal(journal_path):
    """Load the journal; None when absent. Corrupt/schema-foreign → loud
    failure (FEAT-061 discipline: a required gate input that cannot be read
    is a refusal, never a pass)."""
    journal_path = Path(journal_path)
    if not journal_path.is_file():
        return None
    try:
        doc = json.loads(journal_path.read_bytes().decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        raise BigTableMigrationError({
            "code": "migration_journal_unreadable",
            "detail": f"{journal_path} is unreadable ({exc}) — the migration "
                      "journal is required to resume; refusing to guess",
        })
    if (not isinstance(doc, dict)
            or doc.get("schema") != _MIGRATION_JOURNAL_SCHEMA):
        raise BigTableMigrationError({
            "code": "migration_journal_unreadable",
            "detail": f"{journal_path} is not a {_MIGRATION_JOURNAL_SCHEMA} "
                      "journal — refusing",
        })
    return doc


def _migration_write_batch(batches_dir, batch_index, rows):
    """Stage one batch of candidate rows (atomic; content is deterministic
    from the pinned candidate manifest, so re-staging is idempotent)."""
    path = _migration_batch_path(batches_dir, batch_index)
    doc = {"batch": batch_index, "rows": list(rows)}
    _atomic_write_text(path,
                       json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    return path


def _migration_load_batch(batches_dir, batch_index):
    """Read one staged batch's rows; corrupt → loud failure (the staged
    artifact is load-bearing for the post-commit resume path)."""
    path = _migration_batch_path(batches_dir, batch_index)
    try:
        doc = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        raise BigTableMigrationError({
            "code": "migration_batch_unreadable",
            "detail": f"{path} is unreadable ({exc}) — staged batch "
                      "artifacts are required to re-materialize the commit; "
                      "refusing to guess",
        })
    rows = doc.get("rows") if isinstance(doc, dict) else None
    if not isinstance(rows, list):
        raise BigTableMigrationError({
            "code": "migration_batch_unreadable",
            "detail": f"{path} carries no rows list — refusing",
        })
    return rows


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


def _evidence_classification_context_digest(task_versions, context):
    """FEAT-074: pin EVERY classification input of a resumable evidence
    migration — the task-version mapping AND the entity-registration context
    (hot-table states, layout anomalies, requirement-registry ids) the
    five-state classifier consumes. A resume whose world (plan-tracker) no
    longer matches the pinned context refuses loudly instead of silently
    re-classifying against different entity registrations."""
    payload = {
        "task_versions": sorted((str(k), str(v))
                                for k, v in (task_versions or {}).items()),
        "hot_tasks": sorted(
            (str(k), str(v.get("status", "")), str(v.get("version", "")))
            for k, v in (context or {}).get("hot_tasks", {}).items()),
        "hot_anomalies": sorted(
            (str(k), int(p))
            for k, p in (context or {}).get("hot_anomalies", {}).items()),
        "requirement_ids": sorted(
            (context or {}).get("requirement_ids", ())),
    }
    return _sha256_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))


# ── FEAT-075 (DEC-278 unit two): four-family read-only scan + write guard ──
#
# DEC-278 §3.1 单元二: EVD/REVIEW/RECO/TRIAGE four governance row families,
# read-only dry-run scan reusing unit one's classification semantics (the
# five entity states + the six task conditions via _make_ref_verdict /
# _REF_FAILURE_SUBSTATE_ORDER — NO parallel implementation), with each
# family parsed by its OWN id-shape/schema (no assumed isomorphism: EVD ids
# are EVD-N / EVD-FIX-247 with refs in the 关联Task column; REVIEW ids
# embed the reviewed task REVIEW-{TASK}[-SCOPE][-R{n}]; TRIAGE-/RECO- ids
# embed their governing task TRIAGE-{TASK} / RECO-{TASK}). Per DEC-278 §3.2
# the scanner writes NOTHING, and the three non-EVD families are REFUSED at
# code level should they ever reach a write-migration execution path.

#: Families the write-migration paths may carry. FEAT-076 (0.93.0, DEC-293
#: Wave2 全量执行; DEC-287 clearing round; DEC-282 C-1(b)'s 0.93
#: re-authorization conditions delivered in the same version): the 0.92
#: write boundary (DEC-278 §3.2 — EVD-only) is superseded; all FOUR
#: families now carry write migration through the same classification
#: semantics the scan uses (single source, zero drift).
_WRITE_MIGRATION_ROW_FAMILIES = frozenset({"EVD", "REVIEW", "RECO", "TRIAGE"})
#: Families refused at write migration: none of the four known families
#: anymore (0.93 unlock). The guard choke point REMAINS — any family id
#: outside _WRITE_MIGRATION_ROW_FAMILIES (typos, future families not yet
#: admitted) still raises RowFamilyMigrationRejected regardless of dry_run.
_ROW_FAMILY_WRITE_MIGRATION_REFUSED = frozenset()
#: All four families the read-only scanner covers (DEC-278 §3.1 单元二).
_SCAN_ROW_FAMILIES = ("EVD", "REVIEW", "RECO", "TRIAGE")


class RowFamilyMigrationRejected(BigTableMigrationError):
    """FEAT-075 (DEC-278 §3.2): a dry-run-only governance row family reached
    a WRITE-migration execution path. Code-level refusal — not an operator
    convention; the CLI prints the payload and exits non-zero."""


def _guard_row_family_write_migration(row_family):
    """The write-boundary choke point for every migrate entry.

    FEAT-076 (0.93.0): all four known families pass — the 0.92 EVD-only
    boundary (DEC-278 §3.2) was superseded by the clearing-round
    authorization chain (DEC-287 → DEC-292 Wave2 unlock → DEC-293 全量执
    行) WITH the DEC-282 C-1(b) re-authorization conditions delivered in
    the same version (unified read entry via GovernanceDataSource family
    surface, consumer matrix, query-equivalence check faces, digest-pinned
    manifests, read-back + rollback drill). Any family id outside
    _WRITE_MIGRATION_ROW_FAMILIES still raises — the choke point guards
    against typos and unadmitted future families, not against the four
    sanctioned ones.
    """
    if row_family in _WRITE_MIGRATION_ROW_FAMILIES:
        return
    raise RowFamilyMigrationRejected({
        "code": "row_family_write_migration_rejected",
        "detail": (
            f"row family {row_family!r} is not an admitted write-migration "
            f"family. Admitted families: "
            f"{sorted(_WRITE_MIGRATION_ROW_FAMILIES)}; read-only coverage: "
            f"archive.py scan-families"
        ),
        "family": row_family,
    })


def _row_family_journal_category(row_family):
    """FEAT-076: the journal state-dir category for one family's resumable
    migration. EVD keeps the legacy ``evidence`` category (in-flight 0.92
    journals stay resolvable); the three unlocked families get their own
    ``evidence-{family}`` category so same-range migrations of different
    families NEVER collide on a journal (each judges its own world)."""
    _guard_row_family_write_migration(row_family)
    if row_family == "EVD":
        return "evidence"
    return f"evidence-{row_family.lower()}"






def _classify_family_rows(family, lines, line_bytes, task_versions,
                          version_start, version_end, ref_verdict):
    """FEAT-075: classify one non-EVD family's rows under unit one's six
    conditions (shared _make_ref_verdict typer + severity ordering). The
    would_archive verdict feeds BOTH surfaces single-source since FEAT-076:
    the read-only scanner's candidacy projection AND the admitted write
    migration for these families (zero drift by construction). Returns
    per-row records in scan order."""
    id_line_counts = {}
    prefix = f"| {family}-"
    for line_idx, line in enumerate(lines):
        if not line.strip().startswith(prefix):
            continue
        parts = [p.strip() for p in line.split("|")]
        row_id = parts[1] if len(parts) > 1 else ""
        if row_id and _ROW_FAMILY_ID_RES[family].match(row_id):
            id_line_counts.setdefault(row_id, []).append(line_idx)

    records = []
    for line_idx, line in enumerate(lines):
        if not line.strip().startswith(prefix):
            continue
        parsed = _parse_family_row(family, line)
        row_bytes = line_bytes[line_idx]
        if parsed is None:
            parts = [p.strip() for p in line.split("|")]
            records.append({"family": family, "id": (parts[1] if len(parts) > 1 else "") or "?",
                            "line_idx": line_idx, "bytes": row_bytes,
                            "line": line,
                            "migrate": False, "version": None,
                            "reason": "unknown_row_id_shape",
                            "detail": "row ID shape not recognized for family",
                            "ref_types": {}})
            continue
        row_id, refs, ref_column = parsed
        ref_types = {}
        verdicts = {}
        for tid in sorted(refs):
            entity_state, verdict, payload = ref_verdict(tid)
            ref_types[tid] = entity_state
            verdicts[tid] = (verdict, payload)

        def _record(reason, detail, migrate=False, version=None):
            records.append({"family": family, "id": row_id,
                            "line_idx": line_idx, "bytes": row_bytes,
                            "line": line,
                            "migrate": migrate, "version": version,
                            "reason": reason, "detail": detail,
                            "ref_types": ref_types})

        # Six-condition 6 (row identity): duplicate shape-valid id.
        if len(id_line_counts.get(row_id, ())) > 1:
            _record("duplicate_row_id",
                    f"id appears {len(id_line_counts[row_id])} times in input")
            continue
        # Six-condition 5: explicit keep marker — whole-row scan.
        if any(marker in line for marker in _EVIDENCE_KEEP_MARKERS):
            _record("explicit_keep_marker",
                    "row carries an explicit keep marker (retained hot)")
            continue
        gating_fails = {tid: payload for tid, (verdict, payload)
                        in verdicts.items() if verdict == "fail"}
        if not refs or all(v == "nongate" for v, _p in verdicts.values()):
            # No gating task ref at all. FEAT-076 (0.93): Q6 date-window
            # fallback applies to the three unlocked families identically
            # (DEC-278 单元三 ruling — 实体状态优先，日期窗兜底).
            fallback = _q6_date_window_fallback(line, version_end)
            if fallback is not None:
                _record("would_archive_date_window", fallback,
                        migrate=True, version=None)
            else:
                _record("no_task_family_ref",
                        f"refs: {(', '.join(sorted(refs)) or '(none)')[:40]}")
            continue
        if gating_fails:
            for substate, reason in _REF_FAILURE_SUBSTATE_ORDER:
                ids = sorted(t for t, p in gating_fails.items()
                             if p == substate or (
                                 substate == "ambiguous"
                                 and str(p).startswith("ambiguous")))
                if ids:
                    _record(reason, "blocking refs: " + ",".join(ids[:5]))
                    break
            continue
        # Six-condition 3: owning cycle = MAX resolved ref version.
        resolved_versions = [payload for _t, (verdict, payload)
                             in verdicts.items() if verdict == "pass"]
        owning = max(resolved_versions, key=_version_to_tuple)
        if _version_in_range(owning, version_start, version_end):
            _record("would_archive", f"v{owning} (max ref version)",
                    migrate=True, version=owning)
        else:
            _record("ref_version_out_of_range",
                    f"owning cycle v{owning} outside "
                    f"[{version_start}, {version_end}]")
    return records


def _scan_git_commit_anchor(root):
    """FEAT-075: the reproducibility anchor's git commit (input anchoring is
    M-0 prerequisite 1 of 5: 测量工具+输入 commit+逐行输出). 'unknown' when
    git is unavailable — the sha256 digests remain the hard anchor."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    head = (result.stdout or "").strip() if result.returncode == 0 else ""
    return head or "unknown"


def scan_row_families(version_start, version_end, *, families=None,
                      task_versions=None, context=None, content=None,
                      plan_tracker_content=None):
    """FEAT-075 (DEC-278 单元二): READ-ONLY dry-run scan of the four
    governance row families (EVD/REVIEW/RECO/TRIAGE).

    Classification reuses unit one's semantics single-source: the EVD family
    is classified by ``_classify_evidence_rows`` itself (zero drift by
    construction); REVIEW/TRIAGE/RECO by ``_classify_family_rows`` on the
    shared ``_make_ref_verdict`` typer + ``_REF_FAILURE_SUBSTATE_ORDER``
    severity ordering (five entity states + six task conditions). Each
    family keeps its OWN parser/schema (see _ROW_FAMILY_ID_RES /
    _parse_family_row) — no assumed isomorphism of id shape or ref column.

    Reproducible-baseline carrying (M-0 prerequisite 1 of 5): the report
    anchors its inputs (git commit + evidence-log/plan-tracker sha256
    digests) and emits a per-line classification that is saveable and
    diffable (format_family_scan_tsv). This function performs ZERO writes —
    not to the evidence-log, not to any .governance file (asserted by
    regression tests via before/after sha256).

    Args:
        version_start / version_end: the retention window (would_archive is
            reported relative to this window; the window NEVER gates what is
            scanned — every family row produces a record).
        families: subset of _SCAN_ROW_FAMILIES (None → all four).
        task_versions: optional {task_id: version} mapping (None → the
            standalone mapping, same as migrate_evidence_resumable).
        context: optional prebuilt classification context (None → built
            from the live plan-tracker / plan_tracker_content).
        content: optional evidence-log text (None → read the live file).
        plan_tracker_content: optional plan-tracker text for the context.

    Returns the full report dict (schema row-family-scan/1):
        anchors / window / coverage (per-family rows+bytes+reasons, explicit
        malformed and non-family counts — nothing silently skipped) /
        rows (per-line records: 实体解析 ref_types, 周期归属 version, 保留原因
        reason+detail, 候选状态 migrate, 字节量 bytes) / write_boundary.
    """
    families = tuple(_SCAN_ROW_FAMILIES) if families is None else tuple(families)
    for family in families:
        if family not in _SCAN_ROW_FAMILIES:
            raise ValueError(f"unknown row family {family!r}")
    elog = _evidence_log()
    if content is None:
        raw = elog.read_bytes()
        content = raw.decode("utf-8")
        evidence_bytes = len(raw)
        evidence_digest = _sha256_text(content)
        evidence_path = str(elog)
    else:
        evidence_bytes = len(content.encode("utf-8"))
        evidence_digest = _sha256_text(content)
        evidence_path = str(elog)
    if context is None:
        context = _build_classification_context(plan_tracker_content)
    if plan_tracker_content is None:
        try:
            # Byte-faithful read (read_text's universal-newline translation
            # would hash CRLF files differently from their on-disk bytes).
            plan_tracker_content = _plan_tracker().read_bytes().decode("utf-8")
        except OSError:
            plan_tracker_content = ""
    if task_versions is None:
        task_versions = _evidence_task_versions_standalone()

    lines = content.split("\n")
    # FEAT-074 §1 raw byte口径: per-line UTF-8 length + 1 newline byte (the
    # final line carries none) — CRLF rows keep their \r. Same basis as the
    # unit-one diff doc and Check 28s st_size totals.
    line_bytes = [len(line.encode("utf-8")) + (0 if i == len(lines) - 1 else 1)
                  for i, line in enumerate(lines)]

    rows = []
    coverage_families = {}
    for family in families:
        if family == "EVD":
            evd_records = _classify_evidence_rows(
                content, task_versions, version_start, version_end,
                context=context)
            family_rows = []
            for r in evd_records:
                family_rows.append({
                    "family": "EVD", "id": r["id"], "line_idx": r["line_idx"],
                    "bytes": line_bytes[r["line_idx"]], "migrate": r["migrate"],
                    "version": r["version"], "reason": r["reason"],
                    "detail": r["detail"], "ref_types": dict(r["ref_types"]),
                })
        else:
            family_rows = _classify_family_rows(
                family, lines, line_bytes, task_versions,
                version_start, version_end,
                _make_ref_verdict(task_versions, context))
        rows.extend(family_rows)
        reasons = {}
        for r in family_rows:
            slot = reasons.setdefault(r["reason"], [0, 0])
            slot[0] += 1
            slot[1] += r["bytes"]
        coverage_families[family] = {
            "rows": len(family_rows),
            "bytes": sum(r["bytes"] for r in family_rows),
            "malformed_rows": sum(1 for r in family_rows
                                  if r["reason"] in ("unknown_evd_id_shape",
                                                     "unknown_row_id_shape")),
            "would_archive_rows": sum(1 for r in family_rows if r["migrate"]),
            "would_archive_bytes": sum(r["bytes"] for r in family_rows
                                       if r["migrate"]),
            "reasons": reasons,
        }

    family_prefixes = tuple(f"| {family}-" for family in families)
    scanned = {r["line_idx"] for r in rows}
    other_table_lines = 0
    non_table_lines = 0
    for line_idx, line in enumerate(lines):
        if line_idx in scanned:
            continue
        stripped = line.strip()
        if stripped.startswith("|"):
            other_table_lines += 1
        else:
            non_table_lines += 1
    coverage = {
        "total_lines": len(lines),
        "scanned_family_rows": len(rows),
        "other_table_lines": other_table_lines,
        "non_table_lines": non_table_lines,
        "unclaimed_family_prefix_lines": sum(
            1 for line_idx, line in enumerate(lines)
            if line_idx not in scanned
            and line.strip().startswith(family_prefixes)),
        "families": coverage_families,
    }

    rows.sort(key=lambda r: (r["family"], r["line_idx"]))
    return {
        "schema": "row-family-scan/1",
        "dry_run": True,
        "anchors": {
            "git_commit": _scan_git_commit_anchor(ROOT),
            "evidence_log_path": evidence_path,
            "evidence_log_bytes": evidence_bytes,
            "evidence_log_sha256": evidence_digest,
            "plan_tracker_sha256": _sha256_text(plan_tracker_content),
            "task_versions_count": len(task_versions),
        },
        "window": {"start": version_start, "end": version_end},
        "coverage": coverage,
        "rows": rows,
        "write_boundary": {
            "migratable_families": sorted(_WRITE_MIGRATION_ROW_FAMILIES),
            "write_migration_refused": sorted(
                _ROW_FAMILY_WRITE_MIGRATION_REFUSED),
            "note": ("FEAT-076 (0.93.0): all four families carry write "
                     "migration through migrate-big-table / migrate --auto "
                     "(ALL); would_archive here IS the migration candidacy "
                     "the write path uses (single classification source)"),
        },
    }


def format_family_scan_tsv(report):
    """FEAT-075: the diffable per-line report — one deterministic TSV line
    per scanned row (sorted family, then scan order), so two runs on the
    same input diff to nothing and any classification change diffs exactly
    where it changed."""
    header = ("family\tid\tline_idx\tbytes\tcandidate\towning_version\t"
              "reason\tref_types\tdetail")
    out = [header]
    for r in report["rows"]:
        ref_types = ",".join(f"{tid}:{state}"
                             for tid, state in sorted(r["ref_types"].items()))
        detail = (r["detail"] or "").replace("\t", " ")
        out.append("\t".join((
            r["family"], r["id"], str(r["line_idx"]), str(r["bytes"]),
            "would_archive" if r["migrate"] else "retain_hot",
            r["version"] or "-", r["reason"], ref_types, detail,
        )))
    return "\n".join(out) + "\n"


def format_family_scan_summary(report):
    """FEAT-075: the human summary the CLI prints (four-family dry-run)."""
    cov = report["coverage"]
    lines = []
    for family, stats in cov["families"].items():
        lines.append(
            f"  {family}: {stats['rows']} rows / {stats['bytes']:,} B — "
            f"would_archive {stats['would_archive_rows']} rows / "
            f"{stats['would_archive_bytes']:,} B "
            f"(malformed/unknown {stats['malformed_rows']})")
        for reason, (count, nbytes) in sorted(stats["reasons"].items(),
                                              key=lambda kv: (-kv[1][0], kv[0])):
            lines.append(f"      {reason}: {count} rows / {nbytes:,} B")
    lines.append(
        f"  coverage: {cov['total_lines']} lines total = "
        f"{cov['scanned_family_rows']} family rows + "
        f"{cov['other_table_lines']} other table lines + "
        f"{cov['non_table_lines']} non-table lines"
        + (f" (unclaimed family-prefix lines: "
           f"{cov['unclaimed_family_prefix_lines']})"
           if cov["unclaimed_family_prefix_lines"] else ""))
    return "\n".join(lines)


def write_family_scan_outputs(report, tsv_path=None, json_path=None):
    """FEAT-075: save the per-line dry-run report (可落盘/可 diff — M-0
    prerequisite 1). Output paths under the .governance directory are
    REFUSED: the dry-run contract is zero governance-data writes."""
    guard_dir = _gov_dir().resolve()
    for label, path in (("tsv", tsv_path), ("json", json_path)):
        if path is None:
            continue
        target = Path(path)
        try:
            resolved = target.resolve()
        except OSError:
            resolved = target.absolute()
        if resolved == guard_dir or guard_dir in resolved.parents:
            raise BigTableMigrationError({
                "code": "family_scan_output_refused",
                "detail": (
                    f"{label} output {path!r} is inside .governance — the "
                    "dry-run contract writes zero governance data files "
                    "(DEC-278 单元二红线: dry-run 零写入)"),
            })
        if label == "tsv":
            target.write_text(format_family_scan_tsv(report),
                              encoding="utf-8", newline="\n")
        else:
            target.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8", newline="\n")


def _evidence_finalized_world(journal, input_digest, journal_path, dry_run):
    """FIX-417 pipeline stage: a FINALIZED journal's world judgment.

    Returns the already-completed result dict when the hot table matches the
    committed post-image; None when the commit was recorded but the hot leg
    provably never ran (fall through and complete the apply leg, idempotent);
    raises BigTableMigrationError on the ambiguous world (matches neither
    digest).
    """
    commit = journal.get("commit") or {}
    if input_digest == commit.get("hot_after_digest"):
        return {"success": True, "dry_run": bool(dry_run),
                "migrated": len(journal.get("candidates") or []),
                "batches_total": journal.get("batches_total"),
                "batch_size": journal.get("batch_size"),
                "resumed": "already_finalized",
                "journal_path": str(journal_path),
                "archive_file": f"archive/evidence/"
                                f"{commit.get('archive_file')}",
                "decision_authority_state": _decision_authority_state()}
    if input_digest != journal.get("input_digest"):
        # Ambiguous world: the hot table matches NEITHER the committed
        # post-image NOR the pinned input. Cannot prove the commit
        # completed → refuse loudly (a double migration is worse than
        # a stopped one; FEAT-061 完整性失败重启 semantics).
        raise BigTableMigrationError({
            "code": "migration_state_conflict",
            "detail": (
                "journal says finalized but the hot table matches "
                "neither the committed post-migration digest nor the "
                f"pinned input digest ({journal_path}) — manual "
                "inspection required; deleting the migration state dir "
                "starts a deliberate NEW migration"),
        })
    return None


def _evidence_resume_world(journal, *, journal_category, version_start,
                           version_end, journal_path, input_digest, lines,
                           dry_run, evidence_task_versions,
                           classification_context):
    """FIX-417 pipeline stage: resume world judgment against the pinned plan.

    Returns (doc, candidates, batches_total, batch_size, early_result);
    early_result is non-None only for the resumed dry-run report.
    """
    # ── resume: world judgment against the pinned plan ──
    if journal.get("category") != journal_category or tuple(
            journal.get("version_range") or ()) != (version_start,
                                                    version_end):
        raise BigTableMigrationError({
            "code": "migration_journal_conflict",
            "detail": f"{journal_path} belongs to another migration "
                      f"(category={journal.get('category')!r}, "
                      f"range={journal.get('version_range')}) — refusing",
        })
    doc = journal
    _commit = doc.get("commit")
    # Crash-after-hot-rewrite world: the current hot file matches the
    # COMMITTED post-image — the input-digest check below would
    # misread this completed leg as divergence. Judge the commit pin
    # FIRST (world-judgment order: committed → input → diverged).
    hot_leg_done = bool(_commit) and \
        input_digest == _commit.get("hot_after_digest")
    if not hot_leg_done:
        if input_digest != journal.get("input_digest"):
            raise BigTableMigrationError({
                "code": "hot_table_diverged",
                "detail": (
                    "evidence-log.md diverged from the pinned input digest "
                    f"(journal {journal.get('input_digest')[:12]}… vs "
                    f"current {input_digest[:12]}…) — a concurrent writer "
                    "mutated the table mid-migration; per FEAT-061 "
                    "completeness semantics this migration is NOT "
                    "continued: resolve the divergence, then delete the "
                    "migration state dir to restart"),
            })
        context_digest = _evidence_classification_context_digest(
            evidence_task_versions, classification_context)
        if context_digest != journal.get("context_digest"):
            raise BigTableMigrationError({
                "code": "migration_context_changed",
                "detail": (
                    "the task-version context changed since the plan was "
                    "pinned — the candidate manifest may no longer match "
                    "this context; re-judge and restart the migration"),
            })
    batch_size = doc["batch_size"]
    batches_total = doc["batches_total"]
    if hot_leg_done:
        # The pinned input no longer exists on disk (this IS the
        # post-migration world), so pinned line_idx values cannot be
        # validated against `lines` — their integrity is enforced
        # cryptographically downstream (batch rows re-materialized and
        # digest-verified against the commit pin). No line binding here:
        # neither the archive rows (staged batches) nor the hot text
        # (current content) is derived from them on this path.
        candidates = [{"id": c.get("id"), "line_idx": c.get("line_idx"),
                       "version": c.get("version"), "line": None}
                      for c in doc.get("candidates") or []]
    else:
        candidates = []
        for c in doc.get("candidates") or []:
            idx = c.get("line_idx")
            if not isinstance(idx, int) or idx < 0 or idx >= len(lines):
                raise BigTableMigrationError({
                    "code": "migration_journal_unreadable",
                    "detail": f"pinned candidate line_idx {idx!r} is out "
                              "of range for the pinned input — journal "
                              "corrupt",
                })
            candidates.append({"id": c.get("id"), "line_idx": idx,
                               "version": c.get("version"),
                               "line": lines[idx]})
    if dry_run:
        # dry-run honors zero-write on a resumed world too: report the
        # pinned plan's remaining scope without touching anything.
        early = {"success": True, "dry_run": True,
                 "migrated": len(candidates),
                 "batches_total": batches_total, "batch_size": batch_size,
                 "resumed": True,
                 "journal_path": str(journal_path),
                 "archive_file": (f"archive/evidence/"
                                  f"{doc['commit']['archive_file']}"
                                  if doc.get("commit") else None),
                 "decision_authority_state": _decision_authority_state()}
        return doc, candidates, batches_total, batch_size, early
    return doc, candidates, batches_total, batch_size, None


def _evidence_fresh_plan(content, *, row_family, evidence_task_versions,
                         classification_context, version_start, version_end,
                         batch_size, dry_run, state_dir, batches_dir,
                         journal_path, journal_category, input_digest):
    """FIX-417 pipeline stage: fresh plan (classify, pin the world, journal
    phase=intent).

    Returns (doc, candidates, batches_total, early_result); early_result is
    non-None for the fresh dry-run report and the no-candidates skip.
    """
    # ── fresh plan ──
    records = _classify_rows_for_family(
        row_family, content, evidence_task_versions,
        version_start, version_end, context=classification_context)
    candidates = [r for r in records if r["migrate"]]
    batches_total = (len(candidates) + batch_size - 1) // batch_size
    if dry_run:
        early = {"success": True, "dry_run": True,
                 "migrated": len(candidates),
                 "batches_total": batches_total, "batch_size": batch_size,
                 "resumed": False, "journal_path": None,
                 "archive_file": None,
                 "decision_authority_state": _decision_authority_state()}
        return None, candidates, batches_total, early
    if not candidates:
        early = {"success": True, "dry_run": False, "migrated": 0,
                 "batches_total": 0, "batch_size": batch_size,
                 "resumed": False,
                 "skipped": "归档范围内无可迁移 evidence 行",
                 "journal_path": None, "archive_file": None,
                 "decision_authority_state": _decision_authority_state()}
        return None, candidates, batches_total, early
    state_dir.mkdir(parents=True, exist_ok=True)
    batches_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema": _MIGRATION_JOURNAL_SCHEMA,
        "category": journal_category,
        "row_family": row_family,
        "version_range": [version_start, version_end],
        "input_digest": input_digest,
        "context_digest": _evidence_classification_context_digest(
            evidence_task_versions, classification_context),
        "batch_size": batch_size,
        "batches_total": batches_total,
        "candidates": [{"id": c["id"], "line_idx": c["line_idx"],
                        "version": c["version"]} for c in candidates],
        "batches_staged": 0,
        "phase": "intent",
        "created_at": datetime.now().replace(microsecond=0).isoformat(),
    }
    _migration_write_journal(journal_path, doc)
    return doc, candidates, batches_total, None


def _evidence_stage_batches(doc, *, journal_path, batches_dir, candidates,
                            batches_total, batch_size, resumed):
    """FIX-417 pipeline stage: advance the batch cursor (断点续迁
    granularity). Every batch is staged atomically and the journal cursor
    follows; the cursor is validated against its artifacts on resume."""
    batches_staged = doc.get("batches_staged", 0)
    if resumed:
        # the cursor never lies ahead of its artifacts — a staged batch that
        # vanished while the cursor claims it is tampering/corruption → loud
        for k in range(batches_staged):
            if not _migration_batch_path(batches_dir, k).is_file():
                raise BigTableMigrationError({
                    "code": "migration_cursor_ahead_of_artifacts",
                    "detail": (f"journal cursor claims batch {k} is staged "
                               f"but {_migration_batch_path(batches_dir, k)} "
                               "is missing — journal/artifact inconsistent; "
                               "refusing"),
                })
    batches_dir.mkdir(parents=True, exist_ok=True)
    doc["phase"] = "staging"
    for k in range(batches_staged, batches_total):
        chunk = candidates[k * batch_size:(k + 1) * batch_size]
        _migration_write_batch(batches_dir, k, [c["line"] for c in chunk])
        doc["batches_staged"] = k + 1
        _migration_write_journal(journal_path, doc)
    doc["phase"] = "staged"
    doc["batches_staged"] = batches_total
    _migration_write_journal(journal_path, doc)


def _evidence_compose_commit(doc, *, content, lines, candidates,
                             batches_total, resumed, input_digest,
                             version_start, version_end, journal_category,
                             row_family, batches_dir, journal_path):
    """FIX-417 pipeline stage: compose the deterministic commit outputs
    (archive path/text, post-migration hot text, journal commit pin).

    Crash-after-hot-rewrite resume re-materializes the archive rows from the
    STAGED BATCH ARTIFACTS and verifies them against the pin — never
    recomputed from the hot text. Returns (archive_path, archive_text,
    new_hot_text, hot_done, archive_relname, archived_rows).
    """
    # Deterministic commit outputs, re-materializable from the pinned plan.
    commit = doc.get("commit")

    if resumed and commit is not None and \
            input_digest == commit.get("hot_after_digest"):
        # ── crash-after-hot-rewrite resume: complete the finalize leg only.
        # The hot file no longer carries the candidate lines, so the rows
        # are re-materialized from the STAGED BATCH ARTIFACTS (load-bearing)
        # and verified against the pin — never recomputed from the hot text.
        archived_rows = []
        for k in range(batches_total):
            archived_rows.extend(_migration_load_batch(batches_dir, k))
        if len(archived_rows) != len(candidates):
            raise BigTableMigrationError({
                "code": "migration_state_conflict",
                "detail": ("staged batches carry "
                           f"{len(archived_rows)} rows but the pinned "
                           f"manifest has {len(candidates)} — refusing"),
            })
        archive_relname = commit["archive_file"]
        archive_path = _archive_dir() / "evidence" / archive_relname
        header = _build_archive_header(version_start, version_end,
                                       journal_category,
                                       len(archived_rows), prev_file=None,
                                       next_file=None)
        archive_text = header + "\n" + "\n".join(
            list(_row_family_archive_table_header(row_family))
            + archived_rows) + "\n"
        if _sha256_text(archive_text) != commit.get("archive_digest"):
            raise BigTableMigrationError({
                "code": "migration_state_conflict",
                "detail": ("re-materialized archive content does not match "
                           "the pinned commit digest — journal/artifacts "
                           "inconsistent; refusing"),
            })
        # The pinned post-image is digest-equal to the current world; the
        # apply block's hot leg is skipped (hot_done=True) — the binding is
        # only kept so the variable is defined on every path.
        new_hot_text = content
        hot_done = True
    else:
        # ── fresh or pre-apply resume: compose the commit outputs ──
        archived_rows = [c["line"] for c in candidates]
        candidate_idx = {c["line_idx"] for c in candidates}
        new_hot_text = "\n".join(
            ln for i, ln in enumerate(lines) if i not in candidate_idx)
        if resumed and commit is not None:
            # verify the re-materialized outputs against the pinned commit
            # (the pin was computed against the same pinned input — any
            # drift is corruption, never a re-pin)
            if _sha256_text(new_hot_text) != commit.get("hot_after_digest") \
                    or len(archived_rows) != commit.get("archive_rows"):
                raise BigTableMigrationError({
                    "code": "migration_state_conflict",
                    "detail": ("pinned commit record does not match the "
                               "pinned input re-materialization — journal "
                               "corrupt; refusing"),
                })
            archive_relname = commit["archive_file"]
        else:
            archive_relname = _next_family_archive_filename(
                version_start, version_end, row_family)
        archive_path = _archive_dir() / "evidence" / archive_relname
        header = _build_archive_header(version_start, version_end,
                                       journal_category,
                                       len(archived_rows), prev_file=None,
                                       next_file=None)
        archive_text = header + "\n" + "\n".join(
            list(_row_family_archive_table_header(row_family))
            + archived_rows) + "\n"
        doc["commit"] = {
            "archive_file": archive_relname,
            "archive_digest": _sha256_text(archive_text),
            "hot_after_digest": _sha256_text(new_hot_text),
            "archive_rows": len(archived_rows),
        }
        doc["phase"] = "commit_intent"
        _migration_write_journal(journal_path, doc)
        hot_done = False
    return archive_path, archive_text, new_hot_text, hot_done, \
        archive_relname, archived_rows


def _evidence_apply_commit(doc, *, journal_path, elog, archive_path,
                           archive_text, new_hot_text, hot_done):
    """FIX-417 pipeline stage: the single linearization window (FEAT-060
    three-phase apply). Executes under the hot-table lock in the order
    archive → hot → finalize, so every crash window is recoverable."""
    # ── apply: the single linearization window (FEAT-060 three-phase) ──
    with _big_table_target_lock(elog):
        current_digest = _sha256_text(elog.read_text(encoding="utf-8"))
        if current_digest == doc["commit"]["hot_after_digest"]:
            hot_done = True    # crash-after-hot-rewrite world (or idempotent)
        elif current_digest != doc["input_digest"]:
            raise BigTableMigrationError({
                "code": "hot_table_diverged",
                "detail": (
                    "evidence-log.md diverged inside the commit window "
                    "(matches neither the pinned input nor the committed "
                    "post-image) — freeze-window completeness FAILED; "
                    "refusing (FEAT-061 semantics: 完整性失败重启)"),
            })
        if archive_path.exists():
            existing_digest = _sha256_text(
                archive_path.read_text(encoding="utf-8"))
            if existing_digest != doc["commit"]["archive_digest"]:
                raise BigTableMigrationError({
                    "code": "archive_target_conflict",
                    "detail": (f"{archive_path} already exists with FOREIGN "
                               "content (digest mismatch vs the pinned "
                               "commit) — refusing to overwrite"),
                })
        else:
            # FEAT-076: family legs may be the FIRST archive write in a
            # fresh world — the target subdir must exist before the
            # atomic write (mkstemp inside a missing dir raises).
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write_text(archive_path, archive_text)
        if not hot_done:
            _atomic_write_text(elog, new_hot_text)
        doc["phase"] = "finalized"
        _migration_write_journal(journal_path, doc)


def migrate_evidence_resumable(version_start, version_end, *,
                               batch_size=BIG_TABLE_MIGRATION_BATCH_SIZE,
                               dry_run=False, task_versions=None,
                               row_family="EVD"):
    """FIX-385 (B-7b): batched, journaled, RESUMABLE migration of the
    evidence-log table into the archive.

    FEAT-076 (0.93.0): ``row_family`` selects WHICH family this leg
    migrates — all four (EVD/REVIEW/RECO/TRIAGE) are admitted; each family
    migrates through its OWN journal (category ``evidence`` for EVD,
    ``evidence-{family}`` for the others) so same-range legs never collide,
    and classification is single-sourced through
    _classify_rows_for_family (the same semantics scan-families reports —
    scan candidacy and migration candidacy cannot drift).

    Pipeline (FEAT-060/FEAT-061 crash-recovery semantics; FIX-417 extracts
    each stage into its own helper — _evidence_finalized_world /
    _evidence_resume_world / _evidence_fresh_plan / _evidence_stage_batches
    / _evidence_compose_commit / _evidence_apply_commit):

      plan    — classify rows (single-sourced _classify_evidence_rows),
                pin the world: input digest + context (task mapping) digest
                + the full candidate manifest, journal phase=intent.
      stage   — per-batch cursor: each batch of rows is staged atomically
                (batches/batch-NNNNNN.json) and the journal cursor
                (batches_staged) is advanced. An interruption loses at most
                the current batch; resume continues AT the cursor.
      commit  — commit_intent pins the linearization point's outputs
                (archive file name + content digest, expected post-migration
                hot digest); apply executes under the hot-table lock in the
                order archive → hot → finalize, so every crash window is
                recoverable:
                  crash after archive write  → resume rewrites hot only
                  crash after hot rewrite    → resume finalizes only
      resume  — judges the WORLD first: current == pinned input → continue;
                current == committed post-image → complete the leg;
                anything else → loud refusal (hot_table_diverged /
                migration_state_conflict), never a guess. A COMPLETED
                migration whose journal post-image no longer matches the
                hot table is an ambiguous world → loud refusal (deleting
                the journal dir starts a deliberate new migration).

    Args:
        version_start / version_end: semver range ("0.60.0", "0.61.0").
        batch_size: rows per staged batch (>= 1).
        dry_run: plan-only report; zero writes, no journal.
        task_versions: optional explicit {task_id: version} mapping (this-
            run-augmented, migrate-style). None → the standalone mapping
            (_evidence_task_versions_standalone: archived + FIX-235
            completed-hot).

    Returns a structured result dict (success/migrated/batches_total/
    resumed/journal_path/archive_file/decision_authority_state/...).
    Raises BigTableMigrationError on every fail-closed refusal.
    """
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) \
            or batch_size < 1:
        raise BigTableMigrationError({
            "code": "schema_violation",
            "detail": f"batch_size must be an int >= 1, got {batch_size!r}",
        })
    _guard_row_family_write_migration(row_family)
    journal_category = _row_family_journal_category(row_family)
    elog = _evidence_log()
    if not elog.exists():
        return {"success": True, "dry_run": bool(dry_run), "migrated": 0,
                "batches_total": 0, "batch_size": batch_size, "resumed": False,
                "skipped": "evidence-log.md 不存在", "journal_path": None,
                "archive_file": None,
                "decision_authority_state": _decision_authority_state()}
    if task_versions is None:
        evidence_task_versions = _evidence_task_versions_standalone()
    else:
        evidence_task_versions = dict(task_versions)
    # FEAT-074: the entity-registration context is built ONCE and pinned by
    # digest — the plan and every resume judge the same world.
    classification_context = _build_classification_context()

    journal_path = _migration_journal_path(journal_category, version_start,
                                           version_end)
    state_dir = journal_path.parent
    batches_dir = state_dir / "batches"

    content = elog.read_text(encoding="utf-8")
    lines = content.split("\n")
    input_digest = _sha256_text(content)

    journal = _migration_load_journal(journal_path)

    # ── finalized journal: judge the world ──
    if journal is not None and journal.get("phase") == "finalized":
        early = _evidence_finalized_world(journal, input_digest,
                                          journal_path, dry_run)
        if early is not None:
            return early

    resumed = journal is not None
    if resumed:
        doc, candidates, batches_total, batch_size, early = \
            _evidence_resume_world(
                journal, journal_category=journal_category,
                version_start=version_start, version_end=version_end,
                journal_path=journal_path, input_digest=input_digest,
                lines=lines, dry_run=dry_run,
                evidence_task_versions=evidence_task_versions,
                classification_context=classification_context)
        if early is not None:
            return early
    else:
        doc, candidates, batches_total, early = _evidence_fresh_plan(
            content, row_family=row_family,
            evidence_task_versions=evidence_task_versions,
            classification_context=classification_context,
            version_start=version_start, version_end=version_end,
            batch_size=batch_size, dry_run=dry_run, state_dir=state_dir,
            batches_dir=batches_dir, journal_path=journal_path,
            journal_category=journal_category, input_digest=input_digest)
        if early is not None:
            return early

    _evidence_stage_batches(doc, journal_path=journal_path,
                            batches_dir=batches_dir, candidates=candidates,
                            batches_total=batches_total,
                            batch_size=batch_size, resumed=resumed)

    archive_path, archive_text, new_hot_text, hot_done, archive_relname, \
        archived_rows = _evidence_compose_commit(
            doc, content=content, lines=lines, candidates=candidates,
            batches_total=batches_total, resumed=resumed,
            input_digest=input_digest, version_start=version_start,
            version_end=version_end, journal_category=journal_category,
            row_family=row_family, batches_dir=batches_dir,
            journal_path=journal_path)

    _evidence_apply_commit(doc, journal_path=journal_path, elog=elog,
                           archive_path=archive_path,
                           archive_text=archive_text,
                           new_hot_text=new_hot_text, hot_done=hot_done)

    return {"success": True, "dry_run": False, "migrated": len(archived_rows),
            "batches_total": batches_total, "batch_size": batch_size,
            "resumed": resumed,
            "journal_path": str(journal_path),
            "archive_file": f"archive/evidence/{archive_relname}",
            "hot_after_digest": doc["commit"]["hot_after_digest"],
            "decision_authority_state": _decision_authority_state()}


def _next_evidence_archive_filename(version_start, version_end):
    """FIX-385: the commit's archive target under the incremental-* naming
    discipline (reuse of _make_incremental_archive_filename for the
    category-prefixed evidence family) — a commit never overwrites foreign
    archive content."""
    return _make_incremental_archive_filename(version_start, version_end,
                                              category="evidence")


# ── Auditable Dry-Run Explanation (FIX-301 / AUDIT-150) ─────────────
#
# Reasons that mark a scanned row as UNKNOWN STRUCTURE (counted in the
# unknown_structure bucket, excluded from parsed/retained). Everything else
# is a business retention decision on a structurally parsed row.
_EXPLAIN_UNKNOWN_REASONS = frozenset({
    "pipe_layout_anomaly",      # priority-table row with non-7col pipe layout
    "unknown_evd_id_shape",     # evidence row whose ID matches no real shape
    "decision_row_too_short",   # FIX-312: decision row shorter than the
                                # related-column index / canonical schema —
                                # structurally untrusted, retained fail-closed
})


def _finalize_explain(rows):
    """FIX-301: aggregate per-row reason records into the auditable stats.

    Every scanned candidate row contributes EXACTLY ONE
    {"id", "reason", "detail"} record (collected single-source inside the
    migration functions themselves, so the explanation can never drift from
    the actual migration behavior). From those records:

      scanned          — all candidate rows seen (len(rows))
      parsed           — rows whose structure was trusted for a decision
      would_archive    — rows satisfying every business archive condition
      retained         — parsed rows kept hot (with a business reason)
      unknown_structure— rows whose structure could not be trusted
      unknown_ids      — IDs of the unknown-structure rows

    Returns the stats dict (empty input → zeroed stats, never None).
    """
    scanned = len(rows)
    unknown_rows = [r for r in rows if r["reason"] in _EXPLAIN_UNKNOWN_REASONS]
    parsed = scanned - len(unknown_rows)
    # FIX-407: narrative candidacy rides the same would_archive* prefix
    # (would_archive_narrative_q6) — one vocabulary, one count.
    would = sum(1 for r in rows
                if str(r["reason"]).startswith("would_archive"))
    return {
        "scanned": scanned,
        "parsed": parsed,
        "would_archive": would,
        "retained": parsed - would,
        "unknown_structure": len(unknown_rows),
        "unknown_ids": [r["id"] for r in unknown_rows],
        "rows": rows,
    }


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


# ── Rollback ────────────────────────────────────────────────────────

def _get_migration_archive_group(subdir, archive_file):
    """Return archive files that belong to the same migration.

    A normal migration writes task and evidence archive files with the same
    filename in sibling directories.  Rollback therefore treats those same-name
    files as one migration unit while still supporting older task-only or
    evidence-only archives.

    FIX-164: since evidence files are now named evidence-vX-Y.md (matching the
    FIX-162 decisions/risks convention) while task files stay vX~vY.md, the
    same-name fast path no longer matches them. Fall back to grouping by
    parsed version range so a single rollback undoes the whole migration.
    """
    same_name_group = []
    for candidate_subdir in ["tasks", "evidence"]:
        candidate = _archive_dir() / candidate_subdir / archive_file.name
        if candidate.exists() and candidate.is_file() and candidate.name != ".gitkeep":
            same_name_group.append((candidate_subdir, candidate))

    # Only treat same-name matching as authoritative when it grouped files
    # across BOTH categories (a real same-name pair). When only the input file
    # itself matches its own name, fall through to the range-based fallback so
    # the differently-named sibling gets rolled back too.
    if len(same_name_group) >= 2:
        return same_name_group

    # FIX-164: fall back to grouping by version range so evidence files named
    # evidence-vX-Y.md roll back together with task files vX~vY.md. This ONLY
    # groups across the task/evidence categories for a NON-incremental base
    # migration — independent incremental archive files
    # (vX~vY-incremental-DATE-N.md) share the same range but are separate
    # migration units and must NOT be grouped with the base.
    target_range = _parse_archive_version_range(archive_file.name)
    is_incremental = "-incremental-" in archive_file.name
    if target_range and not is_incremental:
        group = list(same_name_group)  # include any same-name hits (input file)
        input_category = subdir
        for candidate_subdir in ["tasks", "evidence"]:
            if candidate_subdir == input_category:
                continue  # only look across categories (the differently-named sibling)
            d = _archive_dir() / candidate_subdir
            if not d.exists():
                continue
            for f in d.glob("*.md"):
                if f.name == ".gitkeep" or "-incremental-" in f.name:
                    continue
                rng = _parse_archive_version_range(f.name)
                if rng and rng == target_range:
                    entry = (candidate_subdir, f)
                    if entry not in group:
                        group.append(entry)
        if len(group) >= 2:
            return group

    return [(subdir, archive_file)]


def _rollback_task_archive(archive_file):
    """Restore one task archive file into plan-tracker.md and remove it."""
    archive_content = archive_file.read_text(encoding="utf-8")
    pt_content = _plan_tracker().read_text(encoding="utf-8") if _plan_tracker().exists() else ""

    # Find the body after the header section
    body_start = 0
    archive_lines = archive_content.split("\n")
    for i, line in enumerate(archive_lines):
        if line.startswith("#") and "归档" in line:
            continue
        if line.startswith("- **归档日期") or line.startswith("- **归档范围") or \
           line.startswith("- **条目数") or line.startswith("- **上一个") or \
           line.startswith("- **下一个") or line.startswith("> "):
            continue
        if line.startswith("###") or line.startswith("---"):
            body_start = i
            break

    # Append task content back to plan-tracker
    task_body = "\n".join(archive_lines[body_start:])
    new_pt = pt_content.rstrip() + "\n\n" + task_body + "\n"

    # Remove [已归档] markers ONLY from version titles in the archive file's
    # version range (not globally).  Parse the version range from the archive
    # filename first; fall back to extracting versions from archive content.
    filename_range = _parse_archive_version_range(archive_file.name)
    if filename_range:
        version_start, version_end = filename_range
        new_lines = new_pt.split("\n")
        for i, line in enumerate(new_lines):
            v_str, _ = _parse_version_from_title(line)
            if v_str and _version_in_range(v_str, version_start, version_end):
                if "[已归档]" in line and not _version_still_covered_by_task_archive(
                    v_str, archive_file
                ):
                    new_lines[i] = line.replace("[已归档]", "").rstrip()
        new_pt = "\n".join(new_lines)
    else:
        # Fallback: find versions that appear in the archive body
        archive_sections, _ = _find_version_sections(archive_content)
        archived_versions = {
            s["version"] for s in archive_sections if s.get("version")
        }
        if archived_versions:
            new_lines = new_pt.split("\n")
            for i, line in enumerate(new_lines):
                v_str, _ = _parse_version_from_title(line)
                if v_str and v_str in archived_versions:
                    if "[已归档]" in line and not _version_still_covered_by_task_archive(
                        v_str, archive_file
                    ):
                        new_lines[i] = line.replace("[已归档]", "").rstrip()
            new_pt = "\n".join(new_lines)

    _plan_tracker().write_text(new_pt, encoding="utf-8")
    archive_file.unlink()
    return f"{archive_file.name} → plan-tracker.md"


def _rollback_evidence_archive(archive_file):
    """Restore one evidence archive file into evidence-log.md and remove it.

    FEAT-076: the file may carry ANY of the four row families' rows —
    every family-prefixed table row is restored (the 0.92 form only
    extracted ``| EVD-`` rows, which would have unlinked a family archive
    file WITHOUT restoring its rows = rollback data loss).
    """
    archive_content = archive_file.read_text(encoding="utf-8")
    ev_content = _evidence_log().read_text(encoding="utf-8") if _evidence_log().exists() else ""

    # Extract evidence rows from archive (all four families).
    ev_rows = []
    for line in archive_content.split("\n"):
        stripped = line.strip()
        if any(stripped.startswith(prefix)
               for prefix in _ROW_FAMILY_LINE_PREFIXES.values()):
            ev_rows.append(line)

    if ev_rows:
        new_ev = ev_content.rstrip() + "\n" + "\n".join(ev_rows) + "\n"
        _evidence_log().write_text(new_ev, encoding="utf-8")

    archive_file.unlink()
    return f"{archive_file.name} → evidence-log.md"


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


def _format_explain_report(explain):
    """FIX-301: render the auditable dry-run explanation as text.

    For each category (tasks/decisions/risks/evidence): the five numbers
    (scanned / structurally parsed / would-archive / retained /
    unknown-structure), the reason distribution over its rows, and — when
    non-empty — the unknown-structure ID list (capped at 10 shown). Generated
    from the SAME per-row records the migration loops collected, so the
    report can never contradict what a real run would do.
    """
    if not explain:
        return ""
    lines = [
        "📋 归档可审计解释（逐类：扫描/结构可解析/满足归档条件/保留/未知结构；"
        "逐条原因由迁移判定路径单源收集）:",
    ]
    vr = explain.get("versions_range")
    if vr:
        lines.append(f"  归档范围: v{vr[0]} ~ v{vr[1]}")
    for cat in ("tasks", "decisions", "risks", "evidence"):
        stats = explain.get(cat)
        if not isinstance(stats, dict):
            continue
        lines.append(
            f"  - {cat}: 扫描 {stats.get('scanned', 0)} | "
            f"结构可解析 {stats.get('parsed', 0)} | "
            f"满足归档条件 {stats.get('would_archive', 0)} | "
            f"保留 {stats.get('retained', 0)} | "
            f"未知结构 {stats.get('unknown_structure', 0)}"
        )
        dist = {}
        for row in stats.get("rows", []):
            dist[row["reason"]] = dist.get(row["reason"], 0) + 1
        if dist:
            rendered = ", ".join(
                f"{reason}={count}" for reason, count in sorted(dist.items())
            )
            lines.append(f"      逐条原因分布: {rendered}")
        unknown_ids = stats.get("unknown_ids") or []
        if unknown_ids:
            shown = ", ".join(unknown_ids[:10])
            extra = ""
            if len(unknown_ids) > 10:
                extra = f"（共 {len(unknown_ids)} 个，仅列前 10）"
            lines.append(f"      未知结构清单: {shown}{extra}")
    return "\n".join(lines)


def _format_auto_summary(result):
    """Format migrate_auto() result as a human-readable summary string.

    Returns summary suitable for bootstrap output stream.
    """
    if result.get("skipped"):
        return f"📦 治理数据归档: 跳过（无可归档数据——{result.get('reason', '')}）"

    vr = result.get("versions_range")
    if vr:
        range_str = f"v{vr[0]} ~ v{vr[1]}（{len(result['versions_archived'])}个版本）"
    else:
        range_str = "未知"

    lines = [
        "📦 治理数据归档完成:",
        f"  - 归档范围: {range_str}",
    ]

    # FIX-385 衔接面: a decision-store authority deferral is never silent.
    deferred = result.get("decision_migration_deferred")
    if deferred:
        lines.append(
            "  - ⚠️ decisions 未迁移（fail-closed）: decision 权威已切换至 "
            f"FEAT-061 JSON store（state={deferred.get('authority_state')!r}）"
            "——decision-log.md 是投影，archive 的 DEC 归档路由由 cutover 票接管"
        )

    task_file = next(
        (f for f in result.get("archive_files_created", []) if f.startswith("archive/tasks/")),
        f"archive/tasks/v{result['versions_range'][0]}~v{result['versions_range'][1]}.md",
    )
    lines.append(f"  - 归档 {result['tasks_archived']} 个 task → {task_file}")

    if result.get("evidence_archived", 0) > 0:
        evidence_file = next(
            (f for f in result.get("archive_files_created", []) if f.startswith("archive/evidence/")),
            f"archive/evidence/v{result['versions_range'][0]}~v{result['versions_range'][1]}.md",
        )
        lines.append(f"  - 归档 {result['evidence_archived']} 条证据 → {evidence_file}")

    # FIX-416: the non-EVD family legs are part of the ALL steady-state
    # pass — the summary must show them or a family-leg migration reads
    # as "0 task, 0 证据" (the 54-vs-28 disclosure gap).
    family_face = ", ".join(
        f"{k}={v}" for k, v in sorted(
            (result.get("row_families_archived") or {}).items())
        if v and k != "EVD"
    )
    if family_face:
        lines.append(f"  - 归档行家族: {family_face}")

    # File size changes
    pt_before = result.get("plan_tracker_before", 0)
    pt_after = result.get("plan_tracker_after", 0)
    if pt_before > 0 and pt_after > 0:
        pt_kb_before = pt_before / 1024
        pt_kb_after = pt_after / 1024
        pt_pct = int((1 - pt_after / pt_before) * 100)
        lines.append(
            f"  - plan-tracker: {pt_kb_before:.0f}KB → {pt_kb_after:.0f}KB (-{pt_pct}%)"
        )

    ev_before = result.get("evidence_log_before", 0)
    ev_after = result.get("evidence_log_after", 0)
    if ev_before > 0 and ev_after > 0:
        ev_kb_before = ev_before / 1024
        ev_kb_after = ev_after / 1024
        ev_pct = int((1 - ev_after / ev_before) * 100)
        lines.append(
            f"  - evidence-log: {ev_kb_before:.0f}KB → {ev_kb_after:.0f}KB (-{ev_pct}%)"
        )

    lines.append(f"  - 索引: archive/index.md（{result['tasks_archived']} 条目）")
    if result.get("dry_run"):
        lines.append("  - 校验: N/A（dry-run——预览模式，不校验归档完整性）")
    else:
        lines.append(
            f"  - 校验: {'PASS' if result.get('verify_pass') else 'FAILED'}"
        )

    return "\n".join(lines)


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


def _build_archive_arg_parser():
    """FIX-417 (moved verbatim from main): the argparse face of the archive
    CLI — every subcommand, its options, and the FIX-416 --row-family
    three-state semantics (explicit --row-family wins; --auto defaults to
    ALL; an explicit version range defaults to EVD)."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="archive",
        description="Governance Data Archive Tool — SYSGAP-030",
    )
    parser.add_argument(
        "--project-root",
        help=(
            "Host project root whose .governance facts should be read. "
            "May also be placed after the subcommand."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # migrate
    migrate_p = subparsers.add_parser("migrate", help="Archive tasks for a version range")
    migrate_p.add_argument("version_start", nargs="?", default=None,
                           help="Start version (e.g. 0.11.0)")
    migrate_p.add_argument("version_end", nargs="?", default=None,
                           help="End version (e.g. 0.24.0)")
    migrate_p.add_argument("--dry-run", action="store_true",
                           help="Report what would be archived without modifying files")
    migrate_p.add_argument("--no-evidence", action="store_true",
                           help="Skip evidence archiving")
    migrate_p.add_argument("--auto", action="store_true",
                           help="Auto-detect version range from plan-tracker roadmap")
    migrate_p.add_argument("--row-family", default=None,
                           choices=sorted(_WRITE_MIGRATION_ROW_FAMILIES) + ["ALL"],
                           help="Governance row family to migrate (FEAT-076: "
                                "all four families are admitted; ALL carries "
                                "EVD+REVIEW+TRIAGE+RECO in one pass — the "
                                "0.93 steady-state M-8 semantics). Default "
                                "(FIX-416): ALL for --auto — Check 27 counts "
                                "all four families, so the hinted command "
                                "must drain them; EVD for an explicit "
                                "version range (0.92 behavior). An explicit "
                                "--row-family always wins.")

    # build-index
    subparsers.add_parser("build-index", help="Rebuild archive/index.md from archive files")

    # rebuild-index (FIX-384 / B-7a): index-loss/corruption recovery entry —
    # rebuild + integrity verification in one step.
    subparsers.add_parser(
        "rebuild-index",
        help="Rebuild archive/index.md from archive files, then verify integrity",
    )

    # verify
    subparsers.add_parser("verify", help="Verify archive integrity")

    # rollback
    subparsers.add_parser("rollback", help="Rollback the most recent migration")

    # migrate-big-table (FIX-385 / B-7b): batched resumable migration of a
    # row-heavy governance table into the archive — journal + batch cursor +
    # crash-safe resume (FEAT-060/061 pattern).
    p = subparsers.add_parser(
        "migrate-big-table",
        help="Batched RESUMABLE migration of a row-heavy governance table "
             "(evidence) into the archive (FIX-385 B-7b)",
    )
    p.add_argument("table", choices=["evidence"],
                   help="Big table to migrate (evidence-log)")
    p.add_argument("version_start", help="Start version (e.g. 0.60.0)")
    p.add_argument("version_end", help="End version (e.g. 0.61.0)")
    p.add_argument("--batch-size", type=int,
                   default=BIG_TABLE_MIGRATION_BATCH_SIZE,
                   help="Rows per staged batch (default: %(default)s)")
    p.add_argument("--dry-run", action="store_true",
                   help="Report what would migrate; zero writes")
    p.add_argument("--row-family", default="EVD",
                   choices=sorted(_WRITE_MIGRATION_ROW_FAMILIES),
                   help="Governance row family for this resumable leg "
                        "(FEAT-076: all four admitted; one family per "
                        "invocation — each leg carries its own journal)")

    # scan-families (FEAT-075 / DEC-278 单元二): READ-ONLY four-family
    # dry-run scan (EVD/REVIEW/RECO/TRIAGE) — reuses unit one's
    # classification semantics; zero writes; per-line report saveable as
    # TSV (--output) / full JSON (--report-json); never writes inside
    # .governance.
    scan_p = subparsers.add_parser(
        "scan-families",
        help="READ-ONLY dry-run scan of the four governance row families "
             "(EVD/REVIEW/RECO/TRIAGE) under unit one's six-condition "
             "classification (FEAT-075 / DEC-278 单元二) — zero writes",
    )
    scan_p.add_argument("version_start", help="Retention-window start (e.g. 0.1.0)")
    scan_p.add_argument("version_end", help="Retention-window end (e.g. 0.91.0)")
    scan_p.add_argument("--family", action="append", metavar="FAM",
                        choices=list(_SCAN_ROW_FAMILIES),
                        help="Restrict to one family (repeatable; "
                             "default: all four)")
    scan_p.add_argument("--output", default=None,
                        help="Write the per-line diffable TSV report here "
                             "(refused inside .governance)")
    scan_p.add_argument("--report-json", default=None,
                        help="Write the full JSON report here (refused "
                             "inside .governance)")
    return parser, migrate_p


def _cli_cmd_migrate(args, migrate_parser):
    """FIX-417 (moved verbatim from main): the migrate subcommand — FIX-416
    row-family three-state resolution, execution, and result printing."""
    try:
        row_family_arg = getattr(args, "row_family", None)
        if row_family_arg is None:
            # FIX-416: --auto defaults to the four-family ALL pass so
            # the command Check 27 hints ("Run archive.py migrate
            # --auto") can actually drain EVERY family the check counts
            # under its ALL caliber — the 0.92-era EVD-only default left
            # REVIEW/TRIAGE/RECO candidates hot forever, a perpetual
            # check-archive-integrity red. An explicit version range
            # keeps the 0.92 EVD default; an explicit --row-family
            # always wins.
            row_family_arg = "ALL" if args.auto else "EVD"
        # "ALL" resolves inside migrate_auto / migrate_by_version (the
        # choke-point guard admits single families only — the old CLI
        # dispatch passed "ALL" straight in, refusing an explicit
        # `--row-family ALL` that argparse itself offered as a choice).
        if row_family_arg != "ALL":
            _guard_row_family_write_migration(row_family_arg)
        if args.auto:
            result = migrate_auto(dry_run=args.dry_run,
                                  row_family=row_family_arg)
        elif args.version_start and args.version_end:
            result = migrate_by_version(
                args.version_start,
                args.version_end,
                dry_run=args.dry_run,
                migrate_evidence=not args.no_evidence,
                row_family=row_family_arg,
            )
        else:
            print("Error: Either --auto or both version_start and "
                  "version_end must be provided.")
            migrate_parser.print_usage()
            sys.exit(1)
    except BigTableMigrationError as exc:
        # FEAT-075: the write-boundary refusal is loud, structured, and
        # non-zero-exit (never a silent no-op).
        print(f"  Migration REFUSED: {exc.payload.get('code')}")
        print(f"  {exc.payload.get('detail')}")
        sys.exit(1)
    if args.auto:
        print(_format_auto_summary(result))
        # FIX-301: the auditable explanation renders for BOTH the skip
        # path and the action path — a skip with triggers satisfied must
        # never be a black box again.
        explain_report = _format_explain_report(result.get("explain"))
        if explain_report:
            print(explain_report)
        if not result["skipped"] and not result["success"]:
            sys.exit(1)
    else:
        print(f"  Dry-run: {result['dry_run']}")
        print(f"  Tasks archived: {result['tasks_archived']}")
        print(f"  Tasks remaining: {result['tasks_remaining']}")
        print(f"  Evidence archived: {result.get('evidence_archived', 0)}")
        families = result.get("row_families_archived") or {}
        if families:
            print(f"  Row families archived: "
                  f"{', '.join(f'{k}={v}' for k, v in sorted(families.items()))}")
        print(f"  Files created: {result.get('archive_files_created', [])}")
        print(f"  {result['details']}")
        deferred = result.get("decision_migration_deferred")
        if deferred:
            # FIX-385 衔接面: the deferral is surfaced, never hidden.
            print(f"  Decision migration DEFERRED (fail-closed): "
                  f"authority state {deferred.get('authority_state')!r} "
                  f"— store-backed DEC route is the cutover ticket's "
                  f"obligation")
        if not result["success"]:
            sys.exit(1)


def _cli_cmd_migrate_big_table(args):
    """FIX-417 (moved verbatim from main): the migrate-big-table
    subcommand (FIX-385 B-7b resumable leg)."""
    try:
        result = migrate_evidence_resumable(
            args.version_start, args.version_end,
            batch_size=args.batch_size, dry_run=args.dry_run,
            row_family=getattr(args, "row_family", "EVD"))
    except BigTableMigrationError as exc:
        # FIX-385: refusals are loud, structured, and non-zero-exit.
        print(f"  Migration REFUSED: {exc.payload.get('code')}")
        print(f"  {exc.payload.get('detail')}")
        sys.exit(1)
    print(f"  Dry-run: {result.get('dry_run', False)}")
    print(f"  Row family: {getattr(args, 'row_family', 'EVD')}")
    print(f"  Migrated rows: {result.get('migrated', 0)}")
    print(f"  Batches: {result.get('batches_total', 0)} "
          f"(batch_size={result.get('batch_size')})")
    print(f"  Resumed: {result.get('resumed', False)}")
    if result.get("archive_file"):
        print(f"  Archive file: {result['archive_file']}")
    if result.get("journal_path"):
        print(f"  Journal: {result['journal_path']}")
    print(f"  Decision authority state: "
          f"{result.get('decision_authority_state')}")
    if not result.get("success"):
        sys.exit(1)


def _cli_cmd_scan_families(args):
    """FIX-417 (moved verbatim from main): the scan-families read-only
    subcommand (FEAT-075). The refusal for output paths under .governance
    is loud + non-zero."""
    try:
        families = tuple(args.family) if args.family else None
        report = scan_row_families(args.version_start, args.version_end,
                                   families=families)
        if args.output or args.report_json:
            write_family_scan_outputs(report, tsv_path=args.output,
                                      json_path=args.report_json)
    except BigTableMigrationError as exc:
        print(f"  Scan REFUSED: {exc.payload.get('code')}")
        print(f"  {exc.payload.get('detail')}")
        sys.exit(1)
    anchors = report["anchors"]
    print("  Row-family dry-run (read-only; zero writes)")
    print(f"  Window: [{report['window']['start']}, "
          f"{report['window']['end']}]")
    print(f"  Anchors: commit={anchors['git_commit']} "
          f"evidence-log={anchors['evidence_log_bytes']:,} B "
          f"sha256={anchors['evidence_log_sha256'][:12]}…")
    print(format_family_scan_summary(report))
    if args.output:
        print(f"  Per-line TSV report: {args.output}")


def _cli_cmd_build_index(args):
    """FIX-417 (moved verbatim from main): the build-index subcommand."""
    result = build_index()
    print(f"  Status: {result['status']}")
    print(f"  Task entries: {result['task_entries']}")
    print(f"  Evidence entries: {result['evidence_entries']}")
    print(f"  Decision entries: {result['decision_entries']}")
    print(f"  Risk entries: {result['risk_entries']}")


def _cli_cmd_rebuild_index(args):
    """FIX-417 (moved verbatim from main): the rebuild-index subcommand
    (FIX-384 B-7a recovery entry)."""
    result = rebuild_index()
    print(
        f"  Status: {'rebuilt' if result['changed'] else 'unchanged (idempotent no-op equivalent)'}"
    )
    print(f"  Index existed before: {result['index_existed']}")
    print(f"  Task entries: {result['task_entries']}")
    print(f"  Evidence entries: {result['evidence_entries']}")
    print(f"  Decision entries: {result['decision_entries']}")
    print(f"  Risk entries: {result['risk_entries']}")
    damaged = result.get("damaged_files", [])
    if damaged:
        print(f"  Damaged archive files ({len(damaged)}):")
        for d in damaged:
            print(f"    - {d['file']}: {d['kind']} ({d['detail']})")
    print(f"  Integrity: {'PASS' if result['verify_pass'] else 'FAILED'}")
    for issue in result["verify_issues"]:
        print(f"    - {issue}")
    if not result["verify_pass"]:
        sys.exit(1)


def _cli_cmd_verify(args):
    """FIX-417 (moved verbatim from main): the verify subcommand."""
    result = verify_archive_integrity()
    print(f"  Pass: {result['pass']}")
    print(f"  Total archived tasks: {result['total_archived_tasks']}")
    print(f"  Total index entries: {result['total_index_entries']}")
    if result["issues"]:
        print(f"  Issues ({len(result['issues'])}):")
        for issue in result["issues"]:
            print(f"    - {issue}")
    if not result["pass"]:
        sys.exit(1)


def _cli_cmd_rollback(args):
    """FIX-417 (moved verbatim from main): the rollback subcommand."""
    result = rollback_last_migration()
    print(f"  Success: {result['success']}")
    print(f"  Rolled back: {result['rolled_back_file']}")
    print(f"  {result['details']}")
    if not result["success"]:
        sys.exit(1)


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

    if args.command == "migrate":
        _cli_cmd_migrate(args, migrate_parser)
    elif args.command == "migrate-big-table":
        _cli_cmd_migrate_big_table(args)
    elif args.command == "scan-families":
        _cli_cmd_scan_families(args)
    elif args.command == "build-index":
        _cli_cmd_build_index(args)
    elif args.command == "rebuild-index":
        _cli_cmd_rebuild_index(args)
    elif args.command == "verify":
        _cli_cmd_verify(args)
    elif args.command == "rollback":
        _cli_cmd_rollback(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()