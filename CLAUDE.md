# Claude Code Project Guidance

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
- **maximum-autonomy（最高权限）**：除关键决策和全部任务完成外，**一切操作自动执行**——包括 git commit+push（含 master/main）、本地命令、文件创建/编辑/删除、package 安装。用户思考流不被打断。
- **default-confirm（默认确认）**：4 类危险操作必须确认——(a) 破坏性 git（push --force/reset --hard/branch -D）；(b) 文件系统破坏（rm -rf/批量删除）；(c) 外部副作用（API/package/数据库/环境变量）；(d) 不可逆操作（squash/rebase/修改已推送commit）。常规操作自动执行。

**治理开关——用户随时动态切换**：
会话中用户说以下任意一句 → 立即切换并更新 plan-tracker：
- "切换到最高权限模式" / "开启最高权限" / "maximum autonomy" → permission_mode = maximum-autonomy
- "切换到默认确认模式" / "开启确认模式" / "default confirm" → permission_mode = default-confirm
- "切换到始终在线" / "切换到按需调用" / "切换到静默跟踪" → trigger_mode 对应切换
- "当前模式" / "现在什么模式" → 输出当前 trigger_mode × permission_mode

**每次会话输出一句确认**：
> 🔍 Governance: {trigger_mode} × {permission_mode} | stage: {stage}, Gate {gate}: {status}, {risk_count} risk(s)

### Step 1: 读 plan-tracker + 跨会话恢复
读取 `.governance/plan-tracker.md`，确认：当前阶段、最近 Gate 结论、活跃风险数、进行中的 P0 任务。如果 `.governance/` 不存在，提醒用户先初始化。

**跨会话状态恢复**：读取 `.governance/session-snapshot.md`（如存在），对照 plan-tracker：
- 快照中的进行中任务 → 确认为 carry-over 任务，继续执行
- 快照中的待确认决策 → 检查是否已过期或仍需确认
- 快照中的风险 escalation deadline ≤ 今天 → 立即升级

**工作流脱轨检测**：检查 plan-tracker 的 `最近复盘日期`——如果距今 > 7 天 AND 有若干新 commit 但 plan-tracker 无更新 → ⚠️ 工作流可能已被忽略。提醒用户是否需要更新治理状态。

**Hook 存活检测**（系统级约束——不依赖 agent 自觉）：检查 `.git/hooks/pre-commit` 和 `.git/hooks/post-commit` 是否存在。缺失 → ⚠️ 治理 hook 缺失——agent 的 commit 不受系统约束。**MUST** 提醒重装：`cp scripts/pre-commit-hook.sh .git/hooks/pre-commit && cp scripts/post-commit-hook.sh .git/hooks/post-commit`

**版本变化自动检测 + bootstrap 自升级**（用户更新插件后首次会话自动触发——零用户行动）：
1. 读取 plan-tracker `工作流版本` 和当前安装版本（SKILL.md frontmatter `version`）
2. **IF** 当前版本 > 记录版本 → 执行以下自动序列：

   **A. 自动输出更新摘要**（告知用户）：
   - 版本跨度 + 从 CHANGELOG.md 提取的新增/修复要点

   **B. 自动升级 CLAUDE.md bootstrap 段**（agent 自己升级自己）：
   - 读取当前 CLAUDE.md，找到 `## Governance Bootstrap` 段落
   - 替换为**与本文件完全一致的最新模板**（按 profile 选精简/完整版）
   - **保留 CLAUDE.md 其余所有内容不变**
   - 输出：`Bootstrap 已自动升级：v{old} → v{new}。`

   **C. 自动补全 plan-tracker 缺失结构**（agent 自动补全——不是提示，是直接做）：
   - 项目配置缺少字段？→ 自动添加（permission_mode、工作流版本）
   - 缺少 `## 版本规划` 节？→ 自动添加（版本路线图空表 + 版本里程碑 + V-Gate + 版本规划纪律）
   - 缺少 `## 需求跟踪矩阵` 节？→ 自动添加
   - 缺少 `## 变更控制` 节？→ 自动添加（含快速通道）
   - 变更控制流程中是旧版（无快速通道）？→ 自动更新为含快速通道的版本
   - `.git/hooks/post-commit` 不存在？→ 提示一次性命令（agent 不能自动写 .git/hooks/——安全问题）

   **D. 更新 plan-tracker `工作流版本`** 为当前版本

**这就是用户要做的全部：/plugin update → 下次会话 → 一切自动完成。**
不需要记住命令，不需要读文档，不需要手动操作——agent 自己升级自己。

### Step 2: 交叉验证（3 项强制检查）
对照 `.governance/plan-tracker.md` 和 `.governance/evidence-log.md`：

1. **证据完整性**：plan-tracker 中状态为"已完成"的任务，evidence-log 中是否有对应证据？缺失 = P0 漏洞，告知用户。
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
❌ 禁止：直接修改 CLAUDE.md 添加新行为
        → 改了用户得不到——狗粮实例不是事实源

✅ 强制：commands/governance-init.md Step 7 注入模板 → bump 版本 →
       用户 /plugin update → bootstrap 自升级 → 本仓库 CLAUDE.md 同步
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
3. agent 的证据可信吗？ → 运行 `python scripts/verify_workflow.py check-governance`
4. agent 的完成是真的吗？ → 读 agent 声称创建/修改的文件

完整的 8 种失败模式、检测方法和应急动作见 `skills/software-project-governance/references/agent-failure-modes.md`。

## 当前项目治理状态快速入口

- 计划跟踪：`.governance/plan-tracker.md`
- 证据记录：`.governance/evidence-log.md`
- 决策记录：`.governance/decision-log.md`
- 风险记录：`.governance/risk-log.md`
- 验证命令：`python scripts/verify_workflow.py`
