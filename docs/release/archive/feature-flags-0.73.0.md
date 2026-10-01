# Feature Flags - 0.73.0

**Version**: 0.73.0 (minor)
**Release**: 三链重构（入口/循环/任务规划）生产接线打包（AUDIT-142 / FIX-236 / FIX-237 / FIX-238 / FIX-239 / FIX-240 / FIX-241 / FIX-233~235）
**Date**: 2026-08-03
**Decision**: REL-066 (user authorized release direction on 2026-08-03)

## Feature Flag Inventory

0.73.0 introduces no runtime feature flag and no kill-switch-controlled rollout. The release packages thirteen already-merged commits: AUDIT-142 three-chain diagnosis + ADR-017, FIX-236 loop production wiring (review-record CLI, loop_exit_bridge next-candidates bridge, Check 30 V6, call-site AST check), FIX-237 task-planning de-cycling + change-triage CLI + Check 32 (mandatory four-step triage analysis with machine records, fail-closed no-record interception), FIX-238 entry bootstrap repair (vendor bootstrap scripts, resolve timeout fallback, web-console install timeout, @bootstrap-version upgrade chain), FIX-239 hook locale hardening, FIX-240 CI pipeline repair, FIX-241 resolve_entry encoding robustness regression tests, FIX-233/234/235 debt package (Check 30 historical exemptions + release gate timeout + archive evidence migration), and FIX-232 evidence-log column structure repair (governance record). No external product surface is toggled by a flag; the changes are static verifier logic, governance-record wiring, deterministic bootstrap tooling, and release-lineage additions operating under the existing candidate/released lineage model.

| Component | Default | Notes |
| --- | --- | --- |
| Candidate lineage | `--lineage-mode candidate` default | Does not require or prove that a release tag exists. |
| Released lineage | explicit mode | Requires `--release-commit`; verifies local and configured remote tag identity under `HOST_PROJECT_ROOT`. |
| Loop wiring (FIX-236) | static verifier + CLI | review-record/next-candidates operate on review evidence records; no flag toggles them. |
| Change triage (FIX-237) | mandatory CLI + Check 32 | Product-code tasks with earliest evidence on/after `TRIAGE_NORMALIZATION_DATE` (2026-08-03) must carry a machine triage record; no flag toggles it. |
| Bootstrap timeout fallback (FIX-238) | env-driven | `SPG_RESOLVE_TIMEOUT` (15s default) / `SPG_WEB_INSTALL_TIMEOUT` (120s default); env vars tune timeouts, not feature toggles. |
| Hook locale hardening (FIX-239) | static | `LC_ALL=C` in review-evidence grep/sed; no flag toggles it. |
| Release docs boundary tokens | static documentation | Each 0.73.0 release doc includes the five `check-release` `boundary_needles` and the compact negation wording verified to pass `_line_has_scoped_claim_negation` for every scoped claim phrase. |

## Rollout and Kill Switch

There is no runtime product flag to phase or disable. The changes are statically validated (FIX-236 36+R1 8 new tests; FIX-237 33 new tests; FIX-238 29 new tests, test_verify_workflow 688 OK; check-version-consistency 13 files PASS; check-projection-sync 13 projections PASS) and internally exercised. Before release, use candidate lineage. After the release commit and `v0.73.0` are created and pushed, use released lineage with the exact commit. A failing released check is the kill switch: stop release completion and correct or roll back the tag/package state; do not weaken the check.

## Test Boundary

- FIX-236: 36 new tests + R1 8 new tests covering record/reopen/close, bridge fuse corrupt fail-closed, Check 30 V6, and call-site wiring.
- FIX-237: 33 new tests for change-triage CLI four-step analysis, record validation, Check 32 fail-closed; task-priority 0-cycle state.
- FIX-238: 29 new tests for bootstrap script exit-code contract, timeout fallback, and upgrade chain.
- FIX-240: CI full-suite 1527 tests unique failure eliminated (threading-determinism Linux fix).
- FIX-241: resolve_entry encoding regression tests (external cp936 claim verified false).
- check-version-consistency PASS (13 files); check-projection-sync PASS (13 projections). The release docs boundary wording is verified directly against the negation function. No full-suite-green claim is made.

## No-overclaim Boundaries

This candidate does not create or prove `v0.73.0` and does not close RISK-036 or RISK-039. 0.73.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
