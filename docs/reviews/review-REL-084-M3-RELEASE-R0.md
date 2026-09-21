# Review — REL-084 · 0.87.0 发布就绪（M-3）Release 半面审查 · R0

> **结论**: **APPROVED_WITH_NOTES**
> **unresolved_blockers=0**
> **Round**: R0（无前轮引用——首轮）
> **审查对象**: 0.87.0 发布就绪全链——四件套（release-plan / release-checklist / rollback-plan / feature-flags 0.87.0）+ M-1 候选 `80d71b5`（FEAT-059，EVD-1129）+ M-1R 批 `f11faa1`（REL-085，EVD-1130）+ M-2 批 `008efa6`（EVD-1131——门禁 #1~#16 回填 + 九失败修复链）+ CHANGELOG 0.87.0 段 + 治理链（EVD-1122~1131 机录 / DEC-226~228 / 九票 APPROVED 终态）
> **审查半面**: M-3 发布面（Release Reviewer 单席，串行）——M-3 复验六重点逐项 + 5 维度 + AI 专项
> **审查者**: Release Reviewer Agent（只读——未修改任何发布文档/代码；本报告为唯一写入物）
> **日期**: 2026-09-21
> **路径消歧声明**: 任务指定路径 `docs/reviews/review-REL-084-RELEASE-R0.md` 已被 **M-0 期 version-plan-0.87.0 发布半面审查报告**（2026-09-20，126 行，CHANGELOG 0.87.0 段治理面与 rollback-plan §5#6 引用的审计留档）占用——为不覆盖历史审查留档，本报告落盘消歧名 `review-REL-084-M3-RELEASE-R0.md`。 Coordinator 机录 review-record 时请引用本路径。

---

## 0. 方法与工具面边界（如实声明）

- 工具面：Read / Grep / Glob only（任务约束——Bash 禁止）。因此：**未复跑任何门禁命令**（verify / pytest / archguard / LRC / ledger），门禁数值以 M-2 实测回填（checklist #1~#16）+ EVD-1131 机录为事实源，本轮做**声明↔工作树↔机录三方一致性**核验 + 数学自洽验算 + 抽查实证。
- git 窗口核验为**静态替代**：`.git/logs/HEAD`（reflog）grep 实证提交存在性与消息内容；`git rev-list --count` 精确计数无法复跑——精确计数义务已内建于文档（M-5 现场取值记 EVD），不构成本轮缺口。

## 1. 证据清单（全部实读/实查）

| # | 证据 | 用途 |
|---|------|------|
| 1 | `docs/release/release-plan-0.87.0.md` 全文（117 行） | 载荷/授权链/门禁摘要/区间锚定 |
| 2 | `docs/release/release-checklist-0.87.0.md` 全文（154 行——**#1~#16 全位已回填**） | 门禁回填真实性主对象 |
| 3 | `docs/release/rollback-plan-0.87.0.md` 全文（166 行） | 回滚能力维度 |
| 4 | `docs/release/feature-flags-0.87.0.md` 全文（74 行） | flag 维度 |
| 5 | `project/CHANGELOG.md` L1~140（0.87.0 段全文 L5~57） | CHANGELOG 完整性/口径一致性 |
| 6 | `.governance/plan-tracker.md` L1~110（REL-084/REL-085/FEAT-059/FIX-364~372/373~376 行） | 票状态一致性 |
| 7 | `.governance/evidence-log.md` EVD-1130（L2496）/ EVD-1131（L2555）——governance-store 机录（op-06e6f7a9… / op-cdaf25e3…，schema v1） | M-1R / M-2 机录在案性 |
| 8 | `.git/logs/HEAD` L513~515 —— `80d71b5`（FEAT-059 M-1）/ `f11faa1`（REL-085 四件套）/ `008efa6`（M-2 批）提交存在性+消息全文 | 提交面静态实证 |
| 9 | `skills/software-project-governance/infra/checks/loop_runtime_claims.py` L225/230/236/243 —— provenance 注释 + `max_semantic_units: int = 361923` | B-9 红线 |
| 10 | `skills/software-project-governance/infra/tests/test_loop_runtime_claims.py` L1879 `class FIX369SemanticBudgetRecalibrationTests` | 反豁免 fail-closed 测试在场性 |
| 11 | `skills/software-project-governance/infra/contract_matrix/snapshots.json` L248 `"locks-release"` | 96 键 CLI 分发面 committed 在场性 |
| 12 | `docs/reviews/review-REL-084-RELEASE-R0.md`（M-0 报告，L1~40 抽读）+ `review-FIX-371-CODE-R0.md` L57 + `review-FEAT-059-RELEASE-R0.md` L56（grep 命中面） | 前链审查背书交叉验证 |
| 13 | `docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md`（REQ-092 关联）等 grep 命中 17 处 | REQ-092 外部依赖面 |

## 2. M-3 复验六重点逐项判定

### 2.1 门禁表回填真实性 — **PASS（抽查面零失实）**

- **#16 LRC 304,481**：数学自洽——304,481 ≤ 361,923 ✓；余量 361,923−304,481 = **57,442** ✓；57,442/361,923 = 15.87% ≈ 15.9% ✓；公式 ceil(301,602×1.2) = ceil(361,922.4) = **361,923** ✓；checklist #16 ↔ EVD-1131「Check 31 PASS/304,481≤361,923 余量 57,442」逐位一致 ✓。常量在树：`loop_runtime_claims.py` L243 `max_semantic_units: int = 361923` + provenance L225-243 实读在场 ✓。
- **#11 pytest 3,847P/0F/1 skipped/504 subtests**：未复跑（工具面）。静态一致性：3,820（0.86.0）→3,847 = **+27**，归因 FIX-370/371/372 新测试与 M-2 修复批叙述自洽；B-9 反豁免测试类实读在树；EVD-1131 refs 含 test_verify_workflow.py / test_archguard_ratchet.py。声明↔机录零矛盾。
- **#8 棘轮 96/96**：contract matrix 快照 committed 含 `locks-release` 键（snapshots.json L248）✓——与 #9「cli_dispatch 96 键含 locks-release」一致；M-2 修复批「archguard regen + FACTS_PRINT_TOTAL 1306→1316（FIX-377 出槽 bisect 归属注记）」在 `008efa6` 提交消息中在案 ✓。R5 精确 96 计数未独立复数（工具面）——以 M-2 archguard-ratchet 实测（EVD-1131）为准，零矛盾。
- **抽查 3 项**：① R5 键数——见上（contract matrix committed 96 键实证 + R5 精确值留 M-2 记录）；② CHANGELOG 段完整性——**完整**（九票交付 9 项逐一含 commit hash/审查结论/EVD 号 + ⑥ 治理面 3 DEC+7 EVD+审查留档 + Added/Changed/Fixed + B-9/B-10/B-11 行为变更节 + 披露①~⑦ + Breaking=无论证 + MINOR 依据 + 版本投影段 + Commit 区间 8 行注记「落库后延伸至 9」自洽）；③ 回滚区间 9 提交——静态三重印证成立：checklist Change Inventory / release-plan 载荷表 / rollback §区间锚定三处**同表 9 提交**（新→旧 `80d71b5`→`5e56021` + FIX-367 零 commit 面如实注记）；reflog 实证 `80d71b5`（L513）、`008efa6`（L515，窗口第 11 提交——M-1R/M-2 批随发布批增长与「计数不写死」条款一致）；下界 `6e25753` = v0.86.0 peel 与 plan-tracker「transition 6e25753」独立印证。F-P3-5（7 个 hash 未逐一 git 实证）见 §5。

### 2.2 九失败修复链披露完整 — **PASS（三源闭环）**

checklist #11 修复批四项 ↔ `008efa6` 提交消息 ↔ EVD-1131③ **逐项对齐**：
1. closure kill-switch docstring 字面量（FIX-370 微修）✓；
2. archguard regen + FACTS 1316 对齐（FIX-377/0.88 bisect 归属如实注记）✓；
3. LRC 真实仓库瞬态（单独复跑 PASS——并行扫描竞争，L1856 注释先例）✓；
4. FIX-371 fixture 翻转误伤回翻（1 处回翻 + 9 位点甄别表——Check 19 判据误伤）✓。
**R0「零断言弱化」声明的证伪与修正如实性**：误伤在 M-2 期被如实披露为「翻转误伤 Check 19 判据」并回翻（回翻=修复误伤而非弱化断言）；FIX-371 R0 NEEDS_CHANGE（F-1）→R1 APPROVED/0 复审必达链在案（plan-tracker L95 + CHANGELOG L21 双载）——证伪→修正的轨迹可追溯，无静默。**RECO 28 票补录**：checklist #1 分解「Check 34 violations×24（RECO 快照补录 28 票）」↔ EVD-1131「RECO 快照补录 28 票（Check 34 violations 24→0）」主口径一致 ✓（28 vs 24 桥接句缺失 → F-P3-2，非阻断）。checklist #1 分解 ↔ `008efa6` 消息（「checklist 16 位回填」）一致 ✓。

### 2.3 披露①~⑨ vs 事实 — **PASS（九条逐一对账）**

| 披露 | 事实核验 | 判定 |
|---|---|---|
| ① candidate manifest 缺席 | Glob `core/releases/*.json` 零命中——与「尚未创建」一致（注：0.86.0 manifest 亦未命中——工具面边界如实标注，F-P3-7；最终以提交批 check-release/ledger 复跑为准） | ✓ 如实 |
| ② REQ-092×6 维持 | Check 16×3+17×3 = 6 FAIL；M-2 回填记录 3 FAIL 全部 = REQ-092（EVD-476/473/423 🚧 blocked）；review-FIX-371-CODE-R0 L57 独立核验「plan-tracker L439 非 ✅ 前缀 → 不豁免 → FAIL 保持」 | ✓ 活体 |
| ③ EVD-248 单条噪声 | CHANGELOG 披露② + checklist 披露③ + FIX-373 triage 出槽行（plan-tracker L97）三载一致 | ✓ 如实 |
| ④ FIX-373~376 出槽 0.88 | plan-tracker REL-084 行出槽注记 + rollback §8 候选池 + CHANGELOG 披露③ | ✓ 如实 |
| ⑤ CRLF 保真 | 四处同口径（CHANGELOG ④ / checklist ⑤ / rollback §1+§7 / feature-flags §5）；护栏双断言声明在案 | ✓（F-P3-1 笔误） |
| ⑥ FIX-366 正道依赖 | checklist 披露⑥ + rollback §7 专节（绕开手法复活面——M-3 MUST 复核项已复核：缺陷本体/修复/回退含义/CRLF 连带/操作者告知义务五要素齐备） | ✓ 如实 |
| ⑦ 过渡态 WARN 开放 | plan-tracker `工作流版本` 仍 0.86.0（本轮实读确认）↔ checklist #2/披露⑦「唯一预期 WARN」 | ✓ 如实 |
| ⑧ no-overclaim | 四件套保守边界 5 token 齐备 + CHANGELOG 披露⑦同口径；全文无可索引活体越界主张 | ✓ |
| ⑨ 回滚弱化面 | LRC 必然 BLOCKED 回归（300,000 < 实测 301,602）/ 豁免消失计数回升 / 锁不恢复 / projection 回缺陷态——四项如实、无 flag 中间态声明与 feature-flags §1「无 flag 级通道」互证 | ✓ 如实 |

### 2.4 REQ-092 披露姿态（0.79.0 先例援引）— **成立**

三要素齐备：外部依赖文档面在场（`docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md` 等，grep 17 命中）+ result matrix 在场声明贯穿（checklist 专席/披露②/feature-flags §4）+ **零豁免红线活体**（REQ-092 行 🚧 blocked 未入账本 → Check 16/17 各 3 FAIL 维持——M-2 回填记录与 review-FIX-371-CODE-R0 独立核验双源）。「0.79.0 先例姿态」援引由 review-FIX-371-CODE-R0 与 review-FEAT-059-RELEASE-R0 前链审查背书；0.79.0 checklist 原文未直接抽读（预算面）——姿态成立性不受影响（F-P3 备注）。

### 2.5 B-9 重定标红线 — **有据吸收成立，非豁免**

- 公式可复算：ceil(301,602×1.2)=361,923 ✓（三处文档+常量行四源同值）；
- provenance 机制在场：`loop_runtime_claims.py` L225-243 注释（DEC-226/FIX-369/v0.87.0/公式/基线锚）实读 ✓；baseline-register 登记声明（gate check-31-semantic-units）在案；
- **反豁免 fail-closed 双测试在树**：`FIX369SemanticBudgetRecalibrationTests`（test_loop_runtime_claims.py L1879）✓——静默上调被守护测试翻红的机制面成立；
- 304,481 < 361,923 属「活数据增长被有据预算吸收」——门禁语义未弱化（BLOCKED→有据 PASS 仅因容量重推导；反豁免测试钉死再重定标必须走同公式）✓。

### 2.6 no-overclaim 终检 — **PASS**

四件套保守边界声明逐份齐备（No official/marketplace/universal runtime/external pilot claim + RISK-036 open + do not claim 1.0.0 production-ready）；「隔离环境安装冒烟（环境变量重定向至临时目录）通过」限定措辞合规（checklist #13——real-home writes: 0）；发布 tip/tag/M-2 预填禁令在 M-1R 期被遵守（本轮实读零预填 hash）；M-2 期回填以「实测后原样回填」执行且 #14/#15 如实保留 ⏳/未排程标注——**无未实测项写成通过**。

## 3. 五维度审查

| 维度 | 判定 | 依据摘要 |
|---|---|---|
| 发布检查清单 | **PASS** | #1~#16 全位：12 项实测回填（#2~#9/#11~#13/#16）+ #10 FAIL 如实归类预提交态预期 + #14 Coordinator 提交批义务 ⏳ + #15 未排程如实——无伪 PASS；Check 16 3 FAIL 专席分解+红线纪律条款在场 |
| 回滚能力 | **PASS（附 P2 建议）** | 区间锚定两段论证（单轨合一+F-04 终点教训）+ revert 程序/替代锚不等价标注 + 验证表 11 项（含 B-9 回退必然 BLOCKED 期望如实）+ 触发条件 7 + 不可回滚 7 + §7 FIX-366 复活风险专节 + 0.88 前进路径。演练未排程=先例同型（0.85.0/0.86.0）+ 文档移交 M-3 裁决——本席裁决：**不阻断**，P2-F1 建议候选提交批后隔离副本补 revert 干跑 |
| CHANGELOG 质量 | **PASS** | 用户视角完整（Added/Changed/Fixed/行为变更 MUST 升级说明/披露/semver 论证）；breaking changes 显式标注「无」且 L11 逐项论证；九票 commit/证据号与 checklist/release-plan 同表；与四件套口径逐字对齐 |
| Feature Flag | **PASS** | B-9/B-10/B-11 无 flag 级通道=登记面+版本级回退唯一路径声明+灰度开关正交性论证（LEGACY_REVERTS 白名单外）+ kill switch N/A 论证各自成立 |
| 版本号合规 | **PASS** | MINOR（L12 新增受治理能力面）/非 PATCH/非 MAJOR 逐项论证；B-9 L11 显式处置（R0-RELEASE-F3 先例同型）；0.87.0 无预留占用、1.0.0 未触碰 |

**AI 专项 — PASS**：①机录凭证链在案——EVD-1122~1131 全部 governance-store evidence-append 机录（本轮实读 EVD-1130/1131 op- 锚 + schema v1）；②无幻觉 hash——抽查实证实测（`80d71b5`/`f11faa1`/`008efa6` reflog 存在且消息与 EVD 逐项对应）；③如实性——失败修复链/披露面/未排程面均不美化；④复审必达链前科清白（FIX-366/370/371 三票 NEEDS_CHANGE→R1 全部履行，0 unresolved blockers）。

## 4. Findings

**BLOCKING：无。**

- **P2-F1（回滚演练未排程——建议+跟踪）**：checklist #15/rollback §4#10 如实标注未演练。不阻断依据：0.85.0/0.86.0 同型已发布先例、区间单轨结构简单、两段论证+F-04/P-12 教训内建、终点依赖 M-5 tip 使提前演练受限。**建议**：candidate 提交批后、tag 前，于隔离副本（`git clone --no-hardlinks` 法）执行一次 `revert --no-commit 6e25753..<发布 tip>` 干跑并记 EVD；若窗口不可行，M-5 现场 rev-list 计数义务为最低兜底（已在文档内建）。
- **P3-F1**：CHANGELOG 披露④「**CRuntime** CRLF 保真行为变化」措辞瑕疵（应为 CRLF 保真/投影面语境）。CHANGELOG 已于 M-1 冻结（`80d71b5`）——不为本瑕疵破冻结；勘误随 0.87.1/下版 CHANGELOG 处理。
- **P3-F2**：RECO 补录「28 票」与「Check 34 violations 24→0」的数量桥接未在 checklist 展开（28 票补录消解 24 violations 的关系可推断未明示）。两处主口径一致，非失实。
- **P3-F3**：任务 brief 口径「CHANGELOG 0.87.0 段…披露①~⑨」与实际不符——CHANGELOG 段为披露①~⑦，①~⑨ 在 release-checklist 披露清单。材料自洽无失实，属 brief 引用偏差（备案）。
- **P3-F4**：plan-tracker REL-084 行内注记「M-1 FEAT-059 审查中」滞后于 FEAT-059 行终态（M-1 GO 已达成、M-2 亦已完成）——叙述漂移，归 M-8 收口回填义务面。
- **P3-F5**：窗口 9 提交中 3 hash（`80d71b5`/`f11faa1`/`008efa6`）经 reflog 独立验证，其余 7 hash（`5e56021`/`a7f89ac`/`9aa27a6`/`80069a2`/`2ab3847`/`aa72c37`/`dd4537b`）未逐一 git 实证（无 Bash）——三文档同表+CHANGELOG+EVD 机录多源一致，M-5 现场 rev-list 义务兜底。
- **P3-F6**：checklist #16「交付时点 301,849」单源数值未在本轮实读面复现出处（疑在 EVD-1129/review-FEAT-059 链）；两个关键数（304,481 / 361,923）已双源验证不受影响。
- **P3-F7**：`core/releases/*.json` Glob 零命中含 0.86.0 manifest 未命中——工具面边界如实备案，不据此扩展任何断言；披露① 的收口以 Coordinator 提交批 check-release/ledger 复跑为准（#10 复跑义务/#14）。

## 5. 硬门槛裁决

| 门槛项 | 判定 | 依据 |
|---|---|---|
| 发布检查清单全部 PASS（逐项有证据） | **PASS** | §3 维度 1——12 项实测+2 项如实标注期义务+1 项未排程如实；门禁表回填真实性抽查零失实（§2.1） |
| 回滚方案存在且（结构）已验证 | **PASS（附 P2-F1 建议）** | §3 维度 2——结构核对三重印证+先例同型裁决；非阻断 |
| CHANGELOG 用户视角完整 | **PASS** | §3 维度 3——四段+行为变更+披露+semver 全覆盖 |
| breaking changes 已标注 | **PASS** | 「Breaking changes：无」显式论证（L11 逐项）+ B-9/B-10/B-11 升级说明义务条款在场 |
| Feature Flag 关闭验证 | **PASS（N/A 论证成立）** | 本版零 flag 出货；B-9 fail-closed 即安全兜底/B-10 acquire 幂等重取内建恢复/B-11 版本级回滚即触发-生效路径 |
| 版本号合规 | **PASS** | MINOR 论证充分、无跳号、无预留占用 |

## 6. 结论

**APPROVED_WITH_NOTES（unresolved_blockers=0）—— M-3 Release 半面 GO。**

0.87.0 发布就绪链在 Release 半面的全部复验重点（门禁表回填真实性/九失败修复链披露/披露①~⑨/REQ-092 姿态/B-9 红线/no-overclaim+5 维度+AI 专项）零 BLOCKING；P2×1 + P3×7 全部非阻断并已给出跟踪/收口路径。** Coordinator 面期义务不因本结论免除**：① candidate manifest 创建+提交批 → #10 复跑（期望 NATIVE_CANDIDATE PASS）+ #14 check-release；② M-4 go/no-go 呈现（DEC-226 预授权形态）；③ 本报告结论 + Design/Code 半面结论经 review-record CLI **机录**（M7.5——禁手写 REVIEW 行），引用路径 `docs/reviews/review-REL-084-M3-RELEASE-R0.md`；④ P2-F1 演练建议裁决留痕；⑤ M-8 收口清单（含 P3-F4 漂移回填）。

---
*REL-084 M-3 Release 半面 R0（2026-09-21，Release Reviewer Agent）。事实基线：四件套/CHANGELOG/plan-tracker/EVD-1130~1131/reflog/loop_runtime_claims.py/test_loop_runtime_claims.py/contract_matrix snapshots.json 全部实读实查（工具面 Read/Grep/Glob——未复跑门禁命令，数值以 M-2 实测记录为事实源）；reflog 实证 `80d71b5`/`f11faa1`/`008efa6` 提交存在性与消息；`review-REL-084-RELEASE-R0.md` 为 M-0 期留档不可覆盖——本报告消歧落盘。未验证面（pytest 复跑/R5 精确计数/ledger 复跑/0.79.0 原文/7 个未抽验 hash）一律如实标注，不写通过。*
