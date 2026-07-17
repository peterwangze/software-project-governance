# 审查 SKILL 循环角色映射

版本背景：本映射随 0.65.0 的 loop-engineering 架构引入；本文档标题与七个审查 SKILL 的 `## 循环角色` 一样是稳定语义，不随版本号更新。

本文档是七个审查 SKILL 的目标 Loop 角色映射事实源。依据 AUDIT-133、EVD-707 与 DEC-104，0.66.1 的 Loop Engineering 定位是 **experimental scaffolding**：runtime activation 为 NOT_MET，migration validity 为 NOT_MET。角色映射不表示持久化 Loop runtime 已激活。

依据 ADR §3.5（`docs/requirements/loop-engineering-architecture-0.65.0-proposed.md` 的 §3.5 与 §4 是逐阶段映射的权威来源）。

## 为什么需要此映射

在 0.51.0-0.55.0，七个审查 SKILL 将 gate 描述为“检查阶段 X”。0.65.0 引入了目标 Loop 角色词汇，但后续审计未证明通用持久化回边、per-unit `loop_count`、tier fuse、PARO transition 或自动升级已经接入生产执行链。当前可执行范围仅是 Coordinator M7.4 的返工/复审，以及 Check 30 对复审链的校验。

<!-- loop-runtime-target:{"claim_id":"LRC-MAPPING-PLANNED-001","target_version":"0.68.0","status":"planned_not_active"} -->
通用持久化 back-edge、flow-unit `loop_count`、tier fuse、PARO transition 与 automatic escalation 是 0.68.0 planned-not-active 行为。

## 术语（ADR §4）

“角色”只使用以下四个值：

- `loop-setup`：一次性、非迭代的准备；立项是唯一的非循环。
- `loop-body`：循环内反复执行的工作。
- `loop-exit-gate`：认证循环的退出条件。
- `loop-entry-gate`：认证进入下一个循环的条件。

## 七个审查 SKILL 的循环角色（ADR §3.5）

| SKILL | 旧语义（检查阶段） | 新循环角色 | 认证的循环 | gate 认证的含义 |
|---|---|---|---|---|
| `requirement-review` | 检查立项产出物 | `loop-setup`（并作为第一个 Middle 的 `loop-entry-gate`） | 立项（非循环） | 认证立项准备已完成，是 setup-loop 的进入门，位于第一个 Middle loop 之前；本身不迭代。 |
| `design-review` | 检查架构阶段 | `loop-entry-gate` | Middle（进入） | 认证 Middle loop 的进入条件：设计收敛，可以开始构建当前 flow unit；失败时在设计子循环中重新设计，不终止项目。 |
| `tech-review` | 检查技术选型或设计质量 | `loop-entry-gate` | Middle（进入，技术深度） | 认证 Middle loop 的设计子迭代已收敛：PoC、备选方案和蓝军挑战已验证风险驱动的深度。 |
| `code-review` | 检查开发阶段 | `loop-exit-gate` | Inner（退出） | 认证 Inner loop 的退出条件：切片或提交可合并；失败时在 Inner loop 中返工并复审；Inner `max_rounds=5`。 |
| `test-review` | 检查测试阶段 | `loop-body` + `loop-exit-gate` | Middle（主体，质量） | 认证 Middle loop 的质量子迭代已收敛：缺陷关闭、回归通过；失败经 `testing-to-development-rework` 返回 Inner loop。 |
| `release-review` | 检查发布阶段 | `loop-exit-gate`（Middle）/`loop-entry-gate`（Outer） | Middle（退出）/ Outer（进入） | 认证 Middle loop 的退出条件（flow unit 可发布）以及 Outer loop 的运营度量进入条件；失败经 `release-to-testing-rework` 返回测试子循环。 |
| `retro-review` | 检查维护阶段 | `loop-exit-gate` | Outer（退出） | 认证 Outer loop 的迭代收敛：经验回灌、下一轮方向确定；失败经 `operations-feedback-to-maintenance-loop` 使 Outer loop 继续迭代。 |

## 可执行审查契约

1. Reviewer 只审查并输出结论，不修改产品代码；修复由所属循环中的实现角色完成。
2. Reviewer 输出 `APPROVED`、`APPROVED_WITH_NOTES`、`NEEDS_CHANGE` 或 `BLOCKED`。`APPROVED_WITH_NOTES` 是保留备注的通过终态，只能用于没有未解决 BLOCKING finding 的审查；其审查输出与 REVIEW 证据 MUST 包含独立结构字段 `unresolved_blockers=0`，字段缺失、非零、非法或重复矛盾时不得通过。自然语言中偶然出现的 `blocking` 不构成该事实。`NEEDS_CHANGE`（及兼容输入 `NEEDS_CHANGES`）不是终态：Coordinator 必须将工作返回所属循环，完成返工后发起下一轮复审。
3. 审查结论写入证据记录，并由 Check 30 的复审链消费。`APPROVED` 与 `APPROVED_WITH_NOTES` 可以通过并结束复审链；`BLOCKED` 结束链路但不是通过；`NEEDS_CHANGE(S)`、未知或格式错误结论必须 fail-closed。超过 Check 30 复审轮次限制的 `NEEDS_CHANGE` 由 Coordinator 升级为 `BLOCKED`。
4. 第 3 条是当前已执行的审查链事实；它不能作为通用 Loop runtime、持久化 `loop_count`、tier fuse 或 PARO 自动转换已实现的证据。

## 相关依据

- ADR §3.5：gate 作为循环退出/进入语义。
- ADR §4：完整 G1-G11 stage 到 loop-role 映射表。
- ADR §3.3：setup-loop（调研、选型、基础设施）及 `MAX_SETUP_ROUNDS=2`。
- ADR §8：各循环层级的 loop fuse（`MAX_ROUNDS`）。
- Check 30：`verify_workflow.py` 的复审终态状态机，消费审查链并校验轮次连续性、fuse 与终态合法性。
