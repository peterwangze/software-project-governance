# Claude Code Project Guidance

本文件只作为仓库级入口指针，用于提示 Claude 在处理本仓库的 workflow 资产时优先查看对应 skill。

## Default Workflow

当任务涉及以下任一场景时，优先查看 `.claude/skills/software-project-governance/SKILL.md`：

- 修改 `protocol/`、`workflows/`、`adapters/`、`scripts/` 下的 workflow 资产
- 规划、评审、验证软件项目治理相关工作
- 更新当前项目样例中的计划、证据、决策、风险记录

## Boundary

- 仓库级约束尽量保持最小化，workflow 规则、事实源和验证要求以 skill 与 workflow 本体为准。
- 如果任务与 `software-project-governance` workflow 无关，不要求额外遵循本文件之外的规则。

## Entry

- Skill entry: `.claude/skills/software-project-governance/SKILL.md`
- Adapter debug entry: `adapters/claude/launch.py`
- Workflow root: `workflows/software-project-governance/`

详细读取顺序、输出约束、Gate 行为与验证命令，请以 skill 正文为准。
