# FIX-359 独立代码审查报告 — Code Review R0（round 0）

- **Task ID**: FIX-359（P2；triage 机录 `.governance/change-triage/FIX-359.json`）
- **审查对象**: 工作树未提交 diff，恰 2 文件——
  - `skills/software-project-governance/infra/tests/test_hooks.py`（+49/−13）
  - `skills/software-project-governance/infra/tests/test_pre_commit_review_evidence.py`（+42/−3）
- **审查者**: Code Reviewer Agent（独立，只读 + 本报告唯一写入面）
- **修复语义**: RISK-056 匹配器族 30→0——A 族 hook 回放 6 项（fixture 漂移，静态钉→运行时派生）+ B 族 review evidence 24 项（环境耦合，bash 名解析→功能探测绝对路径）
- **机器标记**: 本报告为人工审查报告；结论持久化由 Coordinator 经 review-record CLI 执行（本 Reviewer 不写 .governance/）

---

## 总结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`（P0=0 / P1=0 / P2=1 / P3=4；无 BLOCKING finding）。

双族根因均经本机实证支撑「修复而非包装」：A 族旧钉 6 ID 在 live plan-tracker 实测全 MISS（归档漂移属实），重锚后派生集 30 IDs 全 HIT；B 族 System32 WSL stub 存在且 PATH 解析命中、`bash -c :` exit=1，旧代码 `["bash", ...]` 必然解析到 stub——修复让 hook regex 首次被真实执行。零新增非族失败。

---

## 硬门槛裁决

| 门槛项 | 结果 |
|---|---|
| P0 阻塞问题数 = 0 | ✅ 0 |
| 5 维度全覆盖 | ✅ 见下表，逐项有结论 |
| 每条发现标注级别 | ✅ P2×1 + P3×4，逐条有标签 |
| 设计一致性检查 | ✅ 与 FIX-282 匹配器契约 / FIX-261 四态 regex 契约 / FIX-352/353 动态钉先例一致，无偏离 |
| AI 代码专项 5 项 | ✅ 全部完成，见专项节 |

---

## 五维度逐项结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | ✅ 通过 | 派生解析对 live 数据实测 30/30 HIT、零误 MISS；空集哨兵（`assertTrue(live_ids, ...)`）防全漂移假绿；absent-ID 前置 `assertNotIn` + MISS 语义保留；`_find_bash` 探测逻辑（which→已知路径候选→`["-c",":"]` 功能探测 rc==0）与先例逐字一致 |
| 安全性 | ✅ 通过 | subprocess 全程参数列表形式（无 `shell=True`、无字符串拼命令）；探测仅执行 `["-c", ":"]` 只读探针；硬编码路径为只读 `is_file` 候选，无注入面 |
| 可维护性 | ✅ 通过（附 P2-1 / P3-2） | 两函数职责单一、docstring 记录动机与先例出处；重复成本见 P3-2 |
| 性能 | ✅ 通过 | `_BASH = _find_bash()` 模块加载时一次性执行（非每测试）；派生解析 O(行数) 一次遍历 |
| 测试覆盖 | ✅ 通过 | 正集（live 派生 30）+ 负集（FIX-9999 前置 NotIn→MISS）+ 离线构造片段（matcher 语义钉，保留原静态钉形态）+ bash 双引擎 parity 测试全部保留；skip 语义与 test_hooks.py 既有约定一致 |

---

## AI 代码专项 5 项检查

| # | 检查项 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock 残留 | ✅ 无新增 | 本 diff 无 mock；test_hooks.py `_WG_STUB` 为既有 fixture（非本 diff 引入），且注释明确「test fixture, not a production mock」 |
| 2 | 硬编码返回值 | ✅ 无 | 探测/解析均基于真实执行与真实数据，无预设结论 |
| 3 | 幻觉 API | ✅ 无 | `subprocess.run` / `shutil.which` / `Path.is_file` / `re.fullmatch` / `re.splitlines` 均为真实标准库调用，签名正确 |
| 4 | 未实现 TODO | ✅ 无 | diff 无 TODO/FIXME 残留 |
| 5 | 过度实现 | ✅ 无 | `_live_task_ids` 约 15 行单一职责；`_find_bash` 为先例移植非新抽象 |

---

## Findings 逐项

### P0（阻塞）— 0 项

无。

### P1（关键）— 0 项

无。

### P2-1（建议）｜`_live_task_ids` 部分格式漂移静默收缩回放覆盖，非空哨兵只防「全漂移」

- **位置**: `test_hooks.py` L132-147（解析）、L341-344（哨兵）
- **事实**: 哨兵仅在解析结果为**空集**时 fail。若 live 表部分行格式漂移（如任务单元格带后缀 `FIX-xxx ✅`、优先级列出现 `***P1***` 三星形态等），这些行会被解析静默跳过 → 回放覆盖收缩，但测试仍绿（非空集即通过）。注意发散方向安全：解析比 hook ERE（`[*]{0,2}`）更宽松时，产生的失败是 fail-loud（matcher MISS 断言失败），不产生 false-pass；风险仅是「覆盖静默缩水」。
- **影响**: 不阻塞——matcher 语义另有离线构造片段测试独立钉死（test_bold/legacy/mixed/absent/mention 等 12 项），回放收缩不等于语义失守。
- **建议**: 后续批（0.85.0 ⑤ 降噪面）可加「派生计数下界」断言（如 ≥5）或与表头行计数对账，把部分漂移也转为显式失败。本轮不要求。

### P3-1（讨论）｜subtest 计数随 live 数据非确定——申报 58 vs 本机实测 59

- **事实**: `test_replay_real_plan_tracker_hits` 为每个 live ID 产生一个 subTest，总数随活跃表行数漂移。本机实测 30 live IDs → 59 subtests；Developer 申报 58（对应申报时点 29 行）。42 passed 与 0 失败两侧一致。
- **判定**: 非缺陷、非虚报——这正是本修复把静态钉改为动态派生的直接后果（计数 = f(live 数据)）。双口径如实性成立，但后续对账应预期该数字波动，宜以「42 passed + 0 failed」为稳定锚，subtest 数仅参考。

### P3-2（讨论）｜`_find_bash()` 在两个测试文件重复约 30 行

- **事实**: 与 test_hooks.py L161-183 逐字一致（docstring 扩写除外），docstring 已声明「parity by precedent」。
- **判定**: 测试文件间刻意自包含（避免测试模块互依赖）是正当取舍，非本轮缺陷；若出现第三处需要（如 hook 其他测试文件），应提取共享 helper（如 `tests/_harness.py`）。

### P3-3（讨论）｜absent-ID `assertNotIn` 前置断言与循环断言存在语义冗余

- **事实**: 若 `FIX-9999` 未来真入 live 集，前循环 `assertTrue(_run_pattern(...))` 已先失败；`assertNotIn` 形式上冗余。
- **判定**: 保留价值成立——前置断言使失败信息指向「派生集已包含该哨兵 ID，请换 absent 哨兵」而非令人困惑的 MISS 断言失败。防御性写法，非缺陷。

### P3-4（讨论）｜`skipUnless(_BASH)` 语义：无功能 bash → skip 非 fail

- **事实**: B 族 24 项在无功能 bash 环境下静默 skip（绿灯），环境退化导致的覆盖丢失不报警。
- **判定**: 与 test_hooks.py 既有约定完全一致（0.80.0「测试基线修正/环境敏感定性」批已确立该取舍），非本 diff 新增风险；边界如实记录：B 族的「真跑」依赖环境存在 git-bash/WSL/原生 bash，CI 或裸环境需知此面为 skip。`_run_hook_function` L146 `assert _BASH` 为守卫外兜底（当前所有调用方均在 skipUnless 守卫类内，属防御未来调用者），无害。

---

## 双族归因可信度审计（修复 vs 包装）

### A 族（6 项，fixture 漂移）——✅ 归因成立，修复真实

| 论据 | 本机实证 |
|---|---|
| 旧钉 6 ID（REL-071/072、FIX-282、REL-073、FIX-283、FIX-288）活跃行已归档 | 实测 6/6 不在派生集且 hook matcher 对 live plan 全 MISS（matcher MISS = 正确语义，匹配器按 FIX-282 契约工作） |
| 重锚后正集语义 | 派生集 30 IDs（含 FIX-357/359/360/361/362 等）全 HIT，`derived-but-matcher-MISS = []` |
| 空集假绿防护 | L341-344 非空哨兵存在；实测派生集 30 > 0 |
| 独立解析 vs hook ERE 互证价值 | 真实成立：解析走 string-split+fullmatch（`[A-Z]+-[0-9]+` 全匹配 + `P[0-9]+` 优先级单元格全匹配），与 hook ERE（`^ *[|] *[*]{0,2}P[0-9]+[*]{0,2} *[|] *[*]{0,2}${task_id}[*]{0,2} *[|]`）是两条独立引擎路径；任一引擎对 live 数据形态回归都会使断言失败。发散方向审计：解析仅较 ERE 宽松于星号数量（strip 全部 vs ≤2），该发散只产生 fail-loud，无 false-pass 方向 |
| 离线语义钉保留 | test_bold_priority_bold/plain、legacy、mixed、absent、mention、third-column、non-task、req-matrix、archive-pointer 等 12 项构造片段测试未删，matcher 语义不随 live 数据漂移 |

### B 族（24 项，环境耦合）——✅ 归因成立，修复真实（非 skip 包装）

| 论据 | 本机实证 |
|---|---|
| 根因：Windows CreateProcess 顺序使 `["bash", ...]` 命中 System32 WSL stub | 本机 `System32\bash.exe` 存在；`Get-Command bash`（PATH 语义）解析到 `C:\windows\system32\bash.exe`；`bash -c :` exit=1（WSL 无发行版 stub 行为）——旧代码必然 rc=1 → 输出非 HIT/MISS → AssertionError，hook regex 从未执行 |
| 算术一致性 | `ReviewEvidenceRegexTests` bash-backed subtests = 2+2+2+4+2+2+4+2+2+2 = **24**，与申报「B 族 24 项」精确吻合（另有 1 项 copies-identical 不依赖 bash） |
| 修复后真跑 | `_BASH = C:\Program Files\Git\bin\bash.exe`（功能探测选中 git-bash）；声明 1 复验 42 passed / 0 failed——24 项 regex 断言在真实 bash 下执行并通过（regex 真实 HIT/MISS 判定，非被 skip 绕过） |
| 移植保真度 | 与 test_hooks.py `_find_bash()`（L161-183）逐字一致：候选序（which→3 个 git-bash 已知路径）、探针（`["-c",":"]`，timeout=10、DEVNULL stdin、check=False）、异常元组 `(OSError, subprocess.TimeoutExpired)`、rc==0 判定，全同 |
| WSL stub 排除有效性 | 探测语义正确：stub `bash -c :` rc=1 ≠ 0 → 跳过；若宿主装有真实 WSL 发行版则 rc=0 → 该 bash 同样功能可用（`_win_to_msys_or_wsl` 的 /mnt 探测覆盖 WSL 路径形态）——排除的是「坏 stub」而非整个 WSL 类别 |

---

## 非族披露核实 + 范围纪律

| 声明 | 本机核实 | 判定 |
|---|---|---|
| test_verify_workflow.py 3→3（同集零新增） | 实测 **3 failed, 903 passed, 122 subtests**；失败集 = `LoopRuntimeClaimAdapterTests::test_claim_command_emits_complete_pass_report` + `FIX300DualCaliberAgreementTests::test_fixture_identity_mode_agrees_with_engine_on_present_sources` + `::test_identity_host_source_drift_reproduces_divergence_shape`——loop-runtime-claims / FIX-300 双口径域，与 RISK-056 回放族无语义耦合；L257 AssertionError 锚点实证（另两锚点 L95/L296 未逐行复核，失败测试名与数量同申报吻合） | ✅ 非本族，3→3 成立 |
| test_fix270_product_gates.py 7 passed | 实测 **7 passed** | ✅ |
| test_fix270 L126 归属 | L126 = `class HotFactSourceHostScopeTests(unittest.TestCase):`（Check 28c 宿主场景降级测试，类定义行）——Developer「类定义行」结论属实；该文件不在本 diff 修改面，实测全绿，「当前 HEAD 不可复现失败」成立 | ✅ |
| 范围纪律：恰 2 文件在锁面内 | `git status --porcelain` 全树恰 4 文件修改 = 2 in-scope（本审查对象）+ 2 出范围（`infra/checks/review_domain.py`、`infra/tests/test_review_closure_legacy.py`，属并行 FIX-357/361）；`test_verify_workflow.py` / `test_fix270_product_gates.py` 不在修改列表 = 零改动声明成立 | ✅ |
| verify_workflow.py 全子命令 PASSED | 实测 `== Verification Result: PASSED ==`（版本同步 / adapter 契约等全链 OK） | ✅ |

---

## 独立复验命令记录（Reviewer 自跑，非转抄）

| # | 命令（摘要） | exit | 输出摘要 |
|---|---|---|---|
| 1 | `python -c`（importlib 加载两测试模块）→ `_live_task_ids(live_plan)` + `_run_pattern` 交叉 | 0 | live_ids=30（AUDIT-154, FEAT-032~040, FIX-312/314/320/343/348~357/359~362, REL-077/080/081）；derived-MISS=[]；FIX-9999 NotIn + MISS；probe bash=`C:\Program Files\Git\bin\bash.exe` |
| 2 | `python -m pytest .../test_hooks.py .../test_pre_commit_review_evidence.py -q` | 0 | `42 passed, 59 subtests passed in 4.93s`（申报 58 = live 行数 29→30 漂移，见 P3-1） |
| 3 | `python -m pytest .../test_verify_workflow.py -q` | 1 | `3 failed, 903 passed, 122 subtests`（失败集同申报域与数量） |
| 4 | `python -m pytest .../test_fix270_product_gates.py -q` | 0 | `7 passed in 17.56s` |
| 5 | `python skills/software-project-governance/infra/verify_workflow.py` | 0 | `== Verification Result: PASSED ==` |
| 6 | System32 bash 探测（`Test-Path` / `Get-Command bash` / `bash -c :`） | 0/1 | exists=True；PATH 解析=`C:\windows\system32\bash.exe`；`bash -c :` exit=1 |
| 7 | 6 旧钉 ID 实测 | 0 | 6/6 `in live_ids: False` 且 `matcher: False`（归档漂移 + MISS 语义正确） |

---

## 边缘问题（供 Coordinator 参考，不阻塞）

1. **未独立复验项**: 无——申报 1~4 全部经本机独立复验。L95/L296 两个失败锚点未逐行打开 traceback（以失败测试名 + 数量 + 域一致性判定），如需行号级对账可在 FIX-357/361 审查链处理。
2. **subtest 计数口径**: 后续任何引用本套件数字的 evidence 应注明「subtest 数随 live 活跃表行数漂移」，稳定锚为通过/失败计数。
3. **P2-1 的处置窗口**: 建议随 0.85.0 批次⑤（测试静态版本钉机检面）一并考虑派生计数下界，本轮回不要求。
4. **review_domain.py 在途 diff**: 本审查期间工作树含 FIX-357/361 出范围 diff；声明 1 的 42 passed 是在该共存状态下实测，若彼等先行合入，建议复审时重跑声明 1 一次（成本 <5s）。

---

## 结论

**APPROVED_WITH_NOTES**（通过终态）— `unresolved_blockers=0`

P0=0，P1=0，P2=1（建议项，可遗留），P3=4（讨论项）。双族修复均「修复而非包装」，语义钉完整，范围纪律干净，非族披露如实。可合并。
