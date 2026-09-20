# Release Review — FEAT-054（REL-081 M-3 Release 半面 · 0.85.0）— R0

> **Round**: R0（首轮独立审查；前轮引用：无）
> **审查对象**: 工作树 staged 7 文件（4 A 发布材料 + version-plan M / SKILL.md M 两处一行修 + 0.85.0.json A manifest）+ 附带工作树面（fixture 投影 / `.governance` 基线 / 0.84.0 先例四件套）
> **审查人**: Release Reviewer Agent（独立——未参与起草与 M-2 实测；只读审查）
> **日期**: 2026-09-20
> **性质**: 本审查即 **REL-081 M-3 发布半面**——结论同时回答「0.85.0 可否进入 M-4/M-5 transition+tag」（DEC-217 预授权不免除本审查义务，已履行）

---

## 总结论

## **NEEDS_CHANGE**（R0）— `unresolved_blockers = 1`

| 项 | 裁定 |
|---|---|
| 总结论 | **NEEDS_CHANGE**（非终态——Coordinator 修复后 MUST 发起 R1 复审） |
| unresolved_blockers | **1**（P1-F-1：staged 集与 checklist 申报提交面不一致——fixture 投影未 stage） |
| 发布材料 / 门禁 / 回滚 / 归属面 | 全部达标（11 项独立复验与申报一致；详下） |
| P0 findings | 0 |
| P1 findings | 1（F-1，提交动作 MUST 前置修复，动作 = 一条 `git add`） |
| P2 findings | 1（F-2，M-8 收口义务） |
| P3 findings | 3（F-3/F-4/F-5，刷新与精度备注） |
| **M-3 裁定** | **本半面 no-go（暂）→ F-1 修复 + R1 复审通过后 go**。修复后可按 DEC-217 预授权进入 M-4 呈现 → M-5 transition+tag；F-2 补 DEC-222 入账不阻断 M-4/M-5，但 MUST 在 M-8 收口完成 |

**不落入 BLOCKED**：无致命流程缺陷；P1 属操作面缺口（修复动作微小且明确），发布文档内容、门禁实测、回滚方案、CHANGELOG、归属披露全部经独立复验成立。

---

## 一、独立复验表（Reviewer 实跑——11 项，全部与申报一致或有时点解释）

| # | 复验项 | 命令 / 方法 | 实测结果 | 对照申报 | 判定 |
|---|---|---|---|---|---|
| V1 | 窗口计数 | `git rev-list --count 3663423..1cd224e` | **17** | checklist §Change Inventory「= 17」 | ✅ 一致 |
| V2 | 回滚区间交错事实 | `git log --reverse --format="%h %ad"` 时间序 | `be0b844`(09-19 **11:25**) 先于 `d62066b`(09-19 **11:26**) | rollback §区间注记「FIX-356 先于 R6 补提交落库」 | ✅ 交错属实 |
| V3 | tag peel | `git for-each-ref refs/tags/v0.84.0` | obj=tag, peel=**5d1943f** | rollback/checklist「peel = 5d1943f」 | ✅ 一致 |
| V4 | check-version-consistency | 复跑 | PASSED exit 0；13 面+双入口一致；1 WARN（plan-tracker 0.84.0 过渡态） | checklist #1 逐字一致 | ✅ |
| V5 | check-cross-references | 复跑 | **0 dangling / 0 deprecated / 0 circular**（78 文件 724 引用） | checklist #6 修复回合终态 | ✅ SKILL.md:121 前缀修复有效 |
| V6 | release-projection（check-only） | 复跑 | state=**PASS**；source_version=**0.85.0**；projections_checked=**28** | checklist #5 | ✅ |
| V7 | check-injection-budget ×3 profile | 复跑 | lightweight **4,216**/6,000 · standard **5,694**/6,000 · strict **5,966**/6,000，全 PASSED；`gated: none` | checklist #2 逐位一致（strict 余量 34 tok 属实） | ✅ hard 门生效 |
| V8 | release-ledger --no-remote | 复跑 | **FAIL exit 1**，唯一 issue=`candidate_commit: … found 0`；trust_level=**NATIVE_CANDIDATE**；event_identity_digest=`37517e5f…` | checklist #9 披露**逐字一致**（含 digest 前缀） | ✅ 预提交态预期观测如实，未包装为 PASS |
| V9 | manifest-consistency / archguard / entry-bootstrap-sync | 三项复跑 | manifest PASS（canonical **817**/actual **922**）；archguard PASS 0 violations（R7 deterministic=True）；entry-bootstrap PASSED | 申报 813/917（见 F-3 时点差）；archguard/bootsync 一致 | ✅（态一致；数值时点差记 P3） |
| V10 | pytest 抽验 ×2 | ①`test_loop_runtime_claims.py` ②`ResolveEntryTests::test_snapshot_freshness_recent_is_fresh`（01:30 时点） | ① **60 passed + 81 subtests passed**（LRC 族全绿）② **FAILED**（`snapshot_fresh=False`）——午夜窗内同形复现 | checklist #14「ragged row 修复后 5 项转绿、余 1 项午夜窗时间敏感（02:00 后自愈）」 | ✅ 两面均证实（转绿属实 + 余项红色归因同形） |
| V11 | check-governance 构成 | 复跑 | **hot fact source `[OK] synchronized`**；Check 18c/18g **REL-081 packet FAIL ×5** 逐项在（scope 过宽/product_success/acceptance/quality_budget/vertical_slice）；总计 **46 issues** | 申报 48（披露时点）；hot-fact 已由 Coordinator 收口的申报**被证实**；packet ×5 与披露逐项对应 | ✅（48→46 = hot-fact 收口演进，见 F-4） |

**未复跑项（如实声明）**：check-release 全量复合门禁、verify 全量、e2e-check、全量 pytest 6F/3747P 主跑值、dsh upgrade regression 隔离冒烟——基于 V4~V11 共 11 项抽验（含 check-release 的 7 个组成门独立复跑）全部与申报一致的一致性证据**采信申报值**；M-8 candidate 提交后与 M-5 tag 后的复跑义务照旧（checklist #9/#15 已载）。

---

## 二、Findings

### P1（BLOCKING for 提交动作 → 构成本轮 NEEDS_CHANGE）

**F-1 staged 集与 checklist 申报提交面不一致——fixture SKILL.md 投影未 stage**
- **事实**：checklist L53「M-1R prep 批（本提交）：…+ fixture SKILL.md 投影再生（`release-projection --write` written=1）」申报 fixture 投影随候选提交入库；但 `project/e2e-test-project/skills/software-project-governance/SKILL.md` 当前为**未 staged 工作树修改**（`git status` = ` M`；staged 集仅 7 文件）。其 diff 内容经本审查逐字核对 = canonical SKILL.md:121 前缀修复的**同步投影**（同一行 `archive/index.md` → `.governance/archive/index.md`）——再生已执行、stage 缺失。
- **影响**：若 Coordinator 按当前索引提交 7 文件 → 候选树 HEAD 上 canonical（修复版）与 fixture（0.84.0 期内容）投影不一致 → 干净检出后 `check-projection-sync` FAIL（28 面投影合同断裂）+ 工作树永久脏——M-6 released 门禁必炸。当前 V5/V6 在工作树态 PASS 是因为检查消费工作树文件（已再生），不构成对 staged 面的豁免。
- **修复（Coordinator，返工动作）**：`git add project/e2e-test-project/skills/software-project-governance/SKILL.md` 后随候选提交（第 8 文件）；或若 Coordinator 另有提交拆分裁定，则 MUST 修正 checklist L53 申报口径使申报与提交面一致。二选一后发 R1 复审验证。

### P2（非阻断——M-8 收口义务）

**F-2 DEC-222 未入 decision-log——归属承载决策的权威记录缺行**
- **事实**：checklist 披露②、release-plan §载荷构成均引用「→ DEC-222 承载 0.86.0（Coordinator 裁决）」；本审查 grep `.governance/decision-log.md` **零命中 DEC-222**（唯一留痕 = session-snapshot L21 一处括注）。
- **评估**：归属裁决本身事实成立（FEAT-046/047/051 均为 0.86.0 批 1 票面，EVD-1108/1110/1111 实证审查链闭环；CHANGELOG 冻结于 `a91d6b4` 的时序事实成立），且 CHANGELOG 披露⑤（FEAT-049 登记）+ release-plan 披露②双重承载了披露义务；但**权威决策记录缺行 = 审计引用链断裂**——后续复审/审计按「checklist → decision-log」追溯 DEC-222 时落空。
- **修复（Coordinator，M-8 收口）**：decision-log 补 DEC-222 行（内容 = FEAT-046/047/051 CHANGELOG 归属 0.86.0 段裁决 + 引用 session-snapshot 留痕）。不阻断 M-4/M-5。

### P3（记录性备注）

- **F-3 check-manifest-consistency 数值时点差**：checklist #7 记 canonical 813/actual 917（修复回合前初测值），本审查复测 **817/922**（PASS 态一致；差 4 ≈ feature-flags / 0.85.0.json 两 staged 新文件 + untracked 面时点演进）。建议 M-8 复跑时刷新 #7 数值或标注时点。
- **F-4 check-governance 计数已因收口演进**：checklist #12/#10 记 48 issues、余 2 FAIL（hot-fact + gov-health）；本审查实测 **46 issues 且 hot-fact `[OK]`**（Coordinator 已刷新 session-snapshot：date=2026-09-20 可解析 + 0.81.0 历史锚已补——V11 实证）。「余 2」现状实际为「余 1（packet ×5 收口面）+ hot-fact 已收口」。披露方向保守（把已收口项暂记开放）不构成错误，M-8 复跑时刷新。
- **F-5 测试全名精度**：checklist #14 引用 `test_resolve_entry.py::test_snapshot_freshness_recent_is_fresh` 未含类路径（实际为 `ResolveEntryTests::test_snapshot_freshness_recent_is_fresh`）——按简名 pytest 直调报 not found（本审查 V10② 首跑即遇）。测试实际存在，归因不受影响；纯文档精度。

---

## 三、九项审查重点逐项裁定

| # | 重点 | 裁定 | 关键依据 |
|---|---|---|---|
| ① | 发布材料完备性与先例对照 | **PASS** | 四件套成形且无缺面：0.84.0 期**无独立 release-plan**（glob 实证仅 checklist/feature-flags/rollback 三件；0.84.0 manifest `release_docs` 3 件）→ 0.85.0 四件为**超集扩展**非缺面。保守边界 5 token 四文件逐一在场且均为否定形态（「未被授予、未被主张」）；overclaim 复核 CLEAN：四文件无可索引正向主张，`<发布 tip>`/tag/演练未实测面一律不预填（plan/checklist/rollback 三处边界声明均载）。 |
| ② | **回滚区间锚定** | **PASS（论证成立）** | 三层复核：ⅰ 交错事实 git 实测（V2：`be0b844` 11:25 先于 `d62066b` 11:26）；ⅱ 禁 `be0b844..tip` 论证正确——git 区间语义排除下界自身，若锚 be0b844 则 FIX-356 全部改动残留、回不到 0.84.0 行为（0.81.0 F-01 同形失效，先例引用属实）；ⅲ 代价披露完备——`3663423..tip` 将 `d62066b`（0.84.0 R6 报告补提交）一并回退，归档副本义务按 0.84.0 rollback §5 先例（本审查 grep 实证 L115「审计信息损失…MUST 归档副本」同构）写入 §区间注记 2 + §5.6 点名。终点 = 发布 tip 而非候选提交（F-04 教训在场）；`rev-list --count` 不写死、M-5 现场取值——保守正确。 |
| ③ | M-2 门禁结果真实性抽查 | **PASS（抽验 11/11 一致）** | 详见复验表 V4~V11：check-release 的 7 个组成门独立复跑全对上（version/projection/cross-ref/budget×3/ledger/manifest/archguard/bootsync）；pytest 两面抽验证实「5 转绿 + 1 午夜窗保持」；未复跑面以抽验一致性采信并如实声明。**无一处申报值被复验推翻**。 |
| ④ | check-release 余 2 项收口路径 | **PASS（披露充分）** | ⅰ hot-fact：Coordinator 刷新申报**被独立证实**（V11 `[OK] synchronized`；snapshot 文件实读：date 可解析 + 0.81.0 引用已补）；ⅱ gov-health packet ×5：与 0.84.0 先例**同型实证**（0.84.0 checklist #13「Check 18c ×6 = REL-080 missing execution packet → 收口 = execution-packet --write + 契约填充」grep 在案）——packet 为 M-1 开发面形态、发布态由 Coordinator `execution-packet` 更新收口，路径明确、处置人明确。FAIL 不包装、构成逐项列明——披露充分性成立。 |
| ⑤ | FEAT-046/047/051 不入 0.85.0 CHANGELOG 归属 | **PASS（归属正确）+ F-2 记账缺口** | 时序事实成立（`b2152ea`/`1cd224e` 晚于 CHANGELOG 冻结 `a91d6b4`）；三票均 0.86.0 批 1 轨道（EVD-1108/1110/1111 实证 Developer→Reviewer 链闭环：FEAT-047 R0 NEEDS_CHANGE→R1 APPROVED/0 等）；FEAT-049 已专段登记（披露⑤+Added 节）、FEAT-047 括注口径与 release-plan 披露②一致、FEAT-051/046 未登记如实披露。归属 0.86.0 = DEC-221 轨道正确；唯承载决策 DEC-222 权威记录缺行（→ F-2，P2）。 |
| ⑥ | ragged row 修复附带 5 项转绿因果论证 | **PASS（因果链证实）** | ⅰ diff 实证：version-plan 硬门槛自检表 4 行「**PASS** — 依据」合流列 → 「**PASS** \| 依据」分列——markdown 表列数规则化，消除 LRC gate ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY + IDENTITY_ATTESTATION_FAIL 的机械成因（账本快照早于 M-0 故未载该 ragged row——时序自洽）；ⅱ V10①：LRC 族 60+81 全绿——「转绿」声明独立证实；ⅲ V10②：唯一余项 01:30 实测仍红且失败点（`snapshot_fresh=False`）与 fixture date-only 午夜窗解析归因**同形复现**——「与数据/代码修复无关」的反向断言也被证实。归因非编造、非包装。 |
| ⑦ | feature-flags 插曲合规性 | **PASS** | 首版 §6 自检表 token 字面枚举行被 overclaim 检查拦截（局部子句无否定形态→扫描器保守拦截 = 检查器正常工作）；改写为「齐备于保守边界声明节」指针形态——本审查核对：5 项 boundary token 在 §保守边界声明**实际齐全**（非删除规避），新行携带否定语义，扫描 CLEAN 属实。改写 = 消除误报，非绕过检查。最小形态补授（Coordinator 裁决选项 (a)）与 B-1/B-2「无 flag 级降级，版本级回滚」CHANGELOG 原文逐字对齐（§2/§3 交叉核对成立）。 |
| ⑧ | AI 专项 | **PASS** | 四文件全文 + manifest + 两 diff 逐字人工核读；11 项声明抽验零编造（含 digest 前缀、tok 逐位、计数、hash、时间戳全部对上）；全部未实测项显式标注（演练/check-release 全量/tag/transition/ledger 提交后复跑）；每文件尾携带事实基线来源声明。发现的三处数值漂移（F-3/F-4）均有时点解释且方向保守。未发现幻觉、未发现超范围主张、未发现预填未生成事实。 |

---

## 四、M-3 裁定（go/no-go）

**本半面（Release）= NEEDS_CHANGE → 暂 no-go；F-1 修复 + R1 复审通过后 go。**

路径（按 DEC-217 预授权，M-4 无需用户确认，但门禁义务不免除）：

1. **Coordinator 返工（F-1）**：补 stage fixture 投影（第 8 文件）或修正 checklist L53 申报口径（二选一，留痕）；
2. **R1 复审（本 Reviewer 重 spawn）**：逐条比对 F-1~F-5（已修复/未修复/新引入），验证 staged 集 = 申报提交面；R1 通过 = Release 半面 APPROVED；
3. **M-4 go/no-go**：DEC-217 预授权形态由 Coordinator 呈现——本审查建议 go（F-2 按 M-8 义务承载，不阻断）；
4. **M-5 transition+tag → M-6 released 门禁 → M-7 push → M-8 收尾**（M-8 必含：ledger 复跑 / DEC-222 入账 / checklist #7/#12 数值刷新 / plan-tracker 版本更新 / 归档完整性）。

**Design/Code 半面**：本报告仅承载 Release 半面；0.86.0 随树票 ×3（FEAT-046/047/051）的 Code 半面与 0.85.0 两处一行修的 Code 半面按 M-3 双半面安排由相应 Reviewer 承载（不在本报告裁决范围）。

---

## 五、边缘问题（呈 Coordinator）

1. **提交拆分语义**：F-1 若选「另一提交承载 fixture 投影」路径，需注意 single-parent transition（M-5）与 candidate commit 定义的耦合——manifest `trust.candidate_commit.derivation = git_commit_adding_path` 锚定「adding 0.85.0.json 的提交」；fixture 投影晚于 candidate 提交落库将使 candidate..tip 区间多出 1 提交，rollback 区间与 M-6 复跑口径需同步——**推荐同提交入库（单提交 8 文件）**，避免区间语义复杂化。
2. **snapshot freshness（FIX-364 候选）复验时点**：本审查实测时点 01:30（午夜窗内），「02:00 后自愈」预言未及验证——FIX-364 triage 时建议以 02:00 后复跑记录终态，闭合该归因的最后一环。
3. **checklist #12「48 issues」与 #10「余 2」已因 hot-fact 收口演进**（实测 46 / 实余 1）——若 Coordinator 希望候选提交时点披露零滞后，可在 M-8 前顺手刷新两行数值；不刷新亦不构成阻断（披露方向保守）。

---

## 复审指引（R1 MUST）

1. 头部声明 R1 + 引用本报告路径；
2. 逐条比对 F-1~F-5：F-1（staged 集 = 申报面——`git status --porcelain` 复核第 8 文件在列且无其他差异）/ F-2（若 M-8 未到，确认义务挂账即可）/ F-3~F-5（记录性，确认已知悉）；
3. 复跑最小集：`git diff --cached --stat`（8 文件）+ `check-projection-sync --fail-on-issues` + `check-cross-references`；
4. 任何新差异按新 finding 分级，不得沿用 R0 结论。

---
*FEAT-054 R0 发布审查（2026-09-20，Release Reviewer Agent）。事实基线：全部结论基于本审查实跑命令输出（V1~V11）、四文件+manifest+diff 逐字核读、`.governance` 治理文件实读（decision-log / evidence-log / session-snapshot）、0.84.0 先例四件套与 CHANGELOG 0.85.0 段（`a91d6b4` 冻结版）对照。未验证面已如实声明（§一 未复跑项）。本报告为唯一写入物；未修改产品代码 / `.governance/` / 发布文档；未执行 tag/push/transition。*
