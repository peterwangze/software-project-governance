# Rollback Plan — 0.86.0（REL-082 M-1R / REL-083）

> **M-1R 草案（REL-083，2026-09-20）**——Governance Developer Agent 起草、供 Coordinator 审后随候选提交；结构与措辞对齐 `docs/release/rollback-plan-0.85.0.md` 先例（含 0.81.0 R0 F-01/F-04 区间教训）。**回滚演练本版未执行**（0.84.0 演练由 FIX-354 专项承载；0.85.0/0.86.0 批内无对应演练票——如实标注，见 §4 #10）；本草案正文不预填演练结果。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.86.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。回滚验证口径（如执行）全部在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）下进行，隔离验收不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；do not claim 1.0.0 production-ready。
- **发布 tip 未生成前不预先编造**：本文件写作时点（M-1R，2026-09-20）0.86.0 的发布 tip（M-5 transition 提交）**尚不存在**——所有 `<发布 tip>` 占位由 M-5 生成后回填，绝不预先虚构 hash。

## 区间锚定（含先例教训注记、两段论证与本版窗口构成事实 —— MUST 先读）

**回滚区间（triage 锚定，候选面）= `ffcb787..<发布 tip>`；禁用 `44831b8..<发布 tip>`**（release-plan-0.86.0「回滚区间锚定」节同锚同源）：

- **论证①（下界 = `ffcb787`，禁 `44831b8`）**：git 区间语义 `X..Y` **排除下界自身**。`44831b8` = FEAT-058 M-1 bump——版本声明面 0.85.0→0.86.0 的 26 文件 diff（SKILL frontmatter 权威源 / 28 投影面 / CHANGELOG 段 / 豁免账本 11 行 / hooks 版本行 / canonical 标记）——**M-1 bump 属候选面**，必须完整落在撤销集内。误写 `44831b8..<tip>` 则 bump diff 残留 ⇒ 回滚后版本声明面 0.86.0 / 行为载荷面回退 = **版本-载荷不一致混合态**（0.81.0 R0 **F-01** 同形失效模式）。`ffcb787`（FEAT-057 批 2.3——批 2 全清点）作为下界把 M-1 bump 完整纳入。
- **论证②（终点 = `<发布 tip>`，非候选打包提交）**：0.81.0 先例 **F-04**——post-candidate 提交修改区间内新增 release 文档导致 revert 冲突（实测 3 处 UU；0.84.0 演练 P-12 反向实证 exit 1/CONFLICT）。终点 MUST 是 M-5 transition 提交（hash 由 M-5 生成后回填，不预编造）。

> **⚠️ 本版窗口构成事实（M-3 Release Reviewer MUST 复核并裁决双轨适用场景）**：0.86.0 完整 git 窗口 = **`c2cc7c1..<发布 tip>`**（`c2cc7c1` = `v0.85.0` tag peel = REL-081 M-5 transition 提交；`c2cc7c1..44831b8` 实测 **5 提交**：`a5dec3d` FEAT-055 → `a7474e4` FIX-365 → `7709987` FEAT-056 → `ffcb787` FEAT-057 → `44831b8` M-1 bump——批 2 全部行为载荷 + bump；批 0/1 四提交随 `v0.85.0` 树入库，DEC-222 归属裁定）。由此：
>
> 1. **双轨区间如实分述**：**轨道 A（整窗行为回退）= `c2cc7c1..<发布 tip>` revert**——撤销 0.86.0 全部行为 diff（批 2 四提交 + M-1 bump + M-1R 材料 + 后续发布批），回到 `v0.85.0` 行为（0.85.0 先例「区间锚定」节整窗口径的 0.86.0 同型）；**轨道 B（候选面撤销，triage 锚定）= `ffcb787..<发布 tip>` revert**——仅撤销 M-1 bump 与 M-1R/发布材料，批 2 行为载荷保留在树。**两轨不等价**：轨道 B 后的树 = 批 2 功能在场但版本声明面回 0.85.0（适用于「载荷保留、仅撤发布包装」的场景）；完整回退到 0.85.0 行为 MUST 走轨道 A。任务简报所引「ffcb787..<tip>」为轨道 B 锚定——本文件按指令锚定登记，同时如实披露轨道 A 为完整行为回退的唯一区间，M-3 裁决适用场景；
> 2. **`git checkout v0.85.0` 替代锚（不等价，如实标注）**：落点 = peel `c2cc7c1`（transition 提交）——与轨道 A revert 的差异 = 不产生 revert 提交（历史保留 vs 撤销记录）、适合分支操作；代码/版本/行为面落点一致（0.84.0 演练 P-5 同款结论）；
> 3. **终点必须是发布 tip 而非候选打包提交**——post-candidate 提交会修改区间内新增的 release 文档导致 revert 冲突（0.81.0 先例 **F-04**；0.84.0 演练 P-12 反向实证）。

## 1. 本版改动的回滚影响分类

| 类别 | 本版内容 | 回滚影响 |
|---|---|---|
| **治理行写入路径（行为变更 B-3）⚠️ 主载荷** | 受管行族机录优先 + write-guard 面 5 行族对账执法（WARN 姿态上线路由——响亮+可指引+exit 0 不阻断；FEAT-051/046/057） | **回退=版本级回滚（B-3 无 flag 级降级——CHANGELOG 已声明）**：回退后 write-guard 行族对账面消失，手工直写回到无守卫 0.85.0 态（机录 CLI 仍在树——轨道 B 下 7 键写入器保留可用；轨道 A 整窗 revert 后写入器 CLI 亦回退，0.85.0 无此面）。**既有手工路径本版仍可用（非破坏收敛）**——回滚不破坏任何已按机录路径写入的治理行（数据是事实记录） |
| **closure-chain 语义（行为变更 B-4）** | CLI 步超时分类学 step_unknown + effect-based resume 世界核验门控（互斥双腿 landed=reconcile / NOT-landed=重执行+replay 兜底；FEAT-056） | **回退=版本级回滚**：回退后 CLI 步超时回退笼统失败——恢复可靠性弱化（如实列出，不隐瞒）；B-4 为链内部语义不改变既有 CLI 对外退出码契约，回退无接口破坏 |
| **四类原子写入器 CLI + 7 键接线** | task-row-update / locks-extend / locks-amend / evidence-append / decision-append / baseline-register / baseline-evaluate（批 1 三票 + FEAT-055 接线；冻结面 88→95） | 轨道 B 保留（写入器面在批 2.0 `a5dec3d`，位于 `ffcb787` 之前）；**轨道 A 整窗 revert 后消失**——0.85.0 无治理写入器 CLI，治理行写入回到纯手工 + 无对账态（已知代价；0.85.0 期同口径） |
| **M0 契约基座** | contracts.py 五面契约冻结 m0-r1 + 99 存量契约测试（批 0——随 v0.85.0 树入库，零消费） | 位于窗口外（v0.85.0 树内）——**双轨 revert 均不触碰**；回滚后契约测试仍在但消费面随批 1/2 回退而缩减（测试计数下降 = 回滚预期结果，§4 #7 注记） |
| **混沌发布门** | test_closure_chain 35（三边界 kill+resume 零人工修复——隔离 bare 夹具；FEAT-056） | 轨道 A 回退后该门消失——0.87 轨道需重排（M-2 MUST 门回退为规划面）；轨道 B 保留 |
| **write-guard 执法面** | 面 5 受管行族对账 + WARN 路由 + 状态基线 `.write-guard-state.json`（amnesty——存量不追溯；FEAT-057） | 轨道 A 回退后执法面消失——**8 次手工事故防护回到「能力无执法」态**（见 §手工事故披露链）；状态基线文件属守卫工件非治理记录，随回滚失义（无数据损坏） |
| **M-1 bump 版本面** | 24 tracked：SKILL frontmatter + 28 投影面 + CHANGELOG 段 + 豁免账本 11 行 + hooks 版本行 + canonical 标记（`44831b8`） | **轨道 A/B 均完整撤销（triage 锚定义务）**——回滚后版本声明面回 0.85.0；豁免账本随文件回退恢复 0.85.0 期 10 行 dormant 形态，双向自洽（账本 token 匹配 active_version 才生效） |
| **入口文件形态（工作区侧）** | repo-root `CLAUDE.md`（full 9,552B）/ `AGENTS.md`（thin 2,834B）+ fixture 双入口（M-1 已写盘） | **半自动回退项（MUST 手工收口）**：git revert 还原已跟踪入口文件与 canonical 模板，但用户工作区本地未跟踪入口投影 revert 不触碰 ⇒ 回滚后重跑 `sync_entry_projection.py --project <workspace> --source-root <plugin_root> --profile standard --primary CLAUDE.md --write`（幂等，双 apply 零 diff 既有测试锁定） |
| **治理数据面** | 本版 `.governance/` 记录（EVD-1102~1119、REL-082/083 链、机录 DEC/EVD 行） | **不进 git 窗口**（gitignored）——回滚零触碰；0.85.0 引擎读同一份治理数据合法（新增条目对旧引擎是忽略面）；回滚不还原已写入的新证据（数据是事实记录，非版本产物）。**closure 量测工件在 `%TEMP%` sandbox 副本——真实治理数据零触碰（SHA256 三重一致证明）** |
| **测试面** | 批 1/2 写入器/closure/write-guard 测试（40+76+64+30+35+115P 等）+ 契约测试 58 | 轨道 A 回退后测试基线回到 0.85.0 期清单——计数下降是回滚的预期结果，不是回滚失败（§4 验证表 #7 如实注记） |
| **发布文档面** | 本四件套 + `core/releases/0.86.0.json`（待建） | 区间内新增文档——0.81.0 先例 **F-04** ⇒ **回滚 MUST 以完整区间表达到发布 tip**（轨道 A/B 终点同规）；量测 sandbox 工件不入仓库零影响 |
| **渲染/预设交付面** | DSH persona 版本行 / `adapters/dsh/AGENTS.md.template` / hook `@version` 行（M-1 bump 28 面内） | **回滚需重装预设**（0.85.0 同款）：回退后 MUST 重跑适配层安装/渲染（`python <plugin_root>/adapters/dsh/launch.py --sync`），否则宿主注入面仍是 0.86.0 文本而引擎为 0.85.0——版本不匹配混合态。DSH 侧回滚验证以隔离环境（环境变量重定向至临时目录）渲染 parity 为准 |
| **豁免账本/既有开关** | LRC 豁免 4 条与 0.85.0 既有开关零触碰 | 回滚对 LRC 账本与既有开关零影响 |

## 2. 回滚程序

### 2.1 插件侧（维护者）

```powershell
# 1) 记录当前状态（证据）
git -C <plugin_root> log --oneline -1
git -C <plugin_root> for-each-ref refs/tags/v0.86.0   # 期望 v0.86.0（已 tag 时；peel 应为 M-5 transition 提交）
python <plugin_root>/skills/software-project-governance/infra/verify_workflow.py check-version-consistency

# 2) 回退到本版之前的稳定点（按场景二选一/二选二）
#    (a) 轨道 A【完整行为回退——推荐主轨】：区间 = **整个 0.86.0 窗口
#        `c2cc7c1..<发布 tip>`**（<发布 tip> = M-5 transition 提交，hash 由 M-5
#        生成后回填；本文件写作时点该提交不存在，不预填）：
#        ⚠️ 起点必须是 c2cc7c1（v0.85.0 peel）——批 2 行为载荷 a5dec3d/a7474e4/
#        7709987/ffcb787 全在该下界之后，漏任一即行为残留。
git -C <plugin_root> revert --no-commit c2cc7c1..<发布 tip>
#        区间计数不写死：M-5 现场以 `git rev-list --count c2cc7c1..<发布 tip>` 取值记入 EVD。
#    (b) 轨道 B【候选面撤销——triage 锚定 `ffcb787..<发布 tip>`】：仅撤 M-1 bump
#        与 M-1R/发布材料，保留批 2 行为载荷（场景裁决见「区间锚定」披露 1）：
git -C <plugin_root> revert --no-commit ffcb787..<发布 tip>
#    (c) 替代锚【不等价】：直接切回稳定 tag（落点 = peel c2cc7c1；无 revert 记录）
git -C <plugin_root> checkout v0.85.0

# 3) 入口投影重同步（MUST——本地未跟踪入口投影 revert 不覆盖；§1 载体行注记）
python <plugin_root>/skills/software-project-governance/infra/sync_entry_projection.py `
  --project <workspace> --source-root <plugin_root> --profile standard --primary CLAUDE.md --write

# 4) 重装适配层（本版触碰 DSH 模板/persona 版本行/hook 版本行 ⇒ 必做；隔离验证后再考虑后续动作）
python <plugin_root>/adapters/dsh/launch.py --sync
```

### 2.2 用户侧（受影响用户）

1. `/plugin update`（或重装插件）回到 0.85.0——版本号回退后 marketplace 版本比对生效；
2. 重装/重渲染 agent 预设（DSH 宿主：`launch.py --sync`）使注入面与引擎版本一致；
3. 工作区入口文件（`CLAUDE.md` / `AGENTS.md`）恢复为 0.85.0 引导段——按 §2.1 步骤 3 重跑投影（幂等、可重复）；
4. `GOVERNANCE_LEGACY_BEHAVIOR` / `behavior_profile: legacy` 配置可保留（0.85.0 认识该变量，语义不变；如需洁净可移除）；
5. 用户数据无需任何动作（§3）；已按 B-3 机录路径写入的治理行合法保留（0.85.0 引擎按忽略面读取）。

### 2.3 发布前中止（M-0~M-4 窗口）

- 未 tag / 未 push 时中止：候选材料尚未提交 ⇒ 删弃工作树中未提交的四件套即可（本票已提交改动为零——四件套为本票全部写入面；`.governance/` 不受影响）；
- 已提交候选但未 tag：`git reset --hard ffcb787`（轨道 B 场景——保批 2 载荷、撤 bump+候选）或 `git reset --hard c2cc7c1`（轨道 A 场景——整窗丢弃）**按场景选择，执行前 MUST 确认场景语义**；不影响已发布的 0.85.0（tag `v0.85.0` 与 `core/releases/0.85.0.json` 均不在本窗口内；reset 属破坏性命令——执行前 MUST 确认无在途未推送载荷，0.84.0 演练 P-9 同口径推演成立、现场执行属 Coordinator 破坏性 git 确认面）；
- 已 tag 未 push：本地 `git tag -d v0.86.0` + 丢弃 transition 提交（**在 push 之前**；push 之后见 §5）。

## 3. 数据安全（回滚不损坏用户数据）

- **治理数据零风险**：`.governance/`（plan-tracker / evidence-log / decision-log / risk-log / archive / review-artifacts）**不在 git 窗口内**（gitignored），回滚不读不写不删；0.85.0 引擎读取同一份数据合法（新增条目/机录凭证标记对旧引擎是忽略面）；**closure 量测全程在 `%TEMP%` sandbox 副本执行——真实治理数据零写入（SHA256 三重一致证明）**；
- **机录凭证行**：已按 B-3 写入的机器凭证行（`〔op-…〕` 锚 / receipt 台账 / governance-store 标记）回滚后保留——0.85.0 引擎忽略面读取合法，无解析风险（task-row-update 字节保持设计——未触碰行零改写）；
- **工作区入口文件**：回滚重写 `CLAUDE.md` / `AGENTS.md` 的 Governance Bootstrap 段（canonical 模板投影，段替换语义）——段外内容零触碰（先例测试锁定：自定义尾段保留；双 apply 零 diff）；
- **不触碰用户配置目录**：本版回滚操作不写 `$HOME` 下任何配置目录、不写 `$DSH_HOME`；适配层重装按既有隔离约定（`$tmpHome` 临时目录重定向）验证；
- **不可逆数据处理**：本版无数据迁移、无 schema 变更、无文件格式变更（M0 契约基座为纯新增基座，批 0 随 v0.85.0 树入库已存在）⇒ 无「回滚后数据不可读」风险。

## 4. 回滚后验证（MUST 全绿才算完成）

| # | 验证项 | 命令 | 期望（0.85.0 态） |
|---|---|---|---|
| 1 | 版本一致性 | `verify_workflow.py check-version-consistency` | PASSED，source = **0.85.0** |
| 2 | 投影同步 | `verify_workflow.py check-projection-sync --fail-on-issues` | PASSED（registry 28 面〔回退后合同面〕+ 入口双根，按 0.85.0 canonical 源） |
| 3 | 发布投影 | `verify_workflow.py release-projection` | PASS，`source_version = 0.85.0` |
| 4 | 全量资产 | `verify_workflow.py verify` | PASSED（0.85.0 期 snippet 面；新增面随回滚消失） |
| 5 | 入口投影形态 | 读 `AGENTS.md` / `CLAUDE.md` 引导段 | `@bootstrap-version: 0.85.0`（本地未跟踪入口由 §2.1 步骤 3 重同步） |
| 6 | 注入预算姿态 | `verify_workflow.py check-injection-budget --profile standard` | resident 5,694/6,000 hard（数值面双轨一致——0.85.0 翻 hard 延续，回滚**不**弱化该面）；skill 层 entry-skill 回 14,456 口径 |
| 7 | 测试基线 | `pytest` / `verify` 计数 | 轨道 A：回到 0.85.0 期清单（计数下降 = 预期结果，如实注记）；轨道 B：批 2 测试保留（write-guard/closure/写入器面） |
| 8 | e2e | `verify_workflow.py e2e-check` | PASSED（fixture 随窗口回退自洽） |
| 9 | 治理健康 | `verify_workflow.py check-governance` | 与回滚后当场值一致（不预填数字；0.85.0 期既有披露项沿用） |
| 10 | **回滚演练** | 隔离副本执行 §2.1(a)/(b) `revert --no-commit` 干跑 | **未执行（如实标注）**——0.84.0 由 FIX-354 专项承载（隔离副本 `git clone --no-hardlinks` 法 + 零污染三重指纹，rollback-plan-0.84.0 §演练记录先例）；0.85.0/0.86.0 批内无演练票。**建议**：M-3 审查裁决是否补演练（含双轨区间各一腿）；若补，MUST 隔离副本执行（就地执行污染候选索引）+ 真实 `<发布 tip>` 生成后复跑 |

## 5. 不可回滚项（如实列出）

1. **已 push 的 `v0.86.0` tag**：tag 一旦推送即不可撤销——只能前进到 0.86.1（PATCH）修复，不得移动已推送 tag（VERSIONING.md 版本纪律）；
2. **`core/releases/0.86.0.json` 的 transition 事件**：作为发布事实一旦提交即不可「取消」；回滚只能通过新的发布记录表达（不得改写既有 manifest 事件）；
3. **已落账的机录凭证与事件日志**：`.governance/` 内 machine-provenance 行（`〔op-…〕` 锚/receipt 台账/closure-events.jsonl）与新增证据回滚不还原、不删除（数据是事实记录）；
4. **防护/收益不可「部分回滚」的声明面**：B-3 执法可见性（WARN 面板）与 B-4 恢复可靠性均为版本级整体——回滚到 0.85.0 即同时失去行族对账守卫与 step_unknown 恢复语义，不存在「只保留 write-guard、其余回退」的中间态（`GOVERNANCE_LEGACY_BEHAVIOR` 不承载该面——安全语义不回退不变量 + LEGACY_REVERTS 仅 performance 类）；
5. **已发生的用户侧行为**：用户已按 B-3 机录路径完成的治理行写入无法事后重放为手工态——无状态副作用，仅记录事实；
6. **审计信息损失**：区间内新增的审查报告（`docs/reviews/review-FEAT-04x/05x-*`、`review-FIX-365-*`、`review-REL-082-*` 等）与发布文档随 revert 消失——如需保留审计痕迹，回滚前 MUST 归档副本（先例处置：`docs/release/audit-*.md` 类留档）。

## 6. 回滚触发条件

| # | 触发条件 | 判定 | 动作 |
|---|---|---|---|
| 1 | 写入器 CLI 数据损坏（task-row-update/evidence-append 等对治理热文件产生非预期改写——字节保持/原子替换失效） | 行 diff 异常 + `governance-write-guard` 面对账 FAIL + 备份对照 | 立即回滚（轨道 A）+ 从备份恢复治理数据 |
| 2 | closure-chain 恢复语义失效（kill+resume 后重复追加/效果丢失——混沌门在真实使用面复现失败） | journal 单调性 FAIL 或 EVD 重复行实证 | 立即回滚（轨道 A）+ 混沌门回归修复后重发布 |
| 3 | write-guard WARN 风暴（面 5 对账误报淹没有效披露——amnesty 基线漂移） | WARN 计数异常放大 + 逐 digest 核对 | 先核对是否真实漂移；确认误报且不可修 ⇒ 回滚——撤执法面的可行路径为**显式 revert 下界提交 `ffcb787` 本身（单提交）**或轨道 A 整窗回退（轨道 B 区间 `ffcb787..<tip>` 排除下界 ⇒ 执法面随下界保留，不构成撤执法面路径），按 M-3 裁决场景选择 |
| 4 | 治理数据被异常修改或丢失（archive/plan-tracker 非预期变更） | `check-archive-integrity` FAIL 或数据 diff 异常 | 立即回滚 + 从备份恢复 |
| 5 | 投影/入口漂移无法收敛（`check-projection-sync` 双根 apply 后仍 FAIL） | 连续两次 apply 后仍 FAIL | 回滚后重做投影 |
| 6 | M-1 bump 绕开手法后遗症（FEAT-053 P2-1 两阶段耦合缺陷在 28 投影面产生静默丢失——FIX-366 修复前复发） | `release-projection` check 与 declared 面逐字节对照 FAIL | 回滚（轨道 B 下先核对 bypass 手法完整性；不收敛 ⇒ 轨道 A） |

## 7. 8 次手工事故披露链（本版执法面的制度背景——rollback 决策必读）

> 口径源：CHANGELOG 0.86.0 段「如实披露①」+ DEC-220（机录 vs 手工事故对照）+ DEC-224（write-guard 契约修订三条款）+ EVD-1117/1118（写入器时代三活体实证）。

0.86.0 窗口内 **8 次手工行编辑事故全部被 write-guard/审查链捕获并制度性终结**（能力→执法的跨越）：

| # | 阶段 | 事实 | 出处 |
|---|---|---|---|
| 1~5 | DEC-220 期对照记录 | 手工路径 5 次事故（3 次行锚定 + 1 次锁 schema + 1 次入账截断）——全在确定性区，全被 write-guard/复检捕获修复；同期机录路径零事故（change-triage ×8 / review-record ×12 / agent-locks-acquire / execution-packet 全 schema 合规） | DEC-220（2026-09-19） |
| 6~7 | session-snapshot 期 | 手工事故累计 7 次（全捕获）——机录路径持续零事故 | `.governance/session-snapshot.md` |
| 8 | EVD-1117（终值口径） | Coordinator 手写 EVD-1117 被 write-guard 面 5 **首个 WARN 精确捕获**（执法层按设计工作）→ DEC-224 裁定治理行写入转机录路径 → 首机录 EVD-1118 经 evidence-append 落账（三活体实证闭环） | EVD-1117/1118 + DEC-224 |

**回滚决策含义**：回滚到 0.85.0 = 回到「能力无执法」态——8 次事故的防护（面 5 对账 + WARN 路由）消失，手工直写回到无守卫态；已建立的机录路径（EVD→evidence-append / DEC→decision-append / 任务行→task-row-update / 闭环→closure-chain）随轨道 A 一并回退。**回滚决策 MUST 显式评估该防护代价**（§1 write-guard 执法面行同源）。

## 8. 0.87 候选池移交清单（回滚后的前进路径——与本版「不发布什么」对齐）

| # | 候选项 | 来源 | 状态 |
|---|---|---|---|
| 1 | **FIX-366** release/projection.py 两阶段耦合修复（单遍 plan——byte_copy source=同批 transformed target 时 bump 必回滚） | FEAT-053 P2-1 + review-FEAT-058 F-2 落票 | **triage 已入账（0.87.0）**——P1 优先推荐 |
| 2 | write-guard WARN→BLOCK 升级（DEC-224 双约束：不得 WARN-once-then-absorb + hook 窗口消费权台账化） | DEC-224 / version-plan §2 | 0.87 面清单登记 |
| 3 | locks-release 命令缺口（shrink-locks TTL 收缩为最近 Governed 效果——真删除登记缺口） | FEAT-056 gap_disclosure | 候选 |
| 4 | 存储分离 JSON 化（首表 decision-log） | version-plan §3 / arch round-2 | 候选 |
| 5 | closure 铺开（取消/重开/异常接管） | FEAT-056 遗留 | 候选 |
| 6 | FEAT-044 回合心跳 / FEAT-045 并行段识别 | DEC-220 落地映射 | 候选 |
| 7 | B-7 index-rebuild / 大表迁移 / 发版管线自举 | version-plan §3 | 候选 |
| 8 | FIX-364 snapshot freshness 午夜窗修复（fixture 以引擎同口径取日期粒度） | 0.85.0 M-2 遗留 | triage 在案未实施 |
| 9 | 量测边缘观察 4 项（journal detail 透传 / triage-id 词表与 governance id family 词表对齐 / conflict 退出码语义统一 / pre-probe 语义注记） | 本版 M-2 量测首跑 | **新增移交**——Coordinator triage |

---
*REL-083 M-1R 草案冻结（2026-09-20，REL-083，Governance Developer Agent 起草）。事实基线：窗口起点 `c2cc7c1`（v0.85.0 peel，taggerdate 2026-09-20 01:53:52）与 5 提交窗口取自 `git log`/`git rev-list`/`for-each-ref` 实测；B-3/B-4 回退口径取自 CHANGELOG 0.86.0 段（`44831b8` 冻结版）行为变更节原文；8 次手工事故链取自 CHANGELOG 披露① + DEC-220/224 + EVD-1117/1118 实读；0.87 候选池取自 CHANGELOG 披露⑤ + plan-tracker FIX-366 行 + 本版量测边缘观察。回滚演练未执行（如实标注）；`<发布 tip>` 属 M-5 期义务，本文件不预填。*
