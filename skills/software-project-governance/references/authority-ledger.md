# 权威账本与身份契约（FEAT-093）

> schema 锚：`authority-ledger/1`（`infra/authority_ledger.py` 常量 `LEDGER_SCHEMA`）
> 需求源：RPG 长程 session 实测同 ID 双语义 ×5 组 / 22 行僵尸「未开始」/ 计划执行双轨零对账（分析报告 §3.2；DEC-330 拆票，本票为 0.98「可信有界执行内核」首票）。

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
