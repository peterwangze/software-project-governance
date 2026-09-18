# /governance 快照格式规范（`session-snapshot.md` 字段契约）

> FEAT-038 拆分自路由层的「Snapshot 格式规范」节（逐字搬移，零语义丢失）。
> 本文件不在默认注入面——**触发条件**：会话收尾写 `.governance/session-snapshot.md`，或 Scenario D 恢复前校验 snapshot 字段时 Read。

`session-snapshot.md` 必须包含以下字段以确保 Scenario D 可无缝恢复：

`session-snapshot.md` 必须包含以下字段以确保 Scenario D 可无缝恢复：

```markdown
# 会话快照 — {{DATE}}

- **session_id**: {{YYYYMMDD-HHMMSS}}
- **session_date**: {{YYYY-MM-DD}}
- **agent**: {{AGENT_NAME_AND_VERSION}}

## 当前状态
- **current_stage**: {{STAGE_NUMBER_AND_NAME}}
- **current_gate**: {{GATE_ID}} (状态: {{STATUS}})
- **trigger_mode**: {{TRIGGER_MODE}}
- **permission_mode**: {{PERMISSION_MODE}}

## 遗留任务
| 任务 ID | 描述 | 完成百分比 | 阻塞原因 | 优先级 |
|---------|-------------|-----------|------------|----------|

## 待确认决策
| 决策 ID | 标题 | 上下文 | 截止日期 |
|-------------|-------|---------|----------|

## 活跃风险
| 风险 ID | 描述 | 升级截止日期 | 负责人 |
|---------|-------------|---------------------|-------|

## 本轮已完成
{{LIST_WITH_EVIDENCE_REFS}}

## 未完成 / 已延期
{{LIST_WITH_REASONS}}

## 下次会话优先级
{{ORDERED_LIST}}

> FIX-262/REQ-108：本节 MUST 由完成必推荐快照派生——至少引用一个快照行 ID（`RECO-{TASK_ID}`（`task-priority-analysis --evidence-task` 机器写入）或既有 `EVD-{N}` 快照行）。无引用 = 自由手写，Check 34 S2 WARN；引用不存在的 ID = 悬空，Check 34 S3 FAIL。
- **推荐快照引用**: {{RECO-_或_EVD-_快照行_ID}}

## 用户偏好设置
{{PERSISTED_PREFERENCES}}
```
