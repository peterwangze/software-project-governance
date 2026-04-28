# Versioning Policy

本文件定义 `software-project-governance` 的语义化版本规则、版本升级触发条件和废弃通知期。

## 语义化版本规则

采用 [Semantic Versioning 2.0.0](https://semver.org/)：`Major.Minor.Patch`

| 版本段 | 升级触发条件 | 示例 |
|--------|-------------|------|
| **Major** (X.0.0) | Breaking Change：删除/重命名 MUST 规则、改变 Gate 行为语义、改变 governance 文件字段格式（旧版本 agent 按旧规则执行会出错） | 删除 M3.1 DRI 规则、Gate 从 11 个减少到 5 个 |
| **Minor** (0.X.0) | 新增 MUST 规则、新增 B/C 级自动化能力、新增 references 文件、新增子工作流或 skill、扩展 Gate 检查项 | 新增 M8.1 外部验证、新增 gate-check 子命令 |
| **Patch** (0.0.X) | 修复 bug、修正文档措辞、优化已有规则表述（不改变行为语义）、更新模板示例 | 修复 parse_gate_detail regex、修正 README 错字 |

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

## 版本发布流程

1. 确定本次变更的版本段（Major/Minor/Patch）
2. 更新 CHANGELOG.md（在 `## [Unreleased]` 下列出变更）
3. 同步更新 5 个版本声明文件
4. 提交：`git commit -m "Bump version to X.Y.Z"`
5. 在 CHANGELOG.md 中将 `[Unreleased]` 改为 `[X.Y.Z]` + 日期
