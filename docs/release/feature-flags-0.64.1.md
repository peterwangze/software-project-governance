# Feature Flags - 0.64.1

**Version**: 0.64.1 (patch)
**Release**: marketplace.json source 改回 "./" 恢复本地/离线安装能力（FIX-186）
**Date**: 2026-07-10

## Feature Flag Inventory

This release has **no runtime feature flags** — pure marketplace configuration fix, no runtime behavior change. The only change is the `source` field in `.claude-plugin/marketplace.json`.

## Behavior

| Component | Before (0.62.0~0.64.0) | After (0.64.1) |
|-----------|------------------------|----------------|
| marketplace.json `source` | `{"source":"github","repo":"peterwangze/software-project-governance"}` | `"./"` (relative path to marketplace root) |
| `/plugin install` (local marketplace) | clones from GitHub (network required) | reads from local marketplace dir (offline) |
| `/plugin install` (remote marketplace) | clones from GitHub | clones marketplace repo, then reads local `./` |

## No-overclaim boundaries

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No external host-project validation. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No RISK-040 closure. No 1.0.0 readiness. Pure config fix (marketplace source field), restores 0.61.2 offline-installation capability that 0.62.0 inadvertently regressed. Breaking change: direct `/plugin install <git-url>` path no longer available (source is no longer a github object), but standard marketplace add+install works in all scenarios.
