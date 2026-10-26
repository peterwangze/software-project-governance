# FEAT-100 调研报告 — pi 平台加载机制与本仓 adapter 接线方案（0.98.0）

- **Task ID**: FEAT-100（P1，只读调研）
- **日期**: 2026-10-14 · **工作流版本**: 0.98.0 · **报告性质**: 调研事实 + 方案草案（不做最终决策）
- **调研对象**: npm 包 `@earendil-works/pi-coding-agent@1.1.0`（本机命令 `pi`）+ 本治理插件仓库 adapter 登记面
- **证据约定**: `<pi-pkg>` = `C:\Users\peter\AppData\Roaming\npm\node_modules\@earendil-works\pi-coding-agent`；`<repo>` = `D:\AI\agent\claude\coding\project_management_workflow`。命令证据标注退出码；文件证据标注路径+行号；未证实结论显式标注「未证实」。

---

## 1. 身份与版本

| 项 | 事实 | 来源 |
|---|---|---|
| 包名/版本 | `@earendil-works/pi-coding-agent` **1.1.0** | `<pi-pkg>\package.json` L2-3 |
| 定位 | "Coding agent CLI with read, bash, edit, write tools and session management"——终端可扩展 AI agent，给目标和工作目录即可检查文件/跑命令/编辑内容/多步任务 | package.json L4；`<pi-pkg>\docs\index.md` L3 |
| bin | `pi` → `dist/bundle/cli.js` | package.json L9-11 |
| 上游 | monorepo `github.com/earendil-works/pi`（directory `packages/coding-agent`）；作者 Mario Zechner；MIT | package.json L98-104 |
| 关联包 | `@earendil-works/{chord,pi-agent-core,pi-ai,pi-codemode,pi-mcp,pi-tui}` ^1.1.0 | package.json L50-55 |
| homepage 字段 | **无**（package.json 无 homepage 键）；事实入口 = 包内 `docs/`（随包分发，package.json L34）与站点 `pi.dev`（quickstart 安装脚本 URL；`PI_SHARE_VIEWER_URL` 默认 `https://pi.dev/session/`） | package.json 通读；`<pi-pkg>\docs\quickstart.md` L12；`pi --help` 输出（exit 0） |
| 运行要求 | Node.js ≥ 22.19.0（npm 安装路径）；npm 安装建议 `--ignore-scripts` | package.json L105-107；quickstart.md L15-19 |
| 本机安装 | `pi.ps1` shim 存在于 `C:\Users\peter\AppData\Roaming\npm\pi.ps1`（Test-Path=True，exit 0）；`pi --version` → `1.1.0`（exit 0） | pwsh 只读探测（本会话） |
| pi-web-ui | `pi-web-ui@0.102.0` 已装（description: "Just open your browser to get all your work done — browser cockpit for AI coding agents (chat, code, files, terminal, Git in one tab)"）——独立浏览器驾驶舱包，与 CLI 的集成面不在本任务范围 | `C:\Users\peter\AppData\Roaming\npm\node_modules\pi-web-ui\package.json`（读取 version/description，exit 0） |
| 1.1.0 能力面要点 | OSC 7501 程序状态上报、Claude Haiku 5.5、`--tools` 支持 `+name/-name` 增减、GPT-6 Luna 分类器、llama.cpp 原生决策模型（2026-10-07 发布） | `<pi-pkg>\CHANGELOG.md` L3-11 |
| SDK/RPC 面 | `./rpc-entry`、`./experimental/plugin` 导出；自动化面 = print mode / JSON 事件流 / RPC / TypeScript SDK 四通道 | package.json L19-27；docs\index.md L26-29 |

## 2. 项目上下文加载机制

pi 的「项目上下文」分两层：**context files（无需信任，永远加载）** 与 **项目 `.pi/` 配置（信任门后加载）**。

| 机制 | 事实 | 来源 |
|---|---|---|
| Context files 文件名 | `AGENTS.override.md`、`AGENTS.md`、`AGENTS.MD`、`CLAUDE.md`、`CLAUDE.MD`——**同时兼容 AGENTS.md 与 CLAUDE.md 两族** | `<pi-pkg>\docs\configuration.md` L18、L41-47 |
| 发现范围 | agent 目录（`~/.pi/agent`）+ 工作目录 + 工作目录的父目录逐级向上；「A context file applies whenever Pi runs in its directory or anywhere below it」 | configuration.md L43 |
| override 语义 | `AGENTS.override.md` 仅替换**同目录**的 `AGENTS.md`/`CLAUDE.md`，不抑制 agent 目录或其他目录的 context file | configuration.md L45 |
| 信任关系 | Context files 发现**不需要项目信任**，declining trust 也照样加载 | `<pi-pkg>\docs\security.md` L57；configuration.md L47 |
| 关闭开关 | `-nc, --no-context-files` 禁用 AGENTS.md/CLAUDE.md 发现 | `<pi-pkg>\docs\cli.md` L214-215；`pi --help`（exit 0） |
| 项目 `.pi/` 目录 | `.pi/settings.json` / `.pi/mcp.json` / `.pi/SYSTEM.md` / `.pi/APPEND_SYSTEM.md` / `.pi/extensions/` / `.pi/skills/` / `.pi/prompts/` / `.pi/themes/`——**信任门后加载**（package.json `piConfig.configDir: ".pi"`，package.json L6-8） | configuration.md L26-39、L3 |
| `.agents/skills/` | Agent Skills 规范位置：项目 `.agents/skills/` 从工作目录沿祖先发现（存在仓库根时止于仓库根）；用户级 `~/.agents/skills/`；**项目 `.agents/skills` 受项目信任保护** | `<pi-pkg>\docs\skills.md` L61；security.md L43 |
| 系统提示词改写 | `<agent-dir>/SYSTEM.md` 或 `.pi/SYSTEM.md` 整体替换默认 system prompt；`APPEND_SYSTEM.md` 追加；CLI `--system-prompt` / `--append-system-prompt` | configuration.md L19-20、L32-33；cli.md L229-231 |
| rules/其他入口 | 除上述外无其他项目指令入口（docs 全量通读未见 `.pirules`/`.rules` 等机制）——「未发现」基于 docs 44 文件通读 + grep，非穷尽二进制审计 | docs 目录 glob（44 md）+ 定向 grep |

**对本仓的含义（推理，标注）**：本仓根已有 `AGENTS.md` + `CLAUDE.md` 双入口——pi 在本仓 cwd 启动时会**原生自动加载两者**（与 Chrys 的加载路径同构，adapters/chrys/README.md L18-25），零平台配置即获得治理 bootstrap 上下文。

## 3. Skills / 命令 / 扩展 / 插件 / MCP 机制

### 3.1 Skills（Agent Skills 规范兼容）

| 项 | 事实 | 来源 |
|---|---|---|
| 格式 | 目录含 `SKILL.md`（YAML frontmatter `name`/`description` + 正文指令），可带 `scripts/`/`references/`/`assets/` | `<pi-pkg>\docs\skills.md` L11-35 |
| 规范 | 实现 Agent Skills 规范（agentskills.io）；无效字段告警不阻断启动 | skills.md L7 |
| 加载模型 | 启动时扫描已配置 skill 位置，把每个 skill 的 name/description/path 注入 system prompt；**完整指令按需加载**（任务匹配时模型自行读 SKILL.md） | skills.md L43-45 |
| 强制调用 | `/skill:name [args]`（args 追加为用户请求）；`disable-model-invocation: true` 可隐藏出自动路由；`enableSkillCommands` 设置控制命令发现 | skills.md L47-53；settings.md L156 |
| 发现位置 | 用户/项目 skills 目录（递归发现含 SKILL.md 的目录）+ `~/.agents/skills/` + `.agents/skills/` + settings `skills` 路径数组 + Pi 包 | skills.md L59-63；settings.md L152-153 |
| frontmatter 字段 | name/description/license/compatibility/metadata/allowed-tools（实验）/disable-model-invocation；name 小写连字符 ≤64 字符，description ≤1024 | skills.md L69-81 |
| 命名宽容 | 声明名与目录名不一致不告警（其他实现可能强制，建议一致） | skills.md L83 |
| 冲突 | 同名冲突保留先发现者 + 告警 | skills.md L85 |
| 热载 | `/reload` 重载 skills/extensions/templates/themes/context files | skills.md L89；slash-commands.md L49 |

### 3.2 自定义斜杠命令（prompt templates）

- Markdown 文件 → `/`命令：文件名即命令名；frontmatter `description`（缺省用第一个非空行）、`argument-hint`；`$1`/`$@`/`${1:-default}`/`${@:N:L}` 位置参数替换（`<pi-pkg>\docs\prompt-templates.md` L9-49）。
- **常规 prompt 目录只加载直接 `.md` 子文件**（不递归子目录）；settings/prompts/包可经 glob 选嵌套文件（prompt-templates.md L55-57）。
- pi 无 Claude 式 `commands/` 目录约定——本仓 `commands/*.md` 若要成为 pi 命令，经 `prompts` 机制接线（见 §8）。

### 3.3 扩展（extensions）与插件（Pi Packages）

- 扩展 = 加载进 pi 进程的 TypeScript 模块（jiti 免编译），工厂函数收 `ExtensionAPI`，可注册：工具 `registerTool`、命令 `registerCommand`、快捷键/CLI 旗标 `registerShortcut/registerFlag`、provider `registerProvider`、MCP server `registerMcpServer`、虚拟模型、渲染器、事件处理器（`<pi-pkg>\docs\extensions.md` L15-38、L73-87）。位置：`<agent-dir>/extensions/`、`.pi/extensions/`、`-e` 显式路径、包（extensions.md L44-48）。
- **Pi Packages = pi 的官方分发包机制**：普通目录或 npm 包即可，惯例目录 `extensions/ skills/ prompts/ themes/` 自动发现；或 `package.json` 的 `pi` manifest 显式声明路径（packages.md L44-72）；`pi-package` keyword 使 npm 包入 pi.dev 包画廊（packages.md L74）。
- 安装：`pi install npm:@scope/pkg@ver | git:… | <本地路径>`；**个人安装写入 `~/.pi/agent/settings.json` 的 `packages` 数组**，`--local/-l` 写项目 `.pi/settings.json`（packages.md L9-19）；npm 包实体装到 `<agent-dir>/npm/node_modules/`（本机 `pi list` 实证，exit 0）；本地路径源**不拷贝、按解析路径原位加载**（packages.md L36, L40）；单次试用 `pi -e <pkg>`（packages.md L23-27）；资源过滤对象形态 + `pi config` TUI（packages.md L96-121）。

### 3.4 MCP

- 全局 `<agent-dir>/mcp.json` + 项目 `.pi/mcp.json`（信任门后；configuration.md L15、L31；security.md L39）。
- CLI 管理：`pi mcp add/remove/list/login/logout`（stdio 与 streamable HTTP + OAuth；cli.md L320-331）；内置 `builtin:mcp` 扩展默认开启（settings.md L160）；扩展内 `pi.registerMcpServer()`（extensions.md L194-203）；`--tools 'mcp__<server>__*'` 过滤与 `--no-mcp`（cli.md L130-138）。

## 4. 交互与 agent 能力面（对齐 adapter-manifest 声明字段）

| 能力键 | 判定 | 证据 |
|---|---|---|
| `ask_user_question` | **无原生 ask-user 工具**。内置工具仅 read/bash/powershell/edit/write/grep/find/ls（`pi --help` "Built-in Tool Names" 节，exit 0；cli.md L140-149）。docs 全量 grep 正则（ask_question、askUser 两词）零命中；`--help` 示例中 `--exclude-tools ask_question` 仅为扩展示例名（**未证实**为任何内置工具）。可达路径：扩展注册 `model-only` 工具问用户（extensions.md L157）、`ctx.ui.confirm`/dialogs（L174、L244）、RPC 模式可转发对话框（L250；rpc-extension-ui.md）——但 JSON/print 模式无 UI（extensions.md L250-251）→ **headless 场景无交互通道**。本机装有 `@narumitw/pi-plan-mode` 包（`pi list`，exit 0）有无 ask-user 类工具**未证实** | 如左 |
| `sub_agent` | **无原生子代理机制**。docs 全量 grep 正则（subagent、sub-agent、spawn.*agent、delegate 四式）仅无关命中。替代面：扩展内嵌套模型调用 `ctx.modelRegistry.streamSimple()`（extensions.md L212）、`codemode` 工具并行编排工具调用（cli.md L155）、SDK 进程内嵌 agent（docs\index.md L29）——均非 Agent Team 式角色子代理 → **unsupported**（诚实降级，参照 opencode 先例 adapters/opencode/adapter-manifest.json L41-45） | 如左 |
| `tool_calling` | **native**。8 内置工具；`powershell` 仅原生 Windows（windows.md L47，`-NoProfile -NonInteractive -ExecutionPolicy Bypass`，windows.md L35）；`--tools/-t` 允许列表 + `+name/-name` 增减 + `*` 模式 + `--exclude-tools`（cli.md L119-128；settings.md L40-58）；本机 defaultTools 已 +powershell/+grep/+find/+ls/+codemode/+tool_search（`C:\Users\peter\.pi\agent\settings.json` L18-29） | 如左 |
| `browser` | 无内置浏览器自动化工具（内置工具表无；docs 未见）→ **unsupported**。本机装有 `pi-web-access@0.38.0` 包（`pi list`，exit 0）是否构成可声明浏览器通道**未证实** | 如左 |
| `mcp` | **degraded（host-dependent）**：机制 native（§3.4），服务器可用性取决于主机配置——与本仓 chrys/dsh 同口径（adapters/chrys/adapter-manifest.json L55-59） | 如左 |
| `git_hooks` | pi 无自带 git-hook 机制（docs 未见）；治理 hook 是**仓库级**控制（pre-commit/commit-msg/post-commit 安装进 `.git/hooks/`），独立于 agent 运行时 → 按本仓先例记 **native（仓库级）**（adapters/chrys/adapter-manifest.json L60-63 同款论证） | 如左 |
| exploration_channels 四通道（M10.3） | discover=**unsupported**（无原生 web 搜索工具；pi-web-access 未证实）；inspect=**native**（read/grep/find/ls）；consult=**unsupported/degraded**（无子代理、无已验证外部专业源通道；生成≠咨询——FIX-432 规则）；validate=**native**（bash/powershell 执行 verify_workflow.py）。consult 不得映射任何生成通道（QUOTE_SYNC 规则，verify_workflow.py L12072-12088） | 如左 |

## 5. 配置与全局注册

| 项 | 事实 | 来源 |
|---|---|---|
| 配置目录 | 默认 `~/.pi/agent`；`PI_CODING_AGENT_DIR` 环境变量覆盖；SDK `agentDir` 选项 | configuration.md L9；environment-variables.md L81 |
| 会话目录 | `PI_CODING_AGENT_SESSION_DIR` 覆盖；`--session-dir` 优先级更高；`sessionDir` 设置 | environment-variables.md L82；cli.md L96-97；settings.md L64 |
| 包目录 | `PI_PACKAGE_DIR` 覆盖（Nix/Guix 用） | environment-variables.md L83 |
| agent 目录文件面 | settings.json / keybindings.json / mcp.json / models.json / auth.json / AGENTS.md（等 5 变体）/ SYSTEM.md / APPEND_SYSTEM.md / extensions/ / skills/ / prompts/ / themes/ / trust.json / sessions/ / npm/ | configuration.md L11-24；security.md L67-73；本机实测目录列表（Get-ChildItem，只读） |
| 本机现状 | `C:\Users\peter\.pi\agent\` 已存在且在用：settings.json、AGENTS.md、mcp.json、models.json、auth.json、provider-keys.json、bin/、npm/、sessions/、web-search-cache/ | pwsh 只读列目录（本会话） |
| 本机全局注册实证 | settings.json `packages`=[pi-web-access@0.38.0, @upstash/context7-pi@0.1.2, @narumitw/pi-plan-mode@0.59.2]（L12-16）；**`skills`=["D:/AI/agent/pi/developer-kit/skills"]、`prompts`=["D:/AI/agent/pi/developer-kit/prompts"]（L40-45）——用户已用 settings 路径数组模式外接外部 skill/command 目录**；defaultProvider=cc-switch-zhipu-glm / glm-5.3-flash（L38-39） | `C:\Users\peter\.pi\agent\settings.json` L1-46（只读） |
| 外部 skill/command 包「全局接线」官方机制 | 四选一：① `pi install <source>` → 写 settings.json `packages`（npm/git/本地路径，本地不拷贝）；② settings.json `skills`/`prompts`/`extensions` 路径数组（支持绝对路径/~/glob 排除）；③ drop-in 到 `<agent-dir>` 下 skills／prompts／extensions 三惯例目录；④ 单次 `-e/--skill/--prompt-template` 旗标 | packages.md L9-19；settings.md L149-158；configuration.md L21-24；cli.md L194-207 |
| 项目信任 | 受保护资源（.pi/settings.json、.pi/mcp.json、.pi/{extensions,skills,prompts,themes}、.pi/SYSTEM*.md、项目 .agents/skills）触发信任决策；决策序：CLI `--approve/--no-approve` → 扩展 project_trust 事件 → 已存决策（trust.json）→ `defaultProjectTrust`（默认 ask）；**print/JSON/RPC 无信任提示**，ask/never 时跳过受保护资源 → 自动化运行必须显式 `-a` 或 `-na` | security.md L37-45、L61-82 |

## 6. 无头/冒烟方式（`pi --help` 实测为准）

实测 `pi --version` → `1.1.0`（exit 0）；`pi --help`（exit 0）关键旗标（与 `<pi-pkg>\docs\cli.md` L43-49 一致）：

| 旗标 | 用途（隔离冒烟相关） |
|---|---|
| `-p, --print` | 一次性执行 prompt，最终回复写 stdout 后退出（`pi -p "…"`） |
| `--mode json` / `--mode rpc` | JSONL 事件流 / RPC 协议（stdout 保留给协议记录） |
| `--session-dir <dir>` / `--no-session` | 会话存储重定向 / 内存会话不落盘 |
| `-c/--continue`、`-r/--resume`、`--session/--session-id/--fork` | 会话恢复/分支 |
| `--tools read,grep,find,ls` / `-xt` / `-nt` / `-nbt` | 只读工具子集（E2E 用「Read-only mode」先例在 help Examples 节） |
| `-e/--extension`、`--skill`、`--prompt-template` | 单次显式加载资源（**免 settings 写入即可冒烟**） |
| `-nc/--no-context-files` | 禁 AGENTS.md/CLAUDE.md 发现 |
| `-a/--approve`、`-na/--no-approve` | 一次性项目信任/拒绝（headless 必需） |
| `--offline`（=PI_OFFLINE=1） | 禁启动网络操作 |
| `-v/--version`、`-h/--help` | 版本/帮助 |

- stdin/stdout 重定向且未选 json/rpc 时自动进入 print 模式（cli.md L30）——CI 管道天然无头。
- 本会话已验证的只读探测：`pi --version`（exit 0）、`pi --help`（exit 0）、`pi list`（exit 0，列 settings 注册包与实体路径）。

## 7. 本仓 adapter 模式对照（新增平台需要落位的文件面）

### 7.1 三例 adapter 模式

| 维度 | chrys | opencode | dsh |
|---|---|---|---|
| entry_type | half-executable（adapter-manifest.json L4） | thin-projection（L4） | thin-projection（L4） |
| 加载模型 | 原生 AGENTS.md/CLAUDE.md 上下文 + 原生 `load_skill` 工具（README L5-25） | AGENTS.md 薄指针 → SKILL.md（README L33-45） | 渲染 agent preset（`${DSH_HOME}/.agent-presets/governance/`）+ AGENTS.md 注入 + skill-shims（README L9-19） |
| launcher 行为 | 只打印 manifest（launch.py 全文） | 只打印 manifest | **真安装**：`--install` 渲染预设（写侧守卫：真实用户根拒 exit 2，仅隔离 DSH_HOME）+ `--smoke` + `--bootstrap-project`（README L23-30） |
| 能力画像 | ask_user/sub_agent/tool_calling/git_hooks native（manifest L37-69） | 全 degraded/unsupported 除 git_hooks（L35-69） | 与 chrys 并列最强（L38-70） |
| 验证命令 | `python adapters/chrys/launch.py` + `check-agent-adapters [--runtime]`（README L31-40） | + `opencode-provider-preflight` + `agent-runtime-e2e --agent opencode --timeout 90`（README L49-66） | + `check-runtime-readiness-matrix`、`dsh-doctor`（README L48-53；manifest L36） |
| plugin 包目录 | `.chrys-plugin/plugin.json` | — | —（包内 `agent-presets/` + `lib/` 宿主行 + `cordis.patch.yml`） |

**pi 对号入座（事实推断）**：pi 无「plugin.json 目录」平台约定（§3.3）——pi 的包单位是 Pi Package（package.json `pi` manifest / 惯例目录）或 settings 路径注册。dsh 先例证明非 marketplace 平台**不需要** dotfile 插件目录（SKILL.md 平台表 L494-499 中 gemini/opencode/chrys 的 plugin 包列均为「—」）。→ **pi 走三件套（README + adapter-manifest.json + launch.py）即可；是否追加根 package.json `pi` manifest 是方案选择（§8），不是登记面硬要求**。

### 7.2 登记点清单（新增 pi 必须同步的全部位置，grep 实证行号）

**skills/software-project-governance/infra/verify_workflow.py**（28,204 行）：

| 登记点 | 行号 | 内容 |
|---|---|---|
| `PLUGIN_SCOPE_DIRS` | L340-357 | 插件边界目录集（若建 `.pi-plugin` 类目录才需加；三件套方案不加） |
| `REQUIRED_FILES` | L540-561（chrys 行 L550-553） | 每平台 3-4 行（Adapter/Manifest/Launcher/PluginDefinition） |
| `REQUIRED_SNIPPETS` | L788 起（chrys 块 L654-677、`.chrys-plugin` L689-692） | 每平台文件必需 token |
| `MAINSTREAM_AGENT_ADAPTERS` | **L1609** | `["claude","codex","gemini","opencode","chrys","dsh"]` → +`"pi"`（FEAT-101 同步 -`"chrys"`） |
| `ADAPTER_REQUIRED_KEYS` | L1610-1624 | 14 必需键（adapter_id…launcher）——manifest schema 合约 |
| `RUNTIME_MATRIX_AGENT_IDS` | **L2366** | 同上 +cursor/copilot（research-only L2367） |
| `MAINSTREAM_AGENT_LOADING_REQUIRED_DOCS` | L2369-2378 | +`adapters/pi/README.md` |
| `MAINSTREAM_AGENT_LOADING_TIER1` | L2379-2386 | +`"Pi"` 显示名（**大写显示名——case-sensitive grep 会漏，见 §9.3**） |
| `MAINSTREAM_AGENT_LOADING_ADAPTERS` | L2394-2483（chrys L2455-2469） | +pi dict（display/path/tokens） |
| `RUNTIME_CAPABILITY_KEYS` / `ADAPTER_RUNTIME_CAPABILITY_POLICY` | L5410-5417 / L5421-5470（chrys L5454-5461） | +pi 能力策略行（与 manifest runtime_capabilities 机检一致性，`_validate_runtime_capabilities` L5473+） |
| `check_agent_adapter_contract` | L6009-6034（消费 L1609） | 自动覆盖新 adapter |
| `check_runtime_readiness_matrix` | L3175-3213 | 要求矩阵文档含每个 RUNTIME_MATRIX_AGENT_IDS 行 + manifest 状态/version_command 一致 |
| `QUOTE_SYNC_ADAPTER_MANIFESTS` | **L12080-12087** + `CONSULT_DRAW_MARKER` L12088 | 六平台 manifest 元组 → +`adapters/pi/adapter-manifest.json`；其 exploration_channels.note MUST 含「生成≠咨询」标记（FIX-432） |
| `AGENT_RUNTIME_E2E_PLATFORMS` | **L20094-20097** | `("claude","codex","gemini","opencode")`——dsh 因无 headless runner 被刻意排除（注释 L20094-20096）；**pi 有 `-p` → 可入选**，需同时在 `_agent_runtime_e2e_command_matrix`（L20110-20159+，字面量命令表，cwd=project/e2e-test-project）加 pi 命令条目 |

**其余登记文件**：

| 文件 | 行号 | 登记内容 |
|---|---|---|
| `core/manifest.json` | L7-37（projection_ids）、L317-324（canonical .chrys-plugin 条目）、L924-938（cleanup_scope.directories） | 仅当建 pi 专用版本投影/目录时（见 §8 决策点） |
| `core/version-projections.json` | chrys-plugin 投影 L56-61；`package` 投影 L62-67 | 同上；**根 package.json 已是版本投影面**（`/version`） |
| `infra/checks/version.py` | `VERSION_PATHS` L10-18 | 同上 |
| `infra/quickscan_registry.py` | L281、L302、L401（`.chrys-plugin/**` 资产段） | 若建 `.pi-plugin/` 需同步三段 |
| `infra/cleanup.py` | `PLUGIN_SCOPE_DIRS` L46-63（与 verify 同步合约，FIX-053） | 同上 |
| `infra/checks/projection.py` | L43（source Chrys plugin） | 同上 |
| `infra/checks/triage_domain.py` | L91（`.chrys-plugin/`） | 同上 |
| `infra/contract_matrix/golden_samples.txt` | L97、L283-295、L1358（chrys 契约金样） | adapter 集变更后需再生成/更新 |
| `skills/software-project-governance/SKILL.md` | L492-500 适配层平台表 | +Pi 行（三列语义：平台名 Pi、adapter 路径 adapters/pi/、plugin 包 —）（e2e 镜像 `project/e2e-test-project/skills/.../SKILL.md` L498 由 byte_copy 投影随发布同步） |
| 根 `README.md` | L26-34 Tier 1 表 | +Pi 行（zcode 行 L34 先例） |
| `docs/requirements/runtime-readiness-matrix-0.43.0.md` | Summary 表 + 运行时结果表 | +pi 行（check L3175 消费此文档——**改代码常量必须同步改此文档行**，否则 FAIL） |
| `docs/requirements/mainstream-agent-loading-0.47.0.md` | 平台表 | +Pi 行（check-mainstream-agent-loading 消费） |
| `infra/tests/test_verify_workflow.py` | L2722（`_write_all_adapters` 六元循环）、L2601-2618/L3347-3360（matrix/adapter 夹具）、L900-1016（FIX-182 plugin.json 覆盖测试） | 夹具需 +pi（FEAT-101 同步 -chrys） |
| `.github/workflows/ci.yml` | manifest-consistency 四处同步合约（EVD-647：canonical files + verify PLUGIN_SCOPE_DIRS + cleanup PLUGIN_SCOPE_DIRS + cleanup_scope.directories） | 仅当新增 top-level 目录时相关 |

## 8. 本机接线方案草案（FEAT-100 第二段「完成适配后接本机的 pi agent」）

### 8.0 事实基线

- 用户本机已用 **settings 路径数组模式**外接 `D:/AI/agent/pi/developer-kit/{skills,prompts}`（settings.json L40-45）——方案 A 与用户现有用法同构。
- pi 上下文层零成本：在本仓/被治理项目 cwd 运行 pi 即自动加载 `AGENTS.md`（§2）。
- dsh 先例：skill 根用**包内绝对路径**注册（`git pull` 即更新，无副本脱离问题——adapters/dsh/README.md L81；SKILL.md L504）。

### 8.1 方案 A — settings 路径注册（最小侵入，不修改根 package.json）【推荐评估项】

1. **skills**：`~/.pi/agent/settings.json` 的 `skills` 数组追加 `"D:/AI/agent/claude/coding/project_management_workflow/skills"` → pi 递归发现 `skills/*/SKILL.md`：software-project-governance 主 skill + 全部子 skill/阶段 skill 成为 `/skill:name` 命令（skills.md L59；settings.md L153；`enableSkillCommands` 本机已开，settings.json L37）。对齐 dsh `customSkillDirs` 行为（SKILL.md L504）。
2. **commands 投影**：pi prompts 惯例目录只加载直接 `.md` 子文件（prompt-templates.md L55）——`commands/` 的 9 个顶层 `.md` 恰好是直接子文件（`commands/governance/` 子目录拆分文件不会被误注册，且它们本就设计为 Read 按需读取，commands/governance.md L5）。因此 settings `prompts` 数组直接追加 `"<repo>/commands"` **可能无需 dsh 式 shims**。⚠️ 两个待验证点（本调研未实测）：① pi prompts 的 description 回退「第一个非空行」——commands 文件首行是 `# /governance — …` 标题，可用性待确认（prompt-templates.md L19）；② `${1:-default}`/`$1` 替换语法会不会与 commands 文件内潜在 `$` 字面量冲突（prompt-templates.md L38-47）→ **冒烟时必须逐命令验证展开结果**；不通过则退回 dsh 式 `adapters/pi/skill-shims/` 薄投影。
3. **项目级激活**：被治理项目根 `AGENTS.md` 薄指针（先例 `adapters/dsh/AGENTS.md.template`）——pi 原生加载，零平台配置。

### 8.2 方案 B — Pi Package 本地包注册（pi 原生管理面）

1. 根 `package.json` 增 `"pi": {"skills": ["./skills"], "prompts": ["./commands"]}` manifest + `keywords` 追加 `"pi-package"`（packages.md L57-74；package.json 现状 L8-18）。
2. 本机执行 `pi install D:/AI/agent/claude/coding/project_management_workflow`（本地源不拷贝、原位加载，packages.md L36/L40）→ 写 `~/.pi/agent/settings.json` `packages` 数组。
3. 得到 `pi list` / `pi config` / `pi update <source>` 原生管理；代价 = 修改根 package.json（**已是版本投影面** `package` L62-67，且 `files` 白名单 L28-40 需评估是否影响 pi 对 skills/ 的发现——本地路径源不走 npm 打包，`files` 不生效【推理：files 仅约束 npm publish tarball；标注待确认】）。

### 8.3 不推荐：方案 C — drop-in 拷贝/链接到 `~/.pi/agent/skills/`

违反单一事实源（dsh 明确拒绝 copy/快照模式——第二份 skill 树，adapters/dsh/README.md L81）。仅存档为否决项。

### 8.4 隔离冒烟（真实环境防护 R1 三选一之 a——环境变量重定向）

pi 提供完整重定向面（§5/§6）：`PI_CODING_AGENT_DIR`（整个配置+包根）、`PI_CODING_AGENT_SESSION_DIR`/`--session-dir`（会话）、`PI_PACKAGE_DIR`（包实体）。分层冒烟草案：

| 层 | 命令草案（pwsh） | 验证点 | 状态 |
|---|---|---|---|
| L0 静态 | `python adapters/pi/launch.py`；`python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters` | launcher 输出 + 契约 7/7 | 对齐先例（chrys README L31-34） |
| L1 注册面（全隔离） | `$env:PI_CODING_AGENT_DIR="<tmp>\pi-smoke\agent"; pi list`（隔离 settings 中预写 packages/skills 条目或 `pi install <repo>` 后再 `pi list`） | 包/skill 注册可解析、`pi list` 列出本仓 | 机制已证实（pi list 本机 exit 0）；具体冒烟脚本**未实测** |
| L2 skill 发现（免写 settings） | `pi --skill <repo>/skills/software-project-governance --no-session --offline -p "<探针>"`（`--skill` 单次加载，cli.md L200-203） | 启动诊断/skill 注册可见 | **未实测**（`-p` 需模型凭证；`--offline` 禁网络但模型调用仍需 auth.json——隔离目录无凭证时该层与 L3 合并） |
| L3 agent-runtime E2E | 在 `_agent_runtime_e2e_command_matrix` 加 pi 条目：`pi -p "<E2E 探针>" --tools read --no-session`（cwd=project/e2e-test-project；探针先例 `_agent_runtime_e2e_prompt` L20100-20107，判据 `E2E_PLATFORM=pi; E2E_AGENT=…`） | 真实 pi 读 target-cwd 治理事实并返回结构化字段 | **未实测**；需模型凭证（本机真实 settings 配有 cc-switch-zhipu-glm，settings.json L38-39）——见开放问题 O-5 隔离口径 |

- 推荐验收措辞（真实环境防护先例）：L1 用「隔离环境安装冒烟（环境变量重定向至临时目录）通过」；L3 属真机 E2E，须在凭证与写入面口径获批后执行（会话写入可用 `--no-session` 消除）。

## 9. 风险与开放问题

### 9.1 需要用户/Coordinator 决策的开放点

| # | 开放问题 | 影响 |
|---|---|---|
| O-1 | **接线机制二选一**：方案 A（settings 路径数组，与用户现用 developer-kit 模式同构、零包改动、无 pi update 管理）vs 方案 B（Pi Package，pi 原生管理面、动根 package.json 版本投影面）。`launch.py --install` 是否学 dsh 做真安装器（含写侧守卫） | adapter 设计与 change-triage 文件面直接取决于此 |
| O-2 | **能力面降级确认**：pi 无原生 ask_user、无原生 sub_agent（§4）→ 治理工作流在 pi 上 = 单 agent 降级模式（交互边界走外宿主会话、Agent Team 不可原生承载、复审必达等 MUST 契约的可执行性受限）。按 opencode 先例可诚实声明 degraded 入册，但**须用户知情**这是「加载可用 ≠ 完整治理闭环」 | adapter-manifest 能力声明 + README 边界措辞 |
| O-3 | **commands 是否需要 pi 版 shims**：prompts 直接注册 `commands/` 依赖两个未验证点（§8.1-2）；若冒烟不过需 `adapters/pi/skill-shims/`（dsh 先例）→ 文件面 +1 目录 | change-triage 清单 |
| O-4 | **pi 是否加入 AGENT_RUNTIME_E2E_PLATFORMS**：pi 有 `-p` headless（对比 dsh 被刻意排除，verify_workflow.py L20094-20097）→ 技术可入；但需 E2E 命令条目 + 凭证口径 | L3 验收路径 |
| O-5 | **E2E 隔离口径**：全隔离 `PI_CODING_AGENT_DIR` 无 auth.json → 模型调用不可用；备选 = 真实 agent-dir（含凭证与既有包）+ `--no-session` + 只读 `--tools read` 的混合口径（写面=0，读面=真实）——是否符合「隔离环境」标准需 Coordinator 裁定 | 冒烟方案合法性 |
| O-6 | **skill 全量暴露语义**：`skills/` 目录注册会把主 skill + 25 个子 skill 全部注入 system prompt 路由面（skills.md L43-45）——上下文成本与路由质量依赖各 SKILL.md description（skills.md L37 警告）；是否需要收窄（如仅注册主 skill + 关键子集）待权衡 | 使用体验 |
| O-7 | **版本锚点**：pi 1.1.0 迭代快（CHANGELOG 高频）；机制面（skills/prompts/packages）无稳定性承诺。建议 adapter 记录验证版本锚点（dsh host-contract.json 先例，adapters/dsh/README.md L67-76） | 维护策略 |
| O-8 | **FEAT-100/FEAT-101 时序与版本号**：若同期 ±chrys +pi，MAINSTREAM_AGENT_ADAPTERS 等常量一次性改；版本号（0.98.x patch vs 0.99.0 minor）归 Coordinator/用户 | 发布流程 |
| O-9 | **Windows 特有**：pi 原生 Windows bash 工具走 Git Bash（本机 shellPath 已配 `C:\Program Files\Git\bin\bash.exe`，settings.json L17）；powershell 工具原生 Windows 可用（windows.md L47）→ 工具映射表建议按 dsh 先例给 pi 会话替换示例（SKILL.md L509-514）。治理 hook 的 `find_spg_home` 无需 pi 候选路径：pi 经 settings **绝对路径**引用包内 skills（推理：hook 自升级路径解析与 pi 无耦——标注为推理） | SKILL.md 平台说明段 |
| O-10 | **命名冲突**：pi skill 同名冲突 keep-first + 告警（skills.md L85）；用户 developer-kit 已注册的 skill 若与本仓子 skill 同名会静默遮蔽——冒烟需查冲突面 | 冒烟清单 |

### 9.2 风险

| 风险 | 等级 | 缓解 |
|---|---|---|
| pi 机制演进破坏 adapter 假设（skills/prompts 发现规则变更） | 中 | 版本锚点（O-7）+ check-agent-adapters 契约静态守卫 |
| prompts 直接注册 commands 的展开语义偏差（$ 替换/首行 description） | 中 | §8.1-2 两点先冒烟，失败即 shims 兜底（O-3） |
| headless 无交互通道导致治理 MUST 契约（AskUserQuestion 边界）在 pi 内不可执行 | 高（能力面固有） | O-2 诚实降级声明 + 外宿主交互（opencode degraded_mode 先例） |
| 全仓 grep 默认忽略 gitignored 面（见 9.3）导致 FEAT-101 漏删/漏改 | 中 | 补面清单 + `grep -i --no-ignore` 复核命令 |

### 9.3 FEAT-101（移除 chrys）受影响面核对清单——补充遗漏检查

全仓 `grep 'chrys'`（大小写敏感、默认忽略规则）= 181 处命中，**但以下三类面会被该 grep 漏掉**（本调研定向补查实证）：

1. **大小写独占面（grep 'chrys' 漏 'Chrys'）**：
   - `verify_workflow.py` **L2384**：`MAINSTREAM_AGENT_LOADING_TIER1` 列表中的 `"Chrys"`（纯大写行）；
   - `verify_workflow.py` **L2456**：`MAINSTREAM_AGENT_LOADING_ADAPTERS["chrys"]["display"] = "Chrys"`（该行无小写字面量）；
   - 复核命令：`grep -in chrys` 全仓。
2. **gitignored 入口文件面（默认 grep 不命中）**：
   - 根 `AGENTS.md` **L1** 标题 `# Codex / Chrys 项目指引`（.gitignore「Local Codex state: AGENTS.md」；0.61.2 由 EVD-644 记录改名）——FEAT-101 需决定标题回退/更新（此文件是 dsh/多平台共享注入面，非 chrys 专属）；
   - 根 `CLAUDE.md`：定向验证 **0 命中**（无需处理）；
   - `project/e2e-test-project/AGENTS.md`：定向验证 **0 命中**。
3. **`.governance/` 运行时数据面（gitignored）**：`grep -i chrys` = **503 处**，需分三类处置：
   - **活跃记录**（plan-tracker 任务表/依赖链、evidence-log、decision-log 中 DEC-092/093/179/258 等引用 chrys 的行、risk-log RISK-049 措辞、活跃 review-record）——按治理记录策略处理（决策入账引用不追溯改写；活跃任务表随 FEAT-101 行更新）；
   - **不可变归档**（`.governance/archive/**`：DEC-092、EVD-644/645/647、archive/index.md L2875/L2885、tasks 归档）——**不动**（归档=有效证据）；
   - **backups/ 与 incidents/*.jsonl**（`.governance/backups/**`）——**绝对不动**。

其余 grep 已覆盖但**容易在 triage 中漏判性质**的面（补充定性）：

| 面 | 位置 | FEAT-101 处置定性 |
|---|---|---|
| `.chrys-plugin/` 物理目录 + plugin.json | 仓库根（内容 v0.98.0，18 行） | 删除（同步 manifest canonical L317-324、VERSION_PATHS version.py L17、version-projections.json L56-61、projection.py L43、quickscan L281/302/401、cleanup.py L61、manifest cleanup_scope L934、verify L355/L553/L689-692） |
| 契约金样 | `infra/contract_matrix/golden_samples.txt` L97/L283-295/L1358 | fixture——确认再生成机制后更新（非手改产品面） |
| 活跃文档检查面 | `docs/requirements/runtime-readiness-matrix-0.43.0.md`（check_runtime_readiness_matrix L3175-3213 强制行存在）、`docs/requirements/mainstream-agent-loading-0.47.0.md`（check-mainstream-agent-loading 消费） | **必须与代码常量同步删行**（只删代码不删文档行 = FAIL；反之亦然） |
| 历史文档 | CHANGELOG 各版本段、docs/release/release-checklist-*（0.61.2/0.63.4/0.66.2/0.76.0/0.77.0/0.78.0/0.84.0/0.95.0/0.96.0）、rollback-plan-0.61.2/0.63.4、docs/reviews/REL-*.diff、docs/verification/loop-*-0.90.0.md、docs/research/feat-095-*.md、docs/requirements/architecture-audit-facts-0.80.0.md 等 | 不可变历史——**不动**（先例：DEC-093「历史文档保留为历史，不删」） |
| 合成测试夹具（非 chrys 功能面） | `infra/tests/test_loop_unit_manifest.py`、`test_loop_structural_derivation.py`（大量 `adapters/chrys` 合成数据）、`infra/loop_migration.py` L1726/L2086/L2357（注释/docstring 示例） | 功能上可保留（自建临时目录，不依赖真实 chrys adapter）——建议 FEAT-101 显式决策「保留为合成数据」防止后续误清理；或顺手换示例名（纯注释面） |
| 功能测试夹具（真实面） | `test_verify_workflow.py` L2722（六元循环）、L2601-2618、L3347-3360、L8648-8667、L900-1016（FIX-182 zcode/chrys plugin.json 覆盖测试） | 必须改（删 chrys 分支/夹具） |
| 历史发布证据脚本 | `infra/release/verify_rel063_evidence.py` L56 | 历史脚本——保留（0.63.3 版本化证据） |
| `.governance/audit-AUDIT-136-R1.md` L49 | 治理审计记录 | 按治理记录策略（不动/随活跃面归档） |
| EVD/DEC 引用链 | evidence-log/decision-log 活跃文件中 chrys 相关 EVD-644/645/647、DEC-092 | 决策引用不追溯改写；FEAT-101 自身的 DEC/EVD 入账记录移除决策 |

### 9.4 FEAT-100 change-triage `--files` 建议清单（精确路径）

> 依据 §7 登记点 + §8 方案 A（O-1 若选方案 B 则追加 package.json 面）。以下为**建议清单**，最终以 change-triage 机录为准。

**新建**（方案 A，不含 shims 兜底）：

1. `adapters/pi/README.md`
2. `adapters/pi/adapter-manifest.json`（14 必需键 + exploration_channels 含「生成≠咨询」标记 + runtime_e2e 块）
3. `adapters/pi/launch.py`（打印 manifest；是否 `--install` 真安装待 O-1）
4. （O-3 兜底条件新建）`adapters/pi/skill-shims/`（仅当 prompts 直注册冒烟失败）

**修改**（登记点）：

5. `skills/software-project-governance/infra/verify_workflow.py`（L1609 MAINSTREAM_AGENT_ADAPTERS、L2366 RUNTIME_MATRIX_AGENT_IDS、L540-561 REQUIRED_FILES、L654-696 REQUIRED_SNIPPETS、L2369-2386 REQUIRED_DOCS+TIER1、L2394-2483 ADAPTERS dict、L5421-5470 CAPABILITY_POLICY、L12080-12087 QUOTE_SYNC；可选 L20097+L20110 E2E 面待 O-4）
6. `skills/software-project-governance/SKILL.md`（L492-500 平台表 + 可选 pi 平台说明段）
7. `README.md`（L26-34 Tier 1 表）
8. `docs/requirements/runtime-readiness-matrix-0.43.0.md`（+pi 行）
9. `docs/requirements/mainstream-agent-loading-0.47.0.md`（+Pi 行）
10. `skills/software-project-governance/infra/tests/test_verify_workflow.py`（夹具 +pi）
11. `skills/software-project-governance/infra/contract_matrix/golden_samples.txt`（再生成）
12. （方案 B 追加）`package.json`（pi manifest + pi-package keyword）
13. （仅当建 pi 专用目录/投影时——方案 A/B 均不需要）core/manifest.json、core/version-projections.json、infra/checks/version.py、infra/quickscan_registry.py、infra/cleanup.py、infra/checks/projection.py、infra/checks/triage_domain.py

**不新建**：`.pi-plugin/` 类目录——pi 无此平台约定（§7.1 结论）。

---

## 核心结论（≤15 条）

1. pi = `@earendil-works/pi-coding-agent@1.1.0`，Mario Zechner 的 MIT 开源 monorepo（github.com/earendil-works/pi），npm 全局 + `pi.ps1` shim，本机 `pi --version`=1.1.0（exit 0）。〔§1〕
2. pi **原生双兼容 AGENTS.md 与 CLAUDE.md** 上下文发现（工作目录+祖先，无需项目信任）——本仓现有双入口在 pi 下零配置自动生效。〔§2〕
3. pi **原生兼容 Agent Skills 规范**：SKILL.md 目录递归发现、name/description 进 system prompt、正文按需加载、`/skill:name` 命令——本仓 skills/ 树形态直接可被 pi 消费。〔§3.1〕
4. pi 四种全局接线机制：`pi install`（packages 数组）/ settings `skills`/`prompts` 路径数组 / `<agent-dir>` 惯例目录 drop-in / 单次 `-e|--skill` 旗标；本地路径包**不拷贝、原位加载**。〔§3.3/§5〕
5. 用户本机已用 settings 数组模式外接 developer-kit skills/prompts——方案 A 与现有用法同构。〔§5/§8.0〕
6. pi prompts（斜杠命令）= 直接 `.md` 子文件 + 首行回退 description——本仓 `commands/*.md` 可能免 shims 直注册，但有两个待冒烟点（$ 替换冲突、首行 description 可用性）。〔§3.2/§8.1〕
7. **能力面硬事实**：pi 无原生 ask-user 工具、无原生 sub_agent 机制（docs 全量 grep 零命中）；tool_calling native（8 内置工具含 Windows 原生 powershell）；MCP 机制 native 但 host-dependent；git_hooks 按本仓先例记仓库级 native。〔§4〕
8. headless：`-p/--print`、`--mode json/rpc`、`--no-session`、`--session-dir`、`--tools` 只读子集、`-a/-na` 信任一次性决策——pi 可进入本仓 agent-runtime-e2e 矩阵（dsh 因无 headless runner 被排除，pi 不是）。〔§6/§7.2〕
9. 隔离冒烟面齐全：`PI_CODING_AGENT_DIR`（整配置根）、`PI_CODING_AGENT_SESSION_DIR`/`--session-dir`、`PI_PACKAGE_DIR`、`PI_OFFLINE`——R1 三选一之 a 可落地；唯模型凭证在隔离目录缺失，完整 E2E 需混合口径（O-5）。〔§5/§8.4〕
10. 新增 pi adapter 的登记面 = verify_workflow.py 9 处常量/检查 + SKILL.md 平台表 + README Tier 1 表 + 两份活跃矩阵文档行 + 测试夹具 + 金样（全部行号已录 §7.2）——**不需要** `.pi-plugin/` 目录（无此平台约定；gemini/opencode/chrys/dsh 四先例中三个均无 dotfile 目录）。〔§7〕
11. QUOTE_SYNC 守卫要求 pi manifest 的 exploration_channels.note 携带「生成≠咨询」标记（FIX-432 六平台元组 → 七平台）。〔§7.2〕
12. FEAT-101 盲区一：大小写——`grep 'chrys'` 漏掉 verify_workflow.py L2384（TIER1 "Chrys"）与 L2456（display 名）等纯大写行；须 `grep -i`。〔§9.3-1〕
13. FEAT-101 盲区二：gitignored 面——根 `AGENTS.md` L1 标题含 Chrys（.gitignore 忽略故 grep 不命中）；根 CLAUDE.md 与 e2e AGENTS.md 已验证零命中。〔§9.3-2〕
14. FEAT-101 盲区三：`.governance/`（gitignored 运行时数据）`grep -i chrys` = 503 处——活跃记录/不可变归档/backups 三类分级处置，archive 与 backups 绝不动。〔§9.3-3〕
15. 开放决策 10 项（O-1~O-10）集中在：接线机制 A/B 二选一、能力降级知情确认（无 ask_user/sub_agent ⇒ 治理闭环在 pi 是降级模式）、commands shims 与否、E2E 入矩阵与隔离口径、FEAT-100/101 时序。〔§9.1〕

## 附：反面证据与验证计划（stage-research 退出条件对齐）

- **与「pi 可完整承载治理」假设矛盾的证据**：无 ask-user（headless 无 UI，extensions.md L250-251）、无 sub_agent（docs 零命中）——治理 MUST 契约（AskUserQuestion 边界、Agent Team、复审必达的 Reviewer spawn）在 pi 运行时内**不可原生执行**，只能诚实降级（opencode 先例）。
- **未证实项清单**（禁止当事实引用）：`ask_question` 是否存在于任何扩展（help 示例名而已）；pi-web-access 是否构成可声明 browser/discover 通道；pi-plan-mode 是否提供 ask-user 类工具；prompts 直注册 commands 的展开正确性；`package.json files` 对本地路径包的不相关性（推理）；hook find_spg_home 与 pi 无耦合（推理）。
- **验证计划**：上述未证实项全部落入 §8.4 冒烟 L1-L3 与 O-2/O-3/O-5 决策 gate——先 L0/L1（无凭证可测），L2/L3 随 O-5 口径批准后执行。
