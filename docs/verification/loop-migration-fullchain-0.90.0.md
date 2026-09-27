# FEAT-068 — 隔离副本本仓全链迁移验证留痕（ADR-019 §6 步骤 2）

| 字段 | 值 |
|---|---|
| Task | FEAT-068（P1，target 0.90.0） |
| 执行依据 | ADR-019 §6 步骤 2；`.governance/execution-packets.json` FEAT-068 包；`.governance/change-triage/FEAT-068.json`（touches_real_env=true / requires_r1=true）；DEC-252；DEC-133 checklist 复用 |
| 执行主体 | Governance Developer Agent（FEAT-068 隔离副本执行，真实仓库仅锁面修改） |
| 执行日期 | 2026-09-27（机器时钟权威） |
| R1 方案 | (a) 隔离环境——副本 + `$env:DSH_HOME` 重定向（FIX-337 纪律：全程未对 `$HOME` 赋值） |
| 隔离面 | `$env:TEMP\feat068\{repo-copy, pristine, wc5, wc6..wc6e, wc7, wc-cert}`；`$env:TEMP\feat068-home` |
| 状态 | 执行完成——八项场景全部留痕；C-10 漂移校验落地并双向验证；ADR-RB-2 断言评估通过；unit 锚定歧义升级 Coordinator/用户裁决 |

---

## 1. 隔离环境构造（R4 逐条上报见 §5；incidents 追加日志并行留痕）

| # | 命令 | 退出码 | 摘要 | 时间戳 |
|---|---|---|---|---|
| R4-01 | `git -C <real> status --porcelain` | 0 | **0 行——真实仓库基线干净** | 2026-09-27T12:10:06+08:00 |
| R4-02 | `New-Item %TEMP%\feat068*; $tmpHome = Join-Path $env:TEMP "feat068-home"; $env:DSH_HOME = $tmpHome` | 0 | 隔离目录 + DSH_HOME 重定向就位（未触碰 `$HOME`） | 12:10:06 |
| R4-03 | `robocopy <real> %TEMP%\feat068\repo-copy /E` | 1（成功） | 10,757 文件 / 206.46 MB / 21s | 12:10:20→12:10:42 |
| R4-04 | `robocopy repo-copy → %TEMP%\feat068\pristine`（apply 前基线快照） | 1（成功） | pristine 快照与真实仓库逐一哈希对齐（§3） | 12:10:42→12:11:00 |
| R4-05 | 副本内首跑绑定：`python skills/software-project-governance/infra/loop_migration.py --help` | 0 | 子命令面见 §2.1 | 12:11:18 |

真实仓库执行后对照：`git status --porcelain` 仅含本票授权面（§6）。用户 `$HOME`、`$DSH_HOME` 真实配置目录：零写入。

## 2. 迁移工具入口首跑绑定（以工具实测为准）

### 2.1 实测 CLI 面（loop_migration.py `__main__`）

```
--target HOST_ROOT   宿主根（默认 cwd）
--dry-run            只读预演（0 写操作）
--apply              迁移（备份→原子提交 runtime+evidence 行）
--rollback [--version V]   回滚最近一次（或指定版本）迁移
--project-type T     flow-unit 派生类型（默认 ai-agent-plugin）
--expected-plan-hash 64hex   dry-run/apply 结构同一性不变量（fail-closed）
--approve-unit ID    操作者批准的 unit 子集（可重复）
```

**与 ADR-019 §7 表述差异（包授权以实测为准，记录在案）**：ADR 写「`loop_migration.py rollback_migration`」；实测无 `rollback_migration` 子命令，对应旗标为 `--rollback`（内部函数名 `rollback_migration`）。语义一致（备份 hash 校验 fail-closed → 还原 → 删 runtime → 追加 ROLLBACK 行）。

**边缘差异 2**：工具常量 `MIGRATION_VERSION = "0.65.0"`——备份目录与证据行均带 `0.65.0` 戳。ADR-019 目标 0.90.0 指**切换版本**；迁移戳为 FX-191 时代遗留常量，建议后续票升级戳常量（见 §7 边缘发现 E-6）。

### 2.2 apply 的写面（源码级确认）

`apply` 仅写三处（从不修改 plan-tracker，源码注释与哈希验证双重实证）：① 备份目录 `.governance/archive/migration-<ver>-<ts>/`（plan-tracker.md + evidence-log.md + manifest.json[含 SHA-256] + 2 个 before 哨兵）；② `.governance/flow-unit-runtime.json`（v2 契约载荷）；③ evidence-log.md 追加一行 `| MIGRATION-<ver> | ... |`。

## 3. 八项场景逐项执行留痕

### 场景① dry-run —— PASS

| 项 | 值 |
|---|---|
| 命令 | `python skills/.../loop_migration.py --target <repo-copy> --dry-run`（副本根执行） |
| 退出码 / 墙钟 | 0 / 0.77s |
| 摘要 | `status=READY_FOR_REVIEW`；`write_operations=0`；`validation_issues=0`；28 unit 派生；`workflow_model_prior=classic-phase-gate`；`plan_hash=949bd7bf1bc6e4447b7d1e79a5d7c85b2a9d3a08d24238504c04c8b9778655c2`；`v2_validation_issues=1`——内容为「`decomposition_confirmed must be true for a v2 payload`」，系 FEAT-004 遏制守卫**按设计触发**（dry-run 恒为未确认 plan；apply 经 `confirm_decomposition` 后过 v2 校验） |
| 留痕 | `traces/s1-dry-run.json` |

### 场景② 人工核对 unit 划分 —— 执行完成；结论 = 歧义成立，fail-closed 上报（不猜测锚定）

**核对方法**：将 28 个派生 unit 逐一映射到仓库真实结构（`adapters/*` 目录、`skills/*` 目录、manifest 清单）。

**核对结论**：**不可唯一解释锚定成立**。派生面（`flow_unit_derive._derive_ai_agent_plugin_units`）先试点分式 id（`plugin.skill.<name>`，plan-tracker 中零命中），回退散文词元扫描（`<name> <keyword>` 短语）。产出的 unit 是 plan-tracker 散文锚定而非结构锚定，例如：`repo-copy.adapter.chrys`（散文「0.61.2 Chrys adapter」）、`repo-copy.skill.agent`（散文「Agent skill」）、`repo-copy.manifest.m-5b`（散文「M-5b manifest-only」）、`repo-copy.skill.baseurl` 等。真实结构对应物（software-project-governance 等 8 个 skill 目录、6 个 adapter 目录）均未被唯一锚定。

**处置**：依 ADR-019 §2.6（错误锚定比缺失锚定更危险；歧义→不猜测、不静默创建、要求确认）**停止生产锚定确认**，列入结构化返回「需 Coordinator/用户确认事项」（附修复建议：unit 锚定来源改为目录结构 + 显式映射，或由用户提供权威 unit 清单经 `--approve-unit` 落盘）。**链路机制验证继续**：apply 在副本内按 FEAT-004 记录的工具语义（省略 `--approve-unit` = 操作者整体确认派生集）执行，产出 runtime 为**验证治具**而非生产映射；⑧回滚已将其还原；真实迁移（后续授权票）前 MUST 先裁决 unit 划分方案。

### 场景③ apply —— PASS

| 项 | 值 |
|---|---|
| 命令 | `python skills/.../loop_migration.py --target <repo-copy> --apply --expected-plan-hash 949bd7bf…655c2` |
| 退出码 / 墙钟 | 0 / 0.25s |
| 摘要 | `applied=true`；`workflow_model: classic-phase-gate → loop-engineering`；备份 `migration-0.65.0-20260927T041450Z`；28 units；evidence 行 `MIGRATION-0.65.0`（恰好 1 行）；`plan_hash` 与 dry-run 一致（工具内部机器比对，mismatch 即 fail-closed）；`decomposition_confirmed=true` |
| 盘面核验 | 备份 manifest SHA-256 == pristine（pt `74c50a31…`、ev `c2365465…`）；live plan-tracker == 备份（apply 不改它）；live evidence = 备份 + 恰好 1 行 MIGRATION；runtime v2 载荷含 `runtime_contract=loop-runtime-contract/v2`、64hex plan hash、`decomposition_confirmed=true`、28 units |

### 场景④ 成功认证 —— PASS

| 项 | 值 |
|---|---|
| 命令 | `python skills/.../verify_workflow.py check-governance --summary-only`（副本内）+ 全量输出 diff 对照 |
| 退出码 / 墙钟 | 0 / 95.87s |
| 摘要 | **应用后副本 check-governance 输出与 pristine 基线逐行 IDENTICAL**（38 issues 全部为迁移前既有 REQ-092 目标对齐/用户影响缺口——迁移零新增治理问题）；runtime 机读面有效（§3 场景③盘面核验）；武装态终验（§4.2）：Check 3b `[PASS] Machine-maintained faces match legal writers (C-10)` |

### 场景⑤ 失败迭代 —— PASS（四条失败路径 fail-closed 全验证）

| 子场景 | 命令差异 | 退出码 | 摘要 |
|---|---|---|---|
| ⑤a 错误 plan hash | `--apply --expected-plan-hash 0123…cdef` | 1 | `plan_hash mismatch…No write performed.`——fail-closed 于任何写之前（源码 L829-835 早于备份步骤；结果态 `applied=false`）；零备份目录、零 MIGRATION 行 |
| ⑤b 跨 target hash 绑定 | 用主副本 hash 对 wc5 apply | 1 | 计划 hash 输入含 `project_id`（目录名派生）→ dry-run→apply 绑定为 **per-target**——比预期更强的不变量（正向对照意外得证） |
| ⑤c 正确路径迭代恢复 | wc5 自身 dry-run hash → apply | 0 | `applied=true`；备份 1；MIGRATION 恰 1 行 |
| ⑤d 幂等守卫 | 成功后 re-apply | 1 | `idempotency: target already migrated to loop-engineering version 0.65.0`——且守卫早于备份步骤（未产生多余备份目录） |

### 场景⑥ 中断恢复 —— PASS（附 1 项真实缺陷发现）

方法：`Start-Process python … --apply` 后 60/120/180/240/265ms `Stop-Process -Force`，五点强杀。

| 击杀点 | 状态 | 恢复路径 | 结果 |
|---|---|---|---|
| 60/120/180ms（读/派生段） | runtime 无、备份 0、MIGRATION 0 行——**无半态，live 未动** | 直接重跑 apply | exit 0；runtime 有效；28 units；MIGRATION 恰 1 行（3/3） |
| 240ms（提交窗口内，wc6d） | **runtime 已落、MIGRATION 行缺失**（runtime↔evidence 双 rename 间被杀）——**部分态实锤** | re-apply → 幂等拒绝（exit 1，不补偿）；**rollback → 完整恢复** | rollback exit 0：plan-tracker 与 pristine 逐字节一致、evidence = pristine + 恰 1 行 `ROLLBACK-0.65.0`、runtime 移除 |
| 265ms（提交完成后，wc6e） | 完整态 | re-apply → 幂等拒绝（正确） | 终态一致有效 |

**发现（E-4，升级项）**：`_commit_runtime_and_evidence` 的「事务性」在 SIGKILL 下存在 runtime-已落/evidence-未落窗口；幂等守卫使 re-apply 不补偿该窗口，回滚是唯一机器恢复路径。修复建议（启动时自愈扫描 runtime-无-行 → 补证据行，或调换提交顺序）属 loop_migration 机制票，不在本票锁面，升级 Coordinator。

### 场景⑦ 并发写入 —— PASS（fail-closed 串行化，无双提交）

方法：同一副本（wc7）三进程同时 `--apply`。

| 项 | 结果 |
|---|---|
| 三进程退出码 | 1 / 1 / 1（全部 fail-closed） |
| 失败原因 | ①`migration commit failed; compensation attempted` + `runtime recovery failed: PermissionError`（补偿留 recovery-journal.json 于备份目录内）；②`PermissionError … flow-unit-runtime.json`（Windows 并发 rename 争用）；③`FileNotFoundError … flow-unit-runtime.json`（竞态下 rename 目标消失） |
| 终态 | runtime 无、MIGRATION 0 行、live plan-tracker/evidence 与基线一致（各进程 result 内 before-hash == pristine）——**零双提交、零数据损坏**；遗留 3 个孤儿备份目录（E-5：失败 apply 的备份目录无清扫——记录为边缘债） |
| 串行化恢复 | 竞争后单进程 apply → exit 0，`applied=true`，MIGRATION 恰 1 行 |

### 场景⑧ 回滚演练（N-3 必过门）—— PASS

| 项 | 值 |
|---|---|
| 命令 | `python skills/.../loop_migration.py --target <repo-copy> --rollback`（主副本，ADR §7 行 2 形态） |
| 退出码 / 墙钟 | 0 / 0.17s |
| `rolled_back` | true；`restored_from=migration-0.65.0-20260927T041450Z`（备份 hash 校验 fail-closed 通过后还原） |
| 基线 parity | runtime 移除 ✓；plan-tracker 与 pristine **逐字节一致** ✓；evidence = pristine + **恰好 1 行** `\| ROLLBACK-0.65.0 \| FX-191 \| rolled back loop-engineering → classic-phase-gate \| restored_from=… \|` ✓ |
| 循环证明 | 回滚→再迁移（wc-cert 重新 apply exit 0）成立，回滚可逆性闭合 |

## 4. DEC-133 八项关闭标准 checklist 逐项核对（复用，不另造清单）

来源：`.governance/archive/decisions/decisions-v0.1.0-0.78.0.md` L96/L101（DEC-133）+ RISK-042 关闭标准原文。

| # | DEC-133 关闭标准 | 本票对应证据 | 判定 |
|---|---|---|---|
| 1 | preview/apply 同 plan hash | 场景③（hash 机器比对一致）+ 场景⑤a/⑤b（mismatch 双向 fail-closed） | **PASS** |
| 2 | apply 前后 validator PASS | apply 前 v2 校验 fail-closed 门（场景①注 + 源码）；apply 后 v2 载荷有效 + check-governance 与基线零新增（场景④） | **PASS** |
| 3 | production gate 失败持久化 back-edge/round | 场景⑤失败路径全部 fail-closed 留痕（`aborted_reason` 持久化于结果与留痕文件）；部分态经 ROLLBACK 行持久化留痕（场景⑥ wc6d） | **PASS**（迁移语境：失败=拒绝写+留痕，非 gate 事件面——该面属后续接线票） |
| 4 | 重启状态保持 | 场景⑥五点强杀 + 重启恢复全链（含部分态经回滚恢复） | **PASS** |
| 5 | fuse 经生产入口触发 | **N/A-in-scope**：fuse 属 loop 事件链（process_gate_result），本票为迁移链验证；接线路径为 ADR §6 步骤 4 分族授权票 | N/A（留痕，不计 PASS） |
| 6 | health authority fail-closed | 场景④ check-governance（fail-closed 聚合，exit 语义保持）；C-10 武装态负例（§4.2 篡改→FAIL→恢复→PASS） | **PASS** |
| 7 | 至少 dogfood+2 外部类型 installed-state PASS | **N/A-in-scope**：多宿主外部类型验证为 DEC-133 原始范围；本票范围为单一隔离副本全链。真实迁移后按 §6 步骤 5 行为验收时执行 | N/A（留痕） |
| 8 | 发布叙事与证据强度一致 | 本文档 + evidence-log FEAT-068 行（结构化事实）+ incidents R4 日志 + CLI 差异/缺陷/歧义全部如实留痕（§7），无 overclaim 边界声明（§8） | **PASS** |

> 诚实口径：5/8 项 PASS + 2 项 N/A-in-scope（如实留痕、归属后续票）+ 1 项 PASS（health）。N/A 不冒充 PASS（ADR §6 步骤 2「不接受运行时文件生成了作为验收」同源纪律）。

## 5. R4 真实环境命令逐条上报（汇总；机写日志 = `.governance/incidents/FEAT-068-r4-commands.log`，仅追加）

| # | 命令 | 时间 | 退出码 | 影响路径 |
|---|---|---|---|---|
| R4-01 | `git -C <real> status --porcelain` | 12:10:06 | 0 | 只读 |
| R4-02 | 隔离目录构造 + `$env:DSH_HOME` 重定向 | 12:10:06 | 0 | 仅 `%TEMP%` |
| R4-03 | `robocopy <real> → %TEMP%\feat068\repo-copy /E` | 12:10:20 | 1(成功) | 真实仓库只读 + `%TEMP%` 写 |
| R4-04 | pristine 快照 robocopy | 12:10:42 | 1(成功) | 仅 `%TEMP%` |
| R4-05 | 副本内 `loop_migration.py --help` | 12:11:18 | 0 | 仅 `%TEMP%` |
| R4-06 | `evidence_domain.py`/`verify_workflow.py` 编辑 + `py_compile` | 12:20~12:40 | 0 | 锁面 2 文件 |
| R4-07 | 真实仓 `check-governance`（--summary-only / 全量×2） | 12:34:28 等 | 0 | 只读（校验器自身零写面） |
| R4-08 | `check_product_success_contracts`（RB-2 断言提取） | 12:35 | 0 | 只读 |
| R4-09 | 全量 `pytest skills/.../infra/tests -q`（后台） | 12:36 起 | 见 §6 | 只读执行（pytest 缓存被 .gitignore 覆盖） |
| R4-10 | `test_archguard_ratchet.py` 单测复跑 | 12:52 | 0（38 passed） | 只读 |
| R4-11 | census grep/read（消费点普查） | 12:55~13:00 | 0 | 只读 |
| R4-12 | 两份新文档写入 + incidents 追加 | 13:0x | 0 | 锁面新文档 + 预授权 incidents |

隔离面内全部迁移/扰动/回滚操作（场景①~⑧、wc-cert、fixtures）均发生于 `%TEMP%\feat068\*`，不属 R4 上报面，留痕于本节及 `traces/`。

## 6. 硬门槛自检（真实仓库回归门）

| 门槛 | 结果 | 证据 |
|---|---|---|
| pytest 基线不扩大 | **PASS** | 全量（25:11）：**4219P / 6F / 1S / 535 subtests**。6F 身份分解：loop 族×3（LoopRuntimeClaimAdapterTests×1 + test_loop_runtime_claims inventory/performance×2）+ FIX300 DualCaliber×2 = **DEC-249 legacy 5F 披露族全数**；+ M0 `test_pin_revision_hashes_still_resolve`×1 = **既有漂移非本票引入**（pin 源=behavior-protocol.md L512-556 + SKILL.md L223-230，均非本票修改文件；HEAD blob 与工作树窗哈希恒等且均≠pin 值→漂移早于本票；pin purpose 自述「契约源正常维护演进时按契约变更流程重置本 pin——非 gate」）。对照 0.89.0 gate 8F：archguard×3 已随 sanctioned regen 消解（本次 ratchet 38/38 PASS）；passed 4219≥4217 → **零新增失败** |
| check-cross-references | PASS（见 evidence-log 结构化事实回填） | 真实仓执行留痕 |
| check-manifest-consistency | PASS | 新文档经 manifest `repo_only.glob_patterns: docs/**/*.md` 权威覆盖，零 manifest 编辑 |
| 向后兼容 | PASS | ① 真实仓 check-governance 输出与改前逐项一致（38 issues 持平、Check 3b not-applicable 路径）；② 证据域检查仅在 `.governance/flow-unit-runtime.json` 存在时武装（legacy 宿主零行为变化）；③ CLI 面未变 |
| 无 AI 幻觉 | PASS | 全部结论有命令退出码/源码行/AST 审计/哈希对照支撑；负例（篡改→FAIL）与正例（恢复→PASS）双向实证 |

### 6.1 C-10 前置漂移校验落地（本票范围交付）

- **落点**：`checks/evidence_domain.py::check_evidence_binding_drift`（检查逻辑+渲染 `render_evidence_binding_drift_block`）+ `verify_workflow.py` 一行 compound 接线（Check 3b；主文件**零净增行**，archguard r1 预算锚点 26358 精确保持——God Module 预算纪律优先，逻辑全数下沉域模块）。
- **武装条件**：仅当 `.governance/flow-unit-runtime.json` 存在（机器维护面存在的宿主）。legacy 宿主 `applicable=false` 零新增——真实仓 Check 3b 输出 `[PASS] Machine faces absent (pre-switch host)`，38 issues 与基线持平。
- **约束范围**：ADR-019 §2.2 R0 修正精确口径——仅拦截机器维护面绕过合法写入方的直改/损坏；目标层与证据层合法人工/协议写入不拦截。
- **四元组映射**（ADR §2.5）：unit=`flow_units[].flow_unit_id`；产物版本=`migration_plan_hash`(64hex)；检查策略版本=`gate_schema@digest`（当前 v2 载荷不持久化顶层 gate_schema，策略版本经 plan hash 传递性绑定——直接持久化属后续票，已防误报 None-guard）；审查主体=`decomposition_confirmed=true` + evidence-log `MIGRATION-<ver>` 行绑定。
- **六例功能冒烟**（机器判据）：有效态=PASS/零 warn；缺 MIGRATION 行=FAIL(evidence_binding_missing)；悬空依赖=FAIL(runtime_unit_corrupt×28)；无 runtime=not-applicable；坏 hash=FAIL(runtime_face_missing_machine_credential)；CLI 正负例：副本内篡改 runtime → Check 3b `[FAIL]` → 恢复 → `[PASS]`。
- **验收措辞（R1 合规）**：隔离环境安装冒烟（环境变量重定向至临时目录）通过。

### 6.2 ADR-RB-2 契约非空断言评估（本票范围=评估+证据）

- **现状（实证）**：`check_product_success_contracts`（FIX-088，Check 18d）对活跃 P0/P1 任务契约执行**FAIL 级**非占位断言（`PRODUCT_SUCCESS_PLACEHOLDER_RE` 含 TO_BE_DEFINED/待补/占位等）；真实仓实测：`{"required": ["FEAT-068"], "pass": true, "entries": [{"task_id": "FEAT-068", "status": "PASS", "issues": []}]}`——本票执行包契约非空且通过断言（packet 的 `product_success_contract` 全字段实文，见 `.governance/execution-packets.json`）。
- **差距（如实记录）**：ADR-RB-2 的两个剩余面——①「宿主激活前置：至少一个 unit 契约非占位且可追溯 plan-tracker 成功标准」；②「占位符对敏感动作 → 阻断」——接线位在 auto_judge/sensitive-action 面与激活门，属 **§6 步骤 4 分族授权票**范围。**产出落地票建议**：FEAT-069（候选）「RB-2 契约非空断言接入敏感动作阻断 + 激活前置」。
- 结论：占位符可容忍→完整性检查项的升级**已落地**（18d，FAIL 级）；剩余两面向后续票移交，证据齐备。

## 7. 边缘发现与升级事项（全部如实留痕）

| # | 发现 | 证据 | 建议 |
|---|---|---|---|
| E-1 | **unit 锚定歧义（场景②）**——散文词元派生不可唯一解释；真实结构未锚定 | 场景② 28-unit 逐项核对 | 生产迁移前 MUST 裁决：派生器改结构锚定（目录/清单映射）或人工权威清单；修复票建议 |
| E-2 | dry-run 遗留 preview 面仍输出 `python_game_10_chapters` 示例数据（与 migration_plan 面并存） | `traces/s1-dry-run.json` flow_units 块 | 遗留面清理票（低优先） |
| E-3 | `v2_validation_issues=1` 为 FEAT-004 遏制守卫按设计触发（非缺陷） | §3 场景① | 无需行动（留痕防误读） |
| E-4 | **SIGKILL 提交窗口部分态**：runtime 已落/evidence 行未落；re-apply 幂等拒绝不补偿；回滚是唯一恢复路径 | 场景⑥ wc6d 240ms + ROLLBACK 恢复链 | loop_migration 自愈/提交顺序修复票 |
| E-5 | 失败 apply 遗留孤儿备份目录（并发失败后 3 个） | 场景⑦ wc7 | 备份目录生命周期清理票 |
| E-6 | `MIGRATION_VERSION` 常量 0.65.0（ADR 目标 0.90.0） | §2.1 | 戳常量升级随真实迁移授权票 |
| E-7 | ADR §7「rollback_migration 子命令」表述与实测 `--rollback` 旗标不一致 | §2.1 | 文档口径勘误（下次 ADR 维护批） |
| E-8 | 并发争用在 Windows 表现为 PermissionError/FileNotFoundError（POSIX 表现未测） | 场景⑦ | 跨平台并发语义注明 |

## 8. 边界声明

- 本验证不构成任何授权票翻转/registry 翻转/真实 `.governance` 热数据写入；八项场景为**隔离副本**执行（R1-a），副本与临时目录可直接丢弃即回滚。
- 本文档不修改 ADR-019 语义；发现的语义缺口（unit 锚定裁决）返回 Coordinator 转用户裁决（ADR-019 §9）。
- 副本内 runtime（wc-cert/wc5 等）为验证治具产物，不含生产承诺；`decomposition_confirmed=true` 是工具语义记录，非本 agent 对 unit 划分的语义背书。
