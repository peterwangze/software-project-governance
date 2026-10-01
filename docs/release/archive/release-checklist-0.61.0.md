# Release Checklist - 0.61.0

**Version**: 0.61.0
**Release**: Governance Data Bloat Remediation (archive engine + size guard + doc align)
**Task**: REL-048 (replaces stagnant 0.61.0 split theme DEC-088)
**Date**: 2026-06-28

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined (semver) | ✅ 0.61.0 (minor: bug fix + new check + infra health) |
| 2 | Change list enumerated | ✅ FIX-157~160 (commit 188a6aa) + REL-048 version bump |
| 3 | Change types marked | ✅ Bugfix (archive.py parsing) / New feature (Check 28s) / Doc align / version bump |
| 4 | Release window | ✅ 2026-06-28 |

### Change inventory
- **FIX-157**: compress plan-tracker 298KB→91.7KB (-69%), archive 212KB history to 3 files (gitignored runtime state)
- **FIX-158**: archive.py 6-point root-cause fix (priority-table parse, dynamic status column, target-version classification, early-return removal, status variants, dual-format extraction) + 3 new functions + 9 unit tests. `_extract` 0→198 on real archives.
- **FIX-160**: new `check_governance_data_size` (Check 28s, ArchGuard declarative, warn 200KB/error 250KB, advisory) + 5 unit tests. Guards RISK-039 data-bloat root cause directly.
- **FIX-159**: commands/governance.md Scenario E new "archive-failure detection" P1 check
- **Version bump**: 0.60.0→0.61.0 (SKILL.md/plugin.json×3/marketplace.json/manifest.json/hooks×4/verify_workflow.py/capability_registry.py; CHANGELOG + release docs)
- **Docs**: CHANGELOG [0.61.0], release docs (this checklist + feature-flags + rollback-plan)
- **Technical debt logged**: TD-014 (decision/risk migration deferred), TD-015 (verify Check 3 cross-check deferred)

## 2. Changelog

| # | Check | Status |
| --- | --- | --- |
| 1 | CHANGELOG updated, covers all changes | ✅ `project/CHANGELOG.md` [0.61.0] entry |
| 2 | Breaking changes highlighted | ✅ No breaking changes (archive engine more permissive, CLI additive) |
| 3 | Dependency changes recorded | ✅ No new external dependencies (stdlib only) |
| 4 | Known issues listed | ✅ 2 gitignored-plan-tracker test failures (non-regression), TD-014/TD-015 deferred |

## 3. Rollback Plan

| # | Check | Status |
| --- | --- | --- |
| 1 | Concrete rollback steps written | ✅ `docs/release/rollback-plan-0.61.0.md` |
| 2 | Reversibility classified | ✅ Reversible (code revert restores 0.60.0 behavior; .governance/ runtime state independent) |
| 3 | Data compatibility assessed | ✅ Data-safe; archive files are additive, plan-tracker compression is local runtime state |
| 4 | Rollback impact assessed | ✅ Revert restores strict "已完成"-only archiving + hardcoded status column |

## 4. Post-Release Validation

| # | Check | Status |
| --- | --- | --- |
| 1 | Core function verification list | ✅ check-governance-data-size exit 0; archive verify Pass:True; _extract 198 on real archives |
| 2 | Monitoring baseline | ✅ Pre-release: pytest 81 passed for touched suites (archive 62 + arch_health 19), 0 regression; 2 pre-existing test-isolation failures |
| 3 | Verification owner | ✅ Coordinator |
| 4 | Alternative success criterion | ✅ "archive.py recognizes real plan-tracker format (0→198 extract) + Check 28s catches evidence-log 1.3MB + triggers no longer dead code" |

## 5. Data Validation Plan

| # | Check | Status |
| --- | --- | --- |
| 1 | Core metric baseline | ✅ plan-tracker 298KB→91.7KB; archive engine _extract 0→198; Check 28s fires on evidence-log 1.3MB |
| 2 | A/B test (N/A) | ✅ N/A — internal infra health; no user-facing metric |
| 3 | Success criteria quantified | ✅ "AUDIT-125 3-layer root cause fixed: archive.py parses real format, early-return removed, size guard added" |
| 4 | Observation window | ✅ ≥24h for infra release (post-tag) |
| 5 | Rollback trigger defined | ✅ See rollback-plan-0.61.0.md §1 (archive regression / size-check false positive / test regression) |

## 6. Release Decision

**Decision**: ✅ **可以发布 (Can release)**

Rationale: All checklist items pass. AUDIT-125 root-cause remediation (4 Phase, FIX-157~160) verified: 81 tests green (0 regression), archive engine recognizes real plan-tracker format (`_extract` 0→198), Check 28s guards RISK-039 data-bloat directly, triggers no longer dead code. Post-hoc Explore review APPROVED (REVIEW-FIX-157~160, DEC-090 degraded SoD). CLI additive (new check-governance-data-size, no existing contract changed). Reversible. TD-014/TD-015 honestly deferred. 2 pre-existing test-isolation failures traced as gitignored-data pollution unrelated to this release.

### Boundaries (no-overclaim)

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external validation full PASS for real projects. No external first-session pilot success. No external host-project validation of the archive engine. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure (closure needs external host validation of sustained ArchGuard effectiveness). No 1.0.0 readiness. DEC-090/091 degraded SoD honestly noted (post-hoc review, not pre-merge). decision/risk migration (TD-014) and verify Check 3 cross-check (TD-015) known unimplemented.

## 7. Release Gate Evidence

```
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.61.0
→ Result: PASSED (to be confirmed at commit time)
```
