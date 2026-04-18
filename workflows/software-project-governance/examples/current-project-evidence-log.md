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
| EVD-009 | ACCEPT-001 | 验收 | 文档 | Claude 仓库级入口 `CLAUDE.md` 已建立，并指向原生 skill | `CLAUDE.md` | Claude | 2026-04-18 | G6 | 支撑 Claude 原生入口可发现 |
| EVD-010 | ACCEPT-001 | 验收 | 文档 | Claude 原生 project skill 已落地并声明读取顺序、输出规则与验证命令 | `.claude/skills/software-project-governance/SKILL.md` | Claude | 2026-04-18 | G6 | 支撑 Claude skill 可直接消费 workflow |
| EVD-011 | ACCEPT-001 | 验收 | 命令输出 | 升级后的 Claude launcher 与验证脚本已覆盖原生 skill 入口并验证通过 | `adapters/claude/launch.py` | Claude | 2026-04-18 | G6 | 支撑原生入口与 adapter 闭环 |
| EVD-012 | RESEARCH-001 | 规划 | 外部调研 | 已补充 Claude Skills / Slash Commands / MCP 与 Codex、Gemini CLI 集成方式调研结论 | `README.md` | Claude | 2026-04-18 | G2 | 支撑重新定义主流集成方式 |
| EVD-013 | PLAN-004 | 规划 | 文档 | 当前项目样例、决策和风险记录已写入旧路线终止说明与新主线切换信息 | `workflows/software-project-governance/examples/current-project-sample.md` | Claude | 2026-04-18 | G2 | 支撑主线正式切换 |
| EVD-014 | DESIGN-005 | 设计 | 文档 | `plugin-contract` 已从目录布局优先调整为集成模式优先 | `protocol/plugin-contract.md` | Claude | 2026-04-18 | G3 | 支撑低侵入集成方向重构 |
| EVD-015 | DOC-001 | 文档 | 文档 | README 已明确 repo-local 入口仅为探索性样例，不再作为默认推荐接入方式 | `README.md` | Claude | 2026-04-18 | G2 | 支撑对外叙事纠偏 |
| EVD-016 | PLAN-004 | 规划 | 命令输出 | 重规划后的 README、协议与样例治理记录已通过统一校验脚本验证 | `scripts/verify_workflow.py` | Claude | 2026-04-18 | G2 | 支撑新主线闭环 |
