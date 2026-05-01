# Codex Adapter

> **已废弃（Deprecated）**：本目录是早期的 repo-local 探索性样例，已被 Codex 官方插件系统取代。
> 新的正式入口请使用：
> - **自包含插件**：`skills/software-project-governance/SKILL.md`（内嵌核心规则 + `references/` 按需加载 + `stages/` 子工作流和 skills）
> - **Codex 插件**：`.codex-plugin/plugin.json` + `skills/software-project-governance/SKILL.md`
> - **Codex 市场**：`.agents/plugins/marketplace.json`
> - **活跃数据源**：`.governance/`（plan-tracker、evidence-log、decision-log、risk-log）
>
> 本目录保留仅作为历史参考，不再继续扩展。**不要按下方旧入口约定执行**——那是 repo-local 多文件预加载模式，与当前自包含插件架构冲突。

本目录定义 `software-project-governance` workflow 在 Codex CLI 场景下的消费方式（历史）。

## 适配目标

让 Codex 类 coding agent 在执行项目任务时，以统一流程资产为约束，避免直接基于临时上下文做局部最优决策。

## 当前有效入口（与自包含架构一致）

Codex 加载 `skills/software-project-governance/SKILL.md` 作为自包含入口，该文件依赖：
- `skills/software-project-governance/references/` — 按需读取的参考规则
- `skills/software-project-governance/stages/` — 11 个阶段的子工作流和 skill
- 用户项目的 `.governance/` — 活跃治理记录

Codex 用户无需读取下方的旧入口约定。

## 历史入口约定（已废弃，仅供参考）

<details>
<summary>旧版 repo-local 6 步预加载（不再有效）</summary>

以下内容仅在早期 repo-local 架构下有效，已不再推荐使用。

1. 读取 workflow manifest：`skills/software-project-governance/core/manifest.md`
2. 读取协议层：`skills/software-project-governance/core/protocol/workflow-schema.md`、`skills/software-project-governance/core/protocol/plugin-contract.md`、`skills/software-project-governance/core/protocol/external-command-contract.md`
3. 读取规则层：`workflows/software-project-governance/rules/*.md`
4. 读取模板层：`workflows/software-project-governance/templates/*.md`
5. 按当前阶段读取子工作流和 skill：`workflows/software-project-governance/stages/<stage>/`
6. 读取样例：`.governance/plan-tracker.md`

</details>

## 半可执行入口

当前目录已提供两类可被脚本消费的入口：

- `adapters/codex/adapter-manifest.json`：机器可读的适配器元数据
- `adapters/codex/launch.py`：输出读取顺序、输出目标、Gate 行为和校验命令的 launcher

可通过以下命令查看入口输出：

```bash
python adapters/codex/launch.py
```

## 后续可扩展方向

- 可进一步提供面向 Codex CLI 的命令式入口描述。
- 可补充更结构化的 adapter contract，使 Codex 更容易自动消费 workflow。
