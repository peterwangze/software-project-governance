# Code Review: FIX-304-CODE-R0 — FEAT-025 R0 遗留批 F-1~F-10 逐条处置

- **Task**: FIX-304（round 0）
- **Reviewer**: Code Reviewer Agent（只读审查；不修改产品代码、不与用户直接交互）
- **Round**: R0（本批**首次**审查，无同批前轮报告）。**上游依据** = `docs/reviews/review-FEAT-025-CODE-R0.md`（FEAT-025 R0，APPROVED_WITH_NOTES / unresolved_blockers=0 / P1×1+P2×2+P3×7，F-1~F-10）——本批即其 F-1~F-10 的逐条处置，故报告头部同时承担"逐条比对前轮 findings"的义务（role §审查结论 (1)(2)）。
- **审查对象**: **工作树 diff**（非 commit——Step 14 审查证据门要求 FIX 前缀先审后提交），路径限定：
  - `skills/software-project-governance/infra/quickscan_registry.py`
  - `skills/software-project-governance/infra/tests/test_quickscan_registry.py`
- **冻结锚核验（审查开始时 + 报告落盘前两次复算，均一致）**:
  | 文件 | worktree blob（派发锚） | 实测 | base blob @HEAD `36f2040` |
  |---|---|---|---|
  | `quickscan_registry.py` | `4c34b0012cc6af5cdab42e23c470df3141ce878b` | ✅ 相同 | `c0f23bbcf81339d0573df7054dadd7514480ecc9` |
  | `test_quickscan_registry.py` | `527d77549d3464f3f9d721f6cdcf0a1eb86c2cd9` | ✅ 相同 | `651edc0f3c83548a07b2a0a1d69663a2bf0d6e58` |
  **base 锚的关键意义**：base 两 blob 与 **FEAT-025 R0 的审查对象（commit `504cc8f`）逐字节相同**（R0 报告 §头部记载 `c0f23bbc…`/`651edc0f…`）⇒ 本 diff 的 base **恰为 R0 所审状态**，F-1~F-10 的处置面锚定正确，diff 即"R0 结论 → 本批修复"的完整增量。
- **规模核验**: `git diff --numstat`（路径限定）= 72/11 + 325/10 = **397 insertions / 21 deletions / 2 files** ✅ 与派发预期逐数字相同；行数 `996`（935+72−11）+ `903`（588+325−10）。
- **审查方法**: 逐行读两文件 diff **全量**（模块 83 行变更 / 测试 335 行变更，非抽样）→ 对每个 hunk 做**行为级独立核验**（不采信 commit/EVD 描述）→ 对照上游 R0 的 F-1~F-10 逐条裁决。核查等级逐条标注：✅独立复现 / ⚠采信（附静态论证）/ ❓无法核验。
- **执行过的只读命令（诚实披露）**: `git hash-object / rev-parse / status / numstat / diff / show`；`python -B` 内存内省与反例构造（真实引擎、真实快照、真实注册表；含 in-memory 源码注入）；`pytest -B -p no:cacheprovider`（目标文件 78 例 + FEAT-022 消费者 71 例）；`coverage`（`COVERAGE_FILE` 重定向至 `%TEMP%`，**仓外**）；`verify_workflow.py archguard-ratchet`（默认只读路径；写盘仅在 `--regen`，本轮未触发）。
- **边界声明（诚实）**: **未修改任何被审文件**（两 blob 全程恒定）；**未写入任何仓库文件**（除本报告）；`-B` + `-p no:cacheprovider` + `COVERAGE_FILE` 重定向后 `git status --porcelain` 全程为 6 个 ` M`、**零 `??` 新增**；覆盖率数据文件落 `%TEMP%\cov_fix304_review.dat`（仓外，已披露）。
- **环境披露（并发会话，经 Coordinator 转告确认）**: 工作树另有 **4 个 FIX-303 在飞文件**（`core/architecture-baseline.json`、`infra/archguard_ratchet.py`、`infra/contracts.py`、`infra/tests/test_contracts.py`）——**不属本审查面**，全部结论路径限定两 quickscan 文件。唯一受影响项 = `archguard-ratchet` 复跑（FIX-303 改动其自身实现与基线），已在 §四第 3 条显式披露并附"该门禁不消费 `quickscan_registry`"的静态论证。

---

## 一、5 个评审维度逐项结论

### 维度 1：正确性 — 通过（含 P2×1 / P3×2）

**1.1 逐 hunk 行为核验（全部独立复现为真）**

| # | 改动 | 独立核验（本人实测） | 判定 |
|---|---|---|---|
| F-3 | `discover_engine_segment_ids` 返回前唯一性 `ValueError`（:817-823） | 合成引擎 fixture 重复 `# ── 29. ` → **修前**：`len=71 / unique=70 / undeclared=() / ok=True`（R0 反例签名逐字段复现）；**修后**：`ValueError: duplicate engine segment section(s) ['29'] — Check ID uniqueness is zero-tolerance (§4.1 R5)`；`guard_completeness(engine_path=fixture)` 亦抛（永不产出 `ok=True` 裁决）。干净 fixture 对照 = 70 段且集合恒等 | ✅ |
| F-2 | product-gate 解析空集 fail-closed（:843-847） | 单引号块 → `ValueError`（含 "parsed"）；`frozenset({\n})` 仅锚点 → `ValueError`；正对照 `("7","31")` 正确；live = **25 / unique 25**，与 `excluded_ids()` 集合恒等。**残余**：混合引号块 → 静默返回 `('31',)`（见 G-3） | ✅（含 G-3） |
| F-7 | `range(start + 5, …)` → `range(start + 1, …)` + 注释（:810-815） | 真实引擎 start = L14767（`def _run_full_engine_checks(args):`）；**offset 1~7 逐值实测结果恒等**（70 段 / 唯一 / `end=16444`）⇒ 零回归；诱饵反例（真实 `def` 紧随 entry def）新代码 = `("1",)`，旧 `+5` 会越过该 def 并吞入其后的段（=旧代码的存在性缺陷） | ✅ |
| F-5 | `fallback_mode` → `fallback_target`（:910/:969）+ `lines()` 文本（:919） | 健康运行：`fail_closed=False`、`fallback_target='full'`、`hasattr(report,"fallback_mode")==False`、`lines()[0]` = `… fallback_target=full` | ✅ |
| F-6 | `"SEGMENTS"` 入 `__all__`（:106） | 字母序正确（`SEGMENTS` < `SEGMENT_SPEC_FIELDS`，`S`0x53 < `_`0x5F）；`__all__` 无重复；模块自定义公开符号**未导出差集 = `[]`**（实测） | ✅ |
| F-8 | census 序口径 docstring（:790-798） | census 序 ≠ 快照序实测：**首个错位下标 = 55**，`(census[55], snapshot[55]) == ("29","28u")`；集合恒等 True | ✅ |
| F-1 | 测试侧文本截断 → AST 模块体机判 | 真实模块 `_module_level_io_offenses(source) == []`；**in-situ 注入**（真实模块源码尾追加模块级 `read_text`）→ 命中 `line 998: module-level .read_text()` ⇒ 扫描面**已覆盖表区之后**；旧 slice 实测 = **225 行 / 当前 996 行**（R0 在 935 行版本实测 219 行），其内 `SEGMENTS = (`(L234)、`C3_ADJUDICATION = {`(L622)、`_BY_ID = _index()`(L716) **全部不在扫描面内** ⇒ R0 的"假绿"结论在修前版本上被逐项复现。**残余**：模块级调用本模块已定义函数（`_X = _load_table()`）不被拦（见 G-2） | ✅（含 G-2） |
| F-4 | `not-quick:` 扩展词汇 docstring 披露 | docstring 实测含 `not-quick:` / `扩展词汇` / `REFACTOR-light-registry` / `REFACTOR-quickscan-orchestration` / `L253` 全 5 token | ✅ |
| F-10 | C3 basis `_` 符号机判（测试侧 :163-185、:443-463） | 四段 basis 的 `_` 前缀符号全部解析：28g×8 / 28j×3 / 28l×0 / 29×0 = **11 个 distinct 符号，undefined = `()`**（引擎 + `checks/*.py` 实测 **17 文件**）；负对照 `_parse_open_risks` → `('_parse_open_risks',)` | ✅ |

**1.2 设计一致性（对照 §2.4 四态 / §4.1 R5 / §6 L250 ① ② ③ / §255）**
- §4.1 R5（L260 "Check ID 唯一…零容忍（fatal）"）：注册表侧（导入期 :719-720）与观察侧（census 返回前 :818-823）**两侧同构**，新增 `_duplicate_ids()` 为其共用实现 ⇒ 一致性成立（R0 的"观察侧半覆盖"已消除）。**但**：证据链只覆盖 `discover_engine_segment_ids` 一个入口，`guard_completeness(observed_ids=…)` 显式入参路径仍可复现 R0 反例（G-1，P2）。
- §2.4 四态契约：本批**未引入**任何四态实现（Slice-2 职责），F-3 选型把"观察不可信"留给 `ValueError`（→ Slice-2 映射 `undetermined → 回退 full`），**没有**把重复段并入 `undeclared`（那会把"观察不可信"误报为"注册表缺失/覆盖缺口"）⇒ 与 §2.4 第 4 行语义自洽（详见 §六验收 3）。
- §6 L250 ①（70/70 机判）：本批未触及 70 行表本体与快照对账逻辑；`reconcile_snapshot()` 实跑仍 `ok=True`、census 70/70 唯一 ✅。
- §6 L250 ②（新段未入表 → 告警 + fail-closed 回退 full）：既有 fixture 负对照全部保留并复跑通过；本批把守卫的"输入可信性"前置到 census 层 ✅。
- §6 L250 ③（表 schema ⊂ `CheckSpec` 字段集）：本批未改 `SEGMENT_SPEC_FIELDS`/`CHECKSPEC_FIELDS`/行 schema ✅（`fallback_target` 属 `CompletenessReport` 非注册行 schema，不受 ③ 约束）。
- §255（载体禁写入巨石编排体）：引擎零改动（numstat 不含 `verify_workflow.py`）、引擎零 `quickscan` 引用、注册表不 import 引擎 ✅；本批**未新增** CLI/编排/接线。

**1.3 发现（正确性）**
- **G-1（P2）** F-3 的守卫在**显式 `observed_ids` 入参路径**上缺失，R0 原反例签名（71/ok=True/空告警）可逐字段复现（§五）。
- **G-2（P3）** F-1 的 AST 机判对"经本模块函数间接 I/O"的模块级调用不留痕（§五）。
- **G-3（P3）** F-2 的 fail-closed 只覆盖"零命中"，部分形态变化静默返回子集（§五）。

### 维度 2：安全性 — 通过（无发现）

- **产品面零 I/O / 零副作用**：`_module_level_io_offenses` 对真实模块 = `[]`（机判）；新增代码中 `_duplicate_ids()` 为纯函数（两次集合操作，无 I/O）；两文件机判 `subprocess|os.system|shell=True|eval(|exec(` = **0**（测试文件唯一命中为 `assertNotIn("import subprocess", source)` 这一**负向断言**，:590）、`print(` = 0（产品）/ 1（测试内的**负对照夹具字符串** `"print('x')\n"`，:648）。
- **测试侧新增读取面**：`_python_sources()`（:168-178）读引擎 + `checks/*.py`（实测 17 文件）——**只读**，且用模块级缓存避免重复 I/O；`_engine_source()` 既有只读封装。写操作仍仅限 `tempfile.TemporaryDirectory()`（`_write_engine_fixture`/`_write_snapshot` 未变，新增用例沿用同一夹具，无新增写面）。
- **注入 / ReDoS**：新增 `_UNDERSCORE_SYMBOL_RE = re.compile(r"(?<![A-Za-z0-9_])_[A-Za-z][A-Za-z0-9_]*")` 固定形态、无嵌套量词、作用于仓内可控文本；`_SEGMENT_SECTION_RE`/`_PRODUCT_GATE_RE` 未改动；无用户可控字符串拼入正则或命令。
- **fail-closed 方向正确**：F-2 把"锚点在而解析退化为空"由**静默空集**改为**抛错**——空集会令 `plugin_face_not_product_gated()` 把 27 个插件面段误报为"未受 product-gate 管辖"（原 R0 判定的过度披露方向），收紧后不可静默发生 ✅。
- **敏感数据 / 权限面**：两文件零密钥/token/凭据；模块仍为纯只读数据模块，无提权面（P7 数据安全无暴露面）。

### 维度 3：可维护性 — 通过（含 P3×2 讨论项）

- **命名即语义**：F-5 把歧义名 `fallback_mode`（读作"回退后的模式"）改为 `fallback_target`（读作"回退目标"），并在 docstring 明写"`fail_closed` 是唯一判别字段"——直接消除 R0 指出的误读面；新增 `_duplicate_ids`/`_module_level_io_offenses`/`_undefined_basis_symbols`/`_python_sources` 均表意清晰（`_` 前缀私有）。
- **函数长度 / 复杂度**：`discover_engine_segment_ids` 代码体约 25 行（含 docstring 约 43 行 < 50 行阈值）；`_duplicate_ids` 14 行；测试侧 `_module_level_io_offenses` 20 行、`_python_sources` 11 行——无超长函数。
- **注释与文档质量（正面范例）**：F-7 用两行注释解释"为何不需要偏置"替换魔数 `+5`；F-2/F-3/F-5/F-8 的 docstring 均写明**实现口径 + 失败分支 + 设计锚点（§4.1 R5 / §2.4 / §3.6 L221 / §6 L253）**，无"描述与实现不符"（R0 的 F-2 病根）残留。**唯二措辞超出实现处**：G-1 的"故本守卫**永不**把重复 census 报成 `ok`"（:941，绝对措辞）、G-2 的 "declarations with zero I/O / side effects"（测试 :141）。
- **重复代码**：`_duplicate_ids()` 让注册表侧与观察侧共用唯一性语义（与 :719-720 同构），测试侧 `_python_sources()` 缓存避免 4 处重复读盘 —— 均为**消重**方向。
- **改动纯粹性（D4）**：diff 全部 hunk 可逐条追溯至 F-1~F-10（见 §二映射表），无夹带、无格式化噪声（deletions 21 行全部为被替换行）。

### 维度 4：性能 — 通过（无发现）

- **产品面新增成本可忽略**：`_duplicate_ids()` 为 O(n) 单遍（n ≤ 70）；`discover_engine_segment_ids` 仍为"一次 `read_text` + `splitlines` + 一次正则"，无新增 I/O、无循环内 I/O。
- **import 期零变更**：模块级语句仍无 I/O（AST 机判 0 offense）；新增仅一个函数定义与 docstring ⇒ R6 启动预算无新增（复跑 `archguard-ratchet` R6 实测 `196 modules (baseline 196, Δ0)`）。
- **测试侧**：`_python_sources()` 缓存使"引擎 + 17 文件"仅读一次；目标文件 78 例 0.33s（带 coverage 0.44s），未引入可感知开销；无 O(n²) 以上算法、无多余大对象常驻。
- **数据结构**：`_duplicate_ids` 用两个 `set` + 一次 `sorted(key=_id_sort_key)`，输出确定性有序（无 hash 序漂移）。

### 维度 5：测试覆盖 — 通过（含 P2×1 / P3×2 记录项）

- **独立复跑**：`pytest`（`-B -p no:cacheprovider`）= **78 passed / 0.33s**；带覆盖率同跑 = 78 passed / 0.44s。
- **清点与声称对账（重命名级差异，非计数估算）**：old 60 → new 78；`removed = ['test_registry_declares_no_module_level_file_io']`（F-1 改写）、`added = 19`、`kept = 59` ⇒ **59 + 19 = 78** ✅。新增 19 条逐条归属：F-1×4（含 1 条改写）、F-2×3、F-3×3、F-5×1、F-6×2、F-7×1、F-8×2、F-4×1、F-10×2 = 19 ✅ 与处置矩阵声称吻合（EVD-998 的**文字分解**有算术瑕疵，见 G-4）。
- **覆盖率独立复跑（逐数字吻合）**：`Stmts 196 / Miss 1 / 99% / Missing = 720`；L720 = `raise ValueError("quickscan registry declares duplicate CheckID rows")`（:719-720 导入期守卫，**位移自 R0 的 L699**）⇒ "位移守卫"表述属实；因仅 1 miss，可反推 `_duplicate_ids()` 与 census 重复抛错分支（:817-823）**已被测试执行**。
- **负对照有牙（逐条实测，非阅读判断）**：
  - F-1 假绿反例（`test_module_level_guard_catches_the_false_green_counterexample` :624）：合成源中 I/O 位于首 `def` 之下 → 新判命中；并**同时**断言旧 slice 面 = `'"""Module docstring."""'` 且不含 `read_text` ⇒ 证明"旧守卫为何是绿的"，属可打穿的反例（我另行在**真实模块**上做了 in-situ 注入复现）。
  - F-1 非法/裸调用/语句（:644）：`open('x').read()`、`print('x')`、`json.loads('{}')`、`for` 语句四例全部命中；正对照（:653）函数体内读放行、类体 `open` 仍命中。
  - F-3 反例转正（:693 + :705）：重复段 → `ValueError`；`guard_completeness(engine_path=…)` 同样抛（不产 `ok=True`）。
  - F-7 诱饵（:712）：旧 `+5` 会吞掉紧随 def 之后的段（99 被误纳入），新实现返回 `("1",)`。
  - F-8 错位（:732）：`mismatch == 55` 且 `(observed[55], snapshot[55]) == ("29","28u")`（我独立复算相同）+ 文档口径断言；:745 追加"置换不改变裁决"的集合语义正对照。
  - F-10 错名（:452）：`_parse_open_risks` 被抓；:443 断言 `≥8` 个符号以**拒绝空转**（实测 11）。
  - F-2（:811/:833/:846）：空解析抛错 / 正对照解析 / live 25 唯一。
- **覆盖缺口**：
  - **G-1**：`guard_completeness(observed_ids=…)`、`reconcile_snapshot(actual_ids=…)` 的**显式入参重复**路径无负对照（现有 `test_guard_never_reports_a_duplicate_census_as_ok` :705 只走 `engine_path` 发现路径）。
  - **G-5**：F-1 的"in-situ 证明"未以测试形态落库（落库负对照用合成源）。
- **测试卫生（正面）**：两文件零 `unittest.mock`/`MagicMock`/`patch`（机判 0）；写操作仅 tempdir；`sys.path.insert` 与仓内既有约定一致（无 conftest.py，属既有模式）；`_python_sources()` 用模块级缓存而非重复磁盘 I/O。

---

## 二、F-1~F-10 处置逐条裁决（与上游 `review-FEAT-025-CODE-R0.md` 逐条比对）

| 上游项 | 原级别 | 上游要求的处置 | 本批实现位置 | 裁决 | 事实依据（本人实测） |
|---|---|---|---|---|---|
| **F-1** | **P1** | 把假绿守卫改为 AST 模块体机判（白名单 / 禁模块级 `ast.Call`） | 测试 :112-160（判据）+ :611-663（4 用例） | ✅ **有效** | 真实模块 0 offense；in-situ 注真实模块 → 命中 `line 998`；旧 slice 实测 225/996 行、不含 `SEGMENTS`(L234)/`C3_ADJUDICATION`(L622)/`_BY_ID`(L716)（=R0 洞的逐项复现）。残存间接调用盲区 → **G-2**（P3，不重开 F-1） |
| **F-2** | P2 | (a) 措辞更正为"文本解析" 或 (b) 改真 AST；**无论哪条**补结果非空/数量断言 | 模块 :830-834（口径）+ :843-847（空集 fail-closed）；测试 :811-849（3 用例） | ✅ **有效** | 选 (a) 并**同时**补"非空"分支；docstring 机判含 "not AST"/"fail-closed"；空解析/仅锚点实测抛错、正对照与 live 25 唯一通过。残存部分解析 → **G-3**（P3，属 R0 要求范围之内） |
| **F-3** | P2 | 选项 a：census 返回前唯一性校验（与注册表侧同构）／选项 b：并入 `undeclared` + 负对照 | 模块 :697-709（`_duplicate_ids`）+ :817-823（抛错）；测试 :688-711（3 用例） | ✅ **有效（选型 a 成立，见 §六验收 3）**；残存见 **G-1** | 发现路径：修前 `len=71/unique=70/ok=True/undeclared=()` → 修后 `ValueError(['29'])`；注册表侧 :719-720 同构；反例转正测试有牙 |
| **F-4** | P3 | docstring 显式标注扩展词汇 + Phase-2 平移口径归属 | 模块 :33-42（docstring）+ 测试 :342-355 | ✅ **有效** | docstring 含 5 个必需 token（`not-quick:`/`扩展词汇`/`REFACTOR-light-registry`/`REFACTOR-quickscan-orchestration`/`L253`）；机判取代人读 |
| **F-5** | P3 | 改名 `fallback_target` 或未熔断置 `None`；并写明"是否回退以 `fail_closed` 为准" | 模块 :898-901（判别说明）+ :910/:919/:938/:969（改名）；测试 :291-305 + 4 处同步 | ✅ **有效** | 健康运行 `fail_closed=False / fallback_target='full' / hasattr(fallback_mode)=False`；`lines()` 文本同步；改名 5 处调用点全部同步（:253/:262/:278/:867/:880） |
| **F-6** | P3 | 把 `"SEGMENTS"` 加入 `__all__`（或 docstring 注明不导出） | 模块 :106；测试 :665-683 | ✅ **有效** | `SEGMENTS" in __all__ = True`、字母序正确、无重复导出、模块自定义公开符号未导出差集 `[]`（机判替代人读） |
| **F-7** | P3 | 注释说明意图 或 改 `+1` + 边界用例 | 模块 :810-815（`+1` + 注释）；测试 :712-730（诱饵反例） | ✅ **有效** | 真实引擎 offset 1~7 逐值结果恒等（70/唯一/`end=16444`）⇒ 零回归；诱饵反例证明旧 `+5` 的**过捕获**缺陷。注释普适性 → **G-6**（P3 讨论） |
| **F-8** | P3 | docstring 明写"返回序 = 源码序，与快照位序无关；消费面用集合运算" | 模块 :790-798；测试 :732-751（2 用例） | ✅ **有效** | 首个错位下标 55 与 `("29","28u")` 独立复算相同；docstring 含 `source order`/`positional`；追加"置换不改裁决"正对照 |
| **F-9** | P3 | Coordinator 更正 EVD-995 行数 929 → 935 | 非代码改动（治理记录） | ✅ **已完成（回执核实）** | `.governance/evidence-log.md` L1939 实测已含"（935 行/181 stmts——F-9 更正）"，且 F-2 措辞亦已更正为"源码文本解析…〔F-2 更正——非 AST〕"⇒ 与 R0 要求逐项吻合；与本次 diff 无关（正确） |
| **F-10** | P3 | 追加"basis 中 `_` 开头标识符必须能在引擎/`checks` 中检索到"的机判 | 测试 :163-185（机制）+ :443-463（2 用例：正/负） | ✅ **有效** | 4 段 basis 的 11 个 distinct `_` 符号全部解析（`undefined=()`）；负对照抓 `_parse_open_risks`；`≥8` 非空断言防空转；符号域 = 引擎 + `checks/*.py`（实测 17 文件） |

**映射完备性核查（防"漏项/夹带"）**：模块侧 7 个 hunk → F-4(docstring)/F-6(`__all__`)/F-3(`_duplicate_ids`)/F-3+F-8+F-7(census)/F-2(product-gate)/F-5(report 字段)/F-3+F-5(guard 调用)；测试侧 9 个 hunk → 文件头 FIX-304 摘要 / `import ast`(F-1) / F-1 机制 / F-10 机制 / 各 F-* 用例 / F-5 改名同步 / F-7+F-3 fixture 用例 / F-8 用例 / F-6 用例。**diff 中无一条 hunk 无法追溯至 F-1~F-10**（D4 改动纯粹性成立）。

**汇总：10/10 逐条有处置；9 条代码/文档侧判"有效"，1 条（F-9）为治理记录侧"已完成并核实"。** 另登记 1 条 P2（G-1，F-3 的同族残存）+ 5 条 P3（G-2~G-6）。

---

## 三、AI 专项 5 项（逐项结论）

| 项 | 结论 | 依据（可复查事实） |
|---|---|---|
| **mock 残留** | **无** | 两文件机判 `unittest.mock|MagicMock|patch(` = **0**；新增负对照全部使用**真实**构造物——真实引擎文本（F-7/F-8）、真实快照、真实 `tempfile` 合成引擎源码（F-3/F-2）、真实注册表 `C3_ADJUDICATION`（F-10），强于打桩 |
| **硬编码返回值** | **无欺骗性硬编码** | 新增断言中的经验常数经**独立复算全为真**：`mismatch == 55`、`(observed[55], snap[55]) == ("29","28u")`、`len(ids) == 25`、`len(symbols) ≥ 8`（实测 11）、`len(observed) == 71`（重复 fixture）——均系"把已核验事实钉死"，非把实现输出抄成期望值（`_engine_ids_for_fixture()` 从注册表取而非复制常量） |
| **幻觉 API** | **无** | 新增 API 全部真实且经执行验证：`ast.parse/walk` 与 `Import/ImportFrom/Assign/AnnAssign/ClassDef/FunctionDef/AsyncFunctionDef/Expr/If/Call/Name/Attribute`、`Path.read_text/glob`、`re.compile`（后向断言合法）、`tempfile.TemporaryDirectory`、`assertRaisesRegex`、`frozenset`；被测模块新增 `_duplicate_ids` 仅用 `set`/`sorted` |
| **未实现 TODO** | **无** | 两文件机判 `TODO|FIXME|XXX|HACK|NotImplementedError` = **0**、`type: ignore` = **0**；F-3 的 `ValueError` 分支已实测可达（非桩），F-2 的 fail-closed 分支有正/负对照 |
| **过度实现** | **无** | diff 全部 hunk 可追溯至 F-1~F-10（§二映射）；未新增 CLI/旗标/编排/缓存（§255 边界保持）；未碰 70 行表本体与行 schema；唯一"超出字面"处 = F-6 追加"公开符号全导出"机判（:672-683），属**正当加强**（把 F-6 的"清单补齐"升级为"不再静默漏项"的守卫），且非投机功能 |

---

## 四、门禁声称 vs 独立核实

| # | 声称 | 核查结果 | 依据 |
|---|---|---|---|
| 1 | 78 passed（60→78） | ✅ **独立复现** | `pytest -B -p no:cacheprovider` → `78 passed in 0.33s`；重命名级清点 old 60 / new 78（kept 59 + added 19） |
| 2 | 覆盖率 196 stmts / 1 miss = 99%（miss = L720 位移守卫） | ✅ **独立复现** | `pytest --cov=quickscan_registry --cov-report=term-missing`（`COVERAGE_FILE` → `%TEMP%`）→ `Stmts 196 / Miss 1 / 99% / Missing = 720`；L720 实测为导入期重复 id 守卫（R0 记录为 L699，属行位移） |
| 3 | archguard-ratchet PASS 0 violations | ✅ **复跑通过**（含污染披露） | 实跑：`R1 PASS 24329≤24329` / `R2 PASS 46≤46 across 36 files` / `R3 PASS matrix 12 edges; managed 2 modules, SCC 1` / `R4 PASS 1310≤1310` / `R5 PASS cli 82/82 frozen, segments 70/70 frozen` / `R6 INFO 196 modules Δ0` / `R7 PASS deterministic=True; committed==fresh True` → `Result: PASS (0 violations)`, exit 0。**披露**：`archguard_ratchet.py` 与 `core/architecture-baseline.json` 正被 FIX-303 在飞修改，本次复跑是**混合树**结果；**静态论证该门禁不消费本批**：`archguard_ratchet.py` 零 `import quickscan_registry/registry`（机判），R5 走 FEAT-020 extractors + 冻结快照，R1 只计 `verify_workflow.py` LOC；且被审模块若被 R2/R3/R4 面扫描亦合规（零引擎 import、零 `print`、未新增 import） |
| 4 | 全量 2580 / 32F+1E 与基线签名一致，零涉及本批 | ⚠ **采信（未复跑）+ 静态论证** | 未复跑：① 工作树含 FIX-303 在飞两文件（`contracts.py`/`test_contracts.py`），全量结果**当前不可归属**本批；② 静态论证更强——全仓 `quickscan_registry` 的消费面**仅 3 处**：产品 `registry.py`（FEAT-022）+ 两个测试文件；两测试文件均已独立复跑绿（78 + 71）⇒ 本批的回归面在结构上被这两条命令完全覆盖 |
| 5 | FEAT-022 消费者 71 OK（改名零影响） | ✅ **独立复现 + 消费者面核实** | `pytest test_registry.py` → `71 passed in 17.02s`；`registry.py` 仅消费 `_segments.registry_ids()` / `_segments.segment(...)`（机判），**全仓零 `fallback_mode`/`CompletenessReport`/`guard_completeness` 消费**（除被审两文件）⇒ F-5 改名对本批之外零影响，声称成立 |
| 附 | F-1 "+4 测试" / F-2 "+3" / F-10 "引擎+checks/17 文件, 28g×8/28j×3" | ✅ **逐项吻合** | 新增用例归属清点 = 19（F-1×4 含改写、F-2×3、F-3×3、F-5×1、F-6×2、F-7×1、F-8×2、F-4×1、F-10×2）；`checks/*.py` = **17** 文件；`_` 符号逐段实测 28g=8 / 28j=3（合计 11，与声称一致） |
| 附 | 修前反例 "71/70/True 复现 → 修后 ValueError" | ✅ **逐字段复现** | 修前：`len=71 / unique=70 / ok=True / undeclared=() / stale=()`；修后：`ValueError(… duplicate … ['29'] …)` |

**小结**：**5 条主要声称中 4 条独立复现为真、1 条（全量回归）采信并附强静态论证**；无一条被证伪。EVD-998 的记录精度问题仅为**文字分解算术**（G-4），不影响其数字结论。

---

## 五、发现汇总（P0~P3 + file:line + 事实依据 + 建议）

| # | 级别 | 位置（file:line） | 问题与影响 | 事实依据（命令/实测） | 修复建议 |
|---|------|------------------|------------|----------------------|----------|
| **G-1** | **P2** | 模块 `quickscan_registry.py`:939-941（docstring 绝对措辞）+ :943-946（消费显式入参，无唯一性校验）；测试 `test_quickscan_registry.py`:705-711（负对照只走发现路径） | **F-3 的反例在第二入参路径上仍然成立**：`guard_completeness` 的 `observed_ids` 是公开受支持入参（`None` 时才走发现），但唯一性守卫只存在于 `discover_engine_segment_ids`（:817-823）。调用方传入含重复项的 census 时，本函数**原样复现 R0 的 F-3 签名**：`len(observed)=71 / unique=70 / undeclared=() / stale=() / warnings=() / ok=True / fail_closed=False` —— `ok=True` 且**零告警**（完全静默）。同族：`reconcile_snapshot(actual_ids=snapshot+("29",))` → `ok=True / actual len=71 / missing=() / extra=()`。**影响**：① docstring :941"故本守卫**永不**把重复 census 报成 ``ok``"对该路径**不成立**（措辞超出实现，与 R0 F-2 病根同族）；② R0 明确点出"`len(observed)` 被 71/70 混淆时会传递到消费面"——该失真在显式入参路径未被阻断；③ 当前**无产品消费方**（Slice-2 未建），方向 fail-safe（不损失覆盖、不误排除），故非 P0/P1。 | ① 实测 `qr.guard_completeness(observed_ids=tuple(snapshot)+("29",))` → `len=71 unique=70 ok=True fail_closed=False warnings=()`；② 实测 `qr.reconcile_snapshot(actual_ids=…)` 同签名；③ 对照实测 `engine_path=重复fixture` → `ValueError`（发现路径已封）；④ 通行路径对照：真实引擎 `discover_engine_segment_ids()` = 70 且唯一、`guard_completeness()` = `ok=True fail_closed=False observed=70` | 二选一（≤3 行 + 1 测试）：**(a) 补齐守卫**——在 :944-946 得到 `observed` 后统一 `duplicates = _duplicate_ids(observed)`，重复即抛 `ValueError`（与发现路径同构，并让 `reconcile_snapshot` 的 `actual_ids` 同样落检）；**(b) 收窄措辞**——把 :941 改为"经 `discover_engine_segment_ids` 取得的 census 不被本守卫报成 `ok`"，并在 docstring 明写"显式入参不做唯一性校验（调用方自守）"。**无论哪条**，MUST 补一条"显式 `observed_ids` 含重复 → 不得 `ok=True`"的负对照测试（现有 :705 只覆盖 `engine_path` 路径）。**窗口**：R0 已判定 F-2/F-3 须在 Slice-2 消费注册表前闭合，本项属同一窗口；建议 FEAT-026 开工前或紧随补丁轮落地，否则 MUST 由 Coordinator 登记遗留项 + 关闭截止日期 |
| **G-2** | P3 | 测试 `test_quickscan_registry.py`:140-160（判据）+ :112-126（白名单/禁名单）；对应守卫 :611-663 | F-1 的 AST 机判对"**间接 I/O**"无牙：模块级调用**本模块已定义函数**不被拦（`_X = _load_table()` → offenses `[]`），而 `_load_table()` 完全可以在函数体里 `read_text`。故 docstring :141 的"declarations with zero I/O / side effects"对"副作用"一词略宽（真实模块当前合规，:716 `_BY_ID = _index()` 属合法纯调用，故白名单不得不放行模块级 `Call`）。 | ① in-memory 注入实测：`_X = Path('x').read_text(...)` → 命中；`_X = _load_table()` → `[]`；`_X = _index()` → `[]`；类体 `X = open('y')` → 命中（类体确按导入期扫描，正确）；② 真实模块 `offenses == []`；③ 旧洞封闭的对照实测：in-situ 注入真实模块 → `line 998` 命中 | 可选（非阻塞）二选一：把模块级 `ast.Call` 的 `func.id` 限定为**已知纯函数白名单**（如 `{"_index","_id_sort_key"}`），其余模块级调用即 offense；或把 docstring 措辞降为"模块级**直接** I/O 与显式禁名调用"。**不重开 F-1**：R0 实证的洞是"扫描面截断"，已封闭（225→全 996 行） |
| **G-3** | P3 | 模块 `quickscan_registry.py`:842-847 | F-2 的 fail-closed 只覆盖"**零命中**"：`if not ids` 对**部分形态变化**不设防——混合引号块实测静默返回子集 `('31',)`（本应 25 段）。影响方向 = **过度披露**（`plugin_face_not_product_gated()` 会把更多插件面段报为"未 gated"），fail-safe 不损失覆盖，且 live 计数 25 由测试 :846 与 `excluded_ids()` 等值断言双重钉住。 | 实测三态：`'Check 7'` 单引号 → `ValueError`；仅锚点 → `ValueError`；混合引号 → `('31',)`（静默）；live → 25 / unique 25 / `== set(excluded_ids())` | 可选：若 Slice-2 直接消费该函数，把"非空"升级为**形状断言**（如 `len(ids) == 25` 或与冻结面 25 对账）；否则在 docstring 明写"保证非空，**不保证计数**"（当前 :831-834 只写了"结果为空即拒绝回答"，与实际一致，故仅属加强建议） |
| **G-4** | P3 | `.governance/evidence-log.md`:1953（EVD-998） | 证据记录的测试清点式**内部算术不自洽**："测试面 60→78（+19 新增+1 重写〔F-1〕+59 保留〔5 条 F-5 改名同步〕）"——19+1+59 = **79 ≠ 78**；"重写"项（`test_registry_declares_no_module_level_file_io` → `test_registry_module_body_declares_no_import_time_io`）已被计入 added 的 19 条内，属**重复计数**。正确分解 = **59 保留 + 19 新增（其中 1 条为 F-1 改写）→ 78**。影响：仅治理记录可复算性（与 R0 的 F-9 同类、同 P3 级别），无产品影响；`+5 条 F-5 改名同步`一项经核实**正确**（:253/:262/:278/:867/:880 共 5 处）。 | ① 重命名级 diff 实测：`removed=1 / added=19 / kept=59`；② `pytest` 收集 = 78；③ F-5 同步点机判计数 = 5 | 把该括号改为"59 保留 + 19 新增（含 F-1 改写 1 条）→ 78"（其余数字不动） |
| **G-5** | P3 | `.governance/evidence-log.md`:1953（EVD-998 的 "in-situ 证明…"）+ 测试 `:624`（落库负对照为**合成 7 行源**） | 核验等级/留痕口径：EVD-998 称 F-1 以"**in-situ** 证明（注入 `read_text` 后新判命中 L717）"，但**落库**的负对照 `test_module_level_guard_catches_the_false_green_counterexample` 使用的是合成源码（真实模块仅在 :611 做"0 offense + 三 token 存在"断言），该 in-situ 实验本身**未以测试形态入库**——事实为真但不可由 CI 复现（与 R0 对插桩实验"留痕未随交付入库"的同类备注）。**我独立复现了 in-situ**：对真实模块源码尾部注入模块级 `read_text` → `line 998: module-level .read_text()` ⇒ 声称的事实成立，仅留痕形态不同。 | ① 通读 :611-663 三用例：夹具为合成字符串；② 我实测 `_module_level_io_offenses(real_source + "\n_X = Path('x').read_text(...)")` → 命中 L998；③ EVD-998 原文措辞 | 可选（记录/测试加强）：把 in-situ 注入改写成一条测试（读真实模块源码 → 内存注入 → 断言命中），使"in-situ"进 CI 而非一次性实验；或把 EVD-998 措辞改为"in-situ 复核（开发期，非落库用例）+ 合成源负对照" |
| **G-6** | P3 | 模块 `quickscan_registry.py`:810-815（注释） | 讨论项：注释断言"a top-level ``def `` can never appear inside the (indented) docstring"是**本引擎修订版的事实属性**，不是语言保证（三引号串内允许零缩进行）。若未来引擎 docstring 出现列 0 的 `def ` 行，`start+1` 会提前终止扫描 → census 截断；**当前风险为零**且**有测试兜底**：实测 offset 1~7 结果恒等（`end=16444`）证明当前引擎无此形态；一旦截断，census 会失真为"stale 告警"，而 `test_live_census_holds_unique_ids`(:688) / `test_engine_discovery_yields_the_same_70_segments`(:227) 会立即 FAIL（非静默）。 | ① offset 1..7 等价实测；② `lines[14767]` 为 entry def，后续首个顶层 def 在 16444；③ 现有 census 70/70 与集合恒等断言 | 仅讨论，无需改动；若追求更稳，可把注释改为"（本引擎实测）docstring 各行均有缩进"，或断言"扫描区间内零 `def ` 行"作为附带不变式 |
| — | **P0** | — | **无 P0**（无安全漏洞、无数据损坏面、无逻辑错误；改名破坏性经消费者面核实为零影响） | §一/§二/§四 | — |

**汇总：P0 = 0；P1 = 0；P2 = 1（G-1）；P3 = 5（G-2~G-6）。** 全部为非阻塞发现：G-1 是 F-3 在第二入参路径上的**同族残存**（docstring 绝对措辞 + 显式入参未守），窗口与 R0 对 F-2/F-3 的"Slice-2 前修"一致；G-2/G-3 为守卫强度与措辞的**加强建议**；G-4/G-5 为治理记录精度与留痕形态；G-6 为注释普适性讨论。

---

## 六、验收标准逐条裁决（任务书 5 条）

| # | 验收标准 | 裁决 | 事实依据 |
|---|---|---|---|
| 1 | F-1~F-10 每条处置与上游 review 报告的发现对应且有效（修复真修复 / 不修有理由） | **PASS** | §二 10/10 逐条比对（含 hunk→finding 映射完备性核查）：9 条代码/文档侧**实证有效**（每条均有独立复现的行为证据），F-9 为治理记录侧"已完成并核实"（EVD-995 L1939 实测含"935 行…F-9 更正"与 F-2 措辞更正）。无一项"声称修复但未生效"，无一项"未修且无理由"；3 条残存/讨论项（G-1/G-2/G-3）已按级别登记 |
| 2 | 新增测试有牙（负对照真能抓）——重点 F-1 in-situ 证明与 F-3 反例转正 | **PASS** | **F-3 反例转正**：实测修前 `71/unique 70/ok=True/warnings=()` 逐字段复现 → 修后 `ValueError(['29'])`，且拒绝产出 `ok=True`（:693/:705 两用例）。**F-1**：正向 in-situ 复现成立（真实模块注入 → `line 998` 命中）；落库负对照（:624）可打穿旧实现并**同时证明旧 slice 的盲区**（断言旧扫描面仅到 docstring）。其余负对照逐条实测有牙（F-2 空解析 / F-7 诱饵 / F-8 错位 55 / F-10 错名 / F-6 未导出差集）。**限制**：F-1 的 in-situ 形态未入库（G-5，P3 记录项）；显式入参重复路径无负对照（G-1，P2） |
| 3 | F-3 选型合理性（抛错 vs 并入 undeclared——对照 §2.4 四态语义） | **PASS** | **抛错正确**，理由逐条成立：① §2.4 四态按"我们对这段知道了什么"定义（L103 原文），重复段号表示**观察本身不可信**，而非"注册表缺该段"——并入 `undeclared` 会把 `UNDETERMINED(原因)` 误标为 `NOT_RUN(排除原因代码)` 族语义（§2.4 L108/L110），并误导修复方向（去补表行 vs 去修引擎段落注释）；② §2.4 L110 对"注册表缺该段声明/输入未知"的规定动作是"**回退执行该段或回退 full**"，与抛错后由消费方映射"无裁决 → 回退 full"一致；③ §4.1 R5（L260）明文"Check ID 唯一…**零容忍（fatal）**"，而注册表侧已用导入期 `ValueError`（:719-720）——观察侧同构是**最低成本的一致性**；④ 选型即 R0 建议的**选项 a 原文**；⑤ 已实际排除选项 b 的语义污染（`undeclared` 语义保持"引擎有、表无"的纯覆盖缺口，:947 + docstring :937-941）；⑥ 消费侧义务已明示（docstring :940-941 + EVD-998"供 Slice-2 映射 undetermined→回退 full"）。**唯一要求**：该义务 MUST 进入 Slice-2 契约（异常 → undetermined → 回退 full），已在 G-1 一并提示 |
| 4 | 无新范围引入（diff 恰两文件，改动均可追溯至上游 findings） | **PASS** | 路径限定 `git diff --numstat` = **恰 2 文件**（72/11 + 325/10 = 397/21 ✅）；逐 hunk → F-1~F-10 映射完备，零无法追溯 hunk（§二末）；未改引擎（numstat 不含 `verify_workflow.py`、引擎零 `quickscan` 引用）、未改行 schema/70 行表本体、未新增依赖（产品模块 import 未变）、未新增 CLI/编排（§255 保持）。**环境澄清**：工作树另有 4 个 `M` 文件（`architecture-baseline.json`/`archguard_ratchet.py`/`contracts.py`/`test_contracts.py`）= **FIX-303 在飞**（经 Coordinator 转告确认），不属本审查面，未计入本批 diff |
| 5 | AI 专项 5 项 | **PASS** | mock 残留 / 硬编码返回值 / 幻觉 API / 未实现 TODO / 过度实现——逐项有结论 + 机判或实测依据（§三） |

**裁决汇总：5/5 PASS。**

---

## 七、硬门槛裁决

| 门槛 | 结果 |
|------|------|
| 1. 先核对两文件 hash 与冻结锚一致（漂移 → 中止上报） | ✅ **一致**（`4c34b001…` / `527d7754…`，审查开始与落盘前各复算一次相同；未发生中止条件） |
| 2. 逐行读 diff（+397/−21 全量） | ✅ 模块 83 行变更 + 测试 335 行变更逐 hunk 通读（非抽样），并对**每个 hunk 做了行为级独立核验**（§一 1.1 表） |
| 3. 5 维度逐一结论 | ✅ 正确性 / 安全性 / 可维护性 / 性能 / 测试覆盖 逐项有结论（§一） |
| 4. 与上游 `review-FEAT-025-CODE-R0.md` 的 F-1~F-10 逐条比对处置有效性 | ✅ 10/10 逐条裁决 + 映射完备性核查（§二） |
| 5. 结论（APPROVED / APPROVED_WITH_NOTES（含独立行 `unresolved_blockers=0`）/ NEEDS_CHANGE / BLOCKED） | ✅ 见 §八 |
| 附. 每条发现 P0~P3 + file:line + 事实依据 | ✅ G-1~G-6 全部标注级别 + 精确 file:line + 可复查命令/实测输出 |
| 附. AI 代码专项 5 项 | ✅ §三逐项有结论 |
| 附. 声称与事实交叉核对 | ✅ 5 条门禁声称 4 条独立复现、1 条采信（附静态论证）、**0 条被证伪**；另核 3 组处置矩阵明细声称全吻合（§四） |

---

## 八、审查结论

# APPROVED_WITH_NOTES

unresolved_blockers=0

**终态理由**：本批为 FEAT-025 R0（APPROVED_WITH_NOTES / unresolved_blockers=0）十项发现的**逐条处置**。经独立核验：**F-1（原 P1，假绿守卫）的洞已实质封闭**——AST 模块体机判替换文本截断，扫描面由"首 `def` 之前的 225/996 行"扩展到全部导入期语句，并以真实模块 in-situ 注入实测命中（`line 998`），旧 slice 盲区被逐项复现（`SEGMENTS`/`C3_ADJUDICATION`/`_BY_ID` 三者均不在旧面内）；**F-2（P2）**以"文本解析口径明示 + 空集 fail-closed"双落地，与兄弟函数 count 校验同族；**F-3（P2）**按 R0 选项 a 实现（`ValueError`，与注册表侧导入期守卫同构），R0 反例由"修前 71/unique 70/ok=True"经实测转为"修后 `ValueError`"；**F-4~F-8、F-10（P3）**逐条以"文档口径明示 + 机器可判固定物 + 负对照"闭环（F-5 改名经消费者面核实零影响，FEAT-022 71 例复跑绿）；**F-9（P3）**为 Coordinator 侧治理记录更正，已实测核实（EVD-995 含 935 行 + 非 AST 措辞更正）。5 条门禁声称 4 条独立复现为真（78 passed / 196 stmts·1 miss·99% / archguard-ratchet PASS·exit 0 / FEAT-022 71 passed）、1 条（全量回归）采信并附强静态论证（消费面 3 处、两条命令全覆盖），**无一条被证伪**；diff 恰两文件、逐 hunk 可追溯、无新范围引入；AI 专项 5 项无异常。**P0 = 0 且五条验收标准全 PASS** ⇒ 无未解决 BLOCKING finding，满足 code-review SKILL「循环角色」段的通过终态契约，故以 `APPROVED_WITH_NOTES` 结项并以独立结构字段声明 `unresolved_blockers=0`。

**发现计数（独立行，供机器记录）**：P0 = 0；P1 = 0；P2 = 1；P3 = 5。

**机器记录口径提示（沿用 FEAT-025 R0 先例）**：`unresolved_blockers=0` 在本报告中**独占一行且无附着细目**，以免与 provably-zero 探针（附着非零 P0/P1 计数即拒绝认证为零）冲突；P0/P1/P2/P3 计数写在独立行。

**本批通过后的处置要求（给 Coordinator）**：
- **G-1（P2）**：F-3 守卫在**显式 `observed_ids` 入参路径**上的同族残存（docstring 的"永不"措辞亦超出实现）。建议按 §五建议 (a) 或 (b) 在 **FEAT-026 开工前或紧随补丁轮**闭环（≤3 行 + 1 负对照测试）；若本轮不修，MUST 登记为遗留项并附**关闭截止日期**——理由与 R0 对 F-2/F-3 的"Slice-2 消费前必修"窗口一致，且本仓以"守卫必须能被负对照打穿"为标准，`ok=True` + 零告警的静默签名不应留存于公开入参。
- **G-2/G-3（P3）**：守卫强度与 docstring 措辞的加强项，可在任何后续补丁轮顺带处理（各 ≤5 行）。
- **G-4/G-5（P3）**：治理记录精度（EVD-998 清点算术、in-situ 留痕形态），由 Coordinator 决定是否更正记录或转成 CI 用例。
- **G-6（P3）**：纯讨论项，不需动作。

---

## 九、审查边界与残余未核验面（如实声明）

- **只读边界**：本轮**未修改任何产品代码或 `.governance/`**，除本报告外**未写入任何仓库文件**；`git status --porcelain` 全程为 6 个 ` M`、**零 `??`**；被审两文件 blob 在审查前后复算一致（未漂移）。
- **执行过写操作的仓外路径（披露）**：`%TEMP%\cov_fix304_review.dat`（coverage 数据文件，经 `COVERAGE_FILE` 显式重定向）；pytest/unittest 夹具自身的 `TemporaryDirectory()`（系统临时目录，`-B` + `-p no:cacheprovider` 确保仓内零产物）。
- **⚠ 采信项**：全量回归（声称 Ran 2580 / 32F+1E）**未复跑**——工作树含 FIX-303 在飞两文件，全量结果当前不可归属本批；替代证据 = 静态论证（全仓消费面仅 `registry.py` + 两测试文件）+ 两测试文件复跑绿（78 + 71）。
- **⚠ 污染披露**：`archguard-ratchet` 复跑为**混合树**结果（FIX-303 在飞 `archguard_ratchet.py` + `architecture-baseline.json`）；已附"该门禁不消费本批文件"的静态论证（零 `import quickscan_registry/registry`；R5 走 FEAT-020 extractors + 冻结快照；R1 只计 `verify_workflow.py` LOC；被审模块即便入 R2/R3/R4 面亦合规）。
- **❓ 未核验面（不写成事实）**：① F-3 选型对 Slice-2 编排器的**实际**影响（Slice-2 未建，本轮只核到"义务已在 docstring/EVD-998 明示"）；② F-1 的 in-situ 实验**原始留痕**（未随交付入库，我以独立复现替代，见 G-5）；③ lint（ruff/mypy）未运行——本轮未验证其安装状态，**lint 面仍属未验证**。

*审查边界声明：本报告全部结论均指向可复查事实（`git` 命令输出、两文件源码行号、`pytest`/`coverage`/`archguard-ratchet` 实跑输出、内存内省实测）。**无任何结论来自推测或采信性描述**；采信与未核验项已在 §四、§九显式标注。*
