# 五层架构设计

## 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                    入口层                                │
│  主 SKILL.md（仅引导进入 Coordinator）                    │
│  Coordinator Agent（直接由主 agent 加载）                  │
└──────────────────────────┬──────────────────────────────┘
                           │ 加载并成为
┌──────────────────────────▼──────────────────────────────┐
│                  业务智能层（Agent 库）                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │  角色 + 判断 + 可调用多个 SKILL                      │  │
│  │  有 persona / 擅长 / 痛恨 / 工具权限                 │  │
│  │  动态组合，按流程搭配                                │  │
│  │  依赖能力层 SKILL —— 单向依赖，不可反向               │  │
│  └───────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────┘
                           │ 调用（单向依赖）
┌──────────────────────────▼──────────────────────────────┐
│                    能力层（SKILL 库）                      │
│  ┌───────────────────────────────────────────────────┐  │
│  │  确定性步骤，不依赖 LLM 判断能力                      │  │
│  │  一个 SKILL = 一类事务（阶段/审查/模板/命令）          │  │
│  │  触发条件明确 + 步骤确定 + 输入输出契约                │  │
│  │  依赖基础设施层工具 —— 单向依赖，不可反向              │  │
│  └───────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────┘
                           │ 调用（单向依赖）
┌──────────────────────────▼──────────────────────────────┐
│                   基础设施层                              │
│  脚本库 / 工具库 / MCP 库 / hooks / 验证引擎              │
│  可被任何 agent 或 skill 调用，不依赖 LLM                 │
└──────────────────────────┬──────────────────────────────┘
                           │ 引用（单向依赖）
┌──────────────────────────▼──────────────────────────────┐
│                    核心层                                 │
│  工作流合约(protocol/) / 模板(templates/)                 │
│  生命周期定义 / Gate 规则 / Profile 规则                  │
│  输出件模板 / 版本管理策略                                │
└─────────────────────────────────────────────────────────┘
```

## 依赖方向（铁律）

```
入口层 → 业务智能层 → 能力层 → 基础设施层 → 核心层
```

**单向依赖，不可反向。** 上层可以依赖下层，下层 MUST NOT 依赖上层。核心层是最底层基础，不依赖任何上层。

## 各层定义

### 核心层——工作流合约

**是什么**：工作流本身的定义——阶段模型、Gate 规则、模板、版本策略。不包含任何 agent 行为指令，纯粹是"工作流是什么"。

**依赖**：无（最底层）

**包含**：
- 工作流合约（protocol/）
- 输出件模板（templates/）
- 生命周期定义（lifecycle.md, stage-gates.md）
- Profile 规则（profiles.md）
- 版本管理策略（VERSIONING.md）
- 中途接入协议（onboarding.md）
- 审计框架（audit-framework.md）
- Task-Gate 模型定义（task-gate-model.md）

**不包含**：任何 agent 角色的定义、任何执行步骤、任何工具调用指令。

### 基础设施层——脚本/工具/MCP

**是什么**：可被能力层或业务智能层调用的通用能力。不依赖 LLM，独立可执行。

**依赖**：核心层（引用合约定义）

**包含**：
- Git hooks（pre-commit, post-commit, prepare-commit-msg）
- 验证引擎（verify_workflow.py）
- 治理检查脚本（check-governance）
- MCP 服务
- 通用工具

**原则**：任何放在此层的工具必须——(a) 独立可执行，(b) 有明确的输入输出契约，(c) 不依赖 agent 上下文。

### 能力层——SKILL 库（确定性步骤）

**是什么**：标准 SKILL 格式（frontmatter + 触发条件 + 执行流程 + 步骤清单）。只处理一类明确事务，步骤明确，不依赖 LLM 的判断能力。**这是系统的"能力原子"——业务智能层的 Agent 通过组合这些能力来完成复杂任务。**

**依赖**：基础设施层（调用脚本/工具）

**被谁依赖**：业务智能层（Agent 调用 SKILL）

**特征**：
- 触发条件明确（"用户请求代码审查" → 加载 code-review SKILL）
- 步骤确定（步骤1 → 步骤2 → 步骤3，无分支判断）
- 不依赖 LLM 能力（每个步骤有明确的输入/输出/验收标准）
- 标准 SKILL 格式（name, description, 触发条件, 执行流程, 输入参数, 输出格式）
- **不能主动决策**——只执行，不判断

**SKILL 分类**：

| 类别 | 包含 | 说明 |
|------|------|------|
| 项目初始化 | 全新项目初始化, 中途接入, 工作流升级 | 治理基础设施搭建 |
| 阶段工作流 | 立项, 调研, 选型, 环境搭建, 架构设计, 开发, 测试, CI/CD, 发布, 运营, 维护 | 每个阶段一个 SKILL |
| 质量保障 | 代码审查, 技术评审, 安全审查, 测试设计 | 审查类 SKILL |
| 模板生成 | PR/FAQ, OKR, 6-Pager, 发布检查清单, 复盘会议 | 产出物生成 |
| 治理命令 | 状态展示, Gate 检查, 治理验证 | 运维类 SKILL |

### 业务智能层——Agent 库（角色+判断）

**是什么**：有角色定位和 persona 的智能体。可以有判断和决策能力，通过组合能力层的多个 SKILL 来完成复杂任务。**这是系统的"决策中枢"——决定做什么、怎么做、谁来做。**

**依赖**：能力层（调用 SKILL）+ 基础设施层（直接调用工具）

**被谁依赖**：入口层（加载 Coordinator Agent）

**特征**：
- 角色 persona（"你是老周，一个..."）
- 专门提示词（角色定位 + 擅长 + 痛恨 + 职责范围）
- 工具权限声明（哪些工具可用/禁用）
- 可调用多个 SKILL（"当你需要做代码审查时，加载 code-review SKILL"）
- 动态组合（一个工作流可以有多个 Agent 参与）
- **有判断权**——在能力层提供的确定性步骤之上做决策

**Agent 分类**：

| 类别 | Agent | 可调用的 SKILL |
|------|-------|---------------|
| 统筹 | Coordinator | 所有 SKILL（通过路由） |
| 分析 | Analyst | 需求澄清, 竞品分析, PR/FAQ, OKR |
| 设计 | Architect | 技术选型, 架构设计, ADR, 技术评审 |
| 实现 | Developer | 开发, TDD, 环境搭建 |
| 审查 | Reviewer | 代码审查, 技术评审, 安全审查 |
| 测试 | QA | 测试设计, 集成测试, 性能测试 |
| 运维 | DevOps | CI/CD, 环境管理, 监控 |
| 发布 | Release | 发布检查, 版本规划, 变更日志 |
| 维护 | Maintenance | 缺陷修复, 复盘会议, 规则演进 |

### 入口层——引导进入业务智能层

**是什么**：主 SKILL.md，仅做一件事——声明"加载 Coordinator Agent，进入 Agent Team 模式"。不包含任何行为规则，不包含任何执行步骤。

**依赖**：业务智能层（加载 Coordinator Agent）

**被谁依赖**：用户/系统（通过 skill 加载机制）

**内容**：
- 激活流程（4 步）
- 工作流合约引用
- Coordinator 参考知识表
- 治理基础设施列表
- SKILL 库入口

## 能力层 vs 业务智能层（关键区分）

| 维度 | 能力层（SKILL） | 业务智能层（Agent） |
|------|----------------|-------------------|
| **本质** | 工具——"能做什么" | 智能体——"谁来做、怎么做" |
| **决策权** | 无——只执行确定性步骤 | 有——在能力边界内做判断 |
| **LLM 依赖** | 不依赖——步骤确定 | 依赖——需要判断和推理 |
| **组合性** | 被组合——Agent 调用的原子单元 | 组合者——编排多个 SKILL |
| **persona** | 无——不涉及角色 | 有——角色定位驱动行为 |
| **工具权限** | 无——不直接使用工具 | 有——明确允许/禁止的工具 |
| **依赖方向** | → 基础设施层 | → 能力层 + 基础设施层 |
| **示例** | "代码审查 checklist" | "老严——代码审查者" |

## 当前资产映射

### 核心层映射

| 当前文件 | 目标位置 | 说明 |
|---------|---------|------|
| `protocol/*.md` | `core/protocol/` | 保持不变 |
| `workflows/software-project-governance/templates/` | `core/templates/` | 保持不变 |
| `workflows/software-project-governance/manifest.md` | `core/manifest.md` | 工作流身份声明 |
| `references/lifecycle.md` | `core/lifecycle.md` | 阶段定义 |
| `references/stage-gates.md` | `core/stage-gates.md` | Gate 规则 |
| `references/profiles.md` | `core/profiles.md` | Profile 规则 |
| `references/onboarding.md` | `core/onboarding.md` | 接入协议 |
| `references/audit-framework.md` | `core/audit-framework.md` | 审计框架 |
| `VERSIONING.md` | `core/VERSIONING.md` | 版本管理 |
| `references/task-gate-model.md` | `core/task-gate-model.md` | Task-Gate 定义 |

### 基础设施层映射

| 当前文件 | 目标位置 | 说明 |
|---------|---------|------|
| `scripts/pre-commit-hook.sh` | `infra/hooks/pre-commit` | Git hooks |
| `scripts/post-commit-hook.sh` | `infra/hooks/post-commit` | Git hooks |
| `scripts/prepare-commit-msg-hook.sh` | `infra/hooks/prepare-commit-msg` | Git hooks |
| `scripts/verify_workflow.py` | `infra/verify_workflow.py` | 验证引擎 |
| `skills/software-project-governance/TOOLS.md` | `infra/TOOLS.md` | 工具索引 |

### 能力层（SKILL）映射

| 当前文件 | 目标位置 | 类别 |
|---------|---------|------|
| `commands/governance-init.md` | `skills/init/` | 项目初始化 |
| `commands/software-project-governance.md` | `skills/unified-entry/` | 统一入口 |
| `commands/governance-status.md` | `skills/status/` | 治理命令 |
| `commands/governance-gate.md` | `skills/gate-check/` | 治理命令 |
| `commands/governance-verify.md` | `skills/verify/` | 治理命令 |
| `commands/governance-update.md` | `skills/upgrade/` | 治理命令 |
| `stages/initiation/sub-workflow.md` | `skills/stage-initiation/` | 阶段工作流 |
| `stages/research/sub-workflow.md` | `skills/stage-research/` | 阶段工作流 |
| `stages/selection/sub-workflow.md` | `skills/stage-selection/` | 阶段工作流 |
| `stages/infrastructure/sub-workflow.md` | `skills/stage-infra/` | 阶段工作流 |
| `stages/architecture/sub-workflow.md` | `skills/stage-architecture/` | 阶段工作流 |
| `stages/development/sub-workflow.md` | `skills/stage-development/` | 阶段工作流 |
| `stages/testing/sub-workflow.md` | `skills/stage-testing/` | 阶段工作流 |
| `stages/ci-cd/sub-workflow.md` | `skills/stage-cicd/` | 阶段工作流 |
| `stages/release/sub-workflow.md` | `skills/stage-release/` | 阶段工作流 |
| `stages/operations/sub-workflow.md` | `skills/stage-operations/` | 阶段工作流 |
| `stages/maintenance/sub-workflow.md` | `skills/stage-maintenance/` | 阶段工作流 |
| `stages/architecture/tech-review-checklist.md` | `skills/tech-review/` | 质量保障 |
| `stages/development/code-review-standard.md` | `skills/code-review/` | 质量保障 |
| `stages/release/release-checklist.md` | `skills/release-checklist/` | 模板生成 |
| `stages/maintenance/retro-meeting-template.md` | `skills/retro-meeting/` | 模板生成 |
| `stages/initiation/requirement-clarification.md` | `skills/requirement-clarification/` | 需求分析 |
| `stages/initiation/pr-faq-template.md` | `skills/pr-faq/` | 模板生成 |
| `stages/initiation/okr-template.md` | `skills/okr/` | 模板生成 |
| `stages/selection/six-pager-template.md` | `skills/six-pager/` | 模板生成 |

### 业务智能层（Agent）映射

| 当前文件 | 目标位置 | 变更 |
|---------|---------|------|
| `agents/coordinator/SKILL.md` | `agents/coordinator/SKILL.md` | 保持，分离 persona 和 SKILL 引用 |
| `agents/developer/SKILL.md` | `agents/developer/SKILL.md` | 保持 |
| `agents/reviewer/SKILL.md` | `agents/reviewer/SKILL.md` | 保持 |
| `agents/architect/SKILL.md` | `agents/architect/SKILL.md` | 保持 |
| `agents/qa/SKILL.md` | `agents/qa/SKILL.md` | 保持 |
| `agents/devops/SKILL.md` | `agents/devops/SKILL.md` | 保持 |
| `agents/analyst/SKILL.md` | `agents/analyst/SKILL.md` | 保持 |
| `agents/release/SKILL.md` | `agents/release/SKILL.md` | 保持 |
| `agents/maintenance/SKILL.md` | `agents/maintenance/SKILL.md` | 保持 |

### 入口层映射

| 当前文件 | 变更 |
|---------|------|
| `skills/software-project-governance/SKILL.md` | **已瘦身为入口**：~46 行，仅声明"加载 Coordinator Agent，进入 Agent Team 模式" |

## 当前的主要混淆

1. **能力层和业务智能层不分**——SKILL（确定性步骤）和 Agent（角色+判断）混在一起叫"业务层"，混淆了工具和智能体的本质区别。Agent 依赖 SKILL，但 SKILL 不依赖 Agent——这是单向依赖，应该分层表达
2. **主 SKILL.md 曾经是行为协议而非入口**——500 行 M0-M9 规则应该是 Coordinator Agent 的参考知识，不是入口 SKILL 的内容（已在 Phase 1 修复）
3. **agents/coordinator/SKILL.md 和 skills/software-project-governance/SKILL.md 职责重叠**——前者是 persona+协调流程，后者是入口。Coordinator 直接加载前者，用户通过后者进入
4. **commands/ 和 stages/ 的 SKILL 格式不统一**——commands 有 Input Parameters/Execution Flow/Output Format 标准格式，stages 是自由格式 markdown
5. **references/ 混合了核心层（lifecycle, stage-gates）和能力层参考（interaction-boundary, agent-failure-modes）**
6. **Agent 的 SKILL.md 和能力层 SKILL 的 SKILL.md 同名不同质**——前者是 persona 定义（有判断力），后者是步骤定义（无判断力）

## 目标目录结构

```
skills/software-project-governance/
  SKILL.md                        ← 入口层（仅引导进入 Coordinator）
  agents/                         ← 业务智能层（Agent 库）
    coordinator/SKILL.md
    developer/SKILL.md
    reviewer/SKILL.md
    architect/SKILL.md
    qa/SKILL.md
    devops/SKILL.md
    analyst/SKILL.md
    release/SKILL.md
    maintenance/SKILL.md
  skills/                         ← 能力层（SKILL 库）
    init/SKILL.md                 ← 全新项目初始化
    onboarding/SKILL.md           ← 中途接入
    upgrade/SKILL.md              ← 工作流升级
    status/SKILL.md               ← 状态展示
    gate-check/SKILL.md           ← Gate 检查
    verify/SKILL.md               ← 治理验证
    stage-initiation/SKILL.md     ← 立项阶段
    stage-research/SKILL.md       ← 调研阶段
    stage-selection/SKILL.md      ← 选型阶段
    stage-infra/SKILL.md          ← 基础设施阶段
    stage-architecture/SKILL.md   ← 架构设计阶段
    stage-development/SKILL.md    ← 开发阶段
    stage-testing/SKILL.md        ← 测试阶段
    stage-cicd/SKILL.md           ← CI/CD 阶段
    stage-release/SKILL.md        ← 发布阶段
    stage-operations/SKILL.md     ← 运营阶段
    stage-maintenance/SKILL.md    ← 维护阶段
    code-review/SKILL.md          ← 代码审查
    tech-review/SKILL.md          ← 技术评审
    requirement-clarification/SKILL.md ← 需求澄清
    pr-faq/SKILL.md               ← PR/FAQ 模板
    okr/SKILL.md                  ← OKR 模板
    six-pager/SKILL.md            ← 6-Pager 模板
    release-checklist/SKILL.md    ← 发布检查清单
    retro-meeting/SKILL.md        ← 复盘会议模板
  core/                           ← 核心层
    protocol/
    templates/
    manifest.md
    lifecycle.md
    stage-gates.md
    profiles.md
    onboarding.md
    audit-framework.md
    task-gate-model.md
    VERSIONING.md
  infra/                          ← 基础设施层
    hooks/
    verify_workflow.py
    TOOLS.md
  references/                     ← 参考知识（Coordinator 按需读取）
    behavior-protocol.md          ← M0-M9 强制性规则
    agent-team-architecture.md
    agent-failure-modes.md
    interaction-boundary.md
    methodology-routing.md
    agent-communication-protocol.md
    user-perspective-principle.md
    data-boundary.md
    agent-entry-differences.md
    company-practices-summary.md
```

## 需求拆解

### P0（必须——架构正确性）

| ID | 需求 | 工作量 |
|----|------|--------|
| REQ-041 | 主 SKILL.md 瘦身为入口——删除 M0-M9 行为协议（移入 behavior-protocol.md），仅保留"加载 Coordinator Agent"指令 | ✅ 已完成 |
| REQ-042 | 建立统一的能力层（SKILL）目录结构——`skills/{category}/{name}/SKILL.md` | 中 |
| REQ-043 | 统一 SKILL 格式——所有 SKILL 使用相同 frontmatter + 触发条件 + 执行流程 + 步骤清单格式 | 中 |
| REQ-044 | 迁移 stages/ 和 commands/ 到能力层 skills/ 目录 | 大 |
| REQ-045 | 分离核心层文件到 core/ 目录 | 中 |
| REQ-046 | 建立基础设施层目录结构——infra/hooks/, infra/tools/ | 小 |

### P1（重要——可用性）

| ID | 需求 | 工作量 |
|----|------|--------|
| REQ-047 | 每个 Agent 声明可调用的 SKILL 列表——Agent→SKILL 绑定关系（业务智能层→能力层依赖） | 中 |
| REQ-048 | 建立 SKILL 分类索引——按类别（初始化/阶段/审查/模板/命令）组织 | 小 |
| REQ-049 | references/ 清理——核心层移入 core/，参考文档保留 | 中 |

### P2（增强）

| ID | 需求 | 工作量 |
|----|------|--------|
| REQ-050 | 建立统一的工具/MCP 库索引——infra/TOOLS.md 升级 | 小 |
| REQ-051 | verify_workflow.py 适配新目录结构 | 中 |

## 实施分步

### Phase 1: 主 SKILL.md 瘦身（P0, ✅ 已完成）
1. ✅ 将主 SKILL.md 从 487 行行为协议瘦身为 46 行入口
2. ✅ 创建 references/behavior-protocol.md 保存 M0-M9 强制性规则
3. ✅ verify_workflow.py snippets 同步更新

### Phase 2: 核心层和基础设施层建立（P0）
4. 创建 core/ 目录，移入 lifecycle/stage-gates/profiles/onboarding/audit-framework/VERSIONING/task-gate-model
5. 创建 infra/ 目录，移入 hooks/ 和 verify_workflow.py
6. 更新 verify_workflow.py 中的路径引用

### Phase 3: 能力层（SKILL）建立和迁移（P0）
7. 创建统一的 skills/ 目录结构
8. 将 stages/ 下的 SKILL 迁移到 skills/（每阶段一个目录+SKILL.md）
9. 将 commands/ 下的 SKILL 迁移到 skills/（标准化格式）
10. 统一所有 SKILL 格式

### Phase 4: 业务智能层（Agent）升级——Agent↔SKILL 绑定（P1）
11. 为每个 Agent 添加"可调用的 SKILL"列表（声明对能力层的依赖）
12. 建立 SKILL 分类索引

### Phase 5: 验证和发布（P2）
13. verify_workflow.py 适配新结构
14. 版本 bump + CHANGELOG
15. E2E 验证
