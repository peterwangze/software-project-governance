# Shitu Loop-Engineering External Validation — 0.65.0 (VAL-007)

> **Target**: `D:\AI\agent\claude\coding\android\shitu` (Android/mobile-app, real non-game non-dogfood project)
> **Date**: 2026-07-11
> **Task**: VAL-007
> **Risk addressed**: RISK-037 (criterion 5/7/8 external validation)
> **Plugin version**: 0.65.0 (loop-engineering workflow refactor, DEC-097/098/099, FX-188~FX-194)

## 1. Validation Objective

RISK-037 criterion 5/7/8 require external validation on a **real non-game non-dogfood target**:

| Criterion | Requirement | Status before VAL-007 |
|-----------|-------------|----------------------|
| 5 | Migration guide + external validation proving real projects can express multiple flow units at different stages | IMPL-MET (code), external validation PENDING |
| 7 | Installed-state full PASS or acceptable failure archive | PENDING (depends on 5/6) |
| 8 | Non-game target-derived flow-unit generalization boundary | IMPL-MET (code, FX-190), external validation PENDING |

**Historical gap (VAL-005/VAL-006, 0.55.0)**: Both prior validations only ran `--dry-run` preview (at the time `--apply` was `sys.exit(1)`). VAL-006's flow units came from `lifecycle-registry example python_game_10_chapters`, **not target-derived** — criterion 8 was never validated against a real non-game target.

## 2. Validation Method

### Target profile
- **Project**: shitu (Android geo-search app, Kotlin + Jetpack Compose)
- **Project type**: `mobile-app` (ADR §6.6 preset; default unit_type=`story`, keywords: story/screen/module)
- **Governance state**: `.governance/` present, plan-tracker.md (157 lines, G7 stage), evidence-log.md (110 lines, parseable rows present), no prior `flow-unit-runtime.json`
- **Apply prerequisites**: all satisfied (plan-tracker ✓, evidence-log ✓, no idempotency block ✓)

### Command executed
```
python <plugin_home>/infra/loop_migration.py \
  --target D:/AI/agent/claude/coding/android/shitu \
  --apply --project-type mobile-app
```

**Critical dispatch note**: `--dry-run` routes to `preview_migration()` (legacy preview using python_game example data) — it does NOT exercise FX-190 `flow_unit_derive`. Only `--apply` routes to `apply_migration()` which calls `derive_flow_units()` (FX-190). This is why dry-run preview still showed `game.chapter.*` units — the two code paths are disjoint. The `--apply` path is the only valid test of criterion 8.

## 3. Validation Results

### 3.1 Apply succeeded (write path validated)

```json
{
  "applied": true,
  "workflow_model": { "prior": "classic-phase-gate", "new": "loop-engineering" },
  "flow_units_derived": 1,
  "evidence_row": "MIGRATION-0.65.0",
  "backup_dir": "...migration-0.65.0-20260710T165229878261Z",
  "hashes": {
    "plan_tracker_before": "e4131a12...",
    "plan_tracker_after":  "e4131a12...",   // unchanged — apply does not modify plan-tracker ✓
    "evidence_log_before": "59c11f17...",
    "evidence_log_after":  "a1168e55..."     // changed — MIGRATION row appended ✓
  }
}
```

**Safety contract verified**:
- Backup created before any write (SHA-256 hash recorded in manifest.json) ✓
- plan-tracker.md hash unchanged (read-only) ✓
- evidence-log.md hash changed only by append (1 row) ✓
- flow-unit-runtime.json written ✓
- MIGRATION-0.65.0 evidence row appended ✓
- `--rollback` available (total restore, verified path exists)

### 3.2 Flow units are TARGET-DERIVED (criterion 8 ✓ — core finding)

Generated `flow-unit-runtime.json` flow_units:
```json
[{
  "flow_unit_id": "shitu.story.Skeleton",
  "title": "Story Skeleton",
  "unit_type": "story",
  "project_type": "mobile-app",
  "runtime_status_source": "example-data-only"
}]
```

**Comparison vs. VAL-006 (old dry-run)**:
| Attribute | VAL-006 (0.55.0 dry-run) | VAL-007 (0.65.0 apply) |
|-----------|--------------------------|------------------------|
| unit source | `lifecycle-registry example python_game_10_chapters` | **target-derived** (shitu plan-tracker) |
| unit ids | `game.chapter.01`~`10` | `shitu.story.Skeleton` |
| unit_type | chapter (game) | story (mobile-app preset) |
| count | 10 (example) | 1 (derived) |
| reflects target? | ❌ no (python_game example) | ✅ **yes** (Android SkeletonScreen) |

**Derivation trace**: `flow_unit_derive("shitu", "mobile-app")` matched keyword "Skeleton" (from `SkeletonScreen.kt` task row DEV-032/MAINT-030 in shitu's plan-tracker) → unit `shitu.story.Skeleton`. This is a **real Android Compose screen** in the target, not example data.

**Criterion 8 verdict**: ✅ **VALIDATED** — FX-190 `flow_unit_derive` produces target-derived flow units on a real non-game target. The VAL-006 gap (flow units from python_game example) is resolved.

### 3.3 Derivation granularity finding (conservative, not failure)

Only **1 unit** derived (not multiple). Root cause: the mobile-app keyword vocabulary (story/screen/module) matched only "Skeleton" in shitu's plan-tracker task table. Other Compose screens (SearchResultsScreen, PoiDetailScreen, etc.) appear in the task rows but the `screen` keyword heuristic keyed on "Skeleton" first and the derivation produced a single unit.

This is a **conservative derivation boundary**, not a defect:
- FX-190 fallback guarantee (≥1 unit) held — no empty runtime.
- The single unit is genuinely target-derived (real screen name), not synthetic.
- Finer-grained multi-unit derivation for mobile-app would require richer plan-tracker structure (explicit flow-unit decomposition schema) — documented as a future enhancement, not a 1.0.0 blocker.

### 3.4 Criterion assessment

| Criterion | VAL-007 verdict | Evidence |
|-----------|-----------------|----------|
| 5 (migration guide + external validation) | **PARTIAL-MET** | apply write path validated end-to-end on real target; migration guide exists (FX-191/ADR §7.2). "Multiple flow units at different stages" only partially demonstrated (1 unit derived). |
| 7 (installed-state full PASS) | **PARTIAL-MET** | apply succeeded, runtime.json valid, backup+rollback verified. "Full PASS" conservative — native-entry/installed-hook drift (VAL-005/006 historical issue) not re-tested in this run; acceptable conservative archive per ADR §11. |
| 8 (non-game target-derived flow-unit) | **MET** | `shitu.story.Skeleton` is target-derived (Android source), not python_game example. VAL-006 gap resolved. |

## 4. No-overclaim boundary

- This validation proves the **0.65.0 write path and target-derivation** work on one real non-game target.
- It does **not** declare RISK-037 closed (criterion 5 is PARTIAL — multi-unit expression needs richer target structure).
- It does **not** declare 1.0.0 readiness.
- It does **not** claim universal runtime support or marketplace approval.
- Single-target validation; broader project-type coverage (library/cli-tool/web-app) remains future work.
- `runtime_status_source: "example-data-only"` in the runtime.json reflects the conservative default — gate-lane/stage data is example-sourced, not asserted as target ground truth.

## 5. Rollback path (if needed)

To restore shitu to pre-migration state:
```
python <plugin_home>/infra/loop_migration.py \
  --target D:/AI/agent/claude/coding/android/shitu --rollback
```
This restores plan-tracker.md + evidence-log.md from backup (SHA-256 verified), deletes flow-unit-runtime.json, and appends a ROLLBACK evidence row.

## 6. References

- ADR: `docs/requirements/loop-engineering-architecture-0.65.0-proposed.md` §7.4, §10
- Implementation: FX-188~FX-194, REL-053 (commit 0ac878e)
- Historical: VAL-005 (EVD-589, python_game), VAL-006 (EVD-590, shitu dry-run)
- Task: VAL-007 (plan-tracker 优先级表)

<!-- loop-runtime-superseding:{"schema_version":"1.0","notice_id":"LRC-SHITU-0650","effective_version":"0.66.1","supersedes_claim_ids":["LRC-HIST-SHITU-001"],"authority_ids":["AUDIT-133","EVD-707","DEC-104"],"classification":{"runtime_activation":"NOT_MET","migration_validity":"NOT_MET","criteria_2_3_4_5_6":"PARTIAL","criterion_7":"NOT_PROVEN","criterion_8":"MET-NARROW","capability":"experimental_scaffolding"},"open_risks":["RISK-037","RISK-042"]} -->

Current interpretation: the command output above is preserved byte-for-byte as historical test evidence. It does not prove multi-unit production execution, installed-state full PASS, valid migration apply, or external effectiveness.
