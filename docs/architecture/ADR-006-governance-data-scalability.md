# ADR-006: 治理数据伸缩性 —— 版本归档 + 索引混合方案

**日期**: 2026-05-08
**状态**: 已实现（Phase 1 归档基础设施完成：archive.py + GovernanceDataSource + Check 26 + manifest.json 更新。已完成：H6 原型验证、ADR-006 C2 索引大小修正）
**决策人**: Architect（老顾）
**关联任务**: SYSGAP-030
**前置分析**: `.governance/requirements-SYSGAP-030-governance-scalability.md`（Analyst 阿析，v2 已通过审查）
**影响范围**: 治理文件分层模型（新增 `archive/` 目录 + 索引文件）+ CLAUDE.md bootstrap 读取指令修改 + verify_workflow.py 归档感知升级 + 迁移脚本
**可逆性**: 高（归档文件可手动合并回主文件、索引文件可删除重建、bootstrap 读取指令可回退）

---

## 1. 背景

### 1.1 问题陈述

software-project-governance 工作流的 4 个核心治理文件随项目时间线性膨胀，每次会话强制读取全部内容：

| 规模 | 任务数 | 治理数据总量 | tokens 估算 | 占 1M 窗口 |
|------|--------|------------|------------|-----------|
| 当前 (3 周) | 168 | 449 KB | ~180K | 18% |
| 6 个月 | 1,000 | ~2,637 KB | **~1,055K** | **超标 5.5%** |
| 12 个月 | 2,000 | ~5,265 KB | ~2,106K | 超标 111% |

> 数据来源：需求澄清报告 v2（evidence-log 条目增长率修正为 1.41 entries/task）

**根因**：治理框架没有内置数据生命周期管理——所有历史数据永远驻留在"每次会话必读"的热文件中。

### 1.2 设计约束

| # | 约束 | 来源 |
|---|------|------|
| C1 | 治理文件必须保持 Markdown 格式，人类可直接阅读 | 项目设计原则 |
| C2 | verify_workflow.py 的所有现有 Check 必须继续 PASS | 质量保障要求 |
| C3 | 不能依赖外部数据库或网络服务——纯本地文件系统 | Claude Code 能力边界 |
| C4 | 不能破坏现有 ID 命名规范（EVD-xxx, DEC-xxx, RISK-xxx） | verify_workflow.py 依赖 |
| C5 | plan-tracker 的 Markdown 表格结构保持不变 | verify_workflow.py 和 agent 解析依赖 |
| C6 | 每次会话必读治理数据量 < 120 KB（无论项目规模多大） | 需求澄清成功指标 1 |
| C7 | 1000-task 规模下热数据文件总大小 < 500 KB | 需求澄清成功指标 3 |

### 1.3 当前治理文件内容分析

#### plan-tracker.md（193 KB）内容构成

| 内容类别 | 大致大小 | 数据温度 | 说明 |
|---------|---------|---------|------|
| 项目配置 + Gate 状态 + 项目总览 | ~3 KB | **热** | 每次会话必需 |
| 当前活跃事项（优先级一览） | ~21 KB | **热** | 活跃 P0/P1/P2 任务列表 |
| 已完成版本 task 表（0.11.0~0.24.0） | ~6 KB | **冷** | 已发布版本的历史 task |
| 1.0.0 依赖链 | ~0.4 KB | **热** | 待完成依赖 |
| 实施路线图（DEC-052） | ~6 KB | **温→冷** | 已完成并标记归档的路线图 |
| 版本规划（路线图+V-Gate+纪律） | ~11 KB | **热→温** | 版本路线图是热，纪律是温 |
| 需求跟踪矩阵 | ~9 KB | **温** | 偶尔查询 |
| 变更控制 | ~2 KB | **温** | 偶尔查询 |
| 历史审计/修复 task 列表 | ~108 KB | **冷** | 已完成的各种历史记录 |

**关键发现**：当前 plan-tracker 中约 **60-70% 的内容是已完成的历史数据**。真正的"热数据"仅约 **170 行 / ~25 KB**。

#### evidence-log.md（163 KB）内容构成

| 内容类别 | 条目数 | 大致大小 | 数据温度 |
|---------|-------|---------|---------|
| 最近活跃版本的证据 | ~30 条 | ~25 KB | **热** |
| 1-3 个月前证据 | ~80 条 | ~55 KB | **温** |
| 3 个月以上历史证据 | ~126 条 | ~83 KB | **冷** |

#### decision-log.md（74 KB）和 risk-log.md（19 KB）

- decision-log: 60 条决策，当前规模可控。按增长率在 3 年后约 ~600 KB
- risk-log: 28 条风险（活跃仅 2 条），当前规模可控

---

## 2. 方案评估

### 2.1 四个方案方向量化比较

| 评估维度 | 方向 A: 版本归档 | 方向 B: 时间窗口 | 方向 C: 三层存储+索引 | 方向 D: 混合方案(推荐) |
|---------|----------------|----------------|-------------------|-------------------|
| **每次会话读取量** (1000-task) | ~150 KB | ~120 KB | **~100 KB** | ~120 KB |
| **热数据文件总大小** (1000-task) | ~400 KB | ~350 KB | **~300 KB** | ~350 KB |
| **实现复杂度** (1-5) | **2** | 1 | 4 | 3 |
| **查询效率** (跨版本) | 差（需扫多个文件） | 一般 | **好**（索引定位） | **好**（索引定位） |
| **迁移成本** (已有项目) | 低 | 中 | 高 | 中 |
| **边界清晰度** | **好**（版本天然边界） | 差（30天=任意选择） | 好（明确定义） | **好**（版本+补充规则） |
| **与现有 V-Gate 一致** | **是** | 否 | 部分 | **是** |
| **索引维护成本** | 低（隐含在版本名中） | 无 | 高（独立索引） | 中（索引+版本） |
| **归档文件人类可读性** | **好**（按版本浏览） | 差（时间分组不直观） | 一般（需索引辅助） | **好**（版本为主+索引辅助） |
| **verify_workflow.py 改动量** | 中（需遍历 archive/） | 中 | 大（需全新解析逻辑） | 中（遍历+索引加速） |
| **决策引用完整性** | 一般（跨版本决策需特殊处理） | 一般 | 好（索引可标注） | **好**（索引显式记录跨版本引用） |

### 2.2 方向 A：版本归档

**核心思路**：以版本发布为归档边界。版本发布后，该版本内的所有 task、evidence、decision 从主文件移到 `archive/tasks-{version}.md`。

**优势**：
- 边界清晰：版本发布是工作流中自然的、已被定义的分割点
- 与现有版本规划体系（V-Gate、版本路线图）完全对齐
- 归档文件按版本名命名，人类可直接浏览
- 实现复杂度最低

**挑战**：
- 跨版本依赖引用：task 可能依赖已归档版本中的 task——需索引或保留依赖链在主文件中
- 版本之间的"进行中"task：一个任务可能跨越多个版本才完成——归档边界选择需要规则
- decision 可能引用跨版本的证据——需处理引用完整性

### 2.3 方向 B：时间窗口归档

**核心思路**：保留最近 N 天（如 30 天）的数据在主文件中，超过的自动归档。

**优势**：
- 最简单实现
- 不依赖版本概念

**排除理由**：
- 时间边界不如版本边界清晰（"30 天"是任意选择）
- 与版本周期不对齐——一个版本可能跨 2 个月，导致一个版本的数据分散在多个归档文件中
- 人类按时间查历史不如按版本查直观
- 不推荐作为主方案

### 2.4 方向 C：三层存储 + 纯索引

**核心思路**：
- 热文件：仅含活跃 task + 最近 evidence
- 归档目录：所有历史数据
- 索引文件：记录每个条目在哪个归档文件中

**优势**：
- 最灵活的查询能力
- 每次会话开销最小

**挑战**：
- 索引文件与归档文件的一致性维护成本高
- 索引本身可能膨胀
- JSON 索引破坏"纯 Markdown"承诺

### 2.5 方向 D：混合方案（版本归档 + 轻量索引）—— 推荐

**核心思路**：
- 版本归档作为主归档边界（与 V-Gate 对齐）
- 轻量索引文件（Markdown 表格）记录"哪个条目在哪个归档文件里"
- 热文件保留当前活跃版本（未发布）的全部数据 + 结构骨架
- 索引优先 Markdown 格式，保持人类可读性

---

## 3. 决策

**采用方向 D（混合方案：版本归档 + 轻量索引）**，并吸纳方向 C 的热/温/冷分层设计。

### 3.1 选择理由

1. **版本边界是最自然的归档边界**：工作流已有完整的版本规划体系（V-Gate、版本路线图、版本里程碑），归档与版本发布同步进行——每个版本发布后，该版本的数据从热文件移出，下一个版本的开发数据进入热文件。这是"边界清晰"的最优解。

2. **索引是必需的——但形式可以轻量**：不引入独立 JSON 索引文件（破坏人类可读性承诺），而是用归档文件自身的 Markdown 文件头 + 一个轻量的 `archive/index.md`（Markdown 表格）来提供映射。索引查询不超过 1 次额外的 Read tool call。

3. **热/温/冷分层解决了"热数据大小恒定"的核心目标**：三层分类规则明确定义了每个治理段落属于哪一层，归档触发条件有三级优先级确保不会遗漏。

4. **verify_workflow.py 改动量可控**：所有现有 Check 的解析逻辑通过"多文件扫描"适配——原来读 1 个大文件，现在读 1 个热文件 + N 个归档文件。索引用于加速（先查索引定位目标归档文件再读取，而非逐个打开所有归档文件）。

5. **方向 A 单独不够，方向 C 过度设计，方向 D 是两者的最优交集**：
   - 纯版本归档（A）缺少索引 → 跨版本查询需要盲目扫描所有归档文件
   - 纯三层索引（C）维护成本高 + JSON 违反对人类可读性的承诺
   - 混合方案（D）拿版本归档的自然边界 + 索引的查询能力，避免两者的极端缺点

### 3.2 排除备选方案的详细理由

| 方案 | 排除理由 |
|------|---------|
| **仅方案 A（版本归档，无索引）** | 跨版本查询需遍历 `archive/` 下所有文件——verify_workflow.py 全量检查在每个归档文件上盲目解析，性能不可接受。无索引 = 无法回答"task X 的证据在哪里"而不打开所有文件 |
| **仅方案 B（时间窗口归档）** | 边界模糊——"30天"是任意数字，与版本周期不对齐。一个版本的数据可能分散在多个时间窗归档文件中。不选 |
| **仅方案 C（纯三层存储+JSON 索引）** | JSON 索引破坏"人类可读 Markdown"承诺（C1 约束）。索引与归档文件的分布式一致性维护成本高。三层分离增加 agent 读取的认知负担（需要理解三层模型才能找到数据）。过度设计——当前规模不需要如此复杂的存储模型 |
| **方案 A + B 组合** | 两套归档规则并行增加 agent 和 verify_workflow.py 的认知复杂度。版本归档 + 超时兜底（方向 D 的归档触发优先级 3）已覆盖时间兜底需求，不需要独立的时间窗口归档机制 |
| **外部数据库** | 违反 C3 约束——Agent 必须在本地文件系统读取。且引入 SQLite 等依赖破坏"开箱即用" |

---

## 4. 详细设计

### 4.1 文件布局设计

```
.governance/
├── plan-tracker.md          # [修改] 热数据——仅含活跃上下文
├── evidence-log.md          # [修改] 热数据——仅含当前版本证据
├── decision-log.md          # [修改] 热+温——保留近 2 年决策，超过按年归档
├── risk-log.md              # [保持] 当前规模可控，暂不归档
├── session-snapshot.md      # [保持] 跨会话快照
├── agent-locks.json         # [保持] Agent 锁表
│
├── archive/                 # [新增] 归档目录
│   ├── index.md             # [新增] 归档索引——条目→归档文件映射
│   ├── tasks/               # [新增] plan-tracker 归档
│   │   ├── v0.11.0~v0.24.0.md   # 已发布版本的 task 表归档
│   │   └── ...
│   ├── evidence/            # [新增] evidence-log 归档
│   │   ├── v0.11.0~v0.24.0.md   # 已发布版本的证据归档
│   │   └── ...
│   ├── decisions/           # [新增] decision-log 归档（仅当 decision > 2 年）
│   │   └── 2026.md
│   └── risks/               # [新增] risk-log 归档（仅当 risk 数 > 500）
│       └── ...
```

**设计原则**：
- `archive/` 下按治理文件类型分子目录（`tasks/`、`evidence/`、`decisions/`、`risks/`）
- 每个归档文件是独立可读的 Markdown 文件
- 归档文件名与其对应版本一致（如 `v0.11.0~v0.24.0.md` 表示该文件包含版本 0.11.0 到 0.24.0 的数据）
- 版本区间可合并——如果某版本数据量小，可与相邻版本合并到一个归档文件

### 4.2 热/温/冷数据分类规则

#### plan-tracker.md 热数据（每次会话必读）

保留在 `plan-tracker.md` 中的段落：

| 段落 | 理由 | 预估大小（1000-task） |
|------|------|---------------------|
| `## 项目配置` | 会话启动必需——phase/stage/mode 信息 | ~2 KB |
| `## Onboarding 声明` | Gate 状态前置信息 | ~1 KB |
| `## Gate 状态跟踪` | 交叉验证必需 | ~2 KB |
| `## 项目总览` | 当前状态总览 | ~1 KB |
| `## 当前活跃事项` | 仅含未完成的 P0/P1/P2 任务（含"进行中"） | ~30 KB |
| `## {当前版本} — {版本描述}` | 正在开发中的版本的 task 表（含已完成但未发布的任务） | ~25 KB |
| `## 1.0.0 依赖链` 或等效的 top-level 依赖 | 发布前置条件 | ~1 KB |
| `## 版本规划`中的路线图部分 | 当前活跃版本路线 | ~3 KB |
| **合计** | | **~65 KB** |

> 满足指标 3（热数据 < 500 KB），且 bootstrap 实际读取量 < 120 KB（满足指标 1）。

#### plan-tracker.md 温数据（留在主文件，但 bootstrap 不强制读取）

保留在 `plan-tracker.md` 中但 agent 可按需跳过的段落：

| 段落 | 理由 |
|------|------|
| `## 需求跟踪矩阵` | 偶尔查询——每次会话不需要 |
| `## 变更控制` | 偶尔查询 |
| `## 版本规划`中的纪律部分 | 温数据——参考性质的规则说明 |

#### plan-tracker.md 冷数据（归档到 `archive/tasks/`）

| 段落 | 归档文件 | 触发条件 |
|------|---------|---------|
| 已发布版本的 task 表（如 `### 0.11.0 — ...` ~ `### 0.24.0 — ...`） | `archive/tasks/v{start}~v{end}.md` | 版本发布后立即归档 |
| 已完成的审计/修复 task 列表（已归档版本的） | 同上 | 同版本归档 |
| 历史实施路线图（已标记"已完成并归档"的） | `archive/tasks/implementation-roadmap.md` | 路线图完成后归档 |

#### evidence-log.md 分类规则

| 数据 | 位置 | 触发条件 |
|------|------|---------|
| 当前活跃版本（未发布）的证据 | `evidence-log.md`（热） | 始终保留 |
| 上一已发布版本的证据 | `evidence-log.md`（热） | 版本发布后保留一个版本的宽限期 |
| 更早版本的证据 | `archive/evidence/v{start}~v{end}.md`（冷） | 当前版本发布时，归档两版本前的证据 |
| 正在进行的 task 的相关证据 | `evidence-log.md`（热） | 始终保留直到 task 完成并归档 |

#### decision-log.md 分类规则

| 数据 | 位置 | 触发条件 |
|------|------|---------|
| 最近 2 年的决策 | `decision-log.md`（热） | 始终保留 |
| 超过 2 年的决策 | `archive/decisions/{year}.md`（冷） | 每年末归档 |

> 决策有独立查询价值（"这个决策当时为什么这么定"），且增长率远低于 task/evidence——即使在 5 年项目中也只有 ~600 KB。2 年窗口提供足够的查询便利性。

#### risk-log.md 分类规则

| 数据 | 位置 | 触发条件 |
|------|------|---------|
| 所有活跃风险 | `risk-log.md`（热） | 始终保留 |
| 已关闭风险（最近 1 年） | `risk-log.md`（温） | 始终保留 |
| 已关闭风险（超过 1 年且总数 > 200） | `archive/risks/{year}.md`（冷） | 超过阈值时归档 |

> 风险是低频数据（每 6 个 task 产生 1 条风险），1000-task 规模下也只有 ~67 KB。默认不归档 risk-log，仅在极端规模时触发归档。

### 4.3 归档触发条件（三级优先级）

```
优先级 1（强制）：版本发布后自动触发
  ├─ V-Gate 通过后 → 归档脚本扫描当前版本内的所有 task/evidence
  ├─ 将已完成的 task 和相关 evidence 移入归档文件
  ├─ 更新 archive/index.md
  └─ 执行 verify_workflow.py check-governance 验证——PASS 后才算归档完成

优先级 2（增量）：单 task 完成 + 关联证据记录后
  ├─ task 状态变为"已完成" + 在 evidence-log 中有对应条目
  ├─ 如果该 task 属于已发布的版本 → 立即增量归档
  ├─ 写入当前版本的归档文件末尾（追加模式）
  └─ 更新 archive/index.md（追加该 task 的索引条目）

优先级 3（兜底）：超过 N 天未触发归档
  ├─ N = 90 天（一个季度）
  ├─ 如果优先级 1 或 2 长期未触发（如无版本发布节奏的项目）
  ├─ 触发条件：plan-tracker 中最后一个已发布版本的发布时间 > 90 天
  └─ 按优先级 1 的流程执行一次完整的版本归档
```

**设计原理**：
- 优先级 1 是主路径——版本发布是自然的归档时间点
- 优先级 2 降低单次归档负担——每次 task 完成即增量归档，避免版本发布时一次处理大量数据
- 优先级 3 是安全网——防止无版本发布节奏的项目数据无限累积
- 优先级 1 和 2 并行不互斥：版本发布时，已通过优先级 2 归档的 task 直接跳过

### 4.4 索引文件格式设计

**文件路径**: `.governance/archive/index.md`

**格式**: Markdown 表格（保持人类可读性承诺）

```markdown
# 治理数据归档索引

> 自动生成，记录每个治理条目的归档位置。查询路径：条目 ID → 归档文件。
> 维护方式：归档脚本执行时自动更新。

## Task 索引

| Task ID | 状态 | 版本 | 归档文件 |
|---------|------|------|---------|
| FIX-030 | 已完成 | 0.28.0 | `archive/tasks/v0.25.0~v0.32.0.md` |
| SYSGAP-001 | 已完成 | 0.21.0 | `archive/tasks/v0.21.0~v0.24.0.md` |
| AUDIT-082 | 已完成 | 0.11.0 | `archive/tasks/v0.11.0~v0.20.0.md` |
| SYSGAP-030 | 进行中 | 1.0.0 | `plan-tracker.md`（未归档——活跃 task） |

## Evidence 索引

| Evidence ID | 关联 Task | 归档文件 |
|-------------|----------|---------|
| EVD-001 | INIT-001 | `archive/evidence/v0.1.0~v0.10.0.md` |
| EVD-151 | AUDIT-087 | `archive/evidence/v0.25.0~v0.32.0.md` |
| ... | ... | ... |

## Decision 索引

| Decision ID | 日期 | 归档文件 |
|-------------|------|---------|
| DEC-001 | 2026-04-17 | `decision-log.md`（未归档——2 年内） |
| ... | ... | ... |

## Risk 索引

| Risk ID | 状态 | 归档文件 |
|---------|------|---------|
| RISK-001 | 已关闭 | `risk-log.md`（未归档——< 200 条） |
| ... | ... | ... |
```

**设计决策**：
- 索引采用 Markdown 表格而非 JSON——保持人类可直接阅读
- 索引仅记录**已归档**的条目——活跃条目在热文件中，不需要索引
- 每个条目一行——1000-task 规模下 full 索引（task + evidence + decision + risk）约 4000 行 ≈ 120 KB（满足 H4: < 200 KB）。若仅 task 子索引约 1000 行 ≈ 30 KB
- 索引查询步骤：`grep <id> archive/index.md` → 获取归档文件路径 → 一次 Read call

**查询路径示例**：
```
Agent 需要查询 EVD-100 的详细内容：
  1. Read .governance/archive/index.md → grep "EVD-100"
  2. 发现 EVD-100 → archive/evidence/v0.11.0~v0.24.0.md
  3. Read .governance/archive/evidence/v0.11.0~v0.24.0.md → 定位 EVD-100 条目
```
总开销：2 次 Read call（索引 1 次 + 归档文件 1 次）。

### 4.5 CLAUDE.md bootstrap 读取指令修改

#### 当前 Step 1-2 读取指令

当前 CLAUDE.md Step 1 和 Step 2 要求 agent 直接读取整个 `.governance/plan-tracker.md` 和 `.governance/evidence-log.md`。随着文件膨胀，这将成为瓶颈。

#### 修改后的读取指令

```
### Step 1: 读 plan-tracker + 跨会话恢复

1. 读取 `.governance/plan-tracker.md`（热数据文件）
   — 如果文件 > 500 KB（极端情况），仅读取以下段落：
     a. `## 项目配置`（当前 phase/stage/gate/mode）
     b. `## Gate 状态跟踪`（所有 Gate 状态）
     c. `## 项目总览`（当前统计）
     d. `## 当前活跃事项`（仅未完成的任务）
     d. 当前活跃版本的 task 表（版本描述含"进行中"或"未发布"）
   — 以下段落按需读取（不在 bootstrap 阶段强制读取）：
     e. `## 需求跟踪矩阵`
     f. `## 变更控制`
     g. `## 版本规划`中的"规划纪律"部分

2. 读取 `.governance/session-snapshot.md`（如存在），对照 plan-tracker：
   ...（同现有指令）

3. **归档感知**：如果 bootstrap 交叉验证发现某个已完成 task 的 evidence 在 `evidence-log.md` 中找不到，
   → 读取 `.governance/archive/index.md` 查询归档位置
   → 仅在需要验证特定 task 的 evidence 时才读取归档文件

### Step 2: 交叉验证（3 项强制检查）

对照 `.governance/plan-tracker.md` 和 `.governance/evidence-log.md`：

1. **证据完整性**：plan-tracker 中状态为"已完成"的任务，先查 evidence-log.md 热数据。
   缺失 → 查 archive/index.md → 如仍缺失 → 记录为缺失证据（按 Profile 处理）。
   **注意**：归档文件中的证据 = 有效证据——不可误判为缺失。

2. **Gate 一致性**：...（同现有指令）

3. **风险过期**：risk-log 中活跃风险超过 7 天未更新？...（同现有指令）
```

**关键改动**：
1. 明确"热数据段落"列表——agent 知道哪些必须读，哪些按需读
2. 新增归档感知逻辑——先在热文件查，找不到再查索引
3. 归档文件中的证据 = 有效证据——防止误报"缺失证据"

### 4.6 归档文件 Markdown 格式规范

每个归档文件必须包含**标准化文件头**，确保独立可读性：

```markdown
# 归档 Task 记录 — v0.11.0 ~ v0.24.0

- **归档日期**: 2026-05-09
- **归档类型**: plan-tracker task 表
- **覆盖版本**: v0.11.0, v0.12.0, ..., v0.24.0
- **条目数**: 87 tasks
- **上一个归档文件**: `archive/tasks/v0.1.0~v0.10.0.md`（如存在）
- **下一个归档文件**: 无（当前最新归档）

> 本文件为治理数据归档。来自原始 `.governance/plan-tracker.md`。
> 查询方式：通过 `.governance/archive/index.md` 按 task_id 定位。

---

## v0.24.0 — 目标一致性 + 用户影响系统强制

...（原 plan-tracker 中该版本的 task 表内容）
```

**格式约束**：
- 文件头包含归档日期、类型、覆盖版本、条目数
- 保留原 plan-tracker 的版本标题结构和表格格式
- `上一个/下一个归档文件` 字段形成归档文件链——支持顺序浏览
- 每个归档文件是独立可读的完整 Markdown 文件

---

## 5. verify_workflow.py 归档感知升级

### 5.1 升级策略

**核心原则**：所有 Check 的**逻辑不变**，仅**数据源从"单文件"变为"热文件 + 归档文件集合"**。

#### 改造方案：引入 `GovernanceDataSource` 抽象

不修改每个 check 函数的内部逻辑，而是在数据读取层引入统一的多文件扫描。

```python
# 概念设计（不写实现代码——交给 Developer）
class GovernanceDataSource:
    """统一治理数据源——透明聚合热文件 + 归档文件"""
    
    def get_all_tasks(self) -> list:
        """从 plan-tracker.md + archive/tasks/*.md 聚合所有 task"""
        pass
    
    def get_all_evidence(self) -> list:
        """从 evidence-log.md + archive/evidence/*.md 聚合所有证据"""
        pass
    
    def get_all_decisions(self) -> list:
        """从 decision-log.md + archive/decisions/*.md 聚合所有决策"""
        pass
    
    def get_all_risks(self) -> list:
        """从 risk-log.md + archive/risks/*.md 聚合所有风险"""
        pass
    
    def find_entry_by_id(self, entry_id: str) -> Optional[dict]:
        """先查热文件，再查 archive/index.md，最后读归档文件"""
        pass
```

#### 各 Check 受影响分析

| Check 函数 | 数据源变化 | 改动量 | 说明 |
|-----------|-----------|--------|------|
| `parse_completed_task_ids()` | plan-tracker.md → plan-tracker.md + archive/tasks/*.md | 小 | 只需多文件扫描 |
| `parse_evidence_task_ids()` | evidence-log.md → evidence-log.md + archive/evidence/*.md | 小 | 同上 |
| `check_evidence_completeness()` | 依赖上述两个 parse 函数 | 无 | parse 函数改好后自动生效 |
| `check_gate_consistency()` | plan-tracker.md → 多文件 | 小 | 多文件扫描 |
| `check_sequential_ids()` | 4 文件 → 4+N 文件 | 中 | ID 连续性检查需跨所有文件。**关键设计**：归档不破坏 ID 连续性——归档文件的 ID 范围与版本范围对齐，检查时按时间顺序遍历所有文件即可 |
| `check_cross_references()` | 文件引用图 → 多文件 | 小 | 归档文件也是有效的引用目标——需要将 `archive/` 目录加入扫描范围 |
| `check_structural_validity()` | plan-tracker.md → 多文件 | 小 | 每个归档文件也需检查表格列数一致性 |
| `check_risk_staleness()` | risk-log.md → 不变 | 无 | risk-log 当前不归档 |
| 其他 check | — | 无 | 不涉及治理文件内容读取 |

**关键改造点**：

1. **`SAMPLE_PATH` 改为一组路径**：
   ```python
   # 原来
   SAMPLE_PATH = ROOT / ".governance/plan-tracker.md"
   
   # 改为
   HOT_PLAN_TRACKER = ROOT / ".governance/plan-tracker.md"
   ARCHIVE_TASKS_DIR = ROOT / ".governance/archive/tasks/"
   
   def get_all_plan_tracker_files():
       """返回所有 plan-tracker 相关文件（热 + 归档）"""
       files = [HOT_PLAN_TRACKER]
       if ARCHIVE_TASKS_DIR.exists():
           files.extend(sorted(ARCHIVE_TASKS_DIR.glob("*.md")))
       return files
   ```

2. **ID 连续性检查跨文件**：`check_sequential_ids()` 遍历热文件 + 所有归档文件（按版本顺序），构建完整的 ID 序列后再检查连续性。

3. **新增 `check_archive_integrity()`**（Check 26）：
   - 归档文件的条目数之和 + 热文件的条目数 = 索引中记录的条目总数
   - archive/index.md 中每个条目指向的归档文件确实存在
   - 归档文件中的条目在 index.md 中都有对应记录

### 5.2 向后兼容性

- 如果 `archive/` 目录不存在 → 所有现有行为不变（回退到单文件模式）
- 新项目初始化时 `archive/` 目录为空 → 行为与当前完全一致
- 旧项目未执行迁移 → 无 `archive/` 目录 → 行为与当前完全一致

---

## 6. 迁移方案

### 6.1 本项目迁移（168 task 首次归档）

**目标**：将当前 449 KB 治理数据按分层模型拆分。

**迁移步骤**（不写实现代码，定义步骤——交给 Developer）：

```
Phase 1: 创建 Git 回滚点
  └─ git commit -m "pre-archive: snapshot before governance data migration"
     （不 push——仅在本地创建回滚点）

Phase 2: 分析当前版本边界
  ├─ 解析 plan-tracker.md 中所有版本标题
  ├─ 识别每个版本的 task 列表（从版本标题到下一个版本标题之间）
  └─ 确定归档版本范围：v0.11.0 ~ v0.24.0（已发布的版本）

Phase 3: 创建归档文件
  ├─ 创建 archive/tasks/v0.11.0~v0.24.0.md
  │   └─ 从 plan-tracker.md 提取 v0.11.0~v0.24.0 的所有 task 表段落
  │   └─ 添加标准化文件头
  ├─ 创建 archive/evidence/v0.11.0~v0.24.0.md
  │   └─ 从 evidence-log.md 提取对应该版本 task 的证据条目
  │   └─ 添加标准化文件头
  └─ 创建 archive/decisions/（当前不需要——所有决策 < 2 年）

Phase 4: 验证归档完整性（Dry-Run）
  ├─ 对比：归档文件中的 task 数 + 将在热文件中保留的 task 数 == 迁移前 task 总数
  ├─ 对比：归档文件中的 evidence 条目数 + 将在热文件中保留的 evidence 条目数 == 迁移前 evidence 总数
  └─ 生成差异报告——如有不一致 → 终止迁移，人工检查

Phase 5: 从热文件移除已归档内容
  ├─ 从 plan-tracker.md 删除已发布版本的 task 表（保留版本标题 + "已归档"标记）
  ├─ 从 evidence-log.md 删除已归档版本的证据条目
  └─ 保留"当前活跃事项"中的未完成任务

Phase 6: 创建索引文件
  ├─ 创建 archive/index.md
  └─ 为每个归档条目生成索引行

Phase 7: 最终验证
  ├─ 运行 verify_workflow.py check-governance → 全部 PASS
  ├─ 运行 verify_workflow.py check-archive-integrity → PASS
  └─ 人工验证：打开 archive/ 目录下的 Markdown 文件确认可读性

Phase 8: 创建迁移完成 commit
  └─ git commit -m "SYSGAP-030: first governance data migration — 168 tasks archived"
```

**迁移后预期效果**：

| 指标 | 迁移前 | 迁移后 | 改善 |
|------|--------|--------|------|
| plan-tracker.md 大小 | 193 KB | ~60 KB | -69% |
| evidence-log.md 大小 | 163 KB | ~50 KB | -69% |
| decision-log.md 大小 | 74 KB | 74 KB | 不变 |
| risk-log.md 大小 | 19 KB | 19 KB | 不变 |
| **每次会话必读量** | **449 KB** | **~203 KB** | **-55%** |
| archive/ 目录大小 | 0 | ~306 KB | 新增 |

> 迁移后每次会话必读量从 449 KB 降到 ~203 KB（-55%），低于 120 KB 目标还需进一步归档。1000-task 规模下通过持续增量归档可达到目标。

### 6.2 幂等性保证

迁移脚本必须满足以下幂等性要求：
- 重复执行同一迁移不产生重复归档条目
- 检测到已有归档条目 → 跳过
- 检测到归档文件已存在 → 追加模式（仅追加新条目，不覆盖）

---

## 7. 蓝军挑战

### 蓝军挑战 #1: Agent 在 bootstrap 阶段遗漏归档数据，导致误判 Gate 状态

**场景**：归档后首次会话，Agent 只读了 `plan-tracker.md` 热数据，没有发现某个已完成 task 的证据在归档文件中，错误判定"Gate 未通过——缺少证据"。

**影响**：Agent 向用户错误报告 Gate 状态，可能引发不必要的补救行动。

**缓解措施**：
1. CLAUDE.md bootstrap 指令中明确写入归档感知逻辑——"先在热文件查，找不到再查 archive/index.md"
2. `plan-tracker.md` 热数据中保留"已完成 task → 已归档"的标记——agent 看到此标记就知道不需要在热文件中找 evidence
3. verify_workflow.py `check_evidence_completeness()` 自动跨热文件 + 归档文件检查——不依赖 agent 自觉
4. bootstrap SELF-CHECK 新增一步："确认所有已完成 task 的 evidence 状态——如有 task 标记为已归档但索引中无对应证据 → 记录到 risk-log"

**残余风险**：Agent 在多文件读取时可能遗漏某个归档文件的某个段落。通过 verify_workflow.py 外部验证兜底——agent 误判 Gate 状态的机会窗口仅限于两次 verify 运行之间。

### 蓝军挑战 #2: 跨版本 task 依赖链断裂

**场景**：Task A（v0.32.0）依赖 Task B（v0.24.0，已归档）。A 在 plan-tracker.md 中，B 在 archive/tasks/v0.21.0~v0.24.0.md 中。Agent 只读热文件时看不到 B 的状态，错误判定"依赖项 B 不存在或未完成"。

**影响**：Agent 可能拒绝开始 Task A，或错误地尝试查找已被归档的依赖项。

**缓解措施**：
1. **依赖链保留在热文件中**：plan-tracker.md 中的"依赖链"段落（如 `## 1.0.0 依赖链`）保留所有未完成 task 的依赖关系，即使依赖的 task 已归档，依赖边仍然记录在热文件中
2. **归档索引加速跨文件查询**：Agent 在遇到跨版本依赖时，可通过 `archive/index.md` 快速定位被依赖 task 的归档文件
3. **归档文件中保留 task 间依赖关系**：归档文件中的 task 表保留"依赖"列，形成完整的跨文件依赖图
4. **"跨版本依赖"标记**：在 plan-tracker.md 的依赖链中，对已归档的依赖项显式标记 `（已归档 → archive/tasks/vX~Y.md）`——agent 一眼就知道去哪里找

**残余风险**：如果依赖链嵌套多层（A 依赖 B，B 依赖 C，C 又在另一个归档文件中），agent 可能需要进行多次查询。通过索引的一步定位（index → 归档文件）将每次查询限制为 2 次 Read call。

### 蓝军挑战 #3: 归档操作本身引入数据不一致

**场景**：迁移脚本执行过程中崩溃或出错——部分 task 已从 plan-tracker.md 移除但归档文件中缺少对应条目，或索引文件与归档文件不一致。

**影响**：治理数据丢失或不一致，verify_workflow.py 检查失败。

**缓解措施**：
1. **三阶段原子事务**（与 FAQ Q5 一致）：Phase 1 写归档文件（主文件未改）→ Phase 2 验证 → Phase 3 从主文件删除。任何阶段失败可安全回滚
2. **Git 回滚点**：Phase 1 之前创建 git commit——最坏情况 `git checkout` 恢复
3. **Dry-run 模式**：迁移脚本提供 `--dry-run` 模式——先模拟归档并输出差异报告，用户确认后再执行
4. **verify_workflow.py 新增 `check_archive_integrity()`**——自动检测以下不一致：
   - 归档文件中的条目总数 + 热文件中的条目总数 != 索引记录的条目总数
   - 索引中有指向不存在归档文件的引用
   - 归档文件中存在未在索引中记录的条目
5. **幂等性保证**：重复执行迁移不会产生重复条目

**残余风险**：如果 Phase 3 中间崩溃（主文件"部分删除"），最坏情况需要 git checkout 恢复。因为 Phase 1 之前已创建 commit，恢复成本 = 一次 git checkout（< 1 秒）。

### 蓝军挑战 #4: 索引文件自身膨胀，成为新的瓶颈

**场景**：10000-task 项目——索引文件包含 10000 行 task 索引 + 10000 行 evidence 索引 = 20000 行 ≈ 1 MB。索引本身成为"每次会话必读"的负担。

**影响**：索引文件从"小而高效"退化为新的膨胀源。

**缓解措施**：
1. **索引分级**：当索引超过 200 KB 时，自动拆分为"活跃索引"（最近 2 个版本的条目）和"历史索引"（更早版本）
2. **活跃索引 < 50 KB**：仅包含最近 2 个版本的条目——这是 bootstrap 阶段最可能需要查询的范围
3. **历史索引按需读取**：仅在活跃索引中找不到目标条目时才读取历史索引
4. **索引压缩**：索引表格可以省略部分字段（如"状态"列对已归档条目没有信息增量），减小单行大小
5. **这不是本任务要解决的问题**：10000-task 是"未来问题"——当前设计在 1000-task 规模下已验证索引 < 50 KB。如果未来达到该规模，分层模型可通过参数调整演进

**残余风险**：如果项目确实达到 10000+ task 且索引分级后仍超标——那是另一个 SYSGAP，需要引入"归档文件的归档"。当前设计具有可演进性（参数可配置），不硬编码索引结构。

---

## 8. 非功能需求对应方案

| 维度 | 评估 | 设计措施 |
|------|------|---------|
| **性能** | 每次会话读取 < 120 KB | 热数据精确定义——plan-tracker 仅保留活跃段（~65 KB）+ evidence 保留当前版本（~25 KB）= ~90 KB。加上决策和风险 ~93 KB，合计 ~183 KB。通过 bootstrap "按段读取"指令（仅读热段落），实际读取量控制在 120 KB 以内 |
| **可靠性** | 归档操作原子化 | 三阶段事务 + Git 回滚点 + Dry-run 模式 + verify_workflow.py check_archive_integrity |
| **可维护性** | 归档规则简单可解释 | 三级优先级规则明确——版本发布（主）+ 增量归档（减负）+ 90天兜底（安全网）。所有规则是可枚举的布尔条件，无启发式判断 |
| **兼容性** | 向后兼容 | 无 `archive/` 目录时回退到单文件模式；ID 命名规范不变；表格结构不变；新项目初始化时 archive/ 为空目录 |
| **可扩展性** | 支持 1000→10000 task | 分层参数可配置（热数据大小上限、归档触发 N 天）；索引分级机制预留；归档文件链支持无限追加 |
| **人类可读性** | Markdown 格式保持不变 | 归档文件仍是 Markdown + 标准化文件头；索引是 Markdown 表格；任何编辑器可直接打开阅读 |

---

## 9. 风险评估

| 风险 | 级别 | 缓解 | 残余 |
|------|------|------|------|
| **Agent 多文件读取不可靠** | 高 | CLAUDE.md 明确指令 + SELF-CHECK + verify 兜底 | 依赖 agent 自觉——H6 待原型验证 |
| **跨版本依赖引用断裂** | 中 | 依赖链保留在热文件 + 归档文件保留依赖列 + 索引定位 | 深层嵌套依赖可能需要多次查询 |
| **迁移脚本 Bug 导致数据丢失** | 高 | 三阶段事务 + Git 回滚 + Dry-run + 幂等性 | Phase 3 中间崩溃 → git checkout 恢复 |
| **索引与归档不一致** | 中 | check_archive_integrity + 索引自动生成（非手动维护） | 脚本 bug ——通过 verify 检测 |
| **热/温/冷边界漂移** | 低 | 热数据大小持续监控 + 参数可调整 | 超大项目中边界可能需重新定义 |

---

## 10. 影响范围

### 新增文件
| 文件 | 说明 |
|------|------|
| `.governance/archive/` | 归档目录 |
| `.governance/archive/index.md` | 归档索引（Markdown 表格） |
| `.governance/archive/tasks/` | Task 归档文件目录 |
| `.governance/archive/evidence/` | Evidence 归档文件目录 |
| `.governance/archive/decisions/` | Decision 归档文件目录（预留） |
| `.governance/archive/risks/` | Risk 归档文件目录（预留） |
| `skills/software-project-governance/infra/archive.py` | 归档迁移脚本 |
| `skills/software-project-governance/infra/tests/test_archive.py` | 归档脚本的单元测试 |

### 修改文件
| 文件 | 改动内容 |
|------|---------|
| `CLAUDE.md` | Step 1-2 读取指令——增加热段落列表 + 归档感知逻辑 |
| `commands/governance-init.md` | Step 7 bootstrap 模板——读取指令同步更新 |
| `skills/software-project-governance/infra/verify_workflow.py` | 多文件数据源抽象 + check_archive_integrity 新增 + 现有 check 数据源改造 |
| `.governance/plan-tracker.md` | 已发布版本内容移除（迁移后） |
| `.governance/evidence-log.md` | 已归档证据条目移除（迁移后） |
| `skills/software-project-governance/core/manifest.json` | 新增 archive/ 目录声明 |

### 不受影响的部分
- decision-log 当前不归档（< 2 年）
- risk-log 当前不归档（< 200 条）
- session-snapshot.md（不受归档影响）
- agent-locks.json（运行时状态，不归档）
- 所有 SKILL/SKILL.md 和 agents/ 文件

---

## 11. 后续动作

| # | 动作 | 负责人 | 优先级 |
|---|------|--------|--------|
| 1 | **ADR 审查**——Design Reviewer（老洪）独立审查本 ADR | Coordinator → Design Reviewer | P0 |
| 2 | **原型验证 H6**——修改 CLAUDE.md 为多文件读取指令，在 3 个场景测试 agent 启动行为 | Analyst / Developer | P0 |
| 3 | **实现归档脚本**——archive.py（三阶段事务 + Dry-run + 幂等） | Developer | P0 |
| 4 | **实现 verify_workflow.py 升级**——GovernanceDataSource 抽象 + check_archive_integrity | Developer | P0 |
| 5 | **修改 CLAUDE.md bootstrap**——按本 ADR 4.5 节更新读取指令 | Developer | P0 |
| 6 | **本项目首次迁移**——执行 168 task 归档（6.1 节步骤） | Developer + QA | P0 |
| 7 | **归档后验证**——verify_workflow.py 全部 PASS + 人工验证归档文件可读性 | QA | P0 |
| 8 | **governance-init.md 模板更新**——新增 archive/ 目录模板 + bootstrap 模板同步 | Developer | P1 |
| 9 | **test_archive.py**——归档脚本的单元测试 | QA | P1 |

---

## 附录 A: 指标验证矩阵

| 指标 | 目标值 | 本方案预期值（1000-task） | 验证方式 |
|------|--------|--------------------------|---------|
| 每次会话必读治理数据量 | **< 120 KB** | ~120 KB（热 plan-tracker 65 KB + 热 evidence 25 KB + decision 18 KB + risk 10 KB） | 测量 bootstrap 实际 Read 调用字节数 |
| Token 预算占用比 | **< 50K (< 5%)** | ~48K | 基于必读数据量的 tokens 估算 |
| 热数据文件总大小 | **< 500 KB** | ~203 KB（plan-tracker 65 KB + evidence 50 KB + decision 74 KB + risk 19 KB - 不含 bootstrap 不读的段落） | 测量文件系统大小 |
| verify_workflow.py 全量检查 | **全部 PASS** | 全部 PASS | 运行 check-governance |
| 人类可读性 | **保持** | 保持——归档文件是独立 Markdown | 人工验证 |

---

## 附录 B: 与其它架构决策的关系

| 关联 ADR/决策 | 关系 | 说明 |
|-------------|------|------|
| V-Gate（版本规划纪律） | 依赖 | 归档触发依赖版本发布流程——V-Gate 通过 = 归档触发 |
| DEC-052（4 层分层推进模型） | 对齐 | 归档不影响 Layer 推进顺序——归档是数据管理层操作，与功能开发层解耦 |
| CLAUDE.md bootstrap（DEC-037） | 修改 | bootstrap 读取指令是本 ADR 的核心修改目标之一 |
| verify_workflow.py（DEC-023） | 增强 | 本 ADR 为 verify_workflow.py 新增归档感知能力，不改变现有检查逻辑 |
