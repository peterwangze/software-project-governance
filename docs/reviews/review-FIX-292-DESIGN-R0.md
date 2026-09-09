# Design Review — FIX-292 DESIGN R0

- **Task**: FIX-292 — 0.79.0 范围核增（AUDIT-149 N1 / DEC-181）：18c~18i 执行包活跃判定谓词对齐
- **Round**: R0（首轮；判定面语义变更，DEC-181 强制双审的 Design 面）
- **Reviewer**: Design Reviewer Agent（只读审查；未修改任何产品/治理文件；唯一写入 = 本报告）
- **Date**: 2026-09-09
- **审查对象**: 未提交工作树相对 HEAD `c91d705` 的变更——`skills/software-project-governance/infra/verify_workflow.py`（+33/−7，单 hunk @ L12129-12162）+ `skills/software-project-governance/infra/tests/test_verify_workflow.py`（+148，两个新测试类 L17162-17307）
- **规格来源**: plan-tracker.md L277（FIX-292 行）；change-triage/FIX-292.json；execution-packets.json FIX-292 包；docs/release/audit-149-health-noise-0.79.0.md（§3 域 1 / §4 N1）；decision-log.md DEC-181

## 结论

**APPROVED_WITH_NOTES**

unresolved_blockers=0

零阻塞发现。委托方向正确、单一权威源成立、DEC-181 边界（零改写权威面 / M1 不修数据）经 diff 与 grep 双重验证合规。保留 3 条非阻塞备注（P2×1 + P3×2），其中 P2-1 要求 Coordinator 在完成证据中按实测口径回填（不得引用 ≤6 旧目标值）并确认残余噪声的承接任务已登记。

---

## 1. 事实基线（Reviewer 独立复跑，2026-09-09 本会话）

| # | 验证项 | 方法 | 实测结果 | 与任务书基线比对 |
|---|--------|------|---------|------------------|
| F-1 | 工作树构成 | `git status --porcelain` | 恰为声明两文件（M×2），无第三文件 | 一致 |
| F-2 | verify_workflow.py 改动面 | `git diff`（全文） | **单 hunk**（`_is_incomplete_task_status` 重写为委托 + docstring）；`_status_is_completed_cell`（L10389-10427）**零改动**；W-7 词表（L10313-10317）零改动 | 一致（「L10389 起，零改动」证实） |
| F-3 | 全量测试 | `python -B -m pytest skills/software-project-governance/infra/tests/test_verify_workflow.py -q` | **775 passed, 89 subtests passed**（131.79s） | 一致（764→775，Coordinator 复跑 775 佐证） |
| F-4 | 新用例数 | 读 test diff | 两个类共 **11 个 test 方法**（9 谓词级 + 2 端到端） | 一致（「绿 11 OK」） |
| F-5 | check-governance | `--summary-only` + 全量 | **88 issues**（任务书记 89；差 1 = 运行间治理记录自引漂移——execution-packet 字段回填改变 18 系字段检查结果，方向一致） | 基线 126→88（任务书 126→90→89），降幅 −38 量级一致 |
| F-6 | 18 系 FAIL 行 | 全量输出逐行 | **38 行** = FIX-222×6 / FIX-223×6 / FIX-224×6 / FIX-274×6 / FIX-281×6 / FIX-279×5 / FIX-292×3 | Developer 时点 30（时点差 = FIX-292 自身 ×3 + 包字段回填引起 FIX-279 计数漂移——两值均如实，自引漂移已解释） |
| F-7 | 活跃集闭合算术 | F-6 分组反推 | 改后活跃集 = {FIX-222,223,224,279(M1 保守), FIX-274(守卫), FIX-281(真实), FIX-292(自身)} = 7 任务；改前 12 + FIX-292 自身 − 6 掉出（FIX-253/254/255/266/REL-069 全部 M2 + FIX-291 M3）= 7 ✓ **精确闭合** | 与 AUDIT-149「多退少补都要解释」要求相符 |
| F-8 | 调用面完备性 | grep `_is_incomplete_task_status` 全仓 | 恰 7 个调用点（L8346/8366/8425/8880/9008/9030/12238）+ 定义 + 测试；无第八调用方 | 与 Developer 盘点一致，**无未盘点消费方** |
| F-9 | e2e vendored 副本 | 实读 + `git ls-files`/`check-ignore` + manifest grep | `project/e2e-test-project/skills/.../verify_workflow.py` L6908-6916 持旧谓词；该路径 **git-ignored（.gitignore L31）/ 未跟踪**；canonical manifest（core/manifest.json）无此文件（唯一 e2e 匹配 = verify-e2e.sh，另一文件）；该副本**不含 `_status_is_completed_cell` 与 W-7 词表**（整体先于 FIX-291 分叉） | Developer 披露「早已分叉、不在 canonical manifest 同步面」**证实** |
| F-10 | reopened / 裸「终止」live 实例 | grep plan-tracker + session-snapshot | plan-tracker `reopened`=0；session-snapshot reopened=0、非「已终止」=0；plan-tracker 含「终止」4 行的**状态格全部以 ✅ 开头**（间接闭合/完成形状→两代谓词同判完成，无翻转） | 「live 实例为零」**证实** |
| F-11 | FIX-274 状态格 | 实读 plan-tracker L251 | 末格含叙事「1 r1=FIX-273 **未完成**合法跳过」→ 旧谓词：命中 incomplete_markers → 活跃；新谓词：L10410 `未完成` 全文守卫 → 非完成 → 活跃。**两代谓词同判活跃，证实** | 与任务书焦点 5 描述一致 |
| F-12 | 红 8 FAILED | 解析验证（未改动工作树） | 旧谓词语义下逐一推演：M2×3（253/REL-069/266）+ M3×1（291）+ 裸「终止」×1 + reopened×1 + 结构断言×1 + 端到端 drop×1 = **8**；空/活跃/M1 锚定用例两代同判（红相位不失败，符合"锁定"意图） | 与「TDD 红 8 FAILED」算术一致 |

> 未验证项：改前基线 126/66 行未由本 Reviewer 时点复跑（需 revert 工作树，违反只读约束）——按 AUDIT-149 §2 表 B 的 117 构成 + 任务书披露采信，并以改后实测（F-5/F-6/F-7）的方向性闭合交叉印证。

## 2. 六个设计焦点逐一结论（验收标准 1）

### 焦点 1 — 单一权威源原则：✅ 通过

- **委托方向正确**：消费方（`_is_incomplete_task_status`）对齐权威（`_status_is_completed_cell`），而非反向。`return not _status_is_completed_cell(text)`（L12158）是最小委托形态：活跃 = 非可证明完成，语义即权威语义的补。AUDIT-149 诊断的根因（F1.3：同一状态格两套谓词得出相反结论，FIX-291 被 Check 34 判 completed 同时被 18c 判 active）由此在 canonical 面消灭——本次实测 FIX-291 已从 18 系活跃集掉出（F-7）。
- **权威面零改动**（F-2）：git diff 单 hunk，`_status_is_completed_cell`/W-7 词表/断言语义无一行触碰。
- **防回潮结构断言**（test_delegate_keeps_authoritative_predicate_untouched，L17239-17246）：inspect 源码断言不再含 `incomplete_markers`/`completed_markers` 且必须含 `_status_is_completed_cell`——把「语义二源」变成测试可见的回归面。grep 全仓确认 `incomplete_markers` 仅存于 e2e 冻结副本（F-9）。
- **一致性比对**：DEC-181 裁决 (2)「只消费不改写」逐字满足；FIX-291 权威谓词契约（W-7/BC-7 终态链 + 未完成全文守卫 + 保守默认）被原样继承（含其 R1/R2 收紧语义，L10296-10312 注释链完好）。

### 焦点 2 — 判定面语义影响面：✅ 通过（附 P3-1 备注）

- **7 个调用点逐一复核**（全部实读）：
  - L8346（plan `## 当前活跃事项` 上下文任务）、L8366（roadmap 活跃版本）、L8425（session-snapshot 表格）、L8880（`parse_resume_state` 活跃集）、L9008/9030（carry-over 表格与 bullet）、L12238（`_active_execution_packet_tasks` → 18c~18i 七个检查函数 L12812/12910/13076/13195/13655/13778/13801）。
  - **方向一致性**：7 处全部是 include-if-active 过滤语义——谓词收紧（更少判完成）⇒ 各处集合一致地更保守（更多保留）。不存在某调用点需要反向语义（exclude-if-active）的错配。
  - **L9030 特例核查**：该处把整条 bullet 行（非状态格）传入谓词。新谓词对整行同样按「非可证明完成→活跃」处理；与旧谓词的差异仅限保守翻转面（reopened/裸终止），与状态格路径同向。live session-snapshot 无翻转形状（F-10）。
- **未盘点消费方**：grep 全仓无第八调用点（F-8）；`checks/review_domain.py` 消费的是权威谓词本身（L98 显式导入），不经本谓词，不受影响。
- **e2e vendored 副本处置判定：恰当**。事实（F-9）：git-ignored、未跟踪、不在 canonical manifest、整体先于 FIX-291 分叉（连权威谓词都不存在）。在本任务同步它 = 引入一个未经 triage 的第三文件改动（违反 allowed_change_scope 两文件边界）且徒劳（该副本无权威谓词可委托，同步等于全量快照刷新，属 FEAT-010 锁定禁触域——FIX-271 史载「e2e 快照同步（FEAT-010 锁定禁触）」）。Developer 选择披露而不触碰，是边界正确的处置。残留动作见 P3-1。

### 焦点 3 — fail-closed 边界：✅ 通过

- 空/None/纯空白 → 活跃（L12155-12157，test L17206-17209 锁定）。与执行包 `assumption_record` 预声明（「空/缺失状态保持『未完成』判定（fail-closed）……本任务不放宽也不收紧」）逐字一致。
- **与 M1 行形状缺陷的职责切分清晰**：M1（尾空单元格使 `status=cells[-1]=""`）的修复面是行形状数据（写时看护 = FEAT-011 域）；本谓词对拿到的空串保守判活跃是**正确的消费侧行为**——在解析器给出空值时替它猜「完成」才是掩蔽型误判（AUDIT-149 所指 mask 方向）。端到端用例 test_m1_ragged_row（L17287-17305）明确锁定「MUST NOT 为消 M1 而改行形状或放宽空状态语义」，把切分写进测试。
- 消极面核查：显式空守卫虽与权威谓词对空串返回 False 的行为冗余，但承担 None 规范化与 fail-closed 契约的可读性，保留合理（P3-2 备注）。

### 焦点 4 — 保守化副作用：✅ 通过（fail-safe 方向，非回归）

- **`✅ 已发布 → 🔄 reopened`**：链尾状态是活跃——判活跃是**语义正确**而非副作用；旧谓词因「已发布」子串判完成属于掩蔽型误判（活跃任务从看护面消失，危险方向）。新行为 = W-7 docstring 明文契约（L10405-10407 "active-trailing cells keep the ACTIVE verdict"），test L17233-17236 锁定。
- **裸「终止」**：W-7 终态词表含「已终止」（完成体前缀）不含裸「终止」——裸词缺乏断言语形，保守判活跃。这是继承 FIX-291 双审通过的词表决策，方向 fail-safe（可疑状态留在看护面，而非静默消失）。test L17224 显式断言并以 docstring 披露「无 live 实例，fail-safe 方向」。
- **live 实例为零已由本 Reviewer 独立证实**（F-10）：plan-tracker reopened=0；含「终止」4 行状态格均 ✅ 开头（两代同判完成）；session-snapshot 0/0。零实例 + fail-safe 方向 + 测试锁定 ⇒ 接受成立。
- 「live 实例为零是否足以支撑接受」的判据：是——即便未来出现此类格，行为是把可疑行保留在活跃看护面（多报一行可解释的 FAIL），而非把真实活跃任务从看护面抹除；前者是噪声可治理，后者是信号丢失不可接受。方向性不对称使零实例论证充分。

### 焦点 5 — FIX-274 偏差：✅ 处置恰当（附 P2-1 承接要求）

- **事实**（F-11）：状态格叙事「1 r1=FIX-273 未完成合法跳过」同时命中旧谓词 incomplete_markers 与权威谓词 L10410-10411 全文守卫——两代同判活跃。AUDIT-149 将 FIX-274 归类 M2（谓词对齐可治）在此格上**过估**：该格的真实机制是叙事级「未完成」提及，权威守卫按设计拒绝完成。
- **处置判定**：DEC-181 裁决 (2) 禁止改写权威面——为消一行噪声去动一个刚经 FIX-291 双审、被 Check 30/30c/34 多域消费的守卫，风险收益完全倒置。数据面改措辞（如「未完成合法跳过」→不含「未完成」字面的表述）或独立任务承载，是唯一边界正确的路径。Developer 披露为「新事实」而非静默吞掉预期差，符合事实依据红线。
- **残余**：FIX-274 保留 6 行 18 系噪声（F-6）直至数据面处置——承接登记要求见 P2-1。

### 焦点 6 — DEC-181 边界遵守：✅ 通过（差值解释成立）

- **只消费不改写**：F-2 证实（单 hunk；权威面/W-7 词表零 diff）。
- **M1 不修数据**：工作树仅两文件，无 .governance/ 数据改动（F-1）。
- **−61 vs −36 差值算术验证**（以本 Reviewer 实测口径）：
  - 预期 −61 的前提 = AUDIT-149 N1「三选二组合」全落（①谓词对齐 + ②空尾单元格剔除 + ③词边界），活跃集收敛至 {FIX-281}。
  - 实现仅 ①（DEC-181 边界 + FEAT-011 分工的自觉选择）。差值构成（实测）：**M1×4 保留**（FIX-222×6 + FIX-223×6 + FIX-224×6 + FIX-279×5 = 23 行）+ **FIX-274 保留**（6 行）+ **FIX-292 自身入场**（3 行，自引：包字段 last_run/quality_budget 尚未回填 PASS——Coordinator 完成时职责）= 32 行未被移除；67 − 32 = 35 ≈ 实测 38 行（含入场后自引漂移）。**解释成立，算术闭合**。
  - 其中「18c scope 项归属」证实：残余 18c 行（allowed_change_scope too broad）与包字段行均挂在仍活跃任务上，随任务本身处置，不是谓词可治面。

## 3. 发现清单（验收标准 2）

### P2-1 — 完成证据口径与残余噪声承接登记（非阻塞，MUST 随完成动作闭合）

- **级别**: P2
- **位置**: execution-packets.json FIX-292 包 `done_definition[0]`（「18 系 FAIL 行 67→≤6 且仅真实活跃任务」）vs 实测（F-6/F-7）
- **事实**: done_definition 数值目标（≤6）在「仅①」实现下不可达（残余 38 行，含 5 个已完成任务 29 行：M1×4=23 + FIX-274=6）。包内 `assumption_record` 已预声明 M1 保守保留，但 triage 时点 done_definition 与 assumption_record **内在不一致**（前者隐含动作②，后者排除之）。另：M1 存量 4 行 + FIX-274 措辞的数据面承接任务**当前未在任何 tracker 行登记**（FEAT-011 是写时看护，AUDIT-149 明示「防新增，不治存量」）。
- **影响**: 若完成证据照抄 ≤6 目标值 = 与实测矛盾（事实依据红线违规）；若残余无登记承接，29 行噪声永久残留且无归属。
- **建议**: (a) Coordinator 回填完成证据时按实测口径记载（18 系 38 行 / 88 issues + F-7 分组构成 + −38 总降幅），明示对 done_definition 旧目标值的偏差与理由；(b) 为「M1 存量 4 行修复 + FIX-274 措辞调整」登记一个治理记录快速通道小任务（数据面，不触判定面），或并入 FEAT-011 范围并显式注记「含存量」。

### P3-1 — e2e 快照再生成时的谓词代际差登记

- **级别**: P3
- **位置**: project/e2e-test-project/skills/software-project-governance/infra/verify_workflow.py L6908-6916（git-ignored）
- **事实**: 副本停在 FIX-291 之前代际（无权威谓词），本任务后又新增一代语义差。处置（不触碰）正确（F-9）。
- **影响**: e2e fixture 若长期不刷新，其 `_is_incomplete_task_status` 行为将与 canonical 持续分叉；未来基于该副本的 e2e 断言可能锚定过时语义。
- **建议**: 在 FEAT-010（e2e 快照域）的再生成清单注记「快照刷新时须包含 FIX-292 谓词委托」；本任务不动作。

### P3-2 — 委托包装的冗余守卫与命名语义

- **级别**: P3
- **位置**: verify_workflow.py L12155-12158
- **事实**: 显式空守卫与权威谓词对空串的 False 返回行为冗余（权威 `_status_clean_cell("")→""`→各分支不中→False）；`_is_incomplete_task_status` 命名现义为「非可证明完成」，比字面「未完成」宽。
- **影响**: 无行为影响；可读性上靠 docstring 承载契约。
- **建议**: 保留现状（守卫承担 None 规范化 + fail-closed 契约显式化，删除反而损失文档价值）；若未来重构命名，优先 `_status_is_active_cell` 类表述——非本任务面。

## 4. 替代方案评估（验收标准 3）

| 方案 | 描述 | 评估 | 结论 |
|------|------|------|------|
| **A（已实现）委托权威谓词** | `not _status_is_completed_cell(text)` + 空/None 守卫 | 单一词表源、最小 diff、结构断言防回潮、权威语义修复自动传播 | **最优** |
| B 新增共享活跃谓词入口 | 在权威侧再抽 `_status_is_active_cell` 供双侧消费 | 增加一层 API 而不消灭任何决策点（活跃=非完成的补在此形态下本就一行）；空值规范化属消费方职责（缺失数据≠状态语义），上移反而混合关注点 | 不优于 A |
| C 显式枚举状态机 | 状态格结构化/枚举化（要求改数据格式） | 迁移级改造，远超降噪任务边界；dogfood 散文状态格是既定惯例，W-7/BC-7 已提供经双审的容错解析；重写引入新分叉风险 | 过度工程，否决 |
| D 仅修旧词表 | pending 加词边界、补链尾终态检测等到旧谓词 | 精确固化「语义二源」——AUDIT-149 诊断的根因本身；结构断言存在意义即防此路 | 否决（正确地未被采用） |
| E（AUDIT-149 N1 之②）空尾单元格剔除 | 解析层剔除空尾格后取 status | 可消 M1×4，但属解析器面改动（需独立审查面）且掩蔽数据缺陷信号（FEAT-011 存在理由）；本任务按 DEC-181 不并入是边界自觉而非遗漏——代价是 done_definition 数值目标不可达（P2-1） | 合理推迟，须 P2-1(b) 承接 |

**委托方案为最优的论证**：五个候选中只有 A 同时满足「消灭二源（根因）+ 零权威面改动（DEC-181）+ 最小 diff + 回归可测」四约束；B/C 增面不增益，D 复发根因，E 越界。

## 5. 蓝军挑战（≥3 条，标准格式）

| # | 攻击向量 | 影响评估 | 当前缓解 | 残余风险 | 建议增强 |
|---|---------|---------|---------|---------|---------|
| 1 | 权威谓词自身存在掩蔽缺陷（把真活跃判完成）→ 委托把缺陷扩散到 7 个调用面 | 若发生：活跃任务从 resume/carry-over/执行包看护面同时消失（放大器效应） | 权威面经 FIX-291 双审 + ~40 条 live 形状回归（test L16950-17159）；本变更未新增掩蔽语义（旧谓词的掩蔽面 M2 更大且已被消除）；未来权威修复自动传播（单源红利） | 低 | 无额外动作（传播性即单源设计的收益面） |
| 2 | host 项目（text-only 惯例）状态格使用裸「终止」→ 保守翻转为活跃，长死任务复活进活跃集 | 用户项目 resume 输出多出可解释行（噪声，非信号丢失） | fail-safe 方向 + dogfood live 零实例（F-10）+ 显式测试锁定与 docstring 披露 | 低 | host 侧文档化状态词表惯例（远期，非本任务面） |
| 3 | L9030 把整条 bullet 行当状态格判定——行内叙事「已完成」字样可能被判完成而漏 carry-over | 若 bullet 叙事含「已完成」而任务实际活跃：漏一行 carry-over | 旧谓词同受此影响（「已完成」子串同判完成）——非本变更引入；carry-over 漏项由 plan-tracker 活跃集（L8346 路径）兜底 | 低（既有行为，无回归） | 如需收紧，独立任务评估 bullet 行取词范围 |
| 4 | FEAT-011 落地前，M1 存量 4 行 + FIX-274 共 29 行 18 系噪声持续存在，维护者可能误读为修复无效 | 降噪预期（−61）与实测（−38）落差引发信任损耗 | 本报告 P2-1 显式拆解构成 + 实测口径；测试锁定 M1 保守行为（防「顺手放宽」） | 中（登记动作未完成前） | P2-1(b)：登记数据面小任务并注记于 FEAT-011 |

## 6. 非功能需求映射

| 需求 | 架构支撑 | 满足程度 | 遗留风险 |
|------|---------|---------|---------|
| performance（纯字符串解析，无明显开销） | 委托增一次函数调用；775 用例 131.79s | 满足（实测） | 无 |
| reliability（fail-closed） | 空/缺失/歧义→活跃；保守翻转均向看护面 | 满足（测试锁定） | 无 |
| security | 无外部输入面（包内 EXEMPT 口径一致） | EXEMPT（diff 审查证实） | 无 |
| accessibility | CLI 无 UI 面 | EXEMPT | 无 |
| ux（健康摘要降噪） | 126→88 issues；M2/M3 六任务从 FAIL 面消失 | 满足（实测；完整兑现待 P2-1(b) 承接 M1/274 存量） | 29 行残余噪声待数据面任务 |
| maintainability（单一权威源） | 委托 + 结构断言防回潮 | 满足 | e2e 冻结副本代际差（P3-1） |

## 7. 硬门槛自检

- [x] 候选方案 ≥2（§4 五案对比）
- [x] 设计一致性：DEC-181 裁决边界逐条比对（焦点 6）；AUDIT-149 根因诊断（F1.3 双谓词）对照消灭（焦点 1）；FIX-291 权威契约原样继承（焦点 1）；ADR-017（R1 留痕域）与本次改动面无交集——不适用，已核对
- [x] 影响面完备：grep 全量调用点独立复核（F-8，恰 7 处）+ e2e vendored 副本处置判定（焦点 2）
- [x] 蓝军挑战 ≥3（§5，4 条，标准格式）
- [x] 每条发现带级别+位置+事实+影响+建议（§3）
- [x] 事实依据红线：全部结论锚定 文件:行号 / 命令输出 / diff；未验证项显式标注（§1 注）

## 8. 结论重申

**APPROVED_WITH_NOTES** — unresolved_blockers=0

通过理由：委托设计在候选中唯一同时满足根因消灭与 DEC-181 边界；7 调用面方向一致且完备；fail-closed 与保守化方向经测试与 live 双重锁定；差值解释算术闭合。备注（P2-1 / P3-1 / P3-2）为完成证据口径与承接登记事项，属 Coordinator 完成动作，不构成设计返工。
