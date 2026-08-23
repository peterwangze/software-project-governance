# FIX-263 — REQ-145.1~145.7 看护模式统一设计

- **Task ID**: FIX-263（P0，纯设计，禁止改产品代码/infra/hooks/.governance）
- **设计日期**: 2026-08-22（本仓当前时间，与诊断报告一致）
- **执行者**: Architect sub-agent（Governance 快速通道，只读调查 + 单文件设计文档）
- **权威输入**: `docs/requirements/audit-145-watchdog-gap-0.76.0.md`（诊断报告，必读全文；§1-§5 五问机制现状+缺陷断点+候选方案 R-D1a~R-D5c，§6 差距清单 G1-G13，§7.1 REQ 级七项含验收信号）。§7.2 项目侧探针**已由用户裁决排除**，本设计一律不纳入。
- **唯一写操作**: `docs/requirements/audit-145-watchdog-design-0.76.0.md`（本文件）。
- **版本基线**: 本仓 active_version=0.75.0（SKILL.md frontmatter），verify_workflow.py = 21250 行单文件（已验证）。所有零改动决策须在 0.76.0 承载（见 §4 发布链）。
- **修订记录**: **R0** = 初版（2026-08-22）。**R1** = 按 Design Reviewer R0（`.governance/review-FIX-263-DESIGN-R0.md`，NEEDS_CHANGE，3 P1 + 5 P2）修订——消纳 F1-F8，P3（F9-F14）登记处置意见（见本任务交付摘要）。

> **文档性质**：本文件是**方案级设计建议**。凡标注「**决策返 Coordinator**」的为未做最终抉择的设计建议；凡标注「**建议**」的为带依据的推荐；唯一需要在 0.76.0 落地的只是「建议」中已具备充分证据、且无更高层竞争决策的部分。本设计不替代任何 ADR —— 如需 ADR 请由 Coordinator 后续触发。

---

## 0. 设计范围与硬门槛自检

### 0.1 范围

| 项 | 值 |
|---|---|
| 覆盖 | REQ-145.1~145.7 全部七项 |
| 修改文件 | **仅新增** `docs/requirements/audit-145-watchdog-design-0.76.0.md` |
| 禁止 | 改任何产品代码/infra/hooks/.governance/既有文档；不修改 plan-tracker/evidence-log/risk-log；不做最终决策 |
| 约束处理 | (a) DSH persona 预算 1535/1536 字节；(b) verify_workflow.py 21k 单文件 vs `infra/checks/` 域拆分层；(c) FIX-264~269 串行执行序 + merge 顺序 |

### 0.2 自检硬门槛（执行前逐项核验）

| 门槛 | 达成 |
|---|---|
| 1. 纯设计：未改产品代码/infra/hooks/.governance，仅写本文件 | ✅ |
| 2. 每个设计决策带依据（引用诊断报告节/行号或代码事实）；无依据标为假设 | ✅ 见各节「依据」行 |
| 3. 覆盖全部 7 项 REQ 验收信号；每个 check 含误报面分析 | ✅ §3 每节含「误报面分析 + 豁免」 |
| 4. 明确 WARN/FAIL 语义与渐进路径（不回避 severity 决策） | ✅ 每节含「WARN/FAIL 语义」 |
| 5. 不做最终决策（方案级，决策返 Coordinator） | ✅ 每节含「决策返 Coordinator」 |

---

## 1. 总体设计框架

### 1.1 七项 REQ 与实现任务映射对齐

诊断报告 §7.1 给出的七项 + 任务上下文给出的实现任务拆分（FIX-264~269）：

| REQ | 内容 | 实现任务 | 改动面 |
|---|---|---|---|
| REQ-145.1 | bootstrap 健康摘要（M4.1 增一步运行 `check-governance --summary-only`） | FIX-264（与 145.7 合并） | 非 check 模块：behavior-protocol M4.1 + SKILL.md + AGENTS/CLAUDE + DSH persona bootstrap 步 |
| REQ-145.7 | `--summary-only` 精简入口子命令 | FIX-264 | verify_workflow.py `main()` + `cmd_check_governance` 尾部 + 汇总/采集器 |
| REQ-145.2 | 新增 Check 35 `check_snapshot_freshness` | FIX-268 | `infra/checks/snapshot_domain.py`（新域）+ verify_workflow.py 薄再导出 + cmd_check_governance 新 Check 块 |
| REQ-145.3 | 新增 `check_risk_mitigation_closure` | FIX-265 | `infra/checks/risk_domain.py`（已有域，扩展）+ 薄再导出 + cmd_check_governance 新 Check 块 |
| REQ-145.4 | `check_release_readiness` 内嵌 `check_gate_sequence_for_release` | FIX-266 | `infra/checks/gate_domain.py`（新域）+ `check_release_readiness` 调用点 + 独立 Check 块 |
| REQ-145.5 | 新增 `check_ci_evidence` | FIX-267 | `infra/checks/ci_domain.py`（新域）+ 薄再导出 + cmd_check_governance 新 Check 块 |
| REQ-145.6 | 能力分级声明 + L7 改写建议 | FIX-269 | **纯文档**：SKILL.md + commands/governance.md + plan-tracker L7（仅建议措辞，不改写） |

> **任务上下文映射核对（§8 问题 8）**：FIX-264（145.1+145.7）/FIX-265（145.3）/FIX-266（145.4）/FIX-267（145.5）/FIX-268（145.2）/FIX-269（145.6）与模块归置匹配度**高**——三项新增 check（145.2/145.4/145.5）与一项扩展（145.3）落在同一类域拆分模块，仅 FIX-264 跨「引擎改动（145.7）+ 流程集成（145.1）」两种性质，详见 §2.3（约束 c）。
> **更优拆分建议（仅建议，不改变任务表）**：FIX-265（145.3 风险缓解闭环）、FIX-268（145.2 快照新鲜度）、FIX-266（145.4 Gate 互锁）、FIX-267（145.5 CI 证据）四个均为**互相独立的新增/扩展 check 域**，两两无强制依赖。FIX-265（risk_domain.py 扩展）复用的共享名（`RISK_PATH`/`_context_file`/raw `split("|")` 索引）**已全部在 risk_domain.py 内**（Check 2/8 同文件），FIX-265 **不依赖 FIX-268 新建的 snapshot_domain.py**。因此四个 check 域可任意互换，**单一权威串行顺序见 §2.3 执行表（264→265→268→266→267→269）**——本小节不再给出与 §2.3 冲突的独立顺序。

### 1.2 三个跨切面设计原则

1. **内容维度看护优先于时间维度**：既有 Check 2/8 是「时间维度」看护（>7 天 / 截止已过），AUDIT-145 的核心缺陷是「写缓解即完成」无内容断言。本次新增 check 一律以**内容维度**（缓解落地 / 快照新鲜 / Gate 互锁 / CI 实跑）为准，时间维度只作为 WARN→FAIL 的渐进阈值辅助信号（§3.3/§3.6）。
2. **只读优先 + fail-safe**：新 check 全部只读 `.governance/` 与 git 查询，不写任何状态；任何解析失败（文件缺失 / 外来数据 ragged / git 不可用）**fail-safe 到 WARN 或 no-verdict**，绝不误报 FAIL（R-AUDIT-145 §6 第 10 条 tv Check 31 因 ragged 而 BLOCKED 的教训）。
3. **复用既有解析器，不重复造轮**：优先复用 `_governance_table_cells`、`parse_gate_status`、`_latest_published_release_fact`、`task_priority.py` 状态判定、`_TASK_ID_IN_REF_RE`、`_parse_snapshot_date`/`FIX_105_SNAPSHOT_DATE_RE`。仅当既有解析器语义与需求冲突时才扩展（如 risk 状态机需从「仅打开」扩为「非已关闭」，§3.3）。

---

## 2. 三个设计约束的结论

### 2.1 约束 (a)：DSH persona 预算 1535/1536 字节

**事实**：`adapters/dsh/agent.cordis.yml.template` 本身无全局字节上限（agent-instructions 行 `maxBytes: 65536`），但 `infra/tests/test_review_machine_provenance.py:227-236` 的 `test_persona_contract_block_stays_within_budget` 显式断言：从「关键行为契约」到「Git hooks」之间的契约块 **≤ 1536 字节**。当前该块恰在预算边界（FIX-253/FIX-260 先例，README/release-checklist-0.75.0 标注 1.5KB 预算）。

**设计结论（约束 a）**：

| 方案 | 描述 | 结论 |
|---|---|---|
| A1：健康摘要进 persona「关键行为契约」块 | 把「每会话跑 `check-governance --summary-only`」写入契约块 | **否决**——该块已 1535/1536 字节，再注入必超预算；且健康摘要是「动作步骤」而非「行为契约」，语义不匹配 |
| A2：健康摘要进 persona bootstrap 步（第 1-3 步之后） | 在 persona「每会话第一动作」指引后加第 4 步 | **可选**，但不推荐——bootstrap 步虽不在 1536 预算内，仍消耗 persona 正文；且 DSH 宿主差异大，需三档 profile 分别维护 |
| **A3（推荐）：不进 persona，进 SKILL.md + behavior-protocol M4.1** | persona 已强制「第 1 步调用 `skill` 工具加载 SKILL」；SKILL.md 因此**每会话必然被加载**，在 SKILL.md 的 Coordinator bootstrap / behavior-protocol M4.1 增「健康摘要」步骤即可 | **推荐**——零 persona 字节占用，复用 SKILL 每会话加载的事实；符合 persona「规则放仓库 SKILL，persona 只给身份 + 确定性第一动作」的设计定位（agent.cordis.yml.template L8-15 注释） |

**A3 的修改面**（不进 persona）：
- **SKILL.md**：把「每会话第一动作」扩展为含「运行 `python <plugin_root>/skills/software-project-governance/infra/verify_workflow.py check-governance --summary-only`（DSH 支持 CLI）并读取 `Governance: {N} issues` 摘要 + 首个 FAIL/WARN 项」。
- **behavior-protocol.md M4.1**：会话开始协议第 1-4 步之后增「4.5 健康摘要（R-D1a）：运行 `check-governance --summary-only`，按摘要驱动后续动作（FAIL 级直达用户 / WARN 记录 / PASS 无动作）」。
- **AGENTS.md / CLAUDE.md 模板**：仅当 profile 差异化要求「host 项目模板携带摘要步骤」时才同步（见下「profile 差异化」）。
- **DSH / 其他宿主差异**：DSH 下 SKILL 每会话随 persona 第 1 步调用而加载，**无需改 launch.py 生成 persona**（A3 的「persona 不变」指「关键行为契约块」与「健康摘要步骤」不进 persona；**persona 的版本锚 `agent.cordis.yml.template L33 v0.75.0` 仍属发布链**，须随 0.76.0 bump——该锚在「关键行为契约→Git hooks」的 1535 字节块之外，bump 不触碰预算，见 §4.1）；非 DSH 宿主（Claude/Codex/Gemini）若平台入口文件（AGENTS/CLAUDE）不走「首步加载 SKILL」，则需在该平台入口文件 bootstrap 段补摘要步骤——**此为各宿主投影差异，交由适配层处理，非本设计范围**（建议）。
- **只读优先**：摘要显示但**不阻断**（G1/G2 修复）。FIX-254 / DEC-143 已确立「只看门禁不打断」的交互基线：摘要仅在 FAIL 级时触发用户关注（M5.4b 纯通知结构），WARN 记入会话上下文不打断。

**Profile 差异化三档**：轻量（lightweight）/标准（standard）/严格（strict）对应 gate 计数与任务列不同（verify_workflow.py `_PROFILE_GATE_COUNT` 12879-12888）。健康摘要步骤**不按 profile 拆分逻辑**——三档都跑同一个 `--summary-only`，但**输出详略**可按 profile 调节（轻量只输出汇总行 + 首个 FAIL；标准输出汇总 + 首个 FAIL/WARN；严格输出全部 check 段）。该「详略分档」**建议**由 `--summary-only` 的 `--level` 参数承载（见 §3.1 契约），进 SKILL.md 但**不进 persona**。

**决策返 Coordinator**：
- 确认 A3（进 SKILL/M4.1，不进 persona）。
- 确认健康摘要在 FAIL 时的用户触达方式：是「仅展示（M5.4b 纯通知）」还是「FAIL 级强制 ask_user_question」。本设计建议前者（只读优先 + 不打断），但此为用户交互边界决策，返 Coordinator。

### 2.2 约束 (b)：verify_workflow.py 21k 单文件 vs `infra/checks/` 域拆分层

**事实**：verify_workflow.py = 21250 行（已验证）。`infra/checks/` 已是成熟域拆分层，先例为 manifest.py（0.59.0）、capability_registry.py（0.61.1）、evidence_domain.py（0.70.0）、risk_domain.py（0.70.0）、review_domain.py（0.70.0）。所有域模块遵循同一「薄再导出」模式：verify_workflow.py 用 `from checks.<domain> import (...)` 拉回（risk_domain 见 verify_workflow.py:1109-1116），域模块用 `_vw()` 延迟访问器 + `_resolve_shared()` 回取共享名（risk_domain.py:32-75），返回**受结构约束的 dict 结果**而非直接 print。

**设计结论（约束 b）**：

| 改动 | 归置 | 理由 |
|---|---|---|
| `--summary-only`（REQ-145.7）| **留在 verify_workflow.py**（`main()` 参数 + `cmd_check_governance` 尾部汇总） | 这是「引擎调度/汇总」逻辑，非新 check 域；且对既有输出路径零回归的需要使其与既有 print 代码同处。新增一个 `_aggregate_check_summary()` 辅助即可，不拆域 |
| bootstrap 健康摘要（REQ-145.1）| **不进 verify_workflow.py**——是流程步骤，进 SKILL/M4.1（见 §2.1） | |
| 新 Check 35 `check_snapshot_freshness`（REQ-145.2）| **新域** `infra/checks/snapshot_domain.py` + 薄再导出 | 快照新鲜度是独立域，mirror risk_domain.py 模式 |
| `check_risk_mitigation_closure`（REQ-145.3）| **扩展既有域** `infra/checks/risk_domain.py` | 该域已拥有 Check 2/8 + `parse_open_risks`；缓解闭环属同域 |
| `check_gate_sequence_for_release`（REQ-145.4）| **新域** `infra/checks/gate_domain.py` + `check_release_readiness` 内嵌调用点 | 让既有 `check_release_readiness`（verify_workflow.py:6664）保持聚合入口，子检查职责外置到域，避免继续膨胀主文件；也降低与现有 gate 解析的耦合 |
| `check_ci_evidence`（REQ-145.5）| **新域** `infra/checks/ci_domain.py` + 薄再导出 | CI 证据是独立域，需新增 git remote/workflow 探测 |

**「主文件 vs 域拆分」的判据**：凡新增**新 check 规则**（有独立验收信号、独立误报面）→ 域拆分；凡**修改既有命令的调度/汇总/参数**→ 主文件。
**域模块的薄再导出 + cmd_check_governance 新增 Check 块**：新增域函数须按风险域先例在 verify_workflow.py 用 `from checks.<domain> import check_x` 拉回，然后在 cmd_check_governance 的对应序号块调用并 print 摘要——保持与 Check 34（check_completion_recommendation，verify_workflow.py:14343-14361）相同的「调用 + 判定 + print」结构。

**决策返 Coordinator**：确认「新增 check 一律走域拆分，`--summary-only` 走主文件」的边界。这是既有 DEC-083 域拆分路线（0.59.0~0.70.0）的自然延续，中等确定度，建议采纳。

### 2.3 约束 (c)：FIX-264~269 串行执行序与 merge 顺序

**事实**：FIX-264~268（除 269）均改 `verify_workflow.py`（诊断报告与任务上下文均确认真重叠）。三处改动可能冲突：
1. `--summary-only`（FIX-264，REQ-145.7）改 `main()` + `cmd_check_governance` 尾部汇总区；
2. 各新 check 在 `cmd_check_governance` 追加新 Check 块 + 薄再导出 import 区；
3. `check_risk_mitigation_closure`（FIX-265）在 `risk_domain.py` 扩展 `check_risk_staleness/escalation` 同域函数（复用同文件已有的 `line.split("|")` parts 索引与 `RISK_PATH`/`_context_file` 共享名，**不再引入 `_governance_table_cells`**——F6 锁 raw split）。

**设计结论（约束 c）**——串行执行序（每步先 merge 前一步，再改，再验证 `check-governance` 无新 FAIL）：

| 序号 | FIX | REQ | 改动点 | 依赖 | 理由 |
|---|---|---|---|---|---|
| 1 | **FIX-264** | 145.7 + 145.1 | `main()` 加 `--summary-only` 参数 → `cmd_check_governance` 尾部增 `_aggregate_check_summary()` → 复核既有全量输出零回归 → (145.1) 改 SKILL/M4.1 | 无 | 先建引擎侧，后接集成；145.1 依赖 145.7 存在 |
| 2 | **FIX-265** | 145.3 | `risk_domain.py` 扩展 `check_risk_mitigation_closure` | **无**（不依赖 FIX-268）| `_governance_table_cells` 共享名已在 risk_domain.py 的 `_SHARED_NAMES`（L53-58），独立可行；域内解析器直接复用 Check 2/8 的 `line.split("|")` parts 索引 |
| 3 | **FIX-268** | 145.2 | 新建 `checks/snapshot_domain.py` + 薄再导出 + cmd_check_governance Check 块 | 无 | 复用 Check 28c/34 的快照解析器（FIX_105_SNAPSHOT_DATE_RE），独立域 |
| 4 | **FIX-266** | 145.4 | 新建 `checks/gate_domain.py` + `check_release_readiness` 内嵌调用点 | 无 | 独立域；不影响其它 check |
| 5 | **FIX-267** | 145.5 | 新建 `checks/ci_domain.py` + 薄再导出 + cmd_check_governance Check 块 | 无 | 独立域；需 subprocess git（与 release/projection.py:20-30 先例同构） |
| 6 | **FIX-269** | 145.6 | SKILL.md + commands/governance.md 能力分级声明 + plan-tracker L7 建议措辞 | 无 | 纯文档，最后做（不碰代码） |

**merge 顺序要点**：
- 所有改动集中在 `verify_workflow.py`（`main()`、`cmd_check_governance`、import 区）与 `infra/checks/*.py`。两个 FIX 同时改同一行区间（如都往 cmd_check_governance 尾部追加 Check 块）——**merge 冲突高发**，因此强制**串行**（每次只开放一个 FIX 的验证分支），不可并行（§并行调度安全 M7.6）。
- 每步 merge 后 MUST 跑 `python skills/software-project-governance/infra/verify_workflow.py check-governance`，确认既有的 Check 1-34 零新增（不引入回归）、新 check 红→绿夹具通过。
- `__version__`/REQUIRED_SNIPPETS 中的硬编码版本若受任一 FIX 影响，须最后统一 bump 到 0.76.0（见 §4 发布链）。

**决策返 Coordinator**：确认上述串行执行序（**264→265→268→266→267→269**）与「不并行改 verify_workflow.py」。该顺序与任务表 FIX-264~269 的数字顺序不同（FIX-265 提前、FIX-268 居中），是**为消除重叠而做的串行化建议**（四个 check 域两两独立、无强制依赖，故 FIX-265 可提前），返 Coordinator 决定是否采纳。

---

## 3. 七项 REQ 逐一设计

### 3.1 REQ-145.1 + 145.7 — bootstrap 健康摘要 + `--summary-only`

#### 模块归置
- `--summary-only`：**verify_workflow.py**（`main()` 加 `--summary-only` 参数，`cmd_check_governance` 尾部汇总区）。
- bootstrap 健康摘要：**behavior-protocol.md M4.1** + **SKILL.md**（不进 persona，见 §2.1 A3）。

#### `--summary-only` 输出契约

| 字段 | 格式 | 说明 |
|---|---|---|
| 汇总行 | `Governance: {N} issues` | N = 全量 check 累计的 FAIL/violation 数（与全量跑 `Result: ISSUES FOUND — N issue(s)` 的 all_issues 同源，verify_workflow.py:14365-14368）；**N=0 时输出 `Governance: [PASS]`**（对齐 §7.1 验收信号字面「无 issue 时输出 `[PASS]`」，诊断报告 L284）|
| 首个 FAIL/WARN 项 | `[FAIL] <check 名>: <首条详情>` 或 `[WARN] <check 名>: <首条详情>` | 只输出**第一个** FAIL；无 FAIL 但存在 WARN 时输出第一个 WARN；两者皆无则不输出详情行 |
| 附加行 | `[ADVISORY] Check 28s: governance files N ERROR, 0 WARN` | 可选——advisory（fatal_on_error=false）类 issue 在汇总行**不计数**（与全量跑一致，verify_workflow.py:14114-14126），仅当首个 issue 为 advisory 时附注 |

#### 与全量跑的关系：复用同一引擎 vs 轻量扫描（决策点）

**事实**：`cmd_check_governance`（verify_workflow.py:13049-14373）是**单函数内联 print** 的 34 段检查——每段直接 `print("┌─ Check N ...")` 并累加 `all_issues`，只对少数检查（1/2/8/30/30c/34 等）先调用返回 dict 的 check 函数再 print。**不存在**「跑完全部 check 返回结构化计数」的抽象。

| 方案 | 描述 | 运行成本 | 零回归 | 推荐度 |
|---|---|---|---|---|
| 复用同引擎（捕获输出）| 在**同一进程**调用既有 cmd_check_governance 逻辑，用 `contextlib.redirect_stdout` 捕获，从捕获文本用正则提取 `Result: ISSUES FOUND — N` + 首个 `[FAIL]/[WARN]` 行，再打印 `Governance: {N} issues` + 首个 FAIL/WARN | = 全量引擎运行（几秒） | **强**（不改既有 print 代码） | ★★★ 建议 |
| 复用同引擎（collector 重构）| 重构 cmd_check_governance，把 `all_issues` 改成一个 `issues[]` 结构，`--summary-only` 时 suppress 详情 print、只用 `issues[]` 打印汇总 | = 全量引擎运行 | 中（动 print 代码，需回归） | ★★ 备选 |
| 轻量扫描（只跑 FAIL 倾向 check）| 只运行「门禁精简面」子集（如执行门禁类），跳过繁重 WARN/审计 check | **秒级**（最快） | 弱（是另一套语义） | ★ 长线（0.77+）|

**建议**：采用**「复用同引擎（捕获输出）」**作为 0.76.0 基线——它同时满足「复用同一引擎」「对既有输出路径零回归」「摘要稳定（正则锚定稳定格式）」三项，且无需重构 34 段 print。

**性能预算（F8 明确承诺）**：验收信号 §7.1 字面要求「秒级」。0.76.0 的**设计级承诺 = 「秒级」**，即 `--summary-only` 的墙钟耗时与既有全量 `check-governance` 引擎相同（因它复用同一引擎、不改变计算量，只减少输出体积）。**可行性依据**：诊断报告 §1.1/§8 已实测本仓 `check-governance` 可在秒级跑完（Check 30/30c 是大文件循环，是 dominant cost，但本仓实测 66/40/137 issues 均在秒级出结果——即引擎本身耗时已在秒级量级）。因此「复用同引擎=秒级」成立。**验收门禁**：在 0.76.0 的 `check-governance --summary-only` 真机 CI/会话测得墙钟 <15s（对齐 `SPG_RESOLVE_TIMEOUT` 量级）即过门禁。
**若「硬性 <1s」为不可协商要求**：则改为轻量扫描，新增独立的 `--quick-scan` 子集（只跑 Check 1/2/8/30/30c/34 + 五个新 check 的判定函数），该方案改变引擎语义、牺牲「复用同一引擎」原则，**作为 0.77+ 选项返 Coordinator**。0.76.0 不承诺 <1s。

**对既有输出路径零回归的保证方式**：`--summary-only` 是一个**互斥新参数**——缺省（不传）时路径与现状**逐字节一致**（零改动）；传 `--summary-only` 时才进入捕获/汇总分支；捕获分支不写任何文件、不改任何全局状态。通过「缺省路径零 diff」＋「`check-governance`（无参）既有 34 段输出做快照 diff 测试」双重保证。

**函数边界**：
- 新增 `_aggregate_check_summary(stdout_text) -> dict`：入参为全量输出文本，出参 `{issues_count, first_fail, first_warn, advisory}`（均为 None 或缺省时为空）。负责正则提取 + 首个项定位。
- `cmd_check_governance(args)`：当 `args.summary_only` 为真时，`with redirect_stdout(buf): _run_full_engine_checks()`（把原函数体抽到 `_run_full_engine_checks()`），然后调用 `_aggregate_check_summary(buf.getvalue())` 打印摘要——**主体函数体不动**，仅外包一层。

**输入/输出契约**：
- `--summary-only` 入参：无额外必入参；可选 `--level lightweight|standard|strict`（详略分档，缺省 standard）。
- 成功：exit 0，stdout `Governance: {N} issues` 或（N=0）`Governance: [PASS]`（可选 + `[FAIL]/[WARN]` 行）。
- `--fail-on-issues` 与 `--summary-only` 同用时：仍以大写 N>0 触发 exit 1（复用既有 `args.fail_on_issues` 逻辑）。

**WARN/FAIL 语义**：`--summary-only` 是**展示**而非**阻断**（只读优先）。不因方式本身引入新 severity——severity 完全由被调用的各 check 决定（本摘要不带任何独立判定）。

**误报面分析**：
- 正则锚定 `Result: ISSUES FOUND — (\d+) issue(s)` 与 `│  [FAIL]`/`│  [WARN]` 行——若未来某 check 改 print 格式，正则失配 → 摘要缺项。豁免：用宽松正则 + fail-safe（格式漂移时输出 `Governance: N issues (parse degraded)`，不报错）。
- 首个 FAIL/WARN 的「首」依赖 check 执行顺序——顺序由 cmd_check_governance 固定（1→34），稳定。
- DSH 中 `pwsh` 运行该命令 stdout 可能含 GBK 转义残留——豁免：`--summary-only` 复用 cmd_check_governance 的 `sys.stdout.reconfigure(utf-8)`（verify_workflow.py:13052），摘要行用 ASCII 标记（`Governance:`/`[FAIL]`）规避编码问题。

**故障模式 + fail-safe**：
- verify_workflow.py 未定位（模块缺失）→ 摘要步骤 fail-closed：SKILL/M4.1 指示「若 `check-governance` 不可运行，则显示 `Governance: unavailable` 并继续 bootstrap，不阻断（fail-safe 到简报而非硬失败）」。
- 运行超时（>15s，`SPG_RESOLVE_TIMEOUT` 先例）→ 软超时取消该步，输出 `Governance: timed out`，继续会话。
- 解析失败 → `Governance: N issues (parse degraded)`。

**决策返 Coordinator**：「复用同引擎（捕获输出）」vs「轻量扫描」；AGENTS/CLAUDE 模板是否同步；FAIL 触达方式（仅展示 vs 强制问）。

---

### 3.2 REQ-145.2 — Check 35 `check_snapshot_freshness`

#### 模块归置
**新域** `infra/checks/snapshot_domain.py` + verify_workflow.py 薄再导出 + cmd_check_governance 新 Check 块（Check 35，紧接现有 Check 34 之后，verify_workflow.py:14361 之后）。

#### 函数边界
`check_snapshot_freshness(plan_content=None, snapshot_text=None, evidence_mtime=None, commit_date=None)` -> dict。

入参（均可选，便于测试注入 fixture；缺省走 live 读）：
- `plan_content`/`snapshot_text`：文本注入（同 Check 34 的 `evidence_rows`/`snapshot_text` 注入模式，verify_workflow.py:19367）。
- `commit_date`：**最近治理 commit 日期**（ISO 字符串），由 live 模式经 git 推断；测试注入固定值。

出参：`{verdict, reason, violations, warnings, stats}`，verdict ∈ PASS/WARN/FAIL/no-verdict，永不 raise（同 Check 34 契约）。

#### 判定语义（WARN vs FAIL 渐进）

| 信号 | 规则 | severity |
|---|---|---|
| S1a | `session_date` 解析失败或缺失 | **WARN**（fail-safe，不因格式漂移报 FAIL）|
| S1b | `session_date` **< 最近治理 commit 日期**（即快照落后于最近一次 `.governance/` commit）| **WARN**（渐进起点）|
| S1c | S1b 且（距今 ≥ 阈值 D=7 天 **且** 落后 commit 数 ≥ 阈值 C=10）同时成立 | **FAIL**（渐进升级；AND，避免低频项目单一命中误 FAIL）|
| S1d | 快照不存在 / 无 `session_date` 可比 | **no-verdict**（不可判定）|

> **DEC-152 裁定（2026-08-23，FIX-268 实现）**：S1a/S1d 字面划界落地为——快照存在但无 `session_date`（含空串注入 / 非 str 内容 / 不可解析内容）→ S1a WARN（fail-safe 披露）；**no-verdict 仅保留给"快照不存在 / 注入 None / 读取 IOError"**（§5.1 #4/#5 分别对应这两个形状）。

**渐进路径（F2 修订——主判据为「commit 落后度」，**无日历生效日豁免**）**：

- **不以日历生效日豁免**。与 Check 30c/34 的 `REQ107/REQ108_RECOMMENDATION_DATE`（=2026-08-22，用于豁免「机器记录机制出现之前的存量记录」）**不同**：快照新鲜度**不存在**「机制出现前不判」的豁免——因为该机制恰是要**抓出**「全量落后、零更新」的旧快照（tv 08-19/85 commit、router 08-21/41 commit 正是目标案例，诊断 §3.2 L153-158）。若套用日历生效日，这些旧快照会被豁免为 no-verdict，与 §7.1「对 tv/router 实测输出 fresh 警告」直接冲突。
- **生效日取值声明**：本设计**不设** `REQ145_SNAPSHOT_FRESH_DATE`。若实现必须保留一个「机制启用锚点」，则它只用于**决定是否把 git log 视为有效基准**（即用于避免「历史快照早于 `.governance/` 首个 commit」的边缘误报），而**不是**把「早于某日期的快照」豁免为 no-verdict。**对 tv/router 目标案例满足**：tv/router 的 `.governance/` 在快照日期（08-19/08-21）**之后**仍有大量 commit（85/41 个），故其快照**保证**命中 S1b（快照 < 最近治理 commit 日期）→ WARN，绝不被豁免。
- **与既有 Check 30c/34 生效日的关系**：Check 30c/34 沿用 effective-date 豁免，因为它们的对象（机器 REVIEW/RECO 记录）在机制出现前本就无机器写入；而快照新鲜度是**持续属性**，无论机制何时出现，只要快照落后于治理 commit 就应 WARN。故 **Check 35 不复用 effective-date 豁免**，此为有意的语义差异。

#### session_date 解析 + 比较基准

- **session_date 解析**：复用 resolve_entry.py 的 `_parse_snapshot_date`（resolve_entry.py:270 的 `snapshot_fresh` 逻辑，>24h 归 False）与 verify_workflow.py 的 `FIX_105_SNAPSHOT_DATE_RE`（:1820）。两者需有一致正则——resolve_entry.py 已声明「镜像 verify_workflow 的 proven 正则」（L50-52）。
- **「最近治理 commit 日期」基准**：`git -C <host_root> log -1 --format=%cs -- .governance/`（取 `.governance/` 最近一次 commit 的日期）。若 `.governance/` 无 commit（未跟踪/未版本化）→ **该快照降级为 WARN 而非 FAIL**（fail-safe；无 commit 基准不可强判）；再用 `plan-tracker.md`/`evidence-log.md` 文件 mtime 作次级基准。**与现有 Check 28c 的关系**：Check 28c（`_snapshot_fact_source_issues`，verify_workflow.py:1883-1916）比较的是 snapshot 日期 vs **最新已发布版本日期**；Check 35 比较的是 snapshot 日期 vs **最近治理 commit 日期**——两者正交，**保留 28c，新增 35**，不替换。

#### 与 Check 34/Check 28c 的关系
- Check 34（completion recommendation）查「快照是否含推荐收口（RECO/EVD 锚）」——纯派生收口，不查新鲜度。
- Check 28c（snapshot fact source）查「快照版本/日期 vs 最新发布」——发布事实一致性。
- **Check 35（新）**查「快照新鲜度 vs 最近治理 commit」——会话纪律。三者独立、互补，**不复用同一判定**。实现上对同一次运行可能同帧并触发（见 §5.1 测试 #10），须各自独立呈现，互不吞并。

#### 误报面分析 + 豁免
- **误报来源**：① 被治理项目 `.governance` 未纳入 git（私有/运行时）→ 无 commit 可比 → 豁免（降级 WARN）。② 快照手写日期但项目 git 提交频率低（如每周一 session）→ **仅时间维度**会误报 → 豁免：S1c 改为 **AND**（天数 **且** commit 数双超才 FAIL），S1b WARN 起点不变——低频项目若 commit 也少则不会同时满足，**不误 FAIL**（F5 修复）。③ 跨会话并行（多人同仓）→ 不同 session 快照陈旧被视作违反 → 豁免：只对「最新 snapshot」判定（快照内 session 作为最新；如存在多份快照，以最新 session_id 为准）。④ 快照日期早于 `.governance/` 首个 commit（项目刚接治理/快照早于该 git 历史段）→ 无 commit 可比 → 归入 ①（降级 WARN），**不套日历豁免**。

**决策返 Coordinator**：确认 Check 35 编号（Next after 34，紧随 Check 34 块 verify_workflow.py:14361）与 WARN→FAIL 的 **AND 双阈值**（7 天 **且** 10 commit）；确认「主判据 = 最近治理 commit 落后度、**无日历生效日豁免**」对齐 §7.1 验收信号「对 tv/router 实测输出 fresh 警告」。

---

### 3.3 REQ-145.3 — `check_risk_mitigation_closure`

#### 模块归置
**扩展既有域** `infra/checks/risk_domain.py`（该域已拥有 Check 2 `check_risk_staleness`（127-148）与 Check 8 `check_risk_escalation`（151-210））+ verify_workflow.py 薄再导出 + cmd_check_governance 新 Check 块。
**编号约定（F9）**：新增 check 在 cmd_check_governance 的序号块**连续分配**——Check 35 = `check_snapshot_freshness`（145.2，紧随 Check 34）；Check 36 = `check_risk_mitigation_closure`（145.3）；Check 37 = `check_gate_sequence_for_release`（145.4）；Check 38 = `check_ci_evidence`（145.5）。编号仅用于 cmd_check_governance 的块序号与报告标识，不改变域拆分归属。

#### 函数边界
`check_risk_mitigation_closure(risk_content=None, task_status_map=None)` -> dict。

入参：
- `risk_content`：risk-log.md 文本注入（缺省 live 读 `RISK_PATH`）。
- `task_status_map`：`{task_id: status}` 映射注入（缺省由 `task_priority.py` 实时解析 plan-tracker）。

出参：`{verdict, reason, violations, warnings, stats}`。

#### 输入/输出契约
- **解析器锁定（F6 修复）**：risk 行**统一用 `line.split("|")` 的 raw parts 索引**，与既有 Check 2/8（check_risk_staleness/check_risk_escalation，risk_domain.py:177-184）**完全一致**，索引集 = `parts[9]`=当前状态、`parts[10]`=缓解动作、`parts[11]`=截止日期、`parts[12]`=关联任务。**不使用 `_governance_table_cells`**（该函数裁掉首尾空 cell，cells[i] = parts[i+1]，off-by-one；混用会取错列）。**依据**：Check 2/8 在 risk_domain.py 用 `[p.strip() for p in line.split("|")]`（:177），parts[9]=status（:183）、parts[11]=deadline（:184）；新 check 须与同域既有解析器一致，否则 test 复用会不一致（F6）。
- 判定**非「已关闭」**的风险：取 `parts[9]`，**非「已关闭」**即视为待闭环（突破既有仅 `== "打开"` 的限制；纳入「缓解中/缓解完成」等中间态）。**依据**：诊断报告 §2.2 三例中 router RISK-003/tv RISK-001 的「缓解中/打开」态均被 Check 2/8 漏看，因它们只认 `== "打开"`。
- **task 引用解析策略**（§8 问题 3）：优先解析**「关联任务」列（parts[12]）**——该列是显式任务引用（机器可读、低噪）。**次要/备用**解析**「缓解动作」列（parts[10]）**命中的 `FIX-xxx/DEV-xxx` 类引用（用 `_TASK_ID_IN_REF_RE` regex，verify_workflow.py:19311）。两来源**并集去重**。**依据**：risk-log 列模板第 8 行「| 编号 | 日期 | ... | 缓解动作 | 截止日期 | 关联任务 | 备注 |」——关联任务在第 12 列、缓解动作在第 10 列。
- **task 状态判定**：**复用 `task_priority.py`**（`parse_task_dependencies`/`compute_unblocked_tasks` 已被 test_completion_recommendation.py:32-36 复用）作权威状态源；不引入独立轻量解析。**F11 注**：`compute_unblocked_tasks` 内部构建的 `status_map` **不对外暴露**（:1351）；实现时须从其返回的 `PriorityReport` 各 TaskDep 列表（completed/blocked/unblocked/non_executable，各含 `.status`）**重建** `{task_id: status}` 映射，而非直接读取一个现成 map。**若 task_priority 解析失败/缺失** → 该风险 fail-safe 为 WARN（无法验证），不误报 FAIL。**依据**：任务状态口径必须与既有 task-priority/Check 34 一致，避免「同一任务两套状态」。

#### WARN vs FAIL 判定（DEC-146 渐进 + 三例全命中）

| 信号 | 规则 | severity |
|---|---|---|
| R1 | 风险（非已关闭）的关联任务/缓解动作引用 ≥1 个 task 在 task_status_map 中**非「已完成」** | **WARN**（起点）|
| R2 | R1 且该风险**截止日期已过**（parts[11] < today）或等级为**高/严重** | **FAIL** |
| R3 | 关联任务引用在 task_status_map 中**不存在**（跨实体/已归档）| **WARN**（不升级 FAIL；误报面）|
| R4 | 风险非已关闭、**无任何可解析 task 引用**、无 `[无任务引用]`/`[跨实体]`/`[流程动作]` 豁免标记 | **WARN**（内容级空状态披露）——风险「缓解中/活跃」但缓解动作无可机器解析的任务落地引用，**披露而非静默 no-verdict**（F7 修复，击中 router RISK-003）|
| R5 | 风险**已关闭** / 带豁免标记 / 状态不可判定 | **skip / no-verdict**（不误报）|

**渐进路径**：参照 DEC-146 判断——WARN 起步（让低风险、非截止的「缓解未落地」显示但不阻断）；当叠加「截止已过」或「高危」信号时升级 FAIL。**三例命中**：router RISK-003（缓解动作「依赖测试看护/接口奇偶回归/症状知识库」无 FIX-xxx 引用 → **R4 WARN**，非 no-verdict）；tv RISK-001（缓解引用 F-07 未建成 → **R1 WARN / R2 FAIL**）；本仓 RISK-001（CI 未建 → **R1/R2**）。

#### 误报面分析 + 豁免
- 缓解措施**提到已完成任务** → 该任务 status=已完成 → 满足（PASS 不报）。
- **跨实体引用**（引用其他项目任务、历史归档任务）→ task_status_map 无该 id → R3 WARN（不升级 FAIL）。**豁免**：设 `[无任务引用]` 或 `[跨实体]` 显式标记列的豁免——有标记则 skip（避免「缓解动作叙述里出现一个 FIX-xxx 但实为别的项目」的假阳性，R5）。
- **prose 噪声**：缓解动作叙述含「FIX-xxx」但并非「要落地的任务」——优先用「关联任务」列（parts[12]，显式、机器写）作为主判定源，prose 仅作辅助——**若关联任务列为空 only 再扫 prose**。
- **已关闭风险**：status=已关闭 → 直接跳过（R5，PASS/不判）。
- **解析失败**（ragged 行 / 列不足 / 状态缺失）：fail-safe 该行**不判**（R5 skip/no-verdict），不因单行格式漂移报 FAIL（tv Check 31 教训），**但**已解析成功的相邻行不受影响。

**决策返 Coordinator**：确认「非已关闭 + 关联任务列优先（parts[12]）+ task_priority 复用」与 `R2 升级 FAIL` 阈值；确认 R2 的「高危/截止」信号是否足够严谨（另一候选：仅「截止已过」升级 FAIL，更高召回、更低误报）；确认 R4（无 task 引用的非已关闭风险 → 内容级 WARN 披露，而非 no-verdict）是否可接受（避免「仍开放但无任务落地的缓解」被静默放过）。

---

### 3.4 REQ-145.4 — `check_gate_sequence_for_release`

#### 模块归置
**新域** `infra/checks/gate_domain.py` + `check_release_readiness`（verify_workflow.py:6664）内嵌调用点 + 独立 Check 块（**Check 37**，编号紧随 Check 36 之后；见 §3.3 编号约定）。

#### 函数边界
`check_gate_sequence_for_release(gates=None, published_tags=None, profile=None)` -> dict。

入参：`gates`（`parse_gate_status()` 的结果列表，verify_workflow.py:7140）、`published_tags`（已发布 tag 列表，缺省由 git 推断）、`profile`（可空）。
出参：`{verdict, reason, violations, warnings, stats}`。

#### 判定语义（哪些 Gate 算「→发布」前置）
- **发布 Gate 识别**：Gate 表中「阶段转换」列（parts[1]）含「发布」字样即视为「→发布」Gate（tv 行 `| G8 | → 版本发布 | pending | | |`，verify_workflow.py:17690 样例）。
- **前置 Gate 集** = 在 Gate 表中**位于该发布 Gate 之前**（按 `## Gate 状态跟踪` 表的行序）的所有非发布 Gate。
- **Profile 差异**：lightweight=7 合并 Gate（`_PROFILE_GATE_COUNT` 12879-12883）、standard=11。判定逻辑**不按 profile 写死 Gate 编号**——一律用「发布 Gate 之前的行」推导，天然兼容 7/11 两档。**依据**：诊断报告 §4.2 盲区 B「tv G6/G7/G8 pending（standard）而 v1.6.0 已发；router G4-G7 pending（lightweight）而 v0.2.1 已发」——两例的发布 Gate 分别是 G8→版本发布（standard）与 G4→发布（lightweight），编号不同需避免硬编码。

#### 判定数据源
- **Gate 状态表**：`parse_gate_status()`（verify_workflow.py:7140-7163）。
- **已发布 tag**：`git tag` 输出中 `^v?[0-9]+\.[0-9]+\.[0-9]+$` 的 tag，或通过 `check_release_readiness` 的 `lineage_remote` 语料（verify_workflow.py:6673）。**fail-safe**：git 不可用 → 降级只读 Gate 表，只有当 Gate 表某发布 Gate 已标 passed 但存在前置 pending 时才按 WARN 提示（不因「查不到 tag」误报）。

#### WARN vs FAIL

| 信号 | 规则 | severity |
|---|---|---|
| G-s1 | 存在已发布 tag 且其发布时间 **<（早于）** 任一「→发布」前置 Gate **passed** 日期（或 passed 且无日期——无法证实通过先于发布；**passed-on-entry 不算**，见下方误报面 / DEC-153 ④）| **FAIL**「发布绕过 pending Gate」|
| G-s2 | 存在已发布 tag，但任一前置 Gate 为 **pending**（无法确定先后）| **FAIL**（保守，只要发布 tag 存在且前置有 pending 即 FAIL）|
| G-s3 | 无已发布 tag（无法从 git 确认），但 Gate 表显示发布 Gate 已 passed 且前置有 pending | **WARN**（fail-safe 到 WARN）|

#### 对已发布历史（tv/router 已发生的绕过）是否豁免
**建议豁免**：对**历史已发布版本**不追溯 FAIL——仅在**当前候选版本**（`check_release_readiness` 的 `lineage_mode="candidate"`+`release_commit` 场景）触发。理由：G-s1/G-s2 用于**发布前互锁**，若把「历史已发生的绕过」一并 FAIL，会产生大量既有债务噪音（tv v1.6.0/router v0.2.1 已发生），掩盖当前发布候选的真问题。**依据**：诊断报告 §7.2 P-TV-1/P-ROUTER-2 均表述为「不要**再**在 pending Gate 上发布」，指向未来而非历史。豁免实现：用 `lineage_mode` 区分（candidate=判新 tag；released=仅 WARN 披露历史）。

> **R0 修正（2026-08-23，REVIEW-FIX-266-R0 P2-2）**：本表 G-s1 原字面「发布时间 **>** passed 日期 → FAIL」为反向笔误——按字面会把「先过 Gate 后发布」的合规场景判 FAIL，与 FAIL 标题「发布绕过 pending Gate」、G-s2 同向语义、REQ-145.4 G9 意图均矛盾。已修正为「**<（早于）** 或无日期（无法证实通过先于发布）」方向；实现（FIX-266）保持修正后方向，测试 `test_g_s1_tag_after_passed_gate_passes` 锁定。原「passed/passed-on-entry」并入 passed 的表述亦与下方误报面 / DEC-153 ④（passed-on-entry 视为非 pending）矛盾——本行已改为仅 **passed**（on-entry 不算，见误报面）。
**BR-4 注意**：`check_release_readiness` 的 `lineage_mode` **缺省="candidate"**（verify_workflow.py:6671），若调用方 `cmd_check_release`/`check-release`（verify_workflow.py:18178）在检查**已发布版本**时未显式传 `lineage_mode="released"`，历史绕过会误判为 candidate FAIL。**须在 `cmd_check_release` 对已发布版本（`--released` 场景）显式传 `lineage_mode="released"`**，或改为「判定最新候选 tag」的固有边界（推荐前者，改动最小）。

#### 误报面 + 豁免
- Gate 表「passed-on-entry」（onboarding 早期）≠ 真验证 → 豁免：passed-on-entry 算「非 pending」，若整行前置全 passed-on-entry 不 FAIL（该项目为 on-entry 接入，无真实时序可判）——**建议**：仅当存在「passed」而非「passed-on-entry」的前置时才有强互锁诉求。
- 无 git tag 但 Gate 状态自洽（发布 Gate pending）→ 不 FAIL（无发布动作）。
- 多版本 tag：只对「最新候选 tag」判定，避免旧 tag 触发。

**决策返 Coordinator**：确认「发布 Gate 之前」的行序推导 vs 「写死发布 Gate 编号」；确认历史豁免（candidate vs released 区分）。

---

### 3.5 REQ-145.5 — `check_ci_evidence`

#### 模块归置
**新域** `infra/checks/ci_domain.py` + verify_workflow.py 薄再导出 + cmd_check_governance 新 Check 块（**Check 38**，编号紧随 Check 37 之后；见 §3.3 编号约定）。

#### 函数边界
`check_ci_evidence(plan_content=None, repo_root=None)` -> dict。出参 `{verdict, reason, violations, warnings, stats}`。

#### 「声称 CI 已建/已跑」的文本来源
- **plan-tracker 任务行**：任务描述含「CI」+「已建|已跑|已配置|已建立|已完成 CI|workflow 就绪」等肯定声明（tv DEV-003 行「CI 存在……本仓无 remote——首次运行/成功率统计待远端仓库后补验」——注意：**同含「无 remote 从未真跑」的自认**，需识别为「已建但未真跑」）。
- **注记型声明**：`执行记录`/`运行证明` 中「首次运行/成功率统计待远端仓库后补验」= 未跑声明。
- **解析**：扫 plan-tracker 全文，命中「CI（x）已建/已跑/已配置」且未带「未跑/未真跑/待远端/从未」否定词的，视为「声称已跑」；带否定词的视为「声称已建未跑」。

#### 判定语义
| 信号 | 规则 | severity |
|---|---|---|
| C1 | 声称 CI **已建** 但 `.github/workflows/`（或 `.gitlab-ci.yml`/`Jenkinsfile`）**不存在** | **FAIL** |
| C2 | workflow 存在但 **无 remote**（`git remote -v` 为空）或 **无 CI 运行记录证据** | **WARN**「CI 未真跑」|
| C3 | 声称 CI 已跑但本地无法证实时（无 remote/无 run log） | **WARN**（fail-safe，不升 FAIL）|
| C4 | 无 CI 声明且无 workflow → **PASS**（不过度声明） |  |

**fail-safe 到 WARN 而非 FAIL**：`remote` 检测（`git remote -v`）与「运行记录证据」在本地 host 上**无法证实**时一律降级为 WARN（C2/C3），绝不因「无法运行远端 CI」而 FAIL 一个本可工作的检查。**依据**：诊断报告 §4.2 盲区 C「tv 无 remote 从未真跑——local 无法证实时 fail-safe 到 WARN 而非 FAIL」与 R-D4c。

#### 误报面 + 豁免
- `.github/workflows` 存在但为占位（空 job / 仅 lint）→ 记为「存在」但 C2 可再加「语法/工作流是否为 verify_workflow 触发」的深度校验——**0.76.0 不深究，仅存在性 + remote**（防过度工程，R 设计原则第 1 条）。
- 自定义 CI 目录（非 github actions，如 GitLab/Jenkins）→ `check_ci_evidence` 需**多路径探针**（`.github/workflows/`、`.gitlab-ci.yml`、`Jenkinsfile`），任一存在即视为「有 CI 载体」。
- monorepo 子目录 workflow（如 `infra/.github`）→ 用 glob `**/.github/workflows/*`（含深路径）避免漏检。
- git 不可用（无 `.git`）→ remote 检测 fail-safe 为「无法确认」→ C2 WARN（不 FAIL）。

**决策返 Coordinator**：确认「多路径探针」「仅存在性 + remote（不做深度 job 校验）」的范围控制；确认 C1 在没有「已建」声明时是否也探 workflow（建议：仅当有声明时才 FAIL，无声明不判）。

---

### 3.6 REQ-145.6 — 能力分级声明 + L7 建议

#### 模块归置
**纯文档**：SKILL.md + commands/governance.md（能力分级声明）+ plan-tracker L7（仅建议措辞，不改写）。

#### 能力分级声明（A/B/C 级措辞模板）

在 SKILL.md 与 commands/governance.md 中，对「自动/看护」声明逐条标注级别，**引用 plugin-contract.md L114 禁令**（「禁止用笼统的『自动』一词同时指向 A 级与 C 级能力」）：

- 措辞模板（建议，写入 SKILL.md 的「能力分级」小节）：
  ```
  ## 自动化能力分级声明（plugin-contract.md L114）
  本工作流对「自动/看护」的承诺按 plugin-contract.md 三级划分：
  - **A 级（Agent Protocol Automation）**：行为协议自动化——agent 按协议纪律自动执行（如「Coordinator 接管用户交互：只在 critical triggers 触发时打断；常规执行自动推进」= A 级，SKILL.md L38）。
  - **B 级（CLI-Enforced Automation）**：CLI/脚本强制——`verify_workflow.py check-governance` 与 commit hooks 在命令/commit 时点强制（= B 级）。
  - **C 级（System Automation）**：后台系统自动触发、不依赖 agent 记忆——**未实现**（plugin-contract.md L102：MCP/headless runner 仅有协议样例，无可用实现）；0.76.0 通过 `check-governance --summary-only` 的会话 bootstrap 自动运行实现「会话级」自动触发，但**不是** C 级后台 daemon。
  ```
- **逐条标注**：SKILL.md L38（「常规执行自动推进」）→ 标 A 级；L268（「治理基础设施（自动使用）」）→ 标 B 级（事件驱动，非持续）；commands/governance.md L64（「自动分类」）→ 标 B 级（命令时）；README 对外宣示 → 明确「当前治理自动级别 = A/B；C 级为 roadmap 未实现」。

#### L7 目标改写的**建议措辞**（不自行改写 plan-tracker）

plan-tracker L7 现为：「过程自动（agent 在后台持续看护，用户专注思考而非流程管理）」。诊断报告 §5.1 P1 判为「有承诺无机制」。**建议改写为可验收承诺**（仅建议措辞，回给 Coordinator，不写入 plan-tracker）：
```
过程自动（每次会话开始自动运行一次健康摘要 check-governance --summary-only 并汇报——落地 = FIX-264/REQ-145.1；「后台持续看护」为 roadmap，C 级未实现）
```
**含可测验收信号**：①每会话 bootstrap 后输出 `Governance: {N} issues`；②`--summary-only` 只输出汇总 + 首个 FAIL/WARN；③无 issue 时输出 **`Governance: [PASS]`**（对齐 §7.1 验收信号字面「无 issue 时输出 `[PASS]`」）。与 REQ-145.1 验收信号（§7.1）一致。

**决策返 Coordinator**：确认能力分级声明的精确措辞与落位（SKILL.md 具体章节、commands/governance.md 具体章节）；确认 L7 建议措辞是否采用。**注意**：L7 是治理记录（`.governance/plan-tracker.md`），按边界 Coordinator 可直接改，但本设计**不做最终改写**，只给措辞。

---

## 4. 发布链影响（0.76.0 承载）

### 4.1 版本投影文件清单（bump 到 0.76.0，`check_version_consistency` 会逐项校验）

version.py `check_version_consistency`（version.py:46-85）强制下列文件与 SKILL.md frontmatter 一致：

| 文件 | 位置 |
|---|---|
| SKILL.md frontmatter `version` | `skills/software-project-governance/SKILL.md`（source of truth）|
| core manifest `/version` | `skills/software-project-governance/core/manifest.json` |
| Claude plugin / marketplace | `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` |
| Codex plugin | `.codex-plugin/plugin.json` |
| zcode plugin | `.zcode-plugin/plugin.json` |
| Chrys plugin | `.chrys-plugin/plugin.json` |
| verify_workflow.py REQUIRED_SNIPPETS 硬编码版本 | `infra/verify_workflow.py` |
| hooks `@version`（4 个 hook）| `infra/hooks/{pre-commit,commit-msg,post-commit,prepare-commit-msg}`（每处第 A 行 `# @version: 0.75.0`）|
| project/CHANGELOG.md 最新版标题 | `project/CHANGELOG.md` |
| plan-tracker 工作流版本（WARN 级）| `.governance/plan-tracker.md` |

**补充（非 version_consistency 覆盖但需同步）**：
- `adapters/dsh/agent.cordis.yml.template`：`L33 治理工作流（v0.75.0）` → v0.76.0（由 `launch.py --sync` 生成 persona 时同步；`test_review_machine_provenance` 会校验契约块与版本锚）。
- `AGENTS.md` / `CLAUDE.md` 的 `@bootstrap-version` / 模板（若 A3 方案采纳，需同步健康摘要步骤）。
- `adapters/dsh/AGENTS.md.template`：bootstrap 段模板（profile 差异化三档的宿主投影）。
- `project/e2e-test-project/`（e2e 夹具）：若本设计改 SKILL.md / commands / behavior-protocol / AGENTS/CLAUDE 模板，则 `check_projection_sync` 会把 `project/e2e-test-project` 的同名镜像文件（`skills/software-project-governance/SKILL.md`、`.governance/plan-tracker.md`、`commands/*.md`）与仓库源比较——**需同步覆盖**（`_legacy_projection_sync` 计算哈希 diff，projection.py:71-72）。**注（F14/P3）**：`behavior-protocol.md` 也在 e2e 镜像树中（FIX-253 先例），A3 改 M4.1 后须同步其 e2e 副本，否则 `check_projection_sync` 报 `target fixture drift`。

### 4.2 hooks 改动
**建议不加新 hook**（本设计不新增强制 hook——REQ-145.1 的摘要走 bootstrap，REQ-145.2/3/4/5 是 check 而非 hook）。若 Coordinator 希望增强 post-commit（R-D1b/G3），**建议**作为独立小改动（post-commit Step 4 把「grep 前 12 行」升级为「输出 `Governance: {N} issues` 语义」），但本设计**不纳入** 0.76.0 主链（属 G3 P1，可后置）。**决策返 Coordinator**。

### 4.3 CHANGELOG 要点（0.76.0）
```
## [0.76.0] - 2026-08-22
### Added
- FIX-263/REQ-145.1~145.7：看护模式统一修复——bootstrap 健康摘要（--summary-only）、Check 35 快照新鲜度、风险缓解闭环、Gate-发布互锁、CI 证据、能力分级声明、--summary-only 精简入口。
### Changed
- `check-governance --summary-only`：输出汇总 + 首个 FAIL/WARN，秒级。
- SKILL.md/accounts 能力分级声明（A/B/C 级，引用 plugin-contract L114）。
### Fixed
- 风险「写缓解即完成」无机器断言（Check 2/8 时间维度盲区）。
- bootstrap 不诊断（resolve_entry.py 不 import verify；M4.1 增健康摘要步）。
```

---

## 5. 测试计划（红→绿夹具，参照 test_completion_recommendation.py 18 用例先例）

每个新增/扩展 check 都有一组**注入式夹具测试**（inject fixture rows/text，断言 verdict/violations/warnings/stats），参照 `infra/tests/test_completion_recommendation.py`（测试通过 `evidence_rows=`/`snapshot_text=` 注入，verify_workflow.py:19367 支持 live/fixture 双模式）。
**红→绿夹具总数 = 49 条**（5.1=10、5.2=12、5.3=8、5.4=8、5.5=11——为逐条实列之和，非注水预估）。

### 5.1 `check_snapshot_freshness`（10 用例）
| # | 红→绿 | 断言 |
|---|---|---|
| 1 | 红：session_date < 最近治理 commit 日期 → | **WARN**（S1b）|
| 2 | 红：`(距今≥7天 AND 落后 commit≥10)` → | **FAIL**（S1c，AND 双阈值）|
| 3 | 绿：session_date == 最近 commit 日期 → PASS |  |
| 4 | 红：session_date 缺失/解析失败 → WARN（fail-safe） |  |
| 5 | 绿：无快照/无 session_date → no-verdict |  |
| 6 | 红：**tv/router 式旧快照**（08-19/08-21，但其后有大量治理 commit）→ **WARN**，**绝不为 no-verdict**（F2 机器验证：无日历豁免，主判据=commit 落后度） |  |
| 7 | 红：低频项目（天数>7 但 commit 落后<10）→ **WARN** 非 FAIL（S1c AND 使单一命中不 FAIL；F5 验证） |  |
| 8 | 绿：live 模式读 patched paths（mock snap/evidence）→ 判定正确 |  |
| 9 | 绿：与 28c/34 正交（fixture 组合）→ 独立判定不复用 |  |
| 10 | 红：28c / 34 / 35 同一快照**同帧并触发** → 三者各自独立呈现，互不吞并（F14 去重验证） |  |

### 5.2 `check_risk_mitigation_closure`（12 用例）
| # | 红→绿 | 断言 |
|---|---|---|
| 1 | 红：风险（非已关闭）关联任务非已完成 → **WARN**（R1） |  |
| 2 | 红：R1 + 截止已过/高危 → **FAIL**（R2） |  |
| 3 | 绿：关联任务已完成 → PASS |  |
| 4 | 红：引用不存在任务 → WARN（R3，跨实体） |  |
| 5 | 红：非已关闭、无 task 引用、无豁免标记 → **WARN**（R4 内容级披露；F7 验证 router RISK-003 不误 no-verdict） |  |
| 6 | 绿：已关闭风险 → skip（R5） |  |
| 7 | 红：prose 缓解动作引 FIX-xxx（关联列空）→ 命中（辅助源，parts[10]） |  |
| 8 | 绿：带 `[无任务引用]` 标记 → 豁免 skip（R5） |  |
| 9 | 红：ragged 行/列不足 → fail-safe 该行不判（R5），相邻行不受影响 |  |
| 10 | 绿：task_priority 不可用 → 该风险 WARN 不 FAIL |  |
| 11 | 红：关联任务列(parts[12]) **且** 缓解动作列(parts[10]) 同时命中同一 task → **只计一次**（并集去重） |  |
| 12 | 绿：解析器索引固定（raw parts[9]/[10]/[11]/[12]）→ 取列正确（F6 索引验证，防 off-by-one） |  |

### 5.3 `check_gate_sequence_for_release`（8 用例）
| # | 红→绿 | 断言 |
|---|---|---|
| 1 | 红：standard G7 pending + tag v1.6.0 → **FAIL**（G-s1/G-s2） |  |
| 2 | 红：lightweight G3 pending + tag v0.2.1 → **FAIL**（profile 兼容 7 档） |  |
| 3 | 绿：全部前置 passed + 无 tag → PASS |  |
| 4 | 红：无 tag 但发布 Gate passed + 前置 pending → WARN（G-s3 fail-safe） |  |
| 5 | 绿：全 passed-on-entry（on-entry 接入）→ PASS |  |
| 6 | 红：release commit 前 Gate 顺序错乱 → FAIL（candidate 模式） |  |
| 7 | 绿：**strict(11)** 与 standard(11) 同 profile count → 判定正确（F9 测试覆盖） |  |
| 8 | 红：G-s3(WARN) 在新增 tag 后升级为 FAIL(G-s2) → **同 check 内 WARN→FAIL 渐进**（补渐进对） |  |

### 5.4 `check_ci_evidence`（8 用例）
| # | 红→绿 | 断言 |
|---|---|---|
| 1 | 红：声称已建但 `.github/workflows` 不存在 → **FAIL**（C1） |  |
| 2 | 红：workflow 存在 + 无 remote → **WARN**（C2） |  |
| 3 | 红：声称已跑 + 无运行记录 → WARN（C3, fail-safe） |  |
| 4 | 绿：无 CI 声明且无 workflow → PASS（C4） |  |
| 5 | 绿：`.gitlab-ci.yml` 存在（自定义 CI）→ 视为有 CI 载体 |  |
| 6 | 红：monorepo 深路径 `**/.github/workflows/*` → 命中 |  |
| 7 | 绿：git 不可用 → remote fail-safe WARN 不 FAIL |  |
| 8 | 红：workflow 从存在(C2 WARN)到被删(C1 FAIL) → **同 check 内 WARN→FAIL 渐进**（补渐进对） |  |

### 5.5 `--summary-only`（11 用例）
| # | 红→绿 | 断言 |
|---|---|---|
| 1 | 红：全量 N>0 → 只输出 `Governance: {N} issues` + 首个 `[FAIL]` |  |
| 2 | 绿：N=0 → **`Governance: [PASS]`**（无详情行；F1 验证） |  |
| 3 | 红：有 WARN 无 FAIL → `[WARN]` 行输出且 exit 0（除非 --fail-on-issues） |  |
| 4 | 绿：缺省（不传 `--summary-only`）路径与既有逐字节一致（零回归快照 diff） |  |
| 5 | 红：`--fail-on-issues --summary-only` → exit 1 |  |
| 6 | 绿：`--level lightweight` → 只输出汇总 + 首个 FAIL（详略分档） |  |
| 7 | 绿：`--summary-only` 与全量跑的 all_issues 计数一致（同源验证） |  |
| 8 | 红：格式漂移 → `Governance: N issues (parse degraded)`（fail-safe） |  |
| 9 | 红：verify 不可用 → `Governance: unavailable` |  |
| 10 | 红：超时 → `Governance: timed out` |  |
| 11 | 红：advisory（fatal_on_error=false）不计数 + 首个为 advisory 时附注 `[ADVISORY]` 行 |  |

---

## 6. 未决项 / 假设（显式标注）

| 项 | 类型 | 说明 |
|---|---|---|
| 新 check 编号 35/36/37/38 | 假设 | 无既有证据表明 0.76.0 已预占这些编号（现状 cmd_check_governance 到 Check 34，verify_workflow.py:14361），编号为设计假设，返 Coordinator 确认 |
| 快照新鲜度阈值 7 天 **且** 10 commit | 建议 | 无定量标准，为满足「低频项目（时间超但 commit 少）不误 FAIL」而选 **AND** 语义，标为建议 |
| `--summary-only` 秒级 | 设计级承诺 | 0.76.0 承诺「秒级」（复用同引擎，耗时=全量引擎，本仓实测在秒级量级）；**硬性 <1s 的 quick-scan 为 0.77+ 选项**（见 §3.1）|
| tv/router 被治理项目用 DSH 跑 verify 的可用性 | 已验证 | 诊断报告 §8 已推断 OK（本仓可跑），标注为已验证 |
| risk 行解析器索引 = raw `line.split("|")` parts[9]/[10]/[11]/[12] | 已锁定 | 与 check_risk_staleness/escalation（risk_domain.py:177-184）一致，防 off-by-one（F6）|
| gate 互锁历史豁免（released vs candidate）| 建议 | 依据诊断报告 §7.2「不要**再**发布」；须在 `cmd_check_release` 对已发布版本显式传 `lineage_mode="released"`（BR-4）|
| C 级后台看护 | 非本范围 | plugin-contract L102 未实现；0.76.0 只做「会话级」auto-run（--summary-only），C 级为 0.77+ roadmap |

---

## 7. 自检硬门槛复核

| 门槛 | 达成 |
|---|---|
| 1. 纯设计：未改产品代码/infra/hooks/.governance；仅写本文件 | ✅ |
| 2. 每决策带依据（报告节/行号/代码事实）；无依据标假设 | ✅ §3 各节「依据」行 + §6 |
| 3. 覆盖全部 7 项验收信号 + 每 check 误报面 | ✅ §3.1-3.6 每节含「误报面 + 豁免」|
| 4. 明确 WARN/FAIL 语义与渐进路径 | ✅ §3.2/3.3/3.4/3.5 均含 severity 表 + 渐进 |
| 5. 不做最终决策（方案级）| ✅ 每节「决策返 Coordinator」|

---

## 8. 返回 Coordinator 的关键设计决策摘要

**每一项**（都带理由，见对应节）：

1. **REQ-145.1/145.7**：`--summary-only` → 复用同引擎（捕获输出）作 0.76.0 基线（zero-regression、稳定摘要）；**PASS 令牌对齐验收信号 = `Governance: [PASS]`**（F1）；bootstrap 健康摘要 → **不进 persona**，进 SKILL.md + M4.1（A3，因 persona 契约块 1535/1536 已满）；**「秒级」作 0.76.0 设计级承诺**（复用同引擎，耗时=全量引擎，本仓实测秒级量级）；硬性 <1s 的 quick-scan 为 0.77+ 选项。
2. **REQ-145.2**：Check 35 `check_snapshot_freshness` → 新域 `infra/checks/snapshot_domain.py`；基准 = `.governance/` 最近 git commit 日期（fallback mtime）；**主判据 = commit 落后度，无日历生效日豁免**（F2，否则吞掉 tv/router 目标案例）；WARN→FAIL **AND 双阈值**（7 天 **且** 10 commit，F5）；与 Check 28c/34 正交复用不替换。
3. **REQ-145.3**：`check_risk_mitigation_closure` → 扩展 `infra/checks/risk_domain.py`；**解析器锁定 raw `split("|")` parts[9]/[10]/[11]/[12]**（F6，与 Check 2/8 一致）；task 引用优先「关联任务」列（parts[12]），辅「缓解动作」列（parts[10]）；**无 task 引用的非已关闭风险 → R4 内容级 WARN 而非 no-verdict**（F7）；task 状态复用 `task_priority.py`（需从 PriorityReport 重建 status map，F11）；WARN 起步 + 截止已过/高危升级 FAIL；非「已关闭」即待闭环。
4. **REQ-145.4**：Check 37 `check_gate_sequence_for_release` → 新域 `infra/checks/gate_domain.py` + `check_release_readiness` 内嵌；发布 Gate 用「阶段转换含发布」+ 其前所有 Gate 推导（非写死编号，兼容 7/11）；历史已发生绕过（tv/router）**豁免**（candidate 判新，released 仅 WARN——**须 `cmd_check_release` 对已发布版本显式传 `lineage_mode="released"`**，BR-4）。
5. **REQ-145.5**：Check 38 `check_ci_evidence` → 新域 `infra/checks/ci_domain.py`；多路径探针（.github/.gitlab/Jenkins）+ `git remote` 检测；local 无法证实 → fail-safe WARN 不 FAIL。
6. **REQ-145.6**：能力分级声明（A/B/C 级措辞模板）进 SKILL.md + commands/governance.md，引用 plugin-contract L114；L7 建议措辞（含可测验收信号 `Governance: {N} issues` / `Governance: [PASS]`），未实际改写 plan-tracker。
7. **约束 (a)**：健康摘要不进 persona 契约块，进 SKILL/M4.1（理由：契约块 1535/1536 已满 + 语义不匹配 + SKILL 仍每会话经 persona 第 1 步必然加载）。
8. **约束 (b)**：新 check 一律走 `infra/checks/` 域拆分（新域 snapshot/gate/ci + 扩展 risk）；`--summary-only` 走主文件（引擎调度逻辑）。薄再导出 + cmd_check_governance 新 Check 块；编号连续分配 35/36/37/38（F9）。
9. **约束 (c)**：串行执行序 **264→265→268→266→267→269**（F3 修正——四个 check 域两两独立、无不必要的 268↔265 依赖，故 FIX-265 可提前），不并行改 verify_workflow.py；每步 merge 后跑 `check-governance` 零回归。

> 注：本设计不新建 ADR。如需将任一「建议」升格为 ADR（尤其约束 a/b 与《gate 发布 Gate 编号推导》），由 Coordinator 触发 Architect 补 ADR。
