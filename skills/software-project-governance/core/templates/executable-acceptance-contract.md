# Executable Acceptance Contract 模板

该模板用于 P0/P1 用户可见任务。目标是把“应该算通过”的验收口径转成可运行命令和最近一次运行结果，避免只靠说明、截图或内部状态关闭任务。

## Contract

```yaml
acceptance_contract:
  scenario: "用户可见验收场景"
  command: "可运行 E2E、smoke、unit、demo 或 validation 命令"
  expected_output: "具体通过输出、断言或可观察 demo 结果"
  last_run:
    status: "PASS"
    exit_code: 0
    summary: "最近一次运行结果摘要"
  demo_evidence: "CLI 输出、demo 产物或其他可复查验收证据"
```

## 使用规则

- 自动生成的 `TO_BE_DEFINED` 只是草案；P0/P1 任务必须替换为具体场景、命令、预期输出和运行结果。
- `command` 必须可执行，不能写成“人工看看”“review passed”或只描述流程状态。
- `last_run.status` 必须为 PASS，`last_run.exit_code` 必须为 0。
- `expected_output` 必须能让 Reviewer 判断命令结果是否真的满足用户场景。
- `demo_evidence` 用于保留可复查证据，可以是命令输出摘要、demo 产物路径或测试日志。

## 门禁

运行：

```bash
python skills/software-project-governance/infra/verify_workflow.py check-acceptance-contracts --fail-on-issues
```

`check-governance` 会在 Check 18e 中自动执行同一检查。
