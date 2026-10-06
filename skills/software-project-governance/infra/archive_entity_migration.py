#!/usr/bin/env python3
"""
One-shot entity migration legs + rollback recovery for archive.py —
FIX-435 minimal cohesive split of the 28n module_size debt.

Domain (实体迁移/回滚层): the FIX-162/TD-014 decision & risk migration
legs (FIX-407 narrative fallback, FIX-170 closed-status gate, FIX-385
authority-conflict refusal), the FIX-164/FEAT-076 evidence write-migration
leg (all four row families), and the rollback unit (grouping + task /
evidence archive restore). Sibling of archive_parsing / archive_indexing
(FIX-417) and archive_verdicts / archive_migration_engine / archive_cli
(FIX-435).

Seam discipline (FIX-435): every ``*_impl`` takes ``host`` — the
archive.py entry module's live namespace dict. All ROOT-bound lookups
(``host["_decision_log"]()``, ``host["_ensure_archive_dirs"]()`` …) and
test-patchable primitives (``host["_decision_authority_state"]()`` — the
concurrent-cutover tests patch it on the archive module) resolve at call
time, so patch.object / ROOT rebinding / the isolated
spec_from_file_location load all behave exactly as the pre-split
monolith. Pure helpers are imported directly from the sibling modules.
"""

import re

from archive_parsing import (
    _ROW_FAMILY_LINE_PREFIXES,
    _decision_archive_version,
    _decision_narrative_title,
    _decision_related_column_index,
    _find_risk_log_header,
    _find_version_sections,
    _is_risk_closed,
    _make_ref_verdict,
    _parse_version_from_title,
    _row_family_archive_table_header,
    _version_in_range,
)
from archive_indexing import (
    _entry_version_for_archive,
    _parse_archive_version_range,
)
from archive_migration_engine import (
    BigTableMigrationError,
    DecisionStoreAuthorityConflict,
    _build_archive_header,
    _guard_row_family_write_migration,
    _row_family_journal_category,
    _write_archive_file,
    _big_table_target_lock,
)
from archive_verdicts import _decision_narrative_verdict

def _migrate_decisions_impl(version_start, version_end, task_versions,
                            dry_run=False, explain_out=None, *, host):
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
    authority_state = host["_decision_authority_state"]()
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

    dlog = host["_decision_log"]()
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
        narrative_context = host["_build_classification_context"]()
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
                migrate, n_reason, n_detail, n_ver = (
                    _decision_narrative_verdict(
                        line, dec_id, anchor_counts, task_versions,
                        narrative_ref_verdict, version_end,
                        host["_q6_date_window_fallback"]))
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

    host["_ensure_archive_dirs"]()
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
    archive_path = (host["_archive_dir"]() / "decisions" /
                    f"decisions-v{version_start}-{version_end}.md")
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
        authority_state = host["_decision_authority_state"]()
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

def _migrate_risks_impl(version_start, version_end, task_versions,
                        dry_run=False, explain_out=None, *, host):
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
    rlog = host["_risk_log"]()
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

    host["_ensure_archive_dirs"]()
    archive_body = [line for line, _ver in archived]
    archive_path = (host["_archive_dir"]() / "risks" /
                    f"risks-v{version_start}-{version_end}.md")
    header = _build_archive_header(version_start, version_end, "risks", len(archived),
                                   prev_file=None, next_file=None)
    _write_archive_file(archive_path, header, archive_body)
    rlog.write_text("\n".join(kept_lines), encoding="utf-8")
    return len(archived)

def _migrate_evidence_impl(version_start, version_end, task_versions,
                           dry_run=False, explain_out=None,
                           row_family="EVD", *, host):
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
    elog = host["_evidence_log"]()
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
    records = host["_classify_rows_for_family"](
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

    host["_ensure_archive_dirs"]()
    archive_body = list(_row_family_archive_table_header(row_family))
    archive_body.extend(line for line, _ver in archived)
    if row_family == "EVD":
        archive_path = host["_archive_dir"]() / "evidence" / \
            f"evidence-v{version_start}-{version_end}.md"
    else:
        # FEAT-076: family legs get their own never-overwrite filename.
        archive_path = host["_archive_dir"]() / "evidence" / \
            host["_next_family_archive_filename"](version_start, version_end,
                                                row_family)
    header = _build_archive_header(version_start, version_end,
                                   _row_family_journal_category(row_family),
                                   len(archived),
                                   prev_file=None, next_file=None)
    _write_archive_file(archive_path, header, archive_body)
    elog.write_text("\n".join(kept_lines), encoding="utf-8")
    return len(archived)

# ── Rollback recovery (FIX-435 moved verbatim; host-routed paths) ──

def _get_migration_archive_group_impl(subdir, archive_file, *, host):
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
        candidate = (host["_archive_dir"]() / candidate_subdir
                     / archive_file.name)
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
            d = host["_archive_dir"]() / candidate_subdir
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

def _rollback_task_archive_impl(archive_file, *, host):
    """Restore one task archive file into plan-tracker.md and remove it."""
    archive_content = archive_file.read_text(encoding="utf-8")
    plan_tracker = host["_plan_tracker"]()
    pt_content = (plan_tracker.read_text(encoding="utf-8")
                  if plan_tracker.exists() else "")

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
                if "[已归档]" in line and not host[
                        "_version_still_covered_by_task_archive"](
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
                    if "[已归档]" in line and not host[
                            "_version_still_covered_by_task_archive"](
                                v_str, archive_file
                    ):
                        new_lines[i] = line.replace("[已归档]", "").rstrip()
            new_pt = "\n".join(new_lines)

    host["_plan_tracker"]().write_text(new_pt, encoding="utf-8")
    archive_file.unlink()
    return f"{archive_file.name} → plan-tracker.md"

def _rollback_evidence_archive_impl(archive_file, *, host):
    """Restore one evidence archive file into evidence-log.md and remove it.

    FEAT-076: the file may carry ANY of the four row families' rows —
    every family-prefixed table row is restored (the 0.92 form only
    extracted ``| EVD-`` rows, which would have unlinked a family archive
    file WITHOUT restoring its rows = rollback data loss).
    """
    archive_content = archive_file.read_text(encoding="utf-8")
    evidence_log = host["_evidence_log"]()
    ev_content = (evidence_log.read_text(encoding="utf-8")
                  if evidence_log.exists() else "")

    # Extract evidence rows from archive (all four families).
    ev_rows = []
    for line in archive_content.split("\n"):
        stripped = line.strip()
        if any(stripped.startswith(prefix)
               for prefix in _ROW_FAMILY_LINE_PREFIXES.values()):
            ev_rows.append(line)

    if ev_rows:
        new_ev = ev_content.rstrip() + "\n" + "\n".join(ev_rows) + "\n"
        host["_evidence_log"]().write_text(new_ev, encoding="utf-8")

    archive_file.unlink()
    return f"{archive_file.name} → evidence-log.md"
