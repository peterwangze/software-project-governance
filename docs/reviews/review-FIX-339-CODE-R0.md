结论：NEEDS_CHANGE ｜ round=0 ｜ unresolved_blockers=1 ｜ 机录 round 建议 = REVIEW-FIX-339-R1

# FIX-339 代码审查 R0 —— `check_hot_fact_source_consistency` 版本锚参数化（DEC-195 方案 (a) 真修）

- 审查对象：工作树未提交改动（基线 = HEAD `dfafa9591a62f55ad784e72079c623b2c05079cb`）
- 审查者：Code Reviewer Agent（只读审查；唯一写入 = 本报告）
- 审查方式：逐行 diff + 全部四项验收独立复现 + HEAD pristine 引擎双向对照 + 自构反相实验 E1–E4（全部在 `%TEMP%\fix339-review-r0` 副本上执行，未触碰真实 `.governance/`）

---

## 1. 改动清单核验

| 文件 | diff 概况 | 核验结论 |
|---|---|---|
| `skills/software-project-governance/infra/verify_workflow.py` | 24412→24411 行（净 −1）；3 个 hunk 全部落在常量区（L1855-1864）、`_hot_task_ids_for_version` 新 helper（L1899-1917）、`check_hot_fact_source_consistency` 主体（L2054-2132） | ✅ 与声明一致；`FIX_087_ACTIVE_VERSION`/`FIX_087_PREVIOUS_VERSION`/`FIX_087_ACTIVE_TASKS`/`FIX_087_ACTIVE_FIXES` 4 常量删除且全仓主引擎零残留（grep 证实，仅剩 docs 历史文档与 e2e 投影副本）；`FIX_087_READINESS_VERSION`/`FIX_087_REQ_TASKS` 保留 |
| `skills/.../tests/test_verify_workflow.py` | +150 行：`_plan_content` 默认 `plan_version=None→"0.38.0"`、0.42.0 正面 snapshot 测试补 4 个语义参数、`_derived_plan_content` helper + 4 个新测试 | ✅ 旧测试适配不改断言意图（0.42.0 测试补的是面切换语义一致数据）；新测试覆盖 正面派生/虚报负例/缺 roadmap 行/snapshot-latest 四面 |
| `skills/.../core/architecture-baseline.json` | 2 字段：`generated.git_head` 5e6d8c7→dfafa95、`r1_mainfile_budget.anchor_loc` 24412→24411 | ✅ 均为 `--regen` 机械产物；披露精确化：除 R1 锚收缩外 `git_head` 同批刷新（regen 语义的一部分，R7 `committed==fresh` 依赖之），非独立语义变更 |

范围纪律：无顺带改动 ✅（diff 全文逐 hunk 复核，3 hunk 无一越出 hot-fact 函数族）。

## 2. 逐维度裁决

| 维度 | 裁决 | 依据（含独立复现） |
|---|---|---|
| 正确性 | **有保留**（F-01 P1） | 主派生链正确且 fail-closed：锚缺失/不可解析 → 恰 1 条 FAIL 不崩溃不误报（E2 实证）。**但 REL 行识别为精确相等匹配（L1910 `normalized[4] != version` 即跳过），真实数据 REL-077 行（`.governance/plan-tracker.md` L88）目标版本列错位为日期 `2026-09-14` → helper 静默漏识别 → 当前 0.81.0 的 PASS 实际走「无 REL 行 → roadmap 自称已发布」退化路径，而非声明所述「按该版 REL 交付态切换」主路径。E3 证明该形态下虚报完全逃逸（见 §4）** |
| 安全性 | PASS | 无注入面（只读本地治理文件）；`re.escape(active_version)` 正确转义；overstate 正则沿用 `[^。\n|]*` 边界与旧版等价 |
| 回归风险 | PASS | 假阳 9→0 双向实证（工作树 PASSED；HEAD pristine 引擎对同一真实 plan-tracker 报恰好 9 条、全部 0.38.x）；R1-R7 全绿；819 用例 3 红身份与 HEAD pristine 逐一一致；check-release 的 FAIL 面（execution gates / loop runtime claim gate）均为与本次 3 文件无关的既有面——loop claim gate 扫描对象（`docs/reviews/review-FIX-300-CODE-R0.md` 等）与扫描器代码均不在 diff 内；unit tests 子进程 FAIL 为 180s 环境超时（本人全量实测 248.7s，同一超时） |
| 测试质量 | PASS（附 F-01 关联要求） | 定向 `HotFactSourceConsistencyTests`：`Ran 16 tests ... OK`（复现）；全量 `Ran 819 tests ... FAILED (failures=1, errors=2)`，3 红身份 FIX300DualCaliber×2 + LoopRuntimeClaimAdapter×1，且 HEAD pristine（head-infra 临时结构 + HEAD test 文件）复跑同样 3 方法红 → 既有基线声明成立。新测试无 mock 污染、无自证断言（fixture 语义自洽、断言的是引擎输出）。**缺口：未覆盖「REL 行存在但目标版本 cell 错位」变体（F-01 的回归测试要求）** |
| 可维护性 | PASS（附 P3 备注） | helper 13 行职责单一；`FIX_087_` 前缀常量名沿用为既有债务；双正则并存见 F-03 |

## 3. AI 专项 5 项检查

| # | 检查项 | 结论 |
|---|---|---|
| 1 | mock 残留 | 无 —— 新测试全部 tempfile + 真函数调用 |
| 2 | 硬编码返回值 | 无 —— 面判定/任务清单均为数据派生 |
| 3 | 幻觉 API | 无 —— 全部引用符号（`_markdown_table_cells`/`_normalize_markdown_cell`/`_status_cell_is_delivered`/`_version_row_text`/`_contains_fix_token_or_range`/`_hot_task_is_delivered`/`_hot_task_is_open`/`_extract_task_ids`/`FIX_105_SNAPSHOT_RELEASE_VERSION_RE` 等）逐一读实现核实存在且签名匹配 |
| 4 | 未实现 TODO | 无 |
| 5 | 过度实现 | 无 —— 改动聚焦单函数族；唯一超出声明字面的行为差异为 F-04 放宽（记录在案） |

## 4. 独立复现原始输出（关键行）

### 4.1 验收 1 —— check-hot-fact-source 单跑
```
[OK] hot fact-source consistency synchronized
=== Hot Fact-Source Consistency Check ===
  Result: PASSED — hot fact-source sections are synchronized
EXIT=0
```
HEAD pristine 引擎对同一真实 plan-tracker（tmp 加载 + HOST/PLUGIN_ROOT patch 至真实仓库）：
```
[FAIL] ...: 0.38.0 roadmap row must remain 进行中 before REL-013 release
[FAIL] ...: hot sections overstate 0.38.0 as released before REL-013
[FAIL] ...: active 0.38.0 task table missing FIX-082 / FIX-083 / FIX-084 / FIX-085 / FIX-086 / FIX-087 / REL-013
HEAD-pristine issue count: 9   | 0.38.x-related: 9
```
→ 「改前 9 条 0.38.x 假阳」精确证实，红→绿双向成立。

### 4.2 验收 2 —— check-release 0.81.0 candidate
```
  Version: 0.81.0 / Lineage mode: candidate
  [PASS] version consistency | [PASS] release fact source | [PASS] hot fact source
  [PASS] e2e check (exit=0)   （e2e 投影副本过渡态无害实证）
  [FAIL] execution gates      → governance health exit=1（70 issues）；unit tests 超时 180s
  [FAIL] loop runtime claim gate → 8 issues，全部指向 docs/reviews/review-FIX-300-CODE-R0.md 等
                                   未修改文档（AUTHORITY/AMBIGUOUS/UNSUPPORTED 断言）
EXIT=1
```
→ 声明「hot fact source 面 PASS、无新增 FAIL」成立：hot fact 面 PASS ✅；FAIL 面逐项归属为与 3 文件无关的既有基线（扫描对象与扫描器代码均不在 diff；unit tests 超时同因环境性能，本审查全量实测 248.7s）。

### 4.3 验收 3 —— archguard-ratchet
```
[R1] PASS  mainfile loc 24411 ≤ anchor 24411 (only-down)
[R2] PASS  47 ≤ 47 | [R3] PASS | [R4] PASS 1299 ≤ 1299 | [R5] PASS 84/84 + 71/71
[R6] INFO  cold import 196 (Δ0)
[R7] PASS  regen deterministic=True; committed==fresh True
Result: PASS (0 violations) EXIT=0
```
→ R1 锚收缩生效且与工作树行数精确一致；R7 证实 baseline JSON 与主文件一致。

### 4.4 验收 4 —— unittest
```
定向：Ran 16 tests in 0.059s  OK
全量：Ran 819 tests in 248.722s  FAILED (failures=1, errors=2)
  ERROR: ...FIX300DualCaliberAgreementTests.test_fixture_identity_mode_agrees_with_engine_on_present_sources
  FAIL:  ...FIX300DualCaliberAgreementTests.test_identity_host_source_drift_reproduces_divergence_shape
  ERROR: ...LoopRuntimeClaimAdapterTests.test_claim_command_emits_complete_pass_report
HEAD pristine 对照（head-infra + HEAD test 文件，仅跑 3 方法）：
  HEAD-pristine: run=3 failures=2 errors=1（同 3 方法红，身份逐一一致）
```
→ 819/3 红身份/既有基线三项声明全部独立成立。

### 4.5 反相实验（%TEMP% 副本，`inversion_experiments.py`）
- **E1（复现 Developer 场景：锚 0.82.0 + 未发布行虚写已发布）**：hot 面 **恰 4 条 FAIL** ✅
  ```
  0.82.0 roadmap row must not claim 已发布 before its release task is delivered   ← 保护断言 ①
  hot sections overstate 0.82.0 as released before its release task is delivered  ← 保护断言 ②
  0.82.0 roadmap row missing active task FIX-341                                  ← 交叉同步（实证：roadmap 0.82.0 行确无 FIX-341 token；
  project overview missing active version 0.82.0                                     精确匹配 0.82.0 的任务行 = REL-078/FIX-341）
  （另 snapshot 面 2 条联动：0.82.0 newer than snapshot——真实联动行为，非 hot 面）
  ```
- **E2（锚不可解析 fail-closed）**：恰 1 条 `project config missing 工作流版本 (cannot derive active version anchor)`，无崩溃无其他误报 ✅
- **E3（自构缺口探针：E1 + REL-078 目标版本列模拟 REL-077 式错位→日期）**：hot 面 4→**1**，`must not claim 已发布`/`missing active task FIX-341`/`overstate` **全部消失** → **未发布虚报完全逃逸**（F-01 直接证据）
- **E4（0.81.0 锚下删 REL-077 行）**：0 FAIL —— 「已发布面归档容忍」确认（有意设计的退化路径本身工作正常）

### 4.6 已知边界披露核实
- e2e 投影副本（`project/e2e-test-project/.../verify_workflow.py`）确仍含 0.38.0 常量（L1475-1476 等）；check-release `[PASS] e2e check (exit=0)` 实证过渡态无害 → 披露如实 ✅
- `docs/requirements/data-inventory-0.80.0.md` L237-238 为带版本标注的历史时点文档 → 披露如实 ✅
- 真实 plan-tracker 版本行为 `- **工作流版本: 0.81.0`（无闭合 `**`）→ 新宽松正则（L2054）为匹配真实格式所**必需**，非冗余（严格版 `FIX_105_PLAN_WORKFLOW_VERSION_RE` 对该行解析为空，属既有 snapshot face 格局）→ 见 F-03

## 5. Findings

| ID | 级别 | 位置 | 问题 | 事实依据 | 修复建议 |
|---|---|---|---|---|---|
| **F-01** | **P1（blocking）** | `verify_workflow.py` L1910（`_hot_task_ids_for_version` 精确相等匹配）；真实数据 `.governance/plan-tracker.md` L88 | REL 行目标版本 cell 错位/多义时 helper **fail-open**：静默当作「无 REL 行」，`released_face` 回退为 roadmap 自称 → **未发布虚报「已发布」的三条保护断言全部失效**。当前 0.81.0 的 PASS 实际走退化路径而非声明的 REL 交付态主路径（实现与声明「面按该版 REL 任务交付态切换」存在真实偏差） | L88 原文：REL-077 行 7 cell 中第 5 cell = `2026-09-14`（日期占位目标版本列）；E3 实验：同虚报场景 4→1 FAIL 逃逸；0.38.0 时代曾发生同型数据录入（非假想风险）。任务验收标准明列「REL 行多义」为正确性审查点 | REL 行识别放宽：目标版本 cell 非精确匹配时回退「行内任意 cell 含该版本 token / 前缀匹配（`0.82.0 或后续`形态）/ 行 ID+状态联合判定」；并对「`release_declared=False` 且 roadmap 行自称已发布」的组合降级为显式 FAIL（防退化路径吞掉虚报）。补 E3 型反例回归测试 |
| F-02 | P2 | L2127-2128 | REQ 矩阵交付态交叉检查传 `version=active_version`：REQ-070~074 关联的 0.38.0 任务行被版本过滤排除 → `all_tasks_delivered`/`any_task_open` 恒 False → 交付态交叉断言静默空转（missing REQ 行 / must reference 结构断言仍生效）。旧代码在当前数据上同样空转且伴 9 条假阳——非回归，但「真修」应消除 | 精确匹配勘察：0.81.0 锚下 `version_task_ids` 无任何 0.38.0 行；`_task_statuses_for_hot_source` 的 `normalized[4] != version` 过滤 | 改传 `version=None`（按任务行自身版本查交付态）或派生各任务自身目标版本 |
| F-03 | P3 | L1867 vs L2054 | 同一「工作流版本」字段存在两个格式假设不同步的正则（snapshot face 严格 / hot face 宽松）；真实数据格式只有宽松版能匹配 | L11 原文 `- **工作流版本: 0.81.0（**已发布...`；两正则源码 | 后续收敛为单一事实源（宽松版统一，或数据格式归一后统一严格版） |
| F-04 | P3 | 旧 L1864-1865 删除 | 进行中面不再断言 roadmap 行必须含「进行中」字样（仅保留「不得虚写已发布」）——写「规划中/待启动」不再报。与锚参数化目标一致、无虚报风险，但属超出声明字面的有意放宽 | diff 对照 | 在 CHANGELOG/披露中明示该放宽 |
| F-05 | P3 | L1910 | `0.82.0 或后续` 语义目标版本行（FIX-337/FIX-339）被精确匹配排除，进行中面交叉覆盖不覆盖「或后续」行——保守方向（少报不误报），与 F-01 同根 | 勘察：normalized[4]=`'0.82.0 或后续'` 两行 | 可随 F-01 一并处理（前缀匹配语义） |

## 6. 硬门槛裁决

| 门槛 | 结果 |
|---|---|
| P0 阻塞数 | **0** |
| P1 关键数 | **1**（F-01）→ unresolved_blockers = 1 |
| 5 维度覆盖 | 100%（§2） |
| 每条发现标注级别 | 100%（§5） |
| 设计一致性 | 与 DEC-195 方案 (a) 意图一致；与声明「面按 REL 交付态切换」在真实数据上存在 F-01 偏差 |
| AI 专项 5 项 | 全部完成（§3） |

## 7. 结论

**NEEDS_CHANGE（round=0，unresolved_blockers=1）**。

F-01 是本审查在全部四项验收独立复现均成立、Developer 反相场景精确复现（E1=4 FAIL）之外，通过自构 E3 探针发现的唯一阻塞项：它不推翻「假阳清零 + 既有保护面在标准形态下仍 FAIL」的成果，但证实了版本锚参数化后「未发布虚报已发布」的防护在一种**真实已发生**的数据形态（REL 行目标版本列错位，0.81.0 的 REL-077 行即为例证）下完全不设防，且当前真实数据上声明的主路径从未生效（靠退化路径通过）。修复面小（helper 识别放宽 + 显式 fail-closed + 1 个回归测试），建议本轮完成修复后进 R1 复审。

修复后 R1 复审重点：① F-01 修复后 E3 型场景虚报必 FAIL；② REL-077 错位行被正确识别后 0.81.0 主路径（release_delivered=True）生效且真实数据仍 PASS；③ 819 用例红基线身份不变；④ R1-R7 仍全绿。
