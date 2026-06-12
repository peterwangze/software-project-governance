# Feature Flags - 0.50.0

**Version**: 0.50.0

REL-027 / 0.50.0 is a release evidence package for mainstream agent target-cwd read E2E. It does not add a runtime feature flag, does not change default governance execution behavior, and does not enable an approval, marketplace lifecycle, or automatic tool-selection feature.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| Mainstream agent target-cwd read E2E evidence | Available as tracked documentation and adapter facts | Covers Codex, Claude Code, Gemini CLI, and opencode read/bootstrap E2E only; not universal/full runtime support |
| Gemini headless trust guidance | Available in README and adapter docs | Uses process-local `GEMINI_CLI_TRUST_WORKSPACE=true`; not stored credential evidence and not broad Gemini tool-use closure |
| Restricted host benchmark fixtures | Available in validator | Simulated blocked scenarios remain diagnostic fixtures; they do not override current live runtime PASS/DEGRADED facts |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open and 1.0.0 remains blocked |

## Kill Switch and Rollback Boundary

The release package has no runtime flag to disable. The rollback trigger is documentary or metadata overclaim: revert the release package if README, CHANGELOG, release docs, manifests, or validation wording turns target-cwd read E2E evidence into official approval, marketplace acceptance, external validation success, Desktop lifecycle success, automatic best-tool selection, universal/full runtime support, or 1.0.0 readiness.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation PASS. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No 1.0.0 production-ready.

RISK-036 remains open.
