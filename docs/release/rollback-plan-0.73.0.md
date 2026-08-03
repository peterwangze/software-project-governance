# Rollback Plan - 0.73.0

**Version**: 0.73.0 (minor)
**Release**: 三链重构（入口/循环/任务规划）生产接线打包（AUDIT-142 / FIX-236 / FIX-237 / FIX-238 / FIX-239 / FIX-240 / FIX-241 / FIX-233~235）
**Date**: 2026-08-03
**Candidate parent (B)**: `c14bce7` (FIX-238, on top of `9768844` FIX-237, `f5fad1a` FIX-241, `7894689` FIX-240, `51ebf39` FIX-236, `4d1d9fc` FIX-239, `fd03138` FIX-237, `1dce69f` AUDIT-142, `b26c37c` FIX-233/234/235, and the 0.72.0 released lineage)
**Decision**: REL-066 (user authorized release direction on 2026-08-03)

## Rollback Triggers

| Trigger | Detection | Action |
| --- | --- | --- |
| Version declaration drift | `check-version-consistency` fails | Restore all 0.73.0 declarations and fixture pointers to the previous package state. |
| Release docs boundary regression | `check-release` reports a missing `boundary_needles` token or a forbidden release docs overclaim for 0.73.0 | Restore the proven compact negation wording in all three 0.73.0 release docs before release. |
| Boundary wording verbose enough to break negation | `_line_has_scoped_claim_negation` returns False for a scoped claim phrase | Use the compact template wording; do not reintroduce verbose phrasing. |
| Loop wiring regresses (FIX-236) | review-record/next-candidates CLI or Check 30 V6 fails, or loop_exit_bridge fuse accepts corrupt records | Stop release; restore the FIX-236 wiring and re-confirm the 36+R1 8 tests. |
| Change triage regresses (FIX-237) | change-triage CLI or Check 32 fails, or a product-code task after the normalization date lacks a triage record | Stop release; restore the FIX-237 triage integration and re-confirm the 33 tests. |
| Bootstrap fallback regresses (FIX-238) | bootstrap.sh/cmd exit-code contract fails, or resolve timeout fallback breaks | Stop release; restore the vendor bootstrap scripts and re-confirm the 29 tests. |
| Hook locale hardening regresses (FIX-239) | Review-evidence grep/sed fails on UTF-8/emoji again | Stop release; restore `LC_ALL=C` in hooks. |
| Candidate mode incorrectly requires or proves a tag | Candidate release check reports tag existence as required/proven | Revert the candidate and stop release review. |
| Released mode admits missing or mismatched lineage | Local/remote tag or explicit commit mismatch is not rejected | Stop release; do not move an already published tag. |
| Historical tags are created without a decision | `git tag` shows new historical tags without an approved mapping decision | Stop release and remove only the unauthorized local/remote tag action through the Coordinator's governed recovery process. |

## Full Candidate Rollback to 0.72.0

1. Revert the 0.73.0 release-package change (version projection + CHANGELOG + release docs + candidate manifest). The code commits (AUDIT-142/FIX-236~241/FIX-233~235) are the candidate parent B and remain intact as the code base; only the release packaging reverts.
2. Restore version declarations from 0.73.0 to 0.72.0 across source SKILL, manifest, plugin/marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, and e2e fixture pointers.
3. Remove the 0.73.0 CHANGELOG entry and the three 0.73.0 release documents.
4. Rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.
5. Confirm `v0.72.0` still resolves locally and remotely to the 0.72.0 released commit.

## Released-State Recovery

If `v0.73.0` was created but released lineage fails, stop publication immediately. Determine whether the release commit or tag operation is wrong; do not move an already published tag silently. Any remote tag correction is an irreversible release action requiring Coordinator governance and explicit evidence. Restore the 0.72.0 package for users until a corrected release receives review.

## Reversibility

| Component | Reversible | Method |
| --- | --- | --- |
| Version declaration sync and release docs | Yes | Revert the release-package commit. |
| Release docs boundary wording | Yes | Revert the docs files, but keep the compact wording; do not reintroduce verbose phrasing that fails the negation gate. |
| Loop wiring (FIX-236) | Governed | Restore the pre-fix verifier/CLI logic; re-confirm the 36+R1 8 tests before re-release. |
| Change triage (FIX-237) | Governed | Restore the pre-fix triage logic; re-confirm the 33 tests before re-release. |
| Bootstrap fallback (FIX-238) | Governed | Restore the pre-fix entry tooling; re-confirm the 29 tests before re-release. |
| Hook locale hardening (FIX-239) / CI repair (FIX-240) / encoding tests (FIX-241) | Governed | Restore the pre-fix hooks/CI/tests; re-confirm respective gates before re-release. |
| Published remote tag | Not treated as routine reversible state | Governed recovery only; never silently retarget. |
| Historical missing tags | Not changed | No rollback action. |

## Validation After Rollback

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.73.0 --require-changelog --lineage-mode candidate
git diff --check
```

## No-overclaim Boundaries

This plan does not authorize historical tag backfill and does not close RISK-036 or RISK-039. 0.73.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). It claims no official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready status. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
