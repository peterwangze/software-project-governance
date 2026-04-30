# Task-Gate 模型

Agent Team 架构的治理模型——每个任务有独立 Gate，任务间通过显式依赖图管理并行。

## 与 Phase-Gate 的区别

| 维度 | Phase-Gate（旧） | Task-Gate（新） |
|------|-----------------|-----------------|
| Gate 粒度 | 阶段级——整个阶段通过才进入下一阶段 | 任务级——每个任务有独立 Gate |
| 并行 | 仅相邻阶段可重叠 | 无依赖任务可完全并行 |
| 阻塞范围 | 阻塞整个阶段 | 仅阻塞有依赖关系的下游任务 |
| 数据结构 | plan-tracker 单 `当前阶段` 字段 | plan-tracker `workflow_model: agent-team` + 任务依赖图 |
| 审查者 | agent 自审 | Coordinator 跨 Agent 验证 |

## plan-tracker 数据结构变更

### 新增项目配置字段

```markdown
- **workflow_model**: agent-team（phase-gate / agent-team）
```

### 任务依赖图格式

在任务表中新增 `依赖` 列：

| ID | ... | 状态 | 依赖 | Gate 状态 | ... |
|----|-----|------|------|----------|-----|
| AUDIT-053 | ... | 进行中 | — | pending | ... |
| AUDIT-054 | ... | 未开始 | AUDIT-053 | pending | ... |
| AUDIT-055 | ... | 未开始 | AUDIT-054 | pending | ... |

### Task-Gate 状态

每个任务有独立 Gate 状态：
- **pending**: 任务未完成，Gate 未检查
- **passed**: 任务完成，Gate 检查通过
- **blocked**: Gate 检查未通过，阻塞下游依赖任务
- **skipped**: 任务被跳过（显式记录原因）

## 依赖管理规则

1. **显式声明**：每个任务的依赖列列出所有前置任务 ID
2. **传递阻塞**：前置任务 Gate blocked → 当前任务可执行但产出可能无效（警告）
3. **并行安全**：无依赖关系的任务可由不同 Agent 并行执行
4. **循环检测**：Coordinator 在分解任务时检查循环依赖

## Gate 检查项（任务级）

每个任务完成时的 Task-Gate 检查：
1. **Evidence 完整**：evidence-log 有对应条目
2. **审查通过**：Reviewer 返回 APPROVED（如适用）
3. **门禁通过**：lint/test/coverage/security 全部 green（开发任务）
4. **一致性**：产出与依赖任务的产出不矛盾（Coordinator 验证）
5. **Commit traceability**：commit message 含 task ID

## 兼容性

- `workflow_model: phase-gate` → 使用旧 11 阶段 Phase-Gate 模型（向后兼容）
- `workflow_model: agent-team` → 使用 Task-Gate 模型（0.9.0+）
- 新项目默认 `agent-team`，旧项目保持原设置
