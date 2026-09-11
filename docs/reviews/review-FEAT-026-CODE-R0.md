# Code Review: FEAT-026-CODE-R0 — quick-scan Slice-2（quick 编排器 + 四态契约 + shadow 通道）

- **Task**: FEAT-026（round 0）
- **Reviewer**: Code Reviewer Agent（只读审查；不修改产品代码、不与用户直接交互）
- **Round**: R0（首次审查；无前轮报告）
- **审查对象**: **commit `2a5e9ec`**（`git show 2a5e9ec`）
- **冻结锚核验（逐文件 `git rev-parse 2a5e9ec:<path>` vs `git hash-object <path>`，全部一致 + 工作树零 `M`/`??`）**：
  | 文件 | blob | 规模（实测 numstat） |
  |---|---|---|
  | `infra/quickscan_selector.py` | `95e4ab031c5f3a0b0f48e4d9e56dfe5e6822e46c` | 716 / 0（新建） |
  | `infra/tests/test_quickscan_selector.py` | `344deb061f6fd5e928e575e8103d20691ff7e04b` | 571 / 0（新建） |
  | `infra/verify_workflow.py` | `c81b6d37e3ae1c652d332ad89ab5a9e581f001c1` | **29 / 2** |
  | `core/architecture-baseline.json` | `3ad0025317fd0397a7929b397e8b66ca7713aa43` | **4 / 3** |
  | `infra/tests/test_quickscan_registry.py` | `56b8c912e7137cebe0566b95569a33cc9c683a62` | **18 / 2** |
  | `infra/tests/test_archguard_ratchet.py` | `d304942702cfff3bfc3c6973275855f9905536a3` | **13 / 7** |
  | **合计** | — | **6 files changed, 1351 insertions(+), 14 deletions(-)** ✅ |
  **口径对账（如实登记）**：任务书逐文件数字与 commit 实际 numstat **有 4 处不符**——`verify_workflow.py`（书 +31/−14，实 **+29/−2**）、`architecture-baseline.json`（书 +7/−7，实 **+4/−3**）、`test_quickscan_registry.py`（书 +20/−20，实 **+18/−2**）、`test_archguard_ratchet.py`（书 +20/−20，实 **+13/−7**）；两新建文件与**总数 +1351/−14 完全吻合**。以 commit 为准（不影响任何裁决）。
- **设计契约（逐项比对）**: `docs/requirements/quickscan-evaluation-0.79.0.md` §4.1（L157-165 S-A/S-B/S-C 验收与切换门槛）、§4.2（L167-176 性能分档与判定口径）、§4.3（L178-183 回退）、§6 L250-251（Slice-2 验收①②③）、§9.3（L32 原文摘引：选择策略 + 不改检查体 + 未知回退 full）、§2.4（L101-122 四态契约与四条硬约束）；`docs/requirements/architecture-evolution-0.80.0.md` §4.1 R1~R7（L254-262）、§3.6 `CheckSpec`。
- **消费面**: `infra/quickscan_registry.py`（FEAT-025 + FIX-304 终态，`d6d12e8`+`2a5e9ec` 后未变）；`infra/registry.py`（FEAT-022 L1 消费方）。
- **执行过的只读命令**: `git show/rev-parse/hash-object/numstat/status`；`pytest -B -p no:cacheprovider`（目标文件 43 例 + 覆盖率）；`unittest discover`（全量，§六第 6 条）；`verify_workflow.py archguard-ratchet`；**真实运行 4 次**（`check-governance` 默认 / `--quick` / `--shadow` / `--quick --shadow`，计时）；`python -B` 内存内省（映射/根因/优先级/常量引用）。
- **边界声明**: 未修改任何文件（唯一例外 = 本报告）；6 文件 blob 审查前后一致；真实运行后 `git status --porcelain` 为空 ✅（无写入副作用）；仓外写操作仅覆盖率数据文件（`COVERAGE_FILE` → `%TEMP%`）。
- **环境披露（负载）**: 计时与全量复跑期间，本机同时有一个后台全量测试进程在跑 §六第 6 条的全量回归——故 §六第 5 条的墙钟为 **serial-adjacent 观测量级**（RISK-048 口径，不做门禁），本节已如实标注。

---

## 一、5 个评审维度逐项结论

| 维度 | 结论 | 依据（本人独立核验） |
|---|---|---|
| **正确性** | **通过（含 P1×1 / P2×1）** | 选择面与四态裁决在真实树全链正确：`--quick` 真跑 `chosen=45 / not-run=25`（25 段即 C1 排除集，**逐段与注册表排除集/产品门声明恒等**），`N=52` 且 25 段 NOT_RUN 未使 N 归零；`--quick --shadow` 真跑 `[S-A] union=70` + `[S-B] compared=45 mismatches=0`。**但** `--shadow` 单独使用时不成立（**F-1，P1**：quick 面未生效却按 quick 渲染 → 摘要误标 + 24 段伪 POLICY_OBSERVATION_MISMATCH + S-B 退化为 full-vs-full 恒零差异）。 |
| **安全性** | **通过（无发现）** | 选择器零 I/O（AST 机判：模块级零 `read_text/write_text/open` 调用）、零 `print`（AST 机判 `Call(print)=0`）、零 `subprocess/eval/exec`（机判 0）、不 import 巨石（机判 0 命中）、仅 stdlib（hashlib/io/re/contextlib/dataclasses）+ 注册表；无用户可控字符串进入正则/命令；无凭据/敏感数据；fail-closed 方向正确（不可信 → 清除 quick/shadow → 跑 full）。真实运行零写入（`git status` 空）⇒ P7 数据安全无暴露面。 |
| **可维护性** | **通过（含 P3×4）** | 职责单一（选择 / 解析 / 四态 / 渲染 / shadow / 接线入口六段清晰）；函数短小（最长 `parse_engine_sections` ≈52 行含注释、`render_quick_output` 24 行）；docstring 逐条带设计锚点（§4.1/§2.4/§6 L251/§255/§9.3）；消重良好（`_STATE` 属性族、`_runs` 复用）。**缺陷面**：F-3（2 个公开常量零引用）、F-4（指纹只打印前 5）、F-5（基线注记未含本批）、F-8（旗标组合语义未文档化）。 |
| **性能** | **通过（无发现）** | 新增成本 = 1 处分支 + 1 处门控条件 + 1 处惰性 import；R6 复跑 `cold import 196 modules (baseline 196, Δ0)` ⇒ **惰性 import 未进入冷启动 import 集**（机证）；选择器解析为单遍 O(lines)，四态裁决 O(70)；墙钟（本轮 serially-adjacent）：默认 full **52.1s** / `--quick` **9.9s** / `--quick --shadow` **65.0s** / `--shadow` **106.2s**。 |
| **测试覆盖** | **通过（含 P2×1）** | 目标文件 **43 passed**（0.82s，清点 43 个 `def test_` / 5 类）；覆盖率 **375 stmts / 34 miss / 91%**（与声称逐数字吻合）；S-A 契约与 S-B 判定的**纯函数级**负对照齐备（重叠/缺原因码/未落表/裁决不等/缺段）。**缺口**：**F-2（P2）S-A/S-B 的"接线"路径零覆盖**（Missing 含 692-696、699-701、706-716 = `render_quick_output` 的 shadow 分支与 `_capture_full_run`）——F-1 正是从这里逃逸。 |

---

## 二、六条验收逐条交叉核对（独立复现为真 / 采信 / 证伪）

| # | 声称 | 裁决 | 我的独立证据 |
|---|---|---|---|
| **①** | S-A/S-B 真跑 `compared=45 mismatches=0` | ✅ **独立复现（真跑）** | `python -B verify_workflow.py check-governance --quick --shadow` → `[S-A] dry-run shadow — chosen=45 not-run=25 union=70 (registry=70)` + 逐段原因码 + 声明指纹；`[S-B] execution shadow — compared=45 segment(s) mismatches=0` + 「选择集裁决 == full 裁决」；同批 `Governance: 52 issues (quick) | 28 passed / 17 failed / 25 not-run / 0 cache-reused / 0 undetermined` 与 `Governance: 55 issues (full, shadow baseline — authoritative for this invocation)`。**限制（F-1）**：`--shadow` **单独**运行也打印同一句 `mismatches=0`，但那是 full-vs-full 的空转（见 F-1）⇒ **该证据串不能单独区分两种口径**，建议 Coordinator 在取证时记录完整命令 |
| **②** | 四态五计数 + 机器守卫 + 负对照 | ✅ **独立复现** | 真实运行汇总行五计数齐备（passed/failed/not-run/cache-reused/undetermined）且被 §2.4 正则契约接受；负对照测试 4 条（缺计数→违规、全段未执行→`N=unknown` 非 0、parse degraded→违规、25 not-run 而 N=4 不归零）；`test_state_tokens_follow_the_four_state_contract_vocabulary` 校验五 token 词表 |
| **③** | 默认路径逐字节等价（"三例"） | ✅ **成立（口径需精确）** | **结构等价的硬论证**：引擎侧 `args.quick` 的**全部**耦合点仅 2 处（`L14647` dispatch 条件、`L14739` 门控早期返回，机判全文仅此 2 处）；无旗标路径仍走原文 `else: all_issues = _run_full_engine_checks(args)`；`_product_gate_active` 在 `args.quick` 假值时逐行等同原逻辑。**测试实证 3 条**：`test_default_path_is_byte_identical_without_quick`（`assertEqual(buf.getvalue(), engine_output)` = 唯一**逐字节**断言）、`test_summary_only_path_is_unchanged_without_quick`（分支不变+无四态串）、`test_quick_flags_are_registered_on_the_cli`（CLI 注册实证）。**如实口径**：严格"逐字节"断言 = **1 条**，另 2 条为结构/注册对照（任务书"三例"宜读作"三项对照"） |
| **④** | FIX-304 消费口径（duplicate ValueError → UNDETERMINED(CENSUS_UNTRUSTED) → 回退 full；判别 = `fail_closed`） | ✅ **独立复现** | 内存实测：`select(observed_ids=snap+("29",)).untrusted` = `CENSUS_UNTRUSTED: …duplicate CheckID(s) ['29']…`；`select(observed_ids=snap+("41",))` → `fail_closed=True, undeclared=('41',)`；`prepare_quick_args` 两种不可信下均清除 `quick/shadow` 并保留 `quick_requested=True`（回退后渲染 `_fallback_report`，`mode="full-fallback"`，notices 含 `UNDETERMINED(…)`+`full`）；`test_fail_closed_discriminant_is_used_not_fallback_target` 钉住"判别 = `fail_closed` 而非 `fallback_target`"；回归钉：`qr.guard_completeness(observed_ids=dup)`/`reconcile_snapshot(actual_ids=dup)` 仍抛 `ValueError` ✅（FIX-304 R1 守卫保持）。**残差**：注册表侧重复亦标 `CENSUS_UNTRUSTED`（F-3，P3） |
| **⑤** | 性能 69.2s → 14.2s 实测口径 | ✅ **成立（我的复测更快，声称口径未夸大）** | 本轮 serially-adjacent 实测：**默认 full 52.1s / `--quick` 9.9s（5.3×）**；`--quick --shadow` 65.0s；`--shadow` 单独 106.2s。按 §4.2 分档：`--quick` **< 15s = STRETCH 达成**、且远优于 Phase-1 估算 28~33s 与 PASS 下限 <60s ✅。**反向核验**：声称值（full 69.2s / quick 14.2s）**均高于**我的实测 ⇒ 不存在"压低基线放大增益"的夸大方向（差异归因于机器负载与树内容变化，EVD 已如实记录 full 涨至 69.2s 而未放宽达标口径）。**负载披露**：计时期间有后台全量测试进程并行（见头部环境披露） |
| **⑥** | TDD 红 5 failed → 绿 43 passed | ⚠ **GREEN 独立复现；RED 采信** | GREEN：`pytest` → **43 passed / 0.82s**，清点 `def test_` = 43、类 = 5 ✅。RED（接线前 5 failed/35 passed）：**未独立复现**——需重建"接线前引擎 + 已写测试"状态；**静态论证**：`Acceptance3DefaultPathTests` 中 7 条直接驱动 `vw.cmd_check_governance`，未接线时 quick/shadow 分支不存在 ⇒ 这批用例如 `test_quick_implies_the_summary_path_with_the_four_state_line`、`test_quick_calls_the_engine_with_the_product_gate_disabled`、`test_default_path_is_byte_identical_without_quick`（`eng.assert_called_once()` + 分支语义）必然失败，数量级与"5 failed"自洽 ⇒ 采信 |

**汇总：6/6 成立**（① 附 F-1 限制、③ 附口径精确化、⑥ 为采信+静态论证）。

---

## 三、三项 Coordinator 授权：合规性复核

### ① baseline sanctioned regen — ✅ **合规，归属链完整（1 处注记待补，F-5 P3）**
- **数值归属逐项复算**：引擎净增 +27 行（+29/−2）↔ `r1_mainfile_budget.anchor_loc` **24329 → 24356 = +27** ✅ 精确对应；`r4_print_orchestration.per_function` 新增 `"cmd_check_governance": 1`、`total` **1310 → 1311** ✅，且该 print 实测位于 `verify_workflow.py:14655`（`cmd_check_governance` 的 dispatch 分支内）= **L5 渲染位**，非业务段 ✅（R4 纪律"L3 域模块禁 print、渲染归 L5"未被破坏——选择器侧 AST 机判 `Call(print)=0` ✅）。
- **机器自证**：复跑 `archguard-ratchet` → `R1 PASS 24356≤24356`、`R4 PASS 1311≤1311`、**`R7 PASS deterministic=True; committed==fresh True`**（= 提交的基线就是一次忠实 regen 的产物，非手编漂移）+ `Result: PASS (0 violations)`, exit 0 ✅。
- **披露链**：EVD-1000（含"仓外临时 baseline 机证复原路径后执行"的方法）+ commit message「授权①」段 + `test_archguard_ratchet` 的审计链注释 ✅；`exemptions` 未被用作增长许可（其 allowance 仍为 0，仅 DEC-183/184 的 FEAT-019 self-bootstrap RECORD）⇒ anchor 上移走的是**sanctioned regen**而非豁免通道 ✅ 正确路径。
- **唯一缺口**：`r1_mainfile_budget.design_anchor_note` 的自描述仍写 "intervening engine deltas: FIX-300 + FEAT-019 dispatch wiring"，**未包含 FEAT-026 的 +27**（该字段的既有用途正是登记 intervening deltas）→ **F-5（P3）**：数值归属由 EVD/commit 承载未断链，但基线文件自描述已陈旧。

### ② `test_quickscan_registry.py` 守卫强化 — ✅ **真更强（代理断言留 1 处 P3，F-6）**
- **新旧对比**：`assertNotIn("quickscan", source)`（全串零出现）→ 正向 footprint：`assertNotIn("quickscan_registry", source)` **保留**（数据载体零引用不变）+ `len([l for l in source if "quickscan" in l]) == 1` + **该行逐字符等于** `"        from quickscan_selector import prepare_quick_args, render_quick_output"` + `assertNotEqual(wiring[0], wiring[0].lstrip())`（必须在分支内缩进）。
- **更强的三点**：① 任何**第二处**出现（第二个 import、引擎侧新增选择逻辑、甚至注释提及）立即打穿；② 逐字符钉死 import 的模块名与导入名（改名/改目标即失败）；③ 缩进断言把"模块级 import"这一 §255/import 预算违规形态挡住（配合 `test_engine_imports_the_selector_lazily_inside_the_quick_branch`）。
- **未变弱**：注册表数据载体零引用断言仍在；且新增了 selector 侧的正向用例 ⇒ 不是"放宽"而是"换更强的正向不变式" ✅。
- **代理性残差（F-6 P3）**：两处守卫都只断言"该行有缩进"，**未断言其父节点是 `--quick` 分支体**——若 import 上移到 `cmd_check_governance` 函数首行（仍缩进），两测试均通过，但**每次 check-governance 调用都会 import selector**（R6 预算面变化）。建议 AST 断言 `ImportFrom` 的父节点为该 `if` 的 body。

### ③ `FACTS_PRINT_TOTAL` 1310 → 1311 校准 — ✅ **合规，审计链完整**
- 实测：基线 `cmd_check_governance: 1` / `total 1311` ✅ 与 `count_print_calls(ENGINE)["total"]` 的一致性由 `test_r4_total_matches_facts_census` 机判（本轮复跑棘轮族含此断言，见 §六）；棘轮 `R4 PASS 1311≤1311` ✅。
- **审计链注释写全**：`1315（facts §3.1, 2026-09-09）→ 1310（FEAT-012 G5：5 个 print 移出引擎，sanctioned shrink）→ 1311（FEAT-026：dispatch 渲染行，per_function 归属 cmd_check_governance，EVD-1000 授权）` ✅ 与 FEAT-012 先例同款形态（该先例即"校准常量随普查重定"）。
- **质变点**：commit message 明确**拒绝**用 `sys.stdout.write` 规避 R4 计数（"渲染量不变而计数不动 = 对计数器的攻击，非收敛"）——这是正向的治理自觉，予以记录。
- **无越界**：仅 1 常量 + 审计链注释（+13/−7 全在常量与两处 docstring），未触碰 R4 计数逻辑本身。

---

## 四、接线形态合规性（vs §255 载体纪律 / §9.3 ALT-2 / R2 / R6）

| 检查项 | 结论 | 依据 |
|---|---|---|
| 引擎改动仅接线（无检查体改动） | ✅ | diff 3 hunk：dispatch 分支（+11/−1）、`_product_gate_active` quick 面（+9/−1）、CLI 注册（+9/−0）；**无任何 Check 段体内改动**；`args.quick` 全文耦合点仅 2 处（机判） |
| 选择逻辑全部落在 infra/ 独立载体 | ✅ | `quickscan_selector.py` 716 行承载选择/解析/四态/渲染/shadow；引擎只捕获 stdout 并打印返回值 |
| 不 import 巨石（R2 反向依赖禁令） | ✅ | 选择器机判零 `import verify_workflow`/`argparse`；棘轮 `R2 PASS 46 ≤ 46`（域模块反向依赖清单零增长） |
| 惰性 import（R6 启动预算） | ✅ | 引擎侧唯一 `quickscan` 行 = 分支内 import（守卫逐字符钉死）；棘轮 `R6 INFO cold import 196 (baseline 196, Δ0)` ⇒ 未进入冷启动 import 集 |
| **复用 FIX-270 跳过机制（零段级改动）** | ✅ **真实运行机证** | `--quick` 真跑：25 段以既有 `[SKIP]` 机制被跳过（`[NOT_RUN] 25 segment(s): 7(PLUGIN_GIT_FACT_SOURCE), … 40(PLUGIN_PACKAGE_ASSET)`）= 注册表排除集 / `_PLUGIN_PRODUCT_CHECK_IDS` 恒等；无第二套选择路径（`test_engine_source_has_no_second_selection_path`） |
| 与 §9.3 原文一致（"同一批检查的选择策略…不改检查体"） | ✅ | 上表逐项满足；fallback（未知 → full）语义亦已实现 |
| 回退路径（§4.3 项 3：删模块 + 接线行即回现状） | ✅ | 模块零外部状态、零 I/O；接线 3 点可逆 |

---

## 五、两处解析精度缺陷修复：真实性与有牙性

| 缺陷 | 引擎侧真实触发（我独立核实） | 修复 | 有牙性 |
|---|---|---|---|
| ① 段 17 的 `[PASS]` 行**引文**中的 `[SKIP]` 被误判为跳过声明 | `verify_workflow.py:15254` `print(f"│  [PASS] {e['task_id']} ({e['evd_id']}): …")` —— Check 17 逐条打印**来自治理数据**的条目文本；`.governance/evidence-log.md:1818`（EVD-970 行）实测同时含 `[PASS]` 与 `[SKIP]` ⇒ 该行会被打印成 `[PASS] … [SKIP] …`，旧"子串即跳过"规则必误判 | `_is_skip_declaration` 改为**行首标记**（`line.lstrip("│ \t").startswith("[SKIP]")`），:350-358 | ✅ 负对照 `test_skip_marker_quoted_in_prose_does_not_skip_a_segment`（:306）用真实形态合成文本；**真跑机证**：`--quick` 输出 `0 undetermined`（修前为 2 个假 UNDETERMINED） |
| ② 无 banner 段 **30b** 的跳过行落在 30c 段体内被误归属 | `verify_workflow.py:16107-16121`：30b 段**无 `┌─ Check 30b:` banner**，其 `print("│  [SKIP] product self-check — Check 30b loop wiring call sites …")`（:16121）出现在前一段（30c）的 banner 之后 ⇒ 旧规则把它归给 30c，令健康的 30c 变 UNDETERMINED | 跳过声明的 `_SKIP_ID_RE` 点名规则：命名**其他** Check id 的行归属该 id（:383-389） | ✅ 负对照 `test_skip_line_naming_another_check_is_attributed_to_that_check`（:324）；真跑 `--quick` 中 30b = NOT_RUN(PLUGIN_TREE_SCAN)、30c = FAILED（未被误标）✅ |

**判定：两处修复均为真修复且有牙**——触发条件在真实引擎/治理数据中可复现（上表逐处给出源码行与数据行），负对照用合成文本而非打桩，且修复后在真实树上 `0 undetermined` ✅。

---

## 六、门禁声称 vs 独立核实

| # | 声称 | 核查结果 | 依据 |
|---|---|---|---|
| 1 | 目标测试 43 passed | ✅ **独立复现** | `pytest -B -p no:cacheprovider` → `43 passed in 0.82s`；清点 `def test_` = 43、classes = 5 |
| 2 | 覆盖率 91%（375 stmts / 34 miss） | ✅ **逐数字吻合** | `--cov=quickscan_selector --cov-report=term-missing` → `Stmts 375 / Miss 34 / 91%`；Missing = 324-326, 328, 335, 463, 481, 489, 504, 506, 570, 572, 603, 641, 646, 662, **692-696, 699-701, 706-716**（后三项 = shadow 接线与 `_capture_full_run`，见 F-2） |
| 3 | archguard-ratchet PASS（R1 24356 / R2 46 / R4 1311 / R5 82 键+70 段 / R6 Δ0 / R7 committed==fresh） | ✅ **独立复跑** | `R1 PASS 24356≤24356`；`R2 PASS 46≤46 across 36 files`；`R3 PASS`；`R4 PASS 1310…1311`（实测 1311≤1311）；`R5 PASS cli 82/82 frozen, segments 70/70 frozen`；`R6 INFO 196 modules (baseline 196, Δ0)`；`R7 PASS deterministic=True; committed==fresh True` → `Result: PASS (0 violations)`, exit 0 ✅ |
| 4 | 棘轮测试族 38 passed / FIX-304 族 82 passed | ✅ **独立复现** | `test_archguard_ratchet.py` 38 passed、`test_quickscan_registry.py` 82 passed（本轮 R1 复审同款复跑；二者均在 §六第 6 条全量范围内） |
| 5 | 性能 full 69.2s → quick 14.2s（4.9×） | ✅ **成立且未夸大** | 我的 serially-adjacent 实测：full **52.1s** / quick **9.9s**（5.3×）；`--quick --shadow` 65.0s；`--shadow` 单独 106.2s。声称值均高于实测 ⇒ 无夸大方向；按 §4.2 分档 quick < 15s = STRETCH ✅（负载披露见头部） |
| 6 | 全量 discover Ran 2635 / 31F+2E+1S（失败集完全回到基线存量族） | ⚠ **总数复现；F/E 分类差 1 条（合计相等）** | 独立复跑：`Ran 2635 tests in 635.216s` → `FAILED (failures=32, errors=1, skipped=1)` = **32F+1E+1S**——**失败+错误合计 33 = 声称的 31F+2E = 33 相等**（即 1 条用例的 F/E 归类漂移，非新增失败），总数 2635 ✅ 精确复现。**关键判定（FEAT-026 触面零失败）**：失败清单逐条核验，**无一落在本批触面**（`test_quickscan_selector` 43 ✅ / `test_quickscan_registry` 82 ✅ / `test_archguard_ratchet` 38 ✅ 在全量运行中全绿），失败集中于 `test_pre_commit_review_evidence`（多条）、`test_loop_runtime_claims`、`test_change_triage`、`test_cleanup`、`test_hooks`、`test_triage_write_guard`、`test_verify_workflow` 等**非本批模块** ⇒ "失败集完全回到基线存量族 / 非存量失败 = 0" 的**方向成立**。**保留项**：我无法复算"存量族"权威清单（EVD-1000 记 38F、commit 记 31F+2E、我测 32F+1E，三者失败+错误合计 = 40/33/33），且本轮复跑与我的其它只读核验命令并行（**负载未排除**）⇒ 若需精确签名，建议 Coordinator 在空载树复测。`+43` 增量算术（FIX-303 记 2592 → 2635）自洽 ✅ |
| 7 | 静态自检（零 print/零模块级 I/O/不 import 引擎、py39 OK） | ✅ **机判复现（py39 面采信）** | AST：`Call(print)=0`；选择器零 `read_text/write_text/open`；零 `import verify_workflow`/`from verify_workflow`；零 TODO/FIXME/NotImplementedError/type: ignore。**py39 OK 采信**（本机无 3.9 解释器；静态证据：`from __future__ import annotations` + 无 3.10+ 语法） |
| 8 | lint NOT_RUN（ruff/mypy/flake8 缺失） | ⚠ **采信（未验证安装状态）** | 本轮未调用 lint；等价静态自检（机判零 noqa/type: ignore、纯 stdlib、执行通过）不否定该声明，但 lint 面仍属未验证 |

---

## 七、AI 专项 5 项（逐项结论）

| 项 | 结论 | 依据 |
|---|---|---|
| **mock 残留** | **无（生产代码零 mock）** | 选择器机判 `unittest.mock/MagicMock/patch` = 0；`mock` 仅出现在**测试文件**（`mock.patch.object(vw, "_run_full_engine_checks", …)`）——用于隔离 dispatch（避免真跑引擎），且同文件另有**真实子进程** CLI 测试（`subprocess.run([…, "check-governance", "--help"])`）+ 真实树运行证据 ⇒ 属正当测试技术，非打桩残留 |
| **硬编码返回值** | **无欺骗性硬编码** | 被钉住的常量全部经我独立复现为真：`45/25/70`（真实运行输出一致）、`1311/24356`（棘轮实测一致）、`_SKIP_LINE`（= 引擎 :14780 的真句）、`REASON_*` 词表、`_DIGEST_CAP=3`（有界输出）。测试夹具用真实注册表 + 合成引擎文本（**不是**复制实现输出） |
| **幻觉 API** | **无** | 新增 API 全部真实且执行验证：`hashlib.sha256`、`io.StringIO`、`contextlib.redirect_stdout`、`dataclasses.dataclass(frozen=True)`、`re`（含 `_QUICK_SUMMARY_RE` 命名组）、`types.SimpleNamespace`（测试）、`ast.walk`（测试）；无臆造符号（我按 AST 抽出的模块级调用属性集逐项均为真实方法） |
| **未实现 TODO** | **无** | 机判 `TODO/FIXME/XXX/HACK/NotImplementedError` = 0（选择器 + 测试）；`STATE_CACHED` 的 Slice-3 生产者属**经声明的范围边界**（docstring 明写"Slice-2 只声明、计数恒 0 但必现"，§6 L252 归属 Slice-3），非遗留桩 |
| **过度实现** | **无** | 未实现 Phase-1.5 缓存/内容指纹（§6 L252）、未实现 input_deps 闭包（Phase-2）、未新增第二套选择路径、未新增 CLI 子命令（仅 2 旗标）、未触碰 check 体；`declaration_fingerprint` 显式声明为**声明指纹**并划出 Slice-3 边界 ✅ |

---

## 八、发现汇总（P0~P3 + file:line + 事实依据 + 建议）

| # | 级别 | 位置（file:line） | 问题与影响 | 事实依据 | 修复建议 |
|---|------|------------------|------------|----------|----------|
| **F-1** | **P1** | `quickscan_selector.py`:651-675（`prepare_quick_args` 从**不**置 `args.quick=True`）+ `verify_workflow.py`:14647（dispatch 以 `quick **or** shadow` 进入该分支）+ `:23490-23493`（`--shadow` help 宣称 "run quick + full in one invocation"） | **`--shadow` 单独使用时 quick 面未生效，却按 quick 口径渲染**，产生四重后果：① 摘要把 **full 面**的 N 标为 `(quick)`（真跑 `Governance: 55 issues (quick)`，而 `--quick` 面 N=52）；② **24 段伪 `UNDETERMINED(POLICY_OBSERVATION_MISMATCH)`**（"政策说排除、观察却执行"——在此并非真政策违规，而是旗标组合产物）；③ **S-B 比较退化为 full-vs-full** ⇒ 恒 `mismatches=0`，即"选择集裁决 == full 裁决（零意外差异）"是**空转的假绿**；④ §4.1 切换门槛（S-A+S-B ≥3 会话/≥10 commit 零意外差异）若以该形态累积，证据无效。**方向**：不是静默数据损坏（24 段 mismatch 是可见的 fail-safe 披露），但 **验证通道的假绿** 正是本仓最高优先级的病理族（同 FEAT-025 F-1、FIX-304 G-1）。**正向对照**：设计口径 `--quick --shadow` 完全正确（§二①）。 | ① 真实运行 `check-governance --shadow`（无 `--quick`）→ `Governance: 55 issues (quick) | 28 passed / 17 failed / 1 not-run / 0 cache-reused / 24 undetermined` + `[UNDETERMINED] 24 segment(s): 7(POLICY_OBSERVATION_MISMATCH)…40(…)` + `[S-B] compared=45 mismatches=0`；② 真实运行 `--quick --shadow` → `52 issues (quick) | 28/17/25/0/0` + `compared=45 mismatches=0`（对照成立）；③ 真实运行 `--quick` → 52 issues / 25 not-run / **0 undetermined**；④ 单元级根因实证：`prepare_quick_args(SimpleNamespace(quick=False, shadow=True))` → 事后 `quick=False, shadow=True, quick_requested=True` ⇒ 引擎按 **full** 跑（`_product_gate_active` 因 `args.quick` 假值返回 True）而渲染 `mode="quick"` | 三选一（均 ≤5 行）**(a)** `--shadow` 隐含 quick：在 `prepare_quick_args` 判定通过后 `setattr(args, "quick", True)`（与 help 文案一致，推荐）；**(b)** `main` 中 `if args.shadow and not args.quick: parser.error("--shadow requires --quick")`；**(c)** 保留语义但**拒绝空转**：`shadow_compare` 前置校验（捕获文本中存在 not-quick 段被执行 ⇒ 标 `[S-B][INVALID]` 而非 `mismatches=0`），并改 help 文案。**无论哪条**：补 1 条 "`--shadow` 单旗标" 的负对照测试（见 F-2），并修正 `--shadow` 的 help 文案 |
| **F-2** | **P2** | `tests/test_quickscan_selector.py`（缺 `render_quick_output` + `_capture_full_run` 接线用例）；对应覆盖缺口 `quickscan_selector.py`:692-696 / 699-701 / 706-716 | 验收①的**执行 shadow 接线路径零单元覆盖**：现有 S-B 用例只测纯函数 `shadow_compare`/`shadow_lines`，**未测**"引擎捕获 → render → 二次 full 运行 → 比较"的接线（覆盖率 Missing 精确落在这 12 行）。后果：F-1（单旗标空转）与"二次运行 args 状态复原"（`_capture_full_run` 的 try/finally）均无机器看护——**F-1 即由此逃逸**。 | ① 覆盖率 Missing 逐行列出 692-696（shadow 分支体）、699-701（`mode="full"` 渲染）、706-716（`_capture_full_run` 全体）；② 全量 43 例中无一条调用 `render_quick_output(..., args.shadow=True)`（我按测试名单与 grep 双向核对）；③ F-1 的真跑签名（55/24 mismatch）在任何测试中都不可能出现 | 补 2 条接线用例（用 `mock.patch.object` 替换 `engine_runner` 两次返回不同捕获文本）：**(i)** `--quick --shadow` 全链（断言两次 runner 调用、`args.quick` 在第二次调用时为假且调用后被还原、S-B 行出现）；**(ii)** `--shadow` 单旗标（按 F-1 选定语义断言：隐含 quick 或明确报错/INVALID，二者之一被钉死） |
| **F-3** | P3 | `quickscan_selector.py`:61/:109（`REASON_REGISTRY_FAULT`）、:58/:113（`REASON_NOT_QUICK`）；`select()`:284-287 | 两个**公开**（入 `__all__`）UNDETERMINED/NOT_RUN 原因常量**零引用**（机判 0 次非定义引用）；且 `select()` 的 `except ValueError` 不区分故障侧——实测 `declared_ids` 侧（**注册表自身**重复）也被标为 `CENSUS_UNTRUSTED`（"观察不可信"），与 §2.4 的 "注册表缺该段声明" 语义不同源。影响：诊断精度（异常文本内含 context 标签可部分补偿），行为方向正确（仍回退 full）。 | ① 常量引用计数机判：`REASON_REGISTRY_FAULT`=0、`REASON_NOT_QUICK`=0（其余 4 个原因码各 1-3 次）；② 实测 `qs.select(declared_ids=snap+("29",)).untrusted.split(":")[0]` = `CENSUS_UNTRUSTED`；③ `select()` 只捕获一个 `ValueError` 分支 | 在 `select()` 内按异常 context 分流（`"declared_ids" in str(exc)` → `REASON_REGISTRY_FAULT`），或删去未用常量并在 docstring 说明"注册表侧故障亦归 CENSUS_UNTRUSTED" |
| **F-4** | P3 | `quickscan_selector.py`:600-601（`shadow_dry_run_lines` 的指纹行） | §4.1 L161 S-A 机制要求 dry-run 输出「将执行集 + 逐段排除原因 + **逐段输入指纹**」：实现中**排除原因逐段齐备**（25 段 ✅），但**指纹只打印前 5 段**（`selection.chosen[:5]` + `" …"`），且未显式声明截断（读者无法从输出判断是"全部"还是"前 5"）。能力面存在（`declaration_fingerprint(id)` 对 45 段均可调用，测试 :123 已逐段调用）⇒ 属**披露口径**与 §4.1 字面的偏差，非能力缺失。 | ① :601 `chosen[:5]` 硬编码切片 + 省略号；② 真实运行输出 `[S-A] fingerprints: 1:411fa64aad6b0c4c, 2:…, 5:0eaeb7aa1bb209c0 …`（仅 5 项）；③ §4.1 L161 原文"逐段输入指纹" | 二选一：全量打印 45 段（45×18 ≈ 810 字符，仍在 FIX-278 G1 预算内），或显式标注 `first 5 of 45 shown; full set via declaration_fingerprint(<id>)` |
| **F-5** | P3 | `core/architecture-baseline.json`（`r1_mainfile_budget.design_anchor_note`） | 授权①的**基线自描述注记未随本批更新**：该 note 的既有用途是登记 intervening engine deltas，现仅列 "FIX-300 + FEAT-019 dispatch wiring"，**未含 FEAT-026 的 +27**。归属由 EVD-1000/commit 承载且 `R7 committed==fresh` 证明数值忠实 ⇒ **披露链未断**，但基线文件自描述对后续审计者不完整。 | ① 该字段文本（git show 显示为**上下文行**，本批未改）；② `anchor_loc` 24329→24356 与引擎净增 +27 精确对应；③ R7 committed==fresh True | 把 "FEAT-026 Slice-2 dispatch wiring (+27)" 补入该 note 的 deltas 列表（与既有一致口径） |
| **F-6** | P3 | `tests/test_quickscan_registry.py`:580-598（强化后的 footprint 守卫）+ `tests/test_quickscan_selector.py`:552-560 | 守卫是"**缩进 ⇒ 分支内**"的**代理断言**：两处都只断言该 import 行有缩进，未断言其父节点是 `--quick` 分支体。若 import 上移到 `cmd_check_governance` 函数首行（仍缩进），两测试**均通过**，但每次 check-governance 调用都会 import selector（R6"按命令 import 集合计数"面变化）。 | ① 两条测试的断言体（`assertNotEqual(line, line.lstrip())` 为唯一结构约束）；② 引擎全文 `quickscan` 仅 1 处（机判）⇒ 当前无违规，属前瞻性强度问题；③ R6 预算语义 = 按命令 import 集合计数（evolution §4.1 R6 L261） | 用 AST 断言该 `ImportFrom` 的 `parent` 为 `if quick/shadow …` 的 body（约 6 行），使"分支内"成为机判而非代理 |
| **F-7** | P3 | `.governance/evidence-log.md`:EVD-1000（全量数字段）vs commit `2a5e9ec` message（门禁段） | 同一交付的**全量数字两处不一致**：EVD-1000 写 `全量 2635/38F+2E+1S——+7 归因：6=棘轮基线陈旧（regen 复原）+1=FIX-304 守卫按设计证伪（强化处置）`；commit message 写 `全量 discover Ran 2635 / 31F+2E+1S（失败集完全回到基线存量族）`。EVD 记的应是 **regen 前**的观测值，但措辞读作终态结果 ⇒ 复算时不一致（同 FIX-304 G-4 的记录精度族）。**影响**：治理记录可复算性；两处 2635 总数一致。 | ① 两处原文（本报告 §六引）；② 差 7 = EVD 自述的两项归因之和（6+1）⇒ 38F 为修复前观测；③ 我的独立全量复跑给出终态数（见文末补记） | 把 EVD-1000 该句改为"全量终态 2635/**31F**+2E+1S；regen/守卫强化**前**观测 38F（+7 归因：6+1）"（数字不动，只标口径） |
| **F-8** | P3（讨论） | `verify_workflow.py`:14647-14656、:14728-14740、:23486-23496 | **旗标组合语义未文档化**：① `--quick --product-gates` 时 `--quick` **静默压过**用户显式 `--product-gates`（实测 `_product_gate_active` 返回 False）——用户显式要求跑产品自检却被静默忽略；② `--shadow` 单独 vs `--quick --shadow` 的语义差异未在 help 中区分（F-1）；③ `--quick` 与 `--summary-only` 并存时 quick 优先（合理但未写明）。 | ① 实测三组：`{quick:T, product_gates:T}`→False、`{quick:F, product_gates:T}`→True、`{quick:T, product_gates:F}`→False；② `:14739` 的早期返回先于 roots/product_gates 判定；③ help 文案仅描述 `--quick` 效果 | 在两条 help 文案中各加一句优先级说明（如"--quick 优先于 --product-gates：quick 面的定义即排除产品自检段"）；若认为冲突应报错，则在 main 加互斥校验 |
| — | **P0** | — | **无 P0**（无安全漏洞 / 无数据损坏面 / 无不可逆副作用；真跑零写入；核心选择与四态裁决在真实树全链正确） | §一/§二/§六 | — |

**汇总：P0 = 0；P1 = 1（F-1）；P2 = 1（F-2）；P3 = 6（F-3~F-8）。**

---

## 九、硬门槛裁决

| 门槛 | 结果 |
|------|------|
| 冻结锚核对（6 文件 blob 与 commit 逐字节一致） | ✅ 一致（工作树零 `M`/`??`；审查前后复算相同） |
| 逐行读全量改动（+1351/−14，6 文件） | ✅ 两新文件**全文通读**（716 + 571 行）；4 个改动文件**逐 hunk 通读**（引擎 3 hunk / 基线 4 hunk / 两测试各 2-3 hunk），非抽样 |
| 5 维度逐一结论 | ✅ §一 |
| 设计一致性检查（§4.1/§4.2/§4.3/§6 L250-251/§9.3/§2.4/§255/R1~R7） | ✅ §二/§三/§四逐项比对 |
| 每条发现级别 + file:line + 事实依据 | ✅ F-1~F-8 |
| AI 专项 5 项 | ✅ §七 |
| 结论（含 `unresolved_blockers` 独立行） | ✅ §十 |

---

## 十、审查结论

# APPROVED_WITH_NOTES

unresolved_blockers=0

**终态理由**：六条验收**逐条成立**——① S-A/S-B 经**真实树运行**独立复现（`chosen=45 / not-run=25 / union=70` + 逐段原因码 + 声明指纹 + `compared=45 mismatches=0`）；② 四态五计数必现且被 §2.4 正则机器守卫、负对照四类齐备（含"25 not-run 不使 N 归零"与"全段未执行 → `N=unknown`"）；③ 默认路径**结构等价**（`args.quick` 全文仅 2 处耦合，机判）并有逐字节断言与 summary-only/CLI 对照；④ FIX-304 消费口径 6 例实测成立（重复 CheckID → `CENSUS_UNTRUSTED` → 清旗标回退 full，判别字段 = `fail_closed`，且注册表侧守卫回归钉仍在）；⑤ 性能按 §4.2 分档 **quick < 15s（STRETCH）**，且声称值高于我的实测（无夸大方向）；⑥ TDD GREEN 独立复现（43 passed），RED 采信并附静态论证。三项 Coordinator 授权**全部合规**：基线 regen 的 +27/+1 与引擎净增、dispatch 渲染位**精确对应**，`R7 committed==fresh True` 机器自证其数值忠实；守卫强化为**真更强的正向不变式**；R4 校准随普查重定且审计链写全（并明确拒绝 stdout.write 规避计数）。接线形态合规（§255 载体纪律 / §9.3 ALT-2 / R2 46≤46 / R6 Δ0），两处解析缺陷均为**真修复且有牙**（触发点在真实引擎源码与治理数据中逐处可复现；真跑 0 undetermined）。AI 专项 5 项无异常。**P0 = 0，五维硬门槛全通过** ⇒ 依 code-review SKILL「循环角色」段与角色定义（NEEDS_CHANGE 仅当 P0>0 或硬门槛未全通过），本报告给通过终态并声明 `unresolved_blockers=0`。

**发现计数（独立行，供机器记录）**：P0 = 0；P1 = 1；P2 = 1；P3 = 6。

**唯一 P1（F-1）的处置要求**（按 code-review SKILL 第四步「P0=0 且 P1>0（有遗留计划）→ 有条件合并」）：F-1 是 **`--shadow` 单旗标下的验证通道假绿**（S-B 退化为 full-vs-full 恒零差异）+ 摘要误标 + 24 段伪 mismatch。**设计口径 `--quick --shadow` 完全正确**（§二①真跑证据成立），故不构成阻塞；但该单旗标形态被 CLI help 文案（"run quick + full in one invocation"）**主动邀请**，且修复成本 ≤5 行 ⇒ **建议本轮或紧随补丁轮落地**（§八 F-1 的 (a)/(b)/(c) 三选一）。若本轮不修，**MUST 由 Coordinator 登记为遗留项并附关闭截止日期**，且在 §4.1 切换门槛（≥3 会话/≥10 commit）取证时**强制记录完整命令**（`--quick --shadow`），以免空转结果计入累计证据。

**P2 处置要求**：F-2（shadow 接线零覆盖）建议与 F-1 同批落地（新增 2 条接线用例），否则 F-1 的修复本身也无机器看护。

**P3 处置**：F-3（未用常量/故障侧分流）、F-4（指纹截断披露）、F-5（基线注记补 FEAT-026）、F-6（AST 分支归属断言）、F-7（EVD 全量口径）、F-8（旗标优先级文档化）——均非阻塞，可由 Coordinator 记跟踪表或随补丁轮顺带处理。

**机器记录口径提示**：`unresolved_blockers=0` 独占一行且无附着细目（沿用 REL/FEAT/FIX 系列先例，避让 provably-zero 探针）。

---

## 十一、审查边界与残余未核验面（如实声明）

- **只读边界**：未修改任何文件（唯一例外 = 本报告）；6 文件 blob 审查前后一致；**4 次真实引擎运行后 `git status --porcelain` 为空**（零写入副作用）；仓外写操作仅 `%TEMP%\cov_feat026_review.dat`（`COVERAGE_FILE` 显式重定向）+ 各测试自身 `TemporaryDirectory()`。
- **真实运行披露**：`check-governance`（默认 / `--quick` / `--shadow` / `--quick --shadow`）为**仓内只读诊断命令**，未触碰 `$HOME`/`$DSH_HOME`/仓外路径；计时为 **serial-adjacent**（并发后台全量测试进程，负载未排除）。
- **⚠ 采信项**：① TDD 的 **RED 5 failed** 未独立复现（需重建接线前状态），附静态论证（§二⑥）；② `py39 OK` 未验证（本机无 3.9 解释器，静态证据支持）；③ **lint 未运行**（ruff/mypy/flake8 安装状态未验证）⇒ lint 面属未验证；④ §六第 6 条全量回归的**终态计数**以文末补记为准。
- **❓ 未核验面（不写成事实）**：① `--shadow` 单旗标是否被设计视为**受支持形态**——§4.1 L161 只写 `--quick --shadow`，本报告的 P1 定级基于 CLI help 文案的邀请语义（若 Coordinator 判定单旗标非契约形态，可据 F-1 的 (c) 方案降级为文档修正，定级可复核为 P2）；② `input_deps` 闭包类语义属 Phase-2，未评。

*审查边界声明：本报告全部结论指向可复查事实（git 命令输出、文件行号、真实运行 stdout、pytest/coverage/ratchet 输出、内存内省结果）。采信与未核验项已在 §六、§十一显式标注；无结论来自推测。*

---

## 补记（全量回归复跑结果回填）

**复跑命令**：`python -B -m unittest discover -s skills/software-project-governance/infra/tests -p "test_*.py"`（仓内口径；**`pytest` 全仓收集不可用**——`project/e2e-test-project/` 为同树副本，basename 冲突致 51 collection errors，故仓内全量口径是 unittest discover，与 EVD/commit 的 "Ran N" 记法一致）。

| 项 | 结果 |
|---|---|
| 全量终态（本轮独立复跑） | **`Ran 2635 tests in 635.216s` → `FAILED (failures=32, errors=1, skipped=1)`** = 32F+1E+1S，**exit 1** |
| 与声称 `2635 / 31F+2E+1S` 的一致性 | 总数 **2635 ✅ 精确复现**；失败+错误合计 **33 = 31+2 ✅ 相等**；**F/E 归类差 1 条**（同一条用例在两次运行中被归为 FAIL vs ERROR），非新增失败 |
| 非存量失败 = 0 判定 | **方向成立**：失败清单**无一落在 FEAT-026 触面**（quickscan 选择器/注册表、archguard 棘轮三族在本次全量运行中全绿）；失败全部落在非本批模块（`test_pre_commit_review_evidence` / `test_loop_runtime_claims` / `test_change_triage` / `test_cleanup` / `test_hooks` / `test_triage_write_guard` / `test_verify_workflow`）。**保留**：无法复算"存量族"权威清单，且本轮复跑负载未排除（与我的只读核验命令并行）⇒ 精确签名建议空载复测 |
| 三处记录口径（供 Coordinator 取一） | EVD-1000 = 2635/38F+2E+1S（regen **前**观测，+7 归因 6+1）；commit message = 2635/31F+2E+1S（终态）；本轮 Reviewer 复跑 = 2635/32F+1E+1S。三者**失败+错误合计 = 40 / 33 / 33** ⇒ 终态口径一致（33），EVD 的 38F 需按 F-7 标注为"修复前观测" |
