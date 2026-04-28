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
| trigger_mode | enum | no | always-on | always-on / on-demand / silent-track | 默认触发模式（控制何时激活治理） |
| permission_mode | enum | no | default-confirm | maximum-autonomy / default-confirm | 操作权限模式（控制 agent 自主执行范围） |

## Execution Flow

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
  - "标准 (standard) — 推荐" — 11 个全 Gate + 20 列完整跟踪 + 已完成事项需证据。适合团队项目。
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
- 项目配置块：项目名称、Profile、触发模式、操作权限模式、工作流版本（初始化为当前安装版本）、当前阶段
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

**⚡ SELF-CHECK（在任何输出之前先问自己）**：
1. 我是否已经读了 `.governance/plan-tracker.md`？否 → **立即停止，先去读**
2. 我是否知道当前项目处于哪个阶段？否 → **你没读 plan-tracker，去读**
3. 上一 session 结束后是哪个阶段？是否有 carry-over 任务？不知道 → **去读 session-snapshot.md**

如果你已经回答了用户的任务请求但没有执行以上检查 → **停下来补执行。**

### Step 0: 确定双维度模式

读取 `.governance/plan-tracker.md` 的 `## 项目配置` 节，确认两个正交维度：

**维度一：触发模式（何时激活治理）**：
- **always-on** → 执行完整 Step 1~4。治理面板可正常输出。
- **on-demand** → 仅执行 Step 1。Step 2~4 仅在用户显式调用 governance 命令时执行。**MUST NOT** 主动输出治理面板。
- **silent-track** → 执行 Step 1~2，**MUST NOT** 输出治理面板/风险统计/任务进度表。仅在 Gate 失败或风险 escalation 到期时打断用户。

**维度二：操作权限模式（能做什么不打断）**：
- **maximum-autonomy（最高权限）**：除以下 2 类情况外，**一切操作自动执行**不打断用户——
  - (a) 关键决策（范围变更/架构决策/发布决策/风险接受/外部依赖变更/Profile或模式变更）
  - (b) 全部任务完成时（停下来确认下一步）
  - 自动执行范围包括：git commit + push（含 master/main）、本地命令执行、文件创建/编辑/删除、package 安装。**用户思考流不被无意义确认打断。**
- **default-confirm（默认确认）**：以下 4 类**危险操作**必须通过 AskUserQuestion 确认——
  - (a) 破坏性 git 操作：push --force、reset --hard、branch -D、删除远程分支
  - (b) 文件系统破坏：rm -rf、批量删除文件、覆盖重要配置
  - (c) 外部副作用：API 调用（非只读）、package 安装/卸载、数据库变更、环境变量修改
  - (d) 不可逆操作：squash 合并、rebase 变基、修改已推送的 commit
  - 常规操作（读文件/编辑文件/git commit 不带 push/git status/运行测试/创建文件）自动执行。

**治理开关——用户随时可以动态切换**：
会话中用户说以下任意一句 → 立即切换模式并更新 plan-tracker：
- "切换到最高权限模式" / "开启最高权限" / "maximum autonomy" → permission_mode = maximum-autonomy
- "切换到默认确认模式" / "开启确认模式" / "default confirm" → permission_mode = default-confirm
- "切换到始终在线" / "切换到按需调用" / "切换到静默跟踪" → trigger_mode 对应切换
- "当前模式" / "现在什么模式" → 输出当前 trigger_mode + permission_mode

**每次会话输出一句确认**：
> 🔍 Governance: {trigger_mode} × {permission_mode} | stage: {stage}, Gate {gate}: {status}, {risk_count} risk(s)

### Step 1: 读 plan-tracker + 跨会话恢复
读取 `.governance/plan-tracker.md`，确认：当前阶段、最近 Gate 结论、活跃风险数、进行中的 P0 任务。
**跨会话恢复**：读取 `.governance/session-snapshot.md`（如存在）——恢复 carry-over 任务、待确认决策、活跃风险。

**工作流脱轨检测**：检查 `最近复盘日期`——如果距今 > 7 天 AND 有新 commit 但 plan-tracker 无更新 → ⚠️ 提醒用户。

**版本变化自动检测**（用户更新插件后首次会话自动触发——不依赖任何命令）：
1. 对比 plan-tracker `工作流版本` 与当前安装版本（SKILL.md frontmatter `version`）
2. **IF** 当前 > 记录 → 自动输出：版本跨度 + CHANGELOG 摘要 + 需手动采纳项清单 + 自动生效项清单
3. 更新 plan-tracker `工作流版本` 为当前版本
4. **用户不需要记住任何命令——每次会话开始自动执行。**

### Step 2: 交叉验证（3 项强制检查）
1. **证据完整性**：plan-tracker 中"已完成"的任务，evidence-log 中是否有对应证据？
2. **Gate 一致性**：Gate 标记 passed 但无对应证据 = 不一致
3. **风险过期**：risk-log 中活跃风险超过 7 天未更新 = 过期
任一失败 → 列出差距 → AskUserQuestion 征求是否修复。

### Step 3: 阶段跳跃防护（MANDATORY）
**IF** 用户请求直接进入开发/测试/发布等后期阶段，但前置 Gate 均为 pending → **MUST** 警告用户跳过前置阶段的风险。用户可选择继续跳过，但决策记录到 decision-log。

### Step 4: 优先级确认
passed-with-conditions 遗留项或 P0 任务 → 优先处理。上次 session 未完成的 P0 任务 → 继续执行。

**没读 plan-tracker 就开始干活 = 流程违规。跳过 SELF-CHECK = 流程违规。跳过阶段跳跃防护 = 流程违规。**

### 干活前检查（每次收到任务时）
- 这个任务在计划跟踪表里吗？不在就先入账
- 做完后需要补什么证据？先想清楚
- 这个任务会不会影响别的阶段？影响就先记风险
- **用户视角三问**：①用户怎么获得变更（update/init/手动？）②用户怎么知道变更存在？③用户体验真的变了吗？——工作流是给人用的，不是自嗨

### 提问规则（强制）
**AskUserQuestion 是唯一合法的用户提问方式。** 禁止内联文字问"要不要继续""是否如何如何"。

**关键决策** — 无论何种 permission_mode，**永远**停下来用 AskUserQuestion：
- 范围变更 / 架构决策 / 发布决策 / 风险接受 / 外部依赖变更 / Profile或模式变更 / 阶段跳跃

**危险操作确认** — 仅 default-confirm 模式下停下来：
- 破坏性 git（push --force / reset --hard / branch -D）
- 文件系统破坏（rm -rf / 批量删除）
- 外部副作用（API/package/数据库/环境变量）
- 不可逆操作（squash/rebase/修改已推送commit）
- maximum-autonomy 模式下以上操作**自动执行不确认**。

**非关键决策** — 自动执行，不中断：
- 任务排序 / 证据格式 / git commit（不带 --force）/ git push（maximum-autonomy 下自动）/ 治理记录更新 / 微小实现选择 / Gate 自评（仅失败时告知）/ 文件编辑 / 运行测试

### 收工前检查（session 结束前）
1. 输出本轮完成事项摘要
2. 补证据到 `.governance/evidence-log.md`
3. 更新 plan-tracker 任务状态
4. 写入 `.governance/session-snapshot.md`（carry-over任务+待确认决策+活跃风险+下轮优先级）
5. **auto git commit + push**（maximum-autonomy 模式）或 **auto git commit**（default-confirm 模式——push 需确认）
6. 用 AskUserQuestion 确认下一步优先级

### 详细规则
完整行为协议见 `software-project-governance` skill（M0~M9 强制性规则、Gate 行为等）。以上 bootstrap 规则不依赖 SKILL.md 是否被加载——它们就在这里，每次会话必定生效。
```

### Step 8: 安装 git post-commit governance hook

任务间治理盲区是当前工作流最致命的漏洞——agent 在 commit 之间完全不受约束。post-commit hook 让每次 git commit 自动触发治理检查，agent 无法绕过。

- **IF** 项目根目录存在 `.git/` → 安装 hook：
  1. 复制 `scripts/post-commit-hook.sh` 到 `.git/hooks/post-commit`
  2. 验证 hook 文件存在且可执行
- **IF** `.git/hooks/post-commit` 已存在且非本工作流安装 → 备份为 `post-commit.bak`，再安装
- **IF** 项目不是 git 仓库 → 跳过，提醒用户"建议初始化 git 仓库以启用治理 hook"

Hook 行为：每次 `git commit` 后自动执行：
1. 从 commit message 提取 task ID
2. 检查 task ID 是否在 plan-tracker 中存在（不存在 = 任务未入账）
3. 检查 evidence-log 中是否有该 task 的证据（不存在 = 未补证据）
4. 输出 check-governance 摘要
5. Hook 不阻塞 commit——只报告，不拒绝

### Step 9: 输出确认
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
  {if hook_installed}✅ .git/hooks/post-commit — governance hook installed
  {if hook_skipped}⊘ .git/hooks/post-commit — skipped (not a git repo)

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
| INIT-ERR-004 | permission_mode 不在有效值范围 | "Invalid permission_mode '{value}'. Valid values are: maximum-autonomy, default-confirm." | 停止执行，不做任何文件修改 |

## Self-Validation

After execution, agent MUST verify:
- [ ] `.governance/` directory exists and is writable
- [ ] All 4 files (plan-tracker, evidence-log, decision-log, risk-log) exist with correct headers
- [ ] plan-tracker.md contains: project config block, Gate status table (11 rows), project overview table, empty task table header
- [ ] If project_type=existing, decision-log.md contains at least 1 decision record (DEC-001)
- [ ] Output confirmation contains all Required Fields from Output Format
- [ ] No file contains placeholder values for required toplevel182 fields
