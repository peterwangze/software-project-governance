# 回滚方案 — 0.35.0

**版本**: 0.35.0
**发布日期**: 2026-05-20
**回滚目标**: v0.34.0

## 回滚触发条件

- 0.35.0 发布后 `check-release --runtime-adapters` 出现阻断性失败。
- adapter runtime contract 或 `e2e-check` 分层报告导致用户项目无法初始化或验证。
- 版本声明漂移导致 plugin install/update 读取到不一致版本。

## 回滚步骤

1. 回退到 v0.34.0 tag：

```bash
git fetch --tags
git checkout v0.34.0
```

2. 如需在 `master` 上发布回滚提交，将版本声明恢复为 0.34.0：

```bash
git revert <0.35.0-release-commit>
```

3. 如 tag 已推送且必须撤销：

```bash
git tag -d v0.35.0
git push origin :refs/tags/v0.35.0
```

4. 验证回滚后的门禁：

```bash
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py verify
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py e2e-check
```

## 数据兼容性

0.35.0 不引入治理文件格式破坏性变更。新增的 adapter `runtime_e2e` 双块为 manifest 元数据增强；旧版本回滚后会回到 0.34.0 的 runtime-version-probe/unsupported 口径。

## 用户沟通

回滚公告需要明确：0.35.0 的主要目标是 E2E 真实性分层和防夸大，不是 1.0.0 production-ready 声明；回滚不影响 1.0.0 外部验证门槛。
