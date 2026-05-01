# Headless Runner Sample

本文件定义 `software-project-governance` workflow 在外部能力层中的最小 headless runner 样例，用于验证 `external-command-contract.md` 中定义的 shared command 语义，是否能够稳定映射到自动化、CI 与批处理调用场景。

## 目标

本样例解决的问题不是“实现一个真实 runner 程序”，而是：

1. 验证 `software-project-governance.run` 的最小契约能否被 headless 执行面直接消费。
2. 明确 headless runner 在自动化场景下应读取什么、输出什么、阻断什么。
3. 确保自动化执行仍然复用 workflow 本体层和统一事实源，而不是产生第二套机器状态。
4. 为后续 MCP tool schema 或 CI integration 提供更贴近运行态的样例基线。

## runner id

默认样例 runner id：`software-project-governance.headless`

该 runner 只是 `software-project-governance.run` 的一种宿主映射，不改变 command contract 的字段语义。

## 输入映射

headless runner 至少接受以下输入：

- `workflow_id`
- `entry_task`
- `stage`
- `goal`
- `mode`

其中：

- `workflow_id` 默认值仍为 `software-project-governance`
- `mode` 默认值为 `dry-run` 或 `apply`
- `dry-run` 只输出建议的读取顺序、Gate 检查与回写目标
- `apply` 表示允许进入事实源回写与验证闭环

## 输出映射

headless runner 至少输出以下结构：

1. `runner_id`
2. `command_id`
3. `read_order`
4. `write_back_targets`
5. `gate_check`
6. `validation`
7. `execution_mode`
8. `status`

`status` 仅允许以下值：

- `planned`
- `blocked`
- `validated`

## execution mode

### dry-run

用于：

- CI 预检查
- 计划预演
- Gate 阻断前的无副作用分析

要求：

- 不修改任何事实源文件
- 仍然输出完整 `read_order`、`write_back_targets` 和 `gate_check`
- `status` 只能为 `planned` 或 `blocked`

### apply

用于：

- 已确认进入事实源回写的自动化执行
- 命令批处理
- 后续 shared command 封装后的正式执行路径

要求：

- 只允许回写 `.governance/` 四类事实源
- 执行后必须运行 `python skills/software-project-governance/infra/verify_workflow.py`
- 只有校验通过后，`status` 才能为 `validated`

## read order

headless runner 继续复用以下顺序：

### 协议层（必读）

1. `workflows/software-project-governance/manifest.md`
2. `protocol/workflow-schema.md`
3. `protocol/plugin-contract.md`
4. `protocol/external-command-contract.md`
5. `protocol/headless-runner-sample.md`

### 运行时本体层（必读 — 从 skills/ 加载）

6. `skills/software-project-governance/core/lifecycle.md`
7. `skills/software-project-governance/core/stage-gates.md`
8. `skills/software-project-governance/core/profiles.md`
9. `skills/software-project-governance/core/onboarding.md`
10. `skills/software-project-governance/references/interaction-boundary.md`

### 治理记录字段定义（在 skill 入口中内嵌）

`skills/software-project-governance/SKILL.md` 的 M3 段已内嵌 plan-tracker、evidence-log、decision-log、risk-log 的全部字段定义。不需要额外读取外部模板文件。

### 当前阶段子工作流（按 stage 参数加载）

11. `skills/software-project-governance/stages/<stage>/sub-workflow.md`

### 项目实例（必读）

12. `.governance/plan-tracker.md`

## gate behavior

headless runner 的 Gate 规则必须比 shared command 更明确：

1. `dry-run` 模式下，如果发现 Gate 未通过，必须输出 `blocked`，且不得自动降级为建议通过。
2. `apply` 模式下，如果缺少证据、决策或风险留痕，不得继续写入“完成态”。
3. 如果 `validation` 未通过，必须把最终状态收敛为 `blocked`，而不是保留中间成功表象。

## validation

默认验证链路如下：

1. 生成结构化执行结果
2. 如 `mode=apply`，完成允许的事实源回写
3. 运行：

```bash
python skills/software-project-governance/infra/verify_workflow.py
```

4. 只有验证通过时，输出 `status=validated`

## write-back boundary

headless runner 与 shared command 一样，只允许回写：

- `.governance/plan-tracker.md`
- `.governance/evidence-log.md`
- `.governance/decision-log.md`
- `.governance/risk-log.md`

明确禁止：

- 生成 `runner-state.json`
- 生成独立的 automation progress 文件
- 为 CI 或某个 agent 新建私有 project log

## 最小返回样例

```json
{
  "runner_id": "software-project-governance.headless",
  "command_id": "software-project-governance.run",
  "workflow_id": "software-project-governance",
  "entry_task": "MAINT-006",
  "stage": "maintenance",
  "goal": "validate headless runner mapping",
  "execution_mode": "dry-run",
  "read_order": [
    "workflows/software-project-governance/manifest.md",
    "protocol/workflow-schema.md",
    "protocol/plugin-contract.md",
    "protocol/external-command-contract.md",
    "protocol/headless-runner-sample.md"
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
  "status": "planned"
}
```

## 与现有协议的关系

- `external-command-contract.md` 定义 shared command 的最小契约。
- `headless-runner-sample.md` 负责验证该契约如何映射到自动化执行面。
- 后续如进入 MCP，实现也必须继续复用相同字段，而不是绕开该 runner 样例重新定义另一套结构。

## 当前不做

- 不实现真实 Python runner 或 CLI entrypoint
- 不绑定 GitHub Actions、Jenkins 或某个 CI 平台的私有语法
- 不在本文件中定义调度、重试、并发策略

## 状态流转

headless runner 的 `status` 只允许以下流转路径：

```
planned → blocked
planned → validated（仅 apply 模式，且 validation 通过后）
blocked → planned（补齐缺失证据或动作后重新进入）
```

禁止的流转：

- `validated` → `planned` 或 `blocked`（已验证的状态不可回退）
- `planned` → `validated`（dry-run 模式下禁止）
- 跳过 `validation` 直接进入 `validated`

## 重试语义

当 runner 在 `apply` 模式下执行失败时：

1. 不得自动重试超过 1 次。
2. 重试前必须确认失败原因不是 Gate 阻断（Gate 阻断不通过重试解决）。
3. 重试后若仍然失败，`status` 必须收敛为 `blocked`，并附带失败快照。

## 失败快照

当 runner 执行失败或被阻断时，必须在输出中包含以下快照信息：

```json
{
  "snapshot": {
    "last_read_order_step": "<最后成功读取的步骤序号>",
    "last_write_back_target": "<最后成功回写的文件路径>",
    "gate_blocked_at": "<阻断发生的 Gate 编号>",
    "failure_reason": "<失败原因>",
    "required_action": "<解除阻断所需的最小动作>"
  }
}
```

快照的用途：

- 供后续人工或自动化恢复使用。
- 不作为第二事实源。治理记录仍以 `.governance/` 四类文件为准。

## CI 环境最小行为边界

当 headless runner 在 CI 环境中运行时，必须遵守以下额外约束：

1. **无交互假设**：不得假设有人工确认环节，所有阻断必须通过 `gate_check` 自动判定。
2. **幂等性**：同一 `entry_task` 和 `stage` 的 `dry-run` 执行必须产出相同结果。
3. **退出码**：`validated` 对应退出码 0；`blocked` 或 `failed` 对应非零退出码。
4. **不生成 CI 私有文件**：不得在工作目录中生成 `runner-state.json`、`ci-output.log` 等非 contract 定义的状态文件。

## Runner 只是宿主

本文件定义的 runner 只是 `software-project-governance.run` 的执行宿主，不构成第二事实源：

- runner 的输出快照仅供恢复和调试使用。
- 治理记录的唯一事实源仍然是 `.governance/` 四类文件。
- runner 不得把执行中间状态写入 `protocol/`、`workflows/` 或 `scripts/` 下的任何文件。

## 下一步建议

1. 若继续推进运行态验证，可把同一结构映射为 MCP tool input/output schema。
2. 如果未来补真实 runner，必须继续复用 `software-project-governance.run` 和本样例中的 `execution_mode` 语义。
3. 任何自动化接入都不得绕开 `write-back boundary` 和 `validation` 两个抓手。
4. 后续真实 runner 必须遵守状态流转、重试语义和 CI 环境最小行为边界。
