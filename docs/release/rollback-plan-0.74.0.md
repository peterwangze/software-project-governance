# Rollback Plan - 0.74.0

**Version**: 0.74.0 (minor)
**Release**: 入口确定性五修复链打包——archive 双 root / `--auto` 冷却端点 / `--project-root` fail-closed 三端对齐 / 审查遗留清理（FIX-242 / FIX-243 / FIX-244 / FIX-245 / FIX-246）
**Date**: 2026-08-07
**Candidate parent (B)**: `1a375e6` (FIX-246, on top of `9a44898` FIX-245, `d2e454d` FIX-244, `57360b5` FIX-243, `5974ffe` FIX-242, and the 0.73.0 released lineage `515046d`)
**Decision**: REL-067 (0.74.0 MINOR candidate packaging, candidate-only)

## Rollback Triggers

| Trigger | Detection | Action |
| --- | --- | --- |
| Version declaration drift | `check-version-consistency` fails | Restore all 0.74.0 declarations and fixture pointers to the previous package state. |
| Release docs boundary regression | `check-release` reports a missing `boundary_needles` token or a forbidden release docs overclaim for 0.74.0 | Restore the proven compact negation wording in all three 0.74.0 release docs before release. |
| Boundary wording verbose enough to break negation | `_line_has_scoped_claim_negation` returns False for a scoped claim phrase | Use the compact template wording; do not reintroduce verbose phrasing. |
| Dual-root resolution regresses (FIX-242) | archive.py resolves the plugin root as the host root again, or `--project-root` rebinds the wrong seam | Stop release; restore the FIX-242 dual-root resolution and re-confirm the 13 new tests. |
| `--auto` endpoint regresses (FIX-243) | `--auto` archives the current release window or regresses below the roadmap endpoint | Stop release; restore the bounded endpoint formula and re-confirm the 8+1 tests. |
| `--project-root` fail-closed regresses (FIX-244/245) | archive.py or verify_workflow.py accepts empty/missing/non-directory project roots silently | Stop release; restore the strict validation and re-confirm the fail-closed tests on both ends. |
| Dual-root rebind / reason-suffix lock regresses (FIX-246) | HOST_PROJECT_ROOT rebind assertions fail, error reason strings drift, or `.gitattributes` EOL baseline breaks | Stop release; restore the test locks and `.gitattributes` registration. |
| Candidate mode incorrectly requires or proves a tag | Candidate release check reports tag existence as required/proven | Revert the candidate and stop release review. |
| Released mode admits missing or mismatched lineage | Local/remote tag or explicit commit mismatch is not rejected | Stop release; do not move an already published tag. |
| Historical tags are created without a decision | `git tag` shows new historical tags without an approved mapping decision | Stop release and remove only the unauthorized local/remote tag action through the Coordinator's governed recovery process. |

## Full Candidate Rollback to 0.73.0

1. Revert the 0.74.0 release-package change (version projection + CHANGELOG + release docs + candidate manifest). The code commits (FIX-242~246) are the candidate parent B and remain intact as the code base; only the release packaging reverts.
2. Restore version declarations from 0.74.0 to 0.73.0 across source SKILL, manifest, plugin/marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, and e2e fixture pointers.
3. Remove the 0.74.0 CHANGELOG entry and the three 0.74.0 release documents.
4. Rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.
5. Confirm `v0.73.0` still resolves locally and remotely to the 0.73.0 released commit.

## Released-State Recovery

If `v0.74.0` was created but released lineage fails, stop publication immediately. Determine whether the release commit or tag operation is wrong; do not move an already published tag silently. Any remote tag correction is an irreversible release action requiring Coordinator governance and explicit evidence. Restore the 0.73.0 package for users until a corrected release receives review.

## Reversibility

| Component | Reversible | Method |
| --- | --- | --- |
| Version declaration sync and release docs | Yes | Revert the release-package commit. |
| Release docs boundary wording | Yes | Revert the docs files, but keep the compact wording; do not reintroduce verbose phrasing that fails the negation gate. |
| Dual-root resolution (FIX-242) | Governed | Restore the pre-fix archive.py root seams; re-confirm the 13 new tests before re-release. |
| Bounded `--auto` endpoint (FIX-243) | Governed | Restore the pre-fix endpoint formula; re-confirm the 8+1 tests before re-release. |
| `--project-root` fail-closed (FIX-244/245) | Governed | Restore the pre-fix validation on both archive.py and verify_workflow.py; re-confirm fail-closed tests before re-release. |
| Observation cleanup (FIX-246) | Governed | Restore pre-fix test locks and `.gitattributes` state; re-confirm mutation proofs before re-release. |
| Published remote tag | Not treated as routine reversible state | Governed recovery only; never silently retarget. |
| Historical missing tags | Not changed | No rollback action. |

## Validation After Rollback

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.74.0 --require-changelog --lineage-mode candidate
git diff --check
```

## No-overclaim Boundaries

This plan does not authorize historical tag backfill and does not close RISK-036 or RISK-039. 0.74.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). It claims no official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready status. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
