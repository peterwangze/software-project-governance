# 回滚方案 — 0.36.0

**版本**: 0.36.0
**发布日期**: 2026-05-22
**回滚目标**: v0.35.0

## 回滚触发条件

- 0.36.0 发布后 `agent-runtime-e2e` 或 `check-release --runtime-adapters` 出现阻断性失败。
- Codex/Gemini blocked 状态被误展示为 full coverage。
- opencode provider/model preflight 或 90s target-cwd E2E 在主机环境中不可复现，且影响用户判断适配状态。
- 版本声明漂移导致 plugin install/update 读取到不一致版本。

## 回滚步骤

1. 回退到 v0.35.0 tag：

```bash
git fetch --tags
git checkout v0.35.0
```

2. 如需在 `master` 上发布回滚提交，将版本声明恢复为 0.35.0：

```bash
git revert <0.36.0-release-commit>
```

3. 如 tag 已推送且必须撤销：

```bash
git tag -d v0.36.0
git push origin :refs/tags/v0.36.0
```

4. 验证回滚后的门禁：

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py verify
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py e2e-check
```

## 数据兼容性

0.36.0 不引入治理文件格式破坏性变更。新增的 `gemini-auth-preflight`、`opencode-provider-preflight` 和 adapter manifest preflight 字段均为验证能力增强；回滚到 0.35.0 后会回到原有 runtime_e2e 分层口径。

## 用户沟通

回滚公告需要明确：0.36.0 的主要目标是真实 agent runtime E2E 证据闭环和阻塞状态防夸大，不是 1.0.0 production-ready 声明；回滚不改变 Codex/Gemini 真实阻塞事实和 1.0.0 外部验证门槛。
