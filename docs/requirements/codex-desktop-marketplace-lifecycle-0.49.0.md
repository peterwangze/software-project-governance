# Codex Desktop Marketplace Lifecycle Review - 0.49.0

Date: 2026-06-10
Task: VAL-002
Scope: pre-1.0.0 Codex marketplace-management lifecycle review after `v0.48.0`.

This report updates the earlier 0.45.0 Desktop marketplace-management E2E report with the currently available Codex CLI and Codex Desktop state. It is intentionally conservative: it records what can be verified, what remains blocked, and what must not be claimed before 1.0.0.

No official approval. No marketplace approval. No universal/full runtime support. No Codex Desktop marketplace-management E2E PASS. No external project validation PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No catalog entry runtime PASS. No 1.0.0 production-ready status.

## Current Environment Facts

| Fact | Evidence |
| --- | --- |
| Codex CLI is available. | `codex -V` returned `codex-cli 0.125.0`. |
| Codex CLI exposes marketplace source management. | `codex plugin --help` shows `plugin marketplace`; `codex plugin marketplace --help` shows `add`, `upgrade`, and `remove`. |
| Codex CLI does not expose a marketplace list command in this environment. | `codex plugin marketplace list` returned `error: unrecognized subcommand 'list'`. |
| Marketplace `add` accepts repository, HTTP(S), SSH, and local marketplace root sources. | `codex plugin marketplace add --help` documents those source formats. |
| The configured `software-project-governance` marketplace source can be upgraded through CLI. | `codex plugin marketplace upgrade software-project-governance` returned success and reported the installed marketplace root. |
| A second upgrade sees the configured Git marketplace as current. | `codex plugin marketplace upgrade` returned `All configured Git marketplaces are already up to date.` |
| The installed marketplace working copy is at the current pushed commit. | `git -C C:\Users\peter\.codex\.tmp\marketplaces\software-project-governance rev-parse HEAD` returned `51d40fed2c8f7c3e2821bc348f5afc2c8d14d383`, matching VAL-001 remote head. |
| The installed marketplace copy includes the Codex plugin manifest. | `C:\Users\peter\.codex\.tmp\marketplaces\software-project-governance\.codex-plugin\plugin.json` exists and declares `software-project-governance`. |
| Codex Desktop logs show plugin listing and bundled plugin reconciliation, but not this plugin's install/enable lifecycle. | Desktop logs include `method=plugin/list`, `bundled_plugins_reconcile_started/completed`, and a bundled marketplace EBUSY warning; no line proves `software-project-governance` install, enable, invocation, disable, uninstall, or rollback. |

## Command Results

| Command | Exit | Meaning |
| --- | --- | --- |
| `codex -V` | 0 | Codex CLI version probe succeeded: `codex-cli 0.125.0`. |
| `codex plugin --help` | 0 | Plugin command surface exists. |
| `codex plugin marketplace --help` | 0 | Marketplace source commands are limited to `add`, `upgrade`, and `remove`. |
| `codex plugin marketplace add --help` | 0 | Add source contract is discoverable. |
| `codex plugin marketplace upgrade --help` | 0 | Upgrade contract is discoverable. |
| `codex plugin marketplace remove --help` | 0 | Remove contract is discoverable. |
| `codex plugin marketplace list` | 1 | No `list` subcommand is available in this CLI. |
| `codex plugin marketplace upgrade software-project-governance` | 0 | The configured marketplace source upgraded/synced and reported an installed root. |
| `codex plugin marketplace upgrade` | 0 | All configured Git marketplaces reported up to date after the targeted upgrade. |
| `git -C <installed-marketplace-root> rev-parse HEAD` | 0 | Installed marketplace working copy is at `51d40fed2c8f7c3e2821bc348f5afc2c8d14d383`. |

## Lifecycle Matrix

| Lifecycle step | 0.49.0 result | Evidence status | Boundary |
| --- | --- | --- | --- |
| Codex CLI version capture | PASS | `codex-cli 0.125.0` captured. | CLI version is not Desktop UI lifecycle proof. |
| Marketplace source command discovery | PASS | CLI help documents `add`, `upgrade`, and `remove`. | Command availability is not plugin install/enable proof. |
| Marketplace source upgrade/sync | PASS | `upgrade software-project-governance` succeeded; installed Git working copy is at `51d40fe`. | This proves source sync, not Desktop plugin install or enable. |
| Marketplace source list/readback | BLOCKED | No `list` subcommand exists. | Installed root inspection is a filesystem check, not an official CLI list result. |
| Plugin install from Codex Desktop UI | BLOCKED | NOT_RUN. | No Desktop UI action, installed plugin record, or Desktop log proves install. |
| Plugin enable from Codex Desktop UI | BLOCKED | NOT_RUN. | No enable toggle/state, enabled plugin list, or session reload evidence. |
| Plugin visibility with display name/assets in Desktop UI | BLOCKED | NOT_RUN. | Manifest and assets exist, but no Desktop screenshot/log proves UI visibility. |
| Skill discovery or invocation from Desktop | BLOCKED | NOT_RUN. | No Desktop invocation transcript for `software-project-governance`, `/governance`, or its skills. |
| Governance status or Delivery Trust Snapshot from Desktop | BLOCKED | NOT_RUN. | No Desktop-origin project run produced governance status or Delivery Trust Snapshot. |
| Plugin upgrade/reinstall lifecycle from Desktop UI | BLOCKED | NOT_RUN. | CLI source upgrade succeeded, but no Desktop plugin upgrade/reinstall action was captured. |
| Disable, uninstall, or rollback from Desktop UI | BLOCKED | NOT_RUN. | `remove` help exists, but no destructive remove/uninstall was run against the user's configured marketplace, and no Desktop disable/uninstall evidence exists. |
| Official/public marketplace approval | BLOCKED | NOT_SUPPORTED. | No official submission result or approval evidence. |

## Decision

VAL-002 is **not a Codex Desktop marketplace-management E2E PASS**.

The 0.49.0 review improves the evidence base compared with 0.45.0:

- Codex CLI now provides observable marketplace source management commands.
- The configured `software-project-governance` marketplace source can be upgraded.
- The synced marketplace working copy is at commit `51d40fe`, the current pushed head after VAL-001.

The review still does **not** prove:

- Desktop UI install or enable;
- plugin visible in Desktop UI with metadata and assets;
- skill discovery or invocation from Desktop;
- Desktop-origin governance status or Delivery Trust Snapshot;
- Desktop upgrade/reinstall lifecycle;
- Desktop disable/uninstall/rollback lifecycle;
- official or public marketplace approval.

## Required Evidence Before PASS

| Missing evidence | Required proof |
| --- | --- |
| Desktop install and enable | Desktop UI screenshot/log/state showing add/install and enabled plugin state for `software-project-governance`. |
| Desktop plugin visibility | Screenshot or machine-readable Desktop state showing display name, description, icon, and preview from `.codex-plugin/plugin.json`. |
| Desktop invocation | Transcript or log proving `software-project-governance` skill/workflow invocation from a Desktop session. |
| Desktop project output | Desktop-origin run showing governance status or Delivery Trust Snapshot from a real project. |
| Desktop upgrade/reinstall | UI/log/state proving upgrade or reinstall after a manifest version or commit change. |
| Desktop disable/uninstall/rollback | UI/log/state proving disable, uninstall, remove, or rollback without relying only on CLI help. |

## 1.0.0 Boundary

This report keeps RISK-036 open and keeps 1.0.0 blocked. FIX-126 and REL-026 may consume the CLI marketplace source sync evidence, but they must carry forward the Desktop lifecycle blocker unless a later real Desktop run produces direct lifecycle evidence.
