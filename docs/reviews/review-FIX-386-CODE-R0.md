# review-FIX-386-CODE-R0 — 0.87 未承载遗留小项包（代码审查 · R0）

> **Round 声明**：R0（首轮审查，无前轮 REVIEW 报告可比对）。审查对象 = 工作树未 commit 修改：申报 5 文件 +115/−2，另含披露的第 6 文件（`test_loop_runtime_claims.py` 单行 pin 同步，1+/1−）。
>
> **审查方法**：逐行 diff 通读（5 文件全量）+ 关键函数全量阅读（`acquire_dispatch_locks` 全文 L769-959、`_markdown_units` locator 构造 L1914-1985、`test_former_46_locator_ledger` 消费逻辑 L997-1043）+ 6 项独立实测：① scanner 双版探针（git show HEAD 提取旧 ADR-011 字节流直喂引擎，新旧 locator 对拍）② 三套 pytest 串行实测（change_triage 95P / resolve_entry 24P / loop_runtime_claims 60P+79subtests+4F）③ test_governance_store 101P 对照 ④ LRC 引擎双模式实测（findings/units 逐条dump）⑤ verify 全量复跑 ⑥ 新旧账本 families/tests 计数 ConvertFrom-Json 对拍。实测临时脚本均写入 %TEMP% 并即用即删，审查全程未修改产品代码、未触碰 `.governance/`、未执行 git stash 类树变更操作。唯一输出 = 本报告。

---

## 0. 总结论

**NEEDS_CHANGE**（`unresolved_blockers=1`）

| 级别 | 计数 |
|------|------|
| P0 阻塞 | **0** |
| P1 关键 | **1**（F-1——唯一 BLOCKING） |
| P2 建议 | **0** |
| P3 讨论 | **4**（F-2 / F-3 / F-4 / F-5） |

P0=0：账本写回、双 ADR 勘正、两新增测试全部实测通过且证据链闭合；TOCTOU 归因经代码证据链证实无误。唯一 BLOCKING 是 F-1：第 6 文件（越界修改）的同步值错误且其必要性申报被实测证伪——若按现样合入，一条可证伪的「不修则 golden 测试必碎」叙述将随 commit message/证据链进入永久记录，且 golden ledger（测试名即 locator ledger）将携带一个指向空行的错误 locator。修复成本 = 1 行（或整文件回退），修复后 R1 复审预期零阻塞性工作。

机器可读行：`REVIEW-FIX-386-CODE-R0 | round=R0 | verdict=NEEDS_CHANGE | P0=0 | P1=1 | P2=0 | P3=4 | unresolved_blockers=1`

---

## 1. MUST 重点审查项逐项核验

### 1.1 账本写回正确性（env_failure_classification.json）— ✅ 通过

| 核验点 | 结果 | 证据 |
|---------|------|------|
| families 8→9 | 一致 | HEAD ConvertFrom-Json families=8/tests=19；工作树 families=9/tests=20；新家族 `clock_window_sensitive` 位于 L33 |
| tests 19→20 | 一致 | 新条目 `test_resolve_entry.ResolveEntryTests.test_snapshot_freshness_recent_is_fresh` L196-205 |
| JSON 有效性 | 通过 | `python -m json.tool` 零报错 |
| schema 一致性 | 通过 | 新条目字段集（class/family/count/evidence/since/resolved/resolved_by/ticket）与既有 resolved 条目（L124-133，FIX-330 先例）逐字段同形；co_causes/latent_* 为可选字段未滥用 |
| snapshot 头保留 | 通过 | diff 仅触及 families 与 tests 两节；L1-16 头部（schema_version/generated 2026-09-10/generated_by AUDIT-152/suite_summary head a599843）零改动；唯一「修改行」是 live_plan_tracker_row 尾逗号（JSON 语法适配，语义零变化） |
| evidence 链 | 闭合 | FIX-364 commit `9aa27a6` 存在（git show --stat：test_resolve_entry.py 1 file +95/−1）；EVD-1124（evidence-log L2448）原文含「AUDIT-152 账本 proposed 登记待 Developer 席写回」——与 ticket 字段引文逐字吻合；review-FIX-364-CODE-R0.md 存在；双午夜窗钉测试名实存（test_resolve_entry.py L297/L323）；「review-FEAT-054-RELEASE-R0 V10② in-window reproduction」引用属实（该报告 L43：01:30 时点 snapshot_fresh=False 午夜窗内同形复现） |
| 消费契约自洽 | 通过 | 条目为 resolved 保留态，与 maintenance 注记「update alongside data-evolution events」及 FIX-330 先例的「entry kept with resolution record」口径一致，不触发「registered id that passes => classification stale」的清理义务 |

### 1.2 ADR-011/012 勘误方式合规性 — ✅ 通过

- **历史结论零改写红线**：两文件 diff 为纯新增（ADR-011 +21/−0，ADR-012 +7/−0），零删改行——历史文本逐字节保留，勘误以 blockquote（文中就近注记）+ 文末 Errata 节（ADR-011）双层承载，符合「注记不改史」要求。
- **勘误覆盖完备性（穷举复核）**：ADR-011 全文 `300,000` 恰 4 处 = 2 处历史文本（L419 属 REVIEW-FIX-197-DESIGN-R2 resolution mapping 节〔节标题 L411〕、L528 属 Non-Functional Budget 节 extraction bullet〔节标题 L523〕）+ 2 处勘误自指（L422/L554）——Errata 节点名的两个位置恰好穷尽历史出现点，无漏网。ADR-012 全文恰 2 处 = L1196 历史文本（Performance 节）+ L1208 勘误自指——同口径穷尽。
- **provenance 指向有效性**：ADR-011 Errata 引用的 provenance 注释实存（loop_runtime_claims.py L225-243：FIX-369 注记 + `max_semantic_units: int = 361923`）；rollback-plan-0.87.0.md 与 feature-flags-0.87.0.md 均实存，后者 L26/L29 携带同一重定标叙述（300,000→361,923、B-9 回退通道）。
- **数值可复算**：ceil(301,602 × 1.2) = ceil(361,922.4) = 361,923 ✓（与引擎注释 L236 推导式逐字一致）。

### 1.3 两新增测试用例判别力 + 「预实现即绿」披露 — ✅ 通过（披露诚实）

- **真实机制零 mock**：函数级用例（test_change_triage.py L1382-1417）经 `_acquire`（L1237-1246）直调真实 `ct.acquire_dispatch_locks`（注入时钟 + 临时目录）；CLI 级用例（L1571-1604）经 `_run_cli`（L1513-1519）走**真实子进程** `verify_workflow.py agent-locks-acquire`。无 mock/patch/硬编码返回值。
- **判别力构成**（读产品代码逐路径对拍）：
  1. 冲突拒绝报文钉：拒绝分支（change_triage.py L889-891）报文含 `file lock conflict` 与 `locked_by FIX-001`——两断言均有真实对应物。
  2. 拒绝形状钉：成功路径才携带 `cross_check`/`warnings`/`written` 键（L949-958），拒绝路径为裸 error dict——三个 assertNotIn 钉住「拒绝面被 advisory 数据污染」的回归向量。
  3. 字节不变钉：函数级（L1414-1417）与 CLI 级（L1600-1604）均断言 agent-locks.json 字节级不变——钉住「拒绝时残留写」回归。函数级既有钉（L1361-1380）只做 JSON 语义级断言（locked_by 仍为 FIX-001），字节级为新增强度。
  4. 守卫排序钉（超出 docstring 自述的额外强度）：fixture 中 triage 独有文件 `product/triage_says_this.py` 不存在于磁盘——若 face-1 路径校验先于冲突守卫执行，将得到路径错误而非 file lock conflict，测试即红。隐式钉住守卫顺序。
- **预实现即绿披露核验**：属实且定性正确。本票 diff 无任何产品代码改动（仅测试+文档+JSON），新用例是对既有正确行为的组合特征钉（composition pins），非 TDD 红→绿。既有钉面共三层：L1188-1223（face-2 纯集合）、L1361-1380（函数级冲突守卫、无同日 triage 记录变量）、L1521/L1533（CLI 拒绝形状 + 成功 WARN 形状）——新用例补的是「冲突 × 同日 triage 记录错配」「CLI exit 2 × 字节不变」两个此前未钉的组合面。95 passed 实测含两新用例。
- **判定**：与 FIX-386 验收「acquire 互斥成立验证入账」的定位吻合——用例即互斥成立的可执行证明。披露无失实。

### 1.4 第 6 文件越界修改正当性（test_loop_runtime_claims.py）— ❌ 不成立 → F-1（P1 BLOCKING）

三重实测证伪申报理由，详见 §4 F-1。要点：

1. **「不修则 golden 测试必碎」为假**：`test_former_46_locator_ledger` 消费代码 L1028-1036 构造 expected Counter 时显式丢弃 locator（`for path, _locator, state, provenance in FORMER_46_GOLDEN`），actual 侧亦只按（path, state, provenance）三元组计数，断言为 assertGreaterEqual 最小计数（L1038-1043）——locator 列零消费。全仓 FORMER_46_GOLDEN 引用恰 4 处全在该测试文件内（L947/L1009/L1034/L1037），引擎与 verify 零消费。
2. **同步值本身错误**：scanner 实测探针（git show HEAD 提取旧版字节流 + 工作树新版分别直喂 `extract_semantic_units`）——旧版该段落发射 `clause:446:1/2/3`，新版发射 `clause:453:1/2/3`（实际位移 +7：mid-doc 注记 6 行引文 + 1 空行，与 hunk 头 −6/+13 一致）；新文件 L454 为空行，不产生任何语义单元。pin 写 `clause:454:3`、注释写 `shifted +8`——两值皆错。
3. **活体反证**：60 passed 实测轮中 golden 测试（携带错误 pin 454:3）通过——错误 pin 对测试结果零影响，反证该修改无必要。
4. **裁定**：不属 data-evolution 义务（无任何消费者会因不修而碎）；更优处置存在（改对 1 行或整文件回退，见 F-1 修复建议）。

### 1.5 TOCTOU 归因核实 — ✅ 通过（代码证据链完整）

| 主张 | 核验 | 证据 |
|------|------|------|
| acquire 写路径不持 _TargetLock | 证实 | `acquire_dispatch_locks`（change_triage.py L769-959）：L857-859 裸 `read_text` 读入 → L889-891 跨任务冲突拒绝 → L942-945 裸 `write_text` 写回；change_triage.py 全文件 grep `_TargetLock/msvcrt/fcntl/flock/lockf/portalocker` = 0 命中（连文件锁原语都不存在） |
| release/extend/amend 持锁 | 证实 | governance_store.py：L1679=`locks_extend`、L1800=`locks_amend`、L1903=`locks_release`，三者均 `with _TargetLock(governance_dir / LOCKS_FILE_NAME, ...)` |
| 并发丢失更新窗口成立 | 证实 | acquire 的读（L859）与写（L943）之间无互斥保护；持锁写方（release/extend/amend）与不持锁写方（acquire）对同一 agent-locks.json 构成非对称协作——acquire 读旧值后，持锁方提交变更，acquire 再整文件写回即抹除对方变更 |
| 现状串行派发不触发 | 接受 | 触发需同仓并发双进程派发/释放；现行 M7.6 串行派发 + worktree 隔离下不可达——P3 定级恰当 |
| 附带确认 | — | 跨任务互斥语义本身成立：冲突守卫（L880-891）在串行口径下有效拒绝，且由 1.3 的两新用例钉住——「互斥成立 + TOCTOU 并存」的申报框架与代码事实完全一致 |

审查者未独立复跑 stash 探针（审查只读纪律，不做树变更）；以「4 个失败测试的致因全部可归因到两个已 commit 的审查报告文件」替代佐证：LRC 引擎实测 findings 恰 2 条且均指向已提交文件（review-REL-086-RELEASE-R2.md 的 ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY = ragged row 驱动；review-FIX-376-CODE-R0.md 的 UNKNOWN_STATE_PREDICATE = 分类驱动），两文件均不在本票 diff 内——4 failed（inventory/performance 两测试 + FIX320 豁免账本双模式 SUBFAIL）与基线注两驱动逐一对上，与工作树 diff 无因果。

### 1.6 proposed risk-log entry 质量 — ✅ 方向成立（附 1 项登记义务 → F-5）

三要素评估：触发条件（并发 acquire 与持锁写方交错于同一 agent-locks.json）准确；缓解（现状串行派发纪律 + M7.6 worktree 隔离 + fail-closed 冲突拒绝面——后者现已由两新用例钉住）准确；可恢复性（agent-locks.json 为纯 JSON、丢失条目可重新 acquire、locks-release（FIX-370）可清退、Check 26 对 multi_lock_conflict/stale 有旗标检测）成立。修复候选归属 0.88 池恰当——同病同方的先例已存在：FIX-375 已把 locks-release re-apply 腿的 pre-read 移入 _TargetLock 堵并发（commit 04b7a42），acquire 侧同型修复（读入锁内或 acquire 纳入 _TargetLock 协作）可复用该模式。**一项义务**：风险登记必须交叉引用 RISK-046——其缓解列已登记遗留候选 F-2「读写竞态」（risk-log L42），新条目若不显式挂接将形成双条目重复（F-5）。

---

## 2. 五维度审查结论

| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | 通过（1 项 P1 例外） | 账本计数/条目/证据链、ADR 数值与覆盖穷举、两测试全部实测通过；TOCTOU 归因无误；例外 = F-1 pin 值错误 |
| 安全性 | 通过 | 无密钥/注入面；纯仓库内操作；fail-closed 语义未被削弱反而新增拒绝形状钉；无用户数据风险 |
| 可维护性 | 通过（F-1 计入） | 账本延续 maintenance 注记的数据演进纪律；ADR 勘误双层结构可追溯；新测试 docstring 引证 REVIEW-FIX-370 可溯源；例外 = F-1 在 golden ledger 注入失实注释 |
| 性能 | 通过 | 无运行时代码改动；LRC 预算余量实测 307,337 ≤ 361,923（余 54,586）；套件时长 26.55s/0.13s/271.21s 无恶化信号 |
| 测试覆盖 | 通过 | 新增组合面覆盖真实缺口（1.3 判别力构成）；基线 4 failed 与两驱动逐一归因；指定套件零新增失败 |

## 3. AI 代码专项 5 项检查

| 项 | 结论 | 证据 |
|----|------|------|
| mock 残留 | 无 | 两新用例走真实 API + 真实子进程（L1237-1246/L1513-1519）；diff 全文无 patch/mock 引入 |
| 硬编码返回值 | 无 | 断言对象均为真实函数返回结构与真实文件字节；无伪造输出 |
| 幻觉 API 调用 | 无 | 所调 API（acquire_dispatch_locks、agent-locks-acquire CLI、cross_check_triage_files）与所引文件（governance_store.py L1679/1800/1903 等）全部实存并经实测 |
| 未实现 TODO | 无 | diff 无 TODO/FIXME/NotImplemented（grep 实测 0 命中）；无半成品分支 |
| 过度实现 | 有 1 项 | F-1——第 6 文件属任务清单外的不必要修改（必要性理由失实）；两新增测试本身与验收面相称，不过度 |

## 4. 发现清单

### F-1（P1，BLOCKING）— 第 6 文件越界修改：必要性申报失实 + 同步值错误

- **位置**：`skills/software-project-governance/infra/tests/test_loop_runtime_claims.py` L951（pin `clause:454:3` 及行尾注释「shifted +8 by the mid-doc errata note」）。
- **级别理由**：行为情性（locator 无消费者、测试照常通过）本可 P2，但三重事实问题叠加且将随 commit 进入永久记录，按 P-v1 原则 1（基于事实、禁止编造）与交付叙述进入 commit message/证据链的既定路径，列为本轮必须处置的 BLOCKING。
- **事实依据**：
  1. 消费代码 L1028-1036 显式丢弃 `_locator`（expected/actual 两侧均不含 locator）——「不修则 golden 测试必碎」被代码直接证伪；全仓引用恰 4 处全在测试文件内。
  2. scanner 实测：旧版段落发射 clause:446:1/2/3，新版发射 clause:453:1/2/3（位移 +7 = 6 行引文 + 1 空行，hunk 头 −6/+13 互证）；L454 为空行零单元——pin 454:3 指向不存在单元，注释 +8 为错值。
  3. 实测活体反证：携带错误 pin 的 golden 测试在 60 passed 轮中通过。
- **影响**：golden ledger（名为 locator ledger）从此携带一个指向空行的权威样式错误 locator + 一条可证伪的机制注释；申报叙述若照录 commit message/证据将固化为永久失实记录；越界文件以失实理由进入任务面。
- **修复建议（二选一，均 1 分钟级）**：
  - (a) **推荐**：改为 `clause:453:3` 并将注释改为如实表述（例：文档性同步，locator 列不被测试消费；段落 446→453 实移 +7）；
  - (b) 整文件回退 HEAD（`git checkout HEAD -- skills/software-project-governance/infra/tests/test_loop_runtime_claims.py`）——最符合修改纯粹性（D4），保留旧 locator 作为未消费的陈旧文档零功能代价。
  - 无论 (a)/(b)：交付叙述（commit message/证据记录）**不得**再包含「不修则 golden 测试必碎」类失实理由，如实改述为「文档性同步（locator 列测试不消费）」或「越界修改撤回」。

### F-2（P3）— 47P 套件映射未定位

Developer 申报四套件 95P/24P/47P/60P+79subtests：前三套实测逐一对上（95P=change_triage 26.55s；24P=resolve_entry 0.13s；60P+79subtests=loop_runtime_claims 271.21s）。47P 无法在变更相关面定位（test_governance_store 实测为 101P）。建议交付记录补注套件全名；不影响结论。

### F-3（P3）— LRC units 计数 +1 窗口漂移

实测双模式 semantic_units = 307,337（申报 307,336）。+1 属活跃治理数据窗口噪声（账本/热表类活数据在两次测量间合法演进）；material 结论不变：findings 同 2 零新增命中 ✓、307,337 ≤ 361,923 预算 ✓。记录备查，无需动作。

### F-4（P3）— stash 探针未独立复跑的佐证口径

审查者以「失败致因→已提交文件归因 + LRC 引擎实测」替代 stash 复跑（见 1.5）；建议交付记录保留 Developer 的 stash 探针原始输出路径备查，使该佐证链可复查。

### F-5（P3）— 拟新增风险条目必须挂接 RISK-046 F-2

risk-log L42 RISK-046 缓解列已登记遗留候选「读写竞态」（FEAT-013 交付时的 F-1/F-2/F-4 候选清单）。FIX-386 的 TOCTOU 发现即该候选的代码级坐实——登记时 MUST 交叉引用 RISK-046（或直接以 RISK-046 候选更新承载），避免双条目；修复候选注记可引用 FIX-375 先例（pre-read 移入 _TargetLock，commit 04b7a42）与 0.88 池 FEAT-060/061 存储架构承载。

### 正面验证摘要（非发现，供 R1 复审判定基线）

账本 families 9/tests 20/JSON 有效/头保留/证据链四点闭合（9aa27a6 + EVD-1124 + 双审查报告 + V10②）；ADR 双文件纯新增、300,000 覆盖穷举、provenance 全部实存、ceil 推导正确；两新测试真实机制 + 四类判别面 + 95P 实测；TOCTOU 归因三段证据链（acquire 裸读裸写零锁原语 / 三写方持锁 / 丢失更新机制）；verify 复跑 PASSED exit 0；LRC findings 同 2 零新增、预算余量健康。

---

## 5. 硬门槛裁决

| 门槛项 | 裁决 |
|--------|------|
| P0 阻塞问题数 = 0 | ✓（P0 = 0） |
| 5 维度全覆盖 | ✓（§2 逐维有结论） |
| 每条发现标注级别 | ✓（F-1 P1；F-2~F-5 P3） |
| 设计一致性检查 | ✓（勘误方式符合「历史零改写」红线；账本写回符合 AUDIT-152 maintenance 契约；测试与 REVIEW-FIX-370 F-2 验收定位一致） |
| AI 专项 5 项检查 | ✓（§3 逐项有结论；过度实现 1 项 = F-1） |

## 6. 复审指引（R1）

R1 必做：①逐条比对 F-1——核验 pin 值（若保留第 6 文件，须为 clause:453:3 且注释如实；或文件已回退 HEAD）与交付叙述已去除失实理由；②F-5——风险登记面已挂接 RISK-046 或已声明登记方式；③F-2——47P 套件名已补注或如实标注未定位。F-3/F-4 仅备查。修复后预期 APPROVED 或 APPROVED_WITH_NOTES（unresolved_blockers=0）。

**输出物**：本报告（`docs/reviews/review-FIX-386-CODE-R0.md`，唯一输出文件）。审查者未修改任何被审文件、产品代码或 `.governance/` 记录。
