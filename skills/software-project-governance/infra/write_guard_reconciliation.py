"""Compare the current row families with the recorded checksums, receipts and posture."""

from dataclasses import dataclass
from collections.abc import Callable
import hashlib

from write_guard_records import _extract_ops_ledger_records


# ── FEAT-057: row-family reconciliation (受管行族对账) ──────────────────────
#
# The structural faces above judge SHAPES; this face judges the PROVENANCE of
# row-level CHANGES in the managed row families (EVD/REVIEW evidence rows,
# DEC decision rows, plan-tracker task-row status cells, ``*.ops.jsonl``
# receipt ledgers). It is the institutional close-out of the "8 hand row
# edits in one session" incident class: a managed row that changed since the
# last guard run WITHOUT a machine credential is disclosed as a loud WARN
# pointing the writer at governance_store / task_row_update.
#
# Posture (FEAT-064 — 分族 BLOCK 激活): the DEC-224 five families are ruled
# PER FAMILY against the FEAT-049 writer-contract registry (the ruling table
# lives in write_guard_state.FAMILY_RULING_DECLARATION). The shipped default
# is ALL-WARN (DEC-224-pinned posture) until the Coordinator activates a
# family's BLOCK posture through the guard CLI's ``--activate-block``
# management mode, which writes the guard-owned posture config
# (``.governance/.write-guard-posture.json``; absent = all-WARN = zero
# behavioral delta; corrupt = fail-safe all-WARN + loud disclosure).
# Disclosure caliber (review-FEAT-064-R0 P1-1 收敛): the state/baseline
# bytes and the zero-window output stay byte-identical, while the
# ``unattributed_row_change`` WARN TEXT was deliberately rewritten in
# FEAT-064 (the stale "BLOCK 升级留 0.87" tail note became the
# delivered-mechanism pointer) — that rewrite is the contract-matrix
# regeneration face (version.py re-audit + snapshots.json + golden_samples,
# three records in place), not an incidental drift.
# Under an active BLOCK posture an uncredentialed change in that family is
# a BLOCK-class face issue: face 5 FAILs and the guard exits 1 (the
# workflow is blocked loudly — the guard is write-AFTER, it cannot stop the
# file from being modified, M-0 事实填充项③ wording kept honest), and the
# offending surface's baseline is HELD at its previous snapshot (the R2
# flip: no WARN-once-then-absorb under BLOCK — DEC-236 ①). The sanctioned
# unlock is the writer remediation loop (re-apply through the family's
# writer → next run consumes the violation through the FEAT-060 transaction
# which advances the clamped baseline). The break-glass channel
# (``--break-grant``, time-boxed/count-limited/scoped, every use audited
# into the ledger) downgrades scoped BLOCK issues to loud WARN-class
# disclosures while a guard-self-repair window is open — never silent.
#
# Amnesty (存量不追溯): the FIRST sighting of a surface establishes its
# baseline — pre-existing rows are historical facts and are never judged.
# Only the delta since the previous guard run is reconciled. The baseline
# lives in ``.governance/.write-guard-state.json`` — a NEW guard-owned
# artifact, NOT a repair: the guard still never modifies any managed file,
# so the "check-only, zero .governance remediation" contract is unchanged
# for governance records. The state write happens ONLY on the CLI path
# (``persist_state=True``); probe callers (contract-matrix representative
# extraction, tests, aggregate reads) stay read-only and never consume the
# reconciliation window.
#
# FEAT-060 (0.88.0 B1 — DEC-224 双约束 + arch Q2): WARN-class observations
# additionally land in a PERSISTENT violation state machine
# (``.governance/.write-guard-violations.json``, infra/write_guard_state.py
# — the implementation entity; this file keeps only thin wiring, RISK-039
# thin-entry discipline). The WARN output semantics stay byte-identical
# (WARN posture pinned by DEC-224); the state machine adds: durable open/
# consumed/superseded records, same-session second-trigger escalation,
# cross-session persistence, a consumption-right ledger with pre-granted
# single-use grants for registered consumers, and an ops-recoverable consume
# transaction that bundles violation consumption with the baseline advance
# (crash mid-way → journal-driven resume, never a half state). See the
# module docstring of infra/write_guard_state.py for the six rules and
# their posture interpretation.
#
# Credential authority (consumed, never re-stated — FIX-292 lesson):
#   - EVD/DEC rows → the ``机器写入：governance-store <command> <op>`` marker
#     built by ``governance_store._build_evidence_row`` /
#     ``_build_decision_row`` (matched by its stable writer prefix below;
#     the guard test binds this prefix to a REALLY built row, so drift
#     fails the test rather than silently diverging);
#   - REVIEW rows → ``checks.review_domain.REVIEW_MACHINE_ROW_MARKER``
#     (Check 30c V7 authority, imported above);
#   - plan-tracker task rows → ``task_row_update.STATUS_CELL_OP_SUFFIX_PATTERN``
#     applied to the LAST cell (the writer's own "status column = last cell"
#     schema and its end-anchored provenance anchor — deferred import, same
#     pattern as the ``change_triage._TASK_ID_RE`` consumption above);
#   - ``*.ops.jsonl`` lines → the receipt schema anchor ``operation_id``
#     (task_row_update ledger receipt shape).
#
# Deliberate v1 boundaries (disclosed, not silent):
#   - TRIAGE/RECO rows are NOT marker-judged (their writers predate the
#     marker discipline; the DEC-168 column contract above already guards
#     their shape — same classification precedent as Check 30c V7);
#   - row DELETIONS are out of scope (archive migrations legitimately move
#     rows out of hot files; a vanished key is absorbed by the state update,
#     never judged);
#   - ``governance-store-ops.json`` (the JSON-document ledger) is not
#     line-diffable — its structural face is BT-4 adjacent, a later slice.


def _stamp_deferred_observation(observation):
    """FEAT-081 B4 / CR-R1-2: stamp the SKIP 分态 attribution onto the
    face-5 observation counters (mutates ``observation`` in place).

    Detector errors → orchestration_fallback; zero fired hits with the
    detection orchestration having run → vacuum; fired hits leave
    ``skip_kind`` None (not a SKIP shape — the rate-zeroing path owns it).
    Attribution is advisory bookkeeping: a stamping failure never breaks
    the reconciliation face.
    """
    try:
        from checks import loop_gate_processor as _lgp
        if observation["detector_errors"]:
            observation["skip_kind"] = _lgp.SKIP_ORCHESTRATION_FALLBACK
            observation["reason"] = (
                "检测器异常 ×{0}——编排异常兜底（fail-closed 披露）".format(
                    observation["detector_errors"]))
        elif not observation["fired"]:
            observation["skip_kind"] = _lgp.SKIP_VACUUM
            observation["reason"] = (
                "检测编排运行、零命中（rows_judged={0}）——真空面".format(
                    observation["rows_judged"]))
        else:
            observation["skip_kind"] = None
            observation["reason"] = "{0} fired deferred hit(s)".format(
                observation["fired"])
    except Exception:  # noqa: BLE001 — attribution is advisory bookkeeping
        pass


def _rows_snapshot(records):
    """State snapshot of one surface: ``{row_key: [digest, …]}`` (multiset
    per key preserves duplicate row ids)."""
    snapshot = {}
    for record in records:
        snapshot.setdefault(record["key"], []).append(record["digest"])
    for key in snapshot:
        snapshot[key].sort()
    return snapshot


def _build_violation_detection(surface, surface_kind, rel, record,
                               before_hash=None):
    """Face-5 offending record → write_guard_state detection dict
    (FEAT-060; thin adapter — the field vocabulary lives in the state
    machine module)."""
    import write_guard_state
    return write_guard_state.build_detection(
        family=surface,
        family_kind=surface_kind,
        object_id=record["key"],
        rel_path=rel,
        line=record["line"],
        row_text=record["text"],
        after_hash=record["digest"],
        before_hash=before_hash,
    )


def _judge_row_delta(
    surface, rel, records, baseline_rows, issues, surface_kind="text", detections_out=None,
    family_postures=None, honored_families=frozenset(), deferred_out=None, observation=None, *, has_receipt,
):
    """Multiset-diff current records against the baseline digests and emit
    one disclosure per uncredentialed added/changed row instance.

    Posture (FEAT-064): the row's DEC-224 canonical family decides the
    disclosure class — a BLOCK-active family (and not covered by a valid
    break-glass window) yields a BLOCK-class issue (``posture`` field set;
    face 5 FAILs on any such issue); everything else — including every
    family under the shipped all-WARN default — yields the WARN-class
    disclosure of the FEAT-057/060 era (same type/shape/fields; the TEXT
    carries FEAT-064's delivered-mechanism tail note in place of the stale
    "left to 0.87" wording — the deliberate rewrite recorded by the
    contract-matrix regeneration: version.py re-audit + snapshots.json +
    golden_samples, review-FEAT-064-R0 P1-1 收敛口径).

    ``detections_out`` (FEAT-060, CLI path only): when a list is supplied,
    every offending record is also appended as a state-machine detection
    dict (write_guard_state.build_detection) — the disclosure output itself
    is unchanged either way; the ledger is the only consumer."""
    import write_guard_state
    from checks import loop_gate_processor as _lgp
    postures = family_postures or {}
    baseline_pool = {}
    for key, digests in baseline_rows.items():
        if isinstance(digests, list):
            baseline_pool[key] = list(digests)
    for record in records:
        pool = baseline_pool.get(record["key"])
        if pool and record["digest"] in pool:
            pool.remove(record["digest"])  # unchanged instance
            continue
        # ── FEAT-081 / ADR-021 §3.2.1 B4: M2 词集检测 ────────────────────
        # Runs on EVERY added/changed row instance of the scoped families
        # (evidence EVD- rows + task_status plan-tracker rows), BEFORE and
        # ORTHOGONAL to the credential judge — a machine-credentialed row
        # can carry 登记-deferral semantics too (the ADR 判定 has no
        # credential carve-out). Exempt families (decision/review/ops)
        # judge to None. A detector-side error is a LOUD WARN-class
        # disclosure (fail-closed disclosure, ADR §2.4 L4 — never silent).
        if observation is not None:
            observation["rows_judged"] = observation.get("rows_judged", 0) + 1
        try:
            _deferred = _lgp.judge_deferred_row(
                surface, record["key"], record["text"])
        except Exception as exc:  # noqa: BLE001 — detector fail-closed face
            if observation is not None:
                observation["detector_errors"] = (
                    observation.get("detector_errors", 0) + 1)
            issues.append({
                "type": "deferred_registration_detector_error",
                "file": rel,
                "line": record["line"],
                "task_id": record["key"],
                "detail": "M2 词集检测器异常（{0}）——fail-closed 披露不静默"
                          "（ADR-021 §2.4 L4：检测失效静默 = 「登记待以后」"
                          "回归不可见；FEAT-081 B4）".format(exc),
                "expected": "检测器可运行（词集/否定语境窗口为确定性正则，"
                            "异常即缺陷）",
            })
            _deferred = None
        if _deferred is not None:
            if observation is not None:
                observation["hits"] = (
                    observation.get("hits", 0) + len(_deferred["hits"]))
                if _deferred["fired"]:
                    observation["fired"] = observation.get("fired", 0) + 1
            if _deferred["fired"]:
                issues.append({
                    "type": _lgp.DEFERRED_REGISTRATION_ISSUE_TYPE,
                    "file": rel,
                    "line": record["line"],
                    "task_id": record["key"],
                    "detail": _lgp.render_issue_detail(_deferred),
                    "expected": _lgp.DEFERRED_ISSUE_EXPECTED,
                })
            if deferred_out is not None:
                from datetime import date as _d
                today_str = _d.today().isoformat()
                for _hit in _deferred["hits"]:
                    deferred_out.append(_lgp.build_ledger_entry(
                        date_str=today_str,
                        surface=surface,
                        family=_deferred["family"],
                        row_key=record["key"],
                        line=record["line"],
                        hit_word=_hit["word"],
                        negative_context_hit=_hit["negative_context_hit"],
                    ))
        if has_receipt(surface, record["key"], record["text"]):
            continue
        family = write_guard_state.canonical_family(surface, record["key"])
        block_issue = (
            family is not None
            and postures.get(family) == write_guard_state.POSTURE_BLOCK
            and family not in honored_families)
        if detections_out is not None:
            # before_hash = a baseline instance the new content displaced
            # (audit hint, not identity — the multiset pool does not say
            # WHICH instance was replaced).
            detections_out.append(_build_violation_detection(
                surface, surface_kind, rel, record,
                before_hash=(pool[0] if pool else None)))
        if surface_kind == "ops":
            guidance = ("unattributed row change — ops 台账行须由写入器追加"
                        "（receipt 行携 operation_id 凭证）")
        elif surface == "plan-tracker.md":
            guidance = ("unattributed row change — use task_row_update"
                        "（状态列须携 〔op-…〕 机器锚）")
        else:
            guidance = ("unattributed row change — use governance_store"
                        "（行须携 机器写入：governance-store 凭证）")
        if block_issue:
            issues.append({
                "type": "unattributed_row_change",
                "file": rel,
                "line": record["line"],
                "task_id": record["key"],
                "posture": "block",
                "detail": ("unattributed row change — BLOCK 姿态（family {0}"
                           " 分族 BLOCK 已激活——FEAT-064）: {1}；补救 = 经"
                           "写入器补机器凭证后复跑（违规自动消费、基线随事务"
                           "收口）；窗口保持开放直至消费（不吸收——DEC-224 "
                           "R2 BLOCK 翻转）".format(family, guidance)),
                "expected": "受管行变更携带机器凭证（governance-store 标记 / "
                            "〔op-…〕 锚 / receipt operation_id）",
            })
        else:
            issues.append({
                "type": "unattributed_row_change",
                "file": rel,
                "line": record["line"],
                "task_id": record["key"],
                "detail": "{0}（WARN 姿态 0.86.0——响亮披露不阻断；分族 BLOCK "
                          "机制已交付未激活——FEAT-064，姿态经 "
                          "governance-write-guard --show-posture 查看）: {1}"
                          .format(record["key"], guidance),
                "expected": "受管行变更携带机器凭证（governance-store 标记 / "
                            "〔op-…〕 锚 / receipt operation_id）",
            })


def _credential_index(surface, records, surface_kind='text', *, has_receipt):
    """FEAT-060 consumption-eligibility index for one surface:
    ``{object_id: [{"digest", "credentialed"}, …]}`` — the credential
    verdict reuses the SAME authority the WARN judge consumes
    (:func:`has_receipt`; no second credential source)."""
    index = {}
    for record in records:
        index.setdefault(record["key"], []).append({
            "digest": record["digest"],
            "credentialed": has_receipt(
                surface, record["key"], record["text"]),
        })
    return index


@dataclass(frozen=True)
class RowInspection:
    """Readers and judgments which depend on the active task and writer contracts."""

    records: Callable
    credential_index: Callable
    judge_delta: Callable


def _reconcile_row_families(governance_dir, persist_state=False, detections_out=None,
                            records_index_out=None, deferred_out=None, *, inspect, load_baseline,
                            baseline_exists, surfaces, schema_version, tool, now):
    """FEAT-057 face 5 engine — 受管行族对账 (FEAT-064 posture-aware).

    Returns ``(result_face, next_state)``. ``result_face`` is the face dict
    ``{"status", "issues", "baselined"}`` (B4/FEAT-081 additionally carries
    ``deferred_observation`` — the M2 detection run's counters + SKIP 分态
    attribution, consumed by the CLI face's ledger record); the shipped
    all-WARN default keeps every disclosure WARN-class and the face PASS
    (byte-identical to the FEAT-057/060 era). Under an active family BLOCK
    posture (guard-owned posture config) an uncredentialed change in that
    family is a BLOCK-class issue and the face FAILs — the guard CLI then
    exits 1. The face status is FAIL iff at least one issue carries
    ``posture == "block"``; posture-layer and state-machine anomalies stay
    WARN-class disclosures (fail-safe: a broken posture config degrades to
    all-WARN loudly, never to a guessed BLOCK).

    Per managed surface: file SHA256 fast path (unchanged file → zero
    diff), then a per-row multiset digest diff against the baseline —
    added/changed row instances without a machine credential → one
    ``unattributed_row_change`` disclosure each. First sighting of a
    surface (amnesty) records its baseline and discloses it in
    ``baselined``.

    FEAT-060 out-params (CLI path only; probe calls pass None and stay
    byte-identical read-only): ``detections_out`` collects offending-row
    detection dicts for the violation state machine;
    ``records_index_out`` collects the per-surface current-instance map
    (object → digests + credential verdicts) the consumption-eligibility
    judge needs. Neither affects judging or output. FEAT-081 B4 adds
    ``deferred_out`` — the M2 word-set ledger entries (guard CLI face
    only; None on probes/internal paths).
    """
    face = {"status": "SKIPPED", "issues": [], "baselined": []}
    observation = {"rows_judged": 0, "hits": 0, "fired": 0,
                   "detector_errors": 0, "skip_kind": None, "reason": ""}
    face["deferred_observation"] = observation
    next_state = None
    if not governance_dir.is_dir():
        return face, next_state

    issues = []
    # Alias, not copy: every later append (load anomaly, surface errors,
    # judge WARNs) must land in the face — the judge result is the face's
    # payload, never a side list.
    face["issues"] = issues
    state, load_issue = load_baseline(governance_dir)
    if load_issue is not None:
        issues.append(load_issue)
    baseline_files = state["files"]
    next_files = {}
    # A pre-existing state file counts as a seen surface even when every
    # managed file is gone — the state must shrink, not silently vanish.
    surfaces_seen = baseline_exists(governance_dir)

    # FEAT-064 posture inputs (read-only in BOTH paths — probes never
    # consume anything): the family posture config + the valid break-glass
    # scope. A corrupt posture config fails safe to all-WARN (loud); a
    # corrupt ledger never honors a break-glass window (fail-closed).
    import write_guard_state as _wgs
    family_postures, posture_issue = _wgs.load_family_postures(
        governance_dir)
    if posture_issue is not None:
        issues.append(posture_issue)
    honored_families, break_glass_issue = _wgs.active_break_glass_families(
        governance_dir, postures=family_postures)
    if break_glass_issue is not None:
        issues.append(break_glass_issue)

    def _sha256_of(text):
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _surface_file(name):
        return governance_dir / name

    # Text surfaces (evidence / decision / plan-tracker).
    for surface in surfaces:
        path = _surface_file(surface)
        rel = ".governance/" + surface
        if not path.is_file():
            continue
        surfaces_seen = True
        try:
            content = path.read_text(encoding="utf-8")
        except (IOError, OSError, UnicodeDecodeError, ValueError) as exc:
            issues.append({
                "type": "row_family_surface_unreadable",
                "file": rel,
                "line": None,
                "task_id": "",
                "detail": "受管面不可读（{0}）——本轮跳过该面对账（不静默）"
                          .format(exc),
                "expected": "UTF-8 文本",
            })
            if records_index_out is not None:
                records_index_out[surface] = {"kind": "unreadable"}
            continue
        records = inspect.records(surface, content)
        if records_index_out is not None:
            records_index_out[surface] = {
                "kind": "text",
                "by_key": inspect.credential_index(surface, records),
            }
        current_sha = _sha256_of(content)
        baseline = baseline_files.get(surface)
        next_files[surface] = {
            "sha256": current_sha,
            "rows": _rows_snapshot(records),
        }
        if baseline == next_files[surface]:
            continue  # fast path: byte-identical to the baseline snapshot
        if not isinstance(baseline, dict) or "rows" not in baseline:
            # First sighting (or malformed entry) — amnesty, disclose.
            face["baselined"].append(rel)
            continue
        baseline_rows = baseline.get("rows")
        if not isinstance(baseline_rows, dict):
            face["baselined"].append(rel)
            continue
        if baseline.get("sha256") == current_sha:
            continue
        inspect.judge_delta(surface, rel, records, baseline_rows, issues,
                         detections_out=detections_out,
                         family_postures=family_postures,
                         honored_families=honored_families,
                         deferred_out=deferred_out, observation=observation)

    # ops 台账 surfaces (*.ops.jsonl — line-oriented receipt ledgers).
    for path in sorted(governance_dir.glob("*.ops.jsonl")):
        rel = ".governance/" + path.name
        surfaces_seen = True
        try:
            content = path.read_text(encoding="utf-8")
        except (IOError, OSError, UnicodeDecodeError, ValueError) as exc:
            issues.append({
                "type": "row_family_surface_unreadable",
                "file": rel,
                "line": None,
                "task_id": "",
                "detail": "ops 台账不可读（{0}）——本轮跳过该面对账（不静默）"
                          .format(exc),
                "expected": "UTF-8 JSONL",
            })
            if records_index_out is not None:
                records_index_out[path.name] = {"kind": "unreadable"}
            continue
        records = _extract_ops_ledger_records(content)
        if records_index_out is not None:
            records_index_out[path.name] = {
                "kind": "ops",
                "by_key": inspect.credential_index(path.name, records,
                                            surface_kind="ops"),
            }
        current_sha = _sha256_of(content)
        baseline = baseline_files.get(path.name)
        next_files[path.name] = {
            "sha256": current_sha,
            "rows": _rows_snapshot(records),
        }
        if baseline == next_files[path.name]:
            continue
        if not isinstance(baseline, dict) or not isinstance(
                baseline.get("rows"), dict):
            face["baselined"].append(rel)
            continue
        if baseline.get("sha256") == current_sha:
            continue
        inspect.judge_delta(path.name, rel, records, baseline["rows"], issues,
                         surface_kind="ops", detections_out=detections_out,
                         family_postures=family_postures,
                         honored_families=honored_families,
                         deferred_out=deferred_out, observation=observation)

    if not surfaces_seen:
        return face, next_state  # SKIPPED — nothing managed, nothing written

    _stamp_deferred_observation(observation)


    # FEAT-064: FAIL iff at least one BLOCK-class disclosure is present
    # (all-WARN default → PASS — the pinned WARN-era behavior).
    face["status"] = ("FAIL" if any(issue.get("posture") == "block"
                                    for issue in issues) else "PASS")
    if persist_state:
        next_state = {
            "schema_version": schema_version,
            "tool": tool,
            "updated_at": now().isoformat(timespec="seconds"),
            "files": next_files,
        }
    return face, next_state
