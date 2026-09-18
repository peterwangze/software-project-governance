---
name: governance
description: 统一治理入口——一条命令覆盖全部场景：自动检测项目状态并路由到初始化/接入/升级/恢复/状态场景
---

# governance（DSH 投影）

本 skill 是 `commands/governance.md` 在 DeepSeek Harness 上的薄投影（thin pointer），自身不含 workflow 规则，不重复、不覆盖源文件。

加载后执行：

1. 用 `read` 工具读取治理插件仓库的 `commands/governance.md`（`<plugin_root>` 见本会话 persona 或项目 `AGENTS.md` 的 Governance Bootstrap 段；software-project-governance skill 的 resourceBase 亦指向该仓库内 skill 目录）。
2. 完全遵循该文件内容执行。

**分层加载（FEAT-038）**：`commands/governance.md` 是**路由层**（Coordinator 身份 + 检测逻辑 + 决策树 + 六 Scenario 摘要与路由）。命中场景后该文件要求 MUST 再 `read` 对应执行规程——`scenario_hint == X` → `commands/governance/scenario-x.md`；入口解析/错误码 → `commands/governance/bootstrap.md`；快照字段契约 → `commands/governance/snapshot-schema.md`；三方分工/Web console/分级声明 → `commands/governance/overview.md`。路由层的摘要是索引，不是执行依据，**不得跳过**。

若源文件缺失或仓库路径不可得：MUST STOP，向用户报告"治理命令投影无法解析插件仓库根目录"，并给出安装提示（`python <plugin_root>/adapters/dsh/launch.py --install`），不得凭空执行命令内容。
