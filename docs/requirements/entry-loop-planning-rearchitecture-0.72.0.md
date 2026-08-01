# AUDIT-142: 入口/loop/任务规划三链系统性问题复诊报告（0.72.0）

> **状态**: 分析完成，待 0.73.0 前置规划消化（REQ-103/104/105 + FIX-236/237/238）
> **触发**: 用户 2026-08-02 反馈三簇 7 项问题（入口 ×2 / loop ×2 / 任务规划 ×3），FIX-222~229（0.71.0）修复后仍复现
> **关联**: EVD-852（SYSGAP-047 / AUDIT-139 / AUDIT-140 / AUDIT-141 同源）、FIX-222~229、REQ-103~105、ADR-014/017 候选
> **方法**: 只读取证（rg / git log / 代码阅读 / 本地实测），全部结论可定位到 文件:行 或命令输出；无产品代码修改
> **复核声明**: 本报告独立复核并扩展了 Coordinator 的定位事实；标记 ✅CONFIRMED 的结论均经本 Agent 独立验证
> **编号修订（2026-08-02 Requirement Review D1）**: 本报告正文使用 REQ-103/104/105；权威编号（plan-tracker/ADR-017）为 **REQ-104/105/106**（+1 偏移——REQ-101~103 已被 0.58.0~0.60.0 归档需求占用，见 archive/index.md）。映射：REQ-103=入口引导可达性→REQ-104；REQ-104=Loop 双环接线→REQ-105；REQ-105=任务规划闭环→REQ-106。

---

## 0. 执行摘要

三簇 7 项问题经根因链收敛为 **5 个系统性根因**：

| # | 根因 | 症状覆盖 | 证据强度 |
|---|------|---------|---------|
| R1 | **能力交付但未接线（capability-without-wiring）**——resolve_entry / process_gate_result / task-priority-analysis / T1-T4 均存在且可运行，但生产执行链无任何调用点 | 2.1、2.2、3.2 | ✅CONFIRMED |
| R2 | **真实宿主传播缺口**——修复只落在 dev 仓库模板（AGENTS.md/CLAUDE.md/commands），已安装宿主（python_game）仍是 0.54.1 时代引导，升级链存在鸡生蛋 | 1.1、1.2 | ✅CONFIRMED（直接证据） |
| R3 | **卡住感知复合归因**——resolve_entry 本体不可卡（实测 171~236ms），但 /governance 链路上的 check-governance（24.8s）、npm install（阻塞）、旧宿主 FileNotFound 重试链构成"卡住"感知 | 1.2 | ✅CONFIRMED（部分需用户环境） |
| R4 | **任务规划数据债**——依赖列存在 10 条环 + 状态漂移（已发布任务仍 ⏳），tool 输出被污染 → Coordinator 不信任 → 不调用 → 机械选择继续 | 3.1、3.3 | ✅CONFIRMED |
| R5 | **协议内部不一致**——interaction-boundary.md:187 仍规定机械行为，:217 已更新为依赖分析；M7.4 step 6 依赖分析是软性条件（"如果存在子命令"） | 3.1、3.2 | ✅CONFIRMED |

---

## 1. 入口问题

### 1.1 真实环境直接找不到 resolve_entry.py（用户反馈 1.1）

**现象**：在真实宿主执行 `/governance` 后，引导流程要求运行 `python <plugin_home>/infra/resolve_entry.py --json`，但脚本找不到。

**根因链（✅CONFIRMED，直接证据）**：

1. **真实宿主安装的是旧版插件，脚本字面不存在**：
   - `C:\Users\peter\.claude\plugins\cache\spg\software-project-governance\0.54.1\` 存在，其 `infra/` 目录 **无 resolve_entry.py**（实测 `resolve_entry.py=False`；只有 archive.py / cleanup.py / verify_workflow.py / TOOLS.md）。resolve_entry.py 是 0.64.0（FX-130/DEC-096）才引入的。
   - 真实外部宿主 python_game（`D:\AI\agent\claude\coding\python_game`）：**无 AGENTS.md**（`AGENTS.md=False`），CLAUDE.md 为 **0.54.1 时代模板**（`$WORKFLOW_HOME` 解析，见 python_game CLAUDE.md L29-32），plan-tracker `工作流版本: 0.54.1`（VAL-009 报告确认）。
   - 因此真实宿主上任何"运行 resolve_entry.py"的指令都会 FileNotFound——**"直接找不到"是字面成立的事实**。
2. **bootstrap 悖论未在旧宿主消除**：0.72.0 AGENTS.md L4-16 的 FIX-222 三方法（A：skill `file:` 路径推导；B：dev 仓库本地；C：显式参数验证）只存在于**新模板**中；旧宿主（0.54.1-era CLAUDE.md）仍在用 `$WORKFLOW_HOME` 环境变量 + "全局 plugin cache 考古"（LLM 搜索 SKILL.md）——正是 DEC-096 要消灭的路径。
3. **升级链鸡生蛋**：CLAUDE.md 的 Scenario C 自升级序列要求"检测到新插件版本 → 自升级 bootstrap 段"，但检测依赖 `$WORKFLOW_HOME` 解析；插件未更新（.claude cache 仍 0.54.1）→ 引导永不升级 → 用户感知"修复后仍复现"。

**影响面**：所有已初始化但未主动更新插件的宿主（python_game 为代表）永远停留在旧引导；真实环境 `/governance` 无法启动确定性入口，退化为 LLM 路径考古。

### 1.2 当前环境运行 resolve_entry.py 会卡住（用户反馈 1.2）

**本地复现结果（✅CONFIRMED 不可复现）**：

| 场景 | 结果 |
|------|------|
| `python <fullpath>/resolve_entry.py --json`，cwd=repo root | **171 ms** 正常返回 envelope |
| 同上，cwd=`C:\Users\peter` | **197 ms** |
| 同上，cwd=插件安装目录（0.72.0） | **236 ms** |
| 代码审计 | 纯 stdlib（argparse/json/os/re/sys/datetime/pathlib，L30-39）；无 subprocess/网络/input()；`resolve_host_root` 仅 `cwd.resolve(strict=True)`；`main()` 打印 JSON 后 return 0——**结构上不存在阻塞点** |

**候选根因（按证据强度排序，均经本地实测）**：

| 候选 | 证据 | 与"卡住"的相关性 |
|------|------|------------------|
| C1. `/governance` 链路后续步骤耗时被归因 | `check-governance` 实测 **24.8s / 227 issues**；post-commit hook Step 4 每次 commit 都跑它（阻塞至完成）；bootstrap 还要读 198KB plan-tracker + 1.36MB evidence-log | 高——用户看到第一条命令（resolve_entry）"卡住"可能是后续命令未返回 |
| C2. 真实宿主 FileNotFound → LLM 重试/考古循环 | 1.1 根因链；旧模板要求 LLM 在 plugin cache 找 SKILL.md | 高（真实宿主场景） |
| C3. web-console 首次启动阻塞 | `verify_workflow.py:19524` `subprocess.run([npm, "install"], ...)` **阻塞式**；commands/governance.md:91 规定 /governance SHOULD 运行 `web-console --governance-entry`；插件缓存副本无 web/node_modules 时 npm install 分钟级 | 中-高（真实宿主首次运行） |
| C4. 每次 commit 的 hooks 扫描 | 4 个 hooks 各自 `find_spg_home`（pre-commit:55-83，`find "$base" -path "*/skills/software-project-governance/SKILL.md"` 遍历 4 个 base）；实测 .codex cache find=**1.236s**、.claude cache find=**0.410s**；叠加 4 hooks ≈ 5-7s/commit + post-commit 25s | 中（慢而非卡） |
| C5. Windows WSL bash 陷阱 | `C:\windows\system32\bash.exe`（WSL launcher）本机实测 **>10s 超时无输出**（无已安装发行版）；若 hooks/脚本的 `bash` 经 PATH 解析到 system32 → 挂起 | 低-中（环境特定） |
| C6. Windows Store python stub | 真实宿主无 python 时 `python` 触发 Store 安装对话框 | 低-中（需用户环境确认） |

**结论**：直接调用 resolve_entry 不可卡；"卡住"是复合感知，主因是 C1（链路慢）+ C2/C3（真实宿主）。**无法在本地完整复现用户场景**——需要用户环境信息（见 §4）。

---

## 2. Loop 问题

### 2.1 Developer 修改检视意见后不触发复审（小循环失效，用户反馈 2.1）

**根因链（✅CONFIRMED）**：

1. **复审触发是 prose，无机器执行**：behavior-protocol.md:526-551 定义了 FIX-224 确定性触发器 T1-T4（T1：NEEDS_CHANGE → MUST 立即 spawn 同 Reviewer 复审）。但这是**指向 Coordinator LLM 的文档**——没有任何脚本检测 NEEDS_CHANGE 结果并触发 re-spawn。
2. **process_gate_result 生产调用点 = 0**：全仓 rg 确认 `process_gate_result`（loop_gate_processor.py:396 定义）的调用方只有：自身 docstring（L69）、35+ 单元测试、VAL-008 dogfood driver（temp dir，非生产）。**Coordinator 路径 / review 记录路径 / gate-engine 路径 / hooks 全部无调用**（与 AUDIT-140 0.70.0 结论一致，0.72.0 仍字面成立）。
3. **唯一接线点是 C（系统级 fuse block）**：`verify_workflow.py:6688-6711` `check_release_readiness` 调用 `collect_loop_fuse_issues`（L6698-6699）。但 A（review 结论）/B（gate 判定）/D（agent phase）三个接线点从未实现——fuse 块等待永远不会到达的输入。
4. **事后检测≠触发**：Check 30（checks/review_domain.py:1788 `check_review_closure`，verify_workflow.py:14087 接入）只**验证已记录**的复审链格式（V1 终态/V2 轮次连续/V3 熔断/V4 可追溯），不产生复审动作。

**影响面**：复审是否发生完全取决于 Coordinator 是否遵守 prose；上下文压缩、子 agent 场景、未加载协议时即失效。本会话（FIX-233 R0→R1）复审发生说明 prose 在 Coordinator 遵守时有效——**机制正确性 vs 执行确定性**的差距。

### 2.2 单点任务完成后直接结束，不回归上层循环（大循环失效，用户反馈 2.2）

**根因链（✅CONFIRMED）**：

1. **无 outer loop 运行时**：loop tiers（setup/inner/middle/outer）描述 per-unit 迭代语义，不是 task-to-task 序列；registry `back_edges` 只有 `release-to-design-replan` 一条（auto_fire=false 需人工）。无代码/schema 表达"unit X exit → return upper loop → 推荐下一 unit"。
2. **"继续"步骤是 prose**：behavior-protocol.md:552-561（M7.4 step 6，FIX-223 增强版）定义"依赖分析→推荐下一步→AskUserQuestion 呈现→不得直接结束"。这是文档约定，无机器执行；且 step 6a（L553）依赖分析是**软性条件**（"如果存在 task-priority-analysis 子命令"）。
3. **子 agent 天然不回归**：Developer/Reviewer 子 agent 完成即返回 final answer；"回归上层循环"依赖 Coordinator 自觉执行 step 6——同一 prose 依赖链的又一环节。

**影响面**：任务完成后"推荐下一步"完全依赖 Coordinator 会话行为；无证据表明 task-priority-analysis 被任何会话实际调用（evidence-log 全文仅 1 次提及 = 0 次执行记录）。

---

## 3. 任务规划问题

### 3.1 不分析依赖和优先级，机械挑未完成项（用户反馈 3.1）

**根因链（✅CONFIRMED）**：

1. **协议内部矛盾**：interaction-boundary.md:187（决策类型表）仍规定"任务排序 → 读 plan-tracker，**取最高优先级**"（机械行为）；:217（违规模式表）已被 FIX-227 更新为"执行依赖分析→推荐最合理下一步"。**FIX-227 只改了违规表，漏改决策表**——协议自相矛盾。
2. **依赖分析入口是软条件**：behavior-protocol.md:553 "如果存在 `task-priority-analysis` 子命令（FIX-226），运行它获取推荐"——条件句给 Coordinator 提供了不运行的合法路径。
3. **tool 存在但零调用**：`task-priority-analysis` CLI 已实现（verify_workflow.py:19008 cmd_task_priority_analysis，注册于 :20261/:20346，task_priority.py 861 行 + 57 测试全通过），实测可运行（116 tasks / 12 unblocked / 26 blocked），但**无任何生产调用点**（入口命令、变更控制、交互边界均不调用；evidence-log 无执行记录）。

### 3.2 各层 loop 缺任务规划能力，关键节点后不推荐合理推进（用户反馈 3.2）

**根因链（✅CONFIRMED）**：与 2.2 同根（R1）：loop_exit/back_edge 事件（loop_gate_processor.py）只做状态记录（fire-and-forget），不产生"find next unblocked unit"推荐；AskUserQuestion 完成选项是交付审查（确认/修改/拒绝），不是"下一步做什么"；commands/governance.md:324 有"推荐下一步: {next_priority}"模板但**未填充变量**——无代码从依赖计算它。

### 3.3 新事项进入时不系统分析优先级和依赖（用户反馈 3.3）

**根因链（✅CONFIRMED）**：

1. **变更控制已实质化但无强制**：verify_workflow.py:17461 变更控制标准路径已含"依赖分析（运行 task-priority-analysis）→ 优先级判定 → 冲突检查 → 版本适配 → 创建 task"（FIX-228 落地），但这是**模板 docstring**——没有任何 CLI/hook 在任务入账时强制执行；快速通道（.governance/ 范畴）仍可跳过。
2. **checklist 是 markdown 清单**：change-impact-checklist.md:23 增加"运行 task-priority-analysis 确认 unblocked 状态"（FIX-229 落地），但 checklist 无机器校验。
3. **数据债污染工具输出**（R4）：实测 task-priority-analysis 输出含 **10 条依赖环**（FIX-199↔FIX-201、FIX-217↔FIX-218、FIX-220↔REL-063 等，0.66.1 事故链历史数据）+ **状态漂移**（FIX-225~229/FEAT-006~009/VAL-008 已发布仍标 ⏳"待执行"）。工具推荐列表混入已完成的 FIX-225/226/227 等 → Coordinator 无法信任 → 不调用 → 机械选择继续（**恶性循环**）。

---

## 4. 卡住问题专项：本地复现记录与所需用户环境信息

**已本地完成**（见 §1.2 表格）：直接调用 3 场景计时；hooks find 计时；check-governance 计时；web-console 代码审计；WSL bash 陷阱确认；0.54.1 缓存内容确认。

**无法本地复现、需要用户环境信息**：

1. 复现命令**原文**（是否带 `--json`/`--project-root`、cwd、终端类型）
2. "卡住"时长与最终结果（超时被杀？最终返回？返回什么？）
3. 复现所在宿主（python_game / 本仓库 / 其他）与宿主侧插件缓存版本目录（`~/.claude/plugins/cache/**`、`~/.codex/plugins/cache/**`）
4. 宿主 `python` 是否为 Windows Store stub / 是否安装
5. 是否首次运行（web/node_modules 缺失 → npm install 阻塞）
6. 是否发生在 git commit 之后（post-commit 25s check-governance）

---

## 5. FIX-222~229 落地对照（0.71.0/0.72.0）

| FIX | 承诺 | 落地状态 | 残余缺口 |
|-----|------|---------|---------|
| FIX-222 | bootstrap 悖论修复（AGENTS.md 三方法） | ✅ AGENTS.md L4-16 三方法落地（f81060a） | 只更新了模板；**已安装宿主不传播**（python_game 仍 0.54.1 引导）；方法 A 依赖平台暴露 skill `file:` 路径（Codex 有，Claude Code 未必） |
| FIX-223 | 任务完成→下一步推荐显式步骤 | ✅ behavior-protocol.md:552-561 + interaction-boundary.md:217 | 纯 prose；step 6a 软条件；无机器执行 |
| FIX-224 | review 复审确定性触发器 T1-T4 | ✅ behavior-protocol.md:526-551 + Check 21/30 检测 | 触发器是 prose 指令；process_gate_result 0 生产调用；Check 30 只验已记录链 |
| FIX-225 | 依赖列结构化 + 模板升级 | ✅ core/templates/plan-tracker.md:55 格式说明 | 历史数据未清理：10 条依赖环；已发布任务状态漂移 |
| FIX-226 | task-priority-analysis 工具 | ✅ task_priority.py 861 行 + 57 测试 + CLI（verify_workflow.py:19008） | **零生产调用**（evidence-log 0 次执行记录） |
| FIX-227 | 行为协议升级（机械→依赖分析） | ⚠️ 部分：interaction-boundary.md:217 已改，**:187 决策表漏改**（仍"取最高优先级"） | 协议内部矛盾 |
| FIX-228 | 变更控制实质化 | ✅ 模板含标准路径+快速通道边界（verify_workflow.py:17461） | 文档化无强制；无入账拦截 |
| FIX-229 | change-impact-checklist 扩展 | ✅ change-impact-checklist.md:23 | markdown 清单无校验 |

**总体判断**：FIX-222~229 交付了**能力**（模板/工具/协议文本），但**接线、传播、数据、强制**四个维度未闭环——这正是"修复后仍复现"的机制解释。

---

## 6. REQ-103/104/105 需求定义细化

### REQ-103 入口引导可达性（P1, 0.73.0）

- **JTBD**：当我在任意已初始化宿主（含无 AGENTS.md/CLAUDE.md 的宿主）执行 `/governance` 时，引导流程必须在确定时间内定位入口脚本并返回 envelope，不依赖宿主文件存在或 LLM 考古。
- **验收信号（可测）**：
  1. 在 python_game 类宿主（无 AGENTS.md、插件缓存仅旧版）上，`/governance` 引导 ≤5s 内产出确定性诊断（找到/找不到+原因），不进入 LLM 搜索循环
  2. resolve_entry 调用超时兜底：>15s 时输出分类诊断（FileNotFound / 超时 / python 缺失），fail-closed 不静默
  3. 0.54.1 时代 CLAUDE.md 的 `$WORKFLOW_HOME` 解析在插件缺失时给出明确错误而非无限 fallback
- **非目标**：不在插件外分发独立二进制；不改变 resolve_entry 双 root 模型（DEC-096）；不承诺所有平台同一路径。
- **约束**：resolve_entry.py 保持纯 stdlib；向后兼容 0.54.1-era 宿主。
- **方案权衡**（置信度标注）：A. 命令模板支持平台注入变量（`$CLAUDE_PLUGIN_ROOT`/skill file: 路径统一解析）——实测可行（Codex 上下文含 file: 路径）；B. install-time 绝对路径投影——需 marketplace 侧支持，不可控；C. 宿主内 vendor 引导脚本——与现有 e2e fixture 模式一致但增大宿主足迹。**推荐 A + C 兜底**。

### REQ-104 Loop 双环接线（P1, 0.73.0）

- **JTBD**：当审查结论为 NEEDS_CHANGE 或 flow-unit 任务完成时，系统必须（不经 Coordinator 自觉）驱动复审与下一步推荐，且该行为可机器验证。
- **验收信号（可测）**：
  1. `process_gate_result` 生产调用点 ≥2（review 结论记录路径 + gate 判定路径），`check` 可枚举验证（新增 check 或扩展现有）
  2. NEEDS_CHANGE 记录后，24h/下一 commit 前存在 R{n+1} 复审证据（Check 30 从"验格式"升级为"触发时效"）
  3. 任务完成/loop_exit 事件消费路径产出 next-unit 候选（调用 task-priority-analysis 或等价），推荐出现在交互边界
- **非目标**：不实现 escalation 4 选项 UI；不重写 PARO 状态机；不改 v1 宿主行为（no-op 保持）。
- **约束**：接线为薄调用（≤10 行/点，ADR-014 §6 原则）；状态机写失败不得阻断 review 记录（best-effort + 降级）。
- **方案权衡**：A. 在 review 结论持久化路径（evidence 写入器/review CLI）后置薄调用——改动最小；B. auto_judge_gate 判定后置调用——覆盖自动化 gate；C. hook 层触发——可强制但侵入 git 流程。**推荐 A+B**（与 ADR-017 一致，C 留作 1.0.0 后候选）。

### REQ-105 任务规划闭环（P1, 0.73.0）

- **JTBD**：当新事项进入或任务完成后，交互边界呈现的必须是依赖排序后的候选（含推荐理由），且新任务入账前完成依赖/优先级/冲突分析。
- **验收信号（可测）**：
  1. evidence-log 出现 task-priority-analysis 调用记录（命令输出快照），且 Coordinator 会话推荐列表与工具输出一致
  2. 变更控制标准路径 MUST 执行依赖分析（CLI 或等价），产品代码新任务无分析记录时入账被拦截（hook/check）
  3. 依赖环与状态漂移数据债清零：task-priority-analysis 输出 0 cycle，已发布任务状态与 git tag 一致（漂移检测 0）
- **非目标**：不自动执行任务（推荐后仍需用户/Coordinator 决策）；不做跨版本自动重排。
- **约束**：tool 保持纯读；输出格式向后兼容。
- **方案权衡**：A. 先清数据债再集成（推荐——否则工具输出噪声使集成失效）；B. 工具侧容忍环/漂移（过滤已发布版本任务）——快速但治标；C. 直接强制调用不修数据——会产生错误推荐。**推荐 A（数据修复）+ B（工具过滤）双管**。

---

## 7. FIX-236/237/238 修复拆解建议（0.73.0）

### FIX-236 loop 生产接线（P2，REQ-104 消费方）

- **子任务**：
  - 236.1 Wiring A：review 结论（APPROVED/NEEDS_CHANGE/BLOCKED）→ `process_gate_result` 薄调用，挂接在 review 结论持久化路径
  - 236.2 Wiring B：`auto_judge_gate` 判定 → `process_gate_result` 薄调用
  - 236.3 完成事件→推荐桥：loop_exit/任务完成事件消费 → 产出 next-unit 候选（复用 task-priority-analysis）
  - 236.4 可测性：新增/扩展 check 断言"生产调用点存在 + NEEDS_CHANGE→R+1 时效"
- **边界**：不实现 escalation UI；不改 loop_paro_engine/loop_engine 纯函数；v1 宿主 no-op
- **依赖**：REQ-104 → ADR-017（架构授权先行）
- **风险**：状态机写失败影响 review 记录（缓解：best-effort + 失败不阻断）；接线点回归（缓解：236.4 check）
- **验收**：rg 枚举生产调用点 ≥2；新增 check PASS；全量测试 0 回归

### FIX-237 task-priority-analysis 强制集成（P2，REQ-105 消费方）

- **子任务**：
  - 237.1 数据债前置：修复 10 条依赖环（0.66.1 事故链 FIX-199~213/REL-055/REL-063 等历史行处置，与 Check 30 历史豁免同批）；状态漂移回填（FIX-225~229/FEAT-006~009/VAL-008 等标 ✅）
  - 237.2 工具增强：过滤已发布版本任务 + cycle 容错（警告而非 ERROR 阻断输出）
  - 237.3 入口集成：Scenario F/governance-status"推荐下一步"段 MUST 运行 tool
  - 237.4 变更控制集成：标准路径从 docstring 升级为可执行（governance-update 或新 triage 命令 MUST 调用）
  - 237.5 交互边界契约：AskUserQuestion 候选 = tool 输出 top-N + 理由；evidence-log 记录调用快照
- **边界**：不自动执行任务；不改 P0/P1/P2 判定规则本身
- **依赖**：REQ-105；237.1 可独立先行
- **风险**：数据债未清时误推（缓解：237.1 先行 + 237.2 过滤）；Coordinator 绕过（缓解：237.5 证据化）
- **验收**：tool 输出 0 cycle；交互边界候选与 tool 输出一致；evidence-log 出现调用记录

### FIX-238 入口引导修复（P2，REQ-103 消费方）

- **子任务**：
  - 238.1 宿主传播：commands/governance*.md 模板支持平台注入（`$CLAUDE_PLUGIN_ROOT` 等价物 / Codex skill file: 路径统一解析），消除 `<plugin_home>` 占位符解析歧义
  - 238.2 旧宿主自升级链：0.54.1-era 引导检测到更高版本 SKILL.md 时，先升级 bootstrap 段再继续（打破鸡生蛋；需在命令模板内置最低引导版本）
  - 238.3 卡住兜底：resolve_entry 调用超时（15s）+ 分类诊断（FileNotFound/超时/python 缺失/Store stub 检测）
  - 238.4 web-console 非阻塞：`--governance-entry` 默认不阻塞 npm install（提示手动 `--install`），或对 install 加超时
- **边界**：不改 resolve_entry.py 本体逻辑（DEC-096 双 root 保持）；不承诺旧宿主自动升级到最新（需用户 /plugin update 授权）
- **依赖**：REQ-103；238.2 需与 0.73.0 发布同时进行（旧宿主识别新版本）
- **风险**：跨平台命令注入差异（缓解：模板同时支持 POSIX/PowerShell 语法说明）；旧宿主误升级（缓解：版本检测 fail-closed）
- **验收**：python_game 类宿主引导 ≤5s 产出确定性结果；超时/缺失场景输出分类诊断；`--governance-entry` 无阻塞

---

## 8. 反面证据（与项目假设矛盾的发现）

1. **假设"resolve_entry 卡住"** → 矛盾：本地 3 场景直接调用 171~236ms 完成，代码结构无阻塞点。卡住更可能来自链路其他环节（check-governance 25s / npm install / 旧宿主 FileNotFound 重试）。**影响**：REQ-103 验收不能写"卡住修复"，必须按候选根因分类验证（超时兜底 + 传播修复）。
2. **假设"FIX-222~229 未生效/修复无效"** → 部分矛盾：0.72.0 模板与工具确实存在且可运行（task-priority-analysis 57 测试 + 实测输出；AGENTS.md 三方法在位）。残余缺口在**接线/传播/数据/强制**四维度，而非能力缺失。**影响**：修复方向是"接线 + 传播 + 数据治理"，不是重做工具。
3. **假设"小循环完全失效"** → 部分矛盾：本会话 0.72.0 债务包（FIX-233~235）中 R0→R1 复审实际发生（review-FIX-233-CODE-R1.md 存在），证明 prose 机制在 Coordinator 遵守时有效；失效场景是未加载协议/上下文压缩/子 agent 无协议上下文。**影响**：FIX-236 的机器接线是确定性保障，但需保留 prose 作为兜底教育层。

---

## 9. 发现清单（证据定位）

| # | 发现 | 证据 |
|---|------|------|
| F1 | 真实宿主插件为 0.54.1，无 resolve_entry.py | `C:\Users\peter\.claude\plugins\cache\spg\software-project-governance\0.54.1\skills\software-project-governance\infra\` 目录实测 |
| F2 | python_game 无 AGENTS.md，CLAUDE.md 为 0.54.1 时代模板 | python_game CLAUDE.md L3-32（$WORKFLOW_HOME 解析）；plan-tracker `工作流版本: 0.54.1` |
| F3 | resolve_entry.py 直接调用 171-236ms，无阻塞点 | 本报告 §1.2 计时表；resolve_entry.py L30-39 纯 stdlib |
| F4 | check-governance 24.8s（227 issues）；post-commit 每次 commit 阻塞等待 | 实测；post-commit hook Step 4（`python verify_workflow.py check-governance`） |
| F5 | web-console npm install 阻塞 | verify_workflow.py:19524 `subprocess.run([npm,"install"])`；commands/governance.md:91 |
| F6 | process_gate_result 生产调用点 = 0 | 全仓 rg；loop_gate_processor.py:396 def；仅 docstring/测试/VAL-008 driver |
| F7 | loop_fuse_check 已接 check_release_readiness（唯一接线点 C） | verify_workflow.py:6688-6711 |
| F8 | T1-T4 复审触发器为 prose | behavior-protocol.md:526-551；Check 30（review_domain.py:1788）只验已记录链 |
| F9 | M7.4 step 6 依赖分析为软条件 | behavior-protocol.md:553"如果存在 task-priority-analysis 子命令" |
| F10 | interaction-boundary.md 内部矛盾 | :187（决策表，仍"取最高优先级"）vs :217（违规表，已改依赖分析） |
| F11 | task-priority-analysis 零生产调用 | verify_workflow.py:19008 CLI 存在；evidence-log 全文 1 次提及 = 0 执行记录 |
| F12 | 依赖图数据债：10 条环 + 状态漂移 | task-priority-analysis 实测输出（FIX-199↔FIX-201 等；FIX-225~229 仍 ⏳） |
| F13 | 变更控制实质化但无强制 | verify_workflow.py:17461 docstring；change-impact-checklist.md:23 无校验 |
| F14 | hooks find 扫描 1.2-1.6s/次 ×4 hooks | Git Bash 实测（.codex 1.236s / .claude 0.410s）；pre-commit:55-83 |
| F15 | WSL system32 bash 本机挂起 | 实测 `C:\windows\system32\bash.exe` >10s 超时无输出 |

---

## 10. 未决问题（需用户/环境输入，不阻塞 0.73.0 规划）

1. "卡住"精确复现命令与宿主（§4 六项清单）——用于 REQ-103 验收细化
2. 真实宿主是否计划统一 /plugin update（0.54.1 → 0.72.0+）——决定 FIX-238 的传播优先级
3. 依赖环数据债（FIX-199~213 事故链）是否授权与 Check 30 历史豁免同批处置（DEC 级决策）
4. ADR-017（loop 接线架构授权）是否需要独立设计评审先行，还是并入 0.73.0 规划包
