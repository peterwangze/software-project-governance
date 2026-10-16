# FEAT-100-DESIGN-R0 设计审查报告 — pi 平台 Adapter：extension 桥接架构 + 三件套落位方案

- **Task ID**: FEAT-100（审查对象=设计文档，R0 轮）
- **审查对象**: `docs/requirements/pi-adapter-design-0.99.0.md`（Architect 产出，655 行）
- **审查基础输入**: `docs/research/pi-adapter-integration-research-0.98.0.md`（调研事实源，320 行）
- **审查人**: Design Reviewer Agent（角色定义 `agents/design-reviewer.md`；执行规范 `skills/design-review/SKILL.md`）
- **日期**: 2026-10-14 · **轮次**: R0（首轮，无前轮引用）
- **审查方式**: 全程只读静态审查（未运行任何 pi 命令、未修改任何产品文件与 `.governance/`；唯一写入=本报告）

---

## 结论

> **REVIEW RESULT: APPROVED_WITH_NOTES**
>
> unresolved_blockers=0
>
> 两桥（ask_user / subagent）FEASIBLE 裁定的证据锚点链 **100% 实证成立**（55+ 处抽验，见 §3）；7 审查维度无 BLOCKING 发现。P1×1（锚点文件名失实——断言为真、行号正确、仅文件归属错，修复一行）+ P2×2（README tokens 语言不自洽与 boundary 短语缺口——实施即 FAIL 但修复路径已在设计自身原则内闭合；嵌套子进程 extension 继承披露缺口）+ P3×4，全部为可在实施 PR 内闭环的规格级缺陷，不构成设计返工。建议：Architect 在实施交付物中按 §4 发现清单逐条闭环（F-1/F-2 为 MUST-fix，F-3 为 SHOULD-fix，F-4~F-7 为建议），无需重 spawn 设计复审；实施验收（E2E + check 全绿）承担最终验证。

**阻塞发现清单**: 无（P0=0）。
**非阻塞 notes**: 7 条（P1×1、P2×2、P3×4）。

---

## 1. 硬门槛裁决（角色定义 5 项）

| 门槛项 | 阈值 | 判定 | 证据 |
|---|---|---|---|
| 候选方案数 | ≥2 | **PASS** | ADR-1 三案（settings 数组/Pi Package/drop-in，§8 调研 + 设计 ADR-1 排除理由）；ADR-2 两案（spawn 子进程 vs SDK 进程内，§1b.1 完整取舍）；ADR-3 三依据裁决链（§1a.3） |
| ADR 关键字段完整 | =100% | **PASS** | §7.3 ADR 索引 5 条各含：背景/决策/备选与排除理由/后果（影响范围）/可逆性；后续动作经 §7.2 O-1'~O-5' 移交；日期在文档头（2026-10-14） |
| 蓝军挑战条数 | ≥3 | **PASS** | R-1~R-8 共 8 条独立 ID，各配等级与缓解（§7.1） |
| 模块无循环依赖 | =0 | **PASS** | §2.1 依赖方向 `index → {ask-user, dispatch-agent} → {nested-runner, paths}` 单向无环；5 模块各 ≤3 句职责 |
| Bar Raiser 评审 | 已执行 | **PASS** | 本报告即独立评审记录（Architect 产出自证不构成评审；Reviewer 与设计者角色分离） |

---

## 2. 审查维度逐项结论（任务 7 维度 × SKILL 4 维度映射）

### D1 证据锚点抽验（重点维度）—— PASS（1 处轻度失实 → F-1）

**抽验规模**：ask_user 桥 15 处、subagent 桥 21 处、本仓契约/常量/先例 18 处，合计 55+ 处（要求 ≥8、两桥各 ≥3）。逐锚点实读记录见 §3。

**结论**：设计两桥 FEASIBLE 裁定引用的 pi 包证据**行号与语义几乎全部逐字实证一致**——包括所有关键链路锚点（model-only exposure、dialog 签名、hasUI 语义、RPC 子协议、官方 subagent 全部机制锚点、virtual-modules、CLI 旗标）。唯一失实：§1a.4 日志面将 details 契约出处标为 `types.d.ts L135-136`，实际出处为 **extensions.md L135-136**（详见 F-1）。该失实不影响任何裁定结论。

### D2 契约对齐 —— PASS（附 F-3 补强建议）

**ask_user_question schema 逐字段对齐本仓契约**——实读对照 `behavior-protocol.md` M5.1（L294-338：AskUserQuestion 唯一合法渠道、结构化选项、agent MUST 等待回复）与本仓 questions[] 契约结构：

| 契约字段 | 设计 schema（§1a.4） | 判定 |
|---|---|---|
| `questions[]` 顶层 | `Type.Array(GovAskQuestion)` | ✅ |
| `id`（stable id, echoed in answer） | `Type.String({ description: "Stable id for this question; echoed in the answer" })` | ✅ 逐字 |
| `question` | `Type.String({ description: "The specific question to ask the user" })` | ✅ 逐字 |
| `header?` | `Type.Optional(Type.String(...))` | ✅ |
| `options?[{label, description?}]` | `GovAskOption = { label, description? }`，options 可选=自由文本题 | ✅ |
| `multi_select?` | `Type.Optional(Type.Boolean(...))` | ✅ |
| 取消语义 | 整体取消 → `cancelled: true` 结构化结果回传模型按治理规则重问（§1a.2 末行） | ✅ 对齐「跳过=违规、取消为显式结果」 |
| multi_select 原生缺失 | 降级为逐项 confirm 序列，交互损失显式声明（§1c a5） | ✅ 诚实 |

pi dialog 映射（§1a.2）：header 拼入 select title、`"{i+1}. {label}"` 序号解析、description 拼接截断 ~80 字符、`input()` 承载自由文本——映射完整且每行附 types.d.ts L74/L78 签名约束，实证成立（L74 select 仅收 `string[]`，拼接法确为唯一无损通道）。

**dispatch_agent 对齐调度模板**——实读 `references/agent-dispatch-template.md` 占位符表 L94-108：`{role_definition_path}`/`{task_skill_path}` → 设计同名参数 ✅；`{task_id}/{task_description}/{file_list}/{acceptance_criteria}/{hard_gates}/{destructive_redlines}` → 设计 `task_prompt` 参数描述中逐一列举并强制「Fully-filled dispatch prompt following references/agent-dispatch-template.md」✅。

**Sub-agent 硬边界三要素**：
1. **不接触用户**：嵌套子进程 `--mode json -p`（无 UI）+ `allowed_tools` 收窄。关键保障链经本审查补证：cli.md L119-120 明确 `--tools` allowlist 为「built-in, **extension**, or custom tools」的选择面——allowlist 不含的工具不声明给模型 → 只读角色的交互/派发工具被机器化排除 ✅（设计未显式引用此证据，见 F-3）。
2. **不改治理记录**：Reviewer 类角色 `allowed_tools=['read','grep','find','ls']` 只读子集 ✅。
3. **返回结构化结果**：最终 assistant 文本 + `details.usage`（官方 L367-376 聚合模式）✅。

### D3 降级语义合规 —— PASS（附 F-7 流程建议）

- **枚举约束**：实读 verify_workflow.py L5419 `RUNTIME_CAPABILITY_STATUSES = {"native", "degraded", "unsupported"}`——设计 manifest 全部 status 取值合规，「extension-bridged」只进 evidence 文本 ✅（§3.1 注记②与实读一致）。
- **先例对齐**：L5422-5429 claude 行 `ask_user_question: {"degraded"}` 实证存在——设计「原生工具存在但验证面受限时记 degraded」的 claude 先例引用成立；opencode manifest L36-44 的 unsupported 降级文案（"Use the outer host conversation..." / "Do not claim Producer-Reviewer separation..."）与设计 §1a.5/§1b.3 留档文案逐字同构 ✅。
- **用户裁决②的落实**：两桥裁定 FEASIBLE、证伪条件未触发 → 不启用 unsupported 降级文案（预稿仅留档）✅；初版 `degraded` 是「已设计、待 runtime E2E 验证」的时序诚实口径而非「证伪降级」，与裁决②「明确证伪才降级（unsupported）」不冲突；升级路径（O-4' 门槛 + §6.4 验收顺序）已定义 ✅。诚实能力声明（EXP-03/生成≠咨询）在 exploration_channels 全四通道落实（§3.1，QUOTE_SYNC marker 见 D4）。
- **14 键 schema**：L1610-1624 实读 14 必需键与 §3.1 manifest 草案逐键对照 14/14 全含 ✅；runtime_capabilities 六键全集合（L5410-5417）齐备 ✅；blocked 子块带 blocked_reason（L5405-5406 机检）✅。

### D4 登记面完整性 —— PASS（附 F-2 新增面规格缺口）

逐项对照调研 §7.2 与设计 §4：

- **verify_workflow.py 9 处**：MAINSTREAM_AGENT_ADAPTERS L1609 ✅（实读六平台元组）、REQUIRED_FILES L540-561 ✅、REQUIRED_SNIPPETS ✅、RUNTIME_MATRIX_AGENT_IDS L2366 ✅、MAINSTREAM_AGENT_LOADING_ADAPTERS L2394-2483 ✅（实读 dict 结构）、REQUIRED_DOCS+TIER1 L2369-2386 ✅（大小写陷阱显式警示 + R-8 复核命令）、ADAPTER_RUNTIME_CAPABILITY_POLICY L5421-5470 ✅（pi 六键行草案与 chrys L5454-5461 同构）、QUOTE_SYNC L12080-12087 ✅（实读六平台元组——追加 pi 即七平台；CONSULT_DRAW_MARKER L12088「生成≠咨询」实读逐字一致）、E2E 平台 L20094-20097 + 命令矩阵 ✅（实读 dsh 排除注释——pi 有 `-p` 不属排除类，论证成立）。消费面自动覆盖说明（L6009-6034/L3175-3213）与调研一致 ✅。
- **其余 7 文件**：SKILL.md 平台表+工具映射段（含 e2e 镜像 byte_copy 不改源）✅、根 README Tier 1 表 ✅、runtime-readiness-matrix 双向合约（改常量必同步文档行）✅、mainstream-agent-loading ✅、test_verify_workflow.py 夹具（plugin.json 覆盖测试不加 pi——无 dotfile 目录，正确）✅、golden_samples **再生成非手改**（以工具入口当日 --help 为准——与调研 §9.4 一致）✅、core/manifest.json 等七文件零改动（方案 A 不动版本投影面，与调研「仅当建 pi 专用目录时」一致）✅。ci.yml 无新 top-level 目录天然满足 ✅。
- **遗漏检查**：调研 §7.2 全部登记点在 §4 均有对应条目，**无遗漏**。但发现设计新增面（README 规格自身）存在两处与机检合约的缺口——"Load"/"Boundary" token 语言不自洽 + boundary 三短语未披露（见 F-2，实读 verify_workflow.py L5090-5096 消费逻辑 + dsh README L65 先例佐证）。

### D5 真实环境防护 —— PASS

- **R1 三选一之 b 完备**（§5.1）：时间戳备份副本（保留原文件）+ 一致性校验（原件/备份双 ConvertFrom-Json 解析 + 顶层键集 + 数组长度对比）✅。
- **幂等追加**（§5.2）：`-notcontains` SKIP 语义、缺失属性 Add-Member 兜底、`@()` 防单元素数组退化、显式 UTF-8 读写（FIX-278 同教训）✅。keep-first 冲突语义引 settings.md L149-158（实读 L152-154 skills/prompts/extensions 路径数组 + L147 绝对路径支持——引用一致）✅。
- **回滚**（§5.4）：bak 副本 `-Force` 恢复 + `pi list` 验证 + 副本保留策略 ✅。
- **launch.py 只读**（§3.3）：实读 chrys launch.py 全文 52 行——纯只读打印（读 manifest → print，零写操作），设计先例引用准确；pi 版「无 --install、无任何写操作」与用户裁决①（其他用户代价最小=不用安装器触碰用户环境）一致 ✅。
- **阶段纪律**：§5 明确「设计阶段禁止执行」「本设计未运行其中任何一条写命令」✅。

### D6 E2E 方案 —— PASS（附 F-5/F-6 补强建议）

- **混合口径判据可机器断言**：矩阵探针判据 `E2E_PLATFORM=pi; E2E_AGENT=...; E2E_STAGE=...; E2E_MODE=...` 与实读 `_agent_runtime_e2e_prompt` L20100-20107 逐字一致；validator 复用既有 `_validate_agent_runtime_e2e_passed` ✅。
- **headless fallback 判据成立**：`GOV_ASK_USER_HEADLESS` 固定标记（§1a.3 守卫 + §1a.4 错误表）→ `-p` 模式 stdout 最终回复可断言 + 进程正常退出（fail-fast 而非挂起——`ctx.hasUI===false` 直接返回错误，不阻塞）✅。
- **`-na` + context files 论证实证**：security.md L57（context files 免信任加载）+ L61（CLI 覆盖优先）+ L77-82（print/json 无信任提示、-na 显式一次性决策）实读一致；`--no-session` 写面消除 + `--tools read` 只读 ✅。trust 决策不落盘（L73 仅 `/trust` 保存）✅。
- **分层验收顺序**（L0/L1 无凭证先行 → L2 探测 → L3 矩阵）与调研 §8.4 一致；L1 验收措辞对齐真实环境防护先例 ✅。

### D7 蓝军复扫 —— PASS（4 处自报标注全闭环；新增 2 处披露缺口 → F-2/F-3）

设计自报 4 处「未实测/推理」标注的闭环核验：

| 自报标注 | 位置 | 闭环路径 | 判定 |
|---|---|---|---|
| Windows spawn 解析（pi.ps1/shell:false） | §1b.1 ADR-2 后果段 | R-6：优先 `process.execPath + cli.js` 绝对路径 + 实施首日冒烟 | ✅ |
| json 事件流是否含 extension 加载错误 | §6.3 | O-3'：实施时读 docs/json.md 定判据；未证实前保留人工启动诊断面 | ✅ |
| `import type` 编译期擦除 | §2.2 | §6.3 L2 加载探测覆盖（加载失败即暴露，jiti 转译错误在启动诊断报告） | ✅ |
| prompts 展开两点（首行 description 回退 + $ 替换冲突） | O-1'（引调研 §8.1-2） | 实施首日逐命令冒烟 + shims 兜底（dsh 先例）+ REQUIRED_FILES 补行 | ✅ |

本审查新增识别的未披露风险：F-2（README 机检合约缺口——实施即暴露）、F-3（嵌套子进程 extension 继承——机制有兜底但未论证）。两处均已在本报告给出闭环路径，无第三处。

---

## 3. 证据锚点抽验记录（逐锚点实读）

### 3a. ask_user 桥（15 处，要求 ≥3）

| # | 设计引用 | 实读结果 | 判定 |
|---|---|---|---|
| A1 | extensions.md L15（工厂函数收 ExtensionAPI） | L15 原文「An extension exports a default factory that receives `ExtensionAPI`」 | ✅ 逐字 |
| A2 | extensions.md L76（registerTool 集成点） | L73-87 集成点表，L76 `pi.registerTool()` | ✅ |
| A3 | extensions.md L157（model-only 语义） | L157「declared to the model while active, never callable. Use it for tools that orchestrate other tools **or ask the user**」 | ✅ 逐字 |
| A4 | extensions.md L244-253（模式语义）+ L146（isError） | L248-251「Extensions load in interactive, RPC, JSON, and print modes... JSON and print modes have no UI」+ L253「Keep tool and event behavior independent from rendering」+ L146「return the result with `isError: true` instead of throwing」 | ✅ 逐字 |
| A5 | types.d.ts L40-45（ExtensionUIDialogOptions） | L40-45 `{ signal?: AbortSignal; timeout?: number }`，注释「Dialog auto-dismisses with live countdown」 | ✅ 逐字 |
| A6 | types.d.ts L74/L76/L78（select/confirm/input） | L74 `select(title: string, options: string[], opts?): Promise<string \| undefined>`；L76 `confirm(title, message, opts?): Promise<boolean>`；L78 `input(title, placeholder?, opts?)`——签名仅收 string[]，无结构化选项 | ✅ 逐字（拼接法事实约束成立） |
| A7 | types.d.ts L212/L219（ExtensionMode/hasUI） | L212 `"tui" \| "rpc" \| "json" \| "print"`；L219「Whether dialog-capable UI is available (**true in TUI and RPC modes**)」 | ✅ 逐字 |
| A8 | types.d.ts L448-506（ToolDefinition） | L448-506：name/label/description/parameters(TypeBox)/execute 全存在；exposure L475、namespace L477、annotations L479、executionMode L499（sequential/parallel）、defaultActive L481-484（direct/model-only 默认 true） | ✅ |
| A9 | types.d.ts L1204-1205（registerTool） | L1204-1205 `registerTool<...>(tool: ToolDefinition<...>): void` | ✅ 逐字 |
| A10 | question.ts L53-62（headless 错误先例） | L53-62 `if (ctx.mode !== "tui") return { content: [{ type: "text", text: "Error: UI not available (running in non-interactive mode)" }], ... }` | ✅ 逐字 |
| A11 | questionnaire.ts L93-95 | L93-95 `if (ctx.mode !== "tui") return errorResult("Error: UI not available...")` | ✅ |
| A12 | rpc-extension-ui.md L7-10/L14-16/L25/L31-46/L172-194 | L3「In RPC mode, supported calls become a request/response subprotocol」；L7 dialog 方法 extension_ui_request(stdout)/extension_ui_response(stdin, 匹配 id)；L10 timeout 自动消解；L14-16 `custom()` returns `undefined`；L25「`ctx.hasUI` is `true` in RPC mode」；L172-194 响应三形态 value/confirmed/cancelled + 取消时 select/input→undefined、confirm→false | ✅ 全部逐字 |
| A13 | extensions.md L46/L48（多文件 extension/nearby package.json） | L46「Pi loads direct TypeScript or JavaScript files and subdirectories containing an `index.ts` or `index.js` entry point」；L48「Put npm dependencies in a nearby `package.json`」 | ✅ 逐字（§2.1 加载形态 + §2.3 零依赖决议依据成立） |
| A14 | §1a.4「types.d.ts L135-136（details 契约）」 | types.d.ts L135-136 实为 setEditorText/getEditorText——**失实**；契约真实出处 extensions.md L135-136「a `details` field for rendering or state reconstruction」（逐字吻合）；类型层佐证 `@earendil-works/pi-agent-core/dist/types.d.ts` L373-374「Arbitrary structured details for logs or UI rendering」 | ❌ 文件名失实 → **F-1**（断言为真、行号正确） |
| A15 | extensions.md L138-139（throw→failed result） | L138「Throw from `execute()` to produce a failed tool result」 | ✅ 逐字 |

附：官方先例守卫差异说明——question.ts 用 `ctx.mode !== "tui"` 守卫而设计用 `ctx.hasUI`：官方示例渲染走 `ctx.ui.custom()`（tui-only，rpc-extension-ui.md L14-16 证实 RPC 返回 undefined），设计渲染走 dialog 方法族（tui/rpc 双可达）——设计 §1a.2 已显式区分两者，守卫差异自洽，非失实。

### 3b. subagent 桥（21 处，要求 ≥3）

| # | 设计引用 | 实读结果 | 判定 |
|---|---|---|---|
| B1 | subagent/index.ts L300（json/-p/--no-session） | L300 `const args: string[] = ["--mode", "json", "-p", "--no-session"];` | ✅ 逐字 |
| B2 | L302-306（--model/--thinking） | L302-306 模型继承 + thinking 旗标 | ✅ |
| B3 | L307（--tools） | L307 `args.push("--tools", agent.tools.join(","))` | ✅ |
| B4 | L334-338（append-system-prompt） | L334-338 systemPrompt 写临时文件 → `--append-system-prompt` | ✅ 逐字 |
| B5 | L344-421（spawn+JSONL） | L344-347 `getPiInvocation(args)` + spawn(`shell:false`, stdio pipe)；L362-387 message_end/tool_result_end 解析 + usage 聚合 L367-376 + errorMessage L379 | ✅ |
| B6 | L410-420（SIGTERM→SIGKILL） | L410-420 signal→SIGTERM→5000ms 后 SIGKILL | ✅ 逐字 |
| B7 | L249-263（getPiInvocation） | L249-263 含 process.argv[1]/bun 虚拟路径/generic runtime 判断；L262 `return { command: "pi", args }`（PATH 回退） | ✅（Windows 未实测标注恰当） |
| B8 | L239-247（tmpdir+0600） | L240 mkdtemp(os.tmpdir())、L244 writeFile mode 0o600 | ✅ |
| B9 | cli.md L229-232（--system-prompt/--append-system-prompt） | L229-232 `--system-prompt <text\|path>`（替换）/ `--append-system-prompt <text\|path>`（追加、repeatable） | ✅ 逐字 |
| B10 | virtual-modules.js L13-37（L14-19 typebox/L29 pi-coding-agent） | L13-37 VIRTUAL_MODULES；L14-19 typebox 三入口 + @sinclair/typebox 别名；L29 `"@earendil-works/pi-coding-agent"` | ✅ 逐字 |
| B11 | L4-5（isolated context window） | L4-5「Spawns a separate `pi` process for each subagent invocation, giving it an isolated context window」 | ✅ 逐字 |
| B12 | L22-28（运行时 import 包内值） | L22-28 `import { CONFIG_DIR_NAME, ..., getAgentDir, ... } from "@earendil-works/pi-coding-agent"`；L30 `import { Type } from "typebox"` | ✅ |
| B13 | L33-34（MAX_PARALLEL_TASKS=8/MAX_CONCURRENCY=4） | L33-34 逐字 | ✅ |
| B14 | L170-180（倒序找最后 assistant 文本） | L170-180 函数名为 `getFinalOutput`（非 getLastAssistantText——见 F-4），语义=倒序找最后 assistant 文本 | ✅ 语义（措辞 → F-4） |
| B15 | L182-191（isFailedResult） | L182-184 `exitCode !== 0 \|\| stopReason === "error" \|\| "aborted"` | ✅ |
| B16 | L426-439（finally 清理） | L426-439 unlinkSync+rmdirSync 容错清理 | ✅ |
| B17 | L472（registerTool subagent） | L472-473 `pi.registerTool({ name: "subagent", ... })` | ✅ |
| B18 | L219-237（mapWithConcurrencyLimit） | L219-237 并发限制 map 实现 | ✅ |
| B19 | L284-298（Unknown agent 错误） | L286-294 `Unknown agent: "...". Available agents: ...` | ✅ |
| B20 | L520-548（项目信任门） | L520-548 `ctx.ui.confirm("Run project-local agents?", ...)` | ✅ 逐字 |
| B21 | sdk.d.ts L10-65/L67-74（候选 B 机制+排除理由①） | L10-65 CreateAgentSessionOptions（cwd/agentDir/model/tools/resourceLoader/sessionManager）；L67-70 CreateAgentSessionResult.extensionsResult（「Extensions result (for UI context setup...)」）——「构建第二个 extension runtime」排除理由锚点成立 | ✅ |

### 3c. 本仓契约/常量/先例（18 处）

| # | 引用 | 实读结果 | 判定 |
|---|---|---|---|
| V1 | verify L5419 RUNTIME_CAPABILITY_STATUSES | `{"native","degraded","unsupported"}` | ✅ |
| V2 | verify L1609 MAINSTREAM_AGENT_ADAPTERS | `["claude","codex","gemini","opencode","chrys","dsh"]` | ✅ |
| V3 | verify L1610-1624 14 必需键 | 14 键逐键一致；§3.1 manifest 14/14 全含 | ✅ |
| V4 | verify L5421-5470 policy（claude L5422-5429/chrys L5454-5461） | claude ask_user_question={"degraded"} 先例成立；chrys 六键结构成立 | ✅ |
| V5 | verify L5405-5406 blocked_reason 强制 | 逐字 | ✅ |
| V6 | verify L12080-12088 QUOTE_SYNC + MARKER | 六平台元组 + `CONSULT_DRAW_MARKER = "生成≠咨询"` | ✅ |
| V7 | verify L20094-20107 E2E 平台+探针 | dsh 排除注释 + 四平台元组 + E2E_PLATFORM 探针模板逐字 | ✅ |
| V8 | pi package.json L14-18 exports | `"." → { types: "./dist/index.d.ts", import: "./dist/index.js" }` | ✅ |
| V9 | opencode manifest L36-45 降级先例 | ask_user L36-40 / sub_agent L41-45 文案逐字同构 | ✅ |
| V10 | pi dist/index.d.ts L8 类型重导出 | L8 重导出 ExtensionAPI/ExtensionContext/ExtensionUIContext/ExtensionUIDialogOptions 等 | ✅ |
| V11 | settings.md L149-158 路径数组 | L152-154 extensions/skills/prompts string[]；L147 绝对路径/~ | ✅ |
| V12 | security.md L57/L61/L77-82 信任语义 | context files 免信任；CLI 覆盖优先；print/json 无提示 + -na 一次性 | ✅ |
| V13 | behavior-protocol.md M5.1（L294-338） | 唯一合法渠道 + 结构化选项 + 等待回复 | ✅ |
| V14 | agent-dispatch-template.md L94-108 占位符表 | 逐占位符对齐（见 D2） | ✅ |
| V15 | interaction-boundary.md（Type A/B/C + critical triggers） | 交互边界分类与设计契约映射无冲突 | ✅ |
| V16 | chrys launch.py「52 行只读打印」 | 全文 52 行纯只读打印 | ✅ |
| V17 | verify L5083-5098 README tokens/boundary 机检 | L5090-5092 token 精确子串匹配；L5093-5096 三 boundary 短语强制 | ✅（暴露 F-2） |
| V18 | dsh README 先例 | L7「加载模型」/L55「能力边界」中文标题 + L65 三短语 no-overclaim 声明 | ✅（F-2 佐证） |

---

## 4. 发现清单（P0/P1/P2/P3，每条附证据）

### P0（BLOCKING）—— 无

### P1（严重——实施 MUST-fix）

**F-1｜锚点文件名失实：§1a.4 details 契约出处标注错误**
- 位置：设计文档 §1a.4 日志面第 ① 条（L143）「`details` 字段持久化到 tool result（**types.d.ts L135-136** 契约：`details` 用于 rendering/state reconstruction）」
- 实读证据：`<pi-pkg>\dist\core\extensions\types.d.ts` L135-136 实为 `setEditorText`/`getEditorText`（editor 方法族）；契约原文在 `<pi-pkg>\docs\extensions.md` **L135-136**「Its result requires model-facing `content` and a `details` field **for rendering or state reconstruction**」；类型层佐证 `<pi-pkg>\node_modules\@earendil-works\pi-agent-core\dist\types.d.ts` L373-374「Arbitrary structured details for logs or UI rendering」。
- 影响：断言为真、行号正确、仅文件归属错——不影响 FEASIBLE 裁定与日志面设计有效性；但按「锚点失实列 P1」口径必须列出。实施者按错锚点查找会落空。
- 修复：§1a.4 该处「types.d.ts」改为「extensions.md」（一行）。实施 PR 中顺手修正即可。

### P2（WARNING——实施 SHOULD-fix，两处实施即暴露）

**F-2｜README tokens 与骨架语言不自洽 + boundary 三短语未披露（check-mainstream-agent-loading 必 FAIL）**
- 位置：设计 §4.1 登记点 5（L478）tokens 草案 vs §3.2（L436-456）README 骨架。
- 实读证据：
  1. verify_workflow.py L5090-5092：`for token in spec["tokens"]: if token not in content: failures.append(...)` —— 精确子串匹配（大小写敏感）；
  2. §4.1 #5 tokens 含英文 `"Load"`、`"Boundary"`；§3.2 README 骨架标题为中文「## Tier 1 · 加载模型」「## 能力边界」——"Load"/"Boundary" 两 token 在骨架文本中不存在 → 机检 FAIL；
  3. 对照先例：chrys tokens（L2458-2468）英文 `"Load"/"Boundary"` 配 chrys 英文 README；dsh tokens（L2473-2481）中文「加载模型/能力边界」配 dsh 中文 README（dsh README L7/L55 实读）——tokens 必须按 README 实文定制；
  4. verify_workflow.py L5093-5096：**每个** adapter README 还必须含 `"official approval"`/`"marketplace approval"`/`"universal/full runtime support"` 三个 boundary 短语（大小写不敏感）——§3.2 骨架未含、§4 登记清单未披露该要求（dsh README L65「本适配器不声明 official approval、marketplace approval、universal/full runtime support...」为先例）。
- 影响：实施后 check-mainstream-agent-loading 两处 FAIL。设计 §4.1 #5 自己声明「tokens 必须与 README 实文一致——机检」原则正确，但示例骨架与 tokens 草案矛盾。
- 修复：tokens 改 dsh 式中文（「加载模型」「能力边界」）或 README 标题英文化，二择一保持自洽；README 补一行 no-overclaim 声明含三短语。

**F-3｜候选 A 嵌套子进程继承全局 extension 加载——披露与论证缺口**
- 位置：设计 §1b.1 ADR-2 排除理由①（L179）将「extension 二次加载」仅列为候选 B 的排除理由；§1b.2（L229-243）未论证嵌套子进程的工具声明面。
- 事实链：候选 A spawn 的子 pi 进程同样读取全局 `~/.pi/agent/settings.json`——接线后（用户裁决① §5.2 追加 extensions 数组）嵌套子进程会加载本仓 extension 并注册两桥工具（model-only 注册即激活即声明，types.d.ts L481-484 实读）。`ask_user_question` 在嵌套 headless 内恒返 GOV_ASK_USER_HEADLESS（fail-fast，无害）；但 `dispatch_agent` 在 allowed_tools 缺省路径（「Defaults to pi default tools」）下会被声明给嵌套模型——存在递归派发面（嵌套 agent 再 spawn 嵌套）。
- 缓解已隐含存在但未论证：§1b.2 `allowed_tools` 参数 + cli.md L119-120（实读）「`--tools` ... allowlist of built-in, **extension**, or custom tools」——allowlist 不含的工具不声明给模型 → 显式给 allowlist 即可机器化排除两桥工具。设计推荐 Reviewer 用 `['read','grep','find','ls']` 已隐含此机制，但未把它升格为 dispatch_agent 的默认防护。
- 影响：默认路径下递归派发依赖嵌套模型自律（角色定义禁止事项不含「不再派发」），token/凭证消耗面未收口；文档未披露该继承语义。
- 修复（SHOULD）：dispatch_agent 嵌套 args 默认追加 `--exclude-tools ask_user_question,dispatch_agent`（cli.md L121-122 `-xt` 语义实读支持），或 allowed_tools 收紧为必填；§1b.2/README 能力边界补一句继承披露。

### P3（SUGGESTION）

**F-4｜措辞混用：`getLastAssistantText` vs `getFinalOutput`**
- 位置：§1b.1 官方锚点表「结果返回」行（L170）「`getLastAssistantText` 语义（倒序找最后 assistant 文本，L170-180）」。
- 实读：subagent/index.ts L170 函数名为 `getFinalOutput`；`getLastAssistantText` 是 SDK `AgentSession` 方法（候选 B 语境）。语义描述正确，函数名归属混淆。修复：改为「getFinalOutput（官方示例）/getLastAssistantText（SDK）同语义」。

**F-5｜§6.3 L2 探测「模型可声明工具」验证含糊**
- 位置：§6.3 extension 加载验证（L600）`pi -e ... --tools read` → 声称验证「extension 可加载」+「模型可声明工具」。
- 事实：`--tools read` allowlist 下治理两桥工具不在声明面（cli.md L119-120）——该探测实际只验证前者；治理工具的模型声明需省略 `--tools` 或将工具名列入 allowlist 的补充探测。修复：拆分两断言或调整探测命令。

**F-6｜「写面=0」主张建议机器化断言**
- 位置：§6 口径定义。trust 面（-na 一次性不落盘，security.md L73 仅 `/trust` 保存）与会话面（--no-session）已论证；非会话写面（web-search-cache 等）未显式排除。建议 E2E 断言加 agent-dir 前后 mtime/file-list diff，使「写面=0」成为机器可验证判据。

**F-7｜O-4' 升级门槛建议定稿入册**
- 位置：§7.2 O-4'（degraded→native 门槛）为开放项。用户裁决②的意图是「桥接可行即不降级」——若 E2E 通过后 capability 停留 degraded 将偏离裁决意图。建议实施时按 §6.4 验收顺序将 O-4' 建议 standard（矩阵 E2E passed + 一次 dispatch_agent 真派发 EVD 三步机录）经 Coordinator 确认入 decision-log，防止「永久 degraded」。

---

## 5. 蓝军挑战记录（Reviewer 独立挑战，补充设计 R-1~R-8 之外）

| # | 挑战 | 结果 |
|---|---|---|
| C1 | 若嵌套子进程加载了本仓 extension，两桥工具被二次注册怎么办？（设计未披露） | 识别为 F-3：ask_user headless fail-fast 无害；dispatch_agent 递归面经 `--tools`/`--exclude-tools` 机器排除（cli.md L119-122 实证），建议默认值收口 |
| C2 | README 机检 tokens 若与实文语言不一致？（设计自检声称覆盖） | 识别为 F-2：实读消费逻辑 L5090-5096 + 三短语要求——实施即 FAIL，修复路径闭合 |
| C3 | details 契约锚点若找不到实施者会不会误实现？ | 识别为 F-1：证据真实存在（extensions.md L135-136 + pi-agent-core L373-374），仅标注错文件 |
| C4 | RPC 模式 select 取消/超时的返回值语义是否如设计映射？ | 实证 rpc-extension-ui.md L188-194（select/input→undefined、confirm→false）+ L10/L33（timeout 自动消解）——设计 §1a.2/§1a.4 取消与超时行语义完全成立，无缺陷 |
| C5 | 若 pi 升级移除 virtual-modules 键？ | 设计 R-1 已覆盖（import type 擦除 + typebox 单依赖 + 版本锚点 + E2E 回归探针），无新增 |

---

## 6. SKILL 四维度映射结论

| SKILL 维度 | 结论 | 依据 |
|---|---|---|
| 1. 设计合理性 | PASS | 模块拆分单一职责（§2.1 五模块 ≤3 句）；接口最小化（两工具 schema 与本仓契约/模板逐字段对齐）；扩展空间（候选 B 备档、parallel/chain 留作扩展点且明确避免过度工程化） |
| 2. 技术债务评估 | PASS | 无刻意隐性债务——所有妥协（multi_select 降级、headless 错误返回、spawn 开销）显式声明；零 npm 依赖原则消除供应链面（§2.3，extensions.md L48 实证）；依赖最小化（typebox 单运行时依赖，virtual-modules L14-19 双别名兜底） |
| 3. 安全与合规 | PASS | 项目信任门语义实证（security.md L57/L61/L77-82）；临时文件 0600+tmpdir+finally 清理对齐官方（B8/B16）；真实环境防护完备（D5）；E2E 写面=0（附 F-6 补强） |
| 4. 可演进性 | PASS | 版本锚点（supported_runtime + R-1）；证伪清单留档（§1a.5/§1b.3 四条/三条同时成立才 FALSIFIED）；capability 升级路径（O-4' + §6.4）；全部 ADR 标注可逆性 |

---

## 7. 审查自检（事实依据红线）

- 本报告全部结论基于实读文件与行号（§3 抽验记录 55+ 处），无假设/推测/编造。
- 无法静态验证的面（runtime 行为）已在设计中由「未实测/推理」标注覆盖并核验闭环路径（D7）；本审查未将其作为 APPROVED 依据——批准的是**设计**（静态正确性），runtime 有效性由 §6 E2E 方案与 manifest `degraded`/`blocked` 时序口径承接（E2E 通过前不升 native/runtime-verified）。
- 审查过程零命令执行、零产品文件修改、零 `.governance/` 写入（唯一写入=本报告，位于 docs/reviews/ 设计资产区）。

---

*审查结论返回 Coordinator：APPROVED_WITH_NOTES · unresolved_blockers=0 · P0=0 · P1=1 · P2=2 · P3=4 · 复审建议=无需设计返工重审，F-1/F-2 随实施 PR MUST-fix、F-3 SHOULD-fix、F-4~F-7 建议采纳。*
