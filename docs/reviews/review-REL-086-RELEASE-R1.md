# REL-086 发布半面复审报告（RELEASE · R1）

> **Round**: R1（复审——前轮引用：`docs/reviews/review-REL-086-RELEASE-R0.md`，机录号 REVIEW-REL-086-R0-RELEASE，R0 结论 NEEDS_CHANGE/unresolved_blockers=3，P0=0/P1=3/P2=5/P3=5）
> **Task**: REL-086 — 0.88.0 版本规划草案 v2（M-0，DEC-229 预授权）发布半面复审
> **Reviewer**: Release Reviewer Agent（同一审查席——M7.4 T1 同席复审）
> **审查对象**: `docs/planning/version-plan-0.88.0.md`（**草案 v2**，2026-09-24 修订，全文 115 行逐行重读）+ 治理数据修订（plan-tracker 热表/roadmap、change-triage ×7、execution-packets ×3、review-FIX-373-CODE-R0.md 修订）
> **日期**: 2026-09-24

---

## 0. 审查方法与证据边界

**实测命令（本席实际执行）**：
1. `verify_workflow.py check-governance`（全量，exit 0）→ **Result: ISSUES FOUND — 45 issue(s)**（R0 44）；关键面变化：**Check 10 PASS**（R0 BLOCKING×1 消解）、**Check 26 PASS**（R0 BLOCKING×3 消解——「agent-locks.json schema valid, 2 active task(s), 6 file lock(s)」）、**Check 18c 3 包 PASS**（R0 2 包）、**Check 31 仍 BLOCKED**（2 FAIL——ragged table row，inventory hash `c1345ca9…`，候选 954）。不变面：Check 16/17 各 3 FAIL（预期披露）、18d/e/f 三票 FAIL（占位——义务时点内）、28s ERROR（1623.5KB，advisory）、Check 8 PASS（无过期风险）。
2. `verify_workflow.py check-loop-runtime-claims` → `"semantic_units": 306179`（R0 305,604 → +575 治理写入增长；**≤361,923 容量面 PASS**）、`"verdict": "BLOCKED"`——**BLOCKED 由记账面（ragged row）驱动，非容量面**。
3. **ragged row 独立复现扫描（检测器同源函数）**：import `loop_runtime_claims._split_markdown_cells`（L515 实读源）+ 复刻 `_markdown_accounting` 表组判定逻辑（L659-682：表头/separator 识别 → 逐数据行 `len(cells) != len(headers)` 即 ragged），对 **工作树版本** 与 **git HEAD 版本**（`git show HEAD:docs/reviews/review-FIX-373-CODE-R0.md`）分别扫描：
   - **工作树：1 ragged row —— L114（headers 4 / cells 3）**
   - **git HEAD：1 ragged row —— 同一 L114**
   - L72（F-4 行，已改写「省略了「审计驱动任务」与「四层推进模型」间由竖线分隔的子串」）在 git 版与工作树版**均不构成 ragged**——code-span 内 `\|` 受 `_split_markdown_cells` 转义机制保护（L545-547：`\` 置 escaped → 下一字符字面追加），本就不触发折叠。
4. `loop_runtime_claims.py` L1435 实读：`materialize_loop_runtime_git_root(repository, git_ref, ...)`——**确认 Check 31 候选从 git 已提交内容 materialize**（修订摘要的机制描述属实）。
5. 治理数据实读：TRIAGE ×7 JSON 全在（REL-086/FEAT-064/063/044/045/FIX-384/385——glob 实证）；plan-tracker L108-113 六票热表行 + L302 roadmap 0.88.0 行；execution-packets.json L259 FEAT-064 包。
6. check-governance R1 完整输出存档于本席会话日志（含截断层 Check 19~28k：无新 FAIL）。

**只读声明**：未修改审查对象与 `.governance/` 任何文件；独立扫描脚本经 `python -c` 内联执行（临时 git show 快照落 `$env:TEMP`）；本报告为本席唯一输出文件。

---

## 1. 总结论

## **NEEDS_CHANGE**（unresolved_blockers=1）

- **逐条比对计数：已修复 12 / 未修复 1 / 新引入 0**（F-1~F-13 中 F-2 未修复；另登记新事实 N1——F-2 修复定位错误的证据链，归入 F-2 未修复判定，非规划文档新增缺陷）。
- **分级计数：P0=0 / P1=1（F-2 续）/ P2=0 / P3=0**（R0 的 12 项 P2/P3 全部消解；唯一残留为 F-2 的 P1 续行）。
- R0 三项 P1 中 F-1、F-3 已实证修复（命令复验）；**F-2 修复动作已执行但未命中根因**——真正 ragged row 是 **L114** 而非 L72，工作树与 git HEAD 双扫描一致；「工作树零 ragged row」的修复复现声明与实测不符（§3 N1）。Check 31 消解未达成：即使 commit 当前工作树，Check 31 仍将 BLOCKED。
- 修复路径明确且成本低（L114 措辞修正一处 + commit 后复跑），round=2 < fuse 3——R2 复审空间合法。

---

## 2. 逐条比对表（F-1~F-13 × 已修复/未修复）

| # | R0 发现 | 判定 | 复验证据（行号/命令实测） |
|---|---------|------|------------------------|
| **F-1** (P1) | Check 10 BLOCKING 未承载（A7 行 L30 触发 M5 误报） | ✅ **已修复** | 规划 v2 L30——A7 行已改叙述流「**切分器 backport 政策制度化（⑨ 定案——arch Q4）**：制度五件套——触发器（…变更时强制…）、快照清单（…逐项登记）、补丁台账（…）、双运行契约样例、隐性耦合检查（…）与可再生性（…）」，来源列改「定案裁决（⑨ backport 政策化）」——选项列表形态消除；**check-governance R1 实测 Check 10 PASS**（「No M5 anti-patterns in source files」；EXEMPT 20 条均在 FIX-295 白名单路径 docs/release+docs/reviews+docs/requirements，本文件零命中） |
| **F-2** (P1) | Check 31 BLOCKED 未承载（review-FIX-373-CODE-R0.md ragged table row） | ❌ **未修复（修复定位错误）** | 修复动作 = L72 改写（无管道表述）——**实测该行在 git 版与工作树版均不构成 ragged**（code-span 内 `\|` 受检测器转义保护，L545-547 机制实读）；**真正 ragged row = L114**（`| 2 | code-span 内 \`{[}/]\` 仍计 depth、\`\\\`\` 原样追加 | … | … |`——cell2 的 `` `\` `` code-span 自指转义：反斜杠转义掉自身闭合反引号 → code_delimiter 卡开 → 吞 cell2/cell3 管道边界 → 4 表头仅切 3 格），git HEAD 与工作树双扫描一致（同 L114、headers 4/cells 3）；check-governance R1 Check 31 仍 **BLOCKED**（2 FAIL + identity_verdict=FAIL + phase=staged_index）+ check-loop-runtime-claims verdict **BLOCKED**（semantic_units 306,179 ≤ 361,923——容量面非驱动项）。**消解未达成：commit 当前工作树后 Check 31 仍将 BLOCKED**（工作树 L114 在） |
| **F-3** (P1) | 发布链 M-1~M-8 映射与 M-1 bump 票缺位 | ✅ **已修复** | 规划 v2 新增 **§3b 发布链映射节**（L73-81）七条全落：M-1 bump 票（L75——随发布链启动时入账，0.87 FEAT-059 形态 + 输入清单含 static-pin 2 WARN 消解）/ M-1R 四件套（L76——18 票载荷 + M 链全表 + 四重点席回填位）/ M-2（L77——§3 全条目 + 28s 复测）/ M-3（L78——按阶段边界分节）/ M-5/M-7/M-8（L79——roadmap 0.88.0 行回填 + REL-086 终态回填 + 28s 消解复测）/ 回滚锚定原则 + B-12/B-13 显式化（L80）/ 规划落库（L81）。**Check 26 R1 实测 PASS**（R0 3 BLOCKING 消解——2 active/6 locks 一致）；TRIAGE-REL-086.json 机录（glob 实证）+ roadmap 0.88.0 行（plan-tracker L302——含 TRIAGE-×7 注记与 M-0 状态「Design ✅ R1 / Release R0 修复中」如实）。注记（非阻塞）：plan-tracker 热表无 REL-086 P 级任务行——入账形态 = TRIAGE 机录 + roadmap 行登记，Check 26 判定面已通过（与修订摘要「热表行」表述的差异如实记录） |
| **F-4** (P2) | 执行包 18c PASS 但 18d~g/i 契约全 placeholder，义务未登记 | ✅ **已修复（规划层义务承载）** | 规划 v2 §4 表后注记（L92）：「执行包契约义务（F-4 登记）」——18c 存在性 PASS / 18d-18g-18i 占位现状如实 + **派发时填充实质内容、M-2 门禁前全绿** + FEAT-064/062 派发前补建（含 D1 无包现状披露）；**FEAT-064 包已补**（execution-packets.json L259 实证）——**check-governance R1 Check 18c 实测 3 包 PASS**。18d/e/f R1 仍 FAIL（三票占位）= 义务时点内预期状态（派发填充 → M-2 前全绿），非缺陷 |
| **F-5** (P2) | §3.2 组合测试集宣告未兑现 | ✅ **已修复** | 规划 v2 §3.2（L68）「组合测试集清单（F-5 兑现）」四条落字：①guard 台账损坏→FEAT-060 恢复腿 × FEAT-061 切换窗口共存（崩溃注入交错）②BLOCK 激活后迁移路径全部走写入器（零手工写入）③write-guard 基线更新 × decision-append 投影失败恢复交互（B-12/B-13 回退联动）④closure 取消期 locks-release 与 guard 消费权并发（E 阶段票入账后并入）——R0 要求的最小清单达成，交互面覆盖三票交叉 + E 阶段并入时点明确 |
| **F-6** (P2) | Check 28s ERROR 未承载 | ✅ **已修复** | 规划 v2 §3b M-2 条（L77）：「evidence-log 归档后 28s 复测（F-6：现值 1,620KB，M-8 归档消解有效性在 M-2 复测确认——0.87 M-8 归档后仍 1620KB 的先例警示）」+ M-8 条（L79）「含 Check 28s 消解复测」；R1 实测 1,662,416B = 1623.5KB（1 ERROR，advisory fatal_on_error=false 不阻断）——0.87 §2 末行同型承载达成 |
| **F-7** (P2) | 六票未入账（阶段 D 全空 + FEAT-064 无包） | ✅ **已修复** | plan-tracker L108-113 六票热表行全在：FEAT-064（**P1**，TRIAGE-FEAT-064 机录 2026-09-24，D1，来源列引用「REVIEW-REL-086-RELEASE-R0 F-7」）/ FEAT-063（E2）/ FEAT-044（E3）/ FEAT-045（E4）/ FIX-384（E5）/ FIX-385（E6）；roadmap 0.88.0 行（L302）；TRIAGE ×7 JSON glob 实证；**Check 32 R1：records 169（R0 163）/ invalid 0 / without triage 0——PASS**；FEAT-064 执行包补建（execution-packets.json L259 + Check 18c 3 包 PASS）。阶段 D 不再空置 |
| **F-8** (P2) | Check 16/17 3 FAIL 仅隐含承载 | ✅ **已修复** | 规划 v2 §3.4（L70）：「**Check 16/17 EVD-476/473/423 3 FAIL = REQ-092 预期披露非豁免（F-8 显式登记——外部依赖零豁免红线内维持）**」——0.87 门禁摘要 #2 同型显式口径落字；R1 实测 3 FAIL 不变（EVD-476/473/423，豁免账本 30 条外）= 预期披露面 |
| **F-9** (P3) | §7「四阶段」计数失实 | ✅ **已修复** | 规划 v2 §7（L108）：「**18 票五阶段 + 1 项 M1.2 勘正（A4 改非票后）**全链单会话」；A4 改非票 M1.2 治理记录勘正（L27——原拟票 ID FEAT-001 与热表终态行冲突的实证留痕，设计半面 P2-1）；全文档口径一致（§3b L76「18 票载荷」/ §7 L110「18 票 + 1 项 M1.2 勘正」） |
| **F-10** (P3) | §3.4 未列 archguard 棘轮席 | ✅ **已修复** | 规划 v2 §3.4（L70）：「archguard 棘轮席（28o 基线 3 ERROR/26 WARN advisory——M-1R 门禁摘要显式列）」；R1 实测 28o 同基线（3 ERROR/26 WARN，advisory） |
| **F-11** (P3) | B-12/B-13 回退显式化建议 | ✅ **已修复** | 规划 v2 §3b 回滚锚定条（L80）：「B-12 族级 flag 回 WARN 经 D1 break-glass 通道（guard 自指场景下 break-glass 同样适用，不可静默）；B-13 反向转换方案为 C1⑦ 回退演练的**显式交付件**（非隐含承载）」——R0 F-11 两点建议全部落字 |
| **F-12** (P3) | 落库卫生三注记 | ✅ **已修复（义务承载）** | 规划 v2 §3b L81「规划文档落库：M-0 双审 GO 后 git add 入库（当前 untracked——F-12）」+ L75 M-1 输入清单含 static-pin 2 WARN 消解（test_verify_workflow.py:12550 派生化 + :12375 stale exemption 复审）；R1 实测 Check 25 WARN 4 untracked（规划 v2 + review-REL-086-DESIGN-R0/R1 + RELEASE-R0——M-0 落库批 git add 义务在案，预期状态）+ Check 24 同 2 WARN（M-1 消解输入已登记） |
| **F-13** (P3) | 风险窗裁决时点措辞 | ✅ **已修复** | 规划 v2 §7（L109）：「RISK-036/039/046 窗裁决 2026-09-30 **到期即裁决**（本版窗口内——当日完成 risk-log 裁决，不迟于 M-4；若 M-4 晚于 09-30，Check 8 自 10-01 转 FAIL〔现 PASS〕——F-13 口径修正）」；R1 实测 Check 8 PASS（无过期，4 open risks）——deadline 字段 R0 已实测（036/039/046 = 2026-09-30） |

---

## 3. 新引入问题

| # | 级别 | 问题 | 事实依据 |
|---|------|------|---------|
| **N1** | **P1**（归入 F-2 未修复判定；此处登记为修复过程新事实） | **F-2 修复定位错误 + 修复复现声明与实测不符**：①修复改写了 L72（F-4 行）——实测该行在 git HEAD 与工作树**均不构成 ragged**（code-span 内 `\|` 受 `_split_markdown_cells` 转义保护——L545-547 机制：`\` 置 escaped 后下一字符字面追加，管道不被切分、闭合反引号不受影响），改写对该行虽无害（语义等价）但**不产生消解效果**；②真正 ragged row = **L114**（`{[}/]` 后的 `` `\` `` code-span 自指转义——反斜杠转义掉自身的闭合反引号 → code_delimiter 卡开 → 吞 cell2/cell3 边界 → headers 4/cells 3），git 与工作树双扫描一致，**未被告修复**；③修订摘要声称「用检测器自身切分函数复现扫描全文所有表组——工作树版本零 ragged row」——与本席同函数（`_split_markdown_cells` 直接 import）+ 同表组逻辑（L659-682 复刻）的独立扫描结果（1 ragged row @ L114）**不符**；④「check-loop-runtime-claims 仍报 BLOCKED 因其从 git root source materialize——修复已落盘未 commit」的归因**不成立为消解依据**：工作树 L114 仍在，commit 后 Check 31 仍将 BLOCKED（materialize 机制属实——L1435 `materialize_loop_runtime_git_root` 实读确认，但机制正确不等于修复完备）。处置建议：修 L114 措辞（`` `\` `` 改文字化表述如「反斜杠字符原样追加」，或调整 cell 内 code-span 形态使反引号配对）→ commit → 复跑 check-loop-runtime-claims 确认 verdict 非 BLOCKED；修复者的复现扫描方法需复核（疑因 fast-path 分支差异或扫描范围不全漏检 L114） | 工作树/git HEAD 双扫描（`_split_markdown_cells` import 实测）：各 1 ragged row @ L114（headers 4/cells 3，行首「\| 2 \| code-span 内 `{[}/]` 仍计 depth、`\` 原样追加…」）；check-governance R1 Check 31 BLOCKED（inventory `c1345ca9…`）；check-loop-runtime-claims verdict BLOCKED / semantic_units 306,179 |

其余观察（注记级，不构成发现）：Check 31 候选 951→954（+3，治理记录增长）；28s 1620.6→1623.5KB（同前因）；Check 30 sequences 394→395（REL-086 R0 入链）；Check 25 untracked 1→4（规划 v2 + 三份 REL-086 审查报告——M-0 落库批义务面）。

---

## 4. 硬门槛自检

| 门槛项 | 判定 |
|--------|------|
| 逐条比对前轮 findings（已修复/未修复/新引入标注） | **PASS**（§2 全表 13 行 + §3 N1） |
| 报告头部声明 round 号 + 前轮引用 | **PASS**（R1 + REVIEW-REL-086-R0-RELEASE 路径） |
| round ≥ 3 时 BLOCKING 熔断 | 不适用（round=2 < fuse 3——R2 复审空间合法） |
| 「已修复」判定核验实质（命令复验或行号引用） | **PASS**（每行附 check-governance/扫描实测或 v2 行号） |
| 只读审查对象与 .governance/ | **PASS**（独立扫描经 python -c 只读执行，git 快照落 TEMP） |
| 唯一输出文件 = 本 R1 报告 | **PASS** |
| 未实际运行项如实标注 | **PASS**（§0 边界：pytest 未运行〔M-2 义务〕；semantic_units 为当场实测值） |

---

## 5. R2 复审清单（最小闭环）

1. **F-2/N1**：review-FIX-373-CODE-R0.md **L114** 措辞修正落地（`` `\` `` 自指转义消除——文字化或反引号配对）→ **M-0 落库 commit** → 复跑 `check-loop-runtime-claims` 确认 verdict 非 BLOCKED（R2 必查——同时覆盖 git materialize 面与工作树面）。L72 改写保留（无害）。
2. 规划文档无需再动（F-1/F-3~F-13 全部闭环；F-2 的规划侧承载——§3.4 L70 既有面 + §3b L76 M-1R checklist 回填位「Check 31 修复验证」——已在 v2 落字，R2 无规划面动作）。
3. R2 复审范围收窄为单项核验（Check 31 消解 + 无回归面抽查：Check 10/26 维持 PASS）。

---

*REL-086 发布半面 R1 复审冻结（2026-09-24，Release Reviewer Agent——M7.4 T1 同席复审）。证据基线：check-governance 全量实测（exit 0，45 issues，2026-09-24）+ check-loop-runtime-claims 实测（semantic_units 306,179 / verdict BLOCKED）+ ragged row 独立复现扫描（`_split_markdown_cells` import，工作树 + git HEAD 双版本，各 1 ragged row @ L114）+ `materialize_loop_runtime_git_root` 机制实读（L1435）+ 规划 v2 全文逐行 + plan-tracker/execution-packets/change-triage 治理数据实读。前轮引用：docs/reviews/review-REL-086-RELEASE-R0.md。本报告为审查席独立结论，发布 GO/NO-GO 决策权在 Coordinator/用户。*
