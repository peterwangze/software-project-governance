# REVIEW-FEAT-065-CODE-R0 —— 标准链锁腿 locks-release 真释放升级（R0 逐行代码审查）

- **Task**: FEAT-065（DEC-248 验收拆分后范围）
- **审查对象**: commit `ab7a8e1`（HEAD @ 审查时点，2 files +443/-76：`closure_chain.py` +89 区段 / `tests/test_closure_chain.py` +354 区段）
- **Review 轮次**: R0（首轮）
- **审查者**: Code Reviewer Agent（只读约束：除本报告外零写入；测试运行使用临时目录，临时产物已清理）
- **结论**: **APPROVED_WITH_NOTES（unresolved_blockers=0）**——P0=0 · P1=0 · P2=0 · P3×6（记录级）

---

## 1. Developer 申报核验（EVD-1181 对照亲测）

申报原文锚点：`.governance/evidence-log.md` L2802（EVD-1181，op-1b3fc40575c041c2abe4da57e1000fa2）。

| # | 申报 | 亲测结果 | 裁决 |
|---|------|---------|------|
| 1 | 绿相 112P exit 0 | 亲跑 `python -m pytest skills/software-project-governance/infra/tests/test_closure_chain.py -q` → **112 passed, exit 0**（145.24s）；测试方法逐一清点 = 112 | ✅ 复现 |
| 2 | 红相 13F/99P exit 1 | 历史时点不可重放；13+99=112 与测试集总数算术自洽，8 项新测试断言的语义（gate 替换/真释放/fail-closed）对旧实现（TTL 收缩 gate）必然失败——红相叙事与 diff 结构自洽 | ◐ 结构确认（不可重放，如实标注） |
| 3 | 基线 104P 零回归（99 原样 + 5 处钉旧契约断言更新） | 112 = 104 + 8 新增（ReleaseLocksUpgradeTests 8 方法）✓；diff 全量核对：既有测试**零删除**，断言级修改实见 6 处（详见 F-5 计数口径出入） | ✅ 实质成立 |
| 4 | check-governance 50=50 持平 | 主工作树实测 **51 issues**。归因闭环：+1 = `[S1] FEAT-065: completed product-code task … has no recommendation-snapshot row`——EVD-1181 落账后 M7.4 step 6「完成必推荐」快照的**流程内预期待办**（Coordinator 复审通过后落 RECO 行），与 commit `ab7a8e1` 产品代码无关；Developer 的 50 系 EVD 落账前时点，事后不可精确复现 | ◐ 实质成立（F-1） |
| 5 | check-cross-references / check-manifest-consistency PASS | 亲跑：cross-refs **PASS exit 0**（无 dangling/deprecated/circular）；manifest **PASS exit 0**（911 canonical / 1054 actual） | ✅ 复现 |
| 6 | CLI 接口零变化 | diff 无 argparse/add_argument/CLI 分支变更；closure-chain 子命令面未动 | ✅ |
| 7 | 内在行为变化①：PROBE_KINDS 闭集拒绝 `lock_ttl_le` 自定义 spec | `lock_ttl_le` 已移出闭集（L414-421）；双校验：parse 期 `StepSpec` L794-799 + 运行期 `_run_probe` L1096-1099 → 旧自定义 spec parse 即 `ValueError`，fail-closed | ✅ 机制确认 |
| 8 | 内在行为变化②：`lock_ttl` 死输入移除致跨版本 resume digest 失配 | `_REQUIRED_INPUT_DEFAULTS`（L961-964）移除 `lock_ttl` → defaults 并入 merged_inputs（L1799）→ `_inputs_digest`（L1074-1077/L1818）→ resume mismatch 拒绝（L1856-1861）。申报口径「会话内运营态无跨版本 resume 契约」如实 | ✅ 机制确认 |

---

## 2. 票面审查范围逐项裁决

### ① 真释放接线——与 cancel 腿同款 + operation-id 幂等 ✅

- 标准 `release-locks` 步 argv（closure_chain.py L928-948）：`["{python}", "{gs_cli}", "--project-root", "{root}", "locks-release", "--task", "{task}", "--operation-id", "{op:release-locks}"]`。
- cancel 腿 `_cancel_locks_leg`（L2543-2597，argv @ L2584-2587）：`[sys.executable, governance_store.py, --project-root, <root>, "locks-release", --task, <task>, --operation-id, <op_id>, --timeout, <writer_timeout>]`。
- 形态一致：同 writer（`{gs_cli}` → `INFRA_DIR/governance_store.py`，L1031）、同子命令、同 task-scoped 参数组；`--timeout` 为运行时参数非语义差异。**同款接线成立**。
- operation-id 幂等：`{op:release-locks}` 经 `resolve_template` 回退至 `step_operation_id(closure_id, step_id)`（L1056-1057）= `op-` + sha256(`closure_id|step_id`)[:32]（L502-520），跨 resume 稳定；writer 侧 same-id replay 协议（governance_store.py L2196-2240：B-10 先登记后删除 + 同 id 完成后 success no-op）由测试 6/7 端到端实证（replay `replayed=true`、ops ledger 恰一条 locks-release）。

### ② gate 闭集替换——task_locks_released 双面 + fail-closed ✅

实现：closure_chain.py L1158-1245。逐分支核对：

| 检查项 | 实现 | 裁决 |
|--------|------|------|
| 双面判定 | `active_held = task in active`（任务索引）+ 逐项 `entry.get("locked_by") == task` 扫描 file_locks（文件锁归属，不信任索引枚举）→ satisfied 当且仅当两者皆无 | ✅ |
| 不可读/损坏 fail-closed | JSON 解析失败 / 顶层非对象 / active_tasks 非 dict / file_locks 非 dict / 任一 entry 非 dict → `satisfied=False`（归属无法判明一律 fail-closed） | ✅ |
| 锁文件不存在 | `satisfied=True`（空世界 = 后置条件成立——与旧 gate 语义连续，合理） | ✅ |
| 后继任务锁不误判不误删 | 他人锁仅计数 `others`，不影响 satisfied；gate 纯只读（无任何写路径）；「不要求路径全局无锁」注释 (c) 与实现一致；测试 6 端到端实证（后继锁存活 + replay 不删） | ✅ |
| 状态后置条件 ≠ 操作成功回执 | pre-probe 语义（FIX-379，L1090-1094：probe 是执行决策输入，step 完成由 writer receipt 的 `step_completed` 承载，probe 绝不在执行后复读）；测试 1 断言 journal `step_completed.operation_id`/`execution=succeeded` | ✅ |
| 双层 fail-closed 链行为 | probe False → 链对同一世界重发 governed 写 → writer 独立拒绝（governance_store.py `holds_lock`/`_locks_execute` fail-closed）→ 链停 blocked；测试 4 端到端实证（blocked + ready-to-commit 不发出 + `closure_ready` 零事件 + `step_failed` 恰一条） | ✅ |

### ③ 三处披露勘正如实 ✅

对照 review-FEAT-045-CODE-R0 §1.2(a) 三处逐字原文：

| # | 原位置（045 审时行号） | 现状态（ab7a8e1） | 裁决 |
|---|----------------------|------------------|------|
| ① | 模块 docstring L95-100（"NO locks-release … registered gap"） | L95-105 替换为「FEAT-065 … registered gap is CLOSED on the chain face … acquire-side TTL judgment face is FEAT-066's scope — untouched here」 | ✅ 勘正如实且 FEAT-066 边界声明保留 |
| ② | 步骤描述 L784-785（"locks-amend TTL 收缩（locks-release 缺口承载…）"） | L929-932 替换为「locks-release 真释放（FEAT-065…cancel 腿同款接线）」 | ✅ |
| ③ | 链终点摘要 L1446-1447（"locks-release remains a registered gap…"） | `_CHAIN_SUMMARY_BODIES` L1637-1647 替换为「dispatch locks released via locks-release (FEAT-065 true release … never a replacement for the writer's receipt)」 | ✅ |

测试 8（test_closure_chain.py L965-1016）对三处逐一断言（`has NO locks-release` / `registered gap` / `缺口` 消失 + 新文本存在），且 grep 全 infra 确认 `shrink-locks` 在 closure_chain.py 零残留。如实。

### ④ 四红线 ✅（各有集成级测试实证）

| 红线 | 实证 |
|------|------|
| 释放前同文件互斥不放松 | 测试 5：释放前第二任务 acquire 同文件 exit 2；真释放后同文件 acquire exit 0 且 `locked_by=后继` |
| 只释放自持锁 | writer 侧 `locked_by == task_id` 过滤删除（governance_store.py L2234-2240）；测试 6：deterministic-id replay 后后继新锁原样存活 |
| 释放后不改受锁文件 | 链序 release→ready-to-commit（summary 为引擎计算，无 argv 无 writer）；测试 8：release 后 journal 事件序列恰为 `["closure_ready"]`，`do_not_stage` 含 closure-events.jsonl 而不含 agent-locks.json |
| 提交串行隔离 | 测试 8：步序钉扎 `["flip-completed","append-evidence","release-locks","ready-to-commit"]`——release 位置即 0.86 以来提交隔离语义的承载位，未移动 |

### ⑤ 八项最小红绿测试集真实性 ✅

八项（test_closure_chain.py L763/789/808/823/853/877/913/965）全部 integration grade：真实 subprocess（`agent-locks-acquire` exit 2/0 双面、`locks-release` replay）、真实故障注入（`_spawn_run` fault_points=`post-step-effect:release-locks` crash window）、真实 journal/ops ledger/锁文件世界断言。全文件 grep 零 mock/patch 导入——非「argv 看起来对」式参数证明，端到端成立。

### ⑥ Developer 申报核验 ✅/◐ —— 见 §1 逐条（6 项复现/机制确认，2 项结构确认并归因）

### ⑦ 越界检查 ✅

- `git show ab7a8e1 --stat`：修改面严格限于两锁文件；`governance_store.py` / `change_triage.py` **零触碰**（acquire TTL 判定面完整保留给 FEAT-066——模块 docstring L105 亦显式声明该边界）。
- 工作树状态亲测：HEAD = `ab7a8e1`；唯一额外差异 = `docs/planning/version-plan-0.89.0.md` 未提交修改（§2 行6 勘正，内容与 DEC-248⑤/票面逐字一致）——属 Coordinator 收尾批在途治理写回，**不属 ab7a8e1 修改面、非产品代码越界**；「工作树应与 HEAD 一致」前提不完全成立的实情记为 F-6。

---

## 3. 发现清单（P0-P3）

| # | 级别 | 位置 | 描述 | 建议 |
|---|------|------|------|------|
| F-1 | P3 | check-governance 计数（申报 50 / 实测 51） | +1 = S1「FEAT-065 完成缺 task-priority-analysis 推荐快照行」——EVD-1181 落账后 M7.4 step 6 预期待办（流程中间态，非 commit 缺陷）；时点计数不可复现，实质持平成立 | Coordinator 复审通过后按完成必推荐流程落 RECO 快照即消解；此类申报建议附计数构成或检查时点锚 |
| F-2 | P3 | closure_chain.py L2115 | dry-run parse-level 分支代码注释括号示例仍写 "(locks-amend)"（note 生成文本 L2127-2128 已是通用措辞，运行时输出不受影响；该行不在票面三处披露锚点内） | 后续触碰该文件的票顺带勘正注释示例 |
| F-3 | P3 | governance_store.py L2211-2212 | writer docstring「orchestrator's shrink-locks step (TTL 收缩) semantics are deliberately untouched」失准——orchestrator 已无 shrink-locks 步；该文件不属本票锁面（DEC-248① 锁面不变的正确执行结果），属跨票遗留文档失准 | 归属后续触碰 governance_store.py 的票顺带勘正（与 F-2 同批亦可） |
| F-4 | P3 | test_closure_chain.py L538 | `inputs=dict(EVD_INPUTS, lock_ttl="120")` 在 resume-mismatch 测试中现角色为「未知键样本」（其拒绝路径恰为申报② digest 失配语义的活体守护），但键名易误读为仍受支持的链输入 | 改中性键名（如 `legacy_unknown_key`）以免误读 |
| F-5 | P3 | EVD-1181 申报「5 处钉旧契约断言更新」 | diff 实见 6 处既有测试修改：spec step_ids（L328）/E2E effect3（L454）/step status（L479）/dry-run 断言（L690）/KillSwitch 锁断言（L1522）/ReleaseBootstrap summary 断言（L1879）——构成计数口径出入；零回归结论不受影响（112 全绿 + 零删除） | 记录级；后续申报断言修改处数时按 diff hunk 计数 |
| F-6 | P3 | 工作树（非 ab7a8e1） | `docs/planning/version-plan-0.89.0.md` 存在未提交修改（§2 行6 = DEC-248⑤ 要求的勘正，内容与票面逐字一致）——任务前提「工作树与 HEAD 一致」不完全成立；属收尾批在途治理写回 | 提请 Coordinator 收尾时将该勘正随治理写回批提交入库 |

**P0 = 0 · P1 = 0 · P2 = 0** —— 六条均为 P3 记录级，无阻塞发现。

---

## 4. 五维度结论 + AI 专项 5 项检查

| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | **PASS** | 双面 gate 判定/五类损坏 fail-closed/确定性 operation-id 幂等接线逐行核对（§2①②）；112P 亲跑全绿 |
| 安全性 | **PASS** | 只释放自持锁（writer task-scoped + 测试 6）；gate 纯只读、绝不触碰他人锁；argv-list 零 shell；损坏世界双层 fail-closed 链停 blocked（测试 4） |
| 可维护性 | **PASS with notes** | 披露勘正如实且边界声明（FEAT-066）保留；测试注释完备承载 gate 语义五点；F-2/F-3/F-4 注释与命名卫生为记录级 |
| 性能 | **PASS** | probe 为单次文件读 + O(n) 归属扫描；移除 TTL 判定不引入新 I/O 热点；无 N+1/嵌套循环 |
| 测试覆盖 | **PASS** | 八项红绿集成集覆盖：真释放世界态/闭集替换/索引-文件锁去同步/crash window resume/四红线/披露勘正；既有 112 全绿零删除 |

| AI 专项 | 结论 |
|---------|------|
| 1 mock 残留 | **未发现**——全文件零 mock/patch 导入；唯一 "mock" 为 docstring 否定申明（L725） |
| 2 硬编码返回值 | **未发现**——probe 全部分支读真实锁世界；断言锚定 journal/ops ledger/锁文件实态 |
| 3 幻觉 API | **未发现**——`locks-release`（governance_store.py L2196/注册/CLI 派发在案）、`agent-locks-acquire`（verify_workflow 薄入口，测试实跑）均实存 |
| 4 未实现 TODO | **未发现**——无新增 TODO；acquire TTL 面如实声明为 FEAT-066 范围（非隐瞒） |
| 5 过度实现 | **未发现**——修改面严格限于票面范围（接线替换/probe 重写/披露勘正/死输入移除），无顺带改动 |

---

## 5. 硬门槛裁决

| 门槛项 | 裁决 |
|--------|------|
| 逐行审查 diff 全量（+443/-76 不抽样） | ✅ 两文件 diff 逐 hunk 全读；关键实现段（probe L1158-1245、步 spec L928-948、mapping/digest/resume 链、cancel 腿 L2543-2597、writer L2196-2240）对照 HEAD 工作树复核 |
| 亲跑复核 | ✅ pytest 112P exit 0；check-cross-references PASS；check-manifest-consistency PASS；check-governance 51→+1 逐项归因闭环（S1 完成必推荐待办，流程中间态） |
| P0-P3 分级每条标注 | ✅ F-1~F-6 全部带 P 标签 |
| 结论四选一 | ✅ APPROVED_WITH_NOTES（unresolved_blockers=0） |
| 只读约束 | ✅ 唯一写入 = 本报告；pytest 临时目录产物由测试框架自清理；归因验证所用临时 worktree 已 `worktree remove --force` + `prune`，临时输出文件已删除 |

---

## 6. 总结论

**APPROVED_WITH_NOTES（unresolved_blockers=0）**

票面验收（DEC-248 拆分后范围）全部有事实支撑：真释放接线与 cancel 腿同款且 operation-id 幂等；task_locks_released gate 任务索引+文件锁归属双面、五类损坏/不可读 fail-closed、后继锁不误判不误删、状态观测与 writer 回执语义分离；三处披露勘正与 review-FEAT-045 §1.2 原文逐点对应替换；四红线各有集成级测试实证；八项红绿集为真实 subprocess/故障注入端到端（非 mock 参数证明）。Developer 申报与实测一致——绿相 112P exit 0 亲跑复现，check-governance +1 差异归因于 EVD-1181 落账后的完成必推荐流程待办（F-1，非本 commit 缺陷）。修改面严格限于两锁文件，acquire TTL 判定面完整保留（FEAT-066 边界声明在案）。

移交 Coordinator：①按 M7.4 step 6 落完成必推荐快照（同时消解 F-1 的 S1）；②F-6 version-plan 勘正随收尾批提交；③F-2/F-3/F-4/F-5 为记录级遗留，归属后续触碰对应文件的票顺带处理。
