# Code Review — FIX-330-CODE-R0：FIX-330 测试收口的独立代码审查（round 0）

| 项 | 值 |
|---|---|
| Task ID | FIX-330 |
| 审查 round | **R0**（首轮；前轮引用 = `docs/reviews/review-FIX-328-CODE-R0.md`，仅作背景，**未修改**） |
| 审查对象 | 工作树**未暂存**改动（`git diff`，非 `--cached`）——`.git/hooks` 要求 FIX- 前缀产品代码 commit 前置审查，无 commit hash |
| 变更面 | **恰 1 文件 +63/−5**：`skills/software-project-governance/infra/tests/test_triage_write_guard.py`（`git diff --stat` 实证 `1 file changed, 63 insertions(+), 5 deletions(-)`；`git diff --cached --stat` 为空 ⇒ 未暂存，与任务描述一致）；3 处 hunk 全在 L526-592 |
| 审查类型 | Code Review（`agents/code-reviewer.md` + `skills/code-review/SKILL.md` 全文加载执行） |
| Reviewer | Code Reviewer sub-agent（独立于 Developer） |
| 日期 | 2026-09-14 |
| 审查约束 | **只读**：Read / Grep / Glob + 只读命令（`git diff/show/status`、`python -m unittest`、`python -c` 只读探针、`%TEMP%` 副本内的自建验证 harness）；**未执行任何写操作**，未执行 `git add/commit/restore/reset/checkout/stash`；未触碰 `$env:USERPROFILE\.dsh` / `$HOME/.dsh` / 仓库外既有资产；唯一产物 = 本报告 |

---

## 一、终态结论（硬门槛裁决）

**APPROVED_WITH_NOTES —— `unresolved_blockers=0`**

- **P0 = 0**；**P1 = 0**；**P2 × 1**（转出项，非本 diff 缺陷）；**P3 × 3**（全部非阻塞，见 §六）。
- 硬门槛逐条裁决：

| 门槛项 | 阈值 | 裁决 | 依据 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | ✅ 通过（0） | 无 P0 |
| 5 维度全覆盖 | = 100% | ✅ 通过 | §三 正确性 / 安全性 / 可维护性 / 性能 / 测试覆盖 逐项有结论 |
| 每条发现标注级别 | = 100% | ✅ 通过 | F-1~F-4 全部带 P0~P3 标签 |
| 设计一致性检查 | 已完成 | ✅ 通过 | §五：与授权候选 `test-baseline-0.80.0.md:111`、守卫契约 `verify_workflow.py` plan_tracker 分支、FIX-328/R0 五条 finding 的处置逐项比对 |
| AI 代码专项 5 项 | 全部完成 | ✅ 通过 | §四：mock 残留 / 硬编码 / 幻觉 API / 未实现 TODO / 过度实现 五项逐一有结论 |

按 `skills/code-review/SKILL.md` 循环角色契约：本结论为**通过终态**，无未解决 BLOCKING finding，独立结构字段 **`unresolved_blockers=0`**。

---

## 二、对 FIX-328/R0 F-1 前提证伪的明确裁决（任务第 1 项 —— **重点**）

### 裁决：**证伪成立。FIX-328/R0 的 F-1「本次改动引入真实测试灵敏度回退」是误判**；FIX-330 的更正（真实缺陷降级为**诊断失真**）**成立且已机录**。

我不采信任何自述，改用**行为级反相重演**独立裁决：从 `git show HEAD:` 取回改动前原文，按 FIX-328 自述在**同一锚点**注入条件 skip 以重建 (a) 版，再与工作树 (b) 版三版本 × 4 场景对跑（harness 见 §七命令 4；每版本用其自身副本，stub 仅在进程内改写模块级 `SAMPLE_PATH`/`GOVERNANCE_DIR`）。

| 版本 \ 场景 | healthy（live 现状） | known_replay（FIX-279 行重现） | unknown_new（FIX-999 行） | **unreadable（独占锁文件）** |
|---|---|---|---|---|
| **HEAD**（改前） | **FAIL**：`AssertionError: set() is not true : live M1 four rows must be flagged (FEAT-011 acceptance: audit-149 §4 M1 live evidence)` | PASS（无红相） | FAIL：`False is not true : {'FIX-999'}` | **FAIL：`False is not true : {''}`** |
| **FIX-328(a)**（重建） | **SKIP**（`simulated FIX-328(a) skip`） | **PASS（GREEN）** ← 灵敏度回退所在 | PASS（无红相） | **FAIL：`False is not true : {''}`** |
| **FIX-330(b)**（工作树） | PASS | **FAIL**：`'FIX-279' : live plan-tracker 零命中契约被破坏…` | FAIL：`False is not true : {'FIX-999'}` | **FAIL：`'' unexpectedly found in {''} : {'status': 'FAIL', 'issues': [{'type': 'plan_tracker_unreadable', …` |

### 三条待裁决命题的逐条判定

1. **`{''}` 确为非空集；`{''}.issubset(_KNOWN_M1_IDS)` 确为 False —— ✅ 成立（实测）**
   - 不可读分支实测：`[GUARD] status=FAIL n_issues=1 task_ids=[''] types=['plan_tracker_unreadable']`；
     `[SEMANTICS] flagged_nonempty=True subset_known=False eq_empty=False contains_empty_str=True`。
   - 触发条件是**真实的不可读**而非命名把戏：父进程对 `%TEMP%` 副本持有 `msvcrt.LK_NBLCK` 独占锁后，
     `[READPROBE] read_text raised PermissionError: [Errno 13] Permission denied`，`[STUB] locked-path is_file=True`
     ⇒ 走 `verify_workflow.py:22412` `is_file()` 为真 → L22415 `except (IOError, OSError)`（`PermissionError` 是 `OSError` 子类）分支。
   - **代码语义复核**：`verify_workflow.py:22416-22426` 该分支返回恰好 1 条 issue，`"task_id": ""`（L22422），
     故 `flagged = {i["task_id"] …} = {""}`——非空集；`{""}.issubset({"FIX-222","FIX-223","FIX-224","FIX-279"})` 语义上必为 `False`。
   - **改前必红**已被逐字回放：HEAD 版在不可读场景 `fail=1`，traceback 文本 **`AssertionError: False is not true : {''}`** ——
     与 R0 报告 F-1 引用的措辞**逐字相同**，且**未发生任何 skip**。

2. **`status=="PASS" ⟺ issues==[] ⟺ flagged==set()` 的等价性 —— ✅ 成立（在计划内可达状态上）**
   - 代码面：`verify_workflow.py:22429-22432` 可读分支 `status = "FAIL" if issues else "PASS"` ⇒ `PASS ⟺ issues==[]`（同一局部变量，无第二来源）。
   - `issues==[] ⟺ flagged==set()` 的**剩余方向**由 L22257-22296 全量证明：该函数**只**在 L22275、L22286 两处 append，两处均写
     `"task_id": task_id`，而 `task_id = cells[task_idx].strip().strip("*")`（L22272）来自 `_TASK_ID_CELL_RE` 命中的单元格——
     实测 `_TASK_ID_CELL_RE.pattern = ^(?:\*\*)?[A-Z]+-\d+(?:\*\*)?$`，对 `''` / `' '` / `'P0'` 均 `match → False`
     ⇒ **可读分支永不产出空串 task_id**，故 `issues==[] ⇔ flagged==set()`。
   - 全模块 `check_governance_write_shapes()` 仅 2 处给 `plan_tracker` 赋值（L22416、L22429），无第三来源。
   - 实测闭合：live 现状 `[GUARD] status=PASS n_issues=0 task_ids=[]`。
   - **附带的严格性**：该等价性只要求 `issues==[] ⇒ status==PASS` 单向为真即成立（b 版 F-1 建议断言依赖此方向），已证。

3. **因此「真实灵敏度回退」是误判，正确缺陷命名是「诊断失真」—— ✅ 裁决成立**
   - F-1 的机制主张（「`flagged == set()` ⇒ `set().issubset(…)` 恒真 ⇒ 落入 skip」）在**不可读场景不成立**：
     `flagged` 是 `{''}` 而非 `set()`，subset 断言返回 False，用例在该行即中止，**skip 分支不可达**。实测 (a) 版该场景 `skip=0`。
   - R0 报告 F-1「反证」段的原话——"改前（`git show HEAD:...` 已核实）无 skip 分支，同场景在第 2 条断言 `assertTrue(flagged, …)` 处 **FAIL**"
     ——**该句本身正确**；出错的是它的**推论**：同一事实说明改后该场景**仍在同一行 FAIL**，而非「从红变静默跳过」。基于该推论给出的
     F-1 定级（「真实测试灵敏度回退」/「自本次改动起…不再变红而静默跳过」/ 建议单行 `assertEqual(status,"PASS")` 修复）**全部失去前提**。
   - **降级后的真实缺陷**：`{''}` 只表达"某个 task_id 是空串"，不指向"不可读"，失败诊断为**失真措辞**（R0 原文称"`{''}` 不是已知集合子集"）；这是**既有表述弱点**（改前即如此），非 FIX-328 引入，FIX-330 以 `assertNotIn("", flagged, face)` 收口正确。
   - **但 F-1 并非全无价值**：它把"守卫 fail-closed 面无断言"这一长期缺口暴露出来，FIX-330 的 ① 正是该缺口的正确最小收口。**结论：结论错、动机对、处置对。**

4. **FIX-330 本轮灵敏度增益（任务第 4 项前半）—— ✅ 独立复核成立**
   - 关键差异实证：**已知 M1 行（FIX-279）重现**场景，(a) 版 `fail=0 err=0 skip=0`（**GREEN**，静默放过），(b) 版 `fail=1`（**RED**）。
   - 说明：**(b) 恢复了「已知四行重现即红」的越界信号**，而 (a) 在 subset 通过后无任何非空约束，属真实的可观测漏洞——这一条与 F-1 的误判**是两件独立的事**（R0 的 F-2/F-3 已正确指出），FIX-330 的采纳使其闭合。

---

## 三、5 维度逐项结论

### 维度 1：正确性 —— ✅ 通过

| 检查项 | 结论 |
|---|---|
| 逻辑正确 | ✅ 三条判据与 docstring 声明的判据顺序**逐字一致**（L580 ① → L582 ② → L586-592 ③）；实测 live 场景 `fail=0 err=0 skip=0`，达成 F-2(b) 的"零命中即断言"意图 |
| 边界条件 | ✅ 四个可达分支场景均实测有确定终态（§二矩阵）：不可读→①红、已知行重现→③红、未知行→②红、live→绿 |
| 断言顺序正确性 | ✅ ① 位于 ②③ 之前，且在 `flagged` 构造之后立刻求值；不可读场景实测红在 ①（`'' unexpectedly found in {''} : {'status': 'FAIL', …}`），**诊断直指 face 字典**（含 `plan_tracker_unreadable`，优于 R0 建议措辞：实测保留 status 断言时该场景明写 `plan_tracker_unreadable` + OS 错误） |
| 死码清理 | ✅ 原 `assertTrue(flagged, …)` 已删除；F-3 死断言消解（`git diff` 实证 −5 行含该断言与其续行） |
| 并发安全 | ✅ 不适用且无风险：只读调用 `check_governance_write_shapes()`；stub 为单进程内模块级赋值，无跨用例泄漏（各版本各副本独立进程实测） |
| 资源管理 | ✅ 无新增资源；`tempfile.TemporaryDirectory`（`_issues()` L489）由既有 `with` 管理，本次未触碰 |
| 跳过路径 | ✅ 保留的 `if not vw.SAMPLE_PATH.is_file(): skipTest(...)` 为**既有结构**（HEAD 版同在此处），非本次引入；实测 live 下不触发（模块 `skipped=0`） |

### 维度 2：安全性 —— ✅ 通过（零新增风险面）

| 检查项 | 结论 |
|---|---|
| 输入校验 | ✅ 不引入外部输入面；唯一输入为真实 `plan-tracker.md`（`read_text(encoding="utf-8")`，FIX-278 G4/F 纪律） |
| 注入防护 | ✅ 新增代码仅 `set` 成员判定/子集判定/`assertEqual` + 中文字符串常量；无 `eval/exec/subprocess/shell`、无路径拼接、无 SQL/命令面；无文件写入 |
| 敏感数据 | ✅ 无密钥/token/凭据；新增文本仅含仓库内治理 ID 与仓库内相对路径 |
| 权限检查 | ✅ 只读测试；未越出仓库（本报告自身受同一约束；`%TEMP%` 副本仅用于验证 harness，不在仓库内） |
| 文件卫生 | ✅ 实测：无冲突标记（0）、无 BOM（首 3 字节 `34,34,34`）、无 CR（CR=0，LF）、被审文件未被写入（改动前后 `git diff --stat` 恒为 `63 insertions(+), 5 deletions(-)`） |

### 维度 3：可维护性 —— ✅ 通过（含 P3 观察）

| 检查项 | 结论 |
|---|---|
| 命名可读 | ✅ 局部名 `face` / `flagged` 语义清晰（`face` 与守卫四面返回结构、docstring ① 的"面级"术语一致）；新增注释逐字解释 each 判据的"为什么" |
| 函数长度 | ⚠️ docstring 45 行（L526-571）+ 方法体 21 行（L572-592）= 66 行；**docstring 超代码体**。但内容为可复核事实陈述与取舍论证（非泛化叙事），且本仓审查链（R0）明确要求披露取舍理由（F-2/F-5），故判定**必要且价值高于成本**，不作 finding |
| 重复代码 | ✅ 无新增重复；三条判据各 1 行，无镜像分支 |
| 注释质量 | ✅ 注释与代码逐字一致：L577-579 注释声明"须先于命中集合判据暴露" ↔ L580 实际位置早于 L582/L586；L581 ② ↔ L582 实现；L583-585 ③ ↔ L586 实现 |
| 文档一致性 | ✅ 引用的两个合成样本用例名列实测存在（L497、L509）；`_KNOWN_M1_IDS`（L428）与 ② 一致 |

### 维度 4：性能 —— ✅ 通过

| 检查项 | 结论 |
|---|---|
| 算法复杂度 | ✅ 新增 3 条 O(1) set 谓词；守卫侧未改动，仍为单遍 O(n) 行扫描 |
| 数据结构 | ✅ `set` 的成员/子集/相等判定为正确选择 |
| 批量操作 | ✅ 模块 32 用例实测 **0.129s**（`Ran 32 tests in 0.129s`）；零性能回归 |
| 懒加载 | ✅ 不适用（无大对象构造） |

### 维度 5：测试覆盖 —— ✅ 通过（含 F-1 观察）

| 检查项 | 结论 |
|---|---|
| 核心路径有测试 | ✅ 三条判据各自有**可失败**的独立场景，全部由我实测触发（§二矩阵）：① 不可读、② 未知行 FIX-999、③ 已知行 FIX-279 重现 |
| 边界测试 | ✅ live 健康态（零命中）实测全绿，与零命中断言不冲突 |
| 错误路径测试 | ✅ 守卫 fail-closed（不可读）路径**本次首次**获得红相（①）；残余 `status` 字段本身无直接断言（P3 F-1） |
| 无恒真断言 | ✅ **逐条可达性推演**：① 可达（不可读场景实测红，非恒真——构造 `flagged={''}` 即 False）；② 可达（FIX-999 实测红，非恒真）；③ 可达（FIX-279 实测红，非恒真）。**三者均非「可达即恒真」** |
| 覆盖完整性 | ✅ 与守卫 plan_tracker 分支的状态空间一一对应：**A** 可读+issues（②/③ 覆盖）、**B** 可读+无 issues（③ 覆盖）、**C** 不存在（守卫内无路径）、**D** 不可读+1 issue `task_id=""`（① 覆盖）。该覆盖成立依赖 §二.2 已证的 `issues==[] ⇔ flagged==set()` |
| 覆盖率达标 | ✅ 模块 32/32 通过、**`skipped=0`**（改动前为 `OK (skipped=1)`）；单跑金丝雀 `Ran 1 / OK` |

---

## 四、AI 代码专项 5 项（逐条结论）

| # | 专项 | 结论 | 事实依据 |
|---|---|---|---|
| 1 | **mock 残留** | ✅ **无残留** | 本次新增/改动区域内（L526-592）零 `mock` 匹配；同文件 `mock.patch.object`（L492-493）属 `_issues()` 合成夹具的**既有正向用法**（tempdir 隔离），本次未触碰。金丝雀用例自身**不做 mock**（读真实 `SAMPLE_PATH`），其"隔离"由 `%TEMP%` 副本 harness 在**审查侧**实现，不进入产品测试面 |
| 2 | **硬编码返回值** | ✅ **无** | 无伪造返回值/短路返回；`_KNOWN_M1_IDS`（L428）为既有契约常量（M1 签名白名单），是 ② 的设计前提；③ 以 `set()` 为期望值，搭配实测 `flagged=set()` 一致，非硬编码"成功" |
| 3 | **幻觉 API** | ✅ **无** | 新增调用仅 `unittest` 既有 API `assertNotIn` / `assertEqual` / `assertTrue`；无新 import、无未定义符号；`num`/`msg` 参数用法符合 `AssertionError` 语义（不可读场景实测消息为 `'' unexpectedly found in {''} : {'status': 'FAIL', …}`）。**32/32 实跑通过**为最强反证 |
| 4 | **未实现 TODO** | ✅ **无** | 改动区域零 `TODO/FIXME/XXX/HACK`（实测 0 命中）、无 `pass` 占位、无新增 `@skip` 装饰器 |
| 5 | **过度实现** | ✅ **无** | 改动面最小且纯粹：1 处 docstring 重写 + 3 条判据 + 1 处死断言删除，**未触碰产品代码**（`verify_workflow.py` 零改动）、未顺带重构、未改测试名（P3 F-5 采纳"保留+披露"）、未引入无关断言 ⇒ 符合 P-v1 D4。docstring 篇幅偏大但内容为审查链（R0 F-2/F-5）**明确要求**的取舍披露，非冗余 |

---

## 五、设计一致性 —— ✅ 通过

1. **与授权候选一致（任务第 4 项后半）—— ✅ 逐字核实**
   - `docs/requirements/test-baseline-0.80.0.md:111` 原文：`修复候选：断言反转为 \`assertEqual(set(), flagged)\`（AUDIT-152 邻域，本任务不改测试文件）`。
   - 工作树 L586-587：`self.assertEqual(set(), flagged, "…")` —— **参数顺序与语义逐字一致**（`first == second` ⇒ `set() == flagged`），仅补充了失败消息（属加强，非偏离）。文档自述"本任务不改测试文件"正说明修复属承接任务，FIX-330 采纳该候选**方向正确**。

2. **与守卫契约一致（FEAT-011）—— ✅**
   - 变更**不触碰**守卫实现（`verify_workflow.py` 零改动）；只检不改契约不变；本测试仍读真实活体 `plan-tracker`。
   - 实测 live 面：`flagged=set()`、`n_issues=0`、`status=PASS`（双向一致：守卫 CLI 同数据同为零命中）。

3. **对 FIX-328/R0 五条 finding 的处置逐条比对 —— ✅ 全部闭合**

| R0 finding | 级别 | FIX-330 处置 | 我的裁决 |
|---|---|---|---|
| F-1（"真实灵敏度回退"） | P2 | 前提证伪 → 降级为诊断失真；以 ① `assertNotIn("", flagged, face)` 收口 | ✅ 证伪成立（§二）；① 收口有效（不可读场景实测红） |
| F-2（(a)/(b) 取舍未记录、与授权不一致） | P2 | 采纳 (b)，docstring 记录 3 条取舍理由 + 授权出处 | ✅ 已闭合；取舍理由 1/2/3 与我的实测一致（§二.4） |
| F-3（`assertTrue(flagged)` 死代码） | P3 | 删除，并在 docstring 声明义务由合成用例 + ③ 承接 | ✅ 已闭合；实测 (b) 下三者均非恒真 |
| F-4（skip 理由证据链偏弱／遗漏直接证据） | P3 | 改为直指 `archive/tasks/v0.1.0~v0.78.0.md` L131-133 字面任务行 + index 定位 | ✅ 已闭合；归档文件 L131/132/133 实测为 FIX-222/223/224 的**字面任务行**（非索引声称） |
| F-5（测试名在 skip 时过度声称） | P3 | 保留名称 + docstring 披露术语边界（改称"欠声称"） | ✅ 可接受（§六 F-3 裁决） |

4. **与治理记录一致** —— ✅
   - `plan-tracker.md:99`、`DEC-194`、`execution-packets.json`（`FIX-330` 短包 L919+）均已登记本任务的**同一事实**（F-1 证伪 + 采纳 (b) + 哨兵门禁），与本报告裁决无矛盾；残留项已分派 FIX-332 / FIX-333（P2，均"不阻断 0.81.0"）。

---

## 六、发现表（每条含位置 / 级别 / 事实依据 / 影响 / 建议）

| ID | 位置 | 级别 | 问题 | 事实依据 | 影响 | 建议 |
|---|---|---|---|---|---|---|
| **F-1** | `test_triage_write_guard.py:580`（①） + 全模块缺 `status` 断言 | **P3** | ① 断言的是**哨兵字符串**而非**状态字段**：守卫的 `status` 字段在整个测试资产内**无任何直接断言**（`test_triage_write_guard.py` 只消费 `["issues"]`）。现契约下二者等价（§二.2 已证），故当前**零功能缺口**；但「守卫将来新增 `status` 取值却不同步 `issues`」的形态无人拦截 | 实测：`assertNotIn("", flagged, face)` 依赖守卫 L22422 恰好把哨兵写成 `""`；同文件仅有 `test_change_triage.py:1393` 断言 `agent_locks` 面 status，**无** plan_tracker 面 status 断言（grep 全仓核实）；`_TASK_ID_CELL_RE` 实测排除空串 ⇒ 可读分支不可能产出 `{''}`，口径唯一 | 若守卫异常分支改填真实 task_id 或改哨兵（如 `"<unreadable>"`），① 失效且无替代信号；届时仍是**红相**（`{'<unreadable>'}` 触发 ②）而非静默，故影响有界 | **不必本轮改**。若采纳，最小加码 = 在 L580 前加 1 行 `self.assertEqual(face["status"], "PASS", face)`：实测 4 场景下**均不误红**、**不产生死断言**（其失败域 `{不可读 FAIL}` 与 ① 重叠、与 ②③ 不重叠），且可在 ① 被改坏时充当第二道门。**不加不构成阻塞**（现契约 ①+②+③ 已闭集） |
| **F-2** | `docs/reviews/review-FIX-328-CODE-R0.md` F-1 全文（P2 级前提被证伪） | **P2（转出项，非本 diff 缺陷）** | 历史审查报告以**错误前提**给出 F-1 定级与"真实回退"定性；该报告是历史记录不得修改，F-1 更正**必须另行登记** | §二矩阵：不可读场景 HEAD/(a)/(b) 三版**均红**、skip=0；R0 报告 L82「是它真实引入的测试灵敏度回退」与 L83「在本测试内从"红"变"静默跳过"」两句被实测证伪 | 若不登记，后续读者（含复核 0.81.0 发布门禁者）会据该报告认为 FIX-328 曾引入回退，并据此误判 FIX-328/330 的审查链质量 | 登记更正（不改原报告）：`DEC-194` 已载"事实更正"段（**请求 Coordinator 复核其完备性**），`plan-tracker.md:100` FIX-332 已承接"历史报告前提更正登记"。建议登记文本显式引用本报告 §二矩阵（三版本 × 不可读场景 `fail=1 skip=0`）作为更正依据。**级别 P2 属"数据资产失真"**，与本 diff 无关，不阻塞本审查结论 |
| **F-3** | `test_triage_write_guard.py:542`（docstring 判据顺序声明） | **P3** | 措辞精度：「三条**互不遮蔽**」在不可读场景**不完全准确**——① 会先于 ③ 命中（① 抛 `AssertionError` 后 ③ 不执行），即 ① 对 ③ 存在遮蔽 | 实测不可读场景红在 ①（`'' unexpectedly found in {''}`），③ 未参与；docstring 同段又正确承认"后置还会被 ② 抢占而永不触发"，两处口径略不一致 | 纯文档精度，无功能影响；读者可能误以为三条在同一场景都独立求值 | 建议措辞改为「三条覆盖**互不重复**的场景，① 对 ③ 在不可读场景具优先级（先暴露者胜），**不存在恒真断言**」；可选，不阻塞 |
| **F-4** | `test_triage_write_guard.py:544`、`548`（`verify_workflow.py 22415-22426 / 22429-22432` 行号引用） | **P3** | docstring 以**绝对行号**引用产品文件，行号随 `verify_workflow.py`（24412 行）演进会漂移 | 本次审查实测：L22415-22426（不可读分支）、L22416/L22422（哨兵）、L22429-22432（status 计算）**当前准确**；但 0.80.0→0.81.0 窗口该文件已多次变动 | 未来读者若按行号定位可能落空；本仓已有「行号引用过期」同类教训（FIX-332 登记的过期数据资产） | 可选：行号保留但补语义锚（如 `check_governance_write_shapes()` 的 plan_tracker 异常分支），使引用在行号漂移后仍可二元定位；不阻塞 |

### 残留边界与硬门槛专项裁决（任务第 2 项）

**① 形态的充分性 — 裁决：偏离有据、不弱化防护，残留边界可接受，不必加码。**

1. **偏离性质核实**：FIX-330 **未**逐字采纳 R0 的 `assertEqual(result["plan_tracker"]["status"], "PASS", …)`，改用 `assertNotIn("", flagged, face)`。我实测两个替代方案，其给出的改判理由**均成立**：
   - 「逐字插入会被 subset 抢占」：实测**仅在前置 subset 保留时成立**。若把 status 断言插在 R0 指定的位置（L545 之后、即 subset 之前），它在不可读场景**确实会红**（`failed=1`，消息 `plan_tracker_unreadable`），**不被抢占**——故该子句的表述偏强；而**若置于 ③ 之后**则确被抢占（不可读时 ①/② 先中止）。**就"与 ③ 同置"的意义上，其结论正确。**
   - 「在已知 ID 重现场景使 ③ 成为死断言」：**仅在 `status` 与 `issues` 同源（现契约正是如此）时成立**，实测该情景下 status 断言先红、③ 不可达——F-3 口径成立。
2. **充分性判定**：① 用**同一个不可达性洞**（哨兵 `""`）换取"三判据全活 + 诊断信息更佳"，**未削弱防护**——四个可达场景中"应红"者**全部仍红**（§二矩阵三红一绿），且 ① 的红相消息包含 `plan_tracker_unreadable` 与 OS 错误原文，**局部优于** R0 建议措辞。故**偏离有据**。
3. **残留边界裁决**：docstring 自陈的「若守卫未来变为 `status=FAIL 且 issues=[]`，①②③ 均不捕获」——我独立确认该形态在**现契约不可达**（`"FAIL" if issues else "PASS"` + 异常分支必带 1 issue；全模块仅 2 处赋值），且其**功能性后果为零**（CLI 消费 issue 列表而非 status）。**判定：可接受，P3 级观察（F-1），本轮不要求加码。** 若 Coordinator 按"测试须钉住产品状态字段"从严，则应在**新任务**中处理（含 ② 之外的完整 status 面），而非在本 diff 加一行造成"半覆盖"错觉。

### F-5 测试名不改的裁决（任务第 7 项）—— **可接受，无需最小动作**

- **核实其依据属实**：`skills/software-project-governance/infra/tests/env_failure_classification.json:123` 确以 **FQN 键**登记该用例（`…GovernanceWriteGuardPlanTrackerTests.test_live_plan_tracker_flags_only_known_m1_rows`）；`docs/**` 确有 4 份文件引用该全名（`docs/requirements/env-failure-classification-0.80.0.md:87`、`docs/requirements/test-baseline-0.80.0.md:109`、`docs/reviews/review-AUDIT-152-CODE-R0.md:65`、`docs/releases` 侧 `release-checklist-0.81.0.md:83` + `review-FEAT-011-CODE-R2.md:26`）。改名确会牵动**测试资产键 + docs 引用**，其"超出本任务改动面"的自述**成立**。
- **裁决**：**保留名称可接受**。理由三条：(1) `(b)` 已使"零命中"成为硬断言，名称的 `only` 承诺（命中若存在必属已知四行）**完整兑现**；(2) `flags` 的存在性预设不再兑现，但**任何命中即红**（③），回归信号**未丢失**，只是由"名称承诺"转为"断言承诺"；(3) 名字弱于行为属**欠声称**（不误导使用方），且 docstring L561-566 已显式披露边界与改名牵动面。**不构成 finding，不需最小动作。** 若将来做 FIX-332 的 docs/资产收口，可顺带评估 `…_reports_no_new_m1_rows` 改名（一次性改 5 处引用），归 FIX-332 范围。

### AI 专项之外的流程/资产观察（供 Coordinator，均非本 diff 缺陷）

1. **`env_failure_classification.json:123-130` 已过期**：仍把该用例登记为 `"class": "known_defect" / "family": "test_assertion_stale"`，`evidence` 引用已被删除的 HEAD 断言文本（`'set() is not true : live M1 four rows must be flagged' (test L533)`）——该断言在 HEAD 位于 L533、在 (a) 版移至 L553、在 (b) 版**已删除**。**实测该文件不参与 pytest 运行**（仅被审查/登记流程消费），故对测试结果无影响。→ 已由 `FIX-332` 承接（P2）。
2. **`release-checklist-0.81.0.md:83` 已同步更新**：门禁 10 已把 FIX-328 描述更新为"经 FIX-330 收口…`OK` 且 `skipped=0`"并登记 F-1 证伪。**该处不再是过期项**，FIX-332 的范围应重核为"`env_failure_classification.json` + `test-baseline-0.80.0.md:111` + `env-failure-classification-0.80.0.md:87` + 历史报告前提登记"四处（与 `plan-tracker.md:100` 登记一致）。
3. **守卫 `UnicodeDecodeError` 逸出边界（FIX-333）**：我复核 `verify_workflow.py:22415` 仅捕 `(IOError, OSError)`；非 UTF-8 活体文件时 `read_text(encoding="utf-8")` 抛 `UnicodeDecodeError`（`ValueError` 子类）**不被捕获**，与该方法 docstring 的 "Never raises" 不符——**属既有边界，非本批引入**。就本审查而言：该异常会从 `t.run()` 逸出为 unittest **ERROR**（红相），**不会**被任何判据静默吞掉，故对 FIX-330 的防护结论**无影响**。→ 已由 `FIX-333` 承接（P2，不阻断 0.81.0）。

---

## 七、独立复现声明（我亲自核对/实测的内容）

**读盘核实（不采信自述）**
1. **diff 全文**：`git diff -- <被审文件>` 逐行读毕；`git diff --stat` 实证 `1 file changed, 63 insertions(+), 5 deletions(-)`（与任务描述 +63/−5 精确一致）；`git diff --cached --stat` **空** ⇒ 未暂存；`git status --porcelain` = ` M`。3 处 hunk 全在 L526-592，与任务描述一致。
2. **HEAD 原文对照**：`git show HEAD:<被审文件>`（rc=0，32818 bytes）取回改前原文，逐字确认改前为 `subset` 断言 + `assertTrue(flagged, "live M1 four rows must be flagged …")` 双断言、**无任何条件分支**。
3. **守卫不可读分支实现（亲自只读核对）**：`verify_workflow.py:22411-22432`——`if SAMPLE_PATH.is_file():` → `try: content = SAMPLE_PATH.read_text(encoding="utf-8")` / `except (IOError, OSError) as exc:` → 返回 `{"status": "FAIL", "issues": [{…"task_id": "", "type": "plan_tracker_unreadable"…}]}`；`else:` 分支 `status = "FAIL" if issues else "PASS"`。**逐字确认**：异常分支的 issue **恰 1 条**且 `task_id` 为**空串**；status 只由 `issues` 决定。
4. **`_plan_tracker_task_row_issues` 全量复核**：`verify_workflow.py:22230-22296`——仅 2 处 `issues.append`（L22275 / L22286），两处均写 `"task_id": task_id`；`task_id` 源自 `_TASK_ID_CELL_RE` 命中单元格（L22265-22272）。**实测** `_TASK_ID_CELL_RE.pattern = ^(?:\*\*)?[A-Z]+-\d+(?:\*\*)?$`，对 `''`/`' '`/`'P0'` `match → False` ⇒ 可读分支**不可能**产出空串 task_id（建立 `{''}` 的**唯一**来源 = 不可读分支）。
5. **`check_governance_write_shapes()` 赋值面穷举**：全模块仅 `plan_tracker`（L22416 / L22429）、`evidence_log`（L22440 / L22453）、`agent_locks`（L22462）、`execution_packets`（L22516）四处面赋值，`plan_tracker` **仅 2 处** ⇒ 状态空间四分支（可读+issues / 可读+无 issues / 不存在 / 不可读）无遗漏。
6. **被审代码行号逐字核实**：L428 `_KNOWN_M1_IDS`、L497/L509 两个合成样本用例名、L525 测试名、L572-573 保留的 `is_file()` skip、L575 `face`、L580 ①、L582 ②、L586-592 ③（`assertEqual(set(), flagged, "…")` 参数顺序逐字）。
7. **授权文档逐字**：`docs/requirements/test-baseline-0.80.0.md:107-112` §4-F2 —— L109 用例 FQN、L110 证据原文（`AssertionError: set() is not true : live M1 four rows must be flagged`，标注 `test_triage_write_guard.py L533`）、L111 修复候选 `assertEqual(set(), flagged)` **逐字一致**。
8. **docstring 事实性逐条复核（任务第 5 项）**：
   - 归档文件 `.governance/archive/tasks/v0.1.0~v0.78.0.md` **L131/132/133** 实读 = `| **P0** | FIX-222 | bootstrap prose 消除 …`、`| **P0** | FIX-223 | Coordinator task-completion→next-priority …`、`| **P0** | FIX-224 | review 复审确定性触发器 …` ——**确为三行字面任务行**（非索引声称）✅；`archive/index.md` **L391/392/393** 确为对应位置目录条目 ✅（docstring 已正确区分"仅为位置目录"）。
   - `plan-tracker.md` L201 FIX-279 行、L210 FIX-293 完成行（自述 L188/189/190 + L257 归一、`governance-write-guard` FAIL 7 → **PASS/exit 0**）✅；`evidence-log.md` L1755 EVD-963 原文（`守卫改前 FAIL 7（恰 M1 四行）→ 改后 PASS 0`，产物 `.governance/plan-tracker.md（L188/189/190/251/257）`）✅ ⇒ docstring「FIX-279 行形归一（FIX-293/EVD-963）」的关联**成立**。
   - 「两处合成样本用例钉住**命中能力**」✅（L497 / L509 实存且断言 `plan_tracker_duplicate_priority_cell` / `plan_tracker_trailing_empty_status`）。
   - 「改名会牵动 `env_failure_classification.json` 的 unittest 全名键与 `docs/**` 引用」✅（JSON L123 键 + 4 份 docs 实名引用，grep 实测）。
   - 术语边界「名称弱于行为 = **欠声称**」的论证 ✅ **成立**：(b) 下零命中为硬断言 ⇒ `only` 承诺完整兑现；`flags` 预设不兑现但回归信号由 ③ 承接 ⇒ 名称弱于行为，非过度声称。
   - 唯一细微不精确 = §六 F-3 指出的「三条互不遮蔽」措辞（P3）。

**复算 / 复跑实测**
9. **模块级**：`python -m unittest skills.software-project-governance.infra.tests.test_triage_write_guard` → **`Ran 32 tests in 0.129s` / `OK` / exit 0**，**`skipped=0`**（改动前为 `OK (skipped=1)`，与任务描述一致）。
10. **行为级反相矩阵（我自建 harness，非采信自述）**：3 版本（HEAD / 重建 FIX-328(a) / 工作树 FIX-330(b)）× 4 场景（healthy / known_replay / unknown_new / **unreadable**）逐格实测，原始输出见 §二矩阵。关键三格：
    - **不可读（独占锁真实生效）**：三版本**全部 FAIL、skip=0**，HEAD 与 (a) 版 traceback 均为 `AssertionError: False is not true : {''}` ⇒ **F-1 前提证伪的决定性证据**；
    - **known_replay**：(a) 版 GREEN / (b) 版 RED ⇒ **灵敏度增益成立**；
    - **live healthy**：(b) 版 GREEN（`fail=0 err=0 skip=0`）⇒ 零命中断言不误红。
    不可读性的真实性由两道独立探针确认：父进程 `read_text` 亦抛 `PermissionError ([Errno 13] Permission denied)`，子进程 `[READPROBE]` 同抛。
11. **守卫契约探针**：`[GUARD] status=FAIL n_issues=1 task_ids=[''] types=['plan_tracker_unreadable']`（不可读）；live 面 `status=PASS n_issues=0 task_ids=[]`（`_plan_tracker_task_row_issues(live_text)` 直调 + 全守卫调用双向一致）。
12. **文件卫生**：无冲突标记（0）、无 BOM（`34,34,34`）、CR=0（LF）、被审文件字节数 41495（改动前后 `git diff --stat` 恒等 ⇒ 审查过程未写入）。

> **未采信项声明**：行号引用（`verify_workflow.py 22415-22426` 等）**已逐条实读核对为准确**，未直接采信任务描述或 Developer 自述；(b)/(a) 版本差异未依赖文字描述，全部由行为实测判定。

---

## 八、命令上报（逐条：命令 / 退出码 / 输出摘要）

| # | 命令（全部只读） | 退出码 | 输出摘要 |
|---|---|---|---|
| 1 | `git diff -- skills/.../test_triage_write_guard.py` | 0 | 3 hunk / +63−5 全文；docstring 重写 + `face`/①/②/③ 三判据 + 删旧死断言 |
| 2 | `git diff --stat -- <file>` | 0 | `1 file changed, 63 insertions(+), 5 deletions(-)` —— 与任务描述精确一致 |
| 3 | `git diff --cached --stat -- <file>` / `git status --porcelain -- <file>` | 0 / 0 | 暂存面**空**；工作树状态 ` M` ⇒ 未暂存，无越权暂存 |
| 4 | `python %TEMP%\fix330_r0_verify.py`（自建只读 harness：`git show HEAD:` + skip 注入重建 (a) 版 + `%TEMP%` 副本内 `importlib` 加载 + 进程内 stub + `msvcrt` 独占锁） | 0 | 3 版本 × 4 场景矩阵（§二）；不可读场景三版全红 skip=0；known_replay (a) GREEN / (b) RED；live (b) GREEN |
| 5 | `python -m unittest skills.software-project-governance.infra.tests.test_triage_write_guard` | 0 | `Ran 32 tests in 0.129s` / `OK`（**skipped=0**） |
| 6 | `python -c "import verify_workflow as vw; print(vw._TASK_ID_CELL_RE.pattern); … _plan_tracker_task_row_issues(live)"` | 0 | `^(?:\*\*)?[A-Z]+-\d+(?:\*\*)?$`；`''`/`' '`/`'P0'` → False；live `issues=0 / empty task_ids=0` |
| 7 | `git show HEAD:<file>`（经 harness，rc 与字节数打印） | 0 | rc=0 / 32818 bytes；锚点 `flagged = {…}` + `assertTrue(flagged.issubset…` **逐字存在** ⇒ (a) 版重建基准可信 |

> 未执行任何写操作；未执行 `git add/commit/restore/reset/checkout/stash`；未访问 `$env:USERPROFILE\.dsh`、`$HOME/.dsh` 或仓库外既有资产（唯一仓库外写入 = `%TEMP%` 下的验证 harness 及其副本，与被审面无关）。被审文件与历史报告 `review-FIX-328-CODE-R0.md` **均未修改**（`git diff --stat` 恒为 63/5 为该实证）。

---

## 九、需 Coordinator 处置的转出项

| # | 转出项 | 级别 | 归属 / 建议 |
|---|---|---|---|
| 1 | **历史报告 F-1 前提更正登记**——`docs/reviews/review-FIX-328-CODE-R0.md` 的 F-1 前提与结论（"真实测试灵敏度回退"）经实测证伪，报告不得修改 | **P2** | **Coordinator 记账**。`DEC-194` 已载"事实更正"段、`plan-tracker.md:100` FIX-332 已承接；建议登记文本引用本报告 §二矩阵（不可读场景 HEAD/(a)/(b) 三版 `fail=1 skip=0`）为更正依据，并把 F-1 的**最终定性**固定为"诊断失真（`{''}` 不指向不可读）"，同时**保留 R0 动机层面的价值认定**（暴露了 status 面无断言缺口，本 diff ① 已收口）。不阻断本审查 |
| 2 | **过期测试/文档数据资产**——`env_failure_classification.json:123-130`（`known_defect / test_assertion_stale`，evidence 引用已删除的 HEAD 断言）、`test-baseline-0.80.0.md:111`、`env-failure-classification-0.80.0.md:87` | **P2** | **FIX-332**（已登记，0.81.0 或后续，不阻断）。**范围重核建议**：`release-checklist-0.81.0.md:83` **已同步更新**（实测已被 Coordinator 改写为"经 FIX-330 收口…`OK` 且 `skipped=0`"），应从 FIX-332 的"4 处"清单中核减或标注为已处置；余下应为 JSON + 2 份 requirements 文档 + 历史报告登记 |
| 3 | **守卫 `UnicodeDecodeError` 逸出边界**——`verify_workflow.py:22415` 仅捕 `(IOError, OSError)`，非 UTF-8 活体文件时 `UnicodeDecodeError` 逸出，与 "Never raises" docstring 不符 | **P2** | **FIX-333**（已登记，既有边界、非本批引入，不阻断）。**审查侧补充事实**：该异常在测试面表现为 unittest **ERROR**（红相），**不会**被 FIX-330 的三判据静默吞掉；且本测试**不能**在不改动产品代码的前提下捕获它（超出测试面） |
| 4 | **① 的哨兵耦合（可选加码）**——见 §六 F-1 | **P3** | 无需 action。若后续有"测试须钉住产品 status 字段"的系统性口径，应由新任务统一处理（含 evidence_log / agent_locks / execution_packets 三面的 status 断言现状一并评估），不在本 diff 加"半覆盖"行 |
| 5 | **docstring 精度（互不遮蔽措辞、行号引用）**——见 §六 F-3 / F-4 | **P3** | 无 action；若做 FIX-332 时顺带润色更佳 |

---

## 十、结论

**APPROVED_WITH_NOTES —— `unresolved_blockers=0`**

- **FIX-328/R0 F-1「真实灵敏度回退」前提：证伪成立**（§二）。决定性证据 = 我自建的反相矩阵：不可读场景（`msvcrt` 独占锁真实生效，`is_file()=True` + `read_text` 抛 `PermissionError`）下 **HEAD 版与 FIX-328(a) 版均 `fail=1`、`skip=0`**，traceback 逐字为 `AssertionError: False is not true : {''}`——即 **skip 分支在该场景不可达**。真实缺陷应定名为**诊断失真**（`{''}` 不指向"不可读"），FIX-330 以 ① 收口正确。
- **(b) 方案采纳正确且与授权候选逐字一致**（`test-baseline-0.80.0.md:111`）；**灵敏度增益经独立复核成立**：已知 M1 行（FIX-279）重现场景 (a) 版 GREEN、(b) 版 RED。
- **① 形态的偏离（哨兵 `assertNotIn("", flagged, face)` 取代 `assertEqual(status,"PASS")`）有据、不弱化防护**；其披露的残留边界（`status=FAIL 且 issues=[]`）在现契约**不可达**、功能性后果为零，**可接受**，本轮**不要求加码**。
- **三判据各覆盖独立场景、无恒真断言**（①/②/③ 均实测可红且非"可达即恒真"）；死断言（F-3）已删除。
- **docstring 各条声明（归档 L131-133 字面任务行、index L391-393 定位、FIX-279↔FIX-293/EVD-963、合成用例钉命中能力、改名牵动面、术语边界）逐条可复核且成立**；仅 2 处措辞精度（P3，不阻塞）。
- **AI 专项 5 项全部通过**；**F-5 测试名保留可接受**（欠声称 + 显式披露，非过度声称）。
- 硬门槛全部通过；**P0 = 0、P1 = 0**；F-1/F-3/F-4 为 P3、F-2 为 P2 转出项，均**不阻塞**，且 F-2 已由 FIX-332 / DEC-194 承接。

**返回给 Coordinator**：`APPROVED_WITH_NOTES`（`unresolved_blockers=0`），报告路径 `docs/reviews/review-FIX-330-CODE-R0.md`。
