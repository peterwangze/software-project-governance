# Rollback Plan — 0.84.0（REL-080）

> **M-0/M-1 草案（REL-080 prep，2026-09-19）**——Release Agent 起草、Coordinator 审后随 M-1 候选提交；结构与措辞对齐 `docs/release/rollback-plan-0.83.0.md` 先例（含 0.81.0 回滚审查 R0 F-01/F-04 与 0.82.0 区间勘误注记的区间教训）。回滚演练（§4 #10）**已由 FIX-354 于隔离副本执行并记录于文末「## 演练记录（REL-080，2026-09-19）」**（`<发布 tip>` 面待 M-5 后复跑）；本草案正文不预填演练结果。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.84.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。回滚验证全部在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）下执行，隔离验收不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；do not claim 1.0.0 production-ready。
- **发布 tip 未生成前不预先编造**：本文件写作时点（M-0/M-1，2026-09-19）0.84.0 的发布 tip（M-5 transition 提交）**尚不存在**——所有 `<发布 tip>` 占位由 M-5 生成后回填，绝不预先虚构 hash。

## 区间锚定（含先例教训注记 —— MUST 先读）

**回滚区间 = 整个 0.84.0 窗口 `2a15e59..<发布 tip>`**：

- **起点 = `2a15e59`**（0.83.0 **发布线末位提交**——「REL-079: 0.83.0 M-8 发布收尾——checklist ragged row 修复 + Gate 表残留占位清理」，2026-09-17；`v0.83.0` tag peel = transition 提交 `296f4f5`，`git rev-parse v0.83.0^{}` 实测。revert `2a15e59..tip` 恰恢复 0.83.0 发布线终态）；
- **终点 = `<发布 tip>`**（0.84.0 发布 tip = M-5 transition 提交；hash 由 M-5 生成后回填，**不预先编造**）；
- 写作时点计数不写死：M-5 现场以 `git rev-list --count 2a15e59..<发布 tip>` 取值记入 EVD。M-1 起草期已知构成 = **10 个载荷提交**（按 git 时间序：`c3e1da0` AUDIT-154 立项与审计闭环 → `564b7da` FEAT-032 → `457a756` FEAT-037 → `a5d678f` FEAT-033 → `469fb57` FEAT-034 → `38ff7d7` FEAT-036 → `df9e7db` FEAT-035 → `697689d` FEAT-038 → `512fd51` FEAT-039 → `b537976` FEAT-040）+ M-0/M-1 prep 批（本三件套 / CHANGELOG 段 / bump 与投影面 / 候选 ledger manifest）+ M-2/M-3 门禁与审查批 + M-5 transition——后三类在起草期未提交。

> **⚠️ 先例教训注记（区间锚定，照 0.81.0 R0 F-01 / 0.81.0 F-04 / 0.82.0 勘误注记教训）**：起点必须是 0.83.0 **发布线末位**（`2a15e59`；`v0.83.0` tag peel = `296f4f5`），**不是**当前 HEAD（`b537976`——其上已含本版全部载荷），也**不是** tag peel 提交（transition 之后还有 M-8 收尾提交 `2a15e59`——以 `296f4f5` 为起点会漏掉 M-8 收尾改动，回不到 0.83.0 发布线终态）。以 HEAD 或 tag peel 为起点的区间不覆盖/不完整覆盖 0.84.0 载荷，按该区间 revert 将留下全部协议与命令面改动、回不到 0.83.0 行为——与 0.81.0 回滚审查 R0 **F-01**（区间误写代表提交，revert 后回不到上一版本行为）**同形**。终点必须是发布 tip 而非候选打包提交——post-candidate 提交会修改区间内新增的 release 文档导致 revert 冲突（0.81.0 先例 **F-04**，实测 3 处 UU）。M-3 Release Reviewer 复核本节。

## 1. 本版改动的回滚影响分类

| 类别 | 本版内容 | 回滚影响 |
|---|---|---|
| **新增 CLI 能力面** | `governance-bootstrap`（FEAT-033）/ `governance-cost-report`（FEAT-032）/ `check-injection-budget`（FEAT-039）+ RISK-055 复验框架 `--ttfa-acceptance`（FEAT-040） | **能力面消失（非缺陷回归）**：回退后这些子命令不存在——任何脚本/协议投影若引用了它们会报「unknown command」。0.83.0 侧的状态获取路径（`status` / `resolve_entry` / 逐段读热文件）**仍完好**（本版未删除任何既有命令）⇒ 回退后治理可用性不依赖这些新命令 |
| **协议时序面（行为变更 B-1）** | 首次交互前置——快路径热数据就绪即 ask、深检后置（FEAT-034） | **回退即恢复 0.83.0 启动序**（Step 1→2→3→4，深检先行）：已知代价回归——冷启动到首次 ask 回到实测 4m31.8s~7m08s 量级（AUDIT-154 基线），但**无数据损坏风险**；「待检查」健康位语义回归为「深检后即绿」 |
| **写操作授权面（行为变更 B-2）⚠️ 安全面** | 迁移写操作（升级/归档/清理）全部 ask-确认前置（FEAT-035） | **回退即恢复 0.83.0 自动执行语义——安全防护弱化，如实列出（不隐瞒）**：迁移/清理写操作重新可能在用户未响应前执行（含 cleanup **删除面**）。这是本版**唯一带安全性质的回归项**——回滚决策 MUST 显式接受该弱化；建议回滚后以「暂停自动升级/归档」的操作纪律人工替代（无 flag 级替代通道，见 §5）。 |
| **输出/入口形态面（B-3/B-4/B-5）** | Snapshot 8 字段默认视图（FEAT-036）+ `AGENTS.md` 薄指针（FEAT-037）+ `/governance` 按需加载（FEAT-038） | **回退即恢复 0.83.0 形态**：默认视图回到完整输出、双入口各持完整模板（双份注入）、命令文档回到全文单文档 ⇒ **注入与输出成本回升**（0.84.0 的 -83% / -76.5% 收益消失）。无功能性破坏；`check-projection-sync` / `check-entry-bootstrap-sync` 按回退后的 canonical 源判定（自洽，非 fail-closed 误报） |
| **灰度开关（B-6）** | `GOVERNANCE_LEGACY_BEHAVIOR` / `behavior_profile: legacy` 回退通道（FEAT-040） | **回滚即无需该通道**（整体即回退）；回退后设置该 env/配置项**无副作用**（0.83.0 不认识该变量 ⇒ 忽略，非报错）。⚠️ 反向不可用：回滚后不存在"回退 4 项性能行为"的细粒度能力 |
| **入口文件形态（工作区侧，非仅 git）** | `AGENTS.md` / `CLAUDE.md` 引导段回退为 canonical 投影（M-2 已写盘；`AGENTS.md` 与 fixture 两入口**已跟踪**，root `CLAUDE.md` **gitignored/本地**） | **半自动回退项（MUST 手工收口）**：git revert 会还原**已跟踪**入口文件（`AGENTS.md`、`project/e2e-test-project/{AGENTS,CLAUDE}.md`），但 **root `CLAUDE.md` 是本地未跟踪文件**（`.gitignore:3`），revert **不会**触碰它 ⇒ 回滚后它仍带 `@bootstrap-version: 0.84.0`，与回退后的 canonical 源（0.83.0）漂移。**收口动作（MUST）**：回滚后在工作区重跑 `python <plugin_root>/skills/software-project-governance/infra/sync_entry_projection.py --project <workspace> --source-root <plugin_root> --profile standard --primary CLAUDE.md --write`（§2.1 步骤 3），使入口投影回到 0.83.0 模板 |
| **治理数据面** | FEAT-032~040 的 `.governance/` 记录（EVD-1073~1081、REL-080 证据、plan-tracker 行） | **不进 git 窗口**（`.gitignore:10`）——回滚**零触碰**。回退后的 0.83.0 引擎读同一份治理数据仍然合法（新增字段/条目对旧引擎是忽略面）；⚠️ 但回滚**不还原**已写入的新证据/任务行（数据是事实记录，非版本产物） |
| **测试面** | 新增测试与守护（FEAT-032 37 单测 / FEAT-033 42 测试 / FEAT-037 32 测试 / FEAT-036 4 marker+24 反断言 / FEAT-039 预算套件 / FEAT-040 三层机检 + 26 投影） | **回退后测试基线回到 0.83.0 期清单**——计数下降是回滚的预期结果，不是回滚失败（§4 验证表 #7 如实注记）；新守护面（薄指针双面守护、预算门禁、灰度三层机检）随回滚消失 |
| **发布文档面** | 本三件套 + `project/CHANGELOG.md` [0.84.0] 段 + `core/releases/0.84.0.json` | 区间内新增文档——0.81.0 先例 **F-04** 实证「在发布 tip 上 revert 不完整区间会因这些文档冲突」⇒ **回滚 MUST 以完整区间 `2a15e59..<发布 tip>` 表达** |
| **渲染/预设交付面** | `adapters/dsh/AGENTS.md.template`（+ 灰度开关段）/ `agent-presets/governance/agent.cordis.yml.template`（persona 版本行）/ `adapters/dsh/launch.py`（延迟导入复用） | **回滚需重装预设**（与 0.83.0 的"零影响"不同）：本版**触碰**了 DSH 模板与 persona 版本行 ⇒ 回滚后 MUST 重跑适配层安装/渲染（§2.2 步骤 2），否则宿主注入面仍是 0.84.0 文本（含灰度开关段）而引擎为 0.83.0——**版本不匹配的混合态**。DSH 侧回滚验证以隔离环境（环境变量重定向至临时目录）渲染 parity 为准 |
| **豁免账本/既有开关** | 本版零触碰——`core/loop-runtime-claim-exemptions.json`（4 条豁免 + digest 锚）与 0.83.0 既有开关全部保留 | 回滚对豁免账本与既有开关**零影响**（两侧版本同一文件状态） |

## 2. 回滚程序

### 2.1 插件侧（维护者）

```powershell
# 1) 记录当前状态（证据）
git -C <plugin_root> log --oneline -1
git -C <plugin_root> describe --tags            # 期望 v0.84.0（已 tag 时）
python <plugin_root>/skills/software-project-governance/infra/verify_workflow.py check-version-consistency

# 2) 回退到本版之前的稳定点（二选一）
#    (a) 精确回退本版提交区间（推荐，保留历史）——区间 = **整个 0.84.0 窗口
#        `2a15e59..<发布 tip>`**（<发布 tip> = M-5 transition 提交，hash 由 M-5
#        生成后回填；本文件写作时点该提交不存在，不预填）：
git -C <plugin_root> revert --no-commit 2a15e59..<发布 tip>
#        区间计数不写死：M-5 现场以 `git rev-list --count 2a15e59..<发布 tip>` 取值
#        记入 EVD。起点必须是 2a15e59（0.83.0 发布线末位提交，含 M-8 收尾）——
#        不是当前 HEAD、也不是 tag peel 296f4f5，见「区间锚定」先例教训注记。
#    (b) 直接切回稳定 tag
git -C <plugin_root> checkout v0.83.0            # 或 git reset --hard 之后的重新拉取

# 3) 入口投影重同步（MUST——root CLAUDE.md 未跟踪，revert 不覆盖；§1 载体行注记）
python <plugin_root>/skills/software-project-governance/infra/sync_entry_projection.py `
  --project <workspace> --source-root <plugin_root> --profile standard --primary CLAUDE.md --write

# 4) 重装适配层（本版触碰 DSH 模板/persona 版本行 ⇒ 必做；隔离验证后再考虑后续动作）
#    注：0.81.0 B-2 写入守卫属 0.81.0/0.82.0 交付，本窗口未触碰，回滚后仍有效。
```

### 2.2 用户侧（受影响用户）

1. `/plugin update`（或重装插件）回到 0.83.0 —— 版本号回退后 marketplace 版本比对生效；
2. 重装/重渲染 agent 预设（DSH 宿主：`python <plugin_root>/adapters/dsh/launch.py --sync`）使注入面与引擎版本一致；
3. 工作区入口文件（`CLAUDE.md` / `AGENTS.md`）恢复为 0.83.0 引导段——若用户工作区已是 0.84.0 投影，按 §2.1 步骤 3 重跑投影（幂等、可重复）；
4. `GOVERNANCE_LEGACY_BEHAVIOR` / `behavior_profile: legacy` 配置可保留（0.83.0 忽略，无副作用），如需洁净可移除；
5. 用户数据无需任何动作（§3）。

### 2.3 发布前中止（M-0~M-4 窗口）

- 未 tag / 未 push 时中止：`git reset --hard 2a15e59` 即可（本版全部改动集中在该窗口；`.governance/` 不受影响）；
- 已提交候选但未 tag：丢弃候选提交即可，**不影响**已发布的 0.83.0（tag `v0.83.0` 与 `core/releases/0.83.0.json` 均不在本窗口内）；
- 已 tag 未 push：本地 `git tag -d v0.84.0` + 丢弃 transition 提交（**在 push 之前**；push 之后见 §5）。

## 3. 数据安全（回滚不损坏用户数据）

- **治理数据零风险**：`.governance/`（plan-tracker / evidence-log / decision-log / risk-log / archive / review-artifacts）**不在 git 窗口内**（`.gitignore:10`），回滚不读不写不删；0.83.0 引擎读取同一份数据合法（新增条目对旧引擎是忽略面）；
- **工作区入口文件**：回滚重写 `CLAUDE.md` / `AGENTS.md` 的 **Governance Bootstrap 段**（canonical 模板投影，`replace_bootstrap_section` 段替换语义）——段外内容零触碰（先例测试 `test_write_bootstrap_splices_section_preserving_tail` 锁定：自定义尾段保留）；
- **不触碰用户配置目录**：本版回滚操作不写 `$HOME` 下任何配置目录、不写 `$DSH_HOME`；适配层重装按既有隔离约定（`$tmpHome` 临时目录重定向）验证；
- **e2e fixture**：`project/e2e-test-project/**` 属仓库内 fixture，随窗口回退（无用户数据属性）；
- **不可逆数据处理**：本版无数据迁移、无 schema 变更、无文件格式变更 ⇒ 无「回滚后数据不可读」风险。

## 4. 回滚后验证（MUST 全绿才算完成）

| # | 验证项 | 命令 | 期望（0.83.0 态） |
|---|---|---|---|
| 1 | 版本一致性 | `verify_workflow.py check-version-consistency` | PASSED，source = **0.83.0** |
| 2 | 投影同步 | `verify_workflow.py check-projection-sync --fail-on-issues` | PASSED（registry 26 面 + 入口双根，按 0.83.0 canonical 源） |
| 3 | 发布投影 | `verify_workflow.py release-projection` | PASSED，`source_version = 0.83.0` |
| 4 | 全量资产 | `verify_workflow.py verify` | PASSED（0.83.0 期 snippet 面；新增命令的 snippet 随回滚消失） |
| 5 | 入口投影形态 | 读 `AGENTS.md` / `CLAUDE.md` 引导段 | `@bootstrap-version: 0.83.0`（root `CLAUDE.md` 由 §2.1 步骤 3 重同步） |
| 6 | 新命令不存在（能力面回归） | `governance-bootstrap` / `governance-cost-report` / `check-injection-budget` | 报 unknown command（**预期**，非回滚失败） |
| 7 | 测试基线 | `pytest` / `verify` 计数 | 回到 0.83.0 期清单（计数下降 = 预期结果，如实注记） |
| 8 | e2e | `verify_workflow.py e2e-check` | PASSED（fixture 随窗口回退自洽） |
| 9 | 治理健康 | `verify_workflow.py check-governance` | 与回滚后当场值一致（不预填数字；0.83.0 期既有披露项沿用） |
| 10 | **回滚演练（FIX-354 已执行——明细见文末「演练记录」）** | 隔离副本执行 §2.1(a) `revert --no-commit` 干跑 | **exit 0 / 零冲突 / 82 paths**（载荷面 `2a15e59..b537976`）与 **98 paths**（含版本平面的完整窗口近似 `2a15e59..a1027bd`，索引与 `2a15e59` 树逐字节相同）；先例 0.83.0 为 exit 0、零冲突、36 paths；真实 `<发布 tip>` 面待 M-5 后复跑并入 checklist #18 |

## 5. 不可回滚项（如实列出）

1. **已 push 的 `v0.84.0` tag**：tag 一旦推送即不可撤销——只能前进到 0.84.1（PATCH）修复，不得移动已推送 tag（VERSIONING.md 版本纪律）；
2. **`core/releases/0.84.0.json` 的 transition 事件**：作为发布事实一旦提交即不可"取消"；回滚只能通过新的发布记录表达（不得改写既有 manifest 事件）；
3. **安全面弱化不可"部分回滚"**：回滚到 0.83.0 即整体恢复静默迁移写语义（B-2 面）——不存在"只保留确认门、其余回退"的中间态（该细粒度能力本就是本版**新增**的，回滚后不存在）；
4. **已发生的用户侧行为**：用户本地已按 0.84.0 协议完成的会话（首次交互前置/按需加载）**无法事后重放**——无状态副作用，仅记录事实；
5. **`.governance/` 新增证据与 REL-080 记录**：回滚不还原、不删除（数据是事实记录）；
6. **审计信息损失**：区间内新增的审查报告（`docs/reviews/review-REL-080-*`、`docs/reviews/review-FEAT-03x-*`）与发布文档随 revert 消失——如需保留审计痕迹，回滚前 MUST 归档副本（先例处置：`docs/release/audit-*.md` 类留档）。

## 6. 回滚触发条件

| # | 触发条件 | 判定 | 动作 |
|---|---|---|---|
| 1 | 会话启动协议不可用（首次交互前置导致会话无法进入正常流程 / 状态读取失败） | 复现 + 隔离环境确认 | 立即回滚（§2） |
| 2 | **未授权写操作发生**（迁移/清理在用户未确认前执行——B-2 防护失效） | evidence/日志实证 | **最高优先**：立即回滚 + 事件记录（incidents） |
| 3 | 治理数据被异常修改或丢失（archive/plan-tracker 非预期变更） | `check-archive-integrity` FAIL 或数据 diff 异常 | 立即回滚 + 从备份恢复 |
| 4 | 投影/入口漂移无法收敛（`check-projection-sync` 双根 apply 后仍 FAIL） | 连续两次 apply 后仍 FAIL | 回滚后重做投影 |
| 5 | 新增命令/检查面在生产工作区崩溃或误阻（`governance-bootstrap` / `check-injection-budget` 硬 FAIL 误报） | 复现 + 事实核对 | 先关路径（改用 `status` 等既有路径）；不收敛则回滚 |
| 6 | 注入 resident 预算耗尽导致协议文本被裁剪（RISK-058 恶化） | `check-injection-budget` 显示余量耗尽 / 裁剪 | 先压缩文本（DEC-212⑦）；不收敛则回滚 |

---

*M-0/M-1 草案冻结（2026-09-19，REL-080 prep）。事实基线：窗口起点 `2a15e59`（0.83.0 发布线末位提交）与载荷 10 提交取自 `git log` 实测；tag peel = `296f4f5`（`git rev-parse v0.83.0^{}`）；回退面（4 项性能行为 + 安全不变量）取自 DEC-212①/②；B-1~B-6 取自 CHANGELOG 0.84.0 段与 feature-flags-0.84.0.md §2。回滚演练结果见文末「## 演练记录（REL-080，2026-09-19）」；`<发布 tip>` 属 M-5 期义务，本文件不预填。*

## 演练记录（REL-080，2026-09-19）

> **执行方**：Governance Developer Agent（FIX-354）｜**性质**：**隔离副本**只读推演 + 可执行步骤实测——**未对真实仓库执行任何回滚命令**（真实仓库零 git 写操作，核验见 §演练零污染核验）
> **隔离形态**：`git clone --no-hardlinks <repo> %TEMP%\fix354_drill_20260919_032603\repo-clone`（66 MB 独立副本），演练结束整目录删除（`Test-Path` = False，零残留）；0.83.0 侧行为面测试另将 `.governance/`（464 文件）复制进该副本执行——副本内读写，源仓库只读
> **时点约束（如实标注）**：`<发布 tip>`（M-5 transition 提交）演练时点**不存在** ⇒ §2.1(a) 的最终形式**今日不可执行**。演练用两层已标注的替代，**两层都实测**：
> 1. **载荷面**（真实提交）：区间 `2a15e59..b537976`（= 10 提交载荷窗口，HEAD）；
> 2. **完整窗口近似**（构造性）：副本内以**真实 staged 候选**（28 文件——演练时点快照，经 `git diff --cached --binary` 导入，逐字应用 exit 0 / 28 paths）构造 `SYNTHETIC M-1 prep` 提交 `e1aaa5e`，其上再构造 `SYNTHETIC M-5 transition` 提交 `a1027bd`（仅 `core/releases/0.84.0.json` 的 `"lifecycle_state":"candidate"` → `"released"` ×2 处，模仿真实 transition 对候选新增文件的回访）⇒ `2a15e59..a1027bd` 为本文件 §2.1(a) 的**结构等价近似**（含版本平面 + 发布文档 + CHANGELOG + candidate ledger）。两个构造性提交**仅存在于已删除的副本内**，未进入真实仓库。

### 步骤逐项验证

| # | 步骤（本文件出处） | 验证方式 | 实测结果 | 结论 |
|---|---|---|---|---|
| P-1 | 「区间锚定」事实核对 | 真实仓库只读 | `git log -1 2a15e59` = `REL-079: 0.83.0 M-8 发布收尾…`（2026-09-17）✓；`git rev-parse v0.83.0^{}` = `296f4f5…`（tag 对象 `e0cf42a`）✓；`2a15e59` 之父 = `296f4f5` ⇒ 「以 peel 为起点会漏掉 M-8 收尾」成立（实测 M-8 增量 = 1 文件 `docs/release/release-checklist-0.83.0.md`，14+/14-）✓；`git rev-list --count 2a15e59..HEAD` = **10** ✓ 且 hash 清单与 Change Inventory 逐项一致 | **可行**（锚定三项全对） |
| P-2 | §2.1 步骤 1（记录状态） | 真实仓库只读 | `git log --oneline -1` = `b537976`；`git describe --tags` = `v0.83.0-11-gb537976`（0.84.0 未 tag 时的正确观测值，与「已 tag 时」限定语相符）；`check-version-consistency` exit 0（PASSED，1 WARN = plan-tracker 0.83.0） | **可行** |
| P-3 | §2.1 步骤 2(a) 区间 revert 干跑（**载荷面**） | 副本 | `git revert --no-commit 2a15e59..b537976` → **exit 0 / 0 冲突 / 82 paths**；反悔后 `check-version-consistency` PASSED、`release-projection` PASS `source_version=0.83.0`、`AGENTS.md` = `@bootstrap-version: 0.83.0`；`governance-bootstrap` = `invalid choice`（§4 #6 预期） | **可行（实测）** |
| P-4 | §2.1 步骤 2(a) 区间 revert 干跑（**完整窗口近似**：终点 = 近似发布 tip） | 副本 | `git revert --no-commit 2a15e59..a1027bd` → **exit 0 / 0 冲突 / 98 paths**；且 `git diff --cached 2a15e59` **空** ⇒ 索引与 `2a15e59` 树**逐字节相同** = 精确回到 0.83.0 发布线终态；`release-projection` PASS `source_version=0.83.0` | **可行（实测）**；真实 tip 面待 M-5 后复跑 |
| P-5 | §2.1 步骤 2(b) tag 回退 | 副本 | `git checkout v0.83.0` → detached HEAD = `296f4f5`（= peel，**非**发布线末位）；与 (a) 终态相差 **1 个文档提交**（`docs/release/release-checklist-0.83.0.md`，14+/14-） | **推演可行但不等价**（文档面；代码/版本/行为面一致）——§2.1 步骤 2 「二选一」措辞建议注明该差异 |
| P-6 | §2.1 步骤 3（入口投影重同步） | 真实仓库 `--dry-run`（仓库根 + fixture 双跑） | `[SKIP] CLAUDE.md/AGENTS.md already synchronized`、`[PASS]`、exit 0、**零写盘** ⇒ 当前 0.84.0 工作区下为**已收敛的幂等 no-op**；幂等性既有机器证据：`test_entry_projection.py::test_apply_dual_entry_and_double_apply_zero_diff`（双次 apply 零 diff）+ `::test_write_bootstrap_dry_run_writes_nothing`（本次复跑 **2 passed**） | **可行（幂等已证 + 当场零差异）** |
| P-7 | §2.1 步骤 4（重装适配层） | 未执行 | 写宿主注入面 / `$DSH_HOME` = 真实环境写操作；M7.7 三选一（隔离重定向 / 备份校验 / 逐项授权）三者皆缺 ⇒ **禁止执行**（无豁免） | **需人工**（建议隔离环境 `$tmpHome` 重定向下执行并逐条上报留痕） |
| P-8 | §2.2 用户侧 1~5 | 未执行 | 属受影响宿主的 `/plugin update` / 预设重装 / 工作区入口重投影；其中 #3 与本文件步骤 3 同工具，幂等性已证 | **需人工** |
| P-9 | §2.3 发布前中止 | 纯推演 | `git reset --hard 2a15e59` 属破坏性命令（真实仓库执行将丢弃 28 文件候选）⇒ 未执行；语义核对成立：本版改动全部在该窗口内，`.governance/` 在 `.gitignore:10` ⇒ reset 不触碰治理数据 | **推演可行** |
| P-10 | §1 行为开关面（B-6） | 真实仓库只读 + 副本 0.83.0 侧 | 无 env：`behavior.profile=modern / source=default / reverted=[] / invariants×5`；`GOVERNANCE_LEGACY_BEHAVIOR=1`：`profile=legacy / source=env / reverted=[bootstrap 热数据入口, 首次交互时序, snapshot 渲染契约, Scenario 文档加载]`（**4 项**，与 §1 B-6 行逐项一致）/ `invariants×5`（升级确认门 / 异常不隐藏 / fail-closed / 真实环境防护 / 复审必达）**不回退**。0.83.0 侧「无副作用」：副本反悔至 0.83.0 树（`version: 0.83.0` + `.governance/` 副本）→ `check-version-consistency` 于 env off/on 两臂 **exit 0 且输出逐字节相同**；静态核：`git grep GOVERNANCE_LEGACY_BEHAVIOR 2a15e59` = **0 hit**、`behavior_profile` = **0 hit** | **可行（双向实测）** |
| P-11 | §4 回滚后验证 #1/#3/#5/#6 | 副本（0.83.0 树） | #1 `check-version-consistency` = **PASSED**；#3 `release-projection` = **PASS**，`source_version=0.83.0`、`projections_checked=15`（0.83.0 期 registry）；#5 `AGENTS.md` = `@bootstrap-version: 0.83.0`；#6 `governance-bootstrap` = `invalid choice`（能力面回归，**预期**） | **可行（4 项实测）**；#4/#7/#8/#9（`verify` / pytest / e2e / check-governance）属长时或依赖治理数据面，本次**未执行**——如实标注，**不写成通过** |
| P-12 | §4 #10 的 F-04 反向实证 | 副本（正/负两例） | 正确区间 `2a15e59..a1027bd`（终点 = 近似 tip）→ exit 0 / 0 冲突 / 98 paths；**错误区间** `2a15e59..e1aaa5e`（终点 = 候选打包提交，tip 提交残留）→ **exit 1 / 1 条冲突路径（2 条 unmerged 索引项）**：`CONFLICT (modify/delete): skills/software-project-governance/core/releases/0.84.0.json` | **可行（失效模式可复现）**⇒「MUST 以完整区间表达（终点 = 发布 tip）」为**强制项**，非风格建议 |
| P-13 | 干跑清理面 | 副本 | `git revert --abort` 实测完整还原（索引 + 工作树：冲突臂 abort 后 `git status` = 0 项；成功臂 staged 98 → 0）；副本最终 0 残留并整目录删除 | **可行** |

### 就地执行的可行性判定（本演练为何在隔离副本执行 —— 实测依据）

对本文件 §2.1(a) 在**真实仓库就地**执行的可行性做了专门实测（副本内，1 个暂存探针）：

- **`revert --no-commit` 在脏索引下不拒绝**（副本内受控实验）：暂存 1 文件后执行区间 revert → **exit 0**，并逐提交 `Auto-merging skills/…/SKILL.md` ×5 ⇒ 回滚结果被**自动并入**已暂存内容。真实仓库当前持有 **28 个 staged 候选文件**（演练时点 2026-09-19 06:xx 快照——R5 时点为 38，属演练后独立变更，不在本表口径内；其中 `AGENTS.md` / fixture `SKILL.md` / 4 hooks 等均落在回滚区间内）⇒ 就地干跑将污染候选索引，且 `--abort` 之后亦无法保证逐字节还原候选态。
- **结论**：F-03 演练**必须**在隔离副本执行；就地执行列入禁止面。

### 演练零污染核验（真实仓库）

| 核验项 | 演练前 | 演练后 | 判定 |
|---|---|---|---|
| HEAD | `b537976d31f173ad2f2c69cc14888f51a1acbf3a` | 同值 | ✓ |
| staged 文件数 | 28 | **28** | ✓ 不变（演练时点 2026-09-19 06:xx 快照——后续发布期修复 staged 增至 37 属演练后独立变更，不在本表口径内） |
| `git status --porcelain` 全文 SHA256 | `A366E4F6…C6AD1` | 同值 | ✓ 逐字节一致 |
| 索引 `git ls-files -s` 全文 SHA256 | `291BF949…41E72` | 同值 | ✓ 逐字节一致 |
| `git ls-files -u`（冲突残留） | 0 | 0 | ✓ |
| `REVERT_HEAD` / `MERGE_HEAD` 残留 | — | 均不存在 | ✓ |
| 演练临时目录 | — | `%TEMP%\fix354_drill_20260919_032603` 已删除（`Test-Path` = False） | ✓ 零残留 |

### 结论汇总（供 R1 复核）

| 面 | 结论 |
|---|---|
| §2.1(a) 区间 revert | **可行**（载荷面 exit 0 / 0 冲突 / 82 paths；完整窗口近似 exit 0 / 0 冲突 / 98 paths + 索引与 `2a15e59` 树逐字节相同）｜真实 `<发布 tip>` 面**待 M-5 后复跑**（0.81.0 先例为 36 paths） |
| §2.1(b) tag 回退 | **推演可行但不等价**（落点 `296f4f5` = peel，缺 M-8 收尾 1 文档提交） |
| §2.1 步骤 3 入口投影 | **可行 / 幂等已证**（当场 dry-run 零差异 + 既有双 apply 零 diff 测试） |
| §2.1 步骤 4 适配层重装 | **需人工**（真实环境写面，隔离重定向后可执行） |
| §2.2 用户侧 | **需人工**（宿主侧操作，本演练不代执行） |
| §2.3 发布前中止 | **推演可行**（破坏性命令未执行） |
| §1 B-6 行为开关面 | **可行**（0.84.0 侧 4 项回退 + 5 项不变量；0.83.0 侧 env 双臂输出逐字节相同） |
| §4 #1/#3/#5/#6 | **可行**（0.83.0 树实测） |
| §4 #4/#7/#8/#9 | **未执行**（长时 / 治理数据依赖面，如实标注） |
| F-04 反向实证 | **已复现**（错误终点 → exit 1 / 1 冲突路径） |
| 工作树污染 | **零**（指纹前后同值；staged 28 不变——演练时点 2026-09-19 06:xx 口径） |

> **演练方备注（不改本文件既有措辞，留 Coordinator 裁决）**：① §2.1 步骤 2 的「(a)/(b) 二选一」在本演练中**不等价**（见 P-5），建议后续版本注明 (b) 落点为 transition 提交；② 本文 §4 #10 行与页脚已按演练结果回填指针（FIX-354）；③ `<发布 tip>` 落地后 MUST 复跑 P-4 并把 exit 码 / 冲突数 / paths 数记入 checklist #18（本演练为结构等价近似，不替代真实 tip 演练）。

*演练记录冻结（2026-09-19，FIX-354）：隔离副本执行，真实仓库零 git 写操作；所有 exit 码 / 冲突数 / paths 数 / 指纹均为当场实测值，未预填、未外推。*
