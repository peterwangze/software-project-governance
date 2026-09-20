# Code Review 报告 — FIX-368（Round 0 · 重派完成稿）

> 本稿为 R0 **重派完成稿**，取代同路径下前次中断的未完稿。中断稿已完成的验证（正确性 regex 语义、fixture 逐 hunk 对照、AI 专项等）直接吸收；其遗留的两个未裁决项本轮已闭环：①F-1（L14234 疑似同族偏移）→ **已实读 L14140-14314 裁决为确认的 P1**；②`_evidence_row_generic` 残留使用者交集性 → **已全量映射，零交集**。另新增中断稿未覆盖的 B 项全量清单（evidence 列读取点 9 处逐一判定）。
>
> **Round 声明**：R0（重派，无前轮完整 REVIEW 报告可比对；前次中断前 2 条已确认发现按任务指令直接采信、未重复验证：(1) `_plan_task_ids_from_hot_tracker` 无状态过滤——FIX-371 漏检面根因；(2) `_evidence_row_generic` 残留面集中于 gate 判定测试区段）。

| 项 | 值 |
|----|----|
| 任务 | FIX-368 — parse_impact_analysis_entries 列序修正（evd_type/description off-by-one；义务承接 FEAT-046 R0 P3-9） |
| 审查轮次 | R0（重派完成稿） |
| 审查对象 | 工作树未提交修改，diff 快照 `docs/reviews/diff-FIX-368.patch`（226 行，全文已读） |
| 涉及文件 | `skills/software-project-governance/infra/verify_workflow.py`（parse_impact_analysis_entries L12445-12453）；`skills/software-project-governance/infra/tests/test_verify_workflow.py`（fixture 迁移 4 处 + `_delivery_row` 对齐 + 新增 ParseImpactEntriesColumnLayoutTests L11824-11937） |
| triage | `.governance/change-triage/FIX-368.json`（P1 / target 0.87.0 / side_effect 无仓库外触碰 / requires_r1=false → R0 单轮足够） |
| 结论 | **APPROVED_WITH_NOTES** |
| unresolved_blockers | **0** |
| P0 / P1 / P2 / P3 | 0 / 1 / 1 / 3（P1/P2 均为**本 diff 未触碰的存量缺陷**，新票建议，不阻断本票） |
| 事实依据 | diff 全文逐行通读；verify_workflow.py 修改面及全部 evidence 解析点实读（L12421-12481 / L14140-14314 / L14200-14274 / L14460-14500 / L9630-9689 / L10022-10063 / L11975-12002 / L16935-16954 / L17008-17042 / L22195-22264 / L22515-22539 / L22788-22809 / L12249-12273）；test_verify_workflow.py 修改面实读（L11792-11937 / L12038-12132 / L12396-12500 / L16085-16139）；真实 `.governance/evidence-log.md` 实读（表头区 L1-40 + EVD-1118 行 L2422 + EVD-874 行 L30）；triage JSON 全文实读；task_priority.py RECO 写入器 L1851-2016 定位；Coordinator 实跑佐证：pytest 905 passed / 3 failed（均为 FIX-320 登记存量，零交集）、check-goal-alignment EVD-1118 **PASS 180 chars**、entries 4→60 显影面已登记 FIX-371 |

---

## 一、变更摘要（基于 diff 事实）

1. **引擎修正**（verify_workflow.py L12451-12452）：`evd_type` 取列 parts[4]→parts[3]，`description` parts[5]→parts[4]；附 6 行注释记录 LIVE 列布局与 EVD-1118 根因。`file_location = parts[6]`（L12453）逐字未动。
2. **fixture 迁移**：`_impact_evidence_row`（L11792-11804）legacy `cat|type|desc` → LIVE `type|desc|fact`；新增 `_evidence_row_live`（L11807-11821）；GoalAlignmentTests 2 处（L12068、L12105）+ UserImpactTests 2 处（L12431、L12466）`_evidence_row_generic`→`_evidence_row_live`；StructuredEvidenceTests `_delivery_row` 去 `维护` cat 格、type=修复闭环 前移。
3. **新增测试类** ParseImpactEntriesColumnLayoutTests（L11824-11937，已确认落地）：3 测试钉住列序。

## 二、修复正确性核心实证（LIVE 布局三方验证 + 异构行形）

修复声称 LIVE 布局 = parts[3]=type / parts[4]=description / parts[5]=事实依据 / parts[6]=file_location。三方独立实证一致：

1. **真实数据**：evidence-log.md L2422 EVD-1118 行 `| EVD-1118 | REL-082 | 治理记录 | **…目标对齐：…用户影响：…** | 事实依据：… | skills/…infra/{…} | Coordinator… | 日期 | G11 | ✅ 完成 |`——逐列吻合；REVIEW 行（L5-11）同构。
2. **triage 程序化解析**：FIX-368.json reason 记录 `_split_governance_table_row` 直调结果——parts[3]=类型/parts[4]=描述（两行正则均命中）/parts[5]=依据（均不命中）/parts[6]=文件列正确。
3. **切分器锚点**：`_split_governance_table_row`（L12249）按 `|` 切分、保留 JSON/code-span 内管道，行首管道产生 parts[0]=""——与旧 `split("|")` 索引约定一致，引擎与测试同一锚点。

**异构行形兼容**：热证据文件同时存在 10-cell 行（EVD-1118）与 9-cell 历史行（L30 EVD-874，无独立文件列）。两种行形中 type/description 均在 parts[3]/parts[4]（事实依据列插入点在 description 之后）→ 修复对两类行形均取值正确；`len(parts) < 8` 早退守卫不误杀任一行形。

**行为变化面**：evd_type 修正后 `_is_review_evidence`/`_is_audit_or_review_type` 过滤器（L12465-12466）首次收到真实类型值——审计/审查类型行被正确排除出 product_delivery，属恢复设计意图而非回归；entries 4→60 显影即此，已登记 FIX-371 裁决票。新测试行 type 均不含审查/审计 token，不触发误排（中断稿已验 L12224-12233）。

## 三、5 维度逐项结论

### 维度 1：正确性 — ✅ 通过
- 列序修正与真实 EVD-1118 行逐列吻合（三方实证见上）；Coordinator 实跑 check-goal-alignment EVD-1118 PASS（180 chars）端到端佐证。
- 边界守卫保留：`len(parts) > 3/> 4` 与原 `> 4/> 5` 同构；`len(parts) < 8` 早退未动。
- regex 语义正确（中断稿已验）：check_goal_alignment 目标对齐截断 regex（L12521-12525）要求「用户影响」带冒号才截断，fixture DESC 中间提及无冒号不误截断。
- hot task 前提成立：`_plan_task_ids_from_hot_tracker` 无状态过滤（已确认发现 1）使 ✅ 行入 hot set，product_delivery_by_current_task_type 分支可达。
- **P1-1/P2-1 为既有代码缺陷，非本 diff 引入**（见 Findings）。

### 维度 2：安全性 — ✅ 通过
- 无新输入面/IO/权限路径；纯读解析 + 全列 len 守卫；缺文件 fail-closed 返回 []（L12430-12431）；无敏感数据；真实环境零触碰（triage side_effect 一致）。

### 维度 3：可维护性 — ✅ 通过（带 P3）
- 修正点注释精确记录布局契约/偏移方向/根因；`_impact_evidence_row` docstring 记录 pre-fix fixture 为何掩盖 bug——知识留档质量高。
- P3-1：`_evidence_row_generic` legacy builder 与 `_evidence_row_live` 并存（30+ 调用点），套件内双布局漂移面；引擎层尚无单一 LIVE 布局常量/访问器（≥3 种列约定共存，见 B 项）。

### 维度 4：性能 — ✅ 通过
- 单趟逐行扫描 + O(1) 列读取不变；hot set 一次计算（L12434）；新测试为临时目录小 fixture。

### 维度 5：测试覆盖 — ✅ 通过（带 P3）
- 核心路径：explicit_impact 面 / product_delivery_by_current_task_type 面（修复前死分支复活）/ Check 16+17 端到端 PASS 面。
- 回归钉扎：4 处迁移 fixture 的 FAIL 方向断言全部保留，无弱化（见 C 项）；回退旧索引 → 7+ 测试红（见 D 项）。
- 实跑事实：905 passed / 3 failed（FIX-320 存量，零交集）；本票未删除任何测试。
- P3-3：缺镜像负样本（见 Findings）。

## 四、复核点逐项（A~F，本轮核心增量）

### A. `_evidence_row_generic` 残留使用者与 Check 16/17 交集性 — ✅ 零交集，不影响本票语义
- 残留调用点全集：test L16191-16993（GateAutoJudgmentEvidenceQualityTests 等 gate 判定区段）。
- `check_goal_alignment()`/`check_user_impact()` 调用点全集（grep 全量）：L11930-12475。
- 两线段**零重叠**；残留消费者为 gate 自动判定面（registry-backed + 关键词类），不按 LIVE type 列读取；套件全绿佐证无活动破坏。升级中断稿的「抽样 2 处」结论为全量映射。
- 诚实边界：30+ 调用点未逐点深潜每个 gate 消费者的列依赖（时间盒）——以全绿套件 + registry/keyword 消费模式缓解，风险低（中断稿 F-2 的更名/互引警示建议维持）。

### B. 其他 evidence 列读取点同类偏移排查 — ❌ 发现 1 处确认同族 P1 + 1 处约定漂移 P2；其余 7 处安全

verify_workflow.py 全部 evidence 行解析点清单（`startswith("| EVD-")` 12 处 × EVIDENCE_PATH 读取点 19 处交叉定位，无遗漏）：

| # | 位置 | 读取列 | 判定 |
|---|------|--------|------|
| 1 | parse_impact_analysis_entries L12451-12453 | parts[3]/[4]/[6] | ✅ 本票修复，LIVE 正确 |
| 2 | **check_agent_activation（Check 20）L14234-14235、L14291-14295** | **parts[4]/[5] 当 type/desc** | ❌ **同族 +1 偏移，确认（P1-1）** |
| 3 | **evidence format check L10024-10061（注释 L10033-34 自证旧约定）** | **按 3=Stage/4=Type/5=Description** | ❌ **约定漂移（P2-1）** |
| 4 | _task_routing_exempt type map L14492-14493 | parts[3]/[4] | ✅ LIVE 正确（反证 LIVE 为现行约定） |
| 5 | GovernanceDataSource L9641/9668/9685（get_all_evidence_task_ids/map/_extract_evidence_entries） | 仅 parts[1]/[2] | ✅ 布局无关 |
| 6 | _check_evidence_mentions L16949 | 全文关键词 | ✅ 布局无关 |
| 7 | snapshot RECO 判定 L22246/22256 | parts[4]/parts[2] | ✅ 正确（RECO 行为 10 列布局——task_priority.py L1958 写入器同源「the machine RECO-{task} evidence row text (10 columns)」） |
| 8 | 列数对账 L11986、L22516/22524（write-guard 对账） | 仅列数计数 | ✅ 布局无关 |
| 9 | write-guard 行清单 L22798 | 仅行 id（首个 cell） | ✅ 布局无关 |
| — | _iter_archive_aware_evidence_units L17012-17035 | 整行产出，无列索引 | ✅ 布局无关 |

**P1-1（确认——升级中断稿的 F-1「疑似」裁决）**：check_agent_activation（Check 20，SYSGAP-036：P0 跨层任务 Analyst/Architect 激活检查）两段解析（L14234/14235 主扫 + L14291/14295 交叉引用扫）在 LIVE 布局下 evd_type 读到**描述列**、description 读到**事实依据列**。效果链（L14274-14313）：
- `evd_type == "影响分析"` 恒假（描述列长文 ≠ 四字标签）；`"影响分析" in description` 实际扫**事实依据列**——检测从「类型列判定」弱化为「依据列偶然提及才命中」；
- L14291 第二段 `if evd_type != "影响分析": continue` 在 LIVE 下近乎恒 continue → 跨引用路径基本死亡；
- has_impact_analysis 系统性漏检 → analyst_bypassed 低计 → `result["pass"]=True` 轻松达成 → **fail-open 盲检**。author 检查（parts[7]）列位未漂移，属残留的部分检测能力。
- 危害定性：governance 检查面静默失效（fail-open），同类等级参照 FIX-237 R0 P1-1（fail-open 豁免）。**存量缺陷、非本 diff 引入**，按修改纯粹性（D4）不阻断本票 → 新票义务（建议与 P2-1 合并为「evidence 列约定统一」专项票，与 FIX-371 并行规划）。

**P2-1（新增发现，中断稿未覆盖）**：evidence format check（L10033-34 注释自证）按 `3=Stage/4=Type/5=Description/…` 含 Stage 列的旧约定。LIVE 行下 parts[5]=事实依据被当 Description（依据列为空 → 误报 "missing Description"）；9-cell 历史行（如 EVD-874，len(parts)=10<11）→ 误报 "only 9 fields (expected ≥10)"。方向为**误报噪声**（fail-noisy）非静默，降为 P2，并入同一统一票。

### C. 4 处 fixture 迁移 hunk 断言语义等价性 — ✅ 等价，无弱化（吸收中断稿逐 hunk 对照 + 本轮复核）
- GoalAlignmentTests 2 处（L12068/L12105）、UserImpactTests 2 处（L12431/L12466）：调用参数与断言零改动、均关键字参数与 `_evidence_row_live` 签名对位；FAIL 方向语义（缺目标字段→FAIL；有目标缺用户影响→FAIL+「缺少 用户影响」）完整保留。
- 触发条件等价：两布局下 evd_type="实现" 均命中产品类型集、file=verify_workflow.py 均命中产品路径。
- `_delivery_row`：仅列布局对齐（type=修复闭环 前移、插空 fact 列），与引擎修正同向，必要伴随。
- 加分项：迁移后 fixture 在引擎回退场景反而更红（D 项），守卫强度净提升。

### D. 新测试类断言强度 — ✅ 真实钉住（引擎回退必红，7+ 测试翻转）
- `test_explicit_impact_type_read_from_type_column`：回退后 evd_type=DESC（≠影响分析）→ entries=0 ≠ 1 → **红**；`description==DESC` 断言在旧索引读到 FACT → 双红。
- `test_product_delivery_type_read_from_type_column`：回退后 evd_type=DESC ∉ 产品类型集 → entries=0 → **红**。
- `test_check_goal_and_user_impact_pass_on_live_layout`：**判别性构造**（DESC 含双字段、FACT 不含）→ 新引擎双 PASS；回退拿 FACT 列匹配必双 FAIL → **红**。
- 另有 4 处迁移 fixture（entries=0 ≠ 断言 1）→ 回退翻转面 ≥7 测试。绿→红网成立。

### E. file_location=parts[6] 不变验证（triage 红线）— ✅ 通过
- diff 中该行为未触碰上下文行；现文件 L12453 逐字未动。真实 EVD-1118 行 parts[6]=skills/… 文件列 ✓。triage reason 明确记录「file_location=parts[6]（文件列）正确」红线，本 diff 遵守 ✓。新测试 `assertEqual(entries[0]["file_location"], self.FILE_LOC)` 正向钉住。
- 结构性原因（中断稿洞察，维持）：legacy 与 LIVE 均 10 数据格、file 均落 parts[6]——这正是原 bug 只伤 evd_type/description、file_location 长期「看起来正常」的原因。
- 观察记录（并入 P3，非缺陷）：9-cell 历史行 parts[6] 为 author 列——修复前后语义完全一致（`_is_product_code_location(author 串)=False`，与修复前相同），DEC-168 列数对账面已覆盖 heterogeneous 行形。

### F. 5 维度 + AI 专项 5 项 — ✅ 见第三节与下表

| # | AI 检查项 | 结论 |
|---|-----------|------|
| 1 | mock 残留 | ✅ 无——`patch.object(vw, SAMPLE_PATH/EVIDENCE_PATH)` 为套件标准路径注入，非 mock 残留 |
| 2 | 硬编码返回值 | ✅ 无——生产改动仅列索引与注释；测试常量为 fixture 数据 |
| 3 | 幻觉 API | ✅ 无——引用的引擎函数/fixture 构造器/切分器均实证存在且签名一致 |
| 4 | 未实现 TODO | ✅ 无新增 TODO/FIXME/占位 |
| 5 | 过度实现 | ✅ 无——2 行索引修正 + 注释 + fixture 迁移 + 1 新测试类；无顺手重构、无范围外文件 |

## 五、Findings 列表

| # | 级别 | 位置 | 描述 | 处置建议 |
|---|------|------|------|---------|
| P1-1 | **P1 关键（存量，非本 diff 引入）** | verify_workflow.py L14234-14235、L14291-14295 | Check 20（check_agent_activation）同族 +1 列偏移：LIVE 下 evd_type 读描述列、description 读事实依据列 → Analyst 激活检测系统性漏检 → analyst_bypassed 低计 → **fail-open 盲检** | 新票入账（与 P2-1 合并「evidence 列约定统一」票）；不阻断本票 |
| P2-1 | P2 建议（存量，非本 diff 引入） | verify_workflow.py L10024-10061 | evidence format check 按含 Stage 列旧约定（注释 L10033-34）→ LIVE 行依据列被当 Description、9-cell 历史行误报 field-count | 同上票捆绑 |
| P3-1 | P3 | test_verify_workflow.py L16092-16103 | `_evidence_row_generic` legacy builder 与 LIVE builder 并存（L16191-16993 全量映射确认与 Check 16/17 零交集），双布局漂移面/误用风险 | 随统一票迁移或更名 `_evidence_row_legacy` + docstring 互引警示 |
| P3-2 | P3 | 新测试类 | 缺镜像负样本（FACT 列含目标对齐/用户影响而 DESC 列不含 → 应 FAIL 的显式钉子；现由判别性构造隐式覆盖） | 后续维护轮补充 |
| P3-3 | P3（留档） | 新测试类 DESC 常量 | fixture 用户影响子字段为合规变体，真实 EVD-1118 行子字段不合格面由 FIX-371 承载——防后续误以为 Check 17 对真实行已全 PASS | 无需改动；FIX-371 处理时回看 |

**P0 计数 = 0。**

## 六、硬门槛裁决

| 门槛项 | 阈值 | 裁决 |
|--------|------|------|
| P0 阻塞问题数 | = 0 | ✅ 0 |
| 5 维度全覆盖 | = 100% | ✅ 正确性/安全性/可维护性/性能/测试覆盖逐一有结论 |
| 每条发现标注级别 | = 100% | ✅ P1×1 / P2×1 / P3×3 全标注 |
| 设计一致性检查 | 已完成 | ✅ 与 triage FIX-368 验收面一致：列序修正主验收（EVD-1118 误报消除，PASS 180 chars 实测）达成；子字段/显影面分票 FIX-371 无范围蔓延；FEAT-046 R0 P3-9 义务承接闭环；D4 修改纯粹性遵守 |
| AI 代码专项 5 项检查 | 全部完成 | ✅ 见 F 项表 |

## 七、覆盖度诚实声明（未覆盖项）

1. `check_user_impact` 函数体（L12572+）未逐行审读——子字段枚举静态匹配未做；由实跑 905 passed（含三个新测试）佐证（中断稿同项，维持）。
2. `_evidence_row_generic` 30+ 残留使用者的 gate 消费者列依赖未逐点深潜——以全量行段映射（零交集）+ 全绿套件缓解（A 项已声明）。
3. P1-1/P2-1 的运行时实际输出未复跑验证（静态裁决）；修复属新票义务，届时以红绿实测闭环。

## 八、结论

**APPROVED_WITH_NOTES（unresolved_blockers=0）**

理由：列序修正正确且被真实 EVD-1118 行形状、triage 程序化解析、切分器锚点三方实证 + 实跑 PASS 双重佐证；file_location 红线遵守；4 处 fixture 迁移语义等价无弱化；3 新测试 + 4 迁移构成真实红绿翻转回归网（回退必红）；5 维度与 AI 专项全过；零 P0。P1-1（Check 20 同族偏移盲检——中断稿疑似项本轮实读裁决为确认）与 P2-1（格式检查旧约定）均为范围外存量缺陷，按修改纯粹性留作新票义务，建议与 FIX-371 并行规划「evidence 列约定统一」专项。

附带披露（非审查范围裁决）：Developer 结构化结论缺席（interrupt 收尾），本报告基于 Coordinator 代验的测试实跑事实；check-user-impact 对真实 EVD-1118 的子字段不合格面已登记 FIX-371，不属本票验收面。

*审查人：Code Reviewer sub-agent（R0 重派完成稿）· 证据锚点均为现工作树行号，可复查。*
