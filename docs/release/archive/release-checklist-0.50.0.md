# Release Checklist - 0.50.0

**Version**: 0.50.0

**Release theme**: REL-027 Mainstream Agent E2E Risk Release

## Checklist

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | FIX-129 mainstream agent E2E risk release is recorded | PASS | `docs/requirements/mainstream-agent-e2e-risk-release-0.50.0.md`; final runtime harness returned `pass=4, blocked=0, fail=0, total=4` |
| 2 | Tier 1 target-cwd read E2E evidence covers Codex, Claude Code, Gemini CLI, and opencode | PASS / DEGRADED | Real target-cwd read E2E returned machine-readable fields for all four agents; Gemini requires process-local `GEMINI_CLI_TRUST_WORKSPACE=true` for headless trust |
| 3 | Runtime readiness and loading docs are refreshed | PASS | README, runtime/readiness matrix, final command E2E ledger, mainstream loading docs, and Codex/Gemini adapter manifests were updated in FIX-129 |
| 4 | Version declarations are synchronized | PASS | Source SKILL, manifest, Claude/Codex plugin metadata, Claude marketplace metadata, hook @version, target fixture skill, target fixture plan tracker, and REQUIRED_SNIPPETS are 0.50.0 |
| 5 | Release docs are manifest-covered | PASS | `release-checklist-0.50.0.md`, `feature-flags-0.50.0.md`, and `rollback-plan-0.50.0.md` are listed in `core/manifest.json` |
| 6 | RISK-036 remains open | PASS | 0.50.0 releases only the mainstream agent target-cwd read E2E sub-risk and does not claim official approval, marketplace approval, Desktop lifecycle PASS, external validation PASS, or 1.0.0 readiness |

## Release Boundary

0.50.0 packages FIX-129 after the user configured Codex, Claude Code, Gemini CLI, and opencode in the current environment. The final runtime command was:

```bash
GEMINI_CLI_TRUST_WORKSPACE=true python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --timeout 180
```

The result was `pass=4, blocked=0, fail=0, total=4`.

This release changes the current public runtime/readiness facts for the four Tier 1 mainstream agents from older blocked/degraded facts to PASS/DEGRADED target-cwd read E2E evidence. It does not close the remaining RISK-036 criteria: full external project validation, official submission result or approval evidence, Codex Desktop marketplace-management lifecycle PASS or conservative blocked disposition, and final 1.0.0 release review.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation PASS. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No 1.0.0 production-ready.

RISK-036 remains open.
