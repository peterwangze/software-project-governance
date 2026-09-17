结论：NEEDS_CHANGE ｜ round=0 ｜ unresolved_blockers=1 ｜ 机录 round 建议 = REVIEW-REL-078-R1

# REVIEW-REL-078-CODE-R0 — 0.82.0 窗口聚合面（M-3 产品代码半面）代码审查

- **审查对象**：0.82.0 窗口 = `e376ddf..工作树`。实测构成：**14 个已落库 commits**（`git rev-list --count e376ddf..HEAD` = 14；= 任务书枚举的 11 个 0.82.0 载荷 commits `8bd6a8a`~`845c050` + FIX-338 发布后修复 3 commits `1db58f5`/`02ad554`/`dfafa95`——构成与 rollback-plan「区间锚定」节及 checklist Change Inventory 头注**如实一致**）+ **未提交候选增量**（暂存面 **25 文件 / +498 −21**，两次读取一致）+ 审查中途出现的 **2 个未暂存并发修改**（见 F-02a/F-07）。
- **Round**：R0（首轮）；无前轮引用。同型先例：REVIEW-REL-077-CODE-R0（0.81.0 M-1 批）。
- **隔离纪律**：全部引擎命令从仓库根运行；每次调用以 `$tmpHome = Join-Path $env:TEMP ("spg-rel078-code-r0-…" + guid)` 隔离 `DSH_HOME`（FIX-337 非保留变量名规范）；套件日志/JSON 落盘全部在 `%TEMP%`（反相/产物限 %TEMP%）。真实环境（`$HOME/.dsh`、真实 `$DSH_HOME`）**零触碰**；本报告是本次审查**唯一**仓库写入文件。
- **机录**：本报告只产出审查结论；REVIEW 证据行由 Coordinator 经 `review-record` CLI 机录（本报告不手写 REVIEW 行）。

---

## 0. 独立复现声明（我亲自复算/复核的数字，全部在本次会话内实测）

| # | 我亲自复算的内容 | 结果 |
|---|---|---|
| 1 | `git log -1 e376ddf --oneline` | `e376ddf = REL-077: 0.81.0 transition + 门禁收口与审查退回修复`（= 0.81.0 发布 tip，`1db58f5` 的父提交）⇒ 回滚锚语义成立 |
| 2 | `git rev-list --count e376ddf..HEAD` | **14**；14 个 hash 与 checklist Change Inventory 行 1~14 **逐行完全一致**（逆序），无遗漏/多报/跳号 |
| 3 | `git diff --cached --numstat`（T0 与 T2 两次） | **25 文件 / +498 −21**，两次一致 ⇒ 暂存被审面未被并发写污染 |
| 4 | `Get-FileHash adapters/dsh/host-contract.json -Algorithm SHA256` + 字节数 | `63B28311330DCDED6192CC3350C81735F8557E0D6115D570ABCA328853228DF2` / **75331 bytes** ⇒ 与 checklist Gate 12 M-0 预检值**逐字符精确一致** |
| 5 | `git diff --cached -U0 -- host-contract.json` / `adapter-manifest.json` | 契约 = **恰 3 处 note**（evidence.note / `dsh_cli_version_current_measurement` / `recorded_slice`，3+/3−，全在 note 字符串内 ⇒ `recording.writer` 未动）；manifest = 1 行 note（dsh-doctor 登记）⇒ FIX-326③/①「恰 3 note」成立 |
| 6 | `[IO.File]::ReadAllLines` 计 `verify_workflow.py` | **24453 行**（archguard R1 锚恒等的原始行数面） |
| 7 | `check-version-consistency` 实跑（T1，bump 钉未同步时点） | `Result: FAILED — 1 mismatch(es)`，`[FAIL] verify_workflow.py snippet: hardcoded version mismatch`，**exit 1** |
| 8 | 同命令复跑（T3，钉经并发修复后） | `Result: PASSED — all version declarations consistent`，**exit 0**；仅 1 条预期 WARN（plan-tracker 工作流版本 0.81.0——gitignored，M-8 清除面，与 checklist Gate 1 预期披露一致） |
| 9 | `check-projection-sync --fail-on-issues`（T1/T3 两次） | 均 `PASSED`（15 投影同步，Source version 0.82.0），exit 0 |
| 10 | `archguard-ratchet` 实跑 | R1 `PASS 24453 ≤ anchor 24453`、R2 47、R3 12 edges、R4 1299、R5 `cli 84/84 + segments 71/71`、R6 196 Δ0、R7 `committed==fresh True`，`Result: PASS (0 violations)` ⇒ 24453 锚恒等 + feature-flags §3「84/84 + 71/71 不变」声明实测吻合 |
| 11 | `check-dsh-boundary`（28w）实跑 | `Result: PASS — 0 failing criterion(a)`；**K-2 `outside-contract host literals: 0 (11 declared consumer(s) scanned)`** ⇒ 契约外字面量 0 成立；K-7 `NOT_RUN`（verified_on=null，DEC-193 as-built 合法态，review-FIX-324-326 F-3 同口径） |
| 12 | loop-claims 双模式实跑（隔离 DSH_HOME） | `installed_host`：4 条账本豁免**全部生效**（`exemptions_applied` 含 LRC-EXEMPT-FIX300R0-71-1/-71-4/-72-1 + CHECKLIST0810-241-1），`state_totals` = 3 UNSUPPORTED + 1 AMBIGUOUS（恰为账本 4 条族，**无新增语义 finding**），但 `verdict: BLOCKED`、exit 1——唯一未豁免 finding = `ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY: ragged table row` @ `docs/reviews/review-FIX-333-CODE-R0.md`（见 F-03）；`product_release`：exit 1（同族形态） |
| 13 | TestLoader discover 计数 | 全量 `FULL_DISCOVER_COUNT = 3200`（与 checklist Gate 10 B-7 M-0 口径**精确一致**）；模块 `MODULE_DISCOVER_COUNT = 850`（850 口径存在性确认） |
| 14 | `python -m unittest discover -p test_verify_workflow.py`（隔离 DSH_HOME，两次） | **`Ran 850 tests in 198.694s`，`FAILED (failures=4)`**，exit 1：① `test_bootstrap_version_marker_injected_into_all_profiles`（`AssertionError: 0 != 3`）；② `test_fixture_identity_mode_agrees_with_engine_on_present_sources`（`'PASS' != 'FAIL'`，L262）；③ `test_identity_host_source_drift_reproduces_divergence_shape`（`'PASS' != 'BLOCKED'`，L223）；④ `test_claim_command_emits_complete_pass_report`（`0 != 1`，L61）——②③④ 与 #12 的 live 引擎态互证 |
| 15 | 豁免账本读盘（`core/loop-runtime-claim-exemptions.json`） | 4 条九键与 CHANGELOG/feature-flags §1.1 描述一致（3×UNSUPPORTED@review-FIX-300-CODE-R0 `accounting:71:1/71:4/72:1` + 1×AMBIGUOUS@checklist-0.81.0 `accounting:241:1`） |
| 16 | 暂存 25 文件逐 diff 过目（AI 专项/范围纪律面） | 版本投影/标记/模板 = 纯版本字面量 1↔1 替换；契约/manifest = 3+1 note；三件套/CHANGELOG/审查报告/0.82.0.json = 新增文档；`test_change_triage.py` +14/−1 = 日期时钟源修复（review-FIX-324-326-CODE-R0 已审 APPROVED_WITH_NOTES/0）；**暂存面内零产品逻辑变更** |
| 17 | 717-721 双赋值结构溯源 | `git show HEAD:` 同区域比对 ⇒ `REQUIRED_SNIPPETS = {}` + `.update()` ×2 被 L721 字面量重绑定覆盖的结构**窗口前既有**（0.81.0 期已存在），非本窗引入 |

---

## 1. 审查维度逐项结论（任务书维度 1~6）

### 维度 1：版本一致性 — **不通过（F-02；钉面 T3 已绿但模板标记面缺失 + 修复未入暂存）**

- 权威源 `SKILL.md:3` = 0.82.0；15 投影机械校验 PASSED（#9）；hooks `@version` ×4 = 0.82.0；REQUIRED_SNIPPETS 6 钉 = 0.82.0（T3 时点，`"0.81.0"` 全文件 0 处、`"0.82.0"` 恰 6 处）。
- **FAIL 实录（T1）**：候选暂存面（25 文件）**不含** `verify_workflow.py` ⇒ 6 个版本钉仍 0.81.0 ⇒ Gate 1 `FAILED — 1 mismatch(es)`（exit 1）。审查中途该钉与 root `AGENTS.md` 标记以**未暂存**形态被并发修复（T3 复跑 PASSED）——但**按现暂存 index 提交候选 = Gate 1 必然复发 FAIL**（F-02a）。
- **模板标记面缺失（F-02b）**：`commands/governance-init.md`（root + e2e 镜像）`@bootstrap-version` 仍 **0.81.0 ×6 面**（L197/262/533 同位），`project/e2e-test-project/CLAUDE.md:5` 仍 0.81.0。机检零覆盖：`check-version-consistency` 标记面仅 root `AGENTS.md`/`CLAUDE.md`（其输出自证 `+ bootstrap markers (AGENTS.md, CLAUDE.md)`），15 投影契约亦不含模板标记面 ⇒ 陈旧模板只被测试（L15066 动态断言，实测红 `0 != 3`）与 FIX-238.2 会话自升级兜底。0.81.0 先例同面（commands/governance-init.md ×3 + e2e 镜像 ×3）当时全部同步，本批**未同步 = bump 不完整**。
- plan-tracker 工作流版本 WARN：预期过渡态（M-8 清除），**合规**（0.81.0 R0 F-06 同型，不重复立案）。

### 维度 2：窗口完整性 — **通过（14/14 闭合；构成披露如实）**

- `e376ddf..HEAD` = 14 commits，与 checklist Change Inventory 14 行逐行一致（#2）；CHANGELOG [0.82.0] 任务清单覆盖 plan-tracker 0.82.0 承载行全部任务 ID（FIX-339/312/313/314/320/322/323/324/325/326/332/333/336/337/341/342/343/344/345/346 + REL-078 + RISK-050 披露），无遗漏/多报。
- FIX-338 三 commits 不在 CHANGELOG [0.82.0] 任务清单（其归属 = 0.81.0 发布后收口、REVIEW-REL-077-RELEASE-R3 已审），但 checklist Change Inventory 行 1~3 + rollback-plan 区间构成**如实披露兜底** ⇒ 无静默遗漏（P3 观察见 F-05）。

### 维度 3：契约面 — **通过**

- 契约 SHA 复算 = checklist Gate 12 预检值逐字符一致（63B28311…DF2 / 75331 B，#4）；契约变更 = 恰 3 note（#5，FIX-326③ 范围精确）；K-2 契约外字面量 **0**（#11）；28w 全 K 面 PASS。与已入库的 review-FIX-324-326-CODE-R0（APPROVED_WITH_NOTES/0）独立实测互证。

### 维度 4：回归面 — **不通过（F-03；红基线状态相对 850-OK 声明发生翻转）**

- 850 口径实测：`Ran 850 tests, FAILED (failures=4)`（#14）——**非全绿树**。4 失败逐条归因：
  - ① bootstrap 模板标记红 → F-02b（bump 不完整的直接后果，归因确定）。
  - ②③④ FIX-320 族 3 条（checklist Gate 10 明细原文：「预期不再出现，若出现即真回归」）→ 一阶归因：**非 FIX-320/322/345 引擎面回归**（live 实跑证明 4 条豁免照常生效、语义 finding 集合无新增、身份门禁引擎代码面完好），而是 loop-claims 语义 verdict 被 **1 条 accounting finding（review-FIX-333-CODE-R0.md ragged table）**压至 BLOCKED/FAIL ⇒ 3 个以 `PASS` 为期望的测试连坐转红。CHANGELOG 如实披露①已知此 ragged 项并声明「不阻断」，但该判定与 checklist Gate 15「语义面双模式全绿预期」**互斥**（见 F-03）。
  - 与 EVD-1059「850 OK exit 0（2026-09-17 混合工作树）」的关系：ragged 项所在文件 2026-09-16 落库未变，而 850-OK 实测在其后一日 ⇒ 触发机制存在「M-0 文档入树改变 accounting 边界解析」与「基线时点差异」两种候选，**本次未定谳**——按 checklist Gate 10 明细自带的 pristine 隔离 worktree 对照程序由 M-2 裁决（标注：待验证）。
- discover 计数：全量 **3200**（B-7 口径吻合）/ 模块 **850** ✅。archguard：**24453 锚恒等 + R7 committed==fresh True** ✅（#10）。

### 维度 5：发布文档代码面一致性 — **不通过（F-01 P0；其余事实面可验证）**

| 文档事实 | 实测 | 裁决 |
|---|---|---|
| 契约 SHA（checklist Gate 12：63B28311…DF2/75331B） | 逐字符一致（#4） | ✅ |
| 契约 0.81.0 基线（rollback §1/§4：96F92485…43FC6E/74702B） | review-FIX-324-326-CODE-R0 双 blob 导出独立证实 | ✅ |
| archguard 锚 24453（Gate 6） | R1 PASS 24453≤24453 + R7 True（#10） | ✅ |
| Check 28w PASS / 0 failing（Gate 7） | 实跑一致（#11） | ✅ |
| discover 计数 3200/3193 口径（Gate 10 注记） | FULL=3200 精确一致（#13） | ✅ |
| 回滚区间锚 e376ddf | rollback-plan §区间锚定/§2.1 = `e376ddf..<发布 tip>` ✅；**checklist Gate 14 行 = `845c050..<发布 tip>` ❌** | ❌ **F-01** |
| Gate 10 明细「FIX-320 族 3 条若出现即真回归」 | 3 条实测出现，且一阶归因为非回归（见维度 4） | ❌ **F-03** |
| Gate 15「语义面双模式全绿预期」 | 双模式实测 exit 1/BLOCKED（#12） | ❌ **F-03** |
| 棘轮 84/84 + 71/71 不变（feature-flags §3） | R5 PASS 实证 | ✅ |
| 占位纪律（checklist L3/L142：冻结前 ⟦⟧ 全消除） | L47/L48 行、CHANGELOG L21 仍 ⟦待回填⟧（自指 hash 类） | ⚠️ F-04 |

### 维度 6：AI 专项 + 范围纪律 — **通过**（见 §3、§4）

---

## 2. 发现列表

### F-01 — **P0（阻塞）** — checklist Gate 14 回滚区间锚写错：`845c050..<发布 tip>`，与 rollback-plan 勘误后的 `e376ddf..<发布 tip>` 直接矛盾

- **位置**：`docs/release/release-checklist-0.82.0.md:81`（Gate 14 预期列）；矛盾对象 `docs/release/rollback-plan-0.82.0.md:18/24/50/92`
- **事实依据**：rollback-plan「区间锚定」节以整整一段勘误注记（L24）论证「以 `845c050` 为起点的区间**不覆盖已落库的 0.82.0 载荷**（`8bd6a8a..845c050` 共 11 commits），按该区间 revert 将留下全部 0.82.0 引擎改动、回不到 0.81.0 行为」，并明确「REL-078 M-0 任务书原文将区间写作 `845c050..<发布 tip>`」系 0.81.0 R0 **F-01 同形错误**；而 checklist Gate 14 行仍写「回滚区间 = 整个 0.82.0 窗口 `845c050..<发布 tip>`」——该行自述的「整个 0.82.0 窗口」与同一文件 L29 的 Change Inventory 窗口定义（`e376ddf..845c050`）亦自相矛盾。
- **影响**：Gate 14 是 M-2 门禁项且预期列即按此措辞裁决「已交付且可执行」；按 Gate 14 行执行 `git revert --no-commit 845c050..<发布 tip>` 将**留下全部 11 个 0.82.0 载荷提交**（版本锚参数化/归档判据/豁免账本/authority 重锚等全部保留）——与 0.81.0 R0 F-01（P0）完全同形。
- **修复建议**：Gate 14 行改为 `e376ddf..<发布 tip>`（其余措辞不动），与 rollback-plan 对齐；一行文本修复。

### F-02 — **P1（关键，M-2 前必达）** — M-1 bump 批标记/钉面不完整：(a) 钉修复未入暂存；(b) bootstrap 模板标记面 ×7 陈旧；(c) 该面机检零覆盖

- **位置**：(a) `skills/.../infra/verify_workflow.py`（REQUIRED_SNIPPETS 6 钉）+ `AGENTS.md:5`（均为**未暂存**工作树修改）；(b) `commands/governance-init.md:197/262/533` + `project/e2e-test-project/commands/governance-init.md` 同位 ×3 + `project/e2e-test-project/CLAUDE.md:5`；(c) `checks/version.py` 标记面覆盖定义（仅 root AGENTS/CLAUDE）
- **事实依据**：(a) T1 实跑 Gate 1 FAIL（`verify_workflow.py snippet: hardcoded version mismatch`，exit 1）→ 审查中途并发落盘未暂存修复（diff 实测 = 恰 6 钉 0.81.0→0.82.0 + AGENTS.md 标记 1 行）→ T3 复跑 PASS；**暂存 index 两次读取均不含此二文件**（#3）⇒ 按现 index 提交候选 = Gate 1 复发。(b) 模板面 7 处仍 0.81.0（my Select-String 实录）；`test_bootstrap_version_marker_injected_into_all_profiles`（test_verify_workflow.py:15066-15082）动态断言 `> @bootstrap-version: {frontmatter版本}` 恰 3 次，实测 **`AssertionError: 0 != 3`**。(c) `check-version-consistency` 输出自证标记面只查 root 两文件；15 投影契约（release_projection_contract）不含 commands/governance-init.md 模板面 ⇒ 该面纯手工同步且无守卫（0.81.0 R0 §3.2「成员不对称」P3 的延伸实例）。
- **影响**：Gate 1（M-2）不可能在模板面缺失下 PASS；850 套件恒红 ≥1；陈旧模板随版本发布，新 init 项目注入 0.81.0 bootstrap（仅靠 FIX-238.2 会话期自愈兜底）。
- **修复建议**：(a) 将 `verify_workflow.py`（6 钉）与 `AGENTS.md` 并入候选暂存面；(b) `commands/governance-init.md` ×2 镜像共 6 处模板标记 + `project/e2e-test-project/CLAUDE.md:5` 同步 0.82.0（0.81.0 先例同面同法）；(c) 登记「模板标记面纳入机检」候选（DEC/任务池，非本版义务）。

### F-03 — **P1（关键，发布前必达）** — 红基线状态翻转：850 = 4 failures，loop-claims 双模式 BLOCKED，与 checklist Gate 10/15 预期及 CHANGELOG「不阻断」判定互相矛盾；根因项 = 已披露的 ragged-table accounting 项，触发链未定谳

- **位置**：`docs/release/release-checklist-0.82.0.md:86`（Gate 10 明细）、`:82`（Gate 15 预期）、`project/CHANGELOG.md:34`（如实披露①）；`docs/reviews/review-FIX-333-CODE-R0.md`（ragged table 所在报告）
- **事实依据**：① 850 实测 4F（#14），其中 ②③④ = Gate 10 明细自述「若出现即真回归」的 FIX-320 族 3 条；② live 双模式实跑（#12）：4 条账本豁免全部生效、语义 finding 集合无新增（3U+1A 恰为账本族）、唯一未豁免 finding = `ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY: ragged table row` @ review-FIX-333-CODE-R0.md，`verdict: BLOCKED`/exit 1 ⇒ 一阶归因**非身份门禁引擎回归**；③ CHANGELOG 如实披露①已知该 ragged 项并声明「随批披露、不阻断」，但该 finding 在引擎侧即 semantic verdict=BLOCKED 的**唯一在案驱动项**，与 Gate 15「installed_host PASS / 0 findings」全绿预期不可同时成立；④ 该报告文件 2026-09-16 落库后未变，而 EVD-1059 记 850 OK exit 0 于 2026-09-17 ⇒ 「M-0 文档入树改变 accounting 边界解析」vs「基线时点差异」两候选机制未定谳。
- **影响**：M-2 Gate 10/15 若按现预期列执行即 FAIL；若按 CHANGELOG「不阻断」披露放行，则 Gate 15 预期文字失真——两份交付物对同一事实给出不可同时成立的口径，且 3 个红测试以「真回归」字样悬挂，阻塞发布裁决。
- **修复建议**：按 checklist Gate 10 明细自带程序执行 **pristine 隔离 worktree（`git worktree add --detach` @ 845c050）同命令对照**，定谳 ragged 项触发链；随后二选一：(i) 经受审路径消解该 accounting 项（使双模式回绿，Gate 10/15 预期成立）；或 (ii) 如实改写 Gate 10 明细与 Gate 15 预期（披露「语义面 = BLOCKED by 已披露 accounting 基线项 + 3 测试连坐红」的口径，与 CHANGELOG 对齐）。**在定谳前不得将 ②③④ 写成「真回归」或「既有基线」任一结论。**
- **待验证**：ragged 项在 850-OK 基线时点是否已存在（本次只读约束下未做 pristine 对照——见 §6 未验证声明）。

### F-04 — **P2（建议，M-1 冻结时处理）** — 自指 commit hash 占位以 ⟦待回填⟧ 形态存在，与冻结纪律字面冲突

- **位置**：`docs/release/release-checklist-0.82.0.md:47/48`（Change Inventory ⟦15⟧/⟦16⟧ 行）；`project/CHANGELOG.md:21`（`commit hash ⟦M-1 冻结回填⟧`）
- **事实依据**：checklist L142 冻结纪律要求「M-1 冻结前 MUST 消除本清单全部 ⟦待回填⟧/⟦待落地⟧ 占位」并列名「M-0 批 commit hash、候选打包 commit」；但候选打包提交无法自含自身 hash（0.81.0 先例已裁决为「无法自指的合理安排」，处理法 = 以「M-2 期由 `release-ledger` 派生回填」**文字声明**替代 ⟦⟧ 标记——0.81.0 review §3.4 在案）。
- **影响**：若按字面执行冻结纪律则不可能满足；若保留 ⟦⟧ 原样落库，则冻结纪律对自身交付物失真。
- **修复建议**：M-1 冻结提交时将三处占位改写为 0.81.0 先例式文字声明（保留 hash 回填义务于 M-2）。

### F-05 — **P3（讨论）** — CHANGELOG [0.82.0] 不含 FIX-338 三 commits；由 checklist/rollback 构成披露兜底

- **位置**：`project/CHANGELOG.md` [0.82.0] 段；对照 checklist Change Inventory 行 1~3、rollback-plan L22
- **事实依据**：FIX-338（`1db58f5`/`02ad554`/`dfafa95`）物理在 e376ddf..窗口内，CHANGELOG [0.82.0] 段任务清单未列（其审查链属 REVIEW-REL-077-RELEASE-R3）；checklist 与 rollback-plan 已如实登记构成 ⇒ 非静默遗漏。
- **建议**：CHANGELOG 侧可加一句「窗口含 FIX-338 发布后收口 3 commits（见 release-checklist Change Inventory）」以便单文档读者；非必须。

### F-06 — **P3（讨论，窗口外既有）** — `verify_workflow.py` L717-719 dead-store：`REQUIRED_SNIPPETS = {}` + 双 `.update()` 随即被 L721 字面量重绑定丢弃

- **事实依据**：`git show HEAD:` 同区域比对证实该结构 0.81.0 期已存在（窗口外、非本批引入）；现行生效面 = L721 字面量（版本钉实测即在其中）。
- **建议**：后续引擎清理批顺手消除（删 717-719 或让 update 语义生效前先核对 `WORKFLOW_SNIPPETS`/`PROJECTION_SNIPPETS` 的其他消费方）；本版不动。

### F-07 — **P3（讨论）** — 审查期间工作树被并发修改（M-1 收尾在飞）

- **事实依据**：T0 暂存面 = 25 文件；审查中途新增 2 个**未暂存**修改（`verify_workflow.py` 6 钉 + `AGENTS.md` 标记）与磁盘上 root `CLAUDE.md`/`AGENTS.md` 的 0.82.0 自升级面（会话 bootstrap 自升级行为）；暂存 index 两次读取一致（#3）⇒ 被审暂存面未被污染；T1→T3 的 Gate 1 翻转即由该并发修复引起（F-02a 证据链）。
- **影响/建议**：同 0.81.0 R0 F-07——M-2 门禁测量前应固定一次干净快照（冻结提交），避免复审对象漂移。

---

## 3. AI 代码专项 5 项（对暂存 25 文件 + 2 并发修改文件）

| # | 检查项 | 结论 |
|---|---|---|
| 1 | mock 残留 | **未发现**。暂存面无测试 mock/stub；`test_change_triage.py` 修复为真 subprocess + 同源真实时钟（已审报告 F-1 仅登记午夜竞态 P3） |
| 2 | 硬编码返回值 | **未发现缺陷**。版本字面量为投影/钉契约的期望值面（既有契约设计）；日期修复恰是**移除**硬编码日期 |
| 3 | 幻觉 API 调用 | **未发现**。投影/模板/钩子 = 纯字面量 1↔1；契约 3 note 措辞与 `dsh_doctor.py`/DEC-193 实现逐点核实（review-FIX-324-326 §1/§2 独立实证在案，本审查抽核一致） |
| 4 | 未实现 TODO | **代码面未发现**。文档 ⟦⟧ 占位全部属 M-2/M-5 回填协议允许面，自指 hash 类见 F-04 |
| 5 | 过度实现 | **未发现**。25+2 文件全部映射发布面职责（投影 15 + 权威源 1 + 契约/manifest 2 + 发布文档 4 + 审查报告 1 + ledger 1 + 测试修复 1 = 25 ✅ 闭合；+2 = 并发钉/标记修复），无顺带重构、无越界 |

**反向检查（是否漏改）**：15 投影 ✅、hooks ×4 ✅、权威源 ✅、6 钉 ✅（T3）、root 标记面 ✅；**漏改面 = F-02b 的 7 处模板/镜像标记**（已立案）。

## 4. 范围纪律（窗口外零触碰）

- 窗口内 14 commits 均有独立机录审查链（checklist Change Inventory 逐行核对）；暂存 25 文件全部属于发布承载面，未发现窗口外产品逻辑触碰；审查期间全仓状态变化仅 F-07 所列 2+磁盘标记文件，均属发布面。
- 本审查自身：仓库内唯一写入 = 本报告；引擎命令全部以 `$tmpHome`（%TEMP% 下 guid 目录）隔离 DSH_HOME；套件日志/引擎 JSON 输出全部落 %TEMP%；未安装/未卸载/未写真实环境任何路径。

## 5. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **1**（F-01） | ❌ 未通过 |
| 5 维度全覆盖 | = 100% | 正确性❌（F-02/F-03）/ 安全性✅ / 可维护性✅（F-04/F-06 建议）/ 性能✅（无算法面变化；archguard/预算断言面全绿）/ 测试覆盖❌（F-02b 红 + F-03 4F） | ✅ 5/5 有结论 |
| 每条发现标注级别 | = 100% | 7/7 带 P0~P3 | ✅ |
| 设计一致性检查 | 已完成 | 已完成（§1 维度 5 表：9 项验证，3 项偏离） | ✅ |
| AI 专项 5 项 | 全部完成 | 5/5 有结论（§3） | ✅ |

安全性维度说明：无输入处理/注入/凭据面变化；契约 note 更正实为安全属性文档化（单一事实源防未审机变）；hooks 改动仅在 `@version` 注释行。

⇒ 硬门槛未全通过（P0 = 1）→ **结论 NEEDS_CHANGE（R0）**。

## 6. 结论与处置要求

**结论：NEEDS_CHANGE**（`unresolved_blockers=1`，P0×1）

- **阻塞项**：**F-01**（P0，checklist Gate 14 回滚区间锚——一行修复）。
- **M-2 前必达（不阻断本报告归档，但阻断 M-2 正确性）**：**F-02**（钉/标记面补全 + 入暂存）、**F-03**（pristine 对照定谳 + Gate 10/15 预期与实际口径对齐）、**F-04**（冻结提交时占位文字化）。
- **建议/讨论**：F-05、F-06、F-07。
- **复审要求（M7.4）**：修复后 Coordinator 重 spawn 本 Reviewer 执行 **R1**；R1 MUST：① 逐条比对 F-01/F-02/F-03/F-04 修复状态（已修复/未修复/新引入）；② 复跑 Gate 1/projection-sync/28w/archguard 与 850 套件（预期 0 failures 或披露后的披露态基线）；③ 核对 F-03 的 pristine 对照结论与 Gate 10/15 改写后的口径一致性；④ 若模板标记面机检缺口已立 DEC/任务，核对登记在案。

**聚合面单独结论**：14 个窗口 commits 的独立审查链完整可信（逐行核对在案）；版本投影/契约/账本/棘轮/28w 机械面**经本审查实跑全部吻合声明**；阻塞集中在**发布文档事实面（F-01）与 bump 完整性/门禁预期口径（F-02/F-03）**——修复成本为一次模板同步 + 数行文本 + 一次 pristine 对照，无产品代码返工。

---

## 7. 命令上报（只读；工作目录 = 仓库根；DSH_HOME 逐命令 `$tmpHome` 隔离）

| # | 命令 | 退出码 | 输出摘要 |
|---|---|---|---|
| 1 | `resolve_entry.py --json` | 0 | resolved_root_ok=true，active_version=0.82.0，hooks 全装 |
| 2 | `git log e376ddf..HEAD --oneline` / `rev-list --count` / `log -1 e376ddf` | 0 | 14 commits；e376ddf = 0.81.0 transition |
| 3 | `git status --porcelain` ×2 / `git diff --cached --stat` ×2 | 0 | 暂存 25 文件两次一致；中途新增 2 未暂存（F-07） |
| 4 | `git diff --cached --numstat`（全量）| 0 | 25 文件 +498/−21；25 文件闭合核算 ✅ |
| 5 | `Get-FileHash host-contract.json SHA256` + Length | 0 | 63B28311…DF2 / 75331 B |
| 6 | `git diff --cached -U0 -- host-contract.json / adapter-manifest.json` | 0 | 恰 3 note / 1 note |
| 7 | `verify_workflow.py check-version-consistency`（T1） | **1** | FAILED — 1 mismatch（snippet 版本钉） |
| 8 | `verify_workflow.py check-projection-sync --fail-on-issues`（T1/T3） | 0/0 | PASSED ×2 |
| 9 | `Select-String '"0\.81\.0"' / '"0\.82\.0"'`（verify_workflow.py） | — | 0 处 / 6 处（T2 时点） |
| 10 | `verify_workflow.py archguard-ratchet` | 0 | R1~R7 全 PASS，24453 恒等，R7 True |
| 11 | `verify_workflow.py check-dsh-boundary` | 0 | PASS 0 failing；K-2 literals 0 (11 consumers)；K-7 NOT_RUN |
| 12 | `verify_workflow.py check-version-consistency`（T3 复跑） | 0 | PASSED（1 条预期 WARN） |
| 13 | `git diff -- verify_workflow.py / AGENTS.md`（未暂存） | 0 | 恰 6 钉 + 1 标记行 |
| 14 | TestLoader discover ×2 | 0 | FULL=3200 / MODULE=850 |
| 15 | `python -m unittest discover -p test_verify_workflow.py` ×2（第二次全量落盘 %TEMP%） | **1**/1 | Ran 850, FAILED (failures=4)，198.694s；4 失败块逐条取证 |
| 16 | `verify_workflow.py check-loop-runtime-claims --scan-mode installed_host / product_release`（×3 次取字段） | **1** | 双模式 BLOCKED/exit 1；exemptions_applied=4；findings=1（ragged @ review-FIX-333） |
| 17 | 豁免账本读盘 + loop-claims `-h`（CLI 形态确认） | 0 | 4 条九键与文档一致；`--scan-mode` 参数形态 |
| 18 | 暂存小 diff 全量过目 + e2e plan-tracker diff + 标记面 Select-String + `git show HEAD:` L715-723 + `git check-ignore CLAUDE.md` | 0 | 纯版本字面量；模板面 0.81.0 ×7；双赋值结构 HEAD 既有；CLAUDE.md gitignored（.gitignore:3） |

**未执行的命令（只读约束主动不执行）**：`check-hot-fact-source` 活体、`check-release`/`release-ledger`、`--regen`、28u/28v、`check-injection-contract`、`test_loop_runtime_claims`（60 口径）、pristine 隔离 worktree 对照（属 M-2 程序义务，`git worktree add` 为写操作）、任何 `git add/commit/restore/stash`。

## 8. 未验证 / 待验证声明

1. **F-03 触发链机制**（ragged 项在 850-OK 基线时点是否已在）——待验证，交 M-2 pristine 对照；本报告未写成任何一侧结论。
2. **未独立复跑**：Gate 3/4/5/8/9/9b/13 各门禁与 60-loop 套件（M-2 义务；其中 9b 的 `[OK] agent adapter contracts synchronized` 仅以套件日志随行输出为旁证）。
3. **并发修改归属**：F-07 的 2 文件修复 + root 标记面自升级系审查期间他人/他会话在飞动作，本审查仅记录状态时序，不归属责任方。
4. 套件日志含 GBK 控制台 mojibake（仅中文断言消息显示层），不影响失败判读（traceback 关键行均 ASCII/可读）。

—— Code Reviewer，R0，2026-09-18
