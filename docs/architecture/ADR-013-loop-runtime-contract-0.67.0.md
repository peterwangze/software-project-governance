# ADR-013: Loop Runtime Contract 0.67.0 — Canonical Contract, Shared Planner, Decomposition Confirmation

- Status: PROPOSED / READY_FOR_DESIGN_REVIEW
- Date: 2026-07-23
- Version scope: 0.67.0
- Tasks: FEAT-002 (canonical versioned Loop Runtime Contract), FEAT-003 (shared migration planner + immutable plan hash), FEAT-004 (decomposition confirmation + canonical initial gate state)
- Release: REL-059 (0.67.0 — Canonical runtime and planner)
- Authority: DEC-104, AUDIT-133, EVD-707, DEC-097/098/099, AUDIT-130, ADR-011, ADR-012, `docs/requirements/loop-engineering-architecture-0.65.0-proposed.md` (R1 APPROVED)
- Review authority required: independent Design Review (REVIEW-FEAT-002-DESIGN-R0 chain or the Coordinator's designated reviewer); this ADR is design-only and does not self-approve any FEAT task
- Reversibility: the contract schema is versioned and additive (v1 runs alongside the existing visibility-v1 contract); the planner is pure and reversible; FEAT-002~004 do NOT activate any runtime execution engine and do NOT close RISK-037/RISK-042

> **Design-only ADR.** This document specifies the canonical contract schema, the pure migration planner signature, and the decomposition/initial-state contract for 0.67.0. It is written by the Architect role for Design Reviewer review. It does not implement code, does not dispatch a Developer, and does not authorize a release. Each of FEAT-002, FEAT-003, FEAT-004 requires its own DEC + Developer + Code Reviewer + QA cycle per the governance workflow.

---

## 1. Context

### 1.1 DEC-104 roadmap (the binding plan)

DEC-104 (2026-07-11) adopted a runtime-first repair roadmap for Loop Engineering after AUDIT-133 proved the 0.65.0 implementation was schema-only and its outputs were rejected by the canonical validator:

- **0.66.1** — fail-closed containment only (FIX-195/196/197~212): migration apply validates before write and refuses to write a runtime the official validator rejects; health authority fails closed; active wording corrected. Done as containment, not activation.
- **0.67.0 (this ADR)** — canonical versioned Loop Runtime Contract + single shared migration planner (FEAT-002~004). One contract; one plan; dry-run and apply share the same plan.
- **0.68.0** — persistent Plan-Act-Observe-Reflect state machine + production gate back-edge/fuse (FEAT-005~007). The execution engine.
- **0.69.0** — production telemetry + dogfood + two external project-type validation (FEAT-008, VAL-008/009).
- **0.70.0** — verify_workflow Phase 5 extraction (deferred from the original 0.67.0 scope).

0.67.0 is deliberately scoped to **contract + planner + initial state**, NOT execution. RISK-037 and RISK-042 remain open until the runtime execution engine (0.68.0) and external validation (0.69.0) are both complete.

### 1.2 AUDIT-133 findings (the problem this ADR solves)

AUDIT-133 (2026-07-11) audited the actual code, the temporary CLI, the real `shitu` artifact, and 99 special-purpose tests. Its load-bearing findings:

1. **Design direction PARTIAL-MET** — the loop-engineering architecture (`docs/requirements/loop-engineering-architecture-0.65.0-proposed.md`, R1 APPROVED) is sound and is retained.
2. **Runtime activation NOT_MET** — the production lifecycle remains classic active/default; loop code is schema-only (`registry_mode: "schema-only-no-runtime-activation"`); core loop transition APIs (`derive_round`, `fuse_decision`, `escalation_payload`, `activate_loop_state`) have **zero production call sites**.
3. **Migration validity NOT_MET** — `loop_migration.apply_migration` builds a payload with `workflow_model: "loop-engineering"` that the canonical validator (`checks/flow_unit_runtime.py`) **rejects** (21 issues on the temp target, 19 on real `shitu`). Apply therefore fails before write today (the 0.66.1 containment), which is correct but means there is no valid loop runtime to install.
4. **External effectiveness NOT_PROVEN** — VAL-007 ran apply on `shitu` but proved only a single derived unit; multi-unit / multi-lane / installed-state full PASS was never demonstrated.
5. **Health authority fail-open (fixed in 0.66.1)** — FIX-196 made `loop_health` fail closed on missing/corrupt registry.
6. **Field drift** — the five consumers (writer/validator/reader/rollup/health) each read different field sets from `flow-unit-runtime.json`. There is no single contract they share.

### 1.3 Current codebase state (the concrete grounding)

The five consumers today read **inconsistent** shapes:

| Consumer | File | Field set it reads/requires |
|----------|------|------------------------------|
| **Writer** | `infra/loop_migration.py` (`apply_migration`) | Writes `workflow_model: "loop-engineering"`, `migration_version`, `migration_timestamp`, `source`, `flow_units` (from `derive_flow_units`), `no_overclaim_boundary`. Per-unit `loop_state` is the FX-189 9-field shape (`active_loop`, `active_loop_tier`, `loop_count`, `last_loop_type`, `agent_phase`, `iteration_within_inner`, `pause_points_active`, `last_gate_result`, `fuse`). No `current_stage`, no `gate_state`, no `runtime_status_source`, no `rollup_status`. |
| **Validator** | `infra/checks/flow_unit_runtime.py` (`validate_flow_unit_runtime_payload`) | **visibility-v1 contract.** Requires `schema_version: 1.0`, `runtime_scope: "runtime-visibility-only"`, `workflow_model ∈ {classic-phase-gate, dynamic-flow-gate}` (loop-engineering is REJECTED), `default_lifecycle_mode: classic-phase-gate`, `declarative_gate_engine: false`, `project_migration: false`, `runtime_status_source ∈ {hot-project-state, runtime-visibility-only, example-runtime-fixture}`, per-unit `current_stage` (classic vocabulary), `gate_lane`, `gate_references` (G1-G11), `gate_state.status` (classic 8-value enum), `runtime_status_source`, top-level `rollup_status`. |
| **Reader** | `infra/loop_engine.py` (`rollup_loop_state`) | Reads `flow_units[].loop_state.{active_loop, active_loop_tier, loop_count, agent_phase, last_gate_result, fuse.tripped}`. Does NOT read `current_stage`, `gate_state`, `runtime_status_source`, `rollup_status`. |
| **Health** | `infra/loop_health.py` | Reads registry `pause_points` (for Part 1) and runtime `velocity_history`, `dora` (for Part 2 + DORA). Does NOT read per-unit `loop_state` at all. |
| **Registry** | `core/loop-engineering-registry.json` | Declares `loop_gate_semantics`, `loop_fuses`, `pause_points`, `agent_intrinsic_loop.loop_state_fields` (9 fields), `back_edges`. `schema_version: 1.0`, `registry_mode: "schema-only-no-runtime-activation"`. |

**This is the drift FEAT-002 eliminates.** The writer emits loop-engineering fields the validator forbids; the validator requires classic fields the writer never emits; the reader reads a third (loop) field set; health reads a fourth. No two agree.

**Why the current validator must NOT be widened to accept loop-engineering:** the visibility-v1 contract is the 0.52.0/0.66.1 containment boundary. Widening it in place would silently re-admit the AUDIT-133 overclaim path. The correct fix is a **new versioned contract (`runtime-contract/v2`)** that the writer emits and a **new v2 validator** that accepts it, with the v1 validator preserved unchanged for classic/dynamic installations. This is FEAT-002.

### 1.4 The planner gap (FEAT-003 motivation)

Today, dry-run and apply take **completely different code paths**:

- `preview_migration` → `verify_workflow.build_dynamic_lifecycle_migration_preview` (a different module, a different derivation).
- `apply_migration` → inlined `derive_flow_units()` + inlined payload construction (steps 4-5 of the 9-step algorithm).

There is no shared plan object and no hash binding them. REL-059's acceptance criterion — "preview/apply plan hash identical" — is not satisfiable today because there is no plan hash at all. The 21/19 validator issues AUDIT-133 found are exactly the symptom: the dry-run preview reported a shape, apply built a different shape, and neither matched the contract. FEAT-003 extracts one pure `build_migration_plan()` that both paths call.

### 1.5 The decomposition gap (FEAT-004 motivation)

`derive_flow_units()` (FX-190) returns **dormant** units (`loop_state = {active_loop: false, loop_count: 0, last_loop_type: null}`) and never initializes gate/runtime status. There is no confirmation step between "heuristic derived N units" and "activate." AUDIT-133 found migration apply can write units that are effectively dormant or example-data-only while the surrounding code treats the runtime as active. FEAT-004 inserts a decomposition confirmation step and defines the canonical initial per-unit gate/loop/runtime status so a unit is never "masquerading as active" when it is actually dormant.

---

## 2. Decision

Adopt three coordinated, strictly-additive changes for 0.67.0:

1. **FEAT-002 — Canonical versioned Loop Runtime Contract (`runtime-contract/v2`).** Define ONE schema (fields, types, allowed values, version) consumed by writer, validator, reader, rollup, and health. The schema lives in a single source-of-truth file. The existing visibility-v1 validator is preserved unchanged; a new v2 validator accepts the loop-engineering shape. A version discriminator (`schema_version: "2.0"` + `runtime_contract: "loop-runtime-contract/v2"`) routes a payload to the correct validator. v1 and v2 coexist; no installed state is broken.

2. **FEAT-003 — Shared migration planner + immutable plan hash.** Extract a pure `build_migration_plan(target_root, project_type, options) -> MigrationPlan` from `loop_migration.apply_migration`. Dry-run serializes the plan + its hash; apply re-derives the plan, verifies the hash matches, then executes. The invariant: **same target → same unit IDs, same unit count, same project_type, same gate schema** in both dry-run and apply. The hash is SHA-256 over canonical JSON of the plan's load-bearing fields.

3. **FEAT-004 — Decomposition confirmation + canonical initial gate state.** Keep `derive_flow_units()` heuristic advisory. Add a confirmation step (`confirm_decomposition(plan, options) -> ConfirmedPlan`) that the operator/Coordinator approves the unit set before activation. Define the canonical initial per-unit state so an activated unit carries a real gate/loop/runtime status — never dormant, never example-data-only, when claimed active.

These three are sequenced **FEAT-002 → FEAT-003 → FEAT-004** (planner consumes the contract; decomposition consumes contract + planner). None activates the execution engine (0.68.0), none closes RISK-037/RISK-042, none claims 1.0.0 readiness.

---

## 3. Contract Schema Spec (FEAT-002)

### 3.1 Single source of truth

The canonical contract is defined in **one new file**:

```
skills/software-project-governance/core/loop-runtime-contract.json
```

This file is a **declarative schema** (data, like `loop-engineering-registry.json`), not code. It declares:

- `schema_version`: `"2.0"` (the contract version this file describes)
- `contract_id`: `"loop-runtime-contract/v2"`
- `runtime_scope`: `"loop-engineering-runtime"` (distinct from visibility-v1's `"runtime-visibility-only"`)
- `workflow_model`: `"loop-engineering"` (the only allowed value for v2; classic/dynamic stay on v1)
- `required_top_level_fields`: the exact list (see 3.2)
- `required_per_unit_fields`: the exact list (see 3.3)
- `allowed_gate_statuses`: the canonical enum (see 3.4)
- `allowed_loop_tiers`: `["setup", "inner", "middle", "outer"]`
- `allowed_agent_phases`: `["plan", "act", "observe", "reflect"]`
- `allowed_runtime_statuses`: `["active", "dormant", "blocked", "withdrawn"]`
- `status_source`: `"loop-runtime-contract-v2"` (the single source-of-truth token; replaces the visibility-v1 `runtime_status_source` enum)
- `no_overclaim_boundary`: the mandatory boundary tokens (preserved from visibility-v1 plus the 0.67.0 additions: "does not activate execution engine", "RISK-037 remains open", "RISK-042 remains open")

Code modules import the schema by loading this JSON (mirroring `loop_engine.load_loop_registry`). The schema is the authority; the validator, writer, reader, and health each load it and conform. There is no second copy of the field list anywhere.

### 3.2 Top-level fields (the v2 envelope)

A v2 runtime payload (`flow-unit-runtime.json` when `schema_version: "2.0"`) carries exactly:

| Field | Type | Allowed value / shape | Notes |
|-------|------|------------------------|-------|
| `schema_version` | string | `"2.0"` | Routes to the v2 validator. v1 (`"1.0"`) routes to the existing visibility-v1 validator unchanged. |
| `runtime_contract` | string | `"loop-runtime-contract/v2"` | Belt-and-braces discriminator; the v2 validator requires both `schema_version: "2.0"` AND this value. |
| `runtime_scope` | string | `"loop-engineering-runtime"` | Replaces visibility-v1's `"runtime-visibility-only"`. |
| `workflow_model` | string | `"loop-engineering"` | The only v2 value. Classic/dynamic installations keep `schema_version: "1.0"`. |
| `contract_source` | string | `"loop-runtime-contract-v2"` | The single source-of-truth token (replaces the visibility-v1 `runtime_status_source` enum). The reader, rollup, and health use this to confirm they are reading a v2 payload. |
| `migration_version` | string | e.g. `"0.67.0"` | The migration that produced this payload. |
| `migration_plan_hash` | string | 64-hex SHA-256 | **Immutable plan hash from FEAT-003.** The hash of the `build_migration_plan()` output that produced this payload. The validator verifies this matches a re-derived plan for the same target (FEAT-003 invariant). |
| `migration_timestamp` | string | ISO-8601 UTC | When apply ran. |
| `decomposition_confirmed` | boolean | `true` required for v2 | **FEAT-004.** A v2 payload may only be written if decomposition was confirmed. `false`/absent fails validation. |
| `flow_units` | array | non-empty, each per 3.3 | The unit set. |
| `no_overclaim_boundary` | array of strings | non-empty, contains all mandatory tokens | Preserved boundary discipline. The v2 validator checks every mandatory token is present. |

`active_lanes`, `blocked_downstream_units`, `rollup_status` (visibility-v1 rollup fields) are **not** v2 top-level fields. Rollup in v2 is computed by `rollup_loop_state` from the per-unit fields (see 3.5) — it is a derived view, not stored state. This eliminates the "rollup field drift" AUDIT-133 found (stored rollup vs computed rollup diverging).

### 3.3 Per-unit fields (the v2 flow unit)

Each entry in `flow_units` carries exactly:

| Field | Type | Allowed value / shape | Notes |
|-------|------|------------------------|-------|
| `flow_unit_id` | string | non-empty, unique within payload | The unit identity (e.g. `shitu.story.Skeleton`). |
| `title` | string | non-empty | Human label. |
| `unit_type` | string | project-type-derived (`chapter`/`command`/`story`/`module`/...) | From `derive_flow_units`. |
| `project_type` | string | one of the 7 presets | The project type used for derivation. |
| `derivation_reason` | string | non-empty | Why this unit exists (`"dotted-id:game.chapter.03"` / `"no-decomposable-structure-found"`). FEAT-004: the fallback single-unit reason is explicit, never silent. |
| `loop_state` | object | the 9-field FX-189 shape, initialized per FEAT-004 | See 3.4. |
| `gate_state` | object | `{status, gate_id, last_result, evidence_refs}` | The canonical gate state. `status` from the v2 enum; `gate_id` is the current loop-role gate (G1-G11 mapped via `loop_gate_semantics`); `last_result` drives iterate-vs-escalate. **Unified with loop_state.last_gate_result** — see 3.4. |
| `runtime_status` | string | one of `allowed_runtime_statuses` | **FEAT-004.** `active` only when the unit is genuinely activated; `dormant` is explicit and never masquerades as active. |
| `dependencies` | array of strings | valid `flow_unit_id`s | Dependency graph (unchanged semantics). |
| `blockers` | array of strings | | Active blockers. |

Visibility-v1's `current_stage`, `current_subphase`, `gate_lane`, `gate_references`, `allowed_next_transitions`, `runtime_status_source` are **replaced** in v2 by the loop-native fields (`loop_state.active_loop_tier`, `gate_state.gate_id`, `loop_state.agent_phase`). The mapping is deterministic (see 3.6) and lives in the schema file so a reader can translate a v1 payload to a v2 view for read-only purposes if ever needed — but write is v2-only.

### 3.4 The canonical `loop_state` (FEAT-002 + FEAT-004)

The 9 FX-189 fields are retained (they are already declared in `loop-engineering-registry.json` under `agent_intrinsic_loop.loop_state_fields`):

```
active_loop, active_loop_tier, loop_count, last_loop_type,
agent_phase, iteration_within_inner, pause_points_active,
last_gate_result, fuse
```

**FEAT-002 unification:** `loop_state.last_gate_result` and `gate_state.last_result` are the SAME value (the most recent gate outcome driving iterate-vs-escalate). The writer sets both to identical values; the validator enforces equality. This eliminates the "status source drift" — there is one gate result, not two.

**FEAT-004 canonical initial values** (set by the planner when a unit is activated, see §5):

| Field | Initial value (activated unit) | Rationale |
|-------|-------------------------------|-----------|
| `active_loop` | `true` | The unit is activated. |
| `active_loop_tier` | the unit's entry tier (Middle for delivery units; Setup for pre-delivery) | Per the architecture ADR §3. |
| `loop_count` | `0` | First iteration. |
| `last_loop_type` | `null` | No prior iteration type. |
| `agent_phase` | `"plan"` | Entry phase per ADR §5.1. |
| `iteration_within_inner` | `0` | No agent cycles yet. |
| `pause_points_active` | `[]` | No active pause points until the engine (0.68.0) arms them. |
| `last_gate_result` | `null` | No gate has run yet. |
| `fuse` | `{max_rounds: <tier default>, tripped: false}` | From `loop_fuses` in the registry; `tripped: false` at activation. |

A **dormant** unit (`runtime_status: "dormant"`) keeps `active_loop: false` and `loop_count: 0` — but the v2 validator requires `runtime_status` to be explicit, so dormant is a declared state, not an accidental one. This is the FEAT-004 guard against "dormant masquerading as active": the two fields must agree (`runtime_status: "active"` ⇒ `active_loop: true`; `runtime_status: "dormant"` ⇒ `active_loop: false`), and the validator enforces the implication in both directions.

### 3.5 Allowed gate statuses (the unified enum)

The v2 `gate_state.status` enum (declared in `loop-runtime-contract.json`):

```
["pending", "in-progress", "passed", "failed", "blocked", "escalated", "withdrawn"]
```

This replaces the visibility-v1 8-value enum (`backlog, pending, not-started, in-progress, testing, passed, released, blocked`) which was classic-stage vocabulary. The v2 enum is loop-native: a gate is `pending` → `in-progress` → `{passed | failed | blocked | escalated | withdrawn}`. `passed` drives loop exit; `failed` drives iteration; `escalated` is post-fuse; `withdrawn` is the unit-withdrawn terminal. The rollup computes aggregate health from these — no stored `rollup_status`.

### 3.6 Consumer map (how the 5 consumers reference the schema)

| Consumer | How it consumes `loop-runtime-contract.json` |
|----------|----------------------------------------------|
| **Writer** (`loop_migration.apply_migration`) | Loads the schema; builds a v2 payload whose fields are exactly the schema's `required_top_level_fields` + `required_per_unit_fields`; calls the v2 validator before write. |
| **Validator** (new `checks/flow_unit_runtime_v2.py`) | Loads the schema; enforces every field, type, allowed value, boundary token, and the `last_gate_result == gate_state.last_result` invariant; routes on `schema_version` (v1 → existing `flow_unit_runtime.validate_flow_unit_runtime_payload`; v2 → new v2 validator). |
| **Reader** (`loop_engine.rollup_loop_state`) | Loads the schema; reads the v2 per-unit fields to produce the per-unit view. The current `no_global_stage: True` invariant is preserved. |
| **Health** (`loop_health.check_loop_health`) | Loads the schema; Part 1 (registry PausePoints) unchanged; Part 2/DORA read the v2 `velocity_history`/`dora` fields. |
| **Registry** (`loop-engineering-registry.json`) | Unchanged in structure; its `agent_intrinsic_loop.loop_state_fields` list is verified equal to the contract schema's per-unit loop_state field list by a contract-drift test (FEAT-002 acceptance). |

**The drift is eliminated** because there is one field list (in `loop-runtime-contract.json`) and a drift test fails if any consumer's hard-coded field set diverges from it.

### 3.7 Schema versioning (v1 → v2 without breaking installed state)

- **v1 (`schema_version: "1.0"`) is frozen.** The existing `validate_flow_unit_runtime_payload` is preserved byte-for-byte. Classic and dynamic installations keep producing v1. No installed v1 payload is invalidated.
- **v2 (`schema_version: "2.0"`) is additive.** A v2 payload is produced only by the 0.67.0 migration planner when the operator explicitly activates loop-engineering. The v2 validator is a new function (`validate_flow_unit_runtime_payload_v2`) in a new file; it does not modify v1.
- **Routing.** The validator entry point dispatches on `schema_version`: `"1.0"` → v1 validator; `"2.0"` → v2 validator; anything else → fail. Both validators must pass for their respective versions. A payload cannot mix versions.
- **Future v2.x.** Minor contract additions use `schema_version: "2.1"` with a forward-compatible rule (v2.1 validator accepts 2.0 fields + new optional ones; v2.0 validator rejects 2.1). This is the same additive discipline. A v3 (breaking) requires a new ADR.
- **Registry lockstep.** `loop-engineering-registry.json` keeps its own `schema_version: "1.0"` (registry schema, independent of runtime contract schema). A contract-drift test asserts the registry's `loop_state_fields` list matches the contract schema's loop_state field list, so the two cannot silently diverge.

---

## 4. Migration Planner Spec (FEAT-003)

### 4.1 The pure function signature

Extract from `loop_migration.apply_migration` (steps 1-4: resolve root, read plan-tracker, derive units, build payload) into a new pure function in a new module:

```
skills/software-project-governance/infra/loop_migration_plan.py
```

Signature:

```python
def build_migration_plan(
    target_root,                # str/Path host project root (RISK-040: resolved via resolve_entry)
    project_type=None,          # one of the 7 presets; None → "ai-agent-plugin" fallback
    *,
    plan_tracker_text=None,     # optional pre-loaded text (tests / dry-run reuse)
    plugin_home=None,           # optional registry override (tests)
    options=None,               # optional MigrationPlanOptions (confirm_decomposition, etc.)
) -> MigrationPlan:
    ...
```

`MigrationPlan` is an immutable dataclass (frozen):

```python
@dataclass(frozen=True)
class MigrationPlan:
    schema_version: str          # "2.0" — the contract version this plan targets
    contract_id: str             # "loop-runtime-contract/v2"
    target_root: str             # resolved host root (resolved via resolve_entry, never PLUGIN_HOME)
    project_type: str            # the project type used for derivation
    project_id: str              # derived from target_root basename
    workflow_model_prior: str    # parsed from plan-tracker (for rollback record)
    workflow_model_new: str      # "loop-engineering"
    unit_ids: tuple[str, ...]    # the ordered, deduped flow_unit_ids (load-bearing for the hash)
    unit_count: int              # len(unit_ids)
    units: tuple[UnitPlan, ...]  # per-unit plan (id, type, title, derivation_reason, entry_tier, dependencies)
    gate_schema: str             # the gate schema id ("loop-gate-schema-v1") — see 4.3
    decomposition_confirmed: bool # FEAT-004: false from build; true after confirm_decomposition
    plan_hash: str               # 64-hex SHA-256 over canonical JSON of the load-bearing fields (4.2)
```

**Purity contract (load-bearing):** `build_migration_plan` holds no module-level mutable state, caches nothing that accumulates across calls, and is deterministic: two calls with identical arguments return identical `plan_hash`. This mirrors the sacred `derive_round` purity (ADR §8.2). A threading test is mandatory (acceptance).

### 4.2 The immutable plan hash

The hash is SHA-256 over **canonical JSON** of the plan's load-bearing fields. Canonicalization (deterministic, matches the ADR-012 accounting discipline):

1. Build a dict with exactly these keys (sorted): `contract_id`, `project_id`, `project_type`, `schema_version`, `unit_count`, `unit_ids`, `workflow_model_new`, `gate_schema`. (`decomposition_confirmed`, `target_root`, `plan_hash` itself, timestamps, and `workflow_model_prior` are EXCLUDED — they are not load-bearing for the dry-run/apply identity invariant; `target_root` is excluded because it is a path that varies by environment, and the invariant is about the *derived structure*, not the path.)

   > Rationale for excluding `target_root`: the REL-059 invariant is "same target → same unit IDs/count/project_type/gate schema." Two runs against the same target produce the same path; two runs against different targets legitimately differ in structure. Including the path would make the hash environment-coupled without strengthening the structural identity guarantee. The structural fields (unit_ids, unit_count, project_type, gate_schema) ARE the identity.

2. Serialize as JSON: `ensure_ascii=False`, `sort_keys=True`, `separators=(",", ":")`, UTF-8 encoded.
3. Normalize the resulting bytes to Unicode NFC (matching `_sha_text` in `loop_runtime_claims.py`).
4. `plan_hash = hashlib.sha256(nfc_bytes).hexdigest()` — 64 lowercase hex.

This is computed **inside** `build_migration_plan` and stored on the returned `MigrationPlan`. It is immutable.

### 4.3 The gate schema binding

`MigrationPlan.gate_schema` is a string id (`"loop-gate-schema-v1"`) that names the gate schema the plan uses. It is derived from `loop-engineering-registry.json`'s `loop_gate_semantics` (the G1-G11 → loop-role mapping). The hash includes it so a change to the registry's gate semantics (e.g. re-mapping G6's enclosing_loop) produces a different plan hash — making the dry-run/apply identity guarantee cover the gate schema, not just the unit list. This is the load-bearing field that makes REL-059's "same gate schema" criterion executable.

### 4.4 Dry-run and apply share the SAME plan (the invariant)

```
DRY-RUN path:
  plan = build_migration_plan(target_root, project_type, options)
  plan is serialized to JSON (including plan_hash)
  dry-run result = {plan: plan.as_dict(), validation: validate_v2(plan_to_payload(plan))}
  no writes

APPLY path:
  plan = build_migration_plan(target_root, project_type, options)   # RE-DERIVED
  plan_hash_rederived = plan.plan_hash
  (if a hash was supplied via options.expected_plan_hash, assert it equals plan_hash_rederived; mismatch → fail-closed, no write)
  payload = plan_to_payload(plan)        # build the v2 runtime payload from the plan
  issues = validate_flow_unit_runtime_payload_v2(payload)
  if issues: fail-closed, no write (preserves FIX-195 containment)
  ... backup, commit transaction (unchanged from 0.66.1) ...
```

**The invariant (REL-059 load-bearing):** for the same `target_root` + `project_type` + registry state, `build_migration_plan` returns the same `plan_hash`. Therefore the dry-run's serialized plan and the apply's re-derived plan have identical `unit_ids`, `unit_count`, `project_type`, and `gate_schema`. A test proves this by running both paths against the same fixture and asserting the hashes match.

**What this guarantees that 0.66.1 does not:** today, dry-run and apply take different code paths and can disagree (the AUDIT-133 21/19 validator issues). With FEAT-003, disagreement is impossible — both call the same pure function. If `derive_flow_units` is non-deterministic (a bug), the hash differs and apply fails closed.

### 4.5 Where `build_migration_plan` lives and what changes in `loop_migration.py`

- **New module:** `infra/loop_migration_plan.py` — owns `build_migration_plan`, `MigrationPlan`, `MigrationPlanOptions`, `confirm_decomposition` (FEAT-004), `plan_to_payload`, and the hash function. Pure stdlib; imports `resolve_entry` (peer, RISK-040), `flow_unit_derive` (peer), and the contract schema loader (FEAT-002). Does NOT import `verify_workflow` (avoids the cycle, same discipline as `loop_engine`/`loop_health`).
- **Modified module:** `infra/loop_migration.py` — `apply_migration` and `preview_migration` are refactored to call `build_migration_plan`. The 9-step apply algorithm is preserved (backup-before-write, fail-closed cases, compensating transaction); only the plan-derivation + payload-construction steps (4-5) are replaced by `plan = build_migration_plan(...)` + `payload = plan_to_payload(plan)`. `preview_migration` no longer delegates to `verify_workflow.build_dynamic_lifecycle_migration_preview`; it calls `build_migration_plan` and serializes the plan + hash. This is the single biggest behavioral change in 0.67.0 and it is the point.
- **New validator:** `infra/checks/flow_unit_runtime_v2.py` — `validate_flow_unit_runtime_payload_v2(state, display)`. Routes from a thin dispatcher that reads `schema_version`.

---

## 5. Decomposition + Initial Gate State Spec (FEAT-004)

### 5.1 Heuristic stays advisory

`flow_unit_derive.derive_flow_units()` is **unchanged** in behavior. It remains a heuristic, advisory, fail-closed derivation that returns dormant units. FEAT-004 does not modify it. The units it returns are the *candidate* set, not the activated set.

### 5.2 The confirmation step

`build_migration_plan` produces a `MigrationPlan` with `decomposition_confirmed: false`. Before apply writes a v2 payload, the plan must pass through:

```python
def confirm_decomposition(plan, *, approved_unit_ids=None, options=None) -> MigrationPlan:
    ...
```

This function:

1. **Validates the candidate set:** no duplicate IDs, no unknown dependencies, at least one unit, every unit has a non-empty `derivation_reason`.
2. **Applies operator confirmation:** if `approved_unit_ids` is supplied (the operator/Coordinator approved a specific subset), the plan is filtered to exactly those IDs; if `None`, the full derived set is confirmed (the operator accepted the heuristic output wholesale). Either way, the result is an explicit decision, not a silent default.
3. **Returns a new frozen `MigrationPlan`** with `decomposition_confirmed: true` and a **recomputed `plan_hash`** (because the confirmed unit set may differ from the candidate set, the hash must reflect the confirmed set — the dry-run/apply invariant applies to the *confirmed* plan).

**The v2 validator requires `decomposition_confirmed: true`.** A v2 payload written from an unconfirmed plan fails validation — this is the executable guard. Apply calls `confirm_decomposition` (with the operator's approval, or `None` to accept the heuristic set) before `plan_to_payload`; if confirmation is skipped or fails, apply fails closed.

### 5.3 Canonical initial per-unit state (FEAT-004 core)

`plan_to_payload(plan)` initializes each unit per §3.4. The load-bearing FEAT-004 rules:

1. **`runtime_status` is explicit.** Every unit gets one of `active | dormant | blocked | withdrawn`. There is no implicit/default status.
2. **The `runtime_status ⇔ active_loop` implication is enforced.** `runtime_status: "active"` requires `loop_state.active_loop: true`; `runtime_status: "dormant"` requires `active_loop: false`. The validator checks both directions. A unit cannot claim `active` while `active_loop` is false — this is the executable guard against the "dormant masquerading as active" failure AUDIT-133 found.
3. **`gate_state` is initialized, not null.** Every activated unit starts with `gate_state.status: "pending"`, `gate_state.gate_id: <entry gate for the unit's tier>`, `gate_state.last_result: null`, `gate_state.evidence_refs: []`. A unit never reaches the runtime without a gate state.
4. **`last_gate_result == gate_state.last_result`.** Set to `null` at activation; the validator enforces they stay equal on every write.
5. **`derivation_reason` is non-empty.** The fallback single-unit carries `derivation_reason: "no-decomposable-structure-found"` — explicit, not hidden. The validator rejects an empty reason.
6. **Example-data-only is forbidden as `active`.** A unit whose `derivation_reason` indicates example/fixture provenance (a new reserved reason token, e.g. `"example-fixture"`) must have `runtime_status: "dormant"`. The validator enforces this: an `example-fixture` reason with `runtime_status: "active"` fails. This directly closes the AUDIT-133 "example-data-only masquerading as active" path.

### 5.4 What this prevents

AUDIT-133 found migration apply writing units that were effectively dormant or example-data while the surrounding code treated the runtime as active. FEAT-004 makes that state **unrepresentable in a valid v2 payload**: the `runtime_status ⇔ active_loop` implication, the explicit `decomposition_confirmed` flag, and the `example-fixture` reason guard together make "dormant masquerading as active" a validation failure, not a silent pass.

---

## 6. Implementation Order + File Changes

### 6.1 Dependency-confirmed order: FEAT-002 → FEAT-003 → FEAT-004

```
FEAT-002 (contract schema + v2 validator)
   │
   ├── core/loop-runtime-contract.json              (NEW — the schema, single source of truth)
   ├── infra/checks/flow_unit_runtime_v2.py         (NEW — v2 validator + dispatcher)
   ├── infra/loop_engine.py                         (MODIFIED — rollup loads schema; field list from schema)
   ├── infra/loop_health.py                         (MODIFIED — loads schema; reads v2 fields)
   └── infra/tests/test_loop_runtime_contract.py    (NEW — drift test: registry loop_state_fields == contract)
   │
   ▼
FEAT-003 (planner uses the contract)
   │
   ├── infra/loop_migration_plan.py                 (NEW — build_migration_plan, MigrationPlan, hash)
   ├── infra/loop_migration.py                      (MODIFIED — apply/preview call build_migration_plan)
   ├── infra/checks/flow_unit_runtime_v2.py         (EXTEND — validate plan_hash present + re-derivable)
   └── infra/tests/test_loop_migration_plan.py      (NEW — purity, hash determinism, dry-run/apply identity)
   │
   ▼
FEAT-004 (decomposition + initial state uses contract + planner)
   │
   ├── infra/loop_migration_plan.py                 (EXTEND — confirm_decomposition, plan_to_payload init)
   ├── infra/checks/flow_unit_runtime_v2.py         (EXTEND — decomposition_confirmed, runtime_status⇔active_loop, example-fixture guard)
   └── infra/tests/test_loop_decomposition.py       (NEW — confirmation, initial state, masquerading guards)
```

Each FEAT is a separately reviewable commit with its own DEC + Developer + Code Reviewer + QA cycle. FEAT-003 cannot start until FEAT-002 is committed (planner emits v2 fields). FEAT-004 cannot start until FEAT-003 is committed (decomposition operates on a `MigrationPlan`).

### 6.2 What is NOT touched (release-critical isolation)

FEAT-002~004 MUST NOT modify:

- `infra/release/verify_rel063_evidence.py` — the 0.66.x release-critical evidence verifier.
- `infra/checks/flow_unit_runtime.py` (the v1 validator) — frozen; the v2 validator is a new file.
- The 0.66.x compensation assets (FIX-195 transaction recovery, FIX-196 health fail-closed) — preserved; `loop_migration.apply_migration` retains its backup/commit/compensation machinery, only the plan-derivation interior is replaced.
- `core/loop-runtime-claim-allowlist.json` / `core/loop-runtime-claim-authority.json` — the claim scanner policy (ADR-011/012) is untouched. FEAT-002~004 do not change claim classification.
- `core/loop-engineering-registry.json` — structurally unchanged; only a drift test reads it.

### 6.3 Estimated complexity

**Medium, mostly additive.** This is NOT a large refactor of existing logic:

- FEAT-002: one new JSON schema file + one new validator file (~250-350 lines, mostly field checks mirroring the v1 validator's style) + small modifications to `loop_engine.rollup_loop_state` and `loop_health` to load the schema. The v1 validator is untouched. **Additive.**
- FEAT-003: one new pure module (`loop_migration_plan.py`, ~200-300 lines) extracting logic that already exists inline in `apply_migration`. The apply algorithm's safety scaffolding (backup, transaction, compensation) is preserved. The main risk is behavioral: `preview_migration` changes from delegating to `verify_workflow` to calling `build_migration_plan`. **Mostly extraction + one behavioral change (preview path).**
- FEAT-004: extends the planner + validator with confirmation and initial-state rules (~150-250 lines across the two files). **Additive rules.**

Total: ~3 new files, ~3 modified files, ~600-1100 lines net, dominated by new tests. The hardest part is not volume but **invariant proof**: the purity/hash-determinism tests and the dry-run/apply identity test must be airtight.

---

## 7. Release Gates (REL-059 Acceptance)

### 7.1 REL-059 acceptance criteria (from plan-tracker row)

> preview/apply plan hash identical, apply 前后 validator PASS, dual unit can hold different gate/phase; 未接通执行引擎前仍不得关闭 RISK-037.

Translated to executable tests:

### 7.2 Tests that prove FEAT-002~004 meet REL-059

**FEAT-002 (contract):**

- `test_v2_validator_accepts_well_formed_payload` — a v2 payload with all §3 fields passes `validate_flow_unit_runtime_payload_v2`.
- `test_v1_validator_unchanged` — the existing `test_flow_unit_runtime.py` v1 cases still pass byte-for-byte; v1 payloads still route to v1.
- `test_v2_rejects_loop_engineering_on_v1_validator` — a v2 payload presented to the v1 validator fails (the v1 validator's `workflow_model` check still rejects `loop-engineering`). This proves the v1 containment is preserved.
- `test_contract_drift_registry_loop_state_fields` — `loop-engineering-registry.json`'s `agent_intrinsic_loop.loop_state_fields` equals the contract schema's per-unit loop_state field list. Fails on drift.
- `test_consumer_field_sets_match_contract` — `loop_engine.rollup_loop_state` and `loop_health` read exactly the fields the contract declares (a static check or a fixture-driven check).
- `test_last_gate_result_equals_gate_state_last_result` — the unification invariant.

**FEAT-003 (planner):**

- `test_build_migration_plan_is_pure` — two calls with identical args return identical `plan_hash`; a threading test (N threads) proves no accumulation/race (mirrors `test_loop_engine_round.py`'s parallel-safety proof).
- `test_plan_hash_deterministic` — same target + project_type + registry → same hash across runs.
- `test_plan_hash_excludes_path_and_timestamp` — changing only the target path or timestamp does not change the hash for the same derived structure (within the same-project identity).
- `test_plan_hash_changes_on_unit_set_change` — adding/removing a unit changes the hash.
- `test_plan_hash_includes_gate_schema` — changing the registry's `loop_gate_semantics` changes the hash.
- `test_dry_run_apply_plan_hash_identical` — **REL-059 load-bearing.** Run `preview_migration` and `apply_migration` (against a fixture); assert both produce the same `plan_hash` and the same `unit_ids`/`unit_count`/`project_type`/`gate_schema`.
- `test_apply_fails_closed_on_hash_mismatch` — if `options.expected_plan_hash` is supplied and differs from the re-derived hash, apply aborts before any write (preserves FIX-195 containment).
- `test_apply_validates_v2_before_write` — the v2 validator runs before backup/write; an invalid plan fails closed (FIX-195 containment preserved).

**FEAT-004 (decomposition + initial state):**

- `test_confirm_decomposition_filters_to_approved_set` — `confirm_decomposition(plan, approved_unit_ids=[...])` returns a plan with exactly those IDs and a recomputed hash.
- `test_v2_requires_decomposition_confirmed` — a v2 payload with `decomposition_confirmed: false` fails validation.
- `test_runtime_status_active_implies_active_loop_true` — `runtime_status: "active"` + `active_loop: false` fails.
- `test_runtime_status_dormant_implies_active_loop_false` — `runtime_status: "dormant"` + `active_loop: true` fails.
- `test_example_fixture_reason_cannot_be_active` — `derivation_reason: "example-fixture"` + `runtime_status: "active"` fails (the AUDIT-133 guard).
- `test_initial_gate_state_is_pending` — every activated unit starts `gate_state.status: "pending"`, `gate_state.gate_id: <entry gate>`, `last_result: null`.
- `test_dual_unit_holds_different_gate_and_phase` — **REL-059 load-bearing.** A two-unit payload where unit A is `gate_state.gate_id: G6, agent_phase: act` and unit B is `gate_state.gate_id: G5, agent_phase: plan` passes validation and rollup reports both distinctly (no global stage collapse). This proves the per-unit independence RISK-037 criterion 2 demands.

**Integration (the dual-unit scenario end-to-end):**

- `test_end_to_end_dual_unit_apply` — a fixture target with two decomposable units: dry-run → apply → v2 validator PASS → rollup shows two distinct units with different gate/phase → rollback restores exactly. This is the REL-059 "dual unit can hold different gate/phase" proof.

### 7.3 What does NOT close in 0.67.0

- **RISK-037 remains open.** The criterion "no global stage" is met by `rollup_loop_state` (already MET-NARROW), but the runtime execution engine (criteria around persisted back-edge, per-unit loop_count driven by real events, fuse firing in production) is 0.68.0 (FEAT-005~007). 0.67.0 ships the contract and planner, not the engine.
- **RISK-042 remains open.** External effectiveness is not proven until 0.69.0 (VAL-008/009).
- **The loop runtime claim scanner (ADR-011/012) policy** — FEAT-002~004 do not change claim classification. The 0.67.0 ADR (this document) and any new v2 surfaces will need claim-policy attention (likely a new planned-target marker for the v2 contract), but that is a separate FIX/claim task, not FEAT-002~004 scope. This ADR explicitly does not authorize any claim policy change.
- **Production gate back-edge/fuse execution** — 0.68.0 (FEAT-006).
- **verify_workflow Phase 5 extraction** — 0.70.0.

---

## 8. Risk + Regression Analysis

### 8.1 Existing tests that might break (and how to keep them green)

| Test file | Risk | Mitigation |
|-----------|------|------------|
| `test_loop_migration.py` | **HIGH.** `preview_migration` changes path (no longer delegates to `verify_workflow.build_dynamic_lifecycle_migration_preview`); `apply_migration`'s interior changes to call `build_migration_plan`. The 0.66.1 containment tests (`test_current_loop_payload_fails_before_any_host_write`, compensation/recovery tests) must still pass. | The apply algorithm's safety scaffolding (backup, transaction, compensation, fail-closed cases) is preserved unchanged. Only steps 4-5 (derive + build payload) become `plan = build_migration_plan(...)` + `payload = plan_to_payload(plan)`. The containment tests assert behavior (no write on invalid plan, compensation on failure), not the interior code path, so they remain valid. `test_current_loop_payload_fails_before_any_host_write` must be updated: in 0.67.0 the plan produces a v2 payload that the v2 validator ACCEPTS (the whole point), so this test's expectation flips — it becomes `test_v2_payload_passes_v2_validator_and_writes`. The 0.66.1 fail-closed guarantee is re-expressed as: a v2 payload presented to the v1 validator still fails (test_v2_rejects_loop_engineering_on_v1_validator). |
| `test_loop_engine_round.py` | LOW. `derive_round`/`fuse_decision` purity unchanged. | No change needed. |
| `test_loop_health.py` | MEDIUM. `loop_health` loads the contract schema; if the schema file is missing/corrupt it must still fail closed (FIX-196). | Add a fail-closed test: missing `loop-runtime-contract.json` → `loop_health` returns blocking authority finding (mirrors FIX-196). The existing FIX-196 tests for registry-missing must still pass. |
| `test_loop_rollup.py` | MEDIUM. `rollup_loop_state` reads v2 fields; the `no_global_stage: True` invariant must hold. | The rollup's `no_global_stage` invariant is preserved (it is a structural property of the per-unit view, independent of field names). Update the rollup to read the v2 field names; the `no_global_stage` test remains valid. |
| `test_loop_runtime_claims.py` / `test_loop_runtime_claim_attestation.py` | LOW-MEDIUM. FEAT-002~004 add new files and new required-path entries. The claim scanner's `REQUIRED_PATHS` set (in `loop_runtime_claims.py`) lists required surfaces; adding `core/loop-runtime-contract.json`, `infra/loop_migration_plan.py`, `infra/checks/flow_unit_runtime_v2.py` to the repo means the scanner sees new candidates. Any affirmative claim in the new files must be classified. | This ADR and the new files must use scoped-negative / planned-target wording (not bare affirmative claims about runtime activation). The new v2 surfaces describe a *contract and planner*, not *activation* — wording must say "contract" / "planner" / "planned", and any forward-looking statement about the execution engine must use the `<!-- loop-runtime-target:... -->` marker (ADR-011 discipline). This is a documentation/wording discipline at write time, not a code risk. The claim policy itself is NOT modified by FEAT-002~004. |
| `test_loop_registry.py` | LOW. Registry structurally unchanged. | No change; the drift test (`test_contract_drift_registry_loop_state_fields`) is additive. |
| `test_verify_workflow.py` (loop-related) | MEDIUM. The thin `cmd_loop_engineering_migration` / `cmd_loop_rollup` entries delegate to the modules; if dispatch changes, tests need updating. | The thin-entry discipline is preserved. If `cmd_loop_engineering_migration` gains a `--plan-hash` flag (to pass `expected_plan_hash`), that is additive argparse. |

### 8.2 Preserving the 0.66.x fail-closed containment (FIX-195/196)

The 0.66.x containment invariants that MUST remain true after 0.67.0:

1. **Apply validates before write.** `build_migration_plan` → `plan_to_payload` → `validate_flow_unit_runtime_payload_v2` → only then backup + write. A validation failure aborts before any write. **Preserved** (FEAT-003 step ordering).
2. **Backup before live commit.** The 9-step algorithm's step 5 (backup) precedes steps 6-8 (commit). **Preserved** (unchanged).
3. **Compensating transaction on failure.** `_commit_runtime_and_evidence` and its recovery journal are unchanged. **Preserved.**
4. **Health fails closed on missing/corrupt authority.** `loop_health` returns blocking when the registry OR the contract schema is missing/corrupt. **Extended** (FEAT-002 adds the contract schema as an authority source; FIX-196 discipline extended to it).
5. **RISK-040 dual-root discipline.** `build_migration_plan` resolves HOST_PROJECT_ROOT via `resolve_entry`, never PLUGIN_HOME. **Preserved** (FEAT-003 inherits the peer-import discipline).

A dedicated regression test (`test_066x_containment_preserved`) runs the FIX-195/196 test scenarios against the 0.67.0 code and asserts the same fail-closed behavior.

### 8.3 Does FEAT-002~004 touch release-critical assets?

**No.** FEAT-002~004 do not modify:

- `infra/release/verify_rel063_evidence.py` (0.66.x release-critical evidence).
- The 0.66.1 release documents (`docs/release/*-0.66.1.md`), tags, or manifest transitions.
- The claim scanner policy/authority (`core/loop-runtime-claim-*.json`).

The release-critical path for 0.67.0 is REL-059, which is a new MINOR release with its own release docs, not a modification of 0.66.x assets. FEAT-002~004 are additive modules + schema; they do not alter the 0.66.x evidence chain.

### 8.4 The main residual risk

The single highest-risk change is **`preview_migration` switching from `verify_workflow.build_dynamic_lifecycle_migration_preview` to `build_migration_plan`.** If any caller (CLI, test, external script) depended on the old preview's shape, it breaks. Mitigation: the new preview's result dict includes a compatibility envelope (`preview["plan"]` = the new plan; legacy fields like `validation_issues` preserved where sensible), and a deprecation note. The dry-run/apply identity invariant is the payoff that justifies this change.

---

## 9. Authorization Boundary

This ADR is **design only.** It:

- Does NOT implement code. Each of FEAT-002, FEAT-003, FEAT-004 requires:
  1. A separate DEC (task dispatch) from the Coordinator.
  2. A Developer (implementation per this spec).
  3. An independent Code Reviewer (R0, with rounds per Check 30 review-chain fuse).
  4. An independent QA.
  5. For the aggregate, a Release Reviewer for REL-059.
- Does NOT authorize a release. REL-059 requires its own release docs, version projection, and Release Review per the release workflow.
- Does NOT close RISK-037 or RISK-042. Both remain open until 0.68.0 (execution engine) and 0.69.0 (external validation) are complete.
- Does NOT activate the runtime execution engine. No persisted back-edge, no fuse firing, no PARO transition is made executable by FEAT-002~004. Those are FEAT-005~007 (0.68.0).
- Does NOT change the loop runtime claim scanner policy (ADR-011/012). New v2 surfaces added by FEAT-002~004 must comply with the existing claim contract at write time (scoped-negative / planned-target wording); any claim-policy change is a separate FIX task.
- Does NOT modify the 0.66.x release-critical assets or the v1 visibility contract. Both are frozen.

**Design Review scope:** the Design Reviewer reviews this ADR for (a) contract schema completeness and internal consistency, (b) planner purity and hash correctness, (c) decomposition/initial-state guards closing the AUDIT-133 masquerading paths, (d) regression risk to 0.66.x containment, (e) whether the implementation order is sound. On APPROVAL_WITH_NOTES with `unresolved_blockers=0`, the Coordinator may dispatch FEAT-002 (then FEAT-003, then FEAT-004) each with its own execution packet and review chain.

**Authority:** DEC-104 (binding roadmap), AUDIT-133 / EVD-707 (the findings this addresses), `docs/requirements/loop-engineering-architecture-0.65.0-proposed.md` (the R1-APPROVED design ADR whose activation this contracts), ADR-011/012 (the claim-correction boundary this must respect).

---

## Appendix A: Field drift eliminated by FEAT-002 (quick reference)

| Field | visibility-v1 (today) | loop-engineering writer (today) | loop-engineering reader (today) | v2 contract (0.67.0) |
|-------|----------------------|----------------------------------|----------------------------------|----------------------|
| `workflow_model` | `classic-phase-gate` / `dynamic-flow-gate` | `loop-engineering` | (not read) | `loop-engineering` (only v2 value) |
| `runtime_scope` | `runtime-visibility-only` | (absent) | (not read) | `loop-engineering-runtime` |
| `schema_version` | `1.0` | `1.0` (rejected) | (not read) | `2.0` |
| per-unit `current_stage` | required (classic vocab) | (absent) | (not read) | replaced by `loop_state.active_loop_tier` |
| per-unit `gate_lane` | required | (absent) | (not read) | replaced by `gate_state.gate_id` |
| per-unit `gate_state.status` | 8-value classic enum | (absent) | (not read) | 7-value loop-native enum |
| per-unit `runtime_status_source` | required | (absent) | (not read) | replaced by top-level `contract_source` + per-unit `runtime_status` |
| per-unit `loop_state` | `{loop_count}` only checked | 9-field FX-189 shape | reads 9 fields | 9-field FX-189 shape (unified with registry) |
| top-level `rollup_status` | required | (absent) | (not read) | removed — rollup is computed by `rollup_loop_state`, not stored |
| `last_gate_result` vs `gate_state.last_result` | (n/a) | (only `loop_state.last_gate_result`) | reads `last_gate_result` | **unified** — same value, validator-enforced |

The v2 column is the single contract. The drift test fails if any consumer diverges.

## Appendix B: The dry-run/apply identity invariant (REL-059 proof sketch)

```
target = fixture("two-unit-cli")         # plan-tracker with 2 decomposable commands
project_type = "cli-tool"

# DRY-RUN
dry_plan = build_migration_plan(target, project_type)
dry_hash = dry_plan.plan_hash            # e.g. "a1b2..."

# APPLY (later, possibly different process)
apply_plan = build_migration_plan(target, project_type)
assert apply_plan.plan_hash == dry_hash  # REL-059 invariant: IDENTICAL
assert apply_plan.unit_ids == dry_plan.unit_ids        # ["mycli.command.init", "mycli.command.build"]
assert apply_plan.unit_count == dry_plan.unit_count    # 2
assert apply_plan.project_type == dry_plan.project_type # "cli-tool"
assert apply_plan.gate_schema == dry_plan.gate_schema   # "loop-gate-schema-v1"

# The v2 payload written by apply validates
payload = plan_to_payload(confirm_decomposition(apply_plan))
assert validate_flow_unit_runtime_payload_v2(payload) == []

# The two units hold different gate/phase (no global stage collapse)
rollup = rollup_loop_state(target)
assert len(rollup["units"]) == 2
assert rollup["units"][0]["agent_phase"] != rollup["units"][1]["agent_phase"]  # distinct
assert rollup["no_global_stage"] is True
```

This is the executable form of REL-059's three criteria: hash identical, validator PASS, dual-unit distinct gate/phase.
