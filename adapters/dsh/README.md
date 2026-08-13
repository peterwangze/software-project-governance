# DeepSeek Harness Adapter

本目录定义 `software-project-governance` workflow 在 DeepSeek Harness（dsh）上的加载投影、运行时验证状态与边界约束。

DeepSeek Harness is a Tier 1 loading target in 0.73.0. The loading model is a **generated agent preset** plus a thin `AGENTS.md` project pointer — the workflow rules themselves stay in the shared skill entry and are never duplicated per platform.

## 加载模型

dsh 没有 plugin marketplace，也没有 slash-command 扩展面；它的扩展单位是 **agent preset**：`${DSH_HOME}/.agent-presets/<id>/` 下的一组静态文件（`agent.cordis.yml` + `preset.yml`）。本适配器因此采用：

1. **预设投影（preset projection）**：`launch.py --install` 从 `agent.cordis.yml.template` 生成 `governance` 预设。预设只做三件事：
   - persona 携带 Coordinator 身份与 DSH 版 governance bootstrap（每次会话第一动作、SELF-CHECK、模式确认、Agent Team 映射、hook 检查、升级路径）；
   - 通过 `skill-filesystem.customSkillDirs` 把仓库的 `skills/`（工作流本体）与 `adapters/dsh/skill-shims/`（`commands/` 的薄投影）注册为本预设的 skill 根——原生 `skill` 工具直接暴露整个工作流目录（25 个子 skill + 9 个命令投影 skill）；
   - 保留 `standard` 预设的完整编码工具集（shell/fs/jobs/skill/goal/plan/compaction/subagent/subagent_fork/workflow/ralph/ask-user/todo/web），角色 agent 由 `subagent` 工具 spawn 并继承同一组合。
2. **项目投影（project projection）**：`launch.py --bootstrap-project <dir>` 写入项目根 `AGENTS.md`（thin pointer）。dsh 会自动把工作区的 `AGENTS.md` 注入会话，因此治理在任意预设下都能激活；文件只做指针与 SELF-CHECK，不重复 workflow 规则。

命令入口映射：dsh 的 `/name` 用户手势直接加载同名 skill。`commands/*.md` 是跨平台共享资产（其内容被其它平台的斜杠命令与测试直接消费），因此 DSH 不修改它们，而是用 `adapters/dsh/skill-shims/` 下的同名薄投影把它们暴露为 skill——`/governance`、`/governance-status` 等九条命令在 dsh 中成为一等 skill 入口。

Git hooks 发现：`launch.py --install` 额外写入预设目录内的 `skill-root.txt`（仓库根路径标记）。`infra/hooks/` 的 `find_spg_home` 已加入 dsh 候选——预设目录内的 skills 快照（copy 模式）与 `skill-root.txt` 指向的仓库（link 模式）——因此安装在项目 `.git/hooks/` 里的治理 hook 在 dsh 环境下也能自升级，无需环境变量。

## 使用

```powershell
python adapters/dsh/launch.py                 # 查看 adapter manifest
python adapters/dsh/launch.py --install       # 生成 ${DSH_HOME}/.agent-presets/governance/
python adapters/dsh/launch.py --install --mode copy   # 快照模式（skills/commands 复制进预设目录，仓库移动后仍有效）
python adapters/dsh/launch.py --bootstrap-project <项目目录>   # 写入项目级 AGENTS.md
git -C <仓库> pull; python adapters/dsh/launch.py --sync       # 升级后刷新预设
```

然后：启动 dsh 会话并选择「治理协调器」预设（或在被治理项目目录里直接开任意预设会话，由 `AGENTS.md` 激活）。

## 验证

```powershell
python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters
python skills/software-project-governance/infra/verify_workflow.py check-runtime-readiness-matrix
```

本机 2026-07-08 验证结果：本适配器在一个真实 dsh 会话（`dsh --version` 返回 `0.1.0-rc.6`）中完成编写与验证——原生 `skill` 工具加载 skill、原生 `subagent` 工具并行派发 3 个子代理、`ask_user_question`/`pwsh`/fs/web 工具全部可用，生成的 `governance` 预设通过 `agentPresets.standingKeyFor` 挂载校验。该结果证明 dsh 可以原生承载治理工作流；它不代表 browser 自动化或 MCP 服务器已闭环（两者仍是 host-dependent）。

## 能力边界（no-overclaim）

- `ask_user_question`：**native**（dsh 原生工具）。
- `sub_agent`：**native**（`subagent`/`subagent_fork`，in-process spawn/fork，子代理继承父预设组合）。
- `tool_calling`：**native**（pwsh、fs read/write/edit、glob、grep、web_search、jobs、goal、todo）。
- `browser`：**degraded**（有 web_search，无浏览器自动化）。
- `mcp`：**degraded**（安装含 MCP client 包，服务器可用性取决于主机配置）。
- `git_hooks`：**native**（仓库级控制）。
- workflow closure：**degraded**（仅 browser 与 MCP 依赖主机），与 Chrys 并列最强的原生能力画像。

本适配器不声明 official approval、marketplace approval、universal/full runtime support 或 1.0.0 生产就绪。

## 资产

- `adapters/dsh/adapter-manifest.json`：机器可读的适配器元数据（能力声明 + E2E 证据）。
- `adapters/dsh/launch.py`：预设生成器与项目 bootstrap 写入器。
- `adapters/dsh/agent.cordis.yml.template`：预设组合模板（token 由 launch.py 替换；不直接挂载）。
- `adapters/dsh/preset.yml`：预设元数据。
- `adapters/dsh/skill-shims/`：`commands/*.md` 的 DSH 薄投影（扁平 skill，name+description frontmatter）。
- `adapters/dsh/AGENTS.md.template`：DSH 项目级 bootstrap 模板（thin pointer）。

## 与其它适配器的差异

- dsh 是第一个「launcher 真正执行安装」的适配器（其它平台的 launch.py 只打印 manifest）——因为 dsh 预设是普通文件，安装即写文件，无需任何平台内交互。
- dsh 的 skill 目录直接指向仓库 checkout（link 模式），`git pull` 即 skill 更新；`--mode copy` 提供自包含快照作为替代。
- 不需要 `resolve_entry.py` 的平台探测：DSH 下 PLUGIN_HOME 由 skill 的 resourceBase 直接给出（`resolve_entry.py` 的 `__file__` 自定位与 HOST_PROJECT_ROOT=cwd 的双根模型在 DSH 下原样成立）。
