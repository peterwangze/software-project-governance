# REVIEW-FIX-395-CODE-R0 — 后置代码审查报告（Check 28c HotFactSource 终态判定对齐）

> **Round**: R0（首轮） · **前轮引用**: 无（首轮）
> **Task**: FIX-395（P1 · 0.89.0 串行链第三位；FIX-390/def9508、FIX-392/65c8e4b 已集成）
> **审查对象**: staged diff `git diff --cached`（+452/−3）：`skills/software-project-governance/infra/verify_workflow.py`（+42/−3）+ `skills/software-project-governance/infra/tests/test_fix395_hot_fact_source_writer_terminal.py`（新增 410 行 8 测试）
> **审查基线**: HEAD = 65c8e4b · 仓库根 = D:\AI\agent\claude\coding\project_management_workflow · 审查日期 = 2026-09-26
> **规范绑定**: agents/code-reviewer.md + skills/code-review/SKILL.md（P0-P3 分级 · 五维度 · AI 五项 · 事实依据红线）

## 结论

**NEEDS_CHANGE**（P0 = 1，BLOCKING；P1 = 1；P3 = 3）

**unresolved_blockers = 1**（P0-1：staged diff 打破既有 static-version-pin 契约测试）

产品逻辑本体（28c 终态判定消费 FIX-393 判据 by identity、三判定点换用、S_old 字节不变、映射语义文档化）经独立核验**全部属实且正确**；FAIL 面 A/B（恰 −20 FAIL +1 OK）亲验坐实。阻塞点仅为一处可机械修复的回归：新测试文件 23 处字面版本未按 DEC-213③/FIX-352/353 契约登记豁免或改为 derive，打破既有契约测试。修复后按 M7.4 由本 Reviewer 以 R1 复审（须引用本报告路径并逐条比对 findings）。

---

## 一、逐行 diff 审查（维度：正确性 · 设计一致性）

### 1.1 identity 复用真实性 — ✅ 属实

- `_hot_status_cell_is_delivered`（verify_workflow.py:1663-1684，紧邻 `_status_cell_is_delivered`:1659-1660）的 writer 分支为 `_status_is_writer_committed_cell(_status_clean_cell(status))` —— **调用** FIX-393 判据，非复制文本（diff 逐行核对）。
- `_WRITER_STATE_MARKER_CHAIN = task_row_update._STATE_MARKER_CHAIN`（verify_workflow.py:10623，模块级绑定 + :92 `import task_row_update`）——writer 链对象按 identity 消费，非第四镜像。同族既有 sync-guard（test_fix393:141 `assertIs`）继续覆盖。
- `_status_clean_cell`（:10500-10502，剥 markdown/backtick/`**` 装饰）前处理与 FIX-393 既有消费点 `_status_is_completed_cell`（:10667）口径一致——先 clean 后判定，正确。
- `_status_is_writer_committed_cell`（:10627-10640）语义核验：无锚即 False（:10635，B-1 手写 committed 不猜）；链 first-hit 必须 `committed`（:10637-10639，anchored dev/triaged 不误判终态）；链无命中 False（未知不猜）。与 `_STATE_MARKER_CHAIN`（task_row_update.py:287-295）first-hit 顺序语义一致。

### 1.2 三判定点换用完备性 — ✅ 属实（无第四处遗漏）

`_status_cell_is_delivered` 换用后全仓剩余调用点逐一归属：

| 行 | 所属面 | 行类型 | 28c 任务终态？ |
|---|---|---|---|
| :1682 | `_hot_status_cell_is_delivered` legacy 分支自身 | — | 设计如此（S_old 基座） |
| :1953 | `_hot_task_is_delivered` → 28c（调用点 2202/2217/2237） | 任务 | ✅ 已换用 |
| :1960 | `_hot_task_is_open` → 28c（调用点 2238） | 任务 | ✅ 已换用 |
| :2007 | `_hot_task_ids_for_version` release_delivered → 28c（调用点 2153） | REL 行 | ✅ 已换用 |
| :1691 | `_task_id_has_open_status` → FIX-069 release-readiness 面（:1885/1886，FIX-071/074） | 任务 | ❌ 非 28c（范围外，见 P3-2） |
| :1873/1883/1884 | FIX-069 面（REQ-059/061/064） | 需求 | ❌ 非 28c |
| :2239/2241 | **28c 主体内** REQ-070~074 需求矩阵 | 需求 | ❌ 需求终态非任务终态（潜在耦合，见 P3-1） |

`_snapshot_fact_source_issues`（:2044-2077）逐行核读：仅 snapshot 版本/日期/发布串比对，**零任务终态判定，零改动** —— 申报属实。

### 1.3 S_old 字节不变 — ✅ 属实

- `_status_cell_is_delivered` 函数体（:1659-1660）在 diff 中为纯上下文行，未动一字节；新函数为纯追加（hunk @@ -1660,6 +1660,30 @@）。
- legacy 分支行为对照：既有 28c 测试族亲跑 `HotFactSourceConsistencyTests`（test_verify_workflow.py:1592 起）+ `test_snapshot_freshness.py` 全绿（见 §四），含 `test_hot_fact_source_rejects_requirement_delivered_while_task_open` 等 legacy 判定方向用例——S_old 方向零回归。
- `S_new ⊇ S_old` 结构保证：`if legacy: True` 后才落 writer 分支；专项 pin `test_legacy_delivered_semantics_superset_invariant` 覆盖三种 legacy 形态。

### 1.4 守护方向保持 — ✅ 属实

- dev/triaged anchored（每个 writer 写都带锚，first-hit≠committed）→ 不判终态：`test_active_dev_and_triaged_cells_stay_open_and_demanded` 亲跑通过（活体 REL-090/091 形态 🆕 已 triage…〔op-…〕→ 链命中 `triaged` → open）。
- 手写 committed 无锚（B-1）→ 不判终态且 released-claim 保护保持：`test_anchorless_hand_committed_release_row_never_lifts_face` 亲跑通过。
- 未知 token → 不猜：`test_unknown_token_cell_never_terminal` 亲跑通过。

### 1.5 版本行映射语义（deliverable ③）— ✅ 文档化属实 + pin 测试真实

- docstring（:1980-1989）准确描述 FIX-339 any-cell recall 既有语义未改；enumeration 仅在 `not released_face` 时运行（:2176-2181 亲读核验）。
- pin 测试构造活体形态真实：REL-091 行（plan-tracker.md:83）实存 `0.88.0→0.89.0` bump-source 叙事 + triaged 锚 `op-fb75a729…`，与夹具 `ST_TRIAGED_ANCHORED` 逐字同形。**活体 A/B 本身构成该语义的实证**：前侧 census 实测 `0.88.0 roadmap row missing active task REL-091` FAIL，后侧随 released_face 抬起而消失。
- 5 个活体锚全部实存核验：REL-087（plan-tracker:118）/REL-088（:119）/REL-089（:120）/REL-091（:82,83,84）/FIX-382（:106）。

---

## 二、五维度逐项结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | **PASS（产品逻辑）** | §一 全项；20 条伪 FAIL 簇消解亲验（前侧恰 20 → 后侧 0）；守护方向用例全绿。注：P0-1 为测试契约回归，非产品判定逻辑错误 |
| 安全性 | **PASS** | 无外部输入面；regex 均转义/锚定（`re.escape` :1992）；无密钥/注入面；测试全部 `tempfile.TemporaryDirectory`，真实 `.governance` 零触碰（test 文件 :44 自述 + 亲读核验） |
| 可维护性 | **PASS（产品代码）／FAIL（新测试文件 → P0-1）** | 产品侧：函数紧邻同族、docstring 完整、identity 复用。测试侧：23 处字面版本违反 FIX-352/353 dynamization 契约（DEC-213③ 明文要求 derive 或登记豁免） |
| 性能 | **PASS** | 每状态 cell 增一次 ≤7 模式链扫描（first-hit 即出）；census 运行时长同级（~2min 量级，实测两轮无劣化信号） |
| 测试覆盖 | **PASS（新增面）／FAIL（既有契约面 → P0-1）** | 8 新测试覆盖 released-face 抬起/识别 recall/守护方向/S_new⊇S_old/映射 pin；但 staged 态全量套件 8F 中 1F 为本 diff 新引入（既有契约测试转红，申报定向口径未覆盖） |

## 三、AI 代码专项五项

| # | 检查项 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock 残留 | 无 | 测试直接调 `vw.*` 真函数 + 临时目录，无 mock/patch（亲读 410 行全文） |
| 2 | 硬编码返回值 | 无 | diff 无常量返回捷径；判定全走真实解析 |
| 3 | 幻觉 API 调用 | 无 | 所引符号 `_status_is_writer_committed_cell`/`_status_clean_cell`/`_hot_task_is_*`/`_hot_task_ids_for_version`/`check_hot_fact_source_consistency` 均实存（grep 逐一核验） |
| 4 | 未实现 TODO | 无 | diff 无 TODO/FIXME 残留 |
| 5 | 过度实现 | 无 | 改动最小面：1 新函数 + 3 调用点换用 + docstring；`_snapshot_fact_source_issues` 零改动申报属实；无范围蔓生 |

---

## 四、硬门槛亲跑摘要（全部 Coordinator/Reviewer 本机实测）

| # | 门槛项 | 命令 | 结果 |
|---|---|---|---|
| 1 | 新套件 | `python -m pytest …/test_fix395_hot_fact_source_writer_terminal.py -v` | **8 passed** (0.36s) ✓ 申报「绿 8/8」属实 |
| 2 | check-hot-fact-source 后侧（staged） | `verify_workflow.py check-hot-fact-source` | **PASSED — 0 issues** ✓ |
| 3 | check-hot-fact-source 前侧（stash HEAD 主树） | 同上 | **FAILED — 20 issue(s)**：2 overstate + 18 missing（REL-087/088/089/FIX-382/385 writer-committed 5 + legacy ✅ 12（FIX-373/374/376/377/378/379/380/381/386/387/388/389）+ REL-091 recall 1）——与申报 20 条归因逐簇吻合 ✓ |
| 4 | census strict A/B（stash 法，主树同数据） | `check-governance --level strict` 前后各一轮 + Compare-Object | **FAIL 面：恰 −20 `[FAIL] hot fact-source` 行 +1 `[OK]` 行**（52→31 FAIL，另 −1 为 census 汇总行 + 12 行明细块）✓；**WARN 面：+23 static-version-pin WARN +1 INFO 漂移头**（27→50）✗ → P0-1/P1-1；簿记行（files 1050→1051、Candidates 1019→1020、Inventory hash、K-8 75→76 test files）随新增文件固有 |
| 5 | 既有 28c 测试族 | `pytest HotFactSourceConsistencyTests + test_snapshot_freshness.py + fix393 + fix390 + fix394` | **117 passed + 23 subtests** ✓ S_old 零回归 |
| 6 | 全量 infra 套件（staged 主树） | `pytest skills/…/infra/tests -q` | **8 failed / 4192 passed / 1 skipped**（见 §五归因矩阵）|
| 7 | write-guard / manifest / cross-refs | `governance-write-guard` + census Check 11/12 段 | **PASS / PASS / PASS** ✓ 申报属实 |
| 8 | staged 态完整性 | 两次 `stash push --staged`/`pop --index` 进出 + SHA256 对照预备份 | `verify_workflow.py`/`test_fix395…py` 字节恒等 ✓ staged diff 恒 +452/−3 ✓ stash list 空 ✓ |

## 五、全量套件 8F 归因矩阵（stash A/B 三点取证）

| 失败节点 | staged 主树 | HEAD 主树（stash） | HEAD 纯 worktree | 归因 |
|---|---|---|---|---|
| test_static_version_pins::RealTreeContractTests::test_real_tree_scan_is_warn_only_and_clean | **FAIL**（失败内容恰=23 条 fix395 未豁免 pins） | 未单跑（HEAD 扫描域无 fix395 文件，worktree 同域实证 PASS） | **PASS** | **FIX-395 新引入 → P0-1** |
| test_archguard_ratchet::R1MainfileBudgetTests::test_r1_passes_on_current_tree | FAIL | FAIL | FAIL | 既有（非本 diff） |
| test_archguard_ratchet::R7ReproducibilityTests::test_r7_committed_baseline_matches_fresh_regen | FAIL | FAIL | FAIL | 既有 |
| test_archguard_ratchet::CliGateTests::test_cli_green_on_current_tree | FAIL | FAIL | FAIL | 既有 |
| test_loop_runtime_claims::…::test_real_repository_inventory_complete_and_within_budget | FAIL | FAIL | FAIL | 既有 |
| test_verify_workflow::LoopRuntimeClaimAdapterTests::test_claim_command_emits_complete_pass_report | FAIL | FAIL | FAIL | 既有（FIX-390/392 审查已实证基线） |
| test_verify_workflow::FIX300DualCaliberAgreementTests::test_fixture_identity_mode_agrees_with_engine_on_present_sources | FAIL | FAIL | FAIL | 既有（同上三人组） |
| test_verify_workflow::FIX300DualCaliberAgreementTests::test_identity_host_source_drift_reproduces_divergence_shape | FAIL | FAIL | FAIL | 既有（同上） |

申报「定向 970P/3F（3F stash A/B 预先存在）」的三人组与上述既有基线一致、预先存在属实；但该定向口径未覆盖 `test_static_version_pins` 契约测试，致 P0-1 漏检（→ P1-1 申报口径问题）。

---

## 六、发现列表

### P0-1（BLOCKING）新测试文件 23 处未豁免字面版本 pin，打破既有 static-version-pin 契约测试

- **位置**: `skills/software-project-governance/infra/tests/test_fix395_hot_fact_source_writer_terminal.py` 行 88, 102, 104-107, 167, 173-175, 179, 180, 183, 224, 242, 243, 316, 329, 339, 355-357, 394（字面 `"0.88.0"`/含 `0.88.0` 的赋值串，含 :88 `plan_version="0.88.0"` kwarg 默认值与夹具默认场景串）
- **事实**:
  1. `pytest …test_static_version_pins.py::RealTreeContractTests::test_real_tree_scan_is_warn_only_and_clean`：HEAD（worktree 实证）**PASS** → staged 主树 **FAIL**（本审查 1.00s 单测复跑，断言 `[f for f in findings if " pins " in f] == []` 得 23 元素，首条即 `test_fix395…py:88 pins the active version "0.88.0" literally`）。
  2. 测试契约明文（test_static_version_pins.py:334-337）：「Current tree is FIX-352/353-dynamized: every active-version mention is either derived or ledger-exempted — **no unexempted hits may stand**」。
  3. census strict A/B WARN 面 27→50（+23 全部指向本文件），新增 `│  [INFO] 23 non-blocking drift(s):` 段。
- **影响**: 合入即打破既有测试契约（套件转红）；census WARN 面近乎翻倍，污染治理健康信号；`STATIC_PIN_EXEMPTIONS` ratchet 纪律（DEC-213③）被穿破。
- **修复建议**（二选一，机械可修）:
  - (a) 登记 23 行 `(line, token, reason)` 豁免于 `checks/version.py STATIC_PIN_EXEMPTIONS`（先例：test_task_row_update.py / test_verify_workflow.py 等同目录 10 文件）；或
  - (b) 改 derive：`resolve_entry.read_active_version()` / `@@ACTIVE_VERSION@@` token（FIX-352/353 形态）——附带收益：REL-091 bump 后夹具自适配新 active 版本。
  - 修复后 MUST：重跑该契约测试（转绿）+ 重跑 census strict A/B（WARN 面归恒等）+ 通报本 Reviewer R1 复审。

### P1-1（强烈建议本轮修改）申报证据链两处不实/口径缺口

- **位置**: 任务申报文本（FIX-395 开发申报）与对应 evidence 记录。
- **事实**:
  1. 「全量 strict A/B diff 恰=−20 FAIL+1 OK 行**其余面逐条恒等**」——FAIL 面属实，但 WARN 面 +23+1（P0-1 的可见面），非恒等。
  2. 「定向 970P/3F」定向口径未含 `test_static_version_pins` 契约测试，致 P0-1 回归漏检。
- **影响**: 证据可信度受损（P-v1 原则 1：分析基于事实）；Coordinator 依据不完整证据做合并决策。
- **修复建议**: 修复 P0-1 后同步勘正申报/evidence-log 对应行（如实登记「FAIL 面恒等、WARN 面经豁免登记后恒等」）；后续定向套件口径纳入 static-pin 契约测试。

### P3-1（讨论/记录）28c 需求行 legacy 读与 FIX-395 抬面存在潜在耦合

- **位置**: verify_workflow.py:2239/2241（`_status_cell_is_delivered(req_status)`，REQ-070~074 需求矩阵行）。
- **事实**: FIX-395 使 writer-committed 任务行计入 `all_tasks_delivered`；若未来某 REQ-07x 行被写成 writer 形态（无 ✅ 字面），:2239 将新触发 `requirement matrix … is not delivered while … complete` FAIL。活体 REQ-070~074（plan-tracker.md:439-443）全为 `✅ 已交付`，当前不可触发（census A/B 无新 FAIL 佐证）。
- **建议**: 留档为同族第五消费方候选票（REQ 需求终态判定是否对齐 FIX-393 判据），不阻塞本票。

### P3-2（讨论/记录）FIX-069 release-readiness 面仍为 legacy 读（范围外同族候选）

- **位置**: verify_workflow.py:1691（`_task_id_has_open_status`，FIX-071/074）与 :1873/1883/1884（REQ-059/061/064）。
- **事实**: 若 0.29-era 行未来被 writer 形态改写将现同类伪 FAIL；活体均为 legacy ✅ 形态，当前无伪 FAIL。属 28c 范围外，申报「未动」属实。
- **建议**: 同 P3-1 留档候选票。

### P3-3（讨论，可不改）夹具 prose 保真度

- **位置**: test 文件 :73-76 `ST_WRITER_COMMITTED_TRAILING_GROUP`。
- **事实**: 使用 REL-088 真实锚 `op-1e4093d7…` 但 prose 为历史阶段形态（「已 lock 待派发…R0 NEEDS_CHANGE/2→R1 …commit 61618a5」），非当前活体单元格文本（「committed (2026-09-25——并行派发〔docs/release 文件族独立〕）」）；文件头 :43 已声明「judgment keys on the shapes, not the prose」，shape（committed+锚+尾部叙事组）一致。
- **建议**: 无需修改；如做 (b) derive 改造可顺带对齐。

---

## 七、边缘 3 项定级（任务指定）

| 边缘 | 申报 | 定级 | 依据 |
|---|---|---|---|
| ① 三判定点换用完备性（无第四处 28c 任务终态遗漏） | 三处换用 + snapshot 面零改动 | **属实 — PASS** | §1.2 调用点全归属表 |
| ② Check 18 族未动且无同族伪 FAIL | `_hot_status_completion_state` 未动 | **属实 — PASS** | 该函数（:12432-12449）零 diff 行，且 committed 分支已按 identity 消费 FIX-393 判据（:12445），无同类伪 FAIL 残留 |
| ③ A/B 恒等性 | −20 FAIL+1 OK 其余恒等 | **部分属实 — FAIL 面成立，WARN 面不恒等** | §四#4 / P0-1 / P1-1 |

## 八、硬门槛裁决

| 门槛 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **1**（P0-1） | ✗ 不通过 |
| 5 维度全覆盖 | 100% | §二 五维逐一有结论 | ✓ |
| 每条发现标注级别 | 100% | P0×1 / P1×1 / P3×3 | ✓ |
| 设计一致性（ADR/契约比对） | 已完成 | FIX-393 identity 权威 ✓；DEC-213③/FIX-352/353 违反（P0-1）；FIX-339 语义文档化未改 ✓ | ✓（含违例发现） |
| AI 专项 5 项 | 全部完成 | §三 | ✓ |

**终局结论：NEEDS_CHANGE** — P0-1 修复（豁免登记或 derive + 勘正申报）后由本 Reviewer 执行 R1 复审：逐条比对 P0-1/P1-1/P3-1~3（已修复/未修复/新引入），重跑 static-pin 契约测试 + census strict A/B WARN 面 + check-hot-fact-source + 新套件。

---

## 附：审查操作留痕

- staging 完整性：全程未改产品代码/staged/.governance；两次受控 `git stash push --staged` ↔ `pop --index` 进出，恢复后 SHA256 与预备份逐一相同（verify=True / test=True），staged stat 恒 +452/−3，stash list 清空。
- 临时 worktree `$TEMP\fix395-ab-head`（65c8e4b + 活体 .governance 只读拷贝）：A/B 取证毕已按任务要求清理。
- census 原始输出留存：`%TEMP%\fix395_census_before2.txt`（HEAD 基线）/ `%TEMP%\fix395_census_after.txt`（staged）/ `%TEMP%\fix395_hot_before2.txt` / `%TEMP%\fix395_hot_before.txt`。
