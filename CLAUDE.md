# Claude Code Project Guidance

本仓库的核心产品是 `software-project-governance` workflow plugin/skill，而不是单纯的流程文档集合。

## Default Workflow

当任务涉及以下任一场景时，优先使用 `.claude/skills/software-project-governance/SKILL.md` 中定义的 skill：

- 修改 `protocol/`、`workflows/`、`adapters/`、`scripts/` 下的 workflow 资产
- 规划、评审、验证软件项目治理相关工作
- 更新当前项目样例中的计划、证据、决策、风险记录

## Single Source of Truth

所有 workflow 事实源统一落在以下文件，不允许为 Claude 维护第二套主计划：

- `workflows/software-project-governance/examples/current-project-sample.md`
- `workflows/software-project-governance/examples/current-project-evidence-log.md`
- `workflows/software-project-governance/examples/current-project-decision-log.md`
- `workflows/software-project-governance/examples/current-project-risk-log.md`

## Verification

在声称 workflow 相关改动完成之前，必须运行：

```bash
python scripts/verify_workflow.py
```

## Adapter Debug Entry

如需查看当前 Claude adapter 的读取顺序和验证方式，可运行：

```bash
python adapters/claude/launch.py
```
