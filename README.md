# Workflow Plugin Repository

这是一个面向主流 coding agent 的软件项目治理 workflow plugin/skill 仓库。

它的目标不是单纯提供项目管理文档，而是将大型软件公司的项目管理经验固化为流程，再将流程固化为可被 agent 消费的 workflow 插件，优先支持 Claude 和 Codex，后续逐步兼容 Gemini 及更多主流 agent CLI。

## 当前目标

第一阶段聚焦以下事项：

1. 建立适用于多 agent 的 workflow 协议层与 plugin contract。
2. 将大型软件公司的项目管理经验沉淀为生命周期、Gate、证据、风险、决策等规则。
3. 提供 Claude 和 Codex 可消费的首版适配入口。
4. 使用当前项目作为样例，验证 workflow plugin 的可运行性与过程可信度。

## 仓库结构

- `protocol/`：通用 workflow schema 与 plugin contract。
- `workflows/software-project-governance/`：软件项目治理工作流本体。
- `adapters/claude/`：Claude 场景适配入口。
- `adapters/codex/`：Codex 场景适配入口。
- `adapters/gemini/`：Gemini 兼容层预留入口。
- `scripts/`：校验脚本与后续自动化工具。

## 使用方式

建议按以下顺序消费本仓库：

1. 读取 `workflows/software-project-governance/manifest.md`，理解 workflow 目标与边界。
2. 读取 `protocol/workflow-schema.md` 和 `protocol/plugin-contract.md`，理解通用协议。
3. 读取 `workflows/software-project-governance/rules/` 下的生命周期与 Gate 规则。
4. 读取 `workflows/software-project-governance/templates/` 下的模板，作为统一事实源。
5. 在 Claude 场景下，优先通过 `CLAUDE.md` 与 `.claude/skills/software-project-governance/SKILL.md` 加载 workflow；`adapters/claude/launch.py` 作为辅助调试入口。
6. 在其他 agent 场景下，根据所用 agent 进入 `adapters/claude/` 或 `adapters/codex/`。
7. 使用 `workflows/software-project-governance/examples/` 验证流程运行效果，并统一写回当前项目样例事实源。

## 设计原则

- 协议先行：先统一 workflow 与 plugin contract，再做 agent 适配。
- 单一事实源：不同 agent 共享同一套计划、证据、决策与风险记录。
- 经验驱动：流程规则必须来源于大型软件公司的管理经验，而不是拍脑袋定义。
- 过程可信：任务完成、Gate 通过、偏差修正都必须有证据和留痕。
- 适配解耦：workflow 本体与具体 agent 入口解耦，便于后续扩展到更多 agent。
- 样例验证：任何规则与适配设计都必须由当前项目样例验证。