# Review: FEAT-081 — ADR-021 B4 M2 词集检测三件套 CODE R0

- **Task**: FEAT-081（P2，目标 0.94.0）
- **轮次**: R0（首轮）
- **审查对象**: 工作树未提交变更 6 文件（5 M + 1 ??）——`infra/checks/loop_gate_processor.py`（新建 428 行）、`infra/verify_workflow.py`（+284/−31）、`infra/tests/test_verify_workflow.py`（+483/−4）、`core/manifest.json`（+4）、`infra/checks/version.py`（+7/−3）、`core/architecture-baseline.json`（+4/−4）
- **Reviewer**: Code Reviewer Agent（角色定义 `agents/code-reviewer.md` + `skills/code-review/SKILL.md` 已加载）
- **验证方式**: 全部结论基于独立复跑命令、git diff 取证与逐行实读；Developer 自报仅作对照（一处直方图偏差见 F-P3-1）。审查过程零产品代码/`.governance/` 写入（终态 `git status` 复核与起始一致）。
- **日期**: 2026-10-02

---

## 0. 结论摘要

**APPROVED_WITH_NOTES**（`unresolved_blockers = 0`）

| 级别 | 计数 | 说明 |
|------|------|------|
| P0 | 0 | — |
| P1（BLOCKING） | 0 | — |
| P2 | 1 | F-P2-1：ADR B4 批次行「bootstrap 指标面」子项未随交付且无承载锚（治理同步缺口，处置归 Coordinator 勘误写回，非代码返工） |
| P3 | 5 | F-P3-1 自报红态直方图失准；F-P3-2 SKIP 分态推导双实现；F-P3-3 rows_judged 口径含豁免行族；F-P3-4 deferred 按词计数非按行；F-P3-5 台账无轮转策略 |

9 个重点裁定点逐项核查：**8 项成立、1 项（裁定⑧）判定为「不影响本任务验收但存在 ADR-实况同步缺口」**（详见 §2）。CR-R1-1 的实质主张——DEC-288 M2 生效判据不再可平凡满足——经端到端独立复现证实（红态 19 errors → 绿态 25/25，链路钉子真实）。

按 code-review SKILL 关闭规则：P0=0 ∧ P1=0 → 通过终态合法；P2/P3 以遗留项跟踪（§4 处置列）。

---

## 1. 证据矩阵（独立复跑）

| # | 命令/取证 | 结果 |
|---|-----------|------|
| V1 | `git status --porcelain` + `git diff --stat` / `--numstat` | 6 文件：verify_workflow +284/−31（净 +253）、tests +483/−4（净 +479）、manifest +4、version +7/−3、baseline +4/−4、新文件 428 行 |
| V2 | `python skills/software-project-governance/infra/verify_workflow.py verify` | **== Verification Result: PASSED ==**（全文存 `%TEMP%\feat081-verify-out.txt`） |
| V3 | `... check-cross-references` | PASS——77 files / 728 refs，零 dangling/deprecated/circular |
| V4 | `... check-manifest-consistency` | PASS——Canonical files **998**（主张 997→998 ✓；独立遍历 manifest "type":"file" 条目 HEAD 143 → 工作树 144，差 +1 = 新模块条目） |
| V5 | `... check-governance` | 0 failing criterion；**2 issues** = 1 untracked 过渡态（`checks/loop_gate_processor.py`，Check 25 WARN 披露）+ 1 既有归档完整性 WARN（REVIEW=1 archivable）——与「基线 2 issues 不扩大」主张一致；S1b snapshot 时效 WARN 为会话性工件、非本交付所致（交付未触碰 `.governance/`）。活体 Check 42 面实测输出：`[SKIP] 当日无新增问题行且无 deferred 检测——无观测义务（skip_kind=vacuum；window=daily-aggregate（…禁止无标注的静默降级…））`——SKIP 分态 + 降级标注在活体面工作 |
| V6 | `python -m unittest tests.test_verify_workflow.{LoopGateProcessorWordSetTests,DeferredRegistrationFace5Tests,Check42DeferredSignalTests,B3ProvenanceWiringTests}`（cwd=infra） | **Ran 25 tests — OK**（19 新 + 6 既有 B3 接线） |
| V7 | `python -m unittest tests.test_static_version_pins`（cwd=infra） | **Ran 25 tests — OK**（含 RealTreeContractTests 实树扫描 clean——再锚后 pin 绿） |
| V8 | 红态复现（隔离临时树：`git archive HEAD` 基座 + 覆盖新测试文件；零仓库写入；树在 `%TEMP%\feat081-red`） | **Ran 19 tests — FAILED (errors=19)**：ImportError×8（`cannot import name 'loop_gate_processor' from 'checks'`）+ TypeError×7（`check_governance_write_shapes() got an unexpected keyword argument 'deferred_ledger'`）+ ValueError×4（`not enough values to unpack (expected 3, got 2)`） |
| V9 | 双向窗口反事实（python -c 直调模块） | 判据 3 两形态 fired=False ✓；**prefix-only 反事实**：「'登记待以后'=违规」形态零豁免（会 fire → 违反判据 3）、「废除登记待以后」形态豁免——单向前缀臂不满足验收，双向为最小解 |
| V10 | pin token 实证 | 新 21025/21057 行均含 `result = vw.check_release_readiness(version="0.93.0")`（FIX-405 token 未变 ✓）；漂移 +479 = 测试文件净增（+483−4）且全部落于 pin 之前（插入点在 B3ProvenanceWiringTests 之后）——算术精确 |
| V11 | `git rev-parse HEAD` | `84f8819…` == baseline regen `generated.git_head` ✓ |
| V12 | CLI 面 diff | verify_workflow.py diff 中 `add_argument/add_parser/set_defaults` 命中 **0 行**——CLI 零变更 ✓ |
| V13 | 活体台账缺席 | `.governance/.write-guard-deferred-ledger.jsonl` 不存在（V2/V5 复跑后复核 Test-Path False——verify/check-governance 面确不写台账） |
| V14 | 词集逐词核对 | 模块 `DEFERRED_LITERAL_WORDS` 12 词 + `DEFERRED_PATTERN_WORDS` 1 正则与 ADR §3.2.1 L324 逐项一致；`NEGATIVE_CONTEXT_MARKERS` 五标记与 L325 一致；窗口常量 = 8 |

---

## 2. 九个重点裁定点逐项核查

### ① 双向窗口消歧 — **成立**

- **矛盾真实**：ADR §3.2.1 规范文本（L325）「命中词**前 8 个字符**内含 …」为前缀单向；而验收判据 3（L360）首例「'登记待以后'=违规」的 `=` 位于命中词**之后**——前缀窗无论多宽都触不到。§7 BC-3（L458）同用「词前 8 字符」措辞，同样偏前缀。实证（V9）：prefix-only 反事实对该形态零豁免（两 hit `negative_context_hit` 均 False → 会 fire），直接违反判据 3「零 issue」。
- **双向是最小解**：判据 3 第二例「废除登记待以后」的 `废除` 在词前——suffix-only 臂无法豁免；两例同时满足 ⇒ 必须 prefix OR suffix 双臂。比「全行任意位置含标记即豁免」显著更保守（限 8 字符紧邻窗口），误豁免面最小。
- **披露形态合规**：消歧在常量块注释（loop_gate_processor.py L100-107）+ 测试注释（test_negative_context_window_exempts）双重落文，并声明台账第三键保留收紧数据；规格文本变更走 proposed DEC（Coordinator 写回）——符合「实现不越权改 ADR」纪律。审查意见见 §5。

### ② 台账写入路径（rel089 契约）— **成立（写入点枚举完备）**

全仓 `check_governance_write_shapes` / `_reconcile_row_families` / `deferred_ledger` / 台账文件名 grep 结果：

| 调用点 | persist_state | deferred_ledger | 台账写入 |
|--------|--------------|-----------------|---------|
| `cmd_governance_write_guard`（verify_workflow.py L25167-25170，post-commit hook 路径） | True | **True** | **✅ 唯一写点** |
| `run_release_bootstrap_converge`（L25413，rel089 内部 persist 面） | True | 未传（False） | ❌ 无 |
| 收敛探针 `_reconcile_row_families` 直调（L25281-25283） | False | 未传 | ❌ 无 |
| 既有全部测试调用（test_triage_write_guard / test_rel089_release_compat / test_change_triage 等 ~40 处） | 混合 | 未传 | ❌ 无 |

写入块本体（L24857-24889）门条件 `persist_state ∧ deferred_ledger`；写失败 → `deferred_ledger_unwritable` WARN 响亮披露。负例测试 `test_converge_path_writes_no_ledger_file` 钉住 converge/probe 双路径零台账文件；活体面复核（V13）佐证。文件名 grep 全仓仅命中 verify_workflow 与新测试（测试在自己 temp gov 内造 fixture，合法）。

### ③ face-5 钩子时序 — **成立**

`_judge_row_delta`（L24511 起）逐行循环内：multiset-diff 出的新增/变更行实例（基线池 miss = diff 窗口语义，存量行 early-continue 不进检测——`test_stock_rows_inside_baseline_not_prosecuted` 钉住验收 4）→ **先** `judge_deferred_row`（L24522）→ **后** `_row_family_credential_ok`（L24579）。行族过滤在 judge 内完成（EVD-→evidence、plan-tracker→task_status、DEC-/REVIEW-/ops→豁免 None）。正交性有专门钉子：`test_credentialed_row_still_detected` 的 fixture 含真实凭证标记（`机器写入：governance-store`，L24041 前缀子串判定，凭证确过）仍 fire——「凭证判定正交前执行」非纸面主张。

### ④ 两个 rider 正当性 — **成立（归因精确、零夹带）**

- **version.py pin 再锚**：token 为 FIX-405 的 `check_release_readiness(version="0.93.0")` 双行（V10 实证新行位）；漂移 +479 与测试文件净增 +479 精确相等，且测试插入区间（B3ProvenanceWiringTests 之后、pin 行之前）覆盖全部插入行——归因成立；RealTreeContractTests（V7）25/25 绿 = 再锚后 rot-guard 闭合。注释链（FIX-416/418 纪律）延续。
- **archguard regen**：R1 `anchor_loc` 27213→27466 = verify_workflow.py 净 +253（+284/−31，V1 numstat 精确）；R4 `_run_full_engine_checks` 608→611（+3 = Check 42 盒三条净增打印行）与 total 1338→1341 一致；`git_head` 更新为当前 HEAD（V11）。baseline diff 仅这三值 + git_head，**无其他函数条目变动 = 零夹带**；manifest 仅 +1 新文件条目（V4/V9 独立计数），consistency PASS。

### ⑤ 判据不可平凡满足（验收钉子）— **成立**

`Check42DeferredSignalTests.test_fired_ledger_entries_feed_collector_and_zero_rate` 真实钉住全链：今日 fired 台账条目 → 采集器产出**恰 1 条** `deferred_registration` 事件（同 fixture 内 exempt 条目与 other-day 条目均被排除——负例可区分）→ `face_state["deferred_detections"]==1` → `session_closure_rate(...)["deferred_detections"]==1 ∧ rate==0.0 ∧ compliant==False` → `classify_observation_face` 返回 None（deferred>0 压制 SKIP）。生产侧前半链（guard 命中 → 台账落条目）由 `test_new_evd_row_with_word_fires_warn_issue_and_ledger` 独立钉住——两段合起来是完整「检测 → 台账 → 指标」链。红态复现（V8）证明该钉子在 HEAD 上必红（非恒真）。`session_closure_rate` 判定件（provenance_domain.py L412-469，FEAT-080 交付、本 diff 未触碰）的违规前置语义（deferred>0 → rate=0.0、compliant=False）与钉子断言一致。

### ⑥ 19 用例质量 — **实质成立；自报形态有偏差（F-P3-1）**

- **红→绿**：V8 独立复现 19/19 全红；V6 绿态 25/25（含 B3 既有 6 例无回归）。
- **无恒真断言**：全部断言比较具体值（fired 布尔、bucket 三元组、事件列表、计数、rate 浮点）；`test_regex_pool_word_pattern` 含负例（0.93 池不命中）。
- **无 mock 残留**：`mock.patch.object` 仅用于环境重定向（SAMPLE_PATH/GOVERNANCE_DIR 指向 temp gov——套件既有模式）与故障注入（detector-error 例，注入后显式验证还原 `assertEqual(lgp.judge_deferred_row, real)`）。
- **无测试间耦合**：每例独立 `_governance_temp_dir`；无类级共享可变状态。
- **偏差**：自报「ImportError×15/ValueError×8」与实测 8/7/4 不符（ValueError×4 若计入 B3 四处解包修订可解释为 8；ImportError×15 不可复算）——实质（19 全红、非恒真）不受影响，F-P3-1 记录。

### ⑦ 命名遮蔽 — **成立（零遮蔽）**

`infra/loop_gate_processor.py`（ADR-014 PARO 域）经**顶层** `import loop_gate_processor` / `from loop_gate_processor import …` 消费（loop_gate_processor.py L67、review_record.py L60、verify_workflow.py L7770/L18505、两测试文件）；新模块经**包限定** `from checks import loop_gate_processor`（verify_workflow L7361/L17669/L24233/L24511/L24869 + 新测试 15 处）。`checks/` 为正规包（`__init__.py` 实存）。Python 3 绝对导入下两个限定名是不同模块对象，顶层导入不进包目录、包限定无歧义——除非有人把 `checks/` 本身塞进 `sys.path`（全仓无此做法）。新模块 docstring L4-10 显式披露区分与「不激活任何 runtime」边界。

### ⑧ 边界外遗留（bootstrap 指标面）— **不影响本任务验收；存在同步缺口（F-P2-1）**

ADR §4 B4 批次行（L407）内容含「+ bootstrap 指标面」、§3.2.3 落点（L353）指名 `bootstrap_aggregate.py`（未锁，+~10 行）；triage `files` 边界仅两文件（verify_workflow.py + checks/loop_gate_processor.py），交付与 plan-tracker FEAT-081 行均未承载该子项。判定依据：§3.2.3 **验收判据 1-7 逐条不依赖 bootstrap 面**（判据 7 的判定面 = 「Check 42 输出即判定面」，已可用且 V5 活体验证）→ 不阻塞本任务验收。但 ADR 批次口径与实况的差若不落锚，是 CR-R1-1「Adopted 批次治理悬置」模式的微缩重现（NF-1 同型同步缺口）——处置建议见 F-P2-1。

### ⑨ 向后兼容与基线 — **成立**

- CLI 零变更：argparse 面 diff 0 行（V12）；`check_governance_write_shapes` 新增 kw-only 参数带缺省，全部既有调用点语义不变。
- `_collect_session_closure_events` 返回 2→3 元组：下划线内部 API，仓内全部消费点（Check 42 盒 + 4 处测试解包）已同步，全仓 grep 无遗漏。
- rel089 契约：converge/probe 零新工件（②表 + 负例测试 + V13 活体复核）。
- 基线不扩大：verify PASSED（V2）；check-governance 0 failing criterion、2 issues（1 untracked 过渡态 + 1 既有归档 WARN）（V5）。

---

## 3. 五维度 + AI 专项

| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | ✅ | 三件套对 ADR §3.2.1 直译（V14 逐词/逐标记核对）；边界全覆盖（空行/畸形 JSON/不可读 UTF-8/检测器异常→fail-closed 披露）；单写者 append-only，无并发面 |
| 安全性 | ✅ | stdlib-only（json/re）纯函数叶、永不反向 import 引擎；无 eval/注入面；台账路径固定 GOVERNANCE_DIR；无敏感数据 |
| 可维护性 | ✅（带 F-P3-2/3） | 模块 docstring 披露命名区分/规格消歧/纯度契约；词集与文案同文件（调优单点）；SKIP 分态推导存在双实现漂移风险 |
| 性能 | ✅ | 每新增行 12×str.find + 1 regex（微秒级，diff 窗口限域天然小面）；台账全量解析仅观察期、轮转策略见 F-P3-5 |
| 测试覆盖 | ✅ | 19 用例覆盖：词集正/负、窗口边界（7/8 字符双侧）、行族豁免、存量不追诉（验收 4）、正交性、rel089 负例、fail-closed、SKIP 三态、端到端链路（验收 1/2/3 形态）；红→绿独立复现 |

**AI 专项 5 项**：mock 残留 **无**（注入例还原验证在案）｜硬编码返回值 **无违规**（Check 42 vacuum 分支的 `skip_kind=vacuum` 字面量与分支条件值域一致——正确但宜用变量，随 F-P3-2 附注）｜幻觉 API **无**（模块 `__all__` 25 导出逐一实存于文件）｜未实现 TODO **无**｜过度实现 **无**（三件套/SKIP 分态均有 CR-R1-1/2 与 ADR 票面依据；`_stamp_deferred_observation` 的冗余度即 F-P3-2）。

---

## 4. Findings 分级（处置列 = Coordinator/Developer）

| # | 级别 | 位置 | 问题 | 处置建议 |
|---|------|------|------|---------|
| F-P2-1 | P2 | ADR-021 L407（B4 行）/ L353 vs 交付面 | 「bootstrap 指标面」（bootstrap_aggregate.py）为 ADR B4 批次内容但未随交付、triage files 边界未含、无承载锚——ADR 交付状态描述与实况同步缺口（NF-1 同型；不触发本任务验收 1-7） | 随 CR-R1-3 ADR 附录勘误 proposed 文本**一并改标**：B4 行注明「bootstrap 指标面拆出 B4′/显式推迟 + triage 承载锚」，或即刻入账后续任务——二选一，禁止悬置 |
| F-P3-1 | P3 | Developer 自报（红态形态描述） | 自报「ImportError×15/ValueError×8」与实测（8/7/4）不符；实质主张（19 全红→全绿）成立 | 返回文本/证据引用处更正为实测直方图，防证据链引用失真 |
| F-P3-2 | P3 | verify_workflow.py `_stamp_deferred_observation`（L24222-24250）vs loop_gate_processor.observation_face_record（L322-356） | SKIP 分态推导规则双实现（各自编码 detector_errors→fallback / fired→None / else vacuum，reason 文案两份）；当前 stamp 仅测试消费、台账记录自行重推导——可能静默漂移 | 收敛为单一事实源：stamp 改薄壳调用模块分类件，或 record 复用 stamped 值；顺带 vacuum 分支打印改用 `skip42["skip_kind"]` 变量 |
| F-P3-3 | P3 | verify_workflow.py `_judge_row_delta`（L24519-24521） | `rows_judged` 对所有受管面新增/变更行 +1 后才行族过滤——decision/review/ops 行也计入，vacuum reason 的「rows_judged=N」口径偏宽（fired/hits 不受影响） | 仅 scoped families 计数，或 reason 文案注明「含豁免行族」口径 |
| F-P3-4 | P3 | loop_gate_processor.deferred_events_from_entries（L298-319） | 一行多词命中 → 多条 fired 条目 → 多个同 id 事件 → deferred_detections 按词计数，而 face issue 按行 1 条；违规前置/compliant 语义不受影响（>0 即归零），仅计数口径与「检测数」字面有行/词粒度差 | 观察期后随 RT-5 数据回流统一口径（或同 id 事件去重）；翻转评审时一并裁定 |
| F-P3-5 | P3 | 台账文件生命周期（`.write-guard-deferred-ledger.jsonl`） | 每次 guard CLI 运行 append ≥1 条 observation_face（post-commit 每提交一条）+ 每命中一条 deferred_hit；无轮转/压缩策略，长观察期后 Check 42 每跑全量解析 | 随 WARN→FAIL 翻转决议一并声明台账生命周期（翻转后保留/归档/截断）；与 proposed RISK 联动 |

---

## 5. 对 proposed DEC-2xx（双向窗口）与 proposed RISK（观察期误报）的审查意见

**proposed DEC-2xx（否定语境窗口双向裁定）——支持写入，建议文本四要素**：
1. 引 ADR 双处原文（§3.2.1 L325「命中词前 8 个字符」；验收判据 3 L360 首例「'登记待以后'=违规」）实证矛盾——`=` 在词后，前缀臂不可达；
2. 记录最小性论证：prefix-only 违反判据 3 首例（V9 反事实）、suffix-only 违反第二例（`废除` 在词前）→ 前后各 8 字符 OR 臂是同时满足两例的最小窗；比全行扫描保守；
3. 勘误动作明确：§3.2.1 L325 与 §7 BC-3 L458 的「前 8 个字符」措辞同步改为「前后各 8 个字符」等效表述（两处同源，只改一处会留新矛盾）；
4. 与 RT-5 联动声明：台账第三键（否定语境命中）保留收紧数据，翻转评审时可评估收窄（如后缀臂限 `=`/`违规` 子集）。

**proposed RISK（观察期误报）——支持登记，建议文本三要素**：
1. 误报形态具体化：① 词面命中的固有 FP（如「留待复审」类正常表述）；② 窗口假豁免 FN（行内 8 字符内的 `=`/`废除` 指向他物时错误豁免——`=` 标记在表格行内的出现频率值得台账观察）；
2. 缓解链在案且应引用：WARN 姿态（DEFERRED_REGISTRATION_POSTURE="warn"，同 commit 改姿态 = 静默翻转，模块注释已禁）+ 三键台账 + 翻转前误报率报告义务（report→evidence→decision-log，summarize_ledger_buckets 已提供数据面）；
3. 风险参数：观察期长度定义（建议显式锚定版本窗）、误报率阈值预案、台账生命周期（对应 F-P3-5）。

---

## 6. 硬门槛自检

- [x] P0 = 0（自动计数）
- [x] 5 维度 100% 覆盖（§3 逐项有结论）
- [x] 每条发现标注级别（P2×1 / P3×5）
- [x] 设计一致性检查完成（ADR §3.2.1/§3.2.3/§2.4 L283-284/§4 B4 行逐条比对，见 §2）
- [x] AI 专项 5 项逐一有结论（§3 末段）
- [x] 每条结论有命令输出/diff 行号/文件引用支撑（§1 证据矩阵 + §2 行号）
- [x] 审查只读：未修改产品代码与 `.governance/`；报告为本文件；终态 `git status` 与起始一致（6 文件）
- [x] `unresolved_blockers = 0`（独立结构字段，APPROVED_WITH_NOTES 通过终态合法性）

## 7. 复审建议

无需 NEEDS_CHANGE 返工。F-P2-1 处置权在 Coordinator（ADR 勘误写回时一并改标或入账承载锚，属 CR-R1-3 同一批写回动作）；F-P3-1~5 为下一轮收口性质（可随观察期调优/翻转决议或邻近触票顺带清偿），不阻塞 commit。建议 commit message 引用 FEAT-081 与 CR-R1-1/2/3；commit 后 untracked 过渡态 WARN 自然消失。
