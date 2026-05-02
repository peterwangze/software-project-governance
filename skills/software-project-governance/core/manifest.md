# Workflow Manifest: software-project-governance

> **详细文件清单见 `manifest.json`**——canonical source of truth。本文件仅保留概述性说明。

## 基本信息

- `id`: `software-project-governance`
- `name`: 软件项目治理工作流
- `goal`: 将大型软件公司的项目管理经验沉淀为可被 coding agent 消费的项目治理 workflow plugin/skill
- `supported_agents`: `Claude`, `Codex`, `Gemini`
- `planned_agents`: `国内主流 agent CLI`

## 核心能力

- 11 阶段生命周期 + 11 Gate 门禁
- 7 职能组 14 Agent（Coordinator 融入入口层）
- 25 能力层 SKILL
- 计划、证据、决策、风险等记录模板
- 六层架构：适配层→入口层→业务智能层→能力层→基础设施层→核心层

## 流程目标

- 保证项目推进过程不偏离目标
- 保证过程数据可信、可追溯、可维护
- 降低 AI 参与研发时出现多套事实源和过程失真的风险

## 组成结构概览

详细文件清单见 `manifest.json`（`product` 段 = 用户安装获得，`repo_only` 段 = 开发仓库专属）。

- `skills/software-project-governance/`：运行时唯一事实源（入口层 + 核心层 + 基础设施层 + 参考知识）
- `agents/`：业务智能层——14 Agent 平铺
- `skills/`：能力层——25 SKILL 平铺
- `commands/`：用户斜杠命令入口
- `adapters/`：适配层——平台投影
- `project/`：设计时资产
- `.claude-plugin/` `.codex-plugin/` `.agents/`：插件包
