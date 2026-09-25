# Review FEAT-062 · CODE · R1 —— F-1/F-2/F-3 修复复审（M7.4 T1 同席快速复审）

> 审查人: Code Reviewer Agent（同席，只读）· **轮次: R1** · 日期: 2026-09-25
> **前轮引用**: docs/reviews/review-FEAT-062-CODE-R0.md——APPROVED_WITH_NOTES（P0=0 · P1=1 · P2=1 · P3=5 · unresolved_blockers=0）；findings F-1（P1 管道符）/F-2（P2 finalize LockContention）/F-3（P3 CLI ValueError）/F-4~F-7（P3 备查）
> 审查对象: 工作树未提交 diff（`git diff --numstat` 实测）: `infra/closure_chain.py`（**+673/−9**；R0 基线 +631/−6 → 修复增量 +42/−3）+ `infra/tests/test_closure_chain.py`（**+750/−0 纯追加**；R0 基线 +679 → 修复增量 +71 = 3 新测试 L2260-2277/L2346-2395）
> 复审口径（任务指定快速面）: F-1~F-3 修复形态 + 回归；实测 = 69P 复跑 + verify 复跑 + CLI 探针复验；R0 findings 逐条比对（已修复/未修复/新引入）；FIX-384 并行面继续零触碰；全程零 `.governance` 写入

---

## 1. 总结论

## **APPROVED**（P0=0 · P1=0 · P2=0 · P3 维持 4 项备查 · **unresolved_blockers=0**）

R0 三项修复全部核验通过（§2 逐条比对），无新引入问题（§3 −9/+71 构成逐行核对）；69P 复跑全绿 + verify PASSED（§4）；CLI 探针三连实测结构化拒绝（§4）。复审链达成通过终态（APPROVED，Check 30 可消费结束）。

**一项管理面注记（非代码发现，不计 finding）**：任务声明「F-7 已登记 FEAT-061 cutover 验收项」**未能落纸核实**——plan-tracker FEAT-061 行（L109 全行核对）与 version-plan-0.88.0 C1 行（全文 587 字符核对）均无 R0-F7/cancel 对账字样，session-snapshot 无条目，evidence-log 仅 triage 行。按事实依据红线如实记录为**声明未核实**；F-7 本身（P3 潜伏耦合）代码面维持 R0 判定不变。建议 Coordinator 在任务收尾机录时将 F-7 登记补落 FEAT-061 行或对应 cutover 验收面（一行附注即可）。

---

## 2. R0 findings 逐条比对（复审本质=验证修复）

| # | R0 级别 | 判定 | 修复形态核验（行号为当前工作树） |
|---|---------|------|--------------------------------|
| F-1 | P1 | **已修复** | `cancel_closure` 入口 for 循环内、换行检查（L2348-2352）之后新增 `if "\|" in value` 门（L2353-2363）——`schema_violation` 零写拒绝 + detail 完整诊断（writer 表格行分隔符语义 + 「deterministically unwritable / permanently pending」后果），`review-FEAT-062-R0 F-1` 引用注释在场；authorized_by/reason 两字段同循环覆盖（两向）；位置在终态 append 与 expected_status 校验之前（零写门区域内，语义正确）。module docstring 同步（L135-138——「newlines and raw `\|` are refused at the zero-write gate…review-FEAT-062-R0 F-1」）。验收钉 `test_pipe_character_refused_at_zero_write_gate`（test_closure_chain.py:2260-2277）：**两向红绿**（reason 携 `a\|b` / authorized_by 携 `coord\|session`），断言 exit 2 + schema_violation + detail 含 `\|` + 字节快照相等 + 无 cancel 事件；**红相真实性**=docstring 明示判据（放行管道符→DEC 行确定性不可写→腿永久 pending 破坏收敛）+ R0 报告 §3-7 实测探针记录（修复前 writer StoreError 实锤）——该测试对 R0 代码必红（R0 无门→终态落→exit 3≠2） |
| F-2 | P2 | **已修复** | `cmd_finalize` 新增 `except LockContention`（L2566-2572）→ `{code: "lock_contention", disposition: "retryable"}` 结构化拒绝；**exit 映射 disposition 感知**（L2580-2581：`3 if disposition == "retryable" else 2`）。**既有 finalize 拒绝码零变化论证**：cross_record_violation/schema_violation/manual_intervention 的 disposition 均非 retryable → 仍 exit 2，与 R0 的 `return 2 if error else 0` 行为等价（删除行 L 旧映射即此替换，−1+2）。验收钉 `test_finalize_lock_contention_structured_refusal`（:2352-2376）：真实锁竞争注入（测试进程 `cc._RunLock` 持锁 → finalize 子进程 10s 预算耗尽 → LockContention）——断言 stderr 无 Traceback + exit 3 + code/disposition + journal 无 finalized 事件；**红相真实性**=R0 报告 §2 F-2 代码路径记录（cmd_finalize 无捕获→LockContention 逃逸→traceback exit 1 空 stdout）——对 R0 代码必红。代价：套件时长 79.53s→92.86s（该测试 ~10s 锁预算等待，预期内） |
| F-3 | P3 | **已修复** | `cmd_cancel`（L2594-2600）+ `cmd_finalize`（L2573-2578）各新增 `except ValueError` → `schema_violation` JSON（与 cmd_run/cmd_status 同款约定，注释引用 F-3）；cmd_cancel 的 LockContention 仍由 cancel_closure 内部处理（注释明示分工）。验收钉 `test_malformed_closure_id_structured_refusal`（:2378-2395）：cancel+finalize **双面**（`--closure-id not-a-closure-id`）断言无 Traceback + exit 2 + schema_violation；**红相真实性**=R0 报告 §3-8 实测探针（exit 1 traceback 实锤）——对 R0 代码必红 |
| F-4 | P3 | 未修复·**维持备查** | L2185 `journal_terminal: True` 硬编码仍在（R0 判定不变——语义透明度小缺口，无行为危害） |
| F-5 | P3 | 未修复·**维持备查** | L186 docstring「fresh CLI args are disclosed」仍在、payload 仍无披露位（R0 判定不变） |
| F-6 | P3 | 未修复·**维持备查** | L311 CANCELLABLE_STATUSES 仍含 awaiting-world-check（不可达条目，R0 判定不变——拒绝方向保守正确） |
| F-7 | P3 | 未修复·**维持备查+登记待落纸** | replay_source 判别（L2135-2139）与 projection_status 丢弃未动——代码面 R0 判定不变（今日 md backend 不触发）；**管理面**：任务声明「已登记 FEAT-061 cutover 验收项」经 plan-tracker L109 全行 + version-plan C1 行全文 + session-snapshot + evidence-log 四面核查均未落纸——按事实红线记录为未核实，建议收尾机录时补记（见 §1 注记） |

**新引入检查**: 无——修复增量全部对应 F-1/F-2/F-3（§3 构成核对）；69P 全绿含全部 R0 场景测试（竞争单终态/F-5④/中断恢复/锁所有权等零回归）。

---

## 3. diff 构成逐行核对（防夹带）

- **−9 行构成**（vs R0 −6）: R0 原 6 行（空行 / `if finalized:` / epilog 3 行 / handlers 字典行）+ 修复新增 3 行删除 = `payload = finalize_closure(...)` 2 行（重排进 try: 块）+ `return 2 if payload.get("error") else 0` 1 行（→ disposition 感知映射）。**全部为 F-2/F-3 修复直接产物，无意外删除**。
- **+71 测试行**: 3 个新测试方法（L2260-2277 管道符 18 行 + L2346-2395 CLI 拒绝类 50 行含类头）≈71 行——数量吻合；import 块字节不变策略继续保持（static-pin L86 锚不动——verify PASSED 含 static-pin 面）。

---

## 4. 独立复验（R1 实测——Reviewer 本机实跑）

| # | 项目 | 方法 | 结果 |
|---|------|------|------|
| 1 | 全套件 69P | `pytest infra/tests/test_closure_chain.py -q` | **69 passed in 92.86s**——66+3 与申报一致；时长增量=F-2 测试锁预算等待（预期） |
| 2 | verify 全量 | `python infra/verify_workflow.py` | **PASSED, exit 0**——申报「无 WARN」与输出尾部一致 |
| 3 | F-1 CLI 探针 | `cancel --authorized-by "coord\|x"` | **结构化 schema_violation JSON + 完整诊断 detail（含 `\|` 与 permanently pending 语义），exit 2**——无终态事件 |
| 4 | F-3 CLI 探针（cancel） | `cancel --closure-id bogus` | **结构化 schema_violation JSON，exit 2**——无 traceback |
| 5 | F-3 CLI 探针（finalize） | `finalize --closure-id bogus --commit-sha deadbee` | **结构化 schema_violation JSON，exit 2**——无 traceback |
| 6 | diff 构成 | `git diff --numstat` + 删除行全貌 | §3 核对通过——无夹带 |

---

## 5. 复审终态声明

- R0 findings 处置: F-1/F-2/F-3 **已修复**（附验收钉，红相真实性经 R0 实测记录+测试判据双证）；F-4/F-5/F-6 维持备查（P3 非阻塞，R0 §6 修复建议继续有效）；F-7 代码维持备查 + 登记声明待落纸（§1 注记）。
- 硬门槛: P0=0 ✓ · 5 维度 R0 已覆盖且本轮改动不触及维度结论 ✓ · 发现全部有级别+行号+证据 ✓ · 设计一致性 R0 八焦点不受修复影响（F-1 增强限定入口完备性、F-2/F-3 为 CLI 面结构化拒绝补齐——均朝 R0 指出方向收敛）✓ · AI 专项 5 项 R0 全过，修复未引入 mock/TODO/幻觉 API（3 新测试同为真实子进程/真实锁注入）✓
- **结论: APPROVED**（零 BLOCKING，可合并）· **unresolved_blockers=0**
- 复审链: R0 APPROVED_WITH_NOTES → R1 APPROVED——Check 30 可消费（轮次连续 R0→R1 ✓、终态通过 ✓、无熔断触发 ✓）。
