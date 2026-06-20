# Feature Flags - 0.55.0

**Version**: 0.55.0

REL-035 / 0.55.0 publishes the Dynamic Lifecycle migration preview and validation archive package. It exposes read-only migration preview tooling and records external validation facts, but it does not introduce a new default lifecycle mode or activate project migration.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| `classic-phase-gate` lifecycle mode | Active/default | Existing classic registry-backed gate judgment remains the runtime path |
| `dynamic-flow-gate` lifecycle mode | Inactive/non-default | 0.55.0 keeps dynamic mode opt-in only and does not migrate projects |
| `dynamic-lifecycle-migration --dry-run` | Preview only | Produces a structured migration preview with `write_operations=[]` |
| `dynamic-lifecycle-migration --apply` | Blocked | 0.55.0 intentionally has no apply/write path |
| Migration guide | Active documentation | `docs/migration/dynamic-flow-gate-migration-0.55.0.md` documents read-only preview and review boundaries |
| VAL-005 `python_game` archive | Completed as partial validation archive | Dry-run `READY_FOR_REVIEW`; installed-state full PASS blocked by target `CLAUDE.md` path assumption |
| VAL-006 `shitu` archive | Completed as partial validation archive | Dry-run `READY_FOR_REVIEW`; non-game preset generalization remains partial and installed-state validation finds native entry/hook drift |
| Registry automation command execution | Unchanged metadata boundary | 0.55.0 does not change automation command execution behavior |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open and 1.0.0 remains blocked |
| RISK-037 open-risk boundary | Active release boundary | RISK-037 remains open until migration and external validation closure criteria are satisfied |

## Kill Switch and Rollback Boundary

0.55.0 is a migration preview and validation archive package. If the release package implements write/apply migration behavior, migrates projects, makes `dynamic-flow-gate` default, claims non-game preset generalization complete, changes registry automation command execution, closes RISK-036/RISK-037, or overclaims readiness, revert the 0.55.0 release package and return to 0.54.1 while keeping RISK-036 and RISK-037 open.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No completed non-game preset generalization claim. No registry automation command execution change. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
