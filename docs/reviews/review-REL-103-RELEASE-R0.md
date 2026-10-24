# REL-103 RELEASE R0 — 0.99.0 发布面审查报告（M-3）

- Task ID：REL-103 · Round：R0（RELEASE 链；前任实例未交付，本实例全新执行）
- 审查人：Release Reviewer（重派实例；独立于发布面作者 e8730d91/收敛批 c0a4032f）
- 日期：2026-10-24 · 结论：**APPROVED_WITH_NOTES / unresolved_blockers=0**

## 1. 对象绑定（独立复算）

| 面 | 状态 |
|---|---|
| SKILL frontmatter | 0.99.0（check-version-consistency **PASSED**；3 stale exemption WARN 为 DEC-213③ 预存在非阻断） |
| built-plan projections | written=17 针脚同步（check-projection-sync 内嵌面 PASS） |
| e2e fixture 双入口 | **@bootstrap-version 0.98.0 滞留**（mtime 10-15 16:55 未随 bump 重渲染）——见 F-1 |
| project/CHANGELOG.md | `## [0.99.0]` 节在位：五 FEAT+八 FIX+REL-103 载荷、DEC-362~368 链、随版披露全量 |
| rollback-plan-0.99.0.md | §1-§6 完整：三分时点回滚序列/FIX-448 迁移恢复专面（备份 DDD37374+staging evdt-20261024T000345Z+I1 不可变）/保守边界 5 token（§6） |
| release-checklist-0.99.0.md | 结构完整（范围冻结/检查项/GO 披露面提案/发布序列 M-5~M-8/保守边界节） |
| feature-flags-0.99.0.md | 三延续旗标+FIX448_EVD_M2_EXECUTE 门禁旗（非用户开关声明明确）+行为变更面 3 条+token 全量 |
| version-plan-0.99.0.md | DEC-368 四项定稿一致（承载=b/顺延 0.100/P2=FIX-448/D1） |

## 2. candidate 门独立重跑（完整面，含 execution gates）

**FAILED-6**（B 类零残留确认）：
1. **provenance ×2**：FIX-448/FIX-457（machine-signal）载入而 user-named REL-103 未闭合——亲读判定=**REL-103 闭合后自然消解**（发布链 M-7/M-8 收口 → task committed → released lineage 复跑 PASS）。机制核实：ADR-021 §2.2.4/DEC-286(7) 的门只惩罚"版本边界隐形顺延"，正式收口不算。
2. **release docs ×3**：三件套+feature-flags 未 git 跟踪——**发布 commit git add 后消解**（机制：check 逐文件 `git ls-files` 判定）。
3. **execution gates**：verify PASS / **unit tests PASS（exit=0——import 修复生效，1141 口径）** / e2e PASS / **governance health exit=1（11 issues）**=GO 终审披露面（0.98 先例 DEC-358①"FAIL 面以 GO 终审披露"）：18e×3（REL-103 回填+FIX-444/445 暂停披露）/18f/18g/25/28s/30/30c/35/36——全部在册已知族，governance exceptions 机制为 annotation-only（DEC-278(5) 原始 FAIL 保留，不改变结果）。

## 3. 逐项判定

| # | 审查面 | 判定 |
|---|---|---|
| 1 | 版本 bump 面（17 针脚+双根 entry） | PASS（consistency PASSED@0.99.0；主仓 AGENTS/CLAUDE 已 0.99.0） |
| 2 | CHANGELOG 载荷一致性 | PASS（21 commits 窗口载荷逐票在节；窗口锚 7f161a6..HEAD 正确） |
| 3 | rollback-plan 可执行性 | PASS（序列命令化；迁移恢复三件材料路径亲验存在） |
| 4 | feature-flags 诚实性 | PASS（门禁旗≠质量门证明明示；零 kill-switch 滚出面如实） |
| 5 | candidate A 类消解机制 | PASS（5/6 项经 commit+REL-103 收口消解；亲读 gate 源码 L7548/check-release 报文） |
| 6 | GO 披露集诚实性 | PASS（FIX-444/445 顺延/容量 BLOCKED/NOT_RUN 5 条/M5 反模式/099 未规划全披露，无冒充完成） |
| 7 | 发布安全（暂停 WIP 隔离） | PASS-with-note（两文件 M 态=暂停 WIP 既有修改〔1666 diff 行=其自身暂停态〕；发布 commit 精确 add 排除即安全；"与暂停时点字节一致"无基线可独立验证——限制披露） |
| 8 | .governance/junction 零泄漏 | PASS（git status untracked 抽查：.governance 与 node_modules 不在发布面；junction 目标在 gitignored 区） |

## 4. Findings

**P0/P1：无。**

**F-1（P2）e2e fixture 双入口 bootstrap 滞留 0.98.0**：project/e2e-test-project/CLAUDE.md+AGENTS.md 未随版本 bump 重渲染（mtime 10-15；@bootstrap-version 0.98.0）。判定非发布门阻断（check-release gate 面不含 entry-bootstrap-sync——candidate 报文无此项，built-plan projection 面已 PASS）；但为 0.99 载荷真实遗漏（e8730d91"17 针脚"宣称漏 fixture 面）。**建议 M-6 GO 前渲染修复**（发现即闭环，5 分钟面：按 0.99.0 模板重渲染双入口）；若不修，须在 GO 披露面加列（fixture 滞留至 0.99.1 或下批渲染）。

**F-2（P3）untracked 历史产物入库决策**：docs/diagnostics/×5、docs/research/×1、docs/prototypes/、docs/architecture/dsh-upstream-owned-registration.md（0.2.0 旧设计）、closeout-plan-0.99.0.md 等历史 untracked 面随发布 commit 一并入库 or 继续留置——建议发布 commit 面决策时明确（0.98 先例口径对照），避免"顺带入库未经决策"。

**F-3（P3）stale exemption WARN×3**（DEC-213③）：STATIC_PIN_EXEMPTIONS 行号漂移（test_verify_workflow 20803/20806/21336）——非阻断，下批 re-audit。

**F-4（P3）候选收口序**：provenance 消解依赖 REL-103 闭合——发布序列须 tag→REL-103 收口（acceptance/quality_budget 回填+task committed）→ released lineage 复跑，顺序不可倒。

## 5. GO 就绪评估

**GO 可达**（无 P0/P1）：发布 commit（精确 add：22 M 文件面+四件套新文件，排除暂停 WIP 两文件）→ tag v0.99.0 → REL-103 收口回填（18e/18f/18d-RB2 消解）→ `--lineage-mode released --release-commit <commit>` 复跑（provenance×2+docs×3 消解验证）→ governance health 11 issues 按 0.98 先例（DEC-358①）以 GO 终审披露面裁定 → ledger 终账 → push。建议 F-1 在 GO 前闭环。

## 6. 边界合规

只写本报告+scratch（.codex-sandbox/REL-103/review-release-r0/）；零 stage/commit/push；治理热表只读；未修改任何被审对象。通信异常披露：无（未收到其他 agent 转包/委派消息；前任实例未交付原因未知，本实例按 prompt 全新执行）。

*报告完。本文件为 REL-103 RELEASE R0 唯一产出写面。*
