# Gemini Adapter

本目录为 `software-project-governance` workflow 的 Gemini 兼容层预留入口。

## 当前定位

当前阶段不实现完整 Gemini 适配，只定义兼容约束，避免协议层和流程层被 Claude / Codex 私有概念绑死。

## 兼容要求

后续适配 Gemini 或其他 agent CLI 时，应继续复用以下公共资产：

- `protocol/workflow-schema.md`
- `protocol/plugin-contract.md`
- `workflows/software-project-governance/manifest.md`
- `workflows/software-project-governance/rules/*`
- `workflows/software-project-governance/templates/*`
- `workflows/software-project-governance/examples/*`

## 适配原则

- 不复制第二套流程规则。
- 不复制第二套计划事实源。
- 只在 adapter 层解释如何消费已有 workflow 资产。

## TODO

- 识别 Gemini 场景下适合的 skill/plugin/command 承载形式。
- 对齐 Gemini 是否支持文件型流程入口与结构化状态文件。
- 评估国内 agent CLI 的兼容差异，并尽量复用 Gemini 抽象。