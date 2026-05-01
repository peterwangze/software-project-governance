# Workflow Manifest: software-project-governance

## 基本信息

- `id`: `software-project-governance`
- `name`: 软件项目治理工作流
- `version`: `0.14.0`
- `goal`: 将大型软件公司的项目管理经验沉淀为可被 coding agent 消费的项目治理 workflow plugin/skill
- `supported_agents`: `Claude`, `Codex`, `Gemini`
- `planned_agents`: `国内主流 agent CLI`
- `validation_status`: 六层架构落地，11 阶段 100% 审查覆盖，0.11.0 已发布；外部项目验证待执行

## 核心能力

- 11 阶段生命周期 + 11 Gate 门禁
- 7 职能组 9 Agent（管理/设计/开发/测试/评审/运维/维护）
- 25 能力层 SKILL（11 阶段 + 7 审查 + 3 模板 + 3 专项 + 1 入口）
- 计划、证据、决策、风险等记录模板
- 六层架构：适配层→入口层→业务智能层→能力层→基础设施层→核心层

## 流程目标

- 保证项目推进过程不偏离目标
- 保证过程数据可信、可追溯、可维护
- 降低 AI 参与研发时出现多套事实源和过程失真的风险

## 组成结构

- `skills/software-project-governance/`：**运行时唯一事实源**
  - `SKILL.md`：入口层——引导进入 Coordinator
  - `agents/`：业务智能层——7 职能组 9 Agent
  - `skills/`：能力层——25 SKILL
  - `core/`：核心层——protocol/ + templates/ + 生命周期/Gate/Profile 等规则
  - `infra/`：基础设施层——verify_workflow.py + hooks + TOOLS.md
  - `references/`：参考知识——行为协议/架构设计/失败模式等
- `commands/`：用户斜杠命令入口（7 个命令）
- `adapters/`：适配层——平台投影（Claude/Codex/Gemini）
- `project/workflows/software-project-governance/`：设计时资产（research/ + examples/）
- `.claude-plugin/` `.codex-plugin/` `.agents/`：插件包
