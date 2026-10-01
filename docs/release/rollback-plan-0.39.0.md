# 回滚方案 — 0.39.0

**版本**: 0.39.0
**日期**: 2026-05-30

## 回滚触发条件

- Product Success Contract、Executable Acceptance、Quality Budget、Vertical Slice、Deterministic Scaffold 或 User Interruption Policy 对合法任务产生阻断性误报。
- `check-release --version 0.39.0 --require-changelog --runtime-adapters` 在干净 checkout 中产生不可复现失败。
- release 后发现 0.39.0 允许“无可运行验收、无质量预算、无用户可见切片”的低质半成品闭环。
- 用户打断策略遗漏 release/risk/external dependency/mode change 等关键决策，或对 routine work 产生明显噪音。

## 回滚步骤

1. 回滚 0.39.0 发布提交：

```bash
git revert <0.39.0-release-commit>
```

2. 删除本地和远端 tag：

```bash
git tag -d v0.39.0
git push origin :refs/tags/v0.39.0
```

3. 回滚后复跑：

```bash
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.38.0 --require-changelog --skip-execution-gates
```

## 数据兼容性

0.39.0 扩展 `.governance/execution-packets.json` 的运行态短包字段，用于产品成功、验收、质量预算、垂直切片和用户打断策略。该文件位于 `.governance/`，不是发布资产；回滚产品代码后历史 governance evidence 可保留。
