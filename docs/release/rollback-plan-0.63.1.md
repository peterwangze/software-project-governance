# Rollback Plan - 0.63.1

**Version**: 0.63.1 (patch)
**Release**: archive 引擎 build_index 非结构化归档登记修复（FIX-176）
**Date**: 2026-07-05

## 1. Rollback Triggers

| # | Trigger | Detection |
| --- | --- | --- |
| 1 | build_index narrative registration produces duplicate entries | archive-integrity reports duplicate index refs |
| 2 | verify_archive_integrity new section parser breaks existing index format | check-archive-integrity FAIL on previously-PASS index |
| 3 | verify_workflow.py test regression | Unit tests fail beyond known baseline |

## 2. Rollback Steps

```bash
# Revert the 0.63.1 commit
git revert <0.63.1-commit-sha>
# This restores 0.63.0 behavior:
#   - build_index no longer registers narrative/recent-completed
#   - index.md no longer has ## 非结构化归档 section
#   - verify_archive_integrity._parse_index_section back to no 非结构化归档 branch

# Note: reverting re-opens the orphan issue (narrative files become unregistered
# after next build_index rebuild). If the orphan is acceptable (FIX-169 manual
# entry can be re-added), revert is safe.

# Verify
python skills/software-project-governance/infra/verify_workflow.py check-archive-integrity
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
```

## 3. Reversibility

| Aspect | Classification |
|--------|---------------|
| build_index unstructured-archive registration | Fully reversible (git revert) |
| index.md `## 非结构化归档` section | Removed on revert (regenerated on next build_index if fix restored) |
| verify_archive_integrity parser | Restored on revert |

## No-overclaim boundaries

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No external host-project validation of rollback safety. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. Rollback plan is internal documentation, not an external guarantee.
