# 工作流工具目录

本文件是工作流第三层"基础工具/脚本层"的统一索引。所有工具独立于阶段，可被多个子工作流共用，也可被用户直接调用。

## 工具总览

| 工具 ID | 名称 | 类型 | 位置 | 触发场景 | 所属子工作流 | 可独立使用 |
|---------|------|------|------|---------|------------|----------|
| TOOL-001 | 需求澄清 checklist | checklist | `stages/initiation/requirement-clarification.md` | 需求模糊需要结构化澄清时 | 立项（initiation） | 是 |
| TOOL-002 | 技术评审 checklist | checklist | `stages/architecture/tech-review-checklist.md` | 架构/技术方案需要评审时 | 架构设计（architecture） | 是 |
| TOOL-003 | Code Review 规范 | standard | `stages/development/code-review-standard.md` | 代码变更需要审查时 | 开发（development） | 是 |
| TOOL-004 | 发布 checklist | checklist | `stages/release/release-checklist.md` | 版本发布前做最终检查时 | 版本发布（release） | 是 |
| TOOL-005 | 回顾会议模板 | template | `stages/maintenance/retro-meeting-template.md` | 阶段结束或项目复盘时 | 维护（maintenance） | 是 |
| TOOL-006 | 校验脚本 | script | `skills/software-project-governance/infra/verify_workflow.py` | 验证工作流资产完整性时 | 全部阶段 | 是 |
| TOOL-007 | governance-update 命令 | command | `commands/governance-update.md` | 更新 平台原生入口文件 bootstrap 到最新版本（不触碰 .governance/） | 维护（maintenance） | 是 |

## 工具详情

### TOOL-001：需求澄清 checklist

- **文件**：`stages/initiation/requirement-clarification.md`
- **子命令**：通过 Claude Code slash command `/requirement-clarification` 调用，或直接在上下文中加载
- **输入**：用户对需求的原始描述
- **输出**：经过 5 问法 + IN/OUT 边界分析后的结构化需求文档
- **触发条件**：用户表述模糊、需求边界不清、缺乏量化验收标准
- **依赖**：无
- **被以下子工作流使用**：立项（initiation）

### TOOL-002：技术评审 checklist

- **文件**：`stages/architecture/tech-review-checklist.md`
- **子命令**：通过 Claude Code slash command `/tech-review-checklist` 调用，或直接在上下文中加载
- **输入**：待评审的技术方案或架构设计文档
- **输出**：结构化的评审结论（通过/有条件通过/需修改）+ 具体评审意见
- **触发条件**：架构设计完成、技术选型确定、重大技术决策做出后
- **依赖**：无
- **被以下子工作流使用**：架构设计（architecture）、技术选型（selection）

### TOOL-003：Code Review 规范

- **文件**：`stages/development/code-review-standard.md`
- **子命令**：通过 Claude Code slash command `/code-review-standard` 调用，或直接在上下文中加载
- **输入**：待审查的代码变更（diff 或 PR）
- **输出**：分级审查结论（P0 阻塞 / P1 关键 / P2 建议）+ 逐条审查意见
- **触发条件**：代码变更提交 Review、合并前检查
- **依赖**：无
- **被以下子工作流使用**：开发（development）

### TOOL-004：发布 checklist

- **文件**：`stages/release/release-checklist.md`
- **子命令**：通过 Claude Code slash command `/release-checklist` 调用，或直接在上下文中加载
- **输入**：当前版本的变更清单和测试报告
- **输出**：逐项检查结论（通过/未通过/不适用）+ 发布建议
- **触发条件**：版本发布前
- **依赖**：测试报告（子工作流 testing）
- **被以下子工作流使用**：版本发布（release）

### TOOL-005：回顾会议模板

- **文件**：`stages/maintenance/retro-meeting-template.md`
- **子命令**：通过 Claude Code slash command `/retro-meeting` 调用，或直接在上下文中加载
- **输入**：本阶段/本轮的产出物和治理记录
- **输出**：结构化的回顾结论（目标回顾、结果评估、根因分析、改进计划）
- **触发条件**：阶段完成、项目里程碑、定期回顾
- **依赖**：本阶段的 evidence-log、decision-log、risk-log
- **被以下子工作流使用**：维护（maintenance），也可被任意阶段结束时调用

### TOOL-006：校验脚本

- **文件**：`skills/software-project-governance/infra/verify_workflow.py`
- **子命令**：`verify`（全量校验）、`status`（治理状态摘要）、`gate <G1-G11>`（Gate 检查）、`gates`（全部 Gate 状态）、`stage <stage-id>`（阶段状态）、`stages`（全部阶段状态）
- **输入**：无（自动读取项目文件）
- **输出**：校验结果（PASSED/FAILED）+ 治理状态摘要
- **触发条件**：工作流资产变更后、Gate 检查时、定期巡检
- **依赖**：项目需已完成 `governance-init`
- **被以下子工作流使用**：全部阶段

## 工具与子工作流的关系矩阵

| 工具 | 立项 | 调研 | 选型 | 环境 | 架构 | 开发 | 测试 | CI/CD | 发布 | 运营 | 维护 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 需求澄清 | ● | ○ | ○ | | | | | | | | |
| 技术评审 | | | ● | | ● | | | | | | |
| Code Review | | | | | | ● | | | | | |
| 发布检查 | | | | | | | | | ● | | |
| 回顾模板 | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ○ | ● |
| 校验脚本 | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● | ● |

> ● 主要使用者  ○ 可选用

## 添加新工具的约定

向本工作流添加新工具时：

1. **放置位置**：与阶段强绑定的放在 `stages/<stage-id>/`；跨阶段通用的放在 `tools/`（待创建）
2. **命名规范**：`<动词>-<对象>.md`（如 `requirement-clarification.md`）
3. **必须包含**：触发条件、输入输出、执行步骤、独立使用说明、子工作流映射
4. **更新本索引**：在本文件中新增工具条目和关系矩阵
5. **更新校验脚本**：在 `verify_workflow.py` 中补入新工具的存在性检查
