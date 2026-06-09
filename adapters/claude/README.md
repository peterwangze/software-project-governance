# Claude Adapter

This directory records the Claude Code loading path for `software-project-governance`.

Claude Code is a Tier 1 loading target in 0.47.0. The current user-facing path is the plugin marketplace package that loads the self-contained workflow skill:

- marketplace root: `.claude-plugin/marketplace.json`
- plugin manifest: `.claude-plugin/plugin.json`
- workflow entry: `skills/software-project-governance/SKILL.md`
- runtime records: the target project's `.governance/`

## 适配目标

让 Claude 类 coding agent 在执行软件项目任务时，优先读取统一规则与模板，而不是直接自由发挥。

## Load

Recommended Claude Code install path:

```bash
/plugin marketplace add peterwangze/software-project-governance
/plugin install software-project-governance@spg
```

Alternative local or URL install paths:

```bash
/plugin install https://github.com/peterwangze/software-project-governance.git
git clone https://github.com/peterwangze/software-project-governance.git
/plugin install /path/to/software-project-governance
```

After install, open the target project root and run `/governance` to initialize or resume project-local governance state. Do not copy this repository's sample `.governance/` directory into another project.

## Verify

Static adapter contract:

```bash
python adapters/claude/launch.py
python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters
```

Runtime adapter contract:

```bash
python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters --runtime
```

2026-05-20 本机验证结果：`claude --version` 返回 `2.1.123 (Claude Code)`；`claude -p ...` 在 `project/e2e-test-project` 目标 cwd 中读取 `.governance/plan-tracker.md` 并返回当前阶段。该结果证明 Claude Code runtime 与目标 cwd 只读治理用例已真实通过。

## Boundary

Claude Code local runtime evidence is PASS/DEGRADED. That means the target-cwd read use case passed locally while workflow closure still depends on host capabilities such as AskUserQuestion, reviewer separation, git hooks, and release gates.

This adapter does not claim official approval, marketplace approval, universal/full runtime support, or 1.0.0 production-ready status. Plugin install success is not task evidence, independent review evidence, quality gate success, or release approval.

## Current Effective Entry

Claude Code loads `skills/software-project-governance/SKILL.md` as the self-contained entry. That file depends on:
- `skills/software-project-governance/references/` — on-demand reference rules
- the target project's `.governance/` — active governance records

下方旧入口约定已废弃，不要执行。

## 历史入口约定（已废弃，仅供参考）

<details>
<summary>旧版 repo-local 多文件预加载（不再有效）</summary>

```
1. 读取 workflow manifest：skills/software-project-governance/core/manifest.md
2. 读取协议层：skills/software-project-governance/core/protocol/workflow-schema.md、skills/software-project-governance/core/protocol/plugin-contract.md
3. 读取规则层：core/lifecycle.md、core/stage-gates.md
4. 读取模板层：core/templates/*.md
5. 使用样例验证：.governance/plan-tracker.md
```

</details>

## 半可执行入口

当前目录仍保留两类可被脚本消费的辅助入口：

- `adapters/claude/adapter-manifest.json`：机器可读的适配器元数据
- `adapters/claude/launch.py`：输出读取顺序、输出目标、原生 skill 路径、Gate 行为和校验命令的 launcher

可通过以下命令查看入口输出：

```bash
python adapters/claude/launch.py
```

## 入口分工

- Claude 正式加载入口：插件市场安装的 `skills/software-project-governance/SKILL.md`
- Adapter manifest：仓库内部统一 contract
- Launcher：辅助查看和验证当前 Claude 入口映射

## 后续可扩展方向

- 可按需要补充 `.claude/commands/` 下的显式 slash command 入口。
- 可继续补充更贴近 Claude Code 自动触发场景的 skill 说明。
