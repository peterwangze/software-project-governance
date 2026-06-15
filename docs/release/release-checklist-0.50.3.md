# Release Checklist - 0.50.3

**Version**: 0.50.3

**Release theme**: REL-030 External Installed Runtime Field Repair

## Checklist

| # | Item | Status | Evidence |
| --- | --- | --- | --- |
| 1 | FIX-132 installed runtime path resolver is included | PASS | Hooks and governance command templates resolve explicit env, repo-local install, or global plugin cache instead of requiring repo-local `skills/software-project-governance/` in the target |
| 2 | FIX-133 hook message source hardening is included | PASS | pre-commit no longer treats stale `.git/COMMIT_EDITMSG` or `.git/GOV_COMMIT_MSG` as the current commit message source; commit-msg remains authoritative |
| 3 | FIX-134 target-native diagnostics are included | PASS | `external-project-validation --target` reports native entry path assumptions, installed hook drift, stale pre-commit message semantics, and repo-local self-upgrade source diagnostics |
| 4 | VAL-003 shitu archive is correctly bounded | PASS | shitu is recorded as FAIL/PARTIAL diagnostic only; target-native issues remain and target files were not mutated |
| 5 | VAL-004 python_game archive is correctly bounded | PASS | python_game is recorded as FAIL/PARTIAL diagnostic only; installed hook drift remains and target files were not mutated |
| 6 | 0.50.3 release docs are present and manifest-covered | PASS | `release-checklist-0.50.3.md`, `feature-flags-0.50.3.md`, and `rollback-plan-0.50.3.md` are listed in `core/manifest.json` |
| 7 | Version declarations are synchronized | PASS | Source SKILL, canonical manifest, Claude/Codex plugin metadata, Claude marketplace metadata, hook @version, target fixture skill, CHANGELOG, README, and REQUIRED_SNIPPETS are 0.50.3 |
| 8 | 0.50.3 release gate is expected to pass | PASS | `check-release --version 0.50.3 --require-changelog --runtime-adapters` must pass after this package is prepared |
| 9 | RISK-036 remains open | PASS | 0.50.3 does not claim official approval, marketplace approval, two real external projects full PASS, Codex Desktop lifecycle PASS, RISK-036 closure, or 1.0.0 production-ready |

## Release Boundary

0.50.3 packages the external installed runtime field repair scope. It repairs real installed-state blind spots found after 0.50.2: repo-local workflow home assumptions, stale hook commit-message semantics, and missing target-native diagnostics for installed hooks and native entry files.

The expected 1.0.0 blockers remain:

- RISK-036 is not closed.
- Two real external project validation full PASS evidence entries are still missing.
- Official submission result or approval evidence is missing.
- Codex Desktop lifecycle PASS or explicit conservative disposition remains required.

VAL-003 and VAL-004 are diagnostic archives. Their FAIL/PARTIAL results prove the enhanced harness can find real target installed-state problems without mutating the target; they do not prove the targets are fully validated.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No RISK-036 closure. No 1.0.0 production-ready.

RISK-036 remains open.
