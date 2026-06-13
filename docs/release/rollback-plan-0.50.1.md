# Rollback Plan - 0.50.1

**Version**: 0.50.1

Rollback is required if the REL-028 release package overclaims approval, marketplace status, runtime support, Desktop lifecycle status, external validation, automatic capability selection, RISK-036 closure, or 1.0.0 readiness; or if it fails to keep 1.0.0 blocked with explicit hard blockers.

## Triggers

- `check-release --version 0.50.1 --require-changelog --runtime-adapters` fails.
- `check-version-consistency` reports a 0.50.1 declaration mismatch.
- `check-manifest-consistency --fail-on-issues` reports missing 0.50.1 release docs coverage.
- `check-release --version 1.0.0 --require-changelog --runtime-adapters` passes while RISK-036 is open or final evidence is missing.
- The 1.0.0 release gate fails only on missing release docs and does not explicitly report RISK-036, external validation full PASS, official submission result/approval, and Codex Desktop lifecycle blockers.
- README, requirements docs, release docs, manifests, or CHANGELOG claim official approval, marketplace approval, universal/full runtime support, external validation full PASS, external first-session pilot success, Codex Desktop marketplace-management E2E PASS, Desktop lifecycle E2E PASS, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, RISK-036 closure, or 1.0.0 production-ready.
- RISK-036 is marked resolved before its documented exit criteria are satisfied.

## Steps

1. Revert the 0.50.1 package commit after it exists:

```bash
git revert <0.50.1-release-package-commit>
```

2. Re-run the previous release gate:

```bash
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.50.0 --require-changelog --runtime-adapters
```

3. Re-prepare 0.50.1 with the no-overclaim boundary below before retrying REL-028.

## Verification After Rollback

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-release --version 1.0.0 --require-changelog --runtime-adapters
git diff --check
```

The 1.0.0 command must continue to fail with explicit blockers until final evidence and RISK-036 closure criteria are satisfied.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No RISK-036 closure. No 1.0.0 production-ready.

RISK-036 remains open.
