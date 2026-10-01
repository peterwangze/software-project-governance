# Feature Flags - 0.56.0

> **ℹ️ Updated in 0.62.0 (FIX-167, DEC-093).** The `project/zcode-local-load.py`
> dev tool listed below was **removed** in 0.62.0 — zcode's newer runtime ships a
> marketplace chain and this plugin now installs via the shared
> Claude/zcode marketplace protocol. See
> [`docs/marketplace/zcode-marketplace-install.md`](../marketplace/zcode-marketplace-install.md).
> The 0.56.0 table below is unchanged as a historical baseline.

**Version**: 0.56.0

REL-042 / 0.56.0 publishes the zcode plugin marketplace adapter patch. It adds the zcode native plugin surface and a local load tool so the plugin can run in the local zcode installation, without changing Web console entry, dynamic lifecycle, or CLI/client execution.

## Flags and Surfaces

| Surface | State | Boundary |
| --- | --- | --- |
| `.zcode-plugin/plugin.json` | Active (adapter surface) | zcode native plugin manifest; fields align with official superpowers/restore-legacy-sessions/skill-creator |
| Top-level `package.json` | Active (npm identity) | `@zcode/software-project-governance-plugin` scope; package identity only, not an executable |
| `project/zcode-local-load.py` | Active (dev tool) | One-shot local load emulating the runtime seed output; load/--verify/--reload/--unload; idempotent with backups |
| zcode official marketplace listing | Not submitted | 0.56.0 only proves local load/runtime; it is not submitted to or approved by the zcode official marketplace |
| `web-console --governance-entry` | Active (unchanged from 0.55.3) | Manual `/governance` startup/reuse path for local Web UI |
| `web-console --summary-link` | Active read-only (unchanged) | Prints a summary footer without starting services |
| `classic-phase-gate` lifecycle mode | Active/default (unchanged) | Existing classic registry-backed gate judgment remains the runtime path |
| `dynamic-flow-gate` lifecycle mode | Inactive/non-default (unchanged) | 0.56.0 keeps dynamic mode opt-in only and does not migrate projects |
| RISK-036 open-risk boundary | Active release boundary | RISK-036 remains open and 1.0.0 remains blocked |
| RISK-037 open-risk boundary | Active release boundary | RISK-037 remains open until migration and external validation closure criteria are satisfied |

## Kill Switch and Rollback Boundary

0.56.0 is a zcode adapter patch. If the release package claims official/marketplace approval, universal runtime support, external validation full PASS, changes Web console entry or summary behavior, changes dynamic lifecycle activation, closes RISK-036/RISK-037, or overclaims readiness, revert the 0.56.0 release package and return to 0.55.3 while keeping RISK-036 and RISK-037 open.

## No-Overclaim Boundary

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external validation full PASS for two real projects. No external first-session pilot success. No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No project migration. No dynamic-flow-gate default. No apply/write migration path. No completed non-game preset generalization claim. No Web replacement for CLI/client execution. No summary footer service startup. No Web-triggered agent task execution. No RISK-036 closure. No RISK-037 closure. No 1.0.0 production-ready.

RISK-036 remains open. RISK-037 remains open.
