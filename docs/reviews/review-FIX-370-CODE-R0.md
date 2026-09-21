# Review — FIX-370 locks-release（CODE, Round 0）

- **Task**: FIX-370 — writer 族 `locks-release`（task 锚定真删除 + 先登记后删除 + 幂等 + fail-closed）
- **Round**: R0（串行单席，工作树直读模式——staged diff `git diff --cached`，7 文件 +340/−21，与任务描述一致）
- **Reviewer**: Code Reviewer（只读审查，未修改任何代码）
- **审查依据**: diff 全文 + governance_store.py 管线源码（`_locks_execute` / `_apply_locks` / `_complete_pending` / `_ledger_transaction` / `_replay_payload` / `_state_matches`）+ verify_workflow.py 接线 + registry.py + 测试 + snapshots.json
- **限制声明**: Bash 禁止 → 未独立重跑 pytest / check-manifest-consistency；Developer 声明的 93/93 + 77 + 27 + PASS 标注为「Developer 声明 + 静态一致性核验通过」，非本席独立复现。

---

## 结论

# **APPROVED_WITH_NOTES**（unresolved_blockers=0）

- P0 = 0，P1 = 0，P2 = 1（F-1，建议遗留修复），P3 = 3（披露/讨论级）
- 硬门槛全部通过（见 §6 裁决表）；无 BLOCKING finding。
- F-1 为 crash-resume 恢复路径的审计留痕缺口，非正确性/数据安全问题，可作为遗留项记录到跟踪表后合并。

---

## 1. 特别复核点逐项结论（任务 MUST 六项）

### 1.1 writer 正确性 — **PASS**

| 项 | 证据 | 判定 |
|---|---|---|
| 原子性 | `_apply_locks`（governance_store.py L1573-1595）：`_atomic_write_bytes` 单次原子写 → post-write reread JSON 校验 → schema 复验 → `_complete_pending(source="apply")`；reread 失败 → `manual_intervention` 且 pending 行已在盘（可 effect-based resume） | ✓ 无半态 |
| 幂等（op-+32hex replay） | `_locks_execute` L1511-1521：existing ok → `decide_operation_replay` fingerprint 比较；同 payload → `_replay_payload(existing)`（replayed=True, source="ledger"）success no-op。fingerprint 仅 `{command, task}`（L1873 附近）——release 语义是全量释放，payload 确定性成立。测试 `test_replay_is_success_noop_locks_file_unchanged` 断言锁文件字节不变 | ✓ |
| fail-closed | `holds_lock` 谓词（L1538-1543）：task 无 active_tasks entry 且无 `locked_by==task_id` 的 file lock → `cross_record_violation`。guard 位于 `_ledger_entry`/`_ledger_transaction` **之前** → 零写入。测试 `test_lockless_task_refused_zero_writes` 断言锁文件字节不变 + ledger 文件不存在 | ✓ |
| 附带伤害隔离 | `mutate` 仅删 `locked_by==owner` 的条目；测试 happy 路径断言 FIX-200 行零触碰 + `_validate_locks_schema` 复验通过 | ✓ |

### 1.2 B-10 先登记后删除 — **PASS（含 1 项披露缺口 → F-1）**

- **时序实证**（L1560-1570）：`_ledger_entry(status="pending", pending_effects=target, baseline_effects=baseline)` → `_ledger_transaction(stage)`（ledger 锁内原子落盘）→ **之后** `_apply_locks` 才写锁文件。crash 窗口（pending 后、apply 前）→ effect-based resume：world==target → complete（source="resume"）；world==baseline → re-apply 确定性 mutator + complete。台账先行的 B-10 形态成立。
- **released_files 章**：`_complete_pending`（L1613-1614）置 `pending_effects/baseline_effects=None`（family convention，测试钉住 `baseline_effects is None`）→ apply 腿的 stamp（L1877-1891，`replay_source=="apply"` 且 `owned_files` 非空）是被释放文件清单的唯一存续面。`_replay_payload`（L636）实证 apply 腿 payload 携带 `replay_source="apply"` → stamp 分支真实可达（非死代码）。
- **F-1（P2）**：见 §3。

### 1.3 向后兼容 — **PASS**

- `_state_matches` None 扩展（L1478-1483）：仅当 `fields is None` 时走「absence 必须为真」分支；extend/amend 记录的 active_tasks 字段恒为 `{key: list(...)}` 非 None → 既有判定路径逐行为不变。
- `holds_lock` 默认 `None` → L1544-1548 原 guard（`task_id not in active_tasks`）原样保留；extend（L1626 起）/amend 调用点未传谓词 → 行为不变。
- fingerprint 结构未动 → 既有 op-id 重放判定不变。

### 1.4 重定基线完整性 — **PASS（四处自洽）**

| 位置 | 变更 | 一致性 |
|---|---|---|
| registry.py | 表 +1（`("locks-release", "governance_store.cmd_locks_release")`，字母序正确）；docstring 95→96、16→17 outside / 79 inside | 95=16+79 → 96=17+79 ✓ |
| test_registry.py | `FROZEN_CLI_KEYS = 96` + outside 显式集合加 `locks-release` | ✓ |
| snapshots.json | `key_count` 95→96、`handler_count` 92→93、keys 列表插入 `locks-release`（locks-amend < locks-extend < locks-release 字母序 ✓） | ✓ |
| test_contract_matrix.py | `FROZEN_CLI_KEY_COUNT = 95→96`，segment 面冻结 71 不变 | ✓ |
| 接线全链 | build_parser + `add_locks_release_arguments` + `COMMANDS` + `_CLI_HANDLERS` + verify_workflow（import / subparsers / dispatch 表）六处齐备，无孤儿键 | ✓ |

### 1.5 审查新发现（Developer 未披露面） — **1 项 P2 + 2 项 P3**

- **F-1（P2）resume 腿审计章缺口**——Developer 披露「resume 腿 owned_files 按构造为空」只覆盖 world==target 腿；world==baseline 的 re-apply 腿（L1525-1531）payload 同样带 `replay_source=="apply"`，stamp 靠 `and owned_files` 兜住不执行。两条跨进程恢复腿完成的 ok 行均无 released_files 章，且 `_complete_pending` 已清空 effects → 「释放了哪些文件」明细在该场景永久丢失。
- **F-2（P3）acquire+release 并发互斥未验证**——release/extend/amend 全部持 `_TargetLock(LOCKS_FILE_NAME)`（lock order：record-target 外层、ledger 内层，docstring L609-610）；acquire 写路径在 `change_triage.acquire_dispatch_locks`（本次未改，本席未读其锁行为）。若 acquire 不持同一 record-target 锁则存在存量 TOCTOU——属存量家族共性，非本变更引入。**待验证**。
- **F-3（P3）引擎面返回码丢弃确认属实**——verify_workflow L25349 `commands[cmd](args)` 不消费返回值；与 Developer 披露①一致（locks-extend 对照成立，家族共性）。

### 1.6 5 维度 + AI 专项 — 见 §4 / §5。

---

## 2. Findings 列表

| # | 级别 | 位置 | 描述 | 建议 |
|---|---|---|---|---|
| F-1 | **P2** | governance_store.py L1522-1531（resume 腿）+ L1877-1891（stamp） | crash-resume 恢复路径（world==target complete 腿、world==baseline re-apply 腿）完成的 ok 行均不带 `released_files` 章，且 `_complete_pending` 清空 `baseline_effects` → 被释放文件原值明细在该场景永久丢失。代码注释的「resume 腿 owned_files 按构造为空」论述未覆盖 re-apply 腿 payload 亦为 `replay_source=="apply"` 的事实，披露不完整。锁释放本身两条腿均正确——纯审计完整性问题 | 遗留修复：resume 腿完成时从 `existing["baseline_effects"]["file_locks"]` 键集（或 `pending_effects` 逆集）提取清单盖章；或最小改注释如实披露。建议下一轮/随下批变更处理 |
| F-2 | P3 | change_triage.acquire_dispatch_locks（存量，未在本次 diff） | acquire 与 release/extend/amend 的 record-target 锁互斥未验证；若 acquire 无锁则并发下存在 read-modify-write 丢失更新窗口。存量家族共性，非本变更引入 | 独立任务验证 acquire 锁行为；确认后入账或记风险 |
| F-3 | P3 | verify_workflow.py L25349 | 引擎面 `commands[cmd](args)` 丢弃 handler 返回码——Developer 已披露（家族共性，locks-extend 对照实证），本席确认属实 | 已披露，接受；家族级统一处理 |
| F-4 | P3 | governance_store.py L1877-1891 | stamp 在 `_TargetLock` 块外单独执行 `_ledger_transaction`（仅 ledger 锁，无嵌套 → 无死锁）；与其他 ledger 写由 ledger 锁串行化，stamp 条件严格（自身 op_id + status=="ok"）→ 竞争安全。设计备注，非缺陷 | 无需行动 |

**P0 = 0 · P1 = 0 · P2 = 1 · P3 = 3**

---

## 3. F-1 详细论证（唯一 P2）

事实链（全部源码实证）：
1. `_apply_locks` → `_complete_pending(source="apply")` → `_replay_payload(..., source=source)`（L1593-1622）→ **apply 腿与 re-apply 恢复腿的 payload 都携带 `replay_source=="apply"`**。
2. re-apply 恢复腿（L1525-1531）不调用 `effects_of` → 闭包 `owned_files == []` → stamp 的 `and owned_files` 条件为 False → 不盖章。
3. `_complete_pending` 无差别置 `pending_effects=None`、`baseline_effects=None`（L1613-1614）。
4. world==target complete 腿（L1522-1524）payload 为 `replay_source=="resume"` → 双重不满足 stamp 条件。

影响：只有「同进程一次连续执行」的 release 在 ok 行留有被释放文件清单；crash 后经任一恢复腿完成的 release，其 ok 行仅剩 operation_id/command/task_id/revision。B-10 的「先登记后删除」在 crash 窗口期间仍保证明细在盘（pending 行 baseline_effects），但 ok 转换即清空——审计链在恢复路径断链。

定性：P2 而非 P1——非正确性/数据安全问题（两条恢复腿的锁释放均正确、无半态）；触发前提是 crash+resume 边缘窗口；ok 行仍含 task_id 可供人工追溯。但 FIX-370 的动机之一即审计留痕（B-10），恢复路径丢明细与该意图有实质差距，建议遗留修复（实现成本低：恢复腿盖章可从 `existing["pending_effects"]` 的 file_locks 键集取逆，或如实修订注释披露）。

---

## 4. 五维度审查

| 维度 | 结论 | 依据 |
|---|---|---|
| 1 正确性 | **PASS** | §1.1 全项；边界覆盖：file-locks-only task（无 active entry）释放 ✓、他任务锁零附带伤害 ✓、幂等字节级不变 ✓。边界未覆盖：crash-resume 路径无直接测试（resume 腿仅共享管线既有语义背书）→ 计入 F-1 备注，不阻塞 |
| 2 安全性 | **PASS** | 输入校验：`--task` required + `_locks_common` 清洗 + `require_operation_id`；无注入面（JSON 原子写，无 shell/SQL）；无敏感数据；权限：fail-closed（lockless 拒绝、schema 复验、reread 校验、ledger 篡改 fail-closed L591-604） |
| 3 可维护性 | **PASS** | 严格复用家族管线（无第二条 apply 路径）；docstring 披露设计意图与家族惯例；命名与 extend/amend 同构；模块 docstring/`__all__` 同步更新 |
| 4 性能 | **PASS** | file_locks 单遍 O(n) 过滤（两处：mutate/effects_of/holds_lock 各一遍，n=锁条目数，规模极小）；ledger 两次事务写为既有家族模式；无 N+1 |
| 5 测试覆盖 | **PASS** | LocksReleaseTests 四测覆盖 happy（含 ledger 章断言 + schema 复验 + 附带伤害断言）/ fail-closed 零写入 / file-locks-only / 幂等字节不变；WriterCliHandlerTests 两测 exit0/exit2。缺口：无 crash-resume 直接测试（P3 级，随 F-1 一并补） |

---

## 5. AI 代码专项 5 项

| # | 检查项 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock 残留 | **无** | 测试中 `mock.patch` 仅限 stdout 捕获（CLI handler 测试合法用法）；无业务逻辑 mock |
| 2 | 硬编码返回值 | **无** | 所有路径经真实管线（真实文件写、真实 ledger 事务）；测试断言与文件系统实际状态比对（字节级） |
| 3 | 幻觉 API 调用 | **无** | `locks_release` 引用的全部符号（`_ledger_transaction`/`_complete_pending`/`_TargetLock`/`SCHEMA_WINDOW`/`_snapshot_lock_fields`/`_validate_locks_schema`/`decide_operation_replay`）均实证存在于源码 |
| 4 | 未实现 TODO | **无** | diff 中无 TODO/FIXME/占位实现；stamp 分支真实可达（§1.2 实证） |
| 5 | 过度实现 | **无** | 变更严格限于 B-10 范围；shrink-locks/closure_chain 语义零触碰（源码无相关改动）；stamp 是披露过的最小留痕扩展；重定基线为机械 +1 |

---

## 6. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | 0 | ✓ |
| 5 维度全覆盖 | 100% | 5/5 有结论 | ✓ |
| 每条发现标注级别 | 100% | F-1~F-4 全带 P 标签 | ✓ |
| 设计一致性 | 已完成 | 与 triage FIX-370 / 规划 §5 B-10 对照：task 锚定真删除 ✓、先登记后删除 ✓、幂等 ✓、fail-closed ✓、shrink-locks 零改动 ✓；governance_cost 模式（模块自治 + 引擎仅接线）遵守 ✓ | ✓ |
| AI 专项 5 项 | 全部完成 | §5 全部有结论 | ✓ |

## 7. 终态备注（APPROVED_WITH_NOTES 随行备注）

1. **F-1（P2，遗留）**：crash-resume 恢复腿的 released_files 审计章缺口——建议记录到跟踪表，随下批变更修复或如实修订注释披露。
2. **F-2（P3，待验证）**：acquire 侧 record-target 锁互斥未验证（存量面）——建议独立入账验证。
3. Developer 验证声明（pytest 93/93 + 77 + 27 + manifest 967 PASS + capability PASSED + smoke）本席未独立复现（Bash 禁止），静态一致性核验全部通过；建议 Coordinator 侧保留 CI/验证命令输出作为合并前证据。
4. `unresolved_blockers=0` ——本报告无 BLOCKING finding。

---

*Review report generated by Code Reviewer Agent (Round 0) — read-only review; no code modified.*
