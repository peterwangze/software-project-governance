#!/usr/bin/env python3
"""
Pure verdict / classification / explanation face for archive.py — FIX-435
minimal cohesive split of the 28n module_size debt (archive.py 4241 → shell).

Domain (判定层): the DEC-278 unit-one six-condition row classification, the
FEAT-075 four-family classifier, the FIX-407 narrative/Q6 verdict chain, the
FEAT-074 entity-registration context, the FIX-301 auditable-explain
aggregation, and the pure dry-run report renderers. Sibling of the FIX-417
modules (archive_parsing / archive_indexing) and of the FIX-435 engine /
entity-migration / cli modules.

Every function here is a PURE function of its inputs — with ONE injected
seam discipline (FIX-435):

  * none reads the module-level ROOT / PLUGIN_ROOT / HOST_PROJECT_ROOT seam,
    so ``patch.object(archive, "ROOT", ...)`` semantics (FIX-187 / FIX-242
    dual-root model) cannot be affected by the move;
  * the Q6 date-window fallback is NOT resolved here: classification impls
    take a ``q6_fallback`` callable (archive.py's wrapper passes its own
    ``_q6_date_window_fallback``, which resolves ``_window_end_release_date``
    → ``_plan_tracker()`` through the entry module at EVERY call — the
    per-row lazy plan-tracker read and the tests' patch surface
    (``patch.object(archive, "_window_end_release_date", ...)``) are
    preserved exactly);
  * a ``context=None`` default never appears here: the classification
    context is built by archive.py's wrapper (ROOT-bound plan-tracker read)
    and passed in — same call order as the pre-split single module.

archive.py re-imports / wraps every name below, so ``archive.<name>`` keeps
working (tests address these private helpers directly) and the isolated
spec_from_file_location loader for archive.py resolves this module through
the same sys.path entries (infra/ is script-dir / test-injected).
"""

import hashlib
import json
import re
from datetime import datetime

from archive_parsing import (
    _EVD_ID_SHAPE_RE,
    _ROW_FAMILY_ID_RES,
    _DECISION_ID_TOKEN_RE,
    _is_task_family_id,
    _make_ref_verdict,
    _parse_family_row,
    _parse_priority_table_tasks,
    _requirement_registry_ids,
    _version_in_range,
    _version_to_tuple,
)

def _sha256_text(text):
    """SHA-256 over UTF-8 text bytes — the resumable path pins digests over
    the exact bytes it writes, so line endings are platform-independent."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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

def _decision_narrative_verdict(line, dec_id, anchor_counts, task_versions,
                                ref_verdict, version_end, q6_fallback=None):
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
    fallback = (q6_fallback(line, version_end)
                if q6_fallback is not None else None)
    if fallback is None:
        return False, "narrative_date_out_of_window", "", None
    return True, "would_archive_narrative_q6", fallback, version_end

def _build_classification_context_impl(plan_tracker_content):
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

    ``plan_tracker_content`` is the live plan-tracker text. The None →
    live-read default lives in archive.py's same-name wrapper so the
    FIX-187/FIX-242 ROOT seam stays at the entry module (FIX-435).
    """
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

def _classify_rows_for_family_impl(row_family, content, task_versions,
                                   version_start, version_end, *, context,
                                   q6_fallback):
    """FEAT-076: single-source row classification dispatch for ALL four
    families' write-migration paths. EVD → _classify_evidence_rows (unit
    one); the three unlocked families → _classify_family_rows on the shared
    _make_ref_verdict typer (the same classification the read-only scanner
    uses — zero drift between scan candidacy and migration candidacy)."""
    if row_family == "EVD":
        return _classify_evidence_rows_impl(
            content, task_versions, version_start, version_end,
            context=context, q6_fallback=q6_fallback)
    lines = content.split("\n")
    line_bytes = [len(line.encode("utf-8")) + (0 if i == len(lines) - 1 else 1)
                  for i, line in enumerate(lines)]
    return _classify_family_rows_impl(
        row_family, lines, line_bytes, task_versions,
        version_start, version_end,
        _make_ref_verdict(task_versions, context), q6_fallback)


_ROW_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def _q6_date_window_fallback_impl(line, version_end, end_date):
    """FEAT-076 (DEC-278 单元三 Q6 ruling, 0.93-effective): the date-window
    fallback for rows with NO gating task-family refs.

    Returns the migration detail string when the row's own date proves
    closed-cycle membership (row date on/before the window-end version's
    release date), else None (retain hot — undatable rows and rows newer
    than the window end are the working set / fail-closed residue).

    The row date is the FIRST ISO yyyy-mm-dd token in the row — schema-
    drift-tolerant (the date column moved across eras) and unambiguous
    (ids/refs carry no dates)."""
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

def _classify_evidence_rows_impl(content, task_versions, version_start,
                                 version_end, *, context, q6_fallback):
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
            fallback = q6_fallback(line, version_end)
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

def _classify_family_rows_impl(family, lines, line_bytes, task_versions,
                               version_start, version_end, ref_verdict,
                               q6_fallback):
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
            fallback = q6_fallback(line, version_end)
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
