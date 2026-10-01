# Rollback Plan - 0.48.0

**Version**: 0.48.0

Rollback is required if the REL-025 1.0.0 Readiness Reconciliation package overclaims approval, runtime support, automatic selection, Desktop lifecycle status, external validation, or 1.0.0 readiness.

## Triggers

- `check-release --version 0.48.0 --require-changelog --runtime-adapters` fails.
- README, requirements docs, release docs, or CHANGELOG claim official approval, marketplace approval, universal/full runtime support, external first-session pilot success, Codex Desktop marketplace-management E2E PASS, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, or 1.0.0 production-ready.
- RISK-036 is marked resolved before its documented exit criteria are satisfied.
- VAL-001, VAL-002, FIX-126, or REL-026 are described as completed in the 0.48.0 release package without new evidence.
- `check-governance --fail-on-issues` fails on a blocking structural validity issue.

## Steps

1. Revert the 0.48.0 package commit after it exists:

```bash
git revert <0.48.0-release-package-commit>
```

2. Re-run the previous release gate:

```bash
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.47.0 --require-changelog --runtime-adapters
```

3. Re-prepare the readiness reconciliation package with the no-overclaim boundary below before retrying 0.48.0.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No 1.0.0 production-ready.

RISK-036 remains open.
