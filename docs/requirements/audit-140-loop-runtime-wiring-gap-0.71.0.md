<!-- loop-runtime-target: status=planned_not_active subject=audit scope=documentation-only version=0.71.0 -->
# AUDIT-140: Loop Engineering 生产接线缺口——process_gate_result 调用点仍为 0

> **触发**: 用户反馈"Developer 修改检视意见之后未触发复审" + "单点任务完成后直接结束未衔接后续推荐"
> **关联**: AUDIT-133（原"call sites = 0"发现）, FEAT-006（gate processor 实现）, ADR-014 §6（四接线点设计）, RISK-042（评估详见 §1.4）, DEC-104

## 1. 核心发现

### 1.1 process_gate_result 生产调用点 = 0（CONFIRMED）

在 0.70.0 代码中枚举 `process_gate_result(` 的所有调用方：
- `loop_gate_processor.py:69` — 模块 **docstring** 示例，非真实调用
- `loop_gate_processor.py:396` — `def` 定义本身
- `tests/test_loop_gate_processor.py` — 35+ 单元测试调用
- `tests/test_loop_event_log.py` — 4 测试调用
- `.governance/val008_dogfood_driver.py:237,264` — VAL-008 dogfood harness（temp dir，不触碰真实 .governance/）

**Coordinator 路径、agent-dispatch 路径、evidence-log writer、review-skill conclusion 路径、gate-engine 路径、git hook——全部无调用。** AUDIT-133 的"核心 loop API 生产调用点 = 0"在 0.70.0 中**仍字面成立**。

### 1.2 FEAT-006 只接线 wiring point C

ADR-014 §6 设计了 4 个接线点：
- (A) review-skill 结论 → process_gate_result — **未接线**
- (B) gate-engine auto_judge_gate → process_gate_result — **未接线**（auto_judge_gate 是 standalone CLI，行 14557，不调 loop state machine）
- (C) check_release_readiness / Check 28 系统级 fuse block — **已接线**（唯一）
- (D) agent phase transitions — **未接线**

wiring point C 是纯读防御（已在 tripped 的 fuse 上 fail release），但因为没有调用者 trip fuse（A/B/D 缺失），它永远不触发——是一个等待永不到达的输入的死锁。

### 1.3 M7.4 step 4.6 复审状态机是纯 prose

behavior-protocol.md 行 493-536 描述 NEEDS_CHANGE → 返工 → Coordinator MUST re-spawn same Reviewer（round+1）。这是**指向 Coordinator LLM 的 prose**——没有脚本检测 NEEDS_CHANGE 结果并强制 re-spawn。

Check 30（review_domain.py:1755 check_review_closure）只**验证已记录的**复审链格式（V1 终态/V2 轮次连续/V3 熔断/V4 APPROVED 可追溯），**不触发**复审。如果 Coordinator 只记录 R0 然后停止，Check 30 没有 R1 来标记缺失（除非 R0 显式标为 NEEDS_CHANGE——但这依赖 Coordinator 记录行为）。

### 1.4 RISK-042 关闭标准评估

RISK-042 于 2026-07-26 关闭（DEC-133），关闭标准"production gate failure 持久化 back-edge/round"标记 PASS。但：
- VAL-008 dogfood driver 在 temp dir 手动驱动 PARO 链 + 手动调用 process_gate_result——**非生产调用者**
- 关闭标准被起草为"引擎模块被调用时功能正确"——确实正确（VAL-008 证明）
- 但标准**未要求**"非测试生产调用者存在"

这与 RISK-043 的关闭类似（范围 vs 字面解释）——技术上关闭有效，但标准低估了"生产接线"的含义。建议：修正 RISK-042 关闭备注，诚实记录"call sites 仍为 0"，但保持关闭状态（引擎功能正确 + 外部验证通过），将"生产接线"作为独立后续任务。

### 1.5 无 outer loop 运行时

loop tiers（setup/inner/middle/outer）描述 **per-unit 迭代语义**，不是 task-to-task 序列。registry `back_edges` 只定义一个 `release-to-design-replan`（auto_fire=false，需人工批准）。无代码/schema 说"flow unit X exit inner loop → return to middle/outer loop recommend next unit"。

M7.4 step 6（行 544）"继续 plan-tracker 中下一个最高优先级任务"是纯 prose。interaction-boundary.md:217 **明确禁止**"任务完成后停下来问接下来做什么"——正确行为是"查 plan-tracker，取下一个最高优先级未完成任务继续执行"。但这依赖 LLM 遵守一条直接对抗其训练分布的规则。

## 2. 根因总结

| 症状 | 表层原因 | 根因 |
|------|---------|------|
| 修改后不复审 | M7.4 step 4.6 是 prose；process_gate_result 0 生产调用 | ADR-014 §6 接线点 A/B/D 从未实现；FEAT-006 只接 C |
| 任务完成后停止 | 无 outer loop 运行时；step 6 纯 prose | loop tiers 非 task 序列；"continue next task"仅靠 LLM 自觉 |

## 3. 修复方向

### FIX-223: task-completion→next-priority 显式步骤
在 behavior-protocol.md / SKILL.md 中加入 task-completion→next-priority 推荐的**显式步骤**，升级为可 Check 验证的规则（不只是"继续最高优先级"，而是"分析依赖→推荐最合理下一步→AskUserQuestion 呈现"）。

### FIX-224: review 复审确定性触发器
在 behavior-protocol.md M7.4 step 4.6 加入"NEEDS_CHANGE 结果 → MUST re-spawn same Reviewer"的**确定性触发条件**（M5.1b 风格——关键词检测+规则），并补充 Check 21/30 对"NEEDS_CHANGE 后无 R1"的检测。

### Loop runtime 生产接线（0.72.0+ 独立主题）
wiring points A/B/D 的完整实现（review 结论→process_gate_result、gate engine→process_gate_result、agent phase→PARO transition）是更大的工程，适合独立版本。
