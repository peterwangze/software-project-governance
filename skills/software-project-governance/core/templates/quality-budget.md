# Quality Budget 模板

该模板用于 P0/P1 用户可见任务。目标是把性能、可靠性、安全、可访问性、UX 和可维护性从主观判断转成阈值、验证信号、最近结果或显式例外。

## Contract

```yaml
quality_budget:
  dimensions:
    performance:
      threshold: "最低可接受性能阈值"
      validation: "验证命令、指标来源或复查材料"
      status: "PASS"
      evidence: "最近一次结果摘要或证据位置"
      exception: ""
    reliability:
      threshold: "最低可接受可靠性阈值"
      validation: "验证命令、指标来源或复查材料"
      status: "PASS"
      evidence: "最近一次结果摘要或证据位置"
      exception: ""
    security:
      threshold: "最低可接受安全阈值"
      validation: "验证命令、指标来源或复查材料"
      status: "PASS"
      evidence: "最近一次结果摘要或证据位置"
      exception: ""
    accessibility:
      threshold: "最低可接受可访问性阈值"
      validation: "验证命令、指标来源或复查材料"
      status: "PASS"
      evidence: "最近一次结果摘要或证据位置"
      exception: ""
    ux:
      threshold: "最低可接受用户体验阈值"
      validation: "验证命令、指标来源或复查材料"
      status: "PASS"
      evidence: "最近一次结果摘要或证据位置"
      exception: ""
    maintainability:
      threshold: "最低可接受可维护性阈值"
      validation: "验证命令、指标来源或复查材料"
      status: "PASS"
      evidence: "最近一次结果摘要或证据位置"
      exception: ""
```

## 使用规则

- 自动生成的 `TO_BE_DEFINED` 只是草案；P0/P1 任务必须替换为具体阈值、验证信号、状态和证据。
- 六个维度必须齐全：performance、reliability、security、accessibility、ux、maintainability。
- 已关闭或进行中的任务必须使用 `PASS`，或用 `EXEMPT`/`not_applicable` 并写清 `exception`。
- 待实施任务可以暂用 `NOT_RUN_YET`，但仍必须提前写清阈值、验证方式和证据计划。
- 不允许只写治理流程通过、证据已归档或审查完成来替代质量结果。

## 门禁

运行：

```bash
python skills/software-project-governance/infra/verify_workflow.py check-quality-budget --fail-on-issues
```

`check-governance` 会在 Check 18f 中自动执行同一检查。
