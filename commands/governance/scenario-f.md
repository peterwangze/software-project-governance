# Scenario F: 状态展示

> 本文件不在默认注入面——命中 `scenario_hint == "F"` 后按路由层契约 Read。
> 完整执行规程：原 `## Scenario F: 状态展示` 节逐字搬移（零语义丢失）。

## Scenario F: 状态展示

**检测条件**：一切正常——`.governance/` 存在、健康、版本最新、无 snapshot、无异常

**数据源（MUST，FIX-270 秒级快路径）**：状态展示 = 运行 `python <plugin_home>/infra/verify_workflow.py status`（`<plugin_home>` 来自 resolve_entry.py，先 resolve 后 verify）→ **渲染其输出**（文本或 `status --json`），而不是重新手工读取治理文件。

- **bootstrap 聚合快路径（FEAT-033，推荐入口）**：单次会话引导/路由需要 resolve + 状态 + 候选一次性数据时，MAY 运行 `python <plugin_home>/infra/verify_workflow.py governance-bootstrap --format json`（只读聚合：resolve envelope + 状态投影 + 候选 + migration 标志 + next_actions，≤8KB JSON 投影；`--budget-ms` 超时 fail-safe 返回 `deferred` 明示未完成范围）——一次调用替代"多次 verify 调用 + 多段读 plan-tracker"的串行链。`status` 仍是底层全量投影依赖（Delivery Trust Snapshot / Gate 全表等完整面以 `status` 输出为准）；`governance-bootstrap` 的 `health.state` 恒为 `deferred`（v1 未接线健康检查——健康面 MUST 另跑 `check-governance --summary-only`，不得把 deferred 当作已检查）。
- **默认不再要求全量读 4 个治理文件**（plan-tracker.md / evidence-log.md / risk-log.md / decision-log.md）——`status` 命令已用行级结构化解析输出 Scenario F 面板所需全部数据（项目配置 / Gate 状态 / 任务统计 / 活跃风险含 ≤3 天升级线标记 / 最近活动 / 插件版本新鲜度 / 建议下一步线索 / Delivery Trust Snapshot）。
- **按需展开（例外）**：仅当 (a) 用户展开 `<details>` 详情，(b) `status` 输出字段缺失/解析失败，或 (c) 数据对不上时，才用 read 工具按需读取对应治理文件。
- **Delivery Trust Snapshot 数据来源** = `status` 命令输出 + `governance-context` 既有输出（两者都是确定性 CLI 输出；Snapshot 字段合约见下方，不得以手工翻读证据文件替代）。
- **性能基线**：`status` 单次运行 <2s（宿主项目实测）——小时级 LLM 成本不再花在重读文档/记录上；若 `status` 输出显示 `Governance unavailable` 类缺失，按下方错误码处理。

**展示内容（FEAT-036 双契约——默认交互视图瘦身 + 完整机器 artifact，比 `governance-status` 更丰富）**：

Delivery Trust Snapshot 拆为两份契约，`/governance` 与 `/governance-status` 共用同一口径：

1. **默认交互视图（≤8 字段）**——每次状态展示强制生成的唯一 Snapshot 面板（合约见下），生成预算 ≤700 tok。
2. **完整机器契约（20 字段 CLI snapshot 契约 + 4 字段 pack doc-surface 契约）**——不随会话强制生成；CLI snapshot 载体 = 既有确定性 CLI 输出（`status` 文本面 / `status --json` 的 `delivery_trust_snapshot` 对象 / `first-run-demo --assert-snapshot` 本地断言），按需渲染或机器消费；4 个 pack 字段是 doc-surface 契约（两命令文档的固定语义行 + `check-governance-pack-status` 专项校验），不在任何 CLI snapshot 输出中。FEAT-036 不新建平行契约，也不扩展 `governance-bootstrap` schema——其 ≤8KB 数据面（resolve/project/gates/tasks/risks/candidates/health/next_actions）已覆盖默认视图消费，20 字段信任面以 `status` 输出为准。

- 默认视图数据源 = `governance-bootstrap` 聚合数据面 + `check-governance` 健康结果；agent 只做渲染与引导，不做重复数据挖掘
- Existing-project resume signal：已有 `.governance/` 状态时 Mode 字段 MUST 携带 `Existing governance state detected`，并保留 carry-over active task count、open risk count 和 next action；hook state 异常（installed/missing）必须在 Mode/Health 位可见
- Context-aware resume handoff：MUST run the same factual discovery contract as `python <plugin_home>/infra/verify_workflow.py governance-context --fixture project/e2e-test-project --fail-on-issues`（`<plugin_home>` 来自 resolve_entry.py，先 resolve 后 verify）。Next/Decision 字段的未完成事项 MUST be backed by `Source facts`; if no facts exist, output `not found` and `do not invent` new work.
- 展开语义：用户显式请求（如"完整状态"）或高风险场景（发布 / Gate 检查 / 版本 bump / 故障诊断）需要完整面时，从 `status` 输出**直接渲染**完整面板（20 字段 CLI snapshot + pack doc-surface 语义行，不手工重建）；`--level strict` 语义 = 完整面板 + Gate 全表按始终展开处理
- 其余面板内容沿用折叠规则：始终展开 = 默认 Snapshot 视图 + 项目配置摘要（名称、profile、trigger_mode、permission_mode、版本、阶段）+ 建议下一步；默认折叠（`<details>`，非关键信息）= Gate 状态表（G1-G11）→ `<details><summary>Gate 状态表</summary>...表格...</details>`；最近活动（最近 5 个已完成任务、最近 5 个决策）→ `<details><summary>最近活动</summary>...列表...</details>`；插件版本新鲜度 → `<details><summary>插件版本</summary>...版本信息...</details>`；完整 Snapshot 面板（20 字段 CLI + pack doc-surface 语义行；仅显式请求时渲染）
- **折叠红线（异常不隐藏）**：权限风险（hooks 缺失 / permission_mode 非法）、已知 FAIL、证据缺失不得因折叠或瘦身而不可见——默认视图的 Risks/Health 字段必须携带异常位（哪怕压缩为一行）

**输出格式规则**：

**数据即 status/bootstrap 输出**（FIX-270）：默认视图与折叠明细的字段全部来自 `governance-bootstrap` 数据面与 `status` 命令输出（`status --json` 供机器消费）；agent 只做渲染与引导，不做重复数据挖掘。

折叠原则：用户一眼看到项目健康摘要（默认 Snapshot 视图 + 配置 + 下一步），细节按需展开；完整面板（20 字段 CLI snapshot + pack doc-surface 语义行）是显式请求的按需面，不是默认生成面。

**Delivery Trust Snapshot 默认交互视图合约（≤8 字段）**：

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

- **FEAT-034 时序兼容**：ask 前的「最小状态行」= 本视图的一行压缩子集（Mode + Stage/Gate + Risks 计数 + carry-over）；ask 后的深检视图 = 本视图 8 字段全量（Health 位由 `check-governance` 结果填充；deferred → 「待检查」）
- **异常不隐藏红线**：Risks 字段必须含最高升级项（存在时）；Health 字段必须内联已知 FAIL/证据缺失摘要——两者不得以「无异常」外观掩盖事实
- **输出预算（DEC-205 口径：推演值非实测）**：8 字段 × 典型值长度静态推演上界 ≈260 tok（最坏含异常摘要），≤700 tok 契约预算（arch 建议 300-700）留 ≥2.5x 余量；基线对照 = AUDIT-154 §3.2 实测（改造前 24 字段强制生成，Snapshot 面 ≈0.8-1.0K tok/次）

**Delivery Trust Snapshot 完整机器契约（20 字段 CLI snapshot 契约 + 4 字段 pack doc-surface 契约——不随会话强制生成）**：

CLI snapshot 载体（20 字段，全为既有确定性 CLI 输出，`<plugin_home>` 来自 resolve_entry.py）：
- `python <plugin_home>/infra/verify_workflow.py status`——文本面 `┌─ Delivery Trust Snapshot ─┐` 段（20 字段全量）
- `python <plugin_home>/infra/verify_workflow.py status --json`——`delivery_trust_snapshot` 对象（20 键，机器消费入口）
- `python <plugin_home>/infra/verify_workflow.py first-run-demo --assert-snapshot`——demo/local-only 范围断言其中 19 字段（`FIRST_RUN_DEMO_REQUIRED_FIELDS`，不含 `Flow-unit lanes`）与 no-overclaim 标记

CLI snapshot 字段集（20 字段，与 `status` 输出逐字一致）：Resume state、Carry-over、Open risks、Unfinished work、Source facts、Blocker state、Auto-continue、Interrupt boundary、Hooks、Goal、Stage、Gate/setup status、Flow-unit lanes、Risk、Evidence、Next action、Preset guidance、Question budget、Verification signal、No-overclaim boundary。

Pack doc-surface 契约字段集（4 字段）：Pack summary、Default packs、Enabled packs、Pack boundary——载体 = 本文档与 `governance-status.md` 的固定语义行（docs 面），由 `check-governance-pack-status` 专项校验守护，不在任何 CLI snapshot 输出中。

Health 映射注脚：默认视图 Health 位的数据源 = `check-governance --summary-only`，不是 snapshot 字段——完整 CLI artifact 中无对应字段，按 Full 指示行取 artifact 的消费者需另跑 `check-governance` 获取健康面。

固定语义行（常量字段值——CLI snapshot 三行与 `status` 输出逐字一致，pack doc-surface 三行为 docs 契约常量、经 `check-governance-pack-status` token 校验；First-run preset guidance 与 Question budget 属机器契约面，不再挤占默认视图）：
- Preset guidance: lite is the recommended first-run default; standard is for team delivery; strict is for regulated/high-risk work
- Question budget: ask no more than 3 non-critical questions before snapshot; record deferred non-critical fields as assumptions（Snapshot 前 MUST NOT 提超过 3 个 non-critical questions）
- No-overclaim boundary: local/demo-only snapshot; no external credentials required; no official approval, marketplace approval, universal/full runtime support, or 1.0.0 production-ready claim
- Pack summary: Packs are capability modules; profiles are governance intensity presets.
- Default packs: lite -> `governance-core`; standard -> `governance-core`, `quality-gates`, `release-governance`, `agent-team`; strict -> `governance-core`, `quality-gates`, `release-governance`, `agent-team`, `enterprise`（Enabled packs MUST 从 profile/default pack summary 或 registry facts 得出，无法得出时显示 unknown/not configured）
- Pack boundary: pack membership and `pack enabled` are not task evidence, independent review, quality gates, release gates, official approval, marketplace approval, universal/full runtime support, or 1.0.0 production-ready proof

默认交互视图（8 字段）是 `/governance` 或 `/governance-status` first-run/status path 的最小可观察交付信号；它必须在用户不阅读 `plan-tracker.md`、`evidence-log.md`、`risk-log.md` 或完整 SKILL 文件的情况下可见，且完整 20 字段 CLI snapshot 契约可经 `status`/`status --json` 一步取回（两端可达，缺一不可）；4 字段 pack doc-surface 契约由上述固定语义行承载，经 `check-governance-pack-status` 校验。
本地 acceptance harness：运行 `python <plugin_home>/infra/verify_workflow.py first-run-demo --assert-snapshot` MUST 可在 demo/local-only 范围运行，不需要 external credentials，并断言 CLI snapshot 契约 20 字段中的 19 个 demo 断言字段（`FIRST_RUN_DEMO_REQUIRED_FIELDS`，不含 `Flow-unit lanes`）和 no-overclaim boundary——断言对象是 CLI 机器面，不随交互视图瘦身降级（`<plugin_home>` 来自 resolve_entry.py）。
Context acceptance harness：运行 `python <plugin_home>/infra/verify_workflow.py governance-context --fixture project/e2e-test-project --fail-on-issues` MUST pass，并且 no-facts fixture 必须明确输出 `not found`；不得从假设中发明 unfinished work。
已有 `.governance/` 项目的 Scenario F 是 resume happy path，不得提示重新初始化；只有 `.governance/plan-tracker.md` 缺失时才进入初始化/接入错误路径。

**输出模板**：参考 `commands/governance-status.md`，扩展含 permission_mode、版本新鲜度、最近活动，并应用上述折叠规则。

### 状态展示后的引导（MUST）

**时序（FEAT-034 首次交互前置）**：本引导 = 快路径（第二动作）后的首次用户交互——`governance-bootstrap`/`status` 渲染完成后**立即**执行；健康摘要（`check-governance --summary-only`）等深检后置为用户选择后按需执行，`health.state="deferred"` 期间面板健康位显示「待检查」而非通过。

展示完治理面板后，**MUST 通过 AskUserQuestion 引导用户进入下一步**——Scenario F 不是终点，是工作起点。

根据当前项目状态选择合适的问题：

**情况 A — 有遗留任务（carry-over）**：
```
接下来你想做什么？
(1) 继续 "{task_id}" — 恢复上次遗留任务
(2) 创建新任务
(3) 查看 {具体方面} 详情
```

**情况 B — 有 P0 待处理任务**：
```
接下来你想做什么？
(1) 处理 P0 任务 "{task_id}" — {description}
(2) 创建新任务
(3) 查看详细面板
```

**情况 C — 无遗留任务，项目活跃**：
```
接下来你想做什么？
(1) 创建新任务 — 描述你想做的事
(2) 查看 {Gate/风险/证据} 详情
```

**情况 D — 新项目（刚初始化完成）**：
```
项目已就绪！接下来想做什么？
(1) 定义第一个任务 — 描述项目目标或第一个功能
(2) 查看当前阶段子工作流指南
```

**关键原则**：用户运行 `/governance` 不是为了看面板，是为了推进项目。面板是信息，引导是行动。

**Web 入口原则**：用户手动 `/governance` 是进入 Web UI 的默认入口。`/governance` 应启动或复用本地 Web console，并给出 URL，便于后续用 Web UI 查看状态和交互；阶段性任务或 session 收尾时，可以在总结之后追加 `web-console --summary-link` 的只读结果，不额外启动服务。
