# FEAT-099 设计文档：U1 DSH 宿主级执法接线 PoC（host-level enforcement wiring PoC）

- **Task ID**: FEAT-099（plan-tracker L118；DEC-374 用户裁决立项并定版 0.100.0，2026-10-26）
- **角色**: Architect Agent（PoC 链 Architect → Governance Developer 的 Architect 段）
- **需求源**: machine-signal——FEAT-095 M-0 调研 §3/§7 未证实面 U1（`docs/research/feat-095-harness-enforcement-capability-2026-10-10.md` L221）
- **验收基线**（plan-tracker L118 原文）：至少一类越界派发可被宿主级拦截证明（或如实证伪留锚）/降级披露口径随结论更新
- **执行链契约**: `.governance/agent-locks.json`（FEAT-099 Architect 锁，active_tasks.FEAT-099，acquired 2026-10-26T17:21:07）
- **文档版本**: R1+（2026-10-27；implementation_authorized=**true**——REVIEW-FEAT-099-R1 delta 复审 APPROVED_WITH_NOTES/0〔txn-147ee345〕后由 Coordinator 翻转）
- **修订记录**: R0（2026-10-26）→ REVIEW-FEAT-099-DESIGN-R0 NEEDS_CHANGE（D1/D2/D3 P1×3；D4/D5 P2×2；D6/D7/D8 P3×3）→ R1 逐条闭环（D1 参数面前提标注+F1b 证伪分支+V0 探明；D2 投影扩展裁定 (b)；D3 C6 按锚分流；D4 C0 窗口期+V8 时序观测；D5 派生源指认 observed_revision；D6 节号勘误；D7 DEC 第七要点；D8 投影字节断言）→ R1 复审 AWN/0 + R1+ 授权翻转与 N1-N3 勘误（N1 observed_revision 全文件措辞；N2 C0 括注笔误；N3 F1b 分支①未证实标注——Coordinator 2026-10-27 随 R1 复审结论闭环）

## 0. 输入清单与证据口径

| # | 输入 | 用途 |
|---|---|---|
| I1 | `docs/research/feat-095-harness-enforcement-capability-2026-10-10.md` §7（L217-229 U1/U7）、§8.2（L244-249 宿主级试点建议）、§10（L280-289 已交付降级形态） | 设计起点与验收口径 |
| I2 | `skills/software-project-governance/infra/enforcement.py`（727 行，全读） | 策略表/执行器分离现状 |
| I3 | `adapters/dsh/host-contract.json`（2491 行，重点 own 块 L737-880） | parity 契约现状 |
| I4 | `lib/index.js`（700 行，全读）+ `lib/dsh-native/bridge.js`（212 行，全读） | host row 注册现状 |
| I5 | `adapters/dsh/README.md`（86 行）、`adapters/dsh/adapter-manifest.json`（127 行） | adapter 声明/披露面 |
| I6 | DSH 宿主一手文档（只读参考，npm 安装面 @0.1.5-rc.3：`C:\Users\peter\AppData\Roaming\npm\node_modules\@deepseek-ai\dsh\node_modules\@deepseek-ai\`）：`dsh-tools/README.md`、`dsh-tool-subagent/README.md` | 拦截原语锚定 |
| I7 | `skills/software-project-governance/infra/dsh_doctor.py`（STAGES L105-114、CLI L1917-1945）、`infra/authority_ledger.py`（L17-18 账本+快照模式）、`.governance/agent-locks.json`（锁结构） | 验证跑法与治理态源设计 |
| I8 | `skills/software-project-governance/SKILL.md` L234-238（动作级执法契约段） | 降级披露口径锚点 |

> 未证实面沿用调研 §7 口径如实标注「未证实」，不得装作已证实。DSH 安装态（`D:\app\dsh`，Electron 应用，`resources\app.asar` 归档 + `app.asar.unpacked\dsh\node_modules`）全程只读参考。

---

## 1. 现状锚定（逐条路径+行号）

### 1.1 enforcement.py：策略表与执行器分离（CLI 级判定面）

- **策略表 = 数据（STRATEGY）**：`BOUNDARIES` 六边界元组（L89-96：dispatch-execute/dispatch-review/accept-completion/merge/release/goal-resume）；`HARD_BLOCK_RULES` 四类硬阻断（L98-103：revision-mismatch/unauthorized-write/duplicate-identity/unresolved-blocking-review）；`STRATEGY` 字典（L179-199）含审查债阈值 `review_debt_budget: 100`（L193）、白名单通道 fix/re-review/forensics（L105、L195）、WIP carve-out（L198 `"wip_carve_out_boundary": "merge"`）。注释明示「新增边界/规则/阈值改表不动执行器」（L11-12）。
- **执行器 = 泛型 decide()**：`decide(facts, strategy)`（L230-259）纯同步判定，只消费 facts 与策略表，「无边界特判分支」（L202）；四类硬阻断规则命中求值在 `_rule_hit`（L346-429），其中 **revision-mismatch** 判定：`action.revision`（int）与 `state.expected_revision[task_id]` 不等即命中（L352-374）——本 PoC 切片消费的正是这条规则。
- **fail-closed 已内建**：任何内部异常 → 保守 HARD_BLOCK，`reason_code=enforcement-fail-closed`（L33-34、L243-259）；非法开关值不猜（L204-217 `switch_state` 返回 None → L619-639 保守阻断）。
- **零漂移开关**：`GOVERNANCE_ENFORCEMENT=off` → advisory 基线，不读 facts、不落记录、零副作用（L35-36、L642-662）。
- **CLI 出口码四态**：0 ALLOW / 2 HARD_BLOCK（含 fail-closed）/ 3 THROTTLE / 4 STALE_NOTICE（L44-45、L114-117、L606-691）；机器记录 `enforcement-log.jsonl`，grep 锚点 `ENFORCEMENT-ACTION`（L46-47、L577-603）。
- **策略表 JSON 投影已存在**：`_strategy_public()`（L549-574）+ `--print-strategy`（L615-617）输出六边界×三层的可 grep JSON——**本设计将此投影用作宿主侧判定器的策略单源**（见 §3b）。
- **降级披露头注**：模块 docstring L38-42 明示「六平台均无已接线的宿主级拦截——本模块是 CLI 级判定面 + 协议级契约段，不做任何宿主级拦截能力声明」——这是 PoC 结论后要翻新的措辞面之一。

### 1.2 host-contract.json：own.host_row parity 契约现状

- **own 块语义**：`own._note`（L738）「本包约定（我们自己的 parity 契约：JS × Python × 模板 × hooks）。与 host.* 分开」——契约是四平面一致性的事实源。
- **host_row 现状**（L763-775）：`entry: lib/index.js`；`export_surface: [apply, ensurePreset, name, renderComposition]`；**`apply_never_throws: true`**；**`warn_only: true`**；`top_level_io: false`；`runtime_dependencies: []`。coverage.entries 对 `own.host_row` 的守卫（L910-928）：`test_lib_apply_warns_and_never_throws_without_payload` + 反相 fixture FX-JS-03，gap_note「warn-only/永不抛是宿主行对宿主的安全承诺（设计 §2.6 J-1~J-7）」。
- **guard 键已占用为另一含义**：`own.paths.guard = skills/software-project-governance/infra/dsh_compat.py`（L835）——指 Python 兼容守卫。宿主级 guard 扩展的契约命名须避开该键（见 §3a）。
- **架构边界先例**：patch 形状不变量 `exactly-one-insert-row / no-id-update / no-trust / no-!!js`（L776-784）；native 块（L794-811）声明「consumes exactly two PUBLIC host services」语义由 lib/index.js 承载（见 §1.3）。
- **测试先例（本 PoC 复用）**：隔离 DSH_HOME 拒未重定向（coverage L1282-1284：`test_smoke_cli_refuses_unredirected_dsh_home` / `test_smoke_cli_refuses_dsh_home_at_user_home` / `test_smoke_refuses_in_process_when_dsh_home_is_real_home`）；JS×Python 渲染 parity（L830：`test_js_and_python_renderers_agree`——策略/判定 parity 测试的直接先例）。

### 1.3 lib/index.js：host row 注册现状（零守卫）

- **行的唯一入口**：`apply(ctx, config)`（L667-699）——只委托 `applyNative(ctx, config, contractDocument)`（L670），catch 后 warn（L671-675，apply_never_throws 兑现）；native 不可用时按结构化 code warn 并返回（L676-699），**从不调用 `ensurePreset()`**（DEC-366 ②，L457-462 docstring）。
- **架构边界声明（本 PoC 必须修订的面）**：L60-75「two faces, both forward-only」——native face「consumes exactly two PUBLIC host services — `loader` (read-only) and `agentPresets` (registration only) — and publishes nothing」。注册宿主 guard 将新增第三个服务消费（`tools`），该声明与 DEC-187「只动自有行」的合规性论证一并进 DEC 草案（§3a）。
- **失败策略双段声明**：L33-36 与 L86-92「Failure policy (both paths): warn-only. Nothing must ever throw out of `apply()`」——guard 扩展不得削弱该承诺。
- **native 桥的注册时机先例**：bridge.js L129-137/L183-211——服务在行 apply 之后才提供，公共等待原语是 `ctx.inject(['agentPresets'], …)`（L11-13 注释：服务依赖而非 sleep/顺序猜测）；`service(ctx, name)` 防御性读取（L43-50）。**guard 注册沿用同一 inject 模式与能力检测（`typeof ctx?.tools?.guard === 'function'`）**。
- **现状结论**：host row 全模块（index.js 700 行 + dsh-native/ 六件）**没有任何 `ctx.tools.guard` / pre-execute / restrict 调用**——与调研 §6 发现1「插件零接线」一致（I1 L207；R0 误标 §3.1，R1 勘误）。

### 1.4 DSH 宿主拦截原语（一手文档，@0.1.5-rc.3 npm 面）

- **单调同步 guard**：dsh-tools/README.md L89「`ctx.tools.guard(guard)` registers a monotonic synchronous guard after the extensible `tools/pre-execute` waterfall: a returned reason denies the call, and no later listener can turn that denial back into permission」；管线固定次序 L109「`tools/pre-execute` → registered monotonic guards → `tools/execute` → `tools/post-execute` → finalizeContent → `tools/result`」；扩展点 L141「`ctx.tools.guard()` adds monotonic owner policy after it」。
- **per-agent 掩码**：L85 `ctx.tools.restrict(filter)`——masks intersect，scoped 可见，dispose 即解除。
- **关键限制**：L233「`tools/pre-execute` deliberately cannot rewrite `exec.arguments`」——改写禁令隐含 **pre-execute 事件面**持有 `exec.arguments`（可读不可改写）；guard 可拒不可改写派单参数。
- **拒绝的模型可见性**：L126「A pre-execute denial may attach `ToolErrorInfo` beside its model-facing reason」+ L215「Any thrown or denied call becomes exactly `Error: <message>`」——deny 理由可回传模型（remedy 通道成立）。
- **subagent 面漂移注记（相对调研 S8 时点）**：当前 `dsh-tool-subagent/README.md` config 表（L45-53）已**无 `toolFilter` 行**——L72「Tool configuration containing `persona` or `toolFilter` fails at load with a migration error」（迁至 preset 组合面）；`maxDepth` 现为 Host setting 默认 `1`（L53；L63 深度帽仍为执行时拒绝）。**含义：静态掩码路线进一步偏离 per-call 动态判定，`ctx.tools.guard` 是动态治理判定的唯一通道——PoC 选 guard 路线的依据增强。**
- **未证实（沿用 U1 口径）**：① **guard 回调能否读取被调工具的 arguments（prompt）——锚协议的载体前提**（README 全文无一处直接陈述 guard 回调签名与参数面；L233 仅证实 pre-execute **事件面**持有 `exec.arguments`，「guard 回调与该事件共享同一 exec 视图」是架构推断而非文档证实——R0 漏标，R0 审查 D1 补）；② guard 回调内可用的上下文面（能否定位会话 workspace、调用方身份）；③ 第三方包在自有行内注册 guard 的实机行为；④ 每调用开销——全部留给 PoC 实测（I1 L221），探明动作见 §4.1 V0。

### 1.5 披露面现状（PoC 结论后的翻新对象）

- SKILL.md L238：「仅协议+CLI执法，未接线宿主拦截」——现行降级披露口径原文。
- adapter-manifest.json `runtime_capabilities`（L38-70）：七键中无 enforcement 类键——与调研 §8.3 L256「manifest 的 runtime_capabilities 不新增 enforcement 能力键除非 U1 落地证实」一致。
- adapters/dsh/README.md L59-69 能力边界段：无宿主执法声明。
- host-contract.json own.host_row（L763-775）：无 guard 面声明。

---

## 2. PoC 范围裁定

### 2.1 选定切片：subagent/subagent_fork 修订错配派单拒绝（边界①②最小面）

**裁定**：在自有 host row 内注册 `ctx.tools.guard`，覆盖工具面 = `subagent` + `subagent_fork` 两个工具名（host-contract L473-515 组合行 `tool-subagent`/`tool-subagent-fork`；toolName 默认 `subagent`，I6 L48），启用策略 = 硬阻断规则 **revision-mismatch**（enforcement.py L139-147/L352-374）单条。理由：

1. 调研 §5 矩阵（I1 L191）已裁定 dsh 的边界②「guard 可按修订错配动态拒 spawn——FEAT-095 核心用例的唯一宿主级落点」；
2. revision-mismatch 是四类硬阻断中**纯函数可判定**的一条（int 比对，无白名单交互、无债预算聚合），切片最小、故障注入构造最确定；
3. 边界①②共用同一工具面（spawn 通道），一次接线覆盖两边界的第一类证明。

**判定语义（锚协议）**：guard 无法从自由文本 prompt 语义判定修订——pre-execute 又不可改写参数（§1.4）。故 PoC 定义**派单锚**协议级约定（派发方 prompt 首行结构化标记）：

```
[governance-dispatch task=<TASK_ID> rev=<int> channel=<normal|fix|re-review|forensics> actor=<role>]
```

guard 行为：提取锚 → 与治理态 expected revision 投影比对 → `rev ≠ expected[task]` ⇒ **deny**（reason 携带 reason_code=revision-mismatch + remedy；**文案模板单源 = 扩展后的策略投影**——现状 `_strategy_public()` 仅投影 rule id（enforcement.py L560-561），L141-147 的 reason/remedy 模板不在投影内，R1 裁定扩展投影见 §3b/D2，模型可见 reason 通道依据 dsh-tools L126）；`rev = expected` ⇒ allow；**无锚 ⇒ allow + 计数披露**（PoC 阶段不强制锚——强制锚会拒绝一切非治理派单，误伤面不可接受；此对抗缺口如实登记 U7，见 §4.2）；**锚存在但解析失败 ⇒ deny（fail-closed，§3c）**。**前提：guard 回调可读取调用 arguments（§1.4 未证实①）——不成立则锚协议整体证伪（F1b，§5.1）。**

**expected revision 的治理态源（如实裁定）**：调研与现状核实表明**今天不存在单点权威的 expected_revision 治理文件**——CLI 级 facts 由 Coordinator 组装投影（enforcement.py L230 只消费 facts，不读治理文件）；authority_ledger.py 的 tasks 态（L818/864/941）持身份/语义锚而非修订号。故 PoC 裁定：**验收用隔离治理 fixture 声明 expected 投影**（临时项目 `.governance/` 内构造，不进产品面、不碰真实 `.governance/`）。
**生产化路径（R1 指认派生源，R0 审查 D5；N1 勘误）**：现成机写通道 = `task-row-update` 的 content-level CAS——`--inspect` 输出 `observed_revision`（`revision_of(task row text)`——**全文件内容修订指纹（whole-row revision），非单行文本依据**，后续批细化粒度语义时注意，task_row_update.py L1827/L1945-1946），`--expected-revision` 消费它做 CAS 期望（L2200-2201 help 原文「Content-level CAS expectation (from --inspect observed_revision)」，L2215-2217「the CAS expectation source」；不匹配即拒 L2092-2097）。生产化 = 后续批把 `observed_revision` 派生进 governance-bootstrap 热数据投影（单源），guard 读该投影；**PoC fixture → 生产的切换点 = 投影文件由 fixture 手构造改为 bootstrap 聚合机写**（guard 读面接口不变，仅 W 内文件来源切换）——列为实施授权前置项（§6 S1）。

### 2.2 明确不做的面（留后续批）

| 面 | 不做理由 | 依据 |
|---|---|---|
| 其余三类硬阻断（unauthorized-write/duplicate-identity/unresolved-blocking-review） | unauthorized-write 需 fs 写路径拦截（边界③辅助面，工具面不同）；duplicate-identity 源 agent-locks 可机判但需锁语义联调；blocking-review 需白名单交互——均扩大切片 | enforcement.py L148-174 |
| 审查债限流（THROTTLE）与冷面提示（STALE_NOTICE） | 聚合计算面大、非「越界派发拦截」验收对象；缓存架构按全集设计但默认只启用 revision-mismatch（表数据驱动，与 python STRATEGY 同构） | enforcement.py L17-21/L186-193 |
| `update_goal`（边界⑥）/fs 写 `.governance/`（边界③） | 调研 §8.2 L246 列为试点全景，但 PoC 验收只要求「至少一类」；goal 面另有平台自有机械门槛（I1 L97-99） | plan-tracker L118 |
| 静态掩码路线（restrict/toolFilter） | 每实例静态且已迁出 tool config（§1.4），不满足 per-call 动态判定；角色面收窄留后续批 | I1 L209 发现3 |
| sandbox-policy/user-approval 依赖 | 部署策略可关（发现7）；guard 是插件自注册不受用户预设影响——不依赖 | I1 L213/L249 |
| 多通道 spawn（route_agent/workflow/ralph/pwsh 子进程） | PoC 只挂 subagent/subagent_fork；其余通道逃逸如实记录（§4.2 对抗矩阵） | U7 口径 I1 L227 |
| 其余五平台宿主级 | U2-U5 未证实且非本票范围 | I1 L222-225 |

---

## 3. 三项前置裁定设计方案（§8.2 原文逐项）

### 3a. `own.host_row.warn_only=true` 契约变更的 DEC 草案要点（设计仅草案，DEC 入账归 Coordinator）

1. **不变量保留**：`apply_never_throws: true`、`top_level_io: false`、`runtime_dependencies: []`（零依赖纯 JS guard）不变——宿主 boot 安全承诺（§1.2 J-1~J-7）不因执法能力引入而削弱。
2. **warn_only 语义收窄而非翻转**：`warn_only: true` 的管辖域收窄为「**行生命周期面**（apply/注册/预设交付）失败只 warn 不抛」；新增 `own.host_row.enforcement_guard` 子块（避开已占用的 `own.paths.guard` 键，§1.2）声明**执法面**：注册原语（`ctx.tools.guard`）、覆盖工具面（PoC = subagent/subagent_fork）、判定规则集（策略表 JSON 投影单源）、行为规格（§3b/§3c）、开关（`GOVERNANCE_ENFORCEMENT` 同源）。guard 的 deny 是宿主管线一等语义（§1.4 L89），**不是行的异常路径**——warn_only 不适用于 deny 动作本身。
3. **架构边界修订**：native face 服务消费从「exactly two（loader/agentPresets）」（lib/index.js L69-75）扩为「three（+ tools：guard 注册，能力检测式，缺失即 warn 降级）」；仍 publishes nothing（guard 是向宿主管线注册策略回调，不发布服务）；DEC-187「只动自有行」合规性不变（guard 注册在自有行激活内，不触碰任何宿主行）。
4. **失败分层**：注册失败/能力缺失 → 一次结构化 code warn + 降级为「无宿主执法」（与 native 四种不可用态同形态，lib/index.js L86-92）；guard 回调内异常 → fail-closed deny（§3c）。
5. **parity 四面同步**：host-contract（own.host_row 数据）+ lib/（guard.js 实现 + index.js 接线）+ 测试（JS 单测 + JS×Python 判定 parity + 隔离 E2E）+ 协议面措辞（SKILL L238 / README / behavior-contract-details §enforcement）——任一面缺席即契约缺陷（own._note 口径，§1.2）。
6. **可逆性**：`GOVERNANCE_ENFORCEMENT=off` 为整体退出开关（零漂移）；代码回滚 = 移除 guard 子块 + guard.js + 接线三处。
7. **guard 注册窗口期定性（R1 增，R0 审查 D7/D4）**：guard 经 `ctx.inject` 延迟注册（§1.3 先例），行激活 → 注册完成之间存在**已知执法空窗**——DEC 中定性为「已知边界、如实披露」而非缺陷遮蔽：窗口期内带锚错配派发不被拦截（§3c C0），披露面登记（§5.3）；窗口期时长经 V8 观测落盘，宿主时序论证（若有）由后续批补强。

### 3b. guard 读治理态的性能设计（禁每工具调用起 python 进程）

**禁令依据**：调研 §8.2 前置裁定②原文「不能每工具调用起 python 进程——建议 watch/缓存治理面文件，脏时重算」（I1 L247）。

**方案：宿主进程内 JS 判定器 + stat 指纹缓存（脏时重算）**：

- **判定器载体**：`lib/dsh-native/guard.js`（新模块）——纯函数判定，逻辑镜像 enforcement.py `decide()` 的 revision-mismatch 分支。
- **策略与文案模板单源（R1 裁定，R0 审查 D2）**：现状 `_strategy_public()` 的 `hard_block_rules` 仅投影 `rule["id"]`（enforcement.py L560-561），reason/remedy 模板（L137-175，含 L141-147 revision-mismatch 文案）**不在投影内**——R0 的「单源=投影」与「deny 文案对齐 L141-147」直接矛盾。裁定 **(b) 扩投影**：`_strategy_public()` 增列 `hard_block_rules[].{reason, remedy}` 模板（**Python 面数据投影小改，判定语义零改动**，随 PoC 实施列入 §6 S1；否决 (a) 模板硬编码进 guard.js = 无漂移守护的第二源）。fixture 由 `enforcement-check --print-strategy`（L615-617）构建期生成随包分发（受审提交，不运行期起 python）；**双重 parity 守护**（R0 审查 D8）：① JS×Python 判定 parity 测试（同 facts 集输出一致——先例 `test_js_and_python_renderers_agree`，host-contract L830）；② **投影字节断言**——fixture 文件与 `--print-strategy` 当前 stdout 逐字节相等（防投影过期静默漂移，一并守护文案模板）。
- **缓存键**：`fingerprint = Σ stable_hash(path ∥ mtime_ns ∥ size)` over 治理面文件集 W。PoC 切片 W = { 会话 workspace 下 `.governance/agent-locks.json`（锁/身份面，I7）、expected-revision 投影文件（§2.1 fixture）、`.governance/execution-packets.json`（执行包约束） }；生产化后 W 扩为 governance-bootstrap 热数据投影文件（单源）。
- **失效条件**（任一即整缓存失效重算）：① W 中任一文件 `mtime_ns` 或 `size` 变化（每次 guard 调用同步 stat 比对——Windows stat 单文件 ~10-50µs，N=3 时可忽略）；② TTL 兜底 max-age = 30s（防文件系统 mtime 粒度/时钟回拨漏检）；③ 环境开关值变化（每次读 `GOVERNANCE_ENFORCEMENT`）；④ 治理根定位变化（见下）。
- **脏时重算**：重读 W + 重建投影；**审查债预算**（`Σ clamp(severity,1,5) × clamp(age_days,0,30)`，enforcement.py L220-227）仅在指纹脏且启用 admission 边界时重算——PoC 表数据只启用 revision-mismatch，债路径实现但默认关闭（与 python STRATEGY 表驱动同构，切规则不改执行器）。
- **治理根定位（未证实项，PoC 必测）**：guard 运行于宿主进程，其 CWD ≠ 会话 workspace。定位序：`GOVERNANCE_REPO_ROOT` env > 宿主回调上下文中的 workspace 信息（**guard 回调内能否取到会话 workspace——未证实，V0 探明**）> 均无 ⇒ **按锚状态分流（§3c C6a/C6b，R1 修订）**：无锚调用 allow + 一次性 warn 披露降级态（非治理面流量不误伤）；带锚调用 deny（判定依据缺失 = fail-closed，不留静默放行破口）。探测侧「require_explicit / no_fallback」安全属性先例（host-contract L79-86 probe_side）对齐：guard 从不猜默认治理根。
- **性能预算**：guard 单次判定（含 stat 比对 + 判定）p95 ≤ 10ms——对齐 FEAT-095 CLI 级性能守护阈值先例（「性能守护 ≤10ms/次墙钟」，I1 L289）；超预算即证伪判据 F2（§5.1）。

### 3c. fail-closed 语义：guard 自身异常时保守阻断并披露的行为规格

对齐 enforcement.py fail-closed 语义（L33-34/L243-259：执法器异常保守阻断并披露，绝不静默放行）与调研执行包 security 阈值原文（I1 L247③）：

| # | 故障态 | guard 行为 | reason_code |
|---|---|---|---|
| C0 | **注册前窗口期**（行激活 → inject 回调完成前；R1 增，R0 审查 D4） | **已知执法空窗，非故障**：窗口期调用不经 guard、不判定不记录——如实披露（§3a-7/§5.3），时长经 V8 观测落盘；不以概率论证替代判据 | —（窗口期内无 guard 在场——N2 勘误：原文「窗口期外」为笔误） |
| C1 | 治理面文件不可读 / JSON 损坏 | **deny**，reason 指名路径与错误类型，remedy=修复或移除后重试 | `enforcement-fail-closed` |
| C2 | 判定器内部异常（解析/比对抛错） | **deny**，reason 披露异常类型（对齐 enforcement.py L246-248 文案结构） | `enforcement-fail-closed` |
| C3 | 锚存在但格式非法（如 rev 非 int） | **deny**（声明了锚即请求执法判定，判定不了就拒；类型校验对齐 enforcement.py L356-358） | `enforcement-fail-closed` |
| C4 | 开关值非法（词表外） | **deny**（非法值不猜，对齐 L619-639） | `enforcement-switch-invalid` |
| C5 | 开关 off | **allow-through，零判定零记录零副作用**（零漂移，对齐 L642-662——行为等同没有 guard） | `enforcement-disabled`（仅 stdout 一次性提示，不逐调用） |
| C6a | **无锚**调用 + 治理根不可定位（§3b 定位序穷尽） | **allow** + 一次性 warn 披露降级态（无锚本就不请求判定，非治理面流量不误伤；能力缺失分级仅在此面成立） | `enforcement-unlocated`（披露） |
| C6b | **带锚**调用 + 治理根不可定位（R1 修订，R0 审查 D3） | **deny**（按 C3 同一论证：带锚=显式请求执法判定，判定依据缺失正是「判定不了」的形态；与 C1 仅故障形态差异，处置必须同向——fail-closed 总则不留静默放行破口），reason 指名「治理根不可定位」+ remedy=设置 `GOVERNANCE_REPO_ROOT` 或修复 workspace 上下文 | `enforcement-fail-closed` |
| C7 | 无锚调用（治理根正常） | **allow** + 计数（§2.1；协议配合缺口，U7 登记） | `enforcement-unanchored`（计数披露） |

- **deny 的呈现**：reason 必须含 reason_code + remedy（模型可读回传，§1.4 L126/L215）——reason/remedy 文案模板单源 = 扩展后的策略投影（§3b D2 裁定 (b)，模板本体 enforcement.py L137-175）。
- **机器记录**：guard 以 best-effort 追加 `enforcement-log.jsonl`（同锚点 `ENFORCEMENT-ACTION`，对齐 L46-47/L577-603）；**记录写失败不吞不炸**：披露到 deny reason 的 `record_error` 附加字段，不影响已作出的判定（对齐 L592-595）。
- **与 warn_only 契约的关系**：C1-C4 的 deny 是工具调用级动作，不出 host row 生命周期面——`apply_never_throws` 不被触碰（§3a-2）。

---

## 4. 验证方法

### 4.1 PoC 验收步骤（违规 spawn 的最小构造）

**环境形态（真实宿主平面 + 全隔离文件面）**：临时目录 `T`；`T\proj\.governance\` 构造最小治理 fixture（agent-locks.json + expected-revision 投影：`{"POC-1": {"expected_revision": 2}}`）；`DSH_HOME=T\home` 显式重定向（隔离先例：`test_smoke_cli_passes_in_isolated_home`，host-contract L1123；未重定向必拒先例 L1282-1284）；bundle 接入 `dsh plugin --profile <p> add "link:<本仓库绝对路径>"` + 重启（adapters/dsh/README.md L45）；会话 workspace = `T\proj`。**真实 DSH_HOME / 真实 `.governance/` 零触碰。**

| # | 步骤 | 期望观测（验收判据） |
|---|---|---|
| V0 | **首项探明（R1 增，R0 审查 D1；先于一切 V 步）**：隔离环境最小 guard 注册，探明① guard 回调可读取被调工具 arguments（锚载体前提，§1.4 未证实①）② 治理根定位序可用性（§3b）③ 注册原语可达性 | 三项均得实证记录（读到场即记录参数形态；读不到即触发 F1b 分支裁定，§5.1）；探明结果落盘后才进入 V1-V8 |
| V1 | 活体 dsh 会话中发起 `subagent` 调用，prompt 首行 `[governance-dispatch task=POC-1 rev=1 channel=normal actor=Developer]`（expected=2 ⇒ 修订错配） | **调用被宿主拒绝**：模型收到 `Error: [governance-enforcement] revision-mismatch … remedy: …`；子代理未启动；`enforcement-log.jsonl` 追加 HARD_BLOCK 行 |
| V2 | 对照组：同调用 `rev=2` | 子代理正常启动（`started subagent <id>`，I6 L59） |
| V3 | 无锚派发 / `GOVERNANCE_ENFORCEMENT=off` / 非法开关值 / **带锚派发 + 治理根不可定位（清空 env 与 workspace 上下文注入）** | 分别 = allow+计数 / allow-through 零记录 / deny / **deny（C6b，R1 增，R0 审查 D3）** |
| V4 | `subagent_fork` 同构造复跑 V1 | 同 V1（两工具名均覆盖） |
| V5 | fail-closed 注入：expected 投影写坏 JSON 后再发 V1 构造 | deny，reason_code=enforcement-fail-closed（C1） |
| V6 | 性能采样：≥100 次判定（V2 构造循环） | guard 判定墙钟 p95 ≤ 10ms（§3b 预算） |
| V7 | 证据落盘 | session 轨迹 + guard 日志 + 判定记录入 EVD（Coordinator 机录；验收措辞用「隔离环境安装冒烟（环境变量重定向至临时目录）通过」口径） |
| V8 | **注册窗口期时序观测（R1 增，R0 审查 D4）**：boot 起持续记录 guard 注册完成时间戳与全部 subagent 调用时间戳；窗口期内注入一次带锚错配派发 | 窗口期时长落盘（已知边界披露，§3c C0）；窗口期内注入调用**如实记录为未被拦截**（不粉饰为通过）；窗口关闭后同构造复跑 = 拒绝（对齐 V1） |

### 4.2 U7 对抗性故障注入设计要点（多通道逃逸）

U7 原文（I1 L227）：「模型级绕行（如改用 pwsh 直接跑 git）需边界联动（guard 面 + bash/fs 面 + git hooks 面全堵才算闭环）」。PoC 对抗矩阵（隔离环境逐通道注入越界派发，记录拦截/逃逸）：

| 逃逸通道 | 注入形态 | PoC 预期 | 处置 |
|---|---|---|---|
| A1 guard 面-同工具 | 错配修订重试 / 无锚派发 | 前者拒；**后者逃逸成功** | 无锚缺口如实披露（§2.1），强制锚裁定留后续批 |
| A2 guard 面-其他 spawn 工具 | route_agent / workflow / tool-ralph / tool-workflow 派发同名越界任务 | **逃逸成功**（PoC 未挂这些工具） | 逃逸面清单落盘；后续批扩工具面 |
| A3 bash/fs 面 | pwsh 起子进程（python/codex CLI）执行派发 | **逃逸成功**（guard 不做命令内容分析；fs/bash 沙箱=部署策略变量，发现7） | 披露为部署依赖项；联动 fs-sandbox 留后续批 |
| A4 git hooks 面 | 逃逸产物 commit | pre-commit Step7 / commit-msg 审查证据门 `exit 1` 拦（I1 L167-171） | 已有面验证（不需新建） |

**闭环口径（如实）**：PoC 验收 = 「guard 面一类越界派发可被宿主级拦截证明」（plan-tracker L118）；A1-A3 逃逸面**不构成 PoC 失败**，但其清单+严重度是降级披露措辞的强制输入（§5.3），U7 行随结论更新。

### 4.3 dsh-doctor 全阶段跑法

- 命令：`python skills/software-project-governance/infra/verify_workflow.py dsh-doctor`（adapter-manifest.json L36 声明：stages S0-S7、four switches、exit 0/1/2、per-stage crash isolation）；STAGES 定义 dsh_doctor.py L105-114（S0 input/interface → S7 hooks/self-upgrade）；CLI 开关 L1917-1945（`--json/--stage/--offline/--selftest/--record-evidence/--out/--rehearse/--against/--allow-host-probe/--fail-on-issues`）。
- **隔离纪律**：PoC 运行于 `DSH_HOME` 重定向环境；**不加 `--record-evidence`**（真实平面证据采集是维护者受审提交面，FIX-326③ 口径，host-contract L34）；需 `--allow-host-probe` 时按 R1 三选一授权（host-contract L718 dump_config_policy）。
- 判据：S0-S7 全 PASS 或环境缺失面按 NOT_RUN 披露（NOT_RUN 不计 PASS，host-contract L34 口径；先例：I1 执行包 expected_output L1461「S1/S2/S4/S6/S7 PASS 且 S0/S3/S5 以 NOT_RUN 披露」）；guard 扩展不得使任何既有 stage 从 PASS 翻 FAIL（回归判据）。

---

## 5. 证伪路径

### 5.1 证伪判据（观测结果 → 结论）

| # | 观测结果 | 结论 |
|---|---|---|
| F1a | 真实平面能力探测 `ctx.tools.guard` 恒不可达（自有行激活期内），且宿主一手文档无替代注册原语 | 宿主级接线不可行（**注册面证伪**） |
| F1b | guard **可达但读不到调用参数**（V0 探明①失败——锚载体前提崩塌；R1 增，R0 审查 D1） | **锚协议证伪**（deny 原语仍在而锚协议失败，与 F1a 不同结论）。分支处置裁定（按可用面降级序）：① 若 deny reason 面可附参数摘要（**该附件能力本身未证实——dsh-tools L126 仅证实 ToolErrorInfo 可附，参数摘要形态未文档化，实施时验证；N3 标注**） → 锚改载于拒绝反馈流重裁（后续批）；② 否则降级为**工具名级判定**（仅按工具面+治理态全局开关拒派发，无 per-call 修订判定力——能力面大幅收窄，须重新审查）；③ 均不可行 → 「宿主级可达但治理语义不可判」证伪留锚（§5.2） |
| F2 | guard 判定 p95 > 10ms 或会话冷启动/工具循环可感知劣化（>10%），且缓存优化后仍超 | 架构可达但性能不可接受（**性能证伪**） |
| F3 | deny 后 reason 不回传模型（模型不可见拒因）/ 被后续 listener 翻案（与 §1.4 L89 单调性矛盾）/ 调用静默重试不受限 | 拦截语义无效（**语义证伪**） |
| F4 | 自有行内注册 guard 破坏宿主 boot / bundle 加载被宿主拒绝 | 接线通道不可行（**通道证伪**） |
| — | F1a/F1b/F2-F4 均未出现且 V0-V8 全过 | U1 证实（最小切片范围内） |

### 5.2 证伪留锚的记录形态

1. 调研文档 §7 U1 行状态翻转：`未证实（架构可达）` → `已证伪（F#）/已证实（最小切片）` + 证据链接（该文档是 U1 清单的事实源，I1 L221）。
2. 本设计文档追加「§8 PoC 结论」段（结论 + 观测数据 + 证伪类型）。
3. `.governance/evidence-log.md` EVD + incidents log（Coordinator 机录；FEAT-095 先例 `.governance/incidents/FEAT-095-validation.log`，I1 L289）。
4. U7 行同步更新（对抗面结论）。

### 5.3 降级披露口径更新点（随结论翻新）

| 更新点 | 证实时 | 证伪时 |
|---|---|---|
| SKILL.md L238 | 「仅协议+CLI执法，未接线宿主拦截」→「dsh 平台边界①②修订错配已宿主级接线（PoC 证实；范围=guard 面一类，A1-A3 逃逸面披露）；其余边界/平台仍协议级+CLI 级」 | 维持原文 + 追加「宿主级已证伪（F#，日期）」 |
| adapters/dsh/adapter-manifest.json runtime_capabilities | **新增 `enforcement` 能力键**（调研 §8.3 L256 许可条件达成）带证据与 verified_on | 不加键 |
| adapters/dsh/host-contract.json own.host_row | 新增 enforcement_guard 子块（§3a） | 不改（或仅登记证伪注记） |
| adapters/dsh/README.md L59-69 能力边界段 | 增补宿主执法条目（含范围与逃逸面） | 增补证伪披露 |
| enforcement.py 模块 docstring L38-42 / SKILL 动作级执法段 | 措辞收窄至「dsh 边界①②除外」 | 维持 |
| **guard 注册窗口期**（R1 增，R0 审查 D4） | 措辞含「boot 起至 guard 注册完成存在已知执法空窗（时长=V8 实测值）」——写入 SKILL 动作级执法段与 README 能力边界 | 同左（窗口期披露与结论正交，两种结论下均须披露） |
| behavior-contract-details.md §enforcement / references | 同步两侧措辞（两面锚点一致性由守护测试机守，I1 L286） | 同步证伪结论 |

---

## 6. 实施切片（Governance Developer 步骤清单——每步可验证）

> 隔离环境约束（全程）：**不碰真实 DSH_HOME**（一切安装/冒烟经显式重定向 `DSH_HOME=<临时目录>`，先例 `test_smoke_cli_refuses_unredirected_dsh_home`）；`D:\app\dsh` 与 npm 安装面只读参考；测试治理面全部在临时项目 fixture；git 操作由 Coordinator 收口（Developer 零 git）。

| 步骤 | 内容 | 可验证判据 |
|---|---|---|
| S1 | ① **Python 投影扩展（R1 增，D2 裁定 (b)）**：`enforcement.py _strategy_public()` 增列 `hard_block_rules[].{reason, remedy}` 模板（数据投影面小改，判定语义零改动，既有测试零退化）；② 策略投影 fixture（`--print-strategy` 构建期生成）+ `lib/dsh-native/guard.js` 判定器（锚解析/revision-mismatch/无锚/开关；纯函数零宿主依赖） | node 单测绿；**JS×Python 判定 parity 测试**（同 facts 集 vs `enforcement.py decide()` 输出一致）绿；**投影字节断言**（fixture 与 `--print-strategy` 当前 stdout 逐字节相等，R0 审查 D8）绿；enforcement.py 既有测试族零退化 |
| S2 | 治理态缓存层（stat 指纹 + TTL + 开关敏感；§3b 缓存键/失效条件逐条实现） | 单测：mtime/size 变化即失效、TTL 过期失效、开关变化失效、Windows mtime 粒度容忍用例绿 |
| S3 | host row 接线：`apply()` 内能力检测（`ctx?.tools?.guard` 函数性检查）+ inject 模式注册（bridge.js L183-211 先例）+ 注册失败 warn 降级 + off 零注册；**注册完成时间戳落日志（V8 观测锚）** | 既有 dsh 族测试全绿（test_dsh_adapter / test_dsh_native_bridge 零退化）；新增注册成功/能力缺失降级/off 零注册三用例绿 |
| S4 | 隔离 E2E（§4.1 **V0-V8** 全步骤：真实 dsh 平面 + 重定向 DSH_HOME + 临时项目 fixture；V0 探明先行，F1b 触发时按 §5.1 分支裁定中止或降级重审） | V0 三项探明记录在案；V1-V6/V8 判据逐条满足；轨迹/日志证据采集 |
| S5 | U7 对抗注入矩阵（§4.2 A1-A4） | 逃逸面清单（通道×结果×严重度）落盘 `docs/` 或测试 fixture 报告 |
| S6 | dsh-doctor S0-S7 全阶段（隔离重定向环境；无 --record-evidence） | exit 0 或 NOT_RUN 披露面符合预期；**零 stage 回归** |
| S7 | 披露面更新（§5.3 表：SKILL/manifest/README/host-contract + enforcement docstring）+ `implementation_authorized` 翻转链 | check-projection-sync / check-manifest-consistency / check-agent-adapters / check-cross-references 全 PASS；两面锚点一致性守护测试绿 |
| S8 | 全套件回归 | 全套件零退化（FEAT-095 先例口径：20 用例族 + 全量，I1 L289） |

**依赖顺序**：S1→S2→S3 严格串行（每步是下步的构件）；S4 依赖 S3；S5/S6 依赖 S4；S7 依赖 S4-S6 结论（措辞随结论）；S8 收口。

---

## 7. 六节完整性自检表

| 要求节 | 状态 | 承载段 |
|---|---|---|
| 1 现状锚定（路径+行号逐条） | ✅ | §1.1-§1.5（enforcement.py / host-contract / lib/index.js / DSH 原语+参数面前提未证实标注 / 披露面） |
| 2 PoC 范围裁定（一类拦截 + 不做面） | ✅ | §2.1（subagent/subagent_fork 修订错配 + expected 派生源指认 observed_revision）/§2.2 |
| 3 三项前置裁定（DEC 草案/性能/fail-closed） | ✅ | §3a（七要点含窗口期定性）/§3b（缓存键+失效条件+投影扩展裁定 (b)）/§3c（C0/C6a/C6b 分流规格） |
| 4 验证方法（验收构造/U7 对抗/dsh-doctor） | ✅ | §4.1 V0-V8（含参数面探明与窗口期时序观测）/§4.2 A1-A4/§4.3 |
| 5 证伪路径（判据/留锚/披露更新点） | ✅ | §5.1 F1a/F1b/F2-F4/§5.2/§5.3（含窗口期披露行） |
| 6 实施切片（步骤可验证+隔离约束） | ✅ | §6 S1-S8 |

- 唯一写面自检：本文档为本任务唯一落盘产物；未改产品代码 / 未写 `.governance/` / 零 git 操作 / DSH 安装态只读（R1 修订同样仅落本文档）。
- 未证实面如实标注：**guard 回调可读调用参数（§1.4①，锚载体前提，V0 探明）**、guard 回调上下文面（§3b）、第三方包注册实机行为（§1.4）、每调用开销（§1.4）、expected_revision 生产源（§2.1 裁定 fixture + observed_revision 派生源已指认）。
- R1 修订闭环自检：D1（§1.4①+§2.1 前提句+V0+F1b）/ D2（§3b 裁定 (b)+S1①+字节断言）/ D3（C6a/C6b 分流+V3）/ D4（C0+V8+§3a-7+§5.3 行）/ D5（§2.1 派生源指认）/ D6（§1.3 节号）/ D7（§3a-7）/ D8（S1 字节断言）——逐条对 R0 审查报告修复要求闭环。

---

## 8. 实施授权请求（implementation request）

- **implementation_authorized = true**（2026-10-27 翻转——REVIEW-FEAT-099-R1 delta 复审 APPROVED_WITH_NOTES/unresolved_blockers=0〔report b7e9d71b…，txn-147ee345，RECHECK-FEAT-099-R1 cleared〕；授权前置项 1~6 已由 R1 复审逐项核验〔报告「审查重点回应」节〕）
- 授权前置项（审查重点，R1 复审已核验——保留原文供追溯）：
  1. §2.1 锚协议与「无锚 allow」取舍（误伤面 vs 对抗缺口的裁定是否接受）；
  2. §2.1 expected_revision 治理源：PoC fixture 方案 + observed_revision 派生源指认与切换点（R1 已补，R0 审查 D5）是否成立；
  3. §3a warn_only 语义收窄 + native face 三服务边界修订 + 窗口期定性（DEC 草案七要点是否完备，DEC 入账归 Coordinator）；
  4. §3b 热路径单源边界认定（guard 为机器组件直读治理面文件+缓存，不构成 agent 直读热面违规——该认定需审查确认）+ 投影扩展裁定 (b)（Python 面数据投影小改随 PoC 实施，R0 审查 D2）是否接受；
  5. ~~§3c C6 与 fail-closed 总则的张力~~（R1 已由 D3 修订消解：C6a/C6b 按锚分流——无锚 allow+披露、带锚 deny；残留审查点 = 该分流本身是否成立）；
  6. §5.1 F1b 分支处置序（deny reason 面参数摘要 → 工具名级判定降级 → 证伪留锚，R0 审查 D1）是否接受。
