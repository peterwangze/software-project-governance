# Rollback Plan - 0.65.2

**Version**: 0.65.2 (patch)
**Release**: SKILL Loop Role and Check 30 review-closure consistency repair (FIX-191, FIX-193)
**Date**: 2026-07-11

## Rollback Triggers

| Trigger | Detection | Action |
| --- | --- | --- |
| Version declaration drift | `check-version-consistency` fails | Restore every 0.65.2 declaration and fixture pointer to the release commit's previous version, then rerun the check. |
| Projection drift | `check-projection-sync` fails | Restore the source/projection pair from the previous package state, then rerun the check. |
| Loop Role guidance is incomplete or misleading | `check-loop-role-skills` fails or review finds a broken mapping/semantic requirement | Revert FIX-191 guidance and validation changes as one unit; do not patch the loop runtime. |
| Reviewer role boundary regresses | A review SKILL authorizes direct code edits or omits terminal handling | Revert the affected FIX-191 SKILL change and rerun its focused consistency test. |
| Four-state closure gate admits unresolved blockers | `APPROVED_WITH_NOTES` passes with missing, non-zero, invalid, duplicate, or contradictory `unresolved_blockers` evidence | Revert FIX-193 as one protocol unit and restore the previous fail-closed release boundary pending a corrected implementation. |
| Review status semantics diverge again | Check 30, M7.4, routing, mapping, or any review SKILL assigns different outcomes to APPROVED / APPROVED_WITH_NOTES / BLOCKED / NEEDS_CHANGE(S) | Revert the inconsistent FIX-193 slice and rerun the complete focused closure matrix. |
| Release documents overclaim gate health | Any 0.65.2 document states archive integrity, 43 other governance health issues, unverified full-suite health, risk closure, historical tag repair, or zcode official approval as resolved | Correct or revert the release document before release review. |

## Rollback Steps

### Full package rollback to 0.65.1

1. Revert the 0.65.2 release-package commit and the `FIX-191` / `FIX-193` product changes if the guidance or closure protocol must be withdrawn.
2. Restore version declarations from 0.65.2 to 0.65.1 across source SKILL, manifest, plugin metadata, marketplace metadata, package.json, all four source hooks, and e2e fixture pointers.
3. Remove the 0.65.2 CHANGELOG entry and the three 0.65.2 release documents.
4. Rerun:
   - `python skills/software-project-governance/infra/verify_workflow.py check-version-consistency`
   - `python skills/software-project-governance/infra/verify_workflow.py check-projection-sync`
   - `python skills/software-project-governance/infra/verify_workflow.py check-loop-role-skills`
   - `git diff --check`
5. Record the rollback result as a package rollback. Do not imply repair of historical release tags or release-lineage gaps.

### Partial rollback: retain package version, withdraw guidance change

1. Revert the affected `FIX-191` guidance slice or the complete `FIX-193` state-machine/protocol slice. Do not leave Check 30, M7.4, mapping, routing, or review SKILLs on mixed semantics.
2. Update CHANGELOG and release documents to describe the narrowed scope or do not release 0.65.2.
3. Treat the seven migrated historical blocker markers as retained governance evidence unless an explicit evidence correction proves they are wrong; do not silently delete them during product rollback.
4. Obtain a fresh independent review before any release decision.

## Reversibility and Limits

| Component | Reversible | Method |
| --- | --- | --- |
| Version declaration sync | Yes | Mechanical restore of the declaration files and fixture pointers. |
| Loop Role guidance and validator | Yes | Revert `FIX-191` as a cohesive change. |
| Four-state review closure and blocker gate | Yes | Revert `FIX-193` as a cohesive protocol change, then rerun Check 30 and focused closure tests. |
| Loop runtime and migration data | Not changed | No runtime or data rollback is required for this release. |
| Archive trigger gap, 43 governance health issues, and unverified full-suite state | Not resolved here | Remain known conditions; this plan does not misrepresent them as repaired. |

## No-overclaim Boundaries

This plan does not create, repair, or backfill any historical tag. It does not claim official approval, zcode official marketplace approval, universal/full runtime support, external first-session pilot success, RISK-036/RISK-037/RISK-039/RISK-040/RISK-041 closure, or 1.0.0 readiness.
