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
| EVD-017 | RESEARCH-001 | 规划 | 文档 | 已形成 Claude、Codex、Gemini 与 MCP 等集成方式的正式调研结论文档 | `workflows/software-project-governance/research/agent-integration-models.md` | Claude | 2026-04-18 | G2 | 支撑后续默认产品形态设计 |
| EVD-018 | PLAN-003 | 规划 | 文档 | 已形成默认产品形态方案，明确 workflow 本体层、agent 入口投影层与外部能力层分工 | `workflows/software-project-governance/research/default-product-shape.md` | Claude | 2026-04-18 | G2 | 支撑默认产品形态正式收敛 |
| EVD-019 | OPS-001 | 运营 | 文档 | 已形成 Gemini 兼容路线正式方案，明确默认接入顺序与国内 agent CLI 复用抽象 | `adapters/gemini/README.md` | Claude | 2026-04-19 | G7 | 支撑 Gemini 兼容规划进入后续最小验证 |
| EVD-020 | MAINT-003 | 维护 | 文档 | 已形成国内 agent CLI 兼容抽象正式文档，明确三层结构、能力检查清单与默认接入顺序 | `workflows/software-project-governance/research/domestic-agent-cli-compatibility.md` | Claude | 2026-04-19 | G8 | 支撑后续国内 agent CLI 最小验证按统一抽象推进 |
| EVD-021 | PLAN-004 | 规划 | 文档 | 已形成 repo-local 默认主线终止说明正式文档，明确终止原因、保留资产与后续主线接管关系 | `workflows/software-project-governance/research/repo-local-termination-note.md` | Claude | 2026-04-19 | G2 | 支撑旧路线正式收口 |
| EVD-022 | DESIGN-005 | 设计 | 文档 | `plugin-contract` 已正式改写为三层承载模型与集成模式优先协议，明确默认接入要求与投影层边界 | `protocol/plugin-contract.md` | Claude | 2026-04-19 | G3 | 支撑协议层与新主线完全对齐 |
| EVD-023 | DOC-001 | 文档 | 文档 | README 已收敛为路由式入口，显式回指默认产品形态、协议边界、repo-local 终止说明与统一事实源 | `README.md` | Claude | 2026-04-19 | G2 | 支撑对外叙事与正式事实源重新对齐 |
| EVD-024 | MAINT-001 | 维护 | 文档 | 当前项目样例已完成台账瘦身、总览统计重算与重复事项收口，维护治理口径重新一致 | `workflows/software-project-governance/examples/current-project-sample.md` | Claude | 2026-04-19 | G8 | 支撑维护阶段首轮治理闭环 |
| EVD-025 | MAINT-004 | 维护 | 文档 | 已形成外部能力层最小验证方案，明确 `external runner / shared command` 为首轮统一抓手 | `workflows/software-project-governance/research/external-capability-minimum-validation.md` | Claude | 2026-04-19 | G8 | 支撑外部能力层从研究进入最小验证准备 |
| EVD-026 | MAINT-005 | 维护 | 文档 | 已形成 shared command 最小契约样例，明确 `software-project-governance.run` 的输入输出、回写边界和替换边界 | `protocol/external-command-contract.md` | Claude | 2026-04-19 | G8 | 支撑外部能力层从方案进入协议化样例 |
| EVD-027 | MAINT-006 | 维护 | 文档 | 已形成 headless runner 最小样例，明确 `software-project-governance.headless` 的输入映射、execution mode 与运行态状态收敛规则 | `protocol/headless-runner-sample.md` | Claude | 2026-04-19 | G8 | 支撑外部能力层从契约样例进入自动化运行态样例 |
| EVD-028 | PLAN-005 | 规划 | 文档 | 已通过 `DEC-018` 和 `DEC-019` 正式重排实施主线优先级，并承认共同抽象 V1 只是骨架而非强基座 | `workflows/software-project-governance/examples/current-project-sample.md` | Claude | 2026-04-20 | G2 | 支撑优先级收口与基座补强启动 |
| EVD-029 | PLAN-005 | 规划 | 文档 | 已在样例跟踪表新增 `PLAN-005`~`MAINT-007` 七项任务，明确 P0~P3 优先级与执行顺序约束 | `workflows/software-project-governance/examples/current-project-sample.md` | Claude | 2026-04-20 | G2 | 支撑新主线任务正式入账 |
