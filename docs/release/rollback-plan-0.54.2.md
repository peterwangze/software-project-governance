# Rollback Plan - 0.54.2

**Version**: 0.54.2

Rollback is required if the REL-037 release package regresses the deterministic `/governance` fast-start path, restores default long skill loading for Scenario F/status/resume, changes 0.55.0 Dynamic Lifecycle migration/external validation planning, migrates projects, makes `dynamic-flow-gate` default, changes registry automation command execution, changes the release boundary for RISK-036/RISK-037, or overclaims official approval, marketplace status, external validation full PASS, Codex Desktop lifecycle PASS, project migration, or 1.0.0 readiness.

## Triggers

- `check-release --version 0.54.2 --require-changelog --runtime-adapters` fails.
- `check-version-consistency` reports a 0.54.2 declaration mismatch.
- `check-manifest-consistency --fail-on-issues` reports missing 0.54.2 release docs coverage.
- `check-governance --fail-on-issues` reports a release boundary, evidence, or risk posture issue.
- `/governance` default status/resume path requires LLM search or default loading of `skills/software-project-governance/SKILL.md`.
- `governance-fast-start --json` stops returning `full_skill_load_required=false` for existing governance status.
- 0.55.0 migration/external validation planning changes.
- `dynamic-flow-gate` becomes active/default in 0.54.2.
- Registry automation command execution behavior changes.
- Projects are migrated automatically.
- README, CHANGELOG, release docs, manifests, or validator output claim official approval, marketplace approval, universal/full runtime support, external validation full PASS for two real projects, external first-session pilot success, Codex Desktop marketplace-management E2E PASS, Desktop lifecycle E2E PASS, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, project migration, dynamic-flow-gate default, RISK-036 closure, RISK-037 closure, or 1.0.0 production-ready.

## Steps

1. Revert the 0.54.2 package commit after it exists:

```bash
git revert <0.54.2-release-package-commit>
```

2. Re-run the previous release gate:

```bash
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.54.1 --require-changelog --runtime-adapters
```

3. Re-prepare 0.54.2 with the FIX-143 fast-start UX patch and no-overclaim boundary below before retrying REL-037.

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

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No registry automation command execution change. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
