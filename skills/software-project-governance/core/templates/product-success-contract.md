# Product Success Contract 模板

该模板用于 P0/P1 用户可见任务。目标是把“产品是否真的成功”从 LLM 的隐含判断转成可审查、可验证、可追溯的契约。

## Contract

```yaml
product_success_contract:
  user: "谁会直接使用或受影响"
  job_to_be_done: "用户要完成的真实工作，而不是内部实现动作"
  non_goals:
    - "本任务明确不解决的范围"
  success_metrics:
    - "可观察、可验证的成功信号；优先使用命令、E2E、demo、性能或质量指标"
  competitive_baseline: "成熟产品或团队实践下的最低可接受标准"
  done_definition:
    - "产品层完成条件"
    - "验收、质量、审查和证据层完成条件"
```

## 使用规则

- 产品成功契约先于实现产生，并进入 `.governance/execution-packets.json`。
- 自动生成的 `TO_BE_DEFINED` 只是草案；P0/P1 任务必须替换为具体用户、场景、非目标、指标和完成定义。
- P0/P1 任务不得使用 `TBD`、`TODO`、`TO_BE_DEFINED`、`待补`、`unknown`、`无` 等占位内容关闭。
- 成功指标必须同时覆盖用户可感知结果和可运行验证，不得只写“governance/check/review/evidence 已完成”。
- 非目标用于保护范围，防止弱 LLM 把任务扩展成不可验证的大包。
- 竞争基线用于提示 AI：最低标准不是“代码存在”，而是达到成熟团队会接受的产品完成度。

## 门禁

运行：

```bash
python skills/software-project-governance/infra/verify_workflow.py check-product-success-contracts --fail-on-issues
```

`check-governance` 会在 Check 18d 中自动执行同一检查。
