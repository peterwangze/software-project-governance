# Feature Flags - 0.66.3

**Version**: 0.66.3 (patch)
**Release**: docs-fix PATCH repairing 0.66.2 release docs content defects
**Date**: 2026-07-23
**Decision**: DEC-131 (user decision "0.66.3 PATCH 修复 docs")

## Feature Flag Inventory

0.66.3 introduces no runtime feature flag and no kill-switch-controlled rollout. The change is a release docs content fix (boundary wording repair) plus documentation and version metadata. No runtime behavior, default, or migration is changed.

| Component | Default | Notes |
| --- | --- | --- |
| Candidate lineage | `--lineage-mode candidate` default | Does not require or prove that a release tag exists. |
| Released lineage | explicit mode | Requires `--release-commit`; verifies local and configured remote tag identity under `HOST_PROJECT_ROOT`. |
| Release docs boundary tokens | static documentation | Each 0.66.3 release doc includes the five `check-release` `boundary_needles` and uses the compact 0.65.3 negation wording verified to pass `_line_has_scoped_claim_negation` for every scoped claim phrase. |

## Rollout and Kill Switch

There is no runtime activation to phase or disable. Before release, use candidate lineage. After the release commit and `v0.66.3` are created and pushed, use released lineage with the exact commit. A failing released check is the kill switch: stop release completion and correct or roll back the tag/package state; do not weaken the check.

## Test Boundary

The release docs boundary fix is verified directly against the negation function. No full-suite-green claim is made.

## No-overclaim Boundaries

This candidate does not create or prove `v0.66.3`, does not backfill historical tags, and does not close RISK-039 or RISK-041. No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-037/RISK-040 closure, or 1.0.0 production-ready claim is made.
