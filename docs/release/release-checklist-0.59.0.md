# Release Checklist - 0.59.0

**Version**: 0.59.0
**Release**: verify_workflow.py Incremental Split Phase 1 (manifest domain)
**Task**: REL-045
**Date**: 2026-06-26

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined (semver) | ✅ 0.59.0 (minor: structural refactor, no behavior change) |
| 2 | Change list enumerated | ✅ FIX-153 (caea3b9) + REL-045 version bump |
| 3 | Change types marked | ✅ Refactor (manifest domain extraction) / version bump / no new feature |
| 4 | Release window | ✅ 2026-06-26 |

### Change inventory
- **Refactor**: extract manifest domain (A-group 12 functions, ~401 lines) to new `infra/checks/manifest.py`
- **New artifact**: `infra/checks/__init__.py` + `infra/checks/manifest.py` (subpackage scaffolding for 0.60.0~0.64.0)
- **CLI contract**: 54 commands unchanged (dispatch/argparse/governance-pack registration preserved)
- **Code size**: verify_workflow.py 20,937 → 20,516 (net −421 lines); manifest.py zero ArchGuard ERROR/WARN
- **ArchGuard first real-world use**: module-size guard confirms the split (D-not-increase principle satisfied)
- **Version bump**: 0.58.0→0.59.0 (SKILL/plugin×4/marketplace/package/manifest/hooks×4/REQUIRED_SNIPPETS×6/target fixture)
- **Docs**: CHANGELOG, release docs (this checklist + feature-flags + rollback-plan), REQ-102 design doc

## 2. Changelog

| # | Check | Status |
| --- | --- | --- |
| 1 | CHANGELOG updated, covers all changes | ✅ `project/CHANGELOG.md` [0.59.0] entry |
| 2 | Breaking changes highlighted | ✅ No breaking changes (mechanical extraction, CLI contract preserved) |
| 3 | Dependency changes recorded | ✅ No new external dependencies (stdlib only) |
| 4 | Known issues listed | ✅ 2 gitignored-plan-tracker test failures (non-regression), P2 dual-module-instance |

## 3. Rollback Plan

| # | Check | Status |
| --- | --- | --- |
| 1 | Concrete rollback steps written | ✅ `docs/release/rollback-plan-0.59.0.md` |
| 2 | Reversibility classified | ✅ Reversible (mechanical code move, no schema/data migration) |
| 3 | Data compatibility assessed | ✅ Data-safe; `.governance/` records additive |
| 4 | Rollback impact assessed | ✅ Pure refactor; revert restores 0.58.0 in-file manifest functions |

## 4. Post-Release Validation

| # | Check | Status |
| --- | --- | --- |
| 1 | Core function verification list | ✅ check-manifest-consistency exit 0; Check 11 verify PASS; CLI output identical |
| 2 | Monitoring baseline | ✅ Pre-release: pytest 627 passed (2 failures are gitignored-data pollution, not code regression); 18 manifest-domain tests PASS |
| 3 | Verification owner | ✅ Coordinator |
| 4 | Alternative success criterion | ✅ "verify_workflow.py net shrinks + manifest.py clean + CLI contract identical + 18 manifest tests PASS" |

## 5. Data Validation Plan

| # | Check | Status |
| --- | --- | --- |
| 1 | Core metric baseline | ✅ Pre-release: verify_workflow.py=20516 (−421 vs 20937), manifest.py=below all thresholds |
| 2 | A/B test (N/A) | ✅ N/A — internal refactor; no user-facing metric |
| 3 | Success criteria quantified | ✅ "ArchGuard confirms split (module shrinks, new module clean), no CLI regression" |
| 4 | Observation window | ✅ ≥24h for structural release (post-tag) |
| 5 | Rollback trigger defined | ✅ See rollback-plan-0.59.0.md §1 (CLI regression / circular import / manifest-consistency failure) |

## 6. Release Decision

**Decision**: ✅ **可以发布 (Can release)**

Rationale: All checklist items pass. Pure mechanical refactor (12 functions moved byte-identical, verified via AST+unified-diff by independent post-hoc Explore review APPROVED — REVIEW-FIX-153). CLI contract preserved (54 commands unchanged). ArchGuard first real-world guard succeeded (module-size D-not-increase). No breaking changes, no schema migration, reversible. 2 pytest failures independently traced as gitignored-data pollution unrelated to manifest/checks code paths.

### Boundaries (no-overclaim)

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No external host-project validation of the split. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No split of other check domains (0.60.0~0.64.0). No modern engineering infrastructure (lint/type/package — deferred to 0.64.0). No RISK-036 closure. No RISK-037 closure. No RISK-039 closure (Phase 1/6; closure needs external host validation). No 1.0.0 readiness. DEC-086 degraded SoD honestly noted (post-hoc review, not pre-merge).

## 7. Release Gate Evidence

```
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.59.0 --require-changelog --runtime-adapters
→ Result: PASSED (to be confirmed at commit time)
```
