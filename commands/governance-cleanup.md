# governance-cleanup — 插件升级后清理冗余文件

用户从 0.11.0 及之前版本升级到 0.12.0+ 后，插件缓存中可能存在旧版本的冗余文件。本命令清除这些文件，确保插件目录纯净。

## 触发条件

- `/governance-cleanup` — 执行清理
- 首次使用 `/governance` 时自动检测并提示（Scenario C 升级场景）

## 清理目标

以下文件/目录在 0.12.0 之前的版本中存在于插件缓存，升级后应被移除：

| 路径 | 来源 | 说明 |
|------|------|------|
| `.governance/` | 根目录 | 工作流作者的治理运行时数据 |
| `CLAUDE.md` | 根目录 | 工作流作者的 Claude 开发配置 |
| `.claude/` | 根目录 | 工作流作者的本地设置 |
| `e2e-test-project/` | 根目录 | 工作流开发测试项目 |
| `CHANGELOG.md` | 根目录 | 工作流开发历史 |
| `.github/` | 根目录 | 工作流仓库 CI |
| `scripts/` | 根目录 | Python 编译缓存 |
| `workflows/` | 根目录 | 工作流设计时资产（已迁入 project/） |
| `references/architecture.md` | references/ | 内部架构设计文档 |
| `references/agent-team-architecture.md` | references/ | 内部 Agent Team 设计 |
| `references/asset-migration-map.md` | references/ | 内部迁移映射表 |
| `references/user-perspective-principle.md` | references/ | 内部设计原则 |
| `references/data-boundary.md` | references/ | 内部数据边界说明 |
| `references/agent-entry-differences.md` | references/ | 内部兼容性研究 |

### v0.18.0 升级残留：SKILL stub

v0.14.0~v0.17.0 期间在 `skills/` 下创建了 25 个 SKILL stub（重定向文件，每个约 350B）。v0.19.0 起真实 SKILL 已直接迁至 `skills/<name>/SKILL.md` 平铺，stub 不再需要。

升级后残留的 stub 目录：
`skills/code-review/` `skills/design-review/` `skills/main-workflow/` `skills/okr/` `skills/pr-faq/` `skills/release-checklist/` `skills/release-review/` `skills/requirement-clarification/` `skills/requirement-review/` `skills/retro-meeting/` `skills/retro-review/` `skills/six-pager/` `skills/stage-architecture/` `skills/stage-cicd/` `skills/stage-development/` `skills/stage-infra/` `skills/stage-initiation/` `skills/stage-maintenance/` `skills/stage-operations/` `skills/stage-release/` `skills/stage-research/` `skills/stage-selection/` `skills/stage-testing/` `skills/tech-review/` `skills/test-review/`

**检测方法**：检查 `skills/` 下的 SKILL.md 是否包含 stub 标识 `> 本文件是 plugin 发现 stub`。v0.19.0+ 真实 SKILL 已迁至 `skills/<name>/SKILL.md` 平铺，stub 可直接安全删除。

## 执行流程

### Step 1: 检测

检查插件缓存目录中是否存在上述冗余文件。对 SKILL stub 采用内容检测：读取 `skills/*/SKILL.md`（不含 `software-project-governance/`），检查是否包含 `plugin 发现 stub`。

### Step 2: 分类展示

```
冗余文件检测:
  🔴 必须移除（会误导用户）:
    {list of P0 files}
  🟡 建议移除（不必要的信息噪音）:
    {list of P1 files}

(1) 一键清理全部
(2) 仅清理 🔴 必须移除的
(3) 先看详情——逐文件说明
(4) 跳过——保留所有文件（不推荐）
```

### Step 3: 执行清理

按用户选择删除冗余文件。

### Step 4: 输出清理报告

```
清理完成:
  ✅ 已移除 {N} 个冗余文件/目录
  ✅ 插件缓存已纯净

插件现在只包含:
  - skills/    六层架构完整产品
  - commands/  用户斜杠命令
  - adapters/  平台适配器
  - plugin 包
```

## 安全保证

- **不触碰用户项目文件**：只清理插件缓存目录（`~/.claude/plugins/cache/`）
- **不触碰 `.governance/` 在用户项目中的副本**：只清理插件缓存中的
- **清理前展示文件列表**：用户确认后才执行
- **可跳过**：用户可以选择不清理

## 错误码

| 代码 | 条件 | 动作 |
|------|------|------|
| CLEANUP-ERR-001 | 插件缓存目录不存在 | 提示用户检查插件安装状态 |
| CLEANUP-ERR-002 | 无可清理文件 | 告知用户插件已是纯净版本 |

## 自校验

- [ ] 冗余文件列表已展示
- [ ] 用户已确认清理范围
- [ ] 清理后插件缓存只包含产品文件
- [ ] 用户项目文件未被触碰
