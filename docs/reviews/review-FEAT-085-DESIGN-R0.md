# REVIEW-FEAT-085-DESIGN-R0 — M10 主动生态探索协议规则面（后置设计审查）

**Round: R0（首轮）** | Reviewer: Design Reviewer（独立实读审查，零文件修改）| 日期：2026-10-04
审查对象：behavior-protocol.md L821-865（M10 全文四块）+ SKILL.md L364 触发行；行数基线核验：behavior-protocol.md 897 行（基线 851，+46，既有行零删改）、SKILL.md 493 行（基线 491，+2）——改动范围与声明一致。

## 总结论：APPROVED_WITH_NOTES
**unresolved_blockers = 0**（无 BLOCKING finding；M10 设计本身无阻塞缺陷）
findings 计数：P0=0 · P1=1 · P2=1 · P3=4。P1 为 Coordinator 侧闭环前置条件（流程面），不否定设计产物，但 FEAT-085 标记完成前 MUST 闭环（F-1）。

## 逐块审查（全部实读核验）

- **M10.1 条款表（L825-835）— 通过**：编号连续（M0~M10 实测）；引言出处锚（DEC-312②/REQ-146/提案 §2）符合锚习惯；REQ-146 实存（plan-tracker L476，P0）；互链实测正确（M7.2=L465、M7.7 R1=L742/L746）；L835 防冲突澄清与 M7.2 精神一致。A9/A10 符合：全仓 grep「EXP-0[1-5]」仅命中 behavior-protocol.md M10（唯一规范源）、SKILL.md L364（纯指针）、docs/research/（事实源出处）——methodology-routing.md 零匹配、无独立子系统。
- **M10.2 exploration schema（L837-847）— 通过**：A11 复用 evidence 载体达标；四字段与 DEC-312(2) 对应；DEC-312③/B18 隐私边界落地；phase0-baseline §5 前瞻五项要求中前四项已覆盖。
- **M10.3 四通道（L849-860）— 通过（附 P3-1）**：「行为语义非工具流水线」=A11 核心语义落地；adapters/ 目录 grep 零 exploration/EXP/通道声明（「本节不改动 adapters/」承诺属实）。P3-1：consult 映射含 draw（生成≠咨询）——物理化票修正。
- **M10.4 触发入口锚（L862-865）— 通过（附 P3-2）**：与 SKILL.md L364 实际形态一致（A9 零条款复制）；A12 落地实测通过。P3-2：引文与 L364 非逐字同步机制——纳入 sweep 票。
- **SKILL.md L364 触发行 — 通过**：位置/形态/预算三核验全过（entry-skill 面 report-only 16,000，实测 15,247 ok）。

## 语义保真表（EXP-01~05 vs 提案 §2 原文逐字对照）

| 条款 | 判定 | 差异性质 |
|---|---|---|
| EXP-01 | ✅ 一致 | 增益澄清「判断义务而非探索义务」+跳过附因强化 |
| EXP-02 | ✅ 一致 | 五触发逐一对应（细化经提案 L52 授权）；AskUserQuestion 具体化与 M5 对齐；「耗尽后继续执行链不是违规」双向界定 |
| EXP-03 | ✅ 一致 | 「通道」术语统一；「诚实降级合法，能力伪装违规」强化 |
| EXP-04 | ✅ 一致 | 核心语义完整；不可信数据+validate+M7.7 R1 互链=验收⑥承载的有据扩展 |
| EXP-05 | ✅ 一致 | 七项采用依据逐一保留 |

**走样计数=0**。全部差异方向=具体化/强化/治理联动，各有决策依据。

## 预算事实核验（复跑 check-injection-budget 实测）

- resident 4244/6000 tok PASSED（与基线 EVD-1313 同值——零变化 ✓）
- combined M1+M2 worst surface 342 ≤ 370（hard）✓ 硬门零变化、未抬升（A12 ✓）
- entry-skill 15,247 tok（skill tier report-only）；「+33 tok」按 tokenizer 公式估算 ≈33-36 自洽，report-only 不动 verdict
- 与 DEC-313(7) 完全一致 ✓

## Findings 清单

- **F-1（P1）后续票未入账+验收⑤⑥处置悬空**：修复条件（FEAT-085 标记完成前）：(a) 后续票入表（0.95.0 载体）；(b) decision-log 记录拆票裁定；(c) FEAT-085 完成机录显式标注验收⑤（⑥已由 EXP-04 落地）由后续票承载并回指。闭环治理缺口，非设计缺陷。
- **F-2（P2）判定值↔样本类映射缺位**：「需要|可跳过|受限」与「应探索/可跳过/不可联网」称谓不同名——后续票或 sweep 时在 M10.2 补一行映射。
- **F-3（P3）**：consult 映射含 draw——物理化票修正。
- **F-4（P3）**：M10.4 引文与 L364 非逐字同步机制——sweep 滞后描述清单。
- **F-5（P3）**：M10 标题未带（MANDATORY）后缀（M2~M8 带、M9 不带）——sweep 统一定夺。
- **F-6（P3）**：EXP-04 validate 对外部信息作为设计输入场景的验证形式未细化——随前瞻样本票补强。

## 对 Coordinator 三项裁定的审查意见

- 裁定 a（entry-skill +33 维持完整形态）：**合理 ✓**（report-only 不触硬门实测；砍 33 tok 必破坏 A9 形态，语义损失远超收益）。
- 裁定 b（机制落地闭环+拆票）：**方向合理，闭环条件未满足**（见 F-1）。
- 裁定 c（M0-M9 滞后 sweep 后续票）：**合理 ✓**（19 处滞后实测成立：behavior-protocol.md L1/SKILL.md L409·L441/governance-init.md L321/e2e 副本 8+ 处/verify_workflow.py L488·L969/VERSIONING.md L51；本票顺手改将级联内容锚+副本+模板，违反 D4；sweep 票同样 MUST 入账留痕）。

## 蓝军挑战（≥3 条已执行）

① 预算语义攻击（停摆/无限探测）→ EXP-02 双向界定+L835，残余低；② 能力伪装 → EXP-03 MUST NOT+结果四态可审计，残余低（真实性依赖前瞻样本票验证）；③ 提示注入经外部通道进入执行流 → EXP-04 不可信数据+validate+M7.7 R1，残余中（F-6 前瞻票补强）。
