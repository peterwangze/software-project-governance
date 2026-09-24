# review-FIX-376-CODE-R0 — FIX-371 审查遗留候选合并票（代码审查 · R0）

> **Round 声明**：R0（首轮审查，无前轮 REVIEW 报告可比对）。审查对象 = 工作树未 commit 修改（2 文件 +78/-23）：`skills/software-project-governance/infra/verify_workflow.py`（F-3 RTL 扫描 + F-4/F-5 零调用 helper 删除 + F-7 docstring 勘正）与 `skills/software-project-governance/infra/tests/test_verify_workflow.py`（F-6 两新用例）。
>
> **审查方法**：逐行 diff 通读 + 关键函数全量阅读（`_plan_hot_tracker_task_statuses` / `parse_impact_analysis_entries_with_exemptions` / `parse_current_active_tasks` / `_status_is_completed_cell` / `_governance_table_cells` / `check_goal_alignment`）+ 4 项独立实测（活体等价探针复现、两用例双树运行、主运行前后对比、全量套件 + 28 失败节点 HEAD 重放）。实测产物存档于 `%TEMP%\fix376_probe\`（probe_ltr_rtl.py / out_current.txt / out_head_full.txt / diff88.txt / pytest_full_current.txt / pytest_head28.txt）。审查全程未修改产品代码与 `.governance/`；临时树位于 %TEMP%（`git archive HEAD` 提取，不含工作树改动）。

---

## 0. 总结论

**APPROVED_WITH_NOTES**（`unresolved_blockers=0`）

| 级别 | 计数 |
|------|------|
| P0 阻塞 | **0** |
| P1 关键 | **0** |
| P2 建议 | **1**（F-B） |
| P3 讨论 | **3**（F-A / F-C / F-D） |

零 P0、零 P1：F-3 改动正确且豁免面可证明零变化；F-4/F-5 删除安全；F-6 定性（预实现即绿 = 覆盖缺口补齐）经双树实测坐实；向后兼容声明核实。P2/P3 详见 §4，均不阻塞合并。

---

## 1. MUST 重点审查项逐项核验

### 1.1 F-3 RTL 扫描正确性 — ✅ 通过（附关键澄清，见 F-C）

**实现核验**（verify_workflow.py:12293-12300）：

```python
status = ""
for cell in reversed(cells):
    if cell.startswith(_COMPLETED_STATUS_PREFIX):
        status = cell.strip()
        break
if not status and cells:
    status = cells[-1].strip()
statuses[match.group(1)] = status
```

- `reversed(cells)` 作用于 list（`_governance_table_cells` L12408-12414 返回 list），语义正确：取**最右**的 ✅ 词首 cell。
- **fallback 语义逐字保持**：实现块中 fallback 分支（「状态为空且 cells 非空」的条件判定 + 直取末列 cell 文本的条件赋值，字面见上列实现块）与改动前完全一致（diff 仅替换循环行与注释）；空 cells 防护（`and cells`）保留——且该分支实际不可达（L12277 正则要求 `| ID |` 形态，cells 必非空），防御性冗余无副作用。
- **活体探针一致性**：审查者独立复现探针（复刻 LTR/RTL 双扫描 + 与真函数对拍）结果与 Developer 申报完全一致：**130 行 statuses 全等、completed 豁免集 84/84 全等、status 内容 diff=0**。行形态实测分布：compact（✅@末列）25 / legacy（✅@倒数第二列）59 / fallback-last（活跃行）46——F-7 docstring 双形态描述与真实数据吻合。

**关键澄清（RTL 到底修了什么、没修什么）**：

- **豁免面零变化是定理而非仅经验**：豁免谓词 = `status.startswith("✅")`（L12575-12579），为真 ⟺ 该行**存在**至少一个 ✅ 词首 cell。该存在性与扫描方向无关（LTR 取最左 ✅ cell、RTL 取最右 ✅ cell，二者同时存在或同时不存在）→ LTR→RTL 逐行豁免判定不变。RTL 仅在「一行内 ≥2 个 ✅ 词首 cell」时改变**返回内容**（取最右者，即状态列候选）；实测当前热表 0 行属于该情形（early-pickup=0、内容 diff=0），与申报「diff=0」吻合。
- **「活跃行非状态 cell ✅ 词首误豁免向量」未被 RTL 消解**：活跃行（真实状态非 ✅）若更早列存在 ✅ 词首 cell，LTR 与 RTL 都会选中该 cell → 误豁免在两方向下**等价存在**。代码注释（L12287-12291）已如实将其披露为「Residual theoretical vector」并点名列位锚定为未采纳备选——**代码内披露诚实、无过度申报**；但 DEC-232 决策票须显式记载此不可消解性（见 F-C，含方向不变性证明），防止任何「RTL 已消解该向量」的误读。

### 1.2 F-4/F-5 删除安全性 — ✅ 通过

全仓三重复核（`git grep` HEAD、`git grep` 工作树、文件系统级 grep 含未跟踪文件）：

| 位置 | 结果 |
|------|------|
| 工作树代码（verify_workflow.py / tests/ / hooks/） | **零引用** |
| HEAD 代码 | 仅定义本身（verify_workflow.py:12281/12290）+ 旧 docstring 自引（:12239，已随本次 docstring 重写一并清除）——**HEAD 即零调用方**，删除无孤儿化调用 |
| `docs/reviews/review-FIX-287/349/368/371-CODE-R0.md` | 历史审查报告中的记录性提及——合法历史档案，非代码引用 |
| `project/e2e-test-project/.../verify_workflow.py`（未跟踪夹具） | :6785 自带定义 + :7000 自带调用——**自包含**，非对主树被删 helper 的悬空引用（F-8 已知漂移，见 F-D） |

消费方核验：`_plan_hot_tracker_task_statuses` 唯一消费点 = `parse_impact_analysis_entries_with_exemptions`（:12574 `hot_task_statuses = ...`）；旧 helper 的内联等价 `set(hot_task_statuses)`（:12580）与 completed 集内联推导（:12575-12579）均在 FIX-371 已就位，本次删除零行为影响。主运行 exit 0 + 全量套件零 diff 致因翻转（§1.6）提供运行时佐证。

### 1.3 F-6 测试实质 + 预实现即绿定性 — ✅ 通过（实测坐实）

**F-6① `test_goal_alignment_exempts_legacy_req_shape_status_second_to_last`（test_verify_workflow.py:12667-12692）**：

- 夹具：legacy REQ 形态两行——REQ-997 ✅ 已交付（状态=倒数第二列，末列=`EVD-997 / 0.87.0` 闭环路径）+ REQ-998 🔄 进行中。
- 断言（:12688-12692）：`pass=False`（活跃 legacy 行零豁免仍 FAIL——非弱化红线）+ `entries==["REQ-998"]` + 豁免账本含 `{"task_id": "REQ-997", "status": "✅ 已交付"}`。
- **判别力证实**：若实现误读末列（`EVD-997 / 0.87.0`，无 ✅ 词首），REQ-997 不豁免 → entries 变 `["REQ-997","REQ-998"]` → 断言失败。确实钉住「legacy 形态按状态列（倒数第二列）✅ 词首读取」。

**F-6② `test_parse_mixed_fanout_row_exempts_terminal_and_keeps_active`（:12694-12711）**：

- 夹具：单 EVD 行覆盖 `FIX-995, FIX-996`（✅ 已完成 + 🔄 进行中）。
- 断言（:12707-12711）：entries==["FIX-996"]、豁免账本==[FIX-995 带状态串]、legacy wrapper 同返回 ["FIX-996"]。
- **判别力证实**：行级豁免（整 EVD 行豁免）会丢失 FIX-996；无豁免则 entries 含 FIX-995——两种错误实现均使断言失败。确实钉住「按任务粒度分流」（对应 L12616-12629 的 `for covered_task_id in target_ids` 分流循环）。

**预实现即绿实测**：`git archive HEAD` 全树提取 + 覆盖当前测试文件 → 两用例对 **HEAD 代码 2 passed**（63.81s）；当前树同样 2 passed（0.14s）。两夹具行均为单 ✅ cell（方向无关）+ 被测路径零调用被删 helper → 逻辑上也不可能红。**Developer TDD 披露定性成立：被钉行为预存在（FIX-371 交付），无可观测红相，未伪造红相；R0「覆盖缺口而非行为缺陷」定性正确。**

### 1.4 豁免面零变化声明 — ✅ 通过（方法学抽验 + 定理化）

- Developer 探针方法学（LTR/RTL 双实现对拍 + statuses 全等 + completed 集对比 + diff=0）设计合理；审查者独立复现**逐项命中**：130/84/84/0，且探针 RTL 重放与真函数 `==` 全等（方法学自洽）。
- 更进一步：豁免面零变化可**证明**（§1.1 方向不变性论证），不依赖当前数据的偶然性——即使未来热表出现多 ✅ cell 行，豁免面仍不变（仅账本状态串内容可能不同，且 RTL 取最右者更接近真实状态列，属改善）。
- 残余向量（活跃行 + 早列 ✅）活体扫描：**0 行**命中——「theoretical」定性属实。

### 1.5 DEC-232 草案质量 — ⚠️ 部分完整（P3，F-C）

- `.governance/decision-log.md` **尚无 DEC-232 记录**（全 .governance grep 零命中）——决策票尚未入账；现行「草案」= 代码内文档（verify_workflow.py docstring L12252-12259 刻意分叉段 + 注释 L12283-12292）。
- 已覆盖：①豁免谓词保持窄 ✅ 词首、不扩至 FIX-292 `_status_is_completed_cell` 权威谓词的理由（扩面将扩张 DEC-227 路线 b 豁免语义；混合链 🔄→✅ 保持 guarded = 保守 false-FAIL 方向）——理由充分，与 L10545-10569 谓词语核相符；②残余理论向量披露（活跃行 + 早列 ✅）。
- **缺口**：列位锚定备选「未采纳」仅陈述事实、**未记载否决理由**（见 F-C 建议内容）。

### 1.6 向后兼容 — ✅ 通过

- diff 范围核实：仅 2 文件（`git diff --stat` = 46+55 行）；无 argparse/CLI 入口/子命令 hunk——**CLI 零变更属实**。
- legacy wrapper `parse_impact_analysis_entries`（:12539-12554）未触碰，语义不变（仅返回非豁免行）——**wrapper 未触碰属实**（F-6② 第三断言亦为其留检）。
- `_plan_hot_tracker_task_statuses` 签名与返回形态（dict）不变；`_current_release_task_ids` 等相邻函数未动。

---

## 2. 五维度结论

| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | ✅ 通过 | RTL/fallback/空 cells 防护逐行核验（§1.1）；方向不变性定理 + 活体 130 行对拍；`_status_is_completed_cell` 混合链语义与 docstring 描述一致（L10545-10569）；删除 helper 在 HEAD 即零调用（§1.2） |
| 安全性 | ✅ 通过 | 纯本地文件读取解析，无输入注入面/密钥/权限变化；`reversed()` 为内建；无幻觉 API（`_governance_table_cells`/`_COMPLETED_STATUS_PREFIX` 均实存于 L12408/L12233） |
| 可维护性 | ✅ 通过（净改善） | 死代码删除（-14 行）；docstring 从「单源同 scan-source」误述勘正为双形态+刻意分叉留档（FIX-292 谓词分叉显式化）；F-7 勘正与真实数据形态吻合（25/59/46） |
| 性能 | ✅ 通过 | `reversed()` O(1) 迭代器，复杂度不变；删除无运行时收益损失（本就零调用） |
| 测试覆盖 | ✅ 通过（附 P2 缺口 F-B） | +2 行为级用例（走 `check_goal_alignment`/`parse_*` 公开路径，非 mock 捷径），legacy 形态豁免与 fan-out 分流双缺口补钉；**但 F-3 RTL 自身行为变更无判别性用例**（见 F-B） |

## 3. AI 代码专项 5 项检查

| # | 检查项 | 结论 |
|---|--------|------|
| 1 | mock 残留 | ✅ 无——新增代码无 mock；测试中 `patch.object(vw, "SAMPLE_PATH"/"EVIDENCE_PATH")` 为标准路径重定向，非残留 |
| 2 | 硬编码返回值 | ✅ 无——改动为扫描方向与文档，无返回值伪造 |
| 3 | 幻觉 API 调用 | ✅ 无——`reversed`/`startswith`/`strip` 全部内建；引用的符号均实存且被验证 |
| 4 | 未实现 TODO | ✅ 无——diff 无 TODO/FIXME 残留；残余向量已文档化为显式决策而非悬置 TODO |
| 5 | 过度实现 | ✅ 无——单行行为变更 + 文档 + 删除，修改纯粹（D4）；未顺手扩豁免面（克制正确） |

## 4. 发现清单

### F-B | P2 | F-3 RTL 行为变更缺判别性测试钉

- **位置**：verify_workflow.py:12294（`for cell in reversed(cells):`）；对照夹具 test_verify_workflow.py:12672-12679、:12699-12702（均单 ✅ cell）
- **事实**：RTL 的全部行为差异集中在「一行内 ≥2 个 ✅ 词首 cell」场景（LTR 取最左 / RTL 取最右）；现有全部夹具与活体数据（0 行多 ✅）均无法区分两实现——若未来重构回退 LTR，**套件零失败、活体零差异**，本票修复静默失效。
- **建议**：补一条多 ✅ cell 判别用例（如 `| REQ-997 | … | ✅ 说明文字 … | ✅ 已交付 | path |`，断言账本 status == 最右 ✅ cell 原文；该用例在 LTR 下必红），或随 DEC-232 决策票一并裁决承载。不阻塞合并。

### F-A | P3 | F-6① 夹具版本字面量引入 +1 条 static-version-pin WARN（未注册豁免）

- **位置**：test_verify_workflow.py:12674（`"| ✅ 已交付 | EVD-997 / 0.87.0 |"`，token `0.87.0` = 当前活跃版本）；checks/version.py:280-282（registry 仅含 FIX-371 的 `(12375, "0.87.0")` 行）、:331-339（实树零未豁免 pin 契约）
- **事实**：实测主运行对比——HEAD 树无此 WARN，当前树新增 1 条 `[WARN] static-version-pin: test_verify_workflow.py:12674 pins the active version "0.87.0"`（advisory，exit 0 不变）。Developer「主运行 1179 行逐行全等」在**实现层 delta 口径下成立**（TDD 顺序 before = HEAD 码 + 新测试，两条输出本就同含此 WARN——实测 1179==1179）；**完整 HEAD↔工作树对比**则恰有此 +1 行差异，如实披露。另注：基线本身已含同族 WARN（:12550 `_plan_line` 的 0.87.0 pin，两轮输出均在，非本票引入）与 stale-12375 豁免告警（HEAD 即存在，非本票引入）；插入点 12664 位于 12375 之后，无行移位、无新增 stale 告警。
- **建议**：按 DEC-213③/FIX-361 惯例二选一——在 STATIC_PIN_EXEMPTIONS 注册 `(12674, "0.87.0", _REASON_FIXTURE_ROW_TEXT)`，或将夹具字面量改为非活跃版本（如 `EVD-997 / 0.86.0`）。0.88.0 bump 后该 WARN 自休眠，不阻塞。

### F-C | P3 | DEC-232 决策票完整性缺口（列位锚定否决理由未记载 + 不可消解性须显式化）

- **位置**：verify_workflow.py:12289-12291（"column-position pinning was R0's alternative and is not adopted"——无理由）；`.governance/decision-log.md`（无 DEC-232 条目）
- **事实**：验收口径「F-3 决策票留档（保守方向可延后）」尚未兑现；代码内草案已含残余向量披露与谓词不扩面理由，但缺两要素。
- **建议**（DEC-232 入账时补齐）：①记载否决列位锚定的理由——热表 compact/legacy 形态长期共存且历史上多次漂移（FIX-287 三套列位真相教训），钉列位将新立第二列位真相源并随布局漂移腐化，而方向不变性已保证豁免面安全；②显式记载「RTL 不消解活跃行早列 ✅ 误豁免向量（方向不变性定理）」防止后续票误判该向量已闭合；③附活体基线（early-pickup=0、多 ✅ cell=0、130 行对拍）作为 conservative 备查数据。

### F-D | P3 | F-8 e2e 夹具副本漂移按验收口径遗留（观察）

- **位置**：project/e2e-test-project/skills/software-project-governance/infra/verify_workflow.py:6785（旧 `_plan_task_ids_from_hot_tracker` 定义）、:7000（自带调用）
- **事实**：票标题列有 F-8 但 diff 未触碰；对照 plan-tracker FIX-376 验收口径（「F-3 决策票留档 + 清理类落地 + 测试缺口补钉」）与 FIX-371 R0 F-8 处置（「随下次夹具再生消解」·观察），属**登记范围宽于验收范围**的既定遗留，非漏做。夹具自包含（自带定义+调用），不构成对被删 helper 的悬空引用，主树删除不受影响。
- **建议**：无需本票动作；维持 FIX-371 F-8 观察处置，随夹具再生消解。

## 5. Developer 申报核验对照表

| # | 申报 | 核验结果 |
|---|------|---------|
| 1 | 活体等价探针：130 行全等 + completed 84/84 + diff=0 | ✅ 独立复现逐项命中（130/84/84/0；探针 RTL 重放与真函数全等；early-pickup=0） |
| 2 | pytest 3 failed/926 passed 前后全等（FAILED 集=loop-runtime-claims/FIX-300 identity 环境基线） | ⚠️ 部分——**「前后全等」成立**：全量套件 28 failed/3837 passed/2 skipped（1007s），28 失败节点于 HEAD 全树重放**同集全败**（110.72s）→ diff 致因翻转=0；但「3 failed/926 passed」绝对数字今日不可复现（当前树全量即 28 failed，其中 test_verify_workflow.py 内 20 失败含 FIX-339 家族 16 连败——HEAD 同败，属活树契约/时间敏感基线漂移，非本票致因），申报口径疑为更早时点或更窄范围，**精度问题记 P3 级备注，不影响等价性结论** |
| 3 | 主运行 exit 0 + 输出 1179 行逐行全等 | ✅（实现层 delta 口径）当前树 exit 0 + 1179 行实测命中；+1 条 static-pin WARN 为测试文件 delta 所致（F-A），实现 delta 下两轮输出同含 |
| 4 | cross-refs/manifest PASS | ✅ 主运行输出含对应 PASS 面（exit 0）；manifest 项实测通过（967 entries 全 OK） |
| 5 | TDD 披露：F-6 预实现即绿、无可观测红相 | ✅ 双树实测坐实（HEAD 代码 2 passed）+ 判别力分析（§1.3）；「覆盖缺口而非行为缺陷」定性正确 |

## 6. 未验证项（如实披露）

1. **28 个基线失败的根因未深挖**（archguard R1/R7/CliGate、static-pin 实树契约 ×2、quickscan、loop-runtime ×3、FIX-339/HotFact ×20、ExternalHarness ×1）——已证明 HEAD 同集失败（非本票致因），但未逐个溯源；建议 Coordinator 另立健康票（其中 static-pin 实树契约与 stale-12375 豁免行属低垂果实）。审查者探针中 3 个失败类测试的报错样例（如 `AssertionError: [] == []` @ HEAD test:10798）提示 FIX-339 家族可能存在时间敏感夹具（钉 2026-05 日期 vs 当前日期），仅作线索不作结论。
2. Developer 的「3 failed/926 passed」原始运行时点/命令未获快照，无法精确重建（§5 #2 已以双树重放替代验证等价性）。
3. 「fix376_probe」目录在 %TEMP%（会话外不留存承诺由 OS 清理策略承担），报告中数值均可按 §0 方法一节复跑。

## 7. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|--------|------|------|------|
| P0 阻塞数 | =0 | 0 | ✅ |
| 5 维度全覆盖 | 100% | 5/5（§2） | ✅ |
| 每条发现标注级别 | 100% | F-B(P2)/F-A(P3)/F-C(P3)/F-D(P3) | ✅ |
| 设计一致性 | 已完成 | 与 DEC-227 路线 b / FIX-292 谓词分层 / DEC-213③ 豁免账本惯例比对（§1.1/1.5/F-A） | ✅ |
| AI 专项 5 项 | 全部完成 | 5/5（§3） | ✅ |
| 只读约束 | 未修改产品代码/.governance | git status 复核仅原 2 文件改动；临时产物全在 %TEMP% | ✅ |

**最终结论：APPROVED_WITH_NOTES · unresolved_blockers=0 · P0=0 / P1=0 / P2=1 / P3=3**——可合并；F-B 建议随 DEC-232 或后续票补钉，F-A/F-C 材料已备妥供决策票入账时采纳。

---

*审查者：Code Reviewer Agent（FIX-376 派发）· 证据存档 %TEMP%\fix376_probe\ · 报告路径 docs/reviews/review-FIX-376-CODE-R0.md*
