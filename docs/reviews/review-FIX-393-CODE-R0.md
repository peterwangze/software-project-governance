# Review FIX-393 — CODE R0（后置代码审查：三解析器写入器终态判据对齐）

- **Task**: FIX-393（0.89.0 批次一首票——DEC-246）｜ **优先级**: P1
- **Round**: R0（首轮独立审查；无前轮 findings）
- **审查对象**: staged diff（`git diff --cached`，4 文件，+545/-6，HEAD=76c86a9）
  - `skills/software-project-governance/infra/task_priority.py`（+88/-6）
  - `skills/software-project-governance/infra/verify_workflow.py`（+39）
  - `skills/software-project-governance/infra/archive.py`（+60）
  - `skills/software-project-governance/infra/tests/test_fix393_writer_terminal_states.py`（新增 364 行 / 17 用例）
- **审查方式**: 逐行读 diff + 对照契约源码（task_row_update.py / contracts.py）+ 硬门槛命令全部亲跑 + HEAD 基线独立对照（本审查以临时 `git worktree` @76c86a9 + 活体 `.governance/` 拷贝替代 `git stash` 等效方案，全程未触碰 staged 状态）
- **审查结论**: **APPROVED_WITH_NOTES**（`unresolved_blockers=0`）
- **发现计数**: P0=0 / P1=0 / P2=1 / P3=4

---

## 1. 判据核验（对照契约源码，非采信申报）

| 声明 | 独立核验结果 |
|------|-------------|
| 终态 ⟺ 链首命中 committed **且** 〔op-<32hex>〕锚在场 | ✅ 三解析器实现一致（tp L317-321 / archive L477-488 / vw L10590-10605）；contracts.py L759 `"committed": ()` 为唯一空出边终态，L758 `completed→committed` 合法——故保留既有 ✅ 路径不动是正确的（completed 非终态） |
| task_priority / archive 为逐字节镜像 | ✅ 直接对照 `task_row_update.py` L225-233 `_STATE_MARKER_CHAIN`：七态顺序与 pattern 逐字节一致；守护测试另以 pattern 串相等断言钉住（`test_task_priority_mirror_equals_writer_chain` / `test_archive_mirror_equals_writer_chain`） |
| verify_workflow 按身份复用链对象 | ✅ vw L10591 `_WRITER_STATE_MARKER_CHAIN = task_row_update._STATE_MARKER_CHAIN`（import 位于 L92 模块级无条件）；守护测试 `assertIs` 身份断言（`test_verify_workflow_reuses_writer_chain_by_identity`） |
| 无锚 committed fail-closed 不猜终态 | ✅ 三处构造性核验成立：锚正则 `〔op-[0-9a-f]{32}〕` 不命中即返回 False，链首字不参与判断；写入器侧 `build_candidate_row` L484-486 确实向状态单元尾追加 `〔operation_id〕`（operation_id 形如 `op-<32hex>`），锚是写入产物的人面上的机器来源标记 |
| archive 侧「无锚 committed 显式排除」真实防住遗留 closed-marker 子串误读 | ✅ **该分支真实承重**：`_task_status_is_archivable` 的 closed_markers 含「已发布」子串（L526）——若无 L522-523 排除分支，「committed 已发布 (…)」无锚形态将命中该子串被判可归档；排除分支先于 closed_markers 扫描返回 False，负例被 `test_archivable_matrix` 的 `COMMITTED_RELEASED_NO_ANCHOR` 用例直接钉住 |
| 申报边缘问题 3 项 | 判定见 §4 |
| 「3 失败=基线既有」 | ✅ 见 §5 亲跑记录 #5/#6——同 3 用例同断言形态在 HEAD 基线复现 |

**附带语义核验**（申报未展开，审查补充确认）：活体 REL-087「committed 审查中 (…) 〔op-…〕」是真实写入器产物而非脏数据——`build_candidate_row` 的 splice 把 canonical `review` 词换成 `committed` 后，链序（committed 先于 review）+ post-splice re-check（L469-479）使该形态可被写入器自身无歧义读回；解析器判其终态（台账权威压过陈旧叙述「审查中」）与写入器自读语义一致，且有 `COMMITTED_REVIEWING_ANCHORED` 正例钉住。

---

## 2. 五维度结论（硬门槛：全覆盖）

| 维度 | 结论 | 依据（事实指向） |
|------|------|-----------------|
| 正确性 | **通过** | ①镜像=写入器链逐字节（task_row_update.py L225-233 对照）；②vw 分支插入点在「未完成/待完成」否决（L10628）与「已完成」（L10630）之后、✅ 分支（L10641）之前——「committed 已发布 (…) 〔锚〕——验收未完成」仍被否决守卫拦截（测试钉住）；③无锚形态在 vw 侧不会被 W-7 词表误判：`_w7_terminal_assertion_positions` 段首规则要求词前为段界（→/—/格首），「committed 已发布」的前缀 committed 非段界 → 非 assertion → 保持 Active（L10544-10568 构造性核验 + 测试负例）；④archive 开放标记先行（「committed 进行中…〔锚〕」经链首=dev 判非终态→不可归档，保守方向正确）；⑤`_status_is_candidate_eligible` 纵深防御分支（L372-376）边界：位于 ⏳ 前缀（L368）与 `_NON_CANDIDATE_MARKERS`（L370）之后、`_status_is_terminal_word`（L377）之前——理论缺口「⏳ committed…〔锚〕」会在 ⏳ 分支返回 True，但该行上游已被 `_status_is_completed` 判完成、永不进入本谓词，与既有 ✅ 分支注释声明的同构语义完全一致（P3-F5 记录）；⑥None/空串安全：tp/archive 侧 `str(status or "")`，vw 侧唯一调用点传入 `_status_clean_cell` 输出（恒为 str） |
| 安全性 | **通过** | 正则全部为线性交替+有界量词（`{32}`），无嵌套量词、无灾难性回溯；无注入面（无 eval/exec/shell/路径拼接）；无敏感数据硬编码；判据方向是收紧（无锚 fail-closed），缩小而非扩大伪造面 |
| 可维护性 | **通过** | 注释与代码一致——archive L516-521 排除分支注释声明的「误读路径」经构造性核验为真；镜像纪律在两处文件头文档化并指向守护测试；新增函数均 <30 行、职责单一；链双镜像（tp/archive）是声明的纯 stdlib 无对等耦合约束下的受测权衡（各文件头注明），可接受 |
| 性能 | **通过** | 每状态单元新增 ≤8 次线性正则搜索（锚 1 + 链 ≤7），单元短、数据量=单 tracker 文件；活体 `task-priority-analysis --force` 实测无感知开销（秒级完成） |
| 测试覆盖 | **通过** | 17 用例全真跑通过非 skip（0.13s）；覆盖：契约权威机器断言（5）＋ tp 正/负/依赖解锁/真实写入器端到端（7）＋ vw 判定矩阵/incomplete 镜像/Check 18c 供给（3）＋ archive 矩阵/表扫描（2）；守护断言真实有效（两 pattern 串相等 + 一 identity + 契约终态唯一性 + 锚正则对 `build_candidate_row` 真实产物的行为断言，并正确区分了写入器 `STATUS_CELL_OP_SUFFIX_PATTERN` 的单元尾锚定与解析器 search-anywhere 的刻度差异）；负载性负例（无锚+已发布子串）被直接钉住。缺口：边缘①混合链形态未加钉住测试（P3-F3） |

---

## 3. AI 专项五项（硬门槛：逐一结论）

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | **无** | 产品代码零 mock；测试中 `patch.object(vw, "SAMPLE_PATH", sample)` 为向临时文件注入的标准模块态替换（配 TemporaryDirectory），不 mock 被测行为本身；`_writer_committed_row` 调真实 `tru.build_candidate_row` 产物做端到端断言（`test_real_writer_product_end_to_end`），反伪造方向正确 |
| 2 | 硬编码返回值 | **无** | 产品代码无硬编码分支返回；测试 fixture 的锚 hex（ANCHOR_FEAT060 等）为活体单元格形态固化（文件头注明 DEC-213 省略纪律），属正当 fixture 数据而非对被测逻辑的硬编码 |
| 3 | 幻觉 API | **无** | 被引用符号逐一在源码核实：`tru._STATE_MARKER_CHAIN`(L225)/`STATUS_CELL_OP_SUFFIX_PATTERN`(L192)/`STATE_CANONICAL_MARKERS`(L199)/`build_candidate_row`(L403)；`contracts.TASK_STATES/TASK_TRANSITIONS`(L744/753)；`vw._status_is_completed_cell`(L10603)/`_is_incomplete_task_status`(L12502)/`_active_execution_packet_tasks`(L12606)；`archive._parse_priority_table_tasks`(L533)/`_parse_completed_task_versions`；`tp.TaskDep.is_completed`/`compute_unblocked_tasks`(L1593)/`parse_task_dependencies`——且 17/17 真跑通过即为存在性铁证 |
| 4 | 未实现 TODO | **无** | `git diff --cached` 全文 Select-String `TODO|FIXME|XXX|HACK` 零命中 |
| 5 | 过度实现 | **无** | 范围恰为三解析器+测试；+545 中 364 行（67%）为测试；search-anywhere 锚刻度有活体依据（FEAT-061 尾随叙述括号）、纵深防御分支镜像既有 ✅ 分支模式、archive 排除分支为负例所必需——每一面均有事实动机，无投机泛化 |

---

## 4. 边缘问题 3 项定级判定（Developer 披露 → Reviewer 裁定）

| # | Developer 披露 | Reviewer 裁定 | 说明 |
|---|---------------|--------------|------|
| ① | 混合链「🔄…→ committed 已发布〔锚〕」按链首=dev 判非终态（保守方向，无活体实例） | **定级恰当（P3），采纳** | 保守方向正确（已交付误判为活跃只会多推荐、不会丢工作）；tp 与 vw 两侧判定一致（vw 的 W-7 段首规则同样不救援该形态，无解析器分叉）；0.88 活体已交付批全为 committed 前缀直写形态，零实例。建议后续补一条钉住测试固化该语义（见 P3-F3） |
| ② | 链词表大小写敏感（Committed 大写不识别——逐字镜像的对齐代价） | **定级恰当（P3），采纳** | 逐字镜像纪律（守护测试钉 pattern 串）优先于猜测性大小写扩展，与 fail-closed 精神一致；写入器 canonical 形态为小写 `committed`（STATE_CANONICAL_MARKERS L205），活体语料无大写实例；大写+遗留闭环词的行仍走既有 legacy closed-marker 路径（行为不变，非回归）；大写无闭环词行保持活跃=保守侧。batch 2.3 结构性 join 落地后词表读取面整体退役 |
| ③ | FIX-393/REL-091 带〔op-〕锚但台账无对应 receipt（triage 机录非 task_row_update 写入）——batch 2.3 ops 结构性 join 时需区分锚来源 | **Developer 定性正确；本审查记 P2 遗留注记（F-1）** | 活体核实：FIX-393 行（〔op-ac7dcd0f…〕）、REL-091/092 行（〔op-fb75a729…〕）均为 triage 机录锚，链首=triaged/review 非 committed——**当前零终态误判实例**；但该披露揭示判据的证明力边界：锚证「机器写入的单元格」，不证「task_row_update 的 committed 翻转收据」。当前被词表门（链首必须=committed）兜住，batch 2.3 结构性 join 设计时必须区分锚来源（receipt join 为权威、锚仅为人面快速通道）——登记为 P2 跟踪项而非阻塞 |

---

## 5. 亲跑命令与关键输出（硬门槛证据，全部本会话实跑）

1. `python -m pytest skills/software-project-governance/infra/tests/test_fix393_writer_terminal_states.py -v` → **17 passed in 0.13s，0 skipped**（verbose 逐条 PASSED）
2. `python -m pytest skills/software-project-governance/infra/tests -k "task_priority or archive or current_active" -q` → **377 passed, 3760 deselected, 4 subtests passed**（16.99s，与申报 377P/0F 一致）
3. `python skills/software-project-governance/infra/verify_workflow.py task-priority-analysis --force` → **Total 49 — 40 completed, 8 unblocked, 0 blocked, 1 non-executable**；Recommended next = FIX-393/REL-091/REL-092/FEAT-065/FIX-390/391/392/394——**FEAT-060/REL-086/REL-087 均不在推荐**；**Blocked: None**（与申报逐项一致；Completed 桶中「🔄 已 lock 待派发…→ ✅ 完成…」形态经查为混合链既有 ✅ 路径+报告截断显示，非 FIX-393 误判）
4. `python skills/software-project-governance/infra/verify_workflow.py` → **Verification Result: PASSED，EXIT=0**
5. 基线红复现（staged 状态）：`pytest …::LoopRuntimeClaimAdapterTests …::FIX300DualCaliberAgreementTests -q` → **3 failed, 4 passed**：`test_claim_command_emits_complete_pass_report` + `test_fixture_identity_mode_agrees_with_engine_on_present_sources`（'PASS' != 'FAIL'，L296）+ `test_identity_host_source_drift_reproduces_divergence_shape`（'PASS' != 'BLOCKED'，L257）——与申报的类/数量/断言形态一致
6. HEAD 基线对照：`git worktree add %TEMP%\fx393-baseline-wt HEAD`（76c86a9）+ 拷贝活体 `.governance/`（等效于 stash 对照且不触碰 staged 状态）→ 同 3 用例 **3 failed, 4 passed，同断言形态** → **既有基线红，非本票引入** ✅；worktree 已清理，`git status` 复核 staged 四文件原样
7. 镜像核验：`task_row_update.py` L225-233 与 tp/archive 镜像逐字节人工对照一致（另测试面 pattern 串断言通过）；vw 为 identity 复用（`assertIs` 通过）

---

## 6. 发现列表（P0-P3）

> P0=0，P1=0。以下 P2 为非阻塞遗留注记（不阻塞合并），P3 为记录/建议级。

### P2（遗留注记，须跟踪）

- **[P2] F-1｜判据证明力边界：〔op-〕锚非 task_row_update 专属——batch 2.3 结构性 join 必须区分锚来源**
  - 位置：`task_priority.py` L218-221（`_WRITER_OP_ANCHOR_RE`）、`archive.py` L466、`verify_workflow.py` L10592；活体 `.governance/plan-tracker.md` L85（FIX-393 行）/L83-84（REL-091/092 行）
  - 事实：triage 机录同样向任务行写〔op-<32hex>〕锚（FIX-393/REL-091 活体行即锚在场而台账无 receipt）；「committed+锚」证的是机器写入的单元格，不是写入器 committed 翻转收据。当前被链首=committed 的词表门兜住（triage 形态链首=triaged/review），零活体误判。
  - 建议：batch 2.3（ops 结构性 join）设计时以 receipt join 为终态权威、锚降级为人面快速通道，并在设计文档显式记录锚来源枚举（task_row_update / triage 机录 / 未来写入器）。已由 Developer 披露，本审查确认其定性并登记跟踪。

### P3（记录/建议级，不要求修改）

- **[P3] F-2｜链词表大小写敏感为逐字镜像的既定代价**（边缘②）——位置：三处镜像链 committed pattern `\bcommitted\b`。大写形态活体零实例；写入器 canonical 为小写；大写+遗留闭环词仍走 legacy 路径非回归。维持镜像纪律正确，batch 2.3 后词表面退役。定级判定：恰当。
- **[P3] F-3｜混合链 committed 形态判非终态缺钉住测试**（边缘①）——位置：测试文件 fixtures（`MIXED_CHAIN_REOPENED` 为既有形态钉，混合链 committed 形态未钉）。建议后续批次补一条 tp/vw 双侧断言（「🔄 …→ committed 已发布〔锚〕」→ active/unarchivable）固化该保守语义，防止未来 W-7/链序调整时无哨兵。
- **[P3] F-4｜三处锚正则字面量仅行为级互证、无互等断言**——位置：tp L218-221 / archive L466 / vw L10592。守护测试以真实写入器产物行为断言三者（正确的负载性钉法），但三者字面量互相漂移（仍匹配真实锚的宽窄差）不会被捕获。可选：补一条三正则 pattern 串互等断言（一行）；或接受 batch 2.3 收敛时统一。
- **[P3] F-5｜`_status_is_candidate_eligible` 纵深防御分支的 ⏳ 前缀理论缺口**——位置：`task_priority.py` L368-376。假想形态「⏳ committed…〔锚〕」会在 ⏳ 分支先返回 True、FIX-393 分支不可达；但该行上游必被 `_status_is_completed` 判完成，永不进入本谓词——与 ✅ 分支既有注释声明的同构语义一致，实际不可达。仅记录，无需修改。

---

## 7. 验收标准核对与范围红线

| 验收项（triage 机录） | 核对 |
|----------------------|------|
| 三解析器判据对齐 | ✅ 链 identity（vw）/逐字节镜像+守护（tp/archive）/契约终态机器断言 |
| 正负测试 | ✅ 锚在场正例 ×4 形态 + 真实写入器端到端；无锚负例 + 非 committed 回归钉 |
| 活体验证零已交付票推荐 | ✅ 亲跑复现（§5 #3） |
| 不触碰 Check 18/18b 证据判据（FIX-390 范围） | ✅ diff 零涉及 |
| 不触碰 9-cell 行契约 | ✅ diff 零涉及 |
| 不触碰 Check 16/17 刻意分叉（✅-prefix 窄读） | ✅ `_COMPLETED_STATUS_PREFIX = "✅"`（vw L12300）不在 diff 中，窄读原样 |

---

## 8. 审查结论

**APPROVED_WITH_NOTES**（`unresolved_blockers=0`）

- 硬门槛全过：P0=0；五维度逐一有结论；AI 专项五项逐一有结论；每条发现带级别+位置+事实+建议。
- 判据实现与申报一致且经契约源码独立核验；fail-closed 双分支（无锚不猜终态、无锚排除 closed-marker 子串误读）均真实承重并被测试钉住。
- 全部验证申报（17/17、377P/0F、活体零推荐+Blocked=None+40 completed、全量 PASSED、3 失败基线既有）经亲跑逐项属实。
- P2-F1 为已披露的结构性边界（batch 2.3 跟踪项），P3×4 为记录/建议级；均不阻塞合并。

> Reviewer 声明：本审查为只读审查，未修改任何产品代码；唯一写入物为本报告文件。staged 状态在审查全程（含基线对照）保持原样。
