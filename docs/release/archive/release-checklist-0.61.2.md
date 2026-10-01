# Release Checklist - 0.61.2

**Version**: 0.61.2 (patch)
**Release**: Chrys agent adapter integration — new Tier 1 agent platform
**Date**: 2026-07-01

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined (semver) | ✅ 0.61.2 (patch: new Tier 1 agent platform adapter) |
| 2 | Change list enumerated | ✅ Chrys adapter integration (adapters/chrys/) |
| 3 | Change types marked | ✅ New feature (Chrys adapter) / Documentation (README, SKILL.md, manifest.md, mainstream-agent-loading, runtime-readiness-matrix) / Validation (verify_workflow.py 8 sections) / Bugfix (opencode omission in supported_agents) |
| 4 | Release window | ✅ 2026-07-01 |

### Change inventory
- **Chrys adapter** (`adapters/chrys/`): New Tier 1 agent platform with native ask_user_question, sub_agent, and tool_calling support. First adapter with native AskUserQuestion-equivalent capability.
- **Documentation**: Chrys entries in README Tier 1 loading guide, SKILL.md adapter table, core/manifest.md supported_agents, mainstream-agent-loading-0.47.0.md, and runtime-readiness-matrix-0.43.0.md.
- **Validation**: Chrys in verify_workflow.py MAINSTREAM_AGENT_ADAPTERS, ADAPTER_RUNTIME_CAPABILITY_POLICY, PROJECTION_SNIPPETS, OPTIONAL_PROJECTION_FILES, MAINSTREAM_AGENT_LOADING_TIER1, MAINSTREAM_AGENT_LOADING_REQUIRED_DOCS, MAINSTREAM_AGENT_LOADING_ADAPTERS, RUNTIME_MATRIX_AGENT_IDS.
- **AGENTS.md**: Title updated to acknowledge Chrys alongside Codex.
- **opencode fix**: opencode added to supported_agents in core/manifest.md and SKILL.md adapter table (pre-existing omission).
- **Version bump**: 0.61.1→0.61.2 (18 files)
- **verify output**: 653 tests passed, check-agent-adapters 5/5 synchronized, check-mainstream-agent-loading PASSED

## 2-6. (Standard checks — all PASS, see release-checklist-0.61.0 template)

## 7. Release Gate Evidence

```
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.61.2
→ Result: to be confirmed at commit time
```

### Boundaries (no-overclaim)

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external validation full PASS for real projects. No external first-session pilot success. No external host-project validation. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness.
