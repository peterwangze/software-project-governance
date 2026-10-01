# Feature Flag 状态 — 0.35.0

**版本**: 0.35.0
**发布日期**: 2026-05-20

## Feature Flags

**无**。0.35.0 不引入运行时 feature flag。

## Kill Switch

**无**。本版本变更为治理规则、adapter metadata、launcher 输出、验证脚本和发布文档更新，不依赖线上 kill switch。

## 渐进启用说明

0.35.0 的新门禁随插件版本升级即时生效：

- `e2e-check` 输出 source CLI proxy、external target cwd 和 target fixture checks。
- adapter manifests 输出 `runtime_e2e.target_cwd_e2e` 与 `runtime_e2e.agent_runtime_e2e`。
- `full_e2e_verified=true` 必须有 target cwd 与 agent runtime 双 passed 证据。

Gemini/opencode 当前 blocked 状态是事实源，不是 feature flag 降级。用户配置 Gemini auth 或修正 opencode provider/model 后，可重新执行对应 agent runtime E2E 并更新证据。

## 回滚

紧急回滚方式见 `docs/release/rollback-plan-0.35.0.md`。
