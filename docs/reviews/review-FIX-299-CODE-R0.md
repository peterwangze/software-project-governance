# Code Review — FIX-299-R0：cmd_check_release 恒 exit 1 修复（staged diff，commit 前置审查）

| 项 | 值 |
|---|---|
| Task ID | FIX-299 |
| 审查 round | **R0**（首轮；无前轮引用） |
| 审查对象 | staged 未提交改动（`git diff --cached`）——本仓 hook 要求 FIX- 前缀产品代码 commit 前置审查，无 commit hash |
| 变更面 | 恰 2 文件 +133/−6：`skills/software-project-governance/infra/verify_workflow.py`（+8/−1）、`skills/software-project-governance/infra/tests/test_verify_workflow.py`（+130/−5）；`git status --short` 实证 M-staged-only、无越权文件 |
| Reviewer | Code Reviewer sub-agent（角色定义 `agents/code-reviewer.md` + `skills/code-review` SKILL 全文加载执行） |
| 日期 | 2026-09-10（与 EVD-975 同日，后置审查） |
| 审查约束 | 只读：只读 git（diff --cached / show）+ 读文件 + grep；**未运行测试**（采信 Developer 结构化返回 EVD-975：TDD 红→绿、选择集 5 passed、全量 813 passed + 89 subtests、healthy 面仓库级实录 `Result: PASSED` + EXIT=0）；唯一产物 = 本报告 |

---

## 一、终态结论（硬门槛裁决）

**APPROVED_WITH_NOTES —— unresolved_blockers=0**

- P0 = 0（无阻塞项）；P1 = 0；P2 × 1；P3 × 2（全部非阻塞，见发现表）。
- 硬门槛：P0 计数 0 ✅；5 维度 100% 覆盖 ✅；每条发现 100% 标注 P0~P3 ✅；AI 专项 5 项 100% 完成 ✅；设计一致性（与引擎层 L7345 语义、ADR-016 Phase 5 薄 CLI 适配层方向、FEAT-016 R0 F-1 遗留建议的修复方案）✅。
- 按 code-review SKILL 循环角色契约：本结论为通过终态，无未解决 BLOCKING finding，独立结构字段 `unresolved_blockers=0`。

---

## 二、修复正确性独立核实（正确性维度核心）

### 2.1 staged 产品代码（verify_workflow.py L20565-20575，staged 版）

```python
claim_gate = _loop_runtime_claim_gate_detail(claim_report)      # L20565
result["details"]["loop_runtime_claim_gate"] = claim_gate       # L20566
result["issues"].extend(claim_gate["issues"])                   # L20567（先合并）
# FIX-299 注释 7 行 L20568-20574
result["pass"] = not result["issues"]                           # L20575（后判定）
```

逐项核实：

1. **顺序正确**：claim issues 于 L20567 先 extend，`pass` 于 L20575 后从合并列表推导——"合并语义不变"声称属实（staged diff 原文核对）。
2. **与引擎层一致**：`check_release_readiness` 返回 `{"pass": not issues, "issues": issues, ...}`——**L7345 原文逐字核实**（任务锚点精确命中）：CLI 采用同一公式，顶层判定与引擎聚合语义对齐。
3. **exit/print 路径一致**（L20607-20611 staged 原文）：`if result["pass"]: print("Result: PASSED - ...")` / `else: print(f"Result: FAILED - {len(result['issues'])} issue(s)."); sys.exit(1)`——pass=True → 无 SystemExit → 进程 exit 0；pass=False → exit 1。打印与判定同源，无分叉路径。

### 2.2 开发者"L3140 ⇒ findings 非空"论证独立核实 ✅

锚点 `checks/loop_runtime_claims.py` **L3140 原文逐字命中**：

```python
report.verdict = "PASS" if not report.findings and report.parsed_candidates == inventory.candidate_count else "BLOCKED"
```

反证推演（verdict≠PASS ⇒ findings 非空）全路径覆盖：

- **正常终点**（L3140）：非 PASS ⇔ findings 非空 **或** parsed≠count；而 parsed≠count 必有 candidate 走了 `error` 分支（L3100-3102：error 追加进 findings 后 continue，parsed 不递增）——两分支均 ⇒ findings 非空。
- **早退路径**：L3034（SCAN_MODE_INVALID 先 append）；L3040-3041（`not policy or not authority` 早退——`_load_json` L1085-1098 核实：**所有**失败路径返回 `(None, [finding])`，且 schema 校验要求 dict + `schema_version=="1.0"` 排除空 dict falsy 值 ⇒ falsy 必伴随错误 finding，L3039 已 extend）；L3058（enumeration_errors 非空，L3056 已 extend）；L3111（SEMANTIC_BUDGET_EXCEEDED 先 append）。
- **结论**：不变量 `verdict≠PASS ⇒ findings 非空` 在该模块全部返回路径成立，"[FAIL] loop runtime claim gate 组件行 + PASSED topline"矛盾经 claim-gate 路径不可达。

### 2.3 其余 detail 组件的同型矛盾核查（CLI 顶层判定完全依赖引擎聚合后的新增审查面）

`result["pass"] = not result["issues"]` 使顶层判定依赖"每个 detail pass=False ⇒ 其 issues 非空且已并入顶层"。逐组件核实（check_release_readiness L7097-7342 staged）：

- 16 个内联组件（version/fact_source×2/hot_fact/runtime_matrix/first_session/pack_status/adapters/cross_refs/archive/release_docs/gate_sequence/one_dot_zero/execution_gates/dsh_regression/loop_fuse/changelog）：全部 `pass = not <组件 issues>` 且 issues 均 extend 进顶层 ✅；skip 路径（execution_gates 未开、dsh regression skip）issues 为空 + pass=True，无矛盾 ✅。
- **两个透传组件**深入核实：`projection_sync` → `checks/projection.py` **L73 原文** `{"pass": not issues, ...}` ✅；`release_lineage` → `checks/commit.py` + `release/model.py`（`CheckResult.passed = state=="PASS"`）+ `release/git_facts.py` 全部非 PASS 返回路径逐条带 ≥1 issue（L26/28/40-43/61/71/79/81/87/89/98-100），终点 L102-103 `"FAIL" if issues else "PASS"` 由 issues 推导 ✅。
- identity 路径：`_run_identity_attestation_fixture_only` L20497-20498——verdict≠PASS 必 append `IDENTITY_ATTESTATION_{verdict}` issue ✅。

**正确性维度结论：✅ 通过。** 修复语义正确、与引擎层一致、无组件行/topline 矛盾状态可达；FEAT-016 R0 F-1 遗留建议（"L20568 改为 not result['issues'] + 全绿回归测试"）被本修复逐字采纳。

---

## 三、5 维度 + AI 专项逐项结论

| 维度 | 结论 | 依据摘要 |
|---|---|---|
| 1 正确性 | ✅ 通过 | §2.1-2.3 全链核实：修复公式=引擎公式（L7345）；extend→derive 顺序正确；exit/print 同源（L20607-20611）；L3140 不变量+透传组件+identity 路径全覆盖，无矛盾态 |
| 2 安全性 | ✅ 通过 | 无输入处理/密钥/注入面变更；方向分析：修复仅使零 issue 态由假 FAIL 转正确 PASS——任一 issue 仍 exit 1，不引入假绿灯（fail-open）风险；quirk 期的 fail-closed 是以信号摧毁为代价的（狼来了效应），本修复恢复可判定性 |
| 3 可维护性 | ✅ 通过 | 7 行注释的每一项声称均经独立核实为真（引擎保证/合并顺序/历史 commit 4134026——与 AUDIT-150 §14 源码级证实互证）；修复采用与引擎相同的单一公式，消除 CLI/引擎双语义分叉 |
| 4 性能 | ✅ 通过 | `not result["issues"]` O(1)；无新增循环/IO；diff 净逻辑变更 1 行 |
| 5 测试覆盖 | ✅ 通过（附 F-1 P2） | 两态用例为真实行为断言非形式化：healthy 断言 exit None + `Result: PASSED` + NotIn FAILED（L7637-7639）；claim-issues 断言 exit 1 + 精确计数 `2 issue(s)` + `[FAIL] loop runtime claim gate` 组件行（L7654-7657）——与 L20610 打印格式逐字比对一致；FEAT-016 F-2 补 `FAILED - 1 issue(s)` 计数断言（L7507）实现归因强度；红→绿声称与 quirk 旧行为（恒 exit 1 → `AssertionError: 1 is not None`）逻辑自洽；811→813 恰 +2 与新增用例数一致 |

**AI 专项 5 项**：

| 项 | 结论 | 依据 |
|---|---|---|
| mock 残留 | ✅ 无 | 产品 diff 零 mock；测试 mock 为 CLI wiring 测试固有手段且全部经 ExitStack 作用域内进出，无跨测试泄漏 |
| 硬编码返回值 | ✅ 无（净移除 1 处） | 本修复**删除**了无条件硬编码 `False`，改为数据推导 |
| 幻觉 API | ✅ 无 | `result["issues"]`/`result["pass"]` 为引擎返回真实键（L7344-7348）；测试 patch 目标（vw.check_release_lineage / check_gate_sequence_for_release 等 17 个）全部为真实存在属性 |
| 未实现 TODO | ✅ 无 | diff 内无 TODO/FIXME/占位 |
| 过度实现 | ✅ 无 | 恰 2 文件 +133/−6 与 triage 声明面一致（git status 实证无第三文件）；无新 CLI 参数/子命令；测试数恰 2 新增 |

---

## 四、消费面实证（重点 2——最大回归风险面）

**结论：不存在依赖"恒 exit 1" quirk 的消费者；相反，多处机器可读契约要求本修复恢复的 exit 0 语义。** 全仓 grep（check-release/check_release，250+ 命中）分类证据：

| 消费面 | 实证 | 对本修复的依赖方向 |
|---|---|---|
| CI（.github/workflows/ci.yml） | 仅运行 verify / check-manifest-consistency / unittest discover / check-cross-references——**不调用 check-release** | 无关 |
| Git hooks（infra/hooks/） | grep 零命中 | 无关 |
| adapters/（dsh 适配层） | grep 零命中 | 无关 |
| release-ledger | `tests/test_release_ledger.py` L17 直接 import `check_release_lineage` **函数级 API**，不消费 CLI exit code | 无关 |
| 发布验收标准（AUDIT-136 R1/R2 acceptance 表） | "candidate `check-release`; **exit 0**"、"both **exit 0** in its phase"（audit-AUDIT-136-R1/R2.md 多行） | **要求 exit 0 语义——正向受益** |
| stage-release SKILL（L57/L155） | 候选态 candidate PASS → 发布后 released PASS 双段契约 | **要求 exit 0——正向受益** |
| 历史 release-checklist（0.39-0.55 等 20+ 文件） | "Release gate ✅ PASS"（quirk 前 0.44-0.55 实录）——quirk（4134026，2026-07-17 起）使 PASS 不可达 | **恢复被破坏的文档化契约** |
| 近期发布实践（0.74-0.78 CHANGELOG 门禁注记） | quirk 期以"exit 1 + issues 逐条分类"运作——分类的是 **issue 列表**而非"恒 1"本身；修复后任一 issue 仍 exit 1，既有分类纪律不受影响 | 兼容 |
| 既有测试（test_gate_sequence_for_release.py L494-537） | mock 了 `vw.sys.exit`，只断言 lineage kwargs，不依赖 exit 是否触发 | 无关 |

**回归面判定：无回归风险敞口；净效果为契约恢复。**

---

## 五、发现列表

| # | 级别 | 位置 | 事实 | 建议 | 处置 |
|---|---|---|---|---|---|
| F-1 | **P2** | test_verify_workflow.py L7479-7493（`test_FEAT_016_cli_shows_component_and_result_line_when_gates_enabled`）+ `_release_patches` L7184-7208/`_cli_patches` L7274-7294 | 修正后该测试断言 topline `Result: PASSED` + exit None，但其 patch 面未覆盖 `check_gate_sequence_for_release`（真调用：读宿主 plan-tracker Gate 表 + git tags，G-s1/G-s2 违反会产生 issue）与延迟导入的 `collect_loop_fuse_issues`（真读宿主 loop 状态）——topline 判定实际耦合宿主治理状态。**既有模式的延续**：引擎级姊妹测试（L7364-7385/L7417-7430 断言 `result["pass"]` True）携带同一未 patch 面并已经 FEAT-016 R0 审查通过；当前 813 passed 佐证现态无违反。风险=未来某 Gate 行转 pending + 存在已发布 tag、或 fuse 触发时该单元测试环境性假失败 | 在 `_release_patches` 增补 `check_gate_sequence_for_release` + `check_release_lineage` 两 patch（Fix299 `_patches` L7590-7599 已示范，一行级硬化） | 遗留候选（不阻塞；建议随下次触及该文件的任务顺带闭合） |
| F-2 | P3 | test_verify_workflow.py L7600-7601（Fix299 `_patches`） | `run_release_execution_gates` patch 在 `skip_execution_gates=True`（L7620）下不可达（引擎 L7239 `if run_execution_gates` 不触发）——防御性冗余 | 可保留（与 FEAT-016 `_cli_patches` 对称，防 fixture 演化）；或删一行 | 讨论级 |
| F-3 | P3 | test_verify_workflow.py L7562-7564（`_clean_claim_gate`） | fixture 的 `boundary: ""` 与真实 boundary 格式（`semantic_verdict=...; identity_verdict=...` L20521-20527）不同——boundary 仅打印不被断言/解析 | 可选：fixture 填真实形参提升保真度 | 讨论级 |

---

## 六、审查方法与事实依据红线声明

- 每条结论指向可复查事实：staged diff 原文（`git diff --cached`）、staged blob 行号（`git show :file` 带行号投影）、测试名与断言原文、全仓 grep 命中文件。行号均以 **staged 版本**为准（verify_workflow.py / test_verify_workflow.py / checks/loop_runtime_claims.py / checks/projection.py / checks/commit.py / release/model.py / release/git_facts.py）。
- 任务锚点核对：引擎"L7345"与 loop_runtime_claims"L3140"两个行号锚点**均逐字精确命中**（无漂移）。
- 未验证项显式声明：**测试未由本 Reviewer 运行**（只读约束）——全量 813 passed + 89 subtests、TDD 红→绿、healthy 面仓库级实录（`Result: PASSED` + EXIT=0）均采信 Developer 结构化返回（EVD-975）+ 测试代码内容审查交叉印证（断言与打印格式逐字一致、811→813 恰 +2、红因 `AssertionError: 1 is not None` 与 quirk 旧恒-exit-1 行为自洽）。
- 唯一产物 = 本报告（docs/reviews/）；未修改任何产品代码/治理记录；未与用户交互；review-record 持久化由 Coordinator 执行。

## 七、终态

**APPROVED_WITH_NOTES**

- unresolved_blockers = **0**
- P0=0 / P1=0 / P2=1（F-1，遗留候选）/ P3=2
- 复审链语义：本结论为通过终态（Check 30 可消费并结束复审链）；F-1 为非阻塞建议，不构成 NEEDS_CHANGE 事由。
