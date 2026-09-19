# 0.85.0 版本规划提案（Release 半面）

> **任务**: 0.85.0-PLAN/R · **日期**: 2026-09-19 · **状态**: 提案 R1 修订版（R0 双审 NEEDS_CHANGE → 本版逐 finding 修订 → 待 R1 复审 → Coordinator/用户裁定）
> **R0 审查输入**: `docs/reviews/review-REL-081-DESIGN-R0.md`（NEEDS_CHANGE/2——D-F-1/D-F-2 为 BLOCKING）+ `docs/reviews/review-REL-081-RELEASE-R0.md`（NEEDS_CHANGE/1——R-F-1 为 BLOCKING）；本版修订覆盖指令清单 11 项（D-F-1~5 / R-F-1~6）+ 主动响应 D-F-8（A1 趋零），D-F-6/D-F-7 属 Analyst 半面文档不在本文件修订范围
> **性质**: 规划面（非发布执行——本版本尚未开发，不做 checklist/rollback 执行面）
> **裁决权**: 版本号/范围最终由 Coordinator 按本建议提请用户裁定；本文档仅提供依据充分的具体建议 + 条件式分支
> **边界**: 不修改产品代码、不修改 `.governance/`（本文档为 `docs/release/` 唯一写入物）

## 输入事实源（全部经 Read/Grep 核实）

| 事实源 | 核实内容 |
|--------|---------|
| `.governance/plan-tracker.md` `## 版本规划`（L172~334） | 版本路线图 0.82.0/0.83.0/0.84.0 三先例行 + 版本号分配规则 8 条 + V-Gate 表 |
| `.governance/decision-log.md` DEC-210/211/212/213/215（L151~157） | 注入预算 advisory 出货与翻 hard 时点、canonical 口径、M-1 口径盲区、0.85.0 批次规划授权与候选序 |
| `.governance/risk-log.md` L50~54 | RISK-054/055/056/057/058 实况（全部打开） |
| `.governance/session-snapshot.md` | FIX-356 闭环态、候选池 8 项、DEC-215①② 裁决 |
| `project/CHANGELOG.md` 0.82.0/0.83.0/0.84.0 段（L5~148） | 三先例的载荷形态、MINOR bump 依据、行为变更披露形态 |
| `skills/software-project-governance/core/VERSIONING.md` | L11/L12/L13 三段升级触发条件、L37/L38 bump 强制表、版本规划纪律 |
| `docs/release/release-checklist-0.84.0.md` L25/L127~132 | 「目标版本下不发布」先例形态；RISK-053/054/058 的 0.85.0 承接建议 |
| `docs/reviews/review-FEAT-039-CODE-R1.md`、`review-FEAT-040-CODE-R0.md`、`review-REL-080-RELEASE-R2/R3/R4.md` | resident 余量瘦身输入、triage files 冲突检测漏面、C-01 标级 P1、快照一致性校验候补 |
| 归档先例（REL-071/REL-078/REL-079 完成行） | M-0~M-8 标准链逐步形态 |

---

## 交付 1：semver 裁定建议

### 建议：**0.85.0（MINOR）**

### bump 理由（对照候选池内容逐项定性）

候选池 8 项（DEC-215② 序）**不是全部为修复/收口**——含三个规则面/门禁语义变更项：

| 候选项 | 变更性质定性 | VERSIONING 依据 |
|--------|------------|----------------|
| ① standard/strict 模板瘦身 + **翻 hard** | **门禁判定姿态翻转**——`check-injection-budget` standard/strict 从 ADVISORY（不阻断）→ hard（超限 FAIL）。这是检查面判定语义的实质变更，改变发布门禁行为 | **L11 处置段（见下——Major 触发条款的字面落入与 pre-1.0.0 处置）** + L12「新增 MUST 规则、新增子工作流/skill、新增 B/C 级自动化能力」等条款 + 0.82.0/0.83.0 CHANGELOG「判定规则扩展」先例口径（L145/L110——先例解释用语，非 L12 原文） |
| ④ 测试静态版本钉机检面（DEC-213③） | 「纳入 M-1 检查清单**或新增机检面**（全仓 grep 测试面静态钉审计）」——若走新增机检面路径 = **新增验证能力** | L12「新增 B/C 级自动化能力」；L34（verify_workflow.py 新增检查项 → 至少 PATCH；组合入 MINOR 批） |
| ⑧ entry-skill 独立预算 | 预算判定面新增维度（report-only 层从"无预算"→"独立预算线"）——`BUDGET_TIER_POLICY` 数据结构扩展 | L12 同上 |
| ② C-01 豁免行措辞分流 + FIX-341 谓词分歧 13 行 | 审查/判定面措辞与谓词修正 | 修复收口面（不独立触发 MINOR） |
| ③ FIX-356 F-1 CALIBRATION 披露行 | 披露文本 | 修复收口面 |
| ⑤ governance-status.md fixture 同族缺口 | fixture 修复 | 修复收口面 |
| ⑥ P3 族（FEAT-038/039/040 遗留 + 死夹具清理 + FIRST_RUN_DEMO 19→20；其中 FEAT-039 F-1/F-2/F-5/P3-3/P3-4 五子项编排拆出随批 2——见交付 2 ⑥ 族拆分说明） | 修复/清理/计数 | 修复收口面 |
| ⑦ RISK-056 回放族（fixture 重锚或版本世界参数化） | 测试修复 | 修复收口面（L38 口径内，但仅当批次**无**①④⑧时才适用） |

**核心论证**：只要 ①（翻 hard）在版内，本批就存在「门禁判定语义变更」——按 VERSIONING L11/L12 与 0.83.0 先例（判定面变更走 MINOR），MINOR 成立；L38「仅修复 bug（不改变行为语义）→ PATCH」不适用。三先例一致性佐证：0.83.0 仅 3 个修复型任务（FIX-348/349/350），因含判定口径修正与新扫描面仍定为 MINOR（CHANGELOG L110 明文）。

**VERSIONING L11（Major 触发条款）处置（Release R0 F-1 采纳）**：翻 hard 字面落入 L11「改变 Gate 行为语义」（Major 触发条件）——显式处置如下：
1. **L11 pre-1.0.0 括注**：L11 频率列明文「1.0.0 之前 Minor 可含有限 Breaking Change」——直接覆盖本场景；
2. **0.84.0 同域先例**：0.84.0 已在 Changed 面承载「注入预算判定姿态（lightweight hard PASS / standard-strict ADVISORY）」并以 MINOR 发布（CHANGELOG L45），且 L65 明文「Breaking changes：无（无 MUST 规则删除/重命名、无 Gate 行为语义破坏、无 governance 文件字段格式变更）」——注入预算判定姿态变更在同域已有「MINOR + 无 Gate 行为语义破坏」声明的出货先例；翻 hard 是同一判定面的同向延续（硬化/fail-closed 方向，无删除/重命名、无字段格式变更）；
3. **0.82.0/0.83.0 判定规则扩展 MINOR 先例**（CHANGELOG L145/L110）。

据此翻 hard 归入 MINOR 承载面。**边界披露**：若用户对「Gate 行为语义」持严格字面解读而不接受上述 pre-1.0.0 处置，M-0 裁定时可将翻 hard（连同 P3-3 时点绑定）经降级分支一并顺延——见降级分支选项 1a/1b。

### 条件式降级分支：0.84.1（PATCH）——M-0 用户裁定选项文本（消歧后二选一，Design R0 F-3 采纳）

原文「① 翻 hard 与 ⑧ 出槽」存在两种互斥语义，M-0 呈现给用户时 MUST 二选一（不混写）：

- **选项 1a（子项出槽——瘦身 ① 保留在 0.84.1）**：仅翻 hard 与 ⑧ 顺延 0.86.0，① 瘦身本体随 0.84.1 发布。**附随论证义务（PATCH 合规性）**：入口模板大改 + `release-projection --write` 重生成（牵动 16 投影面 + `@bootstrap-version` 标记面）是否落入 VERSIONING L38「仅修复 bug（不改变行为语义）」存疑——若判定为「不改变行为语义的注入面文本裁剪」可入 PATCH，选此项时 MUST 随选项附该论证并经 Release Reviewer 复核；收益 = RISK-057 缓解③「0.85.0 候选池已含瘦身」承诺保留兑现（兑现版本号变为 0.84.1）。
- **选项 1b（① 整体出槽——瘦身随翻 hard 一并顺延 0.86.0）**：0.84.1 仅承载纯修复（②③⑤⑥⑦余项 + ④ 清单路径），L38 合规干净、无需附随论证；**代价 = RISK-057 缓解③「0.85.0 候选池已含瘦身」承诺落空**（顺延至 0.86.0 兑现）、advisory 回弹窗进一步拉长——M-0 呈现时 MUST 显式披露此代价。

**两选项共同前提与代价**：
1. ④ 走 M-1 清单路径（不新增机检面）——因此 **④ 路径裁决时点消歧：若用户考虑降级分支则前移至 M-0 一并裁定；锁定 0.85.0 MINOR 后可后置批 1 triage/design 期**（开放点 A3 已同步）；
2. 翻 hard 属行为语义变更，PATCH 不能承载——顺延 0.86.0 时 **RISK-057/058 复评窗按回退决策树节点 R3 改挂 0.86.0**（见交付 4）；
3. 0.84.1 走「PATCH 事后追加」形态（版本规划纪律规则 4）——先例契合度经勘误（Release R0 F-4）后**成立且增强**：0.78.1 实况（roadmap L274）= **多修复/清理/测试卫生批**（FIX-282~290 族 + 范围核增 DEC-176 + 判定面①⑧出槽 0.79.0 至下一 MINOR），与本降级分支（修复批 PATCH + 判定面翻 hard 顺延下一 MINOR）**结构同型**，为贴合先例（非「单缺陷 hotfix」——原表述失真已更正）；
4. `GOVERNANCE_LEGACY_BEHAVIOR` 无法兜底——advisory 回弹防护（RISK-057 缓解①③）将继续以 advisory 姿态运行。

### 版本号占用与合规检查

- **0.85.0 全仓无预留行、无内容占用**（grep `0.85.0` 全部命中为「0.85.0 候选池/瘦身承接」引用，无路线图预留行）——首次规划占用无冲突（版本规划纪律规则 1）；
- 0.84.0 → 0.85.0 MINOR 顺延，**不跳号**；
- 路线图预留号 0.67.0~0.70.0（Loop runtime/拆分 Phase 5 等规划行）不受影响——0.85.0 不占用任何预留号。

---

## 交付 2：范围裁剪建议

### 先例形态核实（plan-tracker 版本规划节实证）

| 先例 | 载荷形态 | 任务数 | 关键教训 |
|------|---------|-------|---------|
| **0.82.0**（REL-078，DEC-195） | **全量大收尾批**——单一主题（dsh 兼容性适配）全量范围，FIX-338~346 族 + FIX-323~337 文档测试批 + FIX-313/346 | 21 | 用户明确裁决「全量范围」；M-0~M-8 标准链全走；B-1~B-8 八项行为变更集中披露 |
| **0.83.0**（REL-079，DEC-200） | **收口批**——0.82.0 发布后治理健康收尾，FIX-348/349/350 | 3 | 小批快速收口（33→21 issues）；预授权不免除 M-2 门禁实测与 M-3 双审 |
| **0.84.0**（REL-080，DEC-204） | **切片批**——AUDIT-154 切片 A，FEAT-032~040 九任务 + 发布期修复 FIX-352~355 | 9+4 | **RISK-054 并行竞态两例实测**（457a756 卷入 FEAT-033 的 TOOLS.md 改动 + 提交前工作树中间态瞬态 FAIL）；共享冻结面（registry/test_registry/snapshots/baseline）多任务叠加 regen |

### 建议：**8 项全入一版（0.85.0）、批内两批制**

8 项候选的规模介于 0.83.0（3）与 0.84.0（9）之间，单版承载可行；但候选池内部存在**硬依赖链与共享冻结面**，不允许全量并行一批，也不值得拆成两个版本（两版将使翻 hard 再等一轮发布链，RISK-057 回弹窗无谓拉长）。

#### 批 1「降噪与机检面前置」（②③④⑤⑥⑦）

| 项 | 内容 | 同批理由 |
|----|------|---------|
| ⑦ RISK-056 回放族 | 回放 fixture 重锚或版本世界参数化 | **最优先**——30 项既有失败清零后，后续所有批次的 M-2 全量验证噪音下降（每批省去逐项「既有基线 FAIL」披露） |
| ② C-01 豁免行措辞分流（源判 P1，R3/R4 已核）+ FIX-341 谓词分歧 13 行 | 判定面降噪 | 与 ⑦ 同向（审查/验证噪音收敛）；C-01 已有如实标级义务（review-REL-080-RELEASE-R3 L-8 收口态） |
| ③ FIX-356 F-1 CALIBRATION 披露行 | 披露文本 | 低风险小项；落点经 Design R0 F-8 实测**趋零**（`governance_cost.py` 不在任何注入面——见开放点 A1）；triage files 声明保留为防御性惯例 |
| ④ 测试静态版本钉机检面（DEC-213③） | M-1 清单制度化或新增机检面 | DEC-213③ 明示「同类第 5 次复现」教训的制度化窗口；若走新增机检面，与 ⑦ 同属 verify 面可同批验证 |
| ⑤ governance-status.md fixture 同族缺口（FIX-354 R1 发现） | fixture 修复 | 与 DEC-213⑦ F-05 同族（版本钉三门禁盲区） |
| ⑥ P3 族（**FEAT-038/040 遗留 + 死夹具清理 + FIRST_RUN_DEMO 19→20**；FEAT-039 F-1/F-2/F-5/P3-3/P3-4 五子项已拆出随批 2 预算面族——见批 2 表与 ⑥ 族拆分说明） | 修复/清理/计数 | **非「无依赖尾项」**——其 FEAT-039 子项与批 2 ①⑧ 同改 `injection_budget.py`（Design R0 F-2 方案 A 采纳：DEC-211③ P3-3 时点绑定翻 hard + 文件锁纪律） |

批 1 特征：无门禁语义翻转；并行度 ≤3 + RISK-054 缓解制度化（见交付 4）。**验收顺序注记（Design R0 F-5）**：④ 若走新增机检面路径，其「对当前树全量扫描 exit 0」验收 MUST 在 ⑦ 合并后执行（回放族假红/噪音基线先行清理，防互相干扰）；走 M-1 清单路径则无此依赖。

#### 批 2「瘦身与门禁翻转关键路径」（①⑧ + FEAT-039 预算面族）——串行关键路径

| 顺序 | 动作 | 依赖依据 |
|------|------|---------|
| **2.0** | **模板块构成量测（开工否决点——Analyst A1-1 编排落位）**：开工前产出 standard/strict 模板块分节 token 构成量测，结果落 EVD；**量测否决**（可压缩余量不足 3,953/4,154 tok）→ **不进入 2.1**，直接触发瘦身失败回退决策树（交付 4 节点 R1） | Design R0 F-1 采纳——无前置量测则不可达只能在 2.1 完成后暴露（批 2 返工 + RISK-057 回弹窗内注入面已被大改 + DEC-210「翻 hard 时点=瘦身后」承诺被动落空） |
| 2.1 | ① standard/strict 入口模板瘦身（**含灰度开关协议文本压缩**——DEC-212⑦/RISK-058 缓解③；resident 余量 17.4% 为显式输入——review-FEAT-040-CODE-R0 §2 保留意见） | RISK-058 缓解③④ |
| 2.2 | 瘦身后 canonical 重测（权威 extractor `sync_entry_projection.extract_canonical_templates`，DEC-211①）→ 刷新期望值；**仍不达标 → 不进入 2.3，触发回退决策树（节点 R2）** | DEC-210 论证(i) 教训：R0 度量夸大 29%——翻 hard 前数字必须以瘦身后 canonical 口径落定 |
| 2.3 | 翻 hard 执行（`BUDGET_TIER_POLICY` 翻转 + 测试期望同步——RISK-057 缓解②：改 policy 即被测出）+ **FEAT-039 P3-3 断言补充并入同一 commit**（DEC-211③ 时点绑定「0.85.0 翻 hard 时补」明文——断言面 `Feat039InjectionBudgetTests` 与翻 hard 为同一测试类的同一批断言翻转）+ 回退面形态落账（**批 2 设计期裁决、2.3 执行前落账**——与交付 5 项 1(c)/开放点 A2 对齐）；前置不可达 → 触发回退决策树（节点 R3） | DEC-210：**翻 hard 时点 = 瘦身后**；DEC-211③；Design R0 F-2 方案 A |
| 2.4 | ⑧ entry-skill 独立预算 + **FEAT-039 F-1/F-2/F-5/P3-4 预算面族**（与 ①⑧ 同改 `injection_budget.py`——按文件锁串行） | RISK-054 共享冻结面纪律；DEC-210：entry-skill 8,573 tok 属 report-only 层；review-FEAT-039-CODE-R1 实证（F-1/F-2/F-5/P3-4 均落 `injection_budget.py`） |

> **⑥ 族拆分说明（Design R0 F-2 方案 A——审查裁决采纳）**：FEAT-039 F-1/F-2/F-5/P3-3/P3-4 五子项从候选 ⑥ 拆出、随批 2 编入预算面族——P3-3 并入 2.3 翻 hard 同 commit（DEC-211③ 时点绑定），F 族与 P3-4 同 `injection_budget.py` 与 ①⑧ 文件锁串行；⑥ 其余子项（FEAT-038/040 遗留 + 死夹具清理 + FIRST_RUN_DEMO 19→20）留批 1。DEC-215② ①~⑧ 编号可追溯性保持（⑥ 子项拆分在此显式登记，编号仍指 DEC-215② 原序候选 ⑥）。

#### 规划外候补（不入版承诺，仅登记）

- **快照内容一致性校验**（review-REL-080-RELEASE-R2 F-21 后续建议：「登记为 0.85.0 候选（内容一致性校验），不要求本版修引擎」）——列候补，批 1 有余量时经 change-triage 评估入槽；
- **RISK-054 枚举类检查写盘互斥**（release-checklist-0.84.0 L128 建议）——属锁面扩展，评估放 0.85.x/0.86.0，不承诺本版。

### RISK-057/058 与模板瘦身翻 hard 交互（显式分析——任务指定）

1. **瘦身本身是 RISK-057 描述的最高危场景**：「若后续改动注入面无人看 ADVISORY 行则静默回弹」。批 2 瘦身恰是注入面大改——批 2 执行期 MUST 逐面（非只看总量）对照 `check-injection-budget` 分项表 + `sha256_16` 面级指纹（RISK-057 缓解①④在位缓解），每步可机检。
2. **RISK-058 余量收窄风险**：resident 4,957/6,000（余量 17.4%）——review-FEAT-040-CODE-R0 已预警「再叠加两次同量级文本改动即触线」。批 1 的 ③（披露行）落点经 Design R0 F-8 实测**趋零**（`governance_cost.py` 不在任何注入面——风险前提不成立，见开放点 A1）；批 2 瘦身 MUST 把灰度开关文本（+669 tok 的四个 resident 面：persona/lightweight 模板/secondary/agent-instructions）纳入压缩目标，并以 2.0 量测 + 回退决策树（R1/R2 否决点）承接不可达标分支。
3. **翻 hard 的错误数字风险**（DEC-210 原论证）：「现在翻 hard 会用错误数字阻断发布」——R0 期期望值误判 29% 先例（DEC-211① 已归档）证明数字必须来自权威 extractor。2.2 步是 2.3 步的**硬前置**，不可跳过。
4. **顺序不可倒置**：若先翻 hard 后瘦身，standard/strict 超限即 FAIL，开发期每次 check-governance 都被阻断——批 2 内部顺序为硬约束。

---

## 交付 3：里程碑提案

对照 0.84.0/0.82.0/0.83.0 发布链（DEC-197 标准链 + REL-079 最新 M-0~M-8 形态）：

| 里程碑 | 内容 | 对照先例 |
|--------|------|---------|
| **M-0 规划确认**（当前阶段） | 本文档（Release 半面）+ Analyst 半面 → **Release Reviewer + Design Reviewer 双审**（复审必达）→ 用户裁定 semver/范围/批次边界 → roadmap 0.85.0 规划行入账 | DEC-215② 路由：「版本规划/任务排布 → Release + Analyst → Release Reviewer + Design Reviewer」；0.79.0 先例（version-plan-0.79.0.md M-0 四项裁决） |
| **批 1 执行** | 逐任务 change-triage 五步门禁入账（DEC-215② 边界：产品代码任务逐个过 triage）→ 开发 → Code Reviewer 独立审查（复审必达）→ 批 1 验证噪音基线刷新（RISK-056 清零确认） | 0.84.0 切片 A 执行形态 |
| **批 2 执行**（串行关键路径） | 2.0 量测否决点（开工前模板块构成量测，落 EVD）→ 2.1 瘦身 → 2.2 canonical 重测 → 2.3 翻 hard + P3-3 同 commit（DEC-211③）+ 回退面落账 → 2.4 entry-skill 预算 + FEAT-039 预算面族 | DEC-210 翻 hard 时点约束 + Design R0 F-1/F-2 采纳 |
| **灰度/回退面**（若含行为变更——翻 hard 在版内即含） | 行为变更登记（B-x 编号 + feature-flags 文档 §2）；**回退通道形态批 2 设计期裁决、2.3 执行前落账**（与交付 5 项 1(c)/开放点 A2 统一表述——Release R0 F-6）；released 后如需回退，翻 hard 可经一次数据面 revert（`BUDGET_TIER_POLICY` 改回 advisory）+ 测试期望同步实现，属低复杂度回退 | 0.84.0 B-1~B-6 + `GOVERNANCE_LEGACY_BEHAVIOR` 先例 |
| **M-1 候选打包** | CHANGELOG 0.85.0 段 + release 三件套 + `release-projection --write` + `sync_entry_projection --write` + 版本号一致性（13 files / 4 plugin.json + e2e fixture 指针，FIX-182 后口径）→ candidate commit + `release-ledger --no-remote` = NATIVE_CANDIDATE | REL-078/079/080 M-1 同型 |
| **M-2 门禁实测** | 安静窗全量复跑 + `check-release --lineage-mode candidate`；**既有失败披露口径以批 1 后当场值刷新**（若 ⑦ 修复完成，30 项噪音应清零或逐项归因残留） | 0.82.0 安静窗 850 复跑先例；0.84.0 EVD-894 既有基线 FAIL 披露先例 |
| **M-3 双半面审查** | Release Reviewer + Code/Design Reviewer（按变更面），review-record 机录；复审必达（NEEDS_CHANGE → 同审 round+1，round≥3 → BLOCKED 升级） | DEC-197 标准链 M-3 |
| **M-4 用户停点** | transition/tag/push 逐项授权（预授权不免除 M-2/M-3——0.83.0 先例） | DEC-197 用户明确选择逐点可控 |
| **M-5 transition + tag** | release commit（单父 = candidate；manifest-only candidate_to_released + integrity）→ annotated tag（peel = transition commit） | REL-078 M-5 同型 |
| **M-6 released 门禁** | `check-release --lineage-mode released --release-commit <commit>`（执行面 FAIL 逐项归因为既有基线或修复） | REL-078 M-6 |
| **M-7 push** | master + tag 原子推送 github-https（远端 SHA 精确一致）→ `release-ledger --remote github-https` = NATIVE_RELEASED PASS | REL-071~080 七连先例 |
| **M-8 归档检测 + 快照** | `archive.py migrate --auto --dry-run`（触发器检测）→ 需要归档则迁移 → `check-archive-integrity` PASS（发布/版本 bump 收尾 MUST——完整性失败阻断完成）→ 路线图行转已发布 + session-snapshot | REL-078 M-8（22 项 evidence，integrity PASS） |

---

## 交付 4：风险面（对照 risk-log 实况，全部打开态）

### RISK-057（注入预算 advisory 回弹）× 批 2 ——本版最大风险项

- **交互**: 瘦身 = 注入面改动 = 回弹高危窗；翻 hard 是本版唯一门禁硬度变更。
- **在位缓解**（risk-log L53）: ① 分项表 + 逐层超量行每次必打印（不可隐藏）；② 翻 hard 路径被测试钉住（改 `BUDGET_TIER_POLICY` 即被测出）；③ 0.85.0 候选池已含瘦身（本规划承接）；④ sha256_16 面级指纹漂移锚。
- **本规划新增动作**: 批 2 每步（2.0~2.4）执行后立即对照分项表逐面核对 + 指纹 diff 留痕；翻 hard diff 必含测试期望值同步 + P3-3 断言同 commit（DEC-211③，否则测试红 = 自然阻断）。

### RISK-058（resident 成本 +669 tok，余量 17.4%）× 批 2

- **交互**: 瘦身不达标或批 1 ③再吃余量 → 余量耗尽后 advisory 变实际阻断或被迫放宽预算。
- **在位缓解**（risk-log L54 + DEC-212⑦）: 开关文本可再压缩（薄指针/DSH 模板为可裁剪面）；翻 hard 时点 = 瘦身后。
- **本规划新增动作**: resident 余量作为瘦身的显式验收输入——**开工前 2.0 量测步骤先行落位**（模板块分节构成对照可压缩余量 3,953/4,154 tok）；瘦身后验收标准由 2.2 重测数据定，不预先拍脑袋；③ 披露行落点经 Design R0 F-8 实测趋零（`injection_budget.py` INJECTION_BUDGET_SURFACES 全部 6 面不含 `governance_cost.py`——见开放点 A1）。

#### 瘦身失败回退决策树（单一来源——Design R0 F-4 采纳；本节为唯一权威表述，替代各处分散的「三选一/二选一」菜单）

| 触发节点 | 判定 | 动作 |
|---------|------|------|
| **R1: 2.0 量测否决** | 可压缩余量不足 3,953/4,154 tok | 不进入 2.1；升级用户裁决（选项 a/b/c） |
| **R2: 2.1 瘦身后仍不达标** | 2.2 canonical 重测 standard/strict > 预算线 | 不进入 2.3；升级用户裁决（选项 a/b/c） |
| **R3: 2.3 翻 hard 前置不可达** | 回退面形态未落账 / 2.2 后数字未落定 / 用户选择维持 advisory | 不执行翻 hard；翻 hard + P3-3（DEC-211③ 绑定同 commit）显式顺延 0.86.0，**RISK-057/058 复评窗改挂 0.86.0**（防无主承诺——Design R0 蓝军挑战 2 采纳） |

升级用户裁决统一选项集（三选一）：
- **(a) 二段瘦身**——批 2 内追加瘦身轮后重走 2.2（与 Analyst §1⑦ A1-1「二段瘦身」同源）；
- **(b) 阈值复议**——放宽/重划预算线；依据 = **DEC-211②「DEC-210 论证不依赖具体数字档位」**（decision-log L152 原文；经 L151/L152 核对，DEC-210 原文无「阈值复议」预留字样——原「DEC-210 预留选项」引申表述已更正），放宽属新裁决而非既有预留；
- **(c) 维持 advisory 并顺延**——翻 hard 显式顺延 0.86.0 + RISK-057/058 复评窗改挂 0.86.0 + 路线图行注记（本选项即降级分支 1b 的批内触发形态；与 Analyst §10.6 表述对齐——两文档统一后本节为准）。

### RISK-056（30 项既有测试失败与全量验证噪音交互）

- **实况**（risk-log L52）: test_hooks 回放 6 + test_pre_commit_review_evidence 24 + HotFactSource 16 + ExternalProjectValidation 1（风险行自载「30 项」口径，分项合计随采样面变化——按行原文引用，不自行捏合）；worktree 干净 HEAD 复跑原样复现（非新引入）；发布门禁不因此阻断（非产品面）。
- **与 0.85.0 交互**: 每批 M-2 门禁实测都会撞上这组噪音——⑦ 置于批 1 最优先，使批 2 及 M-1~M-8 发布链在低噪音基线上运行；若 ⑦ 仅部分修复，残留项在 M-2 按既有基线 FAIL 逐项归因披露（EVD-894 先例），**不包装为 PASS**。
- **修复路径提示**: 风险行已给出「回放 fixture 重锚或版本世界参数化」两个候选；与 DEC-213③ 版本钉机检面（④）同族（0.82.0 版本世界漂移），批 1 内 ④⑦ 联合设计可避免两次返工。

### RISK-055（复采样窗口）× 0.85.0 发布窗口时序

- **实况**（risk-log L51 + DEC-215①）: 验收机制已修复（FIX-356/EVD-1089：--workspace 过滤 0/344 死循环 → 156 sessions/485 turns/22 TTFA 真实命中）；首次真实判定 FAIL（22 混合样本 p50 4m39s>25s / p95 130m26s>45s）**不作终态**；关闭条件 = **新协议会话积累 ≥3 TTFA 轮后纯净复跑**（PASS→按口径关闭 / FAIL→以纯净基线再裁）。
- **时序关系**: 新协议会话自 0.84.0（2026-09-19）部署后开始积累；0.85.0 执行窗（批 1→批 2→M-1~M-8）期间样本持续自然积累——两轨道**并行不互塞**：0.85.0 发布窗 MUST NOT 阻塞于 RISK-055；纯净复跑时点大概率落在 0.85.0 执行窗中后段或发布后。
- **规划约束**: ① 若纯净复跑 FAIL → TTFA 优化立项/阈值复议届时为选项，**只作为 0.86.0 输入评估，不挤入 0.85.0 范围**（范围纪律）；② 0.85.0 期间任何 TTFA 相关验证 MUST 成对报告 TTFA+TTW + 携带 DEC-205 下界声明 + 对照口径 = 验收时点重新生成基线（RISK-052 不可跨时点 diff——风险行自载）；③ 0.85.0 的 M-2 全量验证若与纯净复跑采样窗重叠，注意采样污染——复采样跑批应避开 M-2 安静窗（同为治理活数据消费者）。

### RISK-054（并行提交竞态——批任务数多时加剧）

- **实况**（risk-log L50）: 0.84.0 实测两例（457a756 归属错位内容无损；瞬态 FAIL 复跑全绿）；共享冻结面 = registry/test_registry/snapshots/baseline（后完成者叠加 regen）。
- **与 0.85.0 交互**: 8 项两批制的直接动机之一——批 1 并行度 ≤3（对比 0.84.0 九任务高并行）；①⑧ 共享 `BUDGET_TIER_POLICY`/期望值冻结面 → 同批串行。
- **在位缓解 + 规划新增动作**: 既有缓解（提交前 `git status --porcelain` staged 清单核对仅含本任务文件 + 共享冻结面后完成者二次校验 regen 零漂移）升级为本版 M-set 制度化前置；「枚举类检查写盘互斥」锁面扩展（checklist-0.84.0 建议）列规划外候补评估。

### 跨版本携带风险（如实披露，本版不关闭）

RISK-036 / RISK-039（均 2026-09-30 复评窗）/ **RISK-046（打开——FEAT-013 根因修复已交付但「维持打开至 09-30 复评窗随批收口」）/ RISK-047（打开·登记观察——review-record force 覆盖 evidence 行语义与 CLI 出路缺口）/ RISK-048（打开·登记观察——test_loop_runtime_claims 性能阈值环境敏感）——三者复评窗均 2026-09-30（与 RISK-039 同窗），落在 0.85.0 执行窗内，M-2/M-4 排期时预留复评位**（Release R0 F-2 采纳）/ RISK-044（缓解中，DEC-177②）/ RISK-050（2026-10-31）/ RISK-052（成本口径时点漂移）/ RISK-053（**FEAT-037 P3×6 薄指针投影族**——主体已随 0.84.0 FEAT-040 处置（P3-1/2/4），残余随 0.85.0+ 复评窗，风险行独立裁决；**≠ 批 1 候选 ⑥**——Release R0 F-5 消歧）。**0.85.0 规划不含任何 RISK 关闭承诺**（本行为重点项非穷尽——打开态全集以 risk-log 实况为准）。

---

## 交付 5：发布门禁前置清单（规划面）

本版本特有 / 本版强化的 gate 前置：

| # | 前置项 | 时点 | 依据 |
|---|--------|------|------|
| 1 | **check-injection-budget ADVISORY→hard 翻转三件套**: (a) 瘦身后 canonical 重测刷新期望值（权威 extractor）；(b) `BUDGET_TIER_POLICY` 翻转 + 测试期望同步 + FEAT-039 P3-3 断言同 commit（DEC-211③）；(c) 回退面形态**批 2 设计期裁决、2.3 执行前落账**（与交付 3/开放点 A2 对齐——Release R0 F-6 统一表述） | 批 2.3（瘦身后——DEC-210 时点）；未满足 → 触发瘦身失败回退决策树（交付 4 节点 R1~R3） | DEC-210/211①③；RISK-057 缓解② |
| 2 | **既有失败披露口径刷新**: 批 1 ⑦ 修复后，M-2 全量验证基线以当场值重载——30 项噪音清零确认或残留逐项归因 | 批 1 完成后、M-2 前 | RISK-056；EVD-894 先例 |
| 3 | **RISK-054 制度化前置**: 每次提交前 staged 清单核对 + 共享冻结面 regen 零漂移二次校验（写入本版任务验收字段） | 批 1/批 2 全程 | risk-log L50 缓解 |
| 4 | **注入面改动指纹留痕**: 凡触及 resident 面（persona/入口模板/薄指针/agent-instructions）的任务，triage `files` 必须显式声明（含 `checks/injection_budget.py`——review-FEAT-039-CODE-R1 P3-7 冲突检测漏面教训）+ 提交后 sha256_16 指纹 diff | 批 1 ③ / 批 2 全程 | DEC-211③；RISK-057 缓解④ |
| 5 | 版本号一致性全量面（13 files / 4 plugin.json + e2e fixture 版本指针） | M-1 | FIX-182 口径；V-Gate 版本号一致性项 |
| 6 | release-ledger candidate/released 两态 + release-projection check-only PASS | M-1 / M-6 | stage-release 退出条件（ADR-010） |
| 7 | quality-tools 结构化记录（Ruff/mypy 未安装 = NOT_RUN 如实记录，不包装 PASS） | M-2 | ADR-010 |
| 8 | hooks_drift 4 项披露（用户一次性重装命令移交中——DEC-213④ 接受态，非阻断但 M-2 披露面） | M-2 | DEC-213④；session-snapshot 优先级 3 |
| 9 | 归档触发检测（dry-run → 迁移 → integrity PASS） | M-8 | ADR-006/007；发布收尾 MUST |
| 10 | 「本版不发布什么」显式记录（对照 0.84.0 checklist L25 先例）: 切片 B/C、TTFA 优化立项（待纯净复跑结论）、快照一致性校验（候补）、写盘互斥锁面（候补）、任何 RISK 关闭声明 | M-0 后随范围裁定落账 | Amazon 显式排除实践；release-checklist-0.84.0 L25 |

---

## 交付 6：roadmap 行提案（plan-tracker `## 版本规划` 表新增行）

对照既有「规划」状态行格式（0.67.0~0.70.0 行 + 0.79.0 行——6 列逐列对齐：版本 | 状态 | 预计日期 | 核心范围 | 包含 Tier/Layer（本批承载依赖/任务 ID）| 关键交付物（语义与链形态））：

```
| **0.85.0** | **规划** | **—** | **治理降噪第二波执行批——批 1 降噪/机检面前置（⑦ RISK-056 回放族 + ② C-01 豁免行措辞分流〔源判 P1〕+ FIX-341 谓词分歧 13 行 + ③ FIX-356 F-1 CALIBRATION 披露行 + ④ 测试静态版本钉机检面〔DEC-213③〕+ ⑤ governance-status.md fixture 同族缺口 + ⑥ P3 族 FEAT-038/040 遗留/死夹具/FIRST_RUN_DEMO 19→20〔FEAT-039 F-1/F-2/F-5/P3-3/P3-4 五子项拆出批 2〕）→ 批 2 瘦身与门禁翻转关键路径（2.0 模板块构成量测否决点 → ① standard/strict 模板瘦身 + 灰度开关文本压缩 → canonical 重测 → check-injection-budget standard/strict 翻 hard〔DEC-210 时点=瘦身后；P3-3 断言同 commit——DEC-211③〕+ FEAT-039 预算面族 F-1/F-2/F-5/P3-4 + ⑧ entry-skill 独立预算）** | **DEC-210/211/212/213/215②, RISK-054~058, REL-080（0.84.0 遗留候选池）, FIX-356 F-1** | **MINOR（判定姿态翻转 + 机检面新增；VERSIONING L11 处置 = pre-1.0.0 括注 + 0.84.0 同域先例——若用户裁定降级分支则 0.84.1 PATCH 且翻 hard+P3-3 顺延 0.86.0、RISK-057/058 复评窗改挂）；M-0 双半面规划双审 → 两批执行（批 1 并行≤3 / 批 2 串行含回退决策树 R1~R3 否决点）→ M-0~M-8 标准链（DEC-197）；行为变更面 = 翻 hard B-x（回退通道形态批 2 设计期裁决、2.3 执行前落账）；不关闭任何 RISK** |
```

> 注入时点: M-0 用户裁定 semver/范围后由 Coordinator 写入（本任务不写 `.governance/`——规划面边界）。若用户采纳降级分支 0.84.1，此行语义列按分支条件改写后入账。

---

## 假设与开放点（显式标注——非事实，需后续裁决/验证）

| # | 假设/开放点 | 状态 | 兑现机制 |
|---|------------|------|---------|
| A1 | 批 1 ③（CALIBRATION 披露行）落点面——**Design R0 F-8 实测已澄清**：`injection_budget.py` INJECTION_BUDGET_SURFACES 全部 6 面均不含 `governance_cost.py`，CALIBRATION 增键仅改 report 输出（模块内消费）——③ 落 resident 注入面的前提不成立，风险趋零 | 审查实测（预期 triage 时直接关闭） | triage files 声明保留为防御性惯例；「挪批 2 同窗」预案撤销 |
| A2 | 翻 hard 的回退通道形态未定——`GOVERNANCE_LEGACY_BEHAVIOR` 的 LEGACY_REVERTS 仅允许 performance 类 + 与 SAFETY_INVARIANTS 不共享 FEAT（DEC-212②）；翻 hard 属 performance 防护还是须保持 hard 的安全语义，**事实源未裁决** | 开放点 | **批 2 设计期裁决、2.3 执行前落账**（与交付 3/交付 5 项 1(c) 统一表述）；裁决前本文档不假定可经 legacy 开关回退，仅确认数据面 revert（policy 改回 + 测试同步）可行 |
| A3 | ④ 走「M-1 检查清单」还是「新增机检面」未定——影响 semver 分支（MINOR vs 0.84.1）与 M-1 工作量 | 开放点（时点已消歧——Design R0 F-3） | **若用户考虑降级分支则前移 M-0 一并裁定；锁定 0.85.0 MINOR 后可后置批 1 triage/design 期**；本文档 semver 主建议按含新增机检面（较强分支）给出 |
| A4 | 瘦身后 standard/strict 是否降至预算线（6,000）以下未知——9,953/10,154 → ? 需 2.2 重测 | 假设（数据未生成；2.0 量测为前置否决点） | 2.0 量测否决或 2.2 重测不达标 → 触发瘦身失败回退决策树（交付 4 节点 R1/R2，选项 a/b/c）——不预设结果 |
| A5 | RISK-055 纯净复跑 ≥3 TTFA 轮的积累速度未知（依赖真实新协议会话频次） | 假设 | 独立轨道观察；不进 0.85.0 关键路径 |
| A6 | DEC-215② 候选序 ①~⑧ 与本文档批次归属的映射为 Release 半面建议——Analyst 半面若有不同归序，以双审合并后的 M-0 裁决为准 | 假设 | 双审合并 |

---

## 硬门槛自检（本任务）

| 门槛项 | 判定 | 依据 |
|--------|------|------|
| 版本号 semver 合规论证充分 | **PASS** | 不跳号（0.84.0→0.85.0）；无预留占用（grep 实证）；bump 理由对照候选内容逐项定性（交付 1 表）；条款依据链 = **VERSIONING L11（Major 触发字面落入 → pre-1.0.0 括注「1.0.0 之前 Minor 可含有限 Breaking Change」+ 0.84.0 同域先例 CHANGELOG L45/L65 处置——R0 F-1 采纳）** + L12/L37/L38 + 三先例（0.82.0 L145/0.83.0 L110/0.84.0 L45/L65）；修订前自检行未含 L11 为依据链缺口，已补全 |
| 范围与路线图/风险状态一致 | **PASS** | 候选池 = DEC-215② 原序 8 项（snapshot + decision-log L157 双源核对）；RISK-054~058 全部按 risk-log L50~54 实况引用（含「30 项口径随采样面变化」原样保留）；无 RISK 关闭承诺 |
| 先例形态经 plan-tracker 实证 | **PASS** | 0.82.0（21 任务全量批）/0.83.0（3 任务收口批）/0.84.0（9 任务切片批）三行 L277~279 逐行核实；M-0~M-8 链形态经 REL-071/078/079 完成行核实 |
| 不修改产品代码 / 不执行发布动作 / 不改 .governance/ | **PASS** | 本文档为唯一写入物（`docs/release/version-plan-0.85.0.md`）；roadmap 行以提案文本交付，写入留给 M-0 裁决后 |
