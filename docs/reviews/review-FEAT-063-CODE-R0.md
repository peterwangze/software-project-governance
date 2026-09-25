<!-- machine-record: FEAT-063 | reviewer: code-reviewer | round-suggestion: rework | verdict: NEEDS_CHANGE | unresolved_blockers=1 -->

# Code Review R0 — FEAT-063 closure 重开 + 异常接管（0.88.0 阶段 E2）

- **轮次声明**：R0（首轮审查；无前轮引用）。
- **审查对象**：工作树未 commit diff vs 基线 `14797be`（FEAT-062 提交），严格限定 2 文件——`skills/software-project-governance/infra/closure_chain.py`（**实测 numstat +808/−52**）、`skills/software-project-governance/infra/tests/test_closure_chain.py`（**实测 numstat +423/−0**）。已验证两文件在 `14797be..HEAD`（`6360ab1`）之间**无已提交改动**——diff 完全为工作树未提交面，纯粹。
- **并行面隔离**：工作树同时含 FEAT-044（`loop_engine.py`/`loop_telemetry.py`/`test_loop_telemetry.py`）+ FIX-385（`archive.py`/`test_archive.py`）改动，本审查零触碰；diff 读取时按文件路径过滤。
- **审查者**：Code Reviewer Agent（只读；全部实测在 `%TEMP%` 隔离探针内完成——`fe063_probe*.py` + pytest，真实 `.governance/` 零写入）。
- **结论**：**NEEDS_CHANGE**（unresolved_blockers=**1**——P0-1 takeover TOCTOU 竞态，活体复现；P1×2 测试看护缺口；P2×4；P3×4 备查）。

---

## 1. 申报核对

| 申报项 | 申报值 | 实测值 | 裁决 |
|---|---|---|---|
| closure_chain.py 增删 | +797/−45 | **+808/−52**（`git diff --numstat 14797be`） | ❌ 数字偏差（P2-4）——申报口径疑为中途统计 |
| test_closure_chain.py 增删 | +430/−0 | **+423/−0** | ❌ 数字偏差（并入 P2-4） |
| 测试 | 83P（69 基线+14 新） | **83 passed**（110.02s）；`-k "ReopenLineage or ExecutionGenerationFencing" --collect-only` = **14/83**（7+7，69 deselected） | ✅ |
| verify | PASSED | **== Verification Result: PASSED ==**（verify_workflow.py） | ✅ |
| 相邻 204P | 申报 | 本轮未复跑相邻套件（并行面文件属 FEAT-044/FIX-385 审查域，且相邻套件不 import closure_chain 两文件的改动面——隔离性由 numstat 文件清单背书） | ⚠️ 未复验，交 Coordinator 汇总时以并行面审查为准 |
| CLI 探针结构化拒绝 | 申报 | **11/11 探针 PASS**（§6 探针 1） | ✅ |
| 心跳语义三层如实 | docstring/detail/fence_note | ✅ 三层均在（`takeover_execution` docstring L2653-2661、fence refusal detail L2706-2717 含 "heartbeat timeout is never a stop proof"、成功 payload `fence_note` L2868-2872 含 "not a stop proof"） | ✅ |

## 2. MUST 重点逐项结论

### ① 重开零擦除 + 单一后继 + recorded intent 绑定 ✅
- **逐字典相等断言真实性**：`test_reopen_cancelled_records_linkage_zero_erasure` 断言 `events_after[:-1] == events_before`（dict 级逐事件相等）+ 长度恰 +1 + 新事件通过 `_validate_closure_event` 与 `check_cas_monotonicity` 双校验 + status 面仍 `cancelled` + resume 拒绝 exit 2。**判定的真实性**：`reopen_closure` 全程只调用 `_append_closure_event` 一次（L2971-2989），无任何改写/删除路径；实现与断言一致，**非摆拍**。
- **单一后继完备性**：二次 reopen 拒绝检查（L2940-2951）读取的是 run lock 内最新加载的 events（`_reopen_locked` 在 `reopen_closure` 的 `_RunLock` 内执行 L3029-3031），任何已成功 reopen 必然留下 `closure_reopened` 事件 → 第二次必然命中拒绝。检查点与 CAS 点（同一把 run lock）重合，**竞态不可达**。
- **--reopen-of mismatch 拒绝**：`_resolve_reopen_linkage` L2908-2914（`expected_successor != successor` → ValueError "recorded linkage stands"）。实测：CLI `run --closure-id <fresh> --reopen-of <orig>` → exit 2 + schema_violation + "recorded successor"（探针 1 P10）。
- **attempt 链递推**：Reviewer 库层探针实测 3 级深化通过（attempt 1→2→3，第三级 successor 的 `closure_started.inputs.reopen_attempt=="3"`）——实现正确；但**测试套只实测到 2 级**（P2-1）。

### ② fencing 写端三面完备性 ✅（无第四面遗漏）
| 面 | 位置 | 实测 |
|---|---|---|
| 入口 | `_run_locked` L1649-1657（fresh start 零写入不记审计；resume 记一条幂等 `closure_fenced`） | ✅ 探针/测试双证 |
| 每可执行步 | L1681-1691——位于 halt-continue 之后、`step.kind=="summary"` 分支与 probe 之前 → **summary 步在声明范围内被覆盖**（"subprocess spawn / summary emission"），且 probe 在 check 之后 → fenced 时 **no probe**（零效果声明成立） | ✅ 字节级断言（tracker/evidence/locks 三文件 `read_bytes()` 前后相等，`test_takeover_fences_stale_holder_writes`） |
| finalize | L2003-2012（位于 finalized-replay 与 cancelled 终态检查之后——**replay finalize 是零写入端点，不受 fence 约束是正确语义**；cancelled 优先拒绝同样正确） | ✅ 测试 + CLI 探针 exit 2 |
- **第四面排查**：`closure_status` 纯只读无需设防；cancel 按设计不 fence 终态（termination is not submission，锁腿单独 skip——见 ⑤）；`closure_reopened`/`takeover` 是授权写非执行写，不在 fence 语义内。**无遗漏面**。
- **ExecutionFenced 零效果强度**：journal 仅 +1 审计事件（幂等——第二次 fence 事件数不变，L2828-2829 实测）；`.governance` 其余文件字节级不变。fresh start 被 fence 时 journal 为空（`test_new_holder_runs_and_third_closure_fenced` L350 `_chain_events(...)==[]`）。
- **closure_fenced 幂等审计**：`_record_fenced_event` L2713-2730 any-检查 + append，仅在 run lock/finalize lock 内调用 → check-then-append 竞态不可达。✅

### ③ 接管安全性 ⚠️（一处 P0）
- **同 holder 重接管拒绝**：实现锁外 pre-check（L2778-2787）+ 锁内 re-check（L2829-2837）双检。**实现正确**（Reviewer CLI 探针实测 exit 2 + "already holds"），**但无测试**（P1-2）。
- **首次接管无 fence 对象**：prior_holder=None → 不获取 old lock → 写 generation 1（L2843-2855）——`test_takeover_fences_stale_holder_writes` 断言 `generation==1` + `prior_holder_closure_id is None`。✅
- **在途链不 fence**：常规路径（prior_holder 从锁外读到锁内不变）成立——`test_takeover_in_flight_refuses_lock_contention` 真锁注入实测。**但锁内 re-read 更新 `prior_holder`（L2838）时，已获取的 run lock 仍绑定锁外读的旧 id（L2804）——并发双 takeover 竞态下 promotion 逃逸真实 prior holder 的 run lock 串行化** → 活体复现在途 executor 被误 fence（**P0-1**，§4）。
- **锁顺序无死锁**：takeover 持 generations lock → old run lock；run/finalize/cancel 只持 run lock 不反向获取 generations lock（fence check 只读 sidecar）。✅
- **`_RunLock` 释放安全性**：`__enter__` 失败（LockContention）时 `_fd=None` → finally 中 `__exit__` no-op（L1173-1174 守卫）——takeover 的 finally 双释放路径安全。✅

### ④ sidecar 健康 ✅（一处 P2）
- **原子替换**：`_write_execution_generations` L2656-2668 同目录 `.tmp` + `os.replace`。✅
- **损坏 fail-closed 对所有任务**：`_load_execution_generations` L2635-2654 unreadable/invalid-shape → `({}, error)`；`_execution_fence_refusal` 对 error → 所有 task 一律 `revision_conflict`（authority 不可判定）。探针实测 CLI exit 2 + "unreadable" + detail 携带恢复指引（"repair or remove .governance/closure-generations.json"）；测试补验 takeover 同场景 → `manual_intervention` + unlink 修复后世界恢复。✅
- **向后兼容**：missing file → `({}, None)` unfenced（测试 unlink 后正常跑 + 探针 unbound task 正常）。缺 `tasks` 键 → unfenced；畸形 record（holder 缺失）→ fail-closed 方向（fenced）。✅
- **持久性偏离**：无 flush+os.fsync——writer 家族 6 处（governance_store.py L449-450、task_row_update.py L695-696、archive.py L1523-1524 等）均 fsync。后果方向保守（断电回退→旧代际保守拒绝新 holder，不会错误放行），但 fencing 权威记录的持久性弱于家族标准（**P2-3**）。

### ⑤ 旧代际 cancel 语义 ✅
- 终态 + DEC 照常：`_cancel_locked` 无入口 fence 检查 → `closure_cancelled` 事件 + DEC leg 照常（L2536-2539）；锁腿 `skipped_fenced`（L2339-2350，`operation_id=None`、world=None）。**ARCH-09 同型一致**（stale owner 不释放新 holder 的 dispatch locks）——测试断言新持有者锁保留（`file_locks`/`active_tasks`）+ DEC leg done + reconciliation consistent + journal_terminal。
- 对账接受 skipped_fenced：L2424/L2431 并入 done 集合 → `consistent=True` → CLI exit 0。语义说明：此处 `locks_world_clear` 表示「本代际无需清理」，非「世界无锁」——设计意图与实现一致，报告如实记录该语义重载。
- replay 幂等：二次 cancel（prior 分支）→ 锁腿再次 skip → 恒收敛。✅

### ⑥ 14 测试判别力 ⚠️（红态真实；三处覆盖缺口）
- **红态真实性** ✅：真实 subprocess/真实 `_RunLock` 注入（`with cc._RunLock(lock_path, 1.0)` 持锁制造 in-flight）/真实 writer CLI（DEC 行、locks-release 走 governance_store）；零写断言用 `.governance` 全树字节快照（`_gov_snapshot` L2008-2014）；零效果断言用三文件 `read_bytes()` 字节级相等。**无 mock 摆拍**。
- **缺口 1**（P1-1）：per-step fence re-check 面无红态测试（入口 resume/fresh 与 finalize 有；「入口过→步中 out-of-band fence→下一步拒绝」无）。
- **缺口 2**（P1-2）：同 holder 重接管拒绝无测试（实现双检正确，探针已代验）。
- **缺口 3**（P2-1）：attempt 链 3 级深化无测试（申报「attempt 链深化 3 级实测」与测试套不符；实现经 Reviewer 探针代验正确）。

### ⑦ −52 删除行核对 ✅ 无夹带
52 删除行（numstat 实测）全部落入 15 组重构点，逐行核对：
1. single-flight docstring 重写（8 行→新 11 行，fence 语义如实更新）；2. F-5 措辞 "disclosed"→"ignored"（3 行）；3. run_chain 签名加 `reopen_of`（1）；4. docstring item 5（1）；5. `inputs` dict 复制（1——必要改动：注入 reopen_* 不污染调用方 dict，行为改进）；6. finalize `started` 提取（1）；7. status task/chain_id 提取（2）；8. `_cancel_locks_leg` docstring（1）；9. `_cancel_reconciliation` 签名+docstring（4）；10. locks_world_clear/legs_done 扩集合（3）；11. journal_terminal 实测化（2，F-4）；12. cancel 字段校验提取为 `_registered_field_refusal`（21→4，消息文本变化见 P3-1）；13. epilog exit-code 更新（2）；14. cmd_run 传参（1）；15. main handlers（1）。**无与 FEAT-063 无关的功能行删除**。

### ⑧ 验证复现 ✅（详见 §6）
83P 全绿（110.02s）+ 14 新测试收集确认 + verify PASSED + CLI 探针 11/11 + 探针 2（attempt 3 级 4/4 + TOCTOU 活体复现 3/3——后者是红态证据非绿态）。

### ⑨ F-4/F-5 顺带修正 ✅
- **F-4（journal_terminal 实测化）**：`_cancel_locked` L2542 在 legs 执行后 re-read journal（`events, problems_after = _load_closure_events(...)`），L2568-2569 传入对账；`journal_terminal` 由硬编码 `True` 改为 `any(e.get("event_type")=="closure_cancelled" for e in events)`（L2433-2434）——**post-leg world 实测确认**。
- **F-5（docstring 措辞）**：L33-40 "fresh CLI args are **ignored**, never re-recorded"——与实现一致（replay 分支 L2525-2533 仅读 recorded intent，CLI args 不进 payload）。

## 3. 五维度结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | **不通过（1×P0）** | P0-1 TOCTOU 竞态（活体复现）；其余逐行核验通过（重开/fencing 三面/cancel 语义/F-4/F-5） |
| 安全性 | 通过（含 1×P2 建议） | fail-closed 方向全对（corrupt→拒/missing→放行=兼容/畸形 record→拒）；字段纪律共享 helper（单行/无竖线/非空，FEAT-062 规则复用）；无注入面（JSON 侧车 + append-only journal）；P2-3 fsync 缺失 |
| 可维护性 | 通过 | helper 提取合理（`_registered_field_refusal` 三消费方）；docstring 诚实边界（heartbeat 声明是亮点）；`__all__`/事件枚举封闭式扩展；模块 3377 行偏大但分区注释清晰 |
| 性能 | 通过 | fence probe = 每 step 一次 sidecar 全量读（O(file)），step 数小、文件小（per-task map），可接受；无 N+1/O(n²)；`_record_fenced_event` 幂等避免审计膨胀 |
| 测试覆盖 | **不通过（2×P1 + 1×P2）** | 核心路径强看护（零擦除/零效果/幂等/竞态锁注入），但 P1-1 per-step 面、P1-2 同 holder、P2-1 attempt 3 级三缺口 |

## 4. 发现清单

### P0-1（阻塞）takeover_execution TOCTOU——promotion 逃逸真实 prior holder 的 run lock 串行化
- **位置**：`closure_chain.py` L2770（锁外 pre-read）→ L2788（锁外提取 prior_holder）→ L2792（拿 generations lock）→ L2804-2808（获取**锁外 id** 的 run lock）→ L2819（锁内 re-read）→ **L2838（锁内更新 `prior_holder` 但不重新获取对应 run lock）**。
- **事实**：锁内 re-read 发现 holder 已从 A 变为 B 时，代码把 `prior_holder`/`prior_generation` 更新为 B 的值并照常提升，而已持有的仍是 A 的 run lock——B 的 run lock 全程未获取。
- **活体复现**（Reviewer 探针 2，`%TEMP%\fe063_probe2_`）：patch `_load_execution_generations` 首调后同步完成 T2 takeover（A→B，gen 2）并**持有 B 的 run lock**（B「在途」）→ T1 takeover（new_holder=C）返回成功（无 error）→ record 变为 gen 3 / holder=C / prior=B → **B 的下一次 run 被 `revision_conflict` fence**。完整时序 7/7 可重复。
- **影响**：违反本 slice 申报的核心不变量「提升串行于前持有者 run lock——在途链 lock_contention 不 fence / takeover never fences a mid-flight run」（docstring L2793-2804、模块 docstring 心跳段）。后果为在途合法 executor 被误中断（需人工再 takeover 恢复）；世界不损坏（写端 fence 保底），但该不变量是异常接管语义的安全承诺本体。触发前置：两个并发 takeover 且窗口内 holder 变更——异常处置场景（多操作者介入同一异常任务）并非不可达。
- **修复建议**：锁内 re-read 后若 `prior_holder` 与已获锁绑定的 id 不一致 → 释放旧锁并返回 `lock_contention` retryable（零写入，与「never fences a mid-flight run」自洽）；不建议在锁内循环换锁（拉长 generations lock 持有时间）。补红态测试：锁内 re-read 前变更 holder 的注入测试（与 P1-1/P1-2 同批）。

### P1-1（关键）per-step fence re-check 面零测试看护
- **位置**：`test_closure_chain.py` ExecutionGenerationFencingTests（7 测试全清单核对）；`closure_chain.py` L1681-1691。
- **事实**：三面中入口（resume/fresh）与 finalize 有红态测试；「入口通过 → sidecar 被出带改写 → 下一可执行步（含 summary）拒绝」的红态无任何测试。per-step re-check 是 out-of-band-edit 残余的唯一防线，无看护的防线等于未验证的防线。
- **建议**：补一个测试——holder run 前 takeover 给第三方（或直接改 sidecar），断言步进中断 + journal +1 fenced + 世界字节不变。

### P1-2（关键）同 holder 重接管拒绝零测试看护
- **位置**：`closure_chain.py` L2778-2787（锁外）+ L2829-2837（锁内）；测试无。
- **事实**：实现双检正确（Reviewer CLI 探针实测 exit 2 + schema_violation + "already holds"），但测试套无任何用例——回归防护缺失。
- **建议**：补测试断言两次 `takeover_execution(--new-holder 同 id)` 第二次拒绝 + record 零变化。

### P2-1（建议）attempt 链 3 级深化无测试；申报「3 级实测」与测试套不符
- **位置**：`test_closure_chain.py` `test_successor_binds_recorded_linkage_and_resumes`（最深 attempt 2）；`closure_chain.py` L2944-2951（own_attempt 递推）。
- **事实**：Reviewer 库层探针实测 3 级通过（attempt 1→2→3、第三级 inputs `reopen_attempt=="3"`）——**实现正确**；但申报中的「attempt 链深化 3 级实测」在测试套中不存在，递推分支（从 successor inputs 解析 attempt→+1）无回归防护。
- **建议**：补 3 级链测试（reopen→successor 终态→reopen→断言 attempt 3 + inputs）。

### P2-2（建议）successor 丢失 `--reopen-of` 时 attempt 编号静默重置
- **位置**：`closure_chain.py` L2944-2951（own_attempt 解析失败 → 1）；`_reopen_locked` run_note L2994-3006。
- **事实**：successor 的 run 若不按 run_argv 携带 `--reopen-of`（操作者手滑），将以 fresh attempt-1 身份运行——lineage attempt 在链上分叉/重置，且无全局校验可拦（single-successor 纪律只防原 closure 二次 reopen，不防 successor 侧丢绑定；successor id 在 mint 前不存在于任何 journal，无法本地识别「我是 successor」）。Reviewer 探针首版即触此形状（attempt-3 successor 的 inputs 实测 `reopen_attempt=="2"`）。当前靠 run_note 文档化提示 + `reopen_lineage` status 披露兜底。
- **建议**：run_note 已属合理缓解；后续 slice 可评估 successor-id 全局索引或 reopen 时对「同 task 无 journal 的悬挂 successor」提示。不阻塞本轮。

### P2-3（建议）generations sidecar 写入无 fsync——偏离 writer 家族持久性惯例
- **位置**：`closure_chain.py` L2656-2668（`tmp.write_text` + `os.replace`，无 flush/fsync）。
- **事实**：writer 家族 6 处均 flush+fsync（governance_store.py L449-450、task_row_update.py L695-701、archive.py L1523-1524、loop_paro_engine.py L459-460、loop_migration.py L497-498、baseline_metadata.py L625-626）；closure journal 底层 loop_event_log 同样无 fsync（sidecar docstring 自称 "same ownership discipline as the closure journal"——与 journal 一致、与 writer 家族不一致）。
- **影响**：断电/崩溃窗口代际提升可能静默回退→旧 holder 解封 + 新 holder 被保守拒绝（方向安全、语义回退）。fencing token 是异常接管场景的权威记录，建议对齐家族标准。

### P2-4（建议）申报 numstat 与实测不符
- **事实**：申报 +797/−45 + 430/−0；实测 `git diff --numstat 14797be` = **+808/−52 + 423/−0**（closure_chain Δ+11/−7、test Δ−7）。疑为中途时点统计。建议申报口径以 `git diff --numstat` 为准并附生成时点。

### P3-1（备查）cancel 字段校验消息文本变化（helper 提取副产品）
- **位置**：`closure_chain.py` L2132-2158（`_registered_field_refusal`）vs 基线 cancel 内联块。
- **事实**：schema_violation 拒绝的 detail 由 `"cancel {0} is required..."` 变为 `"{0} is required..."`（"cancel " 前缀丢失；`\n`/`|` 两条消息同理）。code/disposition/零写语义不变；全测试套无该文本断言（83P 全绿背书）。纯文本面，留档即可。

### P3-2（备查）`_resolve_reopen_linkage` 忽略 journal problems
- **位置**：`closure_chain.py` L2888-2889（`events, _problems = _load_closure_events(...)`）。
- **事实**：torn-line 损坏时基于部分事件解析 linkage；损坏最坏走向 = "no journal"/"no closure_reopened event" 拒绝（fail-closed 方向）。继承 `_load_closure_events` 既有容错语义（cancel 同样消费），可接受；留档。

### P3-3（备查）record.generation 畸形时重置为 1
- **位置**：`closure_chain.py` L2843-2846（非 int/bool → generation=1）。
- **事实**：审计单调性破坏（3→1）；fence 语义不受影响（fence 比较 holder id 非代际数值）；畸形 record 本属 fail-closed 邻域。留档。

### P3-4（备查）run_argv 为展示用途
- **位置**：`closure_chain.py` L2985-2998。
- **事实**：inputs 值含空格/特殊字符时打印 argv 不可直接粘贴执行（list 形式已是最小误读面；不含 reason 等自由文本）。留档。

## 5. AI 代码专项 5 项

| # | 检查项 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock 残留 | **无** | 14 新测试全部真实 subprocess/真实 `_RunLock` 注入/真实 governance_store writer CLI/真实 git；无 unittest.mock 使用 |
| 2 | 硬编码返回值 | **无** | 全部路径经真实状态机（journal/sidecar/锁/世界探针）；无条件返回固定 payload 的形状 |
| 3 | 幻觉 API | **无** | 新引用符号逐一核验存在于本模块/标准库：`_resolve_reopen_linkage`/`_execution_fence_refusal`/`_record_fenced_event`/`_registered_field_refusal`/`ExecutionFenced`/`REOPENABLE_STATUSES`/`CLOSURE_GENERATIONS_FILENAME`/`os.replace`/`msvcrt.locking`（既有）；测试引用 `cc.reopen_closure`/`cc.takeover_execution`/`cc.ExecutionFenced`/`cc.CLOSURE_GENERATIONS_FILENAME` 均在 `__all__` 或模块级 |
| 4 | 未实现 TODO | **无** | grep TODO/FIXME/XXX/HACK/待实现——仅命中 placeholder 模板机制的合法文档（L603/637/893-916） |
| 5 | 过度实现 | **无** | heartbeat/TTL 判死如实声明为 E3 不在本 slice（克制）；payload 字段均有消费方（CLI/status/测试）；`lock_timeout`/`--reopen-of` 参数均接线；无 speculative 分支 |

## 6. 验证复现记录（Reviewer 实测）

| # | 命令/方式 | 结果 |
|---|---|---|
| 1 | `pytest tests/test_closure_chain.py -q` | **83 passed**（110.02s） |
| 2 | `pytest ... -k "ReopenLineage or ExecutionGenerationFencing" --collect-only` | **14/83**（ReopenLineageTests 7 + ExecutionGenerationFencingTests 7；69 deselected） |
| 3 | `verify_workflow.py` | **PASSED** |
| 4 | CLI 探针（`%TEMP%\fe063_probe.py`，隔离 tmp workspace，11 场景） | **11/11 PASS**：字段纪律 exit 2 / first takeover exit 0 gen 1 / **同 holder 拒绝 exit 2** / stale resume CLI exit 2 revision_conflict / stale finalize CLI exit 2 / in-flight takeover CLI exit 3 lock_contention / reopen CLI exit 0 attempt 2 / 二次 reopen exit 2 single-successor / successor adopt recorded id / --reopen-of mismatch exit 2 "recorded successor" / corrupt sidecar CLI exit 2 "unreadable" |
| 5 | 探针 2（`%TEMP%\fe063_probe2.py`）：attempt 3 级链 | **4/4 PASS**（attempt 2→3、第三级 adopt + inputs reopen_attempt=="3"）——实现正确、测试缺（P2-1） |
| 6 | 探针 2：TOCTOU 竞态注入 | **3/3 复现 P0-1**（T1 在 B 在途持锁时成功 + gen3/C/prior-B + B 次轮 run revision_conflict） |
| 7 | 删除行核对 | `git diff 14797be | Select-String '^-'` 逐行归类 15 组，无夹带 |
| 8 | 并行面隔离 | `git log 14797be..HEAD -- <两文件>` 为空 + `git status --porcelain` 全清单核对——本审查零触碰 loop_*/archive* |

## 7. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | =0 | **1**（P0-1） | ❌ 阻断 |
| 5 维度全覆盖 | 100% | §3 五维逐项有结论 | ✅ |
| 每条发现标注级别 | 100% | §4 全部 P0~P3 标注 | ✅ |
| 设计一致性（ADR/申报语义） | 已完成 | FEAT-061 epoch-fencing 同型（revision_conflict 结构化拒绝）、ARCH-09 owner-token（skipped_fenced）、FEAT-062 字段纪律/终态语义/对账——逐项比对一致；**唯申报不变量「在途链不 fence」被 P0-1 竞态违反** | ⚠️ |
| AI 专项 5 项 | 全部完成 | §5 | ✅ |

## 8. 总结论

**NEEDS_CHANGE**（unresolved_blockers=**1**）

- **unresolved_blockers = 1**：P0-1 takeover TOCTOU 竞态（活体复现；修复方向已给出——锁内 re-read 后 prior_holder 变更即拒绝 retryable）。
- P1×2 为测试看护缺口（per-step fence 面 / 同 holder 拒绝），实现本身经探针代验正确，可与 P0 修复同批补齐；P2×4 / P3×4 不阻塞。
- 其余申报语义（重开零擦除、单一后继、recorded intent 绑定、fencing 三面结构、sidecar fail-closed、旧代际 cancel、F-4/F-5、心跳三层如实）逐项核验**属实且实现正确**；14 新测试红态真实、判别力强。
- 修复后按 M7.4 T1 重 spawn 本 Reviewer 复审（R1），R1 将逐条比对本清单并重点复跑：TOCTOU 红绿双相 + 3 个新测试 + 全量套件。
