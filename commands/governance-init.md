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

**版本检测规则**——bootstrap 模板升级时，已注入用户需要升级路径：

- **IF** 项目根目录存在 `CLAUDE.md`：
  - **IF** 含 `## Governance Bootstrap（强制` → 已是最新版中文完整模板，跳过
  - **IF** 含 `## Governance Bootstrap (added by software-project-governance plugin)` → 旧版英文 stub 检测到——**MUST** 提示用户："检测到旧版 governance bootstrap（v0.1 英文 stub）。新版包含触发模式感知、跨会话状态恢复、3 项交叉验证等升级。是否升级？" → 用户确认后替换为新模板
  - **ELSE** → 在文件末尾追加 governance bootstrap 块
- **IF** 项目根目录不存在 `CLAUDE.md` → 创建 `CLAUDE.md`，内容仅为 governance bootstrap 块

**注入时 Profile 差异化**：
- **IF** profile = lightweight → 注入精简版模板（3 节：首次动作/干活前/收工前）
- **IF** profile = standard 或 strict → 注入完整版模板（Step 0~3 + 干活前检查 + 提问规则 + 关键决策分类 + 收工前检查）

Bootstrap 注入内容（按 `profile` 差异化——lightweight 注入精简版，standard/strict 注入完整版）：

**lightweight profile 注入模板**：
```markdown
## Governance Bootstrap (added by software-project-governance plugin)

### 每次会话第一动作
读取 `.governance/plan-tracker.md`，确认：当前阶段、最近 Gate 结论、活跃风险。如果 `.governance/` 不存在，提醒用户先初始化。

### 干活前检查
- 这个任务在计划跟踪表里吗？不在就先入账
- 做完后需要补什么证据？先想清楚

### 收工前检查
1. 输出本轮完成事项摘要
2. 补证据到 `.governance/evidence-log.md`
```

**standard / strict profile 注入模板**（完整版——自包含，不依赖 SKILL.md 加载状态）：
```markdown
## Governance Bootstrap（强制 — 每次会话第一动作）

在执行任何用户任务之前，**MUST** 先完成以下步骤：

### Step 0: 确定触发模式
读取 `.governance/plan-tracker.md` 的 `## 项目配置` 节，确认 `触发模式`：
- **always-on**（默认）→ 执行完整 Step 1~3。治理面板可正常输出。
- **on-demand** → 仅执行 Step 1（读 plan-tracker 确认当前阶段/活跃风险）。Step 2~3 仅在用户显式调用 governance 命令时执行。不主动输出治理面板。
- **silent-track** → 执行 Step 1~2，但 **MUST NOT** 向用户输出治理面板、风险统计、任务进度表。仅在 Gate 失败或风险 escalation 到期时打断用户。

### Step 1: 读 plan-tracker + 跨会话恢复
读取 `.governance/plan-tracker.md`，确认：当前阶段、最近 Gate 结论、活跃风险数、进行中的 P0 任务。
**跨会话恢复**：读取 `.governance/session-snapshot.md`（如存在）——恢复 carry-over 任务、待确认决策、活跃风险。

### Step 2: 交叉验证（3 项强制检查）
1. **证据完整性**：plan-tracker 中"已完成"的任务，evidence-log 中是否有对应证据？
2. **Gate 一致性**：Gate 标记 passed 但无对应证据 = 不一致
3. **风险过期**：risk-log 中活跃风险超过 7 天未更新 = 过期
任一失败 → 列出差距 → 征求用户是否修复（AskUserQuestion）。

### Step 3: 优先级确认
passed-with-conditions 遗留项或有 P0 任务 → 优先处理。上次 session 未完成的 P0 任务 → 继续执行。

**没读 plan-tracker 就开始干活 = 流程违规。**

### 干活前检查（每次收到任务时）
- 这个任务在计划跟踪表里吗？不在就先入账
- 做完后需要补什么证据？先想清楚
- 这个任务会不会影响别的阶段？影响就先记风险

### 提问规则（强制）
**AskUserQuestion 是唯一合法的用户提问方式。** 禁止内联文字问"要不要继续""是否如何如何"。
默认模式：**仅在关键决策停下来**，非关键决策自动执行。

**关键决策** — 必须停下来用 AskUserQuestion：
- 范围变更 / 架构决策 / 发布决策 / 风险接受 / 外部依赖变更 / Profile或触发模式变更

**非关键决策** — 自动执行：
- 任务排序 / 证据格式 / commit时机 / 治理记录更新 / 微小实现选择 / Gate自评（仅失败时告知）

### 收工前检查（session 结束前）
1. 输出本轮完成事项摘要
2. 补证据到 `.governance/evidence-log.md`
3. 写入 `.governance/session-snapshot.md`（carry-over任务+待确认决策+活跃风险+下轮优先级）
4. 用 AskUserQuestion 确认下一步优先级

### 详细规则
完整行为协议见 `software-project-governance` skill（M0~M9 强制性规则、Gate 行为等）。以上 bootstrap 规则不依赖 SKILL.md 是否被加载。
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
