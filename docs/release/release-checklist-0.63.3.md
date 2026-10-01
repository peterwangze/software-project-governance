# Release Checklist - 0.63.3

**Version**: 0.63.3 (patch)
**Release**: e2e fixture SKILL.md adapter 表结构对齐（FIX-180）
**Date**: 2026-07-06
**Documentation provenance**: BACKFILLED on 2026-07-08 by DOC-001 (commit `7792b4e`); not created at release time.

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined (semver) | ✅ 0.63.3 (patch: e2e fixture adapter table alignment) |
| 2 | Change list enumerated | ✅ FIX-180 — e2e fixture SKILL.md adapter table补 opencode + Chrys rows |
| 3 | Change types marked | ✅ Bugfix (e2e fixture drift) / Documentation (version sync, fixture pointer sync) |
| 4 | Release window | ✅ 2026-07-06 |

### Change inventory
- **FIX-180**: source `skills/software-project-governance/SKILL.md` agent adapter table has 6 rows (Claude Code/Codex/Gemini/opencode/Chrys/国内 Agent CLI), but e2e fixture `project/e2e-test-project/skills/software-project-governance/SKILL.md` only had 4 rows — missing opencode and Chrys (0.61.2 introduced Chrys integration but fixture wasn't aligned). This caused `check-projection-sync` (Check 28) to persistently report "target fixture drift: skills/software-project-governance/SKILL.md" FAIL.
- **Fix**: add opencode and Chrys two rows to fixture SKILL.md adapter table after Gemini row, byte-for-byte consistent with source (single file +2 rows, no source change). projection-sync FAIL→PASS.
- **Version bump**: 0.63.2→0.63.3 (11 files: plugin.json×4/marketplace/package/manifest/SKILL/verify_workflow REQUIRED_SNIPPETS/4 hooks)
- **e2e fixture pointer sync**: `project/e2e-test-project/skills/software-project-governance/SKILL.md` + `project/e2e-test-project/.governance/plan-tracker.md` version pointer 0.63.2→0.63.3.
- **verify output**: check-version-consistency PASSED; check-projection-sync PASS (4 mirrored files, no drift); 702 tests passed.

## 2-6. (Standard checks — all PASS, see release-checklist-0.61.0 template)

## 7. Release Gate Evidence

```
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.63.3 --require-changelog --runtime-adapters
→ Result: baseline-consistent with 0.63.2
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync — PASS (FIX-180 core deliverable)
python skills/software-project-governance/infra/verify_workflow.py check-archive-integrity — PASS
```

Review evidence: FX-181 Release Agent + Release Reviewer R0.

### Boundaries (no-overclaim)

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS. No external first-session pilot success. No external host-project validation. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. Pure bug fix (e2e fixture alignment), only affects test data, no runtime behavior change. 降级 SoD (DEC-090/091).
