# Rollback Plan - 0.50.3

**Version**: 0.50.3

Rollback is required if the REL-030 release package overclaims approval, marketplace status, runtime support, Desktop lifecycle status, external validation full PASS, automatic capability selection, RISK-036 closure, or 1.0.0 readiness; or if installed runtime repair, commit message source hardening, or target-native diagnostics regress supported behavior.

## Triggers

- `check-release --version 0.50.3 --require-changelog --runtime-adapters` fails.
- `check-version-consistency` reports a 0.50.3 declaration mismatch.
- `check-manifest-consistency --fail-on-issues` reports missing 0.50.3 release docs coverage.
- Installed hooks cannot resolve the workflow home from explicit env, repo-local install, or plugin cache.
- pre-commit reads stale `.git/COMMIT_EDITMSG` or `.git/GOV_COMMIT_MSG` as the current commit message semantic source.
- commit-msg no longer treats the actual commit message file as authoritative.
- `external-project-validation --target <target> --fail-on-issues` mutates the target project.
- Target-native diagnostics miss known repo-local native entry assumptions, installed hook version/content drift, legacy stale message source, or repo-local self-upgrade source issues.
- README, requirements docs, release docs, manifests, or CHANGELOG claim official approval, marketplace approval, universal/full runtime support, external validation full PASS for two real projects, external first-session pilot success, Codex Desktop marketplace-management E2E PASS, Desktop lifecycle E2E PASS, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, RISK-036 closure, or 1.0.0 production-ready.
- VAL-003 shitu or VAL-004 python_game is described as full PASS rather than FAIL/PARTIAL diagnostic archive.
- RISK-036 is marked resolved before its documented exit criteria are satisfied.

## Steps

1. Revert the 0.50.3 package commit after it exists:

```bash
git revert <0.50.3-release-package-commit>
```

2. Re-run the previous release gate:

```bash
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.50.2 --require-changelog --runtime-adapters
```

3. Re-prepare 0.50.3 with the no-overclaim boundary below before retrying REL-030.

## Verification After Rollback

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-release --version 1.0.0 --require-changelog --runtime-adapters
git diff --check
```

The 1.0.0 command must continue to fail with explicit blockers until final evidence and RISK-036 closure criteria are satisfied.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No RISK-036 closure. No 1.0.0 production-ready.

RISK-036 remains open.
