# REL-090 — M-3 产品代码半面窄域复审（0.89.0 发布窗 33d19b0..HEAD=bda7e88）

- **Round**: 窗口级独立复审 R0（七票个审 R0 已全 AWN/APPROVED——本审不重复个审，只做四项抽查）
- **审查者**: Code Reviewer Agent（只读）· **日期**: 2026-09-26 · **审查对象**: HEAD=bda7e88 提交态（git log/show + grep/read）
- **硬门槛自检**: ①零测试执行（消费 EVD-1184 与个审既有实测）②四项逐一裁决 ③本报告为唯一写入物 ④只读命令集（git log/show、grep、read、Select-String 清点）
- **窗口枚举**: 33d19b0..HEAD 共 16 commit；产品代码票 commit：FIX-393(8a94d64)/FIX-394(3cb4048)/FIX-390(def9508)/FIX-392(65c8e4b)/FIX-395(7795f59)/FIX-391(c9b7415)/FEAT-065(ab7a8e1)；M-2 批(bda7e88) 触 architecture-baseline.json+test_archguard_ratchet.py+checklist（与任务书申报一致）

---

## 一、抽查义务 A（DESIGN-R0 F-6）：FIX-390/392 红侧 fixture 非预录形态 — **PASS**

| 票 | git 事实 | 个审红相记录 | 判定 |
|----|---------|-------------|------|
| FIX-390 | `git log --follow` ：test_fix390_structured_status_judgment.py **唯一命中 def9508**（607 行随票新增，无前置预录提交）；`git show def9508` 抽验断言直接引用本票新增判据符号（`vw._status_is_writer_committed_cell`、`vw._hot_status_completion_state`、"consumed BY IDENTITY — FIX-393" 注记在测试源内） | review-FIX-390-CODE-R0.md §1-#2：同套件 × HEAD 代码 = **16F/4P**，4 绿恰为零回归守恒用例（逐一具名）→ 非自证；§3-⑨ 如实记录申报 19F vs 实测 16F 的 subTest 计数口径差，实质红→绿成立 | ✅ 真红 |
| FIX-392 | test_verify_workflow.py 窗口增量 **+364 行落在 65c8e4b**（CompositeKey 新类随票提交） | review-FIX-392-CODE-R0.md §一-#2：def9508 HEAD worktree 产品代码 + staged 测试 = **6F/3P**（与申报精确一致），失败形态 = V3 伪像（`Lists differ: [{'rule':'V3',…'BLOCKED'}] != []`）+ `KeyError: 'chains'`（HEAD 无 chains 视图）——失败机理恰为本票新增机制所针对，报告明示「测试非恒绿」 | ✅ 真红 |

**A 裁决：PASS**——两票红侧测试均出生在修复 commit 本体、红相（判据修复提交前失败且失败面与修复机理一致）由个审报告独立记录，非预录形态。

## 二、抽查义务 B（F-5）：批次一中间态独立 EVD — **PASS**

- **存在性**: EVD-1172（evidence-log L2773）/EVD-1173（L2776）/EVD-1174（L2781）三条均在案，均 ✅ 完成/G11/2026-09-26/机录 op 锚（op-b120f8ba…/op-ec817a35…/op-e81858cf…）。
- **时序与如实性**: EVD-1172 自述「批次一首票 DEC-246、为 FIX-394/FIX-390 提供判据基础设施」↔ version-plan §2 L32 批次一（FIX-393→FIX-394）↔ commit 序 8a94d64→3cb4048 一致；其申报（17/17、377P/0F、tpa 零推荐+Blocked=None、消费方 3F 基线同形）与 review-FIX-393-CODE-R0 §5 #1/#2/#3/#5/#6 亲跑记录逐项吻合。EVD-1173 申报（28P+12S、dry-run 零写入、13 行=B~E 10 票+发布链 3 票）与 review-FIX-394-CODE-R0 L28/L30/L82 亲跑对账吻合；R0 P1 F-1→R1 APPROVED 修复链在案，EVD-1174 的 13 行 execute 对齐位于修复之后（符合 R0「13 行落地前修复」建议次序）。
- **B 裁决：PASS**。

## 三、抽查义务 C：EVD-1174 的 19→13 映射 — **PASS**（附 P3-2/P3-3 注记）

- **13 行凭证实测**: `.governance/plan-tracker.md.ops.jsonl` 中 `"action":"suffix_refresh"` 收据 = **13 张**；目标 ID = FEAT-060/061/062/063/064+FIX-383/384/385+FEAT-044/045（10）+REL-087/088/089（3）——与 EVD-1173/1174 自述、review-FIX-394-R0 L82 活体枚举**三源逐 ID 精确一致**。
- **19 构成自洽**: 19 = 16 missing-task ID + 2 overstate + 1 bundle（16+2+1=19 ✓）；滞留文本类 13 行 ⊆ 19，其余 6 = roadmap 行关联列（路线图行更新承载）+ FIX-393 判据传播面（FIX-393 集成消解）——19−13=6，EVD-1174 正文自述逻辑内部一致。
- **C 裁决：PASS**。措辞/口径注记见 P3-2（「剩余 8 处」枚举加和含糊）与 P3-3（28c 计数跨时点 19/20 漂移无溯源注记）——均不动摇 13 行对账本身。

## 四、跨票共面 + 终态词汇一致性 — **PASS**（词汇判据面零分叉；记录面 P2×2 勘正义务）

### 4.1 共面/串行声称 vs 实测（git log --stat 全窗枚举）

| 文件 | version-plan §2 声称 | 窗内实测触碰 | 出入 |
|------|---------------------|-------------|------|
| verify_workflow.py | 三票共面 FIX-390/392/393（L36 F-1 落字） | **四票**：FIX-393(+39)/FIX-390(净+86)/FIX-392(+1 re-export)/**FIX-395(45±，7795f59)**；另 REL-091 bump（b66bd25，12± 版本锚面，非判据） | **P2-1**：FIX-395 后补入载荷（DEC-244 六票+FIX-395）但 §2 未回改；串行纪律实际未破（窗口 commit 严格串行；M-2 组合四项 122P+全量 4217P 实测在案——EVD-1184） |
| closure_chain.py | 串行链，且组合③（L128）称「FIX-391 × FEAT-065 × **FIX-394 closure 腿**」三票串行面 | **两票串行**：FIX-391(c9b7415)→FEAT-065(ab7a8e1)；**FIX-394 零触碰 closure_chain.py**（3cb4048 仅 task_row_update.py+测试；EVD-1173 文件面同） | **P2-2**：「FIX-394 closure 腿」（L24 文件面/L128 组合③）未落地且声称未勘正 |
| task_priority.py / archive.py / task_row_update.py | 各单票（L23/L23/L24） | FIX-393 / FIX-393 / FIX-394 单票触碰 ✓ | 无出入 |

### 4.2 committed 终态词汇判据面抽验（每文件 ≤3 锚，全 HEAD 提交态）

- 链元组 `("committed", re.compile(r"\bcommitted\b|已提交"))` **三处同形**：task_priority.py:215 / archive.py:461 / task_row_update.py:291（写入器 canonical；tp/archive 为声明镜像，守护测试钉 pattern 串相等——review-FIX-393 §1 独立核验在案）。
- verify_workflow.py **身份复用非第四副本**：`import task_row_update`（:92）→ `_WRITER_STATE_MARKER_CHAIN = task_row_update._STATE_MARKER_CHAIN`（:10623）；committed 判据消费 :10627-10639（writer-terminal 谓词）、:12437-12445（FIX-390 hot 面按身份复用）。
- task_row_update.py 刷新/对齐门全为链首 committed+〔op-32hex〕锚（:1249-1323 detect→refresh→re-read 双向拒绝；无锚/多锚/非终态拒绝）；终态翻转清滞留后缀（:494-506）。
- closure_chain.py **无独立 committed 判据面**：行状态判定委托 writer `--inspect`（:415 "task_row_state" 探针；:60 "not a writer — never parses plan-tracker content"）——结构上无分叉可能；其 terminal 词汇（finalized/cancelled）为 closure 域独立轴，非同义词表面。
- 已知刻意分叉（FIX-376 F-3 vw W-7 段首规则保守面）经 review-FIX-390 §2 复核确认保留，与申报一致，非漂移。
- **D 裁决：PASS**（判据面零分叉）；记录面出入列 P2-1/P2-2。

---

## 五、发现列表（P0=0 / P1=0 / P2=2 / P3=4）

- **P2-1 共面声称失实（FIX-395 引擎腿未入账）** — version-plan-0.89.0.md L36。事实：实测 verify_workflow.py 窗内四票触碰（+bump）而 §2 仍写「共面票实为三票（FIX-390/392/393）」。影响：记录面事实精度（P-v1 原则 1）；无代码缺陷——串行纪律实际保持、组合/全量实测覆盖引擎面。建议：M-3 收口批对 L36 作一行勘正（四票+bump 实测口径）。
- **P2-2 「FIX-394 closure_chain 腿」未落地未勘正** — version-plan §2 L24/L128。事实：FIX-394 窗内 commit 与 EVD-1173 文件面均为 task_row_update.py+测试；closure_chain.py 实测两票串行。建议：勘正 L24 文件面与 L128 组合③ 为实测口径；并核对 0.89.0 checklist 组合③ 行是否按两票口径回填。
- **P3-1 FIX-392 triage 文件面缺 checks/review_domain.py** — §2 L27 仅列 verify_workflow.py；实测核心实现落 checks/review_domain.py（+205/−26）+verify_workflow.py(+1)。记录精度建议。
- **P3-2 EVD-1174「剩余 8 处」枚举加和含糊** — 「7 行 ✅ 历史叙事+1 行 dev 态活体+FIX-394 行叙述性引用」严格加和 7+1+1=9≠8，须按第三项非加性读方自洽；非承重披露（8 处已定性合法、与 13 行清账分列）。建议后续加计数前缀。
- **P3-3 Check-28c 计数跨时点漂移无溯源注记** — EVD-1174 记 19 条 vs review-FIX-390 P3-5 与 FIX-395 commit 记 20 条：移动数据面不同时点各自自洽，但无「时点+口径」注记，复核易误读为矛盾。
- **P3-4 closure_chain.py:882 步骤描述滞留 legacy 词形** — "task-row-update: review 通过 → ✅ 完成" 为散文描述，写入器终态实际已为 committed token+锚（FIX-393/394 后）。非判据面，随 batch 2.3 词表面退役自然消解。

## 六、窗口级结论

## **APPROVED_WITH_NOTES**（`unresolved_blockers=0`）

- 四项逐一裁决：A **PASS** / B **PASS** / C **PASS** / D **PASS**（词汇判据面零分叉；记录面 2 项勘正义务）。
- 计数：**P0=0，P1=0，P2=2，P3=4**。两处 P2 均为 version-plan 记录面与实测的出入（纯文档勘正），不属产品代码缺陷——红侧 fixture 真实性、EVD 凭证链、19→13 映射、终态词汇单源四项审查性事实链全部独立成立。
- 裁决理由：按「P0=0 且无 BLOCKING → 通过终态」处理；建议 P2-1/P2-2 随 M-3 收口批作 §2 勘正（不触发代码返工），P3×4 留档。

## 附：可复查命令清单

```
git log --oneline --stat 33d19b0..HEAD                      # 窗口 16 commit 全枚举（共面实测源）
git log --follow --oneline -- …/infra/tests/test_fix390_structured_status_judgment.py    # 仅 def9508
git show def9508 -- …/infra/tests/test_fix390_structured_status_judgment.py              # 断言符号抽验
Select-String -Path .governance/plan-tracker.md.ops.jsonl -Pattern '"action":\s*"suffix_refresh"' -Encoding UTF8   # 13 张收据
grep -n "committed" …/infra/{task_priority,archive,task_row_update,verify_workflow,closure_chain}.py     # 词汇锚（§4.2 行号）
```
