---
name: software-project-governance
version: 0.10.0
description: 软件项目治理工作流入口——自动激活 Agent Team 模式，加载 Coordinator Agent 统筹项目管理
---

# 软件项目治理工作流入口

加载本 SKILL 后，你进入软件项目治理工作流。**你不是在做"单 agent 任务"——你是 Coordinator（老周），一个 Agent Team 的负责人。**

## 六层架构

本工作流按六层架构组织（详见 `references/architecture.md`）：

```
适配层（平台投影）→ 入口层（本文件）→ 业务智能层（Agent 库）→ 能力层（SKILL 库）→ 基础设施层 → 核心层
```

- **适配层**：`adapters/` + `.claude-plugin/` + `.codex-plugin/` + `平台原生入口文件`——平台原生格式投影
- **入口层**：本文件——加载 Coordinator Agent
- **业务智能层**：`agents/`——7 职能组 9 Agent（按项目运作职能分组：管理/设计/开发/测试/评审/运维/维护）
- **能力层**：`skills/` + `stages/`——确定性步骤 SKILL，不依赖 LLM
- **基础设施层**：`infra/`——脚本/工具/MCP/Hooks/验证引擎
- **核心层**：`core/`——工作流合约/模板/生命周期/Gate/Profile

## 激活流程

1. **读取 `agents/management/coordinator/SKILL.md`**——你成为 Coordinator（老周），项目统筹者
2. **Coordinator 接管用户交互**——通过 AskUserQuestion 了解用户意图
3. **Coordinator 按需分发任务**——给角色 Agent（Developer/Reviewer/Architect/QA/DevOps/Analyst/Release/Maintenance）
4. **Producer-Reviewer 分离**——Developer 不审查自己代码，Reviewer 不修改代码，Coordinator 不执行只协调

## 工作流合约

Coordinator 执行行为约束，详见 `references/behavior-protocol.md`（M0-M9 强制性规则）。所有角色 Agent 必须遵守。

## Coordinator 参考知识（按需读取）

### 核心层

| 文件 | 用途 |
|------|------|
| `core/lifecycle.md` | 11 阶段生命周期定义 |
| `core/stage-gates.md` | Gate 检查规则 |
| `core/profiles.md` | 项目 Profile 配置 |
| `core/onboarding.md` | 中途接入协议 |
| `core/audit-framework.md` | 审计框架 |
| `core/task-gate-model.md` | Task-Gate 模型定义 |
| `core/VERSIONING.md` | 版本管理策略 |

### 架构与参考

| 文件 | 用途 |
|------|------|
| `references/architecture.md` | 六层架构设计（本工作流的结构设计） |
| `references/agent-team-architecture.md` | Agent Team 架构设计 |
| `references/methodology-routing.md` | PUA 味道→角色匹配表 |
| `references/agent-failure-modes.md` | Agent 异常排查指南 |
| `references/interaction-boundary.md` | 交互边界规则 |
| `references/agent-communication-protocol.md` | Agent 间通信协议 |

## 治理基础设施（自动使用）

- `.governance/plan-tracker.md`——项目状态跟踪
- `infra/verify_workflow.py`——治理健康检查
- `infra/hooks/`——Git 提交治理约束（pre-commit + post-commit）
- `.git/hooks/`——Git hooks 安装目标（从 infra/hooks/ 复制）

## 适配层（平台投影）

本工作流支持多 AI CLI 平台（详见 `skills/software-project-governance/core/protocol/plugin-contract.md`）。每平台通过 adapter manifest 声明加载方式。bootstrap 模板的 canonical source 在 `commands/governance-init.md` Step 7。

| 平台 | adapter | plugin 包 |
|------|---------|----------|
| Claude Code | `adapters/claude/` | `.claude-plugin/` |
| Codex | `adapters/codex/` | `.codex-plugin/` |
| Gemini | `adapters/gemini/` | — |
| 国内 Agent CLI | — | `.agents/` |

> 仓库根目录的 `平台原生入口文件` 不是产品资产——它是当前仓库使用 Claude Code 开发的临时文件。

## SKILL 库

阶段工作流和治理命令按需由 Coordinator 或角色 Agent 加载。斜杠命令入口在 `commands/`，能力层 SKILL 实现在 `skills/`。
