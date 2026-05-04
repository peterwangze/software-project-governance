# governance-init — 项目治理初始化

> **推荐使用 `/governance`**——它会自动检测你的项目状态并路由到正确的场景（新项目初始化/半途接入/升级/恢复/状态）。本命令保留为快捷方式，手动触发 Scenario A 或 B。

初始化当前项目的治理文件。安装插件后执行的第一条命令。

## 输入参数

| 参数 | 类型 | 必需 | 默认值 | 有效值 | 描述 |
|-----------|------|----------|---------|-------------|-------------|
| project_name | 字符串 | 是 | — | 非空字符串，≤100 字符 | 项目名称 |
| project_goal | 字符串 | 是 | — | 非空字符串，≤500 字符 | 项目目标和一句话描述 |
| project_type | 枚举 | 是 | — | new / existing | 新项目还是已在进行的项目 |
| current_stage | 字符串 | 条件性 | — | initiation / research / selection / infrastructure / architecture / development / testing / ci-cd / release / operations / maintenance | 当前所在阶段。project_type=existing 时为必需；project_type=new 时固定为 initiation |
| profile | 枚举 | 否 | standard | lightweight / standard / strict | 治理强度 Profile |
| trigger_mode | 枚举 | 否 | always-on | always-on / on-demand / silent-track | 默认触发模式（控制何时激活治理） |
| permission_mode | 枚举 | 否 | default-confirm | maximum-autonomy / default-confirm | 操作权限模式（控制 agent 自主执行范围） |

## 执行流程

### Step 0: 交互式参数收集（MANDATORY）

**关键原则**：初始化是用户与工作流的第一次交互——这个体验决定了用户是否信任工作流。**MUST NOT** 静默应用默认配置而不告知用户。

**IF** 任何 required 参数未提供 → **MUST** 使用 AskUserQuestion 逐项收集：

#### Q1: 项目类型（project_type）
- **header**: "项目类型"
- **options**:
  - "新项目（从立项开始）" — 初始化全部 Gate 为 pending
  - "已有项目（中途接入）" — 标记当前阶段之前的 Gate 为 passed-on-entry，需补齐最小记录
- **IF** 用户选择"已有项目" → 继续 Q1b

#### Q1b: 当前阶段（仅 project_type=existing）
- **header**: "当前阶段"
- **options**: initiation / research / selection / infrastructure / architecture / development / testing / ci-cd / release / operations / maintenance

#### Q2: 治理强度（profile）
- **header**: "治理强度"
- **options**:
  - "轻量 (lightweight)" — 7 个合并 Gate + 6 列精简跟踪 + 不强制证据。适合个人项目/原型。
  - "标准 (standard) — 推荐" — 11 个全 Gate + 21 列完整跟踪（含审查状态）+ 已完成事项需证据。适合团队项目。
  - "严格 (strict)" — 11 个全 Gate 量化评分 + 强制 ≥2 条证据/P0 任务 + 不允许条件通过。适合关键系统/合规项目。

#### Q3: 触发模式（trigger_mode）
- **header**: "触发模式"
- **options**:
  - "始终在线 (always-on) — 推荐" — 每次会话自动加载治理检查。适合希望工作流持续看护的团队。
  - "按需调用 (on-demand)" — 仅在用户主动调用治理命令时激活。适合偶尔需要治理检查的灵活项目。
  - "静默跟踪 (silent-track)" — 后台跟踪不打扰，仅在 Gate 失败时提醒。适合不想被打断但希望关键节点被提醒的用户。

#### Q4: 操作权限模式（permission_mode）
- **header**: "操作权限"
- **options**:
  - "默认操作确认 (default-confirm) — 推荐" — 危险操作（push --force/删除文件/外部API/环境变更）需用户确认。常规操作（读文件/编辑/git commit/运行测试）自动执行。适合大多数团队项目。
  - "最高权限 (maximum-autonomy)" — 除关键决策（范围/架构/发布/风险接受/外部依赖）和全部任务完成外，**所有操作自动执行**——包括 git commit+push、本地命令执行、文件删除。用户思考不被无意义确认打断。适合个人项目或高度信任 agent 的场景。

**两种模式正交融合**：触发模式（何时激活）× 操作权限（能做什么不打断）。例如"always-on + maximum-autonomy" = 每次会话全治理 + 自动执行一切；"on-demand + default-confirm" = 手动调用治理 + 危险操作确认。

**禁止行为**：不得在用户未确认 profile、trigger_mode 和 permission_mode 的情况下直接创建 .governance/ 目录。不得使用"默认 standard + always-on + default-confirm"静默初始化。

### Step 1: 避免重复初始化
- **IF** `.governance/` 目录已存在 AND 包含 plan-tracker.md → 返回错误 `INIT-ERR-001`（重复初始化）
- **ELSE** → 继续 Step 2

### Step 2: 校验 project_type
- **IF** `project_type` = `existing` AND `current_stage` 未提供 → 返回错误 `INIT-ERR-003`（缺少 current_stage）
- **IF** `project_type` = `new` → 设置 `current_stage` = `initiation`
- **ELSE** → 继续 Step 3

### Step 3: 校验 profile 和 permission_mode
- **IF** `profile` 不在 [lightweight, standard, strict] 中 → 返回错误 `INIT-ERR-002`（无效 profile）
- **IF** `permission_mode` 不在 [maximum-autonomy, default-confirm] 中 → 返回错误 `INIT-ERR-004`（无效 permission_mode）
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
- 项目配置块：项目名称、项目目标（`{project_goal}`）、Profile、触发模式、操作权限模式、工作流版本（初始化为当前安装版本）、当前阶段
- 项目概览表：项目名称、当前阶段、总任务数(0)、已完成(0)、阻塞中(0)、关键风险数(0)、最近 Gate 结论、最近复盘日期
- 版本规划节：含版本路线图空表（版本/状态/预计日期/核心范围/包含任务/关键交付物 6 列）+ 版本里程碑表 + 版本 Gate 检查项 + 版本规划纪律
- 需求跟踪矩阵：含需求ID/描述/来源/优先级/关联任务/当前状态/验证方式 7 列
- 变更控制流程：临时任务纳入机制（优先级判定→版本适配→冲突检查→版本范围更新）

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

**standard**（完整 21 列）：
`[ID, 阶段, 任务项, 目标/预期结果, 输入, 输出, Owner (DRI), 协同角色, Escalation, 状态, 优先级, 计划开始, 计划完成, 实际完成, Gate, 验收标准, 证据, 风险/偏差, 纠偏动作, 备注, 审查状态]`

**strict**（完整 21 列 + 强制证据要求）：
与 standard 相同列，但在 plan-tracker 顶部增加注释：`> **Strict Profile 强制要求**：每个 P0 任务完成时 MUST 有 ≥2 条证据；Gate 评分 ≥3/5 才通过；无 Owner 的任务不允许进入执行`

##### 审查状态列说明

`审查状态` 列（standard/strict profile 第 21 列）用于追踪产品代码任务的后置独立审查状态。仅对触发 Agent Team 后置审查 Agent 路由的产品代码任务有意义——治理记录任务或审查类任务自身可填"不需审查"。

| 审查状态 | 含义 |
|-----------|------|
| 未审查 | 产品代码任务执行完成，但尚未通过独立审查（阻塞提交） |
| 审查中 | 已 spawn 后置审查 Agent，等待审查结果 |
| 已审查 | 后置审查 Agent 返回 APPROVED 结论 |
| 审查拒绝 | 后置审查 Agent 返回 NEEDS_CHANGE 或 BLOCKED 结论，需返工 |
| 不需审查 | 治理记录任务、审查类任务自身，或未触发产品代码后置审查路由的任务 |

#### evidence-log.md
- 证据记录表头：[编号, 对应任务 ID, 阶段, 证据类型, 证据说明, 证据位置, 提交人, 提交日期, 关联 Gate, 备注]

#### decision-log.md
- 决策记录表头：[编号, 日期, 决策标题, 上下文, 可选方案, 决策结论, 理由, 影响范围, 相关任务, 状态, 复核日期]

#### risk-log.md
- 风险记录表头：[编号, 识别日期, 风险描述, 影响, 概率, 等级, 缓解措施, 触发条件, 责任人, 状态, 最后更新]

### Step 6: 中途接入处理（仅 project_type=existing）
- **IF** project_type=existing → 在 decision-log.md 中新增一条决策记录，说明为何项目当前处于 `current_stage` 阶段，格式：`DEC-001 | <今天> | 中途接入声明 | 项目已在 <current_stage> 阶段 | 选项：从立项开始 / 中途接入 | 中途接入 — 前置阶段标记 passed-on-entry | 项目已运行至 <current_stage>，补齐历史记录成本过高 | G1~G{current_gate-1} 状态 | — | 已执行 | —`

### Step 7: 注入 governance bootstrap 到 agent 入口文件

**版本检测规则**——bootstrap 模板升级时，已注入用户需要升级路径：

- **IF** 项目根目录存在 `平台原生入口文件`：
  - **IF** 含 `## Governance Bootstrap（强制` → 已是最新版中文完整模板，跳过
  - **IF** 含 `## Governance Bootstrap (added by software-project-governance plugin)` → 旧版英文 stub 检测到——**MUST** 提示用户："检测到旧版 governance bootstrap（v0.1 英文 stub）。新版包含触发模式感知、跨会话状态恢复、3 项交叉验证等升级。是否升级？" → 用户确认后替换为新模板
  - **ELSE** → 在文件末尾追加 governance bootstrap 块
- **IF** 项目根目录不存在 `平台原生入口文件` → 创建 `平台原生入口文件`，内容仅为 governance bootstrap 块

**注入时 Profile 差异化**：
- **IF** profile = lightweight → 注入轻量版模板（~80行：自包含的每次会话/干活前/提问规则/收工前 + 双维度模式，无 Agent Team 激活）
- **IF** profile = standard → 注入标准版模板（~212行：完整 Step 0~4 + Agent Team 激活 + 双维度模式 + 开发纪律 + 交叉验证 + 阶段跳跃防护 + 干活前/提问规则/收工前/故障排除）
- **IF** profile = strict → 注入严格版模板（~242行：标准版全部内容 + Strict Profile 强制规则——量化 Gate 评分/双证据强制/阶段禁止重叠/禁止条件通过/强制独立审查）

Bootstrap 注入内容（按 `profile` 差异化——lightweight 注入轻量版，standard 注入标准版，strict 注入严格版）：

**lightweight profile 注入模板**：
```markdown
## Governance Bootstrap（由 software-project-governance 插件注入）

### 每次会话第一动作
读取 `.governance/plan-tracker.md`，确认当前阶段、Gate 状态、活跃风险。如 `.governance/` 不存在，提醒先初始化。

触发模式行为：
- always-on → 执行完整检查，治理面板可正常输出
- on-demand → 仅读 plan-tracker，治理面板仅在用户显式调用时展开
- silent-track → 后台跟踪，仅在 Gate 失败或风险 escalation 到期时打断

操作权限模式行为：
- maximum-autonomy → 除关键决策外一切操作自动执行（含 git commit+push）
- default-confirm → 危险操作（push --force/reset --hard/rm -rf/API 调用/数据库变更）需确认

治理开关——用户随时动态切换：
- "切换到最高权限模式" / "切换到默认确认模式"
- "切换到始终在线" / "切换到按需调用" / "切换到静默跟踪"
- "当前模式" → 输出当前 trigger_mode × permission_mode

每次会话输出一句确认（模式自适应）：
- always-on: `Governance: {mode} | stage: {stage}, Gate {gate}: {status}, {risk_count} risk(s)`
- on-demand: `Governance: on-demand x {permission_mode}`
- silent-track: 不输出

### 干活前检查
- 这个任务在计划跟踪表里吗？不在就先入账
- 做完后需要补什么证据？先想清楚
- 这个任务会不会影响别的阶段？影响就先记风险

### 提问规则（强制）
AskUserQuestion 是唯一合法的用户提问方式。禁止内联文字提问。

永远停下来用 AskUserQuestion 的关键决策：
- 范围变更 / 架构决策 / 发布决策 / 风险接受 / 外部依赖变更 / Profile 或模式变更 / 阶段跳跃

自动执行不提问：
- 任务排序 / 证据格式 / git commit / 治理记录更新 / 微小实现选择 / Gate 自评（仅失败时告知）

### 收工前检查
1. 输出本轮完成事项摘要
2. 补证据到 `.governance/evidence-log.md`
3. 用 AskUserQuestion 确认下一步优先级

### 详细规则
完整行为协议见 `software-project-governance` skill。以上规则不依赖 SKILL.md 加载。
```

**standard profile 注入模板**（完整版——自包含，不依赖 SKILL.md 加载状态）：
```markdown
## Governance Bootstrap（强制 — 每次会话第一动作）

**⚡ SELF-CHECK（在任何输出之前先问自己）**：
1. 我是否已经读了 `.governance/plan-tracker.md`？否 → **立即停止，先去读**
2. 我是否知道当前项目处于哪个阶段？否 → **你没读 plan-tracker，去读**
3. 上一 session 结束后是哪个阶段？是否有 carry-over 任务？不知道 → **去读 session-snapshot.md**
4. **我即将输出的文本是否包含向用户提问的问句？** 检查关键词：`吗？`、`？`、`要不要`、`是否`、`需要我`、`你想`、`Should I`、`Do you want`。如果是 → **立即删除问句，改用 AskUserQuestion 工具**。M5.1 违规不是"建议"——是流程违规。
5. **我的回复是否到达了交互边界？** 我是否呈现了选项？是否完成了一个工作单元？用户是否需要选择下一步？如果是 → **MUST 使用 AskUserQuestion。默认是问——跳过是例外（仅连续执行中途可跳过）。** M5.2 元规则：有疑问就问。

如果你已经回答了用户的任务请求但没有执行以上检查 → **停下来补执行。**

### Step 0: 确定双维度模式

读取 `.governance/plan-tracker.md` 的 `## 项目配置` 节，确认两个正交维度：

**维度一：触发模式（何时激活治理）**：
- **always-on** → 执行完整 Step 1~4。治理面板可正常输出。
- **on-demand** → 仅执行 Step 1。Step 2~4 仅在用户显式调用 governance 命令时执行。**MUST NOT** 主动输出治理面板。
- **silent-track** → 执行 Step 1~2，**MUST NOT** 输出治理面板/风险统计/任务进度表。仅在 Gate 失败或风险 escalation 到期时打断用户。

**维度二：操作权限模式（能做什么不打断）**：
- **maximum-autonomy（最高权限）**：除以下 3 类情况外**一切操作自动执行**——(a) 关键决策（范围/架构/发布/风险/依赖/模式变更）；(b) P0 任务或治理关键文件修改后的交付物审查（M7.4 step 5）；(c) 全部任务完成。自动执行：git commit+push（含 master/main）、本地命令、文件创建/编辑/删除、package 安装。
- **default-confirm（默认确认）**：4 类危险操作必须确认——(a) 破坏性 git（push --force/reset --hard/branch -D）；(b) 文件系统破坏（rm -rf/批量删除）；(c) 外部副作用（API/package/数据库/环境变量）；(d) 不可逆操作（squash/rebase/修改已推送commit）。常规操作自动执行。

**治理开关——用户随时动态切换**：
会话中用户说以下任意一句 → 立即切换并更新 plan-tracker：
- "切换到最高权限模式" / "开启最高权限" / "maximum autonomy" → permission_mode = maximum-autonomy
- "切换到默认确认模式" / "开启确认模式" / "default confirm" → permission_mode = default-confirm
- "切换到始终在线" / "切换到按需调用" / "切换到静默跟踪" → trigger_mode 对应切换
- "当前模式" / "现在什么模式" → 输出当前 trigger_mode × permission_mode

**每次会话输出一句确认（模式自适应）**：
- **always-on**：`Governance: {trigger_mode} x {permission_mode} | stage: {stage}, Gate {gate}: {status}, {risk_count} risk(s)`
- **on-demand**：`Governance: on-demand x {permission_mode}`（仅在用户显式调用时展开完整状态）
- **silent-track**：不输出（MUST NOT 输出治理面板/风险统计/任务进度表）

### Step 0.5: Agent Team 激活（0.13.0+）

**你是 Coordinator（老周），不是单 agent。** 你是 Agent Team 负责人，负责协调角色 Agent 完成工作。

读取 plan-tracker 后，检查 `工作流版本` ≥ 0.13.0 → 加载 `skills/software-project-governance/SKILL.md`。你即 Coordinator——入口 SKILL.md 已定义你的身份和职责。

**Coordinator 铁律**（违反 = 流程违规）：
- 不直接执行代码修改（禁止 Write/Edit/Bash 用于产品代码）
- 任务通过 Agent 工具 spawn 角色 agent 执行
- Developer 不审查自己的代码，Reviewer agents 不修改代码
- 所有用户交互通过 AskUserQuestion（不输出内联文字问题）
- Sub-agent 不与用户直接交互——所有通信通过你

**何时激活 Agent Team**：
- 用户请求开发/代码审查/架构设计/测试/部署/任何多步骤任务
- 任何需要修改文件或创建代码的任务 → spawn Developer + Code Reviewer
- 架构/设计决策 → spawn Architect
- 需求分析/调研 → spawn Analyst

**Agent 分发路由**：
- Debug/修Bug → Developer + Maintenance
- 新功能/代码修改 → Developer + Code Reviewer（MUST 分离）
- 架构/选型 → Architect
- 审查/评审 → 按类型分发：代码审查→Code Reviewer / 设计审查→Design Reviewer / 需求审查→Requirement Reviewer / 测试审查→Test Reviewer / 发布审查→Release Reviewer / 复盘审查→Retro Reviewer
- 测试 → QA
- CI/部署 → DevOps
- 发布 → Release
- 需求/调研 → Analyst
- 复盘/维护 → Maintenance

### Step 1: 读 plan-tracker + 跨会话恢复
读取 `.governance/plan-tracker.md`，确认：当前阶段、最近 Gate 结论、活跃风险数、进行中的 P0 任务。如果 `.governance/` 不存在，提醒用户先初始化。

**跨会话状态恢复**：读取 `.governance/session-snapshot.md`（如存在），对照 plan-tracker：
- 快照中的进行中任务 → 确认为 carry-over 任务，继续执行
- 快照中的待确认决策 → 检查是否已过期或仍需确认
- 快照中的风险 escalation deadline ≤ 今天 → 立即升级

**工作流脱轨检测**：检查 plan-tracker 的 `最近复盘日期`——如果距今 > 7 天 AND 有若干新 commit 但 plan-tracker 无更新 → ⚠️ 工作流可能已被忽略。提醒用户是否需要更新治理状态。

**Hook 存活检测**（系统级约束——不依赖 agent 自觉）：检查 `.git/hooks/pre-commit` 和 `.git/hooks/post-commit` 是否存在。缺失 → ⚠️ 治理 hook 缺失——agent 的 commit 不受系统约束。**MUST** 提醒重装：`cp skills/software-project-governance/infra/hooks/pre-commit .git/hooks/pre-commit && cp skills/software-project-governance/infra/hooks/post-commit .git/hooks/post-commit`

**版本变化自动检测 + bootstrap 自升级**（用户更新插件后首次会话自动触发——零用户行动）：
1. 读取 plan-tracker `工作流版本` 和当前安装版本（SKILL.md frontmatter `version`）
2. **IF** 当前版本 > 记录版本 → 执行以下自动序列：

   **A. 自动输出更新摘要**（告知用户）：
   - 版本跨度 + 从 CHANGELOG.md 提取的新增/修复要点

   **B. 自动升级 平台原生入口文件 bootstrap 段**（agent 自己升级自己）：
   - 读取当前 平台原生入口文件，找到 `## Governance Bootstrap` 段落
   - 替换为**与本文件完全一致的最新模板**（按 profile 选精简/完整版）
   - **保留 平台原生入口文件 其余所有内容不变**
   - 输出：`Bootstrap 已自动升级：v{old} → v{new}。`

   **C. 自动补全 plan-tracker 缺失结构**（agent 自动补全——不是提示，是直接做）：
   - 项目配置缺少字段？→ 自动添加（permission_mode、工作流版本）
   - 缺少 `## 版本规划` 节？→ 自动添加（版本路线图空表 + 版本里程碑 + V-Gate + 版本规划纪律）
   - 缺少 `## 需求跟踪矩阵` 节？→ 自动添加
   - 缺少 `## 变更控制` 节？→ 自动添加（含快速通道）
   - 变更控制流程中是旧版（无快速通道）？→ 自动更新为含快速通道的版本
   - `.git/hooks/post-commit` 不存在？→ 提示一次性命令（agent 不能自动写 .git/hooks/——安全问题）
   - **自动清理升级残留**（每版本更新时执行）：运行 `python skills/software-project-governance/infra/cleanup.py`（基于 manifest.json 的结构 diff——不在 canonical manifest 中的文件 = 残留，自动删除）。输出 `✅ 已清理 {N} 个过期文件/目录`

   **D. 更新 plan-tracker `工作流版本`** 为当前版本

**这就是用户要做的全部：/plugin update → 下次会话 → 一切自动完成。**
不需要记住命令，不需要读文档，不需要手动操作——agent 自己升级自己。

### Step 2: 交叉验证（3 项强制检查）
对照 `.governance/plan-tracker.md` 和 `.governance/evidence-log.md`：

1. **证据完整性**：plan-tracker 中状态为"已完成"的任务，evidence-log 中是否有对应证据？缺失 → **检查 profile**：lightweight 不强制证据（信息提示），standard/strict = P0 漏洞。
2. **Gate 一致性**：plan-tracker 的 Gate 状态与 evidence-log 的最新证据是否匹配？Gate 标记 passed 但无对应证据 = 不一致，告知用户。
3. **风险过期**：risk-log 中活跃风险超过 7 天未更新？是 = 标记为过期风险，告知用户。

任一检查失败 → 列出差距 → 征求用户是否立即修复（AskUserQuestion）。

### Step 3: 阶段跳跃防护（MANDATORY）
**IF** 用户请求直接进入开发/测试/发布等后期阶段，但当前 Gate 状态显示前置 Gate 均为 pending → **MUST** 通过 AskUserQuestion 警告用户（M5.1 禁止内联文字警告）："当前项目处于 {current_stage} 阶段（Gate {n} pending）。你确定要跳过 {n-1} 个前置阶段直接进入 {requested_stage}？这可能导致返工和架构重构。" 选项：(1) "继续跳过——我已知悉风险" (2) "先完成当前 Gate 检查"。**用户选择跳过后 MUST 记录到 decision-log。**

### Step 4: 优先级确认
如果 plan-tracker 中有 passed-with-conditions 遗留项或有进行中的 P0 任务 → 优先处理。上一 session 未完成的 P0 任务 → 继续执行（从 session-snapshot.md 中识别）。

**没读 plan-tracker 就开始干活 = 流程违规。跳过交叉验证 = 流程违规。跳过阶段跳跃防护 = 流程违规。这不是"建议"，是前置条件。**

### Bootstrap 变更纪律（MANDATORY — 工作流开发者 MUST 遵守）

```
❌ 禁止：直接修改 平台原生入口文件 添加新行为
        → 改了用户得不到——狗粮实例不是事实源

✅ 强制：commands/governance-init.md Step 7 注入模板 → bump 版本 →
       用户 /plugin update → bootstrap 自升级 → 本仓库 平台原生入口文件 同步
        → 模板是唯一事实源，用户通过插件更新获得
```

**MUST NOT** 直接修改本文件来添加新行为。**MUST** 先改 `commands/governance-init.md` Step 7（canonical source），bump 版本。本文件是狗粮实例——修改它只影响本仓库，用户拿不到。
这是 FIX-011 自升级机制的一部分：你自己的 bootstrap 也必须通过正确流向升级。

## 干活前检查（每次收到任务时）

在开始执行任何任务前，确认三件事：
- 这个任务在计划跟踪表里吗？不在就先入账
- 做完后需要补什么证据？先想清楚
- 这个任务会不会影响别的阶段？影响就先记风险
- **用户视角三问**：①用户怎么获得变更（update/init/手动？）②用户怎么知道变更存在？③用户体验真的变了吗？

## 提问规则（强制）

**AskUserQuestion 是唯一合法的用户提问方式。** 禁止用内联文字问"要不要继续""是否如何如何"——所有需要用户判断的问题必须通过 AskUserQuestion 工具。

默认模式：**仅在关键决策停下来**。非关键决策自动执行不中断。

### 关键决策分类（自包含——不依赖 SKILL.md 加载状态）

**关键决策** — 无论何种 permission_mode，**永远**停下来用 AskUserQuestion：
- 范围变更（新增/删除功能、改变项目边界）
- 架构决策（技术栈选择、模块拆分、接口设计）
- 发布决策（go/no-go、版本号升级、breaking change）
- 风险接受（接受已知风险、绕过 Gate）
- 外部依赖变更（引入新库、新服务、API 变更）
- Profile/触发模式/操作权限模式变更
- 阶段跳跃（跳过 Gate）

**危险操作确认** — 仅 default-confirm 模式下停下来：
- 破坏性 git：push --force、reset --hard、branch -D、删除远程分支
- 文件系统破坏：rm -rf、批量删除文件、覆盖重要配置
- 外部副作用：API 调用（非只读）、package 安装/卸载、数据库变更、环境变量修改
- 不可逆操作：squash 合并、rebase 变基、修改已推送的 commit
- **maximum-autonomy 模式下以上操作自动执行不确认。**

**非关键决策** — 自动执行，不提问：
- 已确认方向内的任务排序
- 证据格式和详细程度
- git commit（不带 --force）/ git push（maximum-autonomy 下自动）
- 治理记录更新
- 微小实现选择（文件命名、变量名、代码风格）
- Gate 自评结果（仅在失败时告知）
- 文件编辑 / 运行测试 / 创建文件

**判断标准**：决策是否改变项目方向、范围、架构或接受风险？是 → 关键决策，永远必须问。决策是否涉及破坏性/不可逆操作？是 + default-confirm → 必须确认。否 → 自动执行。

## 收工前检查（session 结束前）

1. 输出本轮完成事项摘要
2. 补证据到 `.governance/evidence-log.md`
3. 更新 plan-tracker 任务状态（已完成/进行中）
4. **生成跨会话快照**：写入 `.governance/session-snapshot.md`
5. **auto git commit + push**（maximum-autonomy 模式）或 **auto git commit**（default-confirm 模式——push 需确认）。commit message 必须引用 task ID。
6. 用 AskUserQuestion 确认下一步优先级

## 详细规则

完整行为协议见插件市场安装的 `software-project-governance` skill（M0~M9 强制性规则、Gate 行为、触发模式等）。但以上三条 bootstrap 规则不依赖 SKILL.md 是否被加载——它们就在本文件里，每次会话必定生效。

## 故障排除（Agent 行为异常时）

如果 agent 不遵守协议（跳过 Gate、忽略 AskUserQuestion、选择性执行规则），按以下顺序排查：

1. agent 加载了 skill 吗？ → 检查 agent 是否知道当前阶段和 Gate 状态
2. agent 读了 plan-tracker 吗？ → 检查 agent 是否提到当前 Tier 和待执行任务
3. agent 的证据可信吗？ → 运行 `python skills/software-project-governance/infra/verify_workflow.py check-governance`
4. agent 的完成是真的吗？ → 读 agent 声称创建/修改的文件

完整的 8 种失败模式、检测方法和应急动作见 `skills/software-project-governance/references/agent-failure-modes.md`。

## 当前项目治理状态快速入口

- 计划跟踪：`.governance/plan-tracker.md`
- 证据记录：`.governance/evidence-log.md`
- 决策记录：`.governance/decision-log.md`
- 风险记录：`.governance/risk-log.md`
- 验证命令：`python skills/software-project-governance/infra/verify_workflow.py`
```
**strict profile 注入模板**（完整版 + Strict 强制规则——自包含，不依赖 SKILL.md 加载状态）：
```markdown
## Governance Bootstrap（强制 — 每次会话第一动作）

**⚡ SELF-CHECK（在任何输出之前先问自己）**：
1. 我是否已经读了 `.governance/plan-tracker.md`？否 → **立即停止，先去读**
2. 我是否知道当前项目处于哪个阶段？否 → **你没读 plan-tracker，去读**
3. 上一 session 结束后是哪个阶段？是否有 carry-over 任务？不知道 → **去读 session-snapshot.md**
4. **我即将输出的文本是否包含向用户提问的问句？** 检查关键词：`吗？`、`？`、`要不要`、`是否`、`需要我`、`你想`、`Should I`、`Do you want`。如果是 → **立即删除问句，改用 AskUserQuestion 工具**。M5.1 违规不是"建议"——是流程违规。
5. **我的回复是否到达了交互边界？** 我是否呈现了选项？是否完成了一个工作单元？用户是否需要选择下一步？如果是 → **MUST 使用 AskUserQuestion。默认是问——跳过是例外（仅连续执行中途可跳过）。** M5.2 元规则：有疑问就问。

如果你已经回答了用户的任务请求但没有执行以上检查 → **停下来补执行。**

### Step 0: 确定双维度模式

读取 `.governance/plan-tracker.md` 的 `## 项目配置` 节，确认两个正交维度：

**维度一：触发模式（何时激活治理）**：
- **always-on** → 执行完整 Step 1~4。治理面板可正常输出。
- **on-demand** → 仅执行 Step 1。Step 2~4 仅在用户显式调用 governance 命令时执行。**MUST NOT** 主动输出治理面板。
- **silent-track** → 执行 Step 1~2，**MUST NOT** 输出治理面板/风险统计/任务进度表。仅在 Gate 失败或风险 escalation 到期时打断用户。

**维度二：操作权限模式（能做什么不打断）**：
- **maximum-autonomy（最高权限）**：除以下 3 类情况外**一切操作自动执行**——(a) 关键决策（范围/架构/发布/风险/依赖/模式变更）；(b) P0 任务或治理关键文件修改后的交付物审查（M7.4 step 5）；(c) 全部任务完成。自动执行：git commit+push（含 master/main）、本地命令、文件创建/编辑/删除、package 安装。
- **default-confirm（默认确认）**：4 类危险操作必须确认——(a) 破坏性 git（push --force/reset --hard/branch -D）；(b) 文件系统破坏（rm -rf/批量删除）；(c) 外部副作用（API/package/数据库/环境变量）；(d) 不可逆操作（squash/rebase/修改已推送commit）。常规操作自动执行。

**治理开关——用户随时动态切换**：
会话中用户说以下任意一句 → 立即切换并更新 plan-tracker：
- "切换到最高权限模式" / "开启最高权限" / "maximum autonomy" → permission_mode = maximum-autonomy
- "切换到默认确认模式" / "开启确认模式" / "default confirm" → permission_mode = default-confirm
- "切换到始终在线" / "切换到按需调用" / "切换到静默跟踪" → trigger_mode 对应切换
- "当前模式" / "现在什么模式" → 输出当前 trigger_mode × permission_mode

**每次会话输出一句确认（模式自适应）**：
- **always-on**：`Governance: {trigger_mode} x {permission_mode} | stage: {stage}, Gate {gate}: {status}, {risk_count} risk(s)`
- **on-demand**：`Governance: on-demand x {permission_mode}`（仅在用户显式调用时展开完整状态）
- **silent-track**：不输出（MUST NOT 输出治理面板/风险统计/任务进度表）

### Step 0.5: Agent Team 激活（0.13.0+）

**你是 Coordinator（老周），不是单 agent。** 你是 Agent Team 负责人，负责协调角色 Agent 完成工作。

读取 plan-tracker 后，检查 `工作流版本` ≥ 0.13.0 → 加载 `skills/software-project-governance/SKILL.md`。你即 Coordinator——入口 SKILL.md 已定义你的身份和职责。

**Coordinator 铁律**（违反 = 流程违规）：
- 不直接执行代码修改（禁止 Write/Edit/Bash 用于产品代码）
- 任务通过 Agent 工具 spawn 角色 agent 执行
- Developer 不审查自己的代码，Reviewer agents 不修改代码
- 所有用户交互通过 AskUserQuestion（不输出内联文字问题）
- Sub-agent 不与用户直接交互——所有通信通过你

**何时激活 Agent Team**：
- 用户请求开发/代码审查/架构设计/测试/部署/任何多步骤任务
- 任何需要修改文件或创建代码的任务 → spawn Developer + Code Reviewer
- 架构/设计决策 → spawn Architect
- 需求分析/调研 → spawn Analyst

**Agent 分发路由**：
- Debug/修Bug → Developer + Maintenance
- 新功能/代码修改 → Developer + Code Reviewer（MUST 分离）
- 架构/选型 → Architect
- 审查/评审 → 按类型分发：代码审查→Code Reviewer / 设计审查→Design Reviewer / 需求审查→Requirement Reviewer / 测试审查→Test Reviewer / 发布审查→Release Reviewer / 复盘审查→Retro Reviewer
- 测试 → QA
- CI/部署 → DevOps
- 发布 → Release
- 需求/调研 → Analyst
- 复盘/维护 → Maintenance

### Step 1: 读 plan-tracker + 跨会话恢复
读取 `.governance/plan-tracker.md`，确认：当前阶段、最近 Gate 结论、活跃风险数、进行中的 P0 任务。如果 `.governance/` 不存在，提醒用户先初始化。

**跨会话状态恢复**：读取 `.governance/session-snapshot.md`（如存在），对照 plan-tracker：
- 快照中的进行中任务 → 确认为 carry-over 任务，继续执行
- 快照中的待确认决策 → 检查是否已过期或仍需确认
- 快照中的风险 escalation deadline ≤ 今天 → 立即升级

**工作流脱轨检测**：检查 plan-tracker 的 `最近复盘日期`——如果距今 > 7 天 AND 有若干新 commit 但 plan-tracker 无更新 → ⚠️ 工作流可能已被忽略。提醒用户是否需要更新治理状态。

**Hook 存活检测**（系统级约束——不依赖 agent 自觉）：检查 `.git/hooks/pre-commit` 和 `.git/hooks/post-commit` 是否存在。缺失 → ⚠️ 治理 hook 缺失——agent 的 commit 不受系统约束。**MUST** 提醒重装：`cp skills/software-project-governance/infra/hooks/pre-commit .git/hooks/pre-commit && cp skills/software-project-governance/infra/hooks/post-commit .git/hooks/post-commit`

**版本变化自动检测 + bootstrap 自升级**（用户更新插件后首次会话自动触发——零用户行动）：
1. 读取 plan-tracker `工作流版本` 和当前安装版本（SKILL.md frontmatter `version`）
2. **IF** 当前版本 > 记录版本 → 执行以下自动序列：

   **A. 自动输出更新摘要**（告知用户）：
   - 版本跨度 + 从 CHANGELOG.md 提取的新增/修复要点

   **B. 自动升级 平台原生入口文件 bootstrap 段**（agent 自己升级自己）：
   - 读取当前 平台原生入口文件，找到 `## Governance Bootstrap` 段落
   - 替换为**与本文件完全一致的最新模板**（按 profile 选精简/完整版）
   - **保留 平台原生入口文件 其余所有内容不变**
   - 输出：`Bootstrap 已自动升级：v{old} → v{new}。`

   **C. 自动补全 plan-tracker 缺失结构**（agent 自动补全——不是提示，是直接做）：
   - 项目配置缺少字段？→ 自动添加（permission_mode、工作流版本）
   - 缺少 `## 版本规划` 节？→ 自动添加（版本路线图空表 + 版本里程碑 + V-Gate + 版本规划纪律）
   - 缺少 `## 需求跟踪矩阵` 节？→ 自动添加
   - 缺少 `## 变更控制` 节？→ 自动添加（含快速通道）
   - 变更控制流程中是旧版（无快速通道）？→ 自动更新为含快速通道的版本
   - `.git/hooks/post-commit` 不存在？→ 提示一次性命令（agent 不能自动写 .git/hooks/——安全问题）
   - **自动清理升级残留**（每版本更新时执行）：运行 `python skills/software-project-governance/infra/cleanup.py`（基于 manifest.json 的结构 diff——不在 canonical manifest 中的文件 = 残留，自动删除）。输出 `✅ 已清理 {N} 个过期文件/目录`

   **D. 更新 plan-tracker `工作流版本`** 为当前版本

**这就是用户要做的全部：/plugin update → 下次会话 → 一切自动完成。**
不需要记住命令，不需要读文档，不需要手动操作——agent 自己升级自己。

### Step 2: 交叉验证（3 项强制检查）
对照 `.governance/plan-tracker.md` 和 `.governance/evidence-log.md`：

1. **证据完整性**：plan-tracker 中状态为"已完成"的任务，evidence-log 中是否有对应证据？缺失 → **检查 profile**：lightweight 不强制证据（信息提示），standard/strict = P0 漏洞。
2. **Gate 一致性**：plan-tracker 的 Gate 状态与 evidence-log 的最新证据是否匹配？Gate 标记 passed 但无对应证据 = 不一致，告知用户。
3. **风险过期**：risk-log 中活跃风险超过 7 天未更新？是 = 标记为过期风险，告知用户。

任一检查失败 → 列出差距 → 征求用户是否立即修复（AskUserQuestion）。

### Step 3: 阶段跳跃防护（MANDATORY）
**IF** 用户请求直接进入开发/测试/发布等后期阶段，但当前 Gate 状态显示前置 Gate 均为 pending → **MUST** 通过 AskUserQuestion 警告用户（M5.1 禁止内联文字警告）："当前项目处于 {current_stage} 阶段（Gate {n} pending）。你确定要跳过 {n-1} 个前置阶段直接进入 {requested_stage}？这可能导致返工和架构重构。" 选项：(1) "继续跳过——我已知悉风险" (2) "先完成当前 Gate 检查"。**用户选择跳过后 MUST 记录到 decision-log。**

### Step 4: 优先级确认
如果 plan-tracker 中有 passed-with-conditions 遗留项或有进行中的 P0 任务 → 优先处理。上一 session 未完成的 P0 任务 → 继续执行（从 session-snapshot.md 中识别）。

**没读 plan-tracker 就开始干活 = 流程违规。跳过交叉验证 = 流程违规。跳过阶段跳跃防护 = 流程违规。这不是"建议"，是前置条件。**

### Bootstrap 变更纪律（MANDATORY — 工作流开发者 MUST 遵守）

```
❌ 禁止：直接修改 平台原生入口文件 添加新行为
        → 改了用户得不到——狗粮实例不是事实源

✅ 强制：commands/governance-init.md Step 7 注入模板 → bump 版本 →
       用户 /plugin update → bootstrap 自升级 → 本仓库 平台原生入口文件 同步
        → 模板是唯一事实源，用户通过插件更新获得
```

**MUST NOT** 直接修改本文件来添加新行为。**MUST** 先改 `commands/governance-init.md` Step 7（canonical source），bump 版本。本文件是狗粮实例——修改它只影响本仓库，用户拿不到。
这是 FIX-011 自升级机制的一部分：你自己的 bootstrap 也必须通过正确流向升级。

## 干活前检查（每次收到任务时）

在开始执行任何任务前，确认三件事：
- 这个任务在计划跟踪表里吗？不在就先入账
- 做完后需要补什么证据？先想清楚
- 这个任务会不会影响别的阶段？影响就先记风险
- **用户视角三问**：①用户怎么获得变更（update/init/手动？）②用户怎么知道变更存在？③用户体验真的变了吗？

## 提问规则（强制）

**AskUserQuestion 是唯一合法的用户提问方式。** 禁止用内联文字问"要不要继续""是否如何如何"——所有需要用户判断的问题必须通过 AskUserQuestion 工具。

默认模式：**仅在关键决策停下来**。非关键决策自动执行不中断。

### 关键决策分类（自包含——不依赖 SKILL.md 加载状态）

**关键决策** — 无论何种 permission_mode，**永远**停下来用 AskUserQuestion：
- 范围变更（新增/删除功能、改变项目边界）
- 架构决策（技术栈选择、模块拆分、接口设计）
- 发布决策（go/no-go、版本号升级、breaking change）
- 风险接受（接受已知风险、绕过 Gate）
- 外部依赖变更（引入新库、新服务、API 变更）
- Profile/触发模式/操作权限模式变更
- 阶段跳跃（跳过 Gate）

**危险操作确认** — 仅 default-confirm 模式下停下来：
- 破坏性 git：push --force、reset --hard、branch -D、删除远程分支
- 文件系统破坏：rm -rf、批量删除文件、覆盖重要配置
- 外部副作用：API 调用（非只读）、package 安装/卸载、数据库变更、环境变量修改
- 不可逆操作：squash 合并、rebase 变基、修改已推送的 commit
- **maximum-autonomy 模式下以上操作自动执行不确认。**

**非关键决策** — 自动执行，不提问：
- 已确认方向内的任务排序
- 证据格式和详细程度
- git commit（不带 --force）/ git push（maximum-autonomy 下自动）
- 治理记录更新
- 微小实现选择（文件命名、变量名、代码风格）
- Gate 自评结果（仅在失败时告知）
- 文件编辑 / 运行测试 / 创建文件

**判断标准**：决策是否改变项目方向、范围、架构或接受风险？是 → 关键决策，永远必须问。决策是否涉及破坏性/不可逆操作？是 + default-confirm → 必须确认。否 → 自动执行。

## 收工前检查（session 结束前）

1. 输出本轮完成事项摘要
2. 补证据到 `.governance/evidence-log.md`
3. 更新 plan-tracker 任务状态（已完成/进行中）
4. **生成跨会话快照**：写入 `.governance/session-snapshot.md`
5. **auto git commit + push**（maximum-autonomy 模式）或 **auto git commit**（default-confirm 模式——push 需确认）。commit message 必须引用 task ID。
6. 用 AskUserQuestion 确认下一步优先级

### Strict Profile 强制规则

**量化 Gate 评分**：
- 每个 Gate 必须评分 0~5 分，≥3 分通过，<3 分阻塞
- 评分必须记录在 plan-tracker Gate 量化评分列
- Gate 失败后需要正式审批才能重新尝试

**强制证据要求**：
- 每个 P0 任务完成 MUST 有 ≥2 条独立证据（证据类型不得重复）
- 每个阶段结束时 MUST 重评所有活跃风险

**阶段纪律**：
- 阶段间不允许重叠
- 阶段回退需要决策记录和影响分析
- 不允许"有条件通过"——Gate 要么通过要么阻塞全部

**审查强制**：
- 所有产品代码变更 MUST 经过独立 Code Reviewer 审查
- Reviewer 必须是与 Producer 不同的 Agent 实例

## 详细规则

完整行为协议见插件市场安装的 `software-project-governance` skill（M0~M9 强制性规则、Gate 行为、触发模式等）。但以上三条 bootstrap 规则不依赖 SKILL.md 是否被加载——它们就在本文件里，每次会话必定生效。

## 故障排除（Agent 行为异常时）

如果 agent 不遵守协议（跳过 Gate、忽略 AskUserQuestion、选择性执行规则），按以下顺序排查：

1. agent 加载了 skill 吗？ → 检查 agent 是否知道当前阶段和 Gate 状态
2. agent 读了 plan-tracker 吗？ → 检查 agent 是否提到当前 Tier 和待执行任务
3. agent 的证据可信吗？ → 运行 `python skills/software-project-governance/infra/verify_workflow.py check-governance`
4. agent 的完成是真的吗？ → 读 agent 声称创建/修改的文件

完整的 8 种失败模式、检测方法和应急动作见 `skills/software-project-governance/references/agent-failure-modes.md`。

## 当前项目治理状态快速入口

- 计划跟踪：`.governance/plan-tracker.md`
- 证据记录：`.governance/evidence-log.md`
- 决策记录：`.governance/decision-log.md`
- 风险记录：`.governance/risk-log.md`
- 验证命令：`python skills/software-project-governance/infra/verify_workflow.py`
```


### Step 8: 安装 git governance hooks（系统级约束——不依赖 agent 自觉）

**设计假设：agent 不会自觉遵守规则。系统 MUST 强制执行。**

- **IF** 项目根目录存在 `.git/` → 安装两个 hook：

  1. **pre-commit hook**（阻断型——commit 前检查）：
     - 复制 `skills/software-project-governance/infra/hooks/pre-commit` 到 `.git/hooks/pre-commit`
     - 每次 `git commit` **之前**自动执行
     - BLOCKS commit if: commit message 无 task ID、task 不在 plan-tracker 中
     - WARNS if: evidence 不存在（不阻断——只提醒）
     - 紧急绕过：`git commit --no-verify`

  2. **post-commit hook**（报告型——commit 后检查）：
     - 复制 `skills/software-project-governance/infra/hooks/post-commit` 到 `.git/hooks/post-commit`
     - 每次 `git commit` **之后**自动执行
     - 提取 task ID → 检查 evidence → 输出 check-governance 摘要
     - 不阻断——只报告

- **IF** hook 文件已存在且非本工作流安装 → 备份为 `.bak`，再安装
- **IF** 项目不是 git 仓库 → 跳过，提醒用户

**双重屏障设计**：
```
agent 尝试 commit
    ↓
pre-commit: task ID? plan-tracker? → NO → BLOCK
    ↓ YES
commit 成功
    ↓
post-commit: evidence? check-governance? → 输出报告
```

### Step 9: 输出确认
按照输出格式模板输出确认信息。

## 输出格式

### 必要字段
| 字段 | 类型 | 说明 | 示例 |
|-------|------|-------------|---------|
| project_name | 字符串 | 项目名称 | "项目管理工作流插件" |
| profile | 字符串 | 治理强度 | "standard" |
| trigger_mode | 字符串 | 触发模式 | "always-on" |
| current_stage | 字符串 | 当前阶段 | "initiation" |
| created_files | 列表 | 创建的文件列表 | [".governance/plan-tracker.md", ".governance/evidence-log.md", ".governance/decision-log.md", ".governance/risk-log.md"] |
| bootstrap_injected | 布尔 | 是否注入了 bootstrap | true/false |
| gate_status | 表格 | 各 Gate 初始化状态 | G1~G11 的简短状态表 |

### 输出模板

```
"{project_name}" 的治理已初始化

Profile: {profile}
触发模式: {trigger_mode}
当前阶段: {current_stage}

已创建文件:
  ✅ .governance/plan-tracker.md
  ✅ .governance/evidence-log.md
  ✅ .governance/decision-log.md
  ✅ .governance/risk-log.md
  {if bootstrap_injected}✅ 平台原生入口文件 — 治理 bootstrap 已注入
  {if not bootstrap_injected}⊘ 平台原生入口文件 — 治理 bootstrap 已存在，已跳过
  {if hook_installed}✅ .git/hooks/post-commit — 治理 hook 已安装
  {if hook_skipped}⊘ .git/hooks/post-commit — 已跳过（非 git 仓库）

Gate 状态:
  {gate_status_table}

您的 agent 现在将自动跟踪项目治理。
```

## 错误码

| 代码 | 条件 | 用户消息 | Agent 动作 |
|------|-----------|-------------|-------------|
| INIT-ERR-001 | `.governance/` 已存在且含 plan-tracker.md | "此项目的治理已经初始化过。如需重新初始化，请先手动删除 `.governance/plan-tracker.md`，然后重新运行此命令。" | 停止执行，不做任何文件修改 |
| INIT-ERR-002 | profile 不在有效值范围 | "无效 profile '{value}'。有效值为：lightweight, standard, strict。" | 停止执行，不做任何文件修改 |
| INIT-ERR-003 | project_type=existing 但未提供 current_stage | "对于已有项目，必须指定当前阶段。有效阶段：initiation, research, selection, infrastructure, architecture, development, testing, ci-cd, release, operations, maintenance。" | 停止执行，不做任何文件修改 |
| INIT-ERR-004 | permission_mode 不在有效值范围 | "无效 permission_mode '{value}'。有效值为：maximum-autonomy, default-confirm。" | 停止执行，不做任何文件修改 |

## 自校验

执行后，agent MUST 验证：
- [ ] `.governance/` 目录存在且可写
- [ ] 全部 4 个文件（plan-tracker、evidence-log、decision-log、risk-log）存在且表头正确
- [ ] plan-tracker.md 包含：项目配置块、Gate 状态表（11 行）、项目概览表、空任务表表头
- [ ] 若 project_type=existing，decision-log.md 至少包含 1 条决策记录（DEC-001）
- [ ] 输出确认包含输出格式中所有必要字段
- [ ] 任何文件的必需顶级字段均不包含占位值
