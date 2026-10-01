# Feature Flags - 0.77.0

**Version**: 0.77.0 (minor)
**Release**: DSH 标准插件安装支持 + 事故防再发链同槽——FEAT-010（bundle 形态随包安装）+ FIX-271 / AUDIT-146 / FIX-274 / FIX-272 / FIX-273 / FIX-275（RCA → 防再发固化 → always-on 注入面 → 守卫补全 → 检测加固 → 打包卫生）+ FIX-276（F-02 入槽 README 能力分级宣示补注，DEC-163）
**Date**: 2026-08-25
**Decision**: REL-070 (0.77.0 MINOR candidate packaging, candidate-only; transition/tag/push 待用户授权——DEC-143 交互基线)

## Feature Flag Inventory

0.77.0 introduces no runtime feature flag and no kill-switch-controlled rollout. The release packages already-merged commits: FEAT-010 (DSH standard plugin install support — bundle form: `dsh.bundle` + `dsh.skills` 35 entries + `cordis.patch.yml` composition layer + shipped `presets/governance/` preset + README standard install command), FIX-271 (R1-R5 anti-recurrence protocol hardening — M7.7 / dispatch red-line bundle / change-triage fifth step), AUDIT-146 (RCA report docs), FIX-274 (M7.7 always-on injection surface + Check 39 `requires_r1` completion gate, DEC-159/160/161/162), FIX-272 (bundle drift guards — @version-line dynamic anchor + `check_dsh_skills_manifest` + Check 40), FIX-273 (side-effect detection blind-spot hardening), FIX-275 (pyc packaging hygiene), FIX-276 (README capability-grading declaration note, DEC-163). No external product surface is toggled by a flag; the changes are machine checks, added CLI subcommands, behavior-contract injections (always-on text), package-hygiene configuration, and deterministic projection advances operating under the existing candidate/released lineage model.

| Component | Default | Notes |
| --- | --- | --- |
| Candidate lineage | `--lineage-mode candidate` default | Does not require or prove that a release tag exists. |
| Released lineage | explicit mode | Requires `--release-commit`; verifies local and configured remote (`github-https`) tag identity under `HOST_PROJECT_ROOT`. |
| Check 39 `check_r1_completion_gate` (FIX-274) | WARN-first (0.77.x observation window) | `requires_r1=true` task completed without R1 evidence → WARN; **tightening condition registered (DEC-160)**: after 2 consecutive zero-violation 0.77.x releases, escalate to FAIL — escalation MUST be decision-logged. No runtime flag — the progressive WARN→FAIL path is the mechanism. |
| Check 40 `check_dsh_skills_manifest` (FIX-272) | always-on (product-gate, same group as Check 33) | `dsh.skills` 35-entry bidirectional check (package.json ↔ disk); fail-closed; standalone CLI `check-dsh-skills-manifest`. |
| `@version-line` dynamic anchor (FIX-272) | always-on guard | `check_injection_contract` 28 anchors; authority = SKILL.md frontmatter; fail-closed (FIX-250 precedent). |
| M7.7 behavior-contract injection (FIX-274) | always-on injection surface | SKILL.md「关键行为契约」第 4 条 + DSH persona 第 5 条 (R1 three-of-one / R4 per-command relay / R5 wording) — always-on for every session, no toggle. |
| Persona/SKILL contract-block budget (FIX-274, DEC-161/162) | 2560B hard cap | Raised from 1536B/2048B by user decision (option A — contract fidelity over old cap); machine guards `test_persona_contract_block_stays_within_budget` + `test_skill_contract_section_stays_within_budget` (2560). Documentation-level invariant — no runtime flag. |
| Packaging hygiene (FIX-275) | static `files` config | `!**/__pycache__/` + `!**/*.pyc` negation patterns; measured GREEN 0 pyc / 5.72MB (-64%). No toggle — order-sensitivity constraint documented (patterns must stay after all directory whitelist entries). |
| Capability grading (FIX-276 + FIX-269) | static documentation | README now declares A/B implemented / C roadmap not-implemented (plugin-contract L114/L102), aligned to SKILL.md single source of truth. |
| Release docs boundary tokens | static documentation | Each 0.77.0 release doc includes the five `check-release` `boundary_needles` and the compact negation wording verified to pass `_line_has_scoped_claim_negation`. |

## Rollout and Kill Switch

There is no runtime product flag to phase or disable. The changes are statically validated (per-commit TDD red->green; full regressions recorded per commit — FIX-272 window 1923 passed / 28 pre-existing baseline failures; version-consistency/projection-sync/manifest/crossrefs all PASS recorded per commit) and internally exercised. Before release, use candidate lineage. After the release commit and `v0.77.0` are created and pushed (github-https), use released lineage with the exact commit. A failing released check is the kill switch: stop release completion and correct or roll back the tag/package state; do not weaken the check. For Check 39/40, the equivalent "off" state is the rollback path (revert the release package; see rollback-plan-0.77.0.md) — there is no runtime toggle by design, because the checks are the minimum watchdog floor (FIX-271/274 anti-recurrence), not an optional feature.

## Test Boundary

- FEAT-010: isolated-env install smoke + self-asserting boot double PASS; real `~/.dsh` zero-operation dual confirmation (time-window forensics + source counter-proof); review chain R0→R1→R2 APPROVED_WITH_NOTES/0 (REVIEW-FEAT-010-R2).
- FIX-271: TDD 12 new cases red->green (52/52); four-step key order byte-identical; 27 pre-existing failures confirmed unrelated via stash baseline; CODE R0 + DESIGN R0→R1 APPROVED_WITH_NOTES/0×2.
- AUDIT-146: R0 APPROVED_WITH_NOTES/0 (REVIEW-AUDIT-146-R0 machine record); report 266 lines.
- FIX-274: DESIGN R0 APPROVED_WITH_NOTES/0; CODE R0 NEEDS_CHANGE (P1-1 gate misfire / P1-2 SKILL budget over-cap) → R1 rework (DEC-161/162; gate fix red->green 10+2; dual budget guards 15) → CODE R1 APPROVED_WITH_NOTES/0; Check 39 real-data zero false-positives (35 records / 1 r1 incomplete legal skip).
- FIX-272: TDD 9 new cases red->green; pytest 1923 passed / 28 pre-existing baseline failures (stash baseline confirmed unrelated); R0 APPROVED_WITH_NOTES/0 (P2×2 registered follow-up + P3×6 discussion-level).
- FIX-273: TDD 4 red -> 61 green; pytest full 28 pre-existing baseline failures zero new (same baseline); R0 APPROVED_WITH_NOTES/0 (P0=0/P1=0/P2=0/P3=3).
- FIX-275: RED 397 entries/154 pyc/10.34MB → GREEN 243 entries/0 pyc/5.72MB (-64%); Reviewer independent re-verify (precise pyc count 154/10,340,875B + diff 397-243=154 three-way consistent; npm-packlist 10.0.3 source L166-169/L313/L318-338 verified); R0 APPROVED_WITH_NOTES/0 (P0=0/P1=0/P2=0/P3×4 + F5 evidence gap closed by Coordinator EVD-FIX-275).
- FIX-276: full verify PASSED (exit 0) + check-cross-references 68 files/649 refs zero dangling PASS + check-version-consistency 13 files PASS + check-manifest-consistency 565/608 PASS; R0 APPROVED_WITH_NOTES/0 (REVIEW-FIX-276-R0 machine row + RECO-FIX-276).
- Projection (REL-070): `release-projection --write` -> `{"state": "PASS", "written": 15, "source_version": "0.77.0"}` exit 0; persona v0.77.0 / AGENTS.md.template L3 `@bootstrap-version: 0.77.0` / fixture SKILL.md byte-equal / required-snippets pins 0.77.0; marker face 9 lines (governance-init ×3 + e2e mirror ×3 + e2e CLAUDE.md + root AGENTS.md; root CLAUDE.md gitignored local sync).
- check-version-consistency PASS; check-projection-sync --fail-on-issues PASS (15 projections). The release docs boundary wording is verified directly against the negation function template. No full-suite-green claim is made beyond the recorded runs.

## Migration Note (RISK-D5 — DSH preset staleness)

DSH upgrade path: `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --sync`. The persona version line (v0.77.0 + 5 behavior-contract lines) and 0.77.0 bootstrap template reach sessions only after `--sync` rewrites the DSH preset; a pulled-but-not-synced checkout still injects the old template. Do not claim session-level M7.7 effects for unsynced installations. **After sync, the anti-recurrence checks act on the governed project's own `.governance/` records with no per-project reworking.**

## No-overclaim Boundaries

This candidate does not create or prove `v0.77.0` and does not close RISK-036 or RISK-039. 0.77.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
