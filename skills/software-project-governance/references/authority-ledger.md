# 权威账本与身份契约（FEAT-093）

> schema 锚：`authority-ledger/1`（`infra/authority_ledger.py` 常量 `LEDGER_SCHEMA`）
> 需求源：RPG 长程 session 实测同 ID 双语义 ×5 组 / 22 行僵尸「未开始」/ 计划执行双轨零对账（分析报告 §3.2；DEC-330 拆票，本票为 0.98「可信有界执行内核」首票）。
> FEAT-094 审查可信链扩展见文末「审查可信链（FEAT-094）」节。

## 定位

治理核心状态（任务身份与状态 / 审查结论 / 复审义务 / goal 预算）的**单一权威账本**：JSONL 追加事件日志 + 可重建快照（`.governance/authority-ledger/`），事务写入器（含审计日志）；plan-tracker 主表与 Gate 摘要降级为**可重建投影**。本票不做 FEAT-094 审查可信绑定 / FEAT-095 动作级执法 / FEAT-096 执行隔离（另票边界）。

## 物理载体（execution-packet assumption_record 约束）

| 文件 | 角色 |
|------|------|
| `.governance/authority-ledger/events.jsonl` | 追加事件日志（一行一事件；seq 单调 + sha256 哈希链；撕裂尾检测 fail-closed） |
| `.governance/authority-ledger/snapshot.json` | 可重建快照（投影缓存，从事件折叠派生，绝非第二事实源） |

不引入外部数据库依赖。

## 事件 schema（grep 锚：`EVENT_KINDS` / `REQUIRED_FIELDS`）

每个事件行：`seq` / `event_id`（`evt-`+32hex）/ `kind` / `transaction_id` / `actor` / `timestamp` / `payload` / `prev_hash` / `hash`。

`kind` 闭合词汇表（`EVENT_KINDS`）：

- 任务核心状态：`task_registered` / `task_state_changed` / `task_superseded`
- 审查/复审义务/goal 预算（schema 面；深度绑定=FEAT-094）：`review_recorded` / `recheck_obligation_registered` / `recheck_obligation_cleared` / `goal_budget_recorded`
- Gate/风险热区：`gate_recorded` / `gate_state_changed` / `risk_recorded` / `risk_state_changed`
- 审计：`historical_identity_conflict`（迁移期历史双语义，flagged 保留）/ `identity_conflict_rejected`（写入侧拒绝，尝试留痕）/ `historical_migrated`（迁移批次汇总）/ `projection_rebuilt`（重建结果汇总）

## 身份契约（写入侧执法）

- **语义锚**（`semantic_anchor`）：任务行 `事项` 单元格首个 `**粗体**` 声明标题（无粗体时取首个 `——`/`：`/`；` 前导子句，截 120 字符）；指纹 = `anchor_fingerprint`（sha256，空白不敏感）。状态装饰、追加叙述、provenance 后缀**不**改锚——这些演化合法；换锚 = 换语义。口径假设：首个粗体段即声明标题（现行 plan-tracker 表格式使其成立；标题前另起粗体段的畸形格会取错锚——表格式约定属防退化看护面）。
- **同 ID 双语义写入被拒**：已注册 ID 再次以不同锚注册 → 拒绝（`identity_conflict`）+ 追加 `identity_conflict_rejected` 审计事件；拒绝事务不落任何业务事件。禁原 ID 静默换义。**批内同样适用（R0 P1-1）**：`transact` 对整批做模拟折叠校验——同批同 ID 双锚 → 整批拒绝 + 审计事件（批内后序事件对同批先序事件可见）；批内 `task_superseded` 的 new-id 唯一性同口径校验。
- **改语义唯一正道**：`task_superseded`——新任务 ID（或版本化 ID）+ 替代关系记录（`old_task_id`/`new_task_id`/`reason`/`mode`）；`old_task_id` 必须已注册（幻影替代拒绝：`unknown_task_id`——身份血统完整性）；旧 ID 身份此后永久冻结（仍拒换义）。
- **未知身份拒绝（R0 P2-1/P2-2）**：未注册 id 的 `task_state_changed` 在写入面被拒（结构化 `unknown_task_id`）——不再接受后遭折叠静默丢弃（孤儿事件类归零）；raw `transact` 面同口径执法，无绕过面。
- **事务语义**：批内事件全部先验证（闭合 kind + 必填字段 + 身份契约——含批内模拟折叠）再一次性顺序追加（validation atomicity + 单次写入 + fsync）；快照原子刷新。

## 投影与零丢失

- **迁移**（`migrate`，dry-run 默认先行）：解析 plan-tracker 热区（任务表=`优先级|ID` 表头族；Gate 表=`## Gate 状态跟踪` 节；风险表=risk-log `编号|当前状态` 表头族）→ 逐行注册（首个锚注册；同锚重复行计 duplicate；历史双语义行 flagged 保留）→ 迁移前后**任务/Gate/风险计数逐项一致**（facet 词汇：`tasks.rows/distinct_ids/id_set`、`gates.rows/passed/pending/failed/other`、`risks.rows/open/closed/unknown`）。重跑幂等。dry-run 演练以 live 事件日志副本播种（再迁移的 dry-run 同样预测 live 计数，R0 P3-3）；源行不可注册（如空锚行）→ 结构化 `FAIL`（`schema_violation_row`，无堆栈回溯；逐行幂等可续跑，R0 P3-5）。
- **重建**（`rebuild-projection`）：从账本折叠态重建热区投影 + 计数对照；`--write` 物化快照并追加 `projection_rebuilt` 审计事件；drift 面（`ledger_only`/`table_only`/`status_mismatch`）为读切换前置披露，**不**自动改写叙事行。
- **解析口径单源**：表扫描/分桶复用 `bootstrap_aggregate` 的 live 实现（函数内导入，反漂移；R0 P0-1 教训）。

## 渐进开关（写路径先双写，后读切换）

`GOVERNANCE_AUTHORITY_LEDGER` 环境变量 > plan-tracker `## 项目配置` **节内**的 `authority_ledger` 键（仅该节内生效——Gate 解析同款节作用域，节外同形行不翻转开关，R0 P3-6）> 默认 **off**。on 词表：`1/true/yes/on/projection`；off 词表：`0/false/no/off/legacy`；非法值由所见臂即显式报 `invalid` 返回（不咨询下一臂），`switch_enabled` 将 `invalid` 投影为 off（fail-closed 方向，绝不猜）。默认 off = **行写入文件逐字节不变**（CLI stdout 成功路径的 JSON 载荷仍含加性披露键 `authority_ledger: {"status":"off"}`——已披露的加性漂移，机器消费方对照字节级快照时以此口径为准，R0 P3-2）。

- **双写钩子**：`task_row_update` CLI 提交成功后镜像 `task_state_changed` 事件（payload face `authority_ledger` 字段披露结果；镜像失败不回滚已提交行、不吞错——由 migrate/rebuild 对账收口）。采用顺序（先 `migrate --write` 播种，再开双写）由写入器执法：未注册 id 的镜像事件被拒（`unknown_task_id`，披露于载荷）——孤儿事件类归零。
- 已注册任务的行翻转经折叠同步状态桶（`to_bucket`；终态 `completed`/`committed` 与 ✅ 标记同桶——STATE_CANONICAL_MARKERS 同族）。

## CLI

```
python <plugin_home>/infra/verify_workflow.py authority-ledger status   [--governance-dir D]
python <plugin_home>/infra/verify_workflow.py authority-ledger migrate  [--dry-run|--write]
python <plugin_home>/infra/verify_workflow.py authority-ledger rebuild  [--write]
```

退出码：0 正常/PASS；1 FAIL（计数不平衡/完整性破损/源行不可注册 `schema_violation_row`）；status 面只读（开关态/完整性/计数/快照新鲜度）。

## 回滚

`git revert` 单票 commit；开关关闭即回直写路径；账本事件日志为新增产物，随回滚移除或按 EVD 行说明保留。

## 审查可信链（FEAT-094）

> 需求源：RPG session 三实证（REV-009 审查锚定幻影修订〔untracked+并发重写〕/ REV-001+002 两条 R2 义务机录声明后蒸发 / REV-009-R2 机录 APPROVED vs 报告原文 NEEDS_CHANGE，分析报告 §3.5）。写入器：`infra/review_record.py`（`write_review_record` 五步事务）。

**五步不可分割**（提交报告→验证结构与修订→登记发现→自动生成后续义务→更新状态）：`review_recorded` 事件与复审义务事件在**同一 `transact` 批**落账（validation atomicity + 单次顺序追加）；账本先提交、文件面（`review-{task}-R{n}.md` + evidence 行）后落，文件面中途失败对本事务新建的文件做补偿删除并披露已落账事务 id——不留半提交窗口。账本拒绝（撕裂尾/义务契约违反）→ 整笔事务拒绝，零写入（异常不隐藏）。

**① 不可变快照绑定 + 报告哈希**（record 内 grep 锚字段，additive、对 Check 30/30c 锚定解析器惰性）：

| 字段 | 语义 |
|------|------|
| `- report_sha256: <64hex>` | 被审报告**字节**哈希（重算可验证；报告在机录后被改写 ⇒ `verify_review_trust` 判 CONFLICT） |
| `- snapshot_commit: <40hex \| git:unavailable>` | 记录时被审仓库 HEAD（诚实披露，git 不可用不伪造） |
| `- snapshot_worktree: clean \| dirty(N) \| unavailable` | 记录时工作区洁净度披露（WIP 审查合法，仅披露绑定弱化） |
| `- snapshot_bind: <path>=<40hex>` | `git hash-object` blob 钉扎（CLI `--bind-file` 可重复；**untracked 安全**——REV-009 幻影修订类的机器检测面） |

evidence 行 artifacts 单元格携带短钉扎 `report_sha256=<12hex>; commit=<12hex|none>[; obligation=<id>]`（全哈希在 record）。复核 API：`review_record.verify_review_trust(review_file, repo_root)` → `CLEAN / CONFLICT / UNKNOWN / UNPINNED`（legacy 无钉记录=UNPINNED，**不**判 CONFLICT——兼容性设计；CONFLICT 处置=人工消解，禁乐观者胜出，禁改写 record 本身）。

**② R2 义务自动生成且唯一可消解**：NEEDS_CHANGE 机录 ⇒ 同批自动登记 `recheck_obligation_registered`（`obligation_id=RECHECK-{task}-R{n+1}`，携带 `prev_report`/`created_by`/报告哈希/commit）。义务键单源：`authority_ledger.obligation_key`（fold 与写入器共用）。写入器义务契约（`_check_batch_obligations`，整批模拟折叠口径，与身份契约同款姿势）：已 OPEN 键的重复登记 ⇒ 整批拒绝（唯一）；无 OPEN 键的清除 ⇒ 整批拒绝（幻影清除）。**唯一消解路径**=该轮自身的审查事务（APPROVED/APPROVED_WITH_NOTES/NEEDS_CHANGE/BLOCKED 落地即同批清除本轮义务；NEEDS_CHANGE 同时滚动登记下一轮）或 Coordinator 显式 `recheck_obligation_cleared` 事件（人工逃生口，留痕）。追加式事件日志=义务**结构性不可蒸发**；`authority-ledger status` 的 `open_recheck_obligation_keys` 可 grep 未决义务清单。

**③ CONFLICT 判定**：报告清晰携带裁决 token（`**APPROVED|APPROVED_WITH_NOTES|NEEDS_CHANGE|BLOCKED**` 粗体段或「审查结论：」行）而机录 claim 不在其中 ⇒ 拒绝（`code=conflict_report_vs_record`，零写入），处置路径=人工对齐两侧后重跑（禁自动取优）。豁免集 `{BLOCKED, ABORTED, UNKNOWN}`：BLOCKED 是 T2 round≥3 升级裁决（复审必达触发器语义不变——升级记录比报告更严是设计语义而非不一致）；ABORTED/UNKNOWN 是关于代理存活状态的 supervisor 事实，非对被审对象的裁决。无 token 的自由格式报告不参与判定（字节哈希钉扎仍生效）。

**④/⑤ 死亡代理终态**：supervisor 以 `--result ABORTED|UNKNOWN [--abort-reason <文本>]` 记录代理死亡终态（record 内 `- abort_reason:` additive 字段）；终态不触发复审（非 NEEDS_CHANGE）且**不解除未决复审义务**——死亡不豁免该轮仍欠一个真实裁决；补审轮（通常另一位 reviewer，FIX-314 命名空间文件）落真实裁决时同批解除。Check 30 词表已含死亡终态（`_REVIEW_DEATH_TERMINALS`——可解析识别但非合法闭环态：未完成任务 → WARN re-spawn expected；标完成任务 → FAIL fail-closed；死亡终态 R+1 不解除复审必达期望，与账本义务语义一致）。

**触发器语义零变化**（non_goal 硬约束）：T1/T2、round+1、`prev_report` 注入、`next_round` 字段与 summary 键逐字节兼容前置行为（`test_revisit_trigger_fields_byte_compatible` 看护）；本节只加可信绑定。历史 review-record 不回填（provenance 诚实，仅新记录生效）。

**CLI**（全部新参数可选，向后兼容）：

```
python <plugin_home>/infra/verify_workflow.py review-record --task {id} --round {n} \
  --result {APPROVED|APPROVED_WITH_NOTES|NEEDS_CHANGE|BLOCKED|ABORTED|UNKNOWN} \
  --report {报告路径} [--reviewer {名称}] [--bind-file {被审文件}]... [--abort-reason {文本}]
```
