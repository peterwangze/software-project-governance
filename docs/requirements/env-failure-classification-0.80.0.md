# 环境敏感失败定性标记与全量失败分类学 0.80.0（AUDIT-152）

> **Task**: AUDIT-152（P2，0.79.0∥；DEC-184 P0 波次项；RISK-048 承接）
> **角色**: Analyst Agent（测量例外口径同 AUDIT-151——只读 + 运行测试/测量命令；仓库文件修改禁止，仅两产物）
> **日期**: 2026-09-10（下午会话） | **HEAD**: `a599843`（工作树起点 clean，`git status --porcelain` = 0 行）
> **产物 2 件**: 本报告 + `skills/software-project-governance/infra/tests/env_failure_classification.json`（机器可读分类清单）
> **上游**: AUDIT-151 基线（`docs/requirements/test-baseline-0.80.0.md` §4 三族 26 例）+ FEAT-018 会话新增族（EVD-981）
> **下游**: 标记机制消费方（CI/开发者/后续 FIX 任务）；FEAT-018 容差校准切片

---

## 1. 方法节（口径 + 命令原文）

### 1.1 口径

| 项 | 口径 | 值 |
|---|---|---|
| 权威运行命令 | 与 CI 同源（AUDIT-151 §2.3 裁定）：`python -B -m unittest discover -s skills/software-project-governance/infra/tests`，仓库根执行 | 见 §2 |
| 计数规则 | unittest：`Ran N` 计方法数；subTest 失败逐个计入 failures（AUDIT-151 §2.3 注 4） | — |
| 分类学 | 五类：**环境敏感**（bash/WSL/GBK/负载）/ **已知缺陷**（F2/F3）/ **数据耦合**（新类：测试钉死的数据面合法演化——审查文档 claim / 治理归档副作用）/ **真实回归候选** / **未定性** | §3-§4 |
| RISK-048 因果证伪链方法（沿用 AUDIT-151 §3/§5） | ①当日全量实录（负载条件随数字一并引用）②单跑复现（`-k` 串行）对照 ③历史记录对锚（EVD 行号 + git commit 双锚）④负载协变量显式化 | §2/§5 |

### 1.2 命令原文（全部可复现）

```powershell
# 当日全量实录（产物证据：%TEMP%\audit152_unittest_full.txt，全文保留）
$t0=Get-Date; python -B -m unittest discover -s skills/software-project-governance/infra/tests `
  2>&1 | Out-File -Encoding utf8 "$env:TEMP\audit152_unittest_full.txt"; $t1=Get-Date
# → Ran 2304 tests in 716.848s / FAILED (failures=31, errors=1, skipped=1) / exit 1 / 墙钟 717.5s

# 六新例单跑复现（串行；discover -k 多模式过滤）
python -B -m unittest discover -s skills/software-project-governance/infra/tests -v `
  -k test_replay_real_plan_tracker_hits -k test_claim_command_emits_complete_pass_report `
  -k test_fixture_identity_mode_agrees_with_engine_on_present_sources `
  -k test_identity_host_source_drift_reproduces_divergence_shape `
  -k test_real_repository_inventory_complete_and_within_budget `
  -k test_three_run_performance_identity_and_median
# → Ran 6 tests in 185.497s / FAILED (failures=5, errors=1)   ← 与全量逐一同形（§5）

# 扫描器直跑（完整 findings 清单——单因/双因归因的权威证据）
python -B -c "…sys.path.insert(0,'skills/software-project-governance/infra'); import checks.loop_runtime_claims as lrc; …"
# → verdict BLOCKED / findings=4（1 authority + 3 UNSUPPORTED_AFFIRMATIVE，见 §5.1）

# 权威行计数（AUTHORITY_SOURCE_OCCURRENCE 归因）
Select-String -Path ".governance\decision-log.md" -Pattern '^\| DEC-104 \|'   # = 0（live）
Get-ChildItem ".governance\archive\*.md" | Select-String -Pattern '^\| DEC-104 \|'  # = 1（archive）
```

---

## 2. 当日全量实录（2026-09-10 下午，HEAD a599843）

| 项 | 值 | 证据 |
|---|---|---|
| 收集（Ran） | **2,304** | 输出行 `Ran 2304 tests in 716.848s` |
| 通过 | 2,271（2,304 − 31F − 1E − 1skip） | 同上推导 |
| 失败 | **31 failures + 1 error** | `FAILED (failures=31, errors=1, skipped=1)`；exit 1 |
| 跳过 | 1（GBK 负对照，预期行为） | 同上；AUDIT-151 §4-F0 同项 |
| 耗时 | **716.848s**（unittest）/ 717.5s 墙钟 | Stopwatch |
| 环境条件 | Windows 本机；本会话内近似串行（诚实披露：运行期间执行过若干**亚秒级只读命令**——git 元数据查询、文件读取、一次 python JSON 结构读取（<1s）——非同主体测量，但严格「零并发命令」口径未完美保持，如实登记；§5.3 的 ≈2× 漂移量级无法由 <2s 亚秒级读取解释） | 本会话 |

### 2.1 与三条历史口径对账（算术闭合）

| 口径 | 时点 | 数字 | 与今日差异（全部 git/治理记录锚定） |
|---|---|---|---|
| AUDIT-151 基线 | 2026-09-10 上午，HEAD `2be00ec` | 2,194 / 26F / 1skip / 361.1s | 今日 +110 测试（FIX-300 +3〔EVD-976〕→ FEAT-017 +31〔EVD-977〕→ FEAT-020 +27〔EVD-979〕→ FEAT-019 +38〔EVD-980〕→ FEAT-018 +19〔EVD-981〕→ FIX-301 +7〔EVD-982 "test_archive 119→126"〕：2,194+110=2,304 精确闭合）；+6 失败项（§3 逐例） |
| FEAT-019 自述 | commit `c443757` | 2,278 / "健康 31 恒等" | 2,278 + 19（FEAT-018）+ 7（FIX-301）= 2,304 ✓ |
| FEAT-018 全量 | EVD-981（2026-09-10，commit `1bb4268` 邻域） | 2,297 / 30F+1E | 2,297 + 7 = 2,304 ✓；失败面差异 = +1F（`test_replay_real_plan_tracker_hits` REL-071——EVD-983 真迁移在 FIX-301 commit **之后**执行，迁移副作用属 FEAT-018 口径之后新浮现；§5.2）+ 组成漂移（FEAT-018 的 1E 记为「RISK-048 族」且未留 test ID——今日串行环境下 adapter 用例不超时、以数据耦合 F 形态出现，§5.1/§5.2） |

---

## 3. 失败逐例分类（32 项 + 1 跳过，覆盖 100%）

### F1 — 环境敏感（bash/WSL）×24 失败（存量，计数与 AUDIT-151 逐项一致）

- **用例**：`test_pre_commit_review_evidence.ReviewEvidenceRegexTests` 10 方法 × hook∈{pre-commit, commit-msg} subTest = 24 项（8 方法×2 + `test_blockers_tail_must_be_exactly_zero` 2 变体×2 + `test_d_needs_change_misses_both_forms` 2 形态×2）。当日实录 24 行 FAIL 与 AUDIT-151 §4-F1 清单**逐行同名**（实录文件可查）。
- **证据**：traceback `hook function run failed: rc=1`，stdout 为 UTF-16 WSL 错误（`wsl.exe --list --online` / `WSL_E_DEFAULT_DISTRO_NOT_FOUND`）——hook 以 WSL bash 执行，本机无默认发行版。
- **复跑对照**：Linux CI（ubuntu-latest 原生 bash）预期转绿（AUDIT-151 同判）。
- **since**：≤2026-08-25（FIX-278 时点 EVD 已记「24 bash/WSL 环境」，evidence-log L1553 经 AUDIT-151 §4-F1 引）。

### F0 — 环境敏感（代码页）×1 跳过（预期行为）

- `test_utf8_read_guard` GBK 负对照，skip 理由 `system ANSI codepage is 65001, not 936 (GBK)`。非缺陷。

### F2 — 已知缺陷 ×1：live 断言过期（存量）

- `test_triage_write_guard.GovernanceWriteGuardPlanTrackerTests.test_live_plan_tracker_flags_only_known_m1_rows`：`AssertionError: set() is not true : live M1 four rows must be flagged`（L533）。FIX-293（2026-09-09，EVD-963）修复数据后断言未反转——非产品回归（守卫 CLI 当时与今日均 PASS）。修复候选：断言反转为 `assertEqual(set(), flagged)`（本任务不改测试）。**收口注记（FIX-332，2026-09-17）**：候选已由 FIX-330 采纳落地（2026-09-14）：`assertEqual(set(), flagged)` + 面级哨兵门禁 `assertNotIn("", flagged, face)`，当时模块 `Ran 32 OK`、`skipped=0`；FIX-332 复跑实测同结果（2026-09-17，现 35 用例含 FIX-333 GBK 反相）；「L533」为 0.80.0 时点行号快照。依据：`docs/reviews/review-FIX-330-CODE-R0.md`（同轮反相实测证伪 FIX-328/R0 F-1 前提，更正登记归 DEC-194）。

### F3 — 已知缺陷 ×1：manifest `presets/` 三方脱节（存量）

- `test_cleanup.TestPluginScopeDirs.test_all_manifest_dirs_covered`：manifest 声明 `presets/` 目录而 `PLUGIN_SCOPE_DIRS` 与磁盘均无（AUDIT-151 §4-F3 同项）。修复属后续对账任务。

### N1 — 数据耦合（审查文档 claim）×5：`docs/reviews/review-FIX-300-CODE-R0.md` 触发 loop-runtime claim 扫描 BLOCKED（**新增族①，今日定性**）

共同根因：该审查文档（`e994c7a` 2026-09-10 10:57 入库）§3.4 消费面实证段（L73/L75/L79 邻域，locator `accounting:71:1 / 71:4 / 72:1`）同时命中主题正则（loop-runtime 族）与断言式措辞正则（AFFIRMATIVE_RE——『已/自动』前缀接完成类动词等形态，claim_id 见 JSON 清单），且未入 allowlist 绑定（13 条活跃面规则全部禁止现役声明）→ 扫描器判 `UNSUPPORTED_AFFIRMATIVE` ×3 → 任何要求 semantic verdict=PASS 的测试确定性失败。**单跑=全量逐一同形（6 例合并复现 5F+1E，185.5s）——非顺序/负载依赖。**

| # | test_id | 形态 | traceback 要点 | 因果 |
|---|---|---|---|---|
| N1a | `test_verify_workflow.FIX300DualCaliberAgreementTests.test_identity_host_source_drift_reproduces_divergence_shape` | FAIL | L197 `assertEqual("PASS", semantic.verdict)` → `'PASS' != 'BLOCKED'`（installed_host 语义扫描真实仓库） | 仅审查文档因（installed_host 跳过 authority 校验，L1240-1241） |
| N1b | `test_verify_workflow.FIX300DualCaliberAgreementTests.test_fixture_identity_mode_agrees_with_engine_on_present_sources` | **ERROR** | L177→verify_workflow.py L20735 `sys.exit(1)` 未捕获 → `SystemExit: 1` | 审查文档因（必然）+ DEC-041 归档因并存（§N2；任一独立足以 FAIL） |
| N1c | `test_loop_runtime_claims.LoopRuntimeClaimTests.test_real_repository_inventory_complete_and_within_budget` | FAIL | L904 verdict 断言；findings 前 5 = 1×`AUTHORITY_SOURCE_OCCURRENCE`(decision-log found 0) + 3×`UNSUPPORTED_AFFIRMATIVE`(审查文档) | **双因并存**（§N2 + §N1）——扫描器直跑实证 findings 恰 4 条 |
| N1d | `test_loop_runtime_claims.LoopRuntimePerformanceAndGoldenTests.test_three_run_performance_identity_and_median` | FAIL | L1082 `identities[0][0]` `'PASS' != 'BLOCKED'`；finding_snapshots = 3×(UNSUPPORTED_AFFIRMATIVE, review-FIX-300) | 仅审查文档因（`:index` 干净克隆无 `.governance` → authority 校验 FIX-240 豁免） |
| N1e | `test_verify_workflow.LoopRuntimeClaimAdapterTests.test_claim_command_emits_complete_pass_report` | FAIL | L51 `assertEqual(0, completed.returncode)` → `0 != 1`（真实 CLI 子进程，stderr 空） | 审查文档因（+ §N2 若默认口径含 authority——rc=1 已由语义面独立充分） |

> **与任务包口径的如实差异**：任务包/FEAT-018 记新增族①为「4 例」+「RISK-048 族 1 例（1E）」。今日串行实录为 **5 例全确定性数据耦合 + 0 例负载失败**：FEAT-018 并行会话中 N1e（timeout=15s 的 CLI 子进程）大概率以 `TimeoutExpired` ERROR 形态成为其「1E RISK-048 族」（EVD-981 未留 test ID，不可考——如实标注）；串行环境下同一测试不超时、以 rc=1 断言失败（数据耦合 F）呈现。两口径不矛盾：**同一组 5 个测试，暴露形态随负载条件切换**。

### N2 — 数据耦合（治理归档副作用）×0 独立失败例（**新增族②，并入 N1b/N1c 呈现**）

- **机制**：`core/loop-runtime-claim-authority.json` 三条 pinned source_records 之一 `| DEC-104 |`（decision-log，期望恰好 1 次出现）——EVD-983 真数据迁移（2026-09-10，FIX-301 commit 之后执行）将 58 条 decision 迁出 live 文件（decision-log 205.7→104.1KB）→ live 计数 0、archive 计数 1（本会话实测）→ `AUTHORITY_SOURCE_OCCURRENCE: found 0`（loop_runtime_claims.py L1271-1273）→ product_release 口径（host `.governance` 存在时）单独即足以 BLOCKED。
- **独立破坏力证明**：N1c 的 findings 列表同时含两因；若仅有 N2（无审查文档），N1c/N1b/N1e 仍将失败——两条因果链**各自独立充分**，今日恰好同时落地。
- **暴露面**：N1c/N1b（+N1e 若 CLI 默认 product_release）；N1d（克隆无 `.governance`）与 N1a（installed_host 跳过校验）**不受**此因影响。

### N3 — 数据耦合（live plan-tracker 行）×1：`test_hooks.PlanTrackerMatcherTests.test_replay_real_plan_tracker_hits (task_id='REL-071')`（**新增，EVD-983 后新浮现**）

- **traceback**：test_hooks.py L312 `assertTrue(_run_pattern("REL-071", plan_text))` → `False is not true`（仅 REL-071 subTest 失败；REL-072/FIX-282/REL-073/FIX-283/FIX-288 均 HIT，FIX-9999 MISS）。
- **根因**：live 重放测试钉死「加粗 ID 代表 REL-071 必须 HIT」；EVD-983 迁移（88 task 行迁出）后，live plan-tracker 中 REL-071 仅存于 evidence 单元格（L171/L173 等）与路线图行（L411，首格非优先级）——按 FIX-282 锚定匹配器设计**正确 MISS**（test L265-270 明定非任务表行不得满足存在性）。匹配器行为正确，测试钉死的 live 数据前提过期。
- **时序证明**：AUDIT-151（迁移前）26F 无此项；FIX-301 自证「全量 31F/E 零新增」在其 commit（a599843）时点为真；EVD-983 迁移在其后执行 → 本例为**迁移后浮现**，非任何 commit 时点回归。

### 计数汇总（验收①核对：32 项 + 1 skip 全覆盖）

| 分类 | 计数 | 明细 |
|---|---|---|
| 环境敏感（bash/WSL） | **24**（失败） | F1 存量族 |
| 环境敏感（代码页 GBK） | **1**（跳过） | F0 预期行为 |
| 环境敏感（负载/RISK-048） | **0**（当日复现） | 潜在暴露 ×2 测试（N1d median<8s 断言、N1e timeout=15）——§5.2 |
| 已知缺陷 | **2** | F2（测试断言过期）、F3（manifest presets） |
| 数据耦合（审查文档 claim） | **5**（4F+1E） | N1a-e |
| 数据耦合（治理归档副作用） | **0 独立**（并入 N1b/N1c；authority finding 1 条） | N2 |
| 数据耦合（live plan-tracker 行） | **1**（失败） | N3 |
| 真实回归候选 | **0** | 全部 32 项带 traceback/复跑/行计数/git 锚归因 |
| 未定性 | **0** | — |

---

## 4. 分类学定义（供 JSON 与后续复用）

| class（JSON 枚举） | 定义 | 判据 |
|---|---|---|
| `env_sensitive` | 测试结果由执行环境决定（bash/WSL 运行时、系统代码页、机器负载），代码与数据均无缺陷 | 换环境（Linux CI / GBK 机 / 串行窗口）预期转绿或按设计 skip |
| `known_defect` | 已登记缺陷（测试面或清单面），失败可复现且根因已定性、修复方向已明 | 有 EVD/审查登记 + 修复候选 |
| `data_coupling` | 测试钉死的**数据面前提**被合法演化（新文档入库、治理数据归档/修复）打破——代码与扫描器行为均正确 | 单跑=全量确定性复现 + 数据演化事件 git/治理记录锚定 |
| `regression_candidate` | 疑似真实回归（代码变更引入），需升级 Developer 排查 | 排除前三类后的失败 |
| `unclassified` | 证据不足，如实标注 | — |

`family` 细分字段：`bash_wsl_hook` / `codepage_gbk` / `load_timing` / `test_assertion_stale` / `manifest_presets` / `review_doc_claim` / `authority_archive_side_effect` / `live_plan_tracker_row`。

---

## 5. 新增族定性结论（4+1+1 任务的三个新族）

### 5.1 族①（FIX-300 审查文档 claim）——定性：数据耦合，确定性，非回归

- **定性**：审查报告是「关于 claim 的记录」而非产品声明，但其措辞同时命中主题正则与断言式措辞正则且未绑定 → 5 测试确定性失败（§3-N1，单跑=全量实证）。
- **自证注记（AUDIT-152 实录）**：本报告初稿的根因引述段自身曾被 Check 31 标记一条（UNSUPPORTED_AFFIRMATIVE，与族①同机制）——讨论 loop-runtime claim 的任何新文档都可能落入该判定面；本报告随后按扫描面改写措辞并复跑健康检查确认零残留（§8）。这使族①的豁免/绑定裁决成为**反复出现**的问题而非一次性事件，权重支持 notice 绑定候选。
- **候选方向评估（FIX-295 式 docs/reviews 豁免扩展，一句）**：技术可行（FIX-295 先例 = Check 10 M5 对 docs/release+docs/reviews 的记录类豁免 + 披露，wrapper 架构，commit `fc1b739`），但本扫描器的既定机制是**notice 绑定而非目录豁免**（allowlist 7 条历史 claim 全部以 `loop-runtime-superseding` notice 绑定于 docs/release、docs/requirements 文件——从未对 docs/ 整族豁免）；**推荐先走 allowlist notice 绑定**（为该文档 3 个 clause 加 historical_claims + superseding notice，保留扫描覆盖），目录级豁免会打开一个不受审计的 claim 面、属策略变更需 Design Reviewer 裁决。

### 5.2 族②（RISK-048 负载敏感历史族）——当日 **0 复现**（串行），因果证伪链沿用结论成立

- 当日全量（近似串行）与 6 例单跑中，median<8s 断言与 timeout=15 均未以负载形态触发（N1d 失败于其**前面的** verdict 断言 L1082，median 断言未及求值——负载敏感性今日被数据耦合**遮蔽**，非证伪）。
- 历史对锚：EVD-962/964/967（2026-09-09，1 failure LoopRuntime 环境超时）→ AUDIT-151 串行 0 复现 → FEAT-018 并行会话 1E（EVD-981，test ID 未记，不可考——如实标注）。结论沿用 AUDIT-151：**该族仅在并行治理负载下暴露；套件级结论须以串行窗口为准（RISK-048 纪律）**；容差校准归 FEAT-018 后续切片（EVD-981 已登记「查方差源」）。
- 附带发现：N1e（timeout=15 真实 CLI 子进程）与 N1d（median<8s）是族②的**双潜在暴露点**，JSON 以 `latent_class` 标记。

### 5.3 族③（全量耗时同机漂移）——定性：环境敏感（负载/同机方差），当日实测 **717.5s**

- 当日 716.848s vs AUDIT-151 361.133s（同机、同口径、串行条件近似）= **1.99×**；+110 测试仅解释 ≈+5%（0.165s/测试外推 ≈ +18s），残差 ≈1.85× 未解释——与 EVD-981 已披露的 summary 命令同机串行漂移 1.65×（41.31→69.97s，「查方差源（首批切片任务）」）同族同向。
- **任务包「361s→706s（FEAT-018 记录）」核实结论**：仓库与 `.governance/` 全文检索无 706s 锚（最近可验证记录 = EVD-981 的 41.31→69.97s summary 漂移）；该数字应属 FEAT-018 会话未入库的口头/工作树记录——**与本日实测 717.5s 量级吻合**（采信为同族观测，不作事实引用）。方差源定位与容差定档归 FEAT-018 切片任务，本报告只登记不裁决。

---

## 6. 标记机制（最小面：数据先行，零测试代码改动）

### 6.1 产物

`skills/software-project-governance/infra/tests/env_failure_classification.json`——schema：`tests: { <test_id>: {class, family, evidence, since, ticket, count?, latent_class?, notes?} }` + 顶层 `suite_summary`（当日实录数字）+ `classes`（枚举定义）。test_id 采用 unittest 输出原形（文件模块.类.方法）；subTest 族以 `count` 字段计 multiplicity（F1 十方法合计 24）。

### 6.2 消费方式（建议——接线属后续任务，本任务不实现）

| 消费者 | 方式 | 性质 |
|---|---|---|
| CI / 开发者（后处理对照脚本，**推荐**） | 跑完套件后提取全部 `FAIL:`/`ERROR:` 的 test_id 集合，与本 JSON keys 做差集：**出现未登记 id → 新失败按回归候选处理（loud fail，防掩盖）**；登记 id 消失（转绿）→ 提示分类清单过期待清理。~30 行 Python，零测试代码改动 | 数据面即可落地 |
| 测试代码接线（`skipUnless`/`expectedFailure`） | 理论上可由测试动态读取本 JSON 决定 skip/expect——**明确不做**（改测试代码越本任务界；且 WSL 族在 Linux CI 应真跑而非 skip） | 后续 FIX 任务裁决 |
| 报告/人工抽查 | 本报告 §3 表 + JSON 逐例 `evidence` 字段即 AUDIT-151 设想的「防掩盖真实回归的抽查基线」 | 已落地 |

### 6.3 边界声明（如实）

- 本任务**未改任何既有产品/测试代码**（验收⑤：本任务写入仅 2 个新文件——本报告 + JSON；会话同期工作树另见并行任务 DOC-003 的产物 `docs/requirements/data-inventory-0.80.0.md`，非本任务写入面，与本任务零文件冲突）。
- JSON 是**当日截面**（2026-09-10 / HEAD a599843），数据演化（下一份审查文档入库、下一次归档迁移、F2/F3 修复）后须同步更新——更新责任归后续对应任务，消费脚本应把「登记 id 转绿」视为过期信号而非错误。
- `ticket` 字段 null = 尚无专属任务；§7 的候选任务建议是推荐、不代执行。

---

## 7. 处置建议（逐族候选任务，不执行）

| 族 | 建议 | 优先级参考 |
|---|---|---|
| F1 bash/WSL ×24 | 不改测试；以 JSON 标记 + §6.2 对照脚本消费（Linux CI 已天然转绿；Windows 本机属已知环境差） | P3 |
| F2 live 断言过期 | 断言反转 `assertEqual(set(), flagged)` + docstring 更新（AUDIT-151 已给候选；测试面一行修复） | P2 |
| F3 manifest presets | manifest 条目与 `PLUGIN_SCOPE_DIRS`/磁盘三方对账（存量候选） | P2 |
| N1 审查文档 claim ×5 | **推荐** allowlist notice 绑定 3 clause（保留覆盖，先例 = 7 条 historical_claims 机制）；备选 FIX-295 式目录豁免（策略变更，需 Design Reviewer）；配套流程建议：docs/reviews 入库前跑一次 `check-loop-runtime-claims`（可入审查 checklist） | P1（5 例红灯面） |
| N2 authority 归档副作用 | authority JSON source_records 契约扩展「archived source」状态或 re-pin（archive 为机器本地 gitignored 文件——契约如何对待归档源属设计决策，建议 Design Reviewer + Governance Developer） | P1（与 N1 并存双因） |
| N3 live plan-tracker 行 ×1 | 更新 live 重放代表 ID（选当前 live 的加粗行）或改用固定 fixture + live 冒烟分层；配套建议：归档迁移（EVD-983 类）验收清单加入「跑 test_hooks live 重放」 | P2 |
| RISK-048 负载族 | 归 FEAT-018 容差校准切片（EVD-981 已登记方差源调查）；套件级结论继续以串行窗口为准 | 既有任务承接 |
| 耗时漂移（§5.3） | 归 FEAT-018 切片定档（summary/全量各自容差）；登记同机 1.65×~2× 观测 | 既有任务承接 |

---

## 8. 边界声明与硬门槛自检

- **零仓库修改自证**：全程 `-B`；唯一写入 = 2 个产物文件（本报告 + JSON，均为新增，不改任何既有文件）；测试产物仅 `%TEMP%`（unittest 实录 + 测试自建临时目录）；未改 `.governance/`（本任务只读引用 evidence-log/plan-tracker/archive）。
- **硬门槛遵守**：允许面内仅运行了测试与统计命令；每例证据可复查（traceback 行号 / 单跑命令 / 行计数命令 / git-EVD 双锚）。
- **事实红线（未验证项如实标注）**：①FEAT-018 的 1E test ID 未在 EVD-981 留痕——其与本会话 N1e 的同一性为**机制推演**（timeout=15 + 并行负载），不可考；②任务包「706s」无仓库锚（§5.3）；③全量运行期间有亚秒级只读命令（§2 诚实披露）；④N1e 的 CLI 默认扫描口径（是否含 authority 校验）未单独验证——rc=1 已由语义面独立充分，不影响定性。
- **健康零新增（验收⑥）**：本任务 2 产物均为数据/文档面（docs/requirements/*.md 不入治理检查面；infra/tests/ 新增 .json 经 manifest `infra/` 目录型条目自动接纳，无结构违约）。**过程实录（A/B 实测）**：报告初稿落盘后 `check-governance --summary-only --level strict` = `31 issues`（含本报告被 Check 31 标记的 1 条——措辞自证，§5.1 自证注记）；按扫描面改写后复跑 = **`30 issues`、引用本任务两产物的条目 = 0**——本任务前后健康面**净变化 = 0**。当日 30 项中 Check 31 残留 3 条为族①审查文档（`e994c7a` 起既有，非本任务新增；即 §5.1 所述 recurring 面的健康侧表现），其余为存量结构项（28n e2e 夹具 / 28p 重复码等）。
