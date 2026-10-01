# Rollback Plan - 0.63.2

**Version**: 0.63.2 (patch)
**Release**: Check 29 auto-discovery 排除 session-snapshot 误报修复（FIX-178）
**Date**: 2026-07-05
**Documentation provenance**: BACKFILLED on 2026-07-08 by DOC-001 (commit `7792b4e`); not created at release time.

## 1. Rollback Triggers

| # | Trigger | Detection |
| --- | --- | --- |
| 1 | Excluding session-snapshot causes a real runtime violation in snapshot to be missed | (unlikely — snapshot is post-hoc record, not runtime output; reverse-protection test guards detection path) |
| 2 | verify_workflow.py test regression | Unit tests fail beyond known baseline |
| 3 | check-governance Check 29 still FAIL after fix | session-snapshot still being scanned (fix incomplete) |

## 2. Rollback Steps

```bash
# Revert the 0.63.2 commit
git revert <0.63.2-commit-sha>
# This restores 0.63.1 behavior:
#   - Check 29 auto-discovery scans session-snapshot.md as a segment again
#   - check-governance Check 29 will re-report T2 FAIL on snapshot records

# Note: reverting re-introduces the false-positive. This is acceptable if
# the snapshot content is clean, but check-governance signal will be polluted.

# If only the scan-source exclusion is problematic but inline path is fine:
# - Revert only the auto-discovery branch change in check_m5_runtime_triggers
#   (keep the docstring/comment updates if desired)

# Verify
python skills/software-project-governance/infra/verify_workflow.py check-governance
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
```

## 3. Reversibility

| Aspect | Classification |
|--------|---------------|
| Check 29 auto-discovery source exclusion | Fully reversible (git revert) |
| Inline `text=` runtime scan path | Unchanged by this fix (no revert action needed) |
| Detection capability | Preserved on fix; revert re-pollutes check-governance signal but does not weaken inline detection |

## No-overclaim boundaries

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No external host-project validation of rollback safety. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. Rollback plan is internal documentation, not an external guarantee.
