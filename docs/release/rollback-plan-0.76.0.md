# Rollback Plan - 0.76.0

**Version**: 0.76.0 (minor)
**Release**: 看护模式七项 + /governance 性能修复打包——REQ-145.1~145.7 七项落地（AUDIT-145 诊断 → FIX-263 设计 → FIX-264~269 实现链）+ FIX-270 /governance 性能修复，随行 FIX-255/256/258、AUDIT-144、FIX-260/261/262（REQ-107/108 消费方）、DOC-002
**Date**: 2026-08-23
**Candidate parent (B)**: `db1078f` (FIX-269, on top of `4e3d08a` FIX-267, `15051c1` FIX-266, `3a819d0` FIX-268, `cba247b` FIX-265, `1479fcc` FIX-270, `1e9cc4a` DOC-002, `66fa210` FIX-264, `cc79dd0` FIX-262, `3fd5adf` FIX-261, `8922c6e` FIX-260, `e15d453` AUDIT-144, `bae9d5f` FIX-258, `18dc6d7` FIX-256, `347dd64` FIX-255, and the 0.75.0 released lineage `543550c` / tag `v0.75.0`)
**Decision**: REL-069 (0.76.0 MINOR candidate packaging, candidate-only)

## Rollback Triggers

| Trigger | Detection | Action |
| --- | --- | --- |
| Version declaration drift | `check-version-consistency` fails | Restore all 0.76.0 declarations and fixture pointers to the previous package state. |
| Projection drift | `check-projection-sync --fail-on-issues` fails on any of the 15 projections, or `release-projection` check-only reports drift | Re-run `release-projection --write` from a correct SKILL frontmatter; if the frontmatter itself is wrong, fix it first, then re-write. |
| Persona / AGENTS template drift | persona version line or AGENTS.md.template L3 `@bootstrap-version` diverges from the SKILL frontmatter | The two transformed_text projections rewrite deterministically; never hand-edit the version lines — rerun the projection write. |
| `@bootstrap-version` marker face drift (commands/governance-init.md x3 / e2e mirror x3 / e2e CLAUDE.md / root AGENTS.md / root CLAUDE.md) | markers diverge from frontmatter | Restore marker lines to the frontmatter version (FIX-256 marker-face discipline); root CLAUDE.md is gitignored local sync — restore locally, no commit. |
| `REQUIRED_SNIPPETS` pin drift | `check-version-consistency` reports verify_workflow.py snippet mismatch | Restore the 6 version pins in the REQUIRED_SNIPPETS block (version declaration only; no logic change). |
| Watchdog check regression (Check 35-38 / Check 30c / Check 34) | check-governance or check-release verdicts wrong (false FAIL/WARN direction or crash) | Stop release; restore the pre-0.76.0 domains and re-confirm per-commit suites (31+24+41+31, 13-14, 18 cases) + full regressions recorded per commit. Check modules are read-only — restore = revert the domain files to their 0.75.0 state. |
| `--summary-only` regression | bootstrap summary missing / wrong aggregation / no `Governance: {N} issues` line | Stop release; restore FIX-264 engine wiring and re-confirm test_summary_only 15 cases + M4.1/SKILL injection section. |
| `/governance status` regression | status command >2s or Scenario F data wrong / missing | Stop release; restore FIX-270 (A) wiring; re-confirm 15 FIX-270 cases + tv 0.47s/official re-verify. |
| Host product-gate skip misfires | host check-governance misses real product issues or dogfood loses gates | Stop release; restore `_PLUGIN_PRODUCT_CHECK_IDS` splitting; re-confirm FIX-270 (B) tests + dogfood full-gate run. |
| Release docs boundary regression | `check-release` reports a missing `boundary_needles` token or a forbidden release docs overclaim for 0.76.0 | Restore the proven compact negation wording in all three 0.76.0 release docs before release. |
| Candidate mode incorrectly requires or proves a tag | Candidate release check reports tag existence as required/proven | Revert the candidate and stop release review. |
| Released mode admits missing or mismatched lineage | Local/remote tag or explicit commit mismatch is not rejected | Stop release; do not move an already published tag. |
| Historical tags are created without a decision | `git tag` shows new historical tags without an approved mapping decision | Stop release and remove only the unauthorized local/remote tag action through the Coordinator's governed recovery process. |

## Full Candidate Rollback to 0.75.0

1. Revert the 0.76.0 release-package change (version projection + CHANGELOG + release docs + candidate manifest). The code commits (FIX-263~270 and the eight ride-along commits) are the candidate parent B and remain intact as the code base; only the release packaging reverts. `git revert` of the candidate commit is the canonical path — every packaging change is reversible text+metadata.
2. Restore version declarations from 0.76.0 to 0.75.0 across source SKILL, core manifest, plugin/marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, e2e fixture pointers, the two DSH template version lines, and the @bootstrap-version marker faces. Prefer `release-projection --write` after restoring the SKILL frontmatter over hand edits.
3. Remove the 0.76.0 CHANGELOG entry and the three 0.76.0 release documents.
4. Rerun version consistency, projection sync, the applicable candidate/released lineage check, and `git diff --check`.
5. Confirm `v0.75.0` still resolves locally and remotely to the 0.75.0 release commit (`543550c`).

## Released-State Recovery

If `v0.76.0` was created but released lineage fails, stop publication immediately. Determine whether the release commit or tag operation is wrong; do not move an already published tag silently. Any remote tag correction is an irreversible release action requiring Coordinator governance and explicit evidence. Restore the 0.75.0 package for users until a corrected release receives review.

## Reversibility

| Component | Reversible | Method |
| --- | --- | --- |
| Version declaration sync and release docs | Yes | Revert the release-package commit (`git revert`). |
| Release docs boundary wording | Yes | Revert the docs files, but keep the compact wording; do not reintroduce verbose phrasing that fails the negation gate. |
| DSH template version lines (persona / AGENTS L3) | Yes | Deterministic projection rewrite; revert = re-run `release-projection --write` with the restored frontmatter version. |
| Watchdog checks (FIX-264~270) | Governed | Revert the changed domains/engine wiring (checks/snapshot_domain.py, risk_domain.py extension, gate_domain.py, ci_domain.py, verify_workflow.py thin exports & blocks, --summary-only, status command); re-confirm per-commit suites before re-release. Checks are read-only and fail-safe (WARN/no-verdict on parse failure) — reverting restores 0.75.0 behavior with zero data-state changes. |
| REQ-107/108 consumer loop (FIX-260/261/262) | Governed | Revert review_domain.py +246 / hook regex / task-priority-analysis --evidence-task; re-confirm 13-14/11/18 cases; machine records remain in `.governance/` (records are data, not code — no rollback action). |
| Ride-along commits (FIX-255/256/258, AUDIT-144, DOC-002) | Governed | Per-commit revert restores prior behavior; re-confirm per-commit suites (test_change_triage 40, EntryBootstrapTemplate 6/6, bootstrap 20/20, task_priority 128). |
| Installed DSH preset (RISK-D5) | Yes — via resync | After reverting the repo, `python <plugin_root>/adapters/dsh/launch.py --sync` rewrites the preset; unsynced presets keep injecting whatever template they were generated from. |
| Published remote tag | Not treated as routine reversible state | Governed recovery only; never silently retarget. |
| Historical missing tags | Not changed | No rollback action. |

## Validation After Rollback

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.76.0 --require-changelog --lineage-mode candidate
git diff --check
```

(For a full rollback to 0.75.0 the third command validates the restored 0.75.0 package with `--version 0.75.0` as applicable.)

## Migration Note (RISK-D5 — DSH preset staleness)

DSH has no `/plugin update`. Upgrade requires `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`; rollback on the DSH platform likewise requires re-running `--sync` after the repository state is restored. A checkout that has been pulled (or reverted) but not re-synced keeps injecting the stale persona/bootstrap template — version-line drift observed in a session is not evidence about the repository state until sync status is confirmed. **After sync, the watchdog checks act on the governed project's own `.governance/` records with no per-project reworking.**

## No-overclaim Boundaries

This plan does not authorize historical tag backfill and does not close RISK-036 or RISK-039. 0.76.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). It claims no official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready status. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
