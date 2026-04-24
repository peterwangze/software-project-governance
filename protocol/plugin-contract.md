# Plugin Contract

本文件定义一个 workflow plugin/skill 在本仓库中的最小承载约定。

## 目标

让同一套流程资产可以被 Claude、Codex 以及后续的 Gemini、国内 agent CLI 以统一事实源、低侵入接入和可替换投影的方式消费，而不是被某一种 repo-local 目录结构绑死。

## 最小承载单元

每个 workflow plugin/skill 至少应包含以下内容：

1. `manifest`
   - 描述 workflow 的名称、目标、版本、支持 agent、关键能力。
2. `research`
   - 记录来源于大型软件公司的项目管理经验，以及对主流 agent 集成方式的调研结论。
3. `rules`
   - 把经验转成生命周期、Gate、留痕和阻断规则。
4. `stages`
   - 每个阶段的子工作流定义，包含进入条件、活动清单、产出物标准、退出条件和 Gate 映射。
5. `stage skills`
   - 每个阶段的具体事务 skill/script，有触发条件、输入输出和独立执行能力。
6. `templates`
   - 提供计划、证据、决策、风险等记录模板。
7. `examples`
   - 提供真实样例，证明 workflow 可运行。
8. `integration contract`
   - 回答不同 agent 如何触发、加载、回写和验证 workflow。
9. `validation`
   - 提供校验脚本或校验规则，验证资产完整性与一致性。

## 自动化能力分级

本工作流向用户承诺的核心体验是"自动化"。但"自动"在不同实现层级上有根本不同的含义。本协议将自动化分为三级，每一级有不同的能力边界、前提条件和用户预期。

### A 级：Agent Protocol Automation（行为协议自动化）

**定义**：agent 加载 workflow 行为协议后，按 MUST/MUST NOT 规则执行治理动作。

- 证据记录、Gate 检查、风险更新、状态跟踪——由 agent 读规则、记住并手动执行
- 执行质量完全取决于 agent 是否加载并遵守协议
- 没有外部机制阻止 agent 跳过或遗忘治理动作

**前提条件**：
- agent 能访问 workflow skill 文件
- agent 加载并遵守行为协议（MUST/MUST NOT）
- 项目已初始化 `.governance/`

**当前状态**：**已实现**（本仓库自身运行在这一级）

**用户预期**：agent "会记得做"治理动作，但不保证每次都做。适合个人项目和希望低成本接入的团队。

### B 级：CLI-Enforced Automation（脚本强制自动化）

**定义**：在 A 级基础上，增加可执行脚本/命令对关键治理动作进行强制验证。

- CLI 脚本检查证据完整性、Gate 状态一致性、风险过期
- pre-commit hook 或 CI 触发验证
- agent 仍然手动执行治理动作，但脚本能发现遗漏并阻止继续

**前提条件**：
- A 级前提条件全部满足
- 项目安装了验证脚本（`verify_workflow.py` 或等效工具）
- （可选）pre-commit hook 或 CI 集成

**当前状态**：**部分实现**（`verify_workflow.py` 有文件存在性检查，但缺少治理完整性检查）

**用户预期**：遗漏的治理记录会被脚本发现，不能静默跳过。适合团队项目和希望有质量底线的正式产品。

### C 级：System Automation（系统自动化）

**定义**：治理动作由外部系统（hook、daemon、MCP server、CI runner）自动触发和执行，不依赖 agent 记忆。

- 任务完成时自动捕获证据（如 git commit hook）
- 阶段推进时自动触发 Gate 检查
- 风险状态变化时自动通知
- agent 角色从"执行者"退化为"建议者"

**前提条件**：
- B 级前提条件全部满足
- 外部能力层（MCP server / headless runner / CI runner）已部署
- 系统具有文件系统访问权和项目根目录感知

**当前状态**：**未实现**（MCP / headless runner 仅有协议样例，无可用实现）

**用户预期**：治理是"透明的"——agent 正常工作，治理自动发生。适合大型项目和合规系统。

### 分级使用指引

| 项目类型 | 最低推荐级别 | 说明 |
|---------|------------|------|
| 个人探索项目 | A | agent 协议足够，不需要额外设置 |
| 团队正式产品 | B | CLI 强制检查防止遗漏 |
| 大型/合规项目 | C | 系统级自动化确保可审计 |

README 和对外文档必须显式说明当前各项能力处于哪一级，禁止用笼统的"自动"一词同时指向 A 级和 C 级能力。

## 三层承载模型

本协议的默认结构是：`workflow 本体层 + agent 入口投影层 + 外部能力层`。

### 1. Workflow 本体层

这一层是 workflow 的运行时唯一事实源。agent 在运行态通过插件市场安装后只能访问 `skills/` 目录，因此**本体层的运行时承载位置是 `skills/software-project-governance/`**，至少包括：

- `SKILL.md`（入口，内嵌核心行为协议）
- `references/`（lifecycle、stage-gates、profiles、onboarding、interaction-boundary）
- `stages/`（每个阶段的 sub-workflow.md + stage skills）
- `main-workflow.md`（总入口与场景匹配）
- `TOOLS.md`（统一工具索引）

仓库中的 `workflows/software-project-governance/` 承载**设计时资产**，不重复本体层内容：

- `manifest.md`（workflow 元数据）
- `research/`（企业经验、产品形态、兼容抽象等调研结论）
- `templates/`（计划、证据、决策、风险等记录模板）
- `examples/`（历史样例，活跃治理记录已迁移至项目级 `.governance/`）

职责：

- 定义 workflow 的目标、生命周期、Gate、模板和治理记录格式。
- 沉淀产品形态、兼容抽象与调研结论。
- 为所有 agent 提供统一读取顺序与回写约束。

边界：

- 不绑定单一 agent 私有格式。
- 本体层内容在 `skills/` 和 `workflows/` 之间不重复（`skills/` = 运行时正本，`workflows/` = 设计时补充资产）。

### 2. Agent 入口投影层

这一层只负责把 agent 原生能力映射到 workflow 本体层。

由于插件市场的自包含约束，`skills/` 目录同时承担了**本体层（Tier 1）和入口投影层（Tier 2）的双重角色**。投影层不再需要独立的规则副本目录——`skills/` 本身就是 agent 唯一能访问的完整 workflow。

投影层的最小承载形式：

- `CLAUDE.md` / `AGENTS.md` 等 bootstrap 指针（无条件前置检查，不依赖 skill 加载状态）
- `.governance/` 项目级治理数据（plan-tracker、evidence-log、decision-log、risk-log）
- plugin marketplace manifest（`plugin.json`、`marketplace.json`）

禁止承载：

- 独立版本的计划、证据、决策、风险记录
- 只适用于单一 agent 的第二套主计划

### 3. 外部能力层

这一层承载用户仓库外部的可复用能力，优先作为默认产品方向。

典型形式：

- user/global skill
- plugin / extension
- MCP server / tool server
- headless runner / shared command
- CI / automation integration

职责：

- 降低对用户仓库的侵入。
- 提供跨仓库、跨 agent 的复用抓手。
- 把可外置的能力尽量留在仓库外部。

## 集成模式回答的问题

一个 agent 集成方式至少要回答以下问题：

- 何时触发这个 workflow
- 集成入口位于哪里：全局安装、命令入口、MCP、外部服务、项目级投影或其他承载形式
- agent 在执行过程中应读取哪些规则和模板
- 输出或更新哪些记录文件
- 遇到 Gate 未通过时应如何阻断
- 如何验证当前执行结果是否可信
- 用户替换或移除当前集成方式时，哪些项目资产需要保留，哪些应保持外置

## Skill / Plugin 行为描述要素

对任一 skill / plugin / command / service 描述，至少应显式给出以下要素：

1. trigger
   - 何时由用户、agent 或自动化流程触发。
2. load surface
   - 以哪种载体接入：user/global、external capability、project-local projection 或 repo-local sample。
3. read order
   - 进入 workflow 后按什么顺序读取 manifest、rules、templates、examples 或 research。
4. write-back targets
   - 允许更新哪些事实源文件，禁止新增哪些平行状态文件。
5. gate behavior
   - Gate 未通过时如何阻断、降级或回退。
6. validation
   - 如何运行校验命令，确认当前接入方式与 workflow 本体一致。
7. replacement boundary
   - 当用户替换 agent 或接入方式时，哪些资产应留在 workflow 本体层，哪些资产应直接移除。

## 集成模式优先级

在没有额外约束时，优先按以下顺序评估集成方式：

1. 全局可复用能力
   - 例如 user skill、全局配置、共享命令入口。
2. 低侵入外接能力
   - 例如 MCP server、tool server、sidecar service。
3. 项目级显式绑定
   - 例如 project skill、repo rules、仓库级指针文件。
4. repo-local 样例或 fallback
   - 仅在前述方式不成立，或需要做最小可运行验证时使用。

默认推荐的是“外置能力 + 最薄投影”，不是“把 workflow 本体复制进用户仓库”。

## 默认接入要求

无论面向哪种 agent，默认接入方案都必须满足以下要求：

- 继续复用 workflow 本体层，不复制规则、模板和治理日志。
- 优先使用外部能力层或最薄投影层。
- 保持事实源集中在 `.governance/` 等项目级统一记录位置。
- 能说明校验命令、Gate 阻断和回写约束如何稳定执行。

如果某种接入方式只能通过新增大量 repo-local 资产才能成立，它默认只能被视为样例、fallback 或团队级显式绑定方案。

## 兼容原则

- Claude / Codex / Gemini 的真实集成方式应以官方能力边界为准，不预设 plugin market 或统一 registry 必然存在。
- 同一 workflow 的事实源必须共享，不允许为不同 agent 维护不同版本的计划、风险、证据。
- repo-local 入口只能证明“当前仓库可运行”，不能自动推导为“这是最终用户的默认最佳接法”。
- 所有面向最终用户的推荐方案，都应先经过集成方式调研，再进入主线计划。
- 国内 agent CLI 的扩展应优先复用统一兼容抽象，而不是先按目录结构扩张新的 adapter。

## 当前建议目录布局

当前目录布局服务于”运行时正本在 skills/、设计资产在 workflows/、外部能力层后续扩展”的原则：

- `skills/<workflow-id>/`：**运行时唯一事实源**（agent 通过插件市场安装后访问的完整 workflow）
  - `SKILL.md`：入口，内嵌核心行为协议
  - `references/`：生命周期、Gate、Profile、onboarding、交互边界
  - `stages/`：每个阶段的子工作流和 skill/script
  - `main-workflow.md`：总入口与场景匹配
  - `TOOLS.md`：统一工具索引
- `workflows/<workflow-id>/`：**设计时资产**（不重复 skills/ 的运行时内容）
  - `manifest.md`：workflow 元数据
  - `research/`：企业经验、产品形态、兼容抽象等调研结论
  - `templates/`：计划、证据、决策、风险模板
  - `examples/`：历史样例（活跃治理记录已迁移至项目级 `.governance/`）
- `protocol/`：通用协议
- `adapters/<agent>/`：历史探索性投影样例（已废弃，保留为对比基线）
- `scripts/`：校验脚本

如后续确定更适合的承载形态，可增加：

- `integrations/`：按集成模式组织的说明或安装资产
- `services/`：MCP 或外部服务实现
- `packages/`：全局安装或分发相关资产

是否存在 `adapters/<agent>/`，不决定 workflow 是否成立；它只是某一类投影或样例的承载方式。

## 当前仓库中的 plugin 目标

当前仓库的首个 workflow plugin 是：

- `software-project-governance`

它的目标是：

- 将大型软件公司的软件项目管理经验转成 agent 可消费的治理流程。
- 确保项目目标不偏离。
- 确保过程数据可信、可维护、可复盘。
- 在主流 agent 的真实集成方式约束下，找到低侵入、可替换的承载方案。
- 让后续 Claude、Codex、Gemini 与国内 agent CLI 继续共用同一套 workflow 本体。

## Agent 适配准入标准

任一 agent 正式进入主线适配前，必须回答以下准入问题。未能完整回答的 agent 只能停留在兼容预研或样例验证阶段，不得占用主线执行优先级。

### 必答准入问题

1. **默认 load surface**
   - 该 agent 默认通过哪种承载形态接入：user/global skill、plugin/extension、MCP、headless command、project-local projection、repo-local sample？
   - 是否有官方文档支撑该承载形态？

2. **write-back 边界**
   - 该 agent 能否将执行结果回写到项目级统一事实源（`.governance/` 四类文件）？
   - 是否存在 agent 私有状态文件、独立日志或绕开统一 write-back targets 的路径？

3. **Gate 阻断语义**
   - 该 agent 是否支持在 Gate 未通过时阻断后续阶段推进？
   - 阻断后是否允许自动降级为建议通过？

4. **validation 能力**
   - 该 agent 是否能执行 `python scripts/verify_workflow.py` 或等价校验命令？
   - 校验失败后是否能阻止声称"已完成"？

5. **replacement boundary**
   - 替换该 agent 时，哪些资产必须保留，哪些可以移除？
   - agent-specific wrapper 是否会突破 `replacement_boundary` 中的 `replace` 列表？

6. **structured output 能力**
   - 该 agent 是否能输出结构化的 `read_order`、`write_back_targets`、`gate_check`、`validation`、`replacement_boundary`？
   - 是否存在只能输出自由文本、无法映射到 shared command contract 的限制？

### 优先级规则

1. **共同抽象先于 agent 适配。** 任何 agent 适配都必须在共同抽象基座补强完成之后启动。
2. **agent 适配按目标优先级排队。** 当前优先级为 Claude -> Codex -> Gemini / 国内 agent CLI。
3. **优先级由用户确认。** 如用户未显式调整，默认沿用上述顺序。
4. **研究结论不等于执行优先级。** 已有兼容研究文档的 agent（如 Gemini、国内 agent CLI）不因研究完成而提前占用执行前排。

### 默认推荐接法判定标准

一种接法被判定为"默认推荐"时，必须同时满足以下条件：

1. **低侵入**：不需要把 workflow 本体复制进用户仓库，不修改用户项目级文件。
2. **可替换**：用户替换或移除该接法时，workflow 本体和治理记录不受影响。
3. **共享事实源**：接法产生的治理记录统一写入 `.governance/` 四类文件，不维护第二套事实源。
4. **可验证**：有明确的校验命令，且校验失败时能阻止声称完成。
5. **可自动化**：能映射到 shared command contract 或 headless runner 样例的结构化语义。

未能同时满足以上五条的接法，只能作为条件推荐、样例、fallback 或团队级显式绑定方案。

## 冲击场景（Shock Scenarios）

共同抽象基座必须能承受以下冲击，否则不能被视为强基座。每个冲击场景都应有对应的验证手段。

### SC-1：Agent 能力缺口

- **场景**：某个 agent 不支持 structured output 或无法执行校验命令。
- **冲击**：可能导致该 agent 无法通过准入标准，只能停留在样例或 fallback 阶段。
- **验证手段**：在 `DESIGN-007` 或 `DESIGN-008` 阶段，显式回答六项准入问题，任一不通过则该 agent 不进入正式主线。

### SC-2：输出不稳定

- **场景**：某个 agent 在不同执行轮次中输出格式不一致，导致 `gate_check` 或 `validation` 结果漂移。
- **冲击**：可能破坏治理记录的可追溯性。
- **验证手段**：在 Claude 正式接法验收（`ACCEPT-002`）中，至少执行两轮同任务执行并比对输出一致性。

### SC-3：项目级配置冲突

- **场景**：用户项目已有 `CLAUDE.md`、`.claude/skills/` 或其他 agent 配置文件，与 workflow 的默认投影冲突。
- **冲击**：可能导致 workflow 入口被覆盖或静默失效。
- **验证手段**：在 Claude 正式接法方案中，显式说明如何在有冲突时降级或共存，而不是假设用户项目为空白。

### SC-4：运行态分叉

- **场景**：headless runner、MCP tool 或某个 agent 的 custom command 为了适配特定场景，新增私有字段或私有状态文件。
- **冲击**：可能破坏 shared command contract 的单一事实源约束。
- **验证手段**：在 `CI-002` 校验脚本中增加字段边界检查，确保运行态输出不包含 contract 未定义的字段。

### SC-5：Repo-local 回潮

- **场景**：后续实现中因路径依赖，再次把 repo-local 入口当成默认推荐写入 README 或协议。
- **冲击**：可能与 `repo-local-termination-note.md` 的正式终止说明矛盾。
- **验证手段**：在 `CI-002` 校验脚本中保留 repo-local 降级定位的片段检查，防止 README 再次将其写成默认主线。

### SC-6：Agent-specific wrapper 私有字段膨胀

- **场景**：不同 agent 的 command wrapper 各自新增 `agent_metadata`、`platform_context`、`session_state` 等非 contract 字段。
- **冲击**：可能导致 shared command contract 的 `replacement_boundary` 失效，不同 agent 的 wrapper 变得不可互换。
- **验证手段**：在 `external-command-contract.md` 中明确 required / optional 字段边界，并在 `CI-002` 中增加 wrapper 字段白名单检查。