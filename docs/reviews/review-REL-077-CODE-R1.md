# REVIEW-REL-077-CODE-R1 — 0.81.0 M-1 退回项（FIX-329）复审

**结论：APPROVED_WITH_NOTES**（`unresolved_blockers=0`；P0 = 0 / P1 = 1〔登记遗留，关闭截止 = M-2 Gate 11 回填前〕/ P2 = 4 / P3 = 3）

- **Round**：**R1**（第 2 轮）；**前轮引用 `prev_report=docs/reviews/review-REL-077-CODE-R0.md`**（R0 = NEEDS_CHANGE / `unresolved_blockers=1`，P0×1 = F-01）。
- **复审义务履行声明（M7.4 step 4.6）**：本报告**先通读 R0 全文**（291 行），再逐条比对 F-01~F-07 的修复状态，**未**跳过前轮直接 APPROVED。
- **审查对象（FIX-329 变更面）**：`git diff`（**index→worktree**，对照 HEAD `5e6d8c71a2dad19c8cff3b720fbe7a99bae83629`）= **5 文件 / +23 −17**：`README.md`(4±)、`docs/release/feature-flags-0.81.0.md`(10±)、`release-checklist-0.81.0.md`(6±)、`rollback-plan-0.81.0.md`(18+6−)、`version-plan-0.81.0.md`(2±)；另新增**未跟踪**文件 `skills/software-project-governance/core/releases/0.81.0.json`（494 B，candidate 态 manifest）。
  - 状态细节：其中 checklist / rollback-plan / version-plan 为 `MM`（R0 批已暂存 + FIX-329 在其上再改）⇒ 本报告读的是 FIX-329 的**增量**（index→worktree），R0 已核的 R0 批内容不作为本轮结论依据。
- **写入范围声明**：本报告是本次审查**唯一**写入文件；未修改任何被审文件、未执行任何写操作命令、未触碰 `$env:USERPROFILE\.dsh` / `$DSH_HOME` / 仓库外路径、未执行 `git add/commit/restore/reset/checkout/stash`。
- **报告路径说明**：与 R0 一致——本仓库既有审查归档目录 `docs/reviews/`（角色定义默认 `.governance/review-{task_id}.md`；本轮以 Coordinator 任务规范指定路径为准）。

---

## 0. 独立复现声明（我亲自复算/复核的数字与文件）

| # | 我亲自复核的内容 | 结果 |
|---|---|---|
| 1 | `git rev-list --count d87ead8..3074120` | **31**（两次读取一致）⇒ 新文档「31 commits」成立 |
| 2 | `git rev-list --count 71f73eb..3074120` | **32** ⇒ 与 R0 的 F-01 依据一致（`d87ead8..3074120`=31 = 该 32 减去 `d87ead8` 自身） |
| 3 | `git merge-base --is-ancestor 71f73eb d87ead8` / `3074120 HEAD` / `d87ead8 HEAD` | 均 **exit 0** ⇒ `v0.80.0`(`71f73eb`) 是区间起点祖先；两个端点都在本分支历史内 |
| 4 | `git rev-list -n1 v0.80.0` / `v0.79.0`；`git tag -l` | `v0.80.0` → **`71f73ebcf837a5c52eb201866f8ce5adb66aee4f`**（与 README 新表述「peels to `71f73eb`」一致）；`v0.79.0`/`v0.80.0` 本地均存在（`tag -l` 共 100 个 tag） |
| 5 | 全 0.81.0 发布文档的 40 位 hex 扫描 | **未发现任何编造的候选打包 commit hash**；`<0.81.0 候选打包提交>` 以显式占位 + 「不预先编造」声明呈现（R0 修复建议所允许的形态） |
| 6 | `61b571c` / `3074120` 在 0.81.0 文档中的**全部**出现（逐条读） | 均为「V8/V10 终态 commit」「Change Inventory 行」等**正确用法**；**未发现**旧「回滚区间 = 这 2 个提交」表述的任何残留 |
| 7 | 占位符普查（`⟦`）：feature-flags / rollback-plan / version-plan / real-machine-acceptance / README / CHANGELOG | **各 0 处**；checklist 13 处（L74-82 Gate 1~9、L85-86 Gate 12~13、L92 真机回贴、L112 纪律字面引用）——**全部落在 R0 定义的允许面** |
| 8 | `feature-flags-0.81.0.md` 状态行与结尾 | 已从「M-1 草稿」改为「**M-1 冻结**」；`⟦待 V8 回填⟧` **0 处**（余 2 处为「该占位已补齐」的叙述性引用） |
| 9 | 段号 `28w` 真伪：`registry.py:412` `("28w", "checks.dsh_boundary.emit_check_section")`；`quickscan_registry.py:554` `SegmentSpec("28w", ...)` | ✅ 与文档一致 |
| 10 | 棘轮口径 `84/84 + 71/71`：静态计数 `registry.py` `_COMMANDS`（L233–347）= **84**、`_SEGMENT_LOADERS`（L354–424）= **71**；冻结面 `infra/contract_matrix/snapshots.json` `faces.cli_dispatch.keys` = **84**（含 `check-dsh-boundary` / `dsh-doctor`）、`faces.check_segments.ids` = **71**（含 `28w`/`28u`/`28v`）；`test_registry.py:80-81` `FROZEN_CLI_KEYS = 84` / `FROZEN_SEGMENTS = 71` | ✅ 三处互证 |
| 11 | `--offline` 适用域逐阶段对照 `dsh_doctor.py` 代码 | **S2** L520-533（`--offline: Check 28v needs node …` + `re-run without --offline`）、**S4** L866-876（parity 半边 `--offline` → NOT_RUN，Python 半边仍出 sha256）、**S6** L1083-1087（`--offline: the isolated smoke starts a subprocess …`）、**S5** L1000-1010（默认 NOT_RUN，理由含「host entry plane has no offline path (T-2 untouched)」+ M7.7 三选一 remediation）；K-12 比较域 L1283-1292/L1315-1316（`"compared": (not offline) and all(...)`）⇒ ✅ 与文档逐条相符 |
| 12 | 退出码三态 | `dsh_doctor.py:45`「`2` = refused (isolation guard, unauthorised host probe, usage error)」+ L102 `EXIT_REFUSED = 2` + L1333「`0` no FAIL, `1` some FAIL」⇒ 新增的「`2`=REFUSED」是**代码事实**（旧稿「`2`=不可判定：环境缺失」为错，已更正） |
| 13 | `unreadable_compositions` 的机检：`checks/dsh_boundary.py:1801`（`check_dsh_preset_compat` 唯一生成点）+ L1807-1814（缺 `unreadable_compositions` ⇒ K-12 FAIL）+ L1831-1836（PASS 文案） | ✅ K-12 确实机检该字段 |
| 14 | manifest `0.81.0.json` 与 candidate 先例 **逐字节**比对 | 与 `git show 8d9110c:…/0.79.0.json` 在「`0.79.0`→`0.81.0`」归一化后**完全相等**（同一 494 B 结构）；键序、单行 JSON、`CR=0 / LF=1 / 尾 LF` 与 0.78.1/0.79.0/0.80.0 **四个既有 manifest 同构** |
| 15 | 候选 manifest 的 git 事实 | `git ls-files` **无输出**（未跟踪）、`git log -- <该路径>` **无输出**（0 个提交添加该路径）⇒ ledger 的 `found 0` 是机械必然而非异常 |
| 16 | ledger 判定逻辑 | `release/ledger.py:184-191`（`git_commit_adding_path` → `commit_adding_path`）+ L431-443（`trust_level` 由 `lifecycle_state` 独立推出：`candidate`⇒`NATIVE_CANDIDATE`；`candidate_commit` 另行解析）⇒ 「FAIL + NATIVE_CANDIDATE」并存的构造成立 |
| 17 | 文档引用的命令/路径是否真实存在 | `verify_workflow.py:23559` `ledger_p.add_argument("--no-remote", …)` ✅；registry `check-dsh-boundary` 命令键 ✅（`registry.py:256`）；被引文件 4 个全部存在 ✅ ⇒ 无幻觉 API |
| 18 | R0 F-04 的「证伪」方向是否站得住 | 亲自读两测试体：`test_verify_workflow.py:14681-14697`（FIX-256 动态读 frontmatter 版本）、`test_review_machine_provenance.py:218-225`（断言锚 + `issues == []`）——**两测试体内不含任何版本字面量** ⇒「版本钉过期致其失败」在机制上不成立，checklist 的更正方向可静态印证 |
| 19 | FIX-328 修复事实 | `git diff -- test_triage_write_guard.py` = **1 文件 +21/−1**（与 Gate 10 所述一致）；`docs/reviews/review-FIX-328-CODE-R0.md:55` 记 `Ran 32 tests / OK (skipped=1)`、L17 = `APPROVED_WITH_NOTES`；plan-tracker:100 = ✅ 完成 + **遗留 F-1/F-2(P2)、F-3/F-4(P3) 返工批** |
| 20 | README 改动面 | 仅 **2 处**（L92、L442）；L393（R0 列出的第 3 行）内容与 HEAD **逐字相同**，为历史文档引用、**无 tag 状态陈述**；`RISK-049` 披露与隔离验收措辞行**未被触碰** |
| 21 | 被审面指纹稳定性（F-07 复核） | 会话初与收尾两次 `git diff` 头 blob 索引**完全一致**（README `39e0b76..e3793e3`、feature-flags `15a8367..58ceebc`、checklist `b77b048..90615e6`、rollback `9288ff6..327934d`、version-plan `b27748e..b3d2395`），`--stat` 两次均为 5 文件 +23/−17 ⇒ **被审面未被并发写入污染** |

**收尾 sha256 快照（供后续复核）**：`README.md` `B16A7C178C1E26D3…`(54307 B)、`rollback-plan-0.81.0.md` `5A18C6A882615711…`(7781 B)、`release-checklist-0.81.0.md` `DA5FE2EEA0D7F8F3…`(24809 B)、`feature-flags-0.81.0.md` `EF4566FEDDE95C8D…`(5966 B)、`version-plan-0.81.0.md` `AA62FD9BA1EAA5E8…`(18040 B)、`core/releases/0.81.0.json` `F1A57CC84879BDEF…`(494 B)。

---

## 1. R0 findings 逐条比对（已修复 / 未修复 / 新引入）

| ID | R0 级别 | R0 内容 | R1 裁决 | 事实依据（本轮实测） |
|---|---|---|---|---|
| **F-01** | **P0** | 回滚区间把 32 提交写成 2 个（`61b571c`+`3074120`） | **已修复** | ①三个位置（`rollback-plan:3`、`:26-33`、`:87`；`checklist:87`）均已改为 `d87ead8..<0.81.0 候选打包提交>`；②「实测 `d87ead8..3074120` = 31 commits，加候选打包提交本身」= 我实测计数 **31**（§0-1）自洽；③V8/V10 明确标注「仅为区间末两个代表性交付，**不是**区间本身」；④与自身口径自洽：`:5` 回滚目标=0.80.0 行为、`:60` §4 验证 1=版本声明回到 0.80.0、`:65` §4 验证 6=基线实测于 `d87ead8`（区间起点）；⑤**未编造 hash**（§0-5：全 0.81.0 文档 40 位 hex 扫描无新增项，占位 + 「本文件不预先编造该 hash」显式声明）；⑥全文档**无**旧 2-commit 区间残留（§0-6） |
| **F-02** | **P1** | feature-flags 仍「M-1 草稿」+ 5 处 `⟦待 V8 回填⟧` | **已修复** | ①状态 = **M-1 冻结**，`⟦` = **0**（§0-7/8）；②回填内容**与实测一致**：段号 `28w` ✅（registry.py:412 + quickscan_registry.py:554）、棘轮 `84/84 + 71/71` ✅（三处互证，§0-10）、`--offline` 适用域 S2/S4/S6 + S5 ✅（逐阶段代码对照，§0-11）、退出码 `2`=REFUSED ✅（§0-12）、`unreadable_compositions` 由 K-12 机检 ✅（§0-13）；③§2 的 B-1/B-2 **未被触碰**（本批 hunk 仅覆盖 L1-6 / L22-26 / L37-44，§2 = L12-19 无 hunk） |
| **F-03** | **P1** | Gate 10 未冻结本批回归与既有失败分类 | **已修复** | ①期望列已从「无新增失败」改为「**零产品代码回归（既有失败基线如实披露，不得写无条件 PASS）**」；②`failures=38 errors=2` vs pristine `failures=28 errors=9` 与 EVD-1033 原值**逐字一致**（证据源存在）；③差集 +3 自洽（40−37=3）且逐条归因：①活体金丝雀=**真回归→FIX-328 已修**（§0-19：+21/−1 + `OK(skipped=1)` 可追溯）、②两项「版本钉过期」= **经实验证伪的瞬时红**（§0-18：两测试体无版本字面量，机制上可静态印证）、③其余为 pristine 侧噪声且**显式不升级为回归**；④既有失败基线 3 条如实披露（ⓐ2 + ⓑ1 + ⓒ环境敏感类排除）；⑤Result 非无条件 PASS |
| **F-04** | P2 | 3 项失败归因静态不可复现；要求 FIX-328 落地后重跑并贴原始清单 | **已处理**（文档义务落地；本轮按任务规范**未**重跑全量） | Gate 10 行内含 M-2 义务原文：「FIX-328 落地后 MUST 重取一次全量原始失败清单并逐条贴出（REVIEW-REL-077-CODE-R0 **F-04** 要求），门禁结论以该次重取为准」⇒ 义务已冻结进文档。**残留可追溯性问题见 F-R1-06（P3）** |
| **F-05** | P2 | README 对 `v0.80.0` 的陈述过期（称无 tag） | **已修复** | ①「candidate awaiting authorization / no tag exists」表述**已消失**（全文 grep 无命中）；②新表述与事实一致：`v0.79.0`/`v0.80.0` **本地存在**、`v0.80.0` peel = `71f73eb` ✅（§0-4）、0.80.0 于 2026-09-12 发布 ✅（plan-tracker:11）、**未推送** + M-7/§M-8 补推义务交叉引用（checklist:94-97 存在）✅；③README 仅改 **2 处**、其它内容（RISK-049 披露 / 隔离验收措辞）未动 ✅（§0-20）；④R0 列出的第 3 行 `:393` 经核**无 tag 状态陈述**、无需改动（R0 位置清单的 1 行属过量列举，非缺陷） |
| **F-06** | P3 | `check-version-consistency` 含 1 条 plan-tracker `[WARN]`，「all consistent」表述不完整 | **未处理**（如实登记，**不阻断**） | ①`checklist:74` Gate 1 仍为 `⟦待回填⟧（bump 前预检 PASSED）`，**无** `[WARN]` 加注；②`plan-tracker:11` = `工作流版本: 0.80.0`（≠ 权威源 0.81.0）⇒ 该 WARN 在 M-2 仍会复现；③按 code-review 分级 P3 = **不要求修改**，故不构成阻塞；建议在 M-2 回填 Gate 1 时加注（见 F-R1-08） |
| **F-07** | P3 | 审查期间工作树被并发写入 | **登记确认，无污染**（无需修复） | ①被审面两次指纹完全一致（§0-21）；②并发写入仅 2 个文件（`core/architecture-baseline.json`：`generated.git_head` = `5e6d8c7…`；`infra/tests/test_triage_write_guard.py` = FIX-328 的 +21/−1）+ 2 份未跟踪审查报告，**均在本轮被审面之外**；③「基线快照过期」风险已由 Gate 10 的 M-2 重取义务覆盖 |

**新引入回归**：**未发现**。FIX-329 的 5 文件 diff 逐行读完（+23/−17），全部是文档事实/措辞订正与 manifest 新增，无代码/配置面改动、无既有事实被误改（§1 维度 3 与 §4 AI 专项）。

---

## 2. 五维度逐项结论

### 维度 1：正确性 — **通过**（R0 的 P0 已消除，本批事实经独立复核为真）
- F-01 的区间、计数、端点、祖先关系四项全部经我独立复算（§0-1~4）与文档逐字相符。
- feature-flags 的回填事实逐条对照代码验证为真（§0-9~13）——**不是**照抄 Coordinator 自述。
- manifest 与 candidate 先例**逐字节同构**（§0-14/15）⇒ 候选态形态正确。
- 未发现事实性新错误被引入（本批新增的三处事实更正——回滚区间、渲染哈希、Gate 10 分类——均经复核）。
- **扣分项落在「更正不完整」**（F-R1-01：同族陈旧哈希值仍留在验收文档），故本维度判「通过 + 1 项 P1 遗留」，不构成 P0。

### 维度 2：安全性 — **通过（无安全发现）**
- 被审面为纯文档 + 1 个数据文件，无输入处理面、无密钥/凭据/token、无命令注入面、无权限或文件系统写路径变化。
- 回滚方案本身的安全性**未回退**：`rollback-plan:40` 保留「回滚后 `--install` 重新允许写真实 home」的显式告警；`§3 数据安全` 与 `§4` 的隔离限定（`DSH_HOME=%TEMP%` / `real-home writes: 0`）**未被本批削弱**。
- 未出现无限定语的「真实安装 / 真实环境通过」措辞（真机三项仍标 `⟦待用户回贴⟧` / 未验证）⇒ **措辞合规**。

### 维度 3：可维护性 — **通过（附 4 条 P2 改进，均非阻塞）**
- 命名/注释/结构：改动保持原文措辞与表格形态，无重复段落、无超长插入；FIX-329 的遗留修复以「R0 更正」显式标注（`REVIEW-REL-077-CODE-R0 F-01`），可追溯性好。
- 单点事实源原则：回滚区间改为「整窗 + 占位待派生」，避免自指编造——这是本批**最好的设计选择**。
- 改进点：①同族事实的更新未做全仓普查（F-R1-01）；②时序性前置条件未写入文档（F-R1-02）；③一处未限定断言与自身更正文冲突（F-R1-04）；④一处计数与冻结面不符（F-R1-05，预存在）。

### 维度 4：性能 — **通过（无影响）**
- 无算法/数据结构/IO 变化；manifest 494 B、文档合计约 +6 KB 文本，对任何门禁或运行时无可测影响。
- 不影响 `check-release` / `release-ledger` 的读取路径（ledger 仅按路径取 git 事实，见 §0-16）。

### 维度 5：测试覆盖 — **通过（文档批的适用结论）**
- 本批**无产品代码**、不新增/修改测试；测试面结论由既有证据链承载：`review-FIX-328-CODE-R0`（`Ran 32 / OK (skipped=1)`，§0-19）+ EVD-1033（全量原始数值，§0 第 4 条回溯）+ Gate 10 的 M-2 重取义务。
- 与门禁的衔接正确：Gate 10 期望列已改为「零产品代码回归」而非「无新增失败」⇒ 与「候选树非全绿但无本版回归」的真实状态一致。
- **未闭环项**：全量原始失败清单尚未重取（设计上属 M-2 义务，见 F-04 裁决与 F-R1-06）。

---

## 3. 发现列表（本轮）

### F-R1-01 — **P1（关键，发布前必达）** — 渲染哈希更正不完整：验收文档仍以 0.80.0 值作为 0.81.0 的验收期望

- **位置**：`docs/release/real-machine-acceptance-0.81.0.md:84`（**不在本轮 5 文件变更面内**，属被审更正的**同族残留**）
- **事实依据**：该行仍写「三路径渲染 sha256 | 全等 `00e0d330…3723`」，而本批已核定的 0.81.0 候选态为 `6caf90fe…e55d`（16796 B）——同批的 `release-checklist:84`、`rollback-plan:48/:64`、`version-plan:17` **均已更正并显式声明「不得表述为保持 `00e0d330…3723` 不变」**，唯此一行未同步（`00e0d330` 在 0.81.0 文档中的 5 处出现里，仅此处**未**携带 `6caf90fe` 对照）。
- **影响**：该行位于「§2 隔离环境验收（Coordinator 侧，自动化；供对照）」表，是**将被实际执行的验收判据**。按 0.81.0 安装态执行会读到 `6caf90fe…e55d`，与文中期望值不符 ⇒ 要么产生**假性 MISMATCH**（误导为安装异常），要么被填成错误期望值。与已更正的四份文档**直接矛盾**。
- **最小修复动作**：把 `:84` 期望值改为 `` `6caf90fe…e55d`（16796 B；0.80.0 基线 = `00e0d330…3723`，差异仅 persona 版本行 1 处） ``（1 行文本）。
- **关闭截止**：**M-2 Gate 11 回填之前**（或随本轮返工批）；复核方 = M-3 Release Reviewer。
- **附带待验证项（同一表，非本轮引入）**：`real-machine-acceptance-0.81.0.md:83` 写 `dsh-doctor --offline --json` 期望「**8 阶段全 `NOT_RUN`** 且 exit 0」，而 `dsh_doctor.py` 模块文档（L35-40）明确「**Offline is about processes, not about files** …… the file-level criteria keep running」，且 `--offline` 的显式降级只覆盖 S2/S4/S6（+S5 默认 NOT_RUN）⇒ 该期望**可能**不成立。**我未执行 `dsh-doctor`（超出本轮只读命令边界）⇒ 标「待验证」**，建议 M-2 一并实测这一表。

### F-R1-02 — **P2（建议）** — candidate manifest 的落库时序未在文档中声明（含 M-8 措辞与 FIX-329 验收措辞两处张力）

- **位置**：`docs/release/release-checklist-0.81.0.md:4`（候选打包 commit 定义）、`:97`（§M-8 收尾义务）、`:103-113`（M-2 执行序）；`.governance/plan-tracker.md:101`（FIX-329 行验收）
- **事实依据**：
  1. `checklist:4` 定义「候选打包 commit = M-1 打包提交（本 checklist 的冻结提交；其 hash 由 M-2 期 `release-ledger --version 0.81.0 --no-remote` 从 git 派生后回填）」；而 ledger 的 `candidate_commit` 语义 = **添加该 manifest 路径的那个提交**（`ledger.py:184-191` + `trust.candidate_commit.derivation = git_commit_adding_path`）。⇒ 二者相等**当且仅当** manifest 与候选打包提交**同批提交**；若 manifest 单独先行提交，ledger 派生出的 hash 将**不等于**文档定义的「checklist 冻结提交」。
  2. `checklist:97` 仍写「**发布后**：`core/releases/0.81.0.json` 落库」，而 manifest 现已作为 **candidate 态**产出（本批新增）；0.79.0 先例（`8d9110c` = candidate 态 manifest 提交，`17eda48` = 后来的 released transition）表明 candidate 态本就是**发布前**落库、发布时转 released。
  3. `plan-tracker:101`（FIX-329）验收含「`release-ledger --version 0.81.0 --no-remote` = **NATIVE_CANDIDATE PASS**」——在 manifest 提交前该条**不可能**成立（见 §5 附加裁决 3）。
- **影响**：M-2 执行时可能出现「按 `checklist:4` 回填的 hash ≠ ledger 派生值」的定义冲突，或按当前措辞误判 FIX-329 验收未达成。
- **建议**：①在 M-2 执行序加一句次序声明：「`core/releases/0.81.0.json` MUST 与候选打包提交**同批提交**（不得先行单独提交），随后跑 `release-ledger --version 0.81.0 --no-remote` 派生 candidate commit 并回填 `checklist:4/:87` 与 `rollback-plan:29/:32`」；②`checklist:97` 改为「发布后：`core/releases/0.81.0.json` **转 released 态**（candidate 态随候选打包提交落库）」；③FIX-329 验收措辞改为「manifest 提交后 `release-ledger … --no-remote` = NATIVE_CANDIDATE PASS（先提交再校验）」。

### F-R1-03 — **P2（建议）** — Gate 10 对 FIX-328 的闭合陈述未带其自身 R0 遗留（返工批）

- **位置**：`docs/release/release-checklist-0.81.0.md:83`（Gate 10 行）
- **事实依据**：Gate 10 写「① …… **已由 FIX-328 修复**（`test_triage_write_guard.py` L525-554，+21/−1；修复后 `OK (skipped=1)` 且 skip 理由写明）」——该陈述**属实**（§0-19 逐条复核）；但 `review-FIX-328-CODE-R0` 的结论是 `APPROVED_WITH_NOTES`，且 `plan-tracker:100` 明确登记**遗留 F-1（P2，本次改动引入的测试灵敏度回退：`plan_tracker_unreadable` 分支 task_id 为空 ⇒ subset 恒真被 skip 吞掉）/ F-2（P2）/ F-3·F-4（P3）→ 返工批**。
- **影响**：读 Gate 10 会形成「该回归已彻底闭合」的印象，而测试灵敏度面仍有开放 P2；按 P1「分析基于事实、不遗漏」原则，建议在门禁行补一句登记。
- **建议**：Gate 10 的 ① 处补「（FIX-328 R0 = APPROVED_WITH_NOTES/0；遗留 F-1/F-2(P2)、F-3/F-4(P3) 登记为返工批）」——**不**改变门禁结论（产品代码零回归成立）。

### F-R1-04 — **P2（建议）** — `rollback-plan:13` 的「渲染产物 sha256 不变」是未限定断言，与本批更正后的自身事实冲突

- **位置**：`docs/release/rollback-plan-0.81.0.md:13`（§1 回滚影响分类表 · 消费方改造行）
- **事实依据**：该行写「**需重装预设**——见 §2.2（**渲染产物 sha256 不变**，但代码路径变化）」；而同一文件 `:48`、`:64` 已更正为「0.81.0 候选态 = `6caf90fe…e55d` ≠ 0.80.0 基线 `00e0d330…3723`（差异恰为 persona 版本行 1 处）」。字面读 `:13` 与 `:48/:64` **互相矛盾**（前者可被读成「本版渲染哈希不变」）。
- **影响**：低——该行描述的是**消费方改造**（V2/V5/V6/V7 的行为保持属性）而非版本 bump 结果，且回滚**动作**（§2.1）与**验证**（§2.2/§4）均正确；但同文件内两处对「渲染是否变化」的表述不一致，M-3 Release Reviewer 会重复提出。
- **建议**：限定措辞，例如「渲染产物 sha256 **仅因 persona 版本行随版本 bump 变化**（见 §2.2；该行之外逐字节不变），代码路径变化」——1 处词语级修改。

### F-R1-05 — **P2（建议；超出本轮变更面，预存在）** — `version-plan:82` 冻结面计数「82→83」与冻结事实不符（应为 `82→84`）

- **位置**：`docs/release/version-plan-0.81.0.md:82`（§4 门禁清单第 8 行）
- **事实依据**：该行写「`test_registry.py` 全绿（**82→83** / 70→71 / `migrated` +`dsh-doctor`）」；而 `tests/test_registry.py:67-81` 注释与常量明确：「**FEAT-031 (0.81.0 slice V8): 82 -> 84 CLI keys**（`dsh-doctor` **+** the `check-dsh-boundary` gate entry）and 70 -> 71 check segments（`28w`）」+ `FROZEN_CLI_KEYS = 84`；我静态计数 `registry.py` `_COMMANDS` = **84**、冻结面 `snapshots.json` keys = **84**（含两个 V8 新键）⇒ 起点 82 + 2 = **84**，文中「82→83」少了 `check-dsh-boundary`（很可能误抄 0.80.0 期 `test_registry.py:67` 的「82→83」历史变更）。
- **影响**：中低——门禁判据（`test_registry.py` 全绿）本身正确，实际测试断言的是 84/71，故**不会**导致误判通过/失败；但冻结文档中的计数与冻结面不符，属事实错误。
- **建议**：订正为「82→84 / 70→71」，或登记为 M-2 前顺手订正项。**标注：预存在（非 FIX-329 引入）且超出本轮变更面**。

### F-R1-06 — **P3（讨论）** — 「版本钉过期经实验证伪 + 工作树实测二者 OK」尚无可追溯证据行

- **位置**：`docs/release/release-checklist-0.81.0.md:83`（②归因处）；`.governance/evidence-log.md`（无对应 EVD 行）；`.governance/plan-tracker.md:100`
- **事实依据**：`evidence-log` 现仅有 EVD-1033（**修复前**的 `failures=38/errors=2` 与旧归因「版本钉过期 2 + 金丝雀 1」）与 `REVIEW-FIX-328-R0`（仅 `test_triage_write_guard` 复跑）；「在 `%TEMP%` 副本回退标记面以逐字复现瞬时红」与「工作树实测二者 OK」两项由 checklist/plan-tracker 陈述，**我未找到 EVD 行**（也**未**自行执行套件）。
- **影响**：低——该更正方向我已用**静态**证据独立印证（§0-18：两测试体无版本字面量，机制上不可能因「版本钉过期」失败）；但按事实依据红线，M-2 重取全量时宜补一条 EVD 行，使「证伪」本身可复查。
- **建议**：M-2 重取全量原始失败清单时，同一 EVD 行内记录「瞬时红的复现实验 + 重取结果」，并回填 Gate 10。

### F-R1-07 — **P3（讨论）** — README `:92` 的「push credentials blocked」与 `version-plan:19` 的「凭据本会话可用」存在措辞张力

- **位置**：`README.md:92`（本批修改行）vs `docs/release/version-plan-0.81.0.md:19`
- **事实依据**：README 新句写「… but **not yet pushed to the remote**（push credentials blocked — disclosed in `docs/release/release-checklist-0.79.0.md`；the M-7 push carries the back-push obligation）」；`version-plan:19`（2026-09-13）记「push 凭据本会话**可用**（`git ls-remote --tags github-https` 成功、`git push --dry-run` 成功）⇒ 0.79.0/0.80.0 两个 tag 与 118 commits 的补推义务**可在本版一并履行**」。按现在时读 `blocked` 与后者相抵。
- **影响**：低——两句的**结论**一致（未推送 + 补推义务在 M-7/§M-8）；仅「阻塞原因」的时态口径不一致。
- **建议**：README 处限定为历史披露口径（如「previously blocked — see …」）；或按 DEC 口径改为「推送尚未执行（M-7 待履行）」。
- **未验证声明**：README 的「Not yet pushed / GitHub master serves 0.78.1」属**远端状态**，受只读离线约束**我未核实**（不执行 `git ls-remote`/network）；该项与仓库自身治理记录（补推义务登记）一致，标「未验证」。

### F-R1-08 — **P3（讨论；F-06 的登记性遗留）** — `check-version-consistency` 的 1 条 plan-tracker `[WARN]` 仍未加注

- **位置**：`docs/release/release-checklist-0.81.0.md:74`（Gate 1 行）；`.governance/plan-tracker.md:11`
- **事实依据**：`plan-tracker:11` 仍为 `工作流版本: 0.80.0`（权威源 = 0.81.0）⇒ M-2 执行该门禁时 `[WARN] plan-tracker workflow version=0.80.0, expected=0.81.0` 仍会出现；Gate 1 行未加注（R0 F-06 的建议未落地）。
- **影响**：低——命令仍 PASSED/exit 0（`[WARN]` 不计入 fail_items），且 plan-tracker 版本行按设计在 M-8 转 released 时更新；仅在「零告警」误读时产生偏差。
- **建议**：M-2 回填 Gate 1 时加注「含 1 条 plan-tracker `[WARN]`（M-8 清除）」。

---

## 4. AI 代码/内容专项 5 项（逐条结论）

| # | 检查项 | 结论 |
|---|---|---|
| 1 | **mock 残留** | **未发现**——被审面为文档 + 1 个 JSON 数据文件，无 mock/stub/假实现、无测试文件改动。 |
| 2 | **硬编码返回值** | **未发现缺陷**。新出现的硬编码值仅 3 类：版本字面量 `0.81.0`、复核过的哈希（`6caf90fe…e55d`/`00e0d330…3723`）、commit hash（`d87ead8`/`3074120`/`61b571c`/`71f73eb`）。逐条判定：commit hash 经 §0-1~4 实测存在且关系正确；哈希为 Coordinator 实测值（本节第 6 条声明其非我复现）；**候选打包 hash 未硬编码**（显式占位）。无「以硬编码绕过校验」的分支。 |
| 3 | **幻觉 API 调用** | **未发现**——本批引用的命令/文件全部实存（§0-17）：`release-ledger --no-remote`（`verify_workflow.py:23559`）、`check-dsh-boundary`（`registry.py:256`）、`git revert --no-commit <range>`（git 原生支持的区间形式）、4 个被引文档路径全部存在。 |
| 4 | **未实现 TODO** | **未发现隐藏 TODO**——`⟦⟧` 占位仅剩 checklist 的 M-2 门禁结果与真机回贴面（13 处，全在允许面）；`<0.81.0 候选打包提交>` 为**显式声明**的待派生值（非静默 TODO）。 |
| 5 | **过度实现** | **未发现**——变更最小且纯粹（5 文件 +23/−17，纯事实订正 + 1 个候选态 manifest）；无顺带重构、未越界修改未被 R0 要求的文件（README 仅 2 行、版本规划仅 1 行）。反向检查（是否**漏**改）：**发现 1 处漏改**——`real-machine-acceptance-0.81.0.md:84`（F-R1-01）。 |

---

## 5. 附加三项裁决（本轮新出现的事实）

### 附加 1：三路径渲染哈希更正 —— **事实准确、措辞合规，但更正不完整（F-R1-01）**

- **裁定**：更正后的四处表述（`checklist:84`、`version-plan:17`、`rollback-plan:48`、`rollback-plan:64`）**均未**出现「保持 `00e0d330…3723` 不变」类措辞；`6caf90fe…e55d`（16796 B）被明确标为 **0.81.0 候选态**，`00e0d330…3723` 被明确标为 **0.80.0 基线/回滚后期望值**，差异限定为「persona 版本行 1 处」，并在 rollback `:48` 补充了「回滚**会**把该行改回 `v0.80.0`，**除该行外**逐字节不变」的正确定性指引 ⇒ **措辞纪律合规**。
- **结构自洽性佐证（我的静态核验）**：composition 源目录 `agent-presets/` 全目录仅 **1 处**版本字面量（`agent.cordis.yml.template:51`），且 `launch.py` 文档声明该目录「holds exactly two files — the composition template（**the ONE composition source**）」⇒「差异恰为 1 行」在结构上成立。
- **未复现声明**：`6caf90fe…e55d` 的**具体字节值我未独立复现**（复现需执行 `launch.py` / JS 渲染 = 启动子进程 + 写隔离 `DSH_HOME`，超出本轮只读边界）；判定依据 = Coordinator 实测记录 + 我的结构核验 + 四处文档互证一致性。
- **扣分**：更正**未覆盖** `real-machine-acceptance-0.81.0.md:84`（+ `:83` 待验证）⇒ 见 **F-R1-01（P1）**。

### 附加 2：新增 `core/releases/0.81.0.json` —— **候选态形态正确（逐字节同构先例）**

逐键比对（与 `8d9110c:…/0.79.0.json` 的 candidate 态先例、及 HEAD 的 0.79.0 released / 0.80.0 released）：

| 键 | 期望（candidate 形态） | `0.81.0.json` 实测 | 裁决 |
|---|---|---|---|
| `lifecycle_state` | `candidate` | `candidate` | ✅ |
| `effective_state.lifecycle_state` | `candidate` | `candidate` | ✅ |
| `effective_state.amendments` | `[]` | `[]` | ✅ |
| `effective_state.withdrawn` | `false` | `false` | ✅ |
| `events` | `[]` | `[]` | ✅ |
| `provenance` | `native` | `native` | ✅ |
| `schema_version` | `1` | `1` | ✅ |
| `trust.candidate_commit.derivation` | `git_commit_adding_path` | `git_commit_adding_path` | ✅ |
| `version` | `0.81.0` | `0.81.0` | ✅ |
| `artifacts.changelog` | `project/CHANGELOG.md` | 同 | ✅ |
| `artifacts.release_docs` | checklist/feature-flags/rollback-plan 三件套（0.79.0/0.80.0 先例同构） | 同（0.81.0 版） | ✅ |
| `artifacts.review_evidence` | `[".governance/evidence-log.md"]` | 同 | ✅ |
| 形态 | 单行 JSON / 键序升序 / LF / 尾 LF | `CR=0, LF=1, lastByte=10`，且与 4 个既有 manifest 同构 | ✅ |
| 字节级 | — | 494 B，与 8d9110c 候选态在 `0.79.0`→`0.81.0` 归一化后**完全相等** | ✅ |

⇒ **无形态缺陷**。附带建议（并入 F-R1-02）：其落库时序（与候选打包提交同批）需在 M-2 执行序中声明。

### 附加 3：`release-ledger --version 0.81.0 --no-remote` 现返回 `state: FAIL`（`candidate_commit: … found 0`）—— **属预期前置依赖，非真实缺陷**

- **机械证明**：manifest **未跟踪**（`git ls-files` 无输出）且**无任何提交添加该路径**（`git log -- <path>` 无输出）⇒ `derivation = git_commit_adding_path` 的解析只能得到 0 个提交（`ledger.py:184-191`）。同时 `trust_level` 由 `lifecycle_state == "candidate"` **独立**推出（`ledger.py:431-436`）⇒ 「`state: FAIL` + `trust_level: NATIVE_CANDIDATE`」并存**正是**代码对「候选 manifest 尚未提交」的既定行为，**不是**缺陷、**不需要**改代码或改 manifest 形态。
- **次序声明（更优写法，P3 并入 F-R1-02）**：正确次序 = **提交（manifest 与候选打包提交同批）→ 再跑 `release-ledger --version 0.81.0 --no-remote` → 以派生值回填** `checklist:4/:87` 与 `rollback-plan:29/:32`。相应地把 `plan-tracker:101`（FIX-329）验收中的「`release-ledger … = NATIVE_CANDIDATE PASS`」措辞限定为「manifest 提交后」——否则该验收条件在提交前恒不可达。
- **不受影响项**：`checklist:86`（Gate 13）仍为 `⟦待回填⟧`，**未**声称 ledger 当前 PASS ⇒ 无失实陈述。

---

## 6. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **0**（R0 的 F-01 已修复并经独立复核） | ✅ **通过** |
| 5 维度全覆盖 | = 100% | 5/5 逐项有结论（§2） | ✅ 通过 |
| 每条发现标注级别 | = 100% | 8/8 条带 P1~P3 标签（§3） | ✅ 通过 |
| 设计一致性检查 | 已完成 | 已完成（§7，14 项检查，1 项偏离 = F-R1-01） | ✅ 通过 |
| AI 代码专项 5 项 | 全部完成 | 5/5 逐条有结论（§4） | ✅ 通过 |

⇒ 硬门槛全部通过（P0 = 0）→ **结论 APPROVED_WITH_NOTES（`unresolved_blockers=0`）**。P1×1（F-R1-01）按 code-review 质量标准「已处理或**记录为遗留项**（含关闭截止日期）」登记，不构成 BLOCKING。

---

## 7. 设计一致性检查（硬门槛项）

| 检查点 | 期望（ADR/契约/DEC） | 实测 | 裁决 |
|---|---|---|---|
| 回滚口径自洽 | 「回滚目标 = 恢复到 0.80.0 行为」须与所给提交区间自洽（R0 F-01） | 区间 `d87ead8..<候选打包提交>` = 31 + 1 commits，起点 = 基线实测点，与 `:5`/`:60`/`:65` 自洽 | ✅（R0 偏离已消） |
| 候选打包 hash 不编造 | 哈希此刻不存在 ⇒ 只允许「待 ledger 派生后回填」写法 | `<…>` 占位 + 显式声明；全文档无编造 hex | ✅ |
| 版本权威源 | `SKILL.md` frontmatter 唯一权威（DEC-096） | 本批未触碰权威源/投影（改动文档面） | ✅ |
| 冻结完整性 | M-1 冻结前占位全部消除（`checklist:112`） | feature-flags `⟦` = 0；仅余 M-2 门禁结果 + 真机回贴 + 纪律字面引用（允许面） | ✅（R0 偏离已消） |
| 发布记录形态 | `core/releases/*.json` candidate 态同构先例 | 与 8d9110c 先例逐字节同构（归一化后相等） | ✅ |
| 门禁期望措辞 | 不得写无条件 PASS（R0 F-03） | Gate 10 期望列 + Result 均含「如实披露 / 不得写无条件 PASS」 | ✅ |
| 测试基线归因 | 归因须与机制一致 | 两测试体无版本字面量（我静态核实）⇒「瞬时红」归因方向成立 | ✅ |
| 棘轮口径事实 | 文档声称的 84/84 + 71/71 须与冻结面一致 | `_COMMANDS`=84、`_SEGMENT_LOADERS`=71、`snapshots.json` keys=84/ids=71、`test_registry.py` 常量=84/71 | ✅ |
| 段号事实 | `28w` 须与 registry 一致 | `registry.py:412` + `quickscan_registry.py:554` | ✅ |
| `--offline` 语义 | 须与 `dsh_doctor.py` 代码一致 | S2/S4/S6 + S5、K-12 域限定、退出码三态全部相符 | ✅ |
| 措辞纪律（真实环境） | 不得出现无限定语的「真实安装/真实环境通过」 | 真机三项仍 `⟦待用户回贴⟧`；隔离限定保留 | ✅ |
| README 事实 | 须与 `git tag -l` 一致（R0 F-05） | tag 存在 + peel `71f73eb` + 未推送 + 补推义务引用 | ✅ |
| **渲染哈希事实的**全仓**一致** | 更正常见的完整性要求：不再有以 0.80.0 值充当 0.81.0 期望的残留 | `real-machine-acceptance:84` **仍残留** | ❌ **F-R1-01** |
| 发布记录落库时序 | 应由文档声明前置条件（先提交再校验） | 未声明（M-2 执行序缺该句） | ❌ **F-R1-02**（P2，非硬门槛项） |

---

## 8. 命令上报（只读；命令 / 退出码 / 输出摘要）

| # | 命令（工作目录 = 仓库根） | 退出码 | 输出摘要 |
|---|---|---|---|
| 1 | `git status --short` | 0 | 25 个 staged（R0 批）+ `MM`×3（checklist/rollback/version-plan：R0 批已暂存 + FIX-329 再改）+ ` M`×4（README、feature-flags、`architecture-baseline.json`、`test_triage_write_guard.py`）+ `??`×3（两份审查报告 + `core/releases/0.81.0.json`） |
| 2 | `git rev-parse HEAD` | 0 | `5e6d8c71a2dad19c8cff3b720fbe7a99bae83629` |
| 3 | `git diff --stat -- docs/release README.md`（会话初 + 收尾各一次） | 0 | **5 files changed, 23 insertions(+), 17 deletions(-)**（两次一致） |
| 4 | `git diff -- docs/release README.md` | 0 | 全文 diff（本报告主要依据；含 5 个 `index <old>..<new>` blob 头） |
| 5 | `git rev-list --count d87ead8..3074120` / `71f73eb..3074120` / `d87ead8..HEAD` | 0 | **31** / **32** / **32** |
| 6 | `git merge-base --is-ancestor {71f73eb→d87ead8, 3074120→HEAD, d87ead8→HEAD}` | 0 / 0 / 0 | 三项均成立 |
| 7 | `git tag -l`；`git rev-list -n1 v0.79.0`；`git rev-list -n1 v0.80.0` | 0 | 100 个 tag；`v0.79.0` → `17eda48…`；`v0.80.0` → **`71f73eb…`**（无 `v0.81.0`） |
| 8 | `git log -1 --oneline d87ead8` / `3074120` | 0 | `d87ead8` = 「REL-076 M-5 回填补提交…」（0.80.0 线末提交）；`3074120` = V8 交付提交 |
| 9 | `git show HEAD:<0.79.0.json>` / `git show 8d9110c:<0.79.0.json>` / `git show HEAD:<0.80.0.json>` | 0 | released / **candidate 态先例** / released（逐键比对对象） |
| 10 | `git log -1 --oneline 8d9110c`；`git log --oneline -- <0.79.0.json>` | 0 | `8d9110c` = REL-075 candidate 态 manifest 提交；该路径两提交（`8d9110c` candidate → `17eda48` transition） |
| 11 | `git ls-files -- <0.81.0.json>`；`git log --oneline -- <0.81.0.json>` | 0 / 0 | **均无输出** ⇒ 未跟踪、0 个提交添加该路径（ledger FAIL 的机械依据） |
| 12 | `git diff --stat/-p -- test_triage_write_guard.py` | 0 | **1 file changed, 21 insertions(+), 1 deletion(-)**（FIX-328 在制面，非本轮被审面） |
| 13 | `Select-String`（`00e0d330` / `6caf90fe` / `61b571c` / `3074120` / `⟦` / 40 位 hex / `候选打包`）逐文档普查 | 0 | 见 §0-5~8；关键：real-machine-acceptance:84 为唯一未同步的旧哈希期望 |
| 14 | `Select-String`（registry.py / quickscan_registry.py / ledger.py / dsh_doctor.py / dsh_boundary.py / test_registry.py / test_verify_workflow.py / test_review_machine_provenance.py / verify_workflow.py） | 0 | 段号、棘轮计数、退出码、offline 分支、K-12、FIX-328 证据、`--no-remote` 旗标逐项取证 |
| 15 | PowerShell 静态计数（`_COMMANDS` L233-347 / `_SEGMENT_LOADERS` L354-424）；`ConvertFrom-Json` 读 `snapshots.json` `faces` | 0 | 84 / 71；冻结 keys 84（含两 V8 键）、ids 71（含 `28w`） |
| 16 | 字节级检查（`[System.IO.File]::ReadAllBytes`）+ `Get-FileHash SHA256`（5 文件 + manifest） | 0 | `CR=0 / LF=1 / 尾LF`；494 B；收尾哈希见 §0 |
| 17 | `Get-Content -Encoding UTF8`（0.81.0 五文档 + plan-tracker + evidence-log + FIX-328 报告 全文/切片读） | 0 | 全文事实核对（按 FIX-278 G4/F：显式 UTF-8，未使用裸 `Get-Content`） |

**未执行的命令（受只读/边界约束主动不执行）**：`release-ledger`（读代码 + git 事实代证）、`check-version-consistency` 等 `verify_workflow.py` 子命令、`unittest` 全量/单套件、`dsh-doctor`、`launch.py` 渲染、`git ls-remote`/任何网络命令、任何 `git add/commit/restore/reset/checkout/stash`、任何 spawn/写操作。

---

## 9. 未验证 / 超出授权面声明

1. **未执行测试套件**：全量基线为 **EVD-1033（修复前）** 记录 + Gate 10 的 M-2 重取义务；我**未**跑任何测试，「工作树实测二者 OK」采信文档 + 静态印证（§0-18）。
2. **未复现渲染哈希**：`6caf90fe…e55d` / 16796 B 未由我独立复现（需执行渲染）；判定 = Coordinator 实测 + 结构核验 + 四文档互证。F-R1-01 的判定**不依赖**该哈希的具体值（依赖的是「同一文档集内期望值口径不一致」这一可复查事实）。
3. **未执行 door 门禁与 ledger**：`release-ledger` 的 FAIL 结论由代码 + git 事实静态证明（§0-15/16），未复跑命令；`dsh-doctor --offline` 的 S5/S2 期望在 `real-machine-acceptance:83` 标注为**待验证**。
4. **远端状态未核实**：README 的「未推送 / GitHub master 服务 0.78.1」属远端事实，受离线只读约束未验证（与仓库自身补推义务登记一致）。
5. **未触碰用户真实环境**：未访问 `$env:USERPROFILE\.dsh`、`$DSH_HOME`、仓库外任意路径；未做任何安装/验收/写入操作。
6. **并发写入**：被审面两次指纹完全一致（§0-21）；非被审面的 FIX-328 在制改动与被审面**无交集**，结论仅对被审面有效。

---

## 10. 结论与处置要求

**结论：APPROVED_WITH_NOTES**（`unresolved_blockers=0`）

- **R0 阻塞项全部关闭**：**F-01（P0）已修复且经独立复核**——回滚区间改为整个 0.81.0 窗口（`d87ead8..<候选打包提交>`，31+1 commits），V8/V10 已限定为区间末代表提交，无编造 hash，全文档无旧表述残留；F-02（P1）、F-03（P1）同样已修复并经逐条事实核验。
- **本轮 P1 遗留（1 项，随批或 M-2 前必达）**：**F-R1-01** —— `docs/release/real-machine-acceptance-0.81.0.md:84` 的渲染哈希期望值未随本批更正同步（1 行文本即可闭合；关闭截止 = M-2 Gate 11 回填前；复核方 = M-3 Release Reviewer）。
- **P2 建议（4 项，均非阻塞）**：F-R1-02（manifest 落库时序声明 + M-8 措辞 + FIX-329 验收措辞）、F-R1-03（Gate 10 补登 FIX-328 的 R0 遗留）、F-R1-04（`rollback-plan:13` 断言限定）、F-R1-05（`version-plan:82` 计数 82→**84**，超范围预存在）。
- **P3 讨论（3 项）**：F-R1-06（证伪/复跑缺 EVD 行，M-2 重取时补）、F-R1-07（README push 凭据时态口径）、F-R1-08（F-06 的 1 条 `[WARN]` 加注）。
- **附加三项裁决**：①渲染哈希更正**事实准确、措辞合规**（不得表述「保持 00e0d330 不变」的要求已满足）但**覆盖不全**（F-R1-01）；②`core/releases/0.81.0.json` 候选态形态**正确**（与 8d9110c 先例逐字节同构）；③ledger 的 FAIL 是「manifest 未提交」的**预期前置依赖，非缺陷**（附「先提交再校验」次序建议）。
- **复审链状态（M7.4）**：本 R1 为**通过终态**（`APPROVED_WITH_NOTES` / `unresolved_blockers=0`），**不需要** R2；复审链可闭合。
- **产品面单独结论**：本批 5 文件为发布文档事实订正 + 1 个候选态 manifest，**产品代码/配置面零改动**（R0 已单独认可的产品面不在本轮范围内）。
