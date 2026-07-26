# Rollback Plan - 0.69.0

**Version**: 0.69.0 (minor)
**Release**: production telemetry + honest DORA metrics (FEAT-008) + VAL-008 dogfood validation PASS + VAL-009 shitu external validation PASS (first type)
**Date**: 2026-07-26
**Candidate parent (B)**: `9136330` (VAL-008 defect fix, on top of FEAT-008 `aa6e76a` and ADR commits `5540258`)
**Decision**: FEAT-008 + VAL-008 + VAL-009 (REL-061, user authorized)

## Rollback Triggers

| Trigger | Detection | Action |
| --- | --- | --- |
| Version declaration drift | `check-version-consistency` fails | Restore all 0.69.0 declarations and fixture pointers to the previous package state. |
| Release docs boundary regression | `check-release` reports a missing `boundary_needles` token or a forbidden release docs overclaim for 0.69.0 | Restore the proven 0.65.3 compact boundary wording in all three 0.69.0 release docs before release. |
| Boundary wording verbose enough to break negation | `_line_has_scoped_claim_negation` returns False for a scoped claim phrase | Use the compact 0.65.3 template wording; do not reintroduce verbose phrasing. |
| Telemetry overclaims a metric | `loop_telemetry.compute_metrics` returns a fabricated value when evidence is insufficient, or treats activity/plan as success (anti-proxy breach) | Stop release; restore unknown-when-insufficient (`unknown` when evidence insufficient) + anti-proxy; re-confirm the 29 telemetry tests and VAL-008 dogfood telemetry step. |
| Telemetry is not a pure read | `compute_metrics` mutates state or reads outside the event log | Stop release; restore the pure read contract; re-confirm purity tests. |
| Legacy DORA proxy shadowing the honest path | `_dora_metrics_legacy_proxy` is no longer deprecated or the advisory `telemetry` key is missing | Stop release; restore the deprecation marker + advisory `telemetry` key. |
| VAL-008 dogfood regression | DEFECT-1/2 reintroduced (gate event envelope missing REQUIRED_FIELDS, or fuse_trip loses persisted loop_count) | Stop release; restore the defect fix; re-confirm 28 PASS / 0 FAIL / 1 INFO and 211 loop tests + 2 subtests. |
| Candidate mode incorrectly requires or proves a tag | Candidate release check reports tag existence as required/proven | Revert the candidate and stop release review. |
| Released mode admits missing or mismatched lineage | Local/remote tag or explicit commit mismatch is not rejected | Stop release; do not move an already published tag. |
| Historical tags are created without a decision | `git tag` shows new historical tags without an approved mapping decision | Stop release and remove only the unauthorized local/remote tag action through the Coordinator's governed recovery process. |

## Full Candidate Rollback to 0.68.0

1. Revert the 0.69.0 release-package change (version projection + CHANGELOG + release docs + candidate manifest). The FEAT-008 + VAL-008 defect-fix code commits are the candidate parent B and remain intact as the code base; only the release packaging reverts.
2. Restore version declarations from 0.69.0 to 0.68.0 across source SKILL, manifest, plugin/marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, and e2e fixture pointers.
3. Remove the 0.69.0 CHANGELOG entry and the three 0.69.0 release documents.
4. Rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.
5. Confirm `v0.68.0` still resolves locally and remotely to the 0.68.0 released commit.

## Released-State Recovery

If `v0.69.0` was created but released lineage fails, stop publication immediately. Determine whether the release commit or tag operation is wrong; do not move an already published tag silently. Any remote tag correction is an irreversible release action requiring Coordinator governance and explicit evidence. Restore the 0.68.0 package for users until a corrected release receives review.

## Reversibility

| Component | Reversible | Method |
| --- | --- | --- |
| Version declaration sync and release docs | Yes | Revert the release-package commit. |
| Release docs boundary wording | Yes | Revert the docs files, but keep the compact wording; do not reintroduce verbose phrasing that fails the negation gate. |
| Telemetry `compute_metrics` pure read | Governed | Restore unknown-when-insufficient + anti-proxy + purity; re-confirm 29 telemetry tests and VAL-008 telemetry step before re-release. |
| Legacy DORA proxy deprecation | Governed | Restore deprecation marker + advisory `telemetry` key. |
| VAL-008 defect fix (event envelope + fuse_trip loop_count) | Governed | Restore the defect fix; re-confirm 28 PASS / 0 FAIL / 1 INFO and 211 loop tests + 2 subtests. |
| Published remote tag | Not treated as routine reversible state | Governed recovery only; never silently retarget. |
| Historical missing tags | Not changed | No rollback action. |

## Validation After Rollback

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.69.0 --require-changelog --lineage-mode candidate
git diff --check
```

## No-overclaim Boundaries

This plan does not authorize historical tag backfill and does not close RISK-037 or RISK-042. 0.69.0 does not close RISK-037/RISK-042 (second external type validation pending). VAL-009 proves the first external type; a second external type is still required to fully close RISK-037/042. It claims no official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-037/RISK-039/RISK-040/RISK-041/RISK-042 closure, or 1.0.0 production-ready status.
