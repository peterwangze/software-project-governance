# Review Record: REL-099 — M-3b 发布门禁审查（REL，R0）

- **Task**: REL-099（M-3b——0.95.0 发布包全量终审；并行面 M-3a Code Reviewer 版本面定向审进行中，本审查只审发布包面不审代码 diff）
- **Reviewer**: Release Reviewer Agent（角色定义 agents/release-reviewer.md 全文 + skills/release-review/SKILL.md 已加载并遵循；只读——零产品文件修改、零 .governance 写入、零用户交互；唯一写动作=本报告文件）
- **对象**: 0.95.0 发布就绪状态（发布包四件套：m-0-assembly / CHANGELOG 0.95.0 段 / release-checklist / rollback-plan + 治理面实读 + M-1/M-2 机检事实——以调度上下文记载为据，Bash 禁止契约）
- **日期**: 2026-10-05 · **Round**: R0（M3b）
- **结论**: **APPROVED_WITH_NOTES（unresolved_blockers = 0）** · P0=0 / P1=0 / P2=4 / P3=6

## 硬门槛自检

发布检查清单逐项有证据 ✅（§A~F 全有结论+锚，§C 逐命令预期值+状态+责任人）· 回滚方案存在且可执行 ✅（四要素齐备+三序结构+基线锚权威一致；本版未演练以机制先例承载——见 F-8 如实披露）· CHANGELOG 关键段全覆盖 ✅（Added/Changed/Fixed/Breaking 四段）· Breaking 标注=100% ✅（「无」+五点依据）· Flag N/A 依据充分 ✅（M10 为行为协议层非运行时旗标+无机制激活翻转+行为变更已按「非旗标面」披露+回退=git revert）· 事实红线遵守 ✅（未实跑项全部标注「未独立复核/待 M-2 机录」，零虚报 PASS）

## 一、审查输入实读清单

四件套：`docs/release/m-0-assembly-0.95.0.md`（135 行）/ `project/CHANGELOG.md` 0.95.0 段（L5~L41）+ 0.94.0 段残留核对 / `docs/release/release-checklist-0.95.0.md`（109 行）/ `docs/release/rollback-plan-0.95.0.md`（69 行）；feature-flags 件 N/A（不创建——§F 论证）。治理面：plan-tracker（L11 工作流版本、L80~L85 载荷五票+REL-099 行、L209 0.94.0 已发布行、L210 0.95.0 规划行、L481/482 REQ-146/147）；risk-log 热表全量（非关闭 21 行）；evidence-log EVD-1312~1317 六条全实存且 op 哈希与 m-0 §1.1 逐一对上（op-96b9…/op-b56a…/op-2e01…/op-a1b2…/op-f591…/op-0ce8…）；审查链四份报告实读结论核实：review-FEAT-085-DESIGN-R0 / review-FEAT-086-DESIGN-R0 / review-FIX-432-CODE-R0 / review-FIX-432-CODE-R1 **全部 APPROVED_WITH_NOTES + unresolved_blockers=0**（R1 含复审义务履行自检段：前轮报告全文实读+8 findings 逐条三态比对）。VERSIONING.md L9~L57 实读核依据。先例对齐：review-REL-098-M3b-REL-R0.md（AWN/0，P2=1/P3=4）。

## 二、审查维度逐项（7 面）

### 1. 范围一致性 —— ✅ PASS（带 F-4 形态 note）

- 五票 vs 版本行 vs 任务表：plan-tracker L80~L84 五票全「✅ 完成 (2026-10-04 入表)」，与 m-0 §1.1、checklist §A、CHANGELOG L8 四方一致；REL-099 行 L85 triaged 在表。
- 无范围漂移：FEAT-087（L86）/FEAT-088（L87）目标版本均 0.96.0 候选池，未混入本版；CHANGELOG L10 明示同口径。
- Slice-3 不计入 0.95.0：裁定依据核对成立——①DEC-312(7) M-0 冻结五票不含 Slice-3 且无 TRIAGE 机录/热表票行（L86/87 之外无 Slice-3 票）；②「留池 0.95+」（DEC-303(4)）为可用性窗口表述而非立项承诺，冻结载荷不因字面自动扩容；③无活性机器信号（R2 缓解在位：post-commit 全量=每 commit 覆盖，0.94.0 发布门 EVD-1311 达标）。论证链完整，与 L210 约束列②对位。
- 需求面：REQ-146 ✅ 已交付（L481，验收信号 2026-10-04 闭合）；REQ-147 🚧 规划中（L482）——CHANGELOG 与 m-0 §1.3 均只主张 Phase 0+有界 Phase 1，no-overclaim 口径一致。
- 形态缺口：L210「包含任务」列（`DEC-312, REQ-146, REQ-147, AUDIT-157✅(立项), AUDIT-158, FEAT-085, RISK-066`）**未列举 FEAT-086/FIX-432 两票**（不只是未标✅）——见 F-4。

### 2. 门禁证据 —— ✅ PASS（带 F-2/F-3 notes）

- checklist §C 逐命令有预期值+依据+状态：9 行全「⏳ 待 Coordinator/待 M-1 后/M-2/M-5/M-7/M-8」诚实标注，零虚报 PASS ✅（符合 release-review SKILL 事实红线）。
- M-2 机检事实（调度上下文 M-1 报告记载为据）与 checklist 预期一致性核对：13 处一致@0.95.0 ✅（=§C check-version-consistency 预期）、1052 OK ✅（=§C unittest 预期 1047+5）、预算零变化 ✅（=resident 4244/6000、M1+M2 342/370 同值）、全 PASS ✅；**唯 check-governance 基线口径 16 vs 1 失准**——见 F-2。
- 运行前提纪律在场（§ G-5 TEMP 仓库外路径——REL-096 根因先例延续）。

### 3. 回滚方案 —— ✅ PASS（带 F-7/F-8 notes）

- 存在且四要素齐备：步骤（三序：数据面先行声明/版本面 revert+确定性再生/载荷面按需逆序+ledger 处置）、验证 5 项、时间估计（≤60 分钟版本面/≤半工作日全量）、触发条件（P0 缺陷/一致性破裂/用户裁定/观察期信号）。
- 基线锚正确性：`v0.94.0@6da8d04`（candidate=4789f96→release=6da8d04，taggerdate 2026-10-04 annotated 4d4da76）与 plan-tracker L209 权威记载**逐项一致** ✅。
- 可执行性加分面：依赖链警告（FEAT-086→FEAT-085 断链/同文件多票禁单边还原/AUDIT 票 append-only 特殊面）+「受控整改优先于整体回滚」先例链（REL-095~098）+零新增数据面三声明（无 schema/无迁移/无旗标）三方互证（m-0 §版本定义+checklist §F+rollback §回滚分类）。
- 差距：hooks 安装实例交互面未覆盖（F-7）；无本版专属演练（F-8——确定性再生四版先例+0.92.0 隔离副本演练先例 EVD-1233+验证命令在位，如实披露不阻断，与 0.94.0 M3b F-3 同构裁定）。

### 4. CHANGELOG 用户视角 —— ✅ PASS（带 F-1/F-6/蓝军④ notes）

- 四段覆盖：Added×4（M10 协议/六平台通道/前瞻样本/Phase 0 基线）/ Changed×4（称谓 sweep/映射补行+validate/quote_sync/note 标记）/ Fixed×2（28b 漂移/F-A2）/ Breaking 显式段 ✅。
- 具体性：票级+机制级描述（非「修了几个问题」式泛化）✅；决策链/证据链段（DEC-312~316 + EVD-1312~1317 + 四份 REVIEW 全 AWN/0）与治理面实读一致 ✅。
- Breaking=无的五点依据充分：CLI/schema 零变更（消费点 .get 兼容）/无 MUST 规则删改（M10 纯新增+称谓统一非语义变更——DEC-316(1)）/manifest additive 新键（1021 一致 PASS）/无 Gate 语义与 governance schema 变更/1047 零回归实证（1052 待 M-2 复跑——**M-2 已实测 1052 OK（调度记载），M-8 收口时应将「待发布门复跑确认」落定为已确认表述**，见蓝军④）。
- 行为变更披露：L35「行为变更（用户可感知，非旗标面——本版无 feature flag 债务）」——回退路径明示 ✅。
- 准备态纪律：发布日期零预填（FIX-349 口径注释在场）+区间终值回填位+「不预编造」声明 ✅。

### 5. 版本号合规 —— ✅ PASS

- MINOR 理由成立（VERSIONING 实读）：L12 Minor 触发「新增 MUST 规则、新增 B/C 级自动化能力」+ L37「SKILL.md MUST 规则新增 → MINOR」——M10 EXP-01~05 为新增 MUST 行为规则，正中条款；非纯 bug fix，PATCH 不足以承载。
- bump MUST 触发实读核实：L49~L53 条目 1（SKILL.md 行为协议变更 M0~M10——L364 薄入口）、条目 2（references/ 变更——behavior-protocol.md 新增 M10 节+六 manifest note 标记）、条目 3（verify_workflow.py 检查扩展——quote_sync 维度）**三条全命中**（m-0 §5 引条目 2·3，实际依据面更宽，非缺陷）。
- 不跳号：0.94.0 已发布（L209/tag 权威）→ 0.95.0 = MINOR+1 ✅；预留合法性：DEC-312(5) 用户 2026-10-04 裁定正式预留 + VERSIONING L122「已预留版本号不可占用」语义正向满足（本版内容=预留内容：Phase 0+有界 Phase 1）✅。

### 6. 风险关闭 —— ✅ 无发布阻断级

实读热 risk-log 非关闭 21 行（状态「打开」15 + 缓解中 2 + 降级 2 + 已缓解 1 + 已收窄 1；调度口径「17 open」存在计数口径差——F-10 披露）。逐族评估：

- **RISK-066（高，「做薄」执行风险）**：触发条件=「Phase 2/3 执行期（**0.96.0+**，Phase 0 分类完成前禁止任何卸载动作）」——本版载荷零卸载动作（Phase 0 分类已交付、Phase 2/3 未启动），不在触发窗口；复评 2026-10-31 与「0.95.0 立项窗内完成 Phase 0 分类后复评」注记自洽（Phase 0 已随本版交付，复评窗在位）。**不阻断** ✅。
- 观察期族（RISK-062 词集观察/RISK-064 quick-full 口径/RISK-065 排除面）：0.94.0 交付面登记观察项，复评窗均 2026-10-31，非本版引入、非门禁面 ✅。
- 触发条件不满足族：RISK-059（真实权威切换启动时才触发——本版无切换）；RISK-050（dsh 上游漂移——护栏在位，非本版载荷面）✅。
- 长期治理链族（RISK-039 架构腐化/RISK-055 验收尾巴/RISK-052~058 测量与注入面）：历史多版共存、有治理链承载，无本版新增恶化信号 ✅。
- escalation 检查：非关闭行截止列均为 2026-10-31（审查时点 2026-10-05 未到期），无 escalation 到期项 ✅。

### 7. 回填位纪律 —— ✅ PASS（防「先填后验」）

- CHANGELOG：日期占位注释（零预填）/ 窗口上界 `<M-1 回填位>` /「终值随 M-8 批回填——不预编造」✅。
- rollback-plan：区间上界=回填位 / 窗口计数=回填位 / unittest 基线「计数不预填，以 0.94.0 发布门记录为准」/ 边界声明「起草期零预编造」✅。
- 已填锚全部有实录出处：6da8d04/4789f96（L209+EVD-1311 权威）、9a28e4d/c68cbbd（DEC-316 实录）——零预编造违例 ✅。

## 三、发现列表

- **F-1（P2）** `project/CHANGELOG.md` 0.94.0 段头（L43）残留「未发布（准备态）」——与 L209 权威发布事实（tag v0.94.0→6da8d04，taggerdate 2026-10-04 annotated 4d4da76）直接矛盾；REL-098 M-8b taggerdate 回填疑似未落字（m-0 §7 已如实披露，非本版载荷）。0.95.0 发布回填日期后 CHANGELOG 将连续两版版本头与事实矛盾（蓝军①）。处置：随本版 M-8 收口 MUST 修正（对齐 0.93.1 段 L75「已发布（tag …；taggerdate … 权威——FIX-349 口径回填）」形态）。非本版阻断项。
- **F-2（P2）** checklist §C check-governance 预期值「基线 **1 issue**（28n 预存）零新增（EVD-1316 口径）」与 M-1/M-2 实测记载「**16 issues** 零新增（28n 等预存族）」基线数字失准——「零新增」判据两面一致，但预期基线停留在组装时点，M-2 实跑 16 issues 时对照 checklist 预期 1 issue 的 PASS/FAIL 判定口径含糊。处置：M-2 收口时 MUST ①16 issues 逐项归因入 EVD（证全预存族）②checklist §C 预期口径刷新或注记基线随 M-1 后态重定依据。
- **F-3（P2）** M-2 机检事实（13 处一致@0.95.0/1052 OK/预算零变化/16 issues 零新增）截至审查时点**仓内无可溯机录**——evidence-log 仅有 TRIAGE-REL-099 行（L2018），无 M-1/M-2 EVD 行；docs/release/ 下无 M-1 报告文件（glob *0.95* 仅三件）。本审查以 Coordinator 调度上下文转述的 M-1 报告记载为据（授权链在），但发布 APPROVED 的机检事实链应仓内可溯——M-2 收口时 MUST 补 EVD 机录（含命令输出锚）。
- **F-4（P2）** plan-tracker 版本行（实读 L210）「包含任务」列未列举 FEAT-086✅/FIX-432✅——VERSIONING L128「发布内容 MUST 匹配路线图包含任务」形态缺口；0.94.0 先例（L209 全票✅列举）形态对齐要求。缓解：DEC-314(1)(3)/DEC-315①② 拆票承载决策链在案（「不破 0.95.0 M-0 载荷冻结」明示）+ m-0 §1.2 差异披露 + checklist M-8 行已列「L207 回填」。处置：M-8 收口 MUST 执行回填（与 L11 工作流版本行刷新同批）。
- **F-5（P3）** 行号锚漂移 +3：m-0/checklist/CHANGELOG 引「plan-tracker L207 版本行/L206/L478」，实读为 L210/L209/L481（L85~87 REL-099/FEAT-087/FEAT-088 三行 triaged 入表所致；L80~84 五票行号未漂移）。内容锚无碍，建议治理文档引用优先用内容锚（版本号/票 ID）或随 M-8 刷新。
- **F-6（P3）** CHANGELOG 0.95.0 段缺 B16 债务未偿的用户视角披露——archive.py 4241 行拆分债未偿+FIX-430 exclusions 仅止增不删债，m-0 §2.1 与 checklist 边界声明（L101）双面如实披露，但 CHANGELOG（用户主文档）无对应句；0.93.0 段「已知边界披露」小节（archive.py 5,959 行越阈列入）为既有惯例形态。建议 M-8 收口补一句（蓝军③）。
- **F-7（P3）** 回滚方案未覆盖 `.git/hooks` 安装实例交互面：infra/hooks/ 源×4 随版本面提交 revert 回 0.94.0（声明面 13 处一致性验证会 PASS），但工作副本 `.git/hooks/` 安装实例非 git 管理（AUDIT-082 口径同根）——实例 0.95.0 vs 源 0.94.0 版本错位静默，直到 Check 28q hooks_drift 暴露或 hook 行为异常（0.95.0 实例 hook 调用回退后代码的兼容面无验证）。缓解在位（28q 有检测先例——0.93.1「hooks_drift（prepare-commit-msg 重装）」）。建议：回滚验证方式补第 6 项「重装 hooks（cp infra/hooks/* .git/hooks/）+ 28q 复跑」（蓝军②）。
- **F-8（P3）** 回滚无本版专属演练记录——零新增数据面声明+确定性再生四版先例（0.92/0.93/0.93.1/0.94.0 同构回滚方案）+0.92.0 隔离副本演练先例（EVD-1233）+验证命令在位；如实披露不阻断（0.94.0 M3b F-3 同构裁定；checklist §D 已按 stage-release SKILL 口径将演练评估归 Coordinator M-2 面）。
- **F-9（P3·信息性）** 报告文件命名形态差异：checklist §E 与 0.94.0 先例为 `review-REL-099-M3b-REL-R0.md` 形态，本报告按任务指定路径 `review-REL-099-REL-R0.md` 落盘（头部已标 M3b 消歧）。Coordinator 如需对齐先例可重命名（其权限面）或在 review-record 机录时注记映射。
- **F-10（P3·信息性）** 风险计数口径差：调度口径「17 open」，实读热 risk-log 非关闭 21 行（打开 15+缓解中 2+降级 2+已缓解 1+已收窄 1）。无发布阻断级（§维度 6 逐族评估）；口径差如实披露供 bootstrap 面板口径核对。

## 四、蓝军挑战（4 条）

1. **0.94.0 段头「未发布」残留的语义污染面（=F-1 深化）**：0.95.0 发布并回填 taggerdate 后，用户读 CHANGELOG 顶部将见 0.95.0（已发布日期）其下紧接 0.94.0（未发布·准备态）——时间倒置的事实矛盾，且与 marketplace/plugin.json 版本 0.95.0 并存削弱 CHANGELOG 作为用户事实源的可信度。处置建议：M-8 收口批 MUST 回填修正（0.93.1 段形态对齐）；若 M-7 前任何门禁面（Check 28c 族消费 CHANGELOG 状态列的场景）出现解析异常，提前修复不等 M-8。
2. **回滚声明面与 .git/hooks 自升级面的交互（=F-7 深化）**：check-version-consistency 只覆盖 git 管理的 13 处声明面；hooks 安装实例经升级通道 bump 到 0.95.0 后不随 git revert 回退——回滚验证 5 项全 PASS 也可能掩盖实例错位。后续果=28q hooks_drift 延迟暴露或 post-commit 实例与回退后 verify_workflow.py 的参数兼容面未验证。处置建议：序②验证后追加 hooks 重装一步（成本一行 cp 命令）。
3. **B16「止增在位但债务未偿」披露充分性（=F-6 深化）**：m-0 两栏核算诚实（「本版不主张 archive.py 体积债务已清偿」明示），但用户主文档 CHANGELOG 无此信息——「Phase 0 基线与止增纪律」Added 条目可能被误读为债务问题已解决。0.93.0 段先例证明 CHANGELOG 级债务披露是既有惯例。非阻断（checklist/m-0 双面已披露）。
4. **「1052 待发布门复跑确认」的时态落定**：CHANGELOG L33 与 m-0 §7 均以「待 M-2 复跑闭合」句式记载 1052 预期——M-2 已实测 1052 OK（调度记载），M-8 收口时 MUST 将该句落定为已确认表述并补 EVD 锚，避免「待确认」残留让用户误以为零回归未验证。

## 五、未验证项声明（事实红线）

1. **M-2 机检命令未独立复跑**（角色契约 Bash 禁止）：13 处一致@0.95.0 / unittest 1052 OK / 预算零变化 / check-governance 16 issues 零新增——全部以 Coordinator 调度上下文转述的 M-1 报告记载为据，**待 M-2 EVD 机录落账后方可视为仓内可溯事实**（F-3）。
2. **git 对象未机验**：tag v0.94.0→6da8d04 / candidate 4789f96 / FIX-432 两 commit 9a28e4d/c68cbbd——以治理面权威记载（L209/DEC-316/EVD-1311）为据，未跑 git 验证。
3. **前瞻样本附录 A URL 真实性**：承接 REVIEW-FEAT-086-R0 BM-3 口径——仓外不可复查，不作本 APPROVED 依据（依据为仓内可复查事实+机器记录）。
4. **版本面 13 处 bump 实际执行态**：属 M-3a Code Reviewer 定向审查面，本审查不重复（checklist §B 清单形态与调度口径总数 13 一致已核）。

## 六、结论

**APPROVED_WITH_NOTES（unresolved_blockers = 0）**——0.95.0 发布包四件套+治理面就绪：范围冻结无漂移、门禁预期诚实标注、回滚方案四要素齐备且基线锚权威一致、CHANGELOG 四段覆盖且 Breaking 评估充分、MINOR 定级与 bump MUST 触发依据实读成立、无发布阻断级风险、回填位纪律规范。4 项 P2（0.94.0 段头残留/checklist 基线口径/M-2 机录可溯性/L210 包含任务列回填）均有明确收口路径且全部落在 M-2/M-8 既定步骤内，不构成未解决阻塞。**放行条件：F-2/F-3（M-2 EVD 机录+16 issues 归因）与 F-4/F-1（M-8 回填批）随发布链既定步骤 MUST 闭合。** 最终提交、推送与 tag 由 Coordinator 执行。
