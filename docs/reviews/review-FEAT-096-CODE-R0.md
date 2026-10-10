# FEAT-096 Code Review R0 — 执行隔离与恢复保守面四件套（写并发限制+被审/在写互斥+只读快照+租约失权回收）

- **轮次**: R0（初审）
- **审查方**: Code Reviewer Agent（只读审查；唯一写面 = 本报告；未修改产品代码、未触碰 `.governance/`、未 commit）
- **审查对象**: 工作区未 commit 变更 9 文件（HEAD `099acbf`；`git status --porcelain` = 7 M + 2 ??；`git diff --stat` = 400 insertions / 16 deletions）——与任务申报 **完全一致**（9/9 对上，零未申报文件）
- **任务契约**: `.governance/execution-packets.json` packets.FEAT-096（实读全键：allowed_change_scope / non_goals×3 / quality_budget 六维 / scope_guard / rollback_plan）
- **结论**: **NEEDS_CHANGE**（P0=0；P1×1 本轮必须修复——并发正确性缺陷位于本票核心交付面；P2×3 / P3×7）

---

## 0. 结论与理由

**NEEDS_CHANGE ｜ P0=0 ｜ P1×1（本轮必须修复） ｜ P2×3 ｜ P3×7**

四件套的单写者语义、拒绝序、失权回收触发链、旧锁向后兼容、能力诚实披露（验收①）全部经一手证据成立；四项硬门槛独立复现通过；Developer 的「1110 tests OK」声明被独立复现精确成立（§5 行 4）。**但 P1-1 是本票核心租约（shared-file concurrent-write safety）上的未同步读-改-写竞态**：reclaim 对 `agent-locks.json` 的写回不持有该文件既有的 `_TargetLock` 协议锁，与本仓唯一其它写者族（governance_store acquire/release/amend，三处全部持锁）存在丢失更新窗口——丢失的是**活性租约条目**，后果恰是本票立项动机（REV-009 并发重写域破坏可审计性）的复现路径。修复成本一行量级（在已持有的 state.lock 内加持 `_TargetLock(locks_file)`，锁序 state→target 无环），按「发现即闭环」纪律应在本轮闭环，而非作为遗留项进入已关票。故取 NEEDS_CHANGE 而非 APPROVED_WITH_NOTES。

---

## 1. 发现清单

### P1-1（关键·本轮必须修复）reclaim 对 agent-locks.json 的读-改-写未持既有跨进程锁协议——与 governance_store 写者族存在丢失更新竞态

- **位置**: `infra/execution_isolation.py:1182-1184`（`_reclaim_locked` 内 `_write_json(target, locks)`——整个 RMW 仅由本模块私有 `state.lock`（`.execution-isolation-locks/state.lock`，L377-428）保护）；读取面 `:497-528`（`_load_locks`）。
- **事实**（一手核验）: `agent-locks.json` 的生产写者全仓只有两族——①governance_store（`governance_store.py:2136/2257/2360` 三处，**全部** `with _TargetLock(governance_dir / LOCKS_FILE_NAME)`，锁文件落 `.governance-store-locks/agent-locks.json.lock`，`:534-537`）；②本次新增的 execution_isolation reclaim（**不持**该锁）。closure_chain 只读（`closure_chain.py:2415-2440` 查世界）并把释放委托回 governance_store；change_triage/loop_migration 不写。两个锁命名空间完全不相交（`.governance-store-locks` vs `.execution-isolation-locks`，均实测确认）。
- **竞态链**: 进程 A（isolation-lease-reclaim / begin_write 拒绝触发路径）持 state.lock 读 locks（条目 X 已过期、Y 活性）→ 进程 B（agent-locks-acquire）持 target-lock 完成一次加锁写回（新增条目 Z）→ A 基于旧快照删除 X 后整体写回 → **Z 丢失**。反向交错则会复活刚被回收的过期条目。两种方向都破坏 Check 26 账本一致性；丢失活性租约的直接后果是同域可能出现两个自认持锁的写者——正是执行包 success_metrics 要消除的事故类。
- **影响评估**: 触发窗口为亚秒级、需要 reclaim 与 acquire 并发（reclaim 由过期拒绝/独立回收触发，频率低）；且 state-slot 门（按域互斥、由 state.lock 串行）对走门的第二写者仍兜底，故损坏面限于租约账本而非门本身——据此定 P1 而非 P0。但本票即并发安全票，交付物自带其立项缺陷类的新实例，不应带病合并。
- **修复建议**: `_reclaim_locked` 在写回 locks 前 `with _TargetLock(Path(locks_path) or governance_dir/'agent-locks.json', timeout_seconds)`（从 governance_store 导入；锁序 state.lock → target-lock 单向，governance_store 只取 target-lock，无环无死锁）。补一条与 acquire 并发的回归用例（可用两真子进程 + 时序夹逼，或最小化为「reclaim 期间 target-lock 被持 → reclaim 仍正确合并」的序列化断言）。

### P2-1（建议·原则上本轮修）under-review 绑定无 TTL、无接管、无管理员释放面——Reviewer 崩溃即永久封锁其文件域

- **位置**: `infra/execution_isolation.py:1059-1065`（`state["reviews"][domain]` 绑定，无 expires_at）；`:1090-1130`（`release_review` 仅同 task 可释放；无 --force/管理员面）。
- **事实**: 写槽有陈旧语义（TTL 600s + 过期清理 + lockfile 陈旧接管，L750-756/L444-484），reviews 绑定没有任何过期通道。Reviewer 崩溃于 release 前 → 域内写入永久 `under_review` 拒绝；恢复路径只有「同 task 重 spawn 后 release」（治理流内可行）或手改模块自有的 `execution-isolation.json`（manual_intervention 领域，无 CLI 面）。对照：36 锁悬挂 20h 是本票引证的第一根面，写槽面已治、review 面复刻同型悬挂。
- **建议**: 镜像 slot 陈旧语义给 reviews（TTL + 下一写者触发清理 + reclaim_log 审计），或在披露中明确该恢复路径并补一条崩溃恢复用例。

### P2-2（建议·原则上本轮修）非规范域串可同时击穿快照containment 与 snapshot_immutable 前缀门

- **位置**: `infra/execution_isolation.py:203-211`（`_domain` 仅折叠反斜杠与前导 `./`，不拒绝 `..` 段、不做规范化 containment）；`:1023-1028`（快照拷贝 `target = snapshot_root / domain`，`target.parent.mkdir(parents=True)` 可越出快照根）；对照 `:571-582`（snapshot 门 = 字面 `startswith(".governance/review-snapshots/")` 前缀判断）。
- **事实**: ①`--files "docs/../../outside.txt"` 的快照 create 会在快照根**之外**落盘并 chmod 只读——击穿本模块自己声明并测试的不可变根不变量；②`"docs/../.governance/review-snapshots/SNAP-x/f.md"` 不命中前缀判断（以 `docs/` 开头）但解析后**位于快照根内**——被审快照文件的「sanctioned write 拒绝」被非规范路径绕过，而这是件③披露的执行面（「write gate refuses any sanctioned write under the snapshot root」，docstring L21-24）。威胁模型受限（CLI 调用方即本仓代理，非权限提升），但击穿的是模块自设不变量，且修复极小。
- **建议**: `_domain` 拒绝含 `..` 段的输入（schema_violation）；快照 create 与 snapshot 前缀判断统一改为「规范化后 containment 断言」。各补一条红测。

### P2-3（建议）三处已实现的拒绝/失败路径零测试覆盖

- **位置与事实**:
  (a) 多域部分授权回滚 `infra/execution_isolation.py:794-824`（lockfile 冲突 → 全有或全无回滚）——无任何用例，回归可静默破坏原子性承诺；
  (b) 隔离态文件损坏的 fail-closed 面 `:316-343`（`_load_state` → `manual_intervention`）——只测了 locks 损坏（`test_execution_isolation.py:394-399`），state 损坏面未测；
  (c) 同秒 snapshot-id 冲突拒绝 `:1012-1018`——未测。
- **建议**: 各补一条最小用例（(a) 可用「第二域预置他人 lockfile、state 缺席」构造，兼测崩溃窗口披露）。

### P3-1（讨论）`_StateLock.__enter__` 非 FileExistsError 的 OSError 会泄漏进程内 threading.Lock

- **位置**: `infra/execution_isolation.py:389-406`——except 仅捕 `FileExistsError`；`os.open` 抛 `PermissionError` 等 时 `self._inproc` 已 acquire 且不释放，该键进程内此后永久死锁。`IsolationLockTimeout` 路径已正确释放（`:404`）。建议 try/except 包裹整个循环并在异常时释放 inproc（governance_store `_TargetLock.__enter__` `:542-563` 同型问题，先例披露在案——至少应同样披露）。

### P3-2（讨论）locks 重建式写回：静默丢弃假想的兄弟键、静默纠偏无效节（与 governance_store fail-closed 口径分叉）

- **位置**: `infra/execution_isolation.py:497-528` + `:1182-1184`。`_load_locks` 重建为两键 dict；`file_locks`/`active_tasks` 非法时静默置 `{}`（governance_store `locks_load` `:1853-1868` 对同型损坏 `_refuse` fail-closed）。当前 canonical schema 恰为两键（governance_store `:1853` 同样重建），**今日无数据丢失**；但 reclaim 在 file_locks 被纠偏为空时不会写回（reclaimed 必空），active_tasks 损坏 + file_locks 有过期项的混合场景会写出「已纠偏」文件。未来 schema 若加兄弟键（如 updated_at）会被无声剥除。建议写回前保留未知兄弟键，或在注释里显式钉死两键契约。

### P3-3（讨论）冻结面再基线的 rider 未逐项归属（偏离 FIX-441 非掩蔽对账先例）

- **事实**: ①`architecture-baseline.json` anchor_loc 27957→28120（+163）——本票 verify_workflow 实增 +103，余 **+60 来自 FIX-442/FEAT-094**（c783cff3..HEAD 间落地、上次 regen 后未重锚；git log 三 commit 实证）。既有 design_anchor_note 已载「实测为准 at regen time」惯例，合法吸收，但 FIX-441/FIX-438 先例要求「+N=来源 commit 机证」的一行归属，本次没有。②`snapshots.json` `skip_kind: NoneType→str`（deferred 探测器捕获态翻转，环境敏感）——FEAT-093 曾为同型翻转在 test_contract_matrix.py 写明 make-up rider，本次 regen 未披露。两者均建议补一行归属注释（不改数）。

### P3-4（讨论）`_domain_lockfile` 文件名折叠可别名两个不同域（false-conflict 方向）

- **位置**: `infra/execution_isolation.py:439-441`（`/`→`__`、`:`→`_`）。`docs/a.md` 与名为 `docs__a.md` 的文件共享一把锁。后果方向 = 误拒（fail-closed），无安全损失；建议折叠改为对 domain 做 sha1 短摘要后缀或拒绝含折叠歧义字符的输入。

### P3-5（讨论）快照只读的边界披露可再加一句「chmod 非内核边界」；manifest 无读取侧校验面

- **位置**: `infra/execution_isolation.py:1029/1057`（chmod S_IREAD）、`:1045-1056`（manifest 记 sha256 但无 verify 面）。模块级披露（CLI-level / host_isolation_level=unverified）已诚实覆盖大面；但 POSIX 下 rename-over-readonly（目录可写时）可绕 chmod、Windows 目录本身未置只读——建议在快照段加一句显式边界语（与 review 焦点「chmod 非内核边界的披露是否诚实」对齐），并考虑 isolation-status 附带快照完整性重算（sha256 复核）作为审计面。

### P3-6（讨论）lease_expired 拒绝措辞暗示「重新取得租约」是被门强制的，实际回收后无租约重试即获授权（披露边界，措辞对齐）

- **位置**: `infra/execution_isolation.py:592-596`（detail：「重新写入须先经派发重新取得租约」）对照模块披露 `:44-47`（leaseless retry 归派发协议/FEAT-095——本门不管）。语义上：观察过期的那次尝试被拒 + 触发回收后条目已删，同 task 再试即无 lease_expired 拒绝（write slot 不要求持有租约）。与 non_goals 一致、已披露，不构成缺陷；但 refusal 文案对「须先」的强度超过了门实际执法面。建议措辞改为「按派发协议应重新取得租约（本门不执法）」，或在 judge 对「域曾有租约且现无」输出 WARN。

### P3-7（讨论）全量 discover 口径 exit 1 的归因未逐条枚举（环境族先例在案）；验收口径应钉在模块跑

- **事实**: 我的 `unittest discover`（全 tests 目录）exit 1，尾部为 takeown/icacls remediation JSON 面——与 0.83/0.84/0.85 release-checklet 登记的环境敏感族（pre_commit hooks/WSL/dsh-doctor 面）形态一致；本票四件套相关文件（test_execution_isolation 25 / wiring 7 / registry+contract 104 / test_verify_workflow 全模块 1110）全绿。建议 EVD 行以包内验收命令（模块跑 1110 OK + check-governance FAIL 清零）为准，discover 口径如需引用则附失败集逐条归因（先例：release-checklist-0.83.0 #10）。

### P3-8（讨论）小项两则（登记备查）

- `begin_write` 同调用重复域（如 `["docs/a.md","docs/a.md"]`）会走「unlink 自己 lockfile 再重建」两次（`infra/execution_isolation.py:766-784`）——幂等无害，拒绝路径会重复记 waiters；建议去重。
- waiters 记录在后续成功授权后不清除（:726-738 只增）——advisory 日志语义可接受，建议注释钉死「等待者=历史拒绝快照，非队列」。

---

## 2. 五维度结论（硬门槛 ②：100% 覆盖）

| 维度 | 结论 | 依据（一手） |
|------|------|------|
| **正确性** | **PASS（带 P1-1/P2-2/P2-3）** | 单写者语义逐行核验：拒绝序（快照→自租约过期→被审→写冲突，`judge_write` `:568-650`）与文档一致；全有或全无授权+回滚 `:749-824`；`end_write` 非持有者拒绝且保护继任者 lockfile（`:886-892`——代码比 docstring 披露的侵蚀窗口更强）；跨进程原语=域 O_EXCL lockfile+全局 state.lock 双层，模块内全部变更路径都持 state.lock（锁序单向无死锁）；stale 接管（payload expires_at 或 mtime>600s）与崩溃窗口披露 `:49-61` 相符。缺陷面见 P1-1（跨模块锁协议缺失）、P2-2（containment）、P2-3（未测路径） |
| **安全性** | **PASS（带 P2-2/P3-5）** | 输入校验：task_id 闭式正则、TTL int>0、files 非空（`:290-294/:692-699`）；无注入面（无 shell/SQL）；无硬编码敏感数据；fail-closed 一致（损坏文件拒绝而非猜，`:316-343/:497-528`）；错误码闭式词表+disposition（`:163-183`）。快照不可变=chmod+写门双层（Windows 实测 PermissionError，`test:313-321`）；边界诚实度见 P3-5 |
| **可维护性** | **PASS** | 模块自包含（stdlib-only）、组合根+引擎 thin entry 单一选项事实源并有 drift 守卫测试（`test_verify_workflow.py` Feat096 `test_isolation_module_shares_one_option_fact_source`）；策略/锁分离以模块边界+CLI 契约达成（quality_budget 口径，见 §4）；命名/注释与仓内 caliber 一致；28n **零新增**（check-architecture-health 输出无 execution_isolation 条目，4E/33W 全为既有面）；1606 行含 ~350 行 docstring，四个子系统+CLI+披露面比例相称 |
| **性能** | **PASS** | judge ≤10ms 守护用例 median-of-9（`test:468-485`，实测 0.827s 全绿含该用例）；无冲突路径 <0.5s 且零 warning（`test:487-498`）；锁轮询 50ms、状态裁剪上限 50/200/100 有界（`:153-156/:346-356`）；judge 无副作用不建锁文件（`:536`）符合预算面 |
| **测试覆盖** | **PASS（带 P2-3）** | 25 单测+7 接线测全绿（§5）；真实子进程跨进程互斥（DEVNULL+exit code 断言，沙箱安全口径）；旧锁 red-test-first 且断言「可读（judge 拒绝过期）+可回收」双面（`test:429-451`）；快照只读双面（chmod PermissionError+写门拒绝）；失权=拒绝+回收+审计三连带断言（`test:347-372`）。缺口= P2-3 三路径 |

---

## 3. AI 代码专项 5 项（硬门槛 ⑤）

| 项 | 结论 | 依据 |
|----|------|------|
| mock 残留 | **无** | 生产模块 grep `mock/Mock/pdb/breakpoint` 零命中（仅 5 处 CLI `print`，均为合法 stdout 输出面）；测试侧 `mock_env`（临时环境变量上下文）与 `patch.object`（引擎全局注入）为正当测试工具，非残留 |
| 硬编码返回值 | **无（有据静态披露除外）** | `capability_disclosure`（`:1339-1373`）的静态串逐条对上落盘报告事实（§4 验收①）；无业务逻辑硬编码返回 |
| 幻觉 API | **无** | 导入全部 stdlib（argparse/hashlib/json/os/re/stat/sys/tempfile/threading/time/datetime/pathlib）；1110+25+7+104 测试实跑通过即 API 真实性的行为证据 |
| 未实现 TODO | **无** | grep `TODO/FIXME/XXX/HACK` 零命中 |
| 过度实现 | **无** | 逐面映射：四件套+回退开关+披露+状态面各对应验收项或 quality_budget 维度；1600 行单模块相对仓内 caliber（governance_store 2708 行、重 docstring 风格）不构成上帝模块（单一职责=执行隔离保守面）；唯一可议的 `_split_cli_list` 分号容忍为微幅 YAGNI（P3-8 级） |

---

## 4. 设计一致性（硬门槛 ④）

**non_goals×3 逐条**:

| non_goal | 裁定 | 依据 |
|----------|------|------|
| 不引入重依赖虚拟化/容器 | **符合** | stdlib-only 实测；CAPABILITY_REPORT_REF 指向落盘报告，host_isolation_level=unverified 全链一致（模块 docstring `:35-47`、disclosure `:1339-1373`、status 内嵌 `:1281-1284`、测试 `:532-547` 钉死） |
| 不做 FEAT-095 派发侧执法 | **符合** | 他人活性租约=披露 WARN 不拒绝（`:645-650`）；leaseless retry 归派发协议（`:44-47` 披露，P3-6 仅措辞对齐）；under_review/write_conflict 拒绝是本门自身互斥语义非派发执法 |
| agent-locks.json 字段格式向后兼容 | **符合** | 零新增必填字段（状态全部放模块自有 `execution-isolation.json`，`:69-73`）；旧格式（pre-FEAT-013 无 expected_new/极简 active_tasks）可读可回收 red-test-first（`test:429-461`）；reclaim 只删整条目、保留条目原字段 |

**验收①（能力诚实）**: 报告在盘（`docs/research/feat-095-harness-enforcement-capability-2026-10-10.md`，Test-Path=True）；模块披露的三条 report_conclusions 与报告 §5 矩阵行（L199「宿主级一列全部为未证实」）、§7 U1（L221「仅架构推断」）、§6 发现1（L207「插件零接线」）逐条对得上——**零宿主级声称成立**。

**quality_budget 六维**: performance ✓（§2 表）；reliability ✓（1110 全绿复现+旧锁兼容+跨进程稳定；P1-1 为新引入的并发缺口，修复后闭环）；security ✓（失权拒绝+快照只读双面红绿；P2-2 containment 缺口）；accessibility ✓（`render_status_text` grep 锚点测试 `test:500-526`）；ux ✓（拒绝详情含持有者+预计释放并有断言 `test:171-186`；无冲突零感知 `test:487-498`）；maintainability ✓（策略/锁分离经模块边界+thin entry 达成、28n 零新增实测）。

**allowed_change_scope**: 9 文件全部在票面（四件套本体+测试、五子命令接线+测试、四冻结面文件走 documented contract-change path）；无顺带重构、无版本 bump、无 fixture 漂移（skip_kind 翻转为 regen 捕获态，P3-3 建议补披露）。Developer 「不加 registry 行=FIX-438 同型 landing omission」的判断正确——commands dict 实增 5 键而 `_COMMANDS` 不加行必然打破 registry 守卫；行序按字母位插入正确，docstring 计数 99→105 与 17 outside/88 monolith 再普查自洽。

---

## 5. 验证命令与输出（审查者独立实跑）

| # | 命令 | 结果 |
|---|------|------|
| 1 | `git status --porcelain` + `git diff --stat` | 9 文件（7M+2??）+400/−16，与申报一致 |
| 2 | `python -m unittest skills.software-project-governance.infra.tests.test_execution_isolation -v` | **Ran 25 tests in 0.827s — OK** |
| 3 | `python -m unittest …test_verify_workflow.Feat096ExecutionIsolationWiringTests -v` | **Ran 7 tests in 0.099s — OK** |
| 4 | `python -m unittest …test_verify_workflow`（全模块，两遍） | **Ran 1110 tests in 456.862s — OK**（exit 0；与 Developer 声明「1110 OK（1103+7）」精确一致） |
| 5 | `python -m unittest …test_registry …test_contract_matrix` | **Ran 104 tests in 155.288s — OK** |
| 6 | `verify_workflow.py check-governance --summary-only` | **0 FAIL / 2 WARN**（①untracked=本票 2 新文件未 commit 所致；②28n closure_chain/dsh_compat 既有 advisory）——票面期望「FAIL 清零」成立 |
| 7 | `verify_workflow.py check-architecture-health` | 4 ERROR + 33 WARN（advisory）——**execution_isolation 零出现**=28n 零新增；全部命中为既有面 |
| 8 | `python -m unittest discover -s …/infra/tests -p "test_*.py"` | exit 1——尾部为 takeown/icacls remediation JSON（环境敏感族形态，与 0.83-0.85 release-checklist 登记族一致）；逐条归因未展开（P3-7），票面验收口径=行 4+6（全绿） |

---

## 6. 硬门槛自检（输出前）

| 门槛 | 判定 |
|------|------|
| P0 阻塞问题数 = 0 | ✓（P0=0；P1×1 已显式声明为「本轮必须修复」——NEEDS_CHANGE 的依据） |
| 5 维度 100% 覆盖 | ✓（§2 逐项有结论） |
| 每条发现 P0~P3 + 文件:行号 + 事实 + 建议 | ✓（§1 全部四要素） |
| 设计一致性（non_goals + quality_budget 六维） | ✓（§4） |
| AI 专项 5 项逐一结论 | ✓（§3） |
| 事实依据红线 | ✓（每条结论指向文件行号/命令输出/落盘报告；未验证处显式标注——P3-7 discover 归因未逐条枚举如实声明） |

## 7. 给 Coordinator 的复审提示（R1 注入用）

R1 复审 MUST 逐条比对：①P1-1 修复= `_reclaim_locked` 持 `_TargetLock(locks_file)`（锁序 state→target）+ 并发回归用例；②P2-2 修复= `_domain` 拒绝 `..` + containment 断言（双红测）；③P2-1/P2-3 至少补崩溃恢复语义与三未测路径用例（或显式遗留登记）；④P3-3 归属注释。其余 P3 可遗留。修复后预期结论路径：APPROVED 或 APPROVED_WITH_NOTES（unresolved_blockers=0）。
