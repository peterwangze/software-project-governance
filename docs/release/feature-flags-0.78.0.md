# Feature Flags - 0.78.0

**Version**: 0.78.0 (minor)
**Release**: 治理降噪第一批——FIX-278（G4/F 编码显式化 + G1 summary top-N + G2 legacy 判定 + G3 写时 guard）+ FIX-279（write-guard 列数契约修正）+ REL-071 版本规划（M-0 裁决 DEC-169）+ FIX-280（M5 基线小修）
**Date**: 2026-08-26
**Decision**: REL-071 (0.78.0 MINOR candidate packaging — M-1, candidate-only; transition/tag/push 待用户授权——DEC-143 交互基线)

## Feature Flag Inventory

0.78.0 introduces no runtime feature flag and no kill-switch-controlled rollout. The release packages already-merged window commits (`v0.77.0..HEAD` = 4 commits, measured `git rev-list --count v0.77.0..HEAD` = 4): FIX-278 (governance noise-reduction first batch — G4/F explicit UTF-8 guidance for `.governance` reads + G1 `--summary-only` standard-tier top-N output contract + G2 legacy-data downgrade judgment rules L-A/L-B/L-C + G3 change-triage write-time structure guard; AUDIT-147/148 reports archived), FIX-279 (G3 write-guard column-count contract fix — standard_cols takes the first non-written `| TRIAGE-` row of the row family's canonical 10 columns, EVD row only as fallback; DEC-168), REL-071 planning (version-plan-0.78.0.md + M-0 user ruling DEC-169 four items: in-slot = FIX-278 + FIX-279 + M5 baseline fix, RISK-044 maintain, MINOR positioning, N=2 continuation; dual review APPROVED_WITH_NOTES/0 ×2), FIX-280 (M5 baseline fix — version-plan polling-table style Check 10 `m5_option_list_no_auq` waiver notes in both planning docs' §5.1). No external product surface is toggled by a flag; the changes are machine checks, output-contract/judgment-rule behavior, a write-time guard, deterministic projection advances, and documentation — all operating under the existing candidate/released lineage model.

| Component | Default | Notes |
| --- | --- | --- |
| Candidate lineage | `--lineage-mode candidate` default | Does not require or prove that a release tag exists. |
| Released lineage | explicit mode | Requires `--release-commit`; verifies local and configured remote (`github-https`) tag identity under `HOST_PROJECT_ROOT`. |
| Check 39 `check_r1_completion_gate` (0.77.0, FIX-274) | WARN-first (0.77.x observation window) | Unchanged by 0.78.0. Tightening condition registered (DEC-160): after 2 consecutive zero-violation 0.77.x releases, escalate to FAIL — escalation MUST be decision-logged. **0.78.0 is NOT a 0.77.x version; the observation window is not closed by it.** No runtime flag. |
| Check 40 `check_dsh_skills_manifest` (0.77.0, FIX-272) | always-on (product-gate) | Unchanged by 0.78.0; 35/35 bidirectional at 0.78.0 (re-verified at packaging). |
| `@version-line` dynamic anchor (FIX-272) | always-on guard | Resolved at check time to `治理工作流（v<SKILL.md frontmatter>）`; at 0.78.0 the shipped `presets/governance/agent.cordis.yml` line was synced to v0.78.0 during packaging (anchor guard working as designed); fail-closed (FIX-250 precedent). |
| G1 `--summary-only` standard tier (FIX-278) | static output contract — no toggle | Summary + first FAIL/WARN + top ≤5 detail lines (130-char truncation) + "共 N issues，--level strict 查看全部" guidance line; lightweight/strict tiers and the other output paths byte-unchanged (DEC-166 ②). |
| G2 legacy downgrade rules L-A/L-B/L-C (FIX-278) | static judgment rules — no toggle | Pre-adoption historical violations judged by shape+final-state and downgraded to advisory WARN (DEC-166 ③); ACTIVE/真实 nonzero verdicts stay FAIL — fail-safe boundary locked; mixed-state W-7/BC-7 conservative non-downgrade registered for later marker-set extension. |
| G3 change-triage write guard (FIX-278 + FIX-279) | static write-time guard — no toggle | Successful triage writes structurally validated by `record_id` row-ID match (fail-closed exit 2 on anomaly); column contract = first non-written `| TRIAGE-` row family standard (10 cols) per DEC-168. |
| G4/F UTF-8 guidance (FIX-278) | static documentation | `.governance` pwsh read snippets MUST use explicit UTF-8 (`-Encoding UTF8` / `ReadAllText(..., UTF8)`); no runtime switch. |
| M7.7 behavior contract + budgets (0.77.0, FIX-271/274) | always-on, unchanged | 0.78.0 does not modify the 4/5-item contract, the 2560B budgets, or the Check 39/40 wiring. |
| Release docs boundary tokens | static documentation | Each 0.78.0 release doc includes the five `check-release` `boundary_needles` and the compact negation wording verified against the negation-function template. |

## Rollout and Kill Switch

There is no runtime product flag to phase or disable. The changes are statically validated (per-commit review evidence and test records — FIX-278 CODE R1 / DESIGN R1 APPROVED_WITH_NOTES/0 with DEC-166; FIX-279 TDD 15 red→green + CODE R0 APPROVED_WITH_NOTES/0 with DEC-168; FIX-280 Check 10 baseline 110→105 zeroed with EVD-905; version-consistency/projection-sync/manifest/crossrefs PASS recorded at packaging) and internally exercised. Before release, use candidate lineage. After the release commit and `v0.78.0` are created and pushed (github-https), use released lineage with the exact commit. A failing released check is the kill switch: stop release completion and correct or roll back the tag/package state; do not weaken the check. For G1/G2/G3 the equivalent "off" state is the rollback path (revert the corresponding in-window commits or the release package per rollback-plan-0.78.0.md) — there is no runtime toggle by design, because the guard/judgment behavior is the verified contract itself, not an optional feature.

## Test Boundary

- FIX-278: CODE R0 NEEDS_CHANGE → R1 APPROVED_WITH_NOTES/0 (five findings closed; N-P2-1/N-P2-2/P3 group registered for next-touch cleanup); DESIGN R0 NEEDS_CHANGE → R1 APPROVED_WITH_NOTES/0 (9/9 disposition; W-7/BC-7 registered); DEC-166 (G1/G2 L-A/L-B/L-C/G3/G4-F contracts + excluded candidates A-D reasons); commit `3ad9fdd` pushed github-https.
- FIX-279: TDD 14→15 red→green all green; CODE R0 APPROVED_WITH_NOTES/0 (REVIEW-FIX-279-CODE-R0; P0=0/P1=0/P2=3/P3=3); DEC-168 (TRIAGE row-family canonical column contract); live-verification TRIAGE-FIX-279/REL-071 0 false positives; EVD-904 (1985 tests / 0 new failures attributable / 27 pre-existing baseline); commit `c193299` pushed github-https.
- REL-071 planning: dual review APPROVED_WITH_NOTES/0 ×2 (REVIEW-REL-071-RELEASE-R0 / REVIEW-REL-071-DESIGN-R0); M-0 user ruling DEC-169 (ask_user_question); commit `ce4d7fe` pushed github-https.
- FIX-280: EVD-905; Check 10 `m5_option_list_no_auq` baseline zeroed (check-governance 110→105, first FAIL returns to pre-existing 18c); TRIAGE-FIX-280 write-guard live 0-false-positive; commit `a7fd5b3` pushed github-https.
- Projection (REL-071 M-1): `release-projection --write` -> `{"state": "PASS", "written": 15, "source_version": "0.78.0"}` exit 0; persona/preset v0.78.0 + AGENTS.md.template `@bootstrap-version: 0.78.0` + fixture SKILL.md byte-equal + required-snippets pins 0.78.0; marker face 9 lines (governance-init ×3 + e2e mirror ×3 + e2e CLAUDE.md + root AGENTS.md; root CLAUDE.md gitignored local sync).
- check-version-consistency PASS; check-projection-sync --fail-on-issues PASS (15 projections). The release docs boundary wording is verified directly against the negation function template. No full-suite-green claim is made beyond the recorded runs.

## Migration Note (RISK-D5 — DSH preset staleness)

DSH upgrade path: `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`. The persona version line (v0.78.0) and 0.78.0 bootstrap template reach sessions only after `--sync` rewrites the DSH preset; a pulled-but-not-synced checkout still injects the old template. Do not claim session-level effects for unsynced installations. **After sync, the noise-reduction checks act on the governed project's own `.governance/` read-time data with no per-project reworking.**

## No-overclaim Boundaries

This candidate does not create or prove `v0.78.0` and does not close RISK-036 or RISK-039. 0.78.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). RISK-044 is accepted per DEC-149 with the 2026-08-26 checkpoint re-review maintained (DEC-167); its quick-scan subset stays out-slotted to 0.78.x+. No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
