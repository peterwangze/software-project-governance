# FIX-396 设计审查报告 — R0（DESIGN）

> **Round**: R0（首轮） · **审查者**: Design Reviewer Agent · **日期**: 2026-09-26
> **审查对象**: 暂存树 4 files vs HEAD `f64a7b3`（`git diff --cached`，+22/−2）
> **票面**: plan-tracker FIX-396 行（:83）+ change-triage/FIX-396.json + decision-log DEC-251（:193）
> **结论**: **APPROVED_WITH_NOTES** — `unresolved_blockers=0`（无 BLOCKING finding；4×P3 + 3×NOTE 留痕跟踪）

---

## 0. 审查范围与硬门槛自检

| 硬门槛 | 执行情况 |
|--------|---------|
| 暂存 diff 逐行审查（全量不抽样） | ✅ 4 文件全量 diff 逐行覆盖：SKILL.md ×2（同内容 +2 指针段 +行号 187→189）、behavior-protocol.md（+10 M5.1c 权威条款）、interaction-boundary.md（+6 用户回合侧镜像） |
| 亲跑五项检查命令复核（勿只信申报） | ✅ 五项全部亲跑，全 PASS（见 §4）；另亲跑 check-governance 对照 census 基线 |
| P0-P3 分级每条发现标注级别 | ✅ 见 §5（无 P0-P2；4×P3 + 3×NOTE） |
| 只读约束（除报告外零写入） | ✅ 暂存树原样保持，未 commit/未暂存/未重置；唯一写入 = 本报告文件 |
| 报告落位 | `docs/reviews/review-FIX-396-DESIGN-R0.md`（本文件） |

**e2e-check 取舍说明**：未跑 `e2e-check` 子命令——其对夹具项目治理数据有写入风险，与只读硬门槛冲突；夹具「CLI 再生」申报改以字节级一致性证明替代（§4.6），证据充分。

---

## 1. 条款语义完整性（审查范围①）——三要素逐条对照 DEC-251

| DEC-251 决策点 | M5.1c 落字（behavior-protocol.md :330-338） | 判定 |
|---|---|---|
| ① 唯一提问渠道纪律不豁免（禁内联索图） | 「当问题需要用户以上述形态作答时，**M5.1 不豁免**——禁止改为内联文字索图（“请把截图发我”仍是违规问句），问题本身 MUST 仍经 AskUserQuestion 呈现」（:332） | ✅ 对齐 |
| ② 固定回退选项+禁 recommended/首位默认 | 第 1 条：固定回退项+推荐措辞+描述注明+「MUST NOT 设为 recommended/首位默认——避免诱导用户绕过选项化决策」（:334） | ✅ 对齐 |
| ③ 对话框应答回合合法化+DSH 消费路径 | 第 2 条：合法应答回合定义+「M5.1 约束的是 agent 输出问句的渠道，不约束用户主动发送的材料」+原生查看/route_agent vision 双路径（:335） | ✅ 对齐 |
| ④ 通道边界（关键决策仍选项化） | 第 3 条：仅限无法承载形态+「能写成 2-4 个选项的问题不适用本通道」+关键决策五类引用 M5.3（:336） | ✅ 对齐 |

**逐项评估**：

- **回退选项禁 recommended/首位默认——理由成立**：AskUserQuestion 的 recommended 选项获 UI 高亮/默认选中；回退选项若为默认，用户一键即跳过结构化选项集，使回退通道事实化为主通道、侵蚀选项化决策根基。理由与 M5.3 选项化红线（:360-371）自洽：回退选项是输入引导而非决策选项，禁默认降低误触路径。✅
- **「仅限选项无法承载」判定边界可执行**：条款给出双向判据——正向形态枚举（图片/附件/长自由文本：均为工具结构化选项返回值无法承载的载体形态）+ 反向判据（「能写成 2-4 个选项的问题不适用」）。枚举非封闭穷举而是「无法承载」原则下的典型例示，与 M5.3 判断标准（「改变方向/范围/架构或接受风险→关键决策」）同为 LLM 语义层判定风格，粒度一致。✅（边界粒度备注见 NOTE-1）
- **关键决策选项化红线与 M5.1 既有三清单兼容**：M5.1c :336 引用「范围/架构/发布/风险/模式，M5.3」——核对 behavior-protocol.md M5.3（:360-371）：范围变更/架构决策/发布决策/风险接受/Profile·触发模式变更五类逐一对上（M5.3 另含外部依赖变更、阶段跳跃两项，为 M5.1c 引用之超集，引用不冲突）；interaction-boundary.md 既有「关键决策分类」表（:175-185）同类目 ✅；SKILL.md B3 关键决策清单（:154-）同类目 ✅。三处清单既有对齐关系未被 M5.1c 破坏。✅
- **与 M5.1b 确定性触发器兼容**：T1/T2 仅约束 Coordinator 回复散文（豁免区含 AskUserQuestion 工具调用块）；用户对话框应答回合非 agent 回复，不落入触发器判定域。无冲突。✅
- **与 M5.2 触发映射兼容**：M5.1c 不改变触发时机（何时问），仅细化应答承载形态（如何答）——正交细化，非触发器叠加。✅

---

## 2. 落字位置与分层（审查范围②）——FEAT-041 契约 v2 对照

**契约 v2 判据**（CLAUDE.md/AGENTS.md：「触发器行内 + 明细按需——『§Bx』= SKILL.md『Bootstrap 规程明细』」）：通道属**提问方式细化**还是新触发器？

- **判定：提问方式细化，成立**。触发器回答「何时必须交互」——M5.2 触发映射与 M5.3 关键决策分类本次零改动；M5.1c 回答「交互如何承载应答」——属方式层。四层落字与判定自洽：
  1. **behavior-protocol.md M5.1c（权威）**：位于 M5.1b（:304）与 M5.2（:340）之间，M5 系递进位置正确（:330）；
  2. **interaction-boundary.md 用户回合侧节（镜像）**：位于类型 B/C 交互机制定义之后（:90-94），与该文件职责（交互边界）匹配；
  3. **SKILL.md B3 指针**：插入 B3「提问规则」主段（:150）之后（:152），一行内容+摘要式指针，行内含触发语义（附件场景识别）、明细指向 M5.1c——符合契约 v2「触发器行内+明细按需」；
  4. **governance-init.md 压缩行不变——评估正确**：核对模板压缩行（governance-init.md :309-310）为「触发器+三清单+§B3 指针」形态，不含通道细节承载点；附件通道无新增触发条件，压缩行仍准确指向已更新的 §B3 明细。零 bootstrap bump 成立（CLAUDE.md/AGENTS.md @bootstrap-version 0.89.0 未动，verify 投影同步检查 PASS 佐证）。

**triage files 声明 vs 实际落字面差异**：triage JSON `files` 含 `commands/governance-init.md`（预估面），实际未动——已被 DEC-251 ④明文裁定覆盖（「governance-init.md 压缩行不变」），属设计决策修正而非越界或漏改。✅

---

## 3. 一致性与镜像互引（审查范围③④）

### 3.1 跨条款一致性
- **M5.1**：M5.1c 未弱化唯一提问渠道纪律——问题仍 MUST 经工具呈现，仅应答回合合法化，语义切割线（「约束 agent 输出问句的渠道，不约束用户主动发送的材料」）清晰无歧义。✅
- **M5.2/interaction-boundary 既有同步条款**：interaction-boundary :187「任何一方的变更 MUST 同步到另一方」惯例被新镜像节继承（:94「两侧互为镜像，变更 MUST 同步」）✅。
- **DSH 映射表**：映射表 :473「ask_user_question 工具替代 AskUserQuestion」与 M5.1c DSH 消费路径（route_agent vision/附件通道）兼容；新增段中工具语义无矛盾。✅

### 3.2 行号随动校正保真性（187→189）
- HEAD :187 =「如果 agent 不遵守协议（跳过 Gate、忽略 **AskUserQuestion**……」；暂存 :189 同内容——本次 +2 插入（:152 区域）使该行位移 2 行，校正值精确。✅
- 映射表其余行号引用（53 / 195 / 204-208）在 **HEAD 基线即已失准**（实测 HEAD：AskUserQuestion 提及在 :54；isolation: worktree 实际 :379；subagent_type 实际 :389）——非本次引入，且本次插入对完全失准引用无实际语义影响。详见 P3-1。

### 3.3 镜像互引形态（环引用修复形态）
- 双向互引均为**裸文件名 prose**（M5.1c :338「见 interaction-boundary.md『对话框应答回合（FIX-396）』」；interaction-boundary :94「见 behavior-protocol.md M5.1c」）——与既有惯例同款（SKILL.md :56「详见 behavior-protocol.md M7」、:231「interaction-boundary.md 任务排序行」、interaction-boundary :187「与 SKILL.md M5.2 触发映射互补」）。✅
- Developer 申报「中途 2 环自检发现即修复（markdown 链接→裸文件名 prose）」与 check-cross-references 实测「No circular references」吻合（:728 refs 零 dangling/零 deprecated/零 circular）。✅
- 职责分工非循环定义：behavior-protocol 持权威定义，interaction-boundary 持用户回合侧边界——互引为分工引用，环检测 PASS 佐证。✅

### 3.4 e2e 夹具（审查范围⑥部分）
主 SKILL.md 与夹具 `project/e2e-test-project/.../SKILL.md` git hash-object **字节级一致**（`0aece5c7…` = 暂存 blob，且 diff hunk 位置/index 完全相同）——「CLI 再生（release-projection --write，written=1）」申报可信；check-manifest-consistency PASS（920 canonical 无增删）佐证再生为 manifest 认可的同步机制。✅

---

## 4. 验证核验（审查范围⑤）——亲跑记录

| # | 命令 | Developer 申报 | 亲跑实测 | 判定 |
|---|------|---------------|---------|------|
| 1 | `check-injection-contract` | PASSED（3 files/23 anchors） | **PASSED**（Files checked: 3; anchors: 23; EXIT=0） | ✅ 一致 |
| 2 | `check-injection-budget` | 三档 PASS（resident 4216/6000；entry-skill 49030B/14588tok〔+129tok 余量 1412〕；command-doc 3466/6000） | **PASSED**（resident 4216≤6000 gated；entry-skill 14588≤16000 report-only；command-doc 3466≤6000；EXIT=0）——逐数字一致 | ✅ 一致 |
| 3 | `check-cross-references` | PASSED（727→728 refs，2 环修复） | **PASSED**（77 files / 728 refs；dangling/deprecated/circular 全零；EXIT=0） | ✅ 一致 |
| 4 | `check-manifest-consistency` | PASSED（920/1064 无增删） | **PASSED**（Canonical 920 / Actual 1064；EXIT=0） | ✅ 一致 |
| 5 | `verify`（全量） | PASSED | **PASSED**（== Verification Result: PASSED ==；EXIT=0；architecture fact source / agent adapter contracts synchronized） | ✅ 一致 |
| 6 | `check-governance` census | 39→39 基线零扩大（申报注明「任务书 33 为陈旧口径如实披露」） | Summary **35 issue(s)** ≤ 39 基线——**不扩大成立**（实测低于申报口径；运行时点治理数据差异所致，见 NOTE-2） | ✅ 方向一致 |

census 35 项构成核验：Check 31 BLOCKED（IDENTITY_ATTESTATION_FAIL）与 Check 34 FAIL 的失败文件均为 `docs/reviews/review-FIX-395-CODE-R1.md`、`.governance/risk-log.md`、FIX-390/391/396 证据行——**均非本次暂存 4 文件**，无本次引入的扩大项。✅

---

## 5. 发现清单（P0-P3 分级）

> 无 P0（致命）/P1（阻塞）/P2（应修复）发现。

| # | 级别 | 发现 | 依据 | 建议 |
|---|------|------|------|------|
| P3-1 | P3 | SKILL.md DSH 映射表既有行号引用失准（「第 53 行」实际 :54；「第 195 行」实际 :381；「第 204-208 行」实际 :389-395 区域）——**HEAD 基线即失准，非本次引入**；本次仅校正 187→189（本次位移唯一受影响且原本准确的引用），处置符合修改纯粹性（D4） | HEAD/暂存双版本逐行实测（§3.2） | 后续独立任务集中修复映射表行号引用（建议随下次触碰该表的变更顺带，或立 FIX 票） |
| P3-2 | P3 | M5.1c 引用锚「interaction-boundary.md『对话框应答回合（FIX-396）』」与实际节标题「对话框应答回合（附件输入通道——用户回合侧，FIX-396）」非精确匹配（前缀子串可定位，prose 惯例允许） | behavior-protocol :338 vs interaction-boundary :90 | 镜像条款下次同步时统一锚名（简名或全名二选一） |
| P3-3 | P3 | EVD-1187 在 R0 审查终态前预标「✅ 完成」——时序超前；check-governance Check 34 据此报「缺推荐快照」（FIX-390/391 同类为既有） | evidence-log :2801；Check 34 FAIL 行 | 审查链通过后由 Coordinator 按 M7.4 step 6 跑 task-priority-analysis 补 RECO 行（若复审翻案需先回滚完成标记） |
| NOTE-1 | NOTE | 「长自由文本」之「长」无量化阈值；与 interaction-boundary 类型 B 既有「开放输入」（:69/70/74）的边界依赖语义判定（两条路径均经工具呈现、殊途同归，不构成违规歧义） | M5.1c :336；interaction-boundary 类型 B 表 | 后续演进可在 M5.1c 补一句与开放输入的关系说明（非必需） |
| NOTE-2 | NOTE | check-governance 计数口径：申报 39→39，R0 实测 35（≤39 不扩大成立；差异源于运行时点治理数据变化——如 EVD-1187 入账前后 Check 34/32 计数不同） | §4 表 #6 | 无需动作；后续申报建议附 census 快照时间点 |
| NOTE-3 | NOTE | Check 31 BLOCKED（review-FIX-395-CODE-R1.md + risk-log.md ragged table row）与 Check 34 之 FIX-390/391 两个 violations 为既有/前任务问题，非本次暂存引入；不在本审查修复范围 | §4 census 构成核验 | 留给 Coordinator 在相应任务/维护批次处置 |

---

## 6. 总结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`

- **三要素语义完整** ✅：固定回退选项（禁默认理由成立）+ 对话框应答回合合法化（M5.1 语义切割线清晰）+ 通道边界（双向判据可执行、M5.3 三清单兼容无冲突）——四点逐条对齐 DEC-251，无语义漏洞。
- **分层正确** ✅：通道属提问方式细化非新触发器，FEAT-041 契约 v2（触发器行内+明细按需）对照成立；governance-init 压缩行不变评估正确，零 bootstrap bump 自洽。
- **一致性兼容** ✅：M5.1/M5.1b/M5.2/M5.3/DSH 映射表逐项核对无矛盾；187→189 校正保真；镜像互引裸文件名 prose 符合既有惯例且环引用已消除。
- **验证亲证** ✅：五项命令亲跑全 PASS，与 Developer 申报逐数字一致；census 35 ≤ 39 基线不扩大；夹具字节级一致证明 CLI 再生申报。
- **越界检查** ✅：修改面 = 三锁文件 + 1 命令工件（e2e 夹具再生），governance-init.md 未动系 DEC-251 明文裁定。

无 BLOCKING finding。上述 4×P3 + 3×NOTE 均不阻塞本次变更进入 commit 流程；P3-3 的推荐快照补齐属任务收尾动作，请 Coordinator 在审查链闭环后按 M7.4 step 6 执行。

---
*审查方法：暂存 diff 逐行（`git diff --cached` 全量）+ HEAD/暂存双版本对照 + 既有条款逐条核对 + 五项验证命令亲跑 + census 构成归因。证据均引自仓库文件行号/命令输出，无假设性判定。*
