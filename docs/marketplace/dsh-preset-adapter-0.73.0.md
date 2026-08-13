# DSH 预设适配（0.73.0）——DeepSeek Harness 加载投影与边界

Date: 2026-07-08
Task: DSH-ADAPTER-001
Scope: `software-project-governance` 在 DeepSeek Harness（dsh）上的加载投影（adapter）、生成式 agent preset 与项目级 bootstrap。

## 定位

dsh 是继 Chrys 之后第二个具备完整原生能力画像（ask_user_question / sub_agent / tool_calling / git_hooks 全 native）的适配目标。它与 Chrys 的差异在分发面：dsh 没有 plugin marketplace、没有 slash-command 扩展面，其唯一扩展单位是 **agent preset**（`${DSH_HOME}/.agent-presets/<id>/` 下的静态 `agent.cordis.yml` + `preset.yml`）。因此本适配器的形态是「**生成的预设投影 + 薄项目指针**」——workflow 本体仍然只有一份（`skills/software-project-governance/SKILL.md`），平台层只做三件事：persona 注入 Coordinator bootstrap、注册 skill 根、写项目指针。

## 映射表

| workflow 概念 | dsh 承载面 | 状态 |
|---|---|---|
| 入口 bootstrap（每会话第一动作） | 预设 persona + 项目 `AGENTS.md`（dsh 自动注入工作区会话） | native |
| `/governance` 等 9 条命令 | `/name` 用户手势 → 同名 skill（`adapters/dsh/skill-shims/` 薄投影，指向 `commands/*.md`） | native |
| skill 加载 | 原生 `skill` 工具 + `skill-filesystem.customSkillDirs`（仓库 `skills/` + shims） | native |
| plugin_home 定位 | skill 工具返回的 resourceBase = `skills/software-project-governance/`；`resolve_entry.py` 双根模型原样成立（无需平台探测） | native |
| AskUserQuestion | `ask_user_question` 工具 | native |
| Agent Team（spawn 角色 agent） | `subagent` / `subagent_fork`（in-process spawn/fork，子代理继承父预设组合） | native |
| Write/Edit/Bash | `read`/`write`/`edit`/`pwsh` | native |
| `/plugin update` 自升级 | `git pull` + `launch.py --sync`（bootstrap 下次会话自动补全） | degraded（平台无等价物，由 launcher 承担） |
| git hooks | 仓库级 pre-commit/commit-msg/post-commit | native |
| browser 自动化 | 无（仅 web_search） | degraded |
| MCP | dsh 安装含 MCP client 包；服务器可用性 host-dependent | degraded |

## 安装与验证

```powershell
python adapters/dsh/launch.py --install                     # 生成 ${DSH_HOME}/.agent-presets/governance/
python adapters/dsh/launch.py --install --mode copy         # 自包含快照模式
python adapters/dsh/launch.py --bootstrap-project <dir>     # 项目级 AGENTS.md（thin pointer）
python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters
python skills/software-project-governance/infra/verify_workflow.py check-runtime-readiness-matrix
```

## 验证证据（2026-07-08，本机）

1. `dsh --version` 返回 `0.1.0-rc.6`。
2. 本适配器在一个真实 dsh 会话中完成编写：原生 `skill` 工具加载 skill、原生 `subagent` 工具并行派发 3 个子代理、`ask_user_question`/`pwsh`/fs/web 工具全程可用。
3. `launch.py --install` 生成的 `governance` 预设通过 `agentPresets.standingKeyFor` 挂载校验（mounted OK）。
4. 以 standing scope 查询 skill registry：35 个 skill 被发现，含主入口 `software-project-governance`、9 个命令投影（`governance`、`governance-status`、…、`change-triage`）与全部 stage/review skill。
5. `check-agent-adapters` 与 `check-runtime-readiness-matrix` 均通过（dsh 已进入 `MAINSTREAM_AGENT_ADAPTERS` 与 `RUNTIME_MATRIX_AGENT_IDS`）。

## no-overclaim 边界

- 不声明 dsh 官方收录、marketplace approval、universal/full runtime support 或 1.0.0 生产就绪。
- browser 自动化与 MCP 保持 degraded；任何使用 dsh 的会话不得宣称这两项闭环。
- 预设挂载校验证明「组合可挂载 + skill 可发现」；真实会话内的 bootstrap 首动作（resolve_entry → SELF-CHECK → 模式确认）仍需用户在 `governance` 预设下开一次会话确认（适配器清单的 `agent_runtime_e2e` 以本会话为证据，如实标注）。
- `--mode copy` 快照与仓库 checkout 解耦后，升级需重跑 `launch.py --sync`；link 模式（默认）下 skill 更新即 `git pull`。
