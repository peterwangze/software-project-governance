# 默认产品形态方案

本文件是 `PLAN-003` 的正式方案文档，用于基于 `RESEARCH-001` 明确 `software-project-governance` workflow 的默认产品形态、分层结构、接入矩阵与边界约束。

## 目标

本方案解决的问题不是“如何继续扩 repo-local 入口”，而是：

1. workflow 本体应该以什么形态存在，才能保持长期稳定。
2. agent 私有入口应该承担什么职责，避免和 workflow 本体耦合。
3. 默认推荐哪类接入方式，哪些方式只保留为 fallback 或样例。
4. 后续 Claude、Codex、Gemini 以及国内 agent CLI 应如何在统一模型下扩展。

## 方案摘要

默认产品形态采用“三层结构 + 三档接入矩阵”：

1. workflow 本体层
   - 承载协议、规则、模板、样例、研究与验证资产。
   - 是唯一长期事实源。
2. agent 入口投影层
   - 负责把不同 agent 的原生入口映射到 workflow 本体。
   - 只保存最薄入口定义、加载顺序和回写约束。
3. 外部能力层
   - 承载 MCP、tool server、headless runner、plugin/extension 等低侵入能力。
   - 优先作为默认产品方向。

默认接入策略分三档：

- 默认推荐：user/global skill、plugin/extension、MCP、headless command
- 条件推荐：project-local 入口、repo rules、上下文指针文件
- 不推荐作为默认主线：把完整 workflow 规则直接复制进用户仓库并长期扩张

## 为什么不是 repo-local 默认主线

`RESEARCH-001` 已确认以下事实：

- Claude、Codex、Gemini 都存在“用户环境级”或“仓库外部”的接入能力。
- repo-local 入口虽然可运行，但侵入性高、可替换性差、容易让 workflow 和用户仓库资产绑定。
- repo-local 更适合样例验证、fallback 或团队显式绑定场景，而不是默认产品方向。

因此，默认产品形态不能再以 `CLAUDE.md`、`.claude/skills/`、`adapters/codex/*` 之类 repo-local 接法为中心展开。

## 分层设计

### 1. Workflow 本体层

本体的运行时承载位置为 `skills/software-project-governance/`（agent 通过插件市场安装后唯一能访问的目录），包含：

- `skills/software-project-governance/SKILL.md`（入口，内嵌核心行为协议）
- `skills/software-project-governance/references/`（lifecycle、stage-gates、profiles、onboarding、interaction-boundary）
- `skills/software-project-governance/stages/`（子工作流和 stage skills）
- `skills/software-project-governance/main-workflow.md`、`TOOLS.md`

仓库中的 `workflows/software-project-governance/` 承载**设计时资产**，不重复运行时本体内容：

- `workflows/software-project-governance/manifest.md`
- `workflows/software-project-governance/research/`
- `workflows/software-project-governance/templates/`
- `workflows/software-project-governance/examples/`（历史迁移指针）

其他共享资产：
- `protocol/`
- `.governance/`（活跃治理记录）
- `scripts/verify_workflow.py`

职责：

- 定义 workflow 的目标、生命周期、Gate、模板和单一事实源。
- 沉淀大型软件公司的项目管理经验与 agent 集成调研。
- 作为所有 agent 共享的事实依据。

边界：

- 不面向单一 agent 私有格式做深度定制。
- `skills/` 和 `workflows/` 之间不重复内容：运行时规则和子工作流只在 `skills/`；设计文档和模板只在 `workflows/`。

### 2. Agent 入口投影层

这一层负责“映射”，不负责“持有完整规则”。

当前已存在的投影层样例：

- Claude：`CLAUDE.md`、`.claude/skills/software-project-governance/SKILL.md`
- Codex：`adapters/codex/adapter-manifest.json`、`adapters/codex/launch.py`
- Gemini：`adapters/gemini/README.md`

职责：

- 定义该 agent 如何触发 workflow。
- 指向 workflow 本体层的读取顺序与输出规则。
- 描述遇到 Gate 未通过时如何阻断。
- 描述如何验证当前入口接法是否完整。

边界：

- 不复制完整 workflow 规则和模板。
- 不维护独立版本的计划、证据、决策、风险。
- 不把样例入口误写为默认产品方案。

### 3. 外部能力层

这是后续默认产品形态的主抓手，优先承载：

- MCP / tool server
- plugin / extension
- global skill / shared commands
- headless workflow runner
- CI / automation integration

职责：

- 把 workflow 能力从用户仓库内移到外部可复用层。
- 提供更低侵入、更可替换的统一接入方式。
- 为多 agent 复用创造统一接口。

边界：

- 不直接替代 workflow 本体层。
- 不绕开样例与验证资产单独演化。
- 不在缺少正式研究或官方能力依据时抢跑实现。

## 默认接入矩阵

| Agent | 默认推荐 | 条件推荐 | 样例 / fallback | 当前不推荐 |
| --- | --- | --- | --- | --- |
| Claude | personal skill、plugin skill、MCP | project skill、slash commands | `CLAUDE.md` + project skill | 以仓库级入口承载完整 workflow 本体 |
| Codex | 全局安装 + external skill/plugin/config、MCP、headless runner | repo rules、hooks、`AGENTS.md` 投影 | `adapters/codex/*` | 把 repo-local adapter 扩展成默认唯一入口 |
| Gemini | MCP、custom commands、headless runner、extensions | `GEMINI.md` 最薄投影 | `adapters/gemini/README.md` | 在缺少更多验证前深做 repo-local 方案 |
| 国内 agent CLI | MCP、external runner、shared command | 项目级上下文投影 | 待 Gemini 兼容抽象后再补 | 提前绑定单一目录布局 |

## 目录与资产演进建议

当前目录已按"运行时正本在 skills/、设计资产在 workflows/"原则重组：

- `skills/software-project-governance/`
  - 运行时唯一事实源，agent 通过插件市场安装后访问。包含 SKILL.md、references/、stages/、main-workflow.md、TOOLS.md。
- `workflows/software-project-governance/research/`
  - 继续承载调研结论与产品形态方案。
- `workflows/software-project-governance/templates/`
  - 计划、证据、决策、风险等记录模板（governance-init 命令的输入）。
- `adapters/`
  - 明确为探索性投影样例、调试入口、fallback 或兼容占位。
- 后续如启动正式低侵入实现，可考虑新增：
  - `integrations/`：按集成模式组织安装/接入说明
  - `services/`：MCP 或外部 workflow service
  - `packages/`：可安装分发资产

这些新增目录只有在后续实施真正需要时才建立，不提前造目录。

## 对当前主线任务的影响

### 对 `PLAN-003`

- 本任务的完成标志，不是新增更多入口，而是明确默认产品形态与接入边界。
- 后续 README、协议、样例都应以本方案为准。

### 对 `DESIGN-005`

- `plugin-contract` 已经切到集成模式优先，但后续若继续细化，应围绕“三层结构 + 三档矩阵”展开。

### 对 `DOC-001`

- README 后续应增加对默认产品形态方案的引用，避免 README 再次承担全部设计说明。

### 对 `OPS-001`

- Gemini 与后续国内 agent CLI 兼容路线，应优先复用外部能力层抽象，而不是先做 repo-local 入口。

## 成功标准

`PLAN-003` 视为完成，需要同时满足：

1. 有正式方案文档说明默认产品形态。
2. 样例计划中 `PLAN-003` 有明确产出物与状态变化。
3. 证据、决策、风险至少各回写一处，形成治理闭环。
4. 校验脚本已覆盖方案文档存在性与关键片段。
5. 验证命令通过。

## 暂不做的事

- 不直接实现新的 MCP server 或 plugin/extension。
- 不在缺少官方依据的前提下定义统一 marketplace 分发方案。
- 不新增更多 repo-local adapter 入口来伪装进展。

## 下一步建议

1. 基于本方案将 `PLAN-003` 在样例计划中标记完成。
2. README 后续如需收敛，应链接本方案而不是继续堆叠长说明。
3. 进入下一轮设计时，优先选择一个外部能力层抓手做最小验证，例如 MCP 或 headless runner。
