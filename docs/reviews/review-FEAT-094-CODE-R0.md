# FEAT-094 Code Review R0 — 审查可信链（五步事务+快照绑定+CONFLICT+R2 义务+ABORTED/UNKNOWN）

- **轮次**: R0（初审）
- **审查方**: Code Reviewer Agent（只读；唯一写面 = 本报告）
- **审查对象**: 工作区未 commit 变更 7 M 文件（HEAD `75cc7e5`，`git diff --stat` = 1238 insertions / 58 deletions），Developer 声称清单与实际 `git status --porcelain` **完全一致**（7/7 对上，零未申报文件）
- **任务契约**: `.governance/execution-packets.json` packets.FEAT-094（实读 L1285-1404）+ plan-tracker L84（实读）
- **结论**: **APPROVED_WITH_NOTES（unresolved_blockers=0）**

---

## 0. 结论

**APPROVED_WITH_NOTES ｜ unresolved_blockers=0 ｜ P0=0 ｜ P1=0 ｜ P2×1 ｜ P3×8**

五步事务原子性、快照绑定严密性、CONFLICT 拒收、R2 义务唯一可消解、触发器零变化五大主张全部经一手证据成立；四项硬门槛全部独立复现通过。P2-1 为集成缝隙（Check 30 词表未同步新终态 token），行为面降级结果恰好正确（fail-closed 方向），不构成阻塞，建议随票或紧随补测试+文档一句。

---

## 1. 发现清单

### P2-1（建议）Check 30 复审链词表未同步 ABORTED/UNKNOWN——集成缝隙未测试、未披露

- **位置**: `infra/checks/review_domain.py:1553-1555`（`_REVIEW_TERMINAL_CONCLUSIONS = (*APPROVAL, "BLOCKED")`，无 ABORTED/UNKNOWN）；消费臂 L2604-2658；`infra/verify_workflow.py` 全文 ABORTED 仅出现于 CLI 定义（L27521）；`references/authority-ledger.md` FEAT-094 节未披露此交互。
- **事实**: FEAT-094 引入 `REVIEW-{task}-R{n}` 证据行新结论 token ABORTED/UNKNOWN，但 Check 30 的终态词表未扩。实测代码推演（review_domain L2604）：ABORTED 为链终态时落入「non-terminal」臂——任务未完成 → V1 WARN「re-spawn expected」（**语义恰好正确**：死亡≠消解、补审预期）；任务标完成 → V1 FAIL（**fail-closed 正确**：带 ABORTED 终态不得过审收口）。同轮补审（Relief reviewer 命名空间行）依赖 L2165 的 duplicate-round「most-terminal wins」合并（ABORTED 非 terminal → 被 APPROVED 覆盖）——该规则存在且方向正确。
- **影响**: 无错误结果可物化（两个方向都安全），但 (a) 14 个新测试无一覆盖 Check 30/30c 消费面；(b) 该边界未在 references FEAT-094 节披露——继「自由格式报告不参与 CONFLICT」之后第二个未文档化边界。
- **建议**: 补一条 Check 30 消费用例（ABORTED 终态→WARN 不 FAIL；同轮补审 APPROVED→终态 APPROVED）+ references 节一句话披露。

### P3-1（讨论）provenance rider 内部小数字不自洽：+~728 vs 实差 732

- **位置**: `infra/checks/loop_runtime_claims.py:257-265`（rider："review trust chain +~728 net units after in-ticket dedup"）。
- **事实**: 361,949（实测，见 §4）− 361,217（rider 所引 pre-FEAT-094 值）= 732，非 728。锚定数（361,217 / 361,949 / 434,339）全部正确，公式与 pin 正确；仅中间描述数有 4 单位出入（"~"近似语言）。DEC-261 纪律要求 provenance 可复算——建议下次挪常数时保持三数互洽。

### P3-2（讨论）verify_review_trust 对「bind 文件被删除」判 UNKNOWN 而非 CONFLICT——与 commit 面不对称

- **位置**: `infra/review_record.py:380-389`（bind 循环：`hash-object` 失败 → `None` → `unverified` → UNKNOWN）对照 L352-360（commit 面：git 活但 commit 不解析 → `""` → mismatch → CONFLICT）。
- **事实**: 被钉扎文件被删除时 git 可用但 `hash-object` 非零 → 判 UNKNOWN（「当前不可复核」）而非 CONFLICT（「漂移」）。fail-closed 不受影响（UNKNOWN≠通过，仍需人工处置），但删除这一最强漂移信号反而落在弱档。建议先探 git 活性再降级（与 commit 面同款姿势）。

### P3-3（讨论）review 文件部分写入残留 corner：无补偿删除 + 收敛措辞不精确

- **位置**: `infra/review_record.py:989-998`（`review_file_unwritable` 分支）对照 L1030-1038（仅 evidence-row 失败有补偿删除）。
- **事实**: `write_text` 中途 OSError（如盘满）可能残留半文件；该 corner 下 (a) 无补偿 unlink（补偿只覆盖 row 失败面）；(b) 错误消息「re-running this command converges」不精确——重跑会先撞 FIX-289⑤ overwrite guard，需 force。概率极低（账本先行已披露 txn id，人工可恢复），登记备查。

### P3-4（讨论）义务契约拒收无审计事件——与身份契约拒收不对称

- **位置**: `infra/authority_ledger.py:718-770`（`_check_batch_obligations` 只 raise）对照 `_refuse_identity_conflict`（落 `identity_conflict_rejected` 审计事件后 raise）。
- **事实**: 重复 OPEN 登记/幻影清除的**被拒尝试**只在调用方错误输出可见，账本内无审计痕（事件词表无 obligation 拒收类）。身份面有、义务面无——设计不对称；拒绝本身正确（整批零写入），仅审计可见性弱一档。

### P3-5（讨论）锁面与修改面不完全对齐（流程观察，移交 Coordinator）

- **事实**: `agent-locks.json` file_locks 锁 6 文件（含锁而未改的 `governance_store.py`），但 7 个实改文件中 `review_record.py`（+602 主文件）与 `references/authority-ledger.md` 未入锁。扩锁 2（`loop_runtime_claims.py` 16:02:02 / `test_loop_runtime_claims.py` 16:02:03，理由=sanctioned recalibration）已实证留痕。并发风险实际低（无他任务并发写这两个文件），纪律面登记。

### P3-6（讨论）manual clear 逃生口无 CLI 操作面

- **事实**: references 节述「Coordinator 显式 recheck_obligation_cleared 事件（人工逃生口，留痕）」——事件本身即审计痕（actor/timestamp/append-only），但操作路径只有 LedgerWriter API（无 `authority-ledger` 子命令封装）。可用但不易达，建议后续票补 CLI。

### P3-7（讨论）实现面 EVD 行未落（流程提醒，completion 收口项）

- **事实**: execution-packet quality_budget 各面均「dev 完成时落 EVD 行」，当前 `.governance/evidence-log.md` 无 FEAT-094 实现行（REVIEW 机录行将由本事务自动追加）。与 FEAT-093 先例同口径（completion 时收口），非本轮阻塞项，列此防丢。

### P3-8（讨论）测试边角缺口（非阻塞）

- 14 测试断言深度总体扎实（同 txn id/零部分写入/补偿删除/字节兼容均有），缺四个边角：①「审查结论：」行式 token 的 CONFLICT 用例（仅测了粗体式）；②force 覆写 + row 失败的「文件保留+披露」补偿分支；③报告引用前轮 token 的多 token 容忍（tokens={NEEDS_CHANGE, APPROVED} + claim=APPROVED 应放行）；④ABORTED 行的 Check 30 消用例（同 P2-1）。

---

## 2. 审查重点逐项核验（本票特有面）

### 2.1 五步事务原子性与补偿（重点①）✅

- **账本先行**：`write_review_record`（`review_record.py:710`）顺序 = 输入校验 → FIX-289⑤ 只读守卫（L878 采 `file_preexisted`）→ 报告字节钉扎（fail-closed：不可读=error dict 无写入）→ CONFLICT 判定（零写入）→ **`_review_ledger_transaction`（L635）单 transact 批落 `review_recorded` + 义务事件** → 文件面（备份→记录→evidence 行）。
- **「本事务新建 vs 既有文件」区分正确**：`file_preexisted` 在账本事务**之前**采集（L878），evidence-row 失败的补偿删除仅限 `not file_preexisted`（L1030-1038）；force 覆写路径保留新记录+备份并在错误消息中披露备份路径——**误删既有文件结构性不可能**。`test_row_failure_compensates_fresh_review_file` 钉住（unlink 断言 + 义务存续断言）。
- **撕裂账本拒新事务**：`authority_ledger.py:280-325`（`_read_events_raw` 逐行验 seq/prev_hash/hash，撕裂尾置 `integrity.ok=False`）→ `_require_integrity`（L549）在 transact 前置 raise → review 侧转 `code=ledger_refused` 结构化错误、零文件写入。`test_torn_ledger_tail_refuses_whole_transaction` 钉住。
- **transact 批原子**：`authority_ledger.py:588-649`——integrity gate → payload 校验 → `_check_batch_identity` → `_check_batch_obligations`（均在**任何字节追加前**）→ 单次 blob append + flush + fsync → 重折叠 + 原子 snapshot。账本拒收（`ledger_refused`）时文件面零写入（文件在账本之后才写）。
- **force 备份失败路径**（backup_unreadable/backup_unwritable）：旧记录原样保留、新记录未写、错误披露已提交 txn id——披露式半提交，可 force 重跑收敛，符合「异常不隐藏」。

### 2.2 快照绑定严密性（重点②）✅

- **真字节级**：`hashlib.sha256(report.read_bytes())`（L908 区域）——原始字节，无编码/换行归一化，重算可验证；`test_acceptance1_report_hash_and_snapshot_fields` 以 `hashlib.sha256(report.read_bytes())` 独立复算比对。
- **hash-object 路径安全**：argv-list 调用（`["git","-C",root,"hash-object","--",spec]`，无 shell）、无 `-w`（不写对象库）、`--` pathspec 防 option 注入；与 `governance_store.py:923` 的 rev-parse 先例同姿势（governance_store 未改理由成立——其对象校验面已存在，本票新增面独立于它）。
- **git 不可用=诚实披露不伪造**：commit → `git:unavailable`、worktree/bind → `unavailable`（`snapshot_binding` L270-297，全部经 `_HEX40_RE` 门禁，无任何伪造哈希路径）；`test_acceptance1_worktree_dirt_disclosed_and_git_unavailable_honest` 钉非 git 目录三字段。untracked bind 钉扎 + 事后改写 → `verify_review_trust` CONFLICT（`test_acceptance1_untracked_bind_detects_concurrent_rewrite`——REV-009 幻影修订的红绿钉）。

### 2.3 CONFLICT 判定边界（重点③）✅（边界=已知披露）

- **判定方向**：`review_record.py:905-916`——报告携带可解析 token（`**TOKEN**` 粗体或「审查结论：」行）且 claim 不在 token 集 → `code=conflict_report_vs_record` 拒收（零写入，测试断言无文件/无行/无账本目录）。**双向不一致均拒**（report=NC+claim=APPROVED 拒；report=APPROVED+claim=NC 亦拒）。
- **恶意利用面评估**：任务书假设「机录 NC + 报告写 APPROVED 且不带可解析 token → 静默通过」——该形态下机录落 **NEEDS_CHANGE（悲观侧）**，非乐观胜出；且报告字节哈希已钉，事后改写即 CONFLICT。危险方向（report=NC + 机录 APPROVED）需报告完全无 token——**实测 293 份历史报告中 250 份带 `**TOKEN**` 粗体锚**（grep 一手数据），仓库真实格式覆盖率高；无 token 自由格式报告不参与判定=包内已披露边界（assumption_record）。豁免集 {BLOCKED, ABORTED, UNKNOWN} 只豁免 **claim 侧**且全部朝悲观/事实方向（升级/死亡），**无乐观上行路径**——BLOCKED 记录在 Check 30 是非通过终态，不构成绕过。
- P3-8①：行式 token 与多 token 边角缺测（见发现）。

### 2.4 R2 义务唯一可消解（重点④）✅

- **同批原子**：`_review_ledger_transaction`——`review_recorded` 与 `recheck_obligation_registered`（`RECHECK-{task}-R{n+1}`，携 prev_report/created_by/报告哈希/commit）同一 `transact` 批；`test_acceptance2_needs_change_registers_r2_obligation_atomically` **断言两事件 transaction_id 相等**。
- **批内模拟折叠正确且与 FEAT-093 同款姿势**：`_check_batch_obligations`（L718-770）从 writer 折叠态出发按批内顺序应用——重复 OPEN 拒（唯一）、幻影清除拒、无 key 拒；与 `_check_batch_identity` 同「整批先验后写」姿势、刻意不合并（两类契约两类拒收语义）——语义一致性成立。`obligation_key` 单源（L241-252，obligation_id 优先、task_id 兼容 FEAT-093 legacy 形状），fold/批校验/写入器三方共用。
- **NC 滚动登记**：R{n} NC 同批清 `RECHECK-{task}-R{n}` + 开 `RECHECK-{task}-R{n+1}`（`test_acceptance2_obligation_cleared_by_discharging_round` 断言两态并存）；重试收敛 already_open 不重复登记（`test_acceptance2_duplicate_open_obligation_refused_and_retry_converges` 断言仅 1 条 registered 事件）。
- **ABORTED 不消解 + 补审消解**：`_OBLIGATION_DISCHARGING_RESULTS` 不含 ABORTED/UNKNOWN；死亡后义务保持 OPEN，Relief reviewer 同轮真实裁决同批清偿（`test_acceptance5_aborted_does_not_discharge_obligation` 断言 `REVIEW-FEAT-094-R1-RELIEF-AGENT` 清偿）。
- **manual clear 留痕**：`recheck_obligation_cleared` 事件本身=append-only 审计痕（actor/timestamp）；`authority-ledger status` 新增 `open_recheck_obligation_keys`（L1516-1521）可 grep 未决清单（蒸发面的人读兜底）。缺 CLI 面（P3-6）。

### 2.5 触发器零变化（重点⑤）✅

- diff 未触及 `_wire_to_loop`/revisit 字段构造逻辑；`revisit_required = (result_norm == "NEEDS_CHANGE")` 原行不变——ABORTED/UNKNOWN/BLOCKED 天然不触发复审。`test_revisit_trigger_fields_byte_compatible` 钉 `next_round=REVIEW-{task}-R{n+1}` + `prev_report`（summary 键 + record 字段双面）+「## 复审必达（NEEDS_CHANGE）」段。`_RESULT_RE` 扩 ABORTED/UNKNOWN 为纯增量；CLI choices 同步；`abort_reason` 仅限终态（否则 error）。

### 2.6 重校面（重点⑥）✅——见 §4 核验。

### 2.7 D4 纯粹性（重点⑦）✅——见 §5。

### 2.8 测试质量（重点⑧）✅——见 §6。

---

## 3. 验收①~⑤对照（plan-tracker L84）

| # | 验收项 | 判定 | 一手证据 |
|---|--------|------|---------|
| ① | review-record 增加快照绑定与报告哈希字段 | ✅ | `review_record.py:153-314`（钉扎字段+`verify_review_trust`）+ record/evidence 双面锚（`- report_sha256:`/`- snapshot_commit:`/`- snapshot_worktree:`/`- snapshot_bind:`；row pins `report_sha256=<12hex>; commit=<12hex>`）；测试 3 条全绿 |
| ② | R2 义务随 NEEDS_CHANGE 机录自动登记且唯一可消解 | ✅ | §2.4 全链 + 3 条专项测试绿 + `_check_batch_obligations` 整批拒收 |
| ③ | CONFLICT 判定与处置路径 | ✅ | §2.3 + `conflict_report_vs_record` 结构化错误（含 manual disposition 文案）+ 零写入测试 |
| ④ | 死亡代理 ABORTED 记录 | ✅ | CLI `--result ABORTED\|UNKNOWN --abort-reason` + record `- abort_reason:` 字段 + 不消解测试（UNKNOWN 同面） |
| ⑤ | 红绿测试+全套件回归零退化 | ✅ | 14 专项绿 + 全套件 Ran 1102 OK（=1088 基线+14，零退化） |

**non_goal 守卫**：触发器语义零变化（§2.5）✅；历史零回填（无迁移代码；legacy 记录 `UNPINNED` 不判 CONFLICT——兼容性设计有测试）✅；无 FEAT-095 执法面/096 隔离面代码 ✅。

---

## 4. 硬门槛复现（本席独立执行，非转述 Developer）

| # | 门槛 | Developer 声称 | 本席复现 | 结果 |
|---|------|---------------|---------|------|
| ① | 全套件 | Ran 1102 OK exit 0 | `python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py`（PYTHONDONTWRITEBYTECODE=1） | **Ran 1102 tests in 537.709s / OK / python exit 0** ✅（=1088+14） |
| ② | check-governance | [PASS] | `check-governance --summary-only` | **Governance: [PASS]，exit 0** ✅ |
| ③ | arch-health | 净树/本树 4E/33W 持平 | `check-architecture-health`（本树） | **4 ERROR / 33 WARN**（advisory）——4E 均存量结构性巨物（verify_workflow.py 28017 行等，HEAD 期即超阈，+27 行不改变存在性）；净树未复跑（避免 stash 突变工作区，据 4E 构成判定持平成立） ✅ |
| ④ | 复审必达等价 | 字节兼容测试+95 项 review/ledger 回归绿 | 专项 14 绿 + `-k "*eview*" -k "*edger*"` | **Ran 161 tests / OK**（模式为声称口径的超集）+ byte-compat 测试绿 ✅ |
| - | 专项 | 14 新测试 | `-k FEAT094` | **Ran 14 tests in 3.683s / OK** ✅ |

工作区卫生：全套件跑后 `git status --porcelain` 除 7 M 外零残留（测试自清理，含 sd-write-face 虚构文件）。

## 5. 重校核验（sanctioned recalibration）

- **公式**：ceil(361,949 × 1.2) = ceil(434,338.8) = **434,339** —— 数学正确；`ScanLimits().max_semantic_units = 434339`（`loop_runtime_claims.py:270`）。
- **实测复现**：本席跑 `check-loop-runtime-claims` → **`"semantic_units": 361949`、exit 0**——与 rider 声称的 measured_peak 逐位一致；`semantic_payload_bytes: 19,185,877`（rider 记 19,185,832；差 45B = Coordinator baseline-register live 写入所致，量级无意义差，`< 32MiB` 预算结论不变）。
- **pin 同步**：`test_loop_runtime_claims.py` FIX369 类双断言改钉 434339 == math.ceil(361949*1.2)，本席 `-k "*FIX369*"` **Ran 2 / OK**。
- **纪律**：DEC-261/FIX-369 同款（结构耗尽 99.8%=361,217/361,923，非 waiver）；扩锁留痕（16:02:02/03，ttl_reason 明示）；rider 自含 provenance（含本 rider 自身）；M-2 复测义务保留。Coordinator baseline-register live 写入在案（gate=check-loop-runtime-claims.semantic-units，row_digest=4c2aa3cf——任务上下文交接，未重算 digest）。
- 小瑕疵：P3-1（~728 vs 732）。

## 6. D4 纯粹性

- **7 文件全在票面**：review_record.py（五步事务核心）/ authority_ledger.py（义务契约+key 单源+status 键）/ verify_workflow.py（CLI 透传 27 行）/ test_verify_workflow.py（+507 专项）/ loop_runtime_claims.py + test_loop_runtime_claims.py（sanctioned 重校）/ references/authority-ledger.md（accessibility 预算要求的字段语义锚——包 quality_budget.accessibility 明文「锚入 SKILL/references」）。无无关重构、无版本 bump、无 fixture 漂移。
- **不越票**：无 FEAT-095 执法/限流代码、无 FEAT-096 隔离/锁回收代码；`task_row_update.py` 未动（FEAT-093 开关面保持）；`governance_store.py` 锁而未改（理由成立，§2.2）。
- **一个 commit 承载一个功能**：待 commit 时验证（当前工作区态符合）。
- 流程注记：P3-5（锁面 2 文件未覆盖）、P3-7（EVD 收口）。

## 7. 测试覆盖评估（14 新测试）

- **断言深度**：同 txn id 原子性（2 处）、零部分写入（CONFLICT 三面不存在的显式断言）、补偿删除（unlink + 义务存续）、字节兼容（trigger 字段双面）、死亡不消解（fold 态断言）、真实 git repo fixture（真 SHA 钉扎，非 mock 哈希）、撕裂尾（追加坏行后拒收）、already_open 收敛（事件计数=1）——深度扎实，非冒烟级。
- **缺口**：P3-8 四边角。质量预算 performance 守卫（2.0s 墙钟）与 maintainability（单模块内聚、无跨文件半提交窗口——账本与文件面同函数序内聚）均满足。

## 8. 五维度结论 + AI 专项 + 设计一致性

| 维度 | 结论 |
|------|------|
| 正确性 | ✅ 边界（无 git/撕裂尾/重复登记/幻影清除/force/补偿）全部显式处理且有测试；资源管理（fsync/原子 snapshot/temp 清理）正确 |
| 安全性 | ✅ 无 shell 注入面（argv-list+`--`）；无敏感数据；权限面=仓库内只读 git 查询；伪造路径零（诚实披露三态） |
| 可维护性 | ✅ `obligation_key` 单源防漂移；两类契约刻意分离有注释；grep 锚+references 文档化；P3-4 审计不对称为小疵 |
| 性能 | ✅ 2.0s 墙钟守卫测试；hash 计算单次；账本 O(n) 重折叠为 FEAT-093 已披露姿势 |
| 测试覆盖 | ✅ 14 专项+161 回归+全套件 1102 绿；P3-8 边角缺口非阻塞 |

**AI 专项 5 项**：mock 残留 ❌无（真 git 子进程 fixture）；硬编码返回值 ❌无（哈希全部实算+正则门禁）；幻觉 API ❌无（subprocess/git/LedgerWriter 均存在且被测）；未实现 TODO ❌无；过度实现 ❌无（每个面均有票面验收项对应；`already_open` 收敛面向真实故障恢复路径非臆想）。

**设计一致性**：✅ 与 execution-packet 五步不可分割目标、DEC-330 审查可信链裁定、REV-009/R2 蒸发实证形态逐一对应；与 FEAT-093 账本底座姿势一致（模拟折叠/追加式/渐进开关不越界——review 路径账本原生化为票面设计，非开关绕过；`.governance/authority-ledger/` 当前不存在且 gitignored，首次机录播种为文档化行为）。

---

## 9. 复审指引（如走 NEEDS_CHANGE 不适用——本轮通过；P2-1 供 Coordinator 裁定随票补或转后续票）

*审查方：Code Reviewer Agent（只读；唯一写入=本报告）｜审查对象：工作区未 commit 7 M 文件 @HEAD 75cc7e5｜结论：APPROVED_WITH_NOTES（unresolved_blockers=0）｜机录建议：Coordinator 以 review-record 持久化（--task FEAT-094 --round 0 --result APPROVED_WITH_NOTES --report docs/reviews/review-FEAT-094-CODE-R0.md）*
