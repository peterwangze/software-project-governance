# Review Report — FIX-385（B-7b 大表迁移）· Code Review R0

> round: R0（首轮） · task: FIX-385（P2，E6——⑩拆票之三；FEAT-061 衔接）
> reviewer: Code Reviewer Agent（governance workflow 0.87.0）
> 日期: 2026-09-24
> 审查对象（工作树未 commit diff，严格限定两文件；并行面 FEAT-063/FEAT-044/FEAT-045 在途——未触碰、未审查）:
> - `skills/software-project-governance/infra/archive.py`（+964/−86）
> - `skills/software-project-governance/infra/tests/test_archive.py`（+583，17 新测试）

---

## 总结论

## **APPROVED_WITH_NOTES** · `unresolved_blockers=0`

| 级别 | 数量 | 说明 |
| --- | --- | --- |
| P0 阻塞 | **0** | — |
| P1 关键 | **1** | 衔接面 TOCTOU（F-1）——强烈建议本轮修复，遗留路径明确（不构成 BLOCKING：影响有界且自愈，见 F-1 分析） |
| P2 建议 | **3** | 申报口径准确性 ×2（F-2/F-3）+ 并行面失败披露（F-4） |
| P3 讨论 | **6** | F-5 ~ F-10 |

硬门槛核对：P0=0 ✓ · 五维度全覆盖 ✓ · 每条发现标注级别 ✓ · 设计一致性（ADR-006 / FEAT-060/061 模式符合性）已完成 ✓ · AI 专项 5 项全部完成 ✓。
依据 code-review SKILL 关闭条件：P0=0 且 P1>0（有遗留计划）→ 有条件合并（APPROVED_WITH_NOTES）。**建议**：Developer 在本工作树窗口内顺手修复 F-1（≈5 行，形态有 FEAT-061 P0-F1 先例），F-2/F-3 口径勘正并入 EVD 记录；随后按 M7.4 以 R1 复核 F-1 修复（逐条比对前轮 findings）。

---

## 1. 审查范围与方法（全部结论可复查）

- 逐行通读两目标文件 diff 与全文（archive.py 4472 行 / test_archive.py 5153 行中 FIX-385 相关段 L107-114、L116-126、L647-705、L1062-1075、L1077-1200、L1284-1478、L1480-2060、L2105-2304、L3877-3885、L3972-4045、L4133-4145、L4320-4417；test L4570-5149）。
- 依赖面核验：governance_store（`_atomic_write_bytes` L441、`_TargetLock` L511、evidence_append 持锁 L1140）、decision_repository（`load_authority` L318、`initial_authority`→MD_ACTIVE、`AUTHORITY_STATE_FILE` L131 与 pin 常量 L114 一致）、decision_migration（cutover/freeze L308、rollback_activate L836 持 `_TargetLock(md_target)`）。
- 实测（全部本会话机跑，输出见 §5）：RED 隔离复现 / GREEN 精确复现 / 全量 infra 套件 / pure-HEAD worktree isolate 两步归因实验 / 单源抽取纯度对照驱动 / 真实 host 只读探针（archive-integrity、migrate-big-table --dry-run）。
- 只读约束遵守：真实 `.governance/` 只读（探针为 dry-run/verify 类零写命令，事后核实零残留）；隔离沙箱均在 `%TEMP%`；审查期间未修改任何产品代码与并行面文件；`git worktree` 隔离副本已用后即删（`git worktree list` 已核实无残留）。

---

## 2. MUST 重点 8 项逐条裁决

### ① resume 世界判定正确性 —— **通过（实证）**
- 世界判定顺序「committed post-image → pinned input → diverged」三层完备（archive.py L1753-1781 finalized 分支、L1796-1827 resume 分支、L2008-2037 apply 窗内复检）：
  - crash-after-archive-write（hot 未写）：resume 时 `input_digest`（=当前热表摘要）== pinned input → candidates 从 `lines` 重绑定（含 idx 越界校验 L1841-1854）→ apply 内 archive 已存在且 digest 相符 → 只补 hot 腿。
  - crash-after-hot-rewrite（journal 仍 commit_intent）：当前热表摘要 == `commit.hot_after_digest` → `hot_leg_done=True`（L1802-1803，commit pin 先判，注释 L1798-1801 正确解释了判定顺序）→ 行文本从 **staged batch 工件**重-materialize（L1941-1943），count 对 pinned manifest 校验（L1944-1950）+ 合成 archive_text 对 `commit.archive_digest` 校验（L1958-1964）→ apply 只补 finalize 腿。
  - finalized + hot==post-image → 幂等 no-op；finalized + hot 匹配两者皆非 → `migration_state_conflict` 响亮拒绝（L1766-1779）。
- **batch 工件被删/篡改的行为**（任务点名）：删除 → `migration_batch_unreadable`（L1625-1646）；篡改 → 合成 archive digest 对 pin 校验失败 `migration_state_conflict`（L1958-1964）；游标声称 ahead of artifacts → `migration_cursor_ahead_of_artifacts`（L1909-1920）。三者均有测试（test_cursor_ahead_of_staged_artifacts_refuses L4890；删批/tamper 路径由前两者+守恒断言覆盖）→ **承重论证成立**：batch 工件不可信时永不静默降级。
- `input_digest` 命名在 resume 语境实为「本次运行起始的热表摘要」，与 pinned input 复用同一变量——判定逻辑正确（digest 按内容自证明），注释已部分解释；纯命名澄清记 P3 观察并入 F-5。
- 注入测试实证：staging 窗（test L4749，cursor=3 续迁仅补 3 批）、commit 窗（test L4796，archive 已写 hot 未写→补 hot 且 archive 不重复）、finalize 窗（test L4830，hot 已写 journal 未 finalize→仅 finalize）全过；守恒断言（每 EVD 全局恰一次，test L4705-4712）全过。

### ② 线性化与并发 —— **通过（附 F-1 衔接面例外）**
- commit 单线性化点声明核实：apply 三步（archive 写→hot 写→finalize journal）全部在 `with _big_table_target_lock(elog)` 内（L2009-2037），锁目标 = `_gov_dir()/evidence-log.md`，与机器写入器 `governance_store.evidence_append` 的 `_TargetLock(target)`（governance_store.py L1140，同一路径 → 同一 lockfile `.governance/.governance-store-locks/evidence-log.md.lock`）互斥——**机器写入 vs commit 窗的真实互斥成立**。
- 并发写热表检测窗口：apply 入口在锁内重读 digest（L2010），≠pin input 且 ≠post-image → `hot_table_diverged` 响亮拒绝（L2013-2021）；resume 入口同型检测（L1805-1816）。并发**另一迁移进程**收敛（双进程同 pin → 第二进程判 hot_done=True 幂等 finalize）；并发**外部写入** → 拒绝。注入测试 test_resume_refuses_loudly_on_hot_divergence（L4858-4888）实证。
- 残余窗口（锁内 digest 读与 hot 写之间的非持锁手写 TOCTOU）为锁模型固有边界；降级无锁时窗口扩大——并入 F-8。

### ③ 单源抽取纯度 —— **通过（实测等价）**
- `_classify_evidence_rows`（L1284-1363）抽取后 `_migrate_evidence` one-shot 路径（L1366-1446）改为 records 驱动 + line_idx 过滤重建 kept_lines（L1434-1436）。
- **实测**：old（HEAD archive.py）vs new 对同一边缘 fixture（compound-ID EVD-FIX-247 / 纯 cross-entity / mixed / live-ref / out-of-range / malformed / 重复行文本 / 非行文本）输出**全字段一致**——count=7、explain 逐条一致、hot_text 一致、archive_text 一致（驱动脚本对照，%TEMP%/fix385_purity/old.json vs new.json，逐字段 diff 全 SAME）。140 基线测试随 GREEN 157P 全过 → 可信度实证，非仅 diff 目检。
- `_archived_task_versions`（L1647-1664）与 migrate_by_version 原内联循环逐语句等价（含 try/except pass、sorted glob、setdefault 优先级）；`_EVIDENCE_ARCHIVE_TABLE_HEADER`（L1068-1071）与原硬编码两行逐字符一致。

### ④ FEAT-061 衔接面 —— **有条件通过（发现 F-1 P1）**
- 静态门完备：authority 判定在读投影前（L1121-1134）；非 MD_ACTIVE（含 CUTOVER_FROZEN/ROLLBACK_FROZEN/JSON_ACTIVE/unreadable）一律 raise；corrupt marker → `load_authority` 内部 `_fail` raise → 捕获 → `"unreadable"`（L1545-1562）→ fail-closed，测试 test_corrupt_authority_marker_fails_closed（L5127）实证。
- deferral 可见性全链：migrate_by_version 捕获记账（L2266-2281）→ dry-run 预检传播（L3880-3882）→ migrate_auto 双路传播（L3993-3994、L4042-4043）→ 摘要 ⚠️ 行（L4136-4144）→ CLI migrate 打印（L4378-4385）。无静默吞没路径。测试 L5093 实证（投影未被改写 + 其余类目正常迁移 + DEC 行留守）。
- **绕过路径存在**：entry 判定与 L1197-1199（archive 写 + `dlog.write_text` 热重写）之间**无锁、无 in-lock 复核**——并发 cutover（MD_ACTIVE→FROZEN→JSON_ACTIVE，其流程持 `_TargetLock(md_target)`，decision_migration.py L308/L836）落入窗口时，迁移把投影当权威重写（删行），正是该门要防的架构腐化。同型窗口在写入器侧已被 REVIEW-FEAT-061-CODE-R0 P0-F1 以 in-lock 复核修复（governance_store.py L1350 注释明言该威胁模型）。评级 P1 而非 P0 的理由：需并发 cutover 精确落入 migrate 运行窗（两者均为人工/Coordinator 驱动，现实低概率）；影响有界且自愈（store 侧数据不丢、行双存于 store+archive 文件、投影由 cutover 票的 sync 重建）。**修复建议**：`_migrate_decisions` 热重写前在 `_TargetLock(dlog)` 内重判 `_decision_authority_state()`（镜像 L1350 形态，≈5 行）。
- corrupt marker → unreadable → 拒绝：已实证（上）。`_DECISION_AUTHORITY_MARKER_NAME` pin 值与 decision_repository.AUTHORITY_STATE_FILE 逐字符一致。
- evidence 路径与 decision authority 解耦：测试 L5138 实证（JSON_ACTIVE 下 resumable 迁移照常完成并如实上报 `decision_authority_state`）。

### ⑤ 降级路径 —— **通过（披露核实，附 F-8/F-10）**
- try/except 隔离加载降级确认（L122-126）：peer 缺失时 `_TargetLock=None` → `_big_table_target_lock` 无锁 yield（L1535-1542）；`_atomic_write_bytes=None` → 本地 mkstemp+fsync+replace（L1505-1532，缺 dir-fsync，对照 governance_store L452）。
- digest 世界判定兜底声明核实：无锁下（a）resume/apply 入口的 digest 重读仍拒绝 pre-window 分叉；（b）双迁移进程因输出确定性而收敛；（c）**残余风险=commit 窗内非持锁写入者的 TOCTOU**（digest 读过之后、hot 写之前的丢更新）——降级场景中机器写入器（evidence_append）也失去互斥。申报措辞「digest 世界判定兜底」如实（有兜底、非零风险），披露成立；缓解建议见 F-8（按 import 拆分 try，避免 decision_repository 失败连带降级 lock+write 原语）。
- 降级路径 pragma no cover、无测试覆盖——如实申报，非隐瞒（F-8 记改进项）。

### ⑥ 17 测试判别力 —— **通过（RED 真实性实测，口径偏差记 F-2）**
- **实测 RED**：HEAD archive.py + 现行 17 测试（%TEMP% 隔离沙箱，HEAD archive.py 经 `git show HEAD:` 重建、零 resumable 引用核实）= **16 failed / 141 passed**（141 = 140 基线 + 1 控制测试 `test_md_authority_still_migrates_decisions` 在 RED 即过——其设计意图即控制组，不依赖新 API）。申报「RED 15F」与实测差 1（F-2，P2）。
- RED→GREEN 纪律实质成立：全部 12+4 个新行为测试 pre-diff 失败（AttributeError/KeyError/口径断言失败），post-diff 全过。
- **实测 GREEN**：157 passed（1.90s）——140 基线 + 17 新，精确复现申报。
- 判别力抽查：三 crash 窗注入使用 mock.patch 引擎自有写原语（无产品测试钩子）；diverged 测试断言拒绝码+零迁移副作用；游标篡改测试直接删 batch 工件。测试与实现同步性：无实现侧测试钩子、无为测试放宽的行为。

### ⑦ 验证复现 —— **通过（附 F-3/F-4 口径勘正）**
| 申报 | 实测 | 结果 |
| --- | --- | --- |
| GREEN 157P（140 基线+17 新） | `pytest test_archive.py -q` = **157 passed** | ✅ 精确 |
| 相邻 283P | 精确子集无法复原（申报未给命令）；改跑**全量 infra 套件** = **4099 passed / 7 failed / 1 skipped / 517 subtests**（23m19s） | ✅ 以更强证据覆盖（7F 归因见 F-4） |
| verify full PASSED | `verify_workflow.py verify` = **PASSED** | ✅ |
| cross-refs PASS | `check-cross-references` = 无悬空/无弃用路径/无循环引用 **PASS** | ✅ |
| manifest 881 canonical | `check-manifest-consistency` = **Canonical 882 / Actual 1018，PASS** | ⚠️ 数差 1（F-3） |
| archive-integrity（真实 host 只读）PASS | `archive.py verify` = **Pass: True**（1131 tasks / 1276 index entries，只读） | ✅ |
| archguard 6F 存量（worktree isolate） | **两步 isolate 复现**：pure HEAD worktree → 同 6 项 archguard F 原样复现（存量成立）；HEAD+仅 FIX-385 两文件 overlay → 仍恰同 6F、零新增 + inventory 测试 PASS（FIX-385 排除） | ✅ 方法与结论均复核成立 |

### ⑧ 边缘披露核验 —— **通过（附 F-4 并行面失败披露）**
- archguard 6F 存量：isolate 方法复核成立（见 ⑦ 表末行）——6F 为 HEAD pre-existing，非 FIX-385 亦非本工作树并行 diff 引入。
- evidence 固定名覆盖不对称——one-shot 侧未动的零回归声明核实：one-shot `_migrate_evidence` 的 `archive_path = evidence-v{range}.md` 直写路径（L1441）未改（覆盖不对称 pre-existing，非本 diff 引入）；resumable 侧经 `_make_incremental_archive_filename`（L647-677 扩展 evidence 族）+ apply 内存在性/digest 双检（L2022-2031，FOREIGN 内容 `archive_target_conflict` 拒绝）→ **commit 永不覆盖外来 archive 内容**成立。one-shot 侧零回归由 140 基线全过 + 纯度对照实证。
- `_parse_archive_version_range` 增量后缀扩展（L695-704）消费面核验：build_index/rollback 分组（`_get_migration_archive_group` L3329-3383——incremental 独立回滚单元 + base 名按 range 配对）/integrity 全兼容。

---

## 3. 五维度逐项结论

| 维度 | 结论 | 依据摘要 |
| --- | --- | --- |
| 正确性 | ✅ 通过 | 三 crash 窗完备（代码追踪+3 注入测试）；世界判定三层序正确；守恒断言；单源抽取实测等价；幂等/无可迁不建 journal/dry-run 零写（fresh+resumed）测试实证。例外：F-1（衔接面 TOCTOU，P1） |
| 安全性 | ✅ 通过 | 无注入面（无 shell/SQL/exec）；digest pin 覆盖 batch 工件/archive/热表全部承重输入，删改均响亮拒绝；batch_size 校验含 bool 排除（L1724-1729，测试 L4996）；无硬编码敏感数据 |
| 可维护性 | ✅ 通过 | 单源抽取×3（分类器/任务版本映射/表头常量）消除漂移面；复用原语不重造；注释与代码一致（F-9 一处字节级声明除外）。观察：`migrate_evidence_resumable` ≈365 行超 50 行指引——相位分段注释内聚，状态机拆分反损世界判定可读性，记 P3（F-7），不要求拆 |
| 性能 | ✅ 通过 | O(n) 单遍分类；批式原子落盘+游标，中断损失 ≤1 批；digest 计算次数与 1.7MB 规模乘积可忽略；无 N+1/O(n²) |
| 测试覆盖 | ✅ 通过 | 核心路径（计划/续迁/三 crash 窗/并发 diverged/篡改/幂等/CLI/衔接面×5）全有测试；边界（batch_size=1/ oversized/bool）有断言。缺口（如实披露，非阻塞）：双真进程并发无测试（锁收敛为代码追踪结论）；fallback 降级路径 pragma no cover；lock 争用路径无测试（F-10）。仓库未跑 coverage 工具——按 standard profile 阈值未量化，如实声明 |

## 4. AI 专项 5 项

| # | 检查 | 结论 | 证据 |
| --- | --- | --- | --- |
| 1 | mock 残留 | ✅ 无 | 产品代码零 mock；测试内 mock.patch 均为 crash 注入且随 with 块收敛，无跨测试泄漏 |
| 2 | 硬编码返回值 | ✅ 无 | 全部返回值由计算/IO 派生；测试常量 MIGRATABLE=54 与 fixture 推导一致（57−3×FIX-900 行） |
| 3 | 幻觉 API | ✅ 无 | 逐符号实测存在：`governance_store._TargetLock` L511 / `_atomic_write_bytes` L441；`decision_repository.load_authority` L318 / `AUTHORITY_STATE_FILE`=".decision-store-state.json"（与 pin 常量 L114 一致）；`_parse_completed_task_versions` L558、`_extract_tasks_from_archive_file` L2484、`_build_archive_header` L736、`_make_incremental_archive_filename` L647 |
| 4 | 未实现 TODO | ✅ 无 | FIX-385 区段（L1449-2060）grep TODO/FIXME/XXX/HACK = 0；「table-agnostic adapter」仅为注释级前瞻，CLI `choices=["evidence"]` 与实现一致，无空头承诺 |
| 5 | 过度实现 | ✅ 无 | 单表实现+常量 pin+原语复用；无未用参数/死分支（bool 排除有测试）；journal 相位机每相位均有消费者 |

## 5. 发现清单

### F-1（P1）衔接面 TOCTOU：`_migrate_decisions` authority 门仅 entry 判定，热重写无锁无复核
- **位置**：archive.py L1121-1134（entry 门）→ L1197-1199（`_write_archive_file` + `dlog.write_text`）；对照 decision_migration.py L308/L836（cutover/rollback 持 `_TargetLock(md_target)`）、governance_store.py L1345-1350（decision_append in-lock 复核 = REVIEW-FEAT-061-CODE-R0 P0-F1 先例）。
- **事实**：entry 判定（MD_ACTIVE）通过后、L1199 投影重写前，若并发 cutover 完成 MD_ACTIVE→CUTOVER_FROZEN→JSON_ACTIVE，迁移将以权威姿态重写投影（删行）且结果不记 deferral——正是 `DecisionStoreAuthorityConflict` 要杜绝的世界。任务问「有无绕过路径」：**有，即此窗口**。
- **影响**：有界且自愈——store 数据不丢（行双存 store+archive 文件）；投影失真由 cutover 票的 projection sync 重建；触发需并发 cutover 精确落入 migrate 运行窗（现实低概率）。故 P1 非 P0。
- **修复建议**：热重写前 `_TargetLock(dlog)` 内重判 `_decision_authority_state()`，非 MD_ACTIVE 则 raise（镜像 P0-F1 形态，≈5 行）；或至少在 L1197 前无锁重判一次（缩小但不闭合窗口）。
- **处置**：建议本窗口修复后 R1 复核；若遗留，MUST 记入 cutover 票的义务清单。

### F-2（P2）申报口径偏差：RED 15F → 实测 16F/141P
- **证据**：%TEMP% 隔离沙箱（HEAD archive.py `git show HEAD:` 重建 + 现行测试）`pytest -q --tb=no` = `16 failed, 141 passed`。141 = 140 基线 + `test_md_authority_still_migrates_decisions`（控制测试，不依赖新 API，RED 即过）。申报「RED 15F」隐含 2 测试 RED 即过，实测仅 1。
- **影响**：RED→GREEN 纪律实质不受影响（16/16 新行为测试 pre-diff 失败）；属证据记账数字失实。**建议**：EVD 记录勘正为 16F/141P（或补注控制测试口径）。

### F-3（P2）申报口径偏差：manifest 881 canonical → 实测 882（PASS）
- **证据**：`verify_workflow.py check-manifest-consistency` = `Canonical files: 882 / Actual files: 1018 / [PASS]`。
- **影响**：检查本身 PASS；数字差 1（可能为并行面文件入账时点差或计数快照差）。**建议**：EVD 勘正。

### F-4（P2）全量套件 7F vs 申报 6F——第 7 项为并行面引入，申报未提
- **证据**：全量 infra 套件 = 7F/4099P（6×test_archguard_ratchet + 1×test_loop_runtime_claims::test_real_repository_inventory_complete_and_within_budget）。isolate 两步实验：pure HEAD → archguard 同 6F 复现、**inventory 测试 PASS**；HEAD+仅 FIX-385 两文件 overlay → archguard 仍恰 6F（零新增）、**inventory PASS** → 第 7 项由在途并行面（FEAT-044/045 的 loop_engine/loop_telemetry 未提交增量）引入，非 FIX-385、非 HEAD 存量。
- **影响**：FIX-385 本身零新增失败（审查结论不受影响）；但 6F 存量声明未覆盖第 7 项，Coordinator 需将 inventory 失败路由给并行面责任人（FEAT-044/045 收尾时随其 ratchet/预算一并处理）。**建议**：本报告转达 Coordinator 入账。

### F-5（P3）resume 路径 journal payload 信任面
- **位置**：L1828-1829（`doc["batch_size"]`/`doc["batches_total"]`）、L1864（`doc['commit']['archive_file']`）、L1951。schema 门（L1607-1621）只验 `schema` 字段。
- **事实**：被篡改但 schema 合法的 journal 缺上述键 → 裸 KeyError/TypeError 拒绝（仍 fail-closed、零腐化），但违背「loud, structured refusal」自述。另一角：hot_leg_done + 游标被篡改缩小 → 以 `line=None` 行覆写完好 batch 工件后才 TypeError（L1924-1925、L1941-1943）——仅篡改可达（crash 一致态游标必 ==total：批写与游标写逐对原子推进），archive 文件已持行、无数据丢失。
- **建议**：resume 入口对 `batch_size`/`batches_total`/`commit.archive_file` 做类型校验并入 schema 门；hot_leg_done 路径跳过 re-stage（游标 <total 时直接 `migration_cursor_ahead_of_artifacts` 同型拒绝）。

### F-6（P3）字节级行尾不对称 + 「byte-identical」注释过度声明
- **位置**：L112-114 注释；one-shot `_write_archive_file`（L727-733，text mode → Windows 写 CRLF）vs resumable `_atomic_write_text`（L1505-1532，LF bytes）。
- **事实**：真实 host `.governance/evidence-log.md` 实测全 CRLF（2675/0，1,715,381 bytes）→ resumable 热重写将整文件翻转为 LF。功能无感：全部消费者 read_text 通用换行 + git autocrlf 归一化（终态等价测试经 read_text 比较——已实测相等）。但注释「compose byte-identical archive files」在 Windows 字节级为假。**建议**：注释改为「newline-normalized equivalent」，或报告中披露（本条即披露）。

### F-7（P3）`migrate_evidence_resumable` ≈365 行
- **位置**：L1681-2045。超出 50 行指引；相位分段注释内聚、世界判定集中一处反利于崩溃语义审计——**仅记录，不要求拆分**。

### F-8（P3）peer-import 单 try 耦合 + fallback 耐久性缺口
- **位置**：L122-126。`decision_repository` 导入失败会连带把 `_TargetLock`/`_atomic_write_bytes` 一并降级；fallback 缺 dir-fsync（对照 governance_store L452）；`_big_table_target_lock` 无锁降级的残余 TOCTOU 见 ②⑤。降级路径无测试覆盖（pragma no cover）。**建议**：按 import 拆分 try；fallback 补 dir-fsync；补一条 monkeypatch `_TargetLock=None` 的降级行为测试。

### F-9（P3）rollback 与 `.migration` 状态目录无清理接线
- **位置**：`_rollback_evidence_archive` L3446-3463 / `rollback_last_migration` L3466-3526（只删 archive 文件+回插行）。
- **事实**：resumable 迁移回滚后，finalized journal 与热表既非 post-image 亦非 pinned input → 同 range 重迁必然 `migration_state_conflict`（响亮、设计如此），但需手动删状态目录。**建议**：rollback 检测同 range journal 并清理，或输出中提示删除命令。

### F-10（P3）lock 争用异常未映射为 BigTableMigrationError
- **位置**：`_TargetLock.__enter__` 争用超时 → governance_store `_refuse` → `StoreError`（governance_store L100-108 附近）；archive.py CLI migrate-big-table 仅捕 `BigTableMigrationError`（L4394-4400）→ 争用时裸 traceback（仍非零退出）。**建议**：`_big_table_target_lock` 内转译 `StoreError(payload)` → `BigTableMigrationError`。

## 6. 验证复现记录（命令与原始输出摘要）

```text
[RED]  %TEMP%/fix385_red = worktree infra 副本 + git show HEAD:…archive.py（0 处 resumable 引用核实）
       python -m pytest …/tests/test_archive.py -q --tb=no → 16 failed, 141 passed in 44.75s
[GREEN]python -m pytest skills/…/infra/tests/test_archive.py -q → 157 passed in 1.90s
[FULL] python -m pytest skills/…/infra/tests -q --tb=no → 7 failed, 4099 passed, 1 skipped,
       517 subtests passed in 1399.28s（6×archguard + 1×loop_runtime_claims，归因见 F-4）
[ISO-1] git worktree add %TEMP%/fix385_wt HEAD --detach（d7b9add）
       pytest test_archguard_ratchet.py → 6 failed, 32 passed（同 6 项，存量成立）
       pytest test_loop_runtime_claims::…inventory → 1 passed（非存量）
[ISO-2] overlay 仅 FIX-385 两文件后重跑 → 6 failed, 33 passed（archguard 零新增 + inventory PASS）
       git worktree remove --force（已清理，git worktree list 核实）
[HOST] archive.py verify → Pass: True（1131 tasks / 1276 index entries，只读）
       archive.py migrate-big-table evidence 0.86.0 0.88.0 --dry-run → Dry-run: True /
       Migrated rows: 29 / Batches: 1 / Resumed: False / Decision authority state: MD_ACTIVE
       事后核实 .governance/archive/ 无 .migration 目录（零残留）
[PURI] %TEMP%/fix385_purity/driver.py：old(HEAD) vs new 逐字段对照
       count=7 == 7；explain / hot_lines / archive_lines / archive_file 全 SAME
[GOV]  verify_workflow.py verify → PASSED；check-manifest-consistency → PASS（canonical 882）；
       check-cross-references → PASS ×3
```

## 7. 遗留项与处置建议（供 Coordinator）

1. **F-1（P1）**：建议 Developer 本工作树窗口内修复（in-lock 复核，≈5 行，有 P0-F1 先例形态）→ R1 复审逐条比对。若决定遗留：MUST 转入 cutover 票义务清单并记 risk/decision 入账。
2. **F-2/F-3（P2）**：EVD 申报数字勘正（16F/141P；manifest 882）——与 FEAT-063 R0 报告同口径处理。
3. **F-4（P2）**：inventory 失败路由至 FEAT-044/045 并行面（非本票义务）；本票 6F 存量归因经 isolate 复核成立。
4. **F-5~F-10（P3）**：不阻塞合并；F-5/F-8/F-10 建议随下一个 archive 域切片吸收，F-6/F-9 建议在 cutover 票或文档面吸收，F-7 仅记录。

---
*审查者声明：本报告全部结论基于本会话机跑命令输出与逐行读码事实；未验证项已如实标注；未修改任何产品代码；真实 .governance/ 全程只读且零残留。*
