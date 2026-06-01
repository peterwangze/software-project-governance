# 竞品对标与官方收录演进规划

> 日期：2026-06-01
> 触发：用户要求对标 GitHub 高星 agentic AI coding plugin/skill 竞品，尤其 Superpowers，推演当前项目优势、劣势、缺陷和后续版本承载。

## 结论

当前项目不应定位为“另一个 Superpowers”。Superpowers 的优势是轻量、易懂、跨平台、官方入口和 TDD/plan/subagent 工作流；本项目的优势是长期项目治理可信层：目标不偏离、事实依据、证据链、风险/决策/版本/Gate、真实 E2E、降级声明、质量预算和发布门禁。

战略定位调整为：

> Software Project Governance is the delivery trust layer for AI coding agents: it keeps goals, evidence, risks, quality gates, and releases verifiable across Claude, Codex, Gemini, OpenCode, and other agent runtimes.

换句话说，本项目应成为 AI coding agent 的“项目治理与交付可信层”，可以独立使用，也可以和 Superpowers、Agent Skills、各类 agent marketplace 共存。

## 外部竞品事实

事实采集以 GitHub API、官方插件仓库和项目 README 为准；数据时间为 2026-06-01。

| 项目 | 采用信号 | 关键能力 |
| --- | ---: | --- |
| Superpowers (`obra/superpowers`) | GitHub API 显示约 214k stars；OpenAI plugins 仓库含 `plugins/superpowers`；README 声明支持 Claude Code、Codex CLI/App、Factory Droid、Gemini CLI、OpenCode、Cursor、GitHub Copilot CLI | 14 个核心 skills：brainstorming、writing-plans、TDD、systematic-debugging、subagent-driven-development、code review、finish branch 等 |
| `wshobson/agents` | GitHub API 显示约 36k stars | 多 harness marketplace：83 plugins、191 agents、155 skills、102 commands；从单一 Markdown 源生成多平台原生资产 |
| `addyosmani/agent-skills` | GitHub API 显示约 47k stars | 23 个生产级工程 skills，生命周期命令清晰，强调 process、verification、progressive disclosure |
| `anthropics/claude-plugins-official` | GitHub API 显示约 29k stars | 官方 Claude plugin 目录；强调高质量、安全标准和标准插件结构 |
| 当前项目 | GitHub API 显示 0 stars；本地仓库已有 26 个 SKILL、15 个 agents、8 个 commands、4 个 adapters、23 个工具索引、360 个验证测试 | 治理可信度强，但市场化表达、官方级 manifest、跨平台一键入口、外部采用信号不足 |

参考链接：

- https://github.com/obra/superpowers
- https://github.com/openai/plugins/tree/main/plugins/superpowers
- https://github.com/openai/plugins
- https://github.com/anthropics/claude-plugins-official
- https://github.com/wshobson/agents
- https://github.com/addyosmani/agent-skills

## 当前项目优势

1. 可验证治理强：已有 `check-governance`、结构化事实、Agent Team 降级模式、真实 runtime E2E harness、质量预算、产品成功契约、Git hooks、发布门禁和 hot fact-source consistency。
2. 长期项目视角强：竞品多聚焦单次 coding workflow，本项目覆盖决策、风险、证据、版本、Gate、外部验证和维护。
3. 防过度声明能力强：已明确区分 real-agent E2E、target cwd E2E、source proxy、blocked/degraded，不把近似信号包装成完整适配。
4. 对官方收录有潜在契合点：官方目录更重视结构清晰、安全边界、安装后行为可解释；本项目可以用“delivery trust layer”形成差异化。

## 劣势和缺陷

1. 市场化表达弱：README 仍偏“项目管理/治理”，普通用户不容易立刻感到“装上就能提升 AI coding 交付质量”。
2. 官方入口准备不足：当前 `.codex-plugin/plugin.json` 和 `.claude-plugin/plugin.json` 仍是极简 manifest，缺少 Codex 官方插件常见的 `skills`、`interface`、logo、defaultPrompt、homepage、repository、license、privacy/terms 等字段。
3. 跨平台闭环不够漂亮：Claude/opencode 证据较强，Codex/Gemini 仍有 degraded/blocked 口径；事实记录正确，但不利于“主流 agent 一键可用”的市场承诺。
4. 上下文负担偏高：虽然 0.40.0 已收敛 AI-facing 文本，但相比 Superpowers / Agent Skills 的 progressive disclosure，本项目仍需要拆成轻量核心和可选治理模块。
5. 外部采用信号缺失：当前仓库 stars/forks 为 0，未进入 OpenAI/Anthropic 官方目录，缺少外部项目验证样本和官方提交包。

## 差异化路线

不与 Superpowers 在“更多 coding skills”上硬拼。更合适的关系是：

- Superpowers / Agent Skills：提升 agent 如何计划、TDD、debug、review、执行分支。
- Software Project Governance：验证这些过程是否真的服务目标、是否有事实依据、是否有可运行验收、是否有风险/决策/版本/发布闭环。

产品话术从“项目管理工作流”收敛为“AI coding delivery trust layer”。这保留项目已有优势，也避开竞品已经占据的轻量技能包心智。

## 版本承载路线

| 版本 | 目标 | 承载事项 |
| --- | --- | --- |
| `0.40.1` | CI hotfix patch 正式发布 | 将 FIX-095 已完成的 GitHub CI clean checkout 修复做版本 bump、CHANGELOG、tag/push |
| `0.41.0` | Official Marketplace Readiness | 补齐 Codex/Claude 官方级 manifest、assets、default prompts、英文 README、隐私/安全说明、官方提交 checklist |
| `0.42.0` | 5 分钟成功路径 | 一键初始化、lite/standard/strict preset、最小 demo 项目、首次运行只展示一个清晰 happy path |
| `0.43.0` | Cross-Harness E2E Closure | Claude/Codex/Gemini/OpenCode 扩展到 Cursor/Copilot；每个平台真实 E2E pass/blocked 矩阵公开化 |
| `0.44.0` | Composable Governance Packs | 拆成 `governance-core`、`quality-gates`、`release-governance`、`agent-team`、`enterprise` 等可选包，降低安装和上下文负担 |
| `0.45.0` | Governance Eval & Benchmark | 建立类似 plugin-eval 的评测：弱 LLM 遵从率、目标偏离率、证据完整率、交付质量通过率、外部项目样本 |
| `0.46.0` | Ecosystem & Official Submission | 发布官网式文档、示例、对比页、迁移指南；向 OpenAI/Anthropic 官方目录提交 |
| `1.0.0` | Production-ready / 官方候选 | 只在外部项目验证、主流入口闭环、官方提交包齐备后发布 |

## 成功标准

- 用户 5 分钟内完成初始化并看到一个清晰的治理价值闭环。
- 官方级 manifest 和视觉/隐私/安全素材齐备，能提交 OpenAI/Anthropic 官方目录。
- 至少 2 个外部项目完成真实治理闭环验证。
- 主流 agent adapter 不夸大能力；每个平台具备 pass/blocked/degraded 的公开矩阵。
- README 首屏表达从“管理流程”转成“让 AI coding 交付可信”。
- 能解释与 Superpowers 的互补关系：不替代 coding workflow，而是治理其交付可信度。
