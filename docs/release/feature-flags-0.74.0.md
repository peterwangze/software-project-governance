# Feature Flags - 0.74.0

**Version**: 0.74.0 (minor)
**Release**: 入口确定性五修复链打包——archive 双 root / `--auto` 冷却端点 / `--project-root` fail-closed 三端对齐 / 审查遗留清理（FIX-242 / FIX-243 / FIX-244 / FIX-245 / FIX-246）
**Date**: 2026-08-07
**Decision**: REL-067 (0.74.0 MINOR candidate packaging, candidate-only)

## Feature Flag Inventory

0.74.0 introduces no runtime feature flag and no kill-switch-controlled rollout. The release packages five already-merged commits: FIX-242 archive.py dual-root host resolution + `--project-root`, FIX-243 archive `--auto` bounded endpoint with 1-release cooling (DEC-140), FIX-244 archive `--project-root` fail-closed validation, FIX-245 verify_workflow `--project-root` fail-closed validation aligned with archive, and FIX-246 leftover observation cleanup (dual-root rebind + fail-closed reason suffix lock + `.gitattributes` EOL baseline). No external product surface is toggled by a flag; the changes are static verifier logic, archive CLI input contracts, deterministic root resolution, and repository EOL normalization operating under the existing candidate/released lineage model.

| Component | Default | Notes |
| --- | --- | --- |
| Candidate lineage | `--lineage-mode candidate` default | Does not require or prove that a release tag exists. |
| Released lineage | explicit mode | Requires `--release-commit`; verifies local and configured remote tag identity under `HOST_PROJECT_ROOT`. |
| Dual-root resolution (FIX-242) | cwd-first host root | `_resolve_host_root()` prefers resolve_entry host root, falls back to parents[3] dogfood; `--project-root` explicitly rebinds only the host root. |
| `--auto` bounded endpoint (FIX-243) | ledger second-to-last released | `_release_ledger_released_versions()` + `_auto_archive_bounded_endpoint()`; frontmatter no longer advances the endpoint; release-window evidence protected by 1-release cooling. |
| `--project-root` fail-closed (FIX-244/245) | strict validation | Empty/missing/non-directory values exit 2 with classified diagnostics on both archive.py and verify_workflow.py; no flag toggles it. |
| EOL baseline (FIX-246) | `.gitattributes` `*.py text eol=lf` | Locks Python source working-tree line endings to LF; index already 556/556 LF with zero commit diff. |
| Release docs boundary tokens | static documentation | Each 0.74.0 release doc includes the five `check-release` `boundary_needles` and the compact negation wording verified to pass `_line_has_scoped_claim_negation` for every scoped claim phrase. |

## Rollout and Kill Switch

There is no runtime product flag to phase or disable. The changes are statically validated (FIX-242 test_archive 106 passed; FIX-243 115 passed; FIX-244 118 passed; FIX-245 test_verify_workflow 693+87; FIX-246 118 + 695+87 all green; check-version-consistency 13 files PASS; check-projection-sync 13 projections PASS) and internally exercised. Before release, use candidate lineage. After the release commit and `v0.74.0` are created and pushed, use released lineage with the exact commit. A failing released check is the kill switch: stop release completion and correct or roll back the tag/package state; do not weaken the check.

## Test Boundary

- FIX-242: test_archive.py 106 passed (13 new dual-root/CLI tests, red->green); test_verify_workflow 688+87 zero regression; python_game cwd dual-run proof (phantom 134 evidence rows eliminated).
- FIX-243: test_archive.py 115 passed (8 + 1 fail-open type guard tests); test_verify_workflow 688+87 zero regression; dry-run v0.1.0~v0.72.0 / 128 rows; 0.73.0 evidence 9 rows stay hot.
- FIX-244: test_archive.py 118 passed (3 new fail-closed tests); manual matrix 4 scenarios.
- FIX-245: test_verify_workflow 693+87 (5 new fail-closed cases); test_archive 118 zero regression; manual matrix 3 scenarios.
- FIX-246: test_archive 118 passed, test_verify_workflow 695+87 all green; mutation proofs 2 groups; verify_workflow full PASSED.
- check-version-consistency PASS (13 files); check-projection-sync PASS (13 projections). The release docs boundary wording is verified directly against the negation function. No full-suite-green claim is made.

## No-overclaim Boundaries

This candidate does not create or prove `v0.74.0` and does not close RISK-036 or RISK-039. 0.74.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
