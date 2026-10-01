# Feature Flags - 0.65.2

**Version**: 0.65.2 (patch)
**Release**: SKILL Loop Role and Check 30 review-closure consistency repair (FIX-191, FIX-193)
**Date**: 2026-07-11

## Feature Flag Inventory

0.65.2 introduces no runtime feature flags and no kill-switch-controlled rollout. The release normalizes review-SKILL guidance, adds validation for that guidance, and aligns the Check 30 review-closure state machine with the four-state protocol. It does not alter the loop runtime or migration data format.

## Behavior

| Component | Default | Notes |
| --- | --- | --- |
| Review SKILL Loop Role section | enabled as packaged guidance | Seven review SKILLs use the stable `## 循环角色` heading. Version history is in body text, not the heading. |
| `check-loop-role-skills` | available through `verify_workflow.py` | Fails closed for a missing review SKILL, unstable heading, invalid mapping reference, or missing required loop/reviewer/terminal semantics. |
| Four-state review closure | enabled | `APPROVED` passes; `APPROVED_WITH_NOTES` passes only with consistent `unresolved_blockers=0`; `BLOCKED` closes without passing; `NEEDS_CHANGE(S)` and malformed/unknown evidence fail closed. |
| Historical review marker compatibility | migrated evidence | Seven historical `APPROVED_WITH_NOTES` markers now carry `unresolved_blockers=0`; live Check 30 is WARN with no V5/closure violations. |
| Loop runtime and migration format | unchanged | This release does not change loop execution, fuse thresholds, state derivation, or migration data. |

## E2E Fixture Pointer

- Source fixture SKILL: `project/e2e-test-project/skills/software-project-governance/SKILL.md` -> `version: 0.65.2`
- Target fixture plan: `project/e2e-test-project/.governance/plan-tracker.md` -> `工作流版本: 0.65.2`

## Rollout and Kill Switch

There is no runtime rollout or kill switch. If the packaged SKILL guidance or consistency validation regresses, use the documented Git rollback path before release; do not disable or alter a loop runtime feature.

## No-overclaim Boundaries

No git tag has been created by this package-preparation task. No official approval, marketplace approval, universal/full runtime support, external first-session pilot success, RISK-036/RISK-037/RISK-039/RISK-040/RISK-041 closure, or 1.0.0 readiness is claimed. The existing archive trigger gap and 43 other governance health issues remain visible. No post-FIX-193 full-suite PASS is claimed; only the recorded focused validations are asserted.
