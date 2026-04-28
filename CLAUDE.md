# Claude Code Project Guidance

## Governance Bootstrap（强制 — 每次会话第一动作）

**⚡ SELF-CHECK（在任何输出之前先问自己）**：
1. 我是否已经读了 `.governance/plan-tracker.md`？否 → **立即停止，先去读**
2. 我是否知道当前项目处于哪个阶段？否 → **你没读 plan-tracker，去读**
3. 上一 session 结束后是哪个阶段？是否有 carry-over 任务？不知道 → **去读 session-snapshot.md**

如果你已经回答了用户的任务请求但没有执行以上检查 → **停下来补执行。**

### Step 0: 确定触发模式

读取 `.governance/plan-tracker.md` 的 `## 项目配置` 节，确认 `触发模式`：

- **always-on**（默认）→ 执行完整 Step 1~3。治理面板可正常输出。
- **on-demand** → 仅执行 Step 1（读 plan-tracker 确认当前阶段/活跃风险）。Step 2 交叉验证和 Step 3 优先级确认仅在用户显式调用 governance 命令（`/governance-status`、`/governance-gate`、`/governance-verify`）时执行。不主动输出治理面板。
- **silent-track** → 执行 Step 1~2（读 plan-tracker + 交叉验证），但 **MUST NOT** 向用户输出治理面板、风险统计、任务进度表。仅在 Gate 检查失败或风险 escalation 到期时打断用户。Step 3 仅在 P0 任务阻塞时提醒。

**触发模式差异可被检测到**：用户切换模式后观察到 agent 治理输出量显著变化。如果 silent-track 模式下 agent 仍输出完整治理面板 = 触发模式未生效。

### Step 1: 读 plan-tracker + 跨会话恢复
读取 `.governance/plan-tracker.md`，确认：当前阶段、最近 Gate 结论、活跃风险数、进行中的 P0 任务。如果 `.governance/` 不存在，提醒用户先初始化。

**跨会话状态恢复**：读取 `.governance/session-snapshot.md`（如存在），对照 plan-tracker：
- 快照中的进行中任务 → 确认为 carry-over 任务，继续执行
- 快照中的待确认决策 → 检查是否已过期或仍需确认
- 快照中的风险 escalation deadline ≤ 今天 → 立即升级

**工作流脱轨检测**：检查 plan-tracker 的 `最近复盘日期`——如果距今 > 7 天 AND 有若干新 commit 但 plan-tracker 无更新 → ⚠️ 工作流可能已被忽略。提醒用户是否需要更新治理状态。

### Step 2: 交叉验证（3 项强制检查）
对照 `.governance/plan-tracker.md` 和 `.governance/evidence-log.md`：

1. **证据完整性**：plan-tracker 中状态为"已完成"的任务，evidence-log 中是否有对应证据？缺失 = P0 漏洞，告知用户。
2. **Gate 一致性**：plan-tracker 的 Gate 状态与 evidence-log 的最新证据是否匹配？Gate 标记 passed 但无对应证据 = 不一致，告知用户。
3. **风险过期**：risk-log 中活跃风险超过 7 天未更新？是 = 标记为过期风险，告知用户。

任一检查失败 → 列出差距 → 征求用户是否立即修复（AskUserQuestion）。

### Step 3: 阶段跳跃防护（MANDATORY）
**IF** 用户请求直接进入开发/测试/发布等后期阶段，但当前 Gate 状态显示前置 Gate 均为 pending → **MUST** 警告用户跳过前置阶段的风险（没有明确目标就开始编码的返工风险 / 没有架构设计导致后续重构成本高 / 缺少 Gate 检查的证据记录）。**这不是阻止用户前进——是确保用户知悉风险。** 用户可以选择继续跳过，但决策必须记录到 decision-log。

### Step 4: 优先级确认
如果 plan-tracker 中有 passed-with-conditions 遗留项或有进行中的 P0 任务 → 优先处理。上一 session 未完成的 P0 任务 → 继续执行（从 session-snapshot.md 中识别）。

**没读 plan-tracker 就开始干活 = 流程违规。跳过交叉验证 = 流程违规。跳过阶段跳跃防护 = 流程违规。这不是"建议"，是前置条件。**

## 干活前检查（每次收到任务时）

在开始执行任何任务前，确认三件事：
- 这个任务在计划跟踪表里吗？不在就先入账
- 做完后需要补什么证据？先想清楚
- 这个任务会不会影响别的阶段？影响就先记风险

## 提问规则（强制）

**AskUserQuestion 是唯一合法的用户提问方式。** 禁止用内联文字问"要不要继续""是否如何如何"——所有需要用户判断的问题必须通过 AskUserQuestion 工具。

默认模式：**仅在关键决策停下来**。非关键决策自动执行不中断。

### 关键决策分类（自包含——不依赖 SKILL.md 加载状态）

**关键决策** — 必须停下来用 AskUserQuestion：
- 范围变更（新增/删除功能、改变项目边界）
- 架构决策（技术栈选择、模块拆分、接口设计）
- 发布决策（go/no-go、版本号升级、breaking change）
- 风险接受（接受已知风险、绕过 Gate）
- 外部依赖变更（引入新库、新服务、API 变更）
- Profile/触发模式变更

**非关键决策** — 自动执行，不提问：
- 已确认方向内的任务排序
- 证据格式和详细程度
- 自然边界的 commit 时机（按 DEC-025 自动提交）
- 治理记录更新
- 微小实现选择（文件命名、变量名、代码风格）
- Gate 自评结果（仅在失败时告知）

**判断标准**：决策是否改变项目方向、范围、架构或接受风险？是 → 关键决策，必须问。决策是关于如何在已确认方向内执行？是 → 非关键决策，自动执行。

## 收工前检查（session 结束前）

1. 输出本轮完成事项摘要
2. 补证据到 `.governance/evidence-log.md`
3. 更新 plan-tracker 任务状态（已完成/进行中）
4. **生成跨会话快照**：写入 `.governance/session-snapshot.md`（格式见 SKILL.md M4.2）——记录 carry-over 任务、待确认决策、活跃风险和下一 session 优先级。下一 session 的 Step 1 将从此文件恢复状态。
5. 自动 git commit（DEC-025：每次有意义变更即提交，commit message 必须引用 task ID）
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
