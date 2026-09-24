# review-FIX-387-CODE-R0 — 套件内全局态污染修复（代码审查 · R0）

> **Round 声明**：R0 首轮审查。审查对象 = 工作树未 commit diff（`git diff --numstat` 实测：**单文件 +116/−0**，`skills/software-project-governance/infra/tests/test_governance_store.py`，HEAD=17e5663）。审查方法：diff 逐行通读 + verify_workflow.py L234-276 重绑面逐行对照 + 全测试目录调用点普查 + 五组实测（R1 文件套件 / R2 FIX-377 决定性四组合 / R3 全套件 / R4 canary 负面对照 / R5 HEAD 存档树归因运行）。只读被审代码与 `.governance/`；唯一输出 = 本报告（负面对照用的泄漏模拟文件建于 `%TEMP%`、仓库外，用后已删除并留痕于 §1-R4）。

---

## 0. 总结论

**APPROVED**（`unresolved_blockers=0`）

| 级别 | 计数 |
|------|------|
| P0 阻塞 | **0** |
| P1 关键 | **0** |
| P2 建议 | **0** |
| P3 讨论 | **4**（F-1~F-4，全部为边界记录/流程注记，见 §5） |

机器可读行：`REVIEW-FIX-387-CODE-R0 | round=R0 | verdict=APPROVED | P0=0 | P1=0 | P2=0 | P3=4 | unresolved_blockers=0`

---

## 1. 审查方法与实测清单

| # | 实测 | 命令/方式 | 结果 |
|---|------|----------|------|
| R1 | 被审文件全套件 | `python -m pytest …/tests/test_governance_store.py -q -p no:cacheprovider` | **102 passed (3.94s)**——与申报「全套 101→102 passed（+1 canary）」一致 |
| R2 | FIX-377 决定性四节点组合（EVD-1144 机录 node ids 原样） | `pytest test_governance_store.py::EngineDispatchExitCodeTests::test_engine_main_returns_writer_refusal_code + test_verify_workflow.py::HotFactSourceConsistencyTests::test_fix339_rejects_unreleased_version_marked_published + test_quickscan_selector.py::Acceptance3DefaultPathTests::test_default_invocation_keeps_the_product_gate_active + test_verify_workflow.py::ExternalProjectValidationHarnessTests::test_hot_fact_skip_requires_external_validation_sentinel` | **4 passed (0.20s)**——与申报「四测试组合 3F+1P→4P（0.19s）」一致（0.20s 为机器计时方差） |
| R3 | 全套件（工作树） | `pytest skills/software-project-governance/infra/tests -q --tb=no -rf` | **12 failed / 3859 passed / 1 skipped / 515 subtests passed (913.06s)**——失败集 = ②8 + ④2 + 2 subtest，与修复后预期基线逐位吻合（§2.4） |
| R4 | canary 负面对照（模拟泄漏） | 仓库外 `%TEMP%\fix387_leak_sim\test_00_fix387_leak_sim.py`（字母序最前，run 阶段重绑 `HOST_PROJECT_ROOT`/`GOVERNANCE_DIR` + `REQUIRED_FILES` 加键，不恢复——复刻 L234-276 泄漏终态）+ 被审文件 + quickscan 下游节点同进程运行 | **canary FAILED（drift 报告精确点名 3 个漂移名→`.fix387-leak-sim-root`）+ quickscan 节点 FAILED（`False is not true` = 泄漏致 product gate 关闭）**，其余 102 passed——canary 判别力与 18 节点污染机制方向双双独立坐实；**模拟文件与目录已删除（`Test-Path` → False）** |
| R5 | HEAD 存档树归因运行 | `git archive HEAD` → `%TEMP%\fix387_head_tree`（纯 git 对象读出，零工作树改动；存档树无 `.git`/`.governance` 属环境降级，仅用于失败集存在性/根因佐证，不作 1:1 基线） | 12 节点同集全败 + 根因可见：R1 `main-file LOC 25534 > anchor 25462 (+72)`、R7 baseline-stale、static-pin `stale ledger row …:12375 (token 0.87.0)` / WARN `:12550`；HEAD 存档树全套件 71F/3807P——HotFact 16 节点 + quickscan + External sentinel（=18 污染受害者全家族）在 HEAD 侧全红 |

环境口径：`PYTHONDONTWRITEBYTECODE=1` + `-p no:cacheprovider`（全部运行零 `.pytest_cache`/`__pycache__` 写入）；R1/R2/R3/R5 相互独立进程。

---

## 2. MUST 重点审查七项逐项核验

### 2.1 快照/恢复实现的正确性 ✓

**（a）12 量清单与重绑面逐一对照——全等同序。** verify_workflow.py 全模块仅一处 `global` 声明（L234-237），实测 12 名：`HOST_PROJECT_ROOT, GOVERNANCE_DIR, EXECUTION_PACKET_PATH / SAMPLE_PATH, SESSION_SNAPSHOT_PATH, EVIDENCE_PATH, RISK_PATH / ARCHIVE_INDEX_PATH, ARCHIVE_TASKS_DIR, ARCHIVE_EVIDENCE_DIR / ARCHIVE_DECISIONS_DIR, ARCHIVE_RISKS_DIR`。`_VW_REBIND_GLOBALS`（test 文件 L1449-1454）**12 名逐一对应、顺序一致**——Developer「12 量（非 11）」修正属实。REQUIRED_FILES（L431 定义）经 L270-276 `.update()` 原地突变，由快照面第 13 键单独承载。

**（b）面完备性——被覆盖场景下 12+REQUIRED_FILES 即全部。** `_apply_project_root_override` 全模块唯一调用点 = `main()` L25406-25407（grep 实测 2 命中：定义 L221 + 调用 L25407），裸调用无 try/finally 无恢复——hunk1 注释「the CLI never restores them」属实。进程内引擎测试走 `locks-extend` 拒绝路径，不触及 L18193 的 `_load_archive_module()`（该调用属 check-governance 的 archive-trigger 检查路径）——archive 模块重绑面不在被覆盖路径上（见 §5 F-3 的边界记录）。grep 全测试目录普查：进程内触面的调用点仅 EngineDispatchExitCodeTests（本 diff 恢复）与 test_verify_workflow.py FIX-245 类（全无效 root + 自带恢复，§2.6-②）；其余 `--project-root` 命中全部为 subprocess（test_governance_store L833/841/925/1350、test_verify_workflow L18673、test_behavior_profile L528 等）或异构模块自身 parser（test_bootstrap_aggregate L805 = `ba.build_arg_parser()`）。

**（c）REQUIRED_FILES 原地重建引用语义——正确且防御性更优。** restore（L1478-1479）`clear()+update()` 保持 dict 对象同一性。grep 实测当前无任何 `from verify_workflow import REQUIRED_FILES` 形态的 by-reference 捕获者（infra 全域 25 命中均为模块属性访问或 verify_workflow 内部使用）——原地重建对现状是冗余安全，对未来捕获取向是正确选择（一致性 P4 防护网取向）。

**（d）_VW_MISSING sentinel 边界——对称闭环。** snapshot `getattr(vw, name, _VW_MISSING)` / restore 对 `_VW_MISSING` 执行 `vw.__dict__.pop(name, None)` / drift 用 `is` 同一性比较（L1487-1489）——「属性缺失」与「属性值为 None」不混淆，缺失↔缺失不误报。今日 12 名全部在导入期无条件定义（L164/167-168/7538-7539/9457-9463 实测），sentinel 路径为防御性死代码——无害且与 P4 取向一致（§5 注记）。

**（e）setUp/tearDown 语义——顺序正确。** 快照是 setUp 最后一条语句：setUp 前段（`_make_governance_dir`）失败时 unittest 跳过 tearDown，而彼时测试体未运行、无重绑发生——无泄漏窗口。tearDown 先恢复表面后清理 tmp（互不依赖，序无碍）。测试体中途断言失败时 unittest 必跑 tearDown——恢复不依赖测试成功。R4 附加实证：先于本文件发生的预泄漏态下，本类 setUp 快照捕获「当时态」、tearDown 原样恢复，类内测试不受扰、不误报——类级隔离（相对快照）+ 文件级 canary（对导入基线的绝对钉）双层设计自洽。

### 2.2 canary 判别力（负面对照复现）✓

R4 实录（§1）：模拟泄漏后 canary 立即 FAILED，drift 报告**精确点名且仅点名**被模拟突变的三项：`HOST_PROJECT_ROOT`（基线仓库根→`.fix387-leak-sim-root`）、`GOVERNANCE_DIR`（→`.fix387-leak-sim-root/.governance`）、`REQUIRED_FILES`（新增 `Fix387 Leak Sim` 键），其余 10 量零误报；消息含基线→现值 repr 与修复指引（指向 `EngineDispatchExitCodeTests.setUp / _vw_rebind_surface_restore`）。同进程下游 `test_default_invocation_keeps_the_product_gate_active` 同步转红（`_product_gate_active` 因 `_host_plugin_roots_divergent()` 为真返回 False）——FIX-377 记载的 18 节点污染机制（宿主/插件根分歧→product gate 关闭→下游节点翻转）被独立复现。判别力成立。

### 2.3 四测试组合转绿复现 ✓

R2：FIX-377 决定性四节点组合（污染者 + 三受害者，EVD-1144 机录 node ids）在修复后工作树 **4 passed (0.20s)**。前向 3F+1P 红态由 FIX-377 独立审查坐实（EVD-1144：「污染复现 0.21s（污染者+三受害者组合 3F+1P）」机录在案），本轮不再 stash 复演红态（避免工作树突变风险），以 R4 机制演示 + R5 HEAD 侧同族节点全红补足三角。

### 2.4 全套零回归 ✓

R3 工作树全套件 **12 failed（10 节点 + 2 subtest）/ 3859 passed**，与 EVD-1144（FIX-377 机录 HEAD 基线：28 节点 + 2 subtest 四类归类）**节点级对拍逐位吻合**：

| FIX-377 桶 | EVD-1144 记载 | 本轮实测（R3） | 判定 |
|-----------|--------------|----------------|------|
| ③ 测试基建缺陷→18 节点污染 | FIX-375 进程内 main() 重绑泄漏（16 HotFact + quickscan + External sentinel） | **0 命中**——HotFact/quickscan/External 全绿；R2 四组合 4P | **红→绿（修复目标桶）** |
| ② 环境语义 8 | 「LRC 触发文档轮换至 REL-086-R2 ragged row〔0233f49〕+ FIX-376 L29〔3d31c49〕+ R1 锚 +72 归因 FIX-373/374/375/376 合法交付」 | archguard R1/R7/CliGate（3）+ loop_runtime_claims inventory/performance（2）+ verify FIX300×2 + LoopRuntimeClaimAdapter（1）= **8**；R5 根因可见（ragged row findings 指向 review-REL-086-RELEASE-R2.md / review-FIX-376-CODE-R0.md；R1 `LOC 25534 > anchor 25462 (+72)`） | 既有基线，与本 diff 无因果 |
| ④ 账本过期 2 | 「static-pin 12375→12550 漂移 + L12674 未豁免」 | static_version_pins×2；R5 根因可见（`stale ledger row …:12375 (token 0.87.0)` / WARN `:12550`——与 EVD-1144 原文逐字对应） | 既有基线（FIX-388 承载） |
| +2 subtests | ②内 | FIX320ExemptionLedger SUBFAILED×2（mode=installed_host/product_release） | 既有基线 |

算术闭环：28F+2sub − 18 污染 = **10F+2sub = 实测 12 failed**（Coordinator 注「10F」为节点计数口径，与 FIX-377「28+2」同约定）。12 个失败节点全部位于 diff 未触碰文件、根因均为 0.88 窗合法交付/账本时点的函数（R5 佐证），**零新引入失败**。R5 caveat 如实声明：HEAD 存档树无 `.git`/`.governance`，其 71F 为环境降级形态，仅用于（i）12 节点失败存在性（ii）18 污染家族 HEAD 侧红态两个用途，不作 1:1 基线比较；同环境 HEAD 基线的权威记载 = EVD-1144（HEAD 17e5663 即 FIX-377 收口提交本身）。

### 2.5 选型理由核验（(b)/(c) 否决依据）✓

- **(b) subprocess 化否决——事实成立**：subprocess 兄弟用例实存——`test_engine_subprocess_refusal_exit2`（L1555-1564）与 `test_engine_subprocess_success_exit0_unchanged`（L1566-1575），转换即纯重复；且 in-process 钉持的是 `main()` **返回值契约**（`rc = vw.main(...)` 断言 `rc == 2`，L1546-1553）——engine dispatch 丢弃 writer 族 int 返回码的 FIX-375 假绿回归面（类 docstring L1508-1515 + EVD-1140「引擎分发返回码透传」）只有进程内可见，subprocess 只能钉真实进程退出码。
- **(c) patch no-op 否决——P7 论证成立**：main() L25406-25407 在 `explicit_project_root is not None` 时调用 override；patch 成 no-op 则重绑不发生，后续 handler 以导入期 `HOST_PROJECT_ROOT`（真实宿主仓库根）执行——本用例拒绝路径虽无写入，但引擎逻辑在真实 `.governance` 事实面上运行本身即 P7 缺陷敞口（任何后续成功路径断言变体将直接写真实治理面）。(a) 的 setUp/tearDown 恢复同时消解该敞口——修复本身就是 P7 防护的落点。

### 2.6 边缘披露三条核查 ✓

1. **「12 全局量（非 11）」**——属实（§2.1-a，L234-237 实测）。
2. **「FIX-245 类不构成第二污染源」**——属实：`TestVerifyCliProjectRootFailClosed`（test_verify_workflow.py L18930-19015）4 个进程内 `vw.main()` 用例的 root 全部无效（nonexistent/file/empty-string/prefix-form-nonexistent），fail-closed `sys.exit(2)` 发生在 L240-246、**先于 L247 首个重绑赋值**——「无效 root 在重绑前 exit」代码证据完整；该类另自带 3 名手工恢复（L18938-18945）双保险。
3. **「archive 重绑面仅 2 名且有 try/finally 恢复」**——属实：`archive._apply_project_root_override` 为**另一模块**的独立函数（archive.py L3234-3249，`global ROOT, HOST_PROJECT_ROOT` 恰 2 名），test_archive.py L3885-3906 try 前存快照、finally 恢复两名。

### 2.7 canary 覆盖边界披露的如实性 ✓

披露④如实：pytest 无配置文件随机化（pyproject.toml 仅 ruff/mypy，实测 0 命中 pytest 配置）→ 文件按字母序、类按定义序执行。`_VW_HOST_BASELINE` 在**收集期**（本文件导入时）捕获，早于一切测试运行——故字母序更早文件（含 test_fix270_product_gates.py 的 `mock.patch.object` 双钉、test_change_triage.py 的 GOVERNANCE_DIR patch 等——grep 普查全部带恢复）运行期泄漏可被捕获；字母序更晚文件（test_hooks/test_registry/…/test_verify_workflow.py 等）在本文件 canary 之后运行，**不可捕获**——与披露逐字一致。负面对照选用字母序最前位置实测检出，正落在可捕获半区。

---

## 3. 五维度结论

| 维度 | 结论 | 关键依据 |
|------|------|---------|
| 正确性 | ✓ 通过 | §2.1 全部子项；R1/R2/R4 实测 |
| 安全性 | ✓ 通过 | 测试仅写 TemporaryDirectory；canary 只读模块态；无注入/敏感数据/权限面；(c) 否决的 P7 论证成立（§2.5）；修复本身消除真实面触碰敞口 |
| 可维护性 | ✓ 通过 | 注释/docstring 与代码一致（L234-276 行号引用逐段实测准确）；三 helper 均 <20 行、各有唯一消费方；命名表意清晰（`_vw_rebind_surface_*` 族） |
| 性能 | ✓ 通过 | 快照/恢复 = 13 键 dict ×2/用例，可忽略；文件套件 3.94s（102 tests）；全套件 913s 与既有基线同量级 |
| 测试覆盖 | ✓ 通过 | +1 canary 防回归（负面对照实测检出）；类级恢复覆盖全类 3 用例（2 个 subprocess 用例的快照/恢复为无害冗余）；边界如实披露（§2.7 + §5 F-1/F-2） |

## 4. AI 代码专项 5 项检查

| # | 检查项 | 结论 |
|---|--------|------|
| 1 | mock 残留 | ✓ 无——diff 零 mock 引入 |
| 2 | 硬编码返回值 | ✓ 无——断言值（rc==2 / drifted=={}）均为契约钉而非捏造返回 |
| 3 | 幻觉 API 调用 | ✓ 无——`vw.main`（L24386）、`_apply_project_root_override`（L221）、`REQUIRED_FILES`（L431）及 unittest/dict API 全部实存 |
| 4 | 未实现 TODO | ✓ 无 |
| 5 | 过度实现 | ✓ 无——snapshot（setUp+baseline 两消费方）/restore（tearDown）/drift（canary）三 helper 职责单一无死代码；`_VW_MISSING` 为防御性对称（§2.1-d 注记，非过度实现） |

## 5. 发现清单

| 编号 | 级别 | 位置 | 描述与依据 |
|------|------|------|-----------|
| F-1 | P3 | test_governance_store.py L1498-1502 | **基线投毒理论边界**：canary 基线取「本文件导入时」表面态；若未来某字母序更早测试文件（或新增 conftest）在**模块导入期**（收集阶段）突变表面，基线将被投毒、canary 对该投毒失明。当前零实存（grep 普查：全部表面突变均在测试方法/setUp 作用域且带恢复；tests 目录无 conftest.py）。记录性边界，无动作需求 |
| F-2 | P3 | test_governance_store.py L1745-1775 | **字母序更晚文件不可捕获**（§2.7）——Developer 已如实披露；扩面与否属 Coordinator 决策（可选项：test_verify_workflow.py 尾部镜像 canary / conftest 级 teardown 钉）。不阻塞本票 |
| F-3 | P3 | verify_workflow.py L9466/L18193；test_verify_workflow.py L19034-19043 | **archive 模块重绑面在 canary 保护域之外**（既有行为，非本 diff 引入）：`_load_archive_module` 依据当时 `vw.HOST_PROJECT_ROOT` 再绑定 archive.ROOT/HOST_PROJECT_ROOT；`TestLoadArchiveModuleRebind` 的 tearDown 只恢复 `vw.HOST_PROJECT_ROOT`（L19030-19031），archive 模块两名滞留测试 tmp 根直至下一次 `_load_archive_module` 调用刷新。当前无害（archive 消费者均经 `_load_archive_module` 再解析或测试自带 try/finally），记录为未来加固候选 |
| F-4 | P3 | `.governance/execution-packets.json` | **流程注记（非代码）**：grep 实测无 FIX-387 条目——活跃 P1 的执行包 Check 18c 义务属 Coordinator 侧，随本报告一并提请注意 |

## 6. 硬门槛裁决

| 门槛项 | 裁决 |
|--------|------|
| P0 阻塞问题数 = 0 | ✓（P0=0；P1=0 无遗留处理义务） |
| 5 维度全覆盖 = 100% | ✓（§3 逐维有结论） |
| 每条发现标注级别 = 100% | ✓（§5 四条全带 P 标签） |
| 设计一致性检查 | ✓——选型 (a) 与 FIX-377/EVD-1144 归类、FIX-375 返回码契约（EVD-1140）、FIX-245 fail-closed 先例（L200-246）全部对齐；hunk 注释引用的调查结论与 EVD-1144 机录一致 |
| AI 代码专项 5 项 | ✓（§4 逐项） |

## 7. 交付机录义务（非阻塞——随 commit 承载，Coordinator 执行）

1. commit message/EVD 按本轮实测口径机录：单文件 +116/−0；文件套件 102 passed；四组合 4 passed；全套件 12 failed = ②8+④2+2sub（与 EVD-1144 预期修复后基线逐位吻合、零新引入）；canary 负面对照检出实录。
2. §5 F-2（canary 扩面决策）与 F-4（执行包补写）转 Coordinator 处置，不阻塞 APPROVED 终态。

---

*审查方法学披露：全部 pytest 运行只读仓库（`PYTHONDONTWRITEBYTECODE=1` + `-p no:cacheprovider`）；唯一写操作 = 本报告文件 + `%TEMP%` 内已删除的泄漏模拟文件（R4）+ `%TEMP%` 内 HEAD 存档树（R5）；被审代码零修改；未使用 git stash（红态复演以 R4 机制演示 + R5 + EVD-1144 机录三角替代，规避工作树突变风险）。*
