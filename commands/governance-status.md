# governance-status — 项目治理状态展示

展示当前项目的治理状态摘要。

## Input Parameters

此命令不接受任何输入参数。

## Execution Flow

### Step 1: 检查是否已初始化
- **IF** `.governance/plan-tracker.md` 不存在 → 返回错误 `STATUS-ERR-001`（未初始化）
- **ELSE** → 继续 Step 2

### Step 2: 读取治理记录
- 读取 `.governance/plan-tracker.md`，提取：
  - 项目配置（项目名称、Profile、触发模式、当前阶段）
  - Gate 状态跟踪表（G1~G11 各行的状态和通过日期）
  - 项目概览表（总任务数、已完成、阻塞中、关键风险数、最近 Gate 结论）
- 读取 `.governance/risk-log.md`，统计状态为"活跃"的风险

### Step 3: 计算指标
- 完成率 = 已完成 / 总任务数 × 100（总任务数为 0 时显示 "N/A"）
- 未完成 P0 任务数 = 状态非"已完成"且优先级=P0 的任务数
- 活跃风险数 = risk-log 中状态="活跃"的条目数

### Step 4: 按 Output Format 模板输出状态面板

## Output Format

### Required Fields
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| project_name | string | 项目名称 | "项目管理工作流插件" |
| profile | string | 治理强度 | "standard" |
| trigger_mode | string | 触发模式 | "always-on" |
| current_stage | string | 当前阶段中文名 | "维护与演进" |
| total_tasks | number | 总任务数 | 74 |
| completed_tasks | number | 已完成任务数 | 54 |
| completion_rate | string | 完成率百分比 | "73%" |
| blocked_tasks | number | 阻塞中任务数 | 0 |
| active_p0_tasks | number | 未完成的 P0 任务数 | 3 |
| active_risks | number | 活跃风险数 | 3 |
| last_gate_conclusion | string | 最近 Gate 结论 | "G11 通过" |
| last_review_date | string | 最近复盘日期 | "2026-04-25" |
| gate_status_table | table | G1~G11 状态表 | 见模板 |

### Output Template

```
┌─────────────────────────────────────────────────────┐
│  {project_name} — Governance Status                │
├─────────────────────────────────────────────────────┤
│  Profile: {profile}   Trigger: {trigger_mode}       │
│  Stage: {current_stage}                             │
├─────────────────────────────────────────────────────┤
│  Tasks: {completed}/{total} ({completion_rate})      │
│  Blocked: {blocked}   P0 pending: {active_p0}       │
│  Active risks: {active_risks}                        │
│  Last Gate: {last_gate_conclusion}                   │
│  Last Review: {last_review_date}                     │
├─────────────────────────────────────────────────────┤
│  Gate   │ Status               │ Date               │
│  G1     │ {status}             │ {date}             │
│  G2     │ {status}             │ {date}             │
│  ...                                              │
│  G11    │ {status}             │ {date}             │
└─────────────────────────────────────────────────────┘
```

Gate 状态列的合法值：
- `passed` — 已通过
- `passed-on-entry` — 接入时标记通过
- `passed-with-conditions` — 有条件通过（需注明条件）
- `pending` — 待检查
- `blocked` — 阻塞

## Error Codes

| Code | Condition | User Message | Agent Action |
|------|-----------|-------------|-------------|
| STATUS-ERR-001 | `.governance/plan-tracker.md` 不存在 | "Project has not been initialized yet. Run `/governance-init` to set up governance tracking for this project." | 停止执行，不做任何文件修改 |

## Self-Validation

After execution, agent MUST verify:
- [ ] All Required Fields are present in output
- [ ] completion_rate is a percentage string or "N/A"
- [ ] gate_status_table contains exactly G1 through G11
- [ ] Every gate status is one of the 5 legal values
- [ ] All numeric fields contain actual numbers (not descriptions or "—")
- [ ] Output uses Unicode box-drawing characters as shown in template
