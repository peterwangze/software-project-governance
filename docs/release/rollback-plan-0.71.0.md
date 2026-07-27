# Rollback Plan - 0.71.0

**Version**: 0.71.0 (minor)
**Release**: systematic UX fixes for entry/loop/task-planning (FIX-222~229) — bootstrap entry determinism + behavior protocol dependency-aware recommendation + review deterministic triggers + task planning system
**Date**: 2026-07-27
**Candidate parent (B)**: `da1ac77` (FIX-225~229 task planning system commit, on top of `f81060a` FIX-222~224 and `c069d89` docs)
**Decision**: FIX-222~229 (REL-063, user authorized)

## Rollback Triggers

| Trigger | Detection | Action |
| --- | --- | --- |
| Version declaration drift | `check-version-consistency` fails | Restore all 0.71.0 declarations and fixture pointers to the previous package state. |
| Release docs boundary regression | `check-release` reports a missing `boundary_needles` token or a forbidden release docs overclaim for 0.71.0 | Restore the proven compact negation wording in all three 0.71.0 release docs before release. |
| Boundary wording verbose enough to break negation | `_line_has_scoped_claim_negation` returns False for a scoped claim phrase | Use the compact template wording; do not reintroduce verbose phrasing. |
| task-priority-analysis regresses | `task_priority.py` 57 tests fail, or DAG parsing / unblocked computation / cycle detection breaks | Stop release; restore the pre-fix `task_priority.py` and re-confirm 57 tests PASS before re-release. |
| Bootstrap entry resolution regresses | AGENTS.md 3-method plugin_home location no longer resolves on a supported platform, or `<plugin_home>` chicken-and-egg reappears | Stop release; restore the FIX-222 3-method bootstrap prose and re-confirm entry resolution. |
| Behavior-protocol dependency recommendation regresses | M7.4 step 6 / interaction-boundary.md:217 revert to mechanical highest-priority, or task-completion ends without dependency analysis + AskUserQuestion | Stop release; restore the FIX-223/227 dependency-aware recommendation prose. |
| Review deterministic triggers regressed | M7.4 step 4.6 T1-T4 no longer enforce deterministic re-review/terminal/escalation | Stop release; restore the FIX-224 T1-T4 deterministic trigger prose. |
| Candidate mode incorrectly requires or proves a tag | Candidate release check reports tag existence as required/proven | Revert the candidate and stop release review. |
| Released mode admits missing or mismatched lineage | Local/remote tag or explicit commit mismatch is not rejected | Stop release; do not move an already published tag. |
| Historical tags are created without a decision | `git tag` shows new historical tags without an approved mapping decision | Stop release and remove only the unauthorized local/remote tag action through the Coordinator's governed recovery process. |

## Full Candidate Rollback to 0.70.0

1. Revert the 0.71.0 release-package change (version projection + CHANGELOG + release docs + candidate manifest). The FIX-222~229 code commits are the candidate parent B and remain intact as the code base; only the release packaging reverts.
2. Restore version declarations from 0.71.0 to 0.70.0 across source SKILL, manifest, plugin/marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, and e2e fixture pointers.
3. Remove the 0.71.0 CHANGELOG entry and the three 0.71.0 release documents.
4. Rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.
5. Confirm `v0.70.0` still resolves locally and remotely to the 0.70.0 released commit.

## Released-State Recovery

If `v0.71.0` was created but released lineage fails, stop publication immediately. Determine whether the release commit or tag operation is wrong; do not move an already published tag silently. Any remote tag correction is an irreversible release action requiring Coordinator governance and explicit evidence. Restore the 0.70.0 package for users until a corrected release receives review.

## Reversibility

| Component | Reversible | Method |
| --- | --- | --- |
| Version declaration sync and release docs | Yes | Revert the release-package commit. |
| Release docs boundary wording | Yes | Revert the docs files, but keep the compact wording; do not reintroduce verbose phrasing that fails the negation gate. |
| task-priority-analysis (FIX-226) | Governed | Restore the pre-fix `task_priority.py` and CLI entry; re-confirm 57 tests PASS before re-release. |
| Bootstrap entry / behavior-protocol / change-control prose (FIX-222/223/224/227/228/229) | Governed | Restore the pre-fix governance-record prose; re-confirm the documented resolution path before re-release. |
| plan-tracker 依赖 column (FIX-225) | Governed | Restore the pre-fix template; re-confirm dependency format before re-release. |
| Published remote tag | Not treated as routine reversible state | Governed recovery only; never silently retarget. |
| Historical missing tags | Not changed | No rollback action. |

## Validation After Rollback

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.71.0 --require-changelog --lineage-mode candidate
git diff --check
```

## No-overclaim Boundaries

This plan does not authorize historical tag backfill and does not close RISK-036, RISK-039, RISK-040, or RISK-041. 0.71.0 does not close RISK-036/RISK-039/RISK-040/RISK-041 (official marketplace operations, ArchGuard external validation, entry determinism host validation, and release-lineage historical-tag disposition each have independent closure criteria not yet satisfied). It claims no official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039/RISK-040/RISK-041 closure, or 1.0.0 production-ready status.
