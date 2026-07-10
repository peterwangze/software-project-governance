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
"""

import json
import re
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
