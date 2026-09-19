# review-FIX-358-CODE-R0 — 独立代码审查报告（round 0）

- **Task**: FIX-358（谓词并集五件套）— review-FIX-355-CODE-R0 C-02/03/05 + review-FIX-357-CODE-R0 P3-1/2 折叠修复
- **Reviewer**: Code Reviewer Agent（独立审查，未参与实现；Developer 不自审）
- **日期**: 2026-09-19 ｜ **审查性质**: 只读（零产品代码/.governance 写入；本报告为唯一新增仓库文件）
- **审查范围（恰 2 文件，工作树未提交 diff）**:
  - `skills/software-project-governance/infra/checks/review_domain.py`（+67/−13，blob `f98d547..2563f1a`）
  - `skills/software-project-governance/infra/tests/test_review_closure_legacy.py`（+317/−0，blob `1c8fc99..0402605`）
- **前像链完整性**: `f98d547` = review-FIX-357-CODE-R0 的后像 blob（其报告 §前像锚记载 `e681bfa..f98d547`）→ 修复链前像衔接无缝；`1c8fc99` = FIX-357 测试后像，同证。review-FIX-355 binding note 5 的重跑条款不触发。
- **会话状态披露（如实）**: 审查窗口内并行任务（version pins / manifest）的 3 个工作树文件被并行流程 commit 出工作树（HEAD `5a4c4f4`）；本任务 2 文件 diff 全程未变（blob 锚与开工捕获逐字一致），审查证据面有效。

---

## 0. 总结论

## **APPROVED_WITH_NOTES** — unresolved_blockers = **0**

**发现计数：P0 = 0 ｜ P1 = 0 ｜ P2 = 0 ｜ P3 = 4（N-1~N-4，全部记录性/讨论性，不阻塞）**

五项审查重点（①~⑥）全部通过；5 项动态复验全部真实执行且与 Developer 申报吻合（1 项计数偏差 363t→364t 经 A/B 实验证明与本 diff 无关，见 N-1）。修复语义与 C-02 裁决②（并集而非 cell 归一化）、C-03 契约文、C-05 三分支锁定、P3-1 两门端到端正例、P3-2 不变量看护逐项一致。

---

## 1. 独立复验结果表（Reviewer 本会话当场执行，全部 exit 0）

| # | 命令 / 操作 | 当场结果 | 与 Developer 申报对照 |
|---|---|---|---|
| R1 | `pytest …/test_review_closure_legacy.py -q` | **63 passed**（0.45s） | 申报 63（54+9）✓ 逐数吻合 |
| R2 | 只读内存补丁脚本（真实 `.governance/archive/index.md`，162,737 B）：f341 臂置空 → 测 arm1；还原 → 测 union；直测 f341 | arm1=**362**，f341=321，union=**375**，**union == arm1∪f341**，**f341−arm1 = 恰 13** | 申报「362→375（13/13）」✓ 实测复现 |
| R2b | 13 个新增 ID 的原始状态格逐条 dump + `live_active` 交叉核对 + 加粗 ID 行扫描 | 13/13 均为确凿闭环散文/发布形态（逐条见 §3.1）；**新增∩live-active = ∅**；**加粗 ID 行 = 0**（docstring 披露的 arm-only widening 现网零实例） | docstring「13 verified-closed」「方向安全」✓ |
| R3 | M4 突变实证（内存补丁 `_status_is_completed_cell → "完成" in cell` 后单跑 C-05 用例③；前后基线各跑一次） | 基线 PASS → 突变 **FAIL**（`AssertionError: 'ARCH-201' not found in []`——与预测 kill 路径逐字一致）→ 还原后 PASS → **M4 KILLED: True** | review-FIX-355 V-12 存活突变已被 C-05③ 击杀 ✓ |
| R4 | `pytest …/test_task_priority.py -q` | **147 passed**（5.38s）——f341 臂源模块回归无污染 | 申报 147 ✓ |
| R5 | 真实 `.governance` live `check_review_closure()` | **WARN / violations=0 / warnings=29 / tasks_checked=364**（V2×3=FIX-071/FIX-246/REL-078，V1×21，V3×4，V5×1） | 申报「WARN/0v/29w」✓；「363t」实测 **364t** → 见 N-1 |
| R5b | **当前工作树精确 A/B**：f341 臂禁用（=修复前语义）×2 与启用 ×1 各跑 live Check 30，全输出（含逐条 reason 文本）比对 | **A == B 全输出逐字一致：True**（A′ 复跑确定性 ✓；双侧 tasks_checked 同为 364） | 申报「Check 30 A/B 逐字一致」✓，且经当前树独立复证 |

未独立复验项：无——申报清单中可复验的 6 项全部真实执行。（verify 全子命令 / cross-refs / manifest 三项未列为本审查必验面：本 diff 不触这些计数面，R5b 全输出一致为更强证据。）

---

## 2. 审查重点逐项结论

### ① 并集方向安全实证复核 — **通过（实测复现）**
- f341−arm1 = 恰 13，且 13 个 ID 与 review-FIX-355 C-02 清单**逐 ID 一致**（FIX-165 / REL-048 / AUDIT-131 / AUDIT-134 / AUDIT-137 / AUDIT-138 / FIX-152 / FIX-214 / FIX-263 / REQ-101 / REQ-104 / REQ-105 / REQ-106）。
- 13 个状态格逐条人工复核（R2b UTF-8 dump）：`完成 + 已发布 0.61.2 (…)`、`完成——Requirement R3/R2 APPROVED`、`发布完成 + pushed (…)`、`已交付 (2026-08-02)`×3、`设计定稿 (…)——…`、`实现完成 + 事后审查 APPROVED`、`分解计划完成 + 审查通过（APPROVED_WITH_NOTES…）`、`设计完成 + 实现前独立复核通过`、`完成/Alternative A已选择`、`完成——DESIGN_AUTHORIZED`——全部为确凿闭环断言，无一条含开放语义。
- `union == arm1∪f341` 实测成立（单调可加）；新增集∩live_active = ∅（现网无 veto 交互），且上游 `- live_active` veto 在合并点结构性在位（L2168-2169）。
- REL-078 仍由 arm 1 独占看护（f341 判 False/arm1 判 True；arm1−f341=54 含之）——docstring「PRIMARY 状态格谓词看护候选提交形态」的主张实测成立。

### ② lazy import 纯函数不抛语义 — **通过**
- `from task_priority import parse_archive_index_completed_ids`（L2731）为函数内 lazy import，与同文件既有先例 L2614（`parse_task_dependencies`）同型；`task_priority` 为 pure-stdlib peer leaf（bootstrap_aggregate L33 注释在案）。
- **无新增导入失败面**：同一 live 路径上 L2614 的先例导入先于本导入执行（`_live_task_completion_sets` 在 L2151 先被调用）——若 peer 模块不可导入，检查在更早处已走 except fail-safe，本行不构成新暴露面。
- 被导入函数不抛性源码核实（task_priority.py L671-715）：None → 空 frozenset；bytes → `decode(errors="replace")`；`str()` 强转；空文本 → 空 frozenset——纯文本入 → frozenset 出。即使异常，调用方 try/except Exception（L2172-2175）兜底为 `closed = completed`（fail-safe 方向 = 不扩大豁免）。

### ③ C-05 用例③双任务装置真实性 — **通过（M4 实证击杀）**
- 双任务同运行装置成立：ARCH-201（`尚未完成 (…)`——两谓词皆 False → 保持 V2 violation）与 ARCH-202（`已完成 3/8 项 (…)`——真实谓词既定行为 → 豁免）耦合在一条 evidence 流中，互为对照。
- **M4 突变击杀经 R3 实证**：谓词退化为子串测试时 ARCH-201 被误豁免（violations 翻空），断言 `assertIn("ARCH-201", …violations)` 翻红——FIX-355 V-12 的存活突变就此闭环。
- 豁免 WARN 断言携带 closure basis 归档披露（`closure basis: archived task` + `DEC-214②`）且 `assertNotIn("closure basis: live")`——与 FIX-357 分流契约同口径锁定。
- 装置保真：V-8 三形 fixture 与真实语料行**逐字一致**（R2b dump 比对 3/3）；`_live_run` 走 temp `.governance` + 真实 `check_review_closure()` live 路径，与文件内既有用例同构；C-05① 的 fragile/control 双运行设计使「UNKNOWN 当空 active 集」fail-open 突变必被杀（fragile FAIL / control WARN 对照）。

### ④ 负标记否决表只收缩自身输出 — **通过**
- 结构面：veto 表（task_priority L641-645）仅在 `_archive_index_status_is_completed` 内消费，只影响 f341 自身返回集；合并为 `completed |= f341`，veto 无法触及 arm1 已收入集。
- 实证面：arm1−f341 = 54（含 REL-078「候选=候选提交」例）——veto 收缩只发生在 f341 侧，arm1 输出经并集原样保留（R2 `union == arm1∪f341`）。
- docstring 同时披露 f341 臂的加粗 ID widening（`_strip_markdown`，C-06 记载的分叉）——现网实测 0 实例（R2b），方向可加。

### ⑤ 范围纪律 — **通过**
- 恰 2 文件；review_domain.py 全部 4 个 hunk 落于 closed 合并点（L2158-2171）与 `_archived_completed_task_ids`（docstring/except/union 两行）——**V1 破链门与 V1 措辞零改动**（不在任何 hunk；R5b A/B 全输出一致为行为级佐证）。
- C-04（DEC-214 残留类补记，Coordinator 面）、C-06（常量/正则去重）、C-07（冗余断言改写）、C-08（`_live_done` 复用 + 宽 except 诊断）均**未并入**——与任务范围声明一致；测试 diff 起于 L1293，C-07 所指既有用例（L1082 区）逐字未动。
- 测试写入面仅 tempfile（零 `.governance` / 零仓库写入）；本审查窗口 `git status` 中本任务 2 文件外无新增改动面。

### ⑥ AI 代码专项 5 项 — **全部通过**

| # | 检查项 | 结论 |
|---|---|---|
| 1 | mock 残留 | **通过**——生产代码零 mock；测试 `mock.patch.object` 为既有 fixture 隔离模式 |
| 2 | 硬编码返回值 | **通过**——13 ID 等数值为 docstring 记载的实测事实（本审查 R2 独立重测吻合），非投机常量 |
| 3 | 幻觉 API | **通过**——`parse_archive_index_completed_ids`（task_priority L671）与 `_strip_markdown`（L382）实测存在且行为与注释一致（R2/R4 实跑） |
| 4 | 未实现 TODO | **通过**——新增行 TODO/FIXME/XXX/HACK/NotImplemented/print **0 命中**（git diff 逐加行扫描） |
| 5 | 过度实现 | **通过**——生产面最小（1 lazy import + 1 并集行 + except 元组扩 1 项 + 1 防御断言）；测试 317 行/9 用例，每用例锁定单一形态，无投机分支 |

---

## 3. 五维度结论

| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | ✅ 通过 | ①并集方向安全实测（§2①）；C-03 契约成立（非法 UTF-8 → 空集，R1 内用例 + 单元面）；P3-2 断言语义正确（`set >=` 超集判定；置于 try 内，即便触发亦被 except 兜为 live-only fail-safe，不碎 Check 30） |
| 安全性 | ✅ 通过 | 无注入/凭据/eval 面；全程只读；输入为仓库内受信治理文件；ID 正则线性无回溯 |
| 可维护性 | ✅ 通过 | docstring 记载裁决②理由 + 三形实证 + veto 方向论证 + widening 披露，质量高于基线；与 FIX-341/FIX-355/FIX-357 报告互引完整 |
| 性能 | ✅ 通过 | 并集为同文本二次单遍解析（f341 ~ms 级），Check 30 总耗时 5.9s 基线下占比可忽略（FIX-355 V-13 量级外推）；无循环内 I/O |
| 测试覆盖 | ✅ 通过 | 63 passed（R1）；C-05 三分支 + V-8 三形 + P3-1 两门正例 + C-03 单元/端到端双面；M4 存活突变经 R3 实证转为击杀；红相存在性构造成立（修复前三形/三分支均必红） |

---

## 4. Findings

| 级别 | 位置 | 描述 | 建议 |
|------|------|------|------|
| P0 | — | 无 | — |
| P1 | — | 无 | — |
| P2 | — | 无 | — |
| N-1 (P3) | 记录面 | Developer 申报「363t」，本审查实测 tasks_checked=**364**——R5b 证明该计数与本 diff 无关（A/B 双侧同 364），为审查窗口内语料漂移（并行任务 review 证据入账）所致；申报时点与审查时点语料不同 | 无需动作；evidence-log 记录时以实测 364 并注明时点 |
| N-2 (P3) | review_domain.py L2732（讨论） | f341 臂继承子串教义：假想未来格「部分已交付 (…)」（含已发布/已交付正面 marker、无 veto 词）会被并集豁免——该 fail-open 类与 arm1 既有已裁决子串类（C-05③ 锁定的「已完成 3/8 项」）同类，现网 13 个新增全部确凿闭环、0 反例 | 记录性：若未来归档语料出现「部分已交付」类格，f341 veto 表是收敛点（加 marker 即收缩），无需改本文件 |
| N-3 (P3) | review_domain.py L2170-2171 | P3-2 防御断言位于 try 内——若未来回归触发，输出静默降级为 live-only（方向安全但零诊断，与 C-08「静默即契约」同族） | 可接受（抛出断言反而违反豁免门 fail-safe 契约）；未来触及该文件时可随 C-08 一并补 except 注释 |
| N-4 (P3) | review_domain.py L2667 | docstring「13 verified-closed IDs (3.5% of the index)」——实测 13/375 ≈ 3.47%，比例表述成立但分母（唯一 ID 基数）未在文中写明 | 无需动作；下次触及时可补「of N unique IDs」 |

---

## 5. 硬门槛逐项裁决

| 门槛项 | 裁决 |
|--------|------|
| P0 阻塞问题数 = 0 | ✅（P0 = 0，P1 = 0，P2 = 0） |
| 5 维度全覆盖 = 100% | ✅（§3 逐维有结论） |
| 每条发现标注级别 = 100% | ✅（§4，4 条全部 P3 并显式记录无 P0/P1/P2） |
| 设计一致性检查 | ✅——与 C-02 裁决②（并集方向，非 cell 归一化）、C-03 契约文、C-05 三分支建议、P3-1/P3-2 原建议文本、DEC-214② 合并语义、FIX-341 解析序逐项比对（§1/§2） |
| AI 代码专项 5 项 | ✅（§2⑥） |
| 独立复验命令真实执行 | ✅ 全额达成——R1~R5b 全部 exit 0 入表（无「未独立复验」标注项） |
| 报告落盘 docs/reviews/（唯一写入面） | ✅（本文件） |

## 6. 边缘问题（呈 Coordinator，不阻塞）

1. **C-04 未闭环提醒**：C-02/03/05 已由本 diff 代码面收口，但 review-FIX-355 C-04（DEC-214 补记 V1 残留类清单）属 Coordinator 治理记录面，本任务正确地未代劳——该项仍悬，勿随本任务误标完成。
2. **并行任务工作树**:审查窗口内 version-pins/manifest 3 文件被并行流程 commit；本报告证据面以 blob 锚 `f98d547..2563f1a` / `1c8fc99..0402605` 锁定，复审条款：若二文件 blob 变更，本报告复验面失效须重跑 R1~R5b。
3. **N-1 计数时点**: Coordinator 记录 FIX-358 证据时建议引用本报告 R5/R5b 实测值（364t）而非申报值（363t），避免带陈旧计数入账。
4. 临时验证脚本 5 个均落于会话 %TEMP% 目录（仓库外），未在仓库留下任何临时文件。

---

*审查方：Code Reviewer Agent（独立走链，只读）｜审查对象：FIX-358（`2563f1a` + `0402605`，前像链 f98d547/1c8fc99 ← FIX-357 后像）｜结论：**APPROVED_WITH_NOTES / unresolved_blockers=0**｜机录义务：Coordinator 以 `review-record` 持久化本结论（Reviewer 不写治理状态）*

— review-FIX-358-CODE-R0 完 —
