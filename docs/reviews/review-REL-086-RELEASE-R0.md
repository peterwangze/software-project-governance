# REL-086 发布半面独立审查报告（RELEASE · R0）

> **Round**: R0（初审，无前轮引用）
> **Task**: REL-086 — 0.88.0 版本规划草案 v1（M-0，DEC-229 预授权）发布半面独立审查
> **Reviewer**: Release Reviewer Agent（独立审查席，只读）
> **审查对象**: `docs/planning/version-plan-0.88.0.md`（草案 v1，Coordinator 起草 2026-09-23，全文 103 行逐行读取）
> **对照先例**: `docs/planning/version-plan-0.87.0.md`（M-0 双审先例）、`docs/release/release-plan-0.87.0.md`（M-1R 四件套先例）、0.87 发布链（REL-084/REL-085，tag v0.87.0 已发布）
> **日期**: 2026-09-24

---

## 0. 审查方法与证据边界

**实测命令（本席实际执行）**：
1. `verify_workflow.py check-governance`（全量，exit 0）→ **Result: ISSUES FOUND — 44 issue(s)**；关键面：Check 10 BLOCKING×1、Check 16/17 各 3 FAIL、Check 18d/18e/18f/18g/18i FAIL（FEAT-060/061 placeholder）、Check 26 BLOCKING×3（REL-086 未入账）、Check 28s ERROR×1、Check 31 BLOCKED（2 FAIL）、Check 8/11/12/37 等 PASS。完整输出已存档于本席会话日志。
2. `verify_workflow.py check-loop-runtime-claims` → `"semantic_units": 305604`、`"verdict": "BLOCKED"`（容量 305,604 ≤ 361,923——BLOCKED 非 SEMANTIC_BUDGET_EXCEEDED 驱动，与 Check 31 的 accounting/identity FAIL 一致）。
3. `Get-Item .governance/evidence-log.md` → **1,659,471 bytes = 1620.6 KB**（与 Check 28s ERROR 数值一致）。
4. `.governance/risk-log.md` RISK-036/039/046/050 行 deadline 字段逐条提取：036/039/046 = **2026-09-30**，050 = **2026-10-31（打开）**。
5. `loop_runtime_claims.py` L225-243 实读：`max_semantic_units: int = 361923`（L243）；provenance 注释 `ceil(301602 x 1.2) = ceil(361922.4) = 361923`（L236）；测试钉 `test_loop_runtime_claims.py` L1898-1899 双断言同值——**§3.4「361,923 复算」钉值核实成立**。
6. `.governance/execution-packets.json` 实读：FEAT-060（L5）、FEAT-061（L132）存在；**FEAT-064 无条目**。
7. `.governance/plan-tracker.md` 逐行检索：0.88 已入账活跃行 = FIX-375/376/377/379/380/381/382/386（阶段 A1~A8）+ FEAT-060（B1，P1）+ FIX-383（B2）+ FEAT-061（C1，P1）+ FEAT-062（E1）共 **12 行**；**FEAT-064 / FEAT-063 / FIX-384 / FIX-385 无任何任务行**，FEAT-044/045 仅有候选池行（L360-361）；**无 0.88.0 roadmap 行**；REL-086 无任务行（Check 26 实证）。
8. `.governance/decision-log.md` L171 DEC-229 实读：引用原文与规划 L5 一致；裁定②「0.88.0 目标版本——M-1~M-8 标准链」；FIX-376 空票约束（P1）——规划 §2 A2（L24）已赋予具体范围（机录范围为准），**该约束已兑现**。

**以读代跑边界**：全量 pytest 未运行（M-0 阶段无此义务——§3.1 将其定为 M-2 义务，本审查仅审口径）；Check 31 ragged row 的确切行位未逐行复现（失败为文件级定位，机理推断见 F-2）；`语义单位 305,604` 为实测当场值（会随治理写入漂移，M-2 复算为准）。

**只读声明**：未修改 `docs/planning/version-plan-0.88.0.md`；未修改 `.governance/` 任何治理记录；本报告为本席唯一输出文件（文件锁 `review-REL-086-RELEASE-R0.md` locked_by REL-086，Check 26 实证在锁）。

---

## 1. 总结论

## **NEEDS_CHANGE**（unresolved_blockers=3）

- **分级计数：P0=0 / P1=3 / P2=5 / P3=5。**
- 规划主体质量高：范围授权链（DEC-229）实测一致、五阶段排布符合 arch 修正案、门禁口径五大面中三项（pytest 预算语义/独立证明包/REQ-092 红线）完备且 LRC 钉值可复算、行为变更面 B-12/B-13/B-14 回退路径可操作。
- **但**：①规划文档自身触发 Check 10 BLOCKING 且未承载处置路径；②Check 31 当前 BLOCKED（文档记账面）未被 §3 承载——性质不同于 0.87 的容量重定标，不能引用「0.87 先例口径」覆盖；③发布链 M-1~M-8 映射与 M-1 bump 票在规划中完全缺位（0.87 M-0 §4 显式先例）。三项均为 P1，修复成本低（措辞修正/补票/补节），但按 0.87 先例（M-0 即须承载当期 FAIL 面——version-plan-0.87.0 §3 对 Check 31/16-17/28s 逐项落处置）MUST 在规划层补齐后方可 M-0 GO。
- NEEDS_CHANGE 非终态：Coordinator 返工（规划 v2 修订或补票）后须重 spawn 本席复审（R1）；本报告 §6 列 R1 复审清单。

---

## 2. 分级发现列表

### P1（unresolved_blockers，3 项）

| # | 发现 | 规划文档引用 | 事实依据 |
|---|------|------------|---------|
| **F-1** | **Check 10 BLOCKING 由规划文档自身触发，规划未承载处置路径**。A7 行（L30）叙述触发 M5 误报（选项列表形态 + 决策语境无 AskUserQuestion——M5.1 反模式判定）；`docs/planning` 不在 FIX-295 record-doc 白名单（实测白名单 = docs/release + docs/reviews + docs/requirements，该三路径 19 条同类 issue 均已 EXEMPT，本文件独 BLOCKING）。M-2 check-governance 将复现 1 BLOCKING。规划 §3（L65-71）与 §7（L93-98）均无此面处置。 | `version-plan-0.88.0.md:30`（A7 行） | check-governance 实测：`[BLOCKING] 1 M5 anti-pattern(s) — docs/planning/version-plan-0.88.0.md:30 \| A7 \| FIX-381 \| **切分器 backport 政策制度化（⑨ 定案——arch Q4）**…Fix: Option list detected with choice context but no AskUserQuestion`；`[EXEMPT] 19 record-doc M5 issue(s) — FIX-295 path whitelist docs/release, docs/reviews, docs/requirements`。0.87 对照：version-plan-0.87.0 无 docs/planning 路径触发面（0.87 深检 45 issues 中无 Check 10 BLOCKING 记录）。处置建议（Coordinator 裁决）：(a) A7 行措辞去选项列表形态（最小改动，规划 v2 内完成）；或 (b) 立票扩 FIX-295 白名单至 docs/planning（附理由：版本规划同属 record text 非 agent instructions——与 19 条 EXEMPT 同型） |
| **F-2** | **Check 31 当前 BLOCKED 未被规划承载，且与 0.87 失败源不同**。两条 FAIL：`ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY: docs/reviews/review-FIX-373-CODE-R0.md ragged table row` + `IDENTITY_ATTESTATION_FAIL`（identity_verdict=FAIL; phase=staged_index）。这是**文档记账面**失败，非容量面——实测 semantic_units 305,604 ≤ 361,923（余量 56,319，无 SEMANTIC_BUDGET_EXCEEDED）。规划 §3.4（L70）「既有面……0.87 先例口径」不能覆盖：0.87 的 Check 31 FAIL 是容量超限（300,701>300,000→FIX-369 重定标），本次是 ragged table row 导致的记账/身份验证失败，**重定标不解决**。M-2 复现 BLOCKED。0.87 先例：M-0 对当期 Check 31 FAIL 立票 FIX-369 + §3.1 五标准方案对照（version-plan-0.87.0 L20/L30-42）——本版零承载。 | 规划无对应条目（§3 L65-71 缺 Check 31 处置） | check-governance Check 31 实测原文（Verdict: BLOCKED; Candidates: 951; parsed: 951; Inventory: 233ccbf2d86e1d56…）；机理推断（未逐行复现，标为推断）：review-FIX-373-CODE-R0.md §2 表格（L38-43）含 quote/backtick 高密度 code-span cell，失败机理与该报告自述的切分器残留场景 2（code-span 行尾不闭合折叠后续管道——F-3/F-2 观察项）一致；确切行位由修复票定位。处置建议：立票修复该审查报告 ragged row（历史审查记录修订——修复方式 Coordinator 裁决：格式修订留痕 or 处置票披露），M-2 前落地 |
| **F-3** | **发布链 M-1~M-8 映射与 M-1 bump 票在规划中缺位**。§2（L17-63）仅承载阶段 A~E 工程票（19 票），无 M-1 bump 票（0.87 先例 FEAT-059：全仓 bump + CHANGELOG 段 + 投影再生——release-plan-0.87.0 L47）、无 M-1R 四件套票（REL-085 先例）、无 M-2~M-8 标准链映射节、无 M-8 归档义务行、无 roadmap 0.88.0 行回填义务、无回滚区间锚定原则预声明。0.87 M-0 先例**全部显式在文**：§4「M-1: 版本 bump 0.86.0→0.87.0 + CHANGELOG 0.87.0 段 + 投影再生…」「M-2~M-8: 标准链（门禁实测→双半面审查→transition→tag→推送→ledger→归档+快照）」（version-plan-0.87.0 L61-62）+ M-1R 演练腿裁决义务（L63）+ M-5/M-8 回填义务（L64）+ §2 末行「Check 28s 由 M-8 归档迁移消解——不占工程票」（L24）+ §8 回滚预案（L81-83）。DEC-229 裁定②已授权「M-1~M-8 标准链」（decision-log L171 实测）——**授权面完备，规划落字面缺失**。 | `version-plan-0.88.0.md:17-63`（§2 全节）、§7 L96（「19 票四阶段全链单会话」——仅工程票视角） | plan-tracker 实测：无 0.88.0 roadmap 行；REL-086 无任务行（Check 26 BLOCKING×3：active_tasks['REL-086'] + 2 file locks 均未入账）；无 M-1 bump 候选票（0.88 票族 FIX-375~386/FEAT-060~064 中无 bump 票）。处置建议：规划 v2 补「§4 发布链排布」节（M-1 bump 票入账 + M-1R 四件套义务 + M-2~M-8 标准链映射 + M-8 归档义务行〔顺带承载 F-6〕+ roadmap 回填义务）+ Coordinator 补 REL-086 任务行入账（消 Check 26） |

### P2（5 项）

| # | 发现 | 规划文档引用 | 事实依据 |
|---|------|------------|---------|
| **F-4** | **FEAT-060/061 执行包：Check 18c 复验 PASS，但 18d/18e/18f/18g/18i 契约字段全 placeholder（10 FAIL 行）**。任务上下文「2026-09-24 已由 execution-packet --write 补齐，需复验」的复验结论：**补齐的是包存在性（18c PASS），非契约内容**——product_success_contract / acceptance_contract / quality_budget / vertical_slice / assumption_record 全部 TO_BE_DEFINED 占位（execution-packets.json L11/L12/L28/L41~L76/L85/L132 实读）。quality_budget 允许 NOT_RUN_YET 但字段须具体非占位。规划 §4 事实填充项（L73-80）未含「派发前补齐执行包契约」义务。 | `version-plan-0.88.0.md:73-80`（§4） | check-governance 实测：18c `[PASS] FEAT-060/061: execution packet ready`；18d `[FAIL] FEAT-060/061: product_success_contract.user must be specific and non-placeholder…`（六字段）；18e `[FAIL] …acceptance_contract…`（七字段）；18f `[FAIL] …quality_budget…`（六维）；18g `[FAIL] …vertical_slice…`（六字段）；18i `[FAIL] …assumption_record…`（五字段）。处置：FEAT-060/061 派发时由 Coordinator/Developer 填充契约（M-2 前须全绿）——建议规划 §4 增第⑤项或在票验收面登记 |
| **F-5** | **§3.2 组合测试义务「M-0 预指定组合测试集」宣告未兑现**——声称预指定，全文未列任何具体测试集/场景清单（FEAT-060×061×064 交互面如：guard 台账×存储切换期写入、BLOCK 激活×决策记录迁移、消费权台账×投影失败语义）。义务声明与内容落差，「禁全量不得退化为只测单票」的执行抓手缺位。 | `version-plan-0.88.0.md:68` | 规划 L68 原文：`跨票边界（FEAT-060×FEAT-061×FEAT-064 三者交互面）M-0 预指定组合测试集——「禁全量」不得退化为「只测单票」`——§2~§8 无任何测试集枚举。处置：规划 v2 或三票验收面补最小组合测试集清单（可后置于票内，但 M-0 宣告与内容须一致） |
| **F-6** | **Check 28s ERROR 未承载**：evidence-log.md 实测 1,659,471B（1620.6 KB）= Check 28s 1 ERROR（advisory, fatal_on_error=false）。0.87 先例在 M-0 §2 末行显式承载「Check 28s（1,593.5KB 超限）由 M-8 归档迁移消解——不占工程票」（version-plan-0.87.0 L24）+ §3.3 复测义务（L48）。本规划无对应行；「随 M-8 归档瘦身」口径仅存在于会话记忆面，未落规划文本。**且注意**：0.87 M-8 已执行归档（release_forced 归档 integrity PASS——plan-tracker L11）后 evidence-log 仍达 1620.6KB——归档消解有效性存疑或增量抵消，M-8 瘦身路径需 M-2 复测确认有效。 | `version-plan-0.88.0.md:65-71`（§3.4 缺项）、§7 L98（仅 LRC 面） | check-governance Check 28s 实测：`[ERROR] .governance/evidence-log.md 1659471 bytes (1620.6 KB)`（advisory）；Get-Item 实测同值。处置：规划 v2 补 M-8 归档义务行（0.87 同型），并登记「归档后复测阈值口径」 |
| **F-7** | **6 票未在 plan-tracker 入账 + 阶段 D 全空**：D1 FEAT-064（本版执法激活核心票——B-12 行为变更载体）+ E2 FEAT-063 + E3 FEAT-044 + E4 FEAT-045 + E5 FIX-384 + E6 FIX-385 无活跃任务行；FEAT-064 且无执行包（execution-packets.json 无条目；Check 18c required=2 与 FEAT-060/061 一致，FEAT-064 未计入——其尚未活跃）。FEAT-044/045 仅有候选池行（plan-tracker L360-361）。0.87 先例：M-0 时点全部票 triage 机录 + 任务行落账并设「批 1 开工前置门」（version-plan-0.87.0 L26/L56）。本规划无入账状态注。附：A4 FEAT-001（L27）属治理记录数据修正（task-row-update 面——deps 列自环消除），非派发票，不受此限。 | `version-plan-0.88.0.md:50`（D1）、L57-61（E2~E6） | plan-tracker 逐行检索实测（见 §0 第 7 条）；DEC-229① 授权「全部已登记项一次性推进闭环」——未登记项不在授权闭环内，入账是派发前置。处置：阶段 D/E 派发前完成 triage 机录 + 任务行 + （P0/P1 者执行包）；不要求 M-0 时点全量入账（阶段化排布下后段票可后置），但规划宜登记入账时点纪律 |
| **F-8** | **Check 16/17 3 FAIL（EVD-476/473/423）仅隐含承载，建议显式登记预期披露口径**。实测两 Check 各 3 FAIL：REQ-092 行缺 `目标对齐:`（EVD-476/473/423）与缺 `用户影响:` 字段——historical exempted 30 条不含此三行（FIX-371/DEC-227 豁免账本外）。规划 §3.5「REQ-092 披露面维持（外部依赖零豁免红线——非本版范围）」（L71）覆盖语义但未显式写「3 FAIL = M-2 预期披露非豁免」。0.87 同面显式登记（release-plan-0.87.0 门禁摘要 #2：「真实面 3 FAIL 姿态（31→5→3——REQ-092 blocked 维持 FAIL = 预期披露非豁免）」L100）。 | `version-plan-0.88.0.md:71`（§3.5） | check-governance Check 16/17 实测各 3 FAIL（行号引用见 §0 第 1 条）；evidence-log EVD-476（L551）/EVD-473（L574）/EVD-423（L1127）实读确认缺字段。处置：M-1R 四件套门禁摘要显式登记（0.87 同型）；规划层可仅注记引用 |

### P3（5 项）

| # | 发现 | 规划文档引用 | 事实依据 |
|---|------|------------|---------|
| **F-9** | §7「19 票**四阶段**全链单会话」计数失实——§2 定义**五**阶段（A 契约与卫生/B 恢复与执法基础/C 单点存储切换/D 执法激活/E 能力与剩余，L19/33/40/46/52）。票数 19 核对无误（A9+B2+C1+D1+E6）。 | `version-plan-0.88.0.md:96` vs §2 | 规划文本逐节核对 |
| **F-10** | §3.4 既有面未列 archguard 棘轮席（0.87 M-1R 门禁摘要 #4 有「棘轮 R1~R7 R5 期望 96/96 frozen」席位——release-plan-0.87.0 L102）；当前 Check 28o 实测 3 ERROR / 26 WARN（advisory 不阻断）。0.88 大票（FEAT-060/061/064 存储与执法面）落地后棘轮不越线需 M-2 实测——建议 M-1R 门禁摘要显式列席。 | `version-plan-0.88.0.md:70` | check-governance Check 28o 实测 |
| **F-11** | B-12/B-13 回退路径可操作但建议显式化两处：①B-12「族级 flag 回 WARN（数据级）」未引用 D1 break-glass——若 flag 翻转动作本身被 BLOCK 拦截（guard 自指），恢复须走 break-glass（D1 L50 已定义「限定对象/操作者/理由/有效期/次数 + 不可静默记录」，承载面存在）；②B-13 反向转换的交付面经 C1⑦「回退演练覆盖迁移后新增 DEC」（L44）**隐含**承载——建议 C1 验收显式列「反向转换为交付件而非仅演练项」。B-13「仅备份不算可回滚」口径本身正确且必要（见 §3 关注面 2 判定）。 | `version-plan-0.88.0.md:84-85` | 规划文本 + D1/C1 交叉比对 |
| **F-12** | 发布面卫生三注记（M-1 bump 输入清单）：①规划文档未入库（Check 25 WARN：version-plan-0.88.0.md untracked——M-0 落库批须 git add）；②Check 24 static-version-pin 2 WARN：test_verify_workflow.py:12550 pin「0.87.0」字面量 + :12375 stale exemption——M-1 bump 至 0.88.0 时须处置（derive 化或 STATIC_PIN_EXEMPTIONS 勘正）；③Check 35 WARN：session-snapshot 2026-09-23 早于治理文件末次修改 2026-09-24（fail-safe WARN——session 收口时更新）。 | `version-plan-0.88.0.md:3`（草案状态） | check-governance Check 24/25/35 实测 |
| **F-13** | §7 风险窗裁决措辞时点歧义：「RISK-036/039/046 窗裁决 2026-09-30 到期（本版窗口内）——M-4 前处理」（L97）——若 M-4 晚于 2026-09-30，Check 8 自 10-01 起转 FAIL（实测 Check 8 现为 PASS：无过期，4 open risks）。建议明确「2026-09-30 到期即裁决」（裁决 = risk-log 记录更新，非工程票，随时可执行），而非绑定 M-4 时点。 | `version-plan-0.88.0.md:97` | risk-log deadline 实测（036/039/046 = 2026-09-30）+ Check 8 PASS 现状 |

---

## 3. 关注面逐项判定（任务指定五面）

### 关注面 1：门禁口径完备性（§3 L65-71）

| 子项 | 判定 | 依据 |
|------|------|------|
| 全量 pytest M-2 一次预算语义 | **PASS** | §3.1（L67）三要素齐：①「全量只在 M-2」= 正常路径预算非免检许可；②M-3 修改可执行代码 → 原 M-2 证据不自动覆盖须退回验证评估；③最终门禁绑定实际发布提交。语义正确无漏洞 |
| 跨票组合测试义务 FEAT-060×061×064 | **PASS（口径）／FAIL（兑现）→ F-5 P2** | §3.2（L68）义务声明在，「M-0 预指定组合测试集」但全文无测试集内容——宣告与内容落差 |
| FEAT-061 独立证明包必查席 | **PASS** | §3.3（L69）五要素齐：固定源 commit 摘要/记录级比对/故障注入/回退演练含迁移后新增行/绑定发布提交，定为 M-2 必查席；与 §1 对冲交付物（L15）和 C1⑦（L44）三处一致 |
| LRC 预算 361,923 复算 | **PASS（钉值核实）／M-2 义务在** | §3.4（L70）+ §7（L98）双登记；钉值实测：`loop_runtime_claims.py` L243 `max_semantic_units=361923`、L236 公式注释、测试 L1898-1899 双钉；当前实测 305,604（余量 56,319）；M-2 复算 + 越线按 FIX-369 公式重定标（非豁免）口径正确 |
| REQ-092 披露面维持 | **PASS（红线）／F-8 P2（3 FAIL 显式化）** | §3.5（L71）零豁免红线明确；Check 16/17 实测 3 FAIL 为账本外既有披露面，建议 M-1R 显式登记预期口径 |
| **本面总缺口** | **F-1/F-2 P1** | §3 未承载 Check 10 BLOCKING 与 Check 31 BLOCKED（当前 44 issues 中仅有的两个 BLOCKING/BLOCKED 级门禁面）——0.87 M-0 先例对当期 FAIL 面逐项落处置（§3.1 方案对照 / §3.2 FIX-371 承载 / §3.3 M-8 归档），本版缺同型承载 |

### 关注面 2：行为变更登记完备性（§5 L82-87）

| 子项 | 判定 | 依据 |
|------|------|------|
| B-12 write-guard BLOCK 激活（L84） | **回退可操作 ✓（附 P3 建议）** | 回退 = 族级 flag 回 WARN（数据级）——guard 激活态为数据面 flag，回 WARN 后持续记录语义保留（WARN 不改基线，FEAT-060 六规则承载）；guard 自指场景（flag 翻转被 BLOCK 拦截）由 D1 break-glass 承载（L50：限定对象/操作者/理由/有效期/次数 + 不可静默记录）——建议 B-12 回退路径显式引用 break-glass（F-11①）。启用顺序由合法写路径覆盖率裁定（L50）——与 §4 事实填充项③（L79「写前/写后语义如实入票」）衔接，无 overclaim |
| B-13 decision-log JSON 权威化（L85） | **回退可操作 ✓（附 P3 建议）** | **「仅备份不算可回滚——须覆盖迁移后新增行的反向转换」口径明确且正确**——切前快照只覆盖切前状态，迁移后新增 DEC 只能靠反向转换恢复，该口径堵住了 0.87 前各版「快照=可回滚」的隐含误读。承载链：C1⑦ 独立证明包（L44）回退演练覆盖迁移后新增 DEC = 反向转换被演练验证——可操作；建议反向转换交付件显式化（F-11②）。外部 CLI 契约零变化 + 旧工具对新格式明确拒绝（非静默误读）——fail-safe 完整 |
| B-14 closure 取消/重开/接管（L86） | **回退可操作 ✓** | 纯新增能力面无删除——回退 = 不激活即回退，无数据迁移面；E1/E2 验收（L56-57）含幂等重放/竞争单终态/中断恢复等七场景，新增面风险受控 |
| skill/注入面（L87） | **登记姿态正确** | 「随 FEAT-044/045 落地时按实际面登记」——M-0 阶段不预编造，符合事实依据红线 |

### 关注面 3：已知 M-2 前置 FAIL 面处置路径（逐项）

| FAIL 面 | 实测现状 | 规划承载 | 判定 |
|---------|---------|---------|------|
| Check 10 BLOCKING（version-plan-0.88.0.md:30，A7 行 M5 误报——docs/planning 不在 FIX-295 白名单 docs/release+docs/reviews+docs/requirements） | **实测在案**（1 BLOCKING；白名单三路径 19 条 EXEMPT） | **无** | **需补票/措辞修正**（F-1 P1）——处置二选一：(a) A7 行措辞去选项列表形态（规划 v2 内最小改动）；(b) 立票扩白名单至 docs/planning（record text 同型理由） |
| Check 31 两条（review-FIX-373-CODE-R0.md ragged table row → ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY + IDENTITY_ATTESTATION_FAIL） | **实测 BLOCKED**（identity_verdict=FAIL; phase=staged_index；容量面 PASS——305,604≤361,923） | **无**（§3.4「0.87 先例口径」不覆盖——0.87 为容量面，本次为文档记账面） | **需补票**（F-2 P1）——修复 ragged row（历史审查记录修订，方式 Coordinator 裁决）或登记披露处置；0.87 先例 = M-0 即立票（FIX-369）+ §3.1 方案对照 |
| Check 16/17 三条（EVD-476/473/423 缺目标对齐/用户影响） | **实测各 3 FAIL**（豁免账本 30 条外） | **隐含**（§3.5 REQ-092 零豁免红线 L71） | **口径可接受，建议显式化**（F-8 P2）——M-1R 门禁摘要按 0.87 同型显式登记「3 FAIL = 预期披露非豁免」 |
| Check 28s（evidence-log 1620KB） | **实测 1 ERROR**（1620.6KB，advisory） | **无**（「随 M-8 归档瘦身」仅存会话记忆面未落规划文本） | **需补登记**（F-6 P2）——规划补 M-8 归档义务行（0.87 §2 末行同型）+ 归档有效性复测义务（0.87 归档后仍 1620KB——消解有效性存疑） |
| Check 18c~18i（FEAT-060/061 执行包） | **实测：18c PASS（包就绪）；18d/18e/18f/18g/18i 全 FAIL（placeholder）；18h PASS** | **无**（§4 事实填充项未含契约补齐义务） | **复验结论：存在性已补齐、契约内容未补齐**（F-4 P2）——派发时填充，M-2 前须全绿；建议 §4 增列义务 |

### 关注面 4：发布链完整性（§2 阶段与 M-1~M-8 映射）

**判定：不完整（F-3 P1）。** 逐项：
- **M-1 版本 bump 票尚未入账——需要随发布链补入**。19 票全为工程票，无 bump 票；0.87 先例 M-1 bump 票 FEAT-059（bump 24 tracked 面 + CHANGELOG 段 + 投影再生正道首活体）在 M-0 规划 §4 显式列步（version-plan-0.87.0 L61）、载荷表显式列票（release-plan-0.87.0 L47）。DEC-229② 授权「M-1~M-8 标准链」（decision-log L171）——授权面有、规划面无。
- M-1R 四件套义务无承载（REL-085 先例：plan/checklist/rollback/feature-flags + M-2 回填位预留）。
- M-2~M-8 标准链映射节缺失（0.87 §4 L62 先例）；M-5/M-8 roadmap 回填义务缺失（0.87 R0-DESIGN-F8 先例 L64）；M-8 归档义务行缺失（0.87 §2 L24 先例——顺带承载 F-6）；回滚区间锚定原则预声明缺失（0.87 §8 L81-83 先例：下界含 M-1 bump 完整 diff、终点 = 发布 tip、M-1R 起草义务）。
- REL-086 本身未入账（Check 26 BLOCKING×3）+ 无 0.88.0 roadmap 行——M-0 落库批义务（0.87 先例：REL-084 落库批含 roadmap 行 + 审查报告留档）。
- 现有 tag 基线健康：Check 37 PASS（latest tag v0.87.0；lineage mode: candidate）——链起点无障碍。

### 关注面 5：风险登记处置（§7 L93-98）

| 子项 | 判定 | 依据 |
|------|------|------|
| RISK-036/039/046 窗裁决 2026-09-30 | **承载 ✓ 可执行 ✓（附 P3 措辞建议）** | risk-log deadline 实测三行均 2026-09-30（L39/40/42）；规划 §7 L97「M-4 前处理（risk-log 裁决，非工程票）」——裁决为治理记录更新无需工程票，窗口内（今 2026-09-24 → 09-30）可执行；Check 8 现为 PASS（无过期，4 open risks）。建议改「到期即裁决」措辞（F-13——若 M-4 晚于 09-30，Check 8 将先转 FAIL） |
| RISK-050 维持打开 | **一致 ✓** | risk-log 实测 deadline 2026-10-31、状态「打开」（L44）；规划 L97「RISK-050（10-31）维持打开」——一致 |
| LRC 增量预算 | **承载 ✓** | §7 L98：本版治理记录增量可观（19 票 TRIAGE/EVD/REVIEW 机录）——M-2 复算 + 越线按 FIX-369 公式口径重定标（非豁免）；当前 305,604 实测（余量 56,319）——19 票机录增量是否越线由 M-2 实测裁决，口径完备 |
| 假绿复合风险（首位风险） | **对冲结构完整 ✓** | §1 对冲交付物（L15）+ §3.2/3.3 组合测试与证明包门 + §7 L95 缓解 = M-3 双半面按阶段边界分节审查——arch 总体提醒的三处落地在文（附 F-5 组合测试集内容缺口的减损项） |

---

## 4. 硬门槛自检

| 门槛项 | 判定 |
|--------|------|
| 每项发现引用规划文档行号/原文或命令实测输出 | **PASS**（§2 表格逐项 + §0 实测清单） |
| 只读审查对象——未修改 version-plan-0.88.0.md | **PASS** |
| 未修改 .governance/ 治理记录 | **PASS**（状态翻转/入账留 Coordinator 机录） |
| 未运行发布门禁类写操作、无 tag/push/transition | **PASS** |
| 报告写入指定路径 docs/reviews/review-REL-086-RELEASE-R0.md（唯一输出文件） | **PASS** |
| 结论四选一 + unresolved_blockers 计数 + 分级发现计数 | **PASS**（NEEDS_CHANGE / 3 / P0=0 P1=3 P2=5 P3=5） |
| 未做 GO/NO-GO 最终决策（留 Coordinator/用户） | **PASS**（本报告仅审查结论；「发布 GO/NO-GO 决策由 Coordinator/用户承载」） |
| 事实依据红线（未实际运行项标未验证/推断） | **PASS**（§0 以读代跑边界：pytest 未运行如实标注；ragged row 行位标推断；语义单位为当场实测值会漂移） |

---

## 5. 正面确认（复审无需重验的面）

1. **授权链**：DEC-229 实测一致（decision-log L171——引用原文、三项裁定、FIX-376 空票约束已由 §2 A2 L24 范围赋予兑现）。
2. **arch 协作记录**：§8（L100-103）三次尝试如实记录（两失败一成功）、成功轮意见全量消化映射可追溯（批次重排→§2、⑨→A7、guard 状态机→B1、存储→C1、取消纵切→E1、⑩拆票→B2/E5/E6、假绿对冲→§1/§3、截断优先序→§2 注）。
3. **截断优先序**（L63）：「不得把候选池已登记改写成候选池已闭环」+ 接续包纪律——容量风险对冲正确。
4. **Check 11/12/13/27/37** 等结构面 PASS（manifest 852 一致、交叉引用干净、ID 序列干净、归档完整、发布 Gate 序列 PASS）。
5. **LRC 钉值与公式**：361,923 = ceil(301,602×1.2) 代码/测试/provenance 三面一致。

---

## 6. R1 复审清单（Coordinator 返工后复审必达）

1. **F-1**：A7 行措辞或 FIX-295 白名单处置落地 → R1 复跑 check-governance 确认 Check 10 无 BLOCKING（或 EXEMPT 披露）。
2. **F-2**：review-FIX-373-CODE-R0.md ragged row 处置落地 → R1 确认 Check 31 verdict 不再 BLOCKED（或披露口径入账）。
3. **F-3**：规划 v2 含发布链节（M-1 bump 票/M-1R 义务/M-2~M-8 映射/M-8 归档义务/回滚锚定原则）+ REL-086 入账 + roadmap 行 → R1 逐项对照 0.87 §4 先例核验。
4. **F-4/F-5/F-6/F-7/F-8**：契约补齐义务登记、组合测试集清单、M-8 归档义务行、入账状态注、3 FAIL 显式口径——R1 逐项核销或标注后置时点。
5. 前轮引用声明：R1 报告 MUST 引用本报告路径并逐条标注「已修复/未修复/新引入」。

---

*REL-086 发布半面 R0 审查冻结（2026-09-24，Release Reviewer Agent）。证据基线：check-governance 全量实测（exit 0，44 issues，2026-09-24）+ check-loop-runtime-claims 实测（semantic_units 305,604 / verdict BLOCKED）+ evidence-log 尺寸实测（1,659,471B）+ risk-log deadline 字段提取（036/039/046=2026-09-30、050=2026-10-31 打开）+ loop_runtime_claims.py L225-243 实读 + execution-packets.json / plan-tracker / decision-log L171 逐行读取 + version-plan-0.87.0.md / release-plan-0.87.0.md 先例对照。未生成事实（M-2 门禁数值、发布 tip、tag）一律标期义务，不预填。本报告为审查席独立结论，发布 GO/NO-GO 决策权在 Coordinator/用户。*
