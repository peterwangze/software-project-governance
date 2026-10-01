# Rollback Plan - 0.65.3

**Version**: 0.65.3 (patch)
**Release**: release lineage/tag gate and marketplace source facts (FIX-192)
**Date**: 2026-07-11

## Rollback Triggers

| Trigger | Detection | Action |
| --- | --- | --- |
| Version declaration drift | `check-version-consistency` fails | Restore all 0.65.3 declarations and fixture pointers to the previous package state. |
| Projection drift | `check-projection-sync` fails | Restore source/projection pairs from 0.65.2 and rerun the check. |
| Candidate mode incorrectly requires or proves a tag | Candidate release check reports tag existence as required/proven | Revert the FIX-192 lineage change and stop release review. |
| Released mode admits missing or mismatched lineage | Local/remote tag or explicit commit mismatch is not rejected | Revert FIX-192 as one unit and retain 0.65.2 pending correction. |
| Remote query is unsafe or interactive | URL/userinfo/option-like input reaches Git, prompts occur, timeout is absent, or credentials appear in diagnostics | Revert the remote-lineage implementation and stop release. |
| Marketplace source facts regress | Docs claim direct git URL support, zcode official approval, or confuse remote metadata with plugin source | Correct or revert the release package before review. |
| Historical tags are created without a decision | `git tag` shows new 0.63.0~0.65.0 tags without an approved mapping decision | Stop release and remove only the unauthorized local/remote tag action through the Coordinator's governed recovery process. |

## Full Candidate Rollback to 0.65.2

1. Revert the 0.65.3 release-package change and, if the lineage implementation itself must be withdrawn, revert FIX-192 commit `1c734c7` as a separate auditable revert.
2. Restore version declarations from 0.65.3 to 0.65.2 across source SKILL, manifest, plugin/marketplace metadata, package.json, four source hooks, and e2e fixture pointers.
3. Remove the 0.65.3 CHANGELOG entry and the three 0.65.3 release documents. Retain audit/source-matrix evidence only when FIX-192 remains part of repository history.
4. Rerun version consistency, projection sync, hot-fact-source, archive integrity, `verify`, and `git diff --check`.
5. Confirm `v0.65.2` still resolves locally and remotely to `073c2c07251b87b8e7d309be8d527770847c24b6`.

## Released-State Recovery

If `v0.65.3` was created but released lineage fails, stop publication immediately. Determine whether the release commit or tag operation is wrong; do not move an already published tag silently. Any remote tag correction is an irreversible release action requiring Coordinator governance and explicit evidence. Restore the 0.65.2 package for users until a corrected release receives review.

## Reversibility

| Component | Reversible | Method |
| --- | --- | --- |
| Version declaration sync and release docs | Yes | Revert the release-package commit. |
| Candidate/released lineage implementation | Yes | Revert FIX-192 as one cohesive change, then rerun focused checks. |
| Audit and source matrix | Yes as repository files | Revert files without rewriting observed Git history. |
| Published remote tag | Not treated as routine reversible state | Governed recovery only; never silently retarget. |
| Historical missing tags | Not changed | No rollback action; RISK-041 remains open. |

## Validation After Rollback

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync
python skills/software-project-governance/infra/verify_workflow.py check-hot-fact-source --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-archive-integrity
python skills/software-project-governance/infra/verify_workflow.py verify
git diff --check
```

## No-overclaim Boundaries

This plan does not authorize historical tag backfill and does not close RISK-039 or RISK-041. It claims no official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-037/RISK-040 closure, or 1.0.0 production-ready status.
