# Feature Flags - 0.49.0

**Version**: 0.49.0

REL-026 / 0.49.0 is a release evidence package. It does not add a runtime feature flag, does not change default governance execution behavior, and does not enable an approval or marketplace lifecycle feature.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| External project validation evidence | Available as tracked documentation | Useful smoke evidence only; not external validation PASS |
| External new-project empty ID guard | Available in validator | Prevents empty DEC/EVD/RISK Check 13 crash; does not make partial external installs pass full governance health |
| Codex CLI marketplace source sync evidence | Available as tracked documentation | CLI source sync only; not Desktop install/enable/invoke/upgrade/uninstall lifecycle |
| Official submission candidate bundle review | Available as tracked documentation | Candidate bundle review only; not official submission result, official approval, or marketplace approval |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open and 1.0.0 remains blocked |

## Kill Switch and Rollback Boundary

The release package has no runtime flag to disable. The rollback trigger is documentary or metadata overclaim: revert the release package if README, CHANGELOG, release docs, manifests, or validation wording turns blocked evidence into approval, PASS, universal support, or 1.0.0 readiness.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation PASS. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No 1.0.0 production-ready.

RISK-036 remains open.
