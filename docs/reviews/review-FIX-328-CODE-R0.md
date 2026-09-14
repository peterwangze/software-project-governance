# Code Review — FIX-328-CODE-R0：活体金丝雀测试收口（未暂存 diff，commit 前置审查）

| 项 | 值 |
|---|---|
| Task ID | FIX-328 |
| 审查 round | **R0**（首轮；无前轮引用） |
| 审查对象 | 工作树**未暂存**改动（`git diff`，非 `--cached`）——`.git/hooks` 要求 FIX- 前缀产品代码 commit 前置审查，无 commit hash |
| 变更面 | **恰 1 文件 +21/−1**：`skills/software-project-governance/infra/tests/test_triage_write_guard.py`（`git diff --stat` 实证 `1 file changed, 21 insertions(+), 1 deletion(-)`；`git diff --cached` 为空 ⇒ 未暂存，与任务描述一致） |
| Reviewer | Code Reviewer sub-agent（角色定义 `agents/code-reviewer.md` + `skills/code-review/SKILL.md` 全文加载执行） |
| 日期 | 2026-09-12 |
| 审查约束 | 只读审查：Read / Grep / Glob + 只读命令（git diff/status/show、unittest 复跑、guard CLI、`python -c` 只读判定）；**未执行任何写操作与 `git add/commit/restore/reset/checkout/stash`**；未触碰 `$env:USERPROFILE\.dsh` 或仓库外路径；唯一产物 = 本报告 |

---

## 一、终态结论（硬门槛裁决）

**APPROVED_WITH_NOTES —— `unresolved_blockers=0`**

- **P0 = 0**（无阻塞项）；**P1 = 0**；**P2 × 3**；**P3 × 2**（全部非阻塞，见发现表）。
- 硬门槛逐条裁决：

| 门槛项 | 阈值 | 裁决 | 依据 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | ✅ 通过（0） | 无 P0；核心防护（subset 断言）经逐字核实未被弱化（§二.2） |
| 5 维度全覆盖 | = 100% | ✅ 通过 | §三 正确性/安全性/可维护性/性能/测试覆盖 逐项有结论 |
| 每条发现标注级别 | = 100% | ✅ 通过 | F-1~F-5 全部带 P0~P3 标签 |
| 设计一致性检查 | 已完成 | ✅ 通过 | §五：与 FEAT-011 契约、FIX-293 数据面语义、`test-baseline-0.80.0.md` §4-F2 授权依据逐项比对 |
| AI 代码专项 5 项 | 全部完成 | ✅ 通过 | §四：mock 残留/硬编码/幻觉 API/未实现 TODO/过度实现 五项逐一有结论 |

- 按 `skills/code-review/SKILL.md` 循环角色契约：本结论为**通过终态**，无未解决 BLOCKING finding，独立结构字段 **`unresolved_blockers=0`**。

> **给 Coordinator 的定级透明声明**：F-1（P2）是本次改动引入的**真实测试灵敏度回退**（非风格问题），但触发条件窄（plan-tracker 不可读）、影响限于测试面（产品守卫 CLI 同场景仍 exit 1 独立报错）、单行可修。我按 P2 定级并建议**同一会话内修复**（§六）；若 Coordinator 与本仓"fail-closed 链路完整性必须零缺失"口径从严，可将其升为 P1——**我不以 P2 掩饰该回退**，事实与影响见 F-1 全文。

---

## 二、独立复现声明（我亲自读盘 / 复算的内容）

以下每项均由我本人执行，未采信 Developer 或 Coordinator 的自述：

**读盘核实**
1. **diff 全文**：`git diff -- skills/.../test_triage_write_guard.py` 逐行读毕 —— 确为 `+21/−1`；**唯一被删改的原文**是 docstring 内 `FIX-293 将修数据` → `FIX-293 已修数据`（−1/+1，同句替换）；其余 20 行全为新增（docstring 补充 + 注释 + `if not flagged:` skip 分支）。
2. **改动前后原文对照**：`git show HEAD:...` 取出 HEAD 版 L525-534 —— 确认改前为 `subset 断言` 紧随 `assertTrue(flagged, "live M1 four rows must be flagged …")` 双断言、无任何条件分支；与 Developer 自述一致。
3. **落地代码行号逐字核实**（`Select-String` 实测）：L541 首 skip / **L545 `self.assertTrue(flagged.issubset(_KNOWN_M1_IDS), flagged)`** / L547 新 skip / L553 原「必须命中」断言。文件共 768 行。
4. **`_KNOWN_M1_IDS` 定义**（L428）= `{"FIX-222", "FIX-223", "FIX-224", "FIX-279"}` —— 与 subset 断言配套，一致。
5. **守卫 issue 结构**：`verify_workflow.py` `_plan_tracker_task_row_issues()`（L22230-22296）**每条 issue 必带 `task_id`**（两个 append 分支均含 `"task_id": task_id`，L22279 / L22290）⇒ `{i["task_id"] for i in issues}` 对 M1 签名类 issue 无 KeyError、不产生空串（除下述 unreadable 路径）。
6. **skip 理由三事实逐项复核**：
   - `.governance/archive/index.md` L391/392/393：`FIX-222 | 完成 (2026-07-26) | 0.71.0 | archive/tasks/v0.1.0~v0.78.0.md`（223/224 同型）✅
   - **强证据**：`.governance/archive/tasks/v0.1.0~v0.78.0.md` L131/132/133 —— 三行**字面行**确在归档文件内（`| **P0** | FIX-222 | bootstrap prose 消除 …`，223/224 同型），**非仅索引声称** ✅（超出 Developer 自述的核对深度）
   - `.governance/plan-tracker.md`：**搜 `FIX-222|FIX-223|FIX-224` 零命中**（仅 L165/204 作依赖/描述引用）⇒ "归档迁出"属实；且 FIX-293 完成记录（L204）自述修 L188/189/190，而**现 L188/189/190 实为 FIX-272/AUDIT-146/FIX-273** ⇒ 行号移位归档已被自身记录交叉印证 ✅
   - `EVD-963`（`.governance/evidence-log.md` L1755）原文存在：`守卫改前 FAIL 7（恰 M1 四行）→ 改后 PASS 0`，产物面 `.governance/plan-tracker.md（L188/189/190/251/257）`；plan-tracker L204 FIX-293 完成行同载 `FAIL 7 → PASS/exit 0` ✅
   - `FIX-279 行形归一`：FIX-279 行现存于 plan-tracker L195（未被归档，与 skip 理由只声称"行形归一"而非"归档"一致），守卫实测 0 命中 ⇒ 尾空单元格确已消除 ✅
7. **授权依据**：`docs/requirements/test-baseline-0.80.0.md` §4-F2（L107-112）逐字核实 —— 该文档自身即为**根因发现记录**：`AssertionError: set() is not true : live M1 four rows must be flagged`，定性「已知缺陷（测试面）——非产品回归。自 FIX-293 落地起必然变红」，并注明"修复属后续任务"。FIX-328 属其**承接任务**（见 F-4）。

**复算 / 复跑实测**
8. `python -m unittest skills.software-project-governance.infra.tests.test_triage_write_guard -v` → **`Ran 32 tests in 0.168s` / `OK (skipped=1)` / exit 0**，skip 项恰为本用例，无失败。
9. 单跑本用例 → skip 理由字符串完整回显（与 L548-551 源码逐字一致）。
10. `python skills/software-project-governance/infra/verify_workflow.py governance-write-guard` → **`Result: PASS — 0 issue(s)` / exit 0**，四面绿；plan-tracker 面 `0 issue(s)` ⇒ **live 零命中是"数据已治愈"的真实零，而非守卫失灵**（守卫 CLI 同一数据同为零命中，双向一致）。
11. `SAMPLE_PATH` 绑定核实（`python -c` 实测）：`HOST = D:\AI\agent\claude\coding\project_management_workflow`，`SAMPLE_PATH = …\.governance\plan-tracker.md`，`is_file=True` ⇒ 金丝雀确读**真实活体文件**（非 mock、非空转）。
12. 独立复算：`flagged = set()`，`set() == flagged → True`，`plan_tracker.status = PASS`（即 (b) 方案实测可用，见 F-2）。

---

## 三、5 维度逐项结论

### 维度 1：正确性 —— ✅ 通过（含 F-1 回退项）

| 检查项 | 结论 |
|---|---|
| 逻辑正确 | ✅ 改动达成声明意图：命中集合为空 → skip；非空 → 仍强制断言。三段结构（subset → empty-skip → must-flag）语义自洽 |
| **异常路径下 subset 是否可能被跳过** | ✅ **不会**。L545 位于 L540 `is_file()` 门控之后、L546 `if not flagged:` 之前；`assertTrue` 抛 `AssertionError` 中止用例，**不存在被后续分支或 except 吞掉的路径**；全方法无 `try/except`、无第二处 skip、无 `return` 早退。顺序与 Developer 声称的"无条件先执行"逐字一致 |
| 边界条件 | ⚠️ 发现 F-1（见下）：`flagged` 非空但**全部携带空 task_id** 的路径（`plan_tracker_unreadable`）会静默转 skip |
| 并发安全 | ✅ 不适用且无风险：只读调用 `check_governance_write_shapes()`，纯函数面无共享可变状态 |
| 资源管理 | ✅ 无新增资源；`tempfile.TemporaryDirectory`（`_issues()` L489）由既有 `with` 上下文管理，本次未触碰 |

**F-1（P2，本次改动引入）— `plan_tracker_unreadable` 的 fail-closed 信号被 skip 静默吞掉**

- **位置**：`test_triage_write_guard.py:546-552`（skip 分支） + `verify_workflow.py:22415-22426`（`except (IOError, OSError)` 分支）
- **事实依据**（三条均为我亲自核实）：
  1. `verify_workflow.py:22418-22424`——plan-tracker 不可读时守卫返回 `status: "FAIL"`，但 issue 的 **`task_id: ""`**；
  2. 本用例 L543 只提取 `{i["task_id"] …}` ⇒ 该 FAIL 下 `flagged == set()`；
  3. L545 `set().issubset(_KNOWN_M1_IDS)` → **True（空集是任意集子集）** → 落入 L546 `if not flagged:` → **skip**。
- **反证**：改前（`git show HEAD:...` 已核实）无 skip 分支，同场景在第 2 条断言 `assertTrue(flagged, "live M1 four rows must be flagged")` 处 **FAIL** ⇒ 这是本改动**真实引入的测试灵敏度回退**，不是既有行为。
- **影响**：`status="FAIL"`（守卫唯一 fail-closed 分支）在本测试内从"红"变"静默跳过"；测试从此**不能**发现"活体 plan-tracker 不可读"。护栏：产品守卫 CLI 同场景仍 **exit 1** 独立暴露，故影响限于测试面，非产品缺陷；触发条件窄（不可读需越权/编码/损坏）。
- **与"核心防护不弱化"声称的关系**（经字面复核，避免过度指控）：Developer 原话限定为"『活体真实 plan-tracker 不得出现已知四行之外的新误报』（**subset 断言**）无条件生效"——该**字面声称属实**（subset 确无条件先执行）。**但** skip 理由尾部"『不得出现新误报』子集断言仍已生效"（L550-551）同样字面成立、却不足以覆盖 status 面——测试对"守卫 fail-closed"的整体防护确有弱化。
- **修复建议（单行，推荐本会话采纳）**：在 L545 之后、L546 之前插入
  `self.assertEqual(result["plan_tracker"]["status"], "PASS", result["plan_tracker"])`
  依据：`verify_workflow.py:22429-22432` 使 `status ∈ {FAIL if issues else PASS}` ⇒ **无 issue 时 status 必为 PASS**；故该断言在"数据健康"与"下一枚 M1 行出现"两种场景下均不误红（已据 L11 实测 `status=PASS` 复算），却能拦下 unreadable FAIL。

### 维度 2：安全性 —— ✅ 通过（零新增风险面）

| 检查项 | 结论 |
|---|---|
| 输入校验 | ✅ 不引入外部输入面；唯一输入为真实 `plan-tracker.md`，经 `read_text(encoding="utf-8")` 显式编码（FIX-278 G4/F 纪律，无 GBK mojibake 风险） |
| 注入防护 | ✅ 新增代码仅为集合判空 + 字符串常量 skip 理由，无 `eval/exec/subprocess/shell`、无路径拼接、无 SQL/命令面 |
| 敏感数据 | ✅ 无密钥/token/凭据；skip 理由与 docstring 仅含仓库内治理 ID，零环境泄漏 |
| 权限检查 | ✅ 只读测试；`tempfile` 临时目录（既有 `_issues()`）不越界；**未触碰 `$HOME/.dsh` 或仓库外路径**（本报告自身受同一约束） |

### 维度 3：可维护性 —— ✅ 通过（含 P3 命名项）

| 检查项 | 结论 |
|---|---|
| 命名可读 | ⚠️ F-5（P3）：`test_live_plan_tracker_flags_only_known_m1_rows` 在 skip 时名实部分不符（§五.3 明确裁决） |
| 函数长度 | ✅ 用例 30 行（L525-554），远低于 50 行建议阈值；无新增函数 |
| 重复代码 | ❌ 发现 F-3（P3）：L553「必须命中」断言在 L546 skip 后**成为死代码**（可达性上恒真），属残留冗余 |
| 注释质量 | ✅ 注释与代码逐字一致（L544 注释"先于 skip 判定"与 L545 实际位置精确吻合）；skip 理由为可复核事实陈述，非泛化借口；docstring 更新为"FIX-293 已修数据"与实测一致 |

### 维度 4：性能 —— ✅ 通过

| 检查项 | 结论 |
|---|---|
| 避免不必要循环 | ✅ 无新增循环；守卫侧 `_plan_tracker_task_row_issues` 本就为单遍 `O(n)` 逐行扫描，未因本次改动变化 |
| 数据结构选择 | ✅ `set` 求差/子集判定的正确选择；`issubset` 语义直白 |
| 懒加载 | ✅ 不适用（无大对象构造） |
| 批量操作 | ✅ 全用例 **0.035s**（单跑实测）／模块 32 用例 **0.168s** —— 零性能回归 |

### 维度 5：测试覆盖 —— ⚠️ 有条件通过（F-1 为唯一缺口；见 F-2 方案比较）

| 检查项 | 结论 |
|---|---|
| 核心路径有测试 | ✅ "守卫能否命中 M1 签名"由同文件 L497-518 **两个合成样本用例**钉住（含 task_id/行号/期望列形断言），**非**依赖本活体用例 |
| 边界测试 | ✅ 空命中集合（skip）、部分命中（非空态）、已知集合外误报（L545 subset）三条分支语义均明确 |
| 错误路径测试 | ⚠️ **F-1 缺口**：守卫 fail-closed（`status=FAIL` / unreadable）路径在本用例内不产生红相 |
| 覆盖率达标 | ✅ 本用例改动面（3 行逻辑）被自身路径全覆盖；32/32 用例通过、`skipped=1` 恰为本金丝雀，零新增失败（与 EVD-1033 记录的全量 delta=1 项口径吻合） |

**反相（红绿）证据可信性裁决**（任务第 3 项）：
- 反相一（其它两个测试双红，`SKILL.md→9.9.9`）：**与本文件无关**，仅证明 harness/版本钉耦合，不构成对本 skip 的防护证明 —— **不作为证据采信**。
- 反相二之 subset 相（未知 ragged 行 FIX-999 → L545 FAIL `{'FIX-999'}`）：**证据充分**。我独立复核了 subset 语义与其无条件执行位置（§二.3/§三.1），该相成立可信。
- 反相二之 skip 相（已知 ragged 行 FIX-279 → 非空 → 未 skip）：可证"**命中集合非空时不会 skip**"（L546 的 `if not flagged` 逐字支撑）。
- **关键结论**：以上两相**足以证明 skip 不是无条件吞掉失败**——方向 1（新误报被 subset 拦下）有实证；方向 2 由 L546 条件语义（仅 `flagged` 为空才 skip）与 L553 恒真性共同锁死，不存在"任何失败都 skip"的通道。
- **防护边界（Developer 自述标注，经我核实成立）**：`skipTest` 分支本身**无红相**；且我进一步指出：**改前的"必须命中"断言在改后变为不可达（L553 恒真）**，故"已知 M1 行重新出现"在 live 面上**只 skip、不红**。Developer 的处理是**诚实披露**（docstring L530-536 明写"live 数据零命中属数据已治愈的正常终态""不再存在 live M1 evidence 可断言"，并指定合成用例为命中能力钉）——**判定：标注诚实，不构成新 finding**；但该边界正是 F-2 的核心权衡，故我在此显式升级面向 Coordinator 可见，并作为 F-2 的裁决依据而非重复指控。

---

## 四、AI 代码专项 5 项（逐条结论）

| # | 专项 | 结论 | 事实依据 |
|---|---|---|---|
| 1 | **mock 残留** | ✅ **无残留** | 本改动**零 match** 于 `mock`（L540-554 内无 `mock.patch`）；同文件 L492-493 的 `mock.patch.object(vw, "SAMPLE_PATH"/"GOVERNANCE_DIR")` 属**合成样本 `_issues()` 夹具的既有正向用法**（tempdir 隔离），非调试残留、非本次改动 |
| 2 | **硬编码返回值** | ✅ **无** | 本次新增代码无任何伪造返回值/短路返回；`_KNOWN_M1_IDS`（L428）为既有的**契约常量**（M1 签名白名单），其硬编码是 subset 断言的设计前提而非掩饰；skip 理由为字面事实陈述，非硬编码"成功" |
| 3 | **幻觉 API** | ✅ **无** | 新增调用仅 `unittest` 既有 API `self.assertTrue` / `self.skipTest`（均已在同方法/同文件内既有使用）；无新 import、无未定义符号；**32/32 用例实跑通过**为最强反证 |
| 4 | **未实现 TODO** | ✅ **无** | 本次改动新增文本零 `TODO/FIXME/XXX/HACK`；无 `pass` 占位、无空实现、无 `pytest.mark.skip` 装饰器 |
| 5 | **过度实现** | ✅ **无** | 改动面最小：仅 1 处条件分支 + docstring 同步，**未触及产品代码**（`verify_workflow.py` 零改动，`git status` 已核实）；未顺带重构、未改测试名、未引入无关断言 → 符合 P-v1 D4「不做冗余修改」 |

---

## 五、设计一致性 —— ✅ 通过

1. **FEAT-011（governance-write-guard）语义仍成立** ✅
   - 变更**不触碰**守卫实现（`verify_workflow.py` 未在 diff 内，且我实测其 `governance-write-guard` 四面绿 / 0 issue / exit 0），仅调整测试对活体数据的**断言口径**；
   - 守卫"只检不改"契约、四面结构、exit 0/1/SKIP 语义零变化；
   - 本用例经 L11 实测确认读**真实宿主 plan-tracker**（`HOST_PROJECT_ROOT` 解析正确），故"活体金丝雀"身份保留，未退化为空转。

2. **FIX-293（数据修复）语义仍成立** ✅
   - FIX-293 交付 = M1 四行行形状归一 + 守卫 FAIL 7 → PASS/exit 0（EVD-963 / plan-tracker L204 / 我实测 CLI 三方互证）；
   - 改动后 docstring 由"FIX-293 **将**修数据"改为"**已**修数据"——与 EVD-963 记录的实际状态一致，属**正确的语义同步**（消除了改前的时序失真叙述）；
   - 新增 skip 分支正是"数据已治愈"这一终态的显式建模，与 FEAT-011 born-red 窗口闭合的叙事一致。

3. **F-5（P3）测试名与行为的术语诚实性 —— 明确裁决：部分不一致**
   - **裁决**：`test_live_plan_tracker_flags_only_known_m1_rows` 在 **skip 时不能成立**。名称含两个承诺：(i) `flags`（守卫**命中** rows）与 (ii) `only`（命中**仅限**已知集合）。skip 分支只兑现 (ii)（subset 仍生效），**不兑现 (i)**（零命中、无任何行被 flag）。故 skip 场景下名称**过度声称**。
   - **减责事实**：docstring（L530-536）已显式披露"不再存在 live M1 evidence 可断言"，且 skip 理由字符串同步声明零命中 —— **披露充分，非隐蔽失实**；模块整体为测试资产，不进入产品宣示面，无对外误导风险。
   - **建议（P3，择一）**：
     - 更准确措辞 A（最小改）：`test_live_plan_tracker_reports_no_new_m1_rows`；
     - 更准确措辞 B（保留 subset 语义）：`test_live_plan_tracker_only_known_m1_rows_or_clean`。
   - 若采纳 F-2 方案 (b)，名称可保持不改（因 (b) 下"零命中"本身成为硬断言，`only`+`flags` 的双承诺已被"恰为零"覆盖）。

4. **与授权依据的一致性**：FIX-328 是 `test-baseline-0.80.0.md` §4-F2 的承接修复（见 F-4），改动方向（消除 live 断言与数据修复的时序耦合）与该文档诊断一致 ✅。

---

## 六、发现表（每条含位置 / 级别 / 事实依据 / 影响 / 修复建议）

| ID | 位置 | 级别 | 问题 | 事实依据 | 影响 | 修复建议 |
|---|---|---|---|---|---|---|
| **F-1** | `test_triage_write_guard.py:546-552`（配合 `verify_workflow.py:22415-22426`） | **P2** | 新增 skip 分支吞掉守卫唯一的 fail-closed 信号：plan-tracker 不可读时 `status=FAIL` 且 `task_id=""` ⇒ `flagged` 空 ⇒ subset 恒真 ⇒ skip（改前同场景 FAIL） | 守卫 except 分支返回 `status:"FAIL"` + `task_id:""`（L22418-22424）；L543 只取 task_id；L545 空集子集恒真；改前无 skip 分支故必红（HEAD 原文已核实） | 自本次改动起，"活体 plan-tracker 不可读"在测试面**不再变红**而静默跳过；影响限测试面（产品 CLI 仍 exit 1），触发条件窄 | 本会话采纳单行修复：L545 后插入 `self.assertEqual(result["plan_tracker"]["status"], "PASS", result["plan_tracker"])`（无 issue ⇒ status 必 PASS，两种健康/退化场景下均不误红，已复算） |
| **F-2** | `test_triage_write_guard.py:525-554`（取舍记录缺失） | **P2** | 在 (a)"保留 live 语义 + 条件 skip"与 (b)"非空断言外移 / 改为 `assertEqual(set(), flagged)`"间选 (a)，但**未记录 (b) 的排除理由**，且与授权文档的修复候选不一致；同时在 (a) 下"已知 M1 行重现"只 skip 不红（L553 恒真） | `test-baseline-0.80.0.md:111` 明写修复候选为 `assertEqual(set(), flagged)`（即 (b)）；我实测 (b) 可行（`flagged=set()`、`set()==flagged → True`）；L553 因 L546 前置条件而成死代码 | (a) 比 (b) 弱：live 面**丧失**"任何 M1 行重现即红"的越界信号（该信号对"允许 M1 行重现"的 (a) 取舍而言其实是负向价值）；**不构成 P0/P1**——subset 防护未弱化、合成用例钉住命中能力、live 金丝雀仍活 | 首选：改用 (b)（`self.assertEqual(set(), flagged, …)`，F-2 与 F-3 同时消解，语义最强且与 §4-F2 建议一致）；若保留 (a)：在 docstring 补 1 条排除理由（建议措辞："(b) 会使『合法 M1 行重新入账』时用例变红，本测试定位为**误报**金丝雀而非**存量缺陷**断言，故取 (a)"）；无论何选，建议把 (a)/(b) 取舍按 DEC 入账（超出本次代码面，属 Coordinator 范围） |
| **F-3** | `test_triage_write_guard.py:553-554` | **P3** | skip 后残留的"必须命中"断言成为**死代码**：可达即恒真（`flagged` 非空），恒真不断言 | L546 `if not flagged: skip` ⇒ 得达 L553 则 `flagged` 必非空 ⇒ `assertTrue(flagged, …)` 恒真；改前该断言是唯一非空保护，改后失去效力 | 残留冗余易被后续维护误读为"非空仍有断言保护"；无功能影响 | 删除 L553-554；若希望保留该语义，改为对**合成样本**断言（(b) 同族），或按 F-1 方案把 status 纳入断言 |
| **F-4** | `test_triage_write_guard.py:548-551`（skip 理由字符串） | **P3** | skip 理由引用 `archive/index.md` 条目作为"归档迁出"依据，但索引仅为**位置目录**；且遗漏更直接证据（`plan-tracker` 三行 grep 零命中 + 归档文件字面行） | 我需二次跳转并读 `archive/tasks/v0.1.0~v0.78.0.md` L131-133 才确证字面行存在；索引 L391-393 仅声明完成状态与位置 | 理由**结论成立且可复核**（我已独立证实，非失实），但引用链偏弱，未来读者需重复二次取证 | 理由字符串改为直指强证据，例如："FIX-222/223/224 已迁出至 `archive/tasks/v0.1.0~v0.78.0.md` L131-133（index.md L391-393 定位）" |
| **F-5** | `test_triage_write_guard.py:525`（测试名） | **P3** | 测试名 `…_flags_only_known_m1_rows` 在 skip 时过度声称（`flags` 承诺未兑现） | §五.3 裁决；skip 理由自陈零命中 | 名称与 skip 行为语义张力；docstring 已披露，无对外误导 | 择一改名：`…_reports_no_new_m1_rows` / `…_only_known_m1_rows_or_clean`；或采纳 F-2 的 (b) 后名称自然成立 |

**非本 diff 的流程观察（不计入级别、不阻塞本审查，供 Coordinator 记账）**：EVD-1033（`evidence-log.md:2094`）已把"活体金丝雀数据漂移 1"项归因至 **FIX-328**，但 `.governance/plan-tracker.md` 与 `execution-packets.json` 中**均无 FIX-328 行/包**（我已 grep 确认）。属任务入账缺口，建议 Coordinator 补登以保依赖链与 18c 包完整。

---

## 七、命令上报（逐条：命令 / 退出码 / 输出摘要）

| # | 命令（只读） | 退出码 | 输出摘要 |
|---|---|---|---|
| 1 | `git status --porcelain` | 0 | 目标文件为 ` M`（未暂存）；同仓另有既有 M 项（非本次变更面） |
| 2 | `git diff --stat -- <test file>` | 0 | `1 file changed, 21 insertions(+), 1 deletion(-)` —— 与任务描述的 +21/−1 精确一致 |
| 3 | `git diff -- <test file>` | 0 | diff 全文，仅 docstring 1 行被替换，其余 20 行新增（subset 断言原位保留、后置 skip 分支） |
| 4 | `git show HEAD:<test file>`（L520-539 切片） | 0 | 改前无 skip 分支，`subset` 后直连 `assertTrue(flagged, …)` —— 证实改动性质 |
| 5 | `git diff --cached --stat -- <test file>` | 0 | **空** —— 确认未暂存，无越权暂存 |
| 6 | `Select-String … -Pattern "issubset\|self.skipTest\|assertTrue\(flagged"` | 0 | L541 / **L545** / L547 / L553；文件 768 行 —— 锚定行号诚实 |
| 7 | `python -m unittest …test_triage_write_guard -v` | 0 | `Ran 32 tests in 0.168s` / `OK (skipped=1)`；skip 项 = 本用例；零失败 |
| 8 | `python -m unittest …test_live_plan_tracker_flags_only_known_m1_rows -v` | 0 | `Ran 1 test in 0.035s` / `OK (skipped=1)`；skip 理由完整回显，与 L548-551 逐字一致 |
| 9 | `python verify_workflow.py governance-write-guard` | 0 | `Result: PASS — 0 issue(s)`；四面全 PASS（plan-tracker / evidence-log / agent-locks / execution-packets） |
| 10 | `python -c "import verify_workflow as vw; print(vw.HOST_PROJECT_ROOT, vw.SAMPLE_PATH, vw.SAMPLE_PATH.is_file()); r=vw.check_governance_write_shapes(); …"` | 0 | `HOST=D:\AI\…\project_management_workflow`；`SAMPLE_PATH=<repo>\.governance\plan-tracker.md`；`is_file=True`；`plan_tracker status=PASS`；`n_issues=0`；`flagged=set()`；`set()==flagged → True`（(b) 方案可行性 + live 零命中真实性双向确认） |
| 11 | `Select-String -Path .governance/archive/tasks/v0.1.0~v0.78.0.md -Pattern "FIX-222\|FIX-223\|FIX-224"` | 0 | 归档文件存在；L131/132/133 命中三行字面任务行 —— 归档迁出**字面证实** |

> 未执行任何写操作命令；未执行 `git add/commit/restore/reset/checkout/stash`；未访问仓库外路径（`.governance/archive/index.md`、`plan-tracker.md`、`evidence-log.md`、`docs/requirements/` 全在仓库内，属只读范围）。

---

## 八、结论

**APPROVED_WITH_NOTES —— `unresolved_blockers=0`**

- 核心防护（`flagged ⊆ _KNOWN_M1_IDS`）经逐字核实**未被弱化**：L545 无条件先执行、位于 skip 之前、无异常路径可绕过 —— Developer 该条声称**属实**。
- skip 理由的三项可复核事实（FIX-222/223/224 归档迁出、FIX-279 行形归一、EVD-963 记录 FAIL 7 → PASS）经我**独立读盘**（含归档文件字面行）**全部成立**，非"用 skip 掩盖真实缺陷"。
- 反相二（subset 相）证据充分；skip 分支**无红相**的防护边界经 Developer 诚实自述、经我核实成立，未构成隐蔽失实。
- 改动达成 FIX-328 目标（消除 live 断言与数据修复的时序耦合），且经 `test-baseline-0.80.0.md` §4-F2 授权承接。
- **无 P0、无 P1**，硬门槛全部通过；F-1~F-5 为 P2/P3 非阻塞项，其中 **F-1（P2）建议本会话内以单行断言修复**（修复后本结论可直接沿用，无需重开审查轮次；若 Coordinator 从严升为 P1，则须返工后重新审查）。

**返回给 Coordinator**：`APPROVED_WITH_NOTES`（`unresolved_blockers=0`），报告路径 `docs/reviews/review-FIX-328-CODE-R0.md`。
