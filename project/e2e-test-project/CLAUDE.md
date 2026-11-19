# Claude Code 项目指引

## Governance Bootstrap（强制 — 每次会话第一动作）

> @bootstrap-version: 0.99.0（模板最低引导版本——低于 SKILL frontmatter active_version 即陈旧，先升级本段再继续）
>
> 契约 v2：触发器行内，§Bx 指 `skills/software-project-governance/SKILL.md`「Bootstrap 规程明细」。

**⚡ SELF-CHECK（输出前自问——硬约束行内；全文 §B0）**：
1-3. 当前工作区的根、阶段/Gate/模式和 carry-over 可由本次启动结果证实吗？未知 → 先定位或展开相应缺面。
4. **我即将输出的文本是否包含向用户提问的问句？**（吗？/？/要不要/是否…）→ **立即删除，改用 AskUserQuestion**（M5.1 = 流程违规）。
5. **到达交互边界**（呈现选项/完成工作单元/需用户选择）？→ **MUST AskUserQuestion**（默认是问，跳过是例外）。
6. **即将写入的内容是否有事实依据？**无文件/命令/测试/日志/用户输入支撑 → 标 `BLOCKED`/`待验证`，禁止编造。

关键行为契约第 5/6 条（完整规则 SKILL.md「关键行为契约」段）：5. **推荐必标需求源**：推荐与排序呈现逐项标注需求源（用户点名、活性缺陷、机器信号三选一标注），不标即违规；同优先级内 user-named 未闭合时 machine-signal 不得排前（DEC-286(7)）。6. **发现即闭环**：问题在触发点当场闭环（FAIL 即修/发现即改/风险即决/发布即结账）；「登记待以后」=违规；付不起闭环成本的动作不开始（DEC-286）。
关键行为契约第 7~9 条（FEAT-090，完整规则 M7.8）：7. 并行优先派发——独立任务单步批量 spawn，等待期间禁 Start-Sleep/轮询。8. 健康检查事件化——全量深检仅会话首检/推进类动作前/异常三类触发。9. 热路径单源——热数据唯一读取路径 governance-bootstrap，直读热面文件=违规。
关键行为契约第 10 条（FEAT-097）：goal 预算必收口（SKILL.md）。

### Step 0: 确定双维度模式（明细 §B0）
复用同次启动、同一项目的结果，否则运行 `python "<plugin_home>/infra/verify_workflow.py" governance-bootstrap --format json`。除下述旧版情形，须成功退出、JSON 有效且 `resolve.resolved_root_ok == true`，否则 MUST STOP 并显示诊断。 取 `project` 双维度模式：always-on 执行 Step 1~4；on-demand 仅 Step 1，显式调用才展开；silent-track 执行 Step 1~2，仅 Gate 失败或风险到期打断。maximum-autonomy 自动执行（含提交推送），关键决策、P0/治理关键交付审查、全部完成时询问；default-confirm 对破坏性 Git/文件操作、外部副作用和不可逆操作须确认。用户切换模式时同步 plan-tracker。**行为灰度开关**：`GOVERNANCE_LEGACY_BEHAVIOR=1` 优先于 `behavior_profile: legacy`，非法值见 `behavior.invalid`。**安全语义不回退**：升级确认、异常披露、fail-closed、真实环境防护、复审必达。按 §B0 确认模式；always-on 显示 `Governance: {trigger_mode} x {permission_mode} | stage: {stage}, Gate {gate}: {status}, {risk_count} risk(s)`。

### Step 0.5: Agent Team 激活（0.13.0+）
**你是 Coordinator，不是单 agent。**plan-tracker `工作流版本` ≥ 0.13.0 → 加载 `skills/software-project-governance/SKILL.md` 即 Coordinator 身份。**铁律**（违反 = 流程违规）：不直接修改产品代码；任务经 Agent 工具 spawn 角色 agent；Developer 不自审、Reviewer 不改码；用户交互只经 AskUserQuestion；sub-agent 不接触用户；spawn 前查 `.governance/agent-locks.json` 并写锁，完成后释放。何时激活/分发路由：SKILL.md「Agent 分发路由」。

### Step 1: 读 plan-tracker + 跨会话恢复（明细：§B1）
1. **快路径**：复用 Step 0 的热面。仅旧 CLI 明报未知子命令时运行 `python <plugin_home>/infra/resolve_entry.py --json`；成功退出且 `resolved_root_ok == true` 后可六段读取 `.governance/plan-tracker.md`。 显式 legacy 按本次 `behavior` 回退；六段与缺面规则见 §B1。
2. **首次交互前置（FEAT-034）**：热数据就绪 → MUST AskUserQuestion 首次交互（最小状态行：模式确认句 + 阶段/Gate 摘要 + carry-over/风险计数；deferred 健康位显示「待检查」）；深检后置 ≠ 可选——推进类动作前 MUST 补齐；升级待处理确认随本次首次交互 ask 一并呈现（Scenario C 同口径）。
3. **Execution Packet**：读 `.governance/execution-packets.json` 当前 TASK_ID 短包约束执行边界；活跃 P0/P1 缺包 → `execution-packet --write` 后再读（Check 18c 阻断缺包）。
4. **恢复与感知**：session-snapshot 进行中→carry-over；待确认决策→查时效；风险 escalation deadline ≤ 今天→立即升级；`archive/index.md` 存在→归档证据 = 有效证据；脱轨（复盘 >7 天 + 新 commit 无更新）→提醒；`.git/hooks/` 三 hook 缺失→提示重装（命令 §B1）。
5. **版本变化检测 + bootstrap 升级**。安装版高于项目记录时**呈现升级待处理**。AskUserQuestion 列出版本跨度、CHANGELOG 要点、写入清单和回滚方式，默认「执行升级（推荐）」。**用户未响应前零写操作**。版本升级写序列属推进类动作（DEC-207② P2-1 / M5.5 条 3），先深检再按 §B1 更新受管段、补计划结构。`.git/hooks/post-commit` 不存在时只提示安装。插件残留清理删除面仅对已确认的独占安装根预演 `python "<plugin_home>/infra/cleanup.py" --target "<plugin_root>" --dry-run`，另获确认才清理同一目标，归属不明则跳过。**D. 更新 plan-tracker `工作流版本`**。持续归档触发检测与执行按 §B1 在宿主根进行。无可归档数据则跳过，完整性失败时发布/版本 bump 收尾场景 MUST 阻断完成。

**用户要做的仍然只有：/plugin update → 下次会话。** 检测到版本差 → 呈现升级待处理（默认执行升级（推荐）），用户未响应前零写操作。

### Step 2: 交叉验证（3 项强制检查——后置深检；明细 §B2）
时序：首次交互后按需执行；推进类动作（发布/版本 bump/治理写回/恢复遗留任务的实际修改）前 MUST 先完成。会话健康摘要 = `check-governance --summary-only --scope quick`（FEAT-084）；推进类深检固定 full 面（`--summary-only` 无 scope）。三项：①证据完整性（已完成任务查 evidence-log，缺则查 archive/index.md——归档证据=有效证据）②Gate 一致性（passed 无对应证据 = 不一致）③风险过期（活跃风险 >7 天未更新）。任一失败 → 列出差距 → AskUserQuestion 征求修复。

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

完整行为协议见插件 `software-project-governance` skill（M0~M10 强制性规则、Gate 行为、触发模式等）。以上 bootstrap 规则不依赖 SKILL.md 是否被加载——每次会话必定生效。

## 故障排除（Agent 行为异常时）

agent 不守协议（跳 Gate/忽略 AskUserQuestion/选择性执行）→ 四步排查：①加载了 skill 吗 ②读了 plan-tracker 吗 ③证据可信吗（`check-governance`）④完成是真的吗（读其声称改的文件）——明细 §B5；完整 8 种失败模式见 `skills/software-project-governance/references/agent-failure-modes.md`。

## 当前项目治理状态快速入口

- 计划跟踪：`.governance/plan-tracker.md` · 证据：`.governance/evidence-log.md` · 决策：`.governance/decision-log.md` · 风险：`.governance/risk-log.md`
- 验证命令：`python <plugin_home>/infra/verify_workflow.py`（`<plugin_home>` 取本次定位结果）；完整治理交互：`/governance`
- **查询已归档 entry**：Read `.governance/archive/index.md` → grep 目标 ID → 按索引 Read 归档文件（§B1）
- 治理文件读取编码（FIX-278 G4/F）：pwsh 读 `.governance` 治理文件 MUST 显式 UTF-8——`Get-Content -Encoding UTF8`；禁止裸 `Get-Content`——Windows 默认 GBK 解码产生 mojibake。
