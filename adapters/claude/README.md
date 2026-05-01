# Claude Adapter

> **已废弃（Deprecated）**：本目录是早期的 repo-local 探索性样例，已被 Claude Code 官方插件系统取代。
> 新的正式入口请使用：
> - **自包含插件**：`skills/software-project-governance/SKILL.md`（内嵌核心规则 + `references/` 按需加载）
> - **插件市场**：`.claude-plugin/marketplace.json` + `plugin.json`
> - **交互命令**：`/governance:governance-init`、`/governance:governance-status`、`/governance:governance-gate`、`/governance:governance-verify`
> - **活跃数据源**：`.governance/`（plan-tracker、evidence-log、decision-log、risk-log）
>
> 本目录保留仅作为历史参考，不再继续扩展。下方"入口约定"和"执行要求"描述的是早期 repo-local 多文件读取模式，与当前自包含插件架构不一致，请以 SKILL.md 为准。

本目录定义 `software-project-governance` workflow 在 Claude 场景下的消费方式（历史）。

## 适配目标

让 Claude 类 coding agent 在执行软件项目任务时，优先读取统一规则与模板，而不是直接自由发挥。

## 当前有效入口

Claude Code 通过插件市场加载 `skills/software-project-governance/SKILL.md` 作为自包含入口，该文件依赖：
- `skills/software-project-governance/references/` — 按需读取的参考规则
- 用户项目的 `.governance/` — 活跃治理记录

下方旧入口约定已废弃，不要执行。

## 历史入口约定（已废弃，仅供参考）

<details>
<summary>旧版 repo-local 多文件预加载（不再有效）</summary>

```
1. 读取 workflow manifest：skills/software-project-governance/core/manifest.md
2. 读取协议层：skills/software-project-governance/core/protocol/workflow-schema.md、skills/software-project-governance/core/protocol/plugin-contract.md
3. 读取规则层：core/lifecycle.md、core/stage-gates.md
4. 读取模板层：core/templates/*.md
5. 使用样例验证：.governance/plan-tracker.md
```

</details>

## 原生 skill 入口

当前仓库提供 Claude 原生入口：

- `skills/software-project-governance/SKILL.md`：自包含插件 skill（通过插件市场安装）

## 半可执行入口

当前目录仍保留两类可被脚本消费的辅助入口：

- `adapters/claude/adapter-manifest.json`：机器可读的适配器元数据
- `adapters/claude/launch.py`：输出读取顺序、输出目标、原生 skill 路径、Gate 行为和校验命令的 launcher

可通过以下命令查看入口输出：

```bash
python adapters/claude/launch.py
```

## 入口分工

- Claude 正式加载入口：插件市场安装的 `skills/software-project-governance/SKILL.md`
- Adapter manifest：仓库内部统一 contract
- Launcher：辅助查看和验证当前 Claude 入口映射

## 后续可扩展方向

- 可按需要补充 `.claude/commands/` 下的显式 slash command 入口。
- 可继续补充更贴近 Claude Code 自动触发场景的 skill 说明。