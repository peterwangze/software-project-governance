# Codex Adapter

This directory records the Codex loading path for `software-project-governance`.

Codex is a Tier 1 loading target in 0.47.0. The current repository provides a Codex plugin/project guidance package:

- personal marketplace root: `.agents/plugins/marketplace.json`
- plugin manifest: `.codex-plugin/plugin.json`
- project bootstrap: `AGENTS.md`
- workflow entry: `skills/software-project-governance/SKILL.md`
- runtime records: the target project's `.governance/`

## 适配目标

让 Codex 类 coding agent 在执行项目任务时，以统一流程资产为约束，避免直接基于临时上下文做局部最优决策。

## Load

Use this repository as a Codex plugin and project guidance package. The manifest path chain is:

```text
.agents/plugins/marketplace.json
  -> .codex-plugin/plugin.json
  -> skills/software-project-governance/SKILL.md
```

For project-level guidance, `AGENTS.md` bootstraps the Coordinator and points to the same workflow entry. In Codex Desktop/App contexts that support plugin marketplace loading, add the local/personal marketplace file according to the host UI or command surface, then enable the `software-project-governance` plugin from that marketplace.

If the Codex environment cannot consume `.codex-plugin/plugin.json` directly, keep the repo as a skill/plugin asset package and load `skills/software-project-governance/SKILL.md` through the host-supported skill or project instruction mechanism.

## Verify

Codex plugin and marketplace assets:

```bash
python -m json.tool .agents/plugins/marketplace.json
python -m json.tool .codex-plugin/plugin.json
python C:\Users\peter\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py .
```

Static adapter contract:

```bash
python adapters/codex/launch.py
python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters
```

CLI target-cwd E2E gate:

```bash
python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent codex --timeout 180
```

## Boundary

2026-06-11 local evidence supports Codex manifest validation, personal marketplace JSON validation, and Codex CLI headless target-cwd read E2E. The runtime command returned machine-readable fields from `project/e2e-test-project`: `E2E_PLATFORM=codex`, `E2E_AGENT=Coordinator`, and `E2E_MODE=always-on x default-confirm`.

That does not prove Codex Desktop marketplace add/install/enable/upgrade/uninstall lifecycle E2E, official approval, marketplace approval, or universal/full runtime support. Codex CLI read E2E is PASS/DEGRADED; interaction boundaries, Agent Team separation, browser/MCP availability, and broader tool-use closure remain host-dependent.

## Current Effective Entry

Codex 加载 `skills/software-project-governance/SKILL.md` 作为自包含入口，该文件依赖：
- `skills/software-project-governance/references/` — 按需读取的参考规则
- `skills/software-project-governance/stages/` — 11 个阶段的子工作流和 skill
- 用户项目的 `.governance/` — 活跃治理记录

当前仓库还提供 Codex 原生投影：

- `AGENTS.md`：Codex 项目级 bootstrap，本会话已通过该入口读取 `.governance/plan-tracker.md` 并执行治理流程。
- `.codex-plugin/plugin.json`：Codex 插件 manifest。
- `.agents/plugins/marketplace.json`：Codex/agent marketplace 索引。
- `adapters/codex/adapter-manifest.json` + `launch.py`：可复跑的 adapter contract 和 runtime E2E 元数据。

2026-06-11 本机验证结果：`codex --version` 返回 `codex-cli 0.125.0`，`python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent codex --timeout 180` 在 `project/e2e-test-project` 中 PASS，返回机器可读 E2E 字段。

Codex App 当前会话仍不能替代 Codex Desktop marketplace-management lifecycle evidence。主流 agent 适配的 read target-cwd 闭环标准已经由真实 `codex exec` 用例验证；下一层边界仍是 Desktop add/install/enable/invoke/upgrade/uninstall、官方批准、市场批准和非 read-only 能力闭环。

## 历史入口约定（已废弃，仅供参考）

<details>
<summary>旧版 repo-local 6 步预加载（不再有效）</summary>

以下内容仅在早期 repo-local 架构下有效，已不再推荐使用。

1. 读取 workflow manifest：`skills/software-project-governance/core/manifest.md`
2. 读取协议层：`skills/software-project-governance/core/protocol/workflow-schema.md`、`skills/software-project-governance/core/protocol/plugin-contract.md`、`skills/software-project-governance/core/protocol/external-command-contract.md`
3. 读取规则层：`core/*.md`
4. 读取模板层：`core/templates/*.md`
5. 按当前阶段读取子工作流和 skill：`skills/<skill-name>/SKILL.md`
6. 读取样例：`.governance/plan-tracker.md`

</details>

## 半可执行入口

当前目录已提供两类可被脚本消费的入口：

- `adapters/codex/adapter-manifest.json`：机器可读的适配器元数据
- `adapters/codex/launch.py`：输出读取顺序、输出目标、Gate 行为和校验命令的 launcher

可通过以下命令查看入口输出：

```bash
python adapters/codex/launch.py
```

## 后续可扩展方向

- 可进一步提供面向 Codex CLI 的命令式入口描述。
- 可补充更结构化的 adapter contract，使 Codex 更容易自动消费 workflow。
