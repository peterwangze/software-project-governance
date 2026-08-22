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

### Step 3.6: Delivery Trust Snapshot
- 输出一个 compact `Delivery Trust Snapshot`，作为 `/governance` Scenario F 的 first-run/status 可观察信号。
- **FIX-270 起**：Snapshot 数据来源 = `status` 命令输出（`Delivery Trust Snapshot` 段，含 Resume state/Carry-over/Open risks/Hooks/Goal/Stage/Gate/setup status/Risk/Next action/Verification signal/No-overclaim boundary）+ `governance-context` 既有输出（`Unfinished work`/`Source facts`/`Blocker state`/`Auto-continue`/`Interrupt boundary`）。不得以手工通读 evidence-log 替代。
- Snapshot MUST 包含：Resume state、Carry-over、Open risks、Unfinished work、Source facts、Blocker state、Auto-continue、Interrupt boundary、Hooks、Goal、Stage、Gate/setup status、Risk、Evidence、Next action、Pack summary、Default packs、Enabled packs、Pack boundary、Verification signal、No-overclaim boundary。
- 已有 `.governance/` 状态时，`Resume state` MUST 明确写出 `Existing governance state detected`，并展示 carry-over active task count、open risk count/details、hook state 和 next action。
- `Unfinished work` MUST come from recorded facts only: `.governance/plan-tracker.md` active rows/version roadmap, `.governance/session-snapshot.md` carry-over or next priorities, `.governance/risk-log.md`, and current local context. Every detected item MUST have `Source facts`; if no facts exist, output `not found` and `do not invent` new work.
- `Blocker state` MUST distinguish no blocker recorded, open risk guard, and blocked facts. `Auto-continue` MUST be `yes` only when unfinished work is fact-backed and no blocker/critical decision boundary is recorded. `Interrupt boundary` MUST state when AskUserQuestion is required.
- 已有 `.governance/` 状态时，输出 MUST NOT 暗示或建议重新初始化；重新初始化提示只允许出现在 `.governance/plan-tracker.md` 缺失的错误路径。
- First-run preset guidance MUST 展示：`lite is the recommended first-run default`；`standard is for team delivery`；`strict is for regulated/high-risk work`。
- Pack summary MUST 展示：`Packs are capability modules; profiles are governance intensity presets.`；Default packs MUST 至少列出 `governance-core`、`quality-gates`、`release-governance`、`agent-team`、`enterprise`；Enabled packs MUST 来自 profile/default pack summary 或明确显示 unknown/not configured；Pack boundary MUST 说明 pack membership/`pack enabled` 不是 task evidence、independent review、quality gates、release gates、official approval、marketplace approval、universal/full runtime support 或 1.0.0 production-ready proof。
- Snapshot 前 MUST NOT 提超过 3 个 non-critical questions；剩余 deferred non-critical fields MUST 记录为 assumptions。
- `Verification signal` MUST 是一个可运行或可观察的本地信号，例如 `python <plugin_home>/infra/verify_workflow.py status`（`plugin_home` 来自 `resolve_entry.py`）；如果只能观察插件加载状态，必须明确 `plugin_home` 未解析。
- `No-overclaim boundary` MUST 明确说明该 snapshot 只是 demo/local-only 本地治理状态信号、不需要 external credentials，且不声明 official approval、marketplace approval、universal/full runtime support 或 1.0.0 production-ready。
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
| delivery_trust_snapshot | 面板 | Resume state/Carry-over/Open risks/Unfinished work/Source facts/Blocker state/Auto-continue/Interrupt boundary/Hooks/Goal/Stage/Gate/setup status/Risk/Evidence/Next action/Preset guidance/Question budget/Pack summary/Default packs/Enabled packs/Pack boundary/Verification signal/No-overclaim boundary | 见模板 |

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
│  Delivery Trust Snapshot                             │
│  Resume state: Existing governance state detected    │
│  Carry-over: {carry_over_count} active task(s)        │
│  Open risks: {open_risk_count} open risk(s); {risk_details} │
│  Unfinished work: {detected_item_or_not_found}        │
│  Source facts: {fact_source_paths_and_rows}           │
│  Blocker state: {blocker_state}                       │
│  Auto-continue: {yes_or_no}                           │
│  Interrupt boundary: {ask_user_question_boundary}     │
│  Hooks: {hook_state}                                 │
│  Goal: {project_goal}                                │
│  Stage: {current_stage}                              │
│  Gate/setup status: {gate_or_setup_status}           │
│  Risk: {risk_status}                                 │
│  Evidence: {evidence_status}                         │
│  Next action: {next_action}                          │
│  Preset guidance: lite is the recommended first-run default; standard is for team delivery; strict is for regulated/high-risk work │
│  Question budget: no more than 3 non-critical questions before snapshot; deferred non-critical fields become assumptions │
│  Pack summary: Packs are capability modules; profiles are governance intensity presets. │
│  Default packs: lite -> `governance-core`; standard -> `governance-core`, `quality-gates`, `release-governance`, `agent-team`; strict -> `governance-core`, `quality-gates`, `release-governance`, `agent-team`, `enterprise` │
│  Enabled packs: {enabled_pack_summary_or_unknown}       │
│  Pack boundary: pack membership and `pack enabled` are not task evidence, independent review, quality gates, release gates, official approval, marketplace approval, universal/full runtime support, or 1.0.0 production-ready proof │
│  Verification signal: {verification_signal}          │
│  No-overclaim boundary: {no_overclaim_boundary}      │
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
- [ ] 输出必须明确包含 `Delivery Trust Snapshot`
- [ ] Delivery Trust Snapshot 必须包含 Resume state、Existing governance state detected、Carry-over、Open risks、Unfinished work、Source facts、Blocker state、Auto-continue、Interrupt boundary、Hooks、Goal、Stage、Gate/setup status、Risk、Evidence、Next action、Preset guidance、Question budget、Pack summary、Default packs、Enabled packs、Pack boundary、Verification signal、No-overclaim boundary
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
