# Feature Flags - 0.54.0

**Version**: 0.54.0

REL-034 / 0.54.0 publishes Declarative Gate Engine classic registry execution for FIX-138. It versions lifecycle registry gate execution metadata and the TOOL-040 guard, but it does not migrate projects or make dynamic-flow-gate the default.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| `classic-phase-gate` lifecycle mode | Active/default | Existing G1-G11 behavior remains the runtime path, now judged from registry definitions |
| `dynamic-flow-gate` lifecycle mode | Inactive/non-default | Registry data, runtime visibility, project-type presets, and classic registry execution exist, but dynamic-flow-gate is not the default lifecycle |
| `gate_execution_registry` | Active for classic judgment | Classic G1-G11 required artifacts, checks, evidence queries, human confirmation policy, severity, and project-type override metadata are read by classic gate judgment |
| `automation_command` entries | Metadata only | Commands describe possible automation surfaces but are not executed by gate judgment in 0.54.0 |
| TOOL-040 Declarative Gate Engine guard | Available through `check-lifecycle-registry` | Validates gate execution registry completeness, executor names, evidence queries, override contract, malformed check fail-closed behavior, and no-overclaim boundaries |
| Gate focused regression coverage | 12/12 PASS in FIX-138 evidence | Release package versions the already reviewed classic registry execution implementation |
| LifecycleRegistry focused regression coverage | 33/33 PASS in FIX-138 evidence | Release package versions registry contract coverage and no-overclaim guard coverage |
| Project migration | Not active | 0.55.0 remains the planned migration/external validation version |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open and 1.0.0 remains blocked |
| RISK-037 open-risk boundary | Active release boundary | RISK-037 remains open until migration and external validation are complete |

## Kill Switch and Rollback Boundary

0.54.0 changes classic gate judgment to use registry definitions, but it does not enable dynamic-flow-gate migration. If the release package migrates projects, makes `dynamic-flow-gate` default, executes registry automation commands during gate judgment, closes RISK-036/RISK-037, or overclaims readiness, revert the 0.54.0 release package and return to 0.53.0 while keeping RISK-036 and RISK-037 open.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No automation command execution by gate judgment. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
