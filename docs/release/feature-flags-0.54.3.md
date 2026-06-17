# Feature Flags - 0.54.3

**Version**: 0.54.3

REL-038 / 0.54.3 publishes the governance same-package skill fast-start hotfix for FIX-144. It versions the corrected `/governance` command contract for loaded plugin execution. It does not introduce Dynamic Lifecycle runtime activation.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| `/governance` same-package skill fast-start | Active as FIX-144 patch scope | When the command came from a loaded plugin, the default path uses that plugin package's `skills/software-project-governance` skill directly |
| Environment variable startup path | Diagnostic fallback only | `SOFTWARE_PROJECT_GOVERNANCE_HOME`, `SPG_HOME`, and `WORKFLOW_HOME` are not required for the loaded-plugin fast-start path |
| LLM skill path discovery | Not active by default | The default command path must not search the repo or spend tokens finding `SKILL.md` when plugin loading already proves the package exists |
| `/governance` command docs | Active compact command contract | Source and target docs remain Chinese, slim, and preserve `状态面板`, `Delivery Trust Snapshot`, `Source facts`, `AskUserQuestion`, and no-overclaim anchors |
| `classic-phase-gate` lifecycle mode | Active/default | Existing 0.54.x classic registry-backed gate judgment remains the runtime path |
| `dynamic-flow-gate` lifecycle mode | Inactive/non-default | 0.54.3 does not make dynamic-flow-gate default and does not migrate projects |
| 0.55.0 migration/external validation planning | Unchanged | 0.55.0 remains the planned Dynamic Lifecycle migration/external validation version |
| Registry automation command execution | Unchanged metadata boundary | 0.54.3 does not change automation command execution behavior |
| FIX-144 regression coverage | Completed before release packaging | GovernanceFastStart 4/4, fast-start JSON, projection sync, e2e-check, cross-reference, manifest, governance health, py_compile, diff check, and Code Reviewer Avicenna approval are recorded |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open and 1.0.0 remains blocked |
| RISK-037 open-risk boundary | Active release boundary | RISK-037 remains open until migration and external validation are complete |

## Kill Switch and Rollback Boundary

0.54.3 is a fast-start hotfix. If the release package regresses `/governance` startup, restores environment variables as prerequisites, restores LLM path search as the default loaded-plugin path, migrates projects, makes `dynamic-flow-gate` default, changes registry automation command execution, closes RISK-036/RISK-037, or overclaims readiness, revert the 0.54.3 release package and return to 0.54.2 while keeping RISK-036 and RISK-037 open.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No registry automation command execution change. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
