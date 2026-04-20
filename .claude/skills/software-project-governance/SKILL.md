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

## Session lifecycle

### 会话开始时

1. 读取 `examples/current-project-sample.md` 的项目配置和 Gate 状态跟踪
2. 确认当前阶段、最近 Gate 结论、活跃风险数
3. 如果有遗留项（passed-with-conditions 的未关闭项），优先处理

### 会话结束时

每个会话在完成主要工作后，必须输出**会话状态总结**和**后续建议**。

#### 会话状态总结（纯文本输出）

```
## 会话状态总结

- 本轮完成：[列出本轮完成的事项]
- 治理记录已同步：[决策/证据/风险 是否已补齐]
- 校验结果：verify_workflow.py 通过/未通过
```

#### 后续建议（混合输出：文本 + AskUserQuestion）

后续建议由两部分组成：

**文本部分**（不需要用户判断，直接告知）：
- 下一个最优先事项（从样例跟踪表取最高优先级未开始任务）
- 待关闭的遗留项（passed-with-conditions 的未关闭项）
- 风险提醒（当前打开的高严重级别风险）

**AskUserQuestion 部分**（需要用户判断的问题）：
- 凡是需要用户做选择或判断的问题，必须通过 AskUserQuestion 工具以选项形式呈现
- 每个问题给出 2~4 个选项，每个选项附带简要说明
- 用户只需点击选择，不需要自己组织语言回答
- 如果问题之间有依赖关系，按依赖顺序排列

这个机制的目的是：用户只负责选择和判断，不需要自己组织语言、翻看项目状态或理解上下文。工作流负责整理信息、提炼选项、呈现决策点。

## Validation

在完成 workflow 相关改动后，运行以下命令：

```bash
python scripts/verify_workflow.py
```

如需检查 Claude adapter 的当前加载顺序，可运行：

```bash
python adapters/claude/launch.py
```
