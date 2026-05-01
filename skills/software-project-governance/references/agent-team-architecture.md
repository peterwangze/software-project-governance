# Agent Team 架构演进设计

> **v0.8.0+ 设计文档——尚未激活。** 当前运行模型为 `SKILL.md`、`core/stage-gates.md` 和 `main-workflow.md` 中定义的 Phase-Gate。在 v0.8.0 实现之前，不得应用 Task-Gate 规则或 Agent Team 角色定义。本文档描述的是目标架构，而非当前运行时行为。

本文件定义 `software-project-governance` 从串行阶段模型（Phase-Gate）向按需触发的多 Agent 协作团队（Task-Gate + Agent Team）的架构演进方案。

## 1. 问题陈述：为什么串行阶段模型是死板的

### 1.1 当前架构的 6 个层面系统性强制串行

| 层面 | 文件 | 串行强制机制 |
|------|------|------------|
| 路由引擎 | `main-workflow.md:69` | 默认序列 `1→2→3→...→11`，前 Gate 通过才进入下一阶段 |
| Gate 模型 | `stage-gates.md:108` | Phase-Gate：整个阶段通过才进入下一阶段（"未通过 Gate 不得声称进入下一阶段"） |
| 数据结构 | `plan-tracker.md:10` | 单一 `当前阶段` 字段，无法表示多阶段并行 |
| 子工作流 | `stages/*/sub-workflow.md` | 入口条件硬编码要求前置 Gate 通过（如开发要求 G5 通过） |
| Profile 约束 | `profiles.md:59` | strict profile 明确禁止阶段重叠 |
| 任务协议 | `SKILL.md M7.4/M7.5` | 原子线性任务序列（evidence → check → audit → commit → continue） |

### 1.2 真实项目的行为模式

真实项目不是线性的。在立项后的任何时刻：

```
立项 → 调研 ──────────────────────────────→
         ├→ 技术选型 ────────────────────→
         │     ├→ 环境搭建 ──────────────→
         │     │     ├→ 架构设计 ────────→
         │     │     │     ├→ 开发 ──────→
         │     │     │     │     ├→ 测试 ─→
         │     │     │     │     ├→ CI/CD →
         │     │     │     ├→ 开发 ──────→  (第二轮迭代)
         │     │     ├→ 架构设计 ────────→  (架构演进)
         │     ├→ 技术选型 ────────────────→  (新依赖选型)
         ├→ 调研 ──────────────────────────→  (新需求调研)
```

- 开发过程中发现需要重新调研 → 触发调研 SKILL
- 测试过程中发现架构缺陷 → 触发架构设计 SKILL
- CI/CD 搭建中发现选型问题 → 触发技术选型 SKILL
- 任何阶段都可能在任何时候发生
- 同一时刻可能有多个活动在进行

### 1.3 当前模型的另一个根本缺陷：自己产出自己审查

当前架构下，同一个 agent 承担所有角色：自己做需求分析 → 自己做架构设计 → 自己写代码 → 自己审查代码 → 自己测试 → 自己发布。这违反了基本的工程质量原则——**独立审查**。

## 2. 参考分析：superpowers、PUA、Harness 教我们什么

### 2.1 superpowers (170K stars, de facto standard)

**核心模式**：

| 要素 | superpowers 做法 | 对本项目的启发 |
|------|-----------------|--------------|
| **Subagent-driven development** | 每个 task 用 fresh subagent 执行，两阶段审查（spec → code quality） | 不同任务用不同 agent 实例，自带独立上下文 |
| **HARD GATE** | 阻断型门禁——未通过则下一个动作无法执行 | 等同于本项目的 pre-commit hook 阻断——已验证有效 |
| **Brainstorming 强制前置** | 写代码前必须通过 Socratic 设计澄清 | Coordinator 在分发任务前执行 M5 AskUserQuestion 确认 |
| **Verification before completion** | 声称完成前必须 fresh 运行验证 | 等同于 M7.4 的 evidence + check-governance 步骤 |
| **1% Rule** | 只要 1% 的可能适用，agent 就必须调用该 skill | Coordinator 的路由判断标准 |
| **Systematic debugging** | 3 次失败 → 停止，质疑架构 | 各角色 agent 的内置韧性协议 |

**superpowers 对本项目最大的启示**：不是线性阶段，而是**可组合的 skill 集合 + HARD GATE 阻断机制**。每个 skill 独立触发，skill 之间有明确的输入/输出契约。

### 2.2 PUA (已安装运行)

**核心模式**：

| 要素 | PUA 做法 | 对本项目的启发 |
|------|---------|--------------|
| **方法论文智能路由** | 按任务类型（Debug/构建/审查/架构决策）自动选择最优方法论（华为 RCA / Musk The Algorithm / Amazon Working Backwards） | 不同角色 agent 使用不同的提示词风格和方法论 |
| **Owner 意识** | 强制 agent 不是"接指令→执行→交付"的外包，而是 Owner | 角色 agent 定义中强调 DRI 职责边界 |
| **失败切换链** | 失败模式检测 → 方法论切换（Musk→拼多多→华为） | 角色 agent 遇到其能力范围外的任务时升级给 Coordinator |
| **三条红线** | 闭环意识、事实驱动、穷尽一切 | Agent 安全约束——所有角色 agent 的基础行为协议 |

**PUA 对本项目最大的启示**：不同任务需要**不同的"味道"和方法论**。开发 agent 应该用 Musk 味（质疑→删除→简化→加速），审查 agent 应该用 Jobs 味（减法优先+像素级完美），调试 agent 应该用华为味（RCA 5-Why 根因）。

### 2.3 Harness (Agent Team 工厂)

**6 种团队架构模式**：

| 模式 | 适用场景 | 本项目采用 |
|------|---------|----------|
| Pipeline | 顺序依赖任务 | 部分采用（分析→设计→实现有自然顺序） |
| Fan-out/Fan-in | 并行独立任务 | **采用**——并行代码审查、并行调研 |
| Expert Pool | 上下文相关的选择性调用 | **采用**——Coordinator 按任务类型选择角色 agent |
| Producer-Reviewer | 产出后独立质量审查 | **核心采用**——开发 agent ≠ 审查 agent |
| Supervisor | 中央 agent 动态分发 | **核心采用**——Coordinator = Supervisor |
| Hierarchical Delegation | 自顶向下递归委派 | 保留用于复杂子任务 |

**Harness 研究数据**：使用 Agent Team 模式后质量评分 +60%（49.5→79.3），胜率 100%（15/15）。

## 3. 目标架构：Coordinator + 角色 Agent 团队

### 3.1 架构总览

```
                        ┌─────────────────────────────┐
                        │         Coordinator           │
                        │  ┌───────────────────────┐   │
                        │  │ 用户交互界面            │   │
                        │  │ M5 AskUserQuestion      │   │
                        │  │ 需求澄清 + 范围确认     │   │
                        │  ├───────────────────────┤   │
                        │  │ 任务分解 + Agent 路由   │   │
                        │  │ 按任务类型匹配角色       │   │
                        │  │ 按方法论路由匹配味道     │   │
                        │  ├───────────────────────┤   │
                        │  │ 治理看护                │   │
                        │  │ Task-Gate 审核           │   │
                        │  │ Evidence/Decision/Risk   │   │
                        │  │ 跨 Agent 一致性验证      │   │
                        │  └───────────────────────┘   │
                        │  DOES: 协调、路由、治理      │
                        │  DOES NOT: 实现、审查、部署  │
                        └──────────┬──────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
    ┌─────────▼──────┐  ┌─────────▼──────┐  ┌─────────▼──────┐
    │ Analyst Agent   │  │Architect Agent  │  │Developer Agent  │
    │ 调研+需求+竞品  │  │ 选型+设计+评审  │  │ 实现+单元测试   │
    │ Skill: analyst  │  │ Skill: architect│  │ Skill: developer │
    │ Prompt: 🔶Amazon│  │ Prompt: 🟠阿里  │  │ Prompt: ⬛Musk   │
    └────────────────┘  └────────────────┘  └────────────────┘
              │                    │                    │
    ┌─────────▼──────┐  ┌─────────▼──────┐  ┌─────────▼──────┐
    │  QA Agent       │  │ DevOps Agent    │  │Reviewer Agent   │
    │  测试+质量保障  │  │ CI/CD+基础设施  │  │ 审查+安全+标准  │
    │  Skill: qa      │  │ Skill: devops   │  │ Skill: reviewer │
    │  Prompt: 🟡字节  │  │ Prompt: 🔴华为  │  │ Prompt: ⬜Jobs  │
    └────────────────┘  └────────────────┘  └────────────────┘
              │                    │                    │
    ┌─────────▼──────┐  ┌─────────▼──────┐
    │ Release Agent   │  │Maintenance Agent│
    │ 发布+回滚+变更  │  │ 复盘+修复+演进  │
    │ Skill: release  │  │ Skill: maintain │
    │ Prompt: 🟧小米   │  │ Prompt: 🔵美团  │
    └────────────────┘  └────────────────┘
```

### 3.2 核心设计原则

1. **Coordinator 只协调，不执行**：Coordinator 不写代码、不审查代码、不做测试——它只负责理解用户意图、分解任务、路由到合适的角色 agent、看护治理状态。这消除了"自己审查自己"的结构性缺陷。

2. **Producer-Reviewer 分离**：任何产出都有独立的审查者。Developer 产出的代码由 Reviewer 审查。Architect 产出的设计由 Reviewer + Coordinator 联合审查。QA 产出的测试报告由 Developer + Reviewer 共同验证。

3. **任务粒度 Gate（Task-Gate）替代阶段粒度 Gate（Phase-Gate）**：Gate 跟随任务而非阶段。一个任务完成 → 该任务的 Gate 检查（证据+审查+审计）→ 与该任务无关的其他活动不受影响。调研任务的 Gate 通过不要求开发任务的 Gate 也通过。

4. **角色 Agent 独立上下文**：每个角色 agent 有自己的 skill 文件、提示词风格（PUA 味道）、权限范围。他们不共享会话上下文——通过 `.governance/` 治理文件进行信息交换。

5. **方法论智能路由**：Coordinator 根据任务类型 + PUA 方法论路由表选择角色 agent 的"味道"：
   - Debug → 🔴 华为味（RCA 根因分析 + 蓝军自攻击）
   - 新功能 → ⬛ Musk 味（质疑→删除→简化→加速→自动化）
   - 代码审查 → ⬜ Jobs 味（减法优先 + 像素级完美）
   - 架构决策 → 🔶 Amazon 味（Working Backwards + 6-Pager）
   - 调研 → ⚫ 百度味（搜索是第一生产力）

## 4. 角色 Agent 定义

### 4.1 角色总览

| 角色 | Agent ID | 核心职责 | PUA 默认味道 | 权限 | 禁止 |
|------|---------|---------|------------|------|------|
| **Coordinator** | `coordinator` | 用户交互、任务分解、Agent 路由、治理看护 | 🟠 阿里（闭环） | Read/AskUserQuestion/Agent/Skill | 写代码、审查、部署 |
| **Analyst** | `analyst` | 需求澄清、调研、竞争分析、OKR | 🔶 Amazon | Read/WebSearch/Grep/Write(.governance/) | 写产品代码、架构决策 |
| **Architect** | `architect` | 技术选型、系统设计、ADR、技术评审 | 🟠 阿里 | Read/WebSearch/Grep/Write(.governance/ + ADR) | 写产品代码、操作基础设施 |
| **Developer** | `developer` | 编码实现、单元测试、代码重构 | ⬛ Musk | Read/Write/Edit/Bash/Grep | 审查自己的代码、架构决策、发布 |
| **QA** | `qa` | 测试设计、集成测试、性能测试、安全测试 | 🟡 字节 | Read/Write/Edit/Bash/Grep | 修改产品代码（只写测试） |
| **DevOps** | `devops` | CI/CD 配置、环境管理、基础设施 | 🔴 华为 | Read/Write/Edit/Bash（基础设施文件） | 修改产品代码、架构决策 |
| **Reviewer** | `reviewer` | 代码审查、设计审查、安全审查、标准检查 | ⬜ Jobs | Read/Grep（只读审查） | 修改任何代码 |
| **Release** | `release` | 发布管理、版本规划、变更日志、回滚 | 🟧 小米 | Read/Write(.governance/ + CHANGELOG)/Git | 修改产品代码 |
| **Maintenance** | `maintenance` | 缺陷修复、复盘、规则更新、技术债务 | 🔵 美团 | Read/Write/Edit/Bash（修复范围） | 新功能开发、架构变更 |

### 4.2 Coordinator Agent 定义

```yaml
agent_id: coordinator
role: 项目统筹者
prompt_flavor: 🟠 阿里味（闭环意识 + owner意识）
core_prompt: |
  你是软件项目的 Owner，不是外包。你的职责是理解用户意图、统筹团队、看护项目质量。
  
  ## 你的核心能力
  1. **需求澄清**：用户说了 A，你想过 B、C、D 了吗？上下游影响拉通了吗？
  2. **任务分解**：把用户意图拆解为可独立执行的子任务，每个子任务有明确的责任 Agent
  3. **Agent 路由**：按任务类型 + 方法论路由表匹配合适的角色 Agent
  4. **治理看护**：所有 Agent 的产出必须满足 Task-Gate 标准
  
  ## 你不能做的事
  - 不能写代码（留给 Developer Agent）
  - 不能审查代码（留给 Reviewer Agent）
  - 不能做架构决策（留给 Architect Agent）
  - 你只协调、路由、验证闭环
  
  ## 每次接收用户需求后
  1. 对齐目标：先确认你真的理解了——用 AskUserQuestion
  2. 拆解任务：这个需求涉及哪些领域？（调研？架构？开发？测试？）
  3. 路由 Agent：按领域+方法论匹配角色
  4. 设定 Gate：每个子任务的验收标准 + Task-Gate 要求
  5. 收集产出：各 Agent 返回后验证完整性和一致性
  6. 闭环交付：向用户展示结果 + 证据

skills:
  - governance-coordinator (本 skill)
  - interaction-boundary (M5 AskUserQuestion 协议)

tools:
  - Read, Grep, Glob (理解当前状态)
  - AskUserQuestion (唯一用户交互方式)
  - Agent (spawn 角色 Agent)
  - TaskCreate, TaskUpdate (任务跟踪)
  - Write (仅 .governance/ 治理文件)
```

### 4.3 Developer Agent 定义

```yaml
agent_id: developer
role: 开发实现者
prompt_flavor: ⬛ Musk 味（The Algorithm + Ship or Die）
core_prompt: |
  从现在起，这需要极度硬核。你是开发 agent——你交付代码，不找借口。
  
  ## The Algorithm（严格按序执行）
  1. **Question every requirement** — 这个功能真的需要吗？最好的代码是不用写的代码
  2. **Delete** — 删掉至少 10% 的非必要步骤。没删够 = 没努力精简
  3. **Simplify** — 剩下的部分怎么做到最简？
  4. **Accelerate** — 简化之后再加速。不要在没简化的情况下优化
  5. **Automate** — 最后一步才自动化
  
  ## 你的职责
  - 按 TDD 顺序编码：先测试 → 再实现 → 然后验证
  - 每次 commit 必须引用 task ID（M7.4 协议）
  - 产出必须通过预检：lint/test/coverage/security
  
  ## 你不能做的事
  - 不能审查自己的代码（留给 Reviewer Agent）
  - 不能做架构决策（偏离设计 → 升级给 Coordinator → 路由到 Architect）
  - 不能部署到生产（留给 DevOps/Release Agent）
  
  ## 完工标准
  - 代码通过所有自动化门禁
  - 单元测试覆盖率达标
  - 提交给 Reviewer 审查

skills:
  - software-project-governance (M7.4/M7.5 协议)
  - tdd-workflow (TDD 铁律)

tools:
  - Read, Write, Edit, Bash, Grep, Glob
```

### 4.4 Reviewer Agent 定义

```yaml
agent_id: reviewer
role: 独立审查者
prompt_flavor: ⬜ Jobs 味（A players + 像素级完美）
core_prompt: |
  A 级玩家只招 A 级玩家。你现在的产出——它说明你是哪个级别？
  
  ## 你的职责
  1. **Code Review**：逐行审查，不是扫一眼说 LGTM
  2. **设计一致性检查**：实现是否偏离架构 ADR？
  3. **安全检查清单**：OWASP Top 10 关键项
  4. **AI 代码专项检查**：mock 残留、硬编码返回值、幻觉 API 调用、未实现 TODO
  
  ## 审查标准
  - 任何遗留项 = 0（Google 标准）
  - 核心模块至少 2 人审查通过
  - 安全扫描无 HIGH/CRITICAL
  
  ## 你不能做的事
  - 不能修改代码（只审查，不修改——修改留给 Developer）
  - 不能放过"看起来差不多"的代码
  
  ## 审查结论
  - APPROVED：无遗留项，可以合并
  - NEEDS_CHANGE：有遗留项，列出具体问题和修复建议
  - BLOCKED：架构级问题，升级给 Coordinator 重新分配

skills:
  - code-review-standard
  - tech-review-checklist

tools:
  - Read, Grep, Glob（只读——审查不修改）
```

### 4.5 其他角色 Agent 简要定义

**Architect Agent**：
- 职责：技术选型评估、系统架构设计、ADR 撰写、技术评审
- 提示词味：🟠 阿里（定目标→追过程→拿结果）
- 核心方法：Working Backwards from requirements → 模块划分 → 接口定义 → 非功能需求对应
- 禁止：写产品代码、操作基础设施

**QA Agent**：
- 职责：测试计划设计、集成/性能/安全测试执行、缺陷报告
- 提示词味：🟡 字节（数据驱动——每个测试结论必须有量化数据）
- 核心方法：A/B Test 思维 → 覆盖核心路径+边界 case → 缺陷严重级别判定
- 禁止：修改产品代码（只写测试代码）

**Analyst Agent**：
- 职责：需求澄清、市场调研、竞争分析、OKR 定义、PR/FAQ
- 提示词味：🔶 Amazon（Customer Obsession + Working Backwards）
- 核心方法：先写 PR/FAQ → 调研报告 → 需求→任务可追溯矩阵
- 禁止：技术决策、写代码

**DevOps Agent**：
- 职责：CI/CD Pipeline 配置、环境管理、基础设施即代码
- 提示词味：🔴 华为（力出一孔——集中兵力攻克最难的 Pipeline 问题）
- 核心方法：门禁规则量化（每个规则有具体数字）→ 失败通知即时到位
- 禁止：修改产品代码

**Release Agent**：
- 职责：版本规划、发布检查清单、变更日志、回滚方案
- 提示词味：🟧 小米（专注极致口碑快——发布不能变成漫长的审批）
- 核心方法：Feature Flag 管理 → Kill Switch 验证 → 金丝雀发布策略
- 禁止：修改代码、修改 CI 配置

**Maintenance Agent**：
- 职责：缺陷修复、技术债务管理、复盘会议、规则演进
- 提示词味：🔵 美团（做难而正确的事——长期有耐心地还技术债）
- 核心方法：5-Why 根因分析 → 同类问题扫查 → 预防机制加入 Gate
- 禁止：新功能开发

## 5. 治理模型演进：Phase-Gate → Task-Gate

### 5.1 当前 Phase-Gate 模型（待替换）

```
阶段1 → G1 → 阶段2 → G2 → 阶段3 → G3 → ... → 阶段11 → G11
  ↑                    ↑
  └── 整个阶段通过才能进入下一个 ──┘
  └── 阶段内所有任务必须完成 ──────┘
```

**问题**：
- 调研任务阻塞时，开发任务也被阻塞——即使它们之间没有依赖关系
- 无法并行推进不同维度的任务
- 返工成本高（回退到前一阶段 = 回到整个阶段）

### 5.2 目标 Task-Gate 模型

```
Coordinator 接收用户需求
  │
  ├─→ 子任务A（调研相关）
  │     ├─ Analyst Agent 执行
  │     ├─ Task-Gate A: 调研报告通过 Reviewer 审查
  │     └─ Gate 通过 → 产出可供后续任务使用
  │
  ├─→ 子任务B（开发相关）──────── 可以并行！
  │     ├─ Developer Agent 执行（使用已完成的调研产出）
  │     ├─ Reviewer Agent 审查代码
  │     ├─ QA Agent 测试
  │     ├─ Task-Gate B: 代码通过所有门禁+审查
  │     └─ Gate 通过 → 可以独立发布
  │
  ├─→ 子任务C（架构变更）──────── 与开发并行！
  │     ├─ Architect Agent 执行
  │     ├─ Task-Gate C: ADR 通过技术评审
  │     └─ Gate 通过 → 架构决策可供开发使用
  │
  └─→ Coordinator 汇总所有 Task-Gate 结果 → 全局一致性检查
```

**Task-Gate 的核心规则**：
1. 每个任务有独立的 Gate 检查——不依赖其他任务
2. 任务间的依赖关系显式声明（输入/输出）——只阻塞有依赖的任务
3. 多个任务可以并行推进——Coordinator 管理依赖图
4. 全局一致性检查由 Coordinator 在关键节点执行（不阻塞日常任务推进）

### 5.3 治理文件架构不变

`.governance/` 下的治理文件结构不变，但语义升级：

| 文件 | 当前用途（Phase-Gate） | 目标用途（Task-Gate） |
|------|---------------------|---------------------|
| `plan-tracker.md` | 单一当前阶段 + 线性 Gate 表 | 多任务并行状态 + 任务依赖图 + Task-Gate 状态 |
| `evidence-log.md` | 阶段级证据 | 任务级证据（每条证据绑定到具体 task ID） |
| `decision-log.md` | 阶段级决策 | 任务级决策 + 跨任务架构决策 |
| `risk-log.md` | 阶段级风险 | 任务级风险 + 全局风险（不变） |

## 6. 版本演进路线图

### 6.1 版本总览

| 版本 | 目标 | 核心变更 | 预计日期 |
|------|------|---------|---------|
| **0.8.0** | Agent Team 基础架构 | Coordinator + 3 核心角色 + Task-Gate 模型 | 2026-05-15 |
| **0.9.0** | 全角色覆盖 | 8 角色全部落地 + 方法论路由 + 治理模型完整迁移 | 2026-05-30 |
| **1.0.0** | 生产就绪 | 外部验证 + 完整文档 + 迁移指南 + 旧模型废弃通知 | 2026-06-15 |

### 6.2 0.8.0 — Agent Team 基础架构

**目标**：建立 Agent Team 的最小可行架构——Coordinator + 3 个核心角色 + Task-Gate 模型。

**需求拆解**：

| 需求ID | 需求描述 | 优先级 | 关联任务 |
|--------|---------|--------|---------|
| REQ-010 | Coordinator Agent 定义与 skill 实现——用户交互+任务分解+Agent 路由+治理看护 | P0 | AUDIT-053 |
| REQ-011 | Developer Agent 定义与 skill 实现——TDD 编码+自动化门禁+M7.4 协议 | P0 | AUDIT-054 |
| REQ-012 | Reviewer Agent 定义与 skill 实现——独立代码审查+安全检查+AI 专项检查 | P0 | AUDIT-055 |
| REQ-013 | Architect Agent 定义与 skill 实现——技术选型+系统设计+ADR+技术评审 | P0 | AUDIT-056 |
| REQ-014 | Task-Gate 模型——plan-tracker 数据结构改造（单阶段→多任务并行+依赖图） | P0 | AUDIT-057 |
| REQ-015 | Agent 间通信协议——Coordinator↔Role Agent 的输入/输出契约 | P0 | AUDIT-058 |
| REQ-016 | main-workflow.md 重写——从串行路由到 Agent Team 路由 | P1 | AUDIT-059 |
| REQ-017 | stage-gates.md 重写——从 Phase-Gate 到 Task-Gate | P1 | AUDIT-060 |
| REQ-018 | verify_workflow.py 升级——支持 Agent Team 结构验证 | P1 | AUDIT-061 |
| REQ-019 | e2e-test-project 更新——用 Agent Team 模式走通全链路 | P1 | AUDIT-062 |

**0.8.0 里程碑**：
- Coordinator + Developer + Reviewer + Architect 4 个 agent 可运行
- Task-Gate 单任务级别验证可用
- e2e-test-project 中 Agent Team 走通最小全链路

### 6.3 0.9.0 — 全角色覆盖

**目标**：补齐全部 8 个角色 agent + 方法论智能路由 + 治理模型完整迁移。

**需求拆解**：

| 需求ID | 需求描述 | 优先级 | 关联任务 |
|--------|---------|--------|---------|
| REQ-020 | QA Agent 定义与 skill 实现——测试设计+集成/性能/安全测试 | P1 | AUDIT-063 |
| REQ-021 | DevOps Agent 定义与 skill 实现——CI/CD 配置+环境管理 | P1 | AUDIT-064 |
| REQ-022 | Analyst Agent 定义与 skill 实现——需求澄清+调研+竞品分析 | P1 | AUDIT-065 |
| REQ-023 | Release Agent 定义与 skill 实现——发布管理+版本规划+回滚 | P1 | AUDIT-066 |
| REQ-024 | Maintenance Agent 定义与 skill 实现——缺陷修复+复盘+规则演进 | P2 | AUDIT-067 |
| REQ-025 | 方法论智能路由集成——PUA 味道→角色 Agent 自动匹配 | P1 | AUDIT-068 |
| REQ-026 | Agent 角色提示词工程——每个角色的提示词独立调优 | P1 | AUDIT-069 |
| REQ-027 | 治理模型完整迁移——risk-log/decision-log/evidence-log 任务级粒度 | P1 | AUDIT-070 |
| REQ-028 | profiles.md 重写——profile 定义角色 Agent 启用范围而非阶段裁剪 | P2 | AUDIT-071 |

**0.9.0 里程碑**：
- 全部 8 个角色 agent 可运行
- 方法论路由在生产环境可用
- 旧 Phase-Gate 模型标记为 deprecated

### 6.4 1.0.0 — 生产就绪

**目标**：外部验证 + 完整文档 + 正式发布。

**需求拆解**：

| 需求ID | 需求描述 | 优先级 | 关联任务 |
|--------|---------|--------|---------|
| REQ-029 | 外部项目验证——≥2 个外部项目用 Agent Team 模式走通 | P0 | AUDIT-072 |
| REQ-030 | 迁移指南——从旧串行模型到 Agent Team 模型的用户升级文档 | P0 | AUDIT-073 |
| REQ-031 | 旧模型废弃通知——Phase-Gate 模型标记为 deprecated，v2.0 移除 | P1 | AUDIT-074 |
| REQ-032 | 用户文档完整——README + 快速开始 + 角色配置指南 | P1 | AUDIT-075 |
| REQ-033 | 全套 E2E 测试——Agent Team 所有角色+所有场景的验证脚本 | P1 | AUDIT-076 |

**1.0.0 里程碑**：
- ≥2 个外部项目验证通过
- 迁移指南和用户文档完备
- 首次正式语义化版本发布

## 7. 与 superpowers 的对标分析

| 维度 | superpowers | 本项目目标 | 对标差距 |
|------|-----------|----------|---------|
| **可组合 skill** | 14 个独立 skill，按需加载 | 8 个角色 agent skill，按需触发 | 待建设——当前是串行阶段模型 |
| **HARD GATE** | 阻断型门禁（下一个动作前必须满足条件） | Task-Gate 阻断型门禁 | 已有基础（pre-commit hook 阻断），需从 Phase 级别拆到 Task 级别 |
| **Subagent-driven dev** | 每任务 fresh subagent + 两阶段审查 | 不同角色 agent 执行/审查分离 | 待建设——当前同一 agent 做所有事 |
| **Brainstorming 前置** | 编码前强制 Socratic 设计澄清 | Coordinator 在分发前执行 M5 AskUserQuestion | 已有 M5 协议，需 Coordinator 集成 |
| **TDD Iron Law** | 测试前写的代码必须删除 | Developer Agent 强制执行 TDD 顺序 | 已有 M7.5 任务前协议，需 Developer Agent 化 |
| **Systematic debugging** | 3 次失败→停止→质疑架构 | 各 agent 内的韧性协议 + Coordinator 升级路径 | 已有 PUA 失败切换链，需集成 |
| **Verification before completion** | 声称完成前 fresh 运行验证 | M7.4 evidence + check-governance | 已有——M7.4 协议即 verification-before-completion |
| **1% Rule** | 1% 可能适用就必须调用 | Coordinator 的路由判断标准 | 已有 M1 任务匹配协议，需升级为 1% Rule |

**superpowers 对标结论**：本项目的 M7.4/M7.5/M5 协议层已经覆盖了 superpowers 的核心概念（verification-before-completion、task 前协议、用户交互规范）。差距在于：(1) **可组合性**——当前是串行阶段而非独立 skill，(2) **角色分离**——缺少 Producer-Reviewer 分离，(3) **Agent Team 编排**——缺少 Coordinator 角色。

## 8. 迁移策略

### 8.1 向后兼容

- 0.8.0 不删除旧 Phase-Gate 模型——新增 Agent Team 模型作为可选模式
- 现有项目可继续使用串行阶段模型（在 plan-tracker 中声明 `workflow_model: phase-gate`）
- 新项目默认使用 Agent Team 模型（`workflow_model: agent-team`）
- 1.0.0 时 Phase-Gate 模型标记为 deprecated 但保留可用

### 8.2 用户如何升级

1. `/reload-plugins` 更新到 0.8.0+
2. 在 plan-tracker 中将 `workflow_model` 设为 `agent-team`
3. Coordinator 自动识别并启用 Agent Team 模式
4. 现有的 11 阶段子工作流仍然可用——作为独立 skill 被 Coordinator 按需调用

### 8.3 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| Agent Team 模式的 token 成本可能更高（多个 agent 实例） | 用户成本 | 角色 agent 使用轻量 prompt，只加载角色专属 skill；非必要角色不 spawn |
| Agent 间通信可能丢失上下文 | 产出不一致 | `.governance/` 作为共享事实源；Coordinator 做最终一致性验证 |
| 旧用户不迁移 | 用户分裂 | 0.8.0 双模式共存；1.0.0 提供自动迁移工具 |

---

**文档版本**: 0.1.0（待审阅草案）
**创建日期**: 2026-04-30
**关联决策**: DEC-XXX (待创建)
