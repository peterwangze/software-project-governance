"""Canonical visibility-v1 flow-unit runtime validation.

This stdlib-only leaf is shared by the CLI adapter and migration writer.  It
intentionally validates the existing visibility contract; loop-engineering
activation belongs to the later runtime-contract migration.

**Version routing (FEAT-002, ADR-013 / 0.67.0):** ``validate_flow_unit_runtime_payload``
below is the BYTE-FROZEN visibility-v1 validator (the 0.52.0/0.66.1 containment
boundary). It is preserved unchanged — do not modify its logic. The
:func:`validate_flow_unit_runtime_payload_dispatch` entry point at the bottom of
this file routes a payload on ``schema_version``: ``"1.0"`` (or absent) → this
v1 validator (unchanged); ``"2.0"`` → the new v2 validator in
``flow_unit_runtime_v2.py``; anything else → fail. v1 and v2 coexist; no
installed state is broken.
"""

import re


RUNTIME_SCOPE = "runtime-visibility-only"
ACTIVE_MODE = "classic-phase-gate"
DYNAMIC_MODE = "dynamic-flow-gate"
ALLOWED_SOURCES = {"hot-project-state", "runtime-visibility-only", "example-runtime-fixture"}
ALLOWED_GATE_STATUSES = {
    "backlog", "pending", "not-started", "in-progress", "testing",
    "passed", "released", "blocked",
}
GATES = [f"G{i}" for i in range(1, 12)]
STAGES = [
    "initiation", "research", "selection", "infrastructure", "architecture",
    "development", "testing", "ci-cd", "release", "operations", "maintenance",
]
REQUIRED_FLOW_FIELDS = [
    "flow_unit_id", "title", "unit_type", "project_type", "lifecycle_mode",
    "current_stage", "current_subphase", "gate_lane", "gate_references",
    "allowed_next_transitions", "dependencies", "blockers", "evidence_refs",
    "loop_state", "runtime_status_source",
]
BOUNDARY_TOKENS = [
    "runtime visibility only",
    "does not activate declarative gate engine",
    "does not migrate projects",
    "classic G1-G11 remains compatible",
    "does not close RISK-036",
    "does not close RISK-037",
    "does not claim 1.0.0 production-ready",
]
FORBIDDEN_OVERCLAIMS = [
    ("risk-036 closed", re.compile(r"\brisk-036\b[^\n.;|]{0,48}\bclosed\b")),
    ("risk-036 closed", re.compile(r"\bclosed\b[^\n.;|]{0,48}\brisk-036\b")),
    ("risk-036 closure achieved", re.compile(r"\brisk-036\b[^\n.;|]{0,48}\bclosure\s+achieved\b")),
    ("risk-037 closed", re.compile(r"\brisk-037\b[^\n.;|]{0,48}\bclosed\b")),
    ("risk-037 closed", re.compile(r"\bclosed\b[^\n.;|]{0,48}\brisk-037\b")),
    ("risk-037 closure achieved", re.compile(r"\brisk-037\b[^\n.;|]{0,48}\bclosure\s+achieved\b")),
    ("1.0.0 production-ready", re.compile(r"\b1\.0\.0\s+production-ready\b")),
]


def _string_list(value):
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and item.strip() for item in value
    )


def _text_values(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _text_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _text_values(item)


def _claim_local_window(text, start, end):
    clause_start = max(
        (text.rfind(marker, 0, start) for marker in ";；.!?！？|:："),
        default=-1,
    ) + 1
    clause_ends = [text.find(marker, end) for marker in ";；.!?！？|:："]
    clause_end = min((pos for pos in clause_ends if pos >= 0), default=len(text))
    return text[clause_start:start], text[end:clause_end]


def _word_count(text):
    return len(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", text.lower()))


def _marker_positions(text, markers):
    lower = text.lower()
    positions = []
    for marker in markers:
        marker_lower = marker.lower()
        if re.search(r"[a-z0-9]", marker_lower):
            pattern = rf"(?<![a-z0-9]){re.escape(marker_lower)}(?![a-z0-9])"
            positions.extend(
                (match.start(), match.end(), marker_lower)
                for match in re.finditer(pattern, lower)
            )
        else:
            start = lower.find(marker_lower)
            while start != -1:
                positions.append((start, start + len(marker_lower), marker_lower))
                start = lower.find(marker_lower, start + len(marker_lower))
    return positions


def _claim_is_negated(text, matched_claim):
    """Preserve the legacy validator's complete local negation semantics."""
    lower = text.lower()
    claim_lower = matched_claim.lower()
    noun_claim_terms = (
        "1.0.0 production-ready", "risk-036 closed", "risk-037 closed",
        "risk-036 closure achieved", "risk-037 closure achieved",
    )
    direct_pre_markers = (
        "not", "no", "does not", "do not", "is not", "are not", "isn't",
        "doesn't", "don't", "不是", "不等于", "不得", "不能", "不声明", "未",
        "未发现", "没有", "明确否定", "阻断", "拦截",
    )
    predicate_markers = (
        "does not claim", "do not claim", "not claim", "does not mean",
        "do not mean", "doesn't mean", "don't mean", "is not", "are not",
        "isn't", "no", "不是", "不等于", "不替代", "不得", "不能", "不声明",
        "未", "未发现", "没有", "avoid", "avoids", "避免", "明确否定", "阻断", "拦截",
    )
    post_markers = (
        "is not", "are not", "isn't", "not claimed", "not verified", "not proof",
        "不是", "不等于", "不得", "不能", "不声明", "未", "没有", "不可用",
        "不可发布", "仍不可用", "仍不可发布", "保守处置", "继续保留", "继续打开",
        "仍打开", "仍需", "阻断", "拦截", "过度声明", "肯定式过度声明",
    )
    matches = list(re.finditer(re.escape(claim_lower), lower))
    if not matches:
        return False
    for match in matches:
        prefix, suffix = _claim_local_window(lower, match.start(), match.end())
        negated = False
        prefix_window = prefix[-96:]
        for _start, marker_end, _marker in _marker_positions(prefix_window, direct_pre_markers):
            between = prefix_window[marker_end:]
            if not re.search(r"[,;；.!?！？|:：]", between) and _word_count(between) <= 2:
                negated = True
                break
        if not negated:
            for _start, marker_end, marker in _marker_positions(prefix, predicate_markers):
                between = prefix[marker_end:]
                if marker == "no":
                    if claim_lower not in noun_claim_terms:
                        continue
                    if not any(other_claim in between for other_claim in noun_claim_terms):
                        continue
                if _word_count(between) <= 36:
                    negated = True
                    break
        if not negated:
            suffix_head = suffix[:96]
            for marker_start, _end, _marker in _marker_positions(suffix_head, post_markers):
                between = suffix_head[:marker_start]
                if not re.search(r"[,;；.!?！？|:：]", between) and _word_count(between) <= 3:
                    negated = True
                    break
        if not negated:
            return False
    return True


def validate_flow_unit_runtime_payload(state, display=".governance/flow-unit-runtime.json"):
    """Return all visibility-v1 contract violations for an in-memory payload."""
    if not isinstance(state, dict):
        return [f"{display}: flow-unit runtime root must be an object"]

    failures = []
    if state.get("schema_version") not in {"1.0", 1}:
        failures.append(f"{display}: schema_version must be 1.0")
    if state.get("runtime_scope") != RUNTIME_SCOPE:
        failures.append(f"{display}: runtime_scope must be {RUNTIME_SCOPE}")
    if state.get("workflow_model") not in {ACTIVE_MODE, DYNAMIC_MODE}:
        failures.append(f"{display}: workflow_model must be classic-phase-gate or dynamic-flow-gate")
    if state.get("default_lifecycle_mode") != ACTIVE_MODE:
        failures.append(f"{display}: default_lifecycle_mode must preserve {ACTIVE_MODE}")
    if state.get("declarative_gate_engine") is not False:
        failures.append(f"{display}: declarative_gate_engine must be false for runtime visibility only")
    if state.get("project_migration") is not False:
        failures.append(f"{display}: project_migration must be false for runtime visibility only")
    if state.get("runtime_status_source") not in ALLOWED_SOURCES:
        failures.append(f"{display}: runtime_status_source must be a declared hot-state/runtime-visibility source")

    boundary = state.get("no_overclaim_boundary")
    if not _string_list(boundary):
        failures.append(f"{display}: no_overclaim_boundary must be a non-empty string list")
        boundary = []
    boundary_text = " ".join(boundary).lower()
    for token in BOUNDARY_TOKENS:
        if token.lower() not in boundary_text:
            failures.append(f"{display}: missing flow-unit runtime boundary token `{token}`")

    flow_units = state.get("flow_units")
    if not isinstance(flow_units, list) or not flow_units:
        failures.append(f"{display}: flow_units must be a non-empty list")
        flow_units = []
    seen = []
    unit_by_id = {}
    directly_blocked = set()
    for unit in flow_units:
        if not isinstance(unit, dict):
            failures.append(f"{display}: each flow unit must be an object")
            continue
        unit_id = unit.get("flow_unit_id")
        label = f"{display}: flow unit {unit_id or '<missing>'}"
        if not isinstance(unit_id, str) or not unit_id.strip():
            failures.append(f"{label}: flow_unit_id must be a non-empty string")
            continue
        seen.append(unit_id)
        unit_by_id[unit_id] = unit
        for field in REQUIRED_FLOW_FIELDS:
            if field not in unit:
                failures.append(f"{label}: missing required field `{field}`")
        if unit.get("lifecycle_mode") not in {ACTIVE_MODE, DYNAMIC_MODE}:
            failures.append(f"{label}: lifecycle_mode must be classic-phase-gate or dynamic-flow-gate")
        if unit.get("current_stage") not in STAGES:
            failures.append(f"{label}: current_stage must reference classic stage vocabulary")
        if not isinstance(unit.get("gate_lane"), str) or not unit.get("gate_lane"):
            failures.append(f"{label}: gate_lane must be a non-empty string")
        gate_refs = unit.get("gate_references")
        if not _string_list(gate_refs):
            failures.append(f"{label}: gate_references must be a non-empty string list")
        else:
            for gate_id in gate_refs:
                if gate_id not in GATES:
                    failures.append(f"{label}: unknown gate reference `{gate_id}`")
        for field in ("dependencies", "blockers", "evidence_refs"):
            if not isinstance(unit.get(field), list):
                failures.append(f"{label}: {field} must be a list")
        loop_state = unit.get("loop_state")
        if not isinstance(loop_state, dict):
            failures.append(f"{label}: loop_state must be an object")
        else:
            loop_count = loop_state.get("loop_count")
            if isinstance(loop_count, bool) or not isinstance(loop_count, int) or loop_count < 0:
                failures.append(f"{label}: loop_state.loop_count must be a non-negative integer")
        gate_state = unit.get("gate_state")
        if not isinstance(gate_state, dict):
            failures.append(f"{label}: gate_state must be an object")
        elif gate_state.get("status") not in ALLOWED_GATE_STATUSES:
            failures.append(f"{label}: gate_state.status is not allowed")
        if unit.get("blockers") or (isinstance(gate_state, dict) and gate_state.get("status") == "blocked"):
            directly_blocked.add(unit_id)

    duplicates = sorted({unit_id for unit_id in seen if seen.count(unit_id) > 1})
    for unit_id in duplicates:
        failures.append(f"{display}: duplicate flow_unit_id `{unit_id}`")
    for unit_id, unit in unit_by_id.items():
        for dep in unit.get("dependencies", []) if isinstance(unit.get("dependencies"), list) else []:
            if dep not in unit_by_id:
                failures.append(f"{display}: flow unit {unit_id} has unknown dependency `{dep}`")

    active_lanes = {}
    for unit_id, unit in unit_by_id.items():
        lane = unit.get("gate_lane")
        if lane:
            active_lanes.setdefault(lane, []).append(unit_id)
    declared_lanes = state.get("active_lanes")
    if declared_lanes is not None and declared_lanes != active_lanes:
        failures.append(f"{display}: active_lanes must match flow_units by gate_lane")
    expected_downstream = sorted([
        unit_id for unit_id, unit in unit_by_id.items()
        if any(dep in directly_blocked for dep in unit.get("dependencies", []))
    ])
    declared_downstream = state.get("blocked_downstream_units")
    if not isinstance(declared_downstream, list):
        failures.append(f"{display}: blocked_downstream_units must be a list")
        declared_downstream = []
    if sorted(declared_downstream) != expected_downstream:
        failures.append(f"{display}: blocked_downstream_units must include only declared downstream dependents")
    if any(unit_id in declared_downstream for unit_id in directly_blocked):
        failures.append(f"{display}: directly blocked units must not be listed as downstream")
    if not isinstance(state.get("rollup_status"), str) or not state.get("rollup_status", "").strip():
        failures.append(f"{display}: rollup_status must be a non-empty string")

    for text in _text_values(state):
        lowered = text.lower()
        for label, pattern in FORBIDDEN_OVERCLAIMS:
            for match in pattern.finditer(lowered):
                claim = text[match.start():match.end()]
                if not _claim_is_negated(text, claim):
                    failures.append(f"{display}: forbidden flow-unit runtime overclaim `{label}`")
                    break
        if "declarative gate engine active" in lowered:
            failures.append(f"{display}: forbidden declarative gate engine activation wording")
        if "sibling completion implied" in lowered:
            failures.append(f"{display}: sibling completion must not be implied")
    return failures


# ═══════════════════════════════════════════════════════════════════════════
# FEAT-002 (ADR-013 / 0.67.0) — Version router.
#
# ``validate_flow_unit_runtime_payload`` ABOVE is the byte-frozen visibility-v1
# validator (the 0.52.0/0.66.1 containment boundary). FEAT-002 does NOT modify
# it. This dispatcher is the ONLY addition: it reads ``schema_version`` and
# routes a payload to the correct validator. v1 (``"1.0"`` or absent) → v1
# validator UNCHANGED; v2 (``"2.0"``) → the new v2 validator in
# ``flow_unit_runtime_v2.py``; unknown → fail. Both validators return the same
# ``list[str]`` shape (empty ⇒ valid), so callers see a uniform interface.
# ═══════════════════════════════════════════════════════════════════════════


def validate_flow_unit_runtime_payload_dispatch(state, display=".governance/flow-unit-runtime.json", plugin_home=None):
    """Route a flow-unit runtime payload to the version-correct validator.

    Reads ``schema_version`` from ``state`` and dispatches:

      - ``"1.0"`` (or absent / non-string) → :func:`validate_flow_unit_runtime_payload`
        (the byte-frozen visibility-v1 validator, UNCHANGED).
      - ``"2.0"`` → :func:`flow_unit_runtime_v2.validate_flow_unit_runtime_payload_v2`
        (the new Loop Runtime Contract v2 validator).
      - any other value → a single-element failure list (fail-closed).

    Returns a ``list[str]`` of failures (empty ⇒ valid), matching the shape both
    validators already return. This dispatcher never raises.

    Args:
        state: the in-memory flow-unit runtime payload dict.
        display: the display path used in failure messages.
        plugin_home: optional plugin-home override (forwarded to the v2
            validator's schema loader; accepted by v1 for API symmetry and
            ignored by v1, which does not load a schema).

    Returns:
        list[str]: empty if the payload is valid under its declared version;
        otherwise one specific failure string per violation.
    """
    if not isinstance(state, dict):
        # Non-dict root: route to v1, which already produces the canonical
        # "root must be an object" failure. (v2 would produce the equivalent.)
        return validate_flow_unit_runtime_payload(state, display)

    schema_version = state.get("schema_version")

    # v1: schema_version "1.0" OR absent (legacy visibility payloads). Routed
    # to the byte-frozen v1 validator UNCHANGED.
    if schema_version == "2.0":
        # Deferred import to keep v1 byte-frozen and avoid importing the v2
        # module (and transitively the contract schema loader) when only v1 is
        # needed. The v2 validator is a peer module in the same ``checks``
        # package, so the import uses the package-qualified path (same
        # convention as loop_migration.py / verify_workflow.py importing v1).
        from checks.flow_unit_runtime_v2 import validate_flow_unit_runtime_payload_v2  # noqa: WPS433
        return validate_flow_unit_runtime_payload_v2(state, display, plugin_home)

    if schema_version in ("1.0", 1) or schema_version is None:
        return validate_flow_unit_runtime_payload(state, display)

    # Unknown schema_version → fail-closed. Do NOT silently route to v1 (a
    # future "3.0" must not be validated by either v1 or v2 by accident).
    return [
        f"{display}: unsupported schema_version `{schema_version}` "
        f"(expected '1.0' for visibility-v1 or '2.0' for loop-runtime-contract/v2)"
    ]
