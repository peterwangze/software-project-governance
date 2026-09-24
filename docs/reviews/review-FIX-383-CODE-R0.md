# Review: FIX-383 — B-7c 发版管线自举（Code Review · R0）

> **结论：APPROVED_WITH_NOTES ｜ unresolved_blockers=0 ｜ P0=0 · P1=0 · P2=1 · P3=4**
>
> | 字段 | 值 |
> |---|---|
> | Task | FIX-383（P2，0.88.0 阶段 B2——rollback-0.86.0 §8 #7 ⑩拆票之一） |
> | 轮次 | R0（首次审查） |
> | 审查对象 | 工作树未 commit diff：5 文件 +796/−15（closure_chain.py +147、verify_workflow.py +264、test_closure_chain.py +393、checks/version.py ±4、TOOLS.md +3——`git diff --stat` 实测与申报一致） |
> | 审查方法 | 逐行 diff + probe/resume 引擎逐边界核对 + 五检查活体逐条溯源 + 四套件独立复现（49P/74P/25P/verify PASSED）+ 权威源比对（rollback-plan §8 #7 / version-plan §2 B2·L88 / triage JSON / FEAT-056·057·060 契约原文 / FIX-379 pre-probe 语义注记） |
> | 结论性质 | APPROVED_WITH_NOTES 仅表示硬门槛通过，不替代测试或发布审查 |
> | 独立结构字段 | **unresolved_blockers=0** |

---

## 0. 审查输入与事实基线

- 仓库根：工作目录 = 治理插件仓库根（plan-tracker 0.88.0 阶段 B2；FIX-383 行「🔄 已 lock 待派发 (2026-09-23——0.88 阶段 B2)」实读）。
- diff 范围实测：`git status --porcelain` = 恰 5 个 M 文件，与派发清单一致；无未跟踪产物泄漏。
- 权威溯源：`docs/release/rollback-plan-0.86.0.md` L160（§8 #7「B-7 index-rebuild / 大表迁移 / 发版管线自举」）= 拆票来源；`docs/planning/version-plan-0.88.0.md` L38（B2 = FIX-383，验收「自举路径实现 + 故障注入恢复测试」）+ L88（②发布自举路径审计面——「时序可后置兑现」，与 Developer 边缘披露第 4 条一致）。
- 验收定义复现：plan-tracker FIX-383 行「验收 = 自举路径实现 + 故障注入恢复测试（中断后重入零人工修复）」——10 测试中 3 条为父控 kill 故障注入纵切（见 §2.5）。

---

## 1. 五维度审查结论

### 维度 1：正确性 — ✅ 通过

**自举链 spec（closure_chain.py L616-655 新增 RELEASE_WINDOW_BOOTSTRAP）**：两步（`write-guard-converge` cli + `bootstrap-ready` summary）；`required_inputs=[]`；probe `command_exit` argv = `write-guard-bootstrap --check-only`（主 argv 不含 `--check-only`，`test_builtin_bootstrap_spec_parses` 双向断言）；`dry_run_flag=None` 为 parse-level 分辨率（--help 契约，locks-amend 先例注记在案）。

**前探针语义承载核实（MUST #1）——正确，且是既有引擎语义的零特例复用**：

| # | 边界 | 行为 | 证据 |
|---|------|------|------|
| 1 | probe 判定 | `_run_probe` `command_exit` 分支（closure_chain.py L877-893）：`satisfied = proc.returncode == 0`——exit 0 = `--check-only` converged | 只读世界查询，`anchor` = stdout 前 200 字节 |
| 2 | run/resume 边界统一 | `run_chain` L1458：probe 在每步执行前运行（resume + fresh alike），FIX-379 item-4 pre-probe 语义注记原文在场（L1447-1457）——probe 是执行决策输入，非执行后验证 | 承载声明成立：FIX-379 pre-probe + FEAT-056 effect-based resume 均为既有代码路径，本票未改动引擎 |
| 3 | 已收敛重入 | probe satisfied → `step_reconciled`（L1469-1483），guard **不重跑** | 实测：`test_converge_reaches_ready...` 第二次运行后 `.write-guard-state.json` 字节相等 |
| 4 | bookkeeping 在前 | `step_state=="completed"` → completed + note（L1464-1468） | 实测 note = "bookkeeping present; probe confirms effect" |
| 5 | 未收敛执行 | probe miss → 落入执行 `write-guard-bootstrap`（converge 模式）→ exit 0/1 分派 | 实测：fresh fixture converge → ready；R6 损坏 → blocked |
| 6 | converge 拒绝传播 | verify_workflow exit 1 + 顶层 JSON `code:"manual_intervention"` → `_refusal_from_cli_output` 第三来源识别（L1062-1064）→ `step_failed` → 链 blocked exit 2（L1922-1925） | 实测：`test_corrupt_ledger...` exit 2 / status blocked / code=manual_intervention |

**reconcile-vs-execute 判定的世界一致性**：probe 判定的对象是**世界本身**（五检查读基线/台账/受管面），不是 journal——「查世界不信日志」在本链成立。converge 内部双遍自洽：persist 遍（`check_governance_write_shapes(persist_state=True)`）写基线后，world 遍（`check_release_bootstrap_world` 内 `_reconcile_row_families(persist_state=False)`）对同一世界重对账 → 零 diff → 零 issue，无「自己刚写的状态被自己判发散」的自反窗口；基线写入让行/失败时 world 遍会如实报 `row_families_clean` 未收敛（verify_workflow.py L23625-23646 让行/失败双分支响亮披露）→ converge 返回 manual_intervention → 链 blocked，**不静默吸收**。

**_summary_payload 泛化（L134-215）——字节级等价独立核对**：新格式 `"Chain: {2} {3}"` 拼接 `_CHAIN_SUMMARY_BODIES["standard-ticket-closure"]`（= 旧字面量 `(FEAT-056 standard ticket closure)\nTask row flipped...` 段）在标准链上与旧 `{2} (FEAT-056 standard ticket closure)\nTask row...` 逐字节相同；subject 表条目同样恒等。`test_standard_chain_summary_bytes_unchanged_by_chain_awareness` 断言完整 pre-FIX-383 字面量 + unknown chain fallback 同文本（表 miss → `.get(chain_id) or _CHAIN_SUMMARY_BODIES["standard-ticket-closure"]`，L190-191）——自定义 `--spec` 链输出不变。

**_builtin_spec（L1885-1894）**：未知 chain_id → `ValueError` → cmd_run 捕获 → `schema_violation` exit 2（L1916-1921）——closed registry fail-closed；deep copy 经 `json.loads(json.dumps(template))` 保留（防 spec 常量被 run 间污染）。

**五检查（verify_workflow.py L23864-24042）逐条活体**：

| 检查 | 判定逻辑 | 实测证据 |
|---|---|---|
| `guard_state_current` | state 缺席 + face-5 SKIPPED = 零足迹主机 ok（L23973-23978）；缺席 + 受管面在场 = FAIL（首跑 amnesty 恢复路径）；corrupt/外来 schema（`_load_write_guard_state` L23131-23144 issue）= FAIL，恢复 = converge 显式重建 | `test_check_only_..._unbaselined_window`（exit 1 + zero-write）+ `test_foreign_state_schema_...`（schema_version 99→1，重建后世界转绿） |
| `row_families_clean` | probe 遍 `persist_state=False`（L23148-23172 契约：probe callers never consume the window）零问题 | converged 报告零 issue；发散场景由 checks[].detail 携带写入器补凭证处置文本 |
| `violation_ledger_healthy` | `load_ledger`（write_guard_state.py L341-374）：损坏/外来 schema → `(None, issue)`，R6 永不静默重建（重建=amnesty 全部 open 违规——docstring 明文） | `test_corrupt_ledger...` exit 1 + 三检查联动 |
| `no_pending_txn` | `pending_txn` 非空 → FAIL；恢复 = 三分支 `resume_pending_txn` | `test_pending_txn_...`：journal 清空/违规 consumed/grant used 三断言 |
| `ledger_no_drift` | open 违规的 `after_hash` 不再命中其登记身份（records_index digest 对账）→ drift；面缺席 = drift（消费按资格规则）；面 unreadable → 不双计（由 row_families_clean 承载，L23953-23955） | `test_ledger_drift_...`：object_id="5" 指向 EOF 外 → drift 检出 → converge 消费 → drift 清零 |

**ledger 不可读联动 fail-closed**（L23913-23927）：healthy / no_pending / no_drift 三检查同轮 FAIL，open_count=None 如实输出——无部分判定、无静默前移。

### 维度 2：安全性 — ✅ 通过

- 注入面：probe/step argv 均经 `resolve_template`（untrusted → argv list，never a shell line——L124 既有契约），新链无新模板键引入 shell 语义；`vw_cli` 映射为 INFRA_DIR 绝对路径拼接（L678）。
- 敏感数据：无硬编码密钥/token；报告 tool 字段为机器来源戳（`governance-write-guard/release-bootstrap-check`）。
- fail-closed 强度（MUST #4）：R6 损坏台账阻断 + **台账零写**（测试对 ledger 文件前后 `read_bytes()` 相等断言——损坏字节原样保留，恢复=人工按规则，不吸收不前移）；converge 结构面 FAIL（faces 1-4）→ `manual_intervention` 结构化拒绝（L23994-24005）；未知 chain → exit 2；不可判定态（面 unreadable、drift 不可判定）全部响亮——无静默吸收路径。
- 「治理记录零写入」声明核实：converge 唯一写面 = `check_governance_write_shapes(persist_state=True)` 的守卫自身工件——状态基线 `.write-guard-state.json` + 违规台账 `.write-guard-violations.json` + 共享锁目录 `.governance/.governance-store-locks/`（write_guard_state.py L96-98 单锁源声明）；faces 1-4 只检不改（L23453-23460 契约原文）。`do_not_stage` 追加三元组与该写面精确对应（closure_chain.py L160-170）。

### 维度 3：可维护性 — ✅ 通过

- 表驱动泛化：per-chain subject/body/do_not_stage 三表 keyed by chain_id，closed registry + fallback——新增链零散点修改（P-v5 泛化性合规）。
- 单一来源纪律：序列化器单源（verify_workflow.py L23308-23315 委托 `write_guard_state.state_json_text`）、锁单源、resume 三分支单源（write_guard_state.py L745-782）——FIX-383 全部复用未复制。
- 注释质量：模块 docstring（L108-121）、链 docstring（L656-663）、verify_workflow 新段注释（L23847-23859）、CLI help（L25729-25748）、TOOLS.md TOOL-057 注记五处口径互相一致（converge 只写自身工件 / check-only 零写入零消费 / exit 0/1）。

### 维度 4：性能 — ✅ 通过

- probe 120s 超时（closure_chain.py L887）对 `--check-only` 冷启动（导入 + 两面只读对账，秒级）充裕；converge 双遍对账 O(受管面) 无 N+1；`import write_guard_state` deferred（L23907）与全仓 heavy-module 惯例一致。

### 维度 2 之外的补充：测试覆盖（维度 5）— ✅ 通过

见 §2.5 判别力分析 + §6 复现记录：10 新全绿、39 基线零回归、关联套件 74P/25P 全绿、verify 全量 PASSED。

---

## 2. MUST 重点审查 8 项逐项结论

| # | 审查点 | 结论 | 关键证据 |
|---|---|---|---|
| 1 | 自举链设计正确性（前探针语义 + reconcile-vs-execute 世界一致性） | ✅ | §1 维度 1 六边界表；probe=--check-only 世界判定非日志；converge 双遍自洽；阻塞路径结构化拒绝 |
| 2 | 五检查完备性（三类中间态映射） | ✅（P3 级覆盖缺口 2 条，见 §4） | 基线未 regen→guard_state_current(+row_families_clean)；schema 变化→guard_state_current(state_issue)+violation_ledger_healthy（外来台账 schema 走 R6 人工——不可静默重建，方向正确）；行号漂移→ledger_no_drift；外加 pending_txn/R6/零足迹/台账不可读联动；无「漏检即静默通过」的中间态——未检出的中间态全部落入 FAIL 侧（fail-closed 方向正确） |
| 3 | 只读性证明 | ✅ | --check-only 路径三函数全读（_load_write_guard_state / _reconcile_row_families(persist_state=False) / load_ledger）；测试 `_snapshot_tree` 全树字节快照零写入断言；converge 写面=守卫三工件，faces 1-4 零写 |
| 4 | fail-closed 强度 | ✅ | R6 阻断+零写（字节断言）；不可判定态响亮（三检查联动 FAIL/面缺席 drift 登记非吸收）；unknown chain exit 2；结构面 FAIL 拒绝 |
| 5 | 10 测试判别力 | ✅ | 故障注入真实性：命名故障点（pre-step / post-step-effect 走 `_maybe_fault` handshake 机制 L1000-1021）+ 父控 `proc.kill()`（非 raise 等价类）；字节断言强度：state 文件前后 `read_bytes()` 相等 = guard 未重跑的直接证据 + `_snapshot_tree` 全树 + CAS 单调性；post-step kill 后断言 journal 无 step_completed（crash window 精确圈定） |
| 6 | 标准链兼容 | ✅ | summary 字节级不变测试断言 pre-FIX-383 完整字面量（本审查独立拼接核对等价）；unknown chain fallback 同文本；do_not_stage 扩展 assertNotIn（标准链）/assertIn（bootstrap 链）双向 |
| 7 | 锁面扩展四处披露合规 | ⚠️ 实质合规，形式瑕疵 1 项（P2-1） | 四个锁面外文件（verify_workflow.py / test_closure_chain.py / checks/version.py / TOOLS.md）的扩展在任务上下文、申报验证清单、TOOLS.md 注记、version.py 豁免注释中逐处披露（FIX-379「锁面外测试扩展审查裁定合规」同口径）；但 triage 记录 files 面失实——见 P2-1 |
| 8 | 验证复现 | ✅ | §6——四组数字全部独立复现，与申报逐一吻合 |

---

## 3. AI 代码专项 5 项检查

| # | 检查项 | 结论 | 证据 |
|---|---|---|---|
| 1 | mock 残留 | ✅ 无 | 新测试全部真实 subprocess（真实 verify_workflow CLI / 真实 closure_chain CLI），故障注入走 handshake 环境变量机制非 mock |
| 2 | 硬编码返回值 | ✅ 无 | 五检查全部基于文件实读判定；报告字段由实际对账产出 |
| 3 | 幻觉 API 调用 | ✅ 无 | 测试引用的 `wgs.SCHEMA_VERSION/TOOL_ID/GUARD_CLI_IDENTITY/CLI_CONSUMER`（write_guard_state.py L141/142/148/155）、`loop_event_log.check_cas_monotonicity`、`cc.new_closure_id/default_event_log_path` 均实存（套件 49P 实测）；`release/ledger.py` 不在调用面（仅 triage 预估失实，见 P2-1） |
| 4 | 未实现 TODO | ✅ 无 | diff 无 TODO/stub；「M-1~M-8 接线」为披露的后续票边界，非本票残桩（version-plan L88「时序可后置兑现」一致） |
| 5 | 过度实现 | ✅ 无 | 五检查与三类中间态+R6+pending_txn 映射紧密；无多余命令面/配置面；do_not_stage 仅按链扩展 |

---

## 4. 发现清单

### P2-1（治理记录准确性——非阻塞，建议本轮修正申报映射）｜ triage 记录 files 面失实

- **位置**：`.governance/change-triage/FIX-383.json` L8-11（`files` 字段）。
- **证据**：申报 files = `["skills/software-project-governance/infra/release/ledger.py", ".../closure_chain.py"]`；实测 `glob release/ledger.py` → **No files found**（该路径不存在），`git diff --stat` 实际修改面 = closure_chain.py / verify_workflow.py / test_closure_chain.py / checks/version.py / TOOLS.md（release/ledger.py 零改动、verify_workflow.py 等四文件未入账）。
- **影响**：triage 为机器记录，`release/ledger.py` 被永久记为 FIX-383 修改面而实际从未修改，后续追溯（conflict 分析/发布 manifest 对照）会命中失实条目；实现方向（release ledger 面 → write-guard 自举面）的演变未回写任何机器记录。
- **建议**：收口 EVD 的 artifacts 面如实记录五文件交付映射并注明 triage 预估演变（或在 M-2 门禁前以机录路径对 triage 记录做一次勘误注记）；不必改代码。
- **级别理由**：不影响代码运行与审查结论的实质正确性（权威审查范围以 Coordinator 派发清单为准，五文件均经本审查逐行覆盖），但构成可证伪的治理记录失实条目，M-2 门禁（量测/manifest 对照）前应修正。

### P3-1（测试覆盖缺口——低风险）｜ ledger_no_drift「登记面缺席」分支无直接故障注入

- **位置**：verify_workflow.py L23946-23953（`surface_index is None` → drift 登记）；测试 test_closure_chain.py `test_ledger_drift_detected_then_consumed_by_converge` 仅构造 `by_key`-miss（object_id 指向 EOF 外、面在场）。
- **证据/影响**：「family 不在 records_index」（面文件整体缺席或词域外 family）分支与 by_key-miss 分支在消费资格规则上同构（`eligible_open_violation_ids` L580-584：surface None → eligible），实现风险低；但 drift 判定文本与消费路径对该分支无直接回归钉。
- **建议**：FEAT-064（分族 BLOCK/词表演进）时补一条 family-absent fixture 一并覆盖。

### P3-2（覆盖归属澄清——非缺陷）｜ pending_txn 新测试仅覆盖三分支之一

- **位置**：test_closure_chain.py `test_pending_txn_resumed_by_chain_three_branch_world_judgment`——构造 `baseline_target` = 当前 state（world==target leg，finalize-only）。
- **证据**：world==previous（re-apply baseline）与 diverged（响亮披露不推进）两分支由既有 `test_triage_write_guard.py` L1710/L1757/L1797 看护（本审查实测该套件 74P）。
- **建议**：申报与 EVD 表述「三分支消费」应读作「机制承载三分支 + 新增纵切覆盖 target leg」，避免被读作新增三分支测试。

### P3-3（设计边界观察——建议接线票明确）｜ completed 幂等分支的 probe miss 不 gate

- **位置**：closure_chain.py L1464-1468——`step_state=="completed"` 直接 completed + note，probe 结果（可能 satisfied=false）仅入 `info["probe"]` 审计面，不 gate。
- **影响**：收敛完成后世界再发散（如人工直写治理记录）时重入会再次报 ready——发散不由自举路径承接，由 guard WARN 披露/FEAT-064 执法承接，属职责边界而非缺陷；probe miss 信号在报告 payload 中可见（审计不丢失），只是不阻断。
- **建议**：M-1~M-8 接线票中把「bookkeeping 完成后世界再发散」窗口的责任边界写明（或在 completed 分支对 probe miss 附加 note）。

### P3-4（文本打磨）｜ converge 后未收敛的拒绝 detail 未点名 row_families_clean 处置路径

- **位置**：verify_workflow.py `run_release_bootstrap_converge` 后置分支 detail（「基线写入让行/失败时复跑收敛即可续推；R6 损坏台账按规则人工处置；发散事务按三分支第三分支响亮披露」）——未列 `row_families_clean` 的「写入器补凭证后收敛运行」路径（该文本只在 checks[].detail 中）。
- **影响**：信息仍可达（`not_converged` id 列表 + 各 check 自带处置文本），纯可读性打磨。

---

## 5. Developer 边缘披露四条评估

| # | 披露 | 评估 |
|---|---|---|
| 1 | 保守面（未做的泛化不冒进） | 认可——closed registry/fallback 均为最小改动面 |
| 2 | 窗口丢失语义留 FEAT-064 | 与 version-plan L88「时序可后置兑现」及 FEAT-057 WARN posture（0.86.0 既定）一致；converged ≠ 零 open 违规的语义边界（open 记录持久响亮、由台账承载而非吸收）与 FEAT-057/060 契约吻合，非静默吸收 |
| 3 | WARN 姿态吸收 | 同上——`open_violations` 字段在 converged 报告中照常输出，未隐藏 |
| 4 | M-1~M-8 接线时机建议 | 本票交付自举能力不接线发布链——TOOLS.md「被以下子工作流使用…发布」注记与 version-plan B2 范围一致，披露充分、无隐瞒 |

---

## 6. 验证复现记录（独立实测，非转述申报）

| 声明 | 复现命令 | 结果 |
|---|---|---|
| 49P（39 基线+10 新） | `python -m pytest skills/software-project-governance/infra/tests/test_closure_chain.py -q` | **49 passed** in 56.15s ✓（10 新 = ReleaseBootstrapTests 恰 10 方法逐一核对） |
| 74P | `python -m pytest .../test_triage_write_guard.py -q` | **74 passed** in 1.18s ✓（含 FEAT-060 三分支 resume 既有覆盖） |
| 25P | `python -m pytest .../test_static_version_pins.py -q` | **25 passed** in 1.84s ✓（version.py 豁免重锚 83→86 与豁免表自洽；0.86.0 token 实读位于 test_closure_chain.py L86 `_TRACKER_ROW`） |
| verify | `python skills/software-project-governance/infra/verify_workflow.py` | **== Verification Result: PASSED ==**（exit 0）✓ |
| diff 范围 | `git status --porcelain` / `git diff --stat` | 5 M 文件 +796/−15，与申报一致 ✓ |
| static-pin 漂移量 | diff 逐行 | +3 行（`import hashlib` / `import write_guard_state` / `VW_PATH = ...`）→ 83→86 重锚量精确 ✓ |

---

## 7. 总结论

- **结论：APPROVED_WITH_NOTES**
- **unresolved_blockers = 0**（无未解决 BLOCKING finding；P0=0、P1=0）
- 遗留项（不阻塞合并）：P2-1（triage files 面失实——建议 M-2 门禁前机录勘正）+ P3×4（覆盖缺口/归属澄清/设计边界注记/文本打磨，均建议随 FEAT-064 或 M-1~M-8 接线票吸收）。
- 审查性质声明：本 APPROVED_WITH_NOTES 表示代码审查硬门槛（P0=0、五维度全覆盖、AI 专项 5 项、设计一致性）通过，不替代测试审查、发布审查或 M-2 量测门禁。
