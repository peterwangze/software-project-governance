# Release Checklist - 0.50.1

**Version**: 0.50.1

**Release theme**: REL-028 1.0.0 Release Gate Blocker Guard

## Checklist

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | FIX-130 1.0.0 release blocker guard is included | PASS | `check_one_dot_zero_release_blockers()` is wired into release readiness and is covered by ReleaseReadinessCommand tests |
| 2 | Patch scope is limited to release-gate false-pass protection | PASS | 0.50.1 packages only the guard that keeps 1.0.0 blocked when final evidence is missing |
| 3 | 0.50.1 release docs are present and manifest-covered | PASS | `release-checklist-0.50.1.md`, `feature-flags-0.50.1.md`, and `rollback-plan-0.50.1.md` are listed in `core/manifest.json` |
| 4 | Version declarations are synchronized | PASS | Source SKILL, canonical manifest, Claude/Codex plugin metadata, Claude marketplace metadata, hook @version, target fixture skill, target fixture plan tracker, root plan tracker, CHANGELOG, and REQUIRED_SNIPPETS are 0.50.1 |
| 5 | 0.50.1 release gate is expected to pass | PASS | `check-release --version 0.50.1 --require-changelog --runtime-adapters` must pass after this package is prepared |
| 6 | 1.0.0 release gate remains blocked | PASS | `check-release --version 1.0.0 --require-changelog --runtime-adapters` must fail with explicit blockers for RISK-036, external validation full PASS, official submission result/approval, and Codex Desktop lifecycle PASS or conservative disposition |
| 7 | RISK-036 remains open | PASS | 0.50.1 does not claim official approval, marketplace approval, external validation full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready |

## Release Boundary

0.50.1 is a patch release for release-gate honesty. It packages FIX-130 so a future `check-release --version 1.0.0` cannot appear blocked only by missing 1.0.0 release docs while hiding the real hard blockers.

The expected 1.0.0 blockers remain:

- RISK-036 is not closed.
- External project validation full PASS evidence is missing.
- Official submission result or approval evidence is missing.
- Codex Desktop lifecycle PASS or explicit conservative disposition remains required.

0.50.1 does not change the 0.50.0 mainstream agent target-cwd read E2E evidence package. That evidence remains scoped to the read/bootstrap use case and does not become universal/full runtime support.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No RISK-036 closure. No 1.0.0 production-ready.

RISK-036 remains open.
