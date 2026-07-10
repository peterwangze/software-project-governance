# Release Checklist - 0.64.1

**Version**: 0.64.1 (patch)
**Release**: marketplace.json source 改回 "./" 恢复本地/离线安装能力（FIX-186）
**Date**: 2026-07-10

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined (semver) | ✅ 0.64.1 (patch: marketplace config fix) |
| 2 | Change list enumerated | ✅ FIX-186 — marketplace.json source `"github"` → `"./"` |
| 3 | Change types marked | ✅ Bugfix (0.62.0 regression) |
| 4 | Release window | ✅ 2026-07-10 |

### Change inventory
- **FIX-186** (user feedback): `.claude-plugin/marketplace.json` plugin `source` from `{"source":"github","repo":"peterwangze/software-project-governance"}` back to `"./"`. Root cause: 0.62.0 (REL-051/DEC-093) changed source to `github` to adapt zcode marketplace protocol, which caused `/plugin install` to clone from GitHub even when marketplace was added from a local directory — breaking offline/restricted-network installation. Claude Code/zcode `/plugin install` reads the `source` field to determine where to get plugin content: `github` triggers network clone, `"./"` reads local marketplace dir. Fix: `"./"` restores 0.61.2 behavior. zcode investigation confirmed `"./"` is compatible (zcode marketplace add supports local path + reuses Claude protocol).
- **Version bump**: 0.64.0→0.64.1 (13 declaration files + e2e fixture pointers)
- **Breaking change**: `/plugin install https://github.com/.../xxx.git` direct git-URL path no longer available. Standard `/plugin marketplace add` + `/plugin install software-project-governance@spg` works in all scenarios (local/remote/offline).

## 7. Release Gate Evidence

```
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
→ Result: PASSED (all at 0.64.1)
python skills/software-project-governance/infra/verify_workflow.py check-projection-sync — PASS
```

### Boundaries (no-overclaim)

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS. No RISK-036/037/039/040 closure. No 1.0.0 readiness. Pure config fix restoring offline-installation capability. Breaking change (direct git-URL install path removed) is acceptable trade-off — standard marketplace add+install covers all scenarios.
