# Software Project Governance

> Govern AI coding work in nested loops, from a local fix to independent product acceptance and authorized release.

Software Project Governance keeps each work unit tied to the user's goal and acceptance criteria. When a session resumes, the agent reads the unit, its parent, its current loop and its latest evidence. The role responsible for the next action can then repair a failed result, review the deliverable or ask the user for a decision.

## Marketplace Review Ready

Use this workflow when your AI coding setup needs:

- **Evidence-backed delivery**: every meaningful task can carry facts about what changed, why it changed, how it was verified, and what remains risky.
- **Gates within each loop.** A gate checks the evidence and authorization required for this unit's current action. A failed check returns work to the responsible unit for repair and another attempt.
- **Reviewer separation with degraded-mode honesty**: the workflow distinguishes real independent review from degraded or environment-dependent execution, and does not present every agent as fully supported.
- **Getting started.** Open `/governance` and initialize `.governance/`. On return, use `loop status --unit <id>` to see the current attempt, its evidence and the next action.

## Release and validation

For the source layout, runtime entry points and project data locations, see the [repository navigation](https://github.com/peterwangze/software-project-governance/blob/master/project/references/architecture.md#当前目录导航). The [version history](https://github.com/peterwangze/software-project-governance/blob/master/project/CHANGELOG.md) records release changes.

The v0.101.0 release plan compares the workflow with v0.100.0 on a game and a command-line application. It follows each original goal through design changes, independent acceptance and recovery. See the [release scope](https://github.com/peterwangze/software-project-governance/blob/v0.101.0/docs/release/version-plan-0.101.0.md), [release checklist](https://github.com/peterwangze/software-project-governance/blob/v0.101.0/docs/release/release-checklist-0.101.0.md) and [rollback instructions](https://github.com/peterwangze/software-project-governance/blob/v0.101.0/docs/release/rollback-plan-0.101.0.md). Published packages are available from [GitHub Releases](https://github.com/peterwangze/software-project-governance/releases).

## Mainstream Agent Loading

Use the adapter table to choose a loading path and verify it on your host. Earlier observations are recorded in the [agent loading report](https://github.com/peterwangze/software-project-governance/blob/7b9fd3720376549c53b06d4fc362f5fb0c96e40b/docs/requirements/mainstream-agent-loading-0.47.0.md) and [runtime readiness matrix](https://github.com/peterwangze/software-project-governance/blob/7b9fd3720376549c53b06d4fc362f5fb0c96e40b/docs/requirements/runtime-readiness-matrix-0.43.0.md).

Tier 1 loading guide:

| Agent | Load or install path | First verification | Current boundary |
| --- | --- | --- | --- |
| Claude Code | Add this repo as a Claude plugin marketplace, then install `software-project-governance@spg`. | `python adapters/claude/launch.py` and `python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters --runtime` | Claude target-cwd read use case is PASS/DEGRADED in local evidence. This is not official marketplace approval. |
| Codex | Use `.agents/plugins/marketplace.json`, `.codex-plugin/plugin.json`, `AGENTS.md`, and `skills/software-project-governance/SKILL.md` as the Codex plugin/project guidance package. | `python -m json.tool .agents/plugins/marketplace.json`, `python -m json.tool .codex-plugin/plugin.json`, `python adapters/codex/launch.py`, and `python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent codex --timeout 180` | Codex CLI headless target-cwd read E2E is PASS/DEGRADED as of 2026-06-11. This test did not establish Codex Desktop marketplace-management E2E PASS. |
| Gemini CLI | Use a thin `GEMINI.md` project context pointer to `skills/software-project-governance/SKILL.md`; custom commands, MCP, and extensions remain separate extension points. | `python adapters/gemini/launch.py`, then `GEMINI_CLI_TRUST_WORKSPACE=true python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent gemini --timeout 180` | Gemini CLI target-cwd read E2E is PASS/DEGRADED as of 2026-06-11 when headless workspace trust is enabled. No Gemini plugin marketplace claim. |
| opencode | Use `AGENTS.md` or configured opencode instructions to point at `skills/software-project-governance/SKILL.md`. | `python skills/software-project-governance/infra/verify_workflow.py opencode-provider-preflight` and `python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent opencode --timeout 90` | opencode target-cwd runtime E2E is PASS/DEGRADED in local evidence; provider/model preflight still guards future regressions. |
| DeepSeek Harness (dsh) | [DSH setup and upgrades](adapters/dsh/README.md#使用) | `python adapters/dsh/launch.py --check` | Governance preset, native user interaction and subagents. |
| zcode | Add this repo as a plugin marketplace and install: `/plugin marketplace add peterwangze/software-project-governance`, then `/plugin install software-project-governance@spg`. zcode reuses the Claude marketplace protocol (`.claude-plugin/marketplace.json` + `.zcode-plugin/plugin.json`). | `python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters` | Protocol-conformant marketplace install. Not zcode official curation or approval. The 0.56.0 reverse-engineered local-load tool was retired in 0.62.0 (DEC-093). |
| Pi | pi natively loads `AGENTS.md`/`CLAUDE.md` context files and implements the Agent Skills spec. Wire via three path arrays in `~/.pi/agent/settings.json` (`skills`/`prompts` -> repo `skills/`+`commands/`, optional `extensions` -> `adapters/pi/extension` for the governance bridge tools). | `python adapters/pi/launch.py` and `python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent pi --timeout 90` | Extension-bridged `ask_user_question`/`dispatch_agent` (tui/rpc interactive scope; headless fails fast with `GOV_ASK_USER_HEADLESS`); tool_calling and git_hooks native. Runtime E2E pending — capability honestly recorded as designed/degraded. |

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

To install from a local checkout:

```bash
/plugin marketplace add /path/to/software-project-governance
/plugin install software-project-governance@spg
```

Codex personal marketplace package:

```bash
python -m json.tool .agents/plugins/marketplace.json
python -m json.tool .codex-plugin/plugin.json
# optional: if your Codex environment ships a plugin validator (e.g. a
# plugin-creator skill's scripts/validate_plugin.py), run it against this
# checkout — no validator is distributed with this repo.
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
4. Look for the **Delivery Trust Snapshot**: the intended outcome, current work unit, outstanding evidence, blockers and next action.
5. For a local demo-only check that needs no external credentials, run:

```bash
python skills/software-project-governance/infra/verify_workflow.py first-run-demo --assert-snapshot
```

The snapshot is the first trust signal: it proves the workflow can show what it knows, what remains missing, and the next evidence-backed action. It is not a claim of official approval, marketplace approval, universal/full runtime support, or 1.0.0 production-ready status.

The original first-session study recorded local_demo=PASS and external_pilot=NOT_MEASURED. [First-session measurement](https://github.com/peterwangze/software-project-governance/blob/7b9fd3720376549c53b06d4fc362f5fb0c96e40b/docs/requirements/first-session-measurement-0.43.0.md).

For a real task, give the work unit the user's words with `loop start --intent` and describe the observable result with `--acceptance`. If a trial changes the approach, use `loop learn --kind decision` to keep its evidence and repeat the original acceptance check. After delivery, record feedback with `--kind opportunity`. A later session can inspect the proposal and its success criteria with `loop status --unit <id> --json`, then select it for a new work unit. [Worked invoice reconciliation example](skills/software-project-governance/core/lifecycle.md)

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
- 一次修改、一次交付或一轮运营反馈需要作决定时，核对**本轮的工件、独立回执和待验条件**
- 遇到方向选择时，**帮你列出选项和后果**，你做判断
- 风险、决策、计划变更——**全程留痕，可复盘**

你不需要手动维护项目文档、不需要记住"上次做到哪了"、不需要提醒自己"该做 code review 了"。

## 自动化能力分级声明（plugin-contract.md L114）

本工作流对「自动/看护」的承诺按 [plugin-contract.md 三级划分](skills/software-project-governance/core/protocol/plugin-contract.md)；**禁止用笼统的「自动」一词同时指向 A 级与 C 级能力**（plugin-contract.md L114 禁令——README 和对外文档必须显式说明当前各项能力处于哪一级）：

- **A 级（Agent Protocol Automation）**：行为协议自动化——agent 按协议纪律自动执行。本 README「一句话说明」「日常体验」中的自动承诺（「过程管理全自动」「自动记录证据」「自动检查 Gate」「工作流自动做的事」「记录更新、文件编辑、状态跟踪——全自动」等）与会话内 agent 动作（自动升级 bootstrap + 补全缺失结构、创建 `.governance/` 治理文件和首个工作单元、记录当前单元的活动与观察结果、按本轮验收条件检查质量等）均属本级——agent 按协议纪律自动推进并记录，**不是**系统后台触发。
- **B 级（CLI-Enforced Automation）**：CLI/脚本强制——`verify_workflow.py check-governance`、`status` 与 commit hooks 在命令/commit 时点强制（= B 级）；「唯一命令」「5 分钟开始」「验证」中的 `/governance` 自动场景检测、自动诊断修复路由属本级（命令时点、事件驱动，非持续）。
- **C 级（System Automation）**：后台系统自动触发、不依赖 agent 记忆——**未实现（roadmap）**（plugin-contract.md L102：MCP/headless runner 仅有协议样例，无可用实现）。0.76.0 起经会话 bootstrap 的 `check-governance --summary-only` 自动运行的「会话级」健康摘要不是 C 级后台 daemon。

**当前治理自动级别 = A 级 + B 级；C 级为 roadmap（未实现）**。完整分级声明与对外宣示口径见 [`skills/software-project-governance/SKILL.md`](skills/software-project-governance/SKILL.md)「自动化能力分级声明」；对外宣示不得把 C 级未实现说成已实现。README 中其余「自动」表述（如「安装后，工作流入口会在后续会话中自动可用」、适配器边界说明中的「headless 自动化」「browser 自动化」「dsh 自动注入」）为宿主/适配器加载机制或能力边界说明，与治理自动化分级无关。

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

# 或从已有本地仓库安装
/plugin marketplace add /path/to/software-project-governance
/plugin install software-project-governance@spg
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

### DeepSeek Harness (dsh)

预设安装、升级、项目接入和能力验证见 [DSH 适配器指南](adapters/dsh/README.md)。

### 其他平台的安装与维护

| Agent | 安装 | 升级 | 降级 | 卸载 |
|-------|------|------|------|------|
| Claude Code | `/plugin marketplace add` + `/plugin install software-project-governance@spg` | `/plugin marketplace update` 后更新插件 | 从所需 tag 的本地检出目录添加市场，按插件名重装 | 宿主 `/plugin` 命令面卸载（以 `/plugin` 帮助为准） |
| zcode | 同 Claude 协议（`/plugin marketplace add` + `/plugin install`） | 同上 | 同上 | 同上 |
| Codex / Gemini CLI / opencode | 无官方包管理器——克隆仓库 + 平台投影指针（`AGENTS.md` / `GEMINI.md` 等） | `git pull`（指针不变） | `git checkout v<tag>` | 删除投影指针（可选删除克隆目录） |

### zcode

zcode 新版运行时复用了 Claude 插件市场协议，支持通过 `marketplace add` + `plugin install` 两步安装：

```bash
/plugin marketplace add peterwangze/software-project-governance
/plugin install software-project-governance@spg
```

zcode 读取 `.claude-plugin/marketplace.json`（市场清单）和 `.zcode-plugin/plugin.json`（插件元数据）。**0.62.0 起**，0.56.0 的逆向 seed-hash 本地植入工具 `project/zcode-local-load.py` 已废弃移除（DEC-093）——新版 zcode 原生支持市场安装，不再需要逆向耦合。

当前边界：这是协议一致性安装，不是 zcode 官方收录或审核批准。RISK-036（官方收录准备）继续打开。

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
| 日常状态查看 | 显示工作单元、父子关系、待验条件、阻塞和下一动作 |
| 工作流版本更新 | 自动升级 bootstrap + 补全缺失结构 |

**所有场景，一条命令，零记忆负担。**

## 5 分钟开始

先拿到一个本地信任信号，再理解完整治理模型。最短 happy path 是：运行 `/governance` 或 status，看到 Delivery Trust Snapshot；再用本地 demo harness 复核这个首屏信号。

### 第一步：看到 Delivery Trust Snapshot

**首次使用时，确认目标和验收操作，再创建首个工作单元。**

在 Claude Code 中直接运行：

```
/governance
```

如果你的环境能直接显示 status，status 输出里的 Delivery Trust Snapshot 也是同一个第一信号。它会用很短的字段告诉你：用户目标、当前单元、待验条件、阻塞、证据、下一步动作、预设建议、验证命令，以及不得过度宣称的边界。

首次运行会自动检测到项目尚未初始化，引导你完成：
1. 输入项目名称和目标
2. 确认成品验收条件和本轮工作的范围
3. 选择治理强度（lite/standard/strict）
4. 创建 `.governance/` 治理文件和首个工作单元

### 第二步：跑本地 demo-only 验收

这个 demo path 不需要 external credentials，也不访问外部服务；它只验证本地 first-run snapshot 是否具备必要字段：

```bash
python skills/software-project-governance/infra/verify_workflow.py first-run-demo --assert-snapshot
```

Delivery Trust Snapshot 是第一个 trust signal：它证明工作流能把“已知事实、缺失证据、下一步动作和边界声明”摆在你面前。它不是官方批准、marketplace approval、universal/full runtime support，也不是 1.0.0 production-ready 声明。

首次会话试验记录了 local_demo=PASS、external_pilot=NOT_MEASURED。[查阅原始测量记录](https://github.com/peterwangze/software-project-governance/blob/7b9fd3720376549c53b06d4fc362f5fb0c96e40b/docs/requirements/first-session-measurement-0.43.0.md)。

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

### 开始一个交付目标

在项目根运行 `/governance`，告诉助手成品要交给谁、用户会如何操作、怎样判断成功。例如，“让成员导出本月账单，金额须与账本一致”。助手用立项时的 G1 核实投入依据，再按实际需要开设准备、内层、交付或反馈单元。已经有原型的团队可登记本次要验收的改动。

在会话结束前或换宿主后，用 `loop status --unit <id>` 查看同一单元。金额对账失败时，测试者交回差异样本；开发者修复后，独立复验消除该笔差异。上级交付保留未解条件。

### 只用某个功能

不需要加载全流程。你可以直接告诉 agent：

- "帮我做一次技术方案评审" → 加载技术评审 checklist
- "帮我做 Code Review" → 加载 Code Review 规范
- "帮我做发布 checklist" → 加载发布检查清单
- "帮我做项目复盘" → 加载回顾会议模板

## 治理强度与日常使用

轻量档按本次风险记录必要证据，标准档覆盖团队所需的分工和复验，严格档增加独立取证与审批。各档使用相同的目标、工作单元和适用门禁。

| 工作发生在哪里 | 需要决定的事 |
| --- | --- |
| 立项及准备 | G1 核实投入依据。准备循环的 G2、G3、G4 看护调研、试用选型和运行环境。 |
| 一次修改 | 内层 G6、G7 核实修改和测试的实际效果，失败样本交回原单元修复。 |
| 一次交付 | 中层 G5 看护设计，G9 凭独立成品回执看护交付。显式发布还需 G8 发布保护及当次授权。 |
| 使用后反馈 | 外层 G10、G11 核对真实使用效果，决定下一轮目标。 |

助手可自行补证、复验和更新记录。范围变化、风险接受或发布授权由有权人裁决。

## 验证

**推荐方式**（在 agent 内部）：运行 `/governance`，异常时自动触发诊断修复。

**手动方式**（在终端中）：

```bash
python skills/software-project-governance/infra/verify_workflow.py              # 完整校验
python skills/software-project-governance/infra/verify_workflow.py status       # 项目状态
python skills/software-project-governance/infra/verify_workflow.py gates        # 所有 Gate
```

CI 使用 Python 3.11。维护者运行全量单测时，先执行 CI 中的 `Install test dependencies`，再运行 `python -m unittest discover -s skills/software-project-governance/infra/tests`。[CI 配置](.github/workflows/ci.yml)

## 内部文档

以下文档供工作流开发者和贡献者参考，普通用户不需要阅读：

- [当前代码与文档导航](https://github.com/peterwangze/software-project-governance/blob/master/project/references/architecture.md#当前目录导航)
- [版本变更记录](https://github.com/peterwangze/software-project-governance/blob/master/project/CHANGELOG.md)
- [从项目治理记录提炼的演进方向](docs/governance/evolution.md)
- [协议层定义](skills/software-project-governance/core/protocol/plugin-contract.md)
- [生命周期规则](skills/software-project-governance/core/lifecycle.md)
- [Gate 门禁规则](skills/software-project-governance/core/stage-gates.md)
- [Profile 配置](skills/software-project-governance/core/profiles.md)
- [中途接入协议](skills/software-project-governance/core/onboarding.md)
- [企业实践摘要](skills/software-project-governance/references/company-practices-summary.md)
- [产品形态设计原始记录](https://github.com/peterwangze/software-project-governance/blob/7b9fd3720376549c53b06d4fc362f5fb0c96e40b/project/workflows/software-project-governance/research/default-product-shape.md)
