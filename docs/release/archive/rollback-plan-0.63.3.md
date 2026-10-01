# Rollback Plan - 0.63.3

**Version**: 0.63.3 (patch)
**Release**: e2e fixture SKILL.md adapter 表结构对齐（FIX-180）
**Date**: 2026-07-06
**Documentation provenance**: BACKFILLED on 2026-07-08 by DOC-001 (commit `7792b4e`); not created at release time.

## 1. Rollback Triggers

| # | Trigger | Detection |
| --- | --- | --- |
| 1 | Fixture adapter table alignment introduces a new projection-sync drift | `verify_workflow.py check-projection-sync` FAIL |
| 2 | e2e test regression | e2e fixture-based tests fail |
| 3 | verify_workflow.py test regression | Unit tests fail beyond known baseline |

## 2. Rollback Steps

```bash
# Revert the 0.63.3 commit
git revert <0.63.3-commit-sha>
# This restores 0.63.2 behavior:
#   - fixture SKILL.md adapter table back to 4 rows (missing opencode + Chrys)
#   - check-projection-sync will re-report fixture drift FAIL

# Note: reverting re-introduces the projection-sync FAIL. This is the
# pre-existing state flagged in FX-175/177/179 Release Reviewer R0 rounds
# as "out-of-PATCH-scope structural drift". Acceptable to revert if needed,
# but the FAIL signal will return.

# If only the fixture row addition is problematic:
# - Revert just the +2 rows in project/e2e-test-project/.../SKILL.md
#   (keep version pointer sync if desired, downgrade manually)

# Verify
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
```

## 3. Reversibility

| Aspect | Classification |
|--------|---------------|
| Fixture adapter table +2 rows | Fully reversible (git revert) |
| Source SKILL.md | Unchanged by this fix (no revert action needed) |
| Version pointer sync | Restored on revert (0.63.3→0.63.2 across 11 files + fixture pointers) |

## No-overclaim boundaries

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No external host-project validation of rollback safety. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. Rollback plan is internal documentation, not an external guarantee.
