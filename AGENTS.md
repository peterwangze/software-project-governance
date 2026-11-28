# Codex 项目指引

## Governance Bootstrap（强制 — 每次会话第一动作 · 次要平台入口薄指针）

> @bootstrap-version: 0.102.0

主入口 `CLAUDE.md` 承接完整规则，或加载 `skills/software-project-governance/SKILL.md`。

### 最小存活检查（第一动作）

复用同次启动、同一项目的结果。首次运行时把 `<plugin_home>` 换成本次宿主技能清单中主技能 `software-project-governance` 的 `SKILL.md` 所在绝对目录；仅给插件包根时取其 `skills/software-project-governance` 子目录。确认技能名和脚本存在，从用户项目根运行 `python "<plugin_home>/infra/verify_workflow.py" governance-bootstrap --format json`。须成功退出、JSON 有效且 `resolve.resolved_root_ok == true`，否则 MUST STOP 并显示诊断。 仅当旧 CLI 明报未知子命令才用 `resolve_entry.py --json` 定位安装根。根或运行记录无效时停止并显示诊断。 从 `loops` 找到本次目标、单元及父单元、层级、轮次、最新裁决和证据。无单元时从用户的第一项交付登记工作；数据损坏或目标有歧义时保留原件并报告。

### SELF-CHECK

核对本轮对象、证据和可执行动作。待用户的关键决策使用 AskUserQuestion。`GOVERNANCE_LEGACY_BEHAVIOR=1` 仅调整性能。always-on 显示本次目标、工作单元、循环层、轮次及尚需的验收或裁决；on-demand 按用户请求展开；silent-track 仅在阻塞、权限边界或风险到期时打断。

### 治理状态快速入口

`.governance/plan-tracker.md` 记录任务来源，`.governance/evidence-log.md` 及归档记录提供回执，当前单元用 `loop status --json` 复读。PowerShell 使用 `Get-Content -Encoding UTF8`。

## 项目质量原则（P-v1 — DEC-150）

> 全文与执行锚点映射：`.governance/project-principles.md`（P-vN 版本化，只升不降；演进经 decision-log 入账）。本段为会话投影——每次会话注入，作为所有实现/设计/审查活动的质量基线。

**原则（P1-P7）**：
1. 分析和推演基于事实，不允许假设和编造
2. 实现进行全面的分析，避免修改遗漏
3. 实现考虑对原有功能的影响，避免引入新问题
4. 实现进行测试看护，构建防护网，避免后续问题反复
5. 实现考虑泛化性，严禁单点修改
6. 以高质量交付为准则，严禁为了完成任务而忽略质量
7. 修复保证安全性，避免引入导致损坏用户数据的情况

**编程要求（D1-D4）**：
1. 设计考虑可扩展性和可维护性，基于未来进行设计
2. 实现避免架构腐化，避免引入架构问题和可维护性问题
3. 实现保证模块/类/接口职责单一，避免上帝类/上帝模块和多功能接口
4. 实现不做冗余修改，保持修改纯粹性，一个 commit 承载一个问题修改/功能实现

## 本仓库的分支协作与发布交接

独立改动从自己的任务分支向 `origin/master` 提交 PR。当前工作树由其他任务使用时，另建工作树。PR 合入后，获取 `origin` 的最新状态并快进本地 `master`。需要同步的开发分支再将自己的提交 rebase 到 `origin/master`。保留工作区内的改动，改写已发布分支前与分支负责人确认，并使用带预期远端提交号的 `--force-with-lease` 推送。

发布交接时，比较 `git rev-parse --verify refs/heads/master` 与 `git ls-remote --exit-code origin refs/heads/master` 返回的完整提交号。确认两端一致后，将提交号记入发布回执，供后续会话核对。
