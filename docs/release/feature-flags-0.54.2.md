# Feature Flags - 0.54.2

**Version**: 0.54.2

REL-037 / 0.54.2 publishes the governance fast-start UX patch for FIX-143. It versions the deterministic `/governance` fast-start path that was already implemented, reviewed, pushed, and verified by CI. It does not introduce Dynamic Lifecycle runtime activation.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| `/governance` fast-start | Active as FIX-143 patch scope | Default Scenario F/status/resume runs `governance-fast-start --json` and returns a compact local hot-state envelope |
| Full skill load for status path | Not active by default | `full_skill_load_required=false`; `skill_entry_path` is data unless initialization, upgrade, diagnosis, deep routing, or role dispatch details are needed |
| `/governance` command docs | Active compact command contract | Source and target docs remain Chinese, slim, and preserve `状态面板`, `Delivery Trust Snapshot`, `Source facts`, `AskUserQuestion`, and no-overclaim anchors |
| `classic-phase-gate` lifecycle mode | Active/default | Existing 0.54.x classic registry-backed gate judgment remains the runtime path |
| `dynamic-flow-gate` lifecycle mode | Inactive/non-default | 0.54.2 does not make dynamic-flow-gate default and does not migrate projects |
| 0.55.0 migration/external validation planning | Unchanged | 0.55.0 remains the planned Dynamic Lifecycle migration/external validation version |
| Registry automation command execution | Unchanged metadata boundary | 0.54.2 does not change automation command execution behavior |
| FIX-143 regression coverage | Completed before release packaging | GovernanceFastStart 3/3, e2e-check, governance context/status tests, release guards, Code Reviewer Singer approval, and CI success are recorded |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open and 1.0.0 remains blocked |
| RISK-037 open-risk boundary | Active release boundary | RISK-037 remains open until migration and external validation are complete |

## Kill Switch and Rollback Boundary

0.54.2 is a fast-start UX patch. If the release package regresses `/governance` startup, restores long default skill loading for status/resume, migrates projects, makes `dynamic-flow-gate` default, changes registry automation command execution, closes RISK-036/RISK-037, or overclaims readiness, revert the 0.54.2 release package and return to 0.54.1 while keeping RISK-036 and RISK-037 open.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No registry automation command execution change. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
