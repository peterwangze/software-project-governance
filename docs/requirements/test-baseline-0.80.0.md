# 测试收集关系调查与全量基线 0.80.0（AUDIT-151）

> **Task**: AUDIT-151（P1，0.79.0∥ → 0.80.0 首槽；DEC-184 P0 波次依赖枢纽）
> **角色**: Analyst Agent（测量例外口径——只读 + 运行测试/测量命令，禁改仓库文件）
> **日期**: 2026-09-10 | **HEAD**: `2be00ec`（仅增 docs——测试面与 `213fbba` 2026-09-09 17:16 完全一致，git diff --stat 证实零测试文件变更）
> **唯一写入产物**: 本报告 | **上游**: AUDIT-150 §10 P0 / facts §7（`docs/requirements/architecture-audit-facts-0.80.0.md` L406-431）
> **下游**: FEAT-018 / FEAT-019 / FIX-301 / AUDIT-152（§7 直接引用）

---

## 1. 方法节（口径定义 + 全部命令原文）

### 1.1 收集口径定义（四种，勿混用）

| 口径 | 定义 | 范围 | 今日值 |
|---|---|---|---|
| **A. 静态全仓 grep** | 正则 `^\s*def test_` 对全部测试 py 文件逐文件求和 | 47 个 py 文件（infra/tests 46 含 2 个 `__init__.py` + 仓库根 `tests/test_product_code.py`） | **2,201** |
| **B. 动态 unittest discover**（**权威**） | `unittest.TestLoader.discover` 实际装载的用例数 | infra/tests 46 文件（**不含**根 tests 7 个——discover 起点目录之外） | **2,194** |
| **C. 动态 pytest collect（插件根 CWD）** | `pytest --collect-only` | 同 B 范围（pytest 默认发现，从插件根运行） | **2,194** |
| **D. 单文件** | test_verify_workflow.py 一个文件 | 1 文件 | **811** |

**关键恒等式（本会话三方实测）**：A(infra/tests 部分) = B = C = **2,194**——全部 44 个测试文件的每个 `def test_` 均被两个 runner 无遗漏收集（零死定义、零条件漏收）。A 的全仓值 2,201 = 2,194 + 7（根 tests，不在任何门禁命令覆盖内）。

### 1.2 命令原文（全部可复现；`-B` 为禁字节码缓存的测量安全变体，不改变收集与结果）

```powershell
# 口径 A（静态普查；facts §7.1 同法复核）
Select-String -Path "skills/software-project-governance/infra/tests/**/*.py" -Pattern '^\s*def test_'   # 求和 = 2194
Select-String -Path "tests/*.py" -Pattern '^\s*def test_'                                              # = 7；合计 2201

# 口径 B（权威口径；CI 同款——.github/workflows/ci.yml L23 带 -v）
python -B -c "import unittest; print(unittest.TestLoader().discover('skills/software-project-governance/infra/tests').countTestCases())"  # = 2194

# 口径 C（必须从插件根运行！仓库根运行会 44 收集错误——见 §2 注 3）
cd skills/software-project-governance; python -B -m pytest --collect-only -q   # = "2194 tests collected in 0.79s"

# 口径 D（单文件）
Select-String -Path "skills/software-project-governance/infra/tests/test_verify_workflow.py" -Pattern '^\s*def test_'   # = 811

# 当日全量基线（§3；工作目录 = 仓库根）
python -B -m unittest discover -s skills/software-project-governance/infra/tests
```

---

## 2. 收集关系表（2,201 / 2,104 / 811 / 788 各口径解释）

### 2.1 主表

| 数字 | 口径 | 时点 | 解释 / 对应命令 | 出处 |
|---|---|---|---|---|
| **2,201** | A 静态全仓 grep | 2026-09-10 HEAD | 47 文件 `def test_` 定义普查（2,194 + 根 7）。**是"定义总数"，不是任何 runner 的运行数** | 本报告实测；facts §7.1 一致（注：facts"46 含 3 个 `__init__.py`"系笔误，实测 2 个，总数 47 不受影响） |
| **2,194** | B/C 动态收集 | 2026-09-10 HEAD | discover/pytest 实际装载（§1.2 命令） | 本报告实测 |
| **2,130**（= 2,104 passed + 26 failed） | pytest 全量运行 | 2026-09-08（FIX-291，commit `5c630d7`） | pytest 全量当时态。**精确闭合**：git grep 该 commit def 总数 = 2,130 = 2,104+26（逐个对账一致） | EVD-949（evidence-log L1751）「全量 26 failed/2104 passed」 |
| **2,003**（= 1,976 passed + 27 failed） | pytest 全量运行 | 2026-08-25/26（FIX-278，`3ad9fdd` 邻域） | **精确闭合**：def 总数 1,979 + 24 = 2,003——pytest 对 subTest **失败**逐个计数（pre_commit 12 方法×2 hook=+24），unittest 只计方法数。两种 runner 的计数差 = "漂移"观感的机制性来源之一 | EVD-FIX-278（L1553）「1976 passed+215 subtests（27 failed 全既有基线——24 bash/WSL 环境 + cleanup presets + loop-runtime 抖动 + resolve_entry snapshot-freshness）」 |
| **1,768** | pytest 全量运行 | 2026-08-23（FIX-270） | 更早时点态；趋势一致（1,768→2,003→2,130→2,194 单调随任务 TDD 增量上升）。与最近可考 commit（`2bc8569` def=1,895）差 −127 = 运行时点 commit 早于该打包 commit 的日内时序残差（如实登记，未逐 commit 对账） | EVD-FIX-270（L1394）「全量 1768 passed+237 subtests 0 failed」 |
| **811** | D 单文件（静态=运行） | 2026-09-09 17:16 起（`213fbba`→HEAD 不变） | test_verify_workflow.py 当前态；EVD-970 pytest 口径「811 passed + 89 subtests」同数 | git show 逐 commit 计数 + EVD-970（经 facts §7.2 L421 引） |
| **798** | D 单文件运行 | 2026-09-09 15:51（`3cbdc92`） | 同文件历史态。**EVD-967 措辞「全量 798 ran」实为单文件口径**——治理记录"全量"一词混用是漂移观感根因之二 | EVD-967（L1825）；git `3cbdc92` def=798 精确吻合 |
| **788** | D 单文件运行 | 2026-09-09 14:35（`76f67bd`） | **任务书采信数**。同文件历史态（FIX-294 落点后、FIX-295 前） | EVD-964（L1808）「单文件 unittest Ran 788 failures=1」；git `76f67bd` def=788 精确吻合 |
| **775** | D 单文件运行 | 2026-09-09 11:53（`1d3d973`） | 同上（FIX-292 +11 后） | EVD-960（L1780）「全量 764→775」/ EVD-962（L1804）「775 ran」 |
| **764** | D 单文件运行 | 2026-09-08 19:13（`5c630d7`） | 同上（FIX-291 落点） | EVD-955（L1761）「764 passed + 89 subtests」/ EVD-957（L1767）「Ran 764 OK（140.3s）」 |

单文件考古链（git 逐 commit `def test_` 计数，零插值）：`764@5c630d7 → 775@1d3d973 → 788@76f67bd → 795@fc1b739 → 798@3cbdc92 → 811@213fbba(→HEAD)`。

### 2.2 「2,201 vs 788」一句话结论

**2,201 是当前 HEAD 全仓 47 个测试文件的静态定义总数；788 是 2026-09-09 14:35 时点 test_verify_workflow.py 单文件的 unittest 运行数——两者是「全仓 vs 单文件」×「今 vs 昨」的双重口径交叉，本就不可对减；同口径对齐后：全仓动态收集今日 = 2,194（其中该单文件占 811），788 只是其历史切片。** 无测试丢失、无收集黑洞——差异 100% 由范围差（+1,380 其他文件）与时点差（811−788=23 为 FIX-295 +7 / FIX-296 +3 / FEAT-016 +13 三个日内后续任务）构成，全部 git 实证。

### 2.3 权威「预期收集数」裁定

> **权威预期收集数 = 2,194**；权威命令 = `python -m unittest discover -s skills/software-project-governance/infra/tests`（**从仓库根运行**）。

理由：(a) 与 CI 门禁同源（`.github/workflows/ci.yml` L23 同款带 `-v`——回归判定面唯一被 CI 消费的口径）；(b) 三方恒等验证（§1.1）；(c) 2,201 中的根 tests 7 个不在任何门禁命令覆盖内，属"定义普查增量"，不是运行口径。

**注 3（pytest CWD 陷阱，复跑者必读）**：pytest 全量/收集**必须从插件根**（`skills/software-project-governance/`）运行。从仓库根运行会得到 **44 个收集错误**（`ModuleNotFoundError: No module named 'infra.tests.*'`——测试以插件根为 sys.path 基准的绝对导入）且只收集 373 项（含 `project/e2e-test-project/` git 跟踪夹具副本 15 文件的污染——该夹具是 e2e 测试产物，EVD-969「28o e2e 夹具度量」同域）。历史 EVD 中 pytest 全量运行的 CWD 均未记录——**治理记录缺口，如实登记**（今日复跑以插件根验证可行）。

**注 4（runner 计数差）**：unittest `Ran N` 计方法数（subTest 通过不增计数、失败逐个计入 failures）；pytest collected = 方法数，但 subTest **失败**逐个计入 failed（FIX-278 时点 +24 实证）。同套件两 runner 的 passed/failed 总量可有 ±24 量级差异——跨 runner 比较必须先对齐计数规则。

---

## 3. 当日全量基线（2026-09-10）

| 项 | 值 | 证据 |
|---|---|---|
| 日期/环境 | 2026-09-10，Windows（pwsh 7 包装，**串行独占**——运行期间零并发测量，RISK-048 纪律） | 本会话 |
| 命令 | `python -B -m unittest discover -s skills/software-project-governance/infra/tests`（仓库根） | §1.2 |
| **收集（Ran）** | **2,194** | 输出行 `Ran 2194 tests in 361.133s` |
| **通过** | **2,167**（2,194 − 26 失败 − 1 跳过） | 同上推导 |
| **失败** | **26**（failures=26, errors=0） | `FAILED (failures=26, skipped=1)`；exit 1 |
| **跳过** | **1** | 同上；§4-F0 |
| **耗时** | **361.133s**（unittest 报告）/ 362s 墙钟（含解释器启动） | Stopwatch 362.x |
| 完整输出 | `%TEMP%\audit151_unittest_full.txt`（121,329 bytes，保留为证据） | — |

**历史「1 failure」对照**：EVD-962/964/967 记载的「1 failure（LoopRuntimeClaimAdapterTests 环境超时）」**今日未复现**（26 失败中零 loop-runtime 项）——与 RISK-048 因果链一致（该测试 median<8s 断言仅在并行治理负载下超阈；本次串行独占运行通过）。反向新增 1 例 triage_write_guard live 失败（§4-F2，自 FIX-293 起潜伏）。

---

## 4. 失败分类学（26 失败逐条归因）

### F1 — 环境敏感 ×24（+1 跳过）：bash/WSL 依赖族

- **用例**：`test_pre_commit_review_evidence.ReviewEvidenceRegexTests` 10 个方法 × hook∈{pre-commit, commit-msg} subTest（8 方法×2 + 2 方法×4 变体 = **24 项失败**）：`test_a_legacy_end_column_hits`、`test_b_machine_row_with_zero_blockers_hits`、`test_blocked_never_passes`、`test_blockers_tail_must_be_exactly_zero`（tail_cols 双变体）、`test_c_machine_row_with_nonzero_blockers_misses`、`test_d_needs_change_misses_both_forms`（legacy/machine 双变体）、`test_machine_plain_approved_still_hits`、`test_other_task_machine_row_does_not_hit`、`test_plain_approved_with_blockers_tail_misses`、`test_replay_real_evidence_log_fix260`
- **证据**：traceback 逐项 `hook function run failed: rc=1`，stdout 为 UTF-16 WSL 错误信息（可辨片段 `wsl.exe --list --online` / `WSL_E_DEFAULT_DISTRO_NOT_FOUND`）——hook 以 WSL bash 执行，本机无默认发行版
- **分类**：**环境敏感**（bash/WSL 运行时依赖）。FIX-278（EVD L1553）已定性同族 ×24（「24 bash/WSL 环境」），今日计数不变——存量基线，非新增
- **复跑对照**：具备 WSL 发行版的环境 / Linux CI（ubuntu-latest 用原生 bash）预期转绿——AUDIT-152 定性标记的直接标的

### F2 — 已知缺陷 ×1：live 金丝雀断言与既定数据修复时序耦合（**本日新发现**）

- **用例**：`test_triage_write_guard.GovernanceWriteGuardPlanTrackerTests.test_live_plan_tracker_flags_only_known_m1_rows`
- **证据**：`AssertionError: set() is not true : live M1 four rows must be flagged`（test_triage_write_guard.py L533）。docstring（L525-527）自述「FIX-293 将修数据，本守卫只检不改」——作者预知数据修复将清空 flagged 集，但断言仍要求非空。EVD-963（L1805）：FIX-293 于 2026-09-09 修复 M1 四行→守卫 PASS。本会话守卫 CLI 复跑：**PASS / 0 issues / exit 0**（四面绿）——产品面健康，纯测试断言过期
- **分类**：**已知缺陷（测试面）**——非产品回归。自 FIX-293 落地起必然变红，潜伏被「单文件回归口径」掩盖（FEAT-011 验收只跑 test_verify_workflow.py 775，未跑自家 live 测试所在文件全量）。修复候选：断言反转为 `assertEqual(set(), flagged)`（AUDIT-152 邻域，本任务不改测试文件）
- **方法论注记**：这是「单文件绿 ≠ 全仓过」教训（FEAT-016 R0 先例，facts §7.2）的又一实证——治理记录以单文件数充当回归证据时，跨文件数据耦合断言不被覆盖

### F3 — 已知缺陷 ×1：manifest `presets/` 三方脱节

- **用例**：`test_cleanup.TestPluginScopeDirs.test_all_manifest_dirs_covered`
- **证据**：`AssertionError … {'presets'} : FIX-053 F-001: manifest.json declares these top-level dirs not covered by PLUGIN_SCOPE_DIRS`。`core/manifest.json` L231 声明 dir `presets/`（L235/L239 另有 `presets/governance/*` 文件条目）；`infra/cleanup.py` L46-56 `PLUGIN_SCOPE_DIRS` 无 `presets`；且 `skills/software-project-governance/presets/` **磁盘不存在**（Test-Path False）——manifest / 清理范围 / 磁盘三方脱节
- **分类**：**已知缺陷（清单一致性）**。FIX-278 时点即存在（「cleanup presets」同项），今日计数不变——存量基线，非新增。修复属后续任务（manifest 条目与实际产物面对账），非本任务范围

### F0 — 跳过 ×1（环境敏感，按设计跳过）

- **用例**：`test_utf8_read_guard` GBK 负对照——skip 理由原文 `system ANSI codepage is 65001, not 936 (GBK) — mojibake negative control not reproducible on this machine`（本机 UTF-8 代码页）。分类：环境敏感（skip 为该测试的预期行为，非缺陷）

### 三类计数汇总

| 分类 | 计数 | 明细 |
|---|---|---|
| 环境敏感 | **24 失败 + 1 跳过** | F1 bash/WSL ×24；F0 GBK 负对照 ×1 |
| 已知缺陷 | **2** | F2 live 断言过期（测试面，新发现）；F3 manifest presets（清单面，存量） |
| 真实回归候选 | **0** | — |
| 未定性 | **0** | 全部 26 项带复跑/对照/CLI 证据归因 |

---

## 5. 超时归因

**未发生超时**——单次串行运行 361.1s 完成（无命令超时、无单测超阈、未使用任何 timeout 参数、无需分段）。分段对照（如实登记，非本次实测分段）：EVD-957 单文件 764 tests = 140.3s（≈0.18s/测试）vs 本次全量 2,194 tests = 361.1s（≈0.16s/测试）——单位耗时同量级，无异常放大。历史环境敏感超时项今日状态：loop-runtime median<8s **通过**（串行独占环境）；resolve_entry snapshot-freshness（FIX-278 时点 1 失败）今日**通过**。RISK-048 提示：并行治理负载下 loop-runtime 族可能复现超阈——本基线的环境条件（串行独占）必须随数字一并引用。

---

## 6. 对下游的输入（可直接引用的基线数字与命令）

| 下游任务 | 可引用内容 |
|---|---|
| **FEAT-018**（性能测量协议） | 全量基线：`python -B -m unittest discover -s skills/software-project-governance/infra/tests` = 2,194 tests / **361.1s**（串行独占，2026-09-10）；单文件对照 764 tests/140.3s（EVD-957）；RISK-048 复验锚点：loop-runtime 族在串行环境 PASS——容差表设计须以负载条件为协变量 |
| **FEAT-019**（ArchGuard 棘轮） | 测试计数锚：**2,194**（unittest discover 权威运行口径）/ 2,201（grep 全仓普查口径，含根 tests 7）——只升不降棘轮可用本报告 §1.2 命令机检；与 R1=24,252 代码行锚互补 |
| **FIX-301**（归档识别修复） | 依赖前置已满足（基线已立）；本报告先例：产物仅 docs/ 的快速通道（DEC-184①）+ 全部数字带命令原文可复算 |
| **AUDIT-152**（失败定性标记） | §4 三族清单直接承接：24 bash/WSL（hook 执行面）+ 1 GBK 跳过 + 2 已知缺陷（F2 live 断言反转候选 / F3 manifest presets 对账）+ 0 回归候选 + 0 未定性；标记机制防掩盖真实回归的抽查基线 = 本报告 26 项逐条清单 |

---

## 7. 复跑命令附录（验收契约对照）

```powershell
# 验收场景：任一改动可对照基线判回归
# 固化口径（报告口径 = CI 口径 + -B）：
cd <repo-root>
python -B -m unittest discover -s skills/software-project-governance/infra/tests
# 预期（HEAD 2be00ec 测试面）：
#   Ran 2194 tests in ~361s
#   FAILED (failures=26, skipped=1)     ← 26 = §4 三族（24 环境敏感 + 2 已知缺陷）
# 失败逐项分类标记与归因 → 对照本报告 §4 清单（用例名逐一可匹配）
# 注意：pytest 等价复跑必须从插件根（cd skills/software-project-governance），否则 44 收集错误（§2.3 注 3）
```

---

## 8. 边界声明与硬门槛自检

- **零仓库修改自证**：全量运行后 `git status --porcelain` = 0 行；全程 `-B`（无字节码写入）；测试产物仅 `%TEMP%`（unittest 输出文件 + 测试自建临时目录，均系统临时域）
- **非目标遵守**：未修改任何产品/测试代码、未改 `.governance/`、未做修复（F2/F3 归因后修复属后续任务）、未放大 timeout（§5）
- **事实依据红线**：历史数字全部带 EVD 行号与 git commit 双锚；本会话每个数字带命令原文与输出行；未验证项显式标注——
  - **未验证 1**：pytest 全量运行今日未执行（collect-only 已证三方恒等 2,194；全量 pytest 与 unittest 同集合，跑一遍属冗余 6 分钟负载）
  - **未验证 2**：历史 pytest 全量（1,768/1,976/2,104）的运行 CWD 未在 EVD 记录（治理记录缺口，§2.3 注 3）；今日以插件根 CWD 验证该口径可行
  - **残差 1**：FIX-270 的 1,768 与最近可考 commit def 数 1,895 差 −127 = 运行时点与打包 commit 的日内时序（未逐 commit 对账；趋势与机制已闭合）
- **显示层注记**：unittest traceback 中文经 pwsh 捕获呈 GBK/UTF-8 错配 mojibake（FIX-278 G4/F 同域显示问题，不影响判定——证据引用取 ASCII 片段）
