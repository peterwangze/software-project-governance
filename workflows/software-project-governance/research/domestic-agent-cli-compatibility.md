# 国内 agent CLI 兼容抽象

本文件作为 `MAINT-003` 的正式输出，用于定义 `software-project-governance` workflow 面向国内 agent CLI 的兼容抽象、能力分层、接入顺序与边界约束。

## 目标

本方案解决的问题不是“要不要立刻适配某一个国内 agent CLI”，而是：

1. 在外部生态差异较大的前提下，先抽象一套稳定的兼容判断模型。
2. 明确哪些能力必须复用 workflow 本体层，哪些只属于 agent 投影层或外部能力层。
3. 给后续接入国内 agent CLI 提供统一检查清单，避免每接一个 agent 都重新发明目录结构。
4. 在缺少统一市场标准时，仍保持低侵入、可替换和单一事实源。

## 兼容背景

当前国内 agent CLI 生态存在以下共性：

- 能力形态差异大，既有命令式 CLI，也有带项目上下文文件、插件、MCP 或服务端扩展能力的实现。
- 官方标准和文档成熟度不一致，能力边界可能快速变化。
- 项目级上下文绑定通常存在，但不应默认等同于 workflow 本体承载方式。
- 对自动化、命令编排、结构化输出的支持程度，是决定是否适合接 workflow 的关键因素。

因此，国内 agent CLI 的兼容路线不能直接复制 Claude、Codex、Gemini 的表面形式，而应先抽象能力接口，再决定投影方式。

## 兼容抽象

统一按三层结构评估国内 agent CLI：

### 1. Workflow 本体层

始终复用：

- `protocol/`
- `workflows/software-project-governance/rules/`
- `workflows/software-project-governance/templates/`
- `workflows/software-project-governance/examples/`
- `workflows/software-project-governance/research/`
- `scripts/verify_workflow.py`

要求：

- 不因接入新的国内 agent CLI 而复制第二套规则、模板或样例记录。
- 计划、证据、决策、风险继续共用同一套事实源。

### 2. Agent 入口投影层

仅允许承载：

- 上下文指针文件
- command / slash command / preset prompt
- 入口说明与读取顺序
- Gate 未通过时的阻断说明

要求：

- 投影层只负责把 agent 的原生能力映射到 workflow 本体。
- 不允许把项目级入口文件扩张成完整 workflow 容器。

### 3. 外部能力层

优先评估：

- MCP 或兼容的 tool server 协议
- external runner / shared command
- headless CLI / JSON 输出
- CI / automation integration

要求：

- 优先把可复用能力放在用户仓库外部。
- 如果 agent 不支持标准 MCP，也优先寻找等价的外接工具协议，而不是先退回 repo-local 方案。

## 默认接入顺序

后续适配任一国内 agent CLI 时，按以下顺序推进：

1. external runner / shared command
   - 先验证是否支持稳定命令入口、脚本调用、非交互执行或结构化输出。
2. MCP / tool protocol
   - 如支持结构化工具扩展，优先用它承载 Gate 检查、状态查询与验证动作。
3. 项目级最薄投影
   - 仅在需要仓库内显式绑定时，增加最小上下文指针文件。
4. 探索性 adapter 样例
   - 只在前述方式都无法表达时，才用 repo-local adapter 做样例或 fallback。

## 能力检查清单

接入一个新的国内 agent CLI 前，至少回答以下问题：

1. 是否支持非交互执行、批处理或脚本调用？
2. 是否支持 JSON、结构化文本或其他可验证输出？
3. 是否支持命令扩展、自定义 commands、slash commands 或预设 prompt？
4. 是否支持 MCP、tool server 或等价的外部工具协议？
5. 是否要求项目级上下文文件？如果需要，它能否保持在最薄投影层？
6. 是否允许把校验命令、Gate 阻断和回写约束稳定地固化下来？

若以上问题大部分答案是否定，则该 agent 只适合作为条件兼容或观察对象，不应立即进入正式实现主线。

## 分类策略

根据能力成熟度，将国内 agent CLI 分为三档：

- 默认推荐
  - 支持 external runner / commands，且具备结构化输出或外部工具能力。
- 条件推荐
  - 支持项目级上下文绑定，但外部扩展能力较弱，需要最薄投影配合。
- 样例 / fallback
  - 只能通过 repo-local 说明文件或弱绑定方式接入。
- 当前不推荐
  - 不支持稳定命令入口，且无法保证 Gate、验证、回写行为可重复。

## 与 Gemini 路线的关系

`OPS-001` 已确认 Gemini 兼容优先走 `external runner / MCP / custom commands + 最薄投影`。

`MAINT-003` 进一步确认：

- 国内 agent CLI 默认复用同一抽象，不单独发明第二套产品形态。
- Gemini 路线是国内 agent CLI 兼容的第一参考对象，但不是唯一模板。
- 只有当某个国内 agent CLI 的能力边界明显不同，才补充专有约束，而不是先改 workflow 本体。

## 当前不做

- 不点名绑定某一个国内 agent CLI 为唯一主线。
- 不在缺少正式验证前新增 `adapters/<domestic-agent>/` 目录。
- 不提前定义统一 marketplace、registry 或分发协议。
- 不为国内 agent CLI 维护独立的计划、证据、决策、风险日志。

## 成功标准

`MAINT-003` 视为完成，需要同时满足：

1. 有正式文档定义国内 agent CLI 的兼容抽象。
2. 文档明确三层结构、默认接入顺序与能力检查清单。
3. 样例、证据、决策、风险至少各回写一处。
4. 校验脚本已覆盖文档存在性和关键片段。
5. 验证命令通过。

## 下一步建议

1. 若要进入实现验证，优先选一个支持 external runner 或 MCP 的国内 agent CLI 做最小样例。
2. 将验证结果继续回写到 `examples/`，而不是在 adapter 层单独维护状态。
3. 如果某个国内 agent CLI 只支持项目级上下文文件，也应坚持“最薄投影”原则。 
