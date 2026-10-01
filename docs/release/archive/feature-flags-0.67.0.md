# Feature Flags - 0.67.0

**Version**: 0.67.0 (minor)
**Release**: canonical Loop Runtime Contract + shared migration planner + decomposition confirmation
**Date**: 2026-07-23
**Decision**: DEC-104 + FEAT-002~004 + REL-059 (user decision "继续")

## Feature Flag Inventory

0.67.0 introduces no runtime feature flag and no kill-switch-controlled rollout. The change adds a canonical versioned Loop Runtime Contract (v2 schema + byte-frozen v1 containment), a pure shared migration planner with an immutable `plan_hash`, and decomposition confirmation producing canonical initial gate state. No runtime execution is activated; the units remain dormant.

| Component | Default | Notes |
| --- | --- | --- |
| Candidate lineage | `--lineage-mode candidate` default | Does not require or prove that a release tag exists. |
| Released lineage | explicit mode | Requires `--release-commit`; verifies local and configured remote tag identity under `HOST_PROJECT_ROOT`. |
| Loop Runtime Contract schema | v2 canonical | `flow_unit_runtime_v2.py` validator; v1 byte-frozen containment boundary (FIX-195 intact) with version routing. |
| Migration plan identity | immutable `plan_hash` | `build_migration_plan()` is a pure function; dry-run and apply serialize the same plan; apply only validates and executes that plan. |
| Decomposition confirmation | advisory heuristic | `confirm_decomposition` requires operator confirmation before activation; dormant/example-data-only cannot masquerade as active. |
| Execution engine | NOT activated in 0.67.0 | Runtime execution engine is scheduled for 0.68.0; units remain dormant. |
| Release docs boundary tokens | static documentation | Each 0.67.0 release doc includes the five `check-release` `boundary_needles` and uses the compact 0.65.3 negation wording verified to pass `_line_has_scoped_claim_negation` for every scoped claim phrase. |

## Rollout and Kill Switch

There is no runtime activation to phase or disable. The contract/planner/decomposition confirmation are statically validated and dormant until the execution engine lands in 0.68.0. Before release, use candidate lineage. After the release commit and `v0.67.0` are created and pushed, use released lineage with the exact commit. A failing released check is the kill switch: stop release completion and correct or roll back the tag/package state; do not weaken the check.

## Test Boundary

- FEAT-002: 40 tests pass; v1/v2 drift parity 9/9 match, no regression.
- FEAT-003: 28+68 regression pass; purity 16-thread CONFIRMED; preview/apply plan hash identical; validator PASS before and after apply.
- FEAT-004: 36+96 regression pass; dormant-as-active is unrepresentable.
- 104 new tests total, 0 P0. The release docs boundary fix is verified directly against the negation function. No full-suite-green claim is made.

## No-overclaim Boundaries

This candidate does not create or prove `v0.67.0`, does not backfill historical tags, and does not close RISK-037 or RISK-042. 0.67.0 does not activate execution engine; RISK-037 remains open; RISK-042 remains open. No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-037/RISK-039/RISK-040/RISK-041/RISK-042 closure, or 1.0.0 production-ready claim is made.
