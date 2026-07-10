# Rollback Plan - 0.64.0

**Version**: 0.64.0 (minor)
**Release**: 入口确定性重构——resolve_entry.py 双 root 解析器 + WORKFLOW_HOME 消除 + 版本权威源切换（DEC-096/AUDIT-129/FX-130/FX-131）
**Date**: 2026-07-09

## Rollback Triggers

| Trigger | Severity | Detection | Action |
|---------|----------|-----------|--------|
| resolve_entry.py reads plugin-self .governance/ instead of host (0.54.2/0.54.3 regression) | Critical | resolve_entry.py output shows plugin's own governance state (wrong version roadmap/stage) in a real host project | Immediate rollback to 0.63.4; re-open RISK-040 |
| resolve_entry.py fail-closed fires on valid host root | High | resolved_root_ok=false when host .governance/ exists and cwd is valid | Rollback to 0.63.4; fix resolver host-root resolution |
| Commands prose references resolve_entry.py but plugin not installed (path not found) | Medium | LLM cannot locate resolve_entry.py | Fall back to 0.63.4 prose (WORKFLOW_HOME still has rationale notes as fallback documentation) |
| Version authority mismatch (SKILL.md frontmatter disagrees with installed_plugins.json causing confusion) | Low | active_version from frontmatter ≠ installed version record | Advisory only (check_plugin_freshness still reports); no rollback needed |

## Rollback Steps

### Full rollback to 0.63.4
1. `git revert <0.64.0-release-commit>` (reverts resolve_entry.py + prose + version bump)
2. Re-bump version 0.64.0 → 0.63.4 across 13 declaration files
3. Re-push to origin
4. Re-open RISK-040 with regression evidence
5. Record rollback decision in decision-log

### Partial rollback (keep resolve_entry.py, revert prose only)
If resolve_entry.py itself is sound but the prose wiring (FX-131) causes issues:
1. `git revert d70b9f3` (FX-131 prose only — restores WORKFLOW_HOME in commands)
2. Keep resolve_entry.py (c7a9942) available as opt-in tool
3. Commands revert to WORKFLOW_HOME 4-priority resolution (still functional, just slower)

## Reversibility

| Component | Reversible? | Method |
|-----------|-------------|--------|
| resolve_entry.py (FX-130) | ✅ Yes | `git revert c7a9942` — file is additive, removing it restores 0.63.4 behavior |
| Entry prose (FX-131) | ✅ Yes | `git revert d70b9f3` — restores WORKFLOW_HOME needles; test file revert needed too |
| Version bump (0.64.0→0.63.4) | ✅ Yes | Re-edit 13 declaration files (mechanical) |
| RISK-040 closure | ✅ Yes | Re-open in risk-log if regression found |
| resolve_entry.py projection to e2e | ✅ Yes | Remove project/e2e-test-project/skills/.../resolve_entry.py |

### No-overclaim boundaries

No official approval. No marketplace approval. No universal/full runtime support. No RISK-036/037/039/040 closure. No 1.0.0 readiness. Rollback plan covers the regression scenarios specific to this release (dual-root binding failure = the 0.54.2/0.54.3 class of bug). Full and partial rollback paths are reversible via git revert + mechanical version re-bump. resolve_entry.py is additive (no destructive migration), so rollback is low-risk.
