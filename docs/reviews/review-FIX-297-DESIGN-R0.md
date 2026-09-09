# FIX-297 设计审查报告 — DESIGN R0

| 项 | 值 |
|---|---|
| Task | FIX-297 — FEAT-011 Design R0 P1 F-1 处置（方案 2）：MUST 复跑规则落盘 + 宣示口径修正 |
| Round | R0（首轮独立设计审查） |
| Reviewer | Design Reviewer Agent（`agents/design-reviewer.md` + `skills/design-review/SKILL.md`） |
| 日期 | 2026-09-09 |
| 审查对象 | 未提交工作树相对 HEAD `e90ed17` 的**本任务两文件**：`references/behavior-protocol.md` **+1**（L75）/ `SKILL.md` **+2**（L116 / L126）——纯增量 3 行零删除。并行在途 FIX-294（`infra/verify_workflow.py` +205 / `infra/tests/test_verify_workflow.py` +270，实测 stat 口径）不在本轮范围，仅作测试运行环境的如实披露背景 |
| 结论 | **APPROVED_WITH_NOTES** |
| unresolved_blockers | **0** |

---

## 1. 审查对象与事实基线复跑

只读复跑（本 Reviewer 披露后执行，命令均可复查）：

| 命令 | 结果 | 与任务基线对照 |
|---|---|---|
| `git rev-parse HEAD` / `git diff HEAD --stat` | HEAD=`e90ed17`；4 文件 477 insertions / 1 deletion——本任务面 = SKILL.md +2、behavior-protocol.md +1 | 一致——「纯增量 3 行零删除」逐 hunk 核实（仅两个 hunk，frontmatter 无改动） |
| `verify_workflow.py check-injection-contract` | **PASSED** — Files checked: 4; anchors: 28 | 一致——「28 锚点含 SKILL.md」 |
| `verify_workflow.py check-manifest-consistency` | **PASS**（Canonical 611 / Actual 664 一致） | 一致 |
| `verify_workflow.py check-cross-references` | References extracted: **659**；无 dangling / 无 deprecated / 无 circular——**PASS** | 一致——「references 657→659 新增 2 条均解析」（659 终值复现；657 基线为 Developer 时点值，未独立复现时点数据，不作为判定依据） |
| `python -m unittest discover … -p "test_verify_workflow.py"`（仓库根 CWD） | **Ran 788 / failures=1**（唯一失败 `LoopRuntimeClaimAdapterTests.test_claim_command_emits_complete_pass_report`——FEAT-011 CODE R0/R2 双重定性的 subprocess 型环境预算既有项） | **部分一致**——「failures=1 既有定性维持」精确复现 ✔；「Ran 775」实测为 **788**（+13 = FIX-294 在途新增测试方法；Developer 引用了 FIX-294 合入前的旧基数）→ F-5 |
| `python -m unittest discover … -p "test_*.py"` 全量（2171 tests / 415s） | **Ran 2171 / failures=30 / skipped=1**。逐条定性：pre_commit_review_evidence ×24（WSL 基线，与 FIX-291 CODE R2 记载「×24〔WSL 基线〕」精确吻合）+ cleanup manifest ×1 + loop_runtime_claims/perf ×2（计时/清单存量类）+ LoopRuntimeClaimAdapter ×1（上述既有定性）+ `GovernanceWriteGuardPlanTrackerTests.test_live_plan_tracker_flags_only_known_m1_rows` ×1（FEAT-011 活体断言「恰中 M1 四行」在 **FIX-293 数据修复后已知过期**——plan-tracker L279 登记的 FEAT-011 遗留 F-3 测试补强项，与本任务无因果）+ `Fix294Check36ArchiveResolutionTests` ×1（**FIX-294 在途测试**——范围外） | 全量未包含在 Developer 基线声明内（其口径为单文件）；**30 failures 零归因本任务**——本任务改动为两个协议 Markdown 纯文本增量，失败集中域（hook 正则 / cleanup manifest / loop 计时 / 活体治理数据断言）无一消费这两处文本形状，且 injection 28 锚点 + cross-references 659 双 PASS 直接证明结构面无损 |

规格来源均已读取：`docs/reviews/review-FEAT-011-DESIGN-R0.md`（F-1 原文 / 三选一 / §5 推荐）；`.governance/change-triage/FIX-297.json`；`skills/software-project-governance/SKILL.md` L112-129（判定规则 + 自动化能力分级声明）；`skills/software-project-governance/core/protocol/plugin-contract.md` L50-114（A/B/C 分级定义 + L114 禁令）；`references/behavior-protocol.md` M1.1/M1.2 全节；守卫实现 `verify_workflow.py` L22357-22415；`.governance/plan-tracker.md` L279；`docs/release/version-plan-0.79.0.md` L37/L51/L52/L60。

**事实红线声明**：本报告所有结论均引用上述可复查事实（文件:行号 / 命令输出）；未验证项已显式标注（§1 表格内 657 时点基线；§4 焦点 5 中 Coordinator 建议措辞的文本载体——execution-packets 无 FIX-297 短包（P2 无强制），派发 prompt 即措辞来源）。

---

## 2. 五个审查焦点逐一结论

### 焦点 1 — F-1 诉求是否被方案 2 完整承接（宣示失真张力是否消除）

**结论：完整承接。方案 2 的核心义务（触发纪律从代码 docstring 升为 MUST 协议规则 + 口径修正）在产品代码/协议面全部落盘；宣示失真张力在协议文本层面消除。治理记录面四处宣示的修正属 FIX-297 标题承诺的剩余半边，尚未执行（→F-1 发现，P2）。**

事实链：
- F-1（FEAT-011 R0 §3）的诉求结构 = (i) 「复跑纪律」从 docstring 升为协议文本（A 级触发依据）；(ii) 宣示口径与 plugin-contract 分级定义对齐；建议方案 2（§5「协议落盘」——最小充分动作）。
- (i) 落盘：M1.2 L75 全文——触发主体（Coordinator）+ 触发条件（直写四类产物后）+ 动作（命令全路径）+ FAIL 处置（修复→复跑至 PASS）+ fail-closed（CLI 不可用不得降级）五要素齐备；位于「快速通道纪律」列表——正是 Coordinator 直写后的规范阅读路径。
- (ii) 口径对齐：SKILL L126「**governance-write-guard（FEAT-011 / FIX-297）= B 级检查器工件 + A 级协议触发**……对外宣示不得写成纯 B 级时点强制」——与 plugin-contract 分级框架精确相容：A 级定义（plugin-contract L54-60「agent 按协议规则执行……没有外部机制阻止 agent 跳过」）承载触发纪律；B 级定义（L71-77「可执行脚本/命令对关键治理动作进行强制验证」）承载工件强制性（调用即 exit 1）。「B 级检查器工件 + A 级触发」两级各取所需，无越级宣示；L114「README 和对外文档必须显式说明当前各项能力处于哪一级」的禁令由此条**模范执行**（显式分级 + 禁令复述双保险）。
- 双向指针对称：M1.2 L75 尾「分级口径见 SKILL.md『自动化能力分级声明』」↔ SKILL L126「复跑时点由 references/behavior-protocol.md M1.2『直写后 MUST 复跑』协议纪律约束」；check-cross-references 无 circular PASS。
- SKILL 面落点与 F-1 建议 (b) 字面（「SKILL.md『治理基础设施』节」）不同——实际落在「判定规则」节（L116）+「分级声明」节（L126）。判定为**等价且更优**：「治理基础设施（自动使用）」节标题自宣 B 级自动使用（L293 节标题内联「自动化分级：B 级——命令/commit 时点强制」标注），若将该守卫收入该节将重演 F-1 要消除的纯 B 级暗示；分级声明节才是该混合能力级别的正确声明位（→F-4 备注记录，不构成缺口）。
- MINOR 论证自洽性加强：version-plan L52 预留的 L37 论证路径（「若 G3 扩展涉及 SKILL/behavior-protocol 契约新增、或判定面变更伴随 MUST 规则落盘 → L37 面直接支撑」）因本交付**由假设变为事实**——F-1 方案 2 预判「MINOR 支撑不塌」（§5「属 L37 MUST 规则新增，MINOR 支撑面保持」）兑现。

### 焦点 2 — 单源投影纪律（SKILL 最短引用 vs behavior-protocol 权威全文）

**结论：纪律成立。复跑规则权威全文唯一在 M1.2；SKILL L116 为语义恒等最短投影 + 显式权威指针；分级口径单点声明于 SKILL L126（定义权威在 plugin-contract）；无全文重复、无隐藏第二源。轻度双处陈述的同步义务已登记（→F-3，P3）。**

事实链：
- 权威全文唯一性：M1.2 L75 是唯一含四类产物枚举 + FAIL 域括号 + fail-closed 措辞的全文；SKILL L116 投影仅保留触发义务与 FAIL 处置缩写——「FAIL 时修复数据后复跑至 PASS」与 L75「写入者 MUST 按输出行号与期望列形修复数据后复跑至 PASS」语义恒等（缩写省略「按输出行号与期望列形」细节，方向与强度无损）。
- 指针显式性：L116 括号「权威规则见 `references/behavior-protocol.md` M1.2」；指针目标可解析（SKILL.md L72/L252/L284 既有引用链 + cross-references PASS）。
- 分级口径单源：A/B/C 定义权威 = plugin-contract L50-104；SKILL L120-129 分级声明节自述「按 plugin-contract.md 三级划分」；governance-write-guard 的具体分级声明仅单点出现于 L126；M1.2 L75 仅概要引用 + 指针——无第二定义源。
- 重复面盘点：M1.2 L75 概要句「B 级检查器工件 + A 级触发（协议纪律）」与 SKILL L126 声明句各自独立陈述同一事实（非指针引用）——当前措辞逐字一致；这是有意的双向可发现性设计，代价是 hook 接线落地日需同步修改两处（→F-3）。

### 焦点 3 — MUST 措辞强度与可执行性（触发面 / FAIL 处置 / fail-closed 闭环）

**结论：三段全部闭环。四类产物枚举与守卫四面逐一对应；FAIL 处置与 CLI remediation 输出措辞对应；fail-closed 含显式降级禁令。唯一精度瑕疵：触发枚举第二类「evidence-log 追加行」宽于守卫 face 2 实际覆盖面（→F-2，P3，过度触发方向、无害）。**

事实链：
- 四类产物 ↔ 守卫四面（verify_workflow.py L22380-22387）逐一对照：plan-tracker 任务行 ↔ `plan_tracker`（M1 签名）✔；evidence-log 追加行 ↔ `evidence_log`（TRIAGE/RECO 机器行族）✔（粒度差见下）；agent-locks.json ↔ `agent_locks`（Check 26）✔；execution-packets.json ↔ `execution_packets`（Check 18c 字段表）✔。
- FAIL 域括号「（M1 签名 / DEC-168 行族列数与 ID 格式 / Check 26 / Check 18c）」与四面 label 恒等 ✔。
- FAIL 处置闭环：协议「写入者 MUST 按输出行号与期望列形修复数据后复跑至 PASS」↔ CLI 实现 L22410-22413「按上方行号与期望列形修复后由写入者复跑本命令」+ exit 1——协议与工件措辞互相印证 ✔。
- fail-closed 闭环：「CLI 不可用时 fail-closed——修复环境后重试，**不得降级跳过**」——降级禁令显式，与仓库 fail-closed 传统（M0/resolve_entry 等）姿态一致 ✔。「守卫只检不改、零 `.governance` 写入」与实现契约（L22368-22369 docstring + `test_guard_writes_nothing` 字节级断言，FEAT-011 R2 已验）一致 ✔。
- 命令路径可执行性：`python skills/software-project-governance/infra/verify_workflow.py governance-write-guard` 全路径与 behavior-protocol 既有 6 处命令引用惯例（L182/L221/L470/L534/L754/L774 同形式）完全一致 ✔。
- 条目风格：与相邻 L74「REVIEW 行豁免收窄（FIX-260/REQ-107）」同构（**粗体标题（任务 ID）**：正文）——M1.2 列表风格无漂移 ✔。
- 粒度差（F-2）：触发枚举「evidence-log 追加行」字面覆盖一切追加行；守卫 face 2 实际只检 TRIAGE/RECO 机器行族（`_EVIDENCE_MACHINE_ROW_FAMILIES=("TRIAGE","RECO")`，EVD 手工行属 Check 14 读时域）。后果方向：Coordinator 直写 EVD 行后也会复跑（过度触发）——守卫不检的行不会 FAIL，无害；但读者可能误以为 EVD 手工追加行已获写时看护（覆盖高估）。FAIL 域括号已精确限定「DEC-168 行族列数与 ID 格式」，张力有限。

### 焦点 4 — no-overclaim（hook/时点强制暗示残留）

**结论：零残留。两处文本均显式否认接线、定位 hook 为后续候选，且 SKILL L126 附对外宣示禁令。**

事实链：
- M1.2 L75：「但**无 hook/commit 时点系统接线**——复跑时点由本条 MUST 约束，**hook 接线为后续候选**」——显式否认 + 未来工作定位 ✔。
- SKILL L126：「但**无 hook/commit 时点接线**……（hook 接线为后续候选）；**对外宣示不得写成纯 B 级时点强制**」——否认 + 禁令双保险 ✔。
- 全 diff 逐字检查（本任务 3 行新增）：「强制」一词两处均绑定「命令被调用即强制 / FAIL 退出码 1」的工件级语境；无「自动」「写时门禁」「commit 时点强制」无限定语字样 ✔。
- 与 FEAT-011 R0 F-2 建议（对外措辞用「写入后复跑的结构检查器（写入者触发）」）方向一致——本交付协议文本即该措辞的规范化落盘；M1.2 标题「直写后 MUST 复跑」措辞精确（「复跑」而非「写时强制」）✔。

### 焦点 5 — Coordinator 侧宣示修正措辞（plan-tracker L279 / version-plan L37/L51/L60）与交付文本的一致性

**结论：修正方向与交付文本完全一致（统一为「B 级检查器工件 + A 级协议触发」+ hooks 后续候选标注后无张力）；但四处现存宣示均仍是旧口径——不一致是预期中的剩余义务而非已完成的修正。该修正属 FIX-297 标题承诺（「plan-tracker/version-plan 宣示口径修正为『B 级检查器工件 + A 级触发』」——triage title 原文）的组成部分，任务完成宣告前 MUST 由 Coordinator 治理记录快速通道执行（→F-1，P2）。不阻塞本审查对象（两产品文件）通过。**

事实链（四处现状逐一，均于本审查时点读取）：
- `plan-tracker.md` L279（FEAT-011 行处理列）：仍含「产品代码（Developer → Code Reviewer + Design Reviewer——**新增 B 级自动化能力设计面**）」——纯 B 级暗示未加限定；完成列「新子命令 governance-write-guard（四面守卫，只检不改，exit 0/1/SKIP）」为能力描述（无 overclaim），并已登记「F-1 宣示口径（→FIX-297）」转移标记。
- `version-plan-0.79.0.md` L37：任务结构仍为「G3 扩展独立（新写时 guard 引擎 + **hooks/集成** + 测试 + 设计审查）」——hooks/集成仍在窗口任务结构内且无后续候选标注，与交付文本「hook 接线为后续候选」不一致（FEAT-011 R0 F-1 已指出「收窄未显式登记」——本轮仍未登记）。
- `version-plan-0.79.0.md` L51（L12 判据行）：「G3 扩展 = 写时门禁**新增 B 级自动化能力**（扩展至 Coordinator 直写路径）」——纯 B 级宣示原样。
- `version-plan-0.79.0.md` L60（§2.2 判据表首行）：「新增 B/C 级自动化能力（L12）| G3 扩展……新 B 级自动化能力（L12/L37 面）」——同上原样。
- 一致性判定（修正后推演）：四处统一修正为「B 级检查器工件 + A 级协议触发（混合口径）」并在 L37 将「hooks/集成」标注为后续候选后，与 M1.2 L75 / SKILL L126 定义的口径**逐字一致**——修正闭合后 FEAT-011 R0 F-1 的宣示失真张力全面消除，plugin-contract L114 禁令领域退出。version-plan L52 的 L37 论证（「SKILL/behavior-protocol 契约新增、MUST 规则落盘 → MINOR」）随 FIX-297 落盘由预留路径变为既成事实——MINOR 论证加强，修正不削弱发布论证。
- 修正通道合法性：plan-tracker（M1.2 快速通道路径）与 docs/release/version-plan（SKILL「治理记录」表 `docs/**`）均属 Coordinator 直写面——与派发 prompt「你只需判定其一致性，不必要求实现」边界一致。

---

## 3. 发现清单（P0~P3）

> 无 P0、无 P1。每条：级别｜位置｜事实｜影响｜建议。

**F-1（P2）治理记录面宣示修正尚未执行——FIX-297 标题承诺的剩余半边**
- 位置：`.governance/plan-tracker.md` L279；`docs/release/version-plan-0.79.0.md` L37/L51/L60；对照 triage title（FIX-297.json L4「+ plan-tracker/version-plan 宣示口径修正为『B 级检查器工件 + A 级触发』」）。
- 事实：四处现存宣示仍为纯 B 级旧口径 / hooks 在窗结构（§2 焦点 5 逐行引用）；产品代码面（本审查对象）已交付准确口径，但治理记录面修正未动。
- 影响：FIX-297 若在修正前宣告完成，标题承诺（宣示口径修正）只兑现一半；FEAT-011 R0 F-1 的「0.79.0 发布宣示前 MUST」义务在 M-3 双审汇总/发布宣示面仍处打开状态。
- 建议：Coordinator 以治理记录快速通道执行四处修正（plan-tracker L279 处理列加限定；version-plan L51/L60 改混合口径；L37 hooks/集成标注后续候选），随后按 M1.2 新条目复跑 `governance-write-guard`（修正即新条目纪律的首次自我适用——推荐象征性闭环）。

**F-2（P3）M1.2 触发枚举「evidence-log 追加行」宽于守卫 face 2 实际覆盖**
- 位置：`references/behavior-protocol.md` L75 首句括号；对照 `verify_workflow.py` L22383-22384（face 2 label「机器行族 TRIAGE/RECO」）与 `_EVIDENCE_MACHINE_ROW_FAMILIES`。
- 事实：触发枚举字面覆盖一切 evidence-log 追加行；守卫只检 TRIAGE/RECO 机器行族（EVD 手工行属 Check 14 读时域）。FAIL 域括号（L75 中段）已精确限定，张力仅在触发描述粒度。
- 影响：过度触发方向无害（不检的行不会 FAIL）；但读者可能高估写时覆盖面（误以为 EVD 手工行有写时看护）。
- 建议：后续候选——L75「evidence-log 追加行」补「（机器行族 TRIAGE/RECO）」限定，或接受现状（FAIL 域已精确）。不阻塞。

**F-3（P3）分级口径双处独立陈述的同步修改面（hook 接线落地日）**
- 位置：M1.2 L75 尾句 ↔ SKILL L126。
- 事实：同一分级事实两处各自独立成句（非指针）；当前逐字一致；hook 接线落地时两处 + 治理记录多处需同步翻转口径。
- 影响：未来漂移面 = 2 处产品文本；不同步将重现宣示失真。
- 建议：hook 接线候选任务 triage 时把「M1.2 L75 + SKILL L126 + 治理记录宣示面」同步修改清单化为验收项。

**F-4（P3，记录性）F-1 建议 (b) 的 SKILL 面字面落点与实际落点差异**
- 位置：FEAT-011 R0 §3 F-1 建议 (b)「SKILL.md『治理基础设施』节」；实际落点 = SKILL L116（判定规则节）+ L126（分级声明节）；`治理基础设施（自动使用）` 节（L293-299）未收录 governance-write-guard。
- 事实：落点偏移存在；「治理基础设施」节标题自带 B 级自动使用标注，收录该守卫将与其 A 级触发事实冲突。
- 影响：无功能影响；仅 F-1 承接轨迹的完备性记录。
- 建议：接受实际落点（等价且更符合 no-overclaim）；无需回补「治理基础设施」节收录。

**F-5（P3）Developer 基线数字「Ran 775」实测为 788——旧基数引用**
- 位置：任务上下文 Developer 报告「unittest Ran 775 failures=1」；实测（仓库根 CWD，单文件 discover）Ran **788** / failures=1。
- 事实：+13 恰为 FIX-294 在途新增测试方法（test_verify_workflow.py +270 行）；775 为 FIX-294 写入前基数；failures=1（LoopRuntimeClaim 既有定性）精确复现。全量 2171/30 经逐条定性零归因本任务（§1 表）。
- 影响：极小——数字口径瑕疵，方向与结论（既有定性维持、零回归）不受影响。
- 建议：Developer 后续报告区分「FIX-294 在途前/后基数」或在含并行在途改动的工作树上重跑后引用实测值。

---

## 4. 蓝军挑战记录（角色硬门槛 ≥3 条）

| ID | 挑战 | 结论 |
|---|---|---|
| BC-1 | FIX-293 修复后守卫已 PASS——MUST 复跑是否沦为空转纪律？ | 非空转：纪律价值在**防新增**（写入者新错误行立即被捕获，M1 四行静默数周的事故谱正是缺此纪律）；单命令秒级成本；「防新增不治存量」定位（plan-tracker L278）自洽 |
| BC-2 | Agent 只加载 SKILL.md 不读 behavior-protocol——MUST 规则对谁可见？ | 双层可见性成立：SKILL L116 位于「判定规则」节（Coordinator 判定直写合法性时必经）+ M1.2 L75 权威全文指针可达；check-injection-contract 28 锚点含两文件证明注入面完整 |
| BC-3 | 读者误信 EVID 手工行已获写时看护（覆盖高估） | F-2 登记——过度触发无害方向 + FAIL 域括号已精确限定；措辞补限定为后续候选 |
| BC-4 | 协议规则「A 级触发」依赖 agent 自觉——与被替换的 docstring 纪律有何本质区别？ | 区别在文本层级与可见性：docstring 仅代码读者可见、无 MUST 强度；M1.2 是行为协议 MUST（违反 = 工作流执行失败，M0 语义）+ 入口 SKILL 投影 + 审查/证据链可援引——这正是 F-1 方案 2 的全部诉求，A 级固有上限（plugin-contract L60「不保证每次都做」）已由分级声明如实披露，无 overclaim |
| BC-5 | hook 接线落地日口径翻转遗漏 | F-3 已登记同步修改清单义务；当前「后续候选」定位两处一致 |

依赖图分析：本任务为纯文档增量，无代码依赖引入；M1.2 L75 ↔ SKILL L126 双向引用经 check-cross-references 无 circular PASS；无循环依赖（角色硬门槛 ✔）。

---

## 5. 硬门槛裁决（角色定义 + 派发硬门槛）

| 门槛 | 结果 |
|---|---|
| 与 FEAT-011 Design R0 F-1 原文一致性 | ✔ 方案 2 核心义务全部落盘（SKILL 面落点差异 →F-4 记录，等价更优） |
| 与 SKILL.md「自动化能力分级声明」A/B/C 定义一致性 | ✔ 混合口径与 plugin-contract L54-77 及 SKILL L124/L125 既有定义相容，无越级 |
| 与 M1.2 既有条目风格一致性 | ✔ 与 L74 同构（粗体标题 + 任务 ID + 正文）；命令路径与既有 6 处惯例一致 |
| 每条发现带级别 + 位置 + 事实 + 影响 + 建议 | ✔ §3 五条 |
| 事实依据红线 | ✔ 全部引用文件:行号 / 命令输出；未验证项显式标注（657 时点基线 / 焦点 5 措辞载体说明） |

---

## 6. 结论

**APPROVED_WITH_NOTES**（unresolved_blockers=0）

- 两目标文件的设计质量成立：F-1 方案 2 义务完整落盘且与 FEAT-011 R0 判定逐字吻合；单源投影纪律成立（权威全文唯一 + 最短投影 + 双向指针）；MUST 措辞五要素闭环且与守卫工件实现互证；no-overclaim 零残留（显式否认接线 + 对外宣示禁令）；MINOR 论证随 L37 面落盘事实成立而加强。
- 保留备注（非阻塞）：**F-1（P2）治理记录面四处宣示修正 MUST 在 FIX-297 宣告完成前由 Coordinator 快速通道执行**（任务标题承诺的剩余半边；0.79.0 发布宣示前的 F-1 终态义务）；F-2/F-3/F-4/F-5（P3）措辞精度、同步修改面、落点轨迹、基线数字口径。
- 复审触发条件：本 R0 结论对当前工作树两目标文件变更成立；治理记录面修正（F-1）属快速通道治理记录操作，不构成产品代码返工——修正后无需对本两文件重审；若修正中引入新的产品代码变更则按各自面另走审查链。

— Design Reviewer Agent，2026-09-09
