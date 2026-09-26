# Review — REL-092 · RELEASE R0（0.89.0 M-1R 四件套）

> **Task**: REL-092（P1）· **审查对象**: commit `bb6a460`（4 files，+604/−0：release-plan / release-checklist / rollback-plan / feature-flags -0.89.0.md）· **Round**: R0（首轮）· **审查日期**: 2026-09-26 · **Reviewer**: Release Reviewer Agent（独立只读审查）
> **票面**: plan-tracker REL-092 行 + execution-packets REL-092 短包 · **先例**: REL-088（0.88 四件，结构参照树 a8a72a3）· **依据**: agents/release-reviewer.md + skills/release-review/SKILL.md
> **结论（四选一）**: **APPROVED_WITH_NOTES · unresolved_blockers=0**（P0/P1/P2 = 0；P3×4 非阻塞备注）

---

## 1. 申报核验（EVD-1183 事实依据逐项——亲验复现）

| # | 申报项 | 申报值 | Reviewer 亲验 | 裁决 |
|---|---|---|---|---|
| 1 | 四新文件 commit | `bb6a460`（4 files changed, 604 insertions） | `git show --numstat bb6a460`：feature-flags 81 / checklist 192 / release-plan 121 / rollback 210，合计 604 insertions 0 deletions；四文件恰为 TRIAGE-REL-092 expected-new 锁面，**无锁面外夹带**；且 `git diff bb6a460 HEAD -- <四文件>` 为空（工作树与提交一致） | ✅ 一致 |
| 2 | 窗口计数 | `git rev-list --count 33d19b0..HEAD`=12（describe v0.88.0-12-gb66bd25） | 亲跑：`33d19b0..b66bd25`=12、`git describe --tags b66bd25`=v0.88.0-12-gb66bd25；`33d19b0..HEAD`(=d6186ee)=14（候选后两提交 `bb6a460`+`d6186ee`——文档已显式锚定 HEAD=`b66bd25` 并声明「区间计数不写死，M-5 现场取值」） | ✅ 一致（时点绑定如实） |
| 3 | check-cross-references | PASS 77 文件/727 引用/0 dangling/0 deprecated/0 circular | **亲跑复现：Files scanned 77 / References 727 / 三项 PASS / exit 0——逐字一致** | ✅ 复现 |
| 4 | check-manifest-consistency | PASS（917/1055） | 亲跑 PASS：Canonical **917（与申报精确一致）**/ Actual 1060（+5 = 申报时点后新增文件面——四件入库前后与 review-REL-091 报告落档 d6186ee；检查 PASS，canonical 不变量恒等） | ✅ 复现（actual 漂移为候选后增量，非申报错误） |
| 5 | check-version-consistency | PASSED | 亲跑：PASSED——all version declarations consistent，exit 0 | ✅ 复现 |
| 6 | Check 28s 现值 | 1,761,442B / 1,434 行（2026-09-26 实测） | 当前 evidence-log 实测 1,763,204B / 2,812 总行 / **1,435 非空行**——字节差 +1,762B ≈ EVD-1183 行本体；非空行 1,435 = 申报 1,434 + EVD-1183 一行。「行」口径 = 非空行（非总行）自洽；申报已注明「M-2 前置归档席执行时以当场实测为准」 | ✅ 自洽（时点绑定） |
| 7 | 各票审查终态 | FIX-390/391/392/393 R0 AWN/0、FIX-394 R0 AWN→R1 APPROVED、FIX-395 R0 NC→R1 AWN、FEAT-065 R0 AWN/0、REL-090 双 AWN/0、REL-091 AWN/0 | docs/reviews/ 逐份在案（见 §2-⑧）；FIX-395 R0 NEEDS_CHANGE→R1 在四件中如实呈现（checklist L41/release-plan L48），无终态美化 | ✅ 一致 |
| 8 | census 51 vs 49 | 取自 review-REL-091-RELEASE-R0 P2-1 | 报告 L27 实证：「复审实测 **51 issues（exit 0）**——+2 漂移未获逐条归因 → **P2-1**」；四件将其承载为 M-2 专席①对账义务（非擅自归因） | ✅ 一致 |
| 9 | quality-tools | NOT_RUN 不虚报 | 与 version-plan §4.6/ADR-010 口径一致；#16 如实标注 M-5/M-6 批义务 | ✅ 如实 |

**机录凭证**：EVD-1183 带 `governance-store evidence-append op-229dfcff107f42d296738e3957aaafe2`（schema v1）——非手写行。✅

## 2. 八项审查范围逐项结论

**① 四件结构对照 0.88 先例**：✅ 无缺节。release-plan 八节（保守边界/版本号与授权链/发布范围〔载荷构成+不发布什么〕/回滚区间锚定/M 链状态/发布窗口/门禁摘要/硬门槛自检）与 0.88 全同构；checklist 十节全对应（专席 0.88×4 → 0.89×6 为增量席，超额非缺位）；rollback 十四节全对应（§7 由「回退显式化专节」改题「引用不触发专节」= version-plan §7 口径的如实语义调整，非缺面；§8 路径区分/§9 候选池两节承袭 0.88 §8/§9）；feature-flags 八节全对应（§5 由 FIX-375 索引位转为行为修正三面索引——同位职责承接）。

**② 事实链核对**：✅。**13 个 git 锚全部亲验**（hash/日期/主题逐条对上）：七票 `8a94d64`(10:24)/`3cb4048`(12:17)/`def9508`(14:08)/`65c8e4b`(15:23)/`7795f59`(17:31)/`c9b7415`(18:27)/`ab7a8e1`(19:31)+`b950fef`(19:54)；M-0 `76c86a9`(09-25 23:34)；M-1 `b66bd25`(20:31)；前版收尾 `2dac7af`(20:06)/`9347c11`(20:12)；区间下界 `33d19b0`=`git rev-parse v0.88.0^{}` 同一、tag object `82905e6`、taggerdate 2026-09-25 20:08:32 +0800 亲测。checklist Change Inventory 12 行与 `git log 33d19b0..b66bd25` 完全一致。M 链全表（release-plan §M-链状态）八行状态如实：M-0 ✅/七票 ✅/M-1 ✅ 已落库/M-1R 🔄 本票/M-2~M-8 ⏳ 期义务——无超前勾选（checklist 发布步骤 M-1R 勾选框正确留空「本票交付后勾选」）。**DEC-244~248** 全部在 decision-log L186~190（机器写入 op 锚五枚），子条引用逐条核对一致：DEC-244 必选六项+五前置不激活+激活票不捆绑 ✓；DEC-245 M-1→M-8 授权+arch 决策点+M-4 go/no-go 前置+安全语义不削减 ✓；DEC-246①③④⑤⑥⑦⑧⑨（主序列/census 身份集/方案 A/组合四组/措辞收紧/4119P 基线口径/manifest—ledger—tag 绑定）✓；DEC-247 Check 30 V3 链内轮次+census 30→25 ✓；DEC-248①②③④⑤（锁面两文件/FEAT-066 拆出/四红线/不得按原票面宣称完成/version-plan §2 行 6 勘正）✓。**EVD-1171~1183 全部存在**（evidence-log 实查 13/13）。EVD-1176 关键事实五项（26318/26193/P3-4/live 75→75 勘正/sanctioned）逐项 Contains 实证。

**③ 六专席齐备性**：✅ 全部就位且各带事实链+M-2 回填义务——专席① census 对账（P2-1 51 vs 49 分段归因，P3-2 分段快照随行）；专席② archguard sanctioned regen（EVD-1176 路由 + 0.88 M-2 先例 `501d8dc` 亲验实锚：REL-086 M-2 sanctioned regen 锚 25462→26193；「载荷票未完不中途 regen」前置已满足——七票已集成）；专席③ Check 28s 前置归档（DEC-246④ 方案 A 五步 fail-closed 执行序，dry-run 先行、活跃链行停机上报纪律）；专席④ 窗口激活后 18/18b live 复测（EVD-1176 P3-4 路由 + 「禁以 fixture 绿冒充 live 绿」fail-closed 措辞）；专席⑤ FEAT-065 双面演示（DEC-248④ 面 A/面 B 分别演示不混一 + 四红线复确认）；专席⑥ 组合②列补充（F-1：verify_workflow.py 三票共面——FIX-393 腿共存面补测 + DEC-246⑤ 判据要点并入）。

**④ 回填位纪律**：✅ 零预填。checklist #1~#17 全部 ⏳ 待回填或「未排程维持」如实标注；M-2 数值/regen 目标（「待实测不预填」两处显式）/tag/`<发布 tip>`（「本文件不预填」三处显式）/09-30 风险窗结论（披露⑦「本票零预填」）均无预填；quality-tools NOT_RUN 不虚报；#10 ledger 预提交态「预期 FAIL」如实归类非豁免。全文未发现任何未实测项写成通过。

**⑤ 回滚方案**：✅。区间锚定亲验（`33d19b0..b66bd25`=12、describe 交叉印证、12 提交构成与 §窗口构成逐条一致；终点 MUST 为 M-5 transition 提交——0.81.0 F-04 教训在案）；B-12/B-13 引用不触发——0.88 版 `rollback-plan-0.88.0.md` §7（L153「B-12/B-13 回退显式化专节」）与 §8（L174「回退路径区分」）**双锚存在性亲验通过**，且本机 `.write-guard-posture.json` 与 `.decision-store-state.json` 双双缺席（引用不触发前提实证）；§2.1 步骤 1b 第一层确认程序在场；FEAT-065 行为修正回退路径可执行——`closure_chain.py` 与 `tests/test_closure_chain.py` 两文件存在性亲验通过，且 `ab7a8e1` numstat 恰为该两文件（DEC-248① 锁面逐字一致）；FIX-391 同文件事实成立（`c9b7415` 亦触 closure_chain.py）→「整窗 revert 禁单票选择性还原」注记有事实依据（§1 警告行+§5 #6）；路径 A/B 区分 + §3 数据安全 + §4 验证 13 项 + §6 触发条件 8 项齐备；回滚演练未排程如实标注（0.85~0.88 四版先例同型，0.88 版同款措辞在案）。

**⑥ feature-flags 与 CHANGELOG 一致性**：✅。「无新增功能激活」声明与 `project/CHANGELOG.md` 0.89.0 段行为变更节同源同口径（DEC-246⑥ 措辞）；B-12 全 WARN（姿态文件缺席实证）/B-13 MD_ACTIVE 缺省缺席（状态文件缺席实证）与 CHANGELOG「0.89 无 --activate-block 执行/无真实切换」逐字对齐；行为修正三面（①FEAT-065 gate 闭集 ②FIX-391 零写拒绝 ③判据收敛不放宽）在 CHANGELOG/feature-flags §5/checklist 行为变更表/rollback §1 四面同口径；B-x 序列止于 B-14 一致；五前置核验（①②④⑤一致/③ 11≠3 口径漂移如实转述）与 version-plan §5 回填面一致。

**⑦ cross-refs 亲跑 + 四文件互引**：✅。亲跑 PASS（77/727/0/0/0，与申报逐字一致）；四文件互相引用全部可解析（release-plan ↔ rollback §区间锚定同锚同源 / checklist → rollback §1/§4/§7/§8 + feature-flags §5/§6/§7 / feature-flags → checklist 专席⑤ + rollback §1/§7 / rollback → feature-flags §6）。

**⑧ Developer 申报核验**：见 §1——EVD-1183 九项事实全部亲验复现或时点绑定自洽，零虚报。

## 3. 发现清单（P0-P3 分级）

| # | 级别 | 位置 | 发现 | 处置建议 |
|---|---|---|---|---|
| F-1 | **P3** | release-plan L53（载荷表⑥行） | 「审查报告留档 **11 份**」但括号列举 **12** 个报告名（含 review-REL-091-RELEASE-R0——该报告于后继提交 `d6186ee` 才入库，`bb6a460` 时点 docs/reviews 确为 11 份 0.89 窗口报告，已 `git ls-tree` 实证） | 计数与枚举口径对齐即可（M-5 回填批顺带）；不阻塞 |
| F-2 | **P3** | rollback-plan §3（B-12 工件行） | 「`.write-guard-violations.json`（违规台账）在健康宿主为零足迹或缺席」与本机实态不符：该文件在场（25,364B，33 枚 break-glass grant），其中 2 枚签发于 0.89 窗口内（2026-09-25T23:05 / 2026-09-26T12:21）。安全结论不受影响——posture 文件缺席=全 WARN 实证、无激活主张、回滚零触及（gitignored）、§4 #11 验证期望仅姿态文件缺席 | 措辞收紧（「台账可含历史/测试 grant 记录——回滚零触及」）；建议 Coordinator 对窗口内 2 枚 grant 做一次例行归因 glance；不阻塞 |
| F-3 | **P3** | release-plan L114/L115、rollback L3（先例引用） | 「REL-088 commit `a8a72a3` 形态」作 commit-of-record 引用欠精确：0.88 四件实际入库于 `72ddffb`（REL-087 M-1 bump 批），`a8a72a3` 为其后 1 行勘正+CODE 报告批；作为**树形态参照**有效（a8a72a3 树含完整四件，本次审查即以其为对照基准）。该引用口径源自派发票面，非本票新造 | 后续文档引用可改「0.88 四件（入库 72ddffb，形态参照树 a8a72a3）」；不阻塞 |
| F-4 | **P3** | EVD-1183（Developer 申报行） | 「git rev-list --count 33d19b0..HEAD=12」未随行复述 HEAD=`b66bd25` 限定（四件正文均有该限定）；行内 describe v0.88.0-12-gb66bd25 已无歧义锚定时点 | 与 REVIEW-REL-091 P3-2 申报纪律改进（census 附分段快照）同类——时点绑定值随行附锚；不阻塞 |

**P0=0 / P1=0 / P2=0 / P3=4（全部非阻塞备注）**。无 BLOCKING finding。

## 4. 硬门槛裁决

| 门槛项 | 阈值 | 裁决 | 依据 |
|---|---|---|---|
| 四文件逐行审查（+604 行不抽样） | 100% | **PASS** | 四文件 121+192+210+81=604 行全量精读（read 全文+git numstat 对账），无抽样跳读 |
| 亲跑 check-cross-references + git 锚亲验 | 亲跑非转述 | **PASS** | cross-refs/manifest/version-consistency 三命令亲跑（§1 #3~#5）；13 commit 锚+tag peel/taggerdate/describe/rev-list 亲验（§2-②）；回退两文件/0.88 双锚/501d8dc 先例存在性亲验 |
| 每条发现标注 P0-P3 | 100% | **PASS** | §3 四条全部定级（P3×4） |
| 只读约束（除本报告外零写入） | 零违例 | **PASS** | 全程仅读命令（log/show/rev-list/describe/rev-parse/ls-tree/for-each-ref/status/diff/Select-String）+ 三条只读检查命令；零 git 变更、零产品代码/治理文件写入 |
| 发布检查清单逐项有证据 | 100% | **PASS（回填位形态）** | 本票为 M-1R 材料票：#1~#17 全部为显式回填位 + 六专席义务承载——「未实测项写成通过」零发生；已实测项（cross-refs/manifest/version-consistency/区间/git 锚）全部亲验通过 |
| 回滚方案存在且路径可执行 | 显式+可执行 | **PASS** | 区间亲验 12 提交/B-12·B-13 引用不触发双锚在案+FEAT-065 两文件还原路径存在性实证+FIX-391 同文件禁选择性还原注记有据+路径 A/B+§4 验证 13 项 |
| CHANGELOG/feature-flags 一致 | 同口径 | **PASS** | 「无新增功能激活」同源；B-12 全 WARN/B-13 MD_ACTIVE 缺席双实证；行为修正三面四面同口径 |
| 版本号合规 | semver | **PASS** | 0.88.0→0.89.0 MINOR 顺延不跳号；载荷含新门禁面非 PATCH；Breaking changes=无论证与 CHANGELOG 一致；1.0.0 预留未触碰 |

## 5. 总结论

**APPROVED_WITH_NOTES · unresolved_blockers=0**

- 四件套成形且与 0.88 先例结构对齐（无缺节，六专席为增量）；cross-refs PASS 亲跑复现（77/727/0 dangling）；回滚区间锚定与 12 提交窗口 git 亲验一致；B-12/B-13 引用不触发前提实证（双工件缺席）；FEAT-065 回退两文件锁面与 git numstat 逐字一致；回填位零预填；EVD-1183 Developer 申报九项全部亲验复现或时点自洽，无虚报；`bb6a460` 无锁面外夹带。
- **P3×4 备注**（F-1 计数枚举口径 / F-2 violations 台账措辞与窗口内 grant 例行归因 / F-3 先例 commit 引用精度 / F-4 时点值随行附锚）——均为精度改进项，不影响发布材料可用性；F-1 可随 M-5 回填批顺带收口，F-2 建议 Coordinator 例行归因 glance。
- **遗留义务（非本票缺陷，期义务如实承载）**：M-2 门禁实测全席回填（前置归档席先行）→ M-3 双半面审查 → M-4 09-30 风险窗履行 + go/no-go → M-5 candidate manifest（本票锁面外，如实披露①）→ M-6 ledger → M-7 tag → M-8 归档收口。
- 复审链：本报告为 R0 终态（APPROVED_WITH_NOTES 为通过终态）；M-3 发布半面审查按链独立进行，不受本结论预支。

---
*Review-REL-092-RELEASE-R0 · 2026-09-26 · Release Reviewer Agent · 事实基线：全部结论基于本会话亲跑命令输出（git log/show/numstat/rev-list/describe/rev-parse/ls-tree/for-each-ref、check-cross-references、check-manifest-consistency、check-version-consistency、文件存在性 Test-Path、evidence-log/decision-log/review 报告/CHANGELOG/version-plan 实读 UTF-8）。未实测项一律如实标注，无代填。*
