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
- **子命令**：`verify`（全量校验）、`status`（治理状态摘要）、`gate <G1-G11>`（Gate 检查）、`gates`（全部 Gate 状态）、`stage <stage-id>`（阶段状态）、`stages`（全部阶段状态）、`check-governance --fail-on-issues`（治理健康检查）、`e2e-check`（E2E proxy + fixture 分层检查）、`check-version-consistency`、`check-manifest-consistency`、`check-locks`、`check-archive-integrity`
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

> ● 主要使用者  ○ 可选用

## 添加新工具的约定

向本工作流添加新工具时：

1. **放置位置**：与阶段强绑定的放在对应 `skills/stage-*/SKILL.md` 或专项 `skills/*/SKILL.md`；跨阶段自动化脚本放在 `skills/software-project-governance/infra/`
2. **命名规范**：`<动词>-<对象>.md`（如 `requirement-clarification.md`）
3. **必须包含**：触发条件、输入输出、执行步骤、独立使用说明、子工作流映射
4. **更新本索引**：在本文件中新增工具条目和关系矩阵
5. **更新校验脚本**：在 `verify_workflow.py` 中补入新工具的存在性检查；若工具是发布/门禁相关行为，优先提供可复跑子命令
