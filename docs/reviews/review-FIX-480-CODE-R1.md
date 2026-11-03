# review-FIX-480-CODE-R1 — 复审报告（Round 1；R0 引用：docs/reviews/review-FIX-480-CODE-R0.md）

**结论：APPROVED_WITH_NOTES，unresolved_blockers = 0**（通过终态——可进入 commit/证据链收口）。

**审查人**: Code Reviewer（subagent 5445171f-55ed-4fda-820c-faf0b94316ea，与 R0 同一审查者——复审必达 T1）| **日期**: 2026-11-03 | **对象**: FIX-480 修复轮增量（task_priority.py +9 / test_task_priority.py +52）+ 全工作树（12 文件 +597/−79 基线不变）

## P1-1 逐条比对表（R0 → R1）

| R0 发现 | 修复状态 | R1 复证证据（全部亲跑） |
|---|---|---|
| `_build_column_index` 只认 `"ID"`，任务ID 变体无 id 键 → dispatch 漏接 | **已修复** | task_priority.py:1286 `clean in ("ID", "任务ID") and "id" not in idx` → 同一 id 键（R0 建议逐字对症）；`_build_column_index(['任务ID','状态','优先级'])` → `{'id':0,'status':1,'priority':2}` |
| 任务ID 表 status 读备注列（亲测 '里程碑备注'） | **已修复** | R0 同形态脚本复跑：`status='⏳ 进行中'`（语义列）；`assertNotIn("备注", status)` 由新测 2 锁定 |
| target_version 读邻列（亲测 '某目标'） | **已修复** | 复跑：`ver=''`（模板无版本列 → fail-closed 空值）；带版本列 fixture 断言 0.54.2 正确 |
| 零测试覆盖 | **已补** | Fix480TaskIdLedVariantTests 2/2 OK：①R0 亲测点单元锚定（旧代码必 FAIL——R0 实证 keys 无 id）②20 列任务ID 变体四字段语义断言（status/priority/version/deps 含 FIX-502 依赖正向读取）；红面真实性经 R0 实测形态锚定成立 |
| docstring 声称与实现矛盾 | **已修复** | docstring 同步标注「FIX-480 R0 P1-1 — both id-first header labels map to the same "id" key」 |

## 亲跑复证汇总（不轻信声称——全部实测）

- test_task_priority **193/193 OK** ✓（声称吻合）
- Fix480UpgradePathTaskTableTests **9/9** + Fix480TaskIdLedVariantTests **2/2** OK ✓
- test_verify_workflow **全套 1169/1169 OK**（324.6s 实测）✓
- test_archguard_ratchet **38/38 OK** ✓（台账锚与 R0 同值——「零 regen 漂移、无 rider」声称成立；contract_matrix 面包含于 1169 全绿）
- 紧凑基线**三连稳定 rows=69 / completed=54 / non_completed=15**，逐行核验 15 活跃行（FEAT-112 📋/FIX-480 🔄/FIX-470~474/FEAT-105~110/FIX-476/479）completed=False 全部正确——与 R0 测量及 bootstrap 权威（54）一致，**紧凑表零回归** ✓
- 修复轮增量核对：task_priority.py +9 / test_task_priority.py +52，其余 10 文件 stat 与 R0 逐项一致（无夹带）✓

## 新问题检查（R1 要求第 3 项）

- **单一语义键纪律 ✓**：两标签映射同一 `id` 键，无第二语义源；表头检测/`_build_column_index`/docstring 三处口径一致
- **混合表头 first-wins**：`['ID','任务ID','状态']` → id=0（先现者胜）——确定性行为，与既有键（priority/deps/version/status）first-wins 语义一致；单表单 ID 列约定下混用属畸形输入，取首个合理。**P3-4 知悉级注记**（不要求处理）
- 修复未引入新问题（全套绿 + 行为面逐点复证）

## 披露（诚实红线）

- **P3-5**：R1 首测出现过一次 `completed=69` 读数，**无法复现**（紧后三连测+逐行核验稳定 54/15，R0 同口径 54，bootstrap 权威 54）；无法归因（无文件 mtime 证据、无代码路径解释），按单次测量噪声如实披露——零回归判定基于可复现证据链。若后续 Check 1 面再现 69 形态请即复测上报。
- R0 的 P3-1/2/3 维持知悉级（R1 要求第 4 项，未处理不阻塞）；P3-2（Check 1 本仓 69→54 行为变化）建议仍随 commit message 披露一句。

## 裁决

P0=0、P1=0（R0 P1-1 已修复并锁定）、P2=0、P3=5（全部知悉/披露级）→ **APPROVED_WITH_NOTES，unresolved_blockers=0**。FIX-480 修复链两轮收敛（R0 NEEDS_CHANGE → R1 通过），可进入 commit + 证据收口 + 锁释放。
