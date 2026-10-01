# Feature Flags - 0.62.0

**Version**: 0.62.0 (minor)
**Release**: zcode 插件市场适配（废弃逆向 local-load 机制）
**Date**: 2026-07-01
**Documentation provenance**: BACKFILLED on 2026-07-08 by DOC-001 (commit `7792b4e`); not created at release time.

## Feature Flag Inventory

This release has **no runtime feature flags** — the zcode marketplace install path is always active; the legacy local-load mechanism was removed.

## Behavior

| Component | Default | Notes |
|-----------|---------|-------|
| zcode marketplace install path | enabled (always active) | `.claude-plugin/marketplace.json` `source` changed from local `"./"` to structured github object `{"source":"github","repo":"peterwangze/software-project-governance"}` |
| Legacy zcode local-load (0.56.0) | removed | `project/zcode-local-load.py` (20KB reverse seed-hash tool) deleted; `docs/marketplace/zcode-local-load-0.56.0.md` marked DEPRECATED with banner pointing to new doc |

## No-overclaim boundaries

This is **protocol-consistency install**, not zcode official inclusion or review approval. RISK-036 (官方收录准备) stays open. No official approval. No marketplace approval (zcode or otherwise — "marketplace install path" here refers to the shared Claude/zcode marketplace protocol, not a reviewed/approved listing). No universal/full runtime support. No external first-session pilot success. No external host-project validation. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness.
