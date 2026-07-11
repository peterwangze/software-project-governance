---
name: test-review
description: 测试审查——对测试策略、测试计划、测试用例进行独立审查。覆盖测试阶段。质量保障SKILL，由Reviewer Agent调用。
---

# 测试审查

本 SKILL 用于测试与质量保障（stage-testing）阶段的独立测试审查。由 Reviewer Agent 执行。

## 循环角色

版本背景：本循环语义于 0.65.0 引入；本标题是稳定规范，不随版本号变更。

**Gate 语义：** 质量子迭代的 Middle loop 的 `loop-body` + `loop-exit-gate`（每个 flow unit 的缺陷关闭与回归通过）。本审查认证 Middle loop 的**质量子迭代已收敛**：flow unit 的缺陷已关闭且回归测试通过。

审查失败不会终止阶段；它会经 `testing-to-development-rework` 返回所属循环（Inner loop）继续迭代（返工 → 重测），并递增 `loop_count`。只有当 `loop_count` 超过 Middle fuse 时，失败才升级而不是继续迭代。

Reviewer 只审查并输出结论，不修改产品代码。Reviewer 必须输出 `APPROVED`、`APPROVED_WITH_NOTES`、`NEEDS_CHANGE` 或 `BLOCKED`；`APPROVED_WITH_NOTES` 是保留备注的通过终态，只能用于没有未解决 BLOCKING finding 的审查，不得包含未解决的 BLOCKING finding。`APPROVED_WITH_NOTES` 的审查输出与 REVIEW 证据 MUST 包含独立结构字段 `unresolved_blockers=0`；字段缺失、非零、非法或重复矛盾时不得通过，自然语言中偶然出现的 `blocking` 不构成该事实。`NEEDS_CHANGE`（及兼容输入 `NEEDS_CHANGES`）不是终态，Coordinator 必须在返工后发起下一轮复审。终态证据由 Check 30 的复审链消费：`APPROVED` 与 `APPROVED_WITH_NOTES` 可以通过并结束复审链；`BLOCKED` 结束链路但不是通过，必须 escalation；`NEEDS_CHANGE(S)`、未知或格式错误结论必须 fail-closed。超过复审 fuse 的 `NEEDS_CHANGE` 必须升级为 `BLOCKED`。

依据 ADR §3.5（loop-engineering-architecture-0.65.0）。完整映射见 [共享循环角色映射](../software-project-governance/references/loop-role-mapping.md)。

## 审查对象

| 产出物 | 审查重点 |
|--------|---------|
| 测试策略文档 | 测试金字塔是否合理？各层测试比例是否恰当？ |
| 测试计划 | 覆盖范围是否完整？环境/数据/工具是否就绪？ |
| 测试用例（关键路径） | 正向/反向/边界用例是否充分？ |
| 性能测试方案 | 指标基线是否定义？负载模型是否合理？ |

## 审查维度

### 1. 覆盖完整性
- 功能测试是否覆盖所有验收标准？
- 边界条件是否测试（空值/极值/超时/并发）？
- 异常路径是否测试（网络故障/服务不可用/数据损坏）？

### 2. 测试独立性
- 测试是否可独立运行（不依赖执行顺序）？
- 测试数据是否与生产数据隔离？
- Mock/Stub 是否合理且不过度？

### 3. 性能与安全
- 是否有性能基线对比（当前 vs 目标）？
- 安全测试是否覆盖 OWASP Top 10 关键项？
- 是否有负载测试和压力测试方案？

### 4. 可维护性
- 测试代码是否符合与产品代码相同的质量标准？
- 是否有测试辅助工具/脚本的文档？
- CI 中测试是否可自动运行？

## 审查流程

1. **读取产出物**：加载测试策略、计划、关键用例
2. **逐维度审查**：按上述 4 个维度检查
3. **标注发现**：BLOCKING / WARNING / SUGGESTION
4. **输出审查结论**：APPROVED / APPROVED_WITH_NOTES / NEEDS_CHANGE / BLOCKED
5. **返回 Coordinator**：审查报告 + 结论

## 审查结论

- **APPROVED**：测试策略充分，可以进入 CI/CD 阶段
- **APPROVED_WITH_NOTES**：无未解决 BLOCKING finding；保留并跟踪非阻塞测试备注后通过
- **NEEDS_CHANGE**：存在测试缺口，补充后重新审查
- **BLOCKED**：测试覆盖严重不足，不可发布

## 自检

- [ ] 所有验收标准是否都有对应的测试用例？
- [ ] 是否有边界条件测试？异常路径测试？
- [ ] 性能基线是否量化且可对比？
- [ ] CI 中测试是否可自动运行？
