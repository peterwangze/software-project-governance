# 按本轮产出选择技能

协调者通过 `software-project-governance` 建立及恢复工作单元。当目标进入新的专业领域、原审查要求返工或需要选择执行者时，`main-workflow` 按下表调度。技能名对应分发目录 `skills/<技能名>/SKILL.md`。每项活动交付可复核的原件。

| 作用域 / 实际缺口 | 执行角色与技能 | 交给谁、用来做什么 |
| --- | --- | --- |
| 立项或准备 · 成品与受益人不清 | Analyst 用 `stage-initiation`、`requirement-clarification` 提取原始意图、样例与验收操作。用户价值、成功标准需要展开时分别用 `pr-faq`、`okr`。 | 用户确认关键意图，Requirement Reviewer 用 `requirement-review` 检查范围与可验证性。 |
| 准备 · 需要候选与环境依据 | Analyst 用 `stage-research` 收集真实用户和社区候选。Architect 用 `stage-selection` 试用候选，DevOps 或 Developer 用 `stage-infra` 复现实验环境。 | Design Reviewer 用 `tech-review` 复核试用、技术约束与取舍。环境说明交实现者重跑。 |
| 交付 · 设计及接口需要决策 | Architect 用 `stage-architecture` 定义边界与失败条件；复杂取舍用 `six-pager` 对照实测备选。 | Design Reviewer 用 `design-review` 依据本单元及父目标核对契约，要求补证或交付设计。 |
| 内层 · 实现或修复 | Developer 用 `stage-development` 完成宿主修改，Governance Developer 处理治理工具与指引。 | Code Reviewer 用 `code-review` 独立核查实际调用路径及变更；具体发现回到实现者。 |
| 内层 · 真实成品是否达到判据 | QA 用 `stage-testing` 执行独立用户路径，重放失败样本。 | Test Reviewer 用 `test-review` 核实验收范围和原始回执，缺口回到原单元。 |
| 交付 · 部署或发布 | DevOps 用 `stage-cicd` 验证交付保护。Release 用 `stage-release`、`release-checklist` 准备制品、发布许可和回滚。 | 普通 `delivery_goal` 在 G9 消费独立成品验收者的原件。显式 `release_version` 由 Release Reviewer 用 `release-review` 签核候选版本，发布者消费裁决和当次授权。 |
| 外层 · 实际使用与后续决策 | Release 用 `stage-operations` 收集使用与故障反馈。Maintenance 用 `retro-meeting`、`stage-maintenance` 重现问题，推导可验证的改进。 | Retro Reviewer 用 `retro-review` 核实效果、遗留风险和下一轮投入依据，反馈到相应交付或准备单元。 |
