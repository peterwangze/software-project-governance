# Agent 通信协议

Coordinator 与角色 Agent 之间的输入/输出契约。

## 原则

1. **文件传递，非上下文传递**：Agent 之间不共享会话上下文——通过 `.governance/` 治理文件和项目文件传递信息
2. **Coordinator 是唯一用户界面**：角色 Agent 不与用户直接交互
3. **显式 I/O 契约**：每个 dispatch 声明输入文件和期望输出

## Dispatch 格式

Coordinator 使用 Agent 工具 spawn 子 Agent，prompt 从 `agents/<role>.md` 模板构建：

```
Agent(
  description: "{task_id}: {brief}",
  subagent_type: "general-purpose",
  prompt: "[agents/<role>.md 模板] + [具体任务]"
)
```

### 必填字段

| 字段 | 说明 |
|------|------|
| `Task` | task_id + 任务描述 |
| `Input` | 具体文件路径列表 |
| `Output` | 期望产出和写回路径 |
| `Gate` | 验收标准——可自动判定的检查项 |
| `Dependencies` | 前置任务 ID 列表（无则标 `—`） |
| `ADR References` | 相关架构决策（如适用） |

## 角色 Agent I/O 契约

### Developer

**Input**:
```
Task: {task_id} — {description}
Input Files: {具体源文件路径}
Acceptance Criteria: {验收标准}
ADR References: {架构 ADR 引用}
Dependencies: {前置 task ID}
```

**Output**:
```
- Modified files (通过 lint/test/coverage/security)
- Commit hash (含 task ID 前缀)
- Self-check results: lint/test/coverage/security all green
```

**Escalation**: 3 次失败 → 停止，质疑方案，升级给 Coordinator

### Reviewer

**Input**:
```
Review Target: {task_id} — {developer}
Files Changed: {文件列表}
Diff: {git diff 输出或文件路径}
ADR References: {相关架构决策}
```

**Output**:
```
Conclusion: APPROVED | NEEDS_CHANGE | BLOCKED
Findings (if any):
  - File:Line | Severity: BLOCKING|WARNING|SUGGESTION
  - Description + Fix suggestion
```

**Escalation**: BLOCKED → 升级给 Coordinator，附带影响评估 + 建议方向

### Architect

**Input**:
```
Task: {task_id} — {description}
Requirements: {需求文档路径}
Constraints: {技术约束}
Existing ADRs: {已有 ADR}
```

**Output**:
```
- Architecture design doc or ADR
- Module decomposition + interface definitions
- Non-functional requirements mapping
- Technical review conclusion
- Decision record (→ .governance/decision-log.md)
```

**Escalation**: Bar Raiser 否决 → Gate 阻塞，必须解除否决条件

## 错误处理

| 场景 | 处理 |
|------|------|
| Agent 产出不满足 Gate | Coordinator 退回给 Agent 修复，附带具体差距 |
| Agent 需要澄清 | Agent 向 Coordinator 提问（不直接问用户），Coordinator 向用户确认后回答 |
| Agent 产出有跨 Agent 矛盾 | Coordinator 验证一致性——发现矛盾则回退给两个 Agent 协调 |
| Agent 丢失/超时 | Coordinator 重新 dispatch，附带前一次的状态 |

## 治理写回

所有 Agent 的完工证据写入 `.governance/evidence-log.md`，格式：
```
| EVD-{N} | {TASK_ID} | {阶段} | {证据类型} | {摘要} | {文件位置} | {ROLE_AGENT} | {日期} | {GATE} | {备注} |
```
