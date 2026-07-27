# <项目名称>

本项目使用 `software-project-governance` workflow 管理项目治理。

## 项目配置

- **Profile**: `<lightweight / standard / strict>` — 选择依据见下方说明
- **触发模式**: `<always-on / on-demand / silent-track>`
- **操作权限模式**: `<maximum-autonomy / default-confirm>`
- **工作流版本**: `<active_version from resolve_entry.py>`
- **当前阶段**: `<对照 lifecycle.md 声明当前阶段>`
- **接入方式**: `<从立项开始 / 中途接入>`

> **Profile 选择参考**：
> - lightweight：个人项目、探索性项目、MVP → 5 个核心阶段，合并 Gate，最少记录
> - standard：团队项目、正式产品 → 全部 11 阶段，完整 Gate
> - strict：大型项目、合规项目 → 全部阶段，增强 Gate，不允许跳步

## Onboarding 声明（中途接入时填写）

> 如果项目从立项开始就使用本工作流，可删除本段。

- **前置阶段 Gate**: 全部标记为 `passed-on-entry`
- **当前阶段 Gate**: `<pending>`
- **已补齐的前置阶段关键决策**: `<列出或注明"无">`

## Gate 状态跟踪

| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |
| --- | --- | --- | --- | --- |
| G1 | → 调研 | `<passed-on-entry / pending / passed>` | `<YYYY-MM-DD>` | `<证据描述>` |
| G2 | → 技术选型 | `<status>` | | |
| G3 | → 环境搭建 | `<status>` | | |
| G4 | → 架构设计 | `<status>` | | |
| G5 | → 开发实现 | `<status>` | | |
| G6 | → 测试 | `<status>` | | |
| G7 | → 防护网与CI/CD | `<status>` | | |
| G8 | → 版本发布 | `<status>` | | |
| G9 | → 运营 | `<status>` | | |
| G10 | → 维护 | `<status>` | | |
| G11 | → 下一轮 | `<status>` | | |

## 项目总览

| 项目 | 当前阶段 | 总任务数 | 已完成 | 阻塞中 | 关键风险数 | 最近 Gate 结论 | 最近复盘日期 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `<项目名称>` | `<阶段>` | `<数量>` | `<数量>` | `<数量>` | `<数量>` | `<Gx / 通过或未通过>` | `<YYYY-MM-DD>` |

## 样例跟踪表

| 优先级 | ID | 任务项 | 依赖 | 目标版本 | 状态 |
| --- | --- | --- | --- | --- | --- |
| P0 | INIT-001 | `<填写任务>` | — | `<版本>` | 未开始 |

> **依赖列格式（FIX-225）**：逗号分隔的 task ID（如 `FIX-162,DEC-090`）。`—` 表示无依赖。task-family 前缀（FIX/REL/AUDIT/REQ/SYSGAP/FEAT/VAL 等）是可解析的依赖 ID；cross-entity 引用（RISK/DEC/EVD 等）是描述性上下文，不阻塞执行。`task-priority-analysis` 工具（FIX-226）用此列计算 blocked/unblocked 状态。

## 使用规则

- 所有 agent 必须复用同一份主计划。
- 已完成任务必须补齐证据。
- 发生偏差时必须更新风险或决策记录。
- 阶段切换前必须先检查 Gate。
