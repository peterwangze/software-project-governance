# FIX-315 代码审查报告（Code Review R1 — 复审）

- **任务**：FIX-315 — V3「零校验不得 PASS」（DSH 护栏可信面修正）
- **Round**：**R1（复审）**；**前轮引用**：`docs/reviews/review-FIX-315-CODE-R0.md`（NEEDS_CHANGE / unresolved_blockers=1；P0×1 / P1×1 / P2×5 / P3×3）
- **审查对象**：工作树未提交改动（HEAD 由 `6081285` 推进至 **`135e7df`**）——`dsh_compat.py`（+316/−77）、`test_dsh_compat.py`（+597/−2）、`host-contract.json`（+1/−1，仅 `:1018` 属本任务）；三者均未入索引
- **范围外（已核）**：`verify_workflow.py` / `test_verify_workflow.py`（FIX-319）——逐 hunk 确认**未触碰** 28v 接线（`verify_workflow.py:16347 all_issues += emit_check_section()`）
- **Reviewer**：Code Reviewer Agent（全程只读；仓库零写、`~/.dsh` 零写、无仓库路径上的变异/还原实验）
- **结论**：**APPROVED_WITH_NOTES** / `unresolved_blockers=0`（本轮新发现 6 条**全部 P3**，无 P0/P1/P2）

## 1. 逐条比对表（前轮 findings）

| # | 前轮级别 | 本轮判定 | 独立证据 | 仍存问题 |
|---|---|---|---|---|
| **F-01** | **P0** | **已修复** | `UNVERIFIED_KINDS` 现为 `("NO_SCHEMA","BUILTIN")`（`:157-160`）。真探针（1 可校验行 + 1 继承禁用行）：`coverage={enabled:1,verified:1,unverified:0,reasons:{},unreadable_compositions:0}`，**`verified+unverified == enabled → True`**（R0 同输入为 2≠1 → False）；reason 无自相矛盾句；`_matrix_entry` 改忠实模型（`:537-545`）。**M-e 变异（加回该 kind）→ 5 failures**（R0 = 0） | 配套 P3 见 F-R1-02/03 |
| **F-02** | **P1** | **已修复** | UNREADABLE 同时 append 到 `unverified` 与 `details`（`:1129-1134`）；真探针混合场景**三面各 1 行** `[NOT_RUN] … could not be read (ENOENT…) — rows NOT verified`（R0 两面 0 行）；**M-f 变异 → 3 failures** | 无 |
| **F-03** | P2 | **已修复** | 新增 `coverage.unreadable_compositions`；`unverified_reasons` 回归**纯行直方图**（实测 `{}`，无 `UNREADABLE` 键）；L1 用例改断言 `unreadable_compositions == 1` ∧ `"UNREADABLE" not in unverified_reasons` | 无 |
| **F-04a** | P2 | **已修复** | 新增 `test_L3_the_render_is_not_the_old_substring_scan`（假阴性 + 假阳性 + 文件级三向）；**M-c 变异（改回子串判据）→ 1 failure**（R0 = 0） | 无 |
| **F-04b** | P2 | **已修复** | CLI 断言改 `assertIn("Result: NOT_RUN")` + `assertNotIn("Result: PASSED")`；**M-a 下失败列表现同时含 `renderer='cli'` 与 `'section'`**（R0 只含 section） | 无 |
| **F-04c** | P2 | **已修复** | `_matrix_entry` 忠实模型 + `_MATRIX_NOT_STARTED_KINDS`（`:514-519`）+ 新增 F-01 用例 | 无 |
| **F-05** | P2 | **已修复（自然消解）** | HEAD 推进后 `host-contract.json` 恰为 **+1/−1**（仅 `:1018`），FIX-317 的两个 hunk 已在 HEAD；5 文件全部 ` M` 未入索引 | Coordinator 侧：提交时须与 FIX-319 的 2 文件分离 |
| **F-06** | P2 | **已修复** | unreadable-only reason 实测 = `no preset row could be validated — 1 composition(s) could not be read, so their rows were NOT verified: … (fail-closed: never reported as PASS)`；脚本断言 `says 'disabled'? False` / `says 'would mount nothing'? False` | 归因冗余 → F-R1-05（P3） |
| **F-07** | P3 | **已修复** | `_reason_histogram` docstring 重写并与实现（空 → `"no unverified row"`）一致；`"or -"` 已删 | 无 |
| **F-08** | P3 | **已修复**（含 1 项新副作用） | 三面统一 `emit_disclosures()` + `DISCLOSURE_LIMIT=10`：实测 12 行 → 三面均 10 行 + `… and 2 more unverified item(s)`；FAIL 下三面**均不打印**披露；`_print_human` 不再无条件打印；PASS 分支无上限截断已消 | **F-R1-01**、**F-R1-04** |
| **F-09** | P3 | 未修复（P3 保留，非阻塞） | `:1018` 仍为类级 guard 引用；机检 108 OK | V8 K-8 裁决 |
| **F-10** | P3 | 未修复（建议未采纳，非阻塞） | 字段注释未加 "compared, not necessarily accepted"；语义仍由 `_MATRIX_COMPARED_KINDS` + 用例声明（自洽） | P3 保留 |

**额外自述两项的范围判定（Coordinator 指定）**：

| 项 | 判定 | 依据 |
|---|---|---|
| `run_cli` 摘要补 `inherited-disabled rows: N` | **合理范围（P3）** | F-01 把该行移出 `[NOT_RUN]` 通道后，F-08 的"三面口径一致"要求摘要同构；落在同一渲染函数、同一事实、同片边界内；实测三面摘要现均含该计数 |
| 新增 `_informational_details()` + `[INFO]` 行 | **合理范围（P3）** | F-01「行不得从屏幕消失」的直接落地；`[INFO]` 为仓库既有惯例且**不计 issue token**（见 §3③）。残留见 F-R1-02/03 |

**自述数字核对**：`test_dsh_compat.py` 43 → **60** ✓；但"1 改名 + **18** 新增"中 18 含改名替身 ⇒ 实为**净新增 17 + 1 改名**（自述算式小偏差，P3 级，不影响代码）。

## 2. 本轮新发现 findings（全部 P3）

| # | 级别 | 文件:行号 | 事实 | 影响 | 建议 |
|---|---|---|---|---|---|
| **F-R1-01** | P3 | `dsh_compat.py:1578`（`_print_human` 内 `emit_disclosures(report, stream)` 用默认 `prefix="│  "`） | `_print_human` 输出本为**无边框纯文本**，现打印 **`│  [NOT_RUN] …`**（框线字形）；R0 为 `  [NOT_RUN] …` ⇒ 统一三面时沿用了带边框面的默认前缀。实测两例原始输出 | 显示回归（非逻辑回归；`--json` 与语义不受影响） | `emit_disclosures(..., prefix="  ", indent="  ")`；当前**无测试**断言 human 面前缀 |
| **F-R1-02** | P3 | `:1055-1073` / `:1519` / `:1579` vs `:1414-1478` | `[INFO]` 行只在 `run_cli` / `_print_human`；**28v 段面未接线**，仅靠摘要计数 `inherited-disabled rows: N`，与 `_informational_details` docstring 自称不完全一致 | 三面粒度不一致（**不回归 HEAD**；事实未丢） | 接线（`[INFO]` 非 issue token，**无 gate 影响**，已实证）或写明设计取舍 |
| **F-R1-03** | P3 | `:1055-1073`（残差选择条件） | `kind ∉ FINDING_KINDS ∪ UNVERIFIED_KINDS ∧ kind ≠ "PASS"` ⇒ **未知/未来 kind 静默归入 `[INFO]`**。当前探针 10 种 kind 恰只命中 `DISABLED_INHERITED`，**无现网缺陷** | 与设计 §6.1 V4 的 G-18「每个 kind 恰属一类」分类自检交互；残差桶会掩盖新增 kind | V4 落地时把该 kind **显式白名单化**（而非依赖残差） |
| **F-R1-04** | P3 | `:1476` / `:1533` / `:1540`（`DISCLOSURE_LIMIT` 截断分支） | 新增截断路径（`… and N more unverified item(s)`）**无用例覆盖**（tests 中 `DISCLOSURE_LIMIT` / `more unverified` 0 命中）；实测三面行为一致（12 → 10+1） | 新代码路径无回归保护 | 补 1 条 > LIMIT 用例（顺带钉三面同限） |
| **F-R1-05** | P3 | `:1219-1230`（F-06 新分支） | ① `rows_enabled == 0 ∧ unreadable_compositions ≥ 1` 时 reason 只讲读失败——若同时存在另一个"全行禁用"组合，后者事实从 reason 消失（仍在 `details`）；② reason 内联 `unverified` 全文 + `emit_disclosures` 再打印 ⇒ **段面同一文本出现两次**（实测 section 两行） | 归因完备性 + 冗余（不影响事实真伪） | ① 多因并列；② reason 只引用路径/计数 |
| **F-R1-06** | P3 | 设计 `:442`（G01-b）、`:631-632`（§5.1 S2）、ADR-018 `:82` | 实现新增**第 5 个字段** `coverage.unreadable_compositions`（R0 F-03 建议路径，已采纳），但设计 G01-b 仍写 4 字段、§5.1 S2 投影示例仍写 4 字段、ADR-018 未枚举 | 文档与实现漂移；**若 V8 的 doctor S2 照抄 §5.1 示例投影，读失败事实会在 doctor 面丢失**（F-02 同类、换一个面） | **治理记录同步（Coordinator 侧）**：三处各补一句；**V8 落地时 S2 投影 MUST 带该计数** |

## 3. 独立复现结论

**① F-01 恒等式（真探针）**：`verdict=PASS | enabled=1 | checked=1 | inherited=1 | coverage={1,1,0,{},0} | verified+unverified == enabled → **True**`（R0 同输入 = 2≠1 → False）；reason 无自相矛盾句。

**② 继承禁用行"是否仍上屏"——逐路径实测（Coordinator 重点）**：

| 路径 | 结果 |
|---|---|
| ① 三面摘要计数 `inherited-disabled rows: N` | **成立**：section / cli / human 三面均有（实测 1） |
| ② `_informational_details()` → `[INFO]` 行 | **两面成立**：cli 与 human 各 1 行（`[DISABLED_INHERITED] not started — inherits disabled from ancestor entry "outer"`）；**28v 段面不打印**（未接线，见 F-R1-02） |
| ③ 全部行继承禁用 → F4 分支 | **成立**：`NOT_RUN` + `… so this preset would mount nothing`（三面一致） |
| ④ JSON `report["details"]` | **成立**：恒携带该行 |
| ⑤ FAIL 裁决下 | **成立**：`[INFO]` 在 cli/human 仍打印；摘要计数在；披露面按设计抑制（实测三面 `[NOT_RUN]` 均 False） |

⇒ **该行不会真正消失**（最弱面 = 28v 段面，仅计数无行标识，但**不回归 HEAD**——HEAD 亦不打印；R0 出现的行级 `[NOT_RUN]` 恰是 F-01 的过度计数）。

**③ quick-scan / issue token 过滤判定（实证 + 静态）**：`quickscan_selector.py:123 _ISSUE_TOKENS = ("[BLOCKING]","[ERROR]","[FAIL]","[WARN]","[ADVISORY]")` ⇒ **`[INFO]` 与 `[NOT_RUN]` 均不是 issue token**；`_parse_issue_count()` 只读引擎 `Result:` 行 ⇒ 新增 `[INFO]` **不改变 N**；且 `quickscan_registry.py` 中 `SegmentSpec("28v", …, _excluded(...))` ⇒ **28v 本就不在 quick 面**。

**④ F-02 混合披露（真探针）**：`verdict=PASS | unreadable_compositions=1`；三面**各 1 行** `[NOT_RUN] … could not be read (ENOENT…)`（R0：两面 0 行）。

**⑤ 四变异 + baseline（`%TEMP%` 副本跑真实套件，仓库零写）**：

| 变异 | 内容 | 结果 | 判定 |
|---|---|---|---|
| baseline | 未变异副本 | **60 run / 0 fail / 0 err** | 试验台忠实 |
| **M-a** | 停用 `rows_checked == 0` 分支 | **8 failures**（含 **L2 section + cli 双面**） | 抓住 ✓（F-04b 已闭合） |
| **M-c** | `emit_disclosures` 改回子串判据 | **1 failure** = `test_L3_the_render_is_not_the_old_substring_scan` | 抓住 ✓（R0 = 0） |
| **M-e** | `DISABLED_INHERITED` 加回 `UNVERIFIED_KINDS` | **5 failures** | 抓住 ✓（R0 = 0） |
| **M-f** | UNREADABLE 不上 `unverified` 通道 | **3 failures** | 抓住 ✓ |

与自述 8 / 1 / 5 / 3 **逐项一致**。

**⑥ 28v（本仓库，exit 0）**：`Compositions: 1; enabled rows: 23; schema-checked rows: 18; NOT verified: 5; inherited-disabled rows: 0` → `PASSED — verified 18 of 23 …; 5 enabled row(s) NOT verified (NO_SCHEMA=5) — disclosed as [NOT_RUN]`；屏幕 **5 行 `[NOT_RUN]`**；`writes: 0`。厂商口径 23/18 保留。

**⑦ 其他独立核验**：三套件 **60 / 46 / 108 OK**；`check-architecture-health` = **8 ERROR / 28 WARN** 且**输出中无任何 `dsh_compat.py` 条目**（`check_dsh_preset_compat` = **144 行** < 200 棘轮；`_resolve_verdict` = 67）；未用 import **0**；TODO/FIXME/XXX/HACK **0**；生产代码中 `"NOT verified" in` 仅剩 **1 处注释**（`:1471` 描述旧机制）；`host-contract.json` 逐 hunk **仅 `:1018` 一行**；仓库零 scratch；审前审后 `git status` 完全一致；真实 `~/.dsh` mtime = 20:06:00（早于本会话）。

## 4. 硬门槛复核

| 门槛项 | 阈值 | 实测（R1） | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **0** | ✓ PASS |
| 5 维度全覆盖 | = 100% | 5/5 | ✓ PASS |
| 每条发现标注级别 | = 100% | 本轮 6/6 带 P3 | ✓ PASS |
| 设计一致性检查 | 已完成 | §4.3 L1/L2/L3 + §4.4.1 G01-a~e + §4.6 三态 + §5.6 FX-01/02 + §6.1 V3①②③ 逐条 | ✓ PASS |
| AI 专项 5 项 | 全部完成 | 5/5 | ✓ PASS |

**V3 切片验收（设计 §6.1）**：① L1/L2/L3 三不变式测试绿 ✓（60 OK）；② `:365` 改写后绿 ✓，且"**变红属预期**写进 commit message"一条**未验证**（提交尚未发生）；③ `dsh_compat.py --json <FX-NO-SCHEMA-01>` → `NOT_RUN / checked 0 / issues []` ✓。

## 5. 五维度结论

1. **正确性 — 通过**：`rows_verified + rows_unverified == rows_enabled` 在真探针下成立（含 inherited-disabled、unreadable、FAIL 混合三形态）；三态与裁决顺序正确（FINDING 优先 FAIL）；F-01/F-02/F-03/F-06 全修；剩余均为显示/完备性 P3。
2. **安全性 — 通过**：无新增输入面、无注入/命令拼接变化、无密钥；隔离守卫未动（`writes: 0`）；新增输出仅为自有探针 JSON 的字符串回显。
3. **可维护性 — 通过**：`check_dsh_preset_compat` 144 行（< 200 棘轮）、`_resolve_verdict` 67 行抽取合理；无未用 import（AST 实证）；扣分项 = F-R1-01/02/03/05。
4. **性能 — 通过**：单遍 O(rows)；`_informational_details` 仅两个 CLI 面单遍调用；无新增进程/IO。
5. **测试覆盖 — 通过**：60/46/108 全绿；R0 的三处灵敏度缺口**全部闭合**（M-c / M-e / M-a-cli 现均变红）；扣分项 = F-R1-04（截断无测试）、F-R1-01（human 前缀无断言）。

## 6. 结论与下一步

**APPROVED_WITH_NOTES（`unresolved_blockers=0`）** —— FIX-315 可进入提交/闭环流程。

1. **提交时点**：本片 3 文件与并存 FIX-319 的 2 文件**分离提交**；commit message 按设计 §6.1 V3② 写明 `:365` 改红属**预期**（该条是本轮唯一"未验证"项——提交尚未发生）。
2. **后续可选（登记为低优先项，不回流本片）**：F-R1-01（human 面前缀）、F-R1-02（`[INFO]` 接入 28v 面）、F-R1-04（截断用例）。
3. **V4/V8 前置提醒**：F-R1-03（G-18 分类白名单化）；**F-R1-06（设计 G01-b / §5.1 S2 / ADR-018 同步 `unreadable_compositions`；V8 的 doctor S2 投影 MUST 带该计数，否则读失败事实在 doctor 面丢失）**。

## 7. 未验证项（如实列出）

1. 设计 §6.1 V3② 的"commit message 写明改红属预期" —— 提交尚未发生，无法验证。
2. `check-governance` 全引擎运行下的 28v 段 —— 未运行整车；`emit_check_section` 已用真报告在进程内驱动并核对输出，28v 接线一行未变（FIX-319 未触碰），故以子命令 + 进程内渲染为等价证据。
3. FIX-319 的改动 —— 范围外，仅确认其未触碰 28v / `dsh_compat` 路径。

## 8. 真实环境命令上报表（R4）

**统一防护**：全部命令以 `DSH_HOME=%TEMP%\spg-rv315-homeshim` 重定向（隔离环境 R1(a)）；该目录事后条目数 = 0。窗口 2026-09-12 23:0x–23:27 (+08:00)。

| # | 命令（关键片段） | 退出码 | 影响路径 |
|---|---|---|---|
| 1 | `git log/status/diff --stat/--numstat/show HEAD:<path>` | 0 | 只读，无写 |
| 2 | `python -m unittest test_dsh_compat` | 0 | Ran 60 OK；仅 `__pycache__/`（.gitignore） |
| 3 | `python -m unittest test_dsh_adapter` | 0 | Ran 46 OK；安装演练落 `%TEMP%\tmp*` |
| 4 | `python -m unittest test_dsh_contract` | 0 | Ran 108 OK |
| 5 | `python verify_workflow.py check-dsh-preset-compat` | 0 | 只读真实 npm 平面；`writes: 0` |
| 6 | `python verify_workflow.py check-architecture-health` | 0 | 只读；8 ERROR / 28 WARN（无 `dsh_compat.py` 条目） |
| 7 | `%TEMP%\rv315-r1\*.py` 真探针/对照脚本 ×5 | 0 | 产物仅 `%TEMP%` |
| 8 | `%TEMP%\rv315-r1\mutation_runner.py {base,ma,mc,me,mf}` ×5 | 0 | 变异仅落 `%TEMP%\rv315-r1\mut\` |
| 9 | `dsh_fixtures.py --emit-fixture FX-NO-SCHEMA-0{1,2}` ×2 | 0 | 仅写 `%TEMP%\rv315-r1\fx` |
| — | 仓库写 / `~/.dsh` 写 | — | **均 0**（真实 `~/.dsh` mtime = 20:06:00 早于会话；重定向 `DSH_HOME` 条目数 0） |

**红线声明**：未对用户 HOME 下任何配置目录执行删除/清空/重建/移动；未在仓库路径上做任何构造/变异/还原实验；未调用 Write/Edit/Agent/ask_user_question。

---

*报告结束（R1，APPROVED_WITH_NOTES / unresolved_blockers=0）。*
