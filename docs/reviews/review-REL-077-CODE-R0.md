# REVIEW-REL-077-CODE-R0 — 0.81.0 M-1 候选打包批（产品代码面）代码审查

**结论：NEEDS_CHANGE**（`unresolved_blockers=1` → P0×1）

- **Round**：R0（首轮）；无前轮引用。
- **审查对象**：`git diff --cached`（暂存面 = **25 文件 / +75 −76**）。HEAD = `5e6d8c7`；工作区相对索引无其它改动（审查期间被并发写入的 2 个文件不在索引内，见 F-07）。
- **被审面指纹**（取自 `git diff` 头，可复核）：`skills/.../infra/verify_workflow.py` `index 1c7bdc5..54bf53a`；`skills/software-project-governance/SKILL.md` `index 2b4633c..2a724b8`（与 e2e 镜像**同 blob**）；`docs/release/release-checklist-0.81.0.md` `index 57f6f7e..b77b048`。
- **报告路径说明**：本报告写在 `docs/reviews/`（本仓库既有审查归档目录，数百份 `review-*.md` 同址）。角色定义默认写 `.governance/review-{task_id}.md`；本次以 Coordinator 任务规范指定的路径为准，且 EVD-1033 已把 `docs/reviews/review-REL-077-CODE-R0.md` 登记为 PENDING 报告位置，二者一致。
- **写入范围声明**：本报告是本次审查**唯一**写入文件；未修改任何被审文件、未执行任何写操作命令、未触碰 `$HOME/.dsh` / `$DSH_HOME` / 仓库外路径。

---

## 0. 独立复现声明（我亲自复算/复核的数字）

以下每一项都是我在本次会话内**自己跑命令或自己数行**得出的，不是采信 Coordinator 的自述：

| # | 我亲自复算的内容 | 结果 |
|---|---|---|
| 1 | `git diff --cached --stat` 两次读取（会话初 + 并发写发生后） | **25 文件 / +75 −76**，两次一致 ⇒ 被审面未被并发写污染 |
| 2 | `git log --reverse --oneline d87ead8..3074120` 逐行编号 | **31 条**；第 N 个 commit 与 checklist Change Inventory 第 N 行**逐行一致**（31/31 全对，含 #4 `1ddb503`、#12 `3c37342`、#23 `61b571c`、#31 `3074120`） |
| 3 | `git rev-list --count d87ead8..3074120` | 31 ⇒ 窗口 tip = `3074120` 成立 |
| 4 | `git merge-base --is-ancestor 3074120 HEAD` / `d87ead8 HEAD` | 均 exit 0 ⇒ 二者都在本分支历史内 |
| 5 | `git show --shortstat 3074120` | **18 files, 7232 insertions(+), 22 deletions(-)** ⇒ 与「V8 = 18 文件 +7232」一致 |
| 6 | `git show --shortstat/-numstat 61b571c` | **3 files, 329 insertions(+), 13 deletions(-)**；`lib/index.js` **66+/13−**；另 `docs/reviews/review-FIX-313-CODE-R0.md` 76+、`infra/tests/test_dsh_adapter.py` 187+ ⇒ 与「+66/−13（3 文件 +329/−13）」**逐字一致** |
| 7 | `REQUIRED_SNIPPETS` 块范围定位（`REQUIRED_SNIPPETS = {` L721 → 结尾 `}` L1046） | 块内 `"0.81.0"` 字面量出现 **恰好 6 次**（L1029/1032/1035/1038/1041/1044）；块内 `0.80.0` = **0 次**；块内其它版本字面量仅 CHANGELOG 锚 `## [0.10.0]/[0.9.0]/[0.8.0]/[0.7.1]/[0.7.0]/[0.5.0]`（L1021–1026，**未被触碰**）⇒ 「恰好 6 处、块外零误伤」成立 |
| 8 | 15 个投影目标**逐个读盘**取版本字面量（非依赖命令自述） | 15/15 = `0.81.0`（含行号，见 §3） |
| 9 | 镜像字节一致证明（用 `git diff` 头的 blob 号） | 根 `skills/.../SKILL.md` 与 `project/e2e-test-project/skills/.../SKILL.md` 同为 `2b4633c..2a724b8`；两个 `commands/governance-init.md` 同为 `cdff8ed..53c722d` ⇒ byte_copy 投影成立 |
| 10 | 暂存 diff 内**被删行**的版本字面量集合（机械提取） | 仅 `0.80.0 ×32` + `0.81.0 ×11`（后者来自 checklist 被清理的重复 Change Inventory 行）⇒ **未误改任何历史版本字面量** |
| 11 | 暂存 diff 内**新增行**的版本字面量集合 | `0.81.0 ×43` + `0.80.0 ×2`（后者 = checklist「前置稳定版 **0.80.0**（tag `v0.80.0`）」1 行，属前置信引用）|
| 12 | 全仓 `0.80.0` 残留普查（`git grep -c`） | 76 文件 / 365 行，逐类判定见 §3.1 ⇒ **未发现「应改未改」的当前版本位** |
| 13 | `⟦` 占位普查（checklist） | 15 处，全部落在 M-2 门禁结果（L74–L86）+ 真机回贴面（L92）+ 冻结纪律的字面量引用（L112）；`feature-flags-0.81.0.md` 另有 5 处（F-02） |
| 14 | 审查终态核对（读审查报告文件本体，非读文档转述） | `review-FEAT-031-CODE-R0.md` L6/L74/L84、`R1` L8/L75/L85、`review-FIX-313-CODE-R0.md` L8/L66/L76 均 = **APPROVED_WITH_NOTES / `unresolved_blockers=0`** ⇒ 文档声明属实 |
| 15 | 治理记录核对 | `DEC-193` 在 `.governance/decision-log.md:141` 存在；`FIX-325` 在 `.governance/plan-tracker.md:97`（P2）登记 ⇒ 「机器守卫登记 FIX-325」属实 |
| 16 | tag 与回滚基线核对 | `git tag -l` → `v0.79.0`/`v0.80.0` **本地均存在**；`v0.80.0` → `71f73eb`；`71f73eb` 是 `d87ead8` 的祖先；`git rev-list --count 71f73eb..3074120` = **32** ⇒ 见 F-01 |
| 17 | 并发写入检测 | 会话初 `git status --short` 仅 25 个 staged 项；中途复读出现 2 个 worktree-only 改动（`architecture-baseline.json`、`test_triage_write_guard.py`）⇒ 见 F-07 |

---

## 1. 五维度逐项结论

### 维度 1：正确性 — **不通过（阻塞项在发布文档面，代码面正确）**

- 代码面：唯一可执行文件 `verify_workflow.py` 的改动是 4 个字典条目中的 6 个字符串字面量替换（`"0.80.0"`→`"0.81.0"`），无逻辑/控制流/条件判断变化。逐行读完 12 行 diff，无一处误伤（§0 第 7/10 条）。
- 校验方向正确（fail-closed 性质）：钉样设为 `0.81.0` 后，任一投影漏改都会 **FAIL 而非静默通过** ⇒ 方向安全。
- 边界：`.chrys-plugin/plugin.json` **不在** `REQUIRED_SNIPPETS` 块内，但**在** `checks/version.py:16` 的 `VERSION_PATHS` 内 ⇒ 无覆盖缺口（仅成员不对称，见维度 3）。
- 15 个投影目标逐一读盘 = 0.81.0，与权威源（`SKILL.md` frontmatter）一致（§0 第 8/9 条）。
- **阻塞**：发布文档面存在事实错误（F-01，回滚提交区间）⇒ 维度综合判定不通过。

### 维度 2：安全性 — **通过（无安全发现）**

- 无外部输入处理面变化；无密钥/凭据/token（改动内容仅为公共版本号字符串）。
- 4 个 hook（`pre-commit`/`commit-msg`/`post-commit`/`prepare-commit-msg`）的改动**全部落在 `# @version:` 注释行**，不进入任何执行路径 ⇒ 无命令注入、无权限面变化、无执行语义变化（逐行读 diff 确认）。
- 无权限控制/文件系统写路径/路径穿越面变化；无 OWASP Top 10 相关面被触碰。

### 维度 3：可维护性 — **通过（附 1 条 P3 改进）**

- 命名/注释：所有改动行保持原文措辞与格式，无新增函数、无重复代码、无超长函数。
- 漂移面量化：本次 bump 涉及 4 类面共 **30 处**版本位（权威源 1 + 投影 15 + 校验器 6 + 标记面 8，分布于 25 文件）。投影 15 处由 `release-projection --write` **确定性生成**（好），校验器 6 处为**手工同步**（本批 FIX-327 承担），是最高漂移风险点。
- **P3 改进建议**：把 `REQUIRED_SNIPPETS` 的 6 个版本钉改为从 `SKILL.md` frontmatter 派生（或纳入 `version-projections.json` 的派生面），消除每次发布的 6 处手改；同时登记 `.chrys-plugin` 与 `REQUIRED_SNIPPETS` 成员不对称。

### 维度 4：性能 — **通过（无影响）**

- 无算法/数据结构变化；被改的是模块级字面量字典（import 期构建），6 个等长字符串替换 ⇒ 时间/空间开销不可测。
- `release/projection.py::_inventory_value` 对 `REQUIRED_SNIPPETS` 做 AST 解析，输入规模不变（仍是 40+ 条目字典）⇒ 无退化。

### 维度 5：测试覆盖 — **不通过（P1，见 F-03）**

- 本批**未新增、未更新任何测试**（25 文件内无 `tests/` 文件）。
- 版本钉的唯一可执行面由既有测试间接覆盖；但据 EVD-1033，本批 bump 使 **3 项既有测试转红**（`delta_attributed: 3 项（版本钉过期 2 + 活体金丝雀数据漂移 1）→ FIX-328`），修复在制（FIX-328）且**不在本次暂存面内**。
- ⇒ 候选打包批**不是全绿树**；checklist Gate 10 的期望列写的是「无新增失败」，故该门禁在 FIX-328 落地前不可能成立（见 F-03）。3 项失败的具体测试名我**无法**执行套件核对（只读约束），静态复核出现矛盾（F-04）⇒ 标「待验证」。

---

## 2. 发现列表

### F-01 — **P0（阻塞）** — 回滚提交区间填写错误：把 32 个提交写成 2 个

- **位置**：`docs/release/rollback-plan-0.81.0.md:27`（同源错误另见 `:3`、`:81`）；`docs/release/release-checklist-0.81.0.md:87`
- **事实依据**：
  - `git merge-base --is-ancestor 71f73eb d87ead8` → **exit 0**（`v0.80.0` = `71f73eb` 是 `d87ead8` 的祖先）
  - `git rev-list --count 71f73eb..3074120` → **32**；`git rev-list --count d87ead8..3074120` → **31**
  - Change Inventory 窗口 `d87ead8..3074120` 的 31 个提交**全部**是 0.81.0 交付（V1~V8 + V10：FEAT-029/030/031、FIX-311/313/315/316/317/319/321）——逐行核对 §0 第 2 条
  - 被回填的值只有 2 个 hash：`61b571c`（V10，区间第 23 个）+ `3074120`（V8，区间第 31 个）
- **影响**：按该行执行 `git revert --no-commit 61b571c 3074120` 后，**29 个 0.81.0 提交仍在**——契约层、`dsh_contract.py`、`dsh_compat.py` 改造、`launch.py` 守卫、Check 28w / `dsh-doctor` 注册等全部保留，插件**不会**回到 0.80.0 行为。这与本文件自身的三处口径直接冲突：`:5`「回滚目标 = 把插件恢复到 0.80.0 行为」、`:54`「§4 验证 1 = 版本声明回到 0.80.0」、`:59`「0.80.0 基线实测于 `d87ead8`」（即区间起点恰为 `d87ead8`）。同时 checklist `:87` 已把它标为「**已交付**（回滚区间已按实测回填）」⇒ M-2 Gate 14「已交付且可执行」的**可执行性不成立**。
- **补充事实**：本批 checklist `:4` 把「候选打包 commit」定义为 M-1 冻结提交，而该提交本身也在待回滚区间内 ⇒ 正确区间终点是**打包提交**，不是 `3074120`。
- **最小复现**：
  ```
  git merge-base --is-ancestor 71f73eb d87ead8 ; echo $?      # 0
  git rev-list --count 71f73eb..3074120                        # 32
  git log --oneline d87ead8..3074120 | wc -l                   # 31
  ```
- **修复建议**：把 `:27` 改为
  `git -C <plugin_root> revert --no-commit d87ead8..<0.81.0 打包提交>   # 区间 = 0.80.0 线 tip d87ead8 → 本版打包提交（当前实测 31 commits + 冻结提交；V8 `3074120` / V10 `61b571c` 为区间末两个代表性交付）`
  并同步订正 `:3`、`:81` 与 checklist `:87` 的措辞，避免「回滚区间 = 2 个 commit」的表述残留。

### F-02 — **P1（关键，发布前必达）** — 姊妹 release 文档仍带 5 处 `⟦待 V8 回填⟧` 占位（冻结不完整）

- **位置**：`docs/release/feature-flags-0.81.0.md:3`、`:25`、`:26`、`:44`（**不在本次 25 文件暂存面内**）
- **事实依据**：`:3` 仍自称「**M-1 草稿**（2026-09-13）；`⟦待 V8 回填⟧` 项在 FEAT-031 落地后补齐」；`:25` 等「段号/退出码/`--offline` 适用域表」；`:26` 等「S2 投影字段（含 `unreadable_compositions`）」；`:44` 草稿结束语。而 V8 = `3074120` 已于本次冻结核定为「已落地」。
- **影响**：(1) 与 checklist `:112`「M-1 冻结前 MUST 把 `⟦待落地⟧`/`⟦待回填⟧` 占位**全部消除**」冲突——本批清干净了 checklist/rollback/version-plan/CHANGELOG，独留 feature-flags；(2) checklist `:64` 又把该文件 §2 作为「行为变更」的权威出处 ⇒ M-3 Release Reviewer 以「M-1 冻结完整」为前提阅读时会得到不一致事实；(3) 任务规范给定的占位允许面（仅 M-2 门禁结果 + 真机回贴）不覆盖此文件。
- **修复建议**：本轮回填 5 处（段号/退出码/`--offline` 适用域表/S2 字段/EVD-1026 指针），或明确把该文件的回填登记为 M-2 前置并在 checklist 注明「feature-flags 尚未冻结」。

### F-03 — **P1（关键，发布前必达）** — 冻结文档未披露本批引入的 3 项测试失败；FIX-328 未入 plan-tracker

- **位置**：`docs/release/release-checklist-0.81.0.md:82`（Gate 10 行）、`:23`（如实披露行）；`project/CHANGELOG.md`（0.81.0 段）
- **事实依据**：EVD-1033（`.governance/evidence-log.md:2094`）记 `"full_suite": {"current": "Ran 2983 failures=38 errors=2", "pristine_baseline_5e6d8c7": "Ran 2983 failures=28 errors=9", "delta_attributed": "3 项（版本钉过期 2 + 活体金丝雀数据漂移 1）→ FIX-328"}`；而 checklist Gate 10 行只写「既有失败基线（**非本版引入**）已由 pristine-HEAD 对照独立确认：`test_verify_workflow.py` 的 3 条（`UNSUPPORTED_AFFIRMATIVE` → FIX-320）」——**未提本批 bump 引入的 3 项**；登记行 `:23`/`:24` 亦只列 RISK-050 与 FIX-320。
- **影响**：读冻结文档会得出「唯一失败是既有 3 条」的结论；Gate 10 存在**在错误基础上被标 PASS** 的风险；且候选打包提交不是全绿树。差额核对：28F+9E=37 → 38F+2E=40，差 **+3**，与 EVD-1033 的归因一致（数值自洽）。
- **修复建议**：(1) 在 checklist「如实披露」区增一行：本批版本 bump 引入 3 项失败 + `FIX-328` 编号 + 「M-2 Gate 10 之前必须落地」；(2) 把 `FIX-328` 登记进 `plan-tracker`——当前它只在 `evidence-log`（EVD-1033）与 `agent-locks.json` 可见，`plan-tracker` 无该任务行，属 M1.2「先入账再执行」形态缺口。
- **待验证**：3 项失败的具体测试名我无法执行套件核对（见 F-04）。

### F-04 — **P2（建议）** — 3 项失败的归因静态不可复现，且失败集合处于变动中

- **位置**：`skills/software-project-governance/infra/tests/test_verify_workflow.py:14681`、`.../tests/test_review_machine_provenance.py:218`
- **事实依据**：
  - `test_bootstrap_version_marker_injected_into_all_profiles`（L14681）用 FIX-256 **动态**读 `SKILL.md` frontmatter 版本（L14687–14692），断言 `commands/governance-init.md` 中 `> @bootstrap-version: {version}` 出现恰 3 次（L14694–14697）。本批已把该文件 3 处标记同步为 0.81.0 ⇒ **静态判定应为 PASS**，与「该测试因版本钉过期而失败」的归因矛盾。
  - `test_injection_contract_anchors_include_review_record`（L218）断言 `INJECTION_CONTRACT_ANCHORS[...]` 含 `review-record`（`verify_workflow.py:6628` 确含）+ `check_injection_contract()["issues"] == []`，且锚集含**动态** `@version-line`（L6612/L6633）⇒ **静态判定亦应为 PASS**。
  - `agent-locks.json` 当前 `file_locks` = `test_verify_workflow.py` / `test_review_machine_provenance.py` / `test_release_ledger.py`（第三个**不在**任务给出的 3 项失败名单里），而 in-flight 编辑落在 `test_triage_write_guard.py` ⇒ 失败集合尚未收敛。
- **影响**：F-03 的披露文字若照抄现有归因，可能写错测试名/原因，构成新的失实陈述风险。
- **修复建议**：等 FIX-328 落地后**重跑全量并贴原始失败清单**，再据此写披露；不要复用当前归因文本。**标注：待验证。**

### F-05 — **P2（建议，超出本批范围）** — README 对 `v0.80.0` 的状态陈述已过期

- **位置**：`README.md:92`、`:393`、`:442`（**不在本次 25 文件暂存面内**）
- **事实依据**：README 称 `v0.80.0` 是「**candidate awaiting authorization**（no tag exists）」、GitHub master 仍服务 0.78.1；但 `git tag -l` 实测 `v0.79.0`/`v0.80.0` **均存在**，`v0.80.0` → `71f73eb`，且 `.governance/plan-tracker.md:11` 记 0.80.0 已发布（2026-09-12）。
- **影响**：对外文档与仓库事实不符（属 FIX-324 ②/F-9 已登记的「全仓版本字面量口径」面，非本批引入）。
- **修复建议**：随 REL-077 文档批或 M-8 收尾修正；若 0.81.0 发布说明引用 README，则须先修。

### F-06 — **P3（讨论）** — `check-version-consistency` 实际含 1 条 `[WARN]`，Coordinator 结论行未引述

- **位置**：`.governance/plan-tracker.md:11`（`工作流版本: 0.80.0`；该目录被 `.gitignore:10` 忽略，不入 git）；判定逻辑 `checks/version.py:110–115`；命令实现 `verify_workflow.py:21128`（`fail_items` 显式排除 `[WARN]` 前缀，L21143 输出 PASSED）
- **事实依据**：静态推导唯一失败面 = `[WARN] plan-tracker workflow version=0.80.0, expected=0.81.0` ⇒ 结果行仍是「PASSED — all version declarations consistent」、exit 0。**结论行本身正确**，但「all version declarations consistent」省略了该 WARN。
- **影响**：M-2 Gate 1 若按「零告警」理解会与实测不符。按 checklist `:97`，plan-tracker 版本行在 M-8「转 released」时更新 ⇒ M-1/M-2 阶段保留该 WARN 可接受。
- **建议**：Gate 1 行加注「含 1 条 plan-tracker `[WARN]`（M-8 清除）」。（本项为**静态推导**，我未执行该命令——见 §5 未验证声明。）

### F-07 — **P3（讨论）** — 审查期间工作树被并发写入；任务给出的测试基线快照已过期

- **位置**：`skills/software-project-governance/core/architecture-baseline.json`、`skills/software-project-governance/infra/tests/test_triage_write_guard.py`（**均为 worktree-only，未 staged**）
- **事实依据**：会话初 `git status --short` 仅列出 25 个 staged 项；审查中途复读新增 ` M architecture-baseline.json`（`generated.git_head` `210b200…`→`5e6d8c7…`）与 ` M test_triage_write_guard.py`（**+22/−1**，为 `test_live_plan_tracker_flags_only_known_m1_rows` 加 FIX-328 语义：命中集合为空 → `skipTest`，subset 断言无条件保留）。`git diff --cached --stat` 复读仍为 25/75/76 ⇒ 被审面未被污染。`git show HEAD:<该测试文件> | grep FIX-328` **无命中** ⇒ 该改动确系在制（FIX-328），非 HEAD 既有。
- **影响**：(1) 任务给出的「当前工作树 `Ran 2983, failures=38, errors=2`」是这些编辑**之前**的快照，现已过期，任何 M-2 门禁测量必须在 FIX-328 收尾后重取；(2) 审查者与开发者共用工作区存在「复审对象漂移」风险，建议 M-2 前固定一次干净快照。

---

## 3. 版本位一致性专项结论（对应审查重点 1、2、3）

### 3.1 全仓 `0.80.0` 残留（365 行 / 76 文件）逐类判定

| 类别 | 例证 | 判定 |
|---|---|---|
| 历史资产（release 归档） | `docs/release/release-checklist-0.80.0.md`(29)、`rollback-plan-0.80.0.md`(11)、`docs/requirements/architecture-evolution-0.80.0.md`(24)、`test-baseline-0.80.0.md`、`perf-baseline-0.80.0.json` | **应残留**（文件名/内容即历史版本实体） |
| 历史审查报告 | `docs/reviews/review-REL-076-*.md`、`review-FIX-3xx-*.md` 等数百份 | **应残留**（不可改写的历史记录） |
| 已发布版本记录 | `skills/.../core/releases/0.80.0.json` | **应残留**（0.81.0 记录按 checklist `:97` 在 M-8 落库） |
| CHANGELOG 历史条目 | `project/CHANGELOG.md` 中 0.80.0 及更早条目（14 处） | **应残留**（本批只改 0.81.0 条目） |
| 前置信引用 | `docs/release/{release-checklist,rollback-plan,version-plan,real-machine-acceptance,feature-flags}-0.81.0.md`「前置稳定版 0.80.0 / tag `v0.80.0`」 | **应残留**（正是指向 0.80.0 的引用） |
| 源码/测试中指向 0.80.0 文件或历史基线 | `infra/perf_protocol.py:78`、`infra/registry.py:3`、`infra/quickscan_registry.py:16`、`infra/contract_matrix/*`、`tests/test_archive.py:3597+`、`tests/test_quickscan_registry.py:53`、`core/perf-tolerance.json:4`、`core/architecture-baseline.json:18/449` | **应残留**（引用对象名/历史口径，非当前版本位） |
| 对外文档现状陈述 | `README.md:92/:393/:442` | **非版本位**，但陈述已过期 → F-05 |

⇒ **未发现「应已更新却残留（漏改）」的当前版本位。** 唯一「当前版本位」类残留是 `.governance/plan-tracker.md:11`（非 git 跟踪）→ F-06。

### 3.2 `REQUIRED_SNIPPETS` 版本钉（对应审查重点 2）

- 块范围：`L721`（`REQUIRED_SNIPPETS = {`）→ `L1046`（闭合 `}`，其后空行 + `# ── Manifest domain` 锚保持 `checks/version.py:89` 的正则 `REQUIRED_SNIPPETS\s*=\s*\{(?P<body>.*?)\n\}\n{2,}# ── Manifest` 可匹配 —— 我按该正则逐条核对，**未破坏**）。
- 6 处版本钉 = `.claude-plugin/plugin.json`(L1028-1029)、`.claude-plugin/marketplace.json`(L1031-1032)、`.codex-plugin/plugin.json`(L1034-1035)、`.zcode-plugin/plugin.json`(L1037-1038)、`package.json`(L1040-1041)、`core/manifest.json`(L1043-1044) —— **恰好 6 处，块外零误伤**。
- 块内历史锚 `## [0.10.0]/[0.9.0]/[0.8.0]/[0.7.1]/[0.7.0]/[0.5.0]`（L1021–1026）**未被触碰**；`0.80.0` 在块内出现 **0** 次。
- 不对称（P3）：块内覆盖 4 个 plugin manifest + marketplace + package + core manifest，但**缺 `.chrys-plugin/plugin.json`**（该文件在 `VERSION_PATHS` 内，故实际有守卫；仅成员不对称）。

### 3.3 15 个投影目标与权威源一致性（对应审查重点 3，逐目标实测）

| # | projection id | 目标文件 | 读盘结果 |
|---|---|---|---|
| 1 | fixture-skill | `project/e2e-test-project/skills/software-project-governance/SKILL.md:3` | `version: 0.81.0` ✅ |
| 2 | core-manifest | `skills/.../core/manifest.json:4` | `"version": "0.81.0"` ✅ |
| 3 | claude-plugin | `.claude-plugin/plugin.json:3` | ✅ |
| 4 | claude-marketplace | `.claude-plugin/marketplace.json:12`（`/plugins/0/version`） | ✅ |
| 5 | codex-plugin | `.codex-plugin/plugin.json:3` | ✅ |
| 6 | zcode-plugin | `.zcode-plugin/plugin.json:3` | ✅ |
| 7 | chrys-plugin | `.chrys-plugin/plugin.json:3` | ✅ |
| 8 | package | `package.json:4` | ✅ |
| 9 | fixture-plan | `project/e2e-test-project/.governance/plan-tracker.md:9` | `工作流版本: 0.81.0` ✅ |
| 10 | hook-pre-commit | `skills/.../infra/hooks/pre-commit:6` | `# @version: 0.81.0` ✅ |
| 11 | hook-commit-msg | `.../hooks/commit-msg:5` | ✅ |
| 12 | hook-post-commit | `.../hooks/post-commit:4` | ✅ |
| 13 | hook-prepare-commit-msg | `.../hooks/prepare-commit-msg:6` | ✅ |
| 14 | dsh-persona-version | `agent-presets/governance/agent.cordis.yml.template:51` | `治理工作流（v0.81.0）` ✅ |
| 15 | dsh-agents-bootstrap-version | `adapters/dsh/AGENTS.md.template:3` | `> @bootstrap-version: 0.81.0` ✅ |
| — | 权威源 | `skills/software-project-governance/SKILL.md:3` | `version: 0.81.0`（source） |

另：标记面 8 行 = `AGENTS.md:5`、`commands/governance-init.md`(×3) 、`project/e2e-test-project/CLAUDE.md:5`、`project/e2e-test-project/commands/governance-init.md`(×3) 均 = 0.81.0 ✅；CHANGELOG 顶部 `## [0.81.0] - 2026-09-13` ✅（`checks/version.py:107–109` 的首行断言满足）。
**25 文件闭合核算**：15 投影 + 权威源 1 + 校验器 1 + 标记面 4 + release 文档 3 + CHANGELOG 1 = **25** ✅（与 `diff --cached --stat` 完全吻合）。

### 3.4 Change Inventory 与 git log 闭合（对应审查重点 4）

- 表体 `L30–L60` = **31 行**；编号列 **1..31 连续**、无跳号、无重复、无截断半句（逐行读完）。
- 31 个 commit hash 与 `git log --reverse --oneline d87ead8..3074120` **逐行完全一致**（§0 第 2 条）。
- 头部窗口声明 `d87ead8..3074120` 与实际一致；「tip = `3074120`」成立。
- **实际修复的既有缺陷**：旧版把 Change Inventory 的 #20~#32 行错贴在 `Candidate Gate Results` 表下方（14 行截断半句混入），本批已删除并把 #14 行归位 ⇒ 该表恢复为 14 行完整表。
- 待办（非缺陷）：候选打包 commit 的 hash 采用「M-2 期由 `release-ledger --version 0.81.0 --no-remote` 派生后回填」的写法（`checklist:4`），属无法自指的合理安排，未标记 `⟦⟧` 但已用文字显式声明。

---

## 4. AI 代码专项 5 项（逐条结论）

| # | 检查项 | 结论 |
|---|---|---|
| 1 | **mock 残留** | **未发现**。diff 不含 mock/stub/假实现；25 文件中无测试文件被改。 |
| 2 | **硬编码返回值** | **未发现缺陷**（登记为改进点）。diff 内确有硬编码字符串（6 个 `"0.81.0"` + 15 个投影字面量），但这是**既有契约设计**（版本钉/投影契约，由 `manifest.release_projection_contract.validation_inventories` 与 `version-projections.json` 结构化约束），且属「**校验期望值**」而非被返回的业务值；本批只是把期望值从旧版本同步到新版本，未引入任何绕过分支。改进建议见维度 3（P3）。 |
| 3 | **幻觉 API 调用** | **未发现**。diff 未新增任何 import、函数/命令调用、路径或 API 名；`verify_workflow.py` 改动仅在既有字典字面量内。 |
| 4 | **未实现 TODO** | **代码面未发现**。diff 未新增 TODO/FIXME/空实现。文档面的 `⟦待回填⟧` 属 M-2 门禁回填协议（允许面），唯一例外是 `feature-flags-0.81.0.md` 的 5 处（F-02）。 |
| 5 | **过度实现** | **未发现**。改动最小且纯粹：25 文件全部是版本字面量替换 + 文档冻结推进，无顺带重构、无越界修改。反向检查（是否**漏**改）：15 投影逐个读盘 + 标记面 8 处 + 校验器 6 处全部到位，`0.80.0` 残留全部可归为历史资产/前置信引用 ⇒ 无漏改。 |

---

## 5. 设计一致性检查（硬门槛项）

| 检查点 | 期望（ADR/契约/DEC） | 实测 | 裁决 |
|---|---|---|---|
| 版本权威源 | `SKILL.md` frontmatter 唯一权威（DEC-096；`version-projections.json.authority.kind = skill_frontmatter_version`） | 本批未改机制、只改值；`SKILL.md:3` = 0.81.0，15 投影全部跟随 | ✅ |
| 投影契约 | manifest `release_projection_contract`：15 ids / 3 kinds / 2 validation inventories（`projection.py:125–176` 强校验 set 相等） | 15 个 id、kind 集合、2 个 inventory 全部未变；**未手改投影产物**（15 个目标均与引擎计划一致，`written=15`） | ✅ |
| hook 版本面 | `checks/version.py:99–104` 断言 4 个 hook 的 `@version` == source | 4/4 = 0.81.0；改动全在注释行 | ✅ |
| bootstrap 标记面 | `checks/version.py:116–137`：tracked 入口文件陈旧 → FAIL（fail-closed）；e2e 镜像与命令模板同步 | `AGENTS.md` / `commands/governance-init.md` ×3 / e2e 镜像 ×3 / e2e `CLAUDE.md` 均已 bump | ✅ |
| 注入契约面 | `INJECTION_CONTRACT_ANCHORS` 含动态 `@version-line`（L6612/L6633），persona 版本行必须随权威源 | `agent.cordis.yml.template:51` = v0.81.0，与 source 一致 | ✅ |
| DEC 落地 | DEC-193（设计口径收窄）须入 decision-log | `decision-log.md:141` 存在且内容与 checklist `:59` 一致 | ✅ |
| 遗留登记 | V10 验收① 无机器守卫 → 须显式登记 FIX-325 | `plan-tracker.md:97`（P2）登记，含 F1~F5 与修法 | ✅ |
| **回滚口径** | 「回滚目标 = 恢复到 0.80.0 行为」须与所给提交区间自洽 | **不自洽**：区间只给 2/32 个提交 | ❌ **F-01** |
| 冻结完整性 | M-1 冻结前占位全部消除（checklist `:112`） | release 三件套 + CHANGELOG 已清；`feature-flags-0.81.0.md` 仍 5 处 | ❌ **F-02** |

**真实环境措辞纪律（审查重点 5）**：本批 staged 文档**未出现**无限定语的「真实安装/真实环境通过」。核验：`version-plan:137` 正向声明措辞纪律；`:149` 真机三项标「**未验证**」；`checklist:92` `⟦待用户回贴⟧` + 「回贴前 MUST NOT 声明通过」；`CHANGELOG:35` 同口径；`rollback-plan:60` 真机项标「需用户回贴」；`rollback-plan:47` / `checklist:81` 的写入类断言均带 `DSH_HOME=%TEMP%` / `real-home writes: 0` 隔离限定。**裁决：合规**。

**诚实性专项（V10 验收①）**：`CHANGELOG:V10` 条与 `checklist:128–137` 的准确表述为「由独立审查的故障注入复现成立，机器守卫待 FIX-325」，并显式写入硬约束「MUST NOT 声称『验收① 有测试守卫』」；`review-FIX-313-CODE-R0.md` 文件本体确以 `APPROVED_WITH_NOTES / unresolved_blockers=0` 收口且 F1(P1) 即该无守卫判定。**未发现「声称有测试守卫而实际没有」的表述** ⇒ 该历史敏感点本轮**合规**。

---

## 6. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **1**（F-01） | ❌ **未通过** |
| 5 维度全覆盖 | = 100% | 5/5 逐项有结论（§1） | ✅ 通过 |
| 每条发现标注级别 | = 100% | 7/7 条带 P0~P3（§2） | ✅ 通过 |
| 设计一致性检查 | 已完成 | 已完成（§5，9 项检查，2 项发现偏离） | ✅ 通过 |
| AI 代码专项 5 项 | 全部完成 | 5/5 逐条有结论（§4） | ✅ 通过 |

⇒ 硬门槛未全通过（P0 = 1）→ **结论 NEEDS_CHANGE（R0）**。

---

## 7. 结论与处置要求

**结论：NEEDS_CHANGE**（`unresolved_blockers=1`）

- **阻塞项（会阻断 0.81.0 发布）**：**F-01**（P0）。理由：回滚方案是 M-2 Gate 14 的交付物且已在冻结清单中被标为「已交付且可执行」，而其提交区间写成 2/32 个提交 ⇒ 按文执行无法恢复 0.80.0 行为，可执行性不成立。
- **强烈建议本轮修复（发布前必达，不阻断本批合并但阻断 M-2/M-3 的正确性）**：**F-02**（feature-flags 占位残留，冻结不完整）、**F-03**（本批引入 3 项测试失败未披露 + FIX-328 未入 plan-tracker）。
- **建议/讨论**：F-04（归因待验证）、F-05（README 现状陈述过期，超出本批）、F-06（1 条 plan-tracker WARN 未引述）、F-07（并发写入致基线快照过期）。
- **复审要求（M7.4）**：修复后由 Coordinator 重 spawn 本 Reviewer 执行 R1；R1 必须逐条比对 F-01/F-02/F-03 的修复状态（已修复/未修复/新引入），并复核 F-07 指出的基线快照重取结果。

**产品代码面单独结论**：25 文件中的**产品代码/配置面（版本权威源 + 15 投影 + 6 版本钉 + 8 标记面 + hooks）经逐项实测，正确、完整、无漏改、无历史字面量误伤**，可直接采纳；本报告的阻塞项**全部落在发布文档事实面**（`docs/release/rollback-plan-0.81.0.md` + checklist 一行），修复成本极低（约 4 行文本）。

---

## 8. 命令上报（只读；命令 / 退出码 / 输出摘要）

| # | 命令（工作目录 = 仓库根） | 退出码 | 输出摘要 |
|---|---|---|---|
| 1 | `git diff --cached --stat` | 0 | `25 files changed, 75 insertions(+), 76 deletions(-)` |
| 2 | `git status --short` / `git rev-parse HEAD` | 0 | 25 个 `M ` staged 项；HEAD = `5e6d8c71a2dad19c8cff3b720fbe7a99bae83629` |
| 3 | `git diff --cached --no-color` | 0 | 全文 diff（本报告主要依据） |
| 4 | `git log --reverse --oneline d87ead8..3074120` + 计数 | 0 | 31 条，逐行编号与 Change Inventory 全对；tip = `3074120` |
| 5 | `git merge-base --is-ancestor {3074120,d87ead8} HEAD` | 0 / 0 | 两者均在 HEAD 历史内 |
| 6 | `git show --shortstat --oneline 3074120` | 0 | `18 files changed, 7232 insertions(+), 22 deletions(-)` |
| 7 | `git show --shortstat/--numstat 61b571c` | 0 | `3 files changed, 329 insertions(+), 13 deletions(-)`；`lib/index.js` `66/13` |
| 8 | `git grep -I -c "0\.80\.0"` / `"0\.81\.0"` | 0 | 0.80.0 = 76 文件 / 365 行；0.81.0 = 69 文件 / 190 行 |
| 9 | `git grep -n "0\.8[01]\.0" -- <live code/test paths>` | 0 | live 残留全部为「引用 `*-0.80.0.md` 文件名/历史基线/历史散文」，无当前版本位 |
| 10 | `[System.IO.File]::ReadAllLines` 切片 L721–L1046 统计 | 0 | 块内 `"0.81.0"` = 6、`0.80.0` = 0、历史锚未变 |
| 11 | `Select-String` 逐目标取版本字面量（15 目标 + 权威源） | 0 | 16/16 = `0.81.0`（含行号） |
| 12 | `git diff --cached -U0 \| 提取增/删行版本字面量` | 0 | 删 = {0.80.0×32, 0.81.0×11}；增 = {0.81.0×43, 0.80.0×2} |
| 13 | `Select-String -Pattern "⟦"`（checklist / feature-flags） | 0 | checklist 15 处（全在允许面）；feature-flags 5 处（F-02） |
| 14 | `git grep -n "FIX-328"` / `git show HEAD:<test_triage_write_guard.py> \| Select-String FIX-328` | 1 / 0（无命中） | HEAD 无 FIX-328 ⇒ 并发改动确为在制变更 |
| 15 | `git diff --stat`（unstaged） | 0 | 2 文件：`architecture-baseline.json` 2±、`test_triage_write_guard.py` +22/−1 |
| 16 | `git tag -l "v0.79*" "v0.80*" "v0.81*"`；`git rev-list -n1 v0.80.0` | 0 | `v0.79.0`、`v0.80.0` 存在；`v0.80.0` → `71f73eb`（无 v0.81.0 tag） |
| 17 | `git merge-base --is-ancestor 71f73eb d87ead8`；`git rev-list --count 71f73eb..3074120` | 0 | exit 0（祖先成立）；32（vs 窗口 31）⇒ F-01 依据 |
| 18 | `git grep FIX-325/DEC-193`（首次，命中 0 因 `.governance/` 被 gitignore）；改用 Read/Grep 直读 | 1 → 0 | `DEC-193` = decision-log:141；`FIX-325` = plan-tracker:97 |
| 19 | `python -c` 单行（读 `release_projection_contract` + `version-projections.json`） | 0 | 15 个 projection id / 3 kind / 2 inventory，authority = skill frontmatter |
| 20 | 一次多行 `python -c` 因 pwsh 引号被当 ScriptBlock 解析 | **1**（未产生任何副作用） | 改用单行重跑成功（见 #19） |

**未执行的命令（受只读约束主动不执行）**：`verify_workflow.py` 各 check 子命令、`release-ledger`、`--regen`、`unittest` 全量套件、`npm/pnpm` 任何写操作、任何 `git add/commit/restore/reset/checkout/stash`。

## 9. 未验证 / 超出授权面声明

1. **未执行测试套件**：受只读约束，未跑 unittest ⇒ F-03 的失败集合与 F-04 的归因矛盾**均为待验证**（已按 code-review SKILL「事实依据红线」标注，未写成已通过）。
2. **未执行 verify_workflow 门禁命令**：Coordinator 给出的 4 项 PASSED 我**未独立复跑**，仅按源码 + 制品静态复核（结论：其声明的投影/注入契约/版本一致性在制品层面可静态印证；版本一致性的 1 条 `[WARN]` 见 F-06）。
3. **未触碰用户真实环境**：未访问 `$HOME/.dsh`、`$DSH_HOME`、仓库外任意路径；未做任何安装/验收操作。
4. **并发写入**：审查期间工作树被 FIX-328 在制改动（F-07）；被审**暂存面**两次读取一致，结论对暂存面有效。
