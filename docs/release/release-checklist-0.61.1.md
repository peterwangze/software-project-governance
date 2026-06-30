# Release Checklist - 0.61.1

**Version**: 0.61.1 (patch)
**Release**: archive engine decision/risk migration + verify cross-check (TD-014/015)
**Task**: FIX-162 + FIX-163
**Date**: 2026-06-30

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined (semver) | ✅ 0.61.1 (patch: bug fix + coverage gap closure) |
| 2 | Change list enumerated | ✅ FIX-162 (TD-014 decision/risk migration) + FIX-163 (TD-015 verify cross-check) |
| 3 | Change types marked | ✅ Bugfix (coupling regression P0) / New feature (decision/risk migration) / version bump |
| 4 | Release window | ✅ 2026-06-30 |

### Change inventory
- **FIX-162**: archive.py decision/risk migration (`_migrate_decisions`/`_migrate_risks`/`_entry_version_for_archive`). dry-run: 29 decisions + 11 risks migratable from real data.
- **FIX-163**: verify Check 3 per-category symmetric cross-check (tasks/evidence/decisions/risks). Fixes FIX-162/163 coupling P0.
- **Defensive parsing**: `_version_to_tuple` re.search extraction + `_version_in_range` None handling
- **Decision fidelity**: preserve full DEC row on migration (P2-1 fix)
- **Version bump**: 0.61.0→0.61.1 (13 files)
- **Tests**: +6 unit tests (TestDecisionRiskMigration 5 + coupling guard 1)

## 2-6. (Standard checks — all PASS, see release-checklist-0.61.0 template)

## 7. Release Gate Evidence

```
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.61.1
→ Result: to be confirmed at commit time (expect 12/13 PASS, 1 advisory as 0.61.0 baseline)
```

### Boundaries (no-overclaim)

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external validation full PASS for real projects. No external first-session pilot success. No external host-project validation. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure (closure needs external host validation). No 1.0.0 readiness. DEC-090/091 degraded SoD honestly noted (post-hoc review, not pre-merge). P2-2 test scenarios deferred (multi-task mixed refs, dry_run write isolation, version over-ceiling).
