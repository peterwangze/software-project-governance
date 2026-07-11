# Feature Flags - 0.65.3

**Version**: 0.65.3 (patch)
**Release**: release lineage/tag gate and marketplace source facts (FIX-192)
**Date**: 2026-07-11

## Feature Flag Inventory

0.65.3 introduces no runtime feature flag and no kill-switch-controlled rollout. The change is a release-verification command boundary plus documentation and version metadata. Candidate versus released lineage is an explicit CLI mode, not a hidden rollout flag.

| Component | Default | Notes |
| --- | --- | --- |
| Candidate lineage | `--lineage-mode candidate` default | Does not require or prove that a release tag exists. |
| Released lineage | explicit mode | Requires `--release-commit`; verifies local and configured remote tag identity under `HOST_PROJECT_ROOT`. |
| Remote selection | `origin` | Alternate input must be a safe configured remote name; URL/userinfo/option-like/unknown input fails closed. |
| Git remote query | non-interactive, 15-second timeout | Uses `GIT_TERMINAL_PROMPT=0`; credential-bearing input is rejected and not echoed in diagnostics. |
| Marketplace source | `source: "./"` | Supports local/offline and remote marketplace clone/add flows; direct git URL install remains unsupported by the current 0.64.1+ contract. |

## Rollout and Kill Switch

There is no runtime activation to phase or disable. Before release, use candidate lineage. After the release commit and `v0.65.3` are created and pushed, use released lineage with the exact commit. A failing released check is the kill switch: stop release completion and correct or roll back the tag/package state; do not weaken the check.

## Test Boundary

FIX-192 focused validation is 53/53 PASS. The full unit suite is 609/610 because of one existing Check 13 fixture isolation failure; no full-suite green claim is made.

## No-overclaim Boundaries

This candidate does not create or prove `v0.65.3`, does not backfill historical tags, and does not close RISK-039 or RISK-041. No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-037/RISK-040 closure, or 1.0.0 production-ready claim is made.
