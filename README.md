# Software Project Governance

> 让 coding agent 帮你看护项目质量——你只负责思考，过程管理全自动。

## 一句话说明

你的 AI 编程助手（Claude / Codex / 其他）安装这个工作流后，会自动帮你做这些事：

- 每完成一个任务，**自动记录证据**（改了什么、为什么改、怎么验证的）
- 每推进一个阶段，**自动检查 Gate**（有没有遗漏、质量达标没）
- 遇到方向选择时，**帮你列出选项和后果**，你做判断
- 风险、决策、计划变更——**全程留痕，可复盘**

你不需要手动维护项目文档、不需要记住"上次做到哪了"、不需要提醒自己"该做 code review 了"。

## 安装

### Claude Code

```bash
# 方式一：通过插件市场安装（推荐）
/plugin install peterwangze/software-project-governance

# 方式二：克隆到本地后安装
git clone https://github.com/peterwangze/software-project-governance.git
cd your-project
/plugin install /path/to/software-project-governance
```

安装后，工作流会在每次会话自动加载。你不需要做任何额外配置。

### Codex

```bash
# 在项目根目录安装
git clone https://github.com/peterwangze/software-project-governance.git
# Codex 会自动识别 .codex-plugin/plugin.json
```

### 其他 agent（Gemini、国内 agent CLI 等）

1. 克隆本仓库到本地
2. 将 `skills/software-project-governance/SKILL.md` 的内容加载到你的 agent 配置中
3. 确保 agent 能访问仓库中的以下文件（SKILL.md 会按顺序读取它们）：
   - `workflows/software-project-governance/manifest.md`
   - `protocol/workflow-schema.md`、`plugin-contract.md`
   - `workflows/software-project-governance/rules/`（lifecycle、stage-gates、profiles、onboarding、interaction-boundary）
   - `workflows/software-project-governance/templates/`（plan-tracker、evidence-log、decision-log、risk-log）
   - `workflows/software-project-governance/examples/`（治理记录事实源）
   - `workflows/software-project-governance/stages/`（子工作流和 skill）

> 注意：SKILL.md 是入口文件，不是完整工作流。它引用了上述文件，agent 需要能读取整个仓库才能完整工作。

## 常用命令

安装后，在 Claude Code 中可以直接使用以下命令：

| 命令 | 作用 |
|------|------|
| `/governance-status` | 查看当前项目状态、阶段、任务进度、Gate 概览 |
| `/governance-gate` | 检查指定 Gate 详情（如 `/governance-gate G6`） |
| `/governance-verify` | 运行完整校验，检查工作流资产完整性 |

这些命令在 agent 内执行，不需要退出到终端。

## 5 分钟开始

### 新项目

1. 告诉你的 agent："我要开始一个新项目，项目目标是 XXX"
2. 工作流自动从**立项阶段**开始，引导你明确目标、范围和关键决策
3. 每推进一个阶段，agent 会自动检查是否达到质量标准

### 已在进行的项目

1. 告诉你的 agent："我的项目目前在开发阶段，想接入治理工作流"
2. 工作流会要求你补充最少的信息（当前状态、关键决策、已知风险）
3. 之前的阶段自动标记为"已通过"，不需要补齐历史记录
4. 立即从当前阶段开始治理

### 只用某个功能

不需要加载全流程。你可以直接告诉 agent：

- "帮我做一次技术方案评审" → 加载技术评审 checklist
- "帮我做 Code Review" → 加载 Code Review 规范
- "帮我做发布 checklist" → 加载发布检查清单
- "帮我做项目复盘" → 加载回顾会议模板

## 项目规模选择

安装后第一次使用，工作流会问你的项目规模：

| 选择 | 适合 | 工作流做什么 | 你需要做什么 |
|------|------|------------|------------|
| **轻量** | 个人项目、MVP、探索 | 只跟踪核心阶段，最少记录 | 几乎不管，只在关键节点确认 |
| **标准** | 团队项目、正式产品 | 全流程 11 阶段，完整记录 | 方向决策和质量审核 |
| **严格** | 大型项目、合规系统 | 全流程 + 双重证据 + 不允许跳步 | 每个决策审核 + 审批 |

不确定选哪个？先选"标准"，随时可以调整。

## 日常体验

### 工作流自动做的事（不打扰你）

- 记录每个任务完成后的证据
- 检查 Gate 是否通过
- 跟踪风险状态变化
- 更新项目状态面板
- 在阶段转换时提醒你补齐必要记录

### 需要你做的事

- **方向决策**：多条路线时选择走哪条
- **需求澄清**：确认你到底要做什么
- **质量审核**：确认产出物是否满足要求

### 你不会被打扰的事

- 记录更新、文件编辑、状态跟踪——全自动
- Gate 通过时不会打断你
- 两个紧密关联的任务之间不会停下来请示

## 覆盖的项目阶段

```
立项 → 调研 → 技术选型 → 环境搭建 → 架构设计 → 开发 → 测试 → CI/CD → 发布 → 运营 → 维护
```

每个阶段有独立的子工作流，包含：进入条件、活动清单、产出标准、退出检查。你可以从任意阶段开始。

## 验证

**推荐方式**（在 agent 内部）：

```
/governance-verify
```

**手动方式**（在终端中）：

```bash
python scripts/verify_workflow.py              # 完整校验
python scripts/verify_workflow.py status       # 项目状态
python scripts/verify_workflow.py gates        # 所有 Gate
```

## 内部文档

以下文档供工作流开发者和贡献者参考，普通用户不需要阅读：

- [协议层定义](protocol/plugin-contract.md)
- [生命周期规则](workflows/software-project-governance/rules/lifecycle.md)
- [Gate 门禁规则](workflows/software-project-governance/rules/stage-gates.md)
- [Profile 配置](workflows/software-project-governance/rules/profiles.md)
- [中途接入协议](workflows/software-project-governance/rules/onboarding.md)
- [企业实践经验](workflows/software-project-governance/research/company-practices.md)
- [产品形态设计](workflows/software-project-governance/research/default-product-shape.md)
