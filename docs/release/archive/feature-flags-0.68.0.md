# Feature Flags - 0.68.0

**Version**: 0.68.0 (minor)
**Release**: executable Loop Engine — persistent PARO state machine + production gate back-edge/fuse/escalation + restart-safe event log
**Date**: 2026-07-23
**Decision**: FEAT-005~007 + REL-060 (user decision "继续")

## Feature Flag Inventory

0.68.0 introduces no runtime feature flag and no kill-switch-controlled rollout. The change adds an executable Loop Engine: a persistent PARO state machine with CAS write-back, a production gate processor with back-edge/fuse/escalation and a system-level fuse block, and a restart-safe append-only event log with cross-process locking plus dependency blocking and a WIP budget. No external product surface is toggled by a flag; the engine components are statically validated and operate under the existing candidate/released lineage model.

| Component | Default | Notes |
| --- | --- | --- |
| Candidate lineage | `--lineage-mode candidate` default | Does not require or prove that a release tag exists. |
| Released lineage | explicit mode | Requires `--release-commit`; verifies local and configured remote tag identity under `HOST_PROJECT_ROOT`. |
| PARO state machine | CAS write-back | `apply_transition` writes a legal transition (6 legal + 3 terminal) with compare-and-swap; `recover_state` rebuilds from persisted state; fuse boundary triggers past `max_rounds`. |
| Production gate fuse | system-level block | `process_gate_result` drives gate fail→back-edge→round→fuse→escalation; `check_release_readiness` fuse check is a system-level block, not a Coordinator advisory; `loop_fuse_check` is a pure read. |
| Restart-safe event log | append-only JSONL | 14 event types, cross-process lock, monotonicity/legality checks; `loop_admission` dependency blocking + WIP budget (setup=1/inner=5/middle=2/outer=1). |
| Execution engine | activated in 0.68.0 | Engine activates, but runtime completeness still requires 0.69.0 dogfood + external validation. |
| Release docs boundary tokens | static documentation | Each 0.68.0 release doc includes the five `check-release` `boundary_needles` and uses the compact 0.65.3 negation wording verified to pass `_line_has_scoped_claim_negation` for every scoped claim phrase. |

## Rollout and Kill Switch

There is no runtime product flag to phase or disable. The state machine / gate fuse / event log are statically validated and internally exercised (CAS 12-thread 1-success/11-conflict 60x stable; end-to-end gate fail→back-edge→round→fuse→escalation→block; multi-process 4×100=400 0 loss win32). Before release, use candidate lineage. After the release commit and `v0.68.0` are created and pushed, use released lineage with the exact commit. A failing released check is the kill switch: stop release completion and correct or roll back the tag/package state; do not weaken the check.

## Test Boundary

- FEAT-005: 61 new + 104 regression pass; CAS threading 12-thread 1-success/11-conflict 60x stable; fuse boundary >max_rounds.
- FEAT-006: 45 new + 101 regression pass; `loop_fuse_check` pure read CONFIRMED; end-to-end gate fail→back-edge→round→fuse→escalation→block.
- FEAT-007: 53 new + 146 regression pass; multi-process 4×100=400 0 loss win32; restart consistency CONFIRMED.
- 159 new tests total, 0 P0. The release docs boundary fix is verified directly against the negation function. No full-suite-green claim is made.

## No-overclaim Boundaries

This candidate does not create or prove `v0.68.0`, does not backfill historical tags, and does not close RISK-037 or RISK-042. 0.68.0 does not close RISK-037/RISK-042 (external validation 0.69.0). Execution engine activates but runtime completeness requires 0.69.0 dogfood + external validation. No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-037/RISK-039/RISK-040/RISK-041/RISK-042 closure, or 1.0.0 production-ready claim is made.
