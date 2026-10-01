# Feature Flags - 0.64.0

**Version**: 0.64.0 (minor)
**Release**: 入口确定性重构——resolve_entry.py 双 root 解析器 + WORKFLOW_HOME 消除 + 版本权威源切换（DEC-096/AUDIT-129/FX-130/FX-131）
**Date**: 2026-07-09

## Feature Flag Inventory

This release introduces a new deterministic entry resolver (`infra/resolve_entry.py`) with **no runtime feature flags** — the resolver is always active when invoked. There are no toggleable flags; the behavioral change is structural (entry path resolution mechanism).

## Behavior

| Component | Default | Notes |
|-----------|---------|-------|
| `resolve_entry.py` dual-root resolver | enabled (on invocation) | PLUGIN_HOME (from `__file__`, locate executable + read SKILL.md frontmatter active_version) vs HOST_PROJECT_ROOT (--project-root / cwd, read .governance/ facts). Never derives facts source from `__file__`. |
| Version authority source | `skill_frontmatter` | Active version now authoritatively read from SKILL.md frontmatter (was: installed_plugins.json archaeology). `check_plugin_freshness` downgraded to advisory. |
| `scenario_hint` (A-F) | computed deterministically | Replaces LLM multi-step decision tree (6-branch file stat). resolve_entry.py runs once, outputs JSON, LLM branches on scenario_hint. |
| fail-closed | enforced | `resolved_root_ok == false` → STOP + diagnostic, never falls back to plugin-self state (DEC-080 / RISK-038 regression avoidance). |
| WORKFLOW_HOME 4-priority resolve | removed | 44 occurrences across commands/ eliminated; canonical 4-priority block (SPG_HOME / project skills / cache scan) deleted. Remaining 5 occurrences are rationale comments only. |
| resolve_entry.py import constraint | enforced | Cannot import verify_workflow.py (runs before it can be located). Prose mandates: resolve_entry FIRST, then verify_workflow/archive.py/cleanup.py with plugin_home. |

## No-overclaim boundaries

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No RISK-040 closure (validated against e2e-test-project but not a real external installed project beyond the repo's own e2e fixture). No 1.0.0 readiness. This is an entry-architecture refactor (MINOR): new resolve_entry.py capability + version authority source switch + WORKFLOW_HOME elimination. Non-breaking (resolve_entry outputs JSON for LLM consumption, backward-compatible with existing .governance/ structure). Does NOT repeat the 0.54.2/0.54.3 fast-start regression (DEC-080/RISK-038) — this is a deterministic resolver + full skill load, not a fast-start simplified path.
