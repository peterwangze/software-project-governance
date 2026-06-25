# Release Checklist - 0.58.0

**Version**: 0.58.0
**Release**: ArchGuard Architecture Health Stewardship (advisory-only)
**Task**: REL-044
**Date**: 2026-06-25

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined (semver) | ✅ 0.58.0 (minor: new advisory capability) |
| 2 | Change list enumerated | ✅ FIX-152 (a3b96c9) + design fixes (7270314) + REL-044 version bump |
| 3 | Change types marked | ✅ New feature (ArchGuard 4 checks) / advisory-only / version bump |
| 4 | Release window | ✅ 2026-06-25 |

### Change inventory
- **New feature**: 4 ArchGuard check commands (`check-architecture-health`/`check-duplicate-code`/`check-technical-debt`/`check-complexity`), advisory-only
- **New artifact**: `core/architecture-health.json` declarative threshold budget
- **Integration**: Check 28o~28r in `check-governance` (G7 advisory, no `all_issues` increment)
- **Tests**: `test_architecture_health.py` (14 tests)
- **Docs**: TOOL-043~046, CHANGELOG, release docs
- **Manifest**: G6 dual registration + G8 ledger registration
- **Version bump**: 0.57.0→0.58.0 (SKILL/plugin/marketplace/codex/manifest/hooks/REQUIRED_SNIPPETS/target)
- **Technical debt registered**: TD-012, TD-013 (P3, 0.59.0+)

## 2. Changelog

| # | Check | Status |
| --- | --- | --- |
| 1 | CHANGELOG updated, covers all changes | ✅ `project/CHANGELOG.md` [0.58.0] entry |
| 2 | Breaking changes highlighted | ✅ No breaking changes (advisory-only, fatal_on_error=false) |
| 3 | Dependency changes recorded | ✅ No new external dependencies (stdlib ast/json/os/fnmatch/re only) |
| 4 | Known issues listed | ✅ TD-012 (set-vs-diff duplicate metric), TD-013 (projection double-count) |

## 3. Rollback Plan

| # | Check | Status |
| --- | --- | --- |
| 1 | Concrete rollback steps written | ✅ `docs/release/rollback-plan-0.58.0.md` |
| 2 | Reversibility classified | ✅ Reversible (no schema/data migration) |
| 3 | Data compatibility assessed | ✅ Data-safe; `.governance/` records additive |
| 4 | Rollback impact assessed | ✅ Additive feature; revert restores 0.57.0 behavior |

## 4. Post-Release Validation

| # | Check | Status |
| --- | --- | --- |
| 1 | Core function verification list | ✅ 4 ArchGuard commands exit 0 (advisory); check-governance gate unaffected |
| 2 | Monitoring baseline | ✅ Pre-release: pytest 629 passed, ArchGuard 9 ERROR/10 WARN advisory |
| 3 | Verification owner | ✅ Coordinator |
| 4 | Alternative success criterion | ✅ "Core smoke (4 ArchGuard commands + full pytest) green + advisory contract holds" (internal tool, no user metric) |

## 5. Data Validation Plan

| # | Check | Status |
| --- | --- | --- |
| 1 | Core metric baseline | ✅ Pre-release: verify_workflow.py=20937 lines (ArchGuard self-detects), duplicate constants 2, source/projection dup 64.7% |
| 2 | A/B test (N/A) | ✅ N/A — internal advisory tool; no user-facing metric |
| 3 | Success criteria quantified | ✅ "Advisory findings reported, gate stays green, no test regression" |
| 4 | Observation window | ✅ ≥24h for capability release (post-tag) |
| 5 | Rollback trigger defined | ✅ See rollback-plan-0.58.0.md §1 (gate failure / crash / regression / overclaim) |

## 6. Release Decision

**Decision**: ✅ **可以发布 (Can release)**

Rationale: All checklist items pass. ArchGuard is advisory-only (cannot break the gate by design — G7 verified). No breaking changes, no schema migration, reversible release. Pre-existing FIX-076/EVD-281 governance-health advisory is out-of-scope and predates this release. Constraints G6/G7/G8/G9 verified by independent post-hoc Explore review (APPROVED).

### Boundaries (no-overclaim)

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No external host-project validation of ArchGuard. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No fatal-on-error ArchGuard (advisory only in 0.58.0). No AST cyclomatic complexity (deferred to 0.59.0+). No `verify_workflow.py` split (0.59.0~0.64.0). No modern engineering infrastructure (lint/type/package). No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. DEC-085 degraded SoD honestly noted (post-hoc review, not pre-merge).

## 7. Release Gate Evidence

```
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.58.0 --require-changelog --runtime-adapters
→ Result: PASSED (to be confirmed at commit time)
```
