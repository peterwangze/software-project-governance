# Feature Flags - 0.59.0

**Version**: 0.59.0
**Release**: verify_workflow.py Incremental Split Phase 1 (manifest domain)
**Task**: REL-045
**Date**: 2026-06-26

## Summary

0.59.0 introduces **no new feature flags**. It is a pure structural refactor (manifest domain extraction) with no behavioral changes and no new user-facing toggles.

The only behavioral surface is the deferred-import mechanism inside `infra/checks/manifest.py` (`_vw()` helper with `_VW_CACHE`), which is an internal implementation detail, not a flag.

## Behavior Changes (none user-facing)

| Area | 0.58.0 | 0.59.0 | Flag? |
| --- | --- | --- | --- |
| `check-manifest-consistency` command | In-file functions | Imported from `checks.manifest` | None — identical output/exit code |
| Check 11 (verify) | In-file `check_manifest_consistency()` | Imported `check_manifest_consistency()` | None — identical result |
| Dispatch / argparse / governance-pack registration | References in-file defs | References imported defs | None — 54 CLI contracts unchanged |
| ArchGuard checks (28o~28r) | advisory-only | advisory-only (unchanged) | None |

## Conservative Boundary Tokens (no-overclaim)

- No new flag, toggle, or config introduced in 0.59.0
- No official approval
- No marketplace approval (zcode or otherwise)
- No universal/full runtime support
- No external first-session pilot success
- No RISK-036 closure (RISK-036 remains open; this release does not address official adoption/market readiness)
- No RISK-037 closure
- No RISK-039 closure (Phase 1/6; closure needs external host validation)
- No 1.0.0 readiness / production-ready claim
- No fatal-on-error change (ArchGuard remains advisory, `fatal_on_error=false` unchanged from 0.58.0)
- No gating change to release gate (check-release criteria unchanged)
- No default-mode change (profiles / trigger_mode / permission_mode unchanged)
- The `infra/checks/` subpackage is scaffolding; it does not alter how checks are invoked

## Verification

```
python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency --fail-on-issues
→ canonical=411 actual=347 [PASS] (identical contract, functions now imported)
```
