# FEAT-076 消费者矩阵——证据分层迁移读取兼容门（DEC-282 C-1(b) 条件 1）

> **任务**: FEAT-076（0.93.0 清偿轮 Wave2 主载体）
> **授权链**: DEC-278(6) 后继交付契约 → DEC-282 C-1(b)（0.93 重新授权最低五条件）→ DEC-287/292/293（清偿轮全量执行）
> **性质**: 26 组直读消费者逐组标注（需适配/兼容证明/不受影响）——迁移执行的读取兼容门闭合证据
> **基线**: `docs/architecture/evidence-layering-design-admission-inventory.md` §3.1/§3.2（2026-09-28 盘点）；本矩阵在其上标注 0.93 处置终态
> **数据时点**: 2026-09-29（迁移执行前后各一次 check 面对照，见 §3 查询等价证明）

---

## 0. 分层不变式（矩阵判定的公理基础）

分层后的读取契约由四条不变式承载，消费者的兼容性按其对不变式的依赖判定：

| # | 不变式 | 依据 |
|---|--------|------|
| I1 | **写热不变式**：全部四族新行（EVD/REVIEW/RECO/TRIAGE）只写入热表 `evidence-log.md`（governance_store/review_record/change_triage/task_priority 四写入器不变） | 分层设计（写侧零改动） |
| I2 | **本票在热不变式**：当会话/当票产生的行必在热表（追加写热）——hooks 的本票查证语义不依赖冷层 | I1 推论 |
| I3 | **活跃引用留热不变式**：引用未关闭任务（active/in-flight/未解析/保留标记/重复 ID）的行**永不迁移**（六条件分类器 fail-closed） | FEAT-074 分类器 + FEAT-076 单源复用 |
| I4 | **冷层可定位不变式**：已迁移行按行 ID 逐字保全于 `archive/evidence/*.md`，经 `archive/index.md` 行族索引与 `GovernanceDataSource` 族面可定位 | FEAT-076 交付（本票） |

**标注口径**：
- **已适配** = 代码已改为经统一读取入口（GovernanceDataSource 族面/冷行注入）读取跨层历史；
- **兼容证明** = 代码零改动，但其读取语义经不变式推演+实测证明不受迁移影响；
- **不受影响** = 与 evidence-log 行数据无依赖（路径/存在性/写入面）。

## 1. 产品运行时消费者（26 组逐组终态）

| # | 消费者 | 盘点标注 | 0.93 终态 | 依据/实现 |
|---|--------|---------|----------|----------|
| 1 | `verify_workflow.py`（Check 2/13/30/31/32/34 等多处独立全文读） | 高 | **兼容证明** | Check 2（完成证据）与 Check 13（编号缺口/孤儿引用）本就经 `GovernanceDataSource`（热+归档聚合）；Check 31（ragged）只看热表结构=工作集口径；Check 32 只检查**未完成**任务（I3：其证据行必在热）；Check 34 的 RECO 查证=完成推荐快照行（RECO 行随任务关闭迁移后，S1「完成行缺快照关联」的完成行本身也已归档——检查面随之收敛，非破坏）；M5 语料扫描=工作集语料 |
| 2 | `checks/evidence_domain.py` | 高 | **兼容证明** | Check 2 主路径经 `GovernanceDataSource`（get_all_evidence_task_ids 热+冷）；`_parse_evidence_context_tasks`（治理上下文恢复）只关心**未完成**证据事实（I3 留热）；`check_evidence_quality` 扫描热表面（会话上下文引用/循环引用=近期行） |
| 3 | `checks/review_domain.py` | 高 | **已适配** | `_parse_review_coverage_details` 增加 live 模式冷行注入（`_cold_review_evidence_lines`→GovernanceDataSource 族面）：REVIEW/EVD 冷行与热行同语义扫描；`check_agent_team_review`（Check 19）的 EVD 行面同样加热+冷；review-*.md 文件本就不迁移（.governance 根下独立文件）——三源覆盖（行热/行冷/文件）闭合。测试：`tests/test_evidence_layer.py::FEAT076CheckFacesTests` |
| 4 | `checks/triage_domain.py` | 高 | **兼容证明** | Check 32 No-record 面只查**未完成**任务（`task.is_completed(): continue` 先行）+ R1 完成门只查在途任务证据（I3）；TRIAGE 行迁移仅移走已关闭任务的 triage 记录（其 JSON 权威面 change-triage/*.json 不迁移，CLI 记录检查不受影响） |
| 5 | `checks/snapshot_domain.py` | 低 | **不受影响** | mtime 次级新鲜度基线；迁移改写热表 mtime=正常写入事件语义 |
| 6 | `checks/loop_runtime_claims.py` | 中 | **兼容证明** | EVD-707 等锚点行注释自述「Derived pre-archive」——锚点语料在模块内派生物化，不读热表行；会话语料=近期行（I2） |
| 7 | `checks/loop_runtime_claim_attestation.py` | 低 | **不受影响** | 路径存在性检查 |
| 8 | `infra/archive.py`（迁移权威） | 高 | **已适配（本票主对象）** | 族泛化引擎：四族统一经 `_classify_rows_for_family`（与 scan-families 单源零漂移）；族独立 journal（category `evidence-{family}`）；族标记归档文件名（`evidence-{family}-v{range}.md` + incremental 纪律）；索引行族节+完整性第五类计数；回滚恢复四族行。测试：`FEAT076RowFamilyMigrationTests`（6 用例） |
| 9 | `infra/governance_store.py`（evidence-append） | 高 | **不受影响** | 追加写热（I1）；前缀族→文件映射不变 |
| 10 | `infra/change_triage.py`（TRIAGE append） | 中 | **不受影响** | 追加写热（I1） |
| 11 | `infra/review_record.py`（REVIEW append） | 中 | **不受影响** | 追加写热（I1） |
| 12 | `infra/task_priority.py`（RECO append+读） | 中 | **兼容证明** | RECO 读面=`has_reco_row_today`（当日重复闭包判定）——当日行必热（I2）；append 写热（I1） |
| 13 | `infra/loop_migration.py`（全文件备份+改写） | 高 | **兼容证明（运行约束）** | 字节级 digest 契约按「窗口起点的全文」钉住——分层迁移与 loop 迁移窗口互斥（任一方窗口内另一方写入=digest 失配即停，fail-closed 已内建）。运行纪律：M-8 分层迁移不与 loop migration 窗口并发（发布链本就串行） |
| 14 | `infra/loop_engine.py` / `loop_gate_processor.py` | 中 | **兼容证明** | LOOP-{unit}-{tier}-R{n} 行=other-table 族（不在四族迁移面）；round 推导对象=活跃 loop 行（I3 同构） |
| 15 | `infra/closure_chain.py`（:922） | 低 | **不受影响** | 路径引用 |
| 16 | `infra/quickscan_registry.py` | 低 | **不受影响** | 注册表路径声明 |
| 17 | `infra/sync_entry_projection.py` | 低 | **不受影响** | quick entries 同步（plan-tracker 面） |
| 18 | `infra/write_guard_state.py` | 中 | **兼容证明** | 行族对账状态机对「消失对象」有显式处理（absent this run 分支，WARN 披露不阻断）；0.92 M-2 有界迁移（2 任务+18 EVD 行移除）已实证通过；迁移为产品工具写入，EVD 留痕披露 |
| 19 | `infra/resolve_entry.py`（_CORE_GOVERNANCE_FILES） | 低 | **不受影响** | 存在性检查（热表永在） |
| 20 | `infra/release/verify_rel063_evidence.py` | 低 | **不受影响** | 历史证据路径清单（指向 docs/ 归档报告，非热表行） |
| 21 | `web/server.py`（面板展示） | 中 | **兼容证明（口径披露）** | 面板读热表=工作集视图（分层后语义=「当前活跃证据」）；全历史视图经 archive/index.md（面板已有归档链接）。全量跨层面板增强=独立 UI 需求，不阻断迁移 |
| 22 | `hooks/pre-commit` + `hooks/commit-msg`（bash grep 查证） | 高 | **兼容证明** | 查证对象=**本票**证据行（TASK_ID 来自 commit message=当次提交）→ I2 必热；grep 只查热文件语义不变 |
| 23 | `hooks/post-commit`（TASK_ID 存在性确认） | 中 | **兼容证明** | 同 22（I2） |
| 24 | e2e/快照/金样/benchmarks | 中 | **不受影响** | fixture 自建 tmp evidence-log（hermetic）；contract_matrix 快照不覆盖热表数据内容 |
| 25 | `tests/`（~35 文件 fixture 读写） | 中 | **不受影响** | 同 24（fixture 自建）；FEAT-076 新增分层行为测试（test_evidence_layer.py + test_archive.py FEAT076 类） |
| 26 | `project/e2e-test-project/`（投影镜像） | 高 | **不受影响（随发布再生）** | release-projection 生成物，0.93.0 发布链 regen 时携带新 archive.py（非手工同步） |

## 2. 协议/文档/指引消费者

- **读取语义修订**（随本票）：SKILL.md 归档感知条款（「查询已归档 entry：index.md → 归档文件」）已覆盖四族行（行族索引节同一查询路径）；`references/evidence-id-prefix-conventions.md` 的消费者清单由本矩阵更新承载（清单权威=本文档 §1）。
- **不修订面**：bootstrap 收工检查「补证据 evidence-log.md」语义不变（写热，I1）；`core/architecture-health.json`（28s schema）阈值不动——热表口径迁移后自然达标（track 1）；`TOOLS.md` archive 工具族的 CLI 自描述已随代码更新。
- **历史/发布文档**：引用不改码，发布链检查读取 docs/ 归档报告（非热表行），不受影响。

## 3. 查询等价证明（DEC-282 C-1(b) 条件 2）

**方法**：迁移前后各跑一次 check-governance 聚合面 + check-archive-integrity，对照检查面集合。等价判据：分层敏感检查（Check 2 证据完整性/Check 13 编号与孤儿/Check 19 审查覆盖/Check 27 归档候选/Check 28s 尺寸）在迁移后**不产生新 FAIL**，且 Check 27 的 should_archive 面收敛为稳态（无可归档候选）。实测记录见 `.governance/tmp/check-run-20260929/`（迁移前后快照）与 EVD 交付行。

## 4. 五条件闭合表（DEC-282 C-1(b)）

| 条件 | 交付物 | 状态 |
|------|--------|------|
| 1 消费者矩阵 | 本文档 §1/§2（26 组逐组） | ✅ |
| 2 查询等价证明 | §3 + 前后面实测 | ✅（迁移后复验） |
| 3 统一入口或过渡适配 | GovernanceDataSource 族面（get_all_family_rows/find_row/layer_stats）+ Check 19/覆盖率冷行注入 | ✅ |
| 4 清单绑定输入锚漂移即停 | 迁移 journal 钉 input_digest+context_digest（漂移→hot_table_diverged/migration_context_changed 停）；scan-families 锚（commit+sha256）固化于 tmp 快照 | ✅（既有机制复用） |
| 5 回读验收+恢复演练 | 迁移后 check-archive-integrity PASS + 行数守恒对账（迁移统计）+ 回滚演练（test_family_rollback_restores_rows + 生产迁移抽验） | ✅（迁移后复验） |
