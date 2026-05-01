# governance-status — 项目治理状态展示

> **推荐使用 `/governance`**——自动检测项目状态并展示（Scenario F）。本命令保留为快捷方式。

展示当前项目的治理状态摘要。

## 输入参数

此命令不接受任何输入参数。

## 执行流程

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

### Step 3.5: 插件版本新鲜度检查（用户视角——"我的工作流是最新的吗？"）
- **IF** 项目根目录存在 `skills/software-project-governance/infra/verify_workflow.py` → 运行 `check-plugin-freshness`，捕获输出
  - **IF** 状态为 OUTDATED → 在状态面板底部输出更新提醒（版本差距 + commits behind + 操作指引）
  - **IF** 状态为 UP TO DATE → 在状态面板底部简短确认 ✅
- **IF** 不存在 `skills/software-project-governance/infra/verify_workflow.py` → 跳过（外部项目通过插件市场安装，无法直接运行脚本）
  - 提醒用户：`运行 /plugin update 或 /reload-plugins 获取最新版本`

### Step 4: 按输出格式模板输出状态面板

## 输出格式

### 必要字段
| 字段 | 类型 | 说明 | 示例 |
|-------|------|-------------|---------|
| project_name | 字符串 | 项目名称 | "项目管理工作流插件" |
| profile | 字符串 | 治理强度 | "standard" |
| trigger_mode | 字符串 | 触发模式 | "always-on" |
| current_stage | 字符串 | 当前阶段中文名 | "维护与演进" |
| total_tasks | 数字 | 总任务数 | 74 |
| completed_tasks | 数字 | 已完成任务数 | 54 |
| completion_rate | 字符串 | 完成率百分比 | "73%" |
| blocked_tasks | 数字 | 阻塞中任务数 | 0 |
| active_p0_tasks | 数字 | 未完成的 P0 任务数 | 3 |
| active_risks | 数字 | 活跃风险数 | 3 |
| last_gate_conclusion | 字符串 | 最近 Gate 结论 | "G11 通过" |
| last_review_date | 字符串 | 最近复盘日期 | "2026-04-25" |
| gate_status_table | 表格 | G1~G11 状态表 | 见模板 |

### 输出模板

```
┌─────────────────────────────────────────────────────┐
│  {project_name} — 治理状态                          │
├─────────────────────────────────────────────────────┤
│  Profile: {profile}   触发模式: {trigger_mode}       │
│  当前阶段: {current_stage}                           │
├─────────────────────────────────────────────────────┤
│  任务: {completed}/{total} ({completion_rate})        │
│  阻塞: {blocked}   待处理 P0: {active_p0}            │
│  活跃风险: {active_risks}                             │
│  最近 Gate: {last_gate_conclusion}                   │
│  最近复盘: {last_review_date}                        │
├─────────────────────────────────────────────────────┤
│  Gate   │ 状态                  │ 日期               │
│  G1     │ {status}              │ {date}             │
│  G2     │ {status}              │ {date}             │
│  ...                                                  │
│  G11    │ {status}              │ {date}             │
└─────────────────────────────────────────────────────┘
```

Gate 状态列的合法值：
- `passed` — 已通过
- `passed-on-entry` — 接入时标记通过
- `passed-with-conditions` — 有条件通过（需注明条件）
- `pending` — 待检查
- `blocked` — 阻塞

## 错误码

| 代码 | 条件 | 用户消息 | Agent 动作 |
|------|-----------|-------------|-------------|
| STATUS-ERR-001 | `.governance/plan-tracker.md` 不存在 | "项目尚未初始化。运行 `/governance-init` 为此项目设置治理跟踪。" | 停止执行，不做任何文件修改 |

## 自校验

执行后，agent MUST 验证：
- [ ] 所有必要字段均出现在输出中
- [ ] completion_rate 为百分比字符串或 "N/A"
- [ ] gate_status_table 恰好包含 G1 至 G11
- [ ] 每个 Gate 状态均为 5 种合法值之一
- [ ] 所有数字字段包含实际数字（非描述文字或 "—"）
- [ ] 输出使用模板中所示的 Unicode 制表符
