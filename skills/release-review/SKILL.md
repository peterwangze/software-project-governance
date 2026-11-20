---
name: release-review
description: 显式版本发布时核对候选身份、风险、授权和恢复。
---

# 独立签核实际候选

## 循环角色

显式发布单元（`release_version`）在中层 G8、G9 由 Release Reviewer 核对保护、候选版本、回滚和当次授权。普通交付目标（`delivery_goal`）在 G9 消费独立成品验收者按冻结契约出具的回执。 独立 Reviewer 按[共享签核规则](../software-project-governance/references/loop-role-mapping.md)记录本轮回执与未解决阻断数。

Release Reviewer 复读版本、待发制品和相应签核，核对当前候选是否就是已验收者。对本次范围所需的构建、CI、数据变更和恢复方式查原件；存在阻断时列明哪个对象要重测。

正式签核记录候选、版本、审查者和结论。发布者核实用户对实际环境的授权。普通成品的独立交付回执由接收该成品的验收者出具。
