# FEAT-033-CODE-R1 代码审查报告 — R0 findings 修复验证（round 1 复审）

- **round = R1**（复审轮；前轮报告：`docs/reviews/review-FEAT-033-CODE-R0.md`（NEEDS_CHANGE，P0=1/P1=1/P2=3/P3=9，14 条 findings）——本轮逐条比对其 §六 复审锚）
- **复审对象（R1 返工净改动）**：`skills/software-project-governance/infra/bootstrap_aggregate.py`（778→945 行，实数相符）；`skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py`（458→787 行，实数相符）
- **审查者**：Code Reviewer Agent（同一角色 R1 轮；独立只读审查，未参与开发）
- **审查规范**：skills/code-review/SKILL.md（0.65.0 循环角色语义）+ agents/code-reviewer.md
- **方法与限制**：逐行静态审查（Bash/pwsh 角色禁用 → 测试与 CLI 未复跑；Developer 运行时申报以静态实现路径评估 + 活体治理文件逐行核对 + 引擎对照段逐行比对替代验证）。所有结论均指向文件:行号级可复查事实；无法静态验证处明示「未复跑」。

---

## 一、R0 findings 逐条响应表（复审锚 §六 14 条逐一）

| R0 # | 级别 | 裁决 | R1 实证（文件:行级） |
|------|------|------|----------------------|
| P0-1 | P0 阻塞 | **已修复** | `_iter_positional_tables` 重写为引擎 `_status_table_stream` 逐行镜像（bootstrap_aggregate.py:407-457 ↔ verify_workflow.py:10455-10494，逐点对照见 §二）；差分护栏 `test_stream_matches_engine_on_every_fixture`（test:518-526，6 fixture 双向 `list==list`）；分段 fixture `RISK_LOG_SEGMENTED`（test:110-129）断言 open=4 且 914/915 不丢（test:528-537）；幽灵块 `GHOST_BLOCK_COMBINED` 断言恰 2 真表 + 990/991 零计数（test:539-549）；活体形状与引擎 `parse_active_risks` 同值断言（test:551-559）。方案 a（镜像非公共函数化）论证成立：公共函数化触碰 R6=198 冻结面 + 新增反向边（模块 engine-free 红线 bootstrap_aggregate.py:56-60 + 结构断言 test:761-765） |
| P1-1 | P1 关键 | **已修复** | 全阻塞 fixture `PLAN_TRACKER_ALL_BLOCKED`（test:146-163，FEAT-201→FEAT-998 未知依赖 + FEAT-202 链尾）；`EmptyRecommendationTests` 3 测试（test:582-625）断言 `empty_reason` 七键（kind="all_blocked"/total/completed/blocked/non_executable/message/nearest_action，含 FEAT-998 in nearest_action）+ `unblock_recommendation` 字段（root_task_id="FEAT-998"/root_kind="unknown_dependency"/downstream_count=2/reason）+ next_actions「无就绪候选」分支。申报勘误：`unblock_recommendation` 实为 **4 字段**（bootstrap_aggregate.py:495-500），申报「六字段」口径不精确（实现、引擎契约 `UnblockRecommendation` 四字段与测试三方一致，非代码缺陷——见 §七 N-4） |
| P2-1 | P2 建议 | **已修复** | 逐行回退 `topic_cell or content_cell`（bootstrap_aggregate.py:386，对齐引擎 :10704 `(cell("主题") or cell("决策内容"))`）；截断经披露式 `_clip(…, RECENT_TOPIC_LIMIT=60)`（:128/:131-135，60+「…」）；`RecentTopicFallbackTests` 3 测试（test:628-661：61 字符披露截断、空主题回退、id/date 引擎 parity）。60 字符外与引擎静默 `[:60]` 的分歧已声明为有意（declared divergence，:123-128 + :355-357 docstring），parity 测试按前 60 字符断言（test:576-579）——方向诚实 |
| P2-2 | P2 建议 | **已修复（备选方案成立）** | 闭词表 `_GATE_PASSED_STATES`/`_GATE_PENDING_STATES`/`_GATE_FAILED_STATES`（:254-257）+ `_gate_bucket` 精确成员匹配（:260-269，strip/lower/去反引号星号后 set 判等，超集词形落 `other` 可见不吸收）。**事实核查通过**：引擎 gate 判定无独立可引用谓词——`parse_gate_status`（verify_workflow.py:7540-7564）直接返回 status 字符串，调用侧裸比较（:9803 `== "passed"`、:9815 `== "passed-on-entry"`）；`_gate_state` 全仓零命中；`checks/gate_domain` 的保守 interlock 分类器将 failed 并入 pending（合同不同）。bootstrap-local 桶合同以 docstring 显式声明（:243-253）+ `GateBucketContractTests` 2 测试锁定（test:664-686：域词形保桶 + unpassed/pending-review/failed-pending/"passed (见 DEC-1)" 落 other） |
| P2-3 | P2 建议 | **已修复** | `_enforce_projection_budget` 四阶段硬钳制（:744-804）：① diagnostic 裁 200（:773-777）→ ② overview 丢弃（:781-784）→ ③ candidates 裁 1（:788-793）→ ④ `_clamp_strings` 逐字符串 120（:797-804）。每阶段 notes 披露（`_PROJECTION_CLAMP_NOTE`）；终止性成立（④ 后每 str 叶 ≤121 字符、叶数量由固定 faces + caps + 相位数界定）；确定性（仅内容决定，时钟无关）有测试锁定。`ProjectionClampTests` 3 测试（test:689-738：超预算钳到 ≤8KB + 披露在位 + clamp 非预算 defer + 双跑一致 + 预算内零触碰）。附 P3 级新观察 N-3（③④ 无独立触达 fixture） |
| P3-1 | P3 | 未修复＝**如实遗留** | `parse_risk_summary(risk_text)`（:637）仍用真实时钟（:309 `today or date.today()`）；same-day 幂等限定未入文档。新增 `SegmentedTableMirrorTests` 已用 `_TODAY` 注入（test:516/:531/:547）——旧 `AggregateFieldCompletenessTests.test_risk_summary_counts`（test:353-360）保留真实时钟依赖，遗留申报相符 |
| P3-2 | P3 | 未修复＝**如实遗留** | `_read_text` OSError → ""（:708-713）静默全零面路径保持原样，无披露 |
| P3-3 | P3 | 未修复＝**如实遗留** | fail-closed 分支（:925-936）payload 仍缺 generated_at/duration_ms/deferred/profile/budget_ms |
| P3-4 | P3 | 未修复＝**如实遗留** | `builder.report` 仍写入无读者（:633 死状态）；`_table_rows`（:196-212，gates 面）与 `_iter_positional_tables`（:407-457，risks/recent 面）双解析器留存。申报明确披露此项；`_table_rows` 的节内线性收集语义在 R0/R1 间无变化（P0-1 不涉它），无新增风险 |
| P3-5 | P3 | 未修复＝**如实遗留** | `--budget-ms` 负数/非 int 静默回退默认（:916-918），help/docstring 未披露该回退 |
| P3-6 | P3 | 未修复＝**如实遗留** | 旧 fixture 风险日期仍锚定真实时钟（RISK-901 截止 2026-09-05，test:353-360 未注入 today；`today` 参数 :309 在位）；新分段测试已时钟无关（_TODAY 注入 / 引擎同钟 parity），改善但不关闭原条目 |
| P3-7 | P3 | 未修复＝**如实遗留** | `ProfileDetailTests`（test:403-410）仍仅断言 lite 档 recent 缺席 + caps，overview 缺席未断言 |
| P3-8 | P3（流程） | 未修复＝**如实遗留** | triage files 机录 3 vs 实际变更面——Coordinator 记录面事项（DEC-206⑥ 回写义务同族），非代码缺陷，本轮未涉及 |
| P3-9 | P3（上游观察） | 未修复＝**如实遗留** | 活体复核成立：decision-log 尾部 DEC-189~206 行块（.governance/decision-log.md:127-146）无分隔行随行，引擎与 bootstrap 同判不成表——mirror 保真方向正确，上游数据形状债维持独立 FIX 候选登记 |

---

## 二、P0-1 镜像保真核实（本轮核心）

`_iter_positional_tables`（bootstrap_aggregate.py:427-457）与引擎 `_status_table_stream`（verify_workflow.py:10464-10494）逐点对照：

| 语义点 | 引擎 | bootstrap R1 | 一致 |
|--------|------|--------------|------|
| 行切分 | `content.split("\n")` | `text.split("\n")` | ✓ |
| 主游标推进 | 非 `\|` 行 `i+=1` | 同 | ✓ |
| header 提取 | `split("\|")[1:-1]` 逐格 strip | 同 | ✓ |
| 分隔行前空行跳过 | `while j<n and not lines[j].strip(): j+=1` | 同（:437-438） | ✓ |
| 分隔行校验 | `re.match(r"^\\|[\s:\-\|]+\\$", lines[j].strip())` 失败 → `i+=1; continue`（不成表） | `_SEPARATOR_ROW_RE`（:111）**逐字符相同** + 同控制流（:439-441） | ✓ |
| 表内空行 | 跳过容忍（:10483-10485），不断表 | 同（:446-448） | ✓ |
| 表内第二个分隔行 | 跳过继续 | 同（:451-453） | ✓ |
| 断表 | 非 `\|` 行 break，`i=k` 回扫 | 同（:449-450/:457） | ✓ |
| 幽灵表头排除 | 无分隔行 `\|` 行永不成表（`i+=1`） | 同 | ✓ |

双向差分护栏：`test_stream_matches_engine_on_every_fixture`（test:518-526）在 6 fixture（连续表×3 + 空行切段 + 切段+幽灵块×2）上断言 `list(mirror) == list(engine)`——相等断言双向蕴含。fixture 形状与活体类形对应：活体 risk-log 的「一表被空行切 4 段」（.governance/risk-log.md L7-49，切点 L32/L38/L47）由 RISK_LOG_SEGMENTED 三段形态覆盖（多连续空行与单空行走同一 while 吞行路径，语义等价）；活体 decision-log 的「切段 + HISTORICAL 非 `|` 行块断表 + 尾部无分隔行块」（decision-log.md L5-26/L127-146）由 DECISION_LOG_SEGMENTED_GHOST 覆盖。**静态推演活体**：bootstrap 与引擎对活体 risk-log 同得 open=4（RISK-036/039/046/050，13 列、状态恰「打开」）；对活体 decision-log 同得 recent=[DEC-147(08-22), DEC-142(08-13), DEC-141(08-13)]（L5-6 表头段 + 空行容忍 + L19-26 行块断表；排序键 (date, id_num) 降序两侧镜像一致，:390-401 ↔ 引擎 :10707-10720）。未复跑（角色禁用），静态结论。

表扫描器之后的残余 parity 边界（不阻塞，见 §七 N-1/N-2）：列宽判定键集合（引擎 7 列 vs bootstrap 3 列）与列名清洗（引擎 `_status_col_name` 去反引号/星号/lower vs bootstrap `header.index("编号")` 裸匹配）存在理论分歧形状；活体 13 列裸名表头下两侧零分歧（活体 max pos 均=截止日期 pos 10）。

## 三、勘误裁决：「应为 6」vs「引擎机判 4」——**勘误成立**

独立核对活体 `.governance/risk-log.md`（不改写 R0 原文，仅记录）：

1. **RISK-052/053 为 10 列短行**：L48/L49 逐 `|` 分割实数 **10 单元格**（编号/日期/描述/所属阶段/触发条件/影响/严重级别/Owner/当前状态/缓解+尾注合并格）——13 列表头（L7）下位置错位。引擎 `parse_active_risks` 宽度门槛 `len(cells) <= max(idx.values())`（idx 最大 pos = 截止日期 = 10；verify_workflow.py:10633-10634）→ 10 ≤ 10 **排除**；bootstrap `width = max(编号/当前状态/截止日期 pos) = 10`（bootstrap_aggregate.py:318-321）→ 同判排除。**两侧同判**。
2. **RISK-047/048/051 状态为修饰词形**：L43「打开（登记观察）」/ L45「打开（登记观察）」/ L46「打开（已接受，DEC-199 (a) + DEC-203 (a) 扩展）」。引擎谓词 `is_risk_status_open` 精确 `== "打开"`（checks/risk_domain.py:94-96，FIX-270 R0 F3 单一判定）；bootstrap :323 `cells[status_pos].strip() != "打开"` 同谓词。**两侧同判排除**。
3. **引擎机判 4 复核**：RISK-036（L39）/RISK-039（L40）/RISK-046（L42）/RISK-050（L44）均为 13 列且状态恰「打开」→ 两侧同判计入；RISK-044（L41）状态「**缓解中（…）**」排除。open=4（ids RISK-036/039/046/050）与 Developer 机证申报一致。
4. **R0「6」的成因**：R0 §一·P0-1 事实链「恰为『打开』状态的 6 条（…036/039/046/050/052/053…）」系目测含「打开」字样的计数，未执行宽度门槛与精确谓词两道引擎同款判定。**勘误成立**：镜像保真以引擎口径为准（4）。P0-1 的实质论证不受影响——旧扫描器只见表 1 段（RISK-001~024 全部缓解完成/已关闭）→ open=0 静默，0 vs 4 仍是活体事实失真；R0 将失真幅度表述为「0 vs 6」应更正为「0 vs 4」。

---

## 四、五维度

### 维度 1：正确性 — **PASS（P0=0）**
P0-1 修复经逐行镜像对照 + 差分测试 + 活体静态推演三重核实（§二/§三）；P1-1 路径有端到端断言；P2-1/2/2/2-3 修复实现与申报相符。无新引入正确性缺陷：`_iter_positional_tables` 游标单调无死循环；`_gate_bucket` 未知词形落 other（fail-safe 可见方向）；`_enforce_projection_budget` 仅内容决定、阶段④有界终止。

### 维度 2：安全性 — **PASS**
只读红线保持：结构断言在位且 forbidden 列表与 R0 等价（test:767-777）；模块无写路径/subprocess/eval；唯一文件访问 `_read_text` 只读（:708-713）；engine-free 保持（无 verify_workflow import，test:761-765）；无硬编码密钥；argparse choices 约束不变（:879-891）。

### 维度 3：可维护性 — **PASS**
镜像语义以 docstring 显式声明并指向差分护栏（:407-426）；闭词表合同声明（:243-253）；declared divergence 披露（:123-128）。遗留披露如实：`_table_rows` 双解析器留存（P3-4，gates 面单表线性收集语义与 R0 无变化）、`builder.report` 死状态保持。残余边界 N-1/N-2 已在本报告登记供后续收敛裁量。

### 维度 4：性能 — **PASS（静态评估）**
解析面仍 O(行数) 单遍；clamp 四阶段最坏对 payload 各一遍线性（①②③复制单 face、④全树一遍）；无新增 I/O（3 文件读不变）。未复跑（角色禁用），与 R0 申报量级静态相容。

### 维度 5：测试覆盖 — **PASS（附 P3 备注）**
42 测试实数核对相符：既有 26（名单逐一在位，断言体与 R0 引用等价——budget 0 → deferred 非空+gates/candidates 缺席+resolve 在场 test:416-429；结构断言 test:767-777；engine CLI 双跑只读 test:456-489）+ 新增 16（Segmented 5 + Empty 3 + RecentTopic 3 + GateBucket 2 + Clamp 3）。零回归声明经静态名单/断言核对成立（测试执行未复跑）。P1-1 路径（REQ-110）首次获得回归护栏。备注 N-3：clamp 阶段③/④无独立触达 fixture。

---

## 五、AI 生成代码专项 5 项（本轮改动面）

| 项 | 裁决 | 依据 |
|----|------|------|
| mock 残留 | 无 | unittest.mock 仍仅 resolve_entry.PLUGIN_HOME 文档化缝（test:318）；无新增 mock |
| 硬编码返回值 | 无 | `_TODAY=date(2026,9,10)` 为既有的 `today` 注入参数在位使用（:309 缝），非产品伪造；`deps_satisfied: True` 恒真不变量与 R0 裁决一致 |
| 幻觉 API | 无 | 新增跨模块引用逐一核实存在：引擎 `_status_table_stream`（:10455）/`parse_active_risks`（:10610）/`parse_recent_decisions`（:10668）；`report.empty_reason`/`unblock_recommendation`/`cycle_warning`（R0 已核实） |
| 未实现 TODO | 无 | 本轮改动面（945+787 行全文通读）无 TODO/FIXME/XXX/NotImplemented |
| 过度实现 | 否 | 四阶段钳制每阶段对应具体膨胀源申报；闭词表精确匹配对应 R0 误桶向量；镜像方案 a 有 R6 冻结面论证；无投机抽象 |

---

## 六、硬门槛裁决

| 门槛 | 裁决 |
|------|------|
| P0 = 0 | **PASS（P0=0）** |
| 5 维度全覆盖 | PASS |
| 每条发现 P0~P3 分级 | PASS |
| 复审锚（R0 §六）逐条响应 | PASS（14/14，§一响应表） |
| 设计一致性（AUDIT-154 §8） | PASS——①单次输出全部热数据：勘误后活体 risks open=4（=引擎）、recent 3 条（=引擎），热数据可信面成立；②只读幂等 ✓（结构断言+树哈希+双跑测试在位，未复跑）；③预算参数+fail-safe ✓（新增输出端硬钳制强化）；④协议消费指向不变（本两文件改动未触接线） |

## 七、本轮新观察（全部 P3，零 BLOCKING）

| # | 级别 | 位置 | 摘要 |
|---|------|------|------|
| N-1 | P3 | bootstrap_aggregate.py:317-321 ↔ verify_workflow.py:10625-10634 | 列宽判定键集合差异：引擎 width = max(编号/日期/描述/状态/截止/严重/owner 7 列 pos)，bootstrap = max(编号/状态/截止 3 列 pos)。「有截止日期列之外更靠后的已知列 + 短行」的非标准形状下两侧可分歧（bootstrap 偏宽松）；活体 13 列表两侧同值（max=10），差分测试覆盖表流不覆盖此判定。建议随 N-2 一并纳入后续 parity 收敛候选 |
| N-2 | P3 | bootstrap_aggregate.py:313-317/:361-367 ↔ verify_workflow.py:10295-10298 | 列名匹配差异：引擎经 `_status_col_name` 清洗（反引号/星号/lower）后匹配，bootstrap `header.index("编号")` 裸精确匹配——装饰表头（`**编号**`）下引擎能识别、bootstrap 整表跳过。活体表头无装饰，不触发 |
| N-3 | P3 | test_bootstrap_aggregate.py:689-738 | clamp 阶段③（candidates 裁 1）/④（逐字符串 120）无独立 fixture 触达（现有超预算 fixture 在阶段②即回预算内）；且阶段④将 notes 摘除后原样还原（:797-802），理论上存在 clamp 后 + notes 字节恰好越过 8KB 的极小窗口（notes ≤4 条、百字节量级）。兜底逻辑在位、活体不触发，登记覆盖候选 |
| N-4 | P3（申报勘误） | R1 调度申报 | 「empty_reason 七键 + unblock_recommendation 六字段」中七键准确（kind/total/completed/blocked/non_executable/message/nearest_action，测试逐一断言）；`unblock_recommendation` 实为 **4 字段**（root_task_id/root_kind/downstream_count/reason，:495-500 = 引擎 `UnblockRecommendation` 契约同形）——申报口径勘误，实现/测试/引擎三方一致，非代码缺陷 |

## 八、回归面与申报核对

- **行数/测试数**：945 行 / 787 行 / 42 测试（26 既有 + 16 新增）全部实数相符；既有 26 断言体与 R0 引用等价，零回归声明静态核对成立（执行未复跑——Bash/pwsh 角色禁用）。
- **schema governance-bootstrap/1 键面**：不变（:81）；`notes` 为既有可选披露键（未初始化分支 :593 与钳制分支 :771），钳制未触发时零新增键（test:733-738 锁定）。
- **Developer 活体机证申报**（risks open=4 ids 一致 / recent [DEC-147,142,141] 一致 / 双跑幂等 / .governance 零变化）：与活体文件逐行静态推演全部相符（§二/§三）；双跑幂等的只读路径静态成立（唯一读入口 `_read_text`，零写路径），标注「未复跑、静态相符」。

---

## 结论：APPROVED_WITH_NOTES（P0=0 / P1 未解决=0 / P2 未解决=0 / P3 遗留 9 + 本轮新观察 N-1~N-4；unresolved_blockers=0）

P0-1 修复经逐行镜像对照、双向差分测试与活体形状静态推演三重核实；勘误裁决成立（活体 open=4 为引擎同判口径，R0「6」系目测计数，仅记录不改写原文）；P1-1 与 P2×3 修复均有代码+测试实证；P3×9 遗留披露逐条如实。无未解决 BLOCKING finding。N-1~N-4 为 P3 级备注（parity 收敛与钳制覆盖候选），不阻塞合并。复审链通过终态达成，Check 30 可消费本终态。
