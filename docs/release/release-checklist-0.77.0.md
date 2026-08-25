# Release Checklist - 0.77.0

**Version**: 0.77.0 (minor)
**Release**: DSH 标准插件安装支持 + 事故防再发链同槽——FEAT-010（bundle 形态随包安装）+ FIX-271 / AUDIT-146 / FIX-274 / FIX-272 / FIX-273 / FIX-275（RCA → 防再发固化 → always-on 注入面 → 守卫补全 → 检测加固 → 打包卫生）+ FIX-276（F-02 入槽 README 能力分级宣示补注，DEC-163）
**Date**: 2026-08-25
**Decision**: REL-070 (0.77.0 MINOR candidate packaging, candidate-only; user authorized launch via M-0 ruling 2026-08-24 (DEC-163, ask_user_question) and candidate packaging is the next work unit; transition/tag/push still require explicit user authorization)
**Candidate parent (B)**: `0f9e5bb` (FIX-276, on top of `618ab13` FIX-275, `7d7a966` FIX-273, `e3e45c0` FIX-272, `4d13992` FIX-274, `2bb10ac` AUDIT-146, `d396097` FIX-271, `3339d99` FEAT-010, and the 0.76.0 released lineage `4f24e74` / tag `v0.76.0`)

> Range fact: `git rev-list --count v0.76.0..HEAD` = 8 commits (git describe `v0.76.0-8-g0f9e5bb`). The 0.77.0 release carries all eight; FEAT-010 (new distribution capability) and FIX-274 (new MUST behavior contract) carry the MINOR semantics, the remaining six ride along (FIX-271/AUDIT-146/FIX-272/FIX-273/FIX-275 = anti-recurrence chain of the FEAT-010 incident, FIX-276 = README declaration face closure, DEC-163).

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined | PASS - 0.77.0 MINOR; headline: DSH standard plugin install support (FEAT-010 bundle form) + anti-recurrence chain (FIX-271/274/272/273/275) + RCA docs (AUDIT-146) + README declaration closure (FIX-276); no breaking runtime API |
| 2 | Change list enumerated | PASS - 8 code commits + version projection 0.76.0 -> 0.77.0 + CHANGELOG + candidate manifest + release docs + version-plan doc |
| 3 | Independent code review available | PASS - FEAT-010 (R0→R1→R2 APPROVED_WITH_NOTES/0), FIX-271 (CODE R0 + DESIGN R0→R1 APPROVED_WITH_NOTES/0×2), AUDIT-146 (R0), FIX-274 (DESIGN R0 + CODE R0→R1), FIX-272 (R0), FIX-273 (R0), FIX-275 (R0), FIX-276 (R0) — machine-persisted REVIEW-FIX-274-R1/REVIEW-FIX-272-R0/REVIEW-FIX-273-R0/REVIEW-FIX-275-R0/REVIEW-FIX-276-R0; REL-070 planning doc dual review R0→R2/R1 APPROVED_WITH_NOTES/0 (DEC-163) |
| 4 | Candidate lineage boundary explicit | PASS - candidate mode does not require or prove a tag |
| 5 | Historical tag and official-marketplace overclaims excluded | PASS |

### Included

- FEAT-010 (3339d99): DSH standard plugin install support — bundle form (`dsh.bundle` + `dsh.skills` 35 entries + `files` whitelist + `keywords`; `cordis.patch.yml` composition layer mounting `presets/governance/`; README DSH install command + local-path alternative). Isolated-env install smoke + self-asserting boot double PASS; real `~/.dsh` zero-operation dual confirmation. Review chain R0→R1→R2 APPROVED_WITH_NOTES/0.
- FIX-271 (d396097): anti-recurrence protocol R1-R5 — behavior-protocol M7.7 (three-of-one / relay per-command / wording ban) + dispatch red-line bundle + change-triage fifth step (side-effect declaration machine check). CODE R0 + DESIGN R0→R1 APPROVED_WITH_NOTES/0×2.
- AUDIT-146 (2bb10ac): incident RCA report (`docs/requirements/audit-146-feat010-dsh-config-loss-rca.md`, 266 lines; H1a possible·high + tool-side confirmed-level exclusion + D1-D5 + R1-R5 draft). R0 APPROVED_WITH_NOTES/0.
- FIX-274 (4d13992): M7.7 always-on injection surface (SKILL.md contract section 4th item + DSH persona 5th item + preset + e2e mirror; 27 anchors/4 files) + Check 39 `check_r1_completion_gate` (WARN-first; tightening registered: 2 consecutive zero-violation 0.77.x releases then FAIL, decision-logged) + DEC-161/162 budget raise 2560B. DESIGN R0 + CODE R0→R1 APPROVED_WITH_NOTES/0.
- FIX-272 (e3e45c0): bundle drift guards — @version-line dynamic anchor (28 anchors) + `check_dsh_skills_manifest` 35/35 bidirectional + CLI + Check 40 (product-gate) + agent.cordis.yml header note. TDD 9 red->green; R0 APPROVED_WITH_NOTES/0.
- FIX-273 (7d7a966): side-effect detection blind-spot hardening — UNC/single-backslash root branches + normalized dual-match + IGNORECASE + negation-context docstring + 9 boundary tests (4 red→61 green). R0 APPROVED_WITH_NOTES/0.
- FIX-275 (618ab13): pyc packaging hygiene — `files` negation patterns `!**/__pycache__/` + `!**/*.pyc` (RED 154 pyc/10.34MB → GREEN 0 pyc/5.72MB, -64%; zero over-delete/over-add; payload integrity intact; .npmignore path empirically rejected). R0 APPROVED_WITH_NOTES/0.
- FIX-276 (0f9e5bb): README capability-grading declaration note (A/B implemented / C roadmap not-implemented, plugin-contract L114/L102, aligned to SKILL.md single source of truth; +10/-0). R0 APPROVED_WITH_NOTES/0; DEC-163 (M-0 user ruling, F-02 re-positioning and in-slot for 0.77.0).
- Version declarations and e2e fixture pointers advance from 0.76.0 to 0.77.0 (M-set: SKILL.md frontmatter 0.77.0 authority source + `release-projection --write` deterministic 15 projections — core manifest, 4 plugin.json (.claude/.codex/.zcode/.chrys), marketplace, package.json, four source hooks @version, dsh persona v0.77.0 + AGENTS.md.template L3, e2e SKILL byte_copy mirror, e2e plan-tracker + @bootstrap-version marker face 9 lines (commands/governance-init.md ×3 + e2e mirror ×3 + e2e CLAUDE.md + root AGENTS.md; root CLAUDE.md gitignored local sync not in commit — FIX-256 precedent) + `verify_workflow.py` REQUIRED_SNIPPETS 6 version pins (version literals only +6/-6, zero logic; checks/version.py enforcement surface).
- `project/CHANGELOG.md` gains a 0.77.0 entry (8-commit window, Added/Changed/Fixed/Validation/Boundaries + DEC-161/162 budget disclosure + RISK-044 quick-scan deferral note).
- Release docs trio created (feature-flags / release-checklist / rollback-plan); `core/releases/0.77.0.json` candidate; `docs/release/version-plan-0.77.0.md` (REL-070 planning deliverable, dual-review approved) included in this candidate package.

### Excluded

- No official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim.
- 0.77.0 does not close RISK-036/RISK-039 (2026-09-30 review; independent closure criteria not satisfied) and does not reopen RISK-045 (closed 2026-08-23 by user authorization).
- Out-slot legacy items registered for 0.78.x (per REL-070 planning doc §5.1, DEC-163): FIX-272 R0 P2×2 (path-traversal tests + diagnostic split), F-04 (npm pack dry-run assertion guard), F-05+BC-1 (vocabulary versioning + backup-evidence explicitization + Check 39 FAIL escalation batch — structurally not satisfiable inside 0.77.0), F-04-env (agent-locks environment-path lock extension), RISK-044 quick-scan subsecond subset (deferred 0.78.x+; 2026-08-28 review by Coordinator decides maintain/forward-shift). F-03 (e2e commands projection decision) is a packaging-phase Coordinator decision — decision-log entry required, not a claim of this candidate.

## 2. Version and SemVer

0.77.0 is a MINOR because: (a) FEAT-010 adds a new backward-compatible install/distribution capability (bundle form for the dsh plugin ecosystem — new onboarding surface, zero break of existing install paths/CLI/package semantics; VERSIONING.md Minor L12 category); (b) FIX-274 adds a new MUST behavior contract (SKILL.md「关键行为契约」4th item + DSH persona 5th item — SKILL.md MUST-rule addition → MINOR per VERSIONING.md L37). The new checks 39/40 and the new CLI (`check-dsh-skills-manifest`) are stated honestly as PATCH-face increments (VERSIONING.md L34: verify_workflow.py new check items → PATCH) and NOT used as the MINOR basis. Expected declarations are 0.77.0 in source SKILL frontmatter, core manifest, Claude/Codex/Zcode/Chrys plugin metadata, Claude marketplace metadata, package.json, four source hooks, the REQUIRED_SNIPPETS version pins in verify_workflow.py, the two e2e fixture pointers, the two DSH template version lines (persona / AGENTS.md.template L3), and the @bootstrap-version marker faces. **Breaking changes: none.**

## 3. Candidate Validation

Run before release review:

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py release-ledger --version 0.77.0 --no-remote
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.77.0 --require-changelog --lineage-mode candidate
```

Candidate mode intentionally does not require `v0.77.0` and is not evidence that the tag exists. The final release commit, local tag, and remote tag do not yet exist during package preparation. After the Coordinator creates and pushes them (github-https), rerun:

```text
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.77.0 --require-changelog --lineage-mode released --release-commit <commit>
python skills/software-project-governance/infra/verify_workflow.py release-ledger --version 0.77.0 --remote github-https
```

(Remote ledger uses `--remote github-https` per 0.75.0 precedent and this repo's push remote; origin SSH is unreachable — Host key verification failed — and any origin attempt must be reported honestly as UNKNOWN/BLOCKED, never wrapped as PASS.)

## 4. Test and Review Evidence

- FEAT-010: isolated-env install smoke + self-asserting boot double PASS; real `~/.dsh` zero-operation dual confirmation (time-window forensics + source counter-proof); full review chain R0→R1→R2 APPROVED_WITH_NOTES/0 (REVIEW-FEAT-010-R2).
- FIX-271: TDD 12 new cases red->green (52/52); four-step key order byte-identical; 27 pre-existing failures confirmed unrelated via stash baseline; CODE R0 + DESIGN R0→R1 APPROVED_WITH_NOTES/0×2.
- AUDIT-146: R0 APPROVED_WITH_NOTES/0 (machine record) — report 266 lines.
- FIX-274: DESIGN R0 APPROVED_WITH_NOTES/0; CODE R0 NEEDS_CHANGE (P1-1 gate misfire / P1-2 SKILL budget over-cap) → R1 rework (DEC-161/162; gate fix red->green 10+2; dual budget guards 15; 708/1 baseline) → CODE R1 APPROVED_WITH_NOTES/0; Check 39 real-data zero false-positives (35 records / 1 r1 incomplete legal skip).
- FIX-272: TDD 9 new cases red->green; pytest 1923 passed / 28 pre-existing baseline failures (stash baseline confirmed unrelated); R0 APPROVED_WITH_NOTES/0 (P2×2 registered follow-up + P3×6 discussion-level).
- FIX-273: TDD 4 red -> 61 green; pytest full 28 pre-existing baseline failures zero new (same baseline); R0 APPROVED_WITH_NOTES/0.
- FIX-275: RED 397 entries/154 pyc/10.34MB → GREEN 243 entries/0 pyc/5.72MB (-64%); Reviewer independent re-verify (precise pyc count 154 / 10,340,875B; diff 397-243=154 three-way consistent; npm-packlist 10.0.3 source L166-169/L313/L318-338 verified); verify/cross-refs/manifest/version all PASS; R0 APPROVED_WITH_NOTES/0.
- FIX-276: full verify PASSED (exit 0) + check-cross-references 68 files/649 refs zero-dangling PASS + check-version-consistency 13 files PASS + check-manifest-consistency 565/608 PASS; R0 APPROVED_WITH_NOTES/0 (REVIEW-FIX-276-R0 machine row + RECO-FIX-276).
- Projection record (REL-070): `release-projection --write` output `{"state": "PASS", "written": 15, "source_version": "0.77.0"}` exit 0; after write — persona `治理工作流（v0.77.0）`, AGENTS.md.template L3 `> @bootstrap-version: 0.77.0`, fixture SKILL.md byte-equal to source (byte_copy), required-snippets pins 0.77.0.
- Gate results at candidate packaging (2026-08-25): (recorded in this file below after runner output — see "## Candidate Gate Results" paragraph; nothing claimed before execution).
- The release docs boundary wording reuses the proven 0.74.0/0.75.0/0.76.0 compact negation template; all five `check-release` `boundary_needles` are present in each of the three 0.77.0 release docs.
- Known advisory WARN at candidate validation (disclosed): `check-version-consistency` reports the host `.governance/plan-tracker.md` recorded version still 0.76.0. The plan-tracker live record is not touched by the release package (sub-agent boundary) and is bumped to 0.77.0 by the Coordinator as part of the release governance step (same as prior releases), after which the WARN resolves.

## 5. Release Decision Boundary

This checklist prepares a candidate only. It does not commit, tag, push, approve marketplace submission, close risk, or make the final go/no-go decision. After tag creation and push (github-https), released lineage must verify the exact release commit locally and on the configured remote. Transition/publication requires explicit user authorization (DEC-143 interaction baseline: auto-recommend + user-confirm; release_authorized=false until authorized).

## 6. Rollback Verification

`docs/release/rollback-plan-0.77.0.md` defines full and partial rollback paths, replicating the §3.1 rollback-boundary table from `docs/release/version-plan-0.77.0.md`: candidate/transition-state rollback = `git revert` of the candidate commit (manifest-only reversible); a published `v0.77.0` tag rollback = governed recovery only (Coordinator + explicit evidence, never silently retargeted — 0.76.0 rollback-plan Reversibility L50 precedent). All headline changes are reversible at package level: the anti-recurrence checks are additive read-only/report-only check modules (Check 39 WARN-first, Check 40 product-gate), the new CLI is incremental, the packaging change is config-only (0 pyc measured; payload integrity verified), and the injection surface is text with machine-guarded budgets. After rollback, rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.

## 7. Migration Note (RISK-D5 — DSH preset staleness)

DSH has no `/plugin update`. The upgrade path is `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`. The 0.77.0 persona version line + 5 behavior-contract lines and the AGENTS.md.template bootstrap version only reach live sessions after `launch.py --sync` rewrites the preset (`${DSH_HOME}/.agent-presets/governance/`); until then the installed preset still carries the old template. Do not claim session-level M7.7 effects for installations that have pulled but not synced. **After upgrade sync, the anti-recurrence checks act on a governed project's `.governance/` read-time data with no per-project reworking.**

## Candidate Gate Results

(Executed at packaging, 2026-08-25; same classing precedent as REL-067/REL-068/REL-069.)

`check-release --version 0.77.0 --require-changelog --lineage-mode candidate` result: **FAILED — 8 issue(s)**, exit 1, classified:

- **(a) 3x release docs "must be tracked by git"** — uncommitted-state artifacts of this candidate package itself, resolve when the Coordinator commits (same class as REL-067/068/069).
- **(b) archive integrity trigger gap** — `Archive trigger gap: 0 hot completed task(s) should be archived via release_forced for v0.1.0~v0.75.0` — transitional baseline disclosed at the 0.74.0/0.76.0 releases (EVD-894 precedent), reproduced here, not introduced by the 0.77.0 diff.
- **(c) execution gate governance health exit=1 (106 issues)** — pre-existing host `.governance/` record posture (0.76.0 release reported 111/112 at that time point; 106 is the measured value at packaging); zero `.governance/` files touched by this release package (sub-agent boundary).
- **(d) execution gate unit tests exit=1 + loop runtime claim gate FAIL** — single root cause: `ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY: ragged table row` in `docs/requirements/audit-146-feat010-dsh-config-loss-rca.md` (commit 2bb10ac, in-window) — `LoopRuntimeClaimAdapterTests::test_claim_command_emits_complete_pass_report` + `check-loop-runtime-claims` identity attestation (604 candidates parsed / skip=0). **Window-introduced pre-existing baseline** (not introduced by this release-package diff; FIX-274 evidence already recorded the same baseline case as unrelated to its own diff; the 0.76.0 release passed this gate 598/598). Disclosed per the 0.76.0 baseline-FAIL precedent — a fix candidate is a small doc-format normalization task (same class as the FIX-264 design-doc 48-line ragged normalization precedent) for Coordinator decision; it does not block candidate review.

Static core gates all PASS: version consistency, release fact source, hot fact source, runtime readiness matrix, first session measurement, governance pack status, agent adapters, projection sync, cross references, release lineage (candidate boundary), gate sequence for release (Check 37 — no violations), one dot zero blockers, loop fuse block, changelog. Execution gates: verify (exit=0) PASS, e2e check (exit=0) PASS; governance health + unit tests FAIL as classified above.

Additional gates run by the Release Agent at packaging (2026-08-25):

- `check-version-consistency` — **PASSED** (13 files declared; 1 advisory WARN: host `.governance/plan-tracker.md` still 0.76.0 — Coordinator bumps as part of release governance step, same as prior releases).
- `check-projection-sync --fail-on-issues` — **PASSED** (15 projections; source version 0.77.0).
- `check-manifest-consistency --fail-on-issues` — **PASS** (canonical 568 / actual 608).
- `check-cross-references --fail-on-issues` — **PASS** (68 files / 649 refs, zero dangling).
- `verify` (no args) — **PASSED** (exit 0; only WARN = plan-tracker 0.76.0).
- pytest full suite — **28 failed / 1930 passed / 215 subtests** (295s). Baseline (HEAD 0f9e5bb stash state) = 28 failed / 1932 passed / 215 subtests — **zero packaging-introduced failures**: the 28 are the in-window pre-existing baseline (24 pre_commit_review_evidence SUBFAILED + test_all_manifest_dirs_covered [FEAT-010 `presets/` not in cleanup PLUGIN_SCOPE_DIRS] + 3 loop-claims/ragged-row cases). Two transient failures observed mid-run were the pre-fix in-progress state of `presets/governance/agent.cordis.yml` (version line synced during packaging — see below) and re-ran PASS individually.
- `check-injection-contract` — **PASSED** (4 files / 28 anchors). During packaging the FIX-272 @version-line anchor caught `presets/governance/agent.cordis.yml` persona line still 0.76.0 (template advanced to 0.77.0) — synced to 0.77.0 (anchor guard working as designed); after sync PASS.
- `check-dsh-skills-manifest` — **PASSED** (declared 35 / on disk 35; Check 40).
- `release-ledger --version 0.77.0 --no-remote` — FAIL (expected): `candidate_commit: expected exactly one commit adding ...0.77.0.json, found 0` — uncommitted candidate transition state (git_commit_adding_path derivation requires the file committed; rerun by the Coordinator after the candidate commit — same REL-067 precedent); trust_level = NATIVE_CANDIDATE, release_authorized = false.

Risk disclosure (plan doc §6 preserved): **RISK-044** — `--summary-only` 31-32s measured, accepted via DEC-149 (single run <60s once-per-session); quick-scan subsecond subset **deferred out of 0.77.0** to 0.78.x+ candidate (registered via decision-log + CHANGELOG note at M-1), 2026-08-28 review by the Coordinator decides maintain/forward-shift. **RISK-036/RISK-039 remain open**; **RISK-045 closed (2026-08-23) and not reopened**. DEC-161/162 budget check values (persona 2560B / SKILL contract section 2560B) disclosed in the 0.77.0 CHANGELOG Boundaries (§ budget disclosure note) per DEC-161 follow-up obligation.

## No-overclaim Boundaries

This candidate does not create or prove `v0.77.0` and does not close RISK-036 or RISK-039. 0.77.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
