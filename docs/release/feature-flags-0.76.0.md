# Feature Flags - 0.76.0

**Version**: 0.76.0 (minor)
**Release**: 看护模式七项 + /governance 性能修复打包——REQ-145.1~145.7 七项落地（AUDIT-145 诊断 → FIX-263 设计 → FIX-264~269 实现链）+ FIX-270 /governance 性能修复，随行 FIX-255/256/258、AUDIT-144、FIX-260/261/262（REQ-107/108 消费方）、DOC-002
**Date**: 2026-08-23
**Decision**: REL-069 (0.76.0 MINOR candidate packaging, candidate-only)

## Feature Flag Inventory

0.76.0 introduces no runtime feature flag and no kill-switch-controlled rollout. The release packages already-merged commits: FIX-263~269 (watchdog seven — bootstrap health summary `--summary-only`, Check 35 snapshot freshness, Check 36 risk-mitigation closure, Check 37 gate-release interlock, Check 38 CI evidence, capability grading declaration), FIX-270 (/governance status fast path + host check-governance speedup + mixed-root fixes), FIX-260/261/262 (REQ-107/108 consumers — review machine persistence, hook regex alignment, completion-recommendation machine loop), and FIX-255/256/258 + AUDIT-144 + DOC-002 (debt/hardening/diagnosis/projection ride-alongs). No external product surface is toggled by a flag; the changes are machine checks (read-only, fail-safe to WARN/no-verdict), added CLI subcommands, and deterministic projection advances operating under the existing candidate/released lineage model.

| Component | Default | Notes |
| --- | --- | --- |
| Candidate lineage | `--lineage-mode candidate` default | Does not require or prove that a release tag exists. |
| Released lineage | explicit mode | Requires `--release-commit`; verifies local and configured remote tag identity under `HOST_PROJECT_ROOT`. |
| `--summary-only` (FIX-264) | always-on session step (M4.1) | Runs once per session bootstrap via SKILL.md injection; `--level` tiers; >60s soft-timeout cancels; fail-safe to brief (`Governance: unavailable` / parse-degraded). No flag — it is the min behavioral floor, machine-checked by engine reuse. |
| Check 35-38 (FIX-265/266/267/268) | always-on checks | Read-only over `.governance/` + git; any parse failure fail-safes to WARN or no-verdict, never misreports FAIL; part of `check-governance` and (Check 37) `check-release`. No kill switch — a failing check stops release; it does not disable the check. |
| Check 30c / Check 34 (FIX-260/262) | WARN-only + effective-date exemption | REVIEW machine-provenance verdicts WARN-only with REQ107_MACHINE_PROVENANCE_DATE exemption (FIX-173/174 precedent); S2 recommendation reference WARN progressive per DEC-147. |
| `/governance status` fast path (FIX-270-A) | always-on command | Renders Scenario F panel data; `--json`; legacy full-read of governance files demoted to on-demand. |
| Host product-gate skipping (FIX-270-B) | host default skips; `--product-gates` explicit | 22 plugin product self-checks skipped by default on host projects (`[SKIP]` reported honestly); dogfood (this repo) keeps all gates. |
| Capability grading declaration (FIX-269) | static documentation | A-level protocol automation / B-level CLI-enforced / C-level system automation NOT implemented (plugin-contract L102/L114). Declaration, not a runtime toggle. |
| Release docs boundary tokens | static documentation | Each 0.76.0 release doc includes the five `check-release` `boundary_needles` and the compact negation wording verified to pass `_line_has_scoped_claim_negation`. |

## Rollout and Kill Switch

There is no runtime product flag to phase or disable. The changes are statically validated (per-commit TDD red->green; full regressions 1696-1895 passed + 237 subtests 0 failed across the chain; version-consistency/projection-sync/manifest/crossrefs all PASS recorded per commit) and internally exercised. Before release, use candidate lineage. After the release commit and `v0.76.0` are created and pushed, use released lineage with the exact commit. A failing released check is the kill switch: stop release completion and correct or roll back the tag/package state; do not weaken the check. For the watchdog checks, the equivalent "off" state is the rollback path (revert the release package; see rollback-plan-0.76.0.md) — there is no runtime toggle by design, because the checks are the minimum watchdog floor (REQ-145), not an optional feature.

## Test Boundary

- FIX-264: test_summary_only 15 cases red->green; full 1752 passed+237 subtests; R0/R1 APPROVED_WITH_NOTES/0. Timing disclosure (RISK-044, 2026-08-22, accepted via DEC-149): `--summary-only` wall-clock 31-32s, above design §3.1 <15s gate; DEC-149 revised acceptance signal to "single run <60s and once per session" (satisfied); subsecond quick-scan is a 0.77+ candidate; RISK-044 open with 2026-08-28 review milestone.
- FIX-265: 24 cases red->green; full 1792 passed+237 subtests; tv FAIL/router WARN/dogfood WARN live; R0 APPROVED_WITH_NOTES/0.
- FIX-266: 41 cases red->green; full 1864 passed+237 subtests; tv/router + BR-4 end-to-end; R0/R1 APPROVED_WITH_NOTES/0.
- FIX-267: RED 5 failed -> GREEN 31 passed; full 1895 passed+237 subtests; tv WARN/router PASS/host PASS; R0 -> R1 APPROVED_WITH_NOTES/0.
- FIX-268: 31 cases red->green; full 1823 passed+237 subtests; tv WARN/router PASS/dogfood PASS; R0/R1 APPROVED_WITH_NOTES/0.
- FIX-269: verify/projection/crossrefs/manifest/version all PASS; check-governance 113==113 zero new; R0 APPROVED_WITH_NOTES/0.
- FIX-270: 15 cases red->green; full 1768 passed+237 subtests; tv independent re-verify 0.47s status / 2.42s full / 0 plugin-path entries; R0/R1 APPROVED_WITH_NOTES/0.
- FIX-260/261/262: full 1696+213 / 1707+0 / 1725+237 0 failed; machine records REVIEW-FIX-260/261/262-R0 + RECO-FIX-262; R0 APPROVED_WITH_NOTES/0 each.
- Projection (REL-069): `release-projection --write` -> `{"state": "PASS", "written": 15, "source_version": "0.76.0"}` exit 0; persona v0.76.0 / AGENTS.md.template L3 `@bootstrap-version: 0.76.0` / fixture SKILL.md byte-equal / required snippets pins 0.76.0.
- check-version-consistency PASS; check-projection-sync --fail-on-issues PASS (15 projections). The release docs boundary wording is verified directly against the negation function template. No full-suite-green claim is made beyond the recorded runs.

## Migration Note (RISK-D5 — DSH preset staleness)

DSH upgrade path: `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`. The persona version line and 0.76.0 bootstrap template reach sessions only after `--sync` rewrites the DSH preset; a pulled-but-not-synced checkout still injects the old template. Do not claim session-level watchdog effects for unsynced installations. **After sync, the watchdog checks act on the governed project's own `.governance/` records with no per-project reworking.**

## No-overclaim Boundaries

This candidate does not create or prove `v0.76.0` and does not close RISK-036 or RISK-039. 0.76.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
