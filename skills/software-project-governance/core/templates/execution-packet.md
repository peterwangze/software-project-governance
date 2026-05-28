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
      "product_success_contract": {
        "user": "TO_BE_DEFINED: impacted persona for FIX-084",
        "job_to_be_done": "TO_BE_DEFINED: user job and desired outcome for FIX-084",
        "non_goals": [
          "TO_BE_DEFINED: explicit non-goal that protects scope.",
          "TO_BE_DEFINED: explicit non-goal that prevents process evidence from replacing product value."
        ],
        "success_metrics": [
          "TO_BE_DEFINED: user-visible outcome or acceptance scenario.",
          "TO_BE_DEFINED: runnable E2E, test, or command that proves the outcome."
        ],
        "competitive_baseline": "TO_BE_DEFINED: mature-team or competing-product baseline this task must match.",
        "done_definition": [
          "TO_BE_DEFINED: product success evidence is recorded with concrete facts.",
          "TO_BE_DEFINED: independent review confirms the user outcome is not replaced by process completion."
        ]
      },
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

`check-governance` 的 Check 18d 会检查 `product_success_contract`。活跃 P0/P1 任务必须把上述 `TO_BE_DEFINED` 草案替换为具体内容，声明用户、JTBD、非目标、成功指标、竞争基线和完成定义。成功指标必须至少包含一个用户可见结果和一个可运行验证信号，且不得只写 governance/check/review/evidence 等流程完成项。
