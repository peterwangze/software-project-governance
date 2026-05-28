# 回滚方案 — 0.38.0

**版本**: 0.38.0
**日期**: 2026-05-28

## 回滚触发条件

- `check-agent-adapters` 对合法 adapter capability contract 产生阻断性误报。
- `check-governance` Check 18b/18c/19/28b/28c 对合法治理闭环产生阻断性误报。
- `check-release` 因 projection sync 或 hot fact source detail 在干净 checkout 中产生不可复现失败。
- execution packet 或 structured evidence 规则导致当前版本产品代码证据无法正常闭环。

## 回滚步骤

1. 回滚 0.38.0 发布提交：

```bash
git revert <0.38.0-release-commit>
```

2. 删除本地和远端 tag：

```bash
git tag -d v0.38.0
git push origin :refs/tags/v0.38.0
```

3. 回滚后复跑：

```bash
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.37.0 --require-changelog --skip-execution-gates
```

## 数据兼容性

0.38.0 引入 `.governance/execution-packets.json` 运行态短包和结构化 evidence JSON 要求。回滚后历史 evidence 可保留；短包文件位于 `.governance/`，不作为产品代码发布资产提交。
