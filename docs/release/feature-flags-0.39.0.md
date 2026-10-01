# Feature Flag 状态 — 0.39.0

**版本**: 0.39.0
**日期**: 2026-05-30

## Feature Flags

无。0.39.0 不引入运行时 feature flag。

## 行为变化

- `check-governance` 要求活跃 P0/P1 任务具备 Product Success Contract。
- `check-governance` 要求活跃 P0/P1 任务具备可执行验收契约和最近运行结果。
- `check-governance` 要求活跃 P0/P1 任务具备六维 Quality Budget。
- `check-governance` 要求活跃 P0/P1 任务具备用户可见 Vertical Slice。
- `check-governance` 会验证三类 Weak-LLM Deterministic Scaffolds。
- `check-governance` 会验证 User Interruption Policy v2 和 execution packet interruption policy。

## 回滚

紧急回滚方式见 `docs/release/rollback-plan-0.39.0.md`。
