# 用户项目数据与样例数据边界

本文件说明 `software-project-governance` 工作流中用户项目数据与工作流自身样例数据的边界。

## 数据分类

### 用户项目数据（`.governance/`）

用户安装工作流后，在其项目根目录下创建的数据。**这些是用户自己的项目治理记录，不是工作流的一部分。**

| 文件 | 内容 | 归属 | 是否随工作流升级 |
|------|------|:--:|:--:|
| `.governance/plan-tracker.md` | 项目配置、Gate 状态、任务跟踪 | 用户 | 否（bootstrap 自升级可补结构） |
| `.governance/evidence-log.md` | 证据记录 | 用户 | 否 |
| `.governance/decision-log.md` | 决策记录 | 用户 | 否 |
| `.governance/risk-log.md` | 风险记录 | 用户 | 否 |
| `.governance/session-snapshot.md` | 会话快照 | 用户（临时） | 否 |

### 工作流资产（插件文件）

通过插件市场安装，位于 `~/.claude/plugins/cache/` 或项目内的 `skills/` 目录。**这些文件在工作流升级时会被替换。**

### 样例数据（本仓库特有）

`workflows/software-project-governance/examples/` 下的文件是工作流开发仓库的狗粮样例——**用户项目中不存在这些文件**。

| 文件 | 说明 |
|------|------|
| `current-project-sample.md` | 工作流开发仓库自身的项目跟踪样例 |
| `current-project-evidence-log.md` | 工作流开发仓库自身的证据样例 |
| `current-project-decision-log.md` | 工作流开发仓库自身的决策样例 |
| `current-project-risk-log.md` | 工作流开发仓库自身的风险样例 |

### E2E 测试数据（本仓库特有）

`e2e-test-project/` 是 E2E 自动化测试项目——**用户项目中不存在**。

## 工作流升级时的数据行为

| 数据类别 | 升级时是否修改 | 说明 |
|---------|:--:|------|
| 用户 `.governance/` 文件 | **否** | 绝对不触碰用户数据 |
| 用户 `CLAUDE.md` | 是（仅 bootstrap 段） | 自升级机制替换 `## Governance Bootstrap` 段，其余内容保留 |
| 插件文件 | 是（全部） | `/plugin update` 替换整个插件目录 |
| 样例数据 | — | 用户项目中不存在 |

## 用户常见困惑

**Q: 我初始化后看到的 plan-tracker 和示例项目中的一样吗？**
A: 结构一样（版本规划、需求跟踪、变更控制等章节），但内容是你的项目数据。示例项目的 plan-tracker 是工作流开发仓库自身的狗粮数据。

**Q: 工作流升级会覆盖我的 plan-tracker 吗？**
A: 不会。自升级只补缺失的章节结构（如旧版没有版本规划节），不修改你的任务、Gate、风险等数据。

**Q: 我的数据在哪儿？**
A: 全部在项目根目录的 `.governance/` 中。没有其他位置。
