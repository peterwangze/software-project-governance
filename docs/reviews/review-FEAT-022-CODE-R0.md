# Code Review: FEAT-022-R0 — 轻量注册与按命令加载

- **Task**: FEAT-022（R0；AUDIT-150 P1 `REFACTOR-light-registry`，`architecture-evolution-0.80.0.md` §10 **L517** 验收权威）
- **Reviewer**: Code Reviewer Agent（只读审查；不修改产品代码、不与用户交互）
- **Round**: R0（首次审查；无前轮报告）
- **审查对象**: commit `36f2040`（= 当前 `HEAD`；`git show --stat` = **2 files changed, 1860 insertions(+), 0 deletions**，两文件均新增）
  - `skills/software-project-governance/infra/registry.py`（897 行 / 248 stmts）
  - `skills/software-project-governance/infra/tests/test_registry.py`（963 行 / 71 测试）
  - **字节级冻结核验**：`git hash-object` 工作树两文件 = `6a6440ca…` / `a7244fac…`，与 `git rev-parse 36f2040:<path>` **逐字节相同** ⇒ 工作树内容 = 被审 commit 内容，读工作树即读 commit。
- **设计基准**（逐项比对用）: `docs/requirements/architecture-evolution-0.80.0.md` §10 L517（验收三条）、§3.2（L113-148 分层图 / L146 L6 组合根职责与「禁 import 时实例化全部服务」）、§3.5（L168-176 Check/命令粒度与冻结 ID）、§3.6（L178-222 `CheckSpec` 形状）、§9.1（L443-448 静态轻注册 + 受控 loader 白名单 + 四条禁令）、§4.1 **R5**（L260 注册完整性）、§9.5/§4.1 R6（L261/L468-475 启动成本口径）；`infra/contracts.py`@36f2040（FEAT-021 交付，`CheckSpec` 消费基准）；`infra/quickscan_registry.py`@**504cc8f**（FEAT-025 交付，domain/input_deps/modes 消费基准；工作树版本含 FIX-304 在飞改动，故取 commit 版本为参照面）
- **审查方法**: 逐行读两文件**全文**（897 + 963 = 1860 行，非抽样）；再以仓内事实逐条交叉核对，并**复跑只读核验命令**。
- **审查边界（诚实声明）**: 本轮按任务书与 FEAT-025 R0 先例执行**只读**核验命令（`git show/rev-parse/hash-object/diff`、`python -B` 内省、`python -B -m unittest`、`coverage`、`-X importtime` 探针、`subprocess` 隔离探针）——**未修改任何产品代码、未写入任何仓库文件**。覆盖率运行产生的 1 个数据文件落在 `$env:TEMP`（仓外）并已即时删除；全部 python 调用带 `-B`/`PYTHONDONTWRITEBYTECODE=1`，无 `__pycache__` 残留。**未复跑全量回归**（任务书授予的边界为「复跑目标测试与覆盖率」；FEAT-025 R0 先例同口径），全量基线声称标注为**采信**并给交叉佐证（§三 #9）。
- **环境披露（在飞改动的归因纪律）**: 审查期间工作树另有 **FIX-303 / FIX-304 在飞改动**（`contracts.py`、`archguard_ratchet.py`、`core/architecture-baseline.json`、`tests/test_contracts.py`、`quickscan_registry.py`、`tests/test_quickscan_registry.py` 共 6 文件 `M`）。**归因一律以 commit 对象为准**：两被审文件与 blob 逐字节一致；设计契约 `contracts.py` 取 `36f2040:` 版本、`quickscan_registry.py` 取 `504cc8f:` 版本读取（`git diff 504cc8f 36f2040` 对该文件为**空**，两 commit 内容相同）。
  - **复跑口径的残余限制（如实登记）**：测试与覆盖率是在工作树上执行的，故实际加载的是 **FIX-303 版 `contracts.py`** 与 **FIX-304 版 `quickscan_registry.py`**。我核对了 FIX-303 的 `contracts.py` diff（+96/-46）：改动为 docstring 扩写、`_require_sequence` 的 `unique` 形参折入（两处调用点同步更新，内部自洽）、`to_legacy_dict` 增补复核、`_require_loader` 报错文案——**`CheckSpec` 的字段集与构造契约未变**（独立实测 `reg.CHECK_SPEC_FIELDS == ('check_id','domain','loader','input_deps','severity_floor','modes')`），故 registry 的消费面不受影响；FIX-304 面另有独立旁证（EVD-998：「FEAT-022 消费者 test_registry 单独复跑 71 OK（F-5 改名/F-6 导出零影响）」）。严格要求下的替代做法（materialize commit 状态）需要改动工作树，与本次审查边界冲突，故不做。

---

## 一、5 个评审维度逐项结论

### 维度 1：正确性 — 通过（含 P1×1 / P2×2 / P3×4）

**1.1 声明面与消费面逐项实测（验收①④的正面结论）。**
- 独立实测（`python -B` 直接内省，非采信测试）：`len(COMMAND_SPECS)==82`、`len(CHECK_SPECS)==70`、`all(isinstance(s, CheckSpec) for s in CHECK_SPECS)==True`、`CHECK_SPEC_FIELDS==('check_id','domain','loader','input_deps','severity_floor','modes')` —— 与 §3.6 `CheckSpec` 字段集**逐项相等**，`reg.CheckSpec is contracts.CheckSpec` 为同一对象（消费而非重定义，:89-93/:644）。
- **82 键 82/82 与 70 段 70/70 的 loader 全部解析为 callable**（独立执行 `load_handler`/`load_check` 全遍历）：无一处幻觉模块/属性（AI 专项 ③，§3.1）。`legacy_engine_hosted()` 实测 46 段；非引擎宿主命令键实测 4 个（`archguard-ratchet` / `check-capability-registry` / `check-manifest-consistency` / `check-review-debt`），与 :339-342 docstring 的「4 键已在巨石外，其余 78 骑巨石」自洽（82−4=78；70−46=24 段域宿主）。
- **白名单封闭性与完备性双向实测**（docstring :196-201 声称「恰好是两表点名的模块」）：`used - whitelist == ∅` 且 **`whitelist - used == ∅`**（14 个模块无一冗余、无一未声明）—— 该声称经独立复算为**真**。
- **R5 四路机判独立复跑**：`verify_registration()` 实测 `source=live-engine`、`ok=True`、`82==82`、`70==70`、`missing/extra` 双轴全空；冻结快照路径（`snapshots.json` faces）测试通过；missing/extra 负对照有牙（:651-680）；漂移披露非静默（`lines()` :819-837 双轴分别打印 `[FAIL] … registration drift` / `… declaration is stale`）。
- **导入期 join 守卫**（:606-641）读码确认：`set(_segments.registry_ids()) != authored` → `RegistryError` 并**双向点名差集**（:616-619）；`modes` 落空 → `RegistryError`（:626-629）。两分支由 `ImportTimeGuardTests` 以子进程 stub 探针 + **负对照**（:956-959 未改桩则可导入）证明「这两处 import 失败的唯一原因就是桩」——守卫有牙。
- **边界与 fail-closed 对称性**：绝大多数入口对空/非 str/畸形/未知输入均 fail-closed 且报错信息携带 `repr(入参)`（`command_spec` :544-551、`segment_of` :593-603、`select_checks` :699-753、`loader_module`/`loader_attr` :436-466）。**发现一处不对称**：`check_id_of()`（:585-590）只校验类型不校验段形式 → **F-6**。
- **并发安全**：模块级可变对象仅 `_BY_KEY`/`_BY_CHECK_ID`/`_BY_SEGMENT` 三个 dict，均在导入期填充后**只读**；`CommandSpec`/`CheckSpec`/`Assembly`/`RegistrationReport` 为 `frozen=True`；无全局缓存、无惰性突变 ⇒ 未发现并发风险。
- **资源管理**：产品代码零文件句柄（`resolve_loader` 只 `importlib.import_module`）；测试侧 `subprocess.run` 全部带 `timeout=180`、`capture_output`、显式 `encoding="utf-8"`（:169-184），无泄漏进程/句柄。
- **发现**：F-1（P1，R5 provenance 与实际观测面矛盾）、F-2（P2，单轴注入自我比较）、F-6（P2，`check_id_of` fail-open）。

### 维度 2：安全性 — 通过（无发现；含 1 条 P3 加固建议）

- **注入防护（本模块的核心安全控制）**：模块内**唯一**导入点是 `resolve_loader`（:479-505），其前置门槛 `_ensure_whitelisted`（:469-476）以**模块全名**做白名单判定 ⇒ 子模块穿越被结构性阻断。实测：`resolve_loader("verify_workflow.__init__.__globals__")` → `LoaderWhitelistViolation`（module part = `verify_workflow.__init__`，不在白名单）。
- **输入校验**：`_LOADER_SEGMENT_RE`（:429，锚定 `^[A-Za-z_][A-Za-z0-9_]*$`）逐一校验 module 与 attr；`.py` 后缀、`/`、`\`、`:` 一律拒绝（:441-445/:462-465）——文件路径注入面被封。
- **危险构造零命中**：独立读码 + :587-596 机判（`ast.Name`/`ast.Attribute`/`ast.Import` 三面扫描）确认 registry.py 内无 `eval`/`exec`/`compile`/`__import__`/`open`/`pkgutil`/`walk_packages`/`glob`/`iterdir`/`os.system`/`subprocess` —— 与 §9.1「禁止目录扫描/pkgutil 全量发现」一致。
- **第三方面**：`_live_faces()`（:840-855）导入 `contract_matrix.generator`，属 FEAT-020 自产模块（非第三方），且**延迟导入**（不在 import 期）。
- **敏感数据**：两文件零密钥/token/凭据/绝对用户路径硬编码（仅有 `str(_INFRA_DIR)` 这类运行时派生路径）。
- **权限检查**：N/A（纯库模块，无 IO 权限面、无网络）。
- **残余（P3 加固建议，非发现）**：`getattr(module, attr)` 未排除 dunder 属性 —— 理论上白名单模块的任何 callable 属性（含 `__loader__` 等）都可被指名。**实测四个 dunder 路径全部 fail-closed**（`archguard_ratchet.__loader__` / `.__dict__` / `checks.manifest.__loader__` → `LoaderResolutionError`；`verify_workflow.__init__.__globals__` → `LoaderWhitelistViolation`），**未发现可用暴露面**（且调用方本就持有 `import` 权，不构成提权）。建议后续在 `loader_attr` 加一条 `startswith("__")` 拒绝，属卫生加固。

### 维度 3：可维护性 — 通过（含 P2×1 / P3×3）

- **命名与文档**：`command_spec`/`check_spec`/`resolve_loader`/`assemble`/`verify_registration` 表意清晰；错误族为单一链式基类（`RegistryError(ValueError)` ← `UnknownCommandKey`/`UnknownCheckID`/`LoaderWhitelistViolation`/`LoaderResolutionError`，:206-223），且 :581-585 有测试钉住继承关系。
- **函数长度 / 职责单一**：全部函数 < 50 行（最长 `resolve_loader` 27 行含注释、`_build_check_specs` 36 行含 docstring）；897 行中约 190 行为两张**声明表**（§5.1 判定的「适合表驱动」类），约 40% 为带事实锚点的 docstring —— 属「数据表 + 极薄逻辑」，符合 §3.5「一项可独立调度的 Check = 一个注册项，不强制一项=一个文件」。
- **重复代码**：无。loader 解析单一所有者（`loader_module`/`loader_attr`/`_ensure_whitelisted`）；两表共用同一解析路径；**FEAT-025 事实为消费而非拷贝**——`domain`/`input_deps`/`modes` 在导入期由 `_segments.segment()` join 而来（:623-635），独立实测 `modes` 取值集 = `{('full',), ('full','quick')}`，与 FEAT-025 面逐段一致（测试 :349-356 另钉 `domain`/`input_deps` 恒等）。
- **注释质量**：本仓标杆级——模块 docstring 分「事实源清单（消费而非二次派生）/ 四条 caliber 决策 / 显式非目标」；**每条 caliber 都锚定到具体事实**（如 :40-56 用 `contracts._require_loader` 的形态约束解释为何 loader 必须属性限定、:50-56 用引擎 AST 测量解释 `severity_floor` 口径）。我逐条抽查了这些声称，**未发现一处与代码或事实不符**。
- **可维护性风险**：F-1（provenance 与观测面矛盾，最易被后续消费者误信）、F-2（`ok` 不区分「已观测」与「自我比较」）。
- **已核实可接受的设计固有约束（非发现）**：① `ADVISORY_SEGMENTS`（:153-166）是引擎可派生事实的**冻结读数**（7 段元组硬编码），但由测试对引擎 AST 重判（:358-366），漂移必红——因 §9.1 禁止 import 期读文件，硬编码 + 测试重判是唯一合规形态；② 模块只能在 `infra/` 位于 `sys.path` 时导入（`from contracts import …` :89-93；docstring :40-49 已披露并解释为何不用 `infra.` 前缀），与全树既有扁平导入约定一致，但会封死「把 infra 树打包为 package」的后续选项（属 §10 `REFACTOR-main-thin-entry`/晚期切片的议题，非本切片缺陷）；③ 导入 `quickscan_registry` 时若其自检先抛 `ValueError`（FEAT-025 :698-699）会先于 `RegistryError` 显形，属两模块守卫先后次序，无行为影响。

### 维度 4：性能 — 通过（无 P0/P1；验收②的正面结论）

- **import 成本实测（口径 §9.5 / R6）**：`-X importtime` 独立复跑 ⇒ **95 行 / 93 distinct modules / 引擎家族（`verify_workflow`、`checks.*`、`release.*`、`loop_runtime.*`）命中 0 行**，与声称逐数字吻合；`import registry` 后 `sys.modules` = **100**，`assemble('archguard-ratchet')` 后 = **113**，引擎自身启动面 = **196** ⇒ 懒加载收益「113 < 196」实测成立，且**轻命令装配全程不拉引擎**。
- **按命令加载的有效性**：`test_assembling_a_light_command_loads_only_its_module` / `test_loading_a_domain_check_does_not_pull_the_engine` 断言 `verify_workflow not in sys.modules` 且 handler 的 `__module__` 正确 ⇒ 「按命令 import 所选 handler」（§9.1 启动链第二步）为真机判，非装饰。
- **算法复杂度**：产品代码导入期工作 = 1 次 `sorted(82 元组)` + 1 次 O(70) join + 3 次 O(n) dict 构造；查询 O(1)；无 O(n²)、无循环内 I/O、无网络。测试侧 `_segment_facts()` 为 O(AST 节点 × 70) 且 `_engine_modules()` 全树重解析，属**测试期**成本（单模块 71 例 17.7s，可接受）。
- **反向风险（构成 F-1）**：`verify_registration` 的 `source=` 参数可让调用方以为在做「冻结快照」比对，实际触发 `_live_faces()` → 引擎导入 —— 这是本模块唯一一处会削弱自身懒加载承诺的可用路径（详见 §四 F-1）。
- **批量操作**：无（无 I/O 批处理面）。

### 维度 5：测试覆盖 — 通过（含 P1×1 / P2×2 / P3×3）

- **清点与复跑**：`def test_` 静态逐类清点 = ContractShape 6 + CommandRegistry 7 + CheckRegistry 13 + DelegatedLoader 2 + LoaderWhitelist 14 + CompositionRoot 5 + RegistrationIntegrity 8 + StartupImport 9 + DeclarationFace 4 + ImportTimeGuard 3 = **71**，与声称一致；**独立复跑 71 tests OK**（`python -B -m unittest discover`，Python 3.14.3，17.7s / coverage 包裹 19.4s，两次均 OK）。
- **覆盖率独立复跑逐数字吻合**：**248 stmts / 8 miss = 97%**，`Missing = 491-492, 535, 616, 627, 652, 848-849` —— 与 EVD-996 声称的「248 stmts/8 miss=97%（8 行=子进程探针面 6+声明表去重守卫 2）」**逐项吻合**，且分类可逐行验证：`491-492`（`resolve_loader` 导入失败重抛）+ `616`（join 守卫 raise）+ `627`（modes 守卫 raise）+ `848-849`（provider 不可用 raise）= **6 行子进程探针面**；`535` + `652` = **2 行声明表去重守卫**。97% ≥ standard 70% / strict 90% 双档均达标。
- **五类覆盖齐备**：合法路径（全遍历断言）、非法路径（未声明键/未知 CheckID/非白名单模块/畸形路径/非标识符/缺属性/非 callable/白名单导入失败 八类均有负对照）、边界（空串、空白、非 str、非契约 mode token、`domain:` 空名、未知域）、不可变（frozen 对象与 `Assembly` 等值面）、**交叉核对（读真事实源，非空断言）**：真读 `contract_matrix/snapshots.json`、真读 `checks/*` 与引擎源码做「符号定义模块」与「段内调用」双向核对（:140-155/:368-387）、真读 `core/architecture-baseline.json` r6 块。
- **负对照有牙（本仓标准）**：missing/extra 双轴合成投影（:651-680）、漂移双轴披露断言（:690-704）、provider 缺失 → `RegistryError` 且注入路径仍可判（:717-737）、导入期 join 守卫的「唯一失败原因」反证（:956-959）。`DelegatedLoaderTests`（:445-471）更进一步：用 AST 证明引擎侧 wrapper 是**单语句委托**且指向声明 loader —— 这是把「披露」变成机判的正面范例。
- **测试卫生**：产品代码零 mock；测试侧仅**一处**刻意故障注入（`types.ModuleType` 桩 + `sys.modules[...] = None`，:923-937/:516-537），且带负对照 ⇒ 属合法负对照技术，**非 mock 残留**。
- **覆盖缺口**：F-1（`source=` 单独传入路径无测试）、F-6（`check_id_of` 畸形输入无测试）、F-2（单轴自我比较有测试但钉住的是「可绿」而非「须披露」）；另两条 P3：两处去重守卫（L535/L652）无负对照（注入需改模块源码，成本高，可接受但应登记）；`test_report_renders_every_face`（:682-688）仅断言 `"82"`/`"70"` 子串存在，近乎恒真（真实数字由 :754-757 覆盖）。

---

## 二、AI 代码专项 5 项检查

| # | 检查项 | 结论 | 事实依据（可复查） |
|---|---|---|---|
| ① | mock 残留 | **无** | 产品代码零 `unittest.mock`/`MagicMock`/`patch`/`monkeypatch`；测试侧仅 :923-937 一处 `types.ModuleType` 桩与 :516-537 `sys.modules[name]=None`，二者均为导入期守卫的**故障注入负对照**并各自配有反证对照组 |
| ② | 硬编码返回值 | **无（且无掩盖）** | 82/70 条 loader 全解析为真实 callable（独立全遍历）；测试常量 `FROZEN_CLI_KEYS=82`/`FROZEN_SEGMENTS=70`/`FROZEN_ENGINE_IMPORT_COUNT=196`（:66-71）非唯一判据——同文件另有快照**集合**恒等（:274-276/:332-334）、FEAT-025 面恒等（:336-337/:349-356）、引擎实测（:749-757/:816-829）三路独立判据；`ADVISORY_SEGMENTS` 为硬编码 7 元组但由引擎 AST 重判（:358-366），漂移必红 |
| ③ | 幻觉 API 调用 | **无** | 逐符号核实消费面：`contracts.{CheckSpec,CheckID,CommandKey}`（实测同对象）、`quickscan_registry.{registry_ids,segment}`（实测 70/70 join 成功）、`contract_matrix.generator.{extract_cli_dispatch,extract_check_segments}`（实测 `verify_registration()` 走通并返回 82/70）、`perf_protocol.parse_importtime`（实测解析出 95 行）；测试 :140-155 的「符号定义模块」机判使任何幻觉 loader 必红 |
| ④ | 未实现 TODO | **无** | 两文件零 `TODO`/`FIXME`/`XXX`/`NotImplemented`/`pass  #` 占位（全文扫描命中集为空）；未落地项以**显式非目标**形式写在 docstring :68-79（命令范围执行上下文、command→check 绑定），非静默 stub |
| ⑤ | 过度实现 | **无** | 落在 §10 L517 范围（命令键→handler 路径 + CheckID→CheckSpec + 受控 loader 白名单 + L6 组合根雏形）内；`Assembly`/`select_checks` 是 §9.3 的**选择接缝**——只做 token 与已声明字段的匹配，**不派生策略、不读变更文件**（docstring :701-707 显式声明策略属 L4），未越界为 quick-scan 编排实现（那属 `REFACTOR-quickscan-orchestration`）；`verify_registration` 由验收①直接要求；长 docstring 为文档而非功能 |

---

## 三、设计一致性逐项比对

| 设计条目 | 实现位置 | 判定 |
|---|---|---|
| §10 **L517** 验收① R5 注册完整性 PASS | :606-641（导入期 join 守卫）+ :788-897（`verify_registration`/`RegistrationReport`） | ✅ 一致（独立复跑 live 82==82 / 70==70 双轴全空；冻结快照面测试通过；负对照与披露齐备） |
| §10 **L517** 验收② 启动 import 集合不增（`-X importtime` 对照） | :84-95（模块级导入仅 stdlib+`contracts`+`quickscan_registry`）+ 测试 :763-865 | ✅ 一致（复跑 95 行/93 distinct/0 引擎行；引擎 R6 面 196==196 Δ0；registry=100、assemble=113 < 196）。**口径瑕疵见 F-4/F-5** |
| §10 **L517** 验收③ 装配路径测试 | :469-505 `resolve_loader` + 测试 :477-596 | ✅ 一致（fail-closed 六类齐备，其中五类经我直接执行验证异常类型，第六类经子进程探针验证） |
| §3.2 L146 L6 组合根职责「按命令装配实现」/「禁 import 时实例化全部服务」 | :759-785 `Assembly`/`assemble` | ✅ 一致（`assemble` 只解析**一个**命令的 handler；实测装配后不拉引擎） |
| §3.2 L113 依赖方向「只允许上层 import 下层」/ L0 零依赖 | :89-95（L6 → L0 `contracts` + L1 `quickscan_registry`）；`contracts.py` 零 in-repo import | ✅ 一致（未有 L0/L1/L2/L3 反向 import registry：AST 全树扫描 **0 个非测试模块**导入 registry） |
| §3.5 L174 稳定 Check ID（含子相位，如 `check-28p`） | :141-142/:585-603（`check-<segment>`） | ✅ 一致（70 段全含子相位 `18b~18i`/`28b~28u`/`30b~30c`，`CHECK_ID_PATTERN` 由 L0 提供） |
| §3.5 L176 命令键冻结「注册项（键→handler 模块路径），不强制新文件」 | :228-342（82 键）+ :511-531（`CommandSpec`） | ✅ 一致（键集合与 FEAT-020 冻结面**集合恒等**，测试 :274-276） |
| §3.6 `CheckSpec` 六字段形状（`check_id/domain/loader/input_deps/severity_floor/modes`） | :631-640 构造 `contracts.CheckSpec`；:646-648 字段元组取别名 | ✅ 一致（字段元组恒等 + `isinstance` 恒等 + AST 零重定义三项机判齐备） |
| §3.6 L218 `loader: str  # 模块路径字符串（受控白名单加载）` | :436-505（属性限定点分路径）+ `LOADER_WHITELIST` | ✅ 一致（受控白名单落地；形态由 L0 `_require_loader` 强约束，docstring :40-49 说明为何须属性限定） |
| §3.6 L219 `input_deps` / L221 `modes` | :635/:624-625（由 FEAT-025 join） | ✅ 一致（无第二份真相）。**`modes` 不含 `domain:<name>` 字面（与 §3.6 示例的差异属披露口径，见 F-9）** |
| §9.1「注册表只含轻量元数据」 | 全表的值为字符串/元组，无 callable、无实例 | ✅ 一致（`CheckSpec` 持 `loader` 字符串而非已导入对象） |
| §9.1 四条禁令（无目录扫描/pkgutil、无入口 import 全部命令、import 期不读文件/Git、import 期不实例化全部服务） | :84-95 + :606-652（仅纯计算） | ✅ 一致（机判 :587-596 + 我的读码；`-X importtime` 实测 0 引擎行） |
| §9.1「受控 loader 白名单（R5 校验路径可解析性 + 装配路径测试）」 | :180-201（14 模块封闭元组）+ :479-505 | ✅ 一致（白名单与实耗集合双向恒等；解析失败四类均 fail-closed 带上下文） |
| §4.1 **R5**「Check ID 唯一 / 元信息完备 / 80 命令键全覆盖 / loader 路径可解析」 | :534-535 + :651-652（唯一性）+ :606-641（完整性）+ :479-505（可解析） | ✅ 一致（唯一性守卫导入期生效；键/段覆盖率实测 82/82、70/70） |
| §4.1 R5 存量政策「建立时与 facts §3.2/§3.3 清单对账」 | 测试对 FEAT-020 冻结快照 + 活引擎双路对账 | ✅ 一致（双路均 PASS；`contract_matrix.generator` 为 FEAT-020 自有 extractor，消费而非重实现） |
| §9.5/§4.1 R6 启动成本口径（`python -X importtime`） | 测试 :193-201（消费 `perf_protocol.parse_importtime`）、:831-852 | ✅ 一致（口径归属单一：`parse_importtime` 为唯一所有者，不重实现）。**记录口径例外见 F-4** |
| §3.6 端口（`GovernanceStore`/`FilesystemPort`/`GitPort`/`ClockPort`） | 本切片**未**实现（属后续 L0 批次） | ✅ 一致（docstring :68-79 显式列为非目标；未伪装成已落地） |

**设计一致性结论**：无一处实现偏离 §10 L517 / §3.2 / §3.5 / §3.6 / §9.1 / §4.1 的**硬约束**；三处差异（`modes` 词表口径 F-9、`severity_floor` 语义承载 F-10、R6 记录口径 F-4）均为**已披露的口径选择**或记录面瑕疵，不构成功能偏离，但建议按 §四处置。

---

## 四、发现清单

> 每条含级别 / 位置 / 事实依据 / 影响 / 修复建议。级别口径：P0 阻塞（须改才可合并）／P1 关键（强烈建议本轮或紧随补丁轮）／P2 建议／P3 讨论。

### F-1（P1）R5 报告的 `source` 与实际观测面矛盾，且该路径静默导入引擎

- **位置**：`infra/registry.py:863-884`（分支 :876-884）；相关 :790-793（`LIVE_SOURCE`/`INJECTED_SOURCE`）、:840-855（`_live_faces` 延迟导入）
- **事实依据（我执行得到的输出，非推断）**：以隔离进程调用 `verify_registration(source="frozen-snapshot")`（不传任何 observed 面）⇒ `engine_before=False` → `engine_after=True`、`reported_source='frozen-snapshot'`。读码可解释：`if observed_cli_keys is None and observed_segment_ids is None:` 成立 ⇒ 走**活引擎**分支调用 `_live_faces()`；随后 `source = source or LIVE_SOURCE` 因入参为真值而**保留调用方标签**。唯一的 `source=` 测试（`test_registry.py:739-747`）同时传入两个观测面，故该路径**零覆盖**。
- **影响**：① 证据完整性——`source` 是 R5「漂移披露非静默」的 provenance 通道，标签与事实不符即等于**伪证**（本审查charter 的重点防范族）；② 可用性/性能——调用方用 `source="frozen-snapshot"` 的**动机**正是规避引擎导入做廉价比对，实际却触发 `from contract_matrix import generator` → 拉入巨石，与 §9.1 的懒加载纪律及验收②的立意相悖；③ 一旦 R5 被接进启动链或棘轮（EVD-996 已披露「棘轮 R5 尚未消费 registry」，实测 `archguard_ratchet.py` 对 `registry`/`verify_registration` **零引用**），本缺陷会从「P1 潜在」升级为「启动成本回归」。
- **修复建议（≤8 行）**：让 provenance 由**观测事实**派生而非由入参决定——例如在活引擎分支强制 `source = LIVE_SOURCE`（拒绝与观测矛盾的入参，或改为 `raise`），或干脆移除 `source` 形参、由函数自贴标签；并补一条 `source=` 单独传入的测试（断言 `source == LIVE_SOURCE`，或断言该调用被拒）。

### F-2（P2）单轴注入时未观测轴的声明被当作观测结果，`ok` 可绿而该轴从未被观测

- **位置**：`infra/registry.py:879-884`（`observed_cli_keys = _COMMAND_KEYS` / `observed_segment_ids = _SEGMENTS`）、`RegistrationReport.ok` :814-817、`lines()` :819-837
- **事实依据**：`verify_registration(observed_cli_keys=list(reg.command_keys()))` 实测 `observed_segments == declared_segments`、`ok == True`；`lines()` 输出两轴计数外形完全对称，无任何「本轴未观测」标记。
- **影响**：`ok` 与 `lines()` 是下游唯一消费面（`ok` 单布尔、`lines()` 面向人/日志），二者都无法区分「双轴实测」「单轴实测 + 单轴自我比较」。这正是 FEAT-025 R0 F-1「假绿」的同族风险——虽然本包尚未有消费者，但把它登记为已知弱点可避免后续切片在「R5 PASS」字样下误信覆盖面。
- **加重/减轻说明（诚实标注）**：该行为**已在 docstring :870-875 披露**，且**已被测试钉住**（:706-715）——故**不是隐藏缺陷**，而是「有意的单轴便利」缺少披露字段。这一点使其实质风险低于 F-1，故定级 P2 而非 P1。
- **修复建议**：在 `RegistrationReport` 增补 `observed_axes: Tuple[str, ...]`（或令未观测轴的 `observed_*` 保持 `None`），并在 `lines()` 对未观测轴打印 `unobserved (defaulted to declaration)`；调用方从而无法把自我比较误读为实测。

### F-3（P2）续作测试增量枚举自相矛盾：声称 +23，枚举之和为 24

- **位置**：commit `36f2040` message；`.governance/evidence-log.md:1955`（EVD-996）
- **事实依据**：声称「续作 +23：DeclarationFaceTests×4／ImportTimeGuardTests×3／LoaderWhitelist+6／CheckRegistry+3／RegistrationIntegrity+3／StartupImport+4／CompositionRoot+1」⇒ 4+3+6+3+3+4+1 = **24**，与 +23 差 1；我独立测得总数为 **71**（静态 `def test_` 逐类清点 + 实跑），与「48 + 23 = 71」一致 ⇒ 两数中必有一错：若「+23」正确则**前会话数应为 47**（而非 48），否则某项枚举计数应减 1。
- **影响**：前会话 48 例本就**无树内证据**（EVD-996 如实标注 UNVERIFIABLE），是分组中唯一的自由变量；枚举自相矛盾使后续审计无法重建「前 48 / 后 +N」的切分，削弱该条披露的可复核性。**纯记录面缺陷，不影响代码与验收**。
- **修复建议**：Coordinator 在治理记录中更正为自洽的一组数字（并明示哪一处被修正）——建议保留可实测的 71 与枚举明细，将前会话数标注为 47 或「≈48（明细未留痕）」。

### F-4（P2）验收② 的对照口径引用了**不能按字面执行**的 probe 字符串

- **位置**：`test_registry.py:766-771`（断言 r6 `probe` 字面量）、`core/architecture-baseline.json` r6 `probe` 字段；执行侧 `test_registry.py:162-166`（`_isolated_script`）
- **事实依据**：字面命令 `python -I -B -c "import verify_workflow"` 实测 **ModuleNotFoundError**（`-I` 蕴含 `-P`，cwd 不进 `sys.path`）；同一数字仅在**显式注入 infra 目录**后可得（`sys.path.insert(0,'.')` ⇒ 196）。生产者签名亦印证：`perf_protocol.probe_sys_modules(infra_dir: Path)`、`archguard_ratchet.measure_cold_import(infra_dir_str)` **都要求传入 infra 目录**。而 :766-771 把该字符串作为**验收②的比较框架**钉死，测试自身却用注入了 `sys.path` 的探针（:162-166）。
- **影响**：记录的 R6 口径无法复现其自身记录的数字——按本测试自己的原则（`_run_isolated` 注释：「未运行的测量绝不能看起来像通过的测量」，:170-174），口径串失效属同一族问题。**196==196 Δ0 的结论本身不受影响**（我以实际执行口径复现了 196，见 §一维度 4），故是**记录/口径缺陷**而非结论缺陷。
- **修复建议**：更正 baseline 的 `probe` 串为可执行形态（含 `sys.path` 注入说明或等价的可复现命令），并把 :766-771 的断言改为钉住**可执行**形态；baseline 属 archguard 侧产物（`core/architecture-baseline.json` 的 owner 非本包），故建议以「本包改断言 + baseline 更正登记」双线处置。另注意该文件当前正处于 FIX-303 在飞改动中，归因以 `36f2040:` 版本为准。

### F-5（P3）R6 对照只消费 `import_count`，未消费 baseline 已记录的 `import_set_sha256`

- **位置**：`test_registry.py:766-771` / `816-829`；`core/architecture-baseline.json` r6 的 `import_set_sha256`
- **事实依据**：r6 块同时记录 `import_count` 与 `import_set_sha256`（由 `perf_protocol.probe_sys_modules`、`archguard_ratchet.measure_cold_import` 产出）；测试只断言计数 == 196，另加 3 个名字的**负成员**断言（`registry`/`contracts`/`quickscan_registry` 不在引擎面）。
- **影响**：「计数相同、集合不同」的引擎面漂移不会被捕获。**对本包风险为零**——36f2040 对 `verify_workflow.py` **零改动**（`--stat` 仅 2 个新文件），引擎面不可能被本切片改变，故纯属口径面可加强项。
- **修复建议**：若 `import_set_sha256` 的规范化规则（排序 + 连接形态）在生产者侧稳定，测试可直接对该面断言，取代计数比较。

### F-6（P2）`check_id_of()` 不校验段形式，与同族 `segment_of()` 的 fail-closed 口径不对称

- **位置**：`infra/registry.py:585-590`（对照 `segment_of` :593-603；`_SEGMENT_RE` 已在 :575 存在）
- **事实依据（我执行得到的输出）**：`check_id_of("")` → `'check-'`；`check_id_of("   ")` → `'check-   '`；`check_id_of("28p!")` → `'check-28p!'`；`check_id_of("nosuch")` → `'check-nosuch'`；仅非 str（`-1`）抛 `UnknownCheckID`。而同族 `segment_of("")` / `segment_of("nosuch")` **均抛 `UnknownCheckID`**。测试仅覆盖 `check_id_of(None)`（:427-428）。
- **影响**：`check_id_of` 是 `__all__` 公开 API（:116），其 docstring 承诺「Bare segment → stable CheckID」，实现却对任意字符串**拼接前缀**产出不符合 `CHECK_ID_PATTERN` 的 CheckID；这与模块自述纪律（:207「fail-closed, never guessed」）及同族函数口径相悖。**实际危害有限**——该伪造 ID 后续经 `check_spec()` 仍会干净地 fail-closed，无错派发/错门禁风险。
- **修复建议**：以既有 `_SEGMENT_RE` 校验并抛 `UnknownCheckID`（复用 `segment_of` 的报错风格），并把 `""`/`"28p!"`/`"nosuch"` 补进 `test_check_id_and_segment_forms_fail_closed`（:422-428）。

### F-7（P3）`handler_alias_groups()` 按 attr 名分组，忽略所属模块

- **位置**：`infra/registry.py:564-570`
- **事实依据**：分组键为 `loader_attr(spec.handler)`（丢弃模块部分）。实测当前 3 个别名组全部位于 `verify_workflow` 内（`cmd_check_deterministic_scaffolds`/`cmd_check_interruption_policy`/`cmd_dynamic_lifecycle_migration`），**无跨模块重名**，故当下无缺陷。若未来两个不同模块定义同名 handler，二者会被并入同一别名组，产生错误的别名披露，且与冻结快照的 `alias_groups` 对账会以「别名差异」而非「命名冲突」的形式呈现，掩盖真实问题。
- **修复建议**：以完整点分路径作为分组键（或对「同名不同模块」显式抛错）。

### F-8（P3）`assemble()` 先导入 handler，再校验 selection token

- **位置**：`infra/registry.py:774-785`
- **事实依据**：执行序为 `command_spec(key)` → `resolve_loader(spec.handler)`（**导入副作用**）→ `select_checks(...)`（非法 token 在此抛错）。故 `assemble("status", mode="nosuch")` 会先完成模块导入再失败。
- **影响**：无状态损坏（导入是幂等且无副作用的），但在「按命令启动」终态下，先校验后副作用能让 fail-closed 次序更干净、也避免未来的诊断噪声。
- **修复建议**：把 `select_checks` 的 token 校验前置到 `resolve_loader` 之前，或先 `_require_mode_token`/`_require_domain_token` 再解析 handler。

### F-9（P3）`modes` 只落 `full`/`quick`，`domain:<name>` 不进入 `CheckSpec.modes`（与 §3.6 L221 示例字面不同）

- **位置**：`infra/registry.py:150-151`（`CONTRACT_MODE_VOCABULARY`）、:624-625（join 过滤）、:699-753（`domain:` 作为**选择器**处理）；docstring 披露 :62-66
- **事实依据**：实测 `modes` 取值集 = `{('full',), ('full','quick')}`——**不含任何 `domain:` 项**。§3.6 的注释写作 `# ("full", "quick", "domain:<name>")`。
- **影响**：差异**已披露且理由充分**（FEAT-025 的 `not-quick:<CODE>` 是政策 token 非 mode 名，且理由码归 FEAT-025 所有；测试 :349-356 钉住与 FEAT-025 的忠实性）。风险仅在语义预期：后续消费者若按 §3.6 示例把 `modes` 当作「完整可用选择器词表」，会发现域选择器缺席。
- **修复建议**：在 L0 契约 docstring 或一条 DEC 中记录「`modes` 只承载执行模式；域选择器由 L4/registry 的 selector 面表达」，使口径离开本模块的 docstring 而进入契约层。

### F-10（P3）`severity_floor` 承载了「是否可能进入 gate」的语义，该解释为本包自有

- **位置**：`infra/registry.py:147-166`（`SEVERITY_FLOOR_BLOCKING`/`ADVISORY` + `ADVISORY_SEGMENTS`）、:636-638（赋值）；契约侧 `contracts.py:373`/`:388-390`
- **事实依据**：`WARN` 用于「段内从不对 `all_issues` 自增」的 7 段（实测 28p/28q/28r/28s/28t/30c/39），`BLOCKING` 用于其余；§3.6 声明 `severity_floor: str` 但**未定义取值域与语义**，L0 只校验 ∈ `("BLOCKING","WARN","INFO")`。docstring :50-56 披露该 caliber，测试 :358-366 以引擎 AST 重判。
- **影响**：包内自洽且机器重判，无缺陷；但「floor」在通用语义上指**严重度下限**，本实现用它表达「可能进入 gate 的严重度」，第二个消费者可能另作解读。
- **修复建议**：在 L0/§3.6 批次补一句字段语义（或待 §3.6 二次修订时显式登记口径）。

### F-11（P3）「引擎零 import registry」由**子串扫描**背书，可加强为 AST 机判（该声称经我以更强事实核为真）

- **位置**：`test_registry.py:810-814`（`assertNotIn("import registry", source)` / `"from registry import"`）
- **事实依据**：子串扫描可被 `import  registry`（双空格）、`importlib.import_module("registry")`、`from x import registry` 等形态绕过。我以 **AST 全树扫描**（`infra/` 下全部非测试 `.py` 的 `ast.Import`/`ast.ImportFrom`/`import_module("registry")`）复验 ⇒ **命中 0 个产品模块**（唯一命中是 `tests/test_registry.py:53`）⇒ **声称「引擎未接线」为真**，且另有更强独立证据：`git show --stat 36f2040` 证明 `verify_workflow.py` **零改动**（本 commit 仅 2 个新增文件）。同日，棘轮侧「R5 尚未消费 registry」亦经实测为真（`archguard_ratchet.py` 对 `registry`/`verify_registration` 零引用）。
- **影响**：事实无虞，仅测试的**举证强度**弱于可得手段；若后续有人破坏接线，该测试可能漏报。
- **修复建议**：把该断言改为与 `ContractShapeTests` 同族的 AST 机判（:245-261 已有现成范式）。

---

## 五、验收标准逐条裁决

| # | 验收标准（§10 L517 + 任务书 6 条） | 裁决 | 事实依据（可复查） |
|---|---|---|---|
| 1 | **R5 注册完整性（声明面↔实际面机判）** | **PASS**（附 F-1/F-2 口径加强项） | 独立复跑 `verify_registration()`：`source=live-engine`、`ok=True`、keys 82==82、segments 70==70、`missing/extra` 双轴全空；冻结快照面（`snapshots.json`）测试通过；missing+extra 合成负对照有牙（:651-680）；漂移双轴披露非静默（:690-704 断言 `registration drift` + `declaration is stale` 并存）；导入期 join 守卫另有子进程 stub + 反证对照组（:942-959） |
| 2 | **启动 import 集合不增（importtime 口径 + 引擎 R6 Δ0）** | **PASS**（附 F-4/F-5 记录口径项） | `-X importtime` 独立复跑 = **95 行 / 93 distinct / 引擎家族 0 行**（与声称逐数字吻合）；`import registry` → `sys.modules` **100**；`assemble('archguard-ratchet')` → **113**；引擎自身启动面实测 **196** == baseline r6 `import_count` **196** ⇒ Δ0；运行时负成员断言（引擎面不含 `registry`/`contracts`/`quickscan_registry`）测试通过；本 commit 对引擎**零改动** |
| 3 | **装配路径测试（白名单 fail-closed 六类）** | **PASS** | 六类逐一核实：未声明键 → `UnknownCommandKey`（:566-572）、非白名单模块 → `LoaderWhitelistViolation`（:496-502）、畸形路径 → `LoaderResolutionError`（:504-507）、缺属性 → `LoaderResolutionError`（:509-514）、非 callable → `LoaderResolutionError`（:539-544）、白名单模块导入失败 → `LoaderResolutionError` 且 `__cause__=ModuleNotFoundError`（:516-537）。**前五类由我直接执行复现异常类型**，第六类由子进程探针在 71 例实跑中通过；另加非标识符面（:546-550） |
| 4 | **CheckSpec 形状一致（消费而非重定义）** | **PASS** | 四路独立证据：① `all(isinstance(spec, contracts.CheckSpec))` 实测 True；② `reg.CheckSpec is contracts.CheckSpec`（同对象，:230-231 测试钉住）；③ `CHECK_SPEC_FIELDS` 实测 == 契约字段元组（:233-239 另钉 `set(spec.__dict__)`）；④ AST 机判「registry 模块体不定义 L0 形状名」（:245-251）+ registry 确实 import `contracts`（:253-261）。同时 `qr.SEGMENT_SPEC_FIELDS ⊆ reg.CHECK_SPEC_FIELDS`（:241-243）成立 |
| 5 | **TDD 证据链（含 UNVERIFIABLE 部分标注是否得当）** | **PASS**（附 F-3 记录项） | **前会话 48 例红相位**：EVD-996 与 commit message 均**显式标注「红相位证据树内无存——UNVERIFIABLE 如实标注，不伪证」**（`.governance/evidence-log.md:1955`），**未把不可验写成已验** ⇒ 标注得当。**续作红→绿**：我以内存态复现其机制（把 `declared_domains` 从 `reg.__all__` 隐藏后跑 `DeclarationFaceTests`）⇒ `ran=4, failures=1`，失败点正是 `test_every_public_definition_is_exported`（报错文本含「declared_domains is public but missing from __all__」），与声称「红 failures=1〔declared_domains 断言〕」**逐项吻合**；绿相位经独立实跑 **71 tests OK** 复现。附注：红相位的**历史留痕**未入库（与我复现的机制一致，但机制可复现 ≠ 历史已留证），**F-3 另发现该增量的枚举与总数自相矛盾** |
| 6 | **AI 专项 5 项** | **PASS** | 见 §二：mock 残留 / 硬编码返回值 / 幻觉 API / 未实现 TODO / 过度实现，逐项有结论且每条附可复查事实（机判命中数、逐符号核实、独立执行输出） |

**裁决汇总：6/6 PASS。** 无验收标准未通过；F-1/F-2/F-6 是对**接口面与披露面**的加强项，F-3/F-4/F-5 属**记录与口径**项，均不改判本表。

---

## 六、硬门槛裁决

| 门槛 | 结果 |
|------|------|
| P0 阻塞问题数 = 0 | ✅ **0**（11 条发现中无 P0） |
| 5 维度全覆盖 = 100% | ✅ 正确性 / 安全性 / 可维护性 / 性能 / 测试覆盖逐项有结论（§一） |
| 每条发现标注级别 = 100% | ✅ F-1~F-11 全部标注 P1/P2/P3 + file:line + 事实依据 + 修复建议 |
| 设计一致性检查已完成 | ✅ 对照 §10 L517、§3.2、§3.5、§3.6、§9.1、§4.1 R5、§9.5/R6 共 **16 项**逐项比对（§三），另交叉核对 FEAT-021 `contracts.py` 与 FEAT-025 `quickscan_registry.py`@504cc8f 两个消费基准 |
| AI 代码专项 5 项检查全部完成 | ✅ 逐项有结论（§二） |
| 逐行读两文件全文 | ✅ 897 + 963 = **1860 行全文逐行**（非抽样、非抽样跳读）；并逐符号核对对侧事实（引擎段调用、符号定义模块、FEAT-025 行、快照面、baseline r6） |
| 声称与代码事实交叉核对（硬门槛 4） | ✅ 12 条声称逐条给出核查等级（§七）：**9 条独立复现**、**2 条采信（附独立旁证/静态论证）**、**2 条不符并登记为 F-3/F-4**（含一处「可按更强手段核为真但测试举证弱」→ F-11） |

---

## 七、声称与事实交叉核对（核查等级）

| # | Developer 声称（commit message / EVD-996） | 核查等级 | 我的实测/论证 |
|---|---|---|---|
| 1 | 82 命令键注册表 | ✅ 独立复现 | `len(COMMAND_SPECS)==82`；键集合与 FEAT-020 冻结快照**集合恒等** |
| 2 | 70 CheckSpec | ✅ 独立复现 | `len(CHECK_SPECS)==70`；段集合与快照 + FEAT-025 双面恒等 |
| 3 | 消费而非重定义（isinstance / 字段元组 / AST 零重定义） | ✅ 独立复现 | 三项机判齐备，字段元组实测恒等，`reg.CheckSpec is c.CheckSpec` |
| 4 | 受控 loader 白名单 | ✅ 独立复现 | 14 模块封闭元组；与实耗集合**双向恒等**（零冗余、零未声明）；越界/畸形/缺属性/非 callable 均 fail-closed |
| 5 | L6 assemble 组合根 + 按命令加载 | ✅ 独立复现 | `assemble('archguard-ratchet')` 后 `sys.modules`=113、引擎不在其中；`import registry`=100 < 196 |
| 6 | 导入期 join 守卫（FEAT-025 面分歧 → `RegistryError`） | ✅ 独立复现 | 读码确认 :615-619 + :626-629；测试以子进程 stub + 反证对照证明「唯一失败原因」 |
| 7 | R5 四路机判（live / 冻结快照 / missing+extra 负对照 / 漂移披露非静默） | ✅ 独立复现 | 四路逐路复跑：live 双轴 82/70 全空 PASS、快照面通过、负对照有牙、`lines()` 双轴 FAIL 披露 |
| 8 | `-X importtime` 95 行 / 93 distinct / 零引擎行 | ✅ 独立复现 | 独立探针 + `perf_protocol.parse_importtime` 解析 ⇒ **95 / 93 / 0**，逐数字吻合 |
| 9 | 引擎 R6 面 **196 == 196 Δ0**；全量 2580/32F+1E 与基线签名恒等 | ⚠️ **部分采信** | 196 面：✅ 实测 196 == baseline r6 `import_count` 196，且本 commit 对引擎零改动（`--stat` 2 文件）⇒ Δ0 成立。**全量 2580/32F+1E：未复跑**（超出任务书授予的「目标测试与覆盖率」边界），采信并附旁证：EVD-998（并行的 FIX-304）独立报告同一全量签名 `2580/32F+1E`，且其明确记录「FEAT-022 消费者 test_registry 单独复跑 **71 OK**（F-5 改名/F-6 导出零影响）」⇒ 与我的实跑互证（**唯一不一致处**：EVD-998 记为 `2580/32F+1E+1S`，EVD-996 记为 `2580/32F+1E`，差 1 个 skip，属两条并发证据的时点差，建议归一时序口径；因不影响 FEAT-022 的验收判据，登记为观察而非发现） |
| 10 | 装配路径 82 键全 callable + fail-closed 六类 | ✅ 独立复现 | 82/82 callable（全遍历）；六类异常类型逐一实测（五类直接执行、一类子进程探针） |
| 11 | 覆盖率 248 stmts / 8 miss = 97%（8 行分类：子进程探针面 6 + 去重守卫 2） | ✅ 独立复现 | `coverage` 独立复跑：**248 / 8 / 97%**，`Missing=491-492, 535, 616, 627, 652, 848-849`，**逐行分类与披露完全一致**（探针面 6 = 491-492/616/627/848-849；守卫 2 = 535/652） |
| 12 | 引擎未接线（`verify_workflow.py` 零修改）；棘轮 R5 尚未消费 registry | ✅ 独立复现（举证强于测试） | `--stat` 仅 2 新文件 ⇒ 引擎零修改；AST 全树扫描 **0 个产品模块** import registry；`archguard_ratchet.py` 对 registry/`verify_registration` **零引用**（测试侧仅 :810-814 子串扫描，已登记 F-11） |
| 13 | 续作 +23 测试（枚举 7 类）；前会话 48 例红相位 UNVERIFIABLE | ❌ **不符（F-3）** | 总数 71 与枚举明细实测吻合，**但枚举之和为 24 ≠ 声称的 +23**；UNVERIFIABLE 标注本身 ✅ 得当（第四列说明） |
| 14 | （间接）r6 记录口径可由 `probe` 串复现 | ❌ **不符（F-4）** | 字面 `python -I -B -c "import verify_workflow"` → `ModuleNotFoundError`；仅注入 `sys.path` 后得 196 |

**核对汇总**：14 条中 **10 条独立复现**、**2 条采信（附旁证）**、**2 条不符并已登记**（F-3 记录算术语、F-4 probe 口径串）。**未发现任何一条「把不可验写成已验」**（第 13 条的 UNVERIFIABLE 部分恰是正面范例）。

---

## 八、审查结论

# APPROVED_WITH_NOTES

unresolved_blockers=0

**终态理由**：§10 **L517** 的三条验收要点（R5 注册完整性 PASS、启动 import 集合不增、装配路径测试）**全部落地且各有机器可判的固定物**，六条验收标准逐条 PASS（§五）。关键结论均经**独立复跑**而非采信：R5 live 面 82==82 / 70==70 双轴全空；`-X importtime` **95 行/93 distinct/0 引擎行**；引擎 R6 面 **196==196 Δ0**；`registry` 导入面 100、`assemble` 后 **113 < 196**；本轮 71 例 **71 OK**；覆盖率 **248 stmts/8 miss=97%** 且 8 行分类**逐行吻合**披露；`CheckSpec` 消费面经 isinstance + 字段元组 + 同对象 + AST 四路核实；白名单与实耗集合**双向恒等**；82/82 与 70/70 loader 全部解析为真实 callable（零幻觉 API）。设计一致性 16 项逐项比对无硬约束偏离（§三）。AI 专项 5 项无异常（§二）。**P0 = 0** 且硬门槛全部通过 ⇒ 无未解决 BLOCKING finding；P1 仅 1 条且附关闭计划，满足 code-review SKILL「循环角色」段的通过终态契约，并以独立结构字段声明 `unresolved_blockers=0`。

**发现计数（独立行，供机器记录）**：P0 = 0；P1 = 1；P2 = 4；P3 = 6。

**唯一 P1（F-1）的处置要求**（按 code-review SKILL 第四步「P0=0 且 P1>0（有遗留计划）→ 有条件合并」）：F-1 是 R5 **provenance 通道**的逻辑缺陷（`source=` 与真实观测面矛盾，且顺手把引擎拉进来），修复成本 ≤8 行 + 1 条测试。**定级理由（供 Coordinator 复核）**：不升 P0 的依据是**当前无任何消费者**——AST 全树实测 0 个产品模块 import registry，棘轮对 `verify_registration` 零引用，故无数据/门禁损害面；不降 P2 的依据是它**直接削弱验收②的立意**，且是「假绿/伪证」族的同族风险。**MUST 在 R5 被接进启动链或棘轮之前修复**（EVD-996 已把「棘轮 R5 尚未消费 registry」列为后续切片事项）；若本轮不修，Coordinator **MUST 登记为遗留项并附关闭截止日期**，且该遗留项须绑定到「R5 扩面」切片的前置条件上。

**P2 处置要求**：F-2（单轴自我比较的披露字段）建议随 F-1 同批修复（同文件、相邻行）；F-6（`check_id_of` fail-closed 对称性）成本 ≤5 行 + 3 个测试用例，建议本轮或紧随补丁轮落地；F-3/F-4 属治理记录与口径串更正，**不影响任何验收裁决**，建议随本轮 review-record 一并处置。

**机器记录口径提示（给 Coordinator）**：`unresolved_blockers=0` 在本报告中**独占一行且无附着细目**（避免与 FIX-291 的 provably-zero 探针冲突）；P0/P1/P2/P3 计数写在独立行，不与该行混排。

---

## 九、遗留项与建议处置

| 项 | 级别 | 建议处置 | 责任方 |
|---|---|---|---|
| F-1 | P1 | **R5 扩面（接入启动链/棘轮）之前**修复：provenance 由观测事实派生（或拒绝矛盾入参）+ 补 `source=` 单独传入的测试 | Developer（下一轮或紧随补丁轮） |
| F-2 | P2 | 与 F-1 同批：`RegistrationReport` 增补已观测轴字段，`lines()` 显式标注未观测轴 | Developer（同上） |
| F-6 | P2 | 本轮或紧随补丁轮：`check_id_of` 以 `_SEGMENT_RE` 校验并抛 `UnknownCheckID` + 3 个负例测试 | Developer |
| F-3 | P2 | 更正 EVD-996 / commit message 的增量算术（+23 vs 枚举 24），使其自洽并明示被修正项 | Coordinator（治理记录） |
| F-4 | P2 | ① 本包侧把 `test_registry.py:766-771` 的断言改为钉住**可执行**口径；② 更正 `core/architecture-baseline.json` 的 r6 `probe` 串（owner 非本包，需登记给 archguard/baseline 侧，注意该文件正处于 FIX-303 在飞改动） | Developer + Coordinator（跨包登记） |
| F-5、F-7、F-8、F-9、F-10 | P3 | 记跟踪表：F-5 消费 `import_set_sha256` 面；F-7 分组键改完整点分路径；F-8 校验前置；F-9 把 `modes` 口径写入契约/DEC；F-10 记录 `severity_floor` 语义 | Developer / Coordinator |
| F-11 | P3 | 把「引擎零 import registry」断言改为 AST 机判（事实已由我以 AST 复验为真，非事实问题） | Developer |
| 残余未核验面 | — | ① **全量 2580/32F+1E 未复跑**（超出授予边界；旁证 EVD-998 独立同签名，如需机器证据建议 Coordinator 在无并发会话时补跑）；② **复跑在工作树上执行**，故实际加载 FIX-303 版 `contracts.py` 与 FIX-304 版 `quickscan_registry.py`（已论证 `CheckSpec` 契约未变，见头部环境披露）；③ lint NOT_RUN 未独立验证工具安装状态；④ `ADVISORY_SEGMENTS` 的**引擎面完备性**依赖 AST 段落归属启发式（与 FEAT-025 同源口径），未做人工逐段复核 | Coordinator |

---

*审查边界声明：本轮为**只读审查**，按任务书硬门槛与 FEAT-025 R0 先例执行了**只读核验命令**——`git show/--stat/rev-parse/hash-object/diff`、`python -B` 内省（registry 全声明面遍历、六类 fail-closed 直接执行、`check_id_of` 边界输入、`source=` 单独传入探针、AST 全树 import 扫描、静态 `def test_` 逐类清点）、《red 相位机制内存态复现》、`python -B -m unittest`（71 例，两次）、`coverage`（数据文件落仓外 `$env:TEMP` 并已删除）、`-X importtime` 隔离探针、`subprocess` 隔离探针。**未修改任何产品代码、未写入任何仓库文件、未改动 `.governance/`**；全部 python 调用带 `-B`/`PYTHONDONTWRITEBYTECODE=1`，无 `__pycache__` 残留。被审两文件与 `36f2040` blob **逐字节相同**；工作树内 FIX-303/FIX-304 在飞改动的 6 个文件**不属本审查对象且未被改动**，归因一律以 commit 对象（`36f2040:` / `504cc8f:`）为准。核查等级逐条标注于 §七：10 条独立复现、2 条采信（附旁证）、2 条不符（已登记 F-3/F-4）；无法核验项已在 §九「残余未核验面」显式登记，**未写成事实**。*
