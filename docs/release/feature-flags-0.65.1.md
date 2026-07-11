# Feature Flags - 0.65.1

**Version**: 0.65.1 (patch)
**Release**: Evidence trust + post-0.65.0 hotfix closure (FIX-187/FIX-188/FIX-190/AUDIT-132/RISK-041)
**Date**: 2026-07-11

## Feature Flag Inventory

0.65.1 introduces **no new runtime feature flags** and no kill-switch-controlled feature rollout. It is a PATCH release package for evidence correctness, entry/hook compatibility, version declaration sync, and explicit release-lineage risk boundaries.

## Behavior

| Component | Default | Notes |
| --- | --- | --- |
| `resolve_entry.py` / dual-root entry flow | existing behavior preserved | FIX-187/FIX-188 preserve DEC-096 separation between plugin package facts and host project governance facts. |
| `verify_workflow.py --project-root` | available on invocation | Explicit host project root can be passed after the subcommand; only host `.governance` fact paths are rebound. Plugin assets stay rooted at PLUGIN_HOME. |
| pre-commit / commit-msg review evidence matching | enabled | `APPROVED_WITH_NOTES` is accepted as approved review evidence, alongside `APPROVED` / Chinese approved markers. Other non-approved statuses remain blocking. |
| 0.65.0 release evidence correction | documentation only | 0.65.0 archive integrity is recorded as pre-existing FAIL / non-blocking P2 at release review, not retroactively upgraded to PASS. |

## E2E Fixture Pointer

- Source fixture SKILL: `project/e2e-test-project/skills/software-project-governance/SKILL.md` → `version: 0.65.1`
- Target fixture plan: `project/e2e-test-project/.governance/plan-tracker.md` → `工作流版本: 0.65.1`

## Backward Compatibility

- Classic-phase-gate and 0.65.0 loop-engineering behavior remain unchanged.
- This release does not introduce 0.65.2/0.65.3 SKILL Loop Role or tag-gate implementation.
- Hook review-evidence recognition is widened only for `APPROVED_WITH_NOTES`; blocking statuses remain blocked.

## No-overclaim boundaries

No git tag created. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036/RISK-037/RISK-039/RISK-040/RISK-041 closure. No 1.0.0 readiness. Pre-existing archive/tag/release-lineage failures remain visible and must not be represented as a fully green release gate.
