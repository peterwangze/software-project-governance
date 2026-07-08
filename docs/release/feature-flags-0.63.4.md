# Feature Flags - 0.63.4

**Version**: 0.63.4 (patch)
**Release**: check_version_consistency VERSION_FILES 覆盖盲区修复（FIX-182）
**Date**: 2026-07-07

## Feature Flag Inventory

This release has **no runtime feature flags** — pure check-tool coverage scope fix, no runtime behavior change.

## Behavior

| Component | Default | Notes |
|-----------|---------|-------|
| check_version_consistency VERSION_FILES coverage | enabled (always active) | now covers all 4 plugin.json (Claude/Codex/Zcode/Chrys); was only 3/4 (missing .zcode-plugin + .chrys-plugin) |
| Print string N | corrected | "11 files, 3 plugin.json" → "13 files, 4 plugin.json" (N=13 = VERSION_FILES 7 + CHANGELOG 1 + plan-tracker 1 + HOOK_FILES 4) |

## No-overclaim boundaries

No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No external host-project validation. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. Pure bug fix (check-tool coverage scope fix), only affects check-tool coverage, no runtime behavior change.
