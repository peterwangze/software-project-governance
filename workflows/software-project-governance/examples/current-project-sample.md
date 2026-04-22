# 当前项目样例

本文件使用当前项目作为 `software-project-governance` workflow 的样例项目。

## 项目配置

- **Profile**: standard（本项目即为工作流产品本身，需要充分验证标准 profile 的治理能力）
- **触发模式**: always-on（每次会话自动加载，持续跟踪项目状态）
- **当前阶段**: 维护与演进（第 11 阶段）
- **并行活跃阶段**: 规划（第 2 阶段）— 主线 A/B 的 P0 任务已进入规划
- **接入方式**: 从立项开始，但前期未正式执行 Gate 检查，2026-04-20 起补正式 onboarding

## Onboarding 声明

本项目从立项开始就使用工作流跟踪，但前期仅使用了记录层（证据、决策、风险），未执行正式 Gate 检查。2026-04-20 起正式执行 onboarding 协议：

- **前置阶段（1~10）Gate**: 全部标记为 `passed-on-entry`
- **当前阶段（11）Gate**: G11 pending，待维护阶段任务进一步推进后检查
- **已补齐的前置阶段关键决策**: 每个前置阶段至少 1 条（见决策记录 DEC-001~DEC-023）

## Gate 状态跟踪

| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |
| --- | --- | --- | --- | --- |
| G1 | → 调研 | passed-on-entry | 2026-04-20 | DEC-001：仓库定位升级为 agent plugin/skill 仓库 |
| G2 | → 技术选型 | passed-on-entry | 2026-04-20 | DEC-006：调研结果驱动后续主线 |
| G3 | → 环境搭建 | passed-on-entry | 2026-04-20 | DEC-005：集成模式优先于目录布局 |
| G4 | → 架构设计 | passed-on-entry | 2026-04-20 | DEC-022：环境配置以仓库分层结构为准 |
| G5 | → 开发实现 | passed-on-entry | 2026-04-20 | DEC-023：CI 校验脚本覆盖全部关键资产 |
| G6 | → 测试 | passed-on-entry | 2026-04-20 | DEC-003：Claude 入口分层设计 |
| G7 | → 防护网与CI/CD | passed-on-entry | 2026-04-20 | DEC-024：测试以校验脚本和 README 一致性检查为主 |
| G8 | → 版本发布 | passed-on-entry | 2026-04-20 | DEC-015：外部能力层首轮验证先走 shared command |
| G9 | → 运营 | passed-on-entry | 2026-04-20 | DEC-025：版本发布以 git commit 为最小发布单元 |
| G10 | → 维护 | passed-on-entry | 2026-04-20 | DEC-009：Gemini 兼容路线规划作为运营回收产出 |
| G11 | → 下一轮 | passed | 2026-04-21 | 复盘完成、经验已回灌到规则和模板（子工作流+skill）、下轮方向明确、版本化记录已更新 |

## 项目总览

| 项目 | 当前阶段 | 总任务数 | 已完成 | 阻塞中 | 关键风险数 | 最近 Gate 结论 | 最近复盘日期 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 项目管理工作流插件 | 维护（并行活跃：规划） | 37 | 31 | 0 | 3 | G11 通过 | 2026-04-21 |


## 样例跟踪表

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner | 协同角色 | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| INIT-001 | 立项 | 明确插件仓库目标 | 将 workflow 定位为 agent plugin/skill 仓库 | 用户澄清事实 | `README.md` | 项目负责人 | Claude | 已完成 | P0 | 2026-04-17 | 2026-04-17 | 2026-04-17 | G1 | 插件目标明确 | `workflows/software-project-governance/manifest.md` | 无 | 无 | 项目定位已收敛 |
| PLAN-001 | 规划 | 定义协议层与分层结构 | 建立 protocol / workflows / adapters 分层 | 项目定位与调研结果 | `protocol/*.md`, `workflows/`, `adapters/` | Claude | 项目负责人 | 已完成 | P0 | 2026-04-17 | 2026-04-17 | 2026-04-17 | G2 | 目录结构与协议层建立 | `protocol/workflow-schema.md` | 无 | 无 | 已完成首版骨架 |
| PLAN-002 | 规划 | 建立统一演进 backlog | 形成可持续推进的事项清单与状态基线 | 当前样例与模板 | `workflows/software-project-governance/examples/current-project-sample.md` | Claude | 项目负责人 | 进行中 | P0 | 2026-04-17 | 2026-04-18 | | G2 | backlog 覆盖核心演进路线 | `workflows/software-project-governance/examples/current-project-sample.md` | 当前颗粒度仍在收敛 | 持续补齐事项与状态 | 作为当前主要推进抓手 |
| DESIGN-001 | 设计 | 建立 Claude/Codex 适配入口 | 支撑多 agent 消费同一套流程资产 | 协议层、规则层 | `adapters/claude/README.md`, `adapters/codex/README.md` | Claude | 项目负责人 | 已完成 | P0 | 2026-04-17 | 2026-04-18 | 2026-04-17 | G3 | 适配入口完整可读 | `adapters/claude/README.md` | 无 | 无 | 首版文档入口已完成 |
| DESIGN-002 | 设计 | 补齐 Claude 半可执行入口 | 让 Claude adapter 从说明文档升级为机器可读入口 | `adapters/claude/README.md` | `adapters/claude/adapter-manifest.json`, `adapters/claude/launch.py` | Claude | 项目负责人 | 已终止 | P1 | 2026-04-17 | 2026-04-18 | 2026-04-17 | G3 | 完成探索性验证并输出可运行样例 | `adapters/claude/adapter-manifest.json` | repo-local 入口侵入性高，不再作为默认产品主线 | 保留为 sample / fallback，不继续扩展 | 已完成历史验证，但从主线路线图降级 |
| DESIGN-003 | 设计 | 补齐 Codex 半可执行入口 | 让 Codex adapter 从说明文档升级为机器可读入口 | `adapters/codex/README.md` | `adapters/codex/adapter-manifest.json`, `adapters/codex/launch.py` | Claude | 项目负责人 | 已终止 | P1 | 2026-04-17 | 2026-04-18 | 2026-04-17 | G3 | 完成探索性验证并输出可运行样例 | `adapters/codex/adapter-manifest.json` | 缺少对 Codex 主流集成方式的系统调研 | 保留为 sample / fallback，不继续扩展 | 已完成历史验证，但不再视为默认接入方案 |
| DESIGN-004 | 设计 | 统一适配器入口协议 | 为 Claude/Codex/Gemini 预留一致的 adapter contract | 协议层、现有适配说明 | `protocol/plugin-contract.md`, `adapters/*` | Claude | 项目负责人 | 已完成 | P1 | 2026-04-17 | 2026-04-19 | 2026-04-17 | G3 | 各适配器共享统一字段和加载顺序 | `protocol/plugin-contract.md` | 旧协议默认 repo-local 形态，需要在新主线下重写 | 由 DESIGN-005 接管重构 | launcher 已按统一 contract 输出 |
| CI-001 | CI | 升级校验脚本覆盖适配层 | 让验证覆盖半可执行入口与新文件 | `scripts/verify_workflow.py` | 更新后的验证脚本 | Claude | 项目负责人 | 已完成 | P0 | 2026-04-17 | 2026-04-18 | 2026-04-17 | G5 | 新增入口文件和关键字段可校验 | `scripts/verify_workflow.py` | 校验口径当前仍偏向旧主线 | 由 PLAN-004 与 DESIGN-005 同步调整 | launcher 与校验脚本均已通过 |
| ACCEPT-001 | 验收 | 落地 Claude 原生 skill 入口 | 让当前项目可直接通过 Claude skill 机制加载 workflow | `CLAUDE.md`, `.claude/skills/software-project-governance/SKILL.md` | 可用的 Claude skill 入口与回写后的样例记录 | Claude | 项目负责人 | 已终止 | P1 | 2026-04-18 | 2026-04-18 | 2026-04-18 | G6 | 完成 Claude repo-local 入口验证 | `CLAUDE.md` | 当前仅证明仓库内接法可运行，不足以证明产品形态正确 | 保留为 sample / fallback，不再作为默认主线 | 当前作为探索性样板保留 |
| RESEARCH-001 | 规划 | 调研主流 agent 工作流集成方式 | 为重新定义产品形态提供事实依据 | Claude/Codex/Gemini 官方集成方式调研 | 调研结论与接入方式矩阵 | Claude | 项目负责人 | 已完成 | P0 | 2026-04-18 | 2026-04-19 | 2026-04-18 | G2 | 明确 repo-local、全局安装、命令入口、MCP 等模式边界 | `workflows/software-project-governance/research/agent-integration-models.md` | 已形成正式调研结论文件 | 以该文档作为后续产品形态设计事实源 | 当前最高优先级事项已闭环 |
| PLAN-003 | 规划 | 基于调研重定义产品形态 | 把仓库定位从 repo-local 入口样板调整为低侵入 workflow 资产仓库 | 调研结论、现有协议层、样例记录 | 默认产品形态方案与更新后的样例主线 | Claude | 项目负责人 | 已完成 | P0 | 2026-04-18 | 2026-04-19 | 2026-04-18 | G2 | 给出新的默认集成策略、分层结构与接入边界 | `workflows/software-project-governance/research/default-product-shape.md` | 默认产品形态方案已正式成文 | 后续 README、协议与实施均以该方案为准 | 新主线切换核心事项已闭环 |
| PLAN-004 | 规划 | 输出旧路线终止说明 | 为此前偏差方向补齐正式终止/降级说明 | 旧计划、已完成入口、用户纠偏意见 | 更新后的样例、决策、风险与证据记录 | Claude | 项目负责人 | 已完成 | P0 | 2026-04-18 | 2026-04-18 | 2026-04-19 | G2 | 旧路线有状态、有原因、有去向，并形成正式终止说明文档 | `workflows/software-project-governance/research/repo-local-termination-note.md` | 已形成 repo-local 默认主线终止说明正式文档 | 后续不再把 repo-local 入口包装为默认产品进展 | 旧路线已完成正式收口 |
| DESIGN-005 | 设计 | 重写 plugin contract 以支持多种集成模式 | 把协议层从 agent 目录布局优先改为集成模式优先 | 调研结论、`protocol/plugin-contract.md` | 新版 plugin contract | Claude | 项目负责人 | 已完成 | P0 | 2026-04-18 | 2026-04-19 | 2026-04-19 | G3 | 协议层不再默认 repo-local 是唯一承载形态，并明确三层承载模型与默认接入要求 | `protocol/plugin-contract.md` | 旧协议与新主线不一致 | 已完成协议重写，并作为后续 README 与实现设计前置约束 | 新主线关键设计抓手已闭环 |
| DOC-001 | 文档 | 重写 README 与接入说明 | 明确当前仓库的低侵入方向、探索性入口和后续路线 | 新主线决策、协议层、调研结论 | 更新后的 `README.md` | Claude | 项目负责人 | 已完成 | P0 | 2026-04-18 | 2026-04-18 | 2026-04-19 | G2 | README 不再把 repo-local 入口写成默认推荐，并显式回指默认产品形态、协议边界与终止说明 | `README.md` | 当前 README 仍会误导使用者 | 已收敛为路由式入口，后续细节统一回指正式事实源 | 当前优先文档修正项已闭环 |
| OPS-001 | 运营 | 规划 Gemini 兼容路线 | 为后续多 agent 扩展准备兼容约束 | `adapters/gemini/README.md`、调研结论 | Gemini 适配路线说明 | 项目负责人 | Claude | 已完成 | P1 | 2026-04-19 | 2026-04-22 | 2026-04-19 | G7 | 给出兼容约束、默认接入顺序与国内 agent CLI 复用边界 | `adapters/gemini/README.md` | 已形成 Gemini 兼容路线正式方案 | 后续优先验证 external runner / MCP，不先扩 repo-local 入口 | 作为运营阶段首轮兼容规划输出 |
| MAINT-001 | 维护 | 收敛优先级与跟踪颗粒度 | 让样例从展示态升级为持续维护态 | 当前 backlog、风险、证据记录 | 更新后的样例与日志 | Claude | 项目负责人 | 已完成 | P1 | 2026-04-17 | 2026-04-20 | 2026-04-19 | G8 | 优先级、统计口径、重复事项与证据状态已同步收敛 | `workflows/software-project-governance/examples/current-project-sample.md` | 当前主线切换导致状态定义需重新校准 | 已完成台账瘦身、总览重算与重复事项收口 | 当前治理动作已完成首轮闭环 |
| MAINT-002 | 维护 | 补更多大厂实践映射 | 增强规则与流程的经验来源 | 当前 research 文档 | 更丰富的实践映射文档 | 项目负责人 | Claude | 未开始 | P2 | 2026-04-19 | 2026-04-25 | | G8 | 增补至少一轮公司实践案例 | `workflows/software-project-governance/research/company-practices.md` | 当前案例覆盖偏通用 | 后续持续补充 | 不阻塞当前主线 |
| MAINT-003 | 维护 | 规划国内 agent CLI 兼容抽象 | 为后续适配国内 agent CLI 预留统一层 | 协议层、Gemini 兼容规划 | 国内 agent 兼容约束说明 | 项目负责人 | Claude | 已完成 | P2 | 2026-04-22 | 2026-04-28 | 2026-04-19 | G8 | 明确能力检查清单、默认接入顺序与复用边界 | `workflows/software-project-governance/research/domestic-agent-cli-compatibility.md` | 已形成统一兼容抽象正式文档 | 后续优先选择支持 external runner / MCP 的国内 agent CLI 做最小验证 | 作为维护阶段的兼容抽象基线 |
| MAINT-004 | 维护 | 定义外部能力层最小验证方案 | 为默认产品形态补第一个可执行验证抓手，避免主线长期停留在纸面设计 | `default-product-shape.md`、Gemini 路线、国内 agent CLI 兼容抽象 | 外部能力层最小验证方案 | Claude | 项目负责人 | 已完成 | P1 | 2026-04-19 | 2026-04-20 | 2026-04-19 | G8 | 明确首轮验证对象、默认顺序、命令约定草案与边界约束 | `workflows/software-project-governance/research/external-capability-minimum-validation.md` | 外部能力层尚未进入真实最小验证，主线存在继续停留在方案层的风险 | 已先收敛 `external runner / shared command` 作为统一抓手，后续按该方案推进最小 command contract 样例 | 作为维护阶段进入外部能力层验证的起点 |
| MAINT-005 | 维护 | 固化 shared command 最小契约样例 | 把外部能力层抓手进一步落成统一协议样例，避免不同 agent 后续各自定义输入输出边界 | `external-capability-minimum-validation.md`、`plugin-contract.md` | shared command 最小契约 | Claude | 项目负责人 | 已完成 | P1 | 2026-04-19 | 2026-04-20 | 2026-04-19 | G8 | 明确 command id、最小输入输出、read order、write-back targets、gate behavior 与 replacement boundary | `protocol/external-command-contract.md` | 若无正式 contract，后续 shared command / MCP / headless runner 仍会各写各的 | 已补齐统一 command contract 样例，并纳入校验口径 | 作为外部能力层最小验证的第一份协议化样例 |
| MAINT-006 | 维护 | 补 headless runner 最小样例 | 验证 shared command 契约能否稳定映射到自动化、CI 与批处理执行面，避免运行态再次各说各话 | `protocol/external-command-contract.md` | headless runner 最小样例 | Claude | 项目负责人 | 已完成 | P1 | 2026-04-19 | 2026-04-20 | 2026-04-19 | G8 | 明确 runner id、execution mode、dry-run / apply 语义、运行态 Gate 行为与状态收敛规则 | `protocol/headless-runner-sample.md` | 若没有运行态样例，后续自动化实现仍可能绕开 shared command 契约重新发明结构 | 已补最小 headless runner 样例，并纳入统一校验口径 | 共同抽象 V1 资产，后续由 PLAN-005 接管补强 |

## 优先级重排后的新主线

以下任务承接"共同抽象基座补强 -> Claude -> Codex -> Gemini / 国内 agent CLI"的优先级顺序。此前 `OPS-001`、`MAINT-003`~`MAINT-006` 构成 V1 骨架与兼容预研资产，不等于正式 agent 适配已完成。

### 主线 A：产品内容层（愿景驱动）

实现"解放用户非思考动作"愿景的核心内容——没有可执行的子工作流和自动化能力，协议架构再好也是空架子。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner | 协同角色 | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PLAN-006 | 规划 | 产品内容层实施路线 | 把愿景"解放用户非思考动作"拆成可执行的产品内容任务，明确两条主线的并行节奏 | 新愿景（`DEC-020`）、当前审视报告 | 产品内容层实施路线与子工作流优先级排序 | Claude | 项目负责人 | 已完成 | P0 | 2026-04-20 | 2026-04-22 | 2026-04-20 | G2 | 明确子工作流优先级、Gate 量化范围、企业经验覆盖计划 | `workflows/software-project-governance/examples/current-project-sample.md` | 无 | 无 | 主线 A 顶层规划，与主线 B 的 PLAN-005 并行 |
| DESIGN-009 | 设计 | 前 4 个阶段子工作流骨架 | 为立项、调研、技术选型、架构设计补 `stages/<stage-id>/sub-workflow.md` | `PLAN-006` 路线、`lifecycle.md` 11 阶段定义 | 4 个 `sub-workflow.md` 文件 | Claude | 项目负责人 | 已完成 | P0 | 2026-04-22 | 2026-04-26 | 2026-04-20 | G3 | 每个子工作流包含进入条件、活动清单、产出物标准、退出条件；可独立被 agent 读取和执行 | `workflows/software-project-governance/stages/` | 无 | 无 | 选择前 4 个是因为它们覆盖从想法到动手的全链路 |
| DESIGN-010 | 设计 | Gate 量化检查项 | 为 G1~G11 每个检查项补可自动判定的通过/未通过标准 | `stage-gates.md` 现有定性检查项、`DESIGN-009` 子工作流定义 | 更新后的 `stage-gates.md` | Claude | 项目负责人 | 已完成 | P0 | 2026-04-24 | 2026-04-27 | 2026-04-20 | G3 | 每个检查项有明确的"通过/未通过"判定标准，agent 可自动执行判定 | `workflows/software-project-governance/rules/stage-gates.md` | 无 | 无 | Gate 量化是"自动看护"的前提 |
| RESEARCH-002 | 调研 | 企业经验深度补强 | 至少覆盖 4 家企业差异化实践，按阶段映射到具体子工作流步骤 | 现有 `company-practices.md` 6 条通用经验 | 按企业拆解、按阶段映射的经验文档 | Claude | 项目负责人 | 已完成 | P1 | 2026-04-27 | 2026-05-02 | 2026-04-21 | G2 | 至少 4 家企业、每家有适用条件和具体检查项、映射到子工作流步骤 | `workflows/software-project-governance/research/company-practices.md` | 无 | 无 | 替代原 MAINT-002 |
| DESIGN-011 | 设计 | 用户交互边界定义 | 明确"问用户"vs"工作流自己决定"的检查项分类 | `DESIGN-009` 子工作流、`DESIGN-010` Gate 量化 | 每个子工作流标注"需人工判断"和"可自动执行"的检查项 | Claude | 项目负责人 | 已完成 | P1 | 2026-04-28 | 2026-05-01 | 2026-04-20 | G3 | 每个子工作流的活动清单和 Gate 检查项都有明确的交互边界标注 | `workflows/software-project-governance/rules/interaction-boundary.md` | 无 | 无 | "解放用户"不等于"不问用户" |
| DESIGN-012 | 设计 | 常用 skill/script 清单与首批实现 | 为需求澄清、技术评审、Code Review、发布 checklist、回顾会议补 skill 定义 | `DESIGN-009` 子工作流中的具体操作步骤 | 5 个 skill/script 定义文件 | Claude | 项目负责人 | 已完成 | P2 | 2026-05-02 | 2026-05-08 | 2026-04-21 | G3 | 每个 skill 有明确的触发条件、输入输出和可独立执行能力 | `workflows/software-project-governance/stages/initiation/requirement-clarification.md`, `stages/architecture/tech-review-checklist.md`, `stages/development/code-review-standard.md`, `stages/release/release-checklist.md`, `stages/maintenance/retro-meeting-template.md` | 无 | 无 | 第三层"具体事务 skill/script 层"首批 5 个 skill 已落地 |

### 主线 B：交付架构层（已有主线）

与主线 A 并行推进，不互相阻塞但互相验证。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner | 协同角色 | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PLAN-005 | 规划 | 共同抽象基座补强方案 | 把 V1 骨架从"有结构"升级为"可承载长期演进的强基座" | 当前三层协议、shared command contract、headless runner 样例 | 基座补强方案与准入标准文档 | Claude | 项目负责人 | 已完成 | P0 | 2026-04-20 | 2026-04-22 | 2026-04-21 | G2 | 明确准入问题、默认推荐判定标准、优先级规则与冲击场景 | `protocol/plugin-contract.md` | 准入标准、冲击场景、validation matrix 已在前期补入；本轮补齐 read_order（子工作流+skill+交互边界）和跨协议一致性引用 | 与 DESIGN-006 合并执行 | 作为 P0 最高优先级，后续所有 agent 适配的前置依赖 |
| DESIGN-006 | 设计 | 补强 integration contract 与 validation matrix | 在 `plugin-contract`、`external-command-contract`、`headless-runner-sample` 中补入准入标准、required/optional 边界、失败语义与冲击场景 | `PLAN-005` 方案、现有协议 | 补强后的协议文件 | Claude | 项目负责人 | 已完成 | P0 | 2026-04-22 | 2026-04-24 | 2026-04-21 | G3 | 协议补入准入标准、validation matrix 与 shock scenarios，且三者口径一致 | `protocol/external-command-contract.md`, `protocol/headless-runner-sample.md`, `protocol/plugin-contract.md` | V1 骨架已在前期多次补强（字段边界、失败语义、准入标准），本轮补齐 read_order 分层结构和跨协议一致性引用 | 与 PLAN-005 同步闭环 | 基座补强的核心设计任务 |
| CI-002 | CI | 升级校验脚本覆盖基座级约束 | 让 `verify_workflow.py` 校验新增的准入标准、优先级顺序与冲击场景关键片段 | 补强后的协议与样例 | 升级后的校验脚本 | Claude | 项目负责人 | 已完成 | P0 | 2026-04-24 | 2026-04-25 | 2026-04-21 | G5 | 校验脚本覆盖基座补强后的所有新关键片段 | `scripts/verify_workflow.py` | 与 DESIGN-006 同步闭环 | 与 DESIGN-006 同步闭环 | 基座补强的防护网 |
| DESIGN-007 | 设计 | Claude 正式默认接法方案与最小实现样例 | 把"Claude 默认优先 personal skill / plugin skill / MCP"从 README 摘要正式收敛为决策+样例+验收标准 | 补强后的共同抽象基座、调研结论 | Claude 正式接法方案与接入说明 | Claude | 项目负责人 | 已完成 | P1 | 2026-04-25 | 2026-04-28 | 2026-04-21 | G3 | 有正式决策、有接入说明或最小样例、有验收标准、显式说明为什么优于 repo-local | `.claude/skills/software-project-governance/SKILL.md` | 准入审计 6 条标准全 PASS（3 直接 PASS + 3 修复后 PASS） | SKILL.md 补齐 replacement_boundary 声明 | Claude 是目标 agent 优先级最高的第一顺位 |
| ACCEPT-002 | 验收 | Claude 正式默认接法验收 | 验证 Claude 正式接法是否严格遵守共同抽象和 write-back 边界 | Claude 正式接法方案 | 验收结论与证据 | Claude | 项目负责人 | 已完成 | P1 | 2026-04-28 | 2026-04-29 | 2026-04-21 | G6 | 正式接法通过基座准入标准、校验脚本通过、决策/风险/证据同步补齐 | 准入审计报告（会话上下文） | 准入审计 6 条标准全 PASS；校验脚本通过 | 与 DESIGN-007 同步闭环 | Claude 验收闭环后才进入 Codex |
| DESIGN-008 | 设计 | Codex 正式接法 | 基于 Claude 验收后的强基座，验证共同抽象跨 agent 可复用 | Claude 验收结论、共同抽象基座 | Codex 接法方案 | Claude | 项目负责人 | 已完成 | P2 | 2026-04-29 | 2026-05-02 | 2026-04-21 | G3 | 复用相同基座与验证矩阵，不复制第二套协议 | `adapters/codex/adapter-manifest.json`, `adapters/codex/README.md` | Codex manifest 已更新为新 read_order（含 profiles、onboarding、interaction-boundary）和 replacement_boundary | 共同抽象基座验证跨 agent 可复用 | 第二顺位目标 agent |
| MAINT-007 | 维护 | Gemini / 国内 agent CLI 在强基座上的最小验证 | 等 Claude/Codex 收敛后，再进入第三优先级 | Claude/Codex 验收结论、`OPS-001`、`MAINT-003` 兼容预研 | Gemini / 国内 agent CLI 最小验证结论 | 项目负责人 | Claude | 未开始 | P3 | 2026-05-02 | 2026-05-08 | | G8 | 在强基座上验证 Gemini / 国内 agent CLI 是否可复用共同抽象 | 待补 | 必须等前序 agent 验收通过后才能启动 | 不因已有研究文档而提前占用执行优先级 | 第三顺位，研究结论已储备但执行后置 |

### 实战验证：CLI 工具升级

用自身工作流管理一个真实项目，验证"内容是否有用"。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner | 协同角色 | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VAL-001 | 开发 | 升级 verify_workflow.py 为 CLI 工具 | 将校验脚本升级为可管理真实项目的 CLI 工具，支持 verify/status/gate/gates/stage/stages 6 个子命令 | 现有 `verify_workflow.py`、治理资产 | 升级后的 CLI 工具 | Claude | 项目负责人 | 已完成 | P0 | 2026-04-21 | 2026-04-21 | 2026-04-21 | G6 | 6 个子命令全部可运行、向后兼容、Windows GBK 兼容 | `scripts/verify_workflow.py` | 无 | 无 | 实战验证首个任务，验证工作流内容对真实开发是否有帮助 |

### 实战验证：Plugin Marketplace 打包

将现有 workflow 资产打包为 Claude Code 和 Codex 官方插件格式，验证交付架构能否真正对接平台。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner | 协同角色 | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VAL-002 | 开发 | Claude Code Plugin Marketplace 打包 | 创建 `.claude-plugin/marketplace.json` 和 `plugin.json`，将现有 skill 打包为 Claude Code 可安装插件 | 调研结论（Claude Code 插件格式）、现有 `.claude/skills/` | `.claude-plugin/marketplace.json`、`plugin.json` | Claude | 项目负责人 | 已完成 | P0 | 2026-04-22 | 2026-04-22 | 2026-04-22 | G6 | marketplace.json 和 plugin.json 符合 Claude Code 插件规范，校验脚本通过 | `.claude-plugin/marketplace.json`, `plugin.json` | 无 | 无 | P0：验证 Claude Code 真实插件接入 |
| VAL-003 | 开发 | Codex Plugin 打包 | 创建 `.codex-plugin/plugin.json`、Codex skill 和 marketplace，验证 Codex 官方插件格式 | 调研结论（Codex 插件格式）、Claude skill 内容 | `.codex-plugin/plugin.json`、`skills/software-project-governance/SKILL.md`、`.agents/plugins/marketplace.json` | Claude | 项目负责人 | 已完成 | P1 | 2026-04-22 | 2026-04-22 | 2026-04-22 | G6 | plugin.json 符合 Codex 插件规范，Codex skill 可独立加载，校验脚本通过 | `.codex-plugin/plugin.json`, `skills/software-project-governance/SKILL.md` | 无 | 无 | P1：验证 Codex 真实插件接入 |
