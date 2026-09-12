# FIX-319 代码审查报告（Code Review R0）

- **任务**：FIX-319 — Check 18c `allowed_change_scope` 判据把 markdown 粗体当通配符（系统性误报）
- **Round**：0（首次审查；无前轮引用）
- **审查对象**：`skills/software-project-governance/infra/verify_workflow.py`（+47/−1）、`skills/software-project-governance/infra/tests/test_verify_workflow.py`（+69/−0）；实测**未 staged**（`git diff --cached` 为空），diff 以 `git diff HEAD` 取得（与 staged blob 逐字节等价）
- **Reviewer**：Code Reviewer Agent（只读；仓库零写入已实证——收尾 `git status` 仍恰 2 行、两文件 blob 未变）
- **结论**：**APPROVED_WITH_NOTES** / `unresolved_blockers=0`（P0 = 0；P2 × 4；P3 × 2）

---

# 代码审查报告 — FIX-319（Code Review R0）

- **Task ID**: FIX-319
- **轮次**: R0（首次审查，无前轮 findings）
- **审查对象**: 工作树内 2 个修改文件（见 §0.1 索引状态更正）
  - `skills/software-project-governance/infra/verify_workflow.py`（+47 / −1）
  - `skills/software-project-governance/infra/tests/test_verify_workflow.py`（+69 / −0）
- **基线**: HEAD = `3059aae`；diff 取 `git diff HEAD -- <path>`
- **结论**: **APPROVED_WITH_NOTES** / `unresolved_blockers=0`
- **P0 = 0**；P1 = 1（非阻塞，见 F-01 定级说明）；P2 = 3；P3 = 2

---

## 0. 事实基线更正（先于全部结论）

### 0.1 索引状态：2 个文件**未 staged**

任务书称「审查对象 = 当前索引（staged）中的 2 个文件」。实测相反：

```
$ git diff --cached --name-only          → （空，exit 0）
$ git status --porcelain                 →  M skills/.../verify_workflow.py
                                           M skills/.../tests/test_verify_workflow.py
$ git diff HEAD --stat                   → 2 files changed, 115 insertions(+), 1 deletion(-)
```

- 两文件 blob 与索引一致、与 HEAD 不同 ⇒ **索引 = HEAD，改动全在工作树**。
- 因此本审查改用 `git diff HEAD`；**diff 内容与 staged 判据逐字节等价**（同一对 blob），审查效力不受影响。
- 附带事实：`.governance/**` 已被 gitignore（`git status` 全量输出恰 2 行），故 Check 18c 读到的仍是**上一版** packet 文件。

### 0.2 范围纪律：`git status --porcelain` 恰 2 行，仓库根 scratch 残留 = 0

---

## 1. 独立复现结论（全部为本 Reviewer 自行执行，非采信自述）

| # | 复现项 | 方法 | 结果 |
|---|--------|------|------|
| R-1 | 判据层 3/3 误报消除 | AST 从仓库源抽取 `_is_too_broad_scope_text` 等 4 个符号（不 import 全模块），以 `.governance/execution-packets.json` **真实串**驱动 old/new 双判据 | OLD 误报 `['FIX-315','FEAT-031','FIX-317']` → NEW `[]`；7/7 packet 中改动只影响这 3 条，其余 4 条两版同判 ✅ |
| R-2 | ≥8 条宽范围反证 | 自建 47 条向量矩阵（含 9 条任务书指定 + 自创诱饵）+ 28 条对抗诱饵 | 任务书指定 9 条**全部仍 FAIL**；`*.md and **bold**`、`**bold** and src/*`、`**all files** and **whole repo**`、`build/**`、`assets/**`、`docs/**`、`/ **`、`****`、`***` 全部 FAIL ✅ |
| R-3 | 粗体正例 | 3 条真实 packet 串 + 3 条合成正例 | 全部 PASS ✅（含 `a**b**c`） |
| R-4 | 放宽面穷举扫描 | 字母表 `{*,a,f,s,空格,all files,any file,whole repo,install}` 的 r≤3 全笛卡尔积，筛 **OLD=FAIL ∧ NEW=PASS** | 命中 192 条，**分类后 0 条无法解释**：168 条属「短语无词首边界」（`aall files`/`installall files`/`xall files` 类，均为误报消除）；24 条属「成对粗体被中和」。**无任何由粗体剥离新引入的放宽**（数学上亦不可能：删字符无法创造新子串）✅ |
| R-5 | 子集测试计数 | `unittest discover -k ExecutionPacket`（`DSH_HOME` 重定向至 `%TEMP%`） | **Ran 15 tests / OK** ✅（与自述一致） |
| R-6 | 新增测试覆盖 | `coverage --branch`，`-k test_scope`，独立 data-file | `verify_workflow.py` L12708/12715/12718/12726/12729/12736-12739/12742-12750 **全 EXEC**；L12690–12760 区间 `missing_branches` **仅含 12744/12746/12752/12754/12757**——即 `_validate_execution_packet` 的**既有**分支，**新增判据零未覆盖分支**；4 条新测试对新增逻辑达**行 100% + 分支 100%** ✅ |
| R-7 | Check 18c 真实作用域 | 进程内调用 `_active_execution_packet_tasks()` + `check_execution_packets()` | 活跃集 = `REL-077, FEAT-031, FEAT-023, FEAT-024, FEAT-026, FEAT-027`（6 条，**FIX-315/FIX-317 已不在集内**）；`check_execution_packets().pass = False`，`FEAT-031 → PASS`，仅 `REL-077` 仍 FAIL（`missing execution packet`，与本品无关）✅ |
| R-8 | issue 数变化 | `check-governance --summary-only` | **86 issues**（非自述 90 / 非任务书 93）：`10 / 16 / 17×3`。数值差异见 §5 偏离-1 判定 |
| R-9 | 3 个存量失败归因复核 | ① `git archive HEAD` → `%TEMP%` 取**无 FIX-319 的 HEAD 源**；② `PYTHONPATH` 接管 `sys.path[0]` 后跑同一测试类 | **HEAD 源与 FIX-319 源失败签名逐字相同**：`FAILED (failures=1, errors=1)`，同一 2 个测试、同一 `AssertionError: 'PASS' != 'BLOCKED'`、同一 `SystemExit: 1`。⇒ 该失败**与 FIX-319 零因果** ✅ |
| R-10 | 残余 BLOCKED 真源 | 进程内调 `scan_loop_runtime_claims(_loop_runtime_claim_context('installed_host'))` | `verdict = BLOCKED`，`findings` **恰 3 条**，`code=UNSUPPORTED_AFFIRMATIVE`，`normalized_path` **3/3 = `docs/reviews/review-FIX-300-CODE-R0.md`**，`claim_id=LRC-ACTIVE-RUNTIME` ⇒ 与 Coordinator 归因**完全一致** ✅ |
| R-11 | FIX-320 登记 | `grep` `.governance/*.md` | `plan-tracker.md:92`（P2，明示「已登记 FIX-320…本版处置 = (c)」）+ `evidence-log.md:2038`（EVD-1018）⇒ **登记成立** ✅ |
| R-12 | 突变测试（自有反相推演） | 抽取层构造 5 个变体 | 见 §4.4。**M1（换回旧子串判据）被 2 条测试抓回；M2（去词首锚）被抓回；M3/M4 变体抓到 0 条** |
| R-13 | 性能 / 灾难性回溯 | 5 组病态输入（`'**a'*10000`、`'*'*5000`、`'**'*2000`、`'a*'*20000`、`'**b**'*10000`） | 最差 **1.9 ms**（50 KB），无回溯爆炸 ✅ |
| R-14 | 真实环境防护 | 全部写操作限于 `%TEMP%\fix319_review\**`（脚本/probe/突变副本/coverage data）；仓库路径**零写入** | ✅ |

---

## 2. 硬门槛裁决表

| 门槛项 | 阈值 | 实测 | 裁决 |
|--------|------|------|------|
| P0 阻塞问题数 | = 0 | **0** | ✅ 通过 |
| 5 维度全覆盖 | 100% | 正确性/安全性/可维护性/性能/测试覆盖 逐一有结论（§4） | ✅ 通过 |
| 每条发现标注级别 | 100% | F-01 ~ F-06 全部带 P0~P3 | ✅ 通过 |
| 判据语义一致性检查（代设计一致性） | 已完成 | §4.1（与 Check 18c 既有语义 + 生成器 scope 文本形态双向比对） | ✅ 完成 |
| AI 代码专项 5 项 | 全部完成 | §4.5 五项逐一有结论 | ✅ 完成 |

---

## 3. Findings

| # | 级别 | 位置 | 事实 | 影响 | 建议 |
|---|------|------|------|------|------|
| **F-01** | **P2** | `verify_workflow.py:12708`（`_MARKDOWN_BOLD_SPAN_RE`）+ `:12737-12738` | 该正则以「2 个星号 + 内部不含星号 + 2 个星号」配对，**不校验两侧星号是否为真正的 run 边界**。故 **glob 串 `**/tests/**` 落入 span 内 → 整串被替换为 ` /tests/ ` → 无可残留 `*` → 判定 PASS**。实测：`**/tests/**` NEW=PASS、OLD=FAIL；而 `**/*.py` NEW=FAIL（`/` 使 `[^*]+?` 匹配到 `*` 前即失败）。**同一 `**…/**` glob 族内部不一致**——`**/*.py` 被拦、`**/tests/**` 被放行。`:12732-12734` docstring 自述「A *surviving* `*` is a genuine wildcard … stripping must never launder it」在此**未被满足**，`**/*.py` 的 FAIL 属**巧合**而非机制保证。 | 相对 HEAD 的一处**真实（且非任务书类别的）判据放宽**：形如 `**/tests/**` 的 glob scope 从 FAIL 变 PASS。定级 P2 而非 P1 的依据：任务书仅要求 `*`/`any file`/`all files`/`whole repo` 四种字面量仍 FAIL（**已全部满足**），且该串在 packet 语料中未被观测到（`execution-packets.json` 7/7 条无此形态）。 | 若要与 docstring 对齐，可在剥离前加一行「span 两侧不得紧邻 `*` 或 `/`」的守卫，或把剥离限制为**整串唯一/首尾为 run 边界**的 `**…**`。本版不阻塞，建议登记为后续小修。 |
| **F-02** | **P2** | `verify_workflow.py:12708`（同上） | 反向同类：`**a**` 被判为成对粗体 → PASS；`**foo`/`foo**`/`****` 因不成对 → 仍 FAIL。判据语义因此从「`*` = 通配符」漂移为「**部分 markdown 归一化器**」，而单 `*` 强调（`*foo*`）**故意不剥离**（`:12705-12707` 有明确理由）。 | **原误报类别未完全闭合**：含单个 `*emphasis*` 的 packet/断言文本仍会误报 `too broad`。属「收窄修复」而非「放宽」，与任务书（粗体 `**`）一致，故不阻塞。 | 在 FIX-319 覆盖说明或 docstring 中显式声明「仅中和成对 `**`，单 `*` 强调仍按通配符处置」——当前该边界只存在于代码注释，未进入 packet/验收文本。 |
| **F-03** | **P2** | `plan-tracker.md:94`（FIX-319 行）vs `verify_workflow.py:12708-12739` | 该行**明示修法二选一**：`(a)` 生成器剥离 markdown 标记后再写入 scope，`(b)` 判据改为**独立 token 匹配（按分隔符切词后逐词等值，而非子串包含）**。实现走了**第三方案**：判据侧**正则中和成对粗体 + 子串短语（加词首锚）**——既非 (a)，亦非 (b)。 | 交付满足该行两个验收面（含粗体不再误报 + 真宽范围仍 FAIL），但**偏离已登记的既定修法选项且未在偏差报告中申报该条**。契约漂移风险：后续若按 (b) 重做，属重复返工。 | 二选一：①在 packet/EVD 中补记「采纳第三种实现并说明 (a)/(b) 未选的量化理由」，②以 `plan-tracker` 更新该行修法枚举。属治理记录动作，不阻塞代码。 |
| **F-04** | **P2** | `tests/test_verify_workflow.py:11867-11882`（`test_scope_real_wildcards_still_too_broad`） | 该测试的 9 条向量**全部落在「剥离后仍残留 `*` 或残留宽范围短语」的区间**——即任何正确或错误的实现都恒判 FAIL 的区间。实测 M3 变体（`return text.replace("**","")`）与 M4 变体（`[^*]+?`→`.+?`）**均通过全部 9 条向量**。真正暴露 F-01/F-02 的向量（`**/tests/**`、`**a**`、`*foo*` 强调串）**不在集内**。 | 该测试**无法抓回** F-01/F-02 所描述的回退——测试套件在 A↔B 方向上强（M1/M2 抓回），在 B→宽方向的**该子区间**上存在盲区。已独立确认 **M1（换回旧子串判据）被 `test_scope_markdown_bold_is_not_a_wildcard` + `test_scope_phrase_match_is_word_anchored` 抓回，M2（去词首锚）被抓回**——故非「测试无效」，而是「覆盖子区间缺失」。 | 补 3 条向量：`"**/tests/**"`（锁 F-01 当前行为，或修掉）、`"**a**"`（锁 F-02 语义）、`"*emphasis*"`（锁单星号边界）。成本极低，收益是把已发现的语义灰色区固化。 |
| **F-05** | **P3** | `verify_workflow.py:12726` | `lambda match: ...` 的形参名 `match` **遮蔽 `re.match` 内建名**（PEP 8 A002 类问题）。 | 无功能影响（局部作用域，未使用 `re.match`）。 | 改名 `m`。 |
| **F-06** | **P3** | 任务书元数据 / 审查输入 | ①任务书称改动「已 staged」，实测 `git diff --cached` 为空、改动全在工作树（§0.1）；②任务书称「3 条 FAIL / 93 issues」，实测基线为 `FEAT-031` 1 条 / **86 issues**。 | 不改变 FIX-319 代码结论（diff 逐字节等价、误报根因已证），但**审查输入的两个数值前提均与实测不符**。 | Coordinator 侧以实测基线记账；`REL-077` 的 `missing execution packet` 是当前唯一活跃 FAIL，与本片无关。 |

---

## 4. 五维度 + 专项逐一结论

### 4.1 正确性（判据语义一致性检查）

- **与既有语义一致性**：改动**唯一调用点** `:12749`，Check 18c 其余判据（缺包 `:13853`、空包 `_execution_packet_field_issues`、`事实依据` `:12752`、`结构化事实` `:12754`、review 完成定义 `:12757`）**逐字节未动**（`git diff HEAD` 仅 1 处 `-` 行）。`exit code` 语义未变（`check_execution_packets` 的 `pass` 逻辑未动，实测 `pass=False` 仅因 `REL-077` 缺包）。
- **与生成器 scope 文本形态一致性**：`build_execution_packet` `:13790-13793` 确认 scope 由 `f"Only change files required by this task row: {scope}"` + 固定行拼装，`scope` 来自 plan-tracker 行文本——粗体确实会进入判据。实测 7/7 真实 packet，3 条含粗体、4 条不含，改动只翻转这 3 条 ✅。
- **边界条件**：`****`→FAIL、`***foo***`→`* foo *`→FAIL、`**a****b**`→` a  b `→PASS、跨行 `**foo\nbar**`→PASS（`[^*]` 不排除 `\n`）。均无反直觉行为。
- **自述「剥离后不可能新产生 `**` 对」**：**成立**。更强的一般化亦成立——`sub` 只删除字符，**任何由「删字符」实现的宽松化都不可能新造出原文不存在的子串**，故 R-4 的 192 条放宽全部只能来自「成对粗体」或「词首锚」两类，实测分类 0 条例外。
- **空输入**：`_is_too_broad_scope_text("")` 由调用点 `if allowed_text and …` 短路，未暴露空串路径 ✅。

### 4.2 安全性

- 无网络/文件/子进程/权限面；`re` 仅用于固定字面量模式，**无用户可控表达式**，无注入面。
- 硬编码密钥/token/password：**0**（`grep` 全 diff）。
- 失效方向为 **fail-open**（宽范围漏判）：仅 F-01 一处，且不涉及权限/数据边界。**OWASP 面无可报告项**。

### 4.3 可维护性

- 命名清晰（`_strip_markdown_bold_markers` / `_is_too_broad_scope_text` / `_TOO_BROAD_SCOPE_PHRASE_RE`），词首锚与「不锚尾」的**非对称选择在 `:12710-12714` 有明确理由**（保 `any files`/`whole repository` 覆盖）。
- 注释质量高，但 `:12732-12734` 的「stripping must never launder it」与实测 `**/tests/**` 相矛盾（F-01）——**注释略强于机制**。
- 函数长度 9 行 / 8 行；常量模块级预编译；无重复代码；无死代码（4 个新符号均有唯一调用/引用，`grep` 全仓确认无孤儿）。

### 4.4 性能

- `sub` 单趟、正则无嵌套量词，实测病态输入最差 1.9 ms / 50 KB（R-13）✅；判据每 packet 调 1 次，Check 18c 活跃集 6 条。
- 无 N+1 / O(n²) 引入。

### 4.5 测试覆盖 + AI 代码专项 5 项 + 突变推演

**覆盖**：新增逻辑行 100% / 分支 100%（R-6）；既有分支未被削减。

**突变推演（自有反相，抽取层构造，非仓库路径实验）**：

| 变体 | 描述 | 抓到该变体的新测试 | 判定 |
|------|------|-------------------|------|
| M1 | 换回旧子串判据（HEAD 行为） | `test_scope_markdown_bold_is_not_a_wildcard` + `test_scope_phrase_match_is_word_anchored` | **抓回 ✅** |
| M2 | 去掉短语词首锚 `\b` | `test_scope_phrase_match_is_word_anchored` | **抓回 ✅** |
| M3 | `return text.replace("**","")` | **0 条** | 未抓回（但实测该变体 9 条反证向量与 `**all files**` 仍 FAIL，未构成实际放宽 → 属**行为等价类**，非缺陷） |
| M4 | span 正则 `[^*]+?` → `.+?` | **0 条** | 未抓回；该变体恰能把 `**/tests/**` 从 PASS 修回 FAIL，即**测试锁不住 F-01 的两侧** |

**AI 代码专项 5 项**：

| 项 | 结论 |
|----|------|
| mock 残留 | **无**。新增测试用真实 `_validate_execution_packet` / 真实 `check_execution_packets` + `tempfile` 真实 plan-tracker；`patch.object(vw, "SAMPLE_PATH", …)` 是**路径注入**（既有测试的既定手法），非行为 mock |
| 硬编码返回值 | **无**。`_packet_with_scope` 的固定字段是**夹具数据**，非被断言的结果；判据本体无早退常量返回 |
| 幻觉 API | **无**。只用 `re.compile` / `.sub` / `.search` / `str.replace` / `unittest` / `json` / `tempfile` / `patch`，全部为 stdlib 真实 API |
| 未实现 TODO | **无**（diff 内 0 处 TODO/FIXME/pass 占位） |
| 过度实现 | **无阻塞项**。+47 行全部服务单一目标（4 符号 + 注释）；**唯一的「超出任务书字面要求」是短语词首锚**——该改动方向是**收紧误报、不放宽**（实测 168 条放宽全为 `xall files`/`installall files` 类无意义串），已在 `:12710-12714` 留理由，判**可接受**（见 F-03 的范围偏离另计） |

### 4.6 mock / 范围纪律复核

- `git status --porcelain` = **恰 2 行**；仓库根 scratch 残留 **0**；`.governance/execution-packets.json` **未被修改**（无掩盖 FAIL 行为）✅。

---

## 5. 偏离-1 / 偏离-2 / 偏离-3 逐条判定

### 偏离-1（任务书称 3 条 FAIL / 93 issues，实测基线 1 条 / 90 issues，「下降 ≥3」不可达）——**接受**

**判定依据（独立实测）**：Check 18c 作用域 = `_active_execution_packet_tasks()` = P0/P1 **且未完成**。实测活跃集 6 条，**FIX-315/FIX-317 因已标 `✅ 实现完成` 退出集合**，故其误报不再产生 FAIL 行。进程内实测 `check_execution_packets()`：改动前唯一受影响的活跃任务是 `FEAT-031`（FAIL→PASS）；`REL-077` 因缺包仍 FAIL。⇒ **「下降 ≥3」在当前 plan-tracker 状态下在数学上不可达**，非实现缺陷。

**修复目标是否达成**：**是**。目标（「消除系统性误报，同时不得放宽真实宽范围」）在**判据层完整达成**——真实语料 3/3 误报消除（R-1），任务书指定的 4 类宽范围字面量全部仍 FAIL（R-2），且真实 Check 18c 观测到 `FEAT-031` FAIL→PASS。数值验收项（≥3 行）是**对当时的过期基线写的**，应以「判据层 3/3 + 活跃集观测 −1」替代记账，而不是要求实现去制造 2 条额外下降。

### 偏离-2（全量套件 3 个失败为存量）——**接受（归因成立，已由本 Reviewer 独立复核）**

**双重独立证据**：

1. **无 FIX-319 的 HEAD 源 → 失败签名逐字相同**：`git archive HEAD` 取干净源至 `%TEMP%`，`PYTHONPATH` 接管 `sys.path[0]`（该文件自身 `sys.path.insert(0, _INFRA_DIR)` 可被前置路径覆盖，已实测 `RUNNER/LOADED` 指向 HEAD 源、`has FIX-319 = False`），跑同一测试类得 **`FAILED (failures=1, errors=1)`**，与 FIX-319 源**同一 2 个测试、同一 `'PASS' != 'BLOCKED'`、同一 `SystemExit: 1`**（3 个测试中第 3 个通过）。⇒ 与 FIX-319 **零因果**。
2. **残余 BLOCKED 真源逐字段对齐**：`scan_loop_runtime_claims(...)` → `verdict=BLOCKED`，`findings` 恰 3 条、`code=UNSUPPORTED_AFFIRMATIVE`、`normalized_path` 3/3 = **`docs/reviews/review-FIX-300-CODE-R0.md`**、`claim_id=LRC-ACTIVE-RUNTIME`——与 Coordinator 归因（`accounting:71:1 / 71:4 / 72:1`；`e994c7a`，FIX-300/0.66.1 期既有文件）**完全一致**。
3. **FIX-320 登记核实**：`.governance/plan-tracker.md:92`（P2，明示「发现即登记，本版不修」「本版处置 = (c)」）+ `.governance/evidence-log.md:2038`（EVD-1018）⇒ 登记**成立**（注：任务书称「已登记 FIX-320」时未给出位置，实际位于 `.governance/**`，非顶层 tracked 文件）。

⚠️ 一处**表述精度**（不足以推翻归因）：测试类 docstring `test_verify_workflow.py:199` 写「standalone CLI **reports the SAME identity verdict**」，而实测这 3 个测试**同族**中 `test_identity_host_source_drift_reproduces_divergence_shape` 失败于 **semantic caliber**（`scan_loop_runtime_claims` 断言 `PASS` 实得 `BLOCKED`），`test_fixture_identity_mode_agrees_with_engine_on_present_sources` 失败于 `SystemExit: 1`——两者均由语义面 BLOCKED 派生。归因（「语义面既有 BLOCKED ⇒ 3 个测试连带失败」）方向正确，**无需处置**。

### 偏离-3（词首锚定使 `install files under …` / `cover as many files as …` 由 FAIL 变 PASS）——**接受（属误报消除，非放宽）**

- 全笛卡尔积穷举（R-4）证明：词首锚引入的**全部** 168 条放宽都是 `xall files` / `installall files` / `aall files` 这类**无词边界的粘连串**，自然语言/scope 文本不会产出该形态。
- 任务书要求的 `all files` / `any file` / `whole repo` **全部仍 FAIL**（`files: all files`、`scope = all files`、`ALL FILES`、`All Files` 实测亦全部 FAIL）。
- **未引入新漏报**（反向验证）：新判据在结构上是旧判据的**严格子集**（词首锚 ⇒ 匹配集 ⊆ 子串匹配集），**不可能 FAIL 旧判据 PASS 的输入**；故「新增误报」为 0。
- 附带固化缺口（非回归）：`all-files` / `all_files` / `all  files`（双空格）**旧新两版均 PASS** ⇒ 该变体不因本片变差，但注释自称「保尾部开放覆盖」在两个 `all<非字母>files` 变体上未兑现，已在 F-02 同类语义漂移下记录。
- 该测试（`test_scope_phrase_match_is_word_anchored`）**确实是必要防护**：M2 变体（去锚）被它唯一抓回 ✅。

---

## 6. 真实环境命令上报表（R4 合规）

| 序 | 命令（摘要） | 退出码 | 影响路径 | 隔离 |
|----|-------------|--------|----------|------|
| 1 | `git diff --cached --name-only` / `--stat` / `status --porcelain` / `ls-files -s` / `hash-object` / `rev-parse` | 0 | 只读 | — |
| 2 | `git diff HEAD -- <2 paths>` | 0 | 只读 | — |
| 3 | `python -V` / `import coverage` | 0 | 只读 | — |
| 4 | `python probe.py` / `probe2.py`（AST 抽取判据 + 47/28 条向量矩阵 + 192 条穷举） | 0 | 只读仓库源 | 写：`%TEMP%\fix319_review\**` |
| 5 | `python -m unittest discover -k ExecutionPacket` | 0 | 只读 | `DSH_HOME=%TEMP%\fix319_review\tmpdsh` |
| 6 | `python -m unittest discover -k test_scope` | 0 | 只读 | 同上 |
| 7 | `python -m coverage run/json`（3 次，独立 data-file） | 0 / 1 | 只读 | `DSH_HOME` + `COVERAGE_FILE`/`COVERAGE_RCFILE` 均指向 `%TEMP%` |
| 8 | `python -m unittest discover -k FIX300DualCaliberAgreementTests`（Repo 源） | 1（预期存量失败） | 只读 | `DSH_HOME=%TEMP%` |
| 9 | `git archive HEAD \| tar -x -C %TEMP%\headsrc` | 0 | **只读仓库**；写 `%TEMP%\headsrc` | ✅ |
| 10 | `python -m unittest discover -k FIX300DualCaliberAgreementTests`（**HEAD 源**，`PYTHONPATH` 重定向） | 1（同上，签名一致） | 只读 | ✅ 隔离源 |
| 11 | `python scope.py`（`_active_execution_packet_tasks` + `check_execution_packets`） | 0 | 只读 | `DSH_HOME=%TEMP%` |
| 12 | `python -c`（`scan_loop_runtime_claims` findings dump） | 0 | 只读 | `DSH_HOME=%TEMP%` |
| 13 | `python verify_workflow.py check-governance --summary-only` | 0 | 只读 | `DSH_HOME=%TEMP%` |
| 14 | `python mutate3.py`（抽取层突变推演） | 0 | 只读仓库源 | 写：`%TEMP%\fix319_review\**` |
| 15 | `git grep` / `grep` 检索 | 0 | 只读 | — |

**写入清点**：全部写操作位于 `%TEMP%\fix319_review\**`（含 `headsrc`、`mut2`、`cov*\`、`probe*.py`、`mutate*.py`、`scope.py`）。**仓库路径写入 = 0**；`$DSH_HOME`/`~/.dsh` 写入 = 0（会话期经环境变量重定向）。**未**执行任何 `git add/commit/checkout/restore/stash/reset`。

---

## 7. 结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`

**理由**：
1. P0 = 0；5 维度 + 判据语义一致性 + AI 专项 5 项全部完成并列级。
2. 修复**核心目标已独立证实达成**：真实语料 3/3 误报消除；任务书指定的 4 类宽范围字面量（含全部 9 条指定反证向量）**全部仍 FAIL**；活跃 Check 18c 观测 `FEAT-031` FAIL→PASS。
3. 改动**唯一调用点、否则逐字节最小**；未改 packet 文件掩盖 FAIL；新增逻辑行/分支覆盖 100%；未引入性能或安全面问题。
4. 三条偏离均经独立复核**成立且理由充分**；3 个存量失败经「HEAD 源同签名复现 + findings 逐字段对齐」双重证否与 FIX-319 的因果，且已登记 FIX-320（P2，本版不修）。
5. 遗留 F-01~F-06 均为 **P2/P3 非阻塞**：F-01/F-02 是判据**语义灰色区**（相较任务书字面验收不放宽，且与该片「收窄修复」定位一致）；F-03 是治理记录动作；F-04 是测试覆盖子区间缺失。建议随本片或紧邻小修一并处置 F-01 + F-04 三条向量。

> 本审查**未**以「测试通过」代替「逻辑正确」：全部结论均由判据层逐向量实测、真实语料驱动、HEAD 源反证与突变推演共同支撑；**未**以「设计未规定」否定实现。
