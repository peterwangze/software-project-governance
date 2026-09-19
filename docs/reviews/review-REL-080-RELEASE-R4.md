# 发布审查报告 — REL-080（0.84.0 候选就绪状态）RELEASE 半面 R4（T2 授权终验轮）

**结论：NEEDS_CHANGE ｜ round=R4 ｜ unresolved_blockers=2 ｜ M-5 不予放行**

- **T2 授权链（本报告头部必载）**：R3 = BLOCKED（复审 fuse 达限，`review-REL-080-RELEASE-R3.md` §协议口径）→ Coordinator 按 T2 escalation 提请用户 → **用户裁决「R4 终验后放行（推荐）」（2026-09-19）**→ 本轮 = T2 授权下的等价验证终验轮（R3 §5 预设路径：「收口后可经 R4 同 Reviewer 终验关闭」）。**放行前提 = 「全部文本面收口」经本轮逐条确认**。
- **前轮引用**：`docs/reviews/review-REL-080-RELEASE-R3.md`（round=R3，BLOCKED，`unresolved_blockers=4`：B-1~B-4；同批 N-1/N-2 + L-5~L-8）；R2（NEEDS_CHANGE/4，L-1~L-4）；R1（NEEDS_CHANGE/3）；R0（NEEDS_CHANGE/6）
- **审查方**：Release Reviewer Agent（独立终验；只读——写盘足迹仅本文件；复核期 `git status --porcelain --untracked-files=all` = **staged 37 / untracked 0 / 未暂存修改 0**，本报告落盘后 untracked +1，由 Coordinator 决定是否入库）
- **审查对象**：0.84.0 候选 = `HEAD b537976` + **37 个 staged 文件**（R3 期 36 → +`docs/reviews/review-REL-080-RELEASE-R3.md`〔R3 报告入库〕；无其他增量）+ `docs/release/release-checklist-0.84.0.md`（R3 后收口文本）+ `docs/release/{feature-flags,rollback-plan}-0.84.0.md` + `project/CHANGELOG.md [0.84.0]` + `core/releases/0.84.0.json`（`lifecycle_state=candidate` 保持）
- **审查日期**：2026-09-19 ｜ **审查性质**：T2 终验 = R3 四阻断（B-1~B-4）+ N-1/N-2 + L-5~L-8 **逐条当场复核**，并对 Coordinator 收口申报做**申报↔实态一致性**核对——**不盲批申报**
- **门禁面**：未重跑（R2 基线判定面未被触碰——见 §0 W-4/W-5；R2 10 项复跑值继续构成通过基线）

---

## 0. 基线一致性抽查（只读 —— 本轮当场值）

| # | 核验（只读） | 当场结果 | 判定 |
|---|---|---|---|
| W-1 | `git rev-parse HEAD` | `b537976d31f173ad2f2c69cc14888f51a1acbf3a` | 与申报「HEAD b537976 未动」**一致** ✓ |
| W-2 | `git status --porcelain --untracked-files=all` | **staged 37 / untracked 0 / 未暂存修改 0**；staged 构成 = R3 期 36 + `A docs/reviews/review-REL-080-RELEASE-R3.md`，其余逐项同 R3 W-2 | 与申报「staged 36→37〔+R3 报告〕」**一致** ✓；**无夹带** ✓ |
| W-3 | FIX-355 blob 锚（`ls-files -s` + `hash-object` + `diff` index↔worktree，全路径 `skills/…/infra/`） | `checks/review_domain.py` = **`e681bfa36866e8c0606a5e4cd37764bc15736fdf`**；`tests/test_review_closure_legacy.py` = **`610c2efcf174157e09b061d1c6c8b9d3fbba4642`**；索引 blob = 工作树 blob（diff 空） | 与 R2 W-7 / R3 W-3 **逐字节一致** ✓ → **Code Review 结论有效性前提未失效** ✓ |
| W-4 | R3 报告（08:29:13）后写入窗（mtime 实测） | 仅 4 文件被写：`evidence-log.md` 08:29:41（1,579,122 B）→ `release-checklist-0.84.0.md` / `plan-tracker.md` 08:30:46 → `session-snapshot.md` 08:31:04；**`rollback-plan-0.84.0.md` 仍 03:31:04（零写入）**、`feature-flags` 02:29:12、`decision-log` 06:14:38 未动 | 门禁判定面（产品代码/hooks/SKILL/投影/fixture/测试）**零触碰** ✓；但 rollback-plan 未写 = **L-7 未收口的直接物证**（§2） |
| W-5 | 治理记录抽查 | `decision-log.md` L155 = **DEC-214**、L156 = **DEC-214①（勘误）**；全表 **无 `DEC-213⑧`**（DEC-213 仅 ①~⑦）；`evidence-log.md` L2277/2278/2281/2286/2291 = **EVD-1082/1083/1084/1085/1086** 全部落账（EVD-1085 记「P1×1 C-01 + P2×4」；EVD-1086 记归档迁移 + check-governance 21→20 + check-release 2→1） | B-2/B-3 载体核验依据 ✓；**L137① 的 `DEC-213⑧` 引用无对应条目 = 引用不存在的决策条目，条件仍成立** ✗ |

---

## 1. R3 四阻断逐条比对（MUST —— 不得盲批）

| R3 项 | R3 要求 | **R4 判定** | 实证（当场字符串） |
|---|---|---|---|
| **B-1**（L137① 三值） | L137① 全块改写：`1,534.4 KB`→新值；`当场终值 = 21 issues`→**20**；`2 stale risks`→**4 stale（含复评窗日期）**；`系 21 计数`→**20**；句末→「**20 issues** 存量披露发布；本版 **20 < 21** 且 V2 消解」 | **❌ 未收口（4 处残留 3 处）** | L137① 当场文本：「Check 28s（`evidence-log.md` **1,541.8 KB**…）」✓（字节数已刷为 R3 时点值）＋「收口后 check-governance 当场终值 = **21 issues**（构成：… + **2 stale risks**）——…exit 1 系 **21 计数**含 WARN 族（**0.83.0 Gate 16 同型先例**：**21 issues** 存量披露发布；本版**构成 ≤ 同型**且 V2 已消解两项）」——**21/2 stale/21 计数/≤同型 四处仍为收口前旧值**，与同文件 L101（20 issues）/L108（20 issues）/L114（标题「governance health **20 issues** 逐条归因」+ ①⑦ 当场值）/L147（终态构成 = **20 issues**）**并列互斥**；先例义务「不得以旧值作新声明」**仍未达成**。**申报「归因段终值 20（R3 所指系 L137① 旧块，已同步）」与实态不符——L137① 未同步** |
| **B-2**（DEC-213⑧） | L137① 中 `DEC-213⑧ 登记` → `DEC-214 / DEC-214① 登记`（L144 主目标 R3 期已收口） | **❌ 未收口（L137① 半）** | L137① 当场文本仍含「**+ DEC-213⑧ 登记（RISK-051 复评：×2→已消解）**」；W-5 实证 decision-log **不存在 DEC-213⑧**（该语义内容实际承载于 DEC-214 尾部「RISK-051 复评：×2→已消解」——引用对象错位）。**「发布包内成文引用一个不存在的决策条目」条件仍成立**。L144 =「DEC-214 + DEC-214① 勘误」✓（维持收口）。**申报「L137① 相邻文本同步」与实态不符** |
| **B-3**（M-8 义务清单 5 处） | L192/L168/L171/L187/L188/L189 按实态勾选改写 | **✅ 全收口（6/6 行）** | **L192** = `[x]`「归档：…→**已执行**（用户 ask 确认「执行归档（推荐）」；FIX-246/EVD-892 入册；check-archive-integrity PASS；EVD-1086）」✓（与 EVD-1086 逐值一致，旧「无可归档数据/零写操作」已消失）；**L168** = `[x]`「EVD 已落账（**EVD-1082~1086** 发布链 + FIX-352~355 修复链）+ DEC-213/214」（W-5 五实号全在案）✓；**L171** = `[x]`「已落盘（session_date 2026-09-19…）」✓（尾巴「R2 后待终态刷新随 M-8」已过时——快照 08:31:04 已终态刷新，P3 微瑕）；**L187** = `[x]` execution-packet ✓；**L188** = `[x]`「已 staged（36 集内）」✓（计数差 1 见 §3 O-1）；**L189/L190** = `[x]`「R2 Reviewer 独立复跑 30F/3451P/1 skipped（858.70s）」/「unit tests 预算项已收口（R2 复核 PASS）」+ `[ ]` release-ledger M-5 后义务（保留未勾**正确**）✓ |
| **B-4**（inventory 值） | `2df0071d…/848` → 改回 R2 记录值 `2613892f…/851`（来源标明） | **✅ 已收口** | L101 =「loop runtime claim gate（semantic + identity PASS，inventory **`2613892f…`**，candidates **851（R2 报告 W-4 复核值）**）」——与 R2 报告 W-4（`inventory=2613892f…; candidates=851; parsed=851`）**逐值一致 + 来源显式标明** ✓；全仓 grep：`2df0071d` 仅存于 R3 报告引用性提及，checklist **已无此值** ✓；snapshot L18 亦记「inventory 值以 R2 报告 W-4 复核值为准（2613892f…/851）」✓ |

**小结**：R3 的 4 项阻断——**B-3 / B-4（=N-2）全收口；B-1 / B-2 的残项全部集中在同一行 L137①**（该行 R2 期即被 L-2/L-3 点名，R3 期再次点名，R4 终验仍残留）。

---

## 2. N-1/N-2 + L-5~L-8 刷新核验

| 项 | R3 要求 | **R4 判定** | 实证 |
|---|---|---|---|
| **N-1**（L101 PASS 面计数自洽，P3） | 「二者择一并说明口径」使表头计数 = 枚举名数 | **❌ 未收口** | L101 表头 =「**PASS 面（16 门 PASS + 1 门预算覆盖 PASS = 17 面，R2 复核）**」，其后枚举 **18 名**（version consistency / release fact source / hot fact source / runtime readiness / first session measurement / governance pack / agent adapters / projection sync / cross references / archive integrity / release docs / release lineage / gate sequence / one dot zero blockers / changelog / loop runtime claim gate / dsh upgrade regression / unit tests）——**17 面 ≠ 18 名，差 1 的不自洽形态未消除**（仅计数标签措辞更换）。**申报「17 项→…自洽」与实态不符**。维持 R3 定级 P3（不改变 FAILED 1 issue(s) 事实） |
| **N-2**（inventory 可溯源） | 同 B-4 | **✅ 已收口**（=B-4） | 见 §1 |
| **L-5**（快照重写，MUST 同批） | 整体刷新至 R2/R3/T2 期 | **✅ 已收口** | mtime 08:31:04（R3 后重写）；`session_date: 2026-09-19` ✓；L1/L8/L12 =「R3 BLOCKED/T2 升级中」✓；L8/L11 =「20 issues（FAIL 面仅 28s advisory；V2 violations 0）」✓；L9/L10 = FIX-352~355 + EVD-1082~1086 + 归档迁移全记录 ✓；L26 =「C-01 豁免行措辞分流（**源判 P1**）」✓；R0 期旧内容（R1 待发起 / FIX-354 进行中 / F-04 待跑 / V2 ×2 / structural 424 / M-6 归档跳过）**零残留** ✓。（微瑕：L13/L25「36 staged」vs 当场 37，见 §3 O-1） |
| **L-6**（P3 精度项） | 逐 token 刷新 | **⚠ 部分收口（2/4）** | ✓ L38/L71 =「2,699B（M-2 期口径 16,011B→R2 期实测 2,699B——FEAT-037 投影幂等后）」时点限定成立；✓ L104 =「两文件合计 **74** tests OK——32+42」。**✗ L94 仍「canonical 767 / actual 865」**（R2 实测 769/870；grep 实证 769/870 在 checklist 中不存在）——**申报「767/865→769/870 时点」与实态不符**；△ L112 =「staged **36** 项构成」（当场 37，差 1 见 O-1） |
| **L-7**（P3 演练表时点限定语） | `rollback-plan` 补「staged 28 = 演练时点」限定 | **❌ 未收口** | **W-4 物证：`rollback-plan-0.84.0.md` mtime 仍 03:31:04——R3 后零写入**。L162 =「真实仓库当前持有 **28 个 staged 候选文件**」、L170 =「staged 文件数 28→**28** ✓ 不变」、L191 =「零（指纹前后同值；**staged 28 不变**）」——三处均无时点限定语。**申报「演练零污染表 staged 28 加时点限定（06:xx 快照）」与实态不符**。维持 R3 定级：零污染结论本身不被推翻（时点值）→「接受 + 建议」P3 |
| **L-8**（C-01 标级） | 如实标 P1 或登记降级依据 | **✅ 已收口** | plan-tracker L94 =「C-01（**源判 P1**）/P2 残留登记 0.85.0」——与 EVD-1085（L2286「P1×1 C-01 …+ P2×4」）及源报告 review-FIX-355-CODE-R0 的 P1 判级**一致** ✓；snapshot L26 同口径 ✓ |

---

## 3. 本轮新发现（R3→R4 窗口）

| ID | 级别 | 问题（事实） | 处置 |
|---|---|---|---|
| **O-1** | P3 | **staged 计数自指差 1**：L112「staged **36** 项构成」、L188「已 staged（**36 集内**）」、snapshot L13「commit（**36 staged**…）」/L25「staged **36** 原样保持」——当场 staged = **37**（R3 报告已入 index，W-2）。构成描述未含 R3 报告自身 | 统一刷为「37（含 R3 审查报告；R4 报告去留由 Coordinator 决定——入库则 38）」，或补「不含各轮审查报告自身」口径说明 |
| **O-2** | P3 | **evidence-log 字节值再漂移**：L137① 写「1,541.8 KB」（= R3 报告实测 1,578,830 B 时点值）；当场 = **1,579,122 B = 1,542.1 KB**（Δ +292 B，写入时刻 08:29:41 = R3 报告落盘后的结论机录行）。L137① 持「本版收口后终态 2026-09-19」时点限定、值可溯源 R3 报告 → 陈述本身不失实 | P3 时点备注：M-5 期以「当场值」口径引用时 MUST 刷新（28s 为 advisory，不阻断） |
| **O-3** | **程序性（放行前提）** | **收口申报与实态系统性偏差**：9 项申报中 **5 项与实态不符**——B-1（称「已同步」，实未同步）、B-2 之 L137① 半（称「相邻文本同步」，实未同步）、N-1（称「自洽」，实差 1）、L-6 之 767/865 半（称「已改」，实未改）、L-7（称「已加限定」，文件零写入）。**T2 用户裁决的放行前提（「全部文本面收口」）未达成** | 本报告 §5 最小收口清单逐行落笔后走 R5 终验（同 Reviewer，注入本报告），或由用户重新裁决 |

---

## 4. 硬门槛逐项裁决（本轮当场）

| 硬门槛 | 阈值 | 本次事实 | 判定 |
|---|---|---|---|
| 发布检查清单全部 PASS | = 100% | **门禁面维持满足**（R2 基线：check-release candidate FAILED 1 issue(s) = governance health 先例已接受面；本轮判定面零触碰——W-3/W-4）；**文档面未满足**：B-1/B-2 残项集中于 L137① 一行（收口前旧值 + 不存在条目引用） | ✗ **未满足**（文档面） |
| 回滚方案存在且已验证 | = 已验证 | 隔离副本 15 步演练 + R1 独立复算在案（本轮零触碰）；真实 tip 面 = M-5 期义务（先例同型）；L-7 仅为时点限定语缺失，不推翻演练事实 | ✓ **满足** |
| CHANGELOG 用户视角完整 | 关键段全覆盖 | `[0.84.0] - 2026-09-19`（R2 已核，本轮无触碰面） | ✓ |
| breaking changes 已标注 | 100% | 显式「无」+ VERSIONING 反证（R2 已核） | ✓ |
| Feature Flag 关闭验证 | 全部通过 | F-1/F-2 双臂 + 三层机检 + 守护测试（R2 已核，本轮无触碰面） | ✓ |
| P0 任务完成 | — | AUDIT-154 + FEAT-032~040 全 ✅；REL-080 行 ⏳（待 M-5） | ✓ |
| 版本 bump 完整性 | 全平面 | check-version-consistency PASS（R2）；blob 锚逐字节未变（W-3）；37 staged 无夹带（W-2） | ✓ |

---

## 5. 结论与最小收口清单

**结论：NEEDS_CHANGE（round=R4，T2 授权终验轮）｜unresolved_blockers=2**

**阻断项（2，均集中于 checklist L137① 一行——R2 L-2/L-3 → R3 B-1/B-2 → R4 三轮同源残项）**：
1. **B-1′（承 R3 B-1）**：L137① 仍以收口前数值自述——「当场终值 = **21 issues**」「**2 stale risks**」「系 **21 计数**」「本版**构成 ≤ 同型**」，与同文件 L101/L108/L114/L147 的当场值（**20** issues / **4** stale risks）**并列互斥**；先例义务「不得以旧值作新声明」未达成。
2. **B-2′（承 R3 B-2）**：L137① 仍成文引用**不存在的 `DEC-213⑧`**（decision-log 实证仅 ①~⑦；该语义实际承载于 DEC-214 尾部——引用对象错位）。

**M-5 放行裁决**：**不予放行**。T2 用户裁决「R4 终验后放行」的前提 = 本轮确认「全部文本面收口」；实测 2 项阻断残留 + 5 项申报与实态不符（O-3）→ **前提不成立**，`core/releases/0.84.0.json` 保持 `candidate`。DEC-204 预授权与 T2 裁决**均不构成**对本轮审查结论的覆盖——放行必须以终验通过为条件，这是 R3 §5 预设路径的原文语义。

**最小收口清单（全部为行级文本面；不触碰 blob 锚 / 产品代码 / 门禁判定面 / staged 集构成，无需重跑任何门禁）**：
1. **L137① 整块改写**（一处落笔消除 B-1′+B-2′）：「1,541.8 KB」可保留（建议按 O-2 刷新为当场值或标注时点）；「`+ DEC-213⑧ 登记`」→「`+ DEC-214 登记（RISK-051 复评：×2→已消解——DEC-214 尾部在案）`」；「当场终值 = **21 issues**」→「**20 issues**（构成：28s ×1 advisory + 28n/28o God-module 族 + 14×428 structural + 30×29 WARN + 30c ×2 + 28q ×4 + **4 stale risk〔RISK-036/039/046 复评窗 09-30、RISK-050 10-31〕** + 36×16 + Check 27 已 PASS）」；「系 21 计数」→「系 20 计数」；句末「21 issues 存量披露发布；本版构成 ≤ 同型」→「**20 issues** 存量披露发布；本版 **20 < 21** 且 V2 消解」。（与 L114 归因段十类构成对齐，勿再自造简版构成）
2. **L94**（L-6 残项）：补时点限定「（M-2 期值；R2 复核 canonical 769 / actual 870）」或刷为 R2 复核值。
3. **L101**（N-1 残项）：PASS 面表头计数与 18 名枚举对齐（建议「PASS 面 16 门 + 执行闸门子面 verify/e2e/unit tests 全 PASS〔unit tests 系预算覆盖收口〕= 18 项枚举」，与 R2 W-4 口径一致），禁止再次只换标签不改差值。
4. **rollback-plan L162/L170/L191**（L-7 残项）：三处「staged 28」补时点限定语「（演练时点 = FIX-354 期快照，2026-09-19 06:xx；当前候选集已演进至 37，属独立变更——零污染结论按时点值成立）」。
5. **O-1 同批**：L112 / L188 / snapshot L13/L25 的「36」→「37（含 R3 审查报告；R4 报告去留由 Coordinator 决定）」。
6. **L171 尾巴同批**：删「R2 后待终态刷新随 M-8」（快照已于 08:31:04 终态刷新，该尾巴已失实）。

**收口后的路径（由 Coordinator/用户裁决，Reviewer 不决定）**：以上全为文本面修改——收口后经 **R5 终验轮（同 Reviewer，注入本报告）** 关闭；鉴于 R4 残留集中单行、修复面极小，R5 范围可限定为「L137① + §5 清单 2~6 项逐行比对 + W 系基线复核」，无需重走全量。

---

## 6. 本轮复核确认的通过面（无需重做）

R2 门禁基线全维持（archive integrity PASS / unit tests 闸门 PASS + 全量 0 新增失败 30F/3451P/858.70s / hot fact source PASS / release docs / release lineage candidate / gate sequence / one dot zero blockers / changelog / loop runtime claim semantic+identity / verify + e2e + dsh upgrade regression 隔离冒烟 / Check 30 V2 violations = 0 / Check 27 PASS）；**B-3 六行义务清单全收口**；**B-4 = 2613892f…/851 来源标明且 `2df0071d` 全仓清除**；**L-5 快照终态重写零旧内容残留**；**L-8 C-01 源判 P1 三面一致**；**blob 锚 `e681bfa…`/`610c2ef…` 逐字节未变（Code Review 有效性前提存续）**；**37 staged 无夹带、门禁判定面零触碰**；DEC-214/214① 与 EVD-1082~1086 载体齐备。

## 7. 约束性备注（binding notes）

1. **M-5 不予放行**；`core/releases/0.84.0.json` 保持 `candidate`；**37 staged 集保持原样**——禁止触碰 `checks/review_domain.py` / `tests/test_review_closure_legacy.py`（锚 `e681bfa…`/`610c2ef…` 是 Code Review 结论有效性前提，本轮已复核存续）。
2. 本轮 NEEDS_CHANGE **仍属文档面单行子集**：不撤销 R2 门禁面结论，不构成「产品代码不可发布」判断；风险性质 = 「L137① 披露行陈述与当场事实/治理记录不符」+「放行前提申报未兑现」。
3. ** Coordinator 在向用户呈现 R4 结果时 MUST 如实转述 O-3（5/9 项申报失实）**——不得以「均为 P3 小项」弱化；T2 授权前提未达成本身即是用户裁决所需信息。
4. FIX-246 归档行不得为消除 WARN 回退改写（DEC-214/DEC-199 口径维持）。
5. M-5（若后续放行）义务维持 R3 §7-5 原文：commit 后复跑 `release-ledger --no-remote`；tag 后复跑 `check-release --lineage-mode released --release-commit <commit>` 与 `release-ledger --remote origin`。
6. **写盘足迹声明**：本报告为本次审查**唯一**写盘产物（新增 `docs/reviews/review-REL-080-RELEASE-R4.md`；未修改任何 staged 文件；复核期 staged 37 / untracked 0 / unstaged 0 已留痕 W-2，落盘后 untracked +1）。

---

*审查方：Release Reviewer Agent（独立终验，只读）｜审查对象：0.84.0 候选（HEAD `b537976` + 37 staged 文件）｜授权链：R3 BLOCKED → T2 用户裁决「R4 终验后放行」（2026-09-19）→ 本轮｜前轮：`review-REL-080-RELEASE-R3`（BLOCKED/4）｜结论：**NEEDS_CHANGE / round=R4 / unresolved_blockers=2（B-1′ L137① 旧值互斥；B-2′ DEC-213⑧ 不存在条目引用）**｜机录义务：Coordinator 以 `review-record` 持久化本结论（round=R4；Reviewer 不写治理状态）*
