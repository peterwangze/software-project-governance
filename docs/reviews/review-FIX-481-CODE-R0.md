# Review — FIX-481 独立代码审查（CODE R0）

- **Task**: FIX-481 — `parse_current_active_tasks` 状态列恒读末列 → 表头语义映射（FIX-480 同族第 4 消费面收口，D1 第三轮）
- **Reviewer**: Code Reviewer（独立，未参与开发）
- **Round**: R0（首审）
- **审查对象**: 工作树未提交 diff（`git diff` = 2 文件 +280/−2：verify_workflow.py +81/−2、test_verify_workflow.py +201）；工作树另含 .governance（gitignored）与已提交 version.py pin re-anchor（cf8a3e1），均非本票对象
- **Verdict**: **APPROVED_WITH_NOTES**
- **unresolved_blockers: 0**（P0=0 / P1=0 / P2=0 / P3=5）

## 1. 独立复跑证据（全部本机独立执行，不采信自报）

| 复跑项 | 结果 |
|---|---|
| Fix481 测试类（8 用例） | **8/8 OK**（0.027s） |
| 红相真实性（隔离 worktree @cf8a3e1 pristine 引擎 + 仅拷入新测试，验后清理） | **FAILED (failures=5)** — 与自报「红相 5F」逐字吻合；3 个绿相为既有行为 pin（复合前缀 scope pin/真 active 守卫/紧凑零回归），预期即绿 |
| 本仓 quick 面 | **5 issues 零新增**（FAILED 段含 42 段态翻转——经查为今日 EVD 追加驱动的数据面翻转〔EVD-2202 域〕，非代码回归，见 P3-5） |
| 全套件 test_verify_workflow | **exit 0**（unittest 非零即失败——零退化判定成立；计数见 P3-4） |
| 源码 P5 pin 独立断言 | 委托存在（`parse_task_dependencies(`）✓；函数体无「状态」字面量 ✓；紧凑路径尾部 `status = cells[-1].strip()` 逐字保留 ✓（直接读函数体核实，与绿相 pin 一致） |
| 导入面安全 | tests/ 显式注入 infra 路径（test_verify_workflow.py L34-37）；全仓零包式导入（`infra.verify_workflow` grep 0 hits）——裸名延迟导入在脚本/CI discover 两种模式均安全 ✓ |
| 回退链实证 | `closure_path or title or task_id` @ verify_workflow.py:15405；`closure_path or "Task closure path..."` @ :15494（主张真实；Developer 引用行号偏移，见 P3-1） |

## 2. 五维度结论

1. **正确性 — PASS**：两形状语义映射正确——ID-first 行状态/优先级/标题按表头语义读取（红相 5F 实证旧位置读错），✅ 终态历史行退出 `_active_execution_packet_tasks`（120 假 FAIL 根因面消除），真 active 双向守卫（20 列 `🔄 进行中` P1 仍在 packet 集 + 紧凑 `⏳ 待实施` P1 仍在）；紧凑路径逐字保留（零回归 pin）；delegation 返回空 → skip 与既有 task_idx 守卫同向。理论边界（陈旧表头）为 P3-2，fail-closed 方向。
2. **安全性 — PASS**：纯内部治理文件解析，无外部输入注入面/无密钥/无权限变更；微文档构造无字符串执行。
3. **可维护性 — PASS**：P5 单源合规——语义列（task_id/priority/status/target_version）全部委托 `task_priority.parse_task_dependencies` 公共映射，本地仅保留 title 的表头精确列名查找（display 列，共享映射不暴露该字段——非第二语义索引，源码 pin 钉护「状态」字面量零残留）；docstring 诚实取舍（dependency fail-closed 空/closure_path 空+消费方回退链）。
4. **性能 — PASS**：8 用例 0.027s；逐行微文档委托成本 O(行数 × 2 行解析)，活跃表量级（宿主 39 行/本仓 ~20 行）可忽略；quick 面实测无劣化。
5. **测试覆盖 — PASS**：红面复现/守卫双向/形状变体（裸 ID 引导）/零回归 pin/parity pin（全文档双解析器逐字段对齐）/源码 pin 六类齐备；错误路径（delegation 空→skip）经 `if not dep_rows: continue` 覆盖。

## 3. AI 代码专项 5 项

- mock 残留：无（`patch.object(vw, "SAMPLE_PATH", sp)` 全部为 scoped context manager）
- 硬编码返回值：无（全部由输入计算）
- 幻觉 API：无（`parse_task_dependencies` 为 task_priority.py 真实公共函数；TaskDep 字段 task_id/priority/status/target_version/dependencies 均实存）
- 未实现 TODO：无
- 过度实现：无（范围红线核实——`_is_incomplete_task_status`/`_active_execution_packet_tasks`/Check 18 判定语义/FIX-479 谓词族 diff 中零触碰）

## 4. 设计一致性（ADR/P5）

与 FIX-480 表头语义映射血统一致（第 4 消费面收口）；符合 FIX-292「无第二语义源」——委托而非本地索引；FIX-251 headerless 语义未被重复实现（由共享解析器自治）。

## 5. 发现清单（P0-P3）

| # | 级别 | 位置 | 发现 | 依据 |
|---|---|---|---|---|
| P3-1 | P3 | 报告层 | Developer 引用的回退链行号 L15328/L15417 与实际不符（实际 L15405/L15494，偏移 ~80 行）——**主张真实，引用不精确** | 本审查读码实证（L15405/L15494） |
| P3-2 | P3 | verify_workflow.py parse_current_active_tasks 表头跟踪 | 陈旧表头边界：active 节内 ID-first 表后若紧跟**无表头**任务表（或粗体引导的表头行 `**优先级**` 不入识别集），其行将按陈旧 ID-first 表头语义解析；空状态读取落入 `_is_incomplete_task_status`=True（fail-closed 假阳方向，非过滤漏放），理论上存在错格读到 ✅ 词形的过滤面。无活体形状（FIX-251 headerless 表位于非活跃子节，collecting=False 挂起）。建议：后续 scope pin 或与 FIX-479 P3-2（模块词表散布）合流为词形/形状收敛票 | 代码路径推演 + 表头识别集 `{"优先级","任务ID","ID"}` 无粗体归一 |
| P3-3 | P3 | tests parity pin | parity pin 覆盖 status/target_version/priority 三字段，未覆盖 dependency（ID-first 路径 `",".join(dep.dependencies)` vs 紧凑路径原格文本）——packet 面无 dependency 消费，影响极小 | 测试类 L28551-28579 |
| P3-4 | P3 | 报告层 | 套件计数口径漂移：自报「口径 1181+8」与前轮 Fix479 会话实测 1175（已含 Fix479 6 用例）差 6——本审查以 **exit 0** 为零退化权威判据（成立）；建议后续会话统一计数口径（一次运行只报一个数） | 两次会话运行输出对比 |
| P3-5 | P3 | 观察（非本票） | quick 面 Check 42 段态 UNDETERMINED→FAILED 翻转确认为今日 EVD 追加（EVD-2202 deferred_registration 面）驱动的数据面变化，非 FIX-481 代码回归，Coordinator 收口域披露正确 | 本审查 quick 前后对比 + 段面语义 |

## 6. 已知边界确认（Developer 披露核实）

- `⏳ ✅ committed` 复合前缀在 `_is_incomplete_task_status`→`_status_is_completed_cell` 路径保守判活跃（无装饰剥层）——**两表形状同受的既有行为**，scope pin 用例在册锁定（`test_compound_prefix_packet_verdict_is_fix479_domain`），归 FIX-479/FIX-292 域后续票，本票红线未触碰 ✓
- 宿主 python_game 18 族复跑 120→0 属 Coordinator Layer1 验收域，不在本审查内（诚实边界）

## 7. 结论

**APPROVED_WITH_NOTES，unresolved_blockers=0**。核心修复正确、单源合规、守卫双向、零回归；5 项 P3 全部为报告层精度/理论边界/口径类，无阻塞。建议后续：①P3-2 与既有词表散布票合流评估 ②P3-1/P3-4 类计数与行号引用在 Developer 返回模板中要求「单次运行输出实录」锚定。
