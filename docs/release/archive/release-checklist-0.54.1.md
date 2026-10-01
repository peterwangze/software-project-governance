# Release Checklist - 0.54.1

**Version**: 0.54.1

**Release theme**: REL-036 governance hook nested plugin hotfix release

## Checklist

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Semver patch scope is preserved | PASS | 0.54.1 packages reviewed FIX-140 hook metadata only and does not add new runtime features |
| 2 | FIX-140 hook hotfix is the only release scope | PASS | Release package covers nested plugin product path detection and dated evidence row matching |
| 3 | Product hook logic remains unchanged in REL-036 | PASS | Release work only bumps hook `@version` strings; FIX-140 implementation logic was already completed and reviewed |
| 4 | Nested plugin product path boundary is documented | PASS | 0.54.1 records that product path detection covers root product paths and nested plugin/workflow product paths while excluding `.governance/**` |
| 5 | Dated evidence row matching boundary is documented | PASS | 0.54.1 records support for both `EVD | TASK_ID` and `EVD | date | TASK_ID` evidence rows |
| 6 | FIX-140 regression evidence is referenced | PASS | FIX-140 evidence records CommitMsg focused 8/8, CommitMessageSourceHardening 12/12, and `git diff --check` PASS |
| 7 | 0.55.0 Dynamic Lifecycle planning remains unchanged | PASS | 0.54.1 does not migrate projects, does not alter external validation scope, and does not change dynamic-flow-gate default status |
| 8 | 0.54.1 release docs are present and manifest-covered | PASS | `release-checklist-0.54.1.md`, `feature-flags-0.54.1.md`, and `rollback-plan-0.54.1.md` are listed in `core/manifest.json` |
| 9 | Version declarations are synchronized | PASS | Source SKILL, canonical manifest, Claude/Codex plugin metadata, Claude marketplace metadata, hook `@version`, target fixture skill/plan, CHANGELOG, README, and REQUIRED_SNIPPETS are 0.54.1 |
| 10 | 0.54.1 release gate is documented | PASS | Coordinator should run `check-release --version 0.54.1 --require-changelog --runtime-adapters` after this package is prepared |
| 11 | RISK-036 remains open | PASS | 0.54.1 does not claim official approval, marketplace approval, two real external projects full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready |
| 12 | RISK-037 remains open | PASS | 0.54.1 is a hook hotfix package only and does not claim project migration, external validation closure, dynamic-flow-gate default, or dynamic lifecycle readiness |

## Release Boundary

0.54.1 packages the governance hook hotfix scope for FIX-140. It is a semver patch over 0.54.0 and versions already completed/reviewed hook behavior without modifying hook implementation logic during REL-036.

The release includes:

- version declarations for the 0.54.1 patch package;
- release docs and README/changelog boundary text for FIX-140;
- manifest coverage for 0.54.1 release docs;
- hook `@version` metadata synchronized to 0.54.1;
- target fixture and validator release/version snippets synchronized to 0.54.1;
- documentation of nested plugin/workflow product path detection and dated evidence row matching as FIX-140 scope.

The release excludes:

- changes to the hook repair logic itself beyond release metadata strings;
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
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.54.1 --require-changelog --runtime-adapters
git diff --check
```

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No registry automation command execution change. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
