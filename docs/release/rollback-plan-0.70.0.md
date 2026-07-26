# Rollback Plan - 0.70.0

**Version**: 0.70.0 (minor)
**Release**: verify_workflow Phase 5 extraction (FEAT-009) — evidence/risk/review domains extracted to checks/{evidence,risk,review}_domain.py
**Date**: 2026-07-26
**Candidate parent (B)**: `ed8446c` (FEAT-009 commit, on top of ADR-016 `6b97b5e` and claim-scanner policy fix `b617f8c`)
**Decision**: FEAT-009 (REL-062, user authorized)

## Rollback Triggers

| Trigger | Detection | Action |
| --- | --- | --- |
| Version declaration drift | `check-version-consistency` fails | Restore all 0.70.0 declarations and fixture pointers to the previous package state. |
| Release docs boundary regression | `check-release` reports a missing `boundary_needles` token or a forbidden release docs overclaim for 0.70.0 | Restore the proven compact negation wording in all three 0.70.0 release docs before release. |
| Boundary wording verbose enough to break negation | `_line_has_scoped_claim_negation` returns False for a scoped claim phrase | Use the compact template wording; do not reintroduce verbose phrasing. |
| Extraction breaks behavioral equivalence | `check-governance` output differs from the pre-extraction baseline (134 issues), or any of the 626 tests + 82 subtests regress | Stop release; restore the unsplit `verify_workflow.py` and the pre-extraction check domain bodies; re-confirm byte-diff identity and zero regression. |
| Extraction is re-export disguise (DEC-088 breach) | Function bodies are duplicated rather than moved, or thick wrappers remain in `verify_workflow.py` | Stop release; restore real extraction (function bodies moved to `checks/{evidence,risk,review}_domain.py`, only thin re-exports remain). |
| `sys.modules` aliasing guard regresses | `verify_workflow.py` run as `__main__` can no longer resolve `import verify_workflow` to the active module | Stop release; restore the `sys.modules["verify_workflow"] = sys.modules["__main__"]` aliasing guard. |
| Candidate mode incorrectly requires or proves a tag | Candidate release check reports tag existence as required/proven | Revert the candidate and stop release review. |
| Released mode admits missing or mismatched lineage | Local/remote tag or explicit commit mismatch is not rejected | Stop release; do not move an already published tag. |
| Historical tags are created without a decision | `git tag` shows new historical tags without an approved mapping decision | Stop release and remove only the unauthorized local/remote tag action through the Coordinator's governed recovery process. |

## Full Candidate Rollback to 0.69.0

1. Revert the 0.70.0 release-package change (version projection + CHANGELOG + release docs + candidate manifest). The FEAT-009 extraction code commits are the candidate parent B and remain intact as the code base; only the release packaging reverts.
2. Restore version declarations from 0.70.0 to 0.69.0 across source SKILL, manifest, plugin/marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, and e2e fixture pointers.
3. Remove the 0.70.0 CHANGELOG entry and the three 0.70.0 release documents.
4. Rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.
5. Confirm `v0.69.0` still resolves locally and remotely to the 0.69.0 released commit.

## Released-State Recovery

If `v0.70.0` was created but released lineage fails, stop publication immediately. Determine whether the release commit or tag operation is wrong; do not move an already published tag silently. Any remote tag correction is an irreversible release action requiring Coordinator governance and explicit evidence. Restore the 0.69.0 package for users until a corrected release receives review.

## Reversibility

| Component | Reversible | Method |
| --- | --- | --- |
| Version declaration sync and release docs | Yes | Revert the release-package commit. |
| Release docs boundary wording | Yes | Revert the docs files, but keep the compact wording; do not reintroduce verbose phrasing that fails the negation gate. |
| Domain extraction (evidence/risk/review) | Governed | Restore the unsplit `verify_workflow.py` and pre-extraction check bodies; re-confirm byte-diff identity and 626 tests + 82 subtests before re-release. |
| `sys.modules` aliasing guard | Governed | Restore the aliasing guard; re-confirm `__main__` resolution. |
| Published remote tag | Not treated as routine reversible state | Governed recovery only; never silently retarget. |
| Historical missing tags | Not changed | No rollback action. |

## Validation After Rollback

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.70.0 --require-changelog --lineage-mode candidate
git diff --check
```

## No-overclaim Boundaries

This plan does not authorize historical tag backfill and does not close RISK-036, RISK-039, RISK-040, or RISK-041. 0.70.0 does not close RISK-036/RISK-039/RISK-040/RISK-041 (official marketplace operations, ArchGuard external validation, entry determinism host validation, and release-lineage historical-tag disposition each have independent closure criteria not yet satisfied). It claims no official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039/RISK-040/RISK-041 closure, or 1.0.0 production-ready status.
