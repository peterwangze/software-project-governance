# Rollback Plan - 0.65.1

**Version**: 0.65.1 (patch)
**Release**: Evidence trust + post-0.65.0 hotfix closure (FIX-187/FIX-188/FIX-190/AUDIT-132/RISK-041)
**Date**: 2026-07-11

## Rollback Triggers

| Trigger | Severity | Detection | Action |
| --- | --- | --- | --- |
| Version declaration drift | High | `check-version-consistency` reports a non-WARN mismatch | Revert or correct missed 0.65.1 declaration file, then rerun consistency check. |
| Projection drift | High | `check-projection-sync` fails | Re-align source/target fixture pointers without modifying `.governance/**` runtime records. |
| `--project-root` override reads the wrong host facts | Critical | Explicit host fixture shows cwd governance facts instead of requested host root | Revert FIX-188 verify_workflow override block or patch host-path rebinding; rerun project-root regression tests before release. |
| Hook accepts non-approved review statuses | Critical | `NEEDS_CHANGES` / `BLOCKED` review evidence bypasses hooks | Revert hook regex widening and restore strict approved-only matching; add regression test before release. |
| 0.65.0 evidence correction accidentally claims archive PASS | High | Release docs/session references state `check-archive-integrity` was PASS for REL-053 | Correct documentation back to pre-existing FAIL / non-blocking P2; do not ship misleading evidence. |
| Release package claims tag, official approval, RISK closure, or 1.0.0 readiness | Critical | Checklist/changelog/rollback docs include overclaim | Remove overclaim before release; do not tag or publish until corrected and reviewed. |

## Rollback Steps

### Full rollback to 0.65.0 package state

1. Revert the 0.65.1 release-package diff.
2. Restore version declarations from 0.65.1 → 0.65.0 across source SKILL, manifest, plugin metadata, package.json, hooks, REQUIRED_SNIPPETS, and e2e fixture pointers.
3. Remove 0.65.1 release docs and CHANGELOG entry.
4. Rerun:
   - `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
   - `python skills/software-project-governance/infra/verify_workflow.py check-projection-sync`
   - `git diff --check`
5. Report rollback as a package-preparation rollback only; do not imply historical tag repair.

### Partial rollback: keep version bump, revert risky compatibility behavior

If only the hook or `--project-root` compatibility change regresses:

1. Revert the specific hook / `verify_workflow.py` compatibility block.
2. Keep the 0.65.1 version declarations only if CHANGELOG/release docs clearly state the narrowed scope.
3. Rerun hard-gate checks and obtain independent review before Coordinator records evidence.

## Reversibility

| Component | Reversible? | Method |
| --- | --- | --- |
| Version bump 0.65.0 → 0.65.1 | ✅ Yes | Mechanical edit across declaration files and fixture pointers. |
| `verify_workflow.py --project-root` compatibility | ✅ Yes | Revert override parsing/rebinding block. |
| Hook `APPROVED_WITH_NOTES` recognition | ✅ Yes | Revert regex widening in source hooks. |
| 0.65.0 evidence correction docs | ✅ Yes, but should not be undone without contrary evidence | Restore only if authoritative release evidence proves archive integrity was PASS. Current boundary is FAIL/non-blocking P2. |
| AUDIT-132 / RISK-041 release-lineage boundary | ✅ Documentation-level | Remove from 0.65.1 only if another release owns the boundary explicitly. |

## No-overclaim boundaries

No git tag created. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036/RISK-037/RISK-039/RISK-040/RISK-041 closure. No 1.0.0 readiness. This rollback plan covers release-package preparation; it does not repair historical missing tags or release-lineage gaps.
