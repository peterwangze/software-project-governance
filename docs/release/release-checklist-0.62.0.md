# Release Checklist - 0.62.0

**Version**: 0.62.0 (minor)
**Release**: zcode 插件市场适配（废弃逆向 local-load 机制）
**Date**: 2026-07-01
**Documentation provenance**: BACKFILLED on 2026-07-08 by DOC-001 (commit `7792b4e`); not created at release time.

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined (semver) | ✅ 0.62.0 (minor: install-path protocol change) |
| 2 | Change list enumerated | ✅ marketplace.json source → github object; zcode-marketplace-install.md doc; README Tier 1 zcode row; local-load tool removed; DEPRECATED banner |
| 3 | Change types marked | ✅ Added (marketplace github source, install doc, README rows) / Changed (zcode install unified to marketplace protocol) / Removed (zcode-local-load.py) / Documentation (DEPRECATED banner, update notes) |
| 4 | Release window | ✅ 2026-07-01 |

### Change inventory
- **marketplace.json source change**: `"./"` → `{"source":"github","repo":"peterwangze/software-project-governance"}`, matching zcode new runtime `resolveGitPluginSource` accepted format and Claude official marketplace format.
- **zcode-marketplace-install.md**: new two-step install doc (`/plugin marketplace add` + `/plugin install`), with 0.56.0 local-load migration guidance.
- **README Tier 1**: zcode row added (marketplace protocol); Chinese install section adds zcode subsection.
- **Removal**: `project/zcode-local-load.py` (20KB reverse seed-hash tool) — not referenced by verify_workflow.py, no tests reference it, zero code-breakage on delete (DEC-093: reverse-engineered `D:\app\zcode\resources\glm\zcode.cjs` `rdt()`/`sCr()` algorithms to bypass `isSeedCurrent`, a fragile runtime coupling).
- **DEPRECATED banner** on `docs/marketplace/zcode-local-load-0.56.0.md` pointing to new doc; update notes on `official-readiness-gap-analysis-0.56.0.md` and `feature-flags-0.56.0.md`.
- **Version bump**: 0.61.2→0.62.0
- **verify output**: check-version-consistency only plan-tracker local lag (WARN, non-blocking); check-agent-adapters 5/5; full tests green.

## 2-6. (Standard checks — all PASS, see release-checklist-0.61.0 template)

## 7. Release Gate Evidence

```
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.62.0
→ Result: to be confirmed at commit time
```

### Boundaries (no-overclaim)

This is **protocol-consistency install**, not zcode official inclusion or review approval. RISK-036 (官方收录准备) stays open. No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external validation full PASS for real projects. No external first-session pilot success. No external host-project validation. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness.
