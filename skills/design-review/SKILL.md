---
name: design-review
description: 设计审查——对技术选型、系统设计、ADR 进行独立审查。覆盖选型、基础设施、架构设计阶段。质量保障SKILL，由Reviewer Agent调用。
---

# 设计审查

本 SKILL 用于技术选型（stage-selection）、基础设施（stage-infra）和架构设计（stage-architecture）阶段的独立设计审查。由 Reviewer Agent 执行。

## 循环角色

版本背景：本循环语义于 0.65.0 引入；本标题是稳定规范，不随版本号变更。

**角色映射：** 在目标 Loop 模型中，本审查对应 flow unit Middle loop 的 `loop-entry-gate`。0.66.1 的当前运行能力仍是 experimental scaffolding；该映射不表示持久化 Loop runtime 已激活。

当前可执行行为仅为 Coordinator M7.4 的 `NEEDS_CHANGE -> 返工 -> 复审`，以及 Check 30 对复审链终态、轮次连续性和熔断结果的校验。

<!-- loop-runtime-target:{"claim_id":"LRC-DESIGN-PLANNED-001","target_version":"0.68.0","status":"planned_not_active"} -->
持久化 back-edge、flow-unit `loop_count`、Middle fuse、PARO transition 与自动升级属于 0.68.0 规划，当前不生效。

Reviewer 只审查并输出结论，不修改产品代码。Reviewer 必须输出 `APPROVED`、`APPROVED_WITH_NOTES`、`NEEDS_CHANGE` 或 `BLOCKED`；`APPROVED_WITH_NOTES` 是保留备注的通过终态，只能用于没有未解决 BLOCKING finding 的审查，不得包含未解决的 BLOCKING finding。`APPROVED_WITH_NOTES` 的审查输出与 REVIEW 证据 MUST 包含独立结构字段 `unresolved_blockers=0`；字段缺失、非零、非法或重复矛盾时不得通过，自然语言中偶然出现的 `blocking` 不构成该事实。`NEEDS_CHANGE`（及兼容输入 `NEEDS_CHANGES`）不是终态，Coordinator 必须在返工后发起下一轮复审。终态证据由 Check 30 的复审链消费：`APPROVED` 与 `APPROVED_WITH_NOTES` 可以通过并结束复审链；`BLOCKED` 结束链路但不是通过，必须 escalation；`NEEDS_CHANGE(S)`、未知或格式错误结论必须 fail-closed。超过复审 fuse 的 `NEEDS_CHANGE` 必须升级为 `BLOCKED`。

依据 ADR §3.5（loop-engineering-architecture-0.65.0）。完整映射见 [共享循环角色映射](../software-project-governance/references/loop-role-mapping.md)。

## 审查对象

| 产出物 | 来源阶段 | 审查重点 |
|--------|---------|---------|
| 技术选型报告 | 选型 | 选型依据是否充分？备选方案是否公允？PoC 结果是否可信？ |
| ADR（架构决策记录） | 架构设计 | 决策背景是否完整？备选方案是否列出？选择理由是否充分？ |
| 系统设计文档 | 架构设计 | 模块拆分是否合理？接口契约是否明确？数据流是否清晰？ |
| 基础设施方案 | 基础设施 | 环境配置是否可复现？工具链是否就绪？CI 基础是否可用？ |

## 审查维度

### 1. 设计合理性
- 模块拆分是否符合单一职责原则？
- 接口设计是否最小化、可版本化？
- 数据模型是否满足当前需求且有扩展空间？

### 2. 技术债务评估
- 是否有刻意承担的技术债务？是否有偿还计划？
- 选型是否存在"过度工程"（为不需要的规模设计）？
- 依赖是否最小化且版本锁定？

### 3. 安全与合规
- 认证/授权方案是否明确？
- 敏感数据是否有保护策略？
- 第三方依赖是否有安全审计？

### 4. 可演进性
- 设计是否支持未来的扩展方向？
- 是否有明确的废弃/迁移路径？
- 是否有性能瓶颈的预估和应对？

## 审查流程

1. **读取产出物**：加载 ADR、设计文档、选型报告
2. **逐维度审查**：按上述 4 个维度检查
3. **标注发现**：BLOCKING（设计级缺陷）/ WARNING（潜在风险）/ SUGGESTION（改进建议）
4. **输出审查结论**：APPROVED / APPROVED_WITH_NOTES / NEEDS_CHANGE / BLOCKED
5. **返回 Coordinator**：审查报告 + 结论

**事实依据红线**：
- 所有设计审查结论 MUST 引用可复查事实：ADR 段落、代码/配置文件、命令输出、PoC 结果、日志或用户明确输入。
- 无法验证的前提 MUST 标为“未验证/待验证/BLOCKED”，不得作为 APPROVED 的依据。
- 禁止用假设、猜测、推测、估计、编造或幻觉替代事实依据。

## 审查结论

- **APPROVED**：设计合理，可以进入开发
- **APPROVED_WITH_NOTES**：无未解决 BLOCKING finding；保留并跟踪非阻塞备注后通过
- **NEEDS_CHANGE**：存在需要修复的设计问题，修复后重新审查
- **BLOCKED**：设计存在根本性缺陷，需重新设计

## 自检

- [ ] 所有 ADR 的备选方案是否都已列出并分析？
- [ ] 接口契约是否有版本化策略？
- [ ] 安全方案是否覆盖 OWASP Top 10 关键项？
- [ ] 是否有被忽略的非功能需求（性能/扩展性/可维护性）？
