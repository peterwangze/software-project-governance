# 六层架构设计

## 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                   外部 AI CLI 平台                        │
│   Claude Code  │  Codex  │  Gemini  │  国内 Agent CLI     │
└──────────────────────────┬──────────────────────────────┘
                           │ 通过平台原生机制加载
┌──────────────────────────▼──────────────────────────────┐
│                    适配层（Adapter）                       │
│  ┌───────────────────────────────────────────────────┐  │
│  │  平台投影：plugin.json / manifest.json / launch     │  │
│  │  每平台一个 adapter，声明 inputs/outputs/validation  │  │
│  │  不包含工作流逻辑——纯投影/翻译层                      │  │
│  │  依赖入口层 —— 单向依赖，不可反向                     │  │
│  └───────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────┘
                           │ 加载（单向依赖）
┌──────────────────────────▼──────────────────────────────┐
│                    入口层（Entry）                         │
│  主 SKILL.md（仅引导进入 Coordinator）                    │
│  Coordinator Agent（直接由主 agent 加载）                  │
└──────────────────────────┬──────────────────────────────┘
                           │ 加载并成为（单向依赖）
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
适配层 → 入口层 → 业务智能层 → 能力层 → 基础设施层 → 核心层
```

**单向依赖，不可反向。** 上层可以依赖下层，下层 MUST NOT 依赖上层。核心层是最底层基础，适配层是最顶层投影。

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

**不包含**：任何 agent 角色定义、执行步骤、工具调用指令、平台特定文件。

### 基础设施层——脚本/工具/MCP

**是什么**：可被能力层或业务智能层调用的通用能力。不依赖 LLM，独立可执行。

**依赖**：核心层（引用合约定义）

**被谁依赖**：能力层、业务智能层

**包含**：
- Git hooks（pre-commit, post-commit, prepare-commit-msg）
- 验证引擎（verify_workflow.py）
- 治理检查脚本（check-governance）
- MCP 服务
- 通用工具索引（TOOLS.md）

**原则**：(a) 独立可执行，(b) 有明确的输入输出契约，(c) 不依赖 agent 上下文。

### 能力层——SKILL 库（确定性步骤）

**是什么**：标准 SKILL 格式（frontmatter + 触发条件 + 执行流程 + 步骤清单）。只处理一类明确事务，步骤明确，不依赖 LLM 的判断能力。**系统的"能力原子"——业务智能层的 Agent 通过组合这些能力来完成复杂任务。**

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

**是什么**：有角色定位和 persona 的智能体。可以有判断和决策能力，通过组合能力层的多个 SKILL 来完成复杂任务。**系统的"决策中枢"——决定做什么、怎么做、谁来做。**

**依赖**：能力层（调用 SKILL）+ 基础设施层（直接调用工具）

**被谁依赖**：入口层（加载 Coordinator Agent）

**特征**：
- 角色 persona（"你是老周，一个..."）
- 专门提示词（角色定位 + 擅长 + 痛恨 + 职责范围）
- 工具权限声明（哪些工具可用/禁用）
- 可调用多个 SKILL（"当你需要做代码审查时，加载 code-review SKILL"）
- 动态组合（一个工作流可以有多个 Agent 参与）
- **有判断权**——在能力层提供的确定性步骤之上做决策

**Agent 职能分组**（7 组 9 Agent，按项目运作职能组织）：

| 职能组 | Agent | 生命周期覆盖 | 可调用的 SKILL |
|--------|-------|------------|---------------|
| **管理组** | Coordinator | 全流程——统筹调度 | 所有 SKILL（通过路由分发） |
| **设计组** | Analyst, Architect | 立项→调研→选型→架构设计 | 需求澄清, 竞品分析, PR/FAQ, OKR, 6-Pager, 技术选型, 架构设计, ADR, 技术评审 |
| **开发组** | Developer | 开发实现 | 开发, TDD, 环境搭建 |
| **测试组** | QA | 测试与质量保障 | 测试设计, 集成测试, 性能测试 |
| **评审组** | Reviewer | 全流程——独立审查 | 代码审查, 技术评审, 安全审查 |
| **运维组** | DevOps, Release | CI/CD→发布→运营 | CI/CD, 环境管理, 发布检查, 版本规划, 变更日志 |
| **维护组** | Maintenance | 维护与演进 | 缺陷修复, 复盘会议, 规则演进 |

> 目录结构：`agents/{管理组/设计组/开发组/测试组/评审组/运维组/维护组}/{agent名}/SKILL.md`

### 入口层——引导进入业务智能层

**是什么**：主 SKILL.md，仅做一件事——声明"加载 Coordinator Agent，进入 Agent Team 模式"。不包含任何行为规则，不包含任何执行步骤。

**依赖**：业务智能层（加载 Coordinator Agent）

**被谁依赖**：适配层（各平台 adapter 指向此入口）

**内容**：
- 激活流程（4 步）
- 工作流合约引用
- Coordinator 参考知识表
- 治理基础设施列表
- SKILL 库入口

### 适配层——平台投影

**是什么**：将工作流映射到具体 AI CLI 平台的投影层。每个平台有自己的 plugin manifest、bootstrap 文件、launcher 和版本声明。**不包含任何工作流逻辑——纯投影/翻译。**

**依赖**：入口层（指向 SKILL.md 作为加载入口）

**被谁依赖**：外部 AI CLI 平台（通过平台原生插件机制）

**每平台最小资产**：

| 资产 | 作用 | 示例（Claude Code） |
|------|------|-------------------|
| plugin manifest | 声明 plugin id、版本、入口 | `.claude-plugin/plugin.json` |
| marketplace manifest | 声明 marketplace 元数据 | `.claude-plugin/marketplace.json` |
| adapter manifest | 声明 inputs/outputs/validation/read_order | `adapters/claude/adapter-manifest.json` |
| launcher | 验证加载顺序、执行预检 | `adapters/claude/launch.py` |
| bootstrap 模板 | 平台原生入口的**模板**（注入用户项目用） | `commands/governance-init.md` Step 7 |
| adapter README | 平台特定说明 | `adapters/claude/README.md` |

> **注意**：仓库不包含任何平台原生入口文件（如 Claude Code 的 `CLAUDE.md`）——这些是各平台用户项目的本地配置文件，类似于 `.gitignore`、IDE 配置。适配层提供的产品资产是 bootstrap 模板机制（定义在 `commands/governance-init.md`），用于在用户项目中生成其平台对应的入口文件。

**adapter manifest 标准字段**（每个 adapter 必须回答）：

```json
{
  "adapter_id": "平台标识",
  "workflow_id": "software-project-governance",
  "entry_type": "加载方式",
  "supported_runtime": ["支持的运行时列表"],
  "trigger": ["触发条件"],
  "inputs": ["加载的文件列表"],
  "outputs": ["回写的文件列表"],
  "gate_behavior": {
    "on_fail": "block-next-stage",
    "required_action": "update-risk-or-decision-log"
  },
  "validation": {
    "command": "校验命令",
    "required": true
  },
  "native_entry": {
    "repository_entry": "平台原生入口文件名",
    "skill_path": "skills/software-project-governance/SKILL.md"
  },
  "launcher": "launcher 脚本路径"
}
```

**当前支持的平台**：

| 平台 | 状态 | adapter 目录 | plugin 目录 |
|------|------|-------------|------------|
| Claude Code | 主线（已实现） | `adapters/claude/` | `.claude-plugin/` |
| Codex | 预研（样例） | `adapters/codex/` | `.codex-plugin/` |
| Gemini | 兼容分析（文档） | `adapters/gemini/` | — |
| 国内 Agent CLI | 兼容分析（文档） | — | `.agents/` |

**新增平台的标准流程**：
1. 阅读 `skills/software-project-governance/core/protocol/plugin-contract.md` 六项准入问题
2. 创建 `adapters/<platform>/` 目录
3. 编写 `adapter-manifest.json`（回答所有标准字段）
4. 编写 `launch.py`（验证加载顺序）
5. 创建平台原生 plugin/packaging 文件
6. 不修改核心层到入口层的任何文件

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

## 入口层 vs 适配层（关键区分）

| 维度 | 入口层 | 适配层 |
|------|--------|--------|
| **本质** | 工作流的"前门" | 平台的"翻译器" |
| **内容** | 工作流激活指令 | 平台原生格式的投影文件 |
| **数量** | 1 个入口 | N 个 adapter（每平台 1 个） |
| **依赖方向** | → 业务智能层 | → 入口层 |
| **谁维护** | 工作流开发者 | 平台接入者 |
| **变更频率** | 随工作流演进 | 随平台能力变化 |
| **示例** | `SKILL.md` | `plugin.json` + `平台原生入口文件` |

## 与协议层概念的对齐

本六层架构与 `skills/software-project-governance/core/protocol/plugin-contract.md` 的三层承载模型完全对齐：

| 三层承载模型 | 六层架构映射 | 说明 |
|-------------|------------|------|
| Workflow 本体层 | 核心层 + 基础设施层 + 能力层 + 业务智能层 | "工作流本身"——从合约到 Agent |
| Agent 入口投影层 | 入口层 | 主 SKILL.md——引导进入 Coordinator |
| 外部能力层 | 适配层 | 平台原生格式——plugin.json / manifest / bootstrap |

之前的混淆在于把"入口层"当成了"入口投影层"的全部——实际上入口投影还包括适配层的平台原生文件（平台原生入口文件、plugin.json）。六层架构明确了这一区分：入口层是工作流内部的，适配层是平台外部的。

## 当前资产映射

### 核心层映射

| 当前文件 | 目标位置 | 说明 |
|---------|---------|------|
| `protocol/*.md` | `core/protocol/` | 保持不变 |
| `workflows/software-project-governance/templates/` | `core/templates/` | 保持不变 |
| `skills/software-project-governance/core/manifest.md` | `core/manifest.md` | 工作流身份声明 |
| `core/lifecycle.md` | `core/lifecycle.md` | ✅ 已迁移（从 references/） |
| `core/stage-gates.md` | `core/stage-gates.md` | ✅ 已迁移 |
| `core/profiles.md` | `core/profiles.md` | ✅ 已迁移 |
| `core/onboarding.md` | `core/onboarding.md` | ✅ 已迁移 |
| `core/audit-framework.md` | `core/audit-framework.md` | ✅ 已迁移 |
| `core/task-gate-model.md` | `core/task-gate-model.md` | ✅ 已迁移 |
| `core/VERSIONING.md` | `core/VERSIONING.md` | ✅ 已迁移（从根目录） |

### 基础设施层映射

| 当前文件 | 目标位置 | 说明 |
|---------|---------|------|
| `infra/hooks/pre-commit` | `infra/hooks/pre-commit` | ✅ 已迁移（从 scripts/） |
| `infra/hooks/post-commit` | `infra/hooks/post-commit` | ✅ 已迁移 |
| `infra/hooks/prepare-commit-msg` | `infra/hooks/prepare-commit-msg` | ✅ 已迁移 |
| `infra/verify_workflow.py` | `infra/verify_workflow.py` | ✅ 已迁移（从 scripts/） |
| `TOOLS.md` | `infra/TOOLS.md` | 待迁移（仍在 references/ 旁） |

### 能力层（SKILL）映射

| 当前文件 | 目标位置 | 类别 |
|---------|---------|------|
| `commands/governance-init.md` | `skills/init/` | 项目初始化 |
| `commands/software-project-governance.md` | `skills/unified-entry/` | 统一入口 |
| `commands/governance-status.md` | `skills/status/` | 治理命令 |
| `commands/governance-gate.md` | `skills/gate-check/` | 治理命令 |
| `commands/governance-verify.md` | `skills/verify/` | 治理命令 |
| `commands/governance-update.md` | `skills/upgrade/` | 治理命令 |
| `skills/stage-initiation/SKILL.md` | `skills/stage-initiation/` | 阶段工作流 |
| `skills/stage-research/SKILL.md` | `skills/stage-research/` | 阶段工作流 |
| `skills/stage-selection/SKILL.md` | `skills/stage-selection/` | 阶段工作流 |
| `skills/stage-infra/SKILL.md` | `skills/stage-infra/` | 阶段工作流 |
| `skills/stage-architecture/SKILL.md` | `skills/stage-architecture/` | 阶段工作流 |
| `skills/stage-development/SKILL.md` | `skills/stage-development/` | 阶段工作流 |
| `skills/stage-testing/SKILL.md` | `skills/stage-testing/` | 阶段工作流 |
| `skills/stage-cicd/SKILL.md` | `skills/stage-cicd/` | 阶段工作流 |
| `skills/stage-release/SKILL.md` | `skills/stage-release/` | 阶段工作流 |
| `skills/stage-operations/SKILL.md` | `skills/stage-operations/` | 阶段工作流 |
| `skills/stage-maintenance/SKILL.md` | `skills/stage-maintenance/` | 阶段工作流 |
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
| `agents/management/coordinator/SKILL.md` | `agents/management/coordinator/SKILL.md` | 保持 |
| `agents/development/developer/SKILL.md` | `agents/development/developer/SKILL.md` | 保持 |
| `agents/review/reviewer/SKILL.md` | `agents/review/reviewer/SKILL.md` | 保持 |
| `agents/design/architect/SKILL.md` | `agents/design/architect/SKILL.md` | 保持 |
| `agents/testing/qa/SKILL.md` | `agents/testing/qa/SKILL.md` | 保持 |
| `agents/operations/devops/SKILL.md` | `agents/operations/devops/SKILL.md` | 保持 |
| `agents/design/analyst/SKILL.md` | `agents/design/analyst/SKILL.md` | 保持 |
| `agents/operations/release/SKILL.md` | `agents/operations/release/SKILL.md` | 保持 |
| `agents/maintenance/maintenance/SKILL.md` | `agents/maintenance/maintenance/SKILL.md` | 保持 |

### 入口层映射

| 当前文件 | 变更 |
|---------|------|
| `SKILL.md` | ✅ 已瘦身为入口：46 行，仅声明"加载 Coordinator Agent" |

### 适配层映射

| 当前文件 | 平台 | 说明 |
|---------|------|------|
| `adapters/claude/adapter-manifest.json` | Claude Code | adapter 标准字段声明 |
| `adapters/claude/launch.py` | Claude Code | 加载顺序验证 |
| `adapters/claude/README.md` | Claude Code | 平台特定说明 |
| `.claude-plugin/plugin.json` | Claude Code | plugin manifest |
| `.claude-plugin/marketplace.json` | Claude Code | marketplace 元数据 |
| `commands/governance-init.md` Step 7 | 所有平台 | bootstrap 模板（注入用户项目的 canonical source） |
| `adapters/codex/adapter-manifest.json` | Codex | 预研 |
| `adapters/codex/launch.py` | Codex | 预研 |
| `adapters/codex/README.md` | Codex | 预研 |
| `.codex-plugin/plugin.json` | Codex | plugin manifest |
| `adapters/gemini/README.md` | Gemini | 兼容分析 |
| `.agents/plugins/marketplace.json` | 国内 Agent CLI | 兼容分析 |

## 需求拆解

### P0（必须——架构正确性）

| ID | 需求 | 工作量 | 状态 |
|----|------|--------|------|
| REQ-041 | 主 SKILL.md 瘦身为入口 | 小 | ✅ 已完成 |
| REQ-042 | 建立统一的能力层（SKILL）目录结构 | 中 | 待实施 |
| REQ-043 | 统一 SKILL 格式 | 中 | 待实施 |
| REQ-044 | 迁移 stages/ 和 commands/ 到能力层 skills/ | 大 | 待实施 |
| REQ-045 | 分离核心层文件到 core/ 目录 | 中 | 🔄 文件已移动，引用待更新 |
| REQ-046 | 建立基础设施层目录结构 infra/ | 小 | 🔄 文件已移动，引用待更新 |
| REQ-052 | 适配层正式纳入架构——adapter 标准字段 + 新增平台流程 | 小 | 待实施 |

### P1（重要——可用性）

| ID | 需求 | 工作量 |
|----|------|--------|
| REQ-047 | 每个 Agent 声明可调用的 SKILL 列表——Agent→SKILL 绑定 | 中 |
| REQ-048 | 建立 SKILL 分类索引 | 小 |
| REQ-049 | references/ 清理——核心层已移出，参考文档保留 | 中 |

### P2（增强）

| ID | 需求 | 工作量 |
|----|------|--------|
| REQ-050 | 建立统一的工具/MCP 库索引——infra/TOOLS.md | 小 |
| REQ-051 | verify_workflow.py 适配新目录结构 | 中 |
| REQ-053 | adapter 标准字段校验——verify_workflow.py 检查 adapter-manifest.json 完整性 | 小 |

## 实施分步

### Phase 1: 主 SKILL.md 瘦身（P0, ✅ 已完成）
1. ✅ 将主 SKILL.md 从 487 行行为协议瘦身为 46 行入口
2. ✅ 创建 references/behavior-protocol.md 保存 M0-M9 强制性规则
3. ✅ verify_workflow.py snippets 同步更新

### Phase 2: 核心层和基础设施层建立（P0, 🔄 进行中）
4. ✅ 创建 core/ 目录，移入 lifecycle/stage-gates/profiles/onboarding/audit-framework/VERSIONING/task-gate-model
5. ✅ 创建 infra/ 目录，移入 hooks/ 和 verify_workflow.py
6. ⬜ 更新全仓路径引用（~30 个文件）
7. ⬜ verify_workflow.py 适配新路径

### Phase 3: 能力层（SKILL）建立和迁移（P0）
8. 创建统一的 skills/ 目录结构
9. 将 stages/ 下的 SKILL 迁移到 skills/
10. 将 commands/ 下的 SKILL 迁移到 skills/
11. 统一所有 SKILL 格式

### Phase 4: 业务智能层（Agent）升级 + 适配层正式化（P1）
12. 为每个 Agent 添加"可调用的 SKILL"列表
13. 建立 SKILL 分类索引
14. 适配层标准字段文档化（adapter-manifest.json schema）
15. 新增平台 checklist 文档化

### Phase 5: 验证和发布（P2）
16. verify_workflow.py 适配新结构
17. adapter 标准字段校验
18. 版本 bump + CHANGELOG
19. E2E 验证

## 目标目录结构

```
skills/software-project-governance/
  SKILL.md                        ← 入口层（仅引导进入 Coordinator）
  agents/                         ← 业务智能层（Agent 库）
    coordinator/SKILL.md
    management/                   ← 管理组
      coordinator/SKILL.md
    design/                       ← 设计组
      analyst/SKILL.md
      architect/SKILL.md
    development/                  ← 开发组
      developer/SKILL.md
    testing/                      ← 测试组
      qa/SKILL.md
    review/                       ← 评审组
      reviewer/SKILL.md
    operations/                   ← 运维组
      devops/SKILL.md
      release/SKILL.md
    maintenance/                  ← 维护组
      maintenance/SKILL.md
  skills/                         ← 能力层（SKILL 库）
    init/SKILL.md
    onboarding/SKILL.md
    upgrade/SKILL.md
    status/SKILL.md
    gate-check/SKILL.md
    verify/SKILL.md
    stage-initiation/SKILL.md
    ...（其余阶段和技能 SKILL）
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
      pre-commit
      post-commit
      prepare-commit-msg
    verify_workflow.py
    TOOLS.md
  references/                     ← 参考知识（Coordinator 按需读取）
    behavior-protocol.md
    four-layer-architecture.md（本文件——六层架构设计）
    agent-team-architecture.md
    agent-failure-modes.md
    interaction-boundary.md
    methodology-routing.md
    agent-communication-protocol.md
    user-perspective-principle.md
    data-boundary.md
    agent-entry-differences.md
    company-practices-summary.md

adapters/                         ← 适配层（平台投影）
  claude/
    adapter-manifest.json
    launch.py
    README.md
  codex/
    adapter-manifest.json
    launch.py
    README.md
  gemini/
    README.md

.claude-plugin/                   ← 适配层（Claude Code 插件包）
  plugin.json
  marketplace.json
.codex-plugin/                    ← 适配层（Codex 插件包）
  plugin.json
.agents/                          ← 适配层（国内 Agent CLI）
  plugins/marketplace.json
```

## 架构演进原则

1. **新增 AI CLI 平台**：在适配层新增 adapter 目录 + plugin 包，不修改核心层到入口层的任何文件
2. **新增阶段/技能**：在能力层新增 SKILL 文件，在业务智能层声明 Agent 可调用新 SKILL
3. **新增 Agent 角色**：在业务智能层新增 Agent 目录，声明 persona + 工具权限 + 可调用 SKILL 列表
4. **新增工具/脚本**：在基础设施层新增，被能力层和业务智能层按需调用
5. **修改工作流规则**：在核心层修改合约定义，向上逐层验证兼容性
6. **任何层的修改不能跳层依赖**：核心层不能引用基础设施层的具体实现，能力层不能依赖业务智能层的 persona
