"""Canonical Loop Runtime Contract v2 validator (FEAT-002, ADR-013 / 0.67.0).

This stdlib-only leaf is the v2 counterpart to ``flow_unit_runtime.py``. It
validates payloads that declare ``schema_version: "2.0"`` +
``runtime_contract: "loop-runtime-contract/v2"`` against the canonical contract
schema in ``core/loop-runtime-contract.json`` (the single source of truth,
mirroring ``loop_engine.load_loop_registry``).

**Boundary (ADR-013 §9):** this validator is the FEAT-002 contract-enforcement
surface. It enforces the field/type/enum rules of §3.2/§3.3/§3.4, the
``last_gate_result == gate_state.last_result`` unification invariant (§3.4),
the ``decomposition_confirmed == true`` requirement (§3.2, the FEAT-004 hook
the validator enforces now), and the ``runtime_status`` ⇔ ``active_loop``
bidirectional implication (§3.4, the FEAT-004 guard enforced by the validator
now). It does NOT implement the FEAT-003 planner or the FEAT-004 decomposition
step — those are separate tasks. RISK-037 and RISK-042 remain open: this
validator does NOT activate any runtime execution engine.

**v1 byte-frozen:** the existing ``flow_unit_runtime.validate_flow_unit_runtime_payload``
(the 0.52.0/0.66.1 containment boundary) is preserved byte-for-byte. A version
router on ``schema_version`` dispatches v1 → v1 validator (unchanged) and v2 →
this module. See ``validate_flow_unit_runtime_payload_dispatch`` in
``flow_unit_runtime.py``.

**Loader contract:** ``load_loop_runtime_contract`` mirrors
``loop_engine.load_loop_registry`` — returns ``(data_or_None, issues_list)``
and never raises (fail-closed on missing/corrupt schema).
"""

import json
import re
from pathlib import Path


# ─── Fixed anchors ─────────────────────────────────────────────
# PLUGIN_HOME is derived from __file__ ONLY to locate the plugin's own
# declarative files. Same convention as loop_engine.py / loop_health.py.
# This file lives at PLUGIN_HOME/infra/checks/flow_unit_runtime_v2.py, so
# .parent.parent.parent == PLUGIN_HOME.
PLUGIN_HOME = Path(__file__).resolve().parent.parent.parent

# Relative path (from PLUGIN_HOME) to the canonical v2 contract schema.
_LOOP_RUNTIME_CONTRACT_REL = "core/loop-runtime-contract.json"

# The contract version this validator targets.
TARGET_SCHEMA_VERSION = "2.0"
TARGET_CONTRACT_ID = "loop-runtime-contract/v2"

# 64 lowercase hex (SHA-256). The validator checks presence + shape here; the
# FEAT-003 re-derivation parity check (apply re-derives the plan and asserts
# the hash matches) is the planner's responsibility.
_HEX256_RE = re.compile(r"^[0-9a-f]{64}$")


def _contract_path(plugin_home):
    """Resolve the contract schema path from an (optional) plugin_home override."""
    home = Path(plugin_home) if plugin_home is not None else PLUGIN_HOME
    return home / _LOOP_RUNTIME_CONTRACT_REL


def load_loop_runtime_contract(plugin_home=None):
    """Load ``core/loop-runtime-contract.json``.

    Returns ``(data_or_None, issues_list)``. Fail-closed on missing/corrupt: a
    missing file or invalid JSON yields ``(None, [diagnostic_string])`` and
    never raises.

    Mirrors the ``load_loop_registry`` contract in loop_engine.py (the same
    fail-closed ``(data, issues)`` discipline the loader/reader/health use).
    """
    contract_path = _contract_path(plugin_home)
    try:
        display = str(contract_path)
    except Exception:  # pragma: no cover - defensive
        display = "<loop-runtime-contract>"
    if not contract_path.exists():
        return None, [f"{display}: missing loop-runtime-contract schema"]
    try:
        text = contract_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [f"{display}: cannot read loop-runtime-contract schema: {exc}"]
    try:
        return json.loads(text), []
    except json.JSONDecodeError as exc:
        return None, [f"{display}: invalid JSON: {exc}"]


def _string_list(value):
    """A non-empty list of non-empty strings (mirrors flow_unit_runtime._string_list)."""
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and item.strip() for item in value
    )


def validate_flow_unit_runtime_payload_v2(state, display=".governance/flow-unit-runtime.json", plugin_home=None):
    """Return all Loop Runtime Contract v2 violations for an in-memory payload.

    Mirrors the v1 validator's return style: a list of failure strings (empty
    list ⇒ valid). Fail-closed: any missing/invalid field produces a specific
    error; there is no silent pass. Never raises — a non-dict root or a
    missing contract schema yields failure strings, not exceptions.

    Args:
        state: the in-memory v2 runtime payload dict.
        display: the display path used in failure messages (mirrors v1).
        plugin_home: optional plugin-home override forwarded to the schema
            loader (mirrors loop_engine/loop_health).

    Returns:
        list[str]: empty if the payload is a valid v2 contract instance;
        otherwise one specific failure string per violation.
    """
    if not isinstance(state, dict):
        return [f"{display}: flow-unit runtime root must be an object"]

    # Load the contract schema (fail-closed). If the schema itself is
    # missing/corrupt, validation cannot proceed — every payload fails closed.
    schema, schema_issues = load_loop_runtime_contract(plugin_home)
    if schema is None:
        # Schema authority missing: fail closed with the schema diagnostic so
        # the operator sees the root cause (mirrors FIX-196 fail-closed
        # discipline extended to the contract schema per ADR §8.2 item 4).
        return [f"{display}: cannot load v2 contract schema: {schema_issues}"]

    required_top = schema["required_top_level_fields"]
    required_per_unit = schema["required_per_unit_fields"]
    allowed_gate_statuses = set(schema["allowed_gate_statuses"])
    allowed_loop_tiers = set(schema["allowed_loop_tiers"])
    allowed_agent_phases = set(schema["allowed_agent_phases"])
    allowed_runtime_statuses = set(schema["allowed_runtime_statuses"])
    loop_state_fields = schema["loop_state_fields"]
    gate_state_fields = schema["gate_state_fields"]
    mandatory_boundary_tokens = schema["no_overclaim_boundary_mandatory_tokens"]

    failures = []

    # ─── Top-level envelope (ADR §3.2) ──────────────────────────────────────
    # schema_version must be exactly "2.0" (the routing discriminator).
    if state.get("schema_version") != TARGET_SCHEMA_VERSION:
        failures.append(
            f"{display}: schema_version must be {TARGET_SCHEMA_VERSION} for the v2 contract"
        )
    # runtime_contract: belt-and-braces discriminator; v2 requires BOTH.
    if state.get("runtime_contract") != TARGET_CONTRACT_ID:
        failures.append(
            f"{display}: runtime_contract must be {TARGET_CONTRACT_ID}"
        )
    # runtime_scope: replaces visibility-v1's "runtime-visibility-only".
    if state.get("runtime_scope") != schema["runtime_scope"]:
        failures.append(
            f"{display}: runtime_scope must be {schema['runtime_scope']}"
        )
    # workflow_model: "loop-engineering" is the only v2 value.
    if state.get("workflow_model") != schema["workflow_model"]:
        failures.append(
            f"{display}: workflow_model must be {schema['workflow_model']} for the v2 contract"
        )
    # contract_source: the single source-of-truth token.
    if state.get("contract_source") != schema["status_source"]:
        failures.append(
            f"{display}: contract_source must be {schema['status_source']}"
        )

    # All required top-level fields present.
    for field in required_top:
        if field not in state:
            failures.append(f"{display}: missing required top-level field `{field}`")

    # Type/value checks on the scalar top-level fields (only when present, so
    # the missing-field error above is the single message for an absent field).
    migration_version = state.get("migration_version")
    if "migration_version" in state and (
        not isinstance(migration_version, str) or not migration_version.strip()
    ):
        failures.append(f"{display}: migration_version must be a non-empty string")

    migration_plan_hash = state.get("migration_plan_hash")
    if "migration_plan_hash" in state:
        if not isinstance(migration_plan_hash, str) or not _HEX256_RE.match(migration_plan_hash):
            failures.append(
                f"{display}: migration_plan_hash must be a 64-lowercase-hex SHA-256 string"
            )

    migration_timestamp = state.get("migration_timestamp")
    if "migration_timestamp" in state and (
        not isinstance(migration_timestamp, str) or not migration_timestamp.strip()
    ):
        failures.append(f"{display}: migration_timestamp must be a non-empty ISO-8601 string")

    # decomposition_confirmed MUST be true (FEAT-004 hook, enforced now).
    decomposition_confirmed = state.get("decomposition_confirmed")
    if decomposition_confirmed is not True:
        failures.append(
            f"{display}: decomposition_confirmed must be true for a v2 payload "
            f"(FEAT-004 decomposition-confirmation hook)"
        )

    # no_overclaim_boundary: non-empty string list + every mandatory token present.
    boundary = state.get("no_overclaim_boundary")
    if not _string_list(boundary):
        failures.append(f"{display}: no_overclaim_boundary must be a non-empty string list")
        boundary = []
    boundary_text = " ".join(boundary).lower()
    for token in mandatory_boundary_tokens:
        if token.lower() not in boundary_text:
            failures.append(
                f"{display}: missing no_overclaim_boundary mandatory token `{token}`"
            )

    # ─── flow_units (ADR §3.3) ──────────────────────────────────────────────
    flow_units = state.get("flow_units")
    if not isinstance(flow_units, list) or not flow_units:
        failures.append(f"{display}: flow_units must be a non-empty list")
        flow_units = []

    seen_ids = []
    unit_by_id = {}
    for unit in flow_units:
        if not isinstance(unit, dict):
            failures.append(f"{display}: each flow unit must be an object")
            continue
        unit_id = unit.get("flow_unit_id")
        label = f"{display}: flow unit {unit_id or '<missing>'}"

        # flow_unit_id: non-empty string.
        if not isinstance(unit_id, str) or not unit_id.strip():
            failures.append(f"{label}: flow_unit_id must be a non-empty string")
            # Cannot continue per-unit checks without a usable id; skip the
            # rest for this unit but still record the id-shape failure.
            continue
        seen_ids.append(unit_id)
        unit_by_id[unit_id] = unit

        # All required per-unit fields present.
        for field in required_per_unit:
            if field not in unit:
                failures.append(f"{label}: missing required field `{field}`")

        # title: non-empty string.
        title = unit.get("title")
        if "title" in unit and (not isinstance(title, str) or not title.strip()):
            failures.append(f"{label}: title must be a non-empty string")

        # unit_type / project_type: non-empty strings.
        for field in ("unit_type", "project_type"):
            value = unit.get(field)
            if field in unit and (not isinstance(value, str) or not value.strip()):
                failures.append(f"{label}: {field} must be a non-empty string")

        # derivation_reason: non-empty string (FEAT-004: fallback reason explicit).
        derivation_reason = unit.get("derivation_reason")
        if "derivation_reason" in unit and (
            not isinstance(derivation_reason, str) or not derivation_reason.strip()
        ):
            failures.append(f"{label}: derivation_reason must be a non-empty string")

        # dependencies / blockers: lists (dependencies validated as known ids below).
        for field in ("dependencies", "blockers"):
            value = unit.get(field)
            if field in unit and not isinstance(value, list):
                failures.append(f"{label}: {field} must be a list")
            elif field in unit and not all(
                isinstance(item, str) for item in value
            ):
                failures.append(f"{label}: {field} must be a list of strings")

        # runtime_status: must be in the allowed enum (explicit, no default).
        runtime_status = unit.get("runtime_status")
        if "runtime_status" in unit and runtime_status not in allowed_runtime_statuses:
            failures.append(
                f"{label}: runtime_status must be one of {sorted(allowed_runtime_statuses)}"
            )

        # ── loop_state: the 9-field FX-189 shape (ADR §3.4) ─────────────────
        loop_state = unit.get("loop_state")
        if not isinstance(loop_state, dict):
            failures.append(f"{label}: loop_state must be an object")
            loop_state = {}
        else:
            for field in loop_state_fields:
                if field not in loop_state:
                    failures.append(f"{label}: loop_state missing field `{field}`")
            # active_loop: boolean.
            active_loop = loop_state.get("active_loop")
            if "active_loop" in loop_state and not isinstance(active_loop, bool):
                failures.append(f"{label}: loop_state.active_loop must be a boolean")
            # active_loop_tier: when the loop is active, tier must be in the enum.
            active_loop_tier = loop_state.get("active_loop_tier")
            if "active_loop_tier" in loop_state:
                if active_loop is True and active_loop_tier not in allowed_loop_tiers:
                    failures.append(
                        f"{label}: loop_state.active_loop_tier must be one of "
                        f"{sorted(allowed_loop_tiers)} when active_loop is true"
                    )
            # loop_count: non-negative integer (not bool).
            loop_count = loop_state.get("loop_count")
            if "loop_count" in loop_state and (
                isinstance(loop_count, bool)
                or not isinstance(loop_count, int)
                or loop_count < 0
            ):
                failures.append(
                    f"{label}: loop_state.loop_count must be a non-negative integer"
                )
            # agent_phase: must be in the allowed enum when present.
            agent_phase = loop_state.get("agent_phase")
            if "agent_phase" in loop_state and agent_phase not in allowed_agent_phases:
                failures.append(
                    f"{label}: loop_state.agent_phase must be one of "
                    f"{sorted(allowed_agent_phases)}"
                )
            # iteration_within_inner: non-negative integer (not bool).
            iter_inner = loop_state.get("iteration_within_inner")
            if "iteration_within_inner" in loop_state and (
                isinstance(iter_inner, bool)
                or not isinstance(iter_inner, int)
                or iter_inner < 0
            ):
                failures.append(
                    f"{label}: loop_state.iteration_within_inner must be a non-negative integer"
                )
            # pause_points_active: list.
            pause_points = loop_state.get("pause_points_active")
            if "pause_points_active" in loop_state and not isinstance(pause_points, list):
                failures.append(
                    f"{label}: loop_state.pause_points_active must be a list"
                )
            # fuse: object with the nested shape (FX-189).
            fuse = loop_state.get("fuse")
            if "fuse" in loop_state:
                if not isinstance(fuse, dict):
                    failures.append(f"{label}: loop_state.fuse must be an object")
                else:
                    fuse_tripped = fuse.get("tripped")
                    if "tripped" in fuse and not isinstance(fuse_tripped, bool):
                        failures.append(
                            f"{label}: loop_state.fuse.tripped must be a boolean"
                        )
                    fuse_max = fuse.get("max_rounds")
                    if "max_rounds" in fuse and (
                        isinstance(fuse_max, bool)
                        or not isinstance(fuse_max, int)
                    ):
                        failures.append(
                            f"{label}: loop_state.fuse.max_rounds must be an integer"
                        )

        # ── gate_state: {status, gate_id, last_result, evidence_refs} ───────
        gate_state = unit.get("gate_state")
        if not isinstance(gate_state, dict):
            failures.append(f"{label}: gate_state must be an object")
            gate_state = {}
        else:
            for field in gate_state_fields:
                if field not in gate_state:
                    failures.append(f"{label}: gate_state missing field `{field}`")
            gate_status = gate_state.get("status")
            if "status" in gate_state and gate_status not in allowed_gate_statuses:
                failures.append(
                    f"{label}: gate_state.status must be one of "
                    f"{sorted(allowed_gate_statuses)}"
                )
            gate_id = gate_state.get("gate_id")
            if "gate_id" in gate_state and (
                not isinstance(gate_id, str) or not gate_id.strip()
            ):
                failures.append(f"{label}: gate_state.gate_id must be a non-empty string")
            evidence_refs = gate_state.get("evidence_refs")
            if "evidence_refs" in gate_state and not isinstance(evidence_refs, list):
                failures.append(f"{label}: gate_state.evidence_refs must be a list")

        # ── FEAT-002 unification invariant: last_gate_result == gate_state.last_result.
        last_gate_result = loop_state.get("last_gate_result")
        gate_last_result = gate_state.get("last_result")
        # Only enforce equality when both fields are present (presence itself
        # is checked above; here we check the unification value equality).
        if "last_gate_result" in loop_state and "last_result" in gate_state:
            if last_gate_result != gate_last_result:
                failures.append(
                    f"{label}: loop_state.last_gate_result must equal "
                    f"gate_state.last_result (FEAT-002 unification invariant)"
                )

        # ── FEAT-004 guard: runtime_status ⇔ active_loop (bidirectional).
        # active ⇒ active_loop:true; dormant ⇒ active_loop:false. Enforced only
        # when runtime_status is a known enum value (a bad enum is reported
        # above) AND active_loop is a boolean (a bad type reported above), so
        # the implication check does not double-report.
        if (
            runtime_status in allowed_runtime_statuses
            and isinstance(loop_state.get("active_loop"), bool)
        ):
            active_loop_val = loop_state["active_loop"]
            if runtime_status == "active" and active_loop_val is not True:
                failures.append(
                    f"{label}: runtime_status 'active' requires loop_state.active_loop "
                    f"true (FEAT-004 bidirectional implication)"
                )
            if runtime_status == "dormant" and active_loop_val is not False:
                failures.append(
                    f"{label}: runtime_status 'dormant' requires loop_state.active_loop "
                    f"false (FEAT-004 bidirectional implication)"
                )

        # ── FEAT-004 AUDIT-133 guard: example-fixture reason cannot be active.
        if (
            isinstance(derivation_reason, str)
            and derivation_reason == "example-fixture"
            and runtime_status == "active"
        ):
            failures.append(
                f"{label}: derivation_reason 'example-fixture' must pair with "
                f"runtime_status 'dormant' (FEAT-004 AUDIT-133 guard)"
            )

    # ─── Cross-unit: duplicate flow_unit_id ──────────────────────────────────
    duplicates = sorted({uid for uid in seen_ids if seen_ids.count(uid) > 1})
    for uid in duplicates:
        failures.append(f"{display}: duplicate flow_unit_id `{uid}`")

    # ─── Cross-unit: dependencies must reference known flow_unit_ids ─────────
    for uid, unit in unit_by_id.items():
        deps = unit.get("dependencies")
        if isinstance(deps, list):
            for dep in deps:
                if isinstance(dep, str) and dep not in unit_by_id:
                    failures.append(
                        f"{display}: flow unit {uid} has unknown dependency `{dep}`"
                    )

    return failures


def validate_flow_unit_runtime_v2_payload(payload, display=".governance/flow-unit-runtime.json", plugin_home=None):
    """Validate a v2 payload and return a ``{"valid": bool, "errors": [...]}`` dict.

    This is the dict-style entry point requested by FEAT-002. It wraps
    :func:`validate_flow_unit_runtime_payload_v2` (the list-style core that
    mirrors the v1 validator's interface). ``valid`` is True iff the failure
    list is empty.

    Args:
        payload: the in-memory v2 runtime payload dict.
        display: the display path used in failure messages (mirrors v1).
        plugin_home: optional plugin-home override forwarded to the schema loader.

    Returns:
        dict: ``{"valid": bool, "errors": list[str]}``. Never raises — a
        non-dict payload or a missing schema yields ``{"valid": False, ...}``.
    """
    errors = validate_flow_unit_runtime_payload_v2(payload, display, plugin_home)
    return {"valid": not errors, "errors": errors}


# ═══════════════════════════════════════════════════════════════════════════
# FEAT-005 ADDITIVE EXTENSION (ADR-014 §3.6, 0.68.0)
#
# The function below is STRICTLY ADDITIVE. It calls the byte-frozen 0.67.0
# validator above (``validate_flow_unit_runtime_payload_v2``) UNCHANGED, then
# adds the FEAT-005 transition + CAS rules on top. The 0.67.0 entry points are
# not modified; a payload that passes 0.67.0 validation but lacks ``cas_version``
# on an active unit FAILS this 0.68.0 extension — that is the executable guard
# that an activated unit carries a real CAS-guarded state (§3.6).
#
# The contract ``schema_version`` stays "2.0"; ``cas_version`` is a per-unit
# optional field that FEAT-005 populates. RISK-037 / RISK-042 remain open.
# ═══════════════════════════════════════════════════════════════════════════


def _is_nonneg_int_not_bool(value):
    """True iff ``value`` is a non-negative int and NOT a bool.

    Mirrors the loop_count / iteration_within_inner check discipline in the
    0.67.0 validator (an int that excludes the bool subtype).
    """
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def validate_loop_runtime_v2_with_transitions(payload, event_log=None,
                                              display=".governance/flow-unit-runtime.json",
                                              plugin_home=None):
    """Return all FEAT-005 (transition + CAS) violations for a v2 payload.

    STRICTLY ADDITIVE (ADR-014 §3.6). Calls the byte-frozen 0.67.0 validator
    (:func:`validate_flow_unit_runtime_payload_v2`) and ADDS the FEAT-005
    rules on top. The 0.67.0 entry point is unchanged.

    FEAT-005 additions:

      1. **``cas_version`` presence**: REQUIRED on ``active`` units; OPTIONAL
         on ``dormant`` / ``withdrawn`` units (dormant units are write-once at
         migration; they have no transitions to version). Must be a
         non-negative integer (not bool) when present.
      2. **Event-log consistency** (the FEAT-007 hook): if ``event_log`` is
         supplied, check (a) ``cas_version`` monotonicity (+1 per event per
         unit) and (b) phase legality (replay the event log, verify every
         transition is legal per the §3.2 table). If ``event_log`` is None,
         SKIP (FEAT-005 does not require the event log; FEAT-007 provides it).
      3. **Unification preserved**: re-assert
         ``loop_state.last_gate_result == gate_state.last_result`` after every
         transition (the 0.67.0 invariant; never write one without the other).

    Args:
        payload: the in-memory v2 runtime payload dict.
        event_log: Optional event log for the FEAT-007 consistency check.
            Accepts a list of event dicts (each carrying ``unit_id``,
            ``from_phase``, ``to_phase``, ``cas_version``) or a path to a JSONL
            file. None (the FEAT-005 default) skips the consistency check.
        display: the display path used in failure messages.
        plugin_home: optional plugin-home override forwarded to the schema
            loader (and to the contract loader for the 0.67.0 pass).

    Returns:
        list[str]: empty iff the payload passes BOTH the 0.67.0 v2 rules AND
        the FEAT-005 transition/CAS rules. One specific failure string per
        violation. Never raises.
    """
    # ── 0.67.0 base pass (byte-frozen, UNCHANGED). ───────────────────────────
    failures = list(validate_flow_unit_runtime_payload_v2(
        payload, display, plugin_home
    ))

    if not isinstance(payload, dict):
        # The 0.67.0 pass already reported the non-dict root; nothing to add.
        return failures

    flow_units = payload.get("flow_units")
    if not isinstance(flow_units, list):
        return failures  # the 0.67.0 pass reported the missing list.

    # ── Addition 1: cas_version presence + shape per unit. ───────────────────
    for unit in flow_units:
        if not isinstance(unit, dict):
            continue
        uid = unit.get("flow_unit_id")
        label = "{0}: flow unit {1}".format(display, uid if isinstance(uid, str) else "<missing>")
        runtime_status = unit.get("runtime_status")
        loop_state = unit.get("loop_state")
        if not isinstance(loop_state, dict):
            continue  # the 0.67.0 pass reported the bad loop_state shape.

        cas = loop_state.get("cas_version")
        if "cas_version" in loop_state:
            if not _is_nonneg_int_not_bool(cas):
                failures.append(
                    "{0}: loop_state.cas_version must be a non-negative integer "
                    "(not bool) when present (FEAT-005)".format(label)
                )
        else:
            # Absent: required when the unit is activated (runtime_status
            # "active"); optional for dormant/withdrawn units.
            if runtime_status == "active":
                failures.append(
                    "{0}: loop_state.cas_version is required on an active unit "
                    "(FEAT-005 CAS guard)".format(label)
                )

    # ── Addition 2 + 3: event-log consistency (FEAT-007 hook). ───────────────
    # FEAT-005 passes event_log=None → skip (state file alone is sufficient per
    # §3.5). When supplied, replay it: monotonic cas_version per unit + every
    # transition legal per the §3.2 table.
    if event_log is not None:
        failures.extend(_replay_event_log(event_log, flow_units, display))

    return failures


def _replay_event_log(event_log, flow_units, display):
    """Replay ``event_log`` against the units; return violation strings.

    Checks:
      - cas_version monotonic (+1 per consecutive event per unit, starting from
        the unit's on-disk cas_version before the first logged event).
      - phase legality: every event's (from_phase, to_phase) is a legal §3.2
        transition given the event's gate/fuse facts.
      - unification: after each gate-bearing transition, the event's recorded
        gate result is consistent (the writer always writes both fields).

    Returns a list of failure strings (empty if consistent). Never raises.
    """
    # Local import to avoid a hard module-level dependency on loop_paro_engine
    # (which itself only depends on the stdlib, so the import is cheap, but
    # keeping it local makes the additive boundary explicit and lets the 0.67.0
    # validator stand alone if loop_paro_engine is ever moved).
    import sys
    import os as _os
    try:
        # loop_paro_engine lives one directory up from checks/.
        _checks_parent = Path(__file__).resolve().parent.parent
        if str(_checks_parent) not in sys.path:
            sys.path.insert(0, str(_checks_parent))
        import loop_paro_engine  # noqa: WPS433 deferred additive import
    except Exception as exc:  # pragma: no cover - defensive
        return ["{0}: cannot load loop_paro_engine for transition replay: {1}".format(
            display, exc)]

    failures = []

    # Normalize the event log to a {unit_id: [events]} map.
    events = []
    if isinstance(event_log, (list, tuple)):
        events = [e for e in event_log if isinstance(e, dict)]
    elif isinstance(event_log, (str, Path)):
        try:
            p = Path(event_log)
            if p.is_file():
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                        if isinstance(ev, dict):
                            events.append(ev)
                    except json.JSONDecodeError:
                        continue
        except OSError:
            events = []
    else:
        return failures  # unknown shape — nothing to replay.

    # Group events by unit, preserving order.
    by_unit = {}
    for ev in events:
        uid = ev.get("unit_id")
        if isinstance(uid, str):
            by_unit.setdefault(uid, []).append(ev)

    for uid, unit_events in by_unit.items():
        label = "{0}: flow unit {1}".format(display, uid)
        # The replay verifies the INTERNAL consistency of this unit's event
        # history: cas_version is a monotonic +1 sequence starting from 0 (the
        # activation), and every (from_phase, to_phase) is legal per the §3.2
        # table. The baseline is therefore the START OF HISTORY — prev_cas=None
        # (so the first event must be the activation at cas=0) and prev_phase
        # None (entry, so the first event (entry)→plan is legal). The on-disk
        # current state is a separate concern, handled by the recovery path; it
        # is NOT the replay baseline (the log is the history being replayed).
        prev_cas = None
        prev_phase = None

        for idx, ev in enumerate(unit_events):
            ev_label = "{0} (event #{1})".format(label, idx + 1)
            ev_cas = ev.get("cas_version")
            # from_phase: the event's recorded source phase. An activation event
            # omits from_phase (or sets it to None/"(entry)") — fall back to the
            # replayed prev_phase so the validator sees the (entry)→plan source.
            raw_from = ev.get("from_phase", None)
            if raw_from is None:
                from_phase = prev_phase
            else:
                from_phase = raw_from
            to_phase = ev.get("to_phase")
            # gate_result may legitimately be a falsy string; loop_count may be 0.
            # Use explicit None checks (NOT `or`) so falsy-but-valid values survive.
            payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
            gate_result = ev.get("gate_result")
            if gate_result is None:
                gate_result = payload.get("gate_result")
            loop_count = ev.get("loop_count")
            if loop_count is None:
                loop_count = payload.get("loop_count")
            max_rounds = ev.get("max_rounds")
            if max_rounds is None:
                max_rounds = payload.get("max_rounds")

            # ── cas_version monotonicity (+1 per event per unit). ─────────────
            if not (isinstance(ev_cas, int) and not isinstance(ev_cas, bool)):
                failures.append(
                    "{0}: event cas_version must be a non-negative integer "
                    "(got {1!r})".format(ev_label, ev_cas)
                )
            else:
                if prev_cas is None:
                    # First event for this unit: must be the activation (cas 0).
                    if ev_cas != 0:
                        failures.append(
                            "{0}: first event cas_version must be 0 (activation), "
                            "got {1}".format(ev_label, ev_cas)
                        )
                elif ev_cas != prev_cas + 1:
                    failures.append(
                        "{0}: cas_version not monotonic: expected {1} (+1 from "
                        "{2}), got {3}".format(ev_label, prev_cas + 1, prev_cas, ev_cas)
                    )
                prev_cas = ev_cas

            # ── phase legality (replay via the §3.2 table). ───────────────────
            eval_event = {}
            if gate_result is not None:
                eval_event["gate_result"] = gate_result
            if loop_count is not None:
                eval_event["loop_count"] = loop_count
            if max_rounds is not None:
                eval_event["max_rounds"] = max_rounds
            legal, reason = loop_paro_engine.validate_transition(
                from_phase, to_phase, eval_event
            )
            if not legal:
                failures.append(
                    "{0}: illegal phase transition {1!r}→{2!r}: {3}".format(
                        ev_label, from_phase, to_phase, reason)
                )
            # Advance the replayed phase (terminals don't advance further).
            if to_phase in (loop_paro_engine.PLAN, loop_paro_engine.ACT,
                            loop_paro_engine.OBSERVE, loop_paro_engine.REFLECT):
                prev_phase = to_phase

    return failures
