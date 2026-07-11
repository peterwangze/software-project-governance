---
name: retro-review
description: 复盘审查——对运营和复盘阶段的产出物进行独立审查。覆盖运营反馈、复盘报告、改进计划。质量保障SKILL，由Reviewer Agent调用。
---

# 复盘审查

本 SKILL 用于运营（stage-operations）和维护（stage-maintenance）阶段的独立复盘审查。由 Reviewer Agent 执行。

## 循环角色

版本背景：本循环语义于 0.65.0 引入；本标题是稳定规范，不随版本号变更。

**Gate 语义：** 每个项目迭代的 Outer loop 的 `loop-exit-gate`（运营 → 度量 → 维护/复盘）。本审查认证 Outer loop 的迭代已**收敛**：经验已回灌，并已确定下一轮方向。

审查失败不会终止阶段；它会经 `operations-feedback-to-maintenance-loop` 返回所属循环（Outer loop）继续迭代（深化根因、重新规划改进），并递增 `loop_count`。只有当 `loop_count` 超过 Outer fuse 时，失败才升级而不是继续迭代。

Reviewer 只审查并输出结论，不修改产品代码。Reviewer 必须输出 `APPROVED`、`APPROVED_WITH_NOTES`、`NEEDS_CHANGE` 或 `BLOCKED`；`APPROVED_WITH_NOTES` 是保留备注的通过终态，只能用于没有未解决 BLOCKING finding 的审查，不得包含未解决的 BLOCKING finding。`APPROVED_WITH_NOTES` 的审查输出与 REVIEW 证据 MUST 包含独立结构字段 `unresolved_blockers=0`；字段缺失、非零、非法或重复矛盾时不得通过，自然语言中偶然出现的 `blocking` 不构成该事实。`NEEDS_CHANGE`（及兼容输入 `NEEDS_CHANGES`）不是终态，Coordinator 必须在返工后发起下一轮复审。终态证据由 Check 30 的复审链消费：`APPROVED` 与 `APPROVED_WITH_NOTES` 可以通过并结束复审链；`BLOCKED` 结束链路但不是通过，必须 escalation；`NEEDS_CHANGE(S)`、未知或格式错误结论必须 fail-closed。超过复审 fuse 的 `NEEDS_CHANGE` 必须升级为 `BLOCKED`。

依据 ADR §3.5（loop-engineering-architecture-0.65.0）。完整映射见 [共享循环角色映射](../software-project-governance/references/loop-role-mapping.md)。

## 审查对象

| 产出物 | 来源阶段 | 审查重点 |
|--------|---------|---------|
| 运营数据报告 | 运营 | 数据是否真实？关键指标是否有趋势分析？ |
| 用户反馈汇总 | 运营 | 反馈是否分类？优先级是否合理？ |
| 复盘报告 | 维护 | 四步法是否完整？根因分析是否深入？ |
| 改进计划 | 维护 | 改进措施是否具体可执行？是否有 Owner 和 deadline？ |

## 审查维度

### 1. 数据真实性
- 运营数据是否有来源和采集方法说明？
- 关键指标是否有前后对比（基线 vs 当前）？
- 数据是否存在选择性汇报（Cherry-picking）？

### 2. 根因深度
- 复盘是否使用 5-Why 或等效方法？
- 是否区分了直接原因和系统性原因？
- 是否有"这次修了但下次还会发生"的问题？

### 3. 改进可行性
- 改进措施是否具体到可执行步骤？
- 是否有 Owner 和 deadline？
- 改进措施是否进入 plan-tracker？

### 4. 经验沉淀
- 是否有可复用的经验/SOP 产出？
- 规则/模板是否需要更新（经验回灌）？
- 是否有应该通知其他项目的通用教训？

## 审查流程

1. **读取产出物**：加载运营报告、反馈汇总、复盘报告
2. **逐维度审查**：按上述 4 个维度检查
3. **标注发现**：BLOCKING / WARNING / SUGGESTION
4. **输出审查结论**：APPROVED / APPROVED_WITH_NOTES / NEEDS_CHANGE / BLOCKED
5. **返回 Coordinator**：审查报告 + 结论

## 审查结论

- **APPROVED**：复盘质量合格，经验已沉淀
- **APPROVED_WITH_NOTES**：无未解决 BLOCKING finding；保留并跟踪非阻塞复盘备注后通过
- **NEEDS_CHANGE**：复盘深度不足，需补充分析
- **BLOCKED**：复盘敷衍——无根因、无改进措施、无数据支撑

## 自检

- [ ] 复盘四步法是否完整（回顾目标→评估结果→分析原因→沉淀规律）？
- [ ] 根因分析是否区分了直接原因和系统性原因？
- [ ] 改进措施是否有 Owner + deadline + plan-tracker 条目？
- [ ] 是否有可复用的经验/SOP 产出？
