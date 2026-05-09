# ADR-007: 治理数据升级迁移流程 —— 用户和狗粮项目统一升级路径

**日期**: 2026-05-10
**状态**: 提案（已修复 B1+B2——待重新审查）
**决策人**: Architect（老顾）
**关联任务**: SYSGAP-030 Phase 2
**前置 ADR**: ADR-006（治理数据伸缩性——版本归档 + 索引混合方案，已实现 Phase 1 基础设施）
**影响范围**: CLAUDE.md bootstrap 自升级序列（新增 Step E）+ archive.py CLI（新增 --auto 模式）+ governance-init.md 模板（新项目自动带归档结构）+ 本项目首次归档迁移
**可逆性**: 高（归档脚本已有 rollback 命令 + git 回滚点 + dry-run 模式）

---

## 1. 背景

### 1.1 SYSGAP-030 Phase 1 完成状态

ADR-006（治理数据伸缩性）的 Phase 1 基础设施已落地：

| 组件 | 文件 | 状态 |
|------|------|------|
| 归档脚本 | `skills/software-project-governance/infra/archive.py` | 已实现——migrate / build-index / verify / rollback 四个子命令 |
| 多文件数据源 | `verify_workflow.py` 中的 `GovernanceDataSource` | 已实现——透明聚合热文件 + 归档文件 |
| 归档完整性检查 | `verify_workflow.py` Check 26 | 已实现——index-archive consistency + orphan detection |
| 归档目录结构 | `.governance/archive/tasks/`, `evidence/`, `decisions/`, `risks/` | 已创建——均为空（仅有 .gitkeep） |
| 单元测试 | `infra/tests/test_archive.py` | 已实现——16 tests |

**关键缺口**：`archive/index.md` 不存在——归档从未执行。用户更新插件后，治理文件不会自动迁移——plan-tracker 和 evidence-log 继续膨胀。

### 1.2 问题陈述

当前升级路径（CLAUDE.md bootstrap 版本变化检测，Step A~D）处理了以下升级动作：
- A: 输出更新摘要
- B: 自动升级 bootstrap 段
- C: 自动补全 plan-tracker 缺失结构
- D: 更新工作流版本号

**但归档迁移缺失**——这是 SYSGAP-030 的"最后一公里"：基础设施已有，但用户不会主动执行归档。归档迁移必须像 bootstrap 自升级一样**零用户操作、自动触发**。

### 1.3 当前项目规模

| 文件 | 大小 | 内容 |
|------|------|------|
| plan-tracker.md | ~101 KB | 169 tasks，31 个已发布版本 |
| evidence-log.md | ~106 KB | 286+ 条证据 |
| decision-log.md | ~74 KB | 60 条决策 |
| risk-log.md | ~19 KB | 28 条风险 |
| **合计** | **~300 KB** | |

> 注：ADR-006 中引用的 plan-tracker 193 KB 为更早的测量值（含大量历史审计 task 表），当前为 101 KB。但增长率趋势不变——如不归档，6 个月后将远超阈值。

### 1.4 设计约束

| # | 约束 | 来源 |
|---|------|------|
| C1 | 升级流程嵌入现有 bootstrap 自升级序列——不引入新触发路径 | 用户零操作原则 |
| C2 | 归档检测条件必须精确可判定——无启发式、无模糊匹配 | 自动化可靠性 |
| C3 | 归档后 CLAUDE.md 读取指令必须保持全部治理功能——交叉验证、Gate 检查、风险检测不退化 | 功能不减原则 |
| C4 | 向后兼容——老版本用户不触发归档时行为不变 | 兼容性原则 |
| C5 | 可逆——归档出错时可通过 rollback 恢复 | 安全原则 |
| C6 | 归档不依赖 archive.py 的 --auto 标志存在（首次触发时可能尚未安装新版）——检测条件仅依赖文件系统状态 | bootstrap 自举原则 |

---

## 2. 方案评估

### 2.1 方案 A：bootstrap Step E —— 嵌入版本变化检测序列（推荐）

**核心思路**：在现有 bootstrap "版本变化自动检测" 序列（Step A~D）之后新增 Step E：归档迁移检测与执行。版本 bump 是自然的升级触发器——用户更新插件后首次会话即为最佳归档时机。

**优势**：
- 复用现有触发路径——不需要新机制
- 零用户操作——与 bootstrap 自升级相同的交互模型
- 检测条件基于文件系统状态（index.md 存在？plan-tracker 大小？已发布版本数？）——不依赖 archive.py 版本
- 输出格式与 Step A 更新摘要一致——用户感知统一

**挑战**：
- bootstrap 段变长——需控制新增行数
- 归档失败时需清晰错误处理——不能因归档失败阻塞 bootstrap

### 2.2 方案 B：Scenario C 升级流程中嵌入归档检测

**核心思路**：在 `/governance` 命令的 Scenario C（工作流升级）中增加归档检测步骤。

**排除理由**：
- Scenario C 依赖 `/governance` 命令被显式调用——而 bootstrap 自升级每次会话自动执行。归档迁移的触发频率与 bootstrap 一致（版本 bump 时触发一次），嵌入 Scenario C 意味着用户升级后必须主动运行 `/governance` 才能触发归档——违反"零用户操作"原则。
- Scenario C 本身已足够复杂——再嵌入归档检测加重认知负担。

### 2.3 方案 C：post-commit hook 检测归档需求

**核心思路**：在 post-commit hook 中检查 plan-tracker 大小，超过阈值时输出提醒。

**排除理由**：
- Hook 不能修改治理文件——职责边界（hook 是阻断/报告，不是迁移）
- 用户看到提醒后仍需主动操作——违反零用户操作原则
- Hook 在每次 commit 后运行——归档检测逻辑的触发频率远高于实际归档频率（归档一次即可），浪费 hook 执行时间

### 2.4 方案对比

| 评估维度 | 方案 A: Bootstap Step E | 方案 B: Scenario C | 方案 C: Post-commit hook |
|---------|------------------------|-------------------|------------------------|
| 触发时机 | 版本 bump 自动 | 需用户主动调用 | 每次 commit |
| 零用户操作 | **是** | 否 | 否（仅提醒） |
| 与新机制耦合 | 无——复用现有路径 | 无——但需新触发 | 无 |
| 实现复杂度 | 低（~30 行新增 bootstrap） | 中 | 低 |
| 错误容错 | 高（归档失败不阻塞 bootstrap） | 中 | 低（hook 失败影响 commit） |
| 用户感知统一性 | **好**（与 A~D 格式一致） | 一般 | 差（提醒后需手动操作） |

---

## 3. 决策

**采用方案 A：bootstrap Step E —— 归档迁移检测嵌入版本变化自动检测序列**。

### 3.1 选择理由

1. **复用现有触发路径**：版本 bump 是 bootstrap 已有的自动检测序列——用户更新插件后首次会话必然触发版本变化检测。归档迁移嵌入此序列零额外触发成本。

2. **零用户操作**：归档迁移执行模式与 Step B（自动升级 bootstrap）、Step C（自动补全 plan-tracker 结构）一致——检测到条件满足后自动执行，输出摘要告知用户。

3. **检测与执行解耦**：检测条件仅依赖文件系统状态（C6 约束），不依赖 archive.py 版本。即使新版本归档脚本尚未生效，检测逻辑也能正确判断"需要归档但脚本不可用"的边界情况。

4. **错误不阻塞 bootstrap**：归档失败（脚本执行错误、文件权限问题等）记录到 risk-log 但不阻塞 bootstrap 其余步骤。用户不会被"归档失败"打断。

### 3.2 排除备选方案的详细理由

| 方案 | 排除理由 |
|------|---------|
| 方案 B（Scenario C） | 依赖用户主动调用 `/governance`——违反零用户操作原则。Scenario C 已承担升级摘要、bootstrap 替换、结构补全、hook 检测等多项职责，再嵌入归档检测加重认知负担 |
| 方案 C（Post-commit hook） | Hook 职责边界——只阻断/报告，不修改治理文件。每次 commit 都运行归档检测浪费 hook 时间。用户被提醒后仍需手动操作 |

---

## 4. 详细设计

### 4.1 归档检测条件（精确规则）

在版本 bump 检测到 `当前版本 > 记录版本` 后，执行以下三个条件检查。**全部满足**才触发归档：

```
条件 1: .governance/archive/index.md 不存在
  判定方式: 文件不存在（os.path.exists 返回 False 或等效文件系统检查）
  含义: 归档从未执行过——这是首次归档
  
条件 2: plan-tracker.md 文件大小 > 80 KB
  判定方式: 文件系统字节数 > 81920
  含义: 治理数据已膨胀到值得归档的规模
  设计理由: 80 KB 大约对应 60+ 个 task（含 task 表行 + 版本描述）。小于此规模的项目归档收益极低（热/冷分离开销 > 收益），不值得触发
  
条件 3: plan-tracker.md 的版本路线图中有 ≥ 2 个"已发布"版本
  判定方式: 在 `## 版本规划` 节下查找 `### 版本路线图` 子标题中的表格，统计 `| 状态 |` 列为"已发布"的行数
  降级搜索: 如果按上述路径找不到 `### 版本路线图`（例如 plan-tracker 结构差异），降级为全文件搜索任意包含"版本路线图"的 Markdown 标题，再解析其下的表格
  含义: 有可归档的历史版本（至少一个版本已完成并发布）
  设计理由: 如果只有 1 个已发布版本，意味着当前活跃版本尚未发布——归档没有意义
```

**三条件全部满足 → 触发归档**。任一条件不满足 → 跳过，输出"归档条件未满足"（可选——仅 always-on 模式输出）。

**设计原理**：
- 条件 1 确保幂等——归档执行后 index.md 被创建，下次版本 bump 不会再触发
- 条件 2 防止小项目无意义的归档操作——归档的成本（修改热文件 + 创建归档文件 + 构建索引）在小于 80 KB 的 plan-tracker 上不划算
- 条件 3 确保有可归档的内容——所有版本都在进行中的项目没有可归档数据
- 三个条件是**纯文件系统状态检查**——不依赖 archive.py 的任何函数。满足 C6 约束

### 4.2 Bootstrap Step E 流程（伪代码级）

```
Step E: 归档迁移检测与执行

E.1 检测归档条件
    IF .governance/archive/index.md 存在 → 跳过（归档已执行）
    IF plan-tracker.md 文件大小 <= 80 KB → 跳过（数据量不足以触发归档）
    IF 版本路线图中"已发布"版本 < 2 → 跳过（无可归档的历史版本）
    → 否则，进入 E.2

E.2 检查归档脚本可用性
    IF skills/software-project-governance/infra/archive.py 不存在 → 
        输出 "⚠️ 归档脚本不可用——跳过归档迁移。更新到最新版本后自动重试。"
        记录到 risk-log（RISK-XXX: 归档脚本缺失——升级包可能不完整）
        → RETURN（不阻塞 bootstrap）
    IF python 不可用 → 同上

E.3 执行归档迁移
    运行: python skills/software-project-governance/infra/archive.py migrate --auto
    
    --auto 模式行为（见 4.3 节）：
      a. 解析 plan-tracker.md 版本路线图，获取"已发布"版本列表
      b. 确定归档版本范围：最早已发布版本 → 倒数第二个已发布版本
         （保留最新已发布版本在热文件中——因为当前活跃版本可能依赖其 task）
      c. 如果归档范围为空（只有 1 个版本有 task 数据）→ 输出提示，跳过归档
      d. 执行 migrate_by_version(start, end, migrate_evidence=True)
      e. 执行 build_index()
      f. 执行 verify_archive_integrity()
      g. 返回迁移结果摘要

E.4 处理执行结果
    IF migrate 成功 AND verify PASS:
      输出迁移摘要（格式见 4.4 节）
      → 继续 Step D（更新版本号）
    
    IF migrate 成功 BUT verify FAIL:
      输出 "⚠️ 归档完成但索引完整性检查未通过。运行 python ... verify 查看详情。"
      记录到 risk-log
      → 继续 Step D（不阻塞版本升级）
    
    IF migrate 失败（脚本异常、文件权限等）:
      输出 "⚠️ 归档迁移失败: {error_message}。下次会话将自动重试。"
      记录到 risk-log: RISK-XXX（归档迁移失败）
      → 继续 Step D（不阻塞版本升级）

E.5 边界情况处理
    IF plan-tracker.md 在归档过程中被外部修改（git checkout 等）:
      archive.py 内部检测文件变化 → abort with rollback
    IF 归档文件写入磁盘空间不足:
      Python IOError → 捕获 → 回滚 → 输出错误
```

**关键设计决策**：
- 归档失败**不阻塞** bootstrap 其余步骤——bootstrap 的核心职责是 agent 初始化，归档是优化。优化失败不应阻止 agent 启动
- 归档失败记录到 risk-log——确保下次会话可被治理诊断（Scenario E）检测到
- `--auto` 模式内部处理所有边界情况（见 4.3 节）——bootstrap 层仅负责检测和调用，不处理归档内部逻辑

### 4.3 archive.py --auto 模式设计

`--auto` 是 `archive.py migrate` 子命令的新增标志。设计为"零参数自动迁移"——自动检测版本边界并执行全量归档。

```
--auto 模式执行流程（伪代码）:

def migrate_auto():
    """
    自动检测已发布版本边界，执行首次归档迁移。
    
    检测逻辑:
    1. 解析 plan-tracker.md: 在 `## 版本规划` 下查找 `### 版本路线图` 子标题中的表格。
       降级: 如果找不到，全文件搜索任意包含"版本路线图"的 Markdown 标题
    2. 提取状态为"已发布"的版本列表（按 semver 排序）
    3. 排除最新已发布版本（保留在热文件中）
    4. 确定归档范围 = [最早已发布版本, 倒数第二已发布版本]
    5. 如果归档范围内无 task 数据 → 跳过（输出提示）
    
    边界处理:
    - 版本路线图不存在 → 降级为解析 plan-tracker 中的版本标题，取所有标题中的版本
    - 已发布版本数 < 2 → 无归档范围，跳过
    - 版本范围跨越过大（> 30 个版本）→ 分批归档（每批 ≤ 15 个版本），避免单次操作过大
    
    Returns:
        dict: 迁移结果摘要，包含:
            - versions_archived: [version_str, ...]
            - versions_range: "v{start}~v{end}"
            - tasks_archived: int
            - evidence_archived: int
            - plan_tracker_before: int (bytes)
            - plan_tracker_after: int (bytes)
            - archive_files_created: [str, ...]
            - verify_pass: bool
    """
    
    # Step 1: 解析版本路线图
    versions = parse_version_roadmap()  # 返回 [(version, status), ...]
    published = [v for v, s in versions if s == "已发布"]
    published.sort(key=semver_sort)
    
    # Step 2: 确定归档范围
    if len(published) < 2:
        return {"skipped": True, "reason": "少于 2 个已发布版本"}
    
    archive_versions = published[:-1]  # 除最新版本外的所有已发布版本
    
    # Step 3 (pre-check): dry-run 预览——确认至少能识别到可归档的 task，不修改任何文件
    version_start = archive_versions[0]
    version_end = archive_versions[-1]
    
    dry_result = migrate_by_version(version_start, version_end, dry_run=True, migrate_evidence=True)
    
    if dry_result.get("tasks_archived", 0) == 0:
        return {"skipped": True, "reason": "归档版本范围内无可归档的已完成 task"}
    
    # 安全特性声明: migrate_by_version 内部仅归档状态为"已完成"的 task——
    # 进行中/待执行/阻塞中的 task 不会被误归档。
    # 版本范围 [start, end] 内可能包含非"已发布"版本（如路线图中标记为"进行中"的版本），
    # 但这些版本中状态为"已完成"的 task 理应归档——已完成的历史 task 无论所属版本状态如何都应冷存储。
    # 进行中的 task 安全保留在热文件中。这是优于"按版本列表过滤"的设计选择。
    
    # Step 4: 执行迁移
    result = migrate_by_version(version_start, version_end, dry_run=False, migrate_evidence=True)
    
    # Step 5: 构建索引
    if result["success"]:
        build_index()
        verify_result = verify_archive_integrity()
        result["verify_pass"] = verify_result["pass"]
    
    # Step 6: 计算大小变化
    result["plan_tracker_before"] = ...  # 从备份或迁移前快照获取
    result["plan_tracker_after"] = os.path.getsize(plan_tracker_path)
    
    return result
```

**--auto vs 手动 migrate 的区别**：

| 维度 | `migrate v0.1.0 v0.31.0` | `migrate --auto` |
|------|--------------------------|-------------------|
| 版本范围 | 用户显式指定 | 自动从版本路线图解析 |
| 错误处理 | 参数无效 → exit 1 | 自动降级 / 跳过 / 提示 |
| 适用场景 | 开发者手动运维 | bootstrap 自动调用 |
| 幂等性 | 由 migrate_by_version 内部保证 | 额外检测——如果 index.md 已存在 → 跳过 |
| 输出格式 | 详细调试信息 | 简洁摘要（适合 bootstrap 输出流） |

### 4.4 迁移摘要输出格式

与 bootstrap Step A 更新摘要保持一致的输出格式：

```
📦 治理数据归档完成:
  - 归档范围: v0.11.0 ~ v0.31.0（{N}个版本）
  - 归档 {N} 个 task → archive/tasks/v0.11.0~v0.31.0.md
  - 归档 {M} 条证据 → archive/evidence/v0.11.0~v0.31.0.md
  - plan-tracker: {old_size}KB → {new_size}KB (-{pct}%)
  - evidence-log: {old_size}KB → {new_size}KB (-{pct}%)
  - 每次会话必读量: ~{new_read}KB
  - 索引: archive/index.md（{index_entries} 条目）
```

**输出触发条件**：
- always-on 模式 → 完整输出（如上）
- on-demand 模式 → 仅记录到 session-snapshot，用户调用 `/governance` 时展示
- silent-track → 静默执行，仅在失败时打断

### 4.5 CLAUDE.md bootstrap 读取指令修改

以下修改应用于 governance-init.md Step 7 的三个 profile 模板（lightweight/standard/strict）——此处以 standard profile 为例。

#### 4.5.1 Step 1 修改

**当前指令**（CLAUDE.md line 69-70）：
```
### Step 1: 读 plan-tracker + 跨会话恢复
读取 `.governance/plan-tracker.md`，确认：当前阶段、最近 Gate 结论、活跃风险数、进行中的 P0 任务。如果 `.governance/` 不存在，提醒用户先初始化。
```

**修改为**：
```
### Step 1: 读 plan-tracker + 跨会话恢复

1. 读取 `.governance/plan-tracker.md` 的热数据段落（按以下优先级）:
   a. `## 项目配置` — 当前 phase/stage/gate/mode/permission_mode/工作流版本
   b. `## Gate 状态跟踪` — 所有 Gate 状态
   c. `## 项目总览` — 当前统计（任务数/已完成/阻塞中/风险数）
   d. `## 当前活跃事项` — 仅未完成/进行中的 P0/P1/P2 任务
   e. 当前活跃版本的 task 表 — 版本描述中含"进行中"或"未发布"的段落
   f. `## 1.0.0 依赖链` 或等效的活跃依赖链
   — 以下段落按需读取（不在 bootstrap 阶段强制读取）:
   g. `## 需求跟踪矩阵`
   h. `## 变更控制`
   i. `## 版本规划` 中的"规划纪律"部分
   j. 版本规划中的"里程碑"和"版本路线图"

2. **归档感知**：
   — IF `.governance/archive/index.md` 存在:
     a. 读取 `archive/index.md`——了解已归档条目的位置
     b. 后续交叉验证时，如果 evidence-log.md 中找不到某 task 的证据 → 先查 index.md
     c. **归档文件中的证据 = 有效证据——不可误判为缺失**

3. 读取 `.governance/session-snapshot.md`（如存在），对照 plan-tracker：
   ...（同现有指令）

4. 跨会话状态恢复 / 脱轨检测 / Hook 存活检测：
   ...（同现有指令）
```

**关键改动**：
- 明确热数据段落列表——agent 知道哪些必须读、哪些按需读
- 新增归档感知逻辑——先查 index.md，再判定缺失
- 归档文件中的证据 = 有效证据——此条防止"交叉验证误报缺失证据"

#### 4.5.2 Step 2 修改

**当前指令**（CLAUDE.md line 109-116）：
```
### Step 2: 交叉验证（3 项强制检查）
对照 `.governance/plan-tracker.md` 和 `.governance/evidence-log.md`：

1. **证据完整性**：plan-tracker 中状态为"已完成"的任务，evidence-log 中是否有对应证据？缺失 → **检查 profile**：lightweight 不强制证据（信息提示），standard/strict = P0 漏洞。
2. **Gate 一致性**：plan-tracker 的 Gate 状态与 evidence-log 的最新证据是否匹配？Gate 标记 passed 但无对应证据 = 不一致，告知用户。
3. **风险过期**：risk-log 中活跃风险超过 7 天未更新？是 = 标记为过期风险，告知用户。

任一检查失败 → 列出差距 → 征求用户是否立即修复（AskUserQuestion）。
```

**修改为**：
```
### Step 2: 交叉验证（3 项强制检查）

对照 `.governance/plan-tracker.md`（热数据）和 `.governance/evidence-log.md`（热数据）：

1. **证据完整性**：
   a. plan-tracker 热数据中标记为"已完成"的任务 → 先查 evidence-log.md 热数据
   b. 缺失 → 查 `.governance/archive/index.md`（如存在）→ 定位归档文件
   c. 归档文件中存在 = 有效证据——不标记为缺失
   d. 热文件 + 归档文件中均缺失 → **检查 profile**：lightweight 不强制证据（信息提示），standard/strict = P0 漏洞
   
2. **Gate 一致性**：plan-tracker 的 Gate 状态与 evidence-log 的最新证据是否匹配？Gate 标记 passed 但无对应证据 = 不一致，告知用户。

3. **风险过期**：risk-log 中活跃风险超过 7 天未更新？是 = 标记为过期风险，告知用户。

**查询已归档 entry 的标准路径**：
   需要查询特定 task/evidence 的详细内容时:
   Step 1: Read `.governance/archive/index.md` → grep 目标 ID
   Step 2: 从 index.md 获取归档文件路径 → Read 该归档文件 → 定位具体条目
   总开销: 2 次 Read call

任一检查失败 → 列出差距 → 征求用户是否立即修复（AskUserQuestion）。
```

**关键改动**：
- 证据完整性检查新增两级查询（热文件 → 索引 → 归档文件）
- 归档文件中的证据明确标记为有效——防止误报
- 新增"查询已归档 entry 的标准路径"——agent 完成具体查询时按此路径操作

#### 4.5.3 版本变化自动检测序列修改

**当前指令**（CLAUDE.md line 81-104）Step A~D → 新增 Step E：

在 Step D 之前插入 Step E：
```
   **E. 归档迁移检测与执行**（用户更新插件后自动触发——零用户操作）：
   — 检测三条件:
     1. `.governance/archive/index.md` 不存在（归档从未执行）
     2. `plan-tracker.md` 文件大小 > 80 KB（治理数据已膨胀）
     3. plan-tracker 版本路线图中"已发布"版本 ≥ 2（有可归档的历史数据）
   — 三条件全部满足 → 执行:
     a. 运行 `python skills/software-project-governance/infra/archive.py migrate --auto`
     b. 输出归档迁移摘要（格式: 📦 治理数据归档完成: 归档{N}个task→..., plan-tracker: {old}KB→{new}KB(-{pct}%)）
     c. 归档失败不阻塞 bootstrap——记录到 risk-log，下次会话重试
   — 任一条件不满足 → 跳过归档（不输出，静默）
```

### 4.6 governance-init.md 模板修改

#### 4.6.1 Step 5 修改——新项目自动创建 archive/ 目录

在 Step 5（创建治理文件）的"创建 4 个治理记录文件"之后，新增：

```
### Step 5.5: 创建归档目录结构
- 创建 `.governance/archive/` 目录
- 创建子目录: `archive/tasks/`, `archive/evidence/`, `archive/decisions/`, `archive/risks/`
- 每个子目录中创建 `.gitkeep` 文件（空文件，确保目录可被 git 跟踪）
- **不**创建 `archive/index.md`——索引在首次归档时由 archive.py 自动生成
```

**设计理由**：
- 新项目初始化时就准备好归档目录——避免后续创建时的文件系统操作
- `.gitkeep` 确保空目录可被 git 跟踪——manifest.json 需要声明这些目录
- 不预创建 index.md——空索引是错误的信号（暗示归档已执行但无条目）

#### 4.6.2 Step 7 模板同步——bootstrap 模板新增 Step E + 归档感知 Step 1/2

lightweight / standard / strict 三个 profile 的注入模板均需同步以下修改：
1. Step 1 新增热数据段落列表 + 归档感知逻辑
2. Step 2 新增归档感知查询路径
3. 版本变化自动检测序列新增 Step E

**修改范围**（以 standard profile 为例，约 +25 行）：

```
Step 1 修改:
  当前: 69~70 行 → 修改为 ~85 行（+15 行：热数据段落列表 + 归档感知）

Step 2 修改:
  当前: 109~116 行 → 修改为 ~123 行（+7 行：证据两步查询 + 归档路径）

版本变化检测序列修改:
  当前: Step A~D（81~104 行）→ 修改为 Step A~E（81~118 行，+14 行：Step E 归档迁移检测）

总计新增: ~36 行
```

> 完整的三级模板 diff 见附录 A。

---

## 5. 蓝军挑战

### 蓝军挑战 #1: 归档检测在版本 bump 之前触发——archive.py 为新版本但 plan-tracker 仍是旧结构

**场景**：用户从 v0.32.0 更新到 v0.33.0（v0.33.0 首次包含 --auto 支持）。首次会话触发版本变化检测：Step C（补全 plan-tracker 缺失结构）在 Step E（归档迁移）之前执行。但 Step C 只补全结构性缺失（如 permission_mode 字段、版本规划节），不改变 task 表数据。Step E 的 `--auto` 模式需要解析版本路线图——如果版本路线图在 Step C 中被补全但数据为默认值（空表），归档条件 3（≥ 2 个已发布版本）无法满足 → 归档被跳过但不应跳过。

**影响**：首次升级时归档可能被跳过，需等下一个版本 bump 才触发。

**缓解措施**：
1. **Step C 不创建空版本路线图**：Step C "补全缺失结构"中，如果版本路线图不存在 → 创建空表（`| — | — | — | — | — | — |`），而非填充假数据。空表 → 条件 3 不满足 → 正确跳过（无历史版本数据可归档的情况本来就无需归档）
2. **条件 3 的备选路径**：如果版本路线图中无"已发布"版本（可能是 Step C 刚创建的空表），降级为解析 plan-tracker 中的版本标题（`### 0.XX.0 — ...`）——这些标题不会被 Step C 修改。如果存在 ≥ 2 个版本标题含 task 表 → 视为有可归档数据
3. **条件 1 是主 guard**：index.md 不存在是最可靠的"归档未执行"信号——不依赖 plan-tracker 结构

**残余风险**：极端情况下（版本路线图为空 + 版本标题 < 2 个），归档被错误跳过。通过条件 1 的后续会话会再次检测——因为 index.md 仍然不存在。

### 蓝军挑战 #2: 归档迁移执行期间 agent 读取了正在被修改的 plan-tracker.md

**场景**：bootstrap Step E 运行 `archive.py migrate --auto` 时，archive.py 正在修改 plan-tracker.md（删除已归档行 + 更新版本标题）。如果 bootstrap 的其他逻辑（如 Step 1 的 plan-tracker 读取、或 Agent Team 激活的 SKILL.md 加载）在归档脚本执行期间并发读取 plan-tracker.md，可能读到不一致的中间状态（部分行已删除、部分未删除）。

**影响**：agent 读取到不一致的 plan-tracker 状态，可能误判项目状态或 task 状态。

**缓解措施**：
1. **archive.py 的写操作是原子的**：`_plan_tracker().write_text("\n".join(final_lines), encoding="utf-8")` 是一次 write 调用——Python 的 write_text 在 POSIX 上是原子的（write + rename）。Windows 上虽非原子但操作时间极短（< 100ms for 100KB file）
2. **bootstrap 执行顺序保证**：Step E 在版本变化检测序列中位于 Step 1（读 plan-tracker）之后、Step D（更新版本号）之前。Step 1 已经完成了 plan-tracker 和 index.md 的初始读取——后续 Step E 修改 plan-tracker 不会影响已读取的数据
3. **Agent Team 激活在 Step 0.5——远早于 Step E**：SKILL.md 加载、Coordinator 身份注入在 Step E 之前已完成
4. **归档脚本先写归档文件、后删热文件**：Phase 1 写归档文件（plan-tracker 未变）→ Phase 2 验证 → Phase 3 从 plan-tracker 删除。即使在 Phase 3 中间读取，也只影响那些恰好正在被删除的 task 行——不会读到部分写入的归档文件

**残余风险**：Windows 上的非原子写入可能导致极短窗口内的不一致读取。概率极低（< 1 session per 1000），且不一致仅限于"某行 task 已删除但归档文件中有"——agent 查 index.md 可恢复。不需要额外的文件锁机制。

### 蓝军挑战 #3: 归档迁移后 verify_workflow.py 检查失败——归档过程引入数据不完整

**场景**：archive.py migrate --auto 在执行过程中因某种原因（如异常版本标题格式、task 表列数不一致、plan-tracker 中混合中文标点）未能正确识别所有 task 行。部分 task 未归档，或归档文件中的 task 行与 index.md 不一致。

**影响**：verify_workflow.py check-archive-integrity (Check 26) 失败，或更严重——部分 task 在热文件和归档文件中都找不到。

**缓解措施**：
1. **三阶段事务**（已在 archive.py 中实现）：写归档文件 → 验证 → 删除热文件行。任何阶段失败 → 归档文件不会写入 + 热文件不会被修改
2. **archive.py 内部 self-check**：migrate_by_version 返回结果中包含 `tasks_archived` 和 `tasks_remaining`——如果 `tasks_archived == 0`，不会创建归档文件也不会修改 plan-tracker
3. **--auto 模式增加 pre-check**：在执行迁移前，先做一次 dry-run 扫描——确认至少能识别到 task 行后再执行实际迁移
4. **verify_archive_integrity() 在迁移后自动执行**（--auto 模式内建）：如果 verify 失败 → 自动回滚
5. **回滚机制**：archive.py rollback 命令可撤销最近一次迁移——从归档文件恢复 task 行到 plan-tracker，删除归档文件，重建索引
6. **git 保护**：迁移前 create a git commit（由 Coordinator 在 Step E 之前通过 bootstrap 逻辑执行）——最坏情况 git checkout 恢复

**残余风险**：如果三阶段事务 + verify + 回滚全部失败且 git commit 未创建（Coordinator 遗漏）→ 需手动从 git reflog 恢复。通过 Makefile 或 hook 在执行 archive.py 前强制 snapshot 可进一步降低此风险（但超出本 ADR 范围——留给运维文档）。

### 蓝军挑战 #4: archive/index.md 本身膨胀——成为新的每次会话必读瓶颈

**场景**：多次归档后（1000-task 项目经过 10 次版本归档），index.md 包含了全部 1000 个 task 的索引行 + 1400 条 evidence 索引行 = 2400 行 ≈ 72 KB。索引读取成为每次会话的固定开销。

**影响**：索引从"轻量查询辅助"退化为"新的必读负担"——与归档的设计目标（减少每次会话必读量）矛盾。ADR-006 Blue Team Challenge #4 已识别此问题但标记为"未来问题"。

**缓解措施（本 ADR 新增）**：
1. **索引按需读取——不强制每次会话读取**：bootstrap Step 1 的归档感知指令修改为"IF index.md 存在 → 读取"改为"IF index.md 存在 → **仅了解其存在和结构**，不强制读取全文"。agent 仅在交叉验证发现证据缺失时查询索引
2. **索引表头+统计摘要**：index.md 增加可折叠结构和统计数据（如"总计 X 个已归档 task"），agent 可快速获取概况而不需读取全部行
3. **索引分级——当 index.md > 100 KB 时**：自动拆分为 `archive/index-active.md`（最近 N 个版本）和 `archive/index-historical.md`（更早版本）。bootstrap 仅读 active index
4. **这是演进性设计**：当前 index.md = 0 字节（尚未创建）。即使首次归档（本项目 ~100 task + ~150 evidence），index.md 约 250 行 ≈ 7.5 KB——远低于 100 KB 拆分阈值。索引膨胀在实际触发前不需要过度设计

**残余风险**：如果项目达到 5000+ task 且未触发索引分级 → index.md 可能 > 300 KB。通过 verify_workflow.py Check 26 增加索引大小告警（index.md > 100 KB → WARN）可提前感知。

---

## 6. 非功能需求对应方案

| 维度 | 评估 | 设计措施 |
|------|------|---------|
| **可靠性** | 归档操作三阶段事务 + 回滚 + git 保护 | Phase 1 写归档文件 → Phase 2 verify → Phase 3 删热文件。任何阶段失败 → 回滚到 safe state |
| **性能** | 归档执行 < 5 秒（100 KB plan-tracker） | archive.py 纯 Python 文本处理，无网络依赖。--auto 模式增加 pre-check dry-run（~1 秒），实际迁移（~3 秒） |
| **可用性** | 零用户操作——自动检测、自动执行、自动输出摘要 | 与 bootstrap Step A~D 一致的交互模型。失败不阻塞 bootstrap，记录 risk-log 用于后续诊断 |
| **兼容性** | 向后兼容——老版本不触发归档时行为不变；新项目初始化时 archive/ 为空目录 | 检测条件 1（index.md 不存在）确保归档只触发一次。无 archive/ 目录 → 所有行为与当前一致 |
| **可逆性** | archive.py rollback 命令可撤销最近迁移；git 回滚点 | rollback 从归档文件恢复 task 行到 plan-tracker，删除归档文件，重建索引 |
| **可维护性** | 归档检测条件是可枚举的布尔条件——无启发式判断 | 三个条件均为文件系统状态检查（文件存在、文件大小、表格行计数） |

---

## 7. 影响范围

### 7.1 产品代码修改

| 文件 | 改动类型 | 改动内容 | 负责人 |
|------|---------|---------|--------|
| `skills/software-project-governance/infra/archive.py` | 修改 | 新增 `--auto` 子命令（migrate --auto）——自动检测版本边界、pre-check dry-run、内建 verify + 自动回滚 | Developer |
| `skills/software-project-governance/infra/tests/test_archive.py` | 修改 | 新增 --auto 模式的测试用例：正常迁移/空范围/版本路线图缺失/无 task 数据/幂等性 | QA |

### 7.2 治理模板修改

| 文件 | 改动类型 | 改动内容 | 负责人 |
|------|---------|---------|--------|
| `commands/governance-init.md` | 修改 | Step 5.5 新增 archive/ 目录结构创建；Step 7 三个 profile 模板同步修改（Step 1/2 归档感知 + Step E） | Developer |
| `CLAUDE.md`（本项目） | 修改 | 按 4.5 节修改 Step 1/2 读取指令 + 新增 Step E | Developer |

### 7.3 治理数据修改（本狗粮项目迁移后）

| 文件 | 改动类型 | 改动内容 |
|------|---------|---------|
| `.governance/plan-tracker.md` | 修改 | 移除 v0.11.0~v0.31.0 已发布版本的 task 表行。版本标题保留 + "[已归档]"标记 |
| `.governance/evidence-log.md` | 修改 | 移除对应已归档 task 的证据条目 |
| `.governance/archive/tasks/v0.11.0~v0.31.0.md` | 新增 | 已归档 task 表（含标准化文件头） |
| `.governance/archive/evidence/v0.11.0~v0.31.0.md` | 新增 | 已归档 evidence 条目（含标准化文件头） |
| `.governance/archive/index.md` | 新增 | 归档索引——Map<TaskID|EvidenceID → 归档文件路径> |

### 7.4 不受影响的部分

- decision-log.md — 所有决策 < 2 年，不归档
- risk-log.md — < 200 条风险，不归档
- session-snapshot.md — 跨会话快照不受归档影响
- agent-locks.json — 运行时状态，不归档
- 所有 SKILL/SKILL.md 和 agents/ 文件
- manifest.json — archive/ 目录已在 Phase 1 声明
- verify_workflow.py 现有 Check 1-25 — 逻辑不变，仅数据源已通过 GovernanceDataSource 适配

---

## 8. 狗粮项目迁移计划

### 8.1 当前状态

| 指标 | 值 |
|------|-----|
| plan-tracker.md | ~101 KB, 169 tasks |
| evidence-log.md | ~106 KB, 286+ evidence |
| 已发布版本 | 0.1.0 ~ 0.32.0（32 个版本） |
| archive/index.md | 不存在 |
| archive/tasks/ | 空（.gitkeep only） |
| archive/evidence/ | 空（.gitkeep only） |

### 8.2 迁移目标

- **归档版本范围**：v0.11.0 ~ v0.31.0（21 个有 task 数据的已发布版本）
- **保留热数据**：v0.32.0（最新已发布版本）+ 1.0.0 依赖链 + 当前活跃事项
- **不归档版本**：v0.1.0 ~ v0.10.0（passed-on-entry 版本——plan-tracker 中无 task 表，仅在版本路线图中有记录）

### 8.3 预期效果

| 指标 | 迁移前 | 迁移后 | 改善 |
|------|--------|--------|------|
| plan-tracker.md | ~101 KB | ~45 KB | -55% |
| evidence-log.md | ~106 KB | ~55 KB | -48% |
| decision-log.md | ~74 KB | ~74 KB | 不变 |
| risk-log.md | ~19 KB | ~19 KB | 不变 |
| **每次会话必读量** | **~300 KB** | **~193 KB** | **-36%** |
| archive/ 目录 | ~0 KB | ~115 KB | 新增 |
| archive/index.md | 不存在 | ~7 KB | 新增 |

> 注：当前 101 KB 的 plan-tracker 已比 ADR-006 估算的 193 KB 小（可能因内容精简或审计 task 已被移除）。迁移后预期 ~45 KB（保留配置块 + Gate 状态 + 活跃事项 + v0.32.0 task 表 + 版本规划 + 需求跟踪 + 变更控制）。estimated 45 KB vs ADR-006 原估算 65 KB——因热数据实际比估算少。

### 8.4 迁移步骤（由 Developer 执行）

```
Phase 0: 创建 git 回滚点
  git commit -m "pre-archive: governance data snapshot before first migration"

Phase 1: 验证 --auto 模式
  python skills/software-project-governance/infra/archive.py migrate --auto --dry-run
  → 检查输出: 确认识别的版本范围、task 数量、evidence 数量

Phase 2: 执行首次迁移
  python skills/software-project-governance/infra/archive.py migrate --auto
  → 输出迁移摘要
  → plan-tracker.md 和 evidence-log.md 被修改
  → archive/tasks/v0.11.0~v0.31.0.md 被创建
  → archive/evidence/v0.11.0~v0.31.0.md 被创建
  → archive/index.md 被创建

Phase 3: 验证归档完整性
  python skills/software-project-governance/infra/verify_workflow.py check-governance
  python skills/software-project-governance/infra/verify_workflow.py check-archive-integrity
  → 全部 PASS

Phase 4: 人工验证
  - 打开 archive/tasks/v0.11.0~v0.31.0.md — 确认格式正确、task 行完整
  - 打开 archive/evidence/v0.11.0~v0.31.0.md — 确认证据条目完整
  - 打开 archive/index.md — 确认索引条目数与归档 task 数一致
  - 打开 plan-tracker.md — 确认 v0.11.0~v0.31.0 版本标题含 "[已归档]" 标记
  - 打开 plan-tracker.md — 确认 v0.32.0 + 1.0.0 + 当前活跃事项保留完整

Phase 5: 提交迁移结果
  git commit -m "SYSGAP-030: first governance data migration — v0.11.0~v0.31.0 archived"
```

---

## 9. 向后兼容性

### 9.1 老版本用户（安装版本 < 包含 Step E 的版本）

| 场景 | 行为 |
|------|------|
| 老版本用户首次更新到新版 | bootstrap 版本变化检测触发 → Step C 补全结构 → Step E 检测三条件 → 触发归档（如条件满足） |
| 老版本用户未更新（仍用旧版） | 版本无变化 → bootstrap 版本变化检测不触发 → 无归档。治理行为与之前完全一致 |
| 老旧项目——plan-tracker < 80 KB 或 < 2 个已发布版本 | Step E 条件不满足 → 跳过归档。不修改任何治理文件 |

### 9.2 已归档项目

| 场景 | 行为 |
|------|------|
| 已归档项目再次版本 bump | 条件 1（index.md 存在）不满足 → Step E 跳过。不做任何操作 |
| 已归档项目需要增量归档 | 通过优先级 2（task 完成 → 增量归档到对应版本的归档文件）。非 bootstrap 自动触发范围 |

### 9.3 新项目（governance-init 后首次会话）

| 场景 | 行为 |
|------|------|
| 新项目初始化 | archive/ 目录已创建（含 .gitkeep 文件），index.md 不存在。条件 2 不满足（plan-tracker < 80 KB）→ Step E 跳过 |
| 新项目运行 6 个月后首次版本 bump | 条件 2 满足（plan-tracker > 80 KB）+ 条件 3 满足（>= 2 个已发布版本）+ 条件 1 满足（index.md 不存在）→ 触发归档 |

---

## 10. 风险评估

| 风险 | 级别 | 缓解 | 残余 |
|------|------|------|------|
| **归档脚本 --auto 模式首次执行 bug** | 高 | dry-run pre-check + 三阶段事务 + verify + 回滚 + git 保护。本狗粮项目首个迁移对象——发现 bug 后立即修复 | Phase 3/回滚失败 + git 未创建 → git reflog 恢复。概率极低 |
| **归档后 verify_workflow.py 现有 Check 误报** | 中 | GovernanceDataSource 已在 Phase 1 实现了多文件聚合。Check 1-25 逻辑不变——仅数据源变化 | 边界 case——某 Check 内部硬编码了 plan-tracker.md 路径而非使用 GovernanceDataSource。代码审查时逐 Check 检查 |
| **bootstrap 段膨胀——新增 ~36 行** | 低 | 新增的 Step E 是简洁的条件判断 + 单行命令调用。Step 1 修改仅增加必要的归档感知逻辑（非冗余叙述） | lightweight profile 约 80 行 → 增至 ~100 行。仍在 acceptable range |
| **索引膨胀——未来问题** | 低 | 索引按需读取 + 100 KB 自动拆分阈值 + verify_workflow.py Check 26 索引大小告警 | 5000+ task 时才可能触发 > 300 KB。当前 168 task 索引 ~7 KB |

---

## 11. 后续动作

| # | 动作 | 依赖 | 负责人 | 优先级 |
|---|------|------|--------|--------|
| 1 | **ADR 审查**——Design Reviewer（老洪）独立审查本 ADR | — | Coordinator → Design Reviewer | P0 |
| 2 | **实现 archive.py --auto 模式**——auto-detect version boundaries + migrate + verify + rollback on failure | ADR approved | Developer | P0 |
| 3 | **实现 test_archive.py --auto 测试**——正常迁移/空范围/版本路线图缺失/无 task 数据/幂等性 | #2 | QA | P0 |
| 4 | **修改 CLAUDE.md bootstrap**——Step 1/2 归档感知 + Step E | ADR approved | Developer | P0 |
| 5 | **修改 governance-init.md**——Step 5.5 archive/ 目录 + Step 7 三级模板同步 | ADR approved | Developer | P0 |
| 6 | **本狗粮项目首次归档迁移**——执行 8.4 节步骤 | #2, #4 | Developer + QA | P0 |
| 7 | **归档后验证**——verify_workflow.py check-governance + check-archive-integrity 全部 PASS + 人工验证 | #6 | QA | P0 |
| 8 | **bootstrap 模板更新——用户视角验证**：从用户视角检查升级路径闭环（/plugin update → 下次会话 → 自动归档 → 摘要输出 → plan-tracker 缩减 → 交叉验证正确） | #4, #5 | Analyst + QA | P1 |

---

## 附录 A: 三级 Profile bootstrap 模板 diff（关键改动）

以下为 governance-init.md Step 7 三个模板的**新增/修改**部分（非完整模板）。

### A.1 lightweight profile 新增内容

在版本变化检测序列末尾（Step D 之前）新增：

```
   - **治理数据归档检测**（版本 bump 后自动触发）:
     检测三条件: archive/index.md 不存在 AND plan-tracker > 80KB AND ≥2 已发布版本
     → 满足: 运行 archive.py migrate --auto，输出归档摘要
     → 不满足或失败: 静默跳过
```

在 Step 1 读取指令中新增：

```
   - IF .governance/archive/index.md 存在 → 已归档条目可通过索引查询
   - 交叉验证时: 归档文件中的证据 = 有效证据——不可误判为缺失
```

### A.2 standard profile 新增内容（与 4.5 节一致，此处省略重复）

### A.3 strict profile 新增内容

与 standard profile 相同，额外增加：

```
   - **归档完整性强制**: 如果 archive/index.md 存在但 check-archive-integrity 失败 → BLOCK Gate 检查，标记为 P0——归档不一致可能导致证据链断裂
```

---

## 附录 B: archive.py --auto 模式实现要点

以下为 Developer 实现 `--auto` 模式时需要关注的要点（不写实现代码——设计层面的约束）：

1. **版本路线图解析**：在 `## 版本规划` 节下查找 `### 版本路线图` 子标题中的 Markdown 表格——`| 版本 | 状态 | ...`。如果表格不存在或格式不标准，降级为全文件搜索任意包含"版本路线图"的标题，再降级为解析 `### X.Y.Z — ...` 版本节标题
2. **版本排序**：使用 semver 排序（`_version_to_tuple`），确保 `0.10.0 > 0.9.0`（非字典序）
3. **pre-check dry-run**：在实际迁移前，先做一次 `migrate_by_version(start, end, dry_run=True)`——确认能识别到 task 行。如果 `tasks_archived == 0` → 跳过，不修改任何文件
4. **幂等性**：如果 `archive/index.md` 已存在 → 跳过（已在 bootstrap Step E 条件 1 检查，但 --auto 模式自身也做防御性检查）
5. **错误码**：成功 → exit 0。跳过（无可归档数据）→ exit 0 + 输出"无可归档数据"。失败 → exit 1 + 错误信息输出到 stderr
6. **输出格式**：--auto 模式输出精简摘要（适合 bootstrap 输出流），--verbose 标志输出详细调试信息

---

## 附录 C: 与其它架构决策的关系

| 关联 ADR/决策 | 关系 | 说明 |
|-------------|------|------|
| ADR-006（治理数据伸缩性） | 继承 | 本 ADR 是 ADR-006 的 Phase 2——将归档基础设施（Phase 1）集成到升级路径中 |
| V-Gate（版本规划纪律） | 依赖 | 归档触发依赖版本路线图——路线图中"已发布"状态是归档边界判断的关键输入 |
| CLAUDE.md bootstrap（FIX-011 自升级） | 扩展 | bootstrap 自升级序列新增 Step E——归档迁移成为升级路径的标准步骤 |
| FIX-052（版本 bump 自动化） | 对齐 | 版本 bump 自动化依赖版本号一致性——归档不影响版本号。归档后 verify_workflow.py check-version-consistency 应继续 PASS |
| governance-init.md（项目初始化模板） | 修改 | 新项目初始化时预创建 archive/ 目录结构——降低首次归档时的文件系统操作复杂度 |
