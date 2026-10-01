# Feature Flags - 0.55.1

**Version**: 0.55.1

REL-039 / 0.55.1 publishes the Web console CLI/client entry patch. It exposes a discoverable local launcher for the optional companion dashboard, but it does not replace the CLI/client workflow or change dynamic lifecycle activation.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| `web-console --status` | Active | Discovers the local companion dashboard URL and boundary from the CLI/client |
| `web-console --start` | Active | Starts the local Vite Web console when dependencies already exist |
| `web-console --start --install` | Explicit first-run path | Installs Web dependencies only when the operator passes `--install` |
| SPG Web identity probe | Active | Treats non-SPG HTTP responses as occupied ports, not as a running dashboard |
| Web first-screen entry panel | Active | Shows CLI/client origin, launch command, and URL copy action |
| Web task execution | Not implemented | The Web console remains status/config visibility only |
| `classic-phase-gate` lifecycle mode | Active/default | Existing classic registry-backed gate judgment remains the runtime path |
| `dynamic-flow-gate` lifecycle mode | Inactive/non-default | 0.55.1 keeps dynamic mode opt-in only and does not migrate projects |
| `dynamic-lifecycle-migration --dry-run` | Preview only | Preserved from 0.55.0 with `write_operations=[]` |
| `dynamic-lifecycle-migration --apply` | Blocked | 0.55.1 intentionally has no apply/write path |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open and 1.0.0 remains blocked |
| RISK-037 open-risk boundary | Active release boundary | RISK-037 remains open until migration and external validation closure criteria are satisfied |

## Kill Switch and Rollback Boundary

0.55.1 is a Web console entry patch. If the release package makes Web the primary execution surface, silently installs dependencies, launches against a non-SPG service, claims Desktop embedded UI or marketplace lifecycle PASS, changes dynamic lifecycle activation, closes RISK-036/RISK-037, or overclaims readiness, revert the 0.55.1 release package and return to 0.55.0 while keeping RISK-036 and RISK-037 open.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No completed non-game preset generalization claim. No Web replacement for CLI/client execution. No Web-triggered agent task execution. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
