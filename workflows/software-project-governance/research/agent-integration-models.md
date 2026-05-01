# 主流 agent 工作流集成方式调研

本文件用于沉淀 `software-project-governance` workflow 在主流 coding agent 中的真实集成方式、适用边界与默认优先级判断，为 `RESEARCH-001` 和后续 `PLAN-003` 提供正式事实依据。

## 调研目标

本轮调研关注的问题不是“当前仓库里能不能跑”，而是：

1. workflow 应优先以什么形态被用户接入，才能保持低侵入和可替换。
2. 各 agent 当前真实支持哪些入口：project-local、user/global、slash command、MCP、命令行、插件等。
3. 哪些形态适合承载治理规则本体，哪些只适合作为样例、fallback 或调试入口。
4. 如何在不把 workflow 默认变成用户仓库资产的前提下，仍保持单一事实源与可验证性。

## 统一评估维度

评估各集成方式时，统一使用以下维度：

- 侵入性：是否要求把 workflow 文件直接放进用户仓库。
- 可替换性：用户移除或替换集成方式时，是否会残留大量仓库级资产。
- 共享性：是否易于跨仓库、跨团队复用。
- 可发现性：用户是否容易理解入口在哪里、如何触发。
- 可验证性：是否容易把读取顺序、执行约束、Gate 和验证动作固定下来。
- 事实源隔离：workflow 本体能否与 agent 私有入口解耦。

## Claude Code

### 当前可用集成面

1. Personal Skills：放在 `~/.claude/skills/`，跨项目复用。
2. Project Skills：放在 `.claude/skills/`，随仓库进入版本控制，适合团队共享。
3. Plugin Skills：通过 Claude Code plugin 分发 skill，安装后自动可用。
4. Custom Slash Commands：支持 project 级 `.claude/commands/` 与 user 级 `~/.claude/commands/`。
5. MCP Servers：作为外接工具与 prompt 能力入口，由 `/mcp` 管理连接。
6. `平台原生入口文件`：仓库级说明或约束入口，可作为最薄指针，但属于用户仓库资产。

### 关键结论

- Claude Skills 已经天然支持“user/global”与“project-local”两层承载，因此并不需要默认把 workflow 固化进每个用户仓库。
- Project Skill 适合团队级约束或样例仓库验证，但其本质仍是 repo-local 集成，侵入性高于 personal skill 或 plugin skill。
- Personal Skill 更接近低侵入主线：能力装在用户环境，不强依赖目标仓库改造。
- Slash Commands 更适合显式触发的快捷动作、模板化 prompt 或固定操作脚本，不适合单独承载完整治理规则本体。
- MCP 更适合承载“外接能力”而非“静态流程文本”：例如拉取任务系统、读取外部事实源、执行统一验证、暴露结构化 prompts/tools。
- `平台原生入口文件` 适合做最薄边界说明，不适合成为 workflow 规则本体的主要承载位置。

### 对本项目的含义

- 当前仓库中的 `平台原生入口文件` + `.claude/skills/software-project-governance/SKILL.md` 只能视为 project-local 样例。
- 若后续面向真实用户交付，Claude 默认主线应优先评估 personal skill、plugin skill 或 MCP，而不是要求用户复制 repo-local 入口。
- 如果必须保留 repo-local 入口，也只能作为 fallback 或团队级显式绑定方式。

## Codex CLI

### 当前可用集成面

1. 全局安装 CLI：`npm i -g @openai/codex` 或二进制安装，天然偏向用户环境级接入。
2. Config / Rules / Hooks / `AGENTS.md`：文档与配置体系表明 Codex 支持项目级规则与本地行为约束。
3. MCP：官方文档明确列出 MCP 与 tools 扩展能力。
4. Skills / Plugins / Subagents：Codex 文档导航已把这些能力作为正式配置与扩展面。
5. CLI Slash Commands / 非交互执行：适合包装固定流程或自动化入口。

### 关键结论

- Codex 的默认使用姿势首先是“用户本地安装一个 CLI”，而不是“把 workflow 仓库嵌进目标仓库”。
- 项目级规则文件和 hooks 适合绑定仓库上下文，但更像消费 workflow 结论的投影层，不适合作为 workflow 本体唯一事实源。
- MCP 与 skills/plugin 能力说明 Codex 也支持将可复用能力放在仓库外侧或工具侧，这与本项目的低侵入目标一致。
- CLI/exec/headless 入口说明 Codex 很适合接一个统一的外部 workflow runner 或验证器。
- 当前仓库里的 `adapters/codex/adapter-manifest.json` 与 `launch.py` 只能证明“样例 contract 可表达”，不能证明 repo-local 是默认最优形态。

### 对本项目的含义

- Codex 默认主线应优先考虑：全局安装 + 外部 skill/plugin/config + MCP/tool server。
- repo-local adapter 更适合做契约样例、调试入口和兼容对照，不应继续扩展成面向最终用户的唯一入口。
- 后续若为 Codex 提供正式接入，优先方向应是“如何让本 workflow 被已安装的 Codex 消费”，而不是“如何把 Codex 入口文件写满用户仓库”。

## Gemini CLI

### 当前可用集成面

1. 全局安装或即用即走：`npx @google/gemini-cli`、`npm install -g @google/gemini-cli`。
2. `GEMINI.md`：项目上下文文件，用于为当前仓库注入持久上下文。
3. Custom Commands：官方文档提供自定义命令能力。
4. MCP Server Integration：通过 `~/.gemini/settings.json` 配置外部 MCP server。
5. Headless / JSON 输出 / GitHub Action：说明其自动化与外部编排能力较强。
6. Extensions：官方文档与仓库结构都显示 Gemini CLI 正在建设扩展体系。

### 关键结论

- Gemini CLI 的默认产品姿势同样首先是“用户环境里的 CLI”，不是 repo-local workflow 仓库。
- `GEMINI.md` 很像项目级上下文投影层，适合作为显式绑定入口，但不应直接等同于 workflow 本体。
- MCP 是 Gemini 的重要低侵入扩展面，天然适合把结构化能力放在仓库外侧。
- 自定义命令与 headless 模式说明 Gemini 非常适合接统一 runner、脚本化流程和 CI 场景。
- 由于 Gemini 的 extension 与命令生态仍在快速演化，当前不应过早锁定单一目录布局或 repo-local 形式。

### 对本项目的含义

- `adapters/gemini/README.md` 当前保持兼容占位是合理的，不应在缺少更多结论时直接深做 repo-local 入口。
- 后续 Gemini 正式适配应优先研究：`GEMINI.md` 作为最薄投影、MCP server、custom commands、headless runner 这几类组合。
- 与 Claude/Codex 一样，Gemini 的低侵入方向优先于用户仓库内嵌资产。

## 通用集成模式对比

| 集成模式 | 侵入性 | 可替换性 | 共享性 | 适合作为默认主线 | 说明 |
| --- | --- | --- | --- | --- | --- |
| repo-local skill / rules / context file | 高 | 低 | 中 | 否 | 适合团队显式绑定、样例验证、fallback |
| user/global skill or command | 低 | 高 | 中 | 是 | 适合个人复用与低侵入接入 |
| plugin / extension | 低 | 高 | 高 | 是 | 适合标准化分发与版本化 |
| MCP / tool server | 低 | 高 | 高 | 是 | 适合结构化工具、外部事实源与统一 runner |
| headless CLI / command entry | 低 | 高 | 中 | 是 | 适合自动化、CI、外部编排 |
| 纯文档指针（如 `平台原生入口文件` / `GEMINI.md`） | 中 | 中 | 低 | 否 | 只能做投影层，不应承载完整 workflow 本体 |

## 统一判断

### 可以沉淀为产品原则的结论

1. workflow 本体应独立于任一 agent 的 repo-local 目录结构存在。
2. project-local 入口只应作为样例、fallback 或团队显式绑定方案。
3. 默认推荐形态应优先考虑 user/global skill、plugin/extension、MCP、headless command 等低侵入方式。
4. agent 私有入口文件只应承载“如何映射到 workflow 本体”，不应复制整套治理事实源。
5. 单一事实源必须继续保留在项目级 `.governance/` 中，workflow 本体层的 `examples/` 仅保留历史迁移指针，而不是散落到不同 agent 入口文件。

### 暂不做过度结论的部分

- 不默认假设三家都会提供成熟的 plugin marketplace 一键分发路径。
- 不默认假设 Gemini 当前已有稳定的 plugin/skills 标准与 Claude/Codex 完全等价。
- 不默认假设 repo-local 入口完全无价值；它仍适合作为显式绑定场景和样例仓库验证方式。

## 对当前仓库主线的直接影响

1. `README.md` 中“低侵入优先、repo-local 仅为探索性接法”的叙事成立，并应继续保留。
2. `protocol/plugin-contract.md` 应继续坚持“集成模式优先”，而不是回退到 `adapters/<agent>/` 目录布局优先。
3. `adapters/claude/`、`adapters/codex/`、`adapters/gemini/` 应统一定位为样例、fallback、调试入口或兼容占位。
4. `PLAN-003` 的目标不再是补更多 repo-local 入口，而是基于本调研确定默认产品形态。
5. `OPS-001` 与后续国内 agent CLI 兼容设计，应优先复用“MCP / global skill / command / external runner”这类低侵入抽象。

## 建议的后续动作

1. 基于本文件推进 `PLAN-003`，输出默认产品形态方案。
2. 明确哪一层是 workflow 本体、哪一层是 agent 入口投影、哪一层是外部能力层。
3. 为 Claude、Codex、Gemini 分别给出“默认接入 / fallback / 不推荐”三档接入矩阵。
4. 后续如需真正产品化分发，再单独评估 plugin / extension / registry 路径，而不是提前假设其可用。

## Sources

- Claude Code Skills: https://docs.anthropic.com/en/docs/claude-code/skills
- Claude Code Slash Commands: https://docs.anthropic.com/en/docs/claude-code/slash-commands
- Claude Code MCP: https://docs.anthropic.com/en/docs/claude-code/mcp
- Codex CLI docs: https://developers.openai.com/codex/cli
- OpenAI Codex repository: https://github.com/openai/codex
- Gemini CLI repository: https://github.com/google-gemini/gemini-cli
- Gemini CLI docs: https://www.geminicli.com/docs/
