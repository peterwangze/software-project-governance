# FIX-392 后置代码审查报告（R0）——Check 30 复合键判据（task+chain+round）

- **Task ID**: FIX-392（0.89.0 批次二第二票；前置 FIX-390/def9508 已集成——worktree HEAD=def9508 实证）
- **审查对象**: staged diff（`git diff --cached`）：`infra/checks/review_domain.py`（+205/-26 核心）、`infra/verify_workflow.py`（+1 re-export）、`infra/tests/test_verify_workflow.py`（+364 新类）
- **审查轮次**: R0（首轮） · **审查者**: Code Reviewer Agent · **日期**: 2026-09-26
- **依据**: agents/code-reviewer.md + skills/code-review/SKILL.md（五维度 + AI 五项）+ 任务书六项审查重点
- **审查性质**: 只读审查 + 硬门槛实跑；未修改任何产品代码/staged/.governance（临时对照物均在 %TEMP%，worktree 已可清理）

---

## 结论

## **APPROVED_WITH_NOTES**（unresolved_blockers=0）

P0=0 · P1=0 · P2=1 · P3=4。硬门槛全部亲跑通过；申报的核心声明（复合键视图、链归属双通道、V3 链内分段、写入面零改动、census Check 30 面 30→25 逐行恒等、熔断三守卫恒绿）全部独立核验成立。唯一 P2 为**申报措辞精度**：「零漂移回退」需限定为「无 BLOCKED 轮的 canonical 链」——含 BLOCKED 轮的 canonical 链行为有意变化（分段语义），有测试看护、census 数据面验证为仅消解伪 WARN，不构成缺陷。

---

## 一、硬门槛亲跑记录（MUST 实跑核验）

| # | 门槛项 | 命令 | 结果 | 判定 |
|---|--------|------|------|------|
| 1 | 新类测试 | `pytest test_verify_workflow.py -k "CompositeKey" -v` | **9 passed, 13 subtests passed**（0.58s） | ✅ 与申报一致 |
| 2 | 红先行复现 | HEAD worktree（def9508 产品代码）+ staged 测试 | **6 failed / 3 passed**——6F=blocked_boundary/c5_with_chain/parser/dual_chains/artifact_shape/live_collector；失败形态：V3 伪像复现（`Lists differ: [{'rule':'V3',...BLOCKED'}] != []`）+ `KeyError: 'chains'`（HEAD 无 chains 视图） | ✅ 与申报 6F/3P 精确一致，测试非恒绿 |
| 3 | census 亲跑 | `check-governance`（完整报告，before/after 双跑 + before′ 复跑定案） | 见 §四：**Check 30 面 30→25 WARN，V3 五行消解，V1×21/V2×3/V5×1 逐行恒等** | ✅ |
| 4 | write-guard 亲跑 | `governance-write-guard --show-posture` | exit=0，五族姿态表正常（evidence/review/decision/ops_ledger 裁定=block 现值=warn [D1]；task_status deferred），break-glass 无活动窗口 | ✅ |
| 5 | 逐行 diff 通读 | 全量 staged diff + review_domain.py 上下文（_build_review_sequence 全体 / check_review_closure V1-V6 段 / _collect_live_review_sequences 双通道） | 已完成，发现见 §六 | ✅ |
| 6 | 定向族全量 | `pytest test_verify_workflow.py -q`（staged 面） | **3 failed, 939 passed, 139 subtests passed**（251s） | ✅ 3F 基线归属见 §五 |

---

## 二、逐行 diff 审查（review_domain.py 核心）

### 2.1 `_review_chain_attribution`（L1929-1960）——链归属双通道解析

- **双正则分层**：ROUND_RE（`review-([A-Z]+-\d+)-(.+?)-R(\d+)\.md`）优先（有轮次），BARE_RE（`review-([A-Z]+-\d+)-([^.]+)\.md`）兜底（round=0，对齐 C6 bare=R0 约定）。顺序正确：round 通道命中即 return，不会被 bare 通道误降级。
- **误归属防线逐条核验**（实测 + 逐行验证）：
  1. **round 键控镜像排除**：`review-REL-086-R3.md` → ROUND_RE 不匹配（`(.+?)` 需 ≥1 字符，`-R3.md` 前无 slug）；BARE slug=`R3` 被 `_REVIEW_CHAIN_ROUND_TAIL_RE`（`^R\d+`）排除 → `(None, None)` ✅（测试 case 5 实证）
  2. **FIX-314 reviewer 命名空间排除**：`review-REL-086-R0-release.md` → ROUND_RE 不匹配（R0 后非 `.md`）；BARE slug=`R0-release` 含小写 → SLUG_RE（`^[A-Z0-9]+(?:-[A-Z0-9]+)*$`）拒绝 ✅（case 4 实证——round-tail 与小写双排除承重）
  3. **跨任务引用排除**：`review-REL-087-CODE-R0.md` 在 REL-086 的行中 → `group(1) != task_id` skip，finditer 继续扫描同文本后续引用（不提前放弃）✅（case 10 实证）
  4. **小写 slug 排除**：`review-REL-086-design-R0.md` → SLUG_RE 拒绝 ✅（case 11 实证）
  5. **lookbehind**（`(?<![A-Za-z0-9-])`）防 `preview-`/`xreview-` 前缀粘连 ✅
  6. **空/None 防御**：`not task_id or not text → (None, None)` ✅（case 13 实证）
- **带尾缀形态（任务书构造项）**：`review-REL-086-R0-RELEASE.md` 形态——ROUND_RE 不匹配（`-R(\d+)\.md` 要求 R+数字紧跟 `.md`，此处 R0 后是 `-RELEASE`）；BARE slug=`R0-RELEASE` 被 round-tail 排除 → `(None, None)` ✅（分析验证；该形态被正确归入 canonical 而非伪链）。

### 2.2 `_build_review_sequence` chains 复合键视图（L2070-2132）

- 三处 `setdefault` 初始化（L2058/L2065/L2156）**全部**补齐 `"chains": {}`——无 KeyError 面（939P 实证）。
- 归属优先级：`entry["chain"]` 显式字段（fixture 路径）> collector 预推导（活体路径）；`chain_round` 缺省回退 `round_n`——保守正确。
- duplicate-round 处理：chain 视图与全局 rounds 表采用**同一 terminal-preference 规则**（`existing not in TERMINAL and conclusion in TERMINAL`）——V3（消费 chain 视图）与 V1/V2/V4/V5/V6（消费全局表）判定基准一致。
- **canonical 零漂移等价性论证**：全无归属输入下，`chains["canonical"]["rounds"]` 的 key/value 与全局 `seq["rounds"]` 完全同构（每 entry 双写、同 update 规则、同 max 语义）；V3 新判定取 `_chain_fuse_segments(canonical)` 单段 `(max(rounds), conclusion_at_max)`，与旧 `max_round`/`terminal` 二元组**数学等价**；canonical 时 `chain_ctx=""`，violation/warning reason 文本**逐字节一致**（构造对照实证，见 §三）。

### 2.3 `_chain_fuse_segments`（L1962-1990）——V3 链内分段

- BLOCKED 闭链语义：`conclusion == "BLOCKED"` 段闭合、`base = rnd + 1` 重开归零——与 M7.4 step 4.6「✗ → escalation」一致（REL-080 形态）。
- 段内 terminal = local 最大轮结论（sorted 遍历下 local 严格递增，terminal=段末轮）——与旧「最高轮结论」语义同构。
- 空输入返回 `[]`（防御安全）；链无 BLOCKED 时单段 local=recorded rounds（零漂移）。
- **边界正确性**：BLOCKED 轮本身超 fuse 时段 `(seg_max, BLOCKED)` 既非 NC 也非 APPROVAL → 无 finding（BLOCKED 闭链=合法升级终态，不罚，对齐 C3/T2）。

### 2.4 V3 判定改造（L2450-2486）

- `v3_violations` 非空 → extend + `continue`（跳过 V1-V6，与旧 NEEDS_CHANGE 分支等价）；否则 extend warnings + fall-through（与旧 APPROVED-WARN 分支等价）。控制流保持。
- 多链多段聚合后一次 extend——不改变 verdict 规则面。
- V1/V2/V4/V5/V6 全部继续读全局 rounds 表（`terminal`/`rounds[max_round]` 未动）——**复合键只影响 V3**（唯一 chain-sensitive 规则）✅ 申报成立。

### 2.5 采集面双通道（L2966-2988 row / L3010+L3030-3040 mirror）

- row 通道：`_review_chain_attribution(task_id, stripped)` 按行文本推导；`REVIEW-REL-086-R0-RELEASE` 形态行 ID 经 `REVIEW-[A-Z]+-\d+(?:-R\d+)?`（L2958）解析为 `REVIEW-REL-086-R0`，归属走整行文本 → 与 file 通道一致。
- mirror 通道：**`fc = ""` 失败绑定**（L3010）——读失败时 attribution 得 `(None, None)` → canonical → 全局判定回退，**不会因 IO 错误误归属** ✅（fail-closed 方向正确）。
- `REVIEW_MACHINE_ROW_MARKER`/`source_format`/`blocker_evidence` 等字段零改动 ✅。

### 2.6 写入面零改动核验

- `git diff --cached --name-only` = 仅 3 文件，`review_record.py`（infra/review_record.py）**不在 staged**；grep 证实其 import 面（loop_gate_processor/loop_exit_bridge）**无 review_domain 逆向依赖** ✅。
- REVIEW-{task}-R{n} 行 ID 形态、9-cell 行契约、DEC-247 已入账判据语义：采集/写路径无触碰 ✅。

---

## 三、canonical 零漂移构造对照（双代码版本逐字节 diff）

方法：同一组 5 个无归属 fixture，分别在 staged 代码与 HEAD worktree 代码上跑 `check_review_closure`，JSON 逐字节 diff（探针：%TEMP%/fix392-zdrift/zdrift_probe.py）。

| fixture | HEAD（before） | staged（after） | 一致性 |
|---------|---------------|----------------|--------|
| a_r4_approved（R4=APPROVED） | WARN V3 "round 4 > fuse 3 but R4=APPROVED — possible marginal pass…" | 同 | ✅ 逐字节一致 |
| b_r5_nc（R5=NC 终态） | FAIL V3 "round 5 > fuse 3 and R5=NEEDS_CHANGE — must escalate to BLOCKED" | 同 | ✅ 逐字节一致 |
| c_normal（R1=AWN） | FAIL V5（缺 unresolved_blockers=0 token） | 同 | ✅ 逐字节一致 |
| e_midflight（R0=NC 未完成） | WARN V1 non-terminal | 同 | ✅ 逐字节一致 |
| **d_blocked_reopen**（R3=BLOCKED，R6=APPROVED） | **WARN V3 "round 6 > fuse 3 but R6=APPROVED"** | **PASS（分段：段1=(3,BLOCKED) 不罚，段2 local 2）** | ⚠️ **有意行为差异**（见 P2-1） |

**判定**：无 BLOCKED 轮的 canonical 链零漂移**实证成立**（4/5 逐字节一致，含 violation/warning 文本）；含 BLOCKED 轮的 canonical 链按新分段语义变化——该变化恰是 REL-080 类伪 WARN 的消解机理，有专门测试看护（`test_blocked_escalation_boundary_starts_new_segment`，红先行实证 HEAD=FAIL/staged=PASS），census 真实数据面无新增 FAIL（§四）。→ 记 **P2-1 申报措辞精度**，非缺陷。

---

## 四、census 恒等性亲验（审查重点 4）

方法：HEAD 代码经 `--project-root` 扫主工作区数据（before，15:10）vs staged 代码原生跑（after，15:11）+ HEAD 复跑定案（before′，15:13）。

**Check 30 面（本票核心面）**：
- before（HEAD）：`[WARN] 30 closure WARN(s)`，含 V3 五行：FIX-291/REL-073/REL-077/REL-080/REL-086（"round 5/6 > fuse 3 but R5/R6=APPROVED — possible marginal pass"）
- after（staged）：`[WARN] 25 closure WARN(s)`，**V3 五行全部消失**；25 条 = **V1×21 + V2×3 + V5×1**，与申报**精确一致**；diff 中 after 侧零新增 WARN 行 → **25 条逐行恒等** ✅
- Tasks with review sequences: 423（两跑一致面）
- **30c 面**：两跑报告行无差异（恒等）✅；**18/18b 面**：diff 中无该面行（恒等——FIX-390 面 ②② 组合不受本票影响）✅
- Inventory 哈希行变化（申报第 6 行）✅ 吻合

**关于全报告 diff 行数的说明**（审查透明度）：我的跨布局对照（worktree 代码 `--project-root`）产出大 diff，经 before′ 复跑 + 证据定位判定为**布局 artifact**：①before 侧 30 行 `[SKIP] product self-check — host/plugin roots diverge`（检查启用面不同）；②hot-fact（Check 28c）20 条 FAIL 仅出现在主工作区原生布局——内容全部为 plan-tracker 0.88.0 roadmap 过渡态数据面问题，与 review_domain.py 零代码路径交集，且 HEAD 代码在同布局下同样会产生（staged diff 未触碰 hot-fact/plan-tracker 解析）；③框线宽度自适应差异。**申报「全报告 diff 仅 6 行」系同布局 stash 对照口径，其 Check 30 面声明（计数行+V3 五行+Inventory 哈希）与我的独立实测完全吻合**。

---

## 五、V3×5 消解凭证抽查（3 席，超额完成 ≥2 席要求）+ 3F 基线抽查

### 席位 1：REL-086（DEC-242③ 本体——复合键消解）
- evidence-log L2570-2751 九行 REVIEW 行 ↔ docs/reviews 十个链命名报告 ↔ .governance 镜像体 **三向一致**（抽查 review-REL-086-R2-code.md/report→CODE-M3、review-REL-086-R4.md/report→RELEASE-M3-R2 实证双通道同源）
- 链归属推导：DESIGN{0,1} + RELEASE{0,1,2} + CODE-M3{0} + RELEASE-M3{0(R3 bare),2(R4),3(R5)}——链内 max=RELEASE-M3 local 3 ≤ fuse 3 → 消解 ✅；九行全归属、canonical 不残留（与测试 `assertNotIn("canonical", chains)` 同构）
- 旧伪像："global R5 > fuse 3 but R5=APPROVED" → census after 无 REL-086 V3 ✅

### 席位 2：REL-080（BLOCKED 分段消解）
- evidence-log L2260-2278：R0-R2=NC → **R3=BLOCKED**（L2272）→ R4-R6 重开（NC/NC/APPROVED）；全部行引用 `review-REL-080-RELEASE-R{n}.md` → RELEASE 链 local 0-6
- 分段：段1=(3, BLOCKED)（不罚，合法升级终态）+ 段2=(2, APPROVED) ≤ fuse → 消解 ✅；镜像体 review-REL-080-R6.md/report→RELEASE-R6 实证 file 通道同归属
- 旧伪像："round 6 > fuse 3 but R6=APPROVED" → census after 无 REL-080 V3 ✅

### 席位 3：FIX-291（复合键消解，追加置信）
- evidence-log L1670-1680 六行：DESIGN{R0,R2,R4→local 0,1,2} + CODE{R1,R3,R5→local 0,1,2}，双链链内 max=2 ≤ fuse → 消解 ✅；六行全归属无丢失；旧伪像 "round 5" → census after 无 ✅

（REL-073/REL-077 未逐席抽查，形态与上三席同类，census 面已验证消解。）

### 3F=既有基线抽查
- **FIX300DualCaliberAgreementTests 两项**：HEAD worktree 单跑（HEAD×HEAD）**同样 FAIL**（`AssertionError: 'PASS' != 'BLOCKED'`）→ 直接实证既有 ✅
- **LoopRuntimeClaimAdapterTests::test_claim_command_emits_complete_pass_report**：主工作区单跑 FAIL（`check-loop-runtime-claims` exit 1）；直接跑子命令定因：verdict=**BLOCKED**，由 `.governance/risk-log.md` ragged-table 行（ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY，语义记账面）+ state_totals 分布驱动——staged diff 与 LRC 扫描器/risk-log/被扫描文档**零代码交集** → 判定既有（数据面基线）✅
- 备注：申报「定向族 1138P+139S/3F」与实测 939P+139S/3F 在 **3F/139S 完全一致**，P 计数差 199 疑为统计口径差异（如含 subtests 折算/其他入口），不影响失败面结论（P3-4 备注）。

---

## 六、发现列表

### P0（阻塞）：无

### P1（关键）：无

### P2（建议）

- **P2-1 申报措辞精度——「无归属→canonical 链=旧全局判定零漂移回退」需限定**。
  - 位置：review_domain.py L1949-1952 docstring / L2446-2449 注释；申报声明②。
  - 事实：§三构造对照实证——零漂移仅在**链内无 BLOCKED 轮**时逐字节成立；含 BLOCKED 轮的 canonical 链行为变化（d_blocked_reopen：HEAD WARN → staged PASS）。
  - 影响评估：行为本身正确（恰为 REL-080 消解机理）、有红先行实证的测试看护、census 真实数据面无新增 FAIL——非缺陷；但 docstring/申报的「reproduces the task-global judgment exactly」若被后续维护者按字面理解，可能在 BLOCKED+canonical 组合上产生错误预期。
  - 建议：docstring 补一句限定（如 "exactly, for chains without a recorded BLOCKED round; chains with BLOCKED are segmented per M7.4 step 4.6"）；或在本票 changelog/申报注记中显式声明该语义面。**不阻塞合并**。

### P3（讨论/备注）

- **P3-1 纯数字 slug 可成链**：`_REVIEW_CHAIN_SLUG_RE` 允许全数字 slug（如假想 `review-REL-086-086.md` → 链 "086"）。现实命名惯例无此形态且 R\d 开头已排除，属假想边界；保守性不受损（V1/V2 等仍走全局表）。可选加固：slug 首字符要求 [A-Z]。
- **P3-2 一行多链引用取文本序第一**：`finditer` 顺序返回首个本任务链引用（如行内同时出现 DESIGN-R0 与 RELEASE-R2 引用时取 DESIGN）。确定性无损，语义选择未定义；现实证据行/report 行均为单引用（三席抽查实证）。可留档即可。
- **P3-3 `rounds[r]["chain"]` 元数据在 duplicate 轮替换时保留首轮归属**（L2119-2122 取旧 dict 值），与 chains 视图在「同轮双通道异归属」时可能不一致。grep 证实该字段**当前零消费者**（仅写入），纯信息字段；若未来有消费者需先定义权威源。
- **P3-4 申报 P 计数口径**：1138P（申报）vs 939P（实测），3F/139S 一致；建议后续申报注明统计命令口径。

### 边缘 3 项定级（任务书要求）

| 边缘项 | 定级 |
|--------|------|
| 纯数字 slug 成链（假想命名） | P3-1 |
| 一行多链引用的文本序选择 | P3-2 |
| duplicate 轮 chain 元数据不同步（零消费者字段） | P3-3 |

---

## 七、AI 代码专项五项检查

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | ✅ 无 | 测试的 `patch.object(vw, SAMPLE_PATH/...)` 为标准 fixture 注入（临时目录隔离），非 mock 残留；实现零 mock |
| 2 | 硬编码返回值 | ✅ 无 | 实现全为数据推导（regex→tuple→dict 视图），无条件硬编码结论 |
| 3 | 幻觉 API 调用 | ✅ 无 | 仅用 `re.compile/finditer/match`、dict/str 标准 API；lookbehind 固定宽度合法 |
| 4 | 未实现 TODO | ✅ 无 | diff 无 TODO/FIXME/占位 |
| 5 | 过度实现 | ✅ 无 | chains 视图仅 V3 消费；re-export 被 `vw._review_chain_attribution` 测试消费；无未接线的分支 |

## 八、安全检查（OWASP 关键项）

✅ 不适用面为主——纯只读检查器：无注入面（regex 对输入只读匹配）、无敏感数据、无权限逻辑；`rf.read_text(encoding="utf-8")` 显式编码（FIX-278 对齐）、IO 异常 fail-closed（L3010 `fc=""` 绑定）。

## 九、测试覆盖评估（维度 5）

9 用例覆盖：双链互不熔断（正）/单链超熔断仍 FAIL（守卫①）/全局键控伪像回归（负）/BLOCKED 边界重开（分段正）/升级后段超熔断仍 FAIL（守卫②）/C5 WARN 无归属保留（守卫③）/C5 WARN 链归属命名/解析器 13 形态表驱动/活体采集端到端（双通道+canonical 不残留+closure 闭合）。核心路径、边界（BLOCKED 边界、fuse=3 恰好不触发）、错误路径（升级后继续烧）均有看护；红先行 6F/3P 实证看护有效。覆盖率达标（本票面 9/9 新用例全绿 + 既有 933 用例无回归失败）。

---

## 十、硬门槛裁决汇总

| 门槛 | 裁决 |
|------|------|
| P0 = 0 | ✅ |
| 5 维度全覆盖 | ✅（正确性 §二/§三、安全性 §八、可维护性 §六 P2-1/P3 组、性能（行级 O(n) regex 扫描，~0.6s 测试面/census 无劣化）§二.5、测试覆盖 §九） |
| 每条发现标注级别 | ✅（P2×1 + P3×4，全部非阻塞） |
| 设计一致性（DEC-242③/DEC-247/M7.4 step 4.6 C3/C5/C6） | ✅（写入面零改动+判据读侧消解+BLOCKED 闭链语义逐条对齐） |
| AI 五项 | ✅ 全部完成 |

**最终结论：APPROVED_WITH_NOTES（unresolved_blockers=0）**——可合并；P2-1（docstring 申报限定）建议随本票或下一票收口，不阻塞。

---

*审查证据临时物（%TEMP%/fix392-head-wt worktree、fix392-zdrift 探针、census 三份报告、LRC JSON）保留至本票关闭；worktree 可用 `git worktree remove` 清理。*
