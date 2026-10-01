# Rollback Plan - 0.61.2

**Version**: 0.61.2 (patch)
**Release**: Chrys agent adapter integration
**Date**: 2026-07-01

## 1. Rollback Triggers

| # | Trigger | Detection |
| --- | --- | --- |
| 1 | Chrys adapter breaks other platform adapters | `verify_workflow.py check-agent-adapters` reports de-sync |
| 2 | Chrys projection breaks verify contract | `verify_workflow.py check-mainstream-agent-loading` fails |
| 3 | verify_workflow.py regression | Unit tests fail beyond known baseline |

## 2. Rollback Steps

```bash
# Revert the 0.61.2 commit
git revert <0.61.2-commit-sha>
# This restores 0.61.1 behavior (4-adapter list without Chrys)

# If only the Chrys adapter causes issues for other platforms:
# - Revert verify_workflow.py MAINSTREAM_AGENT_ADAPTERS to remove "chrys"
#   from the 4-adapter list.

# Verify
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
```

## 3. Reversibility

| Aspect | Classification |
|--------|---------------|
| Code changes | Fully reversible (git revert) |
| adapters/chrys/ directory | Removed on revert |
| Documentation references | Removed on revert |

## No-overclaim boundaries

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external first-session pilot success. No external host-project validation of rollback safety. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. Rollback plan is internal documentation, not an external guarantee.
