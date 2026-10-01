# Release Checklist - 0.66.2

**Version**: 0.66.2 (patch)
**Release**: non-destructive 0.66.1 incident recovery
**Date**: 2026-07-23
**Architecture authority**: `docs/architecture/release-incident-recovery-0.66.2.md` (FIX-214 Design R2)
**Candidate parent (B)**: `22488058f80228f714367231ee2d030948f0ca2e` (accepted S217)

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | SemVer defined | PASS - 0.66.2 PATCH; non-destructive compensation, no breaking runtime API |
| 2 | Candidate parent exact | PENDING - the candidate commit C must have sole parent B=`22488058f80228f714367231ee2d030948f0ca2e`; becomes PASS only after `--assert-candidate-topology --require-path-count 23` |
| 3 | Three serial slice ancestry | PASS - S215(`d3fc6503...`) -> S216(`2d7ae98f...`) -> S217(`22488058...`) accepted and pushed; verified by `verify_rel063_evidence.py --phase pre_c --require-slice-chain S215,S216,S217` |
| 4 | Six slice evidence (E1) | PASS - FIX-215/216/217 code+qa canonical primary/sidecar pairs, result APPROVED/PASS, unresolved_blockers=0 |
| 5 | exact-C Code Review + QA | PENDING - dispatched only after immutable C exists; subject_sha must equal C |
| 6 | Disposable rehearsal (R7) | PENDING - AUDIT-138 atomic rehearsal bound to C, RTO<=900, workspace UNCHANGED, real_origin_invocations=0 |
| 7 | Release Review (R2) | PENDING - bound to C and H1 digest; release_authorized=true; must postdate rehearsal |
| 8 | Evidence gate (E2) | PENDING - `verify_rel063_evidence.py --phase candidate` PASS, transition_authorized=true, release_authorized=false before T |
| 9 | Manifest-only transition T | PENDING - sole parent C, changes only `skills/software-project-governance/core/releases/0.66.2.json` |
| 10 | Annotated tag + atomic push | PENDING - local annotated `v0.66.2` peels T; one atomic push of master(T)+v0.66.2 |
| 11 | Fresh full validation (R3/R6) | PENDING - `--phase full` after push, release_authorized=true, 1800s no-trigger observation |
| 12 | No-overclaim boundary | PASS - no 1.0.0, official, marketplace, runtime activation, historical tag, or 0.66.1 restoration claim |

## 2. Change Inventory (M063 union N063 = 23 paths)

**M063 (15 mutable, version bump 0.66.1 -> 0.66.2 + CHANGELOG):**
- `project/CHANGELOG.md`, `skills/software-project-governance/SKILL.md`, `project/e2e-test-project/skills/software-project-governance/SKILL.md`
- `skills/software-project-governance/core/manifest.json`
- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json`, `.zcode-plugin/plugin.json`, `.chrys-plugin/plugin.json`, `package.json`
- `project/e2e-test-project/.governance/plan-tracker.md` (workflow version projection 0.66.1 -> 0.66.2 per section 4.4)
- 4 hook files (`pre-commit`, `commit-msg`, `post-commit`, `prepare-commit-msg`) `@version` bump

**N063 (8 new files):**
- `docs/release/release-checklist-0.66.2.md`, `docs/release/feature-flags-0.66.2.md`, `docs/release/rollback-plan-0.66.2.md`
- `skills/software-project-governance/core/releases/0.66.2.json` (candidate manifest, recovery_evidence phase=candidate)
- `skills/software-project-governance/infra/release/verify_rel063_evidence.py` (fail-closed evidence gate)
- `skills/software-project-governance/infra/tests/test_verify_rel063_evidence.py`
- `skills/software-project-governance/infra/release/invoke_rel063_rehearsal.ps1`
- `skills/software-project-governance/infra/tests/run_rel063_rehearsal_fixtures.ps1`

T changes ONLY `skills/software-project-governance/core/releases/0.66.2.json` (candidate -> released).

## 3. Release Gate Evidence

The fail-closed evidence gate is `skills/software-project-governance/infra/release/verify_rel063_evidence.py`. It is the accountable owner for rows C2/C3/C5/R1/R2/R7 and produces no independent review proof. The exact_commands sequence (packet REL-063 `exact_execution_contract`) is normative; this checklist does not restate it as authorizing.

```text
python skills/software-project-governance/infra/release/verify_rel063_evidence.py --phase pre_c --require-slice-chain S215,S216,S217 --require-artifact-count 6 --forbid-artifacts exact-C-code,exact-C-qa,release-review --require-transition-absent --require-local-tag-absent v0.66.2 --require-remote-tag-absent origin:v0.66.2 --write-candidate-manifest skills/software-project-governance/core/releases/0.66.2.json
python skills/software-project-governance/infra/release/verify_rel063_evidence.py --assert-staged-path-set M063,N063 --base <B> --require-path-count 23
python skills/software-project-governance/infra/release/verify_rel063_evidence.py --assert-candidate-topology --candidate <C> --parent <B> --require-path-set M063,N063 --require-path-count 23
python skills/software-project-governance/infra/release/verify_rel063_evidence.py --phase candidate --candidate <C> --require-slice-chain S215,S216,S217 --require-all-nine --require-rehearsal --require-release-review --require-distinct-role-sets --require-fix213-supersession --scanner-limit-seconds 8.0 --require-transition-authorized --require-release-authorized false --write-full-manifest skills/software-project-governance/core/releases/0.66.2.json
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.66.2 --require-changelog --lineage-mode candidate
python skills/software-project-governance/infra/verify_workflow.py release-ledger --version 0.66.2 --no-remote
```

## 4. No-overclaim Boundaries

This package is a release candidate only. This agent does not commit, tag, push, make the final go/no-go decision, close risks, or assert external marketplace approval. Independent exact-C Code Review, exact-C QA, Release Review, and the disposable rehearsal are required before T. Specifically:

- No 1.0.0 readiness, official approval, zcode official approval, marketplace approval, curated listing, partnership, universal/full runtime support, or external first-session pilot success claim.
- No runtime activation, migration-validity claim, or 0.67.0 feature.
- No restoration, movement, or publication of local `v0.66.1`; the 0.66.1 boundary remains withdrawn/untrusted per FIX-217.
- No historical tag backfill or unrelated risk closure.
- A local candidate check is not a released check against fresh remote facts; only `--phase full` after push authorizes release.

## 5. Rollback Reference

`docs/release/rollback-plan-0.66.2.md` covers candidate quarantine (before T), transition quarantine (before push), and post-push non-destructive fallback. Published tags are never silently retargeted; any correction uses a newer PATCH candidate, never a rewrite/move of the boundary.
