# 证据分层设计准入盘点（FEAT-074 预编号——DEC-275(2) 只读测量）

> **任务**: FEAT-074（预编号——β 产品票正式 triage 在设计准入通过后；本盘点为其设计准入前置实测）
> **授权链**: DEC-274 → DEC-275(2)（arch 裁决：β 路径——证据热/冷分层 + 引用透明解析）
> **性质**: 只读测量。零产品代码 / 零测试 / 零治理记录修改；唯一写入 = 本文档。
> **数据时点**: 2026-09-28（本会话实测；0.91.0 已发布、0.92.0 开发中）
> **测量对象**: `.governance/evidence-log.md` = **1,774,376 bytes（1,733.0 KiB）/ 2,906 行**（与 2026-09-28 check-governance 实测一致）

---

## 0. 结论摘要（供 arch 设计准入直接消费）

**核心结论：β 最小分层判据（仅扩展 EVD 行迁移）实测只能迁移 35.3KB（占文件 2.0%），迁移后热表仍为 error 阈值的 6.96×——分层范围必须扩展到 REVIEW/RECO/TRIAGE 行族（+263.2KB 可迁移）并叠加三类引用解析数据修复（REQ 需求实体语义 / FEAT 前缀缺位 / 未规划版本归期），否则 β 票对 Check 28s 无实质缓解。**

| # | 实测事实 | 数字 |
|---|---------|------|
| 1 | live_or_unresolvable_task_ref 当前值（复核 FIX-397⑥ 的 318） | **317 行 / 805,201 B**（09-27 时点 318 → 09-28 迁移 2 行净得 317，见 §1.0） |
| 2 | 四分类主体 = **(ii) 不可解析** | **290 行 / 738,630 B**（live_ref 的 91.5% 行 / 91.8% 字节；占全文件 41.6%） |
| 3 | 不可解析主因 = **REQ-\* 需求实体被 task-family 门控捕获** | 156 行引用 REQ（40 个唯一 ID，REQ-029/083~100 全部存在于 plan-tracker **需求登记表**——不是任务，永无任务版本） |
| 4 | 第二结构性根因 = **FEAT 前缀不在 `_TASK_FAMILY_PREFIXES`** | no_task_family_ref 141 行中 **90 行 / 223,895 B 引用 FEAT-\***（永不可迁移；含 0.92 载荷票 FEAT-073 的证据行——未来 FEAT-074 证据行同样落入此类） |
| 5 | β 判据下保守版本窗（≥1/≥2/≥3）可迁移量 | **均 4 行 / 8,920 B**（窗宽非敏感参数；瓶颈是引用可解析性） |
| 6 | 全窗（≤0.91.0）可迁移量 | **15 行 / 35,275 B** = 现行 would_archive 11 行（26,355 B）+ β 解锁 4 行（8,920 B） |
| 7 | REVIEW/RECO/TRIAGE 行族（**完全不在迁移扫描面**——结构性空白） | 985 行 / 606,107 B（34.2%）；其中关联任务可解析且周期封闭≥1 的 **495 行 / 263,163 B** |
| 8 | 增长速率（近 4 个发布日 09-25~09-28） | EVD 24,749 B/日 + 其他三族 9,801 B/日 ≈ **34,550 B/发布日**；行均字节 2,238.5（近 30 行）/ 2,527.0（近 100 行） |
| 9 | β 最小分层迁移后投影 | **1,739,101 B（1,698.3 KiB）= error 阈值 6.96× / warn 阈值 8.70×**——不达标 |
| 10 | 达标缺口（error 线 250KB） | 需再迁移 **1,524,376 B**——单靠分层判据扩展不可达，需数据修复 + 行族全覆盖 + 稳态定义（准入问题 Q1~Q6，§7） |

**修复解锁量（敏感性，均为估算上界，按修复完成后进入可迁移面计）**：

| 修复项 | 解锁行/字节 | 说明 |
|--------|------------|------|
| (i) 类任务显式归期（未规划版本/G9/G11 → 已封闭周期） | +23 行 / 57,292 B | §1.2 |
| FEAT 前缀加入 allow-list（含 FEAT 票归档后） | +90 行 / 223,895 B 进入可解析面 | §4.3；其中任务已归档部分即可迁移 |
| REQ 需求实体解析语义修复 | 738,630 B 中 REQ 参与156 行引用的主导部分（逐行判定待设计裁定） | §1.3/§7 Q2 |
| REVIEW/RECO/TRIAGE 行族纳入分层 | +495 行 / 263,163 B | §4.3 |

---

## 1. 组 1——317 行 live_or_unresolvable_task_ref 分类（DEC-275 四维度）

### 1.0 当前值复核

- FIX-397⑥（2026-09-27）报 **318 行**；本次实测（2026-09-28）**317 行 / 805,201 B**。
- 差异归因：DEC-264 记录 09-27/28 执行 migrate-big-table 迁移 2 行（1,734,849→1,726,161→…），叠加期间新增 live 引用行——净 318→317。**时点差异已披露，数字以本盘点 317 为准。**

### 1.1 分类方法（判定逻辑）

分类判定与产品迁移门控**零漂移**：直接 `import archive` 调用产品函数 `_classify_evidence_rows`（单一事实源，FIX-385）+ `_evidence_task_versions_standalone()`（= `_archived_task_versions()` 扫 archive/tasks/\*.md 538 条 + `_parse_completed_task_versions` 扫 plan-tracker 优先级表 completed-hot 6 条）。

每行提取 missing task-family IDs（parts[2] 逗号分隔、`[A-Z]+-\d+` 形态、`_is_task_family_id` 过滤、不在 task_versions 者），按下列**优先级顺序**归类（首个命中）：

```
对每个 reason == live_or_unresolvable_task_ref 的行：
  missing := task-family 引用中不在 task_versions 的 ID 集合
  loc(t) := t ∈ task_versions ? resolvable(有版本)
            : t ∈ plan-tracker 活跃表扫描 ? active(tv, status)
            : unresolved                          # 三处均无 → 不可定位
  1. 行文本含显式保留标记（保留热/keep-hot/热保留/禁止归档/禁止迁移/不迁移）
       → (iv) 其余受保护项（reason=explicit_keep_marker）
  2. 任一 missing ID 满足 active ∧ (tv == 0.92.0 ∨ ID ∈ {FIX-401, FEAT-074})
       → (iii) 当前周期必需
  3. 全部 missing ID 为 unresolved → (ii) 不可解析（默认留热 + 入修复清单）
  4. 全部 missing ID 为 active     → (i) 可解析且仍活跃
  5. 其余（混合 active+unresolved） → (iv)（实测=0 行）
```

> 活跃表扫描复刻 `_parse_completed_task_versions` 的容错扫描（表头 `| 优先级 | ID |…`，非 8 管道行跳过）但**不筛状态**，得 21 行热任务（含 2 行 anomalous layout：REL-086=7 管道、FEAT-047=9 管道——产品语义同样跳过，见 §6 修复清单）。

### 1.2 分类结果

| 类别 | 行数 | 字节 | 占 live_ref 字节 | 明细构成 |
|------|------|------|----------------|---------|
| **(i) 可解析且仍活跃** | **23** | **57,292** | 7.1% | REL-077（tv=`G9/G11` 非 semver）7 行；FIX-343(0.82.0) 1 行；FIX-349(0.83.0) 3 行；「未规划版本」已完成任务 11 行：FIX-314/320/348/351、AUDIT-154×2、FIX-396、AUDIT-155×2、AUDIT-156、FIX-397×2（EVD-1196/1197）+1（合计见 i_detail） |
| **(ii) 不可解析** | **290** | **738,630** | 91.8% | 引用 ID 三处（task_versions/活跃表/归档）均无法定位——**默认留热 + 入修复清单**（§6） |
| **(iii) 当前周期必需** | **0** | 0 | 0% | 0.92 任务（FEAT-073/FIX-400/FIX-401）无 EVD 行以 live_ref 形态引用——**注意口径**：FEAT-073 的证据行因 FEAT 前缀缺位落入 no_task_family_ref 类（§4.3），REVIEW-FEAT-073-\* 落入 REVIEW 族；(iii) 的真实「当前周期」体积藏在这两类中，不在 live_ref 内 |
| **(iv) 其余受保护项** | **4** | **9,279** | 1.2% | 显式保留标记 4 行：EVD-553（「不迁移」）、EVD-887/EVD-888（「保留热」）、EVD-1044（「保留热」——归档引擎判据锚点行） |
| **合计** | **317** | **805,201** | 100% | = §1.0 实测值 ✓ |

### 1.3 (ii) 不可解析 290 行的构成（修复清单输入）

按 missing ID 前缀分布（一行可引用多个 missing ID，次数=该前缀 ID 参与 live_ref 行的次数；唯一 ID 数=去重后）：

| 前缀 | 行引用次数 | 唯一 ID 数 | 性质判定 |
|------|-----------|-----------|---------|
| REQ | **156** | 40（REQ-007/029/059~100 等） | **需求登记表实体**（plan-tracker `| REQ-083 | 需求 |…|` 7 列需求表行，已实证 REQ-083/092/095/096 均在）——非任务、永无任务版本；`_TASK_FAMILY_PREFIXES` 含 REQ（注释自认「REQ 也命名需求实体 REQ-082，但 REQ-NNN 可以是任务」），FIX-171 修复了 RISK/DEC/REVIEW 越权但 **REQ 的需求实体用法仍在越权拦截** |
| FIX | 118 | 93 | 历史任务 ID：不在活跃表、不在 archive/tasks（物理删除未归档或编号从未入账）——真不可解析，需逐 ID 核对补映射或标注 superseded（**待设计裁定**） |
| AUDIT | 39 | 34 | 同 FIX（历史审计票） |
| REL | 21 | 14 | 含 REL-086（活跃表行 7 管道 anomalous 被扫描跳过——实际已发布 0.88.0，属**可修复**） |
| SYSGAP | 6 | 3 | 同 FIX |
| VAL | 4 | 2 | 同 FIX |
| ACCEPT | 3 | 1 | 同 FIX |
| FMT | 2 | 2 | 同 FIX |
| DIAG | 1 | 1 | 同 FIX |

高频 ID（行引用次数）：REQ-095/REQ-083 各 14、REQ-092 12、REQ-096 11、REQ-093 9、REQ-085 8、REQ-094 7、REL-077 7（注：REL-077 已发布但 tv 列为 `G9/G11` 非 semver → 归 (i)）、REQ-029 6、REQ-097/098/082/091 各 5。

### 1.4 EVD 行全量 reason 分布（任意 ≤0.90.0 窗下，背景面）

| reason | 行数 | 字节 | 说明 |
|--------|------|------|------|
| live_or_unresolvable_task_ref | 317 | 805,201 | §1.2 |
| no_task_family_ref | 141 | 317,600 | §4.3 构成（FEAT 90 行主导） |
| ref_version_out_of_range | 14 | 30,412 | 引用可解析但版本 > 窗界（窗加宽至 ≤0.91.0 时 3 行/4,057 B 入窗） |
| unknown_evd_id_shape | 10 | 11,660 | EVD-231-FULL/EVD-224B/EVD-FEAT-010-R1/EVD-FIX-271-1/EVD-1087 补记 等（`^EVD-(?:[A-Z]+-)?\d+$` 之外的 ID 形态）——修复清单项 |
| would_archive | 0（≤0.90 窗）/ **11（≤0.91 全窗，26,355 B）** | — | 全窗 11 行 = EVD-1205~1215（0.91.0 发布后新增、任务已归档映射 0.91.0、尚未跑迁移）——**现行判据下即有可归档存量** |

EVD 行族总观：482 行 / 1,164,873 B（65.6% 文件）。**非 EVD 行族（不在迁移扫描面）**：REVIEW 630 行/487,811 B（27.5%）+ TRIAGE 196 行/65,284 B（3.7%）+ RECO 159 行/53,012 B（3.0%）+ 其他表行 9 行/1,842 B + 非表行 1,430 行/1,509 B。

---

## 2. 组 2——版本窗迁移估算

### 2.1 判据定义

**β 判据（DEC-275 口径，行级）**：行可安全迁移 ⟺ ①所属周期封闭（行全部 task-family 引用可解析到版本，取 **max 引用版本**为行的所属周期——保守：最晚引用封闭才算封闭），且 max ≤ 窗上界；②非在途（不引用 0.92.0 任务/FIX-401/FEAT-074）；③引用可解析（含活跃表 tv 可解析的引用——迁移后经清单索引仍可定位热表任务）且迁移后仍可解析；④无显式保留标记。**不是仅按任务 ID 整组迁移**——逐行判定。

保守版本窗（已发布线 0.38.0~0.91.0，最新已发布=0.91.0）：**≥1** → 任务版本 ≤0.90.0；**≥2** → ≤0.89.0；**≥3** → ≤0.88.0；另报**全窗** ≤0.91.0 作上界。

### 2.2 结果

| 窗 | β 可迁移行 | β 可迁移字节 | 构成 |
|----|-----------|-------------|------|
| ≥1（≤0.90.0） | **4** | **8,920** | 全部为 live_ref β 解锁（FIX-343 1 行 + FIX-349 3 行——活跃表 tv 0.82/0.83 可解析且周期封闭）；would_archive=0；out_of_range=0 |
| ≥2（≤0.89.0） | **4** | **8,920** | 同上——**窗宽非敏感** |
| ≥3（≤0.88.0） | **4** | **8,920** | 同上 |
| **全窗（≤0.91.0）** | **15** | **35,275** | would_archive 11 行/26,355 B（§1.4，现行判据即可执行）+ live_ref β 解锁 4 行/8,920 B |

**解读**：(i) 类其余 19 行（REL-077 的 `G9/G11`、11 个「未规划版本」任务）因 tv 非 semver **无法证明周期封闭**——β 判据（版本年龄仅必要条件）下不可迁移，除非先做归期数据修复（+23 行/57,292 B，§0 敏感性）。(ii) 类 290 行引用不可解析 → 全部不可迁移（修复前置）。

### 2.3 结构面扩展估算（非 EVD 行族——现行扫描面之外）

REVIEW/TRIAGE/RECO 行同法判定（关联任务列可解析 + max 版本周期封闭 ≥1 + 排除 0.92）：

| 行族 | 总行/字节 | 可解析且周期封闭≥1（可迁移） | 引用不可解析 | 无任务引用 |
|------|----------|------------------------------|--------------|-----------|
| REVIEW- | 630 / 487,811 | **316 / 203,427** | 118 / 100,205 | 109 / 54,963 |
| TRIAGE- | 196 / 65,284 | **94 / 31,244** | 40 / 13,116 | 58 / 19,588 |
| RECO- | 159 / 53,012 | **85 / 28,492** | 30 / 10,210 | 43 / 13,991 |
| 小计 | 985 / 606,107 | **495 / 263,163** | 188 / 123,531 | 210 / 88,542 |

（估算——行族不在产品扫描面内，本表按 §2.1 判据对行族行直接测算；REVIEW/RECO/TRIAGE 的关联任务列解析与 EVD 同法。）

---

## 3. 组 3——消费者盘点（全仓 grep 面自查闭环）

**grep 面**：`evidence-log`（全仓 Select-String -List，排除 .git 与 backups）+ `\.governance/evidence-log`/`evidence-log.md`（ripgrep 双 pattern 交叉）——命中文件去重后按下列分组；**无统一读取入口存在**（β 设计目标之一；当前基线 = 全部直接读文件，下表「经统一入口」列全部为 否）。

### 3.1 产品运行时消费者（分层后 MUST 适配或验证兼容）

| # | 消费者 | 读取方式 | 行族依赖 | 经统一入口 | 分层后需适配 |
|---|--------|---------|---------|-----------|-------------|
| 1 | `infra/verify_workflow.py`（EVIDENCE_PATH） | **全文读 + 行解析**（Check 2 证据完整性、Check 13 编号缺口、Check 30 审查覆盖、Check 31 ragged、Check 32 triage、Check 34 快照、M5 runtime 语料扫描等多处独立读） | EVD+REVIEW+RECO+TRIAGE | 否 | **高**——多处全文读需改经统一读取入口（热+冷+索引），或至少热表读 + archive/index.md 已有回退路径（SKILL.md 归档感知先例） |
| 2 | `infra/checks/evidence_domain.py` | 全文读 + 行解析（:162/:203/:277/:415/:626 五个入口） | EVD | 否 | **高** |
| 3 | `infra/checks/review_domain.py` | 全文读（REVIEW 行扫描、覆盖率、V3 fuse） | REVIEW | 否 | **高** |
| 4 | `infra/checks/triage_domain.py` | 全文读（最早日期提取、R1 留痕、Check 32） | EVD+REVIEW | 否 | **高** |
| 5 | `infra/checks/snapshot_domain.py` | **mtime**（次级新鲜度基线） | 无内容依赖 | 否 | 低（分层后热表 mtime 语义需定义） |
| 6 | `infra/checks/loop_runtime_claims.py` | 全文读（EVD-707 等锚点 grep + 语料） | EVD（特定锚点） | 否 | 中（锚点行已预归档派生——模块注释自述「Derived pre-archive」；分层后锚点可能在冷表） |
| 7 | `infra/checks/loop_runtime_claim_attestation.py` | 路径存在性 | — | 否 | 低 |
| 8 | `infra/archive.py`（迁移权威） | **全文读 + 行解析 + 改写**（`_classify_evidence_rows`/`_migrate_evidence`/`migrate_evidence_resumable`/rollback/verify_archive_integrity） | EVD（`\| EVD-` 前缀） | 否（它将是分层的写入侧） | **高**——β 票改造主对象；REVIEW/RECO/TRIAGE 行族不在其扫描面（结构性空白 §2.3） |
| 9 | `infra/governance_store.py`（evidence-append） | **追加写**（EVD/REVIEW/RECO/TRIAGE 四前缀族机器写入） | 全部 | 否（写入面） | **高**——追加目标 = 热表（分层语义下写热不变，但前缀族→文件映射 §"EVIDENCE_FILE_NAME" 需与分层兼容） |
| 10 | `infra/change_triage.py`（TRIAGE 行 append :1153） | 追加写 + 存在性 | TRIAGE | 否 | 中 |
| 11 | `infra/review_record.py`（REVIEW 行 append :450） | 追加写 | REVIEW | 否 | 中 |
| 12 | `infra/task_priority.py`（RECO 行 append + 读 :2006/:2155） | 追加写 + 读 | RECO/EVD | 否 | 中 |
| 13 | `infra/loop_migration.py` | **全文件备份 + 改写**（MIGRATION-/ROLLBACK- 行 + 字节级还原契约） | 全部 | 否 | **高**——文件级字节契约与分层后热表语义需重新定义（迁移窗口校验按全文 digest） |
| 14 | `infra/loop_engine.py` / `loop_gate_processor.py` | 全文/行扫描（LOOP-{unit}-{tier}-R{n} 行 round 推导） | LOOP 行（other-table 族） | 否 | 中 |
| 15 | `infra/closure_chain.py`（:922） | 路径引用 | — | 否 | 低 |
| 16 | `infra/quickscan_registry.py`（24 处注册行） | 注册表路径声明 | — | 否 | 低（路径面） |
| 17 | `infra/sync_entry_projection.py`（:82 quick entries） | 读/同步 | — | 否 | 低 |
| 18 | `infra/write_guard_state.py`（:160/:288/:786 evidence-log 面） | 治理写入姿态判定（EVD+REVIEW 双族消歧） | EVD+REVIEW | 否 | 中 |
| 19 | `infra/resolve_entry.py`（:68 `_CORE_GOVERNANCE_FILES`） | 存在性 | — | 否 | 低 |
| 20 | `infra/release/verify_rel063_evidence.py`（:1194） | 证据路径清单 | — | 否 | 低 |
| 21 | `web/server.py`（:254） | 读（Web 面板展示） | 全部 | 否 | 中 |
| 22 | `infra/hooks/pre-commit`（:32）、`hooks/commit-msg`（:31/:52/:288~/:337~/:401/:457） | **bash grep 查证**（REVIEW 证据、目标对齐/用户影响/事实依据/迁移指南字段——LC_ALL=C grep -qE，EVD-874 先例） | EVD+REVIEW（grep 文本） | 否 | **高**——grep 只查热文件；分层后热表不含历史行，查证语义需「热+索引」双查或维持「本票证据必在热表」不变式（新证据写热，查证只查本票——实测影响待设计确认） |
| 23 | `infra/hooks/post-commit`（:148） | bash grep（TASK_ID 存在性确认） | 任意 | 否 | 中（同上） |
| 24 | `infra/verify-e2e.sh`、`contract_matrix/snapshots.json` + `golden_samples.txt`、`benchmarks/closure/cases/standard-success.json` | 快照/金样/e2e | 全部 | 否 | 中（fixture 同步更新面） |
| 25 | `tests/`（~35 文件：test_archive/test_verify_workflow/test_governance_store/test_loop_migration 等 + e2e/test_governance_init） | fixture 读写（tmp dir 临时 evidence-log） | 全部 | 否（fixture 自建） | 中——分层产品票 MUST 同步新增分层行为测试（现有 fixture 语义大多仍有效） |
| 26 | `project/e2e-test-project/`（FIX-350 投影镜像：archive.py/verify_workflow.py/hooks×3/tests/协议文档全套） | 同 1~25 的镜像副本 | 同上 | 否 | **高**——投影镜像随产品票同步（release-projection 生成，非手工） |

### 3.2 协议/文档/指引消费者（分层后需同步修订）

- **Bootstrap/协议**：`CLAUDE.md`/`AGENTS.md`（收工检查「补证据 .governance/evidence-log.md」）、`skills/software-project-governance/SKILL.md`（§121 归档感知、§140~141 交叉验证、§185 收工）、`references/behavior-protocol.md`（:54 写入纪律、:158、:487）、`references/agent-communication-protocol.md`（:10/:377）、`references/change-impact-checklist.md`、`references/interaction-boundary.md`、`references/evidence-id-prefix-conventions.md`（**EVD 前缀消费面权威文档**——分层票 MUST 更新其消费者清单）、`core/protocol/external-command-contract.md`、`core/protocol/headless-runner-sample.md`、`core/templates/*`、`infra/TOOLS.md`（:161/:184/:483 输入声明）、`core/architecture-health.json`（28s schema 本体）、`core/lifecycle-registry.json`、`core/loop-runtime-claim-*.json`
- **入口/命令/角色**：`commands/{change-triage,governance-gate,governance-init,governance-review,governance-status,governance-verify,governance/*}.md`、`agents/{coordinator,governance-developer,maintenance}.md`、`agent-presets/governance/*`、`adapters/*/adapter-manifest.json`（6 个）
- **历史/发布文档**（引用不改码，分层票不需逐个更新但发布链检查读取它们）：`core/releases/*.json`（45 个版本记录）、`changelog.md`、`docs/architecture/ADR-006*`（**治理数据可扩展性 ADR——β 票的设计锚点文档**）、`docs/release/*`、`docs/requirements/*`、`docs/reviews/*`（200+）、`docs/planning/*`、`docs/verification/*`、`docs/knowledge/*`、`project/**`（样例投影）
- **治理数据面**（被引用方，非代码消费者）：`.governance/`（execution-packets.json、change-triage/\*.json、archive/\*\*、review-\*.md 等）

**自查闭环声明**：grep 面（Select-String -List 全仓 + ripgrep `*.py`/`*.md`/hooks/json 交叉）覆盖上表 1~26 + 3.2 全部条目；`.governance/backups/`、`__pycache__/`、`web/dist/`（构建产物）与 `val-009-backup/`（历史验证备份）为非消费者已排除；未发现表外产品代码消费者。

---

## 4. 组 4——迁移后投影与增长速率

### 4.1 热表尺寸投影

| 方案 | 迁移量 | 迁移后热表 | vs error 250KB | vs warn 200KB |
|------|--------|-----------|----------------|----------------|
| 现行判据存量（全窗 would_archive） | 26,355 | 1,748,021 | 6.99× | 8.74× |
| **β 最小分层（EVD-only，全窗）** | **35,275** | **1,739,101** | **6.96×** | **8.70×** |
| β + 行族扩展（+REVIEW/TRIAGE/RECO 可迁移） | 298,438 | 1,475,938 | 5.90× | 7.38× |
| β + 行族 + 全部数据修复（敏感性上界，估算） | ~1,318,000+ | ~456,000 | 1.82× | 2.28× |

> 第 4 行为**估算上界**（REQ 解锁量按 §1.3 逐行判定未完成；FIX/AUDIT 93+34 唯一 ID 修复路径未定）；即使全部达成仍 >250KB——**热表稳态定义（当前工作集）+ 28s 阈值语义演进（DEC-275 已预留：显式变更规则与文档并保留总量监测）是达标的必要组成**，见 §7 Q5。

### 4.2 增长速率（实测）

| 指标 | 值 | 方法 |
|------|-----|------|
| EVD 行新增（近 4 发布日均值） | 24,749 B/日 | 09-25: 24,605 / 09-26: 10,833 / 09-27: 31,986 / 09-28: 31,571（行日期列聚合） |
| REVIEW/TRIAGE/RECO 新增（近 4 发布日均值） | 9,801 B/日 | 09-25: 18,075 / 09-26: 7,853 / 09-27: 7,779 / 09-28: 5,496 |
| **合计增速** | **≈34,550 B/发布日（33.7 KiB）** | 发布节奏 09-25~09-28 为日频（0.88~0.91） |
| EVD 行均字节 | 2,238.5（近 30 行）/ 2,527.0（近 100 行） | 尾部均值 |
| 阈值消耗速率 | 250,000 / 34,550 ≈ **7.2 发布日** 从 0 到 error 线 | 推算 |

### 4.3 no_task_family_ref 构成（FEAT 前缀缺位实证——β 票直接相关）

141 行 / 317,600 B 按引用前缀构成：**FEAT 88 行 / 220,563 B**（+FEAT,RISK 混合 2 行/3,332 B → FEAT 参与共 90 行 / 223,895 B）；(empty 关联列) 21 行 / 22,451 B；**FX 14 行 / 43,961 B**（FX-130 等旧前缀，同样不在 allow-list）；RISK 5 / 10,531；DEC 4 / 5,033；DOC 3 / 5,588；TIER 3 / 3,006；DEC,RISK 1 / 3,135。按月：FEAT 行 2026-07 14 行/33,870 → 2026-09 **75 行/188,742**（0.88~0.91 FEAT 票证据潮）。

**含义**：`_TASK_FAMILY_PREFIXES`（FIX/REL/AUDIT/REQ/FMT/DIAG/MAINT/SYSGAP/TD/DESIGN/VAL/CLEANUP/PRINCIPLE/TASK/RESEARCH/ACCEPT/INIT/PLAN——从旧时点真实数据派生）**不含 FEAT 与 FX**。FEAT 票已成 0.87+ 主力票型 → 其证据行（含 **0.92 载荷候选 FEAT-073 的全部证据行、以及本票 FEAT-074 未来的证据行**）结构性落入永不可迁移类。allow-list 陈旧 = 分层票的前置或同票修复项（§7 Q3）。

### 4.4 下次整理触发点建议

1. **β 产品票落地即执行首次分层迁移**（全窗 ≤0.91.0：would_archive 11 行 + β 解锁 4 行 + 行族面若纳入则 +495 行）；
2. 之后**每版本发布归档（M-8 链）同步分层**（版本窗随最新已发布版本推进，增量迁移该封闭周期行）；
3. 监测触发：Check 28s 保持 advisory + 总量监测（DEC-275 禁缩小检查对象变绿）；热表 >200,000 B（WARN 线）即触发增量分层复核；按当前增速 34,550 B/日，任何一次整理后约 5~6 个发布日内会再触 WARN——**稳态达标依赖行族全覆盖 + 修复清单清偿**（§7 Q5）。

---

## 5. 方法与可复现性

- **判定零漂移**：临时脚本（`%TEMP%\fe074_measure*.py`，**已用后删除**——FIX-401 先例）`sys.path` 注入 `skills/software-project-governance/infra` 后 `import archive`，直接调用产品函数：`_classify_evidence_rows` / `_evidence_task_versions_standalone` / `_parse_completed_task_versions` / `_archived_task_versions` / `_task_status_is_archivable` / `_is_task_family_id` / `_version_to_tuple` / `_version_in_range` / `_EVD_ID_SHAPE_RE`。cwd=仓库根（archive.py 的 HOST_PROJECT_ROOT 为 cwd-first 解析）。**只读**：仅 `read_text`/`stat`/`glob`，零 `.governance` 写入（governance-write-guard 复跑零副作用确认，§5 末）。
- **字节口径**：行字节 = UTF-8 编码长 + 换行符 1B（末行不计）；文件总字节 = `stat().st_size`（与 Check 28s 同口径）。
- **四分类/窗判定/行族测算伪码**：§1.1 与 §2.1；KEEP_MARKERS 词表 =（保留热/keep-hot/热保留/禁止归档/禁止迁移/不迁移）——全文件仅 9 处命中（live_ref 内 4 处归 (iv)；另 5 处在 REVIEW 行/EVD 其他 reason 行，已列 §6）。
- **数据时点**：2026-09-28 会话内；输入 = `.governance/evidence-log.md`（1,774,376 B / 2,906 行）、`.governance/plan-tracker.md`（190,829 B / 458 行；优先级表热任务 21 行 + 需求登记表）、`.governance/archive/tasks/`（36 文件 538 ID 映射）、`archive/evidence/`（31 文件）。已发布线 0.38.0~0.91.0（plan-tracker 版本历史节 + core/releases/*.json）。
- **估算标注**：§2.3 行族测算、§4.1 第 4 行上界、§4.2 阈值消耗推算为**估算**（方法已注）；其余为实测。
- **复核链**：317 vs 318 时点差异（§1.0）；318 原始出处 = FIX-397⑥ EVD-1197/DEC-264（2026-09-27）。

## 6. 边缘发现与修复清单（默认留热项的处置输入）

1. **REQ 需求实体语义**（最大项，156 行引用/40 唯一 ID）：REQ-029/083~100 在 plan-tracker 需求登记表为需求实体，被 task-family 门控捕获。修复路径候选（待 Q2 裁定）：需求登记表作为合法解析目标（可定位=可解析）/ REQ 移出 allow-list（评估 REQ-082 型真任务 ID 影响）/ 数据面改注 cross-entity。
2. **FEAT/FX 前缀缺位**（90+14 行 / 267,856 B）：allow-list 从旧数据派生未覆盖 FEAT/FX。FEAT 加列 + FX 归并为 FIX 或单列（历史 FX-130 系）——含回归测试与 ADR-009（task-id 命名约定）同步。
3. **未规划版本/G9/G11 归期**（(i) 类 19 行 / 51,593 B + REL-077 7 行）：已完成但 tv 非 semver 的任务行（FIX-314/320/348/351、AUDIT-154/155/156、FIX-396/397、REL-077）——补归属周期后即进入可迁移面。
4. **anomalous layout 行**：REL-086（7 管道）、FEAT-047（9 管道）——列数异常致活跃表扫描跳过（REL-086 已发布 0.88.0 却不可定位）；修复 = 行归一（FIX-397① 同型 schema 归一先例）。
5. **unknown_evd_id_shape 10 行 / 11,660 B**：EVD-231-FULL/EVD-224B/EVD-FEAT-010-R1/R2/EVD-FIX-271-1/R1/EVD-FIX-274-R1/EVD-FIX-288-BLOCKED/EVD-1087 补记（含重复 ID EVD-FEAT-010-R1 两行）——ID 形态扩展或数据归一（待设计裁定）。
6. **FIX/AUDIT 真不可解析 93+34 唯一 ID**：历史任务物理删除未归档——补 archive 映射、标注 superseded、或接受永久留热（体积代价见 §1.3）。
7. **REVIEW/RECO/TRIAGE 行族无迁移面**：现行 `_classify_evidence_rows` 只扫 `| EVD-` 前缀——985 行 / 606,107 B 结构性排除在归档之外（§2.3 为其 β 判据测算）。
8. **would_archive 存量 11 行**（EVD-1205~1215 / 26,355 B）：0.91.0 发布后新增、任务已归档、现行判据即可迁移——下次 M-8 归档链即可清偿（无需等 β）。
9. **loop_migration.py 文件级字节契约** vs 分层：全文件 digest 校验/回滚在热冷分立后需重定义（消费者 #13）。

## 7. 设计准入确认问题清单（供 arch 裁定）

- **Q1 范围**：β 最小分层（EVD-only）实测仅 35.3KB（2.0%）——分层范围 MUST 扩展至 REVIEW/RECO/TRIAGE 行族（+495 行/263.2KB）是否随 β 票同载？（否则对 28s 无实质缓解，§4.1）
- **Q2 REQ 语义**：REQ-\* 需求实体引用的解析口径三选一（需求登记表为合法解析目标 / REQ 移出 allow-list / 数据改注 cross-entity）？（解锁 738.6KB 主体的最大份额，§1.3/§6.1）
- **Q3 FEAT/FX**：allow-list 补 FEAT（含 FX 处置）随 β 票还是独立数据修复票？（影响 0.92 载荷票 FEAT-073 及本票 FEAT-074 自身证据行的可迁移性，§4.3）
- **Q4 修复清单归属**：§6 六项数据修复（归期/anomalous/unknown-shape/FIX-AUDIT 不可解析 ID）归 β 票载荷、独立卫生批、还是修复清单挂账？
- **Q5 稳态与阈值**：即使全修复，热表 ≈450KB+（1.8× error 线）——热表稳态定义（当前工作集 = 0.92 活跃链 + 未决审查 + 近 N 版？）与 28s 阈值语义演进（分层后按热表口径 + 总量监测双轨）的裁定？
- **Q6 无引用行**：no_task_family_ref 中 (empty)/RISK/DEC/TIER/DOC 行（34 行/48.5KB）与行族 no_task_ref（210 行/88.5KB）无周期归属——按行日期窗迁移或永久留热？

---

*本盘点为只读测量产物（唯一写入 = 本文档）；未修改任何产品代码/测试/治理记录；未 commit。测量脚本已从 %TEMP% 删除。governance-write-guard 复跑：零副作用（见会话结构化返回）。*
