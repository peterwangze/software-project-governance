#!/usr/bin/env python3
"""
Archive-read / index / integrity support for archive.py — FIX-417 minimal
cohesive split of the 28o architecture-health findings.

Sibling of archive_parsing.py (the judgment face, base layer): this module
carries everything that READS archive files or renders/verifies the index —

  * archive-file entry extraction (_extract_* — single-source calibers
    shared by build_index and verify_archive_integrity Check 3,
    REVIEW-FIX-384-R0 P1-1);
  * damage labeling (_archive_file_damage / _damage_kind_label /
    _damage_description — FIX-384 rebuild-tolerant face);
  * index collection + Markdown rendering (collect_*_index_entries /
    render_index_markdown — FIX-176 unstructured registration, FEAT-076
    family sections);
  * integrity counting (parse_index_section /
    count_archive_file_entries / count_index_section_entries — FIX-163
    per-category symmetric calibers);
  * the migrate_by_version pure compose helpers that key on archive file
    naming/format (parse_archive_version_range / make_archive_filename
    family).

Every function is a PURE function of its inputs — no ROOT / PLUGIN_ROOT
seam, no test patch surface (see archive_parsing.py's module docstring for
the FIX-187/FIX-242 dual-root proof). Shared judgment primitives
(_parse_task_status, _parse_version_from_title, the row-family id
regexes/constants) are imported ONE-WAY from archive_parsing — the base
layer never imports this module, so no import cycle exists.

archive.py re-imports every name below, so ``archive.<name>`` keeps
working (tests address these helpers directly).
"""

import re

from archive_parsing import (
    _EVD_ID_SHAPE_RE,
    _ROW_FAMILY_ID_RES,
    _ROW_FAMILY_LINE_PREFIXES,
    _parse_task_status,
    _parse_version_from_title,
)

def _make_archive_filename(version_start, version_end, category="tasks"):
    """Generate archive file name: v{start}~v{end}.md"""
    return f"v{version_start}~v{version_end}.md"

def _parse_archive_version_range(filename):
    """Parse archive filename into (version_start, version_end).

    Supports both base archive files (vX~vY.md) and independent incremental
    archive files (vX~vY-incremental-YYYYMMDD-N.md). FIX-164 also supports
    category-prefixed names (evidence-vX-Y.md, decisions-vX-Y.md,
    risks-vX-Y.md) produced by the per-category migration functions.
    """
    match = re.match(
        r"^v(\d+\.\d+\.\d+)~v(\d+\.\d+\.\d+)"
        r"(?:-incremental-\d{8}-\d+)?\.md$",
        filename,
    )
    if match:
        return match.group(1), match.group(2)
    # FIX-164: category-prefixed names like evidence-v0.10.0-0.10.0.md
    # FIX-385: the category-prefixed family also admits the incremental
    # suffix (evidence-vX-Y-incremental-YYYYMMDD-N.md) so index/rollback
    # semantics stay coherent for resumable-path archive files.
    # FEAT-076: the two-segment family form (evidence-review-vX-Y.md …)
    # produced by the unlocked three-family write migration.
    m2 = re.match(
        r"^[a-z]+(?:-[a-z]+)*-v(\d+\.\d+\.\d+)-(\d+\.\d+\.\d+)"
        r"(?:-incremental-\d{8}-\d+)?\.md$",
        filename,
    )
    if m2:
        return m2.group(1), m2.group(2)
    return None

def _entry_version_for_archive(line, task_versions):
    """FIX-162: extract the version to classify a decision/risk row under.

    Decision-log and risk-log rows reference task IDs in their cells. We pick the
    first referenced task that is in task_versions (task_id -> version dict) to
    determine the version. Returns a version string, or None if no related task
    is being archived (the row is not ready to migrate).

    FIX-312 scope note: the DECISION path no longer uses this helper — the
    whole-line any-hit semantics mis-attributed NEW decisions that merely
    REFERENCED historical archived tasks (live case: DEC-187 → FEAT-010@0.77.0
    while its governing FIX-310/307/308/309 were still hot; R2 F-R2-01 family).
    Decisions now use :func:`_decision_archive_version` (governing 关联任务
    column + all-refs-archived gate + newest-version attribution). The RISK
    path keeps this helper (risks carry the additional _is_risk_closed gate).
    """
    for m in re.finditer(r"\b([A-Z]+-\d+)\b", line):
        tid = m.group(1)
        if tid in task_versions:
            return task_versions[tid]
    return None

def _version_from_archive_filename(filepath):
    """FIX-171 (AUDIT-126 factor C): best-effort parse of a version label from
    an archive file's NAME, used as a fallback when the file has no in-file
    `### vX.Y.Z` title header.

    Legacy archive files in this repo fall into three naming families:
      - version-scoped single-version: `legacy-v0.10.0.md` → "0.10.0"
      - version-scoped RANGE:          `v0.1.0~v0.31.0.md` → "0.1.0" (the START
        / lower bound — see note below)
      - date-named (NOT version-scoped): `completed-tasks-YYYY-MM-DD_YYYY-MM-DD.md`,
        `narrative-...md`, `recent-completed-...md` → None (these legitimately
        span many versions and have no single version label; current_version
        falls through to "unknown", preserving prior behavior).

    Range-file note: `task_versions` maps a single version per task ID. For a
    range file we conservatively label every task with the range START (lower
    bound). This is safe because the downstream `_version_in_range` membership
    test compares the labeled version against the migration range — and the
    range start is always inside `[start, end]` for any range that includes the
    file's own span. Labeling with the lower bound (rather than, say, "unknown")
    is strictly an improvement: it lets historical tasks from range files
    participate in the task_versions lookup instead of being silently dropped
    (AUDIT-126 found 66 such tasks dropped as version="unknown").

    Args:
        filepath: a pathlib.Path to the archive file.

    Returns:
        A version string like "0.10.0", or None if the filename is not
        version-scoped (date-named or unrecognized).
    """
    name = filepath.name
    # Single-version legacy file: legacy-v0.10.0.md → "0.10.0"
    m = re.match(r"^legacy-v(\d+\.\d+\.\d+)\.md$", name)
    if m:
        return m.group(1)
    # Range file: v0.1.0~v0.31.0.md → start "0.1.0" (lower bound; see docstring).
    # Also matches single-version range v0.10.0~v0.10.0.md → "0.10.0".
    m = re.match(r"^v(\d+\.\d+\.\d+)~v(\d+\.\d+\.\d+)(?:-incremental-\d{8}-\d+)?\.md$", name)
    if m:
        return m.group(1)
    return None

def _extract_tasks_from_archive_file(filepath):
    """Extract task IDs and statuses from an archive file.

    Returns list of (task_id, status, version_str) tuples.

    FIX-171 (AUDIT-126 factor C): when a file has no in-file `### vX.Y.Z`
    title header (legacy files like legacy-v0.10.0.md), the version is now
    derived from the FILENAME via _version_from_archive_filename as a fallback,
    instead of unconditionally defaulting to "unknown". This recovers ~66
    historical tasks that were previously dropped from the task_versions lookup
    (and thus blocked decision/risk/evidence migration referencing them).
    """
    if not filepath.exists():
        return []
    # FIX-384: errors="replace" salvages the readable lines of a partially
    # corrupted archive file instead of crashing on invalid UTF-8. Extracted
    # IDs still have to match strict regexes, so replacement characters can
    # never fabricate a phantom entry.
    content = filepath.read_text(encoding="utf-8", errors="replace")
    results = []
    current_version = None
    # FIX-171: pre-compute the filename-derived version once. It is only used
    # when an in-file `### vX.Y.Z` header has NOT been seen (current_version is
    # None at the row). In-file headers always take precedence.
    filename_version = _version_from_archive_filename(filepath)

    for line in content.split("\n"):
        # Detect version section headers
        v, _ = _parse_version_from_title(line)
        if v:
            current_version = v
            continue

        # Parse task table rows
        stripped = line.strip()
        # FIX-158: support two table formats:
        #   (a) legacy 10-col with ID in column 1: "| TASKID-NNN | desc | ..."
        #   (b) 7-col priority table with ID in column 2: "| **P0** | TASKID-NNN | ..."
        # Try col-1 first (legacy), then col-2 (priority table).
        # FIX-301: the ID cell itself may carry markdown bold ("**REL-071**")
        # in real hot rows — the migration parser strips it, so the archive
        # extraction must tolerate it too, or already_archived/index lookups
        # go blind for those IDs (found by the temp-copy conservation check:
        # 88 rows migrated, only 87 extracted).
        m = re.match(r"\|\s*(?:\*{0,2})([A-Z]+-\d+)(?:\*{0,2})\s*\|", stripped)
        col_offset = 0
        if not m:
            m = re.match(
                r"\|\s*\*{0,2}[Pp][0-9]\*{0,2}\s*\|\s*(?:\*{0,2})([A-Z]+-\d+)(?:\*{0,2})\s*\|",
                stripped,
            )
            col_offset = 1  # status column shifts by 1 when ID is in col 2
        if m:
            task_id = m.group(1)
            # For the 7-col format, status is the last data column; for 10-col
            # legacy it was parts[10]. _parse_task_status defaults to last column
            # which works for both 7-col archive rows. Pass explicit col only if
            # we detect the legacy 10-col layout (>= 10 data cells).
            parts = [p.strip() for p in stripped.split("|")]
            data_cells = parts[1:-1] if len(parts) >= 2 else parts
            if len(data_cells) >= 10:
                status = _parse_task_status(stripped, status_col=9)
            else:
                status = _parse_task_status(stripped)
            # version may be in the 目标版本 column for 7-col format
            version = current_version or filename_version or "unknown"
            if col_offset and len(data_cells) >= 5:
                tv = re.sub(r"[`*]", "", data_cells[4]).strip()
                if re.match(r"^\d+\.\d+\.\d+$", tv):
                    version = tv
            results.append((task_id, status, version))

    return results

def _extract_evidence_from_archive_file(filepath):
    """Extract evidence IDs and associated task IDs from an archive file.

    Returns list of (evidence_id, task_ids_str) tuples.
    """
    if not filepath.exists():
        return []
    # FIX-384: damage-tolerant read (see _extract_tasks_from_archive_file).
    content = filepath.read_text(encoding="utf-8", errors="replace")
    results = []

    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("| EVD-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            evd_id = parts[1]
            task_ids = parts[2]
            # FIX-301: compound IDs (EVD-FIX-247) are extracted too — the
            # shared shape regex keeps the migration side and this index
            # source in lockstep (plain `EVD-\d+` made compound rows
            # invisible to the index while they sat in archive files).
            if evd_id and _EVD_ID_SHAPE_RE.match(evd_id):
                results.append((evd_id, task_ids))

    return results

# FEAT-076: the three unlocked row families' index-extraction single
# source — the same prefix+shape discipline as the EVD extractor above,
# keyed on _ROW_FAMILY_ID_RES so a damaged id shape never enters the
# index (it stays countable via the entry-less narrative registration
# path instead, FIX-384 semantics).
def _extract_row_families_from_archive_file(filepath):
    """Extract REVIEW/TRIAGE/RECO rows from an archive evidence file.

    Returns list of {"family", "id", "task_ids"} dicts (empty when the
    file is unreadable; damage-tolerant read — same as the EVD extractor).
    """
    if not filepath.exists():
        return []
    content = filepath.read_text(encoding="utf-8", errors="replace")
    results = []
    for line in content.split("\n"):
        stripped = line.strip()
        for family, prefix in _ROW_FAMILY_LINE_PREFIXES.items():
            if family == "EVD":
                continue
            if not stripped.startswith(prefix):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                row_id = parts[1]
                match = _ROW_FAMILY_ID_RES[family].match(row_id) \
                    if row_id else None
                if match is not None:
                    results.append({
                        "family": family,
                        "id": row_id,
                        "task_ids": parts[2],
                    })
            break
    return results

def _extract_decisions_from_archive_file(filepath):
    """Extract decision entries from an archive file — SINGLE SOURCE.

    REVIEW-FIX-384-R0 P1-1: build_index's indexing caliber and
    verify_archive_integrity Check 3's counting caliber previously used two
    DIFFERENT regexes (`##\\s+(DEC-\\d+):` with colon vs `^##\\s+DEC-\\d+`
    without), so a colon-damaged DEC header counted 1 on the verify side and
    0 on the index side forever — Check 3 could never pass and the verify
    message "Run build_index() to rebuild" became a dead loop. Both sides now
    call THIS function, so the calibers can never drift again. The canonical
    caliber is the strict one (the format _migrate_decisions writes:
    `## DEC-{n}: {title}`); a damaged header is not indexable and the file is
    handled by the FIX-384 entry-less registration path instead.

    Returns list of {"id", "title"} dicts (empty when unreadable; damage-
    tolerant read — see _extract_tasks_from_archive_file).
    """
    if not filepath.exists():
        return []
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return [
        {"id": m.group(1), "title": m.group(2).strip()}
        for m in re.finditer(r"##\s+(DEC-\d+):\s*(.*)", content)
    ]

def _extract_risks_from_archive_file(filepath):
    """Extract risk entries from an archive file — SINGLE SOURCE.

    REVIEW-FIX-384-R0 P1-1: the same caliber-split defect as decisions —
    build_index required ≥4 pipe cells (id + description indexable) while
    verify Check 3 counted any `| RISK-n`-prefixed line, so a truncated risk
    row made Check 3 permanently FAIL after a rebuild. Both sides now call
    THIS function; the canonical caliber is build_index's (a row is indexable
    only with id + description cells), damaged rows fall to the entry-less
    registration path.

    Returns list of {"id", "description"} dicts (empty when unreadable;
    damage-tolerant read — see _extract_tasks_from_archive_file).
    """
    if not filepath.exists():
        return []
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    results = []
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("| RISK-"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 4:
            risk_id = parts[1]
            desc = parts[2]
            if risk_id and re.match(r"RISK-\d+", risk_id):
                results.append({"id": risk_id, "description": desc})
    return results

# Filename prefixes that mark a task-archive file as non-structured (its body
# is free narrative prose, not a task table). Listed in the order they should
# be checked; the first match wins for kind labeling.
_UNSTRUCTURED_ARCHIVE_PREFIXES = (
    ("narrative-", "叙述段"),
    ("recent-completed-", "滚动指针"),
)

def _is_unstructured_archive_file(filepath):
    """Return True if a task-archive file is a non-structured (free-prose) file.

    Used by build_index() to decide whether a task-archive file that yielded no
    extractable task rows should be registered in the 非结构化归档 index section
    rather than dropped (which would make it an orphan for verify Check 2).
    Detection is filename-prefix based so it is robust to content drift.
    """
    name = filepath.name
    return any(name.startswith(prefix) for prefix, _ in _UNSTRUCTURED_ARCHIVE_PREFIXES)

def _unstructured_archive_kind(filepath):
    """Return a short Chinese kind label for a non-structured archive file."""
    name = filepath.name
    for prefix, kind in _UNSTRUCTURED_ARCHIVE_PREFIXES:
        if name.startswith(prefix):
            return kind
    return "非结构化"

def _unstructured_archive_description(filepath):
    """Build a short human-readable description for a non-structured archive file.

    Pulls the date range from the filename (e.g. ``2026-04-30_2026-06-27``) and,
    when available, the ``- **归档范围**:**`` or ``- **条目数**:**`` line from the
    file header. Falls back to the title line. Kept defensive: any parse miss
    yields a generic non-empty description so the index row is never blank.
    """
    name = filepath.name
    stem = filepath.stem
    # Date range like "...-2026-04-30_2026-06-27" -> "2026-04-30~2026-06-27"
    m = re.search(r"(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})", stem)
    date_range = f"{m.group(1)}~{m.group(2)}" if m else ""

    scope = ""
    count = ""
    title = ""
    if filepath.exists():
        try:
            # FIX-384: errors="replace" — a damaged narrative file must not
            # crash the index build that is registering it.
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            content = ""
        for line in content.split("\n")[:15]:
            stripped = line.strip()
            if not scope and stripped.startswith("- **归档范围**:"):
                scope = stripped.split(":", 1)[1].strip().lstrip("*").strip()
            elif not count and stripped.startswith("- **条目数**:"):
                count = stripped.split(":", 1)[1].strip().lstrip("*").strip()
            elif not title and stripped.startswith("# "):
                title = stripped[2:].strip()

    parts = []
    if date_range:
        parts.append(date_range)
    body = scope or count or title or "非结构化归档文件"
    parts.append(body)
    return " ".join(parts)

def _archive_file_damage(filepath):
    """FIX-384: classify content-level damage of an archive file (or None).

    Returns None when the file is readable and non-empty, otherwise:
      {"kind": "empty"|"unreadable"|"decode_errors", "detail": str}
        - empty         — 0-byte file
        - unreadable    — OSError while reading (permissions, race, ...)
        - decode_errors — file is not valid UTF-8 (readable parts can still
                          be salvaged via errors="replace" reads)
    """
    try:
        data = filepath.read_bytes()
    except OSError as exc:
        return {"kind": "unreadable", "detail": exc.__class__.__name__}
    if not data:
        return {"kind": "empty", "detail": "0 bytes"}
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return {
            "kind": "decode_errors",
            "detail": f"invalid UTF-8 at byte {exc.start}",
        }
    return None

def _damage_kind_label(damage):
    """FIX-384: short Chinese kind label for an entry-less archive file."""
    if damage is None:
        return "无条目"
    return {
        "empty": "空文件",
        "unreadable": "损坏",
        "decode_errors": "损坏",
    }.get(damage.get("kind"), "损坏")

def _damage_description(damage):
    """FIX-384: human-readable description for an entry-less archive file."""
    if damage is None:
        return "文件可读但未解析出可索引条目（结构未识别）"
    kind_zh = {
        "empty": "空文件（0 字节）",
        "unreadable": "不可读",
        "decode_errors": "UTF-8 解码损坏（可读部分已尽力恢复）",
    }.get(damage.get("kind"), "损坏")
    detail = damage.get("detail", "")
    return f"{kind_zh}：{detail}" if detail else kind_zh

def collect_task_index_entries(files):
    """FIX-417 (moved verbatim from build_index): collect task + narrative
    index entries and damage reports from the archive/tasks/*.md files.

    FIX-176: unstructured task-archive files (narrative-*, recent-
    completed-*, and any future free-prose archive) yield no task-table
    rows, so they would otherwise become orphans that fail
    verify_archive_integrity Check 2 — track them for the dedicated index
    section. FIX-384: empty / unreadable / row-less files are registered
    in the 非结构化归档 section with a damage label instead of crashing
    the rebuild or silently orphaning the file.

    Returns (task_entries, narrative_entries, damaged_files).
    """
    task_entries = []
    narrative_entries = []
    damaged_files = []
    for f in files:
        rel_path = f"archive/tasks/{f.name}"
        damage = _archive_file_damage(f)
        if damage is not None:
            damaged_files.append({"file": rel_path, **damage})
        rows = []
        try:
            rows = _extract_tasks_from_archive_file(f)
        except OSError:
            rows = []  # unreadable → registered below with a damage label
        if rows:
            for task_id, status, version in rows:
                task_entries.append({
                    "id": task_id,
                    "status": status or "?",
                    "version": version,
                    "file": rel_path,
                })
        elif _is_unstructured_archive_file(f):
            # FIX-176: register non-table archive file (e.g. narrative-*) so it
            # is referenced by the index and not flagged as an orphan.
            narrative_entries.append({
                "file": rel_path,
                "kind": _unstructured_archive_kind(f),
                "description": _unstructured_archive_description(f),
            })
        else:
            # FIX-384: no extractable entries and no narrative prefix — an
            # empty / unreadable / structure-unrecognized file. Register it so
            # verify Check 2 does not flag it as an orphan and the rebuild can
            # still reach integrity PASS.
            narrative_entries.append({
                "file": rel_path,
                "kind": _damage_kind_label(damage),
                "description": _damage_description(damage),
            })
    return task_entries, narrative_entries, damaged_files

def collect_evidence_index_entries(files):
    """FIX-417 (moved verbatim from build_index): collect EVD + family row
    index entries and damage reports from archive/evidence/*.md.

    FEAT-076: REVIEW/TRIAGE/RECO rows archived alongside EVD under
    archive/evidence/ get their own index section (row-id → file), the
    same lookup discipline the EVD section provides. FIX-384: entry-less
    evidence archive (empty/unreadable/mangled) is registered instead of
    becoming a verify orphan.

    Returns (evidence_entries, family_entries, narrative_entries,
    damaged_files).
    """
    evidence_entries = []
    family_entries = []
    narrative_entries = []
    damaged_files = []
    for f in files:
        rel_path = f"archive/evidence/{f.name}"
        damage = _archive_file_damage(f)
        if damage is not None:
            damaged_files.append({"file": rel_path, **damage})
        ev_rows = []
        fam_rows = []
        try:
            ev_rows = _extract_evidence_from_archive_file(f)
            fam_rows = _extract_row_families_from_archive_file(f)
        except OSError:
            ev_rows = []
            fam_rows = []
        for evd_id, task_ids in ev_rows:
            evidence_entries.append({
                "id": evd_id,
                "task_ids": task_ids,
                "file": rel_path,
            })
        for row in fam_rows:
            family_entries.append({
                "family": row["family"],
                "id": row["id"],
                "task_ids": row["task_ids"],
                "file": rel_path,
            })
        if not ev_rows and not fam_rows:
            # FIX-384: entry-less evidence archive (empty/unreadable/mangled)
            # is registered instead of becoming a verify orphan.
            narrative_entries.append({
                "file": rel_path,
                "kind": _damage_kind_label(damage),
                "description": _damage_description(damage),
            })
    return evidence_entries, family_entries, narrative_entries, damaged_files

def collect_decision_index_entries(files):
    """FIX-417 (moved verbatim from build_index): collect decision index
    entries and damage reports from archive/decisions/*.md.

    REVIEW-FIX-384-R0 P1-1: single-source extraction shared with verify
    Check 3 so the counting calibers can never drift apart on damaged
    files. FIX-384: register the entry-less decision archive.

    Returns (decision_entries, narrative_entries, damaged_files).
    """
    decision_entries = []
    narrative_entries = []
    damaged_files = []
    for f in files:
        rel_path = f"archive/decisions/{f.name}"
        damage = _archive_file_damage(f)
        if damage is not None:
            damaged_files.append({"file": rel_path, **damage})
        # REVIEW-FIX-384-R0 P1-1: single-source extraction shared with
        # verify Check 3 so the counting calibers can never drift apart on
        # damaged files.
        decs = [
            {
                "id": d["id"],
                "title": d["title"],
                "file": rel_path,
            }
            for d in _extract_decisions_from_archive_file(f)
        ]
        decision_entries.extend(decs)
        if not decs:
            # FIX-384: register the entry-less decision archive.
            narrative_entries.append({
                "file": rel_path,
                "kind": _damage_kind_label(damage),
                "description": _damage_description(damage),
            })
    return decision_entries, narrative_entries, damaged_files

def collect_risk_index_entries(files):
    """FIX-417 (moved verbatim from build_index): collect risk index
    entries and damage reports from archive/risks/*.md.

    P1-1: same single-source caliber as the decision face (indexable =
    id + description cells); truncated rows are handled by the FIX-384
    entry-less registration path on BOTH sides.

    Returns (risk_entries, narrative_entries, damaged_files).
    """
    risk_entries = []
    narrative_entries = []
    damaged_files = []
    for f in files:
        rel_path = f"archive/risks/{f.name}"
        damage = _archive_file_damage(f)
        if damage is not None:
            damaged_files.append({"file": rel_path, **damage})
        # REVIEW-FIX-384-R0 P1-1: single-source extraction shared with
        # verify Check 3 (see _extract_risks_from_archive_file).
        risks = [
            {
                "id": r["id"],
                "description": r["description"],
                "file": rel_path,
            }
            for r in _extract_risks_from_archive_file(f)
        ]
        risk_entries.extend(risks)
        if not risks:
            # FIX-384: register the entry-less risk archive.
            narrative_entries.append({
                "file": rel_path,
                "kind": _damage_kind_label(damage),
                "description": _damage_description(damage),
            })
    return risk_entries, narrative_entries, damaged_files

def render_index_markdown(task_entries, evidence_entries, family_entries,
                          decision_entries, risk_entries, narrative_entries):
    """FIX-417 (moved verbatim from build_index): render the index.md
    content (a pure derivative of the collected entries).

    FIX-176: 非结构化归档小节——登记不含可索引 task/evidence/decision/risk
    行的自由叙述类归档文件（如 narrative-*、recent-completed-* 中无表格的），
    使 verify_archive_integrity 的 Check 2（每个归档文件须被索引引用）能识别它们，
    不再误报 orphan。该小节不参与 Check 3 的分类计数漂移检测。
    """
    index_lines = [
        "# 归档索引",
        "",
        "> 自动生成，记录每个治理条目的归档位置。查询路径：条目 ID → 归档文件。",
        "> 维护方式：归档脚本执行时自动更新。可通过 `build_index()` 重建。",
        "",
        "---",
        "",
        "## Task 索引",
        "",
        "| Task ID | 状态 | 版本 | 归档文件 |",
        "|---------|------|------|---------|",
    ]

    for entry in task_entries:
        index_lines.append(
            f"| {entry['id']} | {entry['status']} | {entry['version']} | {entry['file']} |"
        )

    index_lines.extend([
        "",
        "## Evidence 索引",
        "",
        "| Evidence ID | Task ID | 归档文件 |",
        "|-------------|--------|---------|",
    ])

    for entry in evidence_entries:
        index_lines.append(
            f"| {entry['id']} | {entry['task_ids']} | {entry['file']} |"
        )

    # FEAT-076: the three unlocked row families' lookup section. Rows are
    # preserved verbatim in the archive files; this section maps row id →
    # file so a cold REVIEW/TRIAGE/RECO row stays locatable (the same
    # 引用透明解析 discipline the EVD section provides).
    index_lines.extend([
        "",
        "## 行族索引（REVIEW/TRIAGE/RECO）",
        "",
        "| 行ID | 行族 | 关联任务 | 归档文件 |",
        "|------|------|---------|---------|",
    ])

    for entry in family_entries:
        index_lines.append(
            f"| {entry['id']} | {entry['family']} | {entry['task_ids']} | {entry['file']} |"
        )

    index_lines.extend([
        "",
        "## Decision 索引",
        "",
        "| Decision ID | 标题 | 归档文件 |",
        "|-------------|------|---------|",
    ])

    for entry in decision_entries:
        index_lines.append(
            f"| {entry['id']} | {entry['title']} | {entry['file']} |"
        )

    index_lines.extend([
        "",
        "## Risk 索引",
        "",
        "| Risk ID | 描述 | 归档文件 |",
        "|---------|------|---------|",
    ])

    for entry in risk_entries:
        index_lines.append(
            f"| {entry['id']} | {entry['description']} | {entry['file']} |"
        )

    index_lines.extend([
        "",
        "## 非结构化归档",
        "",
        "> 以下文件是归档目录中不含可索引条目（task/evidence/decision/risk 行）的",
        "> 自由叙述类文件，或内容损坏/空文件/结构未识别的归档（FIX-384），仅在此",
        "> 登记以满足归档完整性（每个归档 .md 须被索引引用）。登记只恢复索引视图，",
        "> 不创造数据。",
        "",
        "| 归档文件 | 类型 | 描述 |",
        "|---------|------|------|",
    ])

    for entry in narrative_entries:
        index_lines.append(
            f"| {entry['file']} | {entry['kind']} | {entry['description']} |"
        )

    index_lines.append("")
    return index_lines

def parse_index_section(content_lines, section_name):
    """FIX-417 (moved verbatim from verify_archive_integrity): extract the
    set of archive-file references from one index.md section's table rows.

    FEAT-076: the 行族索引 section's file column is parts[4] (| 行ID |
    行族 | 关联任务 | 归档文件 |); FIX-176: the 非结构化归档 section's
    file is in column 1 (| 归档文件 | 类型 | 描述 |).
    """
    refs = set()
    in_section = False
    table_started = False

    for line in content_lines:
        if line.strip() == f"## {section_name}":
            in_section = True
            continue
        if in_section and line.strip().startswith("## "):
            in_section = False
            continue
        if not in_section:
            continue
        stripped = line.strip()
        if "|---" in stripped:
            table_started = True
            continue
        if not table_started:
            continue
        if not stripped.startswith("| "):
            continue

        parts = [p.strip() for p in line.split("|")]
        if section_name == "Task 索引":
            if len(parts) >= 5:
                refs.add(parts[4])  # archive file column
        elif section_name == "Evidence 索引":
            if len(parts) >= 4:
                refs.add(parts[3])
        elif section_name == "Decision 索引":
            if len(parts) >= 4:
                refs.add(parts[3])
        elif section_name == "Risk 索引":
            if len(parts) >= 4:
                refs.add(parts[3])
        elif section_name.startswith("行族索引"):
            # FEAT-076: | 行ID | 行族 | 关联任务 | 归档文件 |
            if len(parts) >= 5:
                refs.add(parts[4])
        elif section_name == "非结构化归档":
            # FIX-176: file is in column 1 (| 归档文件 | 类型 | 描述 |)
            if len(parts) >= 2:
                refs.add(parts[1])

    return refs

def count_archive_file_entries(archive_files):
    """FIX-417 (moved verbatim from verify_archive_integrity): count the
    indexable entries in the archive files, per-category.

    FIX-163 (TD-015) + FIX-162 coupling fix: count must be symmetric per
    category (tasks/evidence/decisions/risks) so that migrating
    decisions/risks (FIX-162) does not create a false mismatch. Each
    category's file count is compared against its index count
    independently. REVIEW-FIX-384-R0 P1-1: decisions and risks count via
    the SAME single-source extraction build_index indexes with (the
    previous standalone regex disagreed with build_index's caliber on
    damaged headers, making the post-rebuild Check 3 PASS unreachable).
    """
    file_counts = {"tasks": 0, "evidence": 0, "decisions": 0, "risks": 0,
                   "families": 0}
    for subdir, f in archive_files:
        if subdir == "tasks":
            file_counts["tasks"] += len(_extract_tasks_from_archive_file(f))
        elif subdir == "evidence":
            file_counts["evidence"] += len(_extract_evidence_from_archive_file(f))
            # FEAT-076: the three unlocked families live in the same
            # archive subdir; their rows count in their own category.
            file_counts["families"] += len(
                _extract_row_families_from_archive_file(f))
        elif subdir == "decisions":
            file_counts["decisions"] += len(
                _extract_decisions_from_archive_file(f)
            )
        elif subdir == "risks":
            file_counts["risks"] += len(_extract_risks_from_archive_file(f))
    return file_counts

def count_index_section_entries(index_lines):
    """FIX-417 (moved verbatim from verify_archive_integrity): count the
    ID rows in index.md, per-category.

    FIX-301: multi-segment prefixes (compound evidence IDs like
    EVD-FIX-247) count as ID rows, keeping this counter symmetric with the
    archive-file extraction (_extract_tasks/_extract_evidence admit
    compound EVD shapes).
    """
    index_counts = {"tasks": 0, "evidence": 0, "decisions": 0, "risks": 0,
                    "families": 0}
    current_section = None
    section_map = {
        "Task 索引": "tasks", "任务索引": "tasks",
        "Evidence 索引": "evidence", "证据索引": "evidence",
        "Decision 索引": "decisions", "决策索引": "decisions",
        "Risk 索引": "risks", "风险索引": "risks",
        # FEAT-076: the unlocked families' section counts as its own
        # category (substring match, same discipline as the others).
        "行族索引": "families",
    }
    for line in index_lines:
        stripped = line.strip()
        # Detect section headers (## Task 索引, etc.)
        if stripped.startswith("## "):
            for key, cat in section_map.items():
                if key in stripped:
                    current_section = cat
                    break
            else:
                current_section = None
            continue
        if current_section and stripped.startswith("| ") and re.match(
            r"\|\s*[A-Z]+(?:-[A-Z]+)*-\d+", stripped
        ):
            index_counts[current_section] += 1
    return index_counts
