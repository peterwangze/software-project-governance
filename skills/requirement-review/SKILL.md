---
name: requirement-review
description: 需求审查——对立项和调研阶段的产出物进行独立审查。覆盖PR/FAQ、OKR、需求澄清报告、竞品分析。质量保障SKILL，由Reviewer Agent调用。
---

# 需求审查

本 SKILL 用于立项（stage-initiation）和调研（stage-research）阶段的独立需求审查。由 Reviewer Agent 执行，不修改任何文件——仅输出审查结论。

## 循环角色

版本背景：本循环语义于 0.65.0 引入；本标题是稳定规范，不随版本号变更。

**角色映射：** 在目标 Loop 模型中，本审查对应 `loop-setup` 与首个 Middle loop 的 `loop-entry-gate`。0.66.1 的当前运行能力仍是 experimental scaffolding；该映射不表示持久化 Loop runtime 已激活。

当前可执行行为仅为 Coordinator M7.4 的 `NEEDS_CHANGE -> 返工 -> 复审`，以及 Check 30 对复审链终态、轮次连续性和熔断结果的校验。

<!-- loop-runtime-target:{"claim_id":"LRC-REQUIREMENT-PLANNED-001","target_version":"0.68.0","status":"planned_not_active"} -->
持久化 back-edge、flow-unit `loop_count`、setup fuse、PARO transition 与自动升级属于 0.68.0 规划，当前不生效。

Reviewer 只审查并输出结论，不修改产品代码。Reviewer 必须输出 `APPROVED`、`APPROVED_WITH_NOTES`、`NEEDS_CHANGE` 或 `BLOCKED`；`APPROVED_WITH_NOTES` 是保留备注的通过终态，只能用于没有未解决 BLOCKING finding 的审查，不得包含未解决的 BLOCKING finding。`APPROVED_WITH_NOTES` 的审查输出与 REVIEW 证据 MUST 包含独立结构字段 `unresolved_blockers=0`；字段缺失、非零、非法或重复矛盾时不得通过，自然语言中偶然出现的 `blocking` 不构成该事实。`NEEDS_CHANGE`（及兼容输入 `NEEDS_CHANGES`）不是终态，Coordinator 必须在返工后发起下一轮复审。终态证据由 Check 30 的复审链消费：`APPROVED` 与 `APPROVED_WITH_NOTES` 可以通过并结束复审链；`BLOCKED` 结束链路但不是通过，必须 escalation；`NEEDS_CHANGE(S)`、未知或格式错误结论必须 fail-closed。超过复审 fuse 的 `NEEDS_CHANGE` 必须升级为 `BLOCKED`。

依据 ADR §3.5（loop-engineering-architecture-0.65.0）。完整映射见 [共享循环角色映射](../software-project-governance/references/loop-role-mapping.md)。

## 审查对象

| 产出物 | 来源阶段 | 审查重点 |
|--------|---------|---------|
| PR/FAQ | 立项 | 用户价值是否清晰？假设是否可验证？范围是否明确？ |
| OKR | 立项 | 目标是否量化？关键结果是否可衡量？基线数据是否真实？ |
| 需求澄清报告 | 立项 | 边界条件是否完整？验收标准是否可测试？ |
| 竞品分析 | 调研 | 竞品覆盖是否全面？差异化分析是否有数据支撑？ |

## 审查维度

### 1. 目标一致性
- 项目目标是否与组织的战略方向一致？
- 成功标准是否为量化指标（非定性描述）？
- 是否有明确的"不做什么"的范围声明？

### 2. 需求可行性
- 技术可行性是否已初步验证？
- 资源约束（时间/人力/预算）是否已识别？
- 关键假设是否有验证计划？

### 3. 风险识别
- 需求层面的风险是否已识别（市场风险、技术风险、依赖风险）？
- 是否有风险缓解策略？
- 高风险假设是否有早期验证方案？

### 4. 质量基线
- 验收标准是否可测试？
- 非功能需求是否已考虑（性能/安全/可用性）？
- 是否定义了"完成"的明确标准？

## 审查流程

1. **读取产出物**：加载被审查阶段的产出物文件
2. **逐维度审查**：按上述 4 个维度逐一检查
3. **标注发现**：每条发现标注严重级别（BLOCKING/WARNING/SUGGESTION）
4. **输出审查结论**：APPROVED / APPROVED_WITH_NOTES / NEEDS_CHANGE / BLOCKED
5. **返回 Coordinator**：审查报告 + 结论

## 审查结论

- **APPROVED**：零 BLOCKING 问题，需求清晰可行
- **APPROVED_WITH_NOTES**：零未解决 BLOCKING finding；保留并跟踪非阻塞备注后通过
- **NEEDS_CHANGE**：有 BLOCKING 问题，逐条列出修复建议
- **BLOCKED**：需求层面存在根本性问题，需重新定义项目范围

## 自检

- [ ] 所有 PR/FAQ 中的假设是否可验证？
- [ ] OKR 的关键结果是否有基线数据？
- [ ] 需求边界是否明确（IN scope vs OUT of scope）？
- [ ] 验收标准是否具体到可测试？
