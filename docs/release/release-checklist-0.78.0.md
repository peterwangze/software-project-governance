# Release Checklist - 0.78.0

**Version**: 0.78.0 (minor)
**Release**: 治理降噪第一批——FIX-278（G4/F 编码显式化 + G1 summary top-N + G2 legacy 判定 + G3 写时 guard）+ FIX-279（write-guard 列数契约修正）+ REL-071 版本规划（M-0 裁决 DEC-169）+ FIX-280（M5 基线小修）
**Date**: 2026-08-26
**Decision**: REL-071 (0.78.0 MINOR candidate packaging — M-1; M-0 user ruling 2026-08-26 (DEC-169, ask_user_question) confirmed in-slot/out-slot, RISK-044 maintain, MINOR positioning, N=2 continuation; candidate packaging is the next work unit; transition/tag/push still require explicit user authorization — DEC-143)
**Candidate parent (B)**: `a7fd5b3` (FIX-280, on top of `ce4d7fe` REL-071 版本规划, `c193299` FIX-279, `3ad9fdd` FIX-278, and the 0.77.0 released lineage `db9f6c9` / tag `v0.77.0`)

> Range fact: `git rev-list --count v0.77.0..HEAD` = **4 commits** (`git describe v0.77.0-4-gHEAD`). The 0.78.0 release carries all four: FIX-278 (governance noise-reduction first batch — behavior/rule-surface changes) carries the MINOR semantics, FIX-279 (write-guard column-contract fix — PATCH-face increment, DEC-168 contract to ship with 0.78.0), REL-071 planning (version-plan + M-0 ruling + dual review), FIX-280 (M5 baseline fix — docs waiver notes). The v0.77.0 chain itself (candidate `ac5df32` / transition `db9f6c9`) belongs to the already-released 0.77.0 and is not part of this window.

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined | PASS - 0.78.0 MINOR (M-0 confirmed, DEC-169); headline: governance noise-reduction first batch (FIX-278 G4/F+G1+G2+G3) + write-guard column-contract fix (FIX-279) + M5 baseline fix (FIX-280); no breaking runtime API |
| 2 | Change list enumerated | PASS - 4 in-window commits + version projection 0.77.0 -> 0.78.0 + CHANGELOG + candidate manifest + release docs (version-plan-0.78.0.md already committed at ce4d7fe) |
| 3 | Independent code review available | PASS - FIX-278 (CODE R0→R1 APPROVED_WITH_NOTES/0 + DESIGN R0→R1 APPROVED_WITH_NOTES/0), FIX-279 (CODE R0 APPROVED_WITH_NOTES/0), REL-071 planning (RELEASE R0 + DESIGN R0 APPROVED_WITH_NOTES/0 ×2), FIX-280 (docs waiver, EVD-905) — machine-persisted REVIEW-FIX-278-CODE-R1 / REVIEW-FIX-278-DESIGN-R1 / REVIEW-FIX-279-CODE-R0 / REVIEW-REL-071-RELEASE-R0 / REVIEW-REL-071-DESIGN-R0 |
| 4 | Candidate lineage boundary explicit | PASS - candidate mode does not require or prove a tag |
| 5 | Historical tag and official-marketplace overclaims excluded | PASS |

### Included

- FIX-278 (`3ad9fdd`, 16 files +2130/-42, pushed github-https): governance noise-reduction first batch — G4/F explicit UTF-8 encoding guidance for `.governance` reads (audit-147 D6 / audit-148 §4.3 mojibake evidence) + G1 `check-governance --summary-only` standard-tier output contract (first FAIL/WARN + top ≤5 details 130-char truncation + guidance line; other tiers byte-unchanged, DEC-166 ②) + G2 legacy-data downgrade judgment rules L-A/L-B/L-C (shape+final-state; ACTIVE/真实 nonzero stay FAIL — fail-safe locked, DEC-166 ③) + G3 change-triage write-time structure guard (record_id match, fail-closed exit 2) + AUDIT-147/148 reports archived. Dual review R0 NEEDS_CHANGE → R1 APPROVED_WITH_NOTES/0 ×2; DEC-166 (four sub-contract terms + excluded candidates A-D).
- FIX-279 (`c193299`, 2 files +154/-19, pushed github-https): G3 write-guard column-count contract fix — standard_cols takes the first non-written `| TRIAGE-` row (row-family canonical 10 columns); EVD row only as fallback; row-ID match and missing-row explicit error kept (P0-1 no regression); fixes the legal triage write being fail-closed exit 2 mis-flagged (live: TRIAGE-REL-071 / TRIAGE-FIX-279). TDD 15 red→green; CODE R0 APPROVED_WITH_NOTES/0; DEC-168 (TRIAGE row-family canonical column contract, ship with 0.78.0).
- REL-071 planning (`ce4d7fe`, 1 file, pushed): `docs/release/version-plan-0.78.0.md` — in/out-slot adjudication table (16 items, each with source trail), RISK-044 re-review (maintain-accept recommendation), M5 baseline fix in-slot; M-0 user ruling DEC-169 (four items); dual review APPROVED_WITH_NOTES/0 ×2.
- FIX-280 (`a7fd5b3`, 2 files, pushed): M5 baseline fix — Check 10 `m5_option_list_no_auq` waiver notes (AskUserQuestion reference) added to both planning docs' §5.1; check-governance 110→105 baseline zeroed (EVD-905).
- Version declarations and e2e fixture pointers advance from 0.77.0 to 0.78.0 (M-set: SKILL.md frontmatter 0.78.0 authority source + `release-projection --write` deterministic 15 projections — core manifest, 4 plugin.json (.claude/.codex/.zcode/.chrys), marketplace, package.json, four source hooks @version, dsh persona v0.78.0 + AGENTS.md.template `@bootstrap-version`, e2e SKILL byte_copy mirror + e2e plan-tracker 工作流版本 + @bootstrap-version marker face 9 lines (commands/governance-init.md ×3 + e2e mirror ×3 + e2e CLAUDE.md + root AGENTS.md; root CLAUDE.md gitignored local sync not in commit — FIX-256 precedent) + preset `presets/governance/agent.cordis.yml` version line (dynamic @version-line anchor) + `verify_workflow.py` REQUIRED_SNIPPETS 6 version pins (version literals only +6/-6, zero logic)).
- `project/CHANGELOG.md` gains a 0.78.0 entry (4-commit window, Added/Changed/Fixed/Validation/Boundaries + RISK-044 checkpoint note + out-slot queue note).
- Release docs trio created (feature-flags / release-checklist / rollback-plan — rollback-plan replicates version-plan §3.1 boundary table); `core/releases/0.78.0.json` candidate (candidate-only).
- `docs/release/version-plan-0.78.0.md` was already committed at `ce4d7fe` (planning deliverable; not re-added by this package).

### Excluded

- No official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim.
- 0.78.0 does not close RISK-036/RISK-039 (2026-09-30 review; independent closure criteria not satisfied).
- Out-slot legacy items registered for 0.78.x+ (per version-plan-0.78.0.md §5.1 adjudication table, DEC-169): F-03, F-04, F-04-env, F-05+BC-1, FIX-272 P2×2, RISK-044 quick-scan subsecond subset, G3 extension, G5, G6, W-7+BC-7, N-P2-1, N-P2-2, P3 group, FIX-279 follow-up observations (P2×3+P3×3), FIX-276 R0 F-01, change-triage "four-step" stale description. RISK-044 next re-review = 0.79.x (or next planning cycle) — registered.

## 2. Version and SemVer

0.78.0 is a MINOR because (a) FIX-278 changes the behavior/rule surface — G1 modifies the `check-governance --summary-only` output contract (standard tier: first FAIL/WARN + top-N details + guidance line), G2 introduces judgment rules for legacy data downgrade (DEC-166 ③), G3 adds a write-time gate (fail-closed) — cumulative behavior-rule changes and rule changes per VERSIONING.md (L12 milestone + L37 rule-change categories; same-class precedents: 0.75.0 injection/empty-recommendation MINOR, 0.76.0 stewardship-seven MINOR); (b) M-0 user ruling confirmed MINOR positioning (DEC-169). FIX-279 is stated honestly as a PATCH-face increment (VERSIONING.md L34: verify_workflow.py bug fix) and NOT used as the MINOR basis. Expected declarations are 0.78.0 in source SKILL frontmatter, core manifest, Claude/Codex/Zcode/Chrys plugin metadata, Claude marketplace metadata, package.json, four source hooks, the REQUIRED_SNIPPETS version pins in verify_workflow.py, the two e2e fixture pointers, the DSH template/preset version lines, and the @bootstrap-version marker faces. **Breaking changes: none** — G1 other tiers byte-unchanged, G2 fail-safe boundary locked (ACTIVE/真实 nonzero stay FAIL), G3 guard scoped to triage write success path, no interface deletion/rename, no default-behavior break (DEC-166).

## 3. Candidate Validation

Run before release review:

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py release-ledger --version 0.78.0 --no-remote
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.78.0 --require-changelog --lineage-mode candidate
```

Candidate mode intentionally does not require `v0.78.0` and is not evidence that the tag exists. The final release commit, local tag, and remote tag do not yet exist during package preparation. After the Coordinator creates and pushes them (github-https), rerun:

```text
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.78.0 --require-changelog --lineage-mode released --release-commit <commit>
python skills/software-project-governance/infra/verify_workflow.py release-ledger --version 0.78.0 --remote github-https
```

(Remote ledger uses `--remote github-https` per 0.75.0/0.77.0 precedent and this repo's push remote; origin SSH is unreachable — Host key verification failed — and any origin attempt must be reported honestly as UNKNOWN/BLOCKED, never wrapped as PASS.)

## 4. Release Gates (14 items, candidate-state annotated — version-plan-0.78.0.md §4)

| # | Gate (command) | 0.77.0 precedent | 0.78.0 expectation / candidate-state annotation |
| --- | --- | --- | --- |
| 1 | `check-version-consistency` | PASS (13 files; 1 advisory WARN host plan-tracker lag) | PASS expected (13 files declare 0.78.0); 1 advisory WARN — host plan-tracker still 0.77.0, Coordinator bumps after packaging (disclosed, not a failure) |
| 2 | `check-projection-sync --fail-on-issues` | PASS (15 projections) | PASS expected; drift → fix SKILL.md authority first, then `release-projection --write` (written=15), then re-check twice PASS; ADR-010 rollback journal/atomic-write evidence on any `--write` |
| 3 | `check-manifest-consistency` | 568/608 PASS | PASS expected; new files (0.78.0.json, 3 release docs) tolerated per 0.77.0 precedent (docs/release + core/releases not canonical-registered) |
| 4 | `check-cross-references --fail-on-issues` | 68 files/649 refs PASS | PASS expected (zero dangling) |
| 5 | `verify` (no args) | PASSED | PASSED expected; pre-existing baseline failures disclosed per precedent |
| 6 | pytest full suite | FIX-279 context: 1985 tests / 0 new failures / 27 pre-existing baseline (EVD-904) | Recorded at check-release unittest gate; zero packaging-introduced failures; 24×WSL + cleanup + timing-jitter baseline disclosed |
| 7 | check-governance zero-new | 0.77.0 release timepoint 113; bootstrap 2026-08-26 = 105 (post-FIX-280 Check 10 zeroed) | Zero-new relative to measured posture; host `.governance/` untouched by package (sub-agent boundary); 105 measured 2026-08-26 bootstrap, first FAIL = pre-existing 18c |
| 8 | `check-injection-contract` | 28 anchors/4 files PASS | PASS expected (4 files; @version-line resolves to v0.78.0 — preset line synced during packaging) |
| 9 | `check-dsh-skills-manifest` | 35/35 bidirectional PASS | PASS expected (35/35) |
| 10 | `check-release --version 0.78.0 --require-changelog --lineage-mode candidate` | 6 issues all classed (3 uncommitted-state artifacts + 3 pre-existing baseline) | Core static gates PASS; FAIL items classed per precedent: 3× release docs "must be tracked by git" (uncommitted-state — resolve on commit; rerun after commit), plus pre-existing baseline items (archive trigger gap / governance health / in-window loop-claims ragged-row if reproduced — FIX-277 fixed the audit-146 ragged row, expected gone) |
| 11 | `release-ledger --version 0.78.0 --no-remote` | NATIVE_CANDIDATE | Two-phase: pre-commit run reports uncommitted candidate transition state (expected FAIL — 0.77.0 precedent); rerun after candidate commit → NATIVE_CANDIDATE; UNKNOWN/BLOCKED never wrapped as PASS |
| 12 | `quality-tools` | Ruff/mypy not installed → NOT_RUN | NOT_RUN recorded honestly (ADR-010; never packaged as PASS) |
| 13 | `check-release ... --lineage-mode released --release-commit <commit>` | core gates PASS + 3 pre-existing baseline FAIL | M-7 (post tag/push); verifies local + remote tag |
| 14 | `release-ledger --version 0.78.0 --remote github-https` | NATIVE_RELEASED PASS | M-7; remote = github-https (origin SSH unreachable — UNKNOWN/BLOCKED if attempted); ADR-010: unique transition, single parent, merge/repeat/wrong-parent/rename-delete-add blocked |

**Rollback verification** (stage-release hard gate; no independent test env in this repo — 0.77.0 precedent: reversibility analysis + gate re-run as the verification vehicle; rollback-plan-0.78.0.md defines full/partial rollback paths; after rollback rerun #1/#2/#10 and `git diff --check`).

## 5. Test and Review Evidence

- FIX-278: CODE R0 NEEDS_CHANGE (P0-1 guard first-TRIAGE-row check + P2×4) → R1 APPROVED_WITH_NOTES/0 (five findings closed; N-P2-1 duplicate-definition / N-P2-2 dead-injection / P3 group registered for next-touch cleanup); DESIGN R0 NEEDS_CHANGE (F-1/F-2/F-3) → R1 APPROVED_WITH_NOTES/0 (9/9 disposition; W-7/BC-7 mixed-state conservative no-downgrade registered); DEC-166 (G1/G2 L-A-L-B-L-C/G3/G4-F contracts + candidate A/B/C/D exclusion reasons; W-1/W-2/W-3 follow-ups registered); commit `3ad9fdd` pushed github-https; pytest baseline 1976 passed / 27 failed (24×WSL env + cleanup + timing jitter + snapshot-freshness; EVD-FIX-278 note).
- FIX-279: TDD 14→15 red→green all green; CODE R0 APPROVED_WITH_NOTES/0 (REVIEW-FIX-279-CODE-R0; P0=0/P1=0/P2=3/P3=3); DEC-168; EVD-904 (1985 tests / 0 new failures attributable / 27 pre-existing baseline); live verification TRIAGE-FIX-279 / TRIAGE-REL-071 0 false positives; commit `c193299` pushed github-https.
- REL-071 planning: dual review APPROVED_WITH_NOTES/0 ×2 (REVIEW-REL-071-RELEASE-R0 / REVIEW-REL-071-DESIGN-R0); M-0 user ruling DEC-169 (four items, ask_user_question); commit `ce4d7fe` pushed github-https.
- FIX-280: EVD-905; check-governance 110→105 (Check 10 `m5_option_list_no_auq` baseline zeroed, first FAIL returns to pre-existing 18c); TRIAGE-FIX-280 write-guard live 0-false-positive; commit `a7fd5b3` pushed github-https.
- Projection record (REL-071 M-1): `release-projection --write` output `{"state": "PASS", "written": 15, "source_version": "0.78.0"}` exit 0; after write — persona/preset `治理工作流（v0.78.0）`, AGENTS.md.template `> @bootstrap-version: 0.78.0`, fixture SKILL.md byte-equal to source (byte_copy), required-snippets pins 0.78.0.
- The release docs boundary wording reuses the proven 0.77.0 compact negation template; all five `check-release` `boundary_needles` are present in each of the three 0.78.0 release docs.
- Known advisory WARN at candidate validation (disclosed): `check-version-consistency` reports the host `.governance/plan-tracker.md` recorded version still 0.77.0. The plan-tracker live record is not touched by the release package (sub-agent boundary) and is bumped to 0.78.0 by the Coordinator as part of the release governance step (same as prior releases), after which the WARN resolves.

## 6. Release Decision Boundary

This checklist prepares a candidate only. It does not commit, tag, push, approve marketplace submission, close risk, or make the final go/no-go decision. After tag creation and push (github-https), released lineage must verify the exact release commit locally and on the configured remote. Transition/publication requires explicit user authorization (DEC-143 interaction baseline: auto-recommend + user-confirm; release_authorized=false until authorized).

## 7. Rollback Verification

`docs/release/rollback-plan-0.78.0.md` defines full and partial rollback paths, replicating the §3.1 rollback-boundary table from `docs/release/version-plan-0.78.0.md`: candidate/transition-state rollback = `git revert` of the candidate commit (manifest-only reversible); a published `v0.78.0` tag rollback = governed recovery only (Coordinator + explicit evidence, never silently retargeted — 0.76.0 rollback-plan Reversibility L50 precedent). All headline changes are reversible at package level: G1/G2/G3 are in-window content commits with per-commit review evidence; the packaging change is text+metadata; the injection surface is text with machine-guarded anchors. After rollback, rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.

## 8. Migration Note (RISK-D5 — DSH preset staleness)

DSH has no `/plugin update`. The upgrade path is `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`. The 0.78.0 persona/preset version line and the AGENTS.md.template bootstrap version only reach live sessions after `launch.py --sync` rewrites the preset (`${DSH_HOME}/.agent-presets/governance/`); until then the installed preset still carries the old template. Do not claim session-level effects for installations that have pulled but not synced. **After upgrade sync, the noise-reduction checks act on a governed project's `.governance/` read-time data with no per-project reworking.**

## Candidate Gate Results

(Executed at packaging, 2026-08-26; same classing precedent as REL-070/REL-069/REL-068.)

- `check-release --version 0.78.0 --require-changelog --lineage-mode candidate` — **FAILED — 4 issue(s)**, exit 1, classified:
  - **(a) 3x release docs "must be tracked by git"** — `release-checklist-0.78.0.md` / `feature-flags-0.78.0.md` / `rollback-plan-0.78.0.md` — uncommitted-state artifacts of this candidate package itself, resolve when the commit lands (same class as REL-067/068/069/070; rerun after commit).
  - **(b) execution gate governance health exit=1 (132 issues)** — pre-existing host `.governance/` record posture measured today (2026-08-26). Baseline control: the same `check-governance --summary-only --level strict` run against the stashed 0.77.0 (pre-package) state also reports **132** — zero net new issues attributable to this release package (delta class: Check 24 advisory WARN plan-tracker 0.77.0 vs 0.78.0 +1 [resolves when Coordinator bumps the live record], Check 28q advisory hooks-drift +3 [installed `.git/hooks` lagging the bumped source @version — resolves on hook reinstall], offset by -4 run-to-run variance in dynamic sub-counts). Zero `.governance/` files touched by this release package (sub-agent boundary). The "105 issues" bootstrap figure recorded at FIX-280 used the standard-tier summary posture; per version-plan §8.6 the release docs state measured values, not earlier timepoint values (baseline-drifting precedent).
  - **Note — 0.77.0 baseline items not reproduced**: archive trigger gap (0.77.0's (b)) now `[PASS]`; loop runtime claim gate ragged-row FAIL (0.77.0's (d)) now `[PASS]` — 614 candidates parsed / skip=0 / identity PASS (FIX-277 ragged-doc fix confirmed; no window-introduced ragged rows in the 0.78.0 package).

  Static core gates all PASS: version consistency, release fact source, hot fact source, runtime readiness matrix, first session measurement, governance pack status, agent adapters, projection sync, cross references, archive integrity, release lineage (candidate boundary), gate sequence for release (Check 37 — no violations), one dot zero blockers, loop fuse block, changelog, loop runtime claim gate. Execution gates: verify (exit=0) PASS, e2e check (exit=0) PASS, unit tests (exit=0) PASS; governance health exit=1 as classified above.

- `check-version-consistency` — **PASSED** (13 files checked: SKILL.md, manifest.json, marketplace.json, 4 plugin.json, CHANGELOG, plan-tracker, 4 hooks; 1 advisory WARN: host `.governance/plan-tracker.md` still 0.77.0 — Coordinator bumps as part of release governance step, same as prior releases).
- `check-projection-sync --fail-on-issues` — **PASSED** (15 projections; source version 0.78.0).
- `check-manifest-consistency --fail-on-issues` — **PASS** (canonical 574 / actual 619).
- `check-cross-references --fail-on-issues` — **PASS** (68 files / 649 refs, zero dangling; no deprecated/circular).
- `verify` (no args) — **PASSED** (exit 0; only WARN = plan-tracker 0.77.0).
- `check-injection-contract` — **PASSED** (4 files / 28 anchors; dynamic @version-line resolved to `治理工作流（v0.78.0）` — preset line synced during packaging).
- `check-dsh-skills-manifest` — **PASSED** (declared 35 / on disk 35).
- `release-ledger --version 0.78.0 --no-remote` — FAIL (expected): `candidate_commit: expected exactly one commit adding ...core/releases/0.78.0.json, found 0` — uncommitted candidate transition state (git_commit_adding_path derivation requires the file committed; rerun by the Coordinator after the candidate commit — same REL-067/REL-070 precedent); trust_level = **NATIVE_CANDIDATE**, release_authorized = **false**.
- `quality-tools` — **NOT_RUN** (ruff: not installed; mypy: not installed; runtime_dependency=false) — recorded honestly, not packaged as PASS (ADR-010).

Risk disclosure (plan doc §6 preserved): **RISK-044** — re-review at this planning cycle maintained accept (DEC-167 checkpoint: 29.6-32.8s, satisfies revised acceptance "single run <60s and once per session"); quick-scan subset **stays out-slotted to 0.78.x+**; next re-review registered for 0.79.x (Coordinator writes risk-log at M-8). **RISK-036/RISK-039 remain open** (2026-09-30; not closed, not re-opened).

## No-overclaim Boundaries

This candidate does not create or prove `v0.78.0` and does not close RISK-036 or RISK-039. 0.78.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
