# Review — FEAT-052 独立代码审查（Code R0）

- **任务**: FEAT-052 — 批 2.4 ⑧ skill 独立预算（16,000 tok / report-only 数据字段化）+ F 族顺带清理（review-FEAT-050-CODE-R0 F-2/F-3）
- **轮次**: R0（round 0）
- **审查人**: Code Reviewer Agent（独立审查，未参与实现）
- **日期**: 2026-09-19 23:00
- **结论**: **APPROVED_WITH_NOTES** · unresolved_blockers=**0**（P0=0 / P1=1 / P2=0 / P3=4）
- **审查对象**（工作树未提交，与 triage `FEAT-052.json` files 面**逐文件一致**，4/4）:
  1. `skills/software-project-governance/infra/checks/injection_budget.py`（+76/−49 区段：skill 行 `budget_tokens:16000` + `gate:"report-only"` 数据字段化、per-tier 判定 `tier_budgets` 映射、渲染 `Tier budgets` 行、CLI help 更新、模块 docstring §4 扩写）
  2. `skills/software-project-governance/infra/tests/test_injection_budget_gate.py`（套件头注记 + 新增 `Feat052SkillTierBudgetTests` 2 测试；③ 测试 monkeypatch rebase）
  3. `skills/software-project-governance/infra/tests/test_verify_workflow.py`（F-2 删除+承接注记、F-3 docstring 刷新、separation 测试 monkeypatch rebase）
  4. `skills/software-project-governance/infra/TOOLS.md`（TOOL-055 三处：表行 / 工具详情输入 bullet / 预算与裁决段）
- **范围外**: 批 1 三票文件、未跟踪的 docs/planning 与 baseline_metadata/task_row_update 族文件（属其他任务）——已核对 git status，未混入本票 diff。

## 一、基线语义核对（逐项溯源）

| 基线 | 原文/位置 | 实现一致性 |
| --- | --- | --- |
| DEC-215⑧ | decision-log：⑧ = entry-skill 独立预算（批 2 序列 2.4 承载） | ✅ skill 行立 `budget_tokens: 16000`，姿态保持 report-only |
| DEC-210② | slice-A relaxed window 关闭、resident 翻 hard（DEC-211③） | ✅ resident 行未动（hard/无 budget_tokens 字段），零姿态漂移 |
| EVD-1106 | 批 2.3 态：skill 无独立值 6000 沿用（report-only 不并入） | ✅ 本票即把「沿用 6000」字段化为「自有 16,000」，兼容面见 §六-F4 |
| review-FEAT-050-CODE-R0 F-2 | :138 — 方法名字面失真 + `policy["gate"]="hard"` no-op；建议改名或双姿态对照，「advisory 臂已由新套件 #7 承载，可考虑收敛」 | ✅ 采纳收敛分支（删除+承接注记），断言面真子集论证成立（§五） |
| review-FEAT-050-CODE-R0 F-3 | :139 — docstring 陈旧（slice-A 措辞 + 指向已不存在的 advisory 断言） | ✅ 刷新为 hard-gate 口径，see-also 指向真实存在的 separation 测试 |
| 实测基线 14,456 | FEAT-050 边缘⑤ | ✅ 独立复测 14,456 逐位一致；16,000 = +10.7% 余量（数值披露见 F3） |

## 二、独立复验（Reviewer 实跑，5 项）

| # | 复验项 | 命令/方式 | 结果 |
| --- | --- | --- | --- |
| 1 | verify 全量 | `verify_workflow.py verify` | **PASSED**（与 Developer 申报一致） |
| 2 | manifest 一致性 | `verify_workflow.py check-manifest-consistency` | **PASS**（canonical 805 / actual 903——申报「manifest 903 PASS」属实） |
| 3 | 三 profile 零回归 | 直调 `check_injection_budget` 三 profile | resident **4,216 / 5,694 / 5,966** ≤ 6,000 hard，skill **14,456**/16,000 report-only 在线内，command **3,466**/6,000（沿用 resident 线），三 profile verdict=PASS、issues=0——与 EVD-1104 基线逐位一致 |
| 4 | 新套件计数 | `python tests/test_injection_budget_gate.py -v` | **11/11 OK**（9 存量 + 2 新增，申报一致） |
| 5 | Feat039 计数 | `python tests/test_verify_workflow.py Feat039InjectionBudgetTests` | **30/30 OK**（31→30，F-2 删除如实申报） |

另实测复现 P1-F1 缺陷（见 §五）与 Check 33 接线核实：`emit_injection_budget_section`（verify_workflow.py:6902→16352）委托 `injection_budget.emit_check_section` → `format_budget_report`——**聚合与 CLI 确为同一渲染函数**，`Tier budgets` 行不可能在两面分叉。

## 三、五维度逐项结论

| 维度 | 结论 | 依据 |
| --- | --- | --- |
| 正确性 | ✅ 判定路径正确；⚠️ 报告 note 文本一处边界缺陷（P1-F1） | `tier_budgets` 映射（:548）对有 `budget_tokens` 的 tier 用自身线、无字段 tier 沿用 resident 线；per-surface 未声明 tier 回退 resident 线且后续触发显式 fail-closed issue（:604-608）；tier 聚合 `tier_budgets[name]` 不可能 KeyError；`over_budget_tiers`/`gated_over_budget_tiers`/issues/verdict 四通道全部按各自线计算（:571-644）。**缺陷**：:622-624 note headline 使用全局 `budget` 而非 tier 自身线（F1） |
| 安全性 | ✅ 无风险面 | 纯读测量 + 渲染；无 I/O 写、无网络、无 eval、无密钥；策略表突变仅存在于测试内且 try/finally 恢复。OWASP 关键项不适用 |
| 可维护性 | ✅ 良好 | 注释/docstring 与实现逐句对应；决策（report-only 连字符、command 无独立线理由、0.86.0 翻硬去 FEAT-047 BaselineMetadata）就地文档化；TOOLS.md 三处与代码一致（一处枚举缺口见 P3-F5） |
| 性能 | ✅ 无影响 | 每次调用构建 `tier_budgets` dict（O(tiers)=3），无循环内 I/O 变化 |
| 测试覆盖 | ✅ 新面四向钉住；⚠️ note 文本边界面未覆盖（即 F1 所在） | 新增 #10 钉数值+姿态+per-tier 判定+纯 PASS；#11 钉派生阈值（线降 1 tok）超线→零 issue 零 verdict 移动+恢复断言；rebase 后 #5/separation 保持原意图且更强（含 CLI 面）。**缺口**：自身线超限时的 `note` 文本无数值断言——F1 因此漏网 |

## 四、审查重点逐项裁决（对应任务书 ①~⑦）

1. **per-tier 判定正确性** — ✅ 成立（详见 §三正确性行）。CLI `--budget-tokens` 交互与 help 声明一致：有自身线的 tier（skill）**忽略**该 flag、按 16,000 判定，help 原文 "verdict against that line instead"（:747-749）与代码行为逐字吻合；该 flag 只影响 resident 与无字段 tier（command）。Check 33 聚合与 CLI 同渲染已核实（§二）。
2. **16,000 数值依据** — ✅ 合理。16,000 = 14,456 实测 + 10.68% 余量（≈+10.7%）；report-only 语义下该线是可见性阈值而非硬门，超额后果是显式 note 而非 FAIL，余量偏薄不构成风险敞口；数值与基线在代码注释、TOOLS.md、测试 docstring 三处如实披露。余量比例本身未显式落文档 → P3-F3。
3. **F-2 删除处置** — ✅ 证明力无损，论证成立。被删测试断言面 = {standard/5000 下 issues 非空, verdict=FAIL}；承接面：separation 测试同 profile/同 budget 断言 resident∈gated + verdict=FAIL + CLI `FAILED`+`hard gate`（**严格更多**——新增 CLI 面）；gate 套件 #6（issues+`hard gate`+FAIL，lightweight 派生阈值）与 #7（advisory 反事实：同条件零 issue+ADVISORY——恰为 F-2 原文点名的承载者）；姿态面 #1/#2。被删断言 ⊂ 存量断言并集，「No assertion surface was lost」注记属实。删除本身即 F-2 原文建议的「可考虑收敛」分支（no-op 赋值 + 字面失真名）。31→30 计数如实。
4. **:20334 区 monkeypatch rebase** — ✅ 正确。旧法依赖 skill 沿用 resident 线（FEAT-052 后失效），新法 try/finally 内临时降低 skill 线至 1000（separation 测试）/派生阈值 `skill_tokens - 1`（gate #11，对基线漂移稳健）；恢复值直接索引（KeyError 快速失败）；断言面保持 P2-1 分离渲染意图并增强。一处模式不一致 → P3-F2。
5. **report-only 连字符保持** — ✅ 正确决定。`"report-only"` 是既有 gate 姿态词表（`injection_budget_tier_gate` 比较 + 既有测试 `test_skill_and_command_stay_report_only` 钉死），改下划线将破坏已钉契约与 JSON 输出且零收益；任务文本的下划线写法系行文差异，非实现缺陷。
6. **向后兼容** — ✅ 独立排查通过，声明缺口 → P3-F4。`tiers.skill.budget_tokens` JSON 语义 6000（沿用）→16,000（自有）为特性本体；全 infra grep：该字段的读取方仅 injection_budget 自身（渲染/策略）、测试（schema 键/值断言）、Check 33 顶层 `budget_tokens`（resident 头条，语义未变）——**仓内零消费者钉住旧沿用值**。语义变更已在 TOOLS.md TOOL-055 三处 + 模块 docstring §4 披露。
7. **AI 专项 5 项** — 全部通过：① mock 残留：无（策略突变均为有意 monkeypatch + finally 恢复）；② 硬编码返回值：无不当——16,000/14,456/3,466 属策略数据与文档计量，本就应字面化；③ 幻觉 API：无——所引符号（`BUDGET_TIER_POLICY` 再导出、`emit_check_section`）均实测存在（测试全绿佐证）；④ 未实现 TODO：无——"0.86.0+ candidate via FEAT-047 BaselineMetadata" 为与 DEC-215⑧ 一致的前瞻声明，非悬挂 TODO；⑤ 过度实现：无——`tier_budgets` 每调用构建、渲染单行、无多余抽象。

## 五、Findings

| ID | 级别 | 位置 | 描述 | 建议 |
| --- | --- | --- | --- | --- |
| F1 | **P1** | `injection_budget.py:622-624` | **超限 note headline 使用全局 `budget`（resident 线）而非 tier 自身 `budget_tokens`**。实测复现：skill 线降 14,000、tokens=14,456 时 note = `"'skill' tier over budget: 14456 > 6000 tokens by 8456 …"`——实际线 14,000、超 456，行号与差值双双失真。影响面恰为本特性新增的「自身线 tier」（resident 无字段故正确）；report-only 唯一的人读信号即该 note，触发时数字自相矛盾（同报告 `Tier budgets` 行显示 16000/report-only）。**无判定影响**（note 不入 issues、不动 verdict；当前活树 14,456<16,000 不触发）。风险前瞻：0.86.0 若按声明经 BaselineMetadata 把 skill 翻 hard，该错误文案将进入 `issues` 阻断路径文本 | headline 改用 `tier['budget_tokens']`（一行 f-string 修改）；补一条 note 文本数值断言（可并入 #11）；建议随本批顺手修或立紧随修复票，**MUST 在 0.86.0 翻硬前关闭** |
| F2 | P3 | `test_injection_budget_gate.py:123` | 恢复值用 `skill_policy.get("budget_tokens")`：若字段缺失，finally 会以 `None` **创建**该键，使 `policy.get("budget_tokens", budget)` 返回 `None` → `tokens > None` TypeError。树内无害（字段存在），但与 #11 及 test_verify_workflow.py:20349 的直接索引（KeyError 快速失败）模式不一致 | 统一为直接索引 `skill_policy["budget_tokens"]` |
| F3 | P3 | `injection_budget.py:195` / TOOLS.md | 16,000 的余量依据（+10.7%）可推导但未显式落文档——文档只披露「16,000/实测 14,456」两个数，未写选择理由；且该余量相对单次 LLM 编辑的 SKILL.md 增量偏薄（report-only 下后果仅是可见 note，可接受） | 在 FEAT-047 BaselineMetadata 承载翻硬时，把余量比例与选择理由一并入基线元数据 |
| F4 | P3 | 交付文档面 | 「外部消费者排查」无显式声明留存（TOOLS.md 披露了新语义，但无一句消费者排查结论）。Reviewer 已独立完成排查：仓内零消费者依赖旧沿用值 6000（§四.6） | 证据写回时把本报告 §四.6 的排查结论记入 evidence-log，补齐声明面 |
| F5 | P3 | `TOOLS.md` 工具详情「输出」bullet | 输出枚举未列入新增的 `Tier budgets` 行（同节「预算与裁决」段已提及）——输出契约清单与实际渲染面存在一处枚举缺口 | 「输出」bullet 补 `+ "Tier budgets" 逐层预算线行` |

## 六、硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
| --- | --- | --- | --- |
| P0 阻塞数 | = 0 | 0 | ✅ |
| 5 维度全覆盖 | 100% | 5/5 有结论（§三） | ✅ |
| 每条发现标注级别 | 100% | F1~F5 均有 P 级 | ✅ |
| 设计一致性 | 已完成 | DEC-215⑧/DEC-210②/EVD-1106/F-2/F-3 逐项比对（§一） | ✅ |
| AI 专项 5 项 | 全部完成 | 5/5 有结论（§四.7） | ✅ |

## 七、总结论

**APPROVED_WITH_NOTES** — unresolved_blockers = **0**。

- P0=0；P1=1（F1，非阻塞：无判定影响、活树不触发，但 report-only 报告文本错误 + 翻硬前必须修复）；P2=0；P3=4（F2~F5，均为一致性/披露完善项）。
- 判定语义（issue/verdict/JSON 机读面）全部正确；缺陷仅在 report-only note 渲染文本，属显示层边界缺陷，按 code-review 分级标准不构成 BLOCKING，按「P0=0 且 P1>0（有遗留计划）→ 有条件合并」出具有条件通过。
- **遗留条件**：F1 必须以跟踪项落账（本轮顺手修复或紧随修复票），关闭截止 = 0.86.0 skill 翻硬（FEAT-047 BaselineMetadata 承载）之前；F2~F5 可随批 2 收尾或下一批顺带。
- Developer 申报 5 项（verify 全量 PASSED / 三 profile 4,216/5,694/5,966 零回归 / 新套件 11/11 / Feat039 30/30（31→30 如实）/ manifest 903 PASS）经独立复验**全部属实**，无夸大。

## 八、边缘问题（供 Coordinator 参考，非 finding）

1. gate 套件 #5/separation 测试对模块级 `BUDGET_TIER_POLICY` 做 in-place 突变——unittest 串行执行下安全，但若未来引入并行测试执行器需改为 `patch.dict`。
2. `tier_budgets.get(surface["tier"], budget)`（:556）对未声明 tier 静默回退 resident 线，随后由 :604-608 显式 issue 兜底——回退本身无害，但回退行的 `budget_tokens` 列会短暂显示 resident 线；fail-closed 兜底已覆盖，无需改动。
3. ADVISORY 保留臂（:802-820）引用 `result['budget_tokens']`（resident 线）——当前无 advisory 行不可达；若未来 advisory tier 带自身线，该臂文案需随 F1 一并核查。
