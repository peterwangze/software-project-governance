# 工作流工具目录

本文件是工作流第三层"基础工具/脚本层"的统一索引。所有工具独立于阶段，可被多个子工作流共用，也可被用户直接调用。

## 工具总览

| 工具 ID | 名称 | 类型 | 位置 | 触发场景 | 所属子工作流 | 可独立使用 |
|---------|------|------|------|---------|------------|----------|
| TOOL-001 | 需求澄清 checklist | checklist | `skills/requirement-clarification/SKILL.md` | 需求模糊需要结构化澄清时 | 立项（initiation） | 是 |
| TOOL-002 | 技术评审 checklist | checklist | `skills/tech-review/SKILL.md` | 架构/技术方案需要评审时 | 架构设计（architecture） | 是 |
| TOOL-003 | Code Review 规范 | standard | `skills/code-review/SKILL.md` | 代码变更需要审查时 | 开发（development） | 是 |
| TOOL-004 | 发布 checklist | checklist | `skills/release-checklist/SKILL.md` | 版本发布前做最终检查时 | 版本发布（release） | 是 |
| TOOL-005 | 回顾会议模板 | template | `skills/retro-meeting/SKILL.md` | 阶段结束或项目复盘时 | 维护（maintenance） | 是 |
| TOOL-006 | 校验脚本 | script | `infra/verify_workflow.py` | 验证工作流资产完整性时 | 全部阶段 | 是 |
| TOOL-007 | governance-update 命令 | command | `commands/governance-update.md` | 更新 平台原生入口文件 bootstrap 到最新版本（不触碰 .governance/） | 维护（maintenance） | 是 |
| TOOL-008 | 发布就绪检查 | script | `infra/verify_workflow.py check-release` | 版本发布前聚合门禁检查时 | 发布（release） | 是 |
| TOOL-009 | 主流 agent adapter 检查 | script | `infra/verify_workflow.py check-agent-adapters [--runtime]` | 验证 Claude/Codex/Gemini/opencode adapter 状态与 runtime probe 时 | 架构/发布/维护 | 是 |
| TOOL-010 | 治理归档工具 | script | `infra/archive.py` | 治理数据膨胀、版本发布后持续归档、归档迁移时 | 维护/发布 | 是 |
| TOOL-011 | 清理工具 | script | `infra/cleanup.py` | 插件升级后清理过期文件，或做 cleanup dry-run 时 | 维护 | 是 |
| TOOL-012 | Git hooks 防护网 | hook | `infra/hooks/` | commit 前后执行治理门禁、证据检查、锁清理时 | 全部阶段 | 否（由 Git 自动触发） |
| TOOL-013 | 交叉引用检查 | script | `infra/verify_workflow.py check-cross-references` | 路径迁移、文档/skill/agent 引用变更后 | 架构/维护 | 是 |
| TOOL-014 | 真实 agent runtime E2E harness | script | `infra/verify_workflow.py agent-runtime-e2e` | Claude/Codex/Gemini/opencode 真实运行环境入口验证时 | 测试/发布/维护 | 是 |
| TOOL-015 | AI execution packet 生成与检查 | script | `infra/verify_workflow.py execution-packet` + `check-governance` Check 18c | 活跃 P0/P1 任务开始前生成短上下文执行包，提交前验证短包存在且字段有效 | 全部阶段 | 是 |
| TOOL-016 | Projection sync guard | script | `infra/verify_workflow.py check-projection-sync` + `check-governance` Check 28b | workflow source、target fixture、native entry、plugin manifest 变更后 | 测试/发布/维护 | 是 |
| TOOL-017 | Hot fact-source consistency guard | script | `infra/verify_workflow.py check-hot-fact-source` + `check-governance` Check 28c | plan-tracker 热区项目配置、总览、活跃事项、路线图、依赖链和需求矩阵变更后 | 发布/维护 | 是 |
| TOOL-018 | Product Success Contract guard | script | `infra/verify_workflow.py check-product-success-contracts` + `check-governance` Check 18d | P0/P1 任务启动和关闭前检查产品成功契约 | 开发/测试/发布/维护 | 是 |
| TOOL-019 | Executable Acceptance Contract guard | script | `infra/verify_workflow.py check-acceptance-contracts` + `check-governance` Check 18e | P0/P1 任务启动和关闭前检查可运行验收契约 | 开发/测试/发布/维护 | 是 |
| TOOL-020 | Quality Budget Gate | script | `infra/verify_workflow.py check-quality-budget` + `check-governance` Check 18f | P0/P1 任务启动和关闭前检查六维质量预算 | 开发/测试/CI/CD/发布/维护 | 是 |
| TOOL-021 | Vertical Slice Delivery Packet guard | script | `infra/verify_workflow.py check-vertical-slices` + `check-governance` Check 18g | P0/P1 任务启动和关闭前检查用户可见切片、demo、scope guard 和 rollback | 开发/测试/发布/维护 | 是 |
| TOOL-022 | Weak-LLM Deterministic Scaffold generator/check | script + template | `infra/verify_workflow.py generate-deterministic-scaffold` + `check-deterministic-scaffolds` + `check-governance` Check 18h | 弱 LLM 或新项目启动时生成 PRD-lite、验收、质量预算、垂直切片和 demo checklist 脚手架 | 立项/开发/测试/发布/维护 | 是 |
| TOOL-023 | User Interruption Policy v2 guard | script + template | `infra/verify_workflow.py check-interruption-policy` + `check-governance` Check 18i | P0/P1 任务启动和关闭前检查 critical-only 打断边界、assumption record 和打断预算 | 立项/开发/测试/发布/维护 | 是 |
| TOOL-024 | Runtime Readiness Matrix guard | script + doc | `infra/verify_workflow.py check-runtime-readiness-matrix` + `check-governance` Check 28d | adapter runtime facts、公开 readiness matrix 或 release gate 变更后 | 测试/发布/维护 | 是 |
| TOOL-025 | First-Session Measurement guard | script + doc | `infra/verify_workflow.py check-first-session-measurement` + `check-governance` Check 28e | local demo / external pilot 证据或 release note boundary 变更后 | 测试/发布/维护 | 是 |
| TOOL-026 | Governance Pack Registry guard | script + registry | `infra/verify_workflow.py check-governance-packs` + `check-governance` Check 28f | composable governance pack registry、pack 文件/检查归属或 no-overclaim boundary 变更后 | 架构/测试/发布/维护 | 是 |

## 工具详情

### TOOL-001：需求澄清 checklist

- **文件**：`skills/requirement-clarification/SKILL.md`
- **子命令**：通过 Claude Code slash command `/requirement-clarification` 调用，或直接在上下文中加载
- **输入**：用户对需求的原始描述
- **输出**：经过 5 问法 + IN/OUT 边界分析后的结构化需求文档
- **触发条件**：用户表述模糊、需求边界不清、缺乏量化验收标准
- **依赖**：无
- **被以下子工作流使用**：立项（initiation）

### TOOL-002：技术评审 checklist

- **文件**：`skills/tech-review/SKILL.md`
- **子命令**：通过 Claude Code slash command `/tech-review-checklist` 调用，或直接在上下文中加载
- **输入**：待评审的技术方案或架构设计文档
- **输出**：结构化的评审结论（通过/有条件通过/需修改）+ 具体评审意见
- **触发条件**：架构设计完成、技术选型确定、重大技术决策做出后
- **依赖**：无
- **被以下子工作流使用**：架构设计（architecture）、技术选型（selection）

### TOOL-003：Code Review 规范

- **文件**：`skills/code-review/SKILL.md`
- **子命令**：通过 Claude Code slash command `/code-review-standard` 调用，或直接在上下文中加载
- **输入**：待审查的代码变更（diff 或 PR）
- **输出**：分级审查结论（P0 阻塞 / P1 关键 / P2 建议）+ 逐条审查意见
- **触发条件**：代码变更提交 Review、合并前检查
- **依赖**：无
- **被以下子工作流使用**：开发（development）

### TOOL-004：发布 checklist

- **文件**：`skills/release-checklist/SKILL.md`
- **子命令**：通过 Claude Code slash command `/release-checklist` 调用，或直接在上下文中加载
- **输入**：当前版本的变更清单和测试报告
- **输出**：逐项检查结论（通过/未通过/不适用）+ 发布建议
- **触发条件**：版本发布前
- **依赖**：测试报告（子工作流 testing）
- **被以下子工作流使用**：版本发布（release）

### TOOL-005：回顾会议模板

- **文件**：`skills/retro-meeting/SKILL.md`
- **子命令**：通过 Claude Code slash command `/retro-meeting` 调用，或直接在上下文中加载
- **输入**：本阶段/本轮的产出物和治理记录
- **输出**：结构化的回顾结论（目标回顾、结果评估、根因分析、改进计划）
- **触发条件**：阶段完成、项目里程碑、定期回顾
- **依赖**：本阶段的 evidence-log、decision-log、risk-log
- **被以下子工作流使用**：维护（maintenance），也可被任意阶段结束时调用

### TOOL-006：校验脚本

- **文件**：`infra/verify_workflow.py`
- **子命令**：`verify`（全量校验）、`status`（治理状态摘要）、`gate <G1-G11>`（Gate 检查）、`gates`（全部 Gate 状态）、`stage <stage-id>`（阶段状态）、`stages`（全部阶段状态）、`check-governance --fail-on-issues`（治理健康检查）、`e2e-check`（E2E proxy + fixture 分层检查）、`check-version-consistency`、`check-manifest-consistency`、`check-deterministic-scaffolds`、`check-interruption-policy`、`generate-deterministic-scaffold`、`check-locks`、`check-archive-integrity`
- **输入**：无（自动读取项目文件）
- **输出**：校验结果（PASSED/FAILED）+ 治理状态摘要
- **触发条件**：工作流资产变更后、Gate 检查时、定期巡检
- **依赖**：项目需已完成 `governance-init`
- **被以下子工作流使用**：全部阶段

### TOOL-007：governance-update 命令

- **文件**：`commands/governance-update.md`
- **子命令**：`/governance update`
- **输入**：当前仓库中的平台原生入口文件和工作流版本
- **输出**：升级后的 bootstrap 段落和升级摘要
- **触发条件**：插件更新后、bootstrap 模板变化后、用户显式要求更新入口文件
- **依赖**：`commands/governance-init.md` 中的 canonical bootstrap 模板
- **被以下子工作流使用**：维护（maintenance）

### TOOL-008：发布就绪检查

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-release [--version X.Y.Z] [--require-changelog] [--runtime-adapters] [--skip-execution-gates]`
- **输入**：可选版本号；可选要求 CHANGELOG 已包含该版本；可选本机 agent runtime probe；默认执行发布门禁命令
- **输出**：发布就绪检查结果（PASSED/FAILED）+ 版本一致性、release fact source、agent adapter、交叉引用、归档完整性、`verify`、`check-governance --fail-on-issues`、`e2e-check`、unittest 分项结果
- **触发条件**：`stage-release` 执行发布 checklist 时；0.35.0 及后续版本发布前
- **依赖**：`check_version_consistency()`、`check_release_readiness_fact_source()`、`check_agent_adapter_contract()`、`check_cross_references()`、`check_archive_integrity()`、`verify_workflow.py verify`、`check-governance --fail-on-issues`、`e2e-check`、`python -m unittest skills/software-project-governance/infra/tests/test_verify_workflow.py -v`
- **降级口径**：`--skip-execution-gates` 仅用于诊断静态聚合，不作为正式发布 checklist 通过证据。
- **被以下子工作流使用**：版本发布（release）

### TOOL-009：主流 agent adapter 检查

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-agent-adapters [--runtime]`
- **输入**：adapter manifest/README/launcher；`--runtime` 时读取本机 PATH 中的 agent CLI
- **输出**：Claude/Codex/Gemini/opencode 的 STATIC/PASS/UNSUPPORTED/FAIL 状态
- **触发条件**：适配层变更后、发布前检查、主流 agent runtime 证据刷新时
- **依赖**：`adapters/{claude,codex,gemini,opencode}/adapter-manifest.json`
- **被以下子工作流使用**：架构设计（architecture）、版本发布（release）、维护（maintenance）

### TOOL-010：治理归档工具

- **文件**：`infra/archive.py`
- **子命令**：`migrate --auto [--dry-run]`
- **输入**：`.governance/plan-tracker.md`、`.governance/evidence-log.md`、`.governance/archive/index.md`
- **输出**：归档迁移摘要、归档后的 task/evidence 文件、索引更新
- **触发条件**：插件升级归档迁移、版本发布后持续归档、plan-tracker 膨胀到阈值时
- **依赖**：`verify_workflow.py check-archive-integrity`
- **被以下子工作流使用**：版本发布（release）、维护（maintenance）

### TOOL-011：清理工具

- **文件**：`infra/cleanup.py`
- **子命令**：`--dry-run --json`；升级流程中可执行实际清理
- **输入**：`manifest.json` canonical 文件集合与当前工作区文件
- **输出**：清理候选或已清理文件摘要
- **触发条件**：插件升级后、manifest 变化后、需要检查过期文件残留时
- **依赖**：`skills/software-project-governance/core/manifest.json`
- **被以下子工作流使用**：维护（maintenance）

### TOOL-012：Git hooks 防护网

- **文件**：`infra/hooks/prepare-commit-msg`、`infra/hooks/pre-commit`、`infra/hooks/commit-msg`、`infra/hooks/post-commit`
- **触发方式**：Git 自动触发
- **输入**：staged diff、commit message、治理记录、agent locks
- **输出**：阻断型错误或允许型治理提醒；post-commit 锁清理
- **触发条件**：每次 commit
- **依赖**：`.governance/evidence-log.md`、`.governance/plan-tracker.md`、`.governance/agent-locks.json`
- **被以下子工作流使用**：全部阶段

### TOOL-013：交叉引用检查

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-cross-references [--fail-on-issues]`
- **输入**：`skills/software-project-governance/`、`commands/`、`agents/` 下的 Markdown/Python 引用
- **输出**：dangling reference、deprecated path、circular reference 检查结果
- **触发条件**：路径迁移、文档重构、skill/agent/command 引用变更后
- **依赖**：无外部依赖
- **被以下子工作流使用**：架构设计（architecture）、维护（maintenance）

### TOOL-014：真实 agent runtime E2E harness

- **文件**：`infra/verify_workflow.py`
- **子命令**：`agent-runtime-e2e [--target PATH] [--timeout SECONDS] [--agent claude|codex|gemini|opencode]`
- **输入**：`project/e2e-test-project` 或指定 target cwd；本机 PATH 中的 Claude/Codex/Gemini/opencode CLI
- **输出**：每个平台的 `PASS` / `BLOCKED` / `FAIL` 状态、执行命令、cwd、blocked_reason 和截断日志摘要
- **触发条件**：主流 agent 适配状态刷新、发布前真实 runtime 验证、外部环境诊断
- **依赖**：`project/e2e-test-project` 四平台 native entry fixture；对应 agent CLI 与本机认证/模型配置
- **PASS schema**：真实 agent 输出必须包含 `E2E_PLATFORM=<platform>; E2E_AGENT=<workflow role>; E2E_STAGE=<current stage>; E2E_MODE=<trigger x permission>`；platform 必须匹配当前 CLI，workflow role/stage 不得为占位，mode 必须是合法触发模式 × 权限模式
- **判定口径**：`BLOCKED` 表示环境或 agent runtime 配置阻塞，不等于 harness 失败；`FAIL` 表示未分类失败或结构化 PASS schema 不完整，需要修复 harness 或入口适配
- **被以下子工作流使用**：测试（testing）、版本发布（release）、维护（maintenance）

### TOOL-015：AI execution packet 生成与检查

- **文件**：`infra/verify_workflow.py`
- **子命令**：`execution-packet [--write] [--task TASK_ID]`
- **输入**：`.governance/plan-tracker.md` 的 `## 当前活跃事项`
- **输出**：`.governance/execution-packets.json`，包含每个活跃 P0/P1 任务的 `goal`、`allowed_change_scope`、`required_evidence`、`next_commands`、`done_definition`
- **触发条件**：每个 P0/P1 任务启动前；`check-governance` Check 18c 发现缺包或短包无效时
- **依赖**：`check-governance`、`core/templates/execution-packet.md`
- **被以下子工作流使用**：全部阶段，尤其是维护、开发、发布

### TOOL-016：Projection sync guard

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-projection-sync [--fail-on-issues]`
- **输入**：source `skills/**`、`commands/**`、`agents/**`；target fixture `project/e2e-test-project`；`.claude-plugin/plugin.json`、`.codex-plugin/plugin.json`、core manifest 和 target plan-tracker 版本声明
- **输出**：source 版本、镜像文件检查数量、版本声明检查结果、target fixture drift/missing file/native entry marker 缺失问题
- **触发条件**：修改 workflow source、target fixture、native entry、plugin manifest 后；发布前 release readiness 门禁
- **依赖**：`check-governance` Check 28b、`check-release` projection sync detail、`project/e2e-test-project`
- **被以下子工作流使用**：测试（testing）、发布（release）、维护（maintenance）

### TOOL-017：Hot fact-source consistency guard

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-hot-fact-source [--fail-on-issues]`
- **输入**：`.governance/plan-tracker.md` 热区：项目配置、项目总览、当前活跃事项、`1.0.0 依赖链`、版本规划、需求跟踪矩阵
- **输出**：版本阶段叙事、活跃 task 状态、依赖链 blocker、需求矩阵交付状态之间的不一致问题
- **触发条件**：更新当前版本任务状态、路线图、1.0.0 依赖链、需求矩阵或发布前事实源复核时
- **依赖**：`check-governance` Check 28c、`check-release` hot fact source detail
- **被以下子工作流使用**：发布（release）、维护（maintenance）

### TOOL-018：Product Success Contract guard

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-product-success-contracts [--fail-on-issues]`
- **输入**：`.governance/execution-packets.json` 中活跃 P0/P1 任务的 `product_success_contract`
- **输出**：每个活跃任务的用户、JTBD、非目标、成功指标、竞争基线和完成定义完整性检查结果；拒绝占位草案和仅 governance/review/evidence 完成的流程型指标
- **触发条件**：P0/P1 任务启动前、任务关闭前、发布前产品成功门禁复核时
- **依赖**：`check-governance` Check 18d、`core/templates/product-success-contract.md`、`core/templates/execution-packet.md`
- **被以下子工作流使用**：立项（initiation）、开发（development）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-019：Executable Acceptance Contract guard

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-acceptance-contracts [--fail-on-issues]`
- **输入**：`.governance/execution-packets.json` 中活跃 P0/P1 任务的 `acceptance_contract`
- **输出**：每个活跃任务的验收场景、可运行命令、预期输出、最近运行结果和 demo 证据检查结果；拒绝占位草案、不可运行命令和未 PASS 的最近运行结果
- **触发条件**：P0/P1 任务启动前、任务关闭前、发布前验收门禁复核时
- **依赖**：`check-governance` Check 18e、`core/templates/executable-acceptance-contract.md`、`core/templates/execution-packet.md`
- **被以下子工作流使用**：开发（development）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-020：Quality Budget Gate

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-quality-budget [--fail-on-issues]`
- **输入**：`.governance/execution-packets.json` 中活跃 P0/P1 任务的 `quality_budget`
- **输出**：每个活跃任务的 performance、reliability、security、accessibility、ux、maintainability 六维质量预算检查结果；拒绝占位草案、缺维度、失败状态和无理由例外
- **触发条件**：P0/P1 任务启动前、任务关闭前、发布前质量门禁复核时
- **依赖**：`check-governance` Check 18f、`core/templates/quality-budget.md`、`core/templates/execution-packet.md`
- **被以下子工作流使用**：开发（development）、测试（testing）、CI/CD、发布（release）、维护（maintenance）

### TOOL-021：Vertical Slice Delivery Packet guard

- **文件**：`infra/verify_workflow.py`
- **子命令**：`check-vertical-slices [--fail-on-issues]`
- **输入**：`.governance/execution-packets.json` 中活跃 P0/P1 任务的 `vertical_slice`
- **输出**：每个活跃任务的用户可见切片、demo 路径、范围边界、回滚方案、状态和证据检查结果；拒绝占位草案、纯技术层切片、不可演示路径、全仓范围和 review/prose-only 证据
- **触发条件**：P0/P1 任务启动前、任务关闭前、发布前垂直切片门禁复核时
- **依赖**：`check-governance` Check 18g、`core/templates/vertical-slice-delivery-packet.md`、`core/templates/execution-packet.md`
- **被以下子工作流使用**：开发（development）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-022：Weak-LLM Deterministic Scaffold generator/check

- **文件**：`infra/verify_workflow.py` + `core/templates/deterministic-scaffolds/`
- **子命令**：`generate-deterministic-scaffold --type web-app|cli-tool|workflow-plugin [--output PATH]`；`check-deterministic-scaffolds [--fail-on-issues]`
- **输入**：项目类型；scaffold 模板库中的 `index.md`、`web-app.md`、`cli-tool.md`、`workflow-plugin.md`
- **输出**：可直接放入目标项目的 PRD-lite / Product Success Contract / Executable Acceptance / Quality Budget / Vertical Slice / Demo Checklist / Tooling 脚手架；模板完整性检查结果
- **触发条件**：弱 LLM 执行新项目、常见项目类型启动、P0/P1 任务缺产品成功路径、发布前确认 0.39.0 产品成功门禁工具库完整性
- **依赖**：`check-governance` Check 18h、`core/templates/deterministic-scaffolds/index.md`
- **被以下子工作流使用**：立项（initiation）、开发（development）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-023：User Interruption Policy v2 guard

- **文件**：`infra/verify_workflow.py` + `core/templates/user-interruption-policy.md` + `references/interaction-boundary.md`
- **子命令**：`check-interruption-policy [--fail-on-issues]`；alias `check-user-interruption-policy [--fail-on-issues]`
- **输入**：interaction boundary 规则、用户打断策略模板、`.governance/execution-packets.json` 中活跃 P0/P1 任务的 `interruption_policy`
- **输出**：critical-only 策略完整性、产品意图/验收标准/不可逆决策分类 examples、assumption record 五字段和 interruption budget 检查结果
- **触发条件**：P0/P1 任务启动前、任务关闭前、用户反馈打断过多或关键处漏问、发布前 0.39.0 产品成功门禁复核时
- **依赖**：`check-governance` Check 18i、`core/templates/execution-packet.md`
- **被以下子工作流使用**：立项（initiation）、开发（development）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-024：Runtime Readiness Matrix guard

- **文件**：`infra/verify_workflow.py` + `docs/requirements/runtime-readiness-matrix-0.43.0.md`
- **子命令**：`check-runtime-readiness-matrix [--fail-on-issues]`
- **输入**：`adapters/claude|codex|gemini|opencode/adapter-manifest.json`、公开 runtime/readiness matrix 文档
- **输出**：公开矩阵是否覆盖 Claude/Codex/Gemini/opencode/Cursor/Copilot，是否与 adapter manifest 的 PASS/BLOCKED/DEGRADED、version command、blocked reason、workflow closure 和 no-overclaim 边界一致
- **触发条件**：更新 adapter runtime facts、发布 readiness 文档、0.43.0 Cross-Harness E2E Closure 或 release gate 前
- **依赖**：`check-governance` Check 28d、`check-release` runtime readiness matrix detail、`check-agent-adapters --runtime`、`agent-runtime-e2e`
- **被以下子工作流使用**：测试（testing）、发布（release）、维护（maintenance）

### TOOL-025：First-Session Measurement guard

- **文件**：`infra/verify_workflow.py` + `docs/requirements/first-session-measurement-0.43.0.md`
- **子命令**：`check-first-session-measurement [--fail-on-issues]`
- **输入**：first-session measurement evidence 文档中的 `Measurement Status` 表、local demo 命令和 external pilot 状态
- **输出**：local_demo 是否只声明 LOCAL_DEMO_ONLY PASS，external_pilot 是否只使用 PASS/BLOCKED/NOT_MEASURED 且不把 `first-run-demo` local proof 包装成外部 pilot PASS，release note no-overclaim boundary 是否完整
- **触发条件**：更新 5-minute first-session 证据、发布 0.43.0 release notes、外部 pilot 测量状态变化或 release gate 前
- **依赖**：`check-governance` Check 28e、`check-release` first-session measurement detail、`first-run-demo --assert-snapshot`
- **被以下子工作流使用**：测试（testing）、发布（release）、维护（maintenance）

### TOOL-026：Governance Pack Registry guard

- **文件**：`infra/verify_workflow.py` + `core/governance-packs.json`
- **子命令**：`check-governance-packs [--fail-on-issues]`
- **输入**：canonical governance pack registry 中的 pack ID、profile、capability、file reference、check reference、validation command 和 no-overclaim boundary
- **输出**：`governance-core`、`quality-gates`、`release-governance`、`agent-team`、`enterprise` 是否完整；引用文件和引用检查是否存在；是否出现 official approval / marketplace approval / 1.0.0 production-ready 等过度声明
- **触发条件**：新增或调整 composable governance pack、改变文件/检查归属、发布 0.44.0 pack boundary 或 release gate 前
- **依赖**：`check-governance` Check 28f、`core/manifest.json`
- **被以下子工作流使用**：架构设计（architecture）、测试（testing）、发布（release）、维护（maintenance）

### TOOL-027：Governance Context Discovery

- **文件**：`infra/verify_workflow.py` + `/governance` 与 `/governance-status` command contracts
- **子命令**：`governance-context [--fixture <project-root>] [--fail-on-issues]`
- **输入**：`.governance/plan-tracker.md` active rows/version roadmap、`.governance/session-snapshot.md` carry-over/next priorities、`.governance/risk-log.md` open risks、目标项目命令契约文档
- **输出**：fact-backed unfinished work handoff：detected item、source facts、blocker state、next action、auto-continue 和 interrupt boundary；无事实时明确 `not found` 且 `do not invent`
- **触发条件**：`/governance`/status 恢复已有项目、跨会话继续工作、0.44.0 context-aware resume 验收或 release gate 前
- **依赖**：`check-governance` Check 28g、Delivery Trust Snapshot、`first-run-demo --assert-snapshot`
- **被以下子工作流使用**：立项（initiation）、测试（testing）、发布（release）、运营（operations）、维护（maintenance）

### TOOL-028：README Pack Guidance guard

- **文件**：`infra/verify_workflow.py` + `README.md` + `core/governance-packs.json`
- **子命令**：`check-readme-pack-guidance [--fail-on-issues]`
- **输入**：README first-run preset guidance、0.44.0 pack ID、profile vs pack 边界和 no-overclaim wording
- **输出**：README 是否把 `lite`/`standard`/`strict` 映射到 `governance-core`、`quality-gates`、`release-governance`、`agent-team`、`enterprise`，并明确 packs 不替代 profiles、pack enabled 不等于 evidence/review/quality/release/approval/runtime PASS
- **触发条件**：更新 README first-run 文案、调整 pack registry、发布 0.44.0 pack boundary 或 release gate 前
- **依赖**：`check-governance` Check 28h、`check-governance-packs`
- **被以下子工作流使用**：立项（initiation）、测试（testing）、发布（release）、维护（maintenance）

## 工具与子工作流的关系矩阵

| 工具 | 立项 | 调研 | 选型 | 环境 | 架构 | 开发 | 测试 | CI/CD | 发布 | 运营 | 维护 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 需求澄清 | ● | ○ | ○ | | | | | | | | |
| 技术评审 | | | ● | | ● | | | | | | |
| Code Review | | | | | | ● | | | | | |
| 发布检查 | | | | | | | | | ● | | |
| 发布就绪脚本 | | | | | | | | | ● | | ○ |
| Agent adapter 检查 | | | | | ● | | | | ● | | ● |
| 回顾模板 | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ● |
| 校验脚本 | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| 治理归档 | | | | | | | | | ● | | ● |
| 清理工具 | | | | | | | | | | | ● |
| Git hooks | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| 交叉引用检查 | | | | | ● | | | | | | ● |
| 真实 agent runtime E2E | | | | | ○ | | ● | | ● | | ● |
| AI execution packet | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |
| Projection sync guard | | | | | ○ | | ● | | ● | | ● |
| Hot fact-source consistency guard | | | | | ○ | | | | ● | | ● |
| Product Success Contract guard | ● | | | | ○ | ● | ● | | ● | | ● |
| Executable Acceptance Contract guard | | | | | ○ | ● | ● | | ● | | ● |
| Quality Budget Gate | | | | | ○ | ● | ● | ● | ● | | ● |
| Vertical Slice Delivery Packet guard | | | | | ○ | ● | ● | | ● | | ● |
| Weak-LLM Deterministic Scaffold generator/check | ● | ○ | | | ○ | ● | ● | | ● | | ● |
| User Interruption Policy v2 guard | ● | ○ | | | ○ | ● | ● | | ● | | ● |
| Runtime Readiness Matrix guard | | | | | ○ | | ● | | ● | | ● |
| First-Session Measurement guard | | | | | ○ | | ● | | ● | | ● |
| Governance Context Discovery | ● | ○ | | | ○ | ○ | ● | | ● | ● | ● |
| README Pack Guidance guard | ● | | | | ○ | | ● | | ● | | ● |

> ● 主要使用者  ○ 可选用

## 添加新工具的约定

向本工作流添加新工具时：

1. **放置位置**：与阶段强绑定的放在对应 `skills/stage-*/SKILL.md` 或专项 `skills/*/SKILL.md`；跨阶段自动化脚本放在 `skills/software-project-governance/infra/`
2. **命名规范**：`<动词>-<对象>.md`（如 `requirement-clarification.md`）
3. **必须包含**：触发条件、输入输出、执行步骤、独立使用说明、子工作流映射
4. **更新本索引**：在本文件中新增工具条目和关系矩阵
5. **更新校验脚本**：在 `verify_workflow.py` 中补入新工具的存在性检查；若工具是发布/门禁相关行为，优先提供可复跑子命令
