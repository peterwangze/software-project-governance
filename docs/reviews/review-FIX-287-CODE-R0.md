# FIX-287 Code Review R0 — verify_workflow 解析器三缺陷

## 元信息

| 项 | 值 |
|----|----|
| Task | FIX-287（FIX-281②③④，0.78.1 入槽，DEC-173① 方案 A 缺陷面；来源 router 宿主实证 EV-066/071/073） |
| Round | R0（首轮复审） |
| 基线 | 工作树中 FIX-288/FIX-289 已审查通过的未提交改动之上 |
| 范围 | `skills/software-project-governance/infra/verify_workflow.py`（5 hunk，+95）+ `skills/software-project-governance/infra/tests/test_verify_workflow.py`（+194，`Fix287ParserBoundaryTests` L8904-9095） |
| Reviewer | Code Reviewer Agent（只读：Read/Grep/Glob；未调用 Write/Edit/Bash/AskUserQuestion） |
| 审查依据 | `agents/code-reviewer.md` + `skills/code-review/SKILL.md`（已读仓库原文复核） |
| Date | 2026-08-28（Reviewer 无时钟访问，Coordinator 落盘时补记） |

## 终态结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`

（P0=0 且 P1=0；P2×3/P3×7 全部为非阻塞遗留候选。满足 code-review SKILL「循环角色」段通过终态契约：无未解决 BLOCKING finding，含独立结构字段 `unresolved_blockers=0`。）

## 发现计数

| P0 | P1 | P2 | P3 |
|----|----|----|----|
| 0 | 0 | 3 | 7 |

## 5 维度逐项结论表

| 维度 | 结论 | 关键事实（可复查） |
|------|------|---------|
| 正确性 | ✅ 通过（附 P2 非阻塞建议） | ② 列索引公式逐边界验算正确（6→5 / 20→9 / 10→9 / None→9 / 未知→9）；status_index 每文件解析一次（L9317），行级守卫 `status_index < len(parts)`（L9330）防 IndexError；③ 状态机 `## ` break 充分（下一顶级节按定义在活跃节之外），`### ` 挂起/恢复顺序容忍；④ `parse_gate_statuses` L9618-9620 证实为薄包装 `return parse_gate_status()`，单点覆盖成立 |
| 安全性 | ✅ 通过 | 纯只读解析器；无 eval/exec/shell/SQL；文件读取显式 UTF-8；正则输入有界（`^(?:\*\*)?[A-Z]+-\d+(?:\*\*)?$`）；无敏感数据。OWASP 关键面：不适用（本地 CLI） |
| 可维护性 | ✅ 通过（附遗留候选） | 新助手命名清晰、docstring 标注 FIX-287②③④；复用权威源 `_PROFILE_TASK_COLUMNS`（L13747）未新立列数真相；遗留：状态列解析策略现存 3 套并存（F-3）、兄弟函数 `_plan_task_ids_from_hot_tracker` 未同步泛化（F-2） |
| 性能 | ✅ 通过 | ③ 单遍 O(n) 状态机；② `_plan_profile` 每次调用多读一次 plan-tracker（L9302+L9316 共 2 次全读），文件受 Check 28s 200KB 守护，调用点少——可忽略（F-9） |
| 测试覆盖 | ✅ 通过 | 10 用例断言实质（精确 ID 列表/计数，非 smoke）；红相 6 FAIL 声明与用例设计逐例推演吻合（②lightweight + ③×2 + ④×3，其余 4 例为双相守卫）；红相本身未复跑（无 Bash 权限）→「设计层可证、执行层未验证」，绿相由 Coordinator 亲测 exit 0 记录在案 |

## 发现列表（全部非阻塞）

| # | 级别 | 位置 | 事实依据 | 建议 | 处置 |
|---|------|------|---------|------|------|
| F-1 | P2 | verify_workflow.py L7377-7381 | `startswith("## Gate 状态跟踪")` 过度匹配：第二个异后缀顶级节（如 `## Gate 状态跟踪（历史归档）`）命中 L7377 `continue` 先于 L7380 break，其表格行会被并入门 Gates 列表；若该节在正版之前则正版被截断。仅非规范布局可触发（模板仅一个 Gate 节）；且多余行会被 Check 23 gate_rows 计数比对（L13818-13825）自行暴露，失败方向为可见而非静默 | 收紧变体模式（如 `^## Gate 状态跟踪(?:\s*[（(][^#）)]*[）)])?$`），或遇 `## ` 且非本节族标题一律 break | 遗留候选（不阻塞） |
| F-2 | P2 | verify_workflow.py L11743-11764 | 同族遗留：`_plan_task_ids_from_hot_tracker()` 仍为旧边界语义（仅 `### 最近完成` break、无 `## ` 终止、无挂起/恢复）——EV-071 型布局（最近完成前置）下返回空集，致 `parse_impact_analysis_entries` 的 `product_delivery_by_current_task_type`（L11990）欠检出（有 L11988 路径兜底，不至静默放行全部）。属 ③ 缺陷族但非本 diff 引入的回归 | 登记为后续候选：统一复用 `parse_current_active_tasks` 边界状态机或抽取共享扫描器 | 遗留候选（不阻塞） |
| F-3 | P2 | verify_workflow.py L9330 | ② 状态语义词为精确等值 `== "已完成"`，与兄弟解析器词表不一致（`parse_task_stats` 经 `_normalize_task_status` 接受 ✅ 等变体；③ 侧 `_is_incomplete_task_status` 接受「✅ 完成 (date)」）。热表若写 `✅ 已完成` 或带日期后缀会被静默欠采集，削弱证据完备性检查方向。两真实 tracker 等价实证（0→0）说明当前无分歧 | 对齐 `_normalize_task_status` 词表或在注释中明示精确匹配取舍 | 遗留候选（不阻塞） |
| F-4 | P3 | verify_workflow.py L9323-9327 | 行 ID 泛化（任意单元格精确 task-ID）理论误纳面：需同时满足「某非任务行含裸 ID 格单元格 + 状态列恰为已完成」；最左匹配保证规范表形（ID 列恒在最左）取自身 ID；消费方方向（L11402-11403 `missing_evd ⊆ hot_completed`）使过采集体现在更严检查——fail-closed 方向 | 无需修改；保持精确状态等值即可 | 关闭（评审记录） |
| F-5 | P3 | verify_workflow.py L13760-13764 | 中间形态 idx（expected_cols=7/8/9→6/7/8）无实证宿主（`_PROFILE_TASK_COLUMNS` 仅 6/20）；「状态列=末列」假设已对照模板核实成立（core/templates/plan-tracker.md L51-53：6 列、状态末列）。未知 profile→idx9 与 Check 23 未知 profile 显式拒绝（L13808-13811）设计自洽（检查器报错、解析器兜底） | 保留现状；死分支无害且单调安全 | 关闭（评审记录） |
| F-6 | P3 | verify_workflow.py L11896 | ③ 活跃节入口识别保持精确前缀 `## 当前活跃事项`（未随 ④ 泛化）——带括号后缀的活跃节标题将使 ③ 整体失效。属既有语义、不在申报范围 | 与边缘问题 7（parse_overview/parse_project_config 精确匹配同族）一并登记候选 | 遗留候选（讨论级） |
| F-7 | P3 | verify_workflow.py L11879-11884 | 标题*包含*排除子串的保守取舍成立（如「阻塞依赖链分析」误挂起）：欠采集由 `parse_resume_state` 的 session-snapshot 兜底（L8737-8738）缓解；精确等值标题会重新引入 ④ 所修的括号变体问题 | 无需修改 | 关闭（评审记录） |
| F-8 | P3 | test_verify_workflow.py L8948-8966 | standard 守卫用例使用 10 可见列 fixture（`_TASK_COLS`，L287）而非规范 20 列标准表；所测不变量（standard→idx9）仍被真实行使，列数一致性本归 Check 23 管辖。轻微真实感缺口 | 后续可补 20 列变体或加注释说明 | 遗留候选（讨论级） |
| F-9 | P3 | verify_workflow.py L9302 | `parse_project_config` 每次调用重新读盘：`get_all_completed_task_entries` 每次 2 次全读 plan-tracker。I/O 量级可忽略、单进程 CLI 无一致性风险 | 无需修改 | 关闭（评审记录） |
| F-10 | P3 | verify_workflow.py L9317 | 性能正向确认：status_index 文件级一次解析、③ 单遍扫描，无逐行重复解析 | — | 关闭（评审记录） |

## AI 代码专项 5 项

| 检查项 | 结论 | 事实依据 |
|--------|------|---------|
| Mock 残留 | ✅ 无 | 测试用 tempfile+`patch.object(vw, "SAMPLE_PATH")`（正规手段）；产品代码无 mock |
| 硬编码返回值 | ✅ 无 | 唯一常量 `_LEGACY_TASK_STATUS_COLUMN=9`（L13757）溯源至 FIX-038 权威表 `_PROFILE_TASK_COLUMNS`（L13747）与 legacy 20 列格式 |
| 幻觉 API | ✅ 无 | 逐引用核实：`_split_markdown_table_row`(L328)、`parse_project_config`(L7352)、`_PROFILE_TASK_COLUMNS`(L13747)、`_governance_table_cells`(L11857)、stdlib re/Path 全部存在 |
| 未实现 TODO | ✅ 无 | hunk 内注释均为 FIX-287 说明性标记，无 TODO/FIXME/占位 |
| 过度实现 | ✅ 无 | startswith 容差与子串标记均为对应实证（EV-066/071/073）的最小泛化；无投机配置项；7/8/9 死分支系公式固有而非多余机制 |

## 硬门槛裁决

| 门槛 | 阈值 | 裁决 |
|------|------|------|
| P0 阻塞问题数 | = 0 | ✅（0 条） |
| 5 维度全覆盖 | = 100% | ✅ |
| 每条发现标注级别 | = 100% | ✅（10 条，P2×3/P3×7 全部带级别） |
| 设计一致性 | 已完成 | ✅——与 FIX-281②③④ 申报语义逐 hunk 对应；符合 DEC-173① 方案 A 缺陷面；profile 列数以 `_PROFILE_TASK_COLUMNS` 唯一权威源复用；`_plan_profile` 的 profile 提取正则（L9303）与权威消费方 Check 23（L13798）逐字符一致 |
| AI 代码专项 5 项检查 | 全部完成 | ✅ |

## 重点审查项 1-8 逐项核实

1. **列索引公式**：✅ 正确。None/>9→9；6→5；20→9；10→9；7/8/9→6/7/8（无实证宿主，F-5 登记）。末列假设与 core/templates/plan-tracker.md L51-53 模板核实一致；standard=20 与 Check 23 期望（L13815）一致。
2. **行 ID 泛化风险**：✅ 可接受（F-4）。状态语义词限定为精确 `"已完成"`（L9330）足够窄；最左匹配 + 规范表形 ID 列最左；误纳方向 fail-closed。
3. **parse_project_config 兼容性**：✅。签名 `path=None`（L7352）保持默认 SAMPLE_PATH；4 个零参调用点逐一核实不受影响（L8901 `build_delivery_trust_snapshot`、L10567 `cmd_status`、L12034 goal 检查、L13795 Check 23）。
4. **③ 状态机**：✅。`## ` break 充分；挂起/恢复子串匹配保守方向可接受（F-7，含快照兜底）；`## 当前活跃事项` 入口保持原精确逻辑未泛化（F-6 登记，范围纪律正确）。
5. **④ 前缀匹配**：✅ 目的达成；过度匹配为理论情形且被 Check 23 计数自暴露（F-1）。包装函数核实为薄代理（L9618-9620）；同族存在性检查 L4011 用 `in` 本就容忍后缀，无需修。
6. **测试质量**：✅。10 用例断言实质；红相 6 FAIL 与用例推演逐例吻合；4 守卫用例锁住兼容面。红相执行未复跑——「未验证（执行层）」，绿相 exit 0 由 Coordinator 亲测。
7. **等价性声明可证性**：② 0→0 可由代码构造直接证明（standard→idx9≡legacy 9 恒等）；③ 170=170 逻辑层自洽但执行层未复现——「未验证」；④ 11=11 由 startswith⊇exact 构造保证；check-governance 17 行 diff 为基线伪影——「未验证」。
8. **范围纪律**：✅。6 处 FIX-287 标记精确落在申报 5 hunk（L7376/9307/11877/11903/11906/13753）；archive 路径 `parts[9]`（L9354）确认未顺带修；F-2 为本审查新识别候选，非越界指控；FIX-288 区域未读、未作为依据。局限：无 git diff 复核（角色禁 Bash）。

## 未验证项声明

- **红相 6 FAIL 复跑**：未验证（执行层）——红绿对应关系已由用例设计逐例推演建立。
- **③170=170 双向差集、check-governance diff 17 行基线伪影**：未验证（执行层，审查角色无 Bash 权限）；② 0→0 与 ④ 11=11 可由代码构造直接证明。
- **绿相 Fix287ParserBoundaryTests exit 0**：依据 Coordinator 亲测记录（非本审查者复跑）。
- **Date 字段**：未标注（无时钟访问，禁止编造），由落盘时补记（2026-08-28）。

## 遗留项表（均不阻塞合并）

| # | 级别 | 内容 | 关闭建议 |
|---|------|------|---------|
| F-1 | P2 | parse_gate_status 前缀匹配收紧 | 后续修复任务（可与边缘问题 7 同族合并处理） |
| F-2 | P2 | `_plan_task_ids_from_hot_tracker` 旧边界语义统一 | 后续修复任务（复用 ③ 状态机或抽取共享扫描器） |
| F-3 | P2 | ② 状态词表与 `_normalize_task_status` 对齐 | 后续修复任务或注释明示取舍 |
| F-6 | P3 | `## 当前活跃事项` 入口识别泛化 | 与边缘问题 7 一并登记候选 |
| F-8 | P3 | standard 守卫用例 20 列 fixture 真实感 | 测试增强候选 |
