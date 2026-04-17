# Workflow Manifest: software-project-governance

## 基本信息

- `id`: `software-project-governance`
- `name`: 软件项目治理工作流
- `version`: `0.1.0`
- `goal`: 将大型软件公司的项目管理经验沉淀为可被 coding agent 消费的项目治理 workflow plugin/skill
- `supported_agents`: `Claude`, `Codex`
- `planned_agents`: `Gemini`, `国内主流 agent CLI`

## 核心能力

- 提供项目治理阶段模型
- 提供 Gate 门禁与阻断规则
- 提供计划、证据、决策、风险等记录模板
- 提供样例数据，验证流程可运行
- 提供 agent 适配入口和校验脚本

## 流程目标

- 保证项目推进过程不偏离目标
- 保证过程数据可信、可追溯、可维护
- 降低 AI 参与研发时出现多套事实源和过程失真的风险

## 组成结构

- `research/`：大型软件公司管理经验
- `rules/`：生命周期、Gate 与过程规则
- `templates/`：计划、证据、决策、风险模板
- `examples/`：当前项目样例数据

## 当前事实源

当前 workflow 的事实源包括：
- 计划主入口
- 证据记录
- 决策记录
- 风险记录
- 校验脚本输出

这些事实源必须在不同 agent 适配入口中复用，不允许为不同 agent 各自维护独立主计划。
