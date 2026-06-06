# Codex Desktop Marketplace E2E Gap Plan

Version target: 0.45.0

Related risk: RISK-036

Related requirement: REQ-092

Related planning item: AUDIT-110

## Source Facts

| Fact | Evidence |
| --- | --- |
| The repository has a Codex plugin manifest. | `.codex-plugin/plugin.json` defines `software-project-governance`, `skills: ./skills/`, interface metadata, default prompts, logo, composer icon, and screenshot references. |
| The repository has a local marketplace entry. | `.agents/plugins/marketplace.json` points `software-project-governance` to `./` and `.codex-plugin/plugin.json`. |
| The repository has tracked Codex marketplace assets. | `.codex-plugin/assets/logo.svg`, `.codex-plugin/assets/composer-icon.svg`, and `.codex-plugin/assets/governance-preview.svg` exist. |
| Public docs keep the boundary conservative. | `README.md` says the Codex loading path depends on the current Codex environment/plugin mechanism, and that these assets are consumable assets rather than a universal one-command install for every Codex runtime. |
| The public runtime matrix does not claim approval. | `docs/requirements/runtime-readiness-matrix-0.43.0.md` states no official approval, no marketplace approval, and no universal/full runtime support. |

## Gap

The project can be consumed as a Codex plugin asset package in environments that support the `.agents/plugins/marketplace.json` plus `.codex-plugin/plugin.json` path, but it has not closed a real Codex Desktop marketplace-management E2E.

The missing E2E is not a manifest or documentation check. It must run in a real Codex Desktop environment and verify the user-visible install and management path.

## Required E2E Scope

0.45.0 must add a Codex Desktop marketplace E2E evidence path before the project can treat Codex Desktop marketplace support as closed.

The E2E must verify:

- Marketplace add or equivalent local marketplace registration.
- Plugin install or enable from Codex Desktop.
- Plugin visibility with display name, description, icon, and preview assets.
- Skill discovery or invocation path for `software-project-governance`.
- A governance status or Delivery Trust Snapshot action from a real project context.
- Upgrade or reinstall behavior when the manifest version changes.
- Disable, uninstall, or rollback behavior.
- Evidence capture that records exact Codex Desktop version, plugin source, commands or UI path, screenshots/logs where available, pass/blocked status, and no-overclaim boundary.

## Acceptance Criteria

| ID | Criterion | Validation |
| --- | --- | --- |
| CDX-DESKTOP-001 | A real Codex Desktop marketplace-management E2E report exists. | Tracked report under `docs/requirements/` or `docs/marketplace/` with exact environment facts and result matrix. |
| CDX-DESKTOP-002 | The report distinguishes local/personal marketplace support from official/public marketplace approval. | Overclaim scan rejects wording that says official approval, marketplace approval, universal/full runtime support, or 1.0.0 production-ready. |
| CDX-DESKTOP-003 | The E2E covers install, enable/invoke, upgrade/reinstall, and disable/uninstall or rollback. | Result matrix contains each lifecycle step with PASS/BLOCKED/NOT_SUPPORTED and source evidence. |
| CDX-DESKTOP-004 | RISK-036 closure criteria include this E2E. | `risk-log` and release docs for the carrying version name Codex Desktop marketplace-management E2E as a blocker before 1.0.0. |

## Version Placement

This gap belongs in 0.45.0 because 0.45.0 is the Governance Eval & Benchmark release. The missing work is evidence quality and real-environment measurement, not a 0.44.0 composable pack behavior change.

0.46.0 official submission materials must consume the 0.45.0 E2E result. If the real Codex Desktop path remains blocked, 0.46.0 must carry the blocked status forward and must not present the project as officially marketplace-ready.

## Non-Goals

- Do not claim official Codex marketplace approval.
- Do not claim universal Codex runtime support.
- Do not use Codex CLI headless E2E as a substitute for Codex Desktop marketplace-management E2E.
- Do not close RISK-036 from manifest presence alone.
- Do not modify 0.44.0 pack registry scope.
