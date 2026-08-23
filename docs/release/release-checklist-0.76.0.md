# Release Checklist - 0.76.0

**Version**: 0.76.0 (minor)
**Release**: 看护模式七项 + /governance 性能修复打包——REQ-145.1~145.7 七项落地（AUDIT-145 诊断 → FIX-263 设计 → FIX-264~269 实现链）+ FIX-270 /governance 性能修复，随行 FIX-255/256/258、AUDIT-144、FIX-260/261/262（REQ-107/108 消费方）、DOC-002
**Date**: 2026-08-23
**Decision**: REL-069 (0.76.0 MINOR candidate packaging, candidate-only; user authorized launch via completion-recommendation confirm 2026-08-23, see plan-tracker REL-069 row)
**Candidate parent (B)**: `db1078f` (FIX-269, on top of `4e3d08a` FIX-267, `15051c1` FIX-266, `3a819d0` FIX-268, `cba247b` FIX-265, `1479fcc` FIX-270, `1e9cc4a` DOC-002, `66fa210` FIX-264 (+ FIX-263 design doc), `cc79dd0` FIX-262, `3fd5adf` FIX-261, `8922c6e` FIX-260, `e15d453` AUDIT-144, `bae9d5f` FIX-258, `18dc6d7` FIX-256, `347dd64` FIX-255, and the 0.75.0 released lineage `543550c` / tag `v0.75.0`)

> Range fact: `git rev-list --count v0.75.0..HEAD` = 15 commits (git describe `v0.75.0-15-gdb1078f`). The 0.76.0 release carries all fifteen; FIX-263~269 + FIX-270 carry the MINOR semantics (watchdog seven + performance), the remaining eight ride along (FIX-260/261/262 = REQ-107/108 consumers, FIX-255/256/258 = post-release debt/test hardening, AUDIT-144 = read-only diagnosis, DOC-002 = project principles projection).

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined | PASS - 0.76.0 MINOR; headline: watchdog-mode seven (REQ-145.1~145.7 — bootstrap health summary `--summary-only` / Check 35 snapshot freshness / Check 36 risk-mitigation closure / Check 37 gate-release interlock / Check 38 CI evidence / capability grading declaration) + /governance performance (FIX-270); eight ride-along commits; no breaking runtime API |
| 2 | Change list enumerated | PASS - 15 code commits + version projection 0.75.0 -> 0.76.0 + CHANGELOG + candidate manifest + release docs |
| 3 | Independent code review available | PASS - FIX-264 (R0/R1 APPROVED_WITH_NOTES/0), FIX-265 (R0 APPROVED_WITH_NOTES/0), FIX-266 (R0/R1 APPROVED_WITH_NOTES/0), FIX-267 (R0 NEEDS_CHANGE -> R1 APPROVED_WITH_NOTES/0), FIX-268 (R0/R1 APPROVED_WITH_NOTES/0), FIX-269 (R0 APPROVED_WITH_NOTES/0), FIX-270 (R0/R1 APPROVED_WITH_NOTES/0), FIX-260/261/262 (R0 APPROVED_WITH_NOTES/0 each — machine-persisted REVIEW-FIX-260/261/262-R0), FIX-255/256/258 (R0 APPROVED_WITH_NOTES/0 each); check-version-consistency PASS, check-projection-sync --fail-on-issues PASS (15 projections) |
| 4 | Candidate lineage boundary explicit | PASS - candidate mode does not require or prove a tag |
| 5 | Historical tag and official-marketplace overclaims excluded | PASS |

### Included

- FIX-263/264 (66fa210): REQ-145.1+145.7 — `check-governance --summary-only` subcommand (reuses full engine, `_aggregate_check_summary`, `--level` tiers, fail-safe degradation) + session protocol M4.1 new step + SKILL.md injection summary section (A3: SKILL/M4.1, NOT persona — contract block 1535/1536B budget) + DEC-149 threshold alignment. Design doc `audit-145-watchdog-design-0.76.0.md` + `audit-145-watchdog-gap-0.76.0.md` committed with implementation (FIX-263 deliverable).
- FIX-265 (cba247b): REQ-145.3 — Check 36 check_risk_mitigation_closure (risk_domain.py extension, R1-R5 content-dimension verdicts, task_priority ✅ rule authority DEC-151, fail-safe WARN).
- FIX-266 (15051c1): REQ-145.4 — Check 37 check_gate_sequence_for_release (gate_domain.py, line-order derivation, G-s1/G-s2/G-s3, embedded in check_release_readiness + cmd_check_release BR-4 auto-released).
- FIX-267 (4e3d08a): REQ-145.5 — Check 38 check_ci_evidence (ci_domain.py, C1-C4 verdicts, multi-path probes, never-raise guard).
- FIX-268 (3a819d0): REQ-145.2 — Check 35 check_snapshot_freshness (snapshot_domain.py, S1a-S1d, 7d+10commit AND-threshold FAIL, DEC-152 rulings).
- FIX-269 (db1078f): REQ-145.6 — capability grading declaration (SKILL.md A/B/C level section + per-line annotations + commands/governance.md B-level annotation + e2e SKILL.md mirror sync).
- FIX-270 (1479fcc): /governance performance — (A) status fast path (<2s Scenario F data, `--json`, skip_evidence_log); (B) host check-governance speedup (22 product self-checks skipped by default, `--product-gates` explicit, 25.49s→2.40s -91%); (C) mixed-root fixes (Check 28s/25/28c host-rooted).
- FIX-260 (8922c6e): REQ-107 consumer — review conclusion machine persistence (review-record CLI, Check 30c V7/V8, WARN-only + effective-date exemption) — first machine-marked review record repo-wide.
- FIX-261 (3fd5adf): pre-commit/commit-msg review-evidence regex aligned to machine row format (dual-branch, legacy verbatim, 11-column machine form strict).
- FIX-262 (cc79dd0): REQ-108 consumer — machine-verified completion recommendation loop (`--evidence-task` flag, Check 34 S1/S2/S3, RECO-machine rows, DEC-147).
- FIX-258 (bae9d5f): FIX-254 debt pack (visit budget 10,000, diamond tests, pure-refactor split).
- FIX-256 (18dc6d7): @bootstrap-version marker face 0.75.0 alignment (9 lines) + EntryBootstrapTemplate assertion dynamization + FIX-255 F-1 single-source derivation (0.76.0 version-literal recurrence channel closed).
- FIX-255 (347dd64): CI red fix — test_change_triage CLI fixture version literal 0.74.0->0.75.0 alignment (test-only).
- AUDIT-144 (e15d453): dependency blind-spot read-only diagnosis (hot pointer row recommendation — via facts/assumptions separated report).
- DOC-002 (1e9cc4a): DEC-150 project quality principles P-v1 projection (AGENTS.md 19 lines P1-P7 + D1-D4).
- Version declarations and e2e fixture pointers advance from 0.75.0 to 0.76.0 (M-set: 4 plugin.json (.claude/.codex/.zcode/.chrys) + marketplace + package.json — 6 version-metadata targets, source/e2e SKILL frontmatter, core manifest, fixture plan-tracker, four source hooks, DSH persona v0.76.0 line + AGENTS.md.template L3, `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, @bootstrap-version marker face 9 lines across commands/governance-init.md x3 + e2e mirror x3 + e2e CLAUDE.md + root AGENTS.md; root CLAUDE.md gitignored local sync not in commit — FIX-256 precedent; 15 projections written deterministically via `release-projection --write`, written=15 exit=0).
- `project/CHANGELOG.md` gains a 0.76.0 entry; release docs trio created.

### Excluded

- No official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim.
- 0.76.0 does not close RISK-036/RISK-039. RISK-039 closure still requires ArchGuard validation in an external host project, source/projection double-write elimination, and technical-debt registration closure; RISK-036 requires official marketplace operations (Codex Desktop marketplace E2E / official submission package) that cannot be completed locally. No previously closed risk is reopened.
- F-02 (README capability-grading note) and F-03 (e2e commands projection decision) are registered as 0.76.x candidates (DEC-157), NOT claims of this candidate. B1-B4 behavioral sampling and observation-item close-outs (P2/P3 items registered by FIX-264~270 chains) are post-release acceptance items, not claims of this candidate.

## 2. Version and SemVer

0.76.0 is a MINOR because it adds new watchdog capabilities without changing existing plugin runtime APIs or introducing a breaking contract: (a) five new content-dimension machine checks (Check 35-38 + Check 30c/34 extensions from FIX-260/262) and the `--summary-only` subcommand (new capability: session bootstrap health summary); (b) `/governance` `status` fast path (new capability: second-level Scenario F rendering); (c) capability grading declaration (new documentation contract); (d) machine-persisted review conclusions + machine-verified completion recommendations (REQ-107/108 consumers). The ride-along commits are fixes/hardening/test alignment with no breaking API change (all CLI additions are incremental; check numbers 35<36<37<38 are additive, no existing checks renamed/removed). Expected declarations are 0.76.0 in source SKILL, core manifest, Claude/Codex/Zcode/Chrys plugin metadata, Claude marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, the two e2e fixture pointers, the two DSH template version lines (persona / AGENTS.md.template L3), and the @bootstrap-version marker faces. **Breaking changes: none.**

## 3. Candidate Validation

Run before release review:

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py release-ledger --version 0.76.0 --no-remote
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.76.0 --require-changelog --lineage-mode candidate
```

Candidate mode intentionally does not require `v0.76.0` and is not evidence that the tag exists. The final release commit, local tag, and remote tag do not yet exist during package preparation. After the Coordinator creates and pushes them, rerun:

```text
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.76.0 --require-changelog --lineage-mode released --release-commit <commit>
```

## 4. Test and Review Evidence

- FIX-264: test_summary_only 15 cases red->green; full 1752 passed+237 subtests (sole failure = pre-existing resolve_entry time-sensitive flaky 00:00-02:00 window, HEAD same failure); R0/R1 APPROVED_WITH_NOTES/0 (REVIEW-FIX-264-R0/R1 machine records).
- FIX-265: 24 cases red->green; full 1792 passed+237 subtests zero existing-assertion change; three-project read-only measured tv FAIL(R2)/router WARN(R3x3)/dogfood WARN(R3x29) — acceptance reached (router R3-layout-drift disclosure, DEC-151); R0 APPROVED_WITH_NOTES/0.
- FIX-266: 41 cases red->green; full 1864 passed+237 subtests 0 failed; tv/router candidate FAIL + released WARN + BR-4 end-to-end [PASS]; this repo 117==117 zero new; R0/R1 APPROVED_WITH_NOTES/0.
- FIX-267: RED 5 failed (incl. real TypeError ERROR) -> GREEN 31 passed; full 1895 passed+237 subtests 0 failed; tv WARN(C2)/router PASS(C4)/host PASS; R0 NEEDS_CHANGE -> R1 APPROVED_WITH_NOTES/0.
- FIX-268: 31 cases red->green; full 1823 passed+237 subtests 0 failed (isolated; timing flaky passed); tv WARN(S1b 4d/72lag)/router PASS (data evolution reported as-is)/dogfood PASS; R0/R1 APPROVED_WITH_NOTES/0.
- FIX-269: full verify PASSED + projection/crossrefs (646->648 zero dangling)/manifest (557/600)/version (13 files 0.75.0 not bumped) all PASS + check-governance 113==113 zero new (A/B Compare-Object); R0 APPROVED_WITH_NOTES/0 zero P0/P1.
- FIX-270: 15 cases red->green; full 1768 passed+237 subtests 0 failed; independent re-verify: tv status 0.47s / check-governance full 2.42s / 0 plugin-path entries; R0/R1 APPROVED_WITH_NOTES/0 (F1/F2/F3 item-by-item verified).
- FIX-260/261/262: full 1696+213 / 1707+0 / 1725+237 0 failed; machine-persisted REVIEW-FIX-260/261/262-R0 + RECO-FIX-262 (first RECO machine row); R0 APPROVED_WITH_NOTES/0 each.
- FIX-255/256/258 (ride-along): 40/40 + 6/6 + 20/20 + 40/40; TDD red->green (Ran 127 -> 128 OK); test_verify_workflow/test_change_triage green; R0 APPROVED_WITH_NOTES/0 each; FIX-256 closes the version-literal recurrence channel (FIX-248/FIX-255 class).
- Projection record (REL-069): `release-projection --write` output `{"state": "PASS", "written": 15, "source_version": "0.76.0"}` exit 0; after write — persona `治理工作流（v0.76.0）`, AGENTS.md.template L3 `> @bootstrap-version: 0.76.0`, fixture SKILL.md byte-equal to source (byte_copy), required snippets pins 0.76.0.
- Gate results at candidate packaging (2026-08-23): (recorded in this file below after runner output — see "## Candidate Gate Results" paragraph; nothing claimed before execution).
- The release docs boundary wording reuses the proven 0.74.0/0.75.0 compact negation template; all five `check-release` `boundary_needles` are present in each of the three 0.76.0 release docs.
- Known advisory WARN at candidate validation (disclosed): `check-version-consistency` reports the host `.governance/plan-tracker.md` recorded version still 0.75.0. The plan-tracker live record is not touched by the release package (sub-agent boundary) and is bumped to 0.76.0 by the Coordinator as part of the release governance step (same as prior releases), after which the WARN resolves.

## 5. Release Decision Boundary

This checklist prepares a candidate only. It does not commit, tag, push, approve marketplace submission, close risk, or make the final go/no-go decision. After tag creation and push, released lineage must verify the exact release commit locally and on the configured remote. Transition/publication requires explicit user authorization (DEC-143 interaction baseline: auto-recommend + user-confirm).

## 6. Rollback Verification

`docs/release/rollback-plan-0.76.0.md` defines full and partial rollback paths. All headline changes are reversible: the watchdog checks are additive read-only check modules (no state written, fail-safe to WARN/no-verdict), `--summary-only` is a new subcommand with zero change to existing output paths, the status fast path is a new command (existing Scenario F behavior superseded by rendering it), and the performance rework keeps dogfood product gates. After rollback, rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.

## 7. Migration Note (RISK-D5 — DSH preset staleness)

DSH has no `/plugin update`. The upgrade path is `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`. The 0.76.0 persona version line and the AGENTS.md.template bootstrap version only reach live sessions after `launch.py --sync` rewrites the preset (`${DSH_HOME}/.agent-presets/governance/`); until then the installed preset still carries the old template. Do not claim session-level watchdog effects for installations that have pulled but not synced. **After upgrade sync, the watchdog checks act on a governed project's `.governance/` read-time data with no per-project reworking** — `check-governance` / `check-release` / `/governance status` operate on the host project's own records.

## Candidate Gate Results

(Executed at packaging, 2026-08-23; same classing precedent as REL-067/REL-068.)

`check-release --version 0.76.0 --require-changelog --lineage-mode candidate` result: FAILED — 6 issue(s), exit 1, classified: (a) 3x release docs "must be tracked by git" — uncommitted-state artifacts of this candidate package itself, resolve when the Coordinator commits (same class as REL-067/068); (b) hot fact-source — `.governance/session-snapshot.md` records latest published release as 0.74.0 while the ledger is at 0.75.0 — pre-existing host `.governance` record staleness (post-REL-068, zero release-package files touch `.governance/`); (c) archive integrity trigger gap for v0.1.0~v0.74.0 with 0 migratable hot completed tasks — the transitional baseline disclosed at the 0.74.0 release (EVD-894), reproduced here, not introduced by the 0.76.0 diff; (d) execution gate governance health exit=1 (111 issues) — pre-existing host `.governance` record posture, zero `.governance` files touched by this release package.

Static core gates all PASS: version consistency, release fact source, runtime readiness matrix, first session measurement, governance pack status, agent adapters, projection sync, cross references, release lineage (candidate boundary), gate sequence for release (Check 37 — no violations, this repo cascade PASS), one dot zero blockers, loop fuse block, changelog, loop runtime claim gate (semantic_verdict=PASS / identity_verdict=PASS, 598/598 parsed, skip=0). Execution gates pass: verify (exit=0), e2e check (exit=0), unit tests (exit=0).

Risk disclosure (RELEASE R0 F-1): **RISK-044** (2026-08-22 registered, status 已接受/DEC-149, deadline 2026-08-28 review) — `--summary-only` wall-clock measured 31-32s, above the design §3.1 `<15s` gate (engine reuse = full-engine runtime; the design "subsecond" premise did not hold on real-machine measurement). DEC-149 accepted and revised the acceptance signal to "single run <60s and once per session" — 31-32s satisfies it; the subsecond quick-scan remains a 0.77+ candidate and does not change 0.76.0 semantics. RISK-044 remains open (accepted/DEC-149); the 2026-08-28 review milestone is tracked by the Coordinator. The "DEC-149 threshold alignment" wording in §4 is this accepted-state disclosure, not a claim that the <15s design gate was met.

## No-overclaim Boundaries

This candidate does not create or prove `v0.76.0` and does not close RISK-036 or RISK-039. 0.76.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
