# FEAT-050 独立代码审查报告 — R0（round 0）

> **审查对象**：批 2.3 check-injection-budget resident gate advisory→hard 翻转 + FEAT-039 P3-3 同 commit（DEC-211③）
> **Reviewer**：Code Reviewer Agent（独立审查——未参与实现；只读 + 本报告）
> **日期**：2026-09-19 · **基线**：工作树未提交 diff（HEAD 后 4 文件；contracts 族〔contracts.py / test_contracts.py / manifest.json / fixtures/m0〕属 FEAT-049 在途，**出范围未审**——manifest.json +5 行经核对为 `benchmarks/closure/` 注册，归属 FEAT-049/REL-082 面，非本任务漏报）

---

## 总结论

## **APPROVED_WITH_NOTES** — unresolved_blockers=0

| 硬门槛 | 结果 |
|---|---|
| P0 阻塞问题数 = 0 | ✅（0 条） |
| 5 维度全覆盖 = 100% | ✅（§八） |
| 每条发现标注级别 = 100% | ✅（P0=0 / P1=0 / P2=2 / P3=2） |
| 设计一致性检查（vs DEC-211③ / DEC-210 翻 hard 时点承诺） | ✅（§一） |
| AI 代码专项 5 项检查 | ✅（§七） |

计数：**findings 4 条 = P0×0 + P1×0 + P2×2 + P3×2；unresolved_blockers = 0**。两条 P2 均不阻塞合并（流程机录缺口 + 测试命名/证明力漂移），建议随 R1 写回或 Coordinator 快速通道处置。

---

## 一、gate 翻转正确性核验（审查重点①）— 通过

| 核验点 | 事实依据 | 裁定 |
|---|---|---|
| 一行核心翻转 | `checks/injection_budget.py:575-578`（diff）：`BUDGET_TIER_POLICY["resident"]["gate"]` `"advisory"` → `"hard"`，仅此一处数据变更 | ✅ |
| 三值 verdict 机制未破坏 | `injection_budget.py:613-614`：`verdict = "FAIL" if issues else ("ADVISORY" if gated_over_budget_tiers else "PASS")` ——未改动；hard 超限 → `issues`（:595-596）→ FAIL 链路完整 | ✅ |
| unknown→hard fail-closed 默认保留 | `injection_budget.py:502-504`：`BUDGET_TIER_POLICY.get(tier, {}).get("gate", "hard")`——未改动 | ✅ |
| gated 口径一致 | `:584-587`：`gated_over_budget_tiers` = gate ≠ "report-only"（advisory/hard 均动裁决）——P2-1（review-FEAT-039）语义保持 | ✅ |
| fail-closed 兜底面未回归 | 未声明 tier 显式 issue（:574-578）；`resident` 缺行显式 issue（:607-611）——均未改动 | ✅ |
| ADVISORY 保留臂 | `cmd_check_injection_budget` ADVISORY 分支（:762-780）新增不可达性注释（"Unreachable while every non-report-only tier is hard…kept as the data-driven arm"）——删除该分支反而引入 fail-open 文本风险，保留正确 | ✅ |
| 与 DEC-210 时点承诺一致 | DEC-210（翻 hard 时点 = 0.85.0 瘦身后）；DEC-211③（"P3-3——0.85.0 翻 hard 时补"）；EVD-1104（"本行即批 2.2 完成……2.3 翻 hard 的直接依据"）——本 commit 在承诺时点、以承诺基线执行 | ✅ |

**设计一致性**：实现 = 数据单点翻转 + 措辞随动，未扩散 gate 逻辑；与 DEC-211③ 同 commit 纪律（翻 hard + P3-3）相符。

## 二、新测试套件质量（审查重点②，9 测试）— 通过

`tests/test_injection_budget_gate.py`（新建 196 行）逐个核验：

| # | 测试 | 证明力核验 |
|---|---|---|
| 1 | `test_resident_tier_gate_is_hard` | 数据面 + 函数面双钉（`BUDGET_TIER_POLICY` 与 `injection_budget_tier_gate("resident")`）——静默回退 advisory 即红。负向守护之一 ✅ |
| 2 | `test_advisory_gone_from_the_policy_table` | advisory 姿态全表退役钉——未来新增 advisory 行须**同 commit 更新本测试**（docstring 明示）。负向守护之二 ✅（与 #1 构成任务所述"负向守护双钉"） |
| 3 | `test_unknown_tier_gate_defaults_hard_p3_3` | 见 §三 |
| 4 | `test_skill_and_command_stay_report_only` | ⑧ 票边界数据钉 + 函数钉（§六） |
| 5 | `test_skill_and_command_overrun_never_becomes_an_issue` | 行为面：全 tier 压到 budget=1 时 issues 只含 resident headline（`'resident' tier over budget`），不含 `entry-skill`/`command-doc`——report-only 超限留在 verdict 路径外 ✅ |
| 6 | `test_over_budget_resident_moves_verdict_to_fail` | **派生阈值模式**：先取默认预算下 resident 实测 tokens，再以 `resident_tokens - 1` 触发超限——**不真写任何 canonical 模板**（diff 确认零模板写入）；断言 over/gated/`hard gate` issue/FAIL 四点 ✅ |
| 7 | `test_verdict_motion_is_caused_by_the_gate_posture_alone` | **反事实因果证明**：同一超限条件（同 resident_tokens-1）下仅把 gate 姿态改回 advisory → `issues == []` 且 verdict=ADVISORY；finally 恢复 + 恢复后断言（:144-154）。单一变量对照，证明 FAIL 由姿态翻转引起而非度量变化——动态红相真实存在（独立复验单跑 OK）✅ |
| 8 | `test_cli_prints_failed_and_exits_1_for_over_budget_resident` | CLI 面：`Result: FAILED` + `hard gate` 文本 + `--fail-on-issues` → `SystemExit(1)`（CI 可接线形态；advisory 时代 stay exit-0 的行为已翻转并被钉住）✅ |
| 9 | `test_all_three_profiles_pass_at_default_budget` | 三 profile 零破坏回归 + strict 34 tok 余量置于硬门后的定性守护 ✅ |

隔离性：#7 与既有 `test_missing_resident_tier_policy_fails_closed_not_crashes`（pop/finally 恢复先例，test_verify_workflow.py:20369-20393）同模式——try/finally 保证模块级 dict 恢复，无跨测试污染路径。套件实测 9/9 OK（0.123s）。

## 三、P3-3 断言充分性（审查重点③）— 通过（超出 R0 建议面）

- **R0 建议原文**（review-FEAT-039-CODE-R0.md:184）：「补一条 `injection_budget_tier_gate("unknown") == "hard"` 断言，把"未知档=fail-closed"从注释变为可验证事实」。
- **R1 记录**（review-FEAT-039-CODE-R1.md:86,139-147）：未修复、无决策/风险/plan-tracker 落点（F-3）。
- **本 commit 实现**（test_injection_budget_gate.py:75-84）：三态断言 `unknown` / `""` / `not-a-tier` 全部 → `"hard"`，docstring 明示 R0/R1/DEC-211③ 溯源。
- **裁定**：覆盖 R0 建议且增强（单态 → 三态，含空串边界）；DEC-211③"0.85.0 翻 hard 时补"承诺兑现；P3-3 关闭。✅

## 四、锁外随动两处裁决材料核验（审查重点④）— 随动本身通过，机录面有缺口（P2-1）

### 4a. test_verify_workflow.py — 4 方法改钉：语义必然 ✅ 且最小面 ✅

| 方法（行号） | 改动 | 不改必红证明 |
|---|---|---|
| `test_report_separates_gated_from_report_only_over_budget`（:20334-20367） | verdict 断言 ADVISORY→FAIL；CLI 断言改 `Result: FAILED`+`hard gate` | gate 已 hard → 超限进 issues → verdict 恒 FAIL；ADVISORY 断言必红 ✅ |
| `test_standard_and_strict_profiles_within_budget_after_feat041`（:20395-20410） | policy 钉 `advisory`→`hard` + docstring 刷新 | 字面断言必红 ✅ |
| `test_dynamic_tiers_are_measured_but_never_added_to_resident`（:20427-20446） | tiers 钉 `resident` gate `advisory`→`hard` | 同上 ✅ |
| `test_cli_reports_per_surface_budget_and_exit_codes`（:20531-20570 附近） | ADVISORY 隐式 exit-0 → `assertRaises(SystemExit)` + exit 1 + FAILED 文本 | `--fail-on-issues` 下 FAIL 现抛 SystemExit，不改必 error ✅ |

diff hunk 全部限于上述断言/docstring/注释行（49 行变化），无夹带改动——最小面成立。**Developer 边缘①（不改则 verify 硬门槛不可达）成立**：四处均因翻转而必然红，属语义必然随动。

### 4b. TOOLS.md — TOOL-055 两处：如实同步 ✅ 非扩面 ✅

- **表行**（:60）与**工具详情"预算与裁决"段**（:590）两个 hunk 各 1 行替换，全部限于 TOOL-055 语义——无其他工具行变动。
- 原文与新实现确实相反：原文「切片 A 放宽档……超限按 `BUDGET_TIER_POLICY` 报 ADVISORY」「resident = advisory（……本档只报告不阻断）」——不同步则文档宣称 advisory 而实现为 hard。
- 新文与实现逐点一致：hard + issue+FAIL、EVD-1104 数字、"ADVISORY 分支为数据驱动保留臂"（与代码 :763-766 注释一致）、"⑧ 票独立预算面不并入"（与 triage reason 一致）、fail-closed 三处表述未回归。
- 先例符合：与 FEAT-362（manifest 同步）/FIX-357（路径勘误披露）同为"文档随实现如实同步并披露依据"模式。

### 4c. 缺口：triage 机录 `files` 面未随动（P2-1）

- 事实：`.governance/change-triage/FEAT-050.json:11-14` `files` = 仅 `[injection_budget.py, test_injection_budget_gate.py]`；实际 diff 面 4 文件——`test_verify_workflow.py` 与 `TOOLS.md` 未入账；`reason` 段仅提"FEAT-041 已随动改钉"一个测试名，未申报本轮 4 方法改钉与 TOOLS.md 两处。
- 影响：`files` 是 `check_conflicts` 冲突检测输入（review-FEAT-039-CODE-R1 §F-3 同一定位）；`test_verify_workflow.py` 是 20,838 行共享热点测试文件，漏面 = 并行任务冲突检测漏报。**与 R1 F-3 同族模式复发**（当时 DEC-211③ 已把 triage files 面列为教训）。
- 建议：Coordinator 快速通道直改 `FEAT-050.json` `files` 面补 2 文件（R1 §F-3 同款处置），随 R1 机录一并落账。**非阻断**（P2）。

## 五、7 处措辞翻转 EVD-1104 引用准确性（审查重点⑤）— 逐位核对通过

7 处翻转逐一定位（与 Developer 申报数一致）：

1. 模块 docstring §4（:41-51）——"EVD-1104 baseline: lightweight 4,216 / standard 5,694 / strict 5,966" ✅ 与 EVD-1104 原文（evidence-log.md:2370）**逐位一致**；
2. `INJECTION_BUDGET_TOKENS` 常量注释（:70-71）——定性引用 ✅；
3. `BUDGET_TIER_POLICY` 表注释（:166-172）——定性引用 ✅；
4. advisory note 措辞（:597-599）——"advisory-gated (reported, not blocking)"，去 slice-A 窗口语 ✅（该分支当前不可达，措辞中性正确）；
5. `--budget-tokens` help（:705-709）✅；
6. 默认预算打印（:742-744）✅；
7. ADVISORY 打印分支（:767-773）——移除 "in the slice-A relaxed window" ✅。

衍生数字核验：strict 余量 = 6,000 − 5,966 = 34 tok（EVD-1104 "34 tok（0.57%）"一致，新测试 docstring 引用正确）。`injection_budget.py` 全文 grep `slice-A 放宽|slice-A relaxed|放宽档` **零残留**；余下命中均为合法历史叙述（新测试 docstring 的窗口由来、TOOLS.md "自切片 A 放宽档翻转"的翻转史描述）。✅

## 六、skill/command 层 report-only 边界守护（审查重点⑥，⑧ 票不并入）— 通过

- 代码面：`BUDGET_TIER_POLICY["skill"|"command"]["gate"]` = `"report-only"` 未动（injection_budget.py:580-587）；gated 口径排除 report-only（:584-587）。
- 测试面：新套件 #4（数据+函数双钉）、#5（行为面 issues 隔离）+ 既有 `test_dynamic_tiers_are_measured_but_never_added_to_resident`（:20441-20446）三重守护。
- 文档面：TOOLS.md "⑧ 票独立预算面不并入" + 模块 docstring "The skill/command tiers stay report-only…NOT folded into the resident gate"。
- 溯源一致：DEC-215⑧ / plan-tracker 0.85.0 行（批 2.4 entry-skill 独立预算）/ FEAT-050 triage reason（"skill 层 entry-skill 9,387 维持 report-only"）——三处口径一致。✅

## 七、AI 代码专项 5 项检查（审查重点⑧）— 全部完成

| # | 检查 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock 残留 | 无 | 新测试文件 grep `mock|Mock|patch` 零命中；`SimpleNamespace` 为 stdlib 参数替身非 mock 残留 |
| 2 | 硬编码返回值 | 无 | 测试断言全部走真实计算路径（真实树测量/真实 CLI 渲染），无固定值伪造被测行为 |
| 3 | 幻觉 API 调用 | 无 | 新测试引用的全部 API（`check_injection_budget`/`injection_budget_tier_gate`/`BUDGET_TIER_POLICY`/`cmd_check_injection_budget`/`INJECTION_BUDGET_*`）逐一在 injection_budget.py 源码确认存在 |
| 4 | 未实现 TODO | 无 | grep `TODO|FIXME|XXX|NotImplemented` 零命中（diff 面内） |
| 5 | 过度实现 | 无 | 产品代码 diff = 1 行数据 + 7 处措辞 + 注释；ADVISORY 保留臂为防 fail-open 的数据驱动设计（带不可达注释），非死码堆砌 |

## 八、5 维度逐项结论

| 维度 | 结论 | 关键依据 |
|---|---|---|
| 正确性 | ✅ | §一：翻转链路/三值 verdict/fail-closed 兜底逐点核验；9+31 测试全绿 |
| 安全性 | ✅ | 只读检查命令；无注入面/敏感数据；解析失败/未知 tier/缺 resident 行三处 fail-closed 保留 |
| 可维护性 | ⚠ 2 条非阻塞 | docstring 大面更新到位；P2-2 方法名漂移 + P3-1 docstring 陈旧（见 findings） |
| 性能 | ✅ | token 估算为线性文本扫描；新套件 0.123s、Feat039 回归 0.277s；无 N+1/O(n²) 引入 |
| 测试覆盖 | ✅ | 硬门四后果（FAIL 动位/CLI exit/零破坏回归/负向防回退）+ 反事实因果对照 + P3-3 三态，全有测试 |

---

## Findings 清单

| ID | 级别 | 位置 | 描述 | 修复建议 |
|---|---|---|---|---|
| F-1 | **P2** | `.governance/change-triage/FEAT-050.json:11-14` | triage `files` 面漏申报 `test_verify_workflow.py`、`TOOLS.md` 两个锁外随动文件（实际 diff 4 文件，机录 2 文件）——`check_conflicts` 冲突检测输入面不全，review-FEAT-039 R1 F-3 同族复发 | Coordinator 快速通道直改 `files` 面补 2 文件，随 R1 机录落账 |
| F-2 | **P2** | `tests/test_verify_workflow.py:20412-20425` | `test_budget_tier_is_not_a_hard_fail_while_advisory` 翻转后**方法名字面失真**（"while advisory"姿态已不存在）且 `policy["gate"] = "hard"` 赋值退化为 no-op（original 已是 hard）——测试仍绿、断言语义仍真（hard 下超限确 FAIL），但证明力退化为与 :20342（固定 5000）及新套件 #6/#7 重复，失去原"翻转动位对照"意义。**该方法不在 Developer 4 方法改钉面内，属随动边缘遗漏** | 随翻转改名为姿态对照语义（如 `test_hard_gate_makes_over_budget_resident_fail`），或改写为 advisory→hard 双姿态对照（后者的 advisory 臂已由新套件 #7 承载，可考虑收敛） |
| F-3 | **P3** | `tests/test_verify_workflow.py:20312-20321` | `test_live_resident_baseline_is_within_budget` docstring 陈旧（未随动）：仍称 6K 为 "slice-A relaxed budget"；NOTE 称 standard 超限 "reported as an advisory candidate instead (see the next test)"——所指"下一个测试"现断言 FAIL 非 advisory。纯注释漂移，断言语义（lightweight PASS + 派生阈值守卫）仍正确 | 随 F-2 一并刷新 docstring（一句话 hard-gate 口径） |
| F-4 | **P3** | `skills/software-project-governance/SKILL.md:121` | 任务提示的"既有 cross-ref dangling"在 HEAD 定性抽查中**未复现**：SKILL.md:121（归档感知段）引用的 `.governance/archive/index.md` 与 `evidence-log.md` 均存在；全文件 45 个文件引用（39 skill/plugin 根相对 + 6 工作区相对）在正确解析基下全部存在。可能为行号口径差异或旧版本残留 | 建议 Coordinator 核对线索来源行号；若另有其处请指认，本轮以实测证据关闭该抽查票 |

**无 P0 / 无 P1。**

---

## 独立复验表（Reviewer 实跑）

| # | 复验项 | 命令/方法 | 实测结果 | 对照 |
|---|---|---|---|---|
| 1 | 三 profile 预算复跑 | `verify_workflow.py check-injection-budget --profile {lightweight,standard,strict}` | **4,216 / 5,694 / 5,966 tok，全 PASSED** | 与 EVD-1104 逐位一致；Developer 申报一致；翻 hard 零破坏 ✅ |
| 2 | 新测试套件 | `python -m unittest tests.test_injection_budget_gate -v`（infra cwd） | **9/9 OK**（0.123s） | 与申报 9/9 一致 ✅ |
| 3 | advisory 反事实抽查 | 单跑 `test_verdict_motion_is_caused_by_the_gate_posture_alone` | **OK**（动态红相可复现：advisory 姿态下同条件 → ADVISORY 零 issues） | 与申报"反事实动态红相"一致 ✅ |
| 4 | Feat039 回归 | `python -m unittest tests.test_verify_workflow.Feat039InjectionBudgetTests -v` | **31/31 OK**（0.277s） | 与申报 31/31 一致 ✅ |

未独立复现项（如实披露）：Developer 申报的 "verify 全量 PASSED" 未在本轮复跑（全量 verify 含回放族等大面，属 M-2 门禁域；本审查以四项目标复验 + 静态逐行覆盖代替）。

---

## 遗留建议（均非阻断）

1. F-1 / F-2 / F-3 建议随 R1 写回一并处置（F-1 由 Coordinator 快速通道即可，不动代码）；
2. `injection_budget.py:5` docstring 提 "review-FEAT-039 P3-8, accepted by DEC-210" 与 `:607` "AUDIT-154 §8" 等溯源引用本轮抽查可解析（DEC-210 于 decision-log.md:151 在案）；
3. strict 34 tok 余量已受硬门守护（EVD-1104 裁决③的预期形态），无需额外动作。

— Code Reviewer Agent，FEAT-050 R0，2026-09-19
