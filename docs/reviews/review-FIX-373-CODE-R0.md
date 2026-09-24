# FIX-373 代码审查报告（CODE · R0）

> **Round**: R0（初审，无前轮引用）
> **Task**: FIX-373 — 共享切分器 `_split_governance_table_row` 状态泄漏修复（code-span 内引号误开 in_string）
> **Reviewer**: Code Reviewer Agent（独立审查席，只读）
> **审查对象**（未提交工作树 diff，Developer 声称 +9/-2 / +109）:
> - `skills/software-project-governance/infra/verify_workflow.py`（L12314 `_split_governance_table_row`）
> - `skills/software-project-governance/infra/tests/test_verify_workflow.py`（L12114 新增 `Fix373SplitterCodeSpanQuoteTests`，置于 `EvidenceFormatColumnLayoutTests` 之后）
> **优先级**: P2（triage 注记：实际严重级 P3 按 P2 录）

---

## 0. 审查方法与证据边界（以读代跑声明）

- 角色铁律：Bash 禁止。本次审查**未重跑任何命令**——git diff 算术（+9/-2、+109）未以 git 复核，以**当前工作树代码态**核实修复在位与形状吻合；Developer 声称的测试运行结果（红态 failures=3 → 绿态 6/6、43/43、47/47、24/24、check-governance --summary-only exit 0、三 PASS）**记为 Developer-claimed，未复跑**，其真实性以代码证据做一致性/自洽性评估（见 §8）。
- 事实依据全部来自：两审查对象文件相关段全文逐行读取、EVD-248 原始行（`.governance/evidence-log.md` L836）读取、消费方调用点上下文读取（13 处）、全仓同源副本 grep（恰 2 处）、`.gitignore` 读取、`checks/risk_domain.py` 引用核实、tests 目录 glob。

## 1. 修复内容核实

**行为变更（唯一 1 行）**：`verify_workflow.py` L12346

```python
if ch == '"' and not in_code_span:   # 修复前: if ch == '":'
    in_string = True
    current.append(ch)
```

**机理 docstring**：L12317-12321，五句话完整描述缺陷级联（code-span 内引号 → in_string 误开 → 反引号分支被 `not in_string` 抑制 → code-span 永不闭合 → 行尾管道全吞），并引用 live 实证（EVD-248 row folded 10 data cells -> 5）。与代码逐条吻合（见 §2 推演与 §1-EVD-248 复核）。

**EVD-248 原行复核**（L836）：描述格内嵌 code span `` `rg -n \"^## |^### |FMT-001|FIX-064|实施路线图|样例跟踪表|审计驱动任务|四层推进模型\" .governance/plan-tracker.md` ``——含 **7 个竖线 + 2 处转义引号**，整行 10 数据格。修复前逐字符推演：第一个 `\"` 的 `"`（L12346 旧形态无守卫）开启 in_string → 其后闭合反引号走 L12331 分支被 `not in_string` 抑制 → in_string 无配对引号钉到行尾（L12362 flush）→ 描述格吞并其后 5 个数据格（关联文件/录入方式/日期/Gate/摘要）→ 10 格折叠为 5 格 → 证据格式检查 L10051 `len(cells) < 9` 命中，报 `only 5 data fields (expected ≥9)`（L10053 文案与测试 docstring L12125 引用一致）。修复后：守卫阻断开启，反引号正常闭合 code-span，10 格完好。**缺陷机理、live 形状、误报文案三者交叉验证一致。**

## 2. 状态机互斥性独立推演（验收标准 4——不依赖 Developer 自述）

状态变量：`in_string` / `in_code_span` / `escape` / `depth`（均为函数局部变量，**逐行调用无跨行泄漏**——L12323-12328 每次调用重置）。

**入口守卫完备性（逐路径枚举）**：

| 迁移 | 代码位置 | 前置条件 | 结论 |
|---|---|---|---|
| 开启 code-span | L12331 | `ch == "\`" and not in_string` | in_string=True 时反引号走 L12336 字符串分支字面追加，**不可能**在字符串内开启 code-span |
| 开启 string | L12346 | `ch == '"' and not in_code_span` | in_code_span=True 时引号落入 else（L12359-12360）字面追加，**不可能**在 code-span 内开启字符串 |
| 字符串内迁移 | L12336-12344 | in_string=True | 仅 escape 翻转/`"` 闭合；不改 in_code_span |
| code-span 内迁移 | L12331（下一反引号）| not in_string | 唯一出口是配对反引号 |

**不变量**：`not (in_string and in_code_span)` 对任意输入逐字符成立——两标志的开启条件互以对方为假，且任一为真期间另一标志的全部迁移路径被遮蔽（反引号分支被 in_string 遮蔽、引号开启分支被 in_code_span 遮蔽）。**互斥性完备，无残留互斥破洞。**

**三类指定残留场景逐一推演**：

1. **code-span 内单引号**（含未配对）：`"` 走 else 字面追加（守卫拦截），不触碰任何状态；code-span 在下一反引号处正常闭合。✔ 已修。测试 `test_single_quote_inside_code_span_does_not_fold_row`（L12168-12179）以未配对单引号最小复现钉住。
2. **code-span 开启后行尾不闭合**（奇数反引号）：in_code_span=True 至 L12362——行尾后续管道被折叠。**属既有的 code-span 语义**（修复前反引号分支即以 `not in_string` 为门，非本 diff 引入），逐行调用不跨行泄漏。行内自愈性：in_code_span=True 期间 in_string 不可能开启，下一反引号必然闭合。无互斥破洞。
3. **depth 计数耦合**：L12349-12355 花括号分支**无 in_code_span 守卫**——code-span 内不配对 `{`/`[` 会把 depth 钉到行尾折叠后续管道。见 F-2（P3，Developer 已登记边缘 2）。注意其对称面：`}`/`]` 有 `if depth > 0` 下限保护（L12353），不会负漂移。

**结论：修复正确且互斥完备；三类残留均为既有语义或已登记观察项，无一由本 diff 引入。**

## 3. 五维度结论（验收标准 1）

| 维度 | 结论 | 依据 |
|---|---|---|
| **正确性** | **PASS**——修复机理成立，互斥不变量完备（§2），EVD-248 形状修复前后推演与测试断言一致；13 个消费方共享行为同步受益，无消费方需要感知变更（切分器契约不变：仍是"按管道切分 + JSON/code-span 管道保护"） | §1、§2、§4 |
| **安全性** | **PASS**——纯文本表格解析器，无输入执行面（无 eval/exec/subprocess），无注入面（输出仅作为 cell 字符串供各 Check 比对）；本 diff 不扩大输入接受面（守卫是收紧而非放宽：code-span 内引号从"开启状态"改为"字面文本"） | L12314-12363 全文 |
| **可维护性** | **PASS**——最小守卫修复 + 机理 docstring（含 live 引用），符合本文件既有注释契约风格（对照 `_is_incomplete_task_status` L12383-12404、FIX-372 注释 L14350-14352）；不新增分支复杂度；docstring 与代码零漂移 | L12317-12321 |
| **性能** | **PASS**——单遍 O(n) 逐字符扫描，无新增循环/数据结构/正则；守卫为常量判断，性能特征与修复前完全一致 | L12330-12362 |
| **测试覆盖** | **PASS**——6 用例 = 2 负例钉（EVD-248 形状 + 未配对单引号）+ 1 集成钉（证据格式检查端到端）+ 3 保留钉（配对引号/JSON 转义/纯 code-span 管道），全部内容级断言（§6）；红绿算术自洽（§8） | L12114-12221 |

## 4. 发现列表（P0=0 / P1=0 / P2=1 / P3=4）

| # | 级别 | 位置 | 发现 | 事实依据 | 修复建议 |
|---|---|---|---|---|---|
| F-1 | **P2** | `project/e2e-test-project/skills/software-project-governance/infra/verify_workflow.py:6879` | e2e 同源切分器副本仍携带同一缺陷（L6879 无守卫 `if ch == '"':`，L6855 旧 docstring）——即 Developer 登记的边缘问题 1，处置合理但**须有承接**，否则副本随源演进持续漂移 | 全仓 grep `def _split_governance_table_row` 恰 2 处（源 L12314 已修 + e2e L6854 未修）；`.gitignore` L31 `project/e2e-test-project/skills/` 证实为 git-ignored runtime fixture（与 Check 27 "ignored e2e fixture 仅 optional consistency" 先例一致，EVD-245） | 不阻塞本 diff。立后续 FIX 任务二选一：(a) 同步副本；(b) 泛化性根治——把切分器抽为共享模块单一事实源，两处引用（P-v1 原则 5"严禁单点修改"的正向落地，本任务已按契约只修共享源） |
| F-2 | P3 | `verify_workflow.py:12349-12355` | code-span 内 `{[}/]` 仍参与 depth 计数（elif 链无 in_code_span 守卫）——含不配对 `{`/`[` 的 code span 会把 depth 钉到行尾，折叠后续管道。Developer 已登记（边缘 2），无已知实数据误报 | L12349-12355 分支顺序：花括号分支先于管道分支执行，不检查 in_code_span；EVD-248 code span 内无花括号 | 观察项保留。若未来出现实证误报，修法 `elif ch in "{[" and not in_code_span`，且须先补"code-span 内花括号"形状保留钉防过度修复 |
| F-3 | P3 | `verify_workflow.py:12346-12348, 12362` | 行外（code-span 外）未配对引号仍钉 in_string 至行尾折叠后续管道——既有 JSON 字符串语义，非本 diff 引入；Developer 已登记（边缘 3）且如实声明正例钉只覆盖配对形状 | L12346 开启后唯一闭合路径是 L12342-12343 的配对 `"`；测试 L12188-12198/L12200-12209 只钉配对形状 | 处置合理。可选：补一条 retention pin 显式冻结"未配对引号折叠"为既定语义，防未来被误判为回归 |
| F-4 | P3 | `test_verify_workflow.py:12134` | 测试 fixture 与 EVD-248 原行非逐字节等价：pattern 管道 5 个（原行 7 个——省略了「审计驱动任务」与「四层推进模型」间由竖线分隔的子串），描述尾部精简。**形状等价**（双 code-span + 转义引号 + 多管道 + 10 格），不影响缺陷机理覆盖强度 | 对照 `.governance/evidence-log.md` L836 原行逐段比对 | 无需修改。不建议改为直接读 live 治理文件作 fixture——单测将依赖治理热数据，得不偿失 |
| F-5 | P3 | `test_verify_workflow.py:12114-12221` | 互斥对的另一半（in_string 抑制反引号分支，L12331）无直接保留钉——现被 L12188-12209 两正例间接覆盖（字符串内管道折叠隐含反引号字面化），且该路径非本 diff 变更面 | L12331 分支 + 测试类用例清单 | 可选：补钉"字符串内反引号不开启 code-span"显式用例 |

## 5. AI 代码专项 5 项（验收标准 3）

| # | 检查项 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock 残留 | **无** | 测试仅用 `patch.object(vw, "SAMPLE_PATH"/"GOVERNANCE_DIR")` 做路径隔离（L12152-12153），与既有 `EvidenceFormatColumnLayoutTests` L12078-12079 同构的合法测试隔离手法；无对被测行为的 mock/monkeypatch 替身 |
| 2 | 硬编码返回值 | **无** | 断言全部针对真实 `vw._governance_table_cells`（L12373 存在）与 `vw.check_protocol_compliance()["evidence_format"]`（L10052 真实产出键）的实际输出；无预设返回值 |
| 3 | 幻觉 API | **无** | 引用面仅 `unittest/tempfile/patch/vw` 已核实存在的符号；`issues["evidence_format"]`、`SAMPLE_PATH`、`GOVERNANCE_DIR` 均在源文件实位 |
| 4 | 未实现 TODO | **无** | diff 区域无 TODO/FIXME/占位实现；docstring 中的 FIX-373 标注是机理说明而非未完成标记 |
| 5 | 过度实现 | **无** | 行为变更恰 1 行守卫 + 5 行 docstring；无投机抽象、无超范围重构、无未消费的新接口；符合 D4 修改纯粹性 |

## 6. 回归测试质量评估（验收标准 5）

1. **fixture 是否真实复现 EVD-248 形状**：是（形状级）。`_evd248_shape_row`（L12130-12143）复现三要素：双 code-span（`rg -n \"...\"` + `Get-Item ...`）、code-span 内转义引号 `\"` 与多管道、10 数据格整行。与原行差异仅 pattern 管道数（5 vs 7）与描述尾部精简（F-4，P3）。转义引号的字面形状 `\"` 与原行 L836 一致，断言 L12163 以同字面量校验存活。
2. **3 个保留钉是否足以钉住零回归面**：**足以覆盖本 diff 的行为变更面**。行为变更唯一作用点是"code-span 内引号不再开启 in_string"——其反事实面为：(a) code-span 外引号照常开启/闭合（L12188 钉）；(b) 字符串内转义语义不变（L12200 钉）；(c) code-span 管道保护与引号无关、不受影响（L12211 钉）。三条恰为守卫可能误伤的全部邻近路径。未覆盖的未配对引号/字符串内反引号为既有语义（F-3/F-5，可选补钉）。
3. **断言强度**：**内容级，非仅格数**。6 用例全部同时断言格数与内容锚点（cells[0]/[1]/[3] 片段与 endswith/cells[5]/[9]），其中 L12163-12164 验证 code-span 原文（含转义引号）逐字存活、L12164 验证描述格尾部未被吞并（折叠缺陷的直接症状）、cells[9]="✅ 完成" 验证行尾格未被吞并。集成钉（L12181-12186）进一步验证修复前误报文案来源（L10051-10053）消解。
4. **红绿算术自洽性**：修复前恰 3 用例失败（2 负例钉 + 1 集成钉——折叠为 5 格 → len!=10 与 format issue 非空），3 保留钉修复前即通过。与 Developer 声称"红态 FAILED failures=3 → 绿态 6/6"**算术吻合**（§8 未复跑声明）。

## 7. 设计一致性检查（已完成）

- 与 L12366-12369 注释契约一致（单一事实源、"no second shape source" FIX-292 教训）——本修复改在共享定义处，13 个消费点零改动即同步受益，无平行实现分叉。
- 与 FIX-372 建立的列布局契约（10 数据格/LIVE offsets）一致：测试 fixture 按 10 格构造，集成钉复用 FIX-372 的 `check_protocol_compliance` 消费面（对照 L12054-12068、L10040-10050、L14350-14368 注释）。
- docstring 机理说明风格与本文件既有 live-reference 风格（`_is_incomplete_task_status` L12388-12393 引 live FIX-253/254/255/266/REL-069）一致。
- 未偏离任何已知 ADR/契约；无接口变更（函数签名与返回形状不变）。

## 8. Developer 验证声明核实（以读代跑口径）

| 声明 | 核实方式 | 判定 |
|---|---|---|
| 红态 failures=3 → 绿态 6/6 | 测试设计算术推演（§6.4） | **自洽**（未复跑） |
| 消费方映射 8 类 43/43 | 逐点读取：13 调用点 + risk_domain.py deferred 引用（L63/L109）= 活跃任务/路线图/snapshot/carry-over/证据格式/hot-status/Check 16-17/Check 20/write-guard×3/risk_domain ≥ 8 类，映射**真实**；43/43 计数未复跑 | **映射成立；计数 Developer-claimed** |
| test_triage_write_guard.py 47/47、test_risk_mitigation_closure.py 24/24 | 两文件存在于 tests/（glob 证实） | **存在性证实；计数 Developer-claimed（未复跑）** |
| check-governance --summary-only exit 0、EVD-248 披露消解 | 与修复机理一致（L836 行修复后 10 格完好 → 误报来源消解），代码证据无矛盾 | **合理（未复跑）** |
| write-guard/cross-refs/manifest 三 PASS | write-guard 消费面（L22752/22945/22996）行为契约不变（纯解析器，输出形状不变） | **合理（未复跑）** |

## 9. 边缘问题 3 项处置合理性判定（验收标准）

| # | 登记内容 | 事实核实 | 判定 |
|---|---|---|---|
| 1 | e2e 副本 L6854 同缺陷不顺带改 | **准确**（L6879 无守卫实证；.gitignore L31 ignored fixture） | **合理**——符合 D4 修改纯粹性与 Check 27 optional fixture 先例；但需后续任务承接（F-1 P2） |
| 2 | code-span 内 `{[}/]` 仍计 depth、反斜杠字符原样追加 | **准确**（L12349-12355 花括号无守卫；反斜杠在 code-span 内走 else，escape 仅在 in_string 分支置位，无状态影响） | **合理**——观察项定级恰当，无已知实证（F-2 P3） |
| 3 | 行外未配对引号钉 in_string 至行尾 | **准确**（L12346-12348 开启/L12342-12343 唯一闭合） | **合理**——既有语义如实披露，正例钉覆盖声明与实际相符（F-3 P3） |

## 10. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | 0 | ✔ PASS |
| 5 维度全覆盖 | = 100% | 5/5（§3） | ✔ PASS |
| 每条发现标注级别 | = 100% | 5/5（F-1~F-5 均有 P 级） | ✔ PASS |
| 设计一致性检查 | 已完成 | §7 | ✔ PASS |
| AI 代码专项 5 项 | 全部完成 | 5/5（§5） | ✔ PASS |

## 11. 审查结论

## **APPROVED_WITH_NOTES**（unresolved_blockers=0）

- 硬门槛 5/5 通过；零 P0/P1；修复正确、互斥完备、测试内容强断言且红绿算术自洽。
- **Notes**（非阻塞遗留）：F-1（P2）e2e 同源副本漂移需后续任务承接（建议顺带评估切分器抽共享模块的泛化性根治）；F-2~F-5（P3）观察项/可选补钉，不要求本轮修改。
- 本结论仅为代码审查硬门槛通过，不替代测试执行复核（Developer 声称的命令运行结果未由本席复跑）与发布审查。
