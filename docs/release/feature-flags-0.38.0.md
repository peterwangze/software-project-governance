# Feature Flag 状态 — 0.38.0

**版本**: 0.38.0
**日期**: 2026-05-28

## Feature Flags

无。0.38.0 不引入运行时 feature flag。

## 行为变化

- `check-governance` 对当前 release 产品代码证据执行 structured evidence schema 检查。
- `check-governance` 要求活跃 P0/P1 任务存在 execution packet。
- 降级审查、自审和缺独立 Reviewer 标识的 review-like 记录不再解锁产品代码任务。
- 发布前 `check-release` 会检查 projection sync 与 hot fact source consistency。

## 回滚

紧急回滚方式见 `docs/release/rollback-plan-0.38.0.md`。
