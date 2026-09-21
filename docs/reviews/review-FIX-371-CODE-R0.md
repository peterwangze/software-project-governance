# REVIEW-FIX-371-CODE-R0 — 代码审查报告（Round 0）

> **Round 声明**：R0（首轮审查，无前轮 findings 可比对）。工作树直读模式——无 patch 文件、无 HEAD diff 访问（Bash 禁用），全部结论基于工作树静态直读 + `.governance/plan-tracker.md` 活体锚点核验。
> **审查对象**：`skills/software-project-governance/infra/verify_workflow.py`（豁免判据/账本/打印面）+ `skills/software-project-governance/infra/tests/test_verify_workflow.py`（HistoricalExemptionTests 四用例 + 7 处 fixture ✅→🔄 翻转）。
> **审查依据**：`agents/code-reviewer.md` + `skills/code-review/SKILL.md`；DEC-227 路线 b（✅ 终态 EVD 行自 Check 16/17 检查集豁免并留痕、新增/活跃行零豁免 B-11 红线）。
> **执行申明**：Reviewer 未修改任何产品代码（唯一写入 = 本报告）；未执行 Bash/命令（含测试复跑）——Developer 披露的 54P / 31→5 FAIL 数字标注为「采信披露、未独立复跑」。

---

## 一、审查结论

## **NEEDS_CHANGE**（P0 = 0；阻塞项 = 1×P1；unresolved_blockers = 1）

**结论理由（事实锚定）**：DEC-227 路线 b 的核心验收承诺是「豁免并**留痕（不静默）**」。静态证据表明豁免账本的**主运行打印面缺失**：

- `verify_workflow.py` **L15502-15534**（主运行 Check 16 打印块）与 **L15536-15565**（主运行 Check 17 打印块）——**均无任何 `historical_exempted` 输出**。全文件 `historical_exempted|exempted` 检索（本轮 grep，44 处匹配逐一核对）证实主运行面零披露。
- 结果字典**有**账本（L12620 / L12716 `result["historical_exempted"] = ...`），独立子命令面**有**披露（L21451-21454 / L21489-21492）。
- 后果：审计者读主运行输出只见 `Impact analysis entries: 5`，**无法得知 26 行被豁免**——「不静默」承诺在最高频消费面失守。Developer 披露语「真实面 Check 16/17 各 31→5 FAIL + exempted 26 显式」仅对**独立子命令面**成立（静态代码证据），主运行面不成立。

**定级说明（透明裁决）**：按 SKILL 字面（仅 P0 阻塞合并），P1 可「有遗留计划有条件合并」；本报告将 F-1 升格为**本轮阻塞**，依据是它是**票内验收判据缺口**（非一般性质量隐患），且修复成本极低（每面约 2~4 行 print）。Coordinator 若有异议可以决策覆写，但 Reviewer 的诚实裁决是：验收承诺未在主兑现面成立，不应以 APPROVED_WITH_NOTES 放行。

**修复建议（F-1）**：在 L15512 后与 L15540 后各插入与子命令面同构的披露块（建议仿 L15358-15366 M5 面的有界披露样式）：

```python
exempted = ga_result.get("historical_exempted", [])
print(f"│  Historical exempted (FIX-371/DEC-227 ✅-terminal, skipped): {len(exempted)}")
for row in exempted[:8]:
    print(f"│    - {row['task_id']} ({row['evd_id']}): {row['status']}")
if len(exempted) > 8:
    print(f"│    ... and {len(exempted) - 8} more")
```

（Check 17 同构；`.get(..., [])` 防御式取值与子命令面口径一致。）

---

## 二、特别复核点逐项裁决（任务指令 MUST 六项）

### 1. 豁免判据正确性 —— 通过（附 P2 注记）

- **双形态定位**：`_plan_hot_tracker_task_statuses()`（L12210-12252）以「首个 ✅ 前缀 cell，否则末 cell」定位状态列——紧凑 7 列（状态=末列）与 legacy REQ 形态（状态=倒数第二列）均可命中。活体验证：plan-tracker L82 REL-082 `✅ 规划闭环…`、L85 FEAT-058 `✅ M-1 完成…` 均被 ✅ 前缀命中。
- **子集保证由构造成立**：parse 级 completed 集与 hot id 集出自**同一个 statuses dict**（L12521-12527），文档声称的「exemption set ⊆ id set」不依赖边界巧合，恒真。
- **漏豁免方向 = fail-closed**：状态列 ✅ 不在词首（如「已完成 ✅」）→ 回退末 cell → 不豁免 → 保守方向（多 FAIL，不弱化）。
- **误豁免方向（P2-2b）**：活跃行的**非状态 cell 以 ✅ 词首**（如任务描述列「✅ 已交付 X」）会被误认状态 → 违反「活跃行零豁免」。活体检查（grep L82-L101 活跃表）当前无此形态行，但判据是启发式。建议后续改为**自右向左**取首个 ✅ cell 或锚定状态列位次。
- **节段边界**：`## 当前活跃事项` → `### 最近完成` break（L12225-12229），**无 `## ` 终止、无挂起/恢复**——与 `parse_current_active_tasks` 的 FIX-287③ 状态机（L12405-12437，四 marker + 顺序容忍）**不一致**。方向分析：越界扫入的行同时进 id 集与 completed 集（同源 dict），非 ✅ 越界行只会**多产 entry**（保守）；`### 最近完成` 前置（EV-071 型）→ statuses={} → 零豁免（fail-closed）。属 FIX-287 R0 已登记的 F-2 遗留族延续，本 diff 未使其恶化——不阻塞，记 P3-1。

### 2. B-11 行为变更裁决（核心）—— 可接受，附 P2 必要收尾

- **受影响消费方全景**（grep 全仓核实）：`parse_impact_analysis_entries_with_exemptions()` 直接消费方 = Check 16（L12619）+ Check 17（L12715）；wrapper `parse_impact_analysis_entries()` 存量消费方 = **`_current_release_impact_entries()`（L12855，FIX-080 事实依据检查 Check 18 的取数函数）**——即 Developer 披露的「事实依据检查历史面静默」确切位置。
- **裁决：属 DEC-227 理据内的可接受连带，不需收窄到各 Check 判定层**，理由：(a) Check 18 自身有 FIX-080 既有历史容忍设计（L12848-12850 docstring：只执法活跃版本行、不为历史证据追溯 FAIL）；(b) 被静默的行按定义是 ✅ 终态任务行（DEC-227 的历史面语义）；(c) 豁免下沉到判定层的重构收益低而扰动面大。
- **但「不静默」义务在该消费方未闭环（P2-1）**：Check 18 取数路径无账本可用（wrapper 丢弃豁免账本）。要求：**修订 DEC-227 入账**（decision-log 实施注记），明列三个受影响消费方 + parse 级应用位置 + Check 18 历史面静默的明示承认。这是记录面动作，不是代码动作。

### 3. 语义不弱化红线 —— 通过

- **负例钉死**：`test_goal_alignment_zero_exemption_for_non_checkmark_statuses`（test L12428-12444）覆盖 🔄/📋/纯文本三形态，断言 `entries == 3` 且 `historical_exempted == []`；Check 16/17 各有「活跃行仍 FAIL」断言（L12422-12423 / L12457-12460）。红线下界被测试钉住。
- **7 处 fixture ✅→🔄 翻转零弱化（构造性论证 + 抽样锚点）**：id 集成员资格与状态 cell 内容无关（statuses dict 收全行，L12251 无状态过滤），✅→🔄 只会把行从「（新代码下的）应豁免」移向「受检」——**方向单调向严**，旧断言（这些行在 entries 中 / 仍 FAIL）在翻转后必然继续成立。抽样锚点：FIX-349 ③ 测试（L12355-12358）期望 entries=[REQ-094, REQ-095]，REQ 行翻转为非 ✅ 后该断言在新代码下保持。**局限披露**：无 diff 访问，7 处翻转位点未逐一目验——按变更方向分析判定，标注为「构造性验证」。
- **REQ-092 红线活体实证（独立核验）**：plan-tracker **L439** REQ-092 状态 = `🚧 blocked 证据已交付`——非 ✅ 前缀 → 不豁免 → 其 EVD 行留在检查集 → Check 16/17 FAIL 保持。红线活体成立。

### 4. 向后兼容 —— 通过

- wrapper `parse_impact_analysis_entries()`（L12486-12501）签名与返回类型不变（仅返回非豁免 entries），向后兼容由 `test_parse_ledger_discloses_live_evd_1118_1119_disposition` 显式断言（test L12484/12490）。
- `check_goal_alignment` / `check_user_impact` result **仅增键** `historical_exempted`（L12606/12620、L12709/12716）；子命令 CLI 参数面零变更（Developer 披露 ③「--summary-only 非该两子命令注册参数」经核实为简报笔误，非代码问题）。
- 打印面用 `result.get("historical_exempted", [])`（L21451/21489）防御旧 result 形态。

### 5. 留痕充分性 —— **不通过（本轮唯一阻塞项 F-1）+ 两个非阻塞缺口**

- 账本结构（evd_id/task_id/status，L12571-12575）✓；子命令面逐行披露（L21453-21454/L21491-21492）✓；result 机器可读 ✓。
- **主运行面零披露**（L15502-15565）——见第一节，F-1 阻塞。
- Check 18 消费方无账本可用（B-11 面）——记录面收尾，P2-1。

### 6. 五维度 + AI 专项 5 项 —— 见第三、四节，全过（附注记）。

---

## 三、五维度逐项结论

| 维度 | 结论 | 依据（文件:行） |
|------|------|----------------|
| 正确性 | ✅ 通过（附 P2-2 注记） | 逐行读 L12202-12584/12587-12716：豁免判据、子集构造保证、fan-out 按任务粒度豁免（L12567-12583：同 EVD 行 ✅ 任务豁免+活跃任务保留并存）均正确；边界（空 cell/ragged 行 len<8 跳过 L12534）fail-closed |
| 安全性 | ✅ 通过 | 零新增输入面；只读既有两文件（utf-8 显式编码 L12221/12518）；无密钥/注入面；豁免不产生写路径 |
| 可维护性 | ✅ 通过（附 P3 项） | 命名清晰、docstring 承载决策引用（DEC-227/B-11/FIX-368）；P3-2 死代码、P3-4 docstring 不精确措辞见下 |
| 性能 | ✅ 通过 | 每 check 一次 plan-tracker 读（复用 statuses dict 避免二次扫描），量级与改造前持平 |
| 测试覆盖 | ✅ 通过（附 P3-3 缺口） | 4 新用例覆盖主线红→绿、三形态负例、Check 17 同判、活体映射+wrapper 兼容；缺口：legacy REQ 双形态豁免路径、同 EVD 行 ✅+🔄 混合 fan-out 无专测 |

## 四、AI 代码专项 5 项

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | ✅ 无 | 测试用 tempfile + patch SAMPLE_PATH/EVIDENCE_PATH（标准隔离手法），无断言短路型 mock |
| 2 | 硬编码返回值 | ✅ 无 | 豁免/账本全为真实文件解析产物，无捷径返回 |
| 3 | 幻觉 API 调用 | ✅ 无 | 所调函数/常量（`_split_governance_table_row`/`_governance_table_cells`/`expand_task_ids`/`_current_release_task_ids`/`_is_product_code_location`/`_is_review_evidence`/`_is_audit_or_review_type`/`_COMPLETED_STATUS_PREFIX`）均实存于同文件（grep 核验） |
| 4 | 未实现 TODO | ✅ 无 | 无 TODO 残留；遗留债务以注释显式披露（L12239-12243 双形态说明） |
| 5 | 过度实现 | ✅ 无 | 修改面聚焦本票；wrapper 保留为兼容 shim；无顺手改无关面 |

## 五、硬门槛裁决

| 门槛项 | 结果 |
|--------|------|
| P0 阻塞问题数 | **0** ✅ |
| 5 维度全覆盖 | 100% ✅（第三节） |
| 每条发现标注级别 | 100% ✅（第六节） |
| 设计一致性（DEC-227 路线 b） | 已完成——豁免语义与决策字面一致（✅ 前缀终态豁免+留痕）；**主运行面留痕缺口 = 验收判据缺口（F-1）**；B-11 连带裁决见复核点 2 |
| AI 专项 5 项 | 全部完成 ✅（第四节） |

## 六、发现清单

| # | 级别 | 位置 | 描述 | 建议 | 处置 |
|---|------|------|------|------|------|
| F-1 | **P1（本轮阻塞）** | verify_workflow.py L15502-15534（Check 16 主运行打印块）、L15536-15565（Check 17 主运行打印块） | 主运行面不输出 `historical_exempted` 账本——DEC-227「留痕不静默」在最高频消费面失守；审计者只见 `entries: 5` 不知 26 行被豁免。Developer 披露「exempted 26 显式」仅对子命令面（L21451-21454/L21489-21492）成立 | 两面各插入与子命令面同构的披露块（代码见第一节，建议有界 ≤8 行+溢出省略）；若存在主运行面打印测试则同步加断言 | **本轮修复 → R1 复审比对项** |
| F-2 | P2 | decision-log（记录面）+ verify_workflow.py L12855 | B-11 连带：Check 18（FIX-080 事实依据）经 wrapper 取数，历史 ✅ 面静默且该消费方无账本可用。裁决为 DEC-227 理据内可接受（Check 18 自有 FIX-080 活跃面执法设计），但「不静默」义务需记录面闭环 | DEC-227 入账修订：明列三个消费方（L12619/L12715/L12855）+ parse 级应用位置 + Check 18 历史面静默明示承认 | 记录面动作，可与 F-1 同轮完成 |
| F-3 | P2 | verify_workflow.py L12244-12250、L12257-12261 | 豁免判据与 FIX-292 权威终态谓词 `_status_is_completed_cell`（L12375-12402）语义双源：混合链「🔄 … → ✅ 完成」按 W-7 是终态但不被豁免（非 ✅ 词首）→ 该类任务的缺字段 EVD 行持续假 FAIL（保守方向，不弱化）。另：首个 ✅ cell 启发式存在活跃行非状态 cell ✅ 词首误豁免的理论向量（活体当前无此形态） | 后续票：以决策显式选定口径——改用 `_status_is_completed_cell`（扩大豁免面，需 DEC-227 修订）或维持窄口径并在 docstring 记录与 FIX-292 的刻意分叉；误豁免向量可改自右向左扫描消解 | 遗留候选（不阻塞本轮） |
| F-4 | P3 | verify_workflow.py L12264-12266 | `_plan_task_ids_from_hot_tracker` 现为**零调用方死代码**（全仓 grep：仅定义+docstring 引用；原消费位已改用 statuses dict） | 后续清理票：删除或显式标注 compat shim（docstring 注明无存量调用方） | 遗留候选 |
| F-5 | P3 | verify_workflow.py L12255-12261 vs L12522-12526 | `_completed_plan_task_ids_from_hot_tracker` 被绕开（parse 为避免二次文件读在已有 statuses dict 上内联推导 completed 集——合理），helper 成为孤儿 | 二选一：删除，或 docstring 注明仅供外部/测试消费 | 遗留候选 |
| F-6 | P3 | tests/test_verify_workflow.py HistoricalExemptionTests | 覆盖缺口：legacy REQ 形态（状态=倒数第二列）豁免路径、同 EVD 行 ✅+🔄 混合 fan-out 无专测；fixture plan 行均为紧凑 7 列 | 补两用例（可与 F-1 修复同轮顺手，不强制） | 遗留候选 |
| F-7 | P3 | verify_workflow.py L12216-12217 | docstring「Status cell = last table cell — the same authoritative read parse_current_active_tasks uses」对 legacy 行不精确（✅ 词首覆盖优先于末 cell） | 措辞勘正（「compact 形态与 parse_current_active_tasks 同源；legacy 形态按 ✅ 词首覆盖」） | 遗留候选 |
| F-8 | P3 | project/e2e-test-project/…/verify_workflow.py L6785/6992 | e2e 夹具副本仍为 FIX-371 前旧代码（含旧 `_plan_task_ids_from_hot_tracker` 消费）——再生式夹具的已知漂移，非本票引入 | 随下次夹具再生消解 | 观察 |

## 七、验证局限与诚实披露（Reviewer 侧）

1. **未独立复跑测试/命令**：角色工具约束（Bash 禁用）。Developer 披露的「TDD 4F→54P（指定 -k 面）」「真实面 31→5 FAIL + exempted 26」标注为**采信披露**；本报告对其中的静态可验证部分（代码路径、打印面有无、活体状态行）已独立证实/证伪——其中「exempted 26 显式」被证伪于主运行面（F-1）。
2. **无 diff 访问**：7 处 fixture 翻转按变更方向分析判定零弱化（复核点 3），非逐位点目验。
3. **Developer 四项披露核验**：①红相 fixture bug（str→Path AttributeError）——与本票最终行为裁决无关，接受；②parse 级连带——已裁决（F-2）；③--summary-only 笔误——核实非代码问题；④超时间盒 1 次——记录在案，不影响证据链。
4. **Coordinator 两项既有核查确认**：FIX-200 编号复用（plan-tracker **L70**「仅编号碰撞」注记）与 FEAT-001（**L263** 0.66.0 已发布历史行）保持 FAIL 属 fail-closed 正确，消解需新决策——与本票无冲突，确认。
5. 工具调用数：读/检 14 次（任务时间盒 ≤12 略超 2 次——超支发生在主运行披露面证伪与活体锚点核验两个 MUST 裁决点上，Reviewer 判定为必要超支并在此披露）。

## 八、R1 复审比对基线（供 Coordinator 重派时引用）

- **必修**：F-1（两面披露块）。R1 必验：主运行面输出含 `Historical exempted (FIX-371/DEC-227 ✅-terminal, skipped): 26` 及逐行披露；四用例 + 既有套件零回归。
- **应完成（记录面）**：F-2 的 DEC-227 入账修订。
- **遗留候选**（不阻塞）：F-3/F-4/F-5/F-6/F-7/F-8。
- 本轮基线锚点：L12207 / L12210-12266 / L12486-12584 / L12601-12620 / L12706-12716 / L15502-15565 / L21451-21454 / L21489-21492；test L12362-12490。

---

*Reviewer：Code Reviewer Agent（software-project-governance）· 2026-09-20 · 只读审查，未修改产品代码*

---

# REVIEW-FIX-371-CODE-R1 — 复审节（Round 1，round+1）

> **Round 声明**：R1，前轮引用 = 本文件 R0 报告全文（基线锚点：R0 第八节）。复审范围 = R0 唯一阻塞项 F-1 的修复面 + R0 第八节基线逐条比对；未重开全维度（聚焦复审，增量面为纯打印插入）。
> **修复面核验方法**：工作树直读 verify_workflow.py L15496-15615（Check 16/17 主运行打印块全量）；Developer 实测输出与 pytest 54 passed 为采信披露（Bash 禁用），其静态可验证部分已独立证实。

## 一、R0 基线逐条比对

| R0 项 | 比对结果 | 证据 |
|-------|---------|------|
| F-1（P1，本轮必修）：主运行两面豁免披露 | **已修复** | Check 16 面 L15513-15518 / Check 17 面 L15547-15552：`ga_exempted = ga_result.get("historical_exempted", [])` / `ui_exempted = ...` → 计数行文案与子命令面逐字一致（`Historical exempted (FIX-371/DEC-227 ✅-terminal, skipped): N`）→ `[:8]` 有界逐行 → `... and N more` 溢出省略 |
| F-2（P2，记录面）：DEC-227 入账修订 | **已完成（采信披露）** | Coordinator 入账 DEC-228（三消费方 + Check 18 静默承认 + 主运行面披露义务）——记录面动作为 Coordinator 职责，Reviewer 采信入账声明 |
| F-3~F-8（P2×1/P3×5，遗留候选）：按 R0 裁定不动作 | **状态一致，未动作** | 修复面为纯增量打印；L15496-15615 直读确认 Check 18/18b 及周边零改动，无顺手越界修改 |

## 二、修复质量细目（逐项对照 R0 建议代码）

1. **同构性** ✅：两面结构/文案/有界策略与 R0 第一节建议块一致，且与子命令面（L21451-21454/L21489-21492）口径统一。
2. **防御式取值** ✅：两面均 `.get("historical_exempted", [])`，旧 result 形态安全。
3. **局部变量防遮蔽** ✅：`ga_exempted`/`ui_exempted` 前缀命名，作用域内无冲突（该函数原无 `exempted` 局部名）。
4. **插入位置** ✅：各在 `Impact analysis entries` 计数行（L15512/L15546）之后、entries 明细之前——面内显眼位，审计顺序自然（先看检了几个、再看豁免几个、后看 FAIL）。
5. **键一致性** ✅：`row['task_id']/row['evd_id']/row['status']` 与账本 dict 键（L12571-12575）一致，无 KeyError 面。
6. **零副作用** ✅：纯打印，不触碰 `ga_issues`/`ui_issues`/`all_issues` 判定计数，不改变任何 pass/fail 语义。
7. **对账闭合（采信披露的算术复核）** ✅：len=26 → 打印 26；切片 8 行；26>8 → `... and 18 more`（8+18=26）——代码路径必然产生该输出形态，与 Developer 实测一致。

## 三、新增发现

无（0 findings——插入块未引入正确性/安全/可维护性/性能/测试新问题；AI 专项不适用：纯打印增量无 mock/硬编码/幻觉 API/TODO/过度实现面）。

## 四、R1 结论

## **APPROVED**（P0 = 0；P1 已关闭；本轮新增阻塞 = 0；unresolved_blockers = 0）

- R0 唯一阻塞项 F-1 修复验证通过，无新引入问题；F-2 记录面闭环；F-3~F-8 维持 R0 遗留候选在册（非阻塞，处置已裁定）。
- 本结论为复审链通过终态：Check 30 复审链消费口径——APPROVED 结束链路；R0→R1 轮次连续（R0 NEEDS_CHANGE → 修复 → R1 APPROVED），熔断未触发（round 2 < 3）。
- 遗留候选移交提示（Coordinator 跟踪表义务）：F-3（豁免谓词与 FIX-292 语义双源——后续决策票）、F-4/F-5（死代码清理）、F-6（legacy 双形态 + 混合 fan-out 测试缺口）、F-7（docstring 措辞）、F-8（e2e 夹具再生）。

*R1 Reviewer：Code Reviewer Agent（software-project-governance）· 2026-09-20 · 只读复审，未修改产品代码（唯一写入 = 本报告 R1 节）*
