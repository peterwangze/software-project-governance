# AUDIT-148 — V1 深化：verify 告警洪流的样本外取证与跨项目验证

- **任务**: AUDIT-148（V1 闭环）——把「verify 告警洪流」取证扩展到样本外会话并跨项目（router / android\tv / reasoning-level）验证
- **分析者**: Analyst Agent（沿用 AUDIT-147 上下文）
- **分析日期**: 2026-08-26
- **样本边界**: 共 9 个会话（router 3 个含 1 空会话 / tv 2 个 / reasoning-level 6 个——其中 3 个为 AUDIT-147 已分析，新增 6 个）；原始 zstd 源在 `C:\Users\peter\.dsh\sessions\--<project>--\`（只读，未解压未写入）
- **当前姿态基准**（Coordinator 2026-08-26 只读实测 `check-governance --summary-only`）: router `19 issues`（首个 FAIL = Check 30 Review Closure State Machine，12 closure violations）｜android\tv `5 issues`（首个 WARN = Check 16 Goal Alignment，1 duplicate goal alignment）｜reasoning-level `17 issues`（首个 FAIL = Check 14 Structural Validity，1 structural + 1 blocking）

---

## 0. 结论摘要（TL;DR）

1. **用户「verify 告警洪流」感知 = 部分成立，且已定位洪流源头**：唯一真实告警洪流出现在 **router 项目 2026-08-23 15:43 主会话**（`session-e21f98e2-37b6-424c-8ea0-b7983f89bee3`）——`check-governance --summary-only` ×3（`Governance: 20 issues [FAIL] …` → `19 issues`）、完整 check 1 次（1,712 字符 box 输出含 **12 条 closure violations**）、task-priority-analysis ×2、archive dry-run ×1。
2. **洪流的真正形态 ≠ summary 行本身**：summary-only 在 FAIL 时只输出 1 行摘要 + 1 行首个 FAIL（103 字符），但**触发了模型追查链**——模型随后跑完整 check（1,712 字符）、读 snapshot（3,479）、**读 evidence-log -Tail 30（22,311 字符且含乱码）**。用户看到的「告警洪流」≈ summary 行 + 模型为解释告警拉取的 ≈27KB 后续输出。
3. **归因**：router 19 issues 的 trace 可见部分 100% 为 (a) 历史数据/legacy 姿态（Check 30 引用 ARCH-001/002、DEV-002 的旧 review 轮缺失与 RISK-001/002/003 引用已关闭任务）+ 历史发布绕过（Check 37）；**当前真实工作（FIX-006 P0 待实施）不在告警中**。tv 5 issues 无 trace 交集（tv 两会话零治理命令、零治理告警）。reasoning-level 17 issues = 08-25 17:07 之后 MAINT-017 新行入账触发的 Check 14 结构违规——**与当前工作相关（b 类）且为「新入账任务破坏结构合法性」的治理 gap**。
4. **矛盾解释**：08-25 17:07 的 `Governance: [PASS]` 是**真实 PASS**——trace 内当时 plan-tracker 快照（15,222 字符）任务表仅到 MAINT-016、无 MAINT-017 行、结构合法；17 issues 是 17:07 之后（MAINT-017 入账 + 08-26 前后完成记录撰写）才形成的，且 **17:07 之后无任何会话再跑过 check**（S2/S3 零调用）——姿态在无检测窗口内静默恶化。
5. **成本量化（Q4）**：router 告警会话治理 result 字符占比 = **55.9%（77,533/138,743）**——**唯一超过 50% 的会话**；reasoning 中治理词窗口 8.8%。tv 会话 0.0%–0.3%，reasoning-level 早前会话 5.7%–6.0%。

---

## 1. 样本与取证立面

### 1.1 9 个会话清单（全部为 JSON 事件行；行级类型与 AUDIT-147 相同）

| # | 项目 | 会话 | 本地时间 | 类型 | 行数 | tool/call | 备注 |
|---|---|---|---|---|---|---|---|
| R1 | router | `session-e21f98e2-37b6-424c-8ea0-b7983f89bee3` | 08-23 15:43 | 主会话（depth=0） | 2,489 | 60 | **告警洪流会话** |
| R2 | router | `session-ed6b71c1-a100-4185-b3d1-f0d6e636aad4` | 08-23 19:37 | 主会话 | 11 | 0 | 空会话（用户执行 `permission danger-full-access` 后取消，无任何治理动作） |
| T1 | android\tv | `4f7ef27b-6710-49bd-839a-93db97ebda1e` | 08-24 22:34 | 子会话 Code Reviewer SRC-008 R0 | 4,093 | 81 | 零治理命令 |
| T2 | android\tv | `5b158eaa-aa81-4a2f-879e-2a8b341f9027` | 08-24 23:00 | 子会话 Code Reviewer REL-009 R0 | 1,829 | 31 | 零治理命令 |
| L1 | reasoning-level | `9912985f-aa1e-4306-9c3b-0e95cfb2ca79` | 08-25 12:45 | 子会话 Developer MAINT-013 | 3,219 | 94 | 当日首个；零治理命令 |
| L2 | reasoning-level | `session-f2425223-6212-4a2c-b08e-696597fa1579` | 08-25 17:07 | 主会话（AUDIT-147 S1） | 5,455 | 83 | `Governance: [PASS]`（20 字符） |
| L3 | reasoning-level | `7753e85d-5111-431c-bc84-5109af1554da` | 08-25 17:30 | 子会话 Developer MAINT-017 | 9,806 | 87 | 零治理命令 |
| L4 | reasoning-level | `f68578cb-b5b9-42dd-a997-cc96c7de5e26` | 08-25 20:49 | 子会话 Developer（AUDIT-147 S2） | 3,978 | 70 | 零治理命令 |
| L5 | reasoning-level | `9ce49e34-a1b2-4bf1-be5a-2cdfc5b33939` | 08-25 21:06 | 子会话 Code Reviewer R1（AUDIT-147 S3） | 1,492 | 39 | 零治理命令 |

### 1.2 取证口径（沿用 AUDIT-147 §1，补充说明）

- 告警输出提取：对全部 9 个会话的 `tool/result`（两层嵌套 `message.content[i].content[j].text`）匹配 `Governance: [FAIL|WARN|PASS]`、`\d+ issues`、`Check \d+`、`Structural Validity`、`closure violat`、`Goal Alignment` 等模式；每个命中绑定对应 `tool/call` 的 command 全文（判定「哪种调用」）。
- 治理占比：tool call 分类与 result 字符统计口径同 AUDIT-147 §1.2（分类函数修正版）；reasoning 治理词 = 强词 `Governance|check-governance|verify_workflow|task-priority|plan-tracker|resolve_entry` ±40 字符窗口。
- 补充只读核对：router 与 reasoning-level 的 `.governance/plan-tracker.md` 当前内容（显式 UTF-8 读取）；router `evidence-log.md` 由 trace 内 result 取证（未实机重读）。

---

## 2. Q1 — 洪流在哪里（逐次列出）

### 2.1 全样本真实告警输出清单（9 会话，仅 1 个会话存在）

**仅 router `e21f98e2`（08-23 15:43）命中**。逐次：

| # | 行号 | 调用 | 输出字符 | 内容要点 |
|---|---|---|---|---|
| A1 | 150 | `python …/verify_workflow.py check-governance --summary-only` | **103** | `Governance: 20 issues` / `[FAIL] 28c: Hot Fact-Source Consistency (FIX-087): 1 hot fact-source issue(s):` |
| A2 | 832 | `python …/verify_workflow.py check-governance 2>&1 \| Select-String -Pattern '28c\|FAIL' -Context 0,3 \| Select-Object -First 12` | **1,712** | Box 输出：Check 28c FAIL（snapshot 缺 workflow version）+ **Check 30：12 closure violations** + Check 37 FAIL（G-s2：v0.2.1 tag 存在而 G4 pending） |
| A3 | 1522 | `python …/verify_workflow.py task-priority-analysis` | **582** | Task Priority：3 tasks — 0 completed, 3 unblocked（FIX-006 推荐） |
| A4 | 1882 | `python …/verify_workflow.py task-priority-analysis --evidence-task OPS-001; "=== summary ==="; python …/check-governance --summary-only` | **881**（含 summary 段） | `Governance: 19 issues` / `[FAIL] 30: Review Closure State Machine (FIX-174): 12 closure violation(s):` |
| A5 | 2213 | `python …/archive.py migrate --auto --dry-run` | **45** | 跳过（已发布版本 0 < 2） |
| A6 | 2360 | `python …/task-priority-analysis --evidence-task GOV-003; "=== summary ==="; …/check-governance --summary-only` | **881** | 同上（19 issues / FAIL 30） |
| — | 1246 | `Get-Content "…\router\.governance\evidence-log.md" -Tail 30` | **22,311** | 治理数据读取（**含 GBK-as-UTF-8 乱码**，见 §4.3）——模型为查 A1 的 28c 告警上下文而拉取 |

其余 8 个会话：**0 条**真实治理告警输出（tv 两会话唯一「issues」文本 = Android lint `Total issues: 80`，产品工具输出非治理；reasoning-level 全部会话除 AUDIT-147 已记录的 `[PASS]` 外无任何 check 输出）。

### 2.2 洪流来源判定

- **用户感知的「verify 告警洪流」= router 项目 08-23 15:43 主会话的 check-governance 系列**（A1–A6）。
- **调用类型**：`check-governance --summary-only`（输出超单行：FAIL 时 = 摘要行 + 首个 FAIL 行，PASS 时 = 单行）＋ 模型主动追加的完整 `check-governance`（过滤版，A2）＋ `task-priority-analysis` ×2 ＋ `archive migrate --dry-run`。
- **洪流的「放大链」**（关键机制）：summary 行（103 字符）→ 模型不满足 → 追加完整 check（1,712 字符，12+1 条 violations）→ 为查 28c 读 snapshot（3,479 字符）与 evidence-log -Tail 30（**22,311 字符**）→ 为收尾两轮 task-priority-analysis（582+881×2）。**单条 summary → ≈25.5KB 追查输出**。
- 结论：**洪流存在（router，1 个会话），但「洪流」主体是 summary 行触发的追查链，而非 check 命令本身的默认输出量**。

### 2.3 各项目在 sample 内是否经历过告警

| 项目 | 会话数 | 经历 check 的会话 | 经历真实 FAIL 输出的会话 |
|---|---|---|---|
| router | 3（1 空） | 1（e21f98e2，4 次调用） | 1（e21f98e2） |
| android\tv | 2 | **0** | **0** |
| reasoning-level | 6 | 1（f2425223，1 次 [PASS]） | 0 |

tv 与 reasoning-level 的当前问题姿态（5 / 17 issues）在样本内**没有任何会话经历过**——属 08-26 姿态或样本外会话形成。

---

## 3. Q2 — 告警归因分类（a/b/c 三分）

### 3.1 router —— 19 issues（trace 可见 12+1+1 = 14 条明细）→ 100%(a)

| Check | 明细（trace 原文） | 类 | 判定依据 |
|---|---|---|---|
| 28c | `session-snapshot.md: session snapshot missing workflow version`（1 条） | (a) | snapshot 为 08-23 接入时姿态字段缺失；同日已被 GOV-003 任务（8bd1eb3/0.76.0 版本行修复）覆盖——**历史失效姿态** |
| 30 | `[V2] ARCH-001: round continuity broken — missing R[0]` | (a) | ARCH-001 已完成（R1→R2），R0 无 review 记录——**接入治理前的旧任务审查数据不完整** |
| 30 | `[V5] ARCH-002: R0=APPROVED_WITH_NOTES requires exactly unresolved_blockers=0; got invalid` | (a) | ARCH-002 已完成 review 记录格式不合新状态机（旧格式 `unresolved_blocks=` 缺 `_ers`；plan-tracker 当前仍写 `unresolved_bloc…`）——**历史记录格式迁移未做** |
| 30 | `[V2] DEV-002: round continuity broken — missing R[0]` | (a) | DEV-002 已完成（终态 R1），R0 缺失——同 ARCH-001 |
| 30 | `[R3] RISK-001: references task(s) D-1, DEC-017, DEV-001, DEV-002, RES-003 not found in task status map (cross-entity/archived)` | (a) | DEV-001 已关闭（DEC-017）、D-1/DEC-017/RES-003 在计划外/归档——**跨实体引用未同步**（设计 R3 仅 WARN） |
| 30 | `[R3] RISK-002: references task(s) D-1, DEC-015, MIG-001 not found` | (a) | 同上 |
| 30 | `[R3] RISK-003: references task(s) FIX-001 not found` | (a) | 同上 |
| 37 | `[G-s2] published release tag v0.2.1 exists while prerelease gate(s) G4 are pending` | (a) | v0.2.1 为接入治理前发布（既有事实），G4 待评——**历史发布绕过，顺序不可证**（G-s2 保守判定） |
| 30 | 其余 6 条（trace 中被 `Select-String -First 12` 截断，未见明细；与上述同源，推断同为历史 review/跨实体类） | (a)（推断，标注） | — |

- **代表样例**（≤3）：① ARCH-001 missing R[0]（旧任务无旧轮记录）；② RISK-001 引用 DEV-001（已关闭）/ D-1（计划外）；③ v0.2.1 已发布 vs G4 pending（接入前事实）。
- **与当前工作相关性**：router 当前活跃 = FIX-006（P0，待实施）、EVO-004（已完成）、FIX-004（已完成）——**无一在告警中**。告警 100% 指向历史/归档/格式迁移问题。
- **占比**：trace 可见 14 条明细全部 (a)；估算 19 issues 中 ~17–19 条为 (a)，0–2 条为 (b)/(c)（未展开的 5 issues 无证据——标注待验证）。

### 3.2 android\tv —— 5 issues（首个 WARN Check 16 Goal Alignment：1 duplicate goal alignment, template reuse）

- **样本内零交集**：T1/T2 会话（Code Review SRC-008/REL-009 R0）零治理命令、零治理告警输出（治理字符占比 0.3% / 0%）。
- **归因**（基于 Coordinator 摘要 + 检查器名称，无 trace 明细 → 标注为假设）：Check 16 Goal Alignment 对齐检查（「duplicate goal alignment, template reuse」）指向**治理模板复用产生的重复对齐条目**——(a) 数据质量/历史姿态为主，不涉及当前审查工作；(c) 无证据；(b) 无证据。**无法从样本内证实用户在该项目遇到过该告警**。

### 3.3 reasoning-level —— 17 issues（首个 FAIL Check 14 Structural Validity：1 structural + 1 blocking）

- **归因**：Check 14 结构校验 = MAINT-017 新行入账（08-25 17:07 后）触发——**属于 (b) 当前工作相关**（近期完成任务的行状态导致验证失败），或兼 (a)（历史行增长促使）。占 17 issues 中至少 1–2 条（FAIL）；其余 15–16 条按 Check 名称（未展开）无法分类——标注待验证。
- **代表性事实链**（trace 内可证）：L2（17:07）快照任务 ID 列表 = DEV-001/002/003、DOC-001、GOV-001/002、MAINT-001~016、REL-001/002——**无 MAINT-017**；当前 plan-tracker = 含 MAINT-017 行（「⚠️ **新开** (2026-08-26)——用户实测验收失败…→ ✅ **完成** (2026-08-26)——Developer 4 commit…」，行内两段状态 + 长文本 + 嵌套符号）→ 大概率即 Check 14 的「1 structural + 1 blocking」对象（推断，未复跑 check，标注）。

### 3.4 环境类（c）——样本内证据

- **编码乱码**（c 类唯一实证）：router `evidence-log.md` 经 `Get-Content -Tail 30` 读取出现 GBK-as-UTF-8 mojibake（`R1 瀹℃煡 = APPROVED锛坲nresolved_blockers=0…`），22,311 字符输出大面积乱码——**治理数据读取管道编码问题**（与 AUDIT-147 发现的 node_modules package.json 乱码同源：PowerShell 默认 ANSI/GBK 解码）。
- **SSH/超时/跨路径**：grep 全部 9 会话 `ssh|scp|ETIMEDOUT|ECONNREFUSED|180s|超时`——命中 148 处全部为**产品代码内容**（如 `PROBE_TIMEOUT_MS`、测试的 30s 超时语义、`限流/超时 → blocked`），**无一条治理/基础设施环境的超时或 SSH 告警**。AUDIT-147 提到的本仓基线（origin SSH 限制、单元测试 180s 环境超时）在本样本项目中无体现。

---

## 4. Q3 — 「[PASS]」与「17 issues」矛盾的解决

### 4.1 PASS 来源的确凿信息

- L2（08-25 17:07）`check-governance --summary-only` → `Governance: [PASS]`（20 字符，line 155；完整输出，非截断——同命令在 router FAIL 时输出 103 字符 3 行，PASS 时本应更少）。
- 同期（17:07）plan-tracker 快照（line 100 read result，15,222 字符）：任务表到 MAINT-016；**无 MAINT-017 行**；不含「⚠️ 新开」「✅ 完成」混排；结构合法。

### 4.2 矛盾解（trace 证据链）

1. 17:07 时姿态确实合法（无 MAINT-017 行）→ **`[PASS]` 是当时真值**，不是错误输出、也不是跨项目/跨 cwd 误跑（该会话 cwd = `D:\AI\agent\deepseek\plugins\thinking\dsh-reasoning-level`，meta 行证据）。
2. 恶化窗：17:07 → 08-26（Coordinator 实测 17 issues 时）之间，MAINT-017 行入账（L3 100% 是实现会话，17:30 启动）并在完成记录中写入混排状态长文本。
3. **无检测窗口**：17:07 之后全部会话（L3/L4/L5 + 08-26）**零次 check-governance 调用**（全部 9 会话 grep 证实）——姿态在「无复核」时段静默恶化；下一次有人跑 check 时（本次 AUDIT-148 Coordinator 实测）才暴露。
4. 结论：**PASS 与 17 issues 不矛盾**——是「时间点不同 + 期间结构演化 + 无门禁/无增量检测」的组合。**衍生治理 gap：任务入账/完成记录写入后无结构合法性自动复核（Check 14 无写钩子）。**

---

## 5. Q4 — 成本量化（告警引发开销）

### 5.1 router 告警会话（e21f98e2，唯一洪流会话）

| 指标 | 值 | 口径 |
|---|---|---|
| 治理 tool call / 全部 | 21 / 60（**35.0%**） | §1.2 |
| 治理 result 字符 / 全部 | 77,533 / 138,743（**55.9%**） | §1.2 |
| 告警/分析类输出直接量 | ≈2,587 字符（103+1,712+582+95×2） | A1–A4/A6 的 result 求和（archive 45 未计） |
| 围绕告警的追查 action 输出 | ≈25,345 字符（snapshot 3,479 + evidence-log 22,311 + 其他小项） | A2 后动作 |
| reasoning 治理词窗口 / 总 reasoning | 7,592 / 86,627（**8.8%**） | §1.2 |
| usage 侧 | 未单独计算（本会话未在 stats.json 中；字符口径足够） | — |

### 5.2 对照（其余会话治理占比）

| 会话 | 治理 calls % | 治理 result 字符 % | reasoning 治理词 % |
|---|---|---|---|
| tv T1（审查） | 1.2% | 0.3% | 0% |
| tv T2（审查） | 0% | 0% | 0% |
| reasoning L1（MAINT-013） | 2.1% | 5.7% | 0.6% |
| reasoning L3（MAINT-017） | 1.1% | 6.0% | 0% |
| reasoning L2（主会话 [PASS]） | 20.5% | 34.7% | 4.5%（AUDIT-147 口径） |

### 5.3 结论

- **>50% 判定：成立口径=1 个会话（router 55.9%）**；其余 7 个有实据会话 0.0%–34.7%。用户感知「大部分时间花在治理」的最大可能性 = **router 08-23 主会话**（那一天——8-23——正是 router 接入治理/首日（Scenario D 会话）与 19-20 issues 并存的一天）。
- 告警引发的**边际成本**：2,587 字符的直接告警输出只占该会话治理字符的 3.3%，但其引发的追查链 ≈25.3KB 约占 32.7%——**「告警的放大系数 ≈ 10×」**（告警输出 1 单位 → 追查 10 单位）。

---

## 6. V1 结论（明确判定）

> **用户感知成立/不成立/部分成立 + 正确归因**：

- **「verify 告警洪流」= 部分成立**：真实存在（router 2026-08-23 主会话，`20→19 issues [FAIL]`、`Check 30 12 closure violations`、`Check 28c`、`Check 37`，5 次治理命令 4 次告警相关）——但**只发生在 router 项目的一个会话**；tv（2 会话）与 reasoning-level（6 会话）在样本内**零告警经历**（reasoning-level 仅 1 次 [PASS]）。
- **「告警大多不属于当前治理软件/当前项目」= 成立（就 router 而言）**：router trace 可见明细 100% 为历史数据/legacy 姿态类（a）；**当前真实工作（FIX-006 P0 等）全部不在告警中**。
- **「>50% token 花在治理」= 部分成立**：router 会话 55.9% 达标；其余会话 0–34.7% 不达标。用户感知最可能来自 router 08-23 会话（55.9%）+ reasoning 主会话启动引导（34.7%）。
- **正确归因**：告警洪流 = (1) legacy 姿态的「历史包袱检查」（Check 30/37/28c 指向接入前旧数据）+ (2) summary 触发的追查链放大（10×）+ (3) reasoning-level 的「新任务行破坏结构」未在写时检测——**三者均非目标项目「当前工作」的告警**。

---

## 7. 优化方向选项补充（不做裁定）

| # | 选项 | 目标 | 成本 | 收益 | 风险 |
|---|---|---|---|---|---|
| G1 | **summary-only 默认输出 top-N FAIL/WARN 明细**（如 HEAD 3 条 + "…N more"） | 消除「模型追加完整 check」的 1,712 字符追查 | 低（verify_workflow 输出模板改动） | 单次降低 1.6KB + 消除一次主动追查 | 输出多 3 行；API 使用者需适配 |
| G2 | **legacy 基线静默/白名单**（Router 类历史数据：Check 30 的 ARCH-001/002、DEV-002 等接入前任务 → 白名单或降级 advisory，仅 console 不 FAIL） | 消除 12 条 closure violations 的每会话重复 FAIL | 中（白名单机制 + 迁移审查） | 每次 check 从 12 违规 → 0；与用户「告警大多不相关」感知直接对齐 | 掩盖真实 review closure 缺口（需审计日志保留） |
| G3 | **Check 14 类结构校验写时触发**（plan-tracker 被 edit/更新后自动跑结构校验） | 消除「无检测窗口静默恶化」（reasoning-level 17:07→08-26） | 中（hook 或 verify 集成） | 缺陷在写入时暴露，PASS 真值持续可保持 | 写路径变慢；误报需分流 |
| G4 | **证据文件读取 UTF-8 显式化**（`Get-Content -Encoding UTF8` / [IO.File]::ReadAllText——治理数据读取模板） | 消除 evidence-log 22KB 乱码（router） | 极低 | 消除乱码干扰 + 避免「读 22KB 才知道那里写了什么」的二次解读 | 无 |
| G5 | **task-priority-analysis 重复抑制**（同一会话第 2 次调用带 `--no-cache` 语义或直接提示「已分析，推荐未变」） | 消除重复 881×2 输出 | 低 | -1.7KB/会话 | 信息可能过期需手动刷新 |
| G6 | **「告警追查预算」提示**（summary 输出尾部附一行「详见 <command> 获取 full report」） | 减少模型自发拉取全量 check/evidence-log | 低 | 追查从 25KB → 1 行提示 | 无 |

（G1–G6 均为选项；另可复用 AUDIT-147 的 A–F 项（活跃视图/双份引导去重/review findings 落盘/行状态机/lean 模式/编码）作为整体优化池。）

---

## 8. 事实 ↔ 假设、待验证项与合规

### 8.1 事实/假设表（本报告内）

- 事实（trace 行号可复算）：§2.1 全部 6 条告警输出行号与字符量；§3.1 router 明细原文；§4.1 L2 快照任务 ID 列表与 [PASS] 20 字符；§5.1 各项占比（同口径可复算）；router 当前 plan-tracker 18,747 字符、ARCH-001/002 等状态行；tv 两会话零治理命令（grep 全文件）。
- 假设（已标注）：① §3.1 Check 30 其余 6 条明细（被 `-First 12` 截断，推断同源）；② §3.2 tv 5 issues 的 (a) 类归因（无 trace 明细）；③ §3.3 Check 14 的「1 structural + 1 blocking」具体对象（推断为 MAINT-017 行，未复跑 check）；④ §3.4 环境类无 SSH/超时证据——仅证明「样本内无」，不证明「系统无」。

### 8.2 待验证项

| # | 事项 | 证据需求 |
|---|---|---|
| V1' | router 19 issues 中未展开的 5 条明细与 (b)/(c) 占比 | 完整 `check-governance` 输出（Coordinator 已跑 summary；需 full 模式或 `--show-all`） |
| V2' | reasoning-level 17 issues 的 Check 14 违规明细 | 完整 check 输出（本分析未复跑） |
| V3' | 用户感知时间点是否 = 08-23 router 会话当天 | 用户自述/当日会话完整目录（router 其他日期的 session） |
| V4' | evidence-log 乱码在 router 其余读取中是否普遍 | trace 内其他 Get-Content .governance 结果抽查（本报告抽查 A2 行即 22KB 一条，已证实） |

### 8.3 合规确认

- `~/.dsh` **零写入**（本分析仅 read/grep/glob + 只读 PowerShell 管道；原始 zstd 未解压）；`.governance/` **零写入**（对 router/reasoning-level 的 `.governance` 文件仅 `[System.IO.File]::ReadAllText` 只读）；唯一文件写入 = 本报告。
- 与 AUDIT-147 的衔接：本报告沿用其口径与结论，无冲突；AUDIT-147 的 H1 判定（样本内不支持）在本报告范围扩展后**修正为「部分成立（router 单会话）」**。
