# AUDIT-155 — loop 模式线性 Gate 行为偏差根因分析（结构面：Gate 线性模型 vs loop 模型语义冲突定位）

- **日期**: 2026-09-26
- **执行**: Architect Agent（只读结构分析 + 修改方向候选；AUDIT-155，plan-tracker L83 并行票登记 🔄）
- **对象版本**: 工作流 0.89.0（plan-tracker L11 确认已发布态；本仓 dogfood plan-tracker/evidence 为治理运行时事实源）
- **并行票**: AUDIT-156（行为面）——本报告为结构面；两者在 Design Reviewer 审查处汇合
- **性质**: 根因分析（结构层）——用户 2026-09-26 反馈 loop 模式改造后实际运行仍退化为线性 Gate 推进
- **历史链锚点**: DEC-097（`.governance/archive/decisions/decisions-v0.1.0-0.64.0.md` L11/L16，已实际读取）、AUDIT-143（`docs/requirements/audit-143-loop-planning-behavior-gap-0.74.0.md` 全文 340 行，已实际读取）、`skills/software-project-governance/references/loop-role-mapping.md`（全文 50 行，已实际读取）
- **R0 修正**（2026-09-26，按 `docs/reviews/review-AUDIT-155-156-DESIGN-R0.md` 缺陷清单 D-1/D-2）: ① RB-2 前提对账 DEC-133（原稿「loop runtime 从未通过外部验证」被 DEC-133 证伪——时序错置，loop-role-mapping.md L5 为 0.66.1 时点声明）；② C-10 补充「DEC-133 ↔ loop-role-mapping L5 ↔ dogfood 未激活」三方矛盾在案发现；③ §5.2 候选 B 风险①前提修正；④ §8 未验证项 3 同步改写；⑤ 版本计数 15→32（统计口径 CHANGELOG 条目实计）。其余结构、候选方案、矩阵与已证实结论不变。

---

## 1. 执行摘要

**核心结论：DEC-097（2026-07-10，"loop 为唯一模型，G1-G11 退化为 loop-setup"）在结构层从未落地。** 0.65.0 交付的 loop-engineering 是一套**自声明 schema-only** 的旁路资产（`loop-engineering-registry.json` L9 `registry_mode: "schema-only-no-runtime-activation"`；L13-14 明文"不修改 classic G1-G11 gate judgment 行为"），而承载项目状态权威坐标的**全部激活结构**——lifecycle-registry 激活模式、core 层 Gate 定义文档、governance-bootstrap 热数据投影、plan-tracker 数据模型、入口 SKILL.md——至今仍是纯线性 stage-gate 模型。loop 引擎的全部运行时能力（rollup/round/fuse/health/migration）只能通过显式 opt-in CLI 访问，每会话必经的 bootstrap 聚合投影中 grep `loop` **零命中**；本仓 dogfood `.governance/flow-unit-runtime.json` 不存在 = loop 运行时在唯一真实宿主上从未初始化。

**用户观察到的"不管项目实际状态都往下一个 Gate 推进"不是行为层的偶发偏差，而是结构层面必经信息环境的必然产物（行为因果为机制推断，见 H-1——成立的是系统必然提供 classic 主坐标，未证明行为占比与切换后目标导向自然成立；R1 notes N-2 顺带修复 2026-09-26）**：每会话第一动作消费的热数据（bootstrap `gates.next_gate` = 队列第一个 pending Gate；`project.stage` = 单一全局阶段坐标）与模式确认句模板（`stage: {stage}, Gate {gate}: {status}`）持续把 agent 的项目状态心智锚定在"线性队列中下一个待过门"上。DEC-097 想替换的心智模型（用户原话"线性的状态迁移并不合理"）正是当前热数据每会话重建的模型。

| # | 关键发现 | 置信度 |
|---|---|---|
| 1 | 激活生命周期模式仍为 classic-phase-gate（lifecycle-registry L10-11）；loop-engineering registry 自我声明 schema-only 且不改变 classic 判定（L9/L13-14） | 高（文件直读） |
| 2 | bootstrap 热数据 `next_gate` = 第一个 pending Gate（bootstrap_aggregate.py L313-314），直出每会话第一屏（L877-879）；投影全文无 loop 面 | 高（代码直读） |
| 3 | loop 引擎 6 模块能力全部 opt-in CLI；rollup_loop_state 无任何生产聚合调用方 | 高（grep 全仓） |
| 4 | 本仓 dogfood 无 flow-unit-runtime.json；plan-tracker 状态被表达为"停在第 11 阶段等 G11" | 高（glob + 文件直读） |
| 5 | 入口 SKILL.md 全文零 "loop"（grep 实证）；模式确认句以 stage+Gate 为项目状态主坐标 | 高（grep 实证） |
| 6 | "next_gate 投影 → agent 行为拉回线性"为机制推断（H-1），未经受控行为实验证明 | 假设（显式标记） |

---

## 2. 排查面逐面分析

### 2.1 排查面 1：核心层结构文件——Gate 定义语义

| 文件 | 关键证据 | 语义判定 |
|---|---|---|
| `core/stage-gates.md` | L5-104：G1~G11 每个标题即"X → Y"阶段转换（G1"立项 → 调研"…G11"维护 → 下一轮"）；L108 执行原则 1"未通过 Gate，不得声称进入下一阶段" | **纯线性里程碑**。全文无 loop 词汇。原则 5（L112）"Gate 失败后…只需补齐缺失项后重新检查"有微弱迭代意识，但框架仍是"阶段达成" |
| `core/lifecycle.md` | L5-81：11 阶段顺序定义，每阶段"退出条件"；L95-99 回退规则——回退是需记录风险/决策的**异常事件**；L110 治理规则 2"阶段推进：推进前必须通过 Gate 检查" | **纯线性阶段模型**。回退=异常的建模与 loop 语义（回退=所属 loop 的正常迭代）直接冲突 |
| `core/task-gate-model.md` | L7-13：Task-Gate 模型把 Gate 粒度从阶段级降到任务级——**但仍是 Gate 模型**（任务完成即过门，L33-39 四态 pending/passed/blocked/skipped）；L57-61 兼容性只列 phase-gate/agent-team 两值，**无 loop-engineering** | **任务级线性**。Task-Gate 是"更细的里程碑"，不是"loop 退出条件"；workflow_model 词汇表中 loop-engineering 缺席 |
| `core/loop-engineering-registry.json` | L9 `registry_mode: "schema-only-no-runtime-activation"`；L13-14/L16"不激活运行时 instrumentation""不修改 classic G1-G11 gate judgment"；L19-102 loop_gate_semantics 完整定义 G1-G11 的 loop 角色（loop-setup/body/entry-gate/exit-gate + enclosing_loop + on_fail + fuse）；L103-124 四级 fuse；L162-189 AgentIntrinsicLoop schema | **语义正确、激活为零**。这是 DEC-097 目标语义在数据层的完整声明——但被自身 no_overclaim 边界锁死在 schema-only |
| `core/lifecycle-registry.json` | L10-11 `"active_lifecycle_mode": "classic-phase-gate"` / `"default_lifecycle_mode": "classic-phase-gate"`；L40-65 classic preset `active: true, default: true`，携带线性 stage_sequence + gate_sequence；L292-359 gate_references：每个 Gi = from_stage→to_stage 线性跃迁；L360-459 allowed_transitions：11 条 classic-forward + 仅 3 条 flow-unit-loop；L489-502 loop_policy `runtime_activation: false`、`loop_counter_policy: "schema-only-recorded-by-future-runtime"`；L1748-1756 gate_execution_registry `"active-classic-compatibility"`、`execution_scope: "classic-g1-g11-only"` | **当前激活关系实锤：classic 激活、loop 未注册为可选模式**。loop-engineering-registry.json 甚至不在 lifecycle_modes 列表中（只有 classic-phase-gate 与 dynamic-flow-gate 两值）——loop-engineering 作为 workflow_model 在生命周期注册表的模式词汇表里没有席位 |

**classic preset 与 loop-engineering 的当前激活关系结论**：lifecycle-registry 的 `lifecycle_modes` 词汇只认 classic-phase-gate（active）与 dynamic-flow-gate（schema-only）；loop-engineering 是第三个平行 registry 文件，不在模式枚举内，无激活位。DEC-097 决议的"重构式——loop 为唯一模型，G1-G11 退化为 loop-setup"在注册表数据面没有任何对应字段变更——`active_lifecycle_mode` 的候选集里根本没有 loop-engineering 这个值。

### 2.2 排查面 2：loop 引擎模块的实际接线度

能力清单（全部存在于 `skills/software-project-governance/infra/`）：

| 模块 | 能力 | 生产调用方（grep 全仓 .py 实证） |
|---|---|---|
| `loop_engine.py`（1096 行） | registry 加载（L115）、gate loop 语义查询（L151）、round 推导 derive_round（L218，sacred pure）、fuse_decision（L277）、escalation_payload（L337）、activate_loop_state（L389）、round budget/heartbeat（L630-917）、**rollup_loop_state（L973-1096，no_global_stage 载重不变量）** | rollup 仅 CLI 薄入口 `verify_workflow.py loop-rollup`（verify_workflow.py L22487-22493）+ 测试；其余函数无 verify_workflow 聚合路径调用 |
| `flow_unit_derive.py` | 从 plan-tracker 派生 flow units | 仅 `loop_migration.py` L65 / `loop_migration_plan.py` L60（migration 链内部）+ 测试 |
| `loop_migration.py`（1300 行） | classic→loop 数据迁移 + 回滚 + 备份；L229-248 `_parse_workflow_model` 以 `## Gate 状态跟踪` 存在性推断 classic 模式 | 仅 CLI `loop-migrate`（verify_workflow.py L22203/22234）+ 测试 |
| `loop_health.py` | loop runtime 健康检查 | 仅 CLI `check-loop-health`（verify_workflow.py L22400，"advisory-only"）+ 测试 |
| `checks/loop_runtime_claims.py` | loop runtime 声明扫描（防 overclaim） | verify_workflow.py L47-50 导入，用于 installed_host/product_release 两处 claim 扫描（L16671/L21258）——**这是唯一进入常规校验路径的 loop 面 relevante 代码，但作用是"防止声称 loop 已激活"，反向固化 loop 未激活状态** |

**rollup_loop_state 的 no_global_stage 不变量**（loop_engine.py L920/L985-1007）：返回 dict 恒置 `no_global_stage: True`，禁止任何把多 unit 折叠为单 stage 的字段——这是 RISK-037 判据 2 的可执行保证（test_loop_rollup.py L159/L282 有回归锁）。**该不变量是全仓唯一以代码强制 loop 语义的结构实体，但它没有被任何每会话消费路径调用。**

**结论**：loop 引擎能力 = **已交付但不可见**。每会话必然消费的热数据通道（governance-bootstrap）不聚合任何 loop 面；唯一进入常规校验的 loop_runtime_claims 是"防声称激活"的反向守卫。引擎与行为之间隔着一层 opt-in CLI（loop-rollup / loop-migrate / check-loop-health），而没有任何规则、Check 或入口要求 Coordinator 运行它们。

### 2.3 排查面 3：verify 聚合层——bootstrap 的 gates 面与 stage 字段

governance-bootstrap 实现在 `infra/bootstrap_aggregate.py`（verify_workflow.py L84 导入、L26018-26025 注册、L26320 分发）：

- **`project.stage` 生成**（bootstrap_aggregate.py L624-627）：`"stage": _clip(config.get("当前阶段", ""))` ——直接取 plan-tracker `## 项目配置` 的单一 `当前阶段` 字段；L241-256 `parse_overview_row` 同样把 `## 项目总览` 第二列读为 `current_stage`。
- **`gates` 面生成**（L288-315 `parse_gate_summary`）：解析 `## Gate 状态跟踪` 表（`_GATE_SECTION_PREFIX` L121），计数 passed/pending/failed，**`next_gate` = 队列中第一个 status 为 pending 的 Gate id**（L313-314）。L877-879 text 面直出：`"gates: passed %s/%s (pending %s, failed %s); next %s"`。
- **`_build_payload` 全部数据面**（L581-679）：resolve / project / gates / tasks / risks / migration / recent / candidates / health / behavior / next_actions / deferred——**grep `loop` 在本文件零命中**（实证：`loop|stage` 模式仅返回 stage 相关 7 行）。
- **`_next_actions`**（L692-737）：升级提示/风险逾期/候选推荐/hooks 安装——行动建议全部不携带 loop 语义。

**`next_gate` 语义分析**：`next_gate` 的存在本身即线性预设——它假设存在一个全序 Gate 队列，项目状态可表达为"队列中下一个待过的门"。在 loop 语义下，"下一个 Gate"不是合法问题（loop 语义的对应问题是"哪些 unit 处于哪个 tier 的第几轮迭代、哪个 fuse 接近熔断"）。该字段以每会话第一屏的位置权重（bootstrap 是强制第一动作）持续输出线性目标。

**Gate 状态跟踪校验以单一全局队列为权威的程度**：`parse_gate_status`（verify_workflow.py L7662-7686）与 `check_gate_consistency`（L9917-9972）是 Gate 状态的引擎侧判定源。值得注意：check_gate_consistency 对全局 Gate 表的"passed 无对应证据"检查**实际是空转**——L9926-9937 循环内 `found` 计算后从未使用，L9939-9944 passed-on-entry 分支同样以 `pass` 结束；该函数实际只做任务证据完整性与孤儿证据检查。即：全局 Gate 表既无 loop 语义、也无实质机器校验，是**呈现性权威**（bootstrap/`gates` CLI/status 命令的消费对象）而非受校验事实。

### 2.4 排查面 4：plan-tracker 数据模型

live `.governance/plan-tracker.md`（本仓 dogfood，0.89.0）：

- L12：`当前阶段: 维护与演进（第 11 阶段）`——单一全局线性坐标，正文还串联 0.38.0~0.89.0 全部版本史。
- L20-21（Onboarding 声明）：`前置阶段（1~10）Gate: 全部标记为 passed-on-entry`；`当前阶段（11）Gate: G11 pending，待维护阶段任务进一步推进后检查`——**项目自身状态被表达为"停在第 11 阶段，等 G11 过门"**。这是用户所描述的"把 Gate 推进当作目标、停在某个 Gate 等待过门"语义的 dogfood 活样本。
- L24-38（`## Gate 状态跟踪`）：单一全局 11 行线性表，每行 `| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |`——G1→G2→…→G11 队列。注意内部不一致：L38 G11 行状态 `passed`（2026-04-21）、L44 项目总览`最近 Gate 结论: G11 通过`，而 L21 写 `G11 pending`——**同一坐标三处矛盾且无任何 Check 发现**（与 2.3 的校验空转一致）。
- L83：本任务（AUDIT-156/155 并行票）登记行。
- **`.governance/flow-unit-runtime.json`：不存在**（glob 实证）——loop 运行时在本仓从未激活（延续 AUDIT-143 §2.0.2/§324 的 0.74 时点发现，至 0.89.0 未变）。**DEC-097「loop 为唯一模型」的兑现度 = 0**：决策通过 32 个发布版本（0.65.0~0.89.0——统计口径：`project/CHANGELOG.md` `## [0.x.y]` 版本条目逐条实计 32 条〔含 0.65.x/0.66.x patch 线与 0.78.1〕，2026-09-26 复核；R0 修正——原稿误计「15 个版本」），唯一真实宿主的项目状态模型仍是 classic 线性表。

**对照结论**：plan-tracker 数据结构本身强制单一线性坐标（单值 `当前阶段` + 全局 11-Gate 表）；loop 模型要求的 per-unit gate lane / loop_count / tier 视图（lifecycle-registry L503-566 flow_unit_schema 已定义完整字段）在本仓无一落地。

### 2.5 排查面 5：状态机与触发器——恢复路径的 Gate 消费

- **execution-packets**（verify_workflow.py L14300-14395 `build_execution_packet`）：packet 结构含 goal/acceptance_contract/quality_budget/vertical_slice/interruption_policy/allowed_change_scope——**不含任何 stage/Gate 字段**。执行包是任务级约束，不是线性续行源。
- **session-snapshot**：`.governance/session-snapshot.md` 为 markdown 手写文件；bootstrap 仅消费 `snapshot_exists/snapshot_fresh` 两布尔（bootstrap_aggregate.py L597-598）。其"下次会话优先级"内容为手写有序列表（AUDIT-143 §2.2 实证，本次未重复取证）——恢复内容不受 Gate 表结构约束，但也**无 loop 语义的恢复锚**（恢复=继续手写列表，而非"恢复所属 unit 的 loop tier/轮次"）。
- **真正的续行路径锚**是 bootstrap 投影 + 入口模板：模式确认句模板（CLAUDE.md/AGENTS.md/SKILL.md L90 三处同文）`Governance: {trigger_mode} x {permission_mode} | stage: {stage}, Gate {gate}: {status}, {risk_count} risk(s)`——**每会话第一句输出把 stage+Gate 状态定义为项目状态的主坐标**；bootstrap `next_actions` 的行动建议（候选任务/升级/风险）均不含 loop 概念。恢复逻辑因此天然把"项目状态 = 线性坐标 (stage, gate)"作为默认续行框架——不是 snapshot 恢复了线性，而是**每会话开局投影重建线性**。

### 2.6 排查面 6：语义差距矩阵（核心交付）

用户四条理念基准 vs 当前结构实体：

| 结构实体 | 基准 1：Gate=看护门禁非阶段目标 | 基准 2：版本永远往前推进 | 基准 3：多级 loop 服务项目最终目标 | 基准 4：一切动作高效高质无偏差达目标 |
|---|---|---|---|---|
| lifecycle-registry `active_lifecycle_mode: classic-phase-gate`（L10-11） | ✗ 冲突：激活模式即阶段达成模型 | ✗ 冲突：classic-forward 跃迁（L360-459）以过门为推进 | ✗ 冲突：无 loop tier 坐标 | ✗ 冲突：判定权威（gate_execution_registry L1748-1756）只服务过门判定 |
| `core/stage-gates.md`（L5-108） | ✗ 冲突：Gate 定义=阶段转换检查 | ✗ 冲突：原则 1"未过门不得进入下一阶段" | ✗ 冲突：无所属循环概念 | ✗ 冲突：失败=补齐缺失再过门（非回 loop 再迭代） |
| `core/lifecycle.md`（L5-99） | ✗ 冲突：11 阶段+退出条件 | ✗ 冲突：回退=需记录的异常事件（L95-99） | ✗ 冲突：阶段为终态坐标 | △ 部分：允许相邻阶段重叠（L87-93）但仍是阶段框架 |
| bootstrap `gates.next_gate`（bootstrap_aggregate.py L313-314） | ✗ 冲突：热数据直接输出"下一个待过门" | ✗ 冲突：把过门作为下一步行动暗示 | ✗ 冲突：无 unit/tier 分解 | ✗ 冲突：注意力被锚定到门而非目标差距 |
| bootstrap `project.stage` 单值（L627） | ✗ 冲突：全局单一线性坐标 | ✗ 冲突：版本推进被折叠进单一 stage 字符串 | ✗ 冲突：无多 lane 并行表达 | ✗ 冲突：状态失真（如"第 11 阶段"内同时存在发布/修复/审计多线） |
| plan-tracker `## Gate 状态跟踪` 全局表（L24-38） | ✗ 冲突：11 Gate 队列即项目状态权威 | ✗ 冲突：`阶段转换`列定义线性序 | ✗ 冲突：无 per-unit 视图 | ✗ 冲突：三处 G11 状态自相矛盾无校验（呈现性权威） |
| 入口 SKILL.md 模式确认句（L90） | ✗ 冲突：Gate 状态=项目状态主坐标 | ✗ 冲突：确认句无版本/演进坐标 | ✗ 冲突：无 loop tier | ✗ 冲突：每会话第一句重建线性心智 |
| **loop-engineering-registry.json loop_gate_semantics（L19-102）** | **✓ 合规**：G1-G11 全部标注 loop 角色+enclosing_loop+on_fail | ✓ 合规：on_fail=iterate-enclosing-loop | ✓ 合规：setup/inner/middle/outer 层级 | ✓ 合规：fuse+escalation 语义 | 
| **loop_engine.rollup_loop_state no_global_stage（L973-1096）** | **✓ 合规**：无全局 stage 字段的 per-unit 视图 | ✓ 合规：per-unit loop_count | ✓ 合规：by_tier 聚合 | ✓ 合规：fuse_tripped 可见 | 
| loop-role-mapping.md 七审查 SKILL 映射（L25-35） | ✓ 语义合规 | ✓ 合规 | ✓ 合规 | △ 但 L5 为 0.66.1（2026-07-17）时点声明（experimental scaffolding、runtime NOT_MET），未随 DEC-133（07-26 关闭 RISK-037/042）更新——记录漂移在案实例，见 C-10 补充发现（R0 修正） |

**差距方向总结**（示例性正确形态，独立分析结论）：Gate 状态应从「项目全局阶段坐标」改为「每 flow unit / 每 loop 的退出条件态」——loop-engineering-registry 与 rollup_loop_state 已给出正确形态的完整数据契约，缺的是**激活与投影接线**；`next_gate` 应改为 per-unit 的 tier/round 视图或 goal-gap（项目最终目标与当前单元的差距）；`stage` 单值应改为多 lane 并行态（flow_unit_schema 的 gate_lane 词汇 L549-559 已定义 backlog/design/development/testing/release-candidate/released/operations-feedback/maintenance/blocked 九 lane）。

---

## 3. 冲突点清单（10 条）

每条格式：位置 + 机制 + 线性强化的作用路径（谁消费它）+ loop 语义下的正确形态。

- **C-01 激活模式锁死 classic**
  - 位置：`core/lifecycle-registry.json` L10-11（active/default_lifecycle_mode）、L30-66（classic preset active）、L1748-1756（gate_execution_registry `execution_scope: "classic-g1-g11-only"`）
  - 机制：DEC-097 决议 loop 为唯一模型，但注册表的模式枚举（lifecycle_modes L30-103）只含 classic-phase-gate/dynamic-flow-gate，loop-engineering 无激活席位；no_overclaim 边界（L19-29）明文"preserves classic G1-G11 behavior""does not close RISK-037"
  - 作用路径：`auto_judge_gate`（verify_workflow.py L17690-17718）从该注册表读判定检查——**所有 Gate 判定的权威源是 classic 执行注册表**；loop-engineering-registry.json L13-14 自我声明不修改该判定
  - 正确形态：loop-engineering 注册为激活模式（或按 DEC-097 唯一模型直接替换），classic 判定降为兼容 preset
- **C-02 stage-gates.md 教科书级线性定义**
  - 位置：`core/stage-gates.md` L5-104（G1-G11"X → Y"标题）、L108（原则 1）
  - 机制：Gate 的人类可读定义层把 Gate=阶段转换检查写入核心层；loop-role-mapping.md 的四值角色词汇（loop-setup/body/entry-gate/exit-gate）只存在于按需 references 层，核心定义层未更新
  - 作用路径：agent 执行 Gate 检查时按需读取（SKILL.md L426 列为 `core/` 合约资产）——审查 SKILL 与 Gate 检查行为的概念源头
  - 正确形态：每个 Gate 重写为"认证〔某循环〕的退出/进入条件"（loop-role-mapping.md L27-35 映射表已有现成内容），失败语义改写为"退回所属循环再迭代"
- **C-03 lifecycle.md 回退=异常建模**
  - 位置：`core/lifecycle.md` L95-99（回退规则）、L110（治理规则 2"阶段推进：推进前必须通过 Gate"）
  - 机制：回退被建模为需记录风险/决策的异常事件——loop 语义中"gate 失败→回所属 loop 再迭代"是**正常路径**（DEC-097 核心洞察原话：'gate 失败不"失败阶段"而是退回 loop 再迭代'）
  - 作用路径：agent 进入阶段时按需读取（SKILL.md 按需层）；阶段跳跃防护（bootstrap Step 3）以"前置 Gate 均为 pending"为判定前提——线性队列前提的强制执行器
  - 正确形态：阶段定义改写为 loop tier 的 body 描述；"回退"术语退役，改称"loop 内迭代"
- **C-04 bootstrap `next_gate` 线性目标注入**
  - 位置：`infra/bootstrap_aggregate.py` L313-314（next_gate=首个 pending）、L643-644（payload 装配）、L877-879（text 面输出）
  - 机制：`next_gate` 字段名即语义——"下一个 Gate"预设全序队列与"过门=下一步"；每会话强制第一动作消费
  - 作用路径：Coordinator 每会话 bootstrap → 模式确认句与状态行 → 首次交互选项的框架。"不管项目实际状态都往下一个 Gate 推进"的最短结构解释路径：**热数据每天告诉 agent 下一目标是什么门**
  - 正确形态：runtime 存在时输出 loop face（per-unit tier/round 分布，rollup_loop_state 契约）；`next_gate` 更名并改义为 next_loop_iteration 或 goal-gap（项目目标差距），无 runtime 时显式输出"loop runtime 未激活"而非回退线性
- **C-05 bootstrap `project.stage` 单值全局坐标**
  - 位置：bootstrap_aggregate.py L627、L241-256；plan-tracker L12/L42
  - 机制：多线并行（0.89 候选池多任务/多发布线/审计线）被折叠为"维护与演进（第 11 阶段）"单字符串
  - 作用路径：bootstrap JSON/text 面 + CLAUDE.md/AGENTS.md 模式确认句模板 `{stage}` 槽位
  - 正确形态：多 lane 并行态（flow_unit_schema L549-559 gate_lane 九值词汇）；no_global_stage 不变量（loop_engine.py L985-1007 已实现该契约）接入投影
- **C-06 bootstrap 无 loop 面——引擎能力不可见**
  - 位置：bootstrap_aggregate.py `_build_payload` L581-679（全数据面枚举，grep `loop` 零命中）；rollup 唯一生产调用 verify_workflow.py L22487-22493
  - 机制：loop 全部运行时能力为 opt-in CLI，无任何规则/Check/入口要求运行；AUDIT-143 §2.0.1-2.0.2 的注入链断链在 0.89.0 结构面仍然成立（0.74/0.75 修复链处理的是复审触发器与推荐规则——REQ-107/108 方向，未触及 loop 投影）
  - 作用路径：每会话必经 bootstrap；loop 状态对 agent 永不可见，除非 agent 自发运行 loop-rollup（无任何触发点）
  - 正确形态：bootstrap 增加 loop face（runtime_found 时投影 units/summary；缺失时输出迁移提示——loop-rollup 的 `runtime_found: False` 返回值 L1010-1032 已含该契约）
- **C-07 plan-tracker 单一全局 Gate 表 + 单值 stage**
  - 位置：`.governance/plan-tracker.md` L12（当前阶段）、L20-21（Onboarding 声明"停在 G11"）、L24-38（11-Gate 线性表）
  - 机制：治理数据结构本身把项目状态强制为单一线性坐标；loop_migration.py L241-243 甚至以该表存在性判定 classic 模式（数据结构=模式判据）
  - 作用路径：bootstrap gates 面解析源（L121 `_GATE_SECTION_PREFIX`）；engine `parse_gate_status`（L7662-7686）；`gates` CLI/status 命令——全部治理读路径的唯一 Gate 事实源
  - 正确形态：per-unit lane 表（每 flow unit 一行：unit_id / lane / loop_count / tier / fuse 状态）为权威，全局 Gate 表降级为兼容投影或删除
- **C-08 入口 SKILL.md 零 loop 语义 + 模式确认句线性坐标**
  - 位置：`skills/software-project-governance/SKILL.md`（grep `loop` 零命中实证）；L90（确认句模板）、L82（"当前项目处于哪个阶段"）、L108（热数据面 b=Gate 状态跟踪）、L158/L161（风险接受/阶段跳跃=违规）
  - 机制：SKILL.md 是 Coordinator 每会话加载的唯一入口文件（M2 预加载），行为约束投影根；loop 词汇只在 references/loop-role-mapping.md（L5 自我声明 experimental scaffolding）按需层
  - 作用路径：每会话身份加载 → 确认句以 stage+Gate 表达项目状态 → "阶段跳跃防护"以线性 Gate 队列为前提强制执行（Step 3：跳过 pending Gate 前置阶段须警告）
  - 正确形态：入口层携带 loop 最小语义（确认句增加 loop 位或以 tier/lane 替代 Gate 位）；阶段跳跃防护的判定对象从"Gate 队列顺序"改为"loop 进入条件认证"
- **C-09 auto_judge_gate 判定主体 classic、loop 接线为附加分支**
  - 位置：verify_workflow.py L17669-17780；判定源 L17690-17718（gate_execution_registry）；Wiring B L17761-17770（需显式 unit_id，best-effort degrade）
  - 机制：Gate 判定的主产出是 classic passed/blocked/passed-with-conditions/needs_human 四值；loop 事件链仅在调用方显式传 `--unit` 且判定已渲染时附加触发——classic 宿主（本仓）无 unit_id 供给（AUDIT-143 §2.0.5 模型层断层，未修复）
  - 作用路径：`gate-check` CLI 与任何 gate 判定调用；NEEDS_CHANGE 的 loop 语义（回所属 loop 再迭代）在判定产物中无表达
  - 正确形态：判定按 loop 角色渲染——loop-exit-gate 失败的结论应为"unit X 留在 inner loop 第 n+1 轮"而非"Gate G6 blocked"；unit 锚点推断桥（AUDIT-143 REQ-114 的 ADR 方向）
- **C-10 Gate 表校验空转——呈现性权威无事实约束**
  - 位置：verify_workflow.py `check_gate_consistency` L9917-9972（passed 证据检查 L9926-9937 `found` 未使用、分支 `pass`；passed-on-entry L9939-9944 分支 `pass`）
  - 机制：全局 Gate 表通过 bootstrap/status 呈现给每会话，但无任何 Check 实质校验其内部一致性——live 数据 L21"G11 pending" vs L38"G11 passed" vs L44"G11 通过"三处矛盾长期共存
  - 作用路径：校验注意力集中在任务证据完整性（evidence completeness），Gate 坐标自身成为不受质疑的状态权威——错误坐标也会被每会话重放
  - 正确形态：无论最终选择哪条修改方向，Gate/lane 坐标的机器校验必须先于语义切换补齐（否则 loop face 投影的将是同样无校验的数据）
  - **R0 修正补充发现（在案实例——三方矛盾）**：「DEC-133（2026-07-26，`archive/decisions/decisions-v0.1.0-0.78.0.md` L96/L101——VAL-008 dogfood PASS 28/0/1 + VAL-009 双外部类型 PASS〔shitu Android/mobile-app + python_game〕，RISK-037/042 关闭标准 8+8 项全 PASS，Loop Engineering 从 experimental/scaffolding 升级为 externally-validated runtime）↔ loop-role-mapping.md L5（仍滞留 0.66.1〔2026-07-17〕时点 NOT_MET 声明，DEC-133 之后九天未更新）↔ 本仓 dogfood 无 flow-unit-runtime.json（externally-validated runtime 在唯一真实宿主上从未激活，至 0.89.0）」——三份治理事实互斥且无任何 Check 发现漂移。**该矛盾是本报告主题「治理记录间事实漂移无一致性校验」（C-10 病理）的又一在案实例**：与前述 Gate 坐标三处矛盾（plan-tracker L21/L38/L44）同构——一处是呈现层数据漂移，一处是决策记录↔参考文档↔运行时事实的语义漂移。它同时校准本报告自身：初稿 RB-2 即因引用了滞留的 0.66.1 时点声明而失实（见 §6 RB-2 R0 修正）——漂移不仅误导校验器，也误导了引用它的分析报告。

---

## 4. loop 引擎接线度结论（能力清单 vs 每会话消费路径）

| 引擎能力 | 交付状态 | 每会话消费路径覆盖 | 判定 |
|---|---|---|---|
| loop 拓扑/fuse/pause-point 声明（registry L19-161） | 已交付（schema） | 无——bootstrap 不读该 registry | 已交付但不可见 |
| per-unit loop_state rollup（no_global_stage 契约） | 已交付+回归锁 | 无——仅 opt-in CLI `loop-rollup` | 已交付但不可见 |
| round 推导/fuse 判定/escalation | 已交付（pure 函数） | 无——调用方仅 loop_gate_processor（其自身事件链零运行，AUDIT-143 §2.0.2 实证，本仓 loop-event-log.jsonl 至今不存在） | 已交付且事件链未激活 |
| flow-unit 迁移/回滚（含备份） | 已交付 | 无——opt-in `loop-migrate`；本仓从未执行（flow-unit-runtime.json 不存在） | 已交付未使用 |
| loop 健康检查 | 已交付（advisory-only） | 无——opt-in `check-loop-health` | 已交付但不可见 |
| loop runtime 声明扫描（防 overclaim） | 已交付 | **部分覆盖**——installed_host/product_release 两处 claim 扫描进入常规校验（L16671/L21258） | 唯一接线面，但方向是守卫（阻止声称激活）而非投影 |
| plan-tracker 迁移期 Gate 表检测 | 已交付 | 无 | 已交付未使用 |

**一句话结论**：loop 引擎是一台已组装、有自检、但从未接入生产电网的发电机——常规校验里唯一的 loop 代码（claims 扫描）职责是防止任何人声称发电机已并网。0.74.0（AUDIT-143）诊断的"工具在仓库里，行为没有发生"在 0.89.0 的结构面**原样成立**；0.74/0.75 修复链（复审必达/推荐规则入契约）解决了行为契约的另一翼，未触及 loop 投影与激活模式。

---

## 5. 候选方案（≥2，只出方案不做决策）

### 5.0 比较标准（评估前定义——Architect 硬门槛）

| # | 标准 | 度量方式 |
|---|---|---|
| S-1 | 线性偏差消除度 | 用户四基准（§2.6 列头）的直接兑现比例；热数据/判定/数据模型/入口四层各有语义覆盖计分 |
| S-2 | DEC-097 继承度 | 与"重构式 loop 唯一模型 + gate-as-loop-exit + AI 循环一等公民"三项决议的一致程度 |
| S-3 | 迁移成本与风险 | 改动面（文件/模块计数）、God Module 约束（verify_workflow.py 26358 行，RISK-039）、测试矩阵破坏面（pytest 基线 4217P） |
| S-4 | 可回滚性 | 回滚路径的机器支持（既有 rollback 机制复用度）与数据可逆性 |
| S-5 | 对既有 Check/发布链生态的破坏 | check 族/发布门/manifest/投影一致性检查的适配量 |

### 5.1 候选 A——投影重解释（最小接线）：loop 语义进入热数据，判定权威暂不动

- **改动面**：① `bootstrap_aggregate.py` 增加 loop face——runtime 存在时投影 rollup_loop_state 输出（units/summary/no_global_stage），缺失时输出结构化"loop runtime 未激活"提示；`next_gate` 在 loop face 存在时降级为兼容字段并更名（如 `classic_next_gate`）；② 入口模板（commands/governance-init.md Step 7 注入模板，经 FIX-011 链投影三平台）模式确认句增加 loop 槽位；③ plan-tracker 模板增加可选 `## Loop 状态跟踪` 节（per-unit lane 表）与全局 Gate 表并存；④ SKILL.md 按需读取表登记 loop-role-mapping.md 为 Gate 检查必读。
- **迁移成本**：低-中。聚合层 1 文件 + 模板 3 处 + 模板节 1 个；无判定权威迁移、无数据迁移。预估改动 6~10 文件。
- **风险**：双坐标并存期 agent 仍可回落线性（classic 判定权威未动，next_gate 仍在输出）；8KB 投影预算挤压（loop face 需占预算，`_enforce_projection_budget` L791-851 的裁剪序列需新增位次）；"Gate 推进当目标"的行为诱因只被稀释未被移除。
- **回滚路径**：纯增量——删 loop face/还原模板即回滚；无数据迁移无不可逆操作。
- **DEC-097 继承关系**：部分继承——gate-as-loop-exit 语义进入可见层，AI 循环 pause-point 不触及；"loop 为唯一模型"未兑现（该决议明确否决过并存式，本候选实质是受控并存，需用户显式重新授权该偏离）。

### 5.2 候选 B——结构切换（DEC-097 完全落地）：loop 为唯一激活模型

- **改动面**：① `lifecycle-registry.json`：loop-engineering 进入 lifecycle_modes 并翻转 active/default（classic 降 compatibility-preset）；② loop-engineering-registry.json 从 schema-only 升级为判定权威：auto_judge_gate 判定源切换为 loop_gate_semantics + gate_execution_registry 按 loop 角色渲染；③ bootstrap gates 面替换为 loop face（next_gate 退役）；④ plan-tracker 模板：Gate 状态跟踪表 → per-unit lane 表；本仓 dogfood 执行 loop-migrate；⑤ core/stage-gates.md、core/lifecycle.md、task-gate-model.md 按 loop 词汇重写（workflow_model 枚举补 loop-engineering）；⑥ SKILL.md/三平台入口投影重写模式确认句与阶段跳跃防护语义；⑦ unit 锚点推断桥（AUDIT-143 REQ-114 的 ADR 先行）。
- **迁移成本**：高。判定权威迁移 + 数据模型迁移 + 核心文档层全量重写 + 三平台投影 + Check/测试矩阵重建（gate 相关 check 族、release 链 gate 引用、bootstrap 聚合测试）。预估 30+ 文件，跨至少 2 个版本批次（参照 0.88.0 B-12/B-13 执法激活的授权票模式：机制先行、翻转留授权票、分族切换）。
- **风险**：① 宿主激活缺位下的判定可用性风险（**R0 修正前提**：外部验证曾通过——DEC-133 以 VAL-008 dogfood PASS + VAL-009 双外部类型 PASS 关闭 RISK-037/042，其关闭标准含「非 game 泛化边界」项，故原稿仅引 VAL-006〔0.55 时点非 game 派生失败〕属过时证据；但验证通过 ≠ 宿主激活——本仓 dogfood flow-unit-runtime.json 至 0.89.0 不存在，迁移有效性在真实宿主仍为未激活口径，且 flow_unit_derive 当前默认输出 initiation 单元，L259）——候选 B 的进入条件 = 先在本仓执行 loop-migrate 并验证派生/判定/回滚全链（验证门模板可直接复用 DEC-133 的 8 项关闭标准清单）；② God Module 上叠加迁移复杂度（RISK-039 现役约束，DEC-097 当年即因此选择先出 ADR）；③ 行为回归面大（pytest 4217P 基线中 gate/bootstrap/projection 契约测试量大）。
- **回滚路径**：loop_migration.py 自带 rollback_migration + 备份（L41/L281-284 微秒级备份防碰撞）；lifecycle-registry 翻转可逆；入口模板按版本回退。数据面可逆性有机器支持。
- **DEC-097 继承关系**：完全继承——三项决议（唯一模型/一等公民/重构式）全部兑现；这正是 DEC-097 用户决策的原始形态，0.65~0.89 的 32 个发布版本停滞（统计口径见 §2.4 R0 修正）是该决策的执行欠账而非否决（无任何后继 DEC 推翻 DEC-097——DEC-133 关闭的 RISK-037/042 是外部验证标准满足，非方向变更）。

### 5.3 候选 C——混合渐进：per-unit lane 先行 + Gate 表降级为派生视图

- **改动面**：① 本仓 dogfood 先行 loop-migrate（flow-unit-runtime.json 落地）；② bootstrap 增加 loop face（同 A①）；③ Gate 表保留但模板标注"派生视图/兼容投影"（由 lane 表派生全局视图），写入规则：lane 表为权威、Gate 表不得手工直改；④ auto_judge_gate 默认路由 unit（unit 推断桥，消除 Wiring B 的 unit_id 手工传参）；⑤ 判定权威迁移**不做**——gate 判定仍走 classic registry，但结论渲染时附加 loop 语义行。
- **迁移成本**：中。数据迁移（本仓一次）+ 聚合层 + 模板 + unit 桥；判定权威不动。
- **风险**：① **中间态滞留**——classic+loop 双模型长期并存正是 DEC-097 用户决策时明确排除的选项 (b)（排除理由原话："双轨维护成本且不解决根因（线性心智模型仍在）"）；② 双写一致性新负担（lane 表与 Gate 表漂移——C-10 的校验空转使漂移无检测）；③ unit 桥的推断正确性风险（错误锚定比无锚定更糟，需 fail-closed）。
- **回滚路径**：migration rollback + 模板还原；派生关系删除即回到现状。
- **DEC-097 继承关系**：与决议方向冲突（DEC-097 明确否决并存式）——选择本候选 = 用户显式推翻/修订 DEC-097 的"重构式"前提，需新 DEC 入账。

### 5.4 比较矩阵（按 S-1~S-5）

| 候选 | S-1 线性偏差消除 | S-2 DEC-097 继承 | S-3 成本/风险 | S-4 可回滚 | S-5 生态破坏 |
|---|---|---|---|---|---|
| A 投影重解释 | 部分（热数据层；判定/数据模型仍线性） | 部分（并存=偏离原决议） | 低-中 | 高（纯增量） | 小 |
| B 结构切换 | 完整（四层全换） | 完全（原决议落地） | 高 | 中-高（机器 rollback 支持在） | 大（需分批授权票） |
| C 混合渐进 | 中（数据+投影层；判定层保留线性） | 冲突（需修订 DEC-097） | 中 | 中-高 | 中（双写一致性新负担） |

> 决策归用户（Design Reviewer 仅承担质量裁决——通过/条件通过/需修改——不含方案选择）。本报告不推荐具体候选——按 Architect 边界，关键架构决策经独立质量审查后由用户裁决。（R1 notes N-2 顺带修复 2026-09-26）

---

## 6. 蓝军挑战（≥3，独立 ID + 缓解措施）

- **RB-1：热数据投影未必是行为主因**。"bootstrap next_gate 拉回线性"与 AUDIT-143 实证的"行为规则在第四层按需文件才断链"可能竞争同一症状的解释权——若主因是注入链断链（规则不在上下文），改投影只是止痛。缓解：与 AUDIT-156（行为面）交叉归因；任何修复立项必须定义行为级验收（新会话不预读第四层文件仍执行 loop 语义——AUDIT-143 REQ-112 验收信号 4 同款），不能只验字段存在。
- **RB-2：宿主激活从未发生——把"线性偏差"换成"loop 失能"的风险仍在**（R0 修正：原稿前提「loop runtime 从未通过外部验证」被 DEC-133 证伪，时序错置——原引 loop-role-mapping.md L5 的 NOT_MET 是 0.66.1〔2026-07-17〕时点声明，早于 DEC-133〔07-26 关闭 RISK-037/042：VAL-008 dogfood PASS + VAL-009 双外部类型 PASS，Loop Engineering 已升级为 externally-validated runtime〕九天）。**修正后攻击向量**：原型级外部验证曾通过（3 项目原型），但验证通过 ≠ 宿主激活——唯一真实宿主（本仓 dogfood）的 flow-unit-runtime.json 至 0.89.0 不存在、loop-event-log.jsonl 不存在、迁移从未执行；DEC-133 验证的是引擎能力与迁移工具（VAL-009 的原型项目），不是本仓 dogfood 宿主的持续运行态；真实宿主项目激活 loop runtime 的有效性（migration → derive → 判定路由 → rollup 投影全链）在宿主侧仍无运行证据。缓解：候选 B 进入条件 = 在本仓 dogfood 执行完整迁移并验证全链（验证门直接复用 DEC-133 的 8 项关闭标准清单作为 checklist）；候选 A 不依赖激活，免疫此挑战；候选 C 因含本仓迁移步骤**不免疫**宿主激活风险——仅免疫「判定权威切换」面（arch 指出、R1 记录为 N-1；R1 notes 顺带修复 2026-09-26）。
- **RB-3：本报告的因果链是机制推断，非受控实验**。"next_gate/stage 投影 → agent 行为拉回线性"无 A/B 证据；用户观察到的具体行为样本（哪些会话、哪些推进动作）未取证。缓解：报告已将 H-1/H-2 列为显式假设（§7）；修复立项时先做行为取证（最近 N 会话的推进决策与 bootstrap 输出对照），再定改造范围——避免在未证实的因果上投入候选 B 级别的迁移成本。
- **RB-4：迁移面可能被低估——Gate 表结构是测试与发布链的隐性契约**。`## Gate 状态跟踪` 字面量出现在引擎校验（L4138/L7669）、migration 判据（loop_migration L242）、bootstrap 解析（L121）、测试 fixture（test_verify_workflow 20+ 处）、governance-init 模板（e2e 测试 4 处）——任何数据模型切换的真实改动面以这些消费点为准，而非模板本身。缓解：候选 B 必须 Like FEAT-064 分族翻转先例（机制交付 + 出厂 WARN + 翻转留授权票），且立项时先跑一次 Gate 结构消费点普查（grep 清单进 ADR），把 S-3 成本估算从"预估"降为"清点"。

---

## 7. 假设与事实分离

**事实**（文件/命令实证，可复查）：
- §2.1-2.5 全部带路径+行号的引用（文件直读/grep/glob 输出）
- 本仓 `.governance/flow-unit-runtime.json` 不存在；loop-event-log.jsonl 不存在（AUDIT-143 §322-324 记录 0.74 时点不存在，本次 glob 复核 flow-unit-runtime 仍不存在）
- SKILL.md grep `loop` 零命中；bootstrap_aggregate.py grep `loop` 零命中
- DEC-097 原文（归档 L16）、AUDIT-143 全文、loop-role-mapping.md 全文已实际读取
- DEC-133 原文（`.governance/archive/decisions/decisions-v0.1.0-0.78.0.md` L96/L101——VAL-008 dogfood PASS 28/0/1 + VAL-009 双外部类型 PASS、RISK-037/042 关闭标准 8+8 项全满足、"experimental/scaffolding 升级为 externally-validated runtime"）已实际读取（R0 修正轮补读）；`project/CHANGELOG.md` 版本条目计数 32 条已 grep 实计（R0 修正轮）

**假设**（机制推断，显式标记，未受控验证）：
- **H-1**：bootstrap 热数据的 next_gate/stage 字段对 agent 推进行为有因果影响（注意力锚定机制合理、位置权重高，但无行为实验——见 RB-3 缓解路径）
- **H-2**：用户 2026-09-26 观察到的"往下一个 Gate 推进"行为与上述结构投影同源（与 AUDIT-143 断链链互补而非互斥）；用户反馈的具体行为样本未取证
- **H-3**：SKILL.md/CLAUDE.md/AGENTS.md 每会话必然注入（平台机制声明 + AUDIT-143 §2.0.1 的 persona 逐字比对先例；本次未逐平台复核注入链）
- **H-4**：check_gate_consistency 的空转（C-10）是无意为之的实现缺陷而非有意设计（无文档声明该行为是预期）

## 8. 未验证项（继承 + 新增）

| # | 项 | 状态 | 建议验证路径 |
|---|---|---|---|
| 1 | process_gate_result 在 classic 宿主的运行时行为 | 继承 AUDIT-143 §4-1（静态推演未运行验证） | Developer/QA 在 fixture 调用 review-record 观察 wiring.reason |
| 2 | loop-event-log.jsonl 在 0.89.0 是否仍不存在 | 本次未直接 glob 该文件名（以 AUDIT-143 时点 + flow-unit-runtime 不存在旁证） | 补一次 glob 即可闭合 |
| 3 | flow_unit_derive/loop-migrate 在本仓 dogfood 宿主的全链可用性（derive → 迁移 → 判定路由 → rollup 投影） | RB-2 缓解依赖；DEC-133 外部验证曾 PASS 双类型原型（shitu mobile-app + python_game），但验证对象是原型项目而非本仓宿主的持续运行态；flow_unit_derive 当前默认输出 initiation 单元（L259） | 本仓执行 loop-migrate dry-run → apply → 全链验证（候选 B 前置；checklist 复用 DEC-133 8 项关闭标准） |
| 4 | 用户观察样本与结构投影的行为级对照 | RB-3 缓解依赖 | AUDIT-156 行为面 + 最近会话推进决策取证 |
| 5 | `## Gate 状态跟踪` 消费点完整普查 | RB-4 缓解依赖；本报告已列主要消费点（grep 主要命中已核），未穷尽测试 fixture | 立项时 grep 清单进 ADR |

---

## 9. 边界声明

- 本报告为只读分析产物；除本文件外零文件修改，未触碰 `.governance/` 治理记录、产品代码与平台入口文件。
- 所有结论附文件路径+行号；历史锚点（DEC-097/AUDIT-143/loop-role-mapping.md）实际读取后才引用。
- 候选方案为结构方向，不含技术选型决策与实施优先级裁决——决策归 Design Reviewer 审查 + 用户确认（与 AUDIT-156 行为面报告汇合后统一裁决）。
- UTF-8 编码；与 AUDIT-156 的汇合点：§3 C-04/C-06/C-08（投影与入口层）是行为面与结构面的共享根因候选，审查时应双报告对照归因。
