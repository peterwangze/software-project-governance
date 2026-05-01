# External Command Contract

本文件定义 `software-project-governance` workflow 在外部能力层中的最小 shared command / external runner 契约，用于把 `MAINT-004` 的验证方案收敛成可被不同 agent 复用的统一命令接口样例。

## 目标

本契约解决的问题不是“为某个 agent 单独做一个命令包装”，而是：

1. 给 Claude、Codex、Gemini 与国内 agent CLI 提供同一套最小 command 语义。
2. 明确外部能力层 command 至少应接收什么输入、产出什么输出。
3. 保证 command 只映射 workflow 本体层，不复制第二套规则或状态文件。
4. 为后续 MCP tool、headless runner 或 automation integration 提供稳定基线。

## command id

默认 command id：`software-project-governance.run`

这是一个 shared command / external runner 样例标识，不绑定某一个具体 agent 的私有命名规则。

## 最小输入

调用方至少需要提供以下输入：

1. `workflow_id`
   - 默认值：`software-project-governance`
   - 用于声明当前 command 要加载的 workflow 本体。
2. `entry_task`
   - 用于声明当前推进的样例任务，例如 `MAINT-005`。
   - 不允许省略，否则 command 无法绑定计划事实源。
3. `stage`
   - 用于声明当前阶段，例如 `maintenance`。
   - 必须与生命周期和 Gate 口径一致。
4. `goal`
   - 用于声明本次执行目标，避免 command 只剩“跑一下”的空触发。

## 最小输出

command 至少需要产出以下结构化结果：

1. `read_order`
   - 明确进入 workflow 后需要读取的资产顺序。
2. `write_back_targets`
   - 明确允许回写的事实源。
3. `gate_check`
   - 明确本次执行对应的 Gate 与阻断条件。
4. `validation`
   - 明确执行后的校验命令。
5. `replacement_boundary`
   - 明确替换 agent 或替换 command 载体时，哪些资产保留、哪些资产可移除。

## read order

`software-project-governance.run` 的默认读取顺序为：

### 协议层（必读）

1. `workflows/software-project-governance/manifest.md`
2. `protocol/workflow-schema.md`
3. `protocol/plugin-contract.md`
4. `protocol/external-command-contract.md`

### 运行时本体层（必读 — 从 skills/ 加载）

5. `skills/software-project-governance/core/lifecycle.md`
6. `skills/software-project-governance/core/stage-gates.md`
7. `skills/software-project-governance/core/profiles.md`
8. `skills/software-project-governance/core/onboarding.md`
9. `skills/software-project-governance/references/interaction-boundary.md`

### 治理记录字段定义（在 skill 入口中内嵌）

`skills/software-project-governance/SKILL.md` 的 M3 段已内嵌 plan-tracker、evidence-log、decision-log、risk-log 的全部字段定义。不需要额外读取外部模板文件。

### 当前阶段子工作流（按 stage 参数加载）

10. `skills/software-project-governance/stages/<stage>/sub-workflow.md`

### 当前阶段 skill（按需加载）

11. `skills/software-project-governance/stages/<stage>/` 下的 skill 文件

### 项目实例（必读）

16. `.governance/plan-tracker.md`

## write-back targets

command 只允许回写以下统一事实源：

- `.governance/plan-tracker.md`
- `.governance/evidence-log.md`
- `.governance/decision-log.md`
- `.governance/risk-log.md`

明确禁止：

- 新增 agent 私有状态文件
- 新增平行计划文件
- 在 `adapters/` 或其他外部目录中维护第二套治理日志

## gate behavior

默认 gate 行为如下：

1. command 必须根据 `stage` 解析当前适用 Gate。
2. 如必需事实源缺失，不得声称任务完成。
3. 如缺少证据、风险或决策留痕，应先回写事实源，再允许进入下一阶段叙事。
4. 如 Gate 未通过，输出必须显式包含 `blocked` 状态与阻断原因。

## validation

默认校验命令：

```bash
python skills/software-project-governance/infra/verify_workflow.py
```

如 command 只是生成建议而未完成事实源回写，也不得跳过该校验口径。

## replacement boundary

当未来发生以下替换时：

- shared command -> MCP tool
- shared command -> headless runner
- 一个 agent -> 另一个 agent

必须保留：

- `protocol/`
- `skills/software-project-governance/`（运行时本体）
- `workflows/software-project-governance/`（设计时资产）
- `skills/software-project-governance/infra/verify_workflow.py`

可以移除或替换：

- agent 私有 command 封装
- 外部 runner 的宿主实现
- 各 agent 的触发别名或调用包装

## 最小返回样例

```json
{
  "command_id": "software-project-governance.run",
  "workflow_id": "software-project-governance",
  "entry_task": "MAINT-005",
  "stage": "maintenance",
  "read_order": [
    "workflows/software-project-governance/manifest.md",
    "protocol/workflow-schema.md",
    "protocol/plugin-contract.md",
    "protocol/external-command-contract.md"
  ],
  "write_back_targets": [
    ".governance/plan-tracker.md",
    ".governance/evidence-log.md",
    ".governance/decision-log.md",
    ".governance/risk-log.md"
  ],
  "gate_check": {
    "gate": "G8",
    "blocked": false
  },
  "validation": {
    "command": "python skills/software-project-governance/infra/verify_workflow.py"
  },
  "replacement_boundary": {
    "keep": [
      "protocol/",
      "skills/software-project-governance/",
      "workflows/software-project-governance/",
      "skills/software-project-governance/infra/verify_workflow.py"
    ],
    "replace": [
      "agent-specific command wrapper"
    ]
  }
}
```

## 与现有协议的关系

- `workflow-schema.md` 负责定义 workflow、stage、gate 的通用对象模型。
- `plugin-contract.md` 负责定义三层承载模型与集成回答的问题，包含 agent 准入标准、默认推荐判定标准和冲击场景。
- `external-command-contract.md` 负责把外部能力层里的 shared command 进一步收敛成可执行样例，包含字段边界和验证矩阵。
- `headless-runner-sample.md` 负责验证 shared command 契约的自动化运行态映射。
- `interaction-boundary.md` 负责定义用户交互边界，决定哪些活动自动执行、哪些需要用户参与。

五者关系是：上层统一模型 → 中层接入原则 → 下层最小 command 契约 → 运行态映射 → 交互边界约束。

## 当前不做

- 不在本文件中定义真实的 CLI 参数解析实现。
- 不绑定某个具体 agent 的 slash command 语法。
- 不在本文件中承诺远程服务、鉴权或 marketplace 分发。

## 字段边界（Required / Optional）

### Required 字段

以下字段在所有实现中必须存在，缺一不可：

1. `command_id`
2. `workflow_id`
3. `entry_task`
4. `stage`
5. `goal`
6. `read_order`
7. `write_back_targets`
8. `gate_check`（必须包含 `gate` 和 `blocked` 两个子字段）
9. `validation`（必须包含 `command` 子字段）
10. `replacement_boundary`（必须包含 `keep` 和 `replace` 两个子字段）

### Optional 字段

以下字段允许按 agent 能力选择提供，但不允许用 optional 字段替代 required 字段的语义：

- `agent_metadata`：允许记录 agent 名称和版本，但不影响 command 的执行语义。
- `execution_context`：允许记录执行环境信息（如 CI 平台、触发方式），但不作为 Gate 判断依据。

### 禁止字段

以下字段在任何实现中都不允许出现，防止 agent-specific wrapper 绕开统一 contract：

- `agent_private_state`：不允许 agent 维护私有状态文件或状态字段。
- `override_gate`：不允许 agent 在 Gate 未通过时自行覆盖 `blocked` 状态。
- `skip_validation`：不允许 agent 跳过 `validation` 命令的执行。
- `extended_write_back`：不允许 agent 扩展 `write_back_targets` 列表。

## 失败与阻断语义

### 失败返回

当 command 执行失败时，必须返回以下结构：

```json
{
  "command_id": "software-project-governance.run",
  "workflow_id": "software-project-governance",
  "entry_task": "<task-id>",
  "stage": "<stage>",
  "gate_check": {
    "gate": "<gate-id>",
    "blocked": true,
    "reason": "<阻塞原因>"
  },
  "status": "failed"
}
```

不允许：
- 返回空结构或自由文本错误消息
- 省略 `blocked` 和 `reason`
- 把 `status` 设为 `validated` 或 `planned`

### Blocked 返回

当 Gate 未通过但执行本身未失败时，必须返回：

```json
{
  "command_id": "software-project-governance.run",
  "workflow_id": "software-project-governance",
  "entry_task": "<task-id>",
  "stage": "<stage>",
  "gate_check": {
    "gate": "<gate-id>",
    "blocked": true,
    "reason": "<阻断原因>",
    "required_action": "<需要补齐的证据或动作>"
  },
  "status": "blocked"
}
```

### dry-run / apply 语义一致性

`dry-run` 和 `apply` 模式在以下方面必须保持一致：

1. `read_order` 和 `write_back_targets` 的内容和顺序必须完全相同。
2. `gate_check` 的判定逻辑必须完全相同。
3. `validation` 命令必须相同。
4. `replacement_boundary` 必须相同。

唯一允许的差异：
- `dry-run` 不执行事实源回写。
- `dry-run` 的 `status` 只能为 `planned` 或 `blocked`。
- `apply` 允许回写且 `status` 可以为 `validated`。

## Validation Matrix

以下矩阵定义了不同 agent 在接入 shared command 时必须满足的最低能力要求：

| 能力维度 | Claude | Codex | Gemini | 国内 agent CLI |
|---------|--------|-------|--------|---------------|
| 执行 `read_order` | 必须 | 必须 | 必须 | 必须 |
| 回写 `write_back_targets` | 必须 | 必须 | 必须 | 必须 |
| 遵守 `gate_check` 阻断 | 必须 | 必须 | 必须 | 必须 |
| 执行 `validation` 命令 | 必须 | 必须 | 条件 | 条件 |
| 结构化输出完整 contract | 必须 | 必须 | 条件 | 条件 |
| 不新增禁止字段 | 必须 | 必须 | 必须 | 必须 |

- "必须"：该 agent 不满足此项时，不得进入正式主线适配。
- "条件"：该 agent 可在受限模式下运行，但必须在方案中显式说明受限行为和降级路径。

## 下一步建议

1. 基于本契约补一个 headless runner 样例，验证结构化输出是否足够稳定。
2. 再评估是否把相同字段直接映射为 MCP tool schema。
3. 后续任一 agent 接入 shared command 时，不得跳过 `write_back targets` 和 `replacement boundary` 两类字段。
4. 后续任一 agent 的 command wrapper 必须通过 validation matrix 检查，不得引入禁止字段。
