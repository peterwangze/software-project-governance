# 回滚方案 — 0.40.1

**版本**: 0.40.1
**范围**: GitHub CI clean checkout hotfix patch

## 回滚触发条件

- `check-release --version 0.40.1 --require-changelog --runtime-adapters` 在本地或干净 checkout 中失败。
- 发布后 GitHub Governance CI 再次在 `Verify workflow integrity`、`Verify manifest consistency` 或 `Run unit tests` 失败，且失败根因来自 0.40.1 release packaging。
- 版本声明同步导致 plugin manifest、target fixture 或 hook @version 漂移。

## 回滚步骤

1. 回滚 0.40.1 发布提交：

```bash
git revert <0.40.1-release-commit>
```

2. 如 tag 已发布且必须撤销：

```bash
git tag -d v0.40.1
git push origin :refs/tags/v0.40.1
```

3. 复跑门禁：

```bash
python skills/software-project-governance/infra/verify_workflow.py verify
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.40.0 --require-changelog --runtime-adapters
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
```

## 数据边界

`.governance/` 是运行态记录，不随产品发布提交。回滚产品代码后，历史 governance evidence 可保留，用于说明 0.40.1 的发布与回滚事实。
