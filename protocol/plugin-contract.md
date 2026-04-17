# Plugin Contract

本文件定义一个 workflow plugin/skill 在本仓库中的最小承载约定。

## 目标

让同一套流程资产可以被 Claude、Codex 以及后续的 Gemini、国内 agent CLI 以尽量统一的方式消费。

## 最小承载单元

每个 workflow plugin/skill 至少应包含以下内容：

1. `manifest`
   - 描述 workflow 的名称、目标、版本、支持 agent、关键能力。
2. `research`
   - 记录来源于大型软件公司的项目管理经验。
3. `rules`
   - 把经验转成生命周期、Gate、留痕和阻断规则。
4. `templates`
   - 提供计划、证据、决策、风险等记录模板。
5. `examples`
   - 提供真实样例，证明 workflow 可运行。
6. `adapter entry`
   - 至少提供一个具体 agent 的消费入口说明。
7. `validation`
   - 提供校验脚本或校验规则，验证资产完整性与一致性。

## Skill / Plugin 行为描述要素

一个 agent 适配入口至少要回答以下问题：

- 何时触发这个 workflow
- 输入是什么
- agent 在执行过程中应读取哪些规则和模板
- 输出或更新哪些记录文件
- 遇到 Gate 未通过时应如何阻断
- 如何验证当前执行结果是否可信

## 兼容原则

- Claude / Codex 优先：入口格式首先贴合这两个场景。
- Gemini / 其他 agent 兼容：先通过通用协议层承接，不直接复制一套私有流程。
- 同一 workflow 的事实源必须共享，不允许为不同 agent 维护不同版本的计划、风险、证据。

## 当前建议目录布局

- `protocol/`：通用协议
- `workflows/<workflow-id>/`：具体工作流内容
- `adapters/<agent>/`：具体 agent 适配入口
- `scripts/`：校验脚本

## 当前仓库中的 plugin 目标

当前仓库的首个 workflow plugin 是：

- `software-project-governance`

它的目标是：
- 将大型软件公司的软件项目管理经验转成 agent 可消费的治理流程
- 确保项目目标不偏离
- 确保过程数据可信、可维护、可复盘
