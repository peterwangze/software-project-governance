# FEAT-100 设计文档 — pi 平台 Adapter：extension 桥接架构 + 三件套落位方案（0.99.0）

- **Task ID**: FEAT-100（P1，架构设计——不改产品代码）
- **日期**: 2026-10-14 · **设计基线**: 工作流 0.98.0 · **交付目标版本**: 0.99.0（对齐调研报告 O-8：+pi 属 minor）
- **设计者**: Architect Agent（角色定义 `agents/architect.md`；执行规范 `skills/stage-architecture/SKILL.md`）
- **必读输入**: `docs/research/pi-adapter-integration-research-0.98.0.md`（下称〔调研§N〕）
- **证据约定**: `<pi-pkg>` = `C:\Users\peter\AppData\Roaming\npm\node_modules\@earendil-works\pi-coding-agent`（v1.1.0）；`<repo>` = 本仓。文件证据标注路径+行号/符号名；未实测结论显式标注「未实测」；推理标注「推理」。本文档为设计产物，**不构成任何已执行操作的记录**。
- **用户三项裁决（设计约束， MUST 遵守）**:
  1. 接线机制 = **settings 路径数组**（`~/.pi/agent/settings.json` 的 `skills`/`prompts` 数组指向本仓绝对路径；其他用户代价/耦合/影响最小为第一原则；零包改动、不动版本投影面）；
  2. 能力面 = **pi extension（插件）桥接 ask_user 与 subagent 优先**，保持治理当前规则（AskUserQuestion 交互边界 + Agent Team 角色派发）；只有明确证伪不可能时才降级声明，且证伪必须机录证据；
  3. E2E = 入 agent-runtime-e2e 矩阵，本地混合口径（真实 agent-dir 只读凭证 + `--no-session`，写面 = 0）。

---

## 0. 摘要与裁定结论

| 能力桥 | 裁定 | 一句话结论 | 核心证据 |
|---|---|---|---|
| a. ask_user 桥 | **FEASIBLE** | extension 注册 model-only 工具 `ask_user_question`（schema 逐字段对齐本仓交互契约），经 `ctx.ui.select/confirm/input` dialog 方法渲染（tui + rpc 双模式可达，rpc 走 extension UI 子协议转发）；headless（json/print）返回结构化错误（isError）让模型终止并告知用户改用交互模式——与官方 question/questionnaire 示例的 fallback 先例一致 | `<pi-pkg>\docs\extensions.md` L15/L73-87/L157/L244-253；`dist\core\extensions\types.d.ts` L40-45/L72-79/L212-219/L448-506/L1204-1205；`docs\rpc-extension-ui.md` L7-10/L25/L31-46/L172-194；`examples\extensions\question.ts` L53-62、`questionnaire.ts` L93-95 |
| b. subagent 桥 | **FEASIBLE** | extension 注册 model-only 工具 `dispatch_agent`（输入=角色定义路径+任务规范+任务 prompt，语义对齐 `references/agent-dispatch-template.md`），实现走**官方 subagent 示例同款路径**：spawn 嵌套 `pi --mode json -p --no-session --append-system-prompt <角色定义> --tools <子集>` 子进程并解析 JSONL 事件流——完整工具循环、并发上限、abort 语义全部有官方参考实现；SDK 进程内嵌套（`createAgentSession` + `systemPromptOverride` + `SessionManager.inMemory()`）为备选路径，证据同样成立 | `examples\extensions\subagent\index.ts` 全文（L300/L303-307/L334-338/L344-421/L442-469/L538）；`docs\cli.md` L229-232；`docs\sdk.md` L8-18/L42-50/L96-108；`dist\core\sdk.d.ts` L10-65；`examples\sdk\03-custom-prompt.ts` L18-31；`dist\core\extensions\virtual-modules.js` L13-37 |

两项桥接均**未被证伪**——不存在触发降级声明的条件；降级文案不启用（预稿存档于 §1.4 仅作未来维护兜底）。能力入册口径：manifest `runtime_capabilities.*.status` 必须取 `{"native","degraded","unsupported"}` 枚举（`verify_workflow.py` L5419 `RUNTIME_CAPABILITY_STATUSES` 机检），「extension-bridged」语义写入 `evidence` 字段；初版登记 `degraded`（桥接已设计、待 runtime E2E 验证后按证据升级，对齐 claude adapter 先例：原生工具存在但验证面受限时记 degraded，L5422-5429）。

---

## 1. extension 桥接可行性裁定（核心）

### 1a. ask_user 桥 — FEASIBLE

#### 1a.1 机制链（每步有证据锚点）

1. **工具注册**：extension 默认工厂函数接收 `ExtensionAPI`（extensions.md L15；types.d.ts L1162 `export interface ExtensionAPI`），`pi.registerTool(tool: ToolDefinition)` 注册 LLM 可调用工具（extensions.md L76；types.d.ts L1204-1205）。`ToolDefinition` 要求 `name/label/description/parameters(TypeBox TSchema)/execute`（types.d.ts L448-506）。
2. **exposure = model-only**：`exposure: "model-only"` = 「declared to the model while active, never callable. Use it for tools that orchestrate other tools **or ask the user**」（extensions.md L157；types.d.ts L157→L395 `ToolExposure` 联合类型）。注册即激活（types.d.ts L481-484：direct/model-only 默认 `defaultActive: true`）。
3. **UI 通道**：`ctx.ui`（`ExtensionUIContext`，types.d.ts L72-196）提供 dialog 方法族：
   - `select(title: string, options: string[], opts?: ExtensionUIDialogOptions): Promise<string | undefined>`（L74）；
   - `confirm(title, message, opts?): Promise<boolean>`（L76）；
   - `input(title, placeholder?, opts?): Promise<string | undefined>`（L78）；
   - `ExtensionUIDialogOptions = { signal?: AbortSignal; timeout?: number }`（L40-45）——超时自动消解带倒计时。
4. **模式语义**：`ExtensionMode = "tui" | "rpc" | "json" | "print"`（types.d.ts L212）；`hasUI: boolean`——「Whether dialog-capable UI is available (**true in TUI and RPC modes**)」（types.d.ts L219）；extensions.md L248-251：「Extensions load in interactive, RPC, JSON, and print modes. Interactive mode provides the complete terminal UI. **RPC can forward supported dialogs and notifications through the RPC Extension UI protocol** … **JSON and print modes have no UI**. Guard terminal-only behavior with `ctx.mode === "tui"` and use `ctx.hasUI` for interactions supported by interactive and RPC clients.」RPC 模式 `ctx.hasUI === true` 佐证：rpc-extension-ui.md L25。
5. **RPC 转发协议**：dialog 方法在 RPC 模式发出 `extension_ui_request`（stdout）并阻塞等待客户端回传 `extension_ui_response`（stdin，匹配 id）；带 `timeout` 的 dialog 超时自动以默认值消解（rpc-extension-ui.md L7-10/L31-46）；响应三形态 value/confirmed/cancelled（L172-194）；取消时 extension 收到 `undefined`（select/input）或 `false`（confirm）（L188-194）。

#### 1a.2 本仓契约 → pi dialog 的语义映射

本仓 AskUserQuestion 契约（调度与交互模板）：`questions[]`，每题 `{ id, question, header?, options: [{label, description}], multi_select? }`，返回按题 id 回显选择。pi 原生 dialog 为单选字符串列表/确认/文本输入，无 per-option description 与 multi_select——映射设计（**逐题循环渲染**）：

| 契约字段 | pi 映射 | 说明 |
|---|---|---|
| `header` | 拼入 `select` 的 title：`"[{header}] {question}"` | pi select 无独立 header 概念（types.d.ts L74 仅 title+options） |
| `options[].label` | `options: string[]` 元素，格式 `"{i+1}. {label}"` | 返回值为所选字符串，按序号解析回 index |
| `options[].description` | 追加为独立提示行：选前 `ctx.ui.notify(question, "info")` 不适合；**采用拼接法**——每个选项渲染 `"{label} — {description}"`（截断至 ~80 字符防列表溢出），返回后按 `"{i+1}. "` 前缀解析 label，description 不参与回传 | select 签名只收 string[]（types.d.ts L74），无结构化选项；拼接是唯一无损通道〔推理——基于 L74 签名的事实约束〕 |
| `multi_select: true` | **降级为逐选项 confirm 序列**：对每个 option 调 `confirm(title, "{label} — {description}")`，聚合 true 集 | select 单选（返回单个 string）；逐项 confirm 在 tui/rpc 均可达（dialog 方法族），避免 tui-only 的 `custom()` 分叉（rpc-extension-ui.md L14-16：custom() 在 RPC 返回 undefined）。治理场景 multi_select 低频（推荐卡多为单选确认），语义损失可接受且诚实 |
| `options` 缺省（自由文本题） | `input(title, placeholder?)` | types.d.ts L78 |
| 整体取消 | 任一题 dialog 返回 `undefined`（select/input 被取消，rpc-extension-ui.md L190-194）或用户在 confirm 序列全否 → 返回 `cancelled: true` 结构化结果 | 对齐本仓「AskUserQuestion 被跳过=流程违规」语义：取消作为显式结果回传模型，由模型按治理规则重问或升级 |

#### 1a.3 headless（`-p` / `--mode json`）行为设计 — 结论：返回结构化错误

**结论：headless 无 UI 时，工具返回 `isError: true` 的结构化错误，指示模型终止交互尝试并向用户报告需改用交互模式（tui）或 RPC 客户端。不走 RPC 转发。**

依据（三选一裁决链）：

1. **官方先例**：`examples\extensions\question.ts` L53-62 与 `questionnaire.ts` L93-95 对非 tui 模式一律 `return { content: [{ type: "text", text: "Error: UI not available (running in non-interactive mode)" }], ... }`——官方 ask-user 类工具的 fallback 正是「返回明确错误」。
2. **协议不可能**：extension UI 子协议仅在 RPC 模式存在（rpc-extension-ui.md L3：「In RPC mode, supported calls become a request/response subprotocol」）；print 模式 stdout 保留给最终输出、json 模式 stdout 为 JSONL 事件流，两者均无 stdin 回传交互的协议面（extensions.md L250-251「JSON and print modes have no UI」）——「走 RPC 转发」在 json/print 模式无载体，证伪于协议定义。
3. **行为契约**：extensions.md L253「Keep tool and event behavior independent from rendering so non-interactive modes remain functional」——工具层返回错误结果（而非抛异常）保持非交互模式功能性；治理 fail-closed 语义（不静默降级）与错误返回一致。

守卫实现：`execute()` 入口检查 `ctx.hasUI`（types.d.ts L219）——`false`（json/print）直接返回错误；`true`（tui/rpc）走 dialog。错误文本含固定标记 `GOV_ASK_USER_HEADLESS` 供 E2E 断言（见 §6）。

#### 1a.4 工具 schema、TypeScript 骨架、错误语义、日志面

**工具 schema（TypeBox，对齐本仓 ask_user_question 契约）**：

```typescript
// TypeBox schema —— "typebox" 由 pi 运行时虚拟化提供（virtual-modules.js L14-19）
import { Type } from "typebox";

const GovAskOption = Type.Object({
  label: Type.String({ description: "Short user-facing option label" }),
  description: Type.Optional(Type.String({
    description: "One sentence explaining the tradeoff or impact" })),
});
const GovAskQuestion = Type.Object({
  id: Type.String({ description: "Stable id for this question; echoed in the answer" }),
  question: Type.String({ description: "The specific question to ask the user" }),
  header: Type.Optional(Type.String({
    description: "Optional short heading, e.g. 'Confirm' or 'Choose Mode'" })),
  options: Type.Optional(Type.Array(GovAskOption, {
    description: "Choices to show. Omit for free-text input" })),
  multi_select: Type.Optional(Type.Boolean({
    description: "Whether more than one option may be selected. Defaults to false" })),
});
const GovAskUserParams = Type.Object({
  questions: Type.Array(GovAskQuestion, {
    description: "Questions to ask before continuing" }),
});
```

**TypeScript 骨架（签名级）**：

```typescript
import type { ExtensionAPI, ExtensionToolContext, ToolDefinition } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

export function governanceAskUserTool(): ToolDefinition<typeof GovAskUserParams extends infer T ? T : never> {
  return {
    name: "ask_user_question",
    label: "Ask User (governance)",
    description: "Ask the user one or more structured questions when a decision, "
      + "confirmation, or missing information blocks governance-safe progress. "
      + "Each question carries a stable id; answers are echoed per id. "
      + "Reaches the user in interactive and RPC modes; in headless print/json "
      + "modes it fails fast with a headless-mode error.",
    parameters: GovAskUserParams,
    exposure: "model-only",           // extensions.md L157：为 ask-the-user 类工具设计
    namespace: { name: "governance", description: "software-project-governance bridge tools" },
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
    executionMode: "sequential",      // 交互工具必须串行（question.ts L50 同款）
    async execute(toolCallId, params, signal, _onUpdate, ctx) {
      if (!ctx.hasUI) return headlessErrorResult(params);        // §1a.3
      const answers: Array<{ id: string; selected: string[]; custom?: string }> = [];
      for (const q of params.questions) {
        signal?.throwIfAborted();
        answers.push(await askOne(q, ctx, signal));              // §1a.2 映射
      }
      return { content: [{ type: "text", text: renderAnswers(answers) }], details: { answers } };
    },
  };
}
// askOne(q, ctx, signal): Promise<Answer> —— 三分支：
//   options && !multi_select → ctx.ui.select(title(q), renderOptions(q), { signal, timeout })
//   options &&  multi_select → for-of ctx.ui.confirm(title(q), opt) 聚合
//   !options                → ctx.ui.input(title(q), placeholder, { signal })
// 任一返回 undefined/false-取消 → 整体 cancelled 结果（§1a.2 取消行）
```

**错误语义**（全部以工具结果而非异常返回——extensions.md L138-139「Throw from execute() to produce a failed tool result」用于意外错误；预期内失败用 `isError: true` 承载数据，L146）：

| 场景 | 返回 | 标记 |
|---|---|---|
| headless（json/print）调用 | `isError: true`，文本含 `GOV_ASK_USER_HEADLESS` + 「re-run in interactive mode (pi without -p/--mode json) or connect an RPC client」 | §1a.3 |
| 用户取消全部 | 非 error，`details.answers` 空 + 文本 `User cancelled all questions`（对齐 question.ts L223-228 先例） | — |
| dialog 超时（`timeout` 生效，rpc-extension-ui.md L10/L33） | `undefined` → 按取消处理，文本注明 `timeout` | — |
| schema 校验失败（options 空数组等） | `isError: true`，指明违规字段（question.ts L64-69 先例） | — |

**日志面**：无独立文件日志（零依赖原则）；可观测性经三个既有通道：① `details` 字段持久化到 tool result（extensions.md L135-136 契约：`details` 用于 rendering/state reconstruction）——E2E 与 HTML export 可见；② `tool_execution_start/end` 事件自带 durationMs（types.d.ts L848-858），治理 hook 类 extension 可订阅；③ RPC 模式的 `extension_ui_request` 本身就是结构化交互日志（rpc-extension-ui.md L27-46）。

#### 1a.5 证伪证据清单（不触发——留档机录模板）

若未来 pi 版本移除 dialog 方法或 model-only exposure，按下列清单机录后启用降级：`types.d.ts` L72-79 select/confirm/input 签名缺失；extensions.md L157 model-only 语义缺失；rpc-extension-ui.md 协议文档缺失；运行时探测（`pi -e <probe> -p` 加载最小 extension 调 `ctx.ui.select` 于 print 模式期得非错误挂起）——四项同时成立才构成 FALSIFIED。降级声明文案（对齐 `adapters/opencode/adapter-manifest.json` L36-40 先例）：

> `"ask_user_question": { "status": "unsupported", "evidence": "<机录证据路径与行号>", "degraded_mode": "Use the outer host conversation for interaction boundaries and record degraded evidence." }`

### 1b. subagent 桥 — FEASIBLE

#### 1b.1 机制链与路径选择（两候选 ADR）

pi 无原生子代理工具（〔调研§4〕docs 全量 grep 零命中），但 extension 内嵌套完整 agent 有**两条已被上游证据支撑的路径**：

**候选 A（推荐 v1）— spawn 嵌套 `pi` 子进程（官方 subagent 示例同款）**

官方示例 `examples\extensions\subagent\index.ts`（1038 行完整参考实现）证明全部所需语义：

| 需求 | 官方实现锚点 |
|---|---|
| 注册 model 工具 | L472 `pi.registerTool({ name: "subagent", ... })` |
| 嵌套 agent = 完整工具循环（非单次模型调用） | L300 `["--mode", "json", "-p", "--no-session"]`——嵌套 pi 进程自带 read/bash/edit/... 工具集，JSON 事件流回传 `message_end`/`tool_result_end`（L362-387） |
| 自定义 system prompt（角色定义注入） | L334-338：角色 systemPrompt 写临时文件 → `--append-system-prompt <path>`；CLI 侧 `--system-prompt <text\|path>` 整体替换可用（cli.md L229-232） |
| 嵌套工具子集 | L307 `--tools <comma list>`（tools.d.ts/sdk 亦证明 allowlist 语义） |
| 模型/thinking 继承 | L302-306 `--model`（默认继承 `ctx.model.provider/id`）+ `--thinking` |
| 并发 | L33-34 `MAX_PARALLEL_TASKS=8 / MAX_CONCURRENCY=4` + L219-237 `mapWithConcurrencyLimit` |
| 超时/中止 | L410-420 signal → SIGTERM → 5s 后 SIGKILL |
| 结果返回 | `getLastAssistantText` 语义（倒序找最后 assistant 文本，L170-180）+ usage 聚合（L367-376） |
| 运行时 import 包内值 | L22-28 `import { CONFIG_DIR_NAME, getAgentDir, ... } from "@earendil-works/pi-coding-agent"`——经 `virtual-modules.js` L29 解析 |
| 项目信任门 | L520-548 `ctx.ui.confirm("Run project-local agents?")` |

**候选 B（备选，记档不实现）— SDK 进程内嵌套会话**：`createAgentSession({ resourceLoader: new DefaultResourceLoader({ systemPromptOverride: () => <角色定义>, appendSystemPromptOverride: () => [] }), sessionManager: SessionManager.inMemory(), tools: [...], cwd })` → `await session.prompt(task)` → `session.getLastAssistantText()` → `session.dispose()`（sdk.md L8-18/L42-50/L96-108；examples\sdk\03-custom-prompt.ts L18-31；sdk.d.ts L10-65；agent-session.d.ts L534/L904/L635/L386）。

**ADR-2（subagent 桥实现路径）**：
- **上下文**：两路径均可达成「角色定义 + 任务 + 工具循环」语义。
- **决策**：v1 采用候选 A。
- **排除候选 B 理由**：① 进程内 `createAgentSession` 会构建第二个 extension runtime（`CreateAgentSessionResult.extensionsResult`，sdk.d.ts L67-74），父会话已加载的治理 extension 会被二次加载，`ask_user_question`/`dispatch_agent` 在嵌套会话内重复注册且行为不可预期（嵌套无 UI 时 ask_user 恒错）——需要自定义 ResourceLoader 白名单化，复杂度与维护面显著高于 spawn；② 隔离性：子进程上下文窗口隔离是官方示例声明的设计动机（subagent/index.ts L4-5「giving it an isolated context window」），治理 Reviewer/Developer 角色隔离语义与之同构；③ 官方示例承担上游维护成本，候选 B 组合面（loader 覆写 + inMemory + tools）无官方 extension 内嵌套先例。
- **后果**：每任务一个子进程（启动开销 ~pi 冷启动）；`getPiInvocation()`（subagent/index.ts L249-263）已处理 `process.argv[1]`/bun 虚拟路径/PATH 回退，Windows `pi.ps1` shim 场景经 PATH 分支覆盖〔推理：L262 `return { command: "pi", args }` 依赖 PATH，本机 `pi.ps1` 在 npm 全局 bin，已验证 `pi --version` exit 0（〔调研§1〕）——spawn `shell: false` 下 Windows 需要 `pi.cmd`/`pi.ps1` 解析，**标注未实测**，实施时验证，必要时按官方 `getPiInvocation` 同款逻辑优先 `process.execPath + cli.js` 绝对路径〕。
- **可逆性**：可逆（实现切换不影响 manifest 声明与工具 schema）。

#### 1b.2 dispatch_agent 工具设计（对齐调度模板语义）

`references/agent-dispatch-template.md` 的调度语义：**输入 = 角色定义路径（`{role_definition_path}`，如 `agents/developer.md`）+ 任务规范路径（`{task_skill_path}`）+ 任务 prompt（模板填充：task_id/description/file_list/acceptance/hard_gates/redlines）**；输出 = 结构化结论回 Coordinator。工具 schema：

```typescript
const GovDispatchParams = Type.Object({
  role_definition_path: Type.String({
    description: "Path to the role definition markdown, e.g. agents/developer.md. "
      + "Relative paths resolve against the governance plugin root or cwd" }),
  task_skill_path: Type.Optional(Type.String({
    description: "Path to the task SKILL spec, e.g. skills/stage-development/SKILL.md" })),
  task_prompt: Type.String({
    description: "Fully-filled dispatch prompt following "
      + "references/agent-dispatch-template.md (task id, description, file list, "
      + "acceptance criteria, hard gates, destructive redlines)" }),
  working_dir: Type.Optional(Type.String({
    description: "Working directory for the nested agent. Defaults to the current cwd" })),
  allowed_tools: Type.Optional(Type.Array(Type.String(), {
    description: "Tool allowlist for the nested agent, e.g. ['read','grep','find','ls'] "
      + "for read-only roles (Reviewer). Defaults to pi default tools" })),
  system_prompt_mode: Type.Optional(Type.StringEnum(["append", "replace"]), {
    description: "'append' (default, official subagent precedent) appends the role "
      + "definition after pi's default prompt; 'replace' swaps it entirely. "
      + "Use 'replace' only when default tool guidance must not leak" }),
});
```

**TypeScript 骨架（签名级）**：

```typescript
import type { ExtensionAPI, ExtensionToolContext, ToolDefinition } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

export function governanceDispatchAgentTool(pluginRoot: string): ToolDefinition<any, any> {
  return {
    name: "dispatch_agent",
    label: "Dispatch Agent (governance)",
    description: "Dispatch a governance role agent (Developer/Reviewer/Analyst/...) as a "
      + "nested pi process with an isolated context window. Provide the role definition "
      + "path, optional task SKILL path, and the fully-filled dispatch prompt per "
      + "references/agent-dispatch-template.md. Returns the agent's final structured "
      + "report text. Read-only roles should pass allowed_tools=['read','grep','find','ls'].",
    parameters: GovDispatchParams,
    exposure: "model-only",           // 编排类工具（extensions.md L157）
    namespace: { name: "governance", description: "software-project-governance bridge tools" },
    annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: false },
    async execute(_id, params, signal, onUpdate, ctx) {
      // 1. resolve role/skill paths against pluginRoot（读文件 → roleText, skillText）
      // 2. compose systemPromptText = roleText + "\n\n# 任务规范\n" + skillText（skill 可选）
      // 3. writePromptToTempFile(roleText∪skillText)（subagent/index.ts L239-247 同款，tmpdir + 0600）
      // 4. args = ["--mode","json","-p","--no-session"]
      //    + (system_prompt_mode==="replace" ? ["--system-prompt", tmp] : ["--append-system-prompt", tmp])
      //    + (model 继承 ctx.model) + (allowed_tools → ["--tools", join(",")])
      //    + ["Task:\n" + params.task_prompt]
      // 5. spawn + JSONL 行解析（message_end/tool_result_end 聚合，官方 L344-421 模式）
      //    + signal→SIGTERM/SIGKILL + onUpdate 流式回传（L324-331 模式）
      // 6. return { content:[{type:"text",text: finalOutput}], details:{ usage, turns, exitCode, model } }
      //    嵌套 usage 计入结果（extensions.md L136「include their usage in the result」）
    },
  };
}
```

**并发/超时/结果返回**：单任务单进程（v1 不引入 parallel/chain 模式——治理调度模板是单角色单任务派发；官方示例的 parallel/chain 留作未来扩展点，避免过度工程化）；超时经 `execute` 的 `signal`（用户 Esc/abort 传导）+ 工具层可选 `timeout_ms`（v1 不加，abort 语义已覆盖）；结果 = 最终 assistant 文本 + `details.usage`（官方 L367-376 聚合模式）。**临时文件红线对齐**：prompt 临时文件写系统 tmpdir（`os.tmpdir()`，官方 L240 同款），不写 `~/.pi/`、不写仓库；finally 块清理（官方 L426-439 同款）。

**错误语义**：角色路径不存在 → `isError: true` + 可用角色列表（官方 L284-298 模式：`Unknown agent ... Available agents`）；子进程 exit≠0 / stopReason=error|aborted → `isError: true` + stderr/最后输出（官方 L182-191 `isFailedResult` 判定）；模型凭证缺失 → 子进程 JSON 流的 errorMessage 透传（官方 L379）。

#### 1b.3 证伪证据清单（不触发——留档机录模板）

FALSIFIED 仅当：① `--mode json`/`-p`/`--no-session`/`--append-system-prompt` 任一旗标从 cli.md/`pi --help` 消失；② VIRTUAL_MODULES 移除 pi-coding-agent 键（virtual-modules.js L29）且 spawn 通道同时不可用；③ 官方 subagent 示例被移除且无等价文档。降级文案（opencode 先例 L41-45）：

> `"sub_agent": { "status": "unsupported", "evidence": "<机录证据路径与行号>", "degraded_mode": "Do not claim Producer-Reviewer separation from pi runtime alone; require external reviewer evidence." }`

### 1c. 裁定汇总表（FEASIBLE/FALSIFIED + 锚点索引）

| # | 能力 | 裁定 | 关键锚点（文件+行号/符号） | 未证实残留 |
|---|---|---|---|---|
| a1 | model-only 工具注册 | FEASIBLE | extensions.md L157；types.d.ts L395/L448-506/L1204-1205 | 无 |
| a2 | dialog UI 渲染（tui） | FEASIBLE | types.d.ts L72-79；extensions.md L244/L249 | 无 |
| a3 | dialog RPC 转发 | FEASIBLE | rpc-extension-ui.md L7-10/L25/L31-46/L172-194；extensions.md L250 | 无 |
| a4 | headless 错误返回 | FEASIBLE（设计决策） | question.ts L53-62；questionnaire.ts L93-95；extensions.md L250-251/L253 | 无 |
| a5 | multi_select 原生多选 | **不可用→降级映射**（非证伪：单选 confirm 序列承载） | types.d.ts L74（select 单值返回） | 交互体验损失已声明 |
| b1 | 嵌套完整 agent（工具循环） | FEASIBLE | subagent/index.ts L300/L362-387；cli.md L229-232 | Windows spawn 解析（1b.1 标注） |
| b2 | 角色定义注入 system prompt | FEASIBLE | subagent/index.ts L334-338；cli.md L229-232；03-custom-prompt.ts L18-31（B 路径） | 无 |
| b3 | 嵌套工具子集 | FEASIBLE | subagent/index.ts L307；sdk.d.ts L34-54 | 无 |
| b4 | extension 内 import SDK/运行时值 | FEASIBLE | virtual-modules.js L13-37（L29 pi-coding-agent、L14-19 typebox、L25 pi-ai）；examples 105 处运行时 import 先例 | 无 |
| b5 | 并发/abort/usage 聚合 | FEASIBLE | subagent/index.ts L219-237/L410-420/L367-376；extensions.md L136 | 无 |

---

## 2. extension 工件设计（`adapters/pi/extension/`）

### 2.1 目录布局

```
adapters/pi/extension/
├── index.ts            # 入口：default factory —— 注册两个 model-only 工具
├── ask-user.ts         # ask_user_question 工具（schema + 映射 + headless 守卫）
├── dispatch-agent.ts   # dispatch_agent 工具（schema + spawn 编排）
├── nested-runner.ts    # 子进程编排纯函数（spawn/JSONL 解析/abort/usage）——与工具壳解耦，可单测
└── paths.ts            # pluginRoot 解析（extension 文件自定位 → 仓库根；角色/skill 路径解析）
```

单一职责（每模块 ≤3 句）：`index.ts` 只做注册装配；`ask-user.ts` 只承载交互契约映射；`dispatch-agent.ts` 只承载调度语义到 CLI 旗标的翻译；`nested-runner.ts` 只承载子进程 IO；`paths.ts` 只承载路径解析。依赖方向 `index → {ask-user, dispatch-agent} → {nested-runner, paths}`，无环。

pi 加载形态：目录含 `index.ts` 即被识别为多文件 extension（extensions.md L46：「Pi loads direct TypeScript or JavaScript files and subdirectories containing an `index.ts` or `index.js` entry point」）；接线经 settings `extensions` 数组（settings.md L152）或单次 `-e adapters/pi/extension`（cli.md L194-195）。

### 2.2 类型导入方式（决议 + 证据）

- **类型**：`import type { ExtensionAPI, ExtensionToolContext, ToolDefinition } from "@earendil-works/pi-coding-agent"`——官方示例同款（extensions.md L20；question.ts L7）。`import type` 编译期擦除，jiti 转译后无运行时解析需求〔推理：TS 语义，`import type` 不产生 require〕。包 exports 证明确认：package.json L14-18 `"." → { types: "./dist/index.d.ts" }`，且 `dist/index.d.ts` L8 重导出全部 Extension 类型。
- **运行时值**：仅 `import { Type } from "typebox"`（schema 构建）——`typebox` 由 pi 运行时虚拟化（virtual-modules.js L14-19，含 `@sinclair/typebox` 别名 L17-19），extension 无需自带 node_modules。dispatch-agent v1（候选 A）不需要运行时 import SDK；若未来切候选 B，`@earendil-works/pi-coding-agent` 运行时 import 由 virtual-modules.js L29 保证。
- **`declare module` 回退**：不采用（虚拟模块 + exports 已闭环，无缺口）。

### 2.3 无 npm 依赖原则 → package.json 决议：**不需要**

依据：extensions.md L48「Put npm dependencies in a **nearby** package.json」——package.json 仅在 extension 声明 npm 依赖时需要；本 extension 全部依赖（typebox/类型）由 pi 运行时提供（§2.2）。零依赖同时消除：安装步骤、供应链面、与 pi 版本错配的 node_modules 阴影〔推理：无依赖即无解析歧义〕。`examples/extensions/with-deps/`（有依赖先例）对照——本设计刻意不进入该形态。

### 2.4 jiti/TS 兼容约束

- pi 经 jiti 加载 TS 免编译（extensions.md L38「Pi uses jiti, so local TypeScript extensions do not need a separate compilation step」）。
- 约束：仅用 jiti 转译兼容的 TS 子集（类型标注/接口/枚举字面量）；不用 decorator/`emitDecoratorMetadata` 依赖、不 import `.json` with resolveJsonModule、不用 `paths` alias（相对导入）〔推理：jiti v2 默认转译能力面；上游全部示例同为普通 TS〕。风险跟踪见 §7 R-3。

---

## 3. adapter 三件套设计

### 3.1 `adapters/pi/adapter-manifest.json` 全字段草案（14 必需键，对齐 `verify_workflow.py` L1610-1624）

```json
{
  "adapter_id": "pi",
  "workflow_id": "software-project-governance",
  "entry_type": "thin-projection",
  "support_status": "designed",
  "supported_runtime": ["pi >= 1.1.0"],
  "trigger": [
    "Before starting a software project task that changes workflow assets from a pi session",
    "When planning, reviewing, or validating project-governance work on the pi platform"
  ],
  "inputs": [
    "skills/software-project-governance/SKILL.md",
    "skills/software-project-governance/core/stage-gates.md",
    "skills/software-project-governance/core/lifecycle.md",
    ".governance/plan-tracker.md"
  ],
  "outputs": [
    ".governance/plan-tracker.md",
    ".governance/evidence-log.md",
    ".governance/decision-log.md",
    ".governance/risk-log.md"
  ],
  "gate_behavior": {
    "on_fail": "block-next-stage",
    "required_action": "update-risk-or-decision-log"
  },
  "validation": {
    "command": "python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters",
    "required": true
  },
  "native_entry": {
    "project_instruction_file": "AGENTS.md",
    "skill_loading": "native-agent-skills-spec",
    "skill_path": "skills/software-project-governance/SKILL.md",
    "note": "pi natively loads AGENTS.md/CLAUDE.md context files (no trust gate) and implements the Agent Skills spec: SKILL.md trees discovered recursively, name/description injected into the system prompt, full instructions loaded on demand, /skill:name commands. Global wiring uses settings.json skills/prompts path arrays pointing at repo-absolute paths (user ruling #1)."
  },
  "runtime_capabilities": {
    "ask_user_question": {
      "status": "degraded",
      "evidence": "extension-bridged: adapters/pi/extension registers model-only tool ask_user_question rendering via ctx.ui dialog methods (select/confirm/input) — available in tui and rpc modes (rpc via extension_ui_request/response subprotocol); headless json/print modes have no UI and the tool fails fast with GOV_ASK_USER_HEADLESS (official precedent examples/extensions/question.ts L53-62). Design FEASIBLE per docs/research/pi-adapter-design evidence table; runtime E2E verification pending → degraded until then (same enumeration precedent as claude adapter: native tool exists, verified surface limited).",
      "degraded_mode": "In headless pi runs (-p / --mode json), use the outer host conversation for interaction boundaries; interactive/RPC pi sessions use the bridged tool."
    },
    "sub_agent": {
      "status": "degraded",
      "evidence": "extension-bridged: adapters/pi/extension registers model-only tool dispatch_agent spawning a nested pi process (--mode json -p --no-session --append-system-prompt <role definition> --tools <subset>) per the official examples/extensions/subagent reference; role-definition + task-spec + dispatch-prompt semantics align with references/agent-dispatch-template.md. Design FEASIBLE; runtime E2E verification pending → degraded until then.",
      "degraded_mode": "Until agent-runtime E2E passes, require external reviewer evidence for Producer-Reviewer separation claims; after E2E passes, upgrade status with machine-recorded evidence."
    },
    "tool_calling": {
      "status": "native",
      "evidence": "pi has native read/bash/powershell/edit/write/grep/find/ls built-in tools; --tools allowlist with +name/-name deltas; powershell is native on Windows."
    },
    "browser": {
      "status": "unsupported",
      "evidence": "No built-in browser automation tool; pi-web-access package unverified for a declarable channel.",
      "degraded_mode": "Mark browser validation blocked or run it from another host adapter."
    },
    "mcp": {
      "status": "degraded",
      "evidence": "MCP mechanism is native (mcp.json + pi mcp CLI + registerMcpServer) but server availability depends on host configuration.",
      "degraded_mode": "Use local scripts and record MCP unavailable when not configured."
    },
    "git_hooks": {
      "status": "native",
      "evidence": "Git hooks are repository-level controls installed into .git/hooks/ and remain active for pi-driven changes."
    },
    "workflow_closure": {
      "status": "degraded",
      "evidence": "pi achieves extension-bridged ask_user_question and sub_agent (tui/rpc interactive scope), native tool_calling and git_hooks; browser/mcp remain host-dependent; bridge runtime E2E pending.",
      "degraded_capabilities": ["ask_user_question", "sub_agent", "browser", "mcp"]
    }
  },
  "exploration_channels": {
    "source_of_truth": "skills/software-project-governance/references/behavior-protocol.md M10.3",
    "note": "M10.3 four behavior-semantic channels materialized for this platform. consult never maps draw: generation is not consultation (生成≠咨询 — canonical rule marker synced from behavior-protocol.md M10.3, drift-guarded by check-cross-references; origin review-FEAT-085-DESIGN-R0 F-3). Honest degradation is legal; capability masquerade is an EXP-03 violation.",
    "channels": {
      "discover": {
        "status": "unsupported",
        "mapping": "none verified",
        "evidence": "No native web search tool in the pi built-in set; pi-web-access package is not a verified declarable channel.",
        "degraded_mode": "Record 判定=受限 per EXP-03; degrade to local knowledge with disclosed limits; never mark offline knowledge as search results."
      },
      "inspect": {
        "status": "native",
        "mapping": "read / grep / find / ls native tools",
        "evidence": "Native inspection tools (runtime_capabilities.tool_calling native)."
      },
      "consult": {
        "status": "degraded",
        "mapping": "dispatch_agent extension bridge (nested pi role agents) for structured second opinions; no external source verified",
        "evidence": "Extension-bridged sub_agent can carry consult-style role prompts (design FEASIBLE, E2E pending); no external (web or cross-model) professional source is verified; ask_user is a user channel, not an external consult channel; draw-style generation is not consultation (R0 F-3).",
        "degraded_mode": "Record the external-source limit per EXP-03 when consult needs information or judgment beyond the host's own bridged sub-agents."
      },
      "validate": {
        "status": "native",
        "mapping": "bash / powershell + verify_workflow.py / test execution",
        "evidence": "Native shell tools execute the validation contract commands (runtime_capabilities.tool_calling native)."
      }
    },
    "degraded_mode": "When a channel is unavailable, record 判定=受限 in the exploration block (M10.2) per EXP-03; never mark offline knowledge as channel results."
  },
  "runtime_e2e": {
    "e2e_level": "real-agent-target-cwd",
    "command": "pi",
    "version_command": "pi --version",
    "verified_on": "<E2E 执行日回填>",
    "evidence": "To be machine-recorded when agent-runtime E2E executes (mixed scope: real agent-dir read-only credentials + --no-session, zero write surface).",
    "target_cwd_e2e": {
      "status": "blocked",
      "blocked_reason": "Scheduled with FEAT-100 implementation acceptance; mixed-scope approval granted by user ruling #3, execution pending."
    },
    "agent_runtime_e2e": {
      "status": "blocked",
      "blocked_reason": "Matrix entry designed (§6.3); run after implementation lands and registration diff is merged."
    },
    "full_e2e_verified": false
  },
  "launcher": "adapters/pi/launch.py"
}
```

合规注记：① 14 键与 L1610-1624 逐键对齐；② `runtime_capabilities.*.status` 全部取值于 `{"native","degraded","unsupported"}`（L5419 机检约束）——「extension-bridged」语义只进 evidence 文本，**不得**作为 status 值；③ `exploration_channels.note` 逐字携带 `生成≠咨询` 标记（QUOTE_SYNC 守卫 L12080-12088 消费 `CONSULT_DRAW_MARKER` L12088）；④ `ADAPTER_RUNTIME_CAPABILITY_POLICY`（L5421-5470）需同步增加 `"pi"` 行——manifest 声明与 policy 常量一致性由 `_validate_runtime_capabilities`（L5473+）机检，pi 行草案：`{"ask_user_question": {"degraded"}, "sub_agent": {"degraded"}, "tool_calling": {"native"}, "browser": {"unsupported"}, "mcp": {"degraded"}, "git_hooks": {"native"}}`（与 chrys L5454-5461 同构的六键全集合）；⑤ `support_status: "designed"` 首发为设计态，E2E 通过后改 `runtime-verified`（先例：opencode L5、chrys L5 均 `runtime-verified`——发布时按验收结果定稿）；⑥ blocked 状态的 runtime_e2e 子块带 `blocked_reason`（L5405-5406：blocked 无 reason = FAIL）。

### 3.2 `adapters/pi/README.md` 结构

```
# Pi Adapter（软件项目治理工作流）
## Tier 1 · 加载模型
- pi 原生双兼容 AGENTS.md/CLAUDE.md 上下文（免信任门）+ Agent Skills 规范（SKILL.md 递归发现、按需加载、/skill:name 命令）
- 项目级：被治理项目根 AGENTS.md 薄指针（先例 adapters/dsh/AGENTS.md.template）
## 接线指南（settings 路径数组——用户裁决①）
在 ~/.pi/agent/settings.json 追加两行（幂等，已存在不重复加）：
  "skills":   [ "D:/AI/agent/claude/coding/project_management_workflow/skills", ... ]
  "prompts":  [ "D:/AI/agent/claude/coding/project_management_workflow/commands", ... ]
  （可选第三行 "extensions": [ ".../adapters/pi/extension" ] 启用两桥工具）
- 验证：pi list / pi 启动诊断 skill 命令可见性（§5 runbook）
## 能力边界
- ask_user_question：extension 桥（tui/rpc 交互模式可用；headless -p/--mode json 返回 GOV_ASK_USER_HEADLESS 错误——走外宿主会话）
- sub_agent：extension 桥 dispatch_agent（嵌套 pi 子进程，角色定义注入；E2E 验证前按 degraded 声明）
- browser unsupported / mcp host-dependent / git_hooks 仓库级 native
## Verify
- python adapters/pi/launch.py
- python skills/software-project-governance/infra/verify_workflow.py check-agent-adapters [--runtime]
## E2E
- python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent pi --timeout 90
```

（tokens 覆盖 MAINSTREAM_AGENT_LOADING_ADAPTERS["pi"] 的必需 token 集——见 §4 登记点 5。）

### 3.3 `adapters/pi/launch.py` 设计 — 只读打印（明确不做安装器）

对齐 chrys/opencode 先例（chrys launch.py 全文 52 行只读打印）：读 `adapters/pi/adapter-manifest.json` → 打印 workflow/entry_type/support_status/trigger/read_order/outputs/gate_behavior/native_entry/runtime_e2e（含 target_cwd_e2e 与 agent_runtime_e2e 子块 status/command/blocked_reason）/full_e2e_verified/validation。**无 `--install`、无任何写操作**——接线正道 = README 指引 + Coordinator 按 §5 runbook 在 R1 防护下执行 settings.json 追加（用户裁决①：其他用户代价最小 = 不用安装器脚本触碰用户环境；dsh 式真安装器属「宿主有包管理面」场景，pi 无此必要）。

---

## 4. 登记面 diff 计划（Governance Developer 可直接照做的文件级清单）

依据〔调研§7.2〕行号清单 + 本次设计新增核验（行号为 0.98.0 基线；实施时以当日文件为准复核）：

### 4.1 `skills/software-project-governance/infra/verify_workflow.py`（9 处）

| # | 登记点 | 行号（0.98.0） | 具体改动 |
|---|---|---|---|
| 1 | `MAINSTREAM_AGENT_ADAPTERS` | L1609 | `["claude","codex","gemini","opencode","chrys","dsh"]` → 追加 `"pi"`（FEAT-101 同期执行则同时移除 `"chrys"`，见 §7 时序注） |
| 2 | `REQUIRED_FILES` | L540-561（chrys 行 L550-553 先例） | 追加 pi 段 3 行：`adapters/pi/adapter-manifest.json` / `adapters/pi/README.md` / `adapters/pi/launch.py`（无 plugin 包目录——pi 无 dotfile 平台约定，〔调研§7.1〕） |
| 3 | `REQUIRED_SNIPPETS` | L788 起（chrys 块 L654-677） | 追加 pi 块：manifest 需含 token `ask_user_question`/`dispatch_agent`/`生成≠咨询`/`adapters/pi/extension`；README 需含 `Tier 1`/`加载模型`/`能力边界`/`agent-runtime-e2e --agent pi` |
| 4 | `RUNTIME_MATRIX_AGENT_IDS` | L2366 | 追加 `"pi"`（保持 research-only 段 L2367 不变） |
| 5 | `MAINSTREAM_AGENT_LOADING_ADAPTERS` | L2394-2483（chrys L2455-2469 先例） | 追加 `"pi"` dict：`display: "Pi"`、`path: "adapters/pi/README.md"`、`tokens: ["Tier 1", "Load", "Verify", "Boundary", "AGENTS.md", "skills/software-project-governance/SKILL.md", "python adapters/pi/launch.py", "check-agent-adapters", "agent-runtime-e2e --agent pi"]`（tokens 必须与 README 实文一致——机检） |
| 6 | `MAINSTREAM_AGENT_LOADING_REQUIRED_DOCS` + `TIER1` | L2369-2378 / L2379-2386 | docs 列表 +`adapters/pi/README.md`；TIER1 列表 +`"Pi"`（**注意大小写**：显示名纯大写，`grep 'pi'` 大小写敏感会漏——FEAT-101 chrys 教训〔调研§9.3-1〕） |
| 7 | `ADAPTER_RUNTIME_CAPABILITY_POLICY` | L5421-5470（chrys L5454-5461 先例） | 追加 §3.1 注记④的 pi 六键行 |
| 8 | `QUOTE_SYNC_ADAPTER_MANIFESTS` | L12080-12087 | 元组追加 `"adapters/pi/adapter-manifest.json"`（七平台；note 的 `生成≠咨询` 标记由 L12088 常量机检） |
| 9 | `AGENT_RUNTIME_E2E_PLATFORMS` + `_agent_runtime_e2e_command_matrix` | L20097 / L20110-20181 | 平台元组追加 `"pi"`（注释 L20094-20096 的排除理由是 dsh 无 headless runner——pi 有 `-p`，不属于该排除类）；矩阵追加 pi 条目（见 §6.3 命令草案） |

消费面自动覆盖：`check_agent_adapter_contract`（L6009-6034 消费 L1609）与 `check_runtime_readiness_matrix`（L3175-3213 消费 L2366）随常量更新自动纳入 pi——无需单独改检查体。

### 4.2 其余登记文件（7 处）

| # | 文件 | 行号（0.98.0） | 具体改动 |
|---|---|---|---|
| 10 | `skills/software-project-governance/SKILL.md` | L492-500 平台表 | 追加行 `\| Pi \| adapters/pi/ + extension/ \| — \|`；表后新增「### Pi 平台说明」段：加载模型（AGENTS.md 原生 + settings 数组接线）+ **工具映射表**（dsh 先例 L509-517 格式）：AskUserQuestion→`ask_user_question`（extension 桥，tui/rpc；headless 报错走外宿主）；Agent 工具 spawn→`dispatch_agent`（prompt=角色定义路径+任务规范+调度模板填充）；Write/Edit/Bash→`write`/`edit`/`bash|powershell`（读取用 `read`/`grep`/`find`/`ls`）；`isolation: "worktree"`→dispatch_agent 无此参数→同文件并发冲突 MUST 串行化（dsh L516 同款措辞）；`/governance`→prompts 数组注册的 `/governance` 模板命令（展开语义待 O-3 冒烟）。e2e 镜像 `project/e2e-test-project/skills/.../SKILL.md` L498 由 byte_copy 投影随发布同步（〔调研§7.2〕），不改源 |
| 11 | 根 `README.md` | L26-34 Tier 1 表 | 追加 Pi 行（zcode 行 L34 先例格式） |
| 12 | `docs/requirements/runtime-readiness-matrix-0.43.0.md` | Summary 表 + 运行时结果表 | 追加 pi 行：manifest=planned/active、version_command=`pi --version`、状态与 §3.1 runtime_e2e 一致——**改 L2366 常量必须同步改此文档行，否则 check L3175 FAIL**（〔调研§7.2〕双向合约） |
| 13 | `docs/requirements/mainstream-agent-loading-0.47.0.md` | 平台表 | 追加 Pi 行（check-mainstream-agent-loading 消费） |
| 14 | `skills/software-project-governance/infra/tests/test_verify_workflow.py` | L2722（六元循环）、L2601-2618/L3347-3360（matrix/adapter 夹具）、L900-1016（plugin.json 覆盖测试） | 夹具循环 +`"pi"`（`_write_all_adapters` 补 pi manifest 夹具数据——14 键 + note 标记；plugin.json 覆盖测试不加 pi——无 dotfile 目录）；FEAT-101 同期则 -chrys |
| 15 | `skills/software-project-governance/infra/contract_matrix/golden_samples.txt` | L97/L283-295/L1358（chrys 金样先例） | adapter 集变更后**再生成**（非手改——〔调研§9.4〕；再生成方式：跑 contract-matrix 生成命令后 diff 审阅，具体命令以 infra/contract_matrix 工具入口当日 --help 为准） |
| 16 | `core/manifest.json` / `core/version-projections.json` / `infra/checks/version.py` / `infra/quickscan_registry.py` / `infra/cleanup.py` / `infra/checks/projection.py` / `infra/checks/triage_domain.py` | 〔调研§7.2〕 | **零改动**——三件套方案不新建 pi 专用版本投影/目录（方案 A 不动版本投影面，用户裁决①；PLUGIN_SCOPE_DIRS L340-357 无需加） |

### 4.3 变更顺序（单 PR 内原子）

1. 新建三件套 + extension/（§2/§3）；2. verify_workflow.py 9 处 + SKILL.md + README + 两矩阵文档（登记与文档**同一 commit**——只改代码常量不删/加文档行 = FAIL，反之亦然）；3. 测试夹具 +pi；4. golden_samples 再生成（独立 commit）；5. CI manifest-consistency 四处同步合约（〔调研§7.2〕.github/workflows/ci.yml 行）无 pi 新目录，天然满足。

---

## 5. 本机接线 runbook（Coordinator 执行用——设计阶段禁止执行）

> 范围：用户裁决① settings 路径数组接线。目标文件 `C:\Users\peter\.pi\agent\settings.json`（用户真实环境——R1 防护 MUST 生效；本节全部命令为**待执行清单**，本设计未运行其中任何一条写命令）。

### 5.1 R1 防护（三选一之 b：完整备份 + 一致性校验）

```
# 1) 备份（时间戳副本，保留原文件）
Copy-Item "$env:USERPROFILE\.pi\agent\settings.json" `
  "$env:USERPROFILE\.pi\agent\settings.json.bak-feat100-$(Get-Date -Format yyyyMMdd-HHmmss)"
# 2) 一致性校验：备份可解析为合法 JSON 且键面与原文件一致
$a = Get-Content -Raw "$env:USERPROFILE\.pi\agent\settings.json" | ConvertFrom-Json
$b = Get-Content -Raw (Get-ChildItem "$env:USERPROFILE\.pi\agent\settings.json.bak-feat100-*" | Select-Object -Last 1).FullName | ConvertFrom-Json
# 比较顶层键集 + skills/prompts/extensions 数组长度（输出应一致）
"original keys: $($a.PSObject.Properties.Name -join ',')"
"backup   keys: $($b.PSObject.Properties.Name -join ',')"
```

### 5.2 幂等追加（三数组条目）

```
$repo = "D:/AI/agent/claude/coding/project_management_workflow"   # 正斜杠（本机既有条目 L40-45 同款格式）
$p = "$env:USERPROFILE\.pi\agent\settings.json"
$s = Get-Content -Raw -Encoding UTF8 $p | ConvertFrom-Json
# 幂等追加：已存在不重复加（skills.md L149-158：路径数组支持绝对路径；同名 skill 冲突 keep-first——追加不覆盖）
foreach ($pair in @(
  @{ prop = "skills";    val = "$repo/skills" },
  @{ prop = "prompts";   val = "$repo/commands" },
  @{ prop = "extensions";val = "$repo/adapters/pi/extension" }   # 两桥（可选，默认建议加）
)) {
  if (-not $s.($pair.prop)) { $s | Add-Member -NotePropertyName $pair.prop -NotePropertyValue @() }
  $cur = @($s.($pair.prop)); if ($cur -notcontains $pair.val) { $s.($pair.prop) = @($cur + $pair.val); "ADD $($pair.prop): $($pair.val)" } else { "SKIP $($pair.prop) (already present)" }
}
$s | ConvertTo-Json -Depth 10 | Set-Content -Encoding UTF8 $p
```

### 5.3 验证（只读）

```
pi --version                                   # 1.1.0
pi list                                        # 列出注册包与路径（本机已验证 exit 0，〔调研§5〕）——确认本仓 skills/commands/extension 路径可见
pi -e "$repo/adapters/pi/extension" -p "ping" --no-session   # 仅当凭证面获批（§6.4）；无凭证时改用启动诊断
# 交互验证（人工）：pi 启动 → 启动诊断 Extensions/Skills 列表含 governance 条目 → /skill:software-project-governance 可见
```

### 5.4 回滚

```
Copy-Item (Get-ChildItem "$env:USERPROFILE\.pi\agent\settings.json.bak-feat100-*" | Select-Object -Last 1).FullName `
  "$env:USERPROFILE\.pi\agent\settings.json" -Force
# 校验：pi list 恢复原状；三个 bak 副本保留至少一个版本周期后清理
```

---

## 6. E2E 验收方案（混合口径——用户裁决③）

口径定义：**真实 agent-dir（`~/.pi/agent` 只读凭证）+ `--no-session`（内存会话，写面=0）+ `--tools read`（只读工具子集）**。隔离面：会话目录不落盘、项目资源信任经 `-na` 显式拒绝（e2e-test-project 的 AGENTS.md 是 context file，免信任加载不受影响——〔调研§2〕security.md L57）。

### 6.1 L0 静态（无凭证）

`python adapters/pi/launch.py`（打印 manifest）+ `python skills/.../verify_workflow.py check-agent-adapters`（契约 7/7 含 pi）+ `pi --version` / `pi --help`（exit 0）。

### 6.2 L1 隔离冒烟（PI_CODING_AGENT_DIR 重定向——无凭证）

```
$tmpAgent = Join-Path $env:TEMP "pi-smoke-agent-$(Get-Date -Format yyyyMMddHHmmss)"
New-Item -ItemType Directory -Force $tmpAgent | Out-Null
$env:PI_CODING_AGENT_DIR = $tmpAgent
pi list        # 空注册面正常退出（exit 0）——环境变量重定向机制成立
$env:PI_CODING_AGENT_DIR = $null; Remove-Item -Recurse -Force $tmpAgent
```

验收措辞（真实环境防护先例）：「**隔离环境安装冒烟（环境变量重定向至临时目录）通过**」。

### 6.3 L2/L3 agent-runtime E2E（混合口径，入矩阵）

`_agent_runtime_e2e_command_matrix` pi 条目草案（对齐 opencode 条目 L20166-20180 结构 + 探针判据 `_agent_runtime_e2e_prompt` L20100-20107）：

```python
{
    "agent": "pi",
    "label": "pi CLI headless target cwd",
    "cwd": e2e_dir,                     # project/e2e-test-project
    "command": [
        "pi", "-p", prompts["pi"],      # 探针文本 = _agent_runtime_e2e_prompt("pi")
        "--tools", "read",              # 只读子集
        "--no-session",                 # 写面=0
        "-na",                          # 信任一次性拒绝（headless 必需；context files 不受影响）
    ],
    "validator": _validate_agent_runtime_e2e_passed,   # 判据 E2E_PLATFORM=pi; E2E_AGENT=...; E2E_STAGE=...; E2E_MODE=...
}
```

运行：`python skills/software-project-governance/infra/verify_workflow.py agent-runtime-e2e --agent pi --timeout 90`。费用与凭证控制：单次探针为一条最小 prompt + read 工具（模型调用面最小化）；凭证为真实 agent-dir 只读复用（defaultProvider 本机已配，〔调研§5〕）；不触发登录流。

**ask_user 桥 headless fallback 的 E2E 判据**（独立于矩阵探针，验收阶段执行一次）：以 `-p` 模式给 prompt「调用 ask_user_question 工具问我要继续吗」→ 断言最终输出含 `GOV_ASK_USER_HEADLESS`（§1a.3 固定标记）且进程正常退出（错误路径 fail-fast 而非挂起）。**extension 加载验证（只读探测）**：`pi -e "<repo>/adapters/pi/extension" -p "Reply with the word ok only" --no-session --tools read` → 启动诊断无 extension error（extensions 加载错误会在启动 Extensions 列表报告，extensions.md L1716-1719 `LoadExtensionsResult.errors`）+ 输出 "ok"——一次最小模型调用同时验证「extension 可加载」与「模型可声明工具」；无凭证环境降级为「启动即退出码断言 + stderr 无 extension 报错」（启动诊断在交互模式人工看，或 `--mode json` 首事件检查〔未实测：json 事件流是否含 extension 加载错误事件——实施时以 docs/json.md 为准补判据〕）。

### 6.4 验收顺序 gate

L0/L1（无凭证）先行 → L2 extension 加载探测（一次最小模型调用）→ L3 矩阵 E2E + headless fallback 判据 → 全过后：manifest `support_status` → `runtime-verified`、`runtime_e2e.*.status` → `passed`、`full_e2e_verified: true`、capability policy 评估升级（degraded→native 需机录 EVD）。

---

## 7. 风险与开放问题

### 7.1 风险登记（含蓝军挑战 ≥3 + 缓解）

| ID | 蓝军挑战/风险 | 等级 | 缓解 |
|---|---|---|---|
| R-1 | 如果 pi 升级（1.1.x→1.2+）移除/改名 VIRTUAL_MODULES 键或 dialog API，extension 静默失效怎么办？ | 中 | ① 类型 import 全部 `import type`（擦除后运行时零依赖，仅 typebox 一个运行时值依赖——virtual-modules L14-19 双别名兜底）；② 版本锚点：README + manifest `supported_runtime: ["pi >= 1.1.0"]` + host 契约记录（dsh host-contract.json 先例〔调研§9.1 O-7〕）；③ E2E 矩阵条目即回归探针——pi 升级后跑 `agent-runtime-e2e --agent pi` 自动暴露 |
| R-2 | 如果 E2E 环境凭证缺失/失效（auth.json 失效、provider 限额），矩阵 FAIL 会不会误判为 adapter 缺陷？ | 中 | 探针 FAIL 输出分类：模型 errorMessage 透传 vs 工具/加载错误（§1b.2 错误语义）；EVD 记录区分「环境凭证面」与「桥接面」；L0/L1 无凭证层先行隔离登记面问题 |
| R-3 | jiti 转译兼容：如果 extension TS 用了 jiti 不支持的语法（decorator/路径别名），加载期报 extension error | 中 | §2.4 语法白名单约束 + L2 只读探测纳入验收（§6.3）+ 示例语法面（全部官方 examples 同子集）作为事实基线 |
| R-4 | 同名 skill 冲突静默遮蔽（用户 developer-kit 已注册 skills 与本仓 25+ 子 skill 同名——keep-first + 告警，〔调研§9.1 O-10〕） | 中 | 接线冒烟清单加「冲突面检查」：pi 启动诊断告警扫描 + `pi list` 对照；发现同名 → settings 数组顺序调整（先注册者优先）或收窄注册面（O-6） |
| R-5 | `--system-prompt` 整体替换使嵌套 agent 丢失 pi 默认工具使用指引 → 子代理不会正确调用工具 | 中 | `system_prompt_mode` 默认 `append`（官方 subagent 先例 L338 正是 append）；`replace` 仅显式 opt-in 且 description 说明代价（§1b.2） |
| R-6 | Windows spawn 解析：`spawn("pi", ...)` 在 `shell:false` 下解析 `pi.ps1`/`pi.cmd` 的行为未实测 | 中 | nested-runner 采用官方 `getPiInvocation` 模式并优先 `process.execPath + <pi-pkg>/dist/bundle/cli.js` 绝对路径（本机 npm 布局可解析）；实施首日冒烟 |
| R-7 | settings.json 手工编辑损坏用户 pi 环境（JSON 语法/编码） | 低 | §5 runbook：备份+校验先行、ConvertFrom-Json 往返、UTF-8 显式编码（FIX-278 同教训）、幂等 SKIP 语义、回滚副本 |
| R-8 | FEAT-100(+pi) 与 FEAT-101(-chrys) 时序交错导致常量/文档/夹具不一致（grep 'chrys' 大小写与 gitignored 盲区，〔调研§9.3〕） | 中 | 两任务同 PR 序列执行（§4.3 顺序）；复核命令 `grep -in chrys` + `grep -in "\bpi\b"`（大小写不敏感双向）；O-8 由 Coordinator 定夺版本 0.99.0 单 minor 承载 |

### 7.2 开放问题（移交 Coordinator/用户）

| # | 问题 | 影响 | 建议默认 |
|---|---|---|---|
| O-1' | prompts 直注册 `commands/` 的两个待验证点（首行 `#` 标题作 description 回退、`$1/$@` 替换与文件内 `$` 字面量冲突——〔调研§8.1-2〕） | /governance 等 9 命令在 pi 的可用性；不过则需 `adapters/pi/skill-shims/` 兜底（文件面 +1） | 实施首日冒烟逐命令验证展开结果；失败即建 shims（dsh 先例）并补 REQUIRED_FILES 行 |
| O-2' | skill 全量注册的上下文成本（26 个 SKILL.md description 全注入 system prompt，〔调研§9.1 O-6〕） | 路由质量/上下文占用 | 首版全量（与 chrys/dsh 同构）；观察后评估收窄 |
| O-3' | `--mode json` 事件流是否含 extension 加载错误事件（L2 无凭证判据的机器化） | E2E 判据可自动化程度 | 实施时读 docs/json.md 定判据；未证实前保留人工启动诊断面 |
| O-4' | capability 升级门槛：degraded→native 需要哪级证据（矩阵 E2E 通过是否充分） | manifest 定稿措辞 | 建议标准：矩阵 E2E passed + 一次 dispatch_agent 真派发 EVD（角色读取→嵌套运行→结构化返回三步机录） |
| O-5' | 版本锚点记录载体（host-contract 类文件 vs manifest 字段） | 维护面 | manifest `supported_runtime` + README 验证版本注记（1.1.0），不新建文件 |

### 7.3 ADR 索引（本文档承载的关键决策，含可逆性）

| ADR | 决策 | 可逆性 |
|---|---|---|
| ADR-1 | 接线 = settings 路径数组（用户裁决①；方案 B Pi Package/方案 C drop-in 拷贝的排除理由见〔调研§8〕——B 动版本投影面违反裁决、C 违反单一事实源） | 可逆（settings 三行可随时移除） |
| ADR-2 | subagent 桥 = spawn 嵌套子进程（候选 A），SDK 进程内为备选（§1b.1 完整取舍） | 可逆（工具 schema 不变前提下切换实现） |
| ADR-3 | ask_user headless = 结构化错误返回（非 RPC 转发、非挂起）（§1a.3 三依据） | 可逆（headless 交互若未来有协议载体可加队列通道） |
| ADR-4 | manifest 初版 capability = degraded（extension-bridged 语义入 evidence；E2E 后按 O-4' 门槛升级）——枚举合规（L5419）+ 诚实口径（EXP-03） | 可逆（随 EVD 升级） |
| ADR-5 | launch.py 只读打印、不做安装器（§3.3；接线走 README + Coordinator R1 runbook） | 可逆 |

---

## 8. 验收对照（任务验收标准逐条）

| 验收标准 | 落位 |
|---|---|
| 设计文档落盘 + 7 节齐备 | 本文 §0-§7（§1 两桥裁定 / §2 extension 工件 / §3 三件套 / §4 登记面 diff / §5 runbook / §6 E2E / §7 风险开放问题） |
| 每个裁定有 pi 包内证据锚点、无「应该是/大概」；未证实面显式标注 | §1c 汇总表逐行锚点；全文「未实测」「推理」「未证实」标注点：§1b.1 Windows spawn、§6.3 json 事件流、§2.2 import type 擦除、O-1'/O-3' |
| 工具 schema 与本仓交互契约/调度模板语义对齐 | §1a.2 映射表（questions[]/id/header/options{label,description}/multi_select）；§1b.2（role_definition_path/task_skill_path/task_prompt 对齐 agent-dispatch-template 占位符表 L94-108） |
| 「Governance Developer 可直接照做」的文件级实施清单（含行号） | §4.1（verify 9 处行号）+ §4.2（7 文件行号）+ §4.3 顺序 + §2/§3 工件规格 |
| 结构化摘要 | 见文档 §0 摘要表 + 任务返回（两桥裁定 + ≤12 条设计要点 + 实施清单确认 + 遗留开放问题） |

> 设计阶段硬门槛自检：全程只读（唯一写入 = 本文档）；未运行任何 pi 写命令/登录流/模型调用；未修改 `skills/**`、`agents/**`、`adapters/**`、`infra/**`、`.governance/**`；候选方案 ≥2（ADR-1/2/3 各含备选与排除理由）；蓝军挑战 ≥3（R-1~R-8）；无循环依赖（§2.1 依赖方向声明）。
