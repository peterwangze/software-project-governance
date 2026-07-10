# Rollback Plan - 0.64.1

**Version**: 0.64.1 (patch)
**Release**: marketplace.json source 改回 "./" 恢复本地/离线安装能力（FIX-186）
**Date**: 2026-07-10

## Rollback Triggers

| Trigger | Severity | Detection | Action |
|---------|----------|-----------|--------|
| `"./"` source breaks zcode marketplace install | High | zcode `/plugin install` fails with path resolution error | Revert to `{"source":"github",...}`; investigate zcode-specific source handling |
| `"./"` source breaks remote marketplace add (clone scenario) | Medium | `/plugin marketplace add owner/repo` + `/plugin install` fails | Verify `"./"` resolves correctly against cloned marketplace repo; fix if needed |
| Version inconsistency (0.64.1 not propagated) | Low | check-version-consistency FAIL | Re-run version bump on missed file |

## Rollback Steps

### Full rollback to 0.64.0
1. Revert marketplace.json source `"./"` → `{"source":"github","repo":"peterwangze/software-project-governance"}`
2. Re-bump version 0.64.1 → 0.64.0 across 13 declaration files
3. Re-push to origin

### Partial (keep version bump, revert source only)
1. Revert only `.claude-plugin/marketplace.json` source field back to github object
2. Keep 0.64.1 version (mark as "version bump only" release)

## Reversibility

| Component | Reversible? | Method |
|-----------|-------------|--------|
| marketplace.json source | ✅ Yes | Edit one field — `"./"` ↔ `{"source":"github",...}` |
| Version bump (0.64.1→0.64.0) | ✅ Yes | Re-edit 13 declaration files (mechanical) |

### No-overclaim boundaries

No official approval. No marketplace approval. No universal/full runtime support. No RISK-036/037/039/040 closure. No 1.0.0 readiness. Rollback is a single-field config revert + mechanical version re-bump. Low risk — the change is additive (restoring prior behavior), not destructive.
