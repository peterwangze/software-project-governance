# 发布审查报告 — REL-080（0.84.0 候选就绪状态）RELEASE 半面 R5（限定范围终验轮）

**结论：NEEDS_CHANGE ｜ round=R5 ｜ unresolved_blockers=1（程序性——T2 放行前提未达成；R4 两项实质阻断 B-1′/B-2′ 已全收口）｜ M-5 不予放行（本授权链下）**

- **T2 授权链（本报告头部必载）**：R4 = NEEDS_CHANGE（`unresolved_blockers=2`：B-1′/B-2′ 均集中 checklist L137① 单行；`review-REL-080-RELEASE-R4.md` §5）→ Coordinator 完成 R4 后修复并向用户如实转述 O-3（5/9 项申报失实）→ **用户裁决「R4 终验后放行」→ R4 §5 预设路径：「收口后经 R5 终验轮（同 Reviewer，注入本报告）关闭；R5 范围限定为『L137① + §5 清单 2~6 项逐行比对 + W 系基线复核』」**→ 本轮 = 该限定范围终验。**放行前提 = R4 §5 六项清单「全部文本面收口」经本轮逐行确认——实测未达成（见 §3 O-4）**。
- **前轮引用**：`docs/reviews/review-REL-080-RELEASE-R4.md`（round=R4，NEEDS_CHANGE，`unresolved_blockers=2`：B-1′/B-2′；P3 = N-1/L-6/L-7/O-1 + O-1/O-2/O-3）；R3（BLOCKED/4）；R2（NEEDS_CHANGE/4）；R1（NEEDS_CHANGE/3）；R0（NEEDS_CHANGE/6）
- **审查方**：Release Reviewer Agent（同 Reviewer 连续第 6 轮；只读——写盘足迹仅本文件；复核期 `git status --porcelain --untracked-files=all` = **staged 38 / untracked 0 / 未暂存修改 0**，本报告落盘后 untracked +1，由 Coordinator 决定是否入库）
- **审查对象**：0.84.0 候选 = `HEAD b537976` + **38 个 staged 文件**（R4 期 37 → +`docs/reviews/review-REL-080-RELEASE-R4.md`〔R4 报告入库〕；无其他增量）+ R4 后修复写入的 `docs/release/release-checklist-0.84.0.md` / `docs/release/rollback-plan-0.84.0.md`（均 08:50:50）+ `core/releases/0.84.0.json`（`lifecycle_state=candidate` 保持）
- **审查日期**：2026-09-19 ｜ **审查性质**：限定范围终验 = R4 §5 六项清单逐行比对（不盲批申报——申报↔实态逐项核对）+ W 系基线抽查；**不重跑任何门禁**（判定面零触碰，见 W-4′）
- **门禁面**：未重跑（R2 基线判定面未被触碰——W-3/W-4′ 实证；R2 10 项复跑值继续构成通过基线）

---

## 0. W 系基线抽查（只读 —— 本轮当场值）

| # | 核验（只读） | 当场结果 | 判定 |
|---|---|---|---|
| W-1 | `git rev-parse HEAD` | `b537976d31f173ad2f2c69cc14888f51a1acbf3a` | 与申报「HEAD/blob 锚未动」**一致** ✓ |
| W-2 | `git status --porcelain --untracked-files=all` | **staged 38 / untracked 0 / 未暂存修改 0**；staged 构成 = R4 期 37 + `A docs/reviews/review-REL-080-RELEASE-R4.md`，其余逐项同 R4 W-2 | 与申报「staged 38（+R4 报告）」**一致** ✓；**无夹带** ✓ |
| W-3 | FIX-355 blob 锚（`ls-files -s` + `hash-object` + `diff` index↔worktree，全路径 `skills/…/infra/`） | `checks/review_domain.py` = **`e681bfa36866e8c0606a5e4cd37764bc15736fdf`**；`tests/test_review_closure_legacy.py` = **`610c2efcf174157e09b061d1c6c8b9d3fbba4642`**；索引 blob = 工作树 blob（diff 空） | 与 R2 W-7 / R3 W-3 / R4 W-3 **逐字节一致** ✓ → **Code Review 结论有效性前提存续** ✓ |
| W-4′ | R4 报告（08:49:52）后写入窗（staged 全集 38 文件 mtime 实测 + .governance 抽查） | post-R4 写入仅 3 文件：`release-checklist-0.84.0.md` 08:50:50、`rollback-plan-0.84.0.md` 08:50:50（**R4 期「03:31:04 零写入」物证已消——L-7 修复有真实写入**）、`evidence-log.md` 08:50:55（gitignored，**1,579,419 B = 1,542.4 KB**——与 O-2 申报值精确一致）；其余 35 个 staged 文件 mtime 全部 ≤ 08:31:04（hooks ×4 = 02:26:06、SKILL/verify_workflow = 02:26:01、`review_domain.py` = 04:50:41、`test_review_closure_legacy.py` = 04:19:30、投影/fixture/releases JSON/CHANGELOG 均 ≤ 03:23:41）；`decision-log` 06:14:38 / `session-snapshot` 08:31:04 / `feature-flags` 02:29:12 未动 | **门禁判定面（产品代码/hooks/SKILL/投影/fixture/测试/releases JSON）零触碰** ✓；写入面与申报修复范围吻合 ✓ |
| W-5 | 治理记录载体 | `decision-log.md` L155 = **DEC-214**（superseding DEC-203 半面——尾部含「RISK-051 复评：×2→已消解」）、L156 = **DEC-214①（勘误）**；全表 **无 `DEC-213⑧`**（与 R4 W-5 一致；文件自 06:14:38 未动，R4 实测值直接存续） | B-2′ 载体核验依据 ✓ |

---

## 1. R5 范围 1：L137① 单行逐字比对（B-1′/B-2′ 三锚点）

| R4 阻断 | R4 要求 | **R5 判定** | 实证（当场字符串，checklist L137） |
|---|---|---|---|
| **B-1′** | 整行改写：「当场终值 = **20 issues**」「**4 stale risks**〔含 RISK-036/039/046/050 复评窗〕」「系 **20 计数**」「本版 **20** 且 V2 消解、FAIL 面更窄」 | **✅ 全收口** | 「收口后 check-governance 当场终值 = **20 issues**」✓；「**4 stale risks〔RISK-036/039/046/050——复评窗 09-30/10-31 已登记未到期〕**」✓（与 L114⑦ 四风险清单一致）；「`--fail-on-issues` exit 1 **系 20 计数**含 WARN 族」✓；「本版 **20** 且 V2 消解、FAIL 面更窄——实质优于先例」✓（与申报原文逐字一致）。**与 L101/L108/L114/L147 的并列互斥已消除**；「21 issues」全文仅存于先例对照语境（L101/L114/L137/L147 四处均带「0.83.0 Gate 16 同型先例」限定——先例义务「不得以旧值作新声明」**已达成**）；全文 grep「2 stale」零命中 |
| **B-2′** | `DEC-213⑧` → `DEC-214 + DEC-214① 登记` | **✅ 全收口** | 当场文本 =「**+ DEC-214（superseding DEC-203 半面）+ DEC-214① 勘误登记（RISK-051 复评：×2→已消解）**」✓；checklist 全文 `DEC-213⑧` **零命中**；decision-log 载体 L155/L156 实证（W-5）✓——「发布包内引用不存在的决策条目」条件**已消除** |

**备注（非阻断）**：L137① 构成段为 **5 类凝聚式**（28s ×1 / 28n God-module 族 / 14-36 legacy WARN / 28q ×4 / 4 stale risks），未按 R4 §5-1 建议与 L114 十类构成逐类对齐（「勿再自造简版构成」的建言括注未全采）——但凝聚式各值与 L114 无矛盾、无旧值、总数锚定 R4 实证的 20（EVD-1086：check-governance 21→20），不复活 B-1′ 条件；登记为 P3 备注随 M-5 期刷新一并处理。

**小结**：R3→R4 三轮同源残项（B-1/B-2/B-1′/B-2′）**本轮全部收口**——披露真实性核心缺陷已消除。

---

## 2. R5 范围 2：四项 P3 行级核验（N-1 / L94 / L-7 / O-1）+ R4 清单 6

| 项 | R4 要求 | **R5 判定** | 实证 |
|---|---|---|---|
| **N-1**（L101 PASS 面计数自洽） | 表头计数 = 18 名枚举，禁止只换标签不改差值 | **✅ 收口** | L101 =「**PASS 面（17 门 PASS + 1 门预算覆盖 PASS = 18 面，R2 复核）**」——17+1=**18**；枚举当场清点 = **18 名**（version consistency / release fact source / hot fact source / runtime readiness / first session measurement / governance pack / agent adapters / projection sync / cross references / archive integrity / release docs / release lineage / gate sequence / one dot zero blockers / changelog / loop runtime claim gate / dsh upgrade regression / unit tests）——**差 1 形态已消除，自洽成立** ✓（与 R4 §5-3 建议口径一致：unit tests 系预算覆盖收口） |
| **L-6**（L94 精度项） | 「canonical 767 / actual 865」→ 769/870 或补时点限定 | **❌ 未收口——且申报失实** | L94 当场 =「canonical **767** / actual **865**」，**零时点限定**；全文件 grep：`769` 唯一命中 = L95 archguard「24,769 ≤ 24,769」（异义），`870` **零命中**。**申报「✅ 767/865 → 769/870（FIX-354/355 后实测；M-2 期 767/865 时点保留）」与实态不符——两半均未落笔**（申报值不在文件、时点注不在文件）。定级维持 R2/R3/R4 的 P3（check-manifest-consistency PASSED exit 0 事实不变，M-2 期 767/865 为该次实测值） |
| **L-7**（rollback-plan 三处时点限定） | L162/L170/L191 三处「staged 28」补时点限定 | **⚠ 部分收口（2/3）——申报「三处全部」对 1 处失实** | 物证前提已达成：文件 mtime 08:50:50（R4 期零写入已消，W-4′）。**L170 ✓**「staged 文件数 \| 28 \| **28** \| ✓ 不变（**演练时点 2026-09-19 06:xx 快照**——后续发布修复 staged 增至 37 属演练后独立变更，不在本表口径内）」；**L191 ✓**「零（指纹前后同值；staged 28 不变——**演练时点 2026-09-19 06:xx 口径**）」。**L162 ✗**「真实仓库**当前持有 28 个 staged 候选文件**」——仍为无时标现在时陈述（当场 staged = **38**，W-2）；「（副本内受控实验）」限定语在案但只覆盖实验地点、不覆盖「当前持有 28」的时点。零污染结论本身不被推翻（L170/L191 时点值成立） |
| **O-1**（staged 计数自指，4 处） | L112 / L188 / snapshot L13/L25 统一改口径 | **⚠ 部分收口（1/4）** | **L112 ✓**「发布期修复批归属披露（R1 F-19——staged 项构成演进 **28（M-1）→33（R1）→36（R3）→37（R4 时点）**〔R2/R3 期新增：R2/R3 审查报告 + 清单更新 + DEC-214①/EVD-1086/归档三文件入 .governance〕）」——演进链+时点戳形式成立（申报「归属披露段改演进链」对该处**如实**）。**L188 ✗**「已 staged（**36 集内**）」（当场 38）；**snapshot L13 ✗**「commit（**36 staged**，message 含 REL-080）」/**L25 ✗**「staged **36** 原样保持」（快照 08:31:04 未重写）。snapshot 属 gitignored 治理文件、不在发布包内——降权为治理面微瑕；L188 在发布包内 |
| **O-2**（evidence-log 字节值） | 如实申报 | **✅ 申报如实** | 当场 1,579,419 B = **1,542.4 KB**（08:50:55 写入）——与申报值**精确一致**；L137①「1,541.8 KB」持 ① 头「本版收口后终态 2026-09-19」时点限定（R4 O-2 已裁定不失实）。**M-5 期以当场值口径引用时 MUST 刷新**（28s 为 advisory，不阻断）——维持 R4 备注 |
| **R4 清单 6**（L171 尾巴） | 删「R2 后待终态刷新随 M-8」 | **❌ 未收口（未申报、静默未做）** | L171 当场尾部 =「…切片 A 完成态；**R2 后待终态刷新随 M-8**」仍在——快照已于 08:31:04 终态刷新（R4 L-5 裁定该尾巴失实）。本项**不在本轮 7 项申报清单内**——属 R4 §5 六项清单成员被静默遗漏 |

---

## 3. 本轮新发现（R4→R5 窗口）

| ID | 级别 | 问题（事实） | 处置 |
|---|---|---|---|
| **O-4** | **程序性（放行前提）** | **申报↔实态偏差再现 + 放行前提未达成**：本轮 7 项申报中 **2 项与实态不符**——L-6（称「✅ 767/865→769/870 已改」，实为零改动、grep 实证申报值不存在于文件）、L-7 之 L162 处（称「三处全部加时点限定」，实为 2/3）；另有 R4 清单 6（L171 尾巴）未申报亦未做。**R4 §5 六项清单实测 = 2 ✅（清单 1/3）+ 2 ⚠ 部分（清单 4 = 2/3、清单 5 = 1/4）+ 2 ❌（清单 2/6）→ T2 用户裁决的放行前提「全部文本面收口」不成立**。模式与 R4 O-3 同型（申报 ✅ 与落盘实态脱节），频次较上轮收敛（5/9→2/7+1 遗漏）但仍未归零 | 残留 4 行落笔后走 R6 逐行终验（范围 = 本报告 §5 清单 1~4 行 + W 系抽查），**或由用户重新裁决**（「接受 P3 残留放行」属新裁决，不在「R4 终验后放行」原授权语义内——原授权前提即「全部文本面收口」，本轮实证未达成）。Reviewer 不决定 |

---

## 4. 硬门槛逐项裁决（本轮当场）

| 硬门槛 | 阈值 | 本次事实 | 判定 |
|---|---|---|---|
| 发布检查清单全部 PASS | = 100% | **门禁面维持满足**（R2 基线判定面零触碰——W-3/W-4′；blob 锚逐字节存续）；**文档面未满足**：残留 4 行（L94 无时标旧值 / L162「当前持有 28」/ L188「36 集内」/ L171 失实尾巴）——均为时点精度类，无一推翻门禁事实，但「全部文本面收口」前提未达成 | ✗ **未满足（文档面——4 行）** |
| 回滚方案存在且已验证 | = 已验证 | 隔离副本 15 步演练 + R1 独立复算在案（本轮零触碰）；rollback-plan 已获 R4 后真实写入且 L170/L191 时点限定落位（L-7 主面收口 2/3）；真实 tip 面 = M-5 期义务（先例同型） | ✓ **满足** |
| CHANGELOG 用户视角完整 | 关键段全覆盖 | `[0.84.0] - 2026-09-19`（R2 已核；mtime 02:28:49 未动） | ✓ |
| breaking changes 已标注 | 100% | 显式「无」+ VERSIONING 反证（R2 已核，未触碰） | ✓ |
| Feature Flag 关闭验证 | 全部通过 | F-1/F-2 双臂 + 三层机检 + 守护测试（R2 已核；feature-flags 02:29:12 未动） | ✓ |
| P0 任务完成 | — | AUDIT-154 + FEAT-032~040 全 ✅；REL-080 行 ⏳（待 M-5） | ✓ |
| 版本 bump 完整性 | 全平面 | check-version-consistency PASS（R2）；blob 锚逐字节未变（W-3）；38 staged 无夹带（W-2）；HEAD 未动（W-1） | ✓ |

---

## 5. 结论与最小收口清单

**结论：NEEDS_CHANGE（round=R5，限定范围终验轮）｜unresolved_blockers=1（O-4 程序性——T2 放行前提未达成；R4 两项实质文本阻断 B-1′/B-2′ 已全收口）**

**M-5 放行裁决**：**不予放行（本授权链下）**。T2 用户裁决「R4 终验后放行」的前提 = R4 §5 界定的「全部文本面收口」经本轮逐行确认；实测六项清单 2 ✅ + 2 ⚠ + 2 ❌ → **前提不成立**，`core/releases/0.84.0.json` 保持 `candidate`。DEC-204 预授权与 T2 裁决**均不构成**对本轮审查结论的覆盖——「放行必须以终验通过为条件」（R3 §5 / R4 §5 原文语义连续适用）。

**最小收口清单（4 行必改 + 2 项同批可选；全部为文本面，不触碰 blob 锚/产品代码/门禁判定面/staged 集构成，无需重跑任何门禁）**：
1. **L94**（清单 2 残项）：按申报原文本落笔——「canonical **769** / actual **870**（FIX-354/355 后 R2 复核实测；M-2 期值 767/865）」，或保留 767/865 并补「（M-2 期口径；R2 复核 769/870）」。
2. **rollback-plan L162**（清单 4 残项 1/3）：「真实仓库当前持有 28 个 staged 候选文件」补时点限定，与 L170/L191 同口径——如「（演练时点 2026-09-19 06:xx 快照口径；当前候选集已演进至 38，属演练后独立变更——见 checklist L112 演进链）」。
3. **L188**（清单 5 残项）：「已 staged（36 集内）」→「已 staged（M-2 期 36 集内；现集演进见 L112——R4 时点 37，R4 报告入库后 38）」或删括注改指 L112 演进链。
4. **L171 尾巴**（清单 6 残项）：删「；R2 后待终态刷新随 M-8」，或改述为「快照已终态刷新（2026-09-19 08:31）；M-8 commit 后随收尾再刷新」。
5. （同批可选）snapshot L13/L25「36 staged」→ 当场口径（gitignored 不入库；R4 清单 5 列名成员）。
6. （同批可选）L112 链尾「37（R4 时点）」及 rollback-plan「增至 37」处，M-5 期统一按当场值口径刷新（38；R5 报告入库后 39）——避免下一轮再现同型时点漂移。

**收口后的路径（由 Coordinator/用户裁决，Reviewer 不决定）**：以上 4 行落笔后经 **R6 逐行终验（同 Reviewer，注入本报告）**关闭，范围 = 本清单 1~4 行 + W 系抽查；或由用户显式重新裁决（接受残留放行 = 新裁决，须用户明知「申报再现失实」这一事实后作出）。

---

## 6. 本轮复核确认的通过面（无需重做）

**B-1′/B-2′ 全收口**（L137① 三锚点 + DEC-214/214① 载体 + `DEC-213⑧` 全文清零 + 「2 stale」零残留 + 先例语境合规）；**N-1 收口**（17+1=18 自洽）；**R2 门禁基线全维持**（archive integrity PASS / unit tests 闸门 PASS + 全量 0 新增失败 30F/3451P / hot fact source / release docs / release lineage candidate / gate sequence / one dot zero blockers / changelog / loop runtime claim semantic+identity / verify + e2e + dsh upgrade regression 隔离冒烟 / Check 30 V2 violations = 0 / Check 27 PASS）；**blob 锚 `e681bfa…`/`610c2ef…` 逐字节未变（Code Review 有效性前提存续）**；**38 staged 无夹带、门禁判定面零触碰、HEAD 未动**；**rollback-plan 获 R4 后真实写入且 2/3 时点限定落位**；**L112 演进链落位**；**O-2 申报如实**（1,542.4 KB 精确一致）；DEC-214/214① 与 EVD-1082~1086 载体齐备。

## 7. 约束性备注（binding notes）

1. **M-5 不予放行（本授权链下）**；`core/releases/0.84.0.json` 保持 `candidate`；**38 staged 集保持原样**——禁止触碰 `checks/review_domain.py` / `tests/test_review_closure_legacy.py`（锚 `e681bfa…`/`610c2ef…` 是 Code Review 结论有效性前提，本轮已复核存续）。
2. 本轮 NEEDS_CHANGE **仍属文档面 4 行子集 + 程序性前提项**：不撤销 R2 门禁面结论，不构成「产品代码不可发布」判断；风险性质 = 「放行前提申报未兑现（O-4）」+「4 处时点精度残留」——**B-1′/B-2′ 类披露失实阻断已清零，本轮无新增强迫性事实错误**（4 行均为时点/计数精度类）。
3. **Coordinator 在向用户呈现 R5 结果时 MUST 如实转述 O-4（2/7 项申报失实 + 1 项静默遗漏 + 前提未达成）**——同时 MUST 如实转述 B-1′/B-2′ 已全收口（R4 两项实质阻断清零），不得以任何一侧弱化另一侧；用户的再裁决须同时知悉两面。
4. FIX-246 归档行不得为消除 WARN 回退改写（DEC-214/DEC-199 口径维持）。
5. M-5（若后续放行）义务维持 R3 §7-5 / R4 §7-5 原文：commit 后复跑 `release-ledger --no-remote`；tag 后复跑 `check-release --lineage-mode released --release-commit <commit>` 与 `release-ledger --remote origin`。
6. **写盘足迹声明**：本报告为本次审查**唯一**写盘产物（新增 `docs/reviews/review-REL-080-RELEASE-R5.md`；未修改任何 staged 文件；复核期 staged 38 / untracked 0 / unstaged 0 已留痕 W-2，落盘后 untracked +1）。

---

*审查方：Release Reviewer Agent（同 Reviewer，独立终验，只读）｜审查对象：0.84.0 候选（HEAD `b537976` + 38 staged 文件）｜授权链：R3 BLOCKED → T2「R4 终验后放行」→ R4 NEEDS_CHANGE(2) → R4 §5 预设 R5 限定终验 → 本轮｜前轮：`review-REL-080-RELEASE-R4`（NEEDS_CHANGE/2）｜结论：**NEEDS_CHANGE / round=R5 / unresolved_blockers=1（O-4 程序性——放行前提未达成；B-1′/B-2′ 实质阻断已全收口）**｜机录义务：Coordinator 以 `review-record` 持久化本结论（round=R5；Reviewer 不写治理状态）*
