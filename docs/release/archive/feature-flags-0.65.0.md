# Feature Flags - 0.65.0

**Version**: 0.65.0 (minor)
**Release**: Loop-Engineering Workflow Refactor — three-tier nested loop model + AI Plan-Act-Observe-Reflect first-class citizen (DEC-097/098/099, FX-188~FX-194, RISK-037 progress)
**Date**: 2026-07-10

## Feature Flag Inventory

This release introduces the loop-engineering capability layer with **no runtime feature flags** in the toggle sense — the new modules are always active when invoked. The behavioral change is additive/structural (new modules + re-labeled skills), not gated behind toggleable flags. Classic-phase-gate execution is preserved unchanged (backward compatible).

## Behavior

| Component | Default | Notes |
|-----------|---------|-------|
| `loop_engine.py` loop_state activation | enabled (on invocation) | loop_state activation + stateless round derivation (sacred parallel-safe property — round number derived from artifacts, never from shared mutable counter). Fuse generalization: setup=2 / inner=5 / middle=3 / outer=2. |
| `core/loop-engineering-registry.json` | canonical reference | loop_gate_semantics G1-G11, PausePoints, LoopFuses, back-edges. Classic G1-G11 gates preserved as loop-exit/entry certifications (DEC-098 criterion-4 compatibility). |
| `flow_unit_derive.py` | enabled (on invocation) | Target-derived flow-unit generation — closes VAL-006 (non-game targets now derivable). |
| `loop_migration.py` (--apply/--rollback/--dry-run) | opt-in | Migrate classic-phase-gate → loop-engineering. `--apply` writes SHA-256 backup manifest (hash-verified, collision-safe naming, 5 fail-closed cases, RISK-040 divergence guard). `--rollback` fully restores pre-migration state. |
| `loop_health.py` | mixed | Part 1 (velocity-justification) = BLOCKING; Part 2 (cost-exceedance) = advisory; DORA bridge metrics. `check-loop-health` CLI is advisory-only (NOT blocking Check 28). |
| `loop-rollup` CLI | enabled (on invocation) | Per-flow-unit loop_state view (resolves RISK-037 criterion 2 — no more single global stage). |
| `cmd_dynamic_lifecycle_migration` --apply path | unblocked | Was `sys.exit(1)` placeholder in 0.55.0; now functional via loop_migration. |
| 7 review skills re-labeled | semantic-only | requirement/design/tech/code/test/release/retro-review re-labeled with loop-role semantics (ADR §3.5). No functional behavior change. |

## Backward Compatibility

- Classic-phase-gate execution unchanged (no forced migration).
- Rollback path fully restores pre-migration state (DEC-098 criterion-4).
- Advisory-only checks (check-loop-health) don't block release gate.

## No-overclaim boundaries

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No RISK-037 closure (criteria 2/4/5/6/8 IMPL-MET, but external validation of criteria 5/7/8 still pending — not closed by 0.65.0). No RISK-039 closure. No 1.0.0 readiness. This is a loop-engineering workflow refactor (MINOR): 5 new modules + 3 new CLI commands + semantic re-labeling. Non-breaking to classic-phase-gate execution (backward compatible, migration is opt-in).

<!-- loop-runtime-superseding:{"schema_version":"1.0","notice_id":"LRC-FEATURE-FLAGS-0650","effective_version":"0.66.1","supersedes_claim_ids":["LRC-HIST-FEATURE-FLAGS-001"],"authority_ids":["AUDIT-133","EVD-707","DEC-104"],"classification":{"runtime_activation":"NOT_MET","migration_validity":"NOT_MET","criteria_2_3_4_5_6":"PARTIAL","criterion_7":"NOT_PROVEN","criterion_8":"MET-NARROW","capability":"experimental_scaffolding"},"open_risks":["RISK-037","RISK-042"]} -->

Current interpretation: the 0.65.0 switches expose experimental scaffolding only. They do not activate a persisted Loop runtime or make the migration payload valid.
