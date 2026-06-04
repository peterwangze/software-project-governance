# Feature Flag 状态 — 0.43.0

**版本**: 0.43.0

## Runtime Feature Flags

无。0.43.0 不引入运行时 feature flag。

## 行为开关

无新增可配置行为开关。0.43.0 是 Cross-Harness E2E Closure release package，只同步 version declarations、snapshot freshness guard、runtime/readiness matrix、first-session measurement guard、README measured-state pointers、CHANGELOG、release docs、target fixture/projection 和 release gate 期望。

## 非目标

- 不提交到任何 marketplace。
- 不声明 official approval 或 marketplace approval。
- 不声明 universal/full runtime support。
- 不声明 external first-session pilot PASS；当前 measured state 是 local_demo=PASS、external_pilot=NOT_MEASURED。
- 不新增 telemetry、hosted backend、外部 policy URL 或 legal terms URL。
- 不关闭 RISK-036。
- 不创建 1.0.0 changes。

## 回滚

紧急回滚方式见 `docs/release/rollback-plan-0.43.0.md`。
