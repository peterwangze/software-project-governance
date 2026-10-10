# FEAT-096 Code Review R1 — 复审：P1-1 协议锁修复 + P2-2 域规范化修复验证

- **轮次**: R1（复审——验证修复，非重审全票）
- **前轮引用**: `docs/reviews/review-FEAT-096-CODE-R0.md`（R0 结论 NEEDS_CHANGE；P0=0 / P1×1 / P2×3 / P3×7）
- **审查方**: Code Reviewer Agent（同一 Reviewer，M7.4 T1 复审必达；只读审查，唯一写面 = 本报告；未修改产品代码、未触碰 `.governance/`、未 commit）
- **返工范围声明核验**: Developer 声明「仅触 2 文件（execution_isolation.py + test_execution_isolation.py），CLI 面零变化」——**成立**：`git diff --stat` 7 个 M 文件增量与 R0 完全一致（+400/−16），两新文件 1606→1720 / 572→776 行；parser/cmd_*/`__all__` 面未动（接线 7 测试 + option-fact-source drift 守卫全绿佐证）
- **结论**: **APPROVED_WITH_NOTES（unresolved_blockers=0）**

---

## 0. 结论

**APPROVED_WITH_NOTES ｜ unresolved_blockers=0 ｜ P0=0 ｜ 本轮新增 P0/P1 = 0**

R0 两项必修发现（P1-1/P2-2）**均已修复且经独立验证**：修复语义正确、恰好覆盖 R0 修复建议、带真实承载力的回归测试（red face 经内存探针独立复现）、未引入新问题（锁序无环/冷面不变/热路径正对照在位）。R0 裁定留后续票的 P2-1/P2-3/P3×7 **未恶化**（锚点逐一确认未动）。全套件回归零退化（1110 OK 独立复现）。新增 1 条 P3 级措辞微瑕（P3-9）。无未解决阻塞项——可合并；备注项移交 Coordinator 按遗留纪律处置。

---

## 1. R0 findings 逐条处置（复审义务 (1)）

| R0 finding | 处置 | 验证依据（一手） |
|------------|------|--------|
| **P1-1** reclaim 对 agent-locks.json 未持协议锁（丢失更新竞态） | **已修复（充分）** | 见 §2 逐要素核验 |
| **P2-2** 非规范域串越根 + 绕前缀门 | **已修复（充分）** | 见 §3 逐要素核验 |
| **P2-1** under-review 绑定无 TTL/无管理员释放 | **未修复（R0 已裁定留后续票）·未恶化** | `release_review` 同 task 语义未动（`execution_isolation.py:1163`）；reviews 绑定逻辑零变化 |
| **P2-3** 三条已实现拒绝路径零测试（多域回滚/state 损坏 fail-closed/同秒 id 冲突） | **未修复（留后续票）·未恶化** | 新增 6 用例均属 P1-1/P2-2 归属，未含此三路径；对应实现路径未变 |
| **P3-1** `_StateLock` inproc 泄漏（非 FileExistsError OSError） | 未修复·未恶化 | `:460` 区域 except 结构原样 |
| **P3-2** locks 两键重建的未来 schema 脆弱 | 未修复·未恶化 | `_load_locks` 重建逻辑原样（`:540-571` 区） |
| **P3-3** 再基线 rider 未归属（+60 外来吸收 + skip_kind 翻转未披露） | 未修复·未恶化 | architecture-baseline.json / snapshots.json 与 R0 逐字节同 diff（stat 相同） |
| **P3-4** lockfile 名折叠别名 | 未修复·未恶化 | `_domain_lockfile` 逻辑原样（P2-2 顺带缩小了 `:` 别名面——`:` 现被入口拒绝） |
| **P3-5** chmod 边界措辞 + manifest 无校验面 | 未修复·未恶化 | 快照段原样 |
| **P3-6** lease_expired 文案强于执法面 | 未修复·未恶化 | `:658` 措辞原样 |
| **P3-7** discover 口径归因未枚举 | 未修复·未恶化 | 无新增归因文本；本轮验收口径同 R0（模块跑全绿） |
| **P3-8** 重复域/waiters 不清除小项 | 未修复·未恶化 | 原样 |

---

## 2. P1-1 修复验证（复审义务 (3)：两要素逐一）

**要素① 物理获取协议锁** — `execution_isolation.py:1236-1241`：`from governance_store import StoreError, _TargetLock`（函数内局部导入）后 `with _TargetLock(target, timeout_seconds)` 包住整个读-改-写。`target` 解析与 governance_store 三写者同一文件路径 → 同一锁文件（`.governance-store-locks/agent-locks.json.lock`）。
- **锁序无环核验**: state.lock（外层，调用方已持——三调用点 `:782/:889/:1329` 均在 `with _StateLock(...)` 块内）→ target-lock（内层，本函数取）。governance_store 写者从不取 state.lock（全仓 grep 证实无反向取锁）；本模块无 target-lock 嵌套 target-lock 路径（`_TargetLock` 进程内臂为非重入 threading.Lock，同进程嵌套会死锁——不存在此路径）。**无死锁面**。
- **异常面**: `StoreError` → `CODE_LOCK_CONTENTION`（可重试，`:1299-1306`）；`exc.payload` 属性真实存在（`governance_store.py:282-287` 实读核实）——except 臂自身不会 AttributeError。
- **物理阻塞行为测试**: `test_execution_isolation.py:639-704`——父进程持真 `_TargetLock` 后 spawn 真子进程 reclaim，0.5s 后 `poll() is None` 断言仍在阻塞；释放后 rc=0 且终态正确（过期回收/活性保留）。时间戳按真钟播种（子进程 judge 无注入 now——细节诚实）。

**要素② 锁内新鲜重读（查世界不信快照）** — `:1242-1245`：`_load_locks` 在**双锁之下**重读磁盘，回收判定基于新鲜世界而非调用方旧快照；签名删除了 R0 的 `locks` 参数（三调用点全部适配新签名，实读核实）。效果：并发 acquire 在窗口内提交的活性租约被新鲜读**看见**→保留；并发 locks-extend 续期的租约不再被判过期。
- **确定性丢失更新测试**: `test_execution_isolation.py:584-637`——monkeypatch `_load_locks` 使第 2 次读（judge 读，处于门读→回收写窗口）时注入 racing acquire 提交（FIX-777 活性租约）；断言 calls≥3（锁内重读发生）+ racing 租约存活 + 过期租约真回收。
- **Red face 独立复现（内存探针，零落盘，`%TEMP%\feat096-r1-red-probe.py`）**: 模拟前置语义（锁内「重读」返回调用方旧快照）→ **racing 租约丢失**（`racing-lease-LOST=True` → 新用例 `assertIn(domain_b)` 必红）；对照跑（真实修复语义）→ calls=3、租约存活。**该回归用例非空转绿——承载力成立**。Developer 的 nullcontext red/green 声明与此独立复现互相印证。

**R6 冷面声明核验**: `python -I -B -c "import execution_isolation"` 后 `sys.modules` 零 governance_store 模块（直接实测）——函数内导入保冷面 207 成立；`test_registry`+`test_contract_matrix` 104 tests OK（含 R6 import guard 与冻结字面量）。

**未引入新问题**: 授权/拒绝路径行为保持（`:782-787/:889-894` 语义同 R0，仅签名适配）；reclaim_expired_leases 的 domains 范围仍取自外层读（新鲜读下缺失的新条目本轮不回收——保守方向，正确）；超时语义=可重试 fail-closed。

---

## 3. P2-2 修复验证

- **入口校验**: `_domain`（`:222-248`）拒绝绝对路径/`:`/NUL/`\r\n\t`/空段/`.`/`..` 段，返回 `""`；`_domains_or_error`（`:251-271`）一条坏输入**整拒**（schema_violation，列出全部冒犯项），空集亦拒。接入四个公共入口：judge（`:614`，先于任何状态读取——坏输入零状态读写）、begin（`:750`）、end（`:923`）、snapshot-create（`:999`）。
- **containment 纵深**: 快照拷贝循环内 `resolved_target.is_relative_to(resolved_root)` 断言（`:1085-1099`）——不变量自身承载，即使规范化门被绕过也不越根；前缀≡containment 等价注释落在 judge 前缀判断处（`:629-633`）。
- **测试 4 用例**（`:710-773`）: ①六种坏形态×judge/begin/end 三面 + 混合整拒 + **拒绝调用零状态写**断言（state 文件不存在，`:731-733`）；②越根目标真实存在（存在性检查会放行——只有规范化门能拦）+ 快照根下零落盘 + 源文件未被触碰；③R0 走私拼写给两入口拒绝；④**正对照防误拒**——普通路径 + `.governance/notes.md` 点目录热文件全通过（防过度扩张伤热路径，正是复审义务 (4) 关注点）。
- **无热路径误拒**: 正对照用例 + 31/31 全绿（含 R0 全部既有用例零修改通过）实证。

---

## 4. 独立实跑验证汇总

| # | 命令/动作 | 结果 |
|---|-----------|------|
| 1 | `git status/diff --stat` | 7M 与 R0 完全一致（返工仅触 2 新文件）；模块 1720 行/测试 776 行 |
| 2 | `python -m unittest …test_execution_isolation -v` | **Ran 31 tests in 1.489s — OK**（25+6；耗时增量 0.66s ≈ 真子进程 0.5s 阻塞用例） |
| 3 | `…Feat096ExecutionIsolationWiringTests` | **Ran 7 tests — OK**（CLI 面零变化佐证） |
| 4 | `…test_registry …test_contract_matrix` | **Ran 104 tests in 124.077s — OK**（冻结面 + R6 import guard） |
| 5 | `…test_verify_workflow`（全模块） | **Ran 1110 tests in 519.118s — OK**（exit 0；Developer 自报 487s OK，双双全绿） |
| 6 | `python -I -B -c "import execution_isolation"` + sys.modules 检查 | 冷面**零** governance_store 模块（R6 声明直接证实） |
| 7 | `check-governance --summary-only` | 0 FAIL / 2 WARN（既有 28n advisory + untracked——与 R0 同构） |
| 8 | `check-architecture-health` | 4 ERROR + 33 WARN（advisory）与 R0 **完全一致**；`execution_isolation` 零出现（1720 行仍零 28n 面） |
| 9 | 内存探针（red face 复现，零落盘） | 前置语义→racing 租约丢失（新用例必红）；修复语义→calls=3+存活（绿） |

---

## 5. 新增发现（本轮 1 条，P3）

### P3-9（讨论）`_domain` docstring 的「control characters are all refused」强于实现

- **位置**: `execution_isolation.py:232`（docstring）对照 `:241-244`（实现只拒 NUL + `\r\n\t`；`\x01`-`\x08` 等其余 C0 控制字符不拦）。
- **事实**: 其余 C0 控制字符在 Windows 文件名非法、POSIX 罕见，无别名/containment 风险——实现面安全；纯措辞与实现的一行差距。建议二选一：实现补 `any(ord(c) < 0x20 for c in text)` 或 docstring 收窄为「NUL and line/tab controls」。

---

## 6. 五维度 / AI 专项 / 硬门槛（复审口径：增量面重验 + 全量面复跑）

- **正确性**: P1-1 修复语义正确（§2 两要素+锁序+异常面）；P2-2 修复语义正确（§3）。既有 25 用例零修改全绿=行为面无回归。
- **安全性**: containment 闭环（规范化门+纵深断言+等价注释）；`:`/ADS 面顺带收窄。
- **可维护性**: 函数内局部导入（authority_ledger 同型先例）+ 修复处 docstring 完整披露协议加入与锁序——可审计性提升；模块 1720 行仍零 28n 面。
- **性能**: 31 用例含 ≤10ms judge 守护全绿；新增阻塞用例 0.5s 为测试构造非生产路径；生产面开销增量=条件路径上一次锁获取+重读（仅 reclaim 触发时）。
- **测试覆盖**: 31 用例；两新用例承载力经 red-face 探针独立证实；P2-3 三路径仍缺（留后续票，R0 已裁定）。
- **AI 专项 5 项（增量）**: mock 残留无（monkeypatch 仅测试内，正当手段）；硬编码无；幻觉 API 无（局部导入经冷面探针+31 用例行为证实）；TODO 无（grep）；过度实现无（+114 行全部落在两修复及其披露/测试归属）。
- **硬门槛**: P0=0 ✓；五维度 100% ✓；逐条发现带级别+行号+事实+建议 ✓（§1/§5）；设计一致性维持 ✓（non_goals×3 未破坏——锁字段格式仍零新增必填、无 095 执法、无重依赖；allowed_change_scope=返工恰触修复所需最小面）✓；`unresolved_blockers=0`（结构化字段，见结论行）。

## 7. 移交 Coordinator 的遗留清单（均非阻塞）

P2-1（review 绑定 TTL/管理员释放）、P2-3（三未测拒绝路径）、P3-1~P3-9（含本轮新增 P3-9 措辞微瑕）——建议按 R0 §7 + 本报告登记入后续票池（发现即闭环已在本票两必修项上履行；其余为 R0 显式裁定的遗留项）。本票按 done_definition 可收口：commit+push 由 Coordinator 按 interruption_policy auto_execute 面执行。
