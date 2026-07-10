# Release Checklist - 0.65.0

**Version**: 0.65.0 (minor)
**Release**: Loop-Engineering Workflow Refactor — three-tier nested loop model + AI Plan-Act-Observe-Reflect first-class citizen (DEC-097/098/099, FX-188~FX-194, RISK-037 progress)
**Date**: 2026-07-10

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined (semver) | ✅ 0.65.0 (minor: loop-engineering workflow refactor, 5 new modules + 3 new CLI commands + semantic re-labeling) |
| 2 | Change list enumerated | ✅ FX-188~FX-194 (7 implementation slices) + 3 new CLI commands + 7 review-skill re-labels |
| 3 | Change types marked | ✅ New feature (loop_engine/flow_unit_derive/loop_migration/loop_health/registry) / Refactor (gate-as-loop-exit relabel) / Semantic (review-skill loop-role) |
| 4 | Release window | ✅ 2026-07-10 |

### Change inventory

- **FX-188** — `core/loop-engineering-registry.json`: loop_gate_semantics G1-G11, PausePoints, LoopFuses, back-edges. Classic gates preserved as loop-exit/entry certifications (DEC-098 criterion-4).
- **FX-189 / FX-193** — `infra/loop_engine.py` extensions: loop_state activation, stateless round derivation (sacred parallel-safe property — round derived from artifacts not shared counter), fuse generalization (setup=2/inner=5/middle=3/outer=2), per-flow-unit rollup view.
- **FX-190** — `infra/flow_unit_derive.py`: target-derived flow-unit generation, closes VAL-006 gap (non-game targets now derivable).
- **FX-191** — `infra/loop_migration.py`: `--apply` + `--rollback` with SHA-256 backup, manifest-verified hash integrity, collision-safe naming, 5 fail-closed cases, RISK-040 divergence guard.
- **FX-192** — `infra/loop_health.py`: velocity-justification enforcement (Part 1 BLOCKING) + cost-exceedance advisory (Part 2) + DORA bridge metrics.
- **FX-194** — gate-as-loop-exit relabel: 7 review skills (requirement/design/tech/code/test/release/retro-review) re-labeled with loop-role semantics (ADR §3.5). `cmd_dynamic_lifecycle_migration` --apply path unblocked (was sys.exit(1) in 0.55.0).
- **Version bump**: 0.64.1→0.65.0 (13 declaration files + e2e fixture SKILL.md + e2e plan-tracker.md version pointer).
- **New CLI commands**: `loop-engineering-migration`, `check-loop-health` (advisory-only, not blocking Check 28), `loop-rollup`.

## 2-6. (Standard checks — see release-checklist-0.64.0 template for full criteria)

## 7. Release Gate Evidence

```
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
→ Result: PASSED (13 files, all 0.65.0)
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync — PASS
python skills/software-project-governance/infra/verify_workflow.py check-archive-integrity — PASS
```

Review evidence: FX-188~FX-194 each with independent Code Review R0 (7 slices). Test suite: 827 infra tests + 82 subtests passing. Sacred property tests: stateless round derivation parallel-safety proven. VAL-006 closure test: cli-tool 3 commands → 3 units (3 fixture forms). Data integrity: manifest-verified backup, tamper detection, rollback totality. 降级 SoD (DEC-090/091) — Coordinator spawn Release Agent + independent Release Reviewer R0.

### RISK-037 Progress (1.0.0 hard blocker)

- Criterion 2 (plan-tracker rollup): IMPL-MET (FX-193)
- Criterion 4 (gate engine classic compat): IMPL-MET (FX-188 + FX-194)
- Criterion 5 (loop runtime activation): IMPL-MET (FX-189)
- Criterion 6 (apply path): IMPL-MET (FX-191)
- Criterion 8 (non-game generalization): IMPL-MET (FX-190)
- Criteria 5/7/8 external validation: still pending (NOT closed by 0.65.0)

### Boundaries (no-overclaim)

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS. No external first-session pilot success. No RISK-036 closure. No RISK-037 closure (IMPL-MET criteria progress, external validation pending). No RISK-039 closure. No 1.0.0 readiness. This is a MINOR loop-engineering workflow refactor: 5 new modules + 3 new CLI commands + semantic re-labeling. Non-breaking to classic-phase-gate execution (backward compatible, migration is opt-in).
