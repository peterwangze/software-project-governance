# REVIEW-FEAT-103-DESIGN-R6 — R5 增量（F-M3-1~4 收敛 + 锚点裁定 + 状态行）聚焦复核

- 日期：2026-10-22（Asia/Shanghai；命令时刻 UTC）。独立 Design Reviewer（R8 同链新实例，承接 REVIEW-FEAT-103-R8；只写本报告 + scratch `.codex-sandbox/FEAT-103/review-design-r6/`）。
- **对象绑定**：设计 `docs/architecture/dsh-upstream-owned-registration-R1.md` 修订后 SHA-256 `2CA8A9B813E7B0DE2335C396F5709ADE17D67C4C1244AFE7896BEFE20B3FA4F3`（549 行 / 96,752 B——本 Reviewer 独立复算一致）；修订前基线 `30E6FF022EB309FF1895ADE1BA15B9C25D53154FAF9F75792E01339C2EBE7FB5`（515 行 / 83,810 B）= R8 复核输入，与 M3-REPORT §0 收工 SHA 及 Architect revision-log 一致。
- **delta 依据**：`.codex-sandbox/FEAT-103/M3-REPORT.md` §6（F-M3-1~4 原文，逐条比对）+ §2.1/§2.2 实现锚点（`acquireParentAdmission` :897-920、materializeTracked :1822-1833、B1-B12 观测）+ `.codex-sandbox/FEAT-103/design-r5/revision-log.md`（Architect 逐项落点）+ 前轮 `docs/reviews/review-FEAT-103-DESIGN-R5.md`（REVIEW-FEAT-103-R8）。
- **范围**：只核 R5 增量七面（F-M3-2 锚点裁定核心 + F-M3-1/3/4 收敛 + 顺带状态行 + R5 已批面零回退 + section 回归）。未运行宿主/测试；实现行为核对以 M3-REPORT 与 CODE R3 报告的已机录事实为据。

## 1. 结论

```text
conclusion=APPROVED_WITH_NOTES
unresolved_blockers=0
f_m3_items=PASS (4/4)
anchor_ruling=ACCEPTED (a: materializeTracked entry; alternative b documented with impact)
incidental_items=PASS (§5.4 status+N-R4-4 / §5.6 evolution chain / §11 handoff / §14 record)
r5_approved_face_regression=PASS (5/5 anchors in place, grep-verified)
section_regression=STRUCTURAL_PASS (+34 lines accounted; byte diff NOT_RUN — pre-revision snapshot unavailable)
host_run=NOT_RUN
tests=NOT_RUN (design-doc review; M3 test facts cited from machine-recorded reports, not re-run)
new_global_blocker=NONE
```

## 2. 逐项判定

| 项 | 判定 | 事实 |
|---|---|---|
| **F-M3-2 锚点裁定（核心）** | **PASS（裁定接受）** | §4.2 :229-236。裁定 a) 合同锚点 = materializeTracked 编排入口（spawn/cold 统一，入口内同步冻结）。四依据逐条核验：**依据 1（语义）** 成立——继承合同语义自 S-U2 起即"子消费父现行 standing generation"（`composeFrom` 同步取父当前代），materializeTracked 是 spawn/cold 汇合的子编排点；撤销 S-U3 比拟的区分（策略参数=请求性质须入口捕获 vs 资源状态=消费性质消费点冻结）逻辑成立且诚实标注"比拟撤销"。**依据 2（窗口无静默路径）** 有实测支撑——窗口内父换代→观察到新代（继承现行代语义的正确表达）、父关闭→closed 拒收（M3 B6/B4）；关键证伪 B3（acquire 与 setup 之间父切 G2→子仍冻结 G1）证明更晚的 setup 期冻结不满足合同，锚点区间（入口→create/resume 前）+factory-attempt 边界落点（:1822-1833，∈ 区间）与表述一致。**依据 3（双 fence）** — attach 前置判定（A11/B12）+ publicationCommit fence 层层拒收，"不静默取新代"（D2 不变量）双保险成文。**备选 b) 排除论证** 成立——收益仅把窗口内换代从"可观测新代"改为"可观测 closed"，两者均非静默、不改变安全合同；成本=两处签名穿参（:1438/:2221）；**留白恰当**："若后续独立复审裁定合同应取请求时点语义，b) 为既定实施路径"——裁定权归独立复审（含本轮：本 Reviewer 裁定 a) 论证充分，接受），未来可重开而不锁死。 |
| **F-M3-1 双名映射** | **PASS** | §4.4 :253 消费原语映射注记：`mountOwned`/`composeFromOwned` 为设计期原语名；实现未新增（M2 起 §5.4 acquire+attach 为 CODE R3 已批面）；`admission.attach(childCtx)` 对新子即两原语语义；M3 `applyChildCompositionOwned` 内部消费 attach，无重复 API；两分支消费差异（独立 join 新 binding/继承 rebind 父 binding）由 attach 内部按 token 来源 generation 表达。歧义消除充分，与 M3-REPORT §6 F-M3-1 原文逐点对应。 |
| **F-M3-3 cold/spawn 错误面** | **PASS** | §4.2 :238：spawn 面透传 `agent-preset/closed`（B4 实测）；cold resume 面包为 `NOT_RESUMABLE` + cause（`cause.code === "agent-preset/closed"` 可溯源）；沿用 S-U5 既有 NOT_RESUMABLE 纪律（"cold resume 对不可恢复状态统一 NOT_RESUMABLE 是既有 API 合同，本补丁不改变该分类面"）——一致性论证在案；共同保证（closed 根因不丢失、无静默回退）成文。 |
| **F-M3-4 记法对齐** | **PASS** | §4.2 :221：伪码 `acquireAdmission(ownerCtx,…,signal)` → 实现 `acquire({id} \| {id,generation} \| {parent})`（§5.4 R4 增量批准面）；无 ownerCtx 形参（registry 服务自身持有 owner root 语义，同 root 校验在 begin/attach 面执行）、无 signal 形参（abort 期间 acquire await 未完成时无 token 可泄漏，abort 处置归 materializeTracked 外层错误路径与 attempt 边界 try/finally——M3 实测合同）；"本文档其余伪码出现按此映射阅读"。三形态与 M2-FIX（{id,generation}）+M3（{parent}）实现一致。 |
| **§5.4 状态行 + N-R4-4 补列** | **PASS** | :304 状态 bullet 重写至 M3 后事实（M2 A1-A6→M2-FIX→M3 A10/A11/B12/A12）；R4 版漏列的"成功后 collect 失败隔离"缺口项本行补列并显式标注（N-R4-4 闭合）；残余 NOT_RUN（rebind 抛错分支、真实 publish 链、host）如实保留。 |
| **§5.6 状态行（R3-P3-2/P3-4 闭合）** | **PASS** | :320 第 7 条：清除时机演进链（校验前〔R2 P2-1 缺陷〕→record 插入后〔CODE R3 PASS〕→`record.start()` 成功后 + `activating` 门控〔M3 A12 + naive-move 变异体证伪无条件移位〕）；门控语义（pre-aborted signal / close-before-start 的失败 begin 保留墓碑）与同步窗口论证（`_activationSettled` 只在微任务运行，无交错）在案；host NOT_RUN 保持。与 §5.6 第 2 条主合同（"分配/入索引与启动之后"清除）口径一致。 |
| **§11 交接 + §14 记录** | **PASS** | :410 硬门槛候选表补 R5 锚点二候选；:416-434 代码块 `design_revision=R5`（含版本号消歧注：设计版本 R5 ≠ 审查报告文件名 R5〔=R8 审 R4-P2〕——消歧必要且正确）、`r5_findings_addressed` 六项逐条与本报告判定对应、`implementation_progress=M1/M2/M2-FIX/M3 done`、`independent_review=R5 增量待聚焦复核`（PENDING，不自批）；§14 :531-549 修订记录完整（依据/纪律/零回退自检/待复审声明）。 |
| **R5 已批面零回退** | **PASS** | grep 独立验证五锚点在位：N-R4-1 错误码映射段=L286；N-R4-2 `_forget` 措辞（"只清 owner 多值索引与 id 主表；closedIds 墓碑保留"）=L198（+L548 自检引用）；N-R4-3 §9 容量行=L390；N-R4-5 两类 fallback 用例段=L284（+L548）；N-R4-6 文首一致性：L1/L3/L5 R5 标识 ↔ §11 `design_revision=R5` 一致。 |

## 3. 新偏差（均 P3，非阻断）

**R6-P3-1 — §5.4 R4 增量正文（:300）仍为 `acquire({id})` 单形态描述**

- R4 世系合同原文按修订纪律未重写（正确），但单独阅读 §5.4 :300 时不知 `{id,generation}`（M2-FIX）与 `{parent}`（M3）两形态；三形态 currently 仅由 §4.2 :221 记法注记统一衔接，而 :221 声明的映射范围是"其余**伪码**"，:300 是合同句非伪码。轻微不完整。
- 建议：后续小修（合入前顺手）在 :300 句内补"（M2-FIX/M3 起扩展为 {id,generation}/{parent} 形态，见 §4.2 记法注记）"半句；或维持现状由读者经 §4.2 注记衔接（可接受，不阻断）。

**R6-P3-2 — 裁定依据 1 "materializeTracked 是子作为 consumer 首次可行动的时点"措辞**

- "首次可行动"修辞略强（spawn 请求入口处 parent+composition 信息已可得，"可行动"依赖解释为"子编排上下文就绪"）。裁定实质不依赖此句（关键论证在依据 2 窗口语义 + 依据 3 双 fence，均有实测）。纯措辞备注，无需修改即可接受。

## 4. Section 级回归（515 → 549，+34 行）

| 区段（修订后行号） | 判定 |
|---|---|
| 文首 :1-:8（R5 标识/范围声明） | 行内更新（+0 新行）；R5 范围声明与实际修订面一致 |
| §1-§3（:10-:201） | 行数不变；N-R4-2 锚 L198 原样（§3.3 S-C7 更正与 CH-1.6 未触碰） |
| §4.2（:217-:239） | **+10**：:221 记法注记（1）、:229-236 裁定段（8）、:238 错误面 bullet（1）；:227 继承行行内更新 |
| §4.4（:253） | **+1**：映射注记 |
| §5.3-§5.5（:268-:310） | N-R4-1/N-R4-5 锚原样（L286/L284）；§5.4 状态行 :304 行内重写 |
| §5.6（:312-:320） | 第 7 条 :320 行内重写（含小幅增量）；第 1-6 条未触碰 |
| §6-§10（:322-:404） | 未触碰（§9 容量行 L390 原样） |
| §11（:406-:434） | **+2~3**（r5_findings_addressed 行新增、硬门槛/交接行内改写） |
| §12-§13（:435-:529） | 未触碰（R4 记录 :529 补 R5 注半句——行内） |
| §14（:531-:549） | **+19**（新增节） |

- 各区段新增合计 ≈ +32~34，与总增量 +34 吻合；未发现未声明区段变更。
- **byte 级 diff = NOT_RUN**：修订前快照不可独立重建（该文件 untracked、无 git 历史对象；基线 SHA 由 R8 报告/revision-log/M3-REPORT §0 三方一致佐证 30E6FF02…）。不伪造逐字节比对。

## 5. 命令审计（本 Reviewer，全只读）

| # | label | UTC | exit | 要点 |
|---|---|---|---:|---|
| V1 | 设计 SHA/bytes 复算 | 2026-10-22T08:56:4xZ 前后 | 0 | `2CA8A9B8…FA4F3` / 96,752 B；行数 549（read 口径；pwsh Measure-Object -Line 406 为非空行口径，非矛盾） |
| V2 | F-M3-1~4 原文 grep（M3-REPORT §6） | 同上 | 0 | L164-167/L173 六命中；与 R5 修订逐条对应 |
| V3 | 裁定依据锚点 grep（acquireParentAdmission/:897-920/:1822-1833/B3/B6/B12/generationFor） | 同上 | 0 | L67/L75/L81/L126 等命中；测试事实与裁定段引用一致 |
| V4 | R5 已批面五锚点 + R5 修订落点 grep | 2026-10-22T08:5xZ | 0 | §2 表内行号（L286/L198/L390/L284/L221/L229/L238/L253） |

- 设计文档全文 Read（549 行，两次分区）+ revision-log Read + M3-REPORT 定位读取；未运行任何测试/宿主/SDK；无写入（除本报告与 scratch 说明）。

## 6. 边界合规

- **写面**：仅本报告 `docs/reviews/review-FEAT-103-DESIGN-R6.md`（+ 本 scratch 目录说明性日志）；未改设计/代码/测试/副本/治理记录。
- **未 stage/commit/push**；未启动宿主；未设置/读取 DSH_HOME；未读写真实 `~/.dsh`；安装态 SDK 零访问（纯文档审查）。
- 审查对象 SHA 独立复算与派单一致（对象绑定无漂移）；delta 依据三源一致（M3-REPORT / CODE R3 / R8）。

**结论：APPROVED_WITH_NOTES，unresolved_blockers=0。** R5 增量四项收敛 + 锚点裁定（接受 a)）+ 顺带状态行全部落地；R5 已批面零回退；残余 2×P3（§5.4 单形态衔接措辞、"首次可行动"修辞）非阻断，可留合入前小修或按现状接受。host/运行面维持 NOT_RUN 诚实披露。
