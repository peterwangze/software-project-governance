<!-- machine-record: FEAT-063 | reviewer: code-reviewer | round-suggestion: none | verdict: APPROVED_WITH_NOTES | unresolved_blockers=0 -->

# Code Review R1 — FEAT-063 closure 重开 + 异常接管（M7.4 T1 同席复审）

- **轮次声明**：R1；前轮引用 `docs/reviews/review-FEAT-063-CODE-R0.md`（R0 = NEEDS_CHANGE，unresolved_blockers=1——P0-1 takeover TOCTOU 竞态 + P1×2 测试缺口 + P2×4）。本轮按复审协议逐条比对前轮 findings（§5），全部实测以当前工作树 diff 为准。
- **审查对象**：工作树未 commit diff vs 基线 `14797be`，严格限定 2 文件——`infra/closure_chain.py`（**实测 numstat +879/−53**；R1 增量 Δ+71/−1）、`infra/tests/test_closure_chain.py`（**实测 +670/−0**；R1 增量 Δ+247 = 4 测试）。重新验证：两文件在 `14797be..HEAD`（HEAD 已前移至 `467fb55`，新增 FEAT-045 纯审计票）之间**仍无已提交改动**——diff 纯粹性保持；并行面（loop_*/archive*）零触碰。
- **审查者**：Code Reviewer Agent（只读；实测在 `%TEMP%\fe063_r1_*` 隔离探针内，真实 `.governance/` 零写入）。
- **结论**：**APPROVED_WITH_NOTES**（unresolved_blockers=**0**——P0=0、P1=0；R0 全部阻塞/关键项已修实证，维持项 P2-2/P3×4 备查见 §5/§6）。

## 1. R1 核验项 1——P0-1 修复形态 ✅

**锁内重校验块（`closure_chain.py` L2877-2909），三形态 mismatch 拒绝 + 零写入 + 不做锁内换锁：**

| 修复面 | 实现 | 实测 |
|---|---|---|
| 锁内 re-read + observed 化 | L2869 锁内 re-load（generations lock 持有中）；L2878-2879 `observed_holder` 从 current 提取（current 非 dict → None） | ✅ |
| 形态 1（A→B 换持有者） | `observed_holder != prior_holder`（L2890）→ `lock_contention`/retryable，detail 携带 pre-read id 与 observed id + "ZERO changes" + retry 指引 | ✅ 探针 shape1：T1 拒绝 + 世界保持 B 的 promotion |
| 形态 2（记录被移除→observed None） | current=None → observed=None ≠ prior → 同块拒绝 | ✅ 探针 shape2：拒绝 + 世界保持无记录 |
| 形态 3（pre-read 无记录但锁内出现） | prior=None、observed=B → 拒绝 | ✅ 探针 shape3：拒绝（detail "pre-read (None)"）+ 世界保持 B |
| 绿相对照（世界未变） | observed == prior → 正常 promote | ✅ 探针 green-control：gen 2 正常提升，无假拒绝 |
| 零写入 | 拒绝 return 位于 L2926 写入之前；finally（L2927-2930）释放 old_holder_lock + generations_lock | ✅ 探针 world-untouched ×3 |
| 不做锁内循环换锁 | 注释 L2897-2899 记录理由（"swapping to the newly observed id would just relocate the same race one step further"）——与修复声明一致 | ✅ |
| TEST-ONLY 故障点 | `_maybe_fault("post-generations-preread")` L2839——位于 pre-read（L2833）与 generations lock（L2840）之间；BT-9 env 门控，`FaultSurfaceTests::test_production_cli_exposes_no_fault_flags`（既有）钉住 CLI 无 fault 面 | ✅ |

**红相判别力（对 pre-fix 代码双断言必红论证 + 实测翻转）：**
1. *论证*：pre-fix 代码在同一时序下（R0 活体实测）返回**成功 payload**（无 `error`/`code` 键）且 record 被 T1 覆盖为 gen3/holder=C。因此新测试断言 ①`payload["code"]=="lock_contention"`（pre-fix 成功 payload 无 code 键 → assertEqual 红）与 ④`record holder==B gen==2`（pre-fix 下为 C/3 → 红）**双断言必红**。
2. *实测翻转*：R0 的 TOCTOU 探针（`%TEMP%\fe063_probe2.py`）原样对修复后代码复跑——`toctou-takeover-succeeded-despite-B-in-flight` 由 PASS 翻转为 FAIL，实际输出 `T1 error=True code=lock_contention`；`toctou-record-bound-C-prior-B` 翻转（gen=2 保持 B）；`toctou-inflight-B-fenced-after` 翻转（B 不再被 fence）。同探针 attempt 链 4 断言维持 PASS——修复只关闭竞态，零语义回归。

**剩余窗口排查（独立推演）**：observed==prior 通过后，promoter 持有 prior 的 run lock → prior 在途不可能（否则 lock_contention）；其它 takeover 被挡在 generations lock 外；prior 在 promotion 后新启动的 run 在入口 fence check 被 fence 属合法语义（takeover 在先）。**无剩余竞态窗口**。

## 2. R1 核验项 2——P1-1/P1-2/P2-1 三测试判别力 ✅

| 测试 | 判别力要点 | 实测 |
|---|---|---|
| `test_per_step_fence_recheck_refuses_out_of_band_rebind`（test_closure_chain.py L3195-3269） | `post-step-effect:write-one` handshake 暂停 → **越带 hand-edit** re-bind（绕开接管路径 run-lock 串行化 by construction）→ write-two 写边界拒绝。四层断言齐：write-one 效果保留（marker_one 存在——fence 止于下一写，不回滚）+ write-two 未 spawn（marker_two 不存在 + journal 无 `step_started:write-two`）+ `closure_fenced` 恰 1 + `revision_conflict`/conflict | ✅ 单跑绿（4 passed, 3.89s） |
| 同测试 docstring 如实区分 | "Under the takeover path a mid-run fence is unreachable (the promotion holds the run lock); this test simulates the out-of-band authority change (hand-edit class)"——**out-of-band 面与接管路径不可达声明的区分如实** | ✅ |
| `test_same_holder_retakeover_refused_zero_write`（L3271-3290） | 同 holder 二次 takeover → schema_violation + "already holds" + **record 字节相等** + `.governance` 全树快照相等 | ✅ |
| `test_attempt_chain_deepens_three_levels`（L2869-2921，ReopenLineageTests 内） | A(1)→S2(2)→S3(3)；S2 携带 `reopen_of` 跑（协议正确）后终态再 reopen；断言 S2 journal 双向 lineage（back-link attempt 2 + forward reopen attempt 3 naming S3）+ A journal 恰 1 reopen 事件且其后不变（每跳 append-only 隔离） | ✅ |

handshake 机制核验：`_maybe_fault`（closure_chain.py L1222-1243，TEST-ONLY，marker+release 轮询，120s 预算）与测试 helper `_point_marker`/`_wait_marker`（L223-235）命名规则同型（`re.sub(r"[^a-z0-9-]", "__")` 两侧一致）。`_FENCE_STEP_SPEC`（L2628-2649）双 cli 写步 fixture 真实落盘 marker。

## 3. R1 核验项 3——fsync 对齐（P2-3）✅

`_write_execution_generations`（L2681-2707）重写为 writer 家族纪律同型：同目录 `tempfile.mkstemp` + write + `flush` + `os.fsync`（L2698-2699）+ `os.replace`（L2700）+ `_fsync_dir`（L2701；新 helper L2664-2676，best-effort dir fsync，Windows 目录不可打开 → 吞掉——governance_store writer-family shape 的本地镜像，docstring 注明不 import writer 模块以维持 kill-switch 依赖方向）+ 异常路径 tmp 清理（L2702-2707）。与 R0 P2-3 引用的六处纪律（governance_store.py L449-450、task_row_update.py L695-701 等）**四件套同型**。

## 4. R1 核验项 4——复现（仓库根口径）✅

| 项 | 命令/方式 | 实测 |
|---|---|---|
| 票面套件 | `pytest tests/test_closure_chain.py -q` | **87 passed**（115.47s）= 83 + 4，与申报一致 |
| 新测试清单 | `-k "ReopenLineage or ExecutionGenerationFencing" --collect-only` | **18/87**（14 R0 + 4 R1；69 deselected） |
| 4 新测试单跑 | `-k "stale_preread or out_of_band_rebind or same_holder_retakeover or deepens_three_levels"` | **4 passed**（3.89s） |
| 真实仓库 verify（只读） | `verify_workflow.py` | **== Verification Result: PASSED ==** |
| P0-1 三形态 + 绿对照 | `%TEMP%\fe063_r1_probe.py`（patch `_load_execution_generations` 首调注入窗口变异） | **7/7 PASS**（形态 1/2/3 拒绝+世界不动 ×3 + 绿对照 promote） |
| 红绿翻转 | R0 探针 `fe063_probe2.py` 复跑 | TOCTOU 3 断言翻转 FAIL（拒绝语义生效）+ attempt 链 4 断言维持 PASS；attempt 链 3 级（探针侧）仍 4/4 |
| 删除行核对 | `git diff 14797be \| Select-String '^-[^-]'` | 53 行 = R0 已核对 52 行（15 组重构点）+ 1 行 fault-point docstring 枚举行重写（随 `post-generations-preread` 新增）——**无夹带** |
| 并行面隔离 | `git log 14797be..HEAD -- <两文件>` 为空（FEAT-045 零源码修改）+ numstat 文件清单核对 | ✅ |

## 5. R1 核验项 5——R0 findings 逐条比对

| R0 编号 | 内容 | R1 状态 |
|---|---|---|
| P0-1 | takeover TOCTOU——锁内 re-read 更新 prior_holder 但不重取 run lock，竞态下在途 executor 被误 fence（活体复现） | **已修复**（锁内重校验块 L2877-2909，三形态拒绝 + 零写入 + 不换锁理由入注释；§1 全项实证 + 红绿翻转实测） |
| P1-1 | per-step fence re-check 面零测试 | **已修复**（test_per_step_fence_recheck_refuses_out_of_band_rebind——越带面红态 + 四层断言 + docstring 如实区分；§2） |
| P1-2 | 同 holder 重接管拒绝零测试 | **已修复**（test_same_holder_retakeover_refused_zero_write——双零写断言；§2） |
| P2-1 | attempt 链 3 级深化无测试 | **已修复**（test_attempt_chain_deepens_three_levels——S2 携带 reopen_of 协议正确 + 每跳 append-only 断言；§2） |
| P2-3 | sidecar 写入无 fsync（writer 家族偏离） | **已修复**（mkstemp+fsync+replace+dir fsync 四件套同型；§3） |
| P2-4 | 申报 numstat 与实测不符 | **已修复**（申报收口 +879/−53 / +670/−0 == `git diff --numstat 14797be` 实测，逐字节一致） |
| P2-2 | successor 丢失 `--reopen-of` 时 attempt 静默重置（own_attempt 解析失败→1） | **维持**（代码未变——L3032-3035；文档化缓解 run_note/status 披露已在 R0 记录；后续 slice 评估 successor 全局索引。非阻塞） |
| P3-1 | cancel 字段校验消息文本变化（helper 提取副产品） | 维持（未触碰；纯文本面，无测试断言依赖） |
| P3-2 | `_resolve_reopen_linkage` 忽略 journal problems | 维持（L2958 未变；fail-closed 方向） |
| P3-3 | record.generation 畸形重置 1 | 维持（L2910-2914 未变；fence 语义不受影响） |
| P3-4 | run_argv 展示用途限制 | 维持（L3055 未变） |
| — | （新引入检查） | **无功能性新引入**。观察一条（非阻塞）：P0-1 钉测试仅注入形态 1（A→B），形态 2/3 由本审查探针代验（§4 r1_probe 7/7）——形态 2/3 与形态 1 走同一比较分支（`observed_holder != prior_holder`，仅提取路径不同），风险极低，记为 §6 R1-N1 |

## 6. 五维度复核 + AI 专项（R1 增量面）

**五维度**：正确性 ✅（P0-1 关闭，剩余窗口独立推演无遗漏）；安全性 ✅（fsync 四件套对齐家族标准；fail-closed 方向不变）；可维护性 ✅（重校验块注释记录竞态理由与不换锁裁决；`_fsync_dir` docstring 注明依赖方向理由）；性能 ✅（重校验为锁内一次 sidecar 读，无新增 I/O 热点）；测试覆盖 ✅（14+4，R0 三缺口全闭合）。

**AI 专项 5 项（R1 增量面复核）**：①mock 残留——无（4 新测试全真实线程/handshake/字节断言）；②硬编码返回值——无；③幻觉 API——无（`tempfile.mkstemp`/`os.fsync`/`_fsync_dir`/`_maybe_fault` 均实存且接线）；④未实现 TODO——无；⑤过度实现——无（TEST-ONLY fault point 复用既有 BT-9 机制且有 FaultSurfaceTests 钉 CLI 面；fsync 重写对齐既有惯例非 speculative）。

## 7. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | =0 | **0** | ✅ |
| 5 维度全覆盖 | 100% | §6 逐项有结论 | ✅ |
| 每条发现标注级别 | 100% | §5 全部标注 | ✅ |
| 设计一致性（ADR/申报语义） | 已完成 | 「在途链不 fence」不变量恢复且经三形态+绿对照+翻转实测；FEAT-061 epoch-fencing 同型/ARCH-09/FEAT-062 纪律维持；接管路径 mid-run 不可达声明如实 | ✅ |
| AI 专项 5 项 | 全部完成 | §6 | ✅ |

## 8. 总结论

**APPROVED_WITH_NOTES**（unresolved_blockers=**0**）

- R0 全部阻塞/关键项（P0-1 + P1×2）与承诺修复项（P2-1/P2-3/P2-4）**六项全部已修且逐项实证**；红绿双相齐备（P0-1 红相由 R0 活体记录 + 本轮翻转实测双钉）。
- 维持项（非阻塞、备查）：P2-2（successor 丢 `--reopen-of` 的 attempt 重置——文档化缓解已在位）、P3-1~P3-4（R0 备查项未触碰）。
- R1 备注（非阻塞）：
  - **R1-N1**：P0-1 钉测试仅覆盖形态 1；形态 2/3 与形态 1 同一比较分支，本审查探针已代验 7/7——可选后续补两个注入变体，不要求本轮。
- 复审链终态：APPROVED_WITH_NOTES，Check 30 可消费（`unresolved_blockers=0` 独立结构字段在本报告头部 machine-record 行与本节）。
