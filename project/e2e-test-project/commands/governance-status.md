# governance-status — 项目治理状态展示

> **推荐使用 `/governance`**——自动检测项目状态并展示（Scenario F）。本命令保留为快捷方式。

展示当前项目的治理状态摘要。

## 输入参数

此命令不接受任何输入参数。

## 执行流程

### Step 1: 检查是否已初始化
- **IF** `.governance/plan-tracker.md` 不存在 → 返回错误 `STATUS-ERR-001`（未初始化）
- **ELSE** → 继续 Step 2

### Step 2: 运行确定性状态命令（FIX-270 秒级快路径）
- 运行 `python <plugin_home>/infra/verify_workflow.py status`（`<plugin_home>` 来自 resolve_entry.py，先 resolve 后 verify），**渲染其输出**，而不是重新手工读取治理记录。
- `status` 输出已包含：项目配置（项目名称、Profile、触发模式、操作权限模式 permission_mode、工作流版本、当前阶段）、Gate 状态跟踪表（G1~G11 状态/通过日期/关键证据）、项目概览表（总任务数、已完成、阻塞中、关键风险数、最近 Gate 结论）、任务统计（含 P0 待处理）、活跃风险（含 ≤3 天升级截止标记）、最近活动（最近 5 个已完成任务 + 最近 5 个决策）、插件版本新鲜度、建议下一步线索、Delivery Trust Snapshot。
- **默认不再要求 Agent 全量读 4 个治理文件**。仅当 (a) 用户展开详情，(b) `status` 输出字段缺失/解析失败，或 (c) 数据对不上时，才用 read 按需读取 `.governance/plan-tracker.md` / `risk-log.md` / `session-snapshot.md`；`.governance/evidence-log.md` 只在用户明确要求查看证据时读取。
- 若 `status` 不可运行（模块未定位/超时/异常）→ 降级为既有手工读取流程，并记录降级原因（不静默过场）。

### Step 3: 按 status 输出计算指标
- 完成率 = 已完成 / 总任务数 × 100（总任务数为 0 时显示 "N/A"）——直接用 status 输出统计
- 未完成 P0 任务数 = status 输出 `p0_pending`（状态非"已完成"且优先级=P0 的任务数）
- 活跃风险数 = status 输出 `risks` 条目数（risk-log 中状态非"已关闭"）
- Existing governance state detected = `.governance/plan-tracker.md` 存在且可解析；已有治理状态时 MUST NOT 提示重新初始化
- Carry-over = status 输出 Next step hints / Delivery Trust Snapshot Carry-over（当前活跃事项或 session snapshot 中仍未完成的任务数）
- Open risks = 活跃风险数量 + 风险 ID/日期摘要（status 输出 `risks`）
- Hooks = pre-commit、commit-msg、post-commit 的 installed/missing 状态（参考 resolve_entry.py `hooks_installed` 或既有检查）

### Step 3.5: 插件版本新鲜度检查（advisory——非权威版本源）
- 插件新鲜度检查为 **advisory（非权威）**——权威激活版本来自 `resolve_entry.py` 的 `active_version`（DEC-096）。`check-plugin-freshness` 只作为远端/本地差异提示，不作为版本判定依据。
- **先运行 `python <plugin_home>/infra/resolve_entry.py --json`** 拿到 `plugin_home`（`plugin_home` 来自 `resolve_entry.py`，取代 `$WORKFLOW_HOME` 路径考古）。`resolved_root_ok=false` 时 MUST STOP 并展示 diagnostic，不得呈现状态。
- **FIX-270 起**：`status` 命令输出已含 `Plugin Freshness`（active_version vs plan-tracker 记录版本，advisory）；Step 2 已覆盖，无需重复运行。
- **IF**（旧路径或 `status` 缺失时）运行 `check-plugin-freshness`，捕获输出
  - **IF** 状态为 OUTDATED → 在状态面板底部输出更新提醒（版本差距 + commits behind + 操作指引），并标注 `advisory——权威版本见 active_version`
  - **IF** 状态为 UP TO DATE → 在状态面板底部简短确认 ✅
- **IF** 无法定位 `<plugin_home>/infra/verify_workflow.py` → 不声称脚本不可用；输出 `plugin runtime not located` 并提示执行插件刷新
  - 提醒用户：`运行 /plugin update 或 /reload-plugins 获取最新版本`

### Step 3.6: Delivery Trust Snapshot（FEAT-036 双契约）
- 输出默认交互视图（≤8 字段）的 compact `Delivery Trust Snapshot`，作为 `/governance` Scenario F 的 first-run/status 可观察信号；与 `/governance` Scenario F 默认视图同一口径（契约正文见 `/governance` 命令的 Scenario F「默认交互视图合约」节，本文件为同步面）。
- **默认交互视图合约（≤8 字段，生成预算 ≤700 tok）**：

```
Delivery Trust Snapshot (compact)
Mode: {trigger_mode} x {permission_mode}; {Existing governance state detected | first-run}; hooks {installed | missing}
Stage/Gate: {current_stage}; {最近 Gate 结论 | Gate {n} pending}
Tasks: in-progress {n} / blocked {n} / P0 pending {n}
Risks: {open_risk_count} open; {最高升级项一行（overdue/≤3d 风险 ID+截止） | none}
Health: {check-governance 未跑 → 待检查（deferred——FEAT-034 口径，不得显示为通过）}; {已知 FAIL/证据缺失 → 一行摘要内联 | clear}
Next: {top 1~3 候选（含依赖理由）| 结构化空原因}
Decision: {需 AskUserQuestion 的事项 | none}
Full: 20-field CLI snapshot + 4-field pack doc-surface -> `python <plugin_home>/infra/verify_workflow.py status --json` (delivery_trust_snapshot) / `check-governance-pack-status`
```

- **FEAT-034 时序兼容**：ask 前的「最小状态行」= 本视图的一行压缩子集（Mode + Stage/Gate + Risks 计数 + carry-over）；ask 后深检视图 = 8 字段全量（Health 位由 `check-governance` 填充）。
- **异常不隐藏红线**：权限风险（hooks 缺失/permission_mode 非法）、已知 FAIL、证据缺失不得因瘦身不可见——Risks/Health/Mode 字段必须携带异常位。
- **完整机器契约 = 20 字段 CLI snapshot 契约 + 4 字段 pack doc-surface 契约，默认不生成**。CLI snapshot 字段集（20 字段，与 `status` 输出逐字一致）：Resume state、Carry-over、Open risks、Unfinished work、Source facts、Blocker state、Auto-continue、Interrupt boundary、Hooks、Goal、Stage、Gate/setup status、Flow-unit lanes、Risk、Evidence、Next action、Preset guidance、Question budget、Verification signal、No-overclaim boundary——权威载体 = 既有确定性 CLI 输出（不新建平行契约）：
  - `python <plugin_home>/infra/verify_workflow.py status`（文本面 Snapshot 段，20 字段全量）与 `status --json`（`delivery_trust_snapshot` 对象，20 键——机器消费入口）；
  - `python <plugin_home>/infra/verify_workflow.py first-run-demo --assert-snapshot`（demo/local-only 范围断言其中 19 字段（`FIRST_RUN_DEMO_REQUIRED_FIELDS`，不含 `Flow-unit lanes`）与 no-overclaim 标记——断言对象是 CLI 机器面，不随交互视图瘦身降级）。
- Pack doc-surface 契约（4 字段）：Pack summary、Default packs、Enabled packs、Pack boundary——载体 = 本文件与 `/governance` 命令文档的固定语义行（docs 面），由 `check-governance-pack-status` 专项校验守护，不在任何 CLI snapshot 输出中。
- Health 映射注脚：Health 位数据源 = `check-governance --summary-only`，不是 snapshot 字段——按 Full 指示行取 artifact 的消费者需另跑 `check-governance` 获取健康面。
- 用户显式请求（如"完整状态"）或高风险场景（发布/Gate 检查/版本 bump/故障诊断）时，从 `status` 输出**直接渲染**完整面板，不手工重建。
- 已有 `.governance/` 状态时，Mode 字段 MUST 写出 `Existing governance state detected`，并保留 carry-over active task count、open risk count、next action。
- Next/Decision 字段的未完成事项 MUST come from recorded facts only: `.governance/plan-tracker.md` active rows/version roadmap, `.governance/session-snapshot.md` carry-over or next priorities, `.governance/risk-log.md`, and current local context. Every detected item MUST have `Source facts`; if no facts exist, output `not found` and `do not invent` new work.
- Blocker 语义沿用：Blocker state MUST distinguish no blocker recorded, open risk guard, and blocked facts（默认视图折叠进 Decision 字段；完整面在 `Unfinished work`/`Source facts`/`Blocker state`/`Auto-continue`/`Interrupt boundary` 四字段）。`Auto-continue` MUST be `yes` only when unfinished work is fact-backed and no blocker/critical decision boundary is recorded. `Interrupt boundary` MUST state when AskUserQuestion is required.
- 已有 `.governance/` 状态时，输出 MUST NOT 暗示或建议重新初始化；重新初始化提示只允许出现在 `.governance/plan-tracker.md` 缺失的错误路径。
- First-run preset guidance（机器契约固定语义行）：`lite is the recommended first-run default`；`standard is for team delivery`；`strict is for regulated/high-risk work`——渲染完整面板时随 `status` 输出原样呈现。
- Pack 语义（机器契约固定语义行）：Pack summary = `Packs are capability modules; profiles are governance intensity presets.`；Default packs 至少列出 `governance-core`、`quality-gates`、`release-governance`、`agent-team`、`enterprise`；Enabled packs MUST 来自 profile/default pack summary 或明确显示 unknown/not configured；Pack boundary: pack membership/`pack enabled` 不是 task evidence、independent review、quality gates、release gates、official approval、marketplace approval、universal/full runtime support 或 1.0.0 production-ready proof。
- Question budget（机器契约固定语义行）：ask no more than 3 non-critical questions before snapshot; record deferred non-critical fields as assumptions——Snapshot 前 MUST NOT 提超过 3 个 non-critical questions；剩余 deferred non-critical fields MUST 记录为 assumptions。
- `Verification signal` MUST 是一个可运行或可观察的本地信号，例如 `python <plugin_home>/infra/verify_workflow.py status`（`plugin_home` 来自 `resolve_entry.py`）；如果只能观察插件加载状态，必须明确 `plugin_home` 未解析。
- `No-overclaim boundary`（机器契约固定语义行）MUST 明确说明该 snapshot 只是 demo/local-only 本地治理状态信号、不需要 external credentials，且不声明 official approval、marketplace approval、universal/full runtime support 或 1.0.0 production-ready。
- 本地 acceptance harness：运行 `python <plugin_home>/infra/verify_workflow.py first-run-demo --assert-snapshot` MUST 在 demo/local-only 范围断言 snapshot 字段，不需要 external credentials（`plugin_home` 来自 `resolve_entry.py`，resolve 优先于 verify_workflow）。
- Context acceptance harness：运行 `python <plugin_home>/infra/verify_workflow.py governance-context --fixture project/e2e-test-project --fail-on-issues` MUST pass and MUST keep `not found` as a valid no-facts result without inventing unfinished work.

### Step 4: 按输出格式模板输出状态面板

## 输出格式

### 必要字段
| 字段 | 类型 | 说明 | 示例 |
|-------|------|-------------|---------|
| project_name | 字符串 | 项目名称 | "项目管理工作流插件" |
| profile | 字符串 | 治理强度 | "standard" |
| trigger_mode | 字符串 | 触发模式 | "always-on" |
| permission_mode | 字符串 | 操作权限模式 | "maximum-autonomy" |
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
| delivery_trust_snapshot | 面板 | 默认交互视图 ≤8 字段：Mode / Stage and Gate / Tasks / Risks / Health / Next / Decision + Full 指示行（异常位必显）；完整契约 = 20 字段 CLI snapshot（Resume state/Carry-over/Open risks/Unfinished work/Source facts/Blocker state/Auto-continue/Interrupt boundary/Hooks/Goal/Stage/Gate/setup status/Flow-unit lanes/Risk/Evidence/Next action/Preset guidance/Question budget/Verification signal/No-overclaim boundary）经 `status --json` 的 `delivery_trust_snapshot` artifact 获取 + 4 字段 pack doc-surface 契约（Pack summary/Default packs/Enabled packs/Pack boundary，docs 面固定语义行，经 `check-governance-pack-status` 校验） | 见模板 |

### 输出模板

```
┌─────────────────────────────────────────────────────┐
│  {project_name} — 治理状态                          │
├─────────────────────────────────────────────────────┤
│  Profile: {profile}   触发模式: {trigger_mode}       │
│  操作权限模式: {permission_mode}                     │
│  当前阶段: {current_stage}                           │
├─────────────────────────────────────────────────────┤
│  任务: {completed}/{total} ({completion_rate})        │
│  阻塞: {blocked}   待处理 P0: {active_p0}            │
│  活跃风险: {active_risks}                             │
│  最近 Gate: {last_gate_conclusion}                   │
│  最近复盘: {last_review_date}                        │
├─────────────────────────────────────────────────────┤
│  Delivery Trust Snapshot (compact, ≤8 字段)          │
│  Mode: {trigger_mode} x {permission_mode}; {resume_state}; hooks {installed | missing} │
│  Stage/Gate: {current_stage}; {最近 Gate 结论 | Gate {n} pending} │
│  Tasks: in-progress {n} / blocked {n} / P0 pending {n} │
│  Risks: {open_risk_count} open; {最高升级项一行 | none} │
│  Health: {待检查（deferred）| FAIL/证据缺失一行摘要 | clear} │
│  Next: {top 1~3 候选（含依赖理由）| 结构化空原因}      │
│  Decision: {需 AskUserQuestion 的事项 | none}         │
│  Full: status --json delivery_trust_snapshot（20 字段 CLI snapshot + 4 字段 pack doc-surface 契约——显式请求/高风险场景时渲染） │
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
- [ ] 输出必须明确包含 `permission_mode` 或 `操作权限模式`，不得只依赖项目配置原始字段顺序偶然展示
- [ ] 输出必须明确包含 `Delivery Trust Snapshot`（默认交互视图 ≤8 字段：Mode / Stage and Gate / Tasks / Risks / Health / Next / Decision + Full 指示行）
- [ ] 异常不隐藏：已知 FAIL、证据缺失、风险升级线、hooks 缺失在默认视图的 Risks/Health/Mode 位可见（哪怕压缩为一行）；健康面未检查时显示「待检查（deferred）」而非通过
- [ ] 完整机器契约 = 20 字段 CLI snapshot 契约（Resume state、Carry-over、Open risks、Unfinished work、Source facts、Blocker state、Auto-continue、Interrupt boundary、Hooks、Goal、Stage、Gate/setup status、Flow-unit lanes、Risk、Evidence、Next action、Preset guidance、Question budget、Verification signal、No-overclaim boundary——恰 20 个字段名）+ 4 字段 pack doc-surface 契约（Pack summary、Default packs、Enabled packs、Pack boundary）默认不生成；显式请求/高风险场景时 CLI 20 字段从 `status --json` 的 `delivery_trust_snapshot` artifact 直接渲染，不手工重建
- [ ] Unfinished work 必须基于 Source facts；无事实时必须输出 `not found` 和 `do not invent`
- [ ] 运行 `python <plugin_home>/infra/verify_workflow.py governance-context --fixture project/e2e-test-project --fail-on-issues` 必须可通过（`plugin_home` 来自 `resolve_entry.py`）
- [ ] 已有 `.governance/` 项目不得提示重新初始化；必须给出 resume next action
- [ ] First-run preset guidance 必须明确 `lite` 是首次运行推荐默认，`standard` 用于 team delivery，`strict` 用于 regulated/high-risk work
- [ ] Pack summary 必须明确 `Packs are capability modules; profiles are governance intensity presets.`，并至少展示 `governance-core`、`quality-gates`、`release-governance`、`agent-team`、`enterprise`
- [ ] Pack boundary 必须明确 pack membership/`pack enabled` 不等于 task evidence、independent review、quality gates、release gates、official approval、marketplace approval、universal/full runtime support 或 1.0.0 production-ready
- [ ] Snapshot 前不得提出超过 3 个 non-critical questions；deferred non-critical fields 必须记录为 assumptions
- [ ] No-overclaim boundary 必须避免声明 official approval、marketplace approval、universal/full runtime support 或 1.0.0 production-ready
- [ ] completion_rate 为百分比字符串或 "N/A"
- [ ] gate_status_table 恰好包含 G1 至 G11
- [ ] 每个 Gate 状态均为 5 种合法值之一
- [ ] 所有数字字段包含实际数字（非描述文字或 "—"）
- [ ] 输出使用模板中所示的 Unicode 制表符
