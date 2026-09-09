# Code Review — FEAT-011 (R2)

| 项 | 值 |
|---|---|
| Task | FEAT-011 — G3 扩展：写时结构看护引擎扩展至 Coordinator 直写路径（复审轮） |
| Round | **R2**（Code 面第 2 轮；按交错占轮先例对应 review-record `--round 2`） |
| 前轮引用 | `docs/reviews/review-FEAT-011-CODE-R0.md`（R0 = review-record `--round 1`：**APPROVED_WITH_NOTES**，P0=0 / P1×1 / P2×2 / P3×3，`unresolved_blockers=0`；Design 面独立 R0 已 APPROVED_WITH_NOTES/0，不在本轮范围） |
| Reviewer | Code Reviewer Agent（独立派发，只读审查） |
| 日期 | 2026-09-09 |
| 审查对象 | R0 之后的增量 delta（工作树未提交变更之上，HEAD 仍为 `1d3d973` 与 R0 相同）：① F-1 修复 `verify_workflow.py` L12726-12729（`_validate_execution_packet` 委托后补非 dict 早退）；② F-2 修复同文件 L22004-22023（face 3 `locks_path.is_file()` 门控）；③ 回归用例 ×2（`tests/test_triage_write_guard.py` L626-633 / L653-686）。净行数变化与 R0 stat 对比（verify +399→+404、tests +314→+359）恰容两修复 + 两用例，无范围外改动（git status 仍仅 2 M 文件） |
| **结论** | **APPROVED_WITH_NOTES**（P0=0；R0 F-1/F-2 闭环；新发现仅 P3×2；`unresolved_blockers=0`） |

---

## 1. 审查方法与边界

- 逐行通读 delta 三块（F-1 三行 / F-2 门控块 / 两用例）及其上下文；对照 `git show HEAD` 原实现（F-1 恒等论证）与 R0 报告逐条比对。
- 独立探针（脚本 `%TEMP%\feat011_r2_probe.py`，只读仓库、临时目录写入）：三型+扩展型非 dict 探针、HEAD 参考实现恒等电池组（15 输入，含异常路径两侧对比）、Check 18c 端到端畸形包 ×3、face 3 缺席/在场-畸形双探针。
- 全部回归命令独立复跑（§2），含 HEAD 干净快照 A/B（`git archive` + 当前 `.governance` 数据）与双解释器（3.14.3 / 3.13.13）交叉。
- 只读审查：未修改任何产品代码与 `.governance/` 记录；本报告为唯一写入产物。

## 2. 回归事实独立复核（全部自跑，非转述）

| # | 事实（Developer 声明） | 独立复核结果 | 证据 |
|---|---|---|---|
| 1 | pytest `test_triage_write_guard.py` → **32 passed** | ✅ 仓库根 CWD：`32 passed in 0.25s`（含活体金丝雀实跑）。**可复现性边界（新记录）**：从 `infra/` CWD 运行得 `31 passed, 1 skipped`——被 skip 者为活体金丝雀 `test_live_plan_tracker_flags_only_known_m1_rows`，其 `SAMPLE_PATH.is_file()` 自解除条件经 `resolve_entry.resolve_host_root`（cwd 优先）在 infra CWD 下解析失败所致，属运行目录伪象而非用例缺陷（本审查首轮即踩中，已定位并从正确 CWD 复现 32） | 本机复跑 ×2 |
| 2 | unittest 全量 **Ran 775 / failures=1（既有定性 LoopRuntimeClaimAdapterTests）** | ✅ 仓库根 CWD：`tests=775 failures=1 errors=0 skipped=0`，唯一失败 `LoopRuntimeClaimAdapterTests.test_claim_command_emits_complete_pass_report`（R0 已定性：subprocess 型环境预算）。**过程披露**：首轮从 `infra/` CWD 运行得 `failures=10`（9× HotFact/External + 1× LoopRuntimeClaim）；经三步定性排除本 delta 责任——(a) HEAD 干净快照（同 `.governance` 数据）A/B：同名 10 失败完全一致；(b) 双解释器（3.14/3.13）HotFact 组同样 9 失败→非版本差异；(c) 仓库根 CWD 下 HotFact 组 failures=0（`[FAIL]` 行为被测检查的预期 stdout）→ **CWD 敏感伪象**（infra CWD 下 host root 回退改变 harness 解析），R0 的 failures=1 由此在正确 CWD 精确复现 | 本机复跑 ×5 + HEAD 快照 A/B |
| 3 | 三 gate PASS | ✅ `check-manifest-consistency` PASS / `check-cross-references` PASS（infra CWD 可跑）；`check-locks` 需仓库根 CWD：`Active tasks: 2, File locks: 3, Result: PASS`（与派发声明 3 文件锁一致） | 本机复跑 |
| 4 | `check-governance --summary-only` = **79 零新增** | ✅ `共 79 issues`（仓库根 CWD）。零新增结构性成立：F-1 已证与 HEAD 恒等（§4，dict 包输出逐字节不变）；F-2 仅改 `check_governance_write_shapes`，grep 证实其消费点仅定义处 + 自身 CLI 入口 `cmd_governance_write_guard`（L21911/L22163/L22177），不在 check-governance 主链。79 vs R0 时 87 的差值源于轮间其他任务的数据修复（.governance 数据漂移），非本 delta 代码效应 | 本机复跑 + grep |
| 5 | TDD 红 `2 failed`（AttributeError @ L12728 精确复现 / 'FAIL' != 'SKIPPED'） | 过程性声明无工件可复核，标**未验证**；但构造性成立：R0 报告已实证委托版在非 dict 包上 AttributeError（其 PROBE1）；F-2 修复前面 3 缺席经 Check 26 返回 missing issue → FAIL ≠ SKIPPED（R0 探针实证）。本轮探针（PROBE-3/4）在修复后代码上验证了对应的绿路径 | 静态判定 + 本轮探针 |
| 6 | 三型探针返回 `['packet must be object']` 无异常 | ✅ 独立复现，且扩展至五型（str/list/int/**float/bool**）全部 `['packet must be object']` 无异常（PROBE-1）；helper 三型同（PROBE-1b） | 本轮探针 |

## 3. R0 逐条比对表（复审协议硬门槛）

| R0 # | 级别 | 摘要 | R2 状态 | 事实依据 |
|---|---|---|---|---|
| F-1 | P1 | `_validate_execution_packet` 委托后丢失非 dict 早退 → Check 18c 崩溃路径 | **已修复** ✅ | L12727-12729 委托后补 `if not isinstance(packet, dict): return issues`；恒等论证独立验证通过（§4）；Check 18c 端到端三型畸形包结构化 FAIL 零崩溃（PROBE-3）；回归用例就位且实跑通过（32 之一） |
| F-2 | P2 | face 3 无 `is_file()` 门控，缺席 → FAIL 与面 1/2/4 及 docstring/CLI 契约不一致 | **已修复** ✅ | L22005 `locks_path.is_file()` 门控；缺席 → SKIPPED issues=[]（PROBE-4，四面 1/2/4 PASS + 3 SKIPPED，exit-1 条件不置位）；在场但畸形仍 FAIL 且 detail 正确（PROBE-5，门控未过度抑制）；docstring「Absent files SKIP their face」四面均成立；result 初始 `"agent_locks": SKIPPED` 不再是不可达死值；回归用例就位且实跑通过 |
| F-3 | P2 | 测试补强缺口 ×4（RECO 列数 / 面 3 缺席 / unreadable / SKIPPED 面 exit-0） | **部分修复**（关键缺口已补） | 「面 3 缺席分支」由 `test_agent_locks_absent_skipped_not_failed`（L626-633）覆盖——恰为 F-2 未被开发期暴露的那个缺口；其余三项（RECO 列数破坏、面 1/2 unreadable、SKIPPED 面 CLI exit-0）仍无用例，R0 已定性「其余为可选补强」→ 未修复（登记遗留） |
| F-4 | P3 | 测试模块 docstring 面 4 权威表述指 `_validate_execution_packet`（实际消费 helper） | **未修复（登记遗留）** | docstring L25 仍为「Check 18c ``_validate_execution_packet``」——措辞未改，R0 已判定语义主张成立仅指称不精确 |
| F-5 | P3 | face 2 col-mismatch `task_id` 双解析路径 | **未修复（登记遗留）** | L21881 仍 `stripped.split("|")[1].strip()`——未统一 |
| F-6 | P3 | 测试跨 TestCase 实例化复用 helper | **未修复（登记遗留）** | L694 仍 `GovernanceWriteGuardLocksAndPacketsTests()._result(...)` |

R0 遗留判定与派发说明完全一致：F-3 其余 / F-4~F-6 不在本轮范围，标注如上。

## 4. F-1 恒等论证独立验证（验收标准 2 专项）

**Developer 论证**：helper 对非 dict 恰返回 `['packet must be object']`，故委托后 `return issues` 与 HEAD 早退恒等。**独立验证结论：论证成立**，双通道证据：

1. **源级**：HEAD 原实现（`git show` 提取）首二行 `issues = []; if not isinstance(packet, dict): return ["packet must be object"]`。新实现委托的 helper（L12710-12711）对非 dict 返回同一字面量单元素列表 `["packet must be object"]`——**值恒等**（每次调用新列表，无共享状态别名；helper 为纯函数 docstring 声明 + 零 I/O 复核）。求值顺序安全：委托在前不影响（helper 自身先判 isinstance 立即返回，无副作用）。
2. **运行时**：从 `git show HEAD` 字节级提取参考实现 exec 后对拍（避免手工转录误差），15 输入电池组：合法包 / task_id 不匹配 / scope 过宽 / required_evidence 缺两 token / done_definition 无审查 token / 深缺字段 / 空白字符串 / 空数组 / 带空白项数组 / 混合类型数组 / str / list / int / float / bool / None——**0 处不一致**（PROBE-2）。其中混合类型数组（`required_evidence=["事实依据：x", 5]`）两侧同抛同型同消息 `TypeError`（`" ".join` 处）——HEAD 保留行为，恒等性恰恰要求保留它（见 §6 N-2）。

## 5. 五维度逐项结论（delta 范围 + 回归面）

### 5.1 正确性 — 通过
- **F-1**：非 dict 早退恢复 HEAD 语义（§4 双通道恒等）；dict 分支零变化（电池组含全部语义检查路径 0 mismatch）；Check 18c 端到端三型畸形包返回结构化 FAIL entry `{'task_id': 'FIX-301', 'status': 'FAIL', 'issues': ['packet must be object']}`，`pass=False`，零异常（PROBE-3）。R0 记录的「该分支行为恒等声明不成立」缺陷消除——恒等声明现在对全部分支成立。
- **F-2**：门控条件、SKIP 语义、对称性（面 1/2/4 同构）、非过度抑制（在场畸形仍 FAIL）全部实证（PROBE-4/5）；CLI exit 契约不变（SKIPPED 永不置位 failed）。
- 边界：bool/float（int 子类与标量延伸）亦命中早退（PROBE-1 五型）；None 走 Check 18c 既有「missing execution packet」独立分支（电池组含 None，0 mismatch）。

### 5.2 安全性 — 通过
- delta 零新输入面：两修复均在内部分派路径上；无 eval/exec/subprocess/网络/凭据；issue 消息拼接仅控制台展示。OWASP 关键项（输入校验/注入/敏感数据/权限）对 delta 逐项扫描无适用违规。F-1 修复反而消除了一个畸形输入致命令崩溃的 DoS 面（崩溃→优雅 FAIL）。

### 5.3 可维护性 — 通过
- F-1 修复以最小行数（3 行含注释）恢复恒等，注释 `# HEAD-identical early exit: ["packet must be object"]` 精确自证；F-2 以与邻面同构的门控实现，可读性优于 R0 建议的备选案 (b)（修订文案保留不对称）。两用例 docstring 均回链 R0 finding 编号与根因，可追溯性好。R0 遗留 F-4/F-5/F-6 见 §3。

### 5.4 性能 — 通过
- F-1 增加 1 次 isinstance（纳秒级）；F-2 增加 1 次 is_file() stat（面 1/2/4 同型）；无算法/数据结构变化；`check_governance_write_shapes` 消费点未变（仅自身 CLI），主链零开销。pytest 套件 0.25s（与 R0 0.31s 同量级）。

### 5.5 测试覆盖 — 通过
- 两新用例断言强度充分：三型探针 `assertEqual(..., ["packet must be object"], packet)`（失败消息带输入）；Check 18c 端到端 `assertEqual(result["entries"], [{...}])` **整结构精确匹配**；face 3 缺席双断言（status=SKIPPED + issues=[]）。套件 30→32 全绿（仓库根 CWD）。覆盖缺口现状见 §3 F-3 行（遗留）。

## 6. 新发现（本轮引入视角）

| # | 级别 | 位置 | 事实 | 影响 | 处置建议 |
|---|---|---|---|---|---|
| N-1 | **P3** | `tests/test_triage_write_guard.py` L673-686 | Check 18c 端到端畸形包断言仅覆盖 str 型（list/int 只在单元层 `_validate_execution_packet` 探针覆盖） | 广度注记：单元层三型 + 端到端 str + 路径分析已足够防护（本审查 PROBE-3 已补证端到端 list/int 亦不崩溃），风险极低 | 可选：端到端参数化扩至三型 |
| N-2 | **P3**（信息性） | `verify_workflow.py` L12735（语义块 `" ".join`） | 混合类型数组包（如 `required_evidence=["x", 5]`）在 HEAD 与新版**同抛** `TypeError`（PROBE-2 异常路径对拍）——HEAD 既有行为，非本轮引入，且 F-1 的恒等契约恰恰要求保留 | 到达需「字段为 list 但元素非 str」的对抗性畸形包；此时字段检查已记 issue，随后语义块崩溃（响亮失败非静默）；当前仓库数据不可触发 | 登记为独立遗留候选任务（Check 18c 健壮性增强）；**不得**随 FEAT-011 修——会破坏刚验证的 HEAD 恒等 |

**新引入 P0/P1 = 0**；两新发现均为 P3。

## 7. AI 代码专项 5 项检查（delta 范围）

| # | 检查项 | 结论 | 证据 |
|---|---|---|---|
| 1 | mock 残留 | ✅ 无——生产代码零 mock；两新用例 `mock.patch` 均 with 作用域即撤（L680 等） | grep + 逐行 |
| 2 | 硬编码返回值 | ✅ 无新增判定性硬编码——`["packet must be object"]` 字面量是 HEAD 恒等契约的**要求**（复刻 HEAD 字面量），非替代判定的硬编码 | §4 + 逐行 |
| 3 | 幻觉 API 调用 | ✅ 无——delta 引用符号（`_execution_packet_field_issues`/`isinstance`/`locks_path.is_file`/`check_agent_locks_format`）全部定位存在；探针与 32/775 全量实跑通过即活性证明 | 探针 + 复跑 |
| 4 | 未实现 TODO | ✅ 无——delta 区零 TODO/FIXME/XXX/NotImplemented（grep 全文件仅 mock 模式命中） | grep |
| 5 | 过度实现 | ✅ 无——恰为 R0 建议的最小修复（F-1 一行 + 注释；F-2 门控 + 对称）；无顺带重构、无超范围改动（git status 仍 2 M 文件，行数与声明吻合） | diff stat 比对 |

## 8. 硬门槛裁决与结论

| 门槛 | 阈值 | 裁决 |
|---|---|---|
| P0 阻塞问题数 | = 0 | ✅ 0（新发现仅 P3×2） |
| 复审协议（round 声明 + 前轮引用 + 逐条比对 + 不看前轮不 APPROVED） | 满足 | ✅ 头部声明 R2 + R0 引用；§3 六条逐条比对（已修复×2 / 部分修复×1 / 未修复登记×3） |
| 5 维度全覆盖 | 100% | ✅ §5.1-5.5 逐一有结论 |
| 每条发现标注级别 | 100% | ✅ §3/§6 全部带 P 级 + 位置 + 事实 + 依据 |
| 事实依据红线 | 无未验证即写成已通过 | ✅ TDD 红标「未验证（构造性成立）」；其余全部本机复现（§2/§4） |
| AI 专项 5 项 | 全部完成 | ✅ §7 |

### 结论：**APPROVED_WITH_NOTES**

- **`unresolved_blockers=0`**
- 通过理由：R0 两项 MUST notes（F-1 P1 / F-2 P2）均闭环且经独立双通道验证（恒等电池组 0 mismatch / 缺席-在场双探针）；回归四项声明全部独立复现（32 passed / Ran 775 failures=1 既有 / 三 gate PASS / 79 零新增——含结构性零新增论证）；delta 零新引入阻塞或关键问题；R0 采纳的修复方案与其建议案 (a) 一致（两处均取推荐案）。
- 保留 notes（均不阻塞）：§3 F-3 其余三项 + F-4/F-5/F-6（R0 登记 legacy，本轮按约不处理）；§6 N-1/N-2（P3 新注记，N-2 须独立任务处理不得随 FEAT-011 修）。
- 本结论仅为代码审查门通过，不替代测试审查与发布审查。

## 9. 事实依据索引

- delta 代码：`verify_workflow.py` L12726-12743（F-1 + 语义块）、L22003-22023（F-2）；`tests/test_triage_write_guard.py` L626-633 / L653-686
- HEAD 对照：`git show HEAD:…verify_workflow.py`（`_validate_execution_packet` 原实现，字节级提取 exec 为对拍参考）
- 探针：`%TEMP%\feat011_r2_probe.py`（PROBE-1/1b/2/3/4/5 全输出留存）
- 回归复跑：pytest 32 passed（仓库根）/ unittest `tests=775 failures=1 errors=0`（仓库根，唯一失败 LoopRuntimeClaimAdapterTests——R0 既有定性）；infra-CWD 伪象两例（31+1skip / failures=10）及其 HEAD 快照 A/B + 双解释器 + CWD 对照定性过程（§2 #1/#2）
- 三 gate：manifest PASS / cross-references PASS / locks PASS（2 active / 3 file locks，仓库根）
- check-governance：`共 79 issues`；`check_governance_write_shapes` 消费点 grep（L21911/22163/22177）
- R0 报告：`docs/reviews/review-FEAT-011-CODE-R0.md`（F-1~F-6 原文、恒等/探针先例、774/775 既有定性）
