# 质量预算

用户、宿主契约或风险决策给出了实际阈值时，在需要交接的执行包中记录适用维度。下例为明确约定命令耗时的情形，发布前须用该候选的实测值填写 evidence。

```yaml
quality_budget:
  dimensions:
    performance:
      threshold: "生成 200 条交易报表的 p95 低于 300 ms"
      validation: "python tests/bench_report.py --rows 200 --samples 100"
      status: "NOT_RUN_YET"
      evidence: "待在候选构建上保存实际采样输出到 artifacts/report-benchmark.json"
```

可选维度为 performance、reliability、security、accessibility、ux、maintainability。声称 PASS 要有实际验证证据，豁免须说明适用理由；待运行只能用于待实施的工作。用户批准的硬阈值在目标的冻结验收中保留。运行 `check-quality-budget --fail-on-issues` 可核对已声明的预算。
