# Review — REL-073-RELEASE-R0：0.78.1 版本规划文档发布审查（R0）

- **结论：APPROVED_WITH_NOTES**
- **unresolved_blockers = 0**
- **Round**: R0（规划段首审——审查对象为版本规划文档，非发布候选；候选态门禁与双审按规划 §3 属 M-2/M-3 工作单元）
- **审查人**: Release Reviewer Agent（只读审查；执行依据 `agents/release-reviewer.md` + `skills/release-review/SKILL.md`）
- **日期**: 2026-08-27
- **审查对象**: `docs/release/version-plan-0.78.1.md`（251 行，Release Agent REL-073 规划段产出）
- **依据材料**: `docs/release/queue-triage-0.78x.md`；`.governance/decision-log.md`（L7 DEC-169 / L9 DEC-167 / L12 DEC-163 / L18 DEC-143 / L179 DEC-170 / L180 DEC-171 / L181 DEC-172）；`.governance/risk-log.md`（L9 RISK-043 / L11 RISK-041 / L42 RISK-036 / L43 RISK-039 / L44 RISK-044）；`.governance/plan-tracker.md`（L11 工作流版本 / L164 REL-063 行 / L257 FIX-280 行 / L258 REL-071 行 / L259 REL-072 行 / L262 FIX-281 行 / L445/L455-461 路线图 / L462-473 V-Gate / L475-489 版本规划纪律）；`.governance/evidence-log.md`（L1591 EVD-909 / L1595 TRIAGE-FIX-281 / L1597 TRIAGE-REL-073）；`.governance/change-triage/REL-073.json`；`skills/software-project-governance/core/VERSIONING.md`
- **审查边界**: 只读审查对象，零命令执行（纯文档核验）；本报告为唯一写入文件；审查结论 ≠ 发布授权（授权唯一属 M-4 用户，DEC-143 基线）

---

## 1. 结论与统计

| 项 | 值 |
|---|---|
| 结论 | **APPROVED_WITH_NOTES** |
| unresolved_blockers | **0**（无未解决 BLOCKING finding） |
| findings | **P0=0 / P1=0 / P2=0 / P3=6** |
| 判定理由 | 规划文档在授权边界、No-overclaim、V-Gate/纪律符合性、PATCH 语义守界、N=2 机制、待验证项处置、M-1 前置完整性七个重点维度全部通过，事实表引用逐项命中既有治理记录（零编造抽验通过）；全部 findings 为 P3 级精度/对称性/登记面注记，不构成阻塞，保留为非阻塞发布备注随 M-0/M-1 跟踪 |

---

## 2. 七项重点核查逐项裁决

| # | 核查项 | 裁决 | 文档锚点 | 事实依据（既有 ID） |
|---|---|---|---|---|
| 1 | **release_authorized=false 边界** | **PASS** | 规划 L7（Status 行）、L90（M-4）、L236（§8 尾段）、L91-92（M-5/M-6「授权后」） | 显式声明 `release_authorized = false`——transition/tag/push 待用户授权；M-4 标注「用户确认——发布唯一人工门」；§8「不创建、不证明 v0.78.1 tag 存在（candidate-only）」。与 DEC-143（L18，自动推荐+用户确认交互基线）、DEC-170（L179，0.78.0 M-4 授权先例）、DEC-172（L181）链路一致 |
| 2 | **No-overclaim 边界** | **PASS** | 规划 L227-236（§8 六不声明清单）、L213-221（§7 风险披露表） | §8 显式不声明：1.0.0 readiness / official·marketplace approval / universal·full runtime support / RISK-036·039 关闭 / FIX-281 全部已修复 / 历史 tag 状态变更。§7 逐行核对：RISK-036/039（risk-log L42/L43，打开、2026-09-30、1.0.0 硬阻塞）「0.78.1 不关闭」✓；RISK-044（risk-log L44）已接受维持、正式复评挂 0.79.0——规划正确识别 risk-log 行「0.78.x」字样为 DEC-167 时点表述（decision-log L9 ③「下次版本规划（0.78.x）」）并以更后置的 DEC-169 ②（L7「下轮复评 0.79.x」）为权威口径，张力披露而非掩盖 ✓；另保留「打包期实测 >60s 劣化按触发条款升级」安全阀 |
| 3 | **V-Gate 与版本规划纪律符合性** | **PASS**（附 P3-3 措辞注记） | 规划 L20（§0 版本号预留核对）、L58（90% 完成率）、L75-76（§2 纪律行）、L134-172（§5 裁决表）、L86-94（M-0/M-1/M-8） | ① 路线图 0.78.1 行已预留不占号：plan-tracker L459 实证（状态=规划中，包含任务列 = DEC-172 全部 10 项），规划内容与该行 DEC-172 给定范围**一致**，FIX-281 子集入槽 = 范围核增走纪律 5/6（先更新路线图+DEC 再发布，M-1 执行）✓；② 未完成项处置：§5.1 裁决表 22 行覆盖 queue-triage §2 全部 17 项（映射注记 L165 逐项可追溯，抽验 §2.1 #13→#4+#21、#14→#5+#6+#20、§2.2 #17→#1 成立）+ F-3（§3.3 额外行）+ FIX-281 评估行，无隐藏带入 ✓；③ 90% 完成率（V-Gate L468 / 纪律 7 L488）：规划 L58 实际采用更严口径「全部入槽任务完成+审查终态后方可 M-1，超 N=2 出槽」✓；④ 路线图实时更新（纪律 4/8）：M-1 更新 0.78.1 行（含范围核增）、M-8 转已发布 ✓；⑤ 0.66.2 行漂移回写路径：§9 观察 1 + M-0 ⑤ + M-8 顺带（Coordinator 治理记录回写，不占版本范围）✓——TRIAGE-REL-073.json `planned_next=0.66.2` advisory WARN 根因（plan-tracker L445「补偿发布规划中」）实证成立 |
| 4 | **PATCH 语义守界** | **PASS** | 规划 L62-78（§2 判据表 + 一句话论证）、L50-52（§1.2）、L175-207（§6） | 入槽确定项逐项锚定 VERSIONING.md：DEC-171/N-P2-1/N-P2-2/N-P3-1/FIX-279 P2-1·P2-2/四步措辞 → L38（仅修复 bug）；F-3 → **L34 明列**（verify_workflow.py 新增检查项 = PATCH，引文逐字核实）；FIX-272 P2×2 → L13（用户可见小改+测试卫生）；F-01 → L45-46（本身不驱动 bump 随批次）；L19-21/L123（细粒度+计划外变更走 PATCH）支撑 0.78.1 路径。**FIX-281 各落点**：②③④⑨ = L38 缺陷修复论证成立（恢复设计语义，与 plan-tracker L262 行描述逐项吻合）；⑤ = 守卫新增按 L13/L34 类比「PATCH 面增量如实陈述」+ 保守可移 0.79.0 退路 ✓；⑥ 文档面；⑦ = L38 论证成立 + 保守退路（与 G5 同工具判定域）✓；**①⑧ = 判定规则扩展**——以 G2 L-A/L-B/L-C 先例为锚（DEC-169 ③，decision-log L7 原文「G2 判定规则 = 行为/规则面显著变更」支撑 0.78.0 MINOR），并入 0.78.1 将与先例自相矛盾 → 建议出槽 0.79.0（与 DEC-172 已裁决该域的 W-7/BC-7 同批同语义域）——判定面/MINOR 边界论证**成立**，且方案 B 的先例张力在 §6.2 如实呈报不回避 |
| 5 | **N=2 会话上限机制延续** | **PASS** | 规划 L58（§1.3）、L86（M-0 ④）、L220（§7 FIX-281 范围核增风险行） | 「超 N=2 会话上限自动出槽登记后续版本（DEC-163 惯例，DEC-169 ④ 延续）」三处显式；DEC-163（L12 ③）确立、DEC-169（L7 ④）延续、queue-triage §5 注（L153）同口径——链条完整，且作为 FIX-281 范围核增的悬置兜底机制被正确使用 |
| 6 | **3 项待验证项是否阻断 M-0** | **PASS（均不阻断）** | 规划 L18/L29（HEAD 窗口）、L242（§9 观察 1）、L184/L245（FIX-281 ② 行号） | ① HEAD 窗口 commit 清单 → M-1 候选打包期 `git log v0.78.0..HEAD --oneline` 核定（规划段零命令执行是任务边界，非事实缺口，§9 观察 3 自证）✓；② 0.66.2 行状态 → M-0 ⑤/M-8 核实（git tag 存在性 + release-ledger + DEC 核对）后 Coordinator 回写 ✓；③ FIX-281 ② router 实证行号 0.78.0 复核 → 拆分任务执行时核（plan-tracker L262 行原文自带「0.78.0 行号需复核」标注）✓。三项处置路径挂点均正确：M-0 裁决的是落点/入槽/方向/延续/处置方式，均不以前述三项事实闭合为前提；待验证项按 release-review SKILL 事实红线「标为待验证而非写成通过」处理——合规 |
| 7 | **M-1 候选打包前置完整性** | **PASS**（附 P3-2 对称性注记） | 规划 L24（§0 入槽项任务注册状态行）、L57（§1.3 任务化结构）、L86（M-0 行）、L48（§1.1 行 10）、L206（§6.3 拆分执行结构） | §0 显式：「DEC-172 全部入槽项（**含 F-3/FIX-272 P2×2**）均未注册任务行（tpa unblocked=[]）——M-0 裁决后、M-1 启动前 MUST 完成 triage 机器入账 + 注册 + Developer/Reviewer 链」；M-0 行重申「须在 M-1 启动前完成；超期 → 自动出槽」；FIX-272 单独 triage 在 §1.1 行 10 + §5.1 行 10 + M-0 ② 三处显式（DEC-172 L181 后续动作栏原文「F-3/FIX-272 入槽前单独 triage 机器入账」核实）；FIX-281 拆分子任务「各自 triage 机器入账、depends_on 不挂 FIX-281/REL-002 避免 data gap 传染」——该处置与 TRIAGE-REL-073.json 快照实证（FIX-281 blocked_by=[REL-002] data gap、unblocked=[]）正交契合；§1.3 任务化结构（4~6 任务按域分组、编号由 change-triage 机器分配、TDD + SoD）完整。前置链无缺口 |

---

## 3. 硬门槛裁决（release-review SKILL 四维度 × 规划段适配）

规划段审查对象为版本规划文档（非候选包、非发布执行）——SKILL 四维度按「规划完整性」形态适配：

| 维度 | 规划段判定 | 依据 |
|---|---|---|
| 发布就绪 | **规划完备**：M-0~M-8 里程碑链完整（含交互边界标注：M-0/M-4 = 用户确认，其余自动）；规划段无可引用的已执行检查——规划如实将全部验证挂 M-1/M-2 执行，未虚构任何 PASS（事实红线合规） | 规划 §3；DEC-170（REL-071 M-0~M-8 先例全链闭环） |
| 质量门禁 | §4 门禁清单 14 项确定性命令（候选态 #1-#12 + 释放态 #13-#14），每项带 0.78.0 实绩基线对照；「A/B 对照零新增」「NOT_RUN 如实记录（quality-tools）」「UNKNOWN/BLOCKED 不得包装为 PASS」三条诚实性约束显式 | 规划 §4；ADR-010；REL-071 M-2/M-7 实绩（L258） |
| 回滚能力 | §3.1 回滚边界表（候选/transition 态 = git revert 可逆；已发布 tag = 仅 governed recovery、绝不静默重指）+ M-1 三件套义务（rollback-plan-0.78.1.md MUST 复刻边界表——0.77.0 R0 P2-1 先例义务）+ §4 回滚验证（本仓无独立测试环境先例口径：可逆性分析 + 门禁复跑 #1/#2/#10 + `git diff --check`） | 规划 §3.1/§4；0.76.0/0.77.0 rollback-plan 先例 |
| 用户影响 | 无 BREAKING（§2 显式论证 + 迁移指南不适用）；无 feature flag（M-1 按先例出「无 flag 声明」）；DSH preset 时滞迁移说明随发布文档、不宣称未 sync 安装的会话级效果 | 规划 §2/§3 M-1/§7 |

**硬门槛汇总：无未解决 BLOCKING 问题**——规划段四维度全部满足，P3 findings 均为非阻塞注记。

---

## 4. Findings 明细

### P0（0 条）

无。

### P1（0 条）

无。

### P2（0 条）

无。

### P3（6 条）

| # | Finding | 级别 | 文档锚点 | 事实依据 | 建议 |
|---|---|---|---|---|---|
| 1 | 0.66.2 实际发布状态的**佐证材料已存在于规划引用文件内**，「未能从已读治理记录独立确证」的表述过于保守——plan-tracker L164（REL-063 行：🎉 RELEASE PUBLISHED (EVD-834)，✅ 已发布 2026-07-25，annotated tag v0.66.2 原子推送）与 risk-log L9（RISK-043 关闭行：0.66.2 三串行 slice + full-phase gate PASS + remote tag v0.66.2 peel=T 彻底补偿）均为**肯定性发布证据** | P3 | 规划 L242（§9 观察 1） | plan-tracker L164；risk-log L9（RISK-043）；risk-log L11（RISK-041「全量 ledger 16 issues 含 0.66.2 债务」——规划已引用的张力项） | M-0 ⑤ 呈报时引用 L164/RISK-043 作为佐证，将「未能确证」升级为「有强佐证、待 git tag + release-ledger 最终核实」；核实路径本身保留不变（RISK-041 ledger 债务张力仍在，保守核实正确） |
| 2 | §1.1 行 9（F-3）未像行 10（FIX-272）显式标注「入槽前须单独 triage 机器入账」——DEC-172 后续动作栏原文将「F-3/FIX-272」**并列**要求单独 triage；§0/M-0 的总体 MUST 已覆盖 F-3，但行内标注不对称，任务化清单展开时有并入他项 triage 的遗漏风险 | P3 | 规划 L47（§1.1 行 9） vs L48（§1.1 行 10） | decision-log L181（DEC-172 后续动作：「F-3/FIX-272 入槽前单独 triage 机器入账」）；规划 L24（§0 总体 MUST 含 F-3） | M-0 任务化执行时逐项带出单独 triage 义务（F-3 触及 manifest/REQUIRED_SNIPPETS 变更面——§4 门禁 #3 已有对应登记要求，二者联动） |
| 3 | 路线图 0.78.1 行「零行为面」措辞（plan-tracker L459）与规划 §1.3「F-3/DEC-171 为检查器面增改，按 L13/L34 PATCH 面如实陈述」及 FIX-281 ⑤⑦（若入槽 = 防护守卫新增/输出行为修复）存在轻微口径张力 | P3 | plan-tracker L459 vs 规划 L56/L68-69/L187/L189 | plan-tracker L459（「PATCH，零行为面」）；VERSIONING.md L13（PATCH = 任何影响 agent 行为或用户可见的变更——行为类变更本身是 PATCH 面非零行为面） | M-1 范围核增回写路线图 0.78.1 行时同步改写措辞（如「PATCH，修复/清理/测试卫生 + 检查器守卫增量」）；纪律 5/6 动作已规划，此处仅提示措辞一致性，避免 CHANGELOG/路线图口径漂移 |
| 4 | REL-073 任务行尚未登记 plan-tracker 任务表（grep 全文仅 L259 后续引用 + L459 路线图行提及；TRIAGE-REL-073.json snapshot total=176 不含 REL-073 本任务）——REL-071（L258）/REL-072（L259）先例均有任务行 | P3 | plan-tracker 任务表（无 REL-073 行）；evidence-log L1597（TRIAGE-REL-073 机器行已入账） | evidence-log L1597；`.governance/change-triage/REL-073.json`（snapshot total=176/completed=175/blocked=[FIX-281]——REL-073 不在计数内，规划 §0「REL-073（本任务）规划中」表述与此自洽） | Coordinator 在 M-0 呈报或 REL-073 完成回写时补登任务行（治理记录通道，不占 0.78.1 版本范围）；属 Coordinator 登记事项，非审查对象缺陷 |
| 5 | §4 门禁 #6 pytest 行「0.78.0 实绩基线 = 零新增失败（存量基线如实记录）」为惯例措辞——0.78.0 实际实绩为全绿（verify/e2e/unit exit=0），「存量基线如实记录」暗示存在存量失败，与实绩不符 | P3 | 规划 L120（§4 #6 中列） | plan-tracker L258（REL-071 M-2：「17 项静态核心门禁全 PASS + verify/e2e/unit exit=0」）；DEC-170（L179 同口径） | M-2 执行时锚定 0.78.0 基线 = 全绿（exit=0）——据此「零新增失败」等价「全绿」，消除措辞歧义；§9 观察 5「打包期以实测为准」已提供兜底 |
| 6 | M-3 行「机器入账 REVIEW-REL-073-R0」与 REL-071 先例的轮次语义不一致：先例中 R0 = 规划段双审（DEC-169：REVIEW-REL-071-RELEASE-R0 + REVIEW-REL-071-DESIGN-R0 呈 M-0），M-3 候选态双审记 **R1**（L258：「M-3 双审 REVIEW-REL-071-R1 ×2」）；本轮规划段 R0 已被本审查（RELEASE-R0）占用 | P3 | 规划 L89（M-3 行） vs plan-tracker L258 | plan-tracker L258；decision-log L7（DEC-169：version-plan-0.78.0 经 RELEASE-R0/DESIGN-R0 双审后呈 M-0） | M-3 机器入账 ID 对齐先例记 REVIEW-REL-073-R1（或显式声明本轮次编号方案），保持 Check 30 复审链轮次连续性语义（R0 起始 + V8 next_round）自洽 |

---

## 5. 自主补充核查（事实表抽验——规划 §0「零编造」声明验证）

| 抽验项 | 规划声称 | 核验结果 |
|---|---|---|
| 已发布基线 | 0.78.0 / transition afb959d / tag v0.78.0（65eb6b4f，peel=afb959d）已推送 github-https | ✅ plan-tracker L458 + L258（M-5/M-6 实绩逐字吻合，含 65eb6b4f）+ DEC-170（L179） |
| 工作流版本 | 0.78.0 | ✅ plan-tracker L11；TRIAGE-REL-073.json `"current": "0.78.0"` |
| 版本序列与预留 | v0.78.0 → v0.78.1 不跳号；0.78.1 行已预留（规划中） | ✅ plan-tracker L459；TRIAGE-REL-073.json version_chain（0.78.1/0.79.0 均规划中） |
| 出槽队列裁决 | DEC-172（2026-08-26，A 两段式：10 行入槽 + 0.79.0 主题批 + 搁置 9+1 维持） | ✅ decision-log L181 逐项吻合（含 F-3 新登记 + FIX-272 可选单独 triage + 0.79.0 MUST 含 RISK-044 复评） |
| FIX-281 申报批次 | DEC-172 之后新增（2026-08-27 机器入账 TRIAGE-FIX-281），落点未裁决 | ✅ evidence-log L1595；plan-tracker L262（⏳ 待执行，「版本定位待裁决…入槽裁决 = 用户」） |
| 任务面快照 | 176 任务 175 完成；唯一活跃 = FIX-281（blocked_by=[REL-002]）；既有 cycle WARN | ✅ TRIAGE-REL-073.json snapshot 逐字段吻合（total=176 / completed=175 / blocked=[FIX-281←REL-002] / unblocked=[] / cycles=[AUDIT-146↔FEAT-010]） |
| 版本适配 WARN | planned_next=0.66.2 advisory WARN（既有登记漂移） | ✅ TRIAGE-REL-073.json version.issues 原文吻合；根因 = plan-tracker L445 0.66.2 行「补偿发布规划中」 |
| 既有健康基线 | governance health 127 issues（18c 执行包首个 FAIL） | ✅ plan-tracker L258（M-7/M-8 实绩「127 既有基线披露」「首个 FAIL=18c」） |
| §5 覆盖核对 | queue-triage 17 项全覆盖映射 | ✅ queue-triage §2.1 #1-#16 + §2.2 #17 与规划 §5.1 #1-#21 映射逐项核对成立（含 #13/#14 拆行），无遗漏无编造 |
| §6.1 九项分析 | FIX-281 ①-⑨ 逐项 | ✅ plan-tracker L262 行内 ①-⑨ 描述逐项吻合（含 ② 行号「0.78.0 行号需复核」自带标注、⑨ REL-002 第三现、⑧ router 10→13 实证） |
| §2 VERSIONING 引用 | L13/L34/L38/L45-46/L123/L19-21/L12/L37 | ✅ 逐条行号核实（L34 = verify_workflow.py 新增检查项 PATCH 明列；L38 = 仅修复 bug；L123 = 纪律 2 计划外变更用 PATCH） |
| M-0 交互注记 | FIX-280 先例同型样式（避免 Check 10 误报） | ✅ plan-tracker L257（FIX-280 行：§5 加 M-0 交互注记，Check 10 m5_option_list_no_auq 基线归零）——规划 §5/§6 注记为同型合规样式 |

**抽验结论：§0 事实表与全部行号引用零编造、零漂移。**

---

## 6. 对 M-0 五个决策点的发布侧意见（供 Coordinator 呈报参考——非决策）

| 决策点 | 发布侧意见 |
|---|---|
| ① FIX-281 落点（§6 三方案） | **支持方案 A（拆两段）**：发布视角核心依据 = ①⑧并入将直接削弱 PATCH 论证的先例一致性（DEC-169 ③ G2 判定规则先例），且与 DEC-172 已裁决 0.79.0 的 W-7/BC-7 同语义域拆批会造成同域判定面跨两个版本承载——版本边界语义受损；拆两段后 L38 逐项成立、⑤⑦留保守退路（M-0 可收窄为②③④⑨最窄缺陷面）。⑨ router 活体第三现（REL-002）的止血紧迫性是入槽 0.78.1 的正当动因。方案 B 的「部分受损」定性如实；方案 C 代价（⑨第四现风险 + 0.79.0 膨胀 14 项）已在 §6.2 呈报 |
| ② FIX-272 P2×2 入槽 | 中性偏可入：工作量小（<1 循环）、PATCH 面成立（L13）、安全无缺陷前提（14/14 探针）；入槽则范围核增走纪律 5/6（DEC + 路线图行更新，M-1 执行）；出槽则 0.79.x 守卫批次与 F-04 同批——两路均无发布风险 |
| ③ F-3 实现方向 | 发布视角无偏好；提示：两方向的 M-1 变更面不同——扩展 check-version-consistency = 既有检查项内变更（面小）；新增 check-bootstrap-markers = 新检查项（manifest 登记 + 门禁 #3/#9 变更面 + CHANGELOG 新检查项披露）。无论何者均属 L34 PATCH 面，不影响版本定位 |
| ④ N=2 会话上限延续 | **支持延续**（DEC-163/169 ④ 惯例；FIX-281 范围核增后窗口拉长 2~3 循环的预估使该兜底更必要） |
| ⑤ 待验证项处置（0.66.2 行） | 支持「M-8 顺带 + Coordinator 回写」建议；呈报时按 P3-1 引用 L164/RISK-043 佐证（强佐证 + 保守核实并存），回写属治理记录小修不占 0.78.1 范围——该定性正确 |

**流程注记（Coordinator 侧，非本审查对象缺陷）**：REL-071 先例的版本规划经**双审**（RELEASE-R0 + DESIGN-R0，DEC-169）后呈 M-0；本轮任务书仅派发 Release 侧 R0（本报告）。若不安排规划段 Design Reviewer R0，建议 M-0 呈报时显式说明该差异或按先例补派（P3-4/P3-6 的任务行登记与 M-3 轮次编号一并由 Coordinator 处置）。

---

## 7. 边界与合规声明

- 本审查只读执行：未修改审查对象及任何产品/治理文件；本报告（`docs/reviews/review-REL-073-RELEASE-R0.md`）为唯一写入文件；零命令执行（全部核验基于文档与既有机器记录交叉比对）。
- 事实红线合规：本报告全部 findings 附文档锚点 + 既有 ID 事实依据；未将任何未执行检查表述为通过；3 项待验证项维持「待验证」定性。
- **本结论 ≠ 发布授权**：0.78.1 处于纯规划段，`release_authorized=false`；transition/tag/push 授权唯一属 M-4 用户（DEC-143 基线）。
- 不关闭 RISK-036/039（2026-09-30，1.0.0 硬阻塞）；RISK-044 维持已接受、正式复评挂 0.79.0（DEC-169 ② 权威口径）。

---

*Release Reviewer Agent — REL-073-RELEASE-R0，2026-08-27。结论机器入账由 Coordinator 经 review-record 通道执行（手写 REVIEW 行 = 流程违规，DEC-146 ①）。*
