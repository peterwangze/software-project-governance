# Rollback Plan - 0.75.0

**Version**: 0.75.0 (minor)
**Release**: 关键行为规则注入面 + 空推荐降级打包——REQ-112/REQ-110 双落地（DEC-143 前置放大器；FIX-253 DEC-144 方案 A / FIX-254），随行 FIX-247~252 六个观察项/债务 commit 与 AUDIT-143
**Date**: 2026-08-21
**Candidate parent (B)**: `d90c167` (FIX-253, on top of `38c5c32` FIX-254, `7310cd7` AUDIT-143, `439f8b4` FIX-252, `0dc1786` FIX-251, `856301e` FIX-250, `113a959` FIX-249, `9ce4e19` FIX-248, `c9739d0` FIX-247, and the 0.74.0 released lineage `3a64d54` / tag `v0.74.0`)
**Decision**: REL-068 (0.75.0 MINOR candidate packaging, candidate-only)

## Rollback Triggers

| Trigger | Detection | Action |
| --- | --- | --- |
| Version declaration drift | `check-version-consistency` fails | Restore all 0.75.0 declarations and fixture pointers to the previous package state. |
| Projection drift (incl. new projections) | `check-projection-sync --fail-on-issues` fails on any of the 15 projections, or `release-projection` check-only reports drift | Re-run `release-projection --write` from a correct SKILL frontmatter; if the frontmatter itself is wrong, fix it first, then re-write. |
| Persona / AGENTS template drift (FIX-253 projections) | persona L33 version or AGENTS.md.template L3 `@bootstrap-version` diverges from the SKILL frontmatter | The two transformed_text projections (dsh-persona-version / dsh-agents-bootstrap-version) rewrite deterministically; never hand-edit the version lines — rerun the projection write. |
| Injection-surface anchor regression (FIX-253) | `check-injection-contract` (Check 33 / standalone subcommand) fails — persona contract block or SKILL canonical section missing anchors | Stop release; restore the contract blocks (persona 4 lines / SKILL 关键行为契约 section) and re-confirm the 12 anchors + test_dsh_adapter 18 tests. |
| Empty-recommendation regression (FIX-254) | task-priority analysis with unblocked=0 returns an empty recommendation again, or the normal (non-empty) recommendation path changes behavior | Stop release; restore the compute single-point wiring and re-confirm the 19 FIX-254 tests + merged 159/159. |
| Recommendation output shape breaks | `recommended_fallback` / `empty_reason` keys missing on the parse-error path (loop_exit_bridge) | Stop release; restore key propagation (both keys None on parse-error) and re-confirm test_loop_exit_bridge 12/12. |
| Parser visibility regression (FIX-251/252 ride-along) | dependency analysis stops seeing recent-window tasks, or valid document input raises spurious ValueError | Stop release; restore the parser state machine / `_coerce_text` guard and re-confirm the per-commit test suites. |
| Release docs boundary regression | `check-release` reports a missing `boundary_needles` token or a forbidden release docs overclaim for 0.75.0 | Restore the proven compact negation wording in all three 0.75.0 release docs before release. |
| Candidate mode incorrectly requires or proves a tag | Candidate release check reports tag existence as required/proven | Revert the candidate and stop release review. |
| Released mode admits missing or mismatched lineage | Local/remote tag or explicit commit mismatch is not rejected | Stop release; do not move an already published tag. |
| Historical tags are created without a decision | `git tag` shows new historical tags without an approved mapping decision | Stop release and remove only the unauthorized local/remote tag action through the Coordinator's governed recovery process. |

## Full Candidate Rollback to 0.74.0

1. Revert the 0.75.0 release-package change (version projection + CHANGELOG + release docs + candidate manifest). The code commits (FIX-253/254 and the six ride-along commits) are the candidate parent B and remain intact as the code base; only the release packaging reverts. `git revert` of the candidate commit is the canonical path — every packaging change is reversible text+metadata.
2. Restore version declarations from 0.75.0 to 0.74.0 across source SKILL, manifest, plugin/marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, e2e fixture pointers, and the two DSH template version lines (persona L33 / AGENTS.md.template L3). Prefer `release-projection --write` after restoring the SKILL frontmatter over hand edits.
3. Remove the 0.75.0 CHANGELOG entry and the three 0.75.0 release documents.
4. Rerun version consistency, projection sync, the applicable candidate/released lineage check, and `git diff --check`.
5. Confirm `v0.74.0` still resolves locally and remotely to the 0.74.0 release commit (`3a64d54`).

## Released-State Recovery

If `v0.75.0` was created but released lineage fails, stop publication immediately. Determine whether the release commit or tag operation is wrong; do not move an already published tag silently. Any remote tag correction is an irreversible release action requiring Coordinator governance and explicit evidence. Restore the 0.74.0 package for users until a corrected release receives review.

## Reversibility

| Component | Reversible | Method |
| --- | --- | --- |
| Version declaration sync and release docs | Yes | Revert the release-package commit (`git revert`). |
| Release docs boundary wording | Yes | Revert the docs files, but keep the compact wording; do not reintroduce verbose phrasing that fails the negation gate. |
| DSH template version lines (persona L33 / AGENTS L3) | Yes | Deterministic projection rewrite; revert = re-run `release-projection --write` with the restored frontmatter version. |
| Injection surface (FIX-253) | Governed | Revert the contract blocks and anchor registry; re-confirm Check 33 + 12 anchors + test_dsh_adapter 18 tests before re-release. Fully reversible by design (design doc fix-253-injection-surface-design-0.75.0.md reversibility section). |
| Empty-recommendation fallback (FIX-254) | Governed | Revert to the pre-fix task_priority.py/loop_exit_bridge.py state; re-confirm 159/159 merged tests. Fallback-only wiring means the normal path is untouched — reverting restores the previously-empty output. |
| Ride-along hardening (FIX-247~252) | Governed | Per-commit revert restores prior behavior; re-confirm per-commit suites (test_archive 119, test_change_triage, test_task_priority, BootstrapScriptTests). |
| Installed DSH preset (RISK-D5) | Yes — via resync | After reverting the repo, `python <plugin_root>/adapters/dsh/launch.py --sync` rewrites the preset; unsynced presets keep injecting whatever template they were generated from. |
| Published remote tag | Not treated as routine reversible state | Governed recovery only; never silently retarget. |
| Historical missing tags | Not changed | No rollback action. |

## Validation After Rollback

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.75.0 --require-changelog --lineage-mode candidate
git diff --check
```

(For a full rollback to 0.74.0 the third command validates the restored 0.74.0 package with `--version 0.74.0` as applicable.)

## Migration Note (RISK-D5 — DSH preset staleness)

DSH has no `/plugin update`. Upgrade requires `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`; rollback on the DSH platform likewise requires re-running `--sync` after the repository state is restored. A checkout that has been pulled (or reverted) but not re-synced keeps injecting the stale persona/bootstrap template — version-line drift observed in a session is not evidence about the repository state until sync status is confirmed.

## No-overclaim Boundaries

This plan does not authorize historical tag backfill and does not close RISK-036 or RISK-039. 0.75.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). It claims no official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready status. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
