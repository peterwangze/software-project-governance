# REVIEW-FEAT-051-CODE-R1 — task-row-update 写入器 · 复审（R1）

- **任务 / 轮次**：FEAT-051 Code Review **R1**（2026-09-19）——同一 Reviewer，复审必达 T1
- **前轮引用**：`docs/reviews/review-FEAT-051-CODE-R0.md`（NEEDS_CHANGE：P0=0/P1=1/P2=3/P3=7，unresolved_blockers=1）——本报告逐条比对前轮 findings，标注已修复/部分修复/留置/新引入
- **审查对象**：`skills/software-project-governance/infra/task_row_update.py`（实测 **1,476 行**，R0 时 1,357）+ `infra/tests/test_task_row_update.py`（**40 测试**，R0 时 36）
- **范围**：仅复审 R0 findings 的处置与新增代码面；未修改任何代码；`.governance/` 净变更=0

---

## 总结论

| 项 | 值 |
|---|---|
| **总结论** | **APPROVED_WITH_NOTES** |
| P0 / P1 / P2 / P3（本轮新增） | **0 / 0 / 0 / 0** |
| **unresolved_blockers** | **0** |
| R0 findings 处置 | P1×1 已修复 · P2×3 已修复 · P3：4 项修复（①③④⑤部分）+ 3 项留置确认（②⑥⑦） |
| 新引入问题 | **无**（新增 ~119 行逐一复审，未发现正确性/安全/契约问题） |

---

## 一、R0 findings 逐条比对

### P1-1（状态 cell 首尾空白丢失）— **已修复**（双证独立复现）
- **修复实现**：新增 `_cell_parts(raw) → (lead, core, trail)`（L385-393）；`build_candidate_row` 检测读 stripped core（L444），canonical verbatim / match-span 双路径替换均在 core 上（L447-457），回填 `lead + new_core + trail`（L458-460）；op 后缀插在 core 与原 trail **之间**（L476-479）——padding 字节永不移动。docstring 同步更新并引用本审 R0 报告（L409-414）。
- **守护测试**：`test_flip_row_minimal_byte_diff`（测试 L579-598）——fixture 前导 `双空格+U+3000`、尾随 `空格+U+3000+空格`，翻转后**逐字节精确断言**（U+3000 为 Unicode 空白，旧 `strip()` 行为必吃——直击根因）。
- **红相双证**：Developer 申报修复前 4 failed 现场 + monkeypatch `_cell_parts` 模拟旧行为的 mutation 验证；**本审独立复跑 mutation**：`FIXED keeps padding=True / MUTANT keeps padding=False / RED-PHASE-PROOF=True` ✓。

### P2-1（畸形 op-id 裸 traceback）— **已修复**（实证）
- `execute_update` 入口预检（L768-782）：`require_operation_id` 失败 → 结构化 `schema_violation`，以新 mint id 承载（契约不允许 WriterResult 携带非法 id——处理正确）；`--dry-run` 分支同型预检（L1429-1442）。
- **实证**：CLI `--operation-id bad-id` → **exit 3** 结构化 JSON、零 traceback、零写入 ✓；`test_malformed_operation_id_structured_refusal` 覆盖 CLI+库双入口。

### P2-2（degenerate receipt 崩溃）— **已修复**（实证）
- 新增 `_replayable_result_face`（L514-537）：校验 `code='ok'` + 正 int new_revision（排除 bool）+ 合法 execution；replay 分支先过面检（L886-908），不合法 → `manual_intervention`「adjudicate the ledger by hand; nothing was re-executed or written」。
- **实证**：库级探针——pop writer_result 后同 op 重放 → `code=manual_intervention, execution=None, adjudicate=True, ledger 恰 1 行不变` ✓；`test_degenerate_receipt_replay_refuses_manually` 钉住。

### P2-3（裁决锁前 + 并发同 id 误报文案）— **已修复**
- replay/conflict 裁决整体移入锁内（L868-917），与 docstring 步骤 3（L741-747）「under the lock」一致——文档-实现错位消除；同 op 竞态败者现在读到胜者 receipt → 真 replay；`effect_present_without_receipt` hint 仅保留给真实崩溃窗口（receipt 确不在册而行已在目标态，L942-948）——语义正确。
- **验证**：新增 `test_concurrent_same_operation_id_single_execute_rest_replay`（8 线程同 op 同 payload，Barrier 同发 → 全 ok = 1 execute + N-1 replay、恰 1 receipt、direct 结果 new_revision==世界实测）——套件实跑通过；Developer 另申报两真进程复演（p1 execute + p2 replay 同 new_revision、ledger 恰 1 行）——**申报采信**（本审以线程模型+代码审查佐证，未独立复跑进程级场景，见 §三）。

### P3 处置对照
| R0 编号 | 内容 | R1 裁定 |
|---|---|---|
| ① | 「12 边」失准 | **已修复**——L12 改「the 11-edge TASK_TRANSITIONS table」（grep 确认；11=2+2+3+1+1+0+2 与 R0 程序化复核一致）。EVD-1105/triage JSON 的同款失准出票面，维持报 Coordinator |
| ② | dry-run/execute 拒绝码不一致（cross_record_violation vs schema_violation，L1317-1318） | **留置确认**——exit 同为 3、不影响 disposition 分流；P3 不阻断，接受遗留（建议随 schema v2 或下次触达 `_dry_run` 时顺手修） |
| ③ | POSIX 锁无界阻塞 | **已修复**——`LOCK_EX\|LOCK_NB` + 40×1.4^n（截断 10）有界退避 + `LockContention`（L617-634），与 Windows 分支同曲线；fail-closed 语义全平台一致 |
| ④ | rename 持久性 | **已修复**——`os.replace` 后父目录 fsync，OSError 吞掉（Windows best-effort，L691-698）；失败不误清已 replace 的 temp ✓ |
| ⑤ | 命名/死码 5 子项 | **部分修复**——`RECEIPT_RECORD_KIND` 重命名 ✓、`TASK_ROW_UPDATE_RESULT_CODES` 死映射 "replay" 删除 ✓（docstring 说明 replay 即 ok，无独立退出码）；**余 3 子项留置**：`_dry_run(refs=…)` 死参数（L1247）、replay 判定 prose 前缀耦合（L1458）、`expected_revision=1` 占位无注释（L829）——P3 级可遗留，R2+ 触达时顺手清 |
| ⑥ | schema v1 全文件扫描锚定边界 | **留置确认**——schema v2 议题（section-scoped），当前 fail-closed 无错写路径 |
| ⑦ | Unicode 行分隔符吞行 | **留置确认**——理论边角（tracker 实测无此类字符） |

### 新引入检查
新增 ~119 行（`_cell_parts` / `_replayable_result_face` / 两处 op-id 预检 / 锁内裁决 / POSIX NB / dir fsync / 4 测试）逐行复审：无正确性、安全、契约面问题；契约只读消费不变；WriterResult 律各构造点合规（replay 分支现显式构造合法 ok 面）。微瑕（不列 finding）：`build_candidate_row` 内 `_cell_parts` 对同一 cell 调用两次（L444 取 core 判定、L459 取 padding 回填）——语义清晰，纯微冗余。

---

## 二、独立复验表（R1）

| # | 复验项 | 方法 | 结果 |
|---|---|---|---|
| 1 | 全套件实跑 | `pytest test_task_row_update.py -q` | **40 passed, 0.61s** ✓ |
| 2 | mutation 红相复跑 | monkeypatch `_cell_parts`→`("", raw.strip(), "")` 后构造翻转 | FIXED keeps padding=True / MUTANT=False / **RED-PHASE-PROOF=True** ✓ |
| 3 | 真表 dry-run 复演 | `--dry-run completed→committed` 于真实 tracker（带旗标复核） | 零写入：SHA-256 前后一致、无 ledger/lock ✓ |
| + | 畸形 op-id CLI 探针 | `--operation-id bad-id`（隔离 temp） | exit 3 结构化 schema_violation，零 traceback ✓ |
| + | degenerate receipt 库探针 | pop writer_result 后同 op 重放（隔离 temp） | manual_intervention / execution=None / adjudicate / ledger 完整 ✓ |
| + | contracts 回归抽查 | `pytest test_contracts.py -q` | **157 passed** ✓ |
| 申报采信（未独立复跑） | registry 77；verify+archguard R1~R7 全仓门禁；并发同 op **两真进程**复演 | 超出本审复验预算；进程级场景以 8 线程同 op 测试全绿 + 锁内裁决代码审查佐证 | 标注为 Developer 申报 |

## 三、Notes（APPROVED_WITH_NOTES 备注面——均为非阻断）

1. **P3②⑥⑦ + P3-5 余 3 子项留置**：确认合理（P3 级、fail-closed 或纯文档性）；建议登记为 0.86.0 批 2.x 触达 `_dry_run`/schema v2 时的顺手项，勿静默丢失。
2. **申报采信面**：registry 77、verify+archguard R1~R7、两真进程并发复演未由本审独立复跑（预算 3 项已用满并追加 3 项探针）；上列测试与代码证据足以支撑本结论，但发布门（M-2）仍应按既有义务复跑全仓门禁。
3. **勘误传播**：EVD-1105 与 `.governance/change-triage/FEAT-051.json` title 中的「12 边」失准出本票文件面，报 Coordinator 择机勘误（不阻断本票）。
4. `build_candidate_row` 内 `_cell_parts` 双调用微冗余（见 §一新引入检查）。

## 四、复审裁定

R0 全部 BLOCKING 面（P1-1 + P2×3）修复经代码审查 + 实证复跑确认；红相双证之 mutation 路径由本审独立复现；新增测试 4 条各自精准钉住对应修复；无新引入问题。硬门槛：P0=0 ✓、5 维度覆盖 ✓、逐条级别标注 ✓、设计一致性（round-2 §1 五步+组合并发、round-3 P1-1 只读消费）✓、AI 专项 5 项 ✓。

**APPROVED_WITH_NOTES — unresolved_blockers=0**。可进入 commit/收尾流程；P3 留置项按 §三.1 登记。

---
*复审完毕（R1）。本报告为 R1 唯一事实源；未修改任何代码；`.governance/` 净变更=0。*
