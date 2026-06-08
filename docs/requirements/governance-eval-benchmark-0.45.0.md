# Governance Eval & Benchmark Report

Version target: 0.45.0

Related tasks: FIX-115, FIX-116, FIX-117, REL-022

Related requirements: REQ-092, REQ-093

Related risk: RISK-036

## Summary

0.45.0 adds a fact-backed capability discovery and restricted-environment benchmark package. The benchmark is diagnostic: it proves that the workflow can explain capability choices and degrade honestly in constrained environments. It does not prove external capability execution, Desktop marketplace-management success, official approval, marketplace approval, universal/full runtime support, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, or 1.0.0 production-ready status.

## Evidence Matrix

| Area | Result | Evidence | Boundary |
| --- | --- | --- | --- |
| Capability context trace | PASS | `capability-context --fail-on-issues`; FIX-115 commit `3fa8162d0429eab1d3b728c856ae03ff46022cc3`; REVIEW-FIX-115 approved | Diagnostic trace is not successful external execution. |
| External capability registry | PASS | `check-capability-registry --fail-on-issues`; FIX-116 commit `9325af6d022d1a0c642eee1af6465119fd8cdeb6`; REVIEW-FIX-116 approved | Catalog entry is not runtime PASS or external capability availability. |
| Restricted host capability benchmark | PASS | `check-host-capability-context --fail-on-issues`; FIX-117 commit `25677d76bc1317be20f32ef70db3fd1f3a25a8fc`; user-provided remote Governance CI success | Test fixture is benchmark/diagnostic, not Desktop marketplace E2E PASS. |
| Codex Desktop marketplace-management lifecycle | BLOCKED | `docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md` result matrix | No real Desktop add/install/enable/invoke/upgrade/uninstall evidence exists. |
| Official readiness / marketplace approval | BLOCKED | RISK-036 remains open | 0.45.0 is not official approval, marketplace approval, or 1.0.0 production-ready. |

## Restricted Scenario Coverage

| Scenario | Expected 0.45.0 behavior |
| --- | --- |
| `no_network` | Select local diagnostic fallback and mark degraded; do not call external APIs. |
| `no_plugin_install` | Inspect manifest/catalog facts only and mark degraded; do not claim install, enable, upgrade, uninstall, marketplace approval, or Desktop marketplace E2E PASS. |
| `no_mcp` | Mark MCP unavailable or degraded; do not treat MCP catalog facts as runtime PASS. |
| `no_browser` | Mark browser automation unavailable or degraded; do not open or mutate browser state. |
| `no_sub_agent` | Mark true host-native sub-agent separation unavailable or degraded; do not count self-review as independent review. |
| `local_skill_only` | Permit local skill/script diagnostic PASS when local facts exist, while stating it is not external capability execution. |
| `codex_cli_blocked` | Preserve Codex CLI blocked runtime facts; Codex App/session or plugin metadata cannot substitute for Codex CLI runtime PASS. |
| `gemini_auth_blocked` | Preserve Gemini auth blocked facts; Gemini version or thin projection cannot substitute for authenticated runtime PASS. |

## Release Acceptance Commands

- `python skills/software-project-governance/infra/verify_workflow.py capability-context --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-capability-registry --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-host-capability-context --fail-on-issues`
- `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.45.0 --require-changelog --runtime-adapters`
- `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -v`

## No-Overclaim Boundary

- No official approval.
- No marketplace approval.
- No universal/full runtime support.
- No external first-session pilot success.
- No Codex Desktop marketplace-management E2E PASS.
- No automatic best-tool selection.
- No universal plugin/skill/tool availability.
- No catalog entry runtime PASS.
- No 1.0.0 production-ready claim.
