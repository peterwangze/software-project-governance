# Feature Flags - 0.61.0

**Version**: 0.61.0
**Release**: Governance Data Bloat Remediation
**Task**: REL-048
**Date**: 2026-06-28

## Feature Flag Inventory

This release has **no runtime feature flags** — all changes are statically enabled infrastructure improvements. The advisory/non-blocking behavior is configured declaratively via `architecture-health.json`, not runtime flags.

## Advisory vs Blocking Behavior

| Component | Default | Configurable? | Notes |
|-----------|---------|---------------|-------|
| `check_governance_data_size` (Check 28s) | **advisory** (does not block release gate) | Yes — `architecture-health.json` → `gate_integration.fatal_on_error` | WARN at 200KB, ERROR at 250KB. Inherits global `fatal_on_error=false` |
| `archive.py` auto-migration triggers | 4-trigger OR logic (first_migration / release_forced / task_incremental / fallback_90d) | Threshold constants in archive.py (`FIRST_MIGRATION_PLAN_SIZE_THRESHOLD=80KB`, `TASK_INCREMENTAL_THRESHOLD=20`, `FALLBACK_ARCHIVE_DAYS=90`) | Triggers evaluated regardless of task count (FIX-158 early-return fix) |
| `_task_status_is_archivable` status variants | Expanded closed-marker set | Hardcoded in archive.py | Recognizes ✅-variants: 已完成/已交付/已发布/保守闭环/完成候选/etc. |

## Rollback Hooks

No runtime flag to toggle. Rollback = code revert (see `rollback-plan-0.61.0.md`). The archive engine is more permissive than 0.60.0 (recognizes more formats/statuses), so reverting to 0.60.0 strict behavior is safe — already-archived data remains valid.

## Boundary Tokens (conservative)

- `governance_data_size` check is **advisory** (`fatal_on_error=false`) — it reports but does NOT block releases
- No runtime toggle to make it blocking (would require editing `architecture-health.json` `gate_integration.fatal_on_error=true`, affecting ALL ArchGuard checks)
- `enabled: true` in schema — can be set to `false` to disable just this check

### No-overclaim boundaries

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external first-session pilot success. No external host-project validation of the size guard. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. DEC-090/091 degraded SoD honestly noted. The advisory check guards but does not guarantee governance data health — sustained effectiveness needs external validation.
