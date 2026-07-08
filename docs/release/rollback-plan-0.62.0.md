# Rollback Plan - 0.62.0

**Version**: 0.62.0 (minor)
**Release**: zcode 插件市场适配（废弃逆向 local-load 机制）
**Date**: 2026-07-01

## 1. Rollback Triggers

| # | Trigger | Detection |
| --- | --- | --- |
| 1 | marketplace.json github source rejected by zcode/Claude runtime | install via `/plugin marketplace add` fails with source-format error |
| 2 | Removal of zcode-local-load.py breaks a hidden reference | verify_workflow.py or test suite reports missing import |
| 3 | Agent adapter contract regression | `verify_workflow.py check-agent-adapters` reports de-sync |

## 2. Rollback Steps

```bash
# Revert the 0.62.0 commit
git revert <0.62.0-commit-sha>
# This restores 0.61.2 behavior:
#   - marketplace.json source back to "./"
#   - zcode-local-load.py restored
#   - DEPRECATED banner removed

# If only the marketplace source causes issues:
# - Revert .claude-plugin/marketplace.json source to "./"
#   (keep other zcode doc/marketing updates if desired)

# Verify
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters
```

## 3. Reversibility

| Aspect | Classification |
|--------|---------------|
| marketplace.json source change | Fully reversible (git revert) |
| zcode-local-load.py removal | Restored on revert (zero downstream references, so deletion was non-destructive) |
| Documentation references | Restored on revert (DEPRECATED banner removed, install doc removed) |

## 4. Note on existing installations

Per CHANGELOG Upgrade Notes: no breaking change. Existing 0.56.0 local-load installs of zcode are unaffected (zcode does not actively re-seed third-party plugins); new installs all go through marketplace protocol.

## No-overclaim boundaries

This is **protocol-consistency install**, not zcode official inclusion or review approval. RISK-036 (官方收录准备) stays open. No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external first-session pilot success. No external host-project validation of rollback safety. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. Rollback plan is internal documentation, not an external guarantee.
