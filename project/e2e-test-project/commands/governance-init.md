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

### Step 0.5: 确定 `<plugin_home>`（FIX-238.1 平台注入 + vendor 兜底）

本命令及后续所有 `python <plugin_home>/infra/...` 调用先确定 `<plugin_home>`（消除占位符歧义）：

- **平台注入变量（首选）**：
  - Claude Code：`$CLAUDE_PLUGIN_ROOT`（插件安装根；`<plugin_home>` = `$CLAUDE_PLUGIN_ROOT/skills/software-project-governance`）
  - Codex：从 system context 中 `software-project-governance` skill 的 `file:` 绝对路径解析（`<plugin_install_root>/skills/software-project-governance/SKILL.md` → `<plugin_home>` = 该 `skills/software-project-governance` 目录）
  - 通用环境变量：`SOFTWARE_PROJECT_GOVERNANCE_HOME` / `SPG_HOME`（已安装宿主显式指定）
- **vendor 引导脚本兜底（宿主无 AGENTS.md/CLAUDE.md 时仍可定位）**：`<plugin_home>/infra/bootstrap.sh`（POSIX）与 `<plugin_home>/infra/bootstrap.cmd`（Windows）随插件发布分发，定位 resolve_entry.py → 运行 `--json` → 输出 envelope：
  - POSIX：`bash "<plugin_home>/infra/bootstrap.sh"`
  - PowerShell：`& "<plugin_home>\infra\bootstrap.cmd"`（等价地 `python "<plugin_home>/infra/resolve_entry.py" --json`）
- **超时兜底（FIX-238.3）**：resolve_entry 调用具备超时包装（`SPG_RESOLVE_TIMEOUT`，默认 15s，非法回退默认）；超时/缺失输出分类诊断（file-not-found / timeout / python-missing / store-stub）且 exit 非 0，fail-closed 不静默。

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

### Step 5.5: 创建归档目录结构
- 创建 `.governance/archive/` 目录
- 创建子目录: `archive/tasks/`, `archive/evidence/`, `archive/decisions/`, `archive/risks/`
- 每个子目录中创建 `.gitkeep` 文件（空文件，确保目录可被 git 跟踪）
- **不**创建 `archive/index.md`——索引在首次归档时由 archive.py 自动生成

### Step 6: 中途接入处理（仅 project_type=existing）
- **IF** project_type=existing → 在 decision-log.md 中新增一条决策记录，说明为何项目当前处于 `current_stage` 阶段，格式：`DEC-001 | <今天> | 中途接入声明 | 项目已在 <current_stage> 阶段 | 选项：从立项开始 / 中途接入 | 中途接入 — 前置阶段标记 passed-on-entry | 项目已运行至 <current_stage>，补齐历史记录成本过高 | G1~G{current_gate-1} 状态 | — | 已执行 | —`

### Step 7: 注入 governance bootstrap 到 agent 入口文件

**版本检测规则（FIX-238.2——@bootstrap-version 陈旧标记优先）**——bootstrap 模板升级时，已注入用户需要升级路径：

- **陈旧判定**：入口文件引导段 `@bootstrap-version` 头 < SKILL.md frontmatter `active_version`（缺失头 = pre-0.73.0，视为陈旧）
- **标陈旧且更高版本 SKILL.md 已安装** → 先升级 bootstrap 段（写回最新模板，保留入口文件其余内容不变），再继续后续引导
- **未检测到更高版本** → 输出确定性错误 + `/plugin update` 指引（不无限 fallback）
- **版本比较 fail-closed**：无法确定新版本（版本串不可解析）→ 不升级，输出指引

- **IF** 项目根目录存在 `平台原生入口文件`：
  - **IF** 含 `## Governance Bootstrap（强制` → 已是最新版中文完整模板，跳过
  - **IF** 含 `## Governance Bootstrap (added by software-project-governance plugin)` → 旧版英文 stub 检测到——**MUST** 提示用户："检测到旧版 governance bootstrap（v0.1 英文 stub）。新版包含触发模式感知、跨会话状态恢复、3 项交叉验证等升级。是否升级？" → 用户确认后替换为新模板
  - **ELSE** → 在文件末尾追加 governance bootstrap 块
- **IF** 项目根目录不存在 `平台原生入口文件` → 创建 `平台原生入口文件`，内容仅为 governance bootstrap 块

**注入时 Profile 差异化**：
- **IF** profile = lightweight → 注入轻量版模板（自包含的每次会话/干活前/提问规则/收工前 + 双维度模式，无 Agent Team 激活）
- **IF** profile = standard → 注入标准版模板（完整 Step 0~4 + Agent Team 激活 + 双维度模式 + 开发纪律 + 交叉验证 + 阶段跳跃防护 + 干活前/提问规则/收工前/故障排除）
- **IF** profile = strict → 注入严格版模板（= standard 共享基座 + Strict Profile 强制规则差异段，渲染时由 `sync_entry_projection.extract_canonical_templates` 组合——FEAT-041 单次维护；量化 Gate 评分/双证据强制/阶段禁止重叠/禁止条件通过/强制独立审查）
- **行数不在此处承诺**：以 `sync_entry_projection.extract_canonical_templates` 的实测输出为准（`check-entry-bootstrap-sync` 报告逐 profile 字节/行数，`check-injection-budget` 报告逐 profile token——两处硬断言钉住，陈旧行数估计不再维护）。

Bootstrap 注入内容（按 `profile` 差异化——lightweight 注入轻量版，standard 注入标准版，strict 注入严格版）：

**lightweight profile 注入模板**：
```markdown
## Governance Bootstrap（由 software-project-governance 插件注入）

> @bootstrap-version: 0.89.0（模板最低引导版本——低于 SKILL frontmatter active_version 即陈旧，先升级本段再继续）

### 每次会话第一动作
读取 `.governance/plan-tracker.md`，确认当前阶段、Gate 状态、活跃风险。如 `.governance/` 不存在，提醒先初始化。

首次交互前置（FEAT-034）：热数据可经单命令快路径获取——`python <plugin_home>/infra/verify_workflow.py governance-bootstrap --format json`（只读聚合；不可用时回退直接读取 plan-tracker）；快路径就绪后立即向用户呈现最小状态行并进入首次 AskUserQuestion 交互，深检后置为用户选择后按需执行（推进类动作前 MUST 补齐）；健康面未检查时（`health.state="deferred"`）显示「待检查」而非通过。

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

**行为灰度开关（FEAT-040——legacy 回退通道，只回退性能行为）**：`GOVERNANCE_LEGACY_BEHAVIOR=1`（会话级）或 plan-tracker `## 项目配置` 的 `- **behavior_profile**: legacy`（项目级；env 优先；默认 `modern`）→ 快路径→六段读取、首次交互前置→深检先行、≤8 字段视图→完整契约、Scenario 按需→预加载。**安全语义不回退（硬边界）**：升级确认门（FEAT-035）／异常不隐藏／fail-closed／真实环境防护／复审必达——legacy 下全部照常生效。生效形态以 `governance-bootstrap` 的 `behavior` 面为准（`profile`/`source`）。

每次会话输出一句确认（模式自适应）：
- always-on: `Governance: {mode} | stage: {stage}, Gate {gate}: {status}, {risk_count} risk(s)`
- on-demand: `Governance: on-demand x {permission_mode}`
- silent-track: 不输出

**治理数据归档**（版本 bump / 发布收尾后触发；归档写操作 AskUserQuestion 确认后执行——FEAT-035）:
运行 `python <plugin_home>/infra/archive.py migrate --auto --dry-run` 检查持续归档触发器（`<plugin_home>` 来自 resolve_entry.py）:
- 首次迁移: archive/index.md 不存在 AND plan-tracker > 80KB AND ≥2 已发布版本
- 发布强制: 新版本标记已发布后，除最新已发布版本外仍有热文件历史 task
- task 增量: 可归档 completed task 达到阈值
- 90 天兜底: 长期未归档且仍有可归档历史数据
→ dry-run 显示需要归档: 呈现 dry-run 报告并通过 AskUserQuestion 确认后，运行 `python <plugin_home>/infra/archive.py migrate --auto`，再运行 `python <plugin_home>/infra/verify_workflow.py check-archive-integrity`
→ 归档完整性失败: 阻断发布完成 / Gate 完成

- IF .governance/archive/index.md 存在 → 已归档条目可通过索引查询
- 交叉验证时: 归档文件中的证据 = 有效证据——不可误判为缺失

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

- 完整治理交互（状态/恢复/升级/异常修复）→ 使用 /governance 命令

### 详细规则
完整行为协议见 `software-project-governance` skill。以上规则不依赖 SKILL.md 加载。
```

**standard profile 注入模板**（共享基座——standard/strict 单次维护；契约 v2：触发器行内 + 明细按需，DEC-218/FEAT-041；strict 渲染 = 本基座 + strict 差异段末尾追加）：
```markdown
## Governance Bootstrap（强制 — 每次会话第一动作）

> @bootstrap-version: 0.89.0（模板最低引导版本——低于 SKILL frontmatter active_version 即陈旧，先升级本段再继续）
>
> 契约 v2（FEAT-041/DEC-218）：触发器行内 + 明细按需——「§Bx」= `skills/software-project-governance/SKILL.md`「Bootstrap 规程明细」小节（skill 层按需加载，迁移零丢失）；本模板规则不依赖 skill 加载。

**⚡ SELF-CHECK（输出前自问——硬约束行内；全文 §B0）**：
1-3. 读了 `.governance/plan-tracker.md`？知道阶段/Gate/模式？carry-over（session-snapshot）？任一未知 → **立即停止，先读再输出**。
4. **我即将输出的文本是否包含向用户提问的问句？**（吗？/？/要不要/是否…）→ **立即删除，改用 AskUserQuestion**（M5.1 = 流程违规）。
5. **到达交互边界**（呈现选项/完成工作单元/需用户选择）？→ **MUST AskUserQuestion**（默认是问，跳过是例外）。
6. **即将写入的内容是否有事实依据？**无文件/命令/测试/日志/用户输入支撑 → 标 `BLOCKED`/`待验证`，禁止编造。

### Step 0: 确定双维度模式（明细 §B0）
读 plan-tracker `## 项目配置` 确定两正交维度。**触发模式**：always-on = 完整 Step 1~4+治理面板；on-demand = 仅 Step 1（Step 2~4 显式调用时；MUST NOT 主动输出面板）；silent-track = Step 1~2（MUST NOT 输出面板，仅 Gate 失败或风险 escalation 到期打断）。**权限模式**：maximum-autonomy = 除关键决策（范围/架构/发布/风险/依赖/模式变更）、P0/治理关键文件交付物审查、全部任务完成外一切自动（含 git commit+push）；default-confirm = 破坏性 git/文件系统破坏/外部副作用/不可逆操作四类须确认。**治理开关**：用户说"最高权限/确认模式/始终在线/按需/静默跟踪/当前模式" → 立即切换并更新 plan-tracker。**行为灰度开关（FEAT-040）**：`GOVERNANCE_LEGACY_BEHAVIOR=1` 或 plan-tracker `behavior_profile: legacy`（env 优先；默认 modern；非法值报 `behavior.invalid`）→ 只回退性能行为；**安全语义不回退**：升级确认门/异常不隐藏/fail-closed（`resolved_root_ok == false` 即停）/真实环境防护/复审必达。边界表：SKILL.md「行为灰度开关」。**每次会话输出一句确认**：always-on → `Governance: {trigger_mode} x {permission_mode} | stage: {stage}, Gate {gate}: {status}, {risk_count} risk(s)`（on-demand/silent-track 变体 §B0）。

### Step 0.5: Agent Team 激活（0.13.0+）
**你是 Coordinator，不是单 agent。**plan-tracker `工作流版本` ≥ 0.13.0 → 加载 `skills/software-project-governance/SKILL.md` 即 Coordinator 身份。**铁律**（违反 = 流程违规）：不直接修改产品代码；任务经 Agent 工具 spawn 角色 agent；Developer 不自审、Reviewer 不改码；用户交互只经 AskUserQuestion；sub-agent 不接触用户；spawn 前查 `.governance/agent-locks.json` 并写锁，完成后释放。何时激活/分发路由：SKILL.md「Agent 分发路由」。

### Step 1: 读 plan-tracker + 跨会话恢复（明细：§B1）
1. **快路径**：`python <plugin_home>/infra/verify_workflow.py governance-bootstrap --format json` 取热数据（只读聚合 ≤8KB）；聚合命令不可用 → **fallback 六段读取** plan-tracker 热数据段：a 项目配置 / b Gate 状态跟踪 / c 项目总览 / d 当前活跃事项 / e 活跃版本 task 表 / f 活跃依赖链（g~j 按需；缺面展开规则 §B1）。
2. **首次交互前置（FEAT-034）**：热数据就绪 → MUST AskUserQuestion 首次交互（最小状态行：模式确认句 + 阶段/Gate 摘要 + carry-over/风险计数；deferred 健康位显示「待检查」）；深检后置 ≠ 可选——推进类动作前 MUST 补齐；升级待处理确认随本次首次交互 ask 一并呈现（Scenario C 同口径）。
3. **Execution Packet**：读 `.governance/execution-packets.json` 当前 TASK_ID 短包约束执行边界；活跃 P0/P1 缺包 → `execution-packet --write` 后再读（Check 18c 阻断缺包）。
4. **恢复与感知**：session-snapshot 进行中→carry-over；待确认决策→查时效；风险 escalation deadline ≤ 今天→立即升级；`archive/index.md` 存在→归档证据 = 有效证据；脱轨（复盘 >7 天 + 新 commit 无更新）→提醒；`.git/hooks/` 三 hook 缺失→提示重装（命令 §B1）。
5. **版本变化检测 + bootstrap 升级（FEAT-035 确认门）**：安装版本 > 记录版本 → **呈现升级待处理**（AskUserQuestion 升级摘要：版本跨度 + CHANGELOG 要点 + 写操作清单 + 回滚方式；默认「执行升级（推荐）」）——**用户未响应前零写操作**；确认后执行 A~E 序列（§B1 全文：B 升级入口段——深检前置，版本升级写序列属推进类动作（DEC-207② P2-1 / M5.5 条 3）；C 结构补全（`.git/hooks/post-commit` 不存在→提示安装；插件残留清理删除面——cleanup.py --dry-run 先行，确认后再执行 `python <plugin_home>/infra/cleanup.py`）→ **D. 更新 plan-tracker `工作流版本`** → E 持续归档触发检测与执行（dry-run 先行；归档完整性失败 → 发布/版本 bump 收尾场景 MUST 阻断完成；无可归档数据 → 跳过））。

**用户要做的仍然只有：/plugin update → 下次会话。** 检测到版本差 → 呈现升级待处理（默认执行升级（推荐）），用户未响应前零写操作。

### Step 2: 交叉验证（3 项强制检查——后置深检；明细 §B2）
时序：首次交互后按需执行；推进类动作（发布/版本 bump/治理写回/恢复遗留任务的实际修改）前 MUST 先完成。三项：①证据完整性（已完成任务查 evidence-log，缺则查 archive/index.md——归档证据=有效证据）②Gate 一致性（passed 无对应证据 = 不一致）③风险过期（活跃风险 >7 天未更新）。任一失败 → 列出差距 → AskUserQuestion 征求修复。

### Step 3: 阶段跳跃防护（MANDATORY）
**IF** 用户请求直接进入开发/测试/发布等后期阶段，但前置 Gate 均为 pending → **MUST** AskUserQuestion 警告（M5.1 禁止内联警告）："当前项目处于 {current_stage} 阶段（Gate {n} pending）。你确定要跳过 {n-1} 个前置阶段直接进入 {requested_stage}？这可能导致返工和架构重构。" 选项：(1) "继续跳过——我已知悉风险" (2) "先完成当前 Gate 检查"。**跳过后 MUST 记录到 decision-log。**

### Step 4: 优先级确认
passed-with-conditions 遗留项或进行中 P0 → 优先处理；上一 session 未完成 P0 → 继续执行（session-snapshot 识别）。

**没读 plan-tracker 就开始干活 = 流程违规。跳过交叉验证 = 流程违规。跳过阶段跳跃防护 = 流程违规。这不是"建议"，是前置条件。**

### Bootstrap 变更纪律（MANDATORY — 工作流开发者 MUST 遵守）
❌ 直接修改 平台原生入口文件 = 用户拿不到（狗粮实例非事实源）。✅ 先改 `commands/governance-init.md` Step 7 注入模板（canonical source）→ bump 版本 → /plugin update → bootstrap 自升级（FIX-011；模板是唯一事实源）。

## 干活前检查（每次收到任务时）
任务在计划跟踪表里吗（不在先入账）？做完后补什么证据？影响别的阶段吗（先记风险）？——用户视角三问见 §B4。

## 提问规则（强制）
**AskUserQuestion 是唯一合法的用户提问方式**——禁止内联文字问句。默认**仅在关键决策停下来**，非关键自动执行。**判断标准**：改变方向/范围/架构或接受风险 → 永远问；破坏性/不可逆 + default-confirm → 确认；否则自动执行。三清单全文：§B3。

## 收工前检查（session 结束前）
①输出完成摘要 ②补证据 `.governance/evidence-log.md` ③更新 plan-tracker 状态 ④写 `.governance/session-snapshot.md` ⑤auto git commit（maximum-autonomy 加 push；message 引用 task ID）⑥AskUserQuestion 确认下一步。

## 详细规则

完整行为协议见插件 `software-project-governance` skill（M0~M9 强制性规则、Gate 行为、触发模式等）。以上 bootstrap 规则不依赖 SKILL.md 是否被加载——每次会话必定生效。

## 故障排除（Agent 行为异常时）

agent 不守协议（跳 Gate/忽略 AskUserQuestion/选择性执行）→ 四步排查：①加载了 skill 吗 ②读了 plan-tracker 吗 ③证据可信吗（`check-governance`）④完成是真的吗（读其声称改的文件）——明细 §B5；完整 8 种失败模式见 `skills/software-project-governance/references/agent-failure-modes.md`。

## 当前项目治理状态快速入口

- 计划跟踪：`.governance/plan-tracker.md` · 证据：`.governance/evidence-log.md` · 决策：`.governance/decision-log.md` · 风险：`.governance/risk-log.md`
- 验证命令：`python <plugin_home>/infra/verify_workflow.py`（`<plugin_home>` 来自 resolve_entry.py）；完整治理交互：`/governance`
- **查询已归档 entry**：Read `.governance/archive/index.md` → grep 目标 ID → 按索引 Read 归档文件（§B1）
- 治理文件读取编码（FIX-278 G4/F）：pwsh 读 `.governance` 治理文件 MUST 显式 UTF-8——`Get-Content -Encoding UTF8`；禁止裸 `Get-Content`——Windows 默认 GBK 解码产生 mojibake。
```

**strict profile 注入模板**（strict 差异段——渲染时由 `sync_entry_projection.extract_canonical_templates` 组合：strict = standard 共享基座 + 本段末尾追加；FEAT-041 单次维护）：
```markdown
### Strict Profile 强制规则

**量化 Gate 评分**：每个 Gate 评分 0~5 分，≥3 通过 / <3 阻塞；评分记录于 plan-tracker Gate 量化评分列；Gate 失败后需正式审批才能重试。

**强制证据要求**：每个 P0 任务完成 MUST 有 ≥2 条独立证据（类型不重复）；每阶段结束 MUST 重评所有活跃风险。

**阶段纪律**：阶段间不允许重叠；阶段回退需决策记录 + 影响分析；不允许"有条件通过"——Gate 要么通过要么阻塞全部。

**审查强制**：所有产品代码变更 MUST 经独立 Code Reviewer 审查；Reviewer 必须是与 Producer 不同的 Agent 实例。

**归档完整性强制**：check-archive-integrity 失败，或 check-governance 暴露有可归档数据但未归档 → BLOCK Gate/发布完成并标记 P0——归档不一致或触发缺口可能导致证据链断裂
```

**secondary-thin 注入模板**（薄指针版——FEAT-037 双入口去重；仅当工作区同时存在 AGENTS.md 与 CLAUDE.md 且本文件为次要平台入口时注入；`{PRIMARY_ENTRY}` 由生成机制替换为主入口文件名；段内小节只用三级标题——薄指针段边界=下一个二级标题）：
```markdown
## Governance Bootstrap（强制 — 每次会话第一动作 · 次要平台入口薄指针）

> @bootstrap-version: 0.89.0（薄指针版——FEAT-037 双入口去重；完整 bootstrap 见 {PRIMARY_ENTRY}（主入口），行为约束以主入口为准）

本工作区存在两个平台原生入口文件。本文件是次要平台入口（Codex/opencode 等）的薄指针投影，不复制完整模板；主入口 `{PRIMARY_ENTRY}` 携带完整 bootstrap（Step 0~4、交叉验证、阶段跳跃防护、Agent Team、Bootstrap 变更纪律）。

### 最小存活检查（第一动作）

1. 运行 `python <plugin_home>/skills/software-project-governance/infra/resolve_entry.py --json`；`resolved_root_ok == false` → MUST STOP，不呈现治理状态（fail-closed）。
2. 读 `.governance/plan-tracker.md`；阶段/Gate/模式未知 → 读 `## 项目配置` 节；`.governance/` 不存在 → 提醒先初始化。
3. **快路径与行为灰度开关（FEAT-034/040）**：热数据优先 `governance-bootstrap --format json`（不可用回退六段读取）；`GOVERNANCE_LEGACY_BEHAVIOR=1` 或 `behavior_profile: legacy` → 只回退性能行为，**安全语义不回退**；见其 `behavior` 面。
4. 完整规则：加载 `skills/software-project-governance/SKILL.md`（或读主入口 `{PRIMARY_ENTRY}`）。

### SELF-CHECK（在任何输出之前）

1. 读了 `.governance/plan-tracker.md`？知道阶段/Gate/模式（含 carry-over，session-snapshot）？任一未知 → 立即停止，先读。
2. 即将输出问句？→ 改用 AskUserQuestion。到达交互边界？→ MUST 使用 AskUserQuestion（完整 SELF-CHECK：SKILL.md「Bootstrap 规程明细」§B0）。
3. 即将写入的修改/证据是否有事实依据？无支撑 → 标 `BLOCKED`，禁止编造。

### 模式确认（每次会话一句，模式自适应）

- **always-on** → `Governance: {trigger_mode} x {permission_mode} | stage: {stage}, Gate {gate}: {status}, {risk_count} risk(s)`
- **on-demand** → `Governance: on-demand x {permission_mode}`（仅用户显式调用时展开完整状态）
- **silent-track** → 不输出治理面板/风险统计/任务进度表

### 治理状态快速入口

- 计划跟踪 `.governance/plan-tracker.md` · 证据 `.governance/evidence-log.md` · 决策 `.governance/decision-log.md` · 风险 `.governance/risk-log.md`
- 验证命令：`python <plugin_home>/skills/software-project-governance/infra/verify_workflow.py`（`<plugin_home>` 来自 resolve_entry.py）
- 治理文件读取编码（FIX-278）：pwsh 读 `.governance` 文件 MUST 显式 UTF-8——`Get-Content -Encoding UTF8`；裸 `Get-Content` 在 Windows 默认 GBK 解码产生 mojibake。
- 完整治理交互：`/governance`；完整 bootstrap（SELF-CHECK 全文/干活前/提问规则/收工检查）：`{PRIMARY_ENTRY}`（主入口）
```

**双入口去重（FEAT-037——单一 canonical 源生成薄投影）**：
- **IF** 项目根目录同时存在 `AGENTS.md` 与 `CLAUDE.md` → 主入口（platform primary 声明：默认 `CLAUDE.md`，见 sync_entry_projection.py `PRIMARY_DEFAULT`）注入所选 profile **完整模板**；次要入口注入 **secondary-thin 薄指针模板**（`{PRIMARY_ENTRY}` → 主入口文件名，≤40 行 / ≤3072 字节）。**禁止两份完整模板并存**（会话注入成本翻倍——AUDIT-154 §5.3）。
- **IF** 仅存在一个入口文件 → 该文件注入完整模板（单入口行为不变——向后兼容）。
- **确定性执行路径**：`python <plugin_home>/skills/software-project-governance/infra/sync_entry_projection.py --project <项目根> --write`（幂等——跑两次零 diff；默认只读 check）。agent 手工编辑入口 bootstrap 段 = 违反"模板是唯一事实源"纪律。
- **投影同步守护**：`verify_workflow.py check-projection-sync` 附带运行 `check-entry-bootstrap-sync`（主入口段 == canonical 全文；薄指针段 == 渲染结果且 ≤40 行/≤3KB/最小存活检查齐全；双全模板并存 = FAIL）。
- **薄指针保留的最小存活检查**（去重不得删除行为约束）：resolve_entry 第一动作、先读 plan-tracker、SELF-CHECK（对应完整版 6 条的压缩映射：完整 1→薄 1、**完整 2→薄 2**、**完整 3（carry-over 恢复）由主入口指针承载**、完整 4→薄 3、完整 5→薄 4、完整 6→薄 5）、快路径与行为灰度开关（薄 3，FEAT-034/040）、模式确认、治理状态快速入口、主入口指针。

### Step 8: 安装 git governance hooks（系统级约束——不依赖 agent 自觉）

**设计假设：agent 不会自觉遵守规则。系统 MUST 强制执行。**

- **IF** 项目根目录存在 `.git/` → 安装两个 hook：

  1. **pre-commit hook**（阻断型——commit 前检查）：
     - 先运行 `python <plugin_home>/infra/resolve_entry.py --json` 拿到 `plugin_home`，复制 `<plugin_home>/infra/hooks/pre-commit` 到 `.git/hooks/pre-commit`
     - 每次 `git commit` **之前**自动执行
     - BLOCKS commit if: commit message 无 task ID、task 不在 plan-tracker 中
     - WARNS if: evidence 不存在（不阻断——只提醒）
     - 紧急绕过：`git commit --no-verify`

  2. **post-commit hook**（报告型——commit 后检查）：
     - 复制 `<plugin_home>/infra/hooks/post-commit` 到 `.git/hooks/post-commit`（`<plugin_home>` 来自 resolve_entry.py）
     - 每次 `git commit` **之后**自动执行
     - 提取 task ID → 检查 evidence → 输出 check-governance 摘要
     - 不阻断——只报告

  3. **commit-msg hook**（阻断型——消息检查）：
     - 复制 `<plugin_home>/infra/hooks/commit-msg` 到 `.git/hooks/commit-msg`（`<plugin_home>` 来自 resolve_entry.py）
     - 每次 `git commit` 消息准备完毕后自动执行（在 pre-commit 之后）
     - BLOCKS commit if: task ID 缺失、task 不在 plan-tracker、目标对齐/用户影响/Breaking Change 缺失
     - 接收 $1 为 commit message 文件——消息读取可靠（与 pre-commit 依赖滞后桥接不同）

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
| permission_mode | 字符串 | 操作权限模式 | "maximum-autonomy" |
| current_stage | 字符串 | 当前阶段 | "initiation" |
| created_files | 列表 | 创建的文件列表 | [".governance/plan-tracker.md", ".governance/evidence-log.md", ".governance/decision-log.md", ".governance/risk-log.md"] |
| bootstrap_injected | 布尔 | 是否注入了 bootstrap | true/false |
| gate_status | 表格 | 各 Gate 初始化状态 | G1~G11 的简短状态表 |

### 输出模板

```
"{project_name}" 的治理已初始化

Profile: {profile}
触发模式: {trigger_mode}
操作权限模式: {permission_mode}
当前阶段: {current_stage}

已创建文件:
  ✅ .governance/plan-tracker.md
  ✅ .governance/evidence-log.md
  ✅ .governance/decision-log.md
  ✅ .governance/risk-log.md
  {if bootstrap_injected}✅ 平台原生入口文件 — 治理 bootstrap 已注入
  {if not bootstrap_injected}⊘ 平台原生入口文件 — 治理 bootstrap 已存在，已跳过
  {if hook_installed}✅ .git/hooks/pre-commit — 治理 hook 已安装
  ✅ .git/hooks/commit-msg — 治理 hook 已安装
  ✅ .git/hooks/post-commit — 治理 hook 已安装
  {if hook_skipped}⊘ .git/hooks/pre-commit — 已跳过（非 git 仓库）
  ⊘ .git/hooks/commit-msg — 已跳过（非 git 仓库）
  ⊘ .git/hooks/post-commit — 已跳过（非 git 仓库）

Gate 状态:
  {gate_status_table}


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
- [ ] 输出确认必须明确包含 permission_mode / 操作权限模式
- [ ] 任何文件的必需顶级字段均不包含占位值
