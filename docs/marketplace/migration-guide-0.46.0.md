# Migration Guide - Ecosystem Positioning 0.46.0

Version target: 0.46.0

Related task: FIX-118

## Who This Is For

This guide is for users who already use specialized agent capability systems and want governance continuity without replacing those systems.

This guide consumes `docs/requirements/capability-discovery-orchestration-0.45.0.md`, `docs/requirements/governance-eval-benchmark-0.45.0.md`, FIX-115, FIX-116, FIX-117, and the Codex Desktop marketplace-management BLOCKED / NOT_RUN report.

## Migration Path

| Current setup | Recommended migration | Boundary |
| --- | --- | --- |
| You use Superpowers-style capability packs. | Keep the packs. Add Software Project Governance as the delivery trust layer for goals, evidence, risk, review, and release gates. | This workflow does not replace Superpowers-style capabilities. |
| You use Agent Skills. | Keep task skills. Use the capability selection trace to record which skill is available and why it was chosen. | Skill availability remains host-specific. |
| You use MCP servers. | Keep MCP connectors. Record MCP availability, side effects, validation, and fallback. | MCP catalog facts are not runtime PASS. |
| You use browser tools. | Keep browser automation where it is available and authorized. Add evidence and side-effect boundaries. | Browser state is external and must be treated as a side effect. |
| You use host-native plugins. | Keep host-native install and management mechanisms. Use governance records to track readiness and submission evidence. | Manifest presence is not marketplace approval or Codex Desktop lifecycle PASS. |
| You work in restricted environments. | Use local scripts and fallbacks while recording DEGRADED, BLOCKED, NOT_SUPPORTED, or NOT_FOUND when external capability is unavailable. | Fallback success is not external execution success. |

## Validation Commands

Run these checks before treating the migration as ready for official-submission review:

```bash
python skills/software-project-governance/infra/verify_workflow.py capability-context --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-capability-registry --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-host-capability-context --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.46.0 --require-changelog --runtime-adapters
```

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No 1.0.0 production-ready.
