# Loop-Engineering Implementation Breakdown — 0.65.0

> **Version**: 0.65.0 (independent MINOR, per DEC-099)
> **Status**: PLAN (Architect output). No product code is written by this step.
> **Source ADR**: `docs/requirements/loop-engineering-architecture-0.65.0-proposed.md` (R0.1, APPROVED_WITH_NOTES × 2 rounds, all findings resolved)
> **Triggering decisions**: DEC-097 (loop-first refactor mandate, 3 parts) + DEC-098 (RISK-037 criterion-4 re-scope) + DEC-099 (0.65.0 independent MINOR承载)
> **Risk addressed**: advances RISK-037 (1.0.0 hard blocker, due 2026-07-30); does NOT close it. RISK-041 to be registered.
> **Scope discipline**: this document decomposes a FINALIZED ADR into buildable slices. It does not redesign the ADR. Where the ADR left a question open, this plan makes a recommendation with rationale (marked **[ARCHITECT-DEC]**).

---

## 0. No-Overclaim Boundary (read first)

**This is a PLAN, not implementation. No code is written by producing this document.** No file under `skills/software-project-governance/infra/` or `skills/software-project-governance/core/` is modified here. No slice is marked complete. No RISK is closed. No version is released. The slices below are contracts a Developer can build against and a Code Reviewer can review against — nothing more.

The implementation will be authorized by a separate decision (DEC-086-style: either main-agent direct-write + post-hoc Explore review, the path DEC-085/DEC-086 validated for 0.58.0/0.59.0 under the current harness, or standard Developer+Reviewer split if the harness has gained a write-capable sub-agent). That authorization is out of scope for this plan.

---

## 1. Module Dependency Graph

### 1.1 New modules

All new logic lives in **new** files. None of it goes into `verify_workflow.py` (21,651 lines, TD-001 / RISK-039). The only additions to `verify_workflow.py` are ≤20-line `cmd_*` thin-entry delegators plus their argparse/dispatch registration lines (following the Phase-1 split discipline; see §4 for the honest precedent note — the Phase-1 pattern moved `cmd_*` OUT of verify_workflow.py, so leaving thin delegators IN is a new variant, not a replay).

| Module (path) | Role | New / extends |
|---------------|------|---------------|
| `core/loop-engineering-registry.json` | Declarative loop/gate/pause-point/fuse data: the `AgentIntrinsicLoop`, `PausePoint`, `LoopFuse` declarations + the `loop_gate_semantics` extension to each gate + the new `release-to-design-replan` back-edge | **New data file** (see 1.3 for the extend-vs-separate recommendation) |
| `infra/loop_engine.py` | Loop state machine: read/write `flow-unit-runtime.json`, activate `loop_state`, derive round statelessly (§8.2 sacred property), iterate-vs-escalate decision, generalized fuse from M7.4 §4.6 | **New module** |
| `infra/flow_unit_derive.py` | Target-derived flow-unit generation — the VAL-006 gap (ADR §7.4). Derives units per project-type from plan-tracker; fallback single-unit | **New module** |
| `infra/loop_migration.py` | The unblocked `--apply` / `--rollback` (ADR §7.2/§7.3). Read-then-write + SHA-256 backup + total rollback. Reuses `resolve_entry.py` + `flow_unit_derive.py` | **New module** |
| `infra/loop_health.py` | The Check: pause-point velocity-justification (Part 1 BLOCKING) + loop-latency/DORA-bridge advisory (Part 2 ADVISORY) (ADR §9.5, §3.6) | **New module** |
| `infra/checks/__init__.py` | Already exists from Phase-1 split — no change needed (loop modules sit directly under `infra/`, not under `infra/checks/`, see 1.4) | unchanged |
| Thin-entry delegators in `verify_workflow.py` | ≤20 lines each, argparse glue + delegation only. Three new `cmd_*` functions (1.5) | **Edits (additive, ≤20 lines each)** |

### 1.2 Dependency graph (build order)

```
                      ┌──────────────────────────────────┐
                      │ core/loop-engineering-registry.json │   ← data only, no code deps
                      │  (loop_gate_semantics, PausePoint,  │
                      │   LoopFuse, back-edge declarations) │
                      └─────────────────┬────────────────┘
                                        │ (read by)
                                        ▼
  ┌──────────────────────┐     ┌────────────────────────┐
  │ infra/resolve_entry.py│◄────│ infra/loop_engine.py    │  core state machine
  │  (0.64.0, reused;     │     │  • loop_state activation│  reads registry JSON,
  │  MUST NOT import vw)  │     │  • stateless round      │  reads/writes
  └──────────┬───────────┘     │    derivation (§8.2)    │  flow-unit-runtime.json
             │                  │  • fuse iterate/escalate│
             │                  └───────────┬─────────────┘
             │                              │
             │                  ┌───────────▼─────────────┐
             │                  │ infra/flow_unit_derive.py│  VAL-006 derivation
             │                  │  reads plan-tracker,     │  reads project-type
             │                  │  registry presets        │  presets from registry
             │                  └───────────┬─────────────┘
             │                              │
             │                  ┌───────────▼─────────────┐
             └──────────────────►│ infra/loop_migration.py │  --apply/--rollback
                                 │  uses resolve_entry +    │  SHA-256 backup,
                                 │  loop_engine + derive    │  writes runtime.json +
                                 └───────────┬─────────────┘  evidence rows
                                             │
                                 ┌───────────▼─────────────┐
                                 │ infra/loop_health.py     │  Check (velocity + latency)
                                 │  reads runtime.json +    │  reads registry PausePoint
                                 │  registry PausePoints    │  declarations
                                 └───────────┬─────────────┘
                                             │ (delegated to by)
                                             ▼
                       ┌──────────────────────────────────────────┐
                       │ verify_workflow.py  (≤20-line cmd_* x3)   │
                       │   cmd_loop_engineering_migration          │
                       │   cmd_check_loop_health                   │
                       │   (cmd_dynamic_lifecycle_migration stays; │
                       │    its --apply branch delegates to         │
                       │    loop_migration — see 1.5)              │
                       └──────────────────────────────────────────┘
```

**Build order (topological):**

1. `core/loop-engineering-registry.json` — data, no code deps. Can be authored + validated independently.
2. `infra/loop_engine.py` — depends only on the registry JSON + `flow-unit-runtime.json` path constant (already in verify_workflow.py line 1805: `FLOW_UNIT_RUNTIME_STATE_REL`). Reaches verify_workflow shared helpers via the deferred `_vw()` accessor (proven in `checks/manifest.py`).
3. `infra/flow_unit_derive.py` — depends on the registry presets (`project_type_gate_presets`) + plan-tracker parsing. Pure function, testable in isolation.
4. `infra/loop_migration.py` — depends on `resolve_entry.py` (0.64.0, MUST NOT import verify_workflow per its module docstring — so loop_migration calls resolve_entry directly), `loop_engine` (for state write), `flow_unit_derive` (for §7.4 derivation).
5. `infra/loop_health.py` — depends on the registry `PausePoint` declarations + the `flow-unit-runtime.json` written by loop_engine/loop_migration.
6. Thin-entry delegators in `verify_workflow.py` — last; they only wire argparse → dispatch → delegate. The ≤20-line thin-entry discipline is enforced by Code Review in 0.65.0 (ArchGuard has no per-`cmd_*` rule yet — see §4.2 for the honest posture and the 0.66.0+ mechanical-enforcement follow-on).

**Critical: no new module imports verify_workflow at module top-level.** All shared-helper access uses the deferred `_vw()` pattern from `infra/checks/manifest.py` (lines 23-43, the comment block + `_VW_CACHE` + the `_vw()` function), which the Phase-1 split proved avoids the import cycle. `resolve_entry.py` is the exception that MUST NOT import verify_workflow at all (its module docstring line 27 mandates this; loop_migration calls it as a peer, not through verify_workflow).

### 1.3 [ARCHITECT-DEC] Separate `core/loop-engineering-registry.json`, NOT extend `lifecycle-registry.json`

The ADR §12 Q7 left this open. **Recommendation: create a separate `core/loop-engineering-registry.json`.** Rationale:

1. **God-File avoidance at the data layer.** `lifecycle-registry.json` is already 2,441 lines. The ADR §6.2/§6.3/§9.5 adds 3 new declaration objects (`AgentIntrinsicLoop`, `PausePoint`, `LoopFuse`), a `loop_gate_semantics` block per gate (11 gates), the new back-edge, and the per-tier fuse table. Adding all of this would push lifecycle-registry.json past ~2,700 lines — worsening the data-layer equivalent of the God Module problem RISK-039 addresses at the code layer.
2. **Single-source-of-truth is preserved by reference, not by co-location.** The new registry declares `lifecycle-registry.json` as its upstream (a `$references` field pointing at the gates/presets it annotates). `source_of_truth: true` on lifecycle-registry.json means "this is the authoritative lifecycle vocabulary" — it does not mean "every lifecycle-adjacent declaration must live in this one file." The 0.54.0 `gate_execution_registry` already lives inside lifecycle-registry.json because it IS the gate engine; loop-engineering is a separate concern (loop semantics over gates).
3. **Cleaner split-symmetry.** Code logic splits into `infra/loop_*.py` modules (ADR §9.2). Data splitting into `core/loop-engineering-registry.json` mirrors that structure: each runtime module has a clear data home.
4. **Reversibility.** If activation is rolled back (ADR §7.3), the classic state is restored and the new registry file is simply ignored (it is read only when `workflow_model == "loop-engineering"`). Co-locating in lifecycle-registry.json would leave dormant blocks inside the always-read file.

**The new registry's contract:** it is read by `loop_engine.py` and `loop_health.py`. It MUST declare a `schema_version` and a `requires_lifecycle_registry_min_version` field (so a registry/loader can fail-closed if lifecycle-registry.json is older than the gates the loop semantics annotate). The Phase-1 manifest discipline (register the new file in `core/manifest.json` `product.entries` so `check-manifest-consistency` covers it) applies — see slice FX-188.

### 1.4 Why loop modules sit under `infra/`, not `infra/checks/`

The Phase-1 split created `infra/checks/` for extracted **check domains** (manifest, capability_registry). Loop-engineering adds three kinds of module: a state machine (`loop_engine.py`), a migration tool (`loop_migration.py`), a derivation tool (`flow_unit_derive.py`), and only one Check (`loop_health.py`). Putting the non-check modules under `infra/checks/` would mislabel them. They sit as peers of `resolve_entry.py`, `archive.py`, `cleanup.py` under `infra/`. Only `loop_health.py` is a Check in the 28-check sense, and it too sits under `infra/` (mirroring how `archive.py` backs an archive check without living under `checks/`). The `checks/` subpackage stays reserved for future extractions FROM verify_workflow.py per DEC-083; loop modules are net-new, not extractions.

### 1.5 The three thin-entry delegators (detailed in §4)

| CLI command | Thin entry in verify_workflow.py | Delegates to |
|-------------|----------------------------------|--------------|
| `loop-engineering-migration` (`--apply` / `--rollback` / `--dry-run`) | `cmd_loop_engineering_migration` (new, ≤20 lines) | `loop_migration.apply_migration()` / `.rollback_migration()` / `.preview_migration()` |
| `check-loop-health` | `cmd_check_loop_health` (new, ≤20 lines) | `loop_health.check_loop_health()` |
| `dynamic-lifecycle-migration` (existing) | `cmd_dynamic_lifecycle_migration` (existing, line 20352) | The existing dry-run preview stays. The command has TWO blocking guards (guard 1 at 20358-20360 requires `--dry-run`, guard 2 at 20361-20363 blocks `--apply`). To make `--apply` reach `loop_migration.apply_migration()`, BOTH guards must be restructured (or the control flow inverted so `--apply` is checked before the dry-run requirement) — replacing only guard 2 leaves the path broken. This is a control-flow restructure, NOT a net-neutral swap; see §4.1 for the full detail. The NEW `loop-engineering-migration` command is unaffected and its apply path is reachable directly. |

The third item is the only edit to an existing `cmd_*` body. It is NOT a net-neutral single-swap: the command has two blocking guards and BOTH must be restructured (or the control flow inverted) so the `--apply` branch reaches the delegation instead of hitting the dry-run-mandate guard first (see §4.1). The argparse/dispatch registrations for `loop-engineering-migration` and `check-loop-health` are added alongside the existing `dynamic-lifecycle-migration` (line 21402) and `check-architecture-health` (line 21462) subparser blocks, and in the dispatch dict (line 21621+).

---

## 2. Implementation Slices (ordered, each independently shippable)

Slices follow the existing **FX-** convention. Highest FX- in plan-tracker is **FX-187**; this plan starts at **FX-188**. Each slice is a vertical: implement, test, review independently. Complexity is honest (the 0.61.0 FIX-155/156 tasks were abandoned because complexity was underestimated — EVD-632; this plan over-estimates rather than under-estimates).

### FX-188 — Loop-engineering registry + loader
**Title:** Author `core/loop-engineering-registry.json` and a read-only loader in `loop_engine.py`.
**Delivers:** A parseable, validated declaration of `AgentIntrinsicLoop`, `PausePoint` (with mandatory `velocity_cost_justification`), `LoopFuse` (per-tier `max_rounds`: setup=2, inner=5, middle=3, outer=2 per ADR §8.1), the `loop_gate_semantics` block annotating G1-G11 (ADR §6.1/§4 mapping), and the new `release-to-design-replan` back-edge (ADR §6.4, three conjunctive conditions, `auto_fire: false`). No runtime activation yet — this slice only proves the data parses and the loader is fail-closed.
**Modules touched:** `core/loop-engineering-registry.json` (new), `infra/loop_engine.py` (new — loader functions only: `load_loop_registry()`, `get_loop_gate_semantics(gate_id)`, `get_pause_point(pp_id)`, `get_fuse(tier)`), `core/manifest.json` (register new file in `product.entries`), `core/technical-debt-ledger.md` (no new TD; note the new module).
**Dependencies:** none (first slice).
**Test strategy:**
- New fixture: `infra/tests/test_loop_registry.py`. FAIL-on-buggy assertions: (a) every G1-G11 gate in `gate_execution_registry` (lifecycle-registry.json) has a matching `loop_gate_semantics` entry — a missing entry FAILS (this is ADR §10 criterion 4 "every classic gate resolves to a declared loop role," made into a test); (b) every `PausePoint` has a non-empty `velocity_cost_justification` (Part 1 of §9.5, made into a test at the data layer); (c) the `release-to-design-replan` back-edge declares all three conjuncts and `auto_fire: false`; (d) loader fail-closed: corrupt JSON → diagnostic, not crash.
- Regression: `check-manifest-consistency --fail-on-issues` stays green (new file registered). `verify` Check 11 stays PASS.
- Existing suites stay green: full `pytest infra/tests/` (baseline from 0.59.0+ split).
**Complexity:** **M** — the data is large (11 gate annotations + 5 pause points + 4 fuse tiers + 1 back-edge) but mechanically simple. The risk is getting the §4 mapping table transcribed exactly; the test (a) above catches transcription errors.
**Scope:** **0.65.0 IN** (foundation — everything else reads this).

### FX-189 — loop_engine core: loop_state activation + stateless round derivation (sacred)
**Title:** Implement the loop state machine in `loop_engine.py`: activate `loop_state` on a flow unit, derive round statelessly from evidence-log, decide iterate-vs-escalate.
**Delivers:** The generalized M7.4 §4.6 fuse at loop tier. Given a `(flow_unit_id, tier)`, the engine derives `current_round = max({n | evidence-log has LOOP-{U}-{tier}-R{n}})` (ADR §8.2 — the sacred parallel-safe property), reads the tier's `max_rounds` from the registry, and returns `{iterate, escalate}` + the AskUserQuestion escalation payload (ADR §8.3, the 4 options verbatim from M7.4 §4.6). Writes activated `loop_state` (the 5 new fields from ADR §6.2: `active_loop_tier`, `agent_phase`, `iteration_within_inner`, `pause_points_active`, `last_gate_result`, `fuse`) to `flow-unit-runtime.json` via `FLOW_UNIT_RUNTIME_STATE_REL` (verify_workflow.py:1805).
**Modules touched:** `infra/loop_engine.py` (adds `activate_loop_state()`, `derive_round(unit, tier, evidence_log)`, `fuse_decision(unit, tier)`, `escalation_payload(unit, tier, round, last_result)`). No verify_workflow.py logic change (the `FLOW_UNIT_RUNTIME_STATE_REL` constant is imported by reference, not moved — mirrors D1 from the Phase-1 split).
**Dependencies:** FX-188 (reads the registry).
**Test strategy:**
- **Sacred-property test (the load-bearing one):** `infra/tests/test_loop_engine_round.py`. Construct an evidence-log fixture with `LOOP-game.chapter.03-inner-R1`, `-R2`. Assert `derive_round` returns 2. Add `-R3` → returns 3. This proves statelessness. **Parallel-safety proof:** spawn the derivation twice against the same fixture (two calls, no shared state) and assert both return the same round — this is the direct test of ADR §8.2's "parallel-safe by construction" claim. FAIL-on-buggy: if any implementation uses an in-memory counter, the two calls would diverge after a simulated "increment" — the test catches it.
- FAIL-on-buggy: `max_rounds` exceeded → `fuse_decision` returns `escalate`, never `iterate`. Round exactly == max → still iterate (boundary). Round == max+1 → escalate.
- FAIL-on-buggy: escalation payload has exactly 4 options (human arbitrate / split unit / accept degraded / withdraw) — matches M7.4 §4.6 C3/C4 verbatim. No "reluctant APPROVED at round N+1" path (C5).
- Regression: existing `test_verify_workflow.py` FlowUnitRuntimeTests (15/15 from 0.52.0) stay green — this slice only ADDS activation, it does not change the dormant-schema behavior.
**Complexity:** **M** — the stateless derivation is small but the sacred-property test must be airtight. The escalation state machine is a direct port of M7.4 §4.6 (lines 493-536) generalized over tier.
**Scope:** **0.65.0 IN** (the fuse is non-optional per ADR §8; nothing else works without it).

### FX-190 — flow_unit_derive: target-derived flow-unit generation (VAL-006 gap)
**Title:** Implement `infra/flow_unit_derive.py` — derive flow units from a target project's plan-tracker per project type (ADR §7.4).
**Delivers:** Closes the VAL-006 generalization gap at the implementation level: flow units no longer come only from the `python_game` example. For each project type: game→chapters/levels, web-app/mobile-app→stories/screens/modules, library→api-surface/modules, cli-tool→commands, ai-agent-plugin→adapters/skills, internal-script→single unit. Fallback: `{project_id}.whole` with `derivation_reason: "no-decomposable-structure-found"` (ADR §7.4).
**Modules touched:** `infra/flow_unit_derive.py` (new — `derive_flow_units(target_root, project_type, plan_tracker)`, per-type derivation functions, fallback). Reads `project_type_gate_presets` from lifecycle-registry.json (lines 1007-1746) for allowed unit types.
**Dependencies:** FX-188 (for any loop-semantics annotations it attaches to derived units — optional, can default to loop_state dormant).
**Test strategy:**
- **VAL-006 generalization test (the load-bearing one):** `infra/tests/test_flow_unit_derive.py`. Fixture: a synthetic **non-game** target (e.g. a `cli-tool` plan-tracker with 3 commands). Assert derivation produces 3 flow units of `unit_type: command`. FAIL-on-buggy: if derivation falls back to single-unit when the target IS decomposable, the test FAILS. This is the direct test of ADR §7.4 against a non-game target — the exact gap VAL-006 found.
- FAIL-on-buggy: empty/undecomposable target → exactly ONE unit `{project_id}.whole` with the recorded `derivation_reason`.
- FAIL-on-buggy: game target still derives chapters (regression — the python_game path must not break).
- Per-type fixtures: one minimal plan-tracker per project type (game/web-app/library/cli-tool at minimum; the other 3 can share the fallback fixture).
- Regression: existing migration preview tests (`build_dynamic_lifecycle_migration_preview`) stay green — this slice does not yet wire into the migration.
**Complexity:** **L** — honest assessment. Each project type has its own derivation rule; the plan-tracker parsing is the fiddly part (plan-tracker has no formal schema for unit decomposition, so derivation must be tolerant of missing prefixes — ADR §7.4 "group by feature area" fallback). This is the slice most likely to surface surprises; budget review time accordingly. (This is explicitly called out because EVD-632 showed under-estimation kills slices.)
**Scope:** **0.65.0 IN** (required for the migration to work on real non-game targets — RISK-037 criterion 8).

### FX-191 — loop_migration: `--apply` unblock + backup + rollback
**Title:** Implement `infra/loop_migration.py` — the unblocked `--apply` (ADR §7.2), `--rollback` (ADR §7.3), keeping `--dry-run`.
**Delivers:** The apply path that is currently `sys.exit(1)`-blocked in `cmd_dynamic_lifecycle_migration` is re-pointed to `loop_migration.apply_migration()` (the two-guard restructure is detailed in §4.1; the user-facing apply path is also reachable directly via the new `loop-engineering-migration` command). Read-then-write: resolve roots via `resolve_entry.py` (RISK-040 hard constraint), hash plan-tracker + evidence-log (SHA-256, 0.55.0 evidence_preservation contract), backup to `.governance/archive/migration-{version}-{timestamp}/`, derive flow units via FX-190, set `workflow_model: loop-engineering`, write `flow-unit-runtime.json`, write `MIGRATION-{version}` evidence row with before/after hashes. Rollback is total (restores exact prior state). Fail-closed cases per ADR §7.2 (missing files, unresolvable root, idempotency guard, zero derived units).
**Modules touched:** `infra/loop_migration.py` (new — `apply_migration()`, `rollback_migration()`, `preview_migration()` [factored out of existing `build_dynamic_lifecycle_migration_preview` or wrapping it], `_backup_governance_files()`, `_verify_backup_hashes()`). `verify_workflow.py`: in `cmd_dynamic_lifecycle_migration`, the apply path is restructured — BOTH blocking guards (dry-run-mandate guard at 20358-20360 and the explicit apply block at 20361-20363) must be restructured (or the control flow inverted so `--apply` is checked before the dry-run requirement) so `--apply` reaches `loop_migration.apply_migration()` instead of `sys.exit(1)`; this is a control-flow restructure of the existing cmd body, NOT a net-neutral 3-line swap (see §4.1). New `cmd_loop_engineering_migration` thin entry added (§4). `resolve_entry.py`: NO change (called as a peer — its docstring line 27 forbids importing verify_workflow; loop_migration respects this by importing resolve_entry directly).
**Dependencies:** FX-188 (registry), FX-189 (loop_engine state write), FX-190 (flow-unit derivation).
**Test strategy:**
- `infra/tests/test_loop_migration.py`. FAIL-on-buggy assertions:
  - (a) **Idempotency:** apply on an already-`loop-engineering` target → fail-closed diagnostic, no double-write.
  - (b) **Backup integrity:** after apply, the backup dir contains plan-tracker + evidence-log whose SHA-256 matches the recorded before-hashes. Tamper the backup → `_verify_backup_hashes` FAILS.
  - (c) **Rollback totality:** apply then rollback → plan-tracker, evidence-log, `workflow_model` all restored to pre-apply byte-for-byte (where feasible) or hash-for-hash; `flow-unit-runtime.json` removed; a `ROLLBACK-{version}` evidence row appended.
  - (d) **Fail-closed:** missing plan-tracker → abort before any write (no half-applied state). Missing evidence-log → abort. Unresolvable HOST_PROJECT_ROOT (RISK-040 C4) → abort with diagnostic envelope, never read PLUGIN_HOME/.governance.
  - (e) **RISK-040 divergence:** run apply in a fixture where cwd ≠ plugin-root ≠ skill-path (mirror the resolve_entry test discipline from `test_resolve_entry.py`); assert the facts read are the host's, not the plugin's.
- Regression: existing `dynamic-lifecycle-migration --dry-run` output is byte-identical pre/post (the preview path is preserved, not rewritten). Existing dry-run tests stay green.
- **Data-loss safety:** the test suite MUST include a "kill -9 mid-write simulation" (or equivalent: write a corrupt runtime.json, then re-run apply) proving the backup is always restorable. This is the ADR §7.3 "rollback is total" claim made testable.
**Complexity:** **L** — the highest-complexity slice. Read-then-write with backup+hash+rollback is where data-loss risk lives (explicitly flagged in §6 risk impact). The RISK-040 divergence discipline adds test-fixture complexity. This slice MUST get a Code Reviewer with data-integrity focus, not just a style review. Budget the most review time here.
**Scope:** **0.65.0 IN** (the apply path is RISK-037 criterion 6 — without it the version cannot claim to advance RISK-037).

### FX-192 — loop_health: pause-point velocity Check + loop-latency advisory
**Title:** Implement `infra/loop_health.py` — the Check (ADR §9.5 Part 1 BLOCKING + Part 2 ADVISORY; ADR §3.6 DORA-bridge advisory).
**Delivers:** A new `check-loop-health` CLI command. Part 1 (BLOCKING from day one): any active `PausePoint` missing `velocity_cost_justification` → FAIL with per-violation line `PP {id} active but velocity_cost_justification missing — protocol violation (DEC-097 part 2)`. Part 2 (ADVISORY): measured `velocity_cost_ms` > 3× declared bound for 3 consecutive iterations → advisory warning. Loop-latency (DORA bridge: deployment frequency, lead time, change failure rate, MTTR) reported as advisory. Outputs evidence type `LOOP-HEALTH-{flow_unit_id}-velocity`.
**Modules touched:** `infra/loop_health.py` (new — `check_loop_health()`, `_check_velocity_justification()`, `_check_velocity_exceedance()`, `_compute_dora_metrics()`, `cmd_check_loop_health` thin entry in verify_workflow.py). New argparse subparser + dispatch entry (alongside `check-architecture-health` at line 21462). Registered in `GOVERNANCE_PACK_KNOWN_CHECKS` (line 2051) so governance-pack validation covers it.
**Dependencies:** FX-188 (reads `PausePoint` declarations), FX-189 (reads `flow-unit-runtime.json` written by loop_engine).
**Test strategy:**
- `infra/tests/test_loop_health.py`. FAIL-on-buggy:
  - (a) **Part 1 blocking:** fixture with an active PP missing justification → Check returns FAIL. Add justification → PASS. This is the direct enforcement of ADR §9.5 Part 1.
  - (b) **Part 2 advisory:** fixture where measured cost exceeds 3× bound for 3 iterations → Check returns ADVISORY (warning, exit 0). Only 2 iterations → no flag (boundary). Exceeds 2× → no flag (boundary on the N multiplier).
  - (c) **velocity_check_blocking flag:** with the flag set true, Part 2 promotes to FAIL. Default false → Part 2 stays advisory.
  - (d) **DORA metrics computed from runtime.json:** deployment frequency = release-gate passes per unit time; change failure rate = fuse-trip fraction. Fixture with 2 fuse trips out of 5 loops → 40% CFR reported.
- Regression: `verify` (cmd_verify) — decide whether loop-health is a new sub-check under Check 28 (governance) or a standalone. **Recommendation: standalone CLI + advisory entry, NOT a blocking Check 28 sub-item in 0.65.0** (mirrors how ArchGuard started advisory in 0.58.0). This keeps the release gate green even if loop-health surfaces findings on the dogfood project.
**Complexity:** **M** — Part 1 is a simple presence check. Part 2 requires parsing measured latency (which may not exist in quantity until real loops run — hence advisory-first, ADR §9.5). The DORA computation is arithmetic over runtime.json. The subtlety is keeping it advisory so it doesn't block its own first release.
**Scope:** **0.65.0 IN** (ADR §9.5 P1-c resolution — the velocity-justification enforcement is a design-committed item).

### FX-193 — plan-tracker rollup view (RISK-037 criterion 2)
**Title:** Add a per-flow-unit loop_state rollup view so plan-tracker no longer expresses a single fake "current stage."
**Delivers:** A read view (CLI or plan-tracker section) that rolls up all flow units' `loop_state` — showing "chapter 1 released, chapter 2 in Inner loop round 2, chapter 3 in Middle design iteration" instead of one global stage. This is the user-facing resolution of RISK-037's core harm (ADR §1.3 "must be flattened into one fake global stage").
**Modules touched:** `infra/loop_engine.py` (adds `rollup_loop_state(root)` — pure read over `flow-unit-runtime.json`), `verify_workflow.py` (a thin `cmd_loop_rollup` ≤20 lines, OR a print section in an existing status command — recommendation: thin standalone command to avoid touching `cmd_verify` body). Possibly `core/templates/plan-tracker.md` (a documented rollup section convention — non-breaking).
**Dependencies:** FX-189 (reads the loop_state that loop_engine activates), FX-191 (the migration is what populates runtime.json on a real project).
**Test strategy:**
- `infra/tests/test_loop_rollup.py`. FAIL-on-buggy: fixture with 3 flow units at different `active_loop_tier` and `loop_count` → rollup reports each unit's tier+count, NOT a single global stage. The load-bearing assertion: **no field in the rollup collapses multiple units into one stage** (this is the RISK-037 criterion 2 "no more single 当前阶段" made into a test).
- Regression: plan-tracker parsing elsewhere in verify_workflow stays green (the rollup is a new view, not a rewrite of plan-tracker reading).
**Complexity:** **S** — pure read + format. The risk is low; the value (visible resolution of RISK-037's harm) is high. Good candidate for an early-ish win, but it depends on runtime.json being populated, so it lands after the migration.
**Scope:** **0.65.0 IN** (RISK-037 criterion 2 — "plan-tracker supports flow units / task-gate rollup").

### FX-194 — Gate-as-loop-exit re-labeling (6+1 review skills semantic update)
**Title:** Update the 6 review skills (`requirement-review`, `design-review`, `tech-review`, `code-review`, `test-review`, `release-review`) + `retro-review` to describe their gate as a loop-exit/entry certification per ADR §3.5 table, not a "stage inspection."
**Delivers:** The semantic re-labeling that makes the loop model the primary mental model in the skill docs. Each skill's SKILL.md gains a short "Loop role" section citing the ADR §3.5 mapping (e.g. `code-review` → "certifies an Inner loop's EXIT — slice/commit is mergeable"). No behavioral code change; this is documentation alignment.
**Modules touched:** 7 SKILL.md files under `skills/software-project-governance/skills/*-review/`. No `.py` change. Possibly a shared reference snippet in `references/` to avoid 7-way duplication.
**Dependencies:** FX-188 (the registry is what the labels cite). Can proceed in parallel with FX-189-FX-192 since it is doc-only.
**Test strategy:**
- A consistency check (could be a snippet-in-file check added to an existing governance check, or a test): each of the 7 review SKILL.md files mentions its loop role using the ADR §3.5 vocabulary (`loop-exit-gate` / `loop-entry-gate` + the loop tier it certifies). FAIL-on-buggy: a skill that still describes itself purely as "stage inspection" with no loop-role language.
- Regression: the 7 skills' existing review procedures (P0-P3 grading, checklists) are unchanged — only descriptive framing is added.
**Complexity:** **S** — documentation across 7 files. The risk is inconsistency between skills; a shared reference snippet mitigates it.
**Scope:** **0.65.0 IN** but **deferrable within the version** — if schedule pressure hits, this is the first slice to slip to 0.65.1 (it is doc-only; the runtime works without it). Marked IN because it carries the DEC-097 part 1 "loop is the ONLY model" semantic into the skill layer, which is the user-visible signal.

---

## 3. Test Strategy

### 3.1 Per-slice (consolidated from §2)

| Slice | Load-bearing FAIL-on-buggy test | Regression that must stay green |
|-------|----------------------------------|---------------------------------|
| FX-188 | Every G1-G11 gate has a `loop_gate_semantics` entry (ADR §10 criterion 4) | `check-manifest-consistency`, `verify` Check 11, full `pytest infra/tests/` |
| FX-189 | **Stateless round derivation**: two parallel calls against same evidence-log return same round (ADR §8.2 sacred property) | FlowUnitRuntimeTests 15/15, `test_verify_workflow.py` |
| FX-190 | **Non-game derivation**: cli-tool target with 3 commands → 3 `command` units (VAL-006 closure test) | existing migration-preview tests |
| FX-191 | **Rollback totality**: apply→rollback restores hash-for-hash; **RISK-040 divergence**: cwd≠plugin-root reads host facts | `dynamic-lifecycle-migration --dry-run` byte-identical output |
| FX-192 | **Part 1 blocking**: active PP missing justification → FAIL (ADR §9.5) | `verify` release gate stays green (loop-health is advisory entry, not blocking Check 28 sub-item) |
| FX-193 | Rollup reports per-unit tier+count, no global-stage collapse (RISK-037 criterion 2) | plan-tracker parsing |
| FX-194 | Each review SKILL.md cites its loop role per ADR §3.5 | 7 skills' existing review procedures |

### 3.2 Whole-version release gate (what must be green before 0.65.0 ships)

These are the existing suites the release-review will run, all must PASS:

1. `python verify_workflow.py verify` — full governance verify (all 28 Checks; loop-health added as advisory, not blocking).
2. `python verify_workflow.py check-manifest-consistency --fail-on-issues` — new files registered.
3. `python verify_workflow.py check-architecture-health` — ArchGuard module-size guard. **Critical assertion:** verify_workflow.py does NOT grow beyond its current 21,651 lines by more than the 3 thin-entry delegators (~60 lines). If ArchGuard ERRORs on verify_workflow.py size growth, the slice that caused it MUST extract more before merge. This is the RISK-039 God-Module guard, actively enforced. **Scope note:** ArchGuard currently enforces only the GLOBAL `module_size` threshold and a global `function_size.warn_lines`/`error_lines` threshold (currently 200/500) applied to ALL functions via `ast.walk` (verify_workflow.py:18878-18932). It does NOT, in 0.65.0, mechanically enforce the per-`cmd_*` ≤20-line thin-entry limit — that limit is enforced by Code Review (see §4.2 for the honest statement and the 0.66.0+ ArchGuard follow-on).
4. `python verify_workflow.py check-duplicate-code` — no new source/projection duplication from the loop modules.
5. `pytest infra/tests/ -q` — full unit suite (baseline + new loop tests).
6. `infra/verify-e2e.sh` — end-to-end (if it covers migration, extend it for `--apply` on a fixture).
7. Projection-sync (source/projection): the new modules must be projected consistently (no new F3 double-write — loop modules are net-new source, projected once).
8. Version-consistency: SKILL.md frontmatter version bumped to 0.65.0; lifecycle-registry.json `workflow_version`; the new registry's `schema_version`; manifest.json version; changelog. `check-release --version 0.65.0 --require-changelog --runtime-adapters` PASS.

### 3.3 The sacred pattern: stateless round derivation must be PROVEN parallel-safe

ADR §8.2 claims the generalized round derivation is "parallel-safe by construction" because round is derived entirely from the evidence-log max R{n}, with no in-memory counter. This is the property that makes the fuse safe under M7.6/M7.6a parallel dispatch. The test (FX-189) must:

1. **Construct** an evidence-log fixture with a known set of `LOOP-{U}-{tier}-R{n}` rows.
2. **Call** `derive_round(unit, tier, evidence_log)` and assert the expected max.
3. **Prove statelessness:** call it N=10 times in sequence against the same fixture; assert all return the same value (no accumulation).
4. **Prove parallel-safety:** call it from two concurrent threads/processes against the same fixture (read-only); assert both return the same value and neither mutates shared state. (A threading test is sufficient — the derivation must be pure.) This is the direct, executable proof of ADR §8.2.
5. **FAIL-on-buggy:** a buggy implementation using an in-memory counter would either accumulate across calls (caught by step 3) or diverge under concurrency (caught by step 4).

This test is the single most important one in the version. If it passes, the sacred property is preserved; if a future change breaks it, CI catches the regression.

### 3.4 VAL-006 generalization test (how to verify flow-unit derivation works on a non-game target)

VAL-006 proved flow units only came from the `python_game` example. The closure test (FX-190) must:

1. **Pick a non-game project type** (recommend `cli-tool` — cleanest decomposition: one unit per command).
2. **Construct a minimal plan-tracker** for a hypothetical cli-tool with 3 commands (e.g. `mycli.init`, `mycli.build`, `mycli.deploy`).
3. **Run** `derive_flow_units(target_root, "cli-tool", plan_tracker)`.
4. **Assert** 3 flow units result, each `unit_type: command`, with stable `flow_unit_id`s derived from the command names.
5. **Repeat** for at least one more non-game type (`library` → derive from api-surface/modules) to prove the derivation isn't cli-specific.
6. **Fallback path:** an empty/featureless plan-tracker → exactly ONE `{project_id}.whole` unit with `derivation_reason: "no-decomposable-structure-found"` (ADR §7.4 fallback — honest, doesn't fake granularity).
7. **Game regression:** the existing python_game fixture still derives chapters (the proven path must not break).

Archiving the result of running this derivation on a REAL non-game target (not just a fixture) is part of RISK-037 criterion 8 closure — but that archival is post-implementation external validation (ADR §10), not part of the 0.65.0 test suite.

---

## 4. Thin-Entry Delegator Design

Each new CLI command gets a ≤20-line `cmd_*` in verify_workflow.py that does ONLY: stdout reconfigure + argparse field extraction + delegation + result printing + exit code. All real logic lives in the new `infra/loop_*.py` module. This follows the Phase-1 split discipline (D4/D5 from `verify-workflow-split-phase1-manifest-domain-0.59.0.md`).

**Honest precedent note (do not overstate):** the cycle-avoidance PRINCIPLE is proven by `manifest.py`'s `_vw()` deferred-import pattern (infra/checks/manifest.py:31-43). But `cmd_check_manifest_consistency` itself is 45 lines and lives in `infra/checks/manifest.py`, NOT verify_workflow.py — Phase-1 decision D5 MOVED it OUT entirely (verify_workflow.py retains only a `from checks.manifest import (...)` re-export at line 839). So the leave-the-delegator-in-place variant (a ≤20-line `cmd_*` that STAYS in verify_workflow.py) is a NEW application of the cycle-avoidance principle, NOT a replay of the Phase-1 pattern (which moved `cmd_*` OUT of verify_workflow.py entirely). This new variant is accepted by DEC-099 as a temporary trade-off, to be validated by the first loop-engineering slice. It is not "proven" by `cmd_check_manifest_consistency` — the precedent proves the import-cycle avoidance, not the stay-in-place delegator.

### 4.1 Signature sketches (contract for the Developer)

**`cmd_loop_engineering_migration`** (≤20 lines) — delegates to `loop_migration`:
```python
def cmd_loop_engineering_migration(args):
    """Thin entry — delegates to infra/loop_migration.py (0.65.0 loop-engineering)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from loop_migration import apply_migration, rollback_migration, preview_migration  # deferred (cycle-safe)
    if getattr(args, "rollback", False):
        result = rollback_migration(getattr(args, "target", None))
    elif getattr(args, "apply", False):
        result = apply_migration(getattr(args, "target", None))
    else:
        result = preview_migration(getattr(args, "target", None))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") == "BLOCKED" and getattr(args, "fail_on_issues", False):
        sys.exit(1)
```
**Note:** the `from loop_migration import ...` is deferred inside the function (not top-level) to guarantee no import cycle, mirroring the `_vw()` discipline. Total body ≤20 lines.

**`cmd_check_loop_health`** (≤20 lines) — delegates to `loop_health`:
```python
def cmd_check_loop_health(args):
    """Thin entry — delegates to infra/loop_health.py (0.65.0 loop-engineering)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from loop_health import check_loop_health
    result = check_loop_health(getattr(args, "target", None))
    print("\n=== Loop Health Check (velocity + latency) ===")
    findings = result.get("findings", [])
    for f in findings[:25]:
        print(f"  [{f.get('severity','?')}] {f.get('pause_point','')}: {f.get('message','')}")
    blocking = [f for f in findings if f.get("severity") == "FAIL"]
    print(f"\n  Result: {len(blocking)} BLOCKING, {len(findings)-len(blocking)} advisory")
    if blocking and getattr(args, "fail_on_issues", False):
        sys.exit(1)
    print()
```

**`cmd_dynamic_lifecycle_migration`** (EXISTING, line 20352 — control-flow restructure, NOT net-neutral): the command currently has TWO blocking guards. Guard 1 (lines 20358-20360) fires `sys.exit(1)` whenever `--apply` is passed WITHOUT `--dry-run`. Guard 2 (lines 20361-20363) is the explicit `--apply` block. If only guard 2 were replaced, running `dynamic-lifecycle-migration --target X --apply` (without `--dry-run`) would still hit guard 1 and never reach the new delegation — leaving the existing command's `--apply` path broken. Therefore BOTH guards must be restructured (or the control flow inverted so `--apply` is checked BEFORE the `--dry-run` requirement): the `--apply` branch must reach `loop_migration.apply_migration()` without being gated by the dry-run precondition. The existing `--dry-run` preview path is preserved unchanged. This edit is NOT net-neutral — it is a control-flow restructure of the existing command body (the dry-run-mandate guard must move or be conditioned out of the `--apply` path).

**Reachability note:** the NEW `loop-engineering-migration` command (fresh argparse in `cmd_loop_engineering_migration`, above) is unaffected — its `--apply` path is reachable directly. So the user-facing apply path is reachable via the new command regardless of how the existing command's restructure lands. The breakdown does NOT claim the existing `dynamic-lifecycle-migration` command's `--apply` "becomes functional" — only that it is re-pointed to delegate; whether its `--apply` reaches the delegation depends on the guard restructure being done correctly.

### 4.2 ArchGuard enforcement of the ≤20-line limit

ArchGuard (`check-architecture-health`, 0.58.0) already guards module/function sizes, but **the current `check_architecture_health()` (verify_workflow.py:18878-18932) applies a single GLOBAL `function_size.warn_lines`/`error_lines` threshold (200/500) to ALL functions via `ast.walk`.** There is NO per-function-name-pattern override mechanism in the code or in `core/architecture-health.json`. Therefore the ≤20-line thin-entry limit **CANNOT be enforced by ArchGuard via config alone in 0.65.0** — doing so would require new ArchGuard code (extending `check_architecture_health` to support per-pattern thresholds keyed on function name, not just one global threshold).

**Honest enforcement posture for 0.65.0:** the ≤20-line limit is enforced by **Code Review**, not ArchGuard. A Reviewer rejects any `cmd_*` thin entry exceeding 20 lines and requires the excess logic to move into the corresponding `infra/loop_*.py` module before merge. This is the same human-review discipline the Phase-1 split relied on before ArchGuard existed.

**0.66.0+ follow-on (not 0.65.0 scope):** an ArchGuard per-function-name-pattern rule that mechanically flags any `cmd_*` function in verify_workflow.py exceeding 20 lines as a WARN (advisory, matching ArchGuard's current advisory posture), with a documented path to ERROR (blocking) once the split discipline is proven across more slices. Implementing this requires extending `check_architecture_health` to support per-pattern thresholds, not just the global one — it is explicitly out of scope here (no slice decomposition change; it is a future enhancement).

**Why the enforcement gap is acceptable:** DEC-099 already accepts that the thin-entry delegators temporarily stay in the God Module (Risk A, §6.2). The global `module_size` ArchGuard guard still caps verify_workflow.py's total growth (§3.2 item 3), and the per-delegator limit is bounded by review. The gap is acceptable because it is stated honestly — the slices do NOT claim mechanical enforcement they cannot deliver.

### 4.3 argparse / dispatch registration (the only other verify_workflow.py additions)

Three blocks of registration lines (no logic):
- argparse: a new subparser block near line 21402 (`dynamic-lifecycle-migration`) for `loop-engineering-migration` with `--apply`/`--rollback`/`--dry-run`/`--target`/`--fail-on-issues`; a new subparser near line 21462 (`check-architecture-health`) for `check-loop-health`.
- dispatch dict: two new entries near line 21621 (`"loop-engineering-migration": cmd_loop_engineering_migration`, `"check-loop-health": cmd_check_loop_health`).
- `GOVERNANCE_PACK_KNOWN_CHECKS` (line 2051): add `"check-loop-health"`.

These are registration lines, not logic — consistent with the God-Module constraint (the constraint forbids new logic, not new command wiring).

---

## 5. Version Scope Confirmation

### 5.1 IN 0.65.0 (must-ship slices)

| Slice | Title | Complexity | Why must-ship |
|-------|-------|-----------|---------------|
| FX-188 | Loop-engineering registry + loader | M | Foundation — all other slices read it |
| FX-189 | loop_engine core (loop_state + sacred fuse) | M | ADR §8 fuse is non-optional; the parallel-safe property must be proven |
| FX-190 | flow_unit_derive (VAL-006 gap) | L | RISK-037 criterion 8 (non-game generalization) — the apply path is useless on real targets without it |
| FX-191 | loop_migration (--apply + backup + rollback) | L | RISK-037 criterion 6 (apply/write path) — the central unblocking work |
| FX-192 | loop_health (velocity Check + latency advisory) | M | ADR §9.5 P1-c resolution (velocity-justification enforcement, design-committed) |
| FX-193 | plan-tracker rollup view | S | RISK-037 criterion 2 (no more single global stage) — the user-visible harm resolution |
| FX-194 | Gate-as-loop-exit re-labeling (7 skills) | S | DEC-097 part 1 semantic into skill layer (deferrable within version — see below) |

**Total complexity budget:** 2×L + 3×M + 2×S. The two L slices (FX-190, FX-191) are the schedule risk; they are also the two that most directly advance RISK-037. EVD-632 (0.61.0 FIX-155/156 abandonment) is the cautionary precedent — those slices were marked M and were actually L. This plan marks FX-190/FX-191 as L upfront so review/resourcing is honest.

### 5.2 DEFERRED to 0.65.1+ or later (nice-to-have, can ship without)

- **`--rederive-flow-units` subcommand** (ADR §12 Q8): a project that already migrated wants to re-decompose after a restructure. 0.65.0 ships `--apply` (refuses if already loop-engineering) + `--rollback`; re-derivation without touching `workflow_model` is a 0.65.1 follow-on. Rationale: `--apply`'s idempotency guard is simpler and safer for first release; the re-derive use case is rarer.
- **`velocity_check_blocking = true` promotion** (ADR §9.5 Part 2): the flag ships as `false` (advisory). Promoting Part 2 to blocking is deferred until real telemetry calibrates the 3×/3-iteration threshold. Rationale: ADR §9.5 explicitly says premature blocking would fire on noise.
- **`release-to-design-replan` `auto_fire: true` opt-in per preset** (ADR §6.4 P1-b): ships `auto_fire: false` (human-gated). The opt-in is deferred until telemetry proves the G5-concurrence filter is sufficient. Rationale: ADR §6.4 conservative default.
- **loop-health as a blocking Check 28 sub-item**: ships advisory/standalone. Promotion to blocking governance sub-check deferred (mirrors ArchGuard 0.58.0→later-blocking path).
- **Loop-type taxonomy runtime hooks** (ADR §5.5 heartbeat/cron): the taxonomy is declared in the registry (FX-188) but heartbeat/cron trigger runtimes are deferred — the first two loop types (goal-based, hook/event) are native; scheduled/cron reuse existing M7.3 risk-escalation deadlines and need no new code in 0.65.0.
- **Real-target archival for RISK-037 criteria 5/7 external validation** (ADR §10): the derivation runs on fixtures in 0.65.0; running it on a real non-dogfood target and archiving is post-implementation external validation (0.65.1+ or a dedicated validation cycle).

### 5.3 The 90% completion rule

Per the project's version-completion discipline: **≥90% of in-scope slices must complete to release 0.65.0.** There are 7 in-scope slices; 90% = 6.3, so **at least 7 of 7 must complete** (rounding up — 6/7 = 85.7% < 90%). 

This means 0.65.0 is all-or-nearly-all: the only slice with declared deferral room is **FX-194** (the 7-skill doc re-labeling), which can slip to 0.65.1 without blocking the release because it carries no runtime dependency. If FX-194 slips, that is 6/7 = 85.7%, which is below 90% — **so even FX-194 slipping would technically trip the rule.** The honest reading: either (a) ship all 7, or (b) if schedule forces a slip, formally move the slipped slice to 0.65.1 scope BEFORE release (so the 0.65.0 denominator shrinks) and document the re-scope in the changelog + risk-log. Silent partial shipment is not acceptable under the 90% rule.

**Recommendation:** treat all 7 slices as must-ship for 0.65.0; if FX-190 or FX-191 (the L slices) hit trouble, escalate early (DEC-086-style user decision) rather than silently slipping — because those two carry the RISK-037 advancement claim, and 0.65.0 cannot honestly advance RISK-037 without them.

---

## 6. Risk-Register Impact

### 6.1 Does 0.65.0 close RISK-037?

**No.** It **advances** RISK-037. Specifically, post-0.65.0 the status of the 8 closure criteria (ADR §10) becomes:

| Criterion | Pre-0.65.0 | Post-0.65.0 (if all slices ship) |
|-----------|-----------|----------------------------------|
| 1 (registry published) | Met (0.51.0) | Met |
| 2 (plan-tracker flow-unit rollup) | DESIGN-MET, IMPL-PENDING | **IMPL-MET** (FX-193) — pending external validation |
| 3 (game + non-game preset gate standards) | Met (0.53.0) | Met |
| 4 (gate engine classic compat) | DESIGN-MET (DEC-098), IMPL-PENDING | **IMPL-MET** (FX-188 — every gate has loop semantics; FX-194 — skills relabeled) |
| 5 (migration guide + external validation) | DESIGN-MET, IMPL-PENDING | **IMPL-MET for guide/migration** (FX-191); external validation STILL PENDING |
| 6 (apply/write path) | DESIGN-MET, IMPL-PENDING | **IMPL-MET** (FX-191) |
| 7 (installed-state full PASS or acceptable failure archive) | IMPL-PENDING | Still PENDING — depends on external validation |
| 8 (non-game flow-unit generalization) | DESIGN-MET, IMPL-PENDING | **IMPL-MET for derivation** (FX-190); external validation STILL PENDING |

**RISK-037 remains OPEN** because criteria 5, 7, 8 require **external validation on a real non-dogfood target** (ADR §10, §11 no-overclaim) — which is post-implementation work, not 0.65.0 code. The 0.65.0 release notes MUST state this explicitly: "advances RISK-037 criteria 2/4/6 to impl-met; criteria 5/7/8 remain pending external validation; RISK-037 stays OPEN."

### 6.2 New risks introduced by 0.65.0

**Risk A — Thin-entry delegators temporarily in the God Module.** The 3 new `cmd_*` delegators + registration lines ADD ~60-80 lines to verify_workflow.py (currently 21,651). This is a temporary RISK-039 regression: the God Module grows, not shrinks, in 0.65.0. Mitigation: ArchGuard (§4.2) flags any delegator >20 lines; the net growth is bounded and documented; the long-term fix is the continuing DEC-083 split (0.66.0+) which extracts the delegators' parents. **This does not close RISK-039** and the release notes must record the temporary growth.

**Risk B — Migration `--apply` data-loss risk.** FX-191 performs a read-then-write on `.governance/plan-tracker.md` + `evidence-log.md` + new `flow-unit-runtime.json`. A bug in backup/hash/rollback could corrupt governance state. Mitigation: the §3/FX-191 test strategy (backup integrity, rollback totality, kill-mid-write simulation, RISK-040 divergence) is the primary guard; FX-191 gets the heaviest Code Review focus. Additionally, the apply path requires explicit `--apply` (no implicit write), and `--dry-run` remains the default.

**Risk C — Sacred-property regression.** If a future change to `loop_engine.derive_round` reintroduces an in-memory counter, the parallel-safety property breaks silently. Mitigation: the FX-189 sacred-property test (§3.3) runs in CI on every change to loop_engine.py; it is explicitly the load-bearing regression test.

**Risk D — Backward-compatibility break (DEC-097 part 1).** Loop becomes the only primary model; classic G1-G11 becomes a vocabulary/rollback target. Projects that relied on the classic primary mode must migrate. This is an **accepted, user-mandated break** (DEC-097), but it is a break nonetheless — see §6.3.

### 6.3 Should RISK-041 be registered? — YES (ADR §12 Q9)

**Recommendation: register RISK-041 ("loop-engineering activation backward-compat") in `.governance/risk-log.md` as part of 0.65.0, mirroring how RISK-040 governed the 0.64.0 entry-resolver.** Rationale (per ADR §12 Q9, which already leans yes):

1. **Honest separation.** Rolling the loop-engineering activation silently into a RISK-037 advancement claim would conflate "we built it" (0.65.0) with "external projects validated it" (future). RISK-041 keeps these distinct.
2. **Precedent.** RISK-040 was created for the 0.64.0 entry-resolver because it touched a path with a failure history (0.54.2/0.54.3). Loop-engineering touches the primary execution model with a dormancy history (0.51-0.55 schema-only). The symmetry is exact.
3. **Closure criteria for RISK-041 (suggested):**
   - (1) The 7 slices ship with all §3 tests green (this plan).
   - (2) The stateless round-derivation sacred-property test passes (FX-189) — the loop-control mechanism is proven safe.
   - (3) The migration `--apply` + `--rollback` is proven total on a fixture (FX-191 rollback-totality test).
   - (4) **External validation:** run `--apply` on at least one real non-dogfood project and archive the result (this is the same external-validation gate RISK-037 criteria 5/7/8 need — RISK-041 and RISK-037 close together at external validation).
   - (5) Independent Design Reviewer + Code Reviewer sign-off on FX-191 (the data-loss-risk slice).
4. **Due date:** align with RISK-037 (2026-07-30) since they close together at external validation, OR set RISK-041's own date post-0.65.0 (e.g. 2026-09-30, aligning with RISK-039/040) since the external validation can follow the code release. **Recommendation: 2026-09-30** — the code ships in 0.65.0, external validation follows.

**This plan does NOT register RISK-041 itself** (this is a PLAN, §0) — it recommends that the Coordinator register it as the first 0.65.0 governance action.

---

## 7. No-Overclaim Boundaries (restated)

**This document is a PLAN. It:**
- Writes NO product code. No `.py`, no `.json` registry, no SKILL.md is modified by producing this plan.
- Registers NO tasks in plan-tracker (the FX-188..FX-194 IDs are proposed; formal registration is a separate Coordinator action).
- Registers NO risk (RISK-041 is recommended; registration is a separate action).
- Closes NO risk. RISK-037 stays OPEN; RISK-039/040 untouched.
- Claims NO version release. 0.65.0 ships only when the slices are implemented, tested, reviewed, and the release-gate (§3.2) is green.
- Re-decides NOTHING in the ADR. Where the ADR left a question open (Q7 registry placement, Q9 RISK-041), this plan makes a recommendation clearly marked **[ARCHITECT-DEC]** for the Coordinator/Reviewer to confirm or override.

**This document DOES:**
- Decompose a finalized, twice-approved ADR into 7 buildable, independently-reviewable slices.
- Ground every module path, function name, and registry field in the actual codebase (verified: `FLOW_UNIT_RUNTIME_STATE_REL` at verify_workflow.py:1805; `flow_unit_schema.loop_state` at lifecycle-registry.json:520; M7.4 §4.6 at behavior-protocol.md:493-536; `resolve_entry.py` dual-root at lines 11-24; the Phase-1 `_vw()` deferred-accessor pattern at checks/manifest.py:23-43).
- Name the load-bearing test for each slice (the FAIL-on-buggy assertion that proves the ADR's claims).
- Honestly mark the two L slices (FX-190, FX-191) as the schedule/data-loss risks, citing EVD-632 as the precedent for why under-estimation kills slices.

---

## Appendix — Decision Provenance for this Plan

- **DEC-097** (loop-first refactor mandate, 3 parts) — the binding user decision this plan decomposes.
- **DEC-098** (RISK-037 criterion-4 re-scope) — resolves the P0; lets loop-engineering implementation start.
- **DEC-099** (0.65.0 independent MINOR承载) — fixes the version this plan targets.
- **REVIEW-AUDIT-130-R0/R1** — Design Reviewer two-round review of the ADR; APPROVED_WITH_NOTES; 1 P0 + 3 P1 resolved. This plan inherits the resolved design (P1-a setup-loop in FX-188; P1-b human-gated back-edge in FX-188; P1-c velocity Check in FX-192).
- **Phase-1 split methodology** (`verify-workflow-split-phase1-manifest-domain-0.59.0.md` D4/D5) — the thin-entry delegator discipline this plan follows (§4). The Phase-1 cycle-avoidance mechanism is proven by `checks/manifest.py`'s `_vw()` deferred-import pattern (infra/checks/manifest.py:31-43); the stay-in-verify_workflow.py thin-delegator variant is a new application accepted by DEC-099, not a replay of D5 (which moved `cmd_check_manifest_consistency` OUT to manifest.py).
- **EVD-632** (0.61.0 FIX-155/156 abandonment) — the complexity-under-estimation precedent this plan explicitly counters by marking FX-190/FX-191 as L.

---

## Change Record

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-07-10 | 0.1 | Initial implementation breakdown (Architect output, design-only; no code) | Architect |
| 2026-07-10 | 0.2 | Accuracy fixes per Design Reviewer P1/P2 findings: P1-1 ArchGuard ≤20-line enforcement restated as Code-Review-enforced (§3.2 item 3, §4.2, §1.2 build-order 6); P1-2 `cmd_dynamic_lifecycle_migration` two-guard restructure (§1.5 table + closing para, §4.1, FX-191 Delivers + Modules-touched); P1-3 `cmd_check_manifest_consistency` precedent reframed (§1.1 intro, §4 intro, Appendix); P2 line-drift fixed (`GOVERNANCE_PACK_KNOWN_CHECKS` 2395→2051 ×2; `resolve_entry.py` docstring "lines 26-27"→"line 27" ×2; `_vw()` pattern 31-46→23-43). No slice/scope/design changes. | Architect |

<!-- loop-runtime-superseding:{"schema_version":"1.0","notice_id":"LRC-BREAKDOWN-0650","effective_version":"0.66.1","supersedes_claim_ids":["LRC-HIST-BREAKDOWN-001"],"authority_ids":["AUDIT-133","EVD-707","DEC-104"],"classification":{"runtime_activation":"NOT_MET","migration_validity":"NOT_MET","criteria_2_3_4_5_6":"PARTIAL","criterion_7":"NOT_PROVEN","criterion_8":"MET-NARROW","capability":"experimental_scaffolding"},"open_risks":["RISK-037","RISK-042"]} -->

Current interpretation: completion of the listed implementation slices produced experimental scaffolding and review-chain enforcement, not the complete persisted Loop runtime described by the target breakdown.
