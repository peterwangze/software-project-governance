# Release Checklist - 0.69.0

**Version**: 0.69.0 (minor)
**Release**: production telemetry + honest DORA metrics (FEAT-008) + VAL-008 dogfood validation PASS + VAL-009 shitu external validation PASS (first type)
**Date**: 2026-07-26
**Decision**: FEAT-008 + VAL-008 + VAL-009 (REL-061, user authorized)
**Candidate parent (B)**: `9136330` (VAL-008 defect fix, on top of FEAT-008 `aa6e76a` and ADR commits `5540258`)

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined | PASS - 0.69.0 MINOR; production telemetry (FEAT-008 honest flow/DORA metrics from the loop event log), VAL-008 dogfood validation PASS (28 tests), VAL-009 shitu external validation PASS (first type); no breaking runtime API |
| 2 | Change list enumerated | PASS - FEAT-008 telemetry code commit + VAL-008 defect fix + version projection 0.68.0 -> 0.69.0 + CHANGELOG + candidate manifest |
| 3 | Independent code review available | PASS - FEAT-008 APPROVED_WITH_NOTES/0 blocker; ADR-015 design APPROVED_WITH_NOTES/0; 29 new telemetry tests, 0 P0; VAL-008 28 PASS / 0 FAIL / 1 INFO; VAL-009 PASS (first external type) |
| 4 | Candidate lineage boundary explicit | PASS - candidate mode does not require or prove a tag |
| 5 | Historical tag and official-marketplace overclaims excluded | PASS |

### Included

- FEAT-008: production telemetry + honest DORA metrics — `loop_telemetry.py` pure `compute_metrics` (flow lead time / DORA deployment frequency / lead time / change fail / MTTR / fuse trips) + `MetricValue` + `MetricsReport`; unknown-when-insufficient + anti-proxy (no activity/plan treated as success). `loop_health.py` `_compute_dora_metrics` -> `_dora_metrics_legacy_proxy` (deprecated) + advisory `telemetry` key; `verify_workflow.py` +`cmd_loop_telemetry` CLI. 29 new tests, purity/unknown-when-insufficient/anti-proxy verified against source.
- VAL-008: dogfood validation PASS — `val008_dogfood_driver.py` drives 3 units (middle + 2 inner, dependency chain) through plan -> activate -> forward PARO -> gate-fail back-edges -> fuse trip -> system block -> restart recovery -> telemetry -> rollback in an isolated `tempfile.TemporaryDirectory`. DEFECT-1 (gate event envelope now carries all REQUIRED_FIELDS) + DEFECT-2 (fuse_trip payload carries persisted loop_count) fixed. **28 PASS / 0 FAIL / 1 INFO** (was 26 PASS / 2 FAIL). 211 loop tests + 2 subtests pass, 0 regression.
- VAL-009: shitu external validation PASS (first type) — real external project shitu (Android/Kotlin mobile-app, HEAD `c037a04`) executes `build_migration_plan(shitu,"mobile-app")` + `confirm_decomposition` + `plan_to_payload` (v2 validator PASS) + real flow-unit derivation (mobile-app PASS) + native entry resolve + preview/apply plan_hash identity (REL-059/REL-060) + `activate_unit`/`apply_transition` CAS write-back (post-transition v2 validator PASS) + v1/classic-gate rollback. Overall verdict **PASS** (two non-blocking defects documented honestly: shitu pre-existing VAL-007 @0.65.0 artifact fails v1/v2 validator — external legacy debt, not an engine defect).
- Version declarations and e2e fixture pointers advance from 0.68.0 to 0.69.0 (M-set: plugins, marketplace, package.json, source/e2e SKILL frontmatter, manifest, plan-tracker, four source hooks, and the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`).
- `project/CHANGELOG.md` gains a 0.69.0 entry.

### Excluded

- No zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-037/RISK-039/RISK-040/RISK-041/RISK-042 closure, or 1.0.0 production-ready claim.
- 0.69.0 does not close RISK-037/RISK-042 (second external type validation pending). VAL-009 proves the first external type; a second external type is still required to fully close RISK-037/042.

## 2. Version and SemVer

0.69.0 is a MINOR because it adds production telemetry capability (honest flow/DORA metrics from the loop event log) and validation proof (dogfood PASS + first external type PASS) without changing existing plugin runtime APIs or introducing a breaking contract. Expected declarations are 0.69.0 in source SKILL, manifest, Claude/Codex/Zcode/Chrys plugin metadata, Claude marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, and the two e2e fixture pointers.

## 3. Candidate Validation

Run before release review:

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.69.0 --require-changelog --lineage-mode candidate
```

Candidate mode intentionally does not require `v0.69.0` and is not evidence that the tag exists. The final release commit, local tag, and remote tag do not yet exist during package preparation. After the Coordinator creates and pushes them, rerun:

```text
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.69.0 --require-changelog --lineage-mode released --release-commit <commit> --skip-execution-gates
```

## 4. Test and Review Evidence

- FEAT-008 Code Review: APPROVED_WITH_NOTES, 0 blocker (honesty contracts purity/unknown-when-insufficient/anti-proxy independently verified against source); 29 new telemetry tests pass.
- VAL-008 dogfood: 28 PASS / 0 FAIL / 1 INFO (after DEFECT-1/2 fix); 211 loop tests + 2 subtests pass, 0 regression.
- VAL-009 shitu: Overall verdict PASS (first external type); preview/apply plan_hash identity, v2 validator, real flow-unit derivation, CAS write-back all PASS; two non-blocking defects documented.
- 29 new telemetry tests + VAL-008/009 full-chain validation, 0 P0.
- The release docs boundary wording is verified against `_line_has_scoped_claim_negation` and the `check_release_docs_coverage` `boundary_needles`: every forbidden-positive-claim phrase returns True (negated), and the `RISK-036` token is present in each of the three 0.69.0 release docs.
- This package does not claim a full-suite-green state. Any pre-existing gate FAIL unrelated to 0.69.0 (e.g. the loop runtime claim gate, RISK-037/042) is reported honestly and is out of scope for this MINOR.

## 5. Release Decision Boundary

This checklist prepares a candidate only. It does not commit, tag, push, approve marketplace submission, close risk, or make the final go/no-go decision. After tag creation and push, released lineage must verify the exact release commit locally and on the configured remote.

## 6. Rollback Verification

`docs/release/rollback-plan-0.69.0.md` defines full and partial rollback paths. After rollback, rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.
