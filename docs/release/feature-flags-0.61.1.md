# Feature Flags - 0.61.1

**Version**: 0.61.1 (patch)
**Release**: archive engine decision/risk migration + verify cross-check
**Task**: FIX-162 + FIX-163
**Date**: 2026-06-30

## Feature Flag Inventory

This release has **no runtime feature flags** — all changes are statically enabled infrastructure improvements.

## Behavior

| Component | Default | Notes |
|-----------|---------|-------|
| decision/risk migration | enabled (runs in migrate_by_version when task_versions non-empty) | dry-run reports counts without writing |
| verify Check 3 cross-check | enabled (per-category symmetric) | strict equality per category |
| `_version_to_tuple` defensive parsing | enabled | extracts semver from text, returns None for non-semver |

## No-overclaim boundaries

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external first-session pilot success. No external host-project validation. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. DEC-090/091 degraded SoD honestly noted.
