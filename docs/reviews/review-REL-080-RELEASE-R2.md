# 发布审查报告 — REL-080（0.84.0 候选就绪状态）RELEASE 半面 R2

**结论：NEEDS_CHANGE ｜ round=R2 ｜ unresolved_blockers=4**

- **前轮引用**：`docs/reviews/review-REL-080-RELEASE-R1.md`（round=R1，NEEDS_CHANGE，`unresolved_blockers=3`，F-15~F-23）；上上游 `docs/reviews/review-REL-080-RELEASE-R0.md`（round=R0，NEEDS_CHANGE/6）
- **审查方**：Release Reviewer Agent（独立复审；只读——本报告除本文件外零写盘；`git status --porcelain --untracked-files=all` 复跑前后逐行一致：stage **35** 项、未跟踪 **0**、HEAD 仍 `b537976`）
- **审查对象**：0.84.0 候选 = `HEAD b537976` + **35 个 staged 文件**（R1 时 33 → +`docs/reviews/review-FIX-355-CODE-R0.md`〔FIX-355 走链报告〕+`docs/reviews/review-REL-080-RELEASE-R1.md`〔R1 报告入库〕）+ `docs/release/{release-checklist,feature-flags,rollback-plan}-0.84.0.md` + `project/CHANGELOG.md [0.84.0]` + `core/releases/0.84.0.json`（`lifecycle_state=candidate` 实测）
- **审查日期**：2026-09-19 ｜ **审查性质**：R1 三阻断（F-15/F-16/F-17）+ 披露项（F-18）+ P2/P3（F-19~F-23）的收口实证——**逐条标注「已修复/未修复/新引入」，不盲批**
- **证据基线**：MUST 复跑面全量独立复跑（**10 项**：check-archive-integrity / check-governance `--summary-only` + 全量 + `--level strict` Check 2 / `check-release` 全量执行闸门 / **全量 `pytest` 实跑 858.70s** / git 三面 / blob 锚 / 归档落地逐文件核验）——本轮**无「未独立验证」门禁**
- **硬门槛裁决**：**门槛面满足 / 文档面未满足**——`check-release … --lineage-mode candidate` = **FAILED 1 issue(s)**（唯一 FAIL = `execution gates → governance health (exit=1)`；`archive integrity` / `unit tests` / 其余 **16 面全 PASS**）；但发布检查清单仍以与当场实测相矛盾的数值自述，并保留一条已不存在条目的引用 → 见 §8 / §9

---

## 0. 独立复跑证据（只读 —— 与 Coordinator/R1 申报逐项对照）

| # | 命令 / 核验（只读） | 我的当场结果 | 与申报对照 |
|---|---|---|---|
| W-1 | `check-archive-integrity` | **PASSED exit 0**；hot 85 / archived 93 / index **1213** / total 178；`[PASS] Archive integrity verified — 178 total tasks, index consistent` | **R1 F-15 手禁已解除** ✓（R1 为 FAIL exit 1 / pending 1） |
| W-2 | `check-governance --summary-only` | **`Governance: 20 issues` exit 0**；FAIL 面 = **28s ×1**（1,577,503 B / **1540.5 KB**，advisory）；WARN 面 = **2×4（RISK-036/039/046/050）+ 14×428 + 28n×8 + 28q×4 + 30×29 + 30c×2 + 36×16** | 总数 **20** 与申报一致 ✓；**构成枚举与 checklist 文本不符**（见 F-24/F-25） |
| W-3 | `check-governance`（全量 + `--level strict`） | 逐族当场值：**Check 2** stale = `RISK-036 (10d) / RISK-039 (10d) / RISK-046 (10d) / RISK-050 (8d)`；**Check 27** = `[PASS] Archive integrity verified`（**无 WARN**）；**Check 30** = `29 closure WARN(s)`（含 `[V1] REL-080: R1=NEEDS_CHANGE non-terminal`〔本轮自身〕+ `[V2] FIX-246` / `[V2] REL-078` 两条「downgraded」豁免行；**V2 violation 0**）；**Check 30c** = `2 WARN`（FIX-256/258 历史手写行）；**Check 36** = **16 WARN**（RISK-002/004/007/010~014 等 R3 跨实体引用）；**Check 28o** = 3 ERROR / 23 WARN（advisory）；**Check 31** `PASS`（inventory `2613892f…`）、**Check 34** `PASS`（37/37） | V2=0 ✓；**Check 27 已转为 PASS 而非 checklist 所记 WARN ×1**（F-25） |
| W-4 | `SPG_RELEASE_GATE_TIMEOUT=600 check-release --version 0.84.0 --require-changelog --lineage-mode candidate`（**全量执行闸门**） | **FAILED — 1 issue(s) exit 1**。PASS 面 16 项：version consistency / release fact source / hot fact source / runtime readiness matrix / first session measurement / governance pack status / agent adapters / projection sync / cross references / **archive integrity** / release docs / release lineage（candidate 边界贴示在案）/ gate sequence for release / one dot zero blockers / changelog / loop fuse block / loop runtime claim gate（`semantic_verdict=PASS; identity_verdict=PASS; inventory=2613892f…; candidates=851; parsed=851; skip=0; truncate=0`）/ dsh upgrade regression（隔离 temp-DSH_HOME 冒烟）。执行闸门子面：`verify (exit=0) PASS` / **`governance health (exit=1) FAIL`** / `e2e check (exit=0) PASS` / **`unit tests (exit=0) PASS`** | R1 的 **2 issue(s)**（archive integrity + governance health）→ **1 issue(s)**：`archive integrity` **FAIL→PASS 已独立复现**，「唯一 FAIL = governance health」申报**成立** ✓ |
| W-5 | `pytest skills/software-project-governance/infra/tests -q`（全量实跑） | **30 failed / 3451 passed / 1 skipped / 390 subtests passed**（858.70s）；30 项逐条为既有环境族——`test_pre_commit_review_evidence.py::ReviewEvidenceRegexTests::*`（hook 子测 ×24，根因 = `WSL_E_DEFAULT_DISTRO_NOT_FOUND`，stderr 原文当场可查）+ `test_hooks.py::PlanTrackerMatcherTests::test_replay_real_plan_tracker_hits`（×6，活体耦合） | **0 新增失败** ✓（R1 实测 30F/3451P，本轮逐值同型）；**checklist #17 仍记 M-1 期「32 failed / 3441 passed」**（F-26） |
| W-6 | 归档落地逐文件核验 | `archive/index.md` **L498** = `| FIX-246 | 完成 (2026-08-07 恢复登记 2026-09-19) | 0.57.0 | archive/tasks/v0.1.0~v0.82.0-incremental-20260919-1.md |`；**L1008** = `| EVD-892 | FIX-246 | archive/evidence/evidence-v0.1.0-0.82.0.md |`；`archive/tasks/v0.1.0~v0.82.0-incremental-20260919-1.md:15` = FIX-246 完整行（含 EVD-892 + REVIEW-FIX-246-R1 注记）；`archive/evidence/evidence-v0.1.0-0.82.0.md:13` = EVD-892 全文；三文件 mtime = **2026-09-19 07:47**；plan-tracker 侧 `| **P2** | FIX-246 |` 行已移出（grep 0 命中） | **归档写操作确已执行且内容合规** ✓（载体与申报一致：1 task + 1 evidence） |
| W-7 | FIX-355 blob 锚核验（`git hash-object` + `git ls-files -s`） | `review_domain.py` = **`e681bfa36866e8c0606a5e4cd37764bc15736fdf`**；`test_review_closure_legacy.py` = **`610c2efcf174157e09b061d1c6c8b9d3fbba4642`**；stage 区 blob 与工作树 blob **逐值同** | 与 R1/Code Review 申报锚**逐字节一致** ✓；Code Review 复审基线（binding note 5）**未失效** |
| W-8 | FIX-355 七面入账核验 | `plan-tracker.md:94` 任务行（`✅ 完成 (2026-09-19)——EVD-1085` + 独立 Code Review 走链 + C-01/P2 残留登记 0.85.0）；`execution-packets.json` FIX-355 包；`evidence-log.md:2286` EVD-1085（含审查链 + 独立复跑 5 项）；`.governance/change-triage/FIX-355.json`；`.governance/review-FIX-355-R0.md`（`review-record CLI 机器写入`，round R0，`APPROVED_WITH_NOTES` + `unresolved_blockers=0`）；`docs/reviews/review-FIX-355-CODE-R0.md`（已 staged）；checklist L112 归属行点名 `review_domain.py` | **R1 F-16 七面逐面实测齐备** ✓（R1 时 7 面全缺） |
| W-9 | 决策记录核验 | `decision-log.md:155` = **DEC-214 全文在位**（①事实变化 ②修复语义〔FAIL→WARN 可见性保留〕③DEC-199 边界维持 ④**生效条件 = Developer→Code Reviewer 独立走链 + 独立审查裁决语义张力**）；`:156` = **DEC-214① 勘误行**（REL-078 实在 index L504、FIX-246 半面成立、结论不受影响）；**DEC-213 行（L154）仍仅 ①~⑦**（`⑧` 全文件仍 0 命中） | **F-17 前半（superseding 落账）已收口** ✓；**checklist 对 `DEC-213⑧` 的引用仍在**（F-25②） |
| W-10 | 非本次范围面复核（防夹带） | `core/releases/0.84.0.json` = `"lifecycle_state":"candidate"`, `"events":[]`, `"withdrawn":false` ✓；`git rev-list --count 2a15e59..b537976` = **10**（与 Change Inventory 一致）；`project/CHANGELOG.md:5` = `## [0.84.0] - 2026-09-19`；rollback-plan 演练记录 15 步表在案（P-3 `82 paths` / P-4 `98 paths` / P-12 `exit 1` 反向实证 / 零污染表 staged `28→28`）；无 0.85.0 候选池内容夹带、无 RISK 关闭声明 | ✓ 无夹带；演练时点限定语仍未补（F-23 维持 R1 判定） |

---

## 1. R1 三阻断项逐条比对（MUST —— 不得盲批）

| R1 项 | 内容 | **R2 判定** | 实证 |
|---|---|---|---|
| **F-15** | archive integrity FAIL（本版新引入门禁失败）+ checklist #18 演练行未回填 + #14 结论行未刷新 | **部分修复 —— 门禁面收口已独立复现；文档/证据面未收口** | **已成立部分**：① 归档写操作**确已执行**——FIX-246 入 `v0.1.0~v0.82.0-incremental-20260919-1.md`、EVD-892 入 `evidence-v0.1.0-0.82.0.md`、index L498/L1008 双登记（W-6，三文件 mtime 07:47）；② `check-archive-integrity` **PASS exit 0**（W-1，index 1221→1213）；③ `check-release` 中 `archive integrity` **FAIL→PASS**（W-4：R1 的 2 issue(s)→**1 issue(s)**）；④ checklist **#16 已更新**为三段轨迹「PASS→FAIL（R1 F-15）→归档迁移后 PASS」（L103）；⑤ **#18 已回填**为「✅ 已执行」并引 15 步表 + R1 独立复算 + F-04 反向实证（L105）。**未成立部分**：① **#14 行仍写「FAILED — 3 issue(s)」且 FAIL 三项逐条枚举（hot fact source / governance health / unit tests）**（L101），L108 仍写「剩余 3 项 FAIL」——实测 **1 issue(s)** 且 hot fact source 与 unit tests **均 PASS**；② 披露清单 ①（L137）**未反映归档收口终态**（仍 1,534.4 KB / 21 issues 并存）——**即：R1 要求的「checklist 必须能独立证明 F-15 已收口」未达成**，发布文档同时持「已收口」与「仍 3 项 FAIL」两种陈述 |
| **F-16** | FIX-355 入账 7 面全缺 | **已修复** | W-8 逐面实测：task 行 ✓（L94，版本/依赖/交付面齐）／execution packet ✓／EVD-1085 ✓（含审查链 + 独立复跑 5 项）／change-triage `FIX-355.json` ✓（Check 32 实测 113 记录 0 invalid）／独立审查 = `review-FIX-355-CODE-R0` **机录** `review-FIX-355-R0`（round R0，`APPROVED_WITH_NOTES` + `unresolved_blockers=0`）✓／checklist 归属行点名 `checks/review_domain.py`（L112）✓／staged 平面披露把 35 项构成逐一点明（L112，含 review_domain.py + 两份新审查报告）✓。**scope 说明**：Code Review 仅覆盖 DEC-214④「走链」一面，其余六面本报告按发布审查口径独立核验（非代码审查替代） |
| **F-17** | superseding DEC-203 未落账 + 发布文档引用不存在的 `DEC-213⑧` | **部分修复 —— DEC 已落账 + 勘误在案；发布文档引用未纠正** | **已修复部分**：DEC-214 全文在位（L155，含四项：事实变化 / 修复语义（WARN 非 PASS 可见性保留）/ DEC-199 边界维持 / **生效条件 = 走链**）+ 勘误行 DEC-214①（L156，Code Review 事实核查驱动、结论不受影响）；DEC-203 的生效条件（superseding DEC + 走链）**两项均落地**。**未修复部分**：checklist **L144 仍写「superseding DEC-203 半面否决——DEC-213⑧；EVD 入账随 R1」**——`DEC-213⑧` 在 decision-log **仍不存在**（0 命中），且「EVD 入账随 R1」已过期（EVD-1085 已成行）。**即 R1 F-17 的第三面（发布文档引用不存在的条目）在收口后仍以成文形式存在于发布包内** |

> **交叉验证补充（F-16 与走链的实质面）**：Code Review 结论为 `APPROVED_WITH_NOTES` + `unresolved_blockers=0`（合法通过终态），但其§5 记录 **C-01 = P1**（豁免行因果断言对 REL-078/FIX-246 两个现网实例均不成立）；Coordinator 在 plan-tracker L94 与 EVD-1085 中记作「**C-01/P2** 残留登记 0.85.0 候选」。**级别标注与源报告不一致（P1 记为 P2）**——不构成门禁失败（该 P1 不改变 FAIL/WARN 判定、不影响 V2=0），但属账目精度缺陷，见 §7 备注。

---

## 2. F-18 披露颗粒度逐条比对（对照 0.83.0 Gate 16 先例）

**0.83.0 先例义务（`release-checklist-0.83.0.md` L83 明文的 Gate 16 口径）**：「构成稳定 + 逐条归因（存量 21 issues 口径）；**M-2 以当场值为准，构成漂移逐条归因，不得以旧值作新声明**」。先例以该项义务驱动了 RELEASE R0 的 F-1 归因回填。

**R2 当场值（W-2/W-3）**：21 → **20**（Δ = ①28s 数值漂移 1537.6→1540.5 KB；②Check 27 archive WARN **消解**；③Check 14 426→428）。

**逐族对照**：

| 族（当场值） | checklist L114 归因段 | 判定 |
|---|---|---|
| 28s ×1（1,540.5 KB） | 记 **1,540.3 KB**（自述增量 = EVD-1082~1085 + DEC-213/214） | △ 数值偏差 −0.2 KB（量级可忽略；但机制上等于「以旧值作新声明」，与先例义务字面冲突） |
| 28n×8 / 28o 3E+23W | ②28n/28o 族（module_size ×3 + function_size ×5 + checks/ 子模块超限） | ✓ 有归因 |
| **14 structural ×428** | ③记 **×427** | △ 计数未刷新（+1 = 本窗口新 EVD 行，机制已写对） |
| 30 closure WARN ×29 | ④记 **×29**（含两条豁免行 + 历史手写行） | ✓ 与 W-3 逐值一致；**V2 violations 0 实测复现** |
| 30c ×2 | ⑤记 ×2 | ✓ |
| 28q ×4 | ⑥记 ×4 | ✓ |
| stale ×4（RISK-036/039/046/050，10d/10d/10d/8d） | ⑦记「**2 stale risk（RISK-036/039 复评窗 09-30 未到）**」 | ✗ **枚举不完整 2/4 且理由不适配**——RISK-046/RISK-050 未列，且 RISK-050 的复评依据不是「09-30 复评窗」；与 R1 F-18 所记同型缺陷**未修复**（R1 亦曾记为「2 stale」） |
| **27 archive ×1** | ⑧记「**27 archive-integrity WARN ×1（本版新出现——归档迁移待执行，M-8 收口后消）**」 | ✗ **未修复 + 新引入失真**：迁移**已执行**、Check 27 实测 `[PASS] Archive integrity verified`（W-1/W-3）→ 该行把一个**已不存在的 WARN** 记为现存，并把已完成动作（迁移）写成「待执行」——与 checklist 自身 #16（L103：归档迁移后 PASS）**同一文件内互相矛盾** |
| untracked（Check 25） | ⑨「25 untracked（审查报告入库后消）」（不在 20 项内，已消） | ✓ OK，但 CHECKLIST **未记 Check 36 ×16**（W-3 实测）——20 项中的一族在归因段**完全缺项** |
| 标题口径 | L114 标题 = «governance health **21 issues** 逐条归因»；L137 ① = «收口后 check-governance 当场终值 = **21 issues**» | ✗ **标题与终值双双过期**（实测 20；R1 时亦为 21） |

**F-18 裁决**：**部分修复（未达先例颗粒度）**——归因段已从「族名级」升级为「逐条九项」，形式上接近先例，但存在**三处实质缺口**（Check 36 缺项 / Check 27 与实测相反 / stale 2-of-4）+ **三处数值未刷新**（21→20、427→428、1537.6→1540.5 KB）。先例义务的落点正是「**不得以旧值作新声明**」，而本版在**自身收口后**的终值上仍以收口前数值自述 → 未达标。

---

## 3. F-19~F-23（P2/P3）刷新结果

| R1 项 | **R2 判定** | 实证 |
|---|---|---|
| **F-19**（staged 33 平面归属漏 `review_domain.py`；计数关系未列明） | **已修复** | checklist L112 归属段完整：28 原始 M-1 + FIX-353 ×2 + FIX-354 ×3 + **FIX-355 ×2（`checks/review_domain.py` +168/−10 + `tests/test_review_closure_legacy.py` +211）** + R0/R1/FIX-355-CODE-R0 三份审查报告 + 本清单更新 = **35 项**（被测 `git status` 实测 35 ✓）。标题仍写「staged **33** 项构成」为**成文时点残留**（该 33 是 L112 段的写就时点；行内已含 35 项条目）→ 仅措辞，不阻断 |
| **F-20**（#17 计数过期 + #184/#185 未勾选 + 无全量复跑原始输出） | **部分修复 —— 技术面已由我独立复跑确认；包内记录仍未收口** | 技术面：W-4 `unit tests (exit=0) PASS`、W-5 全量 **30F/3451P**（0 新增）；EVD-1085 已含独立复跑 5 项之一（`44 passed`）。包内：#17（L104）**仍为 M-1 期「32 failed / 3441 passed / 1 skipped（1176.95s）」**且仍自述「全量复跑列为 Coordinator/CI 义务（本报告不预填复跑结论）」；#188 复跑义务复选框**未勾选**。→ 与 R1 判定同级，**未收口** |
| **F-21**（session-snapshot 过期 + 通篇未提 FIX-355） | **未修复** | `session-snapshot.md` 当前态仍为「**0.84.0 发布链收口中（REL-080-RELEASE-R0 = NEEDS_CHANGE → 6 阻断项收口 → R1 待发起）**」：L11 记「FIX-354 **进行中** / F-04 Coordinator **待跑**」；L29 记「EVD-1084 落账**随 R1 通过**」（实为已落账 EVD-1084/1085）；L39 仍记「**Check 30 V2 ×2**」为遗留（实测 V2=0）且**通篇 0 次 FIX-355**；L12 仍以「R1 复审」为下一步（R1 已完成、R2 为本轮）。`session_date` 可解析故 Check 35/28c 不报 → 属**内容层陈旧**，机检无兜底 |
| **F-22**（checklist 其余精度项：L38/L71 16,011B→2,699B；L104 42 tests OK；L94 767/865；L100 18c ×6；L101/L108 3 issue(s)；L183 未 staged；L163/L166 义务标签） | **未修复**（逐项复核实测） | L101/L108「3 issue(s)」**实测 1**；L94 仍 767/865（实测 769/870）；L104 仍「42 tests OK」（实测 32+42=74）；L38/L71 仍 16,011B→2,699B（shipped 2,988B，且与 L90 同行自相矛盾）；L183 仍写「当前为工作树修改、**未 staged**」（实测 FIX-353 两文件已在 stage 区）；L167 仍标「proposed EVD-1082」（实为 EVD-1082/1083 已落账、发布证据应为 EVD-1084/1085）；L170 仍标「proposed 全文」（快照**已**落盘）；L188 复跑义务未勾选 |
| **F-23**（演练零污染表 staged 28 → 建议补时点限定语） | **未修复（R1 已标「接受」——建议项）** | rollback-plan L170 仍为 `staged 文件数 28 → 28`、L191「staged 28 不变」，无「演练时点 = R0 staged 28」限定语。**零污染结论本身未被推翻**（该表是时点值，非本轮实测值）→ P3 维持 |

---

## 4. 维度一：门禁事实（本轮当场）

| 门禁 | R1 当场 | **R2 当场（我复跑）** | Δ |
|---|---|---|---|
| `check-archive-integrity` | FAIL exit 1（pending 1） | **PASS exit 0**（index 1213 / total 178） | ✅ 消解 |
| `check-release … candidate` | FAILED **2 issue(s)** | FAILED **1 issue(s)** | ✅ −1 |
| ├ `archive integrity` | FAIL | **PASS** | ✅ |
| ├ `unit tests` | PASS | **PASS**（exit=0，`SPG_RELEASE_GATE_TIMEOUT=600`） | — |
| ├ `hot fact source` | PASS | **PASS** | — |
| └ `execution gates → governance health` | FAIL（exit=1） | **FAIL（exit=1）** | 存量维持 |
| `check-governance` 计数 | 21 issues | **20 issues**（FAIL 面 = 28s ×1 advisory） | ✅ −1，**构成变化已归属**（W-2/W-3） |
| Check 30 V2 | 0 | **0**（两条豁免行以 `downgraded` 形态如实列出） | — |
| 全量 pytest | 30F / 3451P | **30F / 3451P / 1 skipped / 390 subtests**（858.70s） | — （0 新增） |

**门禁面结论**：R1 的「本版新引入门禁失败」（archive integrity）**已彻底消解并独立复现**；残余 FAIL = `governance health` **单一存量子门**（构成 = 1 advisory ERROR + 19 WARN，V2=0）。

---

## 5. 裁决点（任务指定）：governance health gate FAIL 的发布接受性

**事实对照（两版均以「当场值」计）**：

| 对照面 | 0.83.0 Gate 16 先例（`release-checklist-0.83.0.md` L80/L83/L107） | 0.84.0 本版终态（W-2/W-3） | 判定 |
|---|---|---|---|
| check-release 终态 | 17 门 = **16 PASS + 1 FAIL**；FAIL = execution gates 子面 2 项披露（含 governance health） | 17 门 = **16 PASS + 1 FAIL**；FAIL = execution gates 子面 **1 项**（仅 governance health） | **同级或更优** ✓ |
| issue 总数 | 21（存量口径，逐条归因） | **20** | **更优 −1** |
| FAIL 面构成 | 28o 残余 4E（**advisory ERROR**）+ 28s（advisory） + 28q/2/28n 族 WARN | **28s ×1（advisory）+ 19 WARN** | **更窄**（28o 降为 WARN 层）✓ |
| Check 30 V2 | 存量披露（RISK-051，×2 未消解） | **V2 violations = 0**（REL-078 走归档豁免 WARN + FIX-246 走活体行恢复 WARN，均带依据、非静默） | **更优** ✓ |
| 披露姿态 | 明文列为 RELEASE R0 F-1 义务并逐条归因；「**不得以旧值作新声明**」 | 已有逐条归因段（9 项）**但未达先例颗粒度**（Check 36 缺项 / Check 27 与实测相反 / stale 2-of-4 / 三处数值未刷新 / 标题 21≠20） | **未达标** ✗（见 §2） |
| 门禁地位声明 | 「存量披露（advisory/已接受），**非通过项**」 | 同口径声明在案（L137 ①） | ✓ |

**裁决**：**披露的「实质标准」达到并超过 0.83.0 先例**——issue 总数更少（20<21）、FAIL 面更窄（仅 1 条 advisory ERROR）、V2 全消解、`archive integrity` 已回归 PASS；**`governance health` 子门 exit=1 本身不构成发布阻断**（先例已两度接受同型，本项目对 advisory 面采用「披露发布」而非「清零发布」）。
**但「形式标准」未达标**：先例义务的落点是「M-2 以当场值为准、构成漂移逐条归因、**不得以旧值作新声明**」，而本版归因段**在自身收口之后**仍混用收口前数值（21、427、1537.6 KB）并把已消解的 Check 27 WARN 记为现存 → 该缺陷属**可确定性收口的文档义务**，不改变「接受 governance health FAIL」这一实质裁决。
**故 M-5 放行条件 = 走查 §8 的 L-1/L-2/L-4（限文本面，无需重跑门禁）**；一旦这些行改为当场值，**本版披露即同时满足实质与形式标准**，`governance health` FAIL 可照 0.83.0 先例接受。

---

## 6. 维度二：回滚能力 / 变更日志 / 版本号 / Feature Flag（R1 已通过面复核）

| 面 | 结论 | 依据 |
|---|---|---|
| 回滚方案存在且已验证 | **✓ 维持通过** | 15 步演练表在案（P-2~P-13）；P-3 `82 paths` / P-4 `98 paths` + `git diff --cached 2a15e59` 空证明；P-12 反向实证 `exit 1 / CONFLICT`；零污染三重指纹（staged 不变 / ls-files -u 0 / 临时目录已删）。真实 `<发布 tip>` 面为 M-5 期义务（先例同型）——**且 #18 已回填**（R1 F-15② 收口）→ R1 的「条件通过」条件已满足 |
| CHANGELOG 用户视角 | **✓** | `## [0.84.0] - 2026-09-19`（L5）；Added/Changed/Fixed/B-1~B-6/如实披露/Breaking=无/MINOR 依据齐 |
| Breaking changes 标注 | **✓** | 显式「无」+ VERSIONING L11/L38/L83 逐项反证（checklist 版本号决策节） |
| 版本 bump 完整性 | **✓** | check-version-consistency PASS（W-4）；blob 锚与 staged 一致（W-7） |
| Feature Flag / 灰度开关 | **✓** | F-1/F-2 双臂 + I-1~I-5 三层机检 + `behavior_profile.py` 守护测试（R1 已核，本轮抽样未见漂移）；checklist 隔离口径措辞合规（「隔离环境安装冒烟（环境变量重定向至临时目录）通过」） |
| 候选包完整性 | **✓** | `core/releases/0.84.0.json` = candidate / `events: []` / 10 载荷提交计数一致（W-10） |

---

## 7. 备注（约束性）

1. **C-01 的级别标注不一致**：Code Review 源报告 §5 判 **C-01 = P1**；plan-tracker L94 与 EVD-1085 记作「C-01/**P2** 残留登记 0.85.0 候选」。我**不**以该项阻断（其不改变 FAIL/WARN 判定、不影响 V2=0、不落在发布文档的对外陈述面），但账目应如实标级（P1），或在 DEC-214/risk-log 中显式登记为「P1 降级接受（理由：措辞真实性、判定功能不受影响）」。**禁止**在无降级依据的情况下改标级别。
2. **归档迁移缺一条自身证据行**：迁移动作（task+evidence 双迁 + 复跑 PASS）目前**只**由 checklist #16 与磁盘产物承载；`evidence-log.md` 无对应 EVD 行，也未记录 FEAT-035 语义要求的「ask 确认 → 执行 → 复跑」三拍。建议随后续证据行（或 M-5 发布证据 EVD）一并补记（含命令输出摘要）。**不**要求为它新增独立 EVD ID——除非 Coordinator 认为迁移属独立交付物。
3. **快照内容陈旧无机器兜底**：Check 35/28c 只校验 `session_date` 可解析，不校验内容与当前态一致（F-21 因此不被机检捕获）——本版如实暴露该口径缺口，建议登记为 0.85.0 候选（内容一致性校验），**不**要求本版修引擎。
4. **R1 结论 4 的约束维持**：`release-ledger` 于 M-5 commit 后 MUST 复跑（`--no-remote`，期望 `candidate_commit` 可由 git 派生）；tag 后 MUST 复跑 `check-release --lineage-mode released --release-commit <commit>` 与 `release-ledger --remote origin`。
5. **R1 结论 6 的约束在我复核下仍然成立**：本报告为 NEEDS_CHANGE，**R2 通过前不得推进 M-5**；`core/releases/0.84.0.json` 保持 candidate；35 staged 集保持原样（本轮零写盘已复核）。

---

## 8. 发现清单（R2）

### 8.1 阻断项（4 项 —— 全部为文档/证据面，无一是产品代码缺陷）

| ID | 级别 | 前轮来源 | 问题（事实） | 处置（可确定性收口，无需重跑门禁） |
|---|---|---|---|---|
| **L-1** | P1 | F-15 残留 | **checklist #14 行（L101）仍写「FAILED — 3 issue(s)」并按三项枚举 FAIL**（hot fact source / governance health / unit tests），L108 仍写「剩余 3 项 FAIL」——我已实测为 **1 issue(s)**，且 hot fact source 与 unit tests **均 PASS**。发布包**同时**持「已收口」(#16/#18) 与「仍 3 项 FAIL」(#14) 两种互相矛盾的陈述 | 把 #14 刷新为当场值（`FAILED — 1 issue(s)` exit 1，PASS 面 16 项，唯一 FAIL = governance health〔advisory 构成 + 先例〕），L108 同步刷新；#10/#14 的「archive integrity」行随 W-1 改为 PASS |
| **L-2** | P1 | F-18 未达标 + **新引入失真** | **governance health 归因段与当场实测相反/缺项**（§2）：① **Check 27 记「WARN ×1，归档迁移待执行」而实测 `[PASS] Archive integrity verified`**——迁移已执行（#16 自述亦然），该行把已消解 WARN 记为现存、把已完成动作写成待执行；② **Check 36 ×16 整族缺项**（20 项中的现存族）；③ stale 记 2/4（实测 RISK-036/039/046 10d + RISK-050 8d），理由「复评窗 09-30 未到」不适配 RISK-046/050；④ 标题与 ①（L114 标题、L137 ①）仍记 **21 issues**（实测 **20**）；⑤ 数值未刷新：14 → 实测 **428**（记 427）、28s → 实测 **1,540.5 KB**（记 1,540.3） | 逐项改当场值：标题/终值 21→**20**；⑧ 改为「Check 27 archive-integrity **已 PASS**（迁移执行后消解）」；补 **Check 36 ×16**（R3 跨实体引用族，历史）；stale 补为 **4 项并逐项列 ID+天数**；14→428；28s→1,540.5 KB。**同时收口 R0 F-07**（Gate 10「均逐项列明」的表述与枚举对齐） |
| **L-3** | P1 | F-17 残留 | **checklist L144 仍引用不存在的 `DEC-213⑧`**（decision-log 全文件 0 命中；DEC-213 全文仅 ①~⑦）并附过期表述「EVD 入账随 R1」。DEC-214 + DEC-214①（勘误）已在案 → 发布包内**成文引用一个不存在的决策条目**，正是 R1 F-17 的第三面 | L144 改为指向 **DEC-214**（superseding DEC-203 半面 + 生效条件=走链 + 勘误行 DEC-214①）；「EVD 入账随 R1」→「EVD-1085 已入账」；L137 ① 中 `DEC-213⑧ 登记` 同步改为 DEC-214 |
| **L-4** | P1 | F-15 附面 / F-20 残留 | **归档迁移证据未入账 + M-8 义务清单未更新（3 条过期陈述仍在）**：① 迁移动作无 EVD 行 / 无 ask-确认与命令输出留痕（§7 备注 2）；② checklist L191 仍写「`migrate --auto --dry-run` 已实测**无可归档数据 / 零写操作**」（与已执行的迁移相反）；③ L167 仍写「proposed EVD-1082」（EVD-1082/1083 已落账、发布证据为 EVD-1084/1085）+ 复选框未勾；④ L170（M-7 快照）仍写 proposed + 未勾，而快照**已落盘**；⑤ L183 仍写 FIX-353 两文件「未 staged」（**已在 stage 区**）；⑥ **#17（L104）仍为 M-1 期「32 failed / 3441 passed」**且自述「不预填复跑结论」——我已独立复跑得 **30F/3451P**（858.70s，0 新增），L188 义务仍未勾 | 补一条证据行（迁移 + 复跑，或并入 M-5 发布证据行）；L191 改为「已执行：1 task〔FIX-246〕+ 1 evidence〔EVD-892〕→ `v0.1.0~v0.82.0-incremental-20260919-1.md`，`check-archive-integrity` PASS」；L167/L170/L183/L188 按实际态勾选并改写；#17 写入本轮实测值（**30 failed / 3451 passed / 1 skipped，858.70s，30 = 既有环境族〔无 WSL 发行版 + 活体耦合〕，0 新增**） |

### 8.2 非阻断项（随 L-1~L-4 同批刷新即可）

| ID | 级别 | 问题 | 判定 |
|---|---|---|---|
| **L-5**（承 F-21） | P2 | `session-snapshot.md` 内容层陈旧：「REL-080-RELEASE-R0 = NEEDS_CHANGE → 6 阻断项收口 → **R1 待发起**」、FIX-354 **进行中**、F-04 **待跑**、EVD-1084「随 R1」、**Check 30 V2 ×2**、通篇 **0 次 FIX-355**、下一步仍写「R1 复审」 | 非提交前硬阻断；但快照是**下次会话唯一恢复入口**，其失实会直接误导后续会话 → MUST 与 L-1~L-4 同批刷新（并补 FIX-355/归档迁移/门禁终态） |
| **L-6**（承 F-22） | P3 | checklist 其余精度项（L38/L71 16,011B→2,699B 时点值；L104「42 tests OK」实测 74；L94 767/865 实测 769/870；L112 标题「staged 33」实测 35） | 随批刷新 |
| **L-7**（承 F-23） | P3 | 演练零污染表 staged `28 → 28` 未加时点限定语 | 维持「接受 + 建议」；本批顺带补限定语即可 |
| **L-8**（新，本报告） | P3 | 级别标注不一致：C-01 源判 **P1**，plan-tracker/EVD 记 **P2** | 见 §7 备注 1（如实标级或登记降级依据） |

### 8.3 本轮复核确认的通过面（无需重做）

`archive integrity` PASS / `unit tests` 闸门 PASS（exit=0）+ 全量 0 新增失败 / `hot fact source` PASS / release docs PASS / release lineage candidate 边界 PASS / gate sequence PASS / one dot zero blockers PASS / loop fuse block PASS / changelog PASS / loop runtime claim（semantic + identity PASS，inventory `2613892f…`，851/851 parsed）/ verify + e2e check + dsh upgrade regression（隔离 temp-DSH_HOME 冒烟）PASS / Check 31 PASS / Check 32 PASS（113 记录 0 invalid）/ Check 34 PASS（37/37）/ Check 35 PASS / Check 37~39 PASS / FIX-355 七面入账 + blob 锚未变 / DEC-214 + 勘误在案 / 归档落地三文件核验一致 / 35 staged 无夹带。

---

## 9. 硬门槛逐项裁决

| 硬门槛 | 阈值 | 本次事实 | 判定 |
|---|---|---|---|
| 发布检查清单全部 PASS | = 100% | 门禁面：`check-release` **FAILED 1 issue(s)**（唯一 = governance health，**先例已接受面**，我已裁决可接受）；**文档面：checklist 仍以 1 组与实测相反的数值自述（L-1/L-2）+ 引用不存在条目（L-3）+ 义务清单 3 条过期 + 迁移证据缺失（L-4）** | ✗ **未满足**（文档面；门禁面满足） |
| 回滚方案存在且已验证 | = 已验证 | 隔离副本演练 15 步 + 我独立复算关键路径（R1）在案；**#18 本轮已回填** ⇒ R1 的条件解除；真实 tip 面 = M-5 期义务（先例同型） | **✓ 满足** |
| CHANGELOG 用户视角完整 | 关键段全覆盖 | Added/Changed/Fixed/B-1~B-6/披露/Breaking=无/MINOR 依据全覆盖 | ✓ |
| breaking changes 已标注 | 100% | 显式「无」+ VERSIONING 逐项反证 | ✓ |
| Feature Flag 关闭验证 | 全部通过 | F-1/F-2 双臂 + I-1~I-5 三层机检 + 守护测试 | ✓ |
| P0 任务完成 | — | AUDIT-154 + FEAT-032~040 九任务全 ✅；REL-080 行 ⏳（待 M-5） | ✓（发布任务本身待 M-5） |
| 版本 bump 完整性 | 全平面 | check-version-consistency PASS；blob 锚与 staged 一致 | ✓ |

---

## 10. 审查结论

**NEEDS_CHANGE（round=R2）｜unresolved_blockers=4**

**本轮与 R1 的实质差别（必须记录）**：R1 的 3 项阻断中，**门禁层面已全部消解**——`archive integrity` **FAIL→PASS**（我独立复现，R1 的 2 issue(s)→**1 issue(s)**）、FIX-355 七面入账**逐面经我实测齐备**（含机录 round 0 的 `APPROVED_WITH_NOTES/0`）、DEC-214 + 勘误行**已在案**、`unit tests` 闸门 PASS + 全量 **0 新增失败**（30F/3451P，858.70s 我实跑）。**残余 4 项阻断全部落在发布文档/证据面**，且均可在**不重跑任何门禁**的前提下确定性收口。

**阻断项 4 项**：
1. **L-1**（承 F-15）checklist #14/L108 仍自述「**3 issue(s)** / 剩余 3 项 FAIL」（实测 **1**）、#10/#14 未反映 archive integrity 回归 PASS；
2. **L-2**（承 F-18 + 新引入）governance health 归因段与当场实测相反/缺项：**Check 27 记为现存 WARN 而实测 PASS**、**Check 36 ×16 缺项**、stale 2-of-4、标题与终值仍 21（实测 20）、14/28s 数值未刷新；
3. **L-3**（承 F-17 第三面）checklist L144 仍引用**不存在的 `DEC-213⑧`**（应为 DEC-214）+ 过期「EVD 入账随 R1」；
4. **L-4**（承 F-15 附面 / F-20）归档迁移**无自身证据行与 ask-确认留痕**、L191 仍写「无归档数据」、L167/L170/L183/L188 义务标签与勾选状态过期、**#17 仍为 M-1 期 32F/3441P**（本轮实测 30F/3451P）。

**同批必收（非阻断）**：L-5（session-snapshot 内容层陈旧，含「V2 ×2」与「R1 待发起」）、L-6/L-7/L-8（P3 精度与标级）。

**裁决点（任务指定）答复**：**governance health gate FAIL 的披露「实质标准」达到并超过 0.83.0 Gate 16 先例**——20 < 21 issues、FAIL 面仅 1 条 advisory ERROR（28s）、V2 全消解、archive integrity 已 PASS、check-release 同为「16 PASS + 1 FAIL(execution gates)」；**该子门 exit=1 本身不阻断发布**（project precedent：advisory 面「披露发布」）。**「形式标准」（先例明文的「以当场值为准、不得以旧值作新声明」）未达标**，其载体即 L-2；**修完 L-1~L-4 后，本版披露即同时满足实质与形式标准，M-5（commit + transition + tag + push）可放行**——此为**文本面收口**，不涉及产品代码、不涉及 blob 锚、不需重跑门禁。

**约束性备注（binding notes）**：
1. **L-1~L-4 收口前不得推进 M-5**；`core/releases/0.84.0.json` 保持 `candidate`；35 staged 集保持原样（**禁止**为改文档而改动 `review_domain.py`/`test_review_closure_legacy.py`——blob 锚 `e681bfa…`/`610c2ef…` 是 Code Review 结论的有效性前提，若变更则须重跑该审查 V-1~V-16）。
2. **FIX-246 任务行已归档，不得为「消除 WARN」做任何回退或改写**：当前 Check 30 以 `[V2] … downgraded` 形态如实保留 REL-078 与 FIX-246 两条豁免行（V2 violations = 0）——这正是 DEC-214 与 DEC-199 要求的口径（**可见性保留、非静默**）。
3. **C-01（源判 P1）** 的「登记 0.85.0 候选」我**接受**（不改变判定、不影响 V2=0），但 MUST 在 plan-tracker/EVD 中如实标级为 P1 或显式登记降级依据（L-8）。
4. `governance health` 子门 exit=1、Check 28s advisory、Check 36/30c/28q/stale 各族属**存量/先例已接受面**，本报告**不**要求修复，只要求**如实枚举**（L-2）。
5. `release-ledger` 于 M-5 commit 后 MUST 复跑（`--no-remote`）；tag 后 MUST 复跑 `check-release --lineage-mode released --release-commit <commit>` 与 `release-ledger --remote origin`。

**R3 复审范围（重 spawn 同一 Release Reviewer，注入本报告路径）**：仅需复核 **L-1~L-4 的文本收口**（逐条标注「已修复/未修复/新引入」）+ L-5~L-8 刷新；**门禁面无需重跑**（本轮 10 项复跑值构成 R3 通过基线；若 staged/HEAD 或 FIX-355 blob 锚发生任何变化，则 R3 MUST 重跑 W-1/W-2/W-3/W-4/W-5/W-7）。

---

*审查方：Release Reviewer Agent（独立复审，只读）｜审查对象：0.84.0 候选（HEAD `b537976` + 35 staged 文件）｜前轮：`review-REL-080-RELEASE-R1`（NEEDS_CHANGE/3）｜结论：**NEEDS_CHANGE / round=R2 / unresolved_blockers=4**｜机录义务：Coordinator 以 `review-record` 持久化本结论（Reviewer 不写治理状态；证据行 round=R2 自动 next_round）*
