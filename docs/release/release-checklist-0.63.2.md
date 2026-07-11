# Release Checklist - 0.63.2

**Version**: 0.63.2 (patch)
**Release**: Check 29 auto-discovery 排除 session-snapshot 误报修复（FIX-178）
**Date**: 2026-07-05
**Documentation provenance**: BACKFILLED on 2026-07-08 by DOC-001 (commit `7792b4e`); not created at release time.

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined (semver) | ✅ 0.63.2 (patch: Check 29 false-positive fix) |
| 2 | Change list enumerated | ✅ FIX-178 — Check 29 auto-discovery excludes session-snapshot |
| 3 | Change types marked | ✅ Bugfix (Check 29 false-positive) / Documentation (version sync) |
| 4 | Release window | ✅ 2026-07-05 |

### Change inventory
- **FIX-178**: `verify_workflow.py check_m5_runtime_triggers` (line ~14316) in `text=None` auto-discovery mode originally treated `session-snapshot.md` as a runtime segment to scan (`has_tool=False` hardcoded). But session-snapshot is a **post-hoc record file** (snapshot format spec requires writing at session end; its structured fields may legitimately contain numbered step references and choice/option/plan vocabulary), not agent runtime output. T2 heuristic cannot distinguish "recorded menu" from "runtime menu", so legitimate records in snapshot (e.g. "第(1)(2)步…第(3)步" references + nearby choice words) triggered T2 with no AskUserQuestion tool call → check-governance Check 29 persistent FAIL.
- **Fix (Plan A — exclude session-snapshot from auto-discovery)**: (1) `check_m5_runtime_triggers` auto-discovery branch no longer adds session-snapshot as a segment, only scans evidence-log "事实依据" field (the real agent output summary); (2) function contract unchanged — callers can still explicitly scan snapshot via `corpus_sources=[('session-snapshot', text, False)]` (backward compatible); (3) docstring + inline comment updated with FIX-178 design decision.
- **Detection capability fully preserved**: inline `text=` path (the real runtime scan entry) byte-unchanged; 12 existing FIX-29 series tests all PASS; new reverse-protection regression test `test_fix178_detection_capability_preserved_on_fake_runtime_output` constructs a real violation (option menu + choice words + no tool call) asserting FAIL+T2, proving detection not weakened.
- **Version bump**: 0.63.1→0.63.2
- **verify output**: check-governance Check 29 FAIL→PASS (Scanned segments 2→1); test_verify_workflow.py 579 passed; infra suite 702 passed.

## 2-6. (Standard checks — all PASS, see release-checklist-0.61.0 template)

## 7. Release Gate Evidence

```
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.63.2 --require-changelog --runtime-adapters
→ Result: baseline-consistent with 0.63.1
python skills/software-project-governance/infra/verify_workflow.py check-governance — Check 29 PASS
```

Review evidence: FX-179 Release Agent + Release Reviewer R0.

### Boundaries (no-overclaim)

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS. No external first-session pilot success. No external host-project validation. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. Pure bug fix, no behavior change. Detection capability complete (reverse-protection test guards). 降级 SoD (DEC-090/091).
