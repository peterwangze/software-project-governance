# Rollback Plan - 0.55.3

**Version**: 0.55.3

Rollback is required if the REL-041 release package makes Web the primary execution path, starts services from summary footer mode, silently installs dependencies, treats a non-SPG service as the Web console, changes dynamic lifecycle activation, changes the release boundary for RISK-036/RISK-037, or overclaims official approval, marketplace status, external validation full PASS, Codex Desktop lifecycle PASS, project migration, or 1.0.0 readiness.

## Triggers

- `check-release --version 0.55.3 --require-changelog --runtime-adapters` fails.
- `check-version-consistency` reports a 0.55.3 declaration mismatch.
- `check-manifest-consistency --fail-on-issues` reports missing 0.55.3 release docs coverage.
- `check-governance --fail-on-issues` reports a release boundary, evidence, or risk posture issue.
- `web-console --governance-entry` fails to reuse an already running SPG console.
- `web-console --governance-entry` silently installs dependencies or treats an occupied non-SPG port as valid.
- `web-console --summary-link` starts a service, invokes npm, opens a browser, or writes runtime process state.
- README, CHANGELOG, release docs, manifests, or validator output claim official approval, marketplace approval, universal/full runtime support, external validation full PASS for two real projects, external first-session pilot success, Codex Desktop marketplace-management E2E PASS, Desktop lifecycle E2E PASS, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, project migration, dynamic-flow-gate default, RISK-036 closure, RISK-037 closure, or 1.0.0 production-ready.

## Steps

1. Revert the 0.55.3 package commit after it exists:

```bash
git revert <0.55.3-release-package-commit>
```

2. Re-run the previous release gate:

```bash
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.55.2 --require-changelog --runtime-adapters
```

3. Re-prepare 0.55.3 with the governance-entry boundary before retrying REL-041.

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

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No completed non-game preset generalization claim. No Web replacement for CLI/client execution. No summary footer service startup. No Web-triggered agent task execution. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
