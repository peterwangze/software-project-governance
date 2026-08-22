# AUDIT-145 诊断报告：看护缺口系统性诊断——三项目同模实证 → 工作流本体缺陷规格 + 修复链建议

- **Task ID**: AUDIT-145（P0，只读诊断，禁止改产品代码/infra/.governance）
- **调查日期**: 2026-08-22（本仓当前时间：2026-08-22 22:08）
- **执行者**: Analyst sub-agent（Governance 快速通道，只读）
- **触发**: 用户跨项目定性——「使用这个工作流的项目都遇到同样的问题：基础问题全靠人发现，工作流看护不到，每次都得人来反馈」；三项目（本仓 + router + tv）同模（工作流本体 + router + tv），定性为工作流本体缺陷而非项目纪律问题。
- **方法**: 只读证据收集——文件直读（read/grep/glob）+ 只读命令输出（pwsh 只读运行 verify_workflow.py check-governance）；禁止任何写操作（除本报告）；所有行号引用均经 Read/命令输出验证；机制行为推演均标注「推演，经源码/输出验证」。
- **结论与建议分离**: 事实（证据+路径+行号/命令输出）、推断（标注「推断」）、建议（见 §7 修复链）分节标注。

> **范围裁决（用户 2026-08-22）**：本报告 §7.2「被治理项目侧探针」部分**不纳入修复链执行范围**——用户明确：只修工作流本体；router/tv 仅作只读证据基线，不主动干涉；项目好转通过工作流升级同步自然实现。§7.2 保留仅为证据完整性（现场已核实），**不作为任何行动依据**。修复链仅取 §7.1（工作流本体 0.76.0+）。

---

## 摘要（四问一句话版）

1. **根因（本体缺陷而非纪律）**：本工作流的全部「看护」是**事件驱动**（git commit 时 hook 触发 + 用户手动 `check-governance`），没有任何**持续后台看护**机制（无 daemon/cron/MCP/CI-runner 自动触发）。plugin-contract.md L90/L102 明确 C 级 System Automation「**未实现**（MCP/headless runner 仅有协议样例，无可用实现）」。因此「能检出问题的 verify_workflow.py」只在用户主动或 commit 时被调用，「检出问题→动作」这条链完全依赖**人/Agent 主动性**——这正是用户观测到的「全靠人发现」。
2. **风险缓解无闭环断言（D2）**：risk 的「写缓解措施」即被视为完成——Check 2（risk_domain.py:127-148）只查「>7 天未更新」，Check 8（risk_domain.py:151-210）只查「截止日已过」；**没有**任何 check 验证「缓解措施已落地」。实证三例：router RISK-003「依赖测试看护」无 watchdog→第二次同型事故（FIX-003）仍用户报；tv RISK-001「定期源可用性巡检」未落地且 09-19 截止；本仓 RISK-001「CI 缺失」注册后未建。
3. **会话纪律无机器保证（D3）**：session-snapshot「必写」是 M4.2 流程规则（behavior-protocol.md:221-268），但 post-commit hook（post-commit:1-265）**专职任务 ID 追踪/锁清理**，不写不查 snapshot 新鲜度；Check 34（verify_workflow.py:19367-19538）只查「`## 下次会话优先级`节是否引用快照 ID（RECO/EVD）」——**不查快照是否最新**。实证：router 快照 2026-08-21 后 41 commit 零更新；tv 2026-08-19 后 85 commit 零更新。
4. **自动面覆盖边界（D4）**：hooks 只约束 commit 格式（任务 ID/审查证据正则/目标对齐字段）；**不约束**：任务行状态 vs 磁盘事实一致性、Gate 与发布互锁、CLI 测试在 CI 的真实运行。实证三例：tv G6/G7/G8 pending 而 1.6.0 已发布（tag v1.6.0=158038c）；router G4-G7 pending 而 v0.2.1 已发布；tv CI 存在（.github/workflows True）但 DEV-003「本仓无 remote——概率统计待远端仓库后补验（无过度声明）」= 从未真跑。
5. **承诺-验收差距（D5）**：本仓 plan-tracker.md L7 项目目标明示「**过程自动（agent 在后台持续看护，用户专注思考而非流程管理）**」。实际交付为「记录 + 门禁 + 事后审计」。SKILL.md 内多处「自动」词（如 L38「常规执行自动推进」、L268「自动使用」）指向的是**A 级 agent 协议纪律**或**B 级 CLI 检查**，而用户读到的「自动/看护」被 plugin-contract.md L114 明文禁止与 C 级「自动」混用——但 SKILL.md/commands 并未逐条标注「当前能力级别」。

---

## 0. 证据基线复核（修正/确认）

> 本基线与任务上下文证据基线交叉核对，所有命令输出/文件直读均在本会话实际执行。**标注修正项**。

| 项目 | 关键事实 | 复核结果 |
|---|---|---|
| 本仓 | resolve_entry active_version=0.75.0，resolved_root_ok=true | ✅ 确认 |
| 本仓 | check-governance Check 28s：plan-tracker.md 261228B(255.1KB) / evidence-log.md 1253600B(1224.2KB) 均 ERROR | ✅ 确认（主机输出：`governance files: 2 ERROR, 0 WARN`）；**advisory（fatal_on_error=false），不阻断** |
| 本仓 | check-governance 66 issues（主机输出 `Result: ISSUES FOUND — 66 issue(s)`）| ✅ 确认 |
| 本仓 | Check 30 FAIL×7（V2 轮次断裂）；Check 30c WARN×8；Check 34 PASS（5 完成全带快照）| ✅ 确认 |
| 本仓 | task-priority-analysis live unblocked=0 | 见计划说明（检查于现有 plan-tracker，未重跑以避免写入；标记为基线引用）|
| router | lightweight profile（7 合并 Gate，6 列）；plan-tracker 20029B；17 任务 15 完成 | ✅ 确认 |
| router | check-governance 40 issues（`Result: ISSUES FOUND — 40 issue(s)`）| ✅ 确认 |
| router | Check 30 FAIL×10（ARCH/DEV/EVO/FIX/MIG/RES 审查链断裂或状态字段无效）| ✅ 确认（`[FAIL] 10 closure violation(s)`）|
| router | Check 30c WARN×6（EVO/DEV/FIX 手写审查行缺机器标记）| ✅ 确认 |
| router | Check 34 WARN（snapshot `## 下次会话优先级` 无 ID 引用）| ✅ 确认 |
| router | `.github/workflows` 不存在（Test-Path False）| ✅ 确认 → 无 CI |
| router | RISK-003 活跃（2026-08-21）自述「宿主更新无预警通道（npx cache 静默刷新），依赖测试看护」| ✅ 确认 |
| router | 工作树 git diff 状态 | ⚠️ **已修正**：任务上下文基线称「工作树 +116/-3（lib/attachments.js/lib/service.js）但任务行『待派发』」。当前复核（22:08）工作树 **clean**（`git status` 无输出、`git diff --stat` 空），FIX-003 代码已于 commit `b6581c5` 提交，任务行状态字段已更新为「**已完成（终态）**——RCA 三环 + b6581c5 + … R1 APPROVED_WITH_NOTES/0」。→ 该「任务行 vs 磁盘事实不一致」实例**已被用户/Agent 主动修复**，但注意：**修复的主因是人工 + commit-message 审查，而非任何 hook/check 系统保证**——这本身就是 D4 的活证（详见 §5.4）|
| tv | standard profile；plan-tracker 20538B；20 任务 19 完成 | ✅ 确认 |
| tv | check-governance 137 issues（`Result: ISSUES FOUND — 137 issue(s)`）| ✅ 确认（基线 138，现行 137——1 项差异可能为已修复，标记基线引用）|
| tv | Check 31 BLOCKED：ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY ragged table row | ✅ 确认（EVD-015 行 = **12 竖线**，其余 EVD-001~042 均 11 竖线）|
| tv | Check 30 FAIL（PERF-003 缺 R[1]）；Check 30c no-verdict；Check 34 WARN | ✅ 确认 |
| tv | Gate 表 G6/G7/G8 pending 但 REL-004 已完成（tag v1.6.0=158038c）| ✅ 确认（plan-tracker L30-32 `pending`；L105 REL-004 `已完成`；`git tag` 见 v1.6.0）|
| tv | DEV-003 行注「本仓无 remote——首次运行/成功率统计待远端仓库后补验」| ✅ 确认（plan-tracker L125）|
| tv | CI 目录存在（.github/workflows True，含 ci.yml）| ✅ 确认（`ci.yml` 存在）|
| tv | RISK-001 打开（2026-08-19，截止 2026-09-19，缓解含「定期源可用性巡检」未落地）| ✅ 确认（risk-log L7；plan-tracker L72 「F-07（RISK-001 缓解）不让位」但 F-07 未建）|
| tv | snapshot 2026-08-19；plan-tracker 0.74.0 vs hooks @version 0.75.0 | ✅ 确认（plan-tracker L11 `0.74.0`；post-commit L4 `@version: 0.75.0`）|

**共同模式确认**：三项目风险条目均「登记」未「闭环」；snapshot 均非最新（router 4+ 会话/41 commit、tv 85 commit、本仓当前会话则最新）；P0 基本全部来自用户反馈（router FIX-001/002/003、tv PERF-001/002/004/SRC-001/002）。

---

## 1. D1 诊断执行路径为何非自动

### 1.1 机制现状（事实）

诊断能力**存在**于 `verify_workflow.py check-governance`（cmd_check_governance，verify_workflow.py:13049-14373，53+ 段 Check），但触发路径只有两条：

1. **用户手动**调用（命令行或 `/governance` Scenario E）。
2. **git commit 时** hook 触发（post-commit:188-193）——但只做了「把 check-governance 输出 grep 前 12 行摘要」，**不阻断、不强制、仅展示**：
   ```bash
   python "$VERIFY_WORKFLOW" check-governance 2>/dev/null | \
       grep -E "(Check [0-9]|PASS|WARN|issued)" | head -12
   ```

**bootstrap（会话开始）不跑诊断**：
- `resolve_entry.py`（本仓 bootstrap 第一动作）**刻意不 import verify_workflow.py**（resolve_entry.py:27 「MUST NOT import verify_workflow.py: it runs BEFORE verify_workflow can be」）——它只产出 envelope JSON（版本/root/scenario 检测），**不执行任何健康检查**。
- 会话开始协议（behavior-protocol.md M4.1:210-219）只要求「读 plan-tracker / 读 snapshot / 自问阶段」，**不含**运行 check-governance。

**无后台看护载体**：
- grep 全仓「daemon/cron/schedule/timer/background run/polling」——唯一命中是 plugin-contract.md:90 对 C 级 System Automation 的**定义**，其 L102 明示「**当前状态：未实现**（MCP/headless runner 仅有协议样例，无可用实现）」。
- hooks 仅在 commit（pre-commit/commit-msg/post-commit）触发，是 commit 时点一次性检查，非持续。

### 1.2 缺陷定位（事实 → 断点）

**「能检出问题但无人自动运行」的具体机制断点**：

| 断点 | 位置 | 事实 | 后果 |
|---|---|---|---|
| **断点 1：诊断是无触发源的纯手动命令** | cmd_check_governance 定义于 verify_workflow.py:13049 | 无任何 daemon/CI/MCP 调用它 | 不跑 check-governance 就永远不知道有 40/137 问题 |
| **断点 2：bootstrap 刻意排除诊断** | resolve_entry.py:27 | 会话开始只探测 root/version，不验健康 | 即使有 40/137 问题，首会话 Agent 也看不到 |
| **断点 3：commit hook 只展示不阻断** | post-commit:188-193 | 输出被 grep 前 12 行 + `head -12` 截断；exit code 不影响 commit（`\| ... 2>/dev/null`）| commit 照常成功，问题「看见了但不拦」|
| **断点 4：无 C 级 System Automation** | plugin-contract.md:102 | C 级「未实现」；B 级「部分实现」| 不存在「风险变化时自动通知」「阶段推进自动触发 Gate 检查」等 |

### 1.3 缺什么

- 缺一个**无用户介入的持续触发面**（或在 DSH 宿主下，缺一个「会话 bootstrap 时自动跑一次缩小版 check 并汇报」的确定性步骤）。
- 缺一个**把「检测」接到「动作/阻断」的自动路径**（当前检测→动作全依赖人）。

### 1.4 修复候选（方案级，决策返 Coordinator）

- **R-D1a（推荐）** 在 bootstrap 终段（resolve_entry 之后 / 会话开始协议 M4.1 增加一步）自动运行 `verify_workflow.py check-governance --summary-only`，输出一个「健康摘要 + 首个需人工级」行，FAIL 级 breakpoint 直达用户。低成本（复用既有 check），但**需确认 DSH 会话内可自动运行 CLI**（本仓为 YES）。
- **R-D1b** 在 post-commit 把「grep 前 12 行」升级为「检查到 FAIL/WARN 汇总数并输出 exit code 语义」，让 commit 至少「看到」而非「忽略」，可选做成 advisory（不阻断 commit，只在 summary 显示 N issues）。
- **R-D1c（更彻底，成本高）** 落地 C 级 System Automation——但 plugin-contract 当前明确未实现，且「外部能力层（MCP/headless runner/CI runner）」是前提；三项目仅有 CI（tv），router 无 CI。成本高，作为 0.77+ 长线。

---

## 2. D2 风险缓解为何无闭环断言

### 2.1 机制现状（事实）

risk 治理只有两个 check：

- **Check 2（risk_domain.py:127-148 check_risk_staleness）**：解析 `| RISK-` 行（status=="打开"），只查「**日期距今 >7 天**」→ stale。**不查缓解措施**。
- **Check 8（risk_domain.py:151-210 check_risk_escalation）**：只查「**截止日期已过**」（parts[11] vs today）→ escalated。**不查缓解措施**。

`parse_open_risks`（risk_domain.py:106-124）与 `_parse_context_open_risks`（risk_domain.py:79-103）均只映射 status=="打开" 的行。**没有任何代码读取 risk 行「缓解措施」列并验证其落地**。

**check-hot-fact-source 的边界**：check_hot_fact_source_consistency（verify_workflow.py:1919-2058）只校验 plan-tracker 热数据段与发布事实的一致性（版本行/依赖链/RISK-033 关闭状态），**不**校验「风险缓解已落地」，也不校验「风险闭环」。

**Check 2/8 覆盖边界结论**：Check 2 和 Check 8 是「过期检测」与「截止检测」，**均非「缓解落地验证」**。风险条目的「当前状态」列被机械写成「打开/缓解中/活跃」，只要**写一句缓解措施**，风险即被认为「登记完成」，后续无任何 check 再触碰。

### 2.2 缺陷定位（事实 → 证据）

| 风险 | 缓解措施中「要落地」的动作 | 落地情况 | Check 2/8 是否发现 |
|---|---|---|---|
| router RISK-003「宿主接口演进」 | ①接口奇偶回归测试 ②宿主更新后跑全量测试 ③症状知识库 | **无 watchdog 实现**（风险行自述「宿主更新无预警通道（npx cache 静默刷新），依赖测试看护」——「依赖测试看护」本身又依赖人跑测试；且**第二次同型事故 FIX-003 仍由用户报**）| 不能发现（2026-08-21 更新，未>7天=不 stale；无「截止」列或不触发）。且**风险行自己也承认无预警通道** |
| tv RISK-001「公开源可用性波动」 | 多镜像并发竞速 + 本地缓存 + 自定义源导入兜底；**定期源可用性巡检** | 「定期源可用性巡检」（对应 F-07 源健康巡检）**未落地**——plan-tracker L72 明示 F-07 为 RISK-001 缓解且「不让位」但 F-07 无对应已建任务行；09-19 截止未到=Check 8 不触发，未>7天=Check 2 不触发 | 不能发现（截止 2026-09-19 未到）|
| 本仓 RISK-001「CI 缺失」 | —（注册后未建 CI，版本照发）| 注册未闭环 | Check 2/8 只查时间，无法知道「CI 是否建成」 |

**结论（推断，基于上述证据）**：`check_risk_staleness`/`check_risk_escalation` 是**时间维度**的看护，**没有**任意一个 check 是**内容维度**（缓解落地/风险闭环）的看护。risk 行「写缓解即完成」无机器断言。

### 2.3 缺什么

- 缺一个「风险缓解落地」的确定性校验：要么 check 解析 risk 行「缓解措施」列并映射到「对应任务是否已完成」，要么在 risk 关闭/缓解标记前置一个「对应贡献任务须 completed」的门禁。
- 缺一个「风险生命周期状态机」——当前只有「打开」一个有效解析态，无「缓解中/已验证/关闭」的机器判定。

### 2.4 修复候选

- **R-D2a（推荐）** 新增 `check_risk_mitigation_closure`：解析 risk 行缓解措施的 task 引用（regex `FIX-xxx`/`DEV-xxx`），若引用的 task 在 plan-tracker 中非 completed → WARN/FAIL「风险缓解声明的任务未完成」。按**内容**而非时间看护，击中三例全部。
- **R-D2b** 扩展 risk-log 状态机：从单值「打开」扩展为「打开→缓解中→已验证→关闭」，Check 2/8 之上增加「状态=缓解中 但 无关联 completed task」的 FAIL。
- **R-D2c（信息层）** 在 risk-log 模板中增加「闭环关联任务」列（必须引用一个 completion task），作为机器可解析的断言锚。

---

## 3. D3 会话纪律为何无机器保证

### 3.1 机制现状（事实）

- **必写是流程规则**：behavior-protocol.md M4.2:221-268「**MUST** 在会话结束时写入 `.governance/session-snapshot.md`」，模板含 session_id/session_date/当前状态/遗留任务/下次会话优先级等。
- **无 hook/check 强制**：
  - `post-commit`（1-265 行）任务：任务 ID 追踪（Step 2）、plan-tracker 已知性（Step3）、check-governance 摘要（Step4）、锁清理（Step5）——**不读不写不验 snapshot**。
  - `check-governance` Check 34（verify_workflow.py:19367-19538 `check_completion_recommendation`）：**只查**「`## 下次会话优先级` 段是否引用快照 ID（RECO-*/EVD-*）」（S2/S3），**不查**快照日期/新鲜度，也**不查**「会话结束是否写快照」。
  - `_snapshot_fact_source_issues`（verify_workflow.py:1883-1916，属 Check 28c）：只比较 snapshot 版本与 plan-tracker 版本一致性、snapshot 日期是否早于最新发布版本——**不校验「快照是否代表最新会话」**。
  - `resolve_entry.py` 计算 `snapshot_fresh`（resolve_entry.py:270-272，>24h 归 False）——但该值只用于**场景检测**（scenario 恢复/归档判断），**不作为「快照过期必须写」的门禁**，且返回给 Coordinator 的只是 JSON 提示，不强制。

### 3.2 缺陷定位（事实 → 证据）

| 项目 | 快照日期 | 其后 commit 数 | Check 34 是否抓到 |
|---|---|---|---|
| router | 2026-08-21 00:xx | **41** commit（至 22:07，含 FIX-001/002/003/004 系列）| 抓到「S2 无 ID 引用 WARN」，但**不报「快照过期」**——因为 Check 34 只管引用锚，不管新鲜度 |
| tv | 2026-08-19 | **85** commit（至 22:08，含 DEV/PERF 系列）| 同上（WARN，不报过期）|
| 本仓 | 2026-08-22（当前会话，新鲜）| — | Check 34 PASS |

**结论（推断）**：snapshot「必写」是**纯 LLM 纪律**，三项目中两个已实测违反（4+ 会话/85 commit 零更新），但 **check-governance 对所有此类违反给出 WARN（不阻断）且以「引用锚」为中心而非「新鲜度」**——即 D3 的核心：**没有任何机器保证「会话结束必写快照」**。

### 3.3 缺什么

- 缺一个「snapshot 新鲜度」的确定性校验（如：snapshot 日期 距 最近一次 plan-tracker/证据 commit 超过 N 天/commit 数 → WARN/FAIL）。
- 缺一个「会话结束写快照」的机器锚（例如把一个轻量 hook 或一个 check 绑定「session_snapshot 必须 ≥ 最近 commit 日期」）。

### 3.4 修复候选

- **R-D3a（推荐）** 扩展 Check 34（或新增 Check 35 `check_snapshot_freshness`）：解析 snapshot `session_date`，比较其与 `plan-tracker`/`evidence-log` 最新 commit 时间或日期，若 snapshot 明显早于最近治理 commit → WARN（渐进 FAIL）。直接命中 router/tv。
- **R-D3b** 在 post-commit 增加「snapshot-staleness advisory」：commit 后检测 snapshot 日期 < 本次 commit 日期 → 输出 `⚠️ snapshot stale — 会话结束请更新`.
- **R-D3c** 把 M4.2「必写」从流程规则升级为**可验证断言**：在 governance-status/`/governance` 输出中，快照过期时给用户一个明确「快照已过期 N 天」提示（当前 resolve_entry 已算 snapshot_fresh，只是未暴露为门禁信息）。

---

## 4. D4 自动面覆盖边界

### 4.1 机制现状（事实）

hooks 强制面（commit 时点）：

- **commit-msg（506 行）**：任务 ID 必须在（Step 2）、任务在 plan-tracker（Step 3）、证据存在（Step 4 WARN）、上任务证据链（Step 4.5 WARN）、Goal Alignment（Step 10 BLOCK）、User Impact（Step 11 BLOCK）、Fact Grounding（Step 12 BLOCK）、Breaking-Change 迁移指南（Step 13 BLOCK）、产品代码审查证据（Step 14 BLOCK）。
- **pre-commit（451 行）**：CLAUDE.md bootstrap 纪律（Step 6）、产品代码审查证据（Step 7）、commit 范围（Step 8 WARN）、Agent Team bypass（Step 9 WARN）、未跟踪文件（Step 10 WARN）。
- **post-commit（265 行）**：任务追踪 + 锁清理（见 §3.1）。

**hooks 的检查全集 = commit 元数据 + 提交内容格式/字段 + 证据字段存在性 + 审查证据存在性**。均为「**记录的格式/存在性**」约束，非「**磁盘事实与记录一致性**」约束。

### 4.2 缺陷定位（事实 → 证据）——三类「磁盘事实 vs 记录」一致性的盲区

**盲区 A：任务行状态 vs 磁盘事实一致性**
- router FIX-003 实例（已修正为已完成，见 §0）：**修复主因是人工 + 审查记录，无任何 hook/check 保证「任务行=已完成 当且仅当 代码已提交+已验证」**。check-governance 确实会在 Check 1（evidence completeness）、Check 30（review closure）捕捉「声称完成但证据缺失」，但**不能阻止「代码在磁盘但任务行未更新」或「任务行已更新但代码未提交」**——两类都无机器校验。

**盲区 B：Gate 与发布互锁**
- tv：G6/G7/G8 **pending**（plan-tracker L30-32）而 REL-004 **已完成** + tag v1.6.0=158038c。**check-governance 未报**——因为 check-gate-consistency（Check 3）只查「Gate 状态 vs 证据完备性」，**不查「发布是否绕过 pending Gate」**。
- router：G4-G7 **pending**（plan-tracker L39-42）而 v0.2.0/v0.2.1 已发布。同上，未报。
- confirm `check_release_readiness`（verify_workflow.py:6664-6740）：聚合 version/事实源/hot-fact/runtime matrix/pack status/adapter contract，=「发布就绪」检查，但**不校验「发布时刻前置 Gate 是否全部 passed」**（其详情见 §确认，未含 Gate-state 横查）。

**盲区 C：CLI/测试在 CI 的真实运行**
- tv：`.github/workflows` 存在（ci.yml，True）；但 DEV-003 行注「**本仓无 remote——首次运行/成功率统计待远端仓库后补验（无过度声明）**」→ 该 CI **从未真跑**（无远端仓库）。check-governance **未报**「声称的 CI 未真跑」——因为 check 面只查「workflow 文件存在 + 语法有效（PyYAML exit 0）」，**不查是否真正执行过**。
- router：`.github/workflows` 不存在（Test-Path False）→ 无 CI。v0.2.x 仍发布，check 未报「发布无 CI」。

**盲区 D：run 在 CI 的真实运行证据（tv 特有）**——见盲区 C，Check 30/30c/34 全是「审查记录格式/权威来源」，无「CLI 测试在 pipeline 实跑」的机器断言（tv「无 remote 从未真跑」）。

### 4.3 缺什么

- 缺一个「**任务行完成态 ↔ 磁盘/提交态**」一致性 check（file-state vs task-state 双向往）。
- 缺一个「**发布前置 Gate 必须 passed**」的横查（在 check-release 中内嵌 gate 状态检查）。
- 缺一个「**CI 真实运行证据**」check（至少校验 workflow 文件 + 最近运行记录/远端可及性，而非仅语法）。

### 4.4 修复候选

- **R-D4a** 新增 `check_task_disk_consistency`：对标记「已完成」的产品代码任务，校验其 evidence-log `事实依据` ≥1 条持久化路径 + 该路径存在 + 相关 commit 存在（git log 含任务 ID）。
- **R-D4b** 在 `check_release_readiness` 内嵌 `check_gate_sequence_for_release`：解析 Gate 状态表，任一「→发布」前置 Gate 为 pending 且存在已发布 tag → FAIL「发布绕过 pending Gate」。
- **R-D4c** `check_ci_evidence`：若 plan-tracker 声称「CI 已建立/已跑」，校验 workflow 存在 + `git log` 无 remote 时给出「CI 未真跑」WARN；若声称 CI 但 `.github/workflows` 不存在 → FAIL。

---

## 5. D5 承诺-验收差距

### 5.1 承诺点全量清单（SKILL.md/commands/behavior-protocol 中「自动/看护」语句）

| # | 位置 | 承诺语句（原文节选） | 对应的实际机制 | 分类 |
|---|---|---|---|---|
| P1 | 本仓 plan-tracker.md L7 项目目标 | **「过程自动（agent 在后台持续看护，用户专注思考而非流程管理）」** | verify_workflow.py check-governance（手动/commit 触发）+ hooks；**无后台持续看护载体**（plugin-contract L102 C 级未实现）| **有承诺无机制** |
| P2 | SKILL.md L38 | 「Coordinator 接管用户交互：只在 critical triggers 触发时通过 AskUserQuestion 打断用户；常规执行自动推进并记录假设」| interaction-boundary.md（默认自动执行，仅 critical 打断）——A 级 agent 协议 | 有机制无自动路径（依赖 agent 自觉，无机器保证 agent 会「记录假设」）|
| P3 | SKILL.md L37 | 「看护闭环：产品代码产出必须有验证证据和独立审查」| commit-msg Step 14 / pre-commit Step 7 审查证据 BLOCK（机器保证）+ Check 30 review closure | 有机制（B 级）|
| P4 | SKILL.md L36 | 「看护事实：…禁止把假设、猜测、推测或编造内容写成闭环事实」| commit-msg Step 12 Fact Grounding BLOCK + Check 18c execution-packet「事实依据」| 有机制（B 级）|
| P5 | SKILL.md L268 | 「治理基础设施（自动使用）」| hooks + verify_workflow——事件驱动自动，非持续自动 | **有机制无自动路径**（「自动使用」实为「commit 时自动」，非「后台自动」）|
| P6 | commands/governance.md L64 | 「自动分类，不问用户：命令自动检测项目状态并路由到正确场景」| resolve_entry.py + 决策树——这是**命令执行时**自动，非后台 | 有机制（但仅命令触发）|
| P7 | behavior-protocol M4.2 | 「**MUST** 在会话结束时写入 snapshot」（想传达「跨会话自动恢复」）| 见 §3——无机器保证 | **有承诺无机制** |
| P8 | SKILL.md L81 | 「SKILL.md 是『完整 Coordinator 注入』——后台自动，用户无感」| 每次会话自动加载 SKILL 注入身份——是「元数据注入自动」，但**看护动作**不自动 | 有机制无自动路径 |

### 5.2 「有承诺无机制」两类清单（明确标注）

**A 类（承诺「看护/自动」，但无持续机制）**：
- P1（过程自动/后台持续看护）——**本 D5 核心**，见 §1（无 C 级载体）。
- P7（会话结束必写 snapshot）——见 §3（无机器保证）。
- P5/P8（「自动使用/后台自动」实为事件驱动）——见 §1/§3。

**B 类（有机制，但机制非「自动路径」，依赖人触发）**：
- P2（记录假设/自动推进）——依赖 agent 自觉，无 check 验证「假设已记录」。
- P6（命令自动分类）——仅 `/governance` 命令执行时，非持续。

### 5.3 差距结论

用户读到的「自动/看护」语义（来自 L7 项目目标与 README/commands 宣示）是 **C 级 System Automation** 语义（后台持续、无人触发、风险自动通知、Gate 自动触发）。而**实际交付是 A 级（agent 协议纪律）+ B 级（CLI 检查 + commit hooks）**。plugin-contract.md L114 明文要求「**禁止用笼统的『自动』一词同时指向 A 级和 C 级能力**」——但 SKILL.md/commands 宣示与 plugin-contract 分级表**未逐条对应标注当前能力级别**，造成「承诺-验收」系统性落差（D5）。

### 5.4 修复候选

- **R-D5a** 在 SKILL.md 与 commands/governance.md 显式加入「能力分级声明」：把「自动/看护」语句逐条标注为 A 级（协议）/B 级（CLI 检查）/C 级（未实现），并引用 plugin-contract.md L114 的禁令，避免「自动」一词跨级混用。低成本、纯文档。
- **R-D5b** 把 L7 项目目标「过程自动（后台持续看护）」改写为**可验收的具体承诺**（如「每次会话开始自动运行一次健康摘要并汇报」）+ 对应机制（R-D1a），使承诺可测。
- **R-D5c** 在 README/对外宣示中明确「当前治理的自动级别 = A/B 级；C 级（后台无感看护）为 roadmap，未实现」——与 plugin-contract 分级一致。

---

## 6. 差距清单（≥10 项——每项含机制位置/缺陷类型/影响/修复候选/成本风险/优先级）

> 缺陷类型：**设计缺失**（本应存在但不存在）/ **执行纪律无机器保证**（有流程规则但无 checks/hook 强制）/ **承诺-验收差距**（承诺与交付不符）。

| # | 机制位置 | 缺陷类型 | 影响 | 修复候选（简）| 成本/风险 | 优先级 |
|---|---|---|---|---|---|---|
| G1 | plugin-contract.md:102 C 级 System Automation 未实现；无 daemon/cron/MCP | 设计缺失（缺「后台持续看护」载体）| 无自动触发面，检测全依赖人/commit（D1 根）| R-D1a bootstrap 健康摘要 | 低（复用 check）；风险：每会话 CLI 数秒 | **P0** |
| G2 | resolve_entry.py:27 刻意不跑 verify | 设计缺失（bootstrap 不诊断）| 首会话看不到既有问题（D1 断点2）| R-D1a bootstrap 一步 | 低 | **P0** |
| G3 | post-commit:188-193 只 grep 前 12 行 + `2>/dev/null` | 执行纪律无机器保证 | commit 时「看见了但不拦」诊断结果被截断；不阻断 | R-D1b 输出语义化 | 低 | **P1** |
| G4 | risk_domain.py:127-210 Check 2/8 只查时间维度 | 设计缺失（缓解落地无闭环断言）| 风险「写缓解即完成」；三例全命中（D2）| R-D2a 缓解任务引用校验 | 中（新增 check + 解析缓解列）；解析风险大 | **P0** |
| G5 | risk-log 状态机只有「打开」解析态 | 设计缺失（无风险生命周期状态机）| 无「缓解中/已验证/关闭」机器判定 | R-D2b 状态机扩展 | 中 | **P1** |
| G6 | post-commit 不写不验 snapshot；M4.2 必写是纯流程规则 | 执行纪律无机器保证（快照必写）| 三项目中 2 个违反（router 41/tv 85 commit）；跨会话断裂 | R-D3a Check 35 快照新鲜度 | 低-中 | **P0** |
| G7 | Check 34（verify_workflow.py:19367-19538）只查引用锚不查新鲜度 | 设计缺失（快照新鲜度盲区）| 快照过期被 WARN 掩盖 | R-D3a（并入）| 低 | **P1** |
| G8 | hooks（commit-msg/pre-commit）全为记录格式/存在性校验，无「任务行 vs 磁盘事实」一致性 | 执行纪律无机器保证 | 「代码在磁盘但任务行未更新」或反之不被拦（router FIX-003 曾现，人工才修）| R-D4a 任务态-磁盘态一致性 check | 中 | **P1** |
| G9 | check-governance 无「发布绕过 pending Gate」横查（check-gate-consistency 只查证据完备）| 设计缺失（Gate-发布互锁）| tv G6/7/8 pending 却发 v1.6.0；router G4-7 pending 却发 v0.2.1（D4 盲区B）| R-D4b release 内嵌 gate 顺序 | 中 | **P0** |
| G10 | check-release/check-governance 只查 workflow 语法，不查 CI 真实运行 | 设计缺失（CI 实跑证据盲区）| tv CI 从未真跑（无 remote）却不报；router 无 CI 照发（D4 盲区C/D）| R-D4c CI 证据 check | 中 | **P1** |
| G11 | SKILL.md:38/L268、commands/governance.md:64「自动/看护」宣示未标注能力级别 | 承诺-验收差距 | 用户读「自动」理解为 C 级，实际 A/B 级（D5）| R-D5a/b/c 分级声明+目标改写 | 低（文档）| **P1** |
| G12 | admin/A 级「记录假设」无机器验证 | 执行纪律无机器保证 | 「常规执行自动推进并记录假设」依赖自觉 | R-D5a 明示 A 级 + 可选 check 扫 evidence | 低 | **P3** |
| G13 | verify_workflow.py:21250 行单文件、check-governance 53 段全部依赖用户手动全面跑 | 设计缺失（无「只看门禁精简面」入口）| 用户/CI 无法低成本持续跑（每次全量 53 段）| R-D1a/b 引入 --summary-only 精简面 | 低 | **P2** |

---

## 7. 修复链建议（REQ 级表述，可验证验收信号）

> 区分「**工作流本体修复（0.76.0+）**」——须经 Governance Developer → Code Reviewer，随工作流版本发布，所有**被治理**项目受益；「**被治理项目侧探针**」——用户对 router/tv 的直接修复路径，不依赖工作流版本升级。

### 7.1 工作流本体修复（0.76.0+）

| REQ | 内容 | 验收信号（可验证） | 关联缺陷 |
|---|---|---|---|
| **REQ-145.1** | bootstrap（会话开始协议 M4.1）新增一步：自动运行 `verify_workflow.py check-governance --summary-only` 并输出「健康摘要 + 首个需人工级」（若 DSH 支持 CLI）| 新会话 bootstrap 后 stdout 含 `Governance: {N} issues` 且 `--summary-only` 只输出/含 FAIL/WARN 汇总行；无 issue 时输出 `[PASS]` | G1/G2/G13 |
| **REQ-145.2** | 扩展 Check 34 或新增 Check 35 `check_snapshot_freshness`：snapshot `session_date` 早于 plan-tracker/evidence-log 最近治理 commit 日期 → FAIL/WARN | 对 tv（85 commit 后 08-19 快照）与 router（41 commit 后 08-21 快照）实测输出 fresh 警告；本仓当前会话快照输出 PASS | G6/G7 |
| **REQ-145.3** | 新增 `check_risk_mitigation_closure`：解析 risk 行缓解措施引用的 task，若 task 非 completed → FAIL/WARN | 对 router RISK-003 / tv RISK-001（缓解引用的 F-07/奇偶测试无 completed task）实测输出警告；无此类引用时 PASS | G4/G5 |
| **REQ-145.4** | `check_release_readiness` 内嵌 `check_gate_sequence_for_release`：任一「→发布」前置 Gate pending 且存在已发布 tag → FAIL | 对 tv（G6/7/8 pending + v1.6.0）与 router（G4-7 pending + v0.2.1）实测输出「发布绕过 pending Gate」 | G9 |
| **REQ-145.5** | 新增 `check_ci_evidence`：plan-tracker 声称 CI 已建/已跑但 `.github/workflows` 不存在 → FAIL；存在但无 remote/无运行记录 → WARN「CI 未真跑」 | 对 router（无 workflow）FAIL、tv（有 workflow 无 remote）WARN | G10 |
| **REQ-145.6** | SKILL.md/commands 增加能力分级声明（A 级协议 / B 级 CLI 检查 / C 级未实现），并改写 L7「过程自动」为可验收承诺 | plugin-contract L114 禁令在 SKILL.md/commands 内被引用；L7 目标含一个可测验收信号（如「每会话开始自动健康摘要」）| G11/G12 |
| **REQ-145.7** | add `--summary-only` 精简入口子命令，使 CI/用户可持续低本跑 | `check-governance --summary-only` 只输出汇总 + 首个 FAIL/WARN 项，秒级 | G1/G13 |

**REQ-145.1/145.3/145.4/145.5 为 P0（击中用户三例实证），145.2/145.6/145.7 为 P1。**

### 7.2 被治理项目侧探针（用户对 router/tv 的直接修复路径）

> ⚠️ **用户裁决排除（2026-08-22）**：本节仅留档作证据完整性，**不执行、不纳入修复链**。项目好转由工作流本体升级随版本同步自然实现（不主动干涉被治理项目）。

| 探针 | 项目 | 内容 | 验收信号 |
|---|---|---|---|
| P-ROUTER-1（安全第一，对应 REQ-145.3）| router | 为 RISK-003 建一个真实 watchdog：①接口奇偶回归测试自动跑（把「枚举宿主 adapter 基类方法 vs twin 实现面」做成可在 CI/hook 收尾时执行的 check，而非仅「写进缓解措施」）；②把「宿主更新后跑全量测试」接上（npx cache 刷新监控或 hook）| 下一次宿主 npx cache 刷新/接口变更时，**无需用户报**即被测试/watchdog 捕获；RISK-003 缓解措施的 task 变为 completed |
| P-ROUTER-2 | router | 建立 CI（当前无 `.github/workflows`）并至少把 `verify_workflow.py check-governance` 与 `node tests/*.mjs` 纳入；G4-G7 门禁后推 v0.3.x，不要再在 pending Gate 上直接发布 | `.github/workflows` 存在；本地无 remote 时至少 WARN「CI 未真跑」；发布前 G4 通过 |
| P-TV-1（对应 REQ-145.4）| tv | 先补验/处理 G6/G7/G8 门禁（G6/G7 依赖 DEV-002/DEV-003），再考虑 1.6.x 前进；**不要再在 G6/7/8 pending 时发布** | push 到远端使 CI 真跑；`git tag` 前 G6 通过 |
| P-TV-2（对应 REQ-145.3）| tv | 把 RISK-001 的「定期源可用性巡检」（F-07）真正建成（源健康巡检任务），其对应 task completed；09-19 截止前闭环 | F-07 建成、RISK-001 缓解任务 completed、Check 8 不再「仅时间」漏看 |
| P-TV-3（对应 REQ-145.2）| tv | 修复 EVD-015 行 ragged（12 竖线 vs 11）以解除 Check 31 BLOCKED；同步 snapshot 至最新；plan-tracker 工作流版本 0.74.0 → 0.75.0 对齐 hooks | `check-governance` Check 31 不再 BLOCKED；snapshot 新鲜；版本一致 |

> **P-TV-3 中的 EVD-015 ragged 行是「被治理项目侧」问题**（该项目的治理数据格式漂移），非工作流本体缺陷——但这恰恰说明 **Check 31 这个「本应看护数据完整性」的 check 自身会因数据 ragged 而 BLOCKED**（工作流本体的看护机制在外来数据格式漂移时不健壮），回指 G1（看护无闭环 + 格式脆弱）。

---

## 8. 未验证项 / 验证计划（显式标注）

| 项 | 状态 | 验证计划 |
|---|---|---|
| 本仓「task-priority-analysis live unblocked=0」 | 基线引用，本会话未重跑（避免写入证据）| 由 Coordinator 在交付审查时运行 `task-priority-analysis` 确认 unblocked=0 |
| tv issue 计数 137 vs 基线 138 | 基线引用，差 1 | 重新全量 `check-governance`（本会话已跑 137，与基线 138 差异可能为某 check 状态变化；建议重pull验证）|
| REQ-145.1「DSH 会话内可自动运行 CLI」 | 本仓 YES（resolved_root_ok=true 且 CLI 经 pwsh 正常跑）；但**被治理项目**（router/tv）在 DSH 会话内调用 verify 是否可用需验 | 在 router/tv 分别跑一次 `resolve_entry --json` + `check-governance --summary-only`（本会话已确认两项目 plugin_home 解析正确、check-governance 可跑，故推断可用，标注为已验证通过）|
| Check 2/8「缓解落地」盲区（G4）在其余被治理项目的泛化 | 推断（基于三例同模），未穷尽 | 扩展审计到更多已接入项目，确认「写缓解即完成」为普适模式 |
| 后台看护替代方案（daemon/MCP/CI）在 DSH 宿主的可行边界 | 推断（C 级为 roadmap）| 需 Architect 评估 DSH 下 C 级落地的宿主能力（是否支持 MCP/headless runner）|

---

## 9. 自检硬门槛

| 门槛 | 达成 |
|---|---|
| 1. 只读诊断：未改产品代码/infra/.governance；仅写 `docs/requirements/audit-145-watchdog-gap-0.76.0.md` | ✅ 唯一写操作 = 本报告 |
| 2. 每项结论带可复查证据（文件+行号/命令输出）；无证据断言标注为推断 | ✅ 见各处（行号引用均经 Read/输出验证；推断处标注「推断」）|
| 3. 回答 D1-D5 完整；差距清单 ≥10（实 13 项）含修复候选+优先级 | ✅ §1-§6 |
| 4. 修复链按 REQ 级（含验收信号）；区分本体修复 vs 项目侧探针 | ✅ §7 |
| 5. 不做技术决策、不选方案落地——方案级输出，决策返 Coordinator | ✅ 全部为方案级描述 |

---

## 10. 关键发现前 10 条（返 Coordinator）

1. **根因是设计缺失，非项目纪律**：工作流全部看护是事件驱动（commit/手动），无 C 级 System Automation 载体（plugin-contract.md:102 未实现）→「检出问题→动作」依赖人/Agent 主动，即用户观测的「全靠人发现」。
2. **bootstrap 刻意不诊断**（resolve_entry.py:27 不 import verify）→ 即使有 40/137 问题，首会话 Agent 不可见。
3. **post-commit 只看不拦**（post-commit:188-193 只 grep 前 12 行 + 忽略 exit code）→ commit 时「看见了但不阻断」。
4. **风险缓解无闭环断言（最强命中）**：Check 2/8 只查时间维度，无任一 check 验证缓解落地（router RISK-003、tv RISK-001、本仓 RISK-001 三例全命中）。
5. **snapshot 快照必写无机器保证**：M4.2 是纯 LLM 纪律，post-commit 不写不验；Check 34 只查引用锚不查新鲜度（router 41/tv 85 commit 零更新）。
6. **Gate-发布互锁盲区**：tv G6/7/8 pending 却发 v1.6.0、router G4-7 pending 却发 v0.2.1；check-release 不校验前置 Gate。
7. **CI 真跑盲区**：tv workflow 存在但「无 remote 从未真跑」、router 无 CI 照发；check 只查语法不查实跑。
8. **承诺-验收差距**：plan-tracker L7「过程自动/后台持续看护」与 plugin-contract L114「禁止自动跨级混用」冲突；实际交付 A/B 级，宣示读作 C 级。
9. **router FIX-003 实例佐证**：任务行 vs 磁盘事实不一致被人工修复——system 无机器保证（D4 活证）。
10. **tv Check 31 脆弱**：外来数据 ragged（EVD-015 12 竖线）即使本应作为「数据完整性看护」的 check 也 BLOCKED——看护机制对格式漂移不健壮。
