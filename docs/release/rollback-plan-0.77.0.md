# Rollback Plan - 0.77.0

**Version**: 0.77.0 (minor)
**Release**: DSH 标准插件安装支持 + 事故防再发链同槽——FEAT-010（bundle 形态随包安装）+ FIX-271 / AUDIT-146 / FIX-274 / FIX-272 / FIX-273 / FIX-275（RCA → 防再发固化 → always-on 注入面 → 守卫补全 → 检测加固 → 打包卫生）+ FIX-276（F-02 入槽 README 能力分级宣示补注，DEC-163）
**Date**: 2026-08-25
**Candidate parent (B)**: `0f9e5bb` (FIX-276, on top of `618ab13` FIX-275, `7d7a966` FIX-273, `e3e45c0` FIX-272, `4d13992` FIX-274, `2bb10ac` AUDIT-146, `d396097` FIX-271, `3339d99` FEAT-010, and the 0.76.0 released lineage `4f24e74` / tag `v0.76.0`)
**Decision**: REL-070 (0.77.0 MINOR candidate packaging, candidate-only; transition/tag/push 待用户授权——DEC-143 交互基线)

## Rollback Triggers

| Trigger | Detection | Action |
| --- | --- | --- |
| Version declaration drift | `check-version-consistency` fails | Restore all 0.77.0 declarations and fixture pointers to the previous package state. |
| Projection drift | `check-projection-sync --fail-on-issues` fails on any of the 15 projections, or `release-projection` check-only reports drift | Re-run `release-projection --write` from a correct SKILL frontmatter; if the frontmatter itself is wrong, fix it first, then re-write. |
| Persona / AGENTS template drift | persona version line or AGENTS.md.template L3 `@bootstrap-version` diverges from the SKILL frontmatter | The two transformed_text projections rewrite deterministically; never hand-edit the version lines — rerun the projection write. |
| `@bootstrap-version` marker face drift (commands/governance-init.md x3 / e2e mirror x3 / e2e CLAUDE.md / root AGENTS.md / root CLAUDE.md) | markers diverge from frontmatter | Restore marker lines to the frontmatter version (FIX-256 marker-face discipline); root CLAUDE.md is gitignored local sync — restore locally, no commit. |
| `REQUIRED_SNIPPETS` pin drift | `check-version-consistency` reports verify_workflow.py snippet mismatch | Restore the 6 version pins in the REQUIRED_SNIPPETS block (version declaration only; no logic change). |
| M7.7 injection-surface regression (Check 39 / contract-anchor guard) | SKILL.md contract section / persona / preset miss R1-R5 keywords or Check 39 verdicts wrong | Stop release; restore pre-0.77.0 injection surface and re-confirm check-injection-contract (28+ anchors) + CheckR1CompletionGateTests + budget-guard tests (2560B). |
| Check 40 / `check-dsh-skills-manifest` regression | dsh.skills bidirectional check fails or false-negatives | Stop release; restore FIX-272 engine wiring; re-confirm TDD 9 cases + manifestation checks. |
| Packaging hygiene regression (pyc leak recurrence) | `npm pack --dry-run --json` reports any `__pycache__/*.pyc` | Stop release; restore negation patterns position (must stay after all directory whitelist entries — order sensitivity F1 P3); re-measure 243 entries/0 pyc/5.72MB. |
| Side-effect detection regression (FIX-273) | UNC/single-backslash/normalized/IGNORECASE verdicts wrong | Stop release; restore `_OUTSIDE_REPO_FILE_RE` / `_REAL_ENV_TEXT_RE` branches; re-confirm 9 boundary tests (61 green). |
| Change-triage fifth-step regression (FIX-271) | side-effect declaration missing/route wrong | Stop release; restore M7.7/red-line bundle/triage step 5 wiring; re-confirm 12 TDD cases (52/52) + four-step byte-identical invariant. |
| Capability-grading declaration drift (FIX-276) | README claims contradict SKILL.md A/B/C single source of truth | Restore README declaration note to the FIX-276 state; re-run cross-references + manifest checks. |
| Release docs boundary regression | `check-release` reports a missing `boundary_needles` token or a forbidden release docs overclaim for 0.77.0 | Restore the proven compact negation wording in all three 0.77.0 release docs before release. |
| Candidate mode incorrectly requires or proves a tag | Candidate release check reports tag existence as required/proven | Revert the candidate and stop release review. |
| Released mode admits missing or mismatched lineage | Local/remote tag or explicit commit mismatch is not rejected | Stop release; do not move an already published tag. |
| Historical tags are created without a decision | `git tag` shows new historical tags without an approved mapping decision | Stop release and remove only the unauthorized local/remote tag action through the Coordinator's governed recovery process. |

## Full Candidate Rollback to 0.76.0

1. Revert the 0.77.0 release-package change (version projection + CHANGELOG + release docs + candidate manifest). The code commits (FEAT-010/FIX-271/AUDIT-146/FIX-274/FIX-272/FIX-273/FIX-275/FIX-276) are the candidate parent B and remain intact as the code base; only the release packaging reverts. `git revert` of the candidate commit is the canonical path — every packaging change is reversible text+metadata.
2. Restore version declarations from 0.77.0 to 0.76.0 across source SKILL frontmatter, core manifest, plugin/marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, e2e fixture pointers, the two DSH template version lines, and the @bootstrap-version marker faces. Prefer `release-projection --write` after restoring the SKILL frontmatter over hand edits.
3. Remove the 0.77.0 CHANGELOG entry, the three 0.77.0 release documents, `core/releases/0.77.0.json`, and the version-plan-0.77.0.md (or keep it as planning artifact if the Coordinator decides — package scope decision).
4. Rerun version consistency, projection sync, the applicable candidate/released lineage check, and `git diff --check`.
5. Confirm `v0.76.0` still resolves locally and remotely (github-https) to the 0.76.0 release commit (`4f24e74`).

## Released-State Recovery

If `v0.77.0` was created but released lineage fails, stop publication immediately. Determine whether the release commit or tag operation is wrong; do not move an already published tag silently. Any remote tag correction is an irreversible release action requiring Coordinator governance and explicit evidence. Restore the 0.76.0 package for users until a corrected release receives review.

## Rollback Boundaries (mandatory replication of version-plan §3.1)

**Replicating `docs/release/version-plan-0.77.0.md` §3.1** — the release-boundary contract:

| State | Rollback method | Constraint |
| --- | --- | --- |
| Candidate/transition state (candidate commit committed, tag not created/pushed) | `git revert` of the candidate commit (manifest-only reversible) | Routine reversible operation (0.76.0 rollback-plan **Reversibility L43** precedent: "Revert the release-package commit" — L43 is the Reversibility-table row; L46 is the Watchdog checks row, not applicable) |
| Published v0.77.0 tag (local + remote) | **Governed recovery only** (Coordinator + explicit evidence) | **Never silently retarget** — a remote tag correction is an irreversible release action requiring the Coordinator governance flow (0.76.0 rollback-plan **Reversibility L50** precedent: "Published remote tag — Not treated as routine reversible state; Governed recovery only; never silently retarget") |

## Reversibility

| Component | Reversible | Method |
| --- | --- | --- |
| Version declaration sync and release docs | Yes | Revert the release-package commit (`git revert`). |
| Release docs boundary wording | Yes | Revert the docs files, but keep the compact wording; do not reintroduce verbose phrasing that fails the negation gate. |
| DSH template version lines (persona / AGENTS L3) | Yes | Deterministic projection rewrite; revert = re-run `release-projection --write` with the restored frontmatter version. |
| Anti-recurrence checks (FIX-274/272/273 — Check 39/40, @version-line anchor, side-effect branches) | Governed | Revert the changed domains/engine wiring (`checks/` additions, verify_workflow.py thin exports & blocks); re-confirm per-commit suites before re-release. Checks are read-only/report-only and fail-safe (WARN-first / no-verdict on parse failure) — reverting restores 0.76.0 behavior with zero data-state changes. |
| M7.7 / red-line / triage fifth step (FIX-271) | Governed | Revert behavior-protocol M7.7, dispatch template red-line bundle, change-triage step 5; re-confirm 12 TDD cases + four-step byte-identical invariant. |
| Packaging hygiene (FIX-275) | Yes | Restore `files` array to pre-0.77.0 whitelist (8 positive entries); re-measure pack dry-run (154 pyc baseline implies hygiene regression — must re-apply patterns before re-release; the negation patterns themselves are the fix, not a new regression). |
| README declaration note (FIX-276) | Yes — but keep | Restore README to pre-FIX-276 state only if the declaration contradicts the SKILL.md source of truth; otherwise keep (declaration is the L114-convention fix). |
| Ride-along commits (AUDIT-146) | Governed | Per-commit revert restores prior state; re-confirm read-only report availability (docs artifact, no runtime impact). |
| Installed DSH preset (RISK-D5) | Yes — via resync | After reverting the repo, `python <plugin_root>/adapters/dsh/launch.py --sync` rewrites the preset; unsynced presets keep injecting whatever template they were generated from. |
| Published remote tag | Not treated as routine reversible state | Governed recovery only; never silently retarget. |
| Historical missing tags | Not changed | No rollback action. |

## Validation After Rollback

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.77.0 --require-changelog --lineage-mode candidate
git diff --check
```

(For a full rollback to 0.76.0 the third command validates the restored 0.76.0 package with `--version 0.76.0` as applicable.)

## Migration Note (RISK-D5 — DSH preset staleness)

DSH has no `/plugin update`. Upgrade requires `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`; rollback on the DSH platform likewise requires re-running `--sync` after the repository state is restored. A checkout that has been pulled (or reverted) but not re-synced keeps injecting the stale persona/bootstrap template — version-line drift observed in a session is not evidence about the repository state until sync status is confirmed. **After sync, the anti-recurrence checks act on the governed project's own `.governance/` records with no per-project reworking.**

## No-overclaim Boundaries

This plan does not authorize historical tag backfill and does not close RISK-036 or RISK-039. 0.77.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). It claims no official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready status. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
