#!/usr/bin/env python3
"""
Loop-engineering registry loader + round/fuse/loop_state engine.

Two additive slices live in this module:

  - **FX-188 (0.65.0 slice 1)** — read-only loader for
    ``core/loop-engineering-registry.json``. Declares and exposes the loop
    topology / fuse / pause-point schema. Does NOT activate any runtime loop
    behavior, does NOT modify gate judgment, and does NOT auto-fire any
    back-edge.
  - **FX-189 (0.65.0 slice 2)** — stateless round derivation + fuse
    generalization + loop_state activation. Adds four functions on top of the
    FX-188 loader: :func:`derive_round` (SACRED pure function), :func:`fuse_decision`,
    :func:`escalation_payload`, and :func:`activate_loop_state`.
  - **FX-193 (0.65.0 slice 6)** — plan-tracker rollup view. Adds
    :func:`rollup_loop_state`, a PURE READ that produces a per-flow-unit
    loop_state decomposition (resolving RISK-037 criterion 2: the
    plan-tracker's single ``当前阶段`` field is replaced by a per-unit view).
    Reads flow-unit-runtime.json via a deferred verify_workflow import
    (``_vw()`` pattern, same as loop_health.py). Load-bearing invariant:
    ``no_global_stage: True`` is ALWAYS set — the result contains no field
    that collapses multiple units into one stage.
  - **FEAT-044 (0.88.0 slice E3)** — subagent round budget + heartbeat
    reporting + interrupt-recovery productization. Adds
    :func:`resolve_round_budget` (parametrized per-round length/cost budgets),
    :func:`evaluate_round_budget`, :func:`heartbeat_should_fire`,
    :func:`heartbeat_payload` (the N-idle-rounds REPORT), and
    :func:`interrupt_recovery_payload` (the productized FIX-357/359 recovery
    move: interrupt + minimal instruction injection). All PURE; all
    REPORT-only — nothing here terminates an execution body (FEAT-063
    alignment: a heartbeat is not a stop proof).

**Why a separate module (not folded into verify_workflow.py):**

  - The loader must be importable without pulling in verify_workflow.py
    (avoid the import cycle, and keep this cheap for read-only consumers).
    This mirrors resolve_entry.py's "MUST NOT import verify_workflow.py"
    constraint.
  - Fail-closed contract is identical to ``_load_lifecycle_registry`` in
    verify_workflow.py: missing/corrupt JSON returns ``(None, [diagnostic])``
    and never raises.

**Sacred property — derive_round is stateless and parallel-safe (ADR §8.2):**

  :func:`derive_round` is a PURE function. It holds no module-level mutable
  state, no counter, no result cache that could accumulate across calls. Two
  calls (or N concurrent calls) with the same arguments MUST return the same
  value. The 4-step parallel-safety test in
  ``tests/test_loop_engine_round.py`` is load-bearing proof of this property.
  A buggy implementation that used a shared mutable counter would diverge or
  race under concurrency; the test fails on such an implementation.

**Anchors (same as resolve_entry.py line 45):**

  PLUGIN_HOME = Path(__file__).resolve().parent.parent
              (= skills/software-project-governance/, where SKILL.md lives)

The registry file lives at ``PLUGIN_HOME / "core/loop-engineering-registry.json"``.

Usage:
    from loop_engine import load_loop_registry, get_loop_gate_semantics

    data, issues = load_loop_registry()
    if data is None:
        # issues explains why; fail-closed — never raises.
        ...
    g6 = get_loop_gate_semantics("G6")

    # FX-189 additions:
    from loop_engine import derive_round, fuse_decision, escalation_payload, activate_loop_state

    current_round = derive_round("game.chapter.03", "inner", evidence_text)  # pure
    verdict = fuse_decision("game.chapter.03", "inner", evidence_text)
    if verdict["decision"] == "escalate":
        payload = escalation_payload(
            "game.chapter.03", "inner", verdict["current_round"], "BLOCKED", verdict["max_rounds"]
        )

    # FEAT-044 additions (0.88.0 E3):
    from loop_engine import (
        resolve_round_budget, evaluate_round_budget, heartbeat_should_fire,
        heartbeat_payload, interrupt_recovery_payload,
    )

    budget, budget_issues = resolve_round_budget("inner", overrides={"max_idle_rounds": 3})
    round_verdict = evaluate_round_budget(budget, steps_used=15, idle_rounds=3)
    if round_verdict["heartbeat_due"]:
        report = heartbeat_payload("unit.x", "inner", idle_rounds=3, budget=budget)
        recovery = interrupt_recovery_payload(
            "unit.x", "inner", reason="heartbeat", idle_rounds=3
        )
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

# ─── Fixed anchors ─────────────────────────────────────────────
# PLUGIN_HOME is derived from __file__ ONLY to locate the plugin's own
# executables and registry files. Same convention as resolve_entry.py.
PLUGIN_HOME = Path(__file__).resolve().parent.parent

# Relative path (from PLUGIN_HOME) to the loop-engineering registry.
_LOOP_REGISTRY_REL = "core/loop-engineering-registry.json"


def _loop_registry_path(plugin_home):
    """Resolve the registry path from an (optional) plugin_home override."""
    home = Path(plugin_home) if plugin_home is not None else PLUGIN_HOME
    return home / _LOOP_REGISTRY_REL


def load_loop_registry(plugin_home=None):
    """Load loop-engineering-registry.json.

    Returns ``(data_or_None, issues_list)``. Fail-closed on missing/corrupt:
    a missing file or invalid JSON yields ``(None, [diagnostic_string])``
    and never raises.

    Mirrors the ``_load_lifecycle_registry`` contract in verify_workflow.py.
    """
    registry_path = _loop_registry_path(plugin_home)
    try:
        display = str(registry_path)
    except Exception:  # pragma: no cover - defensive
        display = "<loop-engineering-registry>"
    if not registry_path.exists():
        return None, [f"{display}: missing loop-engineering registry"]
    try:
        text = registry_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [f"{display}: cannot read loop-engineering registry: {exc}"]
    try:
        return json.loads(text), []
    except json.JSONDecodeError as exc:
        return None, [f"{display}: invalid JSON: {exc}"]


def _entry_by_id(entries, key, value):
    """Linear search for ``{key: value}`` in a list of dict entries."""
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if isinstance(entry, dict) and entry.get(key) == value:
            return entry
    return None


def get_loop_gate_semantics(gate_id, plugin_home=None):
    """Return the loop_gate_semantics entry for a gate (G1-G11).

    Returns the matching dict, or ``None`` if the gate id is absent or the
    registry cannot be loaded (fail-closed).
    """
    data, _issues = load_loop_registry(plugin_home)
    if data is None:
        return None
    return _entry_by_id(data.get("loop_gate_semantics"), "gate_id", gate_id)


def get_pause_point(pp_id, plugin_home=None):
    """Return a PausePoint declaration by id.

    Returns the matching dict, or ``None`` if absent or the registry cannot
    be loaded (fail-closed).
    """
    data, _issues = load_loop_registry(plugin_home)
    if data is None:
        return None
    pause_points = data.get("pause_points")
    if not isinstance(pause_points, dict):
        return None
    entry = pause_points.get(pp_id)
    return entry if isinstance(entry, dict) else None


def get_fuse(fuse_id, plugin_home=None):
    """Return a LoopFuse declaration by id.

    Returns the matching dict, or ``None`` if absent or the registry cannot
    be loaded (fail-closed).
    """
    data, _issues = load_loop_registry(plugin_home)
    if data is None:
        return None
    fuses = data.get("loop_fuses")
    if not isinstance(fuses, dict):
        return None
    entry = fuses.get(fuse_id)
    return entry if isinstance(entry, dict) else None


# ═══════════════════════════════════════════════════════════════════════════
# FX-189 — 0.65.0 slice 2: stateless round derivation + fuse generalization
# + loop_state activation.
#
# The four functions below build on the FX-188 loader. They are PURE with
# respect to module state: no module-level mutable counter, no accumulating
# cache. derive_round in particular is the SACRED pure function (ADR §8.2
# "parallel-safe by construction"); its purity is load-bearing and proven by
# the threading test in tests/test_loop_engine_round.py.
# ═══════════════════════════════════════════════════════════════════════════


def _tier_to_fuse_id(tier):
    """Map a loop tier name to its default fuse id.

    ``setup``  -> ``FUSE-SETUP-DEFAULT``
    ``inner``  -> ``FUSE-INNER-DEFAULT``
    ``middle`` -> ``FUSE-MIDDLE-DEFAULT``
    ``outer``  -> ``FUSE-OUTER-DEFAULT``
    """
    return "FUSE-{0}-DEFAULT".format(str(tier).upper())


def derive_round(flow_unit_id, tier, evidence_log):
    """Derive the current loop round for a flow unit / tier from the evidence log.

    SACRED PURE FUNCTION (ADR §8.2 — parallel-safe by construction).

    Derivation rule (ADR §8.1)::

        current_round = max({n | evidence-log has LOOP-{flow_unit_id}-{tier}-R{n}})
        (0 if no matching evidence rows)

    This function holds NO module-level mutable state and caches nothing that
    accumulates across calls. Two calls (or N concurrent calls from separate
    threads) with identical arguments MUST return the same value. The
    ``test_derive_round_stateless_no_accumulation`` and
    ``test_derive_round_parallel_safe`` tests in
    ``tests/test_loop_engine_round.py`` are the load-bearing proof: a buggy
    implementation using a shared mutable counter would diverge or race.

    Args:
        flow_unit_id: Flow unit identifier string, e.g. ``"game.chapter.03"``.
        tier: Loop tier — one of ``{"setup", "inner", "middle", "outer"}``.
        evidence_log: Either a single string (the full evidence-log text) or a
            list/iterable of strings (one evidence row per element). Both
            forms are accepted so callers and tests can pass either shape.

    Returns:
        int: the maximum round number ``n`` for which a row
        ``LOOP-{flow_unit_id}-{tier}-R{n}`` appears, or ``0`` if no match.
        Never raises; non-string inputs are tolerated defensively.
    """
    if not isinstance(flow_unit_id, str) or not isinstance(tier, str):
        return 0
    # Normalize both shapes (single string OR list of row strings) to one text
    # blob. We must NOT accumulate anything in module state.
    if evidence_log is None:
        text = ""
    elif isinstance(evidence_log, str):
        text = evidence_log
    elif isinstance(evidence_log, (list, tuple)):
        text = "\n".join(str(row) for row in evidence_log)
    else:
        # Fall back to str(); never raise on unexpected-but-stringifiable input.
        try:
            text = str(evidence_log)
        except Exception:
            return 0

    # Anchor the row pattern. re.escape the ids so dotted flow-unit ids
    # (e.g. "game.chapter.03") and tier names don't get re-interpreted.
    pattern = r"LOOP-{0}-{1}-R(\d+)".format(
        re.escape(flow_unit_id), re.escape(tier)
    )
    try:
        rounds = [int(m) for m in re.findall(pattern, text)]
    except Exception:  # pragma: no cover - defensive
        return 0
    return max(rounds) if rounds else 0


def fuse_decision(flow_unit_id, tier, evidence_log, plugin_home=None):
    """Decide iterate vs escalate for a flow unit / tier.

    Combines :func:`derive_round` (pure) with the tier's ``max_rounds`` drawn
    from the FX-188 registry (:func:`get_fuse`). Fail-closed: a missing or
    corrupt registry (fuse not found) yields a conservative ``escalate``
    verdict rather than raising.

    Boundary semantics (ADR §4.6 C3 / M7.4 §4.6 C3): with ``max_rounds = M``,
    rounds ``1..M`` iterate (round == max is STILL iterate — one more allowed);
    round ``M+1`` escalates. Equivalently ``escalate if current_round >
    max_rounds else iterate``.

    Args:
        flow_unit_id: Flow unit identifier string.
        tier: Loop tier (``setup|inner|middle|outer``).
        evidence_log: Evidence-log text or list of rows (passed to
            :func:`derive_round`).
        plugin_home: Optional plugin-home override (forwarded to
            :func:`get_fuse`).

    Returns:
        dict with keys:
          - ``decision``: ``"iterate"`` or ``"escalate"``
          - ``current_round``: int (from :func:`derive_round`)
          - ``max_rounds``: int (from registry), or ``-1`` if fuse missing
          - ``remaining``: int (``max_rounds - current_round``), floored at 0
          - ``issue``: present only when the fuse is missing (fail-closed)
    """
    current_round = derive_round(flow_unit_id, tier, evidence_log)
    fuse_id = _tier_to_fuse_id(tier)
    fuse = get_fuse(fuse_id, plugin_home)
    if not isinstance(fuse, dict):
        return {
            "decision": "escalate",
            "current_round": current_round,
            "max_rounds": -1,
            "remaining": 0,
            "issue": "fuse {0} not found".format(fuse_id),
        }
    try:
        max_rounds = int(fuse.get("max_rounds"))
    except (TypeError, ValueError):
        return {
            "decision": "escalate",
            "current_round": current_round,
            "max_rounds": -1,
            "remaining": 0,
            "issue": "fuse {0} max_rounds not an int".format(fuse_id),
        }
    remaining = max(0, max_rounds - current_round)
    decision = "escalate" if current_round > max_rounds else "iterate"
    return {
        "decision": decision,
        "current_round": current_round,
        "max_rounds": max_rounds,
        "remaining": remaining,
    }


def escalation_payload(flow_unit_id, tier, current_round, last_result, max_rounds):
    """Build the AskUserQuestion escalation payload when a loop fuse trips.

    Returns EXACTLY 4 options — the verbatim M7.4 §4.6 C3/C4 choices
    translated to loop-tier context. There is NO "reluctant APPROVED at round
    N+1" 5th path (C5 preserved): once a fuse trips, the loop does NOT grant
    itself one more automatic pass — the human must choose one of the four.

    Args:
        flow_unit_id: Flow unit identifier string.
        tier: Loop tier.
        current_round: The round at which the fuse tripped.
        last_result: Short result string, typically ``"NEEDS_CHANGE"`` or
            ``"BLOCKED"``.
        max_rounds: The tier's max_rounds.

    Returns:
        dict shaped for AskUserQuestion consumption:
          - ``question``: human-readable fuse-trip summary
          - ``options``: list of exactly 4 ``{"label", "description"}`` dicts
    """
    question = (
        "Loop {tier} for flow unit {fuid} tripped fuse at round {cr} "
        "(max {mr}). Last result: {lr}. How to proceed?"
    ).format(
        tier=tier,
        fuid=flow_unit_id,
        cr=current_round,
        mr=max_rounds,
        lr=last_result,
    )
    options = [
        {
            "label": "Human arbitration",
            "description": "用户介入裁决",
        },
        {
            "label": "Split the unit / reduce scope",
            "description": "拆分 flow unit 降低复杂度",
        },
        {
            "label": "Accept degraded",
            "description": "接受降级（degraded evidence，明确不计审查通过）",
        },
        {
            "label": "Withdraw the unit",
            "description": "撤回该 flow unit",
        },
    ]
    return {"question": question, "options": options}


def activate_loop_state(
    flow_unit,
    tier,
    evidence_log=None,
    agent_phase="plan",
    pause_points_active=None,
    last_gate_result=None,
    plugin_home=None,
):
    """Activate the dormant loop_state on a flow unit (ADR §6.2).

    Returns a NEW dict: the input flow unit with its ``loop_state`` populated
    across the 5 new FX-189 fields (``active_loop_tier``, ``agent_phase``,
    ``iteration_within_inner``, ``pause_points_active``, ``last_gate_result``,
    and the nested ``fuse`` object). Does NOT mutate the input — functional
    style. The CALLER (a future FX-191 migration) is responsible for writing
    the result to ``flow-unit-runtime.json``; this function writes no files.

    Preservation rules:
      - ``active_loop`` is forced to ``True`` (we are activating the loop).
      - ``loop_count`` is re-derived from ``evidence_log`` via
        :func:`derive_round` when ``evidence_log`` is provided, otherwise the
        existing ``loop_count`` is preserved (or ``0`` if absent).
      - ``last_loop_type`` is preserved from the existing loop_state (or
        ``None``).

    Fuse population: reads the tier's ``max_rounds`` from the registry. If the
    fuse is missing/corrupt, ``fuse.max_rounds`` falls back to ``-1`` and
    ``fuse.tripped`` is set to ``True`` (fail-closed). When evidence is
    provided and :func:`fuse_decision` says ``escalate``, ``fuse.tripped`` is
    set to ``True``.

    Args:
        flow_unit: dict representing a flow unit. Must have (at minimum) a
            ``"flow_unit_id"`` key; an existing ``"loop_state"`` dict is
            optional and preserved where possible.
        tier: Loop tier (``setup|inner|middle|outer``).
        evidence_log: Optional evidence-log text/list for round derivation.
        agent_phase: One of ``plan|act|observe|reflect`` (ADR §5.1). Defaults
            to ``"plan"``.
        pause_points_active: Optional list of active pause-point ids
            (ADR §5.2). Defaults to ``[]``.
        last_gate_result: The most recent gate result driving
            iterate-vs-escalate (e.g. ``"APPROVED"`` / ``"NEEDS_CHANGE"``).
        plugin_home: Optional plugin-home override forwarded to registry reads.

    Returns:
        A NEW flow_unit dict (shallow copy of the input with ``loop_state``
        replaced by the activated state). The original input is untouched.
    """
    # Defensive: tolerate a missing/non-dict flow_unit by synthesizing one,
    # but never mutate the caller's object.
    if not isinstance(flow_unit, dict):
        flow_unit_id = None
        existing = {}
        base = {}
    else:
        flow_unit_id = flow_unit.get("flow_unit_id")
        # Shallow copy the input so we don't mutate the caller's dict.
        base = dict(flow_unit)
        existing = flow_unit.get("loop_state")
        if not isinstance(existing, dict):
            existing = {}

    # Derive current round (pure) only if evidence is supplied.
    derived_round = None
    if evidence_log is not None and isinstance(flow_unit_id, str):
        derived_round = derive_round(flow_unit_id, tier, evidence_log)

    # Preserve loop_count or use the derived value.
    if derived_round is not None:
        loop_count = derived_round
    else:
        try:
            loop_count = int(existing.get("loop_count", 0))
        except (TypeError, ValueError):
            loop_count = 0

    # Resolve the fuse from the registry (fail-closed).
    fuse_id = _tier_to_fuse_id(tier)
    fuse = get_fuse(fuse_id, plugin_home)
    if isinstance(fuse, dict):
        try:
            max_rounds = int(fuse.get("max_rounds"))
        except (TypeError, ValueError):
            max_rounds = -1
    else:
        max_rounds = -1

    # Determine whether the fuse has tripped.
    tripped = False
    if derived_round is not None:
        # Only apply the round-vs-max test when we actually derived a round
        # AND have a usable max_rounds. A missing fuse (-1) is fail-closed:
        # treat as tripped so the caller surfaces escalation.
        if max_rounds < 0 or derived_round > max_rounds:
            tripped = True
    elif max_rounds < 0:
        # No evidence to derive from, but the fuse itself is missing —
        # fail-closed: flag as tripped so the issue is visible.
        tripped = True

    new_loop_state = {
        "active_loop": True,
        "active_loop_tier": tier,
        "loop_count": loop_count,
        "last_loop_type": existing.get("last_loop_type"),
        "agent_phase": agent_phase,
        "iteration_within_inner": derived_round if derived_round is not None else 0,
        "pause_points_active": list(pause_points_active) if pause_points_active else [],
        "last_gate_result": last_gate_result,
        "fuse": {
            "max_rounds": max_rounds,
            "tripped": tripped,
        },
    }

    base["loop_state"] = new_loop_state
    return base


# ═══════════════════════════════════════════════════════════════════════════
# FEAT-044 — 0.88.0 slice E3: subagent round budget + heartbeat reporting +
# interrupt-recovery productization.
#
# Empirical grounding (EVD-1101① "round delay tax" / plan-tracker candidate
# row): in FIX-357 the Developer subagent's return channel stalled ~15 rounds
# (work was on disk; two interrupts were needed to extract it) and in FIX-359
# the Reviewer ran 16 rounds — governance quality was real but latency
# multiplied 3-5x. This slice productizes the countermeasures as PURE
# functions (same discipline as FX-189): parametrized per-round budgets, an
# N-idle-rounds heartbeat REPORT, and the interrupt + minimal-instruction
# recovery payload.
#
# LOAD-BEARING SEMANTIC ALIGNMENT (FEAT-063, version-plan-0.88.0 E2): a
# heartbeat — and any budget breach — is a REPORT, never a stop proof. Nothing
# here terminates, kills, or withdraws an execution body; the
# interrupt/escalate decision stays with the Coordinator/scheduler (and with
# the tier fuse's human-arbitration path, PP-Fuse-Escalate). FEAT-044 is the
# reporting half; FEAT-063's takeover/fencing consumes the same reports.
# ═══════════════════════════════════════════════════════════════════════════

# Heartbeat threshold N (default): consecutive artifact-less rounds before the
# execution body owes the Coordinator/scheduler a heartbeat REPORT.
# Provenance: FIX-357 (~15-round stall) / FIX-359 (16 rounds) — N=3 surfaces
# such stalls at roughly one fifth of the observed waiting tax while staying
# above single-round noise.
HEARTBEAT_IDLE_ROUNDS_DEFAULT = 3

# The explicit over-budget behavior (hard gate: 超预算行为明确). Advisory by
# design — it RECOMMENDS interrupt-recovery, it never auto-terminates.
OVER_BUDGET_ACTION = "report_heartbeat_recommend_interrupt_recovery"

# Default per-round budget (parametrization baseline). ``max_steps_per_round``
# and ``max_minutes_per_round`` are the two dispatch-facing length/cost
# dimensions; their values are PROVISIONAL initial thresholds — no measured
# in-repo baseline exists yet (W-3 provenance discipline: re-derive from
# measured data before relying on them for enforcement). Every value is
# overridable per call (:func:`resolve_round_budget`) and per tier via the
# registry fuse's optional ``round_budget`` key.
DEFAULT_ROUND_BUDGET = {
    "max_idle_rounds": HEARTBEAT_IDLE_ROUNDS_DEFAULT,
    "max_steps_per_round": 12,
    "max_minutes_per_round": 30,
    "over_budget_action": OVER_BUDGET_ACTION,
}

_BUDGET_INT_KEYS = ("max_idle_rounds", "max_steps_per_round", "max_minutes_per_round")
_BUDGET_ACTION_KEY = "over_budget_action"


@dataclass(frozen=True)
class RoundBudget:
    """A resolved per-round budget for a subagent execution body (FEAT-044).

    Attributes:
        tier: the loop tier this budget was resolved for (or ``None``).
        max_idle_rounds: N — consecutive artifact-less rounds that trigger a
            heartbeat REPORT (see :func:`heartbeat_should_fire`).
        max_steps_per_round: per-round length budget in steps (provisional
            default; parametrized).
        max_minutes_per_round: per-round wall-clock budget in minutes
            (provisional default; parametrized).
        over_budget_action: the explicit over-budget behavior string
            (advisory recommendation; never an auto-termination).
        source: provenance marker — which layer last contributed values:
            ``"defaults"`` | ``"registry"`` | ``"overrides"`` (W-3 lesson:
            numeric gates carry their provenance).
    """

    tier: object
    max_idle_rounds: int
    max_steps_per_round: int
    max_minutes_per_round: int
    over_budget_action: str
    source: str


def _usable_int(value):
    """Return True for a usable budget/usage integer (int, not bool)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_budget_patch(patch, issues, source_label):
    """Validate one budget patch dict; return the valid subset (fail-closed).

    Invalid keys keep their default (the caller merges only the returned
    subset) and append an issue line — never raise, never guess.
    """
    if patch is None:
        return {}
    if not isinstance(patch, dict):
        issues.append("{0}: round budget patch is not a dict — ignored".format(source_label))
        return {}
    valid = {}
    for key, value in patch.items():
        if key in _BUDGET_INT_KEYS:
            if _usable_int(value) and value >= 1:
                valid[key] = value
            else:
                issues.append(
                    "{0}: {1} must be an integer >= 1 (got {2!r}) — default kept".format(
                        source_label, key, value
                    )
                )
        elif key == _BUDGET_ACTION_KEY:
            if isinstance(value, str) and value.strip():
                valid[key] = value
            else:
                issues.append(
                    "{0}: {1} must be a non-empty string (got {2!r}) — default kept".format(
                        source_label, key, value
                    )
                )
        else:
            issues.append(
                "{0}: unknown round-budget key {1!r} ignored".format(source_label, key)
            )
    return valid


def resolve_round_budget(tier=None, *, overrides=None, plugin_home=None):
    """Resolve the per-round budget parameters for a subagent execution body.

    FEAT-044 (0.88.0 E3). Parametrization precedence (lowest → highest):

      1. Module defaults (:data:`DEFAULT_ROUND_BUDGET`).
      2. The tier fuse entry's optional ``round_budget`` key in
         ``core/loop-engineering-registry.json`` (ADDITIVE read — the shipped
         registry carries no such key today; this is a forward-compatible
         config surface, the registry file itself is untouched).
      3. Explicit ``overrides`` (highest; per-call configurability).

    Fail-closed per key: an invalid value keeps the default and appends an
    issue line; this function NEVER raises. ``tier=None`` skips the registry
    layer entirely.

    Returns:
        ``(RoundBudget, issues_list)`` — the same ``(data, issues)`` contract
        as :func:`load_loop_registry`.

    Args:
        tier: loop tier (``setup|inner|middle|outer``) or ``None``.
        overrides: optional dict of budget overrides (validated per key).
        plugin_home: optional plugin-home override forwarded to the registry.
    """
    issues = []
    merged = dict(DEFAULT_ROUND_BUDGET)
    source = "defaults"

    if tier is not None:
        fuse_id = _tier_to_fuse_id(tier)
        fuse = get_fuse(fuse_id, plugin_home)
        if isinstance(fuse, dict):
            patch = _validate_budget_patch(
                fuse.get("round_budget"), issues, "registry {0}".format(fuse_id)
            )
            if patch:
                merged.update(patch)
                source = "registry"
        else:
            issues.append(
                "registry fuse {0} not found — budget resolved from "
                "defaults/overrides only".format(fuse_id)
            )

    patch = _validate_budget_patch(overrides, issues, "overrides")
    if patch:
        merged.update(patch)
        source = "overrides"

    budget = RoundBudget(
        tier=tier,
        max_idle_rounds=merged["max_idle_rounds"],
        max_steps_per_round=merged["max_steps_per_round"],
        max_minutes_per_round=merged["max_minutes_per_round"],
        over_budget_action=merged["over_budget_action"],
        source=source,
    )
    return budget, issues


def evaluate_round_budget(budget, *, steps_used=None, minutes_used=None, idle_rounds=None):
    """Evaluate one round's usage facts against a :class:`RoundBudget` (PURE).

    Honesty contract (mirrors loop_telemetry): a dimension with a configured
    limit but NO usable fact is reported in ``not_measured`` — never assumed
    to be zero, never fabricated. ``heartbeat_due`` fires when
    ``idle_rounds >= budget.max_idle_rounds`` and is a REPORT trigger, not a
    termination (FEAT-063: a heartbeat is not a stop proof).

    Args:
        budget: a :class:`RoundBudget`.
        steps_used: measured steps consumed by the round (or ``None`` when
            not measured).
        minutes_used: measured wall-clock minutes of the round (or ``None``).
        idle_rounds: consecutive artifact-less rounds reported by the
            execution body (or ``None`` when not measured).

    Returns:
        dict with keys:
          - ``within_budget``: bool — True when no measured breach exists.
          - ``breaches``: list of ``{"dimension", "limit", "actual"}``.
          - ``not_measured``: list of dimension names lacking a usable fact.
          - ``heartbeat_due``: bool.
          - ``over_budget_action``: the budget's explicit action string.
          - ``note``: the non-termination marker (FEAT-063 alignment).
          - ``issues``: per-fact validation notes (never raises).
    """
    issues = []
    checks = (
        ("steps", budget.max_steps_per_round, steps_used),
        ("minutes", budget.max_minutes_per_round, minutes_used),
    )
    breaches = []
    not_measured = []
    for name, limit, actual in checks:
        if not _usable_int(actual):
            not_measured.append(name)
            if actual is not None:
                issues.append(
                    "{0} usage fact {1!r} is not a usable integer — "
                    "treated as not measured".format(name, actual)
                )
        elif actual > limit:
            breaches.append({"dimension": name, "limit": limit, "actual": actual})

    heartbeat_due = False
    if not _usable_int(idle_rounds):
        if idle_rounds is not None:
            issues.append(
                "idle_rounds fact {0!r} is not a usable integer — "
                "heartbeat not evaluated".format(idle_rounds)
            )
    else:
        heartbeat_due = idle_rounds >= budget.max_idle_rounds

    return {
        "within_budget": not breaches,
        "breaches": breaches,
        "not_measured": not_measured,
        "heartbeat_due": heartbeat_due,
        "over_budget_action": budget.over_budget_action,
        "note": (
            "budget evaluation is advisory: an over-budget or heartbeat-due "
            "round RECOMMENDS interrupt-recovery; nothing is auto-terminated "
            "(FEAT-063: a heartbeat/timeout is not a stop proof)"
        ),
        "issues": issues,
    }


def heartbeat_should_fire(budget, idle_rounds):
    """PURE predicate: does an N-rounds-without-artifact heartbeat fire?

    Fires iff ``idle_rounds`` is a usable integer and
    ``idle_rounds >= budget.max_idle_rounds``. Invalid facts NEVER fire
    (no fabricated heartbeats).
    """
    if not isinstance(budget, RoundBudget) or not _usable_int(idle_rounds):
        return False
    return idle_rounds >= budget.max_idle_rounds


def heartbeat_payload(unit_id, tier, *, idle_rounds, current_round=None,
                      last_artifact_ref=None, budget=None):
    """Build the heartbeat REPORT payload (FEAT-044 — 上报，不是判死).

    The report is what the Coordinator/scheduler SEES instead of dead-waiting:
    it carries the idle-rounds fact, the threshold it crossed, the last
    artifact anchor (evidence), and the recommended next action. It is a
    report ONLY — ``stop_proof`` is always False (FEAT-063: 心跳超时不构成
    停止证明); termination decisions stay with the Coordinator/scheduler.

    Args:
        unit_id: the flow unit / task the execution body is working.
        tier: loop tier of the execution body.
        idle_rounds: consecutive artifact-less rounds (caller-reported fact).
        current_round: current loop round, when known (evidence context).
        last_artifact_ref: reference to the last produced artifact (evidence
            anchor; ``None`` → the report records the gap itself).
        budget: optional :class:`RoundBudget`; without one the module default
            threshold applies.

    Returns:
        A JSON-serializable dict (``kind="round_heartbeat_report"``).
    """
    if isinstance(budget, RoundBudget):
        threshold = budget.max_idle_rounds
    else:
        threshold = HEARTBEAT_IDLE_ROUNDS_DEFAULT
    fires = _usable_int(idle_rounds) and idle_rounds >= threshold
    if last_artifact_ref is None:
        evidence_basis = (
            "idle_rounds reported by the execution body; no artifact anchor "
            "provided — the report itself records the artifact gap"
        )
    else:
        evidence_basis = (
            "idle_rounds reported by the execution body; last artifact "
            "anchor: {0}".format(last_artifact_ref)
        )
    return {
        "kind": "round_heartbeat_report",
        "unit_id": unit_id,
        "tier": tier,
        "current_round": current_round,
        "idle_rounds": idle_rounds,
        "idle_threshold": threshold,
        "fires": bool(fires),
        "last_artifact_ref": last_artifact_ref,
        "evidence_basis": evidence_basis,
        "stop_proof": False,
        "stop_proof_basis": (
            "FEAT-063 alignment: a heartbeat (and its threshold crossing) is "
            "NOT a stop proof — report only; termination/withdrawal decisions "
            "stay with the Coordinator/scheduler"
        ),
        "recommended_action": OVER_BUDGET_ACTION,
    }


def interrupt_recovery_payload(unit_id, tier, *, reason, idle_rounds=None,
                               current_round=None, last_artifact_ref=None,
                               budget=None):
    """Build the productized interrupt + minimal-instruction recovery payload.

    FEAT-044 productizes the recovery move that empirically worked in
    FIX-357/359 (EVD-1101①): interrupt the stalled execution body, then inject
    a MINIMAL instruction that makes it continue — no re-planning, no scope
    expansion, exactly a three-part status return followed by continuing the
    current step. The scheduler/host performs the actual interrupt (this
    module is pure and side-effect free); this payload is the mechanism's
    output: the injection text plus the expected response shape so the
    Coordinator can verify the recovery.

    Args:
        unit_id: the flow unit / task the execution body is working.
        tier: loop tier of the execution body.
        reason: short interrupt reason (e.g. ``"heartbeat"`` or a budget
            breach summary).
        idle_rounds: idle-rounds fact, when known (bound into the text).
        current_round: current loop round, when known.
        last_artifact_ref: last artifact anchor, when known (``None`` → the
            instruction states the artifact gap).
        budget: optional :class:`RoundBudget` (currently unused for the text;
            accepted for API symmetry and future bounding).

    Returns:
        A JSON-serializable dict (``kind="interrupt_recovery"``) with:
          - ``minimal_instruction``: the fact-bound injection text.
          - ``expected_response_shape``: the three-part return the Coordinator
            verifies.
          - ``escalation_note``: interrupt loops are BOUNDED — a recovery turn
            that is itself idle for the threshold escalates via the tier fuse
            path (PP-Fuse-Escalate), it is not interrupted again forever.
          - ``stop_proof``: always False (FEAT-063 alignment).
          - ``productized_from``: the empirical provenance (FIX-357/359).
    """
    if _usable_int(idle_rounds):
        idle_txt = str(idle_rounds)
    else:
        idle_txt = "an unknown number of"
    anchor_txt = (
        str(last_artifact_ref) if last_artifact_ref is not None
        else "none reported (artifact gap)"
    )
    minimal_instruction = (
        "[interrupt-recovery] Interrupted after {idle} round(s) without an "
        "artifact. Do NOT re-plan and do NOT expand scope. In your next turn "
        "return exactly three things: (1) the artifact or concrete progress "
        "produced so far for unit {uid} (last artifact anchor: {anchor}); "
        "(2) the single blocker, if any; (3) the one next action to finish "
        "the current step. Then continue the current step only."
    ).format(idle=idle_txt, uid=unit_id, anchor=anchor_txt)
    return {
        "kind": "interrupt_recovery",
        "unit_id": unit_id,
        "tier": tier,
        "reason": reason,
        "idle_rounds": idle_rounds,
        "current_round": current_round,
        "last_artifact_ref": last_artifact_ref,
        "minimal_instruction": minimal_instruction,
        "expected_response_shape": {
            "artifact_or_progress": "string",
            "blocker": "string or null",
            "next_action": "string",
        },
        "escalation_note": (
            "Interrupt loops are bounded: if the recovery turn is itself idle "
            "for the tier's heartbeat threshold again, escalate via the tier "
            "fuse path (PP-Fuse-Escalate) instead of interrupting forever."
        ),
        "stop_proof": False,
        "productized_from": (
            "FIX-357/359 empirically validated recovery move (EVD-1101① "
            "round delay tax): interrupt the stalled body, inject a minimal "
            "continue instruction"
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
# FX-193 — 0.65.0 slice 6: plan-tracker rollup view (per-flow-unit loop_state).
#
# Resolves RISK-037 criterion 2: the plan-tracker's single fake "current stage"
# (``当前阶段``) is replaced by a per-unit decomposition. ``rollup_loop_state``
# reads flow-unit-runtime.json via a deferred verify_workflow import and produces
# a per-unit view — NOT a single global stage.
#
# LOAD-BEARING INVARIANT: the returned dict ALWAYS sets ``no_global_stage=True``
# and MUST NOT contain any field that collapses multiple units into one stage.
# This is the RISK-037 criterion 2 executable guarantee, proven by
# tests/test_loop_rollup.py.
# ═══════════════════════════════════════════════════════════════════════════

# ─── Deferred verify_workflow import (avoid import cycle) ──────────────────
# loop_engine.py MUST NOT import verify_workflow at module top level — that
# would create a cycle (verify_workflow imports this module's rollup via the
# cmd_loop_rollup thin entry). We resolve verify_workflow lazily on first
# runtime read, mirroring the ``_vw()`` pattern in loop_health.py.
_VW_CACHE = None


def _vw():
    """Lazy accessor for verify_workflow (deferred to avoid the import cycle).

    loop_engine.py MUST NOT import verify_workflow at module top level — that
    would create a cycle (verify_workflow imports this module's rollup via the
    ``cmd_loop_rollup`` thin entry). We resolve verify_workflow lazily on first
    runtime read, exactly mirroring the ``_vw()`` pattern in loop_health.py.
    """
    global _VW_CACHE
    if _VW_CACHE is None:
        import verify_workflow  # noqa: WPS433 deferred import
        _VW_CACHE = verify_workflow
    return _VW_CACHE


def _load_runtime_state(root=None):
    """Load flow-unit-runtime.json via verify_workflow's path resolver.

    Returns the parsed dict, or ``None`` if the file is missing or unreadable.
    Never raises — callers rely on a graceful "no data" response. This mirrors
    the ``_load_runtime`` helper in loop_health.py.
    """
    try:
        vw = _vw()
        path = vw._flow_unit_runtime_path(root)
    except Exception:  # pragma: no cover - defensive (vw loader shape changed)
        return None
    if path is None or not Path(path).exists():
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# The four canonical loop tiers (ADR §4.6). Used to key the by_tier summary.
_LOOP_TIERS = ("setup", "inner", "middle", "outer")


def rollup_loop_state(root=None, plugin_home=None):
    """Roll up per-flow-unit loop_state from flow-unit-runtime.json.

    Returns a per-unit view — NOT a single global stage. This resolves
    RISK-037 criterion 2: the plan-tracker's single ``当前阶段`` field is
    replaced by a per-unit decomposition ("chapter 1 released, chapter 2 in
    Inner loop round 2, chapter 3 in Middle design iteration").

    PURE READ — no writes, no side effects. Fail-closed: a missing or corrupt
    runtime.json yields safe defaults (empty units, ``runtime_found=False``)
    and NEVER raises.

    LOAD-BEARING INVARIANT: the returned dict ALWAYS sets
    ``no_global_stage: True`` and contains NO field that collapses multiple
    units into one stage (no ``current_stage``, ``global_stage``,
    ``single_stage``, etc.). This is the RISK-037 criterion 2 executable
    guarantee — proven by ``tests/test_loop_rollup.py``.

    Args:
        root: Optional host project root (path or str). Used to locate
            ``flow-unit-runtime.json`` via verify_workflow's loader. Defaults
            to the verify_workflow ROOT.
        plugin_home: Optional plugin-home override (accepted for symmetry with
            the other loop_engine functions; the rollup is runtime-only and
            does not read the registry, so this is currently unused but kept
            for API consistency with FX-188/189 peers).

    Returns:
        dict with:
          - ``units``: list of per-unit dicts, each with keys
            ``{flow_unit_id, unit_type, active_loop_tier, loop_count,
            agent_phase, last_gate_result, fuse_tripped}``.
          - ``summary``: ``{total_units, active_loops,
            by_tier: {setup, inner, middle, outer}}``.
          - ``no_global_stage``: always ``True`` (the load-bearing invariant).
          - ``runtime_found``: bool — False when runtime.json is absent/corrupt.

        If flow-unit-runtime.json doesn't exist (pre-migration), returns::

            {"units": [], "summary": {...}, "no_global_stage": True,
             "runtime_found": False,
             "message": "flow-unit-runtime.json not found — project not yet "
                        "migrated to loop-engineering"}
    """
    runtime = _load_runtime_state(root)
    if not isinstance(runtime, dict):
        return {
            "units": [],
            "summary": {
                "total_units": 0,
                "active_loops": 0,
                "by_tier": {tier: 0 for tier in _LOOP_TIERS},
            },
            "no_global_stage": True,
            "runtime_found": False,
            "message": (
                "flow-unit-runtime.json not found — project not yet migrated "
                "to loop-engineering"
            ),
        }

    flow_units = runtime.get("flow_units")
    if not isinstance(flow_units, list):
        flow_units = []

    units = []
    by_tier = {tier: 0 for tier in _LOOP_TIERS}
    active_loops = 0

    for unit in flow_units:
        if not isinstance(unit, dict):
            continue
        ls = unit.get("loop_state")
        if not isinstance(ls, dict):
            ls = {}

        active_loop = bool(ls.get("active_loop", False))
        raw_tier = ls.get("active_loop_tier")

        # Dormant units (active_loop false) report tier=None regardless of any
        # stale active_loop_tier value. Active units report their tier as-is.
        tier = raw_tier if (active_loop and isinstance(raw_tier, str)) else None

        # Count active units into the by_tier buckets (case-insensitive key).
        if tier is not None:
            tier_key = tier.lower()
            if tier_key in by_tier:
                by_tier[tier_key] += 1

        try:
            loop_count = int(ls.get("loop_count", 0))
        except (TypeError, ValueError):
            loop_count = 0

        if active_loop:
            active_loops += 1

        # Fuse tripped flag — nested under loop_state.fuse.tripped (FX-189 shape).
        fuse = ls.get("fuse")
        if isinstance(fuse, dict):
            fuse_tripped = bool(fuse.get("tripped", False))
        else:
            fuse_tripped = False

        units.append({
            "flow_unit_id": unit.get("flow_unit_id"),
            "unit_type": unit.get("unit_type"),
            "active_loop_tier": tier,
            "loop_count": loop_count,
            "agent_phase": ls.get("agent_phase"),
            "last_gate_result": ls.get("last_gate_result"),
            "fuse_tripped": fuse_tripped,
        })

    return {
        "units": units,
        "summary": {
            "total_units": len(units),
            "active_loops": active_loops,
            "by_tier": by_tier,
        },
        "no_global_stage": True,
        "runtime_found": True,
    }
