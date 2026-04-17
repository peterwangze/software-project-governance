# 当前项目证据记录

本文件记录插件化重构阶段的关键证据。

| 编号 | 对应任务 ID | 阶段 | 证据类型 | 证据说明 | 证据位置 | 提交人 | 提交日期 | 关联 Gate | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| EVD-001 | INIT-001 | 立项 | 文档 | workflow 已重新定义为 agent plugin/skill 仓库 | `workflows/software-project-governance/manifest.md` | Claude | 2026-04-17 | G1 | 支撑立项完成 |
| EVD-002 | PLAN-001 | 规划 | 文档 | 协议层与插件约定已建立 | `protocol/workflow-schema.md` | Claude | 2026-04-17 | G2 | 支撑规划完成 |
| EVD-003 | PLAN-002 | 规划 | 文档 | 当前项目样例已扩展为可执行 backlog，并区分优先级与状态 | `workflows/software-project-governance/examples/current-project-sample.md` | Claude | 2026-04-17 | G2 | 支撑演进 backlog 建立 |
| EVD-004 | DESIGN-001 | 设计 | 文档 | Claude 与 Codex 适配入口说明已建立 | `adapters/claude/README.md` | Claude | 2026-04-17 | G3 | 支撑首版适配设计完成 |
| EVD-005 | DESIGN-002 | 设计 | 命令输出 | Claude 半可执行入口已可运行并输出读取顺序与校验命令 | `adapters/claude/launch.py` | Claude | 2026-04-17 | G3 | 支撑 Claude launcher 落地 |
| EVD-006 | DESIGN-003 | 设计 | 命令输出 | Codex 半可执行入口已可运行并输出读取顺序与校验命令 | `adapters/codex/launch.py` | Claude | 2026-04-17 | G3 | 支撑 Codex launcher 落地 |
| EVD-007 | CI-001 | CI | 命令输出 | 升级后的校验脚本已覆盖 adapter manifest 与 launcher，并验证通过 | `scripts/verify_workflow.py` | Claude | 2026-04-17 | G5 | 支撑 CI 闭环完成 |
| EVD-008 | MAINT-001 | 维护 | 文档 | 当前项目样例已从展示态升级为持续跟踪态 | `workflows/software-project-governance/examples/current-project-sample.md` | Claude | 2026-04-17 | G8 | 支撑跟踪治理动作 |
