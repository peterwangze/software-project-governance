# Rollback Plan - 0.63.4

**Version**: 0.63.4 (patch)
**Release**: check_version_consistency VERSION_FILES 覆盖盲区修复（FIX-182）
**Date**: 2026-07-07
**Documentation provenance**: BACKFILLED on 2026-07-08 by DOC-001 (commit `7792b4e`); not created at release time.

## 1. Rollback Triggers

| # | Trigger | Detection |
| --- | --- | --- |
| 1 | VERSION_FILES new entries cause check-version-consistency false FAIL | check-version-consistency reports drift on `.zcode-plugin`/`.chrys-plugin` despite correct versions |
| 2 | Print string N=13 count mismatch | check-version-consistency reports "expected 13, found N" count error |
| 3 | verify_workflow.py test regression | Unit tests fail beyond known baseline |

## 2. Rollback Steps

```bash
# Revert the 0.63.4 commit
git revert <0.63.4-commit-sha>
# This restores 0.63.3 behavior:
#   - VERSION_FILES back to 3 plugin.json entries (missing .zcode-plugin + .chrys-plugin)
#   - print string back to "11 files, 3 plugin.json"
#   - check-version-consistency will not detect .zcode-plugin/.chrys-plugin drift

# Note: reverting re-introduces the coverage blind spot. This is acceptable
# in the short term (projection-sync fallback still catches some drift,
# manual verification covers the rest), but long-term leaves a latent gap.

# If only the new VERSION_FILES entries cause issues (e.g. file doesn't exist
# in a forked variant of the repo):
# - Remove just the .zcode-plugin and .chrys-plugin entries from VERSION_FILES
#   (keep the print string correction if other entries are valid)

# Verify
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync
```

## 3. Reversibility

| Aspect | Classification |
|--------|---------------|
| VERSION_FILES +2 entries | Fully reversible (git revert) |
| Print string N correction | Restored on revert (back to "11 files, 3 plugin.json") |
| Regression test | Removed on revert |

## No-overclaim boundaries

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No external host-project validation of rollback safety. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. Rollback plan is internal documentation, not an external guarantee.
