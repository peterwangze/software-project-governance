# AUDIT-155 — loop 模式线性 Gate 行为偏差根因分析（行为面：注入链/呈现层实证）

- **日期**: 2026-09-26
- **执行**: Analyst Agent（只读定位分析；AUDIT-155）
- **对象版本**: SKILL.md frontmatter `version: 0.89.0`（bootstrap 模板 `@bootstrap-version: 0.89.0`）
- **前序锚点**: DEC-097（2026-07-10，归档 `archive/decisions/decisions-v0.1.0-0.64.0.md` L11-16）→ 0.65.0 实现层 7/7（FX-188~194，EVD-684）→ AUDIT-143（2026-08-17，`audit-143-loop-planning-behavior-gap-0.74.0.md`）→ 0.74/0.75 修复链（FIX-251/252/253/254，FIX-253=REQ-112 关键行为规则注入面）→ 0.84.0 切片 A（FEAT-032~040，REL-080，2026-09-19）
- **性质**: 修复后复诊——AUDIT-143 修复链解决了「行为规则是否到达注入面」，用户 2026-09-26 反馈**呈现框架本身**仍以线性 Gate 推进为主要目标语言。本审计只做行为面（注入链/呈现层）实证定位，不提修改方案（方案属 AUDIT-156 结构面票）。
- **R0 修正**: 2026-09-27 按 Design Review R0（`docs/reviews/review-AUDIT-155-156-DESIGN-R0.md` = NEEDS_CHANGE，round<3 触发器 T1）修复行为面侧缺陷 D-2/D-3/D-4；D-1 属结构面报告（`audit-155-loop-gate-bias-structure-0.89.0.md`），由 Architect 并行修复。修正处均以「R0 修正」标注；原结构与已证实内容不变。
- **边界**: 全程只读；除本报告外零文件修改；未触碰 `.governance/` 治理记录。

---

## 1. 执行摘要

用户反馈的四个观察面（状态行以 Gate 为主坐标 / 推荐总指向推进 Gate / agent 话术把过 Gate 说成阶段目标 / Gate-阶段强绑定命名）**全部在产品注入面与呈现层找到 ≥2 个实证注入点**。

三个假设的验证结论：

| 假设 | 结论 | 一句话依据 |
|---|---|---|
| H1 呈现框架从未 loop 化 | **证实** | 0.74/0.75 修复链把「行为规则」（复审/推荐/机录/真实环境防护契约）送进注入面——现行分布：persona L66-71 五条 + SKILL.md L225-232 四条（双点差异见 §3 表 FIX-253 行 R0 修正），但**状态坐标系语言**（模式确认句/状态投影/协议 M6/能力层总入口/数据结构）全部保持线性 Gate 形态；注入面 loop 语言密度 = **0** |
| H2 推荐逻辑含「下一 Gate」排序倾向 | **部分证伪 + 呈现层部分证实** | 推荐排序是依赖+优先级+版本驱动（`task_priority.py` L1696、`bootstrap_aggregate.py` L692-737、`_status_next_steps` L11056-11062），**无显式 Gate 推进倾向**；但 bootstrap 聚合把 `gates.next_gate`（第一个 pending Gate）作为一等数据面输出（L296/L313-315/L644/L877-879），且 loop 状态零投影——线性倾向在**状态投影字段语义层**，不在推荐排序层 |
| H3 线性话术密度远高于 loop 话术 | **证实（修正表述：分层隔离）** | 不是总量对比（全 skills/ loop 词 3420 > 线性短语 45），而是**分层隔离**：注入面/协议层/呈现层 loop 密度=0（persona 0、SKILL.md 0、behavior-protocol.md 0、入口模板 0、main-workflow 0），loop 语言集中于 `infra/*.py` 工具/测试层（3300+ 处）与第四层按需文件（7 个 review SKILL 的 Loop Role 段、loop-role-mapping.md）。agent 每会话必然接触的语言 100% 是 Gate 语言 |

**一句话总结**：DEC-097 决策（loop 为唯一模型）与 0.65.0 实现把 loop 语义写进了**工具层、registry 数据和按需参考文件**；但产品的**第一投影链**（每会话必然到达 agent 上下文的 persona → bootstrap 状态行 → SKILL §B0 → plan-tracker 结构 → bootstrap 聚合输出）自始至终只有一套坐标语言——线性 Gate/阶段。CHANGELOG 0.65.0 宣称 "the linear G1-G11 stage model is superseded"，而 core/lifecycle.md 的最后修改时间是 2026-05-01（DEC-097 之前两个月）——重构从未触及呈现层。agent 不是「违背了 loop 模型」，而是**从未在注入面见过 loop 模型**：它如实继承了唯一可见的坐标系，并把「过 Gate」当作可见的进步事件来汇报（后半句为机制推断——会话实时输出不落盘，无行为样本直接取证，见 §8 未验证项 1/3；R0 修正加限定，2026-09-27）。

---

## 2. 用户观察面实证定位（观察面 → 注入点）

### 观察面 1：状态行/治理面板以 Gate 为主展示

| # | 注入点 | 位置 | 机制 |
|---|---|---|---|
| 1-1 | **模式确认句 canonical 定义** | `skills/software-project-governance/SKILL.md` L90（§B0）：``Governance: {trigger_mode} x {permission_mode} \| stage: {stage}, Gate {gate}: {status}, {risk_count} risk(s)`` | 每会话必输出的一句状态确认，把 `stage` + `Gate {gate}: {status}` 定义为项目的标准坐标。always-on 模式使用完整句式（L90）；on-demand/silent-track 为变体（L91-92——前者仅展开 `Governance: on-demand x {permission_mode}` 不含 Gate 状态段，后者不输出面板）（R0 修正：原表述「全部三个触发模式共用此句式定义」与 SKILL.md L89-92 实况不符，2026-09-27） |
| 1-2 | **注入模板投影链（canonical source）** | `commands/governance-init.md` L222（lightweight 模板）、L278（standard 模板 Step 0 正文两次）、L369（secondary-thin 模板）——同一句式四套模板重复投影 | Step 7 注入模板是 bootstrap 的唯一事实源（FIX-011），该句式经 sync_entry_projection 渲染进仓库根 `CLAUDE.md`（Gate=12 处/loop=0）与 `AGENTS.md`（Gate=4/loop=0），并写入 `adapters/dsh/AGENTS.md.template` L27 |
| 1-3 | **DSH thin pointer 项目入口** | `adapters/dsh/AGENTS.md.template` L21（「知道阶段/Gate/模式？」）、L27（always-on 确认句全文） | DSH 平台每个以本仓为工作区的会话自动注入 |
| 1-4 | **status 命令文本面板** | `infra/verify_workflow.py` L11190（`Stage:` 面板行）、L11194（`Latest Gate:` 面板行）、L11528-11544（`cmd_gates` 完整 Gate 队列面板） | Scenario F 状态展示以 Stage/Gate 为主行 |
| 1-5 | **bootstrap 聚合 gates 面** | `infra/bootstrap_aggregate.py` L644（`payload["gates"] = parse_gate_summary(...)`）、L877-879（text 输出 `"gates: passed %s/%s ...; next %s"`） | FEAT-033 快路径是每会话**第二动作**（SKILL.md L72），gates 面是其必输出面 |

**狗粮自证**：本审计会话自身的 DSH system prompt 即 `agent.cordis.yml.template` L51-74 的渲染产物，其「模式确认」条目（对应模板 L62）即指向上述 Gate 句式。

### 观察面 2：候选推荐/下一步建议总指向「推进下一个 Gate」类动作

| # | 注入点 | 位置 | 机制 |
|---|---|---|---|
| 2-1 | **`next_gate` 字段语义** | `bootstrap_aggregate.py` L296（`next_gate = None` 初始化）、L313-314（`if next_gate is None and bucket == "pending": next_gate = cells[gate_idx]`）、L291 docstring（"the first pending gate id"——R0 勘正：原引 L292，实为 L291，2026-09-27） | 「下一个 Gate」作为一等结构化字段进入热数据投影；text 面渲染为 `next %s`（L877-879）。「下一个待过 Gate」本身就是线性推进表达 |
| 2-2 | **M7.4 step 6b 推荐语境词** | `references/behavior-protocol.md` L588：「从 unblocked 任务 + 当前最高优先级未完成任务中，**结合版本依赖链和当前项目阶段**，选择最合理的 1~3 个候选下一步」 | 推荐规则本身依赖驱动（无 Gate 排序），但「当前项目阶段」作为推荐语境把阶段坐标带入每一次推荐的语言框架 |
| 2-3 | **M6 通过语义绑定** | `references/behavior-protocol.md` L426：passed = 「所有检查满足，**进入下一阶段**」 | 协议层把「过 Gate」的**语义定义**直接写为「进入下一阶段」——agent 描述推荐与进展时可用的官方词汇表中，过 Gate = 阶段推进 |
| 2-4 | **候选呈现无 loop 坐标可用** | 注入面 loop 语言密度=0（§4 密度表）；`loop-exit-candidates.json` 的 `exit_events_consumed: 0`（§6 面 7） | 即使推荐数据是任务依赖驱动，agent 向用户**包装**推荐时可用的坐标系语言只有 Gate/阶段（分析推断，见 §5 未验证项 3） |

### 观察面 3：agent 推进话术把「进入下一阶段/通过 Gate X」当里程碑

| # | 注入点 | 位置 | 机制 |
|---|---|---|---|
| 3-1 | **M6 Gate 执行规则** | `behavior-protocol.md` L441：「Gate 未通过 → **MUST NOT** 声称进入下一阶段」；L426-429（passed/passed-with-conditions/blocked/passed-on-entry 四态全部以「下一阶段」为参照系定义） | 协议以 MUST-NOT 级别强化「过 Gate ↔ 进入下一阶段」绑定；agent 的里程碑话术是对该定义的忠实执行 |
| 3-2 | **阶段跳跃防护的计数语言** | `SKILL.md` L146（「跳过阶段跳跃防护 = 流程违规」）；L161（关键决策清单含「阶段跳跃（跳过 Gate）」）；`commands/governance-init.md` L295-296（standard 模板 Step 3 全文：「你确定要跳过 {n-1} 个前置阶段直接进入 {requested_stage}？」） | 线性预设以最强语气（MANDATORY/流程违规）注入，且 `{n-1} 个前置阶段` 是全序队列计数语言 |
| 3-3 | **能力层总入口的线性推进规则** | `skills/main-workflow/SKILL.md` L74：「**默认顺序**：1→2→3→...→11，前一阶段 Gate 通过后进入下一阶段」；L56「## 11 阶段总览」；L38（Coordinator 职责：「阶段推进、Gate 把控」）；L127（跨层调用「传递 Gate 状态」） | 场景匹配必经文件明文规定线性顺序；该文件 loop 词频 = **0** |
| 3-4 | **11 个 stage-* 子工作流的 Gate 映射节** | 例：`skills/stage-research/SKILL.md` L36（进入条件「G1 通过」）、L100-102（「本阶段对应 **G2 — 调研完成**」+ Gate 检查项表） | 每个 stage SKILL 以 G 编号自证线性位次；stage-* 全目录 loop 词频 = 0 |

### 观察面 4：Gate/阶段命名体系强绑定（G1 立项→…→G11 维护）

| # | 注入点 | 位置 | 机制 |
|---|---|---|---|
| 4-1 | **数据结构本身是线性的** | `.governance/plan-tracker.md` `## Gate 状态跟踪` 节：单一全局 11-Gate 队列表（`| G1 | → 调研 | passed-on-entry | ...` 至 `| G11 | → 下一轮 | passed |`） | plan-tracker 的 Gate 表以「阶段转换」为列定义——数据模型层面 Gate 与阶段一一绑定；`## 项目配置` 的「当前阶段」为单值字段（bootstrap `parse_project_config` L627 读取为 `project.stage`） |
| 4-2 | **核心层定义未随重构更新** | `core/lifecycle.md`（11 阶段生命周期定义，文件最后修改 **2026-05-01 22:05:56**，早于 DEC-097 2026-07-10）；`core/stage-gates.md`（Gate 检查规则）；`SKILL.md` L425-426 参考表（「core/lifecycle.md → 11 阶段生命周期定义」「core/stage-gates.md → Gate 检查规则」） | 0.65.0 重构交付了 `core/loop-engineering-registry.json`（loop_gate_semantics G1-G11 注解），但核心层的阶段/Gate 定义文档保持 pre-DEC-097 形态 |
| 4-3 | **M6 profile 裁剪表** | `behavior-protocol.md` L435-437（lightweight「G1+G2 合并，G3-G5 跳过…」；standard「全部 11 个 Gate」；strict「全部 11 个 Gate，不允许 passed-with-conditions」） | 即使最激进的 profile 也是对同一条 11-Gate 线性队列做裁剪，而非环化 |
| 4-4 | **strict 模板的极线性化** | `commands/governance-init.md` L339（strict 差异段：「**阶段纪律**：阶段间不允许重叠；阶段回退需决策记录 + 影响分析」）、L335（「每个 Gate 评分 0~5 分」） | strict profile 把线性阶段模型进一步硬化（禁止重叠=纯瀑布语义） |

---

## 3. 历史链对照：决策面 vs 行为面

| 时点 | 决策/交付 | 落点层 | 呈现层是否同步 |
|---|---|---|---|
| 2026-07-10 | DEC-097（`archive/decisions/decisions-v0.1.0-0.64.0.md` L11-16）：「重构式——loop 为唯一模型……核心洞察：gate=loop 的退出条件+下一 loop 入环条件，gate 失败不『失败阶段』而是退回 loop 再迭代」 | 决策 | — |
| 2026-07-10 | 0.65.0 FX-188~194（EVD-684）：`core/loop-engineering-registry.json` + `infra/loop_engine.py`/`loop_migration.py`/`flow_unit_derive.py`/`loop_health.py` + 7 个 review SKILL 加 Loop Role 段（FX-194） | 工具层+数据层+按需参考层 | **否**——CHANGELOG 0.65.0 宣称 "linear G1-G11 stage model is superseded"，但同版本未改 SKILL.md §B0/M6/main-workflow/core/lifecycle.md（lifecycle.md mtime 2026-05-01 为证） |
| 2026-08-17 | AUDIT-143：诊断三环节断裂（注入层/接线层/数据层），REQ-107~114 | 诊断 | — |
| 2026-08~09 | FIX-251/252/253/254：FIX-253（REQ-112）将关键行为契约写入注入面。**现行形态为双点分布（R0 修正——原表述「四条含机录写入两处」与现状不符，2026-09-27）**：persona（`agent.cordis.yml.template` L66-71）携带**五条**压缩契约（复审必达/完成必推荐/选项必带依据/审查结论必机录/真实环境必防护）；SKILL.md L225-232 为 canonical 投影定义处、当前承载**四条**（复审必达/完成必推荐/选项必带依据/真实环境必防护——全文 grep `机录` 0 命中），「审查结论必机录」的 canonical 定义在 behavior-protocol.md M7.4 step 4.6（C8），persona 第 4 条即其压缩形式（behavior-protocol.md L558 明载「step 4.6 (C8)……压缩形式由 DSH persona 契约块第 4 行携带」）；`check-injection-contract` 锚点守护（L558）。条目演化史：真实环境必防护与 FIX-271（M7.7 协议本体，2026-08-23，EVD-FIX-271-1）及其后注入面同步修订（FIX-274，EVD-FIX-274-R1：SKILL 契约段预算守卫 DEC-162 上限 2560B/实测 2446B、`check-injection-contract` 27 锚 PASS）时间一致；FIX-253 时点的原始条数未逐版考古（§8 未验证项 6） | 注入面（行为规则） | 行为规则到达注入面 ✅（反而更强：机录契约的注入面形态在 persona 第 4 条）；但注入的是**行为契约**，不是**状态语言**——persona 全文 Gate=0 且 loop=0（§4），坐标语言由下游 SKILL §B0/plan-tracker/bootstrap 输出供给，仍为线性 Gate |
| 2026-09-19 | 0.84.0 切片 A（FEAT-032~040，CHANGELOG [0.84.0]）：FEAT-033 `governance-bootstrap` 单命令聚合（358ms/4937B）成为每会话第二动作 | 呈现层 | **反向固化**——bootstrap 聚合把 `gates.next_gate` 选为 gates 面的摘要字段（L296/L313-315），loop 状态不在聚合面中；轻量化让线性 Gate 坐标系成为热路径上**唯一**被程序投影的状态 |

**AUDIT-143 修复链与本审计的关系**（H1 的验证核心）：AUDIT-143 §2.0.1 判定「注入链不含 loop/推荐行为规则」；FIX-253 精准修复了这一点（本审计实证 persona L66-71 确已携带契约——现状五条，双点分布见上行 R0 修正）。但 AUDIT-143 的诊断框架本身以「行为规则是否到达注入面」为粒度，未把「**状态呈现语言以什么为坐标系**」当作独立病变。用户 2026-09-26 的反馈指向的正是后者：规则对了，语言没变。

> **R0 修正（版本计数口径，2026-09-27，对照审查 D-2）**：决策停滞期的版本计数修正为「**32 个发布版本条目（0.65.0~0.89.0，`project/CHANGELOG.md` 的 `## [x.y.z]` 段头实计，含 patch/rc 变体）**；其中 0.75.0~0.89.0 区间 16 条」。该「15 个版本」表述实际出现于结构面报告（`audit-155-loop-gate-bias-structure-0.89.0.md` L80「决策通过 15 个版本」/L210「fifteen-version 停滞」），行为面原稿无此句（审查报告 §8 D-2 的行为面定位偏差，在此如实注明供 R1 复核）；行为面本节以下表格与两报告汇合归因引用停滞期时，一律以上述 32 条目口径为准。

---

## 4. 语言密度考古（可复现 grep 统计）

### 4.1 统计命令（pwsh，工作区根执行）

```powershell
$dirs = @("skills","agents","commands","agent-presets","adapters")
# 线性话术 pattern 集
$lin = '下一阶段','下一个 Gate','下一 Gate','进入.{0,6}阶段','推进.{0,8}Gate','next [Gg]ate','通过 [Gg]ate','Gate \{(n|gate)\}','阶段跳跃'
# loop 话术 pattern 集
$loop = 'loop','迭代','back-edge','持续演进','loop-exit','loop_state','flow-unit'
# 逐目录 × 逐 pattern 对 *.md,*.py,*.yml,*.yaml,*.template,*.json 计数
```

注：`adapters/dsh/AGENTS.md.template` 等个别文件 pwsh 读取被沙箱拒绝（Access denied），该目录首轮计数失真；被拒文件已用 grep/read 工具单独实证并在下表注明。`agent-presets/governance/agent.cordis.yml.template` 同样 pwsh 被拒，以 grep 工具计数为准。

### 4.2 注入面/协议层逐文件词频（决定行为的层）

| 文件（角色） | Gate 类计数 | stage/阶段 | loop/迭代 | 依据 |
|---|---|---|---|---|
| `agent-presets/governance/agent.cordis.yml.template`（DSH persona，会话 system 级） | **0** | **0** | **0**（「环」仅出现于「环境」一词，grep 实证 L59/L71） | grep `[Gg]ate` 全文件 0 匹配；`loop\|Loop\|迭代\|环` 仅 2 处「环境」 |
| `skills/software-project-governance/SKILL.md`（入口层，489 行） | 19 | stage 6 + 阶段 10 | **0** / 0（flow-unit 0、back-edge 0、loop-rollup 0） | pwsh regex 计数 |
| 仓库根 `CLAUDE.md`（主入口投影产物） | 12 | 8 | **0** | pwsh 计数 |
| 仓库根 `AGENTS.md`（次要入口薄指针） | 4 | 3 | **0** | pwsh 计数 |
| `commands/governance-init.md`（注入模板 canonical source） | Gate {n|gate} 3 + 通过 Gate 类多处（L201/208/222/233/241/247/250/272/284/285/293/295/301/317/335/339/352/357/363/369） | 阶段跳跃 2 | **0** | grep L171-379 逐行实证；pwsh 对该文件被拒 |
| `references/behavior-protocol.md`（行为协议本体，835 行） | **40** | **21** | **0** / **0** | pwsh regex 计数 |
| `references/interaction-boundary.md` | 9 | 11 | **0** / 0（推荐 6） | pwsh 计数 |
| `skills/main-workflow/SKILL.md`（能力层总入口） | Gate 类 13 处（含 L74 线性规则） | 阶段 15+ | **0** | grep 33 处命中逐行分类 |
| `agents/` 全目录（15 角色定义） | 8 | 4 | **0** | grep 逐条（architect L49、coordinator L22/37、maintenance L43/69、governance-developer L26、release L70、requirement-reviewer L77） |
| `commands/` 其余（governance.md L39、governance/overview.md L126） | 阶段跳跃 2、Gate {n} 3 | — | **0** | grep |
| `agent-presets/governance/preset.yml` | 0 | 0 | 0（纯配置） | grep 0 匹配 |

### 4.3 全 skills/ 目录分布（loop 语言在哪儿）

- 线性短语合计 **45** 处（280 个 md/py/yml 文件）：下一阶段 14、进入{0,6}阶段 18、推进{0,8}Gate 5、通过 Gate 3、Gate {n|gate} 1、阶段跳跃 4。
- loop 词合计 **3420** 处——但 **Top15 全部是 `infra/*.py` 实现与测试**：verify_workflow.py 225、test_loop_runtime_claims.py 172、loop_gate_processor.py 168、test_loop_gate_processor.py 168、flow_unit_runtime_v2.py 134、loop_engine.py 129、test_loop_telemetry.py 102、loop_paro_engine.py 101、loop_runtime_claims.py 98、test_verify_workflow.py 93、test_loop_paro_engine.py 89、test_flow_unit_runtime_v2.py 84、test_loop_engine_round.py 77、loop_migration_plan.py 77、test_loop_rollup.py 69。
- **markdown 层 loop 分布（68 个 .md 中仅 11 个含 loop，合计约 120 处）**：`references/loop-role-mapping.md` 41（FX-194 共享参考）、`infra/TOOLS.md` 14、7 个 review SKILL 各 8~10（`release-review` 10 / `requirement-review` 9 / `retro-review` 9 / `code-review` 8 / `design-review` 8 / `tech-review` 8 / `test-review` 8——FX-194 Loop Role 段）、`references/evidence-id-prefix-conventions.md` 4、`core/task-gate-model.md` 1。
- **主 SKILL.md、main-workflow、core/lifecycle.md、core/stage-gates.md、11 个 stage-* SKILL、references/behavior-protocol.md、references/interaction-boundary.md 的 loop 计数全部为 0**。
- 仓库根入口两文件（CLAUDE.md/AGENTS.md）loop 计数 = 0。

**密度结论**：在「agent 每会话必然接触」的语言面（persona→入口→SKILL→协议→聚合输出）上，线性 Gate/阶段语言与 loop 语言的计数对比为 **约 112 : 0**；loop 语言存在于 agent 需要第三次主动读取才可见的层（review SKILL Loop Role 段、loop-role-mapping.md）与 agent 不直接消费的实现层（infra/*.py）。H3 的「语言密度决定行为倾向」机制成立，但准确机制是**分层隔离**而非总量对比。

### 4.4 里程碑化表述的具体出处（「过 Gate」=「达成阶段」）

1. `references/behavior-protocol.md` L426——passed 的语义定义即「所有检查满足，进入下一阶段」：**canonical 出处**。
2. `references/behavior-protocol.md` L441——「Gate 未通过 → MUST NOT 声称进入下一阶段」：以违规条款反向强化绑定。
3. `skills/main-workflow/SKILL.md` L74——「前一阶段 Gate 通过后进入下一阶段」：能力层总入口的推进规则。
4. `skills/software-project-governance/core/stage-gates.md` / `core/audit-framework.md`（各含「下一阶段」1/3 处）——核心层定义。
5. `commands/governance-init.md` L295-296——阶段跳跃防护警告文本（「跳过 {n-1} 个前置阶段直接进入 {requested_stage}」）。
6. `references/onboarding.md`（「进入{0,6}阶段」3 处）——中途接入协议以阶段为坐标。

---

## 5. H1/H2/H3 逐条验证

### H1 —— 「呈现框架本身从未被 loop 化，注入链让 Gate 成为项目第一投影」→ **证实**

验证过程（非假设）：

1. **行为规则确已到达注入面**（AUDIT-143 修复链生效的实证；R0 修正表述——原稿此处「五条/四条」混用且以 L225-232 单点 canonical 概括两处，与现状不符，2026-09-27）：注入面现状为**双点分布**——`agent.cordis.yml.template` L66-71 携带**五条**压缩契约（复审必达/完成必推荐/选项必带依据/审查结论必机录/真实环境必防护）；`SKILL.md` L225-232 为 canonical 投影定义处、当前承载**四条**（复审必达/完成必推荐/选项必带依据/真实环境必防护，全文 grep `机录` 0 命中）——「审查结论必机录」的 canonical 定义在 behavior-protocol.md M7.4 step 4.6（C8）/L558，persona 第 4 条即其压缩形式。behavior-protocol.md L558 记载 `check-injection-contract` 锚点守护。本会话自身 system prompt 含该契约块（逐字一致），证明注入链活。此双点差异不削弱 H1 结论（审查同判定：契约确已到达注入面，反而更强）。
2. **但状态坐标系语言零 loop 化**：
   - persona 全文 `[Gg]ate`=0、loop/迭代=0——persona 本身中性，坐标语言来自下游；
   - 下游第一供给者 SKILL.md §B0 L90 模式确认句以 `stage: {stage}, Gate {gate}: {status}` 为标准状态行；SKILL.md 全文 Gate+stage+阶段 35 处 vs loop 0；
   - behavior-protocol.md（行为权威源）Gate 40 + 阶段 21 vs loop 0——**连定义 Coordinator 行为的协议本体都是纯 Gate 语言**；
   - bootstrap 聚合（每会话第二动作的热数据源）的 gates 面 + `next_gate` 字段（§2 观察面 2-1），loop 状态零投影（`bootstrap_aggregate.py` 全文无 loop/flow-unit 引用；loop-rollup 是独立命令 `verify_workflow.py` L22486，不进聚合）。
3. **0.65.0 重构的落点核对**：FX-188~194 交付物为 registry 数据 + 4 个 infra 模块 + 7 个 review SKILL Loop Role 段（EVD-684；`skills/` markdown loop 分布计量一致）；`core/lifecycle.md` mtime 2026-05-01 证明核心层阶段定义未被重构触碰；main-workflow L74 线性规则现存。
4. **因果路径**（机制推演，证据支撑）：agent 每会话上下文 = persona + 入口 bootstrap + SKILL §B0 + bootstrap 聚合输出 + plan-tracker 热段——五者供给的项目状态语言 100% 是「stage/Gate」；loop 词汇在该上下文中出现率为 0。agent 将 Gate 推进作为目标语言的直接来源即此。

### H2 —— 「候选推荐/next_actions 生成逻辑存在隐含『下一 Gate』排序倾向」→ **部分证伪（排序逻辑层）+ 部分证实（状态投影层）**

证伪部分（推荐排序逻辑无 Gate 倾向）：

- `task_priority.py` L1696：`recommended = sorted(unblocked, key=_priority_sort_key)`；L1630 步骤注释「``recommended_next`` = ``unblocked`` sorted by priority then version」——排序键为优先级+目标版本，无 Gate/阶段参数。文件中 `gate` 关键词命中均为英文动词或技术语境（如 L477 "the caller additionally gates this on..."、L895 "Gates the headerless task-table recognition"），与治理 Gate 无关。
- `bootstrap_aggregate.py` L692-737 `_next_actions`：动作来源 = Scenario 初始化/版本迁移标志/风险逾期/健康检查/候选任务/hooks 安装——**无任何「推进下一 Gate」类动作模板**。
- `verify_workflow.py` L11033-11073 `_status_next_steps`：排序键 =（priority rank，进行中优先，文档顺序），依赖未满足者剔除——纯任务依赖驱动。
- M7.4 step 6b（behavior-protocol.md L588）的推荐依据为「unblocked 任务 + 最高优先级未完成 + 版本依赖链 + 当前项目阶段」——依赖驱动，无 Gate 排序。

证实部分（状态投影层的线性倾向）：

- `bootstrap_aggregate.py` L291/L296/L313-315/L644/L877-879：gates 面摘要字段即 `next_gate`（第一个 pending Gate），text 面直接渲染 `next %s`——**「下一个该过的 Gate」作为一等程序字段**进入每会话热数据；这是「不管项目实际状态、都往下一个 Gate 推进」体感在工具输出层的对应物。
- 对照面：loop 状态（flow-unit runtime / loop-rollup）完全不在聚合投影中（§6 面 4）——快路径上 Gate 是唯一可见的进度坐标系。

残余不确定：用户观察「推荐总指向推进下一个 Gate」中，agent 向用户呈现推荐时的**话术包装**（用 Gate/阶段语言描述依赖驱动的任务推荐）是合理机制推断，但无会话输出样本可直接证实（§8 未验证项 3）。

### H3 —— 「产品注入面线性推进话术密度远高于 loop 语义密度」→ **证实（修正表述：分层隔离，注入面 loop 密度为 0）**

验证过程：§4.2/§4.3 全量计量。修正点：任务假设的「密度对比」在**全产品面**上不成立（loop 词 3420 > 线性短语 45）；成立的是**注入面/协议层/呈现层 vs 实现层/按需层的分层隔离**——loop 语言 96% 以上位于 `infra/*.py`（agent 不作为行为语言消费）与 11 个按需 markdown 文件（约 120 处，需第三次主动读取）；每会话必达注入面（persona/CLAUDE.md/AGENTS.md/SKILL.md/behavior-protocol.md/main-workflow/governance-init 模板）的 loop 计数**全部为 0**，线性 Gate/阶段语言约 112 处。语言即行为先验：注入面唯一可用的项目坐标词汇表是线性的。

---

## 6. 七个排查面结论汇总

| 面 | 结论 | 关键证据 |
|---|---|---|
| 1 DSH persona 注入链 | persona prefix（L45-74）坐标语言中性（Gate=0/loop=0）；FIX-253 行为契约已注入（L66-71）；Gate 语言经下游 SKILL §B0 与 `adapters/dsh/AGENTS.md.template` L21/L27 到达会话；本会话 system prompt 即渲染产物（狗粮自证） | grep 计数 + read 逐行 |
| 2 入口层 SKILL.md | Gate 19+stage 6+阶段 10 vs loop 0；模式确认句 canonical（L90）；六段 fallback 以 phase/stage/gate/Gate 状态跟踪为热段（L107-108）；阶段跳跃防护两处（L146/L161） | 全文 489 行通读 + 计数 |
| 3 平台入口模板与投影 | governance-init.md Step 7 四套模板（lightweight L196-261 / standard L264-329 / strict L332-344 / secondary-thin L347-379）全部 Gate 语言、loop=0；strict 最线性（L339 禁止阶段重叠）；仓库根 CLAUDE.md Gate=12/loop=0、AGENTS.md Gate=4/loop=0；commands 投影（governance.md L39、overview.md L126）同形态 | read L160-419 + pwsh 计数 |
| 4 呈现/聚合工具层 | `gates.next_gate` 一等字段（bootstrap_aggregate.py L296/L313-315/L644/L877-879）；`project.stage` 单值（L627）；overview 行 current_stage/latest_gate（L251-254）；cmd_status 文本面板 Stage/Latest Gate（verify_workflow.py L11190/L11194）+ cmd_gates 队列面板（L11528-11544）；**loop-rollup/flow-unit-runtime 不进入 bootstrap 聚合**（loop-rollup 独立命令 L22486-22493，读 `.governance/flow-unit-runtime.json`——本仓不存在） | read + grep |
| 5 候选推荐逻辑 | 排序 = priority+version+依赖（task_priority.py L1696/L1630；bootstrap L692-737；_status_next_steps L11056-11062）；REQ-110/FIX-254 空推荐降级已实现（task_priority.py L1548-1590）；**无 Gate 推进排序倾向**（H2 证伪部分） | read + grep 逐条分类 |
| 6 话术密度考古 | §4 全表：注入面 112:0，实现层 loop 3300+，按需 md 层 loop 约 120；里程碑化 canonical 出处 = behavior-protocol.md L426 | pwsh 全量统计 |
| 7 狗粮实证 | plan-tracker `## Gate 状态跟踪` = 单一全局 11-Gate 线性队列（G1→调研 … G11→下一轮）；`flow-unit-runtime.json` **不存在**、`loop-event-log.jsonl` **不存在**（loop 事件链零运行持续，与 AUDIT-143 §2.0.2 一致）；`loop-exit-candidates.json` 存在但 `exit_events_consumed: 0`（2026-09-19 生成，数据源自 task-priority light path 而非 loop 事件） | pwsh Test-Path + ReadAllText |

---

## 7. 行为面根因清单（按影响权重排序）

> 每项 = 位置 + 机制 + 线性强化方式 + 对 agent 行为的影响路径。

**R1（权重最高——每会话必现的第一坐标语言）模式确认句/状态行句式**
- 位置：`SKILL.md` L90（§B0 canonical）→ `commands/governance-init.md` L222/L278/L369（四套注入模板）→ 仓库根 `CLAUDE.md`/`AGENTS.md` → `adapters/dsh/AGENTS.md.template` L27。
- 机制：bootstrap 规定每会话输出一句 `stage: {stage}, Gate {gate}: {status}`——项目状态的第一句话以 Gate 为坐标。
- 线性强化：句式为 MUST 级协议要求；四套模板 + 双入口文件 + persona 间接引用多层重复投影。
- 影响路径：agent 每次会话开口的第一句即宣告「Gate 是项目主坐标」→ 用户观察面 1 的直接语言来源，并为后续状态描述定调（呈现层证据直达；「用户观感由该句驱动」的行为级对应为机制推断，见 §8 未验证项 1/3——R0 修正加限定，2026-09-27）。

**R2（权重高——热数据快路径的唯一进度坐标系）bootstrap 聚合 `gates.next_gate` + loop 零投影**
- 位置：`bootstrap_aggregate.py` L291/L296/L313-315/L644/L877-879；对照 loop 状态零投影（该文件无 loop/flow-unit 引用；`cmd_loop_rollup` 独立于聚合）。
- 机制：FEAT-033 把「第一个 pending Gate」选为 gates 面摘要字段并渲染为 `next %s`；loop 运行时数据（flow-unit-runtime.json）不存在也无读取路径。
- 线性强化：快路径 = 每会话第二动作（SKILL.md L72/L105），是 agent 获取项目状态的最主要程序化来源；其中唯一的方向性字段指向「下一个 Gate」。
- 影响路径：agent 的「下一步感」由 `next_gate` 供给 → 观察面 2 的机制基础（与推荐排序逻辑无关，见 H2 证伪部分）。

**R3（权重高——能力层的明文线性规则）main-workflow 阶段推进规则 + 11 阶段总览 + stage-* Gate 映射**
- 位置：`skills/main-workflow/SKILL.md` L56/L72-77（「默认顺序：1→2→3→...→11，前一阶段 Gate 通过后进入下一阶段」）/L38/L127；11 个 `skills/stage-*/SKILL.md` 的「Gate 映射」节（例：stage-research L100-102「本阶段对应 G2」）。
- 机制：场景匹配必经文件以规则形式规定线性顺序；每个子工作流以 G 编号声明线性位次。
- 线性强化：这些文件是 Coordinator 执行任何阶段活动前的加载对象；loop 语义在其中计数为 0。
- 影响路径：agent 在执行/匹配场景时反复读取「按顺序推进」规则 → 观察面 3/4 的话术与命名来源。

**R4（权重中高——协议语义定义处）M6 Gate 行为的「passed = 进入下一阶段」绑定**
- 位置：`references/behavior-protocol.md` L420-444（L426 语义表、L435-437 profile 裁剪表、L441 MUST-NOT 条款）。
- 机制：过 Gate 的四态语义全部以「下一阶段」为参照定义；profile 裁剪是同一队列的增删而非环化。
- 线性强化：MUST-NOT 级条款（「MUST NOT 声称进入下一阶段」）把 Gate-阶段绑定写入合规边界。
- 影响路径：agent 汇报进展时使用协议官方词汇 → 「通过 Gate X」被表述为「达成阶段」——观察面 3 的语义源头。

**R5（权重中——触发频率低但语气最强）阶段跳跃防护**
- 位置：`SKILL.md` L146/L161；`governance-init.md` L295-296（standard 模板 Step 3，渲染进 CLAUDE.md Step 3）；`commands/governance.md` L39、`governance/overview.md` L126。
- 机制：MANDATORY 警告 + `{n-1} 个前置阶段` 全序计数语言 + 「跳过 = 流程违规」最强语气。
- 线性强化：它是注入面中少数带情感强度的规则，强化记忆；同时把「跳过」定义为需要豁免的异常，隐含「顺序推进 = 正常」。
- 影响路径：用户请求与 Gate 队列错位时，agent 以线性护栏响应，进一步把对话锚定在 Gate 坐标系。

**R6（权重中——根属性）数据模型本身是线性 Gate 队列**
- 位置：`.governance/plan-tracker.md` `## Gate 状态跟踪`（11-Gate 全局队列表，Gate 列绑定「阶段转换」）；`## 项目配置`「当前阶段」单值字段。
- 机制：R1/R2 的工具投影是此数据结构的如实镜像——聚合器没有发明线性，它只是投影了线性。
- 线性强化：数据结构是 check/聚合/入口多方的共同事实源，任何单点语言修正都会被数据形态拉回。
- 影响路径：即使行为语言临时改写，agent 读到的热数据仍以 11-Gate 队列描述项目 → 偏差回归。

**R7（权重中——根因性）核心层定义与 0.65.0 重构脱节**
- 位置：`core/lifecycle.md`（mtime 2026-05-01，pre-DEC-097）、`core/stage-gates.md`、SKILL.md L425-426 参考表措辞（「11 阶段生命周期定义」）；对照 `core/loop-engineering-registry.json`（loop_gate_semantics 已注解 G1-G11）。
- 机制：0.65.0 重构新建了 registry 而未改写核心层阶段/Gate 定义文档；两套事实并存且注入面引用的是旧事实。
- 线性强化：CHANGELOG 0.65.0 的 "superseded" 宣称与文档现实相反，后续维护者以文档为准。
- 影响路径：任何「按文档理解系统」的会话（含按需读取 core/ 的深度会话）都会重建线性心智模型。

**R8（权重中——数据前置条件缺失）loop 运行时零激活**
- 位置：`.governance/flow-unit-runtime.json` 不存在、`loop-event-log.jsonl` 不存在、`loop-exit-candidates.json` `exit_events_consumed: 0`（2026-09-19）；与 AUDIT-143 §2.0.2 的「零运行」判定一致（修复链后仍无事件）。
- 机制：loop 引擎（loop_engine.py 的 loop_state/rollup/fuse）依赖 flow-unit 运行时；本仓 dogfood 是 classic gate 宿主（AUDIT-143 §2.0.5 模型层断层的延续），loop 状态从未产生过数据。
- 线性强化：没有 loop 数据 → 任何聚合器即便想投影 loop 也无米下炊；Gate 数据是唯一存在的进度数据。
- 影响路径：观察面 1/2 的「Gate 是唯一可见坐标系」在数据层成立——不是投影器偏好 Gate，而是只有 Gate 有数据。

### 7.1 行为面 ↔ 结构面根因映射（R0 修正补充，2026-09-27——对照审查 D-4.4）

> 映射关系采自 Design Review R0 §3.1（该节已核验「成立，无矛盾」）；C 条目定义见结构面报告 `audit-155-loop-gate-bias-structure-0.89.0.md` §3。两报告是同一病灶的两个正交切面（行为面 = 语言如何到达 agent；结构面 = 结构为何只供给线性语言），关系为层互补而非 1:1。

| 行为面根因 | 结构面对应 | 关系 |
|---|---|---|
| R1 模式确认句句式 | C-08（入口确认句线性坐标） | 同一注入点的两面 |
| R2 next_gate + loop 零投影 | C-04 + C-06 | 完全对应 |
| R3 main-workflow 线性规则 + stage-* Gate 映射 | C-02（核心定义层）+ C-08 | 部分对应——main-workflow 本身无独立 C 条目（结构面侧缺口，修复立项时按此补位） |
| R4 M6 passed=进入下一阶段 | C-02（stage-gates 原则 1） | 语义同源（behavior-protocol L426 与 stage-gates 同表述，审查已查证） |
| R5 阶段跳跃防护 | C-03 + C-08（判定对象） | 对应 |
| R6 数据模型线性队列 | C-07 + C-01 | 完全对应（R6 即 C-07 的数据面表述；结构面 S10-S13 已实证） |
| R7 核心层脱节 | C-01 / C-02 / C-03 | 对应 |
| R8 loop 运行时零激活 | C-01 + 结构面 §4 接线度分析 | 完全对应 |

---

## 8. 未验证项（显式标注）

| # | 未验证项 | 现状依据 | 验证计划 | 阻碍 |
|---|---|---|---|---|
| 1 | 用户历史会话中 agent 实际输出话术样本（观察面 1-3 的用户端复现） | 会话实时输出不落盘（AUDIT-143 未验证项 2 同一边界）；本审计以注入面语言实证替代行为样本 | 平台提供会话输出审计钩子，或请用户在后续会话中采样 agent 状态行/推荐话术 | 上下文不可观测；超出本仓库范围 |
| 2 | DSH 渲染产物（`${DSH_HOME}/.agent-presets/governance/agent.cordis.yml`）与本仓 template 的逐字节一致性 | 本任务沙箱无法读 `$DSH_HOME`；以 `agent.cordis.yml.template` + `launch.py --install` 渲染机制（模板头部注释 L1-15）为事实源 | 在真实环境防护三选一约束下比对渲染产物 | 沙箱边界 |
| 3 | 「agent 用 Gate 语言包装依赖驱动的任务推荐」（观察面 2 的包装机制） | 分析推断：注入面唯一坐标系语言是 Gate（§4.2）；推荐数据本身依赖驱动（H2 证伪部分） | 同未验证项 1 的会话采样 | 无行为样本 |
| 4 | `adapters/dsh/launch.py` 中 18 处 Gate 命中的逐条语境分类 | pwsh 计数确认存在，未逐一阅读 | 逐一 read 分类 | 与结论弱相关（该文件为安装器，非注入正文） |
| 5 | 0.74/0.75 修复链之后 `check-injection-contract` 的实际运行通过状态 | behavior-protocol.md L558 记载其存在与守护范围 | 运行 `check-governance` 观察 | 本任务只读边界内未运行（该检查属会话健康面，非本审计对象） |
| 6 | FIX-253 时点注入面契约的原始条数（当时 persona/SKILL 各几条）与现行五条/四条形态的逐版演化路径 | 现状双点差异已实证（persona L66-71 五条 / SKILL.md L225-232 四条）；「真实环境必防护」条目与 FIX-271（M7.7 协议本体，2026-08-23）及 FIX-274（注入同步修订）时间一致，但 FIX-253 时点快照未考古 | git 考古 FIX-253 提交时点的两文件契约段 | 演化史细节；R0 修正文本已用弱表述规避（R0 修正补充，2026-09-27） |

---

## 9. 呈现层 loop 语义形态的观察性描述（非修改方案）

以下仅描述「若呈现层以 loop 语义为坐标系，语言形态的自然参照」，全部基于仓库内既有词汇与 DEC-097/098 语义，不构成 AUDIT-156 的方案承诺：

1. **状态行**：loop 坐标系的自然状态要素已存在于 `loop_engine.py` 的运行时词汇——`active_loop_tier`（当前活跃环层：outer/middle/inner/setup）、`iteration_within_inner`（环内迭代轮次）、`agent_phase`（Plan-Act-Observe-Reflect 相位）、`fuse`（熔断余量）。形态上即「当前环 + 轮次 + 相位」，对照线性形态「stage + Gate {n}: {status}」。
2. **方向性字段**：线性形态的方向字段是 `next_gate`（下一个待过 Gate）；loop 语义中 gate = loop 的退出条件 + 下一 loop 入环条件（DEC-097 核心洞察，registry `loop_gate_semantics` 已按此注解）——方向性表述的自然形态是「当前环的退出条件差距 / 下一环的入环条件」，而非队列中的下一个节点。
3. **进度感**：线性模型中进度 = 队列位置（passed 计数 / next_gate）；loop 模型中进度 = 项目目标差距与环的迭代收敛（`task_priority.py` 已有的 `empty_reason`/`unblock_recommendation`「解除阻塞最短路径」语言是目标差距方向的既有语言基础）。
4. **Gate 的位置**：DEC-098 criterion-4 兼容语义下 Gate 是「loop-exit/entry certification」（CHANGELOG 0.65.0 原文）——即 Gate 作为**环退出认证事件**出现在语言中（「内环退出认证通过」），而非阶段里程碑坐标（「进入下一阶段」）。
5. **既有 loop 语言资产**：7 个 review SKILL 的 Loop Role 段（如 code-review「certifies Inner loop EXIT」）、`references/loop-role-mapping.md`——呈现层改造的语言素材在仓库内已存在，未接入注入面。

---

## 10. 硬门槛自检

| 门槛 | 结果 |
|---|---|
| 只读分析，除输出文件外零修改 | ✅ 本会话仅写入本报告（含 R0 修正）；未触碰产品代码与 `.governance/` |
| 每条结论有文件/行号/grep 计数实证 | ✅ §2-§7 全部引用带路径+行号；§4 命令+计数可复现 |
| 历史链锚点实际读取后才引用 | ✅ AUDIT-143 报告全文 340 行已读；DEC-097 归档原文已读（archive/decisions L11-16）；0.65.0/0.84.0 CHANGELOG 段已读 |
| 输出 UTF-8 | ✅ |
| 报告不含修改方案 | ✅ §9 为观察性描述，未提任何实现/结构方案 |
| 未验证项显式标注 | ✅ §8 六项（第 6 项为 R0 修正补充） |
| R0 复审对照修复 | ✅ 2026-09-27 按 `docs/reviews/review-AUDIT-155-156-DESIGN-R0.md` 修复行为面侧 D-2/D-3/D-4；审查证据 B3/B12/B26 复核一致（32 版本条目经本侧独立复现）；审查对行为面报告无 D-1 义务（D-1 属结构面）；D-4.3（§5.4 决策边界措辞）经 grep 确认行为面报告无 §5.4 引用，仅适用结构面——本报告无对应修改点 |

## 附录：检查过的文件清单（关键行）

| 文件 | 用途 |
|---|---|
| `agents/analyst.md`、`skills/stage-research/SKILL.md` | 角色定义与任务规范加载 |
| `docs/requirements/audit-143-loop-planning-behavior-gap-0.74.0.md` | 前序审计全文（L13 摘要 / L31-45 注入链 / L53-57 工具零调用 / L313-316 persona 证据） |
| `.governance/archive/decisions/decisions-v0.1.0-0.64.0.md` L11-16 | DEC-097 原文 |
| `.governance/archive/index.md` L1271、`archive/tasks/v0.1.0~v0.65.1.md` L27-35、`archive/evidence/evidence-v0.1.0-0.65.1.md` L15-16 | 0.65.0 实现链交叉 |
| `project/CHANGELOG.md` [0.65.0] / [0.84.0] 段 | "superseded" 宣称与切片 A 内容 |
| `agent-presets/governance/agent.cordis.yml.template` L45-74、`preset.yml` | persona 注入面 |
| `adapters/dsh/AGENTS.md.template`、`launch.py`（计数） | DSH 投影 |
| `skills/software-project-governance/SKILL.md` 全文 489 行 | 入口层 |
| `commands/governance-init.md` L160-419 | Step 7 四套注入模板 |
| `skills/software-project-governance/references/behavior-protocol.md` L400-624 | M6/M7.4/M5.5/step 6 |
| `skills/software-project-governance/references/interaction-boundary.md`（计数） | 交互边界 |
| `skills/main-workflow/SKILL.md` L38-193 | 能力层总入口线性规则 |
| `skills/software-project-governance/core/lifecycle.md`（计数 + mtime）、`core/stage-gates.md`、`core/task-gate-model.md`（计数） | 核心层 |
| `skills/software-project-governance/infra/bootstrap_aggregate.py` 全文 994 行 | bootstrap 聚合 |
| `skills/software-project-governance/infra/verify_workflow.py` L11033-11203、L11528-11544、L22486-22540 | status/gates/loop-rollup |
| `skills/software-project-governance/infra/task_priority.py`（grep 112 处分类） | 推荐逻辑 |
| `.governance/plan-tracker.md`（Gate 状态跟踪节）、`loop-exit-candidates.json`、文件存在性检查 | 狗粮数据形态 |

## 边界声明

- 本报告为只读分析产物；所有假设与事实分开呈现（§3/§5 为验证结论，§7 为根因定位，§8 为未验证项）。
- 不提出修改方案；§9 为观察性描述。方案归属：AUDIT-156（结构面票）+ 后续修复立项。
- 与用户的交互（会话话术采样等）超出 Analyst 权限，已列入 §8 验证计划返回 Coordinator。
