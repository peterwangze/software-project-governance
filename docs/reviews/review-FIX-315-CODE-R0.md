# FIX-315 代码审查报告（Code Review R0）

- **任务**：FIX-315 — V3「零校验不得 PASS」（DSH 护栏可信面修正）
- **Round**：**R0（首次审查）**；前轮引用：无
- **审查对象**：当前工作树未提交改动（HEAD = `6081285`）——`skills/software-project-governance/infra/dsh_compat.py`（+197/−54）、`skills/software-project-governance/infra/tests/test_dsh_compat.py`（+381/−2）、`adapters/dsh/host-contract.json`（其中 **1 行**属本任务）
- **Reviewer**：Code Reviewer Agent（全程只读；仓库零写、`~/.dsh` 零写、无仓库路径上的构造/还原实验）
- **结论**：**NEEDS_CHANGE** / `unresolved_blockers=1`（P0=1 / P1=1 / P2=5 / P3=3）
- **权威规格**：设计 §4.1 / §4.3 / §4.4.1（G01-a~e）/ §4.6 / §5.6 / §6.1；事实输入 AUDIT-153 §5 G-01

## 1. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **1**（F-01） | ✗ FAIL |
| 5 维度全覆盖 | = 100% | 5/5 逐一有结论 | ✓ PASS |
| 每条发现标注级别 | = 100% | 10/10 带 P0~P3 | ✓ PASS |
| 设计一致性检查 | 已完成 | 逐条比对完成；G01-a/c/d/e 落地，**G01-b 部分不成立** | ✓（含偏离） |
| AI 专项 5 项 | 全部完成 | 5/5 | ✓ PASS |

## 2. Findings 全表

| # | 级别 | 文件:行号 | 事实（可复查） | 影响 | 建议 |
|---|---|---|---|---|---|
| **F-01** | **P0** | `dsh_compat.py:151-155`（`UNVERIFIED_KINDS` 含 `DISABLED_INHERITED`）、`:1100-1115`、`:1305-1308`；`test_dsh_compat.py:517-545` | 探针**从不**把 `DISABLED_INHERITED` 行计入 `entry.enabled`（`:434-441` 先 `inherited_disabled += 1` 并 `continue`，早于 `:443` 的 `entry.enabled += 1`）；而 `_aggregate_composition` 遍历 `entry["rows"]` 时不区分，把这些行计入 `coverage.rows_unverified` 并渲染为 "N **enabled** row(s) NOT verified"。**真探针实测**（1 行 persona 可校验 + 1 行 `disabled: true` group 的子行）：`rows_enabled=1 / rows_checked=1 / rows_inherited_disabled=1`，`coverage={enabled:1, verified:1, unverified:1, reasons:{DISABLED_INHERITED:1}}` ⇒ `verified+unverified = 2 ≠ enabled = 1`；PASS reason = `verified 1 of 1 enabled row(s) …; 1 enabled row(s) NOT verified (DISABLED_INHERITED=1) — disclosed as [NOT_RUN]`；28v 摘要同屏出现 `enabled rows: 1; schema-checked rows: 1; NOT verified: 1; inherited-disabled rows: 1` | ① Developer 自报的恒等式（`verified+unverified+未走到比较的 finding == enabled`）**不成立**；② PASS 结论句**自相矛盾**——正是 G01-d 要消除的措辞缺陷类；③ 已由 `inherited_disabled` 单独计数与 F4 分支披露的行被**二次计入**并误标为"enabled 未校验"。触发面 = **任何含 `disabled` group 祖先的用户预置**（有既有测试 `test_t05_*` 与 F4 分支专门支持，非边角） | **二选一并补测试**：(a) 从 `UNVERIFIED_KINDS` 移除 `DISABLED_INHERITED`（其语义是"未启动"，已有独立计数与 F4 披露）；或 (b) 保留行披露但在 `coverage` 中另立桶（如 `rows_not_started`），PASS reason 只报 enabled 维度。同时把 `_matrix_entry` 改为忠实模型（`enabled = 非 DISABLED_INHERITED 行数`、`inherited_disabled = 其余`）并补"1 可校验行 + 1 继承禁用行"用例 |
| **F-02** | P1 | `dsh_compat.py:1076-1086`（UNREADABLE 只进 `details`）、`:1386-1387`、`:1440-1441`、`:1447-1448`（三处渲染只看 `unverified`） | **披露回退（本轮新引入）**：混合场景（1 个可读 PASS 组合 + 1 个不可读组合，真探针）——HEAD 的 `emit_check_section` 与 `run_cli` **都**打印 `[NOT_RUN] …composition could not be read (ENOENT …) — rows NOT verified`；改后两面**均不再打印**。机制：UNREADABLE 行只 append 到 `details`，未进 `unverified`，而三处上屏判据已统一改为只遍历 `unverified` | 不可读组合在 PASS 运行中从 28v 屏幕与 CLI **消失**——正是本片要消灭的"未校验事实不上屏"；`run_cli:1444-1446` 注释自称 "an unverified row is never only in the machine-readable report" 与实测**不符** | UNREADABLE 分支同时 `report["unverified"].append(...)`（保留 `details` 副本），或三处渲染显式遍历一次 file-level 披露；补"可读 + 不可读"混合用例（当前**无**用例） |
| **F-03** | P2 | `dsh_compat.py:1080-1082`；`test_dsh_compat.py:631-635` | `unverified_reasons["UNREADABLE"] += entry["enabled"]`，而探针对 UNREADABLE 文件直接 `continue` ⇒ `enabled` 恒 0，桶恒为 0 却按键存在。实测 PASS reason 尾部出现 `(NO_SCHEMA=1, UNREADABLE=0)`，而同一报告**确实存在**一个不可读组合 | 直方图把"存在不可读文件"表达为 `UNREADABLE=0`（读者理解为"没有不可读文件"）；可信面在 read-failure 路径**低报**。L1 用例断言 `list(unverified_reasons)==["UNREADABLE"]`，把 0 计数键**固化为期望** | 按"组合"而非"行"计桶（不可读文件的行数本就不可知），或新增 `coverage.unreadable_compositions` 并从直方图移除 0 计数键；同步调 L1 用例。**不涉及** Coordinator 已裁定的 `rows_verified == rows_checked` 口径 |
| **F-04** | P2 | `test_dsh_compat.py:517-545`、`:664-671`（缺失用例） | **反相推演实证的测试灵敏度缺口**：(a) 把三处渲染判据改回 HEAD 的 `for detail in details: if "NOT verified" in detail`（= §4.3 认定的**根因形态**）→ **55/55 仍全绿**（M-c），因新披露文案本身以 "— NOT verified: " 开头且同时进了 `details`；(b) L2 的 CLI 子测试断言 `assertNotIn("[PASS]", out)`，而 `run_cli` 的 PASS token 是无括号 `Result: PASSED` ⇒ M-a 下 verdict 已回退为 PASS，cli 子测试**仍通过**；(c) `_matrix_entry` 的 enabled 模型与探针不一致（见 F-01），使唯一能守恒等式的用例**自证** | "结构化判据"与"`DISABLED_INHERITED` 归属"两项**均无测试可证伪**；CLI 面的 L2 不变式**实际未被检查** | (a) 补"可读 PASS + 不可读"混合渲染用例（同时覆盖 F-02）；(b) 改断言 `"Result: NOT_RUN" in out` / `assertNotIn("Result: PASSED", out)`；(c) 修正 fixture 模型 |
| **F-05** | P2 | `adapters/dsh/host-contract.json`（索引态）+ `git status` | `git status` 显示该文件为 `M `（**整文件已入索引**）：FIX-315 的 1 行 guard 改名与 FIX-317 的 15+2 行**同处索引**；而 FIX-317 的代码面 `dsh_contract.py` / `test_dsh_contract.py` 仍是 ` M`（未入索引） | 直接 `git commit` 会把两个 task 混进一个 commit（违 D4），并使 FIX-317 处于**半提交态** | 提交前分离：`git restore --staged` 后 `git add -p` 只取该 1 行，或**先落 FIX-317 再落 FIX-315**；commit message 按设计 §6.1 V3② 写明 `:365` 改红属**预期** |
| **F-06** | P2 | `dsh_compat.py:1267-1281` | **既有缺陷（HEAD 实测同源，非本轮引入，但落在本片修订区）**：仅有不可读组合时（`status=UNREADABLE, enabled=0, compositions 非空`）落入 `rows_enabled == 0` 分支，reason 输出 "… every row of 1 composition(s) is disabled … so this preset would mount nothing" —— 对一个**读不到**的文件断言其行全部被禁用 | 28v 屏幕上唯一的解释是**错因**；`details` 里正确的 ENOENT 文案两个面都不打印（HEAD 亦不打印） | 该分支按组合状态分派文案（UNREADABLE → 引用读失败原因），或对"仅有不可读组合"给专用 NOT_RUN reason；**可与 F-02 同批修** |
| **F-07** | P3 | `dsh_compat.py:1034-1039` | `_reason_histogram` docstring 写 "or `-`"，实现返回 `"no unverified row"` | 文档/代码漂移 | 改 docstring 或返回值 |
| **F-08** | P3 | `dsh_compat.py:1480-1484`、`:1374-1378`、`:1386-1387` | 三面上屏口径不一致：`_print_human` **无条件**打印 `[NOT_RUN]`（FAIL 裁决下也打印，实测），另两面只在 NOT_RUN/PASS 打印；`emit_check_section` 的 NOT_RUN 分支有 10 行截断、PASS 分支无上限 | 同一事实三种口径；大预置时 PASS 面可能刷 50 行 | 统一为显式 verdict 分派 + 一致截断策略 |
| **F-09** | P3 | `host-contract.json:1018` | 新引用 `test_dsh_compat.py::test_L1_zero_checked_rows_never_verdict_pass` **语义贴切**（L1 零校验不变式正是 D-40/D-76 的落地机制；旧名 `…disclosed_not_failed`（断言 PASS）方向相反 ⇒ 改名属**强化而非削弱**），且被 `test_guard_references_resolve_to_existing_tests_or_checks` 机检通过（108 OK）。但它是**类级**不变式（合成矩阵），不点名 `plan-mode` 行；同 subject 的 `negative_fixtures` 用 `@deepseek-ai/dsh-tool-ask-user` 而非 plan-mode | 属既有粒度（旧引用同样类级），非本轮回归 | 保留现状；V8 K-8 裁决时复核 |
| **F-10** | P3 | `dsh_compat.py:1156-1158` | `rows_verified` 含被 schema **拒绝**的行（`CONFIG_INVALID` 也 `checked += 1`）。实现、注释与测试声明（`_MATRIX_COMPARED_KINDS = ("PASS","CONFIG_INVALID")`）三者自洽 | 命名 "verified" 可能被读作"校验通过" | 保持口径（Coordinator 已裁定），字段说明补一句 "compared, not necessarily accepted" |

## 3. 审查重点逐项结论

| # | 审查重点 | 结论 |
|---|---|---|
| 1 | 三层不变式是否真成立 | **L1 ✓**（`rows_checked==0 ⇒ verdict ∈ {FAIL, NOT_RUN}`，FINDING 优先；M-a **8 红**实证）／**L2 ✓**（零校验报告渲染 `[NOT_RUN]`、无 `[PASS]`；但 cli 面断言无效 → F-04b）／**L3 ✓**（行级逐行披露、判据按 kind；但 UNREADABLE **文件级**披露回退 → F-02）。三态政策（exit 0、不计 gate issue、屏幕 `[NOT_RUN]` + 原因）实测通过 ✓ |
| 2 | 上屏判据是否真结构化 / 双事实源 | 是：`"NOT verified" in detail` **生产代码零命中**（独立 grep；仅 tests 3 处断言**数据**内容 + docs 1 处描述）。但该"结构化"**无测试可证伪**（M-c 55/55 绿 → F-04a）。`unverified` 与 `details` 对**行级**披露同源同文案（同一 `line` 对象，`:1110-1115`）⇒ 非"双事实源"；但二者**不同延**（UNREADABLE 只在 `details`）而渲染只读 `unverified` → **F-02 成因** |
| 3 | `coverage` 口径忠实性 | `rows_verified == rows_checked` 恒等**成立**（同一 `entry["checked"]` 单一来源；含被拒行，有注释 + 测试声明，自洽）。但 **"verified + unverified 覆盖全部 enabled 行" 在 `DISABLED_INHERITED` 上不成立**（真探针实测 2≠1）→ **F-01**；`unverified_reasons` 直方图在 UNREADABLE 路径失真（恒 0 桶）→ F-03 |
| 4 | 改写/改名是否削弱守卫 | **未削弱**：被改写的 `:365` 由"断言 PASS + checked 0"改为"断言 NOT_RUN + issues [] + coverage + 披露"，方向与 C-23 / §4.4.1③ 一致且**更强**；新增 `test_mixed_rows_pass_discloses_the_unverified_ones` 保留 PASS 路径正向覆盖。无"只要不 PASS 就算过"的放宽。新增 12 条**部分**能抓回退（M-a 8 红、M-b 10 红；M-c / M-e 0 红 → F-04） |
| 5 | 契约引用收口 | 新引用语义贴切且方向更强；**仅改这 1 行**，机检通过（108 OK）；与 FIX-317 hunk 可分离（逐 hunk 归属见 §4）→ 但**索引未分离**（F-05）。粒度注记见 F-09 |
| 6 | 范围纪律 | V4（group/walk）、V5、V8 面**均未触碰**（`PROBE_SCRIPT` 仅 `NO_SCHEMA` 文案一处 hunk，属 G01-e）；`launch.py:566` 未碰；`launch.py` / `lib/index.js` / `verify_workflow.py` / `registry.py` 未出现在 `git status` |
| 7 | AI 专项 + scratch | 5 项逐一有结论（§5）；仓库根 scratch = **0**；唯一未跟踪文件属并发任务 |

## 4. 独立复现结论

**① FX-NO-SCHEMA-01 改造前→后（同字节 fixture、同真机 schema 平面）**

| | BEFORE（HEAD 副本） | AFTER（工作树） |
|---|---|---|
| verdict | **PASS** | **NOT_RUN** |
| rows_checked | 0 | 0 |
| issues | `[]` | `[]` |
| coverage / unverified | 键不存在 | `{rows_enabled:1, rows_verified:0, rows_unverified:1, reasons:{NO_SCHEMA:1}}` / 1 行 |
| reason | `0 enabled row(s) validated against the plugin set resolved from …` | `rows_verified 0 of 1 enabled row(s) — NOT verified: no enabled row's config could be compared against a schema (NO_SCHEMA=1); fail-closed: …` |
| 行文案 | `module exports no Config schema — the loader passes this config through unvalidated`（G01-e 指出的**未证实断言**） | `this guard cannot validate this row's config (the module exports no Config schema)` |
| CLI 退出码 | — | **0** |

⇒ 设计 §6.1 V3③（`--json → NOT_RUN`）**成立**；G01-e **成立**。

**② 正向对照不放宽**：persona `text:` 非法 config（%TEMP% 组合，真 schema）→ **FAIL**，`issues[0] = …row "persona" (@deepseek-ai/dsh-persona): $.prefix missing required value`，`rows_enabled=2 / rows_checked=2`。28v 实测 `23 enabled / 18 checked` **未缩水**。

**③ 三套件（`DSH_HOME` 重定向至 `%TEMP%\spg-rv315-homeshim`）**：`test_dsh_compat` **Ran 55 OK**（含 3 条 live fixture 用例实跑未跳过）／`test_dsh_adapter` **Ran 46 OK**／`test_dsh_contract` **Ran 108 OK**（全部 exit 0）。43→55 = +12 与自报一致。

**④ 28v 输出**：`Compositions: 1; enabled rows: 23; schema-checked rows: 18; NOT verified: 5` → `Result: PASSED — verified 18 of 23 …; 5 enabled row(s) NOT verified (NO_SCHEMA=5) — disclosed as [NOT_RUN]`，屏幕 **5 行 `[NOT_RUN]`**，exit 0，`writes: 0`。

**⑤ grep 零命中（独立复核自报 #1）**：`"NOT verified" in detail` 在生产代码 **0 命中**（仅 tests 3 处断言 report **数据**内容 + docs 1 处描述）⇒ 声明为真。

**⑥ hunk 归属（`host-contract.json` +18/−2 逐 hunk）**：

| hunk | 行 | 内容 | 归属 |
|---|---|---|---|
| `@@ -1015,7 +1015,7 @@` | `:1018` | guard 引用改名 | **FIX-315**（+1/−1） |
| `@@ -1200,6 +1200,21 @@` | `:1203-1217` | 新增 `coverage.entries[evidence.recording]` | FIX-317（+15） |
| `@@ -1563,7 +1578,8 @@` | `:1581-1582` | `D-05.slice` 加 `"V8"` | FIX-317（+2/−1） |

⇒ **FIX-315 确实只改 1 行且与 FIX-317 可分离**（索引层面未分离，见 F-05）。

**⑦ 反相推演（5 组，全部在 `%TEMP%` 副本上跑真实套件，仓库零写）**：

| 实验 | 变异 | 结果 | 判定 |
|---|---|---|---|
| baseline | 未变异副本 | 55 run / 0 fail / 0 err | 试验台忠实 |
| **M-a** | 停用 `elif report["rows_checked"] == 0`（退回 PASS） | **8 failures** | L1 真被钉住 ✓ |
| **M-b** | `report["unverified"]` 永不填充 | **10 failures** | 结构化披露真被钉住 ✓ |
| **M-c** | 三处渲染判据改回 `if "NOT verified" in detail`（= §4.3 根因形态） | **0 failures（55/55 绿）** | **根因修复未被测试钉住 ✗ → F-04a** |
| **M-e** | 从 `UNVERIFIED_KINDS` 移除 `DISABLED_INHERITED`（= F-01 最小修复） | **0 failures（55/55 绿）** | 现状与修复都不被区分 ✗ → F-01 佐证 |

另：M-a 下 `test_L2_…never_renders_pass` 仅 `renderer='section'` 失败、cli 子测试通过 → **F-04b**。

**⑧ 范围与红线**：`check_dsh_preset_compat` = **184 行**（AST 实测，自报 #7 成立，>200 warn 已消解）；`_aggregate_composition` = 66 行（拆出合理）；**仓库根 scratch = 0**；审前审后 `git status` / `diff --stat` **完全一致**；**未发生** FEAT-030 审查中那类"瞬时改写契约"行为（全部变异/坏输入只在 `%TEMP%\spg-rv315\` 内构造）。

## 5. AI 代码专项 5 项

| 专项 | 结论 |
|---|---|
| mock 残留 | **0**（`mock.patch.object` 仅作渲染面注入缝，live 用例实跑真探针） |
| 硬编码返回值 | **0**（无硬编码裁决；仅 F-07 文案漂移） |
| 幻觉 API | **0**（AST 确认全部 stdlib + `unittest.mock`） |
| 未实现 TODO | **0**（两文件零命中） |
| 过度实现 | 基本干净；`details` + `unverified` 冗余、`coverage` 参数重复传入属 P3 级 |

## 6. 五维度结论

1. **正确性 — 不通过**：裁决顺序 / L1 / L2 / L3 / 三态政策正确；但 `coverage` 在 `DISABLED_INHERITED` 上算术不成立且 PASS 结论句自相矛盾（**F-01，P0**），UNREADABLE 披露回退（**F-02，P1**），UNREADABLE 直方图桶恒 0（F-03）。
2. **安全性 — 通过**：无新增外部输入面、无注入/命令拼接变化、无密钥；`subprocess` 调用未改；隔离守卫未动（实测 `home_writes: 0`）。
3. **可维护性 — 基本通过**：`_aggregate_composition` 抽出合理（184 行 < 200 棘轮）；命名与注释质量高；扣分项见 F-07/F-08。
4. **性能 — 通过**：单遍 O(rows)；无新增进程/IO。
5. **测试覆盖 — 不通过**：12 条新测试覆盖 L1/L2/L3 与 FX-01/02 端到端（43→55 且实跑）；但存在三处灵敏度缺口（F-04 a/b/c），其中 (a) 使本片的**根因修复在回归上完全无保护**。

## 7. 结论与下一步

**NEEDS_CHANGE（`unresolved_blockers=1`）**。

建议 Coordinator 退回同一 Developer 处理 **F-01（P0，必改）** 与 **F-02（P1，建议同批）**，并顺带 **F-03/F-04/F-06/F-07/F-08**（同文件、同测试面，避免二轮再返），随后按 M7.4 step 4.6 spawn **同一 Code Reviewer 复审（R1）**。提交前 MUST 先解决 **F-05** 的索引混装。

**本方审查不构成"测试通过 = 逻辑正确"的推论**：三套件 209 项全绿的同时，本报告以真探针实测给出 **2 个反例**（F-01/F-02）与 **2 个 55/55 仍绿的反相变异**（M-c/M-e）。

## 8. 真实环境命令上报表（M7.7 R4）

**统一防护**：全部命令以 `DSH_HOME=%TEMP%\spg-rv315-homeshim` 重定向（隔离环境 R1(a)）；该目录事后条目数 = 0。窗口 2026-09-12 22:50–23:06 (+08:00)。

| # | 命令（关键片段） | 退出码 | 影响路径 / 证据 |
|---|---|---|---|
| 1 | `git diff HEAD -- <3 files>` / `git status -uall` / `git show HEAD:…dsh_compat.py` | 0 | 只读；HEAD 副本写 `%TEMP%\spg-rv315\before\`（非仓库） |
| 2 | `python -m unittest test_dsh_compat` | 0 | Ran 55 OK；仅 `__pycache__/`（.gitignore） |
| 3 | `python -m unittest test_dsh_adapter` | 0 | Ran 46 OK |
| 4 | `python -m unittest test_dsh_contract` | 0 | Ran 108 OK |
| 5 | `verify_workflow.py check-dsh-preset-compat` | 0 | 只读扫描真实 npm 平面；`writes: 0` |
| 6 | `python dsh_compat.py --json %TEMP%\…\FX-NO-SCHEMA-01.cordis.yml` | 0 | NOT_RUN / checked 0 / issues 0 |
| 7 | `dsh_fixtures.py --emit-fixture FX-NO-SCHEMA-0{1,2} --out %TEMP%\spg-rv315\fx` | 0 | 仅写 `%TEMP%` |
| 8 | 8 个 `%TEMP%` 对照/变异驱动脚本 | 0 | 只读仓库代码与真实平面；变异全部落 `%TEMP%\spg-rv315\mut\` |
| — | 仓库写操作 / `~/.dsh` 写操作 | — | **均 0**（真实 `~/.dsh` LastWriteTime = 2026-09-12 20:06:00，早于本会话 3 小时） |

**红线声明**：未对用户 HOME 下任何配置目录执行删除/清空/重建/移动；未在仓库路径上做任何构造或还原实验；未调用 Write/Edit/Agent/ask_user_question。

---

*报告结束（R0，NEEDS_CHANGE / unresolved_blockers=1）。*
