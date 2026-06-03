# 0.40.1-0.42.0 Post-Release Review

Date: 2026-06-04
Task: AUDIT-107
Version scope: v0.40.1, v0.41.0, v0.42.0
Follow-up release: 0.43.0

## Review Scope

This review inspects the actual release chain after v0.40.0:

- `v0.40.1`: GitHub CI clean-checkout hotfix release for FIX-095 / REL-016.
- `v0.41.0`: Official Marketplace Readiness package for AUDIT-105, FIX-096-FIX-099, REL-017.
- `v0.42.0`: Five-Minute Success Path package for AUDIT-106, FIX-100-FIX-104, REL-018.

Source commands and files reviewed:

- `git log --oneline --decorate v0.40.0..v0.42.0`
- `git show --stat --oneline --decorate v0.40.1`
- `git show --stat --oneline --decorate v0.41.0`
- `git show --stat --oneline --decorate v0.42.0`
- `git diff --stat v0.40.0..v0.40.1`
- `git diff --stat v0.40.1..v0.41.0`
- `git diff --stat v0.41.0..v0.42.0`
- `project/CHANGELOG.md`
- `docs/marketplace/official-readiness-gap-analysis-0.41.0.md`
- `docs/marketplace/submission-checklist-0.41.0.md`
- `docs/requirements/five-minute-success-path-0.42.0.md`
- `docs/release/release-checklist-0.40.1.md`
- `docs/release/release-checklist-0.41.0.md`
- `docs/release/release-checklist-0.42.0.md`
- `.governance/plan-tracker.md`
- `.governance/session-snapshot.md`

## Confirmed Good State

| Area | Fact |
| --- | --- |
| 0.40.1 | The release is scoped to the CI clean-checkout hotfix and does not mix new product functionality. Release notes cite GitHub CI success evidence and Python 3.11 / stdlib unittest compatibility. |
| 0.41.0 | Marketplace readiness is deliberately conservative: manifests, README first screen, privacy/security documentation, submission checklist, and assets are present without claiming official acceptance or universal runtime support. |
| 0.42.0 | The first-success path is a narrow local/demo path: Delivery Trust Snapshot, existing-project resume signal, first-run preset guidance, demo harness, and README refinement. Release docs explicitly keep RISK-036 open. |
| No-overclaim boundary | 0.41.0 and 0.42.0 repeatedly state that readiness packages are not official approval, marketplace approval, universal/full runtime support, or 1.0.0 production readiness. |

## Findings

| Finding | Severity | Evidence | Risk | Follow-up |
| --- | --- | --- | --- | --- |
| F-107-1: Cross-session snapshot drift is outside the hot fact-source guard. | P1 | `.governance/session-snapshot.md` still records `session_date: 2026-05-29` and workflow version `0.39.0`, while `.governance/plan-tracker.md` records 0.42.0 released on 2026-06-04. `check-governance --fail-on-issues` passes, so this drift is not currently blocked. | A later agent can restore stale 0.39.0 next-step guidance and misread the active release chain, especially after resume or context compaction. | FIX-105 in 0.43.0: add snapshot freshness/update guard and include session snapshot in hot fact-source consistency checks. |
| F-107-2: The five-minute path has local/demo proof but not measured external first-session proof. | P1 | `docs/requirements/five-minute-success-path-0.42.0.md` defines success as 4/5 external pilot users completing setup/resume and naming one trust signal within 5 minutes; 0.42.0 release checklist proves `first-run-demo --assert-snapshot`, not an external pilot. | The project can honestly show first local value, but cannot yet claim measured first-session adoption readiness. | FIX-107 in 0.43.0: add a timed first-run pilot evidence template/check and publish measured PASS/BLOCKED status. |
| F-107-3: 0.41.0 marketplace readiness and 0.42.0 first-success claims need a single public runtime/readiness matrix in the next release. | P1 | 0.41.0 readiness docs defer cross-harness E2E to 0.43.0; 0.42.0 release docs keep runtime support claims conservative and defer external validation to 0.43.0-0.46.0. | Users and reviewers still need one inspectable matrix that connects plugin entry, runtime state, first-success path, blocked/degraded reasons, and no-overclaim boundaries. | FIX-106 in 0.43.0: publish the cross-harness public matrix for Claude, Codex, Gemini, OpenCode, plus Cursor/Copilot research/minimal validation status. |
| F-107-4: 1.0.0 dependency wording can lag behind newly released readiness versions. | P2 | `.governance/plan-tracker.md` states that 1.0.0 waits for 0.43.0-0.46.0 and external validation, but the 1.0.0 roadmap row still lists release blockers only through REL-017. | The release guard narrative can understate already published 0.42.0 and future 0.43.0 release dependencies. | Covered by FIX-105: extend hot fact-source checks to snapshot and 1.0.0 release-blocker wording. |

## Planned 0.43.0 Additions

| Task | Priority | Requirement | Scope | Done definition |
| --- | --- | --- | --- | --- |
| AUDIT-107 | P1 | REQ-084, REQ-089, REQ-090 | Review v0.40.1-v0.42.0 modifications and map post-release findings into the next release. | This document exists, is committed, and governance records link findings to 0.43.0 follow-up tasks. |
| FIX-105 | P1 | REQ-089 | Session snapshot and 1.0.0 blocker fact-source freshness. | `check-governance` or a focused check detects stale `.governance/session-snapshot.md` version/date guidance and missing current release blockers in 1.0.0 dependency wording. |
| FIX-106 | P0 | REQ-084 | Public cross-harness runtime/readiness matrix. | A tracked matrix states pass/blocked/degraded status for Claude, Codex, Gemini, OpenCode, and Cursor/Copilot research/minimal validation, with commands, dates, and no-overclaim boundary. |
| FIX-107 | P1 | REQ-090 | Five-minute first-session measurement evidence. | A tracked pilot/stopwatch evidence template and checker distinguish local demo PASS from external pilot PASS/BLOCKED; 0.43.0 release notes publish the current measured status. |
| REL-019 | P0 | REQ-084, REQ-089, REQ-090, RISK-036 | Release 0.43.0. | Version bump, changelog, release docs, matrix/evidence artifacts, release review, commit, push, and tag. |

## Release Boundary

0.43.0 should not close RISK-036 by itself unless the broader risk closing standard is also met. It should close the next concrete gap: make runtime/readiness status public, machine-checkable, and current enough that 0.41.0/0.42.0 claims are not interpreted beyond their evidence.
