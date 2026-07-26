# Feature Flags - 0.69.0

**Version**: 0.69.0 (minor)
**Release**: production telemetry + honest DORA metrics (FEAT-008) + VAL-008 dogfood validation PASS + VAL-009 shitu external validation PASS (first type)
**Date**: 2026-07-26
**Decision**: FEAT-008 + VAL-008 + VAL-009 (REL-061, user authorized)

## Feature Flag Inventory

0.69.0 introduces no runtime feature flag and no kill-switch-controlled rollout. The change adds honest flow/DORA telemetry computed from the 0.68.0 loop event log (`loop_telemetry.py` pure `compute_metrics` + `MetricValue` + `MetricsReport`, with unknown-when-insufficient + anti-proxy), deprecates the legacy `_dora_metrics_legacy_proxy`, and proves the engine through two independent validations (VAL-008 dogfood and VAL-009 shitu first external type). No external product surface is toggled by a flag; the telemetry component is a pure read over the event log and operates under the existing candidate/released lineage model.

| Component | Default | Notes |
| --- | --- | --- |
| Candidate lineage | `--lineage-mode candidate` default | Does not require or prove that a release tag exists. |
| Released lineage | explicit mode | Requires `--release-commit`; verifies local and configured remote tag identity under `HOST_PROJECT_ROOT`. |
| Telemetry `compute_metrics` | pure read | `loop_telemetry.py` computes flow/DORA metrics from the append-only event log; `MetricValue`/`MetricsReport` typed output; unknown-when-insufficient returns explicit `unknown`, anti-proxy does not treat activity/plan as success. |
| Legacy DORA proxy | deprecated advisory | `_dora_metrics_legacy_proxy` retained with a deprecation marker and an advisory `telemetry` key; the new pure `compute_metrics` is the honest path. |
| `cmd_loop_telemetry` CLI | static entry | New CLI surface in `verify_workflow.py` exposes the pure telemetry read; no flag toggles it. |
| Validation proof | dogfood + first external type | VAL-008 dogfood 28 PASS / 0 FAIL / 1 INFO; VAL-009 shitu first external type PASS (second external type pending for RISK-037/042 closure). |
| Release docs boundary tokens | static documentation | Each 0.69.0 release doc includes the five `check-release` `boundary_needles` and uses the compact 0.65.3 negation wording verified to pass `_line_has_scoped_claim_negation` for every scoped claim phrase. |

## Rollout and Kill Switch

There is no runtime product flag to phase or disable. The telemetry read is statically validated and internally exercised (29 new tests covering purity / unknown-when-insufficient / anti-proxy; VAL-008 28 PASS; VAL-009 first external type PASS). Before release, use candidate lineage. After the release commit and `v0.69.0` are created and pushed, use released lineage with the exact commit. A failing released check is the kill switch: stop release completion and correct or roll back the tag/package state; do not weaken the check.

## Test Boundary

- FEAT-008: 29 new telemetry tests pass; honesty contracts purity/unknown-when-insufficient/anti-proxy verified against source.
- VAL-008: 28 PASS / 0 FAIL / 1 INFO (after DEFECT-1/2 fix); 211 loop tests + 2 subtests pass, 0 regression.
- VAL-009: Overall verdict PASS (first external type); two non-blocking defects documented honestly.
- 29 new telemetry tests + VAL-008/009 full-chain validation, 0 P0. The release docs boundary fix is verified directly against the negation function. No full-suite-green claim is made.

## No-overclaim Boundaries

This candidate does not create or prove `v0.69.0`, does not backfill historical tags, and does not close RISK-037 or RISK-042. 0.69.0 does not close RISK-037/RISK-042 (second external type validation pending). VAL-009 proves the first external type; a second external type is still required to fully close RISK-037/042. No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-037/RISK-039/RISK-040/RISK-041/RISK-042 closure, or 1.0.0 production-ready claim is made.
