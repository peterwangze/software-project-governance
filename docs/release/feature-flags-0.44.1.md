# Feature Flag 状态 — 0.44.1

**版本**: 0.44.1
**类型**: Patch release

## Runtime Feature Flags

无。0.44.1 不引入运行时 feature flag。

## 行为开关

无新增可配置行为开关。0.44.1 仅发布 FIX-113 和 FIX-114 的修复包：

- FIX-113: no-overclaim direct-claim 检查改为 claim-scoped negation，防止同一行无关否定词掩盖肯定式越界声明。
- FIX-114: governance context discovery 补齐 evidence-log 与 root-scoped git fact coverage，同时保持 historical evidence / parent repo do-not-invent 边界。

## Pack 状态

0.44.1 不改变 0.44.0 的 pack registry 语义、profile 映射或 physical split 状态。`governance-packs.json` 仅同步 `workflow_version` 和 release validation command 到 0.44.1。

| Pack | 0.44.1 状态 | 边界 |
|------|-------------|------|
| `governance-core` | 保持 0.44.0 默认状态；受 FIX-114 context discovery 修复保护 | 只基于事实源发现 unfinished work；不得从历史 evidence 或父仓库 git 状态发明当前工作 |
| `quality-gates` | 无变化 | Pack membership 不是质量门禁通过证明 |
| `release-governance` | 无变化；受 FIX-113 no-overclaim 修复保护 | Release checks 不是 official approval、marketplace approval、universal/full runtime support 或 1.0.0 readiness 证明 |
| `agent-team` | 无变化 | Host runtime degraded mode 仍必须如实披露 |
| `enterprise` | 无变化 | Manifest/cleanup/artifact hygiene 不是外部认证或 marketplace approval |

## Kill Switch

紧急关闭路径是回滚 0.44.1 release package commit，恢复到已发布的 0.44.0 package baseline；没有独立 runtime flag 可关闭本 patch。回滚方案见 `docs/release/rollback-plan-0.44.1.md`。

## 非目标

- 不改变 pack semantics 或 profile 映射。
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

紧急回滚方式见 `docs/release/rollback-plan-0.44.1.md`。
