# Rollback Plan - 0.63.0

**Version**: 0.63.0 (minor)
**Release**: Coordinator 检视循环协议修复 + verify Check 29/30（FIX-173/174）+ archive 引擎修复（FIX-168/170/171/172）
**Date**: 2026-07-04

## 1. Rollback Triggers

| # | Trigger | Detection |
| --- | --- | --- |
| 1 | M5.4b tightening breaks existing notification patterns in downstream consumers | Check 29 reports false-positive FAIL on legitimate pure-notification segments |
| 2 | Check 21 review_spawn_gap false-positive | check-governance reports spurious FAIL on tasks without product-code diff |
| 3 | Check 30 closure state machine rejects historical evidence | WARN escalates to FAIL on pre-existing REVIEW-{id} rows |
| 4 | FIX-170/171/172 archive regression | archive.py migrate --auto produces data loss or orphan entries |
| 5 | verify_workflow.py test regression | Unit tests fail beyond known baseline |

## 2. Rollback Steps

```bash
# Revert the 0.63.0 commit
git revert <0.63.0-commit-sha>
# This restores 0.62.0 behavior:
#   - M5.4 back to SHOULD (notification prefix not mandatory)
#   - Check 29/30 removed
#   - Check 21 back to check_review_debt
#   - archive.py pre-FIX-170/171/172 behavior

# If only M5.4 tightening causes issues (most likely scenario):
# - Revert behavior-protocol.md M5.4b section to SHOULD wording
#   (keep Check 29/30 infrastructure, they degrade to no-verdict/advisory)
# - OR prefix existing notification segments with ℹ️ to comply

# If only archive fixes cause issues:
# - Revert archive.py _migrate_risks/_migrate_decisions/_migrate_evidence
#   status-filter/subset-gate/body-write changes individually
#   (each fix is isolated in commits FIX-170/FIX-171/FIX-172)

# Verify
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-governance
```

## 3. Reversibility

| Aspect | Classification |
|--------|---------------|
| Check 29/30 additions | Fully reversible (git revert) — new code, no data migration |
| M5.4b tightening (behavior change) | Reversible — revert behavior-protocol.md wording; existing notification segments need prefix removal if they were adapted |
| Check 21 强化 | Reversible — revert function rename and three-source cross logic |
| Check 18-27 ID drift fix | No-logic-change alignment, fully reversible |
| FIX-168/170/171/172 archive fixes | Reversible individually (isolated commits), but reverting FIX-170 re-opens AUDIT-127 (OPEN risks migrated out of hot risk-log) — coordinate with governance recovery |

## 4. Special note

⚠️ M5.4b is a **behavior change** (SHOULD→MUST). Downstream consumers who relied on bare notification segments without ℹ️/📢 prefix must add a prefix to remain compliant post-rollback-of-the-tightening. Full revert restores the looser SHOULD default.

## No-overclaim boundaries

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No external host-project validation of rollback safety. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. Rollback plan is internal documentation, not an external guarantee. Reverting archive fixes may re-open governance-data-integrity risks (AUDIT-127) — coordinate with governance recovery protocol.
