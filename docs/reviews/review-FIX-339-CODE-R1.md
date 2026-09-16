结论：NEEDS_CHANGE ｜ round=1 ｜ unresolved_blockers=1 ｜ 机录 round 建议 = REVIEW-FIX-339-R2

# FIX-339 代码审查 R1 —— 复审（REVIEW-FIX-339-CODE-R0 退回修复核验）

- **round=1 声明**：本审查为 R1 复审；前轮报告全文重读并逐条比对——`docs/reviews/review-FIX-339-CODE-R0.md`（结论 NEEDS_CHANGE / unresolved_blockers=1；F-01 P1 blocking / F-02 P2 / F-03 P3 / F-04 P3 / F-05 P3；§7 列 R1 复审重点四项）。本报告即该前轮同一审查方的修复验证轮。
- 审查对象：工作树未提交改动（基线 = HEAD `dfafa9591a62f55ad784e72079c623b2c05079cb`，与 R0 基线一致；`git rev-parse` 实证）——R0 已审面之上的修复轮增量，`git diff` 覆盖同 3 文件。
- 审查方式：逐行 diff（4 hunk 全读）+ R0 findings 逐条独立复核（不转抄 Developer 声明）+ 自构反相矩阵 C/A/B/D（%TEMP% 真实 plan 副本，未触碰真实 `.governance/`）+ helper 直调 + HEAD-pristine 引擎对照 + 全量/定向/archguard 实跑。
- 环境事实（对后续轮次重要）：① 测试 MUST 从仓库根运行——`HOST_PROJECT_ROOT` 为 cwd 派生（verify_workflow.py L116-132/L14669-14683），从 `infra/` 子目录运行会落入 host 模式、`_hot_fact_source_plugin_scope()` 判 False → 插件域断言休眠，本审查首次定向跑出 14 个假红即为该 harness 陷阱（非产品缺陷），改仓库根后 20/20 绿；② `.governance/` 整体 gitignore（`.gitignore:10`，`git ls-files` 计 0）——数据面 L88 归位只在磁盘可见，不进 diff，与 EVD-1041「plan-tracker 不进 git」一致。

---

## 1. 改动清单核验 + 范围纪律

| 文件 | numstat（vs HEAD，含 R0+R1 两轮） | 核验结论 |
|---|---|---|
| `infra/verify_workflow.py` | +127/−102（净 +25 = R0 净 −1 + R1 净 +26；物理行 24412→24437，`read` 实证） | 4 hunk：常量区（L1852-1877，含 F-03 注释块）、`_hot_task_ids_for_version`（L1906-1930）、`check_hot_fact_source_consistency` 主体（L2064-2160）+ F-02 注释（L2152 附近）——**全部落在 hot-fact 函数族内，零顺带改动 ✅** |
| `infra/tests/test_verify_workflow.py` | +269/−1（R0 +150 + R1 ≈ +119） | R1 增量 = 4 个新 R1 测试 + test 11 佐证行补全（见 §5.6）；16 既有用例断言行零改动 ✅ |
| `core/architecture-baseline.json` | 2/2（`git_head` 5e6d8c7→dfafa95、`anchor_loc` 24412→24437） | `--regen` 机械产物；R7 `committed==fresh True` 实证非手编 ✅ |

## 2. 前轮 findings 逐条比对表（复审必达）

| R0 ID | R0 级别 | 裁决 | 独立验证事实 |
|---|---|---|---|
| F-01（REL 行识别 fail-open → 虚报逃逸） | P1 | **部分已修复——识别方向闭合，但修复机制在 released-face 侧引入新 fail-open（本轮新发现 F-R1-01 P1，见 §7）** | 识别方向：helper 直调真实 plan `REL-077 in ids: True / release_declared: True / release_delivered: True`（主路径生效）；反相 A（REL-078 目标列改日期 = R0 E3 精确形态）`claimFAIL_A=True`（逃逸闭合）。**但** `release_delivered` 由任意命中行的状态格 OR 累积（L1929）——探针 D 实证：向已交付 REL-077 行叙事格注入一个裸 `0.82.0` 提及 → face 被 unrelated 行抬成 released → 两条保护断言全部消失（issues 5→1）。`released_face = release_delivered` 的佐证机制可被叙事提及污染，仅在当日数据上碰巧正确 |
| F-02（REQ 交叉检查 version 过滤空转） | P2 | **已修复 ✅** | `_task_statuses_for_hot_source` L1890 `if version and …` → `version=None` 无过滤；新测试 `test_fix339_r1_req_matrix_delivery_check_spans_other_version_rows` 红→绿钉住；真实面无行为变化实证：0.81.0 锚下 version_task_ids 25 项中无 FIX-082~087 任何热表行（直调 ids 全列）+ 真实数据 check PASS |
| F-03（双正则不同步） | P3 | **已修复（选注释登记）✅** | L1867-1873 常量区登记块 + L2067-2068 函数内注记：分裂原因（snapshot face 闭合粗体 vs 真实数据未闭合粗体）+ 收敛条件（数据格式归一前不统一；宽松版喂 snapshot face 会改其解析）——与 R0 建议一致 |
| F-04（「进行中」字样放宽披露） | P3 | **已响应（声明面）；仓库内无持久化面** | 全仓 grep：FIX-339 在 docs/project 仅 release-checklist-0.81.0.md 与 review-REL-077-RELEASE-R3.md 的登记引用，三条 CHANGELOG 措辞建议未落任何仓库文件——Developer 称「供发布文档」，属声明面交付；如实记录为 F-R1-03（P3，非阻塞，REL-078 发布文档期为自然承载点） |
| F-05（「或后续」行归属） | P3 | **已修复 ✅** | 词界正则任意格匹配使 `0.82.0 或后续` 行入 version_task_ids（直调 `houbxu: (['FIX-339'], …)` 实证）；完成态判定不变实证：`_task_statuses_for_hot_source` 仍按 `normalized[4] != version` 精确过滤（L1890）→ 或后续行恒不判 delivered（保守方向保持）；新测试 `…_or_later_target_rows_join_active_version_tasks` 红→绿钉住 |

## 3. R0 §7 四项复审重点逐项裁决

| # | 重点 | 裁决 |
|---|---|---|
| ① | F-01 修复后 E3 型场景虚报必 FAIL | **识别方向闭合**：反相 C（目标列完好）/A（目标列改日期）/B（行内零 token）三形态全部 FAIL（C/A → `must not claim 已发布 before its release task is delivered`；B → 新显式 `claims 已发布 but no delivered release task row corroborates it`）；4 个新 R1 测试全绿钉住。**但 D 形态（已交付 REL 行叙事提及锚版本）逃逸**——见 F-R1-01 |
| ② | REL-077 主路径（release_delivered=True）生效且真实数据仍 PASS | **成立 ✅**：helper 直调 `REL-077 recognized: True / release_declared: True / release_delivered: True`；真实数据 `check-hot-fact-source` = `[OK] … synchronized / PASSED / EXIT=0`；数据面 L88 目标版本列 = `G9/G11`（七列语义恢复，磁盘实证） |
| ③ | 819 用例红基线身份不变 | **成立 ✅**：全量 `Ran 823 tests in 216.305s FAILED (failures=2, errors=1)`（+4 = 4 个新 R1 测试，全绿）；3 红身份与 R0 逐一一致：FIX300DualCaliberAgreementTests×2（ERROR test_fixture_identity_mode_agrees_with_engine_on_present_sources + FAIL test_identity_host_source_drift_reproduces_divergence_shape）+ LoopRuntimeClaimAdapterTests×1（FAIL test_claim_command_emits_complete_pass_report） |
| ④ | R1-R7 全绿 + 重锚正当性 | R1-R7 **全绿 ✅**（`[R1] PASS mainfile loc 24437 ≤ anchor 24437 (only-down)` … `[R7] PASS regen deterministic=True; committed==fresh True`）。重锚正当性裁决见 §5.5：**判定正当（修复必需面归因成立），附 F-R1-04 透明度注记** |

## 4. 逐维度裁决（5 维全覆盖）

| 维度 | 裁决 | 依据 |
|---|---|---|
| 正确性 | **有保留（F-R1-01 P1）** | 词界正则无前缀渗透（`0.810` 行对 `0.81.0` 锚零命中实证）；`version=None` 语义正确（L1890）；E2 fail-closed 路径与 R0 实证形态一致（代码未变）；**但 release-face 佐证可被 unrelated 已交付 REL 行的叙事提及污染（探针 D 实证 5→1 全逃逸）** |
| 安全性 | PASS | `re.escape(version)` 转义正确；版本锚源自 `([0-9]+(?:\.[0-9]+){2})` 捕获，注入面不存在；只读本地治理文件；overstate 正则 `[^。\n|]*` 边界与旧版等价 |
| 回归风险 | PASS | 全量 823 用例 3 红身份与 R0/HEAD 基线逐一一致；真实数据 PASS；16 既有用例无弱化（§5.6）；e2e/loop-claim 等既有基线 FAIL 面与本次 3 文件无关（R0 已归属，本轮未变） |
| 测试质量 | PASS（附 F-R1-01 关联缺口） | 4 个新 R1 测试均为 tempfile + 真函数调用、无自证断言（断言引擎输出、含失败信息回显 `f"misaligned target {…!r}: … in {issues}"` 可诊断性好）；**缺口：面侧无「已交付 unrelated REL 叙事提及不得抬升 face」负例（F-R1-01 无测试钉住）** |
| 可维护性 | PASS | helper 25 行仍职责单一，docstring 与实现一致（含 R0 报告指针）；双正则登记注释落位；F-03 分裂原因与收敛条件可追溯 |

## 5. 独立复现原始输出（关键行）

### 5.1 定向套件（仓库根运行）
```
Ran 20 tests in 0.083s  OK   EXIT=0     （16 既有 + 4 新增 R1）
```
（附 harness 陷阱披露：同命令从 `infra/` 子目录运行 → `Ran 20 … FAILED (failures=14)`，全部为 host 模式休眠所致假红——见头部环境事实①；后续轮次验收 MUST 以仓库根为 workdir。）

### 5.2 真实数据主路径（独立验证）
```
[OK] hot fact-source consistency synchronized
=== Hot Fact-Source Consistency Check ===
  Result: PASSED — hot fact-source sections are synchronized
EXIT=0
```
helper 直调（真实 plan-tracker，模块经 `sys.path`+importlib 加载）：
```
total_ids: 25   ids 样本: [FIX-311, FIX-313, FIX-315, FIX-316, AUDIT-153, REL-077, FIX-320, …, FIX-329]
REL-077 in ids: True   release_declared: True   release_delivered: True
0.99.9 control: 0 False False
wb-neg(0.810 行 vs 0.81.0 锚): ([], False, False)      ← 词界守卫无前缀渗透
wb-pos(0.810 行 vs 0.810 锚): (['FIX-999'], False, False)
houbxu(0.82.0 或后续): (['FIX-339'], False, False)      ← F-05 命中
```

### 5.3 反相矩阵（%TEMP% 真实 plan 副本：锚改 0.82.0 + roadmap 0.82.0 行状态格改「已发布（模拟提前虚报）」，其余见探针名）
```
RESULT C-intact   : claimFAIL_A=True  claimFAIL_B=False   ← REL-078 目标列完好(pending) → must not claim 已发布
RESULT A-rel-date : claimFAIL_A=True  claimFAIL_B=False   ← R0 E3 精确形态（目标列→2026-09-20）仍必 FAIL（逃逸闭合）
RESULT B-rel-absent: claimFAIL_A=False claimFAIL_B=True   ← REL-078 行内零 token → 新显式 FAIL（fail-closed 双保险）
RESULT D-narrative: claimFAIL_A=False claimFAIL_B=False  total 5→1 ← 已交付 REL-077 叙事格注入裸 0.82.0 提及 → face 被抬升，保护全失（F-R1-01 直接证据）
```
D 的 helper 直调：`ids: ['REL-077', 'FIX-335', 'FIX-337', 'FIX-339', 'FIX-341'] / release_declared: True / release_delivered: True`——REL-077（已交付，目标版本 0.81.0）仅因叙事提及即被计入 0.82.0 的 REL 交付佐证。

### 5.4 全量套件
```
Ran 823 tests in 216.305s  FAILED (failures=2, errors=1)
  ERROR: …FIX300DualCaliberAgreementTests.test_fixture_identity_mode_agrees_with_engine_on_present_sources
  FAIL:  …FIX300DualCaliberAgreementTests.test_identity_host_source_drift_reproduces_divergence_shape
  FAIL:  …LoopRuntimeClaimAdapterTests.test_claim_command_emits_complete_pass_report
```
→ 819→823（+4）；3 红身份与 R0 §4.4 逐一一致，既有基线声明成立。

### 5.5 archguard 重锚 24437 正当性裁决（任务书授权路径 vs 棘轮纪律）
```
[R1] PASS  mainfile loc 24437 ≤ anchor 24437 (only-down)
[R2] PASS  47 ≤ 47 | [R3] PASS | [R4] PASS 1299 ≤ 1299 | [R5] PASS 84/84 + 71/71
[R6] INFO  cold import 196 (Δ0)
[R7] PASS  regen deterministic=True; committed==fresh True
Result: PASS (0 violations) EXIT=0
```
净 +26（24411→24437）逐类归因（终态树实测；R0 中间态未入 git，字节级逐行差不可复原，见 F-R1-04）：

| 归因 | 行数（终态实测） | 对应 finding |
|---|---|---|
| helper 重写（def + 9 行 docstring + 词界正则 + 任意格匹配 + REL 双旗标） | 13→25 行，净 +12 | F-01/F-05 |
| F-03 登记注释（常量区 7 行 + 函数内 2 行） | +9 | F-03 |
| released_face 机理注释块（L2076-2080） | +5 | F-01 |
| fail-closed 显式 FAIL else 分支（L2089-2090） | +2 | F-01 |
| F-02 注释（REQ 交叉检查处） | +2 | F-02 |
| R0→R1 移除项（精确匹配分支、face 回退行替换等）合计 | 约 −4 | — |
| **合计** | **≈ +26** | 与锚增量一致 |

**裁决：正当**。四 hunk 零元素越出 F-01~F-05 修复面；R7 `committed==fresh` 证明锚为 `--regen` 实跑产物而非手编；only-down 对 committed 锚 24412 的放宽由任务书明确授权（「R1 锚已重置 24412→24437」），且增量全部为修复必需的注释/文档化/fail-closed 分支——无借重锚洗白无关增长的迹象。

### 5.6 test 11 断言意图专项（任务书点名的 fixture 适配）
- test 11 = `test_hot_fact_source_accepts_current_session_snapshot`（0.42.0 正面 snapshot 测试，既有 16 用例按定义序第 11 个）。
- 断言未动：仍为 `self.assertEqual(vw.check_hot_fact_source_consistency(path), [])`（全零要求，比 R0 更严面下是**更强**而非更弱的要求）。
- fixture 补全：新增 1 行已交付 REL-018 佐证行 + 3 行说明注释。**意图不变性论证**：该测试验证「一致的已发布态 → 零 issue」；R0 时代 face 可由 roadmap 自称回退升级故无需 REL 行；R1 将 face 收紧为 `release_delivered` 后，原 fixture 在新语义下语义不完整（roadmap 0.42.0 行自称已发布而无佐证 → 触发新显式 FAIL）。补佐证行是 F-01 严格化的**必然配套**，非断言弱化；配套的负例由 4 个新 R1 测试承载（净防护面增大）。
- 其余 15 个既有用例：diff 逐行核对，除 `_plan_content` 签名扩展（R0：plan_version 默认值 + extra_task_rows 参数）外断言零改动；20/20 绿（含全部负例）实证保护面在位。

## 6. AI 专项 5 项检查（R1 增量面）

| # | 检查项 | 结论 |
|---|---|---|
| 1 | mock 残留 | 无——4 个新测试全部 tempfile + 真函数调用，零 patch/mock |
| 2 | 硬编码返回值 | 无——面判定/任务集全部数据派生（直调实证随数据变化） |
| 3 | 幻觉 API | 无——新增引用逐一读实现核实：`_markdown_table_cells`(L1574)/`_normalize_markdown_cell`(L1609)/`_status_cell_is_delivered`(L1630)/`_contains_fix_token_or_range`(L1643)/`FIX_105_SNAPSHOT_RELEASE_VERSION_RE`(L1875)/`FIX_105_READINESS_RELEASE_BLOCKERS`(L1877)/`FIX_087_READINESS_VERSION`/`FIX_087_REQ_TASKS`/`_line_mentions_completed_range_as_pending`(L1933) |
| 4 | 未实现 TODO | 无 |
| 5 | 过度实现 | 基本无——改动聚焦声明面；「任意格匹配」的面侧副作用为本轮唯一超出生声明字面的行为后果，已立为 F-R1-01（非静默超实现） |

## 7. Findings

| ID | 级别 | 位置 | 问题 | 事实依据 | 修复建议 |
|---|---|---|---|---|---|
| **F-R1-01** | **P1（blocking）** | `verify_workflow.py` L1923-1929（`_hot_task_ids_for_version` 任意格匹配 + `release_delivered` OR 累积） | **F-01 修复机制的面侧 fail-open**：`released_face = release_delivered` 的佐证可被**任意**已交付 REL 行的**任意格**（含叙事/依赖/状态格）对锚版本 token 的提及满足——与该 REL 行是否真承载该版本无关。后果：0.82.0 锚定后，若任何已交付 REL 行叙事出现「后续 0.82.0 承载…」类惯用表述（本仓 narrative 版本交叉引用高频：FIX-320「非 0.81.0 引入」、FIX-335「副本 bump 0.82.0」均为真实行文），未发布虚报「已发布」的两条保护断言**静默全失**（探针 D 实证 issues 5→1）。docstring 声称 face 描述「that version's REL rows」，实现实为「提及该版本的行」——修复机制在其自身声明语义下不健全，当日 PASS 属碰巧正确（实证当日无污染：ids81 中 REL 行仅 REL-077；ids82 无已交付 REL 行）。与 R0 F-01 同族（同一保护面 escape），且系本轮新引入、无测试钉住 | 探针 D 原始输出（§5.3/D 行 + helper 直调三值）；探针 A/B/C 对照（识别方向已闭合）；ids82 = [FIX-335, FIX-337, FIX-339, REL-078, FIX-341]（REL-078 pending，无污染） | 面侧收窄（识别侧保留任意格召回）：`release_declared/release_delivered` 仅从「目标版本 cell 命中锚 token 或事项 cell 含 `发布 <anchor>` 形态」的 REL 行累积（或等价：REL 行单独走目标列+事项头双判据）；补 1 条负例回归测试：已交付 unrelated REL 行叙事提及锚版本 → 不得抬升 face（探针 D 固化为测试）。修复面 ≈ 数行 + 1 测试 |
| F-R1-02 | P3 | helper 任意格匹配 × `_contains_fix_token_or_range`（L1643-1653，仅全 token 子串与 `~` 区间） | 0.82.0 锚定时可预测的 3 条 missing-active-task FAIL（2 假 1 真）：① FIX-335（已交付 0.81.0 任务）因状态格叙事「副本 bump 0.82.0」被牵连（**假阳**，探针实证）；② FIX-337（目标 `0.82.0 或后续`）在 roadmap 0.82.0 行仅以斜杠缩写「…336/337」出现，`_contains_fix_token_or_range` 不解析斜杠缩写 → 判 missing（**字母面假阳/意图面真实缺口**）；③ FIX-341（目标 0.82.0）roadmap 行确实未列（**真阳性**，数据侧需更新 roadmap 行）。方向为过报（fail-closed 侧），无虚报风险；REL-078 候选期 prep 时需消化 | 探针 A/C 输出（`missing active task FIX-335/337/341`）；L1643-1653 源码（无斜杠缩写分支）；roadmap 0.82.0 行 L282 原文 | REL-078 prep 时：roadmap 行补 FIX-341、展开斜杠缩写或数据侧清理 FIX-335 状态格叙事；或后续任务给 `_contains_fix_token_or_range` 补斜杠缩写语义 |
| F-R1-03 | P3 | 仓库（无对应文件） | F-04 处置为声明面：三条 CHANGELOG 措辞建议未持久化到任何仓库文件（grep docs/project 仅登记引用）；REL-078 发布文档期为自然承载点 | 全仓 grep FIX-339 输出 | 打包 REL-078 时将「进行中字样放宽」披露写入 CHANGELOG/发布文档（Developer 已备三条措辞） |
| F-R1-04 | P3 | 流程透明度 | R0 中间态未入 git → R1 净 +26 的字节级逐行归因不可复原；本轮以「终态树逐类实测 + hunk 级范围证明 + R7 committed==fresh」承载裁决（见 §5.5），残余不确定性如实登记 | numstat + §5.5 归因表 | 后续修复轮建议 Developer 在报告中自带「相对上轮审查态的增量 hunk 摘要」，降低复审归因成本 |
| F-R1-05 | P3 | L2119（`completed_active_tasks` 用 `version=active_version`）、L2133（overview remaining 分支同款） | F-02 同族残留：依赖链 stale-range 检查与 overview「已完成任务仍承载 RISK-033」检查仍按锚版本精确过滤目标列 → F-01 形态行（目标列为日期/Gate/「或后续」）永远无法判 delivered，两检查对这类行静默空转（少报不误报，保守方向）。R0 遗漏、本轮补记 | L1890 精确过滤语义 + L2119/L2133 调用点 | 随下一轮顺带统一为 `version=None` 或按行自身目标版本派生（与 F-02 同一模式，约 2 处调用点） |

## 8. 硬门槛裁决

| 门槛 | 结果 |
|---|---|
| P0 阻塞数 | **0** |
| P1 关键数 | **1**（F-R1-01）→ unresolved_blockers = 1 |
| 5 维度覆盖 | 100%（§4） |
| 每条发现标注级别 | 100%（§7） |
| 设计一致性 | 与 DEC-195 方案 (a) 及 R0 修复建议一致；「识别方向」与声明一致，「面佐证机制」存在 F-R1-01 实证偏差（实现弱于其 docstring 声明语义） |
| AI 专项 5 项 | 全部完成（§6） |
| 复审必达 | 前轮 findings 逐条比对（§2）；round 声明 + prev 引用（头部）；未跳过比对直接下结论 |

## 9. 结论

**NEEDS_CHANGE（round=1，unresolved_blockers=1）**。

必须如实肯定：R0 五项 findings 中识别方向修复（F-01 核心）、F-02、F-03、F-05 全部独立实证已修复，R0 §7 四项重点中②③④完全成立，重锚正当性裁决通过，16 既有用例零弱化，真实数据主路径从退化路径恢复为 REL 交付态主路径。本轮唯一阻塞项 F-R1-01 是**修复自身引入**的面侧新缺口：它不否定上述成果，但使「未发布虚报已发布」的防护在一种本仓高频行文形态（narrative 版本交叉引用）下重新静默失效，且该形态未被任何测试钉住。修复面小（面侧判据收窄 + 1 条负例测试），建议本轮完成修复后进 R2 复审。

**R2 复审重点**：
1. F-R1-01 修复后探针 D 形态（已交付 unrelated REL 行叙事提及锚版本）必 FAIL 或不抬升 face——负例测试入库且红→绿实证；
2. 识别方向四形态（C/A/B/主路径）不回归（R1 的 helper 直调 + 反相矩阵可直接复用）；
3. 全量用例 823+N 红基线身份不变（3 红既有身份）；
4. R1-R7 仍全绿；若面侧判据改动带来净行数变化，重锚需按同路径重新核验归因。
