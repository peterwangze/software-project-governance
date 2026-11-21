# DeepSeek Harness Adapter

DSH 是 Tier 1 加载平台。治理预设加载[共享治理技能](../../skills/software-project-governance/SKILL.md)与角色。安装、升级和项目接入由本适配器维护。

DSH 保持已授权直修路径。可复现问题由执行者修复并重放原失败样本，验收者用同一单元执行独立成品验证。启动、返工及复审的命令见[工作单元运行协议](../../skills/software-project-governance/core/lifecycle.md)。

## 使用

在 DSH 和 pnpm 可用的环境中，选一种包来源加入实际使用的 profile，随后重启该 profile。以下以 `web` 为例。GitHub 来源需要 Git 和网络，运行 Python 启动器需要 Python 3。

```powershell
dsh plugin --profile web add "link:<仓库绝对路径>"     # 使用本地检出
dsh plugin --profile web add "file:<仓库绝对路径>"     # 或使用本地快照
dsh plugin --profile web add github:peterwangze/software-project-governance
```

`link:` / `file:` 两种 plugin add 与 launch.py 预设安装已在 Windows 验证。〔isolation: 2026-09-05，临时 DSH_HOME，dsh 0.1.2-rc.1，pnpm 11.22.0〕〔static: github: 依据 pnpm 的包规格〕

### 加载模型与会话入口

包的 `cordis.patch.yml` 插入一条自有行。启动时，该行读取宿主公开的 loader 组合树，找到可用的 agent-preset registry 和唯一可合并的 `standard` 声明。它向基础 persona 追加治理正文，向 `customSkillDirs` 追加包内 `skills/` 与 `adapters/dsh/skill-shims/`，其余宿主工具、顺序和禁用状态随当前基础预设继承。它经 `agentPresets.register` 登记 `governance`，卸载时释放登记，整个原生过程无需写预设目录。

宿主行遇到以下四种状态只告警并返回结构化原因，绝不写目录。**absent** 表示组合树中没有 registry 行，**disabled** 表示该行被禁用，**unreadable** 表示组合树无法枚举，**ambiguous** 表示基础声明缺失、重复或结构无法安全合并。按实际宿主能力选择入口；只有确需目录预设的旧宿主采用下文的显式安装。

- 原生登记完成后，「治理协调器」直接出现在预设选择器中。〔isolation: 2026-10-20，Windows，dsh 0.2.1-rc.2，隔离 profile〕
- 治理技能在治理预设的每个会话中可用。隔离验证同时检查了普通 `standard` 会话的技能目录。〔isolation: 2026-10-20，Windows，治理技能与命令投影只在 governance 会话内出现〕
- 选用治理预设后，用户输入 `/governance` 即加载统一治理入口。同名 skill 投影指向共享的 `commands/*.md`。〔live-session: 2026-07-08，dsh 0.1.0-rc.6 的 /name 手势〕

`python adapters/dsh/launch.py --bootstrap-project <项目目录>` 将治理指针写入项目的 `AGENTS.md`。同版本旧项目先追加 `--dry-run` 预览；确认后执行原命令，仅更新已有治理段并保留项目自有内容。DSH 会自动注入该文件；技能由所选预设提供。原生 `skill` 返回的 `resourceBase` 指向 `skills/software-project-governance/`。`ask_user_question` 负责用户交互，读写使用 `read`、`write`、`edit`、`grep`、`glob` 和 `pwsh`。派发时把角色定义、任务和调度模板交给 `subagent`；它没有 `isolation: "worktree"` 参数，会修改同一文件的任务需串行执行或使用独立工作树。

项目治理 hooks 缺失时提示一次；按需从 `skills/software-project-governance/infra/hooks/` 安装。hooks 可从仓库检出或 `SOFTWARE_PROJECT_GOVERNANCE_HOME` 定位包根，旧版显式安装还提供 `skill-root.txt`。

### dsh 升级 / 重装后恢复接入

| 包来源 | 更新或回退方式 |
|---|---|
| 本地 `link:` | 在检出目录执行 `git pull`，或切换至所需版本。 |
| 本地 `file:` | 移除快照，再从所需版本的本地目录添加。 |
| GitHub | `dsh plugin --profile web update @peterwangze/software-project-governance-plugin`；回退时移除再添加 `github:peterwangze/software-project-governance#<tag>`。 |

移除 bundle 使用 `dsh plugin --profile web remove @peterwangze/software-project-governance-plugin`。以上更改在 profile 重启后生效。若重装 DSH 或重置 profile 后预设消失，检查该 profile 的 `package.json` 中 `dsh.profile.bundles` 是否含本包，缺失则重新添加并重启。

### 旧目录模型的显式安装

先运行 `python adapters/dsh/launch.py --install --dry-run` 查看解析出的目录与写入计划。实际安装请在独立 PowerShell 会话中将 `DSH_HOME` 明确指向隔离目录。例如：

```powershell
$env:DSH_HOME = Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
python adapters/dsh/launch.py --install
```

启动器把包内组合模板渲染到该隔离根的 `.agent-presets/governance/`。更新或回退时选好包版本，再执行 `--install` 或 `--sync`。移除时用同一个隔离根执行 `--uninstall`。这些写操作指向真实用户根时退出码为 2；移除 bundle 只撤回 profile 登记，显式渲染的目录由启动器管理。`--smoke` 可在隔离根验证加载，`--check` 只打印适配器清单。

## 验证

```powershell
python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters
python skills/software-project-governance/infra/verify_workflow.py check-runtime-readiness-matrix
```

2026-11-19 在临时项目和隔离的 `DSH_HOME` 实测，桌面附带的 CLI（`dsh --version` 为 `0.2.2-rc.5`）支持用 `dsh --profile headless --json -` 从标准输入接收任务。出厂 headless 配置忽略 GUI 已保存的登录，API key 依次取自进程环境、当前目录的 `.env` 和 `$DSH_HOME/.env`。本次缺少可用 key，退出码为 1，未取得模型答复，成品验收仍需独立运行证据。

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

### 原生目标验收（FEAT-116）

使用治理预设的会话可由项目明确启用原生目标验收。在会话工作目录写入 `.governance/dsh-goal.json`，`intent_sha256` 填原生目标完整文本的 UTF-8 SHA-256，`max_rounds` 与创建目标时的原生轮次上限相同。`contract` 使用发布验收契约的字段，桥接会用原生目标 ID 补齐 `goal_id`。

```json
{
  "schema_version": 1,
  "intent_sha256": "<原生目标完整文本的 SHA-256>",
  "budget": {"max_rounds": 8, "max_tokens": 2000000, "max_seconds": 600},
  "contract": {
    "release_version": "0.1.0",
    "artifact": "dist",
    "entrypoint": "/",
    "producer": "delivery-agent",
    "verifier": "independent-qa",
    "criteria": {"user-journey": "从正常入口验证交付结果"}
  }
}
```

已验证的 DSH rc.3 通过兼容接线在自动目标轮及同轮后续原生模型步骤前等待 Python 判定。单个步骤内的宿主请求重试共用该步骤的判定。模型上下文只投影经判定的目标、治理预算信号及少量任务建议。工具与 Web 原生完成请求共用目标实例的完成判定，采用同一 Python 策略检查交付证据。已绑定的同一会话与目标保持约束，切换预设或删除项目配置会由判定重新处理。安装或重载宿主行后，日志中的 `GOAL_ADMISSION_REGISTERED` 表示找到并接入所需能力。未接入的宿主继续使用协议和 CLI 检查。

宿主从本目标已开始的轮数扣除正在执行的预约轮，得到已结束轮数。支持原生树预算的宿主记录 `TREE_BUDGET_REGISTERED`，按目标轮中的派发目录递归计入已确认的本地子会话，排除 fork 继承前缀。token 采用已结算事件报告的 `totalTokens` 下界，时间是树内已观测执行时间区间的并集。并行在途调用、缺失用量、不可读子分支及外部代理可能使实际成本更高。

达到 token 或时间阈值时，宿主拒绝关联会话的新模型请求及重试。策略先写入治理检查点，然后宿主暂停原生目标并中断关联子会话。尾部结算复核持久日志位置，缺失、尚未退出或刷新失败记录为 `INCOMPLETE`。重启后门禁读取同一 `tree_stop`，保持拒绝直到尾部结算结束、用户通过 `goal-bridge --action ruling` 作出裁决且较新原生轮通过准入。`goal-bridge --action status` 可查看 `tree_stop` 和已观测预算。

策略进程在治理包目录启动，使用宿主 `PATH` 中项目目录之外的绝对 Python 路径，忽略 `PYTHON*` 设置和用户 site-packages。策略进程出错、超时或回复不匹配时，已启用的目标调用会报告具体阻断代码。回执及验收证据的写入由独立验收者或受保护 CI 控制。

可选的 `.governance/dsh-goal-work.json` 记录同一目标已获授权的验证和修复工作包。使用相同的 `intent_sha256`，每个 `work_packages` 元素提供 `id`、`action`（`verify` 或 `repair`）、现有契约 `criteria`、`method`、`estimated_rounds` 和单行 `instruction`。`method` 可为 `exercise-entrypoint`、`build-release`、`inspect-evidence` 或 `repair-criterion`。侧文件在首次准入时随配置绑定。模型优先收到当前可执行的验收工作包，用户已有的授权继续适用。

### 交付前的零模型预检

在受信 DSH 宿主配置中，为治理插件行设置 `deliveryPreflight`，使用专门的隔离副本。配置指定一个新的 `sessionId`、绝对 `workspace`、副本外的绝对 JSON `receipt`，以及两项检查。工具命令由宿主配置提供，限于该副本已有授权的工作。示例中的浏览器脚本可使用项目的普通玩家入口。

```yaml
deliveryPreflight:
  sessionId: session-12345678-1234-4123-8123-123456789abc
  workspace: D:/scratch/preflight
  receipt: D:/scratch/preflight-result.json
  browser:
    command: python scripts/player-repro.py
    cwd: "."
  build:
    command: npm.cmd run build
    cwd: game
    artifact: game/dist/index.html
```

从认证的 DSH Web 创建指定 ID 和工作区的治理预设会话，使用回环模型配置并关闭标题生成等辅助推理。创建事件通过该会话的原生 Shell 运行检查，沿用 `workspace-write` 和宿主执行器。该副本的会话拒绝模型步骤。对同一个回执路径，独占标记保证只触发一次。预检进程退出前等候完整回执，同一 ID 恢复会话时不会重跑。

浏览器脚本在确实跑过玩家路径后，以最后一行 JSON 报告 `{"status":"PASS","player_path_executed":true}` 和退出码 0，或 `{"status":"FAIL","player_path_executed":true}` 和退出码 1。已知缺陷在实测路径中重现时，执行能力可以通过，回执仍记录产品行为失败。生产构建须退出 0，在配置路径生成本轮新的非空 HTML，并留下 SHA-256。预检携带会话、工作区、执行配方指纹和两项检查结果。只有两项均通过才返回 `PASS`，缺失、截断或不匹配的回执均应停止正式轮次。正式运行使用相同输入与工具链的另一份干净副本，其成品仍需通过独立验收。

#### 已复现缺陷的原生直修

受信治理插件行可为一个正式会话设置 `config.directRepair`。`workspace` 和 `sessionId` 指定正式副本，`preflightWorkspace` 和 `preflightSessionId` 指定另一份独立副本。`receipt` 是两份副本之外的预检回执绝对路径，`receiptSha256` 和 `recipeSha256` 固定该回执及配方。只接纳实际运行的浏览器路径报 `FAIL` 且生产构建通过的回执。

`intentSha256` 固定完整原始目标，`criterionId` 和 `workPackageId` 选择一个只覆盖该验收项的 `repair` / `repair-criterion` 工作包。`profileSha256` 对现有原生配置 JSON 添加 `work_sha256` 后计算 SHA-256，使用 ASCII 转义、递归排序的键、无空格分隔符和结尾换行。`work_sha256` 取工作包配置文件原始字节的 SHA-256。`sourceRoot` 与 `reproducer` 是项目相对路径，`sourceSha256` 取源目录下 POSIX 相对路径到文件 SHA-256 的排序紧凑 UTF-8 JSON，排除顶层 `node_modules` 和 `dist`。`reproducerSha256` 固定复现脚本原始字节。操作者应在启动前核对两边的冻结依赖和工具链。

宿主在指定会话的首个原生目标首次准入时校验两份源码和复现脚本。合格后，仅同一进程中同一目标及契约的准入可继续使用该提示。恢复旧目标、重建目标或提示无效时回到普通治理流程。工作包仍受预算和活跃任务重叠约束。当前独立验收结果优先，正式交付仍由独立回执放行。

`goal-bridge --action status --goal <原生目标 ID>` 的 JSON 在同一条记录中显示目标状态、预算和 `execution_packet`。该引用来自目标已有的持久状态，列出原生目标、交付契约摘要、验收项、工作包和预检回执摘要。重启后仍可追溯该关联。宿主每次准入仍须取得当前的直修凭据并检查实时独立验收、活跃任务和预算。

Windows rc.3 的 `workspace-write` 沙箱允许直接启动项目的 esbuild，Node 的具名管道连接可能返回 `EPERM`。`toolchain/Invoke-WorkspaceNpm.ps1` 可在同一个受限 PowerShell 中，用已安装的绝对 Python 路径启用锁定版本的工具链传输。

```powershell
& D:/workflow/adapters/dsh/toolchain/Invoke-WorkspaceNpm.ps1 -Workspace D:/scratch/preflight -ProjectRoot D:/scratch/preflight/game -PythonExecutable C:/Python314/python.exe -NpmArguments @('run', 'build')
```

传输只匹配已核对哈希的 Vite 5.4.21 和 Windows x64 esbuild 0.21.5。检测到该服务调用的 `EPERM` 时，它以一次性认证的回环连接将数据交给同一沙箱中的匿名管道，继续运行原 esbuild 二进制。Vite 可选的盘符探测收到原错误并沿用其默认路径解析。辅助脚本只对当前 PowerShell 调用设置环境变量。使用独立测试宿主时，可以把相同进程环境传给该宿主，使同一副本的普通 npm 命令使用相同传输。

## 资产

- `adapters/dsh/adapter-manifest.json`：机器可读的适配器元数据（能力声明 + E2E 证据）。
- `adapters/dsh/launch.py`：预设渲染器（渲染 + 原子换入）与项目 bootstrap 写入器。
- `agent-presets/governance/agent.cordis.yml.template`：预设组合模板（唯一组合事实源；token 由 `lib/index.js` / `launch.py` 渲染为绝对路径；**不直接挂载**，`.template` 后缀即防误挂载标记）。
- `agent-presets/governance/preset.yml`：预设元数据（roster 显示名与描述）。
- `lib/index.js`：bundle 插入的宿主行。启动时通过预设注册服务登记，若服务不可用则记录告警。
- `cordis.patch.yml`：bundle 补丁层——**只有一条 `- insert:`**（本包自己的行），不改任何宿主行（DEC-187）。
- `adapters/dsh/skill-shims/`：`commands/*.md` 的 DSH 薄投影（扁平 skill，name+description frontmatter）。
- `adapters/dsh/AGENTS.md.template`：DSH 项目级 bootstrap 模板（thin pointer）。

## 与其它适配器的差异

- dsh 是第一个「launcher 真正执行安装」的适配器（其它平台的 launch.py 只打印 manifest）——因为 dsh 预设是普通文件，安装即渲染写文件，无需任何平台内交互。
- 预设的 skill 根是**包内绝对路径**（渲染时写入），因此 `git pull` 即 skill 更新，且不存在「副本脱离包后 skill 目录为空」的问题；没有 copy/快照模式，也没有第二份 skill 树。
- 不需要 `resolve_entry.py` 的平台探测：DSH 下 PLUGIN_HOME 由 skill 的 resourceBase 直接给出（`resolve_entry.py` 的 `__file__` 自定位与 HOST_PROJECT_ROOT=cwd 的双根模型在 DSH 下原样成立）。
