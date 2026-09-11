# Code Review: FEAT-021-R0 — 最小契约层 L0 落地

- **Task**: FEAT-021（R0；AUDIT-150 §10 `REFACTOR-contract-layer`，设计 §3.6/§3.7/§8.1 类 3）
- **Reviewer**: Code Reviewer Agent（只读审查；不修改产品代码、不与用户交互）
- **Round**: R0（首次审查；无前轮报告）
- **审查对象**: commit `906b209`（`git show 906b209 --stat` = 2 files changed, 1265 insertions(+), 0 deletions —— 两个文件均为新增，`verify_workflow.py` 零改动）
  - `skills/software-project-governance/infra/contracts.py`（478 行）
  - `skills/software-project-governance/infra/tests/test_contracts.py`（787 行）
- **设计基准**（逐项比对用）: `docs/requirements/architecture-evolution-0.80.0.md` §3.6（L178-224 契约形状——本任务验收权威）、§3.7（L226-232 Result dict 兼容）、§8.1 类 3（L415-424 差分类 3）、§3.2/§4.1 R3（L113/L258 依赖方向与层间矩阵）、§9.1（L443-448 轻注册与 loader 白名单）、§7.2（L371-373 记录模型字段）、§10 L516（任务行与验收门）
- **审查方法**: 逐行读两个新增文件全文（478 + 787 = 1265 行，非抽样）；再以仓内事实交叉核对每条声称——`verify_workflow.py` L7285-7297 / L14821-14838 / L17340 / L17372 / L20613-20621 / L22439；`checks/manifest.py` L419；`checks/review_domain.py` L213-221；`tests/test_verify_workflow.py` L7541-7559 / L9364；`contract_matrix/generator.py` L213-235 与 `snapshots.json`（L4-76 段清单、`$seq` 标记）；`archguard_ratchet.py` L87-123；`core/architecture-baseline.json` L257-264 / L428-434；`core/manifest.json` L55 / L139；`pyproject.toml` L2 / L10；`.governance/evidence-log.md` L1919 / L1937（EVD-994）
- **审查边界**: Reviewer 只读——**本轮未执行任何测试/门禁命令**（角色工具约束）。测试运行数字（TDD 红、87/87、覆盖率、archguard、contract-matrix --check、全量基线）按仓内先例采信 Developer 声明，并以代码事实交叉印证；无法静态定案的项逐条标注于 §五，其中 1 项建议 Coordinator 复跑定案（F-12）。

---

## 一、5 个评审维度逐项结论

### 维度 1：正确性 — 通过（含 P1×1 / P2×4）

**1.1 字段与形状逐行核实。**
- `Finding`（contracts.py:247-278）：6 字段与 §3.6 逐字段一致（severity/check/message/file=None/line=None/extra=dict），frozen=True 经 `object.__setattr__` 做 fail-closed 校验；`_require_line` 显式排除 `bool`（int 子类）与 `line < 1`（L172-179）——边界处理到位。
- `CheckResult`（L284-312）：5 字段与 §3.6 一致，非 frozen（L4 聚合用）；`__post_init__` 校验 + 一条设计外不变式 `skipped ⇒ passed=True`（L309-312），该不变式有 legacy 佐证（`tests/test_verify_workflow.py`:7554 断言 skip 路径 `detail["pass"]` 为真，注释「WARN semantics — skip must not FAIL」）⇒ 不变式与引擎事实一致，非臆造。
- `CheckSpec`（L360-399）：6 字段与 §3.6 一致且 frozen；`input_deps` 允许空、`modes` 禁空且去重（L384-394）。
- 四端口（L437-478）：`GovernanceStore.read_records(scope: RecordScope) -> Iterable[LogicalRecord]` 与 §3.6 签名逐字一致；`GitPort` 四法（status/show/tag/rev_parse）与 §3.6 注释逐项对上；`ClockPort.now() -> datetime` 只定 seam 不取环境时钟（L471-478）。
- 校验辅助（L141-241）：`_fail` 单一异常型 `ContractViolation(ValueError)`；消息逐字段带 name/expected/observed（L147/160/168/178 等）——满足 SKILL 事实依据红线对 fail-closed 的要求。

**1.2 `to_legacy_dict` 键集与本轮声明一致（验收 3 的正面结论）。**
- L327-331 构造的 dict 键**恰为** `pass`/`issues`/`details` 三键，无第四键、无删除键；`details` 每次调用取新副本（L326 `dict(value)`）；skip 披露写入 `details` 内部而非顶层（L332-334）⇒ 与 §3.7「不加必填键」一致；测试 `test_key_set_is_exactly_pass_issues_details`（test_contracts.py:413-417）以三种构造（默认/passed=False+findings/skipped）覆盖该键集，`test_adapter_never_adds_top_level_keys`（:779-783）覆盖 skip+details 并存场景 ⇒ **声明与实现一致，PASS**。

**1.3 发现（正确性）**：
- **F-1（P1）** 适配器的 issue 元素口径与"legacy 口径"事实不符（详见 §四）。
- **F-2（P2）** skip 披露位置未与唯一在仓消费方对齐，"verbatim 复用"引用不成立。
- **F-3（P2）** `to_legacy_dict` 边界复验不完整（`skipped` 被序列化却未复验），设计外不变式可被构造后绕过。
- **F-4（P2）** `CheckSpec.loader` 口径歧义（"模块路径" vs 实际接受的"模块+函数"路径）。
- **F-7（P2）** `extra`/`details`「隔离」表述只到浅拷贝。
- **F-8 / F-9（P3）** 见 §四。

### 维度 2：安全性 — 通过

- **零硬编码凭据/无注入面**：全文件无密钥/token/密码字面量；无 `eval`/`exec`/`__import__`/`subprocess`/网络调用；正则只有 3 条自产 pattern（L125-127）且只作用于自己声明形式的字符串（`re.compile` 在 import 期完成，无 ReDoS 面的用户输入）。
- **零 I/O 与 import 期零副作用**（R3 口径，逐行核实）：导入仅 `__future__`/`re`/`collections.abc`/`dataclasses`/`datetime`/`typing`（L69-84），无仓内 import、无相对 import；无 `open`/`print`/文件系统/时钟调用；模块体语句全为声明（docstring/import/赋值/类/函数）——由 `ZeroIoZeroDependencyTests`（test_contracts.py:163-212）以 AST 机判，含"导入白名单 ⊆"、"禁名/禁属性调用"、"模块体节点白名单"、"无 `__main__`"四道断言 ⇒ 与声明一致。
- **测试侧真实环境接触为零**：test_contracts.py 导入面无 `unittest.mock`/`subprocess`/`tempfile`/`os.environ`（已核实；唯一 grep 命中 "patch" 系 "dis**patch**" 子串）；只读 `contracts.py` 与 `contract_matrix/snapshots.json` 两个仓内文件（:38-39），无 `$HOME`/`$DSH_HOME`/仓库外路径、无写操作 ⇒ 破坏性红线不适用（无隔离/备份/授权三选一义务），且无残留写副作用。
- **路径注入面**：`_require_loader`（L402-409）拒 `.py` 后缀、`/`、`\`、`:`（Windows 盘符）⇒ 把「受控 loader 白名单」（§9.1）在 L0 层先做了一道形态约束，方向正确。
- 无权限/越权面（纯类型模块，无执行权）。

### 维度 3：可维护性 — 通过（含 P2×2 / P3×2）

- 命名表意（`_require_*` 族、`legacy_issue_text`、`to_legacy_dict`）；模块 docstring 分节（形状清单 / 层纪律 / 口径决策 / 显式延后项）且**每条口径决策都标注测量来源与行号**——本仓"事实依据"文化的正向范例。
- 职责单一：单文件单职责（L0 契约），无 I/O、无 CLI、无业务政策；478 行中含 67 行 docstring，无超长函数（最长 `to_legacy_dict` 22 行）。
- 校验集中在 `_require_*` 辅助（L141-241），重复逻辑已提取；`Finding`/`CheckSpec` 用 `object.__setattr__` 模式统一。
- **可维护性风险**：F-2（引用与事实不符的"verbatim"表述）、F-4（loader 口径歧义）、F-7（隔离表述超实现）、F-10（py39 守卫覆盖面）。
- 已核实并接受的**设计固有约束**（非发现）：`Finding` 因 `extra: dict` 字段导致 `__hash__` 不可用（L251-254 声明 + test_contracts.py:239-247 以 `assertRaises(TypeError)` 钉住）。若后续 L4 需对 findings 去重，需 `key=` 函数——当前无消费方，无需动作。

### 维度 4：性能 — 通过（无发现）

- 无 I/O、无循环嵌套、无 O(n²) 以上算法；3 条正则 import 期编译一次（L125-127）；`_require_sequence` 的重复检测为 O(n²) 但 n 为 `input_deps`/`modes` 级（≤ 个位数），实测面无风险。
- import 期成本 = 3 次 `re.compile`，符合 §9.1「按命令加载、import 期不做事」的预算方向。
- 无缓存/懒加载需求（无大对象）。

### 维度 5：测试覆盖 — 通过（含 P2×1 / P3×3）

- **清点核实**：`grep -c 'def test_'` 式逐类清点 = ModuleSurface 5 + ZeroIo 4 + Finding 20 + CheckResult 15 + LegacyAdapter 17 + CheckSpec 13 + PortProtocol 6 + Python39 3 + FrozenCrossCheck 2 + AdapterVsFrozen 2 = **87** ⇒ 与「87 测试」声明一致。
- **合法/非法/往返/不可变/负对照五类逐一存在**：
  - 合法路径：默认构造 + 全字段构造（:218-225 / :284-286 / :552-560）；
  - 非法路径：每字段的空白/非文本/类型错/边界值（:254-305 / :344-407 / :567-625），且断言消息内容（`_violation` 辅助 :94-102 检查 needle）而非仅断言异常类型；
  - 往返：`test_legacy_issue_text_round_trips_to_finding_fields`（:501-528）以测试侧反向正则还原 severity/check/message/file/line；
  - 不可变：`:227-232`（frozen）+ `:239-247`（hash 不可用 characterization）+ `:307-318`/`:393-403`（默认工厂不共享）+ `:479-486`（details 每次新副本）；
  - 负对照（守卫有牙）：`:722-732`（py39 检查器对 PEP 604 / match 真报警）+ `:537-546`（突变载荷被适配器拒绝）+ `:465-477`（stale skip 键被规范化）。
- **真实交叉核对**：`FrozenContractCrossCheckTests`（:735-755）真读 `snapshots.json`，把 FEAT-020 冻结的 70 段（已核实 `count: 70`，ids 全为 `NN`/`NN[a-z]` 形态，L4-76）逐段与 `CHECK_ID_PATTERN` 对账 —— 这是模块 docstring 「Cross-checked against the FEAT-020 frozen 70-segment surface」声称的**真实兑现**，非空断言。
- 覆盖缺口：F-3（突变负对照未覆盖 `skipped`）、F-11（一条恒真断言）、F-12（100% 覆盖率声明待复验）、F-13（往返前提未写明）。

---

## 二、设计一致性逐项比对（§3.6 / §3.7 / §8.1）

| 设计条目 | 实现位置 | 判定 |
|---|---|---|
| §3.6 `CheckID = str` / `CommandKey = str` | contracts.py:106-107（测试 :140-142 断言 `is str`） | ✅ 一致 |
| §3.6 `Finding`（frozen；severity/check/message/file/line/extra） | :247-278 字段名、顺序、默认值、类型逐一一致 | ✅ 一致 |
| §3.6 `CheckResult`（非 frozen；check/passed/findings/skipped/details） | :284-312 一致；`skipped: str \| None` 以 `Optional[str]` 过渡（§3.6 L224 明文许可） | ✅ 一致（+2 条设计外校验，见 F-2/F-3） |
| §3.6 `GovernanceStore.read_records(scope: RecordScope) -> Iterable[LogicalRecord]` | :437-441 逐字一致 | ✅ 一致 |
| §3.6 `FilesystemPort`（L207 仅"读树/读文件（UTF-8 强制）"+`...`） | :444-452 `read_text`/`list_files`，docstring 写明实现方 MUST UTF-8（FIX-278 G4/F） | ✅ 合理细化（与 §8.1 类 4 编码纪律同向） |
| §3.6 `GitPort`（status/show/tag/rev-parse） | :455-468 四法齐备，命名与设计逐项对应 | ✅ 一致 |
| §3.6 `ClockPort`（可注入时钟） | :471-478 `now() -> datetime`，实现方拥有时区政策 | ✅ 一致 |
| §3.6 `CheckSpec`（frozen；check_id/domain/loader/input_deps/severity_floor/modes） | :360-399 字段与顺序一致；`input_deps`/`modes` 为 tuple | ✅ 一致（loader 口径见 F-4） |
| §3.6 `loader: str  # 模块路径字符串（受控白名单加载，§9.1）` | :402-409 要求 ≥2 段点分路径、禁扩展名/分隔符/盘符/根级名 | ⚠ 形态比 §3.6 更严 + 与测试默认样例语义冲突（F-4） |
| §3.6 `RecordScope` / `LogicalRecord` 占位 | :415-434；`id/status/time/relations/source_path/source_line` 对齐 §7.2（L373「稳定 ID / 状态 / 时间 / 关系 / 源位置（文件+行）」五要素） | ✅ 一致（占位范围与 docstring L62-66 声明的延后范围一致） |
| §3.2 L0 亦负责「执行上下文」 | 不在本批 —— docstring L66 声明为后续 L0 批次，§3.6 首批清单亦未含 | ✅ 范围一致（非缺项） |
| §3.6 模块名 `L0/contract.py` | 落位 `infra/contracts.py`；docstring L3-5 声明为 packet 决策，§10 L516 未钉路径 | ✅ 无违反（P3 备注：设计文档未同步该落位，见 F-9 备注） |
| §3.7 键名 `pass`/`issues`/`details` 不改、不加必填键 | :327-335 + 测试 :413-417/:779-783 | ✅ 一致 |
| §3.7 内部强类型 + `to_legacy_dict()` 适配器 + 构造校验辅助 | :284-335（适配器）+ :141-241（校验） | ✅ 一致 |
| §8.1 类 3「schema 快照 + 边界用例（空 issues/None details/SKIP 披露）黄金样例」 | 空 issues ✓（:429-430）；None details → 声称为 0 例（未复算，见 §五）；SKIP 披露 ✓（:460-477） | ⚠ 元素口径无牙 + SKIP 位置未对齐（F-1/F-2） |
| §4.1 R3「L0 零依赖、任何层可依赖」 | 模块零出边；未入 `archguard_ratchet.py` 的 `managed_modules`（L101-112） | ⚠ 机器棘轮未实际管辖（F-5） |

**结论：§3.6 首批形状**（验收 1）**全落地、字段级一致，无缺项、无偏离**；偏差集中于两处"比设计更严/更松的实现选择"（loader 形态、适配器元素口径），均已作为发现登记。

---

## 三、AI 专项 5 项 + 声明 vs 代码事实交叉核对

### 3.1 AI 专项 5 项（逐项结论）

| 项 | 结论 | 依据 |
|---|---|---|
| mock 残留 | **无** | contracts.py 无任何测试替身；test_contracts.py 导入面无 `unittest.mock`（:21-29），唯一"替身"是 `test_ports_are_implementable_without_the_contract_changing`（:673-705）中真实实现四个 Protocol 的四个小类（合法做法，非 mock） |
| 硬编码返回值 | **无欺骗性硬编码** | `to_legacy_dict` 全部字段源自 `self.*`（:327-335），无 `return {"pass": True}` 类捷径；文件内字面量仅：严重度词表 `SEVERITIES`（§3.6 声明）、`CHECK_ID_PATTERN`（§3.5 声明）、两条形态 pattern、FIX-270 披露键名 —— 均为契约常量且有设计锚点 |
| 幻觉 API | **无** | 逐项核对：`dataclasses.dataclass/field/FrozenInstanceError`、`typing.{Any,Dict,Iterable,List,NoReturn,Optional,Protocol,Tuple,get_type_hints}`、`collections.abc.Mapping`、`re.compile/match/fullmatch`、`object.__setattr__`、`ast.parse(feature_version=(3,9))`、`str.strip/endswith`、`Path.read_text(encoding=)` —— 全部真实且与 py3.9 兼容 |
| 未实现 TODO | **无** | contracts.py 全文件无 `TODO`/`FIXME`/`XXX`/`HACK`/`type: ignore`/`noqa`（grep 零命中）；两处"未实现"是设计明示的 `Protocol` 方法体 `...` 与 `RecordScope`/`LogicalRecord` 结构占位，均在 docstring L62-66 显式声明范围 |
| 过度实现 | **无实质过度**（2 项 P3 级） | 全 §3.6 外新增的公开面仅 `SEVERITIES`/`CHECK_ID_PATTERN`/`legacy_issue_text`/`ContractViolation`——四者均被校验或验收断言消费（测试 :150-160/:456-458/:601-606）；P3 级余项见 F-8（`unique=False` 分支无调用点）、F-9（`Finding.file` 未校验相对性） |

### 3.2 Developer 声称 vs 代码事实（逐条交叉核对）

| # | 声称 | 核查结果 | 依据 |
|---|---|---|---|
| 1 | 恰 2 个新文件、+1265 行 | ✅ 属实 | `git show 906b209 --stat`：2 files changed, 1265 insertions(+)，均新增，`verify_workflow.py` 零改动 |
| 2 | 87 测试 | ✅ 属实（逐类清点 = 87） | test_contracts.py 各类 `def test_` 计数见 §一维度 5 |
| 3 | TDD 红（ModuleNotFoundError）→ 87/87 OK | ⚠ 采信（未复跑） | `.governance/evidence-log.md`:1937 EVD-994 明载「TDD 红（ModuleNotFoundError: No module named 'contracts'，exit 1）→ 87/87 OK」；test_contracts.py:3-4 docstring 同述；红态原始输出未附于本次审查对象内 |
| 4 | 覆盖率 161 stmts / 0 miss = 100% | ⚠ **待复验**（见 F-12） | 无仓内覆盖率门禁配置（`pyproject.toml` 无 `[tool.coverage]`）；8 个 Protocol `...` 跳转体在测试中从不执行 |
| 5 | contract matrix --check「4 faces, zero drift」 | ✅ 事实层面自洽（未复跑） | 四面来源均在被冻结的 `verify_workflow.py`/引擎函数（generator.py:95-143/160-207/247-252/302-318），两个新增文件不进入任何面；`verify_workflow.py` 零改动 ⇒ 零 drift 结论可静态推出 |
| 6 | archguard-ratchet PASS（R1 24329≤24329 等） | ⚠ 部分独立核实 | R1 锚值 24329 == `infra/verify_workflow.py` 实际物理行数（读全文得 total 24329），且该文件本任务零改动 ⇒ R1 不变可静态确认；R2/R3/R4/R5/R7 未复跑 |
| 7 | check-manifest-consistency PASS（641 canonical / 708 actual） | ✅ 结构自洽（未复跑） | `core/manifest.json`:139 有 `infra/` dir 条目 + :55 `infra/**/*.py` glob ⇒ 新文件自动入 canonical，不会被判 untracked/残留（与 FEAT-020 R0 报告同结论） |
| 8 | 零 I/O 零内部依赖（AST 机判） | ✅ 属实（我逐行核实 + 测试机判双重） | 导入面 L69-84；机判 ZeroIoZeroDependencyTests :163-212；`infra/` 下无与 stdlib 同名的可遮蔽模块（无 `re.py`/`json.py`/`dataclasses.py`/`typing.py`/`collections/`） |
| 9 | issues 元素口径普查 str 210 / dict 45 / other 17 | ⚠ 未独立复算（需执行扫描）；**且该普查未改变结论的适用范围问题** | grep 抽查证实两类均普遍存在；关键反证见 F-1（`verify_workflow.py`:14821-14838 结构化消费 dict 元素；`tests/test_verify_workflow.py`:9364 钉住 `issue["type"]`） |
| 10 | `"pass": None` 恰 3 例（verify_workflow L17340/L17372、checks/manifest L419） | ✅ 属实（逐处读源码） | verify_workflow.py:17340、17372 同函数两处 `result["pass"] = None  # couldn't run`；checks/manifest.py:419 `"pass": None` + `"error": "manifest.json not found or unreadable"` |
| 11 | Python 3.9 兼容（`__future__ annotations`；未用 PEP 604） | ✅ 属实 | contracts.py:69 有 `from __future__ import annotations`；全文件无 PEP 604/`match`/walrus；`pyproject.toml`:2 `target-version = "py39"`、:10 `python_version = "3.9"` 与 docstring 引用一致 |
| 12 | 模块体仅声明（§9.1 无 import 期副作用）、无 `__main__` | ✅ 属实 | 模块体节点全为 import/赋值/类/函数（含 docstring）；源文无 `__main__` 字样 |
| 13 | 遗留：contracts.py 未入 R3 `managed_modules` | ✅ 披露属实，但**验收措辞需收紧**（见 F-5） | archguard_ratchet.py:101-112 `DEFAULT_MANAGED_MODULES` 仅含自身；core/architecture-baseline.json:428-434 注释「unmanaged until REFACTOR-contract-layer admits it」 |

---

## 四、发现汇总（P0~P3 + 位置 + 事实依据 + 建议）

| # | 级别 | 位置（file:line） | 问题与影响 | 事实依据 | 修复建议 |
|---|------|------------------|------------|----------|----------|
| **F-1** | **P1** | `contracts.py`:36-41、50-52、329 | 适配器把 `issues` 元素**一律**渲染为字符串，并把它表述为 legacy 的**唯一**口径（"the legacy caliber is a human-readable line"／"`extra` is the single documented field loss"）。事实：仓内存在 dict 元素面且**有结构化消费方与既有测试钉住**——迁移任一此类 check 到 `CheckResult` 时，产出与旧构造不等价、消费方崩塌，而 §8.1 类 3 冻结只 pin 容器 ⇒ **差分门禁静默通过**（防护网有洞） | ① 同一 docstring 自记普查 str 210 / dict 45 / other 17（.py:36-38）；② `verify_workflow.py`:14821-14838 以 `issue["type"]` 分支并读 `issue["detail"]`（其为 list）；③ `verify_workflow.py`:22439 `issue.get("type", "issue")`；④ `tests/test_verify_workflow.py`:9364 `{issue["type"] for issue in result["issues"]}`；⑤ `checks/review_domain.py`:213-221 产出 7 键 dict（type/file/line/text/severity/pattern/fix）；⑥ `contract_matrix/generator.py`:213-235 `type_signature` 把序列折叠为 `$seq`（"element payloads are state-dependent"），`snapshots.json` 仅含 `$dict`/`$seq` 标记 | 本轮**最小修复**：把 docstring 的口径表述改为按面限定（"字符串口径对 `str` 元素面等价；`dict` 元素面迁移切片 MUST 自行决定元素口径并在 §8.1 类 3 黄金样例中 pin 元素形状"），并删除"single documented field loss"的全称断言。**结构性修复（可遗留）**：为 `Finding`/`to_legacy_dict` 增加结构化元素渲染路径（如 `extra`→`{"type","detail","file","line"}`），并把元素形状纳入类 3 黄金样例。无论哪条，MUST 登记遗留项（关闭截止日期） |
| **F-2** | P2 | `contracts.py`:42-49、332-334；测试 `test_contracts.py`:460-477 | skip 披露写成"reuses the FIX-270 mechanism **verbatim**"，但被引证据是 **label 子块**内的 `{pass,skipped,skip_reason}`，而被引消费方按 `for label, detail in result["details"].items(): if detail.get("skipped")` 遍历 ⇒ 若把 `{"skipped","skip_reason"}` 直接置于 `details` 根，该循环取到 bool/str 值再调 `.get()` 会 `AttributeError`。正确性取决于一处**全仓未定义的聚合嵌套约定**，且无任何测试 pin | ① 被引构建点 `verify_workflow.py`:7285-7297：`details["dsh_upgrade_regression"] = {"pass":…, "skipped":…, "skip_reason":…}`（label 子块）；② 被引消费点 `verify_workflow.py`:20613-20621：`for label, detail in result["details"].items(): if detail.get("skipped")`；③ legacy 形态由 `tests/test_verify_workflow.py`:7541-7559 以 `result["details"]["dsh_upgrade_regression"]["skip_reason"]` 断言；④ 本仓 `details` 根出现 `"skipped"` 的既有先例仅 `archive.py`:2671/2838 与 `loop_exit_bridge.py`:200-209（`{"skipped": True, "reason": …}`，键名亦不同） | 二选一并补测试：(a) 明确并文档化聚合约定「每个 CheckResult 的 legacy dict 嵌于 `details[<label>]` 之下」→ 现状即正确，补一条 pin 该嵌套的测试；(b) 把披露键移入 label 子块。同时把"verbatim"改为精确表述（键名同形、放置层级由聚合约定决定） |
| **F-3** | P2 | `contracts.py`:287-292、314-335；测试 `test_contracts.py`:537-546 | 类 docstring 称 `to_legacy_dict` "re-validates the two fields it serializes"，实际复验 3 个字段（passed/findings/details，:324-326）却**漏掉同样被序列化的 `skipped`**。构造后突变可绕过设计外不变式：`r = CheckResult(..., skipped="x"); r.passed = False; r.to_legacy_dict()` → 产出 `pass=False` + `details["skipped"]=True`，自相矛盾的 legacy 面（skip 披露 + FAIL），与 FIX-270 WARN 语义（:309-312 自述）冲突；现有突变负对照只覆盖 `passed`/`findings` | ① :324-326 复验字段集合；② :309-312 不变式 `skipped ⇒ passed=True`；③ :332-334 序列化 `skipped` 未经校验；④ 不变式的 legacy 佐证 `tests/test_verify_workflow.py`:7554；⑤ 负对照缺口 :537-546 | `to_legacy_dict` 内加 `_require_optional_text` 复验 `skipped` 并重断言不变式（失败即 `ContractViolation`）；补一条 `passed=False + 残留 skipped` 的负对照；修正 "two fields" 措辞（3 处） |
| **F-4** | P2 | `contracts.py`:121-123、402-409；测试 `test_contracts.py`:85、577-580 | `loader` 口径歧义：报错文案与 docstring 称"dotted **module** path（no root-level name）"，但测试默认值与显式通过样例是 `checks.review_domain.run_review_checks` / `infra.checks.review_domain.run_review_checks`（**模块 + 函数名**）；§3.6 L218 与 §9.1 只说"模块路径字符串"。R5「loader 路径可解析」的实现（import 模块 vs `getattr` 属性）必须依赖此决定，当前两种形态都被放行 | ① :402-409 文案；② :123 pattern（≥2 段即可）；③ test_contracts.py:85 `_spec()` 默认 loader 为函数限定路径；④ :577-580 显式接受 4 段含函数名路径；⑤ §3.6:218 / §9.1:445 原文 | 明确二者之一：(a) 仅模块路径 → 末段禁函数名并更新说明/样例；(b) 允许"模块.属性"调用面 → 字段说明与 pattern 文案改为 handler/callable path，并在 R5 消费处写明解析方式 |
| **F-5** | P2 | `archguard_ratchet.py`:101-112；`core/architecture-baseline.json`:428-434；设计 §10 L516 | 验收门措辞为「契约层零 I/O 零内部依赖（**R3 判定**）」，但机器 R3 实际**不管辖**该模块：`DEFAULT_MANAGED_MODULES` 仅含 `infra/archguard_ratchet.py`，且基线注释仍写「unmanaged until REFACTOR-contract-layer admits it」。当前"零依赖"由**模块自带的 AST 测试自证**（测试质量合格，见 §一维度 2），属自证而非独立门禁。影响：验收措辞与机器覆盖面不符（真实性/追溯），非功能缺陷 | ① archguard_ratchet.py:101-112；② architecture-baseline.json:428-434；③ 设计 §10 L516 验收门原文；④ `contracts.py` 零内部边 ⇒ 入册后不可能产生层间违规（模块 docstring L25-27 亦如此陈述，与事实一致） | Coordinator 登记「contracts.py（+ 后续 contract_matrix 模块）入 R3 `managed_modules`（layer 待定，L0 零出边）」为下一棘轮切片首项；本轮验收措辞建议改为「零 I/O 零内部依赖（AST 机判；R3 入册随棘轮切片）」 |
| **F-6** | P2 | `core/architecture-baseline.json`:257-264；`archguard_ratchet.py`:122 | 本任务（REFACTOR-contract-layer）是 R2 清单中 `contract_matrix/generator.py` L51 `import_vw` 违规的**具名 owner_task**，而本交付仅两新文件、未消化该债务（R2 政策只要求"基线长度单调不增"，故不 FAIL）。风险：任务若直接关闭，该违规失去责任人（静默债务丢失），且 `generator.py` 的 `_vw()` 遗留正是 F-5 注释所指的"待本任务接纳"对象 | ① architecture-baseline.json:257-264（`owner_task: "REFACTOR-contract-layer"`, `path: "contract_matrix/generator.py"`, `kind: import_vw`, `lines: [51]`）；② archguard_ratchet.py:110；③ archguard_ratchet.py:122 `("contract_matrix/", "REFACTOR-contract-layer")`；④ 设计 §10 L516 本任务定义；⑤ `git show 906b209 --stat` 证实未触及该文件 | **Coordinator 侧动作**（超出本包文件面，不可由 Developer 在本轮完成）：关闭 FEAT-021 前显式转记 —— 新建/指派 archguard 侧切片承载该 R2 条目，或在基线中改 `owner_task`；本任务行保留 carry-over 注记 |
| **F-7** | P2 | `contracts.py`:251-254、318-320；实现 :182-185；测试 `test_contracts.py`:307-312、479-486 | `Finding.extra` / `to_legacy_dict().details` 的"隔离"表述超实现：`dict(value)` 只做**顶层浅拷贝**。docstring 称 frozen Finding "never aliases caller-owned mutable state"、details "callers cannot corrupt the typed object" —— 嵌套可变值仍是共享引用（反例：`Finding(extra={"a": {"b": 1}})` 后 `f.extra["a"]["b"] = 2` 会改到 frozen 对象内部）；测试只覆盖顶层别名 | ① :182-185 `dict(value)`；② :251-254 / :318-320 措辞；③ 测试覆盖面 :307-312 / :479-486（仅顶层 dict） | 二选一：措辞改为"顶层浅拷贝（嵌套值按引用共享）"，或对 `extra`/`details` 做深拷贝；如保留浅拷贝，补一条嵌套别名 characterization 用例，避免后续切片误信深隔离 |
| **F-8** | P3 | `contracts.py`:203-228（调用点 :384-394） | `_require_sequence(..., unique=...)` 的 `unique=False` 分支**无调用点**（两处调用均 `unique=True`），即"允许重复"这一行为规格未被任何用例执行；属死参数或未覆盖规格 | ① :203-209 签名含 `unique`；② :384-394 两处调用均 `unique=True`；③ 全文件无其他调用 | 删除 `unique` 参数（并把去重逻辑内联），或补一条 `unique=False` 允许重复的用例固定该行为 |
| **F-9** | P3 | `contracts.py`:172-179、260-274 | `Finding.file` 未校验 §3.6 注释的"相对仓库根路径"语义：`file="C:\\x\\y.md"`、`file="/abs/x"` 均可通过；L0 不解析路径故影响低，但契约面存在"声明了却未约束"的空隙（相较 `loader` 的严格形态约束不对称） | ① §3.6:192 `file: str \| None = None  # 相对仓库根路径`；② :272-274 仅 `_require_optional_text` | 若无意在 L0 约束相对性，在字段说明写明"L0 不校验相对性，由解析/渲染方负责"；若有意约束，加"禁绝对路径/禁盘符"校验与负对照 |
| **F-10** | P3 | 测试 `test_contracts.py`:105-134、718-720 | py39 守卫只扫描**注解位置**（`_annotation_nodes`：arg/returns/AnnAssign）的 PEP 604；非注解位置的 `Alias = str \| None` 形态（py39 grammar 合法、运行时 TypeError）不在检测面内——恰是该守卫要防的一类漂移；负对照只覆盖注解形态与 `match` | ① :105-115 收集面；② :125-134 判定逻辑；③ :722-732 负对照范围 | 把 PEP 604 检测扩到全 AST 的 `BinOp(BitOr)` 类型表达式（或至少覆盖模块级赋值右侧），并补一条 `Alias = str \| None` 的负对照 |
| **F-11** | P3 | 测试 `test_contracts.py`:750-755 | `test_frozen_cli_keys_are_plain_strings_of_the_command_key_alias` 对 JSON 对象键做 `isinstance(key, str)` —— JSON 键必为字符串，断言恒真、信息量近零，易被读作"CLI 键面已有保护"（实际上 `CommandKey` 的语义保护只有 :140-142 的 `is str`） | ① :750-755 断言体；② JSON 规范键必为 str；③ 对比有牙的 `:738-748` 段清单对账 | 删除，或改为与冻结键集逐键对账（例如断言键数 == `snapshots.json` `cli_dispatch.key_count` 且键名唯一），使该测试具备拦截力 |
| **F-12** | P3 | `contracts.py`:441、449、452、459、462、465、468、478 | 「覆盖率 161 stmts / 0 miss = 100%」存在一处**与代码事实的张力**：8 个 Protocol 方法体 `...` 在整套测试中从不执行（`:631-651` 只做属性引用与 `callable()`；`:673-705` 调用的是四个**子类**实现）。若 coverage 把这些语句计入 161，则 100% 与代码事实不符；若 coverage 不计入（如将其视为 stub 体），则声明成立。**本审查为只读，不执行命令，无法静态定案** | ① 上述 8 行跳转体；② :637-641 只做实例化拒绝断言；③ :702-705 调子类方法；④ `pyproject.toml` 无 `[tool.coverage]` 门禁配置 ⇒ 该数字为一次性测量、不可从仓内配置复现 | Coordinator 复跑一次 `python -m coverage run -m unittest ... -p "test_contracts.py"` + `report --include="*infra/contracts.py"`，把 stmts/miss 与声明并记入 evidence；若 100% 不成立，按实际数字更正 EVD-994 的表述（不影响交付本身） |
| **F-13** | P3 | 测试 `test_contracts.py`:501-528（前提见 :62-63；反例 :494） | `test_legacy_issue_text_round_trips_to_finding_fields` 的 docstring 称"Every field the legacy caliber can carry survives the round trip"，但该往返**只在 message 不含括号时成立**（同文件 :62-63 注释自认；:494 另有含括号 message 用例未参与往返）。断言本身有效（构造输入确无括号），风险在于被后续切片读作"任意 Finding 与 legacy 串可互转" | ① :501-510 构造输入；② :62-63 注释；③ :64-66 反向正则的 `(?: \(...\))?` 歧义；④ :494 含括号 message 未纳入往返 | 在往返测试 docstring 明写适用前提（message 不含 `" (...)"` 形态），或补一条含括号 message 的用例固定"该形态不保证可逆"的 characterization |

**汇总：P0 = 0（无阻塞项）。P1×1 / P2×6 / P3×6。** 全部为非阻塞发现：F-1 的最小编修复是**文档级**（措辞按面限定 + 登记遗留），不改变本次交付的机器核验正确性；F-2/F-3 为适配器边界与披露面的口径/复验缺口（当前零在产消费方接入）；F-4~F-6 为契约语义与验收措辞/追溯面；F-7~F-13 为建议级。

---

## 五、硬门槛裁决

| 门槛 | 结果 |
|------|------|
| P0 阻塞问题数 = 0 | ✅ 0（13 条发现中无 P0） |
| 5 维度全覆盖 = 100% | ✅ 正确性/安全性/可维护性/性能/测试覆盖逐项有结论（§一） |
| 每条发现标注级别 = 100% | ✅ F-1~F-13 全部标注 P1/P2/P3 + file:line + 事实依据 + 建议 |
| 设计一致性检查已完成 | ✅ 对照 §3.6 逐字段（14 项）、§3.7（键集/强制类型/适配器）、§8.1 类 3（边界用例）、§3.2/§4.1 R3（层间矩阵与管辖范围）、§9.1（loader 白名单）、§7.2（记录模型字段）、§10 L516（任务验收门）逐项比对（§二） |
| AI 专项 5 项全部完成 | ✅ mock 残留/硬编码返回值/幻觉 API/未实现 TODO/过度实现 逐项有结论（§3.1） |
| 逐行读两文件全文 | ✅ 478 + 787 = 1265 行全文逐行（非抽样） |

---

## 六、审查结论

# APPROVED_WITH_NOTES

unresolved_blockers=0

**终态理由**：§3.6 首批形状（CheckID/CommandKey、Finding、CheckResult+to_legacy_dict、CheckSpec、四端口 Protocol、RecordScope/LogicalRecord 占位）**逐字段落地且与设计一致，无缺项、无偏离**；`to_legacy_dict` 键集恰为 `pass`/`issues`/`details` 且不加必填键，与 §3.7 及本轮声明一致；零 I/O、零内部依赖、import 期仅声明经逐行核实且有 AST 机判双重固定；py39 兼容属实（`__future__` + `Optional`，pyproject 双钉核对一致）；87 例测试逐类清点属实，合法/非法/往返/不可变/负对照五类齐备，且 70 段冻结清单对账为**真交叉核对**（真读 `snapshots.json`，count=70 已核实）；AI 专项 5 项无异常；两个新增文件未触碰引擎（`verify_workflow.py` 零改动，纯新增 +1265）。P0 = 0 ⇒ 无未解决 BLOCKING finding，满足 code-review SKILL「循环角色」段的通过终态契约，并以独立结构字段声明 `unresolved_blockers=0`。

**唯一 P1（F-1）的处置要求**（按 SKILL 第四步「P0=0 且 P1>0（有遗留计划）→ 有条件合并」）：F-1 的**最小修复（docstring 口径按面限定 + 删除"唯一字段损耗"全称断言）建议本轮或紧随补丁轮落地**（≤8 行文档改动，不动代码行为）；若本轮不修，**MUST 由 Coordinator 登记为遗留项并附关闭截止日期**——否则后续 dict-元素面切片会在"类 3 差分通过"的假绿下破坏消费方（含既有测试 `tests/test_verify_workflow.py`:9364 钉住的 `issue["type"]` 形态）。P2×6 / P3×6 均按「遗留项 + 跟踪表」处理，不构成本轮阻塞；其中 **F-5/F-6 需 Coordinator 侧动作**（棘轮入册与 R2 owner_task 转记），**F-12 需复跑覆盖率定案**。

**机器记录口径提示（给 Coordinator）**：`unresolved_blockers=0` 在本报告中**独占一行且无附着细目**，以免与 FIX-291 的 provably-zero 探针（附着 `P0/P1` 非零计数即拒绝认证为零）冲突；P0/P1/P2/P3 计数均写在独立行。

---

## 七、遗留项与建议处置

| 项 | 级别 | 建议处置 | 责任方 |
|---|---|---|---|
| F-1 | P1 | 本轮修 docstring 口径（按面限定 + 去全称断言），或登记遗留（关闭截止日期）与后续元素口径切片 | Developer / Coordinator |
| F-2、F-3、F-4、F-7 | P2 | 随下一契约侧补丁轮处理；补 3 条负对照/边界用例（skip 突变、聚合嵌套 pin、loader 口径、嵌套别名） | Developer（下一轮） |
| F-5、F-6 | P2 | 棘轮入册 + R2 owner_task 转记（协调动作，超出本包文件面） | Coordinator |
| F-8~F-13 | P3 | 记跟踪表；F-12 需复跑覆盖率定案 | Coordinator / Developer |

*审查边界声明：本轮为只读审查，**未执行任何测试或门禁命令**（Reviewer 角色工具约束）。测试与门禁数字（TDD 红、87/87、覆盖率 161/0、archguard R1~R7、contract-matrix --check、全量 2422/32F/2E 与零新增归属）采信 Developer 声明与 `.governance/evidence-log.md` EVD-994 记录，并以代码事实交叉印证（§3.2 逐条给出核实等级）；其中 R1=24329 与 `verify_workflow.py` 实际物理行数一致、`verify_workflow.py` 零改动、87 例计数、3 例 `pass: None` 行号、FIX-270 skip 语义、70 段冻结清单、pyproject py39 双钉均为本审查**独立核实**为真。唯一无法静态定案的机器数字为覆盖率 100%（F-12），已给出复跑命令。*
