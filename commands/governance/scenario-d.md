# Scenario D: 会话恢复

> 本文件不在默认注入面——命中 `scenario_hint == "D"` 后按路由层契约 Read。
> 完整执行规程：原 `## Scenario D: 会话恢复` 节逐字搬移（零语义丢失）。

## Scenario D: 会话恢复

**检测条件**：`session-snapshot.md` 存在 AND 日期在 24h 内

**数据源补充（FEAT-033 bootstrap 聚合快路径；FEAT-034 时序重排）**：恢复面板所需的当前状态交叉验证数据（任务统计 / 风险 / 候选）MAY 优先取自单次 `python <plugin_home>/infra/verify_workflow.py governance-bootstrap --format json`（只读聚合，≤8KB），替代多次 verify 调用 + 逐段读 plan-tracker；snapshot 字段解析与 D1-D3 流程不变。**首次交互前置（FEAT-034）**：快路径数据就绪后 D3 恢复面板 + AskUserQuestion **立即**执行——D2 交叉验证与其它深检后置为用户选择后按需执行（用户选择"继续上次"并进入实际修改前 MUST 补齐 D2 交叉验证）；`health.state="deferred"` 期间恢复面板健康位显示「待检查」而非通过。

**新鲜度规则**：
| 时间 | 处理 |
|------|------|
| ≤24h | 活跃恢复——自动展示恢复面板，直接提供"继续上次"选项 |
| 24h~7d | 展示恢复面板 + 标记"⚠️ 快照已 {N} 小时——项目状态可能已有变化"，**仍提供"继续上次"选项**（交叉验证 plan-tracker 后再执行），同时提供"重新开始"选项 |
| >7d | 归档——展示快照摘要供参考（不提供恢复），自动转 Scenario F |

**流程**：

### Step D1: 加载并验证 snapshot

解析 `session-snapshot.md` 所有字段。缺失必要字段（session_date, carry_over_tasks）→ 降级为 Scenario F。

### Step D2: 与 plan-tracker 交叉验证

| 检查 | 方法 | 不一致时 |
|------|------|---------|
| 任务状态 | snapshot carry-over task ID → plan-tracker 中查找 | plan-tracker 中已标记"已完成" → 从 carry-over 移除 |
| 决策 | snapshot pending decision ID → decision-log 查找 | decision-log 已有 → 标记为已解决 |
| 风险 escalation | snapshot active risk → 比较 escalation deadline vs 今天 | deadline 已过 → 标记为"需立即升级" |
| Gate 状态 | snapshot current_gate → plan-tracker Gate 表 | 已通过 → 更新状态 |

### Step D3: 输出恢复面板

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
欢迎回来。上次会话: {session_date} ({agent})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

活跃遗留任务:
  🔄 {task_id} — {description} ({complete_pct}%)
  🔄 ...

待确认决策:
  ⏳ {decision_id} — {title}

需要关注的风险:
  ⚠️ {risk_id} — {description} (升级: {deadline}, 剩余 {days_left}天)

推荐下一步: {next_priority}

(1) 继续上次——恢复遗留任务
(2) 先审查快照——展示完整 session-snapshot
(3) 重新开始——转 Scenario F 状态展示
```

### Step D4: 按用户选择执行

- (1) 继续: 设置遗留任务为当前活跃任务，恢复 trigger_mode/permission_mode
- (2) 审查: 展示完整 snapshot，然后询问是否继续
- (3) 重新开始: 转 Scenario F
