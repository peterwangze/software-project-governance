# Review Record: FIX-425 — 后置代码审查（CODE，R0）

- **Task**: FIX-425 — review-FIX-424-CODE-R0 裁决①执行票：provenance_domain.py 模块 docstring 两处修正（纯注释零行为面）
- **Reviewer**: Code Reviewer Agent（只读；round 0；未写任何文件——报告全文随结构化返回交付，由 Coordinator 落盘与机录）
- **审查对象**: docs/reviews/FIX-425-R0.diff + skills/software-project-governance/infra/checks/provenance_domain.py 全文（692 行）+ docs/architecture/ADR-021-meta-mechanisms.md §3.2.3（L330-368 实读）+ docs/reviews/review-FIX-424-CODE-R0.md + infra/exception_registry.py（L1-40 + I/O 模式 grep）
- **日期**: 2026-10-03
- **结论**: **APPROVED_WITH_NOTES** — **unresolved_blockers=0，P0=0**

## 1. 变更概述
纯 docstring 修正票（单文件两 hunk，均位于模块 docstring L2-73 内）：
1. **L6-8（F2 修复）**：`every function here is a pure predicate; …` → `the judgement functions here are pure predicates; FEAT-083 appends one disclosed file-reading collection core (see the purity contract below); …`
2. **第 4 bullet L37（F1 修复）**：`(FEAT-083)` 后插入 `— ADR-021 §3.2.3 (W(session))`，其余原词全保留仅 reflow。

## 2. 逐行/逐句事实核验（新表述 → 代码现状）
| # | 核验点 | 事实锚点 | 判定 |
|---|---|---|---|
| 1 | "the judgement functions here are pure predicates" | 三判定函数 check_priority_inversion(L151)/check_release_admission(L317)/session_closure_rate(L433)：确定性输入→dict、零 I/O、never raises；两列匹配臂 closure_evidence_events(L522)/closure_risk_events(L551) 亦纯（text→events 零 I/O）；全模块 I/O 模式（Path/read_text/date.today）仅存在于 L573/L619 两函数内 | ✅ |
| 2 | 字面矛盾消除 | 旧句被 read_deferred_ledger_events(L573)/collect_session_closure_events(L619) 两文件读函数证伪；新句主语限定 judgement functions（真）+ 采集核显式披露 + 指针，矛盾消除 | ✅ |
| 3 | "one disclosed file-reading collection core" ↔ purity contract "ONE disclosed file-reading collector"（L49-51） | 同计数（=1）、同指称；ledger arm（L573）按 bullet 4 自身枚举为该 core 组成臂——core-with-arms 计数口径三处（L6-7 / L49-51 / bullet 4）一致 | ✅ 可辩护且自洽（残余精度见 N-3） |
| 4 | 指针可达性 | "(see the purity contract below)" → 同 docstring L45 起段，紧随 bullets | ✅ |
| 5 | 第 4 bullet 锚真实性 | ADR-021 L337（§3.2.3 节题「会话内闭环率指标」）+ L351（W(session) 窗口函数定义原文）实读确认；与函数级锚 L622、节注释 L493 一致 | ✅ |
| 6 | "each anchored to its ADR section"（L16） | 4/4 bullet 显式 § 锚：§2.2.3(L18)/§2.2.4(L26)/§3.2.3(L32)/§3.2.3+W(session)(L37)——FIX-424 F1 指出的 bullet 级缺口闭合 | ✅ |
| 7 | reflow 原词零删改 | 逐词比对：合并换行后新旧全文唯一差异 = 在 `(FEAT-083)` 与 `:` 之间插入 ` — ADR-021 §3.2.3 (W(session))`；其余每一词逐一相同 | ✅ |
| 8 | 零行为变更 | 两 hunk 全部行位于模块 docstring（L2 起、L73 `"""` 终止）内；终止符旧 L70→新 L73（净+3）与 +10/−7 吻合 | ✅ |

## 3. 发现列表（全部 P3，零阻塞）
| ID | 级别 | 位置 | 问题 | 处置建议 |
|---|---|---|---|---|
| N-1 | P3 | docs/reviews/FIX-425-R0.diff hunk 2 | **工件渲染异常（非代码问题）**：未变更行被渲染为 −/+ 对（工件正文计 8删/10增），而 hunk 头 `+34,13` vs `-32,12` 与任务口径 10增/7删 对应最小 diff。三重独立证据证实真实变更 = 7删/10增（①该行新旧文本逐字节相同；②docstring 终止符 L70→L73 净+3；③函数级锚 L619→L622 净+3） | 零代码影响（新侧与工作树逐行一致）；建议 Coordinator 后续 diff 工件用规范 `git diff` 生成保持头/体自洽（卫生项，可不修） |
| N-2 | P3 | provenance_domain.py L13-14（**非本票回归**） | "anchors are ADR-021 §2.2 section references" 字面不穷尽（4 bullet 中 2 个锚 §3.2.3）——本票前已如此；可辩护读法=该句限指 check-box/wiring 锚族 | 无需随票动作（D4 纯粹性）；未来 docstring 微票可顺带消歧 |
| N-3 | P3 | provenance_domain.py L6-7（裁决记录） | "one collection core" 为架构复合体计数；按「公开文件读函数」数仍得 2。**裁决：可辩护自洽**——口径三处一致、指针链完整（bullet 4 枚举臂 + L574 自述 "Ledger arm" + purity contract） | 不修；如求极致精确可未来微票写明 ledger arm 为 core 组成部分（可选） |

## 4. 5 维度逐项结论
- **正确性 PASS**：§2 八项事实核验全过。
- **安全性 PASS/N-A**：纯注释零新输入面；文件读行为如实披露（透明度正向）。
- **可维护性 PASS（净改善）**：F1/F2 双缺口闭合，docstring 内部恢复自洽；遗留 P3 均带可不修处置。
- **性能 PASS/N-A**：docstring 不在执行路径。
- **测试覆盖 PASS/N-A**：零行为变更无新测试义务；架构事实由 FEAT-083 单源/interface-equivalence 测试机检承载（Developer 自报定向 94 passed 基线持平——未重跑，作声称对待）。

## 5. AI 代码专项 5 项
1. mock 残留：无（纯 docstring）。2. 硬编码返回值：无（无代码）。3. 幻觉 API/引用：无——`ADR-021 §3.2.3 (W(session))` 经 ADR 原文实读证实。4. 未实现 TODO：无。5. 过度实现：无——变更面恰为裁决①两点，单文件 docstring（D4）。

## 6. 设计一致性比对
- vs review-FIX-424-CODE-R0：F1 verbatim 落地 + F2 按裁决另立微票执行——D4 遵守 ✅
- vs ADR-021 §3.2.3：锚真实（L337/L351）；collect_session_closure_events 即 W(session) 窗口采集实现 ✅
- vs purity 契约（L45-53）：ONE collector 口径一致；function-local import 披露与实况吻合 ✅
- vs 模块自身词汇：与 L638 判定件/采集件二分连贯 ✅

## 7. 三项边缘披露裁决建议
1. **行号漂移（L619→L622）**：属实。裁决：无需动作——review 记录为历史快照；建议后续引用以「函数名+锚文本」替代裸行号（新旧 L619 语义重合误读风险）。
2. **bullet 4 两处 "W(session)"**：裁决：保留——锚内 (W(session)) 兼具消歧作用（§3.2.3 内区分 bullet 3 与 bullet 4），非纯冗余。
3. **exception_registry.py L26**：实读核实（零写操作）。裁决：同意不立项——"read-only and returns NEW structures"（无变异）与文件读取不矛盾，性质不同于原 "pure predicate"（隐含零 I/O）矛盾。

## 8. 硬门槛裁决
- P0 阻塞 = 0 ✅；5 维度覆盖 100% ✅；每条发现标注级别 ✅；设计一致性检查完成 ✅；AI 专项 5 项逐一有结论 ✅；diff 逐行读完 + reflow 逐词比对 ✅；两处新表述逐句事实比对 ✅；零行为变更确认 ✅

**终态：APPROVED_WITH_NOTES（unresolved_blockers=0）**

## 限制声明
- 无 Bash：Developer 自报 verify/xref/manifest/定向 94 passed 未重跑，作声称对待；可静态核实的事实已全部独立核实。
- 「工作树 diff 仅此一文件」未独立枚举；以 diff 工件 + 目标文件工作树一致性替代核实。
- 未写任何文件（含 .governance/ 与 docs/reviews/——留给 Coordinator 落盘与机录）。
