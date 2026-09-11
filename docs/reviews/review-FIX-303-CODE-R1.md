# Code Review: FIX-303-R1 — NF-1 / NF-2 提交前微补增量（复审）

- **Task**: FIX-303（**R1 复审**——同一 Reviewer，前轮 = `docs/reviews/review-FIX-303-CODE-R0.md`）
- **Reviewer**: Code Reviewer Agent（只读审查；不修改产品代码、不与用户交互）
- **Round**: **R1**（前轮 R0 = `review-FIX-303-CODE-R0.md`，终态 `APPROVED_WITH_NOTES` / `unresolved_blockers=0`，`P0=0 / P1=1 / P2=0 / P3=4`）
- **前轮引用**：R0 报告已**逐条重读**（266 行，内容与本 Reviewer 前轮输出一致，无第三方改动）；R0 的五条发现编号沿用：**NF-1（P1，本轮修复对象）/ NF-2（P3，本轮修复对象）/ NF-3 / NF-4 / NF-5（P3，本轮声明未动）**。
- **审查对象**: **工作树 diff（路径限定 4 文件）**——R1 增量（前置于提交）
  ```
  git diff -- skills/software-project-governance/infra/contracts.py \
              skills/software-project-governance/infra/tests/test_contracts.py \
              skills/software-project-governance/infra/archguard_ratchet.py \
              skills/software-project-governance/core/architecture-baseline.json
  ```
  实测 `git diff --stat` = **4 files changed, 442 insertions(+), 63 deletions(-)** —— 与声明恒等。
  **R1 与 R0 的差量（本审查逐处比对得出，非采信）**：`contracts.py` +45 行 / `test_contracts.py` +34 行 / `archguard_ratchet.py` 与 `architecture-baseline.json` 行数不变（仅 note 文本改写）⇒ 增量 = **81 插入 / 2 删除**，全部落在：①`contracts.py` 的 `_LEGACY_DISCLOSURE_KEYS` + `_require_no_reserved_disclosure_keys` + `to_legacy_dict` 一行调用 + 三处措辞（模块 caliber 2 / 类 docstring / 方法 docstring）；②`test_contracts.py` 的 2 条新测试；③两处 NF-2 note 文案。
- **R0 blob 不可 diff 的处置（方法披露）**：R0 状态未提交，其 blob（`23a7cc7c…` 等）**不在 git 对象库**（`git cat-file -t` 实测报错）⇒ 无法用 `git diff <R0> <R1>` 求增量。本审查改用：**逐处比对「当前 diff 全文」与「R0 已审 diff 全文」**（R0 diff 在本 Reviewer 前轮上下文与 R0 报告 §六/§五 中逐字留存），并辅以行数/语句数算术交叉验证（见 §三 表注）。
- **审查边界**：工作树现仅本批 4 文件被修改（`git status --porcelain` 实测；R0 期间在飞的 FIX-304 面已随其提交落库，`registry.py`/`test_registry.py` 已不在工作树）⇒ **本轮零并行改动混杂**，全部核验命令结果可**单独归因于本批**。
- 破坏性红线**不适用**：全程只读；唯一写入 = 本报告；coverage 数据文件按 `COVERAGE_FILE` 重定向 `$TEMP` 并同命令内删除。

---

## 一、冻结锚核对（fail-fast，先于一切审查）

| 文件 | 声明锚值（R1） | 实测 `git hash-object` | 字节数 | 行数 |
|---|---|---|---|---|
| `infra/contracts.py` | `b6bd78688f0c5e8f5b73a41a51178d51aeaf3c57` | `b6bd78688f0c5e8f5b73a41a51178d51aeaf3c57` ✅ | 24,654 | **573** ✅ |
| `infra/tests/test_contracts.py` | `4f4c33b032d105c7b2b716c70bd58cfe627deaaf` | `4f4c33b032d105c7b2b716c70bd58cfe627deaaf` ✅ | 46,826 | **1050** ✅（`def test_`=99 ✅） |
| `infra/archguard_ratchet.py` | `a1b318fdab19dafa7962b818ff70526b1fdf49da` | `a1b318fdab19dafa7962b818ff70526b1fdf49da` ✅ | 49,405 | **1122** ✅ |
| `core/architecture-baseline.json` | `d0990a499cdd340f88030c2f34ef7b9f7176a37f` | `d0990a499cdd340f88030c2f34ef7b9f7176a37f` ✅ | 14,495 | 552 ✅ |

**4/4 命中，无漂移**（口径同 R0：锚值 = git blob SHA1；本轮实测字节数与声明行数亦逐项一致）。`architecture-baseline.json` 的 `generated.git_head` = `70773da4cd5c27fa3b51df2de7084b11a46402ae`——`git cat-file -t` 实测该哈希**在库中为 commit**（真实提交，非臆造），且该字段经 R7 **剥离**后参与双真判定（见 §三），与前轮一致。

---

## 二、前轮发现逐条比对（已修复 / 未修复 / 新引入）

| 前轮 ID | 级别 | R1 处置落点 | 独立核验 | 裁决 |
|---|---|---|---|---|
| **NF-1**（`details` 通道可产出「FAIL 被披露为 SKIP」的矛盾面 + docstring 措辞超实现） | P1 | `contracts.py`:279-307（新增 `_LEGACY_DISCLOSURE_KEYS` 保留键表 + `_require_no_reserved_disclosure_keys`）；L403-404 调用；L414-419（方法 docstring）；L330-334（类 docstring）；L58-63（模块 caliber 2）；`test_contracts.py`:744-770（2 条新测试） | 见 §三 A（4 组实测）+ §四（选型裁决） | ✅ **已修复**（拒绝式选型经裁决**成立且必要**，措辞超实现已消除） |
| **NF-2**（同一 diff 内两处 note 仍指向已关闭的 `REFACTOR-contract-layer`） | P3 | `archguard_ratchet.py`:110-112 与 `core/architecture-baseline.json` → `r3_layer_matrix.managed_modules["infra/archguard_ratchet.py"].note`：改 "unmanaged until **its own slice - owner task FIX-303, F-6 transfer**"；`infra/contracts.py` 条目 note 末句（两处）同步 | 见 §三 B | ✅ **已修复** |
| **NF-3**（F-2 引擎口径 pin 为手写复刻，与引擎无机判绑定） | P3 | **未动**（`test_contracts.py` 的 `engine_loop` 与其 docstring 与 R0 逐字相同） | 由 R1 diff 逐处比对确认无改动 | ⚠ **未修复（如实声明，非本轮义务）** |
| **NF-4**（py39 启发式欠达面未在 docstring 披露） | P3 | **未动**（`_looks_like_type_union` 与 `_TYPE_LIKE_NAMES` 与 R0 逐字相同） | 同上 | ⚠ **未修复（如实声明）** |
| **NF-5**（覆盖率口径未在仓内 pin） | P3 | **未动**（`pyproject.toml` 不在 `git status` 修改列表 ⇒ 无 `[tool.coverage]` 新增；无 `.coveragerc`/`setup.cfg`/`tox.ini`） | `git status --porcelain` 实测仅 4 文件 | ⚠ **未修复（如实声明）** |
| **新引入问题** | — | **无阻塞级新问题**；1 条 P3（R1-N1，见 §五） | §五 | — |

**R0 已闭环处置未回归（回归核对）**：F-1~F-13 的全部落点在本轮 diff 中**逐字保留**（caliber 1/3、loader 三处文案、`_require_skip_consistent`、F-7~F-13 各测试与 characterization），R1 仅**追加**；`test_contracts.py` 97→99 例全绿 ⇒ R0 处置**无回归** ✅。

---

## 三、独立核验结果（本轮实际执行的只读命令）

| # | 核验项 | 命令 | 实测结果 | 与声明比对 |
|---|---|---|---|---|
| 1 | 目标测试套件 | `python -m unittest discover -s skills/.../infra/tests -p "test_contracts.py"` | `Ran 99 tests ... OK`，exit 0；`def test_` 实测 = **99** | ✅ 99/99 属实 |
| 2 | 架构棘轮 | `python skills/.../infra/verify_workflow.py archguard-ratchet` | `Result: PASS (0 violations)`；R1 `24329 ≤ 24329`；R2 `46 ≤ 46`；**R3 `managed 2 modules, 0 edges, SCC max 1`**；R4 `1310 ≤ 1310`；R5 `82/82, 70/70`；**R7 `deterministic=True; committed==fresh True`** | ✅ R3 managed 2 / R7 双真 属实 |
| 3 | 契约矩阵差分 | `python skills/.../infra/contract_matrix/generator.py --check` | `4 faces, zero drift`，exit 0 | ✅ |
| 4 | 清单一致性 | `... verify_workflow.py check-manifest-consistency` | `Canonical 648 / Actual 721 / [PASS]`，exit 0 | ✅ |
| 5 | 覆盖率 | `COVERAGE_FILE=$TEMP python -m coverage run -m unittest ...` → `report --include="*contracts.py"` | `contracts.py  **172**  0  100%` | ✅ 172 stmts / 0 miss 属实 |
| 6 | **全量套件** | `python -m unittest discover -s skills/.../infra/tests -p "test_*.py"` | **`Ran 2592 tests in 748.460s` / `FAILED (failures=32, errors=1, skipped=1)`** | ⚠ **测试总数 2592 恒等 ✅**；**非通过总数 33 = 31+2 ✅**；**F/E 分类与声明不同**（声明 31F+2E，实测 32F+1E）——差异**恰为 1 项**且该 1 项为负载敏感项，见 §3.C |
| 7 | 分类翻转归因（抽验） | ①孤立复跑 `-p "test_loop_runtime_claims.py"`；②扫描器 findings 按路径聚合 | ①`Ran 52 tests in 125.320s` / `FAILED (failures=2)` ⇒ **孤立态 = FAIL（存量模态），非 ERROR**；②`verdict: BLOCKED | findings: 4`——`.governance/decision-log.md` ×1（`AUTHORITY_SOURCE_OCCURRENCE` found 0）+ `docs/reviews/review-FIX-300-CODE-R0.md` ×3（`UNSUPPORTED_AFFIRMATIVE`）；**引 FIX-303 的 findings = 0**、**落在本批 4 文件的 findings = 0** | ✅ **开发者归因成立**（详见 §3.C） |
| 8 | 增量语句数算术（覆盖率口径佐证） | 比对 R0/R1 覆盖率与 diff | R0 `164` → R1 `172` = **+8**；diff 增量语句恰为：模块级 `_LEGACY_DISCLOSURE_KEYS = (...)`(1) + 新函数体 `def`/`if … is not None:`/`return`/`carried = [...]`/`if carried:`/`_fail(...)`(6) + `to_legacy_dict` 新增调用行(1) = **8** ⇒ 逐步自洽 | ✅ 数字与代码增量自洽（无隐藏语句来源） |
| 9 | 范围核查 | `git status --porcelain` + 路径限定 diff | 工作树**仅本批 4 文件**被修改（FIX-304 面已落库，无混杂） | ✅ 无范围外改动 |

### 3.A NF-1 修复有效性（四组实测，全部由本审查独立构造并执行）

| 场景 | 实测结果 | 判定 |
|---|---|---|
| R0 原始复现：`CheckResult(passed=False, details={"skipped": True, "skip_reason": "injected"})` → `to_legacy_dict()` | `ContractViolation`：`… details carries the adapter-owned disclosure key(s) ['skipped', 'skip_reason'] while skipped is None — … set CheckResult.skipped to disclose a skip, or drop the keys from details` | ✅ **R0 复现路径已关闭**（且消息给出可执行的两条出路） |
| 两个 stale 态（`{"skipped": False}` / 仅有 `{"skip_reason": "…"}`） | 两者**均**抛 `ContractViolation`（列出实际携带的键） | ✅ 与声明"注入 + 两 stale 态"一致；**单独携带 `skip_reason` 亦被拒**（覆盖更严，见 §四） |
| 回归 pin：`skipped="fresh reason"` + 陈旧 `details` | `{'skipped': False,'skip_reason':'stale reason'}` → `{'skipped': True,'skip_reason':'fresh reason'}`；`{'skipped': True,'skip_reason':'old'}` → 同上 | ✅ **覆盖式规范化保留**，无回归 |
| 误报面：自由形态 `details` | `{"records_checked": 3}` ✅ 放行；`{"sub": {"skipped": True, "skip_reason": "…"}}`（**嵌套**）✅ 放行、键面不变；`{}` ✅ 放行；`{"skipped": None}` ❌ 拒绝 | ✅ 保留键仅限 **`details` 顶层**，嵌套与其它键完全自由（docstring 声明与实现一致） |

### 3.B NF-2 核验

- **机判等值**：`archguard_ratchet.DEFAULT_MANAGED_MODULES == baseline["r3_layer_matrix"]["managed_modules"]` 实测 **True**（两键集一致，逐条目 `identical=True`）⇒ 声明"DEFAULT_MANAGED_MODULES==baseline.managed_modules 机判 True"**属实**。
- **R7 双真**：`deterministic=True; committed==fresh True`（= 提交态 == 重生成态，note 改写经 regen 同步，无手编漂移）。
- **陈旧引用残留**：`archguard_ratchet.py` 中 `REFACTOR-contract-layer` 出现 **1 次**（L129，`_OWNER_TASK_MAP` 上方注释："FEAT-021 / REFACTOR-contract-layer closed without consuming … so the debt would otherwise lose its owner on task closure"）——属**历史性说明**（解释为何转记），非"未来承认方"的错误表述 ⇒ **不构成残留缺陷**；`architecture-baseline.json` 中该串出现 **0 次** ✅。

### 3.C 全量套件的分类翻转归因（抽验结论）

Developer 声明"31F+2E+1S（LoopRuntimeClaim FAIL→ERROR=15s 预算越界，孤立复跑回 FAIL 存量模态，判负载触发）"，本审查独立抽验：

1. **测试总数 2592 恒等** ✅，**非通过总数 33 恒等** ✅，`skipped=1` 恒等 ✅ —— 声明与实测在**规模面完全一致**；差异仅为 F/E 标签（声明 31F+2E / 实测 32F+1E）。
2. **孤立复跑（无并发负载）模态 = FAIL**：`test_loop_runtime_claims.py` 单独运行 = `Ran 52 tests in 125.320s` / `FAILED (failures=2)`，两条均为**断言失败**（`test_real_repository_inventory_complete_and_within_budget`：`'PASS' != 'BLOCKED'`；`test_three_run_performance_identity_and_median` 同源）——**不是 ERROR/超时**。⇒ 该文件在无负载下是 **FAIL 存量模态**，与 Developer 的"孤立复跑回 FAIL"**一致**。
3. **根因与 FIX-303 无关（决定性证据）**：该测试扫描**真实仓库**（`_real_repository_roots()`），其 `verdict=BLOCKED` 仅由 **4 条** finding 造成——`.governance/decision-log.md` ×1（`AUTHORITY_SOURCE_OCCURRENCE` found 0）、`docs/reviews/review-FIX-300-CODE-R0.md` ×3（`UNSUPPORTED_AFFIRMATIVE`）。**引用 FIX-303 的 findings = 0；落在本批 4 文件的 findings = 0** ⇒ 该失败为**存量、内容驱动、与本批零关联**；且**本 Reviewer 的 R0 报告同样未产生任何 finding**（`review-FIX-303-CODE-R0.md` 不在聚合结果中）。
4. **结论**：分类翻转属同一**负载敏感的存量失败**在"断言失败 ↔ 预算/错误"两种模态间的摆动（该文件含 125s 级三跑性能断言，与 `15s 预算` 量级同族的时限敏感面）；**Developer 的归因成立**，且**不构成 FIX-303 的回归**。R1 判定**不因此降级**（该失败在 R0 前的仓库状态下即存在，其触发文件与本批无关）。

---

## 四、NF-1 拒绝式选型裁决（Coordinator 指定裁决项）

**选型：`skipped` 已设置 → 覆盖式规范化（保留原行为）；`skipped is None` 且 `details` 顶层携带保留键 → `ContractViolation` 拒绝（而非静默清除）。本审查裁决：成立、正确、且比"仅按真值拒绝"更必要。**

1. **与模块自身口径一致（拒绝优于静默清除）**：`contracts.py` 模块 docstring 第 3 段明文「Construction is fail-closed (§3.7 step 2) … **Nothing is coerced silently**」。静默清除 `details` 中的调用方数据 = 静默丢弃调用方提交的载荷，与该口径直接冲突；拒绝式让调用方自己决定（消息给出两条出路："set `CheckResult.skipped` … or drop the keys from `details`"）⇒ **选型与模块哲学自洽**。
2. **必须按"键存在"而非"键真值"拒绝（决定性论证，本审查独立实测）**：本批 R0 新 pin 的聚合约定以**键存在**派生 label 块——
   `label_block["skipped"] = "skipped" in legacy["details"]`（`test_contracts.py`:592-596）。实测两种注入：
   - `details["skipped"]=True` → `label_block["skipped"]=True` → 引擎视图 `[('the_label','SKIP','x')]`
   - `details["skipped"]=**False**` → `label_block["skipped"]=**True**` → 引擎视图**同样** `[('the_label','SKIP','x')]`
   ⇒ 在既定约定下，**任何**顶层 `skipped` 键（含 `False`/`None`）都会被提升为"已跳过"。若实现改用"仅当真值才拒绝"，`details={"skipped": False}` 仍可穿透并把 FAIL 披露为 SKIP ⇒ **现值存在键的拒绝规则是必要的，而非过度严格**（实测亦证 `{"skipped": None}` 被拒）。这一条同时回答了"拒绝式是否误伤"：被拒的恰是**会被误读**的形态。
3. **实现正确性**：`_require_no_reserved_disclosure_keys(where, details, skipped)` 在 `_require_skip_consistent` 之后、构造 legacy 面之前调用（L403-404）⇒ 不可能产出矛盾面；`carried = [key for key in _LEGACY_DISCLOSURE_KEYS if key in details]` 对两键**独立**判定（单独 `skip_reason` 亦被拒，覆盖更严）；早退分支 `if skipped is not None: return` 保证"记录跳过 → 覆盖规范化"旧口径不变（回归 pin 实测通过）。**无 KeyError/类型面风险**（`in` 对任意键型安全）。
4. **措辞超实现已消除**：类 docstring 现为"re-validates every field it serializes — passed/findings/skipped/details, **the skip invariant, and the adapter-owned disclosure keys inside `details`**"；方法 docstring 补"a recorded skip overwrites it from the typed object, and a caller-supplied pair with no recorded skip is refused rather than forwarded (NF-1)"；模块 caliber 2 补"adapter-owned … so the `details` channel cannot re-introduce the FAIL-disclosed-as-SKIP face"。三处断言与实测行为**逐条对齐** ⇒ **R0 的"措辞超实现"已消除**（残余范围限定见 R1-N1）。

---

## 五、R1 发现清单

| # | 级别 | 位置 | 问题与影响 | 事实依据 | 建议 |
|---|---|---|---|---|---|
| **R1-N1** | P3 | `contracts.py`:58-63（模块 caliber 2 断言范围）、L279-307（保留键规则的**执行层**） | 保留键规则在 **adapter 层**执行：构造期与**直接读 `CheckResult.details` 的消费方**不受其覆盖。实测：`CheckResult(passed=False, details={"skipped": True})` **构造成功**（对象可处于矛盾态），仅 `to_legacy_dict()` 拒绝。影响面：只对"绕过适配器、直接读 typed 对象 `details`"的切片成立——而本批 pin 的聚合约定是从**适配器输出**提升键（`legacy["details"]`）⇒ 文档路径安全；但 caliber 2 的断言"the `details` channel cannot re-introduce the FAIL-disclosed-as-SKIP face"未限定"经适配器"，直接读者可能被读作已受保护 | ① 实测：注入构造**不抛**、适配抛 ② 实测：嵌套 `details={"sub":{"skipped":True}}` 放行（保留键仅顶层） ③ pin 约定从 `legacy["details"]` 提升（`test_contracts.py`:592-596） | 一行范围限定即可：在 caliber 2 或 `_require_no_reserved_disclosure_keys` docstring 注明"保留键在**适配器输出面**强制执行；直接消费 `CheckResult.details` 的切片不受此保护，MUST 走 `to_legacy_dict()`"。**不要求**改代码行为（构造期加固会与"构造期 details 自由形态"及变异逃逸口并存，属可选加固） |
| **R1-N2** | P3 | 见 §二 表 | **NF-3 / NF-4 / NF-5 三条 R0 P3 仍未处置**（本轮如实声明未动，非本轮义务，无回归） | 逐处 diff 比对 + `pyproject.toml` 未修改 | 随跟踪表继续挂账；NF-3 建议在"把 CheckResult 接入 L4/registry 聚合"切片**之前**处理（该切片会依赖被 pin 的引擎口径） |

**汇总：P0 = 0 / P1 = 0 / P2 = 0 / P3 = 2（R1-N1 新增；R1-N2 = 前轮 3 条 P3 的如实挂账）。无 BLOCKING 发现。**

---

## 六、5 个评审维度逐项结论（针对 R1 增量）

| 维度 | 结论 | 依据 |
|---|---|---|
| **1 正确性** | **通过**（R0 的 P1 已闭环） | 新增守卫位置正确（不变式断言之后、legacy 面构造之前）、早退分支保持旧规范化口径、两键独立判定、键存在判定经实测为**必要**（§四·2）；R0 全部落点逐字保留、无回归；99/99 绿 |
| **2 安全性** | **通过** | 零新增 import/零 I/O/零正则（守卫仅做键成员判定）；`__all__` 未变，新增符号为私有常量（`_LEGACY_DISCLOSURE_KEYS`）；fail-closed 方向正确（拒绝而非透传）；模块体仍仅声明（AST 机判绿） |
| **3 可维护性** | **通过**（含 1 条 P3 范围限定） | 保留键集中为单一名表 `_LEGACY_DISCLOSURE_KEYS`（消除字面量散落）；新函数 6 行、docstring 说明"为何拒绝而非清除"并给调用方两条出路；三处文案与实现对齐；R1-N1 仅为断言范围限定 |
| **4 性能** | **通过** | 增量 = 1 次 2 键成员判定（O(1)）+ 1 次模块级常量构造；每 result 调用 1 次；覆盖率语句 +8 与增量逐条对应（§三 表注 8）⇒ 无隐藏成本、无循环 |
| **5 测试覆盖** | **通过**（含 R1-N2 挂账） | 99/99（新增 2 例：注入+两 stale 态负对照；记录跳过→覆盖规范化回归 pin）；**新负对照有牙**：R0 状态下无该守卫（R0 diff 中 `to_legacy_dict` 无此行调用）⇒ 该断言改前必红，与 Developer"修前 failures=1 → 修后 99/99"一致；断言含 3 个 needle（`adapter-owned`/`skipped`/`skip_reason`），经消息实测命中 ⇒ 非恒真 |

**AI 专项 5 项（R1 增量）**：**mock 残留** 无（新测试仅构造真实对象）；**硬编码返回值** 无（断言依赖真实异常消息 needle，无造值）；**幻觉 API** 无（`in`/列表推导/`Tuple[str, ...]` 均真实）；**未实现 TODO** 无（增量零 `TODO/FIXME/noqa/type: ignore`）；**过度实现** 无（拒绝式严格度经实测判定为**必要**，非过度；`_LEGACY_DISCLOSURE_KEYS` 名表消除重复字面量属收窄）。

---

## 七、范围核查（无新范围）

| 声明 | 实测 | 判定 |
|---|---|---|
| `contracts.py` +45 / `test_contracts.py` +34 / 另 2 文件行数不变（442+/63−） | `git hash-object`+行数+`--stat` 三项一致 | ✅ |
| 增量仅可追溯 NF-1 / NF-2 | 增量 100% 落在 §二 表 NF-1/NF-2 落点；无其它 hunk | ✅ **无未授权扩面** |
| NF-3 / NF-4 / NF-5 未动 | 三处代码逐字同 R0；`pyproject.toml` 未在 `git status` 列表 | ✅ |
| 无范围外文件 | 工作树仅 4 文件（FIX-304 面已落库） | ✅ |

---

## 八、硬门槛裁决

| 门槛 | 结果 |
|------|------|
| 冻结锚核对 | ✅ 4/4 命中（blob + 字节数 + 行数三重一致） |
| 逐行读 R1 增量 + 受影响文件 | ✅ 增量 81+/2− 逐行；`contracts.py` 573 行全文重读（新增段逐行）；2 条新测试逐行；ratchet/baseline note 逐行 |
| 前轮发现逐条比对（已修复/未修复/新引入） | ✅ 5 条逐条裁决（NF-1/NF-2 已修复；NF-3/4/5 未修复如实声明；无新引入阻塞项） |
| P0 阻塞问题数 = 0 | ✅ 0 |
| 5 维度全覆盖 = 100% | ✅ §六 逐项 |
| 每条发现标注级别 = 100% | ✅ R1-N1/R1-N2 标注 P3 + 位置 + 事实依据 + 建议 |
| 设计一致性检查 | ✅ 与 §3.7 键集（三点未变）、模块 fail-closed 口径、FIX-270 WARN 语义、pin 聚合约定逐项对齐 |
| AI 专项 5 项 | ✅ §六 末段逐项 |
| 机判门禁独立复跑 | ✅ 99/99；ratchet PASS（R3 managed 2 / R7 双真）；matrix 零漂移；manifest PASS；覆盖率 172/0=100%；全量 2592（非通过 33） |
| 审查边界约束 | ✅ 只读；唯一写入 = 本报告；coverage 数据文件重定向 `$TEMP` 并删除 |

---

## 九、审查结论

# APPROVED_WITH_NOTES

unresolved_blockers=0

**P0 = 0 / P1 = 0 / P2 = 0 / P3 = 2（R1-N1 新增 + R1-N2 前轮 3 条 P3 挂账）。**

**终态理由**：R0 的两条修复对象**均已闭环并经独立实测**——(1) **NF-1（R0 唯一 P1）已修复**：R0 的矛盾面复现路径现被 `ContractViolation` 拒绝（消息给出两条可执行出路），两个 stale 态同样被拒，而"记录跳过 → 覆盖规范化"的旧口径经回归 pin 保留；嵌套/自由形态 `details` 全部放行 ⇒ 无过度误伤。**拒绝式选型经裁决成立且必要**：模块自身「Nothing is coerced silently」口径排除静默清除；且本批自身 pin 的聚合约定按**键存在**提升（实测 `details["skipped"]=False` 同样被提升为 `skipped=True` ⇒ 引擎读作 SKIP），故"按键存在拒绝"是消除矛盾的**最小必要**规则，而非过度严格；三处措辞（模块 caliber 2 / 类 docstring / 方法 docstring）已与实测行为逐条对齐 ⇒ R0 的"措辞超实现"消除。(2) **NF-2 已修复**：两处 note 文案改写，`DEFAULT_MANAGED_MODULES == baseline.managed_modules` 机判 **True**，R7 `deterministic=True; committed==fresh True`（改写经 regen 同步、无手编漂移）；唯一残留的 `REFACTOR-contract-layer` 出现（ratchet L129）为**历史性说明**，不构成缺陷。

**机判面全部独立复跑一致**：`test_contracts.py` **99/99 OK**；`archguard-ratchet` **PASS / 0 violations**（R3 `managed 2, 0 edges, SCC max 1`；R7 双真；R2 `46 ≤ 46`）；contract matrix **`4 faces, zero drift`**；manifest **PASS**（648/721）；覆盖率 **172 stmts / 0 miss = 100%**（较 R0 的 164 恰 +8，与本轮增量语句数**逐条对应**）。**全量套件 `Ran 2592`（非通过 33 + skipped 1）**——测试总数与声明**恒等**，非通过总数与声明（31F+2E=33）**恒等**；唯一差异为 **F/E 分类标签**（实测 32F+1E vs 声明 31F+2E），抽验证明该差异落在 **1 个负载敏感的存量失败**上：`test_loop_runtime_claims.py` 孤立复跑为 **FAIL 存量模态**（`Ran 52 / FAILED (failures=2)`，125s，非 ERROR），其 `BLOCKED` 仅由 4 条 finding 造成（`docs/reviews/review-FIX-300-CODE-R0.md` ×3 + `.governance/decision-log.md` ×1），**引用 FIX-303 的 findings = 0、落在本批 4 文件的 findings = 0** ⇒ **非本批回归**，Developer 归因成立，不构成降级理由。

**范围**：增量 442+/63− 全部可追溯 NF-1/NF-2，工作树仅本批 4 文件（R0 期间在飞的 FIX-304 面已落库，**无混杂**）；NF-3/NF-4/NF-5 如实声明未动（R1-N2 继续挂账）。

**遗留（均 P3，不阻塞）**：**R1-N1**——保留键规则在**适配器输出面**执行，构造期与"直接读 `CheckResult.details`"的消费方不受覆盖，建议在 caliber 2 加一行范围限定（要求文档级，不要求改行为）；**R1-N2**——NF-3（引擎口径 pin 为手写复刻，与引擎无机判绑定）、NF-4（py39 启发式欠下界未披露）、NF-5（覆盖率口径未在仓内 pin）三条 R0 P3 仍未处置。建议 Coordinator 将 **NF-3 的关闭时限前置到"把 `CheckResult` 接入 L4/registry 聚合"切片之前**（该切片会消费本批 pin 的引擎读取口径）。

**机器记录口径提示**：`unresolved_blockers=0` 独占一行且无附着细目（避免与 FIX-291 provably-zero 探针冲突）；P0/P1/P2/P3 计数写在上一行。

---

## 十、审查边界声明

- 本轮为**只读复审 + 只读命令复跑**：未修改产品代码、未写 `.governance/`、未写除本报告外任何文件；coverage 数据文件经 `COVERAGE_FILE` 重定向 `$TEMP` 并即时删除。
- **R0 blob 不在对象库**，故 R1 增量由"当前 diff 全文 vs R0 已审 diff 全文"逐处比对得出（方法已在报告头披露），并以行数（+45/+34/0/0）、diffstat（442+/63−）、覆盖率语句增量（+8）三重交叉验证。
- **未复现/未独立验证的项（如实披露）**：(a) Developer 所称"修前 `failures=1`"的**原始运行输出**未附；本审查以"R0 状态下该守卫不存在（R0 diff 中 `to_legacy_dict` 无此调用行）"静态推定其改前必红，而非复跑历史状态；(b) **声明中 31F+2E 的 ERROR 模态未复现**——本审查在最接近其"负载触发"描述的两轮运行中均得到 32F+1E（全量）与 2 FAIL（孤立），已如实记为标签差异而非实质差异；(c) 全量套件**逐测试名签名比对**（新增 0/消失 0）未复跑——本批 4 文件的实际覆盖由第 1~5 项路径限定核验锁定，且失败归因已由第 7 项按路径聚合完成。
