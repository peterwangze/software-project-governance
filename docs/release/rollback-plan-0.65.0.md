# Rollback Plan - 0.65.0

**Version**: 0.65.0 (minor)
**Release**: Loop-Engineering Workflow Refactor — three-tier nested loop model + AI Plan-Act-Observe-Reflect first-class citizen (DEC-097/098/099, FX-188~FX-194, RISK-037 progress)
**Date**: 2026-07-10

## Rollback Triggers

| Trigger | Severity | Detection | Action |
|---------|----------|-----------|--------|
| Loop-engineering migration (--apply) corrupts project state | Critical | `loop_migration.py --apply` writes partial/inconsistent artifacts; SHA-256 manifest mismatch | Run `loop_migration.py --rollback` (restores pre-migration state from hash-verified backup); if rollback fails, manual restore from backup manifest |
| loop_engine stateless round derivation breaks (parallel-safety regression) | Critical | Sacred property test fails under concurrent invocation; round numbers diverge | Immediate rollback to 0.64.1; re-open FX-189 round-derivation invariant |
| loop_health Part 1 (BLOCKING velocity-justification) false-positives blocks valid flow | High | Valid flow unit blocked by velocity check incorrectly | Rollback to 0.64.1; fix Part 1 threshold logic (advisory-only path is not blocking) |
| Classic-phase-gate execution regresses (loop re-label breaks G1-G11 path) | High | Classic gate workflow fails where 0.64.1 worked (DEC-098 criterion-4 broken) | Rollback to 0.64.1; re-verify loop_gate_semantics preserves classic compat |
| check-loop-health advisory mistakenly blocks release gate (Check 28) | Medium | Release gate blocked by advisory check that should be non-blocking | Confirm advisory-only wiring; advisory checks must not block release gate |
| Version inconsistency (0.65.0 not propagated) | Low | check-version-consistency FAIL | Re-run version bump on missed file |

## Rollback Steps

### Full rollback to 0.64.1
1. `git revert <0.65.0-release-commit>` (reverts loop-engineering modules + re-labels + version bump)
2. For any project that ran `loop-engineering-migration --apply`: run `loop_migration.py --rollback` against the backup manifest to fully restore pre-migration state (DEC-098 criterion-4 — rollback path restores totality)
3. Re-bump version 0.65.0 → 0.64.1 across 13 declaration files + e2e fixture pointers
4. Re-push to origin
5. Record rollback decision in decision-log; re-open affected RISK-037 criteria if regression found

### Partial rollback (keep new modules, disable migration apply path)
If the new modules (loop_engine/flow_unit_derive/loop_health/registry) are sound but `loop_migration.py --apply` causes issues:
1. Revert FX-191 (loop_migration) — restore `cmd_dynamic_lifecycle_migration` --apply path to `sys.exit(1)` placeholder (0.55.0 behavior)
2. Keep loop_engine / flow_unit_derive / loop_health / registry available as opt-in tools (additive, non-invasive)
3. Classic-phase-gate execution unaffected (no migration applied)

### Partial rollback (revert review-skill re-label only, FX-194)
If the 7 review-skill re-labels cause confusion without functional regression:
1. Revert FX-194 semantic relabel — restore classic review-skill descriptions
2. Keep loop-engineering modules intact

## Reversibility

| Component | Reversible? | Method |
|-----------|-------------|--------|
| loop_migration --apply (FX-191) | ✅ Yes | `loop_migration.py --rollback` — SHA-256 manifest-verified, fully restores pre-migration state (5 fail-closed cases + RISK-040 divergence guard) |
| loop_engine.py extensions (FX-189/193) | ✅ Yes | `git revert` — additive extensions, removing restores 0.64.1 behavior |
| flow_unit_derive.py (FX-190) | ✅ Yes | `git revert` — new file, removal restores 0.64.1 |
| loop_health.py (FX-192) | ✅ Yes | `git revert` — new file; advisory-only wiring means no gate dependency |
| loop-engineering-registry.json (FX-188) | ✅ Yes | `git revert` — new canonical reference, removal restores 0.64.1 |
| review-skill re-labels (FX-194) | ✅ Yes | `git revert` — semantic-only, no functional dependency |
| Version bump (0.65.0→0.64.1) | ✅ Yes | Re-edit 13 declaration files + e2e fixture pointers (mechanical) |

### No-overclaim boundaries

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036/037/039 closure (RISK-037 IMPL-MET progress, external validation pending). No 1.0.0 readiness. Rollback plan covers the regression scenarios specific to this release (migration corruption / parallel-safety regression / classic-compat break). Loop-engineering modules are additive (opt-in migration), so rollback is low-risk — classic-phase-gate execution is never forced to migrate. The `loop_migration.py --rollback` path is the primary safety mechanism (DEC-098 criterion-4: rollback restores totality, hash-verified).
