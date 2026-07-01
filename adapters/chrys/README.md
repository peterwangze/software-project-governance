# Chrys Adapter

This directory records the Chrys loading path for `software-project-governance`.

Chrys is a Tier 1 loading target. Chrys auto-loads `AGENTS.md` and `CLAUDE.md` as native context files, and has native `load_skill` / `read_skill_resource` / `run_skill_script` tools for skill consumption. The current effective entry is the self-contained workflow skill:

- native context files: `AGENTS.md`, `CLAUDE.md`
- workflow entry: `skills/software-project-governance/SKILL.md`
- skill loading: native `load_skill` tool
- runtime records: the target project's `.governance/`

## 适配目标

让 Chrys coding agent 在执行软件项目任务时，通过原生 AGENTS.md 上下文加载 + 原生 `load_skill` 工具，自动进入 governance bootstrap 并维护治理闭环。

## Load

Chrys auto-loads `AGENTS.md` and `CLAUDE.md` from the project root. These files bootstrap the Coordinator identity and governance workflow. Chrys also has native skill loading:

```text
AGENTS.md / CLAUDE.md
  -> skills/software-project-governance/SKILL.md (via native load_skill)
```

No separate plugin manifest or marketplace entry is needed. Chrys reads the project context files directly and loads the skill through its native `load_skill` tool.

## Verify

Static adapter contract:

```bash
python adapters/chrys/launch.py
python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters
```

Runtime adapter contract:

```bash
python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters --runtime
```

## Boundary

Chrys has the strongest native capability profile of any adapter: native `ask_user` tool (AskUserQuestion equivalent), native sub-agents (`explore_agent`/`plan_agent`/`general_agent`), native tool calling (`read_file`/`write_file`/`edit_file`/`grep`/`glob`/`pwsh`/`git_bash`), and native skill loading (`load_skill`/`read_skill_resource`/`run_skill_script`). Only browser automation and MCP remain host-dependent.

This adapter does not claim official approval, marketplace approval, universal/full runtime support, or 1.0.0 production-ready status.

## Current Effective Entry

Chrys loads governance through two native paths:
1. **Context files**: `AGENTS.md` and `CLAUDE.md` — auto-loaded at session start, contain the Governance Bootstrap (Step 0–4)
2. **Skill loading**: `skills/software-project-governance/SKILL.md` — loaded via native `load_skill` tool, defines Coordinator identity and workflow entry

The skill depends on:
- `skills/software-project-governance/references/` — on-demand reference rules
- the target project's `.governance/` — active governance records

## 半可执行入口

当前目录仍保留两类可被脚本消费的辅助入口：

- `adapters/chrys/adapter-manifest.json`：机器可读的适配器元数据
- `adapters/chrys/launch.py`：输出读取顺序、输出目标、原生入口、Gate 行为和校验命令的 launcher

可通过以下命令查看入口输出：

```bash
python adapters/chrys/launch.py
```

## 入口分工

- Chrys 正式加载入口：`AGENTS.md` + `CLAUDE.md`（原生上下文文件）+ `load_skill` 加载 `skills/software-project-governance/SKILL.md`
- Adapter manifest：仓库内部统一 contract
- Launcher：辅助查看和验证当前 Chrys 入口映射

## 后续可扩展方向

- 可按需要提供面向 Chrys 原生能力的 explicit skill catalog 声明。
- 可继续补充更贴近 Chrys 自动触发场景的 skill 说明。
