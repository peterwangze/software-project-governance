# Release Checklist - 0.65.3

**Version**: 0.65.3 (patch)
**Release**: release lineage/tag gate and marketplace source facts (FIX-192, SYSGAP-046)
**Date**: 2026-07-11

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined | PASS - 0.65.3 PATCH |
| 2 | Change list enumerated | PASS - FIX-192, lineage audit, source matrix, backfilled markers, metadata synchronization |
| 3 | Independent code review available | PASS - `REVIEW-FIX-192-R2`, `APPROVED`, `unresolved_blockers=0` |
| 4 | Candidate lineage boundary explicit | PASS - candidate mode does not require or prove a tag |
| 5 | Historical tag and official-marketplace overclaims excluded | PASS |

### Included

- `check-release` candidate/released lineage modes.
- Released-mode validation of explicit release commit, local tag, configured remote tag, and matching commit identity under `HOST_PROJECT_ROOT`.
- Safe remote-name validation, remote existence check, 15-second timeout, non-interactive Git, and diagnostics that do not echo credential-bearing input.
- 0.62.0~0.65.2 lineage audit. The 0.62.0~0.63.4 release checklist, feature flags, and rollback plan files are 18/18 marked `BACKFILLED`.
- Marketplace source matrix for local add/install, offline package, remote marketplace clone/add with `source: "./"`, and unsupported direct git URL installation.
- Version declarations and e2e fixture pointers advance from 0.65.2 to 0.65.3.

### Excluded

- No historical tag creation or backfill. The missing 0.63.0~0.65.0 tags require a separate governance decision approving version-to-commit mappings.
- No complete declarative release ledger; that remains FEAT-001 / 0.66.0 scope.
- No zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-037/RISK-039/RISK-040/RISK-041 closure, or 1.0.0 production-ready claim.

## 2. Version and SemVer

0.65.3 is a PATCH because it repairs release verification and packaging facts without changing plugin runtime APIs or introducing a breaking contract. Expected declarations are 0.65.3 in source SKILL, manifest, Claude/Codex/Zcode/Chrys plugin metadata, Claude marketplace metadata, package.json, four source hooks, and the two e2e fixture pointers.

## 3. Candidate Validation

Run before release review:

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync
python skills/software-project-governance/infra/verify_workflow.py check-hot-fact-source --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-archive-integrity
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.65.3 --require-changelog --skip-execution-gates --lineage-mode candidate
python skills/software-project-governance/infra/verify_workflow.py verify
git diff --check
```

Candidate mode intentionally does not require `v0.65.3` and is not evidence that the tag exists. The final release commit, local tag, and remote tag do not yet exist during package preparation. After the Coordinator creates and pushes them, rerun:

```text
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.65.3 --require-changelog --skip-execution-gates --lineage-mode released --release-commit <commit>
```

## 4. Test and Review Evidence

- FIX-192 focused tests: 53/53 PASS.
- Full unit suite: 609/610. The one failure is the existing Check 13 fixture isolation boundary; this package does not claim full-suite green.
- Review R0/R1 returned `NEEDS_CHANGE`; R2 is `APPROVED`, `unresolved_blockers=0` after source/direct-URL/timeout and credential diagnostic fixes.
- Candidate release checks must report tracked/staged-file conditions and any existing governance or archive issue honestly; package preparation does not convert them into PASS.

## 5. Release Decision Boundary

This checklist prepares a candidate only. It does not commit, tag, push, approve marketplace submission, close risk, or make the final go/no-go decision. Independent Release Review is required before release execution. After tag creation and push, released lineage must verify the exact release commit locally and on the configured remote.

## 6. Rollback Verification

`docs/release/rollback-plan-0.65.3.md` defines full and partial rollback paths. After rollback, rerun version consistency, projection sync, hot-fact-source, archive integrity, the applicable candidate/released lineage check, `verify`, and `git diff --check`.
