# Feature Flags - 0.72.0

**Version**: 0.72.0 (minor)
**Release**: Check 31 安装态消解打包 + release lineage 多版本授权 + 0.64.x docs 债务（FIX-200 / FIX-230 / AUDIT-140 / FIX-231）
**Date**: 2026-08-01
**Decision**: REL-065 (user authorized)

## Feature Flag Inventory

0.72.0 introduces no runtime feature flag and no kill-switch-controlled rollout. The release packages four already-merged commits: FIX-200 identity attestation gate (`_loop_runtime_claim_gate_detail` runs the real `build_identity_attestation`, eliminating `IDENTITY_ATTESTATION_PENDING` from Check 31 and producing identity_verdict=PASS), FIX-230 release-ledger multi-version tag authorization resolver (matches `(decision_id, version, commit)` triples; 8 historical manifests backfilled per DEC-136), AUDIT-140 claim-scanner-safe audit report wording (Check 31 repo-side unblock), and FIX-231 0.64.x release docs boundary tokens (DOC-001 gap closure). No external product surface is toggled by a flag; the changes are governance-record wording, static verifier logic, and release-lineage authorization additions operating under the existing candidate/released lineage model.

| Component | Default | Notes |
| --- | --- | --- |
| Candidate lineage | `--lineage-mode candidate` default | Does not require or prove that a release tag exists. |
| Released lineage | explicit mode | Requires `--release-commit`; verifies local and configured remote tag identity under `HOST_PROJECT_ROOT`. |
| Identity attestation gate (FIX-200) | static verifier | Check 31 runs the real `build_identity_attestation`; identity_verdict=PASS in repo state; no flag toggles it. |
| Release-ledger tag authorization (FIX-230) | static resolver | `ledger.py` matches `(decision_id, version, commit)`; 8 historical manifests carry `tag_decision=DEC-136`; no flag toggles it. |
| Audit report claim wording (AUDIT-140) | static documentation | Claim-scanner-safe wording in `docs/requirements/audit-140-*.md`; no flag toggles it. |
| 0.64.x release docs tokens (FIX-231) | static documentation | Boundary tokens added to the three 0.64.x release docs; no flag toggles it. |
| Release docs boundary tokens | static documentation | Each 0.72.0 release doc includes the five `check-release` `boundary_needles` and the compact negation wording verified to pass `_line_has_scoped_claim_negation` for every scoped claim phrase. |

## Rollout and Kill Switch

There is no runtime product flag to phase or disable. The changes are statically validated (FIX-200 identity verdict tests PASS; FIX-230 resolver 39 tests 38 PASS + 1 pre-existing 0.66.2 FAIL, 2 new tests +67 lines; check-version-consistency 13 files PASS; check-projection-sync 13 projections PASS) and internally exercised. Before release, use candidate lineage. After the release commit and `v0.72.0` are created and pushed, use released lineage with the exact commit. A failing released check is the kill switch: stop release completion and correct or roll back the tag/package state; do not weaken the check.

## Test Boundary

- FIX-200: identity attestation gate tests cover real verdict PASS and FAIL paths; Check 31 identity_verdict=PASS.
- FIX-230: ledger resolver TDD + 2 new tests (+67 lines; 39 tests 38 PASS + 1 pre-existing 0.66.2 FAIL); 8 historical manifests verified (DEC-136 / EVD-859).
- AUDIT-140: repo-side Check 31 unblock verified (EVD-858); FIX-231: DOC-001 gap closure verified (EVD-863).
- check-version-consistency PASS (13 files); check-projection-sync PASS (13 projections). The release docs boundary wording is verified directly against the negation function. No full-suite-green claim is made.

## No-overclaim Boundaries

This candidate does not create or prove `v0.72.0`, does not backfill historical tags, and does not close RISK-036 or RISK-039. 0.72.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
