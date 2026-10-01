# Rollback Plan - 0.47.0

**Version**: 0.47.0

Rollback is required if the REL-024 Mainstream Agent Loading Readiness package overclaims approval, runtime support, automatic selection, Desktop lifecycle status, or 1.0.0 readiness.

## Triggers

- `check-release --version 0.47.0 --require-changelog --runtime-adapters` fails.
- README, adapter READMEs, release docs, requirements docs, or CHANGELOG claim official approval, marketplace approval, universal/full runtime support, external first-session pilot success, Codex Desktop marketplace-management E2E PASS, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, or 1.0.0 production-ready.
- `check-mainstream-agent-loading --fail-on-issues` fails or is removed from Check 28n.
- Tier 2 compatibility rows stop saying compatibility/research only or claim runtime PASS without native entry projection and target-cwd E2E evidence.
- FIX-120 carried-forward Codex marketplace root schema prerequisite regresses or is described as Codex Desktop marketplace lifecycle E2E PASS.
- FIX-123 Codex manifest asset path validation regresses.

## Steps

1. Revert the 0.47.0 package commit after it exists:

```bash
git revert <0.47.0-release-package-commit>
```

2. Re-run the previous release gate:

```bash
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.46.0 --require-changelog --runtime-adapters
```

3. Re-prepare the mainstream loading docs, adapter guides, manifest paths, Check 28n, and TOOL-035 with the no-overclaim boundary below before retrying 0.47.0.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No 1.0.0 production-ready.

RISK-036 remains open.
