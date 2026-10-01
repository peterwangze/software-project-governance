# Rollback Plan - 0.67.0

**Version**: 0.67.0 (minor)
**Release**: canonical Loop Runtime Contract + shared migration planner + decomposition confirmation
**Date**: 2026-07-23
**Candidate parent (B)**: `4275e22` (FEAT-004, on top of FEAT-003 `2e79e5f` and FEAT-002 `b628a54`)
**Decision**: DEC-104 + FEAT-002~004 + REL-059 (user decision "继续")

## Rollback Triggers

| Trigger | Detection | Action |
| --- | --- | --- |
| Version declaration drift | `check-version-consistency` fails | Restore all 0.67.0 declarations and fixture pointers to the previous package state. |
| Release docs boundary regression | `check-release` reports a missing `boundary_needles` token or a forbidden release docs overclaim for 0.67.0 | Restore the proven 0.65.3 compact boundary wording in all three 0.67.0 release docs before release. |
| Boundary wording verbose enough to break negation | `_line_has_scoped_claim_negation` returns False for a scoped claim phrase | Use the compact 0.65.3 template wording; do not reintroduce verbose phrasing. |
| Loop Runtime Contract v1 containment byte drift | `flow_unit_runtime.py` v1 byte-frozen boundary no longer matches FIX-195 | Stop release; restore the byte-frozen v1 boundary and rerun drift parity (9/9 match). |
| Migration plan identity breaks | dry-run and apply serialize different plans, or `plan_hash` is not immutable | Stop release; restore the pure `build_migration_plan()` and re-confirm purity (16-thread). |
| Decomposition confirmation lets dormant masquerade as active | `confirm_decomposition` activates without operator confirmation | Stop release; restore the advisory heuristic + operator-confirmation gate. |
| Candidate mode incorrectly requires or proves a tag | Candidate release check reports tag existence as required/proven | Revert the candidate and stop release review. |
| Released mode admits missing or mismatched lineage | Local/remote tag or explicit commit mismatch is not rejected | Stop release; do not move an already published tag. |
| Historical tags are created without a decision | `git tag` shows new historical tags without an approved mapping decision | Stop release and remove only the unauthorized local/remote tag action through the Coordinator's governed recovery process. |

## Full Candidate Rollback to 0.66.3

1. Revert the 0.67.0 release-package change (version projection + CHANGELOG + release docs + candidate manifest). The FEAT-002~004 code commits are the candidate parent B and remain intact as the code base; only the release packaging reverts.
2. Restore version declarations from 0.67.0 to 0.66.3 across source SKILL, manifest, plugin/marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, and e2e fixture pointers.
3. Remove the 0.67.0 CHANGELOG entry and the three 0.67.0 release documents.
4. Rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.
5. Confirm `v0.66.3` still resolves locally and remotely to `ae277ab356d324a731570f55bc4bdf46b7a96b25`.

## Released-State Recovery

If `v0.67.0` was created but released lineage fails, stop publication immediately. Determine whether the release commit or tag operation is wrong; do not move an already published tag silently. Any remote tag correction is an irreversible release action requiring Coordinator governance and explicit evidence. Restore the 0.66.3 package for users until a corrected release receives review.

## Reversibility

| Component | Reversible | Method |
| --- | --- | --- |
| Version declaration sync and release docs | Yes | Revert the release-package commit. |
| Release docs boundary wording | Yes | Revert the docs files, but keep the compact wording; do not reintroduce verbose phrasing that fails the negation gate. |
| Loop Runtime Contract v1 containment byte | Governed | Restore byte-frozen boundary; rerun drift parity before re-release. |
| Migration plan identity | Governed | Restore pure function + immutable `plan_hash`; re-confirm purity. |
| Decomposition confirmation gate | Governed | Restore operator-confirmation gate; re-verify dormant-as-active is unrepresentable. |
| Published remote tag | Not treated as routine reversible state | Governed recovery only; never silently retarget. |
| Historical missing tags | Not changed | No rollback action. |

## Validation After Rollback

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.67.0 --require-changelog --lineage-mode candidate
git diff --check
```

## No-overclaim Boundaries

This plan does not authorize historical tag backfill and does not close RISK-037 or RISK-042. 0.67.0 does not activate execution engine; RISK-037 remains open; RISK-042 remains open. It claims no official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-037/RISK-039/RISK-040/RISK-041/RISK-042 closure, or 1.0.0 production-ready status.
