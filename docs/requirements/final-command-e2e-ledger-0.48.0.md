# Final Command E2E Ledger - 0.48.0

Date: 2026-06-10
Task: FIX-125
Source audit: AUDIT-113

This ledger consolidates the command, fixture, runtime, capability, and release-gate evidence needed to retire the old scattered REQ-033 / REQ-058 "full command E2E" planning debt. It does not make 1.0.0 releasable.

No official approval. No marketplace approval. No universal/full runtime support. No external validation PASS. No Codex Desktop marketplace-management E2E PASS. No 1.0.0 production-ready status.

## Command Ledger

| Area | Command | Result | Evidence boundary |
| --- | --- | --- | --- |
| Source CLI proxy commands | `python skills/software-project-governance/infra/verify_workflow.py e2e-check` | PASS | Source proxy matrix passed 6/6. These are source-root executable proxies, not external project validations. |
| External target-cwd commands | `python skills/software-project-governance/infra/verify_workflow.py e2e-check` | PASS | Target fixture command matrix passed 4/4 from `project/e2e-test-project`. |
| Target fixture contract | `python skills/software-project-governance/infra/verify_workflow.py e2e-check` | PASS | Target fixture checks passed 8/8; runtime-only contracts are reported separately as 4 contract-only checks. |
| 0.47.0 release readiness without execution gates | `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.47.0 --require-changelog --runtime-adapters --skip-execution-gates` | PASS | Release fact source, hot fact source, runtime matrix, first session measurement, pack status, adapters, projection sync, cross references, archive integrity, release docs, and changelog passed. |
| Runtime readiness matrix | `python skills/software-project-governance/infra/verify_workflow.py check-runtime-readiness-matrix --fail-on-issues` | PASS | Public matrix remains aligned with adapter facts and no-overclaim boundaries. |
| Mainstream loading guidance | `python skills/software-project-governance/infra/verify_workflow.py check-mainstream-agent-loading --fail-on-issues` | PASS | README, Tier 1 adapters, and 0.47.0 requirements stay synchronized. |
| Capability context trace | `python skills/software-project-governance/infra/verify_workflow.py capability-context --fail-on-issues` | PASS / DEGRADED boundary | Local read-only diagnostic selected; registry is catalog fact source, not runtime PASS. |
| Restricted host capability benchmark | `python skills/software-project-governance/infra/verify_workflow.py check-host-capability-context --fail-on-issues` | PASS with mixed scenario states | Benchmark reports no_network/no_plugin_install/no_sub_agent as DEGRADED, no_mcp/no_browser as NOT_SUPPORTED, Codex/Gemini runtime blockers explicitly, and local_skill_only PASS. |
| Official submission ecosystem boundary | `python skills/software-project-governance/infra/verify_workflow.py check-official-submission-ecosystem --fail-on-issues` | PASS | Official-submission docs remain ecosystem-positioned and no-overclaim safe. |
| Agent runtime E2E harness | `python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --timeout 90` | PASS/BLOCKED, fail=0 | Claude PASS, Codex PASS, opencode PASS, Gemini BLOCKED due auth/401; this is runtime evidence, not external project validation. |
| Full 0.47.0 release gate with execution gates | `python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.47.0 --require-changelog --runtime-adapters` | FAIL | verify PASS, e2e PASS, unit PASS, but governance health fails because root `.governance/evidence-log.md` historical 10-column hot format is counted by `--fail-on-issues` structural validity. |

## Summary

REQ-033 and REQ-058 now have a single command evidence ledger. The command surface is not blank or scattered anymore.

However, 0.48.0 is **not release-ready** yet because the full release gate fails on governance health. The failure is not a runtime adapter failure and not an e2e command failure; it is a governance-health structural-validity issue around historical hot evidence rows.

## New Release Blocker

| Blocker | Required next item | Acceptance |
| --- | --- | --- |
| Governance health fails inside full release gate | FIX-127 | `check-release --version 0.47.0 --require-changelog --runtime-adapters` or the current target release equivalent passes, with structural validity either fixed or correctly scoped so historical hot evidence format does not block release health. |

## 1.0.0 Boundary

This ledger does not close RISK-036 because the following are still missing:

- at least two external project validations;
- Codex Desktop marketplace-management lifecycle PASS or conservative blocked carry-forward in the final submission/release package;
- final official submission bundle review;
- RISK-036 closure decision.
