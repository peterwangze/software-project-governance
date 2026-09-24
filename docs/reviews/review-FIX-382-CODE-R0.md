# Code Review Report — FIX-382（Round 0，串行单席）

- **审查对象**：工作树未提交修改（2 文件，git diff --numstat 实测：verify_workflow.py **41 ins/7 del**、test_verify_workflow.py **80 ins/0 del**，合计 **+121/−7**；任务上下文单文件口径「+48/−7」实为 `--stat` 总变更行数 48=41+7 的误标，总量 +121/−7 正确——见 F-2①）
- **涉及文件**：
  1. `skills/software-project-governance/infra/verify_workflow.py`——9-cell else 分支单判据→三态消歧（L10089-10132：历史 elif（原）→ **trailing-loss elif**（L10109-10122，新增）→ else（L10123-10132））；`_EVIDENCE_DATE_SHAPE_RE` 注释补第二探针 + F-1 裁决口径（L12445-12458）
  2. `skills/software-project-governance/infra/tests/test_verify_workflow.py`——`Fix382NineCellTrailingLossTests` 4 用例（L12273-12352）
- **审查席**：Code Reviewer（只读被审代码与 .governance/；本报告为唯一写产物）
- **前轮引用**：REVIEW-FIX-374-CODE-R0 **F-1（P3，计数口径）/ F-2（P3，①单判据残余面 ②缺 Notes 误报面）/ F-3（P3，非分隔符日期形态留观察）**——本票为 F-2② 清偿 + F-2① 显式不修钉 + F-1 裁决注释 + F-3 不修
- **结论**：**APPROVED_WITH_NOTES（unresolved_blockers=0）**——P0=0，P1=0，P2=1，P3=1
- **工具说明**：本席不受前轮 Bash 禁用约束，**全部运行时声明已独立复跑实测**（红态复现/差分复现/机扫复核/全量套件/verify/cross-refs/manifest），无 Developer-claimed 未验证项

---

## 0. 范围核实

`git diff --numstat` 实测 2 文件 41/7+80/0；`git diff` hunk 恰 2 处：`@@ -10086,17 +10086,45 @@`（check_protocol_compliance 9-cell else 分支）与 `@@ -12420,8 +12448,14 @@`（正则注释块）。test 文件单 hunk `@@ -12270,6 +12270,86 @@`（纯插入新类）。**无范围外修改**：len<9 分支（L10055-10059）、len≥10 分支（L10069-10076）、`_split_governance_table_row`（L12377-12426）、`HistoricalExemptionTests`（L12601，FIX-376/DEC-232 分叉面）零触碰 ✓。`REQUIRED_SNIPPETS` 等文档钉不涉本票修改面 ✓。

## 1. 组合判据正确性——形式化核验 + 30 输入穷举差分实测（MUST 审查点 1）

**三态分支覆盖完备性**（L10104/10109/10123）：分支谓词为 `date(c6)` / `¬date(c6) ∧ date(c7)` / `else`（=`¬date(c6) ∧ ¬date(c7)`）——elif 链互斥且穷尽，逻辑覆盖完备 ✓。语义核验：LIVE 10-cell 布局（L10037-10039 注释）下尾格丢失（Notes→9 格或 Gate→9 格）使真实 Date 左移至 cells[7]、EntryMethod 文本留在 cells[6] → 落 trailing-loss 分支，`Gate` 丢与 `Notes` 丢在 cells[8] 残留内容上互异但机器不可分，统一报「Gate/Notes (trailing LIVE cell lost — Date present at shifted offset)」与决策表 R4/R5「内容不可分统一报」一致 ✓；Location/EntryMethod 在未移位偏移继续校验（L10115-10118），空格与丢尾格可共存 ✓。

**不变量实测证明**（本席构建 30 输入穷举差分：c5∈{"", 非空} × c6∈{"", 自由文本, 2026-09-24, 2026/9/2, "G11"} × c7∈{"", 2026-09-24, "G11"}，HEAD 模块（git show 提取至临时目录）与现行模块逐输入对比 `check_protocol_compliance()["evidence_format"]`）：
- **计数不变**：30/30 输入 issues 条数相等，0 mismatch——申报「issues 计数逐输入不变（两子分支各恰追加一条）」实测成立。机理：每行至多合并追加 1 条 issue（L10134-10137），且三个非历史子分支均无条件含一条追加（else 恒报 Date L10132；trailing 恒报 Gate/Notes L10119-10122）→ 有缺失必报 ✓。
- **静默集相等**：HEAD 与现行静默集**恒等**，实测均为 `{c5≠"" ∧ date(c6)}`（6 组合）——**S_new = S_old = {date(c6) ∧ c5≠""} 申报不变量实测成立**，检测面零缩小、豁免面零变化 ✓。
- **差异面精确限定**：消息差异恰 6 组，全部且仅在 `{¬date(c6) ∧ date(c7)}` R4/R5 面，形态逐字为 HEAD `"…missing fields — Date"` → CUR `"…missing fields — Gate/Notes (trailing LIVE cell lost — Date present at shifted offset)"`（Location/EntryMethod 半段在 c5="" 组合中两版一致保留）——纯消息准确化，无静默化、无新增报错 ✓。

## 2. R1/R2/R3 不可分性论证核验（MUST 审查点 2，逻辑核验）

推演证实决策表「丢 Date 前的格（fact/Location/EntryMethod）显式不修 + 台账披露」取舍成立：
- **R1/R2（丢 Location/EntryMethod→9 格）**：cells = [EVD,T,Type,Desc,fact,Entry,Date,Gate,Notes]，cells[6]=Date 日期形态 → 走**历史分支**；与真历史行 [EVD,T,Type,Desc,fact,Author,Date,Gate,Notes] 逐位对齐后**差异仅在 cells[5]**（EntryMethod 文本 vs Author 文本）——两者皆自由文本（L10101-10102 注释同款论证），任何内容形态启发式区分二者必以「真历史行误伤」为代价，与豁免面零变化约束直接冲突 → 不可分性论证**成立**，不修合理。
- **R3（丢 fact，穷举新增）**：cells[6] 仍为 Date → 同落历史分支，同一不可分结构 ✓。
- **残余面审计钉**：`test_lost_location_before_date_documented_residual_face`（EVD-913 fixture，L12338-12352）断言 `issues == []`——红态亦绿（实测，§3），性质为**披露性回归钉**（docstring 自述 "pin…NOT an endorsed defect"）：未来任何把判据扩展到 cells[5] 面的改动会立即使其变红，使「接受静默」可审计。设计正确 ✓。

## 3. 测试判别力——红态实测逐字捕获（MUST 审查点 3）

本席以 `git show HEAD:` 提取 HEAD 模块置入临时 infra 副本（HEAD 25534 行 vs 工作树 25568 行，Compare-Object 48 差异行=41 新独有+7 旧独有，自洽），对新类实跑红态：

| 用例 | 红态（HEAD 模块） | 结果 | 假阳性逐字捕获 |
|---|---|---|---|
| test_trailing_notes_cell_lost…（EVD-910） | `'Gate/Notes' not found in 'EVD-910: missing fields — Date'` | **FAILED** | ✓ Date 在场的行被报 missing Date |
| test_trailing_gate_cell_lost…（EVD-911） | `'Gate/Notes' not found in 'EVD-911: missing fields — Date'` | **FAILED** | ✓ 同上 |
| test_trailing_loss_with_empty_location…（EVD-912） | `'trailing LIVE cell lost' not found in 'EVD-912: missing fields — Location, Date'` | **FAILED** | ✓ 「Location, **Date**」中 Date 半为假阳性 |
| test_lost_location_before_date…（EVD-913） | （旧代码同样零 issue） | **PASSED** | 审计钉（非判别性，设计如此） |

**红态 3F/1P 与 Developer 申报精确一致，且失败消息逐字展示了 F-2② 假阳性原文** ✓。绿态（现行模块）4P 实测 ✓。断言非仅计数：assertIn("Gate/Notes")/("trailing LIVE cell lost")/("Location") 内容锚定 + len==1 ✓。

## 4. 真实数据零影响——差分复现 + 机扫复核（MUST 审查点 4）

- **差分 IDENTICAL 复现**：HEAD 模块与现行模块对真实 `.governance/evidence-log.md` 同跑 evidence_format，实测 **0=0 issues**（本席 repro 脚本，GOVERNANCE_DIR/SAMPLE_PATH patch 至真实目录）——与申报一致 ✓。
- **机扫复核（production parser census）**：以现行 `_governance_table_cells` + `_EVIDENCE_DATE_SHAPE_RE` 扫描实测——**EVD 行总数 467 ✓、9-cell 行（parser 口径）恰 12 ✓、cells[6] 日期形态 12/12=100% ✓、cells[7] 日期形态 0 ✓（注释「non-date cells[7]」成立）、`¬date(c6)∧¬date(c7)` 新 else 面 0 触发**——生产数据上新分支零 incidence，历史豁免面零触碰，与注释 L12453-12456 声明逐项吻合 ✓。
- **F-1 裁决复核（12/12 成立；字面 11 系解析器保护偏置）**：字面管道拆分口径实测 9-cell=**11**；parser 12 与 literal 11 之差恰锁定 1 行偏置——**EVD-885**（parser 9 格 / literal 10 格），为 FIX-374 R0 F-1 所列 11 行（EVD-879/878/877/876/886/887/888/889/890/891/893）之外的第 12 行 ✓ 裁决「12/12 成立」**实测确认**。但**偏置机制归因不准确**：EVD-885 行内反引号数为 0，被保护管道位于 `[^\\s,;|*]` 正则字符类内——保护状态是 `_split_governance_table_row` 的 **bracket-depth**（L12412-12419：`{[`/`}]` 深度>0 时管道不拆分），**非 code-span**（亦非 JSON-string quote）→ 见 F-1（P2）。

## 5. retention 豁免面（MUST 审查点 5）

- 四类 retention 实测：`EvidenceFormatColumnLayoutTests`(3) + `Fix373SplitterCodeSpanQuoteTests`(6) + `Fix374NineCellDisambiguationTests`(3) + `HistoricalExemptionTests`(6) = **18 passed**；`-k "Exemption"` 全口径 = **10 passed**（HistoricalExemptionTests 6 + 其他豁免类 4）；申报「22P」口径实为 **12P（前三类）+ 10P（Exemption 全口径）= 22**，可复现、两口径无重叠——申报数字成立但类名列举口径未注明（F-2②）。
- **HistoricalExemptionTests（FIX-376/DEC-232 分叉面）6P 全绿**，且 diff 单 hunk（L12270+80 插入）零触碰该类——**新判据不触碰分叉面实测确认** ✓（census 12/12 走历史分支亦佐证豁免面零变化）。
- FIX-374 既有 retention 钉（EVD-906/907/908 三用例）在 `Fix374NineCellDisambiguationTests` 内随全量绿 ✓。

## 6. 验证复现汇总（MUST 审查点 6）

| 申报 | 实测 | 裁决 |
|---|---|---|
| TDD 红 3F/1P（假阳性逐字捕获） | 3F/1P，逐字见 §3 | ✓ 精确一致 |
| 基线 929P+126sub → 933P+126sub（+4 零回归） | **933 passed, 126 subtests passed**（224.75s，全量单文件） | ✓ 终态精确一致，+4=新类 |
| 真实数据差分 IDENTICAL（HEAD vs 现行 evidence_format） | 0=0 issues | ✓ |
| 机扫 467 行 EVD、9-cell 恰 12、cells[6] 100% 日期形态 | 467/12/12÷12 全命中 | ✓（偏置行=EVD-885，机制归因见 F-1） |
| verify 主检查 PASSED | **PASSED**（尾部 4 条 non-blocking WARN=STATIC_PIN 漂移双向检出） | ✓ |
| cross-refs/manifest PASS（869/998） | cross-refs PASS（725 references，无 dangling/deprecated/circular）；manifest PASS（**Canonical 869 / Actual 998**） | ✓ 数字精确吻合 |

**STATIC_PIN 已知边缘核实**（申报：12534/12658→12614/12738，收尾处置）：实测 `check-version-consistency` PASSED + 恰 4 条 WARN——L12614/L12738 未豁免 pin（现内容：L12614 fixture task 行、L12738 legacy REQ 行，均含 0.87.0 token）+ L12534/L12658 stale exemption；漂移量 +80 与 test 文件插入行数吻合。rot-guard（WARN-only）如实检出、verify 不阻塞，与「Coordinator 收尾 version.py 重锚」处置一致 ✓。**注意：该漂移不会自愈，收尾重锚前 4 条 WARN 将持续在场**——已由申报覆盖，非本票发现。

## 7. 「同一注释块内非越界顺带改」声明核验（MUST 审查点 7）

F-1 裁决注释落在 `_EVIDENCE_DATE_SHAPE_RE` 定义上方的同一注释块内（L12445-12458），该块正是 FIX-374 R0 F-1 指认位置（当时的正则注释）——顺带改与被审对象同注释块、同一次读取语境，**边界声明成立** ✓。else 分支注释（L10090-10103）为 F-2② 本体非顺带。无越界面。

## 8. 五维度结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | ✅ 通过 | §1 三态完备 + 30 输入穷举差分：计数不变/静默集恒等/差异面精确限定；§2 不可分性论证成立 |
| 安全性 | ✅ 通过 | 正则 `^\d{4}[-/]\d{1,2}[-/]\d{1,2}$` 量词有界无 ReDoS；纯本地 Markdown 解析无注入面；无敏感数据 |
| 可维护性 | ✅ 通过（含 1 P2） | 注释含 FIX 锚点/机理/real-data basis；elif 结构清晰；P2-F1 注释机制归因不准确 |
| 性能 | ✅ 通过 | 每 9-cell 行至多 2 次 O(len) 正则 match（第二探针仅非 date(c6) 面触发；生产 0 触发）；无嵌套扫描 |
| 测试覆盖 | ✅ 通过 | §3 红态逐字判别 + EVD-913 审计钉；R4/R5 两丢失形态+双缺陷组合+残余面四象限覆盖；生产面 census 佐证 |

## 9. AI 代码专项 5 项

| 项 | 结论 |
|---|---|
| Mock 残留 | ✅ 无——patch.object(SAMPLE_PATH/GOVERNANCE_DIR) 为既有合法依赖注入模式（重定向临时目录），无伪造返回值 |
| 硬编码返回值 | ✅ 无——用例走真实 `check_protocol_compliance()` 文件读取 |
| 幻觉 API | ✅ 无——`_EVIDENCE_DATE_SHAPE_RE`（L12459）、`_governance_table_cells`（L12436）、`_split_governance_table_row`（L12377）读源实证存在且被正确消费 |
| 未实现 TODO | ✅ 无新增——注释均为 FIX 锚点与机理/裁决说明 |
| 过度实现 | ✅ 无——elif 分支严格对应 F-2② 清偿面，EVD-913 为决策表钉测试非镀金 |

## 10. Findings 清单

| # | 级别 | 位置 | 描述 | 建议 |
|---|---|---|---|---|
| F-1 | P2 | verify_workflow.py L12457（FIX-382 新增注释） | F-1 裁决注释「literal-pipe grep counts 11 rows: **code-span** pipe counting bias」机制归因不准确：实测偏置行 EVD-885 行内 **0 个反引号**，被保护管道位于正则字符类 `[^\\s,;|*]` 内，真实机制是 `_split_governance_table_row` 的 **bracket-depth 状态**（L12412-12419，`{[`/`}]` 深度>0 时管道不拆分），非 code-span、亦非 JSON-string quote（FIX-374 R0 F-1 原文「code-span/quote 保护」同样漏列 bracket）。裁决结论本身（12/12 成立）实测不变 | 措辞修正为「parser-protected pipes（code-span / JSON-string / bracket-depth state）」或点名 bracket-depth；零行为影响，可随下次触达该注释的批次顺带修，不阻塞 |
| F-2 | P3 | 任务/申报口径（非代码） | 两处验证声明口径标注：①单文件「+48/−7」实为 `--stat` 总变更行（numstat 实测 41 ins/7 del；总量 +121/−7 正确）；②retention「22P」= 前三类 12P + `-k Exemption` 全口径 10P（含 HistoricalExemptionTests 6P + 其他豁免类 4P），四类单列口径为 18P——数字均可复现，仅类名列举未注口径 | 无需改码；后续验证声明建议标注计数口径 |

## 11. 硬门槛裁决

| 门槛 | 裁决 |
|---|---|
| P0 阻塞数 = 0 | ✅（P0=0） |
| 5 维度全覆盖 | ✅（§8 逐项有结论） |
| 每条发现标注级别 | ✅（F-1=P2、F-2=P3） |
| 设计一致性（对照 FIX-374 F-1/F-2/F-3 与决策表） | ✅（§1/§2/§7：F-2② 组合判据忠实落地、F-2① 显式不修+钉、F-1 裁决归位同注释块、F-3 不修有 census 佐证、DEC-232 分叉面零触碰） |
| AI 专项 5 项 | ✅（§9 逐项有结论） |

## 12. 结论

**APPROVED_WITH_NOTES（unresolved_blockers=0）**——P0=0、P1=0、P2=1（注释机制归因措辞）、P3=1（申报口径备注）。组合判据三态完备，静默集 S_new=S_old 与 issues 计数不变量经 **30 输入穷举差分实测证明**；R1/R2/R3 不可分性论证成立且残余面以 EVD-913 钉测试可审计；4 用例红态 3F/1P 逐字捕获假阳性原文；真实数据差分 IDENTICAL（0=0）、census 467/12/12 全命中、偏置行 EVD-885 实证 F-1 裁决成立（归因措辞修正见 F-1）；retention 豁免面（含 FIX-376/DEC-232 分叉面）零触碰且 933P+126sub 全量零回归；verify/cross-refs/manifest 全 PASS。可合并。

---

*Reviewer: Code Reviewer Agent（software-project-governance）· R0 · 2026-09-24 · 证据：verify_workflow.py L10055-10137/L12377-12426/L12445-12459 / test_verify_workflow.py L12053-12068/L12273-12352/L12601 / review-FIX-374-CODE-R0.md F-1/F-2/F-3 / checks/version.py L205-299 / 实测：红态 3F/1P（HEAD 模块临时副本）、全量 933P+126sub、差分 0=0、census 467/12/12（偏置行 EVD-885 bracket-depth 实证）、fuzz 30 输入（计数 0 mismatch/静默集恒等/差异 6 组全限 R4/R5 面）、retention 18P+Exemption 10P、verify PASSED（4 WARN=pin 漂移）、cross-refs PASS 725 refs、manifest PASS 869/998*
