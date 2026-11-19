# Codex 项目指引

## Governance Bootstrap（强制 — 每次会话第一动作 · 次要平台入口薄指针）

> @bootstrap-version: 0.99.0（薄指针版——FEAT-037 双入口去重；完整 bootstrap 见 CLAUDE.md（主入口），行为约束以主入口为准）

本文件是次要平台入口薄指针，完整 Step 0~4、Agent Team、升级与交叉验证见主入口 `CLAUDE.md`。

### 最小存活检查（第一动作）

1. 复用同次启动、同一项目的结果，否则运行 `python "<plugin_home>/infra/verify_workflow.py" governance-bootstrap --format json`。除下述旧版情形，须成功退出、JSON 有效且 `resolve.resolved_root_ok == true`，否则 MUST STOP 并显示诊断。
2. 未初始化则提示初始化。仅旧 CLI 明报未知子命令时运行 `python <plugin_home>/infra/resolve_entry.py --json`；成功退出且 `resolved_root_ok == true` 后可六段读取 `.governance/plan-tracker.md`。
3. **行为灰度开关**：`GOVERNANCE_LEGACY_BEHAVIOR=1` 或 `behavior_profile: legacy` 按本次 `behavior` 回退性能行为；**安全语义不回退**。
4. 完整规则：加载 `skills/software-project-governance/SKILL.md`（或读主入口 `CLAUDE.md`）。

### SELF-CHECK（在任何输出之前）

1. 阶段/Gate/模式（含 carry-over）未知 → 按主入口展开；拟写入内容无事实依据 → 标 `BLOCKED`。
2. 即将输出问句？→ 改用 AskUserQuestion；到达交互边界？→ MUST AskUserQuestion（完整 SELF-CHECK：SKILL.md「Bootstrap 规程明细」§B0）。

### 模式确认（每次会话一句，模式自适应）

- **always-on** → `Governance: {trigger_mode} x {permission_mode} | stage: {stage}, Gate {gate}: {status}, {risk_count} risk(s)`
- **on-demand** → `Governance: on-demand x {permission_mode}`（仅用户显式调用时展开完整状态）；**silent-track** → 不输出治理面板/风险统计/任务进度表

### 治理状态快速入口

- 计划跟踪 `.governance/plan-tracker.md` · 证据 `.governance/evidence-log.md` · 决策 `.governance/decision-log.md` · 风险 `.governance/risk-log.md`；验证命令：`python <plugin_home>/infra/verify_workflow.py`（`<plugin_home>` 取本次定位结果）
- 完整治理交互：`/governance`；完整 bootstrap（SELF-CHECK 全文/干活前/提问规则/收工检查）：`CLAUDE.md`（主入口）；pwsh 读 `.governance` 文件 MUST 显式 UTF-8：`Get-Content -Encoding UTF8`（裸 `Get-Content` 在 Windows 默认 GBK 解码产生 mojibake——FIX-278）
- 推荐必标需求源/发现即闭环——见 SKILL 关键行为契约

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
