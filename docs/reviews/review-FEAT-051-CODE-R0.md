# REVIEW-FEAT-051-CODE-R0 — task-row-update 写入器（批 1 票 1）· 独立代码审查

- **任务 / 轮次**：FEAT-051（原 FEAT-042R）Code Review **R0**（2026-09-19）
- **审查者**：Code Reviewer Agent（独立子代理，只读审查；本报告为唯一落盘产物）
- **审查对象**（工作树未提交，两新文件；并行票文件 / governance_store / baseline_metadata / FEAT-053 版本面均出范围）：
  - `skills/software-project-governance/infra/task_row_update.py`（实测 **1,357 行**，Developer 申报 ~1,310——口径微差）
  - `skills/software-project-governance/infra/tests/test_task_row_update.py`（**36 测试方法**，与申报一致）
- **语义基准**：contracts.py m0-r1（只读消费核验）· arch round-2 §1（五步流程+组合并发）· round3 P1-1（契约消费）· evolution §4 机录写入器 DoD（编号 0~9）· version-plan §2 批 1 行
- **禁改声明**：本审查未修改任何代码与 `.governance/` 治理记录；复验中发生过一次由我引发的真表写入事故，已字节级回滚并全文披露（见 §六）。

---

## 总结论

| 项 | 值 |
|---|---|
| **总结论** | **NEEDS_CHANGE** |
| P0 / P1 / P2 / P3 | **0 / 1 / 3 / 7** |
| **unresolved_blockers** | **1**（P1-1） |
| 复审义务 | round 0 < 3 → Coordinator 按 T1 返工后重 spawn 本 Reviewer R1（注入本报告路径） |

阻断理由（单一 P1）：写入器每次翻转**静默丢弃状态 cell 的首尾空白**，违反 `build_candidate_row` 自身文档声称的「row 内其余字符 byte-for-byte 保留」不变量（详见 P1-1）。该模块的存在意义就是精准的受治理行手术；此项与本票 DoD 3「可靠落盘」及模块自声称不变量直接冲突，且修复面小，应当本轮修毕再入 R1 复审。其余面（五步流程/锁/CAS/锚定/幂等/恢复/CLI/测试质量）全部达标，36/36 实跑全绿。

---

## 零、声明勘误（审查基准事实核对）

1. **TASK_TRANSITIONS 是 11 条边，不是 12**。程序化复核：`sum(len(v) for v in TASK_TRANSITIONS.values()) = 11`（triaged 2 + dev 2 + review 3 + approved 1 + completed 1 + committed 0 + blocked 2）；七态确认。`task_row_update.py` L12 文档串「the 12-edge TASK_TRANSITIONS table」沿袭了上游失准（同见 `.governance/change-triage/FEAT-051.json` title 与 EVD-1105——后者出本票范围，提请 Coordinator 另行勘误）。→ P3-1。
2. **DoD 实为 0~9 十条**（evolution §4），票面与简报惯称「九条」。本报告按 0~9 逐条核验（§七）。
3. **凭证字段数**：实际落盘 receipt 为 **18 个顶层键**；`test_receipt_join_anchor_fields` 断言其中 **17 个 join 字段**（全部除 `writer_result`）。简报所称「字段 16 项」未在票面/规划文档中找到出处，按 17/18 实测口径验收——schema 完备性本身达标。

---

## 一、五步流程与锁策略（审查重点①）

**结论：忠实实现 round-2 §1，一处文档-实现错位（P2-3）。**

- 五步映射（L646-956）：①提交（CLI 三元组+typed refs）→ ②`_write_lock`（companion `<target>.lock`，Windows `msvcrt.locking LK_NBLCK` 有界退避 40 次/1.4^n 截断 10，POSIX `fcntl.flock LOCK_EX`）→ ③锁下重读+重校验（内容 CAS→锚定→状态 CAS）→ ④`build_candidate_row`+`_atomic_write`（commit point）→ ⑤锁下 receipt append + 写后重读自检 + 释放返回新 revision。
- **组合而非二选一** ✓：CAS（状态层+内容层）与短时锁并存；`LockContention` → `lock_contention`（retryable）永不降级无锁写 ✓（fail-closed，有测试 `test_lock_contention_is_retryable_never_unlocked`）。
- 语义与 round-2 §1「相同 operation_id 重试返回原结果；CAS 冲突不自动换版本执行」一致 ✓。
- **P2-3（文档-实现错位 + 竞态误报细节）**：`execute_update` docstring（L669-672）声称步骤③「under the lock: replay adjudication (ledger + fingerprint…)」，但实现中 replay/conflict 裁决在**取锁之前**（L762-792），锁下（L800-956）不再重读 ledger。后果：同一 operation_id 的两次**并发**执行，输家在锁下只做状态 CAS，看到行已在 `to_state` → 返回 `revision_conflict` 且 detail 附加「no receipt on record (effect_present_without_receipt…)」——而此时 receipt **已在** ledger。不损坏数据、调用方下次重试即自愈为 replay（裁决在锁前重跑会命中 receipt），但裁决文案误导人工对账，且文档与实现不符。建议：把 replay 裁决移入锁内（顺带修复竞态文案），或至少修正 docstring 并将该 hint 限定为「锁下未复查 ledger」语义。

## 二、CAS 双层（审查重点②）

**结论：达标。**

- 聚合 revision = 全文件 UTF-8 字节 SHA-256 前 64 位（`revision_of` L257-268）——「共享单文件锁保护重读+聚合版本」口径的忠实落地；确定性、无依赖、任一字节变化即变。
- 状态层 CAS：锚定行 detected state ≠ `from_state` → `revision_conflict` + observed_revision（L832-844）；已在目标态时附加 effect_present_without_receipt 对账指引（effect-based，不自动补造）✓。
- 内容层 CAS：`expected_revision` 与锁下新鲜观测比对（L812-819），冲突返回 observed、永不自动 rebases ✓（`test_content_cas_conflict_reports_observed_revision` 钉住）。
- 观测面 `inspect_target` 是 CAS 期望源（零写零锁）✓，`test_inspect_is_the_cas_expectation_source` 验证其输出可被内容 CAS 接受。
- 微瑕（P3-5 一部分）：`WriterRequest(expected_revision=… if not None else 1)`（L741）占位符无注释披露——request 对象仅作契约门，真实 CAS 走参数，建议加一行注释。

## 三、凭证 schema 完备性（审查重点③）

**结论：达标（WARN 姿态 + effect-first 窗口诚实披露均落实）。**

- receipt 18 键：record_kind/schema_version/writer/operation_id/task_id/from_state/to_state/reason/timestamp/target_file/revision_before/revision_after/row_before_sha256/row_after_sha256/input_fingerprint/evidence_refs/writer_result/enforcement——结构 join 锚所需字段齐备（17 join 字段有测试逐一断言）。
- `enforcement: "WARN"` 显式落盘（L901）✓——join 执法面留批 2.3 的披露合理。
- effect-first 窗口：`_append_receipt` 失败 → `manual_intervention` + `execution="succeeded"` + prose 披露已提交 revision（遵守 WriterResult 律：错误码不带 new_revision）→ **不自动补造 receipt**（L903-916；`test_receipt_append_failure_disclosed_not_forged` 钉住）✓——「replace 后 append 前崩溃 → effect_present_without_receipt 不自动补造」口径忠实。
- 同 op 异载荷 → `operation_id_conflict` 必带 observed_revision ✓；重试同 op 同载荷 → 原结果原样返回、世界零扰动（文件与 ledger 字节比对钉住，`test_same_operation_id_replays_idempotently`）✓。

## 四、锚定正确性（审查重点④）

**结论：B-1 根因机械化达标，schema v1 边界如实披露。**

- ID 列=视觉第 2 列（`split("|")` 索引 2，`_RECORD_FAMILY_ID_COLUMN`，L228-241 文档解释前导空元素）✓；`**` 粗体剥离 ✓；全等匹配（无词形扫描）→ 叙述 cell/依赖列表中的 id 永不劫持 ✓（`test_status_cell_only_detection_ignores_narrative`）。
- 歧义锚（多行同 id）→ `cross_record_violation` 拒绝猜测 ✓（`test_ambiguous_anchor_refused`）；零命中拒绝 ✓；`FEAT-051` 不锚定 `FEAT-0512` ✓（`test_word_boundary_anchoring`）。
- 词形词典：有序互斥链只扫状态 cell（最后非空 cell），首中即胜；未知 → fail-closed `schema_violation`（不猜）✓；`🔄 M-0 ✅` 复合形按锚定 span 换（L432-441）+ 拼接后同链复检（L447-455）拒绝歧义拼接 ✓（`test_synonym_form_refuses_ambiguous_splice`、`test_compound_dev_form_flips_via_anchored_span`）。
- 边界（记入 P3-6，非阻断）：(a) 全文件扫描锚定——plan-tracker 存在多张表，若他表第 2 视觉列出现同 id 且末 cell 恰为状态词形，将产生误锚或歧义拒绝（当前布局安全；建议 schema v2 做 section-scoped）；(b) 第 2 列之前出现转义管道 `\|` 会使朴素 split 索引右移 → 锚定失败（fail-closed 拒绝，非错写）；(c) 真表复核确认 live 标记为「✅ 完成」稀疏形，与 `STATE_CANONICAL_MARKERS["completed"]="✅ 完成"` 一致，走 canonical 替换路径。

## 五、幂等重放（审查重点⑤）

**结论：达标（同 op 同载荷世界零扰动实测；异载荷拒绝）。** 详见 §三；补充：replay 分支原样重建 WriterResult（code/new_revision/observed/execution 均取自 receipt.writer_result），ledger 只作裁决、世界重读为真相（effect-based ✓）。两处边角：**P2-2**（degenerate receipt → 未捕获 ContractViolation）与 **P2-3**（并发同 id 竞态文案误导）——见 findings。

## 六、原子写细节（审查重点⑥）

**结论：达标（一项 P1 例外——cell 空白丢失，见 P1-1）。**

- `mkstemp`（目标同目录，同卷 `os.replace` 原子）+ `fsync` + `os.replace`（L609-632）；`BaseException` 兜底清 temp ✓（`test_crash_point_leaves_no_temp_and_target_untouched`）；陈旧 `*.tmp` 清扫限定本目标前缀且在锁内执行（无并发误删窗口；注释「concurrent writer owns it」措辞与锁串行化事实略不符，纯注释问题）。
- 读写双侧 `newline=""`（无平移）；UTF-8 无 BOM ✓（`test_crlf_line_endings_preserved` 断言 CRLF 文件零裸 LF、`test_chinese_content_byte_fidelity` 断言无 BOM+未触行字节级不变）。
- **P3-4**：`os.replace` 后未 fsync 父目录（POSIX rename 持久性）——「commit point」表述略强于保证；开发站工具可接受，建议补 dir-fsync 或文档弱化。
- **P3-7**：`row_line_ending` 只认 `\r\n`/`\n`/`\r`（L959-964）——行若以 `\u2028` 等 Unicode 分隔符结尾会被吞并粘行。实测当前 tracker 无此类分隔符（本次复核 has_u2028/u0085/u2029/exotic = False），纯理论边角。

## 七、DoD 0~9 逐条核验（审查重点⑦）

| # | 条目 | 裁定 | 依据 |
|---|---|---|---|
| 0 | 模型输出不可信 | **达标（留 P2-1 缺口）** | 状态枚举/schema 窗口/typed refs/task_id strip 全 fail-closed；投影只输出闭集词形+op 后缀（无注入面）；唯一入参缺口=operation-id 形态未预检（P2-1） |
| 1 | 写前完整验证 | **达标** | 候选行先算后校验拼接（build_candidate_row 自校验）；schema+跨记录约束前置 |
| 2 | 幂等与冲突协议 | **达标** | 三值裁决+effect-based+同 ID 异载荷拒绝（red-trio 钉住）；P2-3 为并发文案边角 |
| 3 | 可靠落盘 | **P1-1 阻断** | 显式 UTF-8/同卷 temp/原子替换/平台声明 ✓——但 cell 首尾空白丢失违反行级 byte-fidelity 自声称不变量 |
| 4 | 写后重读自检 | **达标** | 同一 schema re-read（禁第二定义）；mismatch → manual_intervention（L918-949） |
| 5 | dry-run+结构化结果 | **达标（P3-2 微瑕）** | 四类 disposition 退出码 3/4/5/6 区分（测试逐一钉住）；dry-run 零写零锁实测 ✓；dry-run 与 execute 拒绝码一处不一致 |
| 6 | 恢复路径 | **达标** | temp 清扫/崩溃点测试 ×2/effect-first 窗口诚实披露不伪造凭证 |
| 7 | 守护测试 negative-control | **达标（1 覆盖缺口）** | 键碰撞/GBK ×2/缺行/重复执行 ×2/并发/崩溃点 ×2/特殊字符/legacy 全覆盖；**缺「翻转行字节最小 diff」negative-control**（有它 P1-1 当场红） |
| 8 | 渐进启用+降级 | **达标** | --inspect/--dry-run 渐进演练；kill-switch=本原子 CLI 自身；schema 窗口闭式拒写（新旧双向，`test_schema_version_window_refusal`） |
| 9 | 机器来源标记 | **达标** | 行面 `〔op-<32hex>〕` 后缀 + ledger 结构化 receipt（WARN 姿态披露；join 面留批 2.3 合理） |

## 八、dry-run/inspect 演示复核（审查重点⑧）

**结论：申报属实，已独立复演。** 我在真实 `.governance/plan-tracker.md` 上重跑：`--inspect FEAT-049`（found=true, state=completed, observed_revision 返回）+ `--dry-run --from completed --to committed`（`would_execute=true, writes_performed=0, lock_acquired=false`，SHA-256 前后一致，无 ledger/lock 产生）→ **零写入实证**。预览 row_after 正确呈现标记替换+op 后缀。

## 九、注册形态（审查重点⑨）

**结论：披露合理。** 零 `import verify_workflow`（ArchGuard R2 口径，测试 `test_composition_root_assembly_and_r2_cleanliness` 钉住源码断言）；stdlib-only + L0 contracts 叶；dotted-path `task_row_update.main` 组装点可解析（测试验证）；物理接线（engine dispatch 行）留批 2.0——与 governance_cost/bootstrap_aggregate 先例一致，交付报告披露而非静默假设 ✓。`--file` 默认 `.governance/plan-tracker.md`、缺文件 → validation 拒绝不创建 ✓。

## 十、AI 专项（审查重点⑩）

| 检查 | 结论 |
|---|---|
| mock 残留 | **无**——测试中 `mock.patch` 全部为故意的故障注入（os.replace/_append_receipt/_write_lock），产品代码零 mock |
| 硬编码返回值 | **无**——一切结果由真实计算/契约产出；STATE_CANONICAL_MARKERS 属合法校准表 |
| 幻觉 API | **无**——stdlib（msvcrt/fcntl/tempfile/os.replace/hashlib/json）与 contracts m0-r1 面签名逐一比对相符 |
| 未实现 TODO | **无**（全文无 TODO 残留） |
| 过度实现 | **无**——两文件面未越界；scope 声明（operation_id 全局生成/按 ledger 解析、schema_version CLI 载体）以 prose 披露批 2.0/2.1 归属，属合理边界而非超建 |

测试质量：36 测试结构清晰（5 组），Barrier 模式并发测试（12 线程恰 1 胜、败者全为 conflict+observed_revision、恰 1 receipt、胜者 new_revision==世界实测）设计正确且**单跑复验通过**；崩溃点注入（replace 失败/append 失败）双点覆盖；GBK 守护（BytesIO+GBK TextIOWrapper 包装 stdout 验证 reconfigure 后 UTF-8 输出可解析）真实有效。红相论证（illegal transition / CAS×2 / replay）齐备且每例断言零写入+零 receipt。

---

## 十一、Findings 清单

### P1-1（阻断本轮合并）— 翻转写入静默丢弃状态 cell 首尾空白
- **位置**：`task_row_update.py` L310-316（`_status_cell` 返回 `cells[index].strip()` 的**剥离后文本**）、L423-427（`build_candidate_row` 以该剥离文本为拼接基底）、L443（`candidate_cells[cell_index] = swapped`）、L456-461（op 后缀步骤在已剥离文本上 rstrip）。
- **事实依据（实证）**：对真实 tracker 一次真实翻转产生：原行「…零注入面 **| ✅ 完成 (2026-09-19)——…批 1 解锁 |**」（cell 前导 1 空格+尾随 1 空格）→ 写后「…零注入面 **|committed (2026-09-19)——…批 1 解锁 〔op-…〕|**」——首尾空白双双丢失。代码路径复读确认该行为**确定性**发生（strip 发生在拼接基底上，非检测局部）。
- **违反**：`build_candidate_row` docstring L396-399「Every other character of the row … preserved **byte-for-byte**, so the row-level diff is minimal and joinable」；本票 DoD 3 精神；P-v1 原则 7（不损坏数据——空白亦为受治理记录字节）。
- **影响**：每次翻转对受治理记录做未声明的额外改写；`row_after_sha256` 凭证忠实记录的是**降级后**的行；不破坏状态检测/锚定/join 语义（strip 对检测无影响），但「最小 diff」承诺失效。首次翻转后行处于剥离形态，后续翻转不再复利损伤。
- **修复建议**：`_status_cell` 返回**原始** cell 文本（strip 仅用于检测判定），或 `build_candidate_row` 在原始 cell 上按 pattern 偏移做 span 替换；补一条 negative-control：翻转行与原行的字节 diff 必须恰为「标记 span + op 后缀」（该测试可防复发，即 DoD 7 缺口）。

### P2-1 — 畸形 `--operation-id` 产生未捕获异常裸 traceback
- **位置**：L725（`operation_id` 无形态预检）、L747-748/L967-974（`_validation_result` 构造 `WriterResult` 时 `require_operation_id` 抛 `ContractViolation`，CLI 无捕获）。
- **实证**：`--operation-id bad-id` → `contracts.ContractViolation: WriterResult.operation_id: operation id 'bad-id' does not match …`，exit 1，无结构化结果。
- **影响**：用户输入路径的失败不可机读（违背 DoD 5 四类处置面）；fail-closed 方向正确、零写入。
- **修复**：进入流程前 `require_operation_id` → `schema_violation` 结构化拒绝（一行预检）。

### P2-2 — degenerate ledger receipt 使 replay 分支未捕获崩溃
- **位置**：L771-783：`WriterResult(code=prior.get("code", RESULT_OK), new_revision=prior.get("new_revision"), …)`——若 receipt 的 `writer_result` 缺失/损坏（如 code=ok 而 new_revision=None），`WriterResult.__post_init__` 抛 `ContractViolation` 未捕获。
- **触发面**：手工修补/部分损坏的 ledger 行（`_read_receipts` 对 JSON 语法容错、对语义不校验，其它字段损坏均能存活，唯独此分支炸出）。
- **修复**：构造前校验 `writer_result` 形态，不合法 → `manual_intervention`（与模块自身的 ledger 容错姿态对齐）。

### P2-3 — replay 裁决位置与五步文档错位 + 并发同 id 竞态误报文案
- **位置**：docstring L669-672 vs 实现 L762-792（裁决在锁前）；锁内无 ledger 复查。
- **后果**：并发同 id 竞态下败者收到带「no receipt on record (effect_present_without_receipt…)」hint 的 `revision_conflict`，而 receipt 实际在册——误导对账；下次重试自愈为 replay。零数据风险。
- **修复**：裁决移入锁内（一并修复文案），或修 docstring + 限定 hint 语义。

### P3（七项，不阻断）
1. **P3-1 文档失准**：「12 边」实为 **11 边**（L12 文档串；连带 triage JSON title 与 EVD-1105——后两者出票面，报 Coordinator 勘误）；「DoD 九条」实为 0~9 十条。
2. **P3-2 dry-run 拒绝码不一致**：歧义拼接行 dry-run 报 `cross_record_violation`（L1210-1211 对 `build_candidate_row` 的 ValueError 一并吞入）而 execute 报 `schema_violation`（L851-853）——实测确认（exit 同为 3）；且 `_dry_run` docstring「mirrors the execute path's checks in order」夸大（未预演 replay/conflict 裁决与 WriterRequest 门）。
3. **P3-3 POSIX 锁无界阻塞**：`fcntl.flock(LOCK_EX)` 阻塞式（L568-584），有界退避仅 Windows 侧；持锁者挂起 → POSIX 写入方无限等待。建议超时或文档明示平台不对称。
4. **P3-4 rename 持久性**：`os.replace` 后未 fsync 父目录（POSIX），断电窗口下 commit point 表述略强于保证。
5. **P3-5 命名/死码**：`RECEIFT_RECORD_KIND` 拼写（L170）；`TASK_ROW_UPDATE_RESULT_CODES["replay"]` 为不可达死映射（replay 实际返回 code="ok"，L1042-1057）；`_dry_run(refs=…)` 参数未使用（L1132-1143）；replay 判定耦合 prose 前缀 `"replay of operation"`（L1339）；WriterRequest 占位 `expected_revision=1`（L741）无注释。
6. **P3-6 schema v1 锚定边界**：全文件扫描（多表误锚/歧义拒绝风险，fail-closed）；转义管道在第 2 列前使 split 索引右移 → 拒绝（非错写）。建议 schema v2 section-scoped 锚定并文档化 \| 边界。
7. **P3-7 Unicode 行分隔符**：`row_line_ending` 不认 `\u2028` 等（L959-964）——理论边角（当前 tracker 实测无此类字符）。

---

## 十二、独立复验表

| # | 复验项 | 命令/方法 | 结果 |
|---|---|---|---|
| 1 | 36 套件实跑 | `python -m pytest …/tests/test_task_row_update.py -v` | **36 passed, 0.45s** ✓ |
| 2 | 真表 dry-run 复演 | `task_row_update.py --task FEAT-049 --inspect` + `--dry-run completed→committed`（真实 `.governance/plan-tracker.md`） | inspect found/state/revision ✓；dry-run `would_execute=true, writes=0, lock=false`，**SHA-256 前后一致，无 ledger/lock** ✓ |
| 3 | 并发测试单跑 | `pytest …::ConcurrencyTests::test_many_threads_one_winner_rest_conflict` | **1 passed** ✓（12 线程恰 1 胜） |
| + | 契约边数复核 | `sum(len(v) …) ` | **11 边**（勘误依据） |
| + | 畸形 op-id 探针 | CLI `--operation-id bad-id`（隔离 temp） | ContractViolation 裸 traceback，exit 1（P2-1 实证） |
| + | dry-run/execute 拒绝码探针 | 同一歧义拼接行双模式（隔离 temp） | `cross_record_violation` vs `schema_violation`（P3-2 实证） |
| 未复验（申报采信） | 契约+registry 存量 234 零回归；verify PASSED+archguard R1~R7（R2 47 站点零增/R6 Δ0） | 全仓门禁，超出本审 3 项复验预算；间接佐证：契约只读消费有测试钉、R2 洁净有源码断言测试 | 标记**未复验**（Developer 申报，非本审结论） |

## 十三、审查者事故披露（透明度义务）

复验第 2 项首次执行时**我漏带 `--dry-run` 旗标**，CLI 在真实 tracker 上执行了一次真实翻转（FEAT-049 completed→committed，op-d9c50d73f5804808beaf9fa80a160dad，ledger+lock 产生）。处置：

1. **取证**：读取 receipt（row_before_sha256 / revision_before）。
2. **字节级回滚**：以整行 SHA-256 暴力匹配锁定原始行内容（12 候选中唯一命中），内存中先验全文件聚合 revision == receipt.revision_before 后才落盘；ledger/lock 残留删除。
3. **事后独立复核**（Python 独立运行时）：当前 FEAT-049 行哈希 == receipt.row_before_sha256（`18cdc5b4dc02…`）——**还原字节级成立且经并发插入行扰动后依然完好**。
4. **副作用收益**：该事故顺带完成了一次真表端到端 execute 验证（锚定/转移/CAS/锁/ledger/GBK 全链工作正常）并实证了 P1-1。
5. **残留**：无。另记录：还原与复核之间有**并发写入者**向 tracker 插入 FEAT-047/FEAT-050 任务行（526→528 行；无 ledger/lock 痕迹）——非本审所为、未触及 FEAT-049 行字节，不属本票范围，仅登记供 Coordinator 知悉。

## 十四、R1 复审指引

1. 逐条核对本报告 findings：P1-1 必须修复（代码+新增字节最小 diff negative-control）；P2-1/P2-2/P2-3 建议同轮修复（改动面小）；P3 可遗留但须逐条给出来回（采纳/拒绝+理由/遗留计划）。
2. 重点回归：P1-1 修复后 `test_chinese_content_byte_fidelity`、`test_crlf_line_endings_preserved`、`test_special_characters_in_row_preserved` 必须仍绿，且新增测试应使翻转行 diff 恰为标记 span+后缀。
3. 复审时按角色协议在报告头部声明 R1 并引用本报告路径。

## 十五、边缘问题（供作者/Coordinator 答复，不阻断）

1. receipt 的 `target_file` 记录的是调用方传入路径原样（相对/绝对混用）——批 2.3 join 是否需要规范化口径。
2. ledger 无轮转/无界增长——round-2 BT-4 已登记审计非真相+archive 轮转，确认批 2.1 事件日志 slice 承接即可。
3. `--file` 相对路径依赖 CWD——composition root 接线时是否强制绝对化。
4. 简报「字段 16 项」「12 边」「DoD 九条」「~1,310 行」四处口径与实测（18 键/17 join 断言、11 边、0~9 十条、1,357 行）不符——建议交付报告口径勘误，避免下游票继承失准数字。

---
*审查完毕。本报告为 R0 唯一事实源；未修改任何代码；`.governance/` 净变更 = 0（事故已字节级回滚）。*
