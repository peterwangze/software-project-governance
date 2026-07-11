# Release Checklist - 0.65.2

**Version**: 0.65.2 (patch)
**Release**: SKILL Loop Role consistency and Check 30 review-closure repair (FIX-191, FIX-193)
**Date**: 2026-07-11

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined | PASS - 0.65.2 PATCH |
| 2 | Change list enumerated | PASS - FIX-191, FIX-193, and release metadata synchronization |
| 3 | Scope excludes loop runtime, lineage, and migration changes | PASS |
| 4 | Independent code review available | FIX-191: PASS WITH NOTES - `REVIEW-FIX-191-R0`, `unresolved_blockers=0`; FIX-193: PASS - `REVIEW-FIX-193-R3` |
| 5 | Out-of-scope items explicit | PASS |

### Included

- Seven review SKILLs use the stable Chinese Loop Role heading and place version context in body text.
- Mapping references and failure-to-loop/fuse, reviewer-no-edit, and Check 30 terminal semantics are explicit.
- `check-loop-role-skills` provides fail-closed consistency validation with focused positive and negative tests.
- Check 30, M7.4, Agent communication/routing, the shared mapping, and all seven review SKILLs use the same four-state protocol.
- `APPROVED_WITH_NOTES` passes only with a unique, non-contradictory structured `unresolved_blockers=0`; non-zero, missing, invalid, or contradictory blocker evidence fails closed.
- `APPROVED` remains compatible; `BLOCKED` closes the review chain without passing it; `NEEDS_CHANGE(S)`, unknown, and malformed evidence fail closed.
- Seven historical `APPROVED_WITH_NOTES` evidence markers were migrated with structured `unresolved_blockers=0` facts.
- All version declarations and e2e fixture pointers advance from 0.65.1 to 0.65.2.

### Excluded

- No loop runtime behavior, fuse threshold, state derivation, or migration data-format change.
- No 0.65.3 release-lineage/tag mechanism, release ledger, or historical tag backfill.
- No zcode official marketplace approval claim and no closure of RISK-036, RISK-037, RISK-039, RISK-040, or RISK-041.

## 2. Version Consistency

| Item | Expected |
| --- | --- |
| Source SKILL frontmatter | 0.65.2 |
| Manifest | 0.65.2 |
| Claude/Codex/Zcode/Chrys plugin metadata | 0.65.2 |
| Claude marketplace metadata | 0.65.2 |
| package.json | 0.65.2 |
| Four source hooks `@version` | 0.65.2 |
| E2E fixture SKILL and plan-tracker pointer | 0.65.2 |

## 3. Required Validation

Run before release review and record exact outputs:

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync
python skills/software-project-governance/infra/verify_workflow.py check-hot-fact-source --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-loop-role-skills
git diff --check
```

Expected result: all five commands PASS for the release package.

## 4. Known Conditions and Release Decision

REL-055 R0 returned `NEEDS_CHANGE` because Check 30 and the surrounding review contracts disagreed about `APPROVED_WITH_NOTES`. FIX-193 closed that blocker through independent review rounds R0-R3; R3 is `APPROVED`, and live Check 30 is WARN with no V5/closure violations. This resolves the R0 finding but does not itself constitute a new Release Review approval for the revised package.

`check-release --version 0.65.2 --require-changelog --skip-execution-gates` must still be reported honestly. The existing archive trigger gap remains a failure. The other governance health findings remain at 43 issues and are outside this PATCH. A post-FIX-193 full unit-suite result has not been verified; focused results (CheckReviewClosureTests 17/17, R2 focused 19/19, Loop Role 7/7) must not be represented as full-suite PASS.

This checklist prepares a release package only. It does not itself create a commit, tag, push, marketplace submission, or release approval. An independent Release Reviewer must review the final package before the Coordinator performs a release decision.

No official approval, marketplace approval, universal/full runtime support, external first-session pilot success, RISK-036/RISK-037/RISK-039/RISK-040/RISK-041 closure, or 1.0.0 readiness is claimed.

## 5. Rollback Verification

The rollback plan at `docs/release/rollback-plan-0.65.2.md` defines a reversible Git rollback to the 0.65.1 package state. Re-run the five required validation commands after a rollback.
