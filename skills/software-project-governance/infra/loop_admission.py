#!/usr/bin/env python3
"""Dependency blocking + WIP budget admission control (executable Loop Engine).

FEAT-007 (ADR-014 §5.3, §5.4, 0.68.0). Product code, authorized by Design Review
APPROVED_WITH_NOTES/0 (EVD-841~843).

This module makes the dependency graph **executable** and enforces a per-tier
**WIP (work-in-progress) budget** — the executable form of the architecture
ADR's "stacked loops / parallel review loops" discipline (bounded concurrency,
no unbounded fan-out).

**Scope (FEAT-007):**

  - :func:`check_admission` — the §5.3 admission check. For each dep in the
    unit's ``dependencies`` whose ``gate_state.status != "passed"``, the unit
    is denied admission (a ``dependency_block`` event is recorded). If all
    dependencies pass, the WIP budget is checked.
  - :func:`check_wip_budget` — the §5.4 WIP cap. Counts active units in the
    unit's tier; if at/over budget, denies (a ``wip_deny`` event is recorded);
    else admits (a ``wip_admit`` event is recorded).
  - :class:`AdmissionResult` / :class:`WIPResult` — the frozen result dataclasses.

**Constraints honored:**

  - PURE READS (admission checks do NOT mutate the runtime file). The
    ``dependency_block`` / ``wip_deny`` / ``wip_admit`` events are APPENDED to
    the event log (an audit trail), not used to mutate runtime status. The
    caller decides whether to actually activate a denied unit (admission
    denial leaves the unit ``dormant``/``blocked`` — it is queued, not
    failed; §5.4: "WIP denial is not a fuse trip").
  - The event-log append is best-effort: when ``log_path`` is None or the
    caller does not want events written, the checks still return correct
    results (the events are returned in the result for the caller to append).
  - RISK-037 / RISK-042 remain open.

Usage:
    from loop_admission import check_admission, check_wip_budget

    result = check_admission("shitu.story.Skeleton", runtime_file=path)
    if result.admitted:
        ...  # activate the unit (all deps passed, WIP under budget)
    else:
        ...  # result.reason / result.blocking_dependencies / result.wip_tier

The default WIP budgets (§5.4 table) are the module-level
:data:`WIP_BUDGET_DEFAULTS` constant.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

# loop_event_log is a peer module. The admission check records
# dependency_block / wip_admit / wip_deny events there.
import loop_event_log


# ═══════════════════════════════════════════════════════════════════════════
# WIP budget defaults (ADR-014 §5.4 table)
# ═══════════════════════════════════════════════════════════════════════════

# Default max concurrent ``active`` units per tier (§5.4). Tunable per
# project-type preset in principle; this is the conservative baseline the
# architecture ADR's risk-profile reasoning derived.
WIP_BUDGET_DEFAULTS = {
    "setup": 1,
    "inner": 5,
    "middle": 2,
    "outer": 1,
}

# The runtime statuses that count as "active" for WIP (a unit holding a slot
# in its tier's WIP budget). A dormant unit is not yet admitted; a
# withdrawn/escalated unit has released its slot.
_WIP_ACTIVE_STATUSES = frozenset({"active"})


# ═══════════════════════════════════════════════════════════════════════════
# Result dataclasses
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class WIPResult:
    """Outcome of :func:`check_wip_budget` (§5.4).

    Attributes:
        admitted: True iff the tier is under budget (a new active unit may
            join).
        reason: short diagnostic.
        tier: the tier this check was for.
        active_count: the number of currently-active units in this tier.
        budget: the tier's WIP budget.
        event: the ``wip_admit`` / ``wip_deny`` event dict that would be
            appended to the log (None when no event is produced).
    """
    admitted: bool
    reason: str = ""
    tier: object = None
    active_count: int = 0
    budget: int = 0
    event: dict = None


@dataclass
class AdmissionResult:
    """Outcome of :func:`check_admission` (§5.3 + §5.4).

    Attributes:
        admitted: True iff the unit may activate (all deps passed AND WIP
            under budget).
        reason: short diagnostic (which check denied admission, if any).
        blocking_dependencies: list of dep ``flow_unit_id``s whose gates have
            not passed (empty when the unit was not dependency-blocked).
        wip_tier: the tier used for the WIP check (the unit's
            ``active_loop_tier``, or the ``tier`` arg if the unit has none).
        wip_active_count: active units in the tier at check time.
        wip_budget: the tier's WIP budget.
        events: the list of event dicts (dependency_block / wip_deny /
            wip_admit) produced by this check, for the caller to append.
    """
    admitted: bool
    reason: str = ""
    blocking_dependencies: list = field(default_factory=list)
    wip_tier: object = None
    wip_active_count: int = 0
    wip_budget: int = 0
    events: list = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# Runtime file I/O helpers (mirror loop_paro_engine / loop_gate_processor)
# ═══════════════════════════════════════════════════════════════════════════


def _load_runtime(runtime_path):
    """Load the runtime payload (None if missing/corrupt). Never raises."""
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
    """Return the unit dict for ``unit_id`` or None."""
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


def _tier_of(unit, fallback=None):
    """Return the unit's active_loop_tier (or ``fallback`` if absent)."""
    tier = _loop_state_of(unit).get("active_loop_tier")
    if isinstance(tier, str) and tier:
        return tier
    return fallback


# ═══════════════════════════════════════════════════════════════════════════
# WIP budget check (ADR-014 §5.4)
# ═══════════════════════════════════════════════════════════════════════════


def check_wip_budget(tier, *, runtime_file, budgets=None, actor="admission",
                     unit_id=None, log_path=None, count_self=False):
    """Check whether a new active unit may join ``tier`` (§5.4).

    Counts the currently-active units in ``tier`` (``runtime_status ==
    "active"`` AND ``loop_state.active_loop_tier == tier``). When the count is
    at or above the tier's budget, admission is DENIED (the unit would exceed
    the WIP cap); a ``wip_deny`` event is recorded (or returned in
    :attr:`WIPResult.event`). When the count is below budget, admission is
    GRANTED and a ``wip_admit`` event is recorded.

    Args:
        tier: the loop tier (``setup|inner|middle|outer``).
        runtime_file: path to ``flow-unit-runtime.json``.
        budgets: optional override of :data:`WIP_BUDGET_DEFAULTS` (a dict
            mapping tier → max). None → use the defaults.
        actor: the actor string for the recorded event.
        unit_id: optional — the unit_id for the recorded event (so the log
            shows which unit was admitted/denied).
        log_path: optional event-log path. When given, the wip_admit/wip_deny
            event is appended to the log. When None, the event is returned in
            :attr:`WIPResult.event` but NOT written.
        count_self: when True AND ``unit_id`` matches an already-active unit
            in this tier, that unit is excluded from the count (so a
            re-evaluation of an already-active unit does not count itself
            against the budget). Default False (a NEW unit is being admitted).

    Returns:
        WIPResult. Never raises — a missing/corrupt runtime yields
        ``admitted=True`` with an explanatory reason (fail-OPEN: admission is
        not a safety mechanism, and a missing runtime means there are zero
        active units so the budget is trivially satisfied). The budget for an
        unknown tier defaults to :data:`WIP_BUDGET_DEFAULTS`[tier] if present,
        else 0 (deny) — unknown tiers get no implicit budget.
    """
    budgets = budgets if isinstance(budgets, dict) else WIP_BUDGET_DEFAULTS
    budget = budgets.get(tier, 0) if isinstance(tier, str) else 0
    runtime_path = Path(runtime_file) if not isinstance(runtime_file, Path) else runtime_file
    payload = _load_runtime(runtime_path)

    if not isinstance(payload, dict):
        # No runtime → no active units → budget trivially satisfied (fail-open).
        return WIPResult(
            admitted=True,
            reason="runtime file missing/corrupt; WIP budget trivially satisfied",
            tier=tier, active_count=0, budget=budget,
            event=None,
        )

    flow_units = payload.get("flow_units")
    active_count = 0
    if isinstance(flow_units, list):
        for unit in flow_units:
            if not isinstance(unit, dict):
                continue
            if unit.get("runtime_status") not in _WIP_ACTIVE_STATUSES:
                continue
            if _tier_of(unit) != tier:
                continue
            if count_self and unit_id is not None and unit.get("flow_unit_id") == unit_id:
                continue  # exclude the unit being re-evaluated
            active_count += 1

    under_budget = active_count < budget
    if under_budget:
        ev = loop_event_log.build_event(
            unit_id if unit_id else "(unspecified)", "wip_admit",
            cas_version=None, from_version=None, actor=actor,
            from_phase=None, to_phase=None, gate_id=None, tier=tier,
            payload={"tier": tier, "active_count_after": active_count + 1,
                     "budget": budget},
            reason="WIP under budget",
        )
        if log_path is not None:
            loop_event_log.append_event(ev, log_path=log_path)
        return WIPResult(
            admitted=True,
            reason="tier {0!r} active={1} < budget={2}; admit".format(
                tier, active_count, budget),
            tier=tier, active_count=active_count, budget=budget, event=ev,
        )
    # Over/at budget → deny.
    ev = loop_event_log.build_event(
        unit_id if unit_id else "(unspecified)", "wip_deny",
        cas_version=None, from_version=None, actor=actor,
        from_phase=None, to_phase=None, gate_id=None, tier=tier,
        payload={"tier": tier, "budget": budget, "active_count": active_count},
        reason="WIP over budget",
    )
    if log_path is not None:
        loop_event_log.append_event(ev, log_path=log_path)
    return WIPResult(
        admitted=False,
        reason="tier {0!r} active={1} >= budget={2}; deny".format(
            tier, active_count, budget),
        tier=tier, active_count=active_count, budget=budget, event=ev,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Dependency blocking + WIP admission (ADR-014 §5.3)
# ═══════════════════════════════════════════════════════════════════════════


def check_admission(unit_id, *, runtime_file, tier=None, budgets=None,
                    actor="admission", log_path=None):
    """Check admission for ``unit_id``: dependency gate + WIP budget (§5.3).

    Algorithm:

      1. LOAD the unit. If absent/missing → deny (cannot admit an unknown
         unit).
      2. For each ``dep_id`` in ``unit.dependencies``: load the dep unit; if
         its ``gate_state.status != "passed"`` → collect it as a blocking
         dependency.
      3. If any blocking dependency → DENY, record a ``dependency_block``
         event, and return (WIP is not checked — dependency blocking takes
         precedence).
      4. Else check the WIP budget (:func:`check_wip_budget`) for the unit's
         tier. The WIP result's admit/deny decision is the admission result.

    Args:
        unit_id: the flow_unit_id seeking admission.
        runtime_file: path to ``flow-unit-runtime.json``.
        tier: override the WIP-check tier. None → use the unit's
            ``loop_state.active_loop_tier``.
        budgets: optional WIP-budget override (see :func:`check_wip_budget`).
        actor: the actor string for recorded events.
        log_path: optional event-log path. When given, the
            dependency_block / wip_admit / wip_deny events are appended.

    Returns:
        AdmissionResult. Never raises. ``admitted`` is True ONLY when all
        dependencies passed AND the WIP check admitted.
    """
    runtime_path = Path(runtime_file) if not isinstance(runtime_file, Path) else runtime_file
    payload = _load_runtime(runtime_path)
    if not isinstance(payload, dict):
        return AdmissionResult(
            admitted=False,
            reason="runtime file missing/corrupt; cannot admit unit {0!r}".format(unit_id),
            events=[],
        )
    unit = _find_unit(payload, unit_id)
    if unit is None:
        return AdmissionResult(
            admitted=False,
            reason="flow_unit_id {0!r} not found in runtime file".format(unit_id),
            events=[],
        )

    events = []

    # ── Step 2-3: dependency blocking. ──────────────────────────────────────
    deps = unit.get("dependencies")
    deps = list(deps) if isinstance(deps, list) else []
    blocking = []
    for dep_id in deps:
        if not isinstance(dep_id, str) or not dep_id:
            continue
        dep_unit = _find_unit(payload, dep_id)
        if dep_unit is None:
            # An unknown dependency blocks (fail-closed: cannot confirm it
            # passed). This is the safer default — a typo'd dep id should not
            # silently admit the unit.
            blocking.append(dep_id)
            continue
        dep_status = _gate_state_of(dep_unit).get("status")
        if dep_status != "passed":
            blocking.append(dep_id)

    if blocking:
        ev = loop_event_log.build_event(
            unit_id, "dependency_block",
            cas_version=None, from_version=None, actor=actor,
            from_phase=None, to_phase=None, gate_id=None,
            tier=_tier_of(unit, fallback=tier),
            payload={"unit_id": unit_id, "blocking_dependencies": list(blocking)},
            reason="dependencies not passed",
        )
        events.append(ev)
        if log_path is not None:
            loop_event_log.append_event(ev, log_path=log_path)
        return AdmissionResult(
            admitted=False,
            reason="blocked by {0} unpassed dependencies: {1}".format(
                len(blocking), blocking),
            blocking_dependencies=blocking,
            wip_tier=_tier_of(unit, fallback=tier),
            events=events,
        )

    # ── Step 4: WIP budget. ─────────────────────────────────────────────────
    wip_tier = _tier_of(unit, fallback=tier)
    wip = check_wip_budget(
        wip_tier, runtime_file=runtime_path, budgets=budgets, actor=actor,
        unit_id=unit_id, log_path=log_path,
    )
    # The WIP check already appended its event (when log_path given). Surface
    # it in the result's events for callers that don't pass log_path.
    if wip.event is not None:
        events.append(wip.event)
    return AdmissionResult(
        admitted=wip.admitted,
        reason=wip.reason,
        blocking_dependencies=[],
        wip_tier=wip.tier,
        wip_active_count=wip.active_count,
        wip_budget=wip.budget,
        events=events,
    )


__all__ = [
    "WIP_BUDGET_DEFAULTS",
    "WIPResult",
    "AdmissionResult",
    "check_wip_budget",
    "check_admission",
]


if __name__ == "__main__":  # pragma: no cover - manual smoke
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    print("WIP_BUDGET_DEFAULTS = {0}".format(WIP_BUDGET_DEFAULTS))
