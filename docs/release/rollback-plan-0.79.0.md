# Rollback Plan — 0.79.0 (REL-075)

> 复刻 version-plan-0.79.0.md §3.1 回滚边界表（0.77.0 R0 P2-1 先例义务延续；0.78.1 同型）。**注记**：本文件在边界表语义保真前提下对工作树作适配细化（0.79.0 各交付面的单独回退路径 + 已执行归档迁移的恢复路径）——§3.1 两级回滚边界与约束逐项保持。

## Rollback Triggers（回滚触发条件——不依赖人的临场判断）

| # | 触发条件 | 判定口径 |
|---|---|---|
| 1 | M-2 门禁核心静态项（#1 version-consistency / #2 projection-sync / #3 manifest / #4 cross-refs / #8 injection-contract / #10 check-release candidate 核心）FAIL 且打包期不可当场修复 | 0.78.1 先例：打包期缺陷当场修复（preset 版本行/标记面）后复跑；不可修复 → 回退候选 |
| 2 | pytest 全量出现**新增失败类**（对照存量基线逐类归属——AUDIT-151/152 口径：环境敏感 24+1/已知缺陷 2/数据耦合 6 之外的新类） | 「零新增失败」为 version-plan §4 #6 预期；数据耦合类需按 AUDIT-152 分类学归属后再判 |
| 3 | check-governance 健康基线出现**新增 FAIL 类**（对照 EVD-983 迁移后基线 31 的构成——打包期实测为准） | 基线数字漂移惯例：先实测归类，确认新增类才触发 |
| 4 | M-3 候选双审 NEEDS_CHANGE 超轮（T2 触发器：round ≥ 3 仍 NEEDS_CHANGE） | 治理行为契约 T2——转 BLOCKED + escalation，候选冻结 |
| 5 | M-6 释放态门禁 FAIL（check-release released / release-ledger --remote / tag peel 不一致）或发布后隔离安装冒烟（launch.py --smoke / dsh_upgrade_regression）失败 | 释放态 FAIL = fail-closed 阻断；已推送 tag 见边界表第二行（governed recovery only） |
| 6 | 发布后核心功能冒烟失败 + 48 小时内新缺陷回归（替代判定标准——本仓无生产监控面，0.78.x 先例口径） | 至少一个可验证的成功定义不满足 → 回滚评估 |

## 回滚边界（version-plan-0.79.0.md §3.1 复刻）

| 状态 | 回滚方式 | 约束 |
|---|---|---|
| 候选/transition 态（candidate commit 已提交、tag 未创建/推送） | `git revert` 候选 commit（manifest-only / 版本投影 / 发布文档面可逆） | 常规可逆操作（0.76.0 rollback-plan Reversibility 先例） |
| 已发布 v0.79.0 tag（本地 + 远端） | **仅 governed recovery**（Coordinator + 显式证据 + DEC） | **绝不静默重指**——远程 tag 修正为不可逆发布动作（"Published remote tag — Not treated as routine reversible state；Governed recovery only；never silently retarget"） |

## Rollback Steps

**S1 候选态全量回退**（tag 未创建——默认路径）：

1. `git revert <candidate-commit>`（候选 commit = 版本投影 + CHANGELOG/三件套 + release manifest 面——**不含任务链实体变更**：34 个任务 commit 各自独立可逆，按 §3.1 候选回退不触碰任务链）。
2. 版本投影面恢复：`release-projection --write` 以恢复后的 SKILL frontmatter（0.78.1）重写 15 projections，复跑 #1（check-version-consistency）+ #2（check-projection-sync）。
3. 复跑 #10（check-release --version 0.79.0 --lineage-mode candidate）确认候选事实源一致 + `git diff --check`。
4. 回滚事件入 decision-log（append-only，不改写历史行）。

**S2 部分回滚路径**（按交付面独立回退——各面 commit 独立，0.78.1 先例）：

- **版本投影面**：随 S1 候选回退（子任务 A 交付物在候选 commit 内）。
- **post-commit Step 4b（FEAT-017）**：FEAT-017 自带回滚文档——删除 Step 4b 三态段即回退（advisory 非阻断，M1.2 MUST 保留权威与回退——FIX-302 口径）；或 `git revert c6026ce`（独立可逆）。
- **G5 tpa 缓存（FEAT-012）**：`--force` 旁路即时恢复逐次全量输出；整体回退 `git revert 24c6f61`（fail-open 设计——缓存损坏不阻断）。
- **release gate 新组件（FEAT-016）**：`--skip-execution-gates` 即时旁路（显式 [SKIP] 披露）；整体回退 `git revert 213fbba`。
- **派发锁 API（FEAT-013）**：模板锁操作机器化回退 = 恢复手写协议不推荐；代码面 `git revert 3a108c2`（Check 26 向后兼容——expected_new 可选）。
- **判定面批（FIX-291/292/294/295）**：各自 commit 独立 revert；注意 FIX-292 委托 FIX-291 终态链语义（先 revert 292 再 291——依赖序）。
- **棘轮/契约矩阵（FEAT-019/020）**：基线变更（R1 24,302→24,329 sanctioned）有审计记录；回退代码后按 R7 `--regen` 幂等重建；FEAT-020 快照显式再生成（80→81〔FEAT-019〕→82〔FEAT-013〕键耦合同步）。
- **归档识别（FIX-301）/ 已执行归档迁移（EVD-983）**：代码回退 `git revert a599843`；**已迁移治理数据的恢复** = 从完整备份 `%TEMP%\governance-backup-20260910-prefix301`（863 文件，R1(b) 三选一留痕）Copy-Item 回 `.governance/`，复跑 `verify_workflow.py check-archive-integrity` 校验守恒——迁移本身幂等（FIX-301 验证），禁止手工拼合归档文件与热文件。
- **dsh 已安装用户**（FIX-290 先例对称表）：`link:` 用户 `git checkout v0.78.1` 前滚回退；`file:`/`github:` 用户 `dsh plugin remove` 后以 0.78.1 tag 重装（`github:...#v0.78.1`）；`.agent-presets/governance`（launch.py 装入）用 `launch.py --uninstall` 移除——不受 git 回退影响。
- **治理记录（.governance，gitignored）**：不受 git 回退影响；DEC/EVD 行按 append-only 纪律补记回退事件。

**S3 已发布 tag（governed recovery）**：见边界表第二行——Coordinator + 显式证据 + DEC；历史 tag 变更必须有独立 DEC（ADR-010 historical boundary；historical_backfill 不作为 native PASS）。

## Reversibility 表（Amazon 可逆性分类——release-checklist skill 第三步）

| 变更面 | 可逆性 | 回退方式 | 预计回滚时间 |
|---|---|---|---|
| 版本投影 + 发布文档 + manifest（候选 commit） | 可逆（routine） | git revert + release-projection --write + 门禁复跑 | < 10 min |
| FEAT-017 hook Step 4b | 可逆（文档化回退） | 删 Step 4b 或 revert c6026ce | < 5 min |
| FEAT-012 G5/G6 | 可逆（带 --force 旁路） | revert 24c6f61 | < 5 min |
| FEAT-016 gate 组件 | 可逆（skip 旁路显式） | --skip-execution-gates / revert 213fbba | < 5 min |
| FEAT-013 派发锁 | 可逆（Check 26 向后兼容） | revert 3a108c2 | < 10 min |
| FIX-291/292/294/295/296/299/300/302 判定/缺陷面 | 可逆（依赖序注意） | 逐 commit revert（292→291 依赖序） | < 30 min（全量） |
| FEAT-018/019/020 棘轮/契约/性能（0.80.0 前置波） | 可逆（基线 regen 幂等 + 快照再生成） | revert + R7 --regen + 快照 --regen | < 30 min |
| FIX-301 + EVD-983 归档迁移 | 可逆（完整备份 + 幂等 + integrity 校验） | 备份恢复 + check-archive-integrity | < 30 min |
| 已发布 v0.79.0 tag（本地 + 远端） | **不可逆常规面**（governed recovery only） | Coordinator + 显式证据 + DEC；绝不静默重指 | 按事件裁量 |

## No-overclaim Boundaries

This plan does not authorize historical tag backfill and does not close RISK-036 or RISK-039. 0.79.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). RISK-049 已关闭为既成治理事实（DEC-185——非本计划回滚范围）；RISK-044 缓解中 / RISK-046 根因已交付维持打开至 2026-09-30 复评窗 / RISK-047/048 维持观察——本计划不改变任何风险状态。It claims no official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready status. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.

- 本计划为可逆性分析载体（本仓无独立测试环境——0.76.0/0.77.0/0.78.1 先例）；回滚演练以「部分回滚路径 + 门禁复跑」为验证形式，S1 全量回退未实际执行过（如实声明——不宣称「已在测试环境验证」）。
- candidate-only：`release_authorized=false`——transition/tag/push 待用户授权（DEC-143，M-4 唯一人工门）。
- Breaking changes：无。

## 回滚后验证

复跑 #1（check-version-consistency）/ #2（check-projection-sync）/ #10（check-release --version 0.79.0 --require-changelog --lineage-mode candidate）+ `git diff --check`；归档面加跑 `verify_workflow.py check-archive-integrity`；回滚事件入 decision-log（append-only）。
