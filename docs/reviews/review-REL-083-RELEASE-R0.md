# Release Review — REL-083（RELEASE R0）——0.86.0 M-1R 发布半面独立审查

> **审查对象**：工作树未提交四件套 `docs/release/{release-plan,release-checklist,rollback-plan,feature-flags}-0.86.0.md`（git status 实测 4 个 untracked，与申报一致）
> **审查依据**：DEC-220/221/222/223/224 · EVD-1102~1119 · 0.85.0 四件套先例（FEAT-054 + REVIEW-FEAT-054-RELEASE-R0/R1）· version-plan-0.86.0 §3/§5.5 · benchmarks/closure/protocol.md（m0-r1 冻结）· CHANGELOG 0.86.0 段（`44831b8` 冻结版）
> **审查轮次**：R0（首轮；无前轮 findings 比对义务）
> **审查方式**：只读审查 + 独立复验（7 项实跑/实读）；未修改任何产品代码与 `.governance/` 数据；未执行 tag/push/transition
> **结论**：**APPROVED_WITH_NOTES · unresolved_blockers=0**（P0=0 / P1=0 / P2=2 / P3=3）
> **M-3 裁定**：**GO**——0.86.0 可进 M-4/M-5 transition+tag（DEC-221 预授权承载；本次审查义务不免除且已履行）。两项 P2 建议随 Coordinator 提交批（该批本就触碰四件套与 manifest）一并处置，不构成 GO 前置阻断。

---

## 1. 总结论与计数

| 项 | 值 |
|---|---|
| 总结论（四态） | **APPROVED_WITH_NOTES**（保留备注的通过终态——无未解决 BLOCKING finding） |
| `unresolved_blockers` | **0** |
| findings 计数 | BLOCKING/P0 = **0** · P1 = **0** · P2 = **2** · P3 = **3** |
| 门禁申报复验 | 门禁 #1~#16 申报中可独立复核面（#1/#2/#8/#10/#11/#12/#16 + 量测专节）**全部实跑/实读证实**，零失实申报 |
| no-overclaim 复核 | 四文件边界 token 齐备；CHANGELOG R-F10 固定措辞逐字在场；维度① NOT_EVALUABLE 未被宣传达成 |
| 真实环境防护 | sandbox 零写入主张经双侧交叉核验成立（§4 复验 V7/V8） |

## 2. 独立复验表（Reviewer 实跑——非转引 Developer 申报）

| # | 复验项 | 命令/方法 | 结果 | 与申报对照 |
|---|---|---|---|---|
| V1 | 混沌套件复跑 | `pytest tests/test_closure_chain.py -q` | **35 passed（46.57s）** | ✓ 一致（申报 35P/40.07s——耗时方差正常） |
| V2 | 批 1/2 交付套件抽跑 | `pytest test_contracts + test_governance_store + test_task_row_update + test_triage_write_guard + test_baseline_metadata -q` | **405 passed + 49 subtests（4.59s）** | ✓ 与全量 3,820P/0F 申报无矛盾（抽跑面全绿；全量未重跑——以申报+抽跑+V1 三点交叉采信） |
| V3 | release-ledger 复跑 | `verify_workflow.py release-ledger --version 0.86.0 --no-remote` | **exit 1——`cannot read release manifest: FileNotFoundError`** | ✓ 与 #10 披露逐字同型（预提交态预期；manifest 确未建） |
| V4 | LRC gate 复跑 | `verify_workflow.py check-loop-runtime-claims` | **BLOCKED / verdict_scope=semantic_only / semantic_units=300,706 > 300,000 / payload 15.3MB** | ✓ 与 #16 披露一致；申报 300,701 → 复跑 300,706（+5 漂移）**反向佐证活数据增长归因**；零 claim 违规 finding 属实 |
| V5 | archguard 棘轮复跑 | `verify_workflow.py archguard-ratchet` | **PASS 0 violations；R5 cli keys 95/95 + segments 71/71；R6 205 Δ0；R7 regen deterministic=True** | ✓ 逐位一致 |
| V6 | 版本一致性复跑 | `verify_workflow.py check-version-consistency` | **PASSED（exit 0）；唯一 WARN = plan-tracker 0.85.0 ≠ expected 0.86.0** | ✓ 与 #1/#2 披露一致（过渡态预期） |
| V7 | 量测 journal 抽验 | 解析 `%TEMP%\rel083-sandbox\.governance\closure-events.jsonl` | **19 行 / 3 units；closure-id 三元组（`closure-45773c16…`/`closure-375ec112…`/`closure-0123456789abcdef…`）与 checklist 完全一致且与 closure-locks/ 三锁文件互证；每 unit cas_version 严格 +1（5/7/7）；A 组 EVD-1120（op-bc473e5b…）+ C 组 `anchor present (row reused, no re-append)`（EVD-1122 零重复）**；handshake marker `post-step-effect__append-evidence.reached` 在案 | ✓ 单调性/effects_exactly_once/kill+resume 叙事全部实证 |
| V8 | 真实 .governance 零写入交叉核验 | 反向检查真实治理数据 | 真实 `.governance/` **无** closure-events.jsonl、**无** closure-locks/、evidence-log **无** EVD-1120/1122 行、plan-tracker **无** VAL-861 行 | ✓ 零写入主张从真实侧成立（与 sandbox 侧产物存在互补互证） |
| V9 | 区间事实复算 | `git rev-parse v0.85.0^{commit}` / `rev-list --count` / `log --date` | peel=`c2cc7c1`（taggerdate 2026-09-20 01:53:52 +0800）；`c2cc7c1..44831b8`=**5**；`ffcb787..44831b8`=**1**；批 2 四提交（09:23/09:59/11:22/13:48）+ bump（14:52）**全部在 tag 之后** | ✓ 与两文件区间披露逐位一致 |
| V10 | 表格 ragged-row 扫描 | 逐行管道符计数（转义感知） | 四文件 **0 ragged**（FIX-365 教训履行） | ✓ 自检声明属实 |
| V11 | CHANGELOG 口径抽验 | 读 `project/CHANGELOG.md` 0.86.0 段 | B-3/B-4 行为变更节与 feature-flags/rollback-plan 引用逐字同源；披露①（8 事故链）/披露②（R-F10 固定措辞「基线不可评估（无可信历史 trace）——未宣传达成」）在场 | ✓ 引用链完整 |
| V12 | LEGACY_REVERTS 正交性 | 读 `behavior_profile.py` | LEGACY_REVERTS 全为 REVERT_CLASS_PERFORMANCE（FEAT-034 族等）；`SAFETY_INVARIANTS` 与之互斥且 `revert_contract_issues()` 机检守护 | ✓ feature-flags §4 正交性主张成立 |

## 3. Findings

> 无 BLOCKING（P0/P1）。以下 P2/P3 均为非阻断跟踪项。

### P2-1 · rollback-plan §6 触发表行 3「轨道 B 撤执法面」语义不成立

- **事实**：write-guard 执法面（FEAT-057）落库于 `ffcb787`——即轨道 B（`ffcb787..<tip>`）的**区间下界**。git 区间/ revert 语义排除下界自身（本文件论证① 同一语义），故轨道 B revert **保留** `ffcb787` 的全部 diff（含执法面）。§6 行 3 写「回滚（轨道 B——保载荷撤执法面不可行时轨道 A）」，其「保载荷撤执法面」经轨道 B **不可达**。
- **影响**：WARN 风暴应急场景的 runbook 误导——操作者可能误以为轨道 B 能撤掉误报执法面而实际撤不掉，贻误处置。§1 影响分类表对执法面的双轨判定（「轨道 A 回退后执法面消失」）本身正确，缺陷仅限 §6 行 3 一行。
- **建议处置**：候选提交批（该批本就修改本文件族）修正该行——可行路径实为两条：单提交 revert `ffcb787`（保留 FEAT-055/056 + bump；注意 bump 面依赖需评估）或直接轨道 A；按实际意图改写。

### P2-2 · version-plan §5.5 R-F11「对账快照执行点」M-2 证据缺口

- **事实**：R-F11（Release R1 审定版）：起点=批 1 首票派发前快照；终点=批 2.3 完成时快照；M-2 执行比对（差异 vs 操作记录）；**证据入 release checklist + EVD**。实测：checklist 全文无「对账快照」承载（grep 0 命中），decision-log 无顺延/豁免裁定。
- **影响**：经审定发布半面 R1 的版本计划义务在 M-2 执行记录中静默缺失——「零手写验收」的快照差异 vs 操作记录比对证据链断裂（write-guard amnesty 基线与 EVD-1114~1118 操作记录可作部分替代证据，但不等于 R-F11 要求的起止快照比对）。
- **建议处置**：Coordinator 二选一并留痕：①补做比对（批 1 起点状态可由 git/机录操作记录重构）补入 checklist+EVD；②显式顺延裁定入 decision-log（0.87 候选），不得静默。

### P3-1 ·「A 清单 7 项」标签不可追溯且枚举计数不符

release-plan L77 / checklist L66·L164 引用「A 清单 7 项」——该清单在 version-plan/DEC/规划文档中**无定义出处**（grep 全 docs 仅四件套自引）；且 release-plan L77 枚举实为 8 项（verify/pytest/archguard/contract-matrix/三 profile/混沌/量测首跑/e2e+dsh）。建议：定义该清单或修正计数为可追溯表述。

### P3-2 · 量测对照数字「≈5+ 次交互」溯源薄弱

checklist 量测表对照论证引用「历史手工闭环同工作面 ≈ 5+ 次交互」——其数字源（EVD-1101 记 4 段 / boundary-audit 记 5-8 步）恰是 version-plan §3 R0 修订**明确撤回**的待核实陈述（「无 provenance…不得合并为单一数字」）。因已标注「机制叙述非达成主张」+ 维度① NOT_EVALUATED 固定措辞在场，不构成 overclaim；但建议后续措辞定性化或锚定单一可核出处。

### P3-3 · protocol §5 runs/ 工件未落盘 + TEMP sandbox 保质风险

`benchmarks/closure/runs/`（manifest.json/results.jsonl/summary.md）尚未创建（.gitignore 已在位；checklist 已按「runs/ 由创建批落盘」口径移交 Coordinator）。量测原始 journal 目前仅存于 `%TEMP%\rel083-sandbox`（有系统清理风险）。建议：M-8 Coordinator 落账量测 EVD 时，同批将 closure-events.jsonl + 三锁文件 + handshake marker 副本按 runs/ 规格落盘本地保留。

## 4. 审查重点逐项裁定

| # | 重点 | 裁定 |
|---|---|---|
| ① | 门禁结果真实性抽查 | **属实**——V1~V6 独立实跑零失实；申报数值与复跑一致（LRC units +5 漂移为活数据自然增长，佐证而非矛盾） |
| ② | 回滚区间双轨裁决 | **见 §5 专节**——双轨披露正确、非等价性如实、triage 锚登记合规；一处例外（P2-1 §6 行 3） |
| ③ | 量测方法学 | **合格**——sandbox 纪律双侧互证（V7/V8）；往返计数 2≤2 引用协议 §1 规则 1.1/1.3 准确（触发 1 + 结果确认 1；引擎零 LLM 往返）；维度① R-F10 固定措辞逐字在场（CHANGELOG 披露②）；cases 三路径判定四项全过且与 journal 实证互证；P3-2/P3-3 为边缘注记 |
| ④ | LRC BLOCKED 披露充分性 | **充分**——#16/披露⑨ 完成三重区分：容量越线（300,701>300,000，超 0.23%）≠ claim 违规（findings 零违规项）≠ 本票引入（0.85.0 发布当日活数据增长；V4 复跑 +5 反向佐证）；与 0.85.0 先例（#11 LRC semantic PASS 态）不同态但同「如实披露不包装」口径；fail-closed 提前 return 语义如实（identity 面未出账已披露，复跑义务在案） |
| ⑤ | 四件套完备性 + 8 事故链 + 0.87 移交 | **成立**——对照 0.85.0 四件结构逐节为超集（新增：回滚区间锚定节/量测专节/#12~#16/§7 事故链/§8 移交；0.85.0「Gate 10 明细指引」折叠入 M-2 执行序纪律，无实质缺面）；8 次事故披露链三处同源互证（CHANGELOG 披露① + checklist 披露④ + rollback §7 专节，数字演进 5→7→8 如实注记）；0.87 移交清单 §8 实数 **9 项** ✓ |
| ⑥ | B-3/B-4 与灰度开关正交性 | **成立**——V12：LEGACY_REVERTS 全 performance 类 + SAFETY_INVARIANTS 机检互斥；「不存在 legacy 模式关闭 write-guard/closure-chain 的中间态」与 §5 不可回滚项 4 自洽 |
| ⑦ | manifest 缺建处置 | **先例符合**——V3 实证 manifest 确未建；triage files 锁面仅四件套、manifest 移交 Coordinator 提交批为锁面纪律的正确执行（0.85.0 先例 602a794 三件套+manifest 同 commit 的形态差异已如实分述——checklist #10 特意区分「未 staged」与「未创建」两型 FAIL）；收口义务（ledger 复跑期望 NATIVE_CANDIDATE + check-release candidate）在 #10/#14/披露①/M-8 四处闭环 |
| ⑧ | AI 专项 | **通过**——四文件 no-overclaim 五 token 齐备；无 loop-runtime 活体声明（V4 实证零 claim 违规 finding）；「隔离验收不等于真实外部环境验证通过」限定语在位；预授权链（DEC-221）语义如实转述（「预授权不免除门禁」三处出现） |

## 5. 回滚区间双轨裁决意见（M-3 核心义务——裁定如下）

**区间事实（V9 独立复算）**：`v0.85.0` peel = `c2cc7c1`（2026-09-20 01:53:52 +0800）；批 2 四提交（`a5dec3d`/`a7474e4`/`7709987`/`ffcb787`）+ M-1 bump `44831b8` **全部位于 tag 之后** ⇒ 完整行为窗口 = `c2cc7c1..<发布 tip>`；`ffcb787..44831b8` = 1（仅 bump）⇒ triage 锚 `ffcb787..<tip>` 撤销集 = M-1 bump + M-1R/发布材料，**不含批 2 行为载荷**。

**论证①② 裁定：均成立。** ①`44831b8..` 下界误写致 bump diff 残留 = 版本-载荷不一致混合态（0.81.0 F-01 同形），「禁用 `44831b8..<tip>`」正确；②终点必须为 M-5 transition 提交（0.81.0 F-04 + 0.84.0 P-12 双先例），不预填 hash 正确。

**双轨裁定**：
1. **轨道 A（`c2cc7c1..<发布 tip>` revert）= 完整行为回退的唯一区间，为主轨/推荐轨**——与 0.85.0 先例「整窗口径」（`3663423` 锚定）语义同型。所有以「回到 v0.85.0 行为」为目标的触发条件（rollback §6 行 1/2/4 数据完整性类）MUST 走轨道 A。
2. **轨道 B（`ffcb787..<发布 tip>` revert）仅适用于窄场景「撤销发布包装、保留批 2 载荷待重切」**（含 §2.3 发布前中止 `reset --hard ffcb787`）。其落点树为「版本声明 0.85.0 + 批 2 能力在场」的**混合态**，任何文档与操作口径不得将其表述为「回滚到 0.85.0」（rollback-plan 已按此措辞，合格）。
3. **任务简报所引 triage 锚 `ffcb787..<tip>` = 轨道 B 锚定**——四件套「按指令登记 + 如实披露轨道 A 为完整行为回退唯一区间 + 交 M-3 裁决」的处置**正确且优于 0.85.0 单轨表述**（0.85.0 先例将简报锚降格为「载荷对照窗口」，本版将其升格为有明确适用场景的正式轨道，语义更完整）。
4. **例外修正（P2-1）**：§6 行 3「轨道 B 撤执法面」不成立——执法面在轨道 B 下界之前（区间排除下界），随轨道 B **保留**。修正前，WARN 风暴场景应按「单提交 revert `ffcb787` 或直接轨道 A」执行。
5. **演练缺位裁定（回应 checklist #15 之问）**：不为阻断项——0.85.0 先例同型（无演练票发布），且双轨 revert 的终点依赖 `<发布 tip>`，pre-tag 演练在结构上不可完整执行；区间语义已由本审查以 rev-list 计数独立实证。建议作为 M-5 后应急就绪项（隔离副本 + 真实 tip 生成后双轨各一腿），登记 0.87 候选或提交批裁量。

## 6. M-3 go/no-go 裁定（DEC-221 预授权语境）

**GO。** 0.86.0 可进 M-4/M-5 transition + tag：

- M-2 可独立复核门禁面（verify / 版本一致性 / 三 profile hard 预算 / archguard R1~R7 / contract-matrix / 混沌 35 / 量测首跑 / ledger FAIL 形态 / LRC BLOCKED 形态）经本轮独立复验**零失实**；
- 预授权不免除审查的义务已履行：本报告即为 M-3 Release 半面独立审查产出；复审必达条款由 Coordinator 按 M7.4 消费本结论；
- 两项 P2 建议随 Coordinator 提交批处置（修正 §6 行 3 + R-F11 补做或显式顺延）——该批本就触碰四件套与 manifest，边际成本最低；**不构成 GO 前置阻断**，但若提交批选择不处置，须在提交批披露中如实登记；
- M-5 后期义务提醒：candidate manifest 创建后复跑 ledger（期望 NATIVE_CANDIDATE PASS）+ check-release candidate；tag 后 `--remote` + released 门禁；量测 EVD 落账引用本审查 V7 实证与 runs/ 副本归档（P3-3）。

## 7. 边缘问题（移交 Coordinator / 0.87）

1. §6 行 3 轨道 B 措辞修正（P2-1——提交批顺手修最经济）；
2. R-F11 对账快照补做或显式顺延（P2-2——须留痕，不得静默）；
3. 「A 清单」定义或计数修正（P3-1）；
4. 量测对照数字定性化（P3-2）；
5. runs/ 副本归档防 TEMP 清理（P3-3——M-8 落账时点）；
6. LRC identity 面复跑时点（提交批，与 ledger 复跑同窗）；
7. 量测边缘观察 4 项（checklist 已登记 → rollback §8 移交 #9，维持）。

---
*REL-083 M-3 Release 半面 R0 审查冻结（2026-09-20，Release Reviewer Agent）。事实基线：全部复验命令于 2026-09-20 当场实跑（V1~V12）；区间/hash 取自 `git rev-parse`/`rev-list`/`for-each-ref` 实测；journal/锁文件/handshake 取自 `%TEMP%\rel083-sandbox` 实读；真实 .governance 零写入经反向交叉核验。本报告为只读审查产物——未修改产品代码与 `.governance/`；review-record 机录由 Coordinator 按 M7.5 执行（Review 不手写 REVIEW 行）。*
