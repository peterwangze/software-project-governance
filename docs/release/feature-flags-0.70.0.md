# Feature Flags - 0.70.0

**Version**: 0.70.0 (minor)
**Release**: verify_workflow Phase 5 extraction (FEAT-009) — evidence/risk/review domains extracted to checks/{evidence,risk,review}_domain.py
**Date**: 2026-07-26
**Decision**: FEAT-009 (REL-062, user authorized)

## Feature Flag Inventory

0.70.0 introduces no runtime feature flag and no kill-switch-controlled rollout. The change extracts the evidence/risk/review check domains out of `verify_workflow.py` into `checks/evidence_domain.py` (402 lines, Check 1/1b/6/6b), `checks/risk_domain.py` (212 lines, Check 2/8), and `checks/review_domain.py` (2127 lines, Check 18/18b/21/21b/22/29/30); `verify_workflow.py` drops from 22468 to 20183 lines (-2285 net, real extraction per DEC-088 — function bodies moved, not re-export disguised). Only thin re-export entry points plus the `sys.modules["verify_workflow"] = sys.modules["__main__"]` aliasing guard remain, consistent with the Phase 1 (manifest) / Phase 2 (capability_registry) precedent. No external product surface is toggled by a flag; the extraction is behavior-preserving and operates under the existing candidate/released lineage model.

| Component | Default | Notes |
| --- | --- | --- |
| Candidate lineage | `--lineage-mode candidate` default | Does not require or prove that a release tag exists. |
| Released lineage | explicit mode | Requires `--release-commit`; verifies local and configured remote tag identity under `HOST_PROJECT_ROOT`. |
| Domain extraction (evidence/risk/review) | static module split | `checks/{evidence,risk,review}_domain.py` host the moved check functions; `verify_workflow.py` keeps thin re-exports and the `sys.modules` aliasing guard; no flag toggles it. |
| KEEP rule + deferred `_vw()` | static pattern | Re-export entry points preserve existing call sites unchanged; the deferred `_vw()` resolver binds the active module at call time. |
| Behavioral equivalence | byte-diff verified | `check-governance` final Result line byte-identical pre/post extraction (134 issues both sides); 626 tests + 82 subtests identical, zero regression. |
| Release docs boundary tokens | static documentation | Each 0.70.0 release doc includes the five `check-release` `boundary_needles` and uses the compact negation wording verified to pass `_line_has_scoped_claim_negation` for every scoped claim phrase. |

## Rollout and Kill Switch

There is no runtime product flag to phase or disable. The extraction is statically validated and internally exercised (626 tests + 82 subtests pass before and after; `check-governance` output byte-identical). Before release, use candidate lineage. After the release commit and `v0.70.0` are created and pushed, use released lineage with the exact commit. A failing released check is the kill switch: stop release completion and correct or roll back the tag/package state; do not weaken the check.

## Test Boundary

- FEAT-009: 626 tests + 82 subtests pass before and after extraction (zero regression); real extraction CONFIRMED (function bodies moved, not re-export disguised); behavioral equivalence verified by byte-diffing `check-governance` output (134 issues identical both sides).
- ADR-016 design Design Review: APPROVED_WITH_NOTES / 0.
- 626 tests + 82 subtests, 0 P0. The release docs boundary fix is verified directly against the negation function. No full-suite-green claim is made.

## No-overclaim Boundaries

This candidate does not create or prove `v0.70.0`, does not backfill historical tags, and does not close RISK-036, RISK-039, RISK-040, or RISK-041. 0.70.0 does not close RISK-036/RISK-039/RISK-040/RISK-041 (official marketplace operations, ArchGuard external validation, entry determinism host validation, and release-lineage historical-tag disposition each have independent closure criteria not yet satisfied). No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039/RISK-040/RISK-041 closure, or 1.0.0 production-ready claim is made.
