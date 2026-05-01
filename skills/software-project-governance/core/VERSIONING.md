# 版本管理策略

本文件定义 `software-project-governance` 的语义化版本规则、版本升级触发条件和废弃通知期。

## 语义化版本规则

采用 [Semantic Versioning 2.0.0](https://semver.org/)：`Major.Minor.Patch`。三层本身提供细粒度——Patch 就是最小增量单位。不需要预发布标签。

| 版本段 | 升级触发条件 | 频率 | 示例 |
|--------|-------------|------|------|
| **Major** (X.0.0) | Breaking Change：删除/重命名 MUST 规则、改变 Gate 行为语义、改变 governance 文件字段格式 | 罕见（1.0.0 之前 Minor 可含有限 Breaking Change） | Gate 从 11 个减少到 5 个 |
| **Minor** (0.X.0) | 累积的 PATCH 达到里程碑；或新增 MUST 规则、新增子工作流/skill、新增 B/C 级自动化能力 | 每版本里程碑 | 0.5.0→0.6.0（累积了 bootstrap 升级/触发模式/跨会话/交互式 init/7 子工作流深度/BarRaiser/A/B 测试/CI/Profile 差异化等 30+ 变更） |
| **Patch** (0.0.X) | **任何影响 agent 行为或用户可见的变更**：bootstrap 模板变更、子工作流活动变更、skill/模板新增或修改、governance 文件模板字段变更、CLAUDE.md 行为规则变更、references 文件新增/修改、verify_workflow.py 新增检查项 | **每轮有意义的变更**（通常 1 session 或 1~3 个 task 完成后） | 0.6.0→0.6.1→0.6.2→0.6.3 |

### Patch 就是细粒度

三层版本号的 Patch 位本身就是为增量交付设计的。频繁 bump patch 让用户每次 `/plugin update` 都能获取最新改进，不需要等 Minor 里程碑。

**Patch bump 纪律**：
- 每轮有意义的变更完成后 MUST bump PATCH——不要攒着等 Minor
- PATCH bump 时 MUST 更新 CHANGELOG（简述本轮变更）
- PATCH bump 前后 MUST 运行 verify_workflow.py PASSED
- git commit message 格式：`Bump version to 0.X.Y: <本轮变更摘要>`

以下变更 **MUST** bump：

| 变更类型 | bump 级别 | 说明 |
|---------|----------|------|
| bootstrap 注入模板变更（governance-init.md Step 7） | PATCH | 直接影响新用户初始化体验 |
| CLAUDE.md 狗粮实例行为规则变更 | PATCH | 影响本仓库，同步到注入模板时一起 bump |
| stages/ 子工作流活动步骤变更 | PATCH | 影响 agent 执行行为 |
| skill/模板新增或修改 | PATCH | 新增可执行内容 |
| references/ 文件变更（新增/修改强制检查项） | PATCH | 影响 agent 决策 |
| verify_workflow.py 新增检查项 | PATCH | 新增自动化验证能力 |
| governance 模板字段变更 | PATCH | 影响初始化产出 |
| SKILL.md MUST 规则新增 | MINOR | 影响所有 agent 行为——但 1.0.0 之前可灵活处理 |
| 仅修复 bug（不改变行为语义） | PATCH | |

以下变更 **MUST NOT** bump：

- 仅修改 `.governance/` 治理记录（plan-tracker/evidence/decision/risk）
- 仅修改 `adapters/` 历史样例
- 仅修改 `workflows/research/` 调研文档
- 仅修改 `README.md` 措辞（不影响 agent 行为）

## 版本升级触发条件

以下变更 **MUST** 触发版本号升级：

1. **SKILL.md 行为协议变更**（M0~M9 规则的增/删/改）
2. **references/ 文件变更**（新增/删除/重命名文件，或修改强制检查项）
3. **verify_workflow.py 子命令变更**（新增/删除/修改 CLI 接口）
4. **stages/ 子工作流或 skill 变更**（新增/删除，或修改活动清单中的强制步骤）
5. **governance 文件模板字段变更**（plan-tracker/evidence-log/decision-log/risk-log 列定义）

以下变更 **不需要** 触发版本号升级：

- 仅修改当前项目自身的 `.governance/` 记录（plan-tracker/evidence/decision/risk）
- 仅修改 `adapters/` 历史样例
- 仅修改 `workflows/research/` 调研文档
- 仅修改 `README.md` 措辞（不影响 agent 行为）

## 版本声明位置

所有以下文件中的版本号必须保持一致：

1. `.claude-plugin/plugin.json` — `version` 字段
2. `.claude-plugin/marketplace.json` — `plugins[0].version` 字段
3. `.codex-plugin/plugin.json` — `version` 字段
4. `skills/software-project-governance/SKILL.md` — frontmatter `version` 字段
5. `workflows/software-project-governance/manifest.md` — `version` 字段

`verify_workflow.py` 的 snippet 检查会自动验证这 5 个文件的版本号一致性。

## 废弃通知期

- **Major 版本**：至少提前一个 Minor 版本在 CHANGELOG 中标注废弃内容
- **Minor 版本**：无需通知期（向后兼容的增量变更）
- **1.0.0 之前**：Minor 版本可以包含有限的 Breaking Change，但必须在 CHANGELOG 中显式标注

## 版本规划机制

版本号升级不是事后记录——版本规划在开发开始前定义每个版本的范围。

### 版本路线图

每个项目的 `.governance/plan-tracker.md` 中 **MUST** 包含 `## 版本规划` 节，定义：

| 字段 | 说明 |
|------|------|
| 版本号 | 目标版本号（遵循 semver） |
| 状态 | 规划中 / 开发中 / 已发布 |
| 预计日期 | 目标发布日期 |
| 核心范围 | 一句话描述本版本的核心交付 |
| 包含任务 | 映射到 plan-tracker 中的 task ID 或 Tier/Layer |
| 关键交付物 | 本版本完成后的可验证产出 |

### 版本 Gate（V-Gate）

版本发布前对照版本规划执行 V-Gate 检查：

1. 版本范围完成率 ≥ 90%
2. Breaking Change 有文档 + 迁移指南
3. 版本号一致性（verify_workflow.py PASSED）
4. 未完成项已显式处置（降级/移至下一版本）
5. 用户文档已更新（README/CHANGELOG）

### 版本规划与执行计划的关系

- **执行计划**（DEC-052 分层推进模型）控制"按什么顺序做"——Tier/Layer 依赖关系
- **版本规划**（版本路线图）控制"何时交付什么"——版本范围和里程碑
- 两者互补：执行计划的一个 Tier 可能横跨多个版本，一个版本可能包含多个 Tier 的部分任务
- 版本边界由"可交付的用户价值"定义，不是由"Tier 完成"定义

### 版本规划纪律（强制执行）

**版本号分配规则**：
1. **已预留版本号不可占用**：路线图中已规划的版本号已被预留——不得用其他内容覆盖。违反 = 路线图失效。
2. **计划外变更用 PATCH**：不在当前 MINOR 范围内的变更 → bump PATCH，不占用下一 MINOR。
3. **bump 前检查路线图**：bump 到 X.Y.Z 之前，确认该版本号未被预留或内容匹配。
4. **PATCH 事后追加到路线图**：PATCH 发布后 MUST 追加到路线图。

**版本内容一致性**：
5. 发布内容 MUST 匹配路线图中该版本的"包含任务"。不一致 → 先更新路线图再发布。
6. 范围变更 MUST 记录 decision-log。
7. ≥90% 完成率才能发布。未完成的 10% MUST 显式处置。
8. 发布后 MUST 立即更新路线图状态。

**违规案例**：CONSTRAINT-001 占用已预留的 0.7.0（预留给 10 个外部验证任务）→ 应 bump PATCH 到 0.6.10。已修正。

## 用户如何更新到最新版本

### 方法一：插件市场更新（推荐）

```bash
# 在 Claude Code 会话中
/plugin update software-project-governance

# 或重新加载所有插件
/reload-plugins
```

**更新检测逻辑**：Claude Code 比较 installed_plugins.json 中的 gitCommitSha 与源仓库 HEAD。如果不同 → 拉取最新。版本号 bump 确保 marketplace.json 的 version 字段与源一致——这是 `/plugin` 检查"是否最新"的依据。

### 方法二：手动 git pull + reload

```bash
cd <workflow-repo-path>
git pull
# 然后在 Claude Code 中
/reload-plugins
```

### 方法三：检查新鲜度

```bash
python skills/software-project-governance/infra/verify_workflow.py check-plugin-freshness
```

输出示例：
```
Installed: 0.6.0 (commit d4af922, 2026-04-26)
Source:    0.7.0-alpha.1 (commit xxxxxxx, 2026-04-28)
Status:    OUTDATED — 2 versions behind (14 commits)
Action:    Run /plugin update software-project-governance
```

### 预发布版本更新频率

- **alpha** 版本：每轮有意义变更后 bump（通常每天或每 2 天）
- **beta** 版本：版本范围完成后 bump（通常每周）
- **rc** 版本：验证通过后 bump
- **正式版本**：rc 无阻塞 bug 后正式发布

用户可以通过 `/plugin update` 随时获取最新的预发布版本。

## 版本发布流程

1. 确定本次变更的版本段和预发布标签
2. 更新 CHANGELOG.md（新增版本条目）
3. 同步更新 5 个版本声明文件
4. 运行 `python skills/software-project-governance/infra/verify_workflow.py` —— MUST PASSED
5. 提交：`git commit -m "Bump version to X.Y.Z-alpha.N: <summary>"`
6. 用户执行 `/plugin update` 或 `/reload-plugins` 获取新版本
