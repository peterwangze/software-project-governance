# REVIEW-FEAT-055-CODE-R0 — 批 2.0 集成窗独立代码审查（round 0）

- **任务**: FEAT-055（0.86.0 批 2.0 集成窗——三写入器引擎接线 + 留置收口 + 冻结面 re-baseline）
- **Round**: **R0**（首轮独立审查；无前轮）
- **审查对象**: 工作树未提交 13 文件（对 HEAD=`c2cc7c1`）：`verify_workflow.py` / `registry.py` / 三写入器（`task_row_update.py` / `governance_store.py` / `baseline_metadata.py`）/ 五测试文件（`test_governance_store.py` / `test_task_row_update.py` / `test_baseline_metadata.py` / `test_registry.py` / `test_contract_matrix.py`）/ `checks/version.py` / `contract_matrix/snapshots.json` / `core/architecture-baseline.json`。合计 +1021/−256。
- **语义基准**: version-plan-0.86.0 §2 批 2.0（M0 复跑=兼容性回归）· arch round3 P1-1（批 0→批 1→批 2.0 依赖图）· FEAT-020 冻结面文档化变更程序（--regen 同变更 + 计数 bump + 溯源注释）· FEAT-046/047/051 各自 R0/R1 留置清单 · governance_cost/bootstrap_aggregate 接线先例
- **范围纪律**: 只读审查 + 本报告写入 `docs/reviews/`；`.governance/` 净变更=0（git status 证实）；未修改任何产品代码。

---

## 总结论

## **APPROVED_WITH_NOTES** — P0=0 · P1=0 · P2=0 · P3=4 新增 · **unresolved_blockers=0**

Developer 申报八面（7 键冒烟/88→95 双钉/R6 +6/archguard regen/留置收口/M0 复跑/六套件 462/存量 5 失败归因）经本审查独立复验**全部属实**，其中一项 prose 披露（R6 三叶归属）与机器事实不符降为 P3 勘误项。接线 mechanics 经 AST 级机证与选项集机证确认零执行体语义漂移（唯一例外=已申报、已负控的 P3-4 收紧）。无阻塞项；4 项 P3 均不阻断 commit。

---

## 一、审查重点 ①~⑧ 逐项裁决

| # | 重点 | 裁决 | 依据（本审查独立证据） |
|---|------|------|----------------------|
| ① | **接线正确性** | ✅ 通过 | **选项集机证**：7 命令引擎 subparser options 段与模块 parser options 段逐一恒等（V4）。**单事实源**：`add_arguments`/`add_*_arguments` 为同一函数对象被 `build_parser` 与引擎 subparser 共用——漂移在构造上不可能；baseline_metadata 另有显式机证测试（`test_add_arguments_is_the_single_option_fact_source`，dest→(required, option_strings) 全等）+ 结构钉（`_namespace_to_argv`/`_register_option_map`/`_evaluate_option_map` 消失断言）。**引擎 Namespace 直达**：7 个 `cmd_*` 直消费 Namespace，无 argv 往返；`task_row_update` 走 `_execute(args, parser)`，`parser.error` 保持 argparse exit-2 + usage 契约双路一致（专用测试钉住）。**执行体零改动**：AST 逐函数 HEAD vs 工作树（docstring 剥离）——task_row_update 7/7、governance_store 17/17、baseline_metadata 5/5 核心执行函数 IDENTICAL（V5）。引擎全局参数仅 `--project-root`（default=None），与 7 子命令选项集零 dest 碰撞；`_governance_dir_from` 的 `getattr(...) or "."` 语义：引擎态吃引擎解析的 project_root、自 host 态默认 cwd——与旧 `Path(args.project_root)`（自 host 默认 "."）行为保真 |
| ② | **冻结面 re-baseline 程序合规** | ✅ 通过 | 88→95 走 FEAT-020 文档化路径：`generator --regen` 同变更 + `FROZEN_CLI_KEY_COUNT=95`（test_contract_matrix）+ `FROZEN_CLI_KEYS=95`（test_registry）+ snapshots `key_count 88→95`/`handler_count 85→92` —— **三重钉**（超出"双钉"申报）；R5 实测 live 95/95、segments 71/71（V6）；`generator --check` 4 faces zero drift（V7）；snapshots `git_head` df9e7db→c2cc7c1 + timestamp 更新同窗。**数字勘误成立**：任务书 87→94 过时，实测 pre-state=88（snapshots diff 旧值 88 为准）。**FEAT-039 docstring 漂移披露忠实**：registry.py `_COMMANDS` docstring 明写"shipped stale at FEAT-039 time (said 87 with 8 outside when the table held 88 with 9 outside); corrected here as part of the deliberate re-baseline"——95=16 outside+79 engine 算术自洽，与 handler_count 85→92（+7）一致 |
| ③ | **R6 +6 披露** | ⚠️ 通过（附 P3 勘误） | 数量/SHA/pin 机器面全部正确：199→205（V8 机证，removed=[]），import_set_sha256 双更新，R6 实跑 205 Δ0，`FROZEN_ENGINE_IMPORT_COUNT=205`。contracts 入引擎冷导入面**合法**：三 writer import 处注释一致声明 "L0 — consumed read-only, never redefined / frozen at revision m0-r1"；test_registry 负控反转（assertNotIn→assertIn contracts）有披露、负控收窄到 registry/quickscan_registry——语义合理。**但 prose 归属失准 → F-1（P3）**：申报"三叶 contracts/uuid/threading"中 `threading` 并非新增叶（V8 机器事实：`threading ∈ work face ∧ threading ∉ (work−head) ⇒ threading ∈ HEAD face`——引擎既有链已携带）；第 6 槽实为 `_uuid`（uuid 的 C 加速器伴生模块，未列入披露）。test_registry.py 注释同款失准 |
| ④ | **archguard regen 纪律** | ✅ 通过 | R1 新基线 24852 **only-down 语义保持**（实跑 `24852 ≤ anchor 24852`）；24769+83=24852 与 verify_workflow.py diff（+83/−0）及实测文件行数 24,852 三方吻合；regen 后 R1~R7 全 PASS（V6）；R4 print 1304≤1304 证实引擎接线零 print 增量（diff 注释"R4 print budget untouched"为真）；R7 `deterministic=True; committed==fresh True` |
| ⑤ | **留置八项逐项质量** | ✅ 通过 | 见 §二逐项核验表——负控为真实红相（mtime 操纵/GBK 字节/os.replace 崩溃注入/受控交织），非形式断言；披露与代码逐字对齐（P3-3 经 AST 证实为纯 docstring 变更、函数体零改动） |
| ⑥ | **version.py 豁免 re-anchor** | ✅ 通过 | 六锚 60→63/315→318/392→395/563→566/620→623/738→741 全部 +3 平移且逐行 PIN-OK（V9）；账本注释自载程序与 diff 事实一致——"three import lines"实数（test_baseline_metadata.py 新增 `argparse`/`os`/`mock` 3 行 import）+ "guard-test additions"（新测试类均落文件尾部，不影响前部锚位）；"same six instrument-version fixture rows"属实（行内容零变化仅位移）；`check-version-consistency` PASSED（stale-exemption 审计在位）。锁外连带性质（version.py 非批 1 冻结文件面）已在注释中披露，合规 |
| ⑦ | **存量 5 失败归因** | ✅ 归因成立，另票合理 | 全仓 tests 目录实跑 3775 项：**5 failed / 3769 passed / 1 skipped**（V10）。5 失败全部为 LRC/identity 族（test_loop_runtime_claims ×2 + test_verify_workflow ×3），失败报文**自证根因**：`ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY: ragged table row @ docs/reviews/review-FEAT-054-RELEASE-R0.md` → 门 BLOCKED 而非 PASS。该文件由 602a794（REL-081 M-1R）引入、**不在本批 13 文件 diff 面**（tracked 未改）⇒ HEAD 必现，stash 对照归因逻辑闭环（本审以 diff-范围逻辑佐证，未执行 stash 写操作）。另票建议合理：修复面=docs 卫生（修 ragged row）或 scanner 侧列数容错，均出本票范围；与 FIX-320/DEC-199 处置谱系同族 |
| ⑧ | **AI 专项 5 项** | ✅ 全过 | ① mock 残留：产品三文件零 mock（grep 机判）；测试内 mock.patch 均为故障注入合法用途 ② 硬编码返回值：无——writers 全为真实计算路径；测试 `INSTRUMENT_VERSION` 自 fixture 派生刻意规避版本字面量（注释明示 static-pin 卫生）③ 幻觉 API：零——`Path.is_relative_to`（py3.9+，运行环境 3.14）/`os.utime`/argparse 内省（仅测试侧）均真实存在且用法正确 ④ 未实现 TODO：零（TODO/FIXME/placeholder grep 机判 4 文件无命中）⑤ 过度实现：无——接线不加投机面；TOCTOU 测试钉住已文档化约束而**不**抢实现锁面（锁面归属未来切片，与 docstring 契约一致），实现克制正确 |

---

## 二、留置八项收口逐项核验（对应 FEAT-046/047 R0/R1 留置清单）

| # | 留置项（出处） | 落点 | 核验结论 |
|---|--------------|------|---------|
| 1 | FEAT-046 P3-2 负控×3 + 接管语义披露 | `StaleLockTakeoverTests`（stale 接管正相/全新锁不判 stale/近期锁 lock_contention 不静默吊销）+ 模块 docstring + `_TargetLock` docstring（接管按 PATH 非所有权、慢持有者 `_acquired=True` 残留会 unlink 后继活跃锁的暂态互斥侵蚀边界、无 check 覆盖 + BT-4 登记引用） | ✅ 三负/正控齐备且披露与实现逐字一致；`_stale()` 函数体 AST IDENTICAL（纯披露+负控，零行为变更） |
| 2 | FEAT-046 P3-3 governance_id mention 级披露 | `_validate_governance_id` docstring（`\b` 子串非行锚/mention 即 resolvable/验证≠充分性/拒绝收紧的正当理由——会改变既有合法引用的 resolvable 面） | ✅ AST 证实纯 docstring；模块 docstring 同步双披露 |
| 3 | FEAT-046 P3-4 根内收紧 ×4 负例 | `_validate_ref` repo_file 分支：`resolve()` + `is_relative_to(repo_root)` 容含检查，逃逸 → `("unresolvable", "path escapes the repo root")` → 调用方 cross_record_violation 拒绝；`RepoFileRootContainmentTests` ×4（`../` 逃逸/仓外绝对路径/根内存活路径行为不变/根内缺失朴素 unresolvable） | ✅ **全批唯一执行体语义变更**，方向安全（只读检查收紧，无新写入面）；负例覆盖正反两侧 + 错误文案断言。**本审查将"执行体零改动"申报精确化为：接线 mechanics 零改动；P3-4 为单独申报、单独负控的已授权收紧**——两者在 diff hunk 清单中可完全区分（V5） |
| 4 | FEAT-047 P3-5 DispatchFaceTests ×4 | `test_baseline_metadata.DispatchFaceTests`：register handler 消费引擎 Namespace / evaluate handler 同 / `add_*_arguments` 单事实源机证（dest→(required, option_strings) 全等）/ argv 路由消除结构钉 | ✅ ×4 齐备；单事实源测试比较 canonical subparser vs face parser，机器级防漂移 |
| 5 | FEAT-047 P2-2(b)(c)(d) | `RegistryNegativeControlTests`：(b) key≠row gate_id 篡改 → load 拒绝"keys and rows must agree"/(c) GBK 字节流 → "not valid UTF-8"/(d) `os.replace` 中途崩溃 → 旧文件字节不变 + 零 `.baselines-` temp 残留 | ✅ 三子项齐备；(d) 用真实异常注入而非模拟断言 |
| 6 | FEAT-047 P2-2(a) TOCTOU 钉 + 单写者 docstring | `register()` docstring（UNLOCKED load→mutate→os.replace 全文件写/双 register lost-update 与同门异载荷竞态边界/锁面归属 FEAT-046 管道/落锁 MUST 翻测试）+ `ConcurrentRegisterWindowTests`（受控交织复现 lost-update 窗，零线程调度假设） | ✅ 测试与 docstring 互为契约——窗口被钉住而非掩盖，翻转义务明文 |
| 7 | FEAT-046 test_resume 断言强度（双腿精确钉） | apply 腿 `assertEqual("apply")`（注释载明收紧理由：world==baseline → 恰一次重施，混入 "resume" 会掩盖 apply 腿回归）+ 新增 `test_resume_completes_without_reapplying_when_target_reached`（world==pending_effects → "resume" + TTL 4200 不重施 +600） | ✅ 双腿各自精确、互斥可判 |
| 8 | 接线守护测试族（P2-1 口径随票守护） | governance_store `WriterCliHandlerTests` ×3（Namespace exit 0/结构化拒绝 exit 2 schema_violation/project_root 缺省 cwd 语义钉）+ task_row_update `EngineDispatchFaceTests` ×2（Namespace 翻转正相/缺三元 usage 拒绝 exit 2 与自 host CLI 同型） | ✅ 三模块接线面均有 happy path + 拒绝路径 + 缺省语义守护 |

---

## 三、独立复验表（本审查实跑，全部可复查）

| # | 复验项 | 方法 | 结果 |
|---|--------|------|------|
| V1 | 六套件 462 全绿 | pytest 实跑六套件 | **157 / 87 / 42 / 72(+49 subtests) / 77 / 27 = 462 passed**，与申报逐一吻合（contracts ×2 = "M0 复跑 157×2"）；测试增量 +21（11+2+8）与 diff 面相称，无夹带 |
| V2 | M0 pin 锚 | `pytest test_contracts.py -k "pin or revision or anchor"` | **10 passed**（×2 次全量跑内含）——"pin 三锚 MATCH"证实 |
| V3 | 7 键 --help 冒烟 | 引擎 vs 模块双面实跑 | **7/7 rc=0** PASS（申报为抽样 2，本审全额 7 执行） |
| V4 | 选项集逐一相等机证 | 引擎 subparser options 段 vs 模块 parser options 段（同解释器实跑解析） | **7/7 恒等**（首轮探针两处自身缺陷——正则吃 prose、GBK 解码——修正后重跑；非产品缺陷） |
| V5 | 三写入器执行体零改动 | AST 逐函数 HEAD(`git show`) vs 工作树，docstring 剥离比对 | 29/29 核心执行函数 IDENTICAL；CHANGED=`_validate_ref`（P3-4 唯一语义变更，已申报）+ build_parser/main/cmd_*（接线）；ADDED=add_*/cmd_*/run_*/_run_error/_build_parser/_execute/_configure_stdio/_governance_dir_from；REMOVED=`_namespace_to_argv`+`_register_option_map`+`_evaluate_option_map`+`_add_*_options`（P2-1 兑现机可见） |
| V6 | archguard R1~R7 | `verify_workflow.py archguard-ratchet` 实跑 | **全 PASS**：R1 24852≤24852 (only-down) / R2 47≤47 / R3 12 edges / R4 1304≤1304 / **R5 cli 95/95 + segments 71/71** / **R6 205 Δ0** / R7 deterministic=True; committed==fresh True → exit 0 |
| V7 | 契约快照零漂移 | `contract_matrix/generator.py --check` | **4 faces zero drift** |
| V8 | R6 +6 精确身份 | `git archive HEAD` → 隔离临时目录，同口径（`-I -B` 子进程 sorted(sys.modules)）双面对比 | HEAD=199 / WORK=205；**added = {task_row_update, governance_store, baseline_metadata, contracts, uuid, _uuid}**；removed=[]；threading ∈ 双面（HEAD 已含）→ **F-1** |
| V9 | version.py 六锚 + 一致性 | 逐行读 63/318/395/566/623/741 + `check-version-consistency` 实跑 | 六锚全 **PIN-OK**（0.85.0 instrument-version 行）；check **PASSED** |
| V10 | 存量 5 失败定位 | 全仓 tests 目录实跑（后台 14m06s） | **5 failed / 3769 passed / 1 skipped**；失败报文自证 ragged row @ review-FEAT-054-RELEASE-R0.md；该文件不在本批 diff 面 ⇒ stash 归因逻辑闭环 |

**申报采信面（未独立复跑）**：M0 量测协议工件三路径（协议面未在本批触碰）；"stash 对照"的物理执行（以 V10 diff-范围逻辑替代佐证）。

---

## 四、Findings（P0=0 / P1=0 / P2=0 / P3=4）

| ID | 级别 | 位置 | 描述 | 建议 |
|----|------|------|------|------|
| **F-1** | **P3** | `infra/tests/test_registry.py` `FROZEN_ENGINE_IMPORT_COUNT` 注释（"plus exactly the three leaves ... ``uuid`` ... and ``threading``"）+ 同源申报 prose | **R6 +6 三叶归属失准**：机器事实（V8）`threading` 在 HEAD 冷导入面已存在（引擎既有 import 链携带），governance_store 的 `import threading` 消费的是已在场模块；实际第 6 个新增模块是 `_uuid`（`uuid` 的 C 加速器伴生，随 `import uuid` 自动入场，披露未列）。数量 +6、SHA、`FROZEN_ENGINE_IMPORT_COUNT=205`、R6 基线全部机器正确——**仅注释/申报 prose 的叶清单错一格**。"如实披露"纪律下该偏差应勘误，防止未来 regen 时按错误叶清单预测 import 面 | 注释勘误（把 threading 从"新增叶"改为"既有在场"、补 `_uuid` 伴生说明）；随本批 commit 顺手或入批 2.1 顺手项 |
| **F-2** | **P3** | 流程面（非代码）：review-FEAT-047-CODE-R1 §处置表 "P3-3（契约注释固化）→ 批 2.0（contracts 消费面）" | **FEAT-047 P3-3（pass+block 语义在契约面固化）批 2.0 承接未兑现且未披露处置**。本批未触碰 contracts.py（正确的范围决定——契约变更需走变更流程），但该 P3 留置的"批 2.0"归属既未兑现也不在本批收口清单中，属静默丢弃风险（FEAT-051 R1 notes "勿静默丢失"纪律同族） | 显式登记去向：改挂"下次触达 contracts.py 的契约变更票"或显式降级候选池，一行处置记录即可 |
| **F-3** | **P3** | `verify_workflow.py` 接线 + `task_row_update.py`（`--file` 默认 `.governance/plan-tracker.md`）/ `baseline_metadata.py`（`--registry` 默认 `.governance/baselines.json`，L153） | **引擎全局 `--project-root` 仅 governance_store 族消费**（`_governance_dir_from`），task_row_update/baseline_metadata 的相对缺省恒按进程 cwd 解析、忽略引擎 project_root——新统一派发面上的跨族语义不对称。与批 1 意图行为 parity（旧 option map 从不含 project_root，非本批回归）；受管流程固定 repo 根运行，实际风险低 | 登记候选池：后续切片统一"引擎 project_root → writer 缺省解析"或在两模块 docstring 披露 cwd 语义 |
| **F-4** | **P3** | `test_governance_store.py::RepoFileRootContainmentTests::test_root_internal_path_still_resolvable` L~1160 | **死调用残留**：文件创建前先调用一次 `_validate_ref` 且结果即被第二个同名调用覆盖（红相期遗留），纯测试卫生瑕疵，不影响断言强度 | 顺手删首个死调用 |

**边缘问题移交（非 findings）**：① FEAT-051 R1 留置（P3②⑥⑦ + P3-5 余 3 子项——`_dry_run` 死参数/replay prose 前缀耦合/`expected_revision=1` 占位）申报口径为"批 2.x 触达时顺手项"，本批未触达 `_dry_run` 执行体、未收口亦未宣称收口——**维持登记，无静默丢失**；② FEAT-046 P3-9（引擎列位错位）独立票入账义务在 plan-tracker FEAT-046 行已记录，本批范围外合规；③ FEAT-055 任务行尚未见于 plan-tracker（grep 零命中）——任务入账/change-triage 机录属 Coordinator 收尾义务，非 Developer 范围，提示勿漏。

---

## 五、五维度 + 硬门槛裁决

| 维度 | 结论 |
|------|------|
| 正确性 | ✅ 接线语义保真（AST/选项集/Namespace 缺省语义三重机证）；P3-4 唯一语义变更方向安全且负例齐备；`parser.error` exit-2 契约双路一致有测试 |
| 安全性 | ✅ P3-4 堵住 repo_file 引用逃逸（绝对路径/`..` 前缀）——只读验证面收紧，无新写入面；注入预算六面清单（INJECTION_BUDGET_SURFACES）零触碰（SKILL/persona/entry/agent-instructions 零改动）；无硬编码密钥 |
| 可维护性 | ✅ 双事实源消除（option maps 删除有结构钉）；全部接线点带溯源注释（FEAT-047 P2-1 caliber 引用一致）；registry docstring 历史漂移显式纠正而非静默吸收；F-1/F-4 为微瑕 |
| 性能 | ✅ R6 冷导入 205 Δ0（wall ~149ms，advisory）；R4 print 1304 零涨；六套件时长无异常（test_contract_matrix 60s 为既有 golden 面） |
| 测试覆盖 | ✅ +21 新测试全绿，三型齐备（正相/负相红相/结构钉）；462 总量与申报吻合；核心路径（Namespace 直达/usage 拒绝/P3-4 双侧/TOCTOU 窗）全部有对应测试 |

| 硬门槛 | 裁决 |
|--------|------|
| P0 = 0 | ✅ |
| 5 维度全覆盖 | ✅ |
| 每条发现标注级别 | ✅（F-1~F-4 全 P3） |
| 设计一致性 | ✅（version-plan §2 批 2.0 = M0 复跑+跨票集成验收，本切片正命中；arch P1-1 批次依赖图合规；FEAT-020 文档化变更程序履行；三票留置清单逐项对账） |
| AI 专项 5 项 | ✅（§一⑧） |

---

## 六、复审裁定

**APPROVED_WITH_NOTES — unresolved_blockers=0**（P0=0/P1=0/P2=0/P3=4）。可进入 commit/收尾流程；F-1~F-4 与移交事项按 §四 登记去向。硬门槛全过，无未解决阻塞。

*Reviewer: 独立 Code Reviewer（FEAT-055-CODE-R0）。只读审查；复验命令均只读（V8 的 HEAD 树展开于系统临时目录并已清理）；本报告为 R0 唯一事实源；`.governance/` 净变更=0。*
