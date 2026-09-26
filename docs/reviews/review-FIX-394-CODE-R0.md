# Review FIX-394 — CODE R0（后置代码审查：终态行文本刷新机制 + 13 行一次性对齐工具面）

- **Task**: FIX-394（0.89.0 批次一第二票；前置 FIX-393 已集成 commit 8a94d64——三解析器判据）｜ **优先级**: P2
- **Round**: R0（首轮独立审查；无前轮 findings）
- **审查对象**: staged diff（`git diff --cached`，2 文件，+1368/-12，HEAD=8a94d64）
  - `skills/software-project-governance/infra/task_row_update.py`（+758/-12）
  - `skills/software-project-governance/infra/tests/test_fix394_progress_suffix_refresh.py`（新增 610 行 / 28 用例 + 12 subtests）
- **审查方式**: 逐行读 diff（1478 行 hunk 全读）+ 对照既有五步流与 fingerprint 契约源码 + 硬门槛命令全部亲跑 + HEAD 基线独立对照（临时 `git worktree add --detach` @8a94d64 + 拷贝活体 `.governance/`——等效 stash 对照且全程未触碰 staged 状态；`.governance/` 经核实整体 gitignored 未被 git 跟踪，worktree 必须补拷该目录才是忠实基线）+ 构造性输入探针 4 轮 25+ 项断言
- **审查结论**: **APPROVED_WITH_NOTES**（`unresolved_blockers=0`）
- **发现计数**: P0=0 / P1=1 / P2=2 / P3=5

---

## 1. 判据核验（对照源码与实跑，非采信申报）

| 申报 | 独立核验结果 |
|------|-------------|
| 词表闭集 7 词形；终态叙事词绝不入表 | ✅ `STALE_PROGRESS_PHRASES`（L241-249）恰 7 词形，每词形标注 phase∈TASK_STATES（测试钉住）；「已发布/已完成/完成/已交付」不在表中，且构造探针证实三词置于括号外也不被清除（taboo_survives×3 PASS）；裸英文态词（dev/review…）不入表（词表 docstring 显式声明 B-1 教训） |
| `build_candidate_row` 在 marker swap 后、post-splice re-check 前调 `_refresh_progress_prefix` | ✅ L635-639 插入点逐行核实：marker swap（L624-634）→ refresh（L639）→ 拼回 cell → post-splice re-check（L646-654）——链重读的是刷新后的最终候选，翻转路径的刷新先于自检，设计自洽 |
| 终态翻转清全部滞留词；非终态只清阶段≠目标态；括号内不触碰；只清锚之前括号之外 | ✅ `_refresh_stale_phrases`（L489-529）：committed→全表；否则 `d[1] != to_state` 过滤；`_paren_depth_before`（L477-486）半/全角括号计深；`_refresh_progress_prefix`（L555-568）以 `_OP_ANCHOR_RE` search-anywhere 切前缀。构造探针：嵌套括号（外清内保）、全角括号保护、锚在括号内（前清尾保+原位重锚）均按声明语义（另见 F-3 边界缺口） |
| `canonical_input_fingerprint` 加可选 action 默认 None→既有翻转 fingerprint 逐字节不变 | ✅ 签名尾部追加（L350），action=None 时 payload 与旧实现逐字段相同、json.dumps 参数相同；探针以 3 组代表性翻转入参（含中文 reason、多 evidence_refs、不同 schema_version）对照 HEAD 版模块（worktree 提取）**逐字节相等 PASS**；action=REFRESH_ACTION 时哈希改变 PASS（翻转/对齐不共撞 operation id） |
| 五步流复用真实等价（非旁路新写路径） | ✅ `execute_refresh`（L1329-1633）与 `execute_update`（L900-1245）逐步对照：同一 `_write_lock` 短锁、锁下 `_read_file_text` 重读、锁下 replay adjudication（`decide_operation_replay`/`_replayable_result_face` 逐字同构）、`revision_of` CAS、`_sweep_stale_temps`+`_atomic_write`、锁下 `_append_receipt`、写后字节比对自检；receipt 仅增列 `action`/`stale_phrases_removed`，`writer_result` face/enforcement=WARN 逐字段一致；写后自检比对翻转路径**更强**（新增 stale=空 + 锚数=1 不变量，L1600-1623） |
| fail-closed 拒非 committed/无锚/多锚行 | ⚠️ **部分成立**：非 committed ✓、无锚 ✓（构造探针 5 类拒绝路径全部 schema_violation，库/CLI 双面）；多锚行**在前缀无滞留词时不拒绝**——`execute_refresh` 把 stale 检测（L1508-1518）排在锚计数校验之前，双锚行被「already aligned」ok 放行，而同输入 dry-run 拒绝（schema_violation, exit 3）——见 **P1 F-1** |
| 已对齐行诚实 no-op（不写不落 receipt） | ✅ 构造探针：第二次刷新（新 id）→ ok、文件字节不变、ledger 行数不变 PASS；已对齐预览 `row_after==row_before`+`already_aligned=true` PASS |
| CLI 既有参数面零变化 | ✅ `--help` HEAD vs staged 集合差仅 `--refresh-suffix` 新增项及 usage 行换行；`add_arguments` hunk 仅插入新参数 |
| 刷新落新 op 锚=行内最近一次写入操作 | ✅ `refresh_candidate_row` L1330-1336 原位重锚；构造探针+CLI 端到端（receipt 的 row_after_sha256、锚=本次 operation_id）双证 |
| 幂等 | ✅ 同 id 重放→`replay of operation`、文件不变 PASS；固定同 id 时 dry-run 预览候选与 execute 落盘行**逐字节相等** PASS（不固定 id 时锚随操作 id 变化属设计） |
| 新测试 28P+12subtests | ✅ 亲跑 `28 passed, 12 subtests passed in 0.43s`（TestStaleVocabulary 2 + Flip 7 + Alignment 14 + Composer 2 + Guard 3 = 28；subtests 4+3+5=12） |
| 「dry-run 实测 6 行零写入」 | ✅ 本审查实测 **9 行**零写入（FEAT-060/061/062/063/064、FIX-383、REL-087/088/089），前后 SHA256 相等、git status 不变 |
| FEAT-045 实证补列 13 行=B~E 10 票+发布链 3 票 | ✅ 活体扫描 `.governance/plan-tracker.md` L106-119：已 lock 待派发×10（含 FEAT-045）+审查中/开发中/收尾中×3=13，精确对账（但测试 fixture 注释枚举漏 FEAT-045，见 P3 F-7） |
| 7 FAIL=既有基线 | ✅（具名 6/6 复现）见 §5 #8——archguard R1/R7/CliGate、loop-runtime-claims `test_real_repository_inventory_complete_and_within_budget`、FIX-300×2 在 HEAD+活体 .governance 基线**全部复现**；申报称 7F 但具名合计仅 6，第 7 项未具名（P3 F-6）；全量 4144P 未独立复跑（时长），以具名项全复现为准 |

---

## 2. 五维度结论（硬门槛：全覆盖）

| 维度 | 结论 | 依据（事实指向） |
|------|------|-----------------|
| 正确性 | **通过** | ①刷新语义三边界（词表闭集/括号保护/锚前作用域）实现与声明一致，构造探针逐项验证；②删除器消费前导空格+前瞻尾分隔，邻居词不粘连（探针相邻双滞留词形态验证）；③重叠匹配 `(start,-end)` 排序+cursor 遮蔽逻辑正确；④`_paren_depth_before` 对未配对闭括号不产生负深度、未闭合开括号保守保留（fail-safe 方向）；⑤replay/CAS/no-op/写后自检次序与翻转路径逐步等价；⑥F-1 双锚排序缺陷（P1）与 F-3 检测盲区（P2）为本维度仅有的两处边界缺陷，均无数据损坏（fail-safe 方向） |
| 安全性 | **通过** | 正则全为字面量+有界 `{32}`，无嵌套量词/灾难性回溯；无注入面（无 eval/exec/shell）；无敏感数据；对齐面是收紧方向（无锚/多锚/非终态拒绝、B-1 手改类不洗白——测试 `test_committed_display_prefix_without_anchor_is_refused` 钉住）；临时文件 `_sweep_stale_temps`+原子写与翻转路径同源 |
| 可维护性 | **通过** | 词表/锚正则/action 判别符全部模块级常量+`__all__` 导出；docstring 与行为一致（含「deliberate, test-pinned」扩展纪律）；`execute_refresh` 与 `execute_update` 的同构面可直接对照阅读；轻微问题：receipt 真源双头（F-4）、CLI 以 detail 字符串嗅探 replay/aligned（L2172/L2183——与翻转路径既有惯用法一致，非新引入） |
| 性能 | **通过** | 每次刷新 O(单元格长度×词形数) 的线性正则扫描，单元格短、词形 7 个；锁窗口内无额外 I/O；28 用例 0.43s、9 行活体 dry-run 秒级完成，无感知开销 |
| 测试覆盖 | **通过** | 28 用例+12 subtests 全真跑通过非 skip；覆盖：词表闭集钉住（2）+翻转刷新语义（7，含字节级列不变+全链终态干净+重放幂等）+对齐面（14，含 4 种活体滞留形态/锚后括号/零变 no-op/receipt 契约/重放/CAS 冲突不写/dry-run 零写×2/CLI 端到端/usage 拒绝/padding 不动）+组合①三解析器四面（2）+FIX-393 守护（3，pattern 串相等+identity）；缺口：双锚行双路径一致性未钉（P1 F-1 的测试面）、全角紧贴形态未钉（P2 F-3） |

---

## 3. AI 专项五项（硬门槛：逐一结论）

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | **无** | diff 全文 `mock|patch\(|MagicMock` 零命中；测试全部为 tempfile 真实文件+真实函数直调（含真实五步流 `execute_update`/`execute_refresh` 端到端） |
| 2 | 硬编码返回值 | **无** | 产品代码无硬编码分支返回；测试 fixture 的 OP_A/B/C、日期、id 为 DEC-213 fixture-local 固化（文件头声明），属正当 fixture 数据 |
| 3 | 幻觉 API | **无** | 被引符号逐一在源码核实：`STALE_PROGRESS_PHRASES`(L241)/`REFRESH_ACTION`(L226)/`_OP_ANCHOR_RE`(L199)/`find_stale_progress_phrases`(L532)/`refresh_candidate_row`(L1248)/`execute_refresh`(L1329)/`_dry_run_refresh`(L1902)/`STATUS_CELL_OP_SUFFIX_PATTERN`(L197)；解析器 `tp._status_is_writer_committed`(L240)/`vw._status_is_completed_cell`(L10603)/`vw._status_is_writer_committed_cell`(L10587)/`archive._task_status_is_writer_committed`(L477)/`archive._task_status_is_archivable`(L491)；28/28 真跑通过即存在性铁证 |
| 4 | 未实现 TODO | **无** | diff 全文 `TODO|FIXME|XXX|HACK` 零命中（Select-String 实扫） |
| 5 | 过度实现 | **无** | 范围恰为申报两面（翻转时刷新+对齐工具面）+测试；+1368 中 610 行（45%）为测试；词表 7 词形逐词对应活体语料（词表 docstring 列明行号级出处）、锚后括号形态有 FEAT-061 活体依据、`action` 判别符为台账可审计性所需——无投机泛化 |

---

## 4. 审查重点专项（任务书 6 项）

| # | 重点 | 结论 |
|---|------|------|
| 1 | 刷新语义边界正确性 | 通过（带 F-3 缺口注记）。闭集性：终态叙事词不可入表经测试+构造探针双钉；RE 边界：`[ ]*phrase(?=[ ]|$)` 前导吞噬+尾前瞻保证邻居不粘连、段尾 `$` 使「词紧贴锚」形态可清；嵌套括号/全角括号/锚在括号内构造验证通过。缺口：前瞻只认 ASCII 空格——全角括号紧贴/全角空格/紧邻 CJK 形态静默漏检并误报 aligned（F-3） |
| 2 | 写入器契约零回归 | 通过。五步流逐步等价（非旁路）；fingerprint 3 样本 HEAD vs staged 逐字节相等；receipt 增列不破坏既有键消费者（replay face 同构）；短锁语义一致（`_write_lock` 同参调用）；CLI `--help` 集合差仅新增项 |
| 3 | fail-closed 分支真实承重 | **部分承重**。无锚行/非 committed 行/未知 marker：库+CLI 双面真实拒绝（构造 5 类全 schema_violation，receipt 文件零创建）；多锚行：仅在滞留词在场时拒绝——无滞留词双锚行被 execute 路径 no-op 放行且与 dry-run 拒绝相左（**P1 F-1**） |
| 4 | 组合① FIX-393×FIX-394 | 通过（亲跑）。真实 tracker dry-run 的 row_after 单元格喂三解析器：`tp._status_is_writer_committed`=True、`vw._status_is_completed_cell`=True、`vw._status_is_writer_committed_cell`=True、`_is_incomplete_task_status`=False、`archive._task_status_is_writer_committed`=True、`_task_status_is_archivable`=True、`detect_row_state`=committed、`--inspect` 四面 `state=committed`；控制组证明滞留单元格在 FIX-393 下同样判 committed（刷新是文本卫生，非语义变更） |
| 5 | 幂等 | 通过。同 id 重放零变异；新 id 二次刷新零写零 receipt；dry-run 零变预览镜像 execute no-op；固定同 id 时预览候选与 execute 落盘逐字节相等 |
| 6 | 7 FAIL 基线抽查 | 具名 6/6 在 HEAD 基线全部复现（archguard 3+loop-claims 1+FIX-300 2）；方法论：worktree@HEAD+活体 .governance 拷贝（.governance 未被 git 跟踪，未拷贝的 worktree 是伪基线——首轮 loop-claims/FIX-300 在无 .governance worktree 中误通过/误报，补拷后与申报一致）；申报 7F 具名 6 项，第 7 项未具名（F-6） |

---

## 5. 亲跑命令与关键输出（硬门槛证据，全部本会话实跑）

1. `python -m pytest skills/.../test_fix394_progress_suffix_refresh.py -q` → **28 passed, 12 subtests passed in 0.43s**
2. `python skills/.../task_row_update.py --task FEAT-064 --refresh-suffix --dry-run --reason "review verify" --json` → `stale_phrases_found=["已 lock 待派发"]`；`row_after`=`committed (2026-09-24——0.88 阶段 D1——RELEASE-R0 F-7 入账) 〔op-…〕`；`writes_performed=0`、`lock_acquired=false`；前后文件 SHA256 相等（零写入实证）；`EXIT=0`
3. 组合①探针（row_after 喂三解析器+`--inspect`）→ 六判据全 True/False 如 §4#4；`inspect.state='committed'`；控制组（滞留单元格）双解析器亦 True（FIX-393 透视）
4. 多行活体 dry-run（FEAT-060/FIX-383/FEAT-061/FEAT-062/FEAT-063/REL-087/REL-088/REL-089）→ 各恰检出 1 滞留词；FEAT-061 `row_after` 锚后〔R0 NEEDS_CHANGE/2→R1 APPROVED_WITH_NOTES/0；commit 61618a5；…〕叙事完整保留；批量前后哈希不变
5. 构造探针 4 轮：fingerprint HEAD 对照×3 逐字节相等、action 改哈希、taboo×3 存活、嵌套/全角括号保护、锚在括号内原位重锚、无锚/双锚/非终态/未知 marker×5 拒绝、execute 面拒绝×3、幂等三态（重放/新 id no-op/零变预览）、dry-run↔execute 同 id 字节一致、**双锚无滞留词 execute=ok vs dry-run=exit3 分叉（F-1 实证）**、**锚后括号行翻转产生双 op 锚（F-2 实证）**、CLI `--help` HEAD 差集=仅 --refresh-suffix
6. 邻居回归全绿：test_task_row_update **42P** / test_fix393 **17P** / test_closure_chain **87P** / test_task_priority **147P** / test_archive **159P** / test_archive_decision_attribution **14P+4sub**
7. 硬门槛子命令：`verify`(PASSED)/`check-governance`/`check-version-consistency`/`check-cross-references`/`check-injection-budget` 五命令 **全部 EXIT=0**
8. HEAD 基线对照：`git worktree add --detach %TEMP%\fix394_head_baseline HEAD` + 拷贝活体 `.governance/`（.governance 未被 git 跟踪→必拷）→ archguard **3 failed（R1/R7/CliGate 同测试）**、loop-claims **1 failed（`test_real_repository_inventory_complete_and_within_budget`，L938 同断言）**、FIX-300 **2 failed（同两测试）**——具名 6/6 复现=**既有基线红，非本票引入** ✅；worktree 已 remove 清理，`git status` 复核 staged 两文件原样（+1368/-12 与审查开始逐位一致）
9. 活体对账：plan-tracker L106-119 滞留行 **13 行**=已 lock 待派发×10（FEAT-060/FIX-383/FEAT-061/FEAT-062/FEAT-064/FEAT-063/FEAT-044/FEAT-045/FIX-384/FIX-385）+审查中 REL-087+开发中 REL-088+收尾中 REL-089——「13 行=B~E 10 票+发布链 3 票」精确成立

---

## 6. 发现列表（P0-P3）

> P0=0。P1 为强烈建议本批内修改项（非阻塞），P2 为建议/登记跟踪，P3 为记录级。

### P1（强烈建议修改——原则上本批内处理）

- **[P1] F-1｜`execute_refresh` 的多锚 fail-closed 分支被 no-op 短路，且与 dry-run 语义分叉**
  - 位置：`task_row_update.py` L1508-1518（stale 检测+`if not stale: return ok "already aligned"` 先执行）vs L1297-1304（`refresh_candidate_row` 的多锚拒绝——仅当有滞留词时才可达）；对照 `_dry_run_refresh` L1973-1984（锚计数校验排在 stale 检测 L1986 之前）。
  - 事实（构造输入亲证，probe3 case1）：双锚行 `committed x 〔op-A〕〔op-B〕`（前缀无滞留词）→ `execute_refresh` 返回 **ok「already aligned」**（不写、不落 receipt）；同一输入 dry-run 返回 **refusal schema_violation「ambiguous — 2 ops anchors on one status cell」（exit 3）**。双锚+滞留词形态两路径一致拒绝（probe3 case2）。申报「fail-closed 拒…多锚行」与「dry-run 与 execute 语义一致」在该输入类均不成立。
  - 影响：无写入、无数据损坏（fail-safe 方向）；但「ambiguous 拒绝+人工裁决」契约承诺被执行路径静默降级为 aligned 认定，且同一命令两个面孔给出矛盾裁决。结合 F-2（翻转路径可制造双锚行）该输入类并非纯假想。
  - 建议：将锚计数校验提到 stale 检测之前（约 3 行重排，与 `_dry_run_refresh` 次序对齐）；补一条「双锚行 execute/dry-run 双路径一致拒绝」钉住测试。建议在 13 行 execute 落地前或紧随的同批小票修复。

### P2（建议修改/登记跟踪——不阻塞合并）

- **[P2] F-2｜翻转路径 end-anchored 锚剥离对「锚+锚后叙事括号」行可制造双锚行**（既有行为，非本 diff 引入；与本票工具面直接交互故登记）
  - 位置：`build_candidate_row` L658-661：`base = STATUS_CELL_OP_SUFFIX_PATTERN.sub("", core).rstrip()`——剥离要求锚在单元尾；`_OP_ANCHOR_RE` docstring（L199-206）自述「never assumes it is last」仅落实在刷新面，翻转面未对齐。
  - 事实（构造亲证）：`review 审查中 (2026) 〔op-A〕〔R0 note〕` 翻转 committed → `committed (2026) 〔op-A〕〔R0 note〕 〔op-B〕`——**2 个 op 锚**；FIX-393 判据不受影响（仍判 committed），但该行此后过对齐面时：有滞留词→ambiguous 拒绝（人工裁决），无滞留词→F-1 放行。FIX-394 前同型翻转同样产生双锚（strip 逻辑未变）——非回归，为既有潜在脏行制造机。
  - 建议：翻转路径剥离改 search-anywhere（`_OP_ANCHOR_RE` 子一次）或 `execute_update` 写后自检加锚数==1 断言；与 batch 2.3 ops 结构性 join 议程合并考虑。
- **[P2] F-3｜词表删除器前瞻只认 ASCII 空格/段尾——全角紧贴等形态静默误判 aligned**
  - 位置：`_STALE_PHRASE_RES` L249-253：`r"[ ]*" + re.escape(phrase) + r"(?=[ ]|$)"`；消费面 `find_stale_progress_phrases` L532-552。
  - 事实（构造亲证）：`committed 已 lock 待派发（2026——审查中） 〔op-A〕`（词紧贴全角括号，无 ASCII 空格）→ `find_stale=()` → execute 返回 ok「already aligned」，滞留词留存。同型：全角空格 U+3000 分隔、紧邻 CJK 字符。注意这不是「漏清」而是**肯定性误报 aligned**。13 行活体语料全为半角括号+空格形态（9 行 dry-run 亲证全命中），本批对齐不受影响。
  - 建议：前瞻扩展为词边界类（如 `(?=[\s（(〔]|$)`——前瞻不消费、无删除边界风险），或至少在 already-aligned 详情中显式回显「按空格分隔契约检测」；扩展保持 deliberate+test-pinned 纪律并补负例。

### P3（记录/建议级，不要求修改）

- **[P3] F-4｜receipt 滞留词清单为双真源**——`refresh_candidate_row` L1324 丢弃 `_refresh_progress_prefix` 返回的 `_removed`，receipt 改用执行前 `find_stale_progress_phrases`（L1508）结果。两处同 deleters 同深度检查当前恒一致，写后自检（L1611 reread stale 必须为空）兜底；建议未来让 compute 步返回 removed 供 receipt 直接消费。
- **[P3] F-5｜`_dry_run_refresh` 异常分类粗于 execute 面**——L2000 附近 try 块把块内一切 ValueError 归 `cross_record_violation`（含 `refresh_candidate_row` 的 schema_violation 类），且 `cells[_status_cell(cells)[0]]` 无 `TypeError` 保护（execute 路径 L1519-1524 有 `except (IndexError, TypeError)`）——检测成功后理论上不可达，同 pragma 惯例；建议对齐 execute 的错误分类。
- **[P3] F-6｜申报计数精度**——「全量 7F」具名合计仅 6（第 7 项未具名）；「回归 293P+archive 243P」未声明文件组合（亲跑可对账面：task_priority 147+closure_chain 87+task_row_update 42+fix393 17=293P 恰合「回归」；archive 159+archive_attr 14=173P≠243P，组合不明）。申报实质（基线红非本票引入）经 6/6 具名项 HEAD 复跑证实，实质成立、计数口径欠精确；全量 4144P 未由本审查独立复跑。
- **[P3] F-7｜测试 fixture 注释与活体枚举漂移**——`LIVE_LOCKED` 注释列 9 行「(9 rows)」，活体实为 10 行（FEAT-045 L113 缺席枚举）；申报 13 行口径本身正确。建议补枚举防后续对账困惑。
- **[P3] F-8｜「进行中」词形在 alignment 面不可达**——链序 `dev`（`🔄|进行中`）先于 `committed`：假想滞留行「committed 进行中…〔锚〕」会先被判 dev→refresh 以 schema_violation 拒绝，该词形仅翻转路径可清（alignment 永不可达）。当前 13 行零此形态；词表注释已声明该词形服务翻转路径。记录边界，无需修改。

---

## 7. 验收标准核对与范围红线

| 验收项 | 核对 |
|--------|------|
| 运行时机制（翻转时刷新，三边界语义） | ✅ L635-639 插入点+构造探针逐边界验证 |
| 对齐工具面（--refresh-suffix 五步流复用+receipt+幂等） | ✅ 逐步等价对照+构造探针三态幂等+receipt 契约测试 |
| fail-closed 拒非 committed/无锚行 | ✅ 真实承重（双面拒绝+零 receipt 创建）；多锚行带 F-1 例外 |
| 组合①三解析器+--inspect 四面 committed | ✅ 亲跑（§5 #3） |
| 契约保持（fingerprint 逐字节/CLI 参数面零变化） | ✅ 双向实证 |
| 范围红线（只触碰两申报文件；不改 .governance/；不动 staged 状态） | ✅ diff 面核实；审查全程 git status 逐位复核；.governance 零写入（dry-run 九行前后哈希相等） |

---

## 8. 审查结论

**APPROVED_WITH_NOTES**（`unresolved_blockers=0`）

- 硬门槛全过：P0=0；五维度逐一有结论；AI 专项五项逐一有结论；每条发现带级别+位置+事实+建议。
- 两面机制（翻转时刷新+一次性对齐）与申报一致并经契约源码对照、构造探针、活体 dry-run 三重独立核验；fingerprint/五步流/CLI 参数面三项契约保持全部实证。
- **P1 F-1 建议原则上本批内修复**（约 3 行次序重排+一条钉住测试；建议置于 13 行 execute 批量落地前，或作为紧随小票）——若 Coordinator 裁定必须本轮修复，按 NEEDS_CHANGE 流转返工后由本 Reviewer 复审（R1 逐条比对 findings）。
- P2 F-2/F-3 与 P3×5 均为登记跟踪/记录级，不阻塞合并；遗留项关闭时点建议由 Coordinator 在 F-1 修复排程时一并指定。

> Reviewer 声明：本审查为只读审查，未修改任何产品代码与 staged 状态；唯一写入物为本报告文件。基线对照使用的临时 worktree 已清理，`.governance/` 在审查全程零写入（活体 dry-run 前后 SHA256 相等实证）。
