# Agent 入口差异

不同 coding agent 的插件/工作流加载机制不同。本文件说明每个 agent 的用户入口路径。

## 支持的 Agent

### Claude Code

**安装**：`/plugin marketplace add <repo-path>` → `/plugin install software-project-governance`

**初始化**：`/governance-init` 或直接让 agent 创建 `.governance/`

**日常使用**：
- 平台原生入口文件 bootstrap 在每次会话自动激活（全自动）
- 用户说"切换到最高权限模式"等口头命令即时生效
- `/governance-status` / `/governance-gate` / `/governance-verify` 手动查询

**自升级**：bootstrap 检测到版本变化时自动更新 平台原生入口文件 和 plan-tracker 结构

**特色能力**：
- 完整 bootstrap 模板（SELF-CHECK + 双维度模式 + 阶段跳跃防护）
- 交互式 governance-init（AskUserQuestion）
- 治理开关动态切换
- git hooks（pre-commit + post-commit + prepare-commit-msg）

### Codex (OpenAI)

**安装**：通过 Codex 插件市场或本地路径安装

**初始化**：与 Claude 相同的 governance-init 流程

**日常使用**：平台原生入口文件 或等效入口文件中的 bootstrap 规则（取决于 Codex 的加载机制）

**限制**：
- Codex 的 skill/rule 加载机制与 Claude 不同——bootstrap 模板可能需要适配
- AskUserQuestion 是 Claude 特有工具——Codex 中的等效交互方式待验证
- Git hooks 独立于 agent——在任何 agent 下均可工作

### Gemini (Google)

**安装**：通过 Gemini 的 custom commands 或 external runner 机制

**初始化**：通过 shared command contract（`protocol/external-command-contract.md`）调用

**日常使用**：Gemini 通过 MCP server 或 external runner 调用 workflow 功能

**当前状态**：兼容预研已完成（OPS-001, MAINT-003~006）。**尚未执行最小验证**（MAINT-023）。推荐验证路径：external runner → shared command → MCP server。

### 国内 Agent CLI

**状态**：兼容抽象已建立（`domestic-agent-cli-compatibility.md`），尚未执行任何真实验证。

**推荐接入路径**（按优先级）：
1. 支持 MCP 协议的 agent → 通过 MCP server 接入（AUDIT-013 待实现）
2. 支持 external runner 的 agent → 通过 shared command contract 接入
3. 仅支持 rules/skills 的 agent → 提供独立 rules 文件集

## 跨 Agent 共享的能力

以下机制不依赖特定 agent，在所有环境下均可工作：

| 能力 | 依赖 | 跨 agent 可用 |
|------|------|:--:|
| `.governance/` 文件结构 | 文件系统 | ✅ |
| verify_workflow.py | Python | ✅ |
| git hooks (pre-commit/post-commit) | Git | ✅ |
| check-governance | Python | ✅ |
| plan-tracker/evidence/decision/risk 模板 | 文件系统 | ✅ |
| bootstrap 规则 | Agent 加载机制 | ⚠️ 需适配 |
| AskUserQuestion 交互 | Claude 特有 | ❌ 需替代方案 |
| 治理开关口头命令 | Agent 理解能力 | ⚠️ 需适配 |
| 治理命令（governance-*） | Agent skill 机制 | ⚠️ 需适配 |

## 用户选择 Agent 的建议

| 场景 | 推荐 Agent | 原因 |
|------|-----------|------|
| 完整治理体验 | Claude Code | 全功能——bootstrap 自升级、交互式 init、治理开关、hooks |
| 轻量使用 | 任意 | 核心治理结构（.governance/ + hooks + verify）跨 agent 可用 |
| 非 Claude 环境 | 任意 + MCP server | 通过 MCP 协议接入 governance 功能（待 AUDIT-013 实现） |
