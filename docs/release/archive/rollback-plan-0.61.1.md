# Rollback Plan - 0.61.1

**Version**: 0.61.1 (patch)
**Release**: archive engine decision/risk migration + verify cross-check
**Task**: FIX-162 + FIX-163
**Date**: 2026-06-30

## 1. Rollback Triggers

| # | Trigger | Detection |
| --- | --- | --- |
| 1 | decision/risk migration corrupts decision-log/risk-log | `archive.py verify` Pass:False after real migration, or decision-log.md/risk-log.md unreadable |
| 2 | verify Check 3 false positive (per-category miscounts) | `archive.py verify` reports mismatch when archive is actually consistent |
| 3 | `_version_to_tuple` misparses a real version | task/decision/risk wrongly classified into/out of archive range |
| 4 | Test regression | pytest archive suite fails beyond known baseline |

## 2. Rollback Steps

```bash
# Revert the 0.61.1 commit
git revert <0.61.1-commit-sha>
# This restores 0.61.0 behavior (no decision/risk migration, Check 3 dead-statistic)

# .governance/ runtime state is gitignored and independent — archive/decisions/
# and archive/risks/ files created by FIX-162 (if real migration ran) remain
# readable markdown; index.md can be rebuilt via build-index.

# Verify
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python -m pytest skills/software-project-governance/infra/tests/test_archive.py -q
```

## 3. Reversibility

| Aspect | Classification |
|--------|---------------|
| Code changes | Fully reversible (git revert) |
| .governance/ runtime state | Independent (gitignored); archived DEC/RISK remain readable |
| CHANGELOG | Reversible (remove [0.61.1] section) |

## No-overclaim boundaries

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external first-session pilot success. No external host-project validation of rollback safety. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. DEC-090/091 degraded SoD honestly noted. Rollback plan is internal documentation, not an external guarantee.
