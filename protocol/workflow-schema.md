# Workflow Schema

本文件定义本仓库中 workflow plugin/skill 的通用结构，用于作为 Claude、Codex、Gemini 及其他 agent CLI 的公共协议层。

## 目标

- 将大型软件公司的项目管理经验固化为统一的流程模型。
- 将流程模型进一步固化为可被不同 agent 消费的 workflow/plugin/skill 承载格式。
- 保证流程、状态、证据、风险、决策在不同 agent 之间共享同一事实源。

## 通用对象模型

### 1. Workflow

一个 workflow 表示一套可被 agent 执行或辅助执行的项目治理流程。

建议字段：

- `id`：workflow 唯一标识
- `name`：workflow 名称
- `version`：版本号
- `goal`：workflow 目标
- `supported_agents`：支持的 agent 列表
- `stages`：阶段列表
- `artifacts`：使用到的模板、规则、样例、日志
- `adapters`：已适配的 agent 入口
- `validation`：校验方式

### 2. Stage

一个 stage 表示流程中的阶段节点。

建议字段：

- `id`：阶段 ID
- `name`：阶段名称
- `purpose`：阶段目标
- `inputs`：输入
- `outputs`：输出
- `owner_role`：责任角色
- `gate`：关联 Gate
- `required_evidence`：必需证据

### 3. Gate

一个 gate 表示阶段切换门禁。

建议字段：

- `id`：Gate 编号
- `applies_to`：适用阶段转换
- `required_artifacts`：必审材料
- `checks`：检查项
- `pass_criteria`：通过标准
- `failure_action`：未通过时的阻断动作

### 4. Tracking Record

用于记录计划跟踪事实。

建议字段：

- `task_id`
- `stage`
- `goal`
- `input`
- `output`
- `owner`
- `status`
- `priority`
- `gate`
- `acceptance_criteria`
- `evidence`
- `risk_deviation`
- `correction_action`

### 5. Evidence / Decision / Risk

这三类对象作为过程可信的核心支撑对象。

- `Evidence`：用于证明事项完成或 Gate 通过
- `Decision`：用于解释关键取舍
- `Risk`：用于记录偏差、阻塞与缓解动作

## 设计原则

- 单一事实源：不同 agent 不得维护多份主计划。
- 规则先行：任何 agent 适配都必须基于统一规则层。
- 数据可信：已完成事项必须能追溯到证据、决策或风险记录。
- 适配解耦：协议层不得绑定单一 agent 私有概念。
- 可演进：允许不同团队在不破坏协议层的前提下增量扩展。
