#!/usr/bin/env python3
"""Gate/review terminal processor — production gate back-edge/round/fuse/escalation.

FEAT-006 (ADR-014 §4, 0.68.0). Product code, authorized by Design Review
APPROVED_WITH_NOTES/0 (EVD-841/842).

This module is the **bridge from a real gate event to the PARO state machine**
(the AUDIT-133 "call sites = 0" fix). It exposes one primary entry point,
:func:`process_gate_result`, that consumes a flow-unit gate result, reads the
registry's ``loop_gate_semantics`` + ``loop_fuses``, and atomically records the
back-edge (``reflect → plan``) + increments ``loop_state.loop_count`` + appends a
``gate_result``/``back_edge``/``fuse_trip``/``loop_exit``/``unit_blocked`` event.
When ``loop_count`` would exceed ``fuse.max_rounds`` it trips the fuse. It also
exposes :func:`loop_fuse_check`, a PURE READ that the release/governance gate
calls as a **system-level block** (not a Coordinator advisory).

**Scope (FEAT-006 ONLY):**

  - :func:`process_gate_result` — the §4.1 gate/review terminal processor. Maps
    a gate result to ``iterate`` | ``exit`` | ``escalate``, drives the FEAT-005
    CAS writer (:func:`loop_paro_engine.apply_transition`), and returns a
    :class:`GateOutcome`.
  - :func:`loop_fuse_check` — the §4.4 system-level block. PURE READ: scans
    ``flow-unit-runtime.json`` for units with ``fuse.tripped == true`` AND
    ``runtime_status in {blocked, escalated}``. Returns a list of unresolved
    tripped fuses. It MUST NOT mutate state.

**Out of scope (NOT implemented here):**

  - FEAT-007 (event log JSONL). :func:`process_gate_result` collects the events
    it *would* append in :attr:`GateOutcome.events`; the actual JSONL append is
    FEAT-007. For now events are collected but not written to a log file.

**Constraints honored:**

  - ``loop_engine.py``'s pure functions (:func:`derive_round`,
    :func:`escalation_payload`) are NOT modified. :func:`escalation_payload` is
    INVOKED read-only on fuse trip; :func:`derive_round` is INVOKED read-only
    for the round-counting consistency cross-check.
  - FEAT-005's ``loop_paro_engine.py`` is NOT modified. :func:`apply_transition`
    is the CAS writer this processor drives; it is INVOKED, not changed.
  - The 0.67.0 v2 validator is NOT modified. This module's writer produces
    payloads that pass both the 0.67.0 pass and the FEAT-005 transition/CAS pass.
  - Back-edge atomicity (§4.2): the back-edge (``reflect→plan`` + ``loop_count++``
    + last-result update + round-evidence row) is ONE CAS write — all mutations
    share one ``cas_version`` bump (applied by :func:`apply_transition` via the
    ``side_effects`` callback).
  - Round counting dual representation (§4.3): after each back-edge the writer
    also appends a ``LOOP-{U}-{T}-R{n}`` row to ``loop_state.round_evidence`` so
    the pure :func:`derive_round` re-derives the same value as
    ``loop_state.loop_count``.
  - RISK-037 / RISK-042 remain open.

**CAS protocol (ADR-014 §3.3) — delegated to FEAT-005's writer:**

    process_gate_result does the LOAD/LOOKUP/MAP/UNIFY/DECIDE compute
    (registry reads, fuse evaluation, escalation generation) and then calls
    ``apply_transition(unit_id, target_phase, event, runtime_file=...,
    side_effects=...)``. ``apply_transition`` does the atomic re-read-check-
    replace CAS write (§3.3 step 4) and bumps ``cas_version`` by exactly 1.
    The ``side_effects`` callback applies the FEAT-006-specific mutations
    (evidence_refs append, round-evidence row append) INSIDE the same atomic
    write, so the back-edge + round increment + round-evidence row can never
    diverge.

Usage:
    from loop_gate_processor import process_gate_result, loop_fuse_check

    outcome = process_gate_result(
        "shitu.story.Skeleton", "G6", "NEEDS_CHANGE",
        evidence_ref="review-code-Skeleton-R2.md",
        actor="code-reviewer-agent",
        runtime_file=path_to_flow_unit_runtime_json,
    )
    if outcome.decision == "escalate":
        ...  # outcome.escalation_payload is the 4-option AskUserQuestion

    # System-level block in the release/governance gate (§4.4):
    tripped = loop_fuse_check(root=host_project_root)
    if tripped:
        release_fails(...)  # "不依赖 Coordinator 自觉"
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

# loop_engine is a peer module (no import cycle). It holds the SACRED pure
# functions derive_round / escalation_payload — both invoked read-only here.
import loop_engine
# loop_paro_engine is a peer module (FEAT-005 CAS writer). apply_transition /
# activate_unit / TransitionResult are INVOKED here, not modified.
import loop_paro_engine

# ─── Fixed anchors ─────────────────────────────────────────────
PLUGIN_HOME = Path(__file__).resolve().parent.parent

# ─── Deferred verify_workflow import (avoid import cycle) ──────
# verify_workflow imports this module's loop_fuse_check via the thin release-gate
# wiring, so this module MUST NOT import verify_workflow at module top level. We
# resolve it lazily on first runtime read (the ``_vw()`` pattern, same as
# loop_health.py / loop_engine.py rollup).
_VW_CACHE = None


def _vw():
    """Lazy accessor for verify_workflow (deferred to avoid the import cycle).

    verify_workflow imports this module (the release-gate fuse-block wiring),
    so importing it at module top level would create a cycle. Resolved lazily on
    the first runtime read, exactly mirroring the ``_vw()`` pattern in
    ``loop_health.py`` and ``loop_engine.rollup_loop_state``.
    """
    global _VW_CACHE
    if _VW_CACHE is None:
        import verify_workflow  # noqa: WPS433 deferred import
        _VW_CACHE = verify_workflow
    return _VW_CACHE


# ═══════════════════════════════════════════════════════════════════════════
# Phase / outcome / result vocabulary (kept in sync with loop_paro_engine).
# ═══════════════════════════════════════════════════════════════════════════

PLAN = loop_paro_engine.PLAN
ACT = loop_paro_engine.ACT
OBSERVE = loop_paro_engine.OBSERVE
REFLECT = loop_paro_engine.REFLECT
EXIT = loop_paro_engine.EXIT
ESCALATE = loop_paro_engine.ESCALATE
WITHDRAWN = loop_paro_engine.WITHDRAWN

# GateOutcome.decision values.
DECISION_ITERATE = "iterate"
DECISION_EXIT = "exit"
DECISION_ESCALATE = "escalate"

# Internal mapped statuses (§4.1 step 3): a raw review conclusion is normalized
# to one of {passed, failed, blocked} before the DECIDE step.
_MAPPED_PASSED = "passed"
_MAPPED_FAILED = "failed"
_MAPPED_BLOCKED = "blocked"

# Result-string → mapped-status sets. APPROVED/APPROVED_WITH_NOTES (and
# case/separator variants) → passed. NEEDS_CHANGE/failed (and variants) →
# failed. BLOCKED → blocked. Unknown strings map to failed (fail-closed: an
# unrecognized result is treated as a failure driving iterate-vs-escalate, not a
# silent pass). The raw "passed"/"failed"/"blocked" canonical strings are also
# accepted so tests can pass the mapped status directly.
_PASSED_RESULTS = frozenset({
    "APPROVED", "APPROVED_WITH_NOTES", "APPROVED-WITH-NOTES", "APPROVED WITH NOTES",
    "passed", "pass", "PASS", "ok", "OK", "lgtm", "LGTM",
})
_FAILED_RESULTS = frozenset({
    "NEEDS_CHANGE", "NEEDS-CHANGE", "NEEDS CHANGE", "CHANGES_REQUESTED",
    "REJECTED", "failed", "fail", "FAIL",
})
_BLOCKED_RESULTS = frozenset({
    "BLOCKED", "blocked", "BLOCK",
})


def _map_result(raw_result):
    """Map a raw review/gate conclusion to {passed, failed, blocked} (§4.1 step 3).

    APPROVED/APPROVED_WITH_NOTES → passed; NEEDS_CHANGE/failed → failed;
    BLOCKED → blocked. Unknown non-empty strings map to ``failed`` (fail-closed:
    an unrecognized result is NOT a silent pass — it drives iterate-vs-escalate).
    ``None``/empty maps to ``failed`` as well (a missing result cannot be a pass).
    """
    if not isinstance(raw_result, str):
        return _MAPPED_FAILED
    norm = raw_result.strip()
    if not norm:
        return _MAPPED_FAILED
    upper = norm.upper()
    if norm in _PASSED_RESULTS or upper in {r.upper() for r in _PASSED_RESULTS}:
        return _MAPPED_PASSED
    if norm in _BLOCKED_RESULTS or upper in {r.upper() for r in _BLOCKED_RESULTS}:
        return _MAPPED_BLOCKED
    # Everything else (incl. explicit failed-result strings and unknown values)
    # is a failure driving iterate-vs-escalate.
    return _MAPPED_FAILED


# ═══════════════════════════════════════════════════════════════════════════
# GateOutcome frozen dataclass (ADR-014 §4.1)
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class GateOutcome:
    """Outcome of :func:`process_gate_result` (§4.1).

    Frozen so callers cannot mutate the recorded outcome. The decision is the
    load-bearing field: ``iterate`` (back-edge; loop continues), ``exit`` (gate
    passed; loop exits this tier), or ``escalate`` (fuse tripped or operator
    block; unit is blocked pending human resolution).

    Attributes:
        unit_id: the flow_unit_id whose gate ran.
        decision: ``"iterate"`` | ``"exit"`` | ``"escalate"``.
        new_agent_phase: the unit's ``agent_phase`` after the transition
            (``plan`` on iterate; ``reflect`` on exit; ``reflect`` on escalate).
            None when no transition was committed (illegal/error/conflict).
        new_loop_count: the unit's ``loop_state.loop_count`` after the
            transition. On iterate this is ``old + 1``; on exit/escalate it is
            the count at decision time (exit does not increment; escalate sets
            it to the would-be round).
        fuse_tripped: True iff the fuse tripped on this gate result (escalate
            via fuse exhaustion).
        escalation_payload: the 4-option AskUserQuestion payload (from
            :func:`loop_engine.escalation_payload`) when the fuse tripped; None
            otherwise.
        cas_version: the committed ``cas_version`` after the transition (None
            when no transition was committed).
        events: the list of event dicts this transition *would* append to the
            FEAT-007 JSONL event log. Collected now; the actual append is
            FEAT-007. Each dict carries ``unit_id``, ``event_type``,
            ``cas_version``, ``actor``, ``evidence_ref``, plus event-specific
            payload keys.
        status: the underlying :class:`loop_paro_engine.TransitionResult` status
            on success (``"success"``); one of ``"illegal"`` / ``"conflict"`` /
            ``"error"`` when the CAS write did not commit.
        reason: short diagnostic (always populated; the TransitionResult reason
            on non-success).
        mapped_status: the §4.1 step-3 mapped status (``passed``/``failed``/
            ``blocked``) — recorded for observability.
    """
    unit_id: str
    decision: str
    new_agent_phase: object = None
    new_loop_count: object = None
    fuse_tripped: bool = False
    escalation_payload: dict = None
    cas_version: object = None
    events: list = field(default_factory=list)
    status: str = ""
    reason: str = ""
    mapped_status: str = ""

    @property
    def success(self):
        """True iff the CAS write committed (status == ``"success"``)."""
        return self.status == loop_paro_engine.STATUS_SUCCESS


# ═══════════════════════════════════════════════════════════════════════════
# Runtime file I/O helpers (mirrors loop_paro_engine / loop_health)
# ═══════════════════════════════════════════════════════════════════════════


def _runtime_path(root):
    """Resolve the ``flow-unit-runtime.json`` path for a host ``root``.

    Uses verify_workflow's ``_flow_unit_runtime_path`` (the canonical RISK-040
    HOST_PROJECT_ROOT resolver) when ``root`` is given or verify_workflow is the
    source of truth. When verify_workflow cannot be loaded (defensive), falls
    back to ``<root>/.governance/flow-unit-runtime.json``. Returns None when
    neither root nor verify_workflow can resolve a path. Never raises.
    """
    if root is not None:
        # Explicit host root: prefer verify_workflow's path constant for shape
        # consistency, but compute directly so we never depend on the deferred
        # import for a caller-supplied root (tests pass a tmpdir root).
        return Path(root) / ".governance" / "flow-unit-runtime.json"
    try:
        vw = _vw()
        return Path(vw._flow_unit_runtime_path(None))
    except Exception:  # pragma: no cover - defensive (vw loader shape changed)
        return None


def _load_runtime(runtime_path):
    """Load the runtime payload from ``runtime_path`` (None if missing/corrupt)."""
    if runtime_path is None:
        return None
    path = Path(runtime_path) if not isinstance(runtime_path, Path) else runtime_path
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None


def _find_unit(payload, unit_id):
    """Return the unit dict for ``unit_id`` or None (fail-closed)."""
    if not isinstance(payload, dict):
        return None
    flow_units = payload.get("flow_units")
    if not isinstance(flow_units, list):
        return None
    for unit in flow_units:
        if isinstance(unit, dict) and unit.get("flow_unit_id") == unit_id:
            return unit
    return None


def _loop_state_of(unit):
    ls = unit.get("loop_state")
    return ls if isinstance(ls, dict) else {}


def _gate_state_of(unit):
    gs = unit.get("gate_state")
    return gs if isinstance(gs, dict) else {}


def _fuse_max_rounds(unit):
    """Return the unit's ``fuse.max_rounds`` (int) or None if absent/non-int."""
    fuse = _loop_state_of(unit).get("fuse")
    if not isinstance(fuse, dict):
        return None
    mr = fuse.get("max_rounds")
    if isinstance(mr, bool):
        return None
    if isinstance(mr, int):
        return mr
    return None


def _round_evidence_of(unit):
    """Return the unit's ``loop_state.round_evidence`` list (empty if absent).

    Round-evidence rows (``LOOP-{U}-{T}-R{n}`` strings) are the additive
    FEAT-006 representation that the pure :func:`loop_engine.derive_round`
    re-derives from. Stored under ``loop_state.round_evidence`` (a list of
    strings) — an additive field the 0.67.0 validator tolerates (it only checks
    the 9 canonical fields are *present*, not that no extras exist).
    """
    re_rows = _loop_state_of(unit).get("round_evidence")
    return list(re_rows) if isinstance(re_rows, list) else []


# ═══════════════════════════════════════════════════════════════════════════
# Registry lookups (§4.1 step 2)
# ═══════════════════════════════════════════════════════════════════════════


def _gate_semantics(gate_id, plugin_home):
    """Return ``(tier, on_fail, fuse_ref, issue)`` for ``gate_id``.

    Reads ``registry.loop_gate_semantics[gate_id]``. ``tier`` is the
    ``enclosing_loop`` (the loop this gate certifies); ``on_fail`` is
    ``iterate-enclosing-loop`` | ``escalate-directly``; ``fuse_ref`` is the
    fuse id (e.g. ``FUSE-INNER-DEFAULT``) or ``"none"`` for G1.

    Returns ``issue`` (a non-empty string) on any lookup failure — the caller
    fail-closes (no silent iteration/escalation when the registry semantics are
    unreadable). Never raises.
    """
    if not isinstance(gate_id, str) or not gate_id.strip():
        return None, None, None, "gate_id must be a non-empty string"
    sem = loop_engine.get_loop_gate_semantics(gate_id, plugin_home=plugin_home)
    if not isinstance(sem, dict):
        return None, None, None, (
            "gate_semantics for {0!r} not found in registry (fail-closed)".format(gate_id)
        )
    tier = sem.get("enclosing_loop")
    on_fail = sem.get("on_fail")
    fuse_ref = sem.get("fuse_ref")
    if not isinstance(tier, str) or not isinstance(on_fail, str):
        return None, None, None, (
            "gate_semantics for {0!r} malformed (enclosing_loop/on_fail missing)".format(gate_id)
        )
    return tier, on_fail, fuse_ref, None


def _fuse_max_rounds_from_registry(fuse_ref, plugin_home):
    """Return the registry ``max_rounds`` for ``fuse_ref`` (int) or None.

    Reads ``registry.loop_fuses[fuse_ref].max_rounds``. Returns None when the
    fuse_ref is ``"none"`` or the fuse is absent/corrupt — the caller then
    falls back to the unit's own ``fuse.max_rounds`` (populated at activation).
    Never raises.
    """
    if not isinstance(fuse_ref, str) or fuse_ref == "none" or not fuse_ref.strip():
        return None
    fuse = loop_engine.get_fuse(fuse_ref, plugin_home=plugin_home)
    if not isinstance(fuse, dict):
        return None
    mr = fuse.get("max_rounds")
    if isinstance(mr, bool):
        return None
    if isinstance(mr, int):
        return mr
    return None


# ═══════════════════════════════════════════════════════════════════════════
# process_gate_result — the §4.1 gate/review terminal processor
# ═══════════════════════════════════════════════════════════════════════════


def process_gate_result(
    unit_id,
    gate_id,
    result,
    *,
    evidence_ref,
    actor,
    root=None,
    plugin_home=None,
    runtime_file=None,
    max_retries=0,
    event_log=None,
    event_log_path=None,
):
    """Process a flow-unit gate result and drive the PARO state machine (§4.1).

    This is the AUDIT-133 fix: the single bridge from "a real gate event
    happened" to "the loop state machine advanced." It maps the result to
    ``iterate`` | ``exit`` | ``escalate``, drives the FEAT-005 CAS writer
    (:func:`loop_paro_engine.apply_transition`) so the back-edge + round
    increment are atomic, and returns a :class:`GateOutcome`.

    Algorithm (ADR-014 §4.1):

      1. LOAD the unit (CAS read); assert ``runtime_status == "active"``.
      2. LOOKUP ``gate_semantics`` (tier / on_fail / fuse_ref) and the fuse
         ``max_rounds`` from the registry.
      3. MAP ``result`` → {passed, failed, blocked}.
      4. UNIFY: the last result is written to both ``gate_state.last_result``
         and ``loop_state.last_gate_result`` (the 0.67.0 invariant) by the
         FEAT-005 side-effects; the mapped status sets ``gate_state.status``.
      5. DECIDE: passed → exit; blocked → escalate (runtime blocked);
         failed → ``new_loop_count = loop_count + 1``; if
         ``new_loop_count > max_rounds`` → fuse trip (escalate); else iterate
         (back-edge: ``reflect → plan``). ``on_fail == "escalate-directly"``
         (G1) → escalate.
      6. CAS-WRITE via :func:`apply_transition` (the FEAT-005 CAS writer). The
         transition must be legal per the §3.2 table.
      7. RETURN :class:`GateOutcome`.

    Args:
        unit_id: the flow_unit_id whose gate ran.
        gate_id: G1..G11 (the gate that produced the result).
        result: the raw review/gate conclusion (``"APPROVED"`` /
            ``"APPROVED_WITH_NOTES"`` / ``"NEEDS_CHANGE"`` / ``"BLOCKED"`` / …),
            or the canonical mapped status (``"passed"`` / ``"failed"`` /
            ``"blocked"``).
        evidence_ref: pointer to the review/gate evidence (review-*.md path or
            evidence-log row). Appended to ``gate_state.evidence_refs``.
        actor: who/what produced this (reviewer id, agent id, gate engine).
        root: host project root (RISK-040: resolved via the runtime path; never
            PLUGIN_HOME). When ``runtime_file`` is also given, ``runtime_file``
            wins. When neither is given, the runtime path is resolved via
            verify_workflow's ``_flow_unit_runtime_path``.
        plugin_home: optional plugin-home override forwarded to registry reads.
        runtime_file: explicit path to ``flow-unit-runtime.json`` (used by
            tests; takes precedence over ``root``).
        max_retries: CAS retry budget on CONFLICT (forwarded to
            :func:`apply_transition`). Default 0 = fail-closed on first
            conflict.
        event_log: FEAT-007 hook. Accepts None (skip append — FEAT-006 default,
            events still returned in :attr:`GateOutcome.events`), True
            (default log path under the runtime file's host root), a str/Path
            (explicit log path), or a callable (custom sink). When provided,
            the gate_result / back_edge / fuse_trip / loop_exit / unit_blocked
            events are appended to the audit log AFTER the CAS write commits
            (state-first/event-second ordering, §5.2 point 3). Best-effort: a
            lost event is recoverable via §3.5 phase_recovery.
        event_log_path: DEPRECATED alias for passing a path via ``event_log``.

    Returns:
        GateOutcome. Never raises — all failure modes (unit not active,
        registry unreadable, illegal transition, CAS conflict, I/O error) are
        reported via ``outcome.status`` / ``outcome.reason``. The CAS write
        commits ONLY on ``status == "success"``; on every other status the unit
        is unchanged.
    """
    # ── Resolve the runtime file (root vs explicit path). ────────────────────
    if runtime_file is not None:
        runtime_path = Path(runtime_file)
    else:
        runtime_path = _runtime_path(root)
        if runtime_path is None:
            return GateOutcome(
                unit_id=unit_id, decision=DECISION_ESCALATE,
                status=loop_paro_engine.STATUS_ERROR,
                reason="could not resolve flow-unit-runtime.json path (no root/runtime_file)",
            )

    events = []

    # ── Step 1: LOAD + assert active. ────────────────────────────────────────
    payload = _load_runtime(runtime_path)
    if not isinstance(payload, dict):
        return GateOutcome(
            unit_id=unit_id, decision=DECISION_ESCALATE,
            status=loop_paro_engine.STATUS_ERROR,
            reason="runtime file missing or corrupt: {0}".format(runtime_path),
            events=events,
        )
    # v1 / non-v2 payloads are a no-op (§6.5: process_gate_result does not break
    # classic/dynamic installations). A missing/incorrect schema_version means
    # the host is not on the v2 contract — return without mutating.
    schema_version = payload.get("schema_version")
    if schema_version != "2.0":
        return GateOutcome(
            unit_id=unit_id, decision=DECISION_EXIT,
            status=loop_paro_engine.STATUS_ILLEGAL,
            reason=(
                "schema_version {0!r} is not v2 ('2.0'); process_gate_result is "
                "a no-op for v1/classic installations".format(schema_version)
            ),
            events=events,
        )

    unit = _find_unit(payload, unit_id)
    if unit is None:
        return GateOutcome(
            unit_id=unit_id, decision=DECISION_ESCALATE,
            status=loop_paro_engine.STATUS_ERROR,
            reason="flow_unit_id {0!r} not found in runtime file".format(unit_id),
            events=events,
        )
    if unit.get("runtime_status") != "active":
        return GateOutcome(
            unit_id=unit_id, decision=DECISION_ESCALATE,
            status=loop_paro_engine.STATUS_ILLEGAL,
            reason=(
                "unit {0!r} runtime_status is {1!r}, not 'active' (dormant units "
                "have no gate events; activate first)".format(
                    unit_id, unit.get("runtime_status"))
            ),
            events=events,
        )

    # ── Step 2: LOOKUP gate_semantics + fuse. ────────────────────────────────
    tier, on_fail, fuse_ref, sem_issue = _gate_semantics(gate_id, plugin_home)
    if sem_issue:
        return GateOutcome(
            unit_id=unit_id, decision=DECISION_ESCALATE,
            status=loop_paro_engine.STATUS_ERROR, reason=sem_issue, events=events,
        )

    # max_rounds: the unit's own ``loop_state.fuse.max_rounds`` is the
    # AUTHORITATIVE per-unit threshold — it is populated from the registry fuse
    # at activation (:func:`loop_paro_engine.activate_unit` writes the tier's
    # registry ``max_rounds`` into the unit's ``fuse``). This makes the unit's
    # persisted state the single source of truth for the fuse boundary
    # (consistent with ``loop_state.fuse`` being the persisted CAS-versioned
    # state) and keeps the boundary aligned with the FEAT-005 ESCALATE
    # validator (which reads the same per-unit ``fuse.max_rounds``). We fall
    # back to the registry fuse only when the unit's value is missing (defensive
    # — should not happen post-activation). ADR §4.4: "the fuse trips when
    # loop_count > fuse.max_rounds (per tier, from the registry)" — the
    # registry value is captured into the unit at activation, so reading the
    # unit reads the registry value as of activation.
    max_rounds = _fuse_max_rounds(unit)
    if max_rounds is None:
        max_rounds = _fuse_max_rounds_from_registry(fuse_ref, plugin_home)
    if max_rounds is None:
        return GateOutcome(
            unit_id=unit_id, decision=DECISION_ESCALATE,
            status=loop_paro_engine.STATUS_ERROR,
            reason=(
                "cannot resolve max_rounds: unit fuse.max_rounds missing and "
                "registry fuse_ref {0!r} unreadable (fail-closed)".format(fuse_ref)
            ),
            events=events,
        )

    # ── Step 3: MAP result → {passed, failed, blocked}. ──────────────────────
    mapped = _map_result(result)

    # Current loop_count (BEFORE transition) and from_phase for context.
    loop_count = _loop_state_of(unit).get("loop_count", 0)
    if isinstance(loop_count, bool) or not isinstance(loop_count, int):
        loop_count = 0
    from_phase = _loop_state_of(unit).get("agent_phase")

    # ── Step 4 + 5: UNIFY + DECIDE (build the transition target + event). ────
    # The actual UNIFY (last_gate_result == gate_state.last_result) is applied
    # by FEAT-005's side-effects inside apply_transition; here we only compute
    # the target phase, the gate_result string to record, and the events.
    new_loop_count = loop_count + 1  # the would-be round on iterate/escalate.

    # The gate_result string recorded on loop_state.last_gate_result /
    # gate_state.last_result. Use the raw review conclusion when it is a string
    # (so the evidence trail shows "NEEDS_CHANGE"), else the mapped status.
    recorded_result = result if isinstance(result, str) and result.strip() else mapped

    if mapped == _MAPPED_PASSED:
        decision = DECISION_EXIT
        target_phase = EXIT
        terminal_override = None
        fuse_tripped = False
        escalation = None
        events.append(_event(
            unit_id, "gate_result", gate_id, tier, actor, evidence_ref,
            cas_version=None, payload={"result": result, "mapped_status": mapped},
        ))
        events.append(_event(
            unit_id, "loop_exit", gate_id, tier, actor, evidence_ref,
            cas_version=None, payload={"tier": tier, "final_loop_count": loop_count},
        ))
    elif mapped == _MAPPED_BLOCKED:
        # Operator/gate BLOCKED (not fuse): escalate to runtime blocked. §4.1
        # says runtime_status=blocked, NOT withdrawn. The FEAT-005 ESCALATE
        # terminal hardwires fuse.tripped=true AND requires loop_count >
        # max_rounds, neither of which holds for an operator/gate block. We
        # therefore drive the WITHDRAWN terminal (legal from any phase, no fuse
        # facts required) and OVERRIDE runtime_status→"blocked" +
        # gate_state.status→"blocked" in the side_effects callback, keeping
        # fuse.tripped=False. The side_effects override is what distinguishes
        # "operator/gate blocked" from a real fuse trip.
        decision = DECISION_ESCALATE
        target_phase = WITHDRAWN
        terminal_override = "blocked"  # override withdrawn→blocked
        fuse_tripped = False
        escalation = None
        events.append(_event(
            unit_id, "gate_result", gate_id, tier, actor, evidence_ref,
            cas_version=None, payload={"result": result, "mapped_status": mapped},
        ))
        events.append(_event(
            unit_id, "unit_blocked", gate_id, tier, actor, evidence_ref,
            cas_version=None, payload={"reason": "gate BLOCKED (operator/gate)"},
        ))
    else:
        # mapped == FAILED. The G1 "escalate-directly" path takes precedence
        # over the iterate-vs-fuse decision (§4.1 step 5 last branch). G1 is
        # the initiation gate whose enclosing_loop is "none" — a failed G1
        # cannot iterate (there is no enclosing loop to iterate), so it
        # escalates directly. Same WITHDRAWN+override discipline as BLOCKED:
        # the ESCALATE terminal's fuse-trip + exhaustion requirements do not
        # apply to a direct escalation, so we drive WITHDRAWN and override to
        # "blocked" without tripping the fuse.
        if on_fail == "escalate-directly":
            decision = DECISION_ESCALATE
            target_phase = WITHDRAWN
            terminal_override = "blocked"
            fuse_tripped = False
            escalation = None
            events.append(_event(
                unit_id, "gate_result", gate_id, tier, actor, evidence_ref,
                cas_version=None, payload={"result": result, "mapped_status": mapped},
            ))
            events.append(_event(
                unit_id, "unit_blocked", gate_id, tier, actor, evidence_ref,
                cas_version=None,
                payload={"reason": "gate on_fail=escalate-directly (G1)"},
            ))
        elif loop_count > max_rounds:
            # Fuse trip (loop_count > max_rounds at the reflect node; C5
            # preserved — round == max is still iterate, so the iterate that
            # brought loop_count from max to max+1 was legal, and THIS failure
            # at loop_count > max trips the fuse). The FEAT-005 ESCALATE
            # terminal requires exactly loop_count > max_rounds (strict), so the
            # CAS writer accepts this transition. loop_count is NOT incremented
            # on a fuse trip (FEAT-005 ESCALATE side effects leave it); the
            # round-evidence row is appended ONLY on back-edge (iterate), not
            # on this terminal.
            decision = DECISION_ESCALATE
            target_phase = ESCALATE
            terminal_override = None
            fuse_tripped = True
            escalation = loop_engine.escalation_payload(
                unit_id, tier, new_loop_count, recorded_result, max_rounds,
            )
            events.append(_event(
                unit_id, "gate_result", gate_id, tier, actor, evidence_ref,
                cas_version=None, payload={"result": result, "mapped_status": mapped},
            ))
            events.append(_event(
                unit_id, "fuse_trip", gate_id, tier, actor, evidence_ref,
                cas_version=None,
                payload={
                    "tier": tier, "loop_count": loop_count,
                    "max_rounds": max_rounds,
                    "escalation_exit": (
                        loop_engine.get_fuse(fuse_ref, plugin_home=plugin_home) or {}
                    ).get("escalation_exit"),
                },
            ))
        else:
            # Iterate (back-edge): reflect → plan, loop_count += 1.
            decision = DECISION_ITERATE
            target_phase = PLAN
            terminal_override = None
            fuse_tripped = False
            escalation = None
            events.append(_event(
                unit_id, "gate_result", gate_id, tier, actor, evidence_ref,
                cas_version=None, payload={"result": result, "mapped_status": mapped},
            ))
            events.append(_event(
                unit_id, "back_edge", gate_id, tier, actor, evidence_ref,
                cas_version=None,
                payload={
                    "from_phase": from_phase, "to_phase": PLAN,
                    "tier": tier, "new_loop_count": new_loop_count,
                },
            ))

    # ── Step 6: CAS-WRITE via apply_transition (the FEAT-005 CAS writer). ────
    # Build the event dict the FEAT-005 validator needs for the
    # reflect→{exit, plan, escalate} branch (gate_result + fuse facts).
    transition_event = {
        "gate_result": recorded_result,
        "loop_count": loop_count,
        "max_rounds": max_rounds,
        "reason": "process_gate_result:{0}".format(mapped),
    }

    # The side_effects callback applies the FEAT-006-specific mutations INSIDE
    # the atomic CAS write (§4.2 back-edge atomicity):
    #   - append evidence_ref to gate_state.evidence_refs
    #   - on iterate/escalate-via-fuse: append the LOOP-{U}-{T}-R{n} round row
    #     to loop_state.round_evidence (the §4.3 dual representation)
    # All mutations share the single cas_version bump apply_transition applies.
    capture = {"new_unit": None}

    def _side_effects(new_unit, ev):
        # 4(a): gate_state.evidence_refs append (the evidence pointer).
        gs = _gate_state_of(new_unit)
        if isinstance(gs, dict):
            refs = gs.get("evidence_refs")
            if not isinstance(refs, list):
                refs = []
            if evidence_ref is not None and evidence_ref not in refs:
                refs.append(evidence_ref)
            gs["evidence_refs"] = refs
            # 4(b): gate_state.status ← mapped status (passed/failed/blocked).
            gs["status"] = _gate_status_for(mapped, decision)

        # terminal_override: for operator/gate BLOCKED and G1 escalate-directly
        # we drove the WITHDRAWN terminal (legal from any phase, no fuse facts
        # required) but the §4.1 semantics want runtime_status="blocked", NOT
        # "withdrawn". Override both fields here, and explicitly clear
        # fuse.tripped (WITHDRAWN does not trip it, but we are defensive). The
        # WITHDRAWN terminal also does NOT sync last_gate_result/last_result, so
        # we sync them here to preserve the 0.67.0 unification invariant
        # (§3.6: never write one without the other).
        if terminal_override is not None:
            new_unit["runtime_status"] = terminal_override
            if isinstance(gs, dict):
                gs["status"] = terminal_override
                gs["last_result"] = recorded_result
            ls_ov = _loop_state_of(new_unit)
            ls_ov["last_gate_result"] = recorded_result
            fuse_ov = ls_ov.get("fuse")
            if isinstance(fuse_ov, dict):
                fuse_ov["tripped"] = bool(fuse_tripped)

        # §4.3 dual representation: on iterate (back-edge) append the round row
        # so the pure derive_round re-derives loop_state.loop_count. A fuse trip
        # is terminal and does NOT write a new round row (the iterate that
        # pushed loop_count past max already wrote its row; derive_round and
        # loop_count agree at the trip because both reflect that last iterate).
        if decision == DECISION_ITERATE:
            ls = _loop_state_of(new_unit)
            rows = ls.get("round_evidence")
            if not isinstance(rows, list):
                rows = []
            row = "LOOP-{0}-{1}-R{2}".format(unit_id, tier, new_loop_count)
            if row not in rows:
                rows.append(row)
            ls["round_evidence"] = rows

        capture["new_unit"] = new_unit
        return new_unit

    transition = loop_paro_engine.apply_transition(
        unit_id, target_phase, transition_event,
        runtime_file=runtime_path,
        side_effects=_side_effects,
        max_retries=max_retries,
    )

    # ── Step 7: build + return GateOutcome. ──────────────────────────────────
    if transition.success:
        committed_unit = capture["new_unit"] if isinstance(capture["new_unit"], dict) else transition.unit
        committed_cas = transition.new_cas_version
        # Stamp the committed cas_version onto every collected event (FEAT-007
        # will write them with this version).
        for ev in events:
            ev["cas_version"] = committed_cas
            ev["from_version"] = transition.from_cas_version
        # ── FEAT-007: state-first/event-second (ADR-014 §5.2 point 3). ───────
        # The CAS write committed (above); now append the FEAT-006 gate events
        # to the audit log. The events were NOT passed to apply_transition
        # (FEAT-006 owns the gate/back_edge/fuse_trip/loop_exit/unit_blocked
        # events; FEAT-005's writer would double-record a bare back_edge).
        # Best-effort: a lost event is recoverable via the §3.5 phase_recovery
        # path; it does NOT roll back the committed state.
        if events:
            _append_gate_events(
                events, event_log=event_log, event_log_path=event_log_path,
                runtime_path=runtime_path, actor=actor,
            )
        # new_agent_phase / new_loop_count from the committed unit (authoritative).
        final_phase = _loop_state_of(committed_unit).get("agent_phase") if committed_unit else target_phase
        final_count = _loop_state_of(committed_unit).get("loop_count") if committed_unit else None
        return GateOutcome(
            unit_id=unit_id, decision=decision, new_agent_phase=final_phase,
            new_loop_count=final_count, fuse_tripped=fuse_tripped,
            escalation_payload=escalation, cas_version=committed_cas,
            events=events, status=loop_paro_engine.STATUS_SUCCESS,
            reason="gate {0} {1} → {2}".format(gate_id, mapped, decision),
            mapped_status=mapped,
        )

    # Non-success: illegal / conflict / error. No state mutation, no events stamped.
    return GateOutcome(
        unit_id=unit_id, decision=decision, new_agent_phase=None,
        new_loop_count=None, fuse_tripped=fuse_tripped,
        escalation_payload=escalation, cas_version=None,
        events=events, status=transition.status, reason=transition.reason,
        mapped_status=mapped,
    )


def _gate_status_for(mapped, decision):
    """Map the (mapped_status, decision) pair to a gate_state.status value.

    passed → "passed"; failed+iterate → "failed"; failed+escalate(fuse) →
    "blocked"; blocked → "blocked". Stays within the contract's
    ``allowed_gate_statuses`` enum.
    """
    if mapped == _MAPPED_PASSED:
        return "passed"
    if mapped == _MAPPED_BLOCKED:
        return "blocked"
    # failed.
    if decision == DECISION_ITERATE:
        return "failed"
    return "blocked"  # escalate via fuse or escalate-directly.


def _event(unit_id, event_type, gate_id, tier, actor, evidence_ref, *,
           cas_version, payload, from_phase=None, to_phase=None, from_version=None):
    """Build one event dict for the GateOutcome.events list (§5.1 envelope).

    Includes all loop_event_log.REQUIRED_FIELDS so the event passes
    validate_event. ``from_phase``/``to_phase`` describe the PARO phase
    transition this event represents (e.g. back_edge: reflect→plan).
    """
    import uuid
    from datetime import datetime, timezone
    ev = {
        "event_id": "evt-" + uuid.uuid4().hex[:16],
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "unit_id": unit_id,
        "event_type": event_type,
        "gate_id": gate_id,
        "tier": tier,
        "actor": actor,
        "evidence_ref": evidence_ref,
        "cas_version": cas_version,
        "from_version": from_version,
        "from_phase": from_phase,
        "to_phase": to_phase,
        "payload": payload if isinstance(payload, dict) else {},
    }
    return ev


def _append_gate_events(events, *, event_log, event_log_path, runtime_path, actor):
    """Append FEAT-006 gate events to the FEAT-007 log (state-first/event-second).

    Best-effort: invoked AFTER the CAS write committed (§5.2 point 3). A lost
    event is recoverable via the §3.5 phase_recovery path on restart; it does
    NOT roll back the committed state. Never raises.

    Accepts the same ``event_log`` shapes as
    :func:`loop_paro_engine.apply_transition`:
      - None → skip (FEAT-006 default; events are still returned in GateOutcome).
      - True → the default log path under the runtime file's host root.
      - a str/Path → that explicit path.
      - a callable → custom sink (one event dict per call).
    """
    if not events:
        return
    # Resolve the sink.
    sink = None
    if event_log is None and event_log_path is None:
        return
    if callable(event_log):
        sink = event_log
    else:
        try:
            import loop_event_log  # deferred: FEAT-007 peer module
        except Exception:  # pragma: no cover - defensive
            return
        if event_log is True:
            host_root = Path(runtime_path).resolve().parent
            log_path = host_root / loop_event_log.EVENT_LOG_FILENAME
        elif isinstance(event_log, (str, Path)):
            log_path = Path(event_log)
        elif event_log_path is not None:
            log_path = Path(event_log_path)
        else:
            return

        def _sink(ev):
            loop_event_log.append_event(ev, log_path=log_path)
        sink = _sink

    for ev in events:
        # Ensure generated-default fields (event_id/timestamp) are present.
        if not ev.get("event_id") or not ev.get("timestamp"):
            try:
                import loop_event_log as _lel
                if not ev.get("event_id"):
                    ev["event_id"] = _lel.new_event_id()
                if not ev.get("timestamp"):
                    ev["timestamp"] = _lel.now_timestamp()
            except Exception:  # pragma: no cover - defensive
                pass
        try:
            sink(ev)
        except Exception:  # pragma: no cover - best-effort; never roll back state
            return


# ═══════════════════════════════════════════════════════════════════════════
# loop_fuse_check — the §4.4 system-level block (PURE READ)
# ═══════════════════════════════════════════════════════════════════════════


def loop_fuse_check(root=None, *, plugin_home=None, runtime_file=None):
    """Return the list of UNRESOLVED tripped fuses (§4.4, the system-level block).

    PURE READ — this function MUST NOT mutate state. It scans
    ``flow-unit-runtime.json`` for units with ``loop_state.fuse.tripped == true``
    AND ``runtime_status in {"blocked", "escalated"}`` (the unresolved set). A
    fuse that has been resolved (``runtime_status`` moved to ``withdrawn`` or
    the unit re-activated) is NOT returned. This is the function the
    release/governance gate calls — the load-bearing "不依赖 Coordinator 自觉"
    guarantee: a tripped, unresolved fuse blocks the release/gate.

    Args:
        root: host project root (RISK-040). When ``runtime_file`` is given it
            takes precedence; when neither is given the runtime path is
            resolved via verify_workflow's ``_flow_unit_runtime_path``.
        plugin_home: accepted for symmetry with the other loop functions; the
            fuse check is runtime-only and does not read the registry, so this
            is currently unused but kept for API consistency.
        runtime_file: explicit path to ``flow-unit-runtime.json`` (tests).

    Returns:
        list of dicts, one per unresolved tripped fuse, each:
        ``{unit_id, loop_count, max_rounds, tier, runtime_status}``. Empty list
        when there are no tripped fuses, when the runtime file is missing, or
        when every tripped fuse has been resolved. Never raises.
    """
    if runtime_file is not None:
        runtime_path = Path(runtime_file)
    else:
        runtime_path = _runtime_path(root)
        if runtime_path is None:
            return []
    payload = _load_runtime(runtime_path)
    if not isinstance(payload, dict):
        return []
    # v1 / non-v2 payloads have no per-unit fuse state — empty result.
    if payload.get("schema_version") != "2.0":
        return []
    flow_units = payload.get("flow_units")
    if not isinstance(flow_units, list):
        return []

    unresolved = []
    blocking_statuses = {"blocked", "escalated"}
    for unit in flow_units:
        if not isinstance(unit, dict):
            continue
        runtime_status = unit.get("runtime_status")
        if runtime_status not in blocking_statuses:
            continue
        ls = _loop_state_of(unit)
        fuse = ls.get("fuse")
        if not isinstance(fuse, dict):
            continue
        if not bool(fuse.get("tripped", False)):
            continue
        loop_count = ls.get("loop_count", 0)
        if isinstance(loop_count, bool) or not isinstance(loop_count, int):
            loop_count = 0
        max_rounds = fuse.get("max_rounds")
        if isinstance(max_rounds, bool) or not isinstance(max_rounds, int):
            max_rounds = None
        unresolved.append({
            "unit_id": unit.get("flow_unit_id"),
            "loop_count": loop_count,
            "max_rounds": max_rounds,
            "tier": ls.get("active_loop_tier"),
            "runtime_status": runtime_status,
        })
    return unresolved


def collect_loop_fuse_issues(root=None, *, plugin_home=None, runtime_file=None):
    """Return one release-gate issue string per unresolved tripped fuse (§6.3).

    The system-level block wiring (§6.3) — the load-bearing "不依赖 Coordinator
    自觉" guarantee. This is the helper the release/governance gate calls: it
    invokes :func:`loop_fuse_check` (the PURE READ) and formats each unresolved
    tripped fuse as a specific per-unit issue string suitable for appending to a
    gate's ``issues`` list. A non-empty return list fails the gate closed.

    This is a THIN wrapper over :func:`loop_fuse_check` — no new logic, no
    mutation. The release-gate wiring in ``verify_workflow.check_release_readiness``
    calls this (an invocation, per RISK-039 thin-entry discipline).

    Args:
        root: host project root (RISK-040). Forwarded to :func:`loop_fuse_check`.
        plugin_home: accepted for symmetry; forwarded to :func:`loop_fuse_check`.
        runtime_file: explicit path to ``flow-unit-runtime.json`` (tests).

    Returns:
        list[str]: one issue per unresolved tripped fuse, each naming the unit,
        the round at which the fuse tripped, the max, and the tier. Empty when
        there are no unresolved tripped fuses (the release-gate passes this
        check). Never raises.
    """
    tripped = loop_fuse_check(
        root=root, plugin_home=plugin_home, runtime_file=runtime_file)
    issues = []
    for u in tripped:
        issues.append(
            "loop fuse: unit {0} tripped at round {1} (max {2}, tier {3}); "
            "unresolved ({4}) — release blocked. Resolve via escalation "
            "(human arbitration / split / degraded / withdraw).".format(
                u.get("unit_id"), u.get("loop_count"), u.get("max_rounds"),
                u.get("tier"), u.get("runtime_status"),
            )
        )
    return issues


__all__ = [
    "GateOutcome",
    "process_gate_result",
    "loop_fuse_check",
    "collect_loop_fuse_issues",
    "DECISION_ITERATE", "DECISION_EXIT", "DECISION_ESCALATE",
    "PLAN", "ACT", "OBSERVE", "REFLECT", "EXIT", "ESCALATE", "WITHDRAWN",
]


if __name__ == "__main__":  # pragma: no cover - manual smoke
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    # Tiny smoke of loop_fuse_check (pure read) against the host runtime if any.
    tripped = loop_fuse_check()
    if not tripped:
        print("loop_fuse_check: no unresolved tripped fuses")
    else:
        for u in tripped:
            print("TRIPPED: {0} (round {1}/{2}, tier {3}, status {4})".format(
                u["unit_id"], u["loop_count"], u["max_rounds"],
                u["tier"], u["runtime_status"],
            ))
