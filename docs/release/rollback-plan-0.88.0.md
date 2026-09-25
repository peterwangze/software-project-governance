# Rollback Plan — 0.88.0（REL-086 M-1R / REL-088）

> **M-1R 草案（REL-088，2026-09-25）**——Governance Developer Agent 起草、供 Coordinator 审后随候选提交；结构与措辞对齐 `docs/release/rollback-plan-0.87.0.md` 先例（含 0.81.0 R0 F-01/F-04 区间教训）。**回滚演练本版未排程**（0.84.0 演练由 FIX-354 专项承载；0.85.0/0.86.0/0.87.0/0.88.0 批内无对应演练票——如实标注，见 §4 #10）；本草案正文不预填演练结果。**本版特有面**：**B-12/B-13 回退显式化专节（§7——F-11 义务，version-plan §3b 落字）**——B-12/B-13 均为「机制交付未激活」双层姿态，回退面简化为「不激活即零回退需求」+「激活后回退路径已交付」；B-13 反向转换方案为 C1⑦ 回退演练的**显式交付件**（非隐含承载）。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.88.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。回滚验证口径（如执行）全部在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）下进行，隔离验收不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；do not claim 1.0.0 production-ready。
- **B-12/B-13 未激活面不越权主张**：本版出厂全 WARN（B-12）/ 缺省 `MD_ACTIVE`（B-13）——本文件**不主张**任何 BLOCK 族已激活或 JSON 权威已生效；§7 双层表述的第一层（未激活）是本版实际交付态。
- **发布 tip 未生成前不预先编造**：本文件写作时点（M-1R，2026-09-25）0.88.0 的发布 tip（M-5 transition 提交）**尚不存在**——所有 `<发布 tip>` 占位由 M-5 生成后回填，绝不预先虚构 hash。

## 区间锚定（含先例教训注记、两段论证与本版窗口构成事实 —— MUST 先读）

**回滚区间（triage 锚定）= `602f8f3..<发布 tip>`**（回退点 = **`v0.87.0` tag**；`602f8f3` = tag peel = REL-084 M-5 transition 提交「0.87.0 transition candidate→released manifest-only」；tag object `2e5f715`，taggerdate 2026-09-21 14:02:27 +0800 实测——FIX-349 口径 taggerdate 权威；release-plan-0.88.0「回滚区间锚定」节同锚同源）：

- **论证①（下界 = `602f8f3`——本版候选面与完整窗口合一，无双轨分歧）**：git 区间语义 `X..Y` **排除下界自身**。0.88.0 与 0.86.0 期不同——24 票行为载荷（A14+B2+C1+D1+E6）+ M-0（REL-086）+ M-1 bump（REL-087）**全部落在 `602f8f3` 之后**（无 0.85.0 树内搭车批的 DEC-222 归属面），因此 triage 锚定 `602f8f3..<tip>` 同时就是完整行为回退区间：撤销即回到 `v0.87.0` 行为（peel `602f8f3`）。不存在「载荷保留、仅撤发布包装」的第二轨需求——0.86.0 期双轨在本版**合并为单轨**，M-3 审查只需复核单轨锚定与窗口计数。
- **论证②（终点 = `<发布 tip>`，非候选打包提交）**：0.81.0 先例 **F-04**——post-candidate 提交修改区间内新增 release 文档导致 revert 冲突（实测 3 处 UU；0.84.0 演练 P-12 反向实证 exit 1/CONFLICT）。终点 MUST 是 M-5 transition 提交（hash 由 M-5 生成后回填，不预编造）。

> **窗口构成事实（实测 2026-09-25，M-3 Release Reviewer 复核输入）**：`git rev-list --count 602f8f3..HEAD` = **29**（HEAD = `3fb42c0` FIX-385；`git describe` = v0.87.0-29-g3fb42c0 交叉印证）。29 提交 = 0.87.0 M-8 前版收尾（`fc69196`）+ M-0 三批（`266c32b`/`7d6ff6a`/`0233f49`）+ 24 票五阶段（A14：`3c3218d`/`44cb534`/`6845756`/`04b7a42`/`3d31c49`/`d6dd300`/`17e5663`/`0840876`/`9df2381`+`cdc3a0a`/`b3577c8`/`b7df86c`/`c349f8e`/`b03a0b4`/`ce93eb3`；B2：`c515776`/`0ff12f3`；C1：`61618a5`；D1：`a8afcbf`；E6：`14797be`/`6360ab1`/`467fb55`/`d68355f`/`d7b9add`/`3fb42c0`）；REL-087 M-1 bump 为工作树交付待提交——落库后区间随发布批延伸。区间计数不写死：M-5 现场以 `git rev-list --count 602f8f3..<发布 tip>` 取值记入 EVD。
>
> 1. **单轨 revert 程序**：`git revert --no-commit 602f8f3..<发布 tip>`——撤销 0.88.0 全部行为 diff（24 票 + M-0 + M-1 bump + M-1R 材料 + 后续发布批）；
> 2. **`git checkout v0.87.0` 替代锚（不等价，如实标注）**：落点 = peel `602f8f3`（transition 提交）——与 revert 的差异 = 不产生 revert 提交（历史保留 vs 撤销记录）、适合分支操作；代码/版本/行为面落点一致（0.84.0 演练 P-5 同款结论）；
> 3. **终点必须是发布 tip 而非候选打包提交**——post-candidate 提交会修改区间内新增的 release 文档导致 revert 冲突（0.81.0 先例 **F-04**；0.84.0 演练 P-12 反向实证）。

## 1. 本版改动的回滚影响分类

| 类别 | 本版内容 | 回滚影响 |
|---|---|---|
| **write-guard 分族 BLOCK（行为变更 B-12）⚠️ 双层回退面** | FEAT-064（`a8afcbf`）五族裁定（evidence/review/decision/ops_ledger 四族 BLOCK+task_status WARN 后置——DEC-239①）+ 出厂全 WARN 姿态 + BLOCK 写后执法 + break-glass 四件套 + FEAT-060 遗留三件；**机制交付未激活** | **第一层（未激活——本版实际交付态）**：不激活即零回退需求——缺省 `.write-guard-posture.json` 缺席 = 全 WARN = 零足迹，revert 该票即回到纯 WARN 引擎（FEAT-057 形态），无任何姿态残留。**第二层（发布窗已激活后）**：回退 = **族级 flag 回 WARN**——`governance-write-guard --deactivate-block <families>`（audited B-12 flag rollback——reason + authorized-by 必填留痕；`verify_workflow.py` L23916 实读）+ 恢复窗场景 `--break-grant` break-glass 通道（五限定=对象/操作者/理由/有效期/次数 + use 审计不可静默——**guard 自指场景同样适用不可静默**）；亦可整窗 revert（机制撤除）。**详见 §7 专节** |
| **decision-log JSON 权威化（行为变更 B-13）⚠️ 双层回退面** | FEAT-061（`61618a5`）六层落地：权威状态机/双后端路由/迁移编排/独立校验器；**机制交付未激活**——缺省 `.decision-store-state.json` 缺席 = `MD_ACTIVE` epoch 0 = 零足迹 | **第一层（未切换——本版实际交付态）**：不切换即零回退需求——缺省态零足迹，revert 该票即回到纯 md 权威引擎，无任何状态残留。**第二层（切换授权票执行后）**：回退 = **反向转换方案（显式交付件——非隐含承载）**：`decision_migration.py rollback-begin`（JSON_ACTIVE→ROLLBACK_FROZEN）→ `rollback-export`（当前 JSON 全量反向导出至 rollback-export.md——含**迁移后新增行**，仅备份不算可回滚）→ `rollback-activate`（ROLLBACK_FROZEN→MD_ACTIVE）——FEAT-061 已交付且真实 179 行演练 round_trip 已证字节回环；DEC-237 条款 01 权威恢复协议 + 07 回退兼容窗口承载。**详见 §7 专节** |
| **closure 取消/重开/接管（行为变更 B-14）** | FEAT-062（`14797be`）取消纵切 + FEAT-063（`d68355f`）重开 lineage + 执行代际 fencing——纯新增能力面，无删除 | **回退 = 纯新增能力消失**：无数据迁移、无删除面、外部 CLI 契约不变——revert 后取消/重开/接管入口消失；已登记的 cancellation op/closure_reopened 事件/fencing sidecar 为事实记录保留（0.87.0 引擎按忽略面读取合法）；无悬挂引用面 |
| **write-guard 基座（FEAT-060 + DEC-236）** | 违规持久状态机（12 字段 open/consumed/superseded）+ hook 消费权台账 + ops 可恢复消费事务（journal 三段 resume fail-closed）——WARN 姿态字节零变化 | 回退 = 状态机/台账机制撤除（`.governance/.write-guard-violations.json` 工件随代码回退不再被消费——健康宿主本就零足迹）；已登记违规记录（如 WV-62097f）为事实记录保留；guard 回到 FEAT-057 纯 WARN 路由（0.87.0 已知态） |
| **发版管线自举（FIX-383）** | release-window-bootstrap 内置链 + write-guard-bootstrap 子命令 + registry 收口 96→97 键 + contract-matrix 指令化再生 | 回退 = 自举链消失（发布操作回到手工序列）；CLI 分发面回落 96 键（archguard R5 冻结面随回滚回 96/96，回滚后 MUST archguard regen 对齐） |
| **writer 族退出码透传（FIX-375——DEC-230/231）⚠️ 门禁信号弱化面** | 引擎分发返回码透传（exit 0 假绿→exit 2；8 return-style handlers；无 SystemExit 桥接）+ schema_violation 结构化 + 恢复腿审计章 | 回退 = **exit 0 假绿缺陷复活**——门禁失败被静默吞掉（0.88.0 修复前的已知缺陷态）；无数据损坏面但治理信号弱化，如实列出 |
| **A 阶段修复票（FIX-373/374/376/377/379/380/382/386/387/388/389 + FIX-378）** | 切分器守卫/9-cell 消歧/static-pin 重锚/LRC ragged 清账/量测四项等 | 回退 = 各缺陷复活（EVD-248 误报回归 / fail-blind 回归 / static-pin 4 WARN 回归 / LRC 真实树扫描 BLOCKED 回归〔0.88 M-0 链 R0 形态〕等）——0.87.0 期末修复态回归，如实列出；无数据损坏面 |
| **M-0 规划票（REL-086）** | version-plan-0.88.0 + 双半面审查报告 + roadmap 0.88.0 行（`266c32b`/`7d6ff6a`/`0233f49`——文档/治理记录面） | 文档面随区间 revert 消失（审计信息——§5 #6）；治理记录面（机录 EVD/审查报告登记行）不回退（事实记录） |
| **M-1 bump 版本面（REL-087）** | 全仓 bump：SKILL frontmatter 权威锚 + 28 投影面 + CHANGELOG 0.88.0 段双位 + hooks 版本行 + 双根 entry bootstrap + REQUIRED_SNIPPETS 六锚 + static-pin 消解（工作树交付——revert 程序须先含其落库提交） | **随整窗 revert 完整撤销**——回滚后版本声明面回 0.87.0；`release-projection --write` 单次收敛能力随 FIX-366 系修复保留（0.87.0 已交付——回滚不回退到绕开手法） |
| **入口文件形态（工作区侧）** | repo-root `CLAUDE.md` / `AGENTS.md` 双根 entry bootstrap（M-1 已写盘） | **半自动回退项（MUST 手工收口）**：git revert 还原已跟踪入口文件与 canonical 模板，但用户工作区本地未跟踪入口投影 revert 不触碰 ⇒ 回滚后重跑 `sync_entry_projection.py --project <workspace> --source-root <plugin_root> --profile standard --primary CLAUDE.md --write`（幂等，双 apply 零 diff 既有测试锁定） |
| **治理数据面 + 新工件** | 本版 `.governance/` 记录（EVD-1134~1163、DEC-229~239、REL-086 链、guard 违规台账）+ 守卫工件（`.write-guard-state.json` 基线 / `.write-guard-violations.json` 台账 / `.write-guard-posture.json` 姿态配置）+ 存储工件（`.decision-store-state.json` / `decision-store.json` / 迁移演练工件 rollback-export.md） | **不进 git 窗口**（gitignored）——回滚零触碰；0.87.0 引擎读同一份治理数据合法（新增条目对旧引擎是忽略面）。工件语义：守卫工件为守卫自身状态（健康宿主零足迹）；`.decision-store-state.json` 缺席 = MD_ACTIVE 零足迹（本版缺省态）——**未切换时回滚零触及**；已切换场景见 §7 第二层 |
| **测试面** | 24 票测试载荷（切分器守卫/9-cell 双钉/状态机 24+3/closure 三形态/迁移 157+263/断点续迁 159P+286P 等） | 回滚后测试基线回到 0.87.0 期清单——计数下降是回滚的预期结果，不是回滚失败（§4 验证表如实注记） |
| **发布文档面** | 本四件套 + `core/releases/0.88.0.json`（待建） | 区间内新增文档——0.81.0 先例 **F-04** ⇒ **回滚 MUST 以完整区间表达到发布 tip**（终点同规）；审查报告（review-FIX-375~389 / review-FEAT-060~064 / review-REL-086 系列等）随 revert 消失——如需保留审计痕迹回滚前 MUST 归档副本（§5 #6） |
| **渲染/预设交付面** | DSH persona 版本行 / `adapters/dsh/AGENTS.md.template` / hook `@version` 行（M-1 bump 28 面内） | **回滚需重装预设**（0.87.0 同款）：回退后 MUST 重跑适配层安装/渲染（`python <plugin_root>/adapters/dsh/launch.py --sync`），否则宿主注入面仍是 0.88.0 文本而引擎为 0.87.0——版本不匹配混合态。DSH 侧回滚验证以隔离环境（环境变量重定向至临时目录）渲染 parity 为准 |
| **LRC 文本豁免账本（既有）** | `core/loop-runtime-claim-exemptions.json`（FIX-320 期承载——本版零改动；**与 B-11 Check 16/17 账本是两套机制**，如实区分） | 回滚对该账本零影响（条目维持）；但 Check 16/17 的 REQ-092/EVD-1146 披露面随引擎回退回到 0.87.0 形态（EVD-1146 行对旧引擎为忽略面读取合法） |

## 2. 回滚程序

### 2.1 插件侧（维护者）

```powershell
# 1) 记录当前状态（证据）
git -C <plugin_root> log --oneline -1
git -C <plugin_root> for-each-ref refs/tags/v0.88.0   # 期望 v0.88.0（已 tag 时；peel 应为 M-5 transition 提交）
python <plugin_root>/skills/software-project-governance/infra/verify_workflow.py check-version-consistency

# 1b) B-12/B-13 第一层确认（未激活/未切换 = 零回退需求——本版缺省态核验）
#     期望：.governance/.write-guard-posture.json 不存在（全 WARN 零足迹）
#           .governance/.decision-store-state.json 不存在（MD_ACTIVE 零足迹）
#     任一存在 ⇒ 先走 §7 对应第二层回退通道，再继续整窗 revert

# 2) 回退到本版之前的稳定点（单轨——区间 = 完整窗口 = 候选面合一）
#    区间 = 602f8f3..<发布 tip>（<发布 tip> = M-5 transition 提交，hash 由 M-5
#    生成后回填；本文件写作时点该提交不存在，不预填）：
#    ⚠️ 起点必须是 602f8f3（v0.87.0 peel）——29 提交行为载荷（含 M-1 bump 落库
#    提交）全部在该下界之后，漏任一即行为残留（含 B-12 管理面 / B-13 状态机 /
#    退出码透传 / closure 路径）。
git -C <plugin_root> revert --no-commit 602f8f3..<发布 tip>
#    区间计数不写死：M-5 现场以 `git rev-list --count 602f8f3..<发布 tip>` 取值记入 EVD
#    （M-1R 起草时点实测 = 29，M-1 bump 落库提交另计）。
#    替代锚【不等价】：直接切回稳定 tag（落点 = peel 602f8f3；无 revert 记录）
git -C <plugin_root> checkout v0.87.0

# 3) 入口投影重同步（MUST——本地未跟踪入口投影 revert 不覆盖；§1 载体行注记）
python <plugin_root>/skills/software-project-governance/infra/sync_entry_projection.py `
  --project <workspace> --source-root <plugin_root> --profile standard --primary CLAUDE.md --write

# 4) 重装适配层（本版触碰 DSH 模板/persona 版本行/hook 版本行 ⇒ 必做；隔离验证后再考虑后续动作）
python <plugin_root>/adapters/dsh/launch.py --sync

# 5) 回滚后守卫/存储工件核验（§4 #10/#11——健康宿主期望零足迹文件不再被生成）
```

### 2.2 用户侧（受影响用户）

1. `/plugin update`（或重装插件）回到 0.87.0——版本号回退后 marketplace 版本比对生效；
2. 重装/重渲染 agent 预设（DSH 宿主：`launch.py --sync`）使注入面与引擎版本一致；
3. 工作区入口文件（`CLAUDE.md` / `AGENTS.md`）恢复为 0.87.0 引导段——按 §2.1 步骤 3 重跑投影（幂等、可重复）；
4. `GOVERNANCE_LEGACY_BEHAVIOR` / `behavior_profile: legacy` 配置可保留（0.87.0 认识该变量，语义不变；如需洁净可移除）；
5. 用户数据无需任何动作（§3）；B-12/B-13 缺省零足迹态下无任何守卫/存储工件清理义务；已按机录路径写入的治理行合法保留（0.87.0 引擎按忽略面读取）。

### 2.3 发布前中止（M-0~M-4 窗口）

- 未 tag / 未 push 时中止：候选材料尚未提交 ⇒ 删弃工作树中未提交的四件套与 M-1 bump 面即可（本票已提交改动为零——四件套为本票全部写入面；M-1 bump 为工作树交付，中止 = 放弃其提交；`.governance/` 不受影响）；
- 已提交候选但未 tag：`git reset --hard 602f8f3`（整窗丢弃——本版无双轨场景之分）**执行前 MUST 确认无在途未推送载荷**（reset 属破坏性命令——现场执行属 Coordinator 破坏性 git 确认面，0.84.0 演练 P-9 同口径）；不影响已发布的 0.87.0（tag `v0.87.0` 与 `core/releases/0.87.0.json` 均不在本窗口内）；
- 已 tag 未 push：本地 `git tag -d v0.88.0` + 丢弃 transition 提交（**在 push 之前**；push 之后见 §5）。

## 3. 数据安全（回滚不损坏用户数据）

- **治理数据零风险**：`.governance/`（plan-tracker / evidence-log / decision-log / risk-log / archive / review-artifacts）**不在 git 窗口内**（gitignored），回滚不读不写不删；0.87.0 引擎读取同一份数据合法（新增条目/机录凭证标记对旧引擎是忽略面）；
- **B-12 工件零足迹（未激活态——本版缺省）**：`.write-guard-posture.json`（guard CLI `--activate-block` 独占写入）与 `.write-guard-violations.json`（违规台账）在健康宿主为零足迹或缺席——回滚零触及；已激活场景的回退通道见 §7 第二层（flag 回 WARN / break-glass——均 audited 不可静默）；
- **B-13 工件零足迹（未切换态——本版缺省）**：`.decision-store-state.json` 缺席 = `MD_ACTIVE` epoch 0 零足迹（`decision_repository.py` AUTHORITY_STATE_FILE 设计——缺省即初始世界）；`decision-log.md` 本版全程保持 md 权威字节（双后端路由 MD 零变化面）——回滚零触及；已切换场景回退 = `rollback-export` 全量反向导出（**覆盖迁移后新增行**）+ `rollback-activate`——见 §7 第二层；
- **机录凭证行**：已按机录路径写入的机器凭证行（`〔op-…〕` 锚 / EVD-1134~1163 / DEC-229~239 / receipt 台账 / guard 违规台账行）回滚后保留——0.87.0 引擎忽略面读取合法，无解析风险（task-row-update 字节保持设计——未触碰行零改写）；
- **closure 事件面（B-14）**：已登记的 cancellation op / closure_reopened 事件 / fencing sidecar 为事实记录——回滚后保留（纯新增能力的写入是追加事实，无删除面、无 schema 变更）；
- **工作区入口文件**：回滚重写 `CLAUDE.md` / `AGENTS.md` 的 Governance Bootstrap 段（canonical 模板投影，段替换语义）——段外内容零触碰（先例测试锁定：自定义尾段保留；双 apply 零 diff）；
- **不触碰用户配置目录**：本版回滚操作不写 `$HOME` 下任何配置目录、不写 `$DSH_HOME`；适配层重装按既有隔离约定（`$tmpHome` 临时目录重定向）验证；
- **不可逆数据处理**：本版无数据迁移执行、无 schema 变更执行、无治理文件格式变更执行（B-12/B-13 均机制交付未激活——激活/切换不在本版发布动作内）⇒ 无「回滚后数据不可读」风险；**若发布窗内已执行激活/切换**，其回退数据面由 §7 第二层通道承载（B-13 反向转换显式交付件——仅备份不算可回滚）。

## 4. 回滚后验证（MUST 全绿才算完成）

| # | 验证项 | 命令 | 期望（0.87.0 态） |
|---|---|---|---|
| 1 | 版本一致性 | `verify_workflow.py check-version-consistency` | PASSED，source = **0.87.0** |
| 2 | 投影同步 | `verify_workflow.py check-projection-sync --fail-on-issues` | PASSED（registry 28 面〔回退后合同面〕+ 入口双根，按 0.87.0 canonical 源） |
| 3 | 发布投影 | `verify_workflow.py release-projection` | PASS，`source_version = 0.87.0` |
| 4 | 全量资产 | `verify_workflow.py verify` | PASSED（0.87.0 期 snippet 面；新增面随回滚消失） |
| 5 | 入口投影形态 | 读 `AGENTS.md` / `CLAUDE.md` 引导段 | `@bootstrap-version: 0.87.0`（本地未跟踪入口由 §2.1 步骤 3 重同步） |
| 6 | 注入预算姿态 | `verify_workflow.py check-injection-budget --profile standard` | resident hard 三 profile 与 0.87.0 基线一致（4,216/5,694/5,966——版本 bump 不改 token 计数的对称面：回滚同样零漂移，如实实测注记） |
| 7 | 测试基线 | `pytest` / `verify` 计数 | 回到 0.87.0 期清单（计数下降 = 预期结果，如实注记——24 票测试面随回滚消失） |
| 8 | e2e | `verify_workflow.py e2e-check` | PASSED（fixture 随窗口回退自洽） |
| 9 | 治理健康 | `verify_workflow.py check-governance` | 与回滚后当场值一致（不预填数字；**Check 16/17 预期披露面回到 0.87.0 形态**——REQ-092 3 FAIL 维持 + EVD-1146 行对旧引擎为忽略面，如实归类非回滚失败） |
| 10 | **回滚演练** | 隔离副本执行 §2.1 `revert --no-commit` 干跑 | **未排程（如实标注）**——0.84.0 由 FIX-354 专项承载（隔离副本 `git clone --no-hardlinks` 法 + 零污染三重指纹先例）；0.85.0/0.86.0/0.87.0/0.88.0 批内无演练票。**建议**：M-3 审查裁决是否补演练；若补，MUST 隔离副本执行（就地执行污染候选索引）+ 真实 `<发布 tip>` 生成后复跑 |
| 11 | **B-12 后果核验** | `verify_workflow.py governance-write-guard --show-posture`（或读 `.governance/.write-guard-posture.json`） | **期望全 WARN / 姿态文件缺席**——0.87.0 已知态回归（无分族 BLOCK）；如发布窗曾激活，核验 `--deactivate-block` 已执行且报告留痕（不可静默面）；guard 回到 FEAT-057 纯 WARN 路由 |
| 12 | **B-13 后果核验** | 读 `.governance/.decision-store-state.json` + `decision_migration.py status` | **期望状态文件缺席（MD_ACTIVE 零足迹）**——0.87.0 已知态回归（md 权威）；如曾切换，核验 `rollback-export`（含迁移后新增行全量反向导出）+ `rollback-activate` 已执行、`decision-log.md` 字节回环与切换前快照一致（FEAT-061 演练同款验证） |

## 5. 不可回滚项（如实列出）

1. **已 push 的 `v0.88.0` tag**：tag 一旦推送即不可撤销——只能前进到 0.88.1（PATCH）修复，不得移动已推送 tag（VERSIONING.md 版本纪律）；
2. **`core/releases/0.88.0.json` 的 transition 事件**：作为发布事实一旦提交即不可「取消」；回滚只能通过新的发布记录表达（不得改写既有 manifest 事件）；
3. **已落账的机录凭证与事件日志**：`.governance/` 内 machine-provenance 行（`〔op-…〕` 锚 / EVD-1134~1163 / DEC-229~239 / receipt 台账 / guard 违规台账行 / closure cancellation/reopen 事件）与新增证据回滚不还原、不删除（数据是事实记录）；
4. **B-12 激活后的审计事实**：`--activate-block` 激活报告、break-glass grant/use 审计、BLOCK 期被阻塞面基线前像——激活事实与审计不可静默抹除；回退只改变姿态（flag 回 WARN / 机制撤除），不重写已发生审计；
5. **B-13 切换后的权威期写入**：JSON 权威期新增的 DEC 行不经反向转换承载即回滚代码 = 数据分歧（**仅备份不算可回滚**——DEC-237 条款 01/07 + version-plan §5 B-13 原文）；回退 MUST 走 `rollback-export`（全量反向导出含新增行）→ `rollback-activate`；
6. **防护/收益不可「部分回滚」的声明面**：B-12 执法面、B-13 存储面、B-14 closure 面、FIX-375 退出码透传均为版本级整体——回滚到 0.87.0 即同时失去（`GOVERNANCE_LEGACY_BEHAVIOR` 不承载该面——安全语义不回退不变量 + LEGACY_REVERTS 仅 performance 类）；
7. **审计信息损失**：区间内新增的审查报告（review-FIX-375~389 / review-FEAT-060~064 / review-REL-086 系列等）与本四件套随 revert 消失——如需保留审计痕迹，回滚前 MUST 归档副本（先例处置：`docs/release/audit-*.md` 类留档）；
8. **已发生的用户侧行为**：用户已按 closure 取消/重开完成的终态、已按机录路径完成的治理行写入无法事后重放为手工态——无状态副作用，仅记录事实。

## 6. 回滚触发条件

| # | 触发条件 | 判定 | 动作 |
|---|---|---|---|
| 1 | B-12 BLOCK 激活后误阻合法写入路径（覆盖率裁定缺陷——合法写路径被 BLOCK 面拦截且写入器补凭证闭环不可达） | 活跃 open 违规持续升级 + 写入器消费闭环失败 + 工作流被高频阻断 | **族级 flag 回 WARN**（`--deactivate-block`——audited；guard 自指场景用 `--break-grant` 恢复窗，不可静默）+ 覆盖率复审后重新裁定；机制级缺陷则整窗回滚 |
| 2 | B-12 执法面缺陷（被阻塞面基线前像丢失 / 消费事务致基线非预期推进——DEC-236① 语义被破坏） | 基线 diff 异常 + 消费事务对账 FAIL | 先 break-glass 恢复窗（限定留痕）止损 → 整窗回滚 + FEAT-060/064 复审 |
| 3 | B-13 切换后权威分歧（decision-log.md 投影与 JSON 权威不一致 / freshness 投影滞后阻断发布） | `decision_migration.py status` 投影滞后 + freshness gate 阻断 + DEC 记录级比对 FAIL | **反向转换回退**（§7 第二层：rollback-begin→rollback-export→rollback-activate）+ DEC-237 条款 06 投影恢复协议；切换授权票前置复审 |
| 4 | B-13 迁移编排缺陷（freeze 闭合条件失效 / epoch fencing 被绕过——R0 P0-F1 同型复发） | 状态机转移异常 + 竞窗数据丢失活体复现 | 立即 `cancel`/回退（ROLLBACK_FROZEN→MD_ACTIVE）+ 整窗回滚 + FEAT-061 复审 |
| 5 | FIX-375 退出码透传回归或误伤（合法路径被 exit 2 拒绝） | 对应面测试红 + 逐行归因 | 回滚（整窗）+ FIX-375 复审后重发布 |
| 6 | closure 路径数据风险（取消/接管误释放他者锁 / fencing 失效旧代际写入——ARCH-09 同型破坏） | 锁属主 diff 异常 + 旧代际写入活体复现 | 回滚（整窗）+ FEAT-062/063 复审；已发生终态为事实记录 |
| 7 | 治理数据被异常修改或丢失（archive/plan-tracker 非预期变更） | `check-archive-integrity` FAIL 或数据 diff 异常 | 立即回滚 + 从备份恢复（B-7a index-rebuild 为在场修复工具——回滚后消失，先重建再回滚） |
| 8 | 引擎收口修复回归（EVD-248 误报复现 / 9-cell fail-blind 复现 / static-pin 漂移复现 / LRC BLOCKED 复现） | 对应面测试红 + 逐行归因 | 回滚（整窗）+ 对应票复审后重发布 |

## 7. B-12/B-13 回退显式化专节（F-11 义务——version-plan §3b 落字；M-3 MUST 复核）

> 口径源：version-plan-0.88.0 §3b「回滚锚定原则」原文（B-12 族级 flag 回 WARN 经 D1 break-glass 通道；B-13 反向转换方案为 C1⑦ 回退演练的显式交付件）+ CHANGELOG 0.88.0 段行为变更节 B-12/B-13 回退通道原文 + `verify_workflow.py` L23908-23917 / `write_guard_state.py` L1610-1699 / `decision_repository.py` L37-67 / `decision_migration.py` L1009-1048 实读 + EVD-1155/1156。

### 7.1 双层表述总纲（本版 B-12/B-13 均「机制交付未激活」）

| 层 | B-12（write-guard 分族 BLOCK） | B-13（decision-log JSON 权威化） |
|---|---|---|
| **第一层：未激活（本版实际交付态）** | 不激活即**零回退需求**——出厂全 WARN（`.write-guard-posture.json` 缺席 = 零足迹；DEC-239②「机制交付/真实翻转分离——翻转经 `--activate-block` 由 Coordinator 于发布窗裁决执行」）；整窗 revert 即回 FEAT-057 纯 WARN 引擎，无姿态残留 | 不切换即**零回退需求**——缺省 `MD_ACTIVE` epoch 0 零足迹（`.decision-store-state.json` 缺席 = 初始世界；DEC-238②）；`decision-log.md` 全程 md 权威字节；整窗 revert 即回纯 md 权威引擎，无状态残留 |
| **第二层：激活/切换后** | 回退 = **族级 flag 回 WARN**：`governance-write-guard --deactivate-block <families>`（audited B-12 flag rollback——reason + authorized-by 必填，报告留痕不可静默）；恢复窗场景 = `--break-grant` break-glass 通道（五限定=对象/操作者/理由/有效期/次数 + use 审计不可静默——**guard 自指场景同样适用不可静默**：守卫对自身工件 `.write-guard-state.json`/`.write-guard-violations.json`/`.write-guard-posture.json` 的写入同样受通道约束，无免检豁免）；机制级缺陷走整窗 revert（第一层通道仍可用——激活是运行时姿态非代码前提） | 回退 = **反向转换方案（显式交付件）**：`decision_migration.py rollback-begin`（JSON_ACTIVE→ROLLBACK_FROZEN）→ `rollback-export`（当前 JSON 全量反向导出至迁移目录 rollback-export.md——**MUST 覆盖迁移后新增行**；仅切换前快照备份不算可回滚）→ `rollback-activate`（ROLLBACK_FROZEN→MD_ACTIVE）；切回后 md 为权威、JSON 退位；**FEAT-061 真实 179 行演练 round_trip 已证字节回环**（EVD-1155——独立性三规则活体实证）；切换前快照 + 冻结窗完整性双向摘要复核（DEC-237 条款 02/03）为切换授权票前置义务 |

### 7.2 通道细节与依据

- **B-12 通道代码事实**：`governance-write-guard` 管理 CLI 六动作 = `--activate-block` / `--deactivate-block` / `--show-posture` / `--break-grant` / `--break-clear` / `--break-show`（`verify_workflow.py` L25869-25893 + `write_guard_state.py` L1668-1699 实读）；`--deactivate-block` 被引擎注释明确定为「**the audited B-12 flag rollback**（reason + authorized-by demanded）」（L23916-23917）——即 version-plan §3b「族级 flag 回 WARN」的承载命令；break-glass 为**临时恢复窗**（限定 BLOCK issues 降级为响亮 WARN 披露——不改姿态文件），两通道互补：日常回退走 deactivate，紧急止损走 break-grant；
- **B-12 不可静默红线**：break-glass 五限定 + 每次 CLI 运行 use 审计事件（L23913-23915）——「guard 自指场景 break-glass 同样适用不可静默」（version-plan §3b 原文）；无 BLOCK 不授予（DEC-239④）；
- **B-13 通道代码事实**：迁移 CLI 全子命令面 = freeze / shadow / verify / activate / rollback-begin / rollback-export / rollback-activate / cancel / status / project-repair / proof-pack（`decision_migration.py` argparse L1009-1048 实读）；回退三段 = rollback-begin → rollback-export → rollback-activate；权威状态机含 ROLLBACK_FROZEN 态与 `(ROLLBACK_FROZEN, MD_ACTIVE)` 转移（`decision_repository.py` L151-163）——回退是状态机一等公民非补丁；
- **B-13「仅备份不算可回滚」红线**：version-plan §5 B-13 原文 + DEC-237 条款 01（权威恢复协议——推荐从当前 JSON 全量导出而非初始 md 重放）+ 条款 07（回退兼容窗口内写入须可逆表达）；切换授权票 MUST 携带「回退演练覆盖迁移后新增行」证明（version-plan §3 条 3 证明包门）；
- **B-14 简注**：closure 取消/重开/接管为纯新增能力无删除面——回退 = 能力消失 + 事件事实保留，无专用通道需求（§1/§3 已载）；
- **灰度开关正交**：`GOVERNANCE_LEGACY_BEHAVIOR` **不承载** B-12/B-13 回退——guard 执法与存储权威属安全语义/治理行为，不在 LEGACY_REVERTS 白名单（仅 performance 类）；不存在「legacy 模式下关闭 BLOCK 或回退权威」的中间态（feature-flags-0.88.0 §6 同口径）；
- **操作者告知义务**：M-3 审查与任何回滚/激活/切换执行前，本节 MUST 随回滚手册一并送达执行工位；B-12 激活与 B-13 切换均为授权票动作（DEC-239② / RISK-059+DEC-238④+DEC-239⑦），不得与版本发布动作捆绑静默执行。

## 8. 回退路径区分：部署 v0.87.0 tag vs revert 29 commits 重建（REL-089 · DEC-240③）

**共同前提**：源码回退**不撤销数据写入**——0.88 已产生的持久状态工件原地保留（`.write-guard-state.json` / `.write-guard-violations.json` / `.write-guard-posture.json` / `closure-events.jsonl` 0.88 事件 / `closure-generations.json` / `archive/.migration/` / `.decision-migration/` / `.decision-store-state.json`）。兼容性逐工件定性见 `docs/release/rel-089-m3-precondition-report.md` §③：五件安全忽略/兼容，closure journal 部分兼容（读 fail-safe、语义有界不兼容）。

**回退前通用步骤（0.88 仍在位时执行并留档）**：
1. 登记 in-flight closure 清单：检查 `.governance/closure-events.jsonl` 尾部是否含 0.88-only 事件类型（`closure_cancelled` / `closure_reopened` / `closure_fenced`）——含任一者的 closure 进入「0.88 事件闭包」清单；
2. `write-guard-bootstrap --check-only` 世界判定留档（converged 与否均留档）；
3. 确认 `.governance/.decision-store-state.json` 权威状态 = `MD_ACTIVE`（本版缺省必为 MD_ACTIVE；若非——0.88 期间发生过切换——先执行 B-13 反向转换并校验 md 完整性，否则**禁止回退**）；
4. 冻结写窗（停止一切治理写入）。

**路径 A——部署 v0.87.0 tag**（peel `602f8f3`）：
- 操作：以 v0.87.0 tag 安装/部署插件，`.governance/` 数据不动；
- 特性：0.87 代码**不可修补**——closure 语义防线只有运行手册门禁：**回退后禁止 resume/finalize 任何「0.88 事件闭包」清单中的 closure**（0.87 会响亮披露 `unknown closure event_type` problems——出现该披露即停，经人工核对 journal 尾部后处置；恢复 0.88 后再对该闭包做终态操作）；
- 0.87 下 guard face-5 首跑按 amnesty 对存量行重建基线（0.88 增量键 `updated_at` 被 0.87 容忍读取，首次 0.87 收敛写回 3 键形状——字节面随写收敛，无破坏）；
- 违规台账/姿态配置/fencing sidecar/续迁游标被 0.87 忽略（不破坏、不可见）。

**路径 B——revert 29 commits 重建**（v0.87.0..M-1 tip，清单见 CHANGELOG 0.88.0「Commit 区间」）：
- 操作：按 commit 逆序 revert 全部 29 commits → 重建分支 → 安装重建产物，`.governance/` 数据不动；
- 特性：重建分支**可先行落防御性修复**——按 legacy_snapshot_backport 政策（FIX-381 先例）将 FIX-391（closure 版本感知读取器）backport 进重建分支后再切换，closure 语义面由机检防护（仍建议保留路径 A 的运行手册门禁作为双保险）；
- 其余工件行为与路径 A 完全一致（同一 0.87 语义基线）。

**回退后验证（DEC-240③ 最低验证映射，两路径同集）**：
1. 启动：0.87 `verify_workflow.py` 全量 PASSED；
2. 读写：`governance-store decision-append` 直写 decision-log.md 成功（MD_ACTIVE 世界）；
3. 任务恢复：仅对 journal 无 0.88 事件的 closure 执行 resume；含 0.88 事件者按门禁处置；
4. 一致性：0.87 guard face-5 重建基线零意外 WARN（amnesty）；四类 0.88 工件在场不阻断任何 0.87 检查（REL-089 测试基座佐证）。

**恢复 forward（0.88 复装）**：五件被忽略工件原样恢复生效（posture/violations/fencing/续迁游标零丢失）；closure journal 经 0.88 读取器全量可读（0.88 认识全部事件类型）。

---

## 9. 0.89 候选池移交清单（回滚后的前进路径——与本版「不发布什么」对齐）

| # | 候选项 | 来源 | 状态 |
|---|---|---|---|
| 1 | **write-guard task_status 族 BLOCK**（合法手工面机录化后再 BLOCK）+ 其余行族扩展 | DEC-239① / version-plan §6 | 0.89 面清单登记 |
| 2 | **B-12 真实翻转**（基线登记→`--activate-block`——发布窗授权动作） | DEC-239② | 授权票待发（本版机制交付） |
| 3 | **B-13 真实切换授权票**（DEC-238④ 三缺口 RISK-059 + F-5①③ 组合测试 + R1 N-1~N-5 清扫 + 证明包审查） | DEC-238④/DEC-239⑦/RISK-059 | 授权票待发（本版机制交付） |
| 4 | **存储分离其余表**（evidence-log 等——首表模式验证后推广）+ 主文件大拆解 | version-plan §6 | 候选（0.89+） |
| 5 | **GOVERNANCE_SESSION_ID 接线复核**（FEAT-064 已交付接线——DEC-236③ 0.89 BLOCK 前验收复核） | DEC-236③ | 候选 |
| 6 | **量测协议边缘观察后续面** | version-plan §6 | 候选 |
| 7 | FIX-380 P2-1 双源互检断言（FIX-381 遗留） | review-FIX-380-R0 | 留后续 |
| 8 | **FIX-390**：Check 18/18b 改读结构化状态（basis 列+机器凭证 marker 纳入判定——0.88 例外 2×2 FAIL 的消解票；验收含 committed/✅/未知三态回归+两行红→绿活体+豁免面差分归因） | REL-089 条件② / DEC-240② | 0.89 候选 |
| 9 | **FIX-391**：closure journal 版本感知读取器（0.87 语义误读向量消除——路径 B backport 候选） | REL-089 条件③ | 0.89 候选 |

---
*REL-088 M-1R 草案冻结（2026-09-25，REL-088，Governance Developer Agent 起草）。事实基线：窗口起点 `602f8f3`（v0.87.0 peel，taggerdate 2026-09-21 14:02:27 +0800 权威——FIX-349）与 29 提交窗口取自 `git log`/`git rev-list`/`git describe`/`git rev-parse v0.87.0^{}`/`git for-each-ref` 实测；B-12/B-13/B-14 回退口径取自 version-plan-0.88.0 §3b/§5 + CHANGELOG 0.88.0 段行为变更节原文；B-12 通道面取自 `verify_workflow.py` L23908-23917/L25869-25893 + `write_guard_state.py` L1610-1699/L301 实读；B-13 通道面取自 `decision_repository.py` L37-67/L131/L151-163 + `decision_migration.py` L1009-1048 实读；B-13 演练字节回环与切换前置取自 CHANGELOG 披露④ + DEC-237/238（decision-log 实读）+ RISK-059（risk-log 实读）+ EVD-1155；单轨/终点/演练口径对齐 rollback-plan-0.87.0 先例（0.81.0 F-04 / 0.84.0 P-12 教训沿用）。回滚演练未排程（如实标注）；`<发布 tip>` 属 M-5 期义务，本文件不预填。*
