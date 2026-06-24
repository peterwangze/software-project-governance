# Software Project Governance

> AI coding delivery trust layer for evidence-backed planning, review, risk, quality, and release control.

Software Project Governance helps AI coding agents keep delivery trustworthy while you stay focused on product and technical decisions. It is designed for marketplace reviewers, AI coding users, and teams who need a repeatable way to stop drift, missing evidence, weak review loops, and premature release claims.

## Marketplace Review Ready

Use this workflow when your AI coding setup needs:

- **Evidence-backed delivery**: every meaningful task can carry facts about what changed, why it changed, how it was verified, and what remains risky.
- **Gate and risk control**: stage gates, task status, risks, decisions, and release readiness stay connected instead of living in scattered chat memory.
- **Reviewer separation with degraded-mode honesty**: the workflow distinguishes real independent review from degraded or environment-dependent execution, and does not present every agent as fully supported.
- **5-minute orientation for new users**: start with `/governance`, initialize `.governance/`, then let the agent resume state, check gates, and surface only critical decisions.

## 1.0.0 Readiness Boundary

0.56.1 packages the 0.55.0 Dynamic Lifecycle migration preview and external validation archive, the 0.55.1 Web console CLI/client entry patch, the 0.55.2 passive Web summary entry patch, the 0.55.3 governance-entry correction, the 0.56.0 zcode plugin marketplace adapter, and the FIX-151 Web console real-data dashboard patch. It is not the 1.0.0 release. The release keeps the dry-run-only `dynamic-lifecycle-migration --target <path> --dry-run` preview, the migration guide, the `python_game` chapter-flow validation archive, and the `shitu` non-game validation archive from 0.55.0. 0.55.1 added `web-console --status` and `web-console --start [--install]`; 0.55.2 added `web-console --summary-link` for read-only task, phase, and session summaries; 0.55.3 restores the intended product entry so manual `/governance` starts or reuses the local Web console through `web-console --governance-entry`, then reports the URL for follow-up Web UI interaction; 0.56.0 adds the zcode native plugin surface (`.zcode-plugin/`, top-level `package.json`) and a one-shot `project/zcode-local-load.py` tool so the plugin can run in the local zcode installation; 0.56.1 fixes the Web console dashboard to read real governance data instead of hardcoded mock values, adds a `web/server.py` API server and `web/vite.config.js` proxy, makes all dashboard buttons functional, and keeps the dashboard a read-only local companion. `classic-phase-gate` remains the active/default compatibility preset, `dynamic-flow-gate` remains inactive/non-default and opt-in only, and no project is migrated by this release. The external validations remain intentionally conservative: both dry-run previews reached `READY_FOR_REVIEW`, but installed-state validation still has target-native blockers, and non-game preset generalization remains partial because `shitu` preview flow units still come from the `python_game_10_chapters` example. RISK-036 and RISK-037 remain open: no official approval, no marketplace approval (the zcode adapter proves local load/runtime only; it is not submitted to or approved by the zcode official marketplace), no two-real-project external validation full PASS, no Codex Desktop lifecycle PASS, no project migration, no RISK-036 closure, no RISK-037 closure, and no 1.0.0 production-ready claim.

## Mainstream Agent Loading

0.47.0 makes the current loading paths explicit for mainstream AI coding agents. This is loading readiness, not official approval, marketplace approval, universal/full runtime support, or Codex Desktop marketplace-management E2E PASS. See the 0.47.0 scope note in [docs/requirements/mainstream-agent-loading-0.47.0.md](docs/requirements/mainstream-agent-loading-0.47.0.md) and the public runtime facts in [docs/requirements/runtime-readiness-matrix-0.43.0.md](docs/requirements/runtime-readiness-matrix-0.43.0.md).

Tier 1 loading guide:

| Agent | Load or install path | First verification | Current boundary |
| --- | --- | --- | --- |
| Claude Code | Add this repo as a Claude plugin marketplace, then install `software-project-governance@spg`. | `python adapters/claude/launch.py` and `python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters --runtime` | Claude target-cwd read use case is PASS/DEGRADED in local evidence. This is not official marketplace approval. |
| Codex | Use `.agents/plugins/marketplace.json`, `.codex-plugin/plugin.json`, `AGENTS.md`, and `skills/software-project-governance/SKILL.md` as the Codex plugin/project guidance package. | `python C:\Users\peter\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py .`, `python adapters/codex/launch.py`, and `python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent codex --timeout 180` | Codex CLI headless target-cwd read E2E is PASS/DEGRADED as of 2026-06-11. This is still not Codex Desktop marketplace-management lifecycle PASS. |
| Gemini CLI | Use a thin `GEMINI.md` project context pointer to `skills/software-project-governance/SKILL.md`; custom commands, MCP, and extensions remain separate extension points. | `python adapters/gemini/launch.py`, then `GEMINI_CLI_TRUST_WORKSPACE=true python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent gemini --timeout 180` | Gemini CLI target-cwd read E2E is PASS/DEGRADED as of 2026-06-11 when headless workspace trust is enabled. No Gemini plugin marketplace claim. |
| opencode | Use `AGENTS.md` or configured opencode instructions to point at `skills/software-project-governance/SKILL.md`. | `python skills/software-project-governance/infra/verify_workflow.py opencode-provider-preflight` and `python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent opencode --timeout 90` | opencode target-cwd runtime E2E is PASS/DEGRADED in local evidence; provider/model preflight still guards future regressions. |

Tier 2 compatibility and research rows:

| Agent | Loading surface to watch | 0.47.0 status |
| --- | --- | --- |
| Cursor | Project/user/team rules and `AGENTS.md` style project instructions | Compatibility reference only; no adapter manifest or runtime PASS. |
| GitHub Copilot coding agent | Repository custom instructions and `AGENTS.md` custom instructions | Compatibility reference only; no adapter manifest or runtime PASS. |
| Cline | Markdown rules such as Cline rules files | Compatibility reference only; no adapter manifest or runtime PASS. |
| Windsurf/Cascade | Workspace rules and memories | Compatibility reference only; no adapter manifest or runtime PASS. |
| Kiro | Workspace steering files such as `.kiro/steering/` | Compatibility reference only; no adapter manifest or runtime PASS. |

Claude Code:

```bash
/plugin marketplace add peterwangze/software-project-governance
/plugin install software-project-governance@spg
```

Alternative Claude paths:

```bash
/plugin install https://github.com/peterwangze/software-project-governance.git
git clone https://github.com/peterwangze/software-project-governance.git
/plugin install /path/to/software-project-governance
```

Codex personal marketplace package:

```bash
python -m json.tool .agents/plugins/marketplace.json
python -m json.tool .codex-plugin/plugin.json
python C:\Users\peter\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py .
```

Gemini and opencode thin project projections:

```bash
python adapters/gemini/launch.py
python adapters/opencode/launch.py
```

For every agent, load `skills/software-project-governance/SKILL.md` as the workflow entry and let runtime records live in the target project's `.governance/` directory. Adapter and marketplace assets describe install and loading paths; they are not evidence of marketplace approval or universal runtime readiness.

## Trust and Data Boundary

- The workflow writes project governance state to your project-local `.governance/` directory.
- It uses local files, git hooks, validation scripts, and agent-readable skills to keep delivery facts inspectable.
- The repository's own `.governance/` directory is a dogfood/sample runtime record, not a template to copy into your project.
- Adapter and marketplace assets describe install and loading paths; they are not evidence of marketplace approval or universal runtime readiness.

## 5-Minute Start

The first success path is intentionally small: get one local trust signal before learning the full governance model.

1. Install through one of the paths above.
2. Open your project root in your AI coding environment.
3. Run `/governance`; if your environment exposes status directly, the same first signal is the status output.
4. Look for the **Delivery Trust Snapshot**: goal, stage, gate/setup status, risk, evidence, next action, preset guidance, verification signal, and no-overclaim boundary.
5. For a local demo-only check that needs no external credentials, run:

```bash
python skills/software-project-governance/infra/verify_workflow.py first-run-demo --assert-snapshot
```

The snapshot is the first trust signal: it proves the workflow can show what it knows, what remains missing, and the next evidence-backed action. It is not a claim of official approval, marketplace approval, universal/full runtime support, or 1.0.0 production-ready status.

External first-session measurement is tracked separately from this local demo. The current 0.43.0 measured state is local_demo=PASS and external_pilot=NOT_MEASURED in the [first-session measurement evidence](docs/requirements/first-session-measurement-0.43.0.md).

## Optional Local Web Console

The primary user interface remains your AI coding CLI or client: Claude Code, Codex, Gemini CLI, opencode, or another agent host. The `web/` console is an optional local companion view for users who want a cleaner status surface while still driving work from the CLI/client.

Use it for local configuration, current status, evidence/risk scanning, and advanced maintenance visibility. It does not replace `/governance`, does not auto-run agent tasks, and is not evidence of Codex Desktop marketplace-management lifecycle PASS.

Discover it from the same CLI/client path:

```bash
python skills/software-project-governance/infra/verify_workflow.py web-console --status
```

Manual `/governance` is the default user entry into the Web UI. It should start or reuse the local console and print the URL:

```bash
python skills/software-project-governance/infra/verify_workflow.py web-console --governance-entry
```

Print the no-side-effect footer that agents should append after a task, phase, or session summary:

```bash
python skills/software-project-governance/infra/verify_workflow.py web-console --summary-link
```

Start it from this repository checkout:

```bash
python skills/software-project-governance/infra/verify_workflow.py web-console --start
```

On a first checkout, include dependency installation explicitly:

```bash
python skills/software-project-governance/infra/verify_workflow.py web-console --start --install
```

Then open the local URL printed by the command, usually:

```text
http://127.0.0.1:5173/
```

In a CLI/client session, manual `/governance` starts or reuses the Web console by default so the user can keep interacting through a readable local dashboard. If dependencies are missing on first use, run the explicit install path shown by the CLI. After a task, phase, or session summary, the agent should append the read-only `web-console --summary-link` result: it reports the local URL if the console is already running, or the manual start command if it is not. Keep execution authority in the CLI/client; use the Web console for status, local configuration, and follow-up interaction.

First-run preset guidance:

| Preset | Use first when | What it optimizes for |
|--------|----------------|-----------------------|
| **lite** | You want the quickest first run or a personal/MVP project | Minimal questions and a fast snapshot |
| **standard** | You are running team delivery or a normal product project | Balanced evidence, gates, risks, and review boundaries |
| **strict** | You are in regulated, high-risk, or release-sensitive work | Stronger evidence and approval discipline |

Packs are capability modules; profiles are governance intensity presets. Profiles stay `lite` / `standard` / `strict`, and the current 0.44.0 implementation is registry-first with no physical split.

| Preset | Default packs to start with | What to add later |
|--------|-----------------------------|-------------------|
| **lite** | `governance-core` | Add `quality-gates` when AI output quality needs executable constraints |
| **standard** | `governance-core`, `quality-gates`, `release-governance`, `agent-team` | Add `enterprise` only when auditability and adapter/manifest discipline are worth the extra context |
| **strict** | `governance-core`, `quality-gates`, `release-governance`, `agent-team`, `enterprise` | Keep all packs enabled and treat any degraded runtime as a release risk |

Pack membership is not completion evidence. `pack enabled` does not mean task evidence exists, independent review passed, quality gates passed, release gates passed, official approval was granted, marketplace approval was granted, or universal/full runtime support is verified.

For full Chinese installation details and daily usage guidance, continue below.

## 中文详细说明

> 让 coding agent 帮你看护项目质量——你只负责思考，过程管理全自动。

## 一句话说明

你的 AI 编程助手（Claude / Codex / 其他）安装这个工作流后，会自动帮你做这些事：

- 每完成一个任务，**自动记录证据**（改了什么、为什么改、怎么验证的）
- 每推进一个阶段，**自动检查 Gate**（有没有遗漏、质量达标没）
- 遇到方向选择时，**帮你列出选项和后果**，你做判断
- 风险、决策、计划变更——**全程留痕，可复盘**

你不需要手动维护项目文档、不需要记住"上次做到哪了"、不需要提醒自己"该做 code review 了"。

## 可选本地 Web 控制台

当前主交互界面仍然是 CLI 或客户端：Claude Code、Codex、Gemini CLI、opencode 等。`web/` 是可选的本地伴随控制台，用来把常用本地配置、状态、证据和风险以更清晰的浏览器界面展示出来。

推荐用法：

- 日常推进任务、确认决策、执行 `/governance` 仍在 CLI/客户端里完成。
- Web 控制台用于查看 Local Setup、Status、Evidence & Risks。
- Remote Validation、Release、Maintenance 属于 Advanced 高阶区，不放在首屏干扰普通用户。
- 这不是 Codex Desktop 内嵌 UI，也不是 marketplace lifecycle PASS 证据。

从同一个 CLI/客户端入口发现：

```bash
python skills/software-project-governance/infra/verify_workflow.py web-console --status
```

用户手动执行 `/governance` 是默认进入 Web UI 的入口。它应该启动或复用本地控制台，并输出 URL：

```bash
python skills/software-project-governance/infra/verify_workflow.py web-console --governance-entry
```

阶段性任务或 session 总结之后，agent 应追加这个无副作用入口：

```bash
python skills/software-project-governance/infra/verify_workflow.py web-console --summary-link
```

从当前仓库启动：

```bash
python skills/software-project-governance/infra/verify_workflow.py web-console --start
```

首次 checkout 如未安装前端依赖，显式加 `--install`：

```bash
python skills/software-project-governance/infra/verify_workflow.py web-console --start --install
```

然后打开命令输出的本地地址，通常是：

```text
http://127.0.0.1:5173/
```

在 Codex/Claude 这类客户端里，手动执行 `/governance` 默认应启动或复用 Web 控制台，并给出本地 URL，方便后续用 Web UI 查看状态和继续交互。首次使用如果缺少依赖，按 CLI 输出的一次性 `--install` 路径安装。阶段性任务完成或 session 收尾时，agent 应该在总结之后追加 `web-console --summary-link` 的只读结果：如果 Web 控制台已经运行，就给出本地链接；如果未运行，只给出手动启动命令。CLI/客户端负责执行，Web 控制台负责状态、配置与后续交互。

## 安装

### Claude Code

```bash
# 方式一：通过插件市场安装（推荐，两步）
/plugin marketplace add peterwangze/software-project-governance
/plugin install software-project-governance@spg

# 方式二：直接从 git URL 安装
/plugin install https://github.com/peterwangze/software-project-governance.git

# 方式三：克隆到本地后安装
git clone https://github.com/peterwangze/software-project-governance.git
/plugin install /path/to/software-project-governance
```

安装后，工作流入口会在后续会话中自动可用；**但首次使用前仍必须先完成一次初始化**，在你的项目根目录创建 `.governance/` 治理文件。安装完成不等于已经可用完成。

### Codex

```bash
git clone https://github.com/peterwangze/software-project-governance.git
```

当前仓库已提供 Codex 所需资产：`.codex-plugin/plugin.json` 和 `skills/software-project-governance/SKILL.md`。

但要注意两点：
1. **Codex 的具体加载方式取决于你当前使用的 Codex 环境/插件机制**，不是所有环境都等价于 Claude Code 的 `/plugin install`
2. **首次使用前同样要先初始化项目治理文件**，否则后续状态、Gate、verify 都没有项目事实源

Codex 入口采用**自包含 skill**：`skills/software-project-governance/SKILL.md` 内嵌核心规则，详细规则从同目录 `references/` 按需读取；项目运行数据写入你当前项目根目录 `.governance/`。

如果你当前使用的 Codex 环境不能直接消费 `.codex-plugin/plugin.json`，先把它视为插件资产包，再按该环境支持的 skill/plugin 加载方式接入。当前仓库提供的是**可消费资产**，不是对所有 Codex 运行环境都统一的一键安装命令。

首次进入后，优先完成初始化，再开始日常使用。没有初始化时，不建议直接运行状态类命令。 

### Gemini CLI

Gemini 当前走最薄项目投影，不维护第二套 workflow 规则。项目入口建议使用 `GEMINI.md` 指向：

```text
skills/software-project-governance/SKILL.md
```

验证顺序：

```bash
python adapters/gemini/launch.py
python skills/software-project-governance/infra/verify_workflow.py gemini-auth-preflight
GEMINI_CLI_TRUST_WORKSPACE=true python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent gemini --timeout 180
```

当前边界：本机 Gemini CLI target-cwd read E2E 已在 2026-06-11 PASS/DEGRADED；headless 自动化需要设置 `GEMINI_CLI_TRUST_WORKSPACE=true` 或通过交互式信任当前目录。不要把 `GEMINI.md` 投影写成 Gemini plugin marketplace、official approval、marketplace approval 或 universal/full runtime support。

### opencode

opencode 当前使用 `AGENTS.md` 或平台配置的 instruction file 指向同一个 skill 入口：

```text
skills/software-project-governance/SKILL.md
```

验证顺序：

```bash
python adapters/opencode/launch.py
python skills/software-project-governance/infra/verify_workflow.py opencode-provider-preflight
python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent opencode --timeout 90
```

当前边界：本机 opencode target-cwd E2E 为 PASS/DEGRADED；provider/model preflight 仍然必须保留，避免未来把 provider 配置错误包装成 workflow failure 或 universal support。

### 兼容观察平台（Cursor、Copilot coding agent、Cline、Windsurf/Cascade、Kiro）

这些平台在 0.47.0 只作为 compatibility/research rows。它们都有自己的 rules、custom instructions、memories 或 steering surface，可作为后续薄投影候选；但当前没有 adapter manifest、没有 target-cwd E2E、没有 runtime PASS。不要把这些兼容方向理解为“现在已经存在与 Claude Code 同等级的一键安装入口”。

`SKILL.md` 不是“要求 agent 顺序扫描整个仓库根目录”的索引文件；它是**自包含入口**，只依赖：
- `skills/software-project-governance/SKILL.md`（入口，内嵌核心规则）
- `skills/software-project-governance/core/stage-gates.md`
- `skills/software-project-governance/core/lifecycle.md`
- 你项目中的 `.governance/`（活跃治理记录）

如果你的 agent 不能稳定满足上面 4 个条件，就说明当前更适合走兼容路线，而不是直接按 README 当成现成产品入口使用。

## 唯一命令

安装后，只需记住**一条命令**：

```
/governance
```

这条命令会根据当前项目状态自动决策：

| 你的项目状态 | `/governance` 自动做的事 |
|-------------|------------------------|
| 首次使用（无 `.governance/`） | 引导初始化——收集项目信息 → 创建治理文件 |
| 会话恢复（上次有未完成工作） | 恢复遗留任务 + 待确认决策 + 活跃风险 |
| 异常检测（hook 缺失等） | 自动诊断 → 一键修复 |
| 日常状态查看 | 展示完整治理面板（阶段/Gate/任务/风险） |
| 工作流版本更新 | 自动升级 bootstrap + 补全缺失结构 |

**所有场景，一条命令，零记忆负担。**

## 5 分钟开始

先拿到一个本地信任信号，再理解完整治理模型。最短 happy path 是：运行 `/governance` 或 status，看到 Delivery Trust Snapshot；再用本地 demo harness 复核这个首屏信号。

### 第一步：看到 Delivery Trust Snapshot

**首次使用时，先初始化并看到快照，再谈完整阶段、证据和发布治理。**

在 Claude Code 中直接运行：

```
/governance
```

如果你的环境能直接显示 status，status 输出里的 Delivery Trust Snapshot 也是同一个第一信号。它会用很短的字段告诉你：当前目标、阶段、Gate/setup 状态、风险、证据、下一步动作、预设建议、验证命令，以及不得过度宣称的边界。

首次运行会自动检测到项目尚未初始化，引导你完成：
1. 输入项目名称和目标
2. 确认项目阶段（新项目/已有项目）
3. 选择治理强度（lite/standard/strict）
4. 自动创建 `.governance/` 治理文件

### 第二步：跑本地 demo-only 验收

这个 demo path 不需要 external credentials，也不访问外部服务；它只验证本地 first-run snapshot 是否具备必要字段：

```bash
python skills/software-project-governance/infra/verify_workflow.py first-run-demo --assert-snapshot
```

Delivery Trust Snapshot 是第一个 trust signal：它证明工作流能把“已知事实、缺失证据、下一步动作和边界声明”摆在你面前。它不是官方批准、marketplace approval、universal/full runtime support，也不是 1.0.0 production-ready 声明。

外部 first-session measurement 与这个本地 demo 分开记录。当前 0.43.0 measured state 是 local_demo=PASS、external_pilot=NOT_MEASURED，见 [first-session measurement evidence](docs/requirements/first-session-measurement-0.43.0.md)。

首次预设建议：

| 预设 | 首次适合 | 优化目标 |
|------|----------|----------|
| **lite** | 个人项目、MVP、想最快看到首个快照 | 少提问、快启动 |
| **standard** | 团队项目、正式产品、常规交付 | 平衡证据、Gate、风险和审查边界 |
| **strict** | 高风险、合规、发布敏感项目 | 更严格的证据和审批纪律 |

Pack 是能力模块，profile 是治理强度预设。profile 仍然只有 `lite` / `standard` / `strict`；0.44.0 当前采用 registry-first、no physical split，不要求用户在首次运行时理解或选择所有模块。

| 预设 | 默认起步 pack | 后续何时增加 |
|------|---------------|--------------|
| **lite** | `governance-core` | 当 AI 产出质量需要可执行约束时，再加入 `quality-gates` |
| **standard** | `governance-core`, `quality-gates`, `release-governance`, `agent-team` | 只有在审计性、适配器和 manifest 纪律值得额外上下文成本时，再加入 `enterprise` |
| **strict** | `governance-core`, `quality-gates`, `release-governance`, `agent-team`, `enterprise` | 保持全部 pack，并把任何 degraded runtime 当作发布风险处理 |

Pack 归属不是完成证据。`pack enabled` 不等于任务证据存在、独立审查通过、质量门禁通过、发布门禁通过、官方批准、marketplace approval 或 universal/full runtime support verified。

如果你的环境暂不支持 slash command，就直接告诉 agent 以上信息，让它按 `skills/software-project-governance/SKILL.md` 的规则帮你初始化。

**仓库里已有的 `.governance/` 是本项目自己的运行样例，不是你的初始化模板。** 不要直接复制仓库根目录下已有的治理记录来当你的项目初始状态。

### 新项目

1. 告诉你的 agent："我要开始一个新项目，项目目标是 XXX"
2. 工作流自动从**立项阶段**开始，引导你明确目标、范围和关键决策
3. 每推进一个阶段，agent 会自动检查是否达到质量标准

### 已在进行的项目

1. 告诉你的 agent："我的项目目前在开发阶段，想接入治理工作流"
2. 工作流会要求你补充最少的信息（当前状态、关键决策、已知风险）
3. 之前的阶段自动标记为"已通过"，不需要补齐历史记录
4. 立即从当前阶段开始治理

### 只用某个功能

不需要加载全流程。你可以直接告诉 agent：

- "帮我做一次技术方案评审" → 加载技术评审 checklist
- "帮我做 Code Review" → 加载 Code Review 规范
- "帮我做发布 checklist" → 加载发布检查清单
- "帮我做项目复盘" → 加载回顾会议模板

## 项目规模选择

安装后第一次使用，工作流会问你的项目规模：

| 选择 | 适合 | 工作流做什么 | 你需要做什么 |
|------|------|------------|------------|
| **轻量** | 个人项目、MVP、探索 | 只跟踪核心阶段，最少记录 | 几乎不管，只在关键节点确认 |
| **标准** | 团队项目、正式产品 | 全流程 11 阶段，完整记录 | 方向决策和质量审核 |
| **严格** | 大型项目、合规系统 | 全流程 + 双重证据 + 不允许跳步 | 每个决策审核 + 审批 |

不确定选哪个？先选"标准"，随时可以调整。

## 日常体验

### 工作流自动做的事（不打扰你）

- 记录每个任务完成后的证据
- 检查 Gate 是否通过
- 跟踪风险状态变化
- 更新项目状态面板
- 在阶段转换时提醒你补齐必要记录

### 需要你做的事

- **方向决策**：多条路线时选择走哪条
- **需求澄清**：确认你到底要做什么
- **质量审核**：确认产出物是否满足要求

### 你不会被打扰的事

- 记录更新、文件编辑、状态跟踪——全自动
- Gate 通过时不会打断你
- 两个紧密关联的任务之间不会停下来请示

## 覆盖的项目阶段

```
立项 → 调研 → 技术选型 → 环境搭建 → 架构设计 → 开发 → 测试 → CI/CD → 发布 → 运营 → 维护
```

每个阶段有独立的子工作流，包含：进入条件、活动清单、产出标准、退出检查。你可以从任意阶段开始。

## 验证

**推荐方式**（在 agent 内部）：运行 `/governance`，异常时自动触发诊断修复。

**手动方式**（在终端中）：

```bash
python skills/software-project-governance/infra/verify_workflow.py              # 完整校验
python skills/software-project-governance/infra/verify_workflow.py status       # 项目状态
python skills/software-project-governance/infra/verify_workflow.py gates        # 所有 Gate
```

## 内部文档

以下文档供工作流开发者和贡献者参考，普通用户不需要阅读：

- [协议层定义](skills/software-project-governance/core/protocol/plugin-contract.md)
- [生命周期规则](skills/software-project-governance/core/lifecycle.md)
- [Gate 门禁规则](skills/software-project-governance/core/stage-gates.md)
- [Profile 配置](skills/software-project-governance/core/profiles.md)
- [中途接入协议](skills/software-project-governance/core/onboarding.md)
- [企业实践经验](project/workflows/software-project-governance/research/company-practices.md)
- [产品形态设计](project/workflows/software-project-governance/research/default-product-shape.md)
