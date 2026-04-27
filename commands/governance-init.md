# governance-init — 项目治理初始化

初始化当前项目的治理文件。安装插件后执行的第一条命令。

## Input Parameters

| Parameter | Type | Required | Default | Valid Values | Description |
|-----------|------|----------|---------|-------------|-------------|
| project_name | string | yes | — | 非空字符串，≤100 字符 | 项目名称 |
| project_goal | string | yes | — | 非空字符串，≤500 字符 | 项目目标和一句话描述 |
| project_type | enum | yes | — | new / existing | 新项目还是已在进行的项目 |
| current_stage | string | conditional | — | initiation / research / selection / infrastructure / architecture / development / testing / ci-cd / release / operations / maintenance | 当前所在阶段。project_type=existing 时为必需；project_type=new 时固定为 initiation |
| profile | enum | no | standard | lightweight / standard / strict | 治理强度 Profile |
| trigger_mode | enum | no | always-on | always-on / on-demand / silent-track | 默认触发模式 |

## Execution Flow

### Step 1: 避免重复初始化
- **IF** `.governance/` 目录已存在 AND 包含 plan-tracker.md → 返回错误 `INIT-ERR-001`（重复初始化）
- **ELSE** → 继续 Step 2

### Step 2: 校验 project_type
- **IF** `project_type` = `existing` AND `current_stage` 未提供 → 返回错误 `INIT-ERR-003`（缺少 current_stage）
- **IF** `project_type` = `new` → 设置 `current_stage` = `initiation`
- **ELSE** → 继续 Step 3

### Step 3: 校验 profile
- **IF** `profile` 不在 [lightweight, standard, strict] 中 → 返回错误 `INIT-ERR-002`（无效 profile）
- **ELSE** → 继续 Step 4

### Step 4: 创建 .governance/ 目录
- 检查 `.governance/` 目录是否存在
- **IF** 不存在 → 创建 `.governance/` 目录
- **ELSE** → 继续（目录已存在但无 plan-tracker.md，视为部分损坏，覆盖创建）

### Step 5: 创建 4 个治理记录文件
创建以下文件（字段定义以 SKILL.md M3 节为准）：

#### plan-tracker.md

**Profile 差异化生成规则**——profile 选择产生**不同结构**的 plan-tracker：

##### 通用配置块（所有 profile 均创建）
- 项目配置块：项目名称、Profile、触发模式、当前阶段
- 项目概览表：项目名称、当前阶段、总任务数(0)、已完成(0)、阻塞中(0)、关键风险数(0)、最近 Gate 结论、最近复盘日期

##### Gate 状态跟踪表（按 profile 生成不同 Gate 数量）

**lightweight**（7 Gates — 合并相邻门控）：
- G1（立项→调研，合并 G1 目标检查）
- G2（调研+选型→设计，G2+G3 merged）
- G3（设计→开发，G5）
- G4（开发+测试→CI，G6+G7 merged）
- G5（CI→发布，G8）
- G6（发布→运营，G9）
- G7（运营→维护，G10）

**standard**（11 Gates — 完整门控）：
- G1~G11 全部独立行，状态列按以下规则填写：
  - **IF** project_type=new → 全部标记为 `pending`
  - **IF** project_type=existing → `current_stage` 之前的 Gate 标记为 `passed-on-entry`，`current_stage` 的 Gate 标记为 `pending`

**strict**（11 Gates + 量化评分列）：
- G1~G11 全部独立行，且每行增加"量化评分（0~5）"列
  - ≥3 分通过，<3 分阻塞
  - **IF** project_type=new → Gate 评分列留空标记 `pending`
  - **IF** project_type=existing → 前置 Gate 标记 `passed-on-entry`，评分留 `—`

##### 任务跟踪表（按 profile 生成不同列）

**lightweight**（6 列精简）：
`[ID, 阶段, 任务项, 目标/预期结果, 状态, 优先级]`

**standard**（完整 20 列）：
`[ID, 阶段, 任务项, 目标/预期结果, 输入, 输出, Owner (DRI), 协同角色, Escalation, 状态, 优先级, 计划开始, 计划完成, 实际完成, Gate, 验收标准, 证据, 风险/偏差, 纠偏动作, 备注]`

**strict**（完整 20 列 + 强制证据要求）：
与 standard 相同列，但在 plan-tracker 顶部增加注释：`> **Strict Profile 强制要求**：每个 P0 任务完成时 MUST 有 ≥2 条证据；Gate 评分 ≥3/5 才通过；无 Owner 的任务不允许进入执行`

#### evidence-log.md
- 证据记录表头：[编号, 对应任务 ID, 阶段, 证据类型, 证据说明, 证据位置, 提交人, 提交日期, 关联 Gate, 备注]

#### decision-log.md
- 决策记录表头：[编号, 日期, 决策标题, 上下文, 可选方案, 决策结论, 理由, 影响范围, 相关任务, 状态, 复核日期]

#### risk-log.md
- 风险记录表头：[编号, 识别日期, 风险描述, 影响, 概率, 等级, 缓解措施, 触发条件, 责任人, 状态, 最后更新]

### Step 6: 中途接入处理（仅 project_type=existing）
- **IF** project_type=existing → 在 decision-log.md 中新增一条决策记录，说明为何项目当前处于 `current_stage` 阶段，格式：`DEC-001 | <today> | 中途接入声明 | 项目已在 <current_stage> 阶段 | 选项：从立项开始 / 中途接入 | 中途接入 — 前置阶段标记 passed-on-entry | 项目已运行至 <current_stage>，补齐历史记录成本过高 | G1~G{current_gate-1} 状态 | — | 已执行 | —`

### Step 7: 注入 governance bootstrap 到 agent 入口文件
- **IF** 项目根目录存在 `CLAUDE.md` → 检查是否含 `## Governance Bootstrap`
  - **IF** 已含 → 跳过，不做修改
  - **ELSE** → 在文件末尾追加 goverance bootstrap 块（以 `## Governance Bootstrap (added by software-project-governance plugin)` 开头标记）
- **IF** 项目根目录不存在 `CLAUDE.md` → 创建 `CLAUDE.md`，内容仅为 governance bootstrap 块

Bootstrap 注入内容：
```markdown
## Governance Bootstrap (added by software-project-governance plugin)

Before executing any tasks, read `.governance/plan-tracker.md` to confirm: current stage, latest Gate status, active risks, and in-progress P0 tasks. If `.governance/` does not exist, remind the user to run governance-init first.

Before starting a new task: check if it's already in the plan tracker. If not, add it first.

After completing a task: log evidence to `.governance/evidence-log.md`.
```

### Step 8: 输出确认
按照 Output Format 模板输出确认信息。

## Output Format

### Required Fields
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| project_name | string | 项目名称 | "项目管理工作流插件" |
| profile | string | 治理强度 | "standard" |
| trigger_mode | string | 触发模式 | "always-on" |
| current_stage | string | 当前阶段 | "initiation" |
| created_files | list | 创建的文件列表 | [".governance/plan-tracker.md", ".governance/evidence-log.md", ".governance/decision-log.md", ".governance/risk-log.md"] |
| bootstrap_injected | boolean | 是否注入了 bootstrap | true/false |
| gate_status | table | 各 Gate 初始化状态 | G1~G11 的简短状态表 |

### Output Template

```
Governance initialized for "{project_name}"

Profile: {profile}
Trigger mode: {trigger_mode}
Current stage: {current_stage}

Created files:
  ✅ .governance/plan-tracker.md
  ✅ .governance/evidence-log.md
  ✅ .governance/decision-log.md
  ✅ .governance/risk-log.md
  {if bootstrap_injected}✅ CLAUDE.md — governance bootstrap injected
  {if not bootstrap_injected}⊘ CLAUDE.md — governance bootstrap already present, skipped

Gate status:
  {gate_status_table}

Your agent will now automatically track project governance.
```

## Error Codes

| Code | Condition | User Message | Agent Action |
|------|-----------|-------------|-------------|
| INIT-ERR-001 | `.governance/` 已存在且含 plan-tracker.md | "Governance has already been initialized for this project. To reinitialize, manually delete `.governance/plan-tracker.md` first, then run this command again." | 停止执行，不做任何文件修改 |
| INIT-ERR-002 | profile 不在有效值范围 | "Invalid profile '{value}'. Valid profiles are: lightweight, standard, strict." | 停止执行，不做任何文件修改 |
| INIT-ERR-003 | project_type=existing 但未提供 current_stage | "For existing projects, you must specify the current stage. Valid stages: initiation, research, selection, infrastructure, architecture, development, testing, ci-cd, release, operations, maintenance." | 停止执行，不做任何文件修改 |

## Self-Validation

After execution, agent MUST verify:
- [ ] `.governance/` directory exists and is writable
- [ ] All 4 files (plan-tracker, evidence-log, decision-log, risk-log) exist with correct headers
- [ ] plan-tracker.md contains: project config block, Gate status table (11 rows), project overview table, empty task table header
- [ ] If project_type=existing, decision-log.md contains at least 1 decision record (DEC-001)
- [ ] Output confirmation contains all Required Fields from Output Format
- [ ] No file contains placeholder values for required toplevel182 fields
