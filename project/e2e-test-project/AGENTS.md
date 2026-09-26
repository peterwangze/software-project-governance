# Codex / opencode Project Guidance

## Governance Bootstrap（强制 — 每次会话第一动作 · 次要平台入口薄指针）

> @bootstrap-version: 0.89.0（薄指针版——FEAT-037 双入口去重；完整 bootstrap 见 CLAUDE.md（主入口），行为约束以主入口为准）

本工作区存在两个平台原生入口文件。本文件是次要平台入口（Codex/opencode 等）的薄指针投影，不复制完整模板；主入口 `CLAUDE.md` 携带完整 bootstrap（Step 0~4、交叉验证、阶段跳跃防护、Agent Team、Bootstrap 变更纪律）。

### 最小存活检查（第一动作）

1. 运行 `python <plugin_home>/skills/software-project-governance/infra/resolve_entry.py --json`；`resolved_root_ok == false` → MUST STOP，不呈现治理状态（fail-closed）。
2. 读 `.governance/plan-tracker.md`；阶段/Gate/模式未知 → 读 `## 项目配置` 节；`.governance/` 不存在 → 提醒先初始化。
3. **快路径与行为灰度开关（FEAT-034/040）**：热数据优先 `governance-bootstrap --format json`（不可用回退六段读取）；`GOVERNANCE_LEGACY_BEHAVIOR=1` 或 `behavior_profile: legacy` → 只回退性能行为，**安全语义不回退**；见其 `behavior` 面。
4. 完整规则：加载 `skills/software-project-governance/SKILL.md`（或读主入口 `CLAUDE.md`）。

### SELF-CHECK（在任何输出之前）

1. 读了 `.governance/plan-tracker.md`？知道阶段/Gate/模式（含 carry-over，session-snapshot）？任一未知 → 立即停止，先读。
2. 即将输出问句？→ 改用 AskUserQuestion。到达交互边界？→ MUST 使用 AskUserQuestion（完整 SELF-CHECK：SKILL.md「Bootstrap 规程明细」§B0）。
3. 即将写入的修改/证据是否有事实依据？无支撑 → 标 `BLOCKED`，禁止编造。

### 模式确认（每次会话一句，模式自适应）

- **always-on** → `Governance: {trigger_mode} x {permission_mode} | stage: {stage}, Gate {gate}: {status}, {risk_count} risk(s)`
- **on-demand** → `Governance: on-demand x {permission_mode}`（仅用户显式调用时展开完整状态）
- **silent-track** → 不输出治理面板/风险统计/任务进度表

### 治理状态快速入口

- 计划跟踪 `.governance/plan-tracker.md` · 证据 `.governance/evidence-log.md` · 决策 `.governance/decision-log.md` · 风险 `.governance/risk-log.md`
- 验证命令：`python <plugin_home>/skills/software-project-governance/infra/verify_workflow.py`（`<plugin_home>` 来自 resolve_entry.py）
- 治理文件读取编码（FIX-278）：pwsh 读 `.governance` 文件 MUST 显式 UTF-8——`Get-Content -Encoding UTF8`；裸 `Get-Content` 在 Windows 默认 GBK 解码产生 mojibake。
- 完整治理交互：`/governance`；完整 bootstrap（SELF-CHECK 全文/干活前/提问规则/收工检查）：`CLAUDE.md`（主入口）
