# DeepSeek Harness Adapter

本目录定义 `software-project-governance` workflow 在 DeepSeek Harness（dsh）上的加载投影、运行时验证状态与边界约束。

DeepSeek Harness is a Tier 1 loading target in 0.73.0. The loading model is a **generated agent preset** plus a thin `AGENTS.md` project pointer — the workflow rules themselves stay in the shared skill entry (`skills/software-project-governance/SKILL.md`) and are never duplicated per platform.

## 加载模型

dsh 的扩展单位是 **agent preset**。本适配器有两条交付路径，按**宿主能力**选择，绝不按版本号比较（FEAT-102）：

1. **原生派生（native，唯一默认；宿主声明 `@deepseek-ai/dsh-agent-preset-registry` 时）**：`lib/index.js` 在自己激活时读取公开的 loader 组合树，定位宿主当前已组合的 `standard` 预设声明，只做两个内容差量——把治理 persona 正文追加到基础 persona 的 prefix、把本包两个 skill 根追加到 `skill-filesystem.customSkillDirs`——其余每一行（工具、group、isolate、`!!js`、顺序、禁用位）原样继承，再通过公开的 `agentPresets.register` 登记为 `governance`。**升级解耦**：宿主新增/改名/禁用工具时派生结果自动跟随，本包不持有工具行副本、不写 `$DSH_HOME`；卸载只撤回自己的登记。
2. **宿主行的四种不可用态（DEC-366 ②）——一律只 warn、绝不写目录、不自动渲染**：① **absent**（组合树里没有 registry row；目录模型旧宿主需要**显式** `launch.py --install`，且 `DSH_HOME` 必须重定向到隔离目录）；② **disabled**（声明了该 row 但被禁用）；③ **unreadable**（loader 组合树无法枚举）；④ **ambiguous**（没有唯一可合并的 base 声明：缺失 / 重复 / 形态不可安全合并）。四种态各产生一条 warn 和结构化 code，row 在任何情况下都不调用 `ensurePreset()`。
3. **静态目录投影（legacy；仅显式安装面）**：`launch.py --install` 渲染 `agent-presets/governance/agent.cordis.yml.template` 到 `${DSH_HOME}/.agent-presets/governance/`。这份组合是**一次性快照**，不可能跨宿主代际保持正确——这正是原生路径移除的耦合；它只服务于仍是目录模型的旧宿主，且必须由操作者显式触发。

共享约定：`agent-presets/governance/` 的负载是组合模板、`preset.yml` 元数据与 `persona.md.template`（治理 persona 正文的单一事实源；原生路径直接读它，legacy 组合里的同文段由 `test_dsh_native_bridge.py` 保持同步）。skill 内容始终只有一份（仓库 `skills/` + `adapters/dsh/skill-shims/`），不复制进预设，也没有第二份工具清单需要维护。

**项目投影（project projection）**：`launch.py --bootstrap-project <dir>` 写入项目根 `AGENTS.md`（thin pointer）。dsh 会自动把工作区的 `AGENTS.md` 注入会话，因此治理在任意预设下都能激活；文件只做指针与 SELF-CHECK，不重复 workflow 规则。

命令入口映射：dsh 的 `/name` 用户手势直接加载同名 skill。`commands/*.md` 是跨平台共享资产（其内容被其它平台的斜杠命令与测试直接消费），因此 DSH 不修改它们，而是用 `adapters/dsh/skill-shims/` 下的同名薄投影把它们暴露为 skill——`/governance`、`/governance-status` 等九条命令在 dsh 中成为一等 skill 入口。

Git hooks 发现（仅 legacy 目录形态）：旧路径会额外写入预设目录内的 `skill-root.txt`（包根路径标记），`infra/hooks/` 的 `find_spg_home` 据此发现包检出。native 路径不写该文件；hooks 仍可用既有的 `SOFTWARE_PROJECT_GOVERNANCE_HOME` / 仓库本地检出定位。

## 使用

```powershell
python adapters/dsh/launch.py                 # 查看 adapter manifest
python adapters/dsh/launch.py --install       # 手工/离线路径：渲染 ${DSH_HOME}/.agent-presets/governance/（4 个文件）——写侧守卫：真实用户根必拒 exit 2（write_side_refusal），仅限显式重定向 DSH_HOME 的隔离环境
python adapters/dsh/launch.py --install --dry-run   # 只打印将要写入的路径与 token 渲染映射，不落盘
python adapters/dsh/launch.py --smoke         # 隔离 DSH_HOME 下的预设加载冒烟闸门（0 PASS / 1 FAIL / 2 REFUSED）
python adapters/dsh/launch.py --bootstrap-project <项目目录>   # 写入项目级 AGENTS.md
git -C <仓库> pull    # 升级后：native 宿主重启即生效；用户根目录模型安装需**显式** launch.py --install（隔离 DSH_HOME；宿主行不自动渲染）
```

常用路径不需要 `--install`：`dsh plugin --profile web add "link:<本仓库绝对路径>"` + **重启**。在声明了 agent-preset registry 的宿主（0.2+）上，包内宿主行按能力检测走**原生派生**——不写用户根、不依赖包版本号、宿主工具变化自动跟随；未声明 registry row 的旧宿主（连同 disabled/unreadable/ambiguous 四种不可用态）一律只 warn、**不渲染用户根目录**（DEC-366 ②），目录模型需要显式 `launch.py --install`。

然后：启动 dsh 会话并选择「治理协调器」预设（或在被治理项目目录里直接开任意预设会话，由 `AGENTS.md` 激活）。原生宿主上该预设由宿主 registry 在启动时登记，选择器显示 `preset.yml` 的名称，不再依赖 `${DSH_HOME}/.agent-presets/` 目录是否存在。

### dsh 升级 / 重装后恢复接入

native 路径下预设是**运行时派生**：升级 dsh 后只需确保 bundle 注册仍在（下面的命令）并重启，无需重新渲染任何预设目录。

dsh 升级或 profile 清单重置/重装后，插件的 `dsh.profile.bundles` 注册可能丢失（profile 的 package.json 恢复模板态），bundle 层（`cordis.patch.yml`）不再应用——表现为非治理预设会话中 `/governance` 手势失效；bundle-only 安装时治理预设亦从预设选择器消失（经 `launch.py --install` 写入的用户根 `governance` 预设不受影响，其会话仍保有目录）。恢复方法（bundle 路径）：

```powershell
dsh plugin --profile web add "link:<本仓库绝对路径>"
```

然后重启 dsh——bundle 层是 boot-time 应用，非 HMR，不重启不生效。注意用户根预设（`${DSH_HOME}/.agent-presets/governance`）**不再由宿主行渲染**：bundle 宿主行只做 native 登记或 warn（DEC-366 ②），目录模型下刷新/重装一律走**显式** `launch.py --install`（`link:` 安装下 `git pull` 已更新 Junction 目标，显式重装后重启即生效）；`launch.py --sync` 不适用真实用户根（write_side_refusal 设计性拒绝，exit 2），仅限显式重定向 `DSH_HOME` 的隔离环境（冒烟/测试/离线渲染），且不恢复 bundle 注册。验证：重启后 profile 的 package.json 中 `dsh.profile.bundles` 应含 `@peterwangze/software-project-governance-plugin`；预设选择器应出现「治理协调器」（用户根 ⇒ 自定义预设，可删除、可打开目录）。

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
- `enforcement_host_guard`：**native**（FEAT-099 PoC 证实——自有 host row 注册 `ctx.tools.guard` 单调守卫，覆盖 `subagent`/`subagent_fork` 修订错配派发：带锚错配调用被真实 dsh-tools 管线拒绝且工具体未执行〔in-process 探针、隔离 DSH_HOME、2026-10-27〕；fail-closed 面齐备〔锚非法/投影不可读/开关非法保守拒绝〕、`off` 零注册、guard 面 p95 0.187ms。**未测面如实披露**：活体模型会话；无锚派发放行〔U7 强制缺口在案，协议面 MUST 携锚〕。PoC 级能力：expected 源为 fixture 投影，生产源（bootstrap 聚合机写投影）属后续批）。
- workflow closure：**degraded**（仅 browser 与 MCP 依赖主机），当前最强的原生能力画像。

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
