# Feature Flags - 0.71.0

**Version**: 0.71.0 (minor)
**Release**: systematic UX fixes for entry/loop/task-planning (FIX-222~229) — bootstrap entry determinism + behavior protocol dependency-aware recommendation + review deterministic triggers + task planning system
**Date**: 2026-07-27
**Decision**: FIX-222~229 (REL-063, user authorized)

## Feature Flag Inventory

0.71.0 introduces no runtime feature flag and no kill-switch-controlled rollout. The change delivers systematic UX fixes: FIX-222 bootstrap entry (AGENTS.md 3-method plugin_home location eliminating the chicken-and-egg), FIX-223/227 dependency-aware task-completion recommendation (behavior-protocol M7.4 step 6 + interaction-boundary.md:217 run `task-priority-analysis` then recommend next then AskUserQuestion, replacing mechanical highest-priority), FIX-224 deterministic review re-review triggers T1-T4 (M7.4 step 4.6), FIX-225 plan-tracker template (`依赖` column machine-parseable format + `workflow_model`/`permission_mode` fields), FIX-226 `task_priority.py` pure DAG parser + `compute_unblocked_tasks` + cycle detection + `task-priority-analysis` CLI subcommand (57 tests), FIX-228 change-control substantiated (dependency analysis + priority + conflict check mandatory for product code), FIX-229 change-impact-checklist task-level analysis. No external product surface is toggled by a flag; the fixes are behavior-preserving governance-record and pure-module additions operating under the existing candidate/released lineage model.

| Component | Default | Notes |
| --- | --- | --- |
| Candidate lineage | `--lineage-mode candidate` default | Does not require or prove that a release tag exists. |
| Released lineage | explicit mode | Requires `--release-commit`; verifies local and configured remote tag identity under `HOST_PROJECT_ROOT`. |
| Bootstrap plugin_home location (FIX-222) | static prose | AGENTS.md 3 methods (platform skill `file:` path / dev fallback / explicit param); no flag toggles it. |
| Dependency-aware task recommendation (FIX-223/227) | static protocol | behavior-protocol M7.4 step 6 + interaction-boundary.md:217 run `task-priority-analysis` then recommend then AskUserQuestion; no flag toggles it. |
| Review deterministic triggers T1-T4 (FIX-224) | static protocol | M7.4 step 4.6 deterministic re-review/terminal/escalation rules; no flag toggles it. |
| task-priority-analysis (FIX-226) | pure module + CLI | `task_priority.py` pure DAG parser + `verify_workflow.py task-priority-analysis` thin CLI entry; no flag toggles it. |
| plan-tracker 依赖 column (FIX-225) | static template | `core/templates/plan-tracker.md` machine-parseable dependency format; no flag toggles it. |
| Release docs boundary tokens | static documentation | Each 0.71.0 release doc includes the five `check-release` `boundary_needles` and uses the compact negation wording verified to pass `_line_has_scoped_claim_negation` for every scoped claim phrase. |

## Rollout and Kill Switch

There is no runtime product flag to phase or disable. The fixes are statically validated (task_priority.py 57 tests PASS; check-version-consistency 13 files PASS; check-projection-sync 13 projections PASS) and internally exercised. Before release, use candidate lineage. After the release commit and `v0.71.0` are created and pushed, use released lineage with the exact commit. A failing released check is the kill switch: stop release completion and correct or roll back the tag/package state; do not weaken the check.

## Test Boundary

- FIX-226 task_priority.py: 57 tests cover DAG parsing / unblocked computation / cycle detection / CLI, all PASS.
- DEC-134 authorized FIX-222~229; EVD-852. 3 independent analysis reports (sysgap-047 / audit-140 / audit-141) root-caused the gaps before fixing.
- check-version-consistency PASS (13 files); check-projection-sync PASS (13 projections). The release docs boundary fix is verified directly against the negation function. No full-suite-green claim is made.

## No-overclaim Boundaries

This candidate does not create or prove `v0.71.0`, does not backfill historical tags, and does not close RISK-036, RISK-039, RISK-040, or RISK-041. 0.71.0 does not close RISK-036/RISK-039/RISK-040/RISK-041 (official marketplace operations, ArchGuard external validation, entry determinism host validation, and release-lineage historical-tag disposition each have independent closure criteria not yet satisfied). No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039/RISK-040/RISK-041 closure, or 1.0.0 production-ready claim is made.
