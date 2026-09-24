# REVIEW-FIX-375-CODE-R0 — writer 族三边缘收口（代码审查 · 0.88.0 阶段 A1）

- **Task**: FIX-375（writer 族三边缘收口）｜ **Round**: R0 ｜ **审查对象**: 工作树未 commit 修改，3 文件（+249/−7，`git diff --stat` 核验：verify_workflow.py +13−2 内含注释、governance_store.py +71−5、test_governance_store.py +172）
- **审查依据**: `agents/code-reviewer.md` + `skills/code-review/SKILL.md`；git diff 逐行；两处 main() 与 pipeline 全文；contracts/task_row_update/baseline_metadata/dsh_compat 交叉文件；活体探针与 pytest 实测（见 §6 证据清单）
- **结论**: **APPROVED_WITH_NOTES** ｜ **unresolved_blockers = 0**（BLOCKING=P0 计数=0）
- **计数**: P0=0 ｜ P1=1（F-1，需 Coordinator 显式处置：本轮一行补齐或明示遗留+披露勘正）｜ P2=2 ｜ P3=3

---

## 1. 重点审查六项逐项结论（任务行强制义务）

### 1.1 缺陷落点更正确认 —— **成立（活体实证）**

任务行原定位（governance_store.py main()）不成立、真实落点为引擎分发面，归因核验通过：

- **face A**（governance_store 直跑）: `main()` L2204-2209 `return _CLI_HANDLERS[args.command](args)` + L2213 `sys.exit(main())` —— **本 diff 未触碰该区**（git diff 无此区 hunk），拒绝 → `_emit` 返回 2 → exit 2。活体探针：HEAD 副本与工作树副本同场景均 **exit 2**（§6 探针③④）。
- **face B**（verify_workflow 引擎分发）: 旧代码 `commands[cmd](args)` 为语句（返回值丢弃）+ 模块尾裸 `main()`（返回 None → exit 0）。活体探针：HEAD 副本同一拒绝场景打印完整结构化拒绝 JSON（`code: schema_violation, error: true, disposition: validation`）但 **exit 0** —— 假绿活体复现（§6 探针①）；修复后同场景 **exit 2**（§6 探针②）。

### 1.2 行为变更面 —— **writer 族 8 个 handler 全数核验；另发现 1 个未披露面（F-2）与注释标度不准（F-3）**

AST 全量探针（commands dict 96 个唯一 handler）：

| 类别 | handler | 返回风格 | 透传后退出码变化 |
|---|---|---|---|
| writer 族（FEAT-055 批，dict L25491-25498） | task-row-update / locks-extend / locks-amend / locks-release / evidence-append / decision-append / baseline-register / baseline-evaluate（**8 个**，非申报口径的 7 个——F-5） | 全部 return-style（`_emit` / `_execute` / `run_register` / `run_evaluate` → int） | 恒 0 → 透传（各族标度见 F-3）——**披露内，正确** |
| 非 writer·有返回值 | `cmd_check_dsh_preset_compat`（L21758 → `run_cli`） | return-style | `--fail-on-issues` + FAIL verdict：0 → **1**（dsh_compat.py L2072-2073）——**未披露**（F-2） |
| 非 writer·有返回值 | `cmd_dsh_doctor`（L21812-21819） | 混合：非零走 `sys.exit(code)`，成功路径仅 `return 0` | **无实际变化** ✓ |
| 其余 86 个 | 79 个模块内 none-only/no-return + 7 个导入 sys.exit-style（archguard_ratchet L✓、governance_cost exit 1/2、bootstrap_aggregate exit 1、checks/manifest exit 1、capability_registry exit 1、injection_budget exit 1、review_domain L3405 exit 1） | sys.exit-style | **无变化** ✓（失败在 handler 内部退出，成功返回 None → exit 0，与旧行为一致） |

**消费方排查**：全仓 grep `verify_workflow.py <writer 命令>` 仅 1 处命中且为注释（checks/loop_runtime_claims.py L241，baseline-register 溯源指引），无 hooks/脚本/编排依赖旧 exit 0 行为；`check-dsh-preset-compat` 仓内调用点均不带 `--fail-on-issues`（release-checklist×4、review×4、dsh_doctor.py 提示文本），F-2 的实际爆炸半径限于仓外 CI 消费方。

**task_row_update / baseline_metadata 文件未改、退出码共享透传**：确认无隐性破坏——两模块 cmd 包装是纯 int 返回（`_execute`→`ExitCode.*`；`run_register/run_evaluate`→int），旧分发同样丢弃其返回码（同 bug 面），透传即修复；模块自身 CLI（各自 main+sys.exit）语义不受影响。

### 1.3 无 SystemExit 桥接 —— **成立**

- verify_workflow `main()` 保持普通函数：函数体唯一 `sys.exit(2)` 在 L24383（malformed `--project-root`，**既有**）；新增仅 `return commands[cmd](args)`（L25511）与模块尾 `sys.exit(main())`（L25515，仅 `__main__` 面，import 面不执行）。修复未新增任何 SystemExit 路径（措辞精度小疵见 F-6）。
- governance_store `main()` 未被本 diff 触碰，本来就返回 int。
- 实测：pytest 全量导入两模块无副作用；`test_engine_main_returns_writer_refusal_code`（in-process 调 `vw.main` 返回 2 不抛）即 import 语义冻结的守护钉。

### 1.4 边缘②结构化形状 —— **成立**

- `code: schema_violation` + `disposition: validation`：contracts.py L851-852 `ERROR_CODE_DISPOSITIONS["schema_violation"] = "validation"` ✓。
- 与 writers 自身约定同形：writers 的裸 `_refuse` 拒绝（如 L1645-1648 `{code, detail}`）经 `@_returns_payload`（L347-361）补 `error`+`disposition` 后渲染为 **{code, detail, error, disposition} 四键**——`_run` 的 ContractViolation 分支（L1974-1979）产出**完全相同的四键** ✓（注释「raw-dict shape, the same convention as the writers' own _refuse」措辞精确）。
- `_error_result` 不可用理由成立：`_error_result`（L317-329）构造 `WriterResult`，其 `__post_init__`（contracts.py L1079-1083）**无条件再校验 `operation_id`**——对「关于非法 id 的拒绝」，构造即二次抛 ContractViolation，死循环不可用 ✓。
- 面语义钉：CLI 面转结构化拒绝（exit 2、stdout JSON、stderr 无 Traceback）而**库面保持抛 ContractViolation**（`ContractViolation(ValueError)`，contracts.py L205）——`test_library_face_keeps_contract_exception`（test L1377）反向守护到位。

### 1.5 边缘③审计补章 —— **resume 腿修复正确；但 re-apply（baseline）腿缺口未闭合且新注释声明过宽（F-1，P1，活体复现）**

**成立部分**：
- pre-read 时机正确：`_complete_pending`（L1598-1622）在同一事务内置 `status=ok` + `pending_effects=None` + `baseline_effects=None`（L1610-1614）——清单必须在完成前捕获，pre-read 置于 pipeline 调用前（L1864）满足 ✓。
- guard 正确：status==pending + command==locks-release + `input_fingerprint` 与调用方同指纹（L1858-1859 计算口径与 pipeline 一致）三重门，外来/漂移条目一律 `[]` 不盖章；下游 `replay_source` 由 pipeline 在锁内现判，pre-read 陈旧只会导致**不盖章**，不会盖错章 ✓。
- 各腿零变化声明核验：**ledger replay 腿**（status==ok → `_replay_payload`，replay_source=="ledger"）两分支均不触发、`resume_released` 因 status!=pending 恒 `[]` ✓；**drift 腿**（manual_intervention）与**各 refusal 腿**无 stamp 事务 ✓；**fresh apply 腿** `owned_files` 由 `effects_of` 首调闭包捕获（L1882-1894）非空 → 第一分支行为与旧码一致 ✓。
- 「历史 ok 条目不追溯补写」边界披露**合理**：`_complete_pending` 已清空 effects，世界已释放，历史清单不可重建，无从补写 ✓。

**不成立部分（F-1）**：REVIEW-FIX-370-CODE-R0 F-1 明确覆盖**两条**恢复腿——「world==target 腿 + world==baseline 的 re-apply 腿（payload 同带 `replay_source=="apply"`，stamp 靠 `and owned_files` 兜住）……两条跨进程恢复腿完成的 ok 行均无 released_files 章」。本修复的 elif 仅认 `replay_source=="resume"`；re-apply 腿（`_locks_execute` L1525-1531：world==baseline → 重放 mutator → `_apply_locks` → `source="apply"`）上 `effects_of` 从未被调用 → `owned_files==[]` → 第一分支短路 → **仍不盖章**——而此时 `resume_released` pre-read 数据就在手上（pending 条目未消费）。**活体复现**（§6 探针⑤）：`replay_source: apply, status: ok, released_files: MISSING`。且新注释（L1924-1926）声称「making the audit semantics identical on both completion legs」——对 re-apply 腿为假，重蹈了 F-1 批评过的「披露不完整」模式。锁释放本身各腿均正确，纯审计完整性问题（与 F-1 原判级一致），不阻断。

### 1.6 测试质量 —— **7 新测试断言实质、红态真实；一处覆盖缺口（即 F-1 的同款）**

| 测试（行号） | 红态真实性 | 绿态钉住 | 判定 |
|---|---|---|---|
| test_resume_leg_completing_release_stamps_released_files（L1166） | 真：修复前 resume 腿不跑 `effects_of` → ok 行无 `released_files` → 断言必红；fixture 手造 pending 条目（`_ledger_entry` 签名逐参核对 ✓）+ 世界已释放，场景构造正确 | `replay_source=="resume"` + `released_files==["docs/a.md","docs/b.md"]`（= pending_effects 键集 sorted） | ✓ |
| test_malformed_operation_id_structured_exit2_no_traceback（L1327） | 真：修复前 ContractViolation 穿透 `_returns_payload`（只捕 StoreError）→ 裸 traceback exit 1 | returncode 2 + stdout JSON code + stderr 无 Traceback | ✓ |
| test_cmd_face_renders_structured_schema_violation（L1367） | 同上（cmd 面） | code 2 + error/code/disposition/detail 四键 | ✓ |
| test_library_face_keeps_contract_exception（L1377） | 守护钉（非红测） | 库面保持抛 ContractViolation（防过度转换） | ✓ |
| test_engine_main_returns_writer_refusal_code（L1406） | 真：旧分发丢弃返回值 → main 返回 None | `vw.main(...)` 返回 2 + stdout JSON | ✓ |
| test_engine_subprocess_refusal_exit2（L1416） | 真（本审查探针①已独立活体复现同款红态：exit 0） | 真实进程 exit 2 | ✓ |
| test_engine_subprocess_success_exit0_unchanged（L1427） | 守护钉 | 成功仍 exit 0（防过度透传破坏正常面） | ✓ |

守护钉不掩盖回归：in-process 钉与 subprocess 钉分离，成功面/拒绝面/库面三层互锁。**覆盖缺口**：无 re-apply 腿 stamp 测试（有则 F-1 当场红）；引擎面对 task-row-update（标度 3/4/5/6）与 baseline-evaluate（verdict 1/2）无退出码钉（透传逻辑族级泛化，经 locks-extend 间接覆盖，风险低）。

---

## 2. 五维度结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | **通过（附 F-1/F-2/F-3）** | 三边缘主路径逻辑逐行核验成立（§1.1/1.4/1.5）；红绿活体探针双向证实；恢复腿/并发/陈旧 pre-read 均向「不盖章」fail-closed，无错章路径；ledger 为 JSON 时 `file_locks` 键恒为 str，`sorted()` 无 TypeError 面 |
| 安全性 | **通过** | 无新输入面：`_pending_released_files` 只读台账且三重 guard（status/command/fingerprint），清单仅入审计字段、不作路径使用；UTF-8 显式 + 同目录 temp + `os.replace` 原子写纪律未触碰；`_run` 仅收窄捕获 ContractViolation（StoreError 语义不变），库面异常语义测试钉住 |
| 可维护性 | **通过（附 F-1/F-3 注释勘正项）** | guard 函数独立成文、docstring 引用 F-1 溯源清楚；三处注释与事实有偏差（F-1 「identical on both completion legs」、F-2 「sys.exit-style handlers...return is None」、F-3 标度），需随处置勘正 |
| 性能 | **通过** | 每次 locks-release 增 1 次台账 JSON 读（小文件）；测试侧增 2 个引擎子进程导入，实测全套件 3.51s 无感 |
| 测试覆盖 | **通过（附覆盖缺口注记）** | 100/100 零回归（本审查独立复跑）；7 新测试红态真实、三层互锁；缺口=re-apply 腿 stamp 无测试（F-1 同源） |

## 3. AI 代码专项 5 项

| # | 检查项 | 结论 | 依据 |
|---|---|---|---|
| 1 | mock 残留 | **无** | `mock` 仅用于 stdout 捕获（test L1368/L1407），无产品行为打桩；子进程测试走真实进程 |
| 2 | 硬编码返回值 | **无** | 产品 diff 无硬编码返回；测试硬编码期望码属断言本体 |
| 3 | 幻觉 API 调用 | **无** | 逐个核对：`gs._ledger_entry`（签名 L640-641 逐参匹配）、`gs._ledger_transaction(gov, fn)`（L608 默认超时 ✓）、`gs._fingerprint`、`gs._atomic_write_bytes`、`gs.LEDGER_FILE_NAME`、`_make_governance_dir`（L116）、`seed_release_fixture`（L1047）、`call_release`（L1092）、`vw.main`——全部实存 |
| 4 | 未实现 TODO | **无** | diff 全文无 TODO/FIXME/占位 |
| 5 | 过度实现 | **无** | 改动贴任务行三边缘；elif+guard 函数为 F-1 最小承接；无顺手改、无范围爬移（registry/manifest 未触碰，FEAT-020 冻结面不在本 diff） |

## 4. 发现清单

| # | 级别 | 位置 | 事实与依据 | 建议 |
|---|---|---|---|---|
| F-1 | **P1** | governance_store.py L1909-1927（stamp 分支）、L1920-1926（注释）、L1525-1531（re-apply 腿）、L1864（pre-read） | F-1（REVIEW-FIX-370-CODE-R0）明确两条恢复腿均缺章；本修复仅闭合 resume 腿；re-apply 腿 `owned_files==[]`（`effects_of` 未被调用）→ 第一分支短路、elif 只认 "resume" → 仍无章；**活体复现**：`replay_source: apply, status: ok, released_files: MISSING`（§6 探针⑤）；注释「identical on both completion legs」对该腿为假 | 首选本轮一行补齐：`elif payload.get("replay_source") == "apply" and not owned_files and resume_released:`（fresh apply 腿 `resume_released==[]` 天然不触发，幂等安全）+ 补 re-apply 腿测试；若 Coordinator 裁决遗留，则**必须**同步勘正 L1920-1926 注释为如实披露并出槽承接票 |
| F-2 | P2 | verify_workflow.py L25507-25508（注释）、L21758、L24744；dsh_compat.py L2072-2075 | 透传同时改变了 writer 族之外的一个可达面：`check-dsh-preset-compat --fail-on-issues` FAIL verdict exit 0→1（`run_cli` 返回 1 被旧分发丢弃——同款假绿）；diff 注释「sys.exit-style engine handlers are unaffected (their return is None → exit 0)」对该 handler 不成立。同向正确但**未披露**；仓内无消费方回归（调用点均不带该旗标） | 注释/任务披露补一句影响面勘正；无代码动作必需 |
| F-3 | P2 | verify_workflow.py L25504-25506；task_row_update.py L1142-1178；baseline_metadata.py L977-1052 | 注释标度「(0 ok / 2 refusal / 3 retryable)」仅对 governance_store `_emit`（L1982-1986）准确；task_row_update 为 0/2 usage/3 validation/4 conflict/5 retryable/6 manual；baseline-evaluate 为 0 pass/1 fail/2 not_evaluable（+3 storage）。透传后引擎面暴露**各族不同标度**，消费方按注释写分支会误判 | 注释改为按族列标度（或指向各模块契约表） |
| F-4 | P3 | governance_store.py L1864（pre-read）vs L1904（`_TargetLock`） | pre-read 在目标锁块外：同 op-id 并发重复调用 + 首调在「登记后、写锁前」崩溃的窗口组合下，pre-read 读不到 pending 条目 → resume 腿盖章被跳过（仅审计字段，世界状态不受影响；M7.6 串行化下概率极窄） | 将 pre-read 移入 `with _TargetLock(...)` 块内（仍在 pipeline 调用前），一行位移 |
| F-5 | P3 | verify_workflow.py L25491-25498；本报告 §1.2 | 申报口径「7 个 handlers」与实测不符：writer 族 return-style handler 为 **8 个**（locks×3 + evidence/decision + task-row-update + baseline×2）；另有两个非 writer handler 含返回值路径（§1.2 表） | 披露计数勘正为 8（+2 条件性） |
| F-6 | P3 | verify_workflow.py L25509-25510、L24383 | 注释「no SystemExit raised from main()」作为**变更描述**成立（本修复零新增），作为 main() 的**一般性质**不成立——既有 L24383 `sys.exit(2)` 与 argparse parse 错误仍可抛 SystemExit；import 语义确实冻结（`__main__` 尾才包 sys.exit） | 措辞可改「no NEW SystemExit」，非必改 |

## 5. 硬门槛裁决

| 门槛 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞数 | = 0 | 0 | ✓ |
| 5 维度全覆盖 | 100% | §2 五维逐一有结论 | ✓ |
| 每条发现标注级别 | 100% | F-1~F-6 均带 P 级+位置+事实 | ✓ |
| 设计一致性 | 已完成 | 与 0.86.0 模块契约 docstring（L88-94 组合根双面）、FEAT-055 装配、F-1 承接范围、B-10 登记先行时序一致；无 ADR 偏离（F-1 为 F-1 范围承接争议而非新偏离） | ✓ |
| AI 专项 5 项 | 全部完成 | §3 五项逐一有结论 | ✓ |

## 6. 证据清单（本审查独立实测）

1. `git diff --stat`：3 文件 +249/−7，与申报一致（2026-09-24 工作树）
2. `python -m pytest tests/test_governance_store.py -q` → **100 passed in 3.51s**（零回归独立复跑）
3. 7 新测试点名 `-v -k ...` → **7 passed**（L1166/1327/1367/1377/1406/1416/1427）
4. **探针①红态复现**：`git show HEAD:verify_workflow.py` → $TEMP 副本（仓库零写入），同拒绝场景（locks-extend --task nope）→ stdout 结构化拒绝 JSON 但 **exit 0**
5. **探针②绿态**：工作树同场景 → **exit 2**；**探针③④ face A**：HEAD 与工作树 governance_store.py 直跑同场景均 **exit 2**（归因成立的决定性四联）
6. **探针⑤ F-1 复现**：$TEMP 脚本构造 pending 条目 + world==baseline → `locks_release` → `replay_source: apply, status: ok, released_files: MISSING`
7. `verify_workflow.py check-manifest-consistency` → **PASS exit 0**（857 canonical）
8. 引擎面+registry 回归套件（本审查后台复跑 216s）：**3 failed, 1001 passed, 126 subtests passed** ——与申报（1001 绿/3 既有基线失败）**完全一致**；3 失败均为 loop-runtime-claims / FIX-300 双标尺 identity 面（`test_claim_command_emits_complete_pass_report` / `test_fixture_identity_mode_agrees_with_engine_on_present_sources` / `test_identity_host_source_drift_reproduces_divergence_shape`，断言 installed_host 语义扫描 verdict PASS≠BLOCKED）——环境状态依赖基线，代码路径与本 diff 触及的分发尾无交集、非退出码断言，与 stash 隔离结论互证；静态面本审查未发现新增回归源（透传仅影响 §1.2 表列 handler，均各有成功面守护钉）

## 7. 总结论

**APPROVED_WITH_NOTES ｜ unresolved_blockers = 0**（P0=0，硬门槛全过）。

通过但不静默：**F-1（P1）需 Coordinator 显式处置**——推荐本轮一行补齐 re-apply 腿（`not owned_files and resume_released` 分支 + 补一条测试），或在明示遗留的同时强制勘正 L1920-1926 注释披露；F-2/F-3 随注释勘正一并处理；F-4/F-5/F-6 记录即可。按 code-review SKILL 关闭规则（P0=0 且 P1>0 有处置计划 → 有条件合并），遗留项须入跟踪表。
