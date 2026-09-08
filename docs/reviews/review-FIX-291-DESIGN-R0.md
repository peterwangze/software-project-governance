# Design Review — FIX-291（判定面批：Check 30 历史格式迁移 / Check 30c 机器行分类 / W-7·BC-7 终态 marker 集）

- **审查轮次**: R0（首次设计审查）
- **Reviewer**: Design Reviewer Agent（判定语义面；代码正确性由并行 Code Reviewer 负责）
- **日期**: 2026-09-09
- **审查对象**: 工作树未提交 diff（`git diff`，5 文件 +686/-20：`infra/checks/review_domain.py`、`infra/verify_workflow.py`、3 个测试文件）
- **审查性质**: 判定面变更 MUST 双审（version-plan-0.79.0 §1 任务化结构 / §7 风险披露——G2/DEC-166 先例）——本报告为设计/判定语义面

---

## 0. 审查方法与事实依据（零编造声明）

| 事实源 | 核验方式 |
|---|---|
| 工作树 diff 全文 | `git diff` 通读（两产品文件 + 三测试文件逐 hunk） |
| 设计契约四源 | version-plan-0.79.0.md §2.2/§5 #4/#5/#6/§7/§8 精读；queue-triage-0.78x.md §2.1 #10（L71）+ §1.1 L37/L38/L45；plan-tracker L262（FIX-281 行①⑧申报原文）；G2 L-A/L-B/L-C 先例代码实读（review_domain.py L1613-1670 / L2105-2131 / L2293-2324，FIX-278 注释内嵌语义） |
| live 效果验证 | 只读命令实测（本仓 .governance）：新代码 Check 30 / Check 30c 全量输出；`git archive HEAD` 提取基线代码至 TEMP（仓外，零工作树触碰）同数据对照运行；谓词新旧对照 completed 集合 flip 扫描；29 个 historical 文件盘点复核 |
| 测试证据 | `pytest test_review_closure_legacy.py + test_review_machine_provenance.py`（51 passed）+ `test_verify_workflow.py -k StatusCellMixedTerminalMarker`（9 passed） |

**对照实验中的 harness 伪影披露**：首次基线对照报告 WARN 25(基线) vs 24(新)，经溯源为本审查者临时基线树只提取 `infra/` 导致 `ROOT` 共享名解析缺失 → 路由表 rt_keys=0 → SYSGAP-030 豁免判定失效的**环境伪影，非代码差异**。以完整插件树（182 文件）重跑后：**基线与新代码 Check 30 输出逐条一致**（violations 7 条同任务同规则、warnings 24 条零漂移）。

---

## 1. 设计契约逐项对照（checklist）

### 1.1 契约 1：version-plan-0.79.0 §5 #4/#5/#6 三子项裁决行 + §2.2/§7 边界锁定

| # | 裁决行要求（原文口径） | 实现事实 | 结论 |
|---|---|---|---|
| #4 W-7/BC-7 | 终态 marker 集扩展——状态格混合终态子类「⏳/🔄 + ✅ 已发布/已关闭」保守漏降级修正（判定面规则修改） | `_W7_TERMINAL_MARKERS`（9 词：✅/已发布/已关闭/已终止/已撤回/失效/不可信/取消/废弃）+ `_W7_ACTIVE_MARKERS`（5 词）+ trailing-position 比较（verify_workflow.py L10207-10257）；歧义/active 收尾维持 ACTIVE | ✅ 符合 |
| #5 FIX-281① | Check 30 pre-FIX-174 文件式 review 记录历史格式迁移路径（V2×9/V5×2 误判 11 项 FAIL → 历史形状分类 FAIL→WARN） | `source_format` 三分类（machine/historical/machine_format，review_domain.py L2553-2572）+ V2 全轮 historical 门（L2132-2155，含中缝——L-A 先例仅覆盖前导）+ V5 终轮 historical 门（L2325-2353，missing token / provably-zero prose 附着零值两形态） | ✅ 符合（含一处边界缺口，见 P1-1） |
| #6 FIX-281⑧ | Check 30c 合法机器行（REVIEW-/RECO-）白名单/溯源分类升级路径（新增即入 WARN——router 10→13 实证） | V7/V8 行判定锚定 ID 列（L2794-2803：ID 列非 REVIEW- 前缀的 EVD-/RECO- 行 → `rows_non_review` 分类计数不入 WARN）+ V8 R+1 记录存在豁免（L2722-2741 known_rounds 索引 + L2775-2786/L2842-2847 双通道豁免） | ✅ 符合（豁免条件偏宽，见 P2-2） |
| §2.2/§7 边界锁定 | 「ACTIVE/真实 nonzero 恒 FAIL」不可破；降级方向仅限历史形状/保守漏降级修正；现行机器格式违规不得放宽 | V2/V5 历史门均以 `task_id in completed` 为前置（L2143/L2335）；machine/machine_format rank=2 恒破坏 historical 分类（L1955-1960）；现行手写 REVIEW- 行 V7 WARN 保留（L2833-2841，live 残留 2 WARN 即此形状）；valid nonzero 走 provably-zero 的 status=="invalid" 前置拒绝（L1694） | ⚠ 基本符合——**provably-zero 对 prose 附着 P0/P1 nonzero 细目的盲区构成对锁定字面的可达违背（P1-1）**；evidence-row 通道不破坏 historical 分类（P2-1） |

### 1.2 契约 2：G2 L-A/L-B/L-C 先例语义一致性（0.78.0 FIX-278 引入）

| 先例 | 语义要点 | FIX-291 扩展的一致性 | 结论 |
|---|---|---|---|
| L-A（L2105-2131） | 前导缺轮 + 终态任务 → WARN；中缝缺口/ACTIVE 恒 FAIL；单裁决 per task（P3-3 documented choice） | A 子项为同型扩展至「全轮文件形状」（覆盖前导+中缝）；保持 completed-gate、单裁决 `continue` 语义（V2 历史门命中即 continue，不重复入 V1/V3/V5） | ✅ 同型一致 |
| L-B（L2293-2324） | 降级仅当「可证为空」（all values==0 且无不可解析 token）——fail-closed：无法证明为零的 legacy 值永不视为空 | **A 子项 V5 provably-zero 是对 L-B「可证为空」标准的收窄放宽**：invalid token 中前导数字为 0 者视为可证零。放宽方向符合契约（① FAIL→WARN 历史迁移），但「可证」的实现只证了前导数字、未证附着细目无 blocker（见 P1-1——本仓 live 语料存在 `unresolved_blockers=0，P0=0/P1×1/P2×3/P3×5，共`〔FIX-254 行〕自相矛盾形状） | ⚠ 方向一致、证明标准未达标（P1-1） |
| L-C（FIX-278 判定面边界锁定惯例） | ACTIVE/真实 nonzero 恒 FAIL | 见 §1.1 边界行 + §2.4 组合路径推演 | ⚠ 同上 |

### 1.3 契约 3：queue-triage-0.78x §2.1 #10（W-7/BC-7 原始评估）

原文（L71）：「状态格混合终态子类『⏳/🔄 + ✅ 已发布/已关闭』无『完成』→ 判 ACTIVE → 保守漏降级；本仓静态实例 REL-068/069……(a) 保守方向（fail-safe 一侧——不掩盖当前工作），非误降级；(b) marker 集扩展 = 判定面规则修改 + 测试 + DEC」。

- trailing-terminal 实现的判定方向 = 「真实终态对齐」：状态格是状态历史，收尾态即当前真态——符合原始意图（ REL-069 形态「🔄 进行中 (…) → ✅ 已发布 (…)」实测 flip 为 completed，本仓唯一 flip，见 §2.5）。
- 「非误降级」承诺：歧义/active 收尾默认 ACTIVE 已实现并有测试（`test_active_trailing_after_terminal_stays_active` / `test_terminal_in_version_context_with_trailing_active_stays_active`）；**但 active-先-终态词-后 且无 active 收尾的版本上下文格（如「🔄 进行中 (…)——0.78.1 已发布」）会误判 completed**——该形态未被测试覆盖，是「非误降级」承诺的残余例外（P2-3）。
- 「+ 测试 + DEC」：测试 ✓（9 用例）；DEC 由 M-3 双审 + 发布流程承载（Coordinator 侧，非本 diff 义务）。✅

### 1.4 契约 4：FIX-281①⑧ 缺陷申报原文（plan-tracker L262）

- ①「Check 30 V2×9/V5×2 对 pre-FIX-174 文件式 review 记录（.governance/review-*.md 无 R0 起始机器行）判 11 项 FAIL——FIX-174 状态机无历史格式迁移路径，G2 L-A/L-B/L-C 未覆盖该形状（与 W-7/BC-7 部分重叠但 V2 形状不同）」→ 实现覆盖 V2（全轮形状门）与 V5（missing/prose-zero）两形态，与申报形状定义（无机器 marker 的文件式记录）一致 ✅。本仓 live 无该形状实例（本仓 29 个 historical 文件均无缺轮/V5 违规叠加——见 §2.5 live 零新增降级），价值面向 router 宿主（EV-066 实证域）——与申报「router 实证」一致 ✅。
- ⑧「Check 30c 合法机器行（REVIEW-/RECO-）新增即入 WARN 无白名单/分类升级路径（router 10→13 实证）」→ ID 列锚定 + rows_non_review 分类计数 = 白名单路径；live 35→2 实测消除的 33 条中含 EVD-/RECO- 交叉引用误报（rows_non_review=164）✅ 机制对症。

---

## 2. 设计面焦点审查（焦点 1-6）

### 2.1 焦点 1：A 分类语义与 G2 先例一致性；rank 合并的混合链行为

**结论：语义同型一致；rank 合并对文件贡献正确，对 evidence-row 贡献存在未覆盖通道（P2-1）。**

- 分类语义：`形状（source_format 三分类）+ 终态判定（completed）` 双前置与 L-A/L-B 的「形状+终态」判定模式同构；降级方向（FAIL→WARN）与放宽不收紧契约一致。
- rank 合并（L1955-1960）：machine/machine_format(2) > historical(1) > unknown(0)，高 rank 覆盖低 rank、低 rank 永不覆盖高 rank——**文件通道**的混合链不会误整体降级：任一轮存在现行格式文件贡献即破坏全轮 historical 分类（测试 `test_machine_file_gap_stays_fail` 红线锚定）。
- **P2-1（缺口）**：evidence-log 行通道的 entry 永远 `source_format="unknown"`（L2528-2534 无分类赋值），rank 0 永不破坏 historical 分类。即：某轮同时存在 historical 文件与**现行机器 evidence 行**（行含 `review-record CLI 机器写入` marker、日期 ≥ 生效日）时，该轮仍判 historical——docstring 声明「a current-format contribution to a round always breaks the provably-historical classification」（L1908-1913）**仅对文件贡献成立，对行贡献不成立**。实际概率低（review-record CLI 行+文件成对写入，文件覆写即 machine 分类；行孤立存在需文件写入失败或手工行），但契约声明与实现不符 + 是混合链误降级的理论通道。建议：行通道按 `REVIEW_MACHINE_ROW_MARKER in row` 赋 source_format="machine"；至少须修正 docstring 声明。
- V2 门 `all(rounds[r].source_format == "historical" for r in rounds)` 对「仅行来源」轮（unknown）不满足 → 不降级 → 保守方向正确（本仓 6 条残留 V5 FAIL 即因此正确保持 FAIL，见 §2.5）。

### 2.2 焦点 2：B 豁免逻辑漏洞面；白名单与「手写行 WARN」边界相容性

**结论：ID 列锚定机制正确且对症；V8 豁免为存在性判定、无日期/有效性校验（P2-2）；边界相容性合格。**

- ID 列锚定（L2798-2803）：以 `_parts[1]`（ID 列）而非全行 finditer 判定 review 行——EVD-/RECO-/TRIAGE- 行 description 提及 REVIEW id → `rows_non_review` 计数、不入 WARN。机制与缺陷申报⑧的「新增即入 WARN」增长机制精确对症（live 实测消除 33 条误报）。测试覆盖 EVD-/RECO- 机器行、markdown 修饰 ID 列锚定、边界（手写 REVIEW- 行仍 WARN）。
- **P2-2（豁免偏宽）**：`known_rounds` 收录条件为「文件名匹配 OR ID 列含 REVIEW- id」的**存在性**——不校验 R+1 记录的日期（可早于 NEEDS_CHANGE 记录——同 task 历史轮次命名冲突时可错误豁免）、不校验有效性（conclusion UNKNOWN/不可解析的 R+1 文件同样豁免）。设计问题：「复审必达义务溯源为已履行」的证据标准应是「存在一条**有效的** R+1 复审记录」，而非「存在任何同名记录」。缓解：Check 30 状态机独立复审链路终态（R+1 无效时 V1 仍会捕获），系统级风险有界；但 30c 自身信号被削弱。建议：豁免增加日期序校验（R+1 记录日期 ≥ NEEDS_CHANGE 记录日期，两通道日期均可得）。
- REL-070 同号覆盖形态：release R0 NEEDS_CHANGE + design R0 AWN 覆盖同号文件而 R1/R2 存在——豁免语义正确（复审确实发生了）；测试 `test_needs_change_row_with_next_round_record_no_v8` / `test_needs_change_file_with_next_round_record_no_v8` 锚定。✅
- 边界相容性：现行手写 REVIEW- 行（ID 列 REVIEW-、dated ≥ 2026-08-22、无 marker）仍 V7 WARN（`test_handwritten_review_row_still_warns_v7` + live 残留 2 WARN 实证）——「现行格式违规不得放宽」边界保持。✅

### 2.3 焦点 3：C 保守方向；trailing-terminal 与 W-7/BC-7 原始意图

**结论：主体符合「真实终态对齐」意图；存在一个未覆盖的误降级残余形态（P2-3）。**

- 「⏳ 待执行 → ✅ 已发布」混合格判定 completed——状态历史收尾态即真态，正是 queue-triage #10 登记的 REL-069 漏降级形态；live 唯一 flip 即 REL-069（§2.5）✅。
- 保守边界实现：歧义（无 marker）/active 收尾（终态词后被 active 词）→ ACTIVE；`未完成/待完成` 优先级最高（FIX-274 语料回归测试锁定）；`推进中` 入 trailing active 集使「0.78.0 已发布，0.79.0 推进中」保持 ACTIVE。✅
- **P2-3（残余误降级形态）**：active 词先出现、终态词后出现且无 active 收尾的**版本上下文格**（如「🔄 进行中 (2026-09-08)——0.78.1 已发布」）→ terminal_pos > active_pos → 误判 completed。已测版本上下文用例仅覆盖 active 收尾排序（「已发布，推进中」）；active-先-终态-后的排序未防。误判后果：①V1 方向趋严（completed + 非终态结论 → 误 FAIL——fail-safe 侧）；②A 子项 V2/V5 门需叠加全轮 historical 链才可错误降级（现行工作链通常含现行格式记录 → rank 破坏 → 不触发）——复合概率低但非零。建议：登记为已知残余 + 收紧候选（仅承认转换上下文〔→ 之后〕的终态词，或对版本号前缀的「已发布」作上下文排除）。

### 2.4 焦点 4：边界锁定全局复核（三子项组合路径推演——非单点）

**结论：除 P1-1 外无组合放宽路径；P1-1 为「真实 nonzero 恒 FAIL」锁定字面的可达违背，MUST 修复。**

逐组合路径推演（A=历史格式迁移，B=30c 分类，C=W-7 谓词）：

| 组合路径 | 推演 | 判定 |
|---|---|---|
| A 单独 × ACTIVE 任务 | V2/V5 历史门均前置 `task_id in completed`——ACTIVE 恒不降级（代码 L2143/L2335 + 测试 `test_historical_file_gap_on_active_task_stays_fail`） | ✅ 锁定保持 |
| A × 现行格式记录 | machine/machine_format 文件贡献 rank 破坏 historical 分类（测试 `test_machine_file_gap_stays_fail`）；现行手写 REVIEW- 行 V7 WARN 保留 | ✅（文件通道）；⚠ 行通道见 P2-1 |
| A × 真实 nonzero（valid） | `_blocker_evidence_provably_zero` 前置 `status=="invalid"`——valid 2 直落 violation（测试 `test_historical_file_v5_nonzero_stays_fail`） | ✅ 锁定保持 |
| A × 真实 nonzero（prose 附着） | **P1-1**：`_PROVABLY_ZERO_TOKEN_RE = ^unresolved_blockers=0(?!\d)` 只证前导数字为 0，**不证附着细目无 blocker**。`unresolved_blockers=0，P0=1` / `=0，P1×1`（本仓 live 语料实证存在此形状：FIX-254 行「unresolved_blockers=0，P0=0/P1×1/P2×3/P3×5，共」）→ 匹配 provably-zero → 若该记录为 historical 文件形状 + 任务 completed → 降级 WARN。自相矛盾记录（结构 token 报 0、细目报 P0/P1 nonzero）按 L-B「可证为空」标准**不可证为空**（principle: 无法证明为零的值必须保持 FAIL）——实现未达其自身命名（`provably_zero`）的证明标准。修复方向：regex 增加负向前瞻，附着细目含 nonzero P0/P1 计数（`P[01]\s*[=×x]\s*[1-9]`）即拒绝降级；P2/P3 nonzero 不受影响（非阻塞级，现有测试 fixture 依赖之）。live 语料 FIX-254 形状可直接作红 fixture | ❌ **锁定字面可达违背——P1** |
| A × 歧义值 | 「10，」「02，」不匹配 provably-zero（`(?!\d)` 前瞻）→ 保持 FAIL（fail-closed）✅；但无显式测试锚定（P3-1 测试缺口） | ✅ 行为正确 / ⚠ 缺测试 |
| C 单独（W-7 误判 completed） | 误判方向后果：V1 趋严（fail-safe）；A 门需全轮 historical 链叠加（复合低概率，见 P2-3） | ⚠ 见 P2-3 |
| B × A / B × C | 30c 不消费 completed / source_format——无交叉放宽路径 | ✅ 无交互 |
| A(V2) × A(V5) 同链 | V2 门 `continue` 单裁决语义保持（L-A P3-3 documented choice 延续）——缺轮+终轮缺陷链只出 V2 WARN | ✅ 与先例一致 |
| 三子项叠加（A+B+C 全开） | B 无 completed/source_format 消费；C 的唯一新增 completed（live=REL-069）链为 machine/valid-0（V5 正常通过，无门交互）——live 实测 violations/warnings 零漂移 | ✅ 实证无叠加放宽 |

### 2.5 焦点 5：live 效果合理性（实测复核——只读命令，2026-09-09）

| 声明 | 实测 | 判定 |
|---|---|---|
| Check 30 不变 | 基线（HEAD 代码 @ git archive 完整插件树，同 live 数据）vs 新代码：violations 7 条（V1 FIX-213 + V5 FIX-253/254/255/256/258/REL-068）逐条一致；warnings 24 条零漂移（V1×20 / V2×2 / V5×1 / V3×1） | ✅ **实证不变**（首测 25-vs-24 差异经溯源为本审查者基线 harness 伪影——临时树缺路由文件致 SYSGAP-030 豁免判定失效；完整树重跑后一致，已在 §0 披露） |
| 30c 35→2 | 基线 35 WARN → 新代码 2 WARN（V7 FIX-256 + V7 FIX-258——现行格式手写 REVIEW- 行）；rows_judged 95→70（-25 条 EVD-/RECO- 交叉引用误报出判定域）、rows_non_review=164 新分类计数、V8 REL-070×2 豁免 | ✅ 实证相符 |
| 149→149 | 本审查可测面：`parse_task_dependencies` 全行面上 completed 集合 flip 恰好 1 例（REL-069——W-7 目标实例本身，trailing「✅ 已发布」）；「149」计数面未在可测面复现（所测总行面 184） | ⚠ 实质等价（唯一 flip = 目标实例、无误伤）但计数口径未注明（P3-2——Developer 证据应注明计数面） |
| 余 2 WARN 处置 | 现行格式手写 REVIEW- 行保留 WARN = 契约边界（「现行格式违规不得放宽」）的正确执行，非遗漏 | ✅ 正确边界 |
| A 子项 live 零新增降级 | 本仓 6 条残留 V5 FAIL（FIX-253~258/REL-068）全部为 evidence-row-only 来源（src=unknown）→ 按边界不降级（保守方向正确）；本仓 29 个 historical 文件无一叠加缺轮/V5 违规 → V2/V5 历史门 live 零触发。A 的价值面向 router 宿主形状（EV-066 域）——与申报一致 | ✅ 合理（不是本仓缺陷——是范围使然） |
| 测试 | 51 + 9 passed（含红→绿边界锚定：ACTIVE 恒 FAIL / nonzero 恒 FAIL / machine 格式恒 FAIL / 手写行恒 WARN） | ✅ |

### 2.6 焦点 6：与 0.79.0 版本定位一致性（DEC-177 ①）

- 三子项均为判定规则/分类语义扩展（新增 source_format 维度、provably-zero 形状判定、终态 marker 词表与位置规则、行分类白名单、R+1 溯源豁免）——命中 version-plan §2.2 L12 行「判定规则扩展（G2 L-A/L-B/L-C 先例 DEC-169 ③ 同型）」与 §5 #4/#5/#6 三行「L12 判定规则扩展/判定分类扩展」定位 ✅。
- 非缺陷修复面（0.78.1 已承载缺陷面；①⑧显式出槽 0.79.0——plan-tracker L470）✅；与「放宽/fail-safe 方向、预期零 BREAKING」（§2.2）一致（除 P1-1 需收窄 provably-zero 外无收紧面）✅。
- M-3 双审义务：本报告（Design Reviewer）+ 并行 Release Reviewer——由 Coordinator 调度承载 ✅。

---

## 3. Findings 分级汇总

| ID | 级别 | 发现 | 依据（文件:行 / 契约条款） | 建议 |
|---|---|---|---|---|
| **P1-1** | **P1（阻塞）** | `_PROVABLY_ZERO_TOKEN_RE` 只证前导数字为 0、不证附着细目无 blocker：`unresolved_blockers=0，P0=1` / `=0，P1×1` 形状（本仓 live 语料实证：evidence 行 FIX-254「…P0=0/P1×1/P2×3/P3×5，共」）匹配 provably-zero → historical 文件形状 + completed 任务时降级 WARN——违背 L-B「可证为空」证明标准与 §2.2/§7「真实 nonzero 恒 FAIL 不可破」锁定的字面 | review_domain.py L1673-1704（regex + 判定函数）；L-B 先例 L2298-2305（「provably empty……fail-closed」）；version-plan-0.79.0 §2.2/§7；live 语料 FIX-254 行 | regex 增加负向前瞻：附着细目含 nonzero P0/P1 计数（`P[01][=×x]\s*[1-9]` 类模式）即不匹配；P2/P3 nonzero 保持可降级；以 FIX-254 形状作红 fixture 补边界测试 |
| P2-1 | P2 | evidence-row 通道 entry 恒 `source_format="unknown"`（rank 0）——现行机器 evidence 行并入 historical 文件轮时不破坏 historical 分类；docstring「current-format contribution always breaks the classification」声明仅对文件贡献成立 | review_domain.py L2528-2534（行通道无分类赋值）vs L1908-1913（docstring 声明）vs L1955-1960（rank） | 行通道按 `REVIEW_MACHINE_ROW_MARKER` 赋 source_format="machine"；至少修正 docstring 声明范围 |
| P2-2 | P2 | V8 R+1 豁免为存在性判定（文件名/ID 列命中即可），无日期序与有效性校验——早于 NEEDS_CHANGE 记录的同号历史轮或 conclusion=UNKNOWN 的无效 R+1 文件均可豁免现行复审义务 | review_domain.py L2722-2741（known_rounds 构建）+ L2775-2786 / L2842-2847（豁免点） | 豁免增加 R+1 记录日期 ≥ NEEDS_CHANGE 记录日期校验（两通道日期可得）；缓解背景（Check 30 状态机独立复审终态）已如实记入 |
| P2-3 | P2 | W-7 trailing-terminal 对「active 先、终态词后、无 active 收尾」的版本上下文格（如「🔄 进行中 (…)——0.78.1 已发布」）误判 completed——queue-triage #10「非误降级」承诺的残余例外；已测用例仅覆盖 active 收尾排序 | verify_workflow.py L10252-10257；queue-triage-0.78x L71（(a) 保守方向承诺） | 登记已知残余；收紧候选：仅承认转换上下文（→ 之后）的终态词或版本号前缀上下文排除 |
| P3-1 | P3 | 歧义 prose 值（「10，」「02，」）fail-closed 行为正确但无显式测试锚定 | review_domain.py L1681（`(?!\d)` 前瞻）；测试文件缺该边界用例 | 补 2 条歧义值边界测试 |
| P3-2 | P3 | live 效果声明「149→149」计数面未注明（可测面上 completed flip=1/REL-069、总行面 184） | 任务上下文 live 声明 vs 本审查实测（§2.5） | Developer 证据补记计数面定义（哪张表/哪个解析器的 completed 计数） |

**蓝军挑战（≥3 条独立挑战，角色硬门槛）**：
- BC-1「如果有人手写一条现行格式的 REVIEW- 行并复制机器 marker 文本会怎样？」——marker 可复制是已知既有限制（L2600-2603 注释 + FIX-260 decision-log escalation 路径登记），非本 diff 引入；30c 白名单锚定 ID 列后不放大该面（marker 伪造仍需 ID 列为 REVIEW-，届时本就是被判定域）。结论：无新增暴露。
- BC-2「如果 W-7 误判 completed 叠加 A 门会怎样？」——见 P2-3 组合推演：需全轮 historical 链叠加，复合低概率；V1 方向趋严（fail-safe）。结论：有界，登记残余。
- BC-3「如果 R+1 记录存在但本身无效（UNKNOWN/历史同号）会怎样？」——见 P2-2：30c 豁免、Check 30 V1 兜底。结论：系统级有界、单检查面削弱，建议日期序收紧。
- BC-4「三子项同时作用于同一任务会怎样？」——见 §2.4 组合表：live 实测零漂移 + 路径推演无叠加放宽（除 P1-1 单点）。结论：组合面安全。

**硬门槛裁决（角色定义 §硬门槛）**：本任务为判定语义面审查（非选型/ADR 类）——候选方案数/ADR 字段/循环依赖/Bar Raiser 门槛不适用；蓝军挑战 ≥3 ✓（4 条）；事实依据红线 ✓（每 finding 均有文件:行或命令输出支撑；无法验证项〔「149」计数面〕已标待注明而非假设）。

---

## 4. 终态结论

**NEEDS_CHANGE**

- **理由**：P1-1 构成对设计契约 MUST 级边界锁定（「ACTIVE/真实 nonzero 恒 FAIL 不可破」——version-plan-0.79.0 §2.2/§7，G2 DEC-166 惯例）的可达违背路径，且违背 L-B 先例确立的「可证为空」证明标准。修复面窄（一条 regex 收紧 + 1~2 条边界测试），修复后不触及其余设计。
- **unresolved_blockers = 1**（P1-1）。
- P2-1/P2-2/P2-3 为非阻塞备注（建议随修复一并处理 P2-1 的 docstring 失实声明，成本极低）；P3×2 观察项。
- 复审预期（R1）：验证 P1-1 regex 收紧 + 红fixture（FIX-254 形状）+ 其余 finding 处置状态逐条比对。

---

*本报告为 FIX-291 判定语义面设计审查（R0）。审查过程零产品文件写入（唯一写入 = 本报告）；基线对照实验在 TEMP 目录进行（仓外）。*
