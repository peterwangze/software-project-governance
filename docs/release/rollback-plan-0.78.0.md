# Rollback Plan - 0.78.0

**Version**: 0.78.0 (minor)
**Release**: 治理降噪第一批——FIX-278（G4/F 编码显式化 + G1 summary top-N + G2 legacy 判定 + G3 写时 guard）+ FIX-279（write-guard 列数契约修正）+ REL-071 版本规划（M-0 裁决 DEC-169）+ FIX-280（M5 基线小修）
**Date**: 2026-08-26
**Candidate parent (B)**: `a7fd5b3` (FIX-280, on top of `ce4d7fe` REL-071 版本规划, `c193299` FIX-279, `3ad9fdd` FIX-278, and the 0.77.0 released lineage `db9f6c9` / tag `v0.77.0`)
**Decision**: REL-071 (0.78.0 MINOR candidate packaging — M-1, candidate-only; transition/tag/push 待用户授权——DEC-143 交互基线)

## Rollback Triggers

| Trigger | Detection | Action |
| --- | --- | --- |
| Version declaration drift | `check-version-consistency` fails | Restore all 0.78.0 declarations and fixture pointers to the previous package state. |
| Projection drift | `check-projection-sync --fail-on-issues` fails on any of the 15 projections, or `release-projection` check-only reports drift | Re-run `release-projection --write` from a correct SKILL frontmatter; if the frontmatter itself is wrong, fix it first, then re-write. |
| Persona / preset / AGENTS template drift | persona/preset version line or AGENTS.md.template `@bootstrap-version` diverges from the SKILL frontmatter | The transformed_text projections rewrite deterministically; never hand-edit the version lines — rerun the projection write for the template; the shipped `presets/governance/agent.cordis.yml` version line is guarded by the dynamic `@version-line` anchor (check-injection-contract) and must carry `治理工作流（v0.78.0）`. |
| `@bootstrap-version` marker face drift (commands/governance-init.md ×3 / e2e mirror ×3 / e2e CLAUDE.md / root AGENTS.md / root CLAUDE.md) | markers diverge from frontmatter | Restore marker lines to the frontmatter version (FIX-256 marker-face discipline); root CLAUDE.md is gitignored local sync — restore locally, no commit. |
| `REQUIRED_SNIPPETS` pin drift | `check-version-consistency` reports verify_workflow.py snippet mismatch | Restore the 6 version pins in the REQUIRED_SNIPPETS block (version declaration only; no logic change). |
| G1 summary-tier output-contract regression | check-governance `--summary-only` standard tier loses the first-FAIL/WARN + top-N detail + guidance line, or lightweight/strict tiers change byte-behavior | Stop release; restore the FIX-278 G1 domain (DEC-166 ② — other tiers byte-unchanged invariant); re-confirm review evidence (CODE R1 / DESIGN R1 APPROVED_WITH_NOTES/0) and the audit-148 top-N tests. |
| G2 legacy downgrade regression | pre-adoption historical violations wrongly counted as FAIL (or ACTIVE/真实 nonzero wrongly downgraded) | Stop release; restore the FIX-278 G2 judgment rules (L-A/L-B/L-C, fail-safe boundary, DEC-166 ③); re-confirm DESIGN R1 blue-team 7-band verification + DEC-166 contract. |
| G3 write-guard / write-guard column-contract regression | legal change-triage write mis-flagged (exit 2) or a broken row accepted | Stop release; restore the FIX-278 G3 guard + FIX-279 column contract (standard_cols = first non-written `| TRIAGE-` row, 10 cols; EVD fallback; row-ID match kept); re-confirm TDD 15 cases red→green + live TRIAGE-FIX-279/REL-071 0-false-positive verification (DEC-168). |
| M5 注记 regression | Check 10 `m5_option_list_no_auq` re-triggers on version-plan polling-table styles | Restore both §5.1 waiver notes (AskUserQuestion reference, fact+reference only); re-run check-governance baseline (110→105 zeroed post-FIX-280). |
| Release docs boundary regression | `check-release` reports a missing `boundary_needles` token or a forbidden release docs overclaim for 0.78.0 | Restore the proven compact negation wording in all three 0.78.0 release docs before release. |
| Candidate mode incorrectly requires or proves a tag | Candidate release check reports tag existence as required/proven | Revert the candidate and stop release review. |
| Released mode admits missing or mismatched lineage | Local/remote tag or explicit commit mismatch is not rejected | Stop release; do not move an already published tag. |
| Historical tags are created without a decision | `git tag` shows new historical tags without an approved mapping decision | Stop release and remove only the unauthorized local/remote tag action through the Coordinator's governed recovery process. |

## Full Candidate Rollback to 0.77.0

1. Revert the 0.78.0 release-package change (version projection + CHANGELOG + release docs + candidate manifest `core/releases/0.78.0.json`). The in-window code/planning commits (FIX-278 `3ad9fdd` / FIX-279 `c193299` / REL-071 planning `ce4d7fe` / FIX-280 `a7fd5b3`) are the candidate parent B and remain on master as the content base; only the release packaging reverts. `git revert` of the candidate commit is the canonical path — every packaging change is reversible text+metadata.
2. Restore version declarations from 0.78.0 to 0.77.0 across source SKILL frontmatter, core manifest, plugin/marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, e2e fixture pointers, the DSH template/preset version lines, and the @bootstrap-version marker faces. Prefer `release-projection --write` after restoring the SKILL frontmatter over hand edits.
3. Remove the 0.78.0 CHANGELOG entry, the three 0.78.0 release documents, and `core/releases/0.78.0.json` (keep `docs/release/version-plan-0.78.0.md` as planning artifact — package scope decision).
4. Rerun version consistency, projection sync, the applicable candidate/released lineage check, and `git diff --check`.
5. Confirm `v0.77.0` still resolves locally and remotely (github-https) to the 0.77.0 release commit (`db9f6c9`).

## Released-State Recovery

If `v0.78.0` was created but released lineage fails, stop publication immediately. Determine whether the release commit or tag operation is wrong; do not move an already published tag silently. Any remote tag correction is an irreversible release action requiring Coordinator governance and explicit evidence. Restore the 0.77.0 package for users until a corrected release receives review.

## Rollback Boundaries (mandatory replication of version-plan §3.1)

**Replicating `docs/release/version-plan-0.78.0.md` §3.1** — the release-boundary contract:

| State | Rollback method | Constraint |
| --- | --- | --- |
| Candidate/transition state (candidate commit committed, tag not created/pushed) | `git revert` of the candidate commit (manifest-only reversible) | Routine reversible operation (0.76.0 rollback-plan **Reversibility L43** precedent: "Revert the release-package commit" — L43 is the Reversibility-table row; L46 is the Watchdog checks row, not applicable) |
| Published v0.78.0 tag (local + remote) | **Governed recovery only** (Coordinator + explicit evidence) | **Never silently retarget** — a remote tag correction is an irreversible release action requiring the Coordinator governance flow (0.76.0 rollback-plan **Reversibility L50** precedent: "Published remote tag — Not treated as routine reversible state; Governed recovery only; never silently retarget") |

## Reversibility

| Component | Reversible | Method |
| --- | --- | --- |
| Version declaration sync and release docs | Yes | Revert the release-package commit (`git revert`). |
| Release docs boundary wording | Yes | Revert the docs files, but keep the compact wording; do not reintroduce verbose phrasing that fails the negation gate. |
| DSH template/preset version lines (persona / AGENTS / preset) | Yes | Deterministic projection rewrite; revert = re-run `release-projection --write` with the restored frontmatter version; the preset line is then re-checked by the dynamic `@version-line` anchor. |
| FIX-278 content (G1/G2/G3/G4-F) | Governed | In-window content commit on master (pushed github-https). Reverting the domain requires a separate governed `git revert` of `3ad9fdd` plus the DEC-166 contract records; for packaging-scope rollback only the candidate commit is reverted and the content remains (candidate parent B). |
| FIX-279 content (write-guard column contract) | Governed | Same as FIX-278 — content commit `c193299` (pushed); verify TDD 15 + DEC-168 before re-release. |
| REL-071 planning doc + FIX-280 M5 fix | Governed | Content commits `ce4d7fe` / `a7fd5b3` (pushed); planning doc is read-only planning, FIX-280 is a docs waiver note — reverting restores the baseline Check 10 attribution. |
| Installed DSH preset (RISK-D5) | Yes — via resync | After reverting the repo, `python <plugin_root>/adapters/dsh/launch.py --sync` rewrites the preset; unsynced presets keep injecting whatever template they were generated from. |
| Published remote tag | Not treated as routine reversible state | Governed recovery only; never silently retarget. |
| Historical missing tags | Not changed | No rollback action. |

## Validation After Rollback

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.78.0 --require-changelog --lineage-mode candidate
git diff --check
```

(For a full rollback to 0.77.0 the third command validates the restored 0.77.0 package with `--version 0.77.0` as applicable.)

## Migration Note (RISK-D5 — DSH preset staleness)

DSH has no `/plugin update`. Upgrade requires `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`; rollback on the DSH platform likewise requires re-running `--sync` after the repository state is restored. A checkout that has been pulled (or reverted) but not re-synced keeps injecting the stale persona/bootstrap template — version-line drift observed in a session is not evidence about the repository state until sync status is confirmed. **After sync, the noise-reduction checks act on the governed project's own `.governance/` read-time data with no per-project reworking.**

## No-overclaim Boundaries

This plan does not authorize historical tag backfill and does not close RISK-036 or RISK-039. 0.78.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). It claims no official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready status. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
