# Release Checklist - 0.74.0

**Version**: 0.74.0 (minor)
**Release**: 入口确定性五修复链打包——archive 双 root / `--auto` 冷却端点 / `--project-root` fail-closed 三端对齐 / 审查遗留清理（FIX-242 / FIX-243 / FIX-244 / FIX-245 / FIX-246）
**Date**: 2026-08-07
**Decision**: REL-067 (0.74.0 MINOR candidate packaging, candidate-only)
**Candidate parent (B)**: `1a375e6` (FIX-246 leftover observation cleanup, on top of `9a44898` FIX-245, `d2e454d` FIX-244, `57360b5` FIX-243, `5974ffe` FIX-242, and the 0.73.0 released lineage `515046d`)

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined | PASS - 0.74.0 MINOR; five-fix chain (FIX-242 archive.py dual-root host resolution + `--project-root`; FIX-243 archive `--auto` bounded endpoint with 1-release cooling, DEC-140; FIX-244 archive `--project-root` fail-closed validation; FIX-245 verify_workflow `--project-root` fail-closed validation aligned with archive; FIX-246 leftover observation cleanup: dual-root rebind + fail-closed reason suffix lock + .gitattributes); no breaking runtime API |
| 2 | Change list enumerated | PASS - 5 code commits + version projection 0.73.0 -> 0.74.0 + CHANGELOG + candidate manifest + release docs |
| 3 | Independent code review available | PASS - FIX-242 (R0 APPROVED_WITH_NOTES/0), FIX-243 (R0/R1 APPROVED_WITH_NOTES/0), FIX-244 (R0 APPROVED_WITH_NOTES/0), FIX-245 (R0/R1 APPROVED_WITH_NOTES/0), FIX-246 (R1 APPROVED_WITH_NOTES/0); check-version-consistency PASS (13 declarations), check-projection-sync PASS (13 projections) |
| 4 | Candidate lineage boundary explicit | PASS - candidate mode does not require or prove a tag |
| 5 | Historical tag and official-marketplace overclaims excluded | PASS |

### Included

- FIX-242: `archive.py` dual-root host resolution (mirror of FIX-187): `_resolve_plugin_root()`/`_resolve_host_root()` (resolve_entry.PLUGIN_HOME / resolve_host_root cwd-first, parents[3] dogfood fallback); PLUGIN_ROOT owns plugin assets; ROOT stays the host-fact seam; new `--project-root <path>` CLI for migrate/build-index/verify/rollback (position-independent pre-scan, missing value exit 2, override rebinds only the host root) (EVD-886).
- FIX-243: `archive --auto` bounded endpoint with 1-release cooling (DEC-140): `_release_ledger_released_versions()` reads the release ledger (`core/releases/*.json`, lifecycle_state==released && not withdrawn, 0.66.1 excluded, fail-open on corrupt entries) + `_auto_archive_bounded_endpoint()` (second-to-last released version); endpoint formula = bounded if (bounded >= roadmap endpoint) else roadmap endpoint; frontmatter no longer advances the endpoint (EVD-887).
- FIX-244: `archive.py --project-root` fail-closed validation: `_validate_project_root()` rejects empty values before Path resolution, resolve(strict=True) failures and non-directories emit `spg-archive-error: invalid-project-root — <path> (<reason>)` + exit 2; validation precedes any read/write; aligned line-by-line with resolve_entry.resolve_host_root (EVD-889).
- FIX-245: `verify_workflow.py --project-root` fail-closed validation mirrored verbatim from FIX-244 (`_validate_project_root()` before any host-fact read; `verify_workflow: error: invalid-project-root — <path> (<reason>)` + exit 2; default paths unchanged) (EVD-890).
- FIX-246: FIX-242/244/245 leftover observation cleanup: HOST_PROJECT_ROOT no-rebind assertions + error-reason suffix lock in test_archive.py; `_load_archive_module` dual rebind (module.ROOT + module.HOST_PROJECT_ROOT); new `.gitattributes` (`*.py text eol=lf`, index 556/556 LF, zero commit diff) registered in manifest root_entries.files (EVD-892).
- Version declarations and e2e fixture pointers advance from 0.73.0 to 0.74.0 (M-set: plugins, marketplace, package.json, source/e2e SKILL frontmatter, manifest, fixture plan-tracker, four source hooks, and the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`; 13 projections written deterministically via `release-projection --write`).
- `project/CHANGELOG.md` gains a 0.74.0 entry; release docs trio created.

### Excluded

- No official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim.
- 0.74.0 does not close RISK-036/RISK-039. RISK-039 (architecture-degradation guard) closure still requires ArchGuard validation in an external host project, source/projection double-write elimination, and technical-debt registration closure; RISK-036 requires official marketplace operations (Codex Desktop marketplace E2E / official submission package) that cannot be completed locally. No previously closed risk is reopened.

## 2. Version and SemVer

0.74.0 is a MINOR because it adds the archive/verify_workflow dual-root contract production hardening (host root resolution, `--project-root` fail-closed input validation, bounded `--auto` archive endpoint with release-window cooling, and repository EOL baseline locking) without changing existing plugin runtime APIs or introducing a breaking contract (CLI additions are incremental; default paths have zero behavior change). Expected declarations are 0.74.0 in source SKILL, manifest, Claude/Codex/Zcode/Chrys plugin metadata, Claude marketplace metadata, package.json, four source hooks, the `REQUIRED_SNIPPETS` version pins in `verify_workflow.py`, and the two e2e fixture pointers.

## 3. Candidate Validation

Run before release review:

```text
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync
python skills/software-project-governance/infra/verify_workflow.py release-ledger --version 0.74.0 --no-remote
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.74.0 --require-changelog --lineage-mode candidate
```

Candidate mode intentionally does not require `v0.74.0` and is not evidence that the tag exists. The final release commit, local tag, and remote tag do not yet exist during package preparation. After the Coordinator creates and pushes them, rerun:

```text
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.74.0 --require-changelog --lineage-mode released --release-commit <commit>
```

## 4. Test and Review Evidence

- FIX-242: test_archive.py 106 passed (13 new TestDualRootResolution/TestArchiveCliProjectRoot, red->green 75 failed/31 passed -> 106 passed; 66 ROOT patches zero residue); test_verify_workflow 688 + 87 subtests zero regression; python_game cwd dual-run proof (fixed: correct host resolution/skip vs baseline 134 phantom evidence rows); Code Review R0 APPROVED_WITH_NOTES/0 (EVD-886).
- FIX-243: test_archive.py 115 passed (TestArchiveFix243 8 items + fail-open type guard 1, red->green); test_verify_workflow 688+87 zero regression; repo dry-run range v0.1.0~v0.72.0 (128 evidence rows), 0.73.0 evidence 9 rows stay hot; real ledger 23 manifest cross-check; Code Review R0/R1 APPROVED_WITH_NOTES/0 (EVD-887).
- FIX-244: test_archive.py 118 passed (3 new tests red->green); test_verify_workflow 688+87 zero regression; manual matrix 4 scenarios (exit codes + classified diagnostics); Code Review R0 APPROVED_WITH_NOTES/0 (EVD-889).
- FIX-245: test_verify_workflow 693+87 (5 new cases red->green — HEAD 5 failed); test_archive 118 zero regression; manual matrix 3 scenarios; Code Review R0/R1 APPROVED_WITH_NOTES/0 (EVD-890).
- FIX-246: red-phase 1 failed -> all green; mutation proofs 2 groups restored; test_archive 118 passed, test_verify_workflow 695+87 all green; verify_workflow full PASSED, check-manifest-consistency PASS, check-cross-references PASS; Code Review R1 APPROVED_WITH_NOTES/0 (EVD-892).
- Gate results at candidate packaging (2026-08-07): `check-version-consistency` PASS (13 declarations); `check-projection-sync` PASS (13 projections); `release-ledger --no-remote` for 0.74.0 candidate recorded — the `git_commit_adding_path` derivation requires the candidate file to be committed, so the uncommitted run reports the derivation issue and must be rerun after the Coordinator commits; `check-release` candidate static gates all PASS.
- The release docs boundary wording is verified against the `check_release_docs_coverage` `boundary_needles`: every forbidden-positive-claim phrase returns True (negated), and all five conservative boundary needles are present in each of the three 0.74.0 release docs.
- Known pre-existing FAIL at candidate validation (disclosed, not introduced by this release): `check-release` execution gates — (a) governance health: host `.governance` records report 112 issues (pre-existing host governance-record state, same posture as 0.73.0; not touched by the 0.74.0 diff); (b) unit tests: `unittest test_verify_workflow.py -v` exceeds the 180s release-gate timeout on this machine (environmental; direct pytest run of the same file is green — see Validation section). No new FAIL is introduced by the 0.74.0 M-set; the archive-integrity trigger-gap FAIL disclosed at 0.73.0 is now PASS (FIX-243 bounded endpoint + FIX-246 cleanup).
- Known advisory WARN at candidate validation (disclosed): `check-version-consistency` reports the host `.governance/plan-tracker.md` recorded version still 0.73.0. The plan-tracker live record is not touched by the release package and is bumped to 0.74.0 by the Coordinator as part of the release governance step (same as the 0.73.0 release), after which the WARN resolves.

## 5. Release Decision Boundary

This checklist prepares a candidate only. It does not commit, tag, push, approve marketplace submission, close risk, or make the final go/no-go decision. After tag creation and push, released lineage must verify the exact release commit locally and on the configured remote.

## 6. Rollback Verification

`docs/release/rollback-plan-0.74.0.md` defines full and partial rollback paths. After rollback, rerun version consistency, the applicable candidate/released lineage check, and `git diff --check`.

## No-overclaim Boundaries

This candidate does not create or prove `v0.74.0` and does not close RISK-036 or RISK-039. 0.74.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
