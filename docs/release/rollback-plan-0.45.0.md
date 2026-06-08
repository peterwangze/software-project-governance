# Rollback Plan - 0.45.0

**Version**: 0.45.0
**Scope**: REL-022 release package for Governance Eval & Benchmark + Capability Discovery

## Rollback Triggers

- `check-version-consistency` fails after the release package is prepared.
- `check-release --version 0.45.0 --require-changelog --runtime-adapters` fails locally or in a clean checkout.
- Full unit tests fail after the release package is prepared.
- `check-governance --fail-on-issues` or `check-manifest-consistency --fail-on-issues` fails.
- Version declarations drift between source SKILL, canonical manifest, Claude/Codex plugin manifests, marketplace metadata, governance packs, capability registry, target fixture, or hook @version.
- Release docs, CHANGELOG, or requirement reports contain positive claims for any item in the no-overclaim boundary below.
- `docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md` is missing the result matrix, marks real Desktop lifecycle steps PASS without real Desktop evidence, or omits the blocked evidence boundary.
- The release package mixes in 0.46.0 official submission materials, 1.0.0 production-ready changes, or unrelated product refactors.

## Rollback Steps

1. Revert the 0.45.0 release package commit after it exists:

```bash
git revert <0.45.0-release-package-commit>
```

2. If tag `v0.45.0` has been created and must be withdrawn:

```bash
git tag -d v0.45.0
git push origin :refs/tags/v0.45.0
```

3. Re-run the previous release baseline checks:

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.44.1 --require-changelog --runtime-adapters
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues
git diff --check
```

4. If the issue is only release wording, revert the package and prepare a corrected conservative release package. Do not keep partial 0.45.0 version declarations while reverting only docs, because version consistency and projection sync would drift.

## Data Boundary

`.governance/` is runtime governance state and is not modified by this release package. Rollback only touches versioned product and release package files.

## Risk Boundary

Rollback does not close RISK-036. RISK-036 remains open until official submission materials, external validation, direct Codex Desktop marketplace-management lifecycle evidence or conservative blocked carry-forward, and capability selection evidence are all handled without overclaiming.

## No-Overclaim Boundary

- No official approval.
- No marketplace approval.
- No universal/full runtime support.
- No external first-session pilot success.
- No Codex Desktop marketplace-management E2E PASS.
- No automatic best-tool selection.
- No universal plugin/skill/tool availability.
- No catalog entry runtime PASS.
- No RISK-036 closure.
- No 1.0.0 production-ready claim.
