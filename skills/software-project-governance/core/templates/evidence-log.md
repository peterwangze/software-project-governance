# 证据记录模板

用于记录 workflow 执行过程中的关键证据，支撑任务完成与 Gate 通过。

| 编号 | 对应任务 ID | 阶段 | 证据类型 | 证据说明 | 证据位置 | 提交人 | 提交日期 | 关联 Gate | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EVD-001 | `<任务ID>` | `<阶段>` | 文档 / 代码 / 截图 / CI 记录 / 会议纪要 | `<说明>` | `<文件路径或链接>` | `<姓名>` | `<YYYY-MM-DD>` | `<Gx>` | `<备注>` |

## 使用规则

- 已完成事项必须至少有一条证据。
- Gate 结论必须可追溯到证据。
- 产品代码交付证据必须包含 `事实依据:`、`目标对齐:`、`用户影响:`。
- 0.38.0+ 当前版本产品代码交付证据还必须包含 `结构化事实:` JSON，最小字段如下：

```json
{
  "commands": [
    {
      "cmd": "python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues",
      "exit_code": 0,
      "summary": "Governance health passed with zero issues.",
      "log_path": "terminal output"
    }
  ],
  "files_changed": ["skills/software-project-governance/infra/verify_workflow.py"],
  "diff_summary": "Short summary of the relevant diff.",
  "review": {"conclusion": "APPROVED", "reviewer": "Code Reviewer"}
}
```

- `结构化事实:` 不得包含 API key、token、password、secret 等明文敏感值；只记录脱敏摘要或日志路径。
