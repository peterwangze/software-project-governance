# AI Execution Packet 模板

运行态文件位置：`.governance/execution-packets.json`

每个活跃 P0/P1 任务必须有一个短执行包。执行包面向 AI 执行者，目标是把长规则压缩成当前任务可直接遵守的事实边界。

## JSON 结构

```json
{
  "version": 1,
  "generated_at": "2026-05-23T00:00:00",
  "packets": {
    "FIX-084": {
      "task_id": "FIX-084",
      "priority": "P0",
      "status": "进行中",
      "goal": "FIX-084 AI execution packet",
      "allowed_change_scope": [
        "Only change files required by this task row.",
        "Keep unrelated refactors and release version bumps out of this task."
      ],
      "required_evidence": [
        "evidence-log entry with 事实依据, 目标对齐, 用户影响, and 结构化事实 JSON",
        "validation commands with exit_code and concise output summary",
        "independent review evidence or explicit degraded review evidence"
      ],
      "next_commands": [
        "python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -v",
        "python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues"
      ],
      "done_definition": [
        "Plan-tracker closure path is satisfied.",
        "Reviewer has APPROVED the product-code change.",
        "Single-task commit and push are completed."
      ],
      "source": "plan-tracker.md##当前活跃事项"
    }
  }
}
```

## 生成命令

```bash
python skills/software-project-governance/infra/verify_workflow.py execution-packet --write
```

## 门禁

`check-governance` 的 Check 18c 会读取该文件。活跃 P0/P1 任务缺少执行包，或执行包缺少目标、允许改动范围、必需证据、下一命令、完成定义时，治理检查失败。
