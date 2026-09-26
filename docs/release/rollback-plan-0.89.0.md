# Rollback Plan — 0.89.0（REL-090 M-1R / REL-092）

> **M-1R 草案（REL-092，2026-09-26）**——Governance Developer Agent 起草、供 Coordinator 审后随候选提交；结构与措辞对齐 `docs/release/rollback-plan-0.88.0.md` 先例（含 0.81.0 R0 F-01/F-04 区间教训）。**回滚演练本版未排程**（0.84.0 演练由 FIX-354 专项承载；0.85.0/0.86.0/0.87.0/0.88.0 批内无对应演练票——如实标注，见 §4 #10）；本草案正文不预填演练结果。**本版特有面**：**B-12/B-13 回退预案引用不触发（§7——version-plan §7 口径）**——0.89 无新激活面（DEC-244 激活授权票不捆绑、五前置核验只核验不激活），B-12 回退预案与 B-13 反向转换方案为 0.88 版显式交付件（`docs/release/rollback-plan-0.88.0.md` §7 专节 + §8 部署 tag vs revert 区分节双锚——DESIGN-R0 F-3 勘正），本版**引用不触发**；**行为修正回退注记（§1）**——FEAT-065 gate 闭集替换 / FIX-391 零写拒绝面 / 判据收敛三面的回退 = 版本级还原对应文件，无 flag 级中间态。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.89.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。回滚验证口径（如执行）全部在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）下进行，隔离验收不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；do not claim 1.0.0 production-ready。
- **无激活面不越权主张**：本版出厂全 WARN（B-12）/ 缺省 `MD_ACTIVE`（B-13）姿态与 0.88 一致且 0.89 窗口零触碰——本文件**不主张**任何 BLOCK 族已激活或 JSON 权威已生效；§7 引用不触发语义以「未激活即零回退需求」为本版实际交付态。
- **发布 tip 未生成前不预先编造**：本文件写作时点（M-1R，2026-09-26）0.89.0 的发布 tip（M-5 transition 提交）**尚不存在**——所有 `<发布 tip>` 占位由 M-5 生成后回填，绝不预先虚构 hash。

## 区间锚定（含先例教训注记、两段论证与本版窗口构成事实 —— MUST 先读）

**回滚区间（triage 锚定）= `33d19b0..<发布 tip>`**（回退点 = **`v0.88.0` tag**；`33d19b0` = tag peel = REL-086 M-5 transition 提交「0.88.0 transition candidate→released manifest-only」；tag object `82905e6`，taggerdate 2026-09-25 20:08:32 +0800 实测——FIX-349 口径 taggerdate 权威；release-plan-0.89.0「回滚区间锚定」节同锚同源）：

- **论证①（下界 = `33d19b0`——本版候选面与完整窗口合一，单轨无双轨分歧）**：git 区间语义 `X..Y` **排除下界自身**。七票行为载荷（批次一 FIX-393/394 + 批次二 FIX-390/392/395 + 批次三 FIX-391/FEAT-065）+ M-0（REL-090）+ M-1 bump（REL-091）**全部落在 `33d19b0` 之后**；前版收尾两提交（`2dac7af` REL-086 M-6 修复批 / `9347c11` REL-086 M-8 收口批——0.88.0 发布收尾的文档/治理记录面）亦在 tag 后落库，如实纳入区间（非行为载荷——回退影响见 §1「发布文档面」行）；无 0.85.0 树内搭车批的 DEC-222 归属面，因此 triage 锚定 `33d19b0..<tip>` 同时就是完整行为回退区间：撤销即回到 `v0.88.0` 行为（peel `33d19b0`）。单轨，M-3 审查只需复核单轨锚定与窗口计数。
- **论证②（终点 = `<发布 tip>`，非候选打包提交）**：0.81.0 先例 **F-04**——post-candidate 提交修改区间内新增 release 文档导致 revert 冲突（实测 3 处 UU；0.84.0 演练 P-12 反向实证 exit 1/CONFLICT）。终点 MUST 是 M-5 transition 提交（hash 由 M-5 生成后回填，不预编造）。

> **窗口构成事实（实测 2026-09-26，M-3 Release Reviewer 复核输入）**：`git rev-list --count 33d19b0..HEAD` = **12**（HEAD = `b66bd25` REL-091 M-1 bump；`git describe` = v0.88.0-12-gb66bd25 交叉印证）。12 提交 = 前版收尾 2（`2dac7af` M-6 修复批 + `9347c11` M-8 收口批）+ M-0 一批（`76c86a9`）+ 批次一 2（`8a94d64` FIX-393 / `3cb4048` FIX-394）+ 批次二 3（`def9508` FIX-390 / `65c8e4b` FIX-392 / `7795f59` FIX-395）+ 批次三 3（`c9b7415` FIX-391 / `ab7a8e1`+`b950fef` FEAT-065）+ M-1 bump（`b66bd25`）。区间计数不写死：M-5 现场以 `git rev-list --count 33d19b0..<发布 tip>` 取值记入 EVD。
>
> 1. **单轨 revert 程序**：`git revert --no-commit 33d19b0..<发布 tip>`——撤销 0.89.0 全部行为 diff（七票 + M-0 + M-1 bump + M-1R 材料 + 后续发布批）；
> 2. **`git checkout v0.88.0` 替代锚（不等价，如实标注）**：落点 = peel `33d19b0`（transition 提交）——与 revert 的差异 = 不产生 revert 提交（历史保留 vs 撤销记录）、适合分支操作；代码/版本/行为面落点一致（0.84.0 演练 P-5 同款结论）；
> 3. **终点必须是发布 tip 而非候选打包提交**——post-candidate 提交会修改区间内新增的 release 文档导致 revert 冲突（0.81.0 先例 **F-04**；0.84.0 演练 P-12 反向实证）。

## 1. 本版改动的回滚影响分类

| 类别 | 本版内容 | 回滚影响 |
|---|---|---|
| **FEAT-065 gate 闭集替换 + 锁腿真释放（行为修正①）⚠️ 与 FIX-391 同文件** | `ab7a8e1`+`b950fef`（DEC-248 拆分后链内面）：shrink-locks→release-locks 真释放接线 + gate 闭集 lock_ttl_le→task_locks_released（任务索引+文件锁归属双面 fail-closed）+ 三处过时披露勘正 + lock_ttl 死输入移除；改动面 = `closure_chain.py` + `tests/test_closure_chain.py` 两文件（DEC-248① 锁面） | **回退 = 还原 closure_chain.py + tests/test_closure_chain.py 两文件**：task_locks_released gate 消失、shrink-locks TTL 收缩伪释放回归（0.88 已知态）；lock_ttl 死默认输入面恢复（死输入无行为效果——如实注记）；自定义 spec 链 lock_ttl_le 声明的 fail-closed 拒绝面消失（回到 0.88 静默接受形态——门禁信号弱化面如实披露）；**FIX-391 与本票共文件 closure_chain.py——整窗 revert 按区间回退两票链面，禁单票选择性还原**（同文件串行面——组合③；选择性还原会产生半回退混合态） |
| **FIX-391 closure journal 版本感知读取器（行为修正②）** | `c9b7415`（REL-089 条件③消解 + DEC-241 附带裁定机器门禁落地）：未知事件/出窗 schema 零写拒绝（run/resume/finalize/cancel/reopen 四写入口）+ seq 防占用 backstop + 0.87 兼容矩阵五格红绿；读 fail-safe 半面不变 | **回退 = 机器门禁消失，人工处置路径回归**：0.89 期 journal 由 0.88 读取器读取——0.89 期事件类型与 0.88 **兼容**（release-locks 腿复用 locks-release 接线，journal 事件面不变——EVD-1181「释放后 journal 仅 closure_ready」），0.88 忽略面读取合法；若发布窗内出现未知形态 journal 行（0.89 写入口零写拒绝下不应发生），回退后按 `rollback-plan-0.88.0.md` §8 运行手册门禁处置（0.88 事件闭包清单程序——resume/finalize 禁止面）；**路径 B backport 候选保留**（FIX-391 backport 进重建分支——0.88 rollback §8/REL-089 条件③先例） |
| **判据收敛三票（行为修正③）** | FIX-393（`8a94d64` 三解析器 committed 词表）/ FIX-394（`3cb4048` 终态行刷新机制 + 13 行对齐工具面）/ FIX-395（`7795f59` Check 28c 热事实源判定对齐）——改动面 = task_priority.py / task_row_update.py / verify_workflow.py / archive.py | **回退 = 0.88 已知缺陷态回归（如实列出，无数据损坏面）**：tpa 误推荐已交付票/误 blocked 复活；终态行滞留装饰文本机制消失（13 行对齐结果保留——plan-tracker 为治理数据 gitignored，回滚零触碰，对 0.88 引擎忽略面读取合法）；热事实源 20 条伪 FAIL 簇复活；DEC-246① 退出条件的判据收敛承诺随回滚消失 |
| **检查器族 FIX-390/392** | `def9508`（Check 18/18b 结构化状态判据——DEC-241 消解）+ `65c8e4b`（Check 30 复合键判据——DEC-242③ 消解，V3 链内轮次——DEC-247）——改动面 = verify_workflow.py + checks/ | **回退 = 例外面复活**：DEC-241 例外 2×2 FAIL 形态（Check 18/18b 分叉）+ V3 全局轮号键控伪像（DEC-242③ 登记形态）回归为已知披露；FIX-390 豁免差分（S 30→47 expansion=17）登记面随回滚消失——账本历史行保留（事实记录）；FIX-394 刷新机制与 FIX-390 同窗退回——组合①写入→读取链回 0.88 形态 |
| **M-0 规划票（REL-090）** | version-plan-0.89.0 + 双审报告 + roadmap 0.89.0 行 + 六票 triage 机录（`76c86a9`——文档/治理记录面） | 文档面随区间 revert 消失（审计信息——§5 #7）；治理记录面（机录 EVD/审查报告登记行）不回退（事实记录）；DEC-244~248 决策记录保留（决策事实不随代码回退撤销） |
| **M-1 bump 版本面（REL-091）** | 全仓 bump：SKILL frontmatter 权威锚 + 投影 28 面 + CHANGELOG 0.89.0 段（单 canonical）+ hooks 版本行 + 双根 entry bootstrap + REQUIRED_SNIPPETS 六锚 + static-pin 消解（`b66bd25` 已落库） | **随整窗 revert 完整撤销**——回滚后版本声明面回 0.88.0；static-pin 账本回 0.88 形态（9 bump-time rows 随回滚失义、4 行 self-dormant 恢复）；`release-projection --write` 单次收敛能力随 FIX-366 系修复保留（0.87.0 已交付——回滚不回退到绕开手法） |
| **入口文件形态（工作区侧）** | repo-root `CLAUDE.md` / `AGENTS.md` 双根 entry bootstrap（M-1 已写盘） | **半自动回退项（MUST 手工收口）**：git revert 还原已跟踪入口文件与 canonical 模板，但用户工作区本地未跟踪入口投影 revert 不触碰 ⇒ 回滚后重跑 `sync_entry_projection.py --project <workspace> --source-root <plugin_root> --profile standard --primary CLAUDE.md --write`（幂等，双 apply 零 diff 既有测试锁定） |
| **治理数据面 + 治理工件** | 本版 `.governance/` 记录（EVD-1171~1182、DEC-244~248、七票 TRIAGE/REVIEW 机录、13 行对齐收据、ops 台账 committed 终态行）+ B-12/B-13 工件（posture/state——**0.89 窗口零触碰，缺省缺席**）+ closure journal 0.89 期事件 | **不进 git 窗口**（gitignored）——回滚零触碰；0.88.0 引擎读同一份治理数据合法（新增条目/committed 终态 token 对旧引擎是忽略面——0.89 词表收敛是读取侧判据非写入格式变更）；13 行对齐/后缀刷新结果保留（数据事实）；closure journal 0.89 期事件类型与 0.88 兼容（§FIX-391 行） |
| **测试面** | 七票测试载荷（FIX-393 17 新测试 / FIX-394 28P+12subtests / FIX-390 红绿集 / FIX-392 九用例+364 行 / FIX-391 15+2 用例 / FEAT-065 八项集 / FIX-395 8 测试） | 回滚后测试基线回到 0.88.0 期清单（4119 基线——0.89 新增面随回滚消失）；计数下降是回滚的预期结果，不是回滚失败（§4 验证表如实注记）；static-pin 9 行 bump-time 豁免随回滚失义（0.89.0 字面量 token 回 then-future 形态——如实注记） |
| **发布文档面** | 本四件套 + `skills/software-project-governance/core/releases/0.89.0.json`（待建） | 区间内新增文档——0.81.0 先例 **F-04** ⇒ **回滚 MUST 以完整区间表达到发布 tip**（终点同规）；审查报告（review-REL-090 系列 / review-FIX-390~395 系列 / review-FEAT-065 / review-REL-091 等）随 revert 消失——如需保留审计痕迹回滚前 MUST 归档副本（§5 #7） |
| **渲染/预设交付面** | DSH persona 版本行 / `adapters/dsh/AGENTS.md.template` / hook `@version` 行（M-1 bump 28 面内） | **回滚需重装预设**（0.87.0/0.88.0 同款）：回退后 MUST 重跑适配层安装/渲染（`python <plugin_root>/adapters/dsh/launch.py --sync`），否则宿主注入面仍是 0.89.0 文本而引擎为 0.88.0——版本不匹配混合态。DSH 侧回滚验证以隔离环境（环境变量重定向至临时目录）渲染 parity 为准 |
| **LRC 文本豁免账本（既有）** | `core/loop-runtime-claim-exemptions.json`（FIX-320 期承载——本版零改动；与 B-11 Check 16/17 账本是两套机制，如实区分） | 回滚对该账本零影响（条目维持）；Check 16/17 的 REQ-092/EVD-1146 披露面随引擎回退回到 0.88.0 形态（EVD-1146 行对旧引擎为忽略面读取合法）；Check 30 V3×5 披露面复活（DEC-242③ 例外面——如实归类非回滚失败） |

## 2. 回滚程序

### 2.1 插件侧（维护者）

```powershell
# 1) 记录当前状态（证据）
git -C <plugin_root> log --oneline -1
git -C <plugin_root> for-each-ref refs/tags/v0.89.0   # 期望 v0.89.0（已 tag 时；peel 应为 M-5 transition 提交）
python <plugin_root>/skills/software-project-governance/infra/verify_workflow.py check-version-consistency

# 1b) B-12/B-13 第一层确认（未激活/未切换 = 零回退需求——0.89 缺省态核验，§7 引用不触发前提核验）
#     期望：.governance/.write-guard-posture.json 不存在（全 WARN 零足迹——0.89 窗口零触碰）
#           .governance/.decision-store-state.json 不存在（MD_ACTIVE 零足迹——0.89 无切换）
#     任一存在 ⇒ 先走 rollback-plan-0.88.0 §7 对应第二层回退通道，再继续整窗 revert

# 2) 回退到本版之前的稳定点（单轨——区间 = 完整窗口 = 候选面合一）
#    区间 = 33d19b0..<发布 tip>（<发布 tip> = M-5 transition 提交，hash 由 M-5
#    生成后回填；本文件写作时点该提交不存在，不预填）：
#    ⚠️ 起点必须是 33d19b0（v0.88.0 peel）——12 提交（含前版收尾两提交与 M-1 bump
#    落库提交）全部在该下界之后，漏任一即行为残留（含 gate 闭集 / 零写拒绝 /
#    判据收敛 / 版本面 0.89.0 token）。
git -C <plugin_root> revert --no-commit 33d19b0..<发布 tip>
#    区间计数不写死：M-5 现场以 `git rev-list --count 33d19b0..<发布 tip>` 取值记入 EVD
#    （M-1R 起草时点实测 = 12）。
#    替代锚【不等价】：直接切回稳定 tag（落点 = peel 33d19b0；无 revert 记录）
git -C <plugin_root> checkout v0.88.0

# 3) 入口投影重同步（MUST——本地未跟踪入口投影 revert 不覆盖；§1 载体行注记）
python <plugin_root>/skills/software-project-governance/infra/sync_entry_projection.py `
  --project <workspace> --source-root <plugin_root> --profile standard --primary CLAUDE.md --write

# 4) 重装适配层（本版经 M-1 触碰 DSH 模板/persona 版本行/hook 版本行 ⇒ 必做；隔离验证后再考虑后续动作）
python <plugin_root>/adapters/dsh/launch.py --sync

# 5) 回滚后守卫/存储工件核验（§4 #11/#12——健康宿主期望零足迹文件不出现）
```

### 2.2 用户侧（受影响用户）

1. `/plugin update`（或重装插件）回到 0.88.0——版本号回退后 marketplace 版本比对生效；
2. 重装/重渲染 agent 预设（DSH 宿主：`launch.py --sync`）使注入面与引擎版本一致；
3. 工作区入口文件（`CLAUDE.md` / `AGENTS.md`）恢复为 0.88.0 引导段——按 §2.1 步骤 3 重跑投影（幂等、可重复）；
4. `GOVERNANCE_LEGACY_BEHAVIOR` / `behavior_profile: legacy` 配置可保留（0.88.0 认识该变量，语义不变；如需洁净可移除）；
5. 用户数据无需任何动作（§3）；B-12/B-13 缺省零足迹态下无任何守卫/存储工件清理义务；已按机录路径写入的治理行（含 13 行对齐结果、committed 终态 token）合法保留（0.88.0 引擎按忽略面读取）；中断遗留锁如发布窗内曾按受控流程释放，其释放记录为事实保留。

### 2.3 发布前中止（M-0~M-4 窗口）

- 未 tag / 未 push 时中止：候选材料尚未提交 ⇒ 删弃工作树中未提交的四件套与后续发布批即可（M-1 bump 已落库 `b66bd25`——中止 = revert 该提交或整窗 reset；`.governance/` 不受影响）；
- 已提交候选但未 tag：`git reset --hard 33d19b0`（整窗丢弃——本版无双轨场景之分）**执行前 MUST 确认无在途未推送载荷**（reset 属破坏性命令——现场执行属 Coordinator 破坏性 git 确认面，0.84.0 演练 P-9 同口径）；不影响已发布的 0.88.0（tag `v0.88.0` 与 `skills/software-project-governance/core/releases/0.88.0.json` 均不在本窗口内）；
- 已 tag 未 push：本地 `git tag -d v0.89.0` + 丢弃 transition 提交（**在 push 之前**；push 之后见 §5）。

## 3. 数据安全（回滚不损坏用户数据）

- **治理数据零风险**：`.governance/`（plan-tracker / evidence-log / decision-log / risk-log / archive / review-artifacts）**不在 git 窗口内**（gitignored），回滚不读不写不删；0.88.0 引擎读取同一份数据合法（EVD-1171~1182 / DEC-244~248 / committed 终态 token / 13 行对齐后缀对旧引擎是忽略面——FIX-393 判据收敛是读取侧词表面，非写入格式变更）；已封闭历史周期经专席③前置归档迁移的行按 archive/index.md 可回读（§B1 语义——归档证据=有效证据）；
- **B-12 工件零足迹（未激活态——本版缺省且窗口零触碰）**：`.write-guard-posture.json`（guard CLI `--activate-block` 独占写入）与 `.write-guard-violations.json`（违规台账）在健康宿主为零足迹或缺席——回滚零触及；如发布窗内曾执行激活（授权票动作——本版无），回退通道见 rollback-plan-0.88.0 §7 第二层（flag 回 WARN / break-glass——均 audited 不可静默）；
- **B-13 工件零足迹（未切换态——本版缺省且窗口零触碰）**：`.decision-store-state.json` 缺席 = `MD_ACTIVE` epoch 0 零足迹；`decision-log.md` 本版全程保持 md 权威字节——回滚零触及；如曾切换（授权票动作——本版无），回退 = rollback-plan-0.88.0 §7 第二层（rollback-begin→rollback-export→rollback-activate）；
- **closure journal（FIX-391/FEAT-065 面）**：0.89 期事件类型与 0.88 兼容（release-locks 腿复用 locks-release 接线——journal 事件面不变，EVD-1181）；已登记的 closure 事件为事实记录——回滚后保留；0.89 期经受控流程人工释放的中断遗留锁，其释放记录为事实保留（禁批量清锁纪律下的逐条留痕）；
- **机录凭证行**：已按机录路径写入的机器凭证行（`〔op-…〕` 锚 / EVD-1171~1182 / DEC-244~248 / receipt 台账行）回滚后保留——0.88.0 引擎忽略面读取合法，无解析风险（task-row-update 字节保持设计——未触碰行零改写）；
- **工作区入口文件**：回滚重写 `CLAUDE.md` / `AGENTS.md` 的 Governance Bootstrap 段（canonical 模板投影，段替换语义）——段外内容零触碰（先例测试锁定：自定义尾段保留；双 apply 零 diff）；
- **不触碰用户配置目录**：本版回滚操作不写 `$HOME` 下任何配置目录、不写 `$DSH_HOME`；适配层重装按既有隔离约定（`$tmpHome` 临时目录重定向）验证；
- **不可逆数据处理**：本版无数据迁移执行、无 schema 变更执行、无治理文件格式变更执行（无激活——B-12/B-13 激活/切换不在本版发布动作内；FIX-391/FEAT-065 拒绝面为 fail-closed 门禁非数据迁移）⇒ 无「回滚后数据不可读」风险；**若发布窗内已执行激活/切换**（授权票动作），其回退数据面由 rollback-plan-0.88.0 §7 第二层通道承载（仅备份不算可回滚）。

## 4. 回滚后验证（MUST 全绿才算完成）

| # | 验证项 | 命令 | 期望（0.88.0 态） |
|---|---|---|---|
| 1 | 版本一致性 | `verify_workflow.py check-version-consistency` | PASSED，source = **0.88.0** |
| 2 | 投影同步 | `verify_workflow.py check-projection-sync --fail-on-issues` | PASSED（registry 28 面〔回退后合同面〕+ 入口双根，按 0.88.0 canonical 源） |
| 3 | 发布投影 | `verify_workflow.py release-projection` | PASS，`source_version = 0.88.0` |
| 4 | 全量资产 | `verify_workflow.py verify` | PASSED（0.88.0 期 snippet 面；新增面随回滚消失） |
| 5 | 入口投影形态 | 读 `AGENTS.md` / `CLAUDE.md` 引导段 | `@bootstrap-version: 0.88.0`（本地未跟踪入口由 §2.1 步骤 3 重同步） |
| 6 | 注入预算姿态 | `verify_workflow.py check-injection-budget --profile standard` | resident hard 三 profile 与 0.88.0 基线一致（版本 bump 不改 token 计数的对称面：回滚同样零漂移，如实实测注记） |
| 7 | 测试基线 | `pytest` / `verify` 计数 | 回到 0.88.0 期清单（4119 基线口径——0.89 新增面随回滚消失，计数下降 = 预期结果，如实注记） |
| 8 | e2e | `verify_workflow.py e2e-check` | PASSED（fixture 随窗口回退自洽） |
| 9 | 治理健康 | `verify_workflow.py check-governance` | 与回滚后当场值一致（不预填数字；**census 回 0.88 形态**——REQ-092×n + EVD-1146×1 维持 + DEC-241 例外×4 与 V3×5 披露面复活 + 热事实源伪 FAIL 簇复活，如实归类非回滚失败；EVD-1171~1182 行对旧引擎为忽略面） |
| 10 | **回滚演练** | 隔离副本执行 §2.1 `revert --no-commit` 干跑 | **未排程（如实标注）**——0.84.0 由 FIX-354 专项承载（隔离副本 `git clone --no-hardlinks` 法 + 零污染三重指纹先例）；0.85.0/0.86.0/0.87.0/0.88.0 批内无演练票。**建议**：M-3 审查裁决是否补演练；若补，MUST 隔离副本执行（就地执行污染候选索引）+ 真实 `<发布 tip>` 生成后复跑 |
| 11 | **B-12 后果核验** | `verify_workflow.py governance-write-guard --show-posture`（或读 `.governance/.write-guard-posture.json`） | **期望全 WARN / 姿态文件缺席**——0.88.0 已知态回归（本版窗口零触碰，无姿态残留；如发布窗曾激活——授权票动作，核验 `--deactivate-block` 已执行且报告留痕，不可静默面） |
| 12 | **B-13 后果核验** | 读 `.governance/.decision-store-state.json` + `decision_migration.py status` | **期望状态文件缺席（MD_ACTIVE 零足迹）**——0.88.0 已知态回归（md 权威；本版无切换；如曾切换——授权票动作，核验 rollback-export/rollback-activate 已执行，见 rollback-plan-0.88.0 §7） |
| 13 | **closure journal 兼容核验**（本版新增——行为修正②回退面） | 读 `.governance/closure-events.jsonl` 尾部 + 对含 0.89 期事件的 closure 执行只读检查 | 0.89 期事件类型（closure_ready 面——事件面不变）被 0.88 读取器忽略面读取合法；如出现未知形态行（不应发生），**禁止 resume/finalize 该闭包**——按 rollback-plan-0.88.0 §8 运行手册门禁处置（0.88 事件闭包清单程序）或走路径 B（FIX-391 backport） |

## 5. 不可回滚项（如实列出）

1. **已 push 的 `v0.89.0` tag**：tag 一旦推送即不可撤销——只能前进到 0.89.1（PATCH）修复，不得移动已推送 tag（VERSIONING.md 版本纪律）；
2. **`skills/software-project-governance/core/releases/0.89.0.json` 的 transition 事件**：作为发布事实一旦提交即不可「取消」；回滚只能通过新的发布记录表达（不得改写既有 manifest 事件）；
3. **已落账的机录凭证与事件日志**：`.governance/` 内 machine-provenance 行（`〔op-…〕` 锚 / EVD-1171~1182 / DEC-244~248 / receipt 台账行 / closure 事件）与新增证据回滚不还原、不删除（数据是事实记录）；
4. **B-12 激活后的审计事实（引用——本版无激活）**：激活报告、break-glass grant/use 审计不可静默抹除——本版无激活动作，该条仅在未来授权票执行后适用（rollback-plan-0.88.0 §5 #4 同口径引用）；
5. **B-13 切换后的权威期写入（引用——本版无切换）**：JSON 权威期新增 DEC 行不经反向转换承载即回滚代码 = 数据分歧——本版无切换，该条仅在未来授权票执行后适用（rollback-plan-0.88.0 §5 #5 同口径引用）；
6. **防护/收益不可「部分回滚」的声明面**：FIX-391 零写拒绝面、FEAT-065 gate 闭集与真释放面、判据收敛三票均为版本级整体——回滚到 0.88.0 即同时失去（`GOVERNANCE_LEGACY_BEHAVIOR` 不承载该面——安全语义不回退不变量 + LEGACY_REVERTS 仅 performance 类；恢复安全与锁生命周期属安全语义）；**同文件串行面禁单票选择性还原**（closure_chain.py 承载 FIX-391+FEAT-065 两票——选择性还原产生半回退混合态）；
7. **审计信息损失**：区间内新增的审查报告（review-REL-090 系列 / review-FIX-390~395 系列 / review-FEAT-065 / review-REL-091）与本四件套随 revert 消失——如需保留审计痕迹，回滚前 MUST 归档副本（先例处置：`docs/release/audit-*.md` 类留档）；
8. **已发生的用户侧行为**：用户已按受控流程完成的中断遗留锁释放终态、已按机录路径完成的治理行写入无法事后重放为手工态——无状态副作用，仅记录事实。

## 6. 回滚触发条件

| # | 触发条件 | 判定 | 动作 |
|---|---|---|---|
| 1 | FIX-391 误拒合法链路（0.87 兼容矩阵承诺破面——正常 resume/finalize 被零写拒绝误伤活体复现） | 正常链路 resume/finalize 被拒 + 逐行归因到版本预检判据 | 回滚（整窗）+ FIX-391 复审后重发布；误拒期间被拒闭包按只读检查核对后恢复 |
| 2 | FEAT-065 四红线破约（误释放他者锁 / 释放后修改受锁文件 / 提交串行隔离破坏 / 同文件互斥放松——任一活体复现） | task_locks_released gate 误 PASS + 锁属主 diff 异常 | 立即回滚（整窗）+ FEAT-065 复审；已发生释放为事实记录（按 task+operation 标识核对） |
| 3 | FIX-393 误判复发（已交付票误推荐/误 blocked 活体回归——tpa 推荐面异常） | task-priority 推荐 diff 异常 + 逐行归因 | 回滚（整窗）+ FIX-393 复审后重发布 |
| 4 | FIX-394 刷新破坏行（终态行数据损坏/对齐回退——suffix_refresh 收据链与实际行不一致） | plan-tracker 行 diff 异常 + 收据对账 FAIL | 回滚（整窗）+ FIX-394 复审；13 行对齐结果按收据链核对修复 |
| 5 | FIX-390/392 判据回归（伪 FAIL 复活或真实缺陷漏报——census 身份集异常，专席①对账破面） | check-governance census 分段异常 + 逐行归因 | 回滚（整窗）+ FIX-390/392 复审后重发布；DEC-246③ 口径——修复揭露的真实缺陷按影响分级，不以此掩盖回滚义务 |
| 6 | FIX-395 热事实源误判回归（Check 28c 伪 FAIL 簇复活/热事实源误同步） | check-hot-fact-source diff 异常 | 回滚（整窗）+ FIX-395 复审后重发布 |
| 7 | 治理数据被异常修改或丢失（archive/plan-tracker 非预期变更） | `check-archive-integrity` FAIL 或数据 diff 异常 | 立即回滚 + 从备份恢复（FIX-384 index-rebuild 为在场修复工具——0.88 面保留，回滚后仍可用） |
| 8 | M-2/M-3 实测揭露出被伪像遮蔽的真实缺陷（DEC-246③——按影响分级） | 组合测试四项/专席任一 FAIL + 逐行归因 | 版本级缺陷走整窗回滚；局部缺陷走 M-4 修复窗（M-3 改可执行代码时原 M-2 证据不自动覆盖——退回验证） |

## 7. B-12/B-13 回退预案引用不触发专节（version-plan §7 口径——M-3 MUST 复核）

> 口径源：version-plan-0.89.0 §7「回退面」原文（B-12 回退预案与 B-13 反向转换方案已作为 0.88 rollback-plan 显式交付件——`docs/release/rollback-plan-0.88.0.md` §7 专节 + §8 双锚〔DESIGN-R0 F-3 勘正〕——**0.89 不触发**；激活授权票决策时按该预案 + RISK-059 前置执行）+ DEC-244（激活授权票不捆绑）+ DEC-246⑥（无新增功能激活措辞收紧）+ CHANGELOG 0.89.0 段行为变更节。

### 7.1 引用不触发总纲（本版无新激活面）

| 层 | B-12（write-guard 分族 BLOCK） | B-13（decision-log JSON 权威化） |
|---|---|---|
| **本版实际交付态（未激活——零回退需求）** | 出厂全 WARN 姿态 0.89 窗口**零触碰**（REL-091 24 文件面不含 posture 文件——REVIEW-REL-091 §2）；不激活即**零回退需求**；整窗 revert 即回 0.88.0 引擎（同姿态），无残留 | 缺省 `MD_ACTIVE` epoch 0 零足迹——0.89 **无真实切换**（五前置核验只核验不激活，M-0 已回填——version-plan §5）；`decision-log.md` 全程 md 权威字节；整窗 revert 即回 0.88.0 引擎（同权威态），无状态残留 |
| **回退预案（引用条目——不触发）** | 族级 flag 回 WARN：`governance-write-guard --deactivate-block <families>`（audited B-12 flag rollback）+ break-glass 通道（五限定+use 审计不可静默）——**rollback-plan-0.88.0 §7 专节原文承载** | 反向转换方案：`decision_migration.py rollback-begin` → `rollback-export`（含迁移后新增行全量反向导出）→ `rollback-activate`——**rollback-plan-0.88.0 §7 专节原文承载**（仅备份不算可回滚红线随引） |

### 7.2 触发边界与义务

- **触发条件 = 激活授权票执行**：B-12 翻转授权票 / B-13 切换授权票均为**独立决策、不捆绑 0.89 版本发布**（DEC-244 原文；行为变更需逐项明示授权）；前置 = 五前置闭环（DEC-238④×3 + DEC-239⑦×2——version-plan §5 核验结论：①②④⑤一致、③勘误行计数口径漂移 3≠11 如实登记，迁移阻断判定以 B-13 授权票演练引擎实测为准）+ 证明包审查（feat061-rehearsal-result.json 口径）+ RISK-059 处置；**授权票执行时按 rollback-plan-0.88.0 §7 预案 + §8 两路径区分执行，本文件不复制其命令面**（通道代码事实沿用 0.88 版实读锚——本版零改动，M-2/M-3 如需引用以当场实读复核为准）；
- **操作者告知义务**：M-3 审查与任何回滚/激活/切换执行前，本节与 rollback-plan-0.88.0 §7/§8 MUST 随回滚手册一并送达执行工位；激活/切换不得与版本发布动作捆绑静默执行（DEC-239② 防自锁语义延续）；
- **灰度开关正交**：`GOVERNANCE_LEGACY_BEHAVIOR` **不承载** B-12/B-13 回退，亦不承载本版行为修正三面回退——guard 执法、存储权威、恢复安全与锁生命周期属**安全语义**，不在 LEGACY_REVERTS 白名单（仅 performance 类）；不存在「legacy 模式下关闭零写拒绝/关闭真释放 gate/关执法」的中间态（feature-flags-0.89.0 §6 同口径）。

## 8. 回退路径区分：部署 v0.88.0 tag vs revert 12 commits 重建（REL-089 §8 先例形态——DEC-240③ 语义承袭）

**共同前提**：源码回退**不撤销数据写入**——0.89 已产生的持久状态工件原地保留（`.governance/` 治理数据与机录行 / 13 行对齐结果与 suffix_refresh 收据 / closure journal 0.89 期事件〔事件面与 0.88 兼容〕/ B-12/B-13 工件〔缺省缺席〕）。兼容性逐工件定性：治理数据与机录行 = 安全忽略面（0.88 引擎合法读取）；closure journal = 兼容（0.89 事件类型与 0.88 一致——EVD-1181；未知形态行按门禁处置）；B-12/B-13 工件 = 缺省缺席零触及。

**回退前通用步骤（0.89 仍在位时执行并留档）**：
1. 登记 in-flight closure 清单：检查 `.governance/closure-events.jsonl` 尾部 0.89 期事件——0.89 无新事件类型（如实注记；若发现未知形态行 = FIX-391 零写拒绝承诺破面，按 §6 #1 处置而非常规回退）；
2. `write-guard-bootstrap --check-only` 世界判定留档（converged 与否均留档）；
3. 确认 `.governance/.decision-store-state.json` 权威状态 = `MD_ACTIVE`（本版缺省必为 MD_ACTIVE；若非——发布窗内发生过切换〔授权票动作〕——先执行 B-13 反向转换并校验 md 完整性，否则**禁止回退**）；
4. 冻结写窗（停止一切治理写入）。

**路径 A——部署 v0.88.0 tag**（peel `33d19b0`）：
- 操作：以 v0.88.0 tag 安装/部署插件，`.governance/` 数据不动；
- 特性：0.88 代码**不可修补**——closure 语义防线只有运行手册门禁 + journal 兼容事实：0.89 期事件类型与 0.88 一致（忽略面读取合法）；**如出现未知形态 journal 行**（不应发生），出现 0.88 引擎响亮披露即停，经人工核对 journal 尾部后处置；恢复 0.89 后再对该闭包做终态操作；
- FIX-391 版本感知门禁随回退消失——闭包恢复误读防线回退为人工运行手册（0.88 rollback §8 手册仍有效）；
- FEAT-065 真释放面消失——标准链收口回到 shrink-locks TTL 收缩伪释放（0.88 已知态）；后继票可能再撞人工解锁步（如实预期）；
- 判据收敛面消失——tpa 误推荐/热事实源伪 FAIL 簇回归（0.88 已知态）；V3 键控伪像披露面复活（DEC-242③ 例外面）。

**路径 B——revert 12 commits 重建**（v0.88.0..M-1 tip，清单见 §区间锚定窗口构成事实）：
- 操作：按 commit 逆序 revert 全部 12 commits → 重建分支 → 安装重建产物，`.governance/` 数据不动；
- 特性：重建分支**可先行落防御性修复**——将 FIX-391（closure 版本感知读取器）backport 进重建分支后再切换（0.88 rollback §8 路径 B backport 候选先例——REL-089 条件③同源），closure 语义面由机检防护（仍建议保留路径 A 的运行手册门禁作为双保险）；
- 其余工件行为与路径 A 完全一致（同一 0.88 语义基线）。

**回退后验证（DEC-240③ 最低验证映射，两路径同集）**：
1. 启动：0.88 `verify_workflow.py` 全量 PASSED；
2. 读写：`governance-store decision-append` 直写 decision-log.md 成功（MD_ACTIVE 世界）；
3. 任务恢复：仅对 journal 无未知形态事件的 closure 执行 resume（0.89 期事件与 0.88 兼容——无 0.89-only 事件型，如实注记；含未知形态行者按门禁处置）；
4. 一致性：0.88 guard/check 面零意外 WARN（四类 0.89 工件在场不阻断任何 0.88 检查——治理数据忽略面读取合法）。

**恢复 forward（0.89 复装）**：全部治理数据/机录行/对齐结果原样恢复生效；closure journal 经 0.89 读取器全量可读（FIX-391 版本感知门禁复位）；标准链锁腿真释放复位（FEAT-065 复位——后继票收口不再撞人工解锁步）。

## 9. 0.90 候选池移交清单（回滚后的前进路径——与本版「不发布什么」对齐）

| # | 候选项 | 来源 | 状态 |
|---|---|---|---|
| 1 | **FEAT-066 acquire TTL 判定面**（治理存储层单一执法点：原子临界区〔读+过期判定+冲突判定+状态更新〕+ 过期锁 acquire 拒绝 + 返回过期项与受控回收指引——不自动接管；验收含 change_triage→acquire 全路径一致+旧持有者隔离测试） | DEC-248②（depends_on=FEAT-065——0.89 已交付，依赖满足） | 0.90 候选池已立票 |
| 2 | God Module 拆分 / 存储分离其余表 / task_status BLOCK 机录化 / FEAT-045 P-b / HotFactSource 版本字面量族 / GOVERNANCE_SESSION_ID 复核 / 量测边缘 + FIX-380 P2-1 | DEC-244 挂起清单 | 0.90+（version-plan §7） |
| 3 | review-record CLI --force 旗标 | RISK-047 / DEC-243④ 候选 | 候选未排期（如实登记） |
| 4 | B-12 翻转授权票 / B-13 切换授权票 | DEC-244 / RISK-059 + version-plan §5 五前置 | 独立授权票（不捆绑、不排期——五前置闭环 + 证明包审查后另行决策） |
| 5 | 18/18b live 窗口键控缺陷（P3-4）——若 M-2 专席④复测确认 live 面仍不激活 | EVD-1176 P3-4 | 后续票（M-2 结论承载） |
| 6 | census 申报可归因性改进（EVD 引用 census 计数附分段快照） | REVIEW-REL-091-RELEASE-R0 P3-2 | 申报纪律改进（随专席①执行落地） |

---
*REL-092 M-1R 草案冻结（2026-09-26，REL-092，Governance Developer Agent 起草）。事实基线：窗口起点 `33d19b0`（v0.88.0 peel，tag object `82905e6`，taggerdate 2026-09-25 20:08:32 +0800 权威——FIX-349）与 12 提交窗口取自 `git log`/`git rev-list`/`git describe`/`git rev-parse v0.88.0^{}`/`git for-each-ref` 实测；行为修正三面回退口径取自 CHANGELOG 0.89.0 段行为修正节原文 + version-plan-0.89.0 §7/§8；FEAT-065 锁面两文件与四红线/中断遗留锁受控流程取自 DEC-248 原文（decision-log 实读 UTF-8）；FIX-391 事件面兼容与兼容矩阵取自 EVD-1180 + CHANGELOG 行为修正②；journal 事件面不变取自 EVD-1181；B-12/B-13 引用不触发口径取自 version-plan §7 原文 + DEC-244 + rollback-plan-0.88.0 §7/§8 实读；路径 A/B 区分与最低验证映射承袭 REL-089 §8（DEC-240③ 语义）；0.88 期先例教训（0.81.0 F-04 / 0.84.0 P-5/P-9/P-12）沿用 0.88 版 rollback 实读。回滚演练未排程（如实标注）；`<发布 tip>` 属 M-5 期义务，本文件不预填。*
