# Codex / opencode Project Guidance

## Governance Bootstrap（强制 — 每次会话第一动作 · 次要平台入口薄指针）

> @bootstrap-version: 0.100.0

主入口 `CLAUDE.md` 承接完整规则，或加载 `skills/software-project-governance/SKILL.md`。

### 最小存活检查（第一动作）

复用同次启动、同一项目的结果，否则运行 `python "<plugin_home>/infra/verify_workflow.py" governance-bootstrap --format json`。须成功退出、JSON 有效且 `resolve.resolved_root_ok == true`，否则 MUST STOP 并显示诊断。 仅当旧 CLI 明报未知子命令才用 `resolve_entry.py --json` 定位安装根。根或运行记录无效时停止并显示诊断。 从 `loops` 找到本次目标、单元及父单元、层级、轮次、最新裁决和证据。无单元时从用户的第一项交付登记工作；数据损坏或目标有歧义时保留原件并报告。

### SELF-CHECK

核对本轮对象、证据和可执行动作。待用户的关键决策使用 AskUserQuestion。`GOVERNANCE_LEGACY_BEHAVIOR=1` 仅调整性能。always-on 显示本次目标、工作单元、循环层、轮次及尚需的验收或裁决；on-demand 按用户请求展开；silent-track 仅在阻塞、权限边界或风险到期时打断。

### 治理状态快速入口

`.governance/plan-tracker.md` 记录任务来源，`.governance/evidence-log.md` 及归档记录提供回执，当前单元用 `loop status --json` 复读。PowerShell 使用 `Get-Content -Encoding UTF8`。
