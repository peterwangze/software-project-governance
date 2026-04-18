# 当前项目样例

本文件使用当前项目作为 `software-project-governance` workflow 的样例项目。

## 项目总览

| 项目 | 当前阶段 | 总任务数 | 已完成 | 阻塞中 | 关键风险数 | 最近 Gate 结论 | 最近复盘日期 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 项目管理工作流插件 | CI | 11 | 8 | 0 | 3 | G5 通过 | 2026-04-18 |

## 样例跟踪表

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner | 协同角色 | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| INIT-001 | 立项 | 明确插件仓库目标 | 将 workflow 定位为 agent plugin/skill 仓库 | 用户澄清事实 | `README.md` | 项目负责人 | Claude | 已完成 | P0 | 2026-04-17 | 2026-04-17 | 2026-04-17 | G1 | 插件目标明确 | `workflows/software-project-governance/manifest.md` | 无 | 无 | 项目定位已收敛 |
| PLAN-001 | 规划 | 定义协议层与分层结构 | 建立 protocol / workflows / adapters 分层 | 项目定位与调研结果 | `protocol/*.md`, `workflows/`, `adapters/` | Claude | 项目负责人 | 已完成 | P0 | 2026-04-17 | 2026-04-17 | 2026-04-17 | G2 | 目录结构与协议层建立 | `protocol/workflow-schema.md` | 无 | 无 | 已完成首版骨架 |
| PLAN-002 | 规划 | 建立统一演进 backlog | 形成可持续推进的事项清单与状态基线 | 当前样例与模板 | `workflows/software-project-governance/examples/current-project-sample.md` | Claude | 项目负责人 | 进行中 | P0 | 2026-04-17 | 2026-04-18 | | G2 | backlog 覆盖核心演进路线 | `workflows/software-project-governance/examples/current-project-sample.md` | 当前颗粒度仍在收敛 | 持续补齐事项与状态 | 作为当前主要推进抓手 |
| DESIGN-001 | 设计 | 建立 Claude/Codex 适配入口 | 支撑多 agent 消费同一套流程资产 | 协议层、规则层 | `adapters/claude/README.md`, `adapters/codex/README.md` | Claude | 项目负责人 | 已完成 | P0 | 2026-04-17 | 2026-04-18 | 2026-04-17 | G3 | 适配入口完整可读 | `adapters/claude/README.md` | 无 | 无 | 首版文档入口已完成 |
| DESIGN-002 | 设计 | 补齐 Claude 半可执行入口 | 让 Claude adapter 从说明文档升级为机器可读入口 | `adapters/claude/README.md` | `adapters/claude/adapter-manifest.json`, `adapters/claude/launch.py` | Claude | 项目负责人 | 已完成 | P0 | 2026-04-17 | 2026-04-18 | 2026-04-17 | G3 | Claude 入口可被脚本消费 | `adapters/claude/adapter-manifest.json` | 无 | 无 | 已落地 launcher 与 manifest |
| DESIGN-003 | 设计 | 补齐 Codex 半可执行入口 | 让 Codex adapter 从说明文档升级为机器可读入口 | `adapters/codex/README.md` | `adapters/codex/adapter-manifest.json`, `adapters/codex/launch.py` | Claude | 项目负责人 | 已完成 | P0 | 2026-04-17 | 2026-04-18 | 2026-04-17 | G3 | Codex 入口可被脚本消费 | `adapters/codex/adapter-manifest.json` | 无 | 无 | 已落地 launcher 与 manifest |
| DESIGN-004 | 设计 | 统一适配器入口协议 | 为 Claude/Codex/Gemini 预留一致的 adapter contract | 协议层、现有适配说明 | `protocol/plugin-contract.md`, `adapters/*` | Claude | 项目负责人 | 已完成 | P1 | 2026-04-17 | 2026-04-19 | 2026-04-17 | G3 | 各适配器共享统一字段和加载顺序 | `protocol/plugin-contract.md` | 无 | 无 | launcher 已按统一 contract 输出 |
| CI-001 | CI | 升级校验脚本覆盖适配层 | 让验证覆盖半可执行入口与新文件 | `scripts/verify_workflow.py` | 更新后的验证脚本 | Claude | 项目负责人 | 已完成 | P0 | 2026-04-17 | 2026-04-18 | 2026-04-17 | G5 | 新增入口文件和关键字段可校验 | `scripts/verify_workflow.py` | 无 | 无 | launcher 与校验脚本均已通过 |
| ACCEPT-001 | 验收 | 落地 Claude 原生 skill 入口 | 让当前项目可直接通过 Claude skill 机制加载 workflow | `CLAUDE.md`, `.claude/skills/software-project-governance/SKILL.md` | 可用的 Claude skill 入口与回写后的样例记录 | Claude | 项目负责人 | 已完成 | P0 | 2026-04-18 | 2026-04-18 | 2026-04-18 | G6 | Claude 可发现 skill 并复用统一事实源 | `CLAUDE.md` | Claude skill 入口格式后续可能演化 | 维持 skill 为薄封装，继续复用 workflow 本体 | 当前项目已可作为 Claude 首版 plugin/skill 样板 |
| OPS-001 | 运营 | 规划 Gemini 兼容路线 | 为后续多 agent 扩展准备兼容约束 | `adapters/gemini/README.md` | Gemini 适配路线说明 | 项目负责人 | Claude | 未开始 | P1 | 2026-04-18 | 2026-04-20 | | G7 | 给出兼容约束与切入顺序 | `adapters/gemini/README.md` | 外部标准不稳定 | 先做约束，不做深实现 | 中期扩展事项 |
| MAINT-001 | 维护 | 收敛优先级与跟踪颗粒度 | 让样例从展示态升级为持续维护态 | 当前 backlog、风险、证据记录 | 更新后的样例与日志 | Claude | 项目负责人 | 进行中 | P1 | 2026-04-17 | 2026-04-19 | | G8 | 优先级有区分，状态与证据同步 | `workflows/software-project-governance/examples/current-project-sample.md` | 当前仍有事项待补证据 | 每次推进后同步更新 | 当前治理动作本身也需被治理 |
| MAINT-002 | 维护 | 补更多大厂实践映射 | 增强规则与流程的经验来源 | 当前 research 文档 | 更丰富的实践映射文档 | 项目负责人 | Claude | 未开始 | P2 | 2026-04-18 | 2026-04-25 | | G8 | 增补至少一轮公司实践案例 | `workflows/software-project-governance/research/company-practices.md` | 当前案例覆盖偏通用 | 后续持续补充 | 不阻塞当前主线 |
| MAINT-003 | 维护 | 规划国内 agent CLI 兼容抽象 | 为后续适配国内 agent CLI 预留统一层 | 协议层、Gemini 兼容规划 | 国内 agent 兼容约束说明 | 项目负责人 | Claude | 未开始 | P2 | 2026-04-20 | 2026-04-28 | | G8 | 明确兼容差异与复用边界 | `<待补>` | 外部差异暂不明朗 | Gemini 路线后再展开 | 外围扩展事项 |
