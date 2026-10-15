# FIX-443 Code Review R0 — 运行时声明扫描性能修复（原门限保持）

- **轮次**: R0（初审）
- **审查方**: Code Reviewer Agent（只读审查；唯一写面 = 本报告；未修改产品/测试/治理，未 commit）
- **审查对象绑定**: HEAD `bf6942dd9b961a7f707db295171b1f2c8bc3c21c`（staged 空）；工作区 diff `checks/loop_runtime_claims.py` blob `d2162ac→26ae776`（117+/75−）+ `tests/test_loop_runtime_claims.py` blob `1e46133→41441cc`（66+/0−）——合计 **183+/75−，与申报精确一致**；triage 第三允许文件 `test_verify_workflow.py` 零改动（符合「不需要就不要冗余改动」）
- **需求源**: user-named（DEC-333——用户在 FEAT-097 R5 BLOCKED 升级后明确选择原门限有界修复，change-triage/FIX-443.json `demand_basis` 机录）
- **结论**: **APPROVED_WITH_NOTES**

```json
{"unresolved_blockers": 0}
```

---

## 0. 结论与理由

三处变更**逐行等价 + 资源寿命缺陷真实消除 + 回归看护真实咬合 + 原门守卫独立复验全绿**：①`_json_accounting`/`_json_units` 两个自引用 `walk` 闭包提升为模块级 `_json_walk`/`_json_units_walk`（显式参数替代 cell——遍历序/发射序/叶逻辑/schema roles/pointer/locator 逐字不变）；②`_python_accounting` 的递归 `container_chain` 改迭代（限定祖先跳步、cache 条目、元组构成序逐一等价——我按 diff 内旧码 verbatim 逐行比对）；③新回归 `test_accounting_passes_leave_no_reference_cycles`（unreachable==0 断言，finally 复原 GC）旧码 3 subfail→新码 GREEN（Developer C1/C2 + 我独立复跑 GREEN）。**原 CPU 守卫（原断言 median<27.8、原 in-process 形态）与原 CLI 目标（timeout=36）经我固定一次独立运行全部 OK**。扫描输出等价性有硬证据：修复前后真实语料身份四元组恒等（1128/24,679,503/332,948/`fb1b0cbf…`）。

无阻塞 finding；备注见 §4。`unresolved_blockers=0`。

---

## 1. 变更逐项核验（验收 ①）

| # | 变更 | 等价性判定 | 证据 |
|---|------|-----------|------|
| 1 | `_json_walk` 模块级化（原 `_json_accounting` 内嵌 `walk`） | **等价** | diff 内旧体 verbatim 对照新体：dict 分支（child_pointer f-string/emit json_key/key_context/递归）、list 分支（enumerate/json_array_index）、五叶分支（json_string/json_number/json_boolean "true"/"false"/json_null）、`raise ValueError("unsupported JSON value")` 失败路径——**逐字相同**；调用点 `walk(data,"",[])`→`_json_walk(data,"",[],emit=…,escaped=…,checked_string=…)` 同参；emit/escaped/checked_string 以参数传入=原闭包捕获的同一对象；**遍历与发射顺序不变**（json_key 先发再递归） |
| 2 | `container_chain` 递归→迭代 | **等价** | 旧：入口查 cache→向上跳非 (ClassDef/FunctionDef/AsyncFunctionDef) 祖先→`(*container_chain(outer), ctx)` 逐帧缓存。新：ancestry 自 container 向上收集（逐节点先查 cache 命中即断）、`reversed(ancestry)` 自最外向内 `prefix=(*prefix,ctx)` 并逐节点缓存——**cache 条目集合、元组构成序（外→内）、限定祖先跳步 while 条件、py_class/py_function 分支全部相同**；入口命中快路径等价（ancestry 空→返回 cached）；返回值=原 container 的元组 ✓。消除自引用后闭包仅捕获 parents/container_cache（无回指→无环） |
| 3 | `_json_units_walk` 模块级化（原 `_json_units` 内嵌 `walk`） | **等价** | 六叶判定集（state/status/mode/capability/readiness/activation casefold）、loop_context `any(hint(context[:-1]))`、assertion 三析取（SUBJECT_PATTERNS ∪ {runtime_activation,migration_validity} ∪ state_field∧loop_context）、content f-string、policy 7 键/authority 12 键/exemptions schema_role、`_claim_potential_hint` 门、unit 字段（locator (1,0,1,0)/kind/`json_schema_role`∨`json_pointer:{pointer}`/context）——**逐字相同**；调用点同参（默认 parent_key=""/context=() 保持） |
| 4 | 无越面 | **确认** | 无新文件；无全局 GC/trace 操纵；无跨扫缓存；无 skip/truncate；门限/形态零触碰（guard 测试体未在 diff 中——仅前插新用例；`test_verify_workflow.py` 0 改动→timeout=36 与 semantic 434339/32MiB 断言原样） |
| 5 | 扫描输出等价（真实语料） | **硬证据** | C4（11:46:52Z，隔离回执）：修复后 fresh 扫 idx-tree 身份 `1128/24,679,503/332,948/fb1b0cbf202cd…`——与 R5 期修复前身份**恒等**（command-replay :52 vs R5 shapeI.json :13-14）→ 单位/候选/inventory SHA 三面不变 |

## 2. 回归看护真实性（验收 ②）

- **真咬合**：旧码下三 pass 各留 function↔cell 环（含 `container_chain` 整棵 AST 保留）→ `gc.collect()` 计数>0 → RED（Developer C1：`FAILED (failures=3)`，可见 tail `json_units left 9 object(s)`）；新码 unreachable==0 → GREEN（C2 + 我独立复跑）。若闭包回归即红——非镜像断言。
- **GC 纪律**：测试内 quiesce collect→`gc.disable()`→测 collect→**`finally: if auto: gc.enable()`**（先存 `auto`，正确复原）；性能守卫本体（:1086-1173）无任何 gc 操纵——GC 操纵不泄入性能面。
- **脆弱性评估**：方法依赖 CPython refcount+gc 语义（P3-F0-1）；json_units 空[]豁免有注释依据（hint-gated）；subTest 独立 goal 语义正确。

## 3. 原门守卫独立复验（验收 ③④——我固定一次运行）

| 目标 | 命令（wrapper receipt 机录） | UTC | exit | 结果 |
|------|------------------------------|-----|------|------|
| 原 CPU 守卫 | `unittest …-k three_run_performance_identity_and_median -q`（原断言 median<27.8/原形态） | 11:58:06.86Z→11:59:03.45Z | 0 | **Ran 1 test in 56.314s — OK**（三读数/中位未提取=unknown，不补测不改计数器） |
| 原 CLI 目标 | `unittest test_verify_workflow.LoopRuntimeClaimAdapterTests.test_claim_command_emits_complete_pass_report -q`（timeout=36 原样） | 11:59:03.48Z→11:59:24.65Z | 0 | **Ran 1 test in 20.874s — OK**（36s 内；原 RC0/PASS/parsed/skipped0/truncated0 断言全过） |
| 新回归 | `-k test_accounting_passes_leave_no_reference_cycles -v`（我方五变量隔离） | 12:00:02.30Z→12:00:02.61Z | 0 | **Ran 1 test in 0.011s — OK** |

Wrapper 隔离回执：isolation_root `sg-323344bb`（五变量重定向，rawlog guards-1/2.log 落盘）；我外层命令 11:58:06.38Z→11:59:24.69Z exit 0；B 独立隔离 `fix443-r0-rev-3f22dc09`。

## 4. 备注（非阻塞）

- **P3-F0-1**：新回归依赖 CPython refcount/gc 语义（PyPy 等无 refcount 实现下行为不同）——仓内工具链已 CPython 假设（锚定/守卫同），可接受，注记即可。
- **P3-F0-2**：C1（旧码 RED）两个 sub 失败明细与计数被 `Select-Last 22` 截断=unknown（failures=3 证三 sub 全红；json_units=9 为唯一捕获计数）——已在 command-replay `raw_output_caveat` 如实披露；不影响判定（RED 事实由 failures=3+可见行证实）。
- **P3-F0-3**：C4 单样本 15.125s 为 fresh 形态、不可与 ~35 期不同形态做因果比例（command-replay `interpretation_guard` 已自限）；本修复的机制证据=回归测试（环存在→消除）+ 守卫转绿，非单样本对比。
- **边界**：`-Mode semantic`（reliability/security 面）与全量 1115 不在本轮我的授权内（执行包 next_commands 归 Developer/Coordinator）；本报告不宣称。

## 5. 五维度 + AI 专项（硬门槛 ②⑤）

| 维度 | 结论 |
|------|------|
| 正确性 | **PASS**——三变更逐行等价（§1）；真实语料输出恒等（§1-5） |
| 安全性 | **PASS**——fail-closed 路径/失败消息逐字保留；无 skip/truncate/门限触碰 |
| 可维护性 | **PASS**——模块级函数+显式参数优于闭包自引用；注释锚定 FIX-443 因果；diff 纯粹（2 文件恰票面） |
| 性能 | **PASS**——原门守卫独立复验双绿；机制=消除 per-candidate 环垃圾（回归直证） |
| 测试覆盖 | **PASS（带 P3-F0-1/2）**——新回归真咬合 red→green；65 模块测（Developer C3，176.524s OK）含原守卫 |

AI 专项：mock 残留**无**（patch 仅既有 spy 用例）；硬编码**无**（键集为既有 schema 契约常量）；幻觉 API**无**（gc API/ast 类型均真实；C1 曾因 wrapper API 笔误零扫描失败=过程诚实）；TODO**无**；过度实现**无**（恰三处必要面）。

## 6. 硬门槛自检

P0=0 ✓｜5 维 100% ✓｜发现全带级+位置+事实+建议 ✓｜设计一致性（执行包 non_goals：不调限额/不 fresh 替代/不全局 GC——diff 全符合）✓｜AI 5 项 ✓｜事实红线（等价判定基于 diff verbatim 对照；uncaptured 数字全部 unknown 不编造）✓

## 7. 机录参数

`review-record --task FIX-443 --round 0 --result APPROVED_WITH_NOTES --report docs/reviews/review-FIX-443-CODE-R0.md --reviewer 'Code Reviewer'`（AWN/0 为通过终态）。后续：`-Mode semantic` 与 Coordinator 唯一全量 1115 跑归流水线，非本审查面。
