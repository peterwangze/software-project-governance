# Review FEAT-060 · CODE · R0 —— write-guard 违规持久状态机 + hook 消费权台账（0.88.0 阶段 B1 · WARN 姿态落地）

> 审查人: Code Reviewer Agent（独立，只读）· 轮次: R0 · 日期: 2026-09-25
> 审查对象（工作树未提交 5 文件，4 改 1 增）: `infra/write_guard_state.py`（新增，811 行——状态机实体）+ `infra/verify_workflow.py`（numstat 实测 +164/−36 = 净 +128——face 5 薄接线）+ `infra/tests/test_triage_write_guard.py`（+753，24 新测试，类 :1273-2004）+ `infra/TOOLS.md`（TOOL-057 同步）+ `infra/checks/version.py`（static-pin 台账 re-audit，行移位 992→995 / 1138→1141）
> 语义基准: version-plan-0.88.0 §2 阶段 B1（六规则 + 12 规范字段 + ops 可恢复事务逐字对照）+ DEC-224（双约束绑定「BLOCK 升级时」——原文已调阅）+ arch Q2 + RISK-039 thin-entry 纪律 + FIX-292 单序列化器教训 + FIX-379 私有引用先例
> 审查方法: 逐行读 diff 与两处全文（write_guard_state.py 811 行全读 + verify_workflow face-5 区域全读）；实测优先——测试四轮独立复跑、活体台账现态读取、活体只读 probe、HEAD 算术归因预存红；全程零 `.governance` 写入（probe 前后字节恒等实测）

---

## 1. 总结论

## **APPROVED_WITH_NOTES**（P0=0 · P1=1 · P2=3 · P3=6 · **unresolved_blockers=0**）

5 维度逐项有结论（§3）· AI 专项 5 项全过（§5）· 设计一致性 9 焦点 9 符合（§2）· 独立复验 7/7 通过（§4）。六规则与 DEC-224/version-plan B1 逐字对照全部落地且各含红绿测试；12 规范字段全数在场（活体记录逐字段核对）；消费权闭集 + 单次燃尽 + 伪造/无权拒绝两腿实证；ops 可恢复事务三段原子性 + resume 世界判定三分支（含 diverged 拒推进 fail-closed）经崩溃注入实测；活体首捕→消费闭环在真实台账现态复核成立；活体 probe 零写入字节级实测成立。

**P1-1（不阻塞，建议本轮顺手修复）**：plain-advance 基线写路径（verify_workflow.py:23617）不参与状态机消费事务所用的 `_TargetLock` 锁纪律——并发 guard CLI 运行下，一次无锁 plain 写与在途事务交错时，因 `next_state.updated_at` 时间戳保证两次运行字节必然不同，resume 世界判定会被推入 diverged → manual-intervention 分支（fail-closed、不损坏治理记录，但产生可避免的人工恢复负担）。修复面约 3 行。依据 skill 关闭规则「P0=0 且 P1>0（有遗留计划）→ 有条件合并」，本报告以 APPROVED_WITH_NOTES 通过并登记遗留项（§8）；若 Developer/Coordinator 判定随本轮收尾修复（推荐，成本极低），修复后无需重审（修复面不触及本报告其余结论）。

---

## 2. 设计一致性（九焦点逐项裁定）

| # | 焦点 | 裁定 | 事实依据 |
|---|------|------|---------|
| ① | 12 字段 schema 完整性 | **符合** | version-plan B1 十二字段逐一在场：`_record_violation` write_guard_state.py:368-401（violation_id/family/object_id/before_hash/after_hash/workflow_run_id/hook_identity/first_seen/occurrence/status/grant_id/consumption_event）+ 寻址联合字段（type/family_kind/file/line/snapshot/session_id/last_session_id/last_seen/escalated/escalated_at/notes）。活体记录 WV-62097f（`.write-guard-violations.json`:15-45）逐字段核对一致。测试 `test_cli_records_violation_with_unchanged_warn_output`（:1860-1891）对 12 键逐一 `assertIn` 钉住 |
| ② | R1 观测≠接受 | **符合** | 记录即 `open`（:385），唯一终态迁移点 = `_finalize_txn` 消费事务内（:548）与 supersede 链（:417）；基线路径对违规状态零接触。红绿：test_rule1_observation_is_not_acceptance（:1336）/ not_duplicated（:1349，纯去重 `changed=False` 零改写）/ independent_trigger_supersedes（:1363，occurrence+before_hash 审计链） |
| ③ | R2 WARN 不改基线（口径决策） | **符合（披露充分）** | 字面「WARN 不前移对账基线」与 DEC-224 钉住的 WARN 姿态（吸收窗口）存在字面张力——模块 docstring :38-49 明示口径：机制面 = 基线写入对违规状态零权力 + 消费事务是基线与台账唯一同动点；字面规则随 FEAT-064 BLOCK 翻转。test_rule2（:1385-1396）钉住「基线写入后台账字节恒等 + 记录保持 open」。**裁定：该口径决策成立**——若按字面实现（WARN 不吸收窗口）反而破坏 DEC-224 (a) 款钉住的现行 WARN 语义（响亮披露 exit 0 不阻断）；披露面完整（docstring/TOOLS.md/测试类 docstring 三处） |
| ④ | R3 同会话升级 | **符合（留一处语义余量，P2-2）** | `GOVERNANCE_SESSION_ID` 注入（verify_workflow.py:23603-23604）；未注入保守不升（`session_id is not None` 门，:406-408）——宁可漏升不可误升，docstring :50-56 披露。红绿：同会话升（:1400）/ 跨会话不升（:1415）/ 无身份不升（:1429）+ CLI env 接线测试（:1951-1989）。余量：判据为「与前一条记录连续同会话」（last_session_id 单步比较）——A-B-A 会话序（x→y→x）不升，详见 P2-2 |
| ⑤ | R4 跨会话保留 | **符合** | 台账文件态独立于进程/会话；test_rule4_violations_persist_across_sessions（:1443，完整状态机步进后 open + first_seen 不变）/ test_rule4_open_records_survive_state_baseline_rebuild（:1462，基线文件删除重建后未决违规不丢——amnesty 不波及台账） |
| ⑥ | R5 消费权闭集 + 单次燃尽 | **符合** | `CONSUMER_REGISTRY` 闭集单消费者=guard CLI（:155-161）；grant 只能由注册消费者铸造（:460-466 未登记返回 `(None, False)`）；单次=事务烧毁（`_finalize_txn` :558-560 grant→used）。拒绝闭集实测：unknown_grant / forged_consumer（伪造两腿 :1529-1560）/ unregistered_consumer（:1563-1578）/ grant_used（:1507-1525）全绿且零残留断言在场。hook 不直接持权：post-commit Step 4b 经 `governance-write-guard` CLI 子命令调用（.git/hooks/post-commit 实文核对），状态机对 hook 不可直达 |
| ⑦ | ops 可恢复事务 + resume 三分支 | **符合** | journal 三段（:674-679 phase1 持久 journal → `_apply_baseline_and_finalize` :565-577 phase2 原子基线写（sha 相等跳写——幂等）→ `_finalize_txn` phase3 单次原子台账收尾）；resume 世界判定三分支（:706-723）：world==target→仅收尾 / world==prev→重放基线写+收尾 / **歧义→`violation_txn_diverged` 拒推进**（不吸收不前移不写违规——fail-closed 实测 :1691-1720）。崩溃注入×2 实测通过（相界异常 :1603-1650 + journal 重放 :1652-1690）。私有引用 `_TargetLock`/`_atomic_write_bytes`（governance_store.py:19639/17671 实文核对——O_EXCL 锁文件+同目录 temp+fsync+os.replace）与 FIX-379 先例合理性成立：锁目录 `.governance/.governance-store-locks/` 即 governance_store 既有维护面，docstring :94-99 披露在案 |
| ⑧ | WARN 姿态零变化 + probe 零写入 | **符合** | 输出面：diff 未触及 `unattributed_row_change` issue 构造（_judge_row_delta :23380-23389 原样）；face 状态硬编码 PASS（:23291 WARN posture）；检测追加点在 issue 构造之前、不改变判定（:23364-23370 仅追加 detections_out）。接线隔离：`detections/records_index` 仅 `persist_state=True` 时分配（:23589-23590），probe 传 None（docstring :23156-23162）。夹具钉住：stdout 零 `violation`/`ledger` 字样（:1893-1906）；活体实测：probe 前后台账+基线字节恒等、face PASS 0 issue。调用方 grep 核实：生产代码仅 `cmd_governance_write_guard`（:23775）传 persist_state=True |
| ⑨ | 台账同步 + 薄入口纪律 | **符合** | TOOLS.md TOOL-057 摘要行+详情节与实现逐项对得上（12 字段/六规则/闭集/事务/单源序列化器/健康宿主零足迹/RISK-039+FIX-381 披露）；`state_json_text` 单序列化器委托（:23309-23316 → write_guard_state.py:204-212，与 FEAT-057 plain 写字节参数逐字一致 ensure_ascii=False/indent=2/sort_keys=+\n）+ test_state_serializer_is_single_source（:1993）钉住；version.py 台账行移位实测核符（995 行=`FEAT-057` 夹具行文本、1141 行=`assertIn("WARN 姿态 0.86.0"...)`，+3 = os/threading/wgs 三条 import）；引擎净增 +128 且状态机实体外置新模块——RISK-039 薄入口方向正确（但见 P2-3 棘轮注记） |

---

## 3. 五维度审查结论

| 维度 | 结论 | 要点 |
|------|------|------|
| 正确性 | ⚠️ | 状态机核心逻辑逐行核对无误（去重/supersede 链/授权闭集/事务三段/resume 三分支/TOCTOU 再校验——consume 在锁内对每个 vid 重验 open :644-656，eligible 计算的无锁读由锁内重验兜底）；并发纪律有一处缺口（P1-1）+ 两处语义余量（P2-1/P2-2） |
| 安全性 | ✅ | 零 shell/零 eval/零注入面；消费权闭集 + 伪造两腿 + 未登记拒绝实测；R6 损坏不吸收 fail-closed（零写入字节级断言 :1763-1778）；原子写 fsync+os.replace 单源；台账/基线均守卫自身工件，治理记录零触碰契约不变 |
| 可维护性 | ✅ | 模块 docstring 六规则映射+已知边界+私有引用理由完整；薄接线面（face 5 仅 +157 行差额中的接线与注释，逻辑均在实体模块）；命名一致；consume_violations(~104 行)/reconcile_violation_state(~82 行) 超 50 行指引但内聚（拒绝梯/步进编排），P3-5 注记 |
| 性能 | ✅ | 台账线性扫描（违规量级=治理行族违规，小）；SHA 快路径沿用；锁超时 10s；活体 probe 毫秒级；无 N+1 |
| 测试覆盖 | ✅ | 24 新测试覆盖全部验收映射（重复/并发/消费后崩溃/基线写崩/会话重启/伪造 hook/无权 hook + ops 事务性——plan-tracker 验收行七要素逐一有测试）；崩溃注入为真实异常注入（mock 计数器定位相界）非跳过；缺口为补强项非核心路径（P3-4） |

---

## 4. 独立复验（7/7 通过——Reviewer 本机实跑，全程零 .governance 写入）

| # | 项目 | 命令/方法 | 结果 |
|---|------|----------|------|
| 1 | 目标套件 71P | `python -m pytest tests/test_triage_write_guard.py -q` | **71 passed in 0.86s**——24 新测试全绿，与申报一致 |
| 2 | 全量 infra 申报 | `python -m pytest tests -q`（后台 19:51 实跑） | **3911 passed, 3 failed, 1 skipped, 517 subtests passed**——3F 全部 archguard 棘轮（§6 P2-3 归因）。与申报「3909P/5F（2 已修+3 预存棘轮）」**精确调和**：3909+2 已修=3911P、5−2=3F ✓ |
| 3 | verify 全量 | `python verify_workflow.py verify` | **PASSED, exit 0** ✓（申报核实） |
| 4 | 活体首捕→消费闭环 | 读 `.governance/.write-guard-violations.json` 现态 | **WV-62097f63cc8f2be6e400c96b09feffb3 status=consumed**，consumption_event 完整（txn-1b3e48d3…/grant-08caca1c…/baseline_updated=true），grant status=used，pending_txn=null——申报闭环（23:40:07 捕获 → 00:26:51 消费）现态成立 |
| 5 | 活体 probe 零写入 + WARN 姿态 | `check_governance_write_shapes(persist_state=False)` 前后台账+基线字节比对 | **两工件字节恒等（零写入）+ face 5 PASS / 0 issue**——probe 路径零写入与活体健康态独立证实 |
| 6 | 预存红归因（R1） | `git show HEAD` 引擎行数 vs anchor 算术 | **HEAD 引擎 25,569 行 > anchor 25,462（+107）→ test_r1 在 HEAD 即红（预存实锤）**；工作树 25,697（+235）为本 diff 加深。R7/CLI-gate 两失败与 R1 同根（「engine changed without regen」，CLI 输出实录）；version-plan §3.4 预注册「archguard 棘轮席 3 ERROR——M-1R 门禁摘要显式列」与本实测失败数吻合 |
| 7 | 凭证/序列化/移位台账 | `_credential_index`→`_row_family_credential_ok` 复用核对 + `state_json_text` 字节参数比对 + version.py 移位行内容核对 | 三者均符（§2 焦点⑧⑨）——零第二判据源、零第二序列化器、移位行 token 逐字匹配 |

**标注为 claimed（未独立复验，如实说明）**：①「stash 实证」——stash 为破坏性工作树操作，审查纪律禁止；以 HEAD 算术归因（复验 6）+ 终态调和（复验 2）替代，结论一致。②「活体 CLI stdout 字节级 BYTE-IDENTICAL」——跨版本全 stdout 字节 diff 同样需要 stash；以结构性验证（diff 零 stdout 新增路径 + face-5 issue 构造未触碰）+ 夹具钉住（:1893-1906）+ 活体 probe 0 issue 替代。③「邻接 8 套件 429P / test_verify 933P」逐套件分解——全量复跑已覆盖（3911 总量一致），未做逐套件重跑（非阻断）。

---

## 5. AI 代码专项（5 项全过）

| 项 | 结论 | 证据 |
|----|------|------|
| mock 残留 | ✅ 零 | 生产模块零 mock；测试 mock 全为声明式用途（崩溃注入相界定位 :1614-1621/:1658-1665、env 隔离 :1955、夹具重定向），逐处有明确注释与恢复 |
| 硬编码返回值 | ✅ 零 | 拒绝词表（unregistered_consumer/unknown_grant/grant_used/forged_consumer/unknown_violation/not_open/pending_transaction/ledger_corrupt/schema_violation）全部挂在真实控制流上；无 stub 路径 |
| 幻觉 API | ✅ 零 | 逐符号核实：`_TargetLock(target, timeout)`/`_atomic_write_bytes(path, data)`（governance_store.py 实文，签名匹配）；`_row_family_credential_ok(surface, key, text)`（verify_workflow.py:23087）；`build_detection` 8 参全对位；`STATUS_CELL_OP_SUFFIX_PATTERN`/`REVIEW_MACHINE_ROW_MARKER` 等消费面均为既有 import |
| 未实现 TODO | ✅ 零 | 新模块 grep TODO/FIXME/XXX/HACK/NotImplemented 零命中；v1 边界（行号键控位移/台账增长/新违规类型）为 docstring :83-92 显式披露的延后切片，非存根 |
| 过度实现 | ✅ 无 | 范围=B1 声明；BLOCK 激活/pruning/新违规类型均未提前实现（正确留 FEAT-064/后切片）；`INVOKER_ENV` 覆写为 4 行文档化前向兼容钩子，未越界 |

---

## 6. Findings

### P0（阻塞）——无

### P1（关键——建议本轮修复；不阻塞合并，遗留计划见 §8）

- **P1-1 plain-advance 基线写不参与 `_TargetLock` 锁纪律——并发 CLI 运行可把在途消费事务推进 diverged（manual-intervention）分支** · `verify_workflow.py:23617`（`state_path.write_text(...)` 无锁）× `write_guard_state.py:611/697`（事务/resume 均 `_TargetLock(state_path)` 在案）
  事实：消费事务与 resume 对状态基线文件持 `_TargetLock`，而 WARN 姿态 plain 推进路径对同一文件裸 `write_text`（FEAT-057 既有形态原样保留）。`_TargetLock` 为协作式 O_EXCL 锁——不检查即不互斥。叠加 `next_state.updated_at` 每次运行刷新（verify_workflow.py:23296），任何两次运行的 next_state **字节必然不同**（即便语义内容全同），因此交错后果不是「写同字节无害」而是确定性 sha 分歧：run B 的 plain 写落在 run A 的 phase-1 journal 之后 → A 崩溃或下一轮 resume 时 world 既非事务目标也非事务前像 → `violation_txn_diverged` → manual-intervention。
  影响：**无治理记录损坏、无双重消费（授权在台账锁内烧毁）、fail-closed 姿态正确**——但产生本可避免的人工恢复负担（R6 纪律恰恰不鼓励手工编辑守卫工件），且 FEAT-064 BLOCK 激活后该窗口后果升级。触发概率低（需两次 guard CLI 运行重叠于秒级窗口——hook 提交与手工复跑并发场景现实存在）。
  修复建议（~3 行）：plain 推进包同一把锁——`from governance_store import _TargetLock`（或经 write_guard_state 再导出）后 `with _TargetLock(state_path): state_path.write_text(...)`；锁序与事务一致（state 单锁，无嵌套死锁面）。补一条并发 plain-advance × pending-txn 测试。

### P2（建议——可遗留，不阻塞；FEAT-064 前应处置 ①②）

- **P2-1 消费收尾覆写 `hook_identity`——观测侧溯源丢失** · `write_guard_state.py:549`
  事实：`_finalize_txn` 执行 `record["hook_identity"] = txn["consumer"]`，把检测侧身份（docstring :143-146 定义「which command observed the violation」）覆写为消费方身份；消费方身份已由 `consumption_event.consumer`（:553）承载，覆写纯冗余且破坏溯源。当前闭集下两者恒同为 `governance-write-guard/cli`（活体记录实证同值），故为零现值损害；但 `INVOKER_ENV`（:148，文档化的未来覆写钩子）一旦启用即静默丢失原观测者。
  建议：删除该赋值行；补一条「hook 检测记录消费后 hook_identity 不变」钉住测试。
- **P2-2 R3 升级判据为「连续同会话」——A-B-A 会话序漏升** · `write_guard_state.py:406-408`
  事实：`same_session = session_id == existing.last_session_id` 仅比较紧邻前代。会话序 x→y→x 中，会话 x 第二次独立触发（第 1、3 次）因前代属 y 而不升级；按 B1 字面「同会话同违规第二次独立触发升级」该序应升。现有三测试未覆盖 A-B-A 序。
  影响：FEAT-060 内 escalated 仅标记无行为后果；FEAT-064 将 escalated 接线 BLOCK——届时该语义缺口从标记问题升级为执法判定问题。
  建议：FEAT-064 设计期定案二选一——(a) 按会话累计触发次数（记录内增 session 触发计数或维护 session→first_seen 集合）；(b) 在 version-plan/TOOLS 显式钉住「连续同会话」语义并补 A-B-A 负例测试。当前实现保守（漏升不误升），R0 不构成缺陷。
- **P2-3 引擎净增 +128 行对 only-down R1 棘轮（预存红加深 +107→+235）** · numstat 实测 +164/−36；`core/architecture-baseline.json` r1 anchor 25,462；HEAD 已红实锤（§4 复验 6）
  事实：R1 棘轮规则「only-down；shrink the engine or regen after a sanctioned shrink」——本 diff 在已红状态下继续增长。R7（baseline-stale）与 CLI-gate 两个失败同根；三失败即 version-plan §3.4 预注册的「archguard 棘轮席 3 ERROR——M-1R 门禁摘要显式列」。
  影响：零新增红（全部预存）；债务加深且 M-1R 前无法经 regen 消解（增长不合法 regen）。
  建议：M-1R 席位显式列 3 ERROR 时注明 FEAT-060 加深量（+128）；后续接线类任务优先压缩引擎注释重复面（本 diff 引擎侧六规则叙事与模块 docstring 存在重复，可下沉引用）。

### P3（讨论/建议）

1. **`_validate_ledger` 仅校验 status 字段，12 字段 schema 未强制** · write_guard_state.py:243-279——缺字段的手工编辑台账可通过校验进入消费路径（下游 `.get()` 均有缺省，无崩溃面）。建议后续切片把 `_VIOLATION_STATUSES` 校验升级为必填键集校验（含 grants/pending_txn 键型），与「规范字段」声明对齐。
2. **plan-tracker FEAT-060 行文「11 字段」vs 实现/TOOLS/version-plan 一致口径「12 字段」** · `.governance/plan-tracker.md` FEAT-060 行——文档口径漂移（version-plan B1 逐项点数=12）。建议经 task_row_update 机录路径勘正（手工编辑会触发本守卫 WARN——dogfood 闭环）。
3. **申报口径差：任务书「verify_workflow.py 净 +157」vs numstat 实测 +164/−36 = 净 +128** · 接线判断零影响；后续申报以 numstat 为口径。
4. **测试补强建议**：①`pending_transaction` 拒绝路径（journal 在场时新 consume 被拒）无直接测试；②并发 consume 事务（双 CLI 同时到消费步）仅并发记录有测试；③P2-1 对应的 hook_identity 消费后钉住；④`next_state=None`（受管面全体缺席）时 pending txn 搁浅的理论边界（现网不可达——surfaces_seen 恒真）。
5. **`consume_violations`（~104 行）/`reconcile_violation_state`（~82 行）超 50 行函数指引** · 内聚性良好（拒绝梯/步进编排），仅记录风格注记，无需拆分。
6. **evidence-log 尚无 FEAT-060 实现 EVD**（检索仅 1 条 TRIAGE 行，4 次命中为同行内字符串重复）——收工补证据属 Coordinator 收尾步骤，此处仅流程注记；本报告 §4 复验 1-3 已独立实证测试与 verify 申报。

---

## 7. Developer 申报边缘 · 8 项裁定

| # | 申报 | 裁定 |
|---|------|------|
| 1 | 六规则各专属红绿（R1~R6 列举） | **核实**。24 测试逐条对号（§2 焦点②~⑥ + §3）；红相=违反规则实现必挂的负断言（去重 changed=False/granted 二次消费拒/伪造两腿/diverged 拒推进/零写入字节比对） |
| 2 | 事务崩溃注入×2（相界异常+journal 重放） | **核实**。mock 计数器精确定位相界（call 2=基线写 / call 2=finalize），残留=仅 journal 断言 + resume 三分支各得其所（§2 焦点⑦） |
| 3 | 活体 CLI stdout 字节级 BYTE-IDENTICAL | **结构性核实（跨版本字节 diff 未做——需 stash，破坏性）**。diff 零 stdout 新增路径 + face-5 issue 构造未触碰 + 夹具钉住 stdout 无 violation/ledger 字样 + 活体 probe PASS 0 issue（§4 标注③） |
| 4 | 71/71 + 邻接 429P + test_verify 933P | **总量核实**（3911P 全量覆盖）；逐套件分解未重跑（非阻断） |
| 5 | 全量 3909P/5F（2 已修+3 预存棘轮 stash 实证） | **精确调和**：实测 3911P/3F——3909+2=3911、5−2=3；3F 全 archguard 预存（R1 HEAD 算术实锤 +107，R7/CLI 同根；version-plan §3.4 预注册 3 ERROR 吻合）。stash 复现未执行（破坏性），以算术归因替代，结论一致 |
| 6 | 活体首捕 WV-62097f → Coordinator 补凭证 → 复跑自动消费闭环 | **核实**。台账现态 consumed + grant used + pending null（§4 复验 4）；时间线（23:40 捕获→00:26 消费）与 grant issued_at/updated_at 互洽 |
| 7 | 执行包 18d~18i 已由 Coordinator 填充 | **核实（Check 18d~18i = FIX-088~093 执行包完整性检查项，非包内字段字面量）**；verify 全量 PASSED（复验 3）内联该族检查。包头 product_success_contract 仍见 TO_BE_DEFINED 占位文本——属 Coordinator 记账面，不影响代码审查结论，提请知悉 |
| 8 | WARN 姿态落地为「0.89 BLOCK 前置基座」（任务书措辞） | **口径核实**：version-plan 0.88.0 阶段 D 即 FEAT-064（BLOCK 激活在本版内）；模块/TOOLS 均写 0.88→FEAT-064。任务书「0.89」为措辞偏差，无代码影响 |

---

## 8. 遗留项与复审指引

| 遗留项 | 级别 | 关闭目标 | 建议 |
|--------|------|---------|------|
| P1-1 plain 推进锁纪律 | P1 | 本轮收尾顺手修（推荐，~3 行）或 FEAT-064 第一提交前 | 修复后无需重审（不触及本报告其余结论）；若选择 FEAT-064 前修，随其 BLOCK 前置检查单闭合 |
| P2-1 hook_identity 覆写 | P2 | FEAT-064 前 | 一行删除 + 钉住测试 |
| P2-2 A-B-A 升级语义 | P2 | FEAT-064 设计期定案 | (a) 会话累计计数或 (b) 语义显式钉住 |
| P2-3 棘轮 3 ERROR | P2 | M-1R 席位列出（既有安排） | 注明 FEAT-060 加深 +128 |
| P3-1~P3-6 | P3 | 后续切片/收工 | 见 §6 |

**复审指引（R1 若因 P1-1 本轮修复而触发）**：逐条核对 §6 P1-1（锁包裹 + 并发测试新增）；确认修复未改动 resume 三分支与拒绝词表；复跑 test_triage_write_guard（预期 72P：71+1 并发新增）与全量（预期 3912P/3F——3F 为既列 M-1R 棘轮债务，非本任务面）。

**硬门槛裁决**：P0=0 ✓ · 5 维度全覆盖 ✓ · 发现全标注 ✓ · 设计一致性（DEC-224/version-plan B1 对照）✓ · AI 专项 5 项 ✓ → **APPROVED_WITH_NOTES**（unresolved_blockers=0）。

---

*Review 证据：本报告全部实测命令于 2026-09-25 在工作树 D:\AI\agent\claude\coding\project_management_workflow 执行；全程未 stash、未运行 persist_state=True 路径、`.governance` 零写入（复验 5 字节级证明）。*
