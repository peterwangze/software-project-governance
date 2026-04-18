# Workflow Plugin Repository

这是一个面向主流 coding agent 的软件项目治理 workflow 资产仓库。

它的目标不是把 workflow 默认做成用户仓库内的固定资产，而是先沉淀一套可被不同 agent 低侵入集成的治理流程、事实源约定和验证基线，再根据各 agent 的真实集成能力选择最合适的承载形态。

## 当前目标

当前阶段聚焦以下事项：

1. 建立适用于多 agent 的 workflow 协议层与 plugin contract。
2. 将大型软件公司的项目管理经验沉淀为生命周期、Gate、证据、风险、决策等规则。
3. 调研 Claude、Codex、Gemini 等主流 agent 的真实集成方式，明确低侵入主线。
4. 将此前 repo-local 入口方案降级为探索性样例或 fallback，并以新方案重写演进计划。

## 仓库结构

- `protocol/`：通用 workflow schema 与 plugin contract。
- `workflows/software-project-governance/`：软件项目治理工作流本体。
- `adapters/claude/`：Claude 场景的探索性适配样例与调试入口。
- `adapters/codex/`：Codex 场景的探索性适配样例与调试入口。
- `adapters/gemini/`：Gemini 兼容层与后续调研占位。
- `scripts/`：校验脚本与后续自动化工具。

## 集成方式

建议按以下顺序理解和评估本仓库：

1. 读取 `workflows/software-project-governance/manifest.md`，理解 workflow 目标与边界。
2. 读取 `protocol/workflow-schema.md` 和 `protocol/plugin-contract.md`，理解通用协议与集成问题定义。
3. 读取 `workflows/software-project-governance/rules/` 与 `templates/`，理解治理规则与统一事实源。
4. 读取 `workflows/software-project-governance/examples/`，理解当前样例如何管理计划、证据、决策与风险。
5. 将 `adapters/` 下的内容视为当前已验证的探索性接法，而不是最终默认产品形态。
6. 在决定具体接入方式前，优先评估以下主流集成面：
   - Claude：user/project skill、slash command、MCP server
   - Codex：repo rules、全局配置、命令入口、MCP/tool server
   - Gemini：repo rules、全局配置、命令入口、MCP/tool server
7. 只有当 repo-local 入口被证明是目标场景下的最佳方案时，才将对应入口落到用户仓库资产中。

## 当前结论

- Claude 当前已验证 project skill 与仓库级指针可以工作，但这属于 repo-local 探索性接法。
- Codex 当前已验证 adapter manifest + launcher 的半可执行接法，但这同样属于探索性样例。
- Gemini 当前仅保留兼容占位，还没有正式推荐的接入方案。
- 当前仓库不默认假设存在适合本场景的 plugin market / registry 一键分发路径。

## 设计原则

- 调研先行：先确认主流 agent 的真实集成方式，再决定产品承载形态。
- 低侵入优先：尽量优先选择全局安装、命令入口、MCP 或其他低侵入方式，而不是默认要求用户复制仓库资产。
- 单一事实源：不同 agent 共享同一套计划、证据、决策与风险记录。
- 经验驱动：流程规则必须来源于大型软件公司的管理经验，而不是拍脑袋定义。
- 过程可信：任务完成、Gate 通过、偏差修正都必须有证据和留痕。
- 样例验证：任何规则、协议和集成决策都必须由当前项目样例验证。
- 适配解耦：workflow 本体与具体 agent 入口解耦，`adapters/` 只是可选实现，不是唯一真相。

## 当前已验证的探索性入口

以下入口目前保留为样例或 fallback，用于说明仓库内接法如何工作：

- Claude：`CLAUDE.md`、`.claude/skills/software-project-governance/SKILL.md`、`adapters/claude/launch.py`
- Codex：`adapters/codex/adapter-manifest.json`、`adapters/codex/launch.py`
- Gemini：`adapters/gemini/README.md`

这些入口可以继续作为调试、验证和对比基线，但不再代表对最终用户的默认推荐接法。

## 验证

在修改 workflow 规则、协议或样例治理记录后，运行：

```bash
python scripts/verify_workflow.py
```

如需查看当前探索性 adapter 的读取顺序和验证方式，可运行：

```bash
python adapters/claude/launch.py
python adapters/codex/launch.py
```

它们的输出用于验证样例闭环，不等于最终产品接入方案。

## 外部调研参考

本轮重规划基于以下主流集成方式线索：

- Claude Code：Skills、Slash Commands、MCP
- Codex CLI：repo rules、全局配置、MCP/tool server
- Gemini CLI：repo rules、全局配置、MCP/tool server

这些结论用于指导后续产品形态重规划，而不是继续扩大 repo-local 方案范围。

Sources:
- [Claude Code overview](https://docs.anthropic.com/en/docs/claude-code/overview)
- [Slash commands](https://docs.anthropic.com/en/docs/claude-code/slash-commands)
- [Skills](https://docs.anthropic.com/en/docs/claude-code/skills)
- [Model Context Protocol (MCP)](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [OpenAI Codex - GitHub](https://github.com/openai/codex)
- [Codex CLI docs](https://developers.openai.com/codex/cli)
- [Gemini CLI - GitHub](https://github.com/google-gemini/gemini-cli)
- [Gemini CLI docs](https://ai.google.dev/gemini-api/docs/cli)
