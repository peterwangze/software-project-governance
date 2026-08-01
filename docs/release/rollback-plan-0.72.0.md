# Rollback Plan - 0.72.0

**Version**: 0.72.0 (minor)
**Release**: Check 31 安装态消解打包 + release lineage 多版本授权 + 0.64.x docs 债务（FIX-200 / FIX-230 / AUDIT-140 / FIX-231）
**Date**: 2026-08-01
**Candidate parent (B)**: `e2537c0` (FIX-231, on top of `8cb9983` AUDIT-140, `dfeddb4` FIX-230, `1b77d95` FIX-200, and the 0.71.0 released lineage)
**Decision**: REL-065 (user authorized)

## Rollback Triggers

| Trigger | Detection | Action |
| --- | --- | --- |
| Version declaration drift | `check-version-consistency` fails | Restore all 0.72.0 declarations and fixture pointers to the previous package state. |
| Release docs boundary regression | `check-release` reports a missing `boundary_needles` token or a forbidden release docs overclaim for 0.72.0 | Restore the proven compact negation wording in all three 0.72.0 release docs before release. |
| Boundary wording verbose enough to break negation | `_line_has_scoped_claim_negation` returns False for a scoped claim phrase | Use the compact template wording; do not reintroduce verbose phrasing. |
| Identity attestation gate regresses | Check 31 identity_verdict no longer reflects the real `build_identity_attestation` result, or `IDENTITY_ATTESTATION_PENDING` reappears | Stop release; restore the FIX-200 real-attestation gate and re-confirm identity verdict PASS/FAIL tests. |
| Ledger authorization resolver regresses | `ledger.py` no longer matches the `(decision_id, version, commit)` triple, or a historical manifest disposition is lost | Stop release; restore the FIX-230 resolver and re-confirm the 2 resolver tests (+67 lines; 39 tests 38 PASS + 1 pre-existing 0.66.2 FAIL) + 8 backfilled manifests. |
| Audit report wording regresses | `check-loop-runtime-claims` reports UNSUPPORTED_AFFIRMATIVE on the repo-side audit-140 document | Stop release; restore the AUDIT-140 claim-scanner-safe wording. |
| 0.64.x docs tokens regress | DOC-001 gap check fails on the 0.64.x release docs | Stop release; restore the FIX-231 boundary tokens. |
| Candidate mode incorrectly requires or proves a tag | Candidate release check reports tag existence as required/proven | Revert the candidate and stop release review. |
| Released mode admits missing or mismatched lineage | Local/remote tag or explicit commit mismatch is not rejected | Stop release; do not move an already published tag. |
| Historical tags are created without a decision | `git tag` shows new historical tags without an approved mapping decision | Stop release and remove only the unauthorized local/remote tag action through the Coordinator's governed recovery process. |

## Full Candidate Rollback to 0.71.0

1. Revert the 0.72.0 release-package change (version projection + CHANGELOG + release docs + candidate manifest). The FIX-200/FIX-230/AUDIT-140/FIX-231 code commits are the candidate parent B and remain intact as the code base; only the release packaging reverts.
2. Restore version declarations from 0.72.0 to 0.71.0 across source SKILL, manifest, plugin/marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, and e2e fixture pointers.
3. Remove the 0.72.0 CHANGELOG entry and the three 0.72.0 release documents.
4. Rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.
5. Confirm `v0.71.0` still resolves locally and remotely to the 0.71.0 released commit.

## Released-State Recovery

If `v0.72.0` was created but released lineage fails, stop publication immediately. Determine whether the release commit or tag operation is wrong; do not move an already published tag silently. Any remote tag correction is an irreversible release action requiring Coordinator governance and explicit evidence. Restore the 0.71.0 package for users until a corrected release receives review.

## Reversibility

| Component | Reversible | Method |
| --- | --- | --- |
| Version declaration sync and release docs | Yes | Revert the release-package commit. |
| Release docs boundary wording | Yes | Revert the docs files, but keep the compact wording; do not reintroduce verbose phrasing that fails the negation gate. |
| Identity attestation gate (FIX-200) | Governed | Restore the pre-fix verifier logic and authority fixture; re-confirm identity verdict tests before re-release. |
| Ledger authorization resolver (FIX-230) | Governed | Restore the pre-fix resolver and manifest dispositions; re-confirm the 2 resolver tests (+67 lines; 39 tests 38 PASS + 1 pre-existing 0.66.2 FAIL) before re-release. |
| Audit report wording (AUDIT-140) / 0.64.x docs tokens (FIX-231) | Governed | Restore the pre-fix wording/tokens; re-confirm the claim gate and DOC-001 checks before re-release. |
| Published remote tag | Not treated as routine reversible state | Governed recovery only; never silently retarget. |
| Historical missing tags | Not changed | No rollback action. |

## Validation After Rollback

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.72.0 --require-changelog --lineage-mode candidate
git diff --check
```

## No-overclaim Boundaries

This plan does not authorize historical tag backfill and does not close RISK-036 or RISK-039. 0.72.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). It claims no official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready status. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
