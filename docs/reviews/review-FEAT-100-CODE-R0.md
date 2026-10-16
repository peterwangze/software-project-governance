# FEAT-100-CODE-R0 代码审查报告 — pi adapter 实施（extension 双桥 + 三件套 + 九处登记）

- **Task ID**: FEAT-100（审查对象=已 staged 未 commit 的实施改动，R0 轮）
- **审查人**: Code Reviewer Agent（角色定义 `agents/code-reviewer.md`；执行规范 `skills/code-review/SKILL.md`）
- **审查基础**: 权威设计 `docs/requirements/pi-adapter-design-0.99.0.md`（staged 版，655 行）+ 设计审查 `docs/reviews/review-FEAT-100-DESIGN-R0.md`（F-1/F-2 MUST-fix、F-3 SHOULD-fix）+ 事实源 `docs/research/pi-adapter-integration-research-0.98.0.md`（untracked，只读参照）
- **日期**: 2026-10-16 · **轮次**: R0（首轮，无前轮引用）
- **审查方式**: 全程只读静态审查 + 白名单验证命令抽验（唯一写入=本报告；未 git add/restore/reset/commit，staged 状态原样保持；pi 包目录只读；未运行模型 API）

---

## 结论

> **REVIEW RESULT: APPROVED_WITH_NOTES**
>
> unresolved_blockers=0
>
> 实施与设计 §2/§3/§4 高保真对齐：extension 五模块逐行审查未发现逻辑/安全缺陷，ctx.ui 与 ToolDefinition/AgentToolResult 类型签名经 pi 包 dist 实读逐字对齐，嵌套 spawn 编排与官方 subagent 参考实现逐段同构（含 R-6 Windows 绝对路径分支的正确插入位）；设计审查 F-1/F-2/F-3 全部闭环且有对应机检通过证据；verify_workflow.py 九处登记齐备、无意外逻辑变更（+74/-8 全部归因登记面）；全部抽验机检 PASS（check-agent-adapters 7/7、readiness-matrix、mainstream-agent-loading、cross-references、injection-budget、launch.py）。回归声明 41F/4911P vs 基线 42F/4909P 的差分解释（新增 1 测试 + ratchet rider 修复 1 预存红）经 rider 注释互证自洽。P2×2（被审面申报 18 vs 实际 staged 20 的申报完整性缺口——其中 e2e 镜像手改经查为投影同步提前手动执行、内容逐字节一致；FEAT-100 自身 research 文档 ragged table row 引起 41F 之一失败）+ P3×5，全部不阻塞合并；F-C2 建议 FEAT-100 验收（E2E gate）前闭环。

**阻塞发现清单**: 无（P0=0，P1=0）。
**非阻塞 notes**: 7 条（P2×2、P3×5）。

---

## 1. 硬门槛裁决（角色定义 5 项）

| 门槛项 | 阈值 | 判定 | 证据 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **PASS** | 本报告发现清单 P0=0（§4） |
| 5 维度全覆盖 | = 100% | **PASS** | §2 正确性/安全性/可维护性/性能/测试覆盖逐一有结论 |
| 每条发现标注级别 | = 100% | **PASS** | §4 全部 7 条发现带 P2/P3 标签 |
| 设计一致性检查 | 已完成 | **PASS** | §3.1（TS 五文件 vs 设计 §1a/§1b/§2 骨架与映射表）、§3.2（manifest vs 设计 §3.1）、§3.3（九处登记 vs 设计 §4.1）；两处实施对设计草案的偏差均经机检约束裁定为合理修正（§4 F-C3、设计常量名笔误见 F-C5） |
| AI 代码专项 5 项检查 | 全部完成 | **PASS** | §2 专项段：mock 残留=0、硬编码返回值=0、幻觉 API=0（全部签名实读对齐）、未实现 TODO=0、过度实现=0 |

---

## 2. 审查维度逐项结论（SKILL 5 维度 + AI 专项）

### D1 正确性 —— PASS

- **ask-user.ts（274 行逐行）**：schema 逐字段实现设计 §1a.4 契约（questions[]/id/question/header?/options?{label,description?}/multi_select?，description 文本与设计逐字一致，L24-57）；`dialogTitle` header 拼接（L87）、`renderOptions` `"{i+1}. {label} — {description}"` + 80 字符截断（L95-106）、序号正则回解析（L109-116）与设计 §1a.2 映射表逐行对应；multi_select 降级为逐项 confirm 序列、全否=取消（L193-202）实现正确，且注释诚实披露 pi confirm 无法区分 No 与 dismiss（L180-182）；headless 守卫 `if (!ctx.hasUI)` → `GOV_ASK_USER_HEADLESS` 结构化错误（L250、L123-139，isError:true + 待问 id 列表）；取消/超时经 UserCancelled 异常统一转为非 error 结构化结果（L257-269），对齐设计「取消为显式结果」语义；每题前 `signal?.throwIfAborted()`（L254）。边界：空 questions/空 options 数组/缺 label 均有 fail-closed 校验（L142-163）。
- **dispatch-agent.ts（289 行逐行）**：F-3 修复到位——L253 `args.push("--exclude-tools", "ask_user_question,dispatch_agent")` 为**无条件追加**（不在任何 if 分支内），与工具 description（L132-133）和 README 披露（L56）三面一致；嵌套参数面 `["--mode","json","-p","--no-session"]` + `--append-system-prompt|--system-prompt` 临时文件 + `--model provider/id` 继承 + `--thinking` + `--tools` join（L238-254）与官方 subagent L300-307 逐项同构；task_skill_path 请求但解析失败=dispatch 错误非静默跳过（L146-163，fail-closed 注释）；角色不可解析→官方「Unknown role … Available roles」错误风格（L108-119 + paths.ts listRoleDefinitions）；失败判定 isFailedRun→errorMessage/stderr/finalOutput 三级回退（L269-280）；onUpdate 流式回传（L260-265）对齐官方 L324-331。
- **nested-runner.ts（289 行逐行）**：JSONL 行缓冲解析+畸形行静默容错（L210-217 try/catch + L255-260 split/pop + L267 close 时残尾处理）；usage 聚合（turns/input/output/cacheRead/cacheWrite/cost 累加、model 首值、stopReason/errorMessage 透传，L219-243）与官方 L362-387 逐字同构；abort 路径 signal→SIGTERM→5s→SIGKILL（L277-287，spawn 前已 aborted 亦覆盖）；isFailedRun = exitCode≠0 ∨ stopReason∈{error,aborted} ∨ aborted（L82-89）——`code ?? 0` 的信号终止归 0 缺口由 aborted 布尔兜底，与官方 L403/L410-419 同款（见 F-C6）。并发：v1 单任务单进程，无共享状态并发面（设计 §1b.2 明确不引入 parallel/chain）。
- **paths.ts / index.ts（79+33 行逐行）**：pluginRoot 经 `import.meta.url` 自定位上溯 3 级（L20-24）；resolveRepoPath ~ 展开→绝对 verbatim→pluginRoot 优先→cwd 次之→双 miss null（L42-52）；index default factory + registerTool×2（L30-33）。依赖方向 `index → {ask-user, dispatch-agent} → {nested-runner, paths}` 单向无环（实读 import 语句验证：ask-user 零本地依赖；nested-runner/paths 仅 node: 内置）。
- **launch.py（53 行）**：纯只读打印（读 manifest→print，零写操作、无 --install），打印面覆盖设计 §3.3 清单（含 runtime_e2e 两子块 status/command/blocked_reason），chrys 先例同构。

### D2 安全性 —— PASS

- **路径输入面**：role_definition_path/task_skill_path 允许绝对路径与 ~（paths.ts L42-52）。**裁定：符合设计授权面**——设计 §1b.2 schema 描述即「Relative paths resolve against the governance plugin root or cwd」且未定义 jail 约束（任务审查清单第 1.4 项明示「按设计 §2 裁定，不自行加码」）。无权限提升：dispatch_agent 为 model-only 编排工具，调用者（Coordinator 模型）本身持有 read 类工具可读任意文件；文件内容仅注入嵌套子进程 system prompt，不外传。
- **命令注入**：spawn `shell:false`（nested-runner L250）；prompt 经 argv 单参数传递不经 shell；临时文件名 sanitize `/[^\w.-]+/g→"_"`（nested-runner L164、dispatch-agent L232 同款正则，官方 L241 先例）。
- **临时文件**：`os.tmpdir()` + mkdtemp 私有目录 + 0600 权限 + finally 清理（L159-186、dispatch-agent L283-286），不写 `~/.pi/`、不写仓库——设计「临时文件红线」逐条落实，官方 L239-247/L426-439 同款。
- **递归派发面（F-3）**：嵌套子进程继承全局 extension 接线被机器化阻断（`--exclude-tools` 无条件追加）；allowed_tools 显式收窄仍可用（L248-250 在 exclude 之前独立生效）。
- **敏感数据**：无硬编码密钥/token；usage/cost 仅聚合数值。嵌套子进程环境变量=父进程默认继承（spawn 未做 env 覆盖）——与官方示例一致；E2E 混合口径（--no-session + -na + --tools read）由矩阵条目机检断言（新增测试）承载。
- **凭据面**：本轮零模型 API 调用；E2E 矩阵条目尚未执行（blocked 声明诚实）。

### D3 可维护性 —— PASS

- 五模块各单一职责、模块头注释均 ≤4 句声明职责与证据锚点；函数长度均 <60 行（最长 execute ~150 行但为官方同构编排骨架，步骤注释 1-6 分段）；证据锚点注释（types.d.ts 行号/官方示例行号/review F 编号）全文件贯穿，可追溯性优于仓库均值。
- system_prompt_mode 用 typebox Union 替代设计骨架的 `Type.StringEnum`（pi-ai helper）并注释理由（保持运行时依赖面=仅 typebox，dispatch-agent L64-66）——正确的工程决策，语义等价（literal 联合）。
- 命名与结构对官方先例的映射显式（getFinalOutput 注释同时澄清设计审查 F-4 的两名一义，nested-runner L61-68）。

### D4 性能 —— PASS

- 逐题串行 dialog（executionMode:"sequential" + for-of）为交互正确性所需；JSONL 流式逐行解析 O(n)；无 N+1/不必要循环；单任务单进程避免并发放大；contextTokens 取最后值而非累加（与官方一致，语义正确）。

### D5 测试覆盖 —— PASS（静态面）

- 夹具六元→七元（test L2738）；pi 分支 capability 值与 policy 常量一致（tool_calling=native/browser=unsupported/degraded_capabilities 四项，L2650-2666）；matrix 夹具 pi 行 BLOCKED/DEGRADED（L3378）；matrix 测试断言更新为五平台含 pi；**新增 `test_agent_runtime_e2e_pi_entry_uses_mixed_scope_readonly_flags` 断言质量良好**——command[0]=="pi"、-p、探针文本 verbatim（`vw._agent_runtime_e2e_prompt("pi")`）、`--tools` 后随 "read" 的参数关联、--no-session、-na、validator 身份（`is`）断言，对「去掉任一混合口径旗标/换探针/换 validator」的回归均有 FAIL-on-buggy 价值。
- runtime 行为（jiti 加载/dialog 渲染/spawn）无单测——设计定位由 L2/L3 E2E 分层验收承接（manifest blocked 声明 + README E2E 节），静态面覆盖与设计口径一致，非缺口。

### AI 代码专项 5 项 —— 全部通过

| 项 | 结论 | 证据 |
|---|---|---|
| mock 残留 | 0 | 五 TS 文件无 mock/stub/fixture 字样 |
| 硬编码返回值 | 0 | 全部返回值由参数/IO 派生；唯一常量 DIALOG_TIMEOUT_MS=10min 有防挂起注释（ask-user L82-83） |
| 幻觉 API 调用 | 0 | ctx.ui.select/confirm/input、ExtensionUIDialogOptions、ToolDefinition 泛型（TParams,TDetails）、execute 五参签名、AgentToolResult{content,details,isError}、ctx.model/thinkingLevel/cwd/hasUI **全部经 pi 包 dist 实读逐字对齐**（types.d.ts L40-45/L72-79/L212-240/L269-281/L448-506/L501、pi-agent-core types.d.ts L370-392）；`.ts` 扩展相对导入与 `import.meta.url` 均有官方 examples 先例（doom-overlay/plan-mode/dynamic-resources 等 11 处） |
| 未实现 TODO | 0 | 无 TODO/FIXME/placeholder；设计骨架的注释级步骤（§1b.2 骨架 1-6）全部有实现体 |
| 过度实现 | 0 | 未实现 parallel/chain/timeout_ms（设计明确留作扩展点）；候选 B 未实现（备档）；pluginRootOverride 参数仅 1 处且服务于可测性 |

---

## 3. 任务审查清单逐项证据（8 项）

### 3.1 extension TS 逐行审查（清单 1）—— 见 §2 D1/D2；补充类型对照硬证据

- dialog 签名：pi types.d.ts L74 `select(title: string, options: string[], opts?): Promise<string | undefined>`、L76 `confirm(title, message, opts?): Promise<boolean>`、L78 `input(title, placeholder?, opts?)`——ask-user L198/L205/L211 调用与签名逐字对齐；`ExtensionUIDialogOptions = { signal?, timeout? }`（L40-45）与 `{ signal, timeout: DIALOG_TIMEOUT_MS }` 对齐。
- ToolDefinition（L448-506）：`ToolDefinition<TParams extends TSchema, TDetails, TState>`——`ToolDefinition<typeof GovAskUserParams, GovAskDetails>` 合法；execute L501 五参 `(toolCallId, params, signal, onUpdate, ctx): Promise<AgentToolResult<TDetails>>`——两工具实现签名一致；exposure/namespace/annotations/executionMode 字段存在且 model-only 默认激活（L481-484）。
- AgentToolResult（pi-agent-core dist/types.d.ts L370-392）：`{ content: (Text|Image)[], details: T, isError? }`——textResult/dispatchResult/headlessErrorResult 返回结构合法；L373-374 即设计审查 F-1 引用的类型层佐证（实读复核成立）。
- 官方 subagent 对照（examples/extensions/subagent/index.ts 实读 L240-419）：getPiInvocation 三分支（argv[1]→generic runtime→PATH "pi"）与实现 L132-151 逐字同构，实现在其间插入 R-6 绝对路径分支（`process.execPath + APPDATA/NPM_CONFIG_PREFIX 下 cli.js`，L92-125/L140-143）——设计 R-6 缓解措施的落实，插入位正确（PATH 回退之前）；writePromptToTempFile（mkdtemp+0600+sanitize 正则同款）、processLine/usage 聚合/`code ?? 0`/`if (!proc.killed) SIGKILL` 与官方逐字一致（L403/L414-416）。

### 3.2 adapter-manifest.json（清单 2）—— PASS

- 14 必需键齐备（adapter_id…launcher 逐键对照 L1610-1624 常量与六先例结构）；check-agent-adapters 实跑 **7/7 PASS** 为机检证明。
- exploration_channels.note L74 逐字含「生成≠咨询」（QUOTE_SYNC 七平台消费，check-cross-references 实跑 PASS）。
- runtime_capabilities 六键 ask_user_question/sub_agent=degraded（evidence 含 extension-bridged 语义 + 「runtime E2E verification pending → degraded until then」）+ tool_calling/git_hooks=native + browser=unsupported + mcp=degraded，与 ADAPTER_RUNTIME_CAPABILITY_POLICY["pi"]（verify diff 新增六键行）一致；workflow_closure 第七键 degraded + degraded_capabilities 四项（设计草案同款）；sub_agent evidence 已补 `--exclude-tools` F-3 事实。
- runtime_e2e 块：e2e_level/version_command/verified_on/evidence/target_cwd_e2e{blocked+blocked_reason+evidence}/agent_runtime_e2e{同}/full_e2e_verified=false——字段完整，blocked 子块均带 blocked_reason（L5405-5406 机检）。
- **support_status=runtime-verified + e2e_level=runtime-version-probe 偏离设计草案（designed/real-agent-target-cwd）的裁定**：机检 L6146-6158 只接受 `support_status ∈ {runtime-verified, not-supported-current-release}` 且 runtime-verified 时 e2e_level 必须 ∈ {runtime-version-probe, real-agent-target-cwd}——设计草案值 "designed" 会直接 FAIL；实施取唯一合规组合，诚实性由 e2e_level 取最低档枚举 + 两 blocked 子块 + full_e2e_verified=false + evidence pending 文本承载（另见 F-C3）。

### 3.3 verify_workflow.py 九处登记（清单 3）—— PASS（+74/-8 全部归因登记面）

逐处 diff 审查（行号=staged 后）：

| # | 登记点 | 证据 | 判定 |
|---|---|---|---|
| 1 | MAINSTREAM_AGENT_ADAPTERS | L1630 七平台元组追加 "pi"（chrys 保留——FEAT-101 未同期，符合设计 §4.1 时序注） | ✅ 纯追加 |
| 2 | 适配三件套文件登记 | L554-556（OPTIONAL_PROJECTION_FILES，chrys L550-553 之后插入 3 行；设计文档笔误写作 REQUIRED_FILES——见 F-C5，行号与结构对齐） | ✅ |
| 3 | 三件套 snippet 登记 | L681-698（PROJECTION_SNIPPETS pi 三块：README 4 token/manifest 4 token 含「生成≠咨询」/launch.py 4 token） | ✅ |
| 4 | RUNTIME_MATRIX_AGENT_IDS | L2387 追加 "pi" 于 dsh 后、research-only 段（cursor/copilot）不变 | ✅ |
| 5 | MAINSTREAM_AGENT_LOADING_ADAPTERS | L2506-2520 pi dict：display "Pi"、九 token 与 README 实文一致（英文 Load/Boundary 由双语标题满足——F-2 修复，check-mainstream-agent-loading 实跑 PASS） | ✅ |
| 6 | REQUIRED_DOCS + TIER1 | L2398 +adapters/pi/README.md；L2408 TIER1 +"Pi"（大写显示名，FEAT-101 教训落实） | ✅ |
| 7 | ADAPTER_RUNTIME_CAPABILITY_POLICY | L5508-5515 pi 六键行，与设计 §3.1 注记④草案逐键一致 | ✅ |
| 8 | QUOTE_SYNC_ADAPTER_MANIFESTS | L12133 七平台元组；注释与检查体文案 six→seven 三处同步（L12121-12130/L12168-12175/L22740），无逻辑变更 | ✅ |
| 9 | AGENT_RUNTIME_E2E_PLATFORMS + 命令矩阵 | L20144 五平台元组；L20228-20246 pi 条目 `pi -p <探针> --tools read --no-session -na`，validator 复用 `_validate_agent_runtime_e2e_passed`，注释块声明用户裁决③混合口径——与设计 §6.3 草案逐字段一致 | ✅ |

意外逻辑变更检查：diff 中除上述登记面与跟随性文案（six→seven）外**零逻辑变更**；消费面（check_agent_adapter_contract/check_runtime_readiness_matrix）未动，符合设计「自动覆盖」预判。

### 3.4 文档一致性（清单 4）—— PASS

- SKILL.md（主 + e2e 镜像，两文件 diff 逐字节相同、index hash 一致 df725bc..8232eb5）：平台表 +`| Pi | adapters/pi/ + adapters/pi/extension/ | — |`；「Pi 平台说明」段含加载模型/能力面/五row 工具映射表（AskUserQuestion→桥、Write/Edit/Bash→write/edit/bash|powershell、Agent spawn→dispatch_agent+F-3 披露、isolation worktree→串行化 MUST、/governance→prompts 模板命令 O-3'）+ 尾注——设计 §4.2 #10 要求逐项落实（dsh 先例同构）。
- 根 README：Tier 1 表 +Pi 行（zcode 行先例格式），验证列含 launch.py + `agent-runtime-e2e --agent pi --timeout 90`，边界列 no-overclaim 措辞。
- runtime-readiness-matrix-0.43.0.md：两表 +pi 行（BLOCKED/DEGRADED、version_command=pi --version）——check-runtime-readiness-matrix 实跑 **PASSED**（代码常量↔文档行双向合约满足）。
- mainstream-agent-loading-0.47.0.md：三处 Pi 行（Tier 1 表 + Official Surface Findings + 运行时表 BLOCKED/DEGRADED）——check-mainstream-agent-loading 实跑 **PASSED**（含 L5090-5096 token 精确子串 + 三 boundary 短语大小写不敏感机检，即 F-2 修复的机检证明）。
- adapters/pi/README.md（84 行实读）：L12 `## Load · 加载模型` / L53 `## Boundary · 能力边界（no-overclaim）` 双语标题同时满足两套 token 机检；L63 三 boundary 短语（official approval/marketplace approval/universal/full runtime support）dsh L65 先例同款；L56 F-3 继承披露；L69-72 分层 E2E 清单含 GOV_ASK_USER_HEADLESS 判据。

### 3.5 测试与金样（清单 5）—— PASS（金样措辞见 F-C4）

- test_verify_workflow.py：见 §2 D5。45 行 diff 中 24 行为新增 pi 专项测试、16 行夹具分支、1 行七元循环、1 行 matrix 夹具、3 行四→五平台断言更新——无既有断言弱化（four_platforms 测试同步改名改断言，未删除）。
- golden_samples.txt（+152/-8）：删除 8 行=时间戳 1（2026-10-03→2026-10-16）+ 版本快照 6（0.93.1 token 行）+ INFO 计数 1（1109→1243 entries）；插入 152 行含 pi 三件套行（`Readme: pi`/`pi/adapter-manifest.json`/`pi/Launch`）——**纯机录再生特征成立**（时间戳/计数/全量快照重算），非手改；但再生成同时捕获了非 pi 历史差量（FIX-445 设计文档面 + 0.94-0.98 release 文档面，+134 条目），归因口径见 F-C4。

### 3.6 Rider 三项（清单 6）—— PASS

- **STATIC_PIN_EXEMPTIONS re-anchor**：4 行统一 +39 漂移（21168→21207、21200→21239、20670→20709、20673→20712），版本值与理由常量未变、豁免条目数未增——数学自洽：test 文件在锚点行之前插入 16（L2647 pi 夹具）+1（L3375 matrix 行）+22（L9427 新测试）=+39；注释按既有纪律声明原因。**无语义豁免扩大**。
- **archguard regen +66**：`git diff --cached --numstat` = **+74/-8 → 净 +66**，与 anchor_loc 28204→28270 精确一致；归因抽验 ≥3 处成立：①LOADING pi dict 15 插入行（diff 逐行可见）；②CAPABILITY_POLICY pi 8 行；③QUOTE_SYNC +1 行 + E2E 矩阵 pi 条目 19 行（含注释）；④PROJECTION 21 行。「R1 +66 七面归因 + R4 1376 不变 + R2/R3/R5/R6 零漂移」的 lineage 注释（test_archguard_ratchet.py L148-159）与实测量吻合。
- **ratchet 冻结面披露**：测试断言 27957→28270 的注释**显式披露** FEAT-093→FEAT-100 窗口已存在 +247（27957→28204）无 rider 的历史欠账、`test_metadata_contract` 基线即红（pre-existing）、+247 归因留给独立补票——披露口径诚实完整。
- **设计文档 F-1 勘误**：staged 版 §1a.4 L143 实读为「（**extensions.md** L135-136 契约）」——F-1 修复已含（staged==工作树，无后续 M）。

### 3.7 验证声明复核（清单 7，抽验）—— 全部吻合

| 命令 | 结果 |
|---|---|
| `git diff --cached --stat` | 20 文件 +2219/-27（**申报 18——差异 2 文件见 F-C1**）；FIX-445 两文件 `infra/hooks/commit-msg`、`infra/tests/test_hooks.py` 均 ` M`（未 staged）✅ 与申报一致 |
| `check-agent-adapters` | **7/7 STATIC runtime-verified（含 pi）+ contracts synchronized** ✅ |
| `pytest -k "pi or adapter or matrix or runtime"` | **1 failed / 138 passed / 10 subtests passed**；唯一失败 `LoopRuntimeClaimAdapterTests::test_claim_command_emits_complete_pass_report` 根因=`check-loop-runtime-claims` verdict BLOCKED，唯一 finding `ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY: ragged table row` @ `docs/research/pi-adapter-integration-research-0.98.0.md`（**untracked，非 staged 面**；定位 L81/L82/L99/L170 表格单元格内管道符如 `` `subagent|sub-agent|spawn.*agent` ``）——非 staged 改动引入，见 F-C2 |
| launch.py | 正常打印（只读）✅ |
| check-runtime-readiness-matrix / check-mainstream-agent-loading / check-cross-references / check-injection-budget | 全部 **PASS**（F-2/QUOTE_SYNC/预算口径机检证明） |

### 3.8 回归与预算声明（清单 8）—— 自洽

- **41F/4911P vs 基线 42F/4909P**：41+4911=4952 vs 42+4909=4951，净 +1。差分解释成立且两条均有机码互证：①+1 总数=新增 `test_agent_runtime_e2e_pi_entry_uses_mixed_scope_readonly_flags`（passed，本审查 -k 集实测绿）；②F 42→41 = ratchet rider 注释自证的 `test_metadata_contract` 基线红（27957 literal 陈旧）被本 rider 同步修复转绿（P +1）；合计 P 4909+2=4911 ✅。我的 -k 抽验 1F 即 41F 之一（F-C2）。
- **SKILL.md 注入预算 +640 tok**：check-injection-budget 实跑 **PASSED**——resident 4441≤6200（gate 面）；entry-skill 18124 tok 属 skill tier **report-only**（16000 预算，超 2124，「measured for visibility; not part of the resident budget」）——FIX-450 report-only 口径与申报一致；+640 量级与 +17 行中文段落（CJK=1 tok/char）自洽（未逐字复算基线值，标注：量级复核）。

---

## 4. 发现清单（P0/P1/P2/P3，每条附证据）

### P0（BLOCKING）—— 无

### P1（关键）—— 无

### P2（WARNING——建议本轮或验收 gate 前闭环）

**F-C1｜被审面申报 18 文件 vs 实际 staged 20 文件——申报完整性缺口**
- 证据：`git diff --cached --stat` 实际 20 文件；任务申报清单 18。未申报两文件：①`docs/requirements/pi-adapter-design-0.99.0.md`（A，655 行——设计文档首次入库并承载 F-1 勘误，内容合理）；②`project/e2e-test-project/skills/software-project-governance/SKILL.md`（+17，任务完全未提及）。
- 裁定：e2e 镜像手改经查为**投影同步的提前手动执行**——设计 §4.2 #10 称该镜像「由 byte_copy 投影随发布同步，不改源」，但仓库存在投影同步机制（`infra/release/projection.py` FIXTURE_PREFIX + `infra/checks/projection.py` L81/L125 e2e-fixture target），主 SKILL.md +17 而镜像不跟会导致投影不一致；实施镜像 diff 与主文件**逐字节相同**（两文件 staged index hash 一致 df725bc..8232eb5），等价于投影结果。性质合规，但「不改源」的设计指示与实施行为不一致且未在申报中披露。
- 影响：不阻塞（内容正确、机检全过）；但违反申报完整性预期（D4 修改纯粹性视角：读者按 18 文件清单审计会漏 2 文件）。
- 建议：Coordinator 合并前在 evidence/commit message 补两文件说明（镜像=投影同步提前执行；设计文档=随实施入库+F-1 勘误）。

**F-C2｜FEAT-100 research 文档 ragged table row 引起 41F 之一失败——链内闭环缺口**
- 证据：`check-loop-runtime-claims` 唯一 finding `ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY: ragged table row` @ `docs/research/pi-adapter-integration-research-0.98.0.md`（untracked ??）；定位 L81/L82/L99/L170——表格单元格内裸管道符（如 `` `subagent|sub-agent|spawn.*agent|delegate` ``、`+name/-name` 上下文）；由此 `LoopRuntimeClaimAdapterTests` FAIL（本审查 -k 集实测复现）。
- 裁定：非 staged 改动引入（该文档早于实施存在于工作树，属基线 42F 时代的预存失败；41F vs 42F 差分声明本身无误）。但根因文件是 **FEAT-100 任务链自身的调研交付物**，按「发现即闭环」原则不应带病进入 FEAT-100 验收。
- 影响：`check-loop-runtime-claims` BLOCKED 会持续出现在全套件失败清单；若 FEAT-100 收尾把 41F 全部归因「预存无关」，该条归因不完整。
- 建议：FEAT-100 验收 gate 前将四处管道符转义（`\|`）或改写为无管道表述，使该 check 转 PASS；或在 evidence-log 显式归类该失败归因于 research 文档并开最小修复项。

### P3（SUGGESTION）

**F-C3｜support_status/e2e_level 偏离设计草案未留偏差记录**
- 证据：manifest L5 `runtime-verified` / L102 `runtime-version-probe` vs 设计 §3.1 草案 `designed` / `real-agent-target-cwd`；机检 L6146-6158 只接受 runtime-verified 族枚举（"designed" 必 FAIL）——设计注记⑤与机检矛盾属设计缺陷，实施取唯一合规组合且诚实性保留（blocked 子块+full_e2e_verified=false+evidence pending）。建议在 evidence 或 decision 注记中显式记录该实施修正（含根 README 边界列 "designed/degraded" 与 manifest "runtime-verified" 的词汇差异说明），防止后续读者困惑。

**F-C4｜金样申报措辞与归因口径不完全精确**
- 证据：申报「8 行删除全为时间戳/版本快照差量」——其中 1 行实为 `[INFO] REQUIRED_FILES loaded ... (1109→1243 entries)` 计数差量；且 +152 插入含非 pi 历史差量（FIX-445 文档面、0.94-0.98 release 面共 +134 条目并入）。金样机制上合法（全量快照再生），建议申报措辞修正为「时间戳/版本快照/INFO 计数差量 + 全量再生并入历史欠账」。

**F-C5｜设计文档常量名笔误沿袭（REQUIRED_FILES/REQUIRED_SNIPPETS vs 实际 OPTIONAL_PROJECTION_FILES/PROJECTION_SNIPPETS）**
- 证据：设计 §4.1 登记点 2/3 与调研 §7.2 引用常量名与实际代码不符（实际 verify L532/L566；行号 L550-553/L657-680 与 chrys 实际位置吻合）。实施正确跟随实际代码落位（机检 7/7 证明）。FEAT-101（移除 chrys）将复用同一清单，建议随下一次设计文档勘误修正，避免误导。

**F-C6｜nested-runner 两处上游同款边界行为（观察项，不建议本轮修改）**
- 证据：①`code ?? 0`（L268）——子进程被信号终止时 close code=null 归 0，官方 L403 同款；实现以 `aborted` 布尔兜底（isFailedRun L87），abort 语义无缺口。②`if (!proc.killed) proc.kill("SIGKILL")`（L282）——Node 语义下 SIGTERM 发出后 killed=true，Unix 上 SIGKILL 分支实际不可达（Windows 上 kill 本即强杀，无影响）；官方 L414-416 逐字同款。一致性优先于局部优化，如上游修复可跟进。

**F-C7｜e2e 镜像投影的长期口径**
- 证据：F-C1 的镜像手改虽结果正确，但「投影文件何时手动同步 vs 等发布工具同步」无成文规则（release/projection.py 的同步时机文档未覆盖 mid-cycle 场景）。建议在 FEAT-101 前由 Coordinator 定一句口径（如「主文件变更的同一 commit 必须手动同步镜像」），消除下次的不确定。

---

## 5. 蓝军挑战记录（Reviewer 独立挑战）

| # | 挑战 | 结果 |
|---|---|---|
| C1 | dispatch_agent 递归派发是否真的被机器阻断（而非仅文档声明）？ | 是：`--exclude-tools ask_user_question,dispatch_agent` 无条件追加于 args 组装尾段（dispatch-agent L251-253），新增矩阵测试 + tool description + README 三面一致；allowed_tools 与 exclude 独立叠加不互斥 |
| C2 | `ctx.ui.select` 若返回被 pi 改写过的选项文本（非 verbatim 回显），序号解析会不会错？ | parseSelectedLabel 正则失配时回退裸 label 匹配再回退 verbatim 字符串（ask-user L109-116），任何回退路径都不产生错误映射；最坏情况回传渲染文本，模型可读 |
| C3 | Windows 下 `spawn(process.execPath, [cli.js, ...])` 若用户经非 npm 渠道安装（无 APPDATA 布局）？ | resolvePiInvocation 四级回退：argv[1]→npm-global cli.js→非通用 runtime 直连→PATH "pi"（L131-152）；PATH 分支在 Windows shell:false 下可能失败是设计 R-6 已标注未实测面，与官方回退一致；L2/L3 E2E 探测为既定验证路径 |
| C4 | 金样/版本号 token 是否会被 pi 之外的平台误消费（QUOTE_SYNC 七平台循环）？ | 元组追加在尾部、CONSULT_DRAW_MARKER 常量未动、检查体逻辑零变更（diff 实证）；check-cross-references 实跑 PASS |
| C5 | 新增测试是否只是镜像实现的同义反复（无 FAIL-on-buggy 价值）？ | 否：断言探针 verbatim（`_agent_runtime_e2e_prompt("pi")`）、--tools 参数关联（index+1）、-na/--no-session 存在性、validator 身份——删除任一混合口径旗标即 FAIL |
| C6 | staged 面里是否藏有与 pi 无关的搭车改动？ | 20 文件逐一审阅：除 F-C1 两文件（设计文档/e2e 镜像）与金样历史欠账并入（F-C4）外，无其他搭车；verify_workflow.py +74/-8 全部归因 pi 登记面 |

---

## 6. 审查自检（事实依据红线）

- 本报告全部结论基于实读文件（五 TS 文件全文、manifest/README/launch.py 全文、pi 包 dist 类型与官方示例实读、九处登记 diff 逐处）与实跑命令输出（§3.7 表）；未验证面（runtime 行为：jiti 加载/dialog 实际渲染/spawn 实跑/模型调用）按设计 §6 分层验收定位由 E2E 承接，manifest blocked 声明与之自洽，本报告未将其作为 APPROVED 依据。
- 审查过程零产品文件修改、零 git 状态变更（无 add/restore/reset/commit）、零 `.governance/` 写入、零模型 API 调用、pi 包目录只读（唯一写入=本报告）。
- 临时验证产物仅 `%TEMP%\lrc.json`（会话临时目录，非仓库面）。

---

*审查结论返回 Coordinator：APPROVED_WITH_NOTES · unresolved_blockers=0 · P0=0 · P1=0 · P2=2（F-C1 申报缺口/F-C2 research 文档 ragged row）· P3=5 · 复审建议=无需返工重审；F-C1 建议合并前补披露、F-C2 建议 FEAT-100 验收 gate 前闭环（修复或显式归类），其余 P3 可遗留跟踪。*
