# Rollback Plan - 0.54.3

**Version**: 0.54.3

Rollback is required if the REL-038 release package regresses the corrected `/governance` same-package skill fast-start path, restores environment variables as loaded-plugin startup prerequisites, restores default LLM path search for the command entry, changes 0.55.0 Dynamic Lifecycle migration/external validation planning, migrates projects, makes `dynamic-flow-gate` default, changes registry automation command execution, changes the release boundary for RISK-036/RISK-037, or overclaims official approval, marketplace status, external validation full PASS, Codex Desktop lifecycle PASS, project migration, or 1.0.0 readiness.

## Triggers

- `check-release --version 0.54.3 --require-changelog --runtime-adapters` fails.
- `check-version-consistency` reports a 0.54.3 declaration mismatch.
- `check-manifest-consistency --fail-on-issues` reports missing 0.54.3 release docs coverage.
- `check-governance --fail-on-issues` reports a release boundary, evidence, or risk posture issue.
- `/governance` default loaded-plugin path requires `SOFTWARE_PROJECT_GOVERNANCE_HOME`, `SPG_HOME`, or `WORKFLOW_HOME`.
- `/governance` default loaded-plugin path searches the repo or loads `SKILL.md` to discover an entry path before running fast-start.
- `governance-fast-start --json` stops returning `full_skill_load_required=false` for existing governance status.
- 0.55.0 migration/external validation planning changes.
- `dynamic-flow-gate` becomes active/default in 0.54.3.
- Registry automation command execution behavior changes.
- Projects are migrated automatically.
- README, CHANGELOG, release docs, manifests, or validator output claim official approval, marketplace approval, universal/full runtime support, external validation full PASS for two real projects, external first-session pilot success, Codex Desktop marketplace-management E2E PASS, Desktop lifecycle E2E PASS, automatic best-tool selection, universal plugin/skill/tool availability, catalog entry runtime PASS, project migration, dynamic-flow-gate default, RISK-036 closure, RISK-037 closure, or 1.0.0 production-ready.

## Steps

1. Revert the 0.54.3 package commit after it exists:

```bash
git revert <0.54.3-release-package-commit>
```

2. Re-run the previous release gate:

```bash
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.54.2 --require-changelog --runtime-adapters
```

3. Re-prepare 0.54.3 with the FIX-144 same-package skill fast-start hotfix and no-overclaim boundary below before retrying REL-038.

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
