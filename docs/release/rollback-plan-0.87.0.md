# Rollback Plan — 0.87.0（REL-084 M-1R / REL-085）

> **M-1R 草案（REL-085，2026-09-21）**——Governance Developer Agent 起草、供 Coordinator 审后随候选提交；结构与措辞对齐 `docs/release/rollback-plan-0.86.0.md` 先例（含 0.81.0 R0 F-01/F-04 区间教训）。**回滚演练本版未排程**（0.84.0 演练由 FIX-354 专项承载；0.85.0/0.86.0/0.87.0 批内无对应演练票——如实标注，见 §4 #10）；本草案正文不预填演练结果。**本版特有面**：FIX-366 回退风险披露专节（§7——两遍 plan 撤回 = 绕开手法复活）。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.87.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。回滚验证口径（如执行）全部在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）下进行，隔离验收不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；do not claim 1.0.0 production-ready。
- **发布 tip 未生成前不预先编造**：本文件写作时点（M-1R，2026-09-21）0.87.0 的发布 tip（M-5 transition 提交）**尚不存在**——所有 `<发布 tip>` 占位由 M-5 生成后回填，绝不预先虚构 hash。

## 区间锚定（含先例教训注记、两段论证与本版窗口构成事实 —— MUST 先读）

**回滚区间（triage 锚定）= `6e25753..<发布 tip>`**（`6e25753` = `v0.86.0` tag peel = REL-082 M-5 transition 提交；release-plan-0.87.0「回滚区间锚定」节同锚同源）：

- **论证①（下界 = `6e25753`——本版候选面与完整窗口合一，无双轨分歧）**：git 区间语义 `X..Y` **排除下界自身**。0.87.0 与 0.86.0 期不同——九票行为载荷（批 1 四票 + M-0 + 批 2 三票 + FIX-371）与 M-1 bump **全部落在 `6e25753` 之后**（无 0.85.0 树内搭车批的 DEC-222 归属面），因此 triage 锚定 `6e25753..<tip>` 同时就是完整行为回退区间：撤销即回到 `v0.86.0` 行为（peel `6e25753`）。不存在「载荷保留、仅撤发布包装」的第二轨需求——0.86.0 期双轨（轨道 A 整窗/轨道 B 候选面）在本版**合并为单轨**，M-3 审查只需复核单轨锚定与窗口计数。
- **论证②（终点 = `<发布 tip>`，非候选打包提交）**：0.81.0 先例 **F-04**——post-candidate 提交修改区间内新增 release 文档导致 revert 冲突（实测 3 处 UU；0.84.0 演练 P-12 反向实证 exit 1/CONFLICT）。终点 MUST 是 M-5 transition 提交（hash 由 M-5 生成后回填，不预编造）。

> **窗口构成事实（实测 2026-09-21，M-3 Release Reviewer 复核输入）**：`git rev-list --count 6e25753..HEAD` = **9**（M-1 候选 `80d71b5` 已含；`git describe` = v0.86.0-9-g80d71b5 交叉印证）。九提交（新→旧）：`80d71b5` FEAT-059（M-1 bump+CHANGELOG）→ `a6d3bfb` FIX-371（豁免账本）→ `dd4537b` FIX-370（locks-release）→ `aa72c37` FIX-372（evidence 列约定）→ `2ab3847` FIX-366（两遍 plan+CRLF）→ `80069a2` REL-084（M-0 规划）→ `9aa27a6` FIX-364（午夜窗）→ `a7f89ac` FIX-369（B-9 重定标）→ `5e56021` FIX-368（列偏移）。FIX-367 为治理记录票（机录 op-98c0f7f6，`.governance/` gitignored——零 commit 面，不占窗口计数）。区间计数不写死：M-5 现场以 `git rev-list --count 6e25753..<发布 tip>` 取值记入 EVD（候选提交后随发布批增长）。
>
> 1. **单轨 revert 程序**：`git revert --no-commit 6e25753..<发布 tip>`——撤销 0.87.0 全部行为 diff（九票 + M-1 bump + M-1R 材料 + 后续发布批）；
> 2. **`git checkout v0.86.0` 替代锚（不等价，如实标注）**：落点 = peel `6e25753`（transition 提交）——与 revert 的差异 = 不产生 revert 提交（历史保留 vs 撤销记录）、适合分支操作；代码/版本/行为面落点一致（0.84.0 演练 P-5 同款结论）；
> 3. **终点必须是发布 tip 而非候选打包提交**——post-candidate 提交会修改区间内新增的 release 文档导致 revert 冲突（0.81.0 先例 **F-04**；0.84.0 演练 P-12 反向实证）。

## 1. 本版改动的回滚影响分类

| 类别 | 本版内容 | 回滚影响 |
|---|---|---|
| **Check 31 语义预算（行为变更 B-9）⚠️ 单行回退面** | max_semantic_units 300,000→**361,923 = ceil(301,602×1.2)**（FIX-369；重定标非豁免；provenance 注释 `loop_runtime_claims.py` L225-242 + 公式钉值/反豁免 fail-closed 双测试；基线经 FEAT-047 baseline-register 登记） | **回退 = 单行还原 361,923→300,000 + 基线注销**（数据级、可执行、双向自洽——CHANGELOG B-9 原文）。⚠️ **回滚后 LRC 必然 BLOCKED 回归**：活数据 2026-09-20 当日已实测 301,602 units > 300,000（0.86.0 期已知披露 #16/⑨）——回滚即回到 SEMANTIC_BUDGET_EXCEEDED fail-closed 态，`check-loop-runtime-claims` 不可用直至重新重定标（MUST 走同公式 + baseline-register）。回退无 Gate 结构/判定语义变更（L11 显式处置面） |
| **locks-release 释放语义（行为变更 B-10）** | governance_store 锁清理 governed 化——task 锚定真删除（active_tasks + file_locks + ops 台账登记）+ 先登记后删除 + released_files 审计章 + 三态/幂等 fail-closed；96 键 CLI 分发面重定基线（FIX-370；shrink-locks 保留语义不变） | **回退 = 代码回退承载**（locks-release 命令面移除；CLI 分发面回落 95 键——archguard R5 冻结面随回滚回 95/95，回滚后 MUST archguard regen 对齐）。⚠️ **已释放的锁不随回滚恢复**（真删除已发生——ops 台账登记为事实记录）；过期锁重新悬挂（Check 26 形态回归）；需要时经 acquire 幂等重取重建锁条目（不触任务数据） |
| **Check 16/17 历史豁免账本（行为变更 B-11）** | ✅ 终态历史行（2026-09-20 前存量）豁免 + 新增行零豁免全严检 + 三消费方留痕（Check 16/17/18 取数 wrapper——DEC-228①）+ 主运行面 26=8+18 对账（FIX-371；DEC-227 路线 b） | **回退 = 代码回退承载**（verify_workflow.py +144 行账本机制撤除 + test_verify_workflow.py +149 行测试面消失）。⚠️ **回滚后 Check 16/17 FAIL 计数回升至 0.86.0 已知形态**（列偏移误 FAIL 随 FIX-368 一并回归 + 历史行无豁免）——如实预期非回滚失败。账本数据级通道（DEC-226 非-T2 裁定「账本可增删可回滚」）仅适用于机制在场时的条目增删，机制级回退只能版本级 |
| **projection 两遍 plan（FIX-366）⚠️ 特有回退风险** | byte_copy source = 同批 transformed target 耦合 → 内存 resolve 一次收敛；CRLF 连带根因修复（read_bytes().decode）；4 测试含 CRLF 护栏双断言——0.86.0 披露③ 技术债清偿 | **回退 = 缺陷复活：两遍 plan 撤回 = 绕开手法复活**——版本 bump 操作必须重新启用 FEAT-053/058 同款绕开手法（canonical 标记先达目标值→transformed 幂等→再生 byte_copy），否则 bump 必回滚（fail-closed 无静默腐坏）。**详见 §7 专节** |
| **CRLF 保真（FIX-366 连带）** | transformed target 保留原生换行（替代 read_text 隐式转换） | 回滚随 FIX-366 恢复旧隐式转换行为（transformed 面换行归一化回归——投影字节面 diff，无数据损坏面；护栏测试随回滚消失） |
| **引擎收口修复三票（FIX-368/364/372）** | 列偏移修复（EVD-1118 误 FAIL 消除）/ 午夜窗时间敏感修复 / evidence 列约定统一三处 | 回退 = 三缺陷复活（Check 16/17 误 FAIL / 午夜窗时间敏感 / Check 20 fail-open）——0.86.0 已知缺陷态回归，如实列出；无数据损坏面 |
| **热事实源回填（FIX-367）** | roadmap 0.86.0 行 / 0.85.0 勘正 / 总览 0.86.0（机录 op-98c0f7f6） | **不进 git 窗口**（`.governance/` gitignored）——revert 零触碰；回填的事实记录保留（0.86.0 引擎按忽略面读取） |
| **M-0 规划票（REL-084）** | version-plan-0.87.0 + 双半面审查报告 + roadmap 0.87.0 行（`80069a2`——文档/治理记录面） | 文档面随区间 revert 消失（审计信息——§5 #6）；治理记录面（机录 EVD/审查报告登记行）不回退（事实记录） |
| **M-1 bump 版本面** | 24 tracked：SKILL frontmatter + 28 投影面 + CHANGELOG 段 + hooks 版本行 + canonical 标记 + 双根 entry bootstrap + REQUIRED_SNIPPETS 六锚（`80d71b5`） | **随整窗 revert 完整撤销**——回滚后版本声明面回 0.86.0；`release-projection --write` 回滚后不可单次收敛（§7——须绕开手法） |
| **入口文件形态（工作区侧）** | repo-root `CLAUDE.md` / `AGENTS.md` 双根 entry bootstrap（M-1 已写盘） | **半自动回退项（MUST 手工收口）**：git revert 还原已跟踪入口文件与 canonical 模板，但用户工作区本地未跟踪入口投影 revert 不触碰 ⇒ 回滚后重跑 `sync_entry_projection.py --project <workspace> --source-root <plugin_root> --profile standard --primary CLAUDE.md --write`（幂等，双 apply 零 diff 既有测试锁定） |
| **治理数据面** | 本版 `.governance/` 记录（EVD-1122~1129、DEC-226~228 机录行、REL-084 链、locks-release ops 台账登记行） | **不进 git 窗口**（gitignored）——回滚零触碰；0.86.0 引擎读同一份治理数据合法（新增条目对旧引擎是忽略面）；已按 locks-release 释放的锁不恢复（删除是事实）；回滚不还原已写入的新证据（数据是事实记录，非版本产物） |
| **测试面** | 七票测试载荷（列偏移回归 3 / 午夜窗双钉 / 公式钉值+反豁免双测试 / CRLF 护栏双断言 / evidence 列 / locks-release 三态 / 豁免账本 +149 行） | 回滚后测试基线回到 0.86.0 期清单——计数下降是回滚的预期结果，不是回滚失败（§4 验证表 #7 如实注记） |
| **发布文档面** | 本四件套 + `core/releases/0.87.0.json`（待建） | 区间内新增文档——0.81.0 先例 **F-04** ⇒ **回滚 MUST 以完整区间表达到发布 tip**（终点同规）；审查报告（review-REL-084-* / review-FIX-371-CODE-R0 174 行 / review-FEAT-059-RELEASE-R0 103 行）随 revert 消失——如需保留审计痕迹回滚前 MUST 归档副本（§5 #6） |
| **渲染/预设交付面** | DSH persona 版本行 / `adapters/dsh/AGENTS.md.template` / hook `@version` 行（M-1 bump 28 面内） | **回滚需重装预设**（0.86.0 同款）：回退后 MUST 重跑适配层安装/渲染（`python <plugin_root>/adapters/dsh/launch.py --sync`），否则宿主注入面仍是 0.87.0 文本而引擎为 0.86.0——版本不匹配混合态。DSH 侧回滚验证以隔离环境（环境变量重定向至临时目录）渲染 parity 为准 |
| **LRC 文本豁免账本（既有）** | `core/loop-runtime-claim-exemptions.json` 4 条（FIX-320 期承载——本版零改动；**注意与 FIX-371 的 Check 16/17 账本是两套机制**，如实区分） | 回滚对该账本零影响（4 条维持）；但 FIX-371 账本机制回退（上行） |

## 2. 回滚程序

### 2.1 插件侧（维护者）

```powershell
# 1) 记录当前状态（证据）
git -C <plugin_root> log --oneline -1
git -C <plugin_root> for-each-ref refs/tags/v0.87.0   # 期望 v0.87.0（已 tag 时；peel 应为 M-5 transition 提交）
python <plugin_root>/skills/software-project-governance/infra/verify_workflow.py check-version-consistency

# 2) 回退到本版之前的稳定点（单轨——区间 = 完整窗口 = 候选面合一）
#    区间 = 6e25753..<发布 tip>（<发布 tip> = M-5 transition 提交，hash 由 M-5
#    生成后回填；本文件写作时点该提交不存在，不预填）：
#    ⚠️ 起点必须是 6e25753（v0.86.0 peel）——九提交行为载荷全部在该下界之后，
#    漏任一即行为残留（含 B-9 常量行 / FIX-371 账本 / locks-release 键面）。
git -C <plugin_root> revert --no-commit 6e25753..<发布 tip>
#    区间计数不写死：M-5 现场以 `git rev-list --count 6e25753..<发布 tip>` 取值记入 EVD
#    （M-1R 起草时点实测 = 9，M-1 候选已含）。
#    替代锚【不等价】：直接切回稳定 tag（落点 = peel 6e25753；无 revert 记录）
git -C <plugin_root> checkout v0.86.0

# 3) 入口投影重同步（MUST——本地未跟踪入口投影 revert 不覆盖；§1 载体行注记）
python <plugin_root>/skills/software-project-governance/infra/sync_entry_projection.py `
  --project <workspace> --source-root <plugin_root> --profile standard --primary CLAUDE.md --write

# 4) 重装适配层（本版触碰 DSH 模板/persona 版本行/hook 版本行 ⇒ 必做；隔离验证后再考虑后续动作）
python <plugin_root>/adapters/dsh/launch.py --sync

# 5) B-9 数据级回退确认（revert 已含常量行还原——此处仅核验双向自洽）
#    期望：ScanLimits().max_semantic_units == 300000 且 LRC 回到 0.86.0 已知 BLOCKED 态（§4 #11）
```

### 2.2 用户侧（受影响用户）

1. `/plugin update`（或重装插件）回到 0.86.0——版本号回退后 marketplace 版本比对生效；
2. 重装/重渲染 agent 预设（DSH 宿主：`launch.py --sync`）使注入面与引擎版本一致；
3. 工作区入口文件（`CLAUDE.md` / `AGENTS.md`）恢复为 0.86.0 引导段——按 §2.1 步骤 3 重跑投影（幂等、可重复）；
4. `GOVERNANCE_LEGACY_BEHAVIOR` / `behavior_profile: legacy` 配置可保留（0.86.0 认识该变量，语义不变；如需洁净可移除）；
5. 用户数据无需任何动作（§3）；已按机录路径写入的治理行（含 FIX-370 ops 台账 locks-release 登记行）合法保留（0.86.0 引擎按忽略面读取）；已释放的锁需要时 acquire 幂等重取。

### 2.3 发布前中止（M-0~M-4 窗口）

- 未 tag / 未 push 时中止：候选材料尚未提交 ⇒ 删弃工作树中未提交的四件套即可（本票已提交改动为零——四件套为本票全部写入面；`.governance/` 不受影响）；
- 已提交候选但未 tag：`git reset --hard 6e25753`（整窗丢弃——本版无双轨场景之分）**执行前 MUST 确认无在途未推送载荷**（reset 属破坏性命令——现场执行属 Coordinator 破坏性 git 确认面，0.84.0 演练 P-9 同口径）；不影响已发布的 0.86.0（tag `v0.86.0` 与 `core/releases/0.86.0.json` 均不在本窗口内）；
- 已 tag 未 push：本地 `git tag -d v0.87.0` + 丢弃 transition 提交（**在 push 之前**；push 之后见 §5）。

## 3. 数据安全（回滚不损坏用户数据）

- **治理数据零风险**：`.governance/`（plan-tracker / evidence-log / decision-log / risk-log / archive / review-artifacts）**不在 git 窗口内**（gitignored），回滚不读不写不删；0.86.0 引擎读取同一份数据合法（新增条目/机录凭证标记对旧引擎是忽略面）；
- **机录凭证行**：已按机录路径写入的机器凭证行（`〔op-…〕` 锚 / receipt 台账 / governance-store 标记 / FIX-370 ops 台账 locks-release 登记行）回滚后保留——0.86.0 引擎忽略面读取合法，无解析风险（task-row-update 字节保持设计——未触碰行零改写）；
- **锁条目处置**：已按 locks-release 真删除的锁不随回滚恢复（删除是事实记录）——需要时经 acquire 幂等重取重建，不触任务数据；回滚不产生悬挂引用（released_files 审计章随代码回退，台账行保留可审计）；
- **B-11 账本回退无数据面**：豁免账本为 verify_workflow.py 代码内机制（非独立数据文件）——代码回退零数据删除；历史治理行本身（EVD/审查报告行）零触碰；
- **工作区入口文件**：回滚重写 `CLAUDE.md` / `AGENTS.md` 的 Governance Bootstrap 段（canonical 模板投影，段替换语义）——段外内容零触碰（先例测试锁定：自定义尾段保留；双 apply 零 diff）；
- **不触碰用户配置目录**：本版回滚操作不写 `$HOME` 下任何配置目录、不写 `$DSH_HOME`；适配层重装按既有隔离约定（`$tmpHome` 临时目录重定向）验证；
- **不可逆数据处理**：本版无数据迁移、无 schema 变更、无治理文件格式变更（B-9 为引擎常量 / B-10 为新增命令 / B-11 为代码内账本机制）⇒ 无「回滚后数据不可读」风险。

## 4. 回滚后验证（MUST 全绿才算完成）

| # | 验证项 | 命令 | 期望（0.86.0 态） |
|---|---|---|---|
| 1 | 版本一致性 | `verify_workflow.py check-version-consistency` | PASSED，source = **0.86.0** |
| 2 | 投影同步 | `verify_workflow.py check-projection-sync --fail-on-issues` | PASSED（registry 28 面〔回退后合同面〕+ 入口双根，按 0.86.0 canonical 源） |
| 3 | 发布投影 | `verify_workflow.py release-projection` | PASS，`source_version = 0.86.0` |
| 4 | 全量资产 | `verify_workflow.py verify` | PASSED（0.86.0 期 snippet 面；新增面随回滚消失） |
| 5 | 入口投影形态 | 读 `AGENTS.md` / `CLAUDE.md` 引导段 | `@bootstrap-version: 0.86.0`（本地未跟踪入口由 §2.1 步骤 3 重同步） |
| 6 | 注入预算姿态 | `verify_workflow.py check-injection-budget --profile standard` | resident hard 三 profile 与 0.86.0 基线一致（4,216/5,694/5,966——版本 bump 不改 token 计数的对称面：回滚同样零漂移，如实实测注记） |
| 7 | 测试基线 | `pytest` / `verify` 计数 | 回到 0.86.0 期清单（计数下降 = 预期结果，如实注记——七票测试面 + FIX-371 账本 149 行测试随回滚消失） |
| 8 | e2e | `verify_workflow.py e2e-check` | PASSED（fixture 随窗口回退自洽） |
| 9 | 治理健康 | `verify_workflow.py check-governance` | 与回滚后当场值一致（不预填数字；**Check 16/17 预期 FAIL 计数回升**——B-11 账本机制回退 + FIX-368 列偏移回归的 0.86.0 已知态，如实归类非回滚失败） |
| 10 | **回滚演练** | 隔离副本执行 §2.1 `revert --no-commit` 干跑 | **未排程（如实标注）**——0.84.0 由 FIX-354 专项承载（隔离副本 `git clone --no-hardlinks` 法 + 零污染三重指纹，rollback-plan-0.84.0 §演练记录先例）；0.85.0/0.86.0/0.87.0 批内无演练票。**建议**：M-3 审查裁决是否补演练；若补，MUST 隔离副本执行（就地执行污染候选索引）+ 真实 `<发布 tip>` 生成后复跑 |
| 11 | **B-9 回退后果核验** | `verify_workflow.py check-loop-runtime-claims` | **期望 BLOCKED（SEMANTIC_BUDGET_EXCEEDED）——0.86.0 已知态回归**（300,000 < 活数据实测 301,602）：如实归类为「回滚预期后果」非回滚失败；恢复路径 = 重新重定标（MUST 同公式 ceil(实测峰值×1.2) + baseline-register，反豁免 fail-closed） |

## 5. 不可回滚项（如实列出）

1. **已 push 的 `v0.87.0` tag**：tag 一旦推送即不可撤销——只能前进到 0.87.1（PATCH）修复，不得移动已推送 tag（VERSIONING.md 版本纪律）；
2. **`core/releases/0.87.0.json` 的 transition 事件**：作为发布事实一旦提交即不可「取消」；回滚只能通过新的发布记录表达（不得改写既有 manifest 事件）；
3. **已落账的机录凭证与事件日志**：`.governance/` 内 machine-provenance 行（`〔op-…〕` 锚 / EVD-1122~1129 / DEC-226~228 / receipt 台账 / locks-release ops 台账登记行）与新增证据回滚不还原、不删除（数据是事实记录）；
4. **已按 locks-release 真删除的锁条目**：删除动作已发生且台账留痕——回滚不恢复锁条目（acquire 幂等重取为唯一重建路径）；
5. **防护/收益不可「部分回滚」的声明面**：B-9 容量余量、B-10 释放路径、B-11 历史豁免、FIX-366 正道投影均为版本级整体——回滚到 0.86.0 即同时失去（`GOVERNANCE_LEGACY_BEHAVIOR` 不承载该面——安全语义不回退不变量 + LEGACY_REVERTS 仅 performance 类）；
6. **审计信息损失**：区间内新增的审查报告（`docs/reviews/review-REL-084-DESIGN-R0/R1`、`review-REL-084-RELEASE-R0`、`review-FIX-371-CODE-R0` 174 行、`review-FEAT-059-RELEASE-R0` 103 行等）与本四件套随 revert 消失——如需保留审计痕迹，回滚前 MUST 归档副本（先例处置：`docs/release/audit-*.md` 类留档）；
7. **已发生的用户侧行为**：用户已按 locks-release 释放的锁、已按机录路径完成的治理行写入无法事后重放为手工态——无状态副作用，仅记录事实。

## 6. 回滚触发条件

| # | 触发条件 | 判定 | 动作 |
|---|---|---|---|
| 1 | B-9 重定标被证伪（361,923 容量下 LRC 出现非容量类 claim 违规漏检——公式推导缺陷） | LRC findings 含真实违规但门禁 PASS | 立即回滚（整窗）+ 重定标公式复审后重发布（反豁免 fail-closed 测试在场——复核其边界覆盖） |
| 2 | locks-release 释放语义缺陷（误删活跃锁 / 台账登记与实际删除不一致） | active_tasks/file_locks diff 异常 + ops 台账对账 FAIL + released_files 审计章核对 | 立即回滚（整窗）+ 受影响锁 acquire 幂等重取重建；M-3 复审 FIX-370 遗留面（FIX-375 出槽 0.88 在案） |
| 3 | B-11 账本误豁免（活跃/新增行被豁免——「新增行零豁免」红线破约） | Check 16/17 exempted 清单含 2026-09-20 后新增行 | 先核对是否真实历史行（日期界定）；确认破约 ⇒ 回滚 + DEC-227 红线复审 |
| 4 | 投影正道失效（FIX-366 修复在真实 bump 场景外复现回滚震荡/静默丢失） | `release-projection` check 与 declared 面逐字节对照 FAIL | 回滚（整窗）+ 回到绕开手法操作面（§7）+ FIX-366 复审 |
| 5 | 治理数据被异常修改或丢失（archive/plan-tracker 非预期变更） | `check-archive-integrity` FAIL 或数据 diff 异常 | 立即回滚 + 从备份恢复 |
| 6 | 投影/入口漂移无法收敛（`check-projection-sync` 双根 apply 后仍 FAIL） | 连续两次 apply 后仍 FAIL | 回滚后重做投影 |
| 7 | 引擎收口修复回归（Check 16/17 误 FAIL 复现 / 午夜窗失败复现 / Check 20 fail-open 复现） | 对应面测试红 + 逐行归因 | 回滚（整窗）+ 对应票复审后重发布 |

## 7. FIX-366 回退风险披露专节（两遍 plan 撤回 = 绕开手法复活——本版特有面，M-3 MUST 复核）

> 口径源：CHANGELOG 0.87.0 段「projection 两遍 plan 正道化（FIX-366）」+ 0.86.0 rollback-plan §8 移交清单 #1（FIX-366 P1 优先推荐）+ review-FEAT-058 F-2 落票链 + EVD-1125。

- **缺陷本体**：`release/projection.py` 单遍 plan——当 byte_copy 源 = 同批 transformed 目标时必回滚（fail-closed 无静默腐坏——不会产出错误内容，但 bump 操作无法单次收敛）。
- **0.87.0 修复**：内存 resolve 一次收敛（`2ab3847`）——本版 M-1（FEAT-059）为**首次正道交付**：单次 `release-projection --write` 28 面一次收敛零回滚震荡，FEAT-053/058 两版绕开手法（canonical 标记先达目标值→transformed 幂等→再生 byte_copy）撤除。
- **回退含义（如实披露）**：整窗 revert 将本修复一并撤销 ⇒ **绕开手法复活为回滚后版本 bump 的唯一可行操作法**——(a) 回滚后任何版本声明面操作（如补丁版 bump）MUST 按 FEAT-053/058 手册化步骤执行，否则 bump 必回滚；(b) 0.86.0 期披露③ 的技术债状态整体回归（含其对 M-1 操作复杂度与出错面的代价）；(c) 无数据损坏面（fail-closed——缺陷形态是「拒绝收敛」非「静默错写」），但操作面回退到易错手工序列。
- **CRLF 连带**：回退同时恢复 `read_text` 隐式换行转换旧行为——transformed 面原生 CRLF 保真消失（护栏双断言测试随回滚消失，防回归网一并失去）。
- **操作者告知义务**：M-3 审查与任何回滚执行前，本节 MUST 随回滚手册一并送达执行工位；绕开手法步骤以 0.86.0 期 FEAT-058 M-1 实操记录为先例参照（其 CHANGELOG 版本投影段有原文）。

## 8. 0.88 候选池移交清单（回滚后的前进路径——与本版「不发布什么」对齐）

| # | 候选项 | 来源 | 状态 |
|---|---|---|---|
| 1 | **FIX-373** 切分器状态泄漏（EVD-248 单条噪声——FIX-372 审查 F-4 双向影响：format check fail-noisy + Check 20 fail-blind；验收纳入双向影响评估与 Check 20 形状回归 fixture） | FIX-372 审查落票 | **triage 在案（0.88+）**——P2 优先推荐 |
| 2 | **FIX-374** 9-cell 豁免消歧 | FIX-371 审查链 | triage 在案（0.88+） |
| 3 | **FIX-375**（FIX-370 遗留面） | FIX-370 交付登记 | triage 在案（0.88+） |
| 4 | **FIX-376** | plan-tracker REL-084 状态行出槽注记 | triage 在案（0.88+） |
| 5 | write-guard WARN→BLOCK 升级（DEC-224 双约束：不得 WARN-once-then-absorb + hook 窗口消费权台账化） | DEC-224 / DEC-226 出槽清单 | 0.88 面清单登记 |
| 6 | 存储分离 JSON 化（首表 decision-log）/ closure 铺开（取消/重开/异常接管）/ FEAT-044 回合心跳 + FEAT-045 并行段识别 / B-7 index-rebuild + 大表迁移 + 发版管线自举 | DEC-226 出槽清单（version-plan-0.87.0 §6） | 候选 |
| 7 | 量测边缘观察 4 项（journal detail 透传 / triage-id 词表对齐 / conflict 退出码语义统一 / pre-probe 语义注记） | 0.86.0 M-2 首跑移交——0.87 未处置 | **继续挂账**——Coordinator triage |

---
*REL-085 M-1R 草案冻结（2026-09-21，REL-085，Governance Developer Agent 起草）。事实基线：窗口起点 `6e25753`（v0.86.0 peel，taggerdate 2026-09-20 16:15:13 +0800）与 9 提交窗口取自 `git log`/`git rev-list`/`git describe`/`git rev-parse v0.86.0^{commit}` 实测（`6e25753..80d71b5` = 9，M-1 候选已含）；B-9/B-10/B-11/CRLF 回退口径取自 CHANGELOG 0.87.0 段（`80d71b5` 冻结版）行为变更节原文；B-9 公式与 provenance 取自 `loop_runtime_claims.py` L225-243 实读；FIX-371 账本实现形态取自 `a6d3bfb` commit stat 实读；FIX-366 缺陷本体与绕开手法口径取自 0.86.0 期披露③ + CHANGELOG 0.87.0 段；0.88 候选池取自 CHANGELOG 披露③⑥ + DEC-226 出槽清单。回滚演练未排程（如实标注）；`<发布 tip>` 属 M-5 期义务，本文件不预填。*
