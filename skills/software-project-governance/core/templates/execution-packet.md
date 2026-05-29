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
      "acceptance_contract": {
        "scenario": "TO_BE_DEFINED: user-visible acceptance scenario for FIX-084",
        "command": "TO_BE_DEFINED: runnable E2E, smoke, unit, or validation command",
        "expected_output": "TO_BE_DEFINED: concrete pass output, assertion, or observable demo result",
        "last_run": {
          "status": "TO_BE_DEFINED",
          "exit_code": null,
          "summary": "TO_BE_DEFINED: last run output summary with evidence location"
        },
        "demo_evidence": "TO_BE_DEFINED: demo, CLI output, or artifact proving the scenario"
      },
      "quality_budget": {
        "dimensions": {
          "performance": {
            "threshold": "TO_BE_DEFINED: minimum acceptable performance threshold",
            "validation": "TO_BE_DEFINED: command, metric source, or evidence path",
            "status": "TO_BE_DEFINED",
            "evidence": "TO_BE_DEFINED: latest performance result",
            "exception": ""
          },
          "reliability": {
            "threshold": "TO_BE_DEFINED: minimum acceptable reliability threshold",
            "validation": "TO_BE_DEFINED: command, metric source, or evidence path",
            "status": "TO_BE_DEFINED",
            "evidence": "TO_BE_DEFINED: latest reliability result",
            "exception": ""
          },
          "security": {
            "threshold": "TO_BE_DEFINED: minimum acceptable security threshold",
            "validation": "TO_BE_DEFINED: command, metric source, or evidence path",
            "status": "TO_BE_DEFINED",
            "evidence": "TO_BE_DEFINED: latest security result",
            "exception": ""
          },
          "accessibility": {
            "threshold": "TO_BE_DEFINED: minimum acceptable accessibility threshold",
            "validation": "TO_BE_DEFINED: command, metric source, or evidence path",
            "status": "TO_BE_DEFINED",
            "evidence": "TO_BE_DEFINED: latest accessibility result",
            "exception": ""
          },
          "ux": {
            "threshold": "TO_BE_DEFINED: minimum acceptable UX threshold",
            "validation": "TO_BE_DEFINED: command, metric source, or evidence path",
            "status": "TO_BE_DEFINED",
            "evidence": "TO_BE_DEFINED: latest UX result",
            "exception": ""
          },
          "maintainability": {
            "threshold": "TO_BE_DEFINED: minimum acceptable maintainability threshold",
            "validation": "TO_BE_DEFINED: command, metric source, or evidence path",
            "status": "TO_BE_DEFINED",
            "evidence": "TO_BE_DEFINED: latest maintainability result",
            "exception": ""
          }
        }
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

`check-governance` 的 Check 18e 会检查 `acceptance_contract`。活跃 P0/P1 任务必须把 `scenario`、`command`、`expected_output`、`last_run` 和 `demo_evidence` 替换为具体内容；`command` 必须是可运行验收/E2E/smoke/test/check 命令，`last_run.status` 必须为 PASS 且 `exit_code` 必须为 0。

`check-governance` 的 Check 18f 会检查 `quality_budget`。活跃 P0/P1 任务必须覆盖 performance、reliability、security、accessibility、ux、maintainability 六个维度；每个维度必须有具体阈值、验证信号、状态和证据。已关闭或进行中任务必须为 PASS，或用 EXEMPT/not_applicable 并写清例外理由；待实施任务可以暂用 NOT_RUN_YET，但仍必须写清阈值、验证方式和证据计划。
