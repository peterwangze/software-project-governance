# software-project-governance — 统一治理入口

一个命令覆盖全部治理场景。替代碎片化的 5 个独立命令（init/status/gate/verify/update）。

## 设计原则

1. **自动分类，不问用户**：命令自动检测项目状态并路由到正确场景
2. **最少提问**：每个场景最小化 AskUserQuestion 次数
3. **安全默认**：异常先于状态展示，恢复先于推进
4. **会话连续性**：snapshot 是跨会话的契约

## 决策树（自动分类）

```
/software-project-governance
        │
        ▼
  [Check 1] .governance/ 存在？
        │
        ├── NO ──► [Check 1a] 项目有文件（非空目录）？
        │               │
        │               ├── YES → SCENARIO B: 半途接入
        │               └── NO  → SCENARIO A: 全新项目初始化
        │
        └── YES ──► [Check 2] .governance/session-snapshot.md 存在
                        AND 日期在 24h 内？
                        │
                        ├── YES → SCENARIO D: 会话恢复
                        └── NO  → [Check 3] 异常检测
                                      │
                                      ├── YES → SCENARIO E: 异常恢复
                                      └── NO  → [Check 4] 工作流版本 < 安装版本？
                                                    │
                                                    ├── YES → SCENARIO C: 工作流升级
                                                    └── NO  → SCENARIO F: 状态展示
```

---

## Scenario A: 全新项目初始化

**检测条件**：`.governance/` 不存在 AND 目录基本为空

**流程**：
1. 通过 AskUserQuestion 收集参数（合并为 1-2 个面板，非 4 个连续问题）
2. 创建 `.governance/` 目录及 4 个治理文件（按 profile 差异化）
3. 注入 CLAUDE.md bootstrap（按 profile 差异化）
4. 安装 git hooks（pre-commit + post-commit + prepare-commit-msg）
5. 输出初始化确认面板
6. 询问是否创建首个任务（INIT-001: 定义项目目标）

**参数收集**（单面板）：
- project_name（从目录名推断，可修改）
- project_goal（一句话）
- profile（lightweight/standard/strict）
- trigger_mode（always-on/on-demand/silent-track）
- permission_mode（maximum-autonomy/default-confirm）

**输出**：初始化确认面板 + 已创建文件清单

**参考**：`commands/governance-init.md` 完整实现

---

## Scenario B: 半途接入

**检测条件**：`.governance/` 不存在 AND 项目有文件/commit 历史

**流程**：

### Step B1: 探索项目

读取以下信号自动推断项目状态（不依赖用户知道阶段术语）：

| 信号 | 读取方式 | 用途 |
|------|---------|------|
| 技术栈 | 读取 `package.json`/`pyproject.toml`/`Cargo.toml`/`go.mod` 等 | 确定语言、框架、依赖数量 |
| 目录结构 | `ls -la` 顶级目录 + 关键子目录 | 确定项目组织方式 |
| Git 历史 | `git log --oneline -20`, `git tag -l`, `git rev-list --count HEAD` | 确定项目成熟度 |
| 测试基础设施 | 搜索 `test/`, `tests/`, `spec/`, `__tests__/`, `*_test.*`, `*.spec.*` | 确定测试覆盖 |
| CI/CD | 搜索 `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`, `Dockerfile` | 确定自动化成熟度 |
| 发布历史 | `git tag -l`, `CHANGELOG.md`, `VERSION` 文件 | 确定发布阶段 |
| 文档 | 搜索 `README.md`, `docs/`, `ARCHITECTURE.md`, `CONTRIBUTING.md` | 确定文档成熟度 |
| 项目配置 | 读取 `README.md` 前 50 行——项目名称和一句话描述 | 确定项目目标 |

### Step B2: 推断当前阶段

根据信号矩阵推断（按优先级从上到下匹配）：

| 阶段推断 | 匹配信号 |
|---------|---------|
| **维护** (11) | git log 显示大量 "fix"/"bug"/"patch" commit + 有 release tag |
| **运营** (10) | 有 monitoring/observability 配置 + 有 Dockerfile/k8s + 有 release |
| **发布** (9) | 有 git tag + 有 CHANGELOG + 有 CI/CD |
| **CI/CD** (8) | 有 `.github/workflows/` 或等效 + CI 配置完整 |
| **测试** (7) | 有 test/ 目录 + 测试文件 > 10 + 有 CI |
| **开发** (6) | 有源代码文件 > 10 + 无测试 或 测试很少 |
| **架构设计** (5) | 有 `ARCHITECTURE.md` 或 `docs/architecture/` |
| **基础设施** (4) | 有 `Dockerfile` + `docker-compose.yml` + 环境配置脚本 |
| **技术选型** (3) | 只有依赖文件 + README，源代码 < 5 文件 |
| **调研** (2) | 有 `research/` 目录或调研文档 |
| **立项** (1) | 只有 README 和项目章程，无代码 |

多信号匹配 → 取最成熟的阶段。模糊 → 使用 lifecycle.md 的阶段判定 checklist。

### Step B3: 展示阶段推断

通过 AskUserQuestion 展示发现并让用户确认：

```
项目探索结果：
- 技术栈: {language} + {framework}
- Git: {N} commits, {M} tags
- 测试: {has_tests? 有/无}
- CI/CD: {has_ci? 有/无}

推断当前阶段: **{stage_name}** ({stage_number}/11)

原因: {evidence_summary}

是否准确？
(1) 准确——继续
(2) 调整为: [11 阶段选择]
```

### Step B4: 收集治理参数

单面板 AskUserQuestion（同 Scenario A Step 1）：
- profile: lightweight / standard / strict
- trigger_mode: always-on / on-demand / silent-track
- permission_mode: maximum-autonomy / default-confirm

(project_type 固定为 "existing", current_stage 已从 B3 确定)

### Step B5: 创建 .governance/ 并执行 onboarding

按 profile 差异化执行（参考 `references/onboarding.md`）：

**所有 profile**：
- 创建 4 个治理文件（plan-tracker/evidence-log/decision-log/risk-log）
- plan-tracker: 当前阶段 = B3 确认的阶段，前置 Gate = passed-on-entry
- decision-log: DEC-001 onboarding 声明

**standard + strict 额外**：
- 当前阶段 ≥ 1 条决策 + ≥ 1 条风险 + ≥ 1 条证据
- 前置阶段各 ≥ 1 条关键决策

**strict 额外**：
- 前置阶段各 ≥ 1 条决策 + ≥ 1 条风险
- 当前阶段 ≥ 2 条证据

### Step B6-B7: 注入 bootstrap + 安装 hooks

同 Scenario A Step 7-8。

### Step B8: 接入确认

输出面板：
- 阶段映射: {inferred_stage} — {gate_status}
- 已创建: plan-tracker(含 onboarding 声明) + evidence-log + decision-log + risk-log
- Bootstrap: CLAUDE.md 已注入
- Hooks: pre-commit + post-commit 已安装
- 下一步: 当前阶段子工作流可供使用

**输出**：阶段映射面板 + 已创建文件清单 + onboarding 决策记录

---

## Scenario C: 工作流升级

**检测条件**：`工作流版本` < 安装版本

**流程**：
1. 读取版本差距（plan-tracker vs SKILL.md）
2. 提取 CHANGELOG delta（从 plan-tracker 版本到当前版本）
3. 自动升级序列：
   - A. 替换 CLAUDE.md bootstrap 段为最新模板（保留 profile 差异化）
   - B. 补全 plan-tracker 缺失结构（permission_mode、版本规划、需求跟踪矩阵、变更控制含快速通道）
   - C. Hook 存活检测——缺失则提示安装命令
   - D. 更新 `工作流版本` 为当前版本
4. 输出升级摘要面板

**输出**：升级摘要（版本跨度 + 新增功能 + 已自动升级 + 需手动操作）

**幂等性**：运行两次安全——已是最新版本时自动路由到 Scenario F

---

## Scenario D: 会话恢复

**检测条件**：`session-snapshot.md` 存在 AND 日期在 24h 内

**新鲜度规则**：
| 时间 | 处理 |
|------|------|
| ≤24h | 活跃恢复——自动展示恢复面板 |
| 24h~7d | 可能过期——展示但标记"另一 session 可能已修改项目状态" |
| >7d | 归档——展示供参考，不自动恢复（转 Scenario F） |

**流程**：

### Step D1: 加载并验证 snapshot

解析 `session-snapshot.md` 所有字段。缺失必要字段（session_date, carry_over_tasks）→ 降级为 Scenario F。

### Step D2: 与 plan-tracker 交叉验证

| 检查 | 方法 | 不一致时 |
|------|------|---------|
| 任务状态 | snapshot carry-over task ID → plan-tracker 中查找 | plan-tracker 中已标记"已完成" → 从 carry-over 移除 |
| 决策 | snapshot pending decision ID → decision-log 查找 | decision-log 已有 → 标记为已解决 |
| 风险 escalation | snapshot active risk → 比较 escalation deadline vs 今天 | deadline 已过 → 标记为"需立即升级" |
| Gate 状态 | snapshot current_gate → plan-tracker Gate 表 | 已通过 → 更新状态 |

### Step D3: 输出恢复面板

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
欢迎回来。上次会话: {session_date} ({agent})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

活跃遗留任务:
  🔄 {task_id} — {description} ({complete_pct}%)
  🔄 ...

待确认决策:
  ⏳ {decision_id} — {title}

需要关注的风险:
  ⚠️ {risk_id} — {description} (升级: {deadline}, 剩余 {days_left}天)

推荐下一步: {next_priority}

(1) 继续上次——恢复遗留任务
(2) 先审查快照——展示完整 session-snapshot
(3) 重新开始——转 Scenario F 状态展示
```

### Step D4: 按用户选择执行

- (1) 继续: 设置遗留任务为当前活跃任务，恢复 trigger_mode/permission_mode
- (2) 审查: 展示完整 snapshot，然后询问是否继续
- (3) 重新开始: 转 Scenario F

---

## Scenario E: 异常恢复

**检测条件**：任一异常标记触发

### Step E1: 全量诊断

执行以下检查并分类严重级别：

**P0 — 阻断级（不修复则治理失效）**：
| 检查项 | 检测方法 |
|--------|---------|
| Hooks 缺失 | `test -f .git/hooks/pre-commit` |
| plan-tracker 损坏 | 解析 markdown 表格，检查 `## 项目配置` 和 `## Gate 状态跟踪` 节 |
| 文件缺失 | 检查 `.governance/` 中 plan-tracker/evidence/decision/risk 是否都存在且非空 |

**P1 — 警告级（治理退化但未完全失效）**：
| 检查项 | 检测方法 |
|--------|---------|
| 证据缺口 | `python scripts/verify_workflow.py check-governance` Check 1 |
| Gate 不一致 | Check 3 |
| 过期风险 | Check 2 + Check 8 |
| 过期任务 deadline | Check 9 |
| Commit 无 task ID | Check 7 |

### Step E2: 展示诊断面板

通过 AskUserQuestion 展示：

```
治理异常诊断:

P0 (阻断):
  ❌ Git hooks 缺失——commit 不受治理约束
  ❌ plan-tracker.md 损坏——无法读取项目状态

P1 (警告):
  ⚠️ 3个已完成任务无证据
  ⚠️ 2个风险超过7天未更新

修复选项:
(1) 一键修复全部 ({p0_count}P0 + {p1_count}P1)
(2) 仅修复 P0 ({p0_count}项)
(3) 先看详情
(4) 暂不处理（记录为已接受风险）
```

### Step E3: 执行修复

按用户选择执行：

- **Hooks 缺失**: `cp scripts/pre-commit-hook.sh .git/hooks/pre-commit && cp scripts/post-commit-hook.sh .git/hooks/post-commit`
- **plan-tracker 损坏**: 尝试从 markdown 表格结构恢复；失败则从 profile 模板重建（保留 evidence-log/decision-log/risk-log）
- **文件缺失**: 从 `workflows/software-project-governance/templates/` 复制模板
- **证据缺口**: 创建占位证据条目（标记"补录——需用户确认"）
- **过期风险/任务**: 询问用户是否仍然活跃，是→更新截止日期，否→关闭

### Step E4: 输出修复报告

```
修复完成:
  ✅ Git hooks 已安装
  ✅ plan-tracker.md 已修复
  ⚠️ 3个证据缺口已创建占位条目(标记"补录")

仍需关注:
  - 补录证据需用户确认内容
```

**输出**：诊断报告 + 已执行的修复 + 仍需关注的事项

---

## Scenario F: 状态展示

**检测条件**：一切正常——`.governance/` 存在、健康、版本最新、无 snapshot、无异常

**展示内容**（比 `governance-status` 更丰富）：
- 项目配置摘要（名称、profile、trigger_mode、permission_mode、版本、阶段）
- Gate 状态表（G1-G11，含通过日期和关键证据）
- 任务统计（总数/已完成/阻塞中/P0 待处理）
- 活跃风险（升级截止日期在 3 天内的标记）
- 最近活动（最近 5 个已完成任务、最近 5 个决策）
- 插件版本新鲜度
- 建议下一步

**输出模板**：参考 `commands/governance-status.md`，扩展含 permission_mode、版本新鲜度、最近活动

---

## Snapshot 格式规范

`session-snapshot.md` 必须包含以下字段以确保 Scenario D 可无缝恢复：

```markdown
# 会话快照 — {{DATE}}

- **session_id**: {{YYYYMMDD-HHMMSS}}
- **session_date**: {{YYYY-MM-DD}}
- **agent**: {{AGENT_NAME_AND_VERSION}}

## 当前状态
- **current_stage**: {{STAGE_NUMBER_AND_NAME}}
- **current_gate**: {{GATE_ID}} (状态: {{STATUS}})
- **trigger_mode**: {{TRIGGER_MODE}}
- **permission_mode**: {{PERMISSION_MODE}}

## 遗留任务
| 任务 ID | 描述 | 完成百分比 | 阻塞原因 | 优先级 |
|---------|-------------|-----------|------------|----------|

## 待确认决策
| 决策 ID | 标题 | 上下文 | 截止日期 |
|-------------|-------|---------|----------|

## 活跃风险
| 风险 ID | 描述 | 升级截止日期 | 负责人 |
|---------|-------------|---------------------|-------|

## 本轮已完成
{{LIST_WITH_EVIDENCE_REFS}}

## 未完成 / 已延期
{{LIST_WITH_REASONS}}

## 下次会话优先级
{{ORDERED_LIST}}

## 用户偏好设置
{{PERSISTED_PREFERENCES}}
```

---

## 现有命令路由

旧 5 个命令保留为快捷方式，路由到统一入口：

| 旧命令 | 等价场景 |
|--------|---------|
| `/governance-init` | 手动触发 Scenario A 或 B |
| `/governance-status` | 手动触发 Scenario F |
| `/governance-gate` | 独立 Gate 检查（保留为快捷方式，不路由） |
| `/governance-verify` | 触发 Scenario E 诊断 |
| `/governance-update` | 手动触发 Scenario C |

---

## 错误码

| 代码 | 条件 | 动作 |
|------|------|------|
| GOV-ERR-001 | `.governance/` 不存在但用户拒绝初始化 | 停止，告知用户需初始化 |
| GOV-ERR-002 | plan-tracker.md 损坏且无法修复 | 停止，建议手动检查或重建 |
| GOV-ERR-003 | git hooks 缺失且无法安装（非 git 项目） | 降级模式——session 级检查 |
| GOV-ERR-004 | 版本降级（安装版本 < 记录版本） | 警告，建议更新插件 |

---

## 文件变更清单

### 新增
- `commands/software-project-governance.md`（本文件）

### 修改
- `skills/software-project-governance/SKILL.md` M3 节——将 `/governance-init` 引用更新为 `/software-project-governance`
- `commands/governance-init.md`——添加路由说明
- `commands/governance-status.md`——添加路由说明
- `commands/governance-verify.md`——添加路由说明
- `commands/governance-update.md`——标记为 DEPRECATED，路由到统一命令

### 不变
- `skills/software-project-governance/references/onboarding.md`——Scenario B 的参考协议
- `scripts/verify_workflow.py`——Scenario E 的诊断引擎
