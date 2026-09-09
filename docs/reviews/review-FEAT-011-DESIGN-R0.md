# FEAT-011 设计审查报告 — DESIGN R0

| 项 | 值 |
|---|---|
| Task | FEAT-011 — G3 扩展：写时结构看护引擎扩展至 Coordinator 直写路径 |
| Round | R0（首轮独立设计审查；双审交错占轮 Design=R0 / Code=R1，FIX-291/292 先例） |
| Reviewer | Design Reviewer Agent（`agents/design-reviewer.md` + `skills/design-review/SKILL.md`） |
| 日期 | 2026-09-09 |
| 审查对象 | 未提交工作树相对 HEAD `1d3d973` 的变更：`skills/software-project-governance/infra/verify_workflow.py`（实测 **+398/-2**；任务描述写 +399/-2，勘误见 §2 注）+ `skills/software-project-governance/infra/tests/test_triage_write_guard.py`（+314，15 新用例）；`change_triage.py` 零改动（与任务描述一致） |
| 结论 | **APPROVED_WITH_NOTES** |
| unresolved_blockers | **0** |

---

## 1. 审查对象与事实基线复跑

只读复跑（本 Reviewer 披露后执行，命令均可复查）：

| 命令 | 结果 | 与任务基线对照 |
|---|---|---|
| `git rev-parse HEAD` / `git diff HEAD --stat` | HEAD=`1d3d973`；verify_workflow.py +398/-2、tests +314，共 712 insertions / 2 deletions，仅此两文件被改 | 一致（任务描述 verify +399 系勘误：712−314=398） |
| `verify_workflow.py governance-write-guard`（活体） | **exit 1**；plan_tracker face FAIL 恰中 M1 四行 **7 issues**（L188 FIX-222 / L189 FIX-223 / L190 FIX-224 各 2 条〔重复优先级列 + 行尾空〕；L257 FIX-279 1 条〔仅行尾空〕）；evidence_log / agent_locks / execution_packets 三面 **PASS**；活体 agent-locks 干净（14 违规系前会话事故，已清理） | 一致——「恰中 M1 四行 7 issues、287 行 0 误报」 |
| `python -m pytest tests/test_triage_write_guard.py -q` | **30 passed** in 0.33s（既有 FIX-278/279 15 例 + FEAT-011 15 例） | 一致——「30/30」 |
| `verify_workflow.py check-governance` | `Result: ISSUES FOUND — 87 issue(s)`，exit 0 | 一致——「87 零新增」 |
| 全量 pytest 774/775 | **未复跑**（本审查仅复跑目标测试文件；不作为本报告任何结论的依据） | 任务基线引用处标「未验证」 |

规格来源均已读取：`.governance/plan-tracker.md` L275/L278/L279；`.governance/change-triage/FEAT-011.json`；`docs/release/version-plan-0.79.0.md` §2/§3/L37/L51/L60/L129/L135；`docs/release/audit-149-health-noise-0.79.0.md` §3 域 1 / §4 M1（L97-112）；DEC-168 / DEC-172 / DEC-177 / DEC-181；`skills/software-project-governance/SKILL.md` L119-127「自动化能力分级声明」；`core/protocol/plugin-contract.md` L100-114。

**事实红线声明**：本报告所有结论均引用上述可复查事实（文件:行号 / 命令输出）；无法验证项已显式标注「未验证」。唯一全量套件数字（774/775）未复跑，不出现在任何判定依据中。

---

## 2. 六个设计焦点逐一结论

### 焦点 1 —「写时」语义达成度（no-overclaim 视角）

**结论：「写时守卫」语义在 CLI 工件层面成立、在强制时点层面不成立；命名可保留，但 B 级宣示需修正（→F-1/F-2）。**

事实链：
- change-triage 的 G3 守卫（`_triage_write_structure_guard`，verify_workflow.py L21654）在 `cmd_change_triage` 写入路径**内联**触发、失败 exit 2——写入者无法跳过，这是真·写时强制。
- FEAT-011 的 `governance-write-guard` 是独立子命令（L23712-23720 argparse 注册 + L22151 `cmd_governance_write_guard`）；全仓 grep `governance-write-guard` 仅 8 处命中，**全部位于 verify_workflow.py 实现与测试文件**——无 git hook 接线（`infra/hooks/` 零引用）、无 SKILL.md / references/ / commands/ 协议面载明。触发完全依赖 Coordinator 自觉复跑。
- version-plan-0.79.0.md **L37 明确规划任务结构含「hooks/集成」**（「G3 扩展独立（新写时 guard 引擎 + hooks/集成 + 测试 + 设计审查）」）——工作树未交付该组件；triage record（FEAT-011.json `files`）亦未含 hooks 文件，即任务边界收窄未显式登记差异。
- 实现自身措辞无 overclaim：help 文本「Check … **after** a Coordinator direct write」、docstring「one command after a direct write」「check-only」——准确定位为「写入后复跑的检查器」。

判定：「write-guard」命名指防护对象（写路径产物，与 repo guard 相对）而非强制机制，且 CLI 措辞已守住 no-overclaim 底线——**命名成立、可保留**；但若对外以「写时守卫/写时门禁」宣示而不注明「写入者复跑触发」，将误导。替代接线方案评估见 §5。

### 焦点 2 — 能力分级声明（A 级还是 B 级）

**结论：实际交付 = B 级检查器工件（被调用即强制 exit 1）+ A 级触发（协议自觉，且协议文本尚未落盘）的混合；任务行「新增 B 级自动化能力」宣示与 plugin-contract L114 分级口径不符，MUST 修正口径或补接线登记（→F-1，P1）。**

事实链：
- SKILL.md L124 定义：**B 级 = 「CLI/脚本强制——`verify_workflow.py check-governance` 与 commit hooks 在命令/commit 时点强制」**；check-governance 之所以列 B 级，因被 commit hooks 与 SKILL「治理基础设施（自动使用）」接线到强制/协议时点。
- 本实现：CLI 强制性存在（exit 1 语义完整），但**无任何强制时点**——不挂 commit hook，SKILL.md「治理基础设施」节未收录，behavior-protocol M1.2（治理记录快速通道——Coordinator 直写 `.governance` 的规范路径）未要求复跑。「one command after a direct write」纪律仅存在于代码 docstring——连 A 级（Agent Protocol Automation）所要求的协议文本都未落盘。
- 宣示面：plan-tracker L279「新增 B 级自动化能力设计面」、version-plan L51/L60 以「新增 B 级自动化能力（L12）」作 0.79.0 MINOR 支撑项——均超过交付实际。
- plugin-contract.md L114：「README 和对外文档必须显式说明当前各项能力处于哪一级」——0.79.0 若按现口径发布宣示，即违反该禁令领域。

修正口径建议（三选一，详 §5）：(a) 补 hook 接线 → 宣示成立；(b) SKILL.md/behavior-protocol 落 MUST 复跑规则 → 「A 级触发 + B 级检查器」混合口径（且属 L37 MUST 规则新增，MINOR 支撑不塌）；(c) 仅修 plan-tracker/version-plan 措辞。

### 焦点 3 — 四面覆盖边界与活体事故谱对齐

**结论：覆盖选择与已归档事故谱精确对齐；未覆盖直写面（session-snapshot / decision-log / risk-log / REVIEW 机器行族）未显式登记为遗留（→F-4，P2）。**

事实链：
- M1 四行（audit-149 §4 L97-106：FIX-222/223/224 L188-190 + FIX-279 L257）→ face 1 两条签名精确命中（活体复跑 7 issues 全部 ⊆ 已知四行，0 误报）。
- agent-locks 14 条 Check 26 违规（前会话事故）→ face 3 整体复用 `check_agent_locks_format`（L16934，无第二 schema）。
- execution-packets 两起字段违规 → face 4 复用 `EXECUTION_PACKET_REQUIRED_FIELDS`（L12675）+ `_execution_packet_field_issues`。
- M2×6/M3×1（audit-149 同域）**正确地不属于本任务**——谓词分裂归 FIX-292（DEC-181 明确分工「FEAT-011 防再发（防新增不治存量），FIX-292 治谓词」；plan-tracker L278 FIX-293 行同口径）。分工事实清楚。
- face 2（TRIAGE/RECO 机器行族）属预防面（该域无存量事故），DEC-168 行族权威复用正确。
- **未覆盖面盘点**（工作树 diff / docstring / plan-tracker 行 / version-plan §5 均未登记）：① `session-snapshot.md`（每次收工直写）；② `decision-log.md` / `risk-log.md`（Coordinator 直写高频面）；③ **REVIEW 机器行族**——`review-record` CLI 写入的 `REVIEW-{id}` 行是第三条机器写入路径（change-triage 有写时守卫、review-record 无），且被 face 2 的 `_EVIDENCE_MACHINE_ROW_FAMILIES=("TRIAGE","RECO")` 显式排除（读时由 Check 30/30c 把关，FIX-291 已建历史形状门——但那是读时）。

### 焦点 4 — 复用与单一权威源（两处行为恒等去重）

**结论：两处去重行为恒等成立、配对二源已消灭；Check 26/18c 整体复用无隐藏 schema 二源；但「no second shape source」注释在文件级不完整（既有同字面副本残留，非本任务引入）（→F-7，P3）。**

事实链：
- `_TASK_ID_CELL_RE`（L12126）字面与 `parse_current_active_tasks` 原内联正则（现 L12210-12212）**逐字符相同**——行为恒等 ✔；守卫与解析器共用同一任务 ID cell 识别，正是 M1 面需要的恒等。
- `_execution_packet_field_issues`（L12701）为纯提取：非 dict 早退、必填字段存在性、非空字符串数组校验原样保留；`_validate_execution_packet` 委托后再叠加 task_id 匹配与 scope 语义检查（仍在 Check 18c）——写时结构面 / 读时语义面分工清晰，字段语义单源 ✔。
- face 3 整体复用 Check 26 `check_agent_locks_format`（仅包装 type 前缀与 expected 文案）✔；face 2 复用 `change_triage._TASK_ID_RE`（L108，写入器契约权威）✔。
- 残留副本（均先于本任务存在）：同字面任务 ID 正则在 verify_workflow.py **L8340**（session-context 扫描器）与 **L9470**（`get_all_completed_task_entries`）；`_TASK_ID_RE` 同型定义另存于 review_record.py L74 / task_priority.py L123。L12124 注释「no second shape source」对其**配对**准确、文件级不完整。
- face 1 用 `_governance_table_cells`、face 2 用 `_split_markdown_table_row`——两个切分函数并用**非隐藏二源**：各自跟随其域权威（解析器 cell 语义 vs Check 14/FIX-279 列计数语义），保证守卫与对应读时判定恒等。
- 依赖方向：verify_workflow →（局部）change_triage 单向；change_triage 不导入 verify_workflow（其 import 仅 json/re/datetime/pathlib/task_priority）——无循环依赖 ✔。

### 焦点 5 — 非破坏性与修复分工、读时重复报警

**结论：只检不改契约成立（字节级测试 + 活体双证）；三方修复分工清晰且有治理登记；读时重复报警有界可接受；但全量扫描姿态使守卫「生而红灯」直至 FIX-293 落地（→F-3，P2 / F-8，P3）。**

事实链：
- 非破坏性：`test_guard_writes_nothing`（test L682-699）断言运行前后 `.governance` 目标文件**字节不变**；本审查活体复跑后 `git status` 仍仅两产品文件 M——双重实证 ✔。SKIPPED（产物缺席）不失败、不可读 fail-closed FAIL——边界语义完整。
- 修复分工：守卫只检不改（docstring + FAIL 输出明示「修复动作留给写入者」）；存量 M1 数据修复归 FIX-293（plan-tracker L278 显式「FEAT-011 写时看护——防新增不治存量」）；谓词归 FIX-292（DEC-181）。三方边界在治理记录与代码 docstring 一致 ✔。
- **姿态反转**：`_triage_write_structure_guard` 明文「write guard, not repo guard——既有结构问题不阻塞入账（fail-safe 到写入者自己的产物）」（L21676-21678 + 既有测试 test_guard_scope_ignores_unrelated_preexisting_issues）；FEAT-011 守卫反之——四产物**全量**扫描、既有缺陷照报（活体：M1 四行使每次复跑必 exit 1）。取舍理由成立（Coordinator 直写无 record_id 可供写入范围化），但后果必须显式承认：FIX-293 落地前守卫无绿灯可言（born-red），且 FAIL 措辞「由写入者修复」对 M1 存量行归属失真（修复者是 FIX-293，不是当前复跑的写入者）。
- 读时重叠：face 3/4 与 Check 26/18c 同谓词——同一缺陷写时（guard exit 1）与读时（check-governance）各报一次直至修复；face 1 无读时对应（audit-149 证明 M1 行曾静默数周——真正空白填补）；face 2 与 Check 14 互补（Check 14 `evidence_col_mismatch` 域为 EVD 行族，机器族不在其扫描域，DEC-168 记载）。双报有界（表面小、guard 手动触发），defense-in-depth 可接受；注意 Check 26 读时为 WARN（L16938「informational-only」）而守卫写时 FAIL——同缺陷异级是「写时从严」的刻意姿态，与 F-3 的 born-red 叠加需在文档中说明。

### 焦点 6 — M1 签名召回/精确度边界与行集界定

**结论：两条签名对活体事故谱精确（0 误报实证）；召回边界为签名式、事故驱动的设计选择（docstring 已声明），可构造的漏报变体均不触发 M1 机制或与解析器同盲；「列右移一列」机制叙事对当前解析器不精确（→F-5/F-6，P3）。**

逐一构造（以 `parse_current_active_tasks` L12210-12227 为机制参照——title/dependency/version/closure 读取锚定 `task_idx`，priority 取行内首个 P0-P2 token，status 取 `cells[-1]`）：

| 变体 | 守卫行为 | 判定 |
|---|---|---|
| 三重优先级列 `\| **P0** \| **P0** \| **P0** \| FIX-x \|…` | `len(prio_cells)=3>1` → **命中** | 覆盖 ✔ |
| 中间空单元格（非末格） | 不命中 | **设计边界**：不触发 M1 机制（status 取 cells[-1]，中间空不致 active-forever）；与声明的两条签名域一致 |
| 重复 P3~P9 优先级列 | 不命中（`_normalize_priority` L12064-12066 词表仅 {P0,P1,P2}） | **与解析器同盲**（词表权威单源）——一致盲区，非新增风险 |
| 任务 ID cell 格式破坏（如 `FIX -222` / 带尾注） | 行被跳过（无 standalone task-ID cell） | **与解析器同盲**（解析器同样读不到该行）——一致盲区 |
| 非任务表节的相似行 | 行集 = **全文件**任何含 standalone task-ID cell 的表格行（无节边界限定），命中同两条签名则报 | 比「任务表节」宽是有意为之（M1 四行中 3.5 行活体位于已完成任务节 L188-190/L257）；活体 287 行 0 误报为实证精确度 |
| face 2 单行族破列 | 该行即行族标准 → 0 报 | DEC-168 已接受的 P3 理论盲区在全文件扩展下的延续；镜像变体：首行破列 → 后续合法行全部误报（fail-closed 方向） |

「任务相对列整体右移一列」的 detail 叙事（face 1 issue 文案）：对当前解析器不精确——任务 ID 前多出的单元格不移动 task_idx 相对读取（FIX-222 的实际机制伤害来自行尾空单元格，audit-149 归因 M1=`cells[-1]=""`）。签名的形状不变量（优先级恰一列、居任务 ID 前）本身成立（绝对列序消费者/表渲染会错位），是文案精度问题而非签名缺陷。

---

## 3. 发现清单（P0~P3）

> 无 P0。每条：级别｜位置｜事实｜影响｜建议。

**F-1（P1）能力分级宣示与交付不符——「B 级」缺强制时点接线**
- 位置：plan-tracker.md L279；version-plan-0.79.0.md L37/L51/L60；对照实现 verify_workflow.py L23712-23720（仅子命令注册）、SKILL.md L119-127、plugin-contract.md L114。
- 事实：B 级定义要求命令/commit 时点强制（check-governance 有 hooks + SKILL 基础设施节接线；governance-write-guard 全仓零接线、零协议载明——「复跑纪律」仅在代码 docstring）。version-plan L37 规划的「hooks/集成」组件未交付且收窄未登记。
- 影响：0.79.0 MINOR 支撑项（L12「新增 B 级自动化能力」）与任务行宣示超过交付实际；发布宣示若照抄即触 plugin-contract L114 禁令领域（no-overclaim）；用户误以为直写路径已有强制看护。
- 建议：0.79.0 收尾（M-3 双审汇总/发布宣示）前 MUST 三选一：(a) hook 接线；(b) SKILL.md「治理基础设施」节 + behavior-protocol M1.2 落「直写后 MUST 复跑」规则（属 L37 MUST 新增，MINOR 支撑面保持）；(c) 修正 plan-tracker L279 与 version-plan 措辞为「A 级触发 + B 级检查器（混合）」。最小充分动作 = (b) 或 (c)。

**F-2（P2）「写时守卫」命名/对外措辞的误导风险**
- 位置：verify_workflow.py L22151-22214（`cmd_governance_write_guard` help/docstring）；对外宣示面同 F-1。
- 事实：CLI 措辞准确（"Check … **after** a direct write" / "check-only"）；但子命令名 `governance-write-guard` 与 change-triage 内联写时守卫共享「write guard」词汇，语义不同（后者写入者不可跳过）。
- 影响：后续贡献者/用户可能误判强制时点已存在。
- 建议：命名保留（防护对象语义成立）；对外文档（README/CHANGELOG 0.79.0 条目）措辞用「写入后复跑的结构检查器（写入者触发）」，禁用无限定语的「写时强制」。

**F-3（P2）全量扫描姿态 → 守卫生而红灯（born-red）直至 FIX-293**
- 位置：`check_governance_write_shapes` docstring（whole-file extension 声明）；FAIL 输出文案（「由写入者复跑/修复」）；对照 `_triage_write_structure_guard` L21676-21678 的 write-scoped 契约。
- 事实：活体每次复跑 exit 1（M1 存量 4 行 7 issues）；FIX-293 未落地前无绿灯；remediation 文案对存量行归属失真（修复者 = FIX-293）。
- 影响：写入者对自己刚写的行拿不到信号；告警疲劳风险（AUDIT-149 治噪主题的反面）。
- 建议：(i) 0.79.0 窗口内安排 FIX-293 先于/紧随 FEAT-011 合并，压缩 born-red 窗口（plan-tracker L278 已有分工，补时序约定即可）；(ii) FAIL 输出或 docs 注明「存量缺陷见 FIX-293」的归属区分；(iii) 接受全量姿态（无 record_id 可范围化，取舍成立）但将该取舍记入设计说明。

**F-4（P2）未覆盖 Coordinator 直写面未显式登记**
- 位置：`_EVIDENCE_MACHINE_ROW_FAMILIES`（仅 TRIAGE/RECO）；守卫 docstring 四产物清单；plan-tracker L279 / version-plan §5 无遗留登记。
- 事实：未覆盖面 = session-snapshot.md、decision-log.md、risk-log.md、**REVIEW 机器行族**（review-record CLI 写入——第三条机器写入路径，读时 Check 30/30c 把关但无写时校验）。
- 影响：覆盖边界停留在代码隐式状态；REVIEW 行族作为机器写入却排除在机器族守卫外，与「机器写入 MUST 有写时结构看护」的 G3 叙事有张力。
- 建议：在 plan-tracker FEAT-011 行注记或后续候选登记四面遗留；REVIEW 行族纳入 face 2 作为首选后续候选（复用同一行族列数 + ID 格式机制，增量小）。

**F-5（P3）签名召回边界（焦点 6 表列全部变体）**
- 位置：`_plan_tracker_task_row_issues` / `_evidence_machine_row_issues`。
- 事实：中间空单元格不检（不触发 M1 机制）；P3-P9 优先级与 ID 格式破坏与解析器同盲；face 2 单行族盲区（DEC-168 接受的延续）。
- 影响：有限——均为一致盲区或非 M1 谱系。
- 建议：接受（docstring 已声明签名式边界）；可选：face 2 对「族内仅一行、无标准可校验」输出 INFO 级提示。

**F-6（P3）重复优先级签名「任务相对列整体右移一列」机制叙事不精确**
- 位置：face 1 issue detail 文案（L21792-21800 区域）。
- 事实：解析器读取锚定 task_idx，任务 ID 前的重复列不移动相对读取；FIX-222 的机制伤害来自行尾空单元格（audit-149 L97 归因）。
- 影响：remediation 叙事可能引导写入者误判修复方向（应删重复列——按形状不变量修正是对的，但理由表述失真）。
- 建议：文案改为「与声明列形不符（优先级恰一列且居任务 ID 前）」。

**F-7（P3）「no second shape source」注释文件级不完整**
- 位置：L12122-12126 注释；对照 L8340 / L9470 既有同字面副本；review_record.py L74 / task_priority.py L123 同型 `_TASK_ID_RE`。
- 事实：配对（守卫↔parse_current_active_tasks）二源已消灭 ✔；文件内另有 2 处同字面正则（先于本任务存在，属其它域扫描器）。
- 影响：极小（一致性/可维护性层面）。
- 建议：后续候选：L8340/L9470 一并切换 `_TASK_ID_CELL_RE`（纯重构、行为恒等）；不阻塞。

**F-8（P3）与读时检查的重复报警（face 3/4 ↔ Check 26/18c）**
- 位置：face 3/4 复用谓词；Check 26 读时 WARN vs 守卫 FAIL。
- 事实/影响/建议：见焦点 5——有界 defense-in-depth，接受；建议在守卫文档中说明「同一缺陷写时/读时各报一次直至修复」的预期，避免被当噪声关停。

---

## 4. 蓝军挑战记录（角色硬门槛 ≥3 条）

| ID | 挑战 | 结论 |
|---|---|---|
| BC-1 | Coordinator 忘记/跳过复跑（最可能失效路径）——守卫还剩什么？ | 零防护——正是 F-1 核心；现状等价于「买了灭火器但没装在墙上」。最小补救 = 协议落盘（F-1 建议 b） |
| BC-2 | evidence-log 首个 TRIAGE 行被历史编辑破坏 → face 2 行族标准被污染 | 后续合法行全部误报（fail-closed 方向、可辨认——mismatch 报的是合法行但标准行号可查）；破行自身免检（DEC-168 已接受盲区延续）。可接受，F-5 登记边界 |
| BC-3 | `.governance` 产物不可读（编码/权限） | 守卫 fail-closed FAIL（plan_tracker_unreadable / evidence_log_unreadable 路径），不静默——✔ 已覆盖 |
| BC-4 | 大文件性能 | face 1/2 逐行 O(n) 单遍，活体（plan-tracker ~500 行级）瞬时完成——非问题 |

依赖图分析：verify_workflow →（函数内局部）change_triage 单向；无循环依赖（角色硬门槛 ✔）。

---

## 5. 替代方案与后续候选评估（验收标准 3）

| 候选 | 评估 | 建议处置 |
|---|---|---|
| **hook 接线**（pre-commit / 治理 hook 链内调 governance-write-guard） | 让 commit 时点强制——真正 B 级化；但 `.governance` 直写不必然伴随 commit（会话中途多次写、commit 在收尾），hook 只是近似时点；且 hooks 修改涉治理 hook 链版本面（bootstrap 模板同步），超出 FEAT-011 边界 | 列后续候选（0.79.0 窗口内可做则做；至少登记） |
| **协议落盘**（SKILL.md 治理基础设施节 + behavior-protocol M1.2「直写后 MUST 复跑」） | 最小充分动作：触发纪律从 docstring 升为 MUST 规则；属 L37 面（version-plan L52 已预留该论证路径，MINOR 支撑不塌）；口径修正为「A 级触发 + B 级检查器」 | **推荐**——FEAT-011 收尾或紧随任务承接 |
| **口径修正**（plan-tracker L279 + version-plan §2/§5 措辞） | 治理记录快速通道即可完成；不改行为 | 与上二选一 MUST 执行（F-1） |
| **REVIEW 机器行族纳入 face 2** | 补第三条机器写入路径的写时面；机制复用（行族列数 + ID 格式），增量小；需先确认 REVIEW 行族列数的行族标准现状（live 行族是否已统一） | 后续候选首选（F-4） |
| **session-snapshot / decision-log / risk-log 结构面** | 事故谱中无该域存量事故（audit-149 未归因于此）；优先级低于 REVIEW 行族 | 后续候选登记即可 |
| **L8340/L9470 正则归一** | 纯重构、行为恒等 | 后续候选（低优先级） |

---

## 6. 硬门槛裁决（角色定义 + 派发硬门槛）

| 门槛 | 结果 |
|---|---|
| 与 FIX-278 G3 架构一致性 | ✔ 扩展非重写：`_triage_write_structure_guard`/`cmd_change_triage` 零改动，既有 15 例全过；fail-closed/只检不改纪律延续 |
| 与 DEC-168 列契约一致性 | ✔ face 2 标准取行族首行（DEC-168 行族权威），EVD 手工族显式排除并保留 Check 14 WARN 域 |
| 与 plugin-contract 自动化分级一致性 | ✖ **宣示面不符（F-1，P1）**——实现工件自洽，宣示需修正；不构成代码级阻塞 |
| 与 FEAT-011 任务边界一致性 | ✔ 实改 ⊆ triage files 声明（change_triage.py 声明未改，如实）；「修改文件」声明面为超集，不违规 |
| 每条发现带级别+事实依据 | ✔ §3 八条 |
| 事实依据红线 | ✔ 全部引用文件:行号/命令输出；774/775 未复跑已标「未验证」 |

---

## 7. 结论

**APPROVED_WITH_NOTES**（unresolved_blockers=0）

- 四面守卫引擎设计健全：事故谱对齐精确（活体恰中 M1 四行、0 误报）、权威源复用到位（无新增第二形状定义）、只检不改契约有字节级测试与活体双证、非破坏性与修复分工清晰、exit 语义完整、30/30 测试复现。
- 保留备注（非阻塞，但 F-1 的口径/接线义务 MUST 在 0.79.0 发布宣示前完成）：**F-1（P1）分级宣示修正或接线登记**；F-2/F-3/F-4（P2）对外措辞、born-red 时序、未覆盖面登记；F-5~F-8（P3）边界与文案精度。
- 复审触发条件：若 Coordinator 选择以「补 hook 接线」或「协议落盘」承接 F-1，该承接任务自身按其面走各自审查链；本 R0 结论对当前工作树变更成立。

— Design Reviewer Agent，2026-09-09
