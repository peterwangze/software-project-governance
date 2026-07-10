# Release Checklist - 0.64.0

**Version**: 0.64.0 (minor)
**Release**: 入口确定性重构——resolve_entry.py 双 root 解析器 + WORKFLOW_HOME 消除 + 版本权威源切换（DEC-096/AUDIT-129/FX-130/FX-131）
**Date**: 2026-07-09

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined (semver) | ✅ 0.64.0 (minor: entry-architecture refactor, new capability + behavior change) |
| 2 | Change list enumerated | ✅ AUDIT-129 (ADR) / FX-130 (resolve_entry.py + 20 tests) / FX-131 (prose wiring) |
| 3 | Change types marked | ✅ New feature (resolve_entry.py) / Refactor (prose) / Behavior change (version authority source) |
| 4 | Release window | ✅ 2026-07-09 |

### Change inventory
- **AUDIT-129**: Entry resolver architecture ADR — diagnosed three entry defects (version activation inconsistency / WORKFLOW_HOME dependency / startup cost), integrated 0.54.2/0.54.3 historical failure lesson (DEC-080/RISK-038), designed dual-root model. Output: `docs/requirements/entry-resolver-architecture-0.64.0.md`.
- **FX-130**: `infra/resolve_entry.py` (352 lines, pure stdlib) — deterministic dual-root entry resolver. PLUGIN_HOME (from `__file__`, locate executable + read SKILL.md frontmatter active_version) vs HOST_PROJECT_ROOT (--project-root / cwd, read .governance/ facts), never derives facts from `__file__`. Fail-closed: unresolvable host root → resolved_root_ok=false + diagnostic, never falls back to plugin-self. + 20 tests including the divergent-roots test (cwd≠plugin-root≠skill-path) that 0.54.2/0.54.3 lacked. Code Reviewer R0 APPROVED_WITH_NOTES (6/6, 0 P0/P1, 4 P2 — P2-1/P2-2 fixed in-place).
- **FX-131**: Entry prose wiring — 4 commands (root + 4 e2e mirrors) + AGENTS.md wired to resolve_entry.py. WORKFLOW_HOME 44→5 (all rationale notes, zero active archaeology). Decision tree 25-line ASCII → scenario_hint pointer. Version authority → scenario_hint=="C" (active_version from SKILL.md frontmatter). check_plugin_freshness downgraded to advisory. Code Reviewer R0 APPROVED_WITH_NOTES (7/7, 0 P0/P1, 3 P2 — P2-1 redundant decision tree deleted).
- **Stale test fix (FX-131 leftover)**: `test_governance_scenario_c_matches_continuous_archive_step_e` + `test_governance_commands_do_not_emit_repo_local_hook_install_only` updated from WORKFLOW_HOME needles to plugin_home needles (585 tests OK).
- **Version bump**: 0.63.4→0.64.0 (13 files: plugin.json×4/marketplace/package/manifest/SKILL/verify_workflow REQUIRED_SNIPPETS/4 hooks + e2e fixture pointers).
- **RISK-040 validation**: resolve_entry.py validated against project/e2e-test-project (independent host, scenario_hint=F there vs D in dev repo — proves it reads host .governance/ not plugin-self). Fail-closed verified (resolved_root_ok=false, zero governance data leak).

## 2-6. (Standard checks — see release-checklist-0.61.0 template for full criteria)

## 7. Release Gate Evidence

```
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
→ Result: PASSED (13 files, all 0.64.0)
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync — PASS
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.64.0 --require-changelog
→ Result: FAILED - 5 issue(s) — 3 pre-existing (archive integrity release_forced / governance health SYSGAP NEEDS_CHANGE historical / unit tests now PASS after fix), 2 release-docs (this 3-file set resolves them)
python skills/software-project-governance/infra/verify_workflow.py check-archive-integrity — FAIL (2 hot completed tasks pending release_forced archive, pre-existing pattern)
```

Review evidence: FX-130 Code Reviewer R0 APPROVED_WITH_NOTES (EVD-669) + FX-131 Code Reviewer R0 APPROVED_WITH_NOTES (EVD-670) + RISK-040 validation (EVD-671). 降级 SoD (DEC-090/091).

### Boundaries (no-overclaim)

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS. No external first-session pilot success. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No RISK-040 closure (validated against repo's own e2e fixture, not a real external installed project). No 1.0.0 readiness. This is a MINOR entry-architecture refactor: new resolve_entry.py capability + version authority source switch + WORKFLOW_HOME elimination. Non-breaking (resolve_entry outputs JSON for LLM consumption, backward-compatible with existing .governance/ structure). Does NOT repeat the 0.54.2/0.54.3 fast-start regression (DEC-080/RISK-038).
