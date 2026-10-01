# Rollback Plan - 0.66.3

**Version**: 0.66.3 (patch)
**Release**: docs-fix PATCH repairing 0.66.2 release docs content defects
**Date**: 2026-07-23
**Candidate parent (B)**: `f859bb6f662ecc187dc5f49ba20b077f5b35d882` (released v0.66.2)
**Decision**: DEC-131 (user decision "0.66.3 PATCH 修复 docs")

## Rollback Triggers

| Trigger | Detection | Action |
| --- | --- | --- |
| Version declaration drift | `check-version-consistency` fails | Restore all 0.66.3 declarations and fixture pointers to the previous package state. |
| Release docs boundary regression | `check-release` reports a missing `boundary_needles` token or a forbidden release docs overclaim for 0.66.3 | Restore the proven 0.65.3 compact boundary wording in all three 0.66.3 release docs before release. |
| Boundary wording verbose enough to break negation | `_line_has_scoped_claim_negation` returns False for a scoped claim phrase | Use the compact 0.65.3 template wording; do not reintroduce the verbose 0.66.2 phrasing. |
| Candidate mode incorrectly requires or proves a tag | Candidate release check reports tag existence as required/proven | Revert the candidate and stop release review. |
| Released mode admits missing or mismatched lineage | Local/remote tag or explicit commit mismatch is not rejected | Stop release; do not move an already published tag. |
| Historical tags are created without a decision | `git tag` shows new historical tags without an approved mapping decision | Stop release and remove only the unauthorized local/remote tag action through the Coordinator's governed recovery process. |

## Full Candidate Rollback to 0.66.2

1. Revert the 0.66.3 release-package change.
2. Restore version declarations from 0.66.3 to 0.66.2 across source SKILL, manifest, plugin/marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, and e2e fixture pointers.
3. Remove the 0.66.3 CHANGELOG entry and the three 0.66.3 release documents.
4. Rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.
5. Confirm `v0.66.2` still resolves locally and remotely to `f859bb6f662ecc187dc5f49ba20b077f5b35d882`.

## Released-State Recovery

If `v0.66.3` was created but released lineage fails, stop publication immediately. Determine whether the release commit or tag operation is wrong; do not move an already published tag silently. Any remote tag correction is an irreversible release action requiring Coordinator governance and explicit evidence. Restore the 0.66.2 package for users until a corrected release receives review.

## Reversibility

| Component | Reversible | Method |
| --- | --- | --- |
| Version declaration sync and release docs | Yes | Revert the release-package commit. |
| Release docs boundary wording fix | Yes | Revert the docs files, but keep the compact wording; do not reintroduce the verbose 0.66.2 phrasing that fails the negation gate. |
| Published remote tag | Not treated as routine reversible state | Governed recovery only; never silently retarget. |
| Historical missing tags | Not changed | No rollback action. |

## Validation After Rollback

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.66.3 --require-changelog --lineage-mode candidate
git diff --check
```

## No-overclaim Boundaries

This plan does not authorize historical tag backfill and does not close RISK-039 or RISK-041. It claims no official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-037/RISK-040 closure, or 1.0.0 production-ready status.
