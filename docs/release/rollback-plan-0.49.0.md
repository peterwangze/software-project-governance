# Rollback Plan - 0.49.0

**Version**: 0.49.0

Rollback is required if the REL-026 External Validation and Official Submission Closure package overclaims approval, marketplace status, runtime support, Desktop lifecycle status, external validation, automatic capability selection, RISK-036 closure, or 1.0.0 readiness.

## Triggers

- `check-release --version 0.49.0 --require-changelog --runtime-adapters` fails.
- `check-version-consistency` reports a 0.49.0 declaration mismatch.
- `check-manifest-consistency --fail-on-issues` reports missing 0.49.0 release docs coverage.
- README, requirements docs, release docs, manifests, or CHANGELOG claim official approval, marketplace approval, universal/full runtime support, external validation PASS, external first-session pilot success, Codex Desktop marketplace-management E2E PASS, Desktop lifecycle E2E PASS, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, or 1.0.0 production-ready.
- RISK-036 is marked resolved before its documented exit criteria are satisfied.
- VAL-001, VAL-002, or FIX-126 are described as full PASS evidence instead of conservative partial/blocker evidence.

## Steps

1. Revert the 0.49.0 package commit after it exists:

```bash
git revert <0.49.0-release-package-commit>
```

2. Re-run the previous release gate:

```bash
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.48.0 --require-changelog --runtime-adapters
```

3. Re-prepare 0.49.0 with the no-overclaim boundary below before retrying REL-026.

## Verification After Rollback

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues
git diff --check
```

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation PASS. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No 1.0.0 production-ready.

RISK-036 remains open.
