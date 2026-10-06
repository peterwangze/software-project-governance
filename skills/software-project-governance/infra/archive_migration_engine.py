#!/usr/bin/env python3
"""
Resumable big-table migration engine + four-family scan face for
archive.py — FIX-435 minimal cohesive split of the 28n module_size debt.

Domain (迁移机制层): the FIX-385 (B-7b) journal → staged-batches → commit
pipeline with FEAT-060/061 crash-recovery semantics, the FEAT-075 read-only
four-family scanner and its TSV/JSON report writers, the archive-file
format writers (header/body/incremental naming), the write-boundary guard,
and the decision-store authority seam. Sibling of archive_parsing /
archive_indexing (FIX-417) and archive_verdicts / archive_entity_migration /
archive_cli (FIX-435).

Seam discipline (FIX-435) — this module is self-contained pure machinery
EXCEPT that its entry points take a ``host`` argument: the archive.py entry
module's live namespace dict (``globals()`` of the loaded instance). Every
ROOT-bound lookup (``host["_evidence_log"]()``, ``host["_archive_dir"]()``,
``host["ROOT"]`` …) and every test-patchable primitive
(``host["_migration_write_batch"]``, ``host["_migration_write_journal"]``,
``host["_atomic_write_text"]``, ``host["_decision_authority_state"]``) is
resolved through ``host`` AT CALL TIME, so:

  * ``patch.object(archive, "ROOT"/"_atomic_write_text"/...)`` (the crash-
    injection / concurrent-cutover tests) intercepts exactly as before the
    split — the re-exported names are plain module attributes of archive.py,
    and the engine reads them through the live dict;
  * the isolated spec_from_file_location load
    (verify_workflow._load_archive_module) gets its own instance-consistent
    namespace (``globals()`` of THAT instance), so rebinding
    ``module.ROOT`` reaches the engine exactly as it reached the original
    monolith's module globals.

Host-patch coverage is exact, not blanket: only pipeline call sites that
resolve ``_atomic_write_text`` through ``host`` (archive write, hot
rewrite) honor ``patch.object(archive, "_atomic_write_text", ...)``; the
journal/batch writers' EMBEDDED atomic write is engine-local and is
covered only when the journal/batch writer itself is the patched name.
"""

import contextlib
import json
import os
import subprocess
import tempfile
from datetime import date, datetime
from pathlib import Path

from archive_parsing import (
    _make_ref_verdict,
    _row_family_archive_table_header,
)
from archive_indexing import _make_archive_filename
from archive_verdicts import (
    _classify_evidence_rows_impl,
    _classify_family_rows_impl,
    _evidence_classification_context_digest,
    _sha256_text,
)

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


# ── Archive file format writers (FIX-435 moved verbatim) ────────

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

def _make_incremental_archive_filename_impl(archive_subdir, version_start,
                                           version_end, category="tasks"):
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

def _next_evidence_archive_filename_impl(evidence_subdir, version_start,
                                        version_end):
    """FIX-385: the commit's archive target under the incremental-* naming
    discipline (reuse of _make_incremental_archive_filename for the
    category-prefixed evidence family) — a commit never overwrites foreign
    archive content."""
    return _make_incremental_archive_filename_impl(
        evidence_subdir, version_start, version_end, category="evidence")

def _next_family_archive_filename_impl(evidence_subdir, next_evd_filename,
                                      version_start, version_end, row_family):
    """FEAT-076: the commit's archive target for one family under
    archive/evidence/ — ``evidence-v{range}.md`` for EVD (FIX-385 naming
    discipline preserved via _next_evidence_archive_filename) and
    ``evidence-{family}-v{range}.md`` for the unlocked families, with the
    same never-overwrite-foreign-content incremental suffix discipline."""
    if row_family == "EVD":
        return next_evd_filename(version_start, version_end)
    category = f"evidence-{row_family.lower()}"
    subdir = evidence_subdir
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

def _decision_authority_state_impl(gov_dir):
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
            state = _decision_repository.load_authority(gov_dir).get("state")
            return state if state else "unreadable"
        except Exception:
            return "unreadable"
    marker = gov_dir / _DECISION_AUTHORITY_MARKER_NAME
    return "MD_ACTIVE" if not marker.exists() else "unreadable"

def _migration_state_dir_impl(archive_dir, category, version_start,
                              version_end):
    """Runtime migration state dir (same artifact class as
    .decision-migration/): under archive/, carries only .json files so
    build_index / verify_archive_integrity / _get_existing_archive_files
    never see it."""
    return archive_dir / _BIG_TABLE_MIGRATION_DIRNAME / (
        f"{category}-v{version_start}~v{version_end}")


def _migration_journal_path_impl(state_dir):
    return state_dir / "journal.json"

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

def scan_row_families_impl(version_start, version_end, *, families=None,
                           task_versions=None, context=None, content=None,
                           plan_tracker_content=None, host):
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
    elog = host["_evidence_log"]()
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
        context = host["_build_classification_context"](plan_tracker_content)
    if plan_tracker_content is None:
        try:
            # Byte-faithful read (read_text's universal-newline translation
            # would hash CRLF files differently from their on-disk bytes).
            plan_tracker_content = (
                host["_plan_tracker"]().read_bytes().decode("utf-8"))
        except OSError:
            plan_tracker_content = ""
    if task_versions is None:
        task_versions = host["_evidence_task_versions_standalone"]()

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
            evd_records = _classify_evidence_rows_impl(
                content, task_versions, version_start, version_end,
                context=context,
                q6_fallback=host["_q6_date_window_fallback"])
            family_rows = []
            for r in evd_records:
                family_rows.append({
                    "family": "EVD", "id": r["id"], "line_idx": r["line_idx"],
                    "bytes": line_bytes[r["line_idx"]], "migrate": r["migrate"],
                    "version": r["version"], "reason": r["reason"],
                    "detail": r["detail"], "ref_types": dict(r["ref_types"]),
                })
        else:
            family_rows = _classify_family_rows_impl(
                family, lines, line_bytes, task_versions,
                version_start, version_end,
                _make_ref_verdict(task_versions, context),
                host["_q6_date_window_fallback"])
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
            "git_commit": _scan_git_commit_anchor(host["ROOT"]),
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

def write_family_scan_outputs_impl(gov_dir, report, tsv_path=None,
                                   json_path=None):
    """FEAT-075: save the per-line dry-run report (可落盘/可 diff — M-0
    prerequisite 1). Output paths under the .governance directory are
    REFUSED: the dry-run contract is zero governance-data writes."""
    guard_dir = gov_dir.resolve()
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

def _evidence_finalized_world(journal, input_digest, journal_path, dry_run,
                              host):
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
                "decision_authority_state": host["_decision_authority_state"]()}
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
                           classification_context, host):
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
                 "decision_authority_state": host["_decision_authority_state"]()}
        return doc, candidates, batches_total, batch_size, early
    return doc, candidates, batches_total, batch_size, None


def _evidence_fresh_plan(content, *, row_family, evidence_task_versions,
                         classification_context, version_start, version_end,
                         batch_size, dry_run, state_dir, batches_dir,
                         journal_path, journal_category, input_digest,
                         host):
    """FIX-417 pipeline stage: fresh plan (classify, pin the world, journal
    phase=intent).

    Returns (doc, candidates, batches_total, early_result); early_result is
    non-None for the fresh dry-run report and the no-candidates skip.
    """
    # ── fresh plan ──
    records = host["_classify_rows_for_family"](
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
                 "decision_authority_state": host["_decision_authority_state"]()}
        return None, candidates, batches_total, early
    if not candidates:
        early = {"success": True, "dry_run": False, "migrated": 0,
                 "batches_total": 0, "batch_size": batch_size,
                 "resumed": False,
                 "skipped": "归档范围内无可迁移 evidence 行",
                 "journal_path": None, "archive_file": None,
                 "decision_authority_state": host["_decision_authority_state"]()}
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
    host["_migration_write_journal"](journal_path, doc)
    return doc, candidates, batches_total, None


def _evidence_stage_batches(doc, *, journal_path, batches_dir, candidates,
                            batches_total, batch_size, resumed, host):
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
        host["_migration_write_batch"](batches_dir, k,
                                      [c["line"] for c in chunk])
        doc["batches_staged"] = k + 1
        host["_migration_write_journal"](journal_path, doc)
    doc["phase"] = "staged"
    doc["batches_staged"] = batches_total
    host["_migration_write_journal"](journal_path, doc)


def _evidence_compose_commit(doc, *, content, lines, candidates,
                             batches_total, resumed, input_digest,
                             version_start, version_end, journal_category,
                             row_family, batches_dir, journal_path, host):
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
        archive_path = (host["_archive_dir"]() / "evidence"
                        / archive_relname)
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
            archive_relname = host["_next_family_archive_filename"](
                version_start, version_end, row_family)
        archive_path = (host["_archive_dir"]() / "evidence"
                        / archive_relname)
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
        host["_migration_write_journal"](journal_path, doc)
        hot_done = False
    return archive_path, archive_text, new_hot_text, hot_done, \
        archive_relname, archived_rows


def _evidence_apply_commit(doc, *, journal_path, elog, archive_path,
                           archive_text, new_hot_text, hot_done, host):
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
            host["_atomic_write_text"](archive_path, archive_text)
        if not hot_done:
            host["_atomic_write_text"](elog, new_hot_text)
        doc["phase"] = "finalized"
        host["_migration_write_journal"](journal_path, doc)


def migrate_evidence_resumable_impl(version_start, version_end, *,
                                    batch_size=BIG_TABLE_MIGRATION_BATCH_SIZE,
                                    dry_run=False, task_versions=None,
                                    row_family="EVD", host):
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
    elog = host["_evidence_log"]()
    if not elog.exists():
        return {"success": True, "dry_run": bool(dry_run), "migrated": 0,
                "batches_total": 0, "batch_size": batch_size, "resumed": False,
                "skipped": "evidence-log.md 不存在", "journal_path": None,
                "archive_file": None,
                "decision_authority_state": host["_decision_authority_state"]()}
    if task_versions is None:
        evidence_task_versions = host["_evidence_task_versions_standalone"]()
    else:
        evidence_task_versions = dict(task_versions)
    # FEAT-074: the entity-registration context is built ONCE and pinned by
    # digest — the plan and every resume judge the same world.
    classification_context = host["_build_classification_context"]()

    journal_path = host["_migration_journal_path"](journal_category,
                                                version_start, version_end)
    state_dir = journal_path.parent
    batches_dir = state_dir / "batches"

    content = elog.read_text(encoding="utf-8")
    lines = content.split("\n")
    input_digest = _sha256_text(content)

    journal = _migration_load_journal(journal_path)

    # ── finalized journal: judge the world ──
    if journal is not None and journal.get("phase") == "finalized":
        early = _evidence_finalized_world(journal, input_digest,
                                          journal_path, dry_run, host)
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
                classification_context=classification_context, host=host)
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
            journal_category=journal_category, input_digest=input_digest,
            host=host)
        if early is not None:
            return early

    _evidence_stage_batches(doc, journal_path=journal_path,
                            batches_dir=batches_dir, candidates=candidates,
                            batches_total=batches_total,
                            batch_size=batch_size, resumed=resumed,
                            host=host)

    archive_path, archive_text, new_hot_text, hot_done, archive_relname, \
        archived_rows = _evidence_compose_commit(
            doc, content=content, lines=lines, candidates=candidates,
            batches_total=batches_total, resumed=resumed,
            input_digest=input_digest, version_start=version_start,
            version_end=version_end, journal_category=journal_category,
            row_family=row_family, batches_dir=batches_dir,
            journal_path=journal_path, host=host)

    _evidence_apply_commit(doc, journal_path=journal_path, elog=elog,
                           archive_path=archive_path,
                           archive_text=archive_text,
                           new_hot_text=new_hot_text, hot_done=hot_done,
                           host=host)

    return {"success": True, "dry_run": False, "migrated": len(archived_rows),
            "batches_total": batches_total, "batch_size": batch_size,
            "resumed": resumed,
            "journal_path": str(journal_path),
            "archive_file": f"archive/evidence/{archive_relname}",
            "hot_after_digest": doc["commit"]["hot_after_digest"],
            "decision_authority_state": host["_decision_authority_state"]()}
