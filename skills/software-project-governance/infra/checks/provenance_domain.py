#!/usr/bin/env python3
"""Priority-enforcement provenance judgements — FEAT-077 / ADR-021 B2 (M1-L2).

Pure judgement pieces for the M1 优先级执法底层机制 (ADR-021
meta-mechanisms, DEC-288 Wave1). Delivered as the **unwired B2 half-batch**:
every function here is a pure predicate; the enforcement WIRING (the
check-governance 反倒挂判定 box, the ``check_release_readiness``
sub-check, and the 闭环率指标 face) is B3/B4 scope and lives in
``verify_workflow.py`` — **locked by FIX-404 at delivery time (ADR-021
§1.3 F10 / §4 批次表: 锁释放后实施)**. Check-box NUMBERS are deliberately
NOT hardcoded here (编号随 ADR 返工重编) — anchors are ADR-021 §2.2
section references.

Three functions (each anchored to its ADR section):

  - :func:`check_priority_inversion` — ADR-021 §2.2.3 反倒挂判定
    (Priority Inversion Guard): INV-1 (a machine-signal item ranked above
    an OPEN user-named item inside the recommended pool), INV-2 (an
    unblocked-eligible user-named item parked in ``non_executable`` while
    the recommended pool is non-empty and entirely machine-signal), staged
    fail-closed (demand-source coverage 0 → SKIP + WARN, BC-2 存量海瘫痪
    mitigation) and conflict rows → FAIL (data consistency outranks the
    ordering judgement).
  - :func:`check_release_admission` — ADR-021 §2.2.4 发布门判定
    (provenance release gate): a release version carrying open
    machine-signal work while user-named items stay open → FAIL;
    user-named items explicitly deferred to a strictly later version are
    exempt; a payload task with no declared provenance → FAIL (未申报
    fail-closed — the release gate is the last line).
  - :func:`session_closure_rate` — ADR-021 §3.2.3 闭环率指标 (M2
    effectiveness criterion, DEC-288): in-session closure rate with the
    deferred-registration zeroing precondition; the machine-checkable form
    is ``session_closure_rate == 1.0 ∧ deferred_detections == 0``.
  - :func:`collect_session_closure_events` — the shared W(session)
    event-collection core (FEAT-083): the evidence/risk row arms, the
    deferred-ledger arm and the window note, consumed by BOTH the engine's
    Check 42 (via thin delegation) and the bootstrap aggregate's
    ``behavior.session_closure`` sub-face. Retires the FEAT-082 disclosed
    bootstrap mirror (~150 duplicated lines) — one source, zero second
    implementation (review-FEAT-082-CODE-R0 §6.3 / DEC-302 附带勘误).

Purity contract: this module imports only the standard library plus the
peer pure module :mod:`task_priority` (the demand-source vocabulary) — it
NEVER imports ``verify_workflow`` (wiring stays one-way: the engine
consumes the domain, never the reverse; same discipline as
``checks/snapshot_domain.py`` / ``checks/gate_domain.py``). FEAT-083 adds
ONE disclosed file-reading collector at the bottom of this module (the
shared closure-event collection core); its ``loop_gate_processor``
dependency rides a FUNCTION-LOCAL import, so the module-level import face
stays stdlib + task_priority.

Row contract (shared by the two task-row judgements; mirrors the
:class:`task_priority.PriorityReport` bucket vocabulary so the B3 wiring
maps a report to rows mechanically)::

    {
        "task_id": str,                     # e.g. "FIX-226"
        "demand_source": str,               # user-named | active-defect |
                                            # machine-signal | legacy | conflict
        "bucket": str,                      # recommended | non_executable |
                                            # blocked | completed
        "priority": str,                    # optional, informational
        "target_version": str,              # optional, release-payload match
    }

``legacy`` (存量未标行, ADR-021 §2.2.1 向后兼容) participates in NEITHER
side of the inversion judgement — the 反倒挂判定 enforces the DEC-287(5)
transition discipline only over rows whose provenance is declared; the
staged fail-closed row below governs the all-legacy board.
"""

from __future__ import annotations

import re
from pathlib import Path

from task_priority import DEMAND_SOURCE_VALUES

__all__ = [
    "DEMAND_SOURCE_VALUES",
    "BUCKETS",
    "check_priority_inversion",
    "check_release_admission",
    "session_closure_rate",
    "CLOSURE_LEDGER_FILENAME",
    "RISK_TERMINAL_WORDS",
    "closure_evidence_events",
    "closure_risk_events",
    "read_deferred_ledger_events",
    "collect_session_closure_events",
]

# PriorityReport bucket vocabulary (task_priority.PriorityReport fields).
BUCKETS = ("recommended", "non_executable", "blocked", "completed")

# FEAT-080 / ADR-021 §2.2.3 R0 revision: the P-level qualifier parser. A
# bare ``P0``/``P1``/``P2`` cell parses to its numeric rank; anything else
# (empty, prose, markdown noise) parses to None — a pair that cannot BOTH
# be proven same-level is NEVER a FAIL (fail-closed in the disclosure
# direction: WARN via INV-X, never a FAIL on unprovable evidence).
_PRIORITY_RE = re.compile(r"^P([0-9])$")


def _priority_rank(value):
    """Numeric P-level for a bare ``P0``/``P1``/``P2`` cell, else None."""
    text = str(value or "").strip().upper()
    match = _PRIORITY_RE.match(text)
    return int(match.group(1)) if match else None

# Strict semver shape. Unlike task_priority._version_tuple (which returns
# the (inf, 0, 0) sort-last sentinel for unparseable values), the release
# gate must DISTINGUISH "no version" from "a version above the release" —
# an (inf) sentinel would silently classify every unversioned user-named
# row as explicitly deferred. This parser returns None for anything that is
# not a bare X.Y.Z.
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _parse_semver(value) -> tuple:
    """Strict ``(maj, min, patch)`` for a bare X.Y.Z string, else None."""
    text = str(value or "").strip()
    if not _SEMVER_RE.match(text):
        return None
    return tuple(int(part) for part in text.split("."))


def _rows(rows):
    """Coerce the input to a list of dicts (defensive; never raises)."""
    result = []
    for row in rows or []:
        if isinstance(row, dict):
            result.append(row)
    return result


def _bucket(row):
    return str(row.get("bucket", "") or "")


def _source(row):
    return str(row.get("demand_source", "") or "")


def _task_id(row):
    return str(row.get("task_id", "") or "")


def check_priority_inversion(rows) -> dict:
    """反倒挂判定 — ADR-021 §2.2.3 (Priority Inversion Guard).

    Deterministic, non-semantic machine rules (FAIL = any hit):

      - **INV-1 (推荐位倒挂)** — inside the ``recommended`` bucket, in row
        order, a ``machine-signal`` item M ranked above an OPEN ``user-named``
        item U (``completed`` rows are not open) **at the same P-level**
        (FEAT-080 / ADR-021 §2.2.3 R0 revision: the priority qualifier is
        part of the judgement — the sort's provenance tie-break operates
        within a P level, so a same-level inversion proves a sort defect or
        a hand-written recommendation bypass, both FAIL).
      - **INV-X (跨级压序披露, WARN)** — M ranked above U where M's P-level
        is strictly HIGHER (numerically lower) than U's: the D1 known
        tolerance (the sort deliberately never crosses P levels, ADR-021
        §2.2.2(5)); disclosed, never blocking — the terminal interception
        lives with the release gate (§2.2.4). A pair whose levels cannot
        both be parsed is disclosed the same way (fail-closed in the
        disclosure direction: never a FAIL on unprovable evidence).
      - **INV-2 (可执行性倒挂)** — a ``user-named`` row sits in the
        ``non_executable`` bucket (dependency-satisfied but held by a status
        marker) while the recommended pool is non-empty AND entirely
        ``machine-signal`` — 「用户项被停放而机器项占据全部推荐位」.
      - **conflict** — any row whose ``demand_source`` is ``conflict``
        (triage JSON vs 行内标注矛盾, ADR-021 §2.2.2 (3)) FAILs regardless
        of coverage: data consistency outranks the ordering judgement.

    Staged fail-closed (BC-2 存量海瘫痪 mitigation):

      - demand-source coverage (three-value rows / all rows) == 0 and no
        conflict rows → **SKIP + WARN** (「provenance 标注覆盖率 0——
        DEC-287(5) 过渡期执法未落地」); coverage > 0 → strict enforcement.

    Args:
        rows: ordered row dicts (row contract in the module docstring);
            the ORDER of ``recommended`` rows carries the rank information.

    Returns:
        dict ``{"status": "PASS"|"FAIL"|"SKIP", "issues": [str],
        "warnings": [str], "coverage": {"labeled", "total", "ratio"},
        "conflicts": [task_id], "inv1_pairs": [[m, u], ...],
        "invx_pairs": [[m, u], ...], "inv2_parked": [task_id]}``.
        Never raises.
    """
    rows = _rows(rows)
    issues = []
    warnings = []
    labeled = [r for r in rows if _source(r) in DEMAND_SOURCE_VALUES]
    coverage = {
        "labeled": len(labeled),
        "total": len(rows),
        "ratio": (len(labeled) / len(rows)) if rows else 0.0,
    }

    if not rows:
        return {
            "status": "SKIP", "issues": [], "warnings": [
                "empty rows input — 活跃队列为空，反倒挂判定无判定面"
                "（ADR-021 §2.2.3）"],
            "coverage": coverage, "conflicts": [],
            "inv1_pairs": [], "inv2_parked": [], "invx_pairs": [],
        }

    # conflict rows FAIL first (数据一致性优先于排序判断 — ADR §2.2.3).
    conflicts = [_task_id(r) for r in rows if _source(r) == "conflict"]
    for tid in conflicts:
        issues.append(
            "conflict: `{0}` 行内〔标注〕与 triage 记录 demand_source 冲突——"
            "数据一致性优先于排序判断，须人工校正（ADR-021 §2.2.2/§2.2.3）"
            .format(tid))

    if not labeled and not conflicts:
        return {
            "status": "SKIP", "issues": [], "warnings": [
                "provenance 标注覆盖率 0——DEC-287(5) 过渡期执法未落地"
                "（ADR-021 §2.2.3 分阶段 fail-closed / BC-2：覆盖率 > 0 即"
                "严格执法）"],
            "coverage": coverage, "conflicts": [],
            "inv1_pairs": [], "inv2_parked": [], "invx_pairs": [],
        }

    recommended = [r for r in rows if _bucket(r) == "recommended"]

    # INV-1 — machine-signal ranked above an OPEN user-named item.
    # FEAT-080 / ADR-021 §2.2.3 R0 revision: INV-1 FAILs only on a PROVEN
    # same-P-level inversion; a cross-level pair (machine P-level strictly
    # above the user-named one — the D1 known tolerance) and a pair whose
    # levels cannot both be parsed are disclosed as INV-X WARN instead
    # (never a FAIL on unprovable evidence; the cross-level terminal
    # interception lives with the release gate, ADR-021 §2.2.4).
    inv1_pairs = []
    invx_pairs = []
    for i, m in enumerate(recommended):
        if _source(m) != "machine-signal":
            continue
        for u in recommended[i + 1:]:
            if _source(u) != "user-named":
                continue
            rank_m = _priority_rank(m.get("priority"))
            rank_u = _priority_rank(u.get("priority"))
            if (rank_m is not None and rank_u is not None
                    and rank_m == rank_u):
                inv1_pairs.append([_task_id(m), _task_id(u)])
                issues.append(
                    "INV-1: `{0}`（machine-signal，{2}）排位高于同优先级开放"
                    " user-named 项 `{1}`——推荐位倒挂（ADR-021 §2.2.3 / "
                    "DEC-286(7)）".format(
                        _task_id(m), _task_id(u), m.get("priority") or "?"))
            elif (rank_m is not None and rank_u is not None
                    and rank_m < rank_u):
                invx_pairs.append([_task_id(m), _task_id(u)])
                warnings.append(
                    "INV-X: `{0}`（machine-signal，P{1}）压序 user-named 项"
                    " `{2}`（P{3}）——跨 P 级压序为 D1 已知容忍，披露不阻断"
                    "（终局拦截=发布门，ADR-021 §2.2.2(5)/§2.2.4）".format(
                        _task_id(m), rank_m, _task_id(u), rank_u))
            else:
                if rank_m is None or rank_u is None:
                    invx_pairs.append([_task_id(m), _task_id(u)])
                    warnings.append(
                        "INV-X: `{0}`（machine-signal）排位高于 user-named 项"
                        " `{1}`，但 P 级未全部可解析（{2!r} vs {3!r}）——无法"
                        "证明同级，保守披露不阻断（ADR-021 §2.2.3 FEAT-080）"
                        .format(_task_id(m), _task_id(u),
                                m.get("priority"), u.get("priority")))
                else:
                    # B4-2 (FIX-405 batch): resolved-but-out-of-order — M's
                    # P-level is STRICTLY LOWER yet it ranks above an OPEN
                    # user-named item. A correct sort key makes this shape
                    # impossible (P1 always precedes P2), so its occurrence
                    # proves a sort defect or a hand-written recommendation
                    # bypass: FAIL (ADR-021 §2.2.3 R0 立论——排序缺陷或手写
                    # 绕过均 FAIL), never a mere disclosure.
                    inv1_pairs.append([_task_id(m), _task_id(u)])
                    issues.append(
                        "INV-1: `{0}`（machine-signal，P{1}）排位高于更高优先"
                        "级开放 user-named 项 `{2}`（P{3}）——排序键正确时不可"
                        "能的形态：排序缺陷或手写推荐绕过（ADR-021 §2.2.3 / "
                        "B4-2 拆臂）".format(
                            _task_id(m), rank_m, _task_id(u), rank_u))

    # INV-2 — parked user-named while machine-signal fills the board.
    inv2_parked = [
        _task_id(r) for r in rows
        if _bucket(r) == "non_executable" and _source(r) == "user-named"]
    recommended_sources = {_source(r) for r in recommended}
    if inv2_parked and recommended and recommended_sources <= {"machine-signal"}:
        for tid in inv2_parked:
            issues.append(
                "INV-2: user-named 项 `{0}` 依赖已满足却被停放"
                "（non_executable），而推荐位非空且全部为 machine-signal——"
                "结构性大需求被无限顺延的可机检近似（ADR-021 §2.2.3 / "
                "DEC-286(7)）".format(tid))

    return {
        "status": "FAIL" if issues else "PASS",
        "issues": issues,
        "warnings": warnings,
        "coverage": coverage,
        "conflicts": conflicts,
        "inv1_pairs": inv1_pairs,
        "inv2_parked": inv2_parked,
        "invx_pairs": invx_pairs,
    }


def check_release_admission(rows, version_payload) -> dict:
    """发布门判定 — ADR-021 §2.2.4 (provenance release gate).

    Machine rules (deterministic):

      - **MS** = open rows with ``demand_source="machine-signal"`` whose
        ``target_version`` equals the release version.
      - **UN** = open ``user-named`` rows regardless of version — EXCEPT
        rows whose target version is a bare semver STRICTLY ABOVE the
        release version (用户已知悉的显式改期, DEC-286(7)「或显式请用户
        改期」); unversioned/unparseable targets stay in UN (结构性大需求
        不得因版本边界隐形顺延).
      - **FAIL**: MS non-empty ∧ UN non-empty → issues pair each MS row with
        each open UN row (「{MS 项}（machine-signal）载入 {V} 而 user-named
        {UN 项} 未闭合」).
      - **未申报 fail-closed**: an OPEN payload row (target_version ==
        release version) whose ``demand_source`` is neither of the three
        values → FAIL — 版本载荷的 provenance 不完整即拒绝发布 (新任务
        门禁下必有记录，缺记录只可能是绕过或存量异常). ``conflict``
        payload rows FAIL the same way (data consistency).
      - 存量不在发布门作用域 (BC-2): legacy rows targeting OTHER versions
        are not part of this payload and are never flagged.

    Args:
        rows: row dicts (module docstring contract; ``target_version``
            participates in payload matching).
        version_payload: ``{"version": "X.Y.Z"}`` — the release version being
            admitted (a bare semver string is accepted too). Missing or
            non-semver → SKIP with a warning (a gate without a version has
            no payload to judge; never a silent PASS).

    Returns:
        dict ``{"status": "PASS"|"FAIL"|"SKIP", "issues": [str],
        "warnings": [str], "release_version": str,
        "machine_signal_payload": [id], "open_user_named": [id],
        "deferred_user_named": [id], "undeclared_payload": [id]}``.
        Never raises.
    """
    rows = _rows(rows)
    if isinstance(version_payload, dict):
        release = str(version_payload.get("version", "") or "").strip()
    else:
        release = str(version_payload or "").strip()

    if _parse_semver(release) is None:
        return {
            "status": "SKIP", "issues": [], "warnings": [
                "release version 缺失或非 semver（{0!r}）——发布门无版本载荷"
                "可判，SKIP 而非静默 PASS（ADR-021 §2.2.4）".format(release)],
            "release_version": release,
            "machine_signal_payload": [], "open_user_named": [],
            "deferred_user_named": [], "undeclared_payload": [],
        }

    release_vt = _parse_semver(release)
    issues = []

    open_rows = [r for r in rows if _bucket(r) != "completed"]

    ms = [
        r for r in open_rows
        if _source(r) == "machine-signal"
        and _parse_semver(r.get("target_version")) == release_vt]

    un, deferred = [], []
    for r in open_rows:
        if _source(r) != "user-named":
            continue
        vt = _parse_semver(r.get("target_version"))
        if vt is not None and vt > release_vt:
            deferred.append(_task_id(r))  # 显式改期豁免
        else:
            un.append(_task_id(r))

    undeclared = []
    for r in open_rows:
        vt = _parse_semver(r.get("target_version"))
        if vt != release_vt:
            continue  # 不在本版本载荷内（BC-2：存量不在发布门作用域）
        source = _source(r)
        if source in DEMAND_SOURCE_VALUES:
            continue
        undeclared.append(_task_id(r))
        if source == "conflict":
            issues.append(
                "provenance release gate: 版本载荷任务 `{0}` demand_source "
                "conflict（行内标注与 triage 记录矛盾）——数据一致性优先，"
                "拒绝发布（ADR-021 §2.2.2/§2.2.4）".format(_task_id(r)))
        else:
            issues.append(
                "provenance release gate: 版本载荷任务 `{0}` 无 demand_source "
                "申报（未标/无 triage 记录）——版本载荷的 provenance 不完整即"
                "拒绝发布（ADR-021 §2.2.4 / §2.4 fail-closed）".format(
                    _task_id(r)))

    if ms and un:
        for m in ms:
            for u in un:
                issues.append(
                    "provenance release gate: `{0}`（machine-signal）载入 "
                    "{1} 而 user-named `{2}` 未闭合——用户点名需求不得因版本"
                    "边界隐形顺延（ADR-021 §2.2.4 / DEC-286(7)）".format(
                        _task_id(m), release, u))

    return {
        "status": "FAIL" if issues else "PASS",
        "issues": issues,
        "warnings": [],
        "release_version": release,
        "machine_signal_payload": [_task_id(r) for r in ms],
        "open_user_named": un,
        "deferred_user_named": deferred,
        "undeclared_payload": undeclared,
    }


def session_closure_rate(events) -> dict:
    """闭环率指标 — ADR-021 §3.2.3 (DEC-288 M2 effectiveness criterion).

    Definition (ADR §3.2.3)::

        session_closure_rate = closed_in_session / problems_raised_in_session
        违规前置: deferred_detections > 0 → rate = 0.0

    Pairing is ID-association only (ADR §3.2.2 — 行级启发，不追求语义完备):
    a problem event is closed when a closure event with the SAME id exists in
    the session (``EVD-{n}`` 问题行 ↔ 同 id 修复行 / ``RISK-{m}`` ↔ 同 id
    终局 / FAIL→PASS 复跑同 id / review APPROVED 配对同任务 id). 未配对即
    计入未闭环（保守计数：宁可多计不可漏计——漏计 = 零新账失守）.

    Args:
        events: list of dicts ``{"id": str, "kind": "problem" | "closure" |
            "deferred_registration"}``. Unknown kinds and malformed rows are
            ignored (never raise).

    Returns:
        dict ``{"problems_raised": int, "closed": int, "unclosed_ids": [id],
        "deferred_detections": int, "session_closure_rate": float,
        "compliant": bool}`` where ``compliant`` is the DEC-288 machine form
        ``session_closure_rate == 1.0 ∧ deferred_detections == 0``. An empty
        session (no problems, no deferrals) is trivially compliant (rate
        1.0); any deferred_registration detection zeroes the rate even when
        every raised problem was closed (「登记待以后」行为本身即未闭环的
        极端形态). Never raises.
    """
    events = [e for e in (events or []) if isinstance(e, dict)]
    problems = []
    closure_ids = set()
    deferred_detections = 0
    for event in events:
        kind = str(event.get("kind", "") or "").strip().lower()
        event_id = str(event.get("id", "") or "")
        if kind == "problem" and event_id:
            problems.append(event_id)
        elif kind == "closure" and event_id:
            closure_ids.add(event_id)
        elif kind == "deferred_registration":
            deferred_detections += 1

    raised = len(problems)
    closed = len([pid for pid in problems if pid in closure_ids])
    rate = (closed / raised) if raised else 1.0
    if deferred_detections:
        rate = 0.0  # 违规前置（ADR §3.2.3）
    compliant = (rate == 1.0) and deferred_detections == 0

    return {
        "problems_raised": raised,
        "closed": closed,
        "unclosed_ids": [pid for pid in problems if pid not in closure_ids],
        "deferred_detections": deferred_detections,
        "session_closure_rate": rate,
        "compliant": compliant,
    }


# ── session-closure event collection (FEAT-083, ADR-021 §3.2.3) ──────────────
#
# The W(session) collection core BOTH consumers call — the engine's Check 42
# (verify_workflow's ``_collect_session_closure_events`` is a thin
# delegation to :func:`collect_session_closure_events`) and the bootstrap
# aggregate's ``behavior.session_closure`` sub-face
# (``bootstrap_aggregate.session_closure_face``). FEAT-083 retires the
# FEAT-082 disclosed bootstrap mirror (~150 duplicated lines guarded by a
# tuple-for-tuple differential test — review-FEAT-082-CODE-R0 §6.3,
# DEC-302 附带勘误): one source, zero second implementation, the
# differential test converted to interface-equivalence + single-source
# assertions. Engine-free by construction: this leaf reads the governance
# tree directly and never imports verify_workflow; the ledger arm's JSONL
# parsing/event shaping reuses ``checks.loop_gate_processor`` via a
# FUNCTION-LOCAL import (the R6 cold-import discipline), so this module's
# module-level import face stays stdlib + task_priority.

#: The guard-owned M2 observation ledger filename — the storage contract
#: this READER shares with the write-guard CLI face (verify_workflow's
#: writer, aliased there as ``_DEFERRED_LEDGER_FILENAME``; the two values
#: are pinned equal by the FEAT-083 interface-equivalence tests).
CLOSURE_LEDGER_FILENAME = ".write-guard-deferred-ledger.jsonl"

#: ADR-021 §3.2.2 终局三选一 (「维持待复评」非法) — the RISK closure word
#: set. Matched against the 当前状态 + 备注 columns only (never 缓解 prose,
#: which routinely contains 「关闭」 as part of mitigation narrative).
RISK_TERMINAL_WORDS = ("关闭", "收窄", "升级")


def closure_evidence_events(text, today):
    """Evidence-log arm (pure): deterministic COLUMN matching.

    REVIEW rows (date column == ``today``): NEEDS_CHANGE/BLOCKED →
    problem(task) — BLOCKED joined NEEDS_CHANGE as the not-passed review
    terminals in FIX-405 (复审必达 state machine: both owe a later
    terminal pairing); APPROVED* → closure(task). EVD rows dated
    ``today`` with ``✅`` in the 备注 column → closure(task). Out-of-window
    rows never contribute. Never raises.
    """
    events = []
    for line in str(text or "").splitlines():
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) < 11 or cells[0] or not cells[1]:
            continue
        row_id, task = cells[1], cells[2]
        row_date, status = cells[8], cells[10]
        if row_date != today:
            continue
        if row_id.startswith("REVIEW-"):
            if status in ("NEEDS_CHANGE", "BLOCKED"):
                events.append({"id": task, "kind": "problem"})
            elif status.startswith("APPROVED"):
                events.append({"id": task, "kind": "closure"})
        elif row_id.startswith("EVD-") and "✅" in status:
            events.append({"id": task, "kind": "closure"})
    return events


def closure_risk_events(text, today):
    """Risk-log arm (pure): deterministic COLUMN matching.

    Every RISK row dated ``today`` raises a problem(RISK-id); a terminal
    word (:data:`RISK_TERMINAL_WORDS`) in the 当前状态+备注 tail adds the
    same-day closure (ADR-021 §3.2.2 终局三选一 pairing). Never raises.
    """
    events = []
    for line in str(text or "").splitlines():
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) < 11 or cells[0] or not cells[1].startswith("RISK-"):
            continue
        risk_id, row_date = cells[1], cells[2]
        if row_date != today:
            continue
        events.append({"id": risk_id, "kind": "problem"})
        status_tail = cells[9] + (cells[13] if len(cells) > 13 else "")
        if any(word in status_tail for word in RISK_TERMINAL_WORDS):
            events.append({"id": risk_id, "kind": "closure"})
    return events


def read_deferred_ledger_events(governance_dir, today):
    """Ledger arm: the M2 observation ledger → ``(events, anomaly)``.

    Fired ``deferred_hit`` entries dated ``today`` become
    ``deferred_registration`` events (the REAL signal path that makes the
    DEC-288 conjunct non-trivially satisfiable — CR-R1-1). A MISSING file
    is not an anomaly (the guard simply never recorded on this host —
    vacuum); an unreadable or malformed line IS one (fail-closed
    disclosure: a broken detection data path must never masquerade as a
    measured zero — CR-R1-2 orchestration fallback). Entries before a bad
    line are still counted (conservative direction: 宁可披露不可静默).
    Never raises.
    """
    from checks.loop_gate_processor import (
        deferred_events_from_entries,
        parse_ledger_line,
    )
    events = []
    anomaly = None
    path = Path(governance_dir) / CLOSURE_LEDGER_FILENAME
    if not path.is_file():
        return events, anomaly
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        return events, {"kind": "ledger_read", "reason": str(exc)}
    entries = []
    bad_lines = 0
    for line in lines:
        if not line.strip():
            continue
        parsed, error = parse_ledger_line(line)
        if error is not None:
            bad_lines += 1
            continue
        entries.append(parsed)
    events = deferred_events_from_entries(entries, today)
    if bad_lines:
        anomaly = {
            "kind": "ledger_parse",
            "reason": "{0} bad line(s) in {1}".format(
                bad_lines, CLOSURE_LEDGER_FILENAME),
        }
    return events, anomaly


def collect_session_closure_events(governance_dir, today=None):
    """W(session) event collection for Check 42 / the closure sub-face.

    FEAT-080 / ADR-021 §3.2.3, FEAT-083 single source: the evidence/risk
    row arms (:func:`closure_evidence_events` /
    :func:`closure_risk_events` — deterministic COLUMN matching, never
    semantic guessing), the deferred-ledger arm
    (:func:`read_deferred_ledger_events` — FEAT-081 B4: the deferred count
    is a REAL signal now, not a structural zero) and the window note. A
    session-snapshot carrying today's date upgrades the note to session
    identity; otherwise the note discloses the 按日聚合 degradation
    explicitly — never a silent degrade (ADR-021 §3.2.3 / §2.4 L4).

    Returns ``(events, window_note, face_state)`` — ``face_state`` carries
    the CR-R1-2 SKIP 分态 inputs: ``anomaly`` (ledger read/parse failure,
    or an evidence/risk row-family read failure — an orchestration
    fallback, never a silent vacuum) and ``deferred_detections`` (today's
    fired count). Never raises.

    Unlike the judgement pieces above, this ONE function reads the
    governance tree (the disclosed file-reading collector — FEAT-083).
    ``governance_dir`` is required: the engine-side
    ``governance_dir=None → GOVERNANCE_DIR`` default belongs to the
    caller because this leaf must stay engine-global-free.
    """
    from datetime import date as _date_cls
    today = today or _date_cls.today().isoformat()
    gov = Path(governance_dir)
    events = []
    read_failures = []
    evidence_path = gov / "evidence-log.md"
    if evidence_path.is_file():
        try:
            evidence_text = evidence_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            read_failures.append(
                "evidence-log.md unreadable ({0})".format(exc))
        else:
            events.extend(closure_evidence_events(evidence_text, today))
    risk_path = gov / "risk-log.md"
    if risk_path.is_file():
        try:
            risk_text = risk_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            read_failures.append(
                "risk-log.md unreadable ({0})".format(exc))
        else:
            events.extend(closure_risk_events(risk_text, today))
    deferred_events, ledger_anomaly = read_deferred_ledger_events(
        gov, today)
    events.extend(deferred_events)
    anomaly = ledger_anomaly
    if anomaly is None and read_failures:
        anomaly = {"kind": "row_read", "reason": "; ".join(read_failures)}
    snapshot_path = gov / "session-snapshot.md"
    snapshot_text = ""
    if snapshot_path.is_file():
        try:
            snapshot_text = snapshot_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            snapshot_text = ""
    if today in snapshot_text:
        window_note = ("window=session（session-snapshot 会话身份关联，"
                       "{0}）".format(today))
    else:
        window_note = (
            "window=daily-aggregate（按日聚合，同日多会话合并，精度降级——"
            "session-snapshot 未携带 {0}；禁止无标注的静默降级，"
            "ADR-021 §3.2.3 / §2.4 L4）".format(today))
    face_state = {
        "anomaly": anomaly,
        "deferred_detections": len(deferred_events),
    }
    return events, window_note, face_state
