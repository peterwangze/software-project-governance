# Rollback Plan - 0.52.0

**Version**: 0.52.0

Rollback is required if the REL-032 release package activates declarative gate behavior, migrates projects, makes `dynamic-flow-gate` default, changes classic G1-G11 behavior, closes RISK-036/RISK-037 without evidence, or overclaims official approval, marketplace status, external validation full PASS, Codex Desktop lifecycle PASS, or 1.0.0 readiness.

## Triggers

- `check-release --version 0.52.0 --require-changelog --runtime-adapters` fails.
- `check-version-consistency` reports a 0.52.0 declaration mismatch.
- `check-manifest-consistency --fail-on-issues` reports missing 0.52.0 release docs coverage.
- `check-flow-unit-runtime --fail-on-issues` reports invalid hot-state handling or no-overclaim drift.
- `check-lifecycle-registry --fail-on-issues` reports classic compatibility or dynamic-flow-gate default drift.
- `classic-phase-gate` is no longer active/default.
- `dynamic-flow-gate` becomes active/default in 0.52.0.
- Declarative gate engine behavior is activated.
- Projects are migrated automatically.
- README, CHANGELOG, release docs, manifests, or validator output claim official approval, marketplace approval, universal/full runtime support, external validation full PASS for two real projects, external first-session pilot success, Codex Desktop marketplace-management E2E PASS, Desktop lifecycle E2E PASS, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, RISK-036 closure, RISK-037 closure, or 1.0.0 production-ready.

## Steps

1. Revert the 0.52.0 package commit after it exists:

```bash
git revert <0.52.0-release-package-commit>
```

2. Re-run the previous release gate:

```bash
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.51.0 --require-changelog --runtime-adapters
```

3. Re-prepare 0.52.0 with the visibility-only and no-overclaim boundary below before retrying REL-032.

## Verification After Rollback

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-lifecycle-registry --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-flow-unit-runtime --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-release --version 1.0.0 --require-changelog --runtime-adapters
git diff --check
```

The 1.0.0 command must continue to fail with explicit blockers until final evidence and RISK-036/RISK-037 closure criteria are satisfied.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No declarative gate engine activation. No project migration. No dynamic-flow-gate default. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
