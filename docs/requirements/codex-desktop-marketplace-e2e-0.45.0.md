# Codex Desktop Marketplace-Management E2E Report

Version target: 0.45.0

Related risk: RISK-036

Related requirement: REQ-092

Related planning item: AUDIT-110

Release task: REL-022

## Summary

Codex Desktop marketplace-management E2E is **BLOCKED / NOT_RUN** for 0.45.0.

No real Codex Desktop add/install/enable/invoke/upgrade/uninstall lifecycle was executed in this release package. The repository has plugin manifests and local marketplace metadata, but those files are not Desktop marketplace-management evidence and must not be written as PASS.

## Source Facts

| Fact | Evidence |
| --- | --- |
| The repository has a Codex plugin manifest. | `.codex-plugin/plugin.json` defines `software-project-governance`, `skills: ./skills/`, interface metadata, default prompts, logo, composer icon, and screenshot references. |
| The repository has local/personal marketplace metadata. | `.agents/plugins/marketplace.json` points `software-project-governance` to `./` and `.codex-plugin/plugin.json`. |
| The repository has tracked Codex marketplace assets. | `.codex-plugin/assets/logo.svg`, `.codex-plugin/assets/composer-icon.svg`, and `.codex-plugin/assets/governance-preview.svg` exist. |
| Public docs keep the boundary conservative. | `README.md` says the Codex loading path depends on the current Codex environment/plugin mechanism, and that these assets are consumable assets rather than a universal one-command install for every Codex runtime. |
| The public runtime matrix does not claim approval. | `docs/requirements/runtime-readiness-matrix-0.43.0.md` states no official approval, no marketplace approval, and no universal/full runtime support. |
| The capability registry keeps Codex Desktop manifest facts degraded. | `skills/software-project-governance/core/capability-registry.json` marks `codex.desktop.plugin-manifest` as `DEGRADED` and says local manifest presence is not Codex Desktop marketplace-management lifecycle evidence. |
| The restricted benchmark prevents Desktop lifecycle overclaim. | `check-host-capability-context --fail-on-issues` treats `no_plugin_install` as degraded and says manifest/catalog facts cannot claim install, enable, upgrade, uninstall, marketplace approval, or Desktop marketplace E2E PASS. |

## Result Matrix

| Lifecycle step | 0.45.0 result | Evidence status | Exact missing Desktop evidence |
| --- | --- | --- | --- |
| Codex Desktop version and environment capture | BLOCKED | NOT_RUN | No captured Codex Desktop version, build, OS/session metadata, installed plugin list, logs, screenshots, or UI path from a real Desktop session. |
| Marketplace add or local marketplace registration | BLOCKED | NOT_RUN | No real Desktop action showing marketplace add/registration from `.agents/plugins/marketplace.json` or another supported Desktop marketplace source. |
| Plugin install from Codex Desktop | BLOCKED | NOT_RUN | No real Desktop install event, installed plugin record, UI confirmation, filesystem install evidence, or Desktop log evidence. |
| Plugin enable from Codex Desktop | BLOCKED | NOT_RUN | No real Desktop enable toggle/state, enabled plugin list, or session reload evidence. |
| Plugin visibility with display name, description, icon, and preview | BLOCKED | NOT_RUN | No Desktop UI screenshot/log proving the plugin appears with metadata and assets. Manifest files alone are not visibility evidence. |
| Skill discovery or invocation | BLOCKED | NOT_RUN | No Desktop invocation of `software-project-governance`, no `/governance` or skill picker evidence, and no Desktop session transcript proving the workflow loaded. |
| Governance status or Delivery Trust Snapshot from a real project | BLOCKED | NOT_RUN | No Desktop-origin project run showing governance status, Delivery Trust Snapshot, source facts, or blocked state. |
| Upgrade or reinstall after manifest version change | BLOCKED | NOT_RUN | No Desktop upgrade/reinstall event from 0.44.1 to 0.45.0, no update UI/logs, and no post-upgrade version confirmation. |
| Disable, uninstall, or rollback | BLOCKED | NOT_RUN | No Desktop disable/uninstall/rollback action, removed plugin state, disabled state, or cleanup evidence. |
| Official/public marketplace approval | BLOCKED | NOT_SUPPORTED | No official submission or approval evidence. This release package does not claim marketplace approval. |

## Acceptance Criteria Status

| ID | Criterion | 0.45.0 status | Evidence |
| --- | --- | --- | --- |
| CDX-DESKTOP-001 | A real Codex Desktop marketplace-management E2E report exists. | BLOCKED | This tracked report exists, but it reports NOT_RUN/BLOCKED because real Desktop lifecycle evidence is absent. |
| CDX-DESKTOP-002 | The report distinguishes local/personal marketplace support from official/public marketplace approval. | PASS | Source facts separate local manifests from marketplace approval; no official approval or marketplace approval is claimed. |
| CDX-DESKTOP-003 | The E2E covers install, enable/invoke, upgrade/reinstall, and disable/uninstall or rollback. | BLOCKED | Matrix includes each lifecycle step but every real Desktop lifecycle step is NOT_RUN due to missing Desktop evidence. |
| CDX-DESKTOP-004 | RISK-036 closure criteria include this E2E. | PASS | Release docs and RISK-036 keep Desktop marketplace-management E2E as a required blocker before 1.0.0 or official submission readiness claims. |

## Why This Is Blocked

The current workspace evidence covers local files and validators only. It does not include access to a real Codex Desktop marketplace-management lifecycle, and no UI or log artifact was captured for this release package.

The following evidence would be required before any Desktop lifecycle row could become PASS:

- Codex Desktop version/build and environment details.
- Marketplace add or registration action with source path.
- Install and enable confirmation.
- Plugin visible in Desktop UI with metadata/assets.
- Skill discovery or invocation from Desktop.
- Governance status or Delivery Trust Snapshot generated from Desktop in a real project.
- Upgrade or reinstall from an older manifest version to the target release.
- Disable/uninstall or rollback confirmation.
- Logs, screenshots, transcript, or machine-readable Desktop state for each step.

## Release Boundary

0.45.0 may release the capability discovery and restricted benchmark package with this E2E marked BLOCKED. 0.46.0 official submission materials must carry this blocked status forward unless a later real Desktop run produces direct evidence.

## No-Overclaim Boundary

- No official approval.
- No marketplace approval.
- No universal/full runtime support.
- No external first-session pilot success.
- No Codex Desktop marketplace-management E2E PASS.
- No Codex CLI headless E2E substitution for Desktop marketplace-management evidence.
- No current Codex App dogfood/session substitution for Desktop marketplace-management evidence.
- No manifest/catalog/asset presence as lifecycle PASS.
- No 1.0.0 production-ready claim.
