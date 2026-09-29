# Code Review R1 — FEAT-077（scoped delta：NF-1(a) 修订通道增量）

- **Task**: FEAT-077 增量（设计审查 R1 NF-1(a) 处置：修订通道 commit 前补齐）
- **Reviewer**: Code Reviewer Agent（同 R0 Reviewer，R1 轮）
- **前轮引用**: R0 = `docs/reviews/review-FEAT-077-CODE-R0.md`（APPROVED_WITH_NOTES, unresolved_blockers=0, P2×1+P3×5）
- **审查范围**: 增量 diff only——`change_triage.py` +239（修订通道三函数）/ `task_priority.py` +73（resolve 第四参 + max-sweep + lag WARN + 缓存面）/ 两测试文件 +21 用例。R0 已审交付面不在范围（除非增量破坏）
- **范围排除**: B1a（FEAT-078）/B1b（FEAT-079）在途文件未触碰；FIX-404 已 commit（f627c57）不在工作区

## 结论

# APPROVED_WITH_NOTES

**unresolved_blockers = 0**

| 级别 | 计数 |
|------|------|
| P0 阻塞 | 0 |
| P1 关键 | 0 |
| P2 建议 | 0 |
| P3 讨论 | 5 |

## 测试复跑证据（定向三族，协议限定）

```
$env:TEMP/$env:TMP → .governance/tmp/check-run-20260929（协议重定向）
python -m unittest …test_change_triage …test_task_priority …test_provenance_domain
→ Ran 332 tests in 27.566s — OK（一次通过，无重试）
```

R0 311 → 332（增量 21 用例）。声明「332 OK」吻合；声明「22 用例」实际 21（DemandRevisionChannelTests 声明 12 实测 11——`311+11+6+4=332`），计数差 1 如实记录（覆盖充分性不受影响，见下）。

## 七点重点核验结果

### 1. from 派生链的防伪造完整性 — ✅ PASS
- 写入器派生：`append_demand_revision` 内 `resolve_demand_source(task_id, DEMAND_SOURCE_LEGACY, records, events)`（change_triage.py L885-891）——from = 最新事件 > record；`from` 不在函数签名（调用方不可传）——伪造起点不可表示 ✓
- 链式修订：第二事件 from=上事件终值（事件层 > record 层）——`test_second_revision_derives_from_previous_event` 实证（from="user-named"=事件1 to）✓
- 层次论证：行内标注在 plan-tracker md（tpa 层数据源），写入器不持有——见裁决点 6

### 2. evidence 失败回滚的原子性边界 — ✅ PASS（1 小缺口→P3-2）
- prior_size 写前捕获（L911）；回滚两分支：created→unlink / 已存在→truncate(prior_size)（L929-934）；回滚自身失败→`except OSError: pass` 但 error 消息明示「if the stream still shows the event, remove the trailing line manually」（L937-940）——自披露路径存在，不静默吞 ✓
- 测试 `test_evidence_failure_rolls_back_event_append` 覆盖 created→unlink 分支（断言 events_path 不存在）✓
- 残余边界（固有，非缺陷）：事件行落盘后、evidence 写入前进程崩溃 → 无 evidence 的事件残留（append-only 系统普遍无事务窗口；error 返回路径覆盖可观察失败）。可作 B3 检查面（DSR 事件与 DSR-* evidence 行交叉核对）后续收口——不阻塞

### 3. None≡三参零回归断言的真实性 — ✅ PASS（逐例，非抽样）
`test_none_events_identical_to_three_arg_call`（test_task_priority.py L2523-2545）：6 个 case 参数化——record 权威/两面一致/矛盾→conflict/空 records/他任务 record/存量无键——**覆盖 resolve 全部行为分支**，每例双向 `assertEqual(四参传 None, 三参)`。另有 `test_old_mismatch_with_event_is_not_conflict` 内嵌无事件对照（同输入无事件→conflict 保留）。源码结构佐证：新增逻辑全部位于 `if revision_events:` 块内（L1482-1493），None 时逐字节走原三源链。

### 4. max-sweep 的性能语义与正确性 — ✅ PASS
- 正确性：`_triage_records_mtime` 现为目录+全部条目 max st_mtime（task_priority.py L886-913）——jsonl append（条目集不变、内容增长）bump 文件 mtime → sweep 捕获 ✓ 专测 `test_jsonl_append_invalidates_cached_analysis`（append 后复用消失）；增删由目录+文件 mtime 双覆盖 ✓。附带收益：record 原地篡改（bump 文件 mtime）现也被捕获——R0 P3-5 边界顺带消除
- 旧缓存兼容：无 append 场景 max=目录 mtime → 与旧缓存值相等 → 复用正确继续（数据未变）；有 append → 不等 → 失效重算。语义升级无假阴性/假阳性
- 性能：每次分析一次 iterdir+N stat（~200 记录+N jsonl ≈ 数百 stat，本地盘毫秒级），仅缓存判定路径执行一次。正确性必需的代价，可接受；大目录场景（>10⁴ 条目）如现瓶颈可再加记忆化——当前规模不构成问题

### 5. record 字节不变断言 — ✅ PASS
`DemandRevisionChannelTests.setUp` 捕获 `record_before = read_bytes()`；`test_valid_revision_appends_derived_from_event` 与 `test_second_revision_derives_from_previous_event` 均断言修订后 `read_bytes() == record_before`（字节级，不可变原则不破）✓。`.jsonl` 后缀不被 `load_triage_records` glob("*.json") 误读——`test_jsonl_not_globbed_by_load_triage_records` 实证 ✓

### 6. 裁决点：from 派生=事件>record、不含行内标注 — **歧义 → 澄清项随 B3（不判 finding）**
- ADR 原文（L137）：「`from` 由写入器从当前 resolve 结果自动派生（调用方不传，防伪造起点）」——**未规定派生必须覆盖行内层**；ADR resolve 权威链（§2.2.2）含行内层但那是 tpa 联查语义，非写入器派生义务
- Developer 解释成立的三依据：①立法意图=防伪造（「调用方不传」），非强制完整链；②层次边界——行内标注数据在 plan-tracker md，写入器（change_triage 层）不持有，强制包含需签名加 plan_tracker_text 参数，与「调用方不传」精神冲突；③from 无机器消费面（resolve 只消费 to 的末位合法事件）——纯审计显示
- 实际影响面：「无 record demand_source 值（存量）但有行内〔标注〕」的任务修订时，事件 from 显示 legacy 而非行内值——审计显示粒度损失，无判定影响
- 设计审查 R1 的 NF-1 修复标准（review-DESIGN-021-DESIGN-R1.md L36）同样未细化到该层
- **处置**：随 B3 CLI 接线时 Coordinator 澄清（或 ADR 下轮微注一句「from 在写入器可及域派生：事件>record；行内层属 tpa 显示关注点」）

### 7. INV-1/provenance_domain 未动=范围正确 — ✅ PASS
provenance_domain.py 仍 400 行、test_provenance_domain.py 仍 471 行（与 R0 全文读时一致），零 DSR/revision 痕迹（grep 实证）；29 个 provenance 测试含于 332 全绿。INV-1 same-priority 微调与 Check 接线属 B3 批次承载——非漏项。R0 P3-2 升级提醒（**必须先于 B3 接线完成微调**）继续有效。

## 增量声明交叉核对（以 diff 为准）

| 声明 | 核对 |
|------|------|
| append_demand_revision：append-only + Never-raises + 五重 fail-closed | ✅ 一致（task_id 形状 L855/to 非三值 L857/basis 空 L863/basis_kind 非三值 L868/无 record L879——全部 error dict 零写入） |
| from 写入器派生（事件>record；行内不可达） | ✅ 一致（L885-891 + 专测） |
| event_id=DSR-{TASK}-{seq:03d} | ✅ 一致（L898） |
| 机写 DSR-* evidence（10 列同构）+ 失败回滚 | ✅ 一致（G11 gate 列与主行同值 L799/L1292；回滚+自披露） |
| resolve +第四参 revision_events=None（默认≡三参） | ✅ 一致（逐例对照断言） |
| 合法事件末位权威/旧值历史快照/非法事件落回 | ✅ 一致（三分支各有专测） |
| _triage_records_mtime max-sweep | ✅ 一致 + 专测 |
| _resolve_row_demand_sources 返回 (tasks, lag_warnings)；WARN 入缓存+复用重放 | ✅ 一致（L2510-2511 重放 / L2532 入 state） |
| 测试 22 用例 / 332 OK / 343（七回归族） | ⚠️ 计数差 1：实测增量 21（11+6+4），332 OK 吻合；343 七回归族未按协议复跑（限定三族），源码级核验未发现破坏面 |

**R0 findings 处置对照**：R0 P2-1（测试类头注释反向）**已修复**——增量将注释更新为窗口协议语义 ✓；R0 P3-1（ADR 缺口注释时效）部分修复（类头已改「条款已被 ADR R0 返工版收编」，但方法 docstring 与 change_triage.py L1173 仍留旧表述）→ P3-4 续期；R0 P3-2/P3-3 本增量直接关联项：P3-3（resolve 签名）**已消解**（第四参就位）；R0 P3-5（mtime 篡改边界）**已消解**（max-sweep 覆盖）。

## Findings

| # | 级别 | 位置 | 问题 | 建议 |
|---|------|------|------|------|
| P3-1 | P3 | `change_triage.py` L885-891 / ADR-021 L137 | from 派生域歧义（重点核验 6 裁定：写入器可及域 vs ADR 完整 resolve 链）——Developer 工程解释成立、docstring 已声明、无机器判定影响；ADR 未规定到该粒度 | B3 CLI 接线时 Coordinator 澄清或 ADR 微注（「from 在写入器可及域派生：事件>record」） |
| P3-2 | P3 | `test_change_triage.py` 回滚测试 | evidence 失败回滚的 truncate 分支（已存在文件→恢复 prior_size）无直接测试——现测仅覆盖 created→unlink 分支 | 补一例：先成功一次修订，再以坏 evidence_path 修订第二次，断言 jsonl 恢复为单事件长度 |
| P3-3 | P3 | `test_change_triage.py` 修订通道负例 | append_demand_revision 五重 fail-closed 中 malformed task_id 分支无专属测试（现测 FIX-999 为形状合法的无 record 情形） | 补 `task_id="garbage"` 负例（一行断言） |
| P3-4 | P3 | `change_triage.py` L1173 / `test_change_triage.py` P2 拒绝测试 docstring | R0 P3-1 续期：ADR 收编表述三处口径不一（类头已更新为「已收编」，方法 docstring 与源码注释仍留「ADR 无此条款」旧文） | ADR 合入 commit 时统一三处注释 |
| P3-5 | P3 | `change_triage.py` event_id seq | seq=len(现有该任务事件)+1 在并发写入下可能撞号。单 Coordinator 会话模型下无实际并发（机写单线程），append-only 语义成立 | 纯讨论：若未来多写入器并存，可在 B3 CLI 层加文件锁或改用时间戳后缀；当前不动 |

## 硬门槛裁决

| 门槛项 | 阈值 | 结果 |
|--------|------|------|
| P0 阻塞问题数 | = 0 | ✅ 0 |
| 5 维度全覆盖（增量面） | = 100% | ✅ 正确性（七点核验）/ 安全性（fail-closed 五重+零注入面+审计链完整）/ 可维护性（docstring 锚定充分；P3-4 注释口径）/ 性能（max-sweep 毫秒级）/ 测试覆盖（21 用例：正/负/链式/边界/端到端/缓存时序） |
| 每条发现标注级别 | = 100% | ✅ P3×5 |
| 设计一致性（ADR §2.2.1 修订通道 + 设计审查 R1 NF-1 修复标准） | 已完成 | ✅ 事件 schema 逐字段吻合；resolve 权威链/conflict 收窄/行内滞后 WARN 三项修复标准全落地；唯一歧义点（from 派生域）判澄清项非违背 |
| AI 专项 5 项 | 全部完成 | ✅ 零 mock/零硬编码/零幻觉 API（load_demand_revisions 等实证存在）/零 TODO 残留/零过度实现（NF-1 裁定补齐项） |

## R0 遗留项状态总表（跨轮合并视图）

| R0 项 | 本轮状态 |
|-------|---------|
| P2-1 注释反向 | **已修复**（增量内） |
| P3-1 ADR 缺口注释 | 部分修复 → P3-4 续期 |
| P3-2 INV-1 微调先于 B3 | 未动（B3 承载，正确）——**升级提醒继续有效** |
| P3-3 resolve 签名 | **已消解**（第四参就位 + 零回归实证） |
| P3-4 fail-open 分支测试 | 未动（B3 可补，维持） |
| P3-5 mtime 篡改边界 | **已消解**（max-sweep 覆盖原地变更） |
