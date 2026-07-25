#!/usr/bin/env python3
"""Shared migration planner + immutable plan hash — FEAT-003 (ADR-013 §4, 0.67.0).

This module is the PURE planner extracted from ``loop_migration.apply_migration``
(steps 1-4: resolve root, read plan-tracker, derive units, build payload). It is
the single place that derives a migration plan; both the dry-run
(``preview_migration``) and apply (``apply_migration``) paths call
:func:`build_migration_plan`, which is what makes the REL-059 dry-run/apply
identity invariant executable: two calls with identical arguments return an
identical ``plan_hash``.

**Purity contract (load-bearing, ADR §4.1):** this module holds NO module-level
mutable state, caches nothing that accumulates across calls, and is fully
deterministic. This mirrors the sacred ``derive_round`` purity (ADR §8.2). A
threading test is mandatory and is provided in
``tests/test_loop_migration_plan.py``.

**Boundary (ADR §4.5):** this module imports only PEERS — ``resolve_entry``
(RISK-040 root resolution), ``flow_unit_derive`` (heuristic unit derivation),
and the FEAT-002 contract schema loader (``checks.flow_unit_runtime_v2``). It
does NOT import ``verify_workflow`` or ``loop_migration`` (avoids the cycle,
same discipline as ``loop_engine``/``loop_health``).

**Decomposition (ADR §5):** :func:`build_migration_plan` always returns a plan
with ``decomposition_confirmed=False``. :func:`confirm_decomposition` is the
FEAT-004 hook that flips the flag; FEAT-003 provides only the stub. A v2
payload built from an unconfirmed plan fails the v2 validator's
``decomposition_confirmed`` requirement — that is the executable containment
guard until FEAT-004.

Usage:
    from loop_migration_plan import (
        build_migration_plan, plan_to_payload, confirm_decomposition,
        MigrationPlan, MigrationPlanOptions, UnitPlan,
    )
"""

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, replace as _dc_replace, field as _dc_field
from pathlib import Path

# ─── Fixed anchors ─────────────────────────────────────────────
# PLUGIN_HOME is derived from __file__ ONLY to locate the plugin's own
# declarative files (the registries + the FEAT-002 contract schema). It is
# NEVER used as the facts root (RISK-040). Same convention as the peer modules.
# This file lives at PLUGIN_HOME/infra/loop_migration_plan.py, so
# .parent.parent == PLUGIN_HOME.
PLUGIN_HOME = Path(__file__).resolve().parent.parent

# ─── Peer imports (no verify_workflow / loop_migration dependency) ───────────
# resolve_entry: pure stdlib, gives HOST_PROJECT_ROOT (never PLUGIN_HOME).
from resolve_entry import resolve_host_root  # noqa: E402

# flow_unit_derive: pure stdlib, heuristic unit derivation (stays advisory).
from flow_unit_derive import derive_flow_units  # noqa: E402

# FEAT-002 contract schema loader (fail-closed (data, issues) contract).
from checks.flow_unit_runtime_v2 import load_loop_runtime_contract  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# Constants — the contract version this planner targets (ADR §4.1)
# ═══════════════════════════════════════════════════════════════════════════

SCHEMA_VERSION = "2.0"
CONTRACT_ID = "loop-runtime-contract/v2"
WORKFLOW_MODEL_NEW = "loop-engineering"

# The base id of the gate schema named by loop-engineering-registry.json's
# loop_gate_semantics (ADR §4.3). The value carried on MigrationPlan.gate_schema
# is this id suffixed with a short content digest of the registry's
# loop_gate_semantics, so a registry re-mapping (e.g. G6's enclosing_loop)
# produces a different gate_schema → different plan_hash. This is what makes
# §4.3's "a change to the registry's gate semantics produces a different plan
# hash" literally true.
_GATE_SCHEMA_ID_BASE = "loop-gate-schema-v1"

# Relative path (from PLUGIN_HOME) to the loop-engineering registry carrying
# loop_gate_semantics.
_LOOP_ENGINEERING_REGISTRY_REL = "core/loop-engineering-registry.json"

# Regex for finding the prior workflow_model in the plan-tracker. Mirrors
# loop_migration._WORKFLOW_MODEL_LINE_RE (kept independent here to preserve the
# no-loop_migration-import constraint).
_WORKFLOW_MODEL_LINE_RE = re.compile(
    r"(?im)^\s*[*-]?\s*(?:workflow_model|workflow\s*model|current_workflow_model|"
    r"active_workflow_model|lifecycle_model|工作流模型|当前工作流模型)"
    r"\s*[:：=]\s*(.+?)\s*$"
)

# Migration version stamped on payloads produced by this planner. The contract
# only requires it be a non-empty string; the migration's own version stamp is
# owned by loop_migration.MIGRATION_VERSION and forwarded through
# plan_to_payload's migration_version argument. This default mirrors it so a
# standalone plan_to_payload call yields a contract-shaped payload.
DEFAULT_MIGRATION_VERSION = "0.65.0"


# ═══════════════════════════════════════════════════════════════════════════
# Hashing — the NFC-then-SHA-256 idiom (matches loop_runtime_claims._sha_text)
# ═══════════════════════════════════════════════════════════════════════════


def _sha_text(text):
    """SHA-256 hexdigest of the NFC-normalized UTF-8 encoding of ``text``.

    This is the canonical idiom used across the loop-runtime claim surface
    (``infra/checks/loop_runtime_claims.py:_sha_text``). ADR §4.2 step 3 +
    contract design-review note F2 both require the plan hash reuse this exact
    NFC-then-sha256 normalization. Duplicated locally (5 lines) to preserve the
    no-cross-module-import constraint on the planner.
    """
    return hashlib.sha256(unicodedata.normalize("NFC", text).encode("utf-8")).hexdigest()


def _load_loop_gate_semantics_digest(plugin_home=None):
    """Return a stable digest of the registry's ``loop_gate_semantics``.

    Reads ``loop-engineering-registry.json`` (fail-closed: a missing/corrupt
    registry digests the empty list, so the result is still deterministic).
    The digest is what makes ``gate_schema`` registry-content-sensitive per
    ADR §4.3 — a re-mapping of any gate's ``loop_role`` / ``enclosing_loop`` /
    ``on_fail`` / ``fuse_ref`` changes the canonical JSON and thus the digest.

    Returns the first 12 lowercase hex chars of the SHA-256 over the canonical
    JSON of the semantics list (sorted keys, compact separators, NFC).
    """
    home = Path(plugin_home) if plugin_home is not None else PLUGIN_HOME
    registry_path = home / _LOOP_ENGINEERING_REGISTRY_REL
    semantics = []
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            sem = data.get("loop_gate_semantics")
            if isinstance(sem, list):
                semantics = sem
    except (OSError, json.JSONDecodeError):
        semantics = []  # fail-closed → deterministic empty-list digest
    canonical = json.dumps(
        semantics, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return _sha_text(canonical)[:12]


def _resolve_gate_schema(plugin_home=None):
    """Return the gate_schema string: ``<id>@<content-digest>`` (ADR §4.3).

    The base id names the gate schema version; the ``@<digest>`` suffix is the
    registry-derived content tag. Two registries with different gate semantics
    produce different suffixes → different gate_schema → different plan_hash.
    """
    return "{0}@{1}".format(_GATE_SCHEMA_ID_BASE, _load_loop_gate_semantics_digest(plugin_home))


# ═══════════════════════════════════════════════════════════════════════════
# Small helpers (mirrors of peer-module logic, kept independent)
# ═══════════════════════════════════════════════════════════════════════════


def parse_workflow_model(plan_text):
    """Extract the workflow_model value from a plan-tracker.

    Returns the matched value (lowercased, stripped) or ``"unknown"`` if no
    workflow_model line is found. Mirrors ``loop_migration._parse_workflow_model``
    (kept independent here to avoid importing loop_migration). Used to record
    the PRIOR model for the rollback record (excluded from the hash).
    """
    if not plan_text:
        return "unknown"
    m = _WORKFLOW_MODEL_LINE_RE.search(plan_text)
    if not m:
        # Heuristic: presence of a Gate tracking table implies classic.
        if "## Gate 状态跟踪" in plan_text or "## gate 状态跟踪" in plan_text:
            return "classic-phase-gate"
        return "unknown"
    value = m.group(1).strip().lower()
    # Strip trailing inline-comment / list markers.
    value = re.split(r"[;；#]", value, maxsplit=1)[0].strip()
    return value or "unknown"


def _derive_project_id(target_root):
    """Derive a stable project_id from target_root basename.

    Mirrors ``flow_unit_derive._derive_project_id`` exactly so the planner's
    project_id agrees with the derived units' flow_unit_id prefix. Lowercased,
    alphanumerics + ``.`` + ``-`` kept, everything else collapsed to ``-``.
    """
    if target_root is None:
        return "unknown-project"
    try:
        name = Path(str(target_root)).name
    except Exception:  # pragma: no cover - defensive
        return "unknown-project"
    if not name:
        return "unknown-project"
    sanitized = re.sub(r"[^a-z0-9.\-]+", "-", name.lower())
    sanitized = re.sub(r"-{2,}", "-", sanitized).strip("-")
    return sanitized or "unknown-project"


def _read_plan_tracker_text(target_root):
    """Best-effort read of ``<target_root>/.governance/plan-tracker.md``.

    Returns the file text, or ``""`` if missing/unreadable. Never raises
    (fail-closed: missing tracker → empty text → derive_flow_units fallback).
    Mirrors ``flow_unit_derive._read_plan_tracker``.
    """
    try:
        pt = Path(str(target_root)) / ".governance" / "plan-tracker.md"
    except Exception:  # pragma: no cover - defensive
        return ""
    try:
        return pt.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _resolve_target_root(target_root):
    """Resolve target_root to a string host root (RISK-040: never PLUGIN_HOME).

    Priority: explicit target_root (must resolve to an existing dir) →
    resolve_entry.resolve_host_root(None) (which tries os.getcwd()). Raises
    ValueError if neither resolves — the caller (apply/preview) fail-closes.
    """
    if target_root is not None:
        candidate = Path(str(target_root)).expanduser()
        try:
            candidate = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            raise ValueError(
                "target_root {0!r} did not resolve to an existing directory".format(
                    target_root
                )
            )
        if not candidate.is_dir():
            raise ValueError(
                "target_root {0!r} is not a directory".format(target_root)
            )
        return str(candidate)
    host_root = resolve_host_root(None)
    if host_root is None:
        raise ValueError(
            "HOST_PROJECT_ROOT unresolvable (no target_root and cwd unavailable)"
        )
    return str(host_root)


# ═══════════════════════════════════════════════════════════════════════════
# Frozen dataclasses (ADR §4.1)
# ═══════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class UnitPlan:
    """Per-unit migration plan (ADR §4.1).

    A frozen, hashable snapshot of one derived flow unit's plan-relevant
    fields. Carried on ``MigrationPlan.units``; the structural identity fields
    (``flow_unit_id``) feed the plan hash via ``MigrationPlan.unit_ids``.
    """

    flow_unit_id: str
    unit_type: str
    title: str
    derivation_reason: str
    entry_tier: str
    dependencies: tuple = ()  # tuple[str, ...] — frozen-friendly


@dataclass(frozen=True)
class MigrationPlan:
    """The immutable migration plan (ADR §4.1).

    All load-bearing structural identity fields are frozen. ``plan_hash`` is
    computed inside :func:`build_migration_plan` over the canonical JSON of the
    load-bearing fields (§4.2) and is itself excluded from the hash input.
    ``target_root`` is carried for traceability but is EXCLUDED from the hash
    (the REL-059 invariant is about derived structure, not the host path).
    """

    schema_version: str
    contract_id: str
    target_root: str
    project_type: str
    project_id: str
    workflow_model_prior: str
    workflow_model_new: str
    unit_ids: tuple  # tuple[str, ...]
    unit_count: int
    units: tuple  # tuple[UnitPlan, ...]
    gate_schema: str
    decomposition_confirmed: bool
    plan_hash: str


@dataclass
class MigrationPlanOptions:
    """Optional configuration for :func:`build_migration_plan` / apply.

    ``confirm_decomposition`` defaults to False — FEAT-003 always builds
    unconfirmed plans; FEAT-004 sets True (or the caller uses
    :func:`confirm_decomposition`). ``expected_plan_hash`` is the apply-path
    hash-verification knob: when supplied, apply re-derives the plan and
    asserts the re-derived hash equals this value (fail-closed on mismatch).
    """

    confirm_decomposition: bool = False
    expected_plan_hash: str = None


# ═══════════════════════════════════════════════════════════════════════════
# The immutable plan hash (ADR §4.2)
# ═══════════════════════════════════════════════════════════════════════════


def compute_plan_hash(
    *,
    contract_id,
    project_id,
    project_type,
    schema_version,
    unit_count,
    unit_ids,
    workflow_model_new,
    gate_schema,
):
    """Return the 64-lowercase-hex plan hash over the load-bearing fields.

    Implements ADR §4.2 exactly:
      1. Build a dict with EXACTLY these keys: contract_id, project_id,
         project_type, schema_version, unit_count, unit_ids,
         workflow_model_new, gate_schema. (decomposition_confirmed,
         target_root, plan_hash itself, timestamps, and workflow_model_prior
         are EXCLUDED — not load-bearing for the dry-run/apply identity.)
      2. Serialize as JSON: ensure_ascii=False, sort_keys=True,
         separators=(",", ":"), UTF-8.
      3. NFC normalize the resulting text (matches _sha_text /
         loop_runtime_claims._sha_text).
      4. hashlib.sha256(nfc_bytes).hexdigest() — 64 lowercase hex.

    Exposed publicly so dry-run and apply can each re-derive/verify the hash
    from the same canonical inputs. Pure: no I/O, no module state.
    """
    unit_ids_list = list(unit_ids) if not isinstance(unit_ids, (list, tuple)) else list(unit_ids)
    payload = {
        "contract_id": contract_id,
        "project_id": project_id,
        "project_type": project_type,
        "schema_version": schema_version,
        "unit_count": unit_count,
        "unit_ids": unit_ids_list,
        "workflow_model_new": workflow_model_new,
        "gate_schema": gate_schema,
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return _sha_text(canonical)


# ═══════════════════════════════════════════════════════════════════════════
# build_migration_plan — the PURE function (ADR §4.1, §4.4)
# ═══════════════════════════════════════════════════════════════════════════


def build_migration_plan(
    target_root,
    project_type=None,
    *,
    plan_tracker_text=None,
    plugin_home=None,
    options=None,
):
    """Build an immutable :class:`MigrationPlan` (ADR §4.1, §4.4).

    This is the PURE planner extracted from ``loop_migration.apply_migration``
    steps 1-4. Both dry-run and apply call it; identical arguments yield an
    identical ``plan_hash`` (the REL-059 dry-run/apply identity invariant).

    Steps:
      1. Resolve target_root via resolve_entry (RISK-040: never PLUGIN_HOME).
      2. Read plan-tracker text (from ``plan_tracker_text`` or the file).
      3. Parse workflow_model_prior from the plan-tracker.
      4. Derive flow units via ``flow_unit_derive.derive_flow_units`` (advisory).
      5. Build the UnitPlan tuple from the derived units.
      6. Determine gate_schema from loop-engineering-registry.json's
         loop_gate_semantics (ADR §4.3).
      7. Compute plan_hash over the load-bearing fields (ADR §4.2).
      8. Return a frozen MigrationPlan.

    Args:
        target_root: Host project root (str/Path). If None, resolved from cwd.
        project_type: One of the 7 presets; None → ``"ai-agent-plugin"``.
        plan_tracker_text: Optional pre-loaded plan-tracker text (tests/dry-run).
        plugin_home: Optional registry/contract override (tests).
        options: Optional :class:`MigrationPlanOptions`.

    Returns:
        A frozen :class:`MigrationPlan` with ``decomposition_confirmed=False``
        (FEAT-003; FEAT-004 confirms via :func:`confirm_decomposition`).

    Raises:
        ValueError: if target_root cannot be resolved to an existing directory
            (RISK-040 fail-closed). The apply/preview callers catch this and
            fail-closed themselves.
    """
    opts = options if isinstance(options, MigrationPlanOptions) else MigrationPlanOptions()

    # ── Step 1: resolve target_root (RISK-040: never PLUGIN_HOME) ───────────
    resolved_root = _resolve_target_root(target_root)

    # ── Step 2: read plan-tracker text ──────────────────────────────────────
    if plan_tracker_text is None:
        plan_text = _read_plan_tracker_text(resolved_root)
    else:
        plan_text = plan_tracker_text

    # ── Step 3: parse workflow_model_prior (for the rollback record) ────────
    workflow_model_prior = parse_workflow_model(plan_text)

    # ── Step 4: derive flow units (advisory; stays heuristic per FEAT-004) ──
    chosen_project_type = project_type or "ai-agent-plugin"
    flow_units = derive_flow_units(
        resolved_root, chosen_project_type,
        plan_tracker_text=plan_text, plugin_home=plugin_home,
    )

    # ── Step 5: build the UnitPlan tuple (ordered, deduped by flow_unit_id) ─
    seen_ids = set()
    unit_plans = []
    ordered_ids = []
    for unit in flow_units:
        if not isinstance(unit, dict):
            continue
        fuid = unit.get("flow_unit_id")
        if not isinstance(fuid, str) or not fuid.strip():
            continue
        if fuid in seen_ids:
            continue
        seen_ids.add(fuid)
        ordered_ids.append(fuid)
        deps = unit.get("dependencies")
        deps_tuple = tuple(deps) if isinstance(deps, (list, tuple)) else ()
        deps_tuple = tuple(d for d in deps_tuple if isinstance(d, str))
        reason = unit.get("derivation_reason")
        if not isinstance(reason, str) or not reason.strip():
            # Non-fallback derived units do not carry an explicit reason; give
            # them an explicit, non-empty heuristic provenance so the eventual
            # v2 payload (after FEAT-004 confirmation) satisfies the
            # derivation_reason-non-empty rule.
            reason = "heuristic-derivation:{0}".format(unit.get("unit_type", "unit"))
        unit_plans.append(
            UnitPlan(
                flow_unit_id=fuid,
                unit_type=str(unit.get("unit_type", "")),
                title=str(unit.get("title", fuid)),
                derivation_reason=reason,
                entry_tier="setup",  # dormant units begin at the setup tier
                dependencies=deps_tuple,
            )
        )

    # Defensive: derive_flow_units always yields ≥1 unit, but guard anyway so a
    # future regression can never produce an empty plan (mirrors apply's guard).
    if not unit_plans:
        project_id = _derive_project_id(resolved_root)
        fallback_id = "{0}.script.fallback".format(project_id)
        ordered_ids = [fallback_id]
        unit_plans = [
            UnitPlan(
                flow_unit_id=fallback_id,
                unit_type="script",
                title="{0} (fallback whole project)".format(project_id),
                derivation_reason="no-decomposable-structure-found",
                entry_tier="setup",
                dependencies=(),
            )
        ]
    else:
        project_id = _derive_project_id(resolved_root)

    unit_ids_tuple = tuple(ordered_ids)
    unit_count = len(unit_plans)

    # ── Step 6: determine gate_schema from the registry (ADR §4.3) ──────────
    gate_schema = _resolve_gate_schema(plugin_home)

    # ── Step 7: compute plan_hash (ADR §4.2) ────────────────────────────────
    plan_hash = compute_plan_hash(
        contract_id=CONTRACT_ID,
        project_id=project_id,
        project_type=chosen_project_type,
        schema_version=SCHEMA_VERSION,
        unit_count=unit_count,
        unit_ids=unit_ids_tuple,
        workflow_model_new=WORKFLOW_MODEL_NEW,
        gate_schema=gate_schema,
    )

    # ── Step 8: return the frozen plan ──────────────────────────────────────
    return MigrationPlan(
        schema_version=SCHEMA_VERSION,
        contract_id=CONTRACT_ID,
        target_root=resolved_root,
        project_type=chosen_project_type,
        project_id=project_id,
        workflow_model_prior=workflow_model_prior,
        workflow_model_new=WORKFLOW_MODEL_NEW,
        unit_ids=unit_ids_tuple,
        unit_count=unit_count,
        units=tuple(unit_plans),
        gate_schema=gate_schema,
        # FEAT-003 always builds unconfirmed plans. FEAT-004 confirms via
        # confirm_decomposition; the v2 validator's decomposition_confirmed
        # requirement is the executable containment guard until then.
        decomposition_confirmed=bool(opts.confirm_decomposition),
        plan_hash=plan_hash,
    )


# ═══════════════════════════════════════════════════════════════════════════
# plan_to_payload — the plan → v2 runtime payload bridge (ADR §3.2/3.3, §5.3)
# ═══════════════════════════════════════════════════════════════════════════


def _dormant_initial_loop_state():
    """Return the canonical 9-field DORMANT initial loop_state (ADR §3.4, §5.3).

    FEAT-003 builds dormant units only. The 9-field shape is the v2 TARGET
    (contract design-review note F1); populating it here means the ONLY v2
    validation failure for an unconfirmed plan is decomposition_confirmed —
    making the FEAT-004 containment guard crisp. ``active_loop`` is False
    (dormant), which satisfies the runtime_status⇔active_loop implication for
    ``runtime_status="dormant"``.
    """
    return {
        "active_loop": False,
        "active_loop_tier": None,
        "loop_count": 0,
        "last_loop_type": None,
        "agent_phase": "plan",
        "iteration_within_inner": 0,
        "pause_points_active": [],
        "last_gate_result": None,
        "fuse": {"max_rounds": 2, "tripped": False},
    }


def _initial_gate_state():
    """Return the canonical initial gate_state for a dormant unit (ADR §5.3)."""
    return {
        "status": "pending",
        "gate_id": "G1",  # setup-tier entry gate; validator requires non-empty
        "last_result": None,
        "evidence_refs": [],
    }


def plan_to_payload(plan, *, migration_version=None, migration_timestamp=None,
                    plugin_home=None):
    """Convert a :class:`MigrationPlan` to a v2 runtime payload dict.

    Produces a payload shaped per FEAT-002 contract §3.2/3.3 with ALL
    required_top_level_fields and per-unit fields populated. This is the bridge
    between the plan and the v2 validator: both dry-run and apply build the
    payload from the (re-derived) plan via this function, so they validate the
    SAME structure (the REL-059 invariant, made executable).

    ``decomposition_confirmed`` is forwarded from the plan: an unconfirmed plan
    (FEAT-003) yields a payload the v2 validator REJECTS — that is the
    executable containment guard (ADR §5.2). ``migration_plan_hash`` is set to
    ``plan.plan_hash`` so the persisted payload carries the structural identity
    the apply path re-derives and verifies.

    Args:
        plan: A :class:`MigrationPlan`.
        migration_version: Optional version stamp (defaults to
            :data:`DEFAULT_MIGRATION_VERSION`; the apply path forwards its own).
        migration_timestamp: Optional ISO-8601 timestamp (defaults to the
            current UTC time). Not load-bearing for the hash.
        plugin_home: Optional override forwarded to the contract schema loader.

    Returns:
        A v2 runtime payload dict. Never raises — a missing contract schema
        yields conservative defaults so the payload still has every required
        field (the v2 validator then reports any contract-load failure).
    """
    # Load the contract schema for runtime_scope / contract_source / boundary
    # tokens (fail-closed; mirror the v2 validator's loader).
    schema, _issues = load_loop_runtime_contract(plugin_home)
    if isinstance(schema, dict):
        runtime_scope = schema.get("runtime_scope", "loop-engineering-runtime")
        contract_source = schema.get("status_source", "loop-runtime-contract-v2")
        boundary_tokens = schema.get("no_overclaim_boundary_mandatory_tokens", [])
    else:
        runtime_scope = "loop-engineering-runtime"
        contract_source = "loop-runtime-contract-v2"
        boundary_tokens = []

    # Build the no_overclaim_boundary list: the contract's mandatory tokens
    # MUST each appear (the v2 validator checks every token is present).
    no_overclaim_boundary = list(boundary_tokens) if boundary_tokens else [
        "does not activate execution engine",
        "RISK-037 remains open",
        "RISK-042 remains open",
    ]

    if migration_version is None:
        migration_version = DEFAULT_MIGRATION_VERSION
    if migration_timestamp is None:
        from datetime import datetime, timezone
        migration_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    units = []
    for up in plan.units:
        deps = list(up.dependencies) if isinstance(up.dependencies, tuple) else []
        loop_state = _dormant_initial_loop_state()
        gate_state = _initial_gate_state()
        units.append({
            "flow_unit_id": up.flow_unit_id,
            "title": up.title,
            "unit_type": up.unit_type,
            "project_type": plan.project_type,
            "derivation_reason": up.derivation_reason,
            "loop_state": loop_state,
            "gate_state": gate_state,
            "runtime_status": "dormant",  # FEAT-003 builds dormant units only
            "dependencies": deps,
            "blockers": [],
        })

    return {
        "schema_version": plan.schema_version,
        "runtime_contract": plan.contract_id,
        "runtime_scope": runtime_scope,
        "workflow_model": plan.workflow_model_new,
        "contract_source": contract_source,
        "migration_version": migration_version,
        "migration_plan_hash": plan.plan_hash,
        "migration_timestamp": migration_timestamp,
        "decomposition_confirmed": bool(plan.decomposition_confirmed),
        "flow_units": units,
        "no_overclaim_boundary": no_overclaim_boundary,
    }


# ═══════════════════════════════════════════════════════════════════════════
# confirm_decomposition — the FEAT-004 hook (stub; ADR §4.5, §5.2)
# ═══════════════════════════════════════════════════════════════════════════


def confirm_decomposition(plan, *, approved_unit_ids=None, options=None):
    """Return a NEW :class:`MigrationPlan` with ``decomposition_confirmed=True``.

    FEAT-004 owns the full confirmation step (candidate-set validation, operator
    approval filtering, recomputed hash over the confirmed unit set — ADR §5.2).
    FEAT-003 provides ONLY this stub: it flips the flag via
    ``dataclasses.replace`` and leaves the unit set + hash UNCHANGED.

    ``decomposition_confirmed`` is EXCLUDED from the plan hash (ADR §4.2), so
    flipping the flag does NOT change ``plan_hash`` — the dry-run/apply identity
    invariant holds across the confirmation boundary. FEAT-004 will recompute
    the hash when the confirmed unit set differs from the candidate set.

    Args:
        plan: A :class:`MigrationPlan` (unconfirmed).
        approved_unit_ids: Reserved for FEAT-004 (operator-approved subset).
            Ignored by this stub.
        options: Reserved for FEAT-004.

    Returns:
        A new frozen :class:`MigrationPlan` identical to ``plan`` except
        ``decomposition_confirmed=True``. ``plan_hash`` is unchanged.
    """
    # approved_unit_ids / options are accepted for FEAT-004 signature stability
    # but intentionally unused here (FEAT-003 stub).
    return _dc_replace(plan, decomposition_confirmed=True)


# ═══════════════════════════════════════════════════════════════════════════
# plan_as_dict — serialization helper for the dry-run result (ADR §4.4)
# ═══════════════════════════════════════════════════════════════════════════


def plan_as_dict(plan):
    """Serialize a :class:`MigrationPlan` to a JSON-friendly dict.

    Used by the dry-run path to emit the plan (including ``plan_hash``) in the
    preview result. Tuples become lists so the dict is JSON-serializable.
    """
    return {
        "schema_version": plan.schema_version,
        "contract_id": plan.contract_id,
        "target_root": plan.target_root,
        "project_type": plan.project_type,
        "project_id": plan.project_id,
        "workflow_model_prior": plan.workflow_model_prior,
        "workflow_model_new": plan.workflow_model_new,
        "unit_ids": list(plan.unit_ids),
        "unit_count": plan.unit_count,
        "units": [
            {
                "flow_unit_id": u.flow_unit_id,
                "unit_type": u.unit_type,
                "title": u.title,
                "derivation_reason": u.derivation_reason,
                "entry_tier": u.entry_tier,
                "dependencies": list(u.dependencies),
            }
            for u in plan.units
        ],
        "gate_schema": plan.gate_schema,
        "decomposition_confirmed": plan.decomposition_confirmed,
        "plan_hash": plan.plan_hash,
    }


if __name__ == "__main__":  # pragma: no cover - manual smoke
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    plan = build_migration_plan(None)
    print(json.dumps(plan_as_dict(plan), ensure_ascii=False, indent=2))
