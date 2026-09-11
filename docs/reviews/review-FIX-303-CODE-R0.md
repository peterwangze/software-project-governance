# Code Review: FIX-303-R0 — FEAT-021 R0 遗留批（F-1~F-13 逐条处置）

- **Task**: FIX-303（R0；上游依据 `docs/reviews/review-FEAT-021-CODE-R0.md` 的 F-1~F-13）
- **Reviewer**: Code Reviewer Agent（只读审查；不修改产品代码、不与用户交互）
- **Round**: R0（首次审查本批；无前轮报告，但**有上游报告逐条比对义务**）
- **审查对象**: **工作树 diff（路径限定 4 文件）**——审查前置于提交
  ```
  git diff -- skills/software-project-governance/infra/contracts.py \
              skills/software-project-governance/infra/tests/test_contracts.py \
              skills/software-project-governance/infra/archguard_ratchet.py \
              skills/software-project-governance/core/architecture-baseline.json
  ```
  `git diff --stat` 实测：**4 files changed, 361 insertions(+), 61 deletions(-)** —— 与声明恒等。
  行数实测：contracts.py 478→**528**、test_contracts.py 787→**1016**（`def test_` = **97**）、archguard_ratchet.py 1106→**1122**、architecture-baseline.json 3 处变更（`git_head` / `owner_task` / 新增 `infra/contracts.py` managed 条目）。
- **审查边界（重要）**：工作树另有并行未提交改动 `infra/quickscan_registry.py` + `infra/tests/test_quickscan_registry.py`（FIX-304 在飞）——**本审查全部 diff/核验命令均路径限定或仅针对本批 4 文件，未审查、未复跑 FIX-304 面**（见 §六 边界声明）。
- **可执行只读核验（FEAT-025 / FIX-304 R0 先例口径）**：本轮**执行了只读复跑命令**（测试/棘轮/差分/清单/覆盖率探针），逐条结果见 §三。未修改任何产品代码、未触碰 `.governance/`、未写除本报告外任何文件（唯一例外：coverage 数据文件按 `COVERAGE_FILE` 重定向至 `$TEMP` 并在同命令内删除）。

---

## 一、冻结锚核对（fail-fast，先于一切审查）

任务给出的 4 个锚值经核对**全部命中，无漂移**：

| 文件 | 声明锚值 | 实测 `git hash-object` | 字节数 | 行数 |
|---|---|---|---|---|
| `infra/contracts.py` | `23a7cc7c79d73743db1b1668c7d3caa3016e2159` | `23a7cc7c79d73743db1b1668c7d3caa3016e2159` ✅ | 22,158 ✅ | 528 ✅ |
| `infra/tests/test_contracts.py` | `b6bfdd5ded26dabdbe1c94841802140aed926482` | `b6bfdd5ded26dabdbe1c94841802140aed926482` ✅ | 44,930 ✅ | 1016 ✅ |
| `infra/archguard_ratchet.py` | `cf1fbcd699e332e3de4995190652b908b2a5f0eb` | `cf1fbcd699e332e3de4995190652b908b2a5f0eb` ✅ | 49,355 ✅ | 1122 ✅ |
| `core/architecture-baseline.json` | `f2d9731c4527b70051c8755b8ef72644889779d6` | `f2d9731c4527b70051c8755b8ef72644889779d6` ✅ | 14,445 ✅ | 552 ✅ |

**锚值口径说明（供 Coordinator 复用，避免误判漂移）**：该 4 值不是"文件裸字节 SHA1"，而是 **git blob SHA1**（SHA1 over `blob <len>\0<content>`）。以裸字节口径（`Get-FileHash -Algorithm SHA1` 与 Python `hashlib` 双双验证）实测得 `ebbf7020…` / `ef7b812e…` / `c4b2dc88…` / `84326ad0…`——**四者全部与声明值不同**，但 `git hash-object` 四者全部逐字命中，且字节数、行数、`git diff` 上下文 `index <old>..<new>` 中的新 blob 短号（`3b3e175..23a7cc7`、`d0c96f3..b6bfdd5`、`cf60ea6..cf1fbcd`、`0f70b20..f2d9731`）亦全部一致。⇒ **冻结点完整，审查可继续**；`architecture-baseline.json` 的 `git_head` 属易变字段，本轮以另 3 处语义变更（`owner_task`、新增 `infra/contracts.py` 条目、`git_head`）为准，均已逐一读 diff 核实。

---

## 二、5 个评审维度逐项结论

### 维度 1：正确性 — 通过（含 P1×1，见 §五 NF-1）

逐行读 `contracts.py` 全文 528 行（非抽样）+ 本批 diff 全量（+361/−61）。核心判定：

1. **不变式再实现（`_require_skip_consistent`，L260-272）逻辑正确**：单一异常源（`_fail` → `ContractViolation`），条件 `skipped is not None and passed is not True` 与改前内联版本**语义等价**（改前 L309-312 的 `if self.skipped is not None and self.passed is not True`），仅提取为共享辅助，消息文本逐字保留。
2. **`CheckResult.__post_init__`（L339-347）**：改为调用共享辅助，字段校验顺序（check→passed→findings→skipped→details→不变式）与改前一致，无序敏感副作用。
3. **`to_legacy_dict`（L349-381）复验顺序正确**：`passed`→`findings`→`skipped`→`details` 逐项复验，**先断言不变式、后构造 legacy 面**（L372 在 L373-377 之前）⇒ 矛盾载荷不可能产出 legacy dict。`skipped` 由局部变量承载后，L378-380 的写入与 L370 的复验同源（`self.skipped` → `skipped` 的替换**两处全部完成**，无残留读取 `self.skipped`）。
4. **`details` 隔离面正确**：`_require_mapping` 返回 `dict(value)` 新副本（L203），legacy 面写 `details["skipped"]`（L379-380）只污染副本；重复调用不累积（既有测试已 pin）。
5. **F-8 去参数（`unique`）行为无变化**：`_require_sequence` 去重逻辑改为恒执行，两处调用点改前均传 `unique=True`（grep 实测调用点恰 2 处：L435 `input_deps`、L442 `modes`，无任何 `unique=` 残留）⇒ 规格等价，仅删死分支。
6. **F-4 loader 放宽未引入越权面**：`_DOTTED_PATH_PATTERN` **未改**（仍要求 ≥1 个点段 ⇒ 根级名单段仍被拒），仅文案与语义定案（`<module>` 或 `<module>.<attribute>`）——放宽的是"末段是否可为属性名"，不改变路径形态约束（禁 `.py`/分隔符/盘符）。
7. **边界与空值**：`_require_optional_text` 对非 str/空白仍 fail-closed；`_require_bool` 的 tri-state（`pass: None`）提示保留完整（L206-218）。
8. **资源/并发**：模块纯数据、无 I/O、无共享可变状态、无时钟/文件句柄 ⇒ 无资源管理与并发面。
9. **唯一正确性缺口 = NF-1（P1）**：适配器对 `details` 采取**逐字透传**，而 `details["skipped"]`/`["skip_reason"]` 是适配器自用的披露键——当调用方 `details` 自带该键而 `self.skipped is None` 时，可产出"`pass=False` + `details["skipped"]=True`"的矛盾面，且按本批新 pin 的聚合约定会被引擎读作 SKIP（复现见 §五）。

### 维度 2：安全性 — 通过

- **无新增导入/无新增 I/O**：`contracts.py` 导入面与 `__all__` 本批零变化（导入白名单 AST 机判测试 `test_imports_are_the_allowlisted_stdlib_subset` 仍绿）；全文件仍无 `open`/`print`/`subprocess`/网络/时钟调用（禁名/禁属性 AST 机判仍绿）。
- **注入/ReDoS 面**：本批新增的扫描器（`_type_expression_values`/`_looks_like_type_union`）**只作用于 `ast` 节点**，非正则、非用户输入；`contracts.py` 的 3 条 `re.compile` 未变（import 期编译一次）。
- **凭据/敏感数据**：无密钥/token/密码字面量；无环境变量读取。
- **路径注入面**：`_require_loader` 仍拒 `.py`/`/`/`\`/`:`/根级名（负对照测试 `test_loader_rejects_paths_and_file_names` 保留全部 7 个坏例）⇒ F-4 的放宽**未**削弱形态约束。
- **权限/越权**：纯类型模块，无执行权、无 CLI（`test_module_has_no_cli_entry_point` 仍绿）。
- **测试侧真实环境接触**：新增测试仅构造内存对象与硬编码字符串；`test_contracts.py` 只读仓内 2 个文件（`contracts.py`、`contract_matrix/snapshots.json`）；无 `$HOME`/`$DSH_HOME`/仓库外路径、无写操作 ⇒ **破坏性红线不适用**（无隔离/备份/授权三选一义务）。

### 维度 3：可维护性 — 通过（含 P3×3：NF-2/NF-3/NF-4）

- **DRY 正向**：`_require_skip_consistent` 把"构造期 + 适配期"两处同一不变式收敛为**单一实现 + 单一消息源**，正是本次处置的收益点；命名/参数位次（`where` 首位）与 `_require_*` 家族一致。
- **文案一致性**：F-4 的 3 处口径（模块 L135-141 注释、类 docstring L410-415、报错文案 L455-458）经逐字比对**已统一**为"dotted module/handler path + module 或 module.attribute + 禁根级名"；F-1 的"唯一口径/唯一损耗"全称断言已按面限定。
- **注释质量**：新增/改写注释均**带测量来源与行号**（如 L39-42 引用 4 个 dict 消费方并给出行段），延续本仓"事实依据"文化；改后 docstring 明确把"层级 A/层级 B"与"提升约定"分开陈述，可读性优于改前。
- **函数长度/重复**：新增函数 6 行；无新增长函数；无复制粘贴式重复（唯一相似体 `engine_loop` 属测试侧引擎复刻，见 NF-3）。
- **可维护性风险（P3）**：NF-2（同一 diff 内两处 prose 仍指向已关闭任务）、NF-3（F-2 的引擎口径 pin 是无机判绑定的手写复刻）、NF-4（F-10 启发式的欠达面未在 docstring 披露）。

### 维度 4：性能 — 通过（无发现）

- 本批净增 **3 条可执行语句**（`_require_sequence` −4/+3、新辅助 def 函数体 +3、`__post_init__` −2/+1、`to_legacy_dict` +2 ⇒ 净 +3）。
- `_require_skip_consistent` = O(1)，每 result 调用 2 次（构造 1 次 + 每次适配 1 次）；`to_legacy_dict` 新增 1 次 `dict()` 浅拷贝 + 1 次 `_require_text` 检查 ⇒ 常数级。
- **无新增循环/无嵌套/无 I/O**；`_require_sequence` 的 O(n²) 重复检测为改前既有且 n ≤ 个位数（未变）；import 期成本零变化（无新 import，regex 未增）。
- 无 N+1、无 O(n²) 以上新增算法；无缓存/懒加载需求。

### 维度 5：测试覆盖 — 通过（含 P3×2，归属 NF-3/NF-4）

- **清点独立核实**：`def test_` 计数 = **97**（改前 87 + 新增 10；另有 3 个测试为**改名**而非新增：`test_loader_accepts_*`、`test_extra_has_no_slot_*`、`test_frozen_cli_keys_reconcile_*`）⇒ 「87→97」声明属实；实测 `Ran 97 tests ... OK`（exit 0）。
- **新增 10 例的覆盖性质逐条**：
  - characterization 类 ×4：嵌套别名（`test_extra_copy_is_top_level_only`、`test_details_copy_is_top_level_only`）、不可逆往返（`test_parenthesized_message_is_not_guaranteed_reversible`）、L0 不校验相对性（`test_file_relativeness_is_not_validated_by_l0`）；
  - 负对照（守卫有牙）×4：突变后不变式被拒（`test_adapter_refuses_mutated_skip_invariant`，2 例）、全量序列化字段突变的 4 路循环（`test_adapter_revalidates_every_serialized_field`）、py39 放宽扫描的**不误报**对照（`test_type_union_heuristic_does_not_flag_plain_bitwise_values`，2 例）；
  - 正对照（真能抓）×3：`test_checker_detects_pep604_union_alias_outside_annotations`、`..._with_class_operands`、`test_adapter_output_is_the_level_a_result_dict_not_a_label_block`（双态 pin：陷阱态 + 约定态）；
  - 恒真断言替换 ×1：`test_frozen_cli_keys_reconcile_with_the_frozen_face_counts`。
- **有牙性独立验证（见 §三 第 6 项）**：F-10 的两个正对照输入在**改前检测器的扫描面内不存在任何节点**（`_annotation_nodes` 对其产空）⇒ 改前必然红 ⇒ TDD 红为真；F-3 的两个负对照输入在改前代码路径上**不抛异常**（改前无 `skipped` 复验、无适配期不变式断言）⇒ 改前必然红。
- **覆盖率**：`contracts.py` **164 stmts / 0 miss = 100%**（独立复跑命中，见 §三 第 5 项）；口径机制已实证（§四）。
- **覆盖缺口**：NF-3（引擎读取口径的 pin 为手写复刻，与 `verify_workflow.py` 之间无机判绑定）、NF-4（py39 启发式的欠达形态未披露）。
- 未发现"为通过而写"的空断言：本批**删除**了一条恒真断言（F-11）并**新增强度更高**的三方对账，方向正确。

---

## 三、独立核验结果（本轮实际执行的只读命令）

| # | 核验项 | 命令（绝对/仓根相对路径） | 实测结果 | 与声明比对 |
|---|---|---|---|---|
| 1 | 目标测试套件 | `python -m unittest discover -s skills/software-project-governance/infra/tests -p "test_contracts.py" -v` | `Ran 97 tests ... OK`，exit 0 | ✅ 97/97 OK 属实 |
| 2 | 架构棘轮（fatal gate） | `python skills/software-project-governance/infra/verify_workflow.py archguard-ratchet` | `Result: PASS (0 violations)`；R1 `24329 ≤ 24329`；R2 `46 ≤ 46`（36 files）；**R3 `managed 2 modules, 0 edges, SCC max 1`**；R4 `1310 ≤ 1310`；R5 `cli keys 82/82, segments 70/70`；R6 `196 Δ0`；**R7 `deterministic=True; committed==fresh True`**，exit 0 | ✅ R3 managed 2 / R7 双真 / R2 46≤46 全部属实 |
| 3 | 契约矩阵差分 | `python skills/software-project-governance/infra/contract_matrix/generator.py --check` | `contract matrix: current implementation matches snapshot (4 faces, zero drift)`，exit 0 | ✅ 零漂移属实 |
| 4 | 清单一致性 | `python skills/.../infra/verify_workflow.py check-manifest-consistency` | `Canonical files: 644 / Actual files: 716 / [PASS]`，exit 0 | ✅ manifest PASS 属实 |
| 5 | 覆盖率 | `COVERAGE_FILE=$TEMP/... python -m coverage run -m unittest ... -p "test_contracts.py"` → `coverage report --include="*contracts.py"` | `contracts.py  164  0  100%`（coverage **7.13.5** with C extension） | ✅ 164/164=100% 属实；机制见 §四 |
| 6 | 新测试"有牙"性 | in-memory 探针（`import test_contracts` 后调用 `_annotation_nodes` / `_python39_problems`） | `Alias = str \| None` 与 `Alias = Record \| None` 的 annotation 节点数 = **0**（改前检测器必红）；两个负对照返回 `[]`；经典注解形态仍被标记 | ✅ TDD 红为真、无误报、无回归 |
| 7 | F-11 对账算术 | in-memory 读 `contract_matrix/snapshots.json` | `key_count=82`、`handler_count=79`、`alias_groups` 3 组 / 6 键 ⇒ 79−3=76，76+6=**82** ✅；键唯一 ✅；字段名 `key_count/handler_count/alias_groups` 均真实存在 | ✅「82==79−3+6」逐项复现 |
| 8 | F-2 引擎读取口径 | 读 `verify_workflow.py` L20590-20634 与 L7280-7297 | L20613-20614 `for label, detail in result["details"].items(): if detail.get("skipped"):` —— `detail` **就是 label 块自身**；L7285-7297 把 `pass/skipped/skip_reason` 建在该块**顶层** | ✅ 见 §四（判定：开发者实证成立） |
| 9 | F-1 引用 4 处 | 读 `verify_workflow.py` L14815-14844 / L22434-22445；`checks/review_domain.py` L208-227；`tests/test_verify_workflow.py` L9357-9366 | L14824 `if issue["type"] ==` … L14825 `issue["detail"]` … 至 L14838 ✅；L22439 `issue.get("type", "issue")` ✅；`review_domain.py` L213-221 恰为 7 键 dict（type/file/line/text/severity/pattern/fix）✅；`test_verify_workflow.py:9364` `{issue["type"] for issue in result["issues"]}` ✅ | ✅ 4 处全部实在，且 L14824 比上游 L14821 **更精确** |
| 10 | F-8 死参数清除 | grep `_require_sequence` | 定义 1 处 + 调用点恰 2 处（L435/L442），无 `unique=` 残留 | ✅ 无调用点遗漏 |
| 11 | 并行改动隔离 | `git status --porcelain` + 路径限定 diff | 工作树在飞 6 文件；本批 diff **恰 4 文件**（quickscan 2 文件属 FIX-304，未纳入） | ✅ 无范围外改动 |
| 12 | lint 声明 | `Get-Command ruff/mypy/pyflakes/flake8/pylint` | 五者**全部 NOT INSTALLED** | ✅「lint NOT_RUN（五工具实证未安装）」属实 |
| 13 | 全量回归 | `python -m unittest discover -s .../infra/tests -p "test_*.py"` | 见 §三附注（全量套件结果） | 见附注 |

**附注 — 全量套件与并行改动混杂声明**：本轮启动的全量套件 `-p "test_*.py"` 会在**包含 FIX-304 在飞改动**（`quickscan_registry.py` / `test_quickscan_registry.py`）的工作树上运行，因此其任何失败**不能单独归因于本批**；本批 4 文件的判定以第 1~7 项路径限定核验为准（`test_contracts.py` 与 4 文件中的 3 个 Python 文件均已被第 1、2、3、5 项直接覆盖）。

---

## 四、三项关键实证（决定验收标准 2/3/4 的独立核验）

### 4.1 F-2：引擎读取口径实证 —— **开发者的"前提更正"成立且正确**

上游报告 F-2 的建议选项 (a) 是：「明确并文档化聚合约定『每个 CheckResult 的 legacy dict 嵌于 `details[<label>]` 之下』→ **现状即正确**，补一条 pin 该嵌套的测试」。开发者主张该选项的**前提是错的**：嵌套后引擎读不到 skip。独立核验：

- **构建点**（`verify_workflow.py` L7285-7297，逐行读取）：
  ```python
  details["dsh_upgrade_regression"] = {
      "pass": not dsh_regression_issues,
      "skipped": dsh_regression_skipped_reason is not None,
      "skip_reason": dsh_regression_skipped_reason,
      ...}
  ```
  ⇒ `skipped`/`skip_reason` 建在 **label 块自身顶层**。
- **消费点**（同文件 L20613-20621，逐行读取）：
  ```python
  for label, detail in result["details"].items():
      if detail.get("skipped"):
          print(f"  [SKIP] {label.replace('_', ' ')} — "
                f"{detail.get('skip_reason')}")
          continue
      status = "PASS" if detail["pass"] else "FAIL"
      print(f"  [{status}] {label.replace('_', ' ')}")
  ```
  ⇒ `detail` **即** `details[label]`；读取面比适配器输出**浅一层**。
- **失败模式的完整形态（本审查补充的、比开发者表述更严重的一步）**：若把适配器 dict（键恰为 `pass`/`issues`/`details`）当作 label 块嵌入 `details[label]`，则 `detail.get("skipped")` 取到 `None`（适配器输出顶层无该键）⇒ 不进 SKIP 分支 ⇒ 落到 L20622 `status = "PASS" if detail["pass"] else "FAIL"`。而 skip 态必有 `passed=True`（`_require_skip_consistent` 保证）⇒ **该 check 被渲染为 `[PASS]` 且完全无披露**——不只是"披露丢失"，而是 **skip 静默变 PASS**。开发者的定案描述（"嵌套会让 skip 静默变 PASS"）**属实且方向正确**。
- **独立复现**：新 pin 测试的陷阱半段（`test_adapter_output_is_the_level_a_result_dict_not_a_label_block`）以本地复刻的引擎循环实测 `engine_loop(trapped) == []`（披露为空）而 `trapped` 的 `pass=True` —— 与上面的静态推导一致；约定半段（把两键提升到 label 块顶层）实测得 `[("the_label", "BR-4 released-history query")]` ✅。
- **结论**：F-2 的处置（**保持冻结 3 键 + 文档化"提升到 label 块顶层"约定 + 双态 pin**）是三条路线里**唯一同时满足 §3.7 冻结语义与引擎读取事实**的方案；上游选项 (a) 若采纳会引入静默 PASS。**该处置正确**（残余风险见 NF-3）。

### 4.2 F-5 / F-6：棘轮与基线变更正确性（可复跑，已复跑）

- **F-5（R3 入册）**：`archguard_ratchet.py` 的 `DEFAULT_MANAGED_MODULES`（L114-123）与 `core/architecture-baseline.json` 的 `r3_layer_matrix.managed_modules["infra/contracts.py"]`（`admitted_by: "FIX-303"`, `layer: "L0"`）**双写**，两处 note 文本一致；机判复跑 **R3 PASS：`managed 2 modules, 0 edges, SCC max 1`**。因 `contracts.py` 零内部出边（既有 AST 机判 + 本批零 import 变更共同固定），入册只会增加一个干净 L0 节点——**不可能引入层间违规**，与 note 陈述一致。
  **附带正收益（独立核实）**：设计文档 `docs/requirements/architecture-evolution-0.80.0.md` §10 L516 的验收门原文为「契约层零 I/O 零内部依赖（**R3 判定**）」——在入册后该措辞**已由机器门真实兑现**（复跑 R3 覆盖该模块），即上游 F-5 指出的"措辞与机器覆盖面不符"缺口**从根上消除**，而非仅改措辞。
- **F-6（owner 转记）**：`_OWNER_TASK_MAP` 的 `("contract_matrix/", "REFACTOR-contract-layer")` → `("contract_matrix/", "FIX-303")`，并同步 `architecture-baseline.json` 的 R2 条目。本审查直读 JSON 核实：`{"count": 1, "kind": "import_vw", "lines": [51], "owner_task": "FIX-303", "path": "contract_matrix/generator.py"}` ✅（债务未消失、责任人已换为在办任务）。
  **单一事实源核实**：基线中的 `owner_task` 是**派生值**——`archguard_ratchet.py` L801 `"owner_task": _owner_task_placeholder(path)`，而 `_owner_task_placeholder`（L142-143）只从 `_OWNER_TASK_MAP` 取 ⇒ 开发者选择"改映射 + regen"而非手编提取区是**正确做法**（手编会被 regen 回退）；机判复跑 **R7 `deterministic=True; committed==fresh True`** ⇒ 提交态 == 重生成态，无手编漂移。**R2 `46 ≤ 46`** 单调不减 ✅。
- **R2 政策边界（如实披露）**：R2 只要求"基线长度单调不增"，故 `generator.py` L51 的违规**本轮未消化**（设计如此，`generator.py` 不在 4 文件 diff 内）。风险（"任务关闭后债务失去责任人"）由 owner 转记到 FIX-303 化解；但见 NF-2 的 prose 残留。

### 4.3 F-12：覆盖率"100%"定案的排除机制 —— **成立，且"Protocol 无关"属实**

独立实证（不是采信，而是复现）：

1. **复跑数字**：`contracts.py **164 stmts / 0 miss = 100%**`（coverage 7.13.5 with C extension）——与开发者"改动后 164/164=100%"恒等。
2. **机制定位**：`coverage/parser.py` L124-133 + L276-278 的语句集 = `raw_statements − (excluded ∪ raw_docstrings)`。实测 `analysis2()`：`statements=164, excluded=31, missing=0`，且**8 个 Protocol 方法体 `...`（L491/499/502/509/512/515/518/528）全部落在 `excluded` 内**（31 行 = 8 个 `...` 体 + 8 条 def 签名行 + 相邻空行，由多行匹配 `^\s*` 的 `\s` 可跨行所致）。
3. **排除来源（决定性）**：来自 coverage **内置默认排除表** `coverage.config.DEFAULT_EXCLUDE`（3 条），其中第 2 条为
   ```
   ^\s*(((async )?def .*?)?\)(\s*->.*?)?:\s*)?\.\.\.\s*(#|$)
   ```
   即 **"函数体仅 `...` 即整体排除"** 的 stub 体排除。**不是** `Protocol` 专属规则（该默认表内**无任何 Protocol/abstractmethod 模式**，实测 dump 已核）。
4. **"Protocol 无关"的对照实验**（in-memory，零文件写入）：以同一默认模式复刻 `lines_matching` 后实测——Protocol 方法体 ✅ 被排除、**普通类方法体** ✅ 被排除、**模块级自由函数体** ✅ 被排除、单行 `def f(x) -> int: ...` ✅ 被排除，而 `TOP = ...`（非函数体）❌ 不排除 ⇒ **排除面由"函数体仅 `...`"决定，与 `Protocol` 无关**：开发者的机制陈述**成立**。
5. **"改动前 161" 的算术佐证（本审查独立推导）**：逐条清点本批语句增量 —— `_require_sequence` −4/+3 = **−1**；新 `_require_skip_consistent`（def + `if` + `_fail`）**+3**；`__post_init__` −2/+1 = **−1**；`to_legacy_dict` +2（`skipped = _require_optional_text(...)` 与 `_require_skip_consistent(where, passed, skipped)`）⇒ **净 +3**，即 **161 + 3 = 164**，与"改动前 161/0 miss、改动后 164/164"**自洽**。
6. **残余口径提示（见 NF-5）**：该 100% 依赖 coverage **版本内置默认**排除表；仓内**无** `.coveragerc`/`setup.cfg`/`tox.ini`，`pyproject.toml` 内**无** coverage 配置（已实测无匹配）⇒ 该数字**不可从仓内配置复现**，属"一次性测量 + 工具默认语义"。

---

## 五、发现汇总（P0~P3 + 位置 + 事实依据 + 建议）

| # | 级别 | 位置（file:line） | 问题与影响 | 事实依据 | 修复建议 |
|---|------|------------------|------------|----------|----------|
| **NF-1** | **P1** | `contracts.py`:328-330（措辞）、L371-380（实现）；pin 约定见 `test_contracts.py`:589-596 | F-3 修复**只关闭了 `skipped` 属性通道**，`details` 通道仍可产出**自相矛盾的 legacy 面**，而改后 docstring 声称复验覆盖"**every field it serializes** — passed/findings/skipped/details, **including the skip invariant**"。适配器**逐字透传** `details`，同时又**自用** `details["skipped"]`/`["skip_reason"]` 作披露键 ⇒ 保留键未被强制。可达路径（无需构造后突变）：`CheckResult(check=..., passed=False, findings=[], details={"skipped": True, "skip_reason": "x"})` → `to_legacy_dict()` 产出 `{"pass": False, "issues": [], "details": {"skipped": True, "skip_reason": "x"}}`；按本批**新 pin 的聚合约定**（`test_contracts.py`:589-596 由 `"skipped" in legacy["details"]` 派生 label 块 `skipped`），`verify_workflow.py` L20613-20621 会读作 `[SKIP] the_label — x` 并 `continue` ⇒ **一个 FAIL 被静默披露为 SKIP**（与 FIX-270 WARN 语义相反的方向）。影响面：当前**零在产消费方**（registry/L4 接线为后续切片），故不阻塞；但该措辞会随证据进入后续切片的可信前提 | ① 实测复现（本轮执行）：构造上述对象**不抛异常**，`to_legacy_dict()` 输出含 `pass=False` 且 `details["skipped"]=True`；按 pin 约定提升后引擎视图实测为 `[('the_label', 'injected')]`（FAIL → SKIP）② 仓内 `details` 根出现 `skipped` 键的既有先例：`archive.py`:2671/2838、`loop_exit_bridge.py`:200-209（上游 F-2 同一实证）③ 适配器自用该键：L379-380 ④ 措辞：L328-330 / L362-365 ⑤ F-3 已闭通道：`_require_skip_consistent`（L260-272）+ 负对照 `test_contracts.py`:711-732 | 二选一（首选 a，成本最小）：**(a)** 在 `to_legacy_dict` 内**强制保留键语义**——`skipped is None` 时从输出副本中移除/拒绝 `details` 携带的 `skipped`/`skip_reason`（或对二者做一致性校验），并补一条负对照（`passed=False` + `details` 自带 `skipped` ⇒ 要么 `ContractViolation`、要么输出中无该键、要么输出 `pass=True`）；**(b)** 保留逐字透传但**收窄措辞**：在类 docstring 明写"`details["skipped"]`/`["skip_reason"]` 为适配器保留键，调用方 `details` 携带同键将被原样透传且不参与不变式校验"，并把"including the skip invariant"限定为"对 `skipped` **字段**" |
| **NF-2** | P3 | `archguard_ratchet.py`:110-112（`infra/archguard_ratchet.py` 条目 note）；`core/architecture-baseline.json` → `r3_layer_matrix.managed_modules["infra/archguard_ratchet.py"].note`（同文本） | F-6 的 prose 面**未同步**：同一 diff 内，新条目 note 写"contract_matrix/generator.py stays unmanaged **until its own slice**"，而另两处 note 仍写"**(unmanaged until REFACTOR-contract-layer admits it)**"——`REFACTOR-contract-layer`（FEAT-021）已关闭且该债务已转记 FIX-303 ⇒ 同一事实在同一 diff 内出现两种互相矛盾的表述，后续读者会追到一个已关闭的任务 | ① 本批 diff 未修改的上下文行 `archguard_ratchet.py`:111-112；② 基线 JSON 实测 note 原文（含 "unmanaged until REFACTOR-contract-layer admits it"）；③ 新条目 note 原文（含 "until its own slice"）；④ R2 `owner_task="FIX-303"`（JSON 实测） | 把两处 note 的 "until REFACTOR-contract-layer admits it" 改为"until its own slice (owner FIX-303, F-6 转记)"；因 `owner_task` 由 `_OWNER_TASK_MAP` 派生（L801），改 note 后需 regen 保持 R7 双真 |
| **NF-3** | P3 | `test_contracts.py`:583-596（`engine_loop` 局部复刻）；对应引擎 `verify_workflow.py`:20613-20621 | F-2 的核心 pin（层级 A/层级 B 不可互换）以**手写复刻**的引擎循环表达，与 `verify_workflow.py` 之间**无任何机判绑定**：若引擎读者改为读 `details[label]["details"].get("skipped")`、或改为两级兼容，测试与模块 docstring 的"提升约定"会**同时静默过期**，而仓内不会有任何红灯。影响面：属"pin 可能失效"的长期风险，非当前缺陷（引擎读取口径本轮已由本审查逐行核对属实） | ① 复刻体位置与 docstring 自述"``verify_workflow.py`` L20613-20621 caliber, verbatim"；② 测试文件已有读仓内文件先例（`SNAPSHOT_PATH`，L41）；③ R1 冻结引擎行数（`24329 ≤ 24329`，只降不增）⇒ 引擎改动是**刻意**行为，漂移可被人工发现但不会被机判拦截 | 可选加固（非必须）：在该测试内增加一条**源级绑定**断言（读 `verify_workflow.py` 并断言读者形态存在，或把引擎 blob 短号写进断言/docstring）；若不做，则至少在 docstring 标注"引擎行号随 R1 变更需同步复核" |
| **NF-4** | P3 | `test_contracts.py`:142-160（`_looks_like_type_union`） | F-10 的启发式**欠达面未披露**：`Alias = my_type | None`（操作数为小写非内建名）会被 `if not leaf.id[:1].isupper(): return False` 直接判为"值表达式"而不报警——而该形态在 py39 上同样 `TypeError`，恰是守卫要防的一类漂移。属**有意识权衡**（否则无法与 `combined = left | right` 区分），但 docstring 只说明"看起来像类型联合"，未写明残留下界 | ① 判定分支 L158-159；② 两个负对照 `test_contracts.py`:938-946（`MASK = 1 | 2` / `combined = left | right`）证明权衡必要；③ py39 语义：`type.__or__` 于 3.10 引入，3.9 上 `ClassX | None` 抛 `TypeError` | 在 `_looks_like_type_union` docstring 补一句残留下界（"小写非内建名操作数一律不判为类型联合——`Alias = my_type | None` 形式不在检测面内"）；如需覆盖，可只在**模块级**赋值中放宽（该层无局部变量，误报面显著更小） |
| **NF-5** | P3 | 口径记录面（非代码缺陷）：`pyproject.toml` 无 coverage 配置、仓内无 `.coveragerc` | F-12 的 **100%** 判定依赖 coverage **内置默认排除表**（版本相关）；仓内**无**任何配置 pin 该口径，也无 3.9/3.10 差异说明 ⇒ 该数字**不可从仓内配置复现**，且未来 coverage 升级改动 `DEFAULT_EXCLUDE` 时数字会静默变化（本仓无覆盖率门禁，不会报警） | ① 实测 `DEFAULT_EXCLUDE` 3 条（含 ellipsis stub 模式）② `pyproject.toml` 无 coverage 键（grep 零命中）；无 `.coveragerc`/`setup.cfg`/`tox.ini` ③ 复跑数字随工具默认语义得出 | 随本轮证据**记录机制与版本**（"coverage 7.13.5 内置 ellipsis-stub 排除，Protocol 无关，164/164"）即满足 F-12 的复跑要求；如要长期稳定，再考虑加最小 `[tool.coverage]` 配置 pin（本审查不要求本轮做——加配置会改变门禁语义，需独立 DEC） |

**汇总：P0 = 0（无阻塞项）。P1×1 / P2×0 / P3×4。** 4 条 P3 中，NF-2 属本批同一 diff 内的表述自相矛盾（**建议本轮顺手修**，成本 ≤ 2 行 + regen）；NF-3/NF-4 为可遗留的加固/披露项；NF-5 为证据记录口径。

---

## 六、上游 F-1~F-13 处置逐条裁决（验收标准 1；第 2/3/4 项见 §四）

| 上游 finding | 级别 | 处置落点（本批 diff） | 独立核验 | 裁决 |
|---|---|---|---|---|
| **F-1** 口径全称断言 | P1 | `contracts.py`:36-48（按面限定 + 删"single documented field loss"）；caliber 3 L62-66 限定；`test_contracts.py`:10-13 + 测试改名 `test_extra_has_no_slot_in_the_legacy_issue_string`（:686-694） | 4 处 dict 消费方**逐处读源码命中**（L14824/L22439/`review_domain.py` L213-221/`test_verify_workflow.py`:9364）；引用行段比上游更精确；全称断言已消失 | ✅ **有效** |
| **F-2** skip 披露位置 | P2 | `contracts.py`:49-61（"not verbatim" + 提升约定）+ 双态 pin `test_contracts.py`:558-602 | **引擎口径实证属实**（§4.1）：嵌套 ⇒ 不看"披露丢失"，还会因 `detail["pass"]=True` 被渲染成 `[PASS]`；开发者对上游选项 (a) 的前提更正**正确** | ✅ **有效（且纠正了上游方案）** |
| **F-3** 复验漏 `skipped` | P2 | 共享辅助 `contracts.py`:260-272；两处消费 L347/L372；2 条负对照 + 4 路突变循环 `test_contracts.py`:711-732；措辞 L328-330 | 实测：构造后 `passed=False` + 残留 `skipped` ⇒ 抛 `ContractViolation`（含 `skipped`/`passed=True`/`FIX-270` 三 needle）；`skipped=3` ⇒ 抛；4 个序列化字段逐一被拒 | ✅ **有效**（残余见 NF-1） |
| **F-4** loader 口径歧义 | P2 | 定案 (b)：`contracts.py`:135-141 / L410-415 / L455-458 三处统一；`test_contracts.py`:768-785 | 三处文案一致；`_DOTTED_PATH_PATTERN` 未放宽根级名约束；正/负两侧均有测试（`test_loader_rejects_paths_and_file_names` 保留 7 坏例） | ✅ **有效（定案清晰）** |
| **F-5** R3 未管辖 | P2 | 入册：`archguard_ratchet.py`:114-123 + baseline `r3_layer_matrix.managed_modules["infra/contracts.py"]`（admitted_by FIX-303） | 复跑 **R3 PASS：managed 2 / 0 edges / SCC 1**；设计 §10 L516「R3 判定」**由机器门真实兑现**；零出边 ⇒ 不可能引入违规 | ✅ **有效（超上游建议：真入册而非改措辞）** |
| **F-6** R2 owner 转记 | P2 | `_OWNER_TASK_MAP` `contract_matrix/` → `FIX-303`（L138）+ baseline R2 条目 owner_task | JSON 实测 `owner_task="FIX-303"`；**R7 `committed==fresh True`**（映射为单一事实源、无手编漂移）；**R2 46 ≤ 46** | ✅ **有效（机器面）**；prose 残留见 NF-2 |
| **F-7** 浅拷贝措辞超实现 | P2 | `contracts.py`:282-290（Finding.extra）、L352-360（details）；characterization `test_contracts.py`:378-390、:604-611 | 两处措辞已明确"top-level shallow copy … never deepcopy"；两测试以 `is` 恒等 + 穿透突变真实 pin 嵌套别名（非空断言） | ✅ **有效** |
| **F-8** 死参数 `unique` | P3 | `contracts.py`:221-244（删参 + 去重恒执行）；两调用点 L435/L442 | grep 实测调用点恰 2 处、无 `unique=` 残留；两处改前均传 `True` ⇒ 行为等价 | ✅ **有效** |
| **F-9** `Finding.file` 相对性 | P3 | 字段级注释 `contracts.py`:295-296；characterization `test_contracts.py`:348-356 | 注释明确"L0 不校验相对性，由解析/渲染方负责"；测试 pin 3 种越界形态（`C:\x\y.md` / `/abs/x.md` / `../../escape.md`）均被放行（即"如实记录缺口"） | ✅ **有效** |
| **F-10** py39 守卫覆盖面 | P3 | `contracts.py` 无关，`test_contracts.py`:122-188（`_type_expression_values` + 启发式 + 扩面判定）+ 2 正对照 :933-945 + 2 不误报对照 :938-946 | **有牙性实证**：两正对照输入在改前注解面内**零节点** ⇒ 改前必红（TDD 红为真）；负对照返回 `[]`；经典注解形态仍被标记（无回归） | ✅ **有效（有牙）**；残留下界见 NF-4 |
| **F-11** 恒真断言 | P3 | `test_contracts.py`:965-986（三方对账替换 `isinstance`） | 算术独立复现：`82 == 79 − 3 + 6` ✅；键唯一 ✅；快照字段名 `key_count/handler_count/alias_groups` 真实存在（无幻觉 API） | ✅ **有效（强度高于上游建议）** |
| **F-12** 覆盖率定案 | P3 | 复跑 + 机制定位（本轮独立复现） | 164/164=100% 命中；排除机制 = coverage 内置 ellipsis-stub 模式（**Protocol 无关**，对照实验证实）；"161→164" 与净 +3 语句自洽 | ✅ **定案成立**；口径记录见 NF-5 |
| **F-13** 往返前提 | P3 | 往返测试 docstring `test_contracts.py`:641-647 + 不可逆 characterization :674-684 + 注释 :64-68 | 前提已写明；新测试以具体消息 `over budget (columns=5)` 展示被误读为 `file=columns=5`，断言 `match.group("file") == "columns=5"` 有牙（非恒真） | ✅ **有效** |

**覆盖率判定：F-1~F-13 共 13 条，逐条有对应落点、逐条经独立事实核验为"有效"；无一条未处置、无一条处置落点与 finding 不匹配。**
**范围判定（验收标准 6）**：diff 恰 4 文件、361/-61；4 文件的每一处改动均可追溯到上表某条 finding（或为其派生的一致性同步：caliber 3 的限定措辞、`_LEGACY_ISSUE_RE` 注释、测试改名）——**无范围外功能、无顺手重构、无新增公开 API**（`__all__` 未变，唯一新增符号为私有 `_require_skip_consistent`）。

---

## 七、AI 专项 5 项（逐项结论）

| 项 | 结论 | 依据 |
|---|---|---|
| **mock 残留** | **无 mock**（1 处**测试侧引擎复刻**已披露并单列 NF-3） | `contracts.py` 零测试替身；新增测试唯一的"模拟物"是 `test_contracts.py`:583-586 的 `engine_loop` 局部函数——它复刻的是**被引引擎读者**（非被测对象 SUT 的替身），且 docstring 自述来源与行号（合法做法，风险已记为 NF-3） |
| **硬编码返回值** | **无欺骗性硬编码**；本批**反向改善** | 删除了 1 条恒真断言（F-11）并换成三方对账；正对照的期望值来自被引事实（引擎行号、快照字段）而非硬编造；`contracts.py` 无 `return {"pass": True}` 类捷径，全部字段源自 `self.*` |
| **幻觉 API** | **无** | 本批新增用到的外部面仅：`ast.walk/Assign/AnnAssign/BinOp/BitOr/Name/Constant`、`dict.get/set`、`json.loads`、快照键 `key_count`/`handler_count`/`alias_groups`/`keys`（**逐键实测存在**）、`c.CommandKey`（`is str` 别名，真实）；无任何不存在的库/方法调用 |
| **未实现 TODO** | **无** | 3 个 Python 文件 grep `TODO/FIXME/XXX/HACK/type: ignore/noqa`：新增行**零命中**；既有命中（`archguard_ratchet.py`:180/527/537/538/562、`test_contracts.py`:38 的 `# noqa: E402`）**均在本批 diff 之外**（diff 仅触及 ratchet L99-138） |
| **过度实现** | **无实质过度**（1 项可接受的设计外扩面） | §3.6 外新增仅私有辅助 `_require_skip_consistent`（F-3 直接要求，DRY 收益明确）；测试侧 `_type_expression_values`/`_looks_like_type_union`/`_TYPE_LIKE_NAMES` 属 F-10 明确要求的扩面，并自带 2 正 + 2 负对照（超上游最低要求但可辩护）；`_require_sequence` 是**删参数**（收窄）而非扩面 |

---

## 八、硬门槛裁决

| 门槛 | 结果 |
|------|------|
| 冻结锚核对（漂移即中止） | ✅ 4/4 命中（git blob 口径 + 字节数 + 行数三重一致，见 §一） |
| 逐行读 diff（+361/−61 全量）+ 受影响文件全文 | ✅ diff 全量逐行；`contracts.py` 528 行**全文**逐行；`test_contracts.py` 新增/改动段落全量 + 辅助机具（L60-189、L768-797 等）逐行；`archguard_ratchet.py`/`architecture-baseline.json` 改动段全量 + 基线 R2/R3 节点结构化直读 |
| P0 阻塞问题数 = 0 | ✅ 0（5 条发现中无 P0） |
| 5 维度全覆盖 = 100% | ✅ 正确性/安全性/可维护性/性能/测试覆盖逐项有结论（§二） |
| 每条发现标注级别 = 100% | ✅ NF-1~NF-5 全部标注 P1/P3 + file:line + 事实依据 + 修复建议 |
| 设计一致性检查已完成 | ✅ §3.6（字段/端口/CheckSpec）、§3.7（键集/适配器/不加必填键）、§8.1 类 3（元素口径与黄金样例指引）、§4.1 R3（层间矩阵与入册）、§9.1（loader 白名单与 import 期约束）、§7.2（记录模型占位）、§10 L516（验收门「R3 判定」现由机器门兑现）逐项比对 |
| AI 代码专项 5 项检查 | ✅ mock 残留/硬编码返回值/幻觉 API/未实现 TODO/过度实现 5 项逐一有结论（§七） |
| 上游 F-1~F-13 处置逐条比对 | ✅ 13/13 条逐条裁决（§六），含 F-2 引擎口径独立复证、F-5/F-6 棘轮复跑、F-12 机制实证 |
| 审查边界约束遵守 | ✅ 未修改产品代码/`.governance/`；唯一写入 = 本报告；只读命令全部路径限定；coverage 数据文件 `COVERAGE_FILE` 重定向 `$TEMP` 并即时删除 |

---

## 九、审查结论

# APPROVED_WITH_NOTES

unresolved_blockers=0

**P0 = 0 / P1 = 1 / P2 = 0 / P3 = 4。**

**终态理由**：本批是对 `REVIEW-FEAT-021-CODE-R0` 全部 13 条发现的逐条处置，且**13/13 条均经独立事实核验判定为"有效"**（§六）。三项关键实证均**由本审查独立复现、而非采信声明**：

1. **F-2 的引擎读取口径前提更正成立**——读 `verify_workflow.py` L20613-20621 与 L7285-7297 证实引擎读的是 **label 块自身顶层** 的 `skipped`；上游报告选项 (a)（"嵌套即正确"）的前提确实是错的，采纳它会让 skip **静默变 `[PASS]`**。本批采用的"保持冻结 3 键 + 显式提升约定 + 双态 pin"是三者中唯一同时满足 §3.7 与引擎事实的方案（§4.1）。
2. **F-5/F-6 的棘轮与基线变更正确**——复跑 `archguard-ratchet` 得 **PASS / 0 violations**，其中 **R3 `managed 2 modules, 0 edges, SCC max 1`**（contracts.py 真入册，设计 §10 L516 的「R3 判定」验收门由机器门兑现）、**R7 `committed==fresh True`**（`owner_task` 由 `_OWNER_TASK_MAP` 派生、映射为单一事实源，无手编漂移）、**R2 `46 ≤ 46`**（单调不减）；基线 JSON 直读确认 R2 债务条目 `owner_task="FIX-303"` 未丢失（§4.2）。
3. **F-12 的定案逻辑成立且"Protocol 无关"属实**——复跑得 `164 stmts / 0 miss = 100%`；排除机制定位为 coverage 7.13.5 **内置默认**的 "函数体仅 `...` 整体排除" 模式（非 Protocol 专属，对照实验：普通类方法体/自由函数体同样被排除、`TOP = ...` 不被排除）；"改动前 161" 与本批净 +3 语句**自洽**（§4.3）。

机判面亦全部独立复跑一致：**97/97 OK**、contract matrix **`4 faces, zero drift`**、manifest **PASS**、lint **NOT_RUN（五工具实测未安装，声明属实）**；且 10 条新测试经**改前行为模拟**确认"有牙"（F-10 两正对照在改前检测面内零节点 ⇒ 必红；F-3 两负对照在改前路径上无断言 ⇒ 必红），F-11 的恒真 `isinstance` 已被强度更高的三方对账替换（`82 == 79 − 3 + 6` 逐项复现）。

**唯一 P1（NF-1）的性质与处置要求**：F-3 修复关闭了 `skipped` **属性**通道，但适配器仍**逐字透传** `details` 而 `details["skipped"]`/`["skip_reason"]` 恰是其**自用披露键**，故"矛盾 legacy 面"仍可从 `details` 通道产出（已实测复现：`pass=False` + `details["skipped"]=True` ⇒ 按本批新 pin 的约定会被引擎读作 SKIP），而改后 docstring 声称复验覆盖"every field it serializes … including the skip invariant"——**属措辞超实现 + 边界条件未处理**。按 code-review SKILL 第四步「P0=0 且 P1>0（有遗留计划）→ 有条件合并」：**NF-1 不构成 BLOCKING**（本批硬门槛全过、机判门禁全绿、当前零在产消费方接入），**建议本轮或紧随补丁轮落地**；若本轮不修，**MUST 由 Coordinator 登记为遗留项并附关闭截止日期**，且**必须在后续切片"把 `CheckResult` 接入 L4/registry 聚合"之前关闭**——否则该切片会以"适配器已校验完备"为前提，把 FAIL 静默披露为 SKIP。首选最小修复 = 在 `to_legacy_dict` 内强制 `details` 保留键语义（`skipped is None` 时拒绝或清除 `details` 携带的 `skipped`/`skip_reason`）+ 1 条负对照。

**其余 4 条 P3**：**NF-2**（同一 diff 内两处 note 仍写 "unmanaged until REFACTOR-contract-layer admits it"，与新条目的 "until its own slice" 矛盾——建议**本轮顺手修**，改 note 后 regen 以保 R7 双真）；**NF-3**（F-2 的引擎口径 pin 为手写复刻、与引擎无机判绑定——加固或标注复核条件）；**NF-4**（py39 启发式的欠达形态未在 docstring 披露）；**NF-5**（覆盖率口径未在仓内 pin，建议随证据记录机制与版本）。

**给 Coordinator 的遗留项与记录建议（超出本 4 文件面，Reviewer 不可执行）**：
1. **NF-1** 记入跟踪表并定关闭截止；**在后续 registry/L4 聚合切片派发前**必须关闭或明确降级。
2. **F-12 的证据落地**：`EVD-994` 现存表述仍为 "478 行/161 stmts"（`.governance/evidence-log.md` L1937）——本轮复跑得 **528 行 / 164 stmts / 0 miss = 100%**，建议随 FIX-303 证据行记录新数字 **+ 本审查实证的排除机制**（coverage 7.13.5 内置 ellipsis-stub 排除、Protocol 无关、净 +3 语句），使"定案"落在仓内而非仅存在于派发回报中。
3. **F-6 的债务看护**：`contract_matrix/generator.py` L51 `import_vw` 现由 **FIX-303** 具名负责——FIX-303 自身关闭时该 owner 会再次失效，建议在 FIX-303 任务行保留 carry-over 注记（或在下一棘轮切片重指）。

**机器记录口径提示（给 Coordinator）**：`unresolved_blockers=0` 在本报告中**独占一行且无附着细目**，以免与 FIX-291 的 provably-zero 探针（附着 `P0/P1` 非零计数即拒绝认证为零）冲突；P0/P1/P2/P3 计数写在上一行。

---

## 十、审查边界声明

- 本轮为**只读审查 + 只读核验命令复跑**（FEAT-025 / FIX-304 R0 先例口径）。**未修改任何产品代码**、**未写入 `.governance/`**、**未写除本报告外任何文件**；coverage 数据文件经 `COVERAGE_FILE` 重定向至 `$TEMP` 并在同一条命令内删除（等效于开发者采用的隔离方式，避免污染工作树）。
- **未执行 FIX-304 面的任何命令**；工作树内 `infra/quickscan_registry.py` 与 `infra/tests/test_quickscan_registry.py` 的在飞改动**不在本审查对象内**，其引入的任何测试红/绿均不得归因于本批（§三附注已披露全量套件运行时的这一混杂）。
- 破坏性红线**不适用**：全程无仓外路径访问、无 `$HOME`/`$DSH_HOME` 写入、无安装/卸载、无 git 写操作。
- **未复现的项（如实披露）**：(a) 开发者所称"TDD 红"的**原始输出**未附于审查对象，本审查以**改前行为模拟**（`_annotation_nodes` 零节点 / 改前无适配期断言）替代验证"新测试具备拦截力"，而非验证历史运行日志；(b) 全量套件 32F+1E 的"与基线签名恒等（逐测试名 Compare-Object 新增 0/消失 0）"**未逐名复跑比对**——理由：该比对需与基线快照逐名 diff，且在含 FIX-304 在飞改动的工作树上无法单独归因于本批；本批 4 文件的实际覆盖已由路径限定的第 1~5、7 项核验直接锁定。
