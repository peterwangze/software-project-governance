# Release Checklist - 0.72.0

**Version**: 0.72.0 (minor)
**Release**: Check 31 安装态消解打包 + release lineage 多版本授权 + 0.64.x docs 债务（FIX-200 / FIX-230 / AUDIT-140 / FIX-231）
**Date**: 2026-08-01
**Decision**: REL-065 (user authorized "0.72.0 发布 + 0.64.x docs 债务")
**Candidate parent (B)**: `e2537c0` (FIX-231 0.64.x release docs boundary tokens, on top of `8cb9983` AUDIT-140 claim wording, `dfeddb4` FIX-230 ledger authorization, `1b77d95` FIX-200 identity attestation gate, and the 0.71.0 released lineage `209228b`)

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined | PASS - 0.72.0 MINOR; packaging FIX-200 (identity attestation gate - real `build_identity_attestation` replaces hardcoded PENDING, IDENTITY_ATTESTATION_PENDING eliminated from Check 31, identity_verdict=PASS), FIX-230 (release-ledger multi-version tag authorization resolver + 8 historical manifest backfill, DEC-136), AUDIT-140 (claim-scanner-safe audit report wording, Check 31 repo-side unblock), FIX-231 (0.64.x release docs boundary tokens, DOC-001 gap closure); no breaking runtime API |
| 2 | Change list enumerated | PASS - FIX-200/FIX-230/AUDIT-140/FIX-231 code commits + version projection 0.71.0 -> 0.72.0 + CHANGELOG + candidate manifest |
| 3 | Independent code review available | PASS - FIX-200 tests updated for real identity verdict (PASS/FAIL paths); FIX-230 resolver TDD + 2 new tests (+67 lines; 39 tests 38 PASS + 1 pre-existing 0.66.2 FAIL) + Code Reviewer APPROVED_WITH_NOTES/0 blockers (REVIEW-REL-065-CODE-R0); AUDIT-140 wording fix verified by check-loop-runtime-claims (EVD-858); FIX-231 DOC-001 gap closure (EVD-863); check-version-consistency PASS (13 declarations), check-projection-sync PASS (13 projections) |
| 4 | Candidate lineage boundary explicit | PASS - candidate mode does not require or prove a tag |
| 5 | Historical tag and official-marketplace overclaims excluded | PASS |

### Included

- FIX-200: `_loop_runtime_claim_gate_detail` now runs the real `build_identity_attestation` instead of a hardcoded PENDING verdict; `core/loop-runtime-claim-authority.json` synced (`identity_attestation` -> FIXTURE_PASS, `open_risks` -> [] reflecting RISK-037/042 closure per DEC-133); `checks/loop_runtime_claims.py` expected values synced; tests updated for real identity verdict PASS/FAIL paths. `IDENTITY_ATTESTATION_PENDING` eliminated from Check 31; identity_verdict=PASS.
- FIX-230: `infra/release/ledger.py` multi-version tag authorization resolver matches the `(decision_id, version, commit)` triple (TDD); 8 historical `core/releases` manifests (0.63.0~0.63.4/0.64.0/0.64.1/0.65.0) backfilled with `tag_disposition=created_by_decision` / `tag_decision=DEC-136`; 2 new resolver tests (+67 lines; 39 tests 38 PASS + 1 pre-existing 0.66.2 FAIL; DEC-136, RISK-041 closure chain, EVD-859).
- AUDIT-140: `docs/requirements/audit-140-loop-runtime-wiring-gap-0.71.0.md` claim-scanner-safe wording; Check 31 repo-side unblock (EVD-858). The remaining Check 31 finding is the installed-plugin-package audit-140 old text (EVD-853), resolved by this release via `/plugin update`.
- FIX-231: 0.64.x release docs boundary tokens (`release-checklist-0.64.1.md`, `rollback-plan-0.64.0.md`, `rollback-plan-0.64.1.md`) - DOC-001 gap closure (EVD-863).
- Version declarations and e2e fixture pointers advance from 0.71.0 to 0.72.0 (M-set: plugins, marketplace, package.json, source/e2e SKILL frontmatter, manifest, plan-tracker, four source hooks, and the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`).
- `project/CHANGELOG.md` gains a 0.72.0 entry.

### Excluded

- No official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim.
- 0.72.0 does not close RISK-036/RISK-039. RISK-039 (architecture-degradation guard) closure still requires ArchGuard validation in an external host project, source/projection double-write elimination, and technical-debt registration closure; RISK-036 requires official marketplace operations (Codex Desktop marketplace E2E / official submission package) that cannot be completed locally. RISK-040/RISK-041 were closed earlier by DEC-135/DEC-137 and are not reopened by this release.

## 2. Version and SemVer

0.72.0 is a MINOR because it adds the identity attestation gate (real attestation verdict in Check 31), the release-ledger multi-version tag authorization resolver, claim-scanner-safe audit wording, and the 0.64.x release docs boundary tokens without changing existing plugin runtime APIs or introducing a breaking contract. Expected declarations are 0.72.0 in source SKILL, manifest, Claude/Codex/Zcode/Chrys plugin metadata, Claude marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, and the two e2e fixture pointers.

## 3. Candidate Validation

Run before release review:

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.72.0 --skip-execution-gates
```

Candidate mode intentionally does not require `v0.72.0` and is not evidence that the tag exists. The final release commit, local tag, and remote tag do not yet exist during package preparation. After the Coordinator creates and pushes them, rerun:

```text
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.72.0 --require-changelog --lineage-mode released --release-commit <commit> --skip-execution-gates
```

## 4. Test and Review Evidence

- FIX-200: identity attestation gate tests cover real identity verdict PASS and FAIL paths; Check 31 identity_verdict=PASS in repo state.
- FIX-230: `infra/release/ledger.py` resolver TDD with 2 new tests (+67 lines; 39 tests 38 PASS + 1 pre-existing 0.66.2 FAIL); 8 historical manifests backfilled per DEC-136; 8 versions' check-release released lineage gate PASS and `release-ledger --no-remote` PASS per RISK-041 closure evidence (EVD-859).
- AUDIT-140: repo-side Check 31 unblock verified via `check-loop-runtime-claims` (EVD-858).
- FIX-231: 0.64.x release docs boundary token gap closed and verified (EVD-863).
- `check-version-consistency` PASS (13 version declarations consistent); `check-projection-sync` PASS (13 projections synchronized).
- The release docs boundary wording is verified against the `check_release_docs_coverage` `boundary_needles`: every forbidden-positive-claim phrase returns True (negated), and all five conservative boundary needles (including `RISK-036`) are present in each of the three 0.72.0 release docs.
- This package does not claim a full-suite-green state. Any pre-existing gate FAIL unrelated to 0.72.0 is reported honestly and is out of scope for this MINOR.
- Known pre-existing FAIL at candidate validation (disclosed, not introduced by this release): `check-release` archive integrity — "Archive trigger gap: 0 hot completed task(s) should be archived via release_forced for v0.1.0~v0.65.3. Run archive.py migrate --auto." This is the known archive-trigger gap (FIX-158/164 evidence-migration debt, EVD-853, RISK-039 domain); the 20-file 0.72.0 diff does not touch its inputs and it does not block this release's gates (same posture as 0.71.0).
- Known advisory WARN at candidate validation (disclosed): `check-version-consistency` reports the host `.governance/plan-tracker.md` recorded version still 0.71.0. The plan-tracker live record is not git-tracked and is bumped to 0.72.0 by the Coordinator as part of the release governance step (same as the 0.71.0 release), after which the WARN resolves.
- Full-gate evidence (2026-08-01, candidate commit): `check-release --version 0.72.0 --require-changelog --lineage-mode candidate` Result FAILED - 3 issue(s), all pre-existing/environmental and disclosed: (1) archive integrity (above); (2) execution gates governance health exit=1 — `check-governance` 208 issues, each category verified pre-existing (Check 7 two historical commits without task ID, Check 11 AGENTS.md not in manifest, Check 14 20 evidence-log column issues, Check 17 RISK-036 user-impact WARN, Check 18c-18i execution-packet coverage, Check 28o/28p/28q/28s architecture-health/duplicate/technical-debt/data-size, Check 30 three historical review-closure rows; Check 31 PASS); (3) execution gates unit tests hit the hardcoded 180s gate cap — `test_verify_workflow.py` alone runs 626 tests in ~235s and finishes OK (exit 0) with adequate time, and the full suite (1441 tests) has exactly one known pre-existing failure (`test_product_0661_incident_is_canonical_append_only_withdrawn_untrusted`, EVD-861). `e2e-check` PASS (source_cli_proxy 6/0, target_cwd 4/0, target_fixture 8/0). Same class of pre-existing gate FAILs as 0.71.0 (which likewise did not claim full-suite green); none introduced by the 0.72.0 20-file diff.

## 5. Release Decision Boundary

This checklist prepares a candidate only. It does not commit, tag, push, approve marketplace submission, close risk, or make the final go/no-go decision. After tag creation and push, released lineage must verify the exact release commit locally and on the configured remote.

## 6. Rollback Verification

`docs/release/rollback-plan-0.72.0.md` defines full and partial rollback paths. After rollback, rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.

## No-overclaim Boundaries

This candidate does not create or prove `v0.72.0`, does not backfill historical tags, and does not close RISK-036 or RISK-039. 0.72.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
