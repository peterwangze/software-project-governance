# Rollback Plan - 0.60.0

**Version**: 0.60.0
**Release**: verify_workflow.py Incremental Split Phase 2 (capability-registry domain)
**Task**: REL-046
**Date**: 2026-06-26

## 1. Rollback Triggers

Roll back 0.60.0 to 0.59.0 if ANY of the following occur post-release:

| # | Trigger | Detection |
| --- | --- | --- |
| 1 | `check-capability-registry` CLI output/exit-code differs from 0.59.0 | Manual diff vs 0.59.0 baseline |
| 2 | Circular-import `ImportError` / `ModuleNotFoundError` in any execution path | Direct script run / pytest / subcommand invocation |
| 3 | `check-capability-registry --fail-on-issues` exits nonzero (regression) | Release gate / CI |
| 4 | ArchGuard module-size regression (verify_workflow.py did NOT net-shrink, or capability_registry.py exceeds thresholds) | `check-architecture-health` |
| 5 | Any of the 7 CapabilityRegistryTests fails | `pytest -k capability` |
| 6 | Check 28k (governance) regression | `check-governance` |

## 2. Rollback Procedure

0.60.0 is a **pure mechanical refactor** — no schema, no data migration, no config change. Rollback is a clean git revert.

```bash
# From repo root, after 0.60.0 tag/commit is on master:
git revert <0.60.0-commit-sha> --no-edit
# This restores verify_workflow.py in-file capability-registry functions,
# removes checks/capability_registry.py, reverts manifest.json registration,
# and rolls version back to 0.59.0.
git push
git tag -d v0.60.0   # remove the release tag if pushed
```

### Why revert is safe
- The 3 moved functions + 7 constants are byte-identical to their 0.59.0 originals (AST + unified-diff verified, REVIEW-FIX-154).
- `verify_workflow.py` after revert contains the full in-file definitions again.
- `checks/capability_registry.py` is removed entirely.
- `manifest.json` loses the capability_registry.py entry (no other consumer depends on it).
- `.governance/` records are additive and unaffected.

## 3. Data Compatibility

- **`.governance/` records**: No schema change. Plan-tracker / evidence / decision / risk / snapshot remain valid. The version field rolls back automatically with the revert.
- **User projects**: Users running `/governance` see identical behavior — the capability-registry check is invoked through the same command path. No migration needed.

## 4. Reversibility Classification

**Fully reversible.** No data loss, no manual cleanup beyond the git revert. The split is self-contained in product code paths.

## 5. Post-Rollback Verification

After rollback, confirm:
```bash
python skills/software-project-governance/infra/verify_workflow.py check-capability-registry --fail-on-issues
# expect: PASSED (pre-0.60.0 in-file functions)
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
# expect: PASSED (all 0.59.0)
```

## 6. Boundaries (no-overclaim)

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external first-session pilot success. No external validation. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure (Phase 2/6; closure needs external host validation). No 1.0.0 readiness / production-ready claim. Rollback is a local git operation; it does not constitute any external reliability claim. DEC-087 degraded SoD honestly noted.
