# Loop Engineering Post-Implementation Audit - 0.66.0

**Task**: AUDIT-133
**Date**: 2026-07-11
**Scope**: DEC-097/098/099, the 0.65.0 Loop Engineering ADR, FX-188 through FX-194, current 0.66.0 code, dedicated tests, and VAL-007 external evidence.

## 1. Audit Rule

This audit accepts only repository code, reproducible command output, and recorded external-project artifacts that can still be checked. Design intent does not prove implementation. A test name does not prove its assertion is load-bearing. Dogfood data does not prove external effectiveness. Missing evidence is NOT_PROVEN, never inferred as success.

## 2. Overall Verdict

The architectural direction is useful, but the delivered implementation does **not** meet the stated refactor expectation.

- **Design direction**: PARTIAL-MET. Nested feedback loops, per-flow-unit state, bounded iteration, rollback, evidence grounding, and AI Plan-Act-Observe-Reflect are appropriate design primitives.
- **Runtime activation**: NOT_MET. The product still declares classic phase-gate as active/default and schema-only. Core loop transition functions have no production callers.
- **Migration validity**: NOT_MET. --apply returns success while writing a payload rejected by the product's own runtime validator.
- **External effectiveness**: NOT_PROVEN. VAL-007 proves a write path and one target-derived name, but its persisted runtime currently fails validation and remains dormant.
- **Modern flow/AI outcomes**: PARTIAL-MET. The ADR names relevant concepts, but WIP control, outcome feedback, persistent agent-phase transitions, real back-edges, and complete telemetry are not operational.

The current state is better described as declarations, isolated helpers, migration scaffolding, and documentation relabeling, not an activated loop-first execution model.

## 3. Evidence Matrix

| Expected capability | Design | Implementation | Validation | Verdict |
| --- | --- | --- | --- | --- |
| Loop is the primary execution model | ADR explicitly requires it | lifecycle registry remains classic-phase-gate and schema-only | check-lifecycle-registry reports classic active/default | NOT_MET |
| Per-flow-unit independent state | Schema and rollup are defined | migration derives units but writes dormant loop state; dogfood has no runtime | loop-rollup reports 0 units / not migrated | PARTIAL |
| Plan-Act-Observe-Reflect is first-class | ADR and registry declare phases/pause points | activate_loop_state accepts an arbitrary phase but no production controller calls it | production AST call-site scan returns zero callers | NOT_MET |
| Gate failure iterates a loop/back-edge | ADR and registry declare mappings | auto_judge_gate returns blocked; it does not read loop semantics or execute a back-edge | no production calls to get_loop_gate_semantics | NOT_MET |
| Fuse bounds repeated iterations | Pure functions and registry limits exist | no production call persists rounds, invokes fuse decision, or emits escalation | isolated unit tests pass; runtime wiring absent | PARTIAL |
| Safe, predictable migration | Backup/rollback design exists | dry-run and apply use disjoint planners; apply writes validator-invalid payload | temp target: apply exit 0, validator exit 1 with 21 issues | NOT_MET |
| External non-game proof | VAL-007 uses shitu Android | one unit is target-derived but dormant and marked example-data-only | current shitu runtime validator fails with 19 issues | PARTIAL |
| Loop health and DORA feedback | ADR defines pause cost and four DORA dimensions | registry check is standalone; no telemetry writer; metrics are incomplete | corrupt registry produces 0 blockers; normal output is 0/0 | NOT_MET |
| Parallel flow and modern Flow/WIP | dependencies and per-unit fields are declared | no runtime scheduler, WIP limit, dependency transition engine, or persisted concurrent loop controller | no real multi-unit multi-lane external run | NOT_PROVEN |
| Regression protection | dedicated suites exist | suites test helpers in isolation and encode incompatible payload as expected success | 99/99 tests pass while real validator fails | PARTIAL |

## 4. Confirmed Findings

### F1 - P0: Successful migration produces an invalid runtime artifact

Facts:

- loop_migration.py::apply_migration writes workflow_model=loop-engineering and a reduced payload.
- verify_workflow.py::check_flow_unit_runtime accepts only classic-phase-gate or dynamic-flow-gate and requires a different top-level/unit contract.
- A temporary CLI-tool target returned applied=true, exit 0, and two units. Immediate check-flow-unit-runtime returned exit 1 with 21 issues.
- The persisted VAL-007 shitu runtime also returns exit 1 with 19 issues.

Impact: users receive success for state the product itself rejects. VAL-007 criterion 7 is NOT_MET, not PARTIAL-MET.

Required correction: use one canonical runtime schema shared by planner, writer, reader, validator, and tests. Validate the complete plan before any write and after atomic commit. Any commit failure must automatically restore or expose an explicit transaction-recovery state.

### F2 - P0: The loop execution core is not wired into production

Facts:

- lifecycle-registry.json declares schema-only-no-runtime-activation, active/default classic-phase-gate, and disabled runtime activation.
- Production AST call-site scan found zero calls to activate_loop_state, fuse_decision, escalation_payload, or get_loop_gate_semantics.
- auto_judge_gate executes classic checks and returns blocked; it does not consume loop role, back-edge, or fuse metadata.
- Migration-created units are dormant: active_loop=false, count 0, no agent phase.
- The current project is not migrated; loop-rollup reports zero units and zero active loops.

Impact: Loop-as-the-only-model and first-class Plan-Act-Observe-Reflect are declaration claims, not runtime behavior. Gate failures do not iterate, and fuses cannot bound production rework.

Required correction: introduce a persistent flow-unit transition service that owns phase, gate result, back-edge, round, fuse, and evidence writes. Route production gate outcomes through it.

### F3 - P1: Dry-run cannot predict apply

Facts: preview_migration delegates to the legacy preview and may use python_game example units. apply_migration independently calls target-derived derive_flow_units. VAL-007 records that dry-run showed game units while apply produced one Android unit.

Impact: users cannot review the actual planned write, defeating the safety purpose of dry-run.

Required correction: build one pure migration plan. Dry-run serializes it; apply validates and commits the same plan hash.

### F4 - P1: Loop health fails open and lacks a telemetry pipeline

Facts:

- _check_velocity_justification returns no findings when the registry is unavailable.
- check_loop_health(plugin_home=missing) reports zero blockers/advisories.
- test_envelope_fail_closed_on_corrupt_registry asserts blocking_count == 0, which is fail-open.
- Migration writes no velocity_history or dora data; no production writer was found.
- The ADR names four DORA dimensions. Implementation reports a raw release count, a fuse ratio, and omits lead time/MTTR.

Impact: the only claimed blocking health rule silently passes when its authority is missing, while DORA maturity is overstated.

Required correction: authority failure must be blocking/unknown. Add telemetry event contracts before reporting time-based metrics; normalize by time window or rename raw counters honestly.

### F5 - P1: Dedicated tests do not cover an integrated loop workflow

Facts:

- Six dedicated modules run 99 tests successfully.
- Migration tests assert the incompatible loop-engineering payload as success and never call check_flow_unit_runtime.
- Engine tests invoke activation/fuse helpers directly; production call-site coverage is absent.
- Rollup tests use populated fixtures even though the actual writer creates dormant units.

Impact: a green focused suite coexists with a broken user journey.

Required correction: add preview -> apply -> validator -> gate fail -> persisted back-edge/round -> fuse escalation -> restart -> rollback tests, plus mutation probes that remove production wiring.

### F6 - P1: External validation and historical evidence are overclassified

Facts:

- VAL-007 proves backup/write/rollback availability and one target-derived identifier.
- It does not prove valid runtime, active loops, multiple stages, native-entry/hook full pass, or gate iteration.
- EVD-678 says loop state was activated, but the activation function has no production caller.
- EVD-682 says rollup replaces global stage, while status still uses a global stage and dogfood rollup is empty.
- The 0.65.0 changelog says linear flow is superseded, while registry validation requires classic active/default.

Impact: later agents can skip missing runtime work because governance evidence reports implementation completion.

Required correction: add superseding AUDIT-133 facts without rewriting history; downgrade RISK-037 criteria 2/4/5/7; label current Loop Engineering experimental/scaffolding until runtime gates pass.

### F7 - P2: Modern flow and product-outcome controls are incomplete

Facts: the ADR contains feedback loops, gates, vertical slices, risk escalation, rollback, and pause-cost reasoning. No executable WIP limit, queue policy, batch-size guard, outcome hypothesis loop, or dependency scheduler was found. Heuristic derivation may collapse a mobile project to one unit.

Impact: the model captures iteration vocabulary but cannot yet control overload or prove customer outcomes.

Required correction: add explicit WIP/dependency policies and outcome acceptance signals. Keep heuristic derivation advisory and require confirmed decomposition before activation.

### F8 - P2: Migration can leave a partial write

Facts: runtime JSON is written before the evidence row. If evidence append fails, apply returns false but leaves runtime JSON and asks the user to roll back.

Impact: a failed command can leave the idempotency marker and a partially migrated project.

Required correction: use a transaction journal and automatic rollback, or atomically replace all staged outputs.

## 5. What Is Worth Keeping

- Nested-loop vocabulary and gate-as-loop-exit framing.
- Per-flow-unit state instead of one global project stage.
- Stateless evidence-derived round calculation.
- Explicit fuses and human escalation choices.
- Backup/hash/rollback intent and host/plugin root separation.
- Independent roles, no-overclaim boundaries, and immutable release facts.
- Dedicated modules rather than adding more logic to verify_workflow.py.

## 6. Planned Evolution

### 0.66.1 - Containment hotfix

- FIX-195: block apply unless the planned payload passes the canonical runtime validator; automatically restore failed commit steps.
- FIX-196: make loop-health authority failure blocking/unknown.
- FIX-197: correct active documentation/evidence claims and label current Loop Engineering experimental scaffolding.
- Acceptance: current shitu artifact is diagnosed; a new migration cannot return success with invalid state.

### 0.67.0 - Canonical runtime and planner

- FEAT-002: one versioned Loop Runtime Contract consumed by writer/validator/reader/rollup.
- FEAT-003: one pure planner shared by preview/apply with a plan hash.
- FEAT-004: explicit decomposition confirmation and canonical initial gate state.
- Existing Phase 5 evidence/risk/review extraction moves to 0.70.0; P0 runtime correctness takes precedence.

### 0.68.0 - Executable loop engine

- FEAT-005: persistent Plan-Act-Observe-Reflect phase transitions.
- FEAT-006: per-unit gate back-edges, rounds, fuses, and escalation through production entries.
- FEAT-007: restart-safe event log, dependency blocking, and WIP policy.
- Acceptance: restart preserves state; one failing gate advances one round and the configured fuse eventually trips.

### 0.69.0 - Flow metrics and external proof

- FEAT-008: real telemetry and honestly named flow/DORA metrics.
- VAL-008: dogfood multi-unit/multi-lane scenario.
- VAL-009: two external project types, including shitu, with preview/apply identity, runtime validator PASS, active transitions, rollback, native-entry, and hook checks.
- RISK-037 may only be reconsidered after these results.

## 7. New Release Gates

No future version may claim runtime completion unless all pass:

1. planned payload validates before write;
2. apply output validates after write;
3. preview plan hash equals applied plan hash;
4. two flow units can hold different phases/gates;
5. production gate failure persists one back-edge and increments one round;
6. restart preserves state;
7. fuse escalation is reached through a production entry;
8. health authority failures do not pass;
9. external installed-state validation passes or is archived as failure;
10. release wording matches evidence strength.

## 8. Review Status

Independent review is complete; no role approved the delivered runtime as meeting the refactor expectation.

| Review | Terminal result | Independent conclusion |
| --- | --- | --- |
| AUDIT-133-ARCH | NOT_MET | The design is broad and reusable, but the production runtime closure is absent. RISK-037 must remain open. |
| AUDIT-133-CODE | BLOCKED | Invalid migration output and missing production loop wiring are P0 defects; this is an architectural break, not a local patch-only approval. |
| AUDIT-133-QA | FAIL | 99/99 focused tests pass, but they do not cover apply-to-validator, production transitions, restart, multi-unit flow, or fuse escalation. |

The reviews independently converged on the same release boundary: keep the existing vocabulary, registry, pure helpers, backup intent, and review contracts, but classify the current capability as experimental scaffolding until the canonical runtime and production transition gates in section 7 pass.
