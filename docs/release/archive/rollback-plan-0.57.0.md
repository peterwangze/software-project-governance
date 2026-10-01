# Rollback Plan - 0.57.0

**Version**: 0.57.0

Rollback is required if the 0.57.0 release package claims official/marketplace approval, universal runtime support, implements ArchGuard, modifies `verify_workflow.py` functional code, splits any module, introduces lint/type infrastructure, closes RISK-036/RISK-037/RISK-039, or overclaims 1.0.0 readiness. Because 0.57.0 is a documentation/governance-only release with no functional code change, rollback is a straightforward revert to 0.56.1.

## Triggers

- `check-release --version 0.57.0 --require-changelog --runtime-adapters` fails.
- `check-version-consistency` reports a 0.57.0 declaration mismatch.
- `check-manifest-consistency --fail-on-issues` reports missing 0.57.0 release docs coverage.
- `check-governance --fail-on-issues` reports a release boundary, evidence, or risk posture issue.
- README, CHANGELOG, release docs, manifests, or validator output claim official approval, marketplace approval, universal/full runtime support, external validation full PASS, ArchGuard implementation, `verify_workflow.py` split, modern engineering infrastructure, RISK-036/RISK-037/RISK-039 closure, or 1.0.0 readiness.
- The release accidentally modifies `verify_workflow.py` functional code beyond the version-string assertions in `REQUIRED_SNIPPETS`.

## Steps

1. Revert the 0.57.0 release package commit after it exists:

```bash
git revert <0.57.0-release-package-commit>
```

2. Re-run the previous release gate:

```bash
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.56.1 --require-changelog --runtime-adapters
```

3. Re-prepare 0.57.0 with the documentation-only/no-overclaim boundary before retrying.

## Verification After Rollback

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-release --version 1.0.0 --require-changelog --runtime-adapters
git diff --check
```

The 1.0.0 command must continue to fail with explicit blockers until final evidence and RISK-036/RISK-037/RISK-039 closure criteria are satisfied.

## No-Overclaim Boundary

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No completed non-game preset generalization claim. No Web replacement for CLI/client execution. No Web-triggered agent task execution. No ArchGuard implementation. No `verify_workflow.py` split. No modern engineering infrastructure (lint/type/package). No docs/release archive mechanism. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness.

RISK-036 remains open. RISK-037 remains open. RISK-039 remains open.
