# Code Review Report — FIX-374（Round 0，串行单席）

- **审查对象**：工作树未提交修改（本票无 diff 存档文件；以现行代码 + review-FIX-372-CODE-R0 F-1 原文对照复核）
- **涉及文件**：`skills/software-project-governance/infra/verify_workflow.py`（`_EVIDENCE_DATE_SHAPE_RE` 定义 L12408-12416 + `check_protocol_compliance` evidence format check 9-cell else 分支消歧改造 L10077-10104）+ `infra/tests/test_verify_workflow.py`（新增 `Fix374NineCellDisambiguationTests` L12223-12287）
- **审查席**：Code Reviewer（只读；本报告为唯一写产物）
- **前轮引用**：REVIEW-FIX-372-CODE-R0 **F-1（P2）**——「9-cell 豁免按格数嗅探，缺 Date/Notes 格的截断 LIVE 行（恰 9 格）落入 else 分支用错位偏移检查全通过，真实缺失 Date 漏报」；建议方案一「内容启发式消歧（9-cell 分支校验 cells[6] 日期形态）」
- **结论**：**APPROVED_WITH_NOTES**（unresolved_blockers=0；P0=0，P1=0，P2=0，P3=5）
- **工具时间盒**：10 次调用。Bash 禁用——测试/验证命令未独立复跑，涉及处如实标注（§10）

---

## 0. 范围核实

修改面与任务上下文一致：verify_workflow.py 两处（正则定义 + 9-cell else 分支）+ 测试一个新类（3 用例）。`REQUIRED_SNIPPETS`（L749+）为文档片段钉（README/protocol docs），不涉本票修改面 ✓。既有 `EvidenceFormatColumnLayoutTests` 3 用例与 `Fix373SplitterCodeSpanQuoteTests` 6 用例静态推演零回归（§5）。TRIAGE-FIX-374 机录 2026-09-21（evidence-log L2460）✓。无范围外修改。

## 1. 判据边界推演专节（验收标准 2：两类布局列语义核对）

**列布局语义**（代码注释 L10037-10042 + 真实行 EVD-874（evidence-log L30）逐格核对印证）：

| 布局 | cells[0] | [1] | [2] | [3] | [4] | [5] | [6] | [7] | [8] | [9] |
|---|---|---|---|---|---|---|---|---|---|---|
| LIVE 10-cell | EVD | TaskID | Type | Description | fact basis | Location | **EntryMethod(录入者)** | **Date** | Gate | Notes |
| 历史 9-cell | EVD | TaskID | Type | Description | fact basis | **Author** | **Date** | Gate | Notes | — |

任务提示的疑问「10 格 LIVE 行 cells[6] 是什么位？cells[6]=Actor？」——**核实：LIVE cells[6] = EntryMethod（录入者，即 Actor 位），Date 在 cells[7]**。EVD-874 真实行尾部结构 `…| 证据清单 | Governance Developer + Code Reviewer… | 2026-08-02 | G11 | ✅ 完成 |` 与 LIVE 布局逐格吻合（c5=位置/c6=录入者/c7=Date/c8=Gate/c9=Notes）。任务提示与代码注释对 LIVE 布局的两种表述（Artifacts/Actor/Conclusion vs Location/EntryMethod/Notes）为同位异名，一致。

**判据在两类布局下的推理自洽性**：
- 判据仅作用于 len==9 分支（L10089）。10 格 LIVE 行走 len>=10 分支（L10069-10076），cells[6] 语义与本判据无关——任务提示对 LIVE cells[6] 的疑虑不构成判据风险。
- 历史 9-cell：cells[6]=Date。日期形态匹配 → 判历史行 → 校验 Author（cells[5]）→ **自洽**。
- 截断 LIVE（缺 Date 格，10→9）：cells = [EVD,Task,Type,Desc,fact,Loc,Entry,Gate,Notes]，cells[6]=EntryMethod 录入者文本（如「Coordinator 机写」）→ 非日期形态 → 判截断 LIVE → 校验 Location/EntryMethod（真实偏移）+ 报 missing Date → **自洽**。

**日期正则边界**（`^\d{4}[-/]\d{1,2}[-/]\d{1,2}$`，L12416）：
- 单位数月日/非 0 填充（2026-9-2、2026/09/7）✓ 匹配。
- 非法日历值（2026-13-32）**误纳**——但消歧用途无害：检查目标是「Date 格非空且形似日期」而非日历有效性，非法日期仍证明 Date 格在场；且 LIVE EntryMethod 文本形如 `1234-56-78` 的现实概率≈0。
- 非分隔符形态（20260920、2026年9月2日、段缺「2026-9」）**不匹配** → 假想历史行会被误报为截断 LIVE（fail-noisy 方向）——真实数据 11/11 均分隔符形态（§2），现状零误报；P3-F3 留观察。

**真实数据核验（以读代跑，ripgrep 字面管道计数）**：
- 9-cell 行（恰 8 内部管道符）实测 **11 行**（L13/17/21/23/1227/1231/1234/1237/1241/1244/1254，EVD-879/878/877/876/886/887/888/889/890/891/893）；「cells[6] 为日期形态」的组合 pattern 与之**完全重合（11/11）**——现存全部 9-cell 行判据零误报，独立证实 Developer 方向主张。
- Developer 声称 12/12：计数差 1 属口径差——字面 grep 无法模拟 `_split_governance_table_row` 的 code-span/quote 保护（含 code-span 管道的行字面格数偏大），第 12 行若存在则不可由字面统计裁决。与「check-governance evidence_format=0」声称交叉印证（若第 12 行 cells[6] 非日期形态，机器检查必报）。**方向成立，数字标注 Developer-claimed**（P3-F1）。
- 10-cell LIVE 且 cells[7] 日期形态：字面 14 行（EVD-874/311/232/678/904/1011/1029/1030/1031/1032/1065/1075/1110/1116）。Developer 声称 424 行——同口径差（结构化事实 JSON 时代行内 code-span 保护管道使字面格数 >10），不构成矛盾，如实披露。
- 11-cell 行未单独计数（字面统计受 code-span 污染，裁决意义有限）；该面不受本票修改影响（len>=10 分支未动）。

## 2. 豁免面零弱化独立判定（验收标准 3）

- **len<9 分支（L10055-10059）/ len>=10 分支（L10069-10076）：与 review-FIX-372-CODE-R0 §1② 记载的 FIX-372 后代码逐字对照，零改动** ✓。
- **合法历史行路径逐字对照**：修改前 = `Author(cells[5])` 非空 + `Date(cells[6])` 非空检查；修改后 = 日期形态判定（正则匹配 ⇒ cells[6] 非空，Date 非空检查成为冗余而移除）+ `Author(cells[5])` 非空。对 cells[6] 日期形态的行两版行为**等价**（Date 检查在非空前提下恒通过）✓。
- **无报错集合形式化**：S_old = {9-cell 行 : cells[5]≠"" ∧ cells[6]≠""}；S_new = {9-cell 行 : cells[6] 日期形态 ∧ cells[5]≠""}。日期形态 ⇒ 非空，故 **S_new ⊂ S_old——豁免面严格缩小（检测面严格扩大），零弱化** ✓。retention 测试 `test_nine_cell_historical_row_with_trailing_pipe_retained`（EVD-907）钉住该面。
- **行为变化面共 3 处，全部 fail-noisy 方向**：①截断 LIVE 缺 Date → 由静默漏报变报 missing Date（F-1 修复目标本体）✓；②cells[6] 为空的历史行 → 报错字段名从 Author/Date 错位为 Location/EntryMethod, Date（报错不减，= Developer 边缘 2）✓；③**缺 Notes 格的截断 LIVE 行 → 由静默（F-1 时代）变误报 missing Date**（cells[6]=EntryMethod 非日期 → 截断分支；该行 Date 实际在场）——F-1 建议方案的必然副作用（日期形态判据无法区分缺 Date 与缺 Notes），假阳性属可接受 fail-noisy，纳入 P3-F2 披露。

## 3. 测试断言强度（验收标准 4）

| 用例 | 断言 | 内容锚定 | 修改前红面静态推演 |
|---|---|---|---|
| test_truncated_live_row_missing_date_flagged（EVD-906） | len==1 + "Date" in + "Author" not in | ✓ 非仅计数 | 旧 else 分支 Author/Date 双非空 → issues=[] → `0 != 1` 红——**真实捕获漏报** ✓（与 Developer 声称红态吻合） |
| test_truncated_live_row_missing_location_and_date_both_flagged（EVD-908） | len==1 + "Location" in + "Date" in | ✓ | 旧历史分支报 Author → `'Location' not found in 'EVD-908: missing fields — Author'`——**真实捕获错位** ✓（与 Developer 声称红态吻合） |
| test_nine_cell_historical_row_with_trailing_pipe_retained（EVD-907） | issues==[] | retention（旧代码亦绿，非判别性，设计正确） | 豁免面回归钉 ✓ |

- 红相 2F/1P 组成与 Developer 声称一致（静态推演）；指定套件 12 = 3（Fix374）+ 3（EvidenceFormatColumnLayout）+ 6（Fix373Splitter）数目吻合（运行时未复跑，Developer-claimed）。
- 既有 EvidenceFormatColumnLayoutTests 3 用例静态推演保持绿（EVD-874 形状 fixture cells[6]=2026-05-02 日期形态 → 历史分支 → Author 非空 → issues=[]）✓。
- 覆盖缺口（与登记一致）：缺 fact/Location 截断形态无测试（边缘 1 登记不修的一致面）；非分隔符日期形态无测试（假想形态）。P3-F2/F3。

## 4. 五维度结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | ✅ 通过 | §1 判据两类布局推理自洽；§2 豁免面零弱化；3 处行为变化均 fail-noisy 且 2 处已登记披露；正则边界已推演（非法日历值误纳无害） |
| 安全性 | ✅ 通过 | 正则无 ReDoS 形态（量词有界、无嵌套回溯组）；纯本地 Markdown 解析无注入面；无敏感数据 |
| 可维护性 | ✅ 通过（含 2 P3） | 注释含 FIX 锚点/机理/real-data basis；共享正则模块级单定义，定义位置（_governance_table_cells 之后）与文件既有组织一致。P3-F1 注释计数口径；P3-F4 测试 helper 三副本重复 |
| 性能 | ✅ 通过 | 每 9-cell 行一次 O(len) 正则 match，无嵌套扫描/N+1 |
| 测试覆盖 | ✅ 通过（含 2 P3） | §3：F-1 两形态+豁免面 retention 全覆盖且内容锚定；红相判别性经静态推演证实。P3-F2/F3 覆盖缺口与登记一致 |

## 5. AI 代码专项 5 项

| 项 | 结论 |
|---|---|
| Mock 残留 | ✅ 无——patch.object(SAMPLE_PATH/GOVERNANCE_DIR) 为合法依赖注入（重定向临时目录），无伪造返回值 |
| 硬编码返回值 | ✅ 无——用例走真实 `check_protocol_compliance()` 文件读取 |
| 幻觉 API | ✅ 无——`_EVIDENCE_DATE_SHAPE_RE`（L12416）、`_governance_table_cells`（L12399）读源实证存在且被正确消费 |
| 未实现 TODO | ✅ 无新增——注释均为 FIX 锚点与机理说明 |
| 过度实现 | ✅ 无——else 分支改造严格对应 F-1 建议方案一，无镀金 |

## 6. Developer 登记边缘 3 项处置判定

| # | 登记 | 裁决 |
|---|---|---|
| 1 | 缺 fact/Location 格截断 LIVE 行（截断在 Date 前，cells[6] 恰为 Date）仍落历史分支静默 | **处置合理**——F-1 原文指定场景为「缺 Date/Notes」，建议方案即单判据 cells[6] 形态；组合判据属新设计决策，留票评估正确（避免本票范围膨胀，D4）。推演证实：缺 Location 行 cells=[EVD,T,Type,Desc,fact,Entry,Date,Gate,Notes]，cells[6]=Date 日期形态 → 历史分支 → 静默。残余漏报面真实但超出 F-1 指定面（P3-F2 补充披露） |
| 2 | 假想历史行 cells[6] 空 → 报 "missing EntryMethod, Date" 字段名错位 | **处置合理**——推演证实报错存在（fail-noisy 无漏报）；真实数据 11/11 cells[6] 均非空日期形态，现状零触发 |
| 3 | write-guard L94 WARN | **无关确认成立**——属 Coordinator 建行面既有披露，与本票修改面无交集 |

## 7. Findings 清单

| # | 级别 | 位置 | 描述 | 建议 |
|---|---|---|---|---|
| F-1 | P3 | verify_workflow.py L12414-12415（正则注释） | real-data basis 声称 "all 12 live 9-cell historical rows"；本席字面统计实测 11 行（11/11 日期形态）。差 1 疑为 code-span 保护口径或计数误差，字面 grep 无法独立裁决 | 注释补口径标注（如 "per Developer census；literal-pipe count=11"）或复核计数。不阻塞（方向主张 11/11+12/12 均成立） |
| F-2 | P3 | check_protocol_compliance 9-cell else 分支（L10077-10104） | 单判据残余面：①缺 fact/Location 格截断 LIVE 行仍静默（=边缘 1，登记合理）；②缺 Notes 格截断 LIVE 行由静默变误报 missing Date（本席新识别行为面，F-1 方案必然副作用，fail-noisy 可接受） | 留票评估组合判据时纳入「缺 Notes 误报面」一并权衡；或在 evidence 写入规范钉住「LIVE 行不得物理删格」 |
| F-3 | P3 | _EVIDENCE_DATE_SHAPE_RE（L12416） | 非分隔符日期形态（20260920/2026年9月2日/段缺）不匹配 → 假想历史行误报截断 LIVE（fail-noisy）；真实数据 11/11 分隔符形态，现状零触发 | 留观察：判据放宽（如 `\d{4}([-/]\d{1,2}){1,2}`）或在写入侧钉日期形态约定，二选一随 FIX-373 同窗口评估 |
| F-4 | P3 | test_verify_workflow.py `_format_issues`（L12071/L12145/L12243） | 同一 helper 在三个测试类中逐字重复（FIX-374 新增第三副本） | 低优先级：提取共享 mixin/模块级 helper；随下一测试窗口顺手处理 |
| F-5 | P3 | 验证声明（运行时面） | 「TDD 红 2F/1P」「指定套件 12 passed」「check-governance 30 issues 全 REQ-092 既有面/evidence_format=0」「cross-refs/manifest/write-guard PASS」因 Bash 禁用未独立复跑 | 运行时终验归 pytest/Check 30 门禁；本席静态推演（§3 红相）+ 数目吻合 + 真实数据抽样（§1）交叉印证 |

## 8. 硬门槛裁决

| 门槛 | 裁决 |
|---|---|
| P0 阻塞数 = 0 | ✅（P0=0） |
| 5 维度全覆盖 | ✅（§4 逐项有结论） |
| 每条发现带 P0-P3 | ✅（F-1~F-5 全标注） |
| 设计一致性（对照 F-1 定性与豁免政策） | ✅（§1/§2：实现=F-1 建议方案一忠实落地；豁免面零弱化独立判定成立；边缘 1/2 与 F-1 定性范围关系核实无误） |
| AI 专项 5 项 | ✅（§5 逐项有结论） |

## 9. 结论

**APPROVED_WITH_NOTES（unresolved_blockers=0）**——P0=0、P1=0、P2=0；F-1~F-5（P3×5）均为非阻塞披露/留观察项。判据在 LIVE 与历史两类布局下推理自洽（LIVE cells[6]=EntryMethod、历史 cells[6]=Date 经代码与真实行双向核对）；豁免面经形式化推演严格缩小零弱化；测试红相判别性经静态推演证实捕获「漏报」与「错位」两形态；Developer 边缘 3 项处置全部合理。可合并。

---

*Reviewer: Code Reviewer Agent（software-project-governance）· R0 · 2026-09-23 · 证据：verify_workflow.py L749+/L10025-10111/L12399-12416 / test_verify_workflow.py L12053-12287 / review-FIX-372-CODE-R0.md §1②/§2/F-1 / evidence-log.md L1-12/L13-L30/L2460/L2545-2555（9-cell 11 行 + 10-cell 14 行字面抽样）/ REQUIRED_SNIPPETS 不涉面核验*
