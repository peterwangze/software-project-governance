# Feature Flags - 0.52.0

**Version**: 0.52.0

REL-032 / 0.52.0 publishes Flow Unit Runtime Visibility. It adds an optional hot-state surface that can be read and validated, but it does not enable declarative gate execution or change project lifecycle behavior by default.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| `classic-phase-gate` lifecycle mode | Active/default | Existing G1-G11 behavior remains the runtime path |
| `dynamic-flow-gate` lifecycle mode | Inactive/non-default | Registry data and visibility helpers exist, but dynamic-flow-gate is not the default lifecycle |
| `.governance/flow-unit-runtime.json` | Optional hot state | If absent, status is NOT_FOUND safe; if present, validation is fail-closed |
| `check-flow-unit-runtime` | Available on demand | Validates visibility-only hot state and no-overclaim boundaries |
| Governance context/status flow-unit facts | Visibility only | Reports lanes, per-unit gate state, loop counters, blocked downstream, and rollup facts; it does not execute gates |
| Declarative gate engine | Not active | 0.54.0 remains the planned declarative gate engine version |
| Project migration | Not active | 0.55.0 remains the planned migration/external validation version |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open and 1.0.0 remains blocked |
| RISK-037 open-risk boundary | Active release boundary | RISK-037 remains open until presets, declarative gate engine, migration, and external validation are complete |

## Kill Switch and Rollback Boundary

0.52.0 has no feature flag that changes the active lifecycle engine. If the release package activates declarative gates, migrates projects, makes `dynamic-flow-gate` default, changes classic G1-G11 behavior, closes RISK-036/RISK-037, or overclaims readiness, revert the 0.52.0 release package and return to 0.51.0 while keeping RISK-036 and RISK-037 open.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No declarative gate engine activation. No project migration. No dynamic-flow-gate default. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
