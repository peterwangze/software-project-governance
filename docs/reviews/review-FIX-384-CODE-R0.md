<!-- machine-record: FIX-384 | reviewer: code-reviewer | round-suggestion: REVIEW-FIX-384-R1 | verdict: NEEDS_CHANGE | unresolved_blockers=1 -->

# Code Review R0 — FIX-384 B-7a 归档 index-rebuild

- 审查对象：工作树未 commit diff，2 文件——`skills/software-project-governance/infra/archive.py`（实测 numstat **+260/−14**）、`infra/tests/test_archive.py`（+396/−0）；基线 HEAD `a8afcbffa8dbd57924f76c7ab338f36bece2f7ec`
- 审查者：Code Reviewer Agent（只读审查；全部反相实测在 `%TEMP%\fix384_*` 临时目录/隔离副本内，真实 `.governance/` 零写入、零 stash——并行面 FEAT-062 closure_chain.py / test_closure_chain.py 未触碰）
- 结论：**NEEDS_CHANGE**（unresolved_blockers=1——P1-1 一条；P0=0；P1×1 + P2×1 + P3×6，修复方向见 §6）

## 1. 范围与基线核实

| 项 | 结果 | 证据 |
|---|---|---|
| 审查范围恰 2 文件 | ✅ | `git status --porcelain` 4×M（另 2 文件 = closure_chain 并行面，未纳入审查、未触碰） |
| 基线 HEAD | ✅ | `git rev-parse HEAD` = `a8afcbf` |
| 增量 | ⚠️ | `git diff --numstat` = archive.py **+260/−14**、test_archive.py +396/−0；申报「+274/−14 / 总 +670」与实测差 14 行（→ P3-1，不影响实质） |
| 新测试数 | ✅ | 12 个新测试方法逐一核对（TestArchiveIndexRebuild，L921 起）；HEAD 126 methods → 工作树 138 methods（逐文件 `def test_` 计数） |

## 2. 七个 MUST 重点逐项裁决

### ① 重建语义正确性（索引=纯派生物）——✅ 成立
- `build_index()` 只写 `_index_path()`（L2283），归档文件零写入；「重建不创造数据」的边界经实测：验收链（缺失→重建→PASS）与幂等探针中归档文件 `read_bytes()` 快照逐字节不变（测试 L117-120 断言 + 探针 `idempotent_archive_untouched`/`real_copy_archive_untouched`）。
- 非结构化登记行是视图陈述（文件存在性 + 损伤分类），不引入索引之外的信息源——四类提取全部只读归档文件本身。
- **确定性**：含损伤文件的归档树上两次 `build_index()` 输出逐字节一致（探针 `determinism_two_builds_identical`）；部分损坏索引重建后与健康索引逐字节一致（测试 L192 + 探针）。
- 最强兼容证据：**真实归档隔离副本首轮 rebuild 输出与已提交 index.md 逐字节一致、`damaged_files=[]`、二轮 `changed=False`**（探针 `real_copy_*` 组）——新代码在 1131 条真实归档数据上的输出与现行索引零漂移。

### ② 损伤容错安全性（errors="replace" + U+FFFD 论证）——✅ 核心论证成立，边界需文档化
- **「ID 严格正则不可能伪造条目」独立复核通过**：四类全验——任务 ID 格注入 U+FFFD（`FIX-001\ufffd`/`FIX-\ufffd002`）→ 提取 0 行；evidence `EVD-00\ufffd1` → 0 行；`DEC-00\ufffd1` → 0 条；`RISK-00\ufffd1` → 0 条（探针 `ufffd_no_fabricate_*` 4/4）。机制根因：`[A-Z]+-\d+`、`^EVD-(?:[A-Z]+-)?\d+$`（L1012 双端锚定）、`DEC-\d+:`、`RISK-\d+` 均不含 U+FFFD 可通过的位置。
- **透传面（须知晓）**：非 ID 列的 U+FFFD 会进入索引——evidence 的 task_ids 列（L1853-1860 只校验 evd_id）、decision 标题（L2144）均为原文透传（探针 B：标题 `修\ufffd复` 原样入索引，verify PASS、损伤已报）。这是「尽力恢复」的如实语义而非伪造，但现状无文档声明（→ P3-2）。
- **行级丢弃/混合面（须知晓）**：换行字节损坏会把两行并一行——7 列格式实测：合并行只产出 1 条目，**FIX-302 整行从视图丢失、FIX-301 状态列被污染为 "FIX-302"**（探针 C1）；丢弃登记仅在文件级（damaged_files + 损伤标签），无行级清单（→ P3-3）。

### ③ 无条目文件非结构化登记（FIX-176 语义扩展）——✅ 合理，但范围宣言过宽（→ P1-1）
- 扩展方向正确：登记条件从「叙述类前缀」推广到「任意无条目」（四类对称，L2084-2093/L2115-2122/L2147-2153/L2185-2191），实现「不孤儿化」；`damaged_files` + 损伤中文标签实现「不静默吞」——双通道平衡达成。空文件/decode_errors/无条目三类标签区分清晰（`_damage_kind_label`/`_damage_description`）。
- **但「verify Check 2 PASS 可达」≠「verify PASS 可达」**：损伤的 decisions/risks 文件在 Check 2 通过后，会撞上 Check 3 的**计数口径不对称**（详下），重建后 integrity 仍 FAIL——「重建 → PASS」的承诺在 4 类中的 2 类损伤源不可达，且 Check 3 的修复提示（"Run build_index() to rebuild, then re-verify"，L2492-2493）在该角落成死循环建议。见 P1-1。

### ④ 幂等性——✅ 成立
- 完好索引：`changed=False`、索引字节不变、归档零触碰（测试 L221-243 + 探针 4 项全过）。
- `changed` 语义实现正确：缺失/不可读旧索引 → True（L2528-2541）。
- 微小边界：`changed` 比较基于 replace 解码文本（L2533/L2544），且索引可含透传 U+FFFD（②），理论上损坏旧索引可解码相等而误报 `unchanged`——字节层面文件总被重写为正确内容，影响仅限标志位（并入 P3-2）。

### ⑤ 12 测试判别力——✅ 良好（覆盖缺口见 P2-1）
- 判别力真实性抽验：全链测试的预态 FAIL 断言不是摆设——缺失索引预态断言精确到「index.md 不存在」消息（L98-100）；部分损坏预态断言 FAIL 且 fixture guard 先验证 risk 行确在健康索引中（L171-182）；garbage 索引预态 FAIL（L206-207）。实测同构预态（探针 `chain_pre_fail_when_index_missing`/`chain_garbage_index_pre_fail`）复现一致。
- CLI 测试断言首轮 `Status: rebuilt` + 二轮 `Status: unchanged (idempotent no-op equivalent)`（L401/408）——幂等申报可复现。
- 缺口：decisions/risks 的无条目登记分支与损伤恢复路径零测试（P2-1）；empty-file 全链测试缺预态 FAIL 断言、`survives_unreadable` 实测的是 decode_errors（P3-5）。

### ⑥ 验证复现——✅ 票面全绿；全量口径见 §3

| 项 | 命令 | 实测 |
|---|---|---|
| 票面套件 | `pytest tests/test_archive.py -q` | **138 passed**（0.83s）＝126 基线+12 新，零回归 |
| 真实仓库 verify（只读） | `archive.py verify --project-root .` | **Pass: True**（archived 1131 / index 1276） |
| manifest | `verify_workflow.py check-manifest-consistency` | **PASS**（actual 1013） |
| xref | `verify_workflow.py check-cross-references` | **PASS**（无 circular） |
| 全量 pytest | `pytest skills/.../tests/ -q`（仓库根） | **7 failed / 4026 passed**（6 archguard HEAD 欠账 + 1 LRC 预算，均非本票面，§3）；首跑 infra cwd 31 failed 系 **cwd 伪失败** |
| 隔离副本全链 | %TEMP% 探针（7 组 32 断言） | §2/§6 引用项全部实测通过 |

### ⑦ 向后兼容——✅ 成立
- CLI 纯增量（新增 rebuild-index 子命令，L3520-3525/L3586-3605），既有子命令零改动；`--project-root` 位置无关解析（既有 FIX-242 机制）复用，CLI 测试实证。
- `errors="replace"` 对健康文件零行为变化：合法 UTF-8 解码恒等；真实归档副本首轮 rebuild 字节级零漂移即端到端证明。
- verify 对健康数据路径逐字节同前（真实仓库 PASS + 既有 verify 测试全过）。

## 3. 全量套件失败归因（申报口径复核）

- 首跑（**从 `infra/` cwd**）：31 failed / 4001 passed——抽 3 条代表性失败查 traceback，全部为 `FileNotFoundError: ...\infra\.governance\plan-tracker.md`：**cwd 依赖伪失败**（热态测试按 cwd 解析治理文件），与被审 diff 无关（失败测试均不在 test_archive.py，且 archive.py 改动不触碰 plan-tracker 解析路径）。
- 仓库根口径重跑（`pytest skills/software-project-governance/infra/tests/ -q`，23:12）：**7 failed / 4026 passed / 1 skipped / 517 subtests**——失败清单与申报逐一对应：6×`test_archguard_ratchet`（R1MainfileBudgetTests::test_r1_passes_on_current_tree、R4×3、R7ReproducibilityTests::test_r7_committed_baseline_matches_fresh_regen、CliGateTests::test_cli_green_on_current_tree）+ 1×`test_loop_runtime_claims`（LoopRuntimeClaimTests::test_real_repository_inventory_complete_and_within_budget，`'PASS' != 'BLOCKED'` 预算域）。**均非本票面**：test_archive.py 138 全绿（含于 4026），失败 7 条无一在 archive.py 触及的代码路径。申报「7 失败已归因」**独立复现成立**。
- 票面结论不受影响：test_archive.py 在两种 cwd 下均 138/138 全绿。

## 4. 五维度裁决

| 维度 | 结论 |
|---|---|
| 正确性 | ⚠️ 主链路（缺失/损坏索引→重建→PASS、幂等、确定性）实测全对；损伤源侧 decisions/risks 存在 Check 3 口径不对称死角（P1-1）——失败方式是 fail-visible（exit 1 + issues），非静默错误 |
| 安全性 | ✅ 只读容错不写归档；重建失败 exit 1；无注入面（ID 严格正则伪造论证成立）；无敏感数据；路径校验（FIX-244 fail-closed）未动 |
| 可维护性 | ✅ 注释与实现逐句相符（含「登记只恢复索引视图，不创造数据」索引文案）；损伤分类器小而单一；改进方向：decisions/risks 提取与 Check 3 计数共享单一函数（P1-1 修复建议） |
| 性能 | ✅ 每文件多一次 `read_bytes()` 的 O(n) 分类开销，量级可忽略；套件时长波动属 LRC 域 |
| 测试覆盖 | ⚠️ 12 新测试判别力良好；但新代码 4 个登记分支中 decisions/risks 两个零覆盖，恰为 P1-1 角落（P2-1） |

## 5. AI 专项 5 项

1. **mock 残留**：无。测试的 `patch.object(archive, "ROOT"/"PLUGIN_ROOT")` 为既有 host-facts seam 惯例（L44-49 注释声明的重绑点），非 mock 逃逸。
2. **硬编码返回值**：无。损伤分类输出均为真实探测结果（read_bytes/decode）。
3. **幻觉 API**：无。`read_bytes`/`bytes.decode`/`read_text(errors=)`/`UnicodeDecodeError.start` 均标准库；`verify["pass"]/["issues"]` 键在 L2302-2307 真实存在；CLI 键与 build_index 返回 dict 逐一对应。
4. **未实现 TODO**：diff 无 TODO/FIXME。
5. **过度实现**：无。损伤分类器三态最小实现；四类登记逻辑对称、无夹带重构；closure_chain 并行面零渗漏（diff 干净限于 2 文件）。

## 6. Findings 清单

**P0：0 条。**

### P1-1（阻塞本轮合并）Check 3 计数口径与 build_index 提取口径不对称——损伤的 decisions/risks 源「重建→PASS」不可达，修复提示成死循环
- **位置**：`archive.py:2438`（verify decisions 计数 `^##\s+DEC-\d+`，无冒号要求）vs `archive.py:2144`（build 提取 `##\s+(DEC-\d+):` 要求冒号）；`archive.py:2444-2447`（verify risks 仅前缀匹配）vs `archive.py:2170-2183`（build 要求 `len(parts)>=4` 且 cells 结构）。
- **事实依据（实测）**：① DEC 头冒号字节损坏（`## DEC-042\xff: …`）→ build 登记为无条目（0 条），verify Check 3 计 1 → `count mismatch (category=decisions)`，rebuild `verify_pass=False`；② 截断 risk 行（`| RISK-099 | desc`，无尾列）→ 同型 `category=risks` mismatch，rebuild FAIL（探针 `asym_decision_colon_eaten_verify_fail`/`asym_risk_truncated_row_verify_fail`）。此前该场景在读取层即 UnicodeDecodeError 崩溃，永不触及 Check 3——**是本 diff 把损伤 decisions/risks 引入 Check 3 路径后，这条前在一个的不对称变为承诺违背**。
- **影响**：rollback-0.86.0 §8 #7 的恢复语义（归档完整性恢复）在 4 类中的 2 类损伤源死端：Check 2 通过（文件已登记）但 Check 3 永远 FAIL，且 issue 消息建议的 "Run build_index() … then re-verify"（L2492-2493）正是用户刚做过的操作。申报「隔离冒烟全链（…损伤源仍 PASS）」对 tasks/evidence 成立，对 decisions/risks 不成立（12 测试的 5 损伤态也只覆盖这两类）。
- **现状非激活**：真实归档 12 个 decisions 文件 0 个无冒号头、risk 行均完整——潜伏死角，非现行数据缺陷。
- **修复方向（二选一，Developer 裁决）**：(a) 消除不对称——decisions/risks 各定义单一共享提取/计数函数，build_index 与 verify Check 3 同源调用（推荐，同时服务 P2-1）；(b) 若判定该角落 FAIL-visible 为预期行为，则修正 Check 3 消息（损伤场景不再建议重复 rebuild）、在 `rebuild_index` docstring 与损伤描述中明示该边界、并按 P2-1 补测试锁定。
- **遗留规则**：若申请遗留，须附上述 (b) 三件套的遗留计划；否则按 (a) 本轮修复后 R1 复审。

### P2-1 新登记分支测试缺口——decisions/risks 的无条目登记与损伤恢复零覆盖
- **位置**：`test_archive.py:921-1310`（TestArchiveIndexRebuild 12 方法）——5 个损伤态测试全为 tasks/evidence（L1050 空任务文件、L1172 decode、L1195 部分损坏、L1223 无条目结构、L1246 空 evidence）；L2147-2153/L2185-2191 两个新分支无直接测试。
- **影响**：P1-1 角落无测试看护（P-v1 原则 4）；修复 (a) 后无回归网。
- **建议**：补 ≥2 测试——损伤/无条目 decisions 文件与 risks 文件各一，断言登记、damaged_files、verify 终态。

### P3-1 申报增量数字与实测 numstat 偏差
- 实测 `git diff --numstat`：+260/−14（archive.py）与 +396/−0；申报 +274/−14（总量 670 vs 实测 656）。实质内容申报（12 新测试、功能面）与实测一致，计数虚高 14 行。建议证据行按 numstat 口径修正。

### P3-2 非 ID 列 U+FFFD 透传 + `changed` 比较基于 replace 解码文本——建议文档化
- evidence task_ids（L1853-1860 只校验 evd_id）、decision 标题（L2144）、risk 描述、任务状态列均原文透传，U+FFFD 可入索引（探针 B 实证，verify PASS、损伤已报）。连带：`rebuild_index` 的 changed 比较（L2533/L2544）在 replace 解码域进行，损坏旧索引理论上可解码相等而误报 unchanged（字节层面总被重写为正确内容，影响仅标志位）。建议在 rebuild/build docstring 声明「透传为尽力恢复语义、changed 为解码文本等价」。

### P3-3 换行损坏的行级混合无行级登记
- 7 列格式两行并一行时整行丢失 + 状态列污染（探针 C1：FIX-302 从视图消失、FIX-301 status="FIX-302"）。文件级 damaged_files 如实报告，但无行级丢弃清单——「尽力恢复行级语义」的准确含义是「行正则尽力、行间边界不保证」。建议注释/docstring 声明该边界即可，不要求实现行级登记。

### P3-4 unreadable 的 narrative-* 前缀文件登记标签不含损伤语义
- unreadable 的 narrative-* 文件走 L2076-2083 分支：kind=叙述段、描述为通用文案，索引行不显示「损坏」（damaged_files 有报）。小不一致，可选修：该分支 description 拼接 damage 摘要。

### P3-5 测试小项
- `test_full_chain_index_empty_file_rebuild_verify_pass`（L1038）缺预态 FAIL 断言（其余三个全链测试均有）；`test_rebuild_survives_unreadable_archive_file`（L1172）名实为 decode_errors（真 OSError-unreadable 仅 classifier 单测经 missing file 覆盖）。判别力小瑕疵，不阻塞。

### P3-6 `build-index` CLI 不打印 damaged_files
- 仅 rebuild-index 打印损伤清单（L3596-3600）；build-index（L3578-3584）不打印。恢复入口语义下可接受，可选对称性改进。

## 7. 总结论

**NEEDS_CHANGE** — `unresolved_blockers=1`（P1-1）。

主链路（索引丢失/损坏→重建→integrity PASS、幂等、确定性、U+FFFD 不可伪造、真实数据零漂移、向后兼容）全部实测成立，实现质量整体良好；但 P1-1 的损伤源死角直接抵触本票「归档完整性恢复」的核心承诺且修复提示误导，P2-1 使该角落无测试看护。P1-1 按 §6 修复方向 (a) 或 (b) 处理 + P2-1 补测后，预期 R1 仅需核对修复点即可转 APPROVED_WITH_NOTES；P3×6 均不阻塞。

*取证留存：`%TEMP%\fix384_probe.py` / `fix384_probe2.py` / `fix384_probe3.py` / `fix384_probe_results.json` / `fix384_archive.diff` / `fix384_test.diff`；本报告为唯一仓库内写入物。*
