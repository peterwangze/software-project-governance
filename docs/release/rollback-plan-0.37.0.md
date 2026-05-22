# 回滚方案 — 0.37.0

**版本**: 0.37.0
**日期**: 2026-05-22

## 回滚触发条件

- `commit-msg` 事实依据门禁在合法产品代码提交中产生阻断性误报。
- `pre-commit` Step 6 对合法 `CLAUDE.md` bootstrap self-upgrade 仍产生阻断性误报。
- `check-governance` Fact Grounding 检查导致当前版本证据无法正常闭环。

## 回滚步骤

1. 回滚 0.37.0 发布提交：

```bash
git revert <0.37.0-release-commit>
```

2. 删除本地和远端 tag：

```bash
git tag -d v0.37.0
git push origin :refs/tags/v0.37.0
```

3. 回滚后复跑：

```bash
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
```

## 数据兼容性

0.37.0 不引入治理数据格式破坏性变更。新增 `事实依据:` 字段属于产品代码证据质量要求；回滚后历史 evidence 仍可保留。

