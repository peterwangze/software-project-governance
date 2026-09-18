# 审查报告 — FEAT-036-CODE-R0

- **任务**: FEAT-036 — Snapshot 双契约（完整机器 artifact + 默认交互视图 ≤8 字段）
- **Round**: 0（无前轮 findings 可引用——首轮审查）
- **审查者**: Code Reviewer Agent（只读审查；唯一写操作 = 本报告）
- **审查对象**: 工作树未提交变更集
  1. `commands/governance.md`（668 行）
  2. `commands/governance-status.md`（166 行）
  3. `skills/software-project-governance/infra/tests/test_verify_workflow.py` — `test_governance_snapshot_dual_contract_default_view_guard`（L9554-9598）
- **验收口径**: `.governance/change-triage/FEAT-036.json` — 默认视图 ≤700 tok / 权限风险·FAIL·证据缺失不隐藏 / artifact 保留 24 字段
- **方法与限制（事实依据红线声明）**: 审查者工具面无 Bash/pwsh——`git show/diff` 不可用。HEAD 对照改用三重事实锚：(a) `project/e2e-test-project/commands/governance.md`（636 行，保留重写前面貌，充当旧版 docs 契约快照）；(b) 引擎现状 `verify_workflow.py`（`build_delivery_trust_snapshot` L9069-9156 / `cmd_status` L10851-11036 / `cmd_first_run_demo` L11138-11156 / pack 契约 L2679-2728·L5160-5228）；(c) 测试合法样例（test L3656-3664）。**运行时命令（pytest / check-governance / status 实跑）均未执行**——凡涉运行时的结论均标注"静态核验/未实测"。

---

## 一、五维度审查

### 维度 1：正确性

- 默认交互视图 compact 块在两文件中均为恰 8 条字段行（Mode / Stage/Gate / Tasks / Risks / Health / Next / Decision / Full），与"≤8 字段"契约一致；"Full 指示行计入 8"的边界口径在契约文本与守护测试两处一致，无歧义。
- FEAT-034 时序衔接明确：ask 前「最小状态行」= 一行压缩子集（Mode + Stage/Gate + Risks 计数 + carry-over），ask 后 = 8 字段全量（governance.md:508 / governance-status.md:58）。
- **P1-1（见 findings）**：完整机器契约"24 字段（与 status 输出逐字一致）"的载体声明与引擎现实不符——`build_delivery_trust_snapshot` 返回 **20 键**（无 Pack summary/Default packs/Enabled packs/Pack boundary）；`status` 文本面 Snapshot 段只打印该 20 键（L10961-10964）；`status --json` 的 `delivery_trust_snapshot` 对象即该 20 键 dict（L10926）；`first-run-demo --assert-snapshot` 断言 **19 字段**（`FIRST_RUN_DEMO_REQUIRED_FIELDS` L9159-9179，缺 Flow-unit lanes 与 4 个 Pack 字段）。4 个 Pack 字段在三个声明载体中均不可达——它们是 doc-surface 契约 token（`check-governance-pack-status` L5201-5228 校验 4 个 docs 文件），不是任何 CLI snapshot 输出的组成部分。
- 其余叙述与引擎/事实一致：Snapshot 字段名逐字核对（20 键含 "Gate/setup status"、"Flow-unit lanes" 均与引擎键一致）；`Full:` 指示行指向的命令与对象名真实存在。

### 维度 2：安全性

- **异常不隐藏红线——逐字在场且语义成立**：governance.md:486（折叠红线）、:498（Mode 行 hooks installed|missing）、:502（Health 位 deferred→「待检查」不得显示为通过 + FAIL/证据缺失一行内联）、:509（Risks 必须含最高升级项）；governance-status.md:52、:59（Risks/Health/Mode 必须携带异常位）、:116、:152。折叠/瘦身未把 fail-closed 偷换成静默——Health 的 deferred 语义显式禁止绿色通过外观。
- no-overclaim 措辞安全：governance.md:526-527 与 governance-status.md:69 的 Pack boundary / No-overclaim 行含全部 boundary tokens；对 `GOVERNANCE_PACK_STATUS_FORBIDDEN_OVERCLAIMS` 与 direct claims（含 "1.0.0 production-ready"）经 `_line_has_scoped_claim_negation`（L5078-5157，pre/predicate/post markers 均含中文否定「不是/不等于/避免/未」）静态推演构成 scoped negation，不触发 forbidden overclaim——与测试合法样例（test:3663）逐字同构。**静态核验，运行时未实测。**

### 维度 3：可维护性

- 双契约"同一口径、两文件同步面 + 单一守护测试双文件巡检"结构合理；同步面显式声明（governance-status.md:43「本文件为同步面」）。
- **P2-2**：governance-status.md:153 自校验项在"完整 **24 字段**机器契约（…）"括号内实际枚举 **25** 个 token——多出的 "Existing governance state detected" 是 `Resume state` 字段的值而非字段名（governance.md:519 的清单恰 24）。字段计数滑移恰是本任务要消灭的问题类型。
- **P3-2**：字段命名不一致——"Gate/setup status"（引擎键 / governance.md:519）vs "Gate setup status"（governance-status.md:97）。
- cross-refs 自修复核实：governance-status.md:43 以 `/governance` 命令指称（grep 证实 governance-status.md 内无 `commands/governance.md` 路径引用），路径环已断；governance.md:534 残留单向 `commands/governance-status.md` 路径引用，不成环。

### 维度 4：性能

- **P2 级以下（通过，附注）**：≤700 tok 预算静态推演复核——8 字段典型值长度合计 ≈160-280 tok，最坏（Next 三候选全展开 + Health 异常摘要内联）≈350-450 tok，≤700 契约预算成立，相对 AUDIT-154 基线（改造前 24 字段强制生成 ≈0.8-1.0K tok/次）方向正确。文档已按 DEC-205 如实标注"推演值非实测"（governance.md:510）。无实测数据——预算验收按推演口径通过。

### 维度 5：测试覆盖

- 新守护测试 `test_governance_snapshot_dual_contract_default_view_guard`（test:9554-9598）为**结构断言**而非纯 token 标记：`len(compact_labels)==8` 自检 + 逐文件 (a) 10 个双契约 marker 在场、(b) 正则提取「默认交互视图合约」后代码块、字段行计数**恰 8**、(c) 8 个 label 全在场、(d) 4 个 full-face-only label **反断言**不得泄漏进 compact 块、(e) "Flow-unit lanes" 在案。防回归强度 Adequate——优于标记级。
- 覆盖缺口：fixture（e2e-test-project/commands/*）不在新守护面（旧测试 `..._docs_require_delivery_trust_snapshot_contract` L9496-9552 仍覆盖 fixtures 的 token 在场，故不回归）；预算 ≤700 tok 无静态守护（本质不可静态锁定，可接受）；字段顺序未锁定（可接受）。

---

## 二、Developer 申报逐项核实

| # | 申报 | 结论 | 证据 |
|---|------|------|------|
| 1 | 异常不隐藏红线 | ✅ 成立 | governance.md:486/498/502/509；governance-status.md:52/59/116/152 逐字在场；deferred→「待检查」fail-closed 语义保留 |
| 2 | ≤8 字段计数 | ✅ 成立 | compact 块两文件均恰 8 条字段行；"Full 算第 8 项"边界口径契约与测试一致（测试 L9575 自检 `len==8`） |
| 3 | 机器契约 24 字段可达 | ❌ **不成立（P1-1）** | status 文本面/`--json` 载体均 20 字段（L9120-9156/L10926/L10961-10964）；first-run-demo 断言 19 字段（L9159-9179）；Flow-unit lanes 在 20 内 ✓；4 个 Pack 字段三载体均不可达 |
| 4 | 预算推演 ≈260 tok ≤700 | ✅ 成立（推演口径） | 静态复核典型 ≈160-280 tok / 最坏 ≈350-450 tok；DEC-205「推演值非实测」已如实标注；无实测 |
| 5 | 固定语义行六行原样 | ⚠️ 部分 | 相对 docs 旧版（fixture:492-499）六行逐字原样 ✓（含 Pack boundary 冒号形）；但 Question budget 行与**引擎** L9146-9149 非逐字（P2-1），"与 status 输出逐字一致"声明对该行不成立；Preset guidance（L9142-9145）、No-overclaim（L9151-9155）与引擎逐字 ✓ |
| 6 | 两个自修复 | ✅ 成立 | cross-refs：governance-status.md:43 改 `/governance` 指称、路径环已断（governance.md:534 残留单向引用不成环）；Pack boundary 冒号：governance.md:526 与测试合法样例 test:3663 逐字一致、10 个 boundary tokens 全在场、negation validator 静态通过——PASS 声明与代码现状一致（运行时未实测） |
| 7 | 未动面 | ⚠️ 无法独立核实（工具受限）+ 结构自洽 | Bash 禁→无 git diff；间接证据：引擎 snapshot 20 键/断言 19 字段为既有形态、governance-init.md 无双契约标记（grep 无匹配）；triage files 列表含 verify_workflow.py 属计划面非修改证明。**标"未验证（结构自洽）"** |
| 8 | AI 专项 | ✅ 见第五节 | 无 mock 滥用/幻觉 API/TODO/过度实现 |

---

## 三、特别审查点

1. **双契约边界清晰度**：默认视图与完整契约的使用时机（first-run/status path 默认 8 字段；显式请求或高风险场景渲染完整面）两文件均明确；FEAT-034 衔接（ask 前最小状态行 / ask 后 8 字段）契约内明确。缺口：8 字段 → 24 字段无显式映射表，Health 字段在完整契约中**无对应物**（其数据源是 `check-governance`，非 snapshot 字段）——按 Full 指示行取 artifact 的消费者拿不到 Health（P3-1）。
2. **守护测试强度**：结构断言（计数恰 8 + 泄漏反断言 + marker 在场 + Flow-unit lanes 在案），非纯标记级；不锁顺序/预算/fixture——防回归强度 Adequate，回归主要路径（字段增删、full-face 泄漏、载体措辞丢失）已覆盖。
3. **fixture 漂移披露**：确认漂移——fixture governance.md **636 行** vs canonical 668 行（申报称 637，微差不影响结论）；fixture 无任何双契约标记（grep `默认交互视图合约|≤8 字段|Full: 24-field` 零匹配），旧 23 字段契约（fixture:443，无 Flow-unit lanes）仍在。风险定级 **P2**：不影响用户面（fixture 是 e2e 场景道具，context-discovery 验收不消费其 Scenario F 行为），但若以 fixture docs 为行为样本会复活 24 字段强制生成。归属：Developer 建议另立事项合理（可挂 FEAT-040 四平台投影同步）。
4. **44 个 health issues**：plan-tracker 证实 FEAT-035/039/040（占位契约任务）均 ⏳ 待执行、FEAT-036 本体在审（plan-tracker:84-88）——"占位预存面、非本次引入"的归属判断与静态证据一致；**运行时计数未验证（Bash 禁）**。另：本次措辞经静态分析未发现新增 pack-overclaim FAIL 面（见维度 2）。

---

## 四、Findings 清单

### P1（关键——原则上本轮修改）

- **P1-1 完整机器契约"24 字段三载体可达"声明与引擎现实不符**
  - 位置：governance.md:512-519（"24 字段全量"/"与 status 输出逐字一致"）、:505（Full 指示行）、:529-530（"两端可达，缺一不可"/"断言全部字段"）；governance-status.md:60-62、:97、:123。
  - 事实：`status` 文本面 Snapshot 段 = 20 字段（verify_workflow.py:10961-10964）；`status --json` `delivery_trust_snapshot` = 20 键（:10926，dict 构造 :9120-9156）；`first-run-demo --assert-snapshot` 断言 19 字段（:9159-9179）。Pack summary/Default packs/Enabled packs/Pack boundary 四字段是 doc-surface 契约（:2679-2690 + :5201-5228 校验 docs 文件），不在任何声明的 CLI 载体输出中。
  - 影响：triage acceptance"artifact 保留 24 字段"按字面不可核验（CLI artifact 实为 20 字段）；消费者按 Full 指示行取 `status --json` 得不到 24 字段；"断言全部字段"实为 19/24——契约在 no-overclaim 敏感面自身过度声明。
  - 归因：继承性漂移——旧版 docs（fixture:443，23 字段）已把 pack 字段画进 snapshot 契约而引擎从未输出；FEAT-036 重写规范化为 24（补 Flow-unit lanes ✓）但未修正载体口径，且以更强措辞（"两端可达缺一不可"/"断言全部字段"）固化。
  - 建议（二选一，不动引擎为原则）：(a) docs 侧拆口径——"20 字段 CLI snapshot 契约（status 文本面/--json；first-run-demo 断言其中 19）+ 4 字段 pack doc-surface 契约（check-governance-pack-status 守护）"，同步修正 Full 指示行、:529-530 与 governance-status.md:60-62/97/123 的表述；(b) 若坚持 24 字段单契约，则经 triage 扩引擎（超出 FEAT-036 申报边界，需另立变更）。同步把 P2-2 的 25-token 枚举一并修正。

### P2（建议）

- **P2-1 Question budget 固定语义行与引擎非逐字**：governance.md:523 / governance-status.md:70 = "no more than 3 …; deferred non-critical fields become assumptions"；引擎 :9146-9149 = "ask no more than 3 …; record deferred non-critical fields as assumptions"。语义等价，但"固定语义行（…与 status 输出逐字一致）"声明对该行不成立。建议对齐引擎原文或把该行移出"逐字一致"声明范围。
- **P2-2 "24 字段"枚举滑移**：governance-status.md:153 括号内 25 token（多 "Existing governance state detected"——`Resume state` 的值）。建议删除该 token 使计数与声明一致。
- **P2-3 e2e fixture 漂移未同步**：fixture 636 vs canonical 668 行；fixture 无双契约标记、旧 23 字段契约在场（fixture:443）；新守护测试不覆盖 fixtures。Developer 已披露并建议另立事项——同意；建议挂入 FEAT-040 投影同步或新立 task，0.84.0 发布前闭环。

### P3（讨论）

- **P3-1 Health 字段在完整契约无对应物**：Health 数据源是 `check-governance`（非 24 字段 snapshot 字段），按 Full 指示行取 artifact 拿不到 Health。建议在契约节加一行映射注脚（Health → `check-governance --summary-only`）。
- **P3-2 字段名不一致**："Gate/setup status"（引擎/governance.md:519）vs "Gate setup status"（governance-status.md:97）。建议统一为引擎键名。

---

## 五、AI 生成代码专项（5 项）

1. **mock/占位**：新测试读真实仓库文件，无 mock 滥用 ✅
2. **硬编码敏感信息**：无密钥/token/密码 ✅（marker 硬编码属文档契约守护测试本职）
3. **幻觉 API**：`re.search/read_text/subTest/DOTALL/vw.ROOT` 均真实存在且用法正确 ✅
4. **TODO/残桩**：变更面无 TODO/FIXME/占位实现 ✅
5. **过度实现**：docs 重写未扩引擎、测试 45 行克制、无投机功能 ✅

---

## 六、硬门槛自检

- P0 = 0 ✅
- 5 维度全覆盖 ✅（每维度见第一节）
- 每条发现 P0~P3 分级 ✅（P1×1 / P2×3 / P3×2）
- 设计一致性（triage acceptance）：默认视图 ≤700 tok ✅（推演口径）；异常不隐藏 ✅；artifact 保留 24 字段 ❌（P1-1——按字面不成立）
- AI 专项 5 项 ✅

## 七、遗留项与复审指引

- P1-1 修复仅涉 docs（+可选同步 P2-1/P2-2）→ 返工后 **round 1 复审**，重点核验载体口径改写后与引擎事实一致、Full 指示行可达性声明可核验。
- P2-3 转跟踪（另立事项/挂 FEAT-040），不阻塞本任务合并。
- P3×2 可随 P1-1 顺手机改，不强制。

---

## 结论：NEEDS_CHANGE（P0=0/P1=1/P2=3/P3=2）

阻断依据：P1-1——完整机器契约的载体可达性声明与引擎现实不符（24 字段声明 vs 20 字段 CLI artifact / 19 字段 demo 断言），triage acceptance 第三条（artifact 保留 24 字段）按字面不可核验。无 P0；异常不隐藏与 fail-closed 语义完好；修复成本低（docs 措辞拆口径），修复后复审可达 APPROVED。
