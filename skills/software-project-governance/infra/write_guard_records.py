"""Parse managed governance rows and check their writer receipts and column shapes."""

import hashlib
import json
from pathlib import Path

import governance_readers


def _triage_write_structure_guard(evidence_path, record_path, record_id=None):
    """FIX-278 G3: validate the artifacts ``run_triage`` just wrote.

    AUDIT-148 §4.2 (Check 14 无写时检测): reasoning-level 的 MAINT-017 入账后
    plan-tracker 结构在「无复核窗口」静默恶化（17:07 [PASS] → 08-26 17 issues）
    ——写入（机器入账）后没有结构合法性自动复核。本 guard 在
    ``change-triage`` CLI 的机器写入完成时点触发（等效 write-guard）：

      1. the written evidence-log row (``record_id`` — ``TRIAGE-{task}``,
         appended by ``run_triage`` at the END of the evidence-log) must match
         the column count the evidence-log establishes for its row FAMILY
         (FIX-279). The standard is the TRIAGE row family ITSELF — the first
         ``| TRIAGE- |`` row that is NOT this write: machine rows are
         uniformly 10 cols (incl. the files cell), while the EVD row family
         is a 9/10/11-col manual mix — so the first ``| EVD- |`` row is only
         a fallback when no TRIAGE family exists, and the comparison is
         skipped when neither exists. The written row is matched BY ROW ID —
         never by position — because it is the LAST TRIAGE row (append
         semantics, change_triage.py): positional scanning would both miss a
         broken fresh row (false-pass) and pick the wrong row as written;
      2. the written triage record JSON must parse.

    Scope (write guard, not repo guard): ONLY the written artifacts are
    judged — a pre-existing structural issue elsewhere in the governance dir
    never blocks intake (fail-safe to the writer's own artifacts only).
    FIX-284 (review-FIX-279-CODE-R0 P2-2): the row-family standard is the
    one deliberate overlap with pre-existing rows — the column contract is
    read FROM the evidence-log itself (DEC-168), so in a legacy
    heterogeneous library a historical legacy standard row can flag a write
    that matches the current format; the mismatch issue and the CLI
    remediation message therefore name the standard row source, keeping
    standard-row drift distinguishable from a writer bug.

    Returns a list of issue strings; empty = structurally sound. Never raises.
    """
    issues = []
    try:
        record_text = Path(record_path).read_text(encoding="utf-8")
        json.loads(record_text)
    except (OSError, UnicodeDecodeError) as exc:
        issues.append("triage record unreadable after write: {0}".format(exc))
    except json.JSONDecodeError as exc:
        issues.append("triage record JSON invalid after write: {0}".format(exc))
    try:
        content = Path(evidence_path).read_text(encoding="utf-8")
    except (IOError, OSError, UnicodeDecodeError) as exc:
        issues.append("evidence-log unreadable after write: {0}".format(exc))
        return issues
    # Column contract (FIX-279): the canonical column count for the written
    # | TRIAGE-{task} | row comes from the TRIAGE row family ITSELF — the
    # first | TRIAGE- | row that is NOT this write (machine rows are
    # uniformly 10 cols incl. the files cell). The | EVD- | family is a
    # 9/10/11-col manual mix (first row 9 cols) and must NOT set the standard
    # for machine rows — it is only a fallback when no TRIAGE family exists
    # (legacy repo without prior triage rows), and the comparison is skipped
    # when neither exists. Matching is by row id (``record_id`` or derived
    # from the record file stem), never by position: the written row is the
    # last TRIAGE row (append).
    if not record_id:
        try:
            record_id = "TRIAGE-" + Path(record_path).stem
        except (OSError, ValueError):
            record_id = ""
    standard_cols = None
    standard_source = ""
    triage_family_found = False
    written_cols = None
    written_found = False
    for line in content.split("\n"):
        line = line.strip()
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) > 1:
            written_found |= (parts[1] == record_id)
        if line.startswith("| TRIAGE-"):
            if parts[1] == record_id:
                written_cols = len(governance_readers.markdown_table_cells(line))
            elif not triage_family_found:
                triage_family_found = True
                standard_cols = len(governance_readers.markdown_table_cells(line))
                standard_source = "first non-written TRIAGE-family row"
            continue
        if not triage_family_found and standard_cols is None \
                and line.startswith("| EVD-"):
            standard_cols = len(governance_readers.markdown_table_cells(line))
            standard_source = "EVD fallback row (legacy log without a " \
                "prior TRIAGE family)"
    if not written_found:
        issues.append(
            "written evidence row {0} not found after the machine write — "
            "evidence-log append did not take effect".format(record_id))
    elif (standard_cols is not None and written_cols is not None
            and written_cols != standard_cols):
        issues.append(
            "evidence row {0} has {1} columns, evidence-log standard is {2} "
            "from the {3} (Check 14 evidence_col_mismatch rule; DEC-168 "
            "row-family authority — the standard row may be a historical "
            "legacy row with an older column count; verify the standard row "
            "itself if the written row matches the current format)".format(
                record_id, written_cols, standard_cols, standard_source))
    return issues


def _plan_tracker_task_row_issues(content, *, expected_shape, task_id_pattern, normalize_priority):
    """FEAT-011 face 1 — plan-tracker task-row shape issues (AUDIT-149 §4 M1).

    Scans EVERY table row that carries a standalone task-ID cell (the same
    detection :func:`parse_current_active_tasks` uses — M1 rows live in
    completed-task sections too, e.g. plan-tracker L188-190) for the two
    ragged-row signatures AUDIT-149 §4 M1 documented live:

      - ``plan_tracker_duplicate_priority_cell``: more than one priority
        token before the task-ID cell (live: ``| **P0** | **P0** | FIX-222 |``)
        — shifts every task-relative column read by one;
      - ``plan_tracker_trailing_empty_status``: empty LAST cell (live:
        ``… | ✅ 完成 (…) | |``) — ``cells[-1]`` parses empty, the status
        verdicts ACTIVE forever (67/117 health-noise contributor).

    Shape authorities are reused, never redefined: cell splitting via
    :func:`governance_table_cells` (JSON-pipe/code-span aware), priority
    tokens via :func:`normalize_priority`, task-ID cells via
    ``task_id_pattern``. Legit variations stay untouched (single priority
    column, non-empty trailing status / status-continuation cells — live
    REL-070/FIX-278 shapes), so the three live examples behind the M-0 ②
    pre-observation lift (plan-tracker L255/L257 annotations) take no new
    false positives.

    Pure: parses the passed text, performs no I/O. Returns issue dicts
    ``{"type", "file", "line", "task_id", "detail", "expected"}``.
    """
    issues = []
    for lineno, line in enumerate(content.split("\n"), 1):
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = governance_readers.governance_table_cells(stripped)
        if not cells:
            continue
        task_idx = next(
            (idx for idx, cell in enumerate(cells)
             if task_id_pattern.match(cell.strip())),
            None,
        )
        if task_idx is None:
            continue
        task_id = cells[task_idx].strip().strip("*")
        prio_cells = [c for c in cells[:task_idx] if normalize_priority(c)]
        if len(prio_cells) > 1:
            issues.append({
                "type": "plan_tracker_duplicate_priority_cell",
                "file": ".governance/plan-tracker.md",
                "line": lineno,
                "task_id": task_id,
                "detail": "重复优先级列——任务 ID 前出现 {0} 个优先级"
                          "单元格（{1}），任务相对列整体右移一列"
                          .format(len(prio_cells), "、".join(prio_cells)),
                "expected": expected_shape,
            })
        if not cells[-1].strip():
            issues.append({
                "type": "plan_tracker_trailing_empty_status",
                "file": ".governance/plan-tracker.md",
                "line": lineno,
                "task_id": task_id,
                "detail": "行尾空单元格——末单元格为空，状态列被解析"
                          "为空 → 判活跃（AUDIT-149 §4 M1；修复动作留给"
                          "写入者，本守卫只检不改）",
                "expected": expected_shape,
            })
    return issues


def _evidence_machine_row_issues(content, *, machine_families):
    """FEAT-011 face 2 — evidence-log machine-family row issues.

    For each machine-written family (``machine_families``):

      - column count: every row MUST match the family's own standard — its
        FIRST row (DEC-168 row-family authority; whole-file extension of the
        FIX-279 write-guard column contract, same ``markdown_table_cells``
        counting);
      - ID format: the row id MUST be ``{FAMILY}-{TASK_ID}`` where TASK_ID
        matches the writer's authoritative ``change_triage._TASK_ID_RE``
        (single definition — reused, not re-stated).

    Manual families (EVD/REVIEW legacy mixes) are deliberately NOT column-
    enforced here — their heterogeneity is documented (FIX-279) and Check 14
    already covers them at WARN. Pure: no I/O. Returns issue dicts like
    face 1 (``task_id`` carries the row id).
    """
    from change_triage import _TASK_ID_RE
    issues = []
    family_standard = {}
    lines = content.split("\n")
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        for family in machine_families:
            if not stripped.startswith("| " + family + "-"):
                continue
            cols = len(governance_readers.markdown_table_cells(stripped))
            if family not in family_standard:
                family_standard[family] = cols
            elif cols != family_standard[family]:
                issues.append({
                    "type": "evidence_machine_col_mismatch",
                    "file": ".governance/evidence-log.md",
                    "line": lineno,
                    "task_id": (stripped.split("|")[1].strip()
                                if "|" in stripped else ""),
                    "detail": "机器行族 {0} 列数 {1} ≠ 行族标准 {2}"
                              "（DEC-168 行族权威——标准取行族首行；"
                              "修复动作留给写入者）".format(
                                  family, cols,
                                  family_standard[family]),
                    "expected": "{0} 行族标准 {1} 列（行族首行确立）".format(
                        family, family_standard[family]),
                })
            row_id = stripped[2:stripped.find("|", 2)].strip()
            suffix = row_id[len(family) + 1:] if row_id.startswith(
                family + "-") else ""
            if not _TASK_ID_RE.match(suffix):
                issues.append({
                    "type": "evidence_machine_id_format",
                    "file": ".governance/evidence-log.md",
                    "line": lineno,
                    "task_id": row_id,
                    "detail": "机器行 ID 格式破坏——{0!r} 不匹配 "
                              "写入器契约 {1}-{{PREFIX-NNN}}（权威源 "
                              "change_triage._TASK_ID_RE）".format(
                                  row_id, family),
                    "expected": "{0}-{1}".format(
                        family, "PREFIX-NNN（如 {0}-FIX-241）".format(family)),
                })
            break
    return issues


def _row_has_governance_store_machine_credential(raw_line, *, receipt_pattern):
    """True when an evidence-log row carries the DEC-168 machine credential.

    FIX-390 Check 18b input: a row written by ``governance-store
    evidence-append`` carries its structured provenance (operation id +
    schema receipt) in the marker inside the basis cell — the machine
    counterpart of a hand-written structured-fact JSON payload. Row-level
    search (same granularity as the write-guard face-5 credential scan).
    """
    return bool(receipt_pattern.search(raw_line or ""))


def _write_guard_row_digest(text):
    """Stable row digest (128-bit truncation — collision-safe for
    reconciliation windows; the state file is a host-local artifact)."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:32]


def _extract_managed_row_records(surface, content, *, task_id_pattern):
    """Managed row records of one text surface → ``[record, …]`` where each
    record is ``{"key", "line", "text", "digest"}``.

    Row detection reuses the established parsers only: evidence/decision
    rows are prefix-matched on the rendered row-id cell; plan-tracker task
    rows reuse the exact :func:`governance_table_cells` +
    ``task_id_pattern`` detection of face 1 (no second task-row shape
    source). Pure: no I/O.
    """
    records = []
    for lineno, line in enumerate(content.split("\n"), 1):
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        if surface == "plan-tracker.md":
            cells = governance_readers.governance_table_cells(stripped)
            if not cells:
                continue
            task_idx = next(
                (idx for idx, cell in enumerate(cells)
                 if task_id_pattern.match(cell.strip())),
                None,
            )
            if task_idx is None:
                continue
            key = cells[task_idx].strip().strip("*")
        elif surface == "evidence-log.md":
            if not (stripped.startswith("| EVD-")
                    or stripped.startswith("| REVIEW-")):
                continue
            key = stripped[2:stripped.find("|", 2)].strip()
        else:  # decision-log.md
            if not stripped.startswith("| DEC-"):
                continue
            key = stripped[2:stripped.find("|", 2)].strip()
        records.append({
            "key": key,
            "line": lineno,
            "text": stripped,
            "digest": _write_guard_row_digest(stripped),
        })
    return records


def _extract_ops_ledger_records(content):
    """Receipt-ledger records → ``[record, …]`` keyed by line index (the
    ledger is append-only; the index is the identity a receipt line keeps
    across guard runs)."""
    records = []
    for lineno, line in enumerate(content.split("\n"), 1):
        if not line.strip():
            continue
        records.append({
            "key": str(lineno),
            "line": lineno,
            "text": line.strip(),
            "digest": _write_guard_row_digest(line),
        })
    return records


def _row_family_credential_ok(surface, row_key, row_text, *, review_marker, store_prefix, operation_anchor):
    """True when the changed row carries its writer's machine credential
    (authority mapping in the FEAT-057 block comment above)."""
    if surface == "plan-tracker.md":
        from task_row_update import STATUS_CELL_OP_SUFFIX_PATTERN
        cells = governance_readers.governance_table_cells(row_text)
        if not cells:
            return False
        return bool(STATUS_CELL_OP_SUFFIX_PATTERN.search(cells[-1]))
    if surface == "evidence-log.md":
        if row_key.startswith("REVIEW-"):
            return review_marker in row_text
        return store_prefix in row_text
    if surface == "decision-log.md":
        return store_prefix in row_text
    return operation_anchor in row_text  # *.ops.jsonl receipts
