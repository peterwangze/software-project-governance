# Release Checklist - 0.63.4

**Version**: 0.63.4 (patch)
**Release**: check_version_consistency VERSION_FILES 覆盖盲区修复（FIX-182）
**Date**: 2026-07-07

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined (semver) | ✅ 0.63.4 (patch: check-tool coverage scope fix) |
| 2 | Change list enumerated | ✅ FIX-182 — VERSION_FILES covers all 4 plugin.json + print string fix |
| 3 | Change types marked | ✅ Bugfix (check-tool coverage) / Documentation (version sync, fixture pointer sync) |
| 4 | Release window | ✅ 2026-07-07 |

### Change inventory
- **FIX-182** (FX-181 Release Reviewer R0 independently discovered): `check_version_consistency`'s `VERSION_FILES` dict (verify_workflow.py:9498-9504) only covered 3 plugin-related files (`.claude-plugin/plugin.json` + `marketplace.json` + `.codex-plugin/plugin.json`), missing `.zcode-plugin/plugin.json` and `.chrys-plugin/plugin.json`. Print string (line 20094) hardcoded "3 plugin.json" but the project actually has 4 plugin.json directories. Impact: if a future release misses updating `.zcode-plugin` or `.chrys-plugin` plugin.json version, the `VERSION_FILES` loop would not detect it (`REQUIRED_SNIPPETS` snippet self-check only scans `verify_workflow.py` inline literals, not actual plugin.json file contents). No actual drift this time (manual check + projection-sync fallback).
- **Fix**: (1) `VERSION_FILES` add `.zcode-plugin/plugin.json` and `.chrys-plugin/plugin.json` two entries; (2) print string corrected to "13 files (SKILL.md, manifest.json, marketplace.json, 4 plugin.json, CHANGELOG, plan-tracker, 4 hooks)" (N=13 = VERSION_FILES 7 + CHANGELOG 1 + plan-tracker 1 + HOOK_FILES 4); (3) new regression test `test_fix182_version_files_covers_zcode_and_chrys_plugin`: PASS-after-fix calls real `check_version_consistency` constructing `.zcode-plugin` version drift asserting detected; FAIL-on-buggy self-contained replay demonstrates pre-fix 5-entry dict blind spot.
- **Version bump**: 0.63.3→0.63.4 (11 files: plugin.json×4/marketplace/package/manifest/SKILL/verify_workflow REQUIRED_SNIPPETS/4 hooks)
- **e2e fixture pointer sync**: with FX-177/179/181 precedent.
- **verify output**: check-version-consistency PASSED (13 files, 4 plugin.json, all 0.63.4); 703 tests passed.

## 2-6. (Standard checks — all PASS, see release-checklist-0.61.0 template)

## 7. Release Gate Evidence

```
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
→ Result: PASSED (Files checked: 13, 4 plugin.json, all 0.63.4) — FIX-182 core deliverable
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.63.4 --require-changelog --runtime-adapters
→ Result: baseline-consistent with 0.63.3 (FAIL items pre-existing, not introduced this release)
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync — PASS
python skills/software-project-governance/infra/verify_workflow.py check-archive-integrity — PASS
```

Review evidence: FX-183 Release Agent + Release Reviewer R0 (7/7 checklist, FX-181 R0 P2-1 closed-loop: R0 discover→FIX-182 fix→R0 verify).

### Boundaries (no-overclaim)

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS. No external first-session pilot success. No external host-project validation. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. Pure bug fix (check-tool coverage scope fix), only affects check-tool coverage, no runtime behavior change. 降级 SoD (DEC-090/091).
