# Feature Flags - 0.55.2

**Version**: 0.55.2

REL-040 / 0.55.2 publishes the Web console passive summary entry patch. It adds a read-only summary footer command for CLI/client sessions and keeps Web startup explicit-only.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| `web-console --summary-link` | Active | Prints a summary footer with running URL, unavailable state, or manual start command without starting services |
| `web-console --summary-link --start` | Blocked | Read-only summary mode cannot be combined with service startup |
| Manual `/governance` Web startup | Disabled by contract | `/governance` may report status but must not start Web, Vite, `npm run dev`, or `web-console --start` by default |
| `web-console --status` | Active | Discovers current availability and prints manual start commands only when explicitly requested |
| `web-console --start` | Active explicit path | Starts the local Vite Web console only when the user explicitly requests startup |
| Web task execution | Not implemented | The Web console remains status/config visibility only |
| `classic-phase-gate` lifecycle mode | Active/default | Existing classic registry-backed gate judgment remains the runtime path |
| `dynamic-flow-gate` lifecycle mode | Inactive/non-default | 0.55.2 keeps dynamic mode opt-in only and does not migrate projects |
| `dynamic-lifecycle-migration --dry-run` | Preview only | Preserved from 0.55.0 with `write_operations=[]` |
| `dynamic-lifecycle-migration --apply` | Blocked | 0.55.2 intentionally has no apply/write path |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open and 1.0.0 remains blocked |
| RISK-037 open-risk boundary | Active release boundary | RISK-037 remains open until migration and external validation closure criteria are satisfied |

## Kill Switch and Rollback Boundary

0.55.2 is a passive Web summary entry patch. If the release package starts Web services from manual `/governance`, makes Web the primary execution surface, silently installs dependencies, claims Desktop embedded UI or marketplace lifecycle PASS, changes dynamic lifecycle activation, closes RISK-036/RISK-037, or overclaims readiness, revert the 0.55.2 release package and return to 0.55.1 while keeping RISK-036 and RISK-037 open.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No completed non-game preset generalization claim. No Web replacement for CLI/client execution. No default Web service startup from `/governance`. No Web-triggered agent task execution. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
