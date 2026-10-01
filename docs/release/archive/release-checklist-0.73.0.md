# Release Checklist - 0.73.0

**Version**: 0.73.0 (minor)
**Release**: 三链重构（入口/循环/任务规划）生产接线打包（AUDIT-142 / FIX-236 / FIX-237 / FIX-238 / FIX-239 / FIX-240 / FIX-241 / FIX-233~235）
**Date**: 2026-08-03
**Decision**: REL-066 (user authorized release direction on 2026-08-03)
**Candidate parent (B)**: `c14bce7` (FIX-238 entry bootstrap repair, on top of `9768844` FIX-237 triage integration, `f5fad1a` FIX-241, `7894689` FIX-240, `51ebf39` FIX-236, `4d1d9fc` FIX-239, `fd03138` FIX-237, `1dce69f` AUDIT-142, `b26c37c` FIX-233/234/235, and the 0.72.0 released lineage)

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined | PASS - 0.73.0 MINOR; packaging AUDIT-142 (three-chain diagnosis + ADR-017), FIX-236 (loop production wiring: review-record CLI + auto_judge_gate wiring + loop_exit_bridge + Check 30 V6 + call-site AST check), FIX-237 (task-planning data-debt de-cycling + tool filtering/cycle tolerance + change-triage CLI + Check 32 + interaction-boundary evidence-ization), FIX-238 (entry bootstrap repair: vendor bootstrap scripts + resolve timeout fallback + web-console install timeout + @bootstrap-version upgrade chain), FIX-239 (hook locale hardening), FIX-240 (CI pipeline repair), FIX-241 (resolve_entry encoding robustness regression tests), FIX-233/234/235 (Check 30 historical exemptions + release gate timeout + archive evidence migration), FIX-232 (evidence-log column structure repair, governance record); no breaking runtime API |
| 2 | Change list enumerated | PASS - 13 code commits + version projection 0.72.0 -> 0.73.0 + CHANGELOG + candidate manifest + release docs |
| 3 | Independent code review available | PASS - FIX-236 (36 new tests + R1 8 new tests), FIX-237 (33 new tests; R0 NEEDS_CHANGE/1P1 -> R1 APPROVED_WITH_NOTES/0), FIX-238 (29 new tests; R0/R1 APPROVED_WITH_NOTES/0), FIX-240 (CI 1527 tests unique failure eliminated), FIX-241 (R0 APPROVED_WITH_NOTES); check-version-consistency PASS (13 declarations), check-projection-sync PASS (13 projections) |
| 4 | Candidate lineage boundary explicit | PASS - candidate mode does not require or prove a tag |
| 5 | Historical tag and official-marketplace overclaims excluded | PASS |

### Included

- FIX-236: `review_record.py` record/reopen/close CLI + structured tokens + evidence write-back; `loop_exit_bridge.py` loop_exit -> next-candidates recommendation bridge (fuse corrupt fail-closed); `loop_gate_processor.py` auto_judge_gate loop wiring; Check 30 V6 review-closure final-state token validation; call-site AST check in `verify_workflow.py` (EVD-875, DEC-139 + ADR-017 §3).
- FIX-237: 237.1 task-priority data-debt de-cycling (12 dependency rows + 15 status backfills, 0 cycle); 237.2/237.3 tool filtering (open/plan tool filter by role) + cycle default exit 0 + WARNING (--strict preserved); 237.4 change-control triage mandatory integration (`change-triage` CLI four-step analysis: dependency snapshot / priority / conflict check / version fit + machine triage records `.governance/change-triage/{id}.json` + TRIAGE- evidence rows + Check 32 CLI wiring AST validation + no-record interception, fail-closed); 237.5 interaction-boundary evidence-ization (EVD-872/873/880).
- FIX-238: vendor `infra/bootstrap.sh` (SPG_RESOLVE_TIMEOUT 15s illegal fallback + four-class classified diagnostics + exit-code contract 0/1/2/3/4/5) + `bootstrap.cmd`; thin `resolve-entry` command (resolve_entry.py body untouched, DEC-096); `SPG_WEB_INSTALL_TIMEOUT` (120s); `@bootstrap-version` stale-marker upgrade chain + 3 profile template injection + host-entry marker (EVD-881).
- FIX-239: hook review-evidence grep/sed locale hardening (`LC_ALL=C`; pre-commit +6/-2, commit-msg +3/-1) eliminating GNU grep UTF-8 traversal false negatives (EVD-874).
- FIX-240: manifest AGENTS.md registration + fresh-checkout unit-test determinism + threading-determinism Linux fix + revert CI debug workflow (EVD-876/877/878).
- FIX-241: resolve_entry encoding robustness regression tests; external cp936 claim verified false, detection gap closed (EVD-879).
- FIX-233/234/235: Check 30 historical review-row terminal-state exemptions + check-release unit-test timeout parameterization (180s -> configurable) + archive evidence migration (release-forced version-range advancement + evidence-only migration) (EVD-868/869).
- AUDIT-142: three-chain diagnosis report (`docs/requirements/entry-loop-planning-rearchitecture-0.72.0.md`) + ADR-017 (`docs/adr/ADR-017-loop-wiring-and-task-planning-0.73.0.md`); REQ-104/105/106 delivered (EVD-871).
- FIX-232: evidence-log column structure repair (20 rows evidence_col_mismatch to zero; governance record, EVD-867).
- Version declarations and e2e fixture pointers advance from 0.72.0 to 0.73.0 (M-set: plugins, marketplace, package.json, source/e2e SKILL frontmatter, manifest, fixture plan-tracker, four source hooks, and the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`).
- `project/CHANGELOG.md` gains a 0.73.0 entry; release docs trio created.

### Excluded

- No official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim.
- 0.73.0 does not close RISK-036/RISK-039. RISK-039 (architecture-degradation guard) closure still requires ArchGuard validation in an external host project, source/projection double-write elimination, and technical-debt registration closure; RISK-036 requires official marketplace operations (Codex Desktop marketplace E2E / official submission package) that cannot be completed locally. No previously closed risk is reopened.

## 2. Version and SemVer

0.73.0 is a MINOR because it adds the three-chain production wiring (entry bootstrap deterministic fallback, loop engine wiring, task-planning data-debt de-cycling + mandatory change triage) without changing existing plugin runtime APIs or introducing a breaking contract (protocol amendments are MUST-strengthening wording only). Expected declarations are 0.73.0 in source SKILL, manifest, Claude/Codex/Zcode/Chrys plugin metadata, Claude marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, and the two e2e fixture pointers.

## 3. Candidate Validation

Run before release review:

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.73.0 --require-changelog --lineage-mode candidate
```

Candidate mode intentionally does not require `v0.73.0` and is not evidence that the tag exists. The final release commit, local tag, and remote tag do not yet exist during package preparation. After the Coordinator creates and pushes them, rerun:

```text
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.73.0 --require-changelog --lineage-mode released --release-commit <commit>
```

## 4. Test and Review Evidence

- FIX-236: 36 new tests red->green + R1 8 new tests (review_record 271 lines / loop_exit_bridge 133 lines / loop_gate_processor 48 lines / test_verify_workflow +241 lines); Code Review APPROVED_WITH_NOTES (EVD-875).
- FIX-237: 33 new tests red->green (test_change_triage 431 lines) + test_task_priority +298 lines; Code Review R0 NEEDS_CHANGE/1P1 -> R1 APPROVED_WITH_NOTES/0 (EVD-880).
- FIX-238: 29 new tests red->green; test_verify_workflow 688 OK; Code Review R0/R1 APPROVED_WITH_NOTES/0 (P2-1 CI fresh-checkout blocker fixed) (EVD-881).
- FIX-240: CI full-suite 1527 tests unique failure eliminated; FIX-241: claim verified false + regression tests (R0 APPROVED_WITH_NOTES) (EVD-878/879).
- `check-version-consistency` PASS (13 version declarations consistent); `check-projection-sync` PASS (13 projections synchronized).
- The release docs boundary wording is verified against the `check_release_docs_coverage` `boundary_needles`: every forbidden-positive-claim phrase returns True (negated), and all five conservative boundary needles (including `RISK-036`) are present in each of the three 0.73.0 release docs.
- Known pre-existing FAIL at candidate validation (disclosed, not introduced by this release): `check-release` archive integrity — "Archive trigger gap: 0 hot completed task(s) should be archived via release_forced for v0.1.0~v0.65.3. Run archive.py migrate --auto." This is the known archive-trigger gap (FIX-158/164/235 evidence-migration debt, RISK-039 domain); the 0.73.0 diff does not touch its inputs and it does not block this release's gates (same posture as 0.71.0/0.72.0).
    - Archive/index count mismatch (Check 3): evidence 337 vs index 327; decisions 50 vs 49; risks 12 vs 11 (FIX-235 bounded migration residue, EVD-870)
    - Unregistered archive files: archive/decisions/decisions-v0.63.1-0.65.3.md; archive/evidence/evidence-v0.63.1-0.65.3.md; archive/risks/risks-v0.63.1-0.65.3.md (FIX-235 residue, RISK-039 domain)
- Known advisory WARN at candidate validation (disclosed): `check-version-consistency` reports the host `.governance/plan-tracker.md` recorded version still 0.72.0. The plan-tracker live record is not git-tracked and is bumped to 0.73.0 by the Coordinator as part of the release governance step (same as the 0.72.0 release), after which the WARN resolves.
- Full-gate execution follows the 0.72.0 precedent: unittest suite (1561 tests OK as of FIX-237; test_verify_workflow 688 OK after FIX-238) + `check-governance` + `e2e-check`, with pre-existing/environmental FAILs disclosed rather than hidden.

## 5. Release Decision Boundary

This checklist prepares a candidate only. It does not commit, tag, push, approve marketplace submission, close risk, or make the final go/no-go decision. After tag creation and push, released lineage must verify the exact release commit locally and on the configured remote.

## 6. Rollback Verification

`docs/release/rollback-plan-0.73.0.md` defines full and partial rollback paths. After rollback, rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.

## No-overclaim Boundaries

This candidate does not create or prove `v0.73.0` and does not close RISK-036 or RISK-039. 0.73.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
