# Release Checklist — 0.78.1 (REL-073)

**Version**: 0.78.1 (PATCH — DEC-172 裁决 A + DEC-176 FIX-290 范围核增)
**Window**: `v0.78.0 (afb959d) .. <final pre-transition commit>` — 13 commits（任务链 11 + 编排纠偏 1 + 候选 1；门禁/双审回填已并入候选）
**Status**: candidate（`release_authorized=false`；transition/tag/push 待 M-4 用户授权——DEC-143）

## Scope (per version-plan-0.78.1.md + DEC-176)

- DEC-172 裁决 A 确定入槽 9 项：DEC-171/FIX-282、N-P2-1/N-P2-2/N-P3-1/FIX-283、FIX-279 P2-1/P2-2（随链）、F-01/FIX-285、四步措辞/FIX-283、F-3/FIX-285
- FIX-281 缺陷子集（方案 A 拆两段）：②③④/FIX-287、⑤⑥/FIX-289、⑦⑨/FIX-288；判定面 ①⑧ 出槽 0.79.0
- FIX-272 P2×2：F1 穿越回归测试随 FIX-286 承载（锚定）；F2 诊断拆分随 FIX-284 联合承载
- DEC-176 范围核增：FIX-290 dsh 安全生命周期批（8 文件）
- 治理/规划产物：REL-072 queue-triage、REL-073 version-plan + 规划期双审报告

## Candidate Gate Results (M-2, 2026-09-05, candidate `bff92a1`)

| # | Gate | Result |
|---|------|--------|
| 1 | check-version-consistency | **PASS**（13 文件 0.78.1；advisory WARN ×2 分类：host plan-tracker 记录版本 Coordinator 打包后 bump〔同型惯例〕；根 CLAUDE.md gitignored 本地已同步 FIX-256 先例） |
| 2 | check-projection-sync --fail-on-issues | **PASS**（15 projections） |
| 3 | check-manifest-consistency | **PASS** |
| 4 | check-cross-references --fail-on-issues | **PASS**（零悬空/零废弃/零循环） |
| 5 | verify（无参） | **PASSED** |
| 6 | pytest 全量 | **27 failed / 2049 passed / 226 subtests passed**（amend 后全量复跑，2026-09-05）：FAILED=2 + SUBFAILED=25——逐类归属：test_cleanup manifest-presets **既有**（0.77.0 起结构基线，本轮 v0.78.0 同失败实证）+ test_loop_runtime_claims **既有**（RISK-048 环境敏感）+ test_pre_commit_review_evidence SUBFAILED×25 **既有**（bash/WSL 环境基线，EVD-926 同口径——其中 replay_real_evidence_log 子测试因 evidence-log 本批补账行 EVD-928..947 扩增 +1 子失败，属环境失败类内部的计数扩张非新增失败类）；对照 0.78.0 实绩基线 26（2 FAILED + ~24 SUBFAILED 同类）；打包期 1 新增失败（EntryBootstrapTemplateTests 标记 0!=3）已修复并复跑 6/6 绿（Release Reviewer R0 F-5 亦单点复证 1 passed） |
| 7 | check-governance --summary-only | **117 issues vs 0.78.0 基线 127（-10，零新增）**；首个 FAIL = 18c 执行包既有（FIX-222/223/224/253 allowed_change_scope 既有行）；Check 10 M5 = queue-triage-0.78x.md L66 既有登记（REL-072 规划文档，127 基线已含） |
| 8 | check-injection-contract | **PASS**（28 anchors 含 @version-line 动态锚解析 0.78.1；打包期 preset 版本行漏改已修复） |
| 9 | check-dsh-skills-manifest | **PASS**（35/35） |
| 10 | check-release --version 0.78.1 --require-changelog --lineage-mode candidate | 核心静态门禁 **PASS**（version consistency/release fact source/hot fact source/runtime readiness/first-session/governance pack/agent adapters/projection sync 全 PASS）；基线 FAIL 分类披露（R0 首测时 release docs ×3 **新引入**〔三件套缺 No-overclaim needles——Release Reviewer F-1 判定，非既有基线；已按 0.78.0 模板补齐并复跑，见本行后附〕+ archive integrity 既有 + execution gates〔governance health 117 既有 + unit tests 既有〕）；**F-1 修复后复跑：`[PASS] release docs`**（Result: FAILED - 2 issue(s)——仅剩 archive integrity 既有 + execution gates〔governance 117 既有 + unit tests 既有〕，与 REL-071 基线分类同型） |
| 11 | release-ledger --version 0.78.1 --no-remote | **NATIVE_CANDIDATE**（candidate `bff92a1`；state PASS） |
| 12 | quality-tools | **NOT_RUN** 如实记录（Ruff/mypy 未安装——ADR-010 不虚构 PASS） |

**打包期缺陷当场修复记录**（M-1 内闭环，均已在 amend 收敛）：preset 版本行 @version-line 漏改（injection-contract FAIL→PASS）；governance-init.md ×3 + e2e 镜像 ×3 + e2e CLAUDE.md 标记漏改（pytest 1 新增失败→修复）。

## Review Evidence (M-3)

- 任务链：FIX-282..289 + FIX-290 逐任务 Code Reviewer R0 APPROVED/APPROVED_WITH_NOTES、unresolved_blockers=0（机录行 + docs/reviews/×10）
- REL-073 规划期：DESIGN-R0 + RELEASE-R0 APPROVED_WITH_NOTES/0（机录 REVIEW-REL-073-R0/R1）
- M-3 候选双审：Release Reviewer + Design Reviewer（对 afb959d..candidate 全窗）——结果追加于本节

## 出槽登记（无隐藏带入）

version-plan-0.78.1.md §5.1 裁决表 22 行全承载（含 ①⑧→0.79.0、G3/G5/G6/W-7/BC-7→0.79.0、FIX-279 遗留观察项 P2-3+P3×3、F-03/F-04/F-04-env/F-05+BC-1 维持搁置）；RISK-044 复评挂 0.79.0（DEC-169 ②）。

## No-overclaim Boundaries

This candidate does not create or prove `v0.78.1` and does not close RISK-036 or RISK-039. 0.78.1 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). RISK-049 is newly registered and open (adapter claim-vs-verification-level gap; closure criteria registered). No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.

- candidate-only：`release_authorized=false`——transition/tag/push 待 M-4 用户授权（DEC-143，唯一人工门）。
- Breaking changes：无。
