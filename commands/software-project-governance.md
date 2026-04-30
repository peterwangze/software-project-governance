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
1. **探索项目**：使用 Claude 内置 `/init` 或读取项目文件，收集：
   - 目录结构（顶级目录和关键文件）
   - 技术栈（package.json/pyproject.toml/Cargo.toml 等）
   - git 历史（commit 数量、tag 数量、最近活动）
   - CI/CD 配置、Dockerfile、测试目录
2. **推断当前阶段**：基于发现证据映射到 11 阶段
   - 有 PR/FAQ 无代码 → 调研或立项
   - 有源代码无测试 → 开发
   - 有测试+CI 无 release tag → 测试或 CI/CD
   - 有 git tag → 发布或运营
   - 有 Dockerfile/k8s → 基础设施
3. **展示阶段推断**：通过 AskUserQuestion 让用户确认或调整
4. **收集治理参数**（同 Scenario A 第 1 步）
5. **创建 .governance/**：前置 Gate 标记为 passed-on-entry，当前 Gate 标记为 pending
6. **注入 CLAUDE.md bootstrap + 安装 hooks**
7. **输出接入确认面板**

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

**Snapsho t 新鲜度规则**：
- ≤24h：活跃恢复——自动展示恢复面板
- 24h~7d：可能过期——展示但标记"另一 session 可能已修改"
- >7d：归档——展示供参考，不自动恢复

**流程**：
1. 加载 snapshot，解析所有字段
2. 与 plan-tracker 交叉验证（任务状态、决策、风险）
3. 检查风险 escalation deadline——到期则立即升级
4. 展示恢复面板：
   - 上次会话日期 + agent 身份
   - 活跃 carry-over 任务（含完成百分比）
   - 待确认决策
   - 需关注的风险（escalation deadline 在 3 天内）
   - 推荐下一步
5. 用户选择：(1) 继续上次 (2) 先审查 snapshot (3) 重新开始

**Snapsho t 必要字段**（`session-snapshot.md` 格式规范见下文）：
- session_id, session_date, agent
- current_stage, current_gate, trigger_mode, permission_mode
- carry_over_tasks (ID, 描述, 完成%, 阻塞者, 优先级)
- pending_decisions (ID, 标题, 上下文, deadline)
- active_risks (ID, 描述, escalation deadline, owner)
- completed_in_session, incomplete_in_session
- next_priority, user_preferences

---

## Scenario E: 异常恢复

**检测条件**：任一异常标记——
- `check-governance` 返回 FAILED
- `.git/hooks/pre-commit` 或 `post-commit` 缺失
- `plan-tracker.md` 损坏（解析失败、缺失必要节）
- `.governance/` 中文件数量 < 4

**流程**：
1. 执行全量诊断（Categories A-D + 系统检查）
2. 分类异常严重级别：P0（hooks 缺失、plan-tracker 损坏、文件缺失）、P1（证据缺口、Gate 不一致、过期风险）
3. 通过 AskUserQuestion 展示诊断 + 修复选项：
   - "一键修复全部" / "仅修复 P0" / "先看详情" / "暂不处理（记录为已接受风险）"
4. 执行修复：
   - hooks 缺失 → 从 scripts/ 复制
   - plan-tracker 损坏 → 尝试从 Markdown 表格恢复，或从模板重建（保留 evidence/decision/risk）
   - 证据缺口 → 创建占位证据条目（标记"补录"）
   - 过期风险 → 询问是否仍然活跃
   - 文件缺失 → 从模板重建
5. 输出修复报告

**输出**：诊断报告 + 已执行的修复 + 仍需关注的事项

---

## Scenario F: 状态展示

**检测条件**：一切正常——`.governance/` 存在、健康、版本最新、无 snapshot、无异常

**展示内容**（比 `governance-status` 更丰富）：
- 项目配置摘要（名称、profile、trigger_mode、permission_mode、版本、阶段）
- Gate 状态表（G1-G11，含通过日期和关键证据）
- 任务统计（总数/已完成/阻塞中/P0 待处理）
- 活跃风险（escalation deadline 在 3 天内的标记）
- 最近活动（最近 5 个已完成任务、最近 5 个决策）
- 插件版本新鲜度
- 建议下一步

**输出模板**：参考 `commands/governance-status.md`，扩展含 permission_mode、版本新鲜度、最近活动

---

## Snapshot 格式规范

`session-snapshot.md` 必须包含以下字段以确保 Scenario D 可无缝恢复：

```markdown
# Session Snapshot — {{DATE}}

- **session_id**: {{YYYYMMDD-HHMMSS}}
- **session_date**: {{YYYY-MM-DD}}
- **agent**: {{AGENT_NAME_AND_VERSION}}

## Current State
- **current_stage**: {{STAGE_NUMBER_AND_NAME}}
- **current_gate**: {{GATE_ID}} (status: {{STATUS}})
- **trigger_mode**: {{TRIGGER_MODE}}
- **permission_mode**: {{PERMISSION_MODE}}

## Carry-over Tasks
| Task ID | Description | % Complete | Blocked By | Priority |
|---------|-------------|-----------|------------|----------|

## Pending Decisions
| Decision ID | Title | Context | Deadline |
|-------------|-------|---------|----------|

## Active Risks
| Risk ID | Description | Escalation Deadline | Owner |
|---------|-------------|---------------------|-------|

## Completed This Session
{{LIST_WITH_EVIDENCE_REFS}}

## Incomplete / Deferred
{{LIST_WITH_REASONS}}

## Next Session Priority
{{ORDERED_LIST}}

## User Preferences
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
