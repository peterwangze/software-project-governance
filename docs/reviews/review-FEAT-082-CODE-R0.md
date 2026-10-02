# FEAT-082 代码审查报告（CODE-R0）

| 项 | 值 |
|---|---|
| Task ID | FEAT-082（ADR-021 §3.2.3 B4′——governance-bootstrap behavior 面闭环率指标接线） |
| 审查轮 | R0（首轮） |
| 审查对象 | 工作树未提交 diff，恰 2 文件：`skills/software-project-governance/infra/bootstrap_aggregate.py`（+276）、`skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py`（+295），合计 +571 行（git diff --stat 实测） |
| 审查方式 | 独立复现——全部结论基于本 Reviewer 自行运行的命令输出、git diff 逐行取证与文件行号引用；未采信 Developer 自报（自报数字与本实测的差异在 §三.6/§三.7 与 F-P3-4/F-P3-5 如实记录） |
| 审查日期 | 2026-10-02 |
| 报告路径 | docs/reviews/review-FEAT-082-CODE-R0.md |

## 一、结论摘要

**审查结论：`APPROVED_WITH_NOTES`**

**unresolved_blockers = 0**

- P0（阻塞）= 0；P1（关键）= 0；P2（建议）= 0；P3（讨论/备注）= 5（§五）。
- 硬门槛：P0 计数 0 ✅；5 维度 100% 覆盖（§四）✅；每条发现带级别与位置 ✅；设计一致性（vs ADR-021 §3.2.3）已完成 ✅；AI 专项 5 项全部完成 ✅。
- 一句话裁决：交付主张全部经独立复核成立——判定口径经函数局部导入单源复用（`provenance_domain.session_closure_rate` + `loop_gate_processor.classify_observation_face`），采集层为披露镜像且 `SessionClosureMirrorTests` 双向差分真实有效（本审查另行注入漂移实证其敏感性），活体 `behavior.session_closure` 数值与 check-governance 的 Check 42 面逐字段同核，输出预算/锁纪律/健康诚实契约全部通过。5 条 P3 备注均为非阻塞改进项与披露口径修正。

## 二、独立复跑证据矩阵

全部命令由 Code Reviewer 本人在审查会话内独立运行（workdir = 插件仓库根；测试套件 workdir = `skills/software-project-governance/infra`，串行隔离，无并行 git 操作）：

| # | 命令 | 结果 | 关键数字 |
|---|------|------|---------|
| 1 | `git status --porcelain=v1` + `git diff --stat` | PASS | 恰 2 文件 M，与 TRIAGE-FEAT-082 `files` 边界一致；+276/+295=+571 insertions, 0 deletions |
| 2 | `verify_workflow.py check-cross-references` | PASS (exit 0) | 77 files / 728 refs；0 dangling / 0 deprecated / 0 circular |
| 3 | `verify_workflow.py check-manifest-consistency` | PASS (exit 0) | canonical 999 / actual 1174（canonical 子集口径，一致） |
| 4 | `verify_workflow.py check-injection-budget` | PASSED (exit 0) | resident 4207 ≤ 6000 tok；m2-discovery-closure 条款 active（worst surface 171 tok）；MAX_JSON_BYTES=8192 enforcer 在位；无超预算面 |
| 5 | `python -m unittest tests.test_bootstrap_aggregate` | **55/55 OK** (1.14s, exit 0) | 13 个新用例（SessionClosureFaceTests 8 + SessionClosureAggregateTests 3 + SessionClosureMirrorTests 2）全部 ok、零 skip |
| 6 | `python -m unittest tests.test_verify_workflow` | **Ran 1044 tests, OK** (431.4s, exit 0) | 0 FAIL；摘要无 skip 标记；跑后 `git status` 复查工作树仍恰 2 文件 M（测试产物自清理，零残留） |
| 7 | `verify_workflow.py governance-bootstrap --format json`（活体） | PASS | 投影 5377 字节（cmd 原始重定向实测）≤ 8192；`_enforce_projection_budget` 未触发（无裁剪 notes）；duration_ms=13 / budget_ms=3000；behavior 面恰 8 键 = 既有 7 + `session_closure`；子面 464 字节 |
| 8 | `verify_workflow.py governance-bootstrap --format text`（活体） | PASS | 17 行 ≤ 40；`session-closure: rate 0% closed 0/1 deferred 0 \| window=daily-aggregate（…）` 恰 1 行、紧随 behavior 行（FEAT-040 惯例） |
| 9 | `verify_workflow.py check-governance` | ISSUES FOUND — **3 issue(s)**, FAIL 行数=0 (exit 0) | 3 issues 为既有基线项（DEC-ID gaps [3,24,141,142,178] / ADR-RB-2 宿主激活前置 / archive integrity 1 项）；输出全文零 `bootstrap_aggregate` 相关警戒行（module_size/function_size 列表均不含）——**未因本 diff 扩大** |
| 10 | check-governance 输出中 Check 42 面提取 | 见 §三.6 | problems raised: 1; closed: 0; rate: 0%; deferred detections: 0; unclosed: RISK-062; window=daily-aggregate |
| 11 | `verify_workflow.py`（verify 全套） | **PASSED** (exit 0) | 全套绿 |
| 12 | 差分敏感性注入实验（临时目录 + 进程内 `ba._RISK_TERMINAL_WORDS` 注入漂移，零仓库写入） | 实证有效 | 基线：镜像三元组 == 引擎（closure 事件在）；注入词集漂移后：镜像 ≠ 引擎（closure 事件丢失）→ `SessionClosureMirrorTests` 必红——差分守护非恒真 |

## 三、十核查点逐项结果

### 1. 键位裁定（behavior.session_closure 嵌套子面）——**成立（测试断言为弱形态，见 F-P3-2b）**

- 活体 JSON 实测 behavior 面键集：`profile, source, env_var, plan_tracker_key, reverted, invariants, invalid, session_closure`——恰 1 个新增键，为嵌套子面（命令 7）。
- `_build_payload` 接线（bootstrap_aggregate.py L1017-1028）：仅在既有 `payload["behavior"]` 上追加 `session_closure` 一键；`_behavior().behavior_face(...)` 调用（L1015-1016）零改动。
- 平键归属未受侵入：`behavior_profile.py` 不在 diff 内（git status 恰 2 文件）；FEAT-040 平键契约（7 键）活体复核在位。
- 测试断言：`test_behavior_face_gains_closure_subface`（test L1026-1043）对 7 个既有键做存在性断言 + `session_closure` 数值断言——是「既有键仍在」而非「既有键值不变」的严格形态；「零变更」由 diff 事实（仅追加）+ behavior_profile 零改动支撑。弱形态记录为 F-P3-2b。

### 2. 单源导入纪律——**成立**

- 判定口径导入：`session_closure_face`（bootstrap_aggregate.py L757-）内部 `from checks.provenance_domain import session_closure_rate` + `from checks.loop_gate_processor import classify_observation_face`（函数局部，L774-775）——率值/违规前置归零/compliant/SKIP 分态全部来自导入件，镜像内无私自重算（`_format_session_closure_line` 仅做 `%.0f%%` 格式化，非重算）。
- `provenance_domain.session_closure_rate`（provenance_domain.py L412-469）与 `loop_gate_processor.classify_observation_face`（loop_gate_processor.py L359-389）均实存、纯函数（本 Reviewer 逐行读过定义——非幻觉 API）。
- ModuleDisciplineTests 新红线（test diff，L825-833）：逐行检查 `bootstrap_aggregate.py` 行首（无缩进）`import `/`from ` 语句不得含 `checks.`——语义正确：函数局部导入带缩进不会命中；模块级导入面实测仍为 stdlib + `resolve_entry` + `task_priority`（L78-90），与 `_behavior()` 的 R6 先例（L99-112）同型。
- 台账 JSONL 形状单源：`_closure_ledger_events` 复用 `parse_ledger_line` / `deferred_events_from_entries` 导入（L659-662）；测试 fixture 侧 `_ledger_line` 也经 `build_ledger_entry`（形状源自单源，test L904-914）——无第二形状源（F-P3-2 教训的对立面成立）。

### 3. 镜像差分测试质量——**成立（fixture 覆盖两臂缺口，见 F-P3-2a）**

- **真实双向**：`SessionClosureMirrorTests.test_collector_matches_engine_on_every_fixture`（test L1079-）对每个 fixture 树同时跑 `ba._collect_session_closure_events(gov, today)`（镜像）与 `vw._collect_session_closure_events(governance_dir=gov, today=today)`（引擎，经 `_import_engine` 真实导入，本审查复跑 13 用例零 skip），断言三元组 `(events, window_note, face_state)` 相等——是「镜像 vs 引擎」两个独立实现的差分，非同函数自比。
- **第二向**：`test_face_numbers_equal_check42_judgment_on_same_tree`——face 数值 vs「引擎采集 → 导入判定件」的 Check 42 判定，逐字段（skip_kind/rate/deferred/raised/closed/compliant）相等；fallback 态 face 数值置 None 故 `continue` 跳过数值比对（skip_kind 仍比对）——与 Check 42 自身 fallback 分支不打印率值的行为对齐（verify_workflow.py L17681-17687）。
- **7 fixture 覆盖**：full / partial / deferred（fired+exempt 混合）/ malformed（损坏台账→anomaly）/ snapshot-session / snapshot-stale / vacuum——含 fallback、损坏台账、真空、豁免负例、双窗口态。
- **敏感性实证**（本审查命令 12）：进程内注入 `_RISK_TERMINAL_WORDS` 漂移 → 镜像三元组 ≠ 引擎（closure 事件丢失）→ 差分测试必红。守护非恒真。
- 缺口：`ledger_read`（台账存在但不可读）与 `row_read`（evidence/risk 不可读）两臂无 fixture——这两臂镜像与引擎为代码审读一致（镜像 L654-694 vs 引擎 L7339-7379/L7414-7467 逐行比对，异常构造与优先级 `ledger_anomaly 优先、row_read 次之` 完全一致），但无差分钉子（跨平台权限故障构造不稳定是合理动机）。F-P3-2a。

### 4. 口径完整性——**成立（window_note 截断见 F-P3-3）**

- SKIP 分态：经 `classify_observation_face` 单源——anomaly→`orchestration_fallback`、双零→`vacuum`、否则 None（loop_gate_processor.py L359-389）；测试 `test_vacuum_skip_kind_when_nothing_to_observe` + `test_orchestration_fallback_nulls_metrics_and_discloses` 钉住。
- 按日聚合降级标注：`window_note` 全文含「按日聚合，同日多会话合并，精度降级……禁止无标注的静默降级，ADR-021 §3.2.3 / §2.4 L4」（bootstrap_aggregate.py L741-746，与引擎 L7478-7482 同文本）；测试断言 `按日聚合`+`精度降级` 在。**注意**：`_clip(window_note, 96)` 使活体输出在「ADR-021 §3.…」处截断（核心降级语义保留、ADR 引用残缺）——F-P3-3。
- deferred>0 恒不 SKIP：`classify` 的 else-None 分支 + `test_deferred_detection_zeroes_rate_and_never_skips`（deferred=1 → skip_kind None）。
- fallback 态指标置 None + anomaly 披露：face.update 五字段全 None + `anomaly:{kind,reason}`（L792-805）；测试逐字段 IsNone + `anomaly.kind=="ledger_parse"`。不把缺失当真空（CR-R1-2）：classify 的 anomaly 分支优先于双零真空分支（单源保证）。

### 5. health.state="deferred" 语义——**成立**

- face 自带 `source` 字段：`"check-42-caliber metric (FEAT-082 / ADR-021 §3.2.3 B4′); projection only — health checks NOT run"`（活体输出实测在）。
- `_health_face()` 独立未动；测试 `test_behavior_face_gains_closure_subface` 断言 `payload["health"]["state"]=="deferred"` 且 `pending_checks` 含 `check-governance`；活体 JSON `health.state == "deferred"`（命令 7）。指标呈现不冒充健康检查已执行。

### 6. 输出预算——**成立（Developer 主张 4404 与实测 5377 的差异归因见 F-P3-4）**

- 独立实测：JSON 投影 5377 字节（cmd 原始 stdout 重定向，排除 pwsh 管道编码因素）≤ MAX_JSON_BYTES=8192（bootstrap_aggregate.py L96）；`_enforce_projection_budget`（L1144-1204）未触发（活体无裁剪 notes）；session_closure 子面 464 字节；duration_ms=13/3000。text 面 17 行 ≤ 40。
- 与主张 4404 的差异（+973B）：两时点 .governance 数据面不同（活体投影含 next_actions/risks/recent 等随治理数据演进而变化的面）——口径差异非代码缺陷；核心判据（≤8192、无裁剪、子面量级 ~0.5KB）两者结论一致。

### 7. 基线披露（check-governance）——**成立（「早时 2」无法复现，如实记录）**

- 本审查实测：`ISSUES FOUND — 3 issue(s)`，FAIL=0（命令 9）。3 个 issue 全部为既有基线项，输出全文零 `bootstrap_aggregate` 警戒行（module_size/function_size WARN 列表为 archive.py/closure_chain.py/dsh_compat.py/governance_store.py/loop_gate_processor.py 等，不含本文件）——**+276 行未触发任何新警戒，基线未扩大**，与 Developer 主张 3→3 一致。
- 「会话早时摘要显示 2」：本审查无法在本会话重演早时状态。归因判断：摘要计数（如活跃风险/热数据面）与 check-governance issue 计数是**两个口径**——早时（RISK-062 于 2026-10-02 FEAT-081 审查闭环时登记）之前活跃风险计数为 2 是自洽解释之一。无法进一步确证，如实记录；该差异与本 diff 无因果（引擎不导入 bootstrap_aggregate，check-governance 的 issue 计数路径不含本文件任何面）。

### 8. 回归可信性——**成立**

- `tests.test_bootstrap_aggregate`：**55/55 OK**（串行隔离复跑，1.14s）——Developer 披露的「首次 1F 系并行 git stash 时序干扰」在干净复跑下不复现，最终结论与本实测一致。
- `tests.test_verify_workflow`：**Ran 1044 tests, OK**（431.4s）。
- 「1044+139」中的 **139 无法从本审查复现对上**（本机运行摘要为 `OK` 无 skip 标记）——1044 吻合；139 的出处（可能为 -v 子集计数或 Developer 环境特有 skip）待 Developer 澄清，不影响通过判定。F-P3-5。

### 9. +276 行 vs ADR「+~10 行」超估归因——**归因成立；锁边界内无更小的合规实现**

- ADR-021 L355 估算「bootstrap_aggregate.py ≈ 10 行」的隐含假设是「bootstrap 只呈现已算好的指标」；但 governance-bootstrap **禁导入引擎**（ArchGuard R2——模块 docstring L67-71 明示 + ModuleDisciplineTests 既有红线 `assertNotIn("import verify_workflow")`），且本命令自身不跑 Check 42、无已算数值可读——要呈现率值必须自行采集数据（evidence/risk/ledger/snapshot 四源，L605-755 三臂+编排 ≈240 行）再调导入的判定件。
- 更小合规实现排查：a) 提取采集纯函数入 `checks/` 供双端导入——需改 verify_workflow.py（本票 triage files 两文件**锁外**，越锁禁止；正是 proposed 接口需求的标的，见 §六.3）；b) 子进程调引擎——`test_module_never_spawns_subprocesses_or_writes` 既有红线禁止；c) 只呈现 SKIP 不呈现数值——违背 ADR L353「当会话有新增问题时输出率值」。
- 结论：+276 是 R2/R6 架构约束 + 本票锁边界的必然成本；+295 测试为守护成本（7-fixture 双向差分 + 13 用例）。ADR 估算低估——建议随接口需求票做附录勘误（FEAT-081 CR-R1-3 先例）。

### 10. 锁纪律——**成立**

- `git status --porcelain` 实测恰 2 文件 M，与 TRIAGE-FEAT-082 `files` 完全一致（命令 1）。
- `verify_workflow.py` / `checks/loop_gate_processor.py` / `checks/provenance_domain.py` / `behavior_profile.py` / `checks/*` 零改动（diff 范围实证）。审查过程本 Reviewer 零产品代码修改、零 .governance 写入（唯一输出为本报告文件）。

## 四、五维度审查 + AI 专项

| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | ✅ 通过 | 镜像三臂与引擎逐行比对一致（§三.3）；活体数值与 Check 42 同核且与手工复算吻合（当日 evidence/risk 行独立复算：REVIEW-FEAT-081-R0=APPROVED_WITH_NOTES→closure(FEAT-081)、EVD-1292 ✅→closure(RISK-044)、EVD-1293 ✅→closure(FEAT-081)、RISK-062 今日新行无终局词→唯一 problem→rate 0/1=0.0、台账零 fired→deferred 0——与 face 实测 rate=0.0/raised=1/closed=0/deferred=0 完全一致）；边界（空文件/缺文件/坏行/越窗口行）全部处理（missing ledger=vacuum、bad line=anomaly 且坏行前条目仍计入）；无并发面（只读单进程） |
| 安全性 | ✅ 通过 | 只读（零 .governance/git 写、零 subprocess——测试红线钉住）；无注入面（无 SQL/命令拼接；JSON 输出经标准序列化）；异常消息经 `_clip` 限长（96）防日志膨胀；无敏感数据硬编码 |
| 可维护性 | ✅ 通过（带 P3） | 判定单源 + 披露镜像 + standing 差分的分工在模块注释（L584-600）与 docstring 明示；函数长度均 <50 行（最长 `session_closure_face` ≈52 行含 docstring）；镜像常量漂移风险有差分守护；字面量判等小瑕疵 F-P3-1 |
| 性能 | ✅ 通过 | 活体 duration_ms=13/3000；每源一次全文读 + O(n) 行扫描（与引擎 Check 42 同量级成本面）；预算检查 per-section（`behavior.session_closure` 独立 check_budget，耗尽入 deferred 披露，L1021-1026 与既有段同型） |
| 测试覆盖 | ✅ 通过（带 P3） | 核心路径（正常/部分/违规前置/豁免/真空/fallback）、边界（越窗行/坏台账/缺 snapshot）、错误路径（读失败→anomaly）、端到端（payload 接线/文本行/预算耗尽）全覆盖；差分双向 + 敏感性实证；两臂 read-failure fixture 缺口 F-P3-2a |

**AI 专项 5 项**：mock 残留 **无**（新测试零 mock——全部真文件真函数真引擎导入）｜硬编码返回值 **无违规**（1 处字面量判等附注 → F-P3-1）｜幻觉 API **无**（4 个导入符号 + 测试侧 `build_ledger_entry` 逐一实存复核）｜未实现 TODO **无**（diff 内零 TODO/FIXME/占位 pass）｜过度实现 **无**（+276 有结构归因 §三.9；10 叶键各有 ADR/CR/诚实契约依据；`window`+`window_note` 双键为消费者便利的派生摘要，可接受）。

## 五、Findings（P3 × 5，全部非阻塞）

| # | 级别 | 位置 | 问题 | 建议 |
|---|------|------|------|------|
| F-P3-1 | P3 | bootstrap_aggregate.py L792 | `session_closure_face` 内 fallback 判等用字符串字面量 `"orchestration_fallback"`，未复用同模块已局部导入的 `loop_gate_processor.SKIP_ORCHESTRATION_FALLBACK` 常量——常量重构时判等失配（失配会被差分测试 `test_face_numbers_equal_check42_judgment_on_same_tree` 的 skip_kind 比对抓红，有守护兜底，故仅 P3） | 后续票改用导入常量（与 FEAT-081 R0 对 Check 42 vacuum 字面量的附注同型） |
| F-P3-2 | P3 | test_bootstrap_aggregate.py L868-881（variants）、L1026-1043 | a) 差分 7-fixture 未覆盖 `ledger_read`（台账不可读）与 `row_read`（evidence/risk 不可读）两臂——镜像逻辑与引擎代码审读一致但无差分钉子（跨平台权限故障构造不稳定是合理动机）；b) 既有键为存在性断言（assertIn）非键集合相等，「新增键 only」的严格形态缺直接断言（当前由 diff 事实+behavior_profile 零改动支撑） | a) 后续以注入式 read 失败（如临时替换 `read_text` 抛 OSError）补两臂差分，或在测试 docstring 披露该缺口；b) 可升级为键集合相等断言 |
| F-P3-3 | P3 | bootstrap_aggregate.py L783/785/798 | `window_note`/`skip_reason`/anomaly reason 统一 `_clip(…, 96)`——按日聚合降级标注全文在 96 字符处截断（活体输出止于「ADR-021 §3.…」）：核心降级语义（按日聚合/精度降级/静默降级禁令关键词）保留、测试断言通过，但 ADR L351 要求的显式标注文本引用残缺 | 对 window_note 单独放宽 clip 上限（如 160）或将 ADR 引用前置——后续小修 |
| F-P3-4 | P3 | 报告口径 | Developer 主张投影 4404 字节 vs 本审查实测 5377（两者均 ≤8192、均无裁剪触发）——活体输出随 .governance 数据面（今日 evidence/risk/snapshot 等）在两测量时点间演进所致；非缺陷，但以本审查实测为准 | 无代码动作；后续交付报告引用字节数时注明测量时点 |
| F-P3-5 | P3 | 披露口径 | Developer 披露「test_verify_workflow 1044+139」中 139 无法从本审查复现（本机 `Ran 1044 tests / OK` 无 skip 标记）；1044 吻合 | Developer 澄清 139 出处（-v 子集计数/特定环境 skip）；不影响通过判定 |

## 六、对 proposed DEC / RISK / 接口需求的审查意见

### 6.1 proposed DEC（键位裁定：behavior.session_closure 嵌套子面而非平键）——**支持入账**

1. behavior 面既有 7 键是 FEAT-040 灰度开关的稳定消费契约（`_behavior().behavior_face` 单源生成），追加平键会使该面语义从「灰度开关」漂移为「开关+指标杂烩」；
2. 嵌套子面使指标的删除/演进不触碰灰度键集（本票实测：budget 耗尽时 `session_closure` 整键缺席、灰度 7 键完好——`test_zero_budget_defers_the_closure_section`）；
3. ADR L353「behavior 面追加该指标」的机器形态落在嵌套子面上与「追加」语义一致。
**附带条件**：DEC 文本应写明先例性质——「behavior 平键集 = FEAT-040 契约冻结面；后续追加指标一律嵌套子面」——使其成为可扩展裁定而非孤例；并引用本报告 §三.1 证据。

### 6.2 proposed RISK（采集镜像漂移——差分测试守护）——**支持登记**

1. 漂移面客观存在：2 个镜像字面常量（`_CLOSURE_LEDGER_FILENAME` L149 / `_RISK_TERMINAL_WORDS` L150）+ 三臂行扫描逻辑（L605-694）共 ~150 行与引擎双实现（F-P3-2 教训的受控重现）；
2. 守护实测有效：standing 差分测试 + 本审查注入漂移实证必红（§二 命令 12）；
3. 风险登记应注明：缓解=SessionClosureMirrorTests 双向差分（含引擎侧 `_import_engine` skip 时的披露语义）+ 收敛路径=§6.3 接口需求票；与 RISK-062（词集误报/漏报观察期）同域不同面，**不应合并登记**（一个守检测词集质量、一个守镜像形状一致）。

### 6.3 proposed 接口需求（提取采集纯函数入 checks/ 统一双端）——**支持，建议 0.94.0 候选池**

1. 根治手段正确：将引擎 `_collect_session_closure_events`（verify_workflow.py L7382-7487）及其三臂下沉为 `checks/` 纯叶子（如 `checks/closure_collection.py`），引擎与 bootstrap 双端导入——彻底消灭双实现与差分守护负担（差分测试可降级为「双端调用同函数」的存在性断言）；
2. 合规性核查通过：`checks/*` 是引擎无关纯叶子，bootstrap 函数局部导入 checks.* 已有本票先例（判定件导入），不违反 R2（反向边禁令针对引擎）与 R6（cold-load 面）；
3. 前置条件如实入账：需改 verify_workflow.py + checks/（锁外新票）+ FEAT-081 的 19 用例与 FEAT-082 的 13 用例回归 + ADR L355「+~10 行」估算的附录勘误（§三.9 归因）随票入账——适合作独立 triage 票，不阻塞本票。

## 七、复审建议

- 本轮结论为通过终态（APPROVED_WITH_NOTES，unresolved_blockers=0），无需 R1 复审。
- 5 条 P3 的处置建议：F-P3-1/F-P3-2/F-P3-3 可并入 §6.3 接口需求票或后续小修票（非本票返工理由）；F-P3-4/F-P3-5 为披露口径修正（Developer 后续报告注明测量时点与 139 出处即可）。
- Coordinator 机录时请携带本报告结构化字段：`verdict=APPROVED_WITH_NOTES`、`unresolved_blockers=0`、`round=0`。

（审查依据：git diff 两文件全文、bootstrap_aggregate.py / test_bootstrap_aggregate.py / verify_workflow.py L7336-7487 与 L17655-17708 / checks/provenance_domain.py L412-469 / checks/loop_gate_processor.py L296-415 / ADR-021-meta-mechanisms.md §3.2.3 L337-368 / TRIAGE-FEAT-082 / review-FEAT-081-CODE-R0 F-P3-2；全部命令输出见 §二。）
