# Feature Flags - 0.75.0

**Version**: 0.75.0 (minor)
**Release**: 关键行为规则注入面 + 空推荐降级打包——REQ-112/REQ-110 双落地（DEC-143 前置放大器；FIX-253 DEC-144 方案 A / FIX-254），随行 FIX-247~252 六个观察项/债务 commit 与 AUDIT-143
**Date**: 2026-08-21
**Decision**: REL-068 (0.75.0 MINOR candidate packaging, candidate-only)

## Feature Flag Inventory

0.75.0 introduces no runtime feature flag and no kill-switch-controlled rollout. The release packages already-merged commits: FIX-253 (REQ-112 deterministic injection surface — persona/SKILL contract blocks, version-projection anchoring, anchor check), FIX-254 (REQ-110 empty-recommendation fallback in task-priority analysis), six hardening commits (FIX-247~252: triage record robustness, test fixture alignment, bootstrap diagnostics, template marker sync, parser visibility, input disambiguation), and AUDIT-143 (audit report). No external product surface is toggled by a flag; the changes are injected text contracts, analysis-path additions, and fail-closed hardening operating under the existing candidate/released lineage model.

| Component | Default | Notes |
| --- | --- | --- |
| Candidate lineage | `--lineage-mode candidate` default | Does not require or prove that a release tag exists. |
| Released lineage | explicit mode | Requires `--release-commit`; verifies local and configured remote tag identity under `HOST_PROJECT_ROOT`. |
| Persona contract block (FIX-253) | always-on injected text | 4-line compressed contract (R1/R2/R3) in `adapters/dsh/agent.cordis.yml.template` L59-62; no flag — presence is machine-checked by `check-injection-contract` (Check 33, 12 anchors, fail-closed). |
| SKILL.md canonical contract section (FIX-253) | always-on loaded text | `关键行为契约` section (1623B<=2KB) is the canonical projection definition point; e2e fixture is a byte_copy. |
| Version-projection anchoring (FIX-253) | deterministic write path | `release-projection --write` advances persona L33 and AGENTS.md.template L3 with the frontmatter version; drift is detected by `check-projection-sync` (15 projections). |
| Empty-recommendation fallback (FIX-254) | fallback-only activation | `_build_empty_recommendation_fallback` runs only when the normal recommendation is empty (all tasks blocked); the normal path has zero behavior change — this is a scoped fallback, not a toggleable flag. |
| Anchor check (Check 33) | fail-closed | Missing anchors fail `check-governance` and the standalone subcommand; no kill switch — a failing check stops release, it does not disable the contract. |
| Release docs boundary tokens | static documentation | Each 0.75.0 release doc includes the five `check-release` `boundary_needles` and the compact negation wording verified to pass `_line_has_scoped_claim_negation` for every scoped claim phrase. |

## Rollout and Kill Switch

There is no runtime product flag to phase or disable. The changes are statically validated (FIX-253 S1-S8 all PASS, full regression 699+18+107+12+40 green; FIX-254 19 new tests red->green, merged regression 159/159; check-version-consistency PASS; check-projection-sync --fail-on-issues PASS 15 projections) and internally exercised. Before release, use candidate lineage. After the release commit and `v0.75.0` are created and pushed, use released lineage with the exact commit. A failing released check is the kill switch: stop release completion and correct or roll back the tag/package state; do not weaken the check. For the injected behavior contracts, the equivalent "off" state is the rollback path (revert the release package; see rollback-plan-0.75.0.md) — there is no runtime toggle by design, because the contracts are the minimum behavioral floor (REQ-112), not an optional feature.

## Test Boundary

- FIX-253: S1-S8 all PASS (S4 projection-sync 15 projections exit 0; S6 Check 33 PASS + standalone subcommand exit 0; S7 fixture byte-equal 20884B; S8 test_dsh_adapter 18/18 — version assertions dynamized from SKILL frontmatter, no manual sync channel); full regression 699+18+107+12+40 green.
- FIX-254: 19 new tests red->green (red Ran 119 failures=3 errors=15 -> green 119 OK); merged regression 159/159; live CLI unblocked=0 outputs non-empty Unblock pick (FIX-205 [P0], 7 downstream) + structured all_blocked reason.
- FIX-247~252: per-commit evidence chains closed (EVD-FIX-247~252); test_archive 119 green; test_verify_workflow green.
- Projection first-live-run (REL-068): `release-projection --write` -> `{"state": "PASS", "written": 15, "source_version": "0.75.0"}` exit 0; persona L33 v0.75.0 and AGENTS.md.template L3 `@bootstrap-version: 0.75.0` verified; fixture SKILL.md byte-equal to source.
- check-version-consistency PASS; check-projection-sync --fail-on-issues PASS (15 projections). The release docs boundary wording is verified directly against the negation function template. No full-suite-green claim is made beyond the recorded runs.

## Migration Note (RISK-D5 — DSH preset staleness)

DSH upgrade path: `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`. The persona contract block and 0.75.0 version lines reach sessions only after `--sync` rewrites the DSH preset; a pulled-but-not-synced checkout still injects the old template. Do not claim session-level injection effects for unsynced installations.

## No-overclaim Boundaries

This candidate does not create or prove `v0.75.0` and does not close RISK-036 or RISK-039. 0.75.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
