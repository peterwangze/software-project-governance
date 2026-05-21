# E2E 命令验证清单 — FIX-060

## 测试环境

- **项目**: `project/e2e-test-project/`
- **方式**: `python skills/software-project-governance/infra/verify_workflow.py e2e-check`
- **口径**: `source CLI proxy + external target cwd execution + target fixture checks`。source root 继续执行命令代理；`project/e2e-test-project/` 还会作为外部 target cwd 运行目标项目自己的治理命令，并校验四平台 native entry fixture。

## Source CLI Proxy 命令矩阵

| 用户命令 | 代理命令 | 断言 | 结果口径 |
|---|---|---|---|
| `/governance-status` | `python verify_workflow.py status` | exit code 0；输出含 `Project Overview` / `Tasks` / `Gate` / `maximum-autonomy` | source_cli_proxy |
| `/governance-gate G1` | `python verify_workflow.py gate G1` | exit code 0；输出含 `G1` 和 `Check items` | source_cli_proxy |
| `/governance-gate G99` | `python verify_workflow.py gate G99` | 非 0；输出含 `Gate G99 not found` 或 `GATE-ERR` 语义 | source_cli_proxy |
| `/governance-cleanup` | `python cleanup.py --dry-run --json` | JSON 可解析；接受 `status=clean` 或明确 redundancy report | source_cli_proxy |
| `/governance-verify` | `python verify_workflow.py verify` | 真实执行；仅当前 4 个精确签名可报告为 `EXPECTED_KNOWN_FAILURE` | expected known failure |
| `/governance` | `python verify_workflow.py status` + source `commands/governance.md` 合同 | Scenario F 代理真实执行 status；路由合同存在 | source_cli_proxy + contract |

## Target Fixture Checks

| 目标 | 验证内容 | 结果口径 |
|---|---|---|
| `project/e2e-test-project/CLAUDE.md` | `Governance Bootstrap` / `SELF-CHECK` / `AskUserQuestion` | target_fixture |
| `project/e2e-test-project/AGENTS.md` | Codex/opencode native entry thin projection，指向 `skills/software-project-governance/SKILL.md` | target_fixture |
| `project/e2e-test-project/GEMINI.md` | Gemini native entry thin projection，指向 `skills/software-project-governance/SKILL.md` | target_fixture |
| `project/e2e-test-project/.governance/` | plan/evidence/decision/risk/session 五个 tracked fixture 文件存在 | target_fixture |
| `project/e2e-test-project/.governance/plan-tracker.md` | `工作流版本` / `0.36.0` / `操作权限模式` / `default-confirm` | target_fixture |
| `project/e2e-test-project/skills/software-project-governance/SKILL.md` | `version: 0.36.0` / `Coordinator` / `Agent Team` | target_fixture |
| `project/e2e-test-project/commands/governance.md` | `Scenario F` / `AskUserQuestion` / `Coordinator` | target_fixture |

## 平台运行时 / 合同检查

| 路径 | 标记 | 原因 |
|---|---|---|
| `/governance-review code` → Code Reviewer spawn | `AGENT_RUNTIME_REQUIRED` | Agent spawn 由宿主平台提供，Python CLI 不能伪造 PASS |
| AskUserQuestion 交互边界 | `AGENT_RUNTIME_REQUIRED` | 用户选择工具是平台运行时能力，Python CLI 仅能检查合同文本 |
| `/governance` Scenario F 路由说明 | `CONTRACT_CHECK` | 静态合同只证明路由定义存在；可执行覆盖来自 status 代理 |

## 当前验收标准

- `e2e-check` 不再输出静态 `19/19` 或 “静态验证 6/6”。
- 总结果由 `source_cli_proxy`、`target_cwd_command` 与 `target_fixture` 的 `FAIL` 决定是否退出 1。
- `EXPECTED_KNOWN_FAILURE` 必须报告但不导致 `e2e-check` 失败。
- `AGENT_RUNTIME_REQUIRED` / `CONTRACT_CHECK` 与 source CLI proxy 计数分开展示。
- 真实 agent runtime 命令矩阵由 FIX-076 继续补齐；本清单已经要求 fixture 含 Claude/Codex/Gemini/opencode 原生入口投影。
