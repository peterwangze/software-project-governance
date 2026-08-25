# AUDIT-147 治理动作开销系统性分析 — dsh-reasoning-level DSH session trace 取证

- **任务**: AUDIT-147（P1）— 治理动作开销系统性分析（session trace 只读取证）
- **分析对象**: 用户项目 `D:\AI\agent\deepseek\plugins\thinking\dsh-reasoning-level`（下称**目标项目**）的 DSH session trace
- **取证材料**（`D:\AI\agent\claude\coding\project_management_workflow\.governance\incidents\audit147\`）:

| 会话 | 文件 | 类型 | 行数 | 字节 | 说明 |
|---|---|---|---|---|---|
| S1 | `session-f2425223-6212-4a2c-b08e-696597fa1579.jsonl` | 主会话（delegationDepth=0） | 5,455 | 3.6MB | 17:07，MAINT-017 方向调研与派发，spawn 5 个子 agent |
| S2 | `f68578cb-b5b9-42dd-a997-cc96c7de5e26.jsonl` | 子会话（Developer MAINT-017 返工重派） | 3,978 | 2.9MB | 20:49 |
| S3 | `9ce49e34-a1b2-4bf1-be5a-2cdfc5b33939.jsonl` | 子会话（Code Reviewer MAINT-017 R1 复审） | 1,492 | 1.3MB | 21:06（用户所指「最新 session」） |

S2/S3 的 parentSession 均为 S1（嵌套会话树，非独立会话）。
- **原始沉淀**: `C:\Users\peter\.dsh\sessions\--D-AI-agent-deepseek-plugins-thinking-dsh-reasoning-level--`（zstd，本分析未解压、未写入，只读）
- **分析日期**: 2026-08-26（按 trace 内时间戳与本地取证时间）
- **本仓库（plugin 仓库）**: `D:\AI\agent\claude\coding\project_management_workflow` 是治理软件的开发宿主——归因时区分「治理软件自身问题 / 目标项目治理数据问题 / 环境问题」

---

## 0. 结论摘要（TL;DR）

1. **「verify 告警洪流」在样本内未被证实**：3 个会话中唯一的健康检查输出是 `Governance: [PASS]`（20 字符，`verify_workflow.py check-governance --summary-only`）。**H1 待验证状态 = 样本内不支持，用户感知可能来自样本外会话（本样本仅覆盖 17:07–21:06）**。
2. **用户「>50% 花费在治理」的感知在样本内不成立**（按本报告口径：治理工具输出字符占比 13.9%–34.7%，reasoning 中治理标记字符占比 2.1%–7.9%）。但存在**两个被低估的真实开销**：
   - **治理「读取」远大于治理「命令输出」**：S1 中全部治理命令输出仅约 1.6KB，而治理类读取（skill 15,745 + governance.md 28,718 + plan-tracker 15,222 + snapshot 4,436 + 其他 ≈ 74.4KB）是命令输出的 **46 倍**。
   - **重复注入**：每次会话（含子会话）都重新加载 skill（15,745 字符）+ 读 plan-tracker（~15–17K）；S1 启动阶段治理引导合计 ≈ 64KB。
3. **已证实的干扰源共 8 类**（均带行号证据），其中 4 类为治理软件/治理数据自身问题：行内状态矛盾堆叠、历史任务占比 85%+、R0 报告原文未落盘导致检索成本、概念辨析成本（approval policy vs permission_mode）；1 类环境问题（pwsh 管道 GBK/UTF-8 mojibake）；1 类为治理软件自身的重复加载（skill + governance.md 双份）；2 类为边界情况（子会话 bootstrap 全量重复、git diff 重定向到 .governance 临时目录）。
4. **占大头的不是 verify，而是「治理解析负担」**：plan-tracker 55% 字符是任务表、其中 ~85% 为已完成/已入账历史状态。

---

## 1. 计算口径与可复算性说明

### 1.1 度量口径（本报告所有「治理占比」均按此定义）

- **治理类 tool call**（显式分类，判据见 1.2）：`skill(software-project-governance)`、`pwsh` 命令匹配 `resolve_entry|verify_workflow|archive.py|task-priority|status.py|\.governance`、`read/grep/glob` 路径含 `\.governance` 或 `commands/governance`、`ask_user_question`。
- **治理 result 字符占比** = Σ(治理类 tool result 的 text 字符串字符数) / Σ(全部 tool result text 字符数)。字符为「UTF-8 解码后的字符数」；token 换算另行标注（中文 ≈0.6–1.0 字/token，估算）。
- **reasoning 治理标记占比**：两个口径并存：
  - 口径 A（**stats.json 生成器**）：`reasoning_gov_chars / reasoning_chars`，生成器词表未公开（按其产出反推为宽词表：Governance/check/verify/issue/FAIL/WARN/基线 等，含歧义词）；
  - 口径 B（**本报告自建，可复算**）：对 `reasoning-chunks` 事件 join `data.texts` 后，统计**强治理词**（`Governance|governance|check-governance|check-release|verify_workflow|task-priority|plan-tracker|resolve_entry|execution.packet|Governance health`）每次命中取 ±40 字符窗口的字符量 / reasoning 总字符量。命令（PowerShell，只读）：
    ```powershell
    # 对每个 jsonl：逐行解析 reasoning-chunks → join data.texts → regex 强词窗口计数
    ```
- **usage 口径**：`assistant/message` 事件 `data.usage` 为**每条消息的增量 inputTokens + 累计 cacheReadTokens 快照**（实测：inputTokens 序列为增量，cacheReadTokens 单调递增为快照）。stats.json 的 usage 三数 = 该会话全部 assistant/message 的求和。本报告采用：
  - 会话处理总量 = Σ(inputTokens + cacheReadTokens)（≈ 模型实际处理成本代理）；
  - 最终上下文 = 最后一条 assistant/message 的 cacheReadTokens（≈ 会话末上下文中已缓存部分）。

### 1.2 统计脚本与修正说明

- 原始 `stats.json` 的 `result_chars/result_gov_chars/top_results` **全部为 0（错误）**：tool/result 是两层嵌套（`message.content[i].content[j].text`），生成器只取了一层。本报告已按正确结构重算（`data.message.content[].content[].text`），全部比值来自重算。
- `stats.json` 的 `cmd_features.status` 系把 `git status` 等误计为治理 status（S2 中 8 次 status 实为 `git status`），**不作为数据依据**；本报告的治理命令数基于对全部 pwsh command 文本的人工核验。
- 本报告所有可复算命令均已在只读模式执行；除本报告文件外无任何写入（`~/.dsh` 零写入，见 §7）。

---

## 2. 事实 ↔ 假设分离

### 2.1 用户断言（待验证假设 → 验证结果）

| # | 用户断言 | 状态 | 验证结果 |
|---|---|---|---|
| A1 | verify 动作报了很多**不属于当前治理软件/当前项目**的告警 | **样本内不支持** | 3 会话中唯一健康输出 = "Governance: [PASS]"（20 字符，S1 line 155）；无任何 >100 字符的 verfor/check 告警输出。可能来自样本外会话 |
| A2 | 治理动作占用 **>50% token 消耗** | **样本内不成立** | 治理工具输出字符占比 13.9%–34.7%（S1/S2/S3）；reasoning 治理标记 2.1%–7.9%；即使按最宽的「治理 result 字符」口径，仅 9ce49e34 的 18.1% 与 f2425223 的 34.7% 落在 <50% 区间 |
| A3 | 其他动作（status/check/报告输出等）干扰模型制定逻辑 | **部分证实** | 「报告输出」确有实证（§4.3 的 R0 报告缺失→检索成本、subagent 报告 3–6KB 注入）；status/check 类在样本内未产生输出级干扰 |
| A4 | 用户感知（>50% 时间/精力） | **属感知，记为假设** | 时间维度无法从 trace 计算（无耗时字段）；token/字符维度已证伪 >50% |

### 2.2 已核实事实（每条可复算/可索引）

- F1. 三个会话的治理 tool call 数与治理 result 字符（§6 表 1/表 2）。
- F2. S1 唯一的 `check-governance --summary-only` 输出 = `Governance: [PASS]`（S1 line 155，20 字符）；`web-console --governance-entry` 输出 369 字符（line 334）；`review-record` 输出 660 字符（line 4956，含 wiring 未解析告警）。
- F3. plan-tracker.md（目标项目）当前 18,252 字符（含换行）/ 155 行；其中「## 当前活跃事项」10,092 字符（55.3%），含 22 行任务记录，仅有 3 条未闭环（MAINT-018/019/020，均为「已入账」= 未排期），其余 19 条为 ✅完成/📋已入账（历史信息占 ~85%）。
- F4. S3 中全量 read plan-tracker 返回 16,887 字符（line 71）；S2 中分段读（offset 55 limit 25）返回 8,308 字符（line 1725 为调用参数）。
- F5. `C:\Users\peter\.dsh\profiles\web\node_modules\dsh-reasoning-level\package.json` 中文 description 经 pwsh 读取出现 GBK-as-UTF-8 mojibake（S1 line 785：`ConvertFrom-Json : Invalid object passed in` + `缁熶竴鎺ㄧ悊绛夌骇鎻掍欢…`），全 trace 仅此一处，其余 read 工具输出中文正常（S1/S2/S3 的 plan-tracker read 均正常）。
- F6. `review-MAINT-017-R0.md` 仅 15 行机器记录头（无 findings 原文）——S2 Developer 在 line 328 的 reasoning 中明确「P3×2 details 按报告原文……没有该 report 原文」，并为此读 execution-packets.json（8,522 字符）+ plan-tracker 部分（8,308）。
- F7. S1 line 324/330（assistant/message reasoning）：模型花篇幅论证「平台 approval policy 变更 ≠ 治理 permission_mode 变更」（概念辨析）。
- F8. S1 spawn 5 个子 agent（line 4602/4855/5086/5237/5439），S2/S3 各自重复执行完整 bootstrap（skill 15,745 + resolve_entry 586 + plan-tracker read）。
- F9. 本仓治理基线（governance health 103 issues、task-priority CYCLE WARNING、carry-over 12、REL-069、18c execution packet）在三个 trace 中**无任何出现**（grep `carry-over|REL-069|CYCLE|18c execution|execution packet|archive trigger` 全文件：0 条命中；「CYCLE/cycle」命中全部为 S2 产品代码死锁分析中的 "no cycle"）。
- F10. 用户时间线：S1 中用户通过 ask_user_question 交互 4 次（resume_action/fix_direction/final_direction/gateway_sample），并有多轮直接消息（"你是不是搞复杂了，你直接调研一下现在已经支持的 github 上的相关的插件的实现不就行了" 等）——用户对流程复杂度的不满在 trace 中有直接记录（line 531 用户："我重新安装了，实测并没有任何改善……我不知道你这么久改了啥"）。

### 2.3 归因三分（治理软件自身 / 目标项目治理数据 / 环境）

| 现象 | 归因 |
|---|---|
| 行内状态矛盾堆叠（MAINT-014「⚠️ 已返工待重开」与「✅ 已闭环」同行，MAINT-017「⚠️ 新开」与「✅ 完成」同行） | **目标项目治理数据**（plan-tracker 行内历史堆叠 + 治理条款未强制行级状态机） |
| R0 报告原文未落盘（review 记录只有机器头） | **治理软件**（review-record 写入机头、findings 仅在 Reviewer 会话 context，未持久化） |
| skill+governance.md 双份引导（15,745 + 28,718 = 44,463 字符/会话） | **治理软件**（DSH 投影指引读 commands/governance.md，与 skill 内容重叠） |
| plan-tracker 85% 历史状态、无增量视图 | **目标项目治理数据 + 治理软件**（无「仅活跃」视图选项） |
| pwsh 中文 mojibake | **环境**（PowerShell Get-Content/管道默认编码） |

---

## 3. H1 — verify 告警噪声（量化）

### 3.1 样本内 verify 类输出清单（全部）

| 会话 | 命令 | 输出字符 | 内容 | 结论 |
|---|---|---|---|---|
| S1 | `verify_workflow.py check-governance --summary-only` | 20 | `Governance: [PASS]` | **零告警** |
| S1 | `verify_workflow.py web-console --governance-entry` | 369 | 面板 URL/状态 | 非告警 |
| S1 | `verify_workflow.py review-record --task MAINT-017 --round 0 --result NEEDS_CHANGE` | 660 | 机器记录结果（`wiring.wired=false`、`revisit_required=true`、next_round） | 1 条诊断性提示（wiring 未解析），非告警 |
| S2 | （无） | 0 | — | — |
| S3 | （无） | 0 | — | — |

**合计：verify 类输出 1,049 字符（0.23% 的治理 result），告警 0 条**。

### 3.2 用户感知的解释（假设，需样本外验证）

用户感知「verify 报了很多告警」在**本样本内找不到对应输出**。可能的来源（按似然排序，均标为待验证）：

1. **样本外会话**：样本仅覆盖 17:07–21:06 三个会话；用户全天使用 DSH，早间/午后会话（含 0.77.0 升级、v0.7.1 发布、白天开发会话）不在样本。这些会话可能有完整 check-governance/健康检查输出。
2. **其他项目/其他会话树**：用户感知可能来自其常用环境的多项目会话（非 target 项目）。
3. **把「治理文件内容中的 ⚠️/已入账/待重开 标记」感知为告警**：plan-tracker 行内大量 ⚠️/📋 标记（如 MAINT-014「⚠️ 已返工待重开」）在每次全量 read 时被模型逐行看到——**这是一种「伪告警视觉」**，但用户不会把这些称为「verify 报告」。
4. **时间混淆**：S2/S3 内 `node --test` 输出 `# fail`/`# pass` 等与治理无关。

### 3.3 H1 量化结论

- **样本内 verify 噪声占比 = 0%**（0 条告警输出 / 1,049 字符 verify 输出）。
- **用户断言「verify 告警大量不属于当前项目」样本内无法证实**；三个会话的 verify 输出中，唯一实质内容（review-record 的 wiring 提示）确属「治理软件自身问题」类别（review→gate 映射注册表数据缺失）。
- 已发现的**真实噪声机制 ≠ verify 告警**，而是（a）治理文件全量读取的字符量（§4.1）、（b）行内状态矛盾（§4.3）、（c）mojibake（§4.6）。

---

## 4. H2/H3 — token/字符占比与干扰源清单

### 4.1 治理动作字符占比（修正重算）

**表 1 — tool result 字符占比（本报告重算，stats.json 的 result 字段为 0 已弃用）**

| 会话 | 全部 tool result 字符 | 治理类 result 字符 | 占比 | 治理类 result 数 / 全部 |
|---|---|---|---|---|
| S1 | 214,473 | 74,420 | **34.7%** | 17 / 83 |
| S2 | 222,777 | 30,993 | **13.9%** | 9 / 70 |
| S3 | 199,462 | 36,043 | **18.1%** | 7 / 39 |

**表 2 — reasoning 中治理标记字符占比**

| 会话 | reasoning 总字符 | 口径 A（stats.json 生成器） | 口径 B（本报告强词±40 窗口，命中数） |
|---|---|---|---|
| S1 | 125,243 | 4,309 = 3.4% | 5,682 = **4.5%**（98 命中） |
| S2 | 201,850 | 16,038 = 7.9% | 4,142 = **2.1%**（57 命中） |
| S3 | 79,218 | 4,354 = 5.5% | 2,881 = **3.6%**（40 命中） |

**表 3 — usage（stats.json 求和口径 + 最终上下文快照）**

| 会话 | ΣinputTokens | ΣcacheReadTokens | ΣoutputTokens | ΣreasoningTokens | 最终上下文（末条 cacheRead） |
|---|---|---|---|---|---|
| S1 | 316,568 | 8,008,960 | 83,174 | 49,990 | 193,664 |
| S2 | 136,691 | 6,800,000 | 71,962 | 54,012 | 169,472 |
| S3 | 91,394 | 2,051,968 | 22,420 | 18,432 | 109,440 |

（注：stats.json 的 usage = 各条 assistant/message usage 求和；cacheReadTokens 为累计快照求和——口径见 §1.1。）

### 4.2 关键结构性发现：治理「读取」远大于治理「命令输出」

- S1 治理命令输出（resolve_entry 586 + check-governance 20 + web-console 369 + review-record 660）≈ **1.6KB**；
- S1 治理类读取（skill 15,745 + `commands/governance.md` 28,718 + plan-tracker 15,222 + snapshot 4,436 + decision-log 3,882 + agent-locks 226+226 + review-R0 553 + grep evidence 3,296）≈ **72.8KB**；
- **读取:命令输出 ≈ 46:1**。真正的 token 压力来自「每次会话读治理文件」，而不是「治理命令输出」。这与用户「verify 报很多告警」的感知方向相反——**感知与机制错位**。

### 4.3 干扰源分类清单（每类含 trace 实证 + 干扰机制）

| # | 类别 | trace 实证（会话 + 行/字符） | 对模型的干扰机制 |
|---|---|---|---|
| D1 | **输出巨大** | S1 line 100：plan-tracker 全量 15,222 字符；line 153：governance.md 28,718 字符；line 65：skill 15,745；line 101：snapshot 4,436。S3 line 71：plan-tracker 16,887 | 模型需要完整吸收 ~50-64KB 引导信息才能开始任务；bootstrap 强制 read 无「只读活跃」选项 |
| D2 | **信息与当前工作无关（历史任务/基线披露）** | plan-tracker 18,252 字符中，11 阶段 Gate 表（863）+ 版本路线图（546）+ 需求矩阵（542）+ 已发布版本信息等；「当前活跃事项」10,092 字符里 ~85% 是 ✅完成/📋已入账 状态（仅 3 条待办：MAINT-018/019/020 均为「已入账」） | 模型要先跳过历史再定位活跃；无「delta/活跃视图」时每次全量重读 |
| D3 | **行级状态矛盾（行内漂移）** | plan-tracker L60：MAINT-014 同谓词「⚠️ 已返工待重开（2026-08-26 用户实测——真实环境失效…）」→ 同格「→ ✅ **已闭环** (2026-08-26)」；L62：MAINT-017「⚠️ **新开** (2026-08-26)——用户实测验收失败」→「→ ✅ **完成** (2026-08-26)」 | 一行内两个矛盾状态，模型必须自行推断「哪个是最终态」；若用行末格做规则解析则可能误读（本仓同类基线：carry-over/行级快照滞后） |
| D4 | **重复披露** | S2/S3 每子会话独立 bootstrap（skill 15,745 再次注入 + resolve_entry + plan-tracker read）；S1 启动双份引导（skill 15,745 + commands/governance.md 28,718 内容重叠） | 同一治理知识每会话重复注入；子会话与主会话消耗相同的引导成本 |
| D5 | **概念辨析成本** | S1 line 324/330 (reasoning)：「用户提示 approval policy changed from 'ask' to 'never'……这**不是**治理 permission_mode 变更……」 | 模型花 reasoning 论证平台级/治理级概念区分（同为「权限」两套机制），属于治理信息造成的认知间接税 |
| D6 | **编码乱码** | S1 line 785：pwsh 读 `node_modules/dsh-reasoning-level/package.json` → `缁熶竴鎺ㄧ悊绛夌骇…`（GBK-as-UTF-8）+ `ConvertFrom-Json : Invalid object passed in` 命令失败（**全 trace 唯一一处；read 工具输出无乱码**） | 模型需识别乱码+失败原因；若非本次任务直接相关则纯属干扰（本次相关——是目标项目自身的安装信息，非治理） |
| D7 | **数据缺失→检索/等待成本** | S2 line 328 (reasoning)：「Let me check whether there is a reviewer output record elsewhere…review-MAINT-017-R0.md but got deleted? …read execution-packets.json and plan-tracker」；S2 实际 read execution-packets 8,522 + plan-tracker 8,308；S2 报告：「P3×2 详细原文未落盘……无法逐条对照，若 Coordinator 持有原文请补注」 | R0 报告 findings 未持久化 → Developer 无法处置 → 模型花动作+推理找报告 → 复审挂起（不确定性） |
| D8 | **子会话大报告注入主会话** | S1：subagent 完成报告作为 user/message 注入（「MAINT-017 — 执行完成报告」等，多条 3–6KB；S1 user/message 中报告类合计 ~11.5KB） | 主会话上下文被长报告填充；报告虽为产品事实但重复度高（与 commit message/plan-tracker 行重叠） |

### 4.4 H2 量化判定

- **「>50% token 消耗在治理」样本内不成立**：
  - 工具输入侧（result 字符）：13.9%–34.7%（S2 最低，S1 最高）；
  - 推理侧（reasoning）：2.1%–7.9%；
  - 即便把 user/message 系统注入（15,395 字符，全部为 AGENTS.md/CLAUDE.md 治理 bootstrap 模板）计入「治理输入」，S1 的治理总输入 ≈ (74,420 + 15,395 + 启动时其余) / (所有 input) —— 仍远低于 50%（约 35–40% 上限估计）。
- **误差声明**：字符→token 换算未做（中文 token 化依赖实现）；cacheRead 快照的每轮重读成本（ΣcacheReadTokens 6.8M–8.0M）反映了**长会话重读**成本，但该成本与「治理内容占比」是乘性关系：治理内容占比 13.9%–34.7% 的字符在每轮都被重读。若用户把「重读也已计入总消耗」也算进感知，则治理的**相对**占比仍不变（重读按同比例缩放）——因此 >50% 判定不受影响。
- **真正的偏差来源**：用户感知偏高可能因为（a）S1 的 34.7% 在特定时段（启动+规划期）更高；（b）「时间感知」受「等待模型处理长 context + ask_user_question 往返」放大——**时间维度无数据**（trace 无耗时字段），记为待验证。

### 4.5 H3 汇总

干扰源共 8 类（D1–D8，见 §4.3）。其中与「治理软件自身」强相关的：D4（双份引导/重复注入）、D7（review 记录不落盘）、D2 的「无活跃视图」；与「目标项目治理数据」强相关的：D3（行内状态矛盾）、D2（历史占比 85%）；与「环境」相关的：D6（mojibake）。**D1（输出巨大）是 D2/D4 的量的载体**。

---

## 5. H4 — 频率/动作序列占比

**表 4 — 动作序列统计（依据 tool/call 全量清单，逐条核验）**

| 会话 | tool/call 总数 | 治理类 calls | 治理占比 | 治理 pwsh 数/总 pwsh | 产品类 calls |
|---|---|---|---|---|---|
| S1 | 83 | 17（skill 1、pwsh 4、read 7、grep 1、ask_user_question 4） | 20.5% | 4/29（13.8%） | 66 |
| S2 | 70 | 9（read 8、grep 0**、** 等） | 12.9% | 0/23（0%） | 61 |
| S3 | 39 | 7（skill 1、pwsh 2、read 3、grep 1；其中 2 个为边界：git diff 重定向 → .governance 临时文件 + 读该临时文件） | 17.9% | 2/14（14.3%，含 1 边界） | 32 |

（S3 的 7 个治理 calls 中含 1 个边界：`git diff … > .governance\_tmp\_reviewer_diff_index.txt` + 读该临时文件——Reviewer 为读取 diff 的文件中转，路径在 .governance 下但内容为产品 diff。）

- **治理动作在「动作序列」中占比 12.9%–20.5%，平均 ≈17%**（与 token 占比同量级，二者交叉印证）。
- **治理动作次数虽少但体量大**（S1 表 1）：17 个治理 call 占 34.7% 字符——**平均每次治理调用消耗是产品调用的 2.7 倍**（34.7%/17 ÷ 65.3%/66 ≈ 2.06 / 0.99 = 2.1 倍；精确：74,420/17=4,377 字符/治理call vs 140,053/66=2,122 字符/产品call ≈ 2.06 倍）。S2：30,993/9=3,444 vs 191,784/61=3,144 ≈ 1.1 倍。S3：36,043/7=5,149 vs 163,419/32=5,107 ≈ 1.0 倍。
- **结论**：频率占比（~17%）低于用户感知；但 S1 的每次治理调用字符开销为产品调用的 ~2 倍（主因是 skill/文档/plan-tracker 全量读）。

---

## 6. 优化方向选项（只给选项与权衡，不做决策）

### 选项 A — 治理文件「活跃增量视图」（Recommend 候选，不裁定）
- **目标**: plan-tracker 只读「当前活跃」节（任务表仅未闭环行 + 当前阶段 Gate），历史行折叠为一行计数引用。
- **成本**: 低（修改 read 策略或新增 `status --active` 输出模式；SKILL.md bootstrap 改双模式读取）。
- **收益**: S1 单次 bootstrap 读取从 ~15,222 → ~3,000 字符（-80%）；S2/S3 同步受益；D2 干扰源直接消除。
- **风险**: 模型可能缺失全局上下文（如依赖/交叉任务引用）；需保证活跃视图可溯源到完整视图。

### 选项 B — 消除双份引导（skill + commands/governance.md 去重）
- **目标**: DSH 投影不再要求额外 read 28,718 字符的 governance.md（skill 内容已含 Coordinator 身份/规则），或让投影读「摘要」而非全文。
- **成本**: 低-中（适配层/投影链路小改 + 兼容测试）。
- **收益**: 每次会话 -28.7KB（S1 引导信息 -45%）；D4 部分解决。
- **风险**: 投影与源文件一致性、平台差异（其他 host 仍需完整入口）。

### 选项 C — review 报告全文落盘（review-record 持久化 findings）
- **目标**: Reviewer 的 findings 正文强制写入 `.governance/review-{TASK}-R{n}.md`（目前只有机器头）；Developer/后续轮次无需检索/等待。
- **成本**: 中（reviewer prompt 模板 + review-record 工具扩展 + 报告格式规约）。
- **收益**: D7 消除（Developer 检索 execution-packets+plan-tracker 的 8.5K+8.3K 冗余读取与「无法处置 P3」的空转）；复审 round 效率提升。
- **风险**: 报告体积增长（需裁剪/摘要策略）；无。

### 选项 D — plan-tracker 行状态机（一行一态，历史归档到 archive/近期完成）
- **目标**: 任务行只保留「当前状态」；历史演进（⚠️ 待重开→✅ 闭环）移入 最近完成/archive（**治理条款 D 类数据质量问题**）。
- **成本**: 中（模板/归档迁移 + 既有历史数据整理一次性投资）。
- **收益**: D3 消除；模型不再对同一任务做「哪个状态是最终态」判断；与本仓已知基线（行级快照滞后）同类治理。
- **风险**: 归档链路需完整（引用回查）；迁移期间双轨。

### 选项 E — 治理输出降噪开关（按模式分档）
- **目标**: always-on/silent-track 之外增加「lean 模式」：bootstrap 只做 resolve_entry 最小检查，plan-tracker/snapshot 按需读；session 级「治理开销预算」提示（如 >5% 命令时间则提示）。
- **成本**: 中-高（SKILL 流程分叉 + 教育成本 + 多模式组合矩阵）。
- **收益**: 直接响应用户「少干扰」诉求；D5/D8 间接缓解。
- **风险**: 治理闭环弱化（证据/风险过期检出变弱）；用户可能误配。

### 选项 F — 环境侧：pwsh 命令 UTF-8 显式化（非治理软件问题，但列入清单）
- **目标**: 读取含中文的 json 用 `-Encoding UTF8`（或 `[IO.File]::ReadAllText`），避免 mojibake（D6）。
- **成本**: 极低（模板/最佳实践条目）。
- **收益**: D6 消除（对目标项目自身排查含中文输出时尤其相关）。
- **风险**: 无。

---

## 7. 合规与红线确认

- `~/.dsh` **零写入**：本任务全部读取（read/grep/glob/pwsh 只读管道），未执行任何写/删/移动操作；原始 zstd 未解压至该目录；唯一文件写入为本报告。
- `.governance/` 零写入（证据材料目录为只读引用）。
- 目标项目代码/文件零修改（仅只读 `Get-Item`/`ReadAllText` 取 plan-tracker 尺寸与内容）。
- M7.7 红线：无对 `C:\Users\peter\.dsh` 或用户任何配置目录的写入/删除/清空/移动/重建。
- 本分析对 `C:\Users\peter\.dsh\profiles\...` 的引用均为 trace 内文本记录（只读取证），非实机操作。

---

## 8. 待验证项清单（无证据支撑/样本外）

| # | 事项 | 所需证据 | 优先级 |
|---|---|---|---|
| V1 | 用户感知的 verify 告警洪流 —— 需要样本外会话（17:07 之前 / 21:06 之后的会话 trace，或本仓 0.77.0 health 103 issues 是否出现在目标项目历史会话中） | 更多 session trace（zstd） | 高 |
| V2 | 「>50% 时间」的时间维度 —— trace 无耗时字段，无法从 token 推时间 | 用户在 DSH 面板的耗时统计或 API 计费明细 | 中 |
| V3 | token 精确换算 —— 未按目标模型 tokenizer 重算（字符占比为代理） | DSH 端 tokenize 统计 | 低 |
| V4 | 样本外的会话数/占比 —— 3 个会话是当天 3 个；全天会话数未知 | `C:\Users\peter\.dsh\sessions\--D-AI-agent-deepseek-plugins-thinking-dsh-reasoning-level--` 目录列表（zstd zip 列表，只读） | 中 |
| V5 | web-console 面板（S1 中运行中，PID 24908）是否在用户界面产生告警视觉 —— 无法从 trace 判断 | 用户描述/截图 | 低 |

---

## 9. 附：需 Coordinator 代跑的只读命令清单（可选深化）

本报告数字均已由本 Agent 直接计算（无待跑项）。仅当需要 V1/V4 深化时才需以下命令：

```powershell
# V4：列出目标项目会话目录内容（只读）
Get-ChildItem "C:\Users\peter\.dsh\sessions\--D-AI-agent-deepseek-plugins-thinking-dsh-reasoning-level--" | Select-Object Name,Length,LastWriteTime
# V1：若提供其他 zstd trace，解压至临时目录后按本报告 §1.2 口径重跑统计
```

（不纳入本报告输出硬依赖；报告不因这些命令缺失而欠完整。）
