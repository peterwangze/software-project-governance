# FIX-288 Code Review R0 — change-triage 版本适配事实源 + task-priority-analysis 终态过滤

- **Round**: R0（首审；基线 HEAD = `afb959d`，工作树未提交 diff）
- **Task**: FIX-288（FIX-281⑨⑦，0.78.1 入槽，DEC-173① 方案 A 缺陷面；首派发锁阻塞处置见 EVD-FIX-288-BLOCKED）
- **审查范围**（严格 6 文件）: `task_priority.py`、`change_triage.py`、`verify_workflow.py`、`commands/change-triage.md`、`test_task_priority.py`、`test_change_triage.py`
- **范围红线遵守**: FIX-289 的 3 文件（review_record.py / test_review_record.py / evidence-id-prefix-conventions.md）未读、未引用、未据此发 finding
- **审查方式声明**: 本 Reviewer 无 Bash 权限（角色硬约束），全部结论基于逐行代码阅读 + 结构化检索；Developer 自报的运行类验证（测试执行、verify、xref、live 验收）未独立复核，仅核验其代码层可证性
- **Reviewer**: Code Reviewer（Coordinator spawn）
- **Date**: 2026-08-28

## 终态结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`（P0=0、P1=0、P2=1、P3=5）

## 一、5 维度逐项结论

| 维度 | 结论 | 事实依据（可复查） |
|------|------|------|
| 1 正确性 | **通过** | ⑦ 判定顺序（空→⏳→终态 marker→终态词）逻辑闭合：task_priority.py L281-295；blocking 零变化核实：`_status_is_completed` L180-189 仅 `contains ✅` 未动，L1407 `status_map`/L1417-1430 分桶仅由其驱动，词终态行不入 completed → 依赖方仍被阻塞（保守正确）。⑨ 语义版本比较：`_version_tuple` L311-315 返回 int 元组，`max`/`min`/`>` 均为元组比较——0.10.0=(0,10,0) > 0.9.0=(0,9,0)，无字符串排序陷阱；且 `_OLD_HOST_TRACKER`（test_change_triage.py L917-936）用 0.9.0/0.10.0 相邻行做回归防护。「已发布（tag 缺失待修）」带后缀形态经子串匹配正确入选（L322 `_RELEASED_STATUS_TOKEN="已发布"` + L347 `in`）；已撤回/失效/不可信发布/补偿发布规划中/规划均不含「已发布」子串，不入选。`derive_project_current_version` 无已发布行→`""`（L351-352）→ `validate_version` L434 跳过下界比较 → fail-safe。`_planned_next_version` L377-393 三态逻辑正确。接线：verify_workflow.py L21199 单次读盘，L21202 纯函数复用同一文本快照——无重复磁盘 I/O、无 TOCTOU 时序问题 |
| 2 安全性 | **通过** | 纯文本解析，无 eval/exec/shell 拼接；CLI 测试 subprocess 使用列表参数（test_change_triage.py L1045-1048）；无敏感数据硬编码；无权限/输入面扩大。两个新函数均为无 I/O 纯函数（纯度契约保持） |
| 3 可维护性 | **通过** | 命名表达意图；契约 docstring 三处同步（change_triage.py L16-19/L400-411、verify_workflow.py L21180-21186、run_triage L729-732）；`derive_project_current_version` 已导出 `__all__`（L898）；修改区注释均携带 FIX-288 标记与裁决来源；函数长度均 <50 行 |
| 4 性能 | **通过** | `parse_version_chain` 对同一文本被解析两次——O(2N) 常数因子，plan-tracker 数百行级，可忽略；无 N+1、无重复磁盘 I/O、无新循环嵌套 |
| 5 测试覆盖 | **通过（附 1 条 P2 缺口）** | ⑦ 7 用例（核心排除/入桶/🔄 对照/候选唯一性/completed 词形区分/全终态 router 锚点）；⑨ 7+1 用例含真实 subprocess 端到端。缺口：`_planned_next_version` 的「cur 未知→取最低规划行」分支无直接单测（见 P2-1） |

## 二、发现列表

**P2-1（测试覆盖缺口）** `tests/test_change_triage.py` ProjectCurrentVersionTests（L950-1027）
- 问题：`_planned_next_version` 三态中的「无当前版本（`current_version=""` 或非 semver）→ 取最低规划行」（change_triage.py L388-393 的 `cur is None` 分支）没有直接测试。现有用例的 `current_version` 全部为已知 semver。
- 影响：该分支正是旧宿主（有规划行、无已发布行）场景的 planned_next 事实源；若未来回归（如 first-match 行为在 cur=None 路径复活），现有 15 用例抓不住。
- 建议：补一条 `validate_version(target, current_version="", version_chain=[{"0.66.2","补偿发布规划中"},{"0.78.1","规划中"}])` 期望 `planned_next="0.78.1"` 的用例——同时锁住 cur=None 路径的 first-match 回归。
- 处置：遗留项（不阻塞合并）。

**P3-1（讨论）** task_priority.py L248 — 「完成」子串在无 marker 引导 cell 上可能过匹配：如「未完成」「待完成」「部分完成」会被判终态词 → non_executable。这是 FIX-288 范围裁决（仅完成词触发）的既定保守取舍——被过滤行进 Excluded 桶保持可见（L239-241 声明），不消失、不解锁、不误导 blocking。建议后续任务评估「未/待」类负向前缀豁免；本轮不改（改则违反裁决）。

**P3-2（讨论）** task_priority.py L244/L286-287 — 「⏳ 已终止」类混合形态：⏳ 显式优先于措辞，保持 eligible。与重派发裁决的 ⏳ 豁免一致（注释 L224-225 与测试 docstring L1065-1066 双重声明），非漏洞；若真实数据出现 ⏳+终态词组合会重新成为候选——属数据卫生风险，备案即可。

**P3-3（讨论）** change_triage.py L347 — 「已发布后撤回」类假设性复合措辞会因含「已发布」子串被误判 released。注释声明的排除集均实际不含该子串；substring 风格与模块既有模式一致。无现行数据形态触发，备忘。

**P3-4（事实记录偏差）** Developer 自报「红→绿 14 用例」与实际读到的新测试方法数 **15**（TestTerminalWordStatusFilter 7 + ProjectCurrentVersionTests 7 + ChangeTriageProjectVersionCliTests 1）不符（少计 1）；运行类数据（123/123、69/69、2006/26、live 验收等）均未独立复核（Reviewer 无 Bash）。测试代码存在且断言语义与自报一致，可证性成立；按事实依据红线如实记录计数偏差。

**P3-5（防御不对称，nit）** task_priority.py L281 直接 `status_cell.strip()`，而 L243 用 `str(status_cell or "").strip()`。唯一调用点输入来自 parse（保证 str），无实际风险；可选统一。

## 三、AI 代码专项 5 项结论

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | **无** | 新测试全部真实 tempfile + 真实 subprocess；无 mock/patch |
| 2 | 硬编码返回值 | **无** | 业务词表是带裁决出处的领域词表，与模块既定模式一致（FIX-226/FIX-237 同风格）；既有 CLI 用例动态取 SKILL 版本避免硬编码 |
| 3 | 幻觉 API | **无** | 所用 API 全为真实 stdlib；跨模块 `derive_project_current_version` 已入 `__all__` 并在 L21192 真实 import |
| 4 | 未实现 TODO | **无** | task_priority.py 与 change_triage.py TODO/FIXME/XXX/HACK/NotImplemented 零命中；verify_workflow.py 修改区（L21165-21241）通读无占位 |
| 5 | 过度实现 | **无** | 两函数均为裁决要求的最小实现；「四步分析」标题按裁决未触碰；🔄 双语义、⏳ 豁免均严格按裁决边界，无额外启发式 |

## 四、硬门槛裁决

| 门槛项 | 结果 |
|--------|------|
| P0 阻塞数 = 0 | ✅（P0=0） |
| 5 维度全覆盖 | ✅ |
| 每条发现标注级别 | ✅（P2×1、P3×5） |
| 设计一致性 | ✅ 与 DEC-173① 方案 A（两层语义、宿主路线图最高「已发布」行）一致；与重派发范围裁决一致——planned_next 已纳入、四步措辞未触碰（commands/change-triage.md L27 原样）、🔄 双语义（不入 marker 集、仅完成词触发）、⏳ 显式豁免 |
| AI 专项 5 项 | ✅ |

## 五、终态结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`

P0=0、P1=0；P2-1 为建议级测试覆盖缺口（可遗留，不阻塞合并）；P3 为讨论/备忘项。通过依据均可复查至文件:行号；运行类验证依赖 Developer 自报（已标注未独立复核），代码层可证性核验全部成立。

## 六、重点审查项 1-8 逐项核实结果（摘要）

1. **⑦ 判定逻辑** — ✅ 判定顺序闭合；「🔄 规划段完成+M-0 裁决完成」→终态词命中非候选（fixture FIX-881）、「🔄 进行中」保持 eligible（fixture FIX-885 对照）；blocking 零变化（`_status_is_completed` 未动，分桶仅由其驱动）。
2. **⑨ 派生函数** — ✅ 形态分支全覆盖（fixture 实证）；版本比较 int 元组语义无排序陷阱且有相邻行回归 fixture；无路线图→跳过下界 fail-safe 成立。
3. **_planned_next_version** — ✅ 三态逻辑正确；`None` 态有测试；「cur 未知」态缺直接用例（P2-1）；FIX-237.4 关键词集合兼容（既有用例结果不变）。
4. **接线** — ✅ 单次读盘 + 纯函数复用同一快照，无重复 I/O/TOCTOU；其余 4 处 `_extract_skill_version` 调用逐一核实为 workflow 版本用途，两层语义下本就不该改。
5. **文档同步** — ✅ commands/change-triage.md L32 四要素逐条与实现比对一致；L39 fail-closed 清单一致；L27 标题未触碰与裁决一致。
6. **测试质量** — ✅ router 验收锚点为实质断言（unblocked==[]、recommended_next==[]、empty_reason kind、渲染输出无 Top pick、Excluded 可见性）；CLI 端到端为真实 subprocess 且经 `--project-root` 真实走通路径。
7. **「✅ 代码完成」判定** — ✅ 既有测试 L458-468 + 新测试 L1102-1113 双重固化；「已完成」无 ✅→non_executable 不解锁——保守正确。
8. **范围纪律** — ✅ FIX-288 全仓检索命中仅落 6 目标文件；FIX-289 3 文件未读未引；工作树整体 diff 面未独立复核（无 Bash），如实标注。

## 遗留项列表

| # | 级别 | 内容 | 关闭节点 |
|---|------|------|---------|
| LP-1 | P2 | 补 `_planned_next_version` cur=None 分支直接用例（同时锁 first-match 回归） | 0.78.1 批次内（建议当轮） |
| LP-2 | P3 | 「未/待完成」类负向前缀豁免评估 | 后续任务（数据形态实证后） |
| LP-3 | P3 | ⏳+终态词混合形态数据卫生备案 | 备案即可 |
| LP-4 | P3 | 「已发布后撤回」假设性复合措辞备忘 | 备案即可 |

## 七、Coordinator 后记（2026-08-28，LP-1 执行时发现——不影响本报告终态结论）

**P2-1 建议示例存在笔误， prose 与实现一致。** 执行 LP-1 时 Developer 发现本报告两处表述矛盾：§一维度5 与 §二 P2-1 的 prose（「cur 未知→取最低规划行」「三态逻辑正确」）与实现一致（change_triage.py L393 `min`）；但 P2-1 建议示例（`current_version=""` + [0.66.2, 0.78.1] 规划行 → 期望 `planned_next="0.78.1"`）按原文写入必然 FAIL——实现对该输入返回 `"0.66.2"`（三次只读运行核实；示例期望值仅在 `current_version="0.66.2"` 输入下成立，疑似该参数笔误为 `""`，但那样就不再覆盖 cur=None 分支）。

**裁决（V-A）**：LP-1 以「行序倒置 fixture + 断言实际行为 0.66.2」的 test-only 形态关闭（覆盖 cur=None 分支 + first-match 回归锁）；本报告终态结论（APPROVED_WITH_NOTES/unresolved_blockers=0）不变。

**附带登记（backlog 候选）**：cur=None 路径 min-overall 语义使「无已发布行宿主 triage 真实下一版本」时对陈旧低版本规划行产生误 WARN——与 ⑨ 已修路径同构的 advisory 级残留（P3）。修复属产品行为面变更（L393 min→max 或 target 感知），按 M7.5 走独立 triage 入槽（0.78.1 为 PATCH 批，不借 test-only 通道夹带），见 EVD-914。
