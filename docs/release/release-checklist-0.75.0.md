# Release Checklist - 0.75.0

**Version**: 0.75.0 (minor)
**Release**: 关键行为规则注入面 + 空推荐降级打包——REQ-112/REQ-110 双落地（DEC-143 前置放大器；FIX-253 DEC-144 方案 A / FIX-254），随行 FIX-247~252 六个观察项/债务 commit 与 AUDIT-143
**Date**: 2026-08-21
**Decision**: REL-068 (0.75.0 MINOR candidate packaging, candidate-only; user confirmed immediate packaging via AskUserQuestion 2026-08-21)
**Candidate parent (B)**: `d90c167` (FIX-253 injection surface, on top of `38c5c32` FIX-254 empty-recommendation fallback, `7310cd7` AUDIT-143, `439f8b4` FIX-252, `0dc1786` FIX-251, `856301e` FIX-250, `113a959` FIX-249, `9ce4e19` FIX-248, `c9739d0` FIX-247, and the 0.74.0 released lineage `3a64d54` / tag `v0.74.0`)

> Range fact: `git rev-list --count v0.74.0..HEAD` = 9 commits (git describe `v0.74.0-9-gd90c167`). The 0.75.0 release carries all nine; FIX-253/FIX-254 carry the MINOR semantics, FIX-247~252 + AUDIT-143 ride along (all "no version bump" commits consolidated into this release window).

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined | PASS - 0.75.0 MINOR; two headline commits (FIX-253 REQ-112 key behavioral rules into deterministic injection surface, DEC-144 plan A: dual-point minimal injection + version-projection anchoring + anchor check; FIX-254 REQ-110 empty-recommendation fallback: unblock-chain recommendation + structured empty reason); six ride-along hardening commits (FIX-247~252) + AUDIT-143 audit report; no breaking runtime API |
| 2 | Change list enumerated | PASS - 9 code commits + version projection 0.74.0 -> 0.75.0 + CHANGELOG + candidate manifest + release docs |
| 3 | Independent code review available | PASS - FIX-253 (Design R0 APPROVED_WITH_NOTES/0 + DEC-144 user confirmation + Code R0 APPROVED_WITH_NOTES/0), FIX-254 (Code R0 APPROVED_WITH_NOTES/0 with F-1 P1 fixed in-round), FIX-247 (R0 APPROVED/0), FIX-248 (R0 APPROVED/0), FIX-249 (R0/R1/R2 APPROVED_WITH_NOTES/0), FIX-250 (R0 APPROVED_WITH_NOTES/0), FIX-251 (R0 APPROVED_WITH_NOTES/0), FIX-252 (R0 NEEDS_CHANGE -> R1 APPROVED_WITH_NOTES/0); check-version-consistency PASS, check-projection-sync --fail-on-issues PASS (15 projections) |
| 4 | Candidate lineage boundary explicit | PASS - candidate mode does not require or prove a tag |
| 5 | Historical tag and official-marketplace overclaims excluded | PASS |

### Included

- FIX-253 (d90c167): REQ-112 key behavioral rules into deterministic injection surface (DEC-144 plan A). DSH persona contract block 4 lines 1404B<=1.5KB (R1 re-review-must / R2 completion-must-recommend / R3 options-must-carry-rationale) into `adapters/dsh/agent.cordis.yml.template` L59-62; L33 version drift v0.73.0->v0.74.0 fixed and machine-anchored; SKILL.md "关键行为契约" section 1623B<=2KB (canonical projection definition point) + e2e fixture byte_copy regenerated; AGENTS.md.template single-line pointer; version-projections.json +2 transformed_text projections (dsh-persona-version / dsh-agents-bootstrap-version) + manifest projection_ids sync (15=15); verify_workflow.py INJECTION_CONTRACT_ANCHORS (12 anchors) + check_injection_contract() + Check 33 + standalone fail-closed subcommand; test_dsh_adapter version assertions dynamized from SKILL frontmatter; behavior-protocol.md canonical annotation + step 6b/6c rewrite (EVD-FIX-253).
- FIX-254 (38c5c32): REQ-110 empty-recommendation fallback. task_priority.py UnblockRecommendation + _walk_blocker_roots (unknown_dependency / non_executable_status / cycle; diamond dedup + cycle termination + depth cap 200) + _build_empty_recommendation_fallback (downstream unlock count desc -> priority -> version -> ID strict total order); compute single-point wiring (empty-recommendation only, zero behavior change on normal path); format_report all_blocked branch; loop_exit_bridge.py recommended_fallback/empty_reason key propagation; 19 new tests red->green (EVD-FIX-254).
- FIX-247 (c9739d0): triage record rollback/immutability + bootstrap.sh exit-code contract (EVD-FIX-247).
- FIX-248 (9ce4e19): change-triage CLI test fixture alignment to 0.74.0 (test-only) (EVD-FIX-248).
- FIX-249 (113a959): bootstrap.sh stdlib-fallback diagnostics + 125/126/127 timeout-wrapper distinction + malformed-record immutable boundary (test-only hardening) (EVD-FIX-249).
- FIX-250 (856301e): @bootstrap-version template markers 0.73.0->0.74.0 across projection surface; parse_version_chain stop-at-non-version-row guard; archive --auto dry-run summary N/A; .gitattributes `*.json eol=lf` (EVD-FIX-250).
- FIX-251 (0dc1786): parse_task_dependencies headerless recent-completed window table visibility (live total 124->131) (EVD-FIX-251).
- FIX-252 (439f8b4): _coerce_text str path/text disambiguation + web-console stdout leak fix + fixture alignment (EVD-FIX-252).
- AUDIT-143 (7310cd7): loop engineering effectiveness re-audit report + REQ-107~114 drafts + DEC-143 user decisions (docs/governance records).
- Version declarations and e2e fixture pointers advance from 0.74.0 to 0.75.0 (M-set: plugins, marketplace, package.json, source/e2e SKILL frontmatter, manifest, fixture plan-tracker, four source hooks, DSH persona L33 + AGENTS.md.template L3, and the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`; 15 projections written deterministically via `release-projection --write`, written=15 exit=0 — first release exercising the two FIX-253 projections).
- `project/CHANGELOG.md` gains a 0.75.0 entry; release docs trio created.

### Excluded

- No official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim.
- 0.75.0 does not close RISK-036/RISK-039. RISK-039 (architecture-degradation guard) closure still requires ArchGuard validation in an external host project, source/projection double-write elimination, and technical-debt registration closure; RISK-036 requires official marketplace operations (Codex Desktop marketplace E2E / official submission package) that cannot be completed locally. No previously closed risk is reopened.
- B1-B4 behavioral sampling (FIX-253 design section 9.2) and BR-4/S5 dogfood observations are post-release acceptance items, not claims of this candidate.

## 2. Version and SemVer

0.75.0 is a MINOR because it adds two new capabilities without changing existing plugin runtime APIs or introducing a breaking contract: (a) the deterministic injection surface for key behavioral rules (persona/SKILL contract blocks + version-projection anchoring + anchor check — new capability: session-injected behavior contracts); (b) the empty-recommendation fallback (unblock-chain recommendation + structured empty reason — new capability: recommendation output when all tasks are blocked). The ride-along commits are fixes/hardening with no breaking API change (parser additions guard against previously misparsed rows; CLI input misuse now raises explicit ValueError instead of silent wrong results — fail-closed hardening, not a contract break). Expected declarations are 0.75.0 in source SKILL, manifest, Claude/Codex/Zcode/Chrys plugin metadata, Claude marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, the two e2e fixture pointers, and the two DSH template version lines (persona L33 / AGENTS.md.template L3).

## 3. Candidate Validation

Run before release review:

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py release-ledger --version 0.75.0 --no-remote
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.75.0 --require-changelog --lineage-mode candidate
```

Candidate mode intentionally does not require `v0.75.0` and is not evidence that the tag exists. The final release commit, local tag, and remote tag do not yet exist during package preparation. After the Coordinator creates and pushes them, rerun:

```text
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.75.0 --require-changelog --lineage-mode released --release-commit <commit>
```

## 4. Test and Review Evidence

- FIX-253: S1-S8 all PASS (S4 check-projection-sync 15 projections exit 0; S6 Check 33 PASS + subcommand exit 0; S7 fixture byte-equal 20884B; S8 test_dsh_adapter 18/18); full regression 699+18+107+12+40 green; verify/crossref/manifest PASS; Design R0 APPROVED_WITH_NOTES/0 (4 WARNING reworked and verified) + DEC-144 user confirmation + Code R0 APPROVED_WITH_NOTES/0 (5 P3 non-blocking) (EVD-FIX-253).
- FIX-254: 19 new tests red->green (red phase Ran 119 failures=3 errors=15 -> green 119 OK); full regression 159/159 (task_priority + loop_exit_bridge + change_triage) + test_verify_workflow green; live task-priority-analysis with unblocked=0 now outputs non-empty Unblock pick (FIX-205 [P0], 7 downstream) + structured all_blocked reason; Code R0 APPROVED_WITH_NOTES/0 with F-1 P1 fixed in-round (EVD-FIX-254).
- FIX-247~252 (ride-along): each with evidence + closed review chains (see CHANGELOG 0.75.0 Fixed section); merged regression 159/159 + test_verify_workflow green + test_archive 119 green.
- Projection first-live-run record (REL-068): `release-projection --write` output `{"state": "PASS", "written": 15, "source_version": "0.75.0"}` exit 0; after write — persona L33 `治理工作流（v0.75.0）` (agent.cordis.yml.template, 14456 bytes), AGENTS.md.template L3 `> @bootstrap-version: 0.75.0` (2933 bytes, LF-normalized by the projection engine; git diff shows exactly 1 line changed); fixture SKILL.md sha256 equal to source SKILL.md (byte_copy).
- Gate results at candidate packaging (2026-08-21): `check-version-consistency` PASS (exit 0; 1 advisory WARN — host plan-tracker still 0.74.0, Coordinator bumps it post-packaging); `check-projection-sync --fail-on-issues` PASS (exit 0; 15 projections, both FIX-253 projections in achieved state); `check-manifest-consistency` PASS (exit 0; 554 canonical / 580 actual); `python -m unittest` green — test_release_ledger 39 OK, test_dsh_adapter 18 OK (version assertions dynamized from SKILL frontmatter adapt to 0.75.0 automatically), test_verify_workflow 699 OK (254.9s); `release-ledger --version 0.75.0 --no-remote` reports the expected uncommitted-candidate transitional issue — the `git_commit_adding_path` derivation requires the candidate file to be committed, so the untracked run reports `candidate_commit ... found 0` (trust_level=NATIVE_CANDIDATE, release_authorized=false) and must be rerun after the Coordinator commits; the initial manifest write lacked the canonical trailing LF (CANONICAL_BYTES FAIL on first ledger run) and was corrected to LF-terminated bytes before the recorded rerun; `check-release --version 0.75.0 --require-changelog --lineage-mode candidate` recorded with static gates PASS and execution-gate baseline FAILs disclosed below.
- The release docs boundary wording reuses the proven 0.74.0 compact negation template; all five `check-release` `boundary_needles` are present in each of the three 0.75.0 release docs.
- `check-release --version 0.75.0 --require-changelog --lineage-mode candidate` result: FAILED — 6 issue(s), exit 1, classified per the REL-067 precedent: (a) 3x release docs "must be tracked by git" — uncommitted-state artifacts of this candidate package itself, resolve when the Coordinator commits (same class as REL-067); (b) archive integrity trigger gap for v0.1.0~v0.73.0 with 0 migratable hot completed tasks — the transitional baseline disclosed at the 0.74.0 release (EVD-894), reproduced here, not introduced by the 0.75.0 diff; (c) governance health 217 issues — pre-existing host `.governance` record posture (112 at 0.74.0 packaging, 116 at its release; growth is host-record accumulation, zero `.governance` files touched by this release package); (d) unit tests 180s release-gate timeout — environmental (nested `unittest -v` exceeds 180s; the direct run of the same file is green: 699 OK in 254.9s). Core static gates all PASS: version consistency, release fact source, hot fact source, runtime readiness matrix, first session measurement, governance pack status, agent adapters, projection sync, cross references, release lineage (candidate boundary), one dot zero blockers, loop fuse block, changelog, loop runtime claim gate (semantic PASS / identity PASS, 578/578 parsed).
- Known advisory WARN at candidate validation (disclosed): `check-version-consistency` reports the host `.governance/plan-tracker.md` recorded version still 0.74.0. The plan-tracker live record is not touched by the release package (sub-agent boundary) and is bumped to 0.75.0 by the Coordinator as part of the release governance step (same as the 0.73.0/0.74.0 releases), after which the WARN resolves.

## 5. Release Decision Boundary

This checklist prepares a candidate only. It does not commit, tag, push, approve marketplace submission, close risk, or make the final go/no-go decision. After tag creation and push, released lineage must verify the exact release commit locally and on the configured remote. Transition/publication requires explicit user authorization (DEC-143 interaction baseline: auto-recommend + user-confirm).

## 6. Rollback Verification

`docs/release/rollback-plan-0.75.0.md` defines full and partial rollback paths. Both headline changes are reversible text+code changes: the injection surface is an additive text block with machine-checked anchors; the empty-recommendation fallback only activates on the previously-empty path. After rollback, rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.

## 7. Migration Note (RISK-D5 — DSH preset staleness)

DSH has no `/plugin update`. The upgrade path is `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`. The 0.75.0 persona version line (L33), the persona contract block, and the AGENTS.md.template bootstrap version only reach live sessions after `launch.py --sync` rewrites the preset (`${DSH_HOME}/.agent-presets/governance/`); until then the installed preset still carries the old template. Do not claim session-level injection improvements for installations that have pulled but not synced.

## No-overclaim Boundaries

This candidate does not create or prove `v0.75.0` and does not close RISK-036 or RISK-039. 0.75.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
