# SKILL 分类索引

能力层（SKILL 库）所有 SKILL 的完整索引。每个 SKILL 有明确的触发条件、所属类别和被哪些 Agent 调用。

## 阶段工作流（11 个）

| SKILL | 路径 | 用途 | 调用 Agent |
|-------|------|------|-----------|
| stage-initiation | `skills/stage-initiation/SKILL.md` | 立项与目标定义——问题、目标、范围、成功标准 | Coordinator, Analyst |
| stage-research | `skills/stage-research/SKILL.md` | 调研与竞争分析——调查、竞品分析、可行性 | Coordinator, Analyst |
| stage-selection | `skills/stage-selection/SKILL.md` | 技术选型与方案预研——技术选型、PoC 验证 | Coordinator, Architect |
| stage-infra | `skills/stage-infra/SKILL.md` | 环境搭建与基础设施——开发环境、仓库、基础 CI | Coordinator, Architect, Developer, DevOps |
| stage-architecture | `skills/stage-architecture/SKILL.md` | 架构设计——系统设计、模块拆分、技术评审 | Coordinator, Architect |
| stage-development | `skills/stage-development/SKILL.md` | 开发实现——编码、单元测试、代码审查 | Coordinator, Developer |
| stage-testing | `skills/stage-testing/SKILL.md` | 测试与质量保障——集成、系统、性能、安全测试 | Coordinator, QA |
| stage-cicd | `skills/stage-cicd/SKILL.md` | 防护网与 CI/CD——流水线、自动化、质量门控 | Coordinator, DevOps |
| stage-release | `skills/stage-release/SKILL.md` | 版本发布——发布计划、changelog、回滚方案 | Coordinator, Release |
| stage-operations | `skills/stage-operations/SKILL.md` | 运营与反馈——监控、反馈、优化 | Coordinator, Release |
| stage-maintenance | `skills/stage-maintenance/SKILL.md` | 维护与演进——Bug 修复、规则更新、复盘 | Coordinator, Maintenance |

## 质量保障（2 个）

| SKILL | 路径 | 用途 | 调用 Agent |
|-------|------|------|-----------|
| code-review | `skills/code-review/SKILL.md` | 代码审查标准——审查流程、分级标准、检查项 | Coordinator, Developer, Reviewer |
| tech-review | `skills/tech-review/SKILL.md` | 技术评审 checklist——架构评审、技术选型评审 | Coordinator, Architect, Reviewer |

## 模板生成（3 个）

| SKILL | 路径 | 用途 | 调用 Agent |
|-------|------|------|-----------|
| pr-faq | `skills/pr-faq/SKILL.md` | PR/FAQ 模板——Amazon Working Backwards 文档 | Coordinator, Analyst |
| okr | `skills/okr/SKILL.md` | OKR 模板——目标与关键结果定义 | Coordinator, Analyst |
| six-pager | `skills/six-pager/SKILL.md` | 6-Pager 模板——Amazon 技术方案文档 | Coordinator, Architect, Analyst |

## 专项技能（3 个）

| SKILL | 路径 | 用途 | 调用 Agent |
|-------|------|------|-----------|
| requirement-clarification | `skills/requirement-clarification/SKILL.md` | 需求澄清 checklist——需求分析、边界确认 | Coordinator, Analyst |
| release-checklist | `skills/release-checklist/SKILL.md` | 发布检查清单——发布前检查项、回滚验证 | Coordinator, Release |
| retro-meeting | `skills/retro-meeting/SKILL.md` | 复盘会议模板——目标回顾、结果评估、原因分析、经验沉淀 | Coordinator, Maintenance |

## 能力层入口（1 个）

| SKILL | 路径 | 用途 | 调用 Agent |
|-------|------|------|-----------|
| main-workflow | `skills/main-workflow/SKILL.md` | 统一工作流入口——场景匹配、跨层调用协议 | Coordinator |

## Agent↔SKILL 绑定总表

| Agent | 可调用 SKILL |
|-------|-------------|
| **Coordinator** | 全部 SKILL（通过路由分发） |
| **Analyst** | stage-initiation, stage-research, requirement-clarification, pr-faq, okr, six-pager |
| **Architect** | stage-architecture, stage-selection, stage-infra, tech-review, six-pager |
| **Developer** | stage-development, stage-infra, code-review |
| **Reviewer** | code-review, tech-review |
| **QA** | stage-testing |
| **DevOps** | stage-cicd, stage-infra |
| **Release** | stage-release, release-checklist, stage-operations |
| **Maintenance** | stage-maintenance, retro-meeting |
