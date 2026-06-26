# Feature Flags - 0.60.0

**Version**: 0.60.0
**Release**: verify_workflow.py Incremental Split Phase 2 (capability-registry domain)
**Task**: REL-046
**Date**: 2026-06-26

## Summary

0.60.0 introduces **no new feature flags**. It is a pure structural refactor (capability-registry domain extraction) with no behavioral changes and no new user-facing toggles.

The only behavioral surface is the deferred-import mechanism inside `infra/checks/capability_registry.py` (`_vw()` helper with `_VW_CACHE` + lazy `_manifest_artifact_entries`), which is an internal implementation detail, not a flag.

## Behavior Changes (none user-facing)

| Area | 0.59.0 | 0.60.0 | Flag? |
| --- | --- | --- | --- |
| `check-capability-registry` command | In-file functions | Imported from `checks.capability_registry` | None — identical output/exit code |
| Check 28k (governance) | In-file `check_capability_registry()` | Imported `check_capability_registry()` | None — identical result |
| Dispatch / argparse / governance-pack registration | References in-file defs | References imported defs | None — 54 CLI contracts unchanged |
| ArchGuard checks (28o~28r) | advisory-only | advisory-only (unchanged) | None |

## Conservative Boundary Tokens (no-overclaim)

- No new flag, toggle, or config introduced in 0.60.0
- No official approval
- No marketplace approval (zcode or otherwise)
- No universal/full runtime support
- No external first-session pilot success
- No RISK-036 closure (RISK-036 remains open)
- No RISK-037 closure
- No RISK-039 closure (Phase 2/6; closure needs external host validation)
- No 1.0.0 readiness / production-ready claim
- No fatal-on-error change (ArchGuard remains advisory, `fatal_on_error=false` unchanged)
- No gating change to release gate (check-release criteria unchanged)
- No default-mode change (profiles / trigger_mode / permission_mode unchanged)
- No automatic best-tool selection
- No universal plugin/skill/tool availability

## Verification

```
python skills/software-project-governance/infra/verify_workflow.py check-capability-registry --fail-on-issues
→ [PASS] (identical contract, functions now imported)
```
