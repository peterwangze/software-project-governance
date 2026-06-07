# Feature Flag 状态 — 0.44.0

**版本**: 0.44.0

## Runtime Feature Flags

无。0.44.0 不引入运行时 feature flag。

## 行为开关

无新增可配置行为开关。0.44.0 是 Composable Governance Packs release package，采用 registry-first/no physical split：packs 作为能力模块进入 registry、README guidance、manifest/cleanup guard、status/release boundary 和 release readiness 检查，但不会要求用户在运行时切换新的 flag。

## Pack 状态

| Pack | 0.44.0 状态 | 边界 |
|------|-------------|------|
| `governance-core` | 默认进入 lite/standard/strict；包含 context-aware resume | 只基于事实源发现 unfinished work；无事实时必须 `not found` / `do not invent` |
| `quality-gates` | 默认进入 standard/strict | Pack membership 不是质量门禁通过证明 |
| `release-governance` | 默认进入 standard/strict | Pack membership 不是 release gate 通过证明 |
| `agent-team` | 默认进入 standard/strict | Host runtime degraded mode 仍必须如实披露 |
| `enterprise` | 默认进入 strict | Manifest/cleanup/artifact hygiene 不是外部认证或 marketplace approval |

## Kill Switch

紧急关闭路径是回滚 0.44.0 release commit 或恢复 0.43.0 release package baseline；没有独立 runtime flag 可关闭 pack registry。回滚方案见 `docs/release/rollback-plan-0.44.0.md`。

## 非目标

- 不进行物理拆包。
- 不提交到任何 marketplace。
- 不声明 official approval 或 marketplace approval。
- 不声明 universal/full runtime support。
- 不声明 external first-session pilot success。
- 不声明 Codex Desktop marketplace-management E2E PASS。
- 不新增 telemetry、hosted backend、外部 policy URL 或 legal terms URL。
- 不关闭 RISK-036。
- 不创建 1.0.0 changes。

## 回滚

紧急回滚方式见 `docs/release/rollback-plan-0.44.0.md`。
