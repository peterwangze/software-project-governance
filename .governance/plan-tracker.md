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
| 项目管理工作流插件 | 维护（并行活跃：规划） | 109 | 88 | 0 | 1 | G11 通过 | 2026-04-28 |

## 实施路线图（DEC-052）

**核心原则**：先防跑偏，再验证，然后建内容，最后做增强。计划本身必须被治理体系正式记录——不依赖会话上下文。

### 四层推进模型

```
Layer 0: 防跑偏基础 ──→ Layer 1: 外部验证 ──→ Layer 2: 产品内容 ──→ Layer 3: 体验增强
  (项目不会跑偏)         (产品真的存在)         (工作流有价值)         (从能用到好用)
```

### Layer 0: 防跑偏基础（Anti-Drift Foundation）

**目标**：建立治理强制力——证据可信、责任明确、Gate 可脚本判定、agent 行为可外部验证。不依赖 agent "记得"或"自觉"。

```
Tier 0-A: 快速修复（3 tasks, ~1 session）
  AUDIT-026 (P2) — CLAUDE.md/SKILL.md 循环依赖解耦
  AUDIT-027 (P2) — 协议层与实际目录命名统一
  AUDIT-035 (P1) — Agent 失败模式文档与应急预案
  │ 无前置依赖，三个可并行
  ▼
Tier 0-B: 证据可信度（1 task, ~1 session）
  AUDIT-022 (P1) — 证据质量基线升级
  │ 产出：check-governance 新增证据质量检查（循环引用/会话上下文/空输出）
  │ 前置：0-A 完成（证据格式需先稳定）
  ▼
Tier 0-C: 治理强制力（3 tasks, ~2 sessions）
  AUDIT-030 (P1) — DRI 模型落地（Owner 唯一化 + escalation path）
  AUDIT-031 (P1) — M8 自检外部验证（依赖 0-B 的证据检查基础）
  AUDIT-011 (P1) — Gate 自动判定脚本（依赖 0-B 的证据质量模式）
  │ 产出：Gate 可脚本判定，治理合规可外部验证，DRI 唯一化
  ▼
Tier 0-D: 防漂移机制（3 tasks, ~2 sessions）
  AUDIT-029 (P1) — 跨会话记忆机制（session snapshot）
  AUDIT-017 (P1) — 触发模式实现（always-on/on-demand/silent-track）
  AUDIT-018 (P1) — Profile 差异化行为落地（依赖 0-C 的 Gate 判定能力）
```

**Layer 0 小计：10 tasks，P0:0 P1:8 P2:2，预计 ~6 sessions**

### Layer 1: 外部验证（External Validation）

**目标**：在外部项目中验证产品是否真的可用。没有外部反馈，所有内容改进方向都是猜测。

```
Tier 1-A: 最小外部验证（1 task, ~1 session + 外部项目时间）
  AUDIT-003 (P0) — 外部项目验证最小路径
  │ 产出：第一个真实用户反馈
  │ 前置：Layer 0 完成（防跑偏机制就位后，外部验证才有意义）
  ▼
Tier 1-B: 端到端验证（3 tasks, ~1 session）
  AUDIT-023 (P1) — 端到端可用性验证（依赖 AUDIT-003 的外部项目）
  AUDIT-004 (P1) — governance-init 端到端验证（依赖 AUDIT-003）
  AUDIT-006 (P1) — Claude Code 插件命令验证（依赖 AUDIT-003）
```

**Layer 1 小计：4 tasks，P0:1 P1:3，预计 ~2 sessions**

### Layer 2: 产品内容（Product Content）

**目标**：子工作流从骨架升级为深度指南，企业实践从概念变成可执行步骤。

```
Tier 2-A: 内容深度（2 tasks, ~2 sessions）
  AUDIT-021 (P0) — 7 个子工作流内容深度补强（AI风险表+企业实践映射+Gate自动判定列）
  AUDIT-024 (P1) — company-practices-summary 重写（自包含可执行摘要）
  │ 前置：Layer 1 完成（外部反馈告诉我们哪些阶段最需要补强）
  ▼
Tier 2-B: 企业实践落地（4 tasks, ~2 sessions，可并行）
  AUDIT-032 (P1) — Bar Raiser 否决权（Amazon）
  AUDIT-033 (P1) — 字节 A/B 测试纳入 release
  AUDIT-034 (P2) — 华为蓝军单 agent 适配
  AUDIT-036 (P2) — Release 现代发布实践（依赖 AUDIT-021 release 需先有基础深度）
  ▼
Tier 2-C: 质量均衡（3 tasks, ~1 session）
  AUDIT-025 (P2) — Stage skill 质量均衡（依赖 AUDIT-021）
  AUDIT-038 (P2) — 子工作流独立使用目标锚定强制机制（依赖 AUDIT-021）
  MAINT-002 (P2) — 更多大厂实践映射
```

**Layer 2 小计：9 tasks，P0:1 P1:3 P2:5，预计 ~5 sessions**

### Layer 3: 体验增强（Enhancement）

**目标**：从"能用"到"好用"——B/C 级自动化、工具通用化、兼容性政策。

```
Tier 3-A: 自动化升级（4 tasks, ~2 sessions，严格顺序依赖）
  AUDIT-010 (P1) — CI 集成 check-governance（依赖 0-C AUDIT-011）
  AUDIT-014 (P2) — git hook 治理触发（依赖 AUDIT-010）
  AUDIT-012 (P2) — headless runner 可执行版（依赖 0-C AUDIT-011）
  AUDIT-013 (P2) — MCP server 最小实现（依赖 0-C AUDIT-011）
  │
Tier 3-B: 工具通用化（3 tasks, ~2 sessions）
  AUDIT-009 (P2) — 外部项目中途接入验证（依赖 Layer 1 AUDIT-003）
  AUDIT-019 (P2) — verify_workflow.py 通用化（依赖 Layer 1 AUDIT-003）
  AUDIT-020 (P2) — 自定义 Profile YAML 解析（依赖 0-D AUDIT-018）
  │
Tier 3-C: 兼容与政策（4 tasks, ~2 sessions，可并行）
  AUDIT-037 (P2) — 向后兼容性政策与废弃通知
  MAINT-013 (P1) — 用户项目/样例数据边界说明
  MAINT-014 (P1) — Agent 入口差异显式化
  MAINT-023 (P1) — Gemini/国内 agent CLI 最小验证
```

**Layer 3 小计：11 tasks，P0:0 P1:4 P2:7，预计 ~6 sessions**

### 依赖关系总表

| 任务 | 所属 Tier | 前置任务 | 被依赖 |
|------|----------|---------|--------|
| AUDIT-026 | 0-A | 无 | — |
| AUDIT-027 | 0-A | 无 | — |
| AUDIT-035 | 0-A | 无 | — |
| AUDIT-022 | 0-B | 0-A 完成 | AUDIT-031, AUDIT-011 |
| AUDIT-030 | 0-C | 0-B 完成 | — |
| AUDIT-031 | 0-C | AUDIT-022 | — |
| AUDIT-011 | 0-C | AUDIT-022 | AUDIT-018, AUDIT-010/012/013 |
| AUDIT-029 | 0-D | 0-C 完成 | — |
| AUDIT-017 | 0-D | 0-C 完成 | — |
| AUDIT-018 | 0-D | AUDIT-011 | AUDIT-020 |
| AUDIT-003 | 1-A | Layer 0 完成 | AUDIT-023/004/006/009/019 |
| AUDIT-023 | 1-B | AUDIT-003 | — |
| AUDIT-004 | 1-B | AUDIT-003 | — |
| AUDIT-006 | 1-B | AUDIT-003 | — |
| AUDIT-021 | 2-A | Layer 1 完成 | AUDIT-036/025/038 |
| AUDIT-024 | 2-A | Layer 1 完成 | — |
| AUDIT-032 | 2-B | 2-A 完成 | — |
| AUDIT-033 | 2-B | 2-A 完成 | — |
| AUDIT-034 | 2-B | 2-A 完成 | — |
| AUDIT-036 | 2-B | AUDIT-021 | — |
| AUDIT-025 | 2-C | AUDIT-021 | — |
| AUDIT-038 | 2-C | AUDIT-021 | — |
| MAINT-002 | 2-C | 2-A 完成 | — |
| AUDIT-010 | 3-A | AUDIT-011 | AUDIT-014 |
| AUDIT-014 | 3-A | AUDIT-010 | — |
| AUDIT-012 | 3-A | AUDIT-011 | — |
| AUDIT-013 | 3-A | AUDIT-011 | — |
| AUDIT-009 | 3-B | AUDIT-003 | — |
| AUDIT-019 | 3-B | AUDIT-003 | — |
| AUDIT-020 | 3-B | AUDIT-018 | — |
| AUDIT-037 | 3-C | 无 | — |
| MAINT-013 | 3-C | 无 | — |
| MAINT-014 | 3-C | 无 | — |
| MAINT-023 | 3-C | 无 | — |

### 执行纪律

1. **严格按 Tier 顺序推进**：当前 Tier 的所有任务完成后才能进入下一 Tier。
2. **Tier 内部任务可并行**：同一 Tier 内无依赖关系的任务可并行执行。
3. **每个 Tier 完成后执行审计（D1+D3+D4 维度）**：确认 Tier 的目标是否达成，偏差是否已纠正。
4. **计划本身接受 Meta-Audit**：如果连续 2 个 Tier 的执行顺序被打破，说明依赖分析有误 → 重新梳理依赖。


## 样例跟踪表

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| INIT-001 | 立项 | 明确插件仓库目标 | 将 workflow 定位为 agent plugin/skill 仓库 | 用户澄清事实 | `README.md` | 项目负责人 | Claude | 项目负责人 | 已完成 | P0 | 2026-04-17 | 2026-04-17 | 2026-04-17 | G1 | 插件目标明确 | `workflows/software-project-governance/manifest.md` | 无 | 无 | 项目定位已收敛 |
| PLAN-001 | 规划 | 定义协议层与分层结构 | 建立 protocol / workflows / adapters 分层 | 项目定位与调研结果 | `protocol/*.md`, `workflows/`, `adapters/` | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-17 | 2026-04-17 | 2026-04-17 | G2 | 目录结构与协议层建立 | `protocol/workflow-schema.md` | 无 | 无 | 已完成首版骨架 |
| PLAN-002 | 规划 | 建立统一演进 backlog | 形成可持续推进的事项清单与状态基线 | 当前样例与模板 | `workflows/software-project-governance/examples/current-project-sample.md` | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-17 | 2026-04-18 | 2026-04-24 | G2 | backlog 覆盖核心演进路线 | `workflows/software-project-governance/examples/current-project-sample.md` | 当前颗粒度仍在收敛 | 持续补齐事项与状态 | 演进 backlog 已转入维护阶段常态化管理 |
| DESIGN-001 | 设计 | 建立 Claude/Codex 适配入口 | 支撑多 agent 消费同一套流程资产 | 协议层、规则层 | `adapters/claude/README.md`, `adapters/codex/README.md` | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-17 | 2026-04-18 | 2026-04-17 | G3 | 适配入口完整可读 | `adapters/claude/README.md` | 无 | 无 | 首版文档入口已完成 |
| DESIGN-002 | 设计 | 补齐 Claude 半可执行入口 | 让 Claude adapter 从说明文档升级为机器可读入口 | `adapters/claude/README.md` | `adapters/claude/adapter-manifest.json`, `adapters/claude/launch.py` | Claude | 项目负责人 | 项目负责人 | 已终止 | P1 | 2026-04-17 | 2026-04-18 | 2026-04-17 | G3 | 完成探索性验证并输出可运行样例 | `adapters/claude/adapter-manifest.json` | repo-local 入口侵入性高，不再作为默认产品主线 | 保留为 sample / fallback，不继续扩展 | 已完成历史验证，但从主线路线图降级 |
| DESIGN-003 | 设计 | 补齐 Codex 半可执行入口 | 让 Codex adapter 从说明文档升级为机器可读入口 | `adapters/codex/README.md` | `adapters/codex/adapter-manifest.json`, `adapters/codex/launch.py` | Claude | 项目负责人 | 项目负责人 | 已终止 | P1 | 2026-04-17 | 2026-04-18 | 2026-04-17 | G3 | 完成探索性验证并输出可运行样例 | `adapters/codex/adapter-manifest.json` | 缺少对 Codex 主流集成方式的系统调研 | 保留为 sample / fallback，不继续扩展 | 已完成历史验证，但不再视为默认接入方案 |
| DESIGN-004 | 设计 | 统一适配器入口协议 | 为 Claude/Codex/Gemini 预留一致的 adapter contract | 协议层、现有适配说明 | `protocol/plugin-contract.md`, `adapters/*` | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-17 | 2026-04-19 | 2026-04-17 | G3 | 各适配器共享统一字段和加载顺序 | `protocol/plugin-contract.md` | 旧协议默认 repo-local 形态，需要在新主线下重写 | 由 DESIGN-005 接管重构 | launcher 已按统一 contract 输出 |
| CI-001 | CI | 升级校验脚本覆盖适配层 | 让验证覆盖半可执行入口与新文件 | `scripts/verify_workflow.py` | 更新后的验证脚本 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-17 | 2026-04-18 | 2026-04-17 | G5 | 新增入口文件和关键字段可校验 | `scripts/verify_workflow.py` | 校验口径当前仍偏向旧主线 | 由 PLAN-004 与 DESIGN-005 同步调整 | launcher 与校验脚本均已通过 |
| ACCEPT-001 | 验收 | 落地 Claude 原生 skill 入口 | 让当前项目可直接通过 Claude skill 机制加载 workflow | `CLAUDE.md`, `.claude/skills/software-project-governance/SKILL.md` | 可用的 Claude skill 入口与回写后的样例记录 | Claude | 项目负责人 | 项目负责人 | 已终止 | P1 | 2026-04-18 | 2026-04-18 | 2026-04-18 | G6 | 完成 Claude repo-local 入口验证 | `CLAUDE.md` | 当前仅证明仓库内接法可运行，不足以证明产品形态正确 | 保留为 sample / fallback，不再作为默认主线 | 当前作为探索性样板保留 |
| RESEARCH-001 | 规划 | 调研主流 agent 工作流集成方式 | 为重新定义产品形态提供事实依据 | Claude/Codex/Gemini 官方集成方式调研 | 调研结论与接入方式矩阵 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-18 | 2026-04-19 | 2026-04-18 | G2 | 明确 repo-local、全局安装、命令入口、MCP 等模式边界 | `workflows/software-project-governance/research/agent-integration-models.md` | 已形成正式调研结论文件 | 以该文档作为后续产品形态设计事实源 | 当前最高优先级事项已闭环 |
| PLAN-003 | 规划 | 基于调研重定义产品形态 | 把仓库定位从 repo-local 入口样板调整为低侵入 workflow 资产仓库 | 调研结论、现有协议层、样例记录 | 默认产品形态方案与更新后的样例主线 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-18 | 2026-04-19 | 2026-04-18 | G2 | 给出新的默认集成策略、分层结构与接入边界 | `workflows/software-project-governance/research/default-product-shape.md` | 默认产品形态方案已正式成文 | 后续 README、协议与实施均以该方案为准 | 新主线切换核心事项已闭环 |
| PLAN-004 | 规划 | 输出旧路线终止说明 | 为此前偏差方向补齐正式终止/降级说明 | 旧计划、已完成入口、用户纠偏意见 | 更新后的样例、决策、风险与证据记录 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-18 | 2026-04-18 | 2026-04-19 | G2 | 旧路线有状态、有原因、有去向，并形成正式终止说明文档 | `workflows/software-project-governance/research/repo-local-termination-note.md` | 已形成 repo-local 默认主线终止说明正式文档 | 后续不再把 repo-local 入口包装为默认产品进展 | 旧路线已完成正式收口 |
| DESIGN-005 | 设计 | 重写 plugin contract 以支持多种集成模式 | 把协议层从 agent 目录布局优先改为集成模式优先 | 调研结论、`protocol/plugin-contract.md` | 新版 plugin contract | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-18 | 2026-04-19 | 2026-04-19 | G3 | 协议层不再默认 repo-local 是唯一承载形态，并明确三层承载模型与默认接入要求 | `protocol/plugin-contract.md` | 旧协议与新主线不一致 | 已完成协议重写，并作为后续 README 与实现设计前置约束 | 新主线关键设计抓手已闭环 |
| DOC-001 | 文档 | 重写 README 与接入说明 | 明确当前仓库的低侵入方向、探索性入口和后续路线 | 新主线决策、协议层、调研结论 | 更新后的 `README.md` | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-18 | 2026-04-18 | 2026-04-19 | G2 | README 不再把 repo-local 入口写成默认推荐，并显式回指默认产品形态、协议边界与终止说明 | `README.md` | 当前 README 仍会误导使用者 | 已收敛为路由式入口，后续细节统一回指正式事实源 | 当前优先文档修正项已闭环 |
| OPS-001 | 运营 | 规划 Gemini 兼容路线 | 为后续多 agent 扩展准备兼容约束 | `adapters/gemini/README.md`、调研结论 | Gemini 适配路线说明 | 项目负责人 | Claude | 项目负责人 | 已完成 | P1 | 2026-04-19 | 2026-04-22 | 2026-04-19 | G7 | 给出兼容约束、默认接入顺序与国内 agent CLI 复用边界 | `adapters/gemini/README.md` | 已形成 Gemini 兼容路线正式方案 | 后续优先验证 external runner / MCP，不先扩 repo-local 入口 | 作为运营阶段首轮兼容规划输出 |
| MAINT-001 | 维护 | 收敛优先级与跟踪颗粒度 | 让样例从展示态升级为持续维护态 | 当前 backlog、风险、证据记录 | 更新后的样例与日志 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-17 | 2026-04-20 | 2026-04-19 | G8 | 优先级、统计口径、重复事项与证据状态已同步收敛 | `workflows/software-project-governance/examples/current-project-sample.md` | 当前主线切换导致状态定义需重新校准 | 已完成台账瘦身、总览重算与重复事项收口 | 当前治理动作已完成首轮闭环 |
| MAINT-002 | 维护 | 补更多大厂实践映射 | 增强规则与流程的经验来源 | 当前 research 文档 | 更丰富的实践映射文档 | 项目负责人 | Claude | 项目负责人 | 已终止 | P2 | 2026-04-19 | 2026-04-25 | 2026-04-27 | G8 | 增补至少一轮公司实践案例 | — | 被 RESEARCH-002（企业经验深度补强，Google/Amazon/华为/字节 4 家企业差异化实践）和 AUDIT-024（company-practices-summary 自包含可执行摘要重写）覆盖 | 由 RESEARCH-002 + AUDIT-024 替代，MAINT-002 目标已融入后续任务 | RESEARCH-002 已完成 4 家企业实践映射，超出 MAINT-002 原始范围；AUDIT-024 将进一步升级 summary 为可执行规则 |
| MAINT-003 | 维护 | 规划国内 agent CLI 兼容抽象 | 为后续适配国内 agent CLI 预留统一层 | 协议层、Gemini 兼容规划 | 国内 agent 兼容约束说明 | 项目负责人 | Claude | 项目负责人 | 已完成 | P2 | 2026-04-22 | 2026-04-28 | 2026-04-19 | G8 | 明确能力检查清单、默认接入顺序与复用边界 | `workflows/software-project-governance/research/domestic-agent-cli-compatibility.md` | 已形成统一兼容抽象正式文档 | 后续优先选择支持 external runner / MCP 的国内 agent CLI 做最小验证 | 作为维护阶段的兼容抽象基线 |
| MAINT-004 | 维护 | 定义外部能力层最小验证方案 | 为默认产品形态补第一个可执行验证抓手，避免主线长期停留在纸面设计 | `default-product-shape.md`、Gemini 路线、国内 agent CLI 兼容抽象 | 外部能力层最小验证方案 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-19 | 2026-04-20 | 2026-04-19 | G8 | 明确首轮验证对象、默认顺序、命令约定草案与边界约束 | `workflows/software-project-governance/research/external-capability-minimum-validation.md` | 外部能力层尚未进入真实最小验证，主线存在继续停留在方案层的风险 | 已先收敛 `external runner / shared command` 作为统一抓手，后续按该方案推进最小 command contract 样例 | 作为维护阶段进入外部能力层验证的起点 |
| MAINT-005 | 维护 | 固化 shared command 最小契约样例 | 把外部能力层抓手进一步落成统一协议样例，避免不同 agent 后续各自定义输入输出边界 | `external-capability-minimum-validation.md`、`plugin-contract.md` | shared command 最小契约 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-19 | 2026-04-20 | 2026-04-19 | G8 | 明确 command id、最小输入输出、read order、write-back targets、gate behavior 与 replacement boundary | `protocol/external-command-contract.md` | 若无正式 contract，后续 shared command / MCP / headless runner 仍会各写各的 | 已补齐统一 command contract 样例，并纳入校验口径 | 作为外部能力层最小验证的第一份协议化样例 |
| MAINT-006 | 维护 | 补 headless runner 最小样例 | 验证 shared command 契约能否稳定映射到自动化、CI 与批处理执行面，避免运行态再次各说各话 | `protocol/external-command-contract.md` | headless runner 最小样例 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-19 | 2026-04-20 | 2026-04-19 | G8 | 明确 runner id、execution mode、dry-run / apply 语义、运行态 Gate 行为与状态收敛规则 | `protocol/headless-runner-sample.md` | 若没有运行态样例，后续自动化实现仍可能绕开 shared command 契约重新发明结构 | 已补最小 headless runner 样例，并纳入统一校验口径 | 共同抽象 V1 资产，后续由 PLAN-005 接管补强 |

## 优先级重排后的新主线

以下任务承接"共同抽象基座补强 -> Claude -> Codex -> Gemini / 国内 agent CLI"的优先级顺序。此前 `OPS-001`、`MAINT-003`~`MAINT-006` 构成 V1 骨架与兼容预研资产，不等于正式 agent 适配已完成。

### 主线 A：产品内容层（愿景驱动）

实现"解放用户非思考动作"愿景的核心内容——没有可执行的子工作流和自动化能力，协议架构再好也是空架子。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PLAN-006 | 规划 | 产品内容层实施路线 | 把愿景"解放用户非思考动作"拆成可执行的产品内容任务，明确两条主线的并行节奏 | 新愿景（`DEC-020`）、当前审视报告 | 产品内容层实施路线与子工作流优先级排序 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-20 | 2026-04-22 | 2026-04-20 | G2 | 明确子工作流优先级、Gate 量化范围、企业经验覆盖计划 | `workflows/software-project-governance/examples/current-project-sample.md` | 无 | 无 | 主线 A 顶层规划，与主线 B 的 PLAN-005 并行 |
| DESIGN-009 | 设计 | 前 4 个阶段子工作流骨架 | 为立项、调研、技术选型、架构设计补 `stages/<stage-id>/sub-workflow.md` | `PLAN-006` 路线、`lifecycle.md` 11 阶段定义 | 4 个 `sub-workflow.md` 文件 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-22 | 2026-04-26 | 2026-04-20 | G3 | 每个子工作流包含进入条件、活动清单、产出物标准、退出条件；可独立被 agent 读取和执行 | `workflows/software-project-governance/stages/` | 无 | 无 | 选择前 4 个是因为它们覆盖从想法到动手的全链路 |
| DESIGN-010 | 设计 | Gate 量化检查项 | 为 G1~G11 每个检查项补可自动判定的通过/未通过标准 | `stage-gates.md` 现有定性检查项、`DESIGN-009` 子工作流定义 | 更新后的 `stage-gates.md` | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-24 | 2026-04-27 | 2026-04-20 | G3 | 每个检查项有明确的"通过/未通过"判定标准，agent 可自动执行判定 | `workflows/software-project-governance/rules/stage-gates.md` | 无 | 无 | Gate 量化是"自动看护"的前提 |
| RESEARCH-002 | 调研 | 企业经验深度补强 | 至少覆盖 4 家企业差异化实践，按阶段映射到具体子工作流步骤 | 现有 `company-practices.md` 6 条通用经验 | 按企业拆解、按阶段映射的经验文档 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-27 | 2026-05-02 | 2026-04-21 | G2 | 至少 4 家企业、每家有适用条件和具体检查项、映射到子工作流步骤 | `workflows/software-project-governance/research/company-practices.md` | 无 | 无 | 替代原 MAINT-002 |
| DESIGN-011 | 设计 | 用户交互边界定义 | 明确"问用户"vs"工作流自己决定"的检查项分类 | `DESIGN-009` 子工作流、`DESIGN-010` Gate 量化 | 每个子工作流标注"需人工判断"和"可自动执行"的检查项 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-28 | 2026-05-01 | 2026-04-20 | G3 | 每个子工作流的活动清单和 Gate 检查项都有明确的交互边界标注 | `workflows/software-project-governance/rules/interaction-boundary.md` | 无 | 无 | "解放用户"不等于"不问用户" |
| DESIGN-012 | 设计 | 常用 skill/script 清单与首批实现 | 为需求澄清、技术评审、Code Review、发布 checklist、回顾会议补 skill 定义 | `DESIGN-009` 子工作流中的具体操作步骤 | 5 个 skill/script 定义文件 | Claude | 项目负责人 | 项目负责人 | 已完成 | P2 | 2026-05-02 | 2026-05-08 | 2026-04-21 | G3 | 每个 skill 有明确的触发条件、输入输出和可独立执行能力 | `workflows/software-project-governance/stages/initiation/requirement-clarification.md`, `stages/architecture/tech-review-checklist.md`, `stages/development/code-review-standard.md`, `stages/release/release-checklist.md`, `stages/maintenance/retro-meeting-template.md` | 无 | 无 | 第三层"具体事务 skill/script 层"首批 5 个 skill 已落地 |

### 主线 B：交付架构层（已有主线）

与主线 A 并行推进，不互相阻塞但互相验证。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PLAN-005 | 规划 | 共同抽象基座补强方案 | 把 V1 骨架从"有结构"升级为"可承载长期演进的强基座" | 当前三层协议、shared command contract、headless runner 样例 | 基座补强方案与准入标准文档 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-20 | 2026-04-22 | 2026-04-21 | G2 | 明确准入问题、默认推荐判定标准、优先级规则与冲击场景 | `protocol/plugin-contract.md` | 准入标准、冲击场景、validation matrix 已在前期补入；本轮补齐 read_order（子工作流+skill+交互边界）和跨协议一致性引用 | 与 DESIGN-006 合并执行 | 作为 P0 最高优先级，后续所有 agent 适配的前置依赖 |
| DESIGN-006 | 设计 | 补强 integration contract 与 validation matrix | 在 `plugin-contract`、`external-command-contract`、`headless-runner-sample` 中补入准入标准、required/optional 边界、失败语义与冲击场景 | `PLAN-005` 方案、现有协议 | 补强后的协议文件 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-22 | 2026-04-24 | 2026-04-21 | G3 | 协议补入准入标准、validation matrix 与 shock scenarios，且三者口径一致 | `protocol/external-command-contract.md`, `protocol/headless-runner-sample.md`, `protocol/plugin-contract.md` | V1 骨架已在前期多次补强（字段边界、失败语义、准入标准），本轮补齐 read_order 分层结构和跨协议一致性引用 | 与 PLAN-005 同步闭环 | 基座补强的核心设计任务 |
| CI-002 | CI | 升级校验脚本覆盖基座级约束 | 让 `verify_workflow.py` 校验新增的准入标准、优先级顺序与冲击场景关键片段 | 补强后的协议与样例 | 升级后的校验脚本 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-24 | 2026-04-25 | 2026-04-21 | G5 | 校验脚本覆盖基座补强后的所有新关键片段 | `scripts/verify_workflow.py` | 与 DESIGN-006 同步闭环 | 与 DESIGN-006 同步闭环 | 基座补强的防护网 |
| DESIGN-007 | 设计 | Claude 正式默认接法方案与最小实现样例 | 把"Claude 默认优先 personal skill / plugin skill / MCP"从 README 摘要正式收敛为决策+样例+验收标准 | 补强后的共同抽象基座、调研结论 | Claude 正式接法方案与接入说明 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-25 | 2026-04-28 | 2026-04-21 | G3 | 有正式决策、有接入说明或最小样例、有验收标准、显式说明为什么优于 repo-local | `.claude/skills/software-project-governance/SKILL.md` | 准入审计 6 条标准全 PASS（3 直接 PASS + 3 修复后 PASS） | SKILL.md 补齐 replacement_boundary 声明 | Claude 是目标 agent 优先级最高的第一顺位 |
| ACCEPT-002 | 验收 | Claude 正式默认接法验收 | 验证 Claude 正式接法是否严格遵守共同抽象和 write-back 边界 | Claude 正式接法方案 | 验收结论与证据 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-28 | 2026-04-29 | 2026-04-21 | G6 | 正式接法通过基座准入标准、校验脚本通过、决策/风险/证据同步补齐 | 准入审计报告（会话上下文） | 准入审计 6 条标准全 PASS；校验脚本通过 | 与 DESIGN-007 同步闭环 | Claude 验收闭环后才进入 Codex |
| DESIGN-008 | 设计 | Codex 正式接法 | 基于 Claude 验收后的强基座，验证共同抽象跨 agent 可复用 | Claude 验收结论、共同抽象基座 | Codex 接法方案 | Claude | 项目负责人 | 项目负责人 | 已完成 | P2 | 2026-04-29 | 2026-05-02 | 2026-04-21 | G3 | 复用相同基座与验证矩阵，不复制第二套协议 | `adapters/codex/adapter-manifest.json`, `adapters/codex/README.md` | Codex manifest 已更新为新 read_order（含 profiles、onboarding、interaction-boundary）和 replacement_boundary | 共同抽象基座验证跨 agent 可复用 | 第二顺位目标 agent |
| MAINT-007 | 维护 | Gemini / 国内 agent CLI 在强基座上的最小验证 | 等 Claude/Codex 收敛后，再进入第三优先级 | Claude/Codex 验收结论、`OPS-001`、`MAINT-003` 兼容预研 | Gemini / 国内 agent CLI 最小验证结论 | 项目负责人 | Claude | 项目负责人 | 已终止 | P3 | 2026-05-02 | 2026-05-08 | | G8 | 在强基座上验证 Gemini / 国内 agent CLI 是否可复用共同抽象 | 待补 | P3 长期搁置被挤出视线，被 MAINT-023 替代 | 由 MAINT-023 接管，改为"选最友好目标先验证"策略 | 原"等最后"策略失效，DEC-039 决定替换 |

### 实战验证：CLI 工具升级

用自身工作流管理一个真实项目，验证"内容是否有用"。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VAL-001 | 开发 | 升级 verify_workflow.py 为 CLI 工具 | 将校验脚本升级为可管理真实项目的 CLI 工具，支持 verify/status/gate/gates/stage/stages 6 个子命令 | 现有 `verify_workflow.py`、治理资产 | 升级后的 CLI 工具 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-21 | 2026-04-21 | 2026-04-21 | G6 | 6 个子命令全部可运行、向后兼容、Windows GBK 兼容 | `scripts/verify_workflow.py` | 无 | 无 | 实战验证首个任务，验证工作流内容对真实开发是否有帮助 |

### 实战验证：Plugin Marketplace 打包

将现有 workflow 资产打包为 Claude Code 和 Codex 官方插件格式，验证交付架构能否真正对接平台。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| VAL-002 | 开发 | Claude Code Plugin Marketplace 打包 | 创建 `.claude-plugin/marketplace.json` 和 `plugin.json`，将现有 skill 打包为 Claude Code 可安装插件 | 调研结论（Claude Code 插件格式）、现有 `.claude/skills/` | `.claude-plugin/marketplace.json`、`plugin.json` | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-22 | 2026-04-22 | 2026-04-22 | G6 | marketplace.json 和 plugin.json 符合 Claude Code 插件规范，校验脚本通过 | `.claude-plugin/marketplace.json`, `plugin.json` | 无 | 无 | P0：验证 Claude Code 真实插件接入 |
| VAL-003 | 开发 | Codex Plugin 打包 | 创建 `.codex-plugin/plugin.json`、Codex skill 和 marketplace，验证 Codex 官方插件格式 | 调研结论（Codex 插件格式）、Claude skill 内容 | `.codex-plugin/plugin.json`、`skills/software-project-governance/SKILL.md`、`.agents/plugins/marketplace.json` | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-22 | 2026-04-22 | 2026-04-22 | G6 | plugin.json 符合 Codex 插件规范，Codex skill 可独立加载，校验脚本通过 | `.codex-plugin/plugin.json`, `skills/software-project-governance/SKILL.md` | 无 | 无 | P1：验证 Codex 真实插件接入 |

### 实战验证：SKILL.md 行为协议重构

将 SKILL.md 从参考文档范式重构为行为协议范式，解决 agent 不遵循 skill 规则的根本问题。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DESIGN-013 | 设计 | SKILL.md 行为协议重构 | 将 SKILL.md 从参考文档重构为行为协议，解决 agent 不遵循 skill 规则的问题 | 用户反馈（skill 不生效、AskUserQuestion 未被使用）、根因分析（6 个结构性缺陷） | 重构后的 `.claude/skills/` 和 `skills/` 两个 SKILL.md | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-22 | 2026-04-22 | 2026-04-22 | G3 | SKILL.md 使用 MUST/MUST NOT 强制语言、有明确的 AskUserQuestion 触发器映射、有 compliance 自检机制、有优先级声明、校验脚本通过 | `.claude/skills/software-project-governance/SKILL.md`, `skills/software-project-governance/SKILL.md` | 无 | 无 | 解决"skill 作为上下文不等于 skill 被遵循"的根本问题 |
| DESIGN-014 | 设计 | 插件自包含重构 | 端到端验证发现所有预加载路径在插件安装后失效，SKILL.md 引用的文件用户项目里不存在 | 端到端验证报告（6 个 P0/P1 问题）、用户决策（自包含重构） | 自包含 SKILL.md + references/ 目录 + .governance/ 迁移 + commands 修复 + examples 清理 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-23 | 2026-04-23 | 2026-04-23 | G3 | 插件 SKILL.md 不依赖仓库根目录路径、references/ 从 skill 目录解析、.governance/ 从用户 CWD 解析、所有路径通过验证 | `skills/software-project-governance/SKILL.md`, `skills/software-project-governance/references/`, `.governance/` | 审视发现 README 叙事、verify 校验口径、adapter 历史资产定位和双 SKILL 单源化仍未完全收口 | 新增 MAINT-008~MAINT-011 继续闭环 | 解决"从未从用户视角验证插件"的根本问题 |
| MAINT-008 | 维护 | 自包含架构对外叙事收口 | 清理 README、adapter 与研究文档中仍残留的 repo-root / 多文件预加载叙事，统一到自包含插件主线 | 完整审视结果、`DEC-035`、`README.md`、adapter/readme 现状 | 收口后的 README 与相关说明文档 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-23 | 2026-04-24 | 2026-04-24 | G8 | README、adapter 说明、研究文档对默认接法、自包含边界和项目级 `.governance/` 口径一致，不再误导用户回到 repo-local 多文件读取模式 | README.md、manifest.md、adapters/claude/README.md、adapters/codex/README.md | 当前 README 对 Codex 和其他 agent 仍要求 repo-root 克隆/访问，和自包含主线冲突 | 先修 README，再补其余说明文档 | 本轮完成 adapter README 清除旧入口约定 |
| MAINT-009 | 维护 | 校验脚本按三层承载模型分层 | 重构 `verify_workflow.py`，区分 workflow 本体层必需资产、项目级事实源、可选投影层/历史样例，避免脚本把可替换资产钉成必需项 | 完整审视结果、`protocol/plugin-contract.md`、`skills/software-project-governance/SKILL.md`、`scripts/verify_workflow.py` | 分层后的校验口径与更新后的验证脚本 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-23 | 2026-04-24 | 2026-04-24 | G8 | 校验脚本不再要求历史 adapter / repo-local 投影必须存在；验证结果能区分必需资产与可选投影；replacement boundary 与校验口径一致 | scripts/verify_workflow.py | 当前校验脚本把 CLAUDE.md、adapter、examples 迁移指针等全部钉成 REQUIRED_FILES，违反可替换边界 | 先拆 REQUIRED_FILES 分层，再补对应校验输出 | 本轮补入 skills/references/、skills/stages/ 等 22+5 条新检查项 |
| MAINT-010 | 维护 | 历史 adapter 资产退场策略 | 明确 `adapters/` 是历史样例、调试基线还是正式 contract 的一部分，并补统一 deprecated 元数据或退出机制 | 完整审视结果、`adapters/*`、`DEC-004`、`DEC-011` | 明确的 adapter 资产定位与对应元数据/说明 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-24 | 2026-04-25 | 2026-04-24 | G8 | `adapters/` 的保留范围、消费边界和校验策略被统一定义，不再出现”README 说废弃、脚本说必需、manifest 仍像正式入口”的混搭状态 | adapters/claude/README.md、adapters/codex/README.md | 当前历史 adapter 的 contract 身份和保留边界未完全收口 | 已清除旧入口约定并标注历史章节 | 由本轮完整审视新增 |
| MAINT-011 | 维护 | 双 SKILL 单源化或等价校验 | 消除 `skills/` 与 `.claude/skills/` 两份 SKILL.md 长期漂移风险 | 完整审视结果、两个 SKILL.md、`scripts/verify_workflow.py` | 单源化方案：声明 skills/ 为正源、verify_workflow.py 逐字节等价校验 7 个文件 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-24 | 2026-04-25 | 2026-04-24 | G8 | 两份 SKILL 的关系被显式定义（skills/ 正源，.claude/skills/ 投影）；校验能发现任意字节漂移 | EVD-071、DEC-042 | 当前双份 SKILL 仅做片段校验，长期易漂移 | 已在 verify_workflow.py 增加 check_skill_equivalence() 逐字节比较 7 个文件 | 由本轮完整审视新增，本轮闭环 |
| MAINT-012 | 维护 | 首次使用路径收口 | 从首次安装用户视角收口 README、初始化、命令兜底和 agent 差异说明，避免”装上了但不会开始用” | 用户视角审视结果、`README.md`、`commands/governance-*.md`、插件定义文件 | 收口后的首次使用文档与命令说明 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-23 | 2026-04-24 | 2026-04-24 | G8 | 用户能明确知道：怎么安装、是否已可用、第一步先做什么、未初始化时各命令如何引导、不同 agent 的入口差异是什么 | README.md, commands/governance-*.md | 当前 README 对 Codex/其他 agent 可操作性不足，命令层缺少未初始化兜底 | 先修 README 和 commands，再处理更细的 agent 差异 | 由用户视角完整审视新增 |
| MAINT-013 | 维护 | 用户项目数据与仓库样例数据边界说明 | 明确仓库内 `.governance/` 仅为本仓样例，不是用户初始化模板，避免用户误把作者运行数据当自己的初始状态 | 用户视角审视结果、`README.md`、仓库内 `.governance/` | 明确的数据边界说明 | Claude | 项目负责人 | 项目负责人 | 未开始 | P1 | 2026-04-27 | 2026-04-29 | | G8 | README 或初始化说明中明确区分”仓库样例数据”和”用户项目运行数据” | 待补 | 当前同名 `.governance/` 容易让首次 clone 用户误解其身份 | 重新排期——原 deadline 2026-04-25 已过，本轮修复中重新排期 | 由用户视角完整审视新增 |
| MAINT-014 | 维护 | agent 入口差异显式化 | 为 Claude、Codex、Gemini/其他 agent 给出独立的安装-初始化-日常使用路径，避免只对 Claude 可操作、对其他 agent 仅有作者视角说明 | 用户视角审视结果、`README.md`、插件定义、compatibility 文档 | 按 agent 区分的用户入口说明 | Claude | 项目负责人 | 项目负责人 | 未开始 | P1 | 2026-04-27 | 2026-04-29 | | G8 | 每个 agent 都有可执行的首条路径；研究路线不会再被包装成现成接法 | 待补 | 当前不同 agent 的用户入口路径不对齐 | 重新排期——原 deadline 2026-04-25 已过，本轮修复中重新排期 | 由用户视角完整审视新增 |
| MAINT-015 | 维护 | 自包含插件 references/ 补全 | 将 `profiles.md`、`onboarding.md`、`interaction-boundary.md` 从 `workflows/rules/` 同步到 `skills/references/` 和 `.claude/skills/references/` | 完整审视结果、P0-1 | 6 个新 references 文件（两个目录各 3 个） | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-24 | 2026-04-24 | 2026-04-24 | G8 | 通过 skills/ 加载的 agent 能够发现 profile 选择、中途接入协议和交互边界规则 | `skills/software-project-governance/references/profiles.md` | 无 | 无 | 本轮用户视角审视新增 P0-1 |
| MAINT-016 | 维护 | skills/ 下创建 stages/ 目录 | 将 `workflows/stages/` 全部子工作流和 skill 复制到 `skills/software-project-governance/stages/`，使自包含插件真正包含可用的阶段子工作流和具体 skills | 完整审视结果、P0-2 | `skills/software-project-governance/stages/` 目录（11 个子工作流 + 5 个 skill） | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-24 | 2026-04-24 | 2026-04-24 | G8 | 用户说"帮我做 Code Review"时，agent 能从 skills/stages/ 找到对应文件 | `skills/software-project-governance/stages/` | 无 | 无 | 本轮用户视角审视新增 P0-2 |
| MAINT-017 | 维护 | SKILL.md M2 预加载指令升级 | 将 M2 从简单列举升级为完整的 M2.1（references/ 按需读取表）+ M2.2（stages/ 子工作流和 skills 目录），两个 SKILL.md 同步更新 | 完整审视结果、P0-3 | 升级后的两个 SKILL.md | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-24 | 2026-04-24 | 2026-04-24 | G8 | agent 加载 skill 后能发现所有可用的 references 文件和 stages/ 资源 | `.claude/skills/software-project-governance/SKILL.md`, `skills/software-project-governance/SKILL.md` | 无 | 无 | 本轮用户视角审视新增 P0-3 |
| MAINT-018 | 维护 | skills/references/ 新增企业经验摘要 | 在 `skills/references/` 中创建 `company-practices-summary.md`，让自包含插件用户也能获取企业实践经验 | 完整审视结果、P1-4 | `skills/software-project-governance/references/company-practices-summary.md` | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-24 | 2026-04-24 | 2026-04-24 | G8 | 插件用户能通过 references/ 获取企业实践经验摘要，并知道完整文档在哪 | `skills/software-project-governance/references/company-practices-summary.md` | 无 | 无 | 本轮用户视角审视新增 P1-4 |
| MAINT-019 | 维护 | adapter README 旧入口约定清除 | 将 `adapters/claude/README.md` 和 `adapters/codex/README.md` 中仍残留的 repo-root 多文件预加载指令折叠为已废弃的历史章节，避免与自包含架构冲突 | 完整审视结果、P1-5 | 清理后的两份 adapter README | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-24 | 2026-04-24 | 2026-04-24 | G8 | adapter README 不再引导用户执行旧的多文件预加载流程 | `adapters/claude/README.md`, `adapters/codex/README.md` | 无 | 无 | 本轮用户视角审视新增 P1-5 |
| MAINT-020 | 维护 | verify_workflow.py 覆盖新增 skills/ 资产 | 校验脚本补入 `skills/references/` 新增文件、`skills/stages/` 全部文件、`.claude/skills/references/` 新增文件的检查项，并修复 adapter snippet 检查 | 完整审视结果 | 更新后的 `scripts/verify_workflow.py` | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-24 | 2026-04-24 | 2026-04-24 | G8 | 全量校验通过，新增 22 个 REQUIRED_FILES 条目和 5 个 OPTIONAL_PROJECTION_FILES 条目 | `scripts/verify_workflow.py` | 无 | 无 | 本轮用户视角审视新增 |
| MAINT-021 | 维护 | CLAUDE.md 治理 bootstrap | 将 CLAUDE.md 从"指针文件"升级为"治理 bootstrap"，包含 3 条无条件前置检查：读 plan-tracker → 任务入账 → 补证据。解决"SKILL.md 被加载但从未被执行"的根本问题 | 用户反馈（工作流自我管理无效，持续走偏）、根因分析（CLAUDE.md 是唯一每次会话必定生效的入口，但被浪费成指针） | 重写后的 `CLAUDE.md` | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-24 | 2026-04-24 | 2026-04-24 | G8 | agent 每次会话第一动作必须是读 plan-tracker；不依赖 SKILL.md 是否被加载 | `CLAUDE.md` | 仅解决本仓库行为，用户项目需 MAINT-022 配合 | 与 MAINT-022 配套闭环 | 本轮用户反馈核心问题 |
| MAINT-022 | 维护 | governance-init 注入 CLAUDE.md bootstrap | 更新 `governance-init` 命令，在初始化时自动向用户项目的 CLAUDE.md 注入治理 bootstrap 段落，确保用户项目获得与本仓库一致的治理激活行为 | 用户反馈（本仓库 CLAUDE.md 有 bootstrap，用户项目没有 = 开发/生产行为不一致） | 更新后的 `commands/governance-init.md` | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-24 | 2026-04-24 | 2026-04-24 | G8 | 用户执行 governance-init 后，其项目的 CLAUDE.md 自动获得治理 bootstrap | `commands/governance-init.md` | 无 | 无 | 本轮用户反馈核心问题配套 |
| MAINT-023 | 维护 | Gemini / 国内 agent CLI 入口适配（从纸面研究进入最小验证） | 已有兼容预研（OPS-001、MAINT-003~006）和契约样例，但从未真正验证共同抽象能否跨 agent 复用。Claude/Codex 前序验收已闭环，前置条件满足 | 兼容预研资产、shared command contract、headless runner 样例 | Gemini 或一个国内 agent CLI 的最小验证结论 | Claude | 项目负责人 | 项目负责人 | 未开始 | P1 | 2026-04-25 | 2026-05-02 | | G8 | 至少一个非 Claude/Codex agent 能复用共同抽象（shared command 或 MCP），产出验证结论和差距清单 | 待补 | MAINT-007 作为 P3 长期搁置，在反复架构修补中被挤出视线 | 先选一个最友好的目标 agent 做最小验证，不追求全覆盖。由 DEC-039 重新拉回计划 | 替代原 MAINT-007 的"等到最后"策略，改为"选最友好目标先验证" |
| MAINT-024 | 维护 | 企业经验驱动的子工作流优化（首批 4 阶段） | RESEARCH-002 完成了 Google/Amazon/华为/字节实践→阶段映射，但从未执行"用这些经验改造工作流本身"。当前子工作流是通用骨架，未针对 AI 编程项目特征做适配 | RESEARCH-002 企业实践文档、4 个目标阶段的子工作流 | 优化后的立项/架构设计/开发/测试 4 个子工作流（含 AI 风险表、企业实践标注、自动化判定、企业实践溯源） | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-25 | 2026-05-03 | 2026-04-24 | G8 | 每个优化后的子工作流包含：(1) AI 编程场景特有风险表；(2) 每个活动标注企业实践来源；(3) Gate 检查项有自动化判定列；(4) 企业实践溯源表 | EVD-069、DEC-040 | 企业经验停在"调研报告"层的问题已解 | 后续按此模式扩展其余 7 个阶段 | 由 DEC-039 拉回计划。4 个子工作流同步到 skills/ 副本 |
| MAINT-025 | 维护 | 工作流内容三层架构正式落地（总入口+锚定检查+工具索引） | 用户审视发现当前工作流不符合原始三层设计：Tier1 缺统一总入口和场景匹配机制；Tier2 子工作流独立使用时断了与总目标的锚定链；Tier3 工具散落各处无统一索引。两个基础目的未贯穿到每个子工作流和工具 | 审视结论（DEC-041）、现有 lifecycle.md 三层架构定义 | `main-workflow.md`（总入口）、所有 11 个子工作流补锚定检查、`TOOLS.md`（统一工具索引）、lifecycle.md/SKILL.md 同步更新 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-24 | 2026-04-24 | 2026-04-24 | G8 | (1) main-workflow.md 声明两个基础目的+场景匹配规则+跨层调用协议；(2) 11 个子工作流含独立使用时的目标锚定检查；(3) TOOLS.md 含 6 工具详情+关系矩阵；(4) verify_workflow.py PASSED | EVD-070、DEC-041 | 三层架构从"纸面设计"进入"可执行落地" | 后续验证 main-workflow.md 实际约束力和锚定检查执行率 | 直接响应用户"工作流层面三层设计"的审视反馈 |
### README 承诺 vs 实现 审计驱动任务（AUDIT-xxx）

以下任务基于 2026-04-24 全量审计（DEC-045），按 P0→P1→P2 排序。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AUDIT-001 | 维护 | P0: 建立"自动"的明确语义分级 | 区分三类自动化能力，让 README 不再用笼统的"自动"误导用户 | 审计报告 P0-1 | (A) agent protocol automation：agent 读规则执行 ← 当前能力；(B) CLI-enforced automation：脚本/CI 强制检查 ← 可近期实现；(C) system automation：hook/daemon/MCP 触发 ← 需外部能力层 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-25 | 2026-04-26 | 2026-04-24 | G8 | README 不再承诺当前未实现的自动化级别；三类自动化有明确的能力边界和前提条件 | EVD-075 | README 当前承诺的"全自动"实际上只有 (A) 级别 | 先修正 README 承诺措辞，再规划 (B) 和 (C) 的实现路线 | 这是审计发现的最根本问题——承诺与能力不匹配 |
| AUDIT-002 | 维护 | P0: CLAUDE.md bootstrap 升级为强制验证点 | 让唯一的强制入口不只是"读 plan-tracker"，而是执行 3 项可自动判定的检查 | 审计报告 P0-2 | CLAUDE.md bootstrap 升级：读 plan-tracker → 对照 evidence-log 检查任务完成但缺证据 → 对照 stage-gates 检查 Gate 是否通过 → 任一失败则阻止执行并告知用户 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-25 | 2026-04-27 | 2026-04-24 | G8 | bootstrap 包含 3 项可自动判定的强制检查（证据完整性、Gate 状态、风险过期），任一失败 agent 必须告知用户 | EVD-084 | 当前 bootstrap 只要求"读"plan-tracker，不执行任何检查 | 先做最小可用版本（证据完整性检查），再扩展 Gate 和风险检查 | 这是不需要外部框架就能立即提升"自动化"程度的最高杠杆点 |
| AUDIT-003 | 维护 | P0: 设计外部项目验证的最小路径 | 定义"在外部项目上验证工作流"的最少步骤和成功标准，结束 100% 狗粮测试 | 审计报告 P0-3 | 选定 1 个外部测试项目 + 定义验证 checklist：安装→初始化→agent 行为→命令可用→证据/Gate 实际触发 | Claude | 项目负责人 | 项目负责人 | 未开始 | P0 | 2026-04-26 | 2026-04-30 | | G8 | 至少 1 个外部项目走通全链路（安装→初始化→任务执行→证据记录→Gate 检查→复盘） | 待补 | 从未在外部项目验证，开发/生产体验差距未知 | 选最简单的场景（如一个个人小项目）先验证 | 不验证外部体验，所有优化都是自嗨 |
| AUDIT-004 | 维护 | P1: governance-init 端到端验证 + 修缺 | 在外部项目中验证 init 命令的 8 步流程，修复发现的问题 | 审计报告 P1-1 | 验证报告 + 修复后的 governance-init.md + 修正的 bootstrap 注入（覆盖 Claude/Codex） | Claude | 项目负责人 | 项目负责人 | 未开始 | P1 | 2026-04-28 | 2026-05-02 | | G8 | init 在外部项目上 8 步全通过、创建的文件被 agent 后续会话读取、bootstrap 注入后 agent 行为改变 | 待补 | 当前未在外部项目验证；bootstrap 注入只支持 CLAUDE.md | 先在一个新的 Claude Code 项目中走通完整 init | P0 外部验证（AUDIT-003）的子任务 |
| AUDIT-005 | 维护 | P1: skill 独立使用与治理前置条件解耦 | 解决"用户只想用 Code Review skill 但没初始化 governance"时的死锁 | 审计报告 P1-2 | 每个 skill 的独立使用说明增加"如果 .governance/ 不存在"的降级路径：跳过锚定检查，直接执行 skill 核心流程，末尾提醒用户初始化以获得完整治理 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-27 | 2026-04-28 | 2026-04-24 | G8 | 5 个 skill 全部有未初始化降级路径；用户不需要先初始化就能使用独立 skill | EVD-076 | 当前锚定检查要求读 plan-tracker，未初始化时此步骤失败 | 这是一个关键设计修正——独立使用不应被治理前置条件阻塞 | 直接修复，不需要等外部验证 |
| AUDIT-006 | 维护 | P1: Claude Code 插件命令端到端验证 | 在外部项目中验证 `/governance-status`、`/governance-gate`、`/governance-verify` 是否可调用且行为正确 | 审计报告 P1-3 | 验证报告 + 修复后的命令文件 | Claude | 项目负责人 | 项目负责人 | 未开始 | P1 | 2026-04-28 | 2026-04-30 | | G8 | 3 个命令在插件安装后可调用、输出正确、未初始化时有引导 | 待补 | 命令从未在"安装后"的环境中测试 | P0 外部验证（AUDIT-003）的子任务 |
| AUDIT-007 | 维护 | P1: 证据完整性的 CLI 强制检查 | 在 verify_workflow.py 中新增 `check-governance` 子命令：检查 plan-tracker 中已完成任务是否有对应证据、活跃风险是否过期、Gate 状态是否与证据一致 | 审计报告 P0-2, P1-5 | `python scripts/verify_workflow.py check-governance` 子命令 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-26 | 2026-04-28 | 2026-04-24 | G8 | (1) 已完成任务无证据 → 列出缺失；(2) 活跃风险超过 7 天未更新 → 标记过期；(3) Gate 状态与证据不一致 → 报告 | EVD-083 | 当前 verify 只检查文件存在和片段，不检查治理完整性 | 这是 CLI 层（B 级自动化）能立即实现的最高价值功能 | 不需要外部验证，直接在本仓库开发并狗粮测试 |
| AUDIT-008 | 维护 | P2: README 承诺措辞修正 | 基于审计结论修正 README 中过度承诺的措辞，区分"当前能做到""近期将做到""需要外部框架" | 审计报告 P0-1, P1-5 | 修正后的 README（尤其是标题、一句话说明、日常体验三个区域） | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-04-27 | 2026-04-28 | | G8 | 用户读完 README 后对"自动"的理解与当前实际能力一致；承诺 = 已验证能力 | 待补 | 当前 README 的"全自动"在用户心中建立的是 system automation 预期 | 在 AUDIT-001 语义分级完成后执行 | 先用诚实的语言描述当前能力，等 (B)/(C) 自动化实现后再升级承诺 |
| AUDIT-009 | 维护 | P2: 外部项目中途接入体验验证 | 在外部已有项目中验证 onboarding 协议的用户体验 | 审计报告 P2-2 | 验证报告：用户能否在 5 分钟内完成中途接入、是否需要补充过多信息、前置 Gate 标记是否合理 | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-02 | 2026-05-06 | | G8 | 用户在 5 个问答内完成中途接入、agent 正确标记前置 Gate、下一会话 agent 正确识别当前阶段 | 待补 | 中途接入体验完全未验证 | P0 外部验证（AUDIT-003）的延伸任务 | 可与非狗粮项目验证合并执行 |
| AUDIT-010 | 维护 | P1: CI 集成 check-governance（B 级自动化） | 让 check-governance 在 CI/预提交阶段自动运行，阻断不完整治理记录合并 | AUDIT-007（check-governance 子命令 + --fail-on-issues） | GitHub Actions workflow 或 pre-commit hook 配置，每次 push 自动运行 check-governance | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-26 | 2026-04-28 | | G8 | CI 中 check-governance 失败时阻断合并；输出与 verify 同级的 PASSED/FAILED | 待补 | 当前 check-governance 只能手动运行，无自动执行框架 | 先做 GitHub Actions workflow，再扩展其他 CI 平台 | B 级自动化从"可手动运行"升级为"自动强制执行" |
| AUDIT-011 | 维护 | P1: Gate 自动判定脚本（B 级自动化） | 让 verify_workflow.py 能自动判定指定 Gate 的通过/未通过状态，而不只是展示规则文本 | DESIGN-010（Gate 量化检查项）、子工作流定义 | `python scripts/verify_workflow.py gate-check G<N>` 子命令，对指定 Gate 执行自动判定并输出通过/未通过/有条件通过 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-28 | 2026-05-02 | 2026-04-26 | G8 | (1) G1~G5 检查项可自动判定（20 项检查，19 PASS + 1 NEEDS_HUMAN）；(2) 未通过检查项有明确缺失说明；(3) gate-check 子命令可用且输出结构化结果；(4) --fail-on-blocked 支持 CI 集成 | EVD-103 | 当前 gate 子命令只展示规则不执行判定——已从"展示规则"升级为"自动判定" | 先覆盖 G1~G5 可自动判定的检查项（文件存在/片段存在/数字阈值），人工判断项标记为 NEEDS_HUMAN | B 级自动化从"脚本展示规则"升级为"脚本执行判定"——Gate 判定不再依赖 agent 手动推理 |
| AUDIT-012 | 维护 | P2: headless runner 可执行版（C 级自动化） | 将 MAINT-006 的 headless runner 从协议样例升级为可运行脚本，首次实现无 agent 参与的治理巡检 | MAINT-006（headless runner 样例）、shared command contract | 可执行的 headless runner 脚本，支持 dry-run/apply 模式，可被 cron/CI 调度 | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-02 | 2026-05-08 | | G8 | (1) 可在无 agent 环境下运行；(2) dry-run 输出治理状态报告；(3) apply 模式自动补 evidence-log 和风险标记 | 待补 | 当前 headless runner 只是协议定义，无可执行代码 | 先实现 status 模式（只读巡检），再扩展 apply 模式（自动写回） | C 级自动化从纸面进入可运行 |
| AUDIT-013 | 维护 | P2: MCP server 最小实现（C 级自动化） | 提供 MCP server，让 external agent 可以通过 MCP 协议查询治理状态，首次验证三层架构中"外部能力层"的 MCP 路径 | shared command contract、headless runner、三层承载模型 | MCP server 最小实现，支持 status / gate / check-governance 三个 tool | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-05 | 2026-05-12 | | G8 | MCP server 可通过 MCP 协议被 agent 发现和调用；3 个 tool 返回结构化 JSON | 待补 | 外部能力层从未通过 MCP 验证过 | 先做 Python MCP server，使用 mcp 官方 SDK | C 级自动化进入 MCP 路径验证 |
| AUDIT-014 | 维护 | P2: git hook 治理触发（C 级自动化） | git commit/push 时自动提示治理记录更新，缩小"做完了但忘了记"的窗口 | git hook 机制、check-governance、plan-tracker 结构 | post-commit hook 模板，自动检测本次变更涉及的 task ID 并提示更新 plan-tracker 和 evidence-log | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-08 | 2026-05-10 | | G8 | hook 在 commit 后自动运行，输出"本次变更可能相关的 task ID 列表 + 建议更新的记录类型" | 待补 | 当前 100% 依赖 agent 在会话中记得更新记录，无系统层兜底 | 先做信息提示（不自动修改），验证准确性后再考虑自动写回 | C 级自动化进入 hook 路径验证 |

### 用户视角审视驱动任务（AUDIT-015~020）

以下任务基于 2026-04-25 全量用户视角审视（本次会话），聚焦 README 承诺 vs 实现的系统性差距。与 AUDIT-001~014（README 审计驱动，2026-04-24）互补。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AUDIT-015 | 维护 | P0: 子工作流"自动"活动标注审计与修正 | 11 个子工作流中标注为"自动"的活动（网页搜索、执行 PoC、运行性能测试、Docker 验证、安全扫描等），agent 实际无法可靠自动完成。用户看到的"自动"实际上是 agent 的尽力而为（可能幻觉或不准确），与 README 建立的"全自动"预期冲突 | 用户视角审视报告（类别 A、D） | 对所有子工作流中标注"自动"的活动重新分类为 6 级交互边界分类体系：agent 执行 / agent 执行 → 需用户确认 / agent 执行（结果需人工验证） / 需CI环境执行 / 需测试环境执行 / 需监控环境执行 / 需开发环境执行 / 需外部环境执行 / 需人工XX | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-26 | 2026-05-02 | 2026-04-25 | G8 | (1) 7 个子工作流（research/selection/infrastructure/ci-cd/release/operations/maintenance）全部完成活动标注重分类；(2) 不保留任何 agent 无法可靠执行的"自动"标注；(3) 标注体系与 A/B/C 自动化分级口径一致 | EVD-090 | 无 | 无 | 修正完成：原 4 个子工作流（initiation/architecture/development/testing）无"自动"标注，本次修正了其余 7 个子工作流共 56 处标注 |
| AUDIT-016 | 维护 | P0: 命令层从 Markdown 指令升级为确定性执行框架 | `commands/governance-*.md` 当前是给 agent 阅读的 Markdown 指令文件，非可执行代码。每次执行结果依赖 agent 的解读质量，不同 session/不同 agent 可能产出不同结果。用户执行同一命令两次可能得到不一致的体验 | 用户视角审视报告（类别 C） | (1) 创建 `protocol/command-schema.md` 定义通用命令协议（5 强制章节：Input Parameters/Execution Flow/Output Format/Error Codes/Self-Validation）；(2) 重写 4 个 commands 为带显式 schema 的协议文件；(3) verify_workflow.py 新增 snippet 检查覆盖 command-schema.md 和 4 个命令的 5 强制章节 + 错误码 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-26 | 2026-05-04 | 2026-04-25 | G8 | (1) 4 个命令有明确的输入输出 schema；(2) 命令按决策树协议执行，消除自然语言歧义；(3) 错误码体系统一（INIT/STATUS/GATE/VERIFY-ERR-XXX） | EVD-091 | 无 | 无 | 升级完成：每个命令含 5 强制章节；错误码体系统一；verify_workflow.py 新增 26 个 snippet 检查覆盖全部命令 schema 内容 |
| AUDIT-017 | 维护 | P1: 触发模式（always-on/on-demand/silent-track）实现机制 | `references/lifecycle.md` 定义了三种触发模式，但完全依赖 agent 自行遵守。无 hook、daemon、或 session 注入机制来实际切换模式。用户选择"静默跟踪"后 agent 仍然正常输出，选择"始终在线"后 agent 可能忘记加载 | 用户视角审视报告（类别 B） | (1) always-on 模式：在 CLAUDE.md bootstrap 中落实为每次会话的强制前置动作，不依赖 SKILL.md 加载状态；(2) on-demand 模式：用户主动调用命令时才激活；(3) silent-track 模式：agent 正常工作但不输出治理面板，仅在 Gate 阻断时提醒。三种模式差异可被检测到 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-28 | 2026-04-28 | 2026-04-28 | G8 | (1) CLAUDE.md bootstrap Step 0 新增触发模式感知——读取 plan-tracker 项目配置中的触发模式，按 always-on/on-demand/silent-track 三种模式调整行为（完整 bootstrap/最小检查/静默跟踪仅 Gate 阻断时提醒）；(2) 三种模式差异可被检测到——切换模式后 agent 治理输出量显著变化；(3) verify_workflow.py PASSED | EVD-118 | 当前三种模式仅是文档标签，切换模式对 agent 行为无任何实际影响 | 先落实 always-on（CLAUDE.md bootstrap 已部分解决），再补 on-demand 和 silent-track | 触发模式是 README 宣传的核心能力（"不打扰你"），已从概念落地为可检测行为差异 |
| AUDIT-018 | 维护 | P1: Profile 差异化行为落地到执行路径 | `references/profiles.md` 定义了轻量/标准/严格三种 profile 的阶段范围和 Gate 强度差异，但这些差异仅存在于文档。轻量级合并了阶段（G1+G2 merged, G3-G5 skipped 等）但没有对应的合并子工作流模板；profile 选择不影响 agent 的实际执行路径 | 用户视角审视报告（类别 E） | (1) 为轻量级 profile 设计合并后的简化子工作流（最少 1 个样板）；(2) 在 governance-init 中 profile 选择影响实际创建的 plan-tracker 列数和 Gate 结构；(3) agent 在运行时能根据 profile 调整检查强度（如 strict 下强制要求 ≥2 evidence） | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-28 | 2026-04-28 | 2026-04-28 | G8 | (1) governance-init Step 5 支持三种 profile 的差异化 plan-tracker 生成规则——lightweight（7 Gates+6列）/standard（11 Gates+20列）/strict（11 Gates 量化评分+20列+强制证据注释）；(2) profiles.md 新增"Profile 差异化行为"节——9 维度可观察差异+Agent 行为自动调整规则；(3) verify_workflow.py PASSED | EVD-120 | 用户选"轻量"后仍然面对 11 阶段全量表、18 列全字段 plan-tracker——轻量化只是个名字 | governance-init 按 profile 生成不同结构的 plan-tracker——从"名字不同"升级为"产出不同" | 如果 profile 没区别，README 的"项目规模选择"表格就是在误导用户 |
| AUDIT-019 | 维护 | P2: verify_workflow.py 通用化——从狗粮工具升级为外部项目可用 | `verify_workflow.py` 的 check-governance 子命令解析的是工作流仓库自身的 `.governance/` 记录（evidence-log、risk-log 的特定编号格式），无法直接在外部项目中使用。用户在自己的项目里运行 check-governance 将因字段格式差异而失败或产出错误结果 | 用户视角审视报告（类别 H） | check-governance 子命令支持解析外部项目的治理记录：(1) 不再硬编码 EVD-xxx/RISK-xxx/DEC-xxx 编号格式；(2) 基于字段名而非编号前缀匹配；(3) 在外部项目中测试通过 | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-08 | 2026-05-14 | | G8 | (1) check-governance 在外部项目（非工作流仓库）中运行正确；(2) PASSED/FAILED 判定基于治理记录实际内容而非预期编号 | 待补 | 当前 check-governance 只能在工作流仓库自身运行——这是狗粮工具不是产品工具 | 先在 AUDIT-003 选定的外部测试项目中验证，再修代码 | CLI 工具如果只在开发仓库能用，就不是产品 |
| AUDIT-020 | 维护 | P2: 自定义 Profile YAML 解析实现 | `references/profiles.md` 第 75-101 行定义了用户在项目中通过 YAML 自定义 profile 的格式（声明阶段启用/禁用、Gate 合并规则、记录强度），但无任何代码解析此配置。用户写了自定义配置也不会生效 | 用户视角审视报告（类别 H） | 在 verify_workflow.py 或独立脚本中实现自定义 profile 解析：(1) 读取项目根目录的 profile 配置文件；(2) 根据配置调整 Gate 检查范围和强度；(3) 解析失败时有明确错误提示 | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-12 | 2026-05-20 | | G8 | (1) 用户在项目中创建 profile 配置文件后，Gate 检查行为确实按配置改变；(2) 格式错误时有可读的错误提示；(3) 文档中的 YAML 样例可被解析 | 待补 | profiles.md 定义了 YAML 格式但无解析代码——用户按文档写配置但不会生效 | 先定义解析规则和 schema，再做最小实现 | P2 增强功能，不阻塞基本使用 |

### 第二轮全量审计驱动任务（AUDIT-021~027）

以下任务基于 2026-04-26 第二轮全量审计（目标→实现差距），与 AUDIT-001~020（前两轮审计）互补。本轮聚焦 3 个维度：(1) 内容深度——59 个已完成任务中有多少是"真正有用"的；(2) 证据可信度——证据能否经得起复盘；(3) 外部可用性——用户能否端到端使用。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AUDIT-021 | 维护 | P0: 子工作流内容深度补强——7 个浅层子工作流从骨架升级为深度指南 | 7 个子工作流（research/selection/infrastructure/ci-cd/release/operations/maintenance）只有基础表结构（进入条件/活动清单/退出条件），缺少 3 个关键深度要素：(1) AI 编程场景风险表——agent 执行该阶段时常见的失败模式；(2) 企业经验映射列——每条活动对应的 Google/Amazon/华为/字节实践；(3) Gate 自动判定列——检查项能否被脚本自动判定或需人工判断。用户在这 7 个阶段得到的引导质量显著低于 initiation/architecture/development/testing | 第二轮全量审计类别 B1 | 7 个子工作流的升级版：(1) 每个新增 AI 编程场景风险表（≥3 条风险/阶段）；(2) 活动清单增加企业经验映射列；(3) Gate 映射增加自动判定列（可脚本判定/需人工判断）。达到与 initiation/architecture 同等的深度标准 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-27 | 2026-04-27 | 2026-04-27 | G8 | (1) 7 个子工作流各新增 ≥3 条 AI 场景风险；(2) 活动清单有企业与经验映射；(3) Gate 自动判定列完整；(4) verify_workflow.py PASSED | EVD-114 | 用户在 release/operations 阶段得到的 agent 引导与 initiation 阶段差异巨大——半成品的半成品 | 先完成 2 个样板（release + operations），验证深度模板后批量复制到其余 5 个——策略执行成功 | 这是 AUDIT-015 的后续——AUDIT-015 修了标签，AUDIT-021 补内容深度 |
| AUDIT-022 | 维护 | P1: 证据质量基线升级——消除会话上下文依赖与空口验证 | 证据记录中存在 3 类质量问题：(1) ~30% 证据（约 30 条）位置标注为"会话上下文"——会话结束后证据不可追溯，违反"全程留痕可复盘"承诺；(2) EVD-070 存在循环引用（"详见 EVD-070 完整内容"——自己证明自己）；(3) 多数证据类型标注"命令输出"但未附带实际输出——宣称的验证无法独立核实。结构性问题：证据无持久化机制、无格式验证、无完整性检查 | 第二轮全量审计类别 D1/D2/D3 | (1) 修正所有"会话上下文"引用——替换为持久化文件路径或删除无法追溯的证据；(2) 修复 EVD-070 循环引用；(3) 在 check-governance 中新增证据质量检查项：检测循环引用、检测"会话上下文"引用、检测空输出声明；(4) 升级 governance-verify 命令的输出模板要求附带实际命令输出 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-05-02 | 2026-05-08 | 2026-04-26 | G8 | (1) 证据记录中"会话上下文"引用清零（5 条全部修复）；(2) EVD-070 循环引用修复为实际内容；(3) check-governance 新增 Check 4：证据质量检查（会话上下文/循环引用/空输出），PASSED 0 issues；(4) verify_workflow.py PASSED | EVD-100 | 如果 30% 的证据在会话结束后消失，那"可复盘"就是一句空话 | 先修正现有证据（替换会话上下文引用），再加脚本层自动检查预防复发 | 5 条 EVD（031/034/039/043/074）会话上下文→持久化路径；EVD-070 自引用→实际内容；verify_workflow.py 新增 check_evidence_quality() 函数 |
| AUDIT-023 | 维护 | P1: 端到端可用性验证——在外部项目中验证安装→初始化→使用完整路径 | README 描述了 3 种安装方式（插件市场/git/本地克隆）→ 5 分钟初始化 → 日常使用，但从未有人在外部项目中完整走通过。当前所有验证均在工作流仓库自身完成（狗粮模式）。产品假设"用户安装后就能用"，但这个假设从未被测试。E3 是 AUDIT-003（外部项目验证，P0）的"体验质量"维度 | 第二轮全量审计类别 E3 | (1) 选择 1 个外部项目（不包含 .governance/）；(2) 从零执行 README 安装步骤 → governance-init → 完成至少 1 个阶段的任务跟踪 → 运行 governance-verify；(3) 记录所有卡住用户的问题（安装失败/命令不可用/模板不匹配/agent 不执行规则）；(4) 根据发现修正 README 和命令文件 | Claude | 项目负责人 | 项目负责人 | 未开始 | P1 | 2026-05-04 | 2026-05-12 | | G8 | (1) 在外部项目中按 README 步骤完成初始化；(2) 成功运行 4 个 governance 命令至少各 1 次；(3) 产出体验问题清单 + 对应修复 | 待补 | 当前项目是 workflow 开发仓库——所有"用户验证"实际上是开发者自己跑脚本 | AUDIT-003 选定的外部测试项目优先做端到端验证；可与 AUDIT-003 合并执行 | 这个是"产品是否真的存在"的最后检验——如果 README 步骤走不通，产品就不存在 |
| AUDIT-024 | 维护 | P1: company-practices-summary 从目录导航升级为可执行规则摘要 | `skills/software-project-governance/references/company-practices-summary.md`（23 行）仅有企业名称+实践名称的列表，无任何可执行内容。agent 读完后知道"Google 有 Design Doc"但不知道如何执行 Design Doc 评审。用户期望 summary 文件提供开箱即用的规则，实际得到的是导航链接——需要再跳转到完整文件才能找到内容 | 第二轮全量审计类别 B3 | 重写 summary 为自包含的可执行摘要：(1) 每条实践有 1 句话的"什么时候用"；(2) 每条实践有 2-3 条可执行的检查项；(3) 标注适用的 profile 和阶段。agent 加载 summary 即可执行企业实践指导，不需要再跳转完整文件 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-27 | 2026-04-27 | 2026-04-27 | G8 | (1) summary 包含每个实践的适用条件和检查项；(2) agent 只加载 summary 就能执行企业实践评审；(3) 完整文件保留为深度参考 | EVD-115 | 用户加载 "company-practices-summary" 得到的是"去读 company-practices.md"——summary 不 summarize 任何东西 | 先重写 summary（自包含），再确认完整文件与 summary 不重复 | 这是"Reference"目录中质量最薄弱的文件 |
| AUDIT-025 | 维护 | P2: Stage skill 质量均衡——5 个 stage skill 达到一致深度 | 5 个 stage skill 深度差异显著：code-review-standard（159 行，P0-P3 分级，4 步执行流程）远深于 release-checklist（112 行，部分步骤标记 agent 执行但需外部环境）。用户在不同阶段调用 skill 得到不一致的体验质量——code review 得到系统级评审框架，release 得到基础 checklist | 第二轮全量审计类别 B4 | (1) release-checklist 升级：增加可逆性判断矩阵、回滚验证的具体步骤模板、监控指标清单；(2) retro-meeting-template 升级：增加数据驱动复盘（量化指标 vs 目标对比表）、action item 跟踪模板；(3) 5 个 skill 的深度标准统一：≥120 行、≥4 步执行流程、≥1 个可填充模板 | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-10 | 2026-05-18 | | G8 | (1) release-checklist ≥ 130 行含具体步骤模板；(2) retro-meeting-template ≥ 130 行含量化对比表；(3) 5 个 skill 全部达到统一深度标准 | 待补 | tech-review 和 code-review 是深度产品，release 和 retro 是半成品——同一产品包里质量不一致 | 先升级 release-checklist（最常用），再升级 retro-meeting-template | P2 质量均衡——不阻塞使用但影响专业感受 |
| AUDIT-026 | 维护 | P2: CLAUDE.md / SKILL.md 双入口解耦——消除循环依赖 | CLAUDE.md bootstrap 第 46 行声明"不依赖 SKILL.md 是否被加载"，但第 36 行引用 SKILL.md M5.3 作为"关键决策"的定义来源。冲突场景：SKILL.md 未加载 → 关键决策分类缺失 → CLAUDE.md 的提问规则失去了判断依据 → agent 要么每次提问（过度打扰）要么全部自动执行（可能遗漏关键决策）。两个入口的设计意图正确（最薄 bootstrap + 完整规则），但实现引入了隐含的加载顺序依赖 | 第二轮全量审计类别 G1 | (1) 将"关键决策分类"从 SKILL.md M5.3 复制到 CLAUDE.md bootstrap section（自包含）；(2) 或者 CLAUDE.md 明确声明：如果 SKILL.md 未加载，关键决策默认为"所有范围/架构/发布决策"（保守默认）；(3) 消除任意一个文件缺失时产生的定义空白 | Claude | 项目负责人 | 项目负责人 | 已完成 | P2 | 2026-05-08 | 2026-05-10 | 2026-04-26 | G8 | (1) CLAUDE.md 加载后不依赖 SKILL.md 即可正确执行提问规则；(2) SKILL.md 加载后增强但不冲突；(3) 两个文件独立可用 | EVD-097 | 当前双入口在大部分场景下工作（因为两者都加载），但边界 case（SKILL.md 未加载）下行为未定义 | 选择方案 (1)：将关键决策 6 类清单复制到 CLAUDE.md 的 bootstrap 区域 | P2——当前实际使用中两者通常一起加载，但架构债应清理 |
| AUDIT-027 | 维护 | P2: 协议层与实际目录命名统一 | `protocol/plugin-contract.md` 定义最小承载单元时使用了设计时称谓（"rules"、"stage skills"），但实际目录结构是 `skills/software-project-governance/references/`（不是 rules/）和 `skills/software-project-governance/stages/*/skill-name.md`（不是集中式的 stage skills/）。新开发者按协议文档找对应目录会找不到——协议描述的是概念模型而非物理布局 | 第二轮全量审计类别 G2 | (1) plugin-contract.md 最小承载单元章节增加"实际路径"列：写明每个逻辑单元对应的物理路径；(2) 或统一术语：将物理目录重命名以匹配协议称谓（仅在确认不影响所有引用后执行）；(3) 优先方案 (1)——加映射表，不改目录 | Claude | 项目负责人 | 项目负责人 | 已完成 | P2 | 2026-05-08 | 2026-05-10 | 2026-04-26 | G8 | (1) plugin-contract.md 有逻辑→物理路径映射；(2) 新开发者按协议能找到对应目录；(3) 不破坏现有引用 | EVD-098 | audit 过程自身——按协议文件找 rules/ 目录，实际路径是 references/ | 方案 (1) 最小侵入：在 contracts 加映射表 | P2 开发者体验改进 |

| MAINT-027 | 维护 | AskUserQuestion 唯一合法提问通道 + 关键决策分类机制 | 用户指出两个预期未落地：(1) AskUserQuestion 应是一致使用的提问工具；(2) 用户应能选择"仅在关键决策停下来"。M5/M7 有规则但 agent 实际未执行 | 用户反馈 | SKILL.md M5 升级为 M5.1~M5.4、M7 升级为 M7.1~M7.3、M8 自检升级、interaction-boundary.md 新增关键决策分类、CLAUDE.md 新增提问规则+自动 commit | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-24 | 2026-04-24 | 2026-04-24 | G8 | (1) M5.1: 内联文字提问=违规；(2) M5.3: 6 类关键+6 类非关键决策分类；(3) M7.1: 用户可声明"仅在关键决策停下来"；(4) verify_workflow.py PASSED | EVD-073、DEC-044 | 无 | 无 | 解决"规则写了但 agent 不执行"的执行一致性问题 |
| MAINT-026 | 维护 | 清理 .claude/skills/ 冗余副本 | 用户已通过插件市场加载本地目录，不再需要手工维护 .claude/skills/ 副本。DEC-042 建立的逐字节等价校验也随副本删除而移除 | 用户决策 | 删除 .claude/skills/ 目录、移除 verify_workflow.py 等价校验、清理 settings.local.json 同步 hooks、更新 CLAUDE.md 引用 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-24 | 2026-04-24 | 2026-04-24 | G8 | .claude/skills/ 已删除、verify_workflow.py PASSED、治理记录已更新 | EVD-072、DEC-043 | 无 | 无 | 用户明确指示：插件市场接管同步，无需手工维护副本 |
| MAINT-028 | 维护 | Tier 1 双源合并：skills/ 成为运行时唯一事实源 | 三层架构审计发现 workflows/rules/、workflows/stages/ 与 skills/ 形成双事实源，协议与实现分叉。skills/ 正式成为运行时唯一事实源 | 三层架构审计报告（6 项结构性问题） | 删除 workflows/rules/（5 文件）、workflows/stages/（11 目录）、workflows/main-workflow.md、workflows/TOOLS.md；更新全部协议和文档路径；verify_workflow.py 移除冗余检查项 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-25 | 2026-04-25 | 2026-04-25 | G8 | (1) workflows/ 不再包含规则层和阶段层副本；(2) 所有协议和文档的 Tier 1 定义指向 skills/；(3) verify_workflow.py PASSED | EVD-086、DEC-047 | 无 | 无 | 架构审计驱动——协议描述现实而不是描述愿望 |
| MAINT-029 | 维护 | 全量冗余清理：修复 5 类陈旧引用 | MAINT-028 和 MAINT-026 遗留了指向已删除路径的陈旧引用（main-workflow.md rules/→references/、adapter-manifest.json .claude/skills/→skills/、adapter README .claude/skills/、SKILL.md replacement boundary、.gitignore 死规则），agent 加载时可能断链 | 冗余审计报告（8 项发现） | 5 个文件共 15 处编辑：(1) main-workflow.md: rules/→references/（9 处）；(2) adapter-manifest.json: skill_path 更新；(3) adapters/claude/README.md: .claude/skills/→skills/（4 处）；(4) skills/SKILL.md: 移除已删除目录引用；(5) .gitignore: 移除 3 条死规则 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-25 | 2026-04-25 | 2026-04-25 | G8 | (1) agent 加载 main-workflow.md 不再遇到断链；(2) 所有文件不再引用 .claude/skills/（已删除）；(3) .gitignore 无死规则；(4) verify_workflow.py PASSED | EVD-088 | 无 | 无 | MAINT-028 配套清理——删完文件还要清理引用 |
| AUDIT-028 | 维护 | 审计框架融入工作流：audit-framework.md 正式接入治理体系 | 用户要求"将审计作为重要的看护手段融入工作流，所有阶段必须接受审计"。已创建 `skills/software-project-governance/references/audit-framework.md`（6 维度 × 3 类别审计体系），需同步接入 stage-gates（Gate 原则 #7）、lifecycle（治理规则 #5）、SKILL.md（M1 触发条件 + M2.1 引用表）、verify_workflow.py（文件检查 + snippet 校验） | 用户指令 + audit-framework.md 初稿 | (1) stage-gates.md 新增 Gate 执行原则 #7：审计检查点；(2) lifecycle.md 新增治理规则 #5：审计看护；(3) SKILL.md M2.1 引用表新增 audit-framework.md 行，M1 新增审计触发条件；(4) verify_workflow.py 新增 audit-framework.md 文件检查和 13 个 snippet 校验；(5) 治理记录同步更新 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-26 | 2026-04-26 | 2026-04-26 | G8 | (1) 全量校验 PASSED；(2) check-governance 0 issues；(3) audit-framework.md 被 Gate/生命周期/SKILL 行为协议正式引用 | EVD-094 | 无 | 无 | 审计从"文档中存在"升级为"被治理体系的每个关键环节强制引用"——Gate 过之前必须审计，生命周期规则包含审计看护，SKILL 加载时审计维度可用 |

### 第三轮审计驱动任务（AUDIT-029~038）

以下任务基于 2026-04-26 第三轮全量审计（成熟企业实践 + AI 编程特殊性视角），与前两轮审计互补。本轮聚焦 3 个维度：(1) 企业实践映射——Google/Amazon/Meta/Apple/华为/字节的成熟机制在工作流中的缺失；(2) AI 编程特殊性——agent 执行可靠性、证据持久化、人-AI 交接、跨会话记忆；(3) 架构一致性——协议与实现的对齐、质量均衡。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AUDIT-029 | 维护 | P1: 跨会话记忆机制——agent 状态恢复协议 | agent 会话结束后项目上下文（当前阶段语义、未完成事项的讨论细节、用户偏好）完全丢失。下一会话 agent 仅能从 .governance/ 文件重建——但如果加载不完整或未正确解读，就会出现上下文断裂。人类项目经理有持续记忆，AI agent 每次会话是"失忆"状态。需要：会话结束时自动生成状态快照（当前阶段、活跃任务、待确认决策、用户偏好），下一会话 agent 加载快照即可恢复上下文 | 第三轮审计类别 AI 特殊性 | (1) 定义会话状态快照格式（session-snapshot.md）；(2) 在 M4.1 Session Start Protocol 中增加"加载上次会话快照"步骤；(3) 在 M4.2 Session End Protocol 中增加"生成状态快照"步骤；(4) 可选：在 verify_workflow.py 增加快照完整性检查 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-28 | 2026-04-28 | 2026-04-28 | G8 | (1) SKILL.md M4.2 定义 session-snapshot.md 完整格式（当前状态+carry-over 任务+待确认决策+活跃风险+已完成/未完成事项+下轮优先级）；(2) M4.1 升级——加载快照+对照 plan-tracker 恢复 carry-over 任务/决策/风险；(3) CLAUDE.md Step 1 新增跨会话状态恢复、收工前检查新增快照生成；(4) verify_workflow.py PASSED | EVD-118 | 当前 agent 跨会话"失忆"是 AI 编程工作流最根本的挑战——没有状态恢复协议，治理连续性靠 agent 自觉 | 先定义快照格式（最小字段），再实现 M4.1/M4.2 的加载/生成步骤 | 与 AUDIT-017（触发模式实现）互补——触发模式控制 agent 侵入程度，会话快照控制 agent 记忆连续性 |
| AUDIT-030 | 维护 | P1: DRI（直接责任人）模型落地——Owner 唯一化 + 向上请示路径 | Apple DRI 模型要求每件事有且仅有一个直接责任人，Amazon Single-Threaded Owner 要求一个人全职负责一件事。当前 plan-tracker 的 Owner 列允许多个 owner（"Claude"+"项目负责人"同时出现），无"谁拥有最终决策权"的定义。当任务阻塞时，向上请示路径（escalation path）不存在 | 第三轮审计企业实践 Apple/Amazon | (1) plan-tracker 的 Owner 字段升级为单值（DRI），新增 Escalation 列（阻塞时向谁请示）；(2) SKILL.md 新增 DRI 行为规则：任务分配时必须明确唯一 DRI，多 owner = 未分配；(3) stage-gates.md 新增 Gate 检查项：每个活跃任务是否有明确 DRI；(4) interaction-boundary.md 新增 DRI 决策权限定义 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-05-04 | 2026-05-12 | 2026-04-26 | G8 | (1) plan-tracker 的 Owner 列改为单值；(2) 每个活跃任务有唯一 DRI；(3) Gate 检查时发现无 DRI 的任务→条件通过+创建纠偏任务 | EVD-101 | AI agent 与人类协同时，责任边界模糊是最大风险——agent 认为人类应该决定，人类认为 agent 应该自动执行 | DRI 明确化对 AI 协作项目比传统项目更重要——agent 需要明确的决策权限边界才能正确执行 M5.3 的关键决策分类 | 与 M5.3 关键决策分类联动——DRI 定义了"谁有权限做关键决策" |
| AUDIT-031 | 维护 | P1: M8 自检外部验证机制——消除 agent 自我审计的内在矛盾 | SKILL.md M8 要求 agent 在每项主要任务后自检："所有用户问题都用了 AskUserQuestion？非关键决策自动执行了？"。但让 agent 自我报告违规是内在矛盾——不遵守协议的 agent 也不会诚实地自我报告。成熟企业（华为/Amazon）的审计是独立第三方执行的 | 第三轮审计类别 AI 特殊性 | (1) 在 check-governance 中新增"协议遵守检查"（Check 5）：DRI 违规检测、条件通过未创建纠偏任务、证据格式缺失必填字段；(2) SKILL.md M8 升级为 M8+M8.1 双重机制（agent 自检 + 脚本独立验证）；(3) M8.1 明确外部验证的 3 个强制时机（Gate 通过前/session 结束/P0 任务完成后） | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-05-06 | 2026-05-14 | 2026-04-26 | G8 | (1) check-governance 能独立检测至少 3 类协议违规（DRI缺失/条件通过未纠偏/证据格式缺失）；(2) agent 自我检查 + 独立脚本验证形成双重机制；(3) verify_workflow.py PASSED | EVD-102 | agent 自我审计 = 学生自己批改自己的考卷——独立性为零 | 先从最容易脚本化的检查开始（DRI/条件通过/格式），再逐步扩展到复杂检查（内联提问需会话日志） | 这本质上是把"审计的审计"从 agent 手动升级为脚本自动——Meta-Audit 的 B 级自动化 |
| AUDIT-032 | 维护 | P1: Amazon Bar Raiser 否决权——独立评审从建议升级为否决权 | Amazon Bar Raiser 是有否决权的独立第三方——可以单方面阻止 hiring/launch 决策。当前 architecture/tech-review-checklist.md 中的"独立评审人"只有建议权无否决权——评审人"建议修改"但无法阻止通过。评审结论中的"需修改"选项缺乏强制性——谁负责验证修改已完成？修改未完成能否通过 Gate？ | 第三轮审计企业实践 Amazon | (1) tech-review-checklist.md 评审结论新增"否决（Block）"选项——独立评审人可以单方面阻止 Gate 通过；(2) stage-gates.md G5（设计完成）新增检查项：技术评审中是否有否决意见？有 → Gate blocked 直到否决解除；(3) 定义"独立评审人"的资格要求（非作者、非同一 agent、具备对应领域知识） | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-28 | 2026-04-28 | 2026-04-28 | G8 | (1) 评审结论有"否决（Block）"选项且能阻止 Gate 通过；(2) 否决意见有解除条件和重新评审流程；(3) 独立评审人资格要求已定义（非作者/非同一agent/具备领域知识）+ 单agent最低标准（切换分析框架+挑战3个核心假设） | EVD-119 | 没有否决权的评审 = 橡皮图章。Amazon 花了几十年证明：独立评审人必须有权说"不" | 单 agent 场景下需定义"独立"的最低标准——至少要求 agent 从对立面重新分析而非复用同一分析框架 | 与 AUDIT-034（蓝军单agent限制）互补——否决权是组织机制，蓝军是思维机制 |
| AUDIT-033 | 维护 | P1: 字节跳动 A/B 测试文化纳入 release 阶段 | 字节文化要求"不接受无数字的结论"——每次发布必须有可衡量的影响评估。当前 release/sub-workflow.md 的发布后验证仅检查"核心功能是否正常"，不检查"用户体验是否改善"、"关键指标是否提升"。缺少：A/B 测试分流、灰度发布、功能标记、影响评估报告 | 第三轮审计企业实践 字节跳动 | (1) release/sub-workflow.md 新增"5. 影响评估"活动（5 项活动含 A/B 测试分析+核心指标对比+无数据替代判定）；(2) release-checklist.md 新增"第五步：数据验证计划"（A/B 测试方案+核心指标基线+回滚触发条件+5 种无数据替代标准）；(3) Gate G9 新增影响评估检查项；退出条件新增影响评估完成 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-28 | 2026-04-28 | 2026-04-28 | G8 | (1) release 子工作流有影响评估步骤（5 项活动含 A/B 测试+替代判定数据）；(2) release-checklist 有数据验证步骤和指标对比模板；(3) 无数据时有 5 种替代判定标准（基础设施/安全/内部工具/小项目/底线） | EVD-119 | 字节的方法论对 AI 编程项目特别适用——AI agent 生成的代码质量必须用数据验证，不能靠"看起来不错" | 这也是 AUDIT-021（子工作流内容深度补强）的 release 阶段具体实施方案 | 与 AUDIT-036（现代发布实践）互补——AUDIT-033 侧重验证方法，AUDIT-036 侧重发布机制 |
| AUDIT-034 | 维护 | P2: 华为蓝军机制在单 agent 场景下的适配方案 | 华为蓝军机制要求独立团队扮演对立面挑战方案。architecture/sub-workflow.md 和 tech-review-checklist.md 有"蓝军挑战"步骤，但单 agent 无法同时担任红军和蓝军——真正的蓝军需要独立视角。当前蓝军变成了"agent 自我质疑"，效果大打折扣 | 第三轮审计企业实践 华为 | (1) 定义单 agent 蓝军的最低可行方案：要求 agent 切换分析框架（如从"功能视角"切换到"失败模式视角"）、列出至少 3 个"如果我是攻击者/竞争对手/最愤怒的用户"的场景；(2) 多 agent 场景下：主 agent spawn 独立子 agent 作为蓝军（禁止共享分析上下文）；(3) 蓝军挑战的输出格式标准化：攻击向量 + 影响评估 + 缓解建议 | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-14 | 2026-05-22 | | G8 | (1) 单 agent 蓝军有结构化的"视角切换"协议；(2) 多 agent 场景下蓝军是独立 spawn；(3) 蓝军输出有标准格式 | 待补 | 单 agent 蓝军永远达不到真正独立的水平——但结构化的视角切换比"agent自己质疑自己"强 | 先在 tech-review-checklist.md 中落地单 agent 方案，再扩展到其他评审场景 | P2——蓝军是增值机制不是基本功能，先做好基本评审再加强对抗性 |
| AUDIT-035 | 维护 | P1: Agent 失败模式文档与应急预案 | 当 agent 不遵守协议时（跳过 Gate、忽略审计、不使用 AskUserQuestion、选择性执行规则），用户没有系统性的故障排除路径。成熟企业（Google SRE）对每个系统都有明确的故障模式和应急预案。当前工作流假设 agent 会遵守协议——没有定义"agent 行为异常时的降级操作" | 第三轮审计类别 AI 特殊性 | (1) 创建 `references/agent-failure-modes.md`：列出已知的 agent 行为异常模式（协议跳过/选择性执行/幻觉式证据/虚假闭环）、每种模式的检测方法、用户的应急动作；(2) CLAUDE.md 新增"故障排除"章节——用户看到异常行为时的第一步检查清单；(3) SKILL.md 新增 fallback 规则：当检测到协议可能未被遵守时，agent 应主动降级到保守模式（所有决策都确认、所有完成都验证） | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-05-06 | 2026-05-14 | 2026-04-26 | G8 | (1) agent-failure-modes.md 存在且覆盖 ≥5 种失败模式（实际 8 种）；(2) 每种模式有检测方法和用户应急动作；(3) CLAUDE.md 有故障排除入口 | EVD-099 | AI agent 不是确定性系统——成熟的工作流必须假设 agent 会出错，而不是假设 agent 会遵守所有规则。Google SRE 的第一课：系统一定会坏，问题是什么时候坏和你准备好了没 | 这是用户信任的基础——如果用户不知道 agent 出错时该怎么办，用户就不会信任这个工作流 | 与 AUDIT-031（M8 外部验证）互补——AUDIT-031 是自动检测，AUDIT-035 是检测失败后的手动应急 |
| AUDIT-036 | 维护 | P2: Release 阶段现代发布实践——金丝雀/feature flag/kill switch | Google/Meta/Amazon 的标准发布实践包括：金丝雀发布（先 1%→10%→50%→100%）、功能标记（feature flag——发布与启用解耦）、kill switch（一键关闭问题功能）、渐进式 rollout。当前 release/sub-workflow.md 只有基础的回滚方案，缺少这些现代实践 | 第三轮审计企业实践 Google/Meta/Amazon | (1) release/sub-workflow.md 新增"发布策略选择"活动：根据风险评估选择 big-bang/金丝雀/蓝绿/渐进式；(2) 新增 feature flag 管理步骤——哪些功能通过 flag 控制、flag 的启用/关闭流程；(3) 新增 kill switch 验证步骤——每个发布必须有可一键执行的 kill switch（回滚脚本/配置开关/流量切换）；(4) release-checklist.md 增加对应的检查项 | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-14 | 2026-05-24 | | G8 | (1) release 子工作流有发布策略选择步骤；(2) feature flag 管理流程已定义；(3) kill switch 是发布检查的必选项 | 待补 | 现代软件公司不做 big-bang release——这个实践的缺失说明 release 子工作流停在 2010 年代 | 策略选择要考虑项目规模——轻量项目可能不需要金丝雀（用户量不够分流），但 kill switch 对所有项目都必须 | P2 内容深度升级——先有基本发布流程（AUDIT-021），再加现代实践 |
| AUDIT-037 | 维护 | P2: 向后兼容性政策与废弃通知机制 | 当目录被删除（MAINT-028 删除 workflows/rules/）、路径重命名或字段更新时，已安装工作流的用户可能遇到加载错误。当前无版本升级指南、无废弃通知期、无兼容性承诺。成熟软件产品（Google Cloud/AWS）都有明确的 deprecation policy——废弃前至少一个版本的通知期 | 第三轮审计类别 架构一致性 | (1) 创建 `VERSIONING.md`：定义语义化版本规则（Major.Minor.Patch）、废弃通知期（至少一个 Minor 版本）、兼容性承诺范围；(2) manifest.md 新增"版本兼容性"章节；(3) 每次 Breaking Change 前在 CHANGELOG 中标注废弃日期和迁移指南 | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-12 | 2026-05-18 | | G8 | (1) VERSIONING.md 存在且定义明确的 semver 规则和废弃期；(2) manifest.md 有兼容性声明；(3) 最近一次 Breaking Change（MAINT-028）有迁移指南 | 待补 | 用户安装了 0.1.0 → 升级到 0.2.0 时加载失败 → 卸载。没有兼容性政策 = 每次升级都是一次赌博 | 当前版本 0.1.0——在 1.0.0 之前可以有 breaking change，但必须文档化 | P2——先有产品再有政策，但不应该等到 1.0 才想这个问题 |
### 第四轮审计驱动任务（AUDIT-039~042）—— Tier 审计跳过根因闭环

以下任务基于 2026-04-26 Tier 0-C 审计被跳过的根因分析。分析发现两类问题叠加导致审计可被跳过：(1) 工作流协议漏洞——"每个 Tier 完成后执行审计"规则仅存在于 plan-tracker.md 项目特定说明中，未烘焙到 SKILL.md 的 MUST 规则体系；(2) 用户真实使用场景漏洞——插件缓存过时（落后 6 个 commits），版本号冻结在 0.1.0，无版本升级/不匹配检测/用户通知机制。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AUDIT-039 | 维护 | P0: Tier 审计协议强制化——从 plan-tracker 升级到 SKILL.md MUST 规则 | "每个 Tier 完成后执行审计"规则仅存在于 plan-tracker.md（项目特定执行说明），未进入 SKILL.md 的 MUST 规则体系。agent 加载 SKILL.md 后看到的审计触发条件是"Gate 通过前/阶段完成/P0 完成"——没有 Tier 完成。这是 Tier 0-C 审计被跳过的直接原因 | 根因分析报告（类别 1：工作流协议漏洞） | (1) SKILL.md M2.1 audit-framework.md 行新增"Tier 完成"触发条件；(2) audit-framework.md D1/D3/D4 维度触发时机新增"Tier 完成时（按 DEC-052 分层推进模型）；(3) stage-gates.md Gate 执行原则 #7 扩展为覆盖 Gate + Tier 边界 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-26 | 2026-04-26 | 2026-04-26 | G8 | (1) agent 加载 SKILL.md 后能在审计触发条件中看到"Tier 完成"；(2) audit-framework.md 维度表明确 Tier 完成时的审计维度；(3) verify_workflow.py PASSED | EVD-105 | 项目特定规则（plan-tracker）不被 agent 视为强制性协议——只有 SKILL.md 中的 MUST 规则才会触发"违反=执行失败" | 立即修复——这个问题正在影响当前会话的执行质量（M7.3 实时闭环） | P0：直接导致审计被跳过的根因 |
| AUDIT-040 | 维护 | P1: Tier 审计脚本检测——check-governance 新增 Tier 完成审计检查 | verify_workflow.py 中"Tier"概念完全不存在（grep 返回零结果）。check-governance 5 项检查（证据完整性/风险过期/Gate一致性/证据质量/协议合规）全部不涉及 Tier。Gate 有 gate-check 自动判定（B级自动化）、证据有完整性检查、协议合规有 DRI 检测——但 Tier 审计没有任何自动化检查 | 根因分析报告（类别 1：结构性执行缺口） | (1) check-governance 新增 Check 6：Tier 审计完整性——解析 plan-tracker 中 DEC-052 分层推进模型的 Tier 定义，检测"Tier N 的所有任务已完成但无对应审计证据"；(2) 审计证据匹配规则：Tier 完成审计的证据条目任务ID 格式为 "TIER-X-Y-AUDIT"（如 TIER-0-C-AUDIT）；(3) verify_workflow.py PASSED | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-26 | 2026-04-28 | 2026-04-26 | G8 | (1) Tier 0-C 任务全部完成后运行 check-governance 能检测到"缺少审计证据"；(2) 补审计证据后检查通过；(3) 检测逻辑基于 plan-tracker 的 Tier 定义自动适配 | EVD-107 | Tier 是 DEC-052 分层推进模型的核心组织单位，但脚本完全不知道 Tier 概念——Tier 审计是否执行了全靠 agent 记忆 | 先检测"当前已完成 Tier 的审计"，再考虑历史 Tier 的回溯检查 | P1：脚本强制执行——B 级自动化防止复发 |
| AUDIT-041 | 维护 | P1: 版本升级机制 + 插件版本不匹配检测——VERSIONING.md + CHANGELOG.md + bump to 0.2.0 | 5 个文件一致声明 0.1.0——经过 42 行 SKILL.md 变更、6 个新文件、M3.1 DRI/M8.1 双重机制/Gate 自动判定等重大变更后版本号从未升级。无 VERSIONING.md、无 CHANGELOG.md、无版本升级触发条件。用户安装的插件缓存 commit d4af922 落后当前 HEAD 6 个 commits——关键规则（DRI/M8.1/agent-failure-modes）在缓存中不存在 | 根因分析报告（类别 2：版本陈旧） | (1) 创建 `VERSIONING.md`：语义化版本规则（Major.Minor.Patch）+ 版本升级触发条件（MUST 规则新增/变更→MINOR，Breaking Change→MAJOR，修复→PATCH）；(2) 创建 `CHANGELOG.md`：记录 0.1.0→0.2.0 的所有变更；(3) 统一 bump 所有版本声明文件至 0.2.0（plugin.json + marketplace.json + SKILL.md + manifest.md + codex plugin.json 共 5 个文件）；(4) verify_workflow.py 新增版本一致性检查函数 check_version_consistency() 和 snippet 检查 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-26 | 2026-04-26 | 2026-04-26 | G8 | (1) VERSIONING.md 和 CHANGELOG.md 存在；(2) 5 个版本声明文件统一为 0.2.0；(3) 后续 SKILL.md MUST 规则变更时版本号会相应升级；(4) verify_workflow.py PASSED | EVD-106 | 版本号不升级→用户不知道插件有更新→即使规则修了用户也不会 reinstall→工作流改进永远到不了用户 | 立即修复——这个问题导致所有 Tier 0-C 的改进对已安装用户不可见 | P1：原本 AUDIT-037（P2）是通用兼容性政策，本次分析发现版本管理对开发者自身也是致命问题 |
| AUDIT-042 | 维护 | P2: 插件缓存新鲜度自动检测——check-plugin-freshness 子命令 | installed_plugins.json 记录了 gitCommitSha 但从未与源 HEAD 比较。用户不知道插件已过时——没有任何通知机制。即使版本号被 bump 到 0.2.0，用户仍需手动重新安装才能获得新规则 | 根因分析报告（类别 2：无不匹配检测） | (1) verify_workflow.py 新增 `check-plugin-freshness` 子命令：读取 installed_plugins.json 的 gitCommitSha 和 source 路径，与源目录当前 HEAD 比较，报告 installed/current/diff 状态；(2) 在 check-governance 中新增 Check 7：插件版本新鲜度（或集成到现有检查中）；(3) 过期时输出明确的用户操作指引（/plugin marketplace add <path> 或 /reload-plugins） | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-04-28 | 2026-05-04 | | G8 | (1) check-plugin-freshness 子命令可运行；(2) 当前环境运行报告"6 commits behind"；(3) 过期时输出 reload 指引 | 待补 | 没有新鲜度检测 = 用户永远在用安装时的版本 = 所有后续改进对已安装用户不可见 | 先做检测（信息提示），再考虑是否做自动更新 | P2——检测和通知机制，不阻塞基本使用但直接影响改进的传播速度 |
| AUDIT-043 | 维护 | P0: 工作流执行一致性漏洞闭环——M7.4 任务完成协议 | AUDIT-040 完成时发现系统性执行缺陷：4 条 MUST 规则（审计触发/自动commit/执行连续性/AskUserQuestion唯一通道）全部被跳过。这不是单个规则缺失——规则在 MUST 体系中存在但 agent 不执行。与 Tier 0-C 审计跳过的根因同源但层级更高：那次是"规则不在 MUST 体系"，这次是"规则在 MUST 体系但不被执行" | 用户实时反馈（2026-04-26） | (1) SKILL.md 新增 M7.4 任务完成协议——将 evidence→check-governance→audit→commit→continue 绑定为原子不可跳过序列；(2) M8 自检升级——新增 M7.4 检查项；(3) M8.1 表格从 5 checks 扩展到 6 checks（含 Tier 审计完整性）；(4) audit-framework.md D1 触发条件具体化——新增 governance-critical 文件清单（11 个），修改这些文件的任务完成时 MUST 触发审计（不论任务优先级）；(5) version bump 0.2.0→0.3.0（MINOR：新增 MUST 规则）；(6) CHANGELOG.md 更新 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-26 | 2026-04-26 | 2026-04-26 | G8 | (1) M7.4 在 SKILL.md 中作为 MUST 规则存在；(2) M8 自检覆盖 M7.4；(3) audit-framework.md D1 触发条件包含 governance-critical 文件清单；(4) verify_workflow.py PASSED；(5) 版本 bump 到 0.3.0 | EVD-108 | 工作流承诺的行为与实际执行之间的差距是产品可信度的致命问题——用户装了一个声称"自动看护"的插件但实际 agent 跳过规则时没有任何机制阻止 | 立即闭环——从发现问题到修复到 commit 全程按 M7.4 协议执行，用自身验证自身 | P0：解决"规则存在但 agent 不执行"的系统性执行一致性漏洞。修复后用户需 /reload-plugins 获取 0.3.0 |
| AUDIT-045 | 维护 | P0: 风险 escalation 强制执行——check-governance 新增 Check 8：Risk Escalation Deadline | RISK-021/022/023 escalation 截止日期均为 2026-04-25（已过），状态仍为"打开"。risk-log 定义了 Owner + 截止日期 + 缓解动作，但日期过了什么都没发生。check-governance Check 2 只检测 >7 天未更新（staleness），不检测 escalation deadline。风险升级机制存在于模板定义中但无自动执行——与 M7.4 修复前同一模式："承诺了但不执行" | 深度审计（2026-04-26）| (1) verify_workflow.py 新增 `check_risk_escalation()` 函数——解析 risk-log 中"打开"状态的风险，比较 escalation 截止日期与当前日期，过期→WARN；(2) check-governance 新增 Check 8：Risk Escalation Deadline；(3) SKILL.md M7.3 补充：风险 escalation 到期 MUST 升级；(4) verify PASSED | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-26 | 2026-04-26 | 2026-04-26 | G8 | (1) Check 8 检测到 RISK-021/022/023 过期→WARN；(2) 每个过期风险有明确升级动作 | EVD-111 | 风险 escalation 无强制力=风险管理是纸面承诺。与 M7.4/M7.5 同类的"规则存在但无强制力"漏洞 | 先检测→再强制升级→最后考虑自动升级 | P0：同类系统性漏洞 |
| AUDIT-046 | 维护 | P0: Gate 自动判定覆盖率 45%→100%——G6-G11 启发式规则补全 | `auto_judge_gate()` 只为 G1-G5 定义了启发式规则。G6-G11 全部返回 NEEDS_HUMAN（0 checks）。产品承诺"B 级自动化 Gate 判定"但过半 Gate 完全无自动化。用户运行 `gate-check G11` 得到空结论——不是"需人工判断"，是"根本没实现" | 深度审计（2026-04-26）| (1) 为 G6-G11 各定义 ≥3 条启发式检查项；(2) `auto_judge_gate()` 扩展覆盖全部 11 个 Gate；(3) verify_workflow.py PASSED | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-26 | 2026-04-27 | 2026-04-27 | G8 | (1) 每个 Gate 的 gate-check 返回 ≥3 条检查项；(2) gate-check G11 返回 4/4 PASS | EVD-112 | 产品核心卖点缺失 55%——不是增强是补缺 | G6-G11 检查项可基于 check-governance 数据定义 | P0：产品核心能力不完整 |
| AUDIT-047 | 维护 | P1: Evidence 范围编号规范化——消除 evidence-log 与 plan-tracker 数据模型不匹配 | evidence-log 中 4 条证据用范围标记（AUDIT-015~020、AUDIT-021~027、AUDIT-029~038），但 plan-tracker 每个任务是独立 ID。Check 3 把这些有效证据标记为"orphan evidence"——证据存在但无法通过 task ID 匹配。证据追溯链断裂 | 深度审计（2026-04-26）| (1) parse_evidence_task_ids() 支持解析范围标记（"AUDIT-015~020" → 展开为 6 个 ID）；或拆分范围条目为独立条目；(2) Check 3 orphan evidence 清零 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-28 | 2026-04-28 | 2026-04-28 | G8 | (1) range-expand 正确展开 AUDIT-015~020→6 个独立 ID；(2) Check 1 PASSED（77/77 已完成任务有证据）；(3) Check 3 orphan evidence 消除所有范围标记误报；(4) verify_workflow.py PASSED | EVD-117 | 证据链断裂=追溯性承诺落空 | 解析器支持范围展开 + 逗号分隔 ID | P1：数据完整性 |
| AUDIT-048 | 维护 | P1: 任务/风险 deadline 自动升级机制——check-governance 新增 Check 9 | MAINT-013/014 计划完成 2026-04-25，状态均为"未开始"。plan-tracker 有"计划完成"列但过期任务无自动检测。与 AUDIT-045 同源：deadline 字段存在但无自动检测和升级 | 深度审计（2026-04-26）| (1) verify_workflow.py 新增 `check_task_deadline()` ——解析 plan-tracker 中未完成任务，比较计划完成日期与当前日期，过期→WARN；(2) check-governance 新增 Check 9：Task Deadline Enforcement | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-26 | 2026-04-27 | 2026-04-26 | G8 | check-governance 检测到 MAINT-013/014/MAINT-002 deadline 过期→WARN | EVD-111 | 与 AUDIT-045 同一漏洞模式——deadline 过了和没设没区别 | 与 AUDIT-045 合并实现为"Deadline Enforcement"脚本检测 | P1：与 AUDIT-045 合并实现 |
| AUDIT-049 | 维护 | P2: D5 易用性审计首次执行——验证 audit-framework 6 维度全覆盖 | audit-framework 要求 D5 在"外部验证时（强制）"执行。evidence-log 中无任何 D5 审计记录。6 个审计维度只有 D1/D3/D4/D6 被实际触发过 | 深度审计（2026-04-26）| (1) 对当前工作流产品执行首次 D5 审计：安装→初始化→首次使用步骤数、错误消息可操作性、隐性知识依赖；(2) 产出 D5 审计报告→写入 evidence-log | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-04-28 | 2026-05-02 | | G8 | evidence-log 中有 D5 审计条目 | 待补 | 审计框架承诺 6 维度实际只执行了 4 个——与 Gate 只覆盖 5/11 同类 | 在 AUDIT-003 外部验证时同步执行 D5 | P2：流程完整性 |
| AUDIT-050 | 维护 | P2: M8 自检外部验证覆盖率扩展——补充 M2/M5/M7 行为层检测 | M8 的 7 个自检项中 Check 1-7 覆盖了结构层检测，但 M2 pre-loading/M5 AskUserQuestion/M7 执行连续性的遵守情况完全无外部脚本检测。M8.1 双重机制的覆盖范围只有结构层没有行为层 | 深度审计（2026-04-26）| (1) 分析 M2/M5/M7 可脚本检测的部分；(2) 对可检测项实现脚本检查；(3) 对不可检测项标注"NEEDS_HUMAN"；(4) 更新 M8.1 表格增加"检测方式"列 | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-04 | 2026-05-12 | | G8 | (1) M8.1 表格新增"检测方式"列；(2) 至少新增 1 个可脚本检测的行为层检查 | 待补 | 行为层检测本质困难但至少应标注哪些是脚本强制、哪些依赖 agent 自觉——当前 M8.1 暗示全部 7 checks 同等可信 | 先做分类标注（坦诚），再做可检测实现 | P2：防护网透明性 |

| AUDIT-044 | 维护 | P0: Pre-Task Protocol——修改文件前 MUST 先入账 plan-tracker | AUDIT-043 的修复（M7.4）在入账之前就动手了——8 个文件被修改、5 个版本声明被 bump，但 plan-tracker 里没有对应任务。事后才补的 AUDIT-043。agent 可以在不入账的情况下直接修改文件——工作流没有"任务启动门禁"。这违反了 CLAUDE.md bootstrap "这个任务在计划跟踪表里吗？不在就先入账"的规则——但该规则无强制力 | 用户实时反馈（2026-04-26）+ AUDIT-043 commit 4556685（无 task ID 的 commit） | (1) SKILL.md 新增 M7.5 Pre-Task Protocol——修改文件前 MUST 验证任务在 plan-tracker 中存在，不在则先入账（创建 task ID + 填必填字段）；(2) SKILL.md M7.4 步骤 4 commit 格式强化——commit message MUST 包含 task ID（如 "AUDIT-044: description"）；(3) verify_workflow.py 新增 check_commit_task_references()——检测最近 N 个 commit message 是否引用 plan-tracker 中存在的 task ID，无引用→WARN；(4) check-governance 新增 Check 7：Commit-Task Traceability（commit 可追溯性）；(5) verify_workflow.py PASSED | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-26 | 2026-04-26 | 2026-04-26 | G8 | (1) M7.5 在 SKILL.md 中作为 MUST 规则存在；(2) commit message 格式规范生效；(3) check-governance Check 7 检测到无 task ID 的 commit→WARN；(4) verify_workflow.py PASSED | EVD-109 | 无任务启动门禁=项目会被带进垃圾堆——每次 agent 的"顺手修改"如果不入账，一周后没人知道改了什么、为什么改、谁批准的 | 先入账再动手——AUDIT-044 是第一个实践 M7.5 的任务：先在 plan-tracker 创建条目，再开始修改文件 | P0：工作流"全程可追溯"承诺的基础——如果修改可以不入账，所有 Gate/证据/审计都是空中楼阁 |

| AUDIT-038 | 维护 | P2: 子工作流独立使用时目标锚定的强制机制 | main-workflow.md 和每个子工作流都有"独立使用时的目标锚定"章节：要求 agent 先读 plan-tracker → 确认量化成功标准 → 偏离检查 → 质量底线检查。但 agent 直接加载单个子工作流时（跳过 main-workflow.md），这些规则是否被遵守完全取决于 agent 是否自行发现了 main-workflow.md 中的跨层调用协议 | 第三轮审计类别 AI 特殊性 | (1) 每个子工作流的"独立使用时的目标锚定"章节从"引用 main-workflow.md"改为"内嵌锚定步骤"（自包含——不依赖其他文件被加载）；(2) 锚定步骤包含具体的检查项（不是"请确认目标"——是"读取 plan-tracker 的 ## 项目配置 节，确认当前阶段和项目目标"）；(3) 锚定失败时的降级行为：如果 plan-tracker 不可用，明确告知用户"独立使用模式下目标锚定不可用" | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-12 | 2026-05-20 | | G8 | (1) 每个子工作流的锚定章节是自包含的；(2) 锚定步骤有具体的文件路径和章节引用；(3) 锚定失败时有明确的降级行为 | 待补 | 独立使用是产品的重要卖点——如果用户独立使用子工作流时失去了目标锚定，"不偏离目标"这个基础承诺就失效了 | 先修改 2 个最常用的子工作流（development + release）的自包含锚定，验证模式后批量复制 | P2 体验改进——需要大量子工作流逐一修改，但不阻塞基本使用 |
