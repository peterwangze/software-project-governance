---
name: software-project-governance
description: 在软件项目治理相关任务中加载统一 workflow 规则、模板、Gate 和事实源，并将结果写回当前项目样例。
---

# Software Project Governance

当任务涉及软件项目治理 workflow 的规划、设计、验证、演进或样例记录维护时，使用本 skill。

## Use this skill when

- 需要修改 `protocol/`、`workflows/`、`adapters/`、`scripts/` 下的 workflow 资产
- 需要推进或复盘当前项目样例中的任务状态
- 需要检查 Gate 是否允许阶段推进
- 需要补证据、决策、风险记录，保证过程可信

## Required read order

在开始执行前，按以下顺序读取并理解：

1. `workflows/software-project-governance/manifest.md`
2. `protocol/workflow-schema.md`
3. `protocol/plugin-contract.md`
4. `workflows/software-project-governance/rules/lifecycle.md`
5. `workflows/software-project-governance/rules/stage-gates.md`
6. `workflows/software-project-governance/templates/plan-tracker.md`
7. `workflows/software-project-governance/templates/evidence-log.md`
8. `workflows/software-project-governance/templates/decision-log.md`
9. `workflows/software-project-governance/templates/risk-log.md`
10. `workflows/software-project-governance/examples/current-project-sample.md`

## Output rules

所有与当前项目样例有关的结果只允许写回以下事实源：

- `workflows/software-project-governance/examples/current-project-sample.md`
- `workflows/software-project-governance/examples/current-project-evidence-log.md`
- `workflows/software-project-governance/examples/current-project-decision-log.md`
- `workflows/software-project-governance/examples/current-project-risk-log.md`

不要为 Claude 额外创建第二套项目状态文件。

## Gate behavior

- 如果 Gate 未通过，不得声称进入下一阶段。
- 如果发现偏差或阻塞，必须更新风险记录或决策记录。
- 所有已完成事项必须补证据。

## Validation

在完成 workflow 相关改动后，运行以下命令：

```bash
python scripts/verify_workflow.py
```

如需检查 Claude adapter 的当前加载顺序，可运行：

```bash
python adapters/claude/launch.py
```
