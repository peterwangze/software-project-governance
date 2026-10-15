# M-0 版本面组装评估报告 — 0.98.0（REL-102）

- **版本**: 0.98.0 · **评估时点**: 2026-10-15（+0800） · **状态**: **M-0 组装评估完成（GO 建议·有条件——条件见 §7；定谳项见 §8，正式裁定权在 Coordinator/用户）**
- **主题**: 次版本线：「可信有界执行内核」批（Trusted Bounded Execution Kernel）——DEC-330 联合裁定载荷（FEAT-093 权威账本 / FEAT-094 审查可信链 / FEAT-095 动作级执法〔M-0 前置调研〕 / FEAT-096 执行隔离 / FEAT-097 goal 桥接 / FEAT-098→**0.99.0 顺延〔DEC-354〕**）+ 桥接/修复票（FIX-442~446 族）
- **版本定义**: 0.97.0→0.98.0 MINOR bump（TRIAGE-REL-102 用户立项 2026-10-10「0.98 立项组装（推荐）」；DEC-354 载荷重定：核心载荷=093/094/096/FIX-442〔已 commit〕+095/097〔dev 完成〕）
- **执行角色说明**: 事实集由 **Release Analyst**（只读调研代理，零写入/零 git 写）受 Coordinator 派发采集（2026-10-15）；机器事实全部取自本会话实跑命令输出与治理台账实读（EVD/REVIEW/DEC/plan-tracker/git）。本报告文件由 Coordinator 落盘（docs/** 治理记录）；全程只读产品面——不做版本 bump、不改产品代码、不 git commit。
- **仓库时点**: master 与 origin/master 同步（无 ahead/behind）；工作树**脏**（24 个 M + 大量 untracked——见 §2.3）；载荷窗口 = `v0.97.0..HEAD` 共 6 commits：`42ddbca`（FEAT-093）/`099acbf`（FEAT-094）/`75cc7e5`（FIX-442）/`bf6942d`（FEAT-096）+ `c783cff`（AUDIT-159 治理）/`9950076`（REL-101 M-8 收尾）；`git tag --list "v0.98*"` = 空；canonical CHANGELOG 最新段 = 0.97.0（无 0.98.0 段——M-1 时点预期态）。
- **前置实核承接**: EVD-1697（上轮发布前置实核，21 issues 基线）+ DEC-353/354（载荷重定）——本报告为 M-0 正式载体（REL-102 验收①）。

---

## 1. 载荷一致性核对（票行 vs git vs evidence 三源交叉）

### 1.1 载荷票状态实读

| 票 | plan-tracker 行 | 行状态 | 实核完成态（git/evidence） | 证据锚 |
|---|---|---|---|---|
| FEAT-093 (P1) 权威账本 | L87 | ✅ 完成(2026-10-10) | R0 NEEDS_CHANGE→**R1 AWN/0**；commit `42ddbca`（在 v0.97.0..HEAD 窗口内） | EVD-1363；REVIEW-FEAT-093-R0/R1 |
| FEAT-094 (P1) 审查可信链 | L88 | ✅ 完成(2026-10-10) | R0 AWN/0（P2-1 随票闭环）；commit `099acbf` | EVD-1366；REVIEW-FEAT-094-R0 |
| FEAT-095 (P1) 动作级执法 | L89 | approved(2026-10-15)「commit 待发布链 M-6 组装」 | dev 链全闭环：enforcement.py 727 行 **untracked（零 commit）**；R0 AWN/0→P1-1 措辞收窄（DEC-357）→同 Reviewer R1 AWN/0 | EVD-1698~1701；REVIEW-FEAT-095-R0/R1；RECO-FEAT-095 |
| FEAT-096 (P1) 执行隔离 | L90 | ✅ committed(2026-10-10) | R0 NEE→**R1 AWN/0**；commit `bf6942d`（保守面四件套） | EVD-1367 |
| FEAT-097 (P1) goal 桥接 | L91 | 🆕 approved「待实施」——**行滞后** | 实际已实施：R0~R6（R6=DEC-333 修复后 delta 复审 **AWN/0/unresolved_blockers=0**）；goal_bridge.py 1040 行 + test_goal_bridge.py 722 行 **untracked**；EVD-1460 引擎验收 1115 tests 通过；task-row 收口机录未见 | REVIEW-FEAT-097-CODE-R0~R6（untracked）；EVD-1432~1471 |
| FEAT-098 (P2) 可玩性脊柱 | L92 | 🆕(2026-10-10) | **顺延 0.99.0**（DEC-354；L209 版本规划已载） | DEC-354（经 EVD-1697） |

关联桥接/修复票（0.98.0 target，L81~L85）：

| 票 | 行状态 | 实核状态 | 备注 |
|---|---|---|---|
| FIX-442 | ✅ 完成 | R0 AWN/0，commit `75cc7e5`，EVD-1365 | 已在发布窗口 |
| FIX-443 | 「approved 尚未开发」——**行滞后** | review-FIX-443-CODE-R0 已落盘（**AWN/0**，blob 绑定 d2162ac→26ae776 一致）；工作树 M loop_runtime_claims.py+test 未提交 | commit 待落 |
| FIX-444 | ⛔ BLOCKED | R0~R2 在（R2=NEEDS_CHANGE/3）；R3 熔断→DEC-334→**FIX-445 承接** | 链已转移 |
| FIX-445 | 「BLOCKED 尚未设计」——**行滞后** | DESIGN R0~R15（R15 AWN/0 但 `implementation_authorized:false`）+ CODE R6（**BLOCKED/3，round6=fuse→T4 用户升级，无自动 R7**）；hooks/commit-msg 59,453B 大改在工作树未提交 | **链未收口（T4 悬置）** |
| FIX-446 | 「approved 尚未执行」——**行滞后** | CODE R16→R17（R17 **AWN/0**，DEC-351/352 限修三 file）；EVD-1695/1696 已收口 approved | commit 状态待核（§8 定谳⑥相关） |

**结论**：①DEC-354 核心载荷审查链**全部到达 AWN/0 终态**（093 R1/094 R0/096 R1/095 R1/097 R6 + FIX-442 R0 + FIX-443 R0）；②其中四票已 commit（窗口 6 commits 干净可辨），**FEAT-095/097/FIX-443 产品代码全部 untracked 零 commit**；③plan-tracker ≥5 行状态滞后于 evidence/review 工件实况（097/443/445/446 + REL-102 自身）——发现即闭环义务（§7 C2）。

### 1.2 需求面对照

- **「可信有界执行内核」（DEC-330）**：承载——FEAT-093/094（权威账本+审查可信链，CLI 级执法）/FEAT-095（动作级执法，协议级+CLI 级）/FEAT-096（执行隔离）/FEAT-097（goal 桥接）；发布验证底线=DEC-330 故障注入六项（§3.2 映射）。
- **DEC-354 载荷重定**：FEAT-098 顺延 0.99.0——版本规划 L209 已载，无欠账。

---

## 2. 门禁现状实测（本会话逐条实跑记录）

> 约定：全部为只读评估命令；FAIL 不修（修复属 §7 条件项与发布链动作）。check-governance 明细 = Coordinator 本会话 `--level strict` 实录；其余为 Release Analyst 实跑。

### 2.1 `check-governance --summary-only --level strict`

**实测：24 issues。** FAIL 族（逐条）：

| Check | 差距 | 归因 |
|---|---|---|
| 10 | 2 M5 anti-pattern（源文件问句模式；明细待 Track B 定位） | 待定位（产品代码/治理记录待判） |
| 18c/18d/18d-RB2/18f/18i | FIX-444/445/446/FEAT-095 四票执行包 pending 口径校准（last_run/quality_budget/vertical_slice/interruption_policy/required_evidence/success_metrics） | 流程时序态（四票 dev 中或链转移）——Coordinator 直写 `.governance` 消解 |
| 28s | evidence-log.md **1216.4KB** 超 FAIL 线 | 既有体量；**归档 dry-run 已跑：无可归档数据**（802 条全保留：active_task_ref=392/missing_task_ref=196 等）→ 转 M-2 定谳项 |
| 30 | 2 closure violation（明细待 Track B） | 待定位 |
| 31 | `docs/design/FIX-445-source-verification-R1.md` ragged table row（该文件 untracked） | FIX-445 工件——随链收口或归位消解 |

WARN 族：24（static-pin 过期豁免）/ 25（58 untracked）/ 28n×7（closure_chain/dsh_compat/governance_store 等预存组）/ 28q（hooks_drift: commit-msg）/ 28s×2（plan-tracker 217.1KB / decision-log 238.6KB）/ 30c×42（undated-record，DEC-146③ 接受基线）/ 35（snapshot freshness）/ 36（risk mitigation ×3）。

### 2.2 `check-release`（候选门面）

**实测：Result FAILED — 3 issues（16 项 PASS）。**

| 门面 | 结果 | 归因 |
|---|---|---|
| execution gates（第 16 面） | **FAIL**：governance health exit=1（24 issues，即 §2.1）+ unit tests exit=1（**Ran 1135，3F+1E**；样例 test_verify_workflow.py:133 `test_claim_command_emits_complete_pass_report` 断言 0!=1；与上轮 EVD-1697 基线 1115/3F+1E 同构，+20 为 FEAT-095 用例） | 24 issues=Track B 修复面；**3F+1E=产品代码测试失败（新增阻断项，需 Developer 修复或定谳）** |
| loop runtime claim gate | **FAIL**：semantic_verdict=BLOCKED——`ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY: docs/design/FIX-445-source-verification-R1.md ragged table row` | untracked FIX-445 设计文档触发（=§2.1 Check 31 同根） |
| **强正面（全 PASS）** | version consistency / release fact source / hot fact source / runtime readiness matrix / first session measurement / governance pack status / sd integrity / agent adapters（六平台 static verified）/ projection sync / cross references / archive integrity / release docs（0.97 四件套）/ release lineage（candidate 边界披露）/ gate sequence / **one dot zero blockers** / verify+e2e 执行门 / **dsh upgrade regression（隔离 DSH_HOME 冒烟）** / loop fuse / changelog / governance exceptions | 版本面一致性 **PASS@0.97.0**（bump 未启动=M-1 未做预期态） |

既有披露集族 4 条 boundary 原样在场（pack status / lineage candidate / dsh 隔离冒烟边界 / exceptions annotation-only DEC-278(5)）。

### 2.3 工作树与归置状态（git 实测）

- 24 个 M（含 SKILL.md、verify_workflow.py、registry.py、hooks/commit-msg、contract_matrix/snapshots.json、architecture-baseline.json、两 archive 迁移件、六测试文件）。
- untracked 关键件：**enforcement.py / goal_bridge.py / tests/test_goal_bridge.py**（载荷产品代码）；30+ 份 review 报告（095-R0/R1、097-R0~R6、FIX-443-R0、FIX-444-R0~R2、FIX-445-DESIGN-R0~R15+CODE-R6、FIX-446-R16/R17+supplement×5）；`docs/design/`；`docs/requirements/FIX-445-health-resume-clarification-20261013.md`；`rowdump.txt`（临时件）。
- **判定**：载荷代码与审查工件的 commit 归置是 M-1 前硬前置（§7 C1）。

### 2.4 `archguard-ratchet`（七轴）与补充

- **FAIL ×3**：R1 mainfile loc **28204>anchor 28160**（+44，only-down，标签 EXPIRED:0.82.0）；R5 新 dispatch key `enforcement-check` 不在 FEAT-020 冻结快照（FEAT-095 未 regen）；R7 committed!=fresh（engine 变更未 regen）。R2/R3/R4 PASS（48/48、12 edges、1376≤1376）；R6 INFO（cold import 209，Δ1）。
- 处置路径：sanctioned regen（DEC-324/326 先例）或收窄——R1 +44 的归属（FEAT-095 enforcement 接线增量 vs 其他）需在 regen 裁定时核（§8 定谳②）。
- `quality-tools`：**NOT_RUN**（ruff/mypy 未安装，运行时依赖 false）——按环境事实披露（§8 定谳⑤）。
- `check-version-consistency`：**PASSED @0.97.0**（13 文件一致；1 WARN：static-pin 过期豁免 test_archive.py:5862——与 §2.1 WARN 24 同根）。

---

## 3. FEAT-095 harness 执法能力调研（M-0 前置核心项）

> 既有载体：`docs/research/feat-095-harness-enforcement-capability-2026-10-10.md`（289 行，git M 未提交；EVD-1362）。Release Analyst 本次对全部关键 DSH 锚点独立重验（DSH checkout =@deepseek-ai/dsh@0.1.5-rc.3，package.json 实读；**锚点全部仍有效**）。五平台（非 DSH）结论沿 2026-10-10 报告未重验。

### 3.1 能力判定表

| 能力 | 判定 | 机制+证据 |
|---|---|---|
| 拦 spawn（动态拒单次派发） | **原语存在、插件未接线**→当前=仅协议级+CLI 级 | DSH 真执法原语：`dsh-tools/README.md` L85 `ctx.tools.guard()` 单调同步守卫（拒绝后不可翻案）+L103 固定管线 pre-execute→guards→execute；但插件 host-contract.json L478-505 tool-subagent 行 config_keys 仅 provider/toolName/backgroundMode（**无 toolFilter/maxDepth**）、L763-775 own.host_row `warn_only:true`（**不注册任何 guard**） |
| per-child 工具面限制 | 原语存在（每实例**静态**）→未使用 | `dsh-tool-subagent/README.md` L52 `toolFilter`、L53/L63 `maxDepth`（执行时拒绝，宿主级）、L214「Non-routing child policy is fixed per instance」；`dsh-tools` L81 `ctx.tools.restrict()` per-agent 掩码 |
| 工作区隔离 | **DSH 真执法（策略围栏）**；本部署未启用 | `dsh-fs-sandbox/README.md` L12/L46/L75：read-only 拒绝一切变更 / workspace-write 限 workspace+temp / `FS_SANDBOX_DENIED` 结构化拒绝；L123 诚实边界「A policy fence, not a kernel boundary」。**本会话 runtime 实测 danger-full-access + approval disabled**（宿主有原语≠用户开了围栏） |
| 审批门 | DSH 真执法原语；本部署 disabled | 调研报告 S13（dsh-user-approval L12 ask/never fail-closed；presets L38-44 sandbox×approval 捆绑；沿报告，低风险未重验） |
| agent-locks 锁执法 | **咨询性**（harness 不消费） | `.governance/agent-locks.json` 纯数据文件（当前空）；DSH 无读取机制；CLI 面 agent-locks-acquire exit 2 为写入时校验，绕过面=不调用 CLI |
| goal 面机械约束 | **部分真执法（机械 floor）+语义缺口** | `dsh-tool-goal/README.md` L55：create/edit/pause/resume 需 runtime-root 当前轮**直接人类消息**（subagent 不能建/改 goal）；blocked 在配置轮数前**机械拒绝**；L149-150：semantic intent 与 same-condition blocking 仍是**模型判断** |
| commit 边界 | **仓库级真执法（最强面）** | infra/hooks/pre-commit Step7 产品代码无 APPROVED 审查证据→exit 1（BLOCKING）；commit-msg 14 面 exit 1；逃生门 `--no-verify` 文档化；**无 pre-push hook**（发布边界最薄） |
| 插件六边界执法（FEAT-095 交付物） | **协议级+CLI 级（预授权降级，如实披露）** | enforcement.py：BOUNDARIES(L89)/STRATEGY(L179)/decide(L230)/cmd_enforcement_check(L606)，出口码 0/2/3/4，`ENFORCEMENT-ACTION` jsonl 机录含 remedy；SKILL.md L239-262「动作级执法」段=MUST 协议契约+降级披露（六平台无宿主级拦截、不做宿主级声明）；两面一致性由 test_enforcement_skill_protocol_face_matches_cli_face 机守 |

### 3.2 DEC-330 故障注入六项 × 保障层级映射

| 验收项 | harness 真执法？ | 实际保障层 |
|---|---|---|
| 错修订审查拒收 | 否 | CLI 级（task-row-update CAS + review-record exit2；FEAT-093/094 已落地） |
| 报告机录冲突拒收 | 否 | CLI 级（review-record CONFLICT 判定，FEAT-094） |
| R2 不漏建 | 否 | CLI 级（review-record 自动 next_round，FEAT-094） |
| 代理死亡可恢复 | 否（DSH job/subagent 状态面未接线） | 协议级+CLI 级（FEAT-094 ABORTED/UNKNOWN supervisor 生成） |
| blocked 后无未授权执行 | **部分**（goal 机械 floor；报不报 blocked 是模型判断） | goal_bridge.py（FEAT-097）协议级+CLI 级：BLOCKED 无用户裁定 refuse + unauthorized_attempts 落账（docstring L27-32 实读） |
| 无关任务不被全局冻结 | 否（harness 无此概念） | 纯策略面：enforcement scoped 白名单（fix/re-review/forensics）+ 审查债限流仅 admission 两面（SKILL L260 铁边界①） |

### 3.3 未证实面（沿调研报告 §7，本次未消解）

U1 第三方包注册 guard 实际可行性（架构可达但零 PoC）/ U2 claude 会话内 per-subagent 限制 / U6 CLI 旗标组合面 / U7 拒绝后模型换通道绕行的对抗面。U1 是否立项后续票 → §8 定谳⑥。

**调研结论（M-0 前置判定）**：FEAT-095 的「插件能否真拦 spawn/隔离工作区」= **DSH 宿主具备真执法原语（guard/toolFilter/sandbox 围栏），插件当前未接线，交付物如实以协议级+CLI 级执法+降级披露落地**——与 DEC-330 六项验收的 CLI/协议级保障定位自洽，无失实声明；宿主级接线（guard 注册/toolFilter 配置）为后续增强面（U1 PoC）。

---

## 4. 风险与余量评估（既有基线 vs 本批引入归因）

| # | 项 | 归因 | 处置 |
|---|---|---|---|
| 1 | FEAT-095/097/FIX-443 载荷代码 + 30+ 审查工件 untracked 零 commit | dev 完成待归置（流程时序态） | §7 C1（commit 归置——审查证据均在位） |
| 2 | plan-tracker ≥5 行滞后 | 机录缺口 | §7 C2（task-row-update 对齐） |
| 3 | check-governance 24 issues（18 族四票包校准 + Check 10/30/31 + 28s） | 流程时序态 + 既有体量 | §7 C3（Track B）+ 28s 转 M-2 定谳（归档 dry-run=无可归档数据） |
| 4 | unit tests **3F+1E**（1135 ran） | **产品代码测试失败（阻断项）**——与 EVD-1697 基线同构（+20 FEAT-095 用例） | §7 C4（Developer 修复或 GO 终审定谳——需先定位失败集） |
| 5 | archguard R1/R5/R7 FAIL | engine 已变未 regen（FEAT-095 接线增量） | §7 C5（sanctioned regen，DEC-324/326 先例；R1 +44 归属随裁定核） |
| 6 | FIX-445 链 T4 悬置（CODE R6 BLOCKED fuse→用户升级无后续裁定；DESIGN R15 AWN/0 未授权实施）；其 untracked 工件触发 Check 31/loop claim FAIL | **需用户定谳**（0.98 承载 vs 顺延） | §8 定谳①（关键决策——范围） |
| 7 | strict 注入预算 | 未复跑（0.97.0 基线 6172/6200，headroom 28tok + freeze line ACTIVE） | M-2 复跑兜底（载荷增文若触 resident 面则需等量收缩——本批载荷以 CLI/代码为主，SKILL L239-262 增文已计价与否待 M-2 核） |
| 8 | 28n×7 / 30c×42 / hooks_drift / 58 untracked 等 WARN | 既有基线（0.97.0 m-0 §2 遗留披露同源） | 不随本版扩大；untracked 归置随 C1 消解大半 |
| 9 | quality-tools NOT_RUN | 环境事实（ruff/mypy 未安装） | §8 定谳⑤（披露即可否） |

**本批引入面小结**：#1/#2/#3（18 族）/#5 为载荷交付的流程时序态（非产品缺陷）；**#4 unit tests 3F+1E 与 #6 FIX-445 链为实质阻断**；无未披露的本批引入 FAIL。

---

## 5. 版本号决策记录（semver + bump 理由）

| 项 | 决策 | 依据 |
|---|---|---|
| bump 级别 | **MINOR：0.97.0 → 0.98.0** | ①新增能力面（动作级执法 CLI + goal 桥接 + 权威账本/审查可信链/执行隔离——B 级自动化增强）；②TRIAGE-REL-102 用户立项 + DEC-354 载荷重定；③路线图 L209 既定 |
| 版本号合法性 | 无冲突 | 0.97.0 已发布顺延 +1 不跳号；1.0.0 预留位未触碰（one dot zero blockers PASS）；v0.98.0 tag 不存在 |
| semver 合规性 | 合规 | 0.x 段 MINOR=向后兼容新功能累积；enforcement 出口码/goal 桥接均为新增面，无 Breaking（见回滚） |
| Breaking 评估 | **无**（待 M-2 复核） | CLI 新增子命令/出口码为追加面；`.governance` schema 变更面待 M-2 全量测试核（3F+1E 修复后） |
| 回归基线 | **未达全绿** | unit tests 3F+1E（§4 #4）——**M-1 前置条件含修复或定谳**；契约/provenance/e2e/verify 面 PASS |
| 升级路径 | /plugin update | bootstrap 版本戳 0.98.0 后经 FEAT-035 升级确认门自升级（用户未响应前零写操作） |

---

## 6. （并入 §4/§5，保持先例节号连续性占位）

---

## 7. GO-NOGO 建议与条件

### 建议：**GO（有条件）**

**依据**：DEC-354 核心载荷审查链全部 AWN/0 终态（§1.1）；四票已 commit、窗口干净（§头部）；版本面一致性/e2e/verify/六平台 adapter/one-dot-zero 等强正面全 PASS（§2.2）；FEAT-095 前置调研完成且结论自洽无失实（§3）；全部阻断项均有明确闭合路径（下述条件）。

### 条件（按链序）：

1. **C1（M-1 硬前置）载荷归置**：FEAT-095/097/FIX-443 产品代码 commit 落盘（审查证据在位：R1 AWN/095、R6 AWN/097、R0 AWN/443——pre-commit Step7 需 APPROVED 证据消费）+ 30+ review 报告与 docs/design/ 工件归置 + rowdump.txt 清理；FEAT-097 task-row 收口机录。
2. **C2（M-1 前）plan-tracker 对齐**：≥5 行滞后状态 task-row-update 机录对齐（097/443/445/446/REL-102——以 evidence/review 实况为准）。
3. **C3（M-1 前）Track B 修复**：四票执行包校准（18c/18d/18d-RB2/18f/18i）+ Check 10/30/31 靶点修复（Check 31 随 FIX-445 工件归位或链收口）。
4. **C4（M-1 前）unit tests 3F+1E 处置**：定位失败集→Developer 修复→复跑全绿；或产出事实与选项交用户 GO 终审（0.93.1 先例）。
5. **C5（M-1 前）archguard sanctioned regen**：R1/R5/R7（DEC-324/326 先例；R1 +44 LOC 归属随裁定核）。
6. **C6（定谳前置）FIX-445 链裁定**：T4 用户升级悬置——0.98 承载（授权实施+收口）vs 顺延 0.99（工件归位为披露态）；连带 FIX-443/446 的 0.98 承载确认（§8 定谳①）。
7. **C7（M-1）bump 全套一致 + CHANGELOG 0.98.0 段**（必含：载荷叙事 / FEAT-095 降级披露边界 / DEC-353/354/357 / 故障注入六项验证结果 / 3F+1E 处置披露）。
8. **C8（M-2→M-7）门禁复跑定谳 + 双审 + 组装 + tag/push**：含 28s GO 终审、故障注入六项验证落盘（DEC-330 底线不可豁免）。

### 阻断项：**有（C4 unit tests 3F+1E、C6 FIX-445 链）——均在闭合路径上，无不可解阻断。**

---

## 8. 需定谳项（Coordinator/用户裁定）

1. **FIX-443~446 族 0.98 承载 vs 顺延**（DEC-354 只重定六票未覆盖此族；FIX-445 commit-msg 大改在工作树且被 BLOCKED 链绑定）。
2. **archguard R1 +44 处置**：sanctioned regen vs 收窄（+44 归属=FEAT-095 enforcement 接线增量待核）。
3. **FEAT-097 收口机录时点**（R6 AWN/0 后 task-row 未更新——随 C1/C2 执行）。
4. **loop runtime FAIL 是否随 FIX-445 工件归位/收口自然消解**（同根 Check 31——预期是，需复跑证实）。
5. **quality-tools NOT_RUN 按 environment 事实披露即可否**。
6. **U1（DSH 宿主级 guard PoC）是否立项后续票**（调研报告 §8.2 建议，未立项）。

## 9. 需 Coordinator 复跑/回填清单（M-2 面）

1. `check-governance --summary-only`（C2/C3 后——预期 18 族与 10/30/31 消解、回归 WARN 基线；28s 待定谳）。
2. unit tests 全量复跑（C4 后——预期 3F+1E 归零或 GO 终审留痕）。
3. `archguard-ratchet`（C5 后——预期七轴 PASS）。
4. `check-injection-budget` 三 profile（M-1 后——对照 0.97.0 基线 4416/5899/6172；载荷增文若触 resident 面按 freeze line 等量收缩或 DEC-325 式重定标）。
5. `check-release --lineage-mode candidate`（M-1/M-4 两拍）+ `release-ledger`（M-5/M-6）。
6. `archive.py migrate --auto --dry-run`（M-8——本报告时点无可归档数据已实录）。
7. git 区间锚回填：载荷窗口终值待 C1 归置后重核（新增 commit 哈希入 rollback-plan 回填位）。

## 10. 边界声明（保守边界）

本报告为 M-0 评估时点快照（bump 前）：CHANGELOG/三件套 FAIL 态为预期时序态而非缺陷结论；「GO（有条件）」为 Release Analyst 建议，正式裁定权在 Coordinator/用户。24 issues 中 Check 10/30 明细与 FIX-444 R3 报告全文未展开（Track B 定位中）；上轮（EVD-1697）与本轮 check-release diff 逐面归因未展开；五平台（非 DSH）结论沿 2026-10-10 调研报告未重验；U1/U2/U6/U7 未证实面如实标注。本版不声明 official approval、marketplace approval、universal/full runtime support 或宿主级拦截能力（FEAT-095 交付物为协议级+CLI 级执法+降级披露，见 §3.1 最后一行）。
