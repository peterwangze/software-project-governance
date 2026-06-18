# 工作流"前提事实约束"盲区调研报告

- **任务**: AUDIT-117（Analyst 调研，Coordinator 派发）
- **调研日期**: 2026-06-18
- **事故锚点**: AUDIT-116（已全部回退）—— Coordinator 把前瞻性风险 RISK-038 误当活跃 bug，spawn Analyst+Architect 产出整套修复方案，但未在当前激活版本 0.54.1 上实测 `/governance` 是否真读错宿主状态。
- **特殊纪律**: 本报告调研的正是"agent 容易基于未验证前提作判断"的盲区。因此本报告每条结论附核实来源（文件:行号），推测显式标注【推测】，禁止假设历史范围。

---

## 调研 1：盲区历史发生范围（grep 核实）

### 方法

用 grep 实际查 `.governance/evidence-log.md`、`.governance/decision-log.md`、`.governance/risk-log.md`、`.governance/session-snapshot.md`、`docs/requirements/**`，搜索"未验证/未实测/未复现/前提/假设/误判/误以为/已回退/基于错误前提/桥接"等关键词。

### 实际找到的事件（按"基于未验证前提推进任务"的严格定义筛选）

| # | 任务 | 性质 | 一句话 | 来源 |
|---|------|------|--------|------|
| 1 | AUDIT-116 (2026-06-18) | **事故（已回退）** | Coordinator 基于"verify_workflow.py:17 代码行还在 ⇒ bug 还在"的未验证桥接推论，把已回退的 fast-start 风险 RISK-038 误当活跃 bug 处理；未在 0.54.1 实测 `/governance` 入口 | `.governance/session-snapshot.md:32`（"本会话曾基于错误前提尝试 AUDIT-116 并已全部回退"）、`.governance/evidence-log.md:5` EVD-587、`.governance/decision-log.md:7` DEC-080、`.governance/risk-log.md:7` RISK-038 |
| 2 | FIX-056 H5 假设 (2026-05-07) | **正例（盲区被正确处理）** | 需求澄清报告显式识别"agent-communication-protocol L104 基于未验证前提（Coordinator 能可靠判断超时）"；H5 假设（文件重叠率<5%）被显式标注+实际验证+证伪（实际远高于 5%）+修正方案 | `docs/requirements/FIX-056-agent-concurrency-requirement-clarification.md:151`（"基于一个未验证的前提"）、`:334`（未验证假设表）、`:344`（H5 验证结果 ❌ FALSE） |

### 不计入"基于未验证前提推进任务"的相关事件（边界澄清）

下列事件 grep 命中"误判/误报/已回退"等词，但**不属于 AUDIT-116 同类盲区**，为避免泛化特此排除：

| # | 任务 | 排除理由 | 来源 |
|---|------|---------|------|
| A | RISK-035 / DEC-071 (2026-05-31) | 是**验证器自身**把本地运行态文件误判为仓库产品文件，不是 agent 基于未验证前提推进任务；属于验证器边界缺陷 | `.governance/risk-log.md:10`、`.governance/decision-log.md:16` |
| B | Check 10 误报 (FIX-042 validation plan) | 是 M5 检查的**正则误报**（把 SKILL 文件表格问号识别为违规），不是 agent 判断错误 | `.governance/evidence-FIX-042-validation-plan.md:199` |
| C | FIX-067 G10/G11 弱代理判定 | 是 Gate 自动判定逻辑的**弱代理条件**问题，不是"基于未验证前提" | `.governance/review-AUDIT-099-full-project-audit-2026-05-12.md:39` |
| D | agent-locks.json 损坏误判无锁 | 是**数据损坏**导致的状态误读，不是基于未验证前提的主动判断 | `docs/release/rollback-plan-0.32.0.md:15` |

### 结论

- **严格意义上"基于未验证前提推进任务、事后发现前提不成立"的事故实例仅 1 处（AUDIT-116）**。
- **正例 1 处（FIX-056 H5）**：同类的未验证前提被 task 内部自我标注并验证。
- 历史记录中**没有发现第三处**符合"agent 主动基于桥接推论推进、事后证明桥接不成立"严格定义的事故。
- **不可泛化说"频繁发生"或"历史上多次出现"**——grep 核实只支持"至少 1 次事故 + 1 次正例"。
- 【推测】AUDIT-116 是首次被显式记录的此类事故，可能反映该盲区此前未被识别为独立类别，而非此前未发生过。此推测无法用现有治理记录证实或证伪。

---

## 调研 2：28 个 check 的实际检查内容与类型

### 方法

读 `skills/software-project-governance/infra/verify_workflow.py` 的 `cmd_check_governance`（:14386）实际调度的 check 列表，逐项核实。

### check 类型定义

- **(A) 结构/格式检查**：检查文件存在性、ID 顺序、表格结构、manifest 一致性等。
- **(B) 事后一致性检查**：在记录已写入后，检查证据完整性/Gate 一致/overclaim/审查覆盖等。
- **(C) 事前/前置检查**：在动作发生**前**拦截（如 commit 前、spawn 前）。
- **(D) 前提事实验证**：质询"你要修/声明的事是否被实测/复现"。

### check 清单表（来源：`verify_workflow.py:14397-15246` 及各 check 函数定义行）

| Check | 名称 | 实际检查内容(行号) | 类型 |
|-------|------|-------------------|------|
| 1 | Evidence Completeness | 已完成任务是否有 evidence 条目；归档任务热证据缺失归 INFO（`:14397` → `check_evidence_completeness()` `:9580`） | (B) 事后一致性 |
| 2 | Risk Staleness | 打开风险 >7 天未更新告警（`:14420` → `:9607`） | (B) 事后一致性 |
| 3 | Gate Consistency | Gate 状态与 evidence 是否匹配；orphan evidence（`:14440` → `:9630`） | (B) 事后一致性 |
| 4 | Evidence Quality | evidence 含"会话上下文"引用/循环引用/空输出（`:14466` → `:9820`，Check 1/2/3 在 `:9847-9862`） | (B) 事后一致性 |
| 5 | Protocol Compliance (M8) | DRI 唯一/conditional pass 有修复任务/evidence 必填字段（`:14494` → `:9688`） | (B) 事后一致性 |
| 6 | Tier Audit Completeness | 已完成 Tier 是否有审计证据（`:14533` → `:9932`） | (B) 事后一致性 |
| 7 | Commit-Task Traceability | 最近 20 commit 是否含 task ID 引用（`:14572` → `:10161`） | (B) 事后一致性（看历史 commit） |
| 8 | Risk Escalation Deadline | 打开风险是否过期 escalation（`:14594` → `:10225`） | (B) 事后一致性 |
| 9 | Task Deadline Enforcement | 活跃任务 plan_complete 是否过期（`:14608` → `:10286`） | (B) 事后一致性 |
| 10 | M5 AskUserQuestion Compliance | 源文件是否含内联问句指令；bootstrap/interaction-boundary 是否有 M5 规则（`:14622` → `:10720`，Check 1-4 在 `:10741-10941`） | (A) 结构/格式 |
| 11 | Manifest Consistency | manifest canonical 文件与磁盘文件是否一致（`:14652` → `:1140`） | (A) 结构/格式 |
| 12 | Cross-Reference Checking | 治理文件间引用是否 dangling/deprecated/circular（`:14678` → `:10941`） | (A) 结构/格式 |
| 13 | Sequential ID Checking | EVD/DEC/RISK/FIX ID 是否连续（`:14716` → `:11223`） | (A) 结构/格式 |
| 14 | Structural Validity | 治理文件表格结构有效性（`:14722` → `:11400`） | (A) 结构/格式 |
| 15 | Commit Scope Verification | 最近 20 commit 是否含"顺带"关键词/文件数>15（`:14751` → `:11577`，Check 1/2 在 `:11615-11619`） | (B) 事后一致性（看历史 commit） |
| 16 | Goal Alignment | evidence 是否含 `目标对齐:` 字段且≥30字符；重复模式（`:14773` → `:11914`） | (B) 事后一致性 |
| 17 | User Impact | evidence 是否含 `获得/感知/体验变化/迁移指南`；breaking change 无迁移指南（`:14807` → `:11992`） | (B) 事后一致性 |
| 18 | Fact Grounding (FIX-080) | evidence 是否含 `事实依据:` 字段且≥20字符；是否含"假设/猜测/推测/估计/大概/应该/可能/编造/幻觉"词（`:14838` → `:12165`，正则定义 `:12136-12142`） | (B) 事后一致性（文本格式） |
| 18b | Structured Evidence (FIX-083) | evidence 是否含 `结构化事实:` JSON；commands 数组字段是否合法（`:14858` → `:12324`） | (B) 事后一致性（文本格式） |
| 18c | AI Execution Packet (FIX-084) | 活跃 P0/P1 是否有 execution packet 且必填字段齐全（`:14879` → `:13491`） | (B) 事后一致性 |
| 18d-i | Product Success / Acceptance / Quality Budget / Vertical Slice / Deterministic Scaffolds / Interruption Policy (FIX-088~093) | 活跃 P0/P1 是否有对应契约且字段齐全（`:14900-15029`） | (B) 事后一致性 |
| 19 | Agent Team Review (SYSGAP-035) | 产品代码任务是否有 REVIEW- 证据；排除 degraded/self-review（`:15032` → `:13692`） | (B) 事后一致性 |
| 20 | Agent Activation (SYSGAP-036) | P0 跨层任务是否有 Analyst 激活证据（`:15052` → `:13779`） | (B) 事后一致性 |
| 21 | Review Debt (SYSGAP-042) | 有执行证据但无审查的任务（`:15070` → `:13949`） | (B) 事后一致性 |
| 22 | Review Coverage (FIX-037) | 产品代码任务审查覆盖率（`:15087`） | (B) 事后一致性 |
| 23 | Profile Consistency (FIX-038) | profile 声明与 Gate 表/任务表列数匹配（`:15105`） | (A) 结构/格式 |
| 24 | Version Consistency (FIX-052) | 所有版本声明是否与 SKILL.md 一致（`:15122` → `:9995`） | (A) 结构/格式 |
| 25 | Untracked Files (FIX-057) | git ls-files 未跟踪文件（`:15140`） | (A) 结构/格式 |
| 26 | Agent Lock Consistency (FIX-056) | agent-locks.json schema 有效性（`:15185`） | (A) 结构/格式 |
| 27 | Archive Integrity (SYSGAP-030) | 热任务+归档任务+index 一致性（`:15208`） | (A) 结构/格式 |
| 28 | Governance Review Fallback Policy (FIX-061) | `/governance-review` 是否禁止 Coordinator 自审回退（`:15231`） | (A) 结构/格式 |
| 28b | Projection Sync Guard (FIX-086) | source/target fixture/版本同步（`:15249` → `:6751`） | (A) 结构/格式 |
| 28c | Hot Fact-Source Consistency (FIX-087) | 项目配置/总览/活跃项/路线图/依赖链/需求矩阵是否对齐（`:15267` → `:1806`） | (B) 事后一致性 |
| 28d-h | Runtime Readiness / First-Session / Pack Registry / Context Discovery / README Pack / Mainstream Agent Loading（`:15281-` 后续） | 各专项 no-overclaim 一致性 | (B) 事后一致性 |

### 核心事实回答

**是否存在任何 (C) 事前/前置 check 或 (D) 前提事实验证 check？**

- **(C) 事前/前置 check：check-governance 子命令中 0 个**。`cmd_check_governance`（`:14386`）的所有 check 都在记录已写入后运行（`print` 输出 [PASS]/[WARN]/[FAIL]）。事前拦截发生在 **git hooks**（pre-commit/commit-msg，见调研 3），不在 check-governance 内。
- **(D) 前提事实验证 check：0 个**。没有任何 check 质询"你要修的 bug 是否在当前版本复现"、"你要声明的故障是否被实测"。最接近的 Check 18 Fact Grounding（`:12165`）只做**文本格式检查**：
  - 验证 `事实依据:` 字段存在且≥20字符（`:12180-12187`）
  - 用 `UNGROUNDED_CLAIM_RE`（`:12140-12142`）拦截**显式承认的推测词**（假设/猜测/推测/估计/大概/应该/可能/编造/幻觉）
  - **不验证事实是否真实支持结论**——只验证"是否写了事实依据字段"和"是否用了禁词"

### AUDIT-116 为何未被 28 check 拦截（事实分析）

- AUDIT-116 的桥接推论（"代码行还在 ⇒ bug 还在"）发生在 Coordinator spawn Analyst/Architect **之前**，是运行态判断，**不进入任何 evidence-log 的 `事实依据:` 字段**（因为还没到 commit/evidence 阶段）。
- 即使假设它进入 evidence：Check 18 的 `UNGROUNDED_CLAIM_RE` 不会命中——"代码行还在"是真实事实陈述，"bug 还在"是桥接结论，两者都不含禁词。
- 自检 SELF-CHECK #6（见调研 3）是自觉型，AUDIT-116 发生时 Coordinator 未触发自检。
- 28 check + SELF-CHECK #6 全部 PASSED 的事实，与"无 (C)/(D) 类 check"完全一致——**不是 check 失灵，是 check 范围不覆盖此类盲区**。

---

## 调研 3：现有最接近"前提验证/前置复现"的机制

### 机制清单（核实存在性 + 措辞 + 类型）

| # | 机制 | 存在 | 位置 + 原文措辞 | 自觉型 / 系统级 |
|---|------|------|----------------|----------------|
| 1 | CLAUDE.md SELF-CHECK #6 | ✅ | `CLAUDE.md:11`："我即将写入的修改/审查/证据是否都有事实依据？没有文件、命令、测试、日志、用户明确输入或外部文档支撑 → 不得写成事实。标为 BLOCKED / 待验证 / 未知，禁止假设、猜测、推测或编造。" | **自觉型**——靠 agent 自问自答，无任何工具/hook/check 强制执行该自问 |
| 2 | M7.4 任务完成协议 Step 1 | ✅ | `behavior-protocol.md:418-420`："产品代码/治理关键任务的证据说明 MUST 包含 `事实依据:`...禁止用假设、猜测、推测、估计、编造或幻觉作为闭环依据。" | **自觉型 + 事后文本检查**——M7.4 在 task 标记"已完成"时触发；`事实依据:` 字段被 commit-msg Step 12（见下行）系统级强制存在性，但"是否真实"不强制 |
| 3 | M7.5 任务前协议 | ✅ | `behavior-protocol.md:449-481` | **自觉型**——要求任务先入账（任务存在性），**不要求前提复现**；Step 2.6（`:472-479`）引用 change-impact-checklist Step 1-5 |
| 4 | change-impact-checklist Step 3.6 事实依据分析 | ✅ | `change-impact-checklist.md:40-46`："本次结论来自哪些持久事实？（列出文件路径、命令输出、测试结果、日志、用户明确输入或官方文档）...对无法验证的内容 MUST 写为 BLOCKED / 待验证 / 未知...禁止用假设、猜测、推测、估计、编造或幻觉作为闭环依据。事实依据缺失 → commit-msg hook BLOCK" | **半自觉半系统**——清单本身靠 agent 自觉执行（M7.5 Step 2.6 引用）；commit-msg Step 12 系统级强制 `事实依据:` 字段存在性，**但不验证事实真实性，也不要求"修复前先复现"** |
| 5 | commit-msg hook Step 12 Fact Grounding (FIX-080) | ✅ | `.git/hooks/commit-msg:341-392`："Step 12: Fact Grounding BLOCK...Checks evidence-log for 事实依据: field and [未落地推断词]...missing → BLOCK commit" | **系统级**——但强制的是**字段存在 + 无禁词**，**不验证事实真实性，不要求前提复现**；且仅对**产品代码 commit**触发（`is_product_code`），AUDIT-116 的调研/方案文档 commit 不触发 |
| 6 | pre-commit hook Step 7 产品代码审查证据 | ✅ | `.git/hooks/pre-commit:273`："Step 7: Product Code Review Evidence BLOCK (FIX-036)" | **系统级**——但强制的是**有 REVIEW- 证据**，**不验证被审查的 bug 是否复现** |
| 7 | systematic-debugging skill | ❌ 不在本仓 | 本仓 `skills/` 仅含 software-project-governance 套件 26 个 skill（`ls skills/` 核实），**无 superpowers、无 systematic-debugging**。systematic-debugging 是外部 superpowers 插件的 skill，不在本工作流治理范围。 | N/A——外部依赖 |
| 8 | governance skills 内"复现"措辞 | ✅（仅 prompt 文本） | `SKILL.md:156`（Debug/修Bug 路由："复现事实 + RCA 5-Why + 回归验证"）、`methodology-routing.md:9`（"复现问题 -> 定位直接原因 -> 5-Why -> 最小修复 -> 回归验证"）、`agent-failure-modes.md:161`（"故障处理顺序：遇到卡壳时先读取错误、搜索/检查事实、运行验证，再提出假设"）、`agent-communication-protocol.md:135/140/296`（defect report 含 repro steps） | **自觉型**——全部是 prompt 文本/路由表指令，无 check/hook 强制。且这些路由针对"Debug/修Bug 任务"，**AUDIT-116 不是修 Bug 任务，是"误把风险当 bug"的判断错误**，不进入这些路由 |
| 9 | git hooks 强制内容的边界 | ✅ | pre-commit Steps 0/6/7/8/9/10（`.git/hooks/pre-commit`）；commit-msg Steps 0/1/2/3/4/4.5/5/10/11/12/13/14（`.git/hooks/commit-msg`）；post-commit（存在） | **系统级强制的实例**——但强制内容是：hook 自升级、CLAUDE.md 改动纪律、task ID 引用、evidence 存在性、目标对齐、用户影响、事实依据字段、breaking change 迁移指南、审查证据。**没有任何 hook 强制"前提已复现"** |

### 核心事实结论

- **现有机制中没有一个是 (C) 事前强制或 (D) 前提复现验证的系统级机制**。
- 最接近的 Step 3.6 + commit-msg Step 12 是**半自觉半系统**：清单靠 agent 自觉执行，hook 强制字段存在性，但两者都**只验证"是否写了事实依据"和"是否用了禁词"**，**不验证"事实是否真的支持结论"**。
- AUDIT-116 的桥接推论"代码行还在 ⇒ bug 还在"满足所有现有约束：
  - 事实（代码行存在）真实 → `事实依据:` 可写真实文件路径
  - 结论（bug 还在）不含禁词
  - 它发生在 spawn 前，不进入任何 evidence/commit，所以连字段存在性检查都不触发
- **现有最接近的机制全部自觉型或事后型，没有一个能在 spawn 前/动作前拦截 AUDIT-116 这类盲区**。

---

## 调研 4：可机械验证的"前提已复现"信号（前瞻探讨）

> **本节大部分内容为【推测】**。基于调研 2/3 的事实，探讨可行性，严格区分"现有代码已支持（事实）"和"需要新增（推测）"。本节不设计 check/方案——设计留给 Architect。

### 现有代码已支持的结构（事实）

- **`结构化事实:` JSON 的 commands 数组**（FIX-083，`verify_workflow.py:12279-12298`）已支持结构化命令证据，每条 command 含 `cmd / exit_code / summary / log_path` 字段。**这是机械可解析的**。
- **execution packet 的 `next_commands` 字段**（FIX-084，`:12371`）已存在。
- **Check 18 Fact Grounding 已能机械区分"有/无 `事实依据:` 字段"和"有/无禁词"**（`:12165`，正则 `:12136-12142`）。

### 现有代码不支持的结构（事实）

- commands 数组**无"命令语义"字段**——无法区分一条 command 是"复现 bug 的命令"、"修复后验证的命令"、还是"普通构建命令"。`_validate_structured_fact_payload`（`:12274`）只验证 `cmd/exit_code/summary` 类型，不验证语义。
- 没有"修复前复现证据"字段——现有结构无法表达"我在修复前运行了 X 命令，观察到 Y 故障输出"。
- 没有任何机制表达"前提结论的桥接"——即"事实 A ⇒ 结论 B"中，A 与 B 之间的逻辑链是否被验证。

### 【推测】可能的机械验证方向（仅供 Architect 后续探讨，不设计）

> 以下每条均为【推测】，标注理由。本报告不产出 check/方案设计。

- 【推测】**为修复类任务（如 FIX-/AUDIT- 类）增加"复现证据"结构化字段**——例如 `reproduce_before: {command, observed_failure, exit_code}` 与 `reproduce_after: {command, observed_pass, exit_code}`。
  - 推测理由：现有 commands 数组已机械可解析，扩展一个语义字段在技术上是 verify_workflow.py 可消费的。
  - 推测局限：(a) 无法机械验证"observed_failure 真的是 bug 而非噪音"；(b) 对于"误把风险当 bug"这类**判断错误**（非代码 bug），没有"复现命令"可言——AUDIT-116 根本不是一个可复现的代码 bug，它是 Coordinator 的推理错误。机械验证对判断类错误的覆盖度有限。
- 【推测】**为 spawn 决策增加"前提验证 gate"**——即 Coordinator spawn Analyst/Architect 产出方案前，必须先记录"我声称要解决的问题是 X，X 在当前激活版本的复现证据是 Y"。
  - 推测理由：M7.5 任务前协议（`behavior-protocol.md:449`）已存在"动作前 gate"模式，可扩展。
  - 推测局限：(a) 这是自觉型 gate，除非有 hook/系统强制，否则仍可绕过；(b) 如何判断"哪些 spawn 需要前提验证"本身是判断问题，可能引入新的误判。
- 【推测】**SELF-CHECK #6 升级为系统级强制**——例如在 Coordinator spawn 任何 P0 任务前，要求 evidence-log 写入"前提验证"行。
  - 推测理由：SELF-CHECK #6（`CLAUDE.md:11`）当前是自觉型，AUDIT-116 发生时未触发；若有系统级强制可补此缺口。
  - 推测局限：(a) 系统级强制"自问"在技术上难以实现——hook/check 无法读取 agent 的内部推理过程，只能读取其外部产出；(b) 最可能落地的形态仍是"要求某个外部产出字段"，回到上一条方向。

### 【推测】反直觉观察

> 本节为【推测】。

【推测】AUDIT-116 的根本难点**不是"缺少复现机制"**——因为 AUDIT-116 描述的 bug（RISK-038，`/governance` 读错宿主状态）在当前 0.54.1 **确实不存在可复现的载体**（fast-start 已物理回退）。所以即使有"修复前先复现"check，Coordinator 也会发现"无法复现"——而"无法复现"在当前心智下容易被解读为"bug 隐藏很深/需要更复杂的复现"，而非"bug 可能根本不在当前版本"。**真正的盲区是"无法复现 ⇒ bug 不在当前版本"这个反向推论没有被任何机制鼓励**。此推测无法用现有代码证实，仅作 Architect 后续探讨参考。

---

## 附录：待 Architect 后续探讨的方向

> 本附录全部为【推测】，仅供 Architect 参考，不构成需求或方案。

- 【推测】盲区类别化：是否应把"基于未验证前提推进任务"作为独立 failure mode 纳入 `agent-failure-modes.md`（当前文件不含此类别，`grep "前提|未验证"` 核实）。
- 【推测】check 覆盖度补强：是否应在 28 check 中增加 (D) 类前提事实验证 check，以及该类 check 在"判断类错误"（非代码 bug）场景下的可行性边界。
- 【推测】审计框架 D 维度：`core/audit-framework.md`（未在本报告核实范围内）是否已有针对"前提验证"的审计维度，若有则评估覆盖度，若无则评估新增必要性。
- 【推测】历史正例复用：FIX-056 H5 的"显式标注未验证假设 + 实际验证 + 证伪 + 修正"模式（`docs/requirements/FIX-056-agent-concurrency-requirement-clarification.md:334-357`）是否可提炼为通用模式推广到所有 P0 任务。

---

## 报告自检

- [x] 调研 1：grep 核实，仅 1 处事故（AUDIT-116）+ 1 处正例（FIX-056 H5），未泛化
- [x] 调研 2：28 check 全部读 `cmd_check_governance`（`:14386`）核实，附行号；明确回答"无 (C)/(D) 类 check"
- [x] 调研 3：9 项机制逐一核实存在性+措辞+类型，区分自觉型/系统级
- [x] 调研 4：现有支持（事实）与需新增（【推测】）严格分开；不设计 check/方案
- [x] 每条事实附来源（文件:行号）；所有推测显式标注【推测】
- [x] 未修改任何产品代码（skills/agents/commands/infra/.claude-plugin）
- [x] 未与用户直接交互
