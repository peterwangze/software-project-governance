# Claude Adapter

本目录定义 `software-project-governance` workflow 在 Claude 场景下的消费方式。

## 适配目标

让 Claude 类 coding agent 在执行软件项目任务时，优先读取统一规则与模板，而不是直接自由发挥。

## Claude 入口约定

建议 Claude 适配入口至少包含以下动作：

1. 读取 workflow manifest：
   - `workflows/software-project-governance/manifest.md`
2. 读取协议层：
   - `protocol/workflow-schema.md`
   - `protocol/plugin-contract.md`
3. 读取规则层：
   - `workflows/software-project-governance/rules/lifecycle.md`
   - `workflows/software-project-governance/rules/stage-gates.md`
4. 读取模板层：
   - `workflows/software-project-governance/templates/plan-tracker.md`
   - `workflows/software-project-governance/templates/evidence-log.md`
   - `workflows/software-project-governance/templates/decision-log.md`
   - `workflows/software-project-governance/templates/risk-log.md`
5. 使用样例验证：
   - `workflows/software-project-governance/examples/current-project-sample.md`

## Claude 执行要求

- 先对齐当前项目所处阶段。
- 所有计划状态以计划跟踪表为主事实源。
- 已完成事项必须补证据。
- 发现偏差时必须同步更新风险或决策记录。
- Gate 未通过时，不得声称进入下一阶段。

## 后续可扩展方向

- 可进一步沉淀为 Claude skill 描述文件或更贴近 Claude Code 的加载入口。
- 可补充专门的 prompt contract，使 Claude 在执行任务时自动绑定本 workflow。
