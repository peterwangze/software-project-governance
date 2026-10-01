# Rollback Plan - 0.68.0

**Version**: 0.68.0 (minor)
**Release**: executable Loop Engine — persistent PARO state machine + production gate back-edge/fuse/escalation + restart-safe event log
**Date**: 2026-07-23
**Candidate parent (B)**: `59e08fc` (FEAT-007, on top of FEAT-006 `697f2bd` and FEAT-005 `c33799f`)
**Decision**: FEAT-005~007 + REL-060 (user decision "继续")

## Rollback Triggers

| Trigger | Detection | Action |
| --- | --- | --- |
| Version declaration drift | `check-version-consistency` fails | Restore all 0.68.0 declarations and fixture pointers to the previous package state. |
| Release docs boundary regression | `check-release` reports a missing `boundary_needles` token or a forbidden release docs overclaim for 0.68.0 | Restore the proven 0.65.3 compact boundary wording in all three 0.68.0 release docs before release. |
| Boundary wording verbose enough to break negation | `_line_has_scoped_claim_negation` returns False for a scoped claim phrase | Use the compact 0.65.3 template wording; do not reintroduce verbose phrasing. |
| PARO state machine CAS unsafe | `apply_transition` writes a non-legal transition or loses a conflict under contention (CAS threading 12-thread 1-success/11-conflict 60x unstable) | Stop release; restore the legal-transition table + CAS writer and re-confirm the 12-thread contention run. |
| Production gate fuse is advisory instead of system-level | `check_release_readiness` fuse check becomes Coordinator advisory instead of a system-level block, or `loop_fuse_check` is no longer a pure read | Stop release; restore the system-level fuse block + pure-read `loop_fuse_check`; re-run the end-to-end gate fail→back-edge→round→fuse→escalation→block. |
| Event log loses durability or monotonicity | append-only JSONL event log shows multi-process loss, broken monotonicity/legality checks, or restart inconsistency | Stop release; restore the cross-process lock + monotonicity/legality checks; re-confirm 4×100=400 0 loss and restart consistency. |
| Dependency blocking / WIP budget bypassed | `loop_admission` lets a unit run without its dependency satisfied or exceed its WIP budget (setup=1/inner=5/middle=2/outer=1) | Stop release; restore the dependency block + WIP budget admission. |
| Candidate mode incorrectly requires or proves a tag | Candidate release check reports tag existence as required/proven | Revert the candidate and stop release review. |
| Released mode admits missing or mismatched lineage | Local/remote tag or explicit commit mismatch is not rejected | Stop release; do not move an already published tag. |
| Historical tags are created without a decision | `git tag` shows new historical tags without an approved mapping decision | Stop release and remove only the unauthorized local/remote tag action through the Coordinator's governed recovery process. |

## Full Candidate Rollback to 0.67.0

1. Revert the 0.68.0 release-package change (version projection + CHANGELOG + release docs + candidate manifest). The FEAT-005~007 code commits are the candidate parent B and remain intact as the code base; only the release packaging reverts.
2. Restore version declarations from 0.68.0 to 0.67.0 across source SKILL, manifest, plugin/marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, and e2e fixture pointers.
3. Remove the 0.68.0 CHANGELOG entry and the three 0.68.0 release documents.
4. Rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.
5. Confirm `v0.67.0` still resolves locally and remotely to the 0.67.0 released commit.

## Released-State Recovery

If `v0.68.0` was created but released lineage fails, stop publication immediately. Determine whether the release commit or tag operation is wrong; do not move an already published tag silently. Any remote tag correction is an irreversible release action requiring Coordinator governance and explicit evidence. Restore the 0.67.0 package for users until a corrected release receives review.

## Reversibility

| Component | Reversible | Method |
| --- | --- | --- |
| Version declaration sync and release docs | Yes | Revert the release-package commit. |
| Release docs boundary wording | Yes | Revert the docs files, but keep the compact wording; do not reintroduce verbose phrasing that fails the negation gate. |
| PARO state machine CAS writer | Governed | Restore legal-transition table + CAS writer; re-confirm 12-thread contention run before re-release. |
| Production gate fuse system-level block | Governed | Restore system-level block + pure-read `loop_fuse_check`; re-run end-to-end fuse chain. |
| Restart-safe append-only event log | Governed | Restore cross-process lock + monotonicity/legality checks; re-confirm 4×100=400 0 loss + restart consistency. |
| Dependency blocking / WIP budget | Governed | Restore admission gate; re-verify dependency satisfaction + WIP budget. |
| Published remote tag | Not treated as routine reversible state | Governed recovery only; never silently retarget. |
| Historical missing tags | Not changed | No rollback action. |

## Validation After Rollback

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.68.0 --require-changelog --lineage-mode candidate
git diff --check
```

## No-overclaim Boundaries

This plan does not authorize historical tag backfill and does not close RISK-037 or RISK-042. 0.68.0 does not close RISK-037/RISK-042 (external validation 0.69.0). Execution engine activates but runtime completeness requires 0.69.0 dogfood + external validation. It claims no official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-037/RISK-039/RISK-040/RISK-041/RISK-042 closure, or 1.0.0 production-ready status.
