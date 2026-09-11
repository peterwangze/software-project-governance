# Code Review: FIX-305-R0 — FEAT-022 R0 遗留批处置（F-1/F-2/F-4/F-6）

- **Task**: FIX-305（R0；承接 `REVIEW-FEAT-022-CODE-R0` 的 P1×1〔F-1〕与 P2×3〔F-2/F-4/F-6〕，commit `c87c47d` 已载明「FIX-305 承接」）
- **Reviewer**: Code Reviewer Agent（只读审查；不修改产品代码、不与用户交互）
- **Round**: **R0**（FIX-305 的首次审查）。**性质声明**：本任务同时是 FEAT-022 前轮 findings 的**修复验证轮**，故按 code-review SKILL「循环角色」段与 code-reviewer 角色定义「复审时 MUST 逐条比对前轮 findings，标注『已修复/未修复/新引入』+ 声明轮次与前轮引用」执行——前轮引用 = `docs/reviews/review-FEAT-022-CODE-R0.md`（本 Reviewer 本人产出，APPROVED_WITH_NOTES / `unresolved_blockers=0`），逐条比对见 §一。
- **审查对象**: **工作树 diff（路径限定）**——`git diff -- skills/software-project-governance/infra/registry.py skills/software-project-governance/infra/tests/test_registry.py`
  - **冻结锚核对（先核对，全部吻合）**：`registry.py` worktree `git hash-object` = `d7800647712a814602fec0f41dec796f4ac68633`（**967 行**）== 任务书锚；`tests/test_registry.py` = `dc96601062df3700ac7d6d4297db04dfd62b2b80`（**1092 行 / 77 tests**）== 任务书锚。
  - **diff 规模实测**：`--numstat` = registry.py **+77/−7**、test_registry.py **+131/−2**（合计 +208/−9；`--stat` 列 = 84 / 133）。**恰 2 个文件**。
  - **diff 基线 = 我 R0 的审查基线（归因干净）**：`git diff 36f2040 d6d12e8 -- <两文件>` **为空**，且 `HEAD`(=`d6d12e8`) 两文件 blob 与我在 R0 审核的 `36f2040` blob **逐字节相同**（`6a6440ca…` / `a7244fac…`）⇒ FIX-304 的 commit 未触碰两文件，本 diff 的全部改动可**无歧义归因于 FIX-305**。
- **设计基准**: `architecture-evolution-0.80.0.md` §9.1（L443-448 受控 loader / 懒加载禁令）、§4.1 R5（L260 注册完整性 + 漂移披露）、§9.5/§4.1 R6（L261/L468-475 启动成本口径）；`infra/contracts.py`（`CheckSpec` 消费面，本轮未改）；前轮报告 §四 F-1/F-2/F-4/F-6 的「事实依据 / 影响 / 修复建议」三项原文（作为验收判据）。
- **审查方法**: 先重读前轮报告四条 finding 全文；逐行读 **diff 全文**（208 增 / 9 删）与两文件改动区域的**最终形态**；再以**内存态回滚修复**逐条复现红相位（不写文件、不改工作树）；并以隔离进程探针实测行为与 import 面。
- **审查边界（诚实声明）**: 全程**只读**——`git show/rev-parse/hash-object/diff/numstat`、`python -B` 内省、`python -B -m unittest`、`coverage`（数据文件落 `$env:TEMP` 并已删）、隔离 `subprocess` 探针、`verify_workflow.py archguard-ratchet`（**实跑一次**，见下）、《内存态回滚红相位复现》（`exec` 旧函数/替换类属性，仅进程内生效）。**未修改任何产品代码、未写入任何仓库文件、未改动 `.governance/`**；全部 python 调用带 `-B`/`PYTHONDONTWRITEBYTECODE=1`。**ratchet 运行后已复核卫生**：`git status` 仍为同一 6 个 `M` 文件、**无新增未跟踪文件**、两被审文件 hash **仍等于冻结锚**（ratchet 未改动任何文件）。
- **环境披露（在飞改动的归因纪律）**: 工作树另有 **FIX-303 在飞改动 4 文件**（`core/architecture-baseline.json`、`archguard_ratchet.py`、`contracts.py`、`tests/test_contracts.py`）。归因纪律：① 本 diff 的两文件与冻结锚逐字节一致；② 其余 4 文件的 diff 经关键字扫描（`registry|check_id_of|observed_axes|unobserved|verify_registration|LIVE_SOURCE`）**仅命中 1 行**，为 `contracts.py` 中 FIX-303 既有的 `CheckSpec` docstring 散文行（我在 R0 已读过该处改动），非 FIX-305 产物；③ FIX-304 的 2 个 quickscan 文件已入 commit `d6d12e8`。
  - **复跑口径的残余限制**：测试/覆盖率/ratchet 均在工作树执行，故实际加载 **FIX-303 版 `contracts.py`**。它对 registry 的消费面（`CheckSpec` 字段集与构造契约）**未变**（R0 已论证，本轮 77/77 与 265/9/97% 亦一致）；但要严格 materialize「纯 FIX-305 + 未改 contracts」的状态需改动工作树，与审查边界冲突，故不做。

---

## 一、前轮 findings 逐条比对（已修复 / 未修复 / 新引入）

### F-1（前轮 P1）R5 报告的 `source` 与实际观测面矛盾，且该路径静默导入引擎 → **已修复且有效**

**修复实现（读码）**：`registry.py:929-953`
- 活引擎分支（:929-938）：:930 先判 `if source is not None and source != LIVE_SOURCE:` → :931-935 `RegistryError`（`contradicts the face actually observed` / `provenance is derived from the observation, never asserted`），**该判断位于 :936-937 `_live_faces()` 之前**；:938 改为无条件 `source = LIVE_SOURCE`（删除了原来的 `source or LIVE_SOURCE`）。
- 注入分支（:939-953）：:940-944 拒绝 `source == LIVE_SOURCE`；:945-948 由**实际传入的**面计算 `observed_axes`；:949-952 未观测轴才回落到声明；:953 `source = source or INJECTED_SOURCE`。
- docstring :912-928 与实现逐项对应（provenance「只能与实际所走分支一致，不能凌驾其上」）。

**红→绿复现（行为级，隔离进程，可重跑）**：把 `HEAD:…/registry.py` 中**旧的** `verify_registration`（35 行，AST 定位 `lineno..end_lineno`）`exec` 进 `registry` 命名空间后调用同一表达式：
| 实现 | `verify_registration(source="frozen-snapshot")`（不传面） | `contract_matrix` 已导入 | `verify_workflow` 已导入 |
|---|---|---|---|
| 旧（HEAD blob） | `{"source": "frozen-snapshot", "ok": true}` | **true** | **true** |
| 新（工作树） | `{"type": "RegistryError"}` | **false** | **false** |

⇒ 修复不仅拒绝了矛盾标签，且**在 provider 加载之前**拒绝 ⇒ 任务书声称的「零引擎导入」**实测为真**。

**测试级牙（逐条回滚实测）**：内存态换回旧 `verify_registration` 后，`test_provenance_cannot_be_asserted_over_an_injected_face` **变红（ran=1 failures=1）**；恢复后复绿。新增 4 条 F-1 测试：
- `test_a_contradicting_label_is_refused_before_the_provider_loads`（隔离探针）——断言 `type=RegistryError` + 消息含 `frozen-snapshot` + **`contract_matrix` 与 `verify_workflow` 均未进入 `sys.modules`** ⇒ 本条的 F-1 红相位就是前轮实测的原始缺陷形态，**牙最锋利**。
- `test_provenance_cannot_be_asserted_over_an_injected_face`（进程内）——注入面 + `LIVE_SOURCE` → `RegistryError`，断言消息含 `contradict`。
- `test_the_frozen_snapshot_path_never_imports_the_engine`（隔离探针）——**精确性注记**：该条在旧实现下其 provider/engine 断言**同样会通过**（旧代码对注入面本就不调用 `_live_faces()`），其真实价值是**回归守卫**（防止未来把注入面绕经活 provider）；真正的 F-1 红相位由上面两条承担。如实标注，不夸大其牙。
- `test_an_explicit_live_label_on_the_live_branch_is_accepted`——**负对照**（docstring 自述 "negative control: the honest label is not refused"），验证加严不误伤诚实调用。

**兼容面**：全仓 grep ⇒ `verify_registration` / `observed_axes` / `unobserved_axes` / 轴 token **仅出现在 `registry.py` 与其测试内**，无其他消费方 ⇒ 加严不破坏任何既有调用者（与前轮「棘轮尚未消费 registry」的披露一致）。

**裁决：已修复，验证通过，P1 关闭。**

### F-2（前轮 P2）单轴注入时未观测轴被当作观测结果、`ok` 可绿而无披露 → **已修复**

**修复实现（读码）**：`registry.py:804-805`（`CLI_KEYS_AXIS`/`SEGMENTS_AXIS` 轴 token，均入 `__all__` :102/:112）、:836（`observed_axes: Tuple[str, ...] = ()`）、:844-852（`unobserved_axes` **计算属性**，docstring 自述「computed rather than stored, so a report built without axis information never claims a measurement it cannot back」——默认空元组即"两轴皆未观测"，**保守方向正确**）、:854-874（`lines()` 逐轴调用）、:876-881（`_unobserved_note`）。`ok` 语义**未改**（:838-842，仅 docstring 增补「read `unobserved_axes` for their coverage」）——与我在前轮的建议及本轮任务书口径一致。

**实测渲染（单轴：只注 cli-keys）**：
```
observed_axes = ('cli-keys',) | unobserved_axes = ('segments',)
R5 registration integrity [injected]: PASS
  cli keys: registry=82 observed=82 missing=[] extra=[]
  segments: registry=70 observed=70 missing=[] extra=[]  [unobserved] segments: face defaulted to the registry's own declaration — a self-comparison, not a measurement
```
双轴注入实测 ⇒ `observed_axes=('cli-keys','segments')`、`unobserved_axes=()`、输出中 **不含** `unobserved`。⇒ 「自我比较 vs 实测」在报告与渲染两面均可区分，前轮 F-2 的假绿面闭合。

**测试级牙**：内存态移除披露（`unobserved_axes` → `()`、`_unobserved_note` → `''`）⇒ `test_a_defaulted_axis_is_disclosed_as_unobserved` **变红（ran=1 failures=1）**；恢复后复绿。该测试同时钉住三态：单轴 cli（segments 未观测）、镜像单轴（cli 未观测）、双轴（无 unobserved 字样）。

**裁决：已修复，验证通过，P2 关闭。**

### F-4（前轮 P2）验收② 的对照口径引用了不能按字面执行的 probe 字符串 → **本包半边已修复；跨包半边未闭合（需 Coordinator 登记）**

**已修部分（本包侧）**：`test_registry.py` 原 `assertEqual(budget["probe"], "python -I -B -c 'import verify_workflow' (isolated)")` 被替换为
`assertIn("import verify_workflow", budget["probe"])` + `assertEqual(_engine_startup_face()["count"], budget["import_count"], …)`
⇒ 判据从「钉住一个跑不起来的字符串」改为**「实测可执行口径并必须落在记录数上」**（docstring 明写 `-I` 蕴含 `-P` 的根因、生产者签名要求注入 infra 目录、以及 baseline 标签 owner 非本包）。

**双向实测**：
| 口径 | 结果 |
|---|---|
| 字面串 `python -I -B -c "import verify_workflow"` | 退出码 **1**，`ModuleNotFoundError: No module named 'verify_workflow'` ⇒ **仍不可执行**（缺陷本体未被隐藏） |
| 可执行口径 `_engine_startup_face()["count"]`（注入 infra 目录） | **196** == baseline `r6_startup_budget.import_count` **196** ⇒ 新断言成立且**实测有值** |

新断言还**强于**原有的同族断言：`test_the_engine_frozen_face_is_not_grown_by_the_registry` 用的是 `<= 196`，而本条为 `== 196` ⇒ 计数**下降**（baseline 陈旧）也会被捕获。

**未闭合部分（跨包）**：`core/architecture-baseline.json` r6 的 `probe` 仍为 `"python -I -B -c 'import verify_workflow' (isolated)"`；实测 FIX-305 对该文件的 diff **不含** `probe` / `import_count` / `r6_startup` 任何行 ⇒ 与本包声明的边界一致（owner 非本包，且该文件正处 FIX-303 在飞改动）。**这一半必须由 Coordinator 显式登记**（见 §八），否则前轮 F-4 会以"已修"结案而记录面缺陷残留。

**裁决：本包侧已修复且验证通过；跨包侧未闭合，转登记项（非本包缺陷）。**

### F-6（前轮 P2）`check_id_of()` 不校验段形式、与 `segment_of()` 口径不对称 → **已修复**

**修复实现（读码）**：`registry.py:587-599`——:595 `if not isinstance(segment, str) or _SEGMENT_RE.match(segment) is None:` → :596-598 `UnknownCheckID`，消息改为点名**期望形式**（`'<digits><optional lowercase letter>', e.g. '28p'`）；复用既有 `_SEGMENT_RE = ^([0-9]+)([a-z]?)$`（:577）。非 str 时 `not isinstance(...)` **先短路**，不会对非 str 调用 `.match`。docstring :590-593 显式引用「fail-closed, never guessed」纪律与 `segment_of` 的对侧口径。

**实测（8 负例全抛 + 70 正对照全解析）**：`None, "", "   ", "28p!", "nosuch", "check-28p", "28pa", 28` ⇒ 全部 `UnknownCheckID` 且消息含 `repr(入参)`；`reg.segment_ids()` 全 70 段 ⇒ 均得 `check-<seg>`（正对照）。
- **精确性注记**：任务书称「7 负例」，代码实为 **8 个**（属加强，非缺口）。

**测试级牙**：内存态换回旧实现 ⇒ `check_id_of('')` = `'check-'`（前轮缺陷原形态）且 `test_check_id_of_refuses_anything_but_a_bare_segment` **变红（ran=1 failures=1）**；恢复后复绿。

**回归面**：全仓 grep ⇒ `check_id_of` 仅 `registry.py:641`（`_build_check_specs` 内部调用，其 70 段全为合法形式）+ `__all__` ⇒ **无外部消费方，加严零回归风险**。

**裁决：已修复，验证通过，P2 关闭。**

### 新引入问题

**无 P1/P2 新问题。** 仅 3 条 P3 观察 + 1 条 P3 讨论项（§五）。

---

## 二、5 个评审维度逐项结论

### 维度 1：正确性 — 通过（含 P3×2）

- **四处修复逻辑正确**：F-1 的分支判断与 provenance 绑定（:929-953）；F-2 的轴归属由**实际传入面**计算（:945-948，`face is not None` ⇒ 空列表/空元组也算"已观测"，语义正确）；F-6 的形态校验（:595）；F-4 的实测判据（测试侧）。逐条与 docstring 声称对照，**无一处不符**。
- **校验先于副作用（fail-closed 次序）**：F-1 的活引擎分支把矛盾标签的拒绝放在 :936-937 `_live_faces()` **之前** ⇒ 隔离实测 `provider=false / engine=false`。这是本轮对前轮 F-8（`assemble` 先导入后校验）同类问题的一个正向修正。
- **边界**：`source=""` 在两分支语义相反（活引擎分支视为矛盾 → raise；注入分支视为未提供 → `INJECTED_SOURCE`）——见 **N-2**。其余边界（`None` / 空面 / 双轴 / 单轴 / `LIVE_SOURCE` 显式传入）均实测正确。
- **并发安全**：无新增可变状态（新增的仅是常量、一个带默认值的 frozen 字段、计算属性与方法）；`RegistrationReport` 仍 `frozen=True` ⇒ 无并发风险。
- **资源管理**：新增代码零 I/O、零文件句柄；新探针沿用既有 `_run_isolated`（`timeout=180` + 显式 UTF-8）。

### 维度 2：安全性 — 通过（无发现）

- **无新增导入**：模块级 import 名单实测仍为 `__future__ / contracts / dataclasses / importlib / quickscan_registry / re / typing` ⇒ §9.1「受控白名单 + 禁止未批准动态加载」未被放松；`import verify_workflow` 仍**不存在**。
- **无动态代码执行**：`eval(`/`exec(`/`compile(` 裸计数为 2，**逐处澄清**为 `re.compile(`（`registry.py:431` `_LOADER_SEGMENT_RE`、`:577` `_SEGMENT_RE`）——正则编译对象，非代码执行；与 AST 机判 `test_registry_mechanism_scan_is_not_used` 通过一致。
- **fail-closed**：新增两条 `RegistryError` 均在非法输入/矛盾标签下拒绝，且消息点名矛盾项，无静默降级、无"猜"。
- **敏感数据/权限**：零密钥、零凭据、零绝对用户路径；纯库模块无权限面。
- **注入面**：F-6 的加严使 `check_id_of` 不再可能"铸造"任意 CheckID；F-1 的加严使 provenance 无法被调用方伪造 ⇒ **两处均为安全性质的正向收紧**（降低"伪证"面）。

### 维度 3：可维护性 — 通过（含 P3×2）

- **diff 外科式**：208 增 / 9 删，全部落在 4 个修复点 + 6 条新测试；无顺手重构、无整文件格式化、无无关改动 ⇒ 符合「不做冗余修改，保持修改纯粹性」。
- **命名与对称性**：`observed_axes` / `unobserved_axes` 语义对称、自解释；轴 token 常量化并可导出；`_unobserved_note` 私有助手单一职责。
- **注释/文档质量**：新 docstring 每条都给出**根因与依据**（F-4 段点明 `-I` 蕴含 `-P`、生产者签名要求注入目录、label owner 归属；F-1 段点明「provenance 不能凌驾观测」）——沿用本模块既有的「口径锚定事实」文化。我逐条核对了新 docstring 的每项声称，**无夸大**（唯一的措辞强度问题见下"牙"的精确注记）。
- **可维护性风险**：轴词汇表在 **3 处**枚举，存在"新增轴漏登记 → 静默回到自我比较"的潜在缺口（**N-1**）；新失败模式复用基类 `RegistryError` 而非新增叶类，与既有四叶族模式略不一致（**N-4**，讨论级）。
- **未引入新耦合**：仍未 import 引擎；仍未写文件；仍未消费第三方。

### 维度 4：性能 — 通过（无发现）

- **修复方向对性能是净收益**：F-1 把一条"会拉入巨石却谎报来源"的路径改为**先抛错**（实测 `engine=false`）；F-2 的轴计算为 O(2)；F-6 的校验为单次锚定正则匹配。
- **ratchet R6 独立确认**：`cold import 196 modules (baseline 196, Δ0)` ⇒ 本轮改动未增长启动面（与我的隔离实测一致）。
- **局部成本**：新探针 `test_the_frozen_snapshot_path_never_imports_the_engine` 把 82 键 + 70 段面 repr 内嵌进 `-c` 载荷（≈4~5 KB），远低于 Windows `CreateProcess` 命令行上限；该测试实跑通过（77/77）。测试耗时由 17.7s → 28.7~30.6s（+6 例含两条额外隔离子进程探针），属可接受量级。
- **无循环内 I/O、无 O(n²)、无新增批处理**。

### 维度 5：测试覆盖 — 通过（无发现）

- **清点与复跑**：静态 `def test_` 逐类清点 = ContractShape 6 + CommandRegistry 7 + **CheckRegistry 14**(+1) + DelegatedLoader 2 + LoaderWhitelist 14 + CompositionRoot 5 + **RegistrationIntegrity 13**(+5) + StartupImport 9 + DeclarationFace 4 + ImportTimeGuard 3 = **77**，与声称一致；**独立复跑 2 次均 `Ran 77 tests … OK`**（30.6s / 28.7s），与「三次一致」不矛盾。
- **覆盖率独立复跑逐数字吻合**：**265 stmts / 9 miss = 97%**，`Missing = 493-494, 537, 625, 636, 661, 892-893, 931`。与 R0（248/8/97%、`491-492, 535, 616, 627, 652, 848-849`）逐行对账：+2（`__all__` 两处）/+9（F-6 段）/+44（F-2+F-1 段）位移后**完全一一对应**；**唯一新增 miss = L931** —— 实测该行即 F-1 的活引擎分支 `raise RegistryError(`，由隔离探针 `test_a_contradicting_label_is_refused_before_the_provider_loads` 覆盖 ⇒ 归属「隔离探针面」，与声称一致。**注**：注入分支的 `raise`（L941-944）**未**出现在 miss 表 ⇒ 已由进程内测试覆盖 ✔。
- **牙（逐条回滚实测）**：6 条新测试中 **4 条**在回滚对应修复后变红（F-6 1 条、F-2 1 条、F-1 进程内 1 条、F-1 隔离探针 1 条按行为级红相位验证），另 **2 条**为刻意的负对照/属性回归守卫（`test_an_explicit_live_label_on_the_live_branch_is_accepted` 自述 negative control；`test_the_frozen_snapshot_path_never_imports_the_engine` 的 provider/engine 断言为回归守卫）——**如实区分，未把守卫当红相位**。
- **覆盖缺口**：前轮 F-1/F-2/F-6 的覆盖缺口**已全部补齐**；F-4 的跨包半边不在测试面（记录面）。

---

## 三、AI 代码专项 5 项检查

| # | 检查项 | 结论 | 事实依据（可复查） |
|---|---|---|---|
| ① | mock 残留 | **无** | diff 新增行扫描 `unittest.mock` / `MagicMock` / `patch(` **零命中**；新测试用**真实**隔离进程（`_probe`：`python -I -B` 真解释器）与**真实**快照面（`_frozen_faces()` 读 `contract_matrix/snapshots.json`），未新增任何替身/桩 |
| ② | 硬编码返回值 | **无掩盖（且判据被强化）** | F-1 探针内嵌的 82 键/70 段取自真读的快照面，非硬编码；唯一的字面量断言是 `assertEqual(probe["source"], "frozen-snapshot")`（标签断言，恰当）；**F-4 把原「断言一个字符串」的弱判据换成 `_engine_startup_face()["count"] == baseline["import_count"]` 实测** ⇒ 硬编码面净减少 |
| ③ | 幻觉 API 调用 | **无** | 新引用的 `reg.CLI_KEYS_AXIS` / `SEGMENTS_AXIS` / `report.observed_axes` / `report.unobserved_axes` / `reg.LIVE_SOURCE` / `_engine_startup_face` / `_SEGMENT_RE` 全部存在且被实跑通过；全仓 grep 证实这些符号**仅**在 registry 与其测试内定义/使用，无悬空引用 |
| ④ | 未实现 TODO | **无** | diff 新增行零 `TODO` / `FIXME` / `NotImplemented` / `skip` / `xfail` / `pytest.mark` 命中；4 条修复全部落地到可执行代码，无占位 |
| ⑤ | 过度实现 | **无** | diff 恰对应 F-1/F-2/F-4/F-6 四项；`observed_axes` + `unobserved_axes` + `_unobserved_note` 正是前轮 F-2 的建议形态（字段名与"lines() 打印 unobserved"逐字对应）；`ok` 语义按要求**未改**；无新增功能、无顺手重构、无文档以外的范围外产物 |

---

## 四、验收标准与门禁声称逐条裁决

### 4.1 任务书验收四条

| # | 验收标准 | 裁决 | 事实依据 |
|---|---|---|---|
| 1 | **每条修复有效（红→绿可复现）** | **PASS** | F-1：隔离进程实测旧实现 `source='frozen-snapshot' + provider/engine=true` → 新实现 `RegistryError + provider/engine=false`；测试级回滚旧 `verify_registration` ⇒ 变红。F-2：回滚披露 ⇒ 变红。F-6：回滚校验 ⇒ `check_id_of('')='check-'` 且变红。三者恢复后均复绿。F-4：字面串实测 `ModuleNotFoundError`（不可执行）vs 可执行口径实测 **196 == baseline 196** 双向实证 |
| 2 | **无新范围（diff 恰两文件）** | **PASS** | `--numstat` 恰 registry.py +77/−7、test_registry.py +131/−2；FIX-304 的 2 个 quickscan 文件已入 commit `d6d12e8`；其余 4 个 `M` 属 FIX-303（关键字扫描仅命中其既有 `contracts.py` docstring 散文行） |
| 3 | **测试有牙** | **PASS** | 4/6 新测试在回滚修复后逐条实测变红（各 1 failure），另 2 条为刻意的负对照/回归守卫（已在 §一 F-1 处如实标注牙的归属，未夸大） |
| 4 | **AI 专项 5 项** | **PASS** | 见 §三，逐项有结论且每条附可复查事实 |

### 4.2 门禁声称交叉核对

| # | 门禁声称 | 核查等级 | 我的实测 / 论证 |
|---|---|---|---|
| 1 | 77/77 三次一致 | ✅ **独立复现** | 复跑 **2 次**均 `Ran 77 tests … OK`（30.648s / 28.679s）；静态清点 = 77（CheckRegistry 14 / RegistrationIntegrity 13，其余不变）；与声称的三次一致**无矛盾** |
| 2 | 覆盖率 265 stmts 9 miss = 97%（931 新增活引擎分支 = 隔离探针面） | ✅ **独立复现** | `coverage` 复跑逐数字吻合：**265 / 9 / 97%**，`Missing=493-494, 537, 625, 636, 661, 892-893, 931`；**实测 L931 = F-1 活引擎分支 `raise RegistryError(`**，与 R0 的 8 行 miss 位移后一一对应 ⇒ 唯一新增 miss 归属"隔离探针面"**如实准确** |
| 3 | 全量 2590~2592 失败族全在两文件外（+1error 归因 = FIX-300 存量孤立复现实证） | ⚠️ **采信（附独立论证）** | **未复跑全量**（超出本次授予边界「验收：修复有效/无新范围/测试有牙/AI 5 项 + 门禁声称」）。独立论证其不可能性：FIX-305 仅改两文件、且全仓 grep 证实 registry 无任何产品消费方 ⇒ 对两文件外的测试行为无影响面。**+1error 的 FIX-300 归因我无法核验**，如实标注为采信而非已验 |
| 4 | ratchet PASS | ✅ **独立复现（附归因限定）** | 实跑 `python verify_workflow.py archguard-ratchet` = **`Result: PASS (0 violations; raw findings before exemptions: 0) — fatal gate green`，EXIT=0**；逐规则：R1 `24329 ≤ 24329` / R2 `46 ≤ 46`（36 文件）/ R3 `matrix 12 edges; managed 2 modules, 0 edges, SCC max 1` / R4 `1310 ≤ 1310` / R5 `cli keys 82/82 frozen, segments 70/70 frozen` / R6 `cold import 196 (baseline 196, Δ0)` / R7 `regen deterministic=True; committed==fresh True`。**归因限定**：ratchet 脚本与 baseline 处于 FIX-303 在飞改动中，故该 PASS 证明的是「**FIX-305 未引入新违规**」，非纯 FIX-305 产物；运行**未改动任何文件**（两文件 hash 仍等于冻结锚、无新增未跟踪文件、`M` 集合不变） |

### 4.3 任务书数字对账（记录面观察，非 finding）

| 任务书表述 | 实测 | 定性 |
|---|---|---|
| 「预期 +84/−9 与 +133/−8」 | registry.py **+77/−7**、test_registry.py **+131/−2**（`--stat` 列 = 84 / 133） | 范围声明正确；数字表述混用了 `--stat` 列与逐文件删除数（实际删除 7 与 2，合计 9） |
| F-6「7 负例」 | 实测 **8** 个负例 | 代码强于声明，非缺口 |

---

## 五、新发现清单

> 级别口径：P0 阻塞／P1 关键／P2 建议／P3 讨论。**本轮无 P0/P1/P2 级新发现。**

### N-1（P3）轴词汇表在 3 处枚举，存在"新增轴漏登记 → 静默回到自我比较"的潜在缺口

- **位置**：`registry.py:851`（`unobserved_axes` 内硬枚举 `(CLI_KEYS_AXIS, SEGMENTS_AXIS)`）、`:945-948`（`verify_registration` 内独立枚举同一对）、`:862`/`:867`（`lines()` 逐轴调用 `_unobserved_note`）。
- **事实依据**：「`cli-keys` / `segments`」两 token 在上述 3 处各自硬枚举；模块 docstring 文化主张「单一事实源」。
- **影响**：若后续新增第三个观测轴（如 provider 轴 / 快照轴），只登记 `:945-948` 而漏改 `:851`，则该轴即使**未被观测**也不会被 `unobserved_axes` 点名 ⇒ 报告静默回到 F-2 的原形态（自我比较被当作实测）。属**潜在**缺口，当前无第三轴故未发生。
- **修复建议**：抽出单一模块级 `_AXES: Tuple[str, ...]`（或由 `RegistrationReport` 字段驱动）作为唯一事实源，`unobserved_axes` / `verify_registration` / `lines()` 均从中派生。

### N-2（P3）`source` 为空串时两分支语义相反

- **位置**：`registry.py:930`（`if source is not None and source != LIVE_SOURCE:`）对照 `:953`（`source = source or INJECTED_SOURCE`）。
- **事实依据（实测）**：`verify_registration(source="")`（无注入面）→ **`RegistryError`**；`verify_registration(observed_cli_keys=…, source="")` → **`source='injected'`**。同一输入在一处被当作"矛盾标签"、在另一处被当作"未提供"。
- **影响**：极低——`""` 是退化输入，且活引擎分支方向为**更严**（fail-closed），不产生伪证面；仅口径不匀。
- **修复建议**：活引擎分支改为 `if source not in (None, LIVE_SOURCE):`，与注入分支的"空即未提供"语义对齐（一处改动）。

### N-3（P3）`[unobserved]` 注记与轴行**同行**拼接，非独立行

- **位置**：`registry.py:861-862`、`:866-867`（将 `_unobserved_note(...)` 直接续接在轴行末尾）；`:880`（注记字符串以两个空格开头，形如行首前缀）。
- **事实依据（实测渲染）**：`  segments: registry=70 observed=70 missing=[] extra=[]  [unobserved] segments: face defaulted to the registry's own declaration — a self-comparison, not a measurement`——**是一条很长的单行**。披露内容完整、自识别（注记点名 `segments`）且可 grep，前轮 F-2 的披露要求已满足。
- **影响**：纯排版。注记自带两空格前缀暗示作者原意为换行，读者可能误读为该 `segments:` 项目的一部分（不致误解归属，因注记自报轴名）。
- **修复建议**：注记改为以 `"\n  "` 开头，或 `lines()` 对未观测轴另 `append` 一行。

### N-4（P3，讨论项）新的矛盾失败模式复用基类 `RegistryError` 而非新增叶类

- **位置**：`registry.py:931`、`:941`（两处 `raise RegistryError(...)`）。
- **事实依据**：模块既有错误族为「一条链式基类 + 四个叶类」（`UnknownCommandKey` / `UnknownCheckID` / `LoaderWhitelistViolation` / `LoaderResolutionError`，:206-223），provenance 矛盾作为一个**新的失败模式**沿用基类，与"一模式一叶"的既有模式略不一致。
- **影响**：无——基类可被 `except RegistryError` 捕获，测试亦以 `reg.RegistryError` 断言通过；仅分类学一致性。
- **建议**：登记为讨论项（若要收敛，可增 `ProvenanceContradiction(RegistryError)` 叶类）；**不要求本轮修改**。

---

## 六、硬门槛裁决

| 门槛 | 结果 |
|------|------|
| P0 阻塞问题数 = 0 | ✅ **0**（4 条新发现全部为 P3） |
| 5 维度全覆盖 = 100% | ✅ 正确性 / 安全性 / 可维护性 / 性能 / 测试覆盖逐项有结论（§二） |
| 每条发现标注级别 = 100% | ✅ N-1~N-4 全部标注 P3 + file:line + 事实依据 + 建议 |
| 设计一致性检查已完成 | ✅ 对照 §9.1（受控加载/懒加载禁令）、§4.1 R5（注册完整性 + 漂移披露）、§9.5/§4.1 R6（启动成本口径），并逐项比对前轮报告 §四 各条的「修复建议」原文（§一） |
| AI 代码专项 5 项检查全部完成 | ✅ 逐项有结论（§三） |
| 逐行读 diff 全文 + 改动区域最终形态 | ✅ 208 增 / 9 删逐行；两文件改动区域（`registry.py:587-599`、`:804-807`、`:815-881`、`:907-967`；`test_registry.py` 新增 6 测试）读最终形态 |
| **前轮 findings 逐条比对（复审义务）** | ✅ F-1/F-2/F-6 = 已修复且验证通过；F-4 = 本包侧已修 + 跨包侧未闭合（转登记）；新引入 = 无 P1/P2（§一） |
| 修复有效性红→绿可复现（任务书验收 1） | ✅ 三条以内存态回滚复现红并复绿；F-1 另以隔离进程复现旧实现真实红态（provider/engine=true） |
| 无新范围 / 测试有牙 / AI 5 项（任务书验收 2-4） | ✅ 逐项 PASS（§四 4.1） |

---

## 七、审查结论

# APPROVED_WITH_NOTES

unresolved_blockers=0

**终态理由**：我前轮的 P1×1（F-1）与 P2×2（F-2、F-6）**三条全部修复到位并经红→绿实测验证**——F-1 的 provenance 已由实际分支派生（活引擎分支拒绝矛盾标签且**先于** `_live_faces()`，隔离实测 `provider=false / engine=false`；旧实现同一调用实测 `source='frozen-snapshot' + engine=true`），F-2 的轴覆盖披露字段与 `lines()` 渲染经三态实测可区分"自我比较"与"实测"（`ok` 语义按要求未改），F-6 的形态校验使 fail-closed 口径与 `segment_of` 对称（8 负例全抛 + 70 段正对照全解析、无外部消费方故零回归）。四条修复的探针/断言均**有牙**（4/6 新测试回滚即红，另 2 条为明示的负对照/回归守卫）。范围纪律成立（**恰两文件** +208/−9，diff 基线与我的 R0 基线逐字节同一）；门禁声称中 77/77、覆盖率 265/9/97%、ratchet PASS 三项**独立复现**（ratchet 另经 `git status` + 冻结锚复核确认未改动任何文件）。硬门槛全部通过、**P0 = 0**、无新 P1/P2 ⇒ 无未解决 BLOCKING finding，满足 code-review SKILL「循环角色」段的通过终态契约。**使用 `WITH_NOTES` 而非 `APPROVED` 的理由**：存在 4 条 P3 观察（N-1 轴词汇表三处枚举的潜在静默缺口 / N-2 `source=""` 分支不对称 / N-3 注记同行排版 / N-4 错误分类学），以及一条**未闭合的跨包登记项**（F-4 的 baseline r6 `probe` 标签更正——本包无权修改、owner 在 FIX-303 在飞面），二者均属"留有备注"，不宜以零备注的 APPROVED 结案。

**发现计数（独立行，供机器记录）**：P0 = 0；P1 = 0；P2 = 0；P3 = 4。

**前轮四条处置裁决（供 Coordinator 机器记录）**：

| 前轮 finding | 前轮级别 | 本轮裁决 | 验证事实 |
|---|---|---|---|
| F-1（provenance 被调用方凌驾 + 静默导入引擎） | P1 | **已修复 / 关闭** | 旧实现隔离实测 `{'source':'frozen-snapshot','ok':true,'provider':true,'engine':true}` → 新实现 `RegistryError` + `provider=false/engine=false`；回滚旧 `verify_registration` ⇒ 对应测试变红 |
| F-2（未观测轴被当作实测、无披露） | P2 | **已修复 / 关闭** | `observed_axes`/`unobserved_axes` 三态实测正确；单轴渲染含 `[unobserved] segments: … a self-comparison, not a measurement`，双轴不含 `unobserved`；回滚披露 ⇒ 测试变红 |
| F-4（验收②口径串不可执行） | P2 | **部分修复：本包侧已闭 / 跨包侧未闭（转登记）** | 本包：断言改为实测口径，`_engine_startup_face()["count"]` = **196** == baseline **196**（原为钉一个实测会 `ModuleNotFoundError` 的串）；跨包：baseline r6 `probe` 标签**仍未更正**（FIX-305 对其 diff 零命中），**MUST 由 Coordinator 登记** |
| F-6（`check_id_of` fail-open 不对称） | P2 | **已修复 / 关闭** | `_SEGMENT_RE` 校验落地；8 负例全抛 + 70 正对照全解析；回滚 ⇒ `check_id_of('')='check-'` 且测试变红；全仓无外部消费方 |

**P3 处置要求**：N-1 建议随下一次触碰该模块的切片收敛（唯一事实源化）；N-2 为一行改动，可随任意补丁轮；N-3 排版项；N-4 仅登记讨论。四条**均不阻塞合并**。

**机器记录口径提示（给 Coordinator）**：`unresolved_blockers=0` 在本报告中**独占一行且无附着细目**（避免与 FIX-291 的 provably-zero 探针冲突）；P0/P1/P2/P3 计数写在独立行，不与该行混排；前轮处置裁决另表列出（本轮为 FIX-305 R0，性质上兼作 `REVIEW-FEAT-022-CODE-R0` 的修复验证）。

---

## 八、遗留项与建议处置

| 项 | 级别 | 建议处置 | 责任方 |
|---|---|---|---|
| **F-4 跨包半边** | **登记项（P2 级遗留）** | 更正 `core/architecture-baseline.json` r6 的 `probe` 串为可执行形态（含 infra 目录注入说明或等价可复现命令）。**本包侧已改断言，但记录面缺陷仍在**；该文件 owner 非本包且正处 FIX-303 在飞改动 ⇒ 需 Coordinator 显式登记到 baseline/archguard 侧跟踪表并给关闭截止日期 | Coordinator（跨包登记）→ baseline/archguard 侧执行 |
| N-1 | P3 | 轴词汇表唯一事实源化（`_AXES` 或由报告字段驱动），消除"新增轴漏登记即静默"的潜在缺口 | Developer（下一次触碰该模块时） |
| N-2 | P3 | 活引擎分支改 `if source not in (None, LIVE_SOURCE):`，与注入分支语义对齐（一行） | Developer（可随任意补丁轮） |
| N-3 | P3 | `_unobserved_note` 以 `"\n  "` 开头（或 `lines()` 另 append 一行），使披露独立成行 | Developer |
| N-4 | P3（讨论） | 是否新增 `ProvenanceContradiction(RegistryError)` 叶类以维持"一模式一叶"分类学——**不要求修改** | Coordinator 裁决 |
| 残余未核验面 | — | ① **全量 2590~2592 失败族未复跑**（超出授予边界；已给"registry 无消费方 ⇒ 无影响面"的独立论证）；② 复跑在工作树执行，实际加载 FIX-303 版 `contracts.py`（`CheckSpec` 消费面未变，见头部披露）；③ **+1error = FIX-300 存量孤立复现** 的归因**未核验**，标注为采信；④ `archguard-ratchet` PASS 的归因**受 FIX-303 在飞改动限定**（证明"未引入新违规"，非纯 FIX-305 产物）；⑤ 任务书 diff 数字表述（+84/−9 与 +133/−8）与实际（+77/−7 与 +131/−2）混用了 `--stat` 列，已对账澄清 | Coordinator |

---

*审查边界声明：本轮为**只读审查**——执行了 `git show/rev-parse/hash-object/diff/numstat`、`python -B` 内省与静态 AST 清点、`python -B -m unittest`（77 例，2 次）、`coverage`（数据文件落仓外 `$env:TEMP` 并已删除）、隔离 `subprocess` 探针（F-1 旧/新实现对照、F-4 口径双向）、`verify_workflow.py archguard-ratchet`（一次，运行后经 `git status` 与冻结锚复核确认**未改动任何文件**）、《内存态回滚红相位复现》（仅进程内 `exec`/属性替换）。**未修改任何产品代码、未写入任何仓库文件、未改动 `.governance/`**；全部 python 调用带 `-B`/`PYTHONDONTWRITEBYTECODE=1`。两被审文件 worktree hash **等于**冻结锚（`d7800647…` / `dc966010…`），diff 基线与前轮 R0 基线逐字节同一。核查等级逐条标注于 §四：门禁声称 4 条中 **3 条独立复现、1 条采信（附独立论证）**；前轮四条处置中 **3 条已修复关闭、1 条部分修复转登记**；无法核验项已在 §八「残余未核验面」显式登记，**未写成事实**。*
