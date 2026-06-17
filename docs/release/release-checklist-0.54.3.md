# Release Checklist - 0.54.3

**Version**: 0.54.3

**Release theme**: REL-038 governance same-package skill fast-start hotfix

## Checklist

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Semver patch scope is preserved | PASS | 0.54.3 packages reviewed FIX-144 only and does not add Dynamic Lifecycle runtime migration |
| 2 | FIX-144 same-package skill fast-start is the only release scope | PASS | Release package covers `/governance` command contract, target fixture sync, and regression tests for the empty-env startup bug |
| 3 | Loaded plugin path is first-class | PASS | `/governance` now uses the same loaded plugin package's `skills/software-project-governance` skill before any repo-local or diagnostic fallback |
| 4 | Environment variables are diagnostic fallback only | PASS | `SOFTWARE_PROJECT_GOVERNANCE_HOME`, `SPG_HOME`, and `WORKFLOW_HOME` are not fast-start prerequisites |
| 5 | LLM path search is blocked on the default entry path | PASS | The command contract says the agent must not search the repo or load `SKILL.md` to discover the default entry when the command came from a loaded plugin |
| 6 | Regression coverage is referenced | PASS | GovernanceFastStart 4/4, fast-start JSON, projection sync, e2e-check, cross-reference, manifest, governance health, py_compile, diff check, and Code Reviewer Avicenna APPROVED are recorded in FIX-144 evidence |
| 7 | User update path is versioned | PASS | 0.54.3 bumps plugin metadata and release tag so users can update without waiting for 0.55.0 external validation |
| 8 | 0.55.0 Dynamic Lifecycle planning remains unchanged | PASS | 0.54.3 does not migrate projects, does not alter external validation scope, and does not change dynamic-flow-gate default status |
| 9 | 0.54.3 release docs are present and manifest-covered | PASS | `release-checklist-0.54.3.md`, `feature-flags-0.54.3.md`, and `rollback-plan-0.54.3.md` are listed in `core/manifest.json` |
| 10 | Version declarations are synchronized | PASS | Source SKILL, canonical manifest, Claude/Codex plugin metadata, Claude marketplace metadata, hook `@version`, target fixture skill/plan, CHANGELOG, README, and REQUIRED_SNIPPETS are 0.54.3 |
| 11 | 0.54.3 release gate is documented | PASS | Coordinator should run `check-release --version 0.54.3 --require-changelog --runtime-adapters` after this package is prepared |
| 12 | RISK-036 remains open | PASS | 0.54.3 does not claim official approval, marketplace approval, two real external projects full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready |
| 13 | RISK-037 remains open | PASS | 0.54.3 is a fast-start hotfix only and does not claim project migration, external validation closure, dynamic-flow-gate default, or dynamic lifecycle readiness |

## Release Boundary

0.54.3 packages the governance same-package skill fast-start scope for FIX-144. It is a semver patch over 0.54.2 and makes the corrected `/governance` entry model available to users through normal plugin update flows.

The release includes:

- version declarations for the 0.54.3 patch package;
- release docs and README/changelog boundary text for FIX-144;
- manifest coverage for 0.54.3 release docs;
- hook `@version` metadata synchronized to 0.54.3;
- target fixture and validator release/version snippets synchronized to 0.54.3;
- documentation that loaded plugin command execution should use the same plugin package's governance skill first;
- documentation that env vars are repo-local/dev/diagnostic fallback only.

The release excludes:

- changes to FIX-144 implementation logic beyond release metadata and release docs;
- changes to 0.55.0 Dynamic Lifecycle migration/external validation planning;
- project migration;
- `dynamic-flow-gate` as default;
- registry automation command execution changes;
- official approval, marketplace approval, external validation full PASS, Codex Desktop lifecycle PASS, project migration, or 1.0.0 readiness;
- RISK-036 or RISK-037 closure.

## Coordinator Release Gate Commands

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -k GovernanceFastStart -v
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.54.3 --require-changelog --runtime-adapters
git diff --check
```

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No registry automation command execution change. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
