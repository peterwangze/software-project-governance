# M-0 版本面组装报告 — 0.96.0（REL-100）

- **版本**: 0.96.0 · **组装时点**: 2026-10-07（+0800） · **状态**: **M-0 组装完成（准备态——M-1 版本面 bump 待 Governance Developer 派发执行）**
- **主题**: 次版本线：「做薄」债务本金偿还与看护基线治理批（Minor Line: B16 Principal Repayment & Guardrail Baseline Governance）——B16 债务本金偿还 + DEC-316/317 审查残余 sweep + 治理卫生登记 + 宿主 incident 根治 + 棘轮基线两跳 regen
- **版本定义**: 0.95.0→0.96.0 MINOR bump（DEC-318 候选批组建 + TRIAGE-REL-100 用户立项 2026-10-06「立项，下会话执行」——DEC-312(4)「正式预留随该版 M-0」由本报告兑现）；无破坏性变更（行为收紧面均为既有承诺的缺陷修复兑现——fail-closed 承诺成立）、无机制激活翻转、无 `.governance` schema 变更。
- **执行角色说明**: 本报告由 Coordinator 起草（DSH 环境治理记录边界——`docs/release/**` 属治理记录面）；机器事实全部取自 EVD 行、REVIEW 行、RECO 行、文件实读与 Coordinator 本会话实跑命令输出（check-governance full PASS / check-version-consistency 13 处一致 @0.95.0 / git status ahead 8 / git log 七票哈希）；commit 哈希未取得项以「回填位」标注列入 §7。

---

## 1. 载荷一致性核对（七票 vs 版本行 vs 路线图）

### 1.1 七票状态实读（plan-tracker L86~L96 票行 + git log 实测）

| 票 | 标题（摘要） | commit（实测） | 证据锚 | 审查锚（终态） |
|---|---|---|---|---|
| FIX-435 (P1) | B16 债务本金偿还——archive.py C2 拆分续 + module_size exclusions 棘轮回收 | `e1457a8` | EVD-1331（op-ef308a42…，TRIAGE 机录在案） | REVIEW-FIX-435-R0 AWN/0 → F-1 随票修订 → R1 AWN/0（Code Reviewer 双轮） |
| FIX-436 (P2) | DEC-316/317 sweep 收尾批（F-2 措辞/R1-1 锚失配用例/注释级/F-B3 advisory 载体/F-C1） | `c442e07` | EVD-1334 + RECO EVD-1335 | REVIEW-FIX-436-R0 AWN/0（Code Reviewer） |
| FIX-437 (P2) | 治理卫生登记批（快速通道——Check 30c 处置 + RISK-066 缓解引用改形） | 治理终态（快速通道免产品 commit——.governance 面） | EVD-1328（TRIAGE）+ EVD-1333（交付） | Coordinator 直写治理面（FIX-228 边界免 CLI；机录 EVD-1333） |
| FIX-438 (P1) | FEAT-088 后置债——契约快照/archguard 基线 sanctioned regen（ratchet 五轴 FAIL 消解）+ 契约族测试归位 | `f1a47fd` | EVD-1332（op-c1c5546f…） | REVIEW-FIX-438-R0 AWN/0（非掩盖性六项机证——Code Reviewer） |
| FIX-439 (P1) | DSH bootstrap splice 段定位缺陷族 + evidence-append 拒绝零持久化（外部宿主 incident 紧急插入——第 2 次复发根治） | `f884829` | EVD-1336 + RECO EVD-1337（DEC-323） | REVIEW-FIX-439-R0 AWN/0（Code Reviewer；F-1 归 FIX-440 承接） |
| FIX-440 (P2) | FIX-439 R0 F-1 承接——bootstrap 读侧 CRLF EOL 保留 + F-2/F-3/F-6 P3 riders | `1a56797` | EVD-1338 + RECO EVD-1339 | REVIEW-FIX-440-R0 AWN/0（Code Reviewer；P3×3 入观察池） |
| FIX-441 (P2) | 0.96.0 M-0 前置——archguard 基线 sanctioned regen rider（DEC-324 路径 A） | `36ff0be` | EVD-1340 + RECO EVD-1341 | REVIEW-FIX-441-R0 AWN/0（非掩蔽性逐值对账 14 项——Code Reviewer） |

**结论：七票全 committed（git log 实测七哈希在位），审查链全终态（AWN/0——FIX-435 双轮、FIX-436/438/439/440/441 单轮、FIX-437 快速通道治理面），与 REL-100 任务行调度载荷一致。**

### 1.2 路线图核对（plan-tracker L205 版本行）

- 0.96.0 行在位：**候选批（2026-10-06 组建——用户 ask 裁定「三票入批，Slice-3 留池」〔DEC-318〕；DEC-312(4)：0.96 仅候选不正式预留，正式预留随该版 M-0）**——本报告即 M-0 正式预留兑现动作。
- 行内约束列核对：①「留池观察：FEAT-084 Slice-3 缓存子集（无活性阻塞信号——m-0-assembly §3 论证）」→ 本版不计入（沿用 0.95.0 m-0 §3 核算结论，无新活性信号）；②F-B1/B2/B4/B5 观察 P3 随 FIX-436 注记（已随票注记——EVD-1334）；③其余候选见 session-snapshot §0.96.0 候选池（观察池清扫另行批次，非本版载荷）。
- **差异披露（更新 2026-10-07 双审后）**：L205「包含任务」列 FIX-441✅ **已回填**（28c 热事实源修复顺带）；**REL-100✅ 随 M-8 收口补记**（发布链票自身）。

### 1.3 需求面对照

- **REQ-147（治理做薄，P1）**：🚧 推进中——**本版交付 Phase 2 首笔债务本金偿还**（archive.py 4241→1697 + exclusions 4 行回收——B16 债务从「止增」转「真实清偿」）；棘轮基线两跳 regen（27352→27792→27866）恢复看护全绿。**本版不主张 REQ-147 全量交付**（Phase 3 及其余 W 面按 0.97+ 候选节奏——no-overclaim）。
- **宿主 incident（incident-20261006-dsh-bootstrap-splice-repeat）**：✅ 根治（FIX-439/440——第 2 次复发环闭合：bootstrap 双段并存/span 越界吞噬宿主尾段/evidence-append 拒绝仍持久化三缺陷族 + CRLF EOL 承诺兑现）。

---

## 2. B16 债务两栏核算（正式载体——A8 口径，评估面见 session-snapshot 2026-10-06 §未完成/已延期 L47）

**B16 定义与两栏义务**（承接 m-0-assembly-0.95.0.md §2）：FIX-430 exclusions 为「止增」登记——「0.95 拆分落地后移除」（EVD-1309 原文）；止增与实际还债 MUST 分别报告。

### 2.1 止增栏——FIX-430 exclusions 机制止增面（本版：净空兑现）

| 项 | 事实与锚 |
|---|---|
| @0.95.0 状态（承前） | exclusions 4 行在位、债务本体未偿（archive.py 3663 行超阈值、28n WARN 被压制）——m-0-assembly-0.95.0 §2.1 如实披露。 |
| 本版动作 | **exclusions 4 行移除**（FIX-435 交付——`core/architecture-health.json` exclusions 中 archive.py 条目回收；止增语义「0.95 拆分落地后移除」兑现——EVD-1309 原文义务闭合）。 |
| @0.96.0 状态 | **exclusions 面净空（archive 族）**：28n 面对 archive 家族裸露达标（check-architecture-health 家族零 finding——EVD-1331）；健康信号从「豁免压制的假安静」转「真实达标的真安静」。 |
| 纪律约束 | A5 维持：不扩 exclusions 放宽债务（本版零新增 exclusions 行）；ArchGuard 棘轮只紧不松（R1 anchor 单调上行 sanctioned regen——§2.2 #2）。 |

### 2.2 还债栏——本版本实际偿还项（逐项证据锚）

| # | 偿还项 | 内容 | 证据锚 |
|---|---|---|---|
| 1 | **B16 债务本金偿还（archive.py C2 拆分续）** | archive.py 4241→1697 行（入口壳+host seam 同签名包装器），拆出 archive_verdicts 726 / archive_migration_engine 1170 / archive_entity_migration 589 / archive_cli 332（家族全 ≤2000 阈值）；行为等价三层闭环（dry-run 零翻转 / CLI 逐字节 / AST 78 对比）；219 测试全绿（+8 守护） | EVD-1331；REVIEW-FIX-435-R0/R1 |
| 2 | **archguard 基线两跳 sanctioned regen（看护恢复）** | ①FIX-438：anchor 27352→27792（+440 逐 commit 机证）/R2 48/R4 1369（四代 census 归因拆分）/R5 99+73/R7 committed==fresh——ratchet 全轴 PASS 0 violations，契约族 12 测试归位（全量 19F→4F）；②FIX-441：anchor 27792→27866（+74=c442e07 已审增量）/R4 1369→1371/R7 committed==fresh——fatal gate green 维持 | EVD-1332（DEC-319/320 路径 A）；EVD-1340（DEC-324 路径 A） |
| 3 | registry.py dispatch 行补登 | check-exploration-channels 漏 dispatch 行（FEAT-064 同型）补登 + 三镜像字面量同步（98→99 keys/95→96 handlers） | EVD-1332 |
| 4 | sweep 收尾（DEC-316/317 残余） | F-2 M10.2 F-A5 措辞收紧与 S2 自洽；R1-1 锚失配/unreadable/坏JSON 3 case（守卫 6 分支 committed 覆盖）；R1-2/R1-3 注释级；F-B3 advisory 载体（WARN 级骑 Check 12/CLI 双面，registry 零 churn）；F-C1 document-wide 措辞明示 | EVD-1334；DEC-322(1)(2) |
| 5 | 宿主 incident 缺陷族根治 | bootstrap splice 统一段边界（canonical H2 全集 + `---`/H1 显式终止符，span 收敛不吞宿主尾段）+ H2-singleton 写前守护（违规 ⇒ exit 1 原文件字节不变）+ evidence/decision-append md 腿校验前置（拒绝 ⇒ 零持久化零台账）+ CRLF 读侧 EOL 保留（段外逐字节承诺成立）+ dry-run 预演 guard | EVD-1336/1338；REVIEW-FIX-439-R0/440-R0；DEC-323 |
| 6 | 治理卫生登记 | Check 30c 两行处置（豁免清单预登记路径——DEC-321 绑定 DEC-146 升级批义务）；RISK-066 缓解引用改形（跨实体裁定引用→任务实体锚，Check 36 R3 消解） | EVD-1328/1333 |

**两栏总结论**：止增面**净空兑现**（exclusions 4 行回收、28n 裸露达标）；还债面 6 项落账——本版为 B16 债务从「止增」转「本金真实清偿」的兑现版（REQ-147 Phase 2 首笔），且看护基线经两跳 sanctioned regen 恢复 fatal gate green（先例链 FEAT-080/081/FIX-416/420/421/423/083/438/441 追加）。遗留如实披露：closure_chain.py/dsh_compat.py/governance_store.py/loop_migration.py 等 28n 预存组不在本版载荷（0.97+ 候选池——session-snapshot 观察池「closure_chain 拆分」在案）。

---

## 3. 硬约束延续声明

1. **DEC-312(4)/DEC-318 载荷边界**：本版载荷冻结为七票（§1.1）+ 发布链票 REL-100 自身；FEAT-084 Slice-3 缓存子集留池（0.95.0 m-0 §3 核算结论延续，无新活性信号）；观察池（各票 R0 P3 项/EXC-001 到期/registry 陈旧/自举豁免续期/28s 过阈披露/closure_chain 拆分候选）不占本版，另行批次。
2. **A5 棘轮纪律**：R1 anchor 单调上行（27352→27792→27866 两跳均经裁定先例 sanctioned——DEC-320/DEC-324 路径 A）；exemptions 零新增；only-down 自新锚起算。
3. **A7 阶段推进纪律**：本版承载 REQ-147 Phase 2 首笔（B16 本金偿还）——Phase 3 及其余 W 面不随本版号推进主张。
4. **止增纪律**：本版新增守护面（H2-singleton 写前守卫/dry-run 预演 guard/quote_sync 锚失配 case）均为既有票承载与审查链闭环的缺陷修复面，未经新增准入通道扩治理责任面。
5. **发布门状态（M-0 评估面——承 session-snapshot 2026-10-06 §0.96.0 候选池 L61）**：archguard-ratchet **PASS 0 violations（fatal gate green）**；check-governance full **PASS**（2026-10-07 本会话深检复证——含 REL-100 执行包落盘后 0 issues）；全量失败面=既有披露集族（test_verify_workflow f=2 预存 / contract_matrix 3 预存 result_shapes 漂移 / injection-budget-strict / M0 pin-hash 族）——**M-2 披露面定谳**（§7 复跑清单第 6 项 + 定谳预案）。

---

## 4. 版本号决策记录（semver + bump 理由）

| 项 | 决策 | 依据 |
|---|---|---|
| bump 级别 | **MINOR：0.95.0 → 0.96.0** | ①`core/VERSIONING.md` L49 起 MUST 触发条目 **2**（references/ 文件变更——FIX-436 修改 behavior-protocol.md M10.2 措辞/L855-L857；FIX-438 registry/generator 面）；②新增守护能力面（FIX-439 H2-singleton 写前守护 + evidence/decision-append 校验前置 + FIX-440 dry-run 预演 guard——新增 B 级自动化守卫，VERSIONING L12「新增 MUST 规则、新增 B/C 级自动化能力」Minor 触发）；③非纯 bug fix（含结构性拆分与基线治理），PATCH 不足以承载 |
| bump 义务（MUST） | 触发条件已满足 | 版本行 L205 约束 + TRIAGE-REL-100 用户立项（2026-10-06「立项，下会话执行」）；0.96.0 无 tag/预留冲突（0.95.0 已发布顺延 +1，不跳号；1.0.0 预留位未触碰） |
| 版本号合法性 | 正式预留由本报告兑现 | DEC-312(4)「0.96 仅候选不正式预留，正式预留随该版 M-0」——本报告 §1.2 即兑现载体 |
| semver 合规性 | 合规 | SemVer 2.0.0 于 0.x 段：MINOR=向后兼容的新功能累积里程碑；本版无 Breaking（见下） |
| Breaking 评估 | **无** | ①CLI 接口与 JSON schema 零变更（拆分经 verify_workflow.py 入口 re-export 保持调用面透明——FIX-435 CLI 逐字节对照实证）；②行为收紧面（bootstrap H2-singleton 守护 exit 1 / evidence-append 拒绝零写入 / span 收敛）均为**既有承诺的缺陷修复兑现**（fail-closed 承诺原未成立——incident-20261006 实测），合法调用方零破坏；③无 MUST 规则删除/重命名；④无 Gate 行为语义改变、无 `.governance` schema 变更（FIX-437 为治理登记面改形）；⑤回归基线：test_verify_workflow **Ran 1061 failures=2**（预存披露集，Coordinator 独立复跑定谳——EVD-1338）+ dsh 族 65 OK——M-2 复跑定谳（f=2 归零或 GO 终审披露） |
| 升级路径 | /plugin update | 入口 bootstrap 版本戳 0.96.0 后经 FEAT-035 升级确认门自升级（用户未响应前零写操作）；无迁移指南需求 |

---

## 5. 产物清单（M-0/M-4 批）

| 产物 | 路径 | 状态 |
|---|---|---|
| M-0 组装报告（本件，含 B16 两栏核算 + 版本号决策记录） | `docs/release/m-0-assembly-0.96.0.md` | ✅ 本批 |
| CHANGELOG 0.96.0 段（准备态） | `project/CHANGELOG.md`（canonical 面） | ✅ 本批（追加） |
| 发布检查清单 | `docs/release/release-checklist-0.96.0.md` | ✅ 本批 |
| 回滚方案 | `docs/release/rollback-plan-0.96.0.md` | ✅ 本批 |
| feature-flags 件 | `docs/release/feature-flags-0.96.0.md`（**N/A 声明件**——check-release release-docs 门要求文件在位，内容声明无旗标面与回退路径；0.95.0 先例同构） | ✅ 本批 |

---

## 6. M-2 披露面定谳预案（0.93.1 GO 终审先例口径）

**披露集族清单**（M-0 评估面 + 2026-10-07 check-release 后台复跑待证）：

1. **contract_matrix 3 预存 result_shapes 漂移**（agent_locks/plan_tracker/write 面——.governance 运行态 vs 快照；FIX-441 边缘发现，锁清空态复现）→ 处置优先序：regen 快照对齐运行态 → 不可对齐时豁免登记（DEC-321 先例）→ 均不可行时 GO 终审 ask。
2. **injection-budget-strict** → 处置优先序：预算面核实（resident/M1+M2 与 FEAT-085 基线同值零变化口径）→ 严格面豁免登记 → GO 终审 ask。
3. **test_verify_workflow f=2 预存**（M0 pin-hash 族）→ 归因披露（HEAD 预存 stash 对照先例）或 bump 后随版本面 pin 更新自然归零。
4. **M0 pin-hash 族**（版本面 pin——M-1 bump 后随 `release-projection --write` 确定性再生更新）。

**定谳纪律**：先尝试全绿消解；不可全绿时产出事实与选项经 AskUserQuestion 交用户 GO 终审裁定（0.93.1 先例），不自行定谳；定谳结果 DEC 入账。

---

## 7. 需 Coordinator 复跑/回填清单（M-2 面）

**复跑（发布门 M-2 面——全量）**：

1. `python -m unittest test_verify_workflow` —— 预期 **Ran 1061，failures=2（预存披露集）或 M-2 定谳后归零**（EVD-1338 实测口径；M-1 bump 后 pin-hash 族随版本面再生可能归零——以实测为准）。
2. `check-governance --summary-only`（发布门 full 面）—— 2026-10-07 已 PASS（REL-100 执行包落盘后 0 issues）；M-2 于 M-1 bump 后复跑。
3. `check-injection-budget` —— **M-2 终态 PASS @6200**（DEC-325 重定标：lightweight 4303 / strict 6059≤6200；原「4244/6000 零变化」预期被 DEC-325 取代；M1+M2 combined 342≤370 仍精确成立——EVD-1344）。
4. `check-cross-references` + `check-manifest-consistency` —— 预期 PASS（EVD-1340 时点已证，门禁复跑）。
5. `check-version-consistency` —— bump 后 13 处一致 @0.96.0（当前实读全 0.95.0——待 M-1）。
6. `check-release --version 0.96.0 --require-changelog --lineage-mode candidate` —— 2026-10-07 后台复跑（bump 前时点）：4 issues 归因=hot-fact-source 4 项时间竞态（28c 修复后复跑 PASS 证实）/ release-docs untracked（M-4 组装 commit 后消解——0.95.0 先例同构时序）/ execution-gates unit-tests f=2（已定谳：DEC-325 后全量 1061 OK）。**M-4 后复跑终局判定**。
7. `release-ledger --version 0.96.0 --no-remote`（M-5/M-6 candidate 态；tag/push 后 `--remote origin` + released 模式）。
8. `quality-tools` —— 结构化记录（未安装记 NOT_RUN，不虚构 PASS）。
9. `archive.py migrate --auto --dry-run`（M-8 持续归档触发检查；如需归档→执行+`check-archive-integrity`）。
10. git log 区间锚 —— 载荷窗口 `1ee500a（v0.95.0 tag peel）..M-4 组装 commit`（七票哈希已实测在位 §1.1；REL-100 组装 commit/M-5a/M-5b 哈希待回填 rollback-plan 回填位）。

**回填（发布收口 M-8 面；双审 findings 当场闭环注记 2026-10-07）**：

- 版本窗口终值（`1ee500a..M-4 tip` 终值）→ CHANGELOG 0.96.0 段与 rollback-plan 回填位。
- L205「包含任务」列补 REL-100✅（FIX-441✅ 已回填；七票行 ⏳→✅ 翻转已随双审 findings 当场闭合）。
- CHANGELOG 0.96.0 段发布日期（taggerdate 权威——FIX-349 口径）。
- plan-tracker L11「工作流版本」行发布终态刷新（当前组装中态）。
- ~~CHANGELOG 补 DEC-325 披露~~（M-3b F-1——**已当场闭合**：决策链/行为变更段/版本面再生纪律均已补）；~~CHANGELOG f=2 终态注记~~（M-3a F-3——**已当场闭合**：Ran 1061 OK 口径）；~~checklist §C/§G 预算预期终态化~~（M-3b F-2/M-3a F-4——**已当场闭合**）；~~B16 边界句~~（M-3b F-7——**已当场闭合**）；~~feature-flags 口径统一~~（M-3b F-4/M-3a F-2——**已当场闭合**）；~~§A 行区间精确化~~（M-3b F-9——**已当场闭合**）；~~§1.2 差异披露收窄~~（M-3b F-10——**已当场闭合**）。
- M-8 剩余：rollback-plan hooks 重装步注记核验（M-3b F-8——见下）、injection_budget.py L76-80 注释时态精化（M-3a F-5——产品面微任务）、EVD 补 contract_matrix 3 漂移消解归因注记（M-3b F-11——FIX-438 regen 归位契约族后 28c/governance/全量 f=0 三重佐证，随 M-8 收口 EVD 行落账）。

---

## 8. 边界声明（保守边界——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success；非 Windows 平台未验证，验收全部在仓库内完成（RISK-036 先例口径延续）。B16 本金偿还以 archive 家族为界（closure_chain 等 28n 预存组如实披露未偿）；REQ-147 仅 Phase 2 首笔交付不主张全量；宿主 incident 根治以「云视TV」实测三缺陷族为界（incident 文件口径），不声明全部外部宿主形态验证。
