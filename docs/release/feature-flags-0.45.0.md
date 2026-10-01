# Feature Flag Status - 0.45.0

**Version**: 0.45.0
**Type**: Minor release

## Runtime Feature Flags

None. 0.45.0 does not introduce runtime feature flags.

## Behavior Switches

No new user-configurable behavior switches. 0.45.0 adds diagnostic and validation surfaces:

- `capability-context [--fixture <project-root>] [--fail-on-issues]`
- `check-capability-registry [--fail-on-issues]`
- `check-host-capability-context [--fixture <project-root>] [--fail-on-issues]`

These commands are read-only diagnostics or guards. They do not install plugins, call network APIs, open browsers, mutate Desktop state, commit, push, or submit marketplace artifacts.

## Capability And Pack State

| Surface | 0.45.0 state | Boundary |
|---|---|---|
| `governance-core` pack | Version and release command synchronized | Pack membership is not task evidence, independent review, quality gate, release gate, official approval, marketplace approval, universal/full runtime support, or 1.0.0 production-ready proof |
| `release-governance` pack | Release gate now references 0.45.0 | Release checks do not prove official approval or marketplace approval |
| `capability-registry.json` | Available as canonical catalog | Catalog entry is not runtime PASS, external capability available, automatic best-tool selection, or universal plugin/skill/tool availability |
| `capability-context` | Available as read-only selection trace | Diagnostic trace is not successful external execution |
| `check-host-capability-context` | Available as restricted benchmark guard | Test-time fixture is not Desktop marketplace-management E2E PASS |
| Codex Desktop marketplace-management E2E | BLOCKED / NOT_RUN | No real Desktop add/install/enable/invoke/upgrade/uninstall evidence exists in this release package |

## Kill Switch

The emergency kill switch is reverting the 0.45.0 release package commit after it exists. There is no independent runtime flag to disable the release package. Rollback plan: `docs/release/rollback-plan-0.45.0.md`.

## Non-Goals

- No official approval.
- No marketplace approval.
- No universal/full runtime support.
- No external first-session pilot success.
- No Codex Desktop marketplace-management E2E PASS.
- No automatic best-tool selection.
- No universal plugin/skill/tool availability.
- No catalog entry runtime PASS.
- No 1.0.0 production-ready claim.
- No telemetry, hosted backend, external policy URL, or legal terms URL change.
- No RISK-036 closure.

## Rollback

See `docs/release/rollback-plan-0.45.0.md`.
