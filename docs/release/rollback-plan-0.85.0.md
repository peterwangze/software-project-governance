# Rollback Plan — 0.85.0（REL-081 / FEAT-054 M-1R）

> **M-1R 草案（FEAT-054，2026-09-20）**——Governance Developer Agent 起草、供 Coordinator 审后随候选提交；结构与措辞对齐 `docs/release/rollback-plan-0.84.0.md` 先例（含 0.81.0 R0 F-01/F-04 与 0.82.0 勘误注记的区间教训）。**回滚演练本版未执行**（0.84.0 演练由 FIX-354 专项承载；本版批内无对应票——如实标注，见 §4 #10）；本草案正文不预填演练结果。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.85.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。回滚验证口径（如执行）全部在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）下进行，隔离验收不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；do not claim 1.0.0 production-ready。
- **发布 tip 未生成前不预先编造**：本文件写作时点（M-1R，2026-09-20）0.85.0 的发布 tip（M-5 transition 提交）**尚不存在**——所有 `<发布 tip>` 占位由 M-5 生成后回填，绝不预先虚构 hash。

## 区间锚定（含先例教训注记与本版特有交错事实 —— MUST 先读）

**回滚区间 = 整个 0.85.0 窗口 `3663423..<发布 tip>`**（推荐锚定，见下）：

- **推荐起点 = `3663423`**（0.84.0 manifest canonicalize 提交——「REL-080: canonicalize 0.84.0 release manifest bytes」，2026-09-19）；`v0.84.0` tag peel = transition 提交 `5d1943f`（`git for-each-ref refs/tags/v0.84.0` 实测，tag 对象 `688c281`）；
- **终点 = `<发布 tip>`**（0.85.0 发布 tip = M-5 transition 提交；hash 由 M-5 生成后回填，**不预先编造**）；
- 写作时点计数不写死：M-5 现场以 `git rev-list --count 3663423..<发布 tip>` 取值记入 EVD。M-1R 起草期已知构成 = **17 个窗口提交**（`3663423..1cd224e` 实测 = 17，逐项见 release-checklist §Change Inventory：FIX-356 首票 `be0b844` → … → M-1 打包 `a91d6b4` → 0.86.0 随树票 ×3）+ M-1R prep 批（本三件套 / candidate manifest）+ M-2/M-3 门禁与审查批 + M-5 transition——后三类在起草期未提交。

> **⚠️ 本版特有交错事实（先例教训注记的 0.85.0 变体——M-3 Release Reviewer MUST 复核）**：0.84.0 发布线尾巴与 0.85.0 首票在 git 时序上**交错**——FIX-356（`be0b844`，0.85.0 批 1 首票）**先于** d62066b（REL-080 R6 发布审查报告补提交，0.84.0 M-8 面尾巴）落库。由此：
> 1. **禁止以 `be0b844..<发布 tip>` 作为回滚区间**——git 区间语义排除下界提交自身，`be0b844` 的 diff（FIX-356 全部改动）将**残留**，回不到 0.84.0 行为——与 0.81.0 回滚审查 R0 **F-01**（区间误写代表提交）同形失效模式。任务简报所引「be0b844..1cd224e（16 提交）」是**载荷对照窗口**（release-checklist §Change Inventory 口径），**不是回滚区间**——两者相差首票一项，M-5 现场 MUST 以本节推荐锚定执行；
> 2. **推荐起点 `3663423` 的代价（如实披露）**：以 `3663423..tip` revert 会**一并回退 `d62066b`**（0.84.0 R6 审查报告补提交）——审计面损失。处置（照 0.84.0 rollback §5.6 先例）：回滚前 MUST 将该报告归档副本（其内容已由 REVIEW-REL-080-R6 审查链与 evidence 索引承载，损失为文档面非事实面）；
> 3. **替代锚（不等价，如实标注）**：`git checkout v0.84.0` 落点 = peel `5d1943f`（transition 提交）——缺 `3663423`（canonicalize）与 `d62066b`（R6 报告）两个 M-8 面提交，与 0.84.0 演练 P-5「推演可行但不等价（文档面；代码/版本/行为面一致）」同款结论；
> 4. **终点必须是发布 tip 而非候选打包提交**——post-candidate 提交会修改区间内新增的 release 文档导致 revert 冲突（0.81.0 先例 **F-04**，实测 3 处 UU；0.84.0 演练 P-12 反向实证 exit 1/CONFLICT）。

## 1. 本版改动的回滚影响分类

| 类别 | 本版内容 | 回滚影响 |
|---|---|---|
| **入口模板契约面（行为变更 B-1）⚠️ 主载荷** | bootstrap 模板「自包含全文」→「触发器行内 + 明细按需」（FEAT-041；SKILL.md §B0~B5 承接 + canonical 标记 4→3；resident 5,694/5,966 砍半） | **回退=版本级回滚（无 flag 级降级——CHANGELOG B-1 已声明）**：回退后 resident 注入回升至 0.84.0 形态（4,957/10,718/10,918，+46.9%/+45.4%），会话注入明细回到自包含全文；协议行为约束以入口文件为准的口径回退为 0.84.0 版。无数据损坏风险；**升级路径兼容性使回滚可逆**——「详细规则」H2 恢复 = 边界集超集已验证（旧安装整段替换零残留），反向（0.85.0→0.84.0 模板）同理为整段替换，无残留态风险 |
| **注入预算门禁面（行为变更 B-2）⚠️ 防护弱化** | resident 层 standard/strict 从 ADVISORY 翻 **FAIL 硬门**（FEAT-050；P3-3 三态 fail-closed 断言同 commit） | **回退=版本级回滚（无 flag 级降级——CHANGELOG B-2 已声明）**：回退后 standard/strict 回降 ADVISORY——**预算回弹防护弱化（如实列出，不隐瞒）**，RISK-057 姿态回到 0.84.0 期（缓解②「翻 hard 被测试钉住」的强制力消失，分项表/指纹锚仍在）。`GOVERNANCE_LEGACY_BEHAVIOR` 无法兜底该面（安全语义不回退不变量 + LEGACY_REVERTS 仅允许 performance 类）——**不存在「保留硬门、其余回退」的中间态** |
| **skill 层预算线** | entry-skill 独立数值线 16,000（FEAT-052；report-only 数据字段化 + per-tier 四通道） | 回退后该数值线与 Check 33 渲染消失（report-only，无门禁行为影响）；0.84.0 期 entry-skill 无独立线（被 resident 口径遮蔽——已知代价回归） |
| **新增机检面** | 测试静态版本钉 WARN-only 扫描 + 豁免账本（FIX-361，DEC-213③） | 回退后扫描面消失；版本 bump 期静态钉回归人工发现（FIX-352/353 同型盲区——已知代价）；豁免账本随回滚消失，**双向自洽**：账本 token 匹配 active_version 才生效，0.84.0 active 下 `test_bootstrap_aggregate.py` 的 12 行 0.84.0-tokened 豁免（0.84.0 期账本形态）随文件回退恢复，无假阳 |
| **测试红噪音修复面** | RISK-056 匹配器族 30 项清零（FIX-359：hook 回放 6 重锚 live 派生 + review evidence 24 探测移植） | 回退后 30 项既有失败**回归**（RISK-056 姿态回退）——已知代价；发布门禁不因此阻断（非产品面，0.84.0 期同口径） |
| **归档/健康判定面** | Check 30 closed 集并集派生（FIX-358，13 散文格 ID 收敛）+ 豁免行措辞分流（FIX-357）+ governance-status fixture promote（FIX-362，投影合同 27→28） | 回退后 13 个已归档任务闭环识别回归假红（已知代价）；豁免行措辞回到共用模板（判定逻辑 0.84.0 形态）；fixture 投影合同回 27 面（`check-projection-sync` 按回退后 canonical 源判定，自洽非 fail-closed 误报） |
| **治理成本报告面** | workspace 过滤真实语料修复 + cwd 双源披露（FIX-356/360） | 回退后 `--workspace` 过滤在 dsh v3 会话流下**回归失效**（0→156 sessions 命中修复消失，0 样本死循环回归）——RISK-055 数值验收机制弱化（已知代价；机制修复属 0.85.0 交付） |
| **随树入库的 0.86.0 前置票** | FEAT-049 契约基座（m0-r1 + 58 契约测试）/ FEAT-047 BaselineMetadata / FEAT-051 task-row-update 写入器 / FEAT-046 governance_store 写入器族 | 0.85.0 零行为消费 ⇒ 回退对 0.85.0 行为**无影响**；但 0.86.0 批 0/批 1 在途面随整窗 revert **一并消失**——0.86.0 链需重排（batch 0 契约冻结重做 + 批 1 三票重做）。**回滚决策 MUST 显式评估该代价**（DEC-220/221 轨道在途工作） |
| **入口文件形态（工作区侧）** | repo-root `CLAUDE.md`（full 9,552B）/ `AGENTS.md`（thin 2,834B）+ fixture 双入口——`sync_entry_projection` 投影（M-1 已写盘） | **半自动回退项（MUST 手工收口）**：git revert 还原**已跟踪**入口文件与 canonical 模板，但用户工作区若持有本地未跟踪入口投影（root `CLAUDE.md` gitignored 于部分安装形态——0.84.0 先例 `.gitignore:3` 口径）则 revert 不触碰 ⇒ 回滚后重跑 `sync_entry_projection.py --project <workspace> --source-root <plugin_root> --profile standard --primary CLAUDE.md --write`（幂等，双 apply 零 diff 既有测试锁定） |
| **治理数据面** | 本版 `.governance/` 记录（EVD-1088~1109、REL-081 链、plan-tracker 行） | **不进 git 窗口**（gitignored）——回滚零触碰；0.84.0 引擎读同一份治理数据合法（新增字段/条目对旧引擎是忽略面）；回滚不还原已写入的新证据（数据是事实记录，非版本产物） |
| **测试面** | FIX-358 三分支测试 + M4 突变看护 / FEAT-049 58 契约测试 / FEAT-047 64 测试 / FEAT-051/046 写入器测试 / FIX-361 静态钉套件等批 1/2 新增 | 回退后测试基线回到 0.84.0 期清单——计数下降是回滚的预期结果，不是回滚失败（§4 验证表 #7 如实注记）；`env_failure_classification.json` 登记的 FIX300DualCaliber ×2 + LoopRuntimeClaim ×1 先在失败**不随回滚消失**（其成因 `docs/reviews/review-FIX-300-CODE-R0.md` 与归档迁移均在窗口外） |
| **发布文档面** | 本三件套 + `core/releases/0.85.0.json` + 0.86.0 规划文档（untracked，不入窗口） | 区间内新增文档——0.81.0 先例 **F-04** ⇒ **回滚 MUST 以完整区间 `3663423..<发布 tip>` 表达**（终点 = 发布 tip）；untracked 规划文档不受 revert 影响 |
| **渲染/预设交付面** | DSH persona 版本行 / `adapters/dsh/AGENTS.md.template` / hook `@version` 行（M-1 bump 28 面内） | **回滚需重装预设**（0.84.0 同款）：回退后 MUST 重跑适配层安装/渲染（`python <plugin_root>/adapters/dsh/launch.py --sync`），否则宿主注入面仍是 0.85.0 文本（契约 v2 触发器行内形态）而引擎为 0.84.0——版本不匹配混合态。DSH 侧回滚验证以隔离环境（环境变量重定向至临时目录）渲染 parity 为准 |
| **豁免账本/既有开关** | LRC 豁免 4 条（`core/loop-runtime-claim-exemptions.json`）与 0.84.0 既有开关零触碰 | 回滚对 LRC 账本与既有开关零影响（两侧版本同一文件状态） |

## 2. 回滚程序

### 2.1 插件侧（维护者）

```powershell
# 1) 记录当前状态（证据）
git -C <plugin_root> log --oneline -1
git -C <plugin_root> for-each-ref refs/tags/v0.85.0   # 期望 v0.85.0（已 tag 时；peel 应为 M-5 transition 提交）
python <plugin_root>/skills/software-project-governance/infra/verify_workflow.py check-version-consistency

# 2) 回退到本版之前的稳定点（二选一）
#    (a) 精确回退本版提交区间（推荐，保留历史）——区间 = **整个 0.85.0 窗口
#        `3663423..<发布 tip>`**（<发布 tip> = M-5 transition 提交，hash 由 M-5
#        生成后回填；本文件写作时点该提交不存在，不预填）：
#        ⚠️ 起点必须是 3663423——不是 be0b844（区间语义排除下界自身，FIX-356
#        会残留）、不是当前 HEAD、也不是 tag peel 5d1943f，见「区间锚定」
#        交错事实注记。回滚前将 d62066b（0.84.0 R6 报告）归档副本。
git -C <plugin_root> revert --no-commit 3663423..<发布 tip>
#        区间计数不写死：M-5 现场以 `git rev-list --count 3663423..<发布 tip>` 取值记入 EVD。
#    (b) 直接切回稳定 tag（落点 = peel 5d1943f，缺两个 M-8 面文档提交——不等价，见锚定注记 3）
git -C <plugin_root> checkout v0.84.0

# 3) 入口投影重同步（MUST——本地未跟踪入口投影 revert 不覆盖；§1 载体行注记）
python <plugin_root>/skills/software-project-governance/infra/sync_entry_projection.py `
  --project <workspace> --source-root <plugin_root> --profile standard --primary CLAUDE.md --write

# 4) 重装适配层（本版触碰 DSH 模板/persona 版本行/hook 版本行 ⇒ 必做；隔离验证后再考虑后续动作）
python <plugin_root>/adapters/dsh/launch.py --sync
```

### 2.2 用户侧（受影响用户）

1. `/plugin update`（或重装插件）回到 0.84.0——版本号回退后 marketplace 版本比对生效；
2. 重装/重渲染 agent 预设（DSH 宿主：`launch.py --sync`）使注入面与引擎版本一致；
3. 工作区入口文件（`CLAUDE.md` / `AGENTS.md`）恢复为 0.84.0 引导段——按 §2.1 步骤 3 重跑投影（幂等、可重复）；
4. `GOVERNANCE_LEGACY_BEHAVIOR` / `behavior_profile: legacy` 配置可保留（0.84.0 认识该变量，语义不变；如需洁净可移除）；
5. 用户数据无需任何动作（§3）。

### 2.3 发布前中止（M-0~M-4 窗口）

- 未 tag / 未 push 时中止：候选材料尚未提交 ⇒ 删弃工作树中未提交的四文件即可（本版全部已提交改动集中在窗口内；`.governance/` 不受影响）；
- 已提交候选但未 tag：`git reset --hard 3663423` 丢弃候选提交即可，**不影响**已发布的 0.84.0（tag `v0.84.0` 与 `core/releases/0.84.0.json` 均不在本窗口内；reset 属破坏性命令——执行前 MUST 确认无在途未推送载荷，0.84.0 演练 P-9 同口径推演成立、现场执行属 Coordinator 破坏性 git 确认面）；
- 已 tag 未 push：本地 `git tag -d v0.85.0` + 丢弃 transition 提交（**在 push 之前**；push 之后见 §5）。

## 3. 数据安全（回滚不损坏用户数据）

- **治理数据零风险**：`.governance/`（plan-tracker / evidence-log / decision-log / risk-log / archive / review-artifacts）**不在 git 窗口内**（gitignored），回滚不读不写不删；0.84.0 引擎读取同一份数据合法（新增条目对旧引擎是忽略面）；
- **工作区入口文件**：回滚重写 `CLAUDE.md` / `AGENTS.md` 的 Governance Bootstrap 段（canonical 模板投影，段替换语义）——段外内容零触碰（先例测试锁定：自定义尾段保留；双 apply 零 diff）；
- **不触碰用户配置目录**：本版回滚操作不写 `$HOME` 下任何配置目录、不写 `$DSH_HOME`；适配层重装按既有隔离约定（`$tmpHome` 临时目录重定向）验证；
- **e2e fixture**：`project/e2e-test-project/**` 属仓库内 fixture，随窗口回退（无用户数据属性）；
- **不可逆数据处理**：本版无数据迁移、无 schema 变更、无文件格式变更（FEAT-049 契约基座为纯新增基座，0.85.0 零消费）⇒ 无「回滚后数据不可读」风险。

## 4. 回滚后验证（MUST 全绿才算完成）

| # | 验证项 | 命令 | 期望（0.84.0 态） |
|---|---|---|---|
| 1 | 版本一致性 | `verify_workflow.py check-version-consistency` | PASSED，source = **0.84.0** |
| 2 | 投影同步 | `verify_workflow.py check-projection-sync --fail-on-issues` | PASSED（registry 27 面〔回退后合同面〕+ 入口双根，按 0.84.0 canonical 源） |
| 3 | 发布投影 | `verify_workflow.py release-projection` | PASS，`source_version = 0.84.0` |
| 4 | 全量资产 | `verify_workflow.py verify` | PASSED（0.84.0 期 snippet 面；新增面随回滚消失） |
| 5 | 入口投影形态 | 读 `AGENTS.md` / `CLAUDE.md` 引导段 | `@bootstrap-version: 0.84.0`（canonical 标记回 4 模板形态；本地未跟踪入口由 §2.1 步骤 3 重同步） |
| 6 | 注入预算姿态回归 | `verify_workflow.py check-injection-budget --profile standard` | **ADVISORY** 姿态（B-2 回退）；resident 数值回升 0.84.0 形态（10,718 口径）——`governance-bootstrap` 等回退面按 §1 能力行预期 |
| 7 | 测试基线 | `pytest` / `verify` 计数 | 回到 0.84.0 期清单（计数下降 = 预期结果，如实注记；FIX300DualCaliber ×2 + LoopRuntimeClaim ×1 先在失败**仍在**——其成因在窗口外） |
| 8 | e2e | `verify_workflow.py e2e-check` | PASSED（fixture 随窗口回退自洽） |
| 9 | 治理健康 | `verify_workflow.py check-governance` | 与回滚后当场值一致（不预填数字；0.84.0 期既有披露项沿用） |
| 10 | **回滚演练** | 隔离副本执行 §2.1(a) `revert --no-commit` 干跑 | **未执行（如实标注）**——0.84.0 由 FIX-354 专项承载（隔离副本 `git clone --no-hardlinks` 法 + 零污染三重指纹，见 rollback-plan-0.84.0 §演练记录先例）；本版批内无演练票。**建议**：M-3 审查裁决是否补演练；若补，MUST 隔离副本执行（就地执行污染候选索引——0.84.0 演练「就地执行的可行性判定」实测否决在案）+ 真实 `<发布 tip>` 生成后复跑 |

## 5. 不可回滚项（如实列出）

1. **已 push 的 `v0.85.0` tag**：tag 一旦推送即不可撤销——只能前进到 0.85.1（PATCH）修复，不得移动已推送 tag（VERSIONING.md 版本纪律）；
2. **`core/releases/0.85.0.json` 的 transition 事件**：作为发布事实一旦提交即不可「取消」；回滚只能通过新的发布记录表达（不得改写既有 manifest 事件）；
3. **防护/收益不可「部分回滚」**：B-1 瘦身收益与 B-2 硬门防护均为版本级整体——回滚到 0.84.0 即同时失去注入砍半收益与预算硬门强制力，不存在「只保留硬门、其余回退」的中间态（`GOVERNANCE_LEGACY_BEHAVIOR` 不承载该面——安全语义不回退不变量 + LEGACY_REVERTS 仅 performance 类）；
4. **已发生的用户侧行为**：用户本地已按 0.85.0 契约 v2 协议完成的会话（触发器行内 + 按需加载明细）无法事后重放——无状态副作用，仅记录事实；
5. **`.governance/` 新增证据与 REL-081 记录**：回滚不还原、不删除（数据是事实记录）；
6. **审计信息损失**：区间内新增的审查报告（`docs/reviews/review-FEAT-04x-*`、`review-FIX-35x/36x-*`、`review-FEAT-053-CODE-R0` 等）与发布文档随 revert 消失——如需保留审计痕迹，回滚前 MUST 归档副本（**含 `d62066b` 携入的 0.84.0 R6 报告**——见区间锚定注记 2；先例处置：`docs/release/audit-*.md` 类留档）。

## 6. 回滚触发条件

| # | 触发条件 | 判定 | 动作 |
|---|---|---|---|
| 1 | 契约 v2 触发器行内形态导致会话无法进入正常流程（明细按需加载路径失效/状态读取失败） | 复现 + 隔离环境确认 | 立即回滚（§2） |
| 2 | **注入预算硬门误阻**（standard/strict FAIL 误报阻断正常发布/开发流——B-2 fail-closed 误伤） | 复现 + 事实核对（EVD-1104 基线 4,216/5,694/5,966 对照） | 先核对是否真实超限；确认误报且不可修 ⇒ 回滚（B-2 无 flag 级降级通道） |
| 3 | 治理数据被异常修改或丢失（archive/plan-tracker 非预期变更） | `check-archive-integrity` FAIL 或数据 diff 异常 | 立即回滚 + 从备份恢复 |
| 4 | 投影/入口漂移无法收敛（`check-projection-sync` 双根 apply 后仍 FAIL） | 连续两次 apply 后仍 FAIL | 回滚后重做投影 |
| 5 | 旧安装升级失败（契约 v2 整段替换在真实旧安装形态残留/不兼容——边界集超集验证未覆盖的形态） | 升级后 `check-entry-bootstrap-sync` FAIL 或会话 bootstrap 异常 | 单点可先 `sync_entry_projection` 重投影修复；不收敛 ⇒ 回滚 |
| 6 | 注入 resident 预算耗尽导致协议文本被裁剪（RISK-058 恶化——strict 余量仅 34 tok） | `check-injection-budget` hard FAIL（本版即阻断）/ 面级裁剪 | 硬门 FAIL 本身 = 预期防护动作：先压缩文本或按回退决策树（version-plan 交付 4 节点 R1~R3）升级；不收敛则回滚 |

---
*FEAT-054 M-1R 草案冻结（2026-09-20，FEAT-054，Governance Developer Agent 起草）。事实基线：窗口起点 `3663423` 与 17 提交窗口取自 `git log`/`git rev-list` 实测；tag peel = `5d1943f`（`git for-each-ref` 实测，tag 对象 `688c281`）；B-1/B-2 回退口径取自 CHANGELOG 0.85.0 段（`a91d6b4` 冻结版）「无 flag 级降级，版本级回滚」原文；resident 0.84.0 形态数值（4,957/10,718/10,918）取自 EVD-1104/CHANGELOG 对照段；交错事实（`be0b844` 先于 `d62066b`）取自 `git log --reverse` 时间序实测。回滚演练未执行（如实标注）；`<发布 tip>` 属 M-5 期义务，本文件不预填。*
