# 发布审查报告 — REL-080（0.84.0 候选就绪状态）RELEASE 半面 R3（终验轮）

**结论：BLOCKED ｜ round=R3 ｜ unresolved_blockers=4 ｜ M-5 不予放行**

- **前轮引用**：`docs/reviews/review-REL-080-RELEASE-R2.md`（round=R2，NEEDS_CHANGE，`unresolved_blockers=4`，L-1~L-4）；上上游 `review-REL-080-RELEASE-R1`（NEEDS_CHANGE/3）／`review-REL-080-RELEASE-R0`（NEEDS_CHANGE/6）
- **审查方**：Release Reviewer Agent（独立复审；只读——写盘足迹仅本文件；`git status --porcelain --untracked-files=all` 复核期逐项一致：stage **36**、未跟踪 **0**、未暂存修改 **0**、HEAD 仍 `b537976`；本报告落盘后未跟踪 +1，由 Coordinator 决定是否入库）
- **审查对象**：0.84.0 候选 = `HEAD b537976` + **36 个 staged 文件**（R2 基线 35 → +`docs/reviews/review-REL-080-RELEASE-R2.md`〔R2 报告入库〕；无其他增量）+ `docs/release/release-checklist-0.84.0.md`（R3 收口文本）+ `docs/release/{feature-flags,rollback-plan}-0.84.0.md` + `project/CHANGELOG.md [0.84.0]` + `core/releases/0.84.0.json`（`lifecycle_state=candidate`）
- **审查日期**：2026-09-19 ｜ **审查性质**：R2 四阻断（L-1~L-4）**文本收口终验** + L-5~L-8 刷新核验——逐条标注「已修复/未修复/新引入」，**不盲批**
- **复跑范围（按 R2 §10 约定）**：**门禁面未重跑**——依据 = staged 集唯一增量为 R2 报告（35→36）、FIX-355 blob 锚逐字未变、R2 报告（08:17:29）之后仅清单（08:21:44）被写；R2 的 10 项复跑值构成 R3 通过基线。本轮实际执行的独立核验 = staged/HEAD/blob 锚/mtime 写入窗/治理记录抽查/先例锚（W-1~W-7）
- **硬门槛裁决**：**门槛面维持满足（同 R2）/ 文档面仍未满足**——`check-release … --lineage-mode candidate` 仍为 R2 记录的 **FAILED 1 issue(s)**（唯一 FAIL = `execution gates → governance health`，先例已接受面）；但发布检查清单**仍未完成 R2 指定的文本收口**：R2 四阻断中 **1 项全收口、3 项仅部分收口**，且新增 1 处门禁值不可溯源

---

## 0. 基线一致性抽查（只读 —— 与 Coordinator 申报逐项对照）

| # | 核验（只读） | 我的当场结果 | 申报对照 |
|---|---|---|---|
| W-1 | `git rev-parse HEAD` | `b537976d31f173ad2f2c69cc14888f51a1acbf3a` | 与「HEAD b537976 未动」**一致** ✓ |
| W-2 | `git status --porcelain --untracked-files=all` | **total 36 行 / staged 36 / untracked 0 / 未暂存修改 0**；staged 构成 = R2 基线 35 项 + `A docs/reviews/review-REL-080-RELEASE-R2.md` | 与「staged 36（+R2 报告…）」**一致** ✓；**无夹带**（无 0.85.0 候选内容、无 RISK 关闭声明） ✓ |
| W-3 | FIX-355 blob 锚（`git hash-object` + `ls-files -s` + `git diff` staged↔worktree） | `checks/review_domain.py` = **`e681bfa36866e8c0606a5e4cd37764bc15736fdf`**；`tests/test_review_closure_legacy.py` = **`610c2efcf174157e09b061d1c6c8b9d3fbba4642`**；索引 blob 与工作树 blob **逐值同**（diff 空） | 与 R2 W-7 / Code Review binding **逐字节一致** ✓ → **Code Review 结论有效性前提未失效** |
| W-4 | staged 36 项 mtime 写入窗 | R2 报告（08:17:29）之后**仅** `release-checklist-0.84.0.md`（08:21:44）被写；其余 34 项 mtime ≤ 06:08:53（含 hooks / SKILL / 投影 / fixture / 三件套） | 与「工作未触碰门禁判定面」**一致** ✓；**无 scope drift** ✓ |
| W-5 | 治理记录抽查 | `evidence-log.md:2291` = **EVD-1086**（migrate --auto 归档 FIX-246 + EVD-892、**用户 ask 确认留痕**、`check-archive-integrity` PASS、index 1221→1213、21→20 issues）；`decision-log.md:155/156` = **DEC-214 + DEC-214① 勘误**；`evidence-log.md:2281/2286/2287` = **EVD-1084 / EVD-1085 / RECO-FIX-355** | L-4① / L-3 的治理面载体**齐备** ✓ |
| W-6 | 0.83.0 先例锚（`release-checklist-0.83.0.md`） | L83 = Gate 16 口径「构成稳定 + 逐条归因（存量 **21 issues**）；**M-2 以当场值为准，构成漂移逐条归因，不得以旧值作新声明**」+ L83 归因含「**36×16**」；L80 = 「**17 门 = 16 PASS + 1 FAIL**」；L25/L107 = 存量 **21 issues** | 清单的「先例同型/更优」主张**成立** ✓（先例义务亦因此对 L137① 直接适用） |
| W-7 | risk-log 复评窗（归因段⑦的数值依据） | RISK-036 = **2026-09-30**、RISK-039 = **2026-09-30**、RISK-046 = **2026-09-30**、RISK-050 = **2026-10-31** | 归因段⑦「4 stale risk（RISK-036/039 09-30、RISK-046 09-30、RISK-050 10-31）」**逐值正确** ✓（R2 L-2 的「枚举不完整 2/4 + 理由不适配」已实质消解） |
| W-8 | 门禁面口径 | 未重跑（R2 约定）；R2 的 W-1~W-5 值（archive integrity PASS / unit tests PASS / check-governance **20 issues** / V2=0 / 全量 30F-3451P-1skip 858.70s / check-release FAILED 1 issue(s)）构成 R3 基线 | 与 Coordinator「门禁无需重跑」**一致** ✓ ——**但**见 §3 N-2（清单内一处门禁值与 R2 记录互斥） |

---

## 1. R2 四阻断逐条比对（MUST —— 不得盲批）

| R2 项 | R2 要求（处置列） | **R3 判定** | 实证（当场字符串/行号） |
|---|---|---|---|
| **L-1**（#14/#10 旧值） | #14 刷新为当场值（`FAILED — 1 issue(s)`、PASS 面枚举、唯一 FAIL = governance health），L108 同步；archive integrity 随 W-1 改 PASS | **✅ 已修复** | L101 = 「**R2 终态：FAILED — 1 issue(s)**（exit 1；演进：M-2 期 3 → R2 期 1）」+ PASS 面逐项枚举（含 `hot fact source`／`archive integrity`／`unit tests` 三项新 PASS）+ 「M-2 期原始 3 FAIL **留档**」标注；L108 = 「**R2 终态 1 FAIL**」+ 三项 PASS 与唯一余项口径；L103（#16）= 「**✅ PASS（归档迁移后——R2 独立复现）**」—— **R2 所指的「同一文件内同时持已收口与仍 3 项 FAIL」矛盾已消除** ✓（⚠ 计数标签见 §3 N-1） |
| **L-2**（归因段失真/缺项） | 标题与终值 21→**20**；⑧ Check 27 改「已 PASS」；**补 Check 36 ×16**；stale 补 4 项含 ID+天数；14→**428**；28s→**1,540.5 KB** | **⚠ 部分修复**（归因段已达标；**披露清单① 未同步**） | **已收口**：L114 标题 = 「governance health **20 issues** 逐条归因」；① = **1,540.5 KB**（含增量归因）；③ = **428**（+1 归因）；⑦ = **4 stale risk 含 ID + 复评窗日期**（W-7 逐值校验正确）；⑧ = **36 ×16**（0.83.0 同值延续，W-6 校验正确）；⑨ = Check 27 **已 PASS**；⑩ = Check 25 **已消**。**未收口**：**L137 ① 仍写「`evidence-log.md` 1,534.4 KB」+「当场终值 = **21 issues**」+「**2 stale risks**」**——三个数值均为**收口前**值，与同文件 L101/L108/L114/L147 的当场值（20 / 4 stale / 1,540.5 KB）**并列互斥**；R2 的 L-2 问题陈述④已点名「标题与 ①（L114 标题、**L137 ①**）」，该行即为未达成项 |
| **L-3**（DEC-213⑧ 残留） | L144 改指 **DEC-214**（+ 勘误行）；「EVD 入账随 R1」→ EVD-1085 实号；**L137 ① 中 `DEC-213⑧ 登记` 同步改为 DEC-214** | **⚠ 部分修复**（主目标已修复；**披露清单① 未同步**） | **已收口**：L144 = 「superseding DEC-203 半面——**DEC-214 + DEC-214① 勘误**；…**EVD-1085** + change-triage + **RECO-FIX-355**」——过期表述「EVD 入账随 R1」**已消失**，实号可核（W-5）✓。**未收口**：**L137 ① 仍写「+ `DEC-213⑧` 登记（RISK-051 复评：×2→已消解）」**——`DEC-213` 在 `decision-log.md:154` 全文仅 **①~⑦**（无 ⑧），即 R2 判定为阻断的「**发布包内成文引用一个不存在的决策条目**」条件**在收口后仍成立** |
| **L-4**（归档证据/#17/义务清单） | 补迁移证据行；L191 改「已执行…」；L167/L170/L183/L188 按实际态勾选并改写；#17 写入本轮实测值 | **⚠ 部分修复**（4/9 面已收口；**M-8 义务清单仍 5 处与实态相反**） | **已收口**：① **EVD-1086 在案**（W-5：migrate 实测 + ask 确认留痕 + index 1221→1213）✓；披露② L145 = 「归档迁移（R1 F-15）——✅ 已执行…EVD-1086」✓；L110（M-6 段）= 「**终态——R2 后已执行**」✓；⑥ #17 = 「**R2 终态复跑：30F/3451P/1 skipped/390 subtests（858.70s）——0 新增失败**」✓；L149 版本钉残留义务行 = 「全量 pytest 复跑**已完成**」✓。**未收口（逐行，均为可直接落笔的文本面）**：② **L192（M-8 义务）仍写「归档：`migrate --auto --dry-run` 已实测『无可归档数据 / 零写操作』」**——与**已执行**的迁移（EVD-1086）及同文件 L110 **直接矛盾**；③ **L168 仍写「M-5 发布记录：proposed EVD-1082」**（EVD-1082/1083 早已落账，发布面为 EVD-1084/1085/1086）；④ **L171 仍写「M-7 session-snapshot 刷新：proposed 全文」且 `[ ]`**——快照**已落盘**（mtime 03:21:44，含 session_date），与披露②「M-7 已收口」矛盾；⑤ **L188 仍写「FIX-353 两测试文件…当前为工作树修改、未 staged」**——实测两文件**已在 stage 区**（W-2：未暂存修改 0）；勾选态 **L187（execution-packet）/ L188 / L189（pytest 复跑）仍 `[ ]`**，而同文件已宣告对应动作完成 |

**小结**：R2 的 4 项阻断 —— **L-1 全收口**；**L-2 / L-3 / L-4 各留可确定性的文本残项**（合计 6 处行级 + 3 处勾选态），且残项**全部落在 R2 已点名的行上**（L137① / L168 / L171 / L188 / L189 / L192 / L187）。**无一是新增技术缺陷**：门禁面、blob 锚、staged 集、产品代码均未退化。

---

## 2. L-5~L-8（R2 非阻断同批项）刷新核验

| R2 项 | **R3 判定** | 实证 |
|---|---|---|
| **L-5**（session-snapshot 内容层陈旧，P2「MUST 与 L-1~L-4 同批刷新」） | **❌ 未修复** | `session-snapshot.md` mtime = **03:21:44**（R2 报告 08:17 之后**零写入**）——内容仍为 R0/R1 期：L8「REL-080-RELEASE-R0 = NEEDS_CHANGE → 6 阻断项收口 → **R1 待发起**」；L10「M-6 **归档跳过**」；L11「FIX-354 **进行中** / F-04 Coordinator **待跑**」；L12/L23「**R1 复审** → tag」；L29「EVD-1084（发布证据——**落账随 R1 通过**）」；L39「Check 30 **V2 ×2**」（实测 V2=0）+「structural 424 行」（实测 428）；**通篇 0 次 FIX-355 / 0 次 EVD-1085/1086 / 0 次归档迁移 / 0 次 20 issues**。`session_date` 可解析 ⇒ Check 28c/35 机检不报 → **内容失实无机器兜底**（R2 已登记该口径缺口） |
| **L-6**（P3 精度项） | **❌ 未修复** | 逐 token 复核（grep 命中即原文未变）：L38/L71 仍「16,011B→**2,699B**」（且与 L90 的「AGENTS.md=**2988B**/thin」同行自相矛盾——我另测 staged `AGENTS.md` blob = **4,150 B**，与 2,699/2,988 均不同，刷新时 MUST 以 `check-entry-bootstrap-sync` **当场输出**为准）；L94 仍「canonical **767** / actual **865**」（R2 实测 769/870）；L104 仍「42 tests OK」（R2 实测 32+42=74）；L112 仍「**staged 33** 项构成」（实测 36，落盘后 37） |
| **L-7**（P3 演练零污染表时点限定语） | **❌ 未修复** | `rollback-plan-0.84.0.md` mtime = 03:31:04（未重写）；L170 仍 `staged 文件数 28 → 28`、L191 仍「staged 28 不变」——无「**演练时点 = R0 staged 28**」限定语。**零污染结论本身不被推翻**（时点值，非本轮实测值）→ 维持「接受 + 建议」 |
| **L-8**（P3 标级不一致，C-01） | **❌ 未修复** | 源报告 `review-FIX-355-CODE-R0.md` **L129 / L177 / L185 / L203** 逐处记为 **C-01 = P1**（「发现汇总：P0 = 0｜**P1 = 1（C-01）**｜P2 = 4｜P3 = 3」）；`plan-tracker.md:94` 与 `EVD-1085` 仍记「**C-01/P2** 残留登记 0.85.0」——**既未如实标级 P1，亦未见显式降级依据登记**（R2 要求的二者择一均未执行） |
| **F-07 残留**（R2 并入 L-2 处置的 R0 项） | **⚠ 部分对齐** | 归因段已补 Check 36 族（⑧）✓；但 #13（L100，M-2 期 WARN 枚举）仍不含 Check 35，且 L119 的「FAIL/WARN/ERROR 均逐项列明归属」表述未收窄 → 维持 P3 同批 |

---

## 3. 本轮新发现（R2→R3 窗口内新引入/新暴露）

| ID | 级别 | 问题（事实） | 处置 |
|---|---|---|---|
| **N-1** | P3 | **#14 计数标签与自身枚举不自洽**：L101 表头「PASS 面（**17 项**，R2 复核）」，但其后枚举 **18 名**（… loop runtime claim gate / dsh upgrade regression / unit tests），并与同行「**FAIL 1 项**」冲突——0.83.0 先例口径为「**17 门 = 16 PASS + 1 FAIL**」（W-6/L80）。R2 报告 W-4 自身亦存在同型（写「16 项」而枚举 18 名） | 二者择一并说明口径（推荐按先例写「17 门 = 16 PASS + 1 FAIL」），或把 PASS 面写为「16 项 + 执行闸门子面 unit tests」。**不阻断**（不影响 FAILED 1 issue(s) 的事实） |
| **N-2** | **P2（阻断待澄清）** | **#14 的 loop-runtime-claim 值无可复查出处且与 R2 记录互斥**：L101 写「inventory `2df0071d…`，candidates **848**」并置于「**R2 复核**」语境；但 R2 报告 W-4/W-3/§8.3 三处记录其当场值为「inventory **`2613892f…`**；candidates **851**；parsed=851」。全仓 grep 结果：`2df0071d` **仅出现在清单该行**（无任何命令输出/EVD/报告承载）；`2613892f` 仅出现在 R2 报告；`ace4454b` 为 M-2 期值（#13/L146）。→ 发布包内**同一轮次门禁值互斥且无第三方可查来源**（SKILL 事实依据红线：APPROVED 只能基于可复查事实） | **声明或改回**：要么给出该值的当场命令 + 时间 + 输出（并注明为「Coordinator 复跑」而非「R2 复核」），要么改回 R2 记录值 `2613892f…/851`。若为 R2 后的复跑，须同时说明候选数 851→848 的**减少**原因（新增 EVD-1086/R2 报告只应使枚举**增加**） |
| （观察） | P3 | **28s 数值的时点**：归因段① 记 1,540.5 KB（**R2 终态**，标注正确）；本轮实测 `evidence-log.md` = **1,578,830 B（1,541.8 KB）**，Δ = +1,327 B（EVD-1086 + R2 审查记录行）。作为「R2 终态」陈述**可接受**；若 M-5 期以「当场值」口径引用，MUST 刷新 | M-5 收尾时一并刷新（无需单独修复） |

---

## 4. 硬门槛逐项裁决（本轮当场）

| 硬门槛 | 阈值 | 本次事实 | 判定 |
|---|---|---|---|
| 发布检查清单全部 PASS | = 100% | **门禁面**：`check-release` **FAILED 1 issue(s)**（唯一 = governance health 子门；R2 已裁决「先例已接受面」，本轮无新证据推翻）；**文档面**：R2 四阻断 **3 项仅部分收口**（B-1/B-2/B-3）+ 1 处门禁值不可溯源（B-4） | ✗ **未满足**（文档面） |
| 回滚方案存在且已验证 | = 已验证 | 隔离副本 15 步演练 + R1 独立复算在案；#18 已回填；真实 tip 面 = M-5 期义务（先例同型） | ✓ **满足** |
| CHANGELOG 用户视角完整 | 关键段全覆盖 | `[0.84.0] - 2026-09-19`：Added/Changed/Fixed/B-1~B-6/披露/Breaking=无/MINOR 依据 | ✓ |
| breaking changes 已标注 | 100% | 显式「无」+ VERSIONING 逐项反证 | ✓ |
| Feature Flag 关闭验证 | 全部通过 | F-1/F-2 双臂 + I-1~I-5 三层机检 + 守护测试（R2 已核，本轮无触碰面） | ✓ |
| P0 任务完成 | — | AUDIT-154 + FEAT-032~040 九任务全 ✅；REL-080 行 ⏳（待 M-5） | ✓（发布任务本身待 M-5） |
| 版本 bump 完整性 | 全平面 | check-version-consistency PASS（R2）；staged blob 与索引逐值一致（W-3）；36 staged 无夹带（W-2） | ✓ |

---

## 5. 结论与最小收口清单（行级、可直接落笔、无需重跑门禁）

**结论：BLOCKED（round=R3）｜unresolved_blockers=4**

**协议口径（必须记录）**：R3 = 复审 fuse 达限轮（`release-review` SKILL：「超过复审 fuse 的 NEEDS_CHANGE 必须升级为 BLOCKED」；behavior-protocol M7.4 触发器 **T2**：round≥3 仍 NEEDS_CHANGE → MUST 转 BLOCKED + escalation）。本轮**仍有 BLOCKING**（B-1~B-4），故给出 **BLOCKED 终态**——与「NEEDS_CHANGE → T2 升级为 BLOCKED」语义等价，Coordinator 按 T2 **MUST** escalation（`ask_user_question`），**不得**以「剩余为文本面小改」为由自行放行 M-5。

**阻断项（4）**：
1. **B-1（承 L-2）**：披露清单①（**L137**）仍以收口前数值自述——`1,534.4 KB` / 当场终值 `21 issues` / `2 stale risks`，与同文件 L101/L108/L114/L147 的当场值（20 / 4 stale / 1,540.5 KB）**并列互斥**；先例义务「**不得以旧值作新声明**」未达成。
2. **B-2（承 L-3）**：**L137** 仍引用**不存在的 `DEC-213⑧`**（decision-log L154 仅 ①~⑦）——「发布包内成文引用一个不存在的决策条目」条件仍成立。
3. **B-3（承 L-4）**：M-8 义务清单 5 处与实态相反/未勾——**L192**「归档…已实测无可归档数据/零写操作」（与 EVD-1086 已执行矛盾）、**L168**「proposed EVD-1082」、**L171**「M-7 … proposed 全文」+`[ ]`、**L188**「FIX-353 … 未 staged」+`[ ]`、**L189** pytest 复跑未勾（+**L187** execution-packet 未勾）。
4. **B-4（N-2）**：**L101** 的 `2df0071d…/candidates 848` 无可复查出处且与 R2 报告 W-4 的 `2613892f…/851` 互斥。

**最小收口清单（文本面；逐行改写即可，不触碰 blob 锚/产品代码/staged 构成）**：
1. **L137 ①**：`1,534.4 KB` → `1,540.5 KB`（R2 终态口径）；`+ DEC-213⑧ 登记` → `+ DEC-214 / DEC-214① 登记`；`当场终值 = **21 issues**` → `20 issues`；`2 stale risks` → `4 stale risks（RISK-036/039/046 复评窗 09-30、RISK-050 10-31）`；`系 21 计数` → `系 20 计数`；句末「21 issues 存量披露发布；本版构成 ≤ 同型」→「**20 issues** 存量披露发布；本版 **20 < 21** 且 V2 消解」。
2. **L192**：→「已执行（EVD-1086）：migrate --auto 归档 FIX-246 → `archive/tasks/v0.1.0~v0.82.0-incremental-20260919-1.md` + EVD-892 → `archive/evidence/`；`check-archive-integrity` PASS（index 1221→1213）」+ 勾选 `[x]`。
3. **L188**：→「已 staged（在 36 项候选构成内）」+ `[x]`；**L189**：→ `[x]` + 注明「R2 复跑 30F/3451P/1 skipped（858.70s，0 新增）」；**L187**：→ `[x]`（Check 18c 已收口）。**L168**：`proposed EVD-1082` → 「发布面证据 EVD-1084/1085/1086 已落账；M-5 自身证据行由 Coordinator 落账」（复选框按 M-5 未执行保持 `[ ]`）。**L171**：→ `[x]`「已落盘（session_date 2026-09-19；Check 28c 已修复）」。
4. **L101**：PASS 面计数 → 与枚举一致（推荐「17 门 = 16 PASS + 1 FAIL（PASS 面 16 项 + 执行闸门子面 unit tests）」）；`2df0071d… / 848` → 声明来源或改回 `2613892f… / 851`。
5. **`.governance/session-snapshot.md`**（L-5，**非阻断但 MUST 同批**）：整体刷新至 R2/R3 期——R2/R3 审查链、FIX-355 + EVD-1085/1086、归档迁移已执行、V2=0、20 issues、下一步 = M-5（待放行）；删除「R1 待发起 / FIX-354 进行中 / F-04 待跑 / V2 ×2 / M-6 归档跳过 / structural 424」。
6. **L-6/L-7/L-8/F-07（P3 同批）**：按 §2 逐项刷新（字节数以当场命令输出为准；`staged 28` 补时点限定语；C-01 如实标 **P1** 或登记显式降级依据）。

**收口后的路径（由 Coordinator 裁决，Reviewer 不决定）**：上述均为**文本面**修改（不涉及产品代码、不涉及 blob 锚、不需重跑门禁）——收口后可经 **R4 终验轮（同 Reviewer，注入本报告）** 或按 **T2 escalation 由用户显式授权的等价验证**关闭；`core/releases/0.84.0.json` 在此之前保持 `candidate`。

---

## 6. 本轮复核确认的通过面（无需重做）

`archive integrity` PASS / `unit tests` 闸门 PASS + 全量 **0 新增失败**（30F/3451P/1skipped/858.70s，R2 实测）/ `hot fact source` PASS / release docs PASS / release lineage candidate 边界 PASS / gate sequence PASS / one dot zero blockers PASS / changelog PASS / loop runtime claim（semantic + identity PASS）/ verify + e2e check + dsh upgrade regression（隔离 temp-DSH_HOME 冒烟）PASS / Check 31·32·34·35 PASS / **Check 30 V2 violations = 0**（两条豁免行以 `downgraded` 形态如实保留，非静默）/ **Check 27 已 PASS** / 归因段（L114）①②③④⑤⑥⑦⑧⑨⑩ **逐值与实测一致**（本轮 W-6/W-7 复核）/ FIX-355 七面入账 + **blob 锚逐字节未变**（W-3）/ DEC-214 + DEC-214① 在案（W-5）/ **EVD-1086 归档迁移证据在案**（W-5）/ **staged 36 无夹带 + 无 scope drift**（W-2/W-4）。

## 7. 约束性备注（binding notes）

1. **M-5（commit + transition + tag v0.84.0 + push）不予放行**；`core/releases/0.84.0.json` 保持 `candidate`；**36 staged 集保持原样**——禁止为改文档而触碰 `checks/review_domain.py` / `tests/test_review_closure_legacy.py`（锚 `e681bfa…`/`610c2ef…` 是 Code Review 结论的有效性前提）。
2. **本轮 BLOCKED 属文档面子集**：**不撤销** R2 已确认的门禁面结论（archive integrity PASS / unit tests PASS / V2=0 / 0 新增失败 / 三门禁 PASS）；亦**不构成**「产品代码不可发布」的判断——风险性质是「发布包陈述与当场事实不符」，与 R2 的 L-1~L-4 同源。
3. FIX-246 归档行**不得**为「消除 WARN」回退或改写（DEC-214 / DEC-199 要求可见性保留，V2 violations = 0 正是正确口径）。
4. C-01（源判 **P1**）的「登记 0.85.0 候选」可继续接受，但 MUST 如实标级或登记降级依据（L-8）。
5. `release-ledger --version 0.84.0 --no-remote` 于 M-5 commit 后 MUST 复跑；tag 后 MUST 复跑 `check-release --lineage-mode released --release-commit <commit>` 与 `release-ledger --remote origin`（R1 结论 4 维持）。
6. **写盘足迹声明**：本报告为本次审查**唯一**写盘产物（新增 `docs/reviews/review-REL-080-RELEASE-R3.md`，未跟踪 +1；未修改任何 staged 文件）——复核前 `untracked=0`、复核期 `unstaged=0` 已逐项留痕（W-2/W-4）。

---

*审查方：Release Reviewer Agent（独立复审，只读）｜审查对象：0.84.0 候选（HEAD `b537976` + 36 staged 文件）｜前轮：`review-REL-080-RELEASE-R2`（NEEDS_CHANGE/4）｜结论：**BLOCKED / round=R3 / unresolved_blockers=4**｜机录义务：Coordinator 以 `review-record` 持久化本结论（round=R3；Reviewer 不写治理状态）*
