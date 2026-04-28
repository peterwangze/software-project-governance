# Workflow Manifest: software-project-governance

## 基本信息

- `id`: `software-project-governance`
- `name`: 软件项目治理工作流
- `version`: `0.6.8`
- `goal`: 将大型软件公司的项目管理经验沉淀为可被 coding agent 消费的项目治理 workflow plugin/skill
- `supported_agents`: `Claude`, `Codex`, `Gemini`
- `planned_agents`: `国内主流 agent CLI`
- `validation_status`: `Claude` / `Codex` 已完成插件与 skill 验证；`Gemini` 已有兼容入口与路线定义，但最小验证仍待执行 (`MAINT-007`)

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

- `skills/software-project-governance/`：**运行时唯一事实源**（SKILL.md 入口 + references/ 规则 + stages/ 子工作流 + main-workflow.md + TOOLS.md）
- `workflows/software-project-governance/`：**设计时资产**（manifest + research/ + templates/ + examples/，不重复 skills/ 的运行时内容）
- `protocol/`：通用协议层
- `.governance/`：项目级治理数据（plan-tracker、evidence-log、decision-log、risk-log）
- `scripts/`：校验脚本

## 当前事实源

当前 workflow 的事实源包括：
- 计划主入口
- 证据记录
- 决策记录
- 风险记录
- 校验脚本输出

这些事实源必须在不同 agent 适配入口中复用，不允许为不同 agent 各自维护独立主计划。
