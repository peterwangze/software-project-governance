# Release Checklist - 0.49.0

**Version**: 0.49.0

**Release theme**: REL-026 External Validation and Official Submission Closure

## Checklist

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | VAL-001 external project validation report is recorded | PARTIAL / BLOCKED | `docs/requirements/external-project-validation-0.49.0.md`; `pallets/click` and `psf/requests` target-cwd smoke ran, but full external validation PASS is not claimed |
| 2 | FIX-128 external new-project empty ID guard is consumed | PASS | Empty DEC/EVD/RISK sequences render `no entries found`; full unittest 426/426 and `check-governance --fail-on-issues` passed in FIX-128 evidence |
| 3 | VAL-002 Codex marketplace lifecycle report is recorded | PARTIAL / BLOCKED | `docs/requirements/codex-desktop-marketplace-lifecycle-0.49.0.md`; CLI marketplace source sync is proved, Desktop UI lifecycle remains BLOCKED/NOT_RUN |
| 4 | FIX-126 official submission final bundle review is recorded | PASS WITH BLOCKERS | `docs/requirements/official-submission-final-bundle-review-0.49.0.md`; candidate bundle is coherent, but official result is NOT_AVAILABLE |
| 5 | Version declarations are synchronized | PASS | Source SKILL, manifest, Claude/Codex plugin metadata, Claude marketplace metadata, hook @version, target fixture skill, target fixture plan tracker, and REQUIRED_SNIPPETS are 0.49.0 |
| 6 | Release docs are manifest-covered | PASS | `release-checklist-0.49.0.md`, `feature-flags-0.49.0.md`, and `rollback-plan-0.49.0.md` are listed in `core/manifest.json` |
| 7 | RISK-036 remains open | PASS | 0.49.0 does not claim official approval, marketplace approval, Desktop lifecycle PASS, external validation PASS, or 1.0.0 readiness |

## Release Boundary

0.49.0 packages the External Validation and Official Submission Closure evidence for review. It consumes VAL-001, VAL-002, FIX-126, and FIX-128, but it does not convert partial or blocked evidence into approval, marketplace acceptance, external validation success, Desktop lifecycle success, or 1.0.0 readiness.

VAL-001 remains partial/blocked because the external target smoke used a temporary partial install, had no owner/user pilot, and did not run full Agent Team producer/reviewer E2E. VAL-002 remains partial/blocked because Codex CLI marketplace source sync is not Codex Desktop UI install/enable/invoke/upgrade/uninstall evidence. FIX-126 closes the candidate bundle review only with blockers carried forward.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation PASS. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No 1.0.0 production-ready.

RISK-036 remains open.
