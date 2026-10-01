# 回滚方案 — 0.42.0

**版本**: 0.42.0
**范围**: 5-Minute Success Path release package

## 回滚触发条件

- `check-release --version 0.42.0 --require-changelog --runtime-adapters` 在本地或干净 checkout 中失败。
- 发布后发现版本声明、canonical manifest、plugin manifests、hook @version 或 target fixture/projection 版本漂移。
- Delivery Trust Snapshot、first-run demo harness、README 5-Minute Start 或 release docs 被确认包含 official approval、marketplace approval、universal/full runtime support 或 1.0.0 production-ready 过度声明。
- 发布提交混入 0.43.0 cross-harness E2E、0.44.0 composable packs、0.45.0 benchmark、0.46.0 submission 或 1.0.0 changes。

## 回滚步骤

1. 回滚 0.42.0 发布提交：

```bash
git revert <0.42.0-release-commit>
```

2. 如 tag 已发布且必须撤销：

```bash
git tag -d v0.42.0
git push origin :refs/tags/v0.42.0
```

3. 复跑门禁并确认回到 0.41.0 package baseline：

```bash
python skills/software-project-governance/infra/verify_workflow.py verify
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.41.0 --require-changelog --runtime-adapters
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
git diff --check
```

## 数据边界

`.governance/` 是运行态记录，不随产品发布提交。本回滚只处理产品/release package 文件；历史 governance evidence 可保留，用于说明 0.42.0 的发布准备、验证与回滚事实。

## 风险边界

回滚 0.42.0 不关闭 RISK-036。该风险的关闭标准仍依赖官方提交包齐备、至少 2 个外部项目验证通过、主流入口矩阵公开且不夸大能力、README/manifest 能清晰表达 delivery trust layer 差异化。
