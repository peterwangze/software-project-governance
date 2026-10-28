# Review: FIX-475 — CODE R0（独立代码审查）

- **Reviewer**: Code Reviewer Agent（独立——非实现作者；只读审查 + 本报告文件写入，零代码/测试/治理记录修改；变异检验已精确还原并哈希自证）
- **日期**: 2026-10-28
- **审查对象**: 工作树未提交改动（2 文件）：`skills/software-project-governance/infra/verify_workflow.py`（+23/−11）、`skills/software-project-governance/infra/tests/test_verify_workflow.py`（+122/−11）
- **验收基线**: TRIAGE-FIX-475（.governance/change-triage/FIX-475.json）
- **结论**: **NEEDS_CHANGE**（P0=0；**1 个 P1 阻断项**：Check 24 stale pin 台账回归，须随批闭环后方可 AWN）

## 一、逐项核实证据（独立执行，非采信 Developer 报告）

### 1. diff 纯粹性 — PASS
- `git status --porcelain`：仅 ` M` 两目标文件；未跟踪目录 `.codex-sandbox/`（既有 scratch）与 `.governance-backup-20261028-1425/`（Coordinator 会话备份），非 Developer 改动。
- `git diff --stat`：145 insertions(+) / 11 deletions(-)，与声称一致；逐行读 diff 无无关重构/格式化/行尾漂移（CRLF warning 为 Windows checkout 既有状态）。

### 2. 单一语义源 — PASS（附 F-02 记录精度 P3）
- 源文件旧名 `_is_quality_budget_pending_allowed` / `_is_vertical_slice_pending_allowed` 零残留；新谓词 `_is_task_pending_status_allowed` + 常量 `TASK_PENDING_STATUS_MARKERS` 唯一定义（L14604/L14618），两个调用点（L14671/L14788）均改用共享实现。
- `project/e2e-test-project/.../verify_workflow.py` 仍含旧名 ×4——经查为 7832 行历史快照 **fixture**（源 28384 行，非投影）；`check-governance` full 面 **Check 28b PASS** 证明该文件不在投影同步义务集（对照 FIX-457：真投影漂移会 28b FAIL）。无行为影响（1155 测试 OK）。
- FIX-292「无第二语义」教训落实：重复谓词消除，词表单一常量。

### 3. 词表事实性 — PASS（附 F-03 边缘说明 P3）
- 10 词逐项核实：规划中/待实施/pending/planned（旧词汇回归）+ 派发中（FIX-475 活跃行自身形态）/进行中（plan-tracker L110 历史活细胞「🔄 进行中」）/开发中/in progress/in_progress/wip——活仓或近活仓有据。
- 终态词排除：✅/完成/committed/completed/已交付/已发布均不在词表，且被 `test_terminal_and_unmarked_statuses_stay_rejected`（8 细胞含终态 8 形态→False）+ `test_marker_vocabulary_excludes_terminal_words`（词表级 ratchet）双重钉死。
- 边缘：`📋 待启动` 被排除——grep 证实其仅存在于需求矩阵 backlog 表（REQ-029~033，1.0.0 交付），不进入活跃任务解析面（Check 18 required 集仅 1 = FEAT-111 佐证），零实况影响；`in-progress` 连字符形态全仓零使用。

### 4. 语义边界 — PASS
- diff 证明 PASS 路径（`QUALITY_BUDGET_PASS_STATUSES`）与 EXEMPT 路径（`QUALITY_BUDGET_EXEMPT_STATUSES` + exception 非占位校验）零触碰；threshold/validation/evidence/exception/scope_guard/weak-prose 等其余校验原样；仅 pending 白名单判定两行替换。
- 注释段明确记载设计依据与终态词上游排除机制（`_active_execution_packet_tasks → _is_incomplete_task_status`），与代码事实一致。

### 5. 测试真实性 — PASS（变异检验实证）
- 定向复跑：`Ran 31 tests ... OK`（与声称 GREEN=31 一致；RED=9→GREEN=31 的翻转由 2 个旧语义测试改名翻转 + 6 场景新增 + 3 词表测试构成）。
- **变异检验**：临时将词表 `"规划中"` 改 `"规划中_MUTATED"` → 三类测试 `FAILED (failures=3)`（词表测试 + planning 场景 ×2 真实依赖该词条——非恒真断言）；还原后 SHA256 与变异前一致（hash_restored=True，零残留）。
- 测试走真实管线（SAMPLE_PATH 指向临时 plan fixture → generate_execution_packets → 真实校验函数），非被测对象 mock。
- 旧语义测试翻转（进行中 rejects→allows）由 TRIAGE-FIX-475 验收条款背书（验收原文显含「派发中/进行中 … NOT_RUN_YET 通过」），非 Developer 私自改判。

### 6. 复跑验证 — PASS（18f/18g 清零）+ 发现 F-01
- `check-governance --summary-only --scope quick` 与 full 面（--level strict）：**18f/18g 对 FEAT-111 的 FAIL 全部清零**（full 面 10 issues 清单中无 18 系）。
- 全模块套件：`Ran 1155 tests in 413.044s / OK / exit=0`（与声称一致）。
- **但 full 面出现 Check 24 ×4 新增 WARN**（详见 F-01）。

### 7. 五维度结论（全覆盖）
| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | PASS | 谓词语义 = 旧语义 ⊕ 词表扩展；子串匹配机制与旧实现同构；边界测试覆盖无标记/终态/空串 |
| 安全性 | PASS（无新面） | 纯内部判定词表，无输入解析/注入/权限面变化；无敏感数据 |
| 可维护性 | PASS | 消除重复谓词（本任务核心收益）；命名表意；注释含依据；常量就近定义 |
| 性能 | PASS | `any(marker in status ...)` 10 词子串线性扫描，status 细胞短，每任务一次，无算法退化 |
| 测试覆盖 | PASS | 核心路径（10 词正例）+ 边界（无标记/终态/空/大小写）+ 端到端双检查器管线 + 变异检验实证 |

### AI 代码专项 5 项
mock 残留=无（patch 仅注入 fixture 路径，被测对象真实）/ 硬编码返回值=无 / 幻觉 API=无（全部既有函数与测试基建）/ 未实现 TODO=无 / 过度实现=无（词表 10 词全部有据，无投机扩面）。

## 二、发现清单

### F-01 [P1 — 阻断，本轮必须闭环] Check 24 stale pin 台账回归（变更归因）
- **事实**：full 面新增 4 条 WARN：`static-version-pin: stale exemption test_verify_workflow.py:20971/20974 (token "0.94.0")`、`:21472/21504 (token "0.93.0")`——「line no longer carries the token」。基线对照：今晨 full（改动前）与本会话 quick 复跑均无 Check 24 项；改动 = test 文件 +122/−11 行漂移致 STATIC_PIN_EXEMPTIONS 台账行号失锚。**归因明确**。
- **违反**：验收条款④「全套件零退化」在治理面不成立（+4 WARN）；DEC-213③「行号漂移 → re-audit」随批义务未履行；仓例 EVD-2179（FEAT-104）同类漂移以 `pins re-anchor` 机写 op×4 **随批**闭环。
- **修复**（机械动作，非代码）：`verify_workflow.py pins re-anchor`（FIX-462 机写通道）刷新 4 行锚点后复跑 Check 24 归零；预计 ≤5 分钟。**修复后走 R1 复审**（复审点单一：F-01 闭环 + 全量面零新 WARN）。
- **为何阻断**：本任务本身是治理健康修复票，交付却引入治理面新 WARN 回归 + 留下未履行的机写义务——「登记待以后」违反 DEC-286；且 commit 后 hooks/CI 面将携带该回归。

### F-02 [P3] Developer 声称「旧函数名全仓零残留」不精确
e2e 历史快照 fixture（project/e2e-test-project/.../verify_workflow.py，7832 行）仍含旧名 ×4。经核实非投影（28b PASS）、无行为影响、无同步义务——但「全仓零残留」表述与事实不符，如实修正交付报告口径即可，无动作。

### F-03 [P3] 「待启动」排除的远期注记
词表排除 `待启动`（现仅存于需求矩阵 backlog，不入活跃解析面）当前零影响；若未来 REQ 行进入活跃任务表（如 1.0.0 启动），需重访词表。测试已钉死其当前为拒绝态，语义自洽。

### F-04 [P3 — 非本变更归因] 28v DSH Preset 环境面漂移披露
本次复跑 28v 从今晨 PASS 翻为 FAIL（7 composition rows rejected，DSH_HOME/profiles 插件集判定）——diff 未触及 preset/composition 任何代码，判定为宿主环境 mid-session 漂移。与 FIX-475 无关，建议 Coordinator 另行环境健康核对（非本票阻断）。

### F-05 [P2 — 建议，不阻断] `wip` 子串匹配面偏宽
`marker in status` 子串匹配下，终态叙述细胞若偶然含 "wip"（如「✅ 完成（WIP 清理）」）可获 pending 豁免。现缓解：上游 `_is_incomplete_task_status` 已滤终态任务，实际误授权面≈0；且旧实现对 "pending" 同为子串匹配（等宽语义）。建议未来以词边界/细胞前缀锚定收窄——单独小票承载即可，不要求本批。

## 三、硬门槛裁决

| 门槛 | 结果 |
|------|------|
| P0 阻塞数 | **0** |
| 五维度全覆盖 | 100%（5/5 有结论） |
| 每条发现带级别 | 100%（F-01 P1 / F-02~04 P3 / F-05 P2） |
| 设计一致性 | 与 TRIAGE-FIX-475 验收五条对照：①②③⑤ 满足，④ 治理面不满足（F-01） |
| AI 专项 5 项 | 全部完成、全部无发现 |

## 四、结论

**NEEDS_CHANGE** — blockers=1（F-01：Check 24 ×4 stale pin 随批 re-anchor 闭环 + 复跑验证）。代码与测试本体质量合格（P0=0、变异检验通过、1155 OK、18f/18g 清零达成）；唯一阻断是治理台账随批义务缺失，机械修复即可。**round=0**；修复后按 M7.4 spawn 同一 Code Reviewer R1 复审（复审面：F-01 闭环证据 + full 面 Check 24 归零 + 无新引入）。
