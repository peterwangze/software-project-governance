# FEAT-016 Code Review R0 — RISK-049 关闭标准③：dsh 升级回归固化为 release gate 组件

## 元信息

| 项 | 值 |
|----|----|
| Task | FEAT-016（RISK-049 关闭标准③；plan-tracker.md L289；P2，0.79.0；DEC-177 ③ 承接） |
| Round | **R0**（首轮独立审查；无前轮 findings 比对义务） |
| 基线 | 审查对象 = commit `213fbba0b464006e441ef747689a4c0c13ef57bf`（2026-09-09；parent `58f8e9f`）；2 files changed, 480 insertions(+) |
| 范围 | verify_workflow.py（+115：`run_dsh_upgrade_regression_gates` L7035-7077 + `check_release_readiness` 尾参 L7091/接线块 L7250-7294 + `cmd_check_release` SKIP 分支 L20579-20587）；test_verify_workflow.py（+365：`Feat016DshUpgradeRegressionReleaseGateTests` L7175-7541，13 新用例） |
| Reviewer | Code Reviewer Agent（只读审查；除本报告外未创建/修改任何产品或治理文件；全部验证操作 = git 只读（`git show`/`git log -L`/`git log --oneline`）+ 文件读取 + grep——无测试运行、无工作树/环境变更） |
| 审查依据 | `agents/code-reviewer.md` + `skills/code-review/SKILL.md`（全文加载并遵循）；TRIAGE-FEAT-016（`.governance/change-triage/FEAT-016.json`，声明 files=本两文件）；RISK-049 行（`.governance/risk-log.md` L49 关闭标准(3) 原文）；EVD-970（开发者结构化返回） |
| Date | 2026-09-09 |

## 终态结论

**APPROVED_WITH_NOTES** — `unresolved_blockers=0`

P0 = 0（无阻塞项）。P1×1 / P2×2 / P3×3 全部为非阻塞发现。唯一 P1（F-1）是**既有缺陷的独立核验确认**（FIX-199/200/202/213 引入的 `cmd_check_release` 无条件 `result["pass"] = False`，非本任务引入、未被本任务加剧、开发者已如实披露）——修复它超出 FEAT-016 的 triage 声明面（越权），按 SKILL 第四步「P0=0 且 P1>0（有遗留计划）→ 有条件合并」处理为遗留项（建议 Coordinator 登记后续 FIX 任务）。引擎层（`check_release_readiness`）的 gate 阻断语义经逐行核实完全正确。满足 code-review SKILL 循环角色段通过终态契约：无未解决 BLOCKING finding，含独立结构字段 `unresolved_blockers=0`。

## 发现计数

| P0 | P1 | P2 | P3 |
|----|----|----|----|
| 0 | 1 | 2 | 3 |

## 5 维度逐项结论表

| 维度 | 结论 | 关键事实（可复查） |
|------|------|---------|
| 正确性 | ✅ 通过（F-1 为既有 CLI 层缺陷，引擎层无缺陷） | **接线**：三分支逻辑 L7264-7273 逐行核对——`not run_execution_gates` → skip（--skip-execution-gates 披露）；`lineage_mode == "released" or gate_seq_mode == "released"` → skip（BR-4/DEC-153 ② 披露；`gate_seq_mode = gate_sequence_lineage_mode or lineage_mode` L7210，两入口均覆盖）；else 实跑 `(dsh_upgrade_regression_runner or run_dsh_upgrade_regression_gates)()`（L7275-7276）。**阻断语义**：FAIL → `issues.extend(f"dsh upgrade regression: {issue}")`（L7280-7281，前缀与其他组件一致如 L7242 "execution gate:"）→ `result["pass"] = not issues`（L7344-7345）= False。**skip/WARN 语义**：skip 时 `dsh_regression_issues=[]` → `pass=True`（L7283）、`required=False`、runner 不被调用（测试 L7418/L7436/L7462 `assert_not_called` 三重实证）、不追加 issues → 不误 FAIL（BR-4 历史查询保护正确）。**超时转发链**：`_resolve_release_gate_timeout(os.environ.get(_RELEASE_GATE_TIMEOUT_ENV, ""))`（L7050-7051）与 `_run_release_validation_command` 先例（L5964-5967）逐字同构；默认 180（L5936）、非法值回退（L5940-5954）；`smoke_runner(timeout=timeout)`（L7052）→ `check_dsh_preset_smoke(root=None, timeout=120)`（L6942）的 timeout 形参真实生效（L6976 subprocess timeout=timeout，TimeoutExpired → verdict FAIL L6978-6980 → gate FAIL）。**隔离继承与清理**：FEAT-016 runner 零新子进程构造——完全委托 FEAT-015 `check_dsh_preset_smoke`（temp `mkdtemp` L6963 + `DSH_HOME` 重定向 L6965-6966 + finally `rmtree(ignore_errors=True)` L6984-6985 + 真实 home 写入拒绝 L6995-7001）；`isolation` 字段透传重命名（temp_home→temp_dsh_home，L7065-7072）。**exit_code=None 边界**：smoke 超时/launcher 缺失路径 `exit_code=None`（L6955）→ gate exit_code=None，与 `_run_release_validation_command` 异常路径形状（L5982）一致，CLI 打印 "(exit=None)" 可接受。 |
| 安全性 | ✅ 通过 | 无新攻击面：runner（L7035-7077）不构造 env、不拼接 shell 命令——子进程环境构造全部在 FEAT-015 既有代码（L6965-6977，`os.environ.copy()` + 单键覆盖 `DSH_HOME`，argv 列表形式，无 shell=True，R0 已审）；`command` 字段（L7061-7063）为纯展示字符串（`sys.executable` + `launcher.as_posix()` 常量拼接），不回流入执行。无敏感数据硬编码（grep diff 无 token/path 凭据）。temp 目录规范继承：`tempfile.mkdtemp` 前缀化 + finally 清理（FEAT-015 既有，本 diff 未触碰）。CLI SKIP 分支（L20580-20587）仅格式化打印已有 detail 字段，无新输入面。 |
| 可维护性 | ✅ 通过（附 F-5/F-6 P3） | **形状一致性**：gate dict（L7055-7064）与 execution gate 结果形状逐字段对齐（label/pass/exit_code/issue/command ↔ L5992-5997）；`details["dsh_upgrade_regression"]` 键集（pass/skipped/skip_reason/required/results/issues/isolation/boundary）在既有 `required`（L7233/L7246）、`boundary`（L7138-7143）先例上仅增 skipped/skip_reason/isolation 三个语义自明键。**命名一致**：`dsh_upgrade_regression_runner` 尾参镜像 `execution_gate_runner`（L7086）/`gate_sequence_lineage_mode`（L7090）先例。**复用无重实现**：runner 是 44 行薄适配器（结果形状归一化），冒烟逻辑 100% 委托 FEAT-015——docstring 明示 "reuse only — never a reimplementation"（L7043）。**注释质量**：块注释（L7019-7030）记录 risk 行号/需求溯源/M7.7 (a)/FIX-234 先例，接线块注释（L7250-7259）解释 BR-4 双模式 skip 理由——超出本仓平均水准。重复度：无产品面重复；测试 `_release_patches`（L7187-7212）与相邻测试类的 patch 清单存在相似性，属测试 fixture 常态。 |
| 性能 | ✅ 通过（附 F-4 P3） | **不必要重复子进程分析（任务重点）**：单次全量 `check-release`（execution gates 开启）中 launch.py --smoke 子进程运行次数 ≈ 3：① FEAT-016 gate 直接 1 次；② "governance health" gate（L6012）→ check-governance → Check 28u 1 次（L16412，若 product gate active）；③ "unit tests" gate（L6014，仅跑 test_verify_workflow.py）内 `test_FEAT_016_real_regression_run_...`（L7525）真实 1 次（FEAT-015 的真实冒烟测试在 test_dsh_adapter.py——不在该 gate 命令面内）。该放大是聚合 gate 架构的固有模式（每个 gate 本就互相重跑对方工作，verify/e2e/unit 互嵌先例成立），FEAT-016 净增 = 1 直接 + 1 嵌套，每次冒烟受 timeout 上界约束（默认 180s，env 可调）且 temp home 用后即删——无泄漏累积。check-governance 与 check-release 同会话各跑一次 smoke 属两命令各自语义（健康检查 vs 发布门），非不必要放大。无 N+1、无算法问题（全部 O(1) 适配层）。**超时保护有效性**：见正确性维度——三层（env 覆盖 → resolve 回退 → subprocess timeout）链路完整，超时归一为 FAIL issue 而非挂死。 |
| 测试覆盖 | ✅ 通过（附 F-2 P2） | **13 用例逐一对照任务要求的 7 个面**（无形式化测试——每条均断言行为/调用次数/打印行，非仅不抛异常）：① 阻断=引擎级 L7400（result pass=False + "dsh upgrade regression:" 前缀）+ CLI 级 L7491（[FAIL] 行 + REGRESSION_LABEL + Result: FAILED）；② skip=L7417（skipped=True/pass=True WARN/required=False/runner `assert_not_called`/零 issues/result pass=True 五重断言）；③ BR-4（gate-sequence released）=L7432（seq_mock 断言 `lineage_mode="released"` 入参 + runner 未调用 + "BR-4" 在 skip_reason）；④ explicit released lineage=L7455（lineage_mode="released"+release_commit 路径）；⑤ timeout 转发=L7320（SPG_RELEASE_GATE_TIMEOUT=300 → seen=300）+ L7339（env 清除 → 默认 180）；非法值回退由既有 FIX-234 测试覆盖（L7105-7146，grep 实证）；⑥ CLI 可见性=L7479（[PASS] 组件行 + "(exit=0)" 明细行 + 无 [FAIL]——并对 F-1 既有 quirk 作了诚实注释）/L7491（FAIL）/L7500（[SKIP]+理由+无 PASS 无 FAIL）；⑦ 真实隔离=L7525（零 mock 真跑：pass + exit 0 + real_home_writes=0 + `Path(temp).exists()=False` 清理验证）。**生产接线防漂移**：L7387 断言默认 runner 恰被无参调用一次（`assert_called_once_with()`）——钉住"生产路径 = 真实 runner"不被测试缝漂移。**采信声明**：测试通过结果（811 passed + 89 subtests 等）采信开发者 EVD-970 结构化返回（本审查只读未运行）；测试文件内容审查确认断言与被测行为真实对应、无自证断言（`_fake_regression`/`_smoke` fixture 仅用于接线测试，runner 逻辑由 L7320/L7339/L7352/L7525 直接覆盖）。 |

## 发现列表

| # | 级别 | 位置 | 事实依据 | 影响 | 修复建议 | 处置 |
|---|------|------|---------|------|---------|------|
| F-1 | P1（既有缺陷独立核验；非本任务引入） | verify_workflow.py L20568（`cmd_check_release`）；引入 commit `4134026`（FIX-199/200/202/213，2026-07-17） | **独立核验结论（任务 F-1 项）**：① `git log -L 20564,20570` 实证该行由 4134026 引入（diff 上下文逐字可见 `+ result["pass"] = False`，无注释、无条件守卫），早于 213fbba 两个月——**既有缺陷，开发者声称属实**；② 逐行核对 FEAT-016 diff：未触碰该行、未改变其输入（claim gate 注入路径 L20564-20567 原样）——**未被 FEAT-016 加剧**；③ 实际影响：CLI `cmd_check_release` 无条件 FAILED + exit 1（即使全组件 PASS + 0 issues）——**引擎层无恙**（`check_release_readiness` L7344 的 `pass=not issues` 正确，FEAT-016 阻断语义在引擎层完整成立），受损的是 CLI verdict 区分度：自动化无法以 exit 0/1 判定发布就绪，且长期"狼来了"效应削弱所有 gate 行（含新 gate）的信号价值——方向为 fail-closed（无假绿灯风险），但 exit-1 归因只能靠 [FAIL] 组件行 + issue 计数。开发者已如实披露（EVD-970 + 测试 L7479 注释），披露口径准确 | FEAT-016 的"机器强制"语义在引擎层达成；CLI 层 exit-1 不可归因于单一 gate。修复超 triage 声明面（change-triage files 仅两文件——修复需动 `cmd_check_release` 语义属独立变更，且需独立回归验证全绿→exit 0 路径） | 后续 FIX 任务（建议 Coordinator 入账）：L20568 改为 `result["pass"] = not result["issues"]`（或按 claim_gate 状态条件化），配全绿 → `Result: PASSED`/exit 0 回归测试；同时复核 FIX-199 当时是否有"release 必须 attestation"的 fail-closed 设计意图（查 4134026 关联 review）再定夺 | 遗留项（有遗留计划；不阻塞本任务——按 SKILL「P0=0 且 P1>0 有遗留计划 → 有条件合并」） |
| F-2 | P2 | test_verify_workflow.py L7491-7499（`test_FEAT_016_cli_regression_failure_blocks_with_exit_1`） | 测试名与断言 `assertEqual(1, exit_code)` 声称证明"regression 失败 → exit 1"，但 F-1 quirk 下 exit 1 对任何输入恒真——该断言的归因强度为零；实际载荷由 `[FAIL] dsh upgrade regression` 行断言承担（引擎级阻断已由 L7400 独立证明，语义无缺口，纯测试强度问题） | 未来若 F-1 被修复（exit 0 成为可能），本测试仍通过但不再覆盖"仅 regression 失败"场景的精确性；CLI 层阻断归因缺一条精确断言 | 补一行：`assertIn("Result: FAILED - 1 issue(s)", text)`（该 CLI 测试的 patch 面下其他 gate 全 PASS、issues 恰 1 条——计数断言使 exit-1 归因闭合） | 遗留候选（不阻塞；可随 F-1 修复任务一并做） |
| F-3 | P2 | verify_workflow.py L7019-7024（块注释）vs L7035-7052（实际组成）；`.governance/risk-log.md` L49 关闭标准(3) 原文 | 块注释第一句称「the dsh upgrade regression checklist (isolated re-verification command set, readme.md L380-440 — **temp DSH_HOME link:/file: re-checks**, launch.py preset install, --smoke) becomes a machine-enforced part of release readiness」——但实际组成（docstring "Composition (minimal, per triage)" L7038 + boundary 字段 L7290-7293 "not a live marketplace upgrade"）仅为 FEAT-015 冒烟（launch.py 预设安装/加载面）；README L444-450 命令集中的 `dsh plugin add link:/file:` pnpm 侧复验（依赖真实 dsh CLI + pnpm + 网络）**不在机器 gate 内**。关闭标准(3) 原文「dsh 升级回归清单（隔离复验命令集）固化为 release gate 的一部分」的字面范围宽于交付组成 | 代码无缺陷、boundary 披露到位、EVD-970 未声称整体关闭；但若以无限定措辞关闭标准(3)，将声称 link:/file: 复验已机器化而实际未含——构成 RISK-049 自身定义的宣示-验证等级缺口（元层复现；同构先例：FEAT-015 R0 F-1 / FEAT-014 R0 F-3 的限定收口处置） | 关闭标准(3) 时措辞限定：「preset-session 冒烟子集已机器强制入 release gate；`dsh plugin add` link:/file: pnpm 侧复验依赖宿主二进制与网络，维持人工/隔离手工清单，登记后续候选」——或经 decision-log 修订标准措辞后关闭。可顺带把 L7021-7023 注释首句改为"the core executable subset of the checklist" | Coordinator 决策项（关闭该风险/标准前 MUST 执行）；注释措辞可随下轮顺带收紧 |
| F-4 | P3 | verify_workflow.py L7052（直接运行）+ L16412（Check 28u）+ L6014（unit tests gate 命令面）+ test L7525（真实冒烟测试入 test_verify_workflow.py） | 全量 check-release 单次运行 launch.py --smoke ≈ 3 次（直接 gate + governance-health gate 内 Check 28u + unit-tests gate 内真实测试）；FEAT-015 的真实冒烟测试在 test_dsh_adapter.py 不受该 gate 覆盖，FEAT-016 的在——净增 1 直接 + 1 嵌套。每次秒级、隔离、自清理、timeout 上界 180s | 发布运行时成本增加（有界）；聚合 gate 固有模式的延续，非新架构债 | 可选：为嵌套场景加 env 守卫（如 `SPG_RELEASE_GATE_NESTED=1` 时真实冒烟测试 self-skip）或在 release 文档标注预期成本；不改亦可接受（先例一致） | 遗留候选（讨论级） |
| F-5 | P3 | verify_workflow.py L20580-20587（泛化 `[SKIP]` 分支） | 分支条件 `detail.get("skipped")` 对**所有** details 生效：skipped 组件跳过 results/issues/boundary 打印。grep 全文实证当前 `check_release_readiness` 19 个 details 键中仅 `dsh_upgrade_regression` 含 "skipped"（其余 "skipped" 键属于非 release 检查 L17502/L15606，不经此循环）——今日行为安全；`skip_reason` 为 None 时会打印 "— None"（构造上不可能，仅理论） | 未来组件复用 skipped 键时隐式获得 SKIP 打印且静默丢失明细行——契约未文档化 | 在分支注释中补一句"details carrying a truthy `skipped` key print as [SKIP] without results/issues lines"固化契约；或 skip 分支也打印 boundary | 遗留候选（讨论级） |
| F-6 | P3 | verify_workflow.py L7275-7276（`(dsh_upgrade_regression_runner or run_dsh_upgrade_regression_gates)()`） | 用 `or` 惰性取默认而非参数默认值（`dsh_upgrade_regression_runner=run_dsh_upgrade_regression_gates`）——差异在可测性：`or` 形式在调用时解析模块全局，测试 `patch.object(vw, "run_dsh_upgrade_regression_gates)`（L7389/L7418/L7436/L7462/L7502 五处）得以拦截默认路径；参数默认值会在 def 时绑定原函数使 patch 失效。与 `execution_gate_runner=_run_release_validation_command`（L7086）的默认值先例形成 idiom 分叉，但后者经 `run_release_execution_gates(runner=...)` 显式传参，机制不同 | 无功能影响；未来"统一风格"的无知重构（改成默认参数）会静默破坏 5 处测试拦截 | 在 L7275 上方补一行注释说明 `or`-idiom 的 patchability 用意（防止善意简化） | 遗留候选（讨论级） |

## AI 代码专项 5 项

| 检查项 | 结论 | 事实依据 |
|--------|------|---------|
| Mock 残留 | ✅ 无 | 产品代码增量（verify_workflow.py L7019-7077/L7250-7294/L20579-20587）零 mock/桩/测试符号；`smoke_runner`/`dsh_upgrade_regression_runner` 两缝均为显式命名参数 + None 生产默认（L7048-7049 回落真实 `check_dsh_preset_smoke`），测试 patch 全部 `with` 块内即用即释；diff 增量 grep `TODO\|FIXME\|XXX\|HACK\|Mock\|mock` 仅命中测试文件注释性说明（"run_release_execution_gates is faked because…"，L7277-7281——对 mock 理由的诚实文档化，反模式反面） |
| 硬编码返回值 | ✅ 无 | gate 判定链全执行结果驱动：`passed = smoke["verdict"] == "PASS"`（L7054）← 子进程 returncode + 输出正则（FEAT-015 L6987-6996）；skip 判定 = 两个布尔条件（L7264/L7269）；`pass = not dsh_regression_issues`（L7283）——无任何硬编码 PASS/FAIL 路径；`command` 字符串为展示常量（非执行输入） |
| 幻觉 API | ✅ 无 | 逐符号核实存在且签名正确：`check_dsh_preset_smoke(root=None, timeout=120)`（L6942，`timeout=` 关键字调用合法）、`_resolve_release_gate_timeout`（L5940）、`_RELEASE_GATE_TIMEOUT_ENV`（L5937）、`PLUGIN_ROOT`（L132）、`sys.executable`/`os.environ`（既有 import）；返回结构契约对齐：`smoke["isolation"]` 的 `temp_home`/`real_home_writes` 键在 FEAT-015 全部返回路径初始化（L6952-6958，.get 防御 L7066-7067）；测试侧 `SimpleNamespace`/`ExitStack`/`redirect_stdout` 均为测试文件既有 import（L26/L29，grep 实证） |
| 未实现 TODO | ✅ 无 | diff 两文件增量无 TODO/FIXME/NotImplemented/placeholder/`pass` 占位（diff 全文逐行通读）；所有分支（run/skip×2）均有实现与对应测试（13 用例映射完整） |
| 过度实现 | ✅ 无 | 变更严格限于 TRIAGE-FEAT-016 声明 files 两文件（commit --stat 实证恰 2 files）；无新 CLI 子命令、未触碰 check-governance/Check 28u（复用而非扩张）；CLI `[SKIP]` 分支为任务描述明示交付物（"cmd_check_release 详情打印新增 [SKIP] label — reason 分支"）；13 测试 = 任务描述明示数量，无冗余用例；`boundary`/`isolation`/`mechanism` 字段均有消费者（CLI 打印 + 测试断言） |

## F-1 开发者申报独立核验（任务指定项）

**结论：声称属实，P1 定级成立，不构成本任务 BLOCKING。**

1. **是否既有**：是。`git log -L 20564,20570:verify_workflow.py` 实证 `result["pass"] = False` 由 commit `4134026`（FIX-199/200/202/213，2026-07-17，review APPROVED_WITH_NOTES unresolved_blockers=0）引入，距 213fbba 两个月；开发者自述"~L20568，FIX-199/200/202/213 引入"与事实逐项吻合（现位于 L20568）。
2. **是否被 FEAT-016 加剧**：否。213fbba 未触碰 L20564-20568 及其输入链；新 gate 仅通过 `issues.extend`（L7280）增加 issue 计数——FAILED 输出的信息量增加，语义结构未变。
3. **对本次 gate 语义的实际影响**：引擎层（`check_release_readiness` 返回值）阻断语义完整且正确——这是 RISK-049③"机器强制"的承载层；CLI 层 exit-1 恒真使"exit 1 = 被阻断"不可推断，归因依赖 `[FAIL] dsh upgrade regression` 组件行 + issue 计数（两者均正常工作，测试 L7491 已断言）。方向为 fail-closed（永不假绿灯），风险是信号疲劳而非放行。开发者披露（EVD-970 + 测试注释 L7486-7489）如实、准确、未淡化。
4. **修复归属**：超出 FEAT-016 triage 声明面——按"过度实现 = 越权"红线，本任务不修是正确选择；建议 Coordinator 以独立 FIX 任务收口（建议要点见发现列表 F-1 行）。

## 硬门槛裁决

| 门槛项 | 阈值 | 裁决 | 依据 |
|--------|------|------|------|
| P0 阻塞问题数 | = 0 | ✅ 通过 | 发现计数 P0=0（F-1 为 P1 既有缺陷） |
| 5 维度全覆盖 | = 100% | ✅ 通过 | 5 维度逐项结论表（正确性/安全性/可维护性/性能/测试覆盖各有一行结论 + 可复查事实） |
| 每条发现标注级别 | = 100% | ✅ 通过 | 6 条发现（F-1~F-6）均含 P 级标签 + 文件:行号 + 事实依据 + 修复建议 |
| 每条结论指向可复查事实 | = 100% | ✅ 通过 | 全部结论锚定 文件:行号 / git log -L 输出 / commit stat / 测试方法名；测试通过结果采信开发者 EVD-970 结构化返回并已显式标注采信口径（本审查只读未运行测试——无"已运行通过"类未验证表述） |
| 设计一致性检查 | 已完成 | ✅ 通过 | 与 FEAT-015 先例（`check_dsh_preset_smoke` 复用、Check 28u、CLI 子命令）及 BR-4/DEC-153 ②（gate_seq_mode 判定、WARN 不误 FAIL）逐项对齐；与 FIX-234 超时先例逐字同构；RISK-049③ 需求语义（机器强制非仅披露）在引擎层达成——限定条件见 F-3 |
| AI 代码专项 5 项 | 全部完成 | ✅ 通过 | 5 项逐一有结论 + 事实依据（上表） |

## 结论与建议

实现质量高：薄适配层复用 FEAT-015 冒烟（零重实现）、三分支接线语义精确（run/block/skip×2 全部测试钉住）、形状与命名对齐先例、生产接线有防漂移测试（L7387）、真实隔离有零 mock 用例（L7525）。RISK-049③ 的"固化为 release gate 的一部分（机器强制）"在引擎层达成：execution gates 开启的 candidate 发布中，冒烟 FAIL → issues → `pass=False`，无法静默通过。

两项 Coordinator 决策前提：(1) 关闭标准(3) 的归因措辞必须限定组成（F-3——preset-session 冒烟子集；link:/file: pnpm 侧维持手工清单或登记后续）；(2) F-1 既有缺陷建议独立 FIX 任务收口（CLI verdict 区分度，fail-closed 方向故不紧急）。

**终态：APPROVED_WITH_NOTES，`unresolved_blockers=0`**（P1×1 为既有缺陷遗留项 + P2×2/P3×3 建议项，均无 BLOCKING finding）。
