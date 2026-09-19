# REVIEW-FEAT-046-CODE-R1 — 复审（governance_store 写入器族，批 1 票 2）

- **Round**: **R1**（同 Reviewer 复审；前轮引用：`docs/reviews/review-FEAT-046-CODE-R0.md`——NEEDS_CHANGE，P0=1/P1=0/P2=4/P3=10，unresolved_blockers=1）
- **复审性质**: M7.4 step 4.6——验证修复，非重新开题。前轮 findings 逐条比对「已修复/未修复/新引入」；所有结论锚定本审查独立实跑与逐行读码。
- **复审对象**: `skills/software-project-governance/infra/governance_store.py`（修订后 1,882 行）+ `infra/tests/test_governance_store.py`（修订后 1,081 行 / 76 测试）。
- **范围纪律**: 与 R0 同口径——并行票与 FEAT-053 bump 在途文件出范围；verify 全量 WARN 归因按此区分。

---

## 总结论

## **APPROVED_WITH_NOTES** — P0=0 · P1=0 · P2=0 · P3=0 新增 · **unresolved_blockers=0**

R0 全部阻塞与建议项（P0-1 + P2×4）已修复且经独立复验；P3 便宜四项（P3-1/7/8/10）已顺手关闭；留置 P3 项（P3-2/3/4/5/9 + test_resume 断言强度）逐项裁定均有归属且不构成本票阻塞。复审未发现新引入问题。附非阻塞备注（见「留置裁定与后续归属」）。

---

## 前轮 findings 逐条比对（M7.4 step 4.6）

| R0 finding | 处置申报 | 复审判定 | 独立验证证据 |
|-----------|---------|---------|-------------|
| **P0-1** locks conflict 腿未捕获 ContractViolation | 补 `observed_revision=len(_read_bytes(path))` + 红相负控 ×2 + CLI exit 2 | **已修复** | 代码 L1434-1439（与 append 族同口径，`path` 于 L1430 加载）；`test_same_op_different_payload_conflicts_structured`（L753，extend）+ 同名 amend 版（L887）断言结构化 code + observed_revision 非空 + execution None + **世界字节不变**；`test_..._cli_exit2`（L769）两连跑第二次 exit 2 + JSON 载荷 + **stderr 无 "ContractViolation" 断言**。**R0 崩溃复现脚本原样重跑**：现返回 `{"code":"operation_id_conflict","observed_revision":435,"disposition":"conflict","execution":null,"new_revision":null,"error":true}`——face-5 不变量逐字段恢复 |
| **P2-1** dry-run 缺 ID 碰撞校验 | dry-run 改走 `_next_row_id` + 碰撞 dry-run 测试 + `_peek_next_id` 删除 | **已修复** | `_dry_run_append` docstring 明示 P2-1（L752-758）；`evidence_append.build` L1022 与 decision 对称位均改 `_next_row_id`（与实写 L1082 同源同函数）；`_peek_next_id` 全文件零残留（grep）；`next_id` 改从渲染行 `_split_row(row_text)[0]` 提取（L767）；`test_dry_run_executes_id_collision_check`（L793）：archive 碰撞 fixture → `cross_record_violation` + 字节不变，单跑通过 |
| **P2-2** 账本缺指纹形校验可致 locks 双施 | `_load_ledger` 补 `require_input_fingerprint` + 测试 | **已修复** | L550-563：每条目指纹形校验，`ContractViolation`→`manual_intervention` fail-closed，注释准确引用双重施加根因；`require_input_fingerprint` 已入 import 块（L133，face 1 单一来源非第二实现）；`test_ledger_entry_without_fingerprint_refused`（L803）：种子无指纹 ok 条目 → manual_intervention + 世界不变 |
| **P2-3** `--files` help 与逗号切分不符 | 双分隔符兑现 + `--refs` 独立 `;` 切分器 + 测试 | **已修复** | `_split_cli_list`（L1723-1729）：`;`→`,` 归一后按 `,` 切（注释引 change_triage `_split` 同约定）；`_split_refs_list`（L1732-1736）**仅**按 `;` 切——URL 逗号保真；`main` L1843/L1863 分别接线；`test_split_cli_list_accepts_both_separators`（L828）覆盖混合分隔符 + `url:https://x.io/a,b` 保真 |
| **P2-4** 空目标 CAS 拒绝不可构造（observed_revision=0） | 锁内入口空文件 schema_violation（CAS 前）+ 测试 | **已修复** | evidence L1037-1047 / decision L1214 对称：空文件在 CAS 检查**之前**拒绝（schema_violation，注释明确 observed 0 不可构造）；`test_empty_target_refused_at_entry_even_with_cas`（L839）双族覆盖（expected_revision=5 + 空文件 → schema_violation + 字节不变）。顺带消灭 P3-6 前导空行场景（空文件已不可达 `_append_row_bytes`）——**P3-6 关闭** |
| P3-1 locks 未调 SCHEMA_WINDOW | 补入 | **已修复** | L1553（locks_extend）/ L1623（locks_amend）+ 既有 append 两处——四命令一致 |
| P3-7 无目录 fsync | 补 | **已修复** | `_fsync_dir`（L368-381）：best-effort，Windows 目录 `os.open` 失败即 return（平台差异处理正确）；`_atomic_write_bytes` L395 在 replace 后调用 |
| P3-8 「DoD nine items」措辞 | 改 | **已修复** | L47 现为「DoD ten items (…§4, items 0–9)」 |
| P3-10 exit 3 无 CLI 级测试 | 补 | **已修复** | `test_cli_lock_contention_exits_3`（L857）：持锁 + `--timeout 0.2` → exit 3 + `lock_contention`/`retryable` 断言 |
| P3-2/3/4/5/9 + test_resume 断言强度 | 留置请求 | **留置裁定通过**（见下节） | 均不构成本票阻塞；归属明确 |

**新引入检查**：修订区域（imports/`_load_ledger`/`_dry_run_append`/append/decision 空文件腿/locks conflict 腿/SCHEMA_WINDOW/`_fsync_dir`/CLI 切分器/docstring）逐行读毕——未发现新缺陷。行数 1,812→1,882（+70）与 68→76 测试增量相称，无夹带。

---

## R1 独立复验表

| # | 复验项 | 命令/方法 | 结果 |
|---|--------|----------|------|
| V1 | 76 套件实跑 | `pytest test_governance_store.py -q`（后台独立跑） | **76 passed in 2.03s** |
| V2 | **P0 红相场景复演**（R0 崩溃脚本原样重跑，隔离临时目录） | 种子账本同 ID 异指纹 → `locks_extend` 重试 | **结构化拒绝**：`operation_id_conflict` + `observed_revision=435` + `disposition=conflict` + `execution=null` + `new_revision=null`——R0 的 `UNCAUGHT ContractViolation` 消失 |
| V3 | dry-run 碰撞测试单跑 | `pytest -k dry_run_executes_id_collision` | **1 passed** |
| V4 | 三套回归 | contracts / injection / registry 三套件实跑 | **157 passed / 11 passed (+3 subtests) / 77 passed**——与申报数字逐一吻合 |
| V5 | verify 全量 | `verify_workflow.py` 全量（本审查后台实跑） | 结果见报告末「verify 复核」行 |
| V6 | 修订区域逐行复读 + 新测试质量审 | read 全部修改函数与 8 个新测试 | 无新引入；新测试断言强度达标（结构化字段级 + 世界字节不变 + stderr 负向断言） |

---

## 留置裁定与后续归属（非阻塞备注——APPROVED_WITH_NOTES 的 notes 全体）

| 项 | 裁定 | 理由与归属 |
|----|------|-----------|
| P3-2 stale lockfile 600s 接管语义披露 + `_stale()` 负控缺失 | **留置同意** | 触发前提（单次持锁 >600s 的病态慢操作）在单文件原子写操作下不可达正常发生；风险有界。**披露义务不灭**：接管语义 + `governance-store-ops.json`/`.governance-store-locks/` 无 check 覆盖两点，须在批 2.0 集成切片的 docstring 修订或 risk-log 一行中落账 |
| P3-3 governance_id mention 级检索 | **留置同意** | resolvability-only 语义下 mention 命中不构成假「验证」；批 2.0 集成时行锚定或 docstring 披露 |
| P3-4 repo_file 根内包含检查 | **留置同意** | 只读 `is_file`，无写入/注入面；批 2.0 收紧 |
| P3-5 bool ttl 穿透 Check 26 镜像 | **留置正确** | 引擎 Check 26 同源同洞（verify_workflow L17707）——镜像忠实优先；单独收紧反致镜像漂移。与引擎 Check 26 修复同步 |
| P3-9 引擎 `parse_impact_analysis_entries` 列位错位 | **留置正确 + 入账义务** | 出本票范围（D4 修改纯粹性）；**Coordinator 须将引擎列位错位另行入账**（独立 ticket/audit）——本写入器的骨架正则与 Check 16 逐字一致，两种世界下本票行均不产生新 finding，但引擎侧声明的对齐口径应在引擎票收口 |
| test_resume 断言强度（`assertIn(source,("apply","resume"))`） | **留置同意** | 两分支均为正确终态（resume=已施加完成 / apply=从 baseline 确定性重放一次）；测试核心断言「施加恰一次 + 终态 ok + ttl==4200」不受分支断言弱化影响——双施加仍会被 ttl 断言捕获。属测试精度优化，非防护缺口；可在批 2.0 顺手收紧（确定性时序注入） |

---

## verify 复核

- Developer 申报：verify 全量 PASSED（唯一 WARN = 版本 bump 在途态，出票范围）。
- 本审查独立实跑（后台任务收尾收集）：**Verification Result: PASSED（exit 0）**，唯一 WARN = `[WARN] plan-tracker workflow version=0.84.0, expected=0.85.0`——与申报口径**逐一吻合**，且该 WARN 属 FEAT-053 版本 bump 在途态，按本审查范围纪律（R0 起一致）不归因本票。

---

## 复审结论

**APPROVED_WITH_NOTES · unresolved_blockers=0**

- P0=0，P1=0，P2 全部修复并独立复验，硬门槛（P0=0、5 维度覆盖、逐条标注、设计一致性、AI 专项 5 项）全通过。
- 留置项全部有裁定、有归属、非阻塞，作为本报告 notes 持续可见。
- 复审链建议：本票按 APPROVED_WITH_NOTES 终态收口（Check 30 复审链 R0→R1 连续、轮次 ≤3 合规）。

*Reviewer: 同一独立 Code Reviewer（FEAT-046-CODE-R1）。只读审查 + 本报告写入 `docs/reviews/`；V2 红相复演运行于系统临时目录。*
