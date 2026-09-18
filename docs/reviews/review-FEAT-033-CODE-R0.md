# FEAT-033-CODE-R0 代码审查报告 — 只读 bootstrap 聚合命令 v1（round 0）

- **审查对象**：FEAT-033 工作树未提交变更集（10 文件 + TOOLS.md TOOL-054 一致性核对）
- **审查者**：Code Reviewer Agent（独立只读审查；未参与开发）
- **审查规范**：skills/code-review/SKILL.md（0.65.0 循环角色语义）+ agents/code-reviewer.md
- **方法与限制**：逐行静态审查（Bash/pwsh 角色禁用 → 未运行测试与命令；Developer 运行时申报以静态实现路径评估 + 活体治理文件逐行核对替代验证）。所有结论均指向文件:行号级可复查事实；无法静态验证处明示「未复跑」。
- **目标锚定**：change-triage/FEAT-033.json（P0，0.84.0，depends FEAT-032）+ AUDIT-154 §8 行（docs/requirements/governance-bootstrap-cost-audit-0.84.0.md:179）验收 = 「单次 CLI 输出全部热数据；只读幂等；超时预算参数；bootstrap 协议改为消费该命令」。

---

## 一、五维度逐项

### 维度 1：正确性 — **FAIL（P0×1）**

已核实正确面：
- resolve envelope 复用：`resolve_entry.resolve/resolve_host_root/PLUGIN_HOME` 存在（resolve_entry.py:45/230/301），envelope 10 个消费键在 success/fail 两分支均存在（resolve_entry.py:241-298）——零重推导成立，无 KeyError 向量。
- migration 仅标志：`migration_flag` 纯版本比较（bootstrap_aggregate.py:135-152），全模块无任何迁移执行路径；与 FEAT-035 边界清晰 ✓。
- 预算 fail-safe：`check_budget` 相位间显式检查（:483-487、:531-576），非 try/except 吞错（except 仅捕获 `_BudgetExhausted` :578）；`--budget-ms 0` → deferred 非空 + gates/candidates 缺席 + resolve 在场（测试 :320-333 断言）✓。
- fail-closed：`resolved_root_ok=false` → exit 1 + envelope + 无治理面（:759-770），符合 DEC-080 ✓。
- 候选轻量路径复用：`task_priority.parse_task_dependencies`（task_priority.py:757，text 通道经 FIX-252 消歧）/`compute_unblocked_tasks`（:1517）/`PriorityReport.cycle_warning`（:602）/`UnblockRecommendation` 四字段（:541-547）/`BlockedTask.task`（:500）全部真实存在——无幻觉 API。
- 引擎全局 `--project-root`（verify_workflow.py:23612-23618）→ CLI 双跑测试参数形式成立。

**P0-1（阻断）：mirror 表扫描器与引擎 `_status_table_stream` 口径分歧——活体热文件表内空行导致 risks/recent 面静默失真。**
- 事实链：
  - bootstrap `_iter_positional_tables`（bootstrap_aggregate.py:362-382）：非 `|` 行即断表；断表后首个 `|` 行无条件充当新表头，无分隔行校验。
  - 引擎 `_status_table_stream`（verify_workflow.py:10455-10489）：header 后必须有分隔行才成表；**表内空行跳过容忍**（docstring 明示「live plan-tracker inserts them between sub-groups」）。
  - 活体 `.governance/risk-log.md` 活跃风险表被空行 L32/L38/L47 切成 4 段。bootstrap 解析结果：仅段 1（header L7 + 行 L9-31）成立；段 2/3/4 分别以 **RISK-025/RISK-036/RISK-052 的数据行充当表头**，因缺「编号/当前状态」列被整体丢弃（:276-277）。
  - 恰为「打开」状态的 6 条风险（RISK-036/039/046/050/052/053，risk-log.md L39-49，逐行核对状态列）**全部位于被丢弃段**；引擎 `parse_active_risks`（verify_workflow.py:10610-10665，空行容忍、全文件扫描）对同一文件得到全部行。
  - 活体后果：governance-bootstrap 的 `risks` 面输出 `open=0 / escalation_overdue=0 / overdue_ids=[]`，**静默**；`_next_actions` 风险升级分支（:609-612）对 RISK-039/046 的 2026-09-30 复评窗永久失明。
  - 同根因作用于 decision-log：表 L5-7 后被空行 L8-11 切断，bootstrap 仅见 DEC-147；引擎口径（L5-18 一表，止于 L19 非 `|` 行）为 DEC-147/142/141 三条 → `recent` 面 1 vs 3，mirror parity 破裂。
- 定性：这不是投影响论——命令的存在意义即「单次输出可信热数据」（AUDIT-154 §8 验收①），模块 docstring 自我声明「deliberately MIRROR the proven engine calibers」（:17-24）且 fail-safe 诚实契约禁止「guessed pass」（:38-43）。静默零计数 = 与 QR-4「禁没查报通过」同构的事实失真；schema `governance-bootstrap/1` 是 FEAT-034 协议重排的消费契约面，错误风险面将向上传播。26 个测试的 fixture 全部为连续无空行表（test_bootstrap_aggregate.py:45-102）——测试全绿恰因 fixture 未覆盖活体形状。
- 修复建议：将 `_iter_positional_tables` 逐语义对齐 `_status_table_stream`（header→分隔行校验 + 空行容忍；注意引擎语义是「空行不断表」而非「遇空行断表」，直接加"空行断表后重扫"仍会丢行）；抽公共纯函数或声明双向差分测试；补「空行分段表」fixture（含"数据行充当表头"段落不得产生幽灵计数、亦不得丢行两个断言方向）。

### 维度 2：安全性 — PASS
- 只读红线 ✓：模块面无 `open(`/`write_text(`/`subprocess`/`os.system`/`mkdir(`/`shutil`（结构断言测试 :438-448 在位并核实当前源无违例子串）；唯一文件访问 `_read_text` 只读（:633-638）；引擎侧仅三处 dispatch 接线（verify_workflow.py:78-84/24483-24495/24630），ArchGuard R2 零新增反向边 ✓。
- 注入面 ✓：无 eval/exec/shell 拼接；argparse choices 约束 format/profile（:718-725）。
- 敏感数据 ✓：无硬编码密钥/token。
- fail-closed 语义 ✓（见维度 1）。

### 维度 3：可维护性 — PASS（附 P2/P3）
- 纯函数分层优秀：readers 均为 text-in/dict-out 无 I/O，orchestration 集中在 `_Builder`/`cmd`，CLI 单一 I/O 入口。
- `_clip` 披露式截断纪律明确（:106-116）。
- **P2-1**：`parse_recent_decisions` :342 `topic[:60]` 静默截断（无披露标记），与 `_clip` 的「…」披露纪律不一致；且缺引擎 :704 的「主题空→回退决策内容」逐行回退（bootstrap 只按表头选一列，主题空单元格行 topic=""）。引擎同为静默 `[:60]` → mirror 保真，但披露缺口为两处共有，建议统一披露或至少对齐回退语义。
- **P2-2**：`_gate_bucket`（:224-232）为模块自备桶口径，子串匹配（活体 "passed-on-entry"→passed 方向正确）；但未引用共享域谓词，对未来含 pending/failed 子串的超集词形存在误桶风险。建议 docstring 声明 bootstrap-local 桶合同或收敛到域谓词。
- **P3-4**：`builder.report` 写入后无读者（:479/:558 死状态）；`_table_rows` 与 `_iter_positional_tables` 双表解析器并存。docstring 承认 mirror 靠「review, not by import」同步——本轮 P0-1 即该失效模式的具体兑现，建议修复时一并收敛。

### 维度 4：性能 — PASS（静态评估）
- 单进程 import 复用（resolve envelope 经 import 而非子进程重推）✓；3 次文件读（plan-tracker/risk-log/decision-log）+ 各一次 O(行数) 解析；tpa 轻量路径为引擎已证明实现；无隐性重复全量扫描。358ms 申报与 status 0.49s / resolve_entry 0.09s 先例量级相容（未复跑——Bash 禁用，静态评估）。text 面 ≤40 行断言在位，静态上限约 23 行 ✓。8KB 见 P2-3。

### 维度 5：测试覆盖 — PARTIAL
- 26 测试实数相符（4+12+1+2+2+1+1+3）；schema/预算/幂等（树哈希+双跑 payload）/migration 四态/只读结构断言/engine CLI 双跑冒烟/fail-closed 均有断言，断言强度良好（如 :329-333 显式断言"未跑的 section 缺席而非猜值"）。
- **P1-1（关键）**：REQ-110 空推荐结构化原因路径零覆盖——`_candidate_empty`（:409-428）的 `empty_reason`/`unblock_recommendation` 分支在全部 26 测试中从未执行（fixture 恒有 unblocked 任务）。该路径是本任务申报核心契约（TOOLS.md TOOL-054 明示"空推荐携带结构化原因——REQ-110，禁止机械枚举"）且为 FEAT-034 消费面。字段访问面已静态核实存在，但无回归护栏。建议补全阻塞 fixture 断言 empty_reason.kind / unblock_recommendation.root_task_id 形状。
- **P0-1 的测试面缺口**：无空行分段表 fixture（见维度 1）。
- **P3-6**：fixture 风险日期锚定真实时钟（RISK-901 截止 2026-09-05，需运行日 > 该日才 overdue）——`parse_risk_summary` 已有 `today` 参数（:265）测试未注入。
- **P3-7**：ProfileDetailTests 未断言 lite 档 `overview` 缺席（仅断言 recent 缺席与 caps）。

---

## 二、发现列表（P0=1 / P1=1 / P2=3 / P3=9）

| # | 级别 | 位置 | 摘要 |
|---|------|------|------|
| P0-1 | P0 阻塞 | bootstrap_aggregate.py:362-382/265-307/310-359；对照 verify_workflow.py:10455-10489 | mirror 表扫描与引擎口径分歧：活体 risk-log 空行分段（L32/38/47）致 6 条「打开」风险被静默丢弃（open 0 vs 引擎口径 6）；decision-log 同根因（recent 1 vs 引擎口径 3）。详见维度 1 |
| P1-1 | P1 关键 | test_bootstrap_aggregate.py（全局） | REQ-110 空推荐结构化原因路径（_candidate_empty :409-428）零测试覆盖，FEAT-034 消费契约无回归护栏 |
| P2-1 | P2 建议 | bootstrap_aggregate.py:342 | recent topic `[:60]` 静默截断（引擎同款）+ 缺「主题空→决策内容」逐行回退（引擎 :704 有）——与 _clip 披露纪律不一致 |
| P2-2 | P2 建议 | bootstrap_aggregate.py:224-232 | _gate_bucket 模块自备桶口径未引用域谓词，超集词形有误桶风险（活体词形当前正确） |
| P2-3 | P2 建议 | bootstrap_aggregate.py:542-543/499-511/206-221 | ≤8KB 投影承诺无输出端硬钳制：parse_overview_row 单元格不裁剪（活体 plan-tracker:44 行单元格千字节级散文）、resolve.diagnostic 直通——当前实测 4937B 达标，但契约面随活体增长无界 |
| P3-1 | P3 | bootstrap_aggregate.py:265-266 | risks 面依赖 date.today()：幂等承诺「unchanged tree → payload 相等」跨零点不严格（同日双跑稳定）；建议文档补 same-day 限定 |
| P3-2 | P3 | bootstrap_aggregate.py:528/633-638 | governance_initialized=True 但 plan-tracker 读取 OSError → 全零面静默（gates total 0/tasks total 0 无披露）；建议 notes/deferred 披露读取失败 |
| P3-3 | P3 | bootstrap_aggregate.py:761-770 | fail-closed 分支 payload 缺 generated_at/duration_ms/deferred/profile/budget_ms——schema /1 两形态不一致，FEAT-034 消费需容错；建议 schema 注明可选键 |
| P3-4 | P3 | bootstrap_aggregate.py:479/558/177-193/362-382 | builder.report 死状态 + 双表解析器重复（见维度 3） |
| P3-5 | P3 | bootstrap_aggregate.py:750-752 | --budget-ms 负数静默回退默认 3000（fail-safe 可接受），help/docstring 未披露该回退 |
| P3-6 | P3 | test_bootstrap_aggregate.py:89/257-264 | 风险 fixture 日期锚定真实时钟，2026-09-06 前运行会失败；today 注入参数在位未用 |
| P3-7 | P3 | test_bootstrap_aggregate.py:304-314 | lite 档 overview 缺席未断言 |
| P3-8 | P3（流程） | .governance/change-triage/FEAT-033.json:10-14 | triage files 机录 3 文件 vs 实际变更面 10 文件——RISK-046 同族锁面偏差（FEAT-032/037 已有披露先例与 DEC-206⑥ 回写义务）；Coordinator 记录面事项，非代码缺陷 |
| P3-9 | P3（上游观察） | .governance/decision-log.md:19-26/123-146 + verify_workflow.py:10455-10489 | 活体 decision-log 真正最新决策（DEC-195~206，2026-09-17/18）位于无分隔行尾部行块，**引擎自身** recent 面同样不可见——非 FEAT-033 回归（mirror 保真），登记上游数据形状债，建议独立 FIX 候选 |

---

## 三、特别审查点核对（调度模板 9 项）

1. **358ms/4937B/text 12 行**：静态路径成立——单进程 import 复用、3 文件读、O(n) 解析、无隐性全量扫描；text 静态上限约 23 行 <40。数值未复跑（Bash 角色禁用），标「未复跑、静态相容」。
2. **health v1 恒 deferred** ✓：`_health_face` 为唯一出口且 state 恒 "deferred"（:588-595）；全模块无 health.state=pass/ok 任何路径（未初始化分支与 fail-closed 分支同用该 face）；pending_checks + next_action 指向 check-governance ✓。
3. **只读红线** ✓：结构断言在位 + 代码面核实（无 open(w)/subprocess/os.system，`_read_text` 只读）。
4. **幂等** ✓（同日限定，P3-1）：随机源无；时间戳仅 generated_at/duration_ms（:495/:584）；树哈希 + 双跑 payload 相等 + 引擎 CLI 双跑三重测试在位。
5. **预算 fail-safe** ✓：显式相位检查而非 try/except 吞错；0 预算 → deferred 非空 + gates/candidates 缺席 + resolve 在场有断言。
6. **_clip 80 披露截断** ✓（部分）：stage 等活体长散文截断带「…」披露；保留 P2-1（recent topic 静默截断）与 P2-3（overview 面未裁剪）。
7. **engine-free + R2 零新增反向边** ✓：import 面仅 resolve_entry/task_priority（:71-72）；结构断言 :432-436；LOADER_WHITELIST+1（registry.py:204-208）；r6=198（architecture-baseline.json:553）且 R1 锚 24639 同步（:17，与当前 verify_workflow.py 实际行数 24639 一致）。
8. **协议接线边界** ✓：governance.md:321（Scenario D 数据源补充，MAY 措辞、D1-D3 流程不变）+ :458（Scenario F bullet，含 deferred 免责与「status 仍为全量权威」声明）；SKILL.md:71 同款免责——均仅指向、未动时序，FEAT-034 边界尊重。
9. **candidates 空推荐结构**：实现形状与 next-candidates 契约一致（empty_reason/unblock_recommendation 字段静态核实存在），**但零测试覆盖（P1-1）**。

**申报 10 文件变更面核实**：全部在位且一致——bootstrap_aggregate.py（778 行）/test_bootstrap_aggregate.py（26 测试实数相符）/verify_workflow.py 三处接线/registry.py _COMMANDS+1 + LOADER_WHITELIST+1（87 键 docstring 分账 8+79 一致）/test_registry.py FROZEN 87（:89，含 IMPORT_COUNT=198 :101）/test_contract_matrix.py FROZEN 87（:68）/snapshots.json 含 governance-bootstrap（:237）/architecture-baseline.json r6=198 + R1 24639/governance.md 两处/SKILL.md 一处。**TOOLS.md TOOL-054**（commit 457a756 预入库）：存在、单行单节、无双重写入/冲突标记，内容与实现逐项一致（预算默认 3000、json|text、三 profile、≤8KB/≤40 行、deferred 语义、REQ-110 空原因、--project-root 引擎全局参数）。

---

## 四、AI 生成代码专项 5 项

| 项 | 裁决 | 依据 |
|----|------|------|
| mock 残留 | 无 | 模块零 mock/unittest 依赖；测试内 unittest.mock 仅用于 resolve_entry.PLUGIN_HOME 文档化测试缝（resolve_entry.py:236 明示支持） |
| 硬编码返回值 | 无实质违规 | `deps_satisfied: True`（:402）为上游不变量恒真（recommended_next ⊆ unblocked），非伪造；附 reason 披露来源 |
| 幻觉 API | 无 | 全部跨模块符号逐一核实存在（见维度 1 清单） |
| 未实现 TODO | 无 | TODO/FIXME/XXX/NotImplemented 零命中 |
| 过度实现 | 否 | PROFILE_CAPS 三档有真实 v1 行为差（lite 省 recent+overview、caps 1/3/5）；health deferred 为申报契约非烂尾；_clip 多点复用 |

---

## 五、硬门槛裁决

| 门槛 | 裁决 |
|------|------|
| P0 = 0 | **FAIL（P0=1）** |
| 5 维度全覆盖 | PASS |
| 每条发现 P0~P3 分级 | PASS |
| 设计一致性（change-triage/FEAT-033.json + AUDIT-154 §8 四条验收） | 部分——②只读幂等 ✓ / ③超时预算参数 ✓ / ④协议消费指向接线 ✓（重排归 FEAT-034，边界一致）；①「单次 CLI 输出全部热数据」受 P0-1 折损（活体 risks/recent 面失真）；triage files 漂移见 P3-8 |
| AI 专项 5 项 | PASS |

## 六、复审锚（供 R1 逐条比对）

R0 为首轮，无前轮 findings。R1 复审 MUST 逐条比对本报告 14 条 findings：重点核验 P0-1 修复后（a）mirror 与引擎语义逐点对齐或公共函数化（b）空行分段表 fixture 双向断言（不丢行 + 无幽灵表头计数）（c）活体形状下 risks.open 与引擎 parse_active_risks 同值；（d）P1-1 全阻塞 fixture 补充。

---

## 结论：NEEDS_CHANGE（P0=1/P1=1/P2=3/P3=9）

P0-1 为活体数据事实失真（非风格问题），修复 + 空行分段 fixture 差分测试为合并前置；P1-1 原则上本轮修改。NEEDS_CHANGE 非终态——Coordinator 返工后 MUST 发起 round 1 复审。
