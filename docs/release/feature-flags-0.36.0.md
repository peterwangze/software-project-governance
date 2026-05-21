# Feature Flag 状态 — 0.36.0

**版本**: 0.36.0
**发布日期**: 2026-05-22

## Feature Flags

**无**。0.36.0 不引入运行时 feature flag。

## Kill Switch

**无**。本版本变更为治理规则、adapter metadata、launcher 输出、验证脚本、fixture 和发布文档更新，不依赖线上 kill switch。

## 渐进启用说明

0.36.0 的新门禁随插件版本升级即时生效：

- `agent-runtime-e2e` 可复跑 Claude/Codex/Gemini/opencode 四平台真实 runtime matrix。
- `gemini-auth-preflight` 在缺少 Gemini auth 时输出机器可读 BLOCKED guidance。
- `opencode-provider-preflight` 在 provider/model 配置回退时输出机器可读 BLOCKED guidance。
- Codex full coverage 只接受真实 `codex exec` target-cwd headless PASS，Codex App session 不能替代。

Codex/Gemini 当前 blocked 状态是事实源，不是 feature flag 降级。用户修复对应环境后，可重新执行 runtime E2E 并更新 adapter evidence。

## 回滚

紧急回滚方式见 `docs/release/rollback-plan-0.36.0.md`。
