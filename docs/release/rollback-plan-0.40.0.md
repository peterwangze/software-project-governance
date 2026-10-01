# 回滚方案 — 0.40.0

**版本**: 0.40.0
**范围**: AI 指令精度收敛

## 回滚触发条件

- `check-release --version 0.40.0 --require-changelog --runtime-adapters` 在干净 checkout 中产生不可复现失败。
- 发布后发现 AI-facing 文本收敛移除了必要的治理约束，导致 Agent Team、事实依据、审查或用户交互边界变弱。
- target fixture 与 source workflow 在安装或投影后出现版本漂移。

## 回滚步骤

1. 回滚 0.40.0 发布提交：

```bash
git revert <0.40.0-release-commit>
```

2. 如 tag 已发布且必须撤销：

```bash
git tag -d v0.40.0
git push origin :refs/tags/v0.40.0
```

3. 复跑门禁：

```bash
python skills/software-project-governance/infra/verify_workflow.py verify
python skills/software-project-governance/infra/verify_workflow.py e2e-check
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
```

## 数据边界

`.governance/` 是运行态记录，不随产品发布提交。回滚产品代码后，历史 governance evidence 可保留，用于说明 0.40.0 的发布与回滚事实。
