# Rollback Plan - 0.50.2

**Version**: 0.50.2

Rollback is required if the REL-029 release package overclaims approval, marketplace status, runtime support, Desktop lifecycle status, external validation full PASS, automatic capability selection, RISK-036 closure, or 1.0.0 readiness; or if the external project validation harness mutates its target or reports false PASS.

## Triggers

- `check-release --version 0.50.2 --require-changelog --runtime-adapters` fails.
- `check-version-consistency` reports a 0.50.2 declaration mismatch.
- `check-manifest-consistency --fail-on-issues` reports missing 0.50.2 release docs coverage.
- `external-project-validation --target <temp-target> --fail-on-issues` fails for a simple target.
- The harness writes into the target directory instead of the temporary workspace.
- The hot fact-source skip can be triggered without the generated sentinel and root temporary plan path.
- README, requirements docs, release docs, manifests, or CHANGELOG claim official approval, marketplace approval, universal/full runtime support, external validation full PASS for two real projects, external first-session pilot success, Codex Desktop marketplace-management E2E PASS, Desktop lifecycle E2E PASS, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, RISK-036 closure, or 1.0.0 production-ready.
- RISK-036 is marked resolved before its documented exit criteria are satisfied.

## Steps

1. Revert the 0.50.2 package commit after it exists:

```bash
git revert <0.50.2-release-package-commit>
```

2. Re-run the previous release gate:

```bash
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.50.1 --require-changelog --runtime-adapters
```

3. Re-prepare 0.50.2 with the no-overclaim boundary below before retrying REL-029.

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
