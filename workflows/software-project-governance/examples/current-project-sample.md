# 当前项目样例

本文件使用当前项目作为 `software-project-governance` workflow 的样例项目。

## 项目总览

| 项目 | 当前阶段 | 总任务数 | 已完成 | 阻塞中 | 关键风险数 | 最近 Gate 结论 | 最近复盘日期 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 项目管理工作流插件 | CI | 3 | 3 | 0 | 1 | G3 通过 | 2026-04-17 |

## 样例跟踪表

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner | 协同角色 | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| INIT-001 | 立项 | 明确插件仓库目标 | 将 workflow 定位为 agent plugin/skill 仓库 | 用户澄清事实 | `README.md` | 项目负责人 | Claude | 已完成 | P0 | 2026-04-17 | 2026-04-17 | 2026-04-17 | G1 | 插件目标明确 | `workflows/software-project-governance/manifest.md` | 无 | 无 | 项目定位已收敛 |
| PLAN-001 | 规划 | 定义协议层与分层结构 | 建立 protocol / workflows / adapters 分层 | 项目定位与调研结果 | `protocol/*.md`, `workflows/`, `adapters/` | Claude | 项目负责人 | 已完成 | P0 | 2026-04-17 | 2026-04-17 | 2026-04-17 | G2 | 目录结构与协议层建立 | `protocol/workflow-schema.md` | 无 | 无 | 已完成首版骨架 |
| DESIGN-001 | 设计 | 建立 Claude/Codex 适配入口 | 支撑多 agent 消费同一套流程资产 | 协议层、规则层 | `adapters/claude/README.md`, `adapters/codex/README.md` | Claude | 项目负责人 | 进行中 | P0 | 2026-04-17 | 2026-04-18 | | G3 | 适配入口完整可读 | `adapters/claude/README.md` | Gemini 与国内 agent 仍为预留层 | 后续继续补兼容细节 | 当前处于结构升级期 |
