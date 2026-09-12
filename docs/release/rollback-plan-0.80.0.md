# Rollback Plan — 0.80.0 (REL-076)

> 0.80.0 无 `version-plan-0.80.0.md`（无独立规划工件）；本文件的回滚边界与约束按 0.77.0/0.78.1/0.79.0 先例同型复刻，并按 0.80.0 的两个独立交付面（重构线 P1 首批 / dsh 零侵入改造）细化单独回退路径。

## Rollback Triggers（回滚触发条件——不依赖人的临场判断）

| # | 触发条件 | 判定口径 |
|---|---|---|
| 1 | M-2 门禁核心静态项（#1 version-consistency / #2 projection-sync / #3 manifest / #4 cross-refs / #8 injection-contract / #10 check-release candidate 核心）FAIL 且打包期不可当场修复 | 0.78.1/0.79.0 先例：打包期缺陷当场修复后复跑；不可修复 → 回退候选 |
| 2 | pytest 全量出现**新增失败类**（对照存量基线逐类归属——AUDIT-151/152 分类学之外的新类） | 「零新增失败」为预期；环境敏感/数据耦合类需先按分类学归属再判 |
| 3 | check-governance 健康基线出现**新增 FAIL 类**（对照 EVD-983 迁移后基线构成——打包期实测为准） | 基线数字漂移惯例：先实测归类，确认新增类才触发 |
| 4 | **Check 28v（FIX-309 新增）在真实 dsh 上 FAIL**——即 0.80.0 交付的预设组合在用户环境的 dsh 版本上不合法 | 这是本版新增的**最敏感触发器**：Check 28v 的存在意义就是捕获 FIX-308 类漂移；它 FAIL = 护栏工作正常且必须立即处置（修组合，不修护栏） |
| 5 | **真机验收失败**（用户环境）：a) 安装后预设页/新会话仍异常（0.80.0 要修的原始症状复现）；b) 非治理预设会话**仍能看到**治理技能；c) 设置页无「自定义」标签 / 无法删除 / 无法打开目录 | 三项任一不满足 → 立即回滚评估（本候选**未**验证这三项，见 release-checklist「真机验收面」节） |
| 6 | M-3 候选双审 NEEDS_CHANGE 超轮（T2 触发器：round ≥ 3 仍 NEEDS_CHANGE） | 治理行为契约 T2——转 BLOCKED + escalation，候选冻结 |
| 7 | M-6 释放态门禁 FAIL（check-release released / release-ledger --remote / tag peel 不一致） | 释放态 FAIL = fail-closed 阻断；已推送 tag 见边界表第二行（governed recovery only） |
| 8 | 发布后 48 小时内出现 dsh boot 类故障（预设页崩毁 / 无法创建新会话）且归因于本包 | 0.80.0 的原始症状——同症状复现 = 最高优先级回滚 |

## 回滚边界（0.77.0/0.78.1/0.79.0 先例复刻）

| 状态 | 回滚方式 | 约束 |
|---|---|---|
| 候选/transition 态（candidate commit 已提交、tag 未创建/推送） | `git revert` 候选 commit（manifest-only / 版本投影 / 发布文档面可逆） | 常规可逆操作 |
| 已发布 v0.80.0 tag（本地 + 远端） | **仅 governed recovery**（Coordinator + 显式证据 + DEC） | **绝不静默重指**——远程 tag 修正为不可逆发布动作（"Published remote tag — Not treated as routine reversible state；Governed recovery only；never silently retarget"） |

## Rollback Steps

**S1 候选态全量回退**（tag 未创建——默认路径）：

1. `git revert <candidate-commit>`（候选 commit = 版本投影 + CHANGELOG/三件套 + release manifest 面——**不含任务链实体变更**：本窗 21 个任务 commit 各自独立可逆）。
2. 版本投影面恢复：`release-projection --write` 以恢复后的 SKILL frontmatter（0.79.0）重写 15 projections，复跑 #1 + #2。
3. 复跑 #10（`check-release --version 0.80.0 --lineage-mode candidate`）+ `git diff --check`。
4. 回滚事件入 decision-log（append-only，不改写历史行）。

**S2 部分回滚路径**（按交付面独立回退）：

- **dsh 零侵入改造（FIX-310，单 commit `5a259e2`）**：`git revert 5a259e2` 整体回退（恢复 `cordis.patch.yml` 两条 UPDATE 行 + `presets/` 预烘焙副本 + `dsh.skills` 字段）。**注意**：该 revert 会**重新引入 RISK-050 的结构性根因**（上游内部面耦合）——仅在真机验收失败且短期无法定位时使用，回退后 MUST 记 DEC + 重开处置任务。
- **dsh 已安装用户（FIX-310 之后）**：`dsh plugin --profile <p> remove <ref>` 移除 bundle 行（组合回到未安装态）；已渲染到用户根的 `$DSH_HOME/.agent-presets/governance/` 由用户在设置页删除或手工删除该目录——**它是用户自有目录，git 回退不影响它，反之亦然**；`launch.py --install` 装入的同名副本用 `launch.py --uninstall` 移除。
- **Check 28v（FIX-309）**：`git revert 94c0a61` 整体回退（含 Check 注册面 + 测试 + 快照）；回退后兼容性护栏消失——**只在护栏本身误报时回退**（组合真的不合法时不回退护栏）。
- **FIX-307/308 修复面**：`git revert 031f0fa`（persona 键名）/ `4998c6d`+`73e04e5`（接入兼容性）——FIX-307 面已被 FIX-310 删除，单 revert FIX-307 需处理与 FIX-310 的依赖序（**先 revert 310 再 307**）。
- **重构线 P1 首批（FEAT-021/022/025/026 + FIX-303/304/305）**：各 commit 独立 revert；**依赖序**：FEAT-026 → FIX-306(未入) → FIX-305 → FEAT-022 → FIX-304 → FEAT-025 → FIX-303 → FEAT-021。registry/契约层为**并置事实源**（引擎未接线），回退不改变引擎行为；FEAT-025 注册表 + FEAT-020 快照有对账关系，回退后按 `--regen` 幂等重建快照。
- **治理记录（`.governance`，gitignored）**：不受 git 回退影响；DEC/EVD 行按 append-only 纪律补记回退事件。

**S3 已发布 tag（governed recovery）**：见边界表第二行——Coordinator + 显式证据 + DEC；历史 tag 变更必须有独立 DEC（ADR-010 historical boundary；historical_backfill 不作为 native PASS）。

## Reversibility 表（Amazon 可逆性分类——release-checklist skill 第三步）

| 变更面 | 可逆性 | 回退方式 | 预计回滚时间 |
|---|---|---|---|
| 版本投影 + 发布文档 + manifest（候选 commit） | 可逆（routine） | git revert + release-projection --write + 门禁复跑 | < 10 min |
| FIX-310 dsh 零侵入改造 | 可逆（单 commit；但回退=重新引入 RISK-050 根因） | revert 5a259e2 +（用户侧）`dsh plugin remove` | < 20 min |
| FIX-309 Check 28v | 可逆（独立 commit） | revert 94c0a61 | < 10 min |
| FIX-307/308 修复面 | 可逆（依赖序：310 → 307） | revert 031f0fa / 4998c6d+73e04e5 | < 15 min |
| FEAT-021/022（契约层 + registry，引擎未接线） | 可逆（并置事实源，无引擎耦合） | 按依赖序逐 commit revert | < 20 min |
| FEAT-025/026（quick-scan 两切片 + 快照对账） | 可逆（shadow 默认旁路） | revert + 快照 `--regen` | < 20 min |
| FIX-303/304/305（审查遗留批） | 可逆（小面） | 逐 commit revert | < 15 min |
| 用户根已渲染预设 `$DSH_HOME/.agent-presets/governance/` | 可逆（用户自有目录，幂等重建） | 设置页删除 / 手工删目录 / 重启自动重建 | < 2 min |
| 已发布 v0.80.0 tag（本地 + 远端） | **不可逆常规面**（governed recovery only） | Coordinator + 显式证据 + DEC；绝不静默重指 | 按事件裁量 |

## No-overclaim Boundaries

This plan does not authorize historical tag backfill and does not close RISK-036 or RISK-039. 0.80.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). RISK-050 本版交付结构性根因消除但**维持打开**（真实环境验收 + 复评窗收口）——本计划不改变任何风险状态。RISK-044 缓解中 / RISK-046 根因已交付维持打开至 2026-09-30 复评窗 / RISK-047/048 维持观察 / RISK-049 已关闭（DEC-185，非本计划范围）。本计划不声明真机验收面（设置页标签/删除/打开目录、非治理会话无治理技能、治理会话技能目录完整性）成立。It claims no official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready status. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.

- 本计划为可逆性分析载体（本仓无独立测试环境——0.76.0/0.77.0/0.78.1/0.79.0 先例）；回滚演练以「部分回滚路径 + 门禁复跑」为验证形式，S1 全量回退**未实际执行过**（如实声明——不宣称「已在测试环境验证」）。
- candidate-only：`release_authorized=false`——transition/tag/push 待用户授权（DEC-143，M-4 唯一人工门）。
- Breaking changes：见 `docs/release/release-checklist-0.80.0.md` §Breaking Changes（4 项——①dsh 安装形态变更 ②`package.json` 结构变更〔`type`/`main`/`exports`/`engines` 新增 + `files` 新增 `lib/`、`agent-presets/`、移除 `presets/` + `dsh.skills` 死字段退役〕③四处重复面退役〔`presets/governance/agent.cordis.yml`、`adapters/dsh/preset.yml`、`adapters/dsh/agent.cordis.yml.template`、`dsh.skills` 字段/守卫面〕④其它五适配层与核心规则零改动）。RELEASE R1 N-6 更正：本行原仅列举 `presets/` 一处，与 checklist 的四项枚举不一致。

## 回滚后验证

复跑 #1（check-version-consistency）/ #2（check-projection-sync）/ #10（`check-release --version 0.80.0 --require-changelog --lineage-mode candidate`）+ `git diff --check`；dsh 面加跑 `verify_workflow.py check-dsh-preset-compat`（Check 28v）+ `adapters/dsh/launch.py --smoke`（隔离 home）；重构线面加跑 `archguard-ratchet`（R1/R6/R7）；回滚事件入 decision-log（append-only）。
