# Rollback Plan - 0.56.1

**Version**: 0.56.1

Rollback is required if the REL-043 release package claims official/marketplace approval, universal runtime support, changes the governance workflow/lifecycle, allows the dashboard to execute agent/release/approval actions, closes RISK-036/RISK-037, or overclaims 1.0.0 readiness.

## Triggers

- `check-release --version 0.56.1 --require-changelog --runtime-adapters` fails.
- `check-version-consistency` reports a 0.56.1 declaration mismatch.
- `check-manifest-consistency --fail-on-issues` reports missing 0.56.1 release docs coverage.
- `check-governance --fail-on-issues` reports a release boundary, evidence, or risk posture issue.
- README, CHANGELOG, release docs, manifests, or validator output claim official approval, marketplace approval, universal/full runtime support, external validation full PASS, RISK-036 closure, RISK-037 closure, or 1.0.0 readiness.
- The dashboard is able to execute agent tasks, release, archive, or approval actions (it must remain read-only).

## Steps

1. Revert the 0.56.1 release package commit after it exists:

```bash
git revert <0.56.1-release-package-commit>
```

2. Re-run the previous release gate:

```bash
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.56.0 --require-changelog --runtime-adapters
```

3. Re-prepare 0.56.1 with the read-only/no-overclaim boundary before retrying REL-043.

## Verification After Rollback

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-release --version 1.0.0 --require-changelog --runtime-adapters
git diff --check
```

The 1.0.0 command must continue to fail with explicit blockers until final evidence and RISK-036/RISK-037 closure criteria are satisfied.

## No-Overclaim Boundary

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No completed non-game preset generalization claim. No Web replacement for CLI/client execution. No summary footer service startup. No Web-triggered agent task execution. No RISK-036 closure. No RISK-037 closure. No 1.0.0 readiness.

RISK-036 remains open. RISK-037 remains open.
