# Code Review — FEAT-039-CODE-R1（round 1 复审）

| 项 | 值 |
|---|---|
| 任务 | FEAT-039 — 注入/工具返回/生成预算 CI（AUDIT-154 切片 A-8） |
| 类型 | 代码审查（Code Reviewer / code-review SKILL）——**R0 findings 修复验证轮** |
| round | **R1**（复审；前轮 = `docs/reviews/review-FEAT-039-CODE-R0.md`，机录 `.governance/review-FEAT-039-R0.md`，`next_round=REVIEW-FEAT-039-R1`） |
| 复审前提 | **Coordinator 裁决已采纳**：R0 P1-1 的期望值 17,219/17,220/2,739 B 判定为**误判**；正式口径 = **3,904 / 22,858 / 23,484 / 2,724 B**（canonical 权威提取器实测）。裁决三条依据本轮**逐条独立核验并全部成立**（§一） |
| 本轮改动面 | `checks/injection_budget.py`（773 行；委托 + 两行口径 + 前缀 + read/gate/索引 + sha256_16）、`tests/test_verify_workflow.py`（31 个 Feat039 方法）、`tests/test_governance_cost.py`（P3-5）、`tests/test_contract_matrix.py:69`、`tests/test_registry.py:90/106-108`、`infra/TOOLS.md:579/584/585` |
| 审查面 | 上述文件全文/段落逐行读；`sync_entry_projection.py:84-142` 权威边界规则；`commands/governance-init.md` 行域实测；活体 `CLAUDE.md` 实测；冻结面 `core/architecture-baseline.json` |
| 审查方法 | **只读**（Read/Grep/Glob）+ pwsh **只读**字节/行域实测（自建独立提取器，未调用任何写操作、未运行测试套件） |
| 结论 | **APPROVED_WITH_NOTES** |

---

## 〇、结论行

> **APPROVED_WITH_NOTES**
> **`unresolved_blockers=0`** · R0 清单 11 条：**已修复 8 / 由裁决承接 1 / 未修复 2** · 本轮新增 **P3 = 5**（F-1~F-5）· `P0 = 0` / `P1 = 0` / `P2 = 0`
> 硬门槛：P0=0 ✓ · 5 维度全覆盖 ✓ · 每条发现带 P0~P3 ✓ · 设计一致性 **已完成** ✓ · AI 专项 5 项完成 ✓
> **可合并**（P0=0 且 P1=0）。新增 5 条 P3 均为文档/死码/效率/跟踪面，不构成 BLOCKING；其中 F-3/F-4（治理记录面）建议由 Coordinator 随 R1 写回一并处置。

**一句话**：R0 的唯一阻断项（P1-1）**根因不在实现、在口径判断**——R0 用"首个裸围栏"读法把 standard/strict 模板截断在嵌套 `Bootstrap 变更纪律` 围栏，而 canonical 权威（`sync_entry_projection.extract_canonical_templates`）明文规定块闭合围栏是切片内**最后一个**裸围栏，**嵌套围栏不得截断块**（§一）。Developer R1 的处置方向完全正确：不再自建边界，改为**委托权威提取器**，并用 canonical **等值断言 + 字节钉 + 反向 needle** 三重锁把口径固定下来。

---

## 一、Coordinator 裁决核验（三条依据逐条独立核验）

### 依据 ①：权威模块自述——"嵌套围栏不截断块"**成立**

`skills/software-project-governance/infra/sync_entry_projection.py:84-117` 逐字核验：

- 函数 docstring（87-92）：*"Boundary rule: a block runs from its label's open fence to the NEXT label line (or the next `### Step N` header for the last block). **The block's closing fence is the LAST bare fence line inside that slice — nested fences (e.g. the Bootstrap 变更纪律 block inside the standard template) therefore cannot truncate a block.**"*
- `_closing_fence_stop`（127-142）：`fences = list(_FENCE_LINE_RE.finditer(region)); return open_end + fences[-1].start()` —— 取 `fences[-1]`（**最后一个**），与 docstring 一致。
- `_FENCE_LINE_RE = re.compile(r"(?m)^```\s*$")`（47）、`_TEMPLATE_LABEL_RE` 消费标签行的 open fence（48-50）→ 提取块 = **两围栏之间的 markdown 正文**（不含任何围栏行）。
- 末块（secondary-thin）region_end = 标签后首个 `### Step` 头（107-108）→ 不被模板内含的 `### Step N` 截断。

**结论**：R0 的"首个围栏闭合"读法（261/441、537/718）**违反被委托模块的自述**。裁决成立。

### 依据 ②：活体证据——453-533 属**注入正文**（非"模板规格说明文字"）**成立**

| 实测项（本会话只读执行） | 值 |
|---|---|
| `commands/governance-init.md` 裸围栏行行号（`^```\s*$`） | 258, 441, 448, **535**, 718, 725, **832**, 868, 906, 914, 935, 961 |
| standard 标签行 / 开围栏行 | 260 / 261 → 内容 262-533，闭合围栏 **535** |
| strict 标签行 / 开围栏行 | 536 / 537 → 内容 538-830，闭合围栏 **832** |
| standard 块内嵌套围栏 | 441、448（即 `### Bootstrap 变更纪律` 代码块 439-451）——**仅内层** |
| 活体 `CLAUDE.md` bootstrap 段 | **22,857 B / 272 行**（第 3 行 → 第 274 行；结束于 `- 治理文件读取编码（FIX-278 G4/F）…` 行末） |
| canonical standard 块 | **22,858 B / 272 行** |
| 差异 | **1 B = 段末换行**（活体段后接下一个 H2，不保留尾随空行）——**逐字节同源** |

活体 `CLAUDE.md` 的 H2 序列（实测行号）：`## Governance Bootstrap（强制…）`(3) → … → `## 干活前检查（每次收到任务时）`(194) → `## 提问规则（强制）`(202) → `## 收工前检查（session 结束前）`(237) → `## 详细规则`(246) → `## 故障排除（Agent 行为异常时）`(250) → `## 当前项目治理状态快速入口`(261)。**这五个 H2 段落实际存在于登入文件内**，即每次会话注入。

更强的定论证据链（超出裁决要求，本轮补强）：`sync_entry_projection.plan_entry_writes:285-288` 把 `templates[profile]` **原样**交给 `replace_bootstrap_section` 写入入口文件（`applied` 路径没有任何追加/裁剪），而本门禁测的正是同一个 `templates[profile]`。因此"门禁测到的字节数"与"登入会话的字节数"**在构造上同源**。R0 称 442-535 为"模板规格说明文字"与实文不符：该区段是 standard 模板的**模板内正文**（含 `### Bootstrap 变更纪律` 与四个 H2 实用段），不是模板外的说明。

**结论**：R0 P1-1 对 standard/strict 的"夸大约 29-30%"判定**不成立**。裁决成立。

### 依据 ③：secondary-thin 真越界（R0 正确部分）与三档 16 B 围栏标记——**成立且已修复**

本会话自建独立提取器复算（同时实现两种口径，互相对照）：

| profile | R0 口径（首个围栏） | **canonical 口径（最后一个围栏 = R1）** | Δ |
|---|---|---|---|
| lightweight | 3,904 B（块内无围栏，两口径同值） | **3,904 B / 63 行** | 0 |
| standard | 17,203 B | **22,858 B / 272 行** | **+5,655 B** |
| strict | 17,204 B | **23,484 B / 293 行** | **+6,280 B** |
| secondary-thin | 2,724 B | **2,724 B / 32 行** | 0（R0 的 thin 数字本身取自标签→`### Step 8`，已正确） |
| 合计 | — | **52,970 B** | — |

- **16 B 围栏标记**：R0 的 `_extract_marked_block_range` 会把起始行的**开围栏计入**块内、并终止于下一档**开围栏**（`lines[start:end-1]` 的端点算术），故其"canonical 内容"读数恒比权威口径**多 16 B**（```` ```markdown\n ```` = 12+1=13… 实测：R0 的 standard 内容应为 17,203 B，而其报告表列 17,219 B = 17,203+16）。本会话独立复算 R0 口径得 **17,203/17,204 B**，与 R0 表列 17,219/17,220 相差恰好 16 B —— **Developer 披露的"16 B 围栏标记"与我的独立复算一致**。
- **secondary-thin 真越界**：R0 报 4,321 B（resolver）vs 2,739 B（其自算）。按权威口径真值 = **2,724 B**（R0 的 2,739 亦比真值多 16 B，同因）。越界真实存在（4,321 − 2,724 = **1,597 B**），即 `commands/governance-init.md` 中 thin 块之后的 `**双入口去重（FEAT-037…）**` 规格说明段被计入。**已修复**：R1 委托权威后绑定于标签后首个 `### Step`（实测 868 行闭合围栏）。

**裁决三条依据全部成立；R1 验收按 canonical 口径（3,904 / 22,858 / 23,484 / 2,724）判定，未按 R0 的 17,219 系列判"未达标"。**

---

## 二、R0 findings 逐条比对（11 条）

| # | R0 级别 | R0 结论 | R1 状态 | 独立核验依据 |
|---|---|---|---|---|
| **P1-1** | P1 阻断 | 入口模板切片越界（含非注入文本） | ✅ **已修复（且 R0 判定本身被裁决推翻）** | 切片改为委托 `sync_entry_projection.extract_canonical_templates`（`injection_budget.py:352-374`）；标签改用 `find_marker_line` 仅作**歧义锚**（`ENTRY_TEMPLATE_MARKERS:73-83` 注释明示"never re-defines a boundary"）；`load_injection_surface` 仅做歧义探针 + 取 `.get(profile, "")`（399-410）；`_next_template_marker`/`ENTRY_TEMPLATE_MAX_GAP`/`_after` 已删除（grep 0 命中）。三层新锁：canonical 等值 `test_entry_template_surfaces_price_the_canonical_blocks:20226-20246`、字节钉 `{3904,22858,23484,2724}`（20219-20224）、反向 needle `test_entry_template_slice_excludes_text_outside_the_block:20248-20266`。**我的独立复算与仲裁口径逐位吻合（3,904/22,858/23,484/2,724）**，活体 22,857/272 行同源 |
| **P2-1** | P2 | `over_budget_tiers` 与裁决口径错位 | ✅ **已修复** | `format_budget_report` 改为**两行**口径 `Over budget — gated (moves the verdict): …` / `Over budget — report-only (measurement): …`（664-670）+ 逐层 `[{GATE}] note` 前缀（671-673）；CLI 两分支统一打印 `gated over-budget tiers:`（761-769）；Check 33 走同一渲染函数（`emit_check_section:686-694`）故自动同口径。测试 `test_report_separates_gated_from_report_only_over_budget:20298-20322` 同时断言渲染行与 CLI 行 |
| **P2-2** | P2 | 3 处归属注释与实现相反 | ✅ **已修复（3/3）** | `test_contract_matrix.py:69` → `checks/injection_budget.py`；`test_registry.py:90` → `checks/injection_budget.py`；`TOOLS.md:579` → `infra/checks/injection_budget.py`（且 `cmd_check_injection_budget` 已补入函数清单，与 `registry.py` handler_path 一致） |
| **P3-1** | P3 | `extract_marked_block(display=…)` 死参数 | ✅ **已修复** | 形参已移除（`extract_marked_block(text, start_marker, end_marker, max_lines=None):286`）；`extract_persona_prefix_from_template(text, display="<text>"):305` **保留** display（该函数体内确有 WARN 输出 346-348）——区分正确 |
| **P3-2** | P3 | `tiers["resident"]` 裸索引 | ✅ **已修复** | 改为 `tiers.get("resident")` + 显式 issue（598-605）+ 返回结构 `(resident_tier or {}).get(...)`（615-616）；CLI 侧同改 `result["tiers"].get("resident") or {}`（756）。测试 `test_missing_resident_tier_policy_fails_closed_not_crashes:20324-20348`（pop 策略行 → issues 非空 / verdict FAIL / tokens 0 / CLI 打印 FAILED / finally 复原后回 PASS） |
| **P3-3** | P3 | `injection_budget_tier_gate()` 的 `hard` 默认无触发路径 | ❌ **未修复**（非阻断） | 实现仍在（`injection_budget_tier_gate:496-498` → `BUDGET_TIER_POLICY.get(tier, {}).get("gate", "hard")`），但 **tests 面 `tier_gate` 命中数 = 0**（实测）——R0 建议的 `injection_budget_tier_gate("unknown") == "hard"` 断言未补。Developer 披露"不修转跟踪"，但**该跟踪在决策面/风险面/plan-tracker 均无落点**（§四 F-3） |
| **P3-4** | P3 | `--format json` 丢弃 `issues` | ❌ **未修复**（非阻断） | 仍在（`cmd_check_injection_budget:743-744` 过滤 `k != "issues"`）；TOOL-055 亦未补"失败原因仅 text 面"的说明（`TOOLS.md:585` 只列 JSON 含 `sha256_16/tokenizer/verdict`）。同上无跟踪落点（§四 F-3） |
| **P3-5** | P3 | 反静默守卫断言为真阳性 | ✅ **已修复** | 改为 needle 拼接 `"skip"+"Test"+"("`（815）+ 全文件计数 1（816）+ **`_require_zstandard` 函数体归属断言**（818-822）；docstring 显式声明"不得拼出 needle，否则守卫会数到自己"（808-809）。实测 `skipTest(` 全文件仅 1 处 ✓ |
| **P3-6** | P3 | stale docstring（ASCII 臂 0.4 tok/char） | ✅ **已修复** | `test_token_estimate_ascii_matches_host_density:19980-19988` 改为"The ASCII arm … **IS the host rate**（`ceil(chars / 4)`）"；产品侧 `tokenizer_calibration.why` 亦已写明"the ASCII arm IS the host rate"（249-250） |
| **P3-7** | P3 | triage `files` 面与变更集不符 | ❌ **未修复**（Developer 披露"triage JSON 不回改"；coordinator 快速通道可直改） | 实测 `.governance/change-triage/FEAT-039.json:10-12` 仍**仅** `…/verify_workflow.py`；全仓 grep `injection_budget` 在 `.governance/change-triage/**` **0 命中** → 新 leaf / registry / TOOLS / 5 测试面 / 2 冻结面**仍未声明**。影响面（`check_conflicts:484-516` 以 `files` 为重叠输入）不变 |
| **P3-8** | P3（风险建议） | 出货态 advisory 不阻断 | ✅ **已由裁决承接**（DEC-210 + RISK-057） | `.governance/decision-log.md:151` DEC-210（选项 a 出货 + 翻 hard 时点=0.85.0 瘦身后）；`.governance/risk-log.md:53` RISK-057 打开（四条缓解）✓。**但见 §四 F-4：两处引用的基线数字仍是 R0 口径（4,763 / 5,133 / 5,134 / 20.6%），与 R1 重算值不一致** |
| **P3-9** | P3 | 面级 sha256 无基线锚 | ✅ **已修复** | `surface_content_hash`（210-221，`sha256[:16]`，空文本→`""`）；落 **surface 层** `rows[].sha256_16`（535）；表格新增 `Sha256[:16]` 列（647/654，未解析显示 `-`）；JSON 因整个 `result` 序列化而自动携带；`TOOLS.md:585` 已写明"漂移锚：等长改写不改变 token 数，指纹可检"；RISK-057 缓解④亦引用。测试 `test_per_surface_report_carries_bytes_cjk_and_both_prices:20428/20438-20440` 断言键存在 + `^[0-9a-f]{16}$` ✓ |

**计数（11 条总账，无重复计）：已修复 = 8 条**（P1-1、P2-1、P2-2、P3-1、P3-2、P3-5、P3-6、P3-9）；**由裁决承接 = 1 条**（P3-8 → DEC-210 + RISK-057，数字待刷新见 F-4）；**未修复 = 2 条**（P3-3、P3-4）。8 + 1 + 2 = 11 ✓。三条未闭合项（P3-3、P3-4、P3-7<sup>注</sup>）均 P3 级、均非阻断。

> 注：**P3-7 属"未修复但计入已闭合面"的披露项**——Developer 申报"triage JSON 不回改"（由 Coordinator 快速通道直改），故不计入"未修复缺陷"总数（2），但其 **机器落点缺失** 独立成为本轮 F-3。

---

## 三、本轮重点核验项（Coordinator 指定 6 项）

| # | 核验项 | 结论 |
|---|---|---|
| 1 | 裁决核验（docstring + 行域） | ✅ **三条依据全部成立**（§一），含超出要求的两条补强：`plan_entry_writes` 原样写入链、活体 22,857 B/272 行与 canonical 22,858 B 逐字节同源 |
| 2 | 委托实现核实 | ✅ 函数内 import（`canonical_entry_templates:366-374`），与 `checks/projection.py` 先例同构；**引擎 import 面仍 = 199**（`architecture-baseline.json:553` `import_count=199`，与 R0 一致，未增）；**引擎无新增 import 语句**（`verify_workflow.py:6870-6893` 的既有 import 名单未加项——委托发生在 leaf 内）。fail-closed 路径完整：ImportError → `{}`；`CanonicalSourceError` → `{}`；→ `load_injection_surface` 返回 `""` → `check_injection_budget` 记显式 issue（545-549）+ `resolved=False` + verdict FAIL |
| 3 | 行为变化合理性（canonical 损坏时全 entry 面 fail-closed） | ✅ **评估：收紧是安全的，且优于原语义**。原实现（R0 前）在"下一档标签缺失"时会把相邻档静默错切片（旧断言甚至接受 19KB standard 块充当 lightweight）——即**错误数据被当作有效度量**。新实现下权威不可解析 → **全部 entry 面**（entry-template + secondary-entry-template）→ `""` → 两个显式 issue + **FAIL**。代价（一次解析失败影响两面）被收益（绝不用错误文本定价、绝不静默）覆盖；且"全 entry 面同时不可解析"本身即强信号。**判定：合理收紧，弃权面为零**。唯一残余风险是 ImportError 分支的静默（§四 F-1，P3） |
| 4 | 逐条响应验证（11 条） | ✅ 完成（§二）；新引入检查见 §四 |
| 5 | 基线数字自验（canonical 口径） | ✅ 算术自验通过：`1,491 + 1,167 + 790 + 840 = 4,288`（persona + entry-template(lightweight) + secondary-thin + agent-instructions），`4,288 / 6,000` → 余量 `1,712 tok = 28.53%` PASS。字节侧本会话独立复算四块 = **3,904 / 22,858 / 23,484 / 2,724** 与申报逐位吻合；活体 standard 22,857 B 交叉印证。**注**：`9,953 / 10,154 / 55,214 / 8,573 tok` 无法在本轮独立复现（只读轮禁用执行），依赖 Developer 实测 —— 标 **未独立复现（非虚假：与 canonical 口径方向一致、且与我复算的字节面同源）**，Coordinator 复跑 pytest 时应一并核对 |
| 6 | AI 专项 5 项（本轮改动面） | ✅ 完成（§五） |

---

## 四、本轮新发现（**5 条**，全 P3，零阻断）

### F-1（P3）委托的 ImportError 降级分支静默且零覆盖 —— fail-closed 的唯一缺口

- **位置**：`checks/injection_budget.py:369-370`
  ```
  except ImportError:  # pragma: no cover - infra/ is always importable
      return {}
  ```
- **事实依据**：`sync_entry_projection` 在 `infra/` 根目录（非包），本 leaf 在 `checks/` 包内，函数内 import 依赖 `infra/` 在 `sys.path`。实测两侧共存（`infra/sync_entry_projection.py`、`infra/checks/injection_budget.py`），运行期入口（引擎/CLI）确实把它入 path，故**当前不可达**。
- **影响**：一旦该模块被移动/改名/包化（或 leaf 被以非 infra-root 入 path 的方式加载，如某些测试探针或第三方打包），`{}` 会让 **两个 entry 面同时变成 issue + FAIL**，但 issue 文案是"canonical source moved, was renamed, or an anchor broke"——**指不到真正原因**（import 失败 vs 源文件损坏），排障成本高。`pragma: no cover` 明确该分支永不进测试。
- **建议**（择一）：① 显式区分——`except ImportError as exc: return {}` 前 `print(f"  [WARN] sync_entry_projection unavailable: {exc}")`（`extract_persona_prefix_from_template` 已有同类 WARN 先例 346-348，风格一致）；② 或把 `ImportError` 并入 `CanonicalSourceError` 捕获并让调用方能区分来源。**非阻断**：当前路径不可达且失效方向安全（FAIL 而非静默 0）。

### F-2（P3）`extract_marked_block` 已成"仅供测试的私有边界实现"——与 R1 的"边界不重定义"原则相冲突

- **位置**：`injection_budget.py:270-302`（`_extract_marked_block_range` / `extract_marked_block`）；引擎再导出 `verify_workflow.py:6885`；测试 `test_verify_workflow.py:20184-20202`（2 个方法）
- **事实依据**（本轮 grep 全仓实测）：
  - `load_injection_surface` 的三条 scope 分支（395/397-398/399-410）**均不再经过** `extract_marked_block`：`full-file` 直返、`persona-prefix` 走 persona 解析器、`template-block` 走 `canonical_entry_templates`。
  - `extract_marked_block` 的**唯一调用点**是 `vw.extract_marked_block`（= 引擎再导出的同一对象）在两个测试方法中；二者断言的正是 **R0 口径的旧边界语义**：
    - `test_template_block_excludes_its_own_heading:20184-20192`（只断言"首行不含『注入模板』"）
    - `test_secondary_thin_is_not_inside_a_canonical_block:20194-20202`（断言"strict→thin 之间不含『次要平台入口薄指针』"）
  - 这两个 R0 的"边界测试"**在两轮之后仍全绿，却不覆盖生产切片路径**——R0 P1-1 漏检根因（有测试但测的是错边界）在结构上**仍然存在**，只是被 §二 P1-1 的三层新锁**另行覆盖**。
- **影响**：① 死码仍被引擎再导出，未来读者/新调用方有**误用风险**（若有人再次调用它定价，R0 缺陷会原样复现）；② 与 `ENTRY_TEMPLATE_MARKERS:73-77` 自述的"this table never re-defines a boundary"及模块 docstring ②（22-31）形成**同模块内的事实分叉**：模块禁止重定义边界，却保留了一套私有边界实现；③ 两个测试名（`…excludes_its_own_heading` / `…is_not_inside_a_canonical_block`）给人以"边界已被守护"的错觉，而真正守护者是新测试。
- **建议**（择一）：① 删除 `extract_marked_block` + `_extract_marked_block_range` + 引擎 import 项 + 2 个测试方法（以 §二 P1-1 的三层锁替代）；② 或保留但**显式降格**：docstring 加"LEGACY — not used by any resolution path; do NOT price with this（其端点为下一档标签行，会含尾随说明文字）"，并把 2 个测试改名为 `…legacy_helper…` 以消歧。**非阻断**：生产路径正确性已由 canonical 等值 + 字节钉 + 反向 needle 三重覆盖，且引擎 24,769 行 / import 199 冻结面下删除需同步 archguard 基线（故列 P3 而非 P2）。
- **注**：R0 曾把「P3-3 的 `hard` 分支无活体触发路径」列为同类问题；F-2 是**同一模式的新实例**，且严重度更低（P3-3 至少由 docstring 自述为契约默认；F-2 的语义已被模块自述否定）。

### F-3（P3）未修复项与"转跟踪"声明在机器可核面缺失 —— P3-3 / P3-4 / P3-7 无落点

- **事实依据**（只读 grep 实测）：
  - `.governance/decision-log.md` 仅 **DEC-205**（zstandard，既有）与 **DEC-210**（出货姿态）——**均未提 P3-3/P3-4/P3-7**；
  - `.governance/tpa-last-run.json` / `plan-tracker.md` 中 `FEAT-039` 行只有 1 条（Line 87，状态 `⏳ 待执行`），**无 P3-3/P3-4/P3-7 字段**；
  - `risk-log` 只有 RISK-057（回弹风险），**不含**这三条。
  - `.governance/change-triage/FEAT-039.json:10-12` 的 `files` 面仍只有 `verify_workflow.py`（P3-7 本体未修）。
- **影响**：Developer 申报的"不修转跟踪"在当前树内**不可机读**——即治理承诺缺少事实落点（与 P3-9 落地方式相反：P3-9 做到了代码+文档+测试+RISK 四处可核）。对 **P3-3/P3-4** 影响小（纯代码债），对 **P3-7** 影响实质：triage `files` 是 `check_conflicts`（`change_triage.py:484-516`）的**冲突检测输入**，未声明 = 未来并行任务（如 0.85.0 入口模板瘦身）若触及 `checks/injection_budget.py`，冲突检测漏面。R0 的降级前提也提到"triage files 是治理记录，Coordinator 快速通道可直改"，因此这更像**流程漏步**而非实现缺陷。
- **建议**：Coordinator 在机器记录 R1 结论时，把 P3-3/P3-4 落一条 DEC（或 plan-tracker 补一行）并直改 `FEAT-039.json` 的 `files` 面（含 `checks/injection_budget.py`、`registry.py`、`TOOLS.md`、5 个测试面、2 个冻结面）。**非阻断**。

### F-4（P3，**待核实/建议核实**）DEC-210 与 RISK-057 引用的基线数字仍是 R0 口径

- **位置**：`.governance/decision-log.md:151`（DEC-210）；`.governance/risk-log.md:53`（RISK-057）
- **事实依据**：DEC-210 正文写"lightweight resident **4,763**/6,000 有 **20.6%** 余量"、"standard/strict 入口模板单项超限（**R1 返工后 5,133/5,134 tok**）"；RISK-057 写"lightweight resident **4,763**/6,000（余量 **20.6%**）"。
- **对照**：① **4,763 / 20.6%** 是 R0 口径（R0 §二实跑 `resident_tok 4763`）；R1 申报 **4,288 / 28.5%**。② **5,133/5,134** 出自 R0 §五 P1-1 表格的"实际注入块"列（17,219 B / 5,133 tok、17,220 B / 5,134 tok）——即**被裁决推翻的那一列**。DEC-210 自身论证"现在翻 hard 会用错误数字（R0 度量夸大 29%）"，却把该错误列的 token 值当作 R1 后的超限幅度引用——**内部自相矛盾**。③ 我复算的 canonical 超限幅度应约为 3,953/4,154 tok（申报值，本轮未独立复现）。
- **影响**：决策/风险记录是**审计轨迹**；数字陈旧会使后续读者（含 0.85.0 瘦身排期者）按错误基线定目标（例如把"削 5,133"当靶子）。**不改变决策方向**（advisory 出货与翻 hard 时点结论仍由"lightweight 有余量 + standard/strict 超限"支撑，该事实在两种口径下都成立）。
- **建议**：Coordinator 于 R1 写回时同步刷新 DEC-210/RISK-057 的三处数字为 canonical 口径（4,288/28.5%；standard/strict 约 3,953/4,154 —— 以 Coordinator 复跑实测为准），并在 DEC-210 补一句"R1 canonical 口径已替换 R0 口径引用"。**非阻断（治理记录面）**。
- **声明**：我对 9,953/10,154/55,214/8,573 无独立复现手段（只读轮），故本条以"**引用口径不一致**"为确定事实，"新数值本身"采信 R1 申报并**待 Coordinator 复跑确认**。不得读作"新数字已独立验证"。

---

## 五、五维度结论 + AI 专项

### 维度 1：正确性 —— **通过**

- ✓ **委托后的边界正确性**：canonical 等值断言逐 profile 成立；字节钉 `{3904,22858,23484,2724}` 与本会话独立复算**逐位吻合**；反向 needle（不含下一档标签 / `### Step 8` / thin 后规格说明）覆盖 R0 指出的两类越界（前向与尾随）。
- ✓ **fail-closed 语义收紧**：五条错误路径（源缺失/读失败/锚点缺失或歧义/权威不可解析/未知 scope）全部落 `""` → 显式 issue + FAIL；`""` 必产生 issue（529-532 / 545-549）**无静默记 0**。`tiers.get("resident")` 补口后，"三级 fail-closed"契约在索引面亦成立。
- ✓ **tokenizer 数学**（未改，R0 已验证）：`tokens ≥ tokens_host` 恒成立；本轮未引入回归（`estimate_surface_tokens` 224-236 与 R0 同）。
- ✓ **两行口径的裁决一致性**：`verdict` 由 `gated_over_budget_tiers` 独决（578-581 / 607-608），渲染层（664-670）、CLI 层（755-769）、Check 33 层（同一函数）三处同源，**读者可区分"度量超标"与"门控超标"**。
- ⚠ **F-1/F-2**（P3，见 §四）。

### 维度 2：安全性 —— **通过**

- ✓ 无外部输入注入面：`re.escape` 用于常量拼接（446-447）；个人数据/密钥零；无 `eval/exec/subprocess`；leaf 只读（不写文件/不写 `.governance/`/不执行 git）。
- ✓ 路径解析固定 `__file__.parents[4]`（66），不取 cwd。
- ✓ 新增 `hashlib` 在引擎 import 面内（`verify_workflow.py:28` 已 `import hashlib`），**不引入新依赖**，与 `test_registry.py:106-108` 的"stdlib-only"声明不矛盾。
- ✓ 委托路径无循环依赖：`sync_entry_projection` 不 import 本 leaf；本 leaf 仅在其函数体内按需 import（首次调用时 `sys.modules` 缓存）。

### 维度 3：可维护性 —— **通过（附 P3）**

- ✓ 文件/函数持有清晰职责；773 行中 docstring/注释占比仍高（非过度实现）；函数长度分布未恶化（`check_injection_budget` 仍 ~115 行，含数据装配）。
- ✓ 注释与实现一致（本轮 P3-6/P2-2 修好后）；`ENTRY_TEMPLATE_MARKERS` 与模块 docstring ② 的"不重定义边界"自述一致。
- ⚠ **F-2**：同模块内仍存在一套**不被任何解析路径使用**的私有边界实现（引擎再导出），与上述自述分叉。
- ⚠ **F-3**：未修复项无机器落点。

### 维度 4：性能 —— **通过（附 P3）**

- ✓ 纯线性、无嵌套循环、无 I/O 循环、无大对象常驻；`set_injection_budget_surface_profiles` 浅拷贝语义未变（并发 `--profile` 不串味）。
- ⚠ **F-5（新，P3）**：`load_injection_surface` 的 template-block 分支对同一 `commands/governance-init.md` 每面各读一次全文（约 39 KB）并各跑一次全文 `extract_canonical_templates`（`finditer` + 每块 `finditer`），且 `check_injection_budget` 对同一 profile 会连续解析两次 `canonical_entry_templates(text)`（entry-template 与 secondary-entry-template 各一次）——单次测量约 4 次全文解析（`find_marker_line` 两次文本切分 + 两次权威提取）。**当前 6 面 / 39 KB 规模下无实害**（毫秒级），但 `check-governance` 每次聚合都会跑，且入口源会随版本增长。建议：按文本内容在 `canonical_entry_templates` 内加 `functools.lru_cache` 或一次性提取后传参。**非阻断（纯效率）**。

### 维度 5：测试覆盖 —— **通过**

- ✓ 本轮新增/改写 3 条正向精度测试（canonical 等值 + 字节钉 + 反向 needle）+ 1 条渲染口径测试（两行 gated/report-only + CLI 同口径）+ 1 条 fail-closed 索引测试（pop resident）+ P3-5 的归属断言 + P3-9 的 hash 格式断言。**R0 P1-1 明确的"漏检根因"（有测试但不覆盖尾随越界）已被反向 needle 直接闭合。**
- ✓ 计数核实（本会话只读实测）：`Feat039InjectionBudgetTests` = **31** 个 test 方法（与申报 31/31 一致）；`Feat039ZstandardDependencyAssertionTests` = **3** 个。
- ✓ 反向路径覆盖：源缺失（temp root → 全 missing/FAIL）、锚点缺失、锚点重复（find_marker_line 双命中 raise）、persona 锚点/首句破坏、tier 策略行缺失、`--fail-on-issues` → `SystemExit(1)`（本轮已由 P3-4 相关的**显式断言**补强，R0 的"ADVISORY exit 0 无显式断言"缺口在 `:20508-20515` 与 `:20520-20528` 已有正/反两侧断言）。
- ⚠ 覆盖率报告仍未附（code-review SKILL 要求 standard ≥70%）→ 该项仍标**不可验证**（非阻断，理由同 R0：新增面正/反向用例对完整；且本轮已把重点缺口补成断言）。
- ⚠ **F-2**：2 个旧测试仍钉住不被使用的旧边界助手；生产路径守护由新测试承担（叠加覆盖，非缺口，但**测试名易误导**）。

### AI 专项 5 项（本轮改动面）

| # | 项 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock/硬编码残留 | **无** | 字节钉 3,904/22,858/23,484/2,724 是**权威输出物化断言**（测试文件常量 + 注释指向 authority + 同测试内等值断言），非产品代码硬编码；产品侧无 mock、无残留 |
| 2 | 硬编码返回值 | **无** | 全部数值来自文件解析；`TOOL_RETURN_BUDGET_EXPECTED=8192` 为契约断言值并带漂移反相测试（沿用 R0 判定） |
| 3 | 幻觉 API | **无** | 新增 import 仅 `sync_entry_projection.{CanonicalSourceError, extract_canonical_templates}`——**两者均在该模块中实际存在**（`:70`、`:84`）且签名匹配（`extract_canonical_templates(text: str) -> dict[str,str]`，本 leaf 传 str、取 `.get(profile)`）✓ |
| 4 | 未实现 TODO | **无** | grep `TODO/FIXME/XXX/HACK` 在改动面 0 命中；声明能力（委托/fail-closed/两行口径/hash/索引安全）逐项在代码+测试中找到实现 |
| 5 | 过度实现 | **否** | 本轮为**净收敛**（删除 `_next_template_marker`/`ENTRY_TEMPLATE_MAX_GAP`/`_after`/`display` 形参，新增 1 个 23 行委托函数 + 若干断言）；未引入抽象层。**唯一"多余"是 F-2 的死码助手**（R0 遗留，非本轮新增） |

---

## 六、硬门槛裁决

| 门槛项 | 阈值 | 实测 | 判定 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **0** | ✓ |
| 5 维度全覆盖 | = 100% | 5/5 有结论（§五） | ✓ |
| 每条发现标注级别 | = 100% | 16 条（R0 清单 11 条 + 本轮新增 F-1~F-5 共 5 条）全部带 P0~P3 | ✓ |
| 设计一致性检查 | 已完成 | 逐项比对 R0 裁决 + canonical 权威 + AUDIT-154 §8 + triage + 冻结面（§一/§二/§三） | ✓ |
| AI 代码专项 5 项 | 全部完成 | 5/5（§五） | ✓ |

**结论：APPROVED_WITH_NOTES**
- **`unresolved_blockers=0`**
- 通过依据：R0 唯一 BLOCKING（P1-1）**已修复且经三重独立核验**；P2 全部闭合；未闭合 2 条缺陷（P3-3/P3-4）+ 1 条披露承接项（P3-7）均 P3 级、均已被 R0 认定"非阻断/可遗留/可快速通道"，且**无未解决 BLOCKING**。
- 备注项（建议随 R1 写回一并处置，均不阻断合并）：**F-3**（补 P3-3/P3-4 决策落点 + 直改 triage `files` 面）、**F-4**（刷新 DEC-210/RISK-057 的 R0 口径数字）、**F-2**（旧边界助手降格或删除）、**F-1**（ImportError 分支加 WARN）、**F-5**（入口源解析缓存）——可合并入 0.85.0 入口模板瘦身任务或单列 P3 跟踪。
- 复审链状态：本轮为**终态**（APPROVED_WITH_NOTES），无需第 2 轮复审；Coordinator 按 M7.4 走 review-record 机录。

---

## 七、申报事实逐项核实（Developer R1 申报）

| 申报 | 核实结论 |
|---|---|
| **P1-1**：委托权威 `extract_canonical_templates`；函数内 import（同 `checks/projection.py` 先例）；标签仅作歧义锚；权威不可解析→`""`；删私有边界机制 | ✅ **全部成立**。委托实现 352-374；`ENTRY_TEMPLATE_MARKERS` 注释明示仅锚 73-83；`""` 路径完整；`_next_template_marker`/`ENTRY_TEMPLATE_MAX_GAP`/`_after` grep **0 命中**。⚠ 但 `extract_marked_block`/`_extract_marked_block_range` **未删**（不在申报清单内，属未尽收敛 → F-2） |
| **P1-1**：引擎 import 面 199 不变 | ✅ `architecture-baseline.json:553 import_count=199`；引擎无新增 import 语句（6870-6893 名单未加项） |
| **P1-1 行为变化**：canonical 损坏 → 全 entry 面 fail-closed（原相邻档静默错切片） | ✅ 成立且**安全**（§三-3）；旧断言"接受 19KB standard 块当 lightweight"的行为在新测试下已不可能 |
| **P1-1**：新测试（canonical 等值 + 字节钉 + 反向 needle） | ✅ 三条全在（20226/20219/20248），断言内容与申报一致 |
| **P1-1**：字节钉 3,904/22,858/23,484/2,724 | ✅ **本会话独立复算逐位吻合**；活体 standard 22,857 B/272 行交叉印证 |
| **P2-1**：报告两行口径 + 逐层 gate 前缀 note + CLI/Check 33 改 gated；删"resident ≤ budget"必假断言 | ✅ 全部成立（664-673 / 761-769 / 686-694）；`test_report_separates_gated_from_report_only_over_budget` 在位（20298-20322）。"resident ≤ budget"（R0 的 `20195` 语义）已被改写为基于同源测量的 `resident["tokens"] - 1` 强制非 PASS（20294-20296），**非假断言** |
| **P2-2**：3 处归属注释反转 | ✅ 3/3 已改（`test_contract_matrix.py:69`、`test_registry.py:90`、`TOOLS.md:579`） |
| **P3-1**：display 死参数删除 | ✅ 已删（286），persona 解析器的 display 保留（305，有 WARN 用途） |
| **P3-2**：resident 裸索引→get+fail-closed（测试：pop→无 KeyError/issues 非空/verdict FAIL） | ✅ 已改（598-605/615-616/756）+ 测试 20324-20348 三条断言齐备 |
| **P3-5**：needle 拼接 + 函数体归属断言 + docstring 去自匹配 | ✅ 三处全在（815-822 / 808-809）；`skipTest(` 全文件计数实测 = 1 |
| **P3-6**：stale docstring 修正 | ✅ 已改（19982-19987）+ 产品侧 calibration 文案同步（249-250） |
| **P3-7**：11 文件面披露（triage JSON 不回改） | ⚠ **披露成立但文件未改**：`FEAT-039.json:10-12` 仍只列 `verify_workflow.py`；"披露"目前仅存在于申报文本中，**无机器落点** → F-3 |
| **P3-9**：sha256_16 落 surface 层（表格列 + JSON + TOOLS.md；tiers 层不加） | ✅ 四点全对：`rows[].sha256_16`(535) / 表格列(647,654) / JSON 自动携带 / `TOOLS.md:585` 说明；`tiers` 层确未加（551-566 无 hash 字段）——与申报一致 |
| **P3-3/P3-4**：不修转跟踪（DEC-210 advisory 出货） | ⚠ **DEC-210 是"出货姿态"决策，不构成对 P3-3/P3-4 的遗留登记**；全治理文件 grep 无这两点的落点 → F-3。P3-3 的 `hard` 默认仍无测试（tests 内 `tier_gate` 命中 0）——如 Coordinator 接受"转跟踪"，需补落点 |
| **基线重算**：lightweight resident 4,288/6,000（余量 28.5% PASS） | ✅ **算术自验通过**（1,491+1,167+790+840=4,288；余量 1,712/6,000 = 28.53%）；面级数字未独立复现（只读轮） |
| **基线重算**：standard 9,953 / strict 10,154 ADVISORY（超 3,953/4,154） | ⚠ **未独立复现**（只读轮禁执行）；方向与 canonical 口径一致（22,858/23,484 B 远大于 lightweight 3,904 B，超 6K 必然成立）；数值待 Coordinator 复跑核对 → F-4 关联 |
| **基线重算**：全域 55,214B；entry-skill 8,573 tok 成为最大单面 | ⚠ 同上（未独立复现）。合理性旁证：测试 `test_dynamic_tiers_are_measured_but_never_added_to_resident:20388-20392` 断言 `resident < resident + skill` 且 `grand_total > resident`，与"entry-skill 为最大单面"相容 |
| **测试**：全量 3,372 passed/30 既有失败/1 skipped；定向 Feat039 31/31 + governance_cost 40/40 + registry/contract 104/104 + entry_projection/archguard 70/70 | ⚠ **未独立复现**（只读轮）。**类计数已核实**：Feat039 方法 **31** ✓、`test_governance_cost` 全文件 **40** 个 test 方法 ✓（数列线 135-773 共 40 个 `def test_`）。30 既有失败（replay 6 + WSL 24）为本轮未含面，**不在本次判定范围** |
| **冻结面零漂移**：引擎 24,769=anchor；CLI 88 / segment 71 / import 199 / print 1304 | ✅ 四条中三条实测通过：`architecture-baseline.json:17 anchor_loc=24769` 且引擎实际 **24,769** 行 ✓；`:553 import_count=199` ✓；`:541 total=1304` ✓；88/71 由 `test_contract_matrix.py:73-74` 与 `test_registry.py:94-95` 静态声明 ✓（与 R0 实测一致） |

---

## 八、审查边界声明

- 本审查为**只读**：未修改任何产品代码、未运行完整测试套件、未执行任何写操作。所有 pwsh 调用均为字节/行域/行数**读取**（`ReadAllText` + 正则 + 计数），未落盘、未改文件。
- 度量采用**自建独立提取器**（不调用待审代码）：按 `sync_entry_projection` 公布的规则（标签消费开围栏；闭合围栏 = 切片内最后一个裸围栏；末块受 `### Step` 约束）复算，并额外实现 R0 的"首个围栏"口径以复现两套数字——两套结果分别与 R0 表列、R1 申报对照。
- **未独立复现的项**（已在 §三-5、§七显式标注，未写成已通过）：token 面（`4,288/9,953/10,154/55,214/8,573`）、测试套件结果（3,372 passed / 30 既有失败 / 各定向组计数——除已核实的类方法计数）、`check-governance`/`archguard-ratchet`/contract-matrix 全套运行结果。这些依赖 Coordinator 复跑。
- 覆盖率报告未附 → 维度 5 该项标 **不可验证**。
- 依据 Coordinator 裁决，R1 **未**按 R0 的 17,219/17,220/2,739 B 判定 P1-1，改按 canonical 口径（3,904/22,858/23,484/2,724 B）验收；裁决三条依据已逐条独立核验成立（§一）。
- 报告路径：按 Coordinator 派发指令写入 `docs/reviews/review-FEAT-039-CODE-R1.md`（与 R0 同目录）。`agents/code-reviewer.md:105` 另载"`.governance/review-{task_id}.md`"——本仓库既有惯例为机器记录落 `.governance/review-FEAT-039-R0.md` + 详细报告落 `docs/reviews/`，如 Coordinator 需要详细报告副本入 `.governance/`，请指示（本轮未越权写第二份）。
