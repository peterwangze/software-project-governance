# Code Review — FEAT-039-CODE-R0（round 0）

| 项 | 值 |
|---|---|
| 任务 | FEAT-039 — 注入/工具返回/生成预算 CI（AUDIT-154 切片 A-8） |
| 类型 | 代码审查（Code Reviewer / code-review SKILL） |
| round | **R0**（首轮，无前轮引用） |
| 审查面 | 工作树未提交变更集（FEAT-039 净增）；FEAT-038 文件面已另行提交 697689d，按内容面区分跳过 |
| 审查方法 | 只读：Read/Grep/Glob + pwsh 只读执行（度量复现）；未修改任何产品代码 |
| 结论 | **NEEDS_CHANGE** |

---

## 一、结论行

> **NEEDS_CHANGE**
> P0 = 0 / **P1 = 1** / P2 = 2 / P3 = 6
> `unresolved_blockers` = 1（P1-1；P2-1/P2-2 计数见 §五）
> 硬门槛：P0=0 ✓ · 5 维度全覆盖 ✓ · 每条发现带 P0~P3 ✓ · 设计一致性 **部分**（见 §四）· AI 专项 5 项完成 ✓
> **不得合并**（P0=0 但 P1=1；按 code-review SKILL 第四步：P0=0 且 P1=0 才合并）。

**P1-1 是本轮阻断项**：注入面体积门禁的**入口模板度量口径含 5.6KB / 6.3KB 非注入文本**，直接扭曲本任务唯一交付的价值（"实际加载集合"的定价数字）。

---

## 二、审查对象与证据基座

| 变更面 | 路径 | 核验 |
|---|---|---|
| 核心新增 leaf | `skills/software-project-governance/infra/checks/injection_budget.py`（733 行） | 全文逐行读（1-733） |
| 引擎接线 | `infra/verify_workflow.py`（FEAT-039 段 6848-6904 / Check 33 分项 16332-16366 / subparser 24059-24067 / dispatch 24713） | 4 处逐段读 |
| 注册面 | `infra/registry.py`（LOADER_WHITELIST 191-194；COMMAND_SPECS 288-294） | 读 |
| 文档面 | `infra/TOOLS.md`（总览行 60 / 详情节 577-591） | 读 |
| 测试面 | `test_verify_workflow.py::Feat039InjectionBudgetTests`（19962-20434）；`test_governance_cost.py::Feat039ZstandardDependencyAssertionTests`（777-818）；`test_registry.py`（89-110/309-311/343-366/550-562）；`test_contract_matrix.py`（68-74）；`test_archguard_ratchet.py`（67-76） | 读 |
| 冻结面 | `infra/contract_matrix/snapshots.json`（key_count=88, 168-258）；`core/architecture-baseline.json`（anchor_loc=24769 / total=1304 / import_count=199） | 读 |
| 需求面 | `docs/requirements/governance-bootstrap-cost-audit-0.84.0.md`（§5.3/§7/§8 L185）；`.governance/change-triage/FEAT-039.json` | 读 |

**度量复现（pwsh 只读执行，本会话实跑）**：

```
profile lightweight resident_tok 4763 (host 2514) grand 16737 verdict PASS issues 0 over=['skill'] gated=[]
profile standard    resident_tok 10428 (host 5181) grand 22402 verdict ADVISORY issues 0 over=['resident','skill'] gated=['resident']
profile strict      resident_tok 10629 (host 5245) grand 22603 verdict ADVISORY issues 0 over=['resident','skill'] gated=['resident']
tool_return {'max_json_bytes': 8192, 'enforced': True, 'issues': []}
```

---

## 三、五维度审查结论

### 维度 1：正确性 — **有 P1/P2 发现**（详见 §五）

- ✓ **tokenizer 不低估性数学成立**：`tokens ≥ tokens_host` 恒成立，三档字符类逐项验证
  `Σᵢceil(nᵢ/4) ≤ ceil(Σᵢnᵢ/4)` 与 `ceil(2n/5) ≥ ceil(n/4)`（n≥0）均成立；CJK 1 tok/字 ≥ 0.25 tok/字。
  空串、单调性、跨脚本 5 例均被测钉住（19996-20035）。
- ✓ **fail-closed 解析路径无静默记 0**：文件缺失 / 读失败 / 锚点缺失或歧义 / 切片异常 / 未知 scope 全部返回 `""`
  （`load_injection_surface` 359-395；`find_marker_line` 245-248 双命中即 raise）；`""` 必产生显式 issue（529-532）且 `verdict=FAIL`。
  实跑空 root → `missing=6 / tokens=0 / verdict=FAIL`。
- ✗ **P1-1**：入口模板切片越界（含非注入文本），见 §五。
- ✗ **P2-1**：`over_budget_tiers` 与裁决口径错位，见 §五。
- ⚠ **P3-2**：`tiers["resident"]` 裸索引（589-590），`BUDGET_TIER_POLICY` 改名即 `KeyError`。
- ⚠ **P3-3**：`injection_budget_tier_gate()` 的 `hard` 默认值在本任务无触发路径（测试靠裸改 dict 断言，非经该函数）。

### 维度 2：安全性 — **通过**

- ✓ 无外部输入注入面：`re.escape` 用于常量拼接（431/444），无用户输入进 regex；无 `eval/exec/subprocess/os.environ/open(`（grep 实测仅 4 个 stdlib import）。
- ✓ 无敏感数据硬编码；`sys.stdout.reconfigure` 有 `AttributeError/OSError` 兜底（690-692）。
- ✓ 只读：不写文件、不写 `.governance/`、不执行 git（与 TOOL-055 边界声明一致）。
- ✓ 路径解析固定 `__file__.parents[4]`，不取 cwd，无路径穿越。

### 维度 3：可维护性 — **通过（附 P2/P3）**

- ✓ 职责单一：度量+渲染 leaf，引擎仅 dispatch（`_run_full_engine_checks` +583→ 实测 print 面只增 Check 33 一处）。
- ✓ 命名表达意图、注释与代码一致（唯一例外见 P3-6）。
- ✓ 733 行中约 47% 为 docstring/注释（非过度实现，见 §六 AI 专项）。
- ✗ **P2-2**：3 处 provenance 注释把 handler 归属写成 `verify_workflow.py`。
- ⚠ **P3-1**：`extract_marked_block(..., display=...)` 参数在函数体内未使用（268-285；两个调用点 20168/20179 仍传参）。

### 维度 4：性能 — **通过**

- ✓ 纯线性：每面一次读文件 + O(n) 扫描；无嵌套循环、无 N+1、无 I/O 循环；`splitlines` 复用。
- ✓ 无大对象常驻；`set_injection_budget_surface_profiles` 返回浅拷贝 tuple，不改模块表（并发 `--profile` 不串味，452-464）。
- ✓ 6 面全量测量为单文件级读取，无排序热点。

### 维度 5：测试覆盖 — **通过**（23 个新测试 + 3 个 zstandard 断言）

正/反向路径覆盖矩阵（实测计数）：

| 面 | 正向 | 反向（fail-closed / 漂移） |
|---|---|---|
| tokenizer | ASCII 同率 / CJK 高于 host / 空 / 单调 | 跨脚本 `tokens ≥ host` 不变量（19996） |
| persona 解析 | 活体可解析、与整文件相异（20051） | 锚点改名（20068）/ body 首句篡改（20094）→ `""` |
| 入口模板切片 | 三 profile + secondary-thin 可解析 | 丢 marker（20124）→ `""`，同树他面不受影响 |
| 面声明 | profile_candidates 声明面（20149） | — |
| 预算裁决 | 活体 resident ≤ 6K 且 PASS（20195） | budget-1 立即非 PASS（20213）；硬档 flip → FAIL（20233） |
| 分层 | skill/command 计量但**不并入** resident（20246） | report-only 永不 gate（20264） |
| 面解析失败 | — | 空 root → 全 missing + FAIL（20312） |
| tool-return | 8192 + enforcer 在场（20324） | 漂移 999999 → issue（20339-20347） |
| CLI | text 表 / ADVISORY exit 0 / JSON 可解析 | `--fail-on-issues` + 解析失败 → `SystemExit(1)`（20385） |
| Check 33 内联 | 段内出表且 verdict 单行（20408） | — |
| registry | `handler_path` = `checks.injection_budget.cmd_check_injection_budget`（20421） | — |

覆盖率口径：`code-review` SKILL 要求 standard ≥70%——本变更未附覆盖率报告，**判定为不可验证**（非阻断：新增面以正向+反向用例对覆盖，且核心分支均有用例；`--format json` 的 issues 字段缺失无断言见 P3-4）。

---

## 四、设计一致性（triage / AUDIT-154 §8 acceptance）

| 验收项 | 判定 | 证据 |
|---|---|---|
| 分项体积 + PASS/FAIL 可参数化（triage） | **部分** | 分项表 ✓（`format_budget_report` 611-629，实跑输出 6 面 bytes/chars/CJK/tok/host/status）；PASS/FAIL 可参数化 ✓（`BUDGET_TIER_POLICY` 数据面 + `test_budget_tier_is_not_a_hard_fail_while_advisory` 钉住 flip 行为）——**但切片 A 出货态 resident=advisory，默认永不阻断**（见 §七 R-1） |
| 基线不超 6K | ✓ | lightweight resident = **4,763** ≤ 6,000（实跑）；per-surface `budget_tokens` 字段回填 |
| zstandard 断言 | ✓ | 3 测试：硬 FAIL 带 `pip install zstandard`（791-798）/ 反静默守卫（800-810，`skipTest` 调用点计数=1 且唯一触发源为 import 探针）/ fail-closed 文案（812-818 对照 `governance_cost.py:106-108`） |
| 零回归（既有命令 / 锚点面不变） | ✓ | `INJECTION_CONTRACT_ANCHORS` 仍 3 文件 23 锚点（6678-6706 实测计数 14+8+1=23）；Check 33 段 id 与 registry `("33", "verify_workflow.check_injection_contract")` 未动；segment 面 71 键不变（snapshots `check_segments` + FROZEN_SEGMENTS=71） |
| AUDIT-154 §8 L185「静态注入 ≤6K tok 守护 **FAIL**」 | **部分** | 守护机制在位但 resident 档 = advisory（输出 FAIL 分项、exit 0）。见 §七 R-1 |
| 口径独立性（与 `check-injection-contract` 单一职责分离） | ✓ | 锚点存在性 3 文件/23 锚点未变；体积面独立函数、独立 CLI 键、独立 registry 行；Check 33 内**双信息零新增 segment id**（registry 71 段声明核实） |
| 口径选择（persona prefix 块标量 / canonical 模板 / 多文件求和） | ✓ | persona：锚点链 `@deepseek-ai/dsh-persona` + `config:` + 首句，实测取到 5,031B（整文件 272 行的 YAML 配置与注释未计入）；canonical：`governance-init.md` Step 7 模板，非工作区入口文件（活体 CLAUDE.md 22,835B 不入门禁）；多文件求和：resident = 4 面求和，拆分文件不能绕过（面声明即实际加载集合） |
| 架构合规（R1/R4/R6） | ✓ | `architecture-baseline.json`：`anchor_loc=24769` = 引擎实测 24,769 行；`r4_print_orchestration.total=1304`（`cmd_check_injection_budget` **不在** per_function 表中——handler 在 leaf，引擎仅 1 个 verdict print site）；`r6.import_count=199`；`LOADER_WHITELIST` 含 `checks.injection_budget`（21 项） |
| 基线数据诚实性（AUDIT-154 ~110KB → 56.8KB） | ✓（口径需注明） | 六面全域 bytes 实跑 **56,826B**（16,204 + 29,030 + 11,592）= 申报 56.8KB ✓；但 `-48%` 相对 AUDIT-154 §2「交互前注入+读取 ~110KB 治理材料」——**分子分母口径不同**（110KB 含"读取"的 plan-tracker/命令面，56.8KB 仅测量注入面），-48% 不宜作为等价对照结论 |
| 并发耦合归属（038/039 同树） | ✓ | 按内容面区分：039 = FEAT-039 段 6848-6904 / Check 33 分项 16352-16363 / subparser 24062-24067 / dispatch 24713；038 的归属改指与 snippet 修复面未纳入本轮判定（已在 697689d 披露） |

> 注：全域总和 = 16,204（resident）+ 29,030（skill）+ 11,592（command）= **56,826B**，与申报 56.8KB 吻合（逐面值见 §二实跑输出）。

---

## 五、发现清单（每条带级别、位置、依据、影响、建议）

### P1-1（阻断）入口模板切片越界——resident 度量含 5.6KB / 6.3KB 非注入文本

- **位置**：`skills/software-project-governance/infra/checks/injection_budget.py:252-265`（`_extract_marked_block_range`）、`:393-394`（`load_injection_surface` 的 template-block 分支）、`:335-356`（`_next_template_marker`）
- **事实依据**（pwsh 只读实跑，同一脚本内对照）：

  | profile | resolver 报出 | 实际注入块（markdown 围栏内，去缩进） | 夸大量 |
  |---|---|---|---|
  | lightweight | 3,919 B / 1,171 tok | 3,919 B / 1,171 tok | 0（探针行同时是注入首行） |
  | standard | 22,874 B / 6,836 tok | **17,219 B / 5,133 tok** | **5,655 B / 1,703 tok** |
  | strict | 23,500 B / 7,037 tok | **17,220 B / 5,134 tok** | **6,280 B / 1,903 tok** |
  | secondary-thin | 4,321 B / 1,261 tok | **2,739 B / 793 tok** | **1,582 B / 468 tok** |

- **机理**：切片上界 = `lines[start:end-1]`，`end` 是**下一个模板的探针行行号**，因此中段模板的切片把
  `commands/governance-init.md:442-535`（standard 之后）与 `:719-833`（strict 之后）这两段
  **模板规格说明文字**（`**双入口去重（FEAT-037……）**` 及其 bullet）计入了注入面。
  secondary-thin 额外把 `:869-876` 的同段说明计入。取证：围栏行分布 `(194 open / 258 close)`、`(261 open / 441 close)`、`(537 open / 718 close)`、`(835 open / 868 close)`。
- **影响**：
  1. 本任务唯一交付价值 = "对**实际加载集合**定价"（模块 docstring `:1-7`、TOOL-055:「实际加载集合（多文件求和……）」）——standard/strict 的 resident 数字被夸大 **~29-30%**，超出预算的幅度被虚报；报告对读者是错误陈述。
  2. 漂移检测锚随之失真：基线表把模板规格文字的体积当作注入体积。
  3. 次要：`secondary-thin` 的 canonical 预算 `≤3072 字节 / ≤40 行`（`commands/governance-init.md:871`，由 FEAT-037 的 `check-entry-bootstrap-sync` 守护）在**实际注入块 2,739B / 33 行**下成立（11% 余量）；而门禁报 **4,321B / 41 行**——若不改口径，未来该探针会被误读为超 3KB。
- **修复建议**（改上界，不改总量语义）：
  1. template-block 分支按**本模板 markdown 围栏**收口——`_extract_marked_block_range` 增加可选 `stop_at_fence="```"` 语义：遇到首个与起始同列（或任意）的闭合围栏即终止；或
  2. 在 `_next_template_marker` 之外增加"下界回缩"：从 `end-1` 起向上跳过空行与 `**…注入模板**` 探针行、未闭合前的说明段；或
  3. 最小改动：把 `end` 限定为**本模板围栏闭合行 +1**（`INJECTION_BUDGET_SURFACES` 增 `block_fence` 声明），未找到围栏 → fail-closed 返回 `""`。
  4. 补一条**正向精确性**测试：断言 `entry-template` 面的文本不含 `双入口去重`、`Step 8`、`注入模板**（` 等规格文字（现有 `test_template_block_excludes_its_own_heading` 只断言首行、`test_secondary_thin_is_not_inside_a_canonical_block` 只断言跨档不重复——**都不覆盖尾随越界**，这是漏检根因）。
  5. 更新后重跑并同步基线数字与 TOOL-055/§四表格中的引用值。

### P2-1 `over_budget_tiers` 与裁决口径错位（报告行标注错误）

- **位置**：`injection_budget.py:593-594`（两个字段并存）→ `:632-635`（渲染用 `over_budget_tiers`）、`:717-729`（CLI ADVISORY 分支）、`verify_workflow.py:16357-16360`（Check 33 ADVISORY 行）
- **事实依据**：裁决由 `gated_over_budget_tiers` 决定（`:557-564/581-582`），但三处**对外文案**都打印 `over_budget_tiers`。
- **影响**：ADVISORY 行的"over-budget tiers: X"会把 **report-only 档**（对裁决无影响）与门控档混为一谈。活体 lightweight 实跑即为该形态：`verdict=PASS / over_budget_tiers=['skill'] / gated=[]`——`skill` 档超 2,573 tok，而 `entry-skill` 面 `status=over` 会打印在表格里，读者无法从输出区分"测量超标"与"门控超标"。JSON 消费者拿到两个字段更易误用。
- **建议**：三处文案改用 `gated_over_budget_tiers`（或分列"gated: …，report-only: …"）；`format_budget_report` 对 report-only 行的 `status` 用 `over(report-only)` 限定词；补一条断言（当前仅断言 `gated_over_budget_tiers == []`，无对 `over_budget_tiers` 的渲染断言）。

### P2-2 handler 归属注释与实现相反（3 处）

- **位置 / 事实**：
  - `test_contract_matrix.py:68-69` —「FEAT-039 …；handler in `verify_workflow.py`」 → 实为 `checks.injection_budget.cmd_check_injection_budget`
  - `test_registry.py:89-90` —「handler lives in `verify_workflow.py`」 → 同上
  - `TOOLS.md:579` —「**文件**：`infra/verify_workflow.py`（`check_injection_budget` / `load_injection_surface` / `estimate_surface_tokens`…）」 → 三函数全在 leaf
  - **对照**：`registry.py:290-294`（`checks.injection_budget.cmd_check_injection_budget`）、`test_registry.py:351-356`（「handler lives in `checks/injection_budget.py`」）、`architecture-baseline.json`（`cmd_check_injection_budget` 不在引擎 per_function 表）——三处权威面均与上述注释相反。
- **影响**：FROZEN 计数注释是契约变更的**审计轨迹**（`test_contract_matrix.py:50-74` 逐版本记录 `--regen` 事件）；同文件 `:68-74` 同时存在正确表述（「rides INSIDE check segment 33」），同一段自相矛盾。后续审查者按注释找文件会失败。
- **建议**：三处改为 `checks/injection_budget.py`，并与 `test_registry.py:351-353` 措辞统一。
- **降级说明**：纯文档面，代码与断言均正确；若返工预算紧张，Coordinator 可下调为 P3 并计入遗留——**不建议**，因为 TOOL-055 的「文件」字段是工具目录的检索入口。

### P3-1 `extract_marked_block` 的 `display` 参数未使用
- 位置：`:268-285`（函数体未引用 `display`）；调用点 `test_verify_workflow.py:20168/20179`。
- 依据：grep 该函数体内无 `display` 出现。影响：死参数，读者误以为有诊断输出（persona 解析器同名参数确有 WARN 输出，`:329-331`）。建议：删除参数或对齐 persona 解析器补 WARN。

### P3-2 `tiers["resident"]` 裸索引
- 位置：`:589-590`（另 `test_verify_workflow.py:718-719` 的 CLI 分支同风险）。
- 依据：`tiers` 由 `BUDGET_TIER_POLICY` 的键构成（`:534-549`）；策略表改名/删 `resident` → `KeyError`（崩溃而非 fail-closed）。契约 `:1-47` 声明"三级 fail-closed"，此处是例外。
- 建议：`tiers.get("resident") or {"tokens":0,...}` 或显式校验 + issue。

### P3-3 `injection_budget_tier_gate()` 的 `hard` 默认无触发路径
- 位置：`:480-482`。当前 `BUDGET_TIER_POLICY` 三档齐全（resident=advisory / skill+command=report-only），`hard` 分支（`:572-573`）与默认分支均无活体测试；测试靠直接改 dict（`test_verify_workflow.py:20336-20444`）而非经该函数。
- 建议：补一条 `injection_budget_tier_gate("unknown") == "hard"` 断言，把"未知档=fail-closed"从注释变为可验证事实。

### P3-4 `--format json` 丢弃 `issues`
- 位置：`:704-706`。与 `TOOLS.md:589`「机读断言用 `--format json` 的 `verdict` / `tiers` 字段」不矛盾，但 CI 判失败后仍需跑一次 text 才能看到原因。
- 依据：同族命令 `cmd_check_injection_contract`（`verify_workflow.py:21484-21503`）本就无 `--format`，故属**新增能力上的取舍**而非偏离；测试 `test_cli_json_format_is_machine_readable`（20393-20406）只断言 `surfaces/verdict/budget_tokens`。
- 建议：JSON 增 `issues`（或 `issue_count`）字段，或显式在 help/TOOL-055 注明"失败原因仅 text 面输出"。

### P3-5 反静默守卫断言为真阳性
- 位置：`test_governance_cost.py:800-810`。`needle = "." + "skip" + "Test" + "("` 拼接后为 `.skipTest(`，而源码（`:44`）是 `testcase.skipTest(`——断言通过但**不是**守卫想验证的调用点。当前"唯一 skip 调用点"事实仍成立（grep 实测全文件仅 `:44` 一处），故非事实失真，但守卫在重构后可能失效而不报警。
- 建议：改为断言 `_require_zstandard` 函数体集合，或直接 `assertEqual(source.count("_require_zstandard("), N)`。

### P3-6 测试注释与自身实现不符（stale docstring）
- 位置：`test_verify_workflow.py:19983` 与 `:19986` 写「ASCII arm（0.4 tok/char）」，实现为 `ceil(chars*2/5)`（`:218`）。
- 建议：统一为 `2/5 (=0.4)` 或 `ceil(chars*2/5)`。

### P3-7 triage files 面与变更集不符
- 位置：`.governance/change-triage/FEAT-039.json:10-12` 仅列 `verify_workflow.py`；实际变更含 `checks/injection_budget.py` / `registry.py` / `TOOLS.md` / 5 个测试文件 / 2 个冻结面。
- 依据：triage 的 `files` 面是冲突检测输入（`:439-987` 的大段 conflicts 全部由它派生）。新 leaf 文件未被声明 → 未来并行任务的冲突检测漏面。
- 建议：返工时补 `files` 面（治理记录，Coordinator 快速通道可直改）。

### P3-8 切片 A 出货态 → 详细见 §七 R-1（风险登记建议，非缺陷）
- 位置：`injection_budget.py:162-175`（`BUDGET_TIER_POLICY.resident.gate = "advisory"`）。
- 依据：live 6 档中 `entry-skill` 8,573 tok（超 6K 预算 2,573 tok）为 report-only，`resident` 为 advisory；**出货默认配置下本门禁不会阻断任何回归**（lightweight resident 实跑 4,763/6,000，已有 26% 余量）。AUDIT-154 §8 L185 的验收字面为「守护 FAIL」。
- 处理建议：产品姿态是切片 A 的显式决定（docstring `:36-41` + 测试钉住 flip），本轮**不作阻断**；建议 Coordinator：①在 risk-log 登记一条"注入预算门禁出货态为 advisory，回弹不阻断"，②排期"std/strict 入口模板瘦身"或"resident→hard flip"其一，③把 §七 R-1 的表述补进 TOOL-055/CHANGELOG，避免下游读成"装机即阻断"。

### P3-9 面级 sha256 无基线锚（特别审查点回执）
- 依据：`check_injection_budget` 返回结构（`:583-599`）**不含任何 hash 字段**；但 `project/e2e-test-project` 镜像与本仓的冻结面对照中，`architecture-baseline.json` 用了 `r6.import_set_sha256`、`governance_cost`/`bootstrap_aggregate` 用 `_projection_hash` 先例。
- 影响：本门禁**无**独立于 token 数的漂移检测；同一 token 数的内容替换（等长改写）不可检。COORD 任务提出的"基线指纹前 16 位作为后续漂移锚"——**当前实现未提供该指纹**，属未落地能力。
- 建议：在 `rows`/`tiers` 增 `sha256_16`（对解析后文本），并在 `TOOL-055` 注明其用途（漂移锚）；或明确声明本门禁只做体积面、内容漂移由 `check-injection-contract` 负责（边界已如此声明：TOOLS.md:590 三者互补）。

---

## 六、AI 专项 5 项检查

| # | 项 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock/硬编码残留 | **无** | grep `mock`——leaf 内 0 处；测试用 `patch.object(_DEFAULT_ROOT)` + 临时 root 属正规注入（`test_verify_workflow.py:20384`）。基线数字未硬编码进产品代码（测试阈值由测量派生，`:20195-20199` 明示） |
| 2 | 硬编码返回值 | **无** | 全部数值来自文件解析；`TOOL_RETURN_BUDGET_EXPECTED=8192` 是**契约断言值**（登记 FEAT-033 预算），并带漂移反相测试（`:20334-20347`），属有意设计 |
| 3 | 幻觉 API | **无** | 仅 4 个 stdlib import（`json/re/sys/pathlib`）；无第三方 tokenizer 依赖（口径已文档化 `:11-20` + `tokenizer_calibration()` 逐字引用）；`@deepseek-ai/dsh-token-meter CHARS_PER_TOKEN = 4` 与 `@deepseek-ai/dsh-persona` 均为仓库内实际存在的引用（后者 `agent.cordis.yml.template:46`） |
| 4 | 未实现 TODO | **无** | grep `TODO/FIXME/XXX/HACK`——0 处；声明的能力（六面/三档口径/三层 gate/CLI/Check 33 内联/CI 接线三路径）逐项在代码中找到实现 |
| 5 | 过度实现 | **否** | 733 行 ≈ 47% docstring；函数 21 个，最长 `check_injection_budget` 115 行（含 30 行渲染/结构构造），其余 ≤60 行（`extract_persona_prefix_from_template` 45 / `format_budget_report` 44 / `cmd_check_injection_budget` 55）。单一职责未破，未引入非必需抽象层。**结论：体量合理**，唯一"多余"是 P3-1 死参数与 P3-2 裸索引 |

---

## 七、特别审查点回执

| # | 特别点 | 回执 |
|---|---|---|
| 1 | 口径独立性（与 `check-injection-contract` 单职责分离） | ✓ 通过。锚点面 3 文件/23 锚点不变（`verify_workflow.py:6678-6706` 实测计数）；体积面独立 leaf/CLI/registry 行；两者在 Check 33 内**同段双信息**但各自 verdict 独立（`:16345-16363`），零新增 segment id（registry `("33", ...)` 未动、snapshots `check_segments` 71 键不变） |
| 2 | Check 33 内联 | ✓ 通过（附 P2-1 文案问题）。同段双信息零新增 segment id；`all_issues` 正确累加预算 issue（`:16354`）；ADVISORY 行不阻断（`:16357-16360`） |
| 3 | 面级 sha256 可追溯性 | ✗ **未实现**（P3-9）。返回结构无 hash 字段；"基线指纹前 16 位"在本次变更集中不存在。漂移检测目前仅靠 token 数与 fail-closed 解析 |
| 4 | AI 专项 | ✓ 见 §六（5/5 项完成，无 mock/硬编码/幻觉 API/TODO，非过度实现） |
| 5 | 并发耦合归属（038+039 同树） | ✓ 按内容面区分完成：039 面 = FEAT-039 段（6848-6904）/ Check 33 分项（16352-16363）/ subparser（24062-24067）/ dispatch（24713）/ 新 leaf / registry 2 处 / TOOLS.md / 5 测试面 / 2 冻结面。038 的归属改指与 `REQUIRED_SNIPPETS` 修复面**未纳入**本轮 P 级判定（已在 697689d 披露） |
| 6 | 60 行函数长度（维度 3 检查项） | 例外说明：`check_injection_budget` 115 行 = 数据装配（rows 24 行 + issues 7 行 + tiers 16 行 + verdict 17 行 + 返回结构 17 行），无嵌套控制流，判定可接受；不构成 P 级 |

### R-1（风险登记建议，非缺陷）

**出货态门禁不阻断**：`resident` 档 gate=advisory。后果——lightweight 基线 4,763 tok 距 6,000 有 26% 余量，**回弹到 6K 不会 FAIL**；真正超限的 `entry-skill`（8,573 tok）属 report-only。AUDIT-154 §8 L185 字面「≤6K tok 守护 FAIL」在执行上被延后为"可一行翻转"。
建议（三选一，需 Coordinator/用户裁决，属产品姿态非代码缺陷）：
(a) 本切片接受 advisory 并在 risk-log 登记回弹风险；(b) 把 `resident` flip 为 `hard`（测试已钉住行为，数据改动一行）；(c) 为 `entry-skill` 设独立预算（当前 8,573 tok 无任何门控）。

---

## 八、硬门槛裁决

| 门槛项 | 阈值 | 实测 | 判定 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **0** | ✓ 通过 |
| 5 维度全覆盖 | = 100% | 5/5 有结论（§三） | ✓ 通过 |
| 每条发现标注级别 | = 100% | 11 条全部带 P0~P3（P1×1 / P2×2 / P3×8） | ✓ 通过 |
| 设计一致性检查 | 已完成 | 逐项比对 triage + AUDIT-154 §8（§四）——2 项"部分"：PASS/FAIL 出货态、audit「守护 FAIL」字面 | ⚠ 部分（见 R-1） |
| AI 代码专项 5 项 | 全部完成 | 5/5（§六） | ✓ 通过 |

**结论：NEEDS_CHANGE**
- `unresolved_blockers` = 1（P1-1）
- 返工优先级：P1-1（切片上界口径 + 精度断言 + 基线数字同步）→ P2-2（3 处归属注释）→ P2-1（三处文案口径）→ P3-7（triage files）
- 复审要求（M7.4 step 4.6）：R1 须逐条比对本清单（已修复 / 未修复 / 新引入），并在报告头部声明 round 号与本文件路径
- round ≥ 3 仍有 BLOCKING → 转 BLOCKED + escalation

---

## 九、申报事实逐项核实（Developer claims 1-8）

| # | 申报 | 核实结论 |
|---|---|---|
| 1 | 多文件求和口径：resident 四文件求和 4,763 tok；拆分文件不能绕过 | ✓ 数字吻合（实跑 4,763）；面声明即实际加载集合。口径选择两项均成立：persona 取 `prefix:` 块标量非整 YAML；入口取 canonical Step 7 模板非工作区文件。**但**：`entry-template` 面本身含非注入文本（P1-1） |
| 2 | tokenizer 不低估性：`tokens ≥ tokens_host` 恒成立 | ✓ 数学成立（三档逐项验证 + 5 脚本用例）；CJK 1/字 vs host 1/4 字，中文富文本下主机低估 3-4 倍，预算取大者 |
| 3 | fail-closed 解析：移动/锚点损坏/越界 → 显式 issue 不静默记 0 | ✓ 五条错误路径均返回 `""` 并转为 issue（唯一例外 P3-2 的 `tiers["resident"]` 裸索引） |
| 4 | advisory 语义：standard 10,428 / strict 10,629 超限输出分项但 exit 0；`--fail-on-issues` FAIL→1/ADVISORY→0；翻 hard 是一行数据改动被测试钉住 | ✓ 数字逐位吻合（实跑 10,428 / 10,629）；裁决代码 `:572-582` 核实；flip 行为由 `test_budget_tier_is_not_a_hard_fail_while_advisory` 钉住（但该测试直接改 dict，未经 `injection_budget_tier_gate`——P3-3）。**ADVISORY exit 0 无显式断言**（`test_cli_reports_per_surface_budget_and_exit_codes:20371-20378` 未 `assertRaises`，靠"测试自身不崩"隐含）——P3 级测试覆盖缺口 |
| 5 | zstandard 断言：3 测试（硬 FAIL 带安装命令 / 反静默守卫唯一触发源 / fail-closed 报错文本） | ✓ 3 测试存在且逻辑真实覆盖（`test_governance_cost.py:791-818`）；反静默守卫断言字符串有缺陷（P3-5），但"唯一 skip 调用点"事实成立 |
| 6 | tool-return 登记：`MAX_JSON_BYTES==8192` + `_enforce_projection_budget` 存在 + 漂移反相测试 | ✓ 实跑 `{'max_json_bytes': 8192, 'enforced': True, 'issues': []}`；反相测试改 999999 → issue 成立；`bootstrap_aggregate.py:85` 与 `:744` 双点核实 |
| 7 | 架构合规：初版 680 行引擎内已重构为叶子；引擎净增 1 print；archguard PASS（24,769/1304/199 合流锚） | ✓ `anchor_loc=24769` = 引擎实测 24,769 行；`r4.total=1304`（`cmd_check_injection_budget` 不在 per_function 表）；`r6.import_count=199`；Check 33 净增 1 print site。三项合流锚与 FEAT-038 双向吸收的注记在 `test_archguard_ratchet.py:67-75` 披露 |
| 8 | 基线诚实性：六面表格 + 对照 AUDIT-154 ~110KB → 56.8KB（-48%） | ✓ 六面表格四项/面齐备（bytes/chars/cjk/tok/tok_host/sha256 项——**sha256 项不存在，见 P3-9**）；全域 56,826B ≈ 56.8KB 吻合。**-48% 口径需限定**：110KB 出自 AUDIT-154 §2「交互前注入+读取 ~110KB 治理材料」（含读取面），与注入面口径不同，不宜作等价对照 |

> 另：COORD 任务描述称 `test_verify_workflow +30`——实测新增类 `Feat039InjectionBudgetTests` 含 **23 个 test 方法**（19962-20434，我逐个数出）+ `test_governance_cost` **3 个**。+30 疑为行数口径或与其他面混计；覆盖实质（正/反向对）已核实充分。

---

## 十、审查边界声明

- 本审查为**只读**：未修改任何产品代码、未执行写操作、未运行完整测试套件（仅以 pwsh 只读执行度量复现）。
- 未复跑 `check-governance` / `archguard-ratchet` / contract-matrix 全套（属 Coordinator 的验证职责）；冻结面数字系**静态比对**（引擎行数 24,769 与 `anchor_loc` 一致、dispatch 键计数 88 与 `key_count` 一致——逐行数出 24674-24761 共 88 键、`r4.total` 1304 与 `COMMAND_SPECS` 逐项计数一致）。
- 「既有命令零回归」为**静态**判定（锚点面 3 文件/23 锚点未变、Check 33 段 id 与 segment 面 71 键未变）+ 活体度量实跑；未运行既有测试套件，故"无新增字段/输出对既有断言的副作用"未实测。
- 覆盖率未附报告 → 维度 5 该项标为不可验证。
- 无法从事实验证的项已标 `未验证`，未写成通过。
