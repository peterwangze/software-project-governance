# Feature Flags - 0.50.2

**Version**: 0.50.2

REL-029 / 0.50.2 adds a command surface, not a runtime feature flag. The new `external-project-validation` command is opt-in and does not change default governance execution behavior.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| `external-project-validation` command | Available on demand | Runs only when explicitly invoked with `--target`; it does not mutate the target project |
| Temporary external validation profile | Generated in isolated workspace | Used only for harness execution and guarded by sentinel-scoped hot fact-source behavior |
| 0.50.2 release package | Available as versioned release docs and metadata | Packages FIX-131 only; does not add approval evidence or close RISK-036 |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open and 1.0.0 remains blocked |

## Kill Switch and Rollback Boundary

The command is opt-in. If the harness gives false PASS results, mutates the target, or weakens the no-overclaim boundary, revert the 0.50.2 release package and return to 0.50.1 while keeping 1.0.0 blocked.

## No-Overclaim Boundary

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No RISK-036 closure. No 1.0.0 production-ready.

RISK-036 remains open.
