# Review — REL-084 · 0.87.0 设计兑现度（M-3）Design 半面审查 · R0

> **结论**: **APPROVED_WITH_NOTES**
> **unresolved_blockers=0**
> **Round**: R0（无前轮引用——首轮）
> **审查对象**: 0.87.0 设计兑现度——「治理健康收口」主题完整性：①规划基线 `docs/planning/version-plan-0.87.0.md`（M-0 双审 APPROVED）②兑现证据链 EVD-1122~1131 + DEC-226/227/228 + REVIEW 机录（九票 + M-3 Release 半面 R0 GO）③架构关键实现四处抽查④checklist M-2 回填门禁表
> **审查半面**: M-3 设计面（Design Reviewer 单席，串行）——六复验重点逐项 + 5 维度 + 蓝军挑战 + AI 专项
> **审查者**: Design Reviewer Agent（只读——未修改任何设计文档/代码；本报告为唯一写入物）
> **日期**: 2026-09-21
> **路径消歧声明**: 原名 `docs/reviews/review-REL-084-DESIGN-R0.md` 已被 **M-0 期 version-plan-0.87.0 设计半面审查报告**占用（glob 实证在场）——为不覆盖历史审查留档，本报告落盘消歧名 `review-REL-084-M3-DESIGN-R0.md`。Coordinator 机录 review-record 时请引用本路径。

---

## 0. 方法与工具面边界（如实声明）

- 工具面：Read / Grep / Glob only（任务约束——Bash/Agent/AskUserQuestion 禁止）。**未复跑任何门禁命令**；门禁数值以 M-2 实测回填（checklist #1~#16）+ EVD-1131 机录为事实源，本轮做**设计声明↔实现代码↔机录三方一致性**核验 + 数学自洽验算 + grep 实证抽查。
- 调用时间盒 ≤14 次：本轮取证 12 次（skill+角色定义 2 / 规划+发布面+门禁表+回退面+DEC 链 5 / 代码 grep 4 / EVD+DEC-220 1），未尽面如实标注（§4 P3-F4）。

## 1. 证据清单（全部实读/实查）

| # | 证据 | 用途 |
|---|------|------|
| 1 | `docs/planning/version-plan-0.87.0.md` 全文（86 行——§1 主题/§2 六票/§3.1 三候选对照/§4 批次/B-9~B-11/§6 出槽） | 规划基线 |
| 2 | `docs/release/release-checklist-0.87.0.md` 全文（154 行——#1~#16 全位回填 + 披露①~⑨ + B-9/B-10/B-11 行为变更索引） | M-2 回填主对象 |
| 3 | `docs/release/feature-flags-0.87.0.md` 全文（74 行——B-9/B-10/B-11 回退通道 + 灰度开关正交性） | 回退设计维度 |
| 4 | `docs/reviews/review-REL-084-M3-RELEASE-R0.md` 全文（127 行——APPROVED_WITH_NOTES/0 GO） | 姊妹半面结论交叉验证 |
| 5 | `.governance/decision-log.md` DEC-226（L168）/ DEC-227（L169）/ DEC-228（L170）/ DEC-220（L161）实读 | DEC 链 + 公理锚 |
| 6 | `.governance/evidence-log.md` EVD-1122（L2460）/ EVD-1129（L2493）/ EVD-1131（L2555）实读 | 机录链在案性 |
| 7 | `checks/loop_runtime_claims.py` L225-243——FIX-369 provenance 注释 + `max_semantic_units: int = 361923`（L243） | B-9 实现面 |
| 8 | `verify_workflow.py` grep——`_plan_hot_tracker_task_statuses`（L12210，L12259/L12266/L12521 三处复用）+ `parse_impact_analysis_entries_with_exemptions`（L12513~12584）+ Check 16/17 消费（L12619/L12715）+ Check 18 wrapper（L12845）+ 主运行面留痕（L15513/L15547/L21463/L21501） | B-11 实现面 |
| 9 | `governance_store.py` grep——`locks_release`（L1807，幂等重放 L1818）+ `released_files`（L1889）+ CLI 分发三锚（L2026/L2041/L2137）+ locks 家族声明（L8-13） | B-10 实现面 |
| 10 | `release/projection.py` grep——FIX-366 two-pass plan 注释（L190-192）+ byte_copy 链式 resolve（L238）+ CRLF 保真（L211-213） | FIX-366 实现面 |

## 2. 六复验重点逐项判定

### 2.1 主题兑现：version-plan §1 验收指标 vs M-2 实测 — **PASS（逐项对照零缺口）**

| 规划验收面（version-plan §1/§2） | M-2 实测（checklist/EVD-1131） | 判定 |
|---|---|---|
| Check 31 门禁容量（FIX-369，B-9） | PASS：304,481 ≤ 361,923，余量 57,442 ≈ 15.9%；公式 ceil(301,602×1.2)=361,923 于 checklist #16/feature-flags §2/常量行 L243 **四源同值** | ✓ |
| Check 16/17 引擎缺陷（FIX-368 列偏移 + FIX-371 账本，B-11） | 列偏移修复（EVD-1122，实测 PASS 180 chars）+ 账本生效：真实面 31→5→3；Check 16/17 各 3 FAIL **全部=REQ-092 blocked**（零豁免红线活体）+ historical_exempted 26=8+18 对账闭合 | ✓ |
| Check 20 fail-open 恢复（FIX-372） | EVD-1126：evidence 列约定统一三处修复（Check 20 读路径 fail-blind→恢复 + format check LIVE 对齐 + entry_method 语义）——声明↔机录一致（未复跑，工具面） | ✓ |
| 锁治理缺口（FIX-370，B-10） | locks-release 交付 + 活体验证 op-7c866828；Check 26 活体（REL-082 过期锁悬挂）首次拥有可对账释放路径；R5 96/96 键 | ✓ |
| 热事实源回填（FIX-367） | Check 28c×3 内联验证全绿（op-98c0f7f6）；M-5/M-8 回填义务内建于规划 §4（R0-DESIGN-F8 复发预防） | ✓ |
| Check 28s evidence-log 膨胀 | 按规划由 M-8 归档消解（不占工程票）——期义务如实保留，非失实 | ✓（期义务） |
| FIX-364 午夜窗 / FIX-366（候选池 #1） | EVD-1124 / EVD-1125 交付；FIX-366 两遍 plan **正道首活体**（M-1 单次收敛零回滚 + check-only 幂等，EVD-1129）——0.86.0 披露③ 技术债清偿，§4「绕开手法可撤」验收兑现 | ✓ |

**主题完整性结论**：§1 声明的六面 FAIL 收口全部有对应交付与实测记录；无「规划承载但交付缺席」项；无「交付超出聚焦集却未披露」项（增量票 FIX-371/372 经 DEC-227/228 入账，见 2.2）。

### 2.2 DEC 链一致性 — **PASS**

- **DEC-226（预授权六票聚焦集）**：规划 §2 六票与 DEC-226 范围逐票对应（FIX-367/368/369/366/364/370）。交付面九票 = 六票 + **FIX-371**（FIX-368 修复后 entries 集合 4→60 显影的承载票——规划 §3.2 已预登记「由 FIX-371 承载，为 M-2 门禁前置」）+ **FIX-372**（FIX-373 审查连带）。增量票均在 M-0 双审后经 triage 机录 + DEC 入账（DEC-227/228 实读在案），**未超 DEC-226 授权语义**（T2 类升级边界未触碰——账本可增删可回滚属非-T2 裁定，原文在案）。✓
- **DEC-227（路线 b 判据设计 vs 实现）**：三条设计判据逐一实证——①**✅ 终态判据**：豁免以 hot-tracker 任务状态为机器可判定锚（`_plan_hot_tracker_task_statuses` L12210）；②**单扫描源**：L12521 同源取数 + L12259/L12266 复用同函数——无第二扫描路径漂移面；③**三面留痕**：Check 16（L12619→result["historical_exempted"]）/ Check 17（L12715）/ Check 18 wrapper（L12845 `_current_release_impact_entries`）+ 主运行面打印（L15513/L15547/L21463/L21501）。✓
- **DEC-228（三消费方修订）**：实现与明列三消费方**逐位一致**（grep 实证 L12619/L12715/L12845）；「主运行面披露义务（F-1 修复后生效）」在 checklist #2「三消费方首查 ✓」+ M-2 回填「historical_exempted 26 留痕」双载。✓
- **红线核验**：M-2 回填记录「无新增 FAIL 行入账本（B-11 红线维持）」+ REQ-092 🚧 blocked 未入账本——DEC-227「账本仅容纳 2026-09-20 前存量」红线在交付后仍活体成立。✓

### 2.3 B-9~B-11 行为变更设计 vs 交付 — **PASS（设计↔实现↔回退三闭环）**

| 变更 | 设计（feature-flags） | 实现实证 | 回退通道闭环 |
|---|---|---|---|
| **B-9** | §2：公式钉值 + 反豁免双测试 + baseline-register + 回退=还原预算值+基线注销（回滚后必然 BLOCKED 如实预期） | L225-243 provenance 注释（DEC-226/FIX-369/公式/measured_peak 三实测点）+ L243 常量 361,923；反豁免测试类 `FIX369SemanticBudgetRecalibrationTests`（M-3 Release 半面实证 L1879 在树） | ✓ 版本级唯一路径 + §6 正交性（legacy 不承载预算回退——fail-closed 安全语义面）论证成立 |
| **B-10** | §3：task 锚定真删除 + 先登记后删除 + released_files 审计章 + 三态/幂等 + 95→96 键；shrink-locks 保留语义不变 | `locks_release` L1807（同族三命令 L13 声明；operation_id 幂等重放 L1818；released_files 写入 L1889；CLI 注册/分发/handler 三锚 L2026/L2041/L2137）——「先登记后删除」与 grep 行序（台账调用 L1875 → stored 修改 L1889）静态一致 | ✓ 版本级回退 + acquire 幂等重取内建补偿 + 不可逆面=零论证成立 |
| **B-11** | §4：✅ 终态豁免 + 新增行零豁免 + 三消费方留痕 + 26=8+18 对账；条目级增删仅数据级 | §2.2 已实证（三消费方 + 单扫描源 + 留痕面） | ✓ 机制级=代码回退（+144 行撤除）；条目级=数据级操作非 flag 通道——边界声明清晰无混淆 |
| （连带）CRLF | §5：`read_bytes().decode` 替代 `read_text` 隐式转换 + 护栏双断言 | projection.py L211-213 注释与设计同源（byte-identical 动机 + L238 链式 byte_copy resolve） | ✓ 随 FIX-366 版本级回滚 + 护栏测试同步消失如实披露 |

**任务 brief 对应关系勘误（备案 P3-F1）**：brief 称「FIX-366 两遍 plan——B-10 回退语义设计的兑现」，实际对应关系为 FIX-366↔CRLF 连带行为变化 + M-1 正道化（非独立行为变更号），B-10↔FIX-370 locks-release。材料自身（version-plan §5/checklist 行为变更表/feature-flags）对应关系全部正确自洽，属 brief 引用偏差，非交付缺陷。

### 2.4 架构一致性（DEC-220 公理 + 分层纪律）— **PASS**

- **DEC-220 公理相容性（确定性核心/LLM 边界）**：四处实现全部落在「确定性软件化」侧——B-9 常量+provenance 注释+守护测试钉死（LLM 无法静默上调）；B-10 schema window + operation_id 幂等 + 台账机录（L1826-1832 require_operation_id/require_supported）；B-11 机器可判定终态锚 + wrapper 化取数；FIX-366 两遍 plan 为纯引擎内 resolve（无人工介入面）。无一处把确定性逻辑留给 LLM 判断。✓
- **分层纪律**：checks 层（loop_runtime_claims.py 承载 ScanLimits 与判定）/store 层（governance_store.py 承载锁家族，一族三命令 L8-13 职责内聚）/verify 编排层（verify_workflow.py 消费面 wrapper 化——Check 16/17/18 各自独立 result 字段，共享单扫描源）——方向无越界、无循环依赖新增迹象；FIX-371 单扫描源设计消除多处扫描漂移面，属架构正向收敛。✓
- **M-2 修复批架构面**：kill-switch 修复仅 docstring 字面量（引擎语义未触——混沌复演 35 passed 佐证）；archguard regen 遵守基线纪律（FEAT-055 先例同型；FACTS_PRINT_TOTAL 1306→1316 归属 FIX-377/0.88 bisect **注记式披露**而非静默吸收——机录时代完整性公理遵守）。✓

### 2.5 遗留设计债披露充分性（FIX-373~377 出槽）— **PASS（五票全部多源留痕）**

- FIX-373（切分器状态泄漏——Check 20 双向影响）/ FIX-374（9-cell 豁免消歧）/ FIX-375（FIX-370 遗留）/ FIX-376：checklist 披露④ + plan-tracker 出槽注记 + rollback §8 候选池三载一致（M-3 Release 半面 §2.3④ 已核）。
- FIX-377（FACTS 基线漂移 bisect 归属）：checklist #8 注记 + EVD-1131③——出槽有归属注记、非静默入库。
- 全部出槽票均落 0.88 承接面（version-plan §6 出槽清单同域），无「披露了但无处承接」悬空。✓

### 2.6 五维度 + 蓝军挑战 + AI 专项

| 维度 | 判定 | 依据摘要 |
|---|---|---|
| 设计合理性 | **PASS** | 单扫描源/一族三命令/provenance 常量+守护测试——职责单一、接口最小化（wrapper 复用同函数）；B-9 三候选对照（§3.1）评估标准五条预定义、排除理由援引 DEC-220 公理——选型纪律完整 |
| 技术债务评估 | **PASS** | FIX-366 清偿 0.86.0 披露债 + 绕开手法撤除（三方互证无残留）；FIX-373~377 出槽有披露有承接；无新增未登记债 |
| 安全与合规 | **PASS** | 零豁免红线活体（REQ-092 未豁免）+ fail-closed 反豁免双测试 + no-overclaim 5 token 齐备 + 隔离环境限定措辞合规 |
| 可演进性 | **PASS** | B-9 公式化重定标可复算（ceil×1.2）+ baseline 登记——增长再撞限走同公式非改代码语义；locks 家族可扩展；账本条目级可增删（机制在场时） |
| 模块结构/接口契约 | **PASS** | 2.4 分层纪律面——store/checks/verify 三层各安其位；CLI 96 键经 contract-matrix 冻结 + archguard R5 消费，契约面受双重守护 |

**蓝军挑战（4 条，各附缓解实证）**：
1. *「重定标基线 301,602 单点实测若被污染？」*——缓解：同日三实测点（300,701/300,913/301,602）互证 + provenance 注释登记工作树 commit（`6e25753`）+ 反豁免测试钉死再重定标必须走同公式 + RISK 登记（随批 1 triage 入账：M-2 复算门偏差>裕度即 FAIL）——单点污染不成立为静默通道。
2. *「豁免账本若被塞入活跃行？」*——缓解：✅ 终态判据机器可判定（任务状态锚非自然语言）+ 新增行零豁免全严检 + REQ-092 blocked 活体未被豁免 + 三消费方留痕可审计 + M-2 回填「无新增 FAIL 行入账本」实测记录——滥用面被三重钉死。
3. *「locks-release 误删活跃锁？」*——缓解：task 锚定非盲目清理 + 先登记后删除（operation_id 审计痕迹）+ acquire 幂等重取补偿 + 不可逆面=零（真删除仅及锁条目自身）——最坏后果可逆。
4. *「回滚后账本+预算双失效叠加？」*——rollback 披露⑨四项弱化面如实登记（LRC 必然 BLOCKED/豁免消失计数回升/锁不恢复/projection 回缺陷态）且与 feature-flags §1「无 flag 中间态」互证——叠加态已被设计预期并披露，非隐藏风险。

**AI 专项 — PASS**：①机录凭证链在案（EVD-1122/1129/1131 实读，governance-store op- 锚 + schema v1；EVD-1123~1128 由 checklist↔机录链↔M-3 Release 半面三源交叉印证在案性）；②无幻觉锚点——本半面实读的常量/行号/函数名与文档声明逐位一致（L243/L12210/L12619/L12715/L12845/L1807/L1889/L190）；③复审必达链履历清白（FIX-366/370/371 三票 NEEDS_CHANGE→R1 全部履行，0 unresolved blockers——CHANGELOG/checklist 双载）；④如实性——失败修复链四项/出槽五票/期义务面均不美化。

## 3. 硬门槛裁决（design-reviewer.md）

| 门槛项 | 判定 | 依据 |
|---|---|---|
| 候选方案数 ≥2 | **PASS** | Check 31 重定标三候选 A/B/C 对照（version-plan §3.1，评估标准预定义五条）；DEC-227 三路线 a/b/c 裁决 |
| ADR/DEC 关键字段完整 =100% | **PASS** | DEC-226/227/228 实读：日期+背景+决策+备选方案+排除理由+影响范围+机录 op- 锚全齐 |
| 蓝军挑战 ≥3（各有独立 ID+缓解） | **PASS** | §2.6 四条 |
| 模块无循环依赖 =0 | **PASS（静态抽查面）** | 分层方向 checks←store←verify 无反向引用迹象（grep 面）；深层依赖图全量分析超工具面，如实标注 |
| Bar Raiser 评审完成 | **PASS（同构替代）** | M-0 双半面独立审查（DESIGN-R0/R1 + RELEASE-R0 留档）+ M-3 姊妹半面独立报告交叉——单席制下最高可得独立性形态 |

## 4. Findings

**BLOCKING：无。**

- **P3-F1（brief 对应关系勘误——备案）**：任务 brief「FIX-366 两遍 plan（B-10 回退语义设计的兑现）」对应关系有误（实际 FIX-366↔CRLF 连带/M-1 正道；B-10↔FIX-370）。交付材料自身对应关系全部正确，属引用偏差。
- **P3-F2（B-10 登记顺序核验深度）**：「先登记后删除」经 grep 行序（L1875 台账调用→L1889 released_files 写入）静态一致确认，未逐行读全 `locks_release` 函数体（时间盒）；活体验证 op-7c866828 + REVIEW-FIX-370-R0 APPROVED_WITH_NOTES/0 多源背书，非阻断。
- **P3-F3（checklist #16「交付时点 301,849」单源数值）**：未在本轮实读面复现出处（疑在 EVD-1129/review-FEAT-059 链）——两个关键数 304,481/361,923 已四源同值不受影响；与 M-3 Release 半面 P3-F6 同型，归 M-8 收口复核面。
- **P3-F4（EVD 抽读覆盖声明）**：EVD-1122~1131 中本轮直接实读 1122/1129/1131 三条；1123~1128 在案性由 checklist↔机录链↔姊妹半面报告交叉印证（未逐条展开——调用时间盒内取舍）。零矛盾迹象，如实备案。
- **P3-F5（深层依赖图）**：循环依赖零判定基于 grep 静态抽查 + 分层方向核验，非全量依赖图分析（工具面边界）——同型边界在 M-3 Release 半面方法声明一致，归 archguard R 系检查常态化兜底。

## 5. 结论

**APPROVED_WITH_NOTES（unresolved_blockers=0）—— M-3 Design 半面 GO。**

0.87.0「治理健康收口」主题在 Design 半面的全部复验重点（主题兑现/DEC 链一致性/B-9~B-11 设计↔交付/架构一致性含 M-2 修复批/出槽披露充分性/5 维度+AI 专项）零 BLOCKING；P3×5 全部非阻断（1 备案勘误 + 4 工具面边界如实声明）。设计↔实现↔机录三方一致性抽查零失实：DEC-227 三判据（✅ 终态/单扫描源/三面留痕）与 DEC-228 三消费方在 `verify_workflow.py` 逐位实证；B-10 先登记后删除 + 幂等 + 审计章在 `governance_store.py` 实证；B-9 公式钉值 + provenance 在 `loop_runtime_claims.py` 四源同值。**Coordinator 面期义务不因本结论免除**：①本结论 + Release 半面结论经 review-record CLI **机录**（M7.5——禁手写 REVIEW 行），引用本路径；②M-4 go/no-go（DEC-226 预授权形态，门禁不予放弃）；③Coordinator 提交批（candidate manifest + #10/#14 复跑）；④M-8 收口（含 P3-F3/F5 复核与 P2-F1〔Release 半面〕演练裁决留痕）。

---
*REL-084 M-3 Design 半面 R0（2026-09-21，Design Reviewer Agent）。事实基线：version-plan/checklist/feature-flags/M-3 Release 半面报告/DEC-226~228/DEC-220/EVD-1122·1129·1131/四处实现 grep 实证（loop_runtime_claims.py L225-243 / verify_workflow.py _plan_hot_tracker_task_statuses 及三消费方 / governance_store.py locks_release / projection.py two-pass）全部实读实查。未验证面（门禁命令复跑/pytest 复跑/EVD-1123~1128 逐条展开/locks_release 全函数体逐行/深层依赖图全量）一律如实标注（§4 P3-F2/F4/F5），不写通过。原名 review-REL-084-DESIGN-R0.md 为 M-0 期留档不可覆盖——本报告消歧落盘。*
