# AUDIT-144 诊断报告：已完成任务（叙述段/归档）对 task-priority-analysis 解析器不可见——根因与处置方案

- **Task ID**: AUDIT-144（P2，只读调查，无产品代码修改）
- **调查日期**: 2026-08-22
- **执行者**: Analyst sub-agent（治理记录快速通道）
- **数据基线**: plan-tracker.md 0.75.0 会话态；EVD-899（2026-08-22 task-priority-analysis 快照：141 tasks / 137 completed / 0 unblocked / 4 blocked / 0 non-executable；REQ-110 fallback 推荐 `Unblock pick: AUDIT-124 [P9] (unknown_dependency)`，解锁 3 下游 FIX-155/FIX-156/REL-047）
- **方法**: 文件直读 + Grep（Bash 禁止）；所有行号引用均经 Read 验证；代码行为推演均标注"推演，待实跑验证"

---

## 摘要（四问一句话版）

1. **根因链**：`task_priority.py` 的唯一数据源是 plan-tracker.md 文本（purity contract）；状态机把叙述段 prose 行显式跳过；AUDIT-124 的热任务表行已于 2026-06-28（FIX-157 归档）迁出至 archive，归档文件与 archive/index.md 不在解析数据源内 → `status_map`/`task_index` 无 AUDIT-124 → `compute_unblocked_tasks` L1367 `status_map.get(dep, False)` 默认 False（fail-closed）→ fallback `_walk_blocker_roots` L1080-1083 归为 `unknown_dependency`。
2. **全量盘点**：当前 live 活跃（非 ✅）任务行共 5 行，其中依赖引用"无热任务表行"的 task-family ID 共 **2 个**：**AUDIT-124**（归档任务子类，被 FIX-155/156/REL-047 三行引用）与 **REQ-112**（需求实体子类，被 VAL-010 引用；性质不同，见 §3.2）。除 AUDIT-144 自身外无其他活跃行。
3. **三案对比**：(a) 热表指针行——成本 1 文件 +1 行、解析器零改动、双先例（FIX-257 形态 A + hot-fact-source 指针表 L244-257）、完全可逆；(b) 解析器归档/叙述段感知——成本 3-5 文件，破坏 purity contract，叙述段方案重蹈 FIX-251/252 已定性的自由文本解析根因；(c) 维持现状——零成本但推荐持续含事实错误且依赖每会话人工披露（与 AUDIT-143 注入层教训同构）。
4. **立项建议**：立项**治理记录对账任务（快速通道，非产品代码）**，形态 (a)：为 AUDIT-124 补 1 行指针行。REQ-112 子类不适用指针行，登记为已知盲区（其阻塞语义目前治理上正确）。验收红→绿样例见 §6.3。

---

## 1. 调查问题 1：根因链（代码级定位）

### 1.1 数据源：解析器只读 plan-tracker.md 文本，不读归档、不读叙述段以外的任何结构

- **Purity contract（模块 docstring L45-51）**：`task_priority.py` 只 import 标准库；`parse_task_dependencies` / `compute_unblocked_tasks` / `format_report` 无文件 I/O、无模块级可变状态；**"The CLI entry in `verify_workflow.py` is the only place that reads `plan-tracker.md` from disk; it passes the file *text* to `parse_task_dependencies`"**（L48-50）。
- `parse_task_dependencies` 的唯一读文件通道是入参为 path-like 时的便利读取（L549-553、L792-794），读取对象仍是 plan-tracker 本身。`archive/index.md`、`archive/tasks/*.md`、需求跟踪矩阵以外的任何治理文件**均不在数据源内**——这不是 bug，是 FIX-226 设计决策（可测试性/确定性）。

### 1.2 任务行识别：两类表格，叙述段被状态机显式跳过

`parse_task_dependencies`（L546-694）逐行状态机：

| 代码位置 | 行为 |
|---|---|
| L619-624 | 标题行（`#` 开头）结束当前表、置 `after_heading` |
| **L636-645** | **非空且非 `|` 开头的行（= 叙述段 prose）→ 结束表格、清标志、`continue` 跳过**——L59/L60 的叙述段从不进入任何数据结构 |
| L648-649 | 分隔行（`\|---\|`）跳过 |
| L660-665 | 表头识别：`cells[0]=="优先级" and cells[1]=="ID"`（覆盖 `### 优先级一览` 表与 `### 已归档版本 task` 指针表，docstring L563-566） |
| L676-681 | headerless 表识别（FIX-251）：`after_heading` + `_is_headerless_task_row` 形状检测（≥5 列 + 裸 ID 单元格 + 状态 emoji 单元格，L322-354）——覆盖 `### 最近完成（本会话提交窗口）` |
| L686-692 | 行解析（ID-anchored，L820-911：依赖列 = ID+2、状态 = 最后非空 cell）+ 按 task_id 去重保留首见 |

**叙述段不可见的第一层原因**：叙述段是 prose（`**2026-06-27 DEC-088 …**：…`），命中 L636-645 被跳过。即使叙述段含"任务分解 AUDIT-124（诊断，完成）"（plan-tracker L60）这类完成事实，解析器也从不将其计入 `status_map`。

### 1.3 依赖解析：AUDIT-124 从 FIX-155 行的依赖列进入 task-family 依赖

- `_parse_dependency_cell`（L357-388）用 `_ID_TOKEN_RE`（L118，负向后视防 `REVIEW-FIX-155` 误拆）从依赖列提取 PREFIX-NNN token；`_is_task_family_id`（L123-139）按 `_TASK_FAMILY_PREFIXES`（L97-101）分类——`AUDIT` 在 task-family 集合内。
- 实测行：FIX-155（plan-tracker L78）依赖列 `AUDIT-124, DEC-088, DEC-085/086/087(授权沿用), RISK-039` → task_family=(AUDIT-124)，cross_entity=(DEC-088, DEC-085, DEC-086, DEC-087, RISK-039)。FIX-156（L79）→ (FIX-155, AUDIT-124)；REL-047（L80）→ (FIX-155, FIX-156, AUDIT-124)（行内 `FIX-155✅`/`AUDIT-124✅` 的 ✅ 是依赖状态提示，被 strip 只留 ID，L363-364 注释）。

### 1.4 fail-closed 判定分支（AUDIT-124 归为 unknown_dependency 的精确位置）

两个层面：

**(1) blocked 分类层**——`compute_unblocked_tasks`（L1306-1405）：

```python
L1351  status_map: dict = {t.task_id: t.is_completed() for t in tasks}
L1366      for dep in t.dependencies:
L1367          if status_map.get(dep, False):   # ← AUDIT-124 无表行 → 默认 False
L1368              continue
L1370          # Dependency is either incomplete (in table, non-✅) or unknown
L1371          # (missing from table). Either way it blocks fail-closed.
L1372          blocking.append(dep)
```

`status_map` 的键 = 全部**表内** task_id。AUDIT-124 无表行 → `get` 落默认值 False → "不可证明完成 → 阻塞"（docstring L1316-1319 与 `BlockedTask` L427-433 同义：unknown task-family ID cannot be proven complete, so it blocks fail-closed — FIX-171 conservative default）。于是 FIX-155 `blocking_dependencies=(AUDIT-124,)`。

**(2) fallback 根因层**——REQ-110/FIX-254 空推荐降级链：

```python
L1288  blocked_map = {bt.task.task_id: tuple(bt.blocking_dependencies) ...}
L1289  task_index: dict = {t.task_id: t for t in non_executable}
L1291      task_index[bt.task.task_id] = bt.task        # 仅表内行
...
L1080      blocker = task_index.get(dep)
L1081      if blocker is None:
L1082          roots.setdefault((dep, _ROOT_KIND_UNKNOWN), set()).add(origin_id)
```

`_ROOT_KIND_UNKNOWN = "unknown_dependency"`（L998）。`_unblock_reason`（L1107-1112）生成 EVD-899 引用的原文文案："data gap: `AUDIT-124` is a task-family dependency with no row in the plan-tracker (fail-closed — it cannot be proven complete); verify or record its completion to reopen the chain"。`_pick_unblock_recommendation`（L1125+）按下游解锁数排序：roots = {(AUDIT-124, unknown): {FIX-155, FIX-156, REL-047}=3, (REQ-112, unknown): {VAL-010}=1} → **pick AUDIT-124（3 下游）**——与 EVD-899 / FIX-258.json L578 实测输出逐字吻合。

### 1.5 为什么热文件里没有 AUDIT-124 的任务表行（历史层）

- AUDIT-124（verify_workflow.py 20321 行膨胀根因诊断）完成于 2026-06-27，完成事实现存三处：
  1. **归档任务表行**：`archive/tasks/completed-tasks-2026-04-30_2026-06-27.md` L153——完整 7 列行，状态 `✅ 诊断完成 (2026-06-27)`，目标版本 0.61.0；
  2. **归档索引**：`archive/index.md` L148——`| AUDIT-124 | 诊断完成 (2026-06-27) | 0.61.0 | archive/tasks/completed-tasks-2026-04-30_2026-06-27.md |`；
  3. **热叙述段**：plan-tracker L60"任务分解 AUDIT-124（诊断，完成）→ FIX-155 → FIX-156 → REL-047"（L59 停滞叙述亦提及）。
- **推断 H1（待验证，见 §7）**：AUDIT-124 曾有热任务表行，2026-06-28 FIX-157 归档迁移（plan-tracker L48-52 注记"历史事项已归档（FIX-157，2026-06-28）…已完成 task 表 → archive/tasks/completed-tasks-2026-04-30_2026-06-27.md"）将其随 2026-04-30~2026-06-27 窗口的已完成行一并迁出；其完成日期恰在归档窗口内。归档未留指针行——不同于 0.38.0 链 FIX-082~087/REL-013 因 `check-hot-fact-source` 要求保留的指针表（L244-257）。
- **结论**：任务背景所称"热叙述段盲区变体"在数据层实为 **FIX-257 登记的死链类别 #2 标准形态**（"已归档完成任务的依赖行对解析器不可见"）——叙述段 L60 只是同一完成事实的冗余记载；根本事实是**归档迁移移走了表行且无指针行残留，而解析器数据源单一**。三类完成记载（归档行/索引/叙述段）对解析器全部不可见：前两者不在数据源，第三者被 prose 跳过。

---

## 2. 调查问题 2：全量盘点（live 数据系统扫描）

### 2.1 盘点方法

1. 通读 plan-tracker 全部任务表（`### 优先级一览` L76-228、`### 最近完成（本会话提交窗口）` L230-240、`### 已归档版本 task` 指针表 L249-257），枚举所有**活跃（状态非 ✅）行**及其依赖列 task-family ID；
2. 对每个被引用 ID 反查热任务表是否有行（表头驱动表 + headerless 窗口表 + 指针表，即解析器全部三类可见表）；
3. 无表行者，反查 `archive/index.md` Task 索引、归档任务文件、热叙述段、需求跟踪矩阵定位完成/状态事实；
4. 与解析器实测输出（FIX-258.json L578 report_text、EVD-899）对账验证。

### 2.2 活跃行依赖全景（5 行）

| 活跃行 | 位置 | 状态 | task-family 依赖 | 依赖可解析性 |
|---|---|---|---|---|
| FIX-155 | L78 | ⏸ 停滞待重新评估 | AUDIT-124 | **AUDIT-124 无表行 ❌** |
| FIX-156 | L79 | ⏸ | FIX-155, AUDIT-124 | FIX-155 表内（⏸ 非完成，真实阻塞）；AUDIT-124 ❌ |
| REL-047 | L80 | ⏸ 停滞/被 REL-048 取代 | FIX-155, FIX-156, AUDIT-124 | 前两者表内；AUDIT-124 ❌ |
| VAL-010 | L224 | 🔄 进行中 | FIX-253, REQ-112 | FIX-253 表内 ✅；**REQ-112 无任务表行 ❌** |
| AUDIT-144 | L228 | 🔄 进行中 | FIX-257, FIX-171 | 均表内 ✅，无盲区 |

与 EVD-899 对账：快照时 AUDIT-144 行尚不存在（快照先于任务创建运行），故 4 blocked / 0 unblocked 与上表一致；当前时点 AUDIT-144 行存在且依赖满足、状态 🔄（不在 non-candidate marker 集 L202-204）→ 属 unblocked——即 AUDIT-124 噪声推荐只出现在"无其他 unblocked 任务"的窗口（fallback 仅在 `recommended_next == []` 时触发，L515-519）。

### 2.3 盲区 ID 清单（2 个，分属两个子类）

**实例 1：AUDIT-124（归档任务子类——本调查主对象）**

- 被引用行：FIX-155（L78）、FIX-156（L79）、REL-047（L80）。
- 完成事实验证方法（三源独立可复核）：
  - `archive/index.md` L148（Task 索引行，状态"诊断完成 (2026-06-27)"，版本 0.61.0，指向归档文件）；
  - `archive/tasks/completed-tasks-2026-04-30_2026-06-27.md` L153（完整任务表行，`✅ 诊断完成 (2026-06-27)`，闭环路径注明"详见 EVD-630"）；
  - 热叙述段 plan-tracker L60（"任务分解 AUDIT-124（诊断，完成）"）。
  - 佐证：EVD-630 归档于 `archive/evidence/evidence-v0.1.0-0.61.2.md` L23（诊断证据行）；`archive/index.md` L568-569 Evidence 索引同指。

**实例 2：REQ-112（需求实体子类——同症状、不同病理）**

- 被引用行：VAL-010（L224，依赖列 `FIX-253✅, EVD-897✅(CE), REQ-112, DEC-143/144(CE), 设计§9.2`）。
- 状态事实：需求跟踪矩阵 L561——`| REQ-112 | 关键行为规则进入确定性注入面… | P0 | 待立项（0.75.0 候选） | 📋 草案 | …`。需求矩阵表头为 `| 需求ID | … |`（L477-478），不命中 `优先级|ID` 表头识别；矩阵前有 prose（L475）隔断 headerless 检测 → **REQ-112 对解析器不可见**。
- 病理差异：REQ-112 不是"已完成但被归档隐藏"——它的需求矩阵行状态是 `📋 草案`（且矩阵行未回填：其真实消费方 FIX-253 已 ✅ 完成（L219/L240）、承载发布 REL-068/0.75.0 已 ✅（L221），但矩阵"关联任务"仍写"待立项"）。`REQ` 前缀在 `_TASK_FAMILY_PREFIXES`（L98），故 VAL-010 被其阻塞。EVD-FIX-257 已将该阻塞定性为"验收自环——真实语义"：VAL-010 本身就是 REQ-112 的行为级验收任务（B1 抽样仍 pending，L224），阻塞是治理上正确的保守状态，仅根因归因文案会呈现 `unknown_dependency`（data gap）而非真实语义。
- **因此 REQ-112 不属于"已归档完成任务的依赖行"死链类别 #2**，是指针行方案 (a) 不适用的变体（给需求实体造任务表行会制造 ID 语义混乱）。其自然消解路径：VAL-010 闭环（B1 补样或如实归档）后无活跃行再引用 REQ-112。

**未发现其他实例**：其余全部依赖引用（FIX-253/FIX-257/FIX-171/FIX-155/FIX-156 等）在热表内均有行。指针表 FIX-082~087/REL-013（L249-257）虽依赖 AUDIT-102（无热表行，归档 index.md L21 有行），但这些指针行自身 `✅ 已交付`——completed 行不参与 blocked/unblocked 计算（L1361-1362），不构成活跃盲区。

---

## 3. 调查问题 3：处置方案三案对比

### 3.1 方案 (a)：热表指针行（数据对账，解析器零改动）

为 AUDIT-124 在 plan-tracker 补轻量指针行（建议置于 `### 已归档版本 task（hot-fact-source 指针）` 表 L249-257，与 FIX-082~087 同形态；该表在解析器扫描面内，docstring L564-566）：

```markdown
| — | AUDIT-124 | verify_workflow.py 20321 行膨胀根因诊断——触发 DEC-088 策略转向（0.61.0 链诊断件）| DEC-083, RISK-039, 用户质疑 | 0.61.0 | 已归档至 archive/tasks/completed-tasks-2026-04-30_2026-06-27.md（index L148；叙述段见 L60）| ✅ 诊断完成 (2026-06-27)——指针行 |
```

- 优先级列用 `—`（解析为 P9 sentinel，L250-265）——与指针表先例一致，且 completed 行不参与推荐排序，P9 无副作用。
- 分析器会把指针行当活跃吗？**不会**：状态列以 ✅ 开头 → `_status_is_completed`（L177-186，含 ✅ 即完成）→ 进 completed 桶（L1361-1362），与 FIX-082~087 现行为一致（它们当前正被解析为 completed，无噪声）。完成前缀足够——规则是"含 ✅ 即完成"（L158-163），状态取最后非空 cell（L898-902）。
- **REQ-112 不随本方案处理**（见 §2.3 病理差异；如需消除其 unknown 归因，独立候选：VAL-010 依赖列语义化或需求矩阵回填，另行决策）。

### 3.2 方案 (b)：解析器归档/叙述段感知（task_priority.py 扩展）

两个子形态：

- **b1（归档索引感知）**：CLI 层增读 `archive/index.md` 文本，把 Task 索引的"已完成"行并入一个 side-channel status map；`parse`/`compute` 增第二输入参数。改动面：task_priority.py（签名 + 合并逻辑 + 测试 fixture）、verify_workflow.py CLI、change_triage.py（L196/282/522 消费点）、loop_exit_bridge.py——约 3-5 文件、+80~200 行。破坏 purity contract（L45-51 单文本输入设计）；fail-closed 语义本身可保留（index 是归档引擎生成的结构化数据），但引入第二事实源漂移面（index 与热表双源一致性问题——AUDIT-127 正是归档索引完整性事故先例）。
- **b2（叙述段模式匹配）**：扫描"任务分解 X（…，完成）"类 prose。**强烈不建议**：叙述格式无契约、措辞任意变化即失效、误匹配风险高（叙述提及 ID ≠ 完成——如 L59"FIX-155/156/REL-047 任务状态标记为停滞待定"含三个 ID 但语义是停滞）；把 fail-closed 变 fail-open（叙述误读 → 假完成 → 错误解锁）。项目已有定性先例：AUDIT-143 将自由文本数据列为数据层根因，FIX-251 的修复方向是**给自由格式补结构**（headerless 表形状检测）而非让解析器理解 prose；FIX-252 O1 进一步收紧输入通道歧义。

### 3.3 方案 (c)：维持现状 + 交互披露

不修数据不改代码；推荐呈现时由 Coordinator 披露矛盾（EVD-899 本会话已做）。

### 3.4 四列对比表

| 维度 | (a) 热表指针行 | (b) 解析器归档/叙述段感知 | (c) 维持现状 + 披露 |
|---|---|---|---|
| **实施成本** | 1 文件（plan-tracker.md）+1 行；无代码、无测试改动；快速通道（治理记录范畴） | b1：3-5 文件 +80~200 行（task_priority/verify_workflow/change_triage/loop_exit_bridge + fixture）；b2 同量级但正确性不可保证 | 0 行；每会话人工披露约 1-2 句 |
| **风险清单** | ① 归档引擎未来运行可能把指针行再迁走（假设 H3——经验上优先级一览/指针表大量 ✅ 行历经 2026-08-05 全量归档 v0.1.0~v0.72.0 仍保留，但迁移豁免机制未考证）；② total/completed 计数 +1（141→142/137→138——本就是漏计修正，方向正确）；③ 行为无人看护时指针行状态漂移（低——completed 终态稳定） | ① 破坏 purity contract/单事实源设计（L45-51）；② 双源一致性新漂移面（index vs 热表，AUDIT-127 先例）；③ b2 自由文本解析脆弱 + fail-open 风险（FIX-251/252 反先例）；④ REQ-112 类需求实体仍不可见（需求矩阵不在任何归档机制）；⑤ 需求审查/代码审查/测试全链成本 | ① 依赖分析输出持续含事实错误推荐（每个无-unblocked 窗口期的会话 fallback 都指向 AUDIT-124"verify or record"——它早已完成）；② 披露依赖人工自觉，与 AUDIT-143 注入层根因（行为靠 prose 自觉）同构；③ change-triage 依赖快照持续把三件套标 blocked_by AUDIT-124（unknown），新任务冲突分析受污染；④ DEC-143"机器侧推荐可信度"持续受损 |
| **向后兼容** | 完全兼容：解析器零改动（与 FIX-257 形态 A 同句式）；指针表本就在解析面内（L564-566）；删除该行即完全回退（可逆性最优） | 计算函数签名变更 → 所有调用方（CLI/change_triage/loop_exit_bridge/92+ 测试）需适配；旧调用不传 index 时行为不变可做到，但契约面扩大 | 无兼容问题（无变更），也无改善 |
| **与 FIX-257 形态 A 先例一致性** | **高**：FIX-257 正是"数据行对账 + 解析器零改动"（plan-tracker L74"解析器零改动（注记感知方案登记为未来候选）"），且 EVD-FIX-257 明确预告"未来可用热表指针行或解析器归档感知处置"——本方案即其首选分支；另有指针表（L244-257）第二先例 | **低**：FIX-257 明确未选形态 B（解析器注记感知），理由含 BC-2 漂移规避；b2 与 AUDIT-143/FIX-251 数据层结论相反 | **中**：FIX-257 对类别 #2 采取了"登记后续候选"的过渡处置——但那是待调查登记，非终态 |

---

## 4. 调查问题 4：立项建议

### 4.1 建议结论

**建议立项，形态 (a)，但定位为"治理记录对账任务（Coordinator 直写快速通道）"而非产品代码任务**：

- 任务性质与 FIX-257 完全同族（分析器死链对账、数据行修正、解析器零改动、快速通道边界——FIX-228 先例）。无需 Developer/Reviewer 链。
- 目标形态：§3.1 样例行落盘 `### 已归档版本 task（hot-fact-source 指针）` 表（或优先级一览表尾部，二者解析效果等价；放指针表语义更精确——它是"为满足机器可见性而保留的归档指针"，与该节自述目的 L246-247 一致）。
- **需要补指针行的完整清单：仅 AUDIT-124 一行**（REQ-112 不适用指针行形态，见 §2.3；其余盲区为零，见 §2.3 末段）。
- 建议任务命名沿用对账序列（如 FIX-259 或按 SYSGAP/TD 序列），依赖：AUDIT-144✅（本报告）、EVD-FIX-257、FIX-171（归档引擎 task/CE 区分先例）。
- 同批可选（低优先，非必须）：VAL-010 依赖列的 REQ-112 引用加注记（如 `REQ-112(验收自环——需求矩阵 L561，非任务)`）——纯文档性，不改机器语义（注记被 prose 提取忽略），仅为人类读者消歧。是否做由 Coordinator 决定。

### 4.2 不建议 (b) 的理由（供 Coordinator/用户决策参考）

b1 的双源漂移面与 purity 契约破坏在单实例（1 个 ID）场景下收益/成本比极低；b2 与项目已确立的数据层方向（结构化优先，AUDIT-143/FIX-251/252）相反。若未来盲区实例规模化（如归档加速后 unknown 依赖增多），b1 可作为独立产品代码任务重估——届时应有本报告作为证据基础。

### 4.3 验收信号（红 → 绿样例）

**红（当前实测，EVD-899 / FIX-258.json L578）**：

```
Total: 141 tasks — 137 completed, 0 unblocked, 4 blocked, 0 non-executable
Unblock pick: `AUDIT-124` [P9] (unknown_dependency)
- reason: data gap: `AUDIT-124` is a task-family dependency with no row in the
  plan-tracker (fail-closed — it cannot be proven complete); verify or record
  its completion to reopen the chain
- unlocks 3 downstream: FIX-155, FIX-156, REL-047
Blocked:
- FIX-155 ⏸ blocked_by=[AUDIT-124]
- FIX-156 ⏸ blocked_by=[FIX-155, AUDIT-124]
- REL-047 ⏸ blocked_by=[FIX-155, FIX-156, AUDIT-124]
- VAL-010 🔄 blocked_by=[REQ-112]
```

**绿（补指针行后预期——推演基于解析器代码逻辑，H2 待实跑验证）**：

```
Total: 142 tasks — 138 completed, 0 unblocked, 3 blocked, 1 non-executable   （±AUDIT-144 行存在时 unblocked=1）
Unblock pick: `FIX-155` [P1] (non_executable_status)
- reason: status stop: `FIX-155` is dependency-satisfied but held by terminal
  status '⏸ 停滞待重新评估' — re-evaluate or resume `FIX-155` to reopen the chain
- unlocks 2 downstream: FIX-156, REL-047
Blocked:
- FIX-156 ⏸ blocked_by=[FIX-155]
- REL-047 ⏸ blocked_by=[FIX-155, FIX-156]
- VAL-010 🔄 blocked_by=[REQ-112]      （REQ-112 子类维持，见 §2.3）
Excluded (non-executable):
- FIX-155 ⏸ 停滞待重新评估（deps=[AUDIT-124→已完成]）
```

推演依据：AUDIT-124 进 completed → FIX-155 依赖全满足、⏸ 为 non-candidate marker（L202-204）→ 转 non_executable；FIX-156/REL-047 的 blocker 链在 `_walk_blocker_roots` 中走到 FIX-155（in-table、not completed、not blocked → `_ROOT_KIND_STATUS`，L1094-1097）→ roots={(FIX-155,status):2, (REQ-112,unknown):1} → pick FIX-155。**语义正确性**：推荐从"事实错误的 data gap（AUDIT-124 早已完成）"变为"事实正确的 status stop（0.61.0 停滞链确实等 FIX-155 重新评估——与 L59 叙述、EVD-632 终态一致）"。这正是 FIX-254 设计 fallback 的本意（推荐停滞链头节点）。

**附加绿信号**：change-triage 依赖快照中 FIX-155/156/REL-047 不再出现 `unknown` 依赖标记。

---

## 5. 事实 / 假设 / 建议三分离

- **事实**（均含行号来源，本次 Read/Grep 验证）：§1 全部代码定位；§2 全部盘点；§3 各案成本/先例引用；EVD-899 与 FIX-258.json 输出原文。
- **假设**（未验证，附验证计划）：见 §6。
- **建议**（决策权在 Coordinator + 用户）：§4。

## 6. 未验证假设与验证计划

| # | 假设 | 验证计划（执行者：Coordinator/Developer，Bash 可用） |
|---|---|---|
| H1 | AUDIT-124 曾有热任务表行、被 FIX-157（2026-06-28）归档迁出 | `git log -p -- .governance/plan-tracker.md` 检索 2026-06-27~28 diff 中被删除的 AUDIT-124 行；或查 FIX-157 归档运行的 task_versions 记录 |
| H2 | §4.3 绿色输出推演（含指针行被解析为 completed、fallback 转推 FIX-155） | 补指针行后运行 `task-priority-analysis` 子命令，对照本报告 §4.3 预期输出 |
| H3 | 归档引擎未来运行不会把新指针行再次迁出热文件 | 补行后运行 `archive.py migrate --auto --dry-run` 观察该行是否被列为可归档；同时考证现行引擎对优先级一览/指针表既有 ✅ 行的豁免机制（大量 0.6x 版本 ✅ 行历经 2026-08-05 v0.1.0~v0.72.0 归档仍热存——经验事实，机制未考证） |
| H4 | 需求矩阵 REQ 行对解析器不可见（prose 隔断 + 表头不匹配）已由代码静态分析确认；未构造 fixture 实证 | 可选：test_task_priority 增加"需求矩阵表不误判"回归用例（FIX-251 已有 prose 隔断测试则引用即可） |

## 7. 边界声明

- 本调查只读：未修改 task_priority.py / plan-tracker.md / evidence-log.md / 任何产品代码；唯一写入为本报告文件。
- 未执行任何命令（Bash 禁止）；所有分析基于文件直读 + Grep + 解析器源码静态推演。
- 未做技术选型终裁：三案对比是分析，立项与形态由 Coordinator + 用户决定（本报告建议 (a) 仅为分析结论）。
- 本报告为 Analyst 产出，不含与用户的直接交互。

## 附：关键文件行号索引

| 文件 | 关键行 | 内容 |
|---|---|---|
| `skills/software-project-governance/infra/task_priority.py` | L45-51, L97-101, L118, L158-186, L202-212, L322-354, L357-388, L427-433, L546-694（L636-645 prose 跳过 / L660-665 表头 / L676-681 headerless）, L820-911, L997-998, L1080-1083, L1107-1112, L1288-1300, L1351, L1366-1374 | 解析/compute/fallback 全链 |
| `.governance/plan-tracker.md` | L48-52, L59-60, L64-74, L76-80, L86, L219, L221, L224, L226, L228, L230-240, L244-257, L477-478, L561, L625-630 | 叙述段/任务表/指针表/需求矩阵 |
| `.governance/archive/index.md` | L148（Task 索引 AUDIT-124）, L568-569（EVD 索引） | 归档索引 |
| `.governance/archive/tasks/completed-tasks-2026-04-30_2026-06-27.md` | L153 | AUDIT-124 归档表行 |
| `.governance/evidence-log.md` | L1338（EVD-FIX-257 类别 #2 登记）, L1346（EVD-899 快照） | 治理证据 |
| `.governance/change-triage/FIX-258.json` | L578（report_text 140/136/0/4 + Unblock pick AUDIT-124） | 解析器实测输出 |
| `.governance/session-snapshot.md` | L19, L32 | 盲区候选登记 |
