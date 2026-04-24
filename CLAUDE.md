# Claude Code Project Guidance

## Governance Bootstrap（强制 — 每次会话第一动作）

在执行任何用户任务之前，**MUST** 先完成：

1. 读取 `.governance/plan-tracker.md`
2. 在内心确认：当前阶段、最近 Gate 结论、活跃风险数、进行中的 P0 任务
3. 如果存在 passed-with-conditions 遗留项，优先处理
4. 如果 `.governance/` 不存在，提醒用户先初始化

**没读 plan-tracker 就开始干活 = 流程违规。这不是"建议"，是前置条件。**

## 干活前检查（每次收到任务时）

在开始执行任何任务前，确认三件事：
- 这个任务在计划跟踪表里吗？不在就先入账
- 做完后需要补什么证据？先想清楚
- 这个任务会不会影响别的阶段？影响就先记风险

## 收工前检查（session 结束前）

1. 输出本轮完成事项摘要
2. 补证据到 `.governance/evidence-log.md`
3. 用 AskUserQuestion 确认下一步优先级

## 详细规则

完整行为协议见插件市场安装的 `software-project-governance` skill（M0~M9 强制性规则、Gate 行为、触发模式等）。但以上三条 bootstrap 规则不依赖 SKILL.md 是否被加载——它们就在本文件里，每次会话必定生效。

## 当前项目治理状态快速入口

- 计划跟踪：`.governance/plan-tracker.md`
- 证据记录：`.governance/evidence-log.md`
- 决策记录：`.governance/decision-log.md`
- 风险记录：`.governance/risk-log.md`
- 验证命令：`python scripts/verify_workflow.py`
