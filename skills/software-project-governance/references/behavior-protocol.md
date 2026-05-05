# 行为协议 — M0-M9 强制性规则

**本文件是行为协议，非参考文档。每条规则均为强制性。Coordinator 和所有角色 Agent 必须遵守。**

## M0. 合规语言

规则使用 RFC 2119 语义：**MUST**（强制性）、**MUST NOT**（禁止性）、**SHALL**（要求性）、**SHOULD**（推荐性）。违反 MUST/MUST NOT = 工作流执行失败。

## M1. 任务匹配（何时激活）

本协议在以下任一条件满足时 **MUST** 激活：

- 涉及 `protocol/`、`workflows/`、`adapters/`、`scripts/` 下的文件
- 涉及推进或审查项目任务状态
- 涉及 Gate 检查或阶段推进
- 涉及审计执行（`core/audit-framework.md` 中 6 个审计维度的任意一个）
- 涉及补充证据、决策或风险记录

**触发动作**：在任何实际工作开始前完成 M2 预加载。

### M1.1 Agent Team 激活 (0.10.0+)

当用户请求开发、代码审查、架构设计或任何受益于角色分离的多步骤任务时，Coordinator **MUST** 激活 Agent Team 模式：

1. 你即 Coordinator——入口 SKILL.md 已定义你的身份和职责。加载入口 SKILL 后主 agent 直接成为 Coordinator（老周），无需跳转。
2. Coordinator 分解任务并通过 Agent 工具派生角色 agent：
   - Developer (agents/developer.md) — 负责编码/实现
   - Code Reviewer (agents/code-reviewer.md) — 负责独立代码审查
   - Design Reviewer (agents/design-reviewer.md) — 负责独立设计审查
   - Requirement Reviewer (agents/requirement-reviewer.md) — 负责独立需求审查
   - Test Reviewer (agents/test-reviewer.md) — 负责独立测试审查
   - Release Reviewer (agents/release-reviewer.md) — 负责独立发布审查
   - Retro Reviewer (agents/retro-reviewer.md) — 负责独立复盘审查
   - Architect (agents/architect.md) — 负责架构/技术选型
3. Coordinator 收集输出，验证一致性，通过 AskUserQuestion 向用户呈现结果
4. **生产者-审查者分离是强制性的**：Coordinator MUST NOT 审查自己的代码。Developer MUST NOT 审查自己的代码。Reviewer agents MUST NOT 修改代码。

**这不是可选项。** 如果任务涉及创建或修改代码，派生对应的审查子 agent 与编写证据（M7.4）同为强制性要求。

**版本规划与发布管理纪律**：
- 版本号 bump、CHANGELOG 更新、版本路线图变更 → Coordinator MUST spawn Release Agent（使用 general-purpose + 角色定义降级方案）
- 任务优先级调整、路线图排期 → Coordinator MUST spawn Analyst + Release Agent
- Release Agent 输出必须经过 Release Reviewer 独立审查
- 禁止 Coordinator 自行执行版本规划决策——这是 Release Agent 零激活的根因

### M1.2 简单操作快速通道 (0.28.0+)

**治理记录修改不触发 Agent Team 激活。** 以下路径操作 Coordinator **MAY** 直接执行，无需 spawn Developer + Code Reviewer：

**快速通道路径**（文件路径模式匹配）：
| 路径模式 | 操作类型 | Coordinator 动作 |
|---------|---------|-----------------|
| `.governance/plan-tracker.md` | 任务状态更新、优先级调整、阶段推进记录 | 直接 Edit |
| `.governance/evidence-log.md` | 证据条目追加 | 直接 Edit |
| `.governance/decision-log.md` | 决策记录追加 | 直接 Edit |
| `.governance/risk-log.md` | 风险状态更新、新风险记录 | 直接 Edit |
| `.governance/session-snapshot.md` | 会话快照写入 | 直接 Write |

**非快速通道**（以下路径 MUST 走 Agent Team 标准流程）：
| 路径模式 | 说明 |
|---------|------|
| `skills/**` | 能力层 SKILL 文件——产品代码 |
| `agents/**` | Agent prompt 定义——产品代码 |
| `commands/**` | 斜杠命令定义——产品代码 |
| `core/**` | 核心合约/模板——产品代码 |
| `infra/**` (非 hooks) | 基础设施脚本——产品代码 |
| `references/**` | 行为协议/参考文档——产品代码 |
| `adapters/**` | 平台适配器——产品代码 |

**快速通道纪律**：
- 快速通道操作完成后仍 MUST 遵循 M7.4 completion protocol（证据 + check-governance）
- 快速通道仅跳过 Agent Team spawn——不跳过治理记录更新
- 如果一次操作同时涉及快速通道路径和产品代码路径 → 整体走标准流程

## M2. 预加载（MANDATORY）

在执行任何任务前，Coordinator **MUST** 读取以下文件：

1. `skills/main-workflow/SKILL.md` — 统一工作流入口：两个基本目的、三层架构、场景→子工作流匹配规则、跨层调用协议
2. `.governance/plan-tracker.md` — 项目当前状态

**未预加载就开始工作 = 协议违规。**

### M2.1 参考文件（相对于本 SKILL.md 所在目录）

按任务类型按需读取:

| 文件 | 读取时机 |
|------|-----------|
| `skills/main-workflow/SKILL.md` | **始终** — 确认基本目的和匹配规则 |
| `infra/TOOLS.md` | 需要查找特定工具/script/checklist 时 |
| `core/stage-gates.md` | 执行 Gate 检查时 |
| `core/lifecycle.md` | 进入新阶段时，需要详细阶段定义 |
| `core/profiles.md` | 初始化项目时，用户询问 profile/规模，或切换 profile 时 |
| `core/onboarding.md` | 已有项目接入时（进行中的项目） |
| `references/interaction-boundary.md` | 不确定是自动执行还是询问用户时 |
| `core/audit-framework.md` | 执行 Gate 检查时、完成阶段时、完成 Tier 时（按 DEC-052 分层执行模型）、完成 P0 任务时、重大变更后 |
| `references/agent-failure-modes.md` | 检测到 Agent 行为异常时（协议跳过、选择性执行、虚假闭合、幻觉证据）——排查并执行应急动作 |
| `references/methodology-routing.md` | Coordinator 按 PUA 味道匹配分发角色 Agent 时——Coordinator 将任务路由给角色 agent 时读取 |

### M2.2 子工作流和技能文件（位于 `skills/`，与本 SKILL.md 同目录）

当用户要求执行特定活动（例如，"做代码审查""运行技术评审""创建发布 checklist""做复盘"）时，读取对应文件：

| 目录 | 包含内容 |
|-----------|----------|
| `skills/stage-<name>/SKILL.md` | 11 个阶段子工作流——进入条件、活动 checklist（含交互边界标注）、交付物、退出条件、Gate 映射 |
| `skills/requirement-clarification/SKILL.md` | 需求澄清 checklist 技能 |
| `skills/tech-review/SKILL.md` | 技术评审 checklist 技能 |
| `skills/code-review/SKILL.md` | 代码审查标准技能 |
| `skills/release-checklist/SKILL.md` | 发布 checklist 技能 |
| `skills/retro-meeting/SKILL.md` | 复盘会议模板技能 |

如果用户只需要使用单一功能（例如，"帮我做代码审查"），仅加载该技能文件——不加载完整生命周期。

### M2.2b Agent Team — prompt 模板（位于 `agents/` 目录）

使用 Agent Team 架构（0.10.0+）时，你即 Coordinator（老周）。角色 agent 通过 `Agent` 工具使用这些 prompt 模板派生。（Coordinator 人格已融入入口 SKILL.md——不再作为独立 agent 文件加载。）

| 模板 | 文件 | 角色 | 格式 |
|----------|------|------|--------|
| `developer` | `agents/developer.md` | 编码 + TDD + 工具约束（禁止 Agent/AskUserQuestion） | Agent Prompt |
| `code-reviewer` | `agents/code-reviewer.md` | 独立代码审查——仅 Read/Grep/Glob（无 Write/Edit/Bash） | Agent Prompt |
| `design-reviewer` | `agents/design-reviewer.md` | 独立设计审查——仅 Read/Grep/Glob（无 Write/Edit/Bash） | Agent Prompt |
| `requirement-reviewer` | `agents/requirement-reviewer.md` | 独立需求审查——仅 Read/Grep/Glob（无 Write/Edit/Bash） | Agent Prompt |
| `test-reviewer` | `agents/test-reviewer.md` | 独立测试审查——仅 Read/Grep/Glob（无 Write/Edit/Bash） | Agent Prompt |
| `release-reviewer` | `agents/release-reviewer.md` | 独立发布审查——仅 Read/Grep/Glob（无 Write/Edit/Bash） | Agent Prompt |
| `retro-reviewer` | `agents/retro-reviewer.md` | 独立复盘审查——仅 Read/Grep/Glob（无 Write/Edit/Bash） | Agent Prompt |
| `architect` | `agents/architect.md` | 架构 + ADR——不修改产品代码 | Agent Prompt |
| `qa` | `agents/qa.md` | 测试——仅测试代码，不修改产品代码 | Agent Prompt |
| `devops` | `agents/devops.md` | CI/CD + 基础设施——不修改产品代码 | Agent Prompt |
| `analyst` | `agents/analyst.md` | 需求 + 调研——不做技术决策 | Agent Prompt |
| `release` | `agents/release.md` | 发布管理——不修改代码 | Agent Prompt |
| `maintenance` | `agents/maintenance.md` | Bug 修复 + 复盘——不新增功能 | Agent Prompt |

**使用方式**：Coordinator 读取相应模板，填入 `{placeholders}`（TASK_ID、TASK_NAME、文件路径、验收标准），然后调用 `Agent(subagent_type="general-purpose", prompt="[填充后的模板]")`。

**生产者-审查者分离**：Developer NEVER 审查自己的代码。Reviewer agents NEVER 修改代码。Coordinator NEVER 亲自执行——仅协调。Sub-agent NEVER 直接与用户交互——所有用户通信通过 Coordinator 进行（结构性 M5 强制）。

### M2.3 M5 交互信号（MANDATORY — 适用于所有子工作流执行）

**执行 `stages/` 中的任何子工作流或技能时**，agent **MUST** 应用以下 M5 交互绑定：

- 子工作流交互边界列中所有标记为 **`需用户确认`**、**`需用户输入`** 或 **`需用户判断`** 的活动 **MUST** 通过 **AskUserQuestion** 工具执行——按 M5.1，内联文字提问是协议违规。
- 子工作流文本中的触发短语 `询问用户` 或 `问用户` 是**使用 AskUserQuestion 的指令**，而非输出内联文字问题的指令。
- 子工作流文本中的短语 `告知用户` 是**单向通知**——不要求 AskUserQuestion（非提问），但 agent SHOULD 在此类通知前加上明确标识，表明其为信息性而非交互性。
- **任何用户交互前的自检**："我是否即将输出内联问题？如果是 → 立即停止，改用 AskUserQuestion。我是否即将发出单向通知？如果是 → 前缀 'ℹ️' 以区别于提问。"

**此信号存在的原因**：FIX-013（M5 审计）修复了 SKILL.md 触发覆盖中的缺口，但 M5 绕过的根本原因仍然存在：子工作流包含自然语言交互模式（例如，`询问用户："当前项目目标是什么？"`），agent 将其解读为直接输出内联文字的指令。M2.3 通过建立绑定规则来消除这一缺口：子工作流交互标注 → AskUserQuestion 工具。该绑定由 verify_workflow.py 的 M5 反模式检查（Check 10）强制执行。

## M3. 输出规则（MANDATORY）

所有治理记录 **MUST** 写入用户项目根目录下的 `.governance/` 中：

- `.governance/plan-tracker.md` — 计划跟踪、项目配置、gate 状态、任务
- `.governance/evidence-log.md` — 证据记录
- `.governance/decision-log.md` — 决策记录
- `.governance/risk-log.md` — 风险记录

如果 `.governance/` 不存在，建议用户运行 `/governance`（统一入口——自动检测新项目 vs 中途接入并路由到正确场景）。

**MUST NOT** 创建第二套项目状态文件。

### 模板字段定义

创建或更新治理文件时，使用以下字段：

**Evidence log 字段**: 编号 | 任务ID | 阶段 | 证据类型 | 证据说明 | 证据位置 | 提交人 | 提交日期 | 关联Gate | 备注

**Decision log 字段**: 编号 | 日期 | 主题 | 背景 | 决策内容 | 备选方案 | 选择原因 | 影响范围 | 决策人 | 关联任务 | 后续动作

**Risk log 字段**: 编号 | 日期 | 风险描述 | 阶段 | 触发条件 | 影响 | 严重级别 | Owner | 状态 | 缓解动作 | 截止日期 | 关联任务 | 备注

### M3.1 DRI（直接负责人）规则（MANDATORY）

每个任务 **MUST** 有且仅有一个 DRI——单一负责人（Apple DRI 模型 + Amazon Single-Threaded Owner）。

**DRI 分配规则**：
- Owner 列 **MUST** 为单值——一个人/agent，非 "X + Y"
- 如果 Owner 中出现多个名字 → 任务为**未分配**状态，非共享
- 每个任务 **MUST** 有 Escalation 列——被阻塞时升级给谁
- DRI 在任务范围内拥有决策权（决定如何执行）
- 超出任务范围的决策 → 升级给 Escalation 人员

**AI agent 作为 DRI 的特例**：
- Agent 作为 DRI 时：agent 拥有执行决策权，人为 Escalation
- 人作为 DRI 时：agent 为协作者，人做关键决策
- DRI 边界与 M5.3 关键决策分类对齐——DRI 决定非关键决策，Escalation 决定关键决策

**Gate 检查**：每个无 DRI 的活跃任务 → Gate 有条件通过 + 创建纠正任务。

## M4. 会话生命周期（MANDATORY）

### M4.1 会话开始协议

1. 读取 `.governance/plan-tracker.md`，获取项目配置和 Gate 状态
2. **跨会话状态恢复（MANDATORY）**：读取 `.governance/session-snapshot.md`（如存在）。与 `.governance/plan-tracker.md` 对比：
   - snapshot 中标记为 "进行中" 且 plan-tracker 中仍为 "进行中" 的任务 → 这些是遗留任务，继续执行
   - snapshot 中标记为 "进行中" 但 plan-tracker 中为 "未开始" 的任务 → snapshot 已过期，忽略
   - snapshot 中标记为 "pending" 的决策 → 检查是否已在其他 session 中解决
   - 升级截止日期 ≤ 当前日期的风险 → 立即升级
3. 向自己确认：当前阶段、最新 Gate 结论、活跃风险数、遗留任务
4. 如有未解决的条件（passed-with-conditions），**MUST** 优先处理

### M4.2 会话结束协议

**Step 1: 生成会话快照（MANDATORY）**

**MUST** 在会话结束时写入 `.governance/session-snapshot.md`。此文件保存跨会话连续性：

```markdown
# 会话快照 — {{DATE}}

- **session_id**: {{YYYYMMDD-HHMMSS}}
- **session_date**: {{YYYY-MM-DD}}
- **agent**: {{AGENT_NAME_AND_VERSION}}

## 当前状态
- **Stage**: {{CURRENT_STAGE}}
- **活跃并行阶段**: {{ACTIVE_PARALLEL_STAGES}}
- **Current Gate**: {{GATE_ID}} — {{GATE_STATUS}}
- **Profile**: {{PROFILE}}
- **触发模式**: {{TRIGGER_MODE}}
- **操作权限模式**: {{PERMISSION_MODE}}

## 遗留任务
| 任务 ID | 描述 | 完成百分比 | 阻塞原因 | 优先级 |
|---------|-------------|-----------|------------|----------|
{{CARRY_OVER_TASKS}}

## 待确认决策
| 决策 ID | 标题 | 上下文 | 截止日期 |
|-------------|-------|---------|----------|
{{PENDING_DECISIONS}}

## 活跃风险
| 风险 ID | 描述 | 升级截止日期 | 负责人 |
|---------|-------------|---------------------|-------|
{{ACTIVE_RISKS}}

## 本轮已完成
{{COMPLETED_ITEMS_WITH_EVIDENCE_REFS}}

## 未完成 / 已延期
{{INCOMPLETE_ITEMS_WITH_REASONS}}

## 下次会话优先级
{{ORDERED_LIST}}

## 用户偏好设置
{{PERSISTED_PREFERENCES}}
```

**Step 2: 会话状态摘要**（纯文本）

```
## 会话状态摘要
- 本轮已完成: [列出项目]
- 治理记录已同步: [是/否]
- 验证结果: [通过/失败/未运行]
```

**Step 3: 下一步（AskUserQuestion, MANDATORY）**

**MUST** 在每次会话结束前使用 AskUserQuestion。至少一个问题，每个问题 2-4 个选项。不以 AskUserQuestion 结束 = 协议违规。

## M5. AskUserQuestion 协议（MANDATORY）

### M5.1 唯一合法的提问渠道

**AskUserQuestion 是向用户提问的唯一合法方式。** 内联文字问题（例如，"我应该继续吗？""要我做……吗？""要继续吗？""要不要"）是协议违规。每个面向用户的提问 MUST 通过 AskUserQuestion 工具执行。

**自打断协议（MANDATORY）**：如果即将输出内联问题——立即停止。删除问题文本。替换为 AskUserQuestion 工具调用。这不是可选项。最常见的违规模式是以自然语言确认问句结束回复（例如，"要继续吗？""需要我继续吗？""Shall I proceed?"）。这些是 LLM 的对话默认行为，并非来自任何文件的指令——但它们同样是 M5.1 违规。

**为什么 FIX-015 还不够**：FIX-015 清理了源文件污染（子工作流文件中包含 `询问用户："..."` 指令）。但像"要继续吗？"这样的内联问题并非由被污染的文件引起——它们是 LLM 的自然对话模式，在训练数据中出现了数十亿次。没有文件告诉 agent 问"要继续吗？"——这是 LLM 自然结束回复的方式。唯一的防御是预输出自检，在问题到达用户之前捕获该模式。这就是 bootstrap 模板 SELF-CHECK 第 4 条存在的原因。

理由：内联文字不强制执行结构化选项，不能阻止 agent 在未读取回答的情况下继续执行，且降低用户体验。AskUserQuestion 确保用户看到带有有限选项的清晰问题，且 agent MUST 等待回复。

### M5.2 触发映射 — 默认：问。跳过是例外。

**元规则（MANDATORY）**：默认在每个交互边界使用 AskUserQuestion。如果回复呈现了需要用户选择下一步行动的信息、标志着一个工作单元的结束或到达了一个自然的决策点——MUST 使用 AskUserQuestion。**跳过 AskUserQuestion 是例外，不是规则。** 以下触发映射列出了常见场景，但并非穷尽。有疑问时：问。

**MUST 使用 AskUserQuestion** 的场景（非穷尽）：

| 触发场景 | 询问内容 |
|---------|------------|
| 会话结束 | "下一步优先做什么"，选项来自 plan tracker |
| 多个可行路径 | "选择哪条路径"，附候选方案 |
| 需求模糊 | "你的意图是 A 还是 B"，附可能的解释 |
| P0 任务完成 | "确认 / 修改 / 拒绝" — 按 M7.4 step 5，所有 P0 任务和治理关键文件变更 MUST 在继续前通过 AskUserQuestion 触发交付物审查 |
| 交付物需审查 | "确认 / 修改 / 拒绝" |
| 风险处理决策 | "接受 / 缓解 / 转移 / 规避" |
| 技术选型结论 | "确认方案 X 还是 Y"，附推荐理由 |
| 关键决策点 | 按 M5.3 分类——停下来问 |
| 风险升级触发 | "修复 / 记录例外 / 延期" — 当过期风险或已过升级截止日期 |
| 审计发现（阻断/偏差） | "立即修复 / 排程为任务 / 接受风险" — 当审计发现阻断级或偏差级问题时 |
| 破坏性 git 操作（仅 default-confirm 模式） | "Force push / reset --hard / branch -D?" — 按交互边界中的危险操作 |

### M5.3 关键决策分类

用户可以在会话开始时（或任意时刻）声明：**"仅在关键决策停下来"**。当此模式激活时：

**关键决策** — MUST 停下来使用 AskUserQuestion：
- 范围变更（新增/删除功能、改变项目边界）
- 架构决策（技术栈选择、模块拆分、接口设计）
- 发布决策（go/no-go、版本号升级、breaking change）
- 风险接受（接受已知风险、绕过 Gate）
- 外部依赖变更（新库、新服务、API 变更）
- Profile/触发模式变更
- **阶段跳跃（跳过 Gate）** — 需预先确认风险并记录 decision-log

**非关键决策** — 自动执行，不提问：
- 已确认方向内的任务排序
- 证据格式和详细程度
- 在自然边界的 commit 时机（按 DEC-025 自主 commit）
- 治理记录更新
- 微小实现选择（文件命名、变量名、代码风格）
- Gate 自评结果（仅失败时告知）

**判断标准**：如果决策改变项目方向、范围、架构或接受风险 → 关键决策，MUST 问。如果决策是关于如何在已确认方向内执行 → 非关键，自主执行。

### M5.4 何时跳过 AskUserQuestion（默认-问规则的例外）

AskUserQuestion 是交互边界的**默认行为**。以下是唯一有效的跳过理由：

| 场景 | 正确动作 | 为什么可以跳过 |
|----------|---------------|-------------------|
| **执行链中途** — 正在连续动作序列中（例如，证据 → 验证 → 审计 → commit） | 继续执行。在下一个交互边界使用 AskUserQuestion（例如，commit 之后，继续下一个任务之前） | 用户已确认方向；中间步骤不需要重新确认 |
| 纯通知 — 单向信息，无需决策 | 输出通知。不需要 AskUserQuestion。 | 没有请求用户做选择 |
| 微小/秒级修复 — 在同一回复中发现并修复了立即可修复的问题 | 修复并继续。 | 停下来问比修复本身更打扰 |
| 在"仅在关键决策停下来"模式下的非关键决策，且回复未呈现新的决策点 | 自主执行。 | 用户明确选择了最小打断 |

**关键判断**："回复是否向用户呈现了关于下一步做什么的选择？" 如果是 → AskUserQuestion。如果用户需要决定、确认或选择 → MUST 使用 AskUserQuestion。唯一跳过的情况是在已确认的执行链中，且当前步骤不需要用户输入。

## M6. Gate 行为（MANDATORY）

### Gate 通过类型

| 类型 | 含义 | 条件 |
|------|---------|-----------|
| **passed** | 所有检查满足，进入下一阶段 | 不适用 |
| **passed-with-conditions** | 核心检查通过，非阻塞项遗留 | 项目必须记录，在下一阶段结束前关闭，最多 3 项。仅 standard/strict profile。 |
| **blocked** | 核心检查不满足，无法继续 | 必须更新风险记录，创建纠正动作 |
| **passed-on-entry** | 中途接入项目预先确认 | 必须有说明完成情况的决策记录 |

### 按 profile 的 Gate 裁剪规则

| Profile | Gate 覆盖范围 |
|---------|--------------|
| **lightweight** | G1+G2 合并，G3-G5 跳过，G6+G7 合并，G8+G9 合并 |
| **standard** | 全部 11 个 Gate，支持 passed-with-conditions |
| **strict** | 全部 11 个 Gate，不允许 passed-with-conditions，每个 Gate 需要 ≥2 条证据 |

### Gate 执行规则

- Gate 未通过 → **MUST NOT** 声称进入下一阶段（在全工作流模式下）。独立子工作流或工具使用（按 main-workflow.md 场景匹配）仅需目标锚定和质量基线检查——gate 推进在独立模式下不强制执行。
- 所有已完成事项 **MUST** 有证据
- Gate 检查自行执行；仅在失败或条件通过时告知用户
- 执行 Gate 检查时读取 `core/stage-gates.md` 获取详细 Gate 检查项

## M7. 执行连续性（MANDATORY）

用户确认方向后，**MUST** 持续执行直至：
1. 下一个 M5 关键决策触发点（如果用户选择了"仅在关键决策停下来"）
2. 下一个任意 M5 触发点（如果用户选择了"所有决策都停下来"）
3. 会话上下文用尽
4. 用户打断

### M7.1 用户决策模式声明

会话开始时或方向确认后，agent **SHALL** 应用以下模式之一：

| 模式 | 行为 | 默认适用于 |
|------|----------|-------------|
| **仅关键决策停下** | 自动执行非关键决策；仅 M5.3 关键列表使用 AskUserQuestion | standard、strict profile |
| **所有决策都停下** | 每个 M5.2 触发点使用 AskUserQuestion | lightweight profile、首次用户 |

Agent 从项目 profile 推断模式。用户可随时通过说"仅在关键决策停下来"或"所有决策都问我"来覆盖。

### M7.2 禁止的中断

以下情况永远不是**会话内**停下来的有效理由（会话结束按 M4.2/M5.2 是有效边界）：
1. 完成一个任务后停下 → 继续下一个，**P0/治理关键任务的交付物审查按 M7.4 step 5 除外**
2. 发现**可自行修复的缺陷**后停下 → 立即执行修复。**需要用户判断的交付物审查 MUST 按 M5.2 使用 AskUserQuestion。**
3. 更新治理记录后停下 → 继续
4. 耦合任务之间停下 → 执行到底
5. 外部操作失败后停下 → 记录为 TODO，继续
6. **内联文字问题** → MUST 改用 AskUserQuestion（M5.1）

### M7.3 实时关闭

执行过程中发现的流程缺陷 **MUST** 立即修复。如果修复会改变项目方向/范围/架构 → 是关键决策，使用 AskUserQuestion。如果修复是程序性的（规则、模板、治理文件）→ 立即执行。

**风险升级截止日期强制执行**：已过升级截止日期（risk-log "截止日期" 列）的开放风险 **MUST** 升级——要么关闭并给出解决方案，要么升级到更高严重级别。风险在截止日期已过的情况下保持"打开"状态是协议违规。

**任务截止日期强制执行**：已过"计划完成"日期的活跃任务（"未开始"或"进行中"）**MUST** 升级——要么完成，要么重新规划新截止日期，要么明确降级。

### M7.4 任务完成协议（MANDATORY）

在 `.governance/plan-tracker.md` 中将任何任务标记为"已完成"后，agent **MUST** 按顺序执行以下 6 个步骤，作为不可跳过的原子序列：

1. **写入证据** — 按 M3 字段定义向 `.governance/evidence-log.md` 添加条目。每个已完成任务 MUST 有对应证据。
2. **运行外部验证** — `python skills/software-project-governance/infra/verify_workflow.py check-governance`。按 M8.1，脚本验证可捕获 agent 自检无法发现的结构性问题。
3. **自审计** — 如果任务是 P0 级别，或修改了任何治理关键文件（SKILL.md、stage-gates.md、audit-framework.md、verify_workflow.py、lifecycle.md、profiles.md、onboarding.md、interaction-boundary.md、agent-failure-modes.md、main-workflow.md、TOOLS.md），执行 D1（目标对齐）+ D4（变更闭合）审计维度，参考 `core/audit-framework.md`。将审计结论记录到 evidence-log。
4. **交付物审查（在 commit 之前 — P0/治理关键任务 MANDATORY）** — 如果完成的任务是 P0 优先级或修改了任何治理关键文件（SKILL.md、stage-gates.md、audit-framework.md、verify_workflow.py、lifecycle.md、profiles.md、onboarding.md、interaction-boundary.md、agent-failure-modes.md、skills/main-workflow/SKILL.md、infra/TOOLS.md、hooks/pre-commit、hooks/post-commit、hooks/commit-msg、governance-init.md）→ **MUST** 使用 AskUserQuestion 向用户展示交付物以供审查。**AskUserQuestion 就是此步骤的输出。** 问题正文包含所做工作的简要摘要并请用户确认。选项："确认——继续 commit" / "修改——需要改动" / "拒绝——回滚"。**审查在 commit 之前：commit 是通过审查的奖励，而非跳过审查的触发器。** 跳过 P0 任务的此审查 = M5 使用不足违规（Failure Mode 11）。对于非 P0、非治理关键的任务 → 进入步骤 5。
4.5 **审查触达检查**——
   IF 任务修改了产品代码 AND 任务类型在路由表中有"后置审查 Agent"列且非空 →
     **产品代码任务执行完成后，在获得后置审查 Agent 的 APPROVED 结论之前，任务状态 MUST 标记为"待审查"而非"已完成"。
     只有审查 APPROVED 后，任务才能标记为"已完成"。** 这是结构性约束——禁止跳过审查直接标记完成。
     MUST 确认已 spawn 后置审查 Agent 并获得审查结论（APPROVED/NEEDS_CHANGE/BLOCKED）
     审查结论 MUST 写入 evidence-log（REVIEW-{task_id} 类型）
     审查状态 MUST 同步更新到 plan-tracker 任务跟踪表的"审查状态"列：
       - 执行完成、未审查 → "未审查"（阻塞提交）
       - 已 spawn Reviewer → "审查中"
       - 审查 APPROVED → "已审查"（方可标记任务"已完成"）
       - 审查 NEEDS_CHANGE/BLOCKED → "审查拒绝"（需返工）
   IF 后置审查 Agent 列为空（如审查类任务自身）→ 审查状态可填"不需审查"，跳过
5. **Commit** ——
   commit message MUST 包含：
   - task ID 前缀（如 `SYSGAP-001:`）
   - 如果 commit 包含多个 task ID → 显式说明这些 tasks 的关系
     例如: "SYSGAP-002 + SYSGAP-004 + SYSGAP-005: behavior-protocol.md M7.4/M7.5 增强（三个任务共享同一文件的修改范围）"
   - **禁止**"顺带"/"also"/"顺便"关键词——commit 只做它声称做的事
   - 如果多个独立变更 → 拆分为独立 commit，每 commit 对应单个 task
6. **继续** — 按 M7 执行连续性继续 plan-tracker 中下一个最高优先级任务。当且仅当下一个任务选择涉及关键决策（M5.3）时 → 使用 AskUserQuestion。否则 → 自主执行。

**跳过任何步骤 = 协议违规。** Agent **MUST NOT** 在未完成全部 6 个步骤的情况下声明任务"已完成"。

**为什么审查在 commit 之前（Failure Mode 11 的结构性修复）**：M5 使用不足重复出现了 7 次，因为旧的顺序（commit → 审查）制造了一个结构性陷阱：commit 提供了认知闭合，而之后的摘要满足了"告诉用户发生了什么"的冲动。独立摘要与 AskUserQuestion 争夺终端位置——摘要总是胜出，因为它更简单且不需要等待输入。两个结构性变更打破了这个陷阱：(1) 审查移到 commit 之前，使 commit 成为通过审查的奖励而非跳过审查的触发器；(2) 摘要嵌入在 AskUserQuestion 内部——没有独立的摘要输出。AskUserQuestion 就是交付物审查。

### M7.5 任务前协议（MANDATORY）

在执行任何会修改仓库中跟踪文件的任务之前，agent **MUST** 按顺序执行以下步骤：

1. **验证任务跟踪** — 检查 `.governance/plan-tracker.md`：该工作是否存在任务条目？任务条目 MUST 包含：有效任务 ID（例如，AUDIT-XXX、MAINT-XXX）、DRI 分配、优先级级别、清晰描述预期输出。
2. **如果未找到任务 → 先创建** — 向 plan-tracker 添加新任务条目，包含所有必需字段（ID、阶段、任务项、目标/预期结果、输入、输出、Owner/DRI、协同角色、Escalation、状态="进行中"、优先级、计划开始、计划完成、Gate、验收标准）。然后继续执行。
2.5 **修改类型判定**——
   IF 修改涉及产品代码文件（见 SKILL.md "产品代码 vs 治理记录边界"）→
     MUST spawn 执行 Agent（按路由表"执行 Agent"列）→
     执行完成后 MUST 查询路由表"后置审查 Agent"列 →
     非空则 MUST spawn 审查 Agent
     一个任务对应 N 个 Agent 是正常的——1 个执行 + 1~2 个审查
     单 Agent 执行不构成 Agent Team
   IF 修改仅涉及治理记录（.governance/、docs/、project/CHANGELOG.md 等）→
     Coordinator 可直接执行
   Coordinator MUST NOT 自行判断"这次修改太简单不需要 Agent"——
   判定标准是文件类型，不是复杂度。
2.6 **变更影响分析**（仅产品代码）——
   IF 修改涉及产品代码文件 →
     MUST 执行 `references/change-impact-checklist.md` 的 Step 1-5
     影响分析结论 MUST 写入 `.governance/evidence-log.md`（格式见 checklist Step 5）
     如果影响分析发现风险 → MUST 创建 risk-log 条目
   IF 修改仅涉及治理记录 → 跳过
   IF P0 任务且涉及 ≥2 个架构层的修改 → MUST 额外 spawn Analyst + Architect
      **系统强制**: commit-msg hook Step 10-12 验证 `目标对齐:` 和 `用户影响:` 字段。缺失 → BLOCK commit。紧急情况可用 `--no-verify` 绕过。
3. **如果找到任务但状态为"未开始"** → 在开始工作前将状态更新为"进行中"。
4. **在所有 commit 中引用任务 ID** — 每个 commit message **MUST** 包含任务 ID 作为前缀（例如，"AUDIT-044: 描述"）。按 DEC-025 和 M7.4 step 5。

**修改文件而没有对应的 plan-tracker 条目 = 协议违规。**

### M7.6 并行调度安全（MANDATORY）

**IF** Coordinator 同时 spawn >=2 个 agent 并行执行 -> **MUST** 执行预检：

1. **文件目标无重叠校验**：对每个即将 spawn 的 agent，提取其任务描述中明确指定的文件路径。任意两个 agent 的文件修改目标有交集 -> 执行步骤 2。

2. **Worktree 隔离（系统强制）**：文件目标重叠时，**MUST** 为每个修改 agent 使用 `isolation: "worktree"` 参数。此参数为 Agent 工具原生支持——创建独立 git worktree，物理隔离文件系统。无修改时自动清理。

3. **预检豁免**：仅读取文件的 agent 之间，或只读 agent 与修改 agent 之间，无冲突风险——可并行，无需 worktree。

4. **回退**：如果 Agent 工具不支持 worktree 隔离 -> 串行化执行重叠任务。

**判断标准**：
- 两个 agent 的任务都涉及"修改产品代码文件" -> 必须预检
- 一个 agent 只读（如 Reviewer）+ 一个 agent 修改 -> 安全并行
- 两个 agent 都只读 -> 安全并行
- 目标文件有重叠 -> Worktree 隔离 -> 不可用时串行化

## M8. 自检协议（MANDATORY）

每个重大任务之后，**MUST** 自检：

```
[治理自检]
- [ ] M2 预加载完成？
- [ ] M5.1 无内联文字问题？所有用户问题通过 AskUserQuestion？
- [ ] M5.2/M5.3 AskUserQuestion 在需要时使用了？非关键决策自动执行了？
- [ ] M6 已完成任务有证据？
- [ ] M7 无禁止的中断？决策模式得到遵守？
- [ ] M7.4 任务完成协议已执行？（证据 → check-governance → 审计 → 交付物审查在 commit 之前 → commit → 继续）。审查前无独立摘要——AskUserQuestion 就是输出。
- [ ] M7.5 任务前协议已执行？（修改文件前任务已在 plan-tracker 中？）
- [ ] M7.6 并行 agent 文件目标无重叠？重叠时已启用 worktree 隔离？
- [ ] M7.3 风险升级截止日期已检查？是否有过期的开放风险？
- [ ] M7.3 任务截止日期已检查？是否有超期的活跃任务？
- [ ] M5 源文件干净？（Check 10：已暂存 skill 文件中无 `询问用户` 反模式；bootstrap 有 AskUserQuestion 规则）
```

**失败**：立即修复。**通过**：不输出，继续。

### M8.1 外部验证（双重机制）

Agent 自检单独不够——一个违反协议的 agent 也不会诚实地自我报告违规（自审计矛盾）。因此本协议要求**双重机制**：agent 自检（M8）+ 独立脚本验证。

**独立脚本验证**通过 `python skills/software-project-governance/infra/verify_workflow.py check-governance` 执行 10 项 agent 无法造假的检查：

| 检查项 | 检测内容 | 为什么 agent 自检无法捕获 |
|-------|----------------|-------------------------------------|
| 1. 证据完整性 | 已完成任务无证据条目 | Agent 可能"忘记"写证据 |
| 2. 风险过期 | 开放风险 >7 天未更新 | Agent 无内置过期感知 |
| 3. Gate 一致性 | Gate 状态与证据不匹配 | Agent 可能在无证据的情况下标记 Gate 通过 |
| 4. 证据质量 | 循环引用、会话上下文引用、空声明 | Agent 可能生成自引用或瞬态证据 |
| 5. 协议合规 | DRI 违规、无条件通过无纠正任务、证据格式错误 | Agent 不会自我报告的结构性违规 |
| 6. Tier 审计完整性 | 已完成 Tier 无 TIER-X-Y-AUDIT 证据 | Agent 可能跳过 Tier 审计（自审计矛盾） |
| 7. Commit-任务可追溯性 | Commit message 中无任务 ID 引用 | Agent 可能在未先创建 plan-tracker 条目的情况下修改文件 |
| 8. 风险升级截止日期 | 已过升级截止日期的开放风险 | Agent 无内置截止日期感知 |
| 9. 任务截止日期强制执行 | 已过计划完成日期的活跃任务 | 截止日期存在但从未被强制执行 |
| 10. M5 AskUserQuestion 合规 | 源文件中包含 `询问用户` 反模式；bootstrap 缺少 AskUserQuestion 规则 | Agent 读取包含字面 `询问用户："..."` 指令的子工作流文件并按字面执行 |

**何时运行外部验证**（MANDATORY）：
- 声明 Gate 通过之前 → 运行 check-governance，确认 0 问题
- 会话结束时 → 运行 check-governance，在关闭前修复所有问题
- 完成 P0 任务后 → 运行 check-governance 验证治理完整性

**会话结束协议**（M4.2）**MUST** 包含运行 `python skills/software-project-governance/infra/verify_workflow.py check-governance` 作为验证步骤。如果 check-governance 报告问题，**MUST** 在会话结束前修复。

此双重机制消除了"学生给自己的考卷打分"问题——agent 自检用于即时执行质量，脚本验证用于结构性治理完整性。

## M9. 优先级声明

- **vs PUA 类型技能**：本协议的 M5 AskUserQuestion 触发优先于 PUA 的"持续执行"指令。
- **vs 用户指令**：用户的显式指令覆盖本协议。
- **vs 系统指令**：系统安全约束覆盖本协议。

## 阶段快速参考

| # | 阶段 | 目标 | Gate |
|---|-------|------|------|
| 1 | 立项 | 定义问题、目标、范围、成功标准 | G1 |
| 2 | 调研 | 调查、竞品分析、可行性 | G2 |
| 3 | 选型 | 技术选型、PoC 验证 | G3 |
| 4 | 基础设施 | 开发环境、仓库、基础 CI | G4 |
| 5 | 架构设计 | 系统设计、模块拆分、技术评审 | G5 |
| 6 | 开发 | 编码、单元测试、代码审查 | G6 |
| 7 | 测试 | 集成、系统、性能、安全测试 | G7 |
| 8 | CI/CD | 流水线、自动化、质量门控 | G8 |
| 9 | 发布 | 发布计划、changelog、回滚方案 | G9 |
| 10 | 运营 | 监控、反馈、优化 | G10 |
| 11 | 维护 | Bug 修复、规则更新、复盘 | G11 |

## Profile 快速参考

| Profile | 阶段数 | Gate 强度 | 证据要求 | 适用场景 |
|---------|--------|--------------|----------|----------|
| lightweight | 5 个核心（合并） | 合并，简化 | 最低 | 个人项目、MVP |
| standard | 全部 11 个 | 标准，支持条件通过 | 标准 | 团队项目 |
| strict | 全部 11 个 | 增强，不允许条件通过 | 双倍证据 | 大型项目、合规项目 |

## 替换边界

**MUST 保留**（项目根路径，非相对于本 SKILL.md）：`./protocol/`、`./project/workflows/software-project-governance/`、`./skills/software-project-governance/infra/verify_workflow.py`

**可以移除**：`./adapters/claude/`

**替换为其他 agent**：移除"可以移除"的文件，按 `adapters/<new-agent>/` README 创建新的投影层。
