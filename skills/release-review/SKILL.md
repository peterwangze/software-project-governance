---
name: release-review
description: 发布审查——对发布就绪状态进行独立审查。覆盖CI/CD和发布阶段。质量保障SKILL，由Reviewer Agent调用。
---

# 发布审查

本 SKILL 用于 CI/CD（stage-cicd）和版本发布（stage-release）阶段的独立发布审查。由 Reviewer Agent 执行。

## 循环角色

版本背景：本循环语义于 0.65.0 引入；本标题是稳定规范，不随版本号变更。

**Gate 语义：** Middle loop 的 `loop-exit-gate`，同时也是 Outer loop 的 `loop-entry-gate`（运营 → 度量 → 维护/复盘）。本审查认证 Middle loop 的**退出条件**：flow unit 可发布；同时认证进入 Outer loop 的运营度量阶段。

审查失败不会终止阶段；它会经 `release-to-testing-rework` 返回所属循环（测试子循环，并可回到 Inner loop）继续迭代，并递增 `loop_count`。只有当 `loop_count` 超过 Middle fuse 时，失败才升级而不是继续迭代。

Reviewer 只审查并输出结论，不修改产品代码。Reviewer 必须输出 `APPROVED`、`NEEDS_CHANGE` 或 `BLOCKED`；`NEEDS_CHANGE` 不是终态，Coordinator 必须在返工后发起下一轮复审。终态证据由 Check 30 的复审链消费：仅 `APPROVED` 或 `BLOCKED` 可结束链路，超过复审 fuse 的 `NEEDS_CHANGE` 必须升级为 `BLOCKED`。

依据 ADR §3.5（loop-engineering-architecture-0.65.0）。完整映射见 [共享循环角色映射](../software-project-governance/references/loop-role-mapping.md)。

## 审查对象

| 产出物 | 来源阶段 | 审查重点 |
|--------|---------|---------|
| CI/CD 流水线配置 | CI/CD | 质量门禁是否有效？阻断条件是否正确？ |
| 发布检查清单 | 发布 | 所有检查项是否通过？是否有遗漏？ |
| Changelog | 发布 | 变更描述是否准确？Breaking change 是否标注？ |
| 回滚方案 | 发布 | 回滚步骤是否可执行？回滚时间是否可接受？ |

## 审查维度

### 1. 发布就绪
- 所有 Gate 检查是否通过（G1-G8）？
- 是否有未解决的 BLOCKING 问题？
- P0 任务是否全部完成？

### 2. 质量门禁
- CI 流水线是否全部通过？
- 代码覆盖率是否满足基线？
- 安全扫描是否通过？

### 3. 回滚能力
- 回滚方案是否已演练（至少一次）？
- 回滚时间是否在 SLA 范围内？
- 数据回滚是否已考虑（schema 变更、数据迁移）？

### 4. 用户影响
- Breaking change 是否有迁移指南？
- 用户通知是否已发出？
- 监控和告警是否已配置？

## 审查流程

1. **读取产出物**：加载发布检查清单、changelog、回滚方案
2. **逐维度审查**：按上述 4 个维度检查
3. **标注发现**：BLOCKING / WARNING / SUGGESTION
4. **输出审查结论**：APPROVED / NEEDS_CHANGE / BLOCKED
5. **返回 Coordinator**：审查报告 + 结论

**事实依据红线**：
- 发布 APPROVED 只能基于可复查事实：命令输出、CI/测试结果、tag/commit、release docs、风险/证据记录。
- 未实际运行的检查 MUST 标为“未验证/待验证/BLOCKED”，不得写成通过。
- 禁止用假设、猜测、推测、估计、编造或幻觉替代发布证据。

## 审查结论

- **APPROVED**：发布就绪，可以执行
- **NEEDS_CHANGE**：存在需修复的发布风险
- **BLOCKED**：不可发布，需回退到开发/测试阶段修复

## 自检

- [ ] 所有 Gate 是否通过？CI 是否绿色？
- [ ] 回滚方案是否可执行（非理论）？
- [ ] Breaking change 是否有迁移指南？
- [ ] 监控告警是否已配置且可触发？
