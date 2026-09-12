# DeepSeek Harness Adapter

本目录定义 `software-project-governance` workflow 在 DeepSeek Harness（dsh）上的加载投影、运行时验证状态与边界约束。

DeepSeek Harness is a Tier 1 loading target in 0.73.0. The loading model is a **generated agent preset** plus a thin `AGENTS.md` project pointer — the workflow rules themselves stay in the shared skill entry (`skills/software-project-governance/SKILL.md`) and are never duplicated per platform.

## 加载模型

dsh 没有 plugin marketplace，也没有 slash-command 扩展面；它的扩展单位是 **agent preset**：`${DSH_HOME}/.agent-presets/<id>/` 下的一组静态文件（`agent.cordis.yml` + `preset.yml`）。本适配器因此采用：

1. **预设投影（preset projection）**：包内预设负载 `agent-presets/governance/` 只有两个文件——组合模板 `agent.cordis.yml.template`（唯一组合事实源）与 `preset.yml`。两条交付路径渲染同一模板、写同一位置：bundle 宿主行 `lib/index.js` 的 `ensurePreset()`（`dsh plugin add` 后重启即自动完成，零手工步骤）与手工/离线路径 `launch.py --install`。渲染把 `__GOVERNANCE_*__` token 替换为**包内绝对路径**，因此用户根副本里的 `<plugin_root>` 就是包根，与 persona / 命令投影 / 项目 `AGENTS.md` 的既有措辞一致——**不复制** `skills/`、`commands/`、`agents/`（那是单一事实源违规与 2× 包体）。预设只做三件事：
   - persona 携带 Coordinator 身份与 DSH 版 governance bootstrap（每次会话第一动作、SELF-CHECK、模式确认、Agent Team 映射、hook 检查、升级路径）；
   - 通过 `skill-filesystem.customSkillDirs` 把仓库的 `skills/`（工作流本体）与 `adapters/dsh/skill-shims/`（`commands/` 的薄投影）注册为本预设的 skill 根——原生 `skill` 工具直接暴露整个工作流目录（25 个子 skill + 9 个命令投影 skill）；
   - 保留 `standard` 预设的完整编码工具集（shell/fs/jobs/skill/goal/plan/compaction/subagent/subagent_fork/workflow/ralph/ask-user/todo/web），角色 agent 由 `subagent` 工具 spawn 并继承同一组合。
2. **项目投影（project projection）**：`launch.py --bootstrap-project <dir>` 写入项目根 `AGENTS.md`（thin pointer）。dsh 会自动把工作区的 `AGENTS.md` 注入会话，因此治理在任意预设下都能激活；文件只做指针与 SELF-CHECK，不重复 workflow 规则。

命令入口映射：dsh 的 `/name` 用户手势直接加载同名 skill。`commands/*.md` 是跨平台共享资产（其内容被其它平台的斜杠命令与测试直接消费），因此 DSH 不修改它们，而是用 `adapters/dsh/skill-shims/` 下的同名薄投影把它们暴露为 skill——`/governance`、`/governance-status` 等九条命令在 dsh 中成为一等 skill 入口。

Git hooks 发现：两条交付路径都额外写入预设目录内的 `skill-root.txt`（包根路径标记）。`infra/hooks/` 的 `find_spg_home` 已加入 dsh 候选——`$DSH_HOME/.agent-presets/governance/skills/software-project-governance`（若存在）与 `skill-root.txt` 指向的包检出——因此安装在项目 `.git/hooks/` 里的治理 hook 在 dsh 环境下也能自升级，无需环境变量。

## 使用

```powershell
python adapters/dsh/launch.py                 # 查看 adapter manifest
python adapters/dsh/launch.py --install       # 手工/离线路径：渲染 ${DSH_HOME}/.agent-presets/governance/（4 个文件）
python adapters/dsh/launch.py --install --dry-run   # 只打印将要写入的路径与 token 渲染映射，不落盘
python adapters/dsh/launch.py --smoke         # 隔离 DSH_HOME 下的预设加载冒烟闸门（0 PASS / 1 FAIL / 2 REFUSED）
python adapters/dsh/launch.py --bootstrap-project <项目目录>   # 写入项目级 AGENTS.md
git -C <仓库> pull; python adapters/dsh/launch.py --sync       # 升级后刷新用户根预设
```

常用路径不需要 `--install`：`dsh plugin --profile web add "link:<本仓库绝对路径>"` + 重启后，包内宿主行会按包版本号自动把预设渲染进用户根（幂等；版本未变不写）。

然后：启动 dsh 会话并选择「治理协调器」预设（或在被治理项目目录里直接开任意预设会话，由 `AGENTS.md` 激活）。

### dsh 升级 / 重装后恢复接入

dsh 升级或 profile 清单重置/重装后，插件的 `dsh.profile.bundles` 注册可能丢失（profile 的 package.json 恢复模板态），bundle 层（`cordis.patch.yml`）不再应用——表现为非治理预设会话中 `/governance` 手势失效；bundle-only 安装时治理预设亦从预设选择器消失（经 `launch.py --install` 写入的用户根 `governance` 预设不受影响，其会话仍保有目录）。恢复方法（bundle 路径）：

```powershell
dsh plugin --profile web add "link:<本仓库绝对路径>"
```

然后重启 dsh——bundle 层是 boot-time 应用，非 HMR，不重启不生效。注意 `launch.py --sync` 只刷新用户根预设（`${DSH_HOME}/.agent-presets/governance`），不恢复 bundle 注册。验证：重启后 profile 的 package.json 中 `dsh.profile.bundles` 应含 `@peterwangze/software-project-governance-plugin`；预设选择器应出现「治理协调器」（用户根 ⇒ 自定义预设，可删除、可打开目录）。

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
- `adapters/dsh/launch.py`：预设渲染器（渲染 + 原子换入）与项目 bootstrap 写入器。
- `agent-presets/governance/agent.cordis.yml.template`：预设组合模板（唯一组合事实源；token 由 `lib/index.js` / `launch.py` 渲染为绝对路径；**不直接挂载**，`.template` 后缀即防误挂载标记）。
- `agent-presets/governance/preset.yml`：预设元数据（roster 显示名与描述）。
- `lib/index.js`：bundle 插入的宿主行——开机渲染预设到用户根，失败只 warn 不抛（抛会打断 dsh 启动）。
- `cordis.patch.yml`：bundle 补丁层——**只有一条 `- insert:`**（本包自己的行），不改任何宿主行（DEC-187）。
- `adapters/dsh/skill-shims/`：`commands/*.md` 的 DSH 薄投影（扁平 skill，name+description frontmatter）。
- `adapters/dsh/AGENTS.md.template`：DSH 项目级 bootstrap 模板（thin pointer）。

## 与其它适配器的差异

- dsh 是第一个「launcher 真正执行安装」的适配器（其它平台的 launch.py 只打印 manifest）——因为 dsh 预设是普通文件，安装即渲染写文件，无需任何平台内交互。
- 预设的 skill 根是**包内绝对路径**（渲染时写入），因此 `git pull` 即 skill 更新，且不存在「副本脱离包后 skill 目录为空」的问题；没有 copy/快照模式，也没有第二份 skill 树。
- 不需要 `resolve_entry.py` 的平台探测：DSH 下 PLUGIN_HOME 由 skill 的 resourceBase 直接给出（`resolve_entry.py` 的 `__file__` 自定位与 HOST_PROJECT_ROOT=cwd 的双根模型在 DSH 下原样成立）。
