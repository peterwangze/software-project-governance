# Plugin Contract

本文件定义一个 workflow plugin/skill 在本仓库中的最小承载约定。

## 目标

让同一套流程资产可以被 Claude、Codex 以及后续的 Gemini、国内 agent CLI 以尽量统一、低侵入、可替换的方式消费。

## 最小承载单元

每个 workflow plugin/skill 至少应包含以下内容：

1. `manifest`
   - 描述 workflow 的名称、目标、版本、支持 agent、关键能力。
2. `research`
   - 记录来源于大型软件公司的项目管理经验，以及对主流 agent 集成方式的调研结论。
3. `rules`
   - 把经验转成生命周期、Gate、留痕和阻断规则。
4. `templates`
   - 提供计划、证据、决策、风险等记录模板。
5. `examples`
   - 提供真实样例，证明 workflow 可运行。
6. `integration contract`
   - 回答不同 agent 如何触发、加载、回写和验证 workflow。
7. `validation`
   - 提供校验脚本或校验规则，验证资产完整性与一致性。

## Skill / Plugin 行为描述要素

一个 agent 集成方式至少要回答以下问题：

- 何时触发这个 workflow
- 集成入口位于哪里：repo-local、全局安装、命令入口、MCP、外部服务或其他承载形式
- agent 在执行过程中应读取哪些规则和模板
- 输出或更新哪些记录文件
- 遇到 Gate 未通过时应如何阻断
- 如何验证当前执行结果是否可信
- 用户替换或移除当前集成方式时，哪些项目资产需要保留，哪些应保持外置

## 集成模式优先级

在没有额外约束时，优先按以下顺序评估集成方式：

1. 全局可复用能力
   - 例如 user skill、全局配置、共享命令入口
2. 低侵入外接能力
   - 例如 MCP server、tool server、sidecar service
3. 项目级显式绑定
   - 例如 project skill、repo rules、仓库级指针文件
4. repo-local 样例或 fallback
   - 仅在前述方式不成立，或需要做最小可运行验证时使用

`adapters/<agent>/` 可以继续作为探索性实现目录存在，但不再默认代表最终产品形态。

## 兼容原则

- Claude / Codex / Gemini 的真实集成方式应以官方能力边界为准，不预设 plugin market 或统一 registry 必然存在。
- 同一 workflow 的事实源必须共享，不允许为不同 agent 维护不同版本的计划、风险、证据。
- repo-local 入口只能证明“当前仓库可运行”，不能自动推导为“这是最终用户的默认最佳接法”。
- 所有面向最终用户的推荐方案，都应先经过集成方式调研，再进入主线计划。

## 当前建议目录布局

- `protocol/`：通用协议
- `workflows/<workflow-id>/`：具体工作流内容
- `adapters/<agent>/`：探索性 agent 集成样例、调试入口或对比基线
- `scripts/`：校验脚本

如后续确定更适合的承载形态，可增加：

- `integrations/`：按集成模式组织的说明或安装资产
- `services/`：MCP 或外部服务实现
- `packages/`：全局安装或分发相关资产

## 当前仓库中的 plugin 目标

当前仓库的首个 workflow plugin 是：

- `software-project-governance`

它的目标是：
- 将大型软件公司的软件项目管理经验转成 agent 可消费的治理流程
- 确保项目目标不偏离
- 确保过程数据可信、可维护、可复盘
- 在主流 agent 的真实集成方式约束下，找到低侵入、可替换的承载方案
