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
# 方式一：通过插件市场安装（推荐，两步）
/plugin marketplace add peterwangze/software-project-governance
/plugin install software-project-governance@spg

# 方式二：直接从 git URL 安装
/plugin install https://github.com/peterwangze/software-project-governance.git

# 方式三：克隆到本地后安装
git clone https://github.com/peterwangze/software-project-governance.git
/plugin install /path/to/software-project-governance
```

安装后，工作流入口会在后续会话中自动可用；**但首次使用前仍必须先完成一次初始化**，在你的项目根目录创建 `.governance/` 治理文件。安装完成不等于已经可用完成。

### Codex

```bash
git clone https://github.com/peterwangze/software-project-governance.git
```

当前仓库已提供 Codex 所需资产：`.codex-plugin/plugin.json` 和 `skills/software-project-governance/SKILL.md`。

但要注意两点：
1. **Codex 的具体加载方式取决于你当前使用的 Codex 环境/插件机制**，不是所有环境都等价于 Claude Code 的 `/plugin install`
2. **首次使用前同样要先初始化项目治理文件**，否则后续状态、Gate、verify 都没有项目事实源

Codex 入口采用**自包含 skill**：`skills/software-project-governance/SKILL.md` 内嵌核心规则，详细规则从同目录 `references/` 按需读取；项目运行数据写入你当前项目根目录 `.governance/`。

如果你当前使用的 Codex 环境不能直接消费 `.codex-plugin/plugin.json`，先把它视为插件资产包，再按该环境支持的 skill/plugin 加载方式接入。当前仓库提供的是**可消费资产**，不是对所有 Codex 运行环境都统一的一键安装命令。

首次进入后，优先完成初始化，再开始日常使用。没有初始化时，不建议直接运行状态类命令。 

### 其他 agent（Gemini、国内 agent CLI 等）

**这里当前提供的是兼容方向，不是“已经验证完毕、可直接照抄”的统一安装说明。**

如果某个 agent 支持加载单个 skill / command / plugin 入口，可以优先尝试：
1. 加载 `skills/software-project-governance/SKILL.md`
2. 允许该入口按需读取同目录 `references/`
3. 让治理记录写回你项目根目录的 `.governance/`

如果某个 agent 还不支持这种方式，再退回 external runner / MCP / custom command 等兼容路线。详细兼容原则和限制见 `adapters/gemini/README.md`。

请注意：Gemini 和国内 agent CLI 当前是**兼容研究 + 路线定义已完成**，但最小验证仍在后续计划中（见 `MAINT-007`）。不要把这部分内容理解为“现在已经存在一套与 Claude Code 同等级的一键安装入口”。

`SKILL.md` 不是“要求 agent 顺序扫描整个仓库根目录”的索引文件；它是**自包含入口**，只依赖：
- `skills/software-project-governance/SKILL.md`（入口，内嵌核心规则）
- `skills/software-project-governance/references/stage-gates.md`
- `skills/software-project-governance/references/lifecycle.md`
- 你项目中的 `.governance/`（活跃治理记录）

如果你的 agent 不能稳定满足上面 4 个条件，就说明当前更适合走兼容路线，而不是直接按 README 当成现成产品入口使用。

## 常用命令

安装后，在 Claude Code 中优先使用插件命名空间命令：

| 命令 | 作用 |
|------|------|
| `/software-project-governance:governance-init` | 首次使用时初始化项目治理文件（安装后第一步） |
| `/software-project-governance:governance-status` | 查看当前项目状态、阶段、任务进度、Gate 概览 |
| `/software-project-governance:governance-gate G6` | 检查指定 Gate 详情 |
| `/software-project-governance:governance-verify` | 运行完整校验，检查工作流资产完整性 |

说明：当前 Claude Code 插件环境下，这些命令通常以 `插件名:命令名` 的形式暴露；如果你的环境后续支持短别名，再按该环境实际行为使用。

这些命令在 agent 内执行，不需要退出到终端。

## 5 分钟开始

### 第一步：初始化（必须）

**首次使用时，先初始化，再谈状态/校验/阶段检查。**

在支持 slash command 的环境里，优先运行：

```
/software-project-governance:governance-init
```

这个命令会引导你完成初始设置：
1. 输入项目名称和目标
2. 选择是新项目还是已有项目
3. 选择治理强度（轻量/标准/严格）
4. 自动在当前项目根目录创建 `.governance/` 文件夹，包含所有治理文件

如果你的环境暂不支持 `/software-project-governance:governance-init` 这类命令，就直接告诉 agent：
- 你的项目名称和目标
- 这是新项目还是已有项目
- 当前所处阶段（如果是已有项目）
- 你想使用的治理强度（lightweight / standard / strict）

然后让它按 `skills/software-project-governance/SKILL.md` 的规则帮你初始化 `.governance/`。

**仓库里已有的 `.governance/` 是本项目自己的运行样例，不是你的初始化模板。** 不要直接复制仓库根目录下已有的治理记录来当你的项目初始状态。

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
/software-project-governance:governance-verify
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
- [生命周期规则](skills/software-project-governance/references/lifecycle.md)
- [Gate 门禁规则](skills/software-project-governance/references/stage-gates.md)
- [Profile 配置](skills/software-project-governance/references/profiles.md)
- [中途接入协议](skills/software-project-governance/references/onboarding.md)
- [企业实践经验](workflows/software-project-governance/research/company-practices.md)
- [产品形态设计](workflows/software-project-governance/research/default-product-shape.md)
