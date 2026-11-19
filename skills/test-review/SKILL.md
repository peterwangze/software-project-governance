---
name: test-review
description: 独立审查测试策略、用例与运行回执能否证明验收条件，用于初审及返工后的复审。
---

# 测试审查

本 SKILL 用于测试与质量保障（stage-testing）阶段的独立测试审查。由 Reviewer Agent 执行。

## 循环角色

版本背景：本循环语义于 0.65.0 引入；本标题是稳定规范，不随版本号变更。

**角色映射：** 在目标 Loop 模型中，本审查对应质量子迭代的 `loop-body` + `loop-exit-gate`。0.66.1 的当前运行能力仍是 experimental scaffolding；该映射不表示持久化 Loop runtime 已激活。

当前可执行行为仅为 Coordinator M7.4 的 `NEEDS_CHANGE -> 返工 -> 复审`，以及 Check 30 对复审链终态、轮次连续性和熔断结果的校验。

<!-- loop-runtime-target:{"claim_id":"LRC-TEST-PLANNED-001","target_version":"0.68.0","status":"planned_not_active"} -->
持久化 `testing-to-development-rework` back-edge、flow-unit `loop_count`、Middle fuse、PARO transition 与自动升级属于 0.68.0 规划，当前不生效。

Reviewer 只审查并输出结论，不修改产品代码。Reviewer 必须输出 `APPROVED`、`APPROVED_WITH_NOTES`、`NEEDS_CHANGE` 或 `BLOCKED`；`APPROVED_WITH_NOTES` 是保留备注的通过终态，只能用于没有未解决 BLOCKING finding 的审查，不得包含未解决的 BLOCKING finding。`APPROVED_WITH_NOTES` 的审查输出与 REVIEW 证据 MUST 包含独立结构字段 `unresolved_blockers=0`；字段缺失、非零、非法或重复矛盾时不得通过，自然语言中偶然出现的 `blocking` 不构成该事实。`NEEDS_CHANGE`（及兼容输入 `NEEDS_CHANGES`）不是终态，Coordinator 必须在返工后发起下一轮复审。终态证据由 Check 30 的复审链消费：`APPROVED` 与 `APPROVED_WITH_NOTES` 可以通过并结束复审链；`BLOCKED` 结束链路但不是通过，必须 escalation；`NEEDS_CHANGE(S)`、未知或格式错误结论必须 fail-closed。超过复审 fuse 的 `NEEDS_CHANGE` 必须升级为 `BLOCKED`。

依据 ADR §3.5（loop-engineering-architecture-0.65.0）。完整映射见 [共享循环角色映射](../software-project-governance/references/loop-role-mapping.md)。

## 审查对象与方法

取得本轮工单、验收标准以及已有测试计划、关键用例、执行输出。将 QA 的每项结论与实际证据核对，按以下四个维度说明适用性和剩余风险。

| 维度 | 独立审查的判据 |
| --- | --- |
| 覆盖完整性 | 从用户实际入口把验收条件逐项追到断言及结果，检查契约要求的边界和异常。给出一个能让错误实现仍通过测试的具体输入时，说明遗漏的行为及影响。 |
| 测试独立性 | 确认测试数据、环境和依赖可隔离。检查测试替身是否替代了当前要验证的行为，结果是否依赖前次运行。 |
| 性能与安全 | 按[测试阶段的量化判定](../stage-testing/SKILL.md#量化判定)核对目标上下限、单位、采样和基线的可比性。核对项目要求的安全证据和已知关键风险。正式 G7 逐项复核完整门禁。 |
| 可维护性 | 确认后续执行者能从现有入口复验关键用例，输出可区分失败、跳过和实测通过。 |

## 审查结论

对每项发现标注 BLOCKING、WARNING 或 SUGGESTION，列出依据、用户影响和消除疑点所需的验证。缺少必需证据时标明具体缺口及责任方。范围内可补证的阻塞返回 `NEEDS_CHANGE`；必须升级裁决或已达复审熔断条件时返回 `BLOCKED`。已满足约定条件时返回 `APPROVED`；保留非阻塞备注时使用 `APPROVED_WITH_NOTES` 并给出独立字段 `unresolved_blockers=0`。结论交给 Coordinator，由其按前述协议登记、派返工或升级。
