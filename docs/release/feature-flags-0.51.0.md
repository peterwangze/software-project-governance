# Feature Flags - 0.51.0

**Version**: 0.51.0

REL-031 / 0.51.0 publishes the Dynamic Lifecycle Spec as a schema-only registry. It does not introduce a runtime feature flag that changes project behavior. The dynamic lifecycle surface remains data-only until a later version explicitly ships flow-unit runtime support.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| `classic-phase-gate` lifecycle mode | Active/default | Existing G1-G11 behavior remains the runtime path |
| `dynamic-flow-gate` lifecycle mode | Inactive schema-only | Registry data exists, but flow-unit runtime is not activated |
| Lifecycle registry validator | Available on demand | `check-lifecycle-registry --fail-on-issues` validates schema-only boundaries and classic compatibility |
| python_game 10-chapter example | Example data only | Demonstrates multi-lane lifecycle expression; does not migrate or activate a real project |
| Project type hooks | Schema-only | Defaults and templates are validated, but project-type gate execution is not enabled in 0.51.0 |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open and 1.0.0 remains blocked |
| RISK-037 open-risk boundary | Active release boundary | RISK-037 remains open until runtime, presets, declarative gate engine, migration, and external validation are complete |

## Kill Switch and Rollback Boundary

The dynamic lifecycle registry has no runtime activation flag in 0.51.0. If the release package makes `dynamic-flow-gate` active/default, changes classic G1-G11 runtime behavior, migrates projects, or overclaims readiness, revert the 0.51.0 release package and return to 0.50.3 while keeping RISK-036 and RISK-037 open.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
