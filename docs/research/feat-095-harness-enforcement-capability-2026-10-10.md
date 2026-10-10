# FEAT-095 M-0 前置调研：harness 执法能力评估（插件能否真拦 spawn/工具调用/隔离工作区）

- **Task ID**: FEAT-095（REL-102 发布链 M-0 前置）
- **调研日期**: 2026-10-10
- **角色**: Analyst Agent（Coordinator 派发，expected-new 派发锁已取）
- **触发依据**: DEC-330 arch 联合裁定「检查必须影响执行权限否则 advisory 无效」；复盘报告 `docs/requirements/analysis-rpg-longhaul-capability-session-f3f46901-0.97.0.md` §3.6（L137-139：冷面集体停更且 63 次 verify 无一 FAIL / goal blocked 后 21 轮续跑无阻断）
- **执行包契约**: `.governance/execution-packets.json` packets.FEAT-095（L1413-1540）；assumption_record L1513「插件能否真拦 spawn/工具调用未证实；未证实面降级为协议级（SKILL 契约）+ CLI 级（verify_workflow 出口码）执法并如实披露——不假装有宿主级拦截能力」

---

## 0. 执行摘要（结论先行）

**核心结论：治理插件当前在全部六平台上都没有接线任何宿主级拦截；「插件能否真拦 spawn」的答案今天是「不能」。** 但调研发现 DSH 平台存在完整的一手文档证实的宿主级拦截原语（`tools/pre-execute` 瀑布 + 单调 guard + per-agent 工具掩码 + subagent `toolFilter`/`maxDepth` + fs/bash 沙箱），且治理插件在 DSH 上拥有运行于宿主进程内的自有 host row——宿主级执法在 DSH 上**架构可达但未实施未验证**。其余五平台（claude/codex/gemini/opencode/chrys）的会话内动态拦截 API 均**未证实**；其中 gemini/opencode 连 spawn 通道本身都未验证（sub_agent unsupported——「无可拦对象」）。

**对 FEAT-095 实施面的直接含义**（详见 §6）：六边界执法的默认落点是**协议级 + CLI 级**（与执行包假设一致，如实披露降级）；DSH 可作为唯一宿主级试点面（扩展自有 host row 注册 pre-execute guard，需新 DEC + PoC 故障注入验证）；仓库级 git hooks 是跨六平台唯一已交付的硬阻断（commit 边界），且有 `--no-verify` 文档化逃生门。

---

## 1. 调研问题与范围

### 1.1 需要回答的问题（来自任务行与执行包）

1. 六执法边界（①派发执行 ②派发审查 ③接受完成 ④合并 commit/组装 ⑤发布 tag/push ⑥goal 续跑）在六宿主平台（claude/codex/gemini/opencode/chrys/dsh）上，插件能否拦截/阻断该边界动作？
2. 拦截能力分级：宿主级（阻止工具调用或 spawn 本身）/ CLI 级（verify_workflow 出口码/写入拒绝在命令层强制）/ 协议级（仅 SKILL/注入面契约约束，无机器强制）？
3. 未证实面如实披露——不许假装有宿主级能力。

### 1.2 范围与非目标

- **覆盖**：六平台 adapter manifest 逐条实读；DSH checkout（`@deepseek-ai/dsh@0.1.5-rc.3`，`C:\Users\peter\AppData\Roaming\npm\node_modules\@deepseek-ai\dsh\`，**只读**）一手工具面考察；注入面样例（CLAUDE.md/AGENTS.md）；插件既有 CLI 执法点（verify_workflow.py 子命令面 + git hooks）；DEC-330。
- **非目标**：不做 FEAT-095 实施决策（归 Coordinator/用户）；不写 DSH checkout 或任何仓库外路径；不修改 .governance/ 治理记录；无用户真实环境操作（破坏性红线不适用）。
- **stage-research 维度声明**：本调研为技术能力调研（内部 harness 适配面），市场/用户维度不适用——按 skill 产出物标准以「技术维度发现 × 来源可验证 + 反面证据 + 关键不确定性标注」对齐；竞品矩阵形态由「六边界 × 六平台能力矩阵」（§5）承载。

### 1.3 分级定义（验收标准 ②口径）

| 级别 | 定义 | 判定特征 |
|---|---|---|
| **宿主级** | 宿主平台机制能阻止工具调用或 spawn 本身（动作被平台拒绝执行） | 平台在工具管线/权限层拒绝，模型无法通过「不调用检查器」绕过 |
| **CLI 级** | verify_workflow 出口码 / 写入器拒绝 / git hooks 在命令层强制 | 动作走 CLI/git 时被 exit 2/exit 1 拒绝；绕过面 = 不调用 CLI / `--no-verify` |
| **协议级** | 仅 SKILL/注入面契约约束（MUST 文本），无机器强制 | 违规只能被事后检查发现，不能在动作发生点阻止 |

---

## 2. 信息源清单（逐条可回溯）

| # | 信息源 | 类型 | 用途 |
|---|---|---|---|
| S1 | `adapters/claude/adapter-manifest.json` | 插件声明面 | claude 能力/通道/E2E 命令 |
| S2 | `adapters/codex/adapter-manifest.json` | 插件声明面 | codex 同上 |
| S3 | `adapters/gemini/adapter-manifest.json` | 插件声明面 | gemini 同上 |
| S4 | `adapters/opencode/adapter-manifest.json` | 插件声明面 | opencode 同上 |
| S5 | `adapters/chrys/adapter-manifest.json` | 插件声明面 | chrys 同上 |
| S6 | `adapters/dsh/adapter-manifest.json` | 插件声明面 | dsh 同上 |
| S7 | `C:\Users\peter\AppData\Roaming\npm\node_modules\@deepseek-ai\dsh\node_modules\@deepseek-ai\dsh-tools\README.md`（@deepseek-ai/dsh@0.1.5-rc.3 随包一手文档） | DSH 平台一手 | 工具管线/拦截原语 |
| S8 | 同 checkout `dsh-tool-subagent\README.md` | DSH 平台一手 | spawn 工具 config 面 |
| S9 | 同 checkout `dsh-subagent-spawn-in-process\README.md` | DSH 平台一手 | spawn 后端能力声明 |
| S10 | 同 checkout `dsh-tool-goal\README.md` | DSH 平台一手 | goal 工具权威规则 |
| S11 | 同 checkout `dsh-goal-round-driver\README.md` | DSH 平台一手 | goal 续跑驱动 |
| S12 | 同 checkout `dsh-fs-sandbox\README.md`、`dsh-bash-sandbox\README.md` | DSH 平台一手 | 文件效果围栏 |
| S13 | 同 checkout `dsh-permission-presets\README.md`、`dsh-user-approval\README.md` | DSH 平台一手 | 权限/审批面 |
| S14 | `adapters/dsh/host-contract.json` | 插件↔宿主契约 | 插件当前 DSH 组合行实况 |
| S15 | `skills/software-project-governance/infra/verify_workflow.py` | 插件 CLI 执法点 | 子命令出口码语义 |
| S16 | `skills/software-project-governance/infra/hooks/{pre-commit,commit-msg}` | 插件仓库级执法 | commit 边界硬阻断 |
| S17 | `CLAUDE.md` L22 / `AGENTS.md` L11 / `skills/software-project-governance/SKILL.md` L219/L229 | 注入面 | 协议级约束实际形态 |
| S18 | `.governance/decision-log.md` L197（DEC-330） | 治理记录 | 联合裁定原文 |
| S19 | `docs/requirements/analysis-rpg-longhaul-capability-session-f3f46901-0.97.0.md` §3.6（L132-139）、§4（L153-164）、§5（L168-179） | 复盘分析 | 失效实证与执法需求源 |
| S20 | `.governance/execution-packets.json` L1413-1540（FEAT-095 包）、L907-932（REL-102 M-0 前置） | 执行包 | 任务契约 |

> 编码说明：本报告读写全部显式 UTF-8（FIX-278）；pwsh 仅用于目录列举，未以裸 `Get-Content` 读任何治理文件。

---

## 3. 平台证据档案（六平台逐一）

### 3.1 dsh（DeepSeek Harness）——证据最深的一手面

**平台拦截原语（一手 README 证实，@0.1.5-rc.3）：**

1. **工具调用管线与守卫**（S7 `dsh-tools/README.md`）：
   - L85：「`ctx.tools.guard(guard)` registers a monotonic synchronous guard after the extensible `tools/pre-execute` waterfall: a returned reason denies the call, and no later listener can turn that denial back into permission. The pipeline's events give plugins more control — `tools/pre-execute` decides allow/deny/ask, `tools/execute` wraps dispatch for timeout or retry, `tools/post-execute` inspects or replaces the result, and `tools/result` observes the frozen final outcome.」
   - L103（执行管线固定次序）：「Every call runs a fixed pipeline: `tools/pre-execute` (extensible allow/deny/ask) → registered monotonic guards → `tools/execute` (around-dispatch wrappers) → `tools/post-execute` (inspect/replace, attach context) → definition-owned `finalizeContent` → the observe-only `tools/result` event.」
   - L81：「`ctx.tools.restrict(filter)` applies an allow or deny mask to the global tools one agent inherits; masks intersect, scoped registrations stay visible, and the restriction lifts when disposed.」
   - L224（限制）：「`tools/pre-execute` deliberately cannot rewrite `exec.arguments`」——可拒绝不可改写。
2. **spawn 侧限制原语**（S8 `dsh-tool-subagent/README.md`）：
   - L52-53（config 表）：「`toolFilter` | — | Per-child global-tool restriction; requires the `toolFilter` capability」「`maxDepth` | `3` | Absolute delegation-depth cap (`0` forbids delegation)」
   - L63：「each attempted start checks the calling agent's current depth and rejects with an errored result」——深度帽是执行时拒绝（宿主级）。
   - L214（关键限制）：「Non-routing child policy is fixed per instance — another persona, tool filter, or depth cap requires another distinctly named tool.」——**每实例静态，非按调用动态**。
   - S9 `dsh-subagent-spawn-in-process/README.md` L83：「The backend advertises all five start-time capabilities, including `agentOptions`」；L79：创建窗口内「applies persona, tool filter, and structured output」；L109：「a tool filter removes named global tools from its schemas, executable lookup, and PTC mode SDK bindings」——in-process spawn 后端确实支持 toolFilter（宿主级子代理工具收窄）。
3. **文件效果围栏**（S12 `dsh-fs-sandbox/README.md`）：
   - L12：「In `read-only`, it rejects every mutation; in `workspace-write`, it permits targets only inside the session workspace or a platform temporary root; in `danger-full-access`, it does not restrict mutations.」
   - L50：拒绝以 `FS_SANDBOX_DENIED` 结构化错误呈现，模型可见 `[sandbox: file access denied under <mode> mode]`。
   - L123（诚实边界）：「A policy fence, not a kernel boundary」。
   - `dsh-bash-sandbox/README.md` L12/L60：bash 侧同策略（「If no runner can enforce a confined mode, the command fails with `SANDBOX_UNAVAILABLE` rather than running unconfined」——fail-closed）；L174：「`danger-full-access` deliberately bypasses `ctx.sandbox`」。
4. **审批/权限面**（S13）：
   - `dsh-user-approval/README.md` L12：「The `ask` policy sends each request to the deployment's human or machine answerers; `never` rejects it without prompting. Missing or failed answerers return `unavailable`, so the action fails closed」。
   - `dsh-permission-presets/README.md` L38-44：预设表把 sandbox 模式与 approval 策略捆绑（`workspace-write`+`ask` / `danger-full-access`+`never`）；L132（限制）：「Only two mechanism knobs are bundled」。
5. **goal 续跑面**（S10/S11）：
   - `dsh-tool-goal/README.md` L55：「`create`, `edit`, `pause`, and `resume` additionally require a direct human message in a runtime-root agent's current turn — a subagent or a non-human producer cannot create or edit goals」「a blocked call is mechanically rejected until the configured number of consecutive rounds has passed」；L71-72：「Authority at execution… Host attestation of human input」——goal 变更的权威检查是执行时宿主级强制。
   - L149-150（限制）：「Semantic intent remains model judgment」「Same-condition blocking remains model judgment — the runtime enforces distinct admitted-round count, not semantic equivalence of obstacles」。
   - `dsh-goal-round-driver/README.md` L53：「completion, pause, and blocking suppress continuation… at the cap it records a blocker with the stable code `round-limit`」；L57：「after session resume or fork an active goal stays disarmed until an explicit human-authorized resume — the driver never revives work on its own」；L12：「The driver has no configuration」——**驱动无配置、无外部策略钩子**（治理态门不存在）。

**插件当前在 DSH 上的实装面（S14 `adapters/dsh/host-contract.json`——「我们改了什么」的事实）：**

- `host.rows` 中 `tool-subagent` 行 config_keys = `["provider","toolName","backgroundMode"]`（L478-482）、`tool-subagent-fork` 同（L501-505）——**未声明 toolFilter、未覆写 maxDepth**（工具支持 ≠ 组合接线）。
- 组合行全集（persona/agent-instructions/tool-bash|pwsh/tool-fs/tool-fs-search/tool-jobs/skill-filesystem/tool-skill/tool-goal/planning/compaction/delegation 组/ask-user/todo/web）中**没有任何 `tools/pre-execute` 策略行、guard 行、sandbox-policy/fs-sandbox/user-approval 行**——拦截原语一行都没接线。
- `own.host_row`（L763-775）：`"warn_only": true`、`"apply_never_throws": true`、`"runtime_dependencies": []`——插件自有宿主行（lib/index.js，运行于宿主进程内）当前只做 ensurePreset 渲染，**不注册任何工具守卫**。
- 注入模型（S6 `adapters/dsh/adapter-manifest.json` L36）：「cordis.patch.yml inserts exactly one host row (this package's own — DEC-187 forbids touching any other row)」——宿主级扩展的唯一合法通道是**自有行内**扩展。

**本会话实测佐证（部署策略 ≠ 平台能力）**：本调研所在 dsh 会话 runtime context 显示「Current DSH file policy: danger-full-access」「Approval prompts are disabled」——即沙箱/审批执法面在本部署未启用。这证明 FEAT-095 若依赖宿主级面，**必须把「部署策略变量」纳入设计**（宿主有原语 ≠ 用户会话开了围栏）。

### 3.2 claude

- S1 `adapters/claude/adapter-manifest.json`：
  - L40-42：`sub_agent` **native**（「Claude Code supports Agent-style delegation used by the workflow's Agent Team routing」）；L44-46：`tool_calling` **native**。
  - L58-60：`git_hooks` native（「Workflow installs and validates pre-commit, commit-msg, and post-commit hooks」）。
  - L111（E2E 命令）：`claude -p "..." --permission-mode default --allowedTools Read --output-format text`——**CLI 启动旗标层证实**：claude CLI 支持 `--permission-mode` 与 `--allowedTools`（进程级工具面收窄）。
- **未证实**：会话内 Agent/Task 工具是否支持 per-subagent 工具限制或调用拦截 API——manifest 与本调研一手面均无证据（见 §5 未证实清单 U2）。
- 现状判定：spawn 边界 = 协议级（CLAUDE.md L22 铁律「spawn 前查 .governance/agent-locks.json 并写锁」为纯文本 MUST）+ CLI 级（agent-locks-acquire exit 2，见 §4.1）；commit 边界 = 仓库级 hooks；CLI 旗标（--allowedTools）是**会话启动时一次性静态收窄**，插件在会话内不可动态操控。

### 3.3 codex

- S2 `adapters/codex/adapter-manifest.json`：
  - L42-45：`sub_agent` **degraded**（「Agent Team delegation remains host/tooling dependent and is not proven by the read-only E2E」）；L47-50：`tool_calling` **degraded**。
  - L117（E2E 命令）：`codex exec -C . -s read-only --ephemeral "..."`——**CLI 启动旗标层证实**：codex CLI 支持 `-s read-only` 沙箱模式（调用级文件写禁）。
  - L62-64：`git_hooks` native。
- 现状判定：spawn 边界 = 协议级 + CLI 级（spawn 通道本身未证实为 native——「可拦对象」的通道存在性先于拦截能力，未证实 U4）；`-s read-only` 旗标可用作**审查会话静态只读加固**（与 FEAT-096 只读审查快照呼应），但同样非插件动态操控面。

### 3.4 gemini

- S3 `adapters/gemini/adapter-manifest.json`：
  - L42-44：`sub_agent` **unsupported**（「Current Gemini CLI adapter has no verified sub-agent delegation path」）；degraded_mode L44：「Do not claim Producer-Reviewer separation from Gemini runtime alone; require external review evidence.」
  - L36-39：`ask_user_question` unsupported；L46-49：`tool_calling` degraded（CLI 配置依赖）；L61-63：`git_hooks` native。
- 现状判定：**边界①②在 gemini 上无可拦对象**（无已验证 spawn 通道）——执法问题退化为协议级禁令「不得声称 Producer-Reviewer 分离」+ CLI 级外部验证（validate 通道 degraded_mode L95-97：验证命令须在 Gemini 会话外跑）。

### 3.5 opencode

- S4 `adapters/opencode/adapter-manifest.json`：
  - L42-44：`sub_agent` **unsupported**；L47-49：`tool_calling` degraded（「Real opencode target-cwd E2E passed for reading governance state, but no file-edit or command-tool governance E2E has been verified」；degraded_mode：「Use opencode for read/load validation only」）。
  - L62-64：`git_hooks` native。
- 现状判定：与 gemini 同构——无 spawn 通道可拦，只读验证定位；协议级 + CLI 级（外部跑）。

### 3.6 chrys

- S5 `adapters/chrys/adapter-manifest.json`：
  - L42-44：`sub_agent` **native**（「Chrys has native explore_agent, plan_agent, and general_agent sub-agent tools」）；L38-40：`ask_user_question` native；L46-48：`tool_calling` native（原生工具清单枚举 L77：read_file/write_file/edit_file/grep/glob/pwsh/git_bash/convert_document/sleep）。
  - L62-64：`git_hooks` native。
- **未证实**：Chrys 子代理工具是否支持 per-child 工具限制、平台是否提供工具调用拦截/权限钩子——manifest 枚举的原生工具清单中**没有**权限/拦截类工具（对照 dsh 的 pre-execute/guard/sandbox 原语），一手证据缺席（未证实 U3）。
- 现状判定：spawn 边界 = 协议级 + CLI 级；chrys 是六平台中 native 面第二强的（ask_user/sub_agent/tool_calling 全 native），但「强在通道、弱在拦截」——通道能力与拦截能力是两个正交面。

---

## 4. 既有 CLI/仓库级执法点盘点（跨平台共同底座）

### 4.1 verify_workflow.py 子命令出口码（S15，一手源码）

| 子命令 | 出口码语义 | 引用 |
|---|---|---|
| `agent-locks-acquire` | 「Exit 0 = written (WARNs may accompany on stderr); exit 2 = fail-closed refusal (nothing written)」——派发锁获取的写时校验（路径存在 + expected-new 豁免 + 同日 triage 交叉核） | L25542-25543（docstring）；argparse 注册 L27700-27728 |
| `review-record` | 「exits 2 on a fail-closed input error (the record was not written)」——审查结论唯一机录路径（review-{id}-R{n}.md + evidence 行） | L24074-24075；参数面 L27455-27485（--result 四态枚举 APPROVED/APPROVED_WITH_NOTES/NEEDS_CHANGE/BLOCKED） |
| `governance-write-guard` | 「Exit 0 = no FAIL face…; exit 1 = at least one FAIL face…; exit 2 = a fail-closed management-mode refusal」；BLOCK 姿态可按族激活（`--activate-block`） | L25590-25594、L25576-25581 |
| `task-row-update` | 「Governed single write path for plan-tracker task-row state flips (FEAT-051): state CAS + short-term lock + operation receipts」 | L27734-27740 |
| `task-priority-analysis` | 「Fail-closed (exit 2, no write) on a malformed id」 | L27443-27444 |

**诚实限制（一手原文）**：write-guard 是 **write-AFTER** 的——L25578-25579：「the guard is write-AFTER and cannot stop the file from being modified」。即 CLI 级对「直接手写文件」只能事后 FAIL/披露，不能事前阻止。CLI 级执法的绕过面 = 不调用 CLI 直接写文件（RPG 实测后段 ~45 子代理完全绕开锁与账本即此形态，S19 §3.4 意涵）。

### 4.2 git hooks（S16，仓库级——六平台通吃的唯一已交付硬阻断）

- `pre-commit` L3-5：「Runs BEFORE every git commit. **BLOCKS commits** that don't meet governance criteria… Design assumption: agent WILL NOT follow rules voluntarily. System MUST enforce.」
  - Step 6（L261-294）：CLAUDE.md 直改纪律违规 → `exit 1`（BLOCKING，L293）。
  - Step 7（L297-346）：产品代码无 APPROVED 审查证据 → `exit 1`（L342，M7.4 BLOCKED）——**生产者-审查者分离的系统级执法**。
  - 文档化逃生门：`git commit --no-verify`（L285/L339 原文「Emergency bypass」）。
- `commit-msg`：多面 BLOCK（L253-262 无任务 ID / L274-284 任务不在 plan-tracker / L336-359 目标对齐 / L376-395 用户影响 / L400-449 事实依据 / L453-493 破坏性变更迁移 / L501-537 产品代码审查证据——各处 `exit 1`）。
- **缺口**：hooks 目录（`skills/software-project-governance/infra/hooks/`）只有 `prepare-commit-msg`/`pre-commit`/`commit-msg`/`post-commit` 四件——**没有 pre-push hook**；边界⑤（tag/push）在仓库级无看护（见 §5 矩阵与 §6 建议）。
- 六平台 adapter manifest 全部声明 `git_hooks` native（S1 L58-60 / S2 L62-64 / S3 L61-63 / S4 L62-64 / S5 L62-64 / S6 L61-63）——hooks 是仓库属性，不依赖宿主会话能力，是唯一的跨平台一致执法层。

### 4.3 协议级约束的实际形态（S17，注入面样例）

- `CLAUDE.md` L22：「**铁律**（违反 = 流程违规）：不直接修改产品代码；任务经 Agent 工具 spawn 角色 agent；Developer 不自审、Reviewer 不改码；…spawn 前查 `.governance/agent-locks.json` 并写锁，完成后释放。」——spawn 前置锁检查的现行载体是**纯文本 MUST**。
- `AGENTS.md` L11：「`resolved_root_ok == false` → MUST STOP」（fail-closed 协议形态）。
- `SKILL.md` L219/L229：复审必达（「`NEEDS_CHANGE` 且 round<3 → MUST 立即复审，不得跳过」）——协议级，违规只能事后 check 发现。
- 协议级特征：零机器强制力，依赖模型遵从；RPG 实测（S19 §3.5 L128）「复审必达在第 2 天静默失效」证明协议级在长程压力下衰减。

---

## 5. 六边界 × 六平台能力矩阵（验收标准 ②③④）

> 格式：`宿主级=…｜CLI 级=…｜协议级=…`；「现状」列给出该边界的**当前实际生效级别**（= 六平台交集口径 + 备注）。矩阵按「插件今天能拦什么」评估，不是「平台理论上有什么」（平台原语与插件接线的差距在 §3 已逐条分开）。

| 边界 | claude | codex | gemini | opencode | chrys | dsh | 现状（实际生效） |
|---|---|---|---|---|---|---|---|
| **① 派发执行（spawn 执行类子代理）** | 宿主级=未证实（会话内 Agent 工具拦截 API 无证据；CLI 旗标 `--allowedTools` 仅启动时静态）｜CLI=agent-locks-acquire exit 2｜协议=铁律文本 | 宿主级=未证实（sub_agent 通道本身 degraded）｜CLI/协议同左 | 宿主级=无可拦对象（sub_agent unsupported）｜CLI=外部验证｜协议=禁称分离 | 同 gemini | 宿主级=未证实（原生 explore/plan/general_agent 无工具限制参数证据）｜CLI/协议同 claude | 宿主级=原语存在未接线（pre-execute guard 可动态拒 subagent 调用；toolFilter/maxDepth 每实例静态）｜CLI=agent-locks-acquire exit 2｜协议=铁律文本 | **协议级+CLI 级**（全平台）；CLI 级可被「不调用」绕过（RPG 45 子代理绕锁实证） |
| **② 派发审查（spawn Reviewer）** | 同①（通道 native 但拦截未证实） | 同① | 无通道——审查须外部证据（协议禁令） | 无通道（同左） | 同① | 同①（guard 可按「修订错配」动态拒 spawn——FEAT-095 核心用例的唯一宿主级落点） | **协议级+CLI 级**；gemini/opencode 降为纯协议级+外部证据 |
| **③ 接受完成（任务收口/状态翻转）** | 宿主级=无对应原语｜CLI=task-row-update CAS 拒绝 + review-record exit 2 + write-guard 事后 FAIL｜协议=完成必推荐等 MUST | 同左 | 同左 | 同左 | 同左 | 同左（write-guard BLOCK 姿态可激活） | **CLI 级**（写入器拒绝是真实门）；「接受结论」动作本身无宿主拦截点 |
| **④ 合并（commit/组装）** | 仓库级=pre-commit Step6/7 + commit-msg 1-14 面 exit 1 BLOCK（git_hooks native）｜逃生门=--no-verify | 同左 | 同左 | 同左 | 同左 | 同左 | **仓库级（最强）**；注意契约「commit 前不设卡（WIP checkpoint 必须放行）」——现有审查证据硬门与 WIP 放行的对齐归实施面裁定 |
| **⑤ 发布（tag/push）** | 宿主级=无｜CLI=check-release 出口码（M-2 门禁消费）｜协议=发布链链序 MUST；**无 pre-push hook** | 同左 | 同左 | 同左 | 同左 | 同左 | **CLI 级+协议级**；tag/push 是六边界中机器看护最薄的一环 |
| **⑥ goal 续跑** | 宿主级=claude 侧 goal 机制非本插件面（未证实）｜协议=FEAT-097 桥接设计 | 同左 | 同左 | 同左 | 同左 | 宿主级=**平台自有语义**（round cap/blocked 3 轮机械门槛/resume 需人/驱动无配置无外部钩子——S10/S11）｜治理态门=无 | **协议级+平台自有机械约束**；「blocked 后 21 轮续跑」= 模型不报 blocked 则 host 不拦的实证（S19 L139 + S10 L150「Same-condition blocking remains model judgment」） |

**矩阵读法要点**：

1. **宿主级一列全部为「未证实」或「原语存在未接线」**——这是本调研最重要的单行结论：没有任何边界的宿主级拦截今天是插件可用的。
2. dsh 列是唯一「原语存在」的平台，且覆盖①②（guard 拒 spawn 调用）、③（guard 拒 fs 写 .governance 非授权路径——须与 fs-sandbox 模式联动）、⑥（guard 拒 update_goal 非授权动作）三个边界的动态拦截通道；④⑤不在工具管线内（git 是外部进程），dsh 上仍是仓库级/CLI 级。
3. gemini/opencode 的「无可拦对象」不是优势——它意味着这两平台上的工作流本身就是降级形态（无 Agent Team），执法矩阵对它们退化为「协议级禁令 + 外部 CLI 验证」。

---

## 6. 关键发现（每条带来源）

1. **【发现1｜插件零接线】治理插件在六平台上均未接线任何宿主级拦截原语。** dsh 侧证据：host-contract.json `host.rows` 无 pre-execute/guard/sandbox 行、tool-subagent 行无 toolFilter/maxDepth（S14 L478-505）、`own.host_row.warn_only=true`（L763-775）；其余平台 manifest 无任何拦截类能力声明（S1-S5）。含义：FEAT-095 若要宿主级，全部是**新建面**，不是「打开开关」。
2. **【发现2｜dsh 原语完备】DSH 平台的拦截原语族（pre-execute 瀑布/单调 guard/per-agent 掩码/subagent toolFilter+maxDepth/fs+bash 沙箱/审批 fail-closed）全部有一手文档证实**（S7 L85/L103/L81、S8 L52-53/L63、S9 L83、S12、S13）。含义：dsh 是唯一可以做宿主级 PoC 的平台；且插件自有 host row（lib/index.js）运行在宿主进程内（S14 L763-765 `entry: lib/index.js`），注册 guard 的通道在 DEC-187「只动自有行」约束内**架构可达**。
3. **【发现3｜静态≠动态】dsh 的 subagent toolFilter/maxDepth 是「每实例静态」**（S8 L214「Non-routing child policy is fixed per instance」）——能满足「Reviewer 子代理天然无写工具」这类**角色面收窄**，不能满足 FEAT-095 的「修订错配的这次派单被动态拒绝」这类**治理态判定**。动态判定只能走 pre-execute guard（每调用评估）。
4. **【发现4｜反面证据——CLI 级可绕过】RPG 实测证明协议级+CLI 级组合在长程压力下衰减**：后段 ~45 子代理完全绕开锁与账本（S19 §FEAT-096 任务行 L1548 引 §3.4）；「复审必达」第 2 天静默失效（S19 L128）；goal blocked 后 21 轮续跑无阻断（S19 L139）。这正是 DEC-330 根因①「无执法闭环」的实证（S18 L197「治理状态不构成执行权限的权威来源」）。**反面证据同时界定了本调研的价值边界：只要执法停留在 CLI 级，RPG 形态失效就会复发。**
5. **【发现5｜goal 面的机械 floor 与语义缺口】dsh goal 面有真实机械强制**（blocked 3 轮门槛、round cap、resume 需直接人类消息、subagent 不能 create/edit goal——S10 L55/L71-72；驱动侧 complete/pause/block 抑制续跑、round-limit 阻断码——S11 L53），**但没有治理态门**（驱动无配置无钩子 S11 L12/L45；same-condition 语义是模型判断 S10 L150）。含义：边界⑥的插件侧执法只能靠（a）guard 拦 update_goal（dsh 宿主级可达）或（b）FEAT-097 桥接把治理授权映射进 goal 状态机（协议级+工具调用约定）。
6. **【发现6｜发布边界最薄】tag/push 无任何 hook 看护**（hooks 目录四件套无 pre-push，S16 目录清单）；check-release 是 CLI 门 + M-2 链序是协议消费。六边界中⑤的机器强制最弱，而它恰是副作用最大的动作（不可逆远端操作）。
7. **【发现7｜部署策略变量】宿主能力 ≠ 部署启用**：本 dsh 会话实测 danger-full-access + approval disabled（runtime context）。FEAT-095 的宿主级设计必须处理「用户关掉了围栏」的场景（guard 是插件自注册的所以不受此影响——这正是 guard 路线优于依赖 sandbox-policy 路线的关键差异）。

---

## 7. 未证实清单（每项给验证方法——不许装作已证实）

| # | 未证实面 | 现状表述边界 | 验证方法 |
|---|---|---|---|
| U1 | dsh pre-execute guard 由治理插件自有 host row 注册的**实际可行性**（含性能：同步 guard 内读治理态的方式） | 文档证实原语存在（S7）；「第三方包注册 guard」仅有架构推断（row 在宿主进程内运行是事实 S14，但从未有包这么用过）——**标：未证实（架构可达）** | 扩展 lib/index.js 注册最小 guard 的 PoC + 故障注入（违规 spawn 应被拒）+ 每调用开销实测；dsh 真实平面跑 dsh-doctor 全阶段 |
| U2 | Claude Code 会话内 Agent/Task 工具的 per-subagent 工具限制/拦截参数 | manifest 只证实 CLI 旗标 `--allowedTools`/`--permission-mode`（S1 L111）；会话内 API 无证据——**标：未证实** | 查 Claude Code 官方 Agent tool schema（subagent 配置面）+ 实机 spawn 传 allowed_tools 参数实验 |
| U3 | Chrys 子代理的工具限制参数/平台拦截钩子 | manifest 证实三种子代理工具 native（S5 L42-44）但原生工具清单无权限类工具（L77）——**标：未证实（倾向无）** | 查 Chrys 文档 explore_agent/plan_agent/general_agent 参数面；实机探测 |
| U4 | codex 会话内 spawn 通道的存在与形态 | manifest sub_agent degraded（S2 L42-45）——**标：未证实（通道本身）** | codex 交互会话工具面探测（是否有 Agent/Task 类工具及其参数） |
| U5 | gemini/opencode「无 spawn 通道」的持续性 | manifest unsupported 是时点声明（S3 L42-44 / S4 L42-44）；宿主升级可能新增——**按 EXP-03 漂移降级纪律处理** | 每版本 agent-runtime-e2e 复跑（既有机制） |
| U6 | claude/codex CLI 旗标在插件工作流中的可用性（如用 `claude -p --allowedTools Read` 起只读审查会话） | 旗标存在已证实（S1 L111 / S2 L117）；但插件从会话内派生带旗标子进程的路径未验证——**标：未证实（组合面）** | 在 claude/codex 宿主会话内以 shell 起带旗标 headless 子会话的 PoC |
| U7 | dsh guard 拒绝后对模型行为的实际效果（拒了之后模型会不会换通道绕） | 单调 guard 语义已证实不可翻案（S7 L85）；但模型级绕行（如改用 pwsh 直接跑 git）需边界联动（guard 面 + bash/fs 面 + git hooks 面全堵才算闭环）——**标：未证实（对抗面）** | 故障注入测试设计为多通道逃逸对抗（DEC-330 发布验证底线六项的扩充） |

**降级声明（按执行包 L1513 原文执行）**：U1-U7 全部未证实 ⇒ 除「dsh 宿主级试点」作为**建议选项**外，FEAT-095 的六边界执法面在本调研时点**必须按协议级 + CLI 级落地并如实披露**，不得在任何文档/manifest 中声称宿主级拦截能力。

---

## 8. FEAT-095 实施面分层执法建议（供 Coordinator/用户决策，非本报告越权裁定）

### 8.1 可机器强制（CLI/仓库级——六平台一致，立即可做）

| 边界 | 建议执法形态 | 既有底座 |
|---|---|---|
| ③ 接受完成 | 硬阻断四类（修订错配/未授权写入/重复身份/阻塞复审未闭合）落在**写入器出口码**：task-row-update CAS 拒绝错配修订、review-record CONFLICT 判定（与 FEAT-094 快照绑定联动）、write-guard BLOCK 姿态按族激活 | S15 §4.1 全部子命令已存在，缺的是「执法判定消费检查输出」的接线（这正是 FEAT-095 本体） |
| ④ 合并 | 沿用仓库级 hooks 硬门；**实施时必须对齐契约「commit 前不设卡」**——建议 hook 侧区分 WIP checkpoint（放行语义）与组装 commit（硬门），当前 Step 7 审查证据门与 WIP 放行的区分逻辑需在实施票内显式裁定 | S16 pre-commit Step7 / commit-msg Step14 |
| ⑤ 发布 | 补 **pre-push hook**（含 tag 推送看护）——调研发现的唯一零成本补强点；check-release 出口码保持 M-2 门禁消费 | hooks 目录缺口（§4.2） |
| ①②⑥ | CLI 级前置检查（agent-locks-acquire/审查债预算检查命令）+ 协议级 MUST；**披露**：不调用即绕过（RPG 实证） | §4.1/§4.3 |

### 8.2 dsh 宿主级试点（建议作为独立实施批，先 DEC 后 PoC）

- **路径**：扩展自有 host row（lib/index.js）注册 `tools/pre-execute` 策略/`ctx.tools.guard`——覆盖 `subagent`/`subagent_fork` 调用（边界①②：按治理态动态拒修订错配派单）、`update_goal`（边界⑥：拒未授权续跑动作）、fs 写工具对 `.governance/` 非授权路径（边界③辅助）。
- **前置裁定**：①改 `own.host_row.warn_only=true` 契约需新 DEC（host-contract 是 parity 契约，S14 `own._note`）；②guard 读治理态的性能设计（不能每工具调用起 python 进程——建议 watch/缓存治理面文件，脏时重算审查债预算）；③fail-closed 语义：guard 自身异常时保守阻断并披露（执行包 security 阈值 L1464 原文）。
- **验证**：U1 PoC + U7 对抗性故障注入（多通道逃逸）+ `dsh-doctor` 全阶段。
- **不建议**依赖 sandbox-policy/user-approval 行做执法（部署策略可关——发现7；guard 是插件自注册，不受用户权限预设影响）。

### 8.3 其余五平台（如实降级披露）

- claude/codex：可选加固 = U6 PoC（headless 只读审查子会话：`--allowedTools Read` / `-s read-only`），服务 FEAT-096 只读审查快照；动态拦截未证实前不声明宿主级。
- gemini/opencode：维持「无 Agent Team 降级 + 外部审查证据」协议形态（manifest degraded_mode 原文即此要求）。
- chrys：U3 探明前按协议级+CLI 级。
- 六平台共同：分层执法表（策略表）与执行器分离（执行包 maintainability 阈值 L1485「执法策略表与执行器分离」）——建议策略表按平台列声明级别，manifest 的 `runtime_capabilities` 不新增「enforcement」能力键除非 U1 落地证实。

### 8.4 与 DEC-330 发布验证底线的对齐

DEC-330（S18 L197）发布验证六项中与本调研直接相关：「blocked 后无未授权执行」「无关任务不被全局冻结」「错修订审查拒收」「报告机录冲突拒收」——前两项依赖边界⑥/Scoped 语义（8.2 guard 设计须内嵌 scoped 白名单：修复/复审/取证通道不冻），后两项 CLI 级可闭环（8.1 已列）。「代理死亡可恢复」「R2 不漏建」归 FEAT-094 面，本报告不展开。

---

## 9. 自检（硬门槛对照）

| 门槛 | 状态 |
|---|---|
| 报告 Markdown/UTF-8/路径精确匹配 `docs/research/feat-095-harness-enforcement-capability-2026-10-10.md` | ✅（write 工具显式 UTF-8） |
| 六边界 × 六平台逐一评估（含三级别判定） | ✅ §5 矩阵 + §3 逐平台档案 |
| 信息源逐条引用（路径+行号/原文摘录） | ✅ §2 清单 + 正文全部带 S#/L# 引用 |
| 未证实面如实披露 + 验证方法 | ✅ §7 U1-U7；降级声明按执行包原文 |
| 分层执法建议（硬阻断哪些可机器强制/哪些必须降级） | ✅ §8（标注「供决策，非越权裁定」） |
| 唯一写面（不修改其他文件/.governance/DSH checkout） | ✅ 本报告为唯一落盘产物 |
| 分析基于事实、无编造 | ✅ 每条结论可回溯 §2 信息源；平台原语与插件接线严格分开表述 |

**报告边界声明**：本报告为 M-0 前置调研产出，FEAT-095 实施面决策（尤其 8.2 dsh 宿主级试点是否立项、host_row 契约变更 DEC）归 Coordinator/用户；报告中的「架构可达」「建议」均为调研推断或提案，不是已验证能力。
