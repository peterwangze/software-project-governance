# Feature Flags - 0.53.0

**Version**: 0.53.0

REL-033 / 0.53.0 publishes Project-Type Gate Presets for FIX-137. It versions lifecycle registry preset data for project types and the TOOL-039 guard, but it does not enable declarative gate execution or change project lifecycle behavior by default.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| `classic-phase-gate` lifecycle mode | Active/default | Existing G1-G11 behavior remains the runtime path |
| `dynamic-flow-gate` lifecycle mode | Inactive/non-default | Registry data, runtime visibility, and project-type presets exist, but dynamic-flow-gate is not the default lifecycle |
| `project_type_gate_presets` | Data contract only | Presets cover game, web-app, mobile-app, library, cli-tool, ai-agent-plugin, and internal-script |
| TOOL-039 Project-Type Gate Presets guard | Available through `check-lifecycle-registry` | Validates preset completeness, hook alignment, profile/project-type orthogonality, default packs, quality budget, acceptance templates, release checks, gate policy, gate standards, and no-overclaim boundaries |
| LifecycleRegistry focused regression coverage | 28/28 PASS in FIX-137 evidence | Release package versions the already reviewed preset implementation; it does not add new engine behavior |
| Declarative gate engine | Not active | 0.54.0 remains the planned declarative gate engine version |
| Project migration | Not active | 0.55.0 remains the planned migration/external validation version |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open and 1.0.0 remains blocked |
| RISK-037 open-risk boundary | Active release boundary | RISK-037 remains open until declarative gate engine, migration, and external validation are complete |

## Kill Switch and Rollback Boundary

0.53.0 has no feature flag that changes the active lifecycle engine. If the release package activates declarative gates, migrates projects, makes `dynamic-flow-gate` default, changes classic G1-G11 behavior, closes RISK-036/RISK-037, or overclaims readiness, revert the 0.53.0 release package and return to 0.52.0 while keeping RISK-036 and RISK-037 open.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No declarative gate engine activation. No project migration. No dynamic-flow-gate default. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
