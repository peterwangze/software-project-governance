# FEAT-103 R2 修订版 + R3/R4/R5/R6/R7/R8 增量：DSH 调用方注册终态撤销与会话发布校验隔离补丁设计（R0 三 finding 闭环 → R1 F1–F4 → R3 S-C7 谓词更正 → R4 合同增量 → R5 M3 实施对齐收敛 → R6 合入前文本批 → R7 M4 后终态回写 → R8 M5 后最终回写；重锚 0.2.1-rc.2）

- 日期：2026-10-20（R2 基线，Asia/Shanghai）；**R3 增量 2026-10-21、R4 增量 2026-10-22、R5 增量 2026-10-22、R6 增量 2026-10-22、R7 增量 2026-10-22、R8 增量 2026-10-23**（与 §11 `design_revision=R8` 一致）；R1 取证 UTC 09:15:35Z–09:22:00Z（逐条见 §12 R1 表）；R2 事实复核为 2026-10-20 本会话对 SDK 的只读 Read×4（cordis 四窗口，逐条见 §12 R2 表——Architect 角色无 Bash 权限，无命令级 UTC 时戳，如实声明不编造）。角色：Architect；规范：`agents/architect.md`、`skills/stage-architecture/SKILL.md`。
- 输入：R0 独立审查 `docs/reviews/review-FEAT-103-DESIGN-R0.md`（immutable，三 BLOCKING finding B1–B3）；**R1 独立审查 `docs/reviews/review-FEAT-103-DESIGN-R1.md`（immutable，结论 NEEDS_CHANGE：F1 BLOCKING/P1 + F2 P2 + F3/F4 P3——本 R2 的修订依据）**；原设计 `docs/architecture/dsh-upstream-owned-registration.md`（immutable，基线 0.2.0-rc.2，不修改）；`docs/architecture/dsh-adapter-version-decoupling.md`（§15 U 协议）；`docs/research/dsh-0.2-upgrade-decoupling.md`。
- 本文件性质：**R2 修订版 + R3/R4/R5/R6/R7 增量**（文件名沿用 R1 路径——任务指定的原地修订唯一写面）。R2 对 R1 做**局部修订**：F1 多值 owner 索引（§3.3/§8/§9）+ F2 S-C8 事实更正（§2.3/§9）+ F3 措辞澄清（§5.5）+ F4 观测行（§8）；**R3**=S-C7 谓词更正与 M1 实施反馈（§3.3/§11.1）；**R4**=closedIds 墓碑合同（§5.6）/fallback 冻结 generation（§5.3）/activation-failed 终态（CH-1.6）/M2 API 契约（§5.4/§6.1）/错误码映射（§5.3）；**R5**=M3 实施对齐收敛（依据 M3-REPORT §6 F-M3-1~4：§4.4 消费原语映射注记〔attach ≡ mountOwned/composeFromOwned〕/§4.2 继承冻结合同锚点裁定〔materializeTracked 编排入口〕与 cold 面错误合同区分/§4.2 selector 记法对齐实现 API〔acquire 无 signal 参〕/§5.4·§5.6 状态行更新至 M3 后事实；§11 交接状态回写）；**R6**=合入前文本批（依据 REVIEW-FEAT-103-R11〔AWN/0〕2×P3 备注：§5.4 acquire 形态衔接半句〔R6-P3-1〕/§4.2"首次可行动"修辞替换为编排入口事实表述〔R6-P3-2〕/§11 R11 复核状态回写与 design_revision=R6）；**R7**=M4 后终态回写批（依据 REVIEW-FEAT-103-R13〔AWN/0〕R7-P3-1 三处状态滞后：§11 implementation_progress 补 M4 done/§5.4 rebind 抛错分支闭合〔M4-2〕/§5.6 legacy 分类面部分闭合〔M4-1，default/list 由 M5 终态批补齐在途〕+ design_revision=R7）；**R8**=M5 后最终回写批（依据 M5-REPORT〔微批修复闭环版〕：§5.6 legacy default/list 闭合〔M5-3〕/§8 T09+ 补实现面锚注〔claim live 短路=composeAgent 前跳过 resolve，M5 微批 controller +9/−0 后 3/3 PASS〕/§11 implementation_progress 补 M5 done〔含 KNOWN-GAP 归因→裁定 b 方向 1 修复闭环〕/§16 NOT_RUN 清单两条闭环+剩余 5 条+ design_revision=R8）；R0 B1/B2/B3 闭环面、D1–D3 保留面、§4/§5.3/§5.4 分支合同除本段所列 R5/R6 注记/裁定点外零改动（R4-P2 已批五项修正零回退）。**取代原设计的 §3（owner 触发部分）、§4.1（consumer 表）、§5.1（owner→close 行）、§7（补丁文件面）、§8（测试表增补）**；原设计 D1 fence 位置、D2 P/C/R 分支、D3 终态/兼容表、§4.2/§4.3 持久化 gap 处置在本 R2 中继续有效，仅重锚调用点行号。原设计、R0 报告与 R1 报告零修改。
- 基线：本机实际安装已升级为**完整同代 0.2.1-rc.2**（DSH/registry/agent/agent-loop/scope/session-controller/subagent/subagent-spawn-in-process/subagent-fork-in-process/session/session-persistence/app-boot 均 0.2.1-rc.2；Cordis 4.0.5；Loader 1.0.6；host `@deepseek-ai/dsh` 0.2.1-rc.2）。旧 `dsh-subagent-in-process-driver` 与 `dsh-webhook` 不在当前安装（§2.2）。**本 R1 的所有 SDK 引用均按 0.2.1-rc.2 只读核实，不按 0.2.0 调用点照抄。**
- 写面：仅本文件。SDK 严格只读（未运行、未 probe、未安装、未写用户环境、未改治理记录）。
- 标签：**SOURCE**=本次对安装态 0.2.1-rc.2 的直接只读核实（路径+行号+签名）；**PROPOSED**=供审查裁决的新接口/算法（当前 SDK 不存在）；**NOT_RUN**=无实现/运行证据。三类不混写。

## 1. R0 响应总表

| R0 finding | 结论摘要 | R1 变更点 | 章节 |
|---|---|---|---|
| R0-B1 LOADING owner 的 dispose 起点没有连接到 record close | 采纳。原设计只依赖 owner effect（在 `_unload` 才运行），LOADING owner await `lease.ready` 时形成等待环 | CH-1.1 registry 级 `internal/plugin` dispose-start 观察者（公开事件，SOURCE 已核实同步发射点与监听存活语义）；CH-1.2 无 race 插入/复核序列；CH-1.3 owner effect 降级为幂等兜底；CH-1.4 registry-disposed/root-owner 映射；CH-1.5 反例合同保持为硬验收 | §3 |
| R0-B2 独立 child preset / cold resume 会被统一父 selector 改错 | 采纳。`ChildComposition.agentPreset` 有值=独立选择，无值=继承父 revision；统一取父违反现有语义 | CH-2.1 selector 分支冻结（独立/cold 独立→按 id 精确 reservation；省略→父实际 generation）；CH-2.2 禁止父 token 替换独立选择；CH-2.3 父 owned generation 关闭后新 child 拒收规则按分支承接；CH-2.4 helper 公开返回类型与 setup hook 传递更新；补丁地图改共享 `packages/subagent/subagent`，provider 只读核兼容 | §4 |
| R0-B3 Web claim/live-reuse/fallback 不满足单次 token 完整所有权合同 | 采纳。`claim`/`reuseLive`/fallback 新分支无 lease 生命周期定义 | CH-3.1 admission 获取移出 `composeAgent`；CH-3.2 分支级 operation/factory-attempt 双生命周期合同；CH-3.3 live-switch 冻结 reservation 的 SDK 内部事务（消除 :757 按 id 重解析）；CH-3.4 失败分类（未 attach 可复用/已消费须新取、关闭即失败不换代）；CH-3.5 `reuseSetup` 返回完整 commit；CH-3.6 每出口 P/C/R/监听归零断言 | §5 |

R0 已认定方向无阻断的 D1（最终 publication fence）、D2（旧 committed 保留/新 admission 隔离）、D3（终态/旧 register 兼容）在 R1 中保留并重锚（§6）。**本 R1 不以延长 timeout、"最终清理抵销"、先 release barrier 帮助通过等方式回避任何 R0 反例（验收标准⑤，§11）。**

### 1.1 R1 审查响应总表（本 R2 的修订范围）

R1 审查（`review-FEAT-103-DESIGN-R1.md`）裁定 R0-B1/B2/B3 全部真实闭环（无需重开），新发现 F1–F4。逐条响应：

| R1 finding | 级别 | R2 响应 | 落地章节 |
|---|---|---|---|
| F1 `WeakMap<Fiber, OwnedRecord>` 单值映射不能表达"同一 owner fiber 多次 beginRegistration"的合同合法输入（原设计 :70-71/:192）——第二次 `set` 覆盖第一条 → teardown 只 close 最后一条 → 被覆盖 record 退化为 owner effect 兜底（R0-B1 等待环对该 record 复活）；tombstone 删 WeakMap 条目还连带删同 fiber 兄弟映射 | BLOCKING/P1 | 采纳，选定最小解除方案 **(a) 多值索引**（审查推荐；本 R2 未取得反驳证据）：`ownedByFiber` 改 `WeakMap<Fiber, Set<OwnedRecord>>` 与 id 主表联动；listener 依序 close 集合内全部 record（每 record first-reason-wins/幂等）；CH-1.2 步骤 6 按 record 精确移除集合成员；T01+ 增"同 owner 双 record"反例行。方案 (b)（显式单 record/owner 合同 + 新错误码）的排除理由见 §10 R2 增量 | §3.3 CH-1.1/CH-1.2/CH-1.3/CH-1.5、§7、§8 T01+、§9、§10 |
| F2 S-C8 事实错误——:1093 创建发射实际 `thisArg=null` **无 scope 过滤**（emit 的 thisArg 须为首个 object 参数，此处首参是事件名字符串），非"带 thisArg（经 scope 过滤）" | P2 | 采纳。S-C8 行更正（创建/销毁发射同路径，判别只靠 uid；本 R2 对 SDK 只读复核在案：dispatch :258-264 / emit :280-282 / :1093，§12 R2 表）；§9 性能行补发射次数说明。uid 判别式与 CH-1.1 早退不受影响 | §2.3 S-C8、§9 |
| F3 §5.5 ":488 保持 setup 内 append"措辞不精确——:488 实际在 `reuseSetup` 包装器内、`composition.setup`（:486）返回之后 | P3 | 采纳，措辞澄清（实质语义不变：仍为 pre-publication append） | §5.5 |
| F4 T01+ 缺 root-owner→registry-disposed 映射观测行 | P3 | 采纳，T01+ 增补观测行（CH-1.4 合同性声明的可观测验收） | §8 T01+ |

R1 审查同时确认不构成架构否决：B1-A/B2/B3 方向、D1–D3 保留面、补丁地图、测试合同框架均成立——本 R2 为局部修订，不重开方向讨论。

## 2. 基线重锚：0.2.1-rc.2 SOURCE 事实

### 2.1 版本与目录锚（SOURCE，UTC 09:15:46Z）

令 N=`C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai`。各 `package.json` 的 `version` 与 `repository.directory`：

| 包 | 版本 | repository.directory |
|---|---|---|
| N/dsh-agent-preset-registry | 0.2.1-rc.2 | packages/preset/agent-preset-registry |
| N/dsh-agent-loop | 0.2.1-rc.2 | packages/core/agent-loop |
| N/dsh-agent | 0.2.1-rc.2 | packages/core/agent |
| N/dsh-scope | 0.2.1-rc.2 | packages/core/scope |
| N/dsh-api-session-controller | 0.2.1-rc.2 | packages/api/session-controller |
| N/dsh-subagent | 0.2.1-rc.2 | packages/subagent/subagent |
| N/dsh-subagent-spawn-in-process | 0.2.1-rc.2 | packages/subagent/subagent-spawn-in-process |
| N/dsh-subagent-fork-in-process | 0.2.1-rc.2 | packages/subagent/subagent-fork-in-process |
| N/dsh-session / N/dsh-session-persistence / N/dsh-app-boot | 0.2.1-rc.2 | packages/core/session / packages/session/session-persistence / packages/boot/app-boot |
| N/cordis / N/cordis-plugin-loader | 4.0.5 / 1.0.6 | vendor/cordis / vendor/loader |
| host @deepseek-ai/dsh | 0.2.1-rc.2 | — |

### 2.2 相对 0.2.0 设计基线的结构变化（SOURCE，UTC 09:15:35Z ls）

- `dsh-subagent-in-process-driver` **不在** N 下（原设计 §4.1 的 startInProcessRun 消费点消失）；child 创建/resume 统一在共享 `dsh-subagent`（materialize :1672 / materializeTracked :1764，本地分支 :1794-1824），spawn/fork 只提供 capabilities/seed。
- `dsh-webhook` **不在** N 下（原设计 §4.1 webhook 消费点消失）。当前匹配源码未取得；旧 0.2.0 快照仅历史证据，不声称 current 已覆盖（§6.1、§7）。
- controller 新增 `claim`/`reuseLive`/`reuseSetup`/`inOrder`（§2.3-6）；旧 `createOrAdopt` 不存在。
- Cordis 4.0.5 与 0.2.0 期相同（R0 §2 已核 hash；本 R1 用到的事实全部在当前安装直接复核，§3.2）。

### 2.3 R1 载荷事实清单（SOURCE，逐条路径+行号+签名）

**Cordis（vendor/cordis，B1/D2 载荷）**

| # | 位置 | 事实 |
|---|---|---|
| S-C1 | N/cordis/lib/types/events.d.ts:216-218 | 公开事件类型 `'internal/plugin'(fiber: Fiber): void`，注释："A plugin fiber was created **or its uid was cleared on disposal**"——创建与销毁同用本事件，判别式为 fiber.uid。 |
| S-C2 | N/cordis/lib/index.js:968-984 | `emitPluginDisposed(context, fiber)`：`args=["internal/plugin", fiber]`，`context.events.dispatch("emit", args)` 同步求值回调表并逐个同步调用；per-callback try/catch + 返回 Promise 的 rejection 被消费（仅记日志）；dispatch 抛错也被捕获。监听者异常不破坏 dispose。 |
| S-C3 | N/cordis/lib/index.js:258-264 | `dispatch`：`args[0]` 为字符串事件名 → `thisArg=null` → `filter=undefined` → `!filter` 短路 → **该事件名的全部存活 hook 都收到，无 scope 过滤**；且 `internal/` 前缀不重发 `internal/dispatch`（:261）。 |
| S-C4 | N/cordis/lib/index.js:1075-1091 | Fiber.dispose 闭包顺序：`this.uid=null`（:1078）→ `emitPluginDisposed`（:1079，**同步，先于任何 await**）→ registry fibers 移除（:1080-1083）→ `_setEpoch(INACTIVE)`（:1084）→ `if (!this.inertia) this.inertia = this._unload()`（:1085-1088）→ `while (this.inertia) await this.inertia`（:1089）。**effects（含 plugin cleanup）只在 `_unload` 运行，即当前 inertia（含 loading）落定之后**——LOADING owner 等待环的源码依据。 |
| S-C5 | N/cordis/lib/index.js:1372-1392 | `_unload()` 运行 `this._disposables.clear()` 的全部 effect。 |
| S-C6 | N/cordis/lib/index.js:335-345, 371-380 | `EventsService.on(name, listener, options)`：先 `this.ctx.fiber.assertActive()`（已 dispose 抛 `CordisError('INACTIVE_EFFECT')`），hook 经 `this.ctx.fiber.effect(...)` 存为**注册者 fiber** 的 effect——监听者随注册 fiber 卸载自动移除（存活语义）。 |
| S-C7 | N/cordis/lib/index.js:1687 | root Context 构造器 `this.events = new EventsService(self)`；子 context 经 `extend()`（:1704+）原型继承——**每 root 单一 hook 表**，registry 注册的监听可收到任意后代 fiber 的 teardown 发射。 |
| S-C8 | N/cordis/lib/index.js:1093（路径经 :280-282 `emit` → :258-264 `dispatch`，R2 复核） | 创建发射 `this.context.emit("internal/plugin", this)`：`emit(...args)`（:280-282）把 args=["internal/plugin", fiber] 传入 `dispatch("emit", args)`，dispatch 仅在 args[0] 为 object/function 时取 thisArg（:259）——**args[0] 是事件名字符串 → thisArg=null、filter=undefined、无 scope 过滤，与 S-C4 teardown 发射同一路径**；fiber 是载荷参数而非 thisArg。此时 `fiber.uid` 非 null——**创建/销毁两类发射的判别只靠 uid**，CH-1.1 的 `if (fiber.uid !== null) return` 早退正确过滤创建发射。（R1 版此行曾误记"带 thisArg（经 scope 过滤）"，R2 更正——R1 审查 F2。）另注：创建发射经 `emit`（:280-282）**无 per-callback try/catch**，监听者异常传播至 :1094 catch 触发该 fiber dispose 并重抛——CH-1.1 监听者在创建发射路径只执行 uid 早退、不抛，其失败遏制依赖的 per-callback 捕获仅在 teardown 发射（S-C2）存在且充分。 |
| S-C9 | N/cordis/lib/index.js:1102-1113 | root fiber 分支：`uid=0`、`dispose=()=>this.restart()`——**root fiber 自身无 internal/plugin teardown 发射**（B1 的 root-owner 映射见 §3.3-CH1.4）。 |
| S-C10 | N/cordis/lib/types/registry.d.ts:83-92 | `Plugin.Runtime.fibers: DisposableList<Fiber>` 公开；`Fiber.parent/uid` 公开（原设计 D2 fence 的 census 面继续有效）。 |

**Registry（packages/preset/agent-preset-registry）**

| # | 位置 | 事实 |
|---|---|---|
| S-R1 | N/dsh-agent-preset-registry/lib/index.js:470-494 | `register(definition)` 同步插 record → `record.ready=this.activate(record)` → `await record.ready` 才返 disposer（晚 disposer 形态不变）。 |
| S-R2 | :495-521 | `activate`：`createScope(this.owner,key)`；`generation={scope,key,mount:await mountPreset(...),users:0,retired:false}`——`await mountPreset` 即 payload activation barrier 点。 |
| S-R3 | :533-543 | `diagnostic` `await record.ready`；pending 行回退 `await this.owner.loader.await()`（自等待链保留）。 |
| S-R4 | :632-652 | `retain(id)`：`await diagnostic` 后 `if (this.definitions.get(wanted)!==record) continue` ——**await 后按 id 重试**，是按 id 换代窗口（原设计 snapshot-token 规则的针对点）。 |
| S-R5 | :654-680 | `bind`（rebind：`binding.parent.rebind`、users++/old.users--、`await this.collect(old)`）与 `join`（agent scope effect 释放时 users--/collect）。 |
| S-R6 | :686-795 | `mount(ctx,id)`：retain→bind→finally users--/collect；`composeFrom(ctx,parent)`（:701-712）：`generationFor(parent)` 精确父 generation，无 token，返回 `generation.mount.presetId` 字符串；父 revision 不可用抛 "Parent preset revision is unavailable"；`acquireScope(id)`（:775-787）读 lease（retain + asyncDispose 减计数）。 |
| S-R7 | :750-770 | `select(agent, agentPreset)`：per-agent 串行链（`this.switches`）；blank 校验（:752-756）；**:757 `this.definitions.get(agentPreset)?.generation` 按 id 重解析**；:759 `await this.recompose(...)`；**:760 `agent.session.append("agent-preset/selected",...)` 在 rebind 之后**——append/observer 抛错时存在半绑定窗口（B3 事务针对点）。 |

**Controller（packages/api/session-controller，B3 载荷）**

| # | 位置 | 事实 |
|---|---|---|
| S-T1 | N/dsh-api-session-controller/lib/index.js:351-364 | `composeAgent(presetId)`：`await presets.resolve(presetId)` 得 `resolvedId`，返回 `{agentPreset, setup: async(agentCtx,agent)=>{installSelection; await presets.mount(agentCtx,resolvedId)}}`——**无 token**；setup 内 await mount。 |
| S-T2 | :405-414 | `inOrder(sessionId, op)`：per-session 串行 claims 链。 |
| S-T3 | :416-465 | `claim(sessionId,request)`：live 存在 → `composeAgent`（:422）→ `reuseLive(...) ?? createMinted(...)`（:423）；observed 不存在 → `createAgent`（:430）；`reusable = request.reusable && 无 turn/start`（:443）；`composeAgent`（:451）；!reusable → `createMinted`（:452）；reusable → `agents.resume({setup: this.reuseSetup(composition)})`（:455-459）；catch：`ApiSessionStartedSinceObserved` → `createMinted(cwd, composition)`（**:461 重用同一 composition**）；`SessionAlreadyOwnedError` 且无 live → `createMinted`（:463a），有 live → **`this.claim(sessionId,request)` 递归**（:463b）。 |
| S-T4 | :467-481 | `reuseLive(live,request,composition)`：不可复用/非 blank → undefined；**:473 同 preset（`target===current` 或无 presets/无 target）直接 `return live`——零 factory**；否则 :475 `await presets.select(live,target)`；`agent-preset/locked` → undefined（落 createMinted），其它错误重抛。 |
| S-T5 | :483-491 | `reuseSetup(composition)`：**先 blank 复查（:485，不 blank 抛 StartedSinceObserved）后 `commit = await composition.setup(...)`（:486）**；目标变化则 :488 `agent.session.append("agent-preset/selected",...)`（setup 内 append，先于 old commit）；返回 commit——**实际 hook 包装点**。 |
| S-T6 | :849-905 | `fork(request)`：observe → `buildForkSeed` → workspace → **:880 `composeAgent(presetForObservation(source))`** → :883-898 `agents.create({seed, inheritedEventCount, meta:{...agentPreset}, setup})`；:902-908 workspace attach 失败发生在 create 成功之后。 |
| S-T7 | :508-526 | `createAgent`：`await mkdir` 后 `agents.create({meta:{cwd, agentPreset}, setup})`。 |

**Subagent（packages/subagent/subagent，B2 载荷）**

| # | 位置 | 事实 |
|---|---|---|
| S-U1 | N/dsh-subagent/lib/types/child-agent.d.ts:66-74 | `ChildComposition { agentPreset?: string; persona?; toolFilter? }`，注释："**Independently mounted preset; omission shares the parent's standing generation**"。 |
| S-U2 | N/dsh-subagent/lib/index.js:373-383 | `applyChildComposition(childCtx,parent,composition)`：**`agentPreset!==void 0` → `presets.mount(childCtx, id).then(overrides)`（独立挂载）；省略 → `presets.composeFrom(childCtx, parent.ctx)`（同步继承父当前 generation）**；doc 注释："Registrations belong to the child's scope"。:384-396 overrides：delegation context/persona/toolFilter。 |
| S-U3 | :398-409 | `captureDelegatedPolicyOverrides(parent)`：要求"Call synchronously before the child start's first await"——父代策略快照的同步时点纪律（R1 沿用为继承分支 admission 冻结时点）。 |
| S-U4 | :1764-1824 | `materializeTracked` 本地分支 setup：**独立选择在 create 追加前**（:1797 `await applyChildComposition` → :1799 append `agent-preset/selected` → :1800 descriptor → :1801 policy → :1802-1804 workingDirectory）；**继承在追加后**（:1806）；:1807 structured runtime；:1809/:1815 `agents.resume`/`agents.create`（`parentAgent: parent`）。 |
| S-U5 | :2164-2183 | cold resume：`independentlySelected = hasIndependentPresetSelection(ownEvents)`；独立 → `agentPreset = source.projections?.values.agentPreset`，**无 projection 抛 NOT_RESUMABLE**；`materialize({composition:{agentPreset: agentPreset ?? void 0, persona, toolFilter}})`。 |
| S-U6 | :2258-2265 | `hasIndependentPresetSelection(events)`：own events 中 `agent-preset/selected` 先于 `subagent/descriptor` 即独立。 |
| S-U7 | N/dsh-subagent-spawn-in-process/lib/index.js:19-34 | spawn provider：`capabilities={agentOptions:true, agentPreset:true, outputSchema:true, depthLimit:true}`，`inheritsParentContext=false`。 |
| S-U8 | N/dsh-subagent-fork-in-process/lib/index.js:33-48 | fork provider：`capabilities={..., agentPreset:false, ...}`，`inheritsParentContext=true`，`prepareContinuable` 供父 log seed。 |

**AgentLoop / Agent / Session / Scope / Persistence（D1–D3 载荷）**

| # | 位置 | 事实 |
|---|---|---|
| S-L1 | N/dsh-agent-loop/lib/index.js:1786-1804 | `prepare().publish`：:1789 `assertLive()` → :1790 `sessions.enter(session)` → :1791 `agents.enter(agent,parentAgent)` → :1792 announce → **:1794 首个 await**。两个 enter 同步（S-S1）。**最终 fence 插入点= :1789 之后、:1790 之前。** |
| S-L2 | :1915-1941 | `setupAndPublish`：:1931 `(await raceAbort(setup?.(...)))?.commit()`（old commit 恰一次，在 append 前）→ :1932 `await this.appendUnstoredSuffix(stored,session)`（持久化 await）→ :1933 `return await prepared.publish(source)`——**publish 未接收 finalizer，gap 仍在**（与 0.2.0 相同）。 |
| S-L3 | :1942-1956 | `initializeAgent`：失败路径 `prepared.dispose()`（handle.close 链保留）。 |
| S-A1 | N/dsh-agent/lib/types/index.d.ts:27-33, 40 | `AgentSetupCommit { commit(): void }` **仅有同步 commit**；`AgentSetup` 返回 `AgentSetupCommit | Promise<AgentSetupCommit | void> | void`；CreateAgentOptions.meta 含 `agentPreset?: string`（:70，durable 元数据）。 |
| S-S1 | N/dsh-session/lib/index.js:1853-1883 | `enter(session)` 同步写 store、抛重复、返回精确 detach；无创建事件。:1579-1598 `commit(event,entry)`：`validateNext` + appending 标志 + contained observers——**append/observer 可抛错**（B3 事务必须处理）。 |
| S-S2 | N/dsh-scope/lib/index.js:282-305 | `quiesceFiber`：`await fiber.dispose(); while (fiber.inertia!==void 0) await fiber.inertia`——scope 只跟自身 fiber，不能当代后代同步 fence（D2 公开 fence 候选不变）。 |
| S-P1 | N/dsh-session-persistence/lib/types/handle.d.ts:52-106 | append-only；`flush` durability barrier；`close()` 幂等不可取消、write handle 释放 ownership；**无通用 delete/rollback**（§6 D1 gap 处置不变）。 |

## 3. B1 修订：LOADING owner 的 dispose 起点同步观察与 record close（CH-1）

### 3.1 R0 反例与原设计缺陷（复述）

owner initializer 调 `beginRegistration` 后 `await lease.ready`；payload 持 activation barrier；owner `Fiber.dispose` 清 uid 后等该 initializer 的 loading inertia（S-C4 :1089）；owner cleanup effects 在 `_unload`（:1085-1088 / S-C5）才运行——即 initializer 返回之后；而 initializer 等 `lease.ready`，record close 又依赖 owner effect → **等待环**：owner dispose 等 ready，ready 等 owner effect，owner effect 等 dispose 完成。原设计 §3/§5.1 未指定 activation pending 时哪个**同步公开触发器**先调用 close——R0-B1 成立。

### 3.2 机制选型（候选 ≥2，先定标准）

标准（按序）：dispose 起点同步可达（先于任何 inertia await）→ 只用公开面（无核心修改）→ 监听存活/过滤语义确定 → 无每 record 订阅泄漏 → 修改量。

| 候选 | 机制 | 裁定 |
|---|---|---|
| **B1-A（选定）** registry 级 `internal/plugin` dispose-start 观察者 | registry 服务激活时注册一个 `ctx.on('internal/plugin', ...)`；teardown 发射（S-C2/S-C4）在 uid 清除后、任何 inertia await 前同步送达（S-C3 无 scope 过滤）；按 Fiber 对象身份匹配 owned record 并同步 close | 全部标准满足；S-C1–S-C8 已逐条源码核实；运行验证仍 NOT_RUN（§8） |
| B1-B 禁止 owner 在 initializer 中 await ready（API 合同） | 把"owner 不得 await lease.ready"定为可执法合同，owner 必须先完成 activation 再 begin | **排除**：与用户取消目标相悖（升级/卸载窗口正是 LOADING 期）；R0 明确该路线须"保持用户原取消目标"，实际是把反例推出合同而非解决；且无法执法于第三方插件 owner |
| B1-C Cordis 核心新增显式 owner-teardown 回调 | 在 Fiber.dispose 增设 registry 可订阅的专用同步回调 | **排除**：B1-A 已覆盖所需语义，无需预批核心修改（R0 亦不要求）；仅作为 B1-A 被运行证伪时的缺口声明（§3.6） |

### 3.3 PROPOSED 机制冻结（CH-1.1～CH-1.5）

**CH-1.1 dispose-start 观察者（registry 拥有）**。`AgentPresetRegistry` 服务激活（其自身 fiber 内）注册**单一**监听：

```ts
// PROPOSED — inside AgentPresetRegistry service activation
this.ctx.on('internal/plugin', (fiber: Fiber) => {
  if (fiber.uid !== null) return;              // S-C8（R2 更正）：创建发射过滤——判别只靠 uid（两类发射均 thisArg=null、无 scope 过滤）；teardown 发射时 uid 已清（S-C4 :1078→:1079）
  const owned = this.ownedByFiber.get(fiber);  // WeakMap<Fiber, Set<OwnedRecord>>（F1：多值 owner 索引），对象身份精确匹配
  if (owned !== undefined) for (const record of owned) record.close('owner-disposed'); // 依序 close 集合内全部 record；每 record first-reason-wins + 幂等
  if (fiber === this.ctx.fiber) this.closeAllOwned('registry-disposed');
});
```

- **多值 owner 索引（F1 修复）**：`ownedByFiber: WeakMap<Fiber, Set<OwnedRecord>>`，与 id 主表（definitions）联动。依据：原设计合同 `beginRegistration(definition, {owner, signal})`（原设计 :70-71）**没有**"同一 owner fiber 同时至多一条 owned record"的限制——DUPLICATE_ID 按 id 判（原设计 §3/§6.1）、同 id closed 后允许 new begin（原设计 :192）、不同 id 同 owner 是合同合法输入（当前生态 `dsh-agent-preset` 每插件实例一次 register 是常态形态，非合同约束）。R1 冻结的单值 `WeakMap<Fiber, OwnedRecord>` 在该输入下第二次 `set` 覆盖第一条 → teardown 发射只 close 最后一条 → 被覆盖 record 的 dispose-start 通知丢失、退化为 owner effect 兜底（S-C4/S-C5：effect 只在 inertia 落定后运行）→ **R0-B1 等待环对该 record 复活**；且其 tombstone 回收"删除 WeakMap 条目"连带删同 fiber 兄弟 record 的映射。多值索引下：listener 对集合内**全部** record 依序 close（每 record 独立 first-reason-wins、幂等、不抛）；集合在 close 期间不被修改（tombstone 回收按合同在 drain 完成且旧 readers 已终态之后——原设计 §6.1/§6.2，无需快照迭代）；owner fiber 被 GC 时整集合随之释放，不产生泄漏。
- **监听者所有权/存活**：hook 是 registry 服务 fiber 的 effect（S-C6），随 registry 卸载移除；对任意同 root 后代 owner fiber 的 teardown 发射都可达（S-C3+S-C7：teardown 发射 thisArg=null 不过滤 + 每 root 单一 hook 表）。
- **registry 自身卸载**：registry fiber teardown 发射（S-C4 :1079）先于其 `_unload`（:1085-1088）——此时自身监听**尚未被移除**，`fiber===this.ctx.fiber` 分支同步 `closeAllOwned('registry-disposed')`，不依赖 registry effect 的执行顺序。
- **失败遏制**：close 合同=同步、首次原因定终态、幂等、不抛（routine 错误进 consumed 诊断，沿用原设计 D3）；即使抛错，S-C2 的 per-callback try/catch 只记日志，不破坏其它监听与 dispose 进程。
- **重入**：重复 dispose → 重复发射 → 第二次 close 幂等 no-op；close 与 signal/显式 close 并发 → first-reason-wins（原设计 §6.1 已有，不变）。

**CH-1.2 无 race 插入序列**。`beginRegistration` 以下步骤**同步执行、步骤间无 await**（JS run-to-completion 保证无第三种交错）：

1. 输入校验（EMPTY_ID/DUPLICATE_ID/OWNER_ROOT_MISMATCH，原设计 §3 不变）。
2. owner 预检：`ownerCtx.fiber.uid !== null` 且 `ownerCtx.root === this.ctx.root`（同 root 判定用**公开 root 身份**；原 `events` 对象身份谓词已作废，见下方「S-C7 更正」）。
3. 安装 owner effect 兜底（CH-1.3）：`ownerCtx.effect(() => () => record.close('owner-disposed'))`——`INACTIVE_EFFECT` 抛出即 OWNER_INACTIVE，无任何分配。
4. 分配 record 并加入多值 owner 索引（F1）：`const owned = this.ownedByFiber.get(ownerFiber); owned !== undefined ? owned.add(record) : this.ownedByFiber.set(ownerFiber, new Set([record]))`——**不覆盖既有条目**，同 fiber 兄弟 record 的映射保持。
5. **插入后复核**：`if (ownerFiber.uid === null) record.close('owner-disposed')` ——覆盖"dispose 的发射发生在步骤 4 之前（record 尚未入集合，监听扑空）"的交错；此时 uid 必已为 null（S-C4 :1078 先于 :1079），close 立即执行。发射在步骤 4 之后 → 监听命中并 close 集合内全部 record（含本条）。**不存在发射与插入之间的窗口**（多值索引下同样成立：发射先于步骤 4 → 本 record 未入集合、由本复核 close，兄弟 record 不受影响；发射后于步骤 4 → 集合内全部命中）。
6. signal 合并；tombstone 回收时**按 record 精确移除**：`ownedSet.delete(record)`，Set 为空时才移除该 fiber 的 WeakMap 条目——**不触碰同 fiber 兄弟 record 的映射**（F1；监听者是服务级单例，无 per-record 订阅泄漏）。

**S-C7 更正（R3，2026-10-21）——同 root 谓词改用 `ctx.root` 身份**

- **原谓词（作废）**：CH-1.2 步骤 2 原写 `ownerCtx.events === this.ctx.events`。该写法把 S-C7 的"每 root 单一 hook 表"误推为"每 root 单一 `ctx.events` 对象"。
- **实测证据（M1，真实 cordis 0.2.1-rc.2，进程内隔离副本）**：同一 root 下 `root.events === ext.events === pctx.events` **全为 `false`**（`events` 是绑定到各 context 的服务视图，非共享单例对象）；而 `ctx.root` 身份**严格成立**（同 root `true`、跨 root `false`）。证据链：M1 报告 `.codex-sandbox/FEAT-103/M1-REPORT.md`（SHA-256 `8298ADBB…B92F053`，§2「与设计的实现差异」）；`T01-e` 用例覆盖 `OWNER_ROOT_MISMATCH` 的分配前拒收。
- **更正后的谓词**：`ownerCtx.root !== this.ctx.root → OWNER_ROOT_MISMATCH`（`ctx.root` 是公开 Context 属性，语义等同原意：owner 必须与 registry 同 root）。S-C7 的"每 root 单一 hook 表"**事实不变**——它说明 teardown 发射的**可达性**，不是 `ctx.events` 的对象身份；发射路径（S-C3/S-C4）与监听存活（S-C6）合同均不变。
- **为何不需要 Cordis 核心变更**：`ctx.root` 与 `events` 同属已公开 Context 面（S-C7 同一 SOURCE），本更正只是**设计文本的事实订正**，不触发 §3.5 的核心缺口出口，也不改变 §3.5 的 B1 合同。
- **实现落点（M1，隔离副本内，SOURCE 级）**：`.governance/sandboxes/feat103-impl/upstream/packages/preset/agent-preset-registry/lib/index.js` L596-604（`if (ownerCtx.root !== this.ctx.root) throw ownedRegistrationError("OWNER_ROOT_MISMATCH", …)`，L600-603 注释留证并指向 M1 报告）；该文件 SHA-256 `233CF353…99BE88`、相对上游 **+171/−0**。实现面仍待独立 Code Review（见 §11.1）。

**CH-1.3 owner effect 降级为幂等兜底**。owner scope 内的 cleanup effect 仍安装（步骤 3），继续覆盖 registry 内部错误/监听丢失等残余路径，但**不再承担 early notification**——R0-B1 最小解除条件原文满足（"普通 effect cleanup 保留幂等兜底，不能独担 early notification"）。effect 注册失败不留 record/scope（原设计 §3 不变）。同一 owner fiber 多次 begin 时**每个 begin 各自安装独立 effect、闭包捕获各自 record**（步骤 1–6 逐 begin 执行）——多条 record 的兜底互不覆盖，与多值索引（CH-1.1）一致（F1）。

**CH-1.4 root-context owner 的映射**。root fiber 无 teardown 发射（S-C9：root `dispose=()=>restart()`）。合同：root owner 的终态理由在整体卸载时呈现为 `registry-disposed`（root 卸载必然卸载 registry fiber，其发射触发 closeAllOwned）；root owner 的 effect 兜底同装。文档明示该理由映射，不虚构 root 专属发射。

**CH-1.5 LOADING-owner-await-ready 反例合同（保持成立，T01 硬验收）**。设 owner initializer await 本 `lease.ready`、payload barrier 持有，则可观测顺序必须是：

```text
ownerFiber.dispose() 调用
→ [同步] uid=null → emitPluginDisposed → registry 监听 → record.close('owner-disposed')
→ ready/closed settle（closed outcome）；新旧 readers 全部终态
→ initializer 以 closed 恢复并返回 → loading inertia 落定
→ _unload 运行 owner effect 兜底（幂等 no-op）→ dispose() resolve
→ （其后）payload barrier 释放只影响物理 drain
```

任何实现若使 owner dispose 等待 payload 释放、或使 early close 依赖 owner effect（S-C4/S-C5 证明其只能在 inertia 后运行），即设计失败。**不以延长 timeout、不以 late-dispose/0-unhandled/teardown 成功抵销该门**（R0 §7 约束原文承接）。该顺序合同对 owner fiber 持有的**每一条** owned record 独立成立（F1：同 owner 双 record ids A/B 时，owner dispose 后**两条** record 的 closed/readers 终态均先于 barrier 释放，互不覆盖——T01+ 增行硬验收，§8）。

**CH-1.6 激活失败终态（R4 增量，2026-10-22；依据 M1-FIX 的 R0-F2 修复面）**

- **激活失败即终态**：record 激活抛错时，registry 依次执行 `ready = {state:'failed', code:'agent-preset/activation-failed', message}` → `state='closed'`、`closeReason='activation-failed'`、从 `definitions` 表**精确删除**该 record → `closed` settle 为 `{reason:'activation-failed', previous:'failed'}` → `_drain()`（无 generation，同步 finish）→ `drained={state:'drained'}` + `_forget`（**只清 owner 多值索引与 id 主表**；`closedIds` **墓碑保留**，后续仅由同 id 成功重注册清除，见 §5.6；signal listener 同路径 detach）。
- **first-reason-wins 保持**：若显式 `close()` 已先把状态置终态，则该失败收尾不再改写显式 reason（T01-h）。
- **词表纪律**：`activation-failed` 是 **registry 内部终态**，只由 registry 在激活失败时直接写入；**不进公开 `close(reason)` 的可写词表**——公开四值仍是 `explicit`/`signal-aborted`/`owner-disposed`/`registry-disposed`，`activation-failed` 属内部集合 `OWNED_INTERNAL_TERMINAL_REASONS`，类型上与 `OwnedCloseReason` 区分（`OwnedTerminalReason`）。
- **状态**：M1-FIX 隔离副本内、进程内 SOURCE 级实现（T01-g/T01-h 通过）；host 运行面仍 **NOT_RUN**。

### 3.4 D2 联动

原设计 §5.1 的"Owner cleanup calls close and returns without waiting for P/activation/drain"改为："**dispose-start 观察者（主）与 owner effect（兜底）**调用 close 并立即返回"；P/C/R 分支表、READY+C/R>0 只 retire、最后 holder 释放才 fence/drain、公开 fence 候选与 D2-B1 停止条件全部不变（NOT_RUN 状态不变）。§5.2 公开 fence 的 census 面（S-C10）不变。

### 3.5 Cordis 核心变更缺口声明（验收标准⑥）

本 R1 的 B1 **不需要** Cordis 核心变更：仅使用公开 `Events['internal/plugin']` 类型（S-C1）、`ctx.on` 存活语义（S-C6）、单 root hook 表（S-C7）、teardown 发射时序（S-C4）——全部 SOURCE 核实。**证伪出口**（任一在运行中出现 → 停止并声明缺口，不预授权核心扩张）：(a) 某 owner-dispose 路径（除 §3.3-CH1.4 已声明的 root fiber）未产生 teardown 发射；(b) `thisArg=null` 的 dispatch 仍按 scope 过滤掉 registry 监听；(c) 发射时序与 S-C4 不符（如 uid 清除晚于发射）。届时最小核心能力缺口="Fiber dispose 起点保证送达的同步 owner-teardown 通知（不依赖 inertia）"，修改面=vendor/cordis `Fiber.dispose`/`emitPluginDisposed`——**明确不在本票预批写面**，须独立设计+范围授权（与 D2-B1 同等待遇）。

## 4. B2 修订：child selector 分支与精确 generation（CH-2）

### 4.1 当前语义（SOURCE 汇总）

`ChildComposition.agentPreset` 有值=独立选择（`presets.mount(childCtx,id)`，S-U2；cold resume 从子自身 projection 恢复，S-U5/S-U6）；无值=继承（`composeFrom(childCtx,parent.ctx)` 取父**当前** generation，S-U2/S-R6）。spawn 支持（`agentPreset:true`），fork 不支持（`agentPreset:false`，S-U7/S-U8）。原设计 §4.1 将两分支一律冻结为 `{parent: parent.ctx}` ——父 A 子 B 时会把 A 的 token attach 到 header=B 的子会话（能力/身份不一致），或为保 B 留旧 mount 绕过最终 fence——R0-B2 成立。

### 4.2 PROPOSED：selector 分支冻结（CH-2.1）

`materializeTracked` 本地分支（S-U4 :1796-1824）的 admission 选择按下表；共享入口把 `admission` 连同 `composition` 传入 setup：

> **记法对齐（R5，F-M3-4）**：下表 `acquireAdmission(ownerCtx, …, signal)` 为 R1 设计期伪码记法。**实现 API 自 R4 起冻结为 §5.4「R4 增量」的 `acquire({id} | {id, generation} | {parent})`（CODE R3 复审 APPROVED_WITH_NOTES/0 的批准面）**：无 `ownerCtx` 形参（registry 服务自身持有 owner root 语义，同 root 校验在 begin/attach 面执行）、**无 `signal` 形参**——abort 期间 `acquire` await 未完成时无 token 可泄漏，abort 处置归 materializeTracked 外层错误路径与 attempt 边界 `try/finally`（M3 实测合同，见 M3-REPORT §2.1 attempt 边界 release 行）。本文档其余伪码出现按此映射阅读。

| 分支 | 判定来源 | admission selector | 替代的当前调用 |
|---|---|---|---|
| 显式独立选择 | request 的 `composition.agentPreset !== void 0`（spawn 类） | `acquireAdmission(ownerCtx, {id: composition.agentPreset}, signal)`——该 id **当前** record 的精确 generation，冻结后不按 id 重解析（S-R4 教训承接原设计 snapshot-token 规则）；实现 = `acquire({id})`（记法见上方对齐注） | `presets.mount(childCtx, id)`（:377） |
| cold resume 独立恢复 | `hasIndependentPresetSelection(ownEvents)` 且 projection 存在（:2164-2166；无 projection 保留 NOT_RESUMABLE 抛出） | 同上，id=子自身 projection 值 | 同上 |
| 继承 | `composition.agentPreset === void 0` | `acquireAdmission(ownerCtx, {parent: parent.ctx}, signal)`——**父实际 standing generation**，冻结时点=**materializeTracked 编排入口**（合同锚点裁定见下方「继承分支冻结锚点（R5 裁定）」）；实现 = `acquire({parent})`（记法见上方对齐注） | `presets.composeFrom(childCtx, parent.ctx)`（:381） |

**继承分支冻结锚点（R5 裁定，F-M3-2）——合同锚点 = materializeTracked 编排入口，不上提到 spawn 请求入口**

- **裁定**：继承分支的 generation 冻结合同锚点为 **materializeTracked 编排入口**（spawn 与 cold resume 的统一子编排入口）：冻结在该入口进入后、`agents.create/resume` 之前**同步**发生（M3 实现：registry `acquireParentAdmission` 的 `generationFor(parentCtx)` 在方法首个 await 之前同步求值；subagent `:1822-1833` factory-attempt 边界获取）。
- **依据 1（合同语义）**：继承分支的合同语义是"子消费父的**现行** standing generation，冻结后不重解析"（§4.1：原 `composeFrom` 即取父当前 generation）。materializeTracked 是 spawn 与 cold resume 汇合的子编排入口——子编排上下文在该入口就绪、`agents.create/resume` 在其后发起，冻结即取该入口的父现行代（R6 措辞替换：原文"子作为 consumer 首次可行动的时点"依赖修辞解释，裁定实质不依赖该句）；原 R1 文本"与 S-U3 委派策略快照同一时点纪律"的比拟**撤销**——S-U3 捕获的是**委派策略参数**（请求性质，须在请求入口捕获以避免被处理过程中的变化污染），preset generation 是**资源状态**（消费性质，消费点冻结）；两者时点纪律不同属正常，非合同缺口。
- **依据 2（窗口语义无静默路径）**：spawn 请求入口（:1438）与 materializeTracked 之间存在 SDK 编排 await（resolveDirectory/prepareContinuable 等）——窗口内的父切换**被后锚点观察到**：父换代（G1→G2 同 id 重注册）→ 子冻结 G2（继承"现行代"语义的正确表达，非静默取错——G1 已关闭，冻结 G1 反而直接 closed）；父关闭 → 子 acquire 直接 `agent-preset/closed` 拒收（M3 B6/B4 实测）。窗口内不存在"子取到与观测不一致的代"的静默路径。
- **依据 3（双 fence 兜底）**：冻结后的任何换代由 attach 前置判定（closed/retired/换代拒收，M3 A11/B12）与 `publicationCommit` fence（§5.4/§5.6）双层拒收——即使存在未预见的窗口，合同保证**不静默取新代**（D2 不变量），B3/B12 全链证伪了更晚的"setup 期冻结"形态。
- **备选路径 b)（不上提的排除理由）**：若要求"请求时点冻结"，须把冻结上提到 spawn 请求入口（:1438）与 coldResume 入口（:2221）并穿参（影响两处签名与传参链）——收益仅是把窗口内换代从"观察到新代（可观测、语义正确）"改为"closed 拒收（可观测）"，两者均非静默、不改变安全合同；按最小合同原则不要求上提。若后续独立复审裁定合同应取请求时点语义，b) 为既定实施路径（影响面=上述两处签名）。

- 获取失败（closed/broken/not-found）→ child start 以对应错误失败（REGISTRATION_CLOSED/invalid/not-found 复用原设计错误合同；**R4 映射：owned 路径的消费者可见 code 为 `agent-preset/closed`，见 §5.3「错误码映射」**）；**不回退到另一分支**。
- **错误面区分（R5，F-M3-3）**：上句"以对应错误失败"在两个消费面的**消费者可见形态**不同，均为合同行为：**spawn 面**——`agent-preset/closed` 原样透传（M3 B4 实测；新会话创建的准入错误直接属于 preset 准入分类）；**cold resume 面**——acquire 失败被既有 coldResume catch（:2238-2241）包为 `SubagentError("…unavailable", "NOT_RESUMABLE", { cause })`，**code 不透传但 `cause` 链完整保留 closed 根因**（`cause.code === "agent-preset/closed"` 可溯源）——沿用既有 NOT_RESUMABLE 纪律（S-U5：cold resume 对不可恢复状态统一 NOT_RESUMABLE 是既有 API 合同，本补丁不改变该分类面）。两面的共同保证：**closed 根因不丢失**（直接 code 或 cause 链）、**均无静默回退**。
- attach/`publicationCommit` 语义沿用原设计：attach 单次、same-root、unpublished-Agent only；setup 返回的 commit 携带绑定该精确 generation 的 publicationCommit；`agent-preset/selected` append（:1799/:2164 语义）仍留在 setup 内（先于 old commit），publicationCommit 保持同步不 append。

### 4.3 拒收规则承接（CH-2.2/CH-2.3）

- **CH-2.2 禁止父 token 替换独立选择**：独立分支永远消费该 id 的精确 reservation；父 generation 状态（含关闭）不影响独立分支的 token 来源。
- **CH-2.3 分支化拒收合同**（两条独立成文，不互相放宽）：
  1. 继承分支：父 owned generation 已关闭 → 新 child 拒收（REGISTRATION_CLOSED）；已提交子/父 Agent 继续旧 revision（D2 不变）。legacy 父 record（非 owned）→ 沿用 `composeFrom` 原形状（protocol-required 边界不变，原设计 §4.1 外部行）。
  2. 独立分支：按**该 id 自身** record 状态准入——父 generation 关闭不阻止独立子选择（不同 record，不是对 1 的放宽）；该 id 关闭则拒收。同 id 换代（G1 closed→G2）不跨越：冻结 token 指向 G1 即拒绝，不静默取 G2（S-R4）。
- 顺序/能力保真：独立组合在 create 追加前、继承在追加后（S-U4 顺序原样保留）；descriptor/persona/toolFilter/delegation/workingDirectory/structured runtime 顺序与语义不变；provider 只提供 capabilities/seed——**不向 spawn/fork provider 添加 factory**（R0 §3-B2 明令；能力检查在 admission 获取**之前**：fork 类请求带显式 preset 现行拒绝行为保留，避免先取 token 再拒绝的泄漏）。

### 4.4 helper 公开面（CH-2.4）

`applyChildComposition`（child-agent.d.ts:90，现返回 `void | Promise<void>`）：PROPOSED 新增 owned 变体 `applyChildCompositionOwned(childCtx, parent, composition, admission): AgentSetupCommit | Promise<AgentSetupCommit>`——内部以 `mountOwned(childCtx, admission)` / `composeFromOwned(childCtx, parentCtx, admission)` 消费 token 并返回含 publicationCommit 的完整 commit；legacy definition 继续用原函数/原形状。类型导出增量在 `dsh-subagent/lib/types/child-agent.d.ts`。setup hook 传递：materializeTracked 本地 setup（:1796-1808）把该 commit 作为 setup 返回值交回 AgentLoop（§6.1 链路），外部 provider 分支（remote/external）不经过本面，不改。

> **消费原语映射（R5，F-M3-1）**：本节的 `mountOwned(childCtx, admission)` / `composeFromOwned(childCtx, parentCtx, admission)` 是 R1 设计期原语名。**实现未新增这两个 API**——M2 起批准实现面为 §5.4「R4 增量」的 `acquire` + `attach`（CODE R3 复审 APPROVED_WITH_NOTES/0）：**`admission.attach(childCtx)` 对新子即 mountOwned/composeFromOwned 的语义**（join 冻结 generation + 返回含 `publicationCommit` 的 commit）。M3 的 `applyChildCompositionOwned`（subagent 副本 `:364-407`）内部消费 `attach`，未引入重复 API。本节记法按此映射阅读；两分支的消费差异（独立 join 新 binding / 继承 rebind 父 binding）由 attach 内部按 token 来源 generation 表达，不再区分为两个公开原语。

## 5. B3 修订：claim/reuseLive/fallback 的单次 token 生命周期（CH-3）

### 5.1 当前代码事实（SOURCE 汇总）

`composeAgent` 先 resolve id 并生成 setup（S-T1）；`claim` live 路径先 compose 再 `reuseLive ?? createMinted`（S-T3 :422-423）；`reuseLive` 同 preset 直接返回 live（S-T4 :473，零 factory），改选走 `presets.select(live,target)`（:475，select 内部 :757 按 id 重解析 + :759 recompose + :760 append）；resume 失败回退 `createMinted(同一 composition)`（:461）或递归 `claim`（:463）；`reuseSetup` 是 hook 包装点（S-T5）。原设计围绕旧 createOrAdopt 的"compose 时 acquire、factory finally release、attach 单次"未定义这些新分支——R0-B3 成立。

### 5.2 双生命周期定义（CH-3.2）

- **operation**=一次公开调用（`claim`/`fork`/`create`/`resume`/`resumeObserved`）；`claim` 的 :463b 递归是**新 operation**。
- **factory attempt**=一次 `agents.create`/`agents.resume` 调用。
- token 状态机：`UNACQUIRED → HELD(未 attach) → ATTACHED(已消费，单次) → RELEASED | COMMITTED(随 publicationCommit 提升)`。
- 不变量（每个 operation 的每个出口——return 或 throw）：本 operation 引入的 P（未转移 provisional admission）=0（已 attach 的随 Agent scope effect 归属该 Agent）、本 operation 新增 listener=0、未持有读 lease。测试逐出口断言（§8）。

### 5.3 分支合同表（CH-3.1/CH-3.2）

| # | 分支（当前代码锚点） | admission 生命周期合同 |
|---|---|---|
| 1 | `composeAgent`（S-T1） | **只做 id 解析，不 acquire**（CH-3.1）。否则 :473 纯复用会被 closed registration 错误拒绝（违反 D2 committed 保留）并泄漏 token——R0-B3 第 1 点。 |
| 2 | live 同 preset 直接返回（:473） | 全 operation 零 admission、零 release；closed registration 不影响（已发布 Agent 的 D2 保留）。 |
| 3 | live 改选（:474-480） | 先 `acquire({id:target})`（closed → 上抛：**owned 路径消费者码为 `agent-preset/closed`**；`REGISTRATION_CLOSED` 是既有接口合同名，映射见本节末「错误码映射」段——live 旧绑定不动）；持有冻结 token 进入 §5.4 内部事务；`agent-preset/locked`（:477）→ token 未 attach → release → 返 undefined 落 createMinted（其自行 acquire）；其它错误 → 事务回滚（§5.4）后重抛。 |
| 4 | not-found → `createAgent`（:430）/ !reusable → `createMinted`（:452） | factory attempt 边界 acquire；setup 内 attach 消费；attempt 失败且 token 未 attach → finally release；已 attach → 随回滚的 Agent scope effect 释放（原设计 attach 合同），operation 无残留。 |
| 5 | reusable → resume + `reuseSetup`（:455-459） | attempt 边界 acquire；`reuseSetup` 的 blank 复查（:485）先于 `composition.setup`（:486）→ StartedSinceObserved 时 token 必未 attach → release 后进入 :461 回退。 |
| 6 | `ApiSessionStartedSinceObserved` → `createMinted(同一 composition)`（:461） | 回退 attempt **必须携带首个 attempt 的冻结 generation**（R4 增补：不得只按 id 重新 acquire 当前 generation；composition 必须携带该冻结标识）；若该精确 generation 已关闭/retired → operation 以 **`agent-preset/closed`** 失败，**不按 id 静默换代**（S-R4/S-R7 教训）。未 attach 的旧 token 必已 release（不变量）。 |
| 7 | `SessionAlreadyOwnedError`（:462-463） | 无 live → createMinted：同 #6 分类（**R4 增补：携带冻结 generation，不得按 id 重取；该 generation 已 closed/retired → `agent-preset/closed`**）——token 若已消费（setup 深处失败）随 scope 回滚；有 live → **recursion = 新 operation**：当前 operation 先在 finally 释放全部未 attach token/监听，再递归。 |
| 8 | `fork`（S-T6 :880-:898） | :880 仅 id 解析；:883-898 factory attempt 边界 acquire（同 #4）；:902-908 workspace attach 失败发生在 create 成功后——token 已随 publicationCommit 提升，无 operation 残留；存档保全按 D1 gap 合同（§6.1）。 |
| 9 | `resumeObserved`（S-T :392-404） | 单 factory attempt，同 #4；composition 来自 `presetForObservation`（存档 header 的 id），admission 按该 id 当前 open generation 冻结；关闭 → 拒绝并保留文件（D3 既有行）。 |

- **CH-3.4 失败分类总则**：未 attach（HELD）→ 可在同 operation 内复用或 release 后重取，但重取必须冻结**同一精确 generation**（不可跨代）；已 attach（ATTACHED/COMMITTED）→ 不可复用；任何"继续同一冻结 admission"的路径不得默默换代——换代只能发生在**新 operation** 重新解析/冻结时，且对调用方可观测（新请求语义）。

- **冻结 generation 的传递（R4，2026-10-22；依据 REVIEW-FEAT-103-CODE-R2 P1）**：`composeAgent`/attempt 包装必须把**首个 attempt 冻结的 generation**（或其 token 标识）带入 composition。之后的回退（StartedSinceObserved / SessionAlreadyOwned-无 live）只允许重取**同一 generation**，禁止 `acquire({id})` 落到 `definitions.get(id)` 的当前 generation；G1 close → G2 同 id 重注册后，冻结 G1 的回退一律 `agent-preset/closed`（与 §5.6 墓碑合同联动）。实现面：M2 现状仍按 id 重取（CODE R2 P1-1 未关闭），M2-FIX 必须按本增量修正，并补「G1→G2 + `StartedSinceObserved`」与「G1→G2 + `SessionAlreadyOwned`-无 live」**两类** fallback 用例（断言 closed 或精确复用 G1，不得静默取 G2）。

- **错误码映射（R4，2026-10-22；N-R4-1）**：`REGISTRATION_CLOSED` 是**既有错误合同名**（legacy/接口层沿用，见 §4.2/§4.3 与本表 #3 的历史措辞）；`agent-preset/closed` 是 **owned 路径的消费者可见 code**（close / `activation-failed` 终态、换代隔离、`publicationCommit` fence）。两者**语义等价**：**owned 路径一律发 `agent-preset/closed`；legacy 路径保持 `REGISTRATION_CLOSED` 原样**，实现/测试不得在无解释的情况下混用两套名字；本文档中其余出现 `REGISTRATION_CLOSED` 的历史行按此映射阅读。

### 5.4 live-switch 内部事务（CH-3.3，registry 侧）

新 PROPOSED 内部分支 `selectWithAdmission(live, admission)`（packages/preset/agent-preset-registry；**不改 Session 核心**）：

1. 前置：per-agent 串行链（沿用 `this.switches`，S-R7 :751）+ blank 校验（:752-756 语义）+ token HELD 且其 record open。
2. **消费冻结 generation 对象**做 staged rebind（bind :654-667 形状）——**删除 :757 式 `definitions.get(id)` 按 id 重解析**：G1 close→G2 同 id 替换时，冻结于 G1 的请求得到 REGISTRATION_CLOSED，不取 G2（换代风险消除）。
3. append `"agent-preset/selected"`（:760）：**持有旧 binding 直到 append 成功**；append/observer 抛错（S-S1 :1579-1598 validateNext/observers 可抛）→ **先恢复旧 binding（回滚 staged rebind），后重抛原错误**；任何路径不得出现"已 rebind 未 append"或"已 append 未 rebind"的半绑定。
4. **禁止先 collect 旧 scope 再回滚**：`collect(old)`（S-R5）只在换绑提交成功路径执行；回滚路径不触发 collect。
5. 成功：binding 提升、旧 binding users--/collect、token 转 COMMITTED；返回提交 id。失败：旧 binding 原样、token 未消费 → release、错误上抛。

**R4 增量：M2 落地 API 合同（2026-10-22；依据 REVIEW-FEAT-103-CODE-R2 判定与 M2 实现事实）**

- **`acquire` token 状态机**：`acquire({id})`（**M2-FIX 起扩展为 `{id, generation}` 形态〔回退 attempt 携带冻结代，§5.3「冻结 generation 的传递」〕、M3 起扩展为 `{parent}` 形态〔继承分支，§4.2〕——三形态合同统一见 §4.2 记法注记；R6 补此衔接半句，R6-P3-1**）返回**冻结 token** `{id, generation, state:'HELD', attach, release}`；状态迁移严格为 **`HELD → ATTACHED`（`attach` 单次）→ `COMMITTED`（`commit()`）**；**`release()` 仅对 HELD 生效**（ATTACHED/COMMITTED 为 no-op，归属随 Agent scope 回滚）。任何路径不得从 COMMITTED 回退，也不得对同一 token 二次 attach。
- **`attach` 两阶段与事务性**：`attach()` 返回 `{commit(), publicationCommit()}`；`commit()` 完成 registry 侧提交（HELD→COMMITTED）；`publicationCommit()` **同步、不 append、不 dispatch observer**，只做发布前 fence：校验「冻结 generation 仍 open 且 id 表未换」，否则抛 `agent-preset/closed`。**`attach` 必须事务化**：先执行 join/rebind，**成功后才置 ATTACHED**；任一步抛错必须回滚（旧 binding 不变、`generation.users` 的 operation hold 释放）并重新抛出，**不得留下 ATTACHED 泄漏**（R2-P2-3 的缺陷面：先置 ATTACHED 再 rebind，抛错后 release 已 no-op）。
- **`selectWithAdmission` 回滚合同**：append `agent-preset/selected` 失败 → **先恢复旧 binding（`parent.rebind(previous.key)`）并回滚 generation 计数，不 collect 旧 revision**（token 保持 HELD 可释放，旧 revision 的 users 不被扣减）；成功 → 旧 binding `users--`/collect、token 置 COMMITTED。成功后 `collect(previous)` 的失败必须隔离为诊断/日志，不得让"已提交"与返回错误不一致（R2-P3-2）。
- **冻结 generation 的一致性**：`attach` 与 `selectWithAdmission` 都只消费 token/composition 携带的**冻结 generation**，不得 `definitions.get(id)` 重解析当前 generation（R2-P1-1 的根因面；与 §5.3 冻结 generation 传递、§5.6 墓碑合同一致）。
- **状态（标签纪律，R5 更新至 M3 后事实、R7 更新至 M4 后事实；含 N-R4-4 补列）**：以上为隔离副本内、进程内 SOURCE 级实现——M2（A1-A6）→ M2-FIX（attach 事务化/回滚/冻结传递，CODE R3 复审 A1-A9+C1-C13）→ **M3（R3-P2-1 `collect(previous)` 失败隔离=A10、attach closed/retired 前置判定=A11/B12、`closedIds` 清除移至 `record.start()` 成功后带 `activating` 门控=A12）**；CODE R2 时的三缺口（P2-2 空壳/P2-3 attach 非事务/**P3-2 成功后 collect 失败未隔离——R4 版状态行漏列此项，本行补列（N-R4-4）**）均已闭环。**M4 起补齐 attach 的 rebind 抛错分支（M4-2：rebind 抛错→原错误透传、token 保持 HELD、旧 binding 不变、双方 users 不变、release 归零——无 ATTACHED 泄漏无半绑定；M4-REPORT §2，纯测试批副本零改动，REVIEW-FEAT-103-R12 AWN/0）**。未覆盖/未运行：真实 publish 链、host/运行面 **NOT_RUN**。

blankness 在 writer 获得前改变：事务在串行链内于 append 前复检 blank（等价 S-T5 :485 语义），不 blank → 失败退出（无半绑定）。

### 5.5 `reuseSetup` 完整 commit（CH-3.5）

owned `composition.setup` 返回 `{commit(){}, publicationCommit(){}}`（组合既有 commit 恰一次，§6.1）；`reuseSetup`（:483-491）原样透传该对象；:488 的 selected append 位于 **`reuseSetup` 包装器内、`composition.setup`（:486）返回之后**——即仍在 setup 阶段内、先于 old commit，但不在 `composition.setup` 函数体内部（F3 措辞澄清，R1 审查指正；实质语义不变：pre-publication append，由 `appendUnstoredSuffix` 持久化），**不进入** publicationCommit（同步、不 append、不 dispatch observer 的约束不变，原设计 §4.2 承接）。

### 5.6 `closedIds` 墓碑合同（R4，2026-10-22；依据 REVIEW-FEAT-103-CODE-R2 P2-4 / P2-1 / P3-5）

1. **消费者可见分类与判定点**：`agent-preset/closed` 表示"该 id 的某个 generation 曾以 **owned 终态**关闭"；`not-found` 表示"registry 从未见过该 id，或该 id 仅有 legacy 关闭"。判定点（实现锚点，SOURCE 级，M2 副本）：`acquire`（:885 分类）、`selectWithAdmission`（冻结 generation 已关闭 → closed）、`attach`/`publicationCommit`（record 已关闭或 id 表换代 → closed）。
2. **墓碑生命周期**：**创建** = owned record 进入终态时写入（`close()` 与 `activation-failed` 内部终态两个写入点，:463/:494）；**清除** = **仅在同 id 成功重新注册之后**（`beginRegistration` 完成 owner 存在/uid/root 校验、effect 安装、record 分配/入索引与启动之后）；**失败的重注册必须保留墓碑**（owner 校验失败、effect 失败、启动前失败均不得清除）；**不得在 owner 校验之前清除**（R2-P2-1 实测缺陷：先删墓碑 → 失败 begin → closed 退化为 not-found，探针已复现）。
3. **legacy `register`/disposer/unregister 的关系**：墓碑**只记录 owned 生命周期**；legacy `register` 的 disposer/unregister 关闭**不写墓碑**——对消费者而言 legacy 关闭仍表现为 `not-found`（与 owned `closed` 明确区分）。若未来要求 legacy 也进墓碑，须另立合同并独立复审，不得由实现擅自扩大。
4. **旧 token 换代隔离**：G1 关闭 → G2 同 id 成功注册之后，任何**冻结于 G1** 的 token 在 `select`/`attach`/`publicationCommit` 及回退路径一律得到 **`agent-preset/closed`**，**不得静默取 G2**；与 §5.3 #6/#7 的"冻结 generation 传递"是同一合同面的两面。
5. **清理/生命周期**：墓碑集合随 registry 卸载整体丢弃；同一 id 成功重注册即清除该 id；不设 LRU/容量上限（集合只保留已关闭 id 的字符串，长期大量 close/重注册的增长面在 §9 风险面披露；若需上限/迁移策略须另立合同）。
6. **本条取代/细化 §5.3 #6/#7 的"不按 id 静默换代"**：原文只写"该精确 generation 已关闭 → operation 以 REGISTRATION_CLOSED 失败"，未定义墓碑生命周期、失败重注册保留、legacy 语义与旧 token 的消费者分类；本条补齐，并**覆盖 fallback 路径**（StartedSinceObserved / SessionAlreadyOwned-无 live）。
7. **实现状态（标签纪律，R5 更新至 M3 后事实）**：隔离副本内、进程内 SOURCE 级已实现 Set 墓碑（写入/查询/成功重注册清除）。清除时机演进：M2 曾在校验前清除（CODE R2 P2-1 缺陷）→ M2-FIX 移至 record 插入成功后（CODE R3 复核 PASS）→ **M3 起按本条"分配/入索引与启动之后"口径移至 `record.start()` 成功之后，且带 `record.state === "activating"` 门控**（start 前已终态的失败 begin——pre-aborted signal / close-before-start——`close()` 已把墓碑加回，门控保证"启动前失败保留墓碑"，M3 A12 + naive-move 变异体证伪无条件移位形态）；start 与门控行之间为同步段（`_activationSettled` 只在微任务运行），无交错窗口。legacy 分类面 M4 起部分闭合（M4-1：legacy register→unregister→acquire=**not-found** 且 closedIds 无该 id；存活中重复 register=Duplicate；同 id 后续 owned 注册→close→**closed**——分类对照成立，M4-REPORT §2，纯测试批）；**legacy default/list 回归已由 M5-3 闭合（2026-10-23，R8 回写：list() 形状/defaultId 优先级/resolve() 落 default/isDefault 标记行为用例 PASS；reg-prefix 前缀对照同 PASS=与安装态 legacy 原行为一致零回归）**；容量策略未实现/未测（维持）；host/运行面 **NOT_RUN**。

## 6. D1–D3 保留面重锚

### 6.1 D1（不变，重锚行号）

- AgentLoop 补丁点：`setupAndPublish`（S-L2）改为缓存 `setupCommit`、保持 old commit（:1931）与 append 顺序（:1932），`prepared.publish(source, setupCommit?.publicationCommit)`（:1933）；`publish`（S-L1）签名增可选 finalizer，在 `assertLive()`（:1789）之后、`sessions.enter`（:1790）之前同步调用——两个 enter 同步无创建事件（S-S1），finalizer 与两个 enter 之间无 await/observer。thenable 校验：finalizer 返回 thenable → 视为非法同步 hook，在 enter 前抛出并消费其 rejection（原设计 §4.2 承接，T04/T12 保留）。
- **owned registry 侧 `publicationCommit`（R4 增量，2026-10-22）**：`attach` 返回的第二阶段回调是 D1 fence 的 registry 半边——**同步、不 append、不 dispatch observer**；只读校验「冻结 generation 仍 open 且 id 表未换」，否则抛 `agent-preset/closed`。它与 AgentLoop 的 `prepared.publish(source, setupCommit?.publicationCommit)` 配对：缺任一半即视为 D1 接线错误（D1-1～D1-5 为源码/加载级结构断言；真实 publish 链仍 **NOT_RUN**）。
- consumer 表替换（对原设计 §4.1）：

| 当前 SOURCE 路径（0.2.1） | R1 改动 |
|---|---|
| controller composeAgent :351-364 | CH-3.1：只解析 id；admission 移至 §5.3 各 attempt 边界 |
| controller claim/reuseLive/reuseSetup/fallback :405-491 | §5 全部分支合同 |
| controller fork :849-905 | §5.3-#8 |
| controller resumeObserved :392-404 | §5.3-#9 |
| subagent materializeTracked 本地 setup :1796-1824 + cold :2164-2183 | §4.2 selector 分支；不再对独立选择调裸 mount/composeFrom 换字符串 |
| ~~subagent-in-process-driver startInProcessRun~~ | **包已不存在**（§2.2）；委派权限同步 capture 纪律由 S-U3 承接进继承分支 |
| ~~webhook createWebhookSession~~ | **当前匹配源码未取得**：不在本 R1 覆盖声明内；旧 0.2.0 快照仅历史证据。若后续取得匹配版本源码，先提交精确 consumer 点供同范围独立复核（R0 §5 原文承接） |
| AgentLoop configured create（不消费 preset） | 保留原行为，统一经 prepared.publish（不变） |
| 外部直接 old mount/composeFrom | legacy 形状不变；owned definition 走 prepared admission，旧方法对 owned 新接入 protocol-required（不变） |

- 持久化 gap 处置（原 §4.3）全文有效：fence 拒绝→`{published:false, persistence:'may-exist'}`、close exact handle、保留 header/seed/suffix/合法 resume closers、不 delete/truncate/auto-retry；cleanup 次要错误不吞不盖原 cause。锚点重锚：append 受控 await=S-L2 :1932；resume closers=原 :1949-1962（0.2.1 相应 resume 链）；handle 合同=S-P1。

### 6.2 D2（不变 + B1/B2/B3 增量）

P/C/R 三 holder 分支表、READY+C/R>0 只 retire、最后释放才 fence/drain、tombstone identity、公开 fence 候选与 D2-B1 停止条件、census 面（S-C10）全部不变（NOT_RUN 不变）。增量：owner→close 行按 §3.4 改写；child admission 按 §4.2 分支；live-switch 事务是 P holder 在 SDK 内部事务中的受控消费（§5.4），不新增第四种 holder。

### 6.3 D3（不变 + 覆盖扩展）

原 §6.1/§6.2 全表有效（ready 一次性、closed 首因、drained 独立、同 id 换代隔离、旧 register/坏注册/duplicate/default/selected/list 排序/retired revision 保留、token 不写存档）。增量覆盖：cold 独立子（§4.2）与 live 复用/改选（§5.3）纳入兼容表——"旧 API 未改"的证明现须引用这两族分支的合同，而非仅 0.2.0 消费者形状。

## 7. 更新的最小补丁文件面（0.2.1 module map）

| 上游模块（manifest repository.directory） | R1 范围/职责增量 |
|---|---|
| packages/preset/agent-preset-registry（lib/index.js、lib/types/index.d.ts） | 原 §7 职责（owned facade/state/admission/collection）+ CH-1 dispose-start 观察者（含 F1 多值 owner 索引 `WeakMap<Fiber, Set<OwnedRecord>>` 及其 tombstone 精确移除）+ CH-3.3 `selectWithAdmission` 内部事务 |
| packages/core/agent（lib/types/index.d.ts） | `AgentSetupCommit` 增可选 `publicationCommit?()`（S-A1 证明当前不存在，须显式新增） |
| packages/core/agent-loop（lib/index.js :1786-1804、:1915-1955） | finalizer 传入并在 enter 前调用；错误/handle cleanup 复用原链 |
| packages/api/session-controller（lib/index.js） | composeAgent/claim/reuseLive/reuseSetup/fork/resumeObserved/createAgent 按 §5.3 重排 admission 生命周期 |
| packages/subagent/subagent（lib/index.js、lib/types/child-agent.d.ts） | applyChildCompositionOwned、materializeTracked setup 传 admission/commit、cold resume 分支（§4）；类型导出 |
| packages/subagent/subagent-spawn-in-process、subagent-fork-in-process | **只读核兼容 + 纳入测试**（capabilities/seed 不改，不加 factory） |
| webhook | 当前未安装；不在写面；取得匹配源码前不声称覆盖（§6.1） |
| vendor/cordis、vendor/loader、packages/core/scope、Session/Persistence 核心 | **不在预批写面**（B1 无核心依赖，§3.5 缺口声明） |

静态 DAG 不变（原 §7）：facade→state/admission/collection；admission→公开 scope/AgentSetupCommit 类型；AgentLoop 只消费 commit 形状不 import registry；consumers→registry 公开接口 + AgentRegistry 工厂；模块环=0。运行等待图独立验收（B1 反例为新增硬门）。

## 8. 回归测试合同（原 T01–T14 全部保留；以下为 B1–B3 增量；全部 NOT_RUN）

| ID | 增量必须观测/失败条件 |
|---|---|
| T01+（B1/F1/F4） | 真实 LOADING owner initializer 正在 await **本 lease.ready**、payload barrier 持有：owner dispose 后 closed/新旧 readers 终态先于 barrier 释放，owner dispose 完成不等待 barrier；owner 已 ACTIVE 的对照；dispose 重入（重复发射幂等）；registry fiber 卸载 → registry-disposed 关闭全部 owned；barrier 释放**之后**的 cleanup 不计为 early close（事件屏障断序，不用 sleep）。**同 owner 双 record（F1）**：同 owner fiber 对 ids A、B 各一次 begin（均 LOADING、各自 await lease.ready）→ owner dispose 后**两条** record 的 closed/readers 终态均先于 barrier 释放，A/B 的 dispose-start 通知互不覆盖；A 先 tombstone 回收**不影响** B 的映射（其后 B 的 owner 仍可被正确通知/close）。**root-context owner（F4）**：root owner 的 owned record 在整体卸载时终态理由呈现为 `registry-disposed`（CH-1.4 映射的观测行——经 registry fiber teardown 发射的 `closeAllOwned` 关闭，不虚构 root 专属发射）。 |
| T05+（B3） | 每个 §5.3 分支注入 T03 storage gap；resume 原档/合法 closers 保留；fork 父档不变；每出口 P/listener 归零断言（不变量逐出口核对）。 |
| T06+（B2） | A 父/B 子 spawn；B closed 而 A open → 子 B 失败不回退 A；A closed（继承）→ 新 child 拒收而独立 B 子允许（两合同分别断言）；继承 fork；独立 cold resume（projection 有/无→NOT_RESUMABLE）；各配 storage gap 预期。 |
| T07+（B2/B3） | 同 id 换代：继承分支冻结 G1 → G1 关闭 → 拒绝不取 G2；独立分支同理；live 改选冻结 G1 → G2 替换后事务拒绝 G1、不静默 G2。 |
| T09+（B3） | live 同 preset 且 registration closed → 复用成功（D2 保留）且 P=0；live 真实改选全链；closed 后新 admission/child/acquireScope 拒收。**R8 实现面锚注（2026-10-23）**：closed 变体的实现=claim 的 live 分支在 `composeAgent` 之前短路（与 reuseLive 短路完全同构，唯一差别=跳过 resolve——resolve 对 owned-closed id 按 §5.6 分类抛 not-found，而 live 复用合同不应重解析；agentPreset 缺省落 default 时不可短路）；M5 微批修复（controller 副本 +9/−0）后 t-m5 3/3 PASS，安装态原版对照仍失败=该合同在 M5 前从未被任何版本实现（非补丁回归）——归因与修复证据见 M5-REPORT §2.1。 |
| T11+（B3/D3） | SessionAlreadyOwned 两回退（#7）；setup 前失败（token HELD）vs attach 后失败（token 已消费随 scope 回滚）；claim 递归=新 operation 的 token/监听重建与旧 operation 归零；legacy register/disposer/default/list 回归不降。 |

原 T01–T14 的 barrier/事件屏障/NOT_RUN 诚实约束、不降 schema/base accepted/broken 门、不延时或先 release 帮助通过——全部保持（R0 §7 原文承接）。

## 9. 非功能与蓝军（R1 更新）

| 非功能 | R1 措施 | 残余 |
|---|---|---|
| 取消可用性 | CH-1 dispose-start 同步观察 + close 先于 activation/drain；等待环反例为硬门（T01+） | actual NOT_RUN |
| 存档安全 | §6.1 gap 合同原样；B3 失败分类禁止以重试/换代遮盖残留 | T03/T05+/T13 |
| 版本/会话兼容 | legacy 默认不变；cold 独立子与 live 复用/改选纳入 D3 表（§6.3） | T06+/T09+/T11+ |
| 维护/扩展 | registry 单监听者（无 per-record 订阅）；分支合同表成文；providers 零改动 | 源码映射隔离准备时核对 |
| 性能 | 单一服务级监听：每 **teardown** 发射 **O(该 fiber 的 owned records)** 多值索引查找 + 逐 record close（F1）；**创建发射同样进入监听者**——同 root 每次 plugin fiber 创建/销毁各一次发射、均 thisArg=null 无 scope 过滤（S-C8 R2 更正），非 owned fiber 经 uid 判别 O(1) 早退，即监听者实际收到的发射次数 = 同 root plugin fiber 生命周期事件数、单次开销有界（成文依据 R1 审查 F2(ii)）；D2 fence 仅 close 时扫描（原设计） | T10 census/复扫轮数记录 |
| 可观测 | close reason 区分 owner-disposed/registry-disposed（§3.3-CH1.4 映射成文）；B3 各出口 P/listener 计数可断言 | 避免敏感数据入错误（原设计） |
| 墓碑容量/清理 | `closedIds` 仅保留已关闭 id 的字符串；同 id 成功重注册清除该 id、registry 卸载整体丢弃（§5.6） | **无 LRU/容量上限**：长期大量 close/重注册的 id 会持续占用内存（未测）；若需上限/迁移策略须另立合同（N-R4-3 的残余风险落点） |

蓝军（承接 R0 BR1–BR5，R1 缓解更新）：

- **BR1'**（LOADING owner await ready，含同 owner 多 record 形态——F1）：CH-1.1（多值 owner 索引）/CH-1.5 直接消解；若运行证伪监听语义 → §3.5 缺口出口停止（缓解=源码级核实 + T01+ 硬门，含同 owner 双 record 反例行）。
- **BR2'**（A 父显式 B 子/cold B）：CH-2.1/2.2 分支冻结 + T06+；残余=provider 能力矩阵变化时需复测（spawn/fork 只读核）。
- **BR3'**（claim 零 factory/回退换代）：CH-3.2 不变量 + CH-3.3 事务去 id 重解析 + CH-3.4 分类；T05+/T07+/T11+ 逐出口计数。
- **BR4**（persist 已接受后关闭）：不变（may-exist/close-only/保留原档）。
- **BR5**（十倍 fibers/late inline child）：不变（D2 公开 fence 候选 NOT_RUN；失败即 D2-B1 停）。

## 10. Proposed ADR 增量（Coordinator 机录，Architect 不自批）

在原设计 §9 ADR 基础上追加 R1 决策记录：**2026-10-20，"Owned registration dispose-start 观察与 0.2.1 消费者分支生命周期"**——背景=R0 三 BLOCKING + 安装态升级 0.2.1-rc.2；决策=(a) B1 采用 registry 级 `internal/plugin` 公开事件观察（候选 B1-B/B1-C 排除理由 §3.2），(b) B2 selector 分支冻结（统一父 selector 排除），(c) B3 operation/attempt 双生命周期 + 冻结 token 内部事务（compose 期统一 acquire 排除）；备选与排除=§3.2/§4.1/§5 各候选表；影响=§7 模块面（subagent 替换旧 driver 条目；webhook 未取得）；后果/风险=运行验证 NOT_RUN、webhook 覆盖缺口明示、root-owner 理由映射；可逆性=同原设计（丢弃隔离补丁/恢复已钉 artifact）；后续动作=独立 R1 静态复核 → 通过后 Coordinator 派精确隔离实现/运行；当前结论 PENDING。

**R2 决策增量（F1 修复，2026-10-20）**：owner→record 索引采用**多值** `WeakMap<Fiber, Set<OwnedRecord>>`（与 id 主表联动）。备选排除：**(b) 显式单 record/owner 合同 + 新错误码**（如 OWNER_ALREADY_OWNS）——排除，理由：原设计合同（:70-71/:192）未限制 owner 单 record，收紧合同会 (i) 拒收"不同 id 同 owner"这一合同合法输入，(ii) 新增错误面并改变 begin 语义（与 R0 已接受的合同面冲突），而多值索引是零合同变更的局部数据结构修正（R1 审查 F1 最小解除推荐项，本 R2 未取得反驳证据）。影响=§3.3 CH-1.1/CH-1.2/CH-1.3/CH-1.5、§8 T01+、§9 性能行；可逆性=可逆——实现期若须回退为方案 (b)，须同步重开合同文本、错误表与 T01+ 行并重新过独立复审。

## 11. 设计自检与交接状态

**Design Doc 最小结构**：目标（§头部+§1）/方案（§3-§6）/替代方案（§3.2、§1.1 R1 响应表、§4 候选注记、§5 分类 vs 换代、原设计 §2 保留）/风险（§9）/非功能覆盖（§9）——齐全。

**硬门槛自检**：候选方案 ≥2（B1 三候选；**F1 修复二候选 (a) 多值索引 vs (b) 单 record 合同+错误码，§1.1/§10 R2 增量**；**R5 继承冻结锚点裁定二候选 a) materializeTracked 入口 vs b) spawn 入口上提+穿参，§4.2**；B2/原 §2 三候选；B3 三分类路线）PASS；ADR 字段完整（§10 含 R2 增量：标题/日期/背景/决策/备选/排除/影响/后果/可逆/后续）PASS；蓝军 ≥3（BR1'–BR5）PASS；静态模块环=0（§7）PASS；独立 Bar Raiser=R1 轮已执行（NEEDS_CHANGE，F1–F4 见 `review-FEAT-103-DESIGN-R1.md`）；R2=REVIEW-FEAT-103-R2、R3=REVIEW-FEAT-103-R3、**R4 与 R4-P2=REVIEW-FEAT-103-R7（AWN/0）+ R8（APPROVED/0）均已独立复核**；**R5 增量聚焦复核已完成——REVIEW-FEAT-103-R11（报告 `docs/reviews/review-FEAT-103-DESIGN-R6.md`，2026-10-22 机录）= APPROVED_WITH_NOTES / unresolved_blockers=0：锚点裁定 a) 被接受、F-M3-1~4 收敛与状态行全部 PASS、R5 已批面零回退 grep 验证；其 2×P3 备注（§5.4 单形态衔接/"首次可行动"修辞）已由 R6 文本批收敛（§14）**；**R6 文本批 + 合入前设计终态聚焦复核已完成——REVIEW-FEAT-103-R13（报告 `docs/reviews/review-FEAT-103-DESIGN-R7.md`，2026-10-22 机录）= APPROVED_WITH_NOTES / unresolved_blockers=0：R6 四项全 PASS、零回退 10/10 独立复验、+17 行 section 回归吻合；其 2×P3 备注（R7-P3-1 M4 后三处状态滞后 / R7-P3-2 C-1 交合入决策）中 R7-P3-1 由 R7 终态回写批闭合（§16）、R7-P3-2 登记交合入决策**；**R8 注（2026-10-23）：R7-P3-2（C-1 T09+ closed 变体）已由 M5 终态批闭环——归因为实现缺口（合同自始未被任何版本实现，安装态原版同错非补丁回归），Coordinator 裁定 b（方向 1 微批修复：claim live 短路提前跳过 resolve），修复后 t-m5 3/3 PASS；CODE R6 复审在途，本节不预写审查结果（§17）**。

**验收标准对照（R2 任务①–⑥）**：① F1 按方案 (a) 完整落到 §3.3（CH-1.1 代码与契约 / CH-1.2 步骤 4/5/6 / CH-1.3 / CH-1.5）、§8 T01+ 反例行、§9 性能行与 BR1'——多 record 生命周期（listener 依序 close、每 begin 独立 effect 兜底、first-reason-wins）与 tombstone 按 record 精确移除语义一致；② F2 S-C8 更正为 thisArg=null 无 scope 过滤（SDK 只读复核在案，§12 R2 表）+ §9 发射次数说明；③ F3 §5.5 措辞澄清、F4 T01+ root-owner 观测行落盘；④ R0 已闭环面（B1 机制层/B2/B3/CH-1.2 race 序列/CH-1.5 反例合同/D1–D3）零回退——本 R2 对 §4/§5.3/§5.4/§6 零合同改动（仅 §5.5 措辞、§7 registry 行描述性增量）；⑤ SOURCE/PROPOSED/NOT_RUN 标签纪律保持（S-C8 更正仍为 SOURCE 且注明 R2 复核；新增代码/合同均为 PROPOSED；运行面仍全 NOT_RUN）；⑥ 本交接状态节更新（implementation_authorized=false 保持）。

**交接状态**：

```text
design_revision=R8 (in-place revision of R1/R2/R3/R4/R5/R6/R7; R8 = post-M5 final write-back: legacy default/list closure (M5-3), T09+ implementation-anchor note (§8, claim live short-circuit skipping resolve), implementation_progress += M5 done, §16 NOT_RUN list two closures; filename kept per task instruction; NOTE: design-doc revision numbers R5/R6/R7/R8 are independent of review-report file numbering — review-FEAT-103-DESIGN-R5.md (REVIEW-FEAT-103-R8) reviewed the R4-P2 correction, review-FEAT-103-DESIGN-R6.md (REVIEW-FEAT-103-R11) reviewed the R5 increment, review-FEAT-103-DESIGN-R7.md (REVIEW-FEAT-103-R13) reviewed the R6 text batch + pre-merge final state)
r1_findings_addressed=F1(option-a multi-value owner index),F2(S-C8 thisArg=null correction),F3(section 5.5 wording),F4(T01+ root-owner observation row)
r0_findings_addressed=B1,B2,B3 (closure preserved in R2, not reopened)
r3_findings_addressed=S-C7 same-root predicate corrected to ctx.root identity (M1 measured events views are per-context; see §3.3 S-C7 correction)
r4_findings_addressed=closedIds tombstone contract (§5.6),fallback frozen-generation contract (§5.3 #6/#7 + 冻结 generation 传递),activation-failed internal terminal semantics (CH-1.6),M2 API contracts acquire/attach/selectWithAdmission/publicationCommit (§5.4/§6.1)
r5_findings_addressed=F-M3-1(§4.4 consumption-primitive mapping note: attach ≡ mountOwned/composeFromOwned),F-M3-2(§4.2 inheritance freeze anchor ruled = materializeTracked entry; S-U3 same-instant analogy retracted; alternative b spawn-entry hoisting documented with impact),F-M3-3(§4.2 error-face distinction: spawn passthrough agent-preset/closed vs cold-resume NOT_RESUMABLE+cause),F-M3-4(§4.2 notation aligned to implemented acquire({id}|{id,generation}|{parent}) — no signal param, abort handled at outer attempt boundary),N-R4-4(§5.4 status row now lists collect-failure isolation),§5.6 status row updated to M3 facts (closedIds delete after record.start() with activating gate)
reanchor=0.2.1-rc.2 (R1 verified read-only 2026-10-20T09:15:35Z-09:22:00Z; R2 F2 fact re-verification SDK read-only Read x4 2026-10-20, see section 12 R2 table)
independent_review=R5 increment focused re-review DONE (REVIEW-FEAT-103-R11, report docs/reviews/review-FEAT-103-DESIGN-R6.md, 2026-10-22, APPROVED_WITH_NOTES/unresolved_blockers=0 — anchor ruling accepted, F-M3-1~4 + status rows PASS, R5-approved-face zero-regression verified; its 2xP3 notes closed by R6 text batch per section 14); R6 text batch + pre-merge final-state re-review DONE (REVIEW-FEAT-103-R13, report docs/reviews/review-FEAT-103-DESIGN-R7.md, 2026-10-22, APPROVED_WITH_NOTES/unresolved_blockers=0 — R6 items 4/4 PASS, zero-regression 10/10 independently re-verified, pre-merge final state PASS; its 2xP3 notes: R7-P3-1 status-lag closed by R7 write-back per section 16, R7-P3-2 C-1 test gap registered for merge decision); R4/R4-P2 already reviewed (REVIEW-FEAT-103-R7 AWN/0 + R8 APPROVED/0); R3 already reviewed APPROVED_WITH_NOTES/unresolved_blockers=0
implementation_authorized=true（DEC-367，用户 2026-10-21 显式选择隔离实施；M3 实施面〔CH-2 + CODE R3 残留闭环〕、M4 合入前测试批〔纯测试、副本零改动〕与 M5 终态批〔含 Coordinator 裁定 b 的方向 1 微批修复——T09+ 为本设计 §8 已批合同，修复=实现既定合同非扩权；副本仅 controller 单文件 +9/−0〕均在该授权面内，CODE R3/R10 建议"M3/合入前处理"已执行）
implementation_progress=M1 done / M2 done / M2-FIX done / M3 done / M4 done / M5 done（M5=终态批：M5-1〔T09+ closed 变体〕归因为实现缺口〔claim :467 无条件 composeAgent → resolve 被 owned-closed 分类拒收，复用短路不可达；安装态原版同错=合同自始未实现非补丁回归〕→ 裁定 b 方向 1 微批修复闭环〔controller 副本 B9999EE6/3420L→24E3C2F4/3429L，claim live 分支 composeAgent 前短路块、与 reuseLive 短路同构、唯一差别=跳过 resolve、缺省 preset 不短路〕，修复后 t-m5 3/3 PASS（同一断言 FAIL→PASS 未弱化）、六族+T01 全绿〔B 12/12、A 12/12、C 14/14、d1 10/10、M4 6/6、T01 9/9〕、ctrl-prefix 安装态原版对照仍 FAIL=修复非空转铁证；M5-2 复用零 admission PASS；M5-3 legacy default/list PASS〔R5-P3-1 闭合，reg-prefix 同 PASS=legacy 原行为一致〕；CODE R6 复审在途——落笔时不预写审查结果）
runtime=NOT_RUN (host boot not executed; M1/M2/M3 evidence is in-process SOURCE level, see §11.1)
storage_regression=NOT_RUN
cordis_core_change_required=false (falsification exits declared in §3.5; S-C7 correction needs no core change)
webhook_coverage=NOT_OBTAINED (open item, not claimed)
upstream_patch_authorized=false (no external submission; isolated copy only)
release_authorized=false
timeout_or_eventual_cleanup_offset=FORBIDDEN_AND_NOT_USED
```

### 11.1 实施反馈（M1，2026-10-21）

**范围**：M1 只在**仓库内隔离副本**（`.governance/sandboxes/feat103-impl/`）复制 0.2.1-rc.2 相关上游模块并打补丁；已安装 SDK 只读（Junction 指向，无写入）；未启动宿主进程、未设置/读取 `DSH_HOME`、未读写真实 `~/.dsh`；未改产品代码/测试/契约/README；未 stage/commit。依据：DEC-367（用户显式授权隔离实施）、DEC-363（范围）；报告 `.codex-sandbox/FEAT-103/M1-REPORT.md`（SHA-256 `8298ADBB…B92F053`）。

**已发生的实现事实（如实记录，标签见下）**：

| # | 事实 | 证据 |
|---|---|---|
| 1 | 隔离副本 **11 个源文件双端 SHA-256 一致**（registry 3 + core/agent types 1 + core/agent-loop 1 + api/session-controller 1 + subagent 2 + spawn 1 + fork 1 + vendor/scope 1；`copy-manifest.txt` 全部 `一致性=True`） | M1 §1；`.codex-sandbox/FEAT-103/copy-manifest.txt` |
| 2 | registry 副本相对上游 **+171 行 / −0**（纯增量：`OwnedRecord` + 类成员 + 构造器监听） | M1 §1；副本 `lib/index.js` SHA-256 `233CF353…99BE88` |
| 3 | **T01+ positive：5 passed / 0 failed / exit 0**（UTC `2026-10-21T05:50:46.093Z → 05:50:46.473Z`） | `.codex-sandbox/FEAT-103/test-audit.txt`（SHA-256 `E2FAB9F2…0A3F99`）；M1 §3 |
| 4 | 变异体证伪：**no-observer** 3 passed / **2 failed**（exit 1；T01-a watchdog 复现原等待环、T01-c 无 `registry-disposed`）；**single-owner** 4 passed / **1 failed**（exit 1；T01-b 兄弟 record 未通知） | 同上；变异体仅在测试面，不在交付面 |

**标签纪律（不得读成发布/运行通过）**：

- 以上全部是**隔离副本内、进程内、SOURCE 级**证据——不是宿主运行、不是已安装 SDK 上的行为、不是产品交付物。
- **NOT_RUN**：host boot/真实 preset 会话（M2）、CH-2（精确 generation）/CH-3（claim/reuseLive/fallback）（M2+）、`T05+`/`T06+`/`T07+`/`T09+`/`T11+` 矩阵、legacy 交互面（owned record 与 `list`/`diagnostic`/`retain`/`mount`/`select` 的合同未定）、signal-abort 路径测试、性能（T10 census）、webhook（未取得源码）。`close-before-start` 的插入后复核分支在单线程同步段不可复现交错，**如实声明为防御性路径，未用 fake 时序冒充**。
- M1 同时证伪了一个设计文本事实（S-C7 的 `events` 身份谓词）——已在 §3.3 的「S-C7 更正」中更正，属本 R3 的唯一合同性文本变更；其余实现与 §3.3 CH-1.1～1.5 一致（落点见 M1 §2）。

## 12. 真实环境只读命令审计（Coordinator 机录 EVD 用）

本 R1 撰写期间对仓库外 SDK 的全部访问如下（严格只读；无运行/probe/写入/安装；`Read`=ZCode Read 工具按行窗口读取）。bash 命令 UTC 取自命令内 `date -u` 输出；Read 调用发生于相邻两条 bash 时间戳之间，以批次区间标注。

| # | UTC | 类型 | 命令/目标路径 | 结果摘要 |
|---|---|---|---|---|
| 1 | 2026-10-20T09:15:35Z | bash | `date -u`; `ls C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/`; `ls .../@deepseek-ai/dsh/node_modules/@deepseek-ai/` | @deepseek-ai 下仅 `dsh`（无 `deepseek-cli`）；N 下无 `dsh-subagent-in-process-driver`、无 `dsh-webhook`；有 subagent/spawn/fork 三包 |
| 2 | 2026-10-20T09:15:46Z | bash | 12 个包 `package.json` 的 version/directory grep + host dsh version | 全部 0.2.1-rc.2；cordis 4.0.5；loader 1.0.6（§2.1 表） |
| 3 | 2026-10-20T09:15:47Z | bash | `grep -n "internal/plugin"` cordis/lib/index.js + registry.d.ts；`grep emit(/\|.on(/\|events\.` | 命中 :970/:1093（发射）与 :237/:261/:280/:378/:390 等（dispatch/on）；types 命中 events.d.ts:218 |
| 4 | 09:15:47Z–09:17:15Z | Read×4 | cordis/lib/index.js 窗口 212-321、940-1019、1055-1129、1345-1404 | S-C2/S-C3/S-C4/S-C5 及 Fiber 构造/root 分支（S-C8/S-C9 依据） |
| 5 | 2026-10-20T09:17:15Z | bash | `grep new EventsService\|events =\|static filter` cordis/lib/index.js；`grep -rn internal/plugin cordis/lib/types/`；`grep -n on(name` | :1687 单例装配；events.d.ts:218；:371 EventsService.on |
| 6 | 09:17:15Z–09:17:52Z 前 | Read×3 | cordis/lib/index.js 325-419、1645-1704；cordis/lib/types/events.d.ts 185-244 | S-C6（register/on/assertActive）、S-C7（root 构造器）、Events 接口全文（S-C1） |
| 7 | 09:17:52Z 前 | Read×2 | cordis/lib/types/registry.d.ts 30-159；dsh-api-session-controller/lib/index.js 345-529 | S-C10；S-T1–S-T5（composeAgent/claim/reuseLive/reuseSetup/createAgent） |
| 8 | 2026-10-20T09:21:52Z 前 | Read×3 | dsh-subagent/lib/index.js 355-409、1780-1844、2145-2194 | S-U2/S-U3；S-U4；S-U5 |
| 9 | 同上区间 | Read×3 | dsh-subagent/lib/types/child-agent.d.ts 全文；spawn-in-process 1-55；fork-in-process 1-60 | S-U1；S-U7；S-U8 |
| 10 | 同上区间 | Read×3 | dsh-agent-loop/lib/index.js 1780-1824、1915-1974；dsh-agent/lib/types/index.d.ts 20-139 | S-L1；S-L2/S-L3；S-A1 |
| 11 | 同上区间 | Read×3 | dsh-agent-preset-registry/lib/index.js 462-551、628-722、744-812 | S-R1–S-R7 |
| 12 | 同上区间 | Read×4 | dsh-scope/lib/index.js 268-312；dsh-session/lib/index.js 1850-1894、1572-1611；dsh-session-persistence/lib/types/handle.d.ts 1-110 | S-S2；S-S1；S-P1 |
| 13 | 2026-10-20T09:21:52Z | bash | grep fork/presetForSession/presetForObservation（controller）；materialize/hasIndependentPresetSelection（subagent） | fork :849/:880；materializeTracked :1764、materialize :1672、hasIndependentPresetSelection :2258 |
| 14 | 09:21:52Z 后（≤09:22:00Z） | Read×2 | controller 845-909；subagent 2255-2272 | S-T6（fork 全链）；S-U6 |

注：本表为架构设计取证（重锚 0.2.1 接口事实），非运行验证；所有 SOURCE 事实的运行时行为仍 NOT_RUN。原始设计 §10 与 R0 §8 的历史命令审计不变。

### R2 修订事实复核（本会话，严格只读；Coordinator 机录 EVD 用）

R2 修订（F2 事实更正 + F1 合同依据复核）期间的 SDK 访问如下。**时戳声明**：Architect 角色工具权限无 Bash（`agents/architect.md`），无法取命令级 UTC 时戳；访问发生于 2026-10-20 本会话、晚于 R1 审查取证终点 09:45:06Z——如实声明，不编造精确时戳。

| # | UTC | 类型 | 目标路径/行窗口 | 结果摘要 |
|---|---|---|---|---|
| R2-V01 | 2026-10-20（>09:45:06Z，无命令级时戳） | Read | N/cordis/lib/index.js :245-274 | `dispatch` :258-264：:259 thisArg 仅在 args[0] 为 object/function 时取（否则 null）；:262 filter=thisArg?.[Context.filter]；:263 `!filter` 短路全量 hook——S-C8/S-C3 更正依据 |
| R2-V02 | 同上 | Read | N/cordis/lib/index.js :963-987 | `emitPluginDisposed` :968-984：:970 args=["internal/plugin", fiber]、:973 dispatch、:978-983 per-callback try/catch + Promise rejection 消费——S-C2 复核一致 |
| R2-V03 | 同上 | Read | N/cordis/lib/index.js :1070-1119 | Fiber.dispose 闭包 :1075-1091（:1078 uid=null → :1079 emitPluginDisposed → :1080-1083 移除 → :1084 INACTIVE → :1085-1088 inertia=_unload → :1089 await）；创建发射 :1093（含 :1094 catch）；root 分支 :1102-1113（uid=0、dispose=restart）——S-C4/S-C8/S-C9 复核一致 |
| R2-V04 | 同上 | Read | N/cordis/lib/index.js :275-292 | `emit` :280-282：`dispatch("emit", args).map(cb=>cb(...args))`，同步、**无 per-callback try/catch**——:1093 创建发射路径闭合（S-C8 "判别只靠 uid"与遏制不对称注的依据） |

仓库内读取（非用户环境）：R1 审查报告、R1 文档、R0 报告、原设计（复核 F1 合同依据 ：70-71/:192）。SDK 零写入、零运行、零 probe、零安装；`.governance/` 零写入。

### R3 修订事实复核（本会话，严格只读；Coordinator 机录 EVD 用）

R3 修订（S-C7 谓词更正 + M1 实施反馈 + 交接状态）期间的只读核对如下。**未运行 cordis/host、未读真实 SDK、未写 `.governance`；除本设计文档外仓库零写入。**

| # | UTC 起 → 止 | 类型 | 目标 | 结果摘要 |
|---|---|---|---|---|
| R3-V01 | `2026-10-21T05:53:25.956Z` → `05:53:26.012Z` | PowerShell 只读 | 设计文档修订前 hash/行数；`M1-REPORT.md`；`test-audit.txt`；sandbox registry `lib/index.js`；`DEC-367` 存在性 | 设计 `7B43101C…EBA3734`（412 行 / 62,356 B）；M1 报告 `8298ADBB…D92F053`；test-audit `E2FAB9F2…0A3F99`；registry 副本 `233CF353…99BE88`；DEC-367 命中 1；exit 0 |
| R3-V02 | `2026-10-21T05:53:11.323Z` → `05:53:11.368Z` | PowerShell 只读 | sandbox registry `lib/index.js` L595-604；`test-audit.txt` 三行 | L596-604：`if (ownerCtx.root !== this.ctx.root) throw ownedRegistrationError("OWNER_ROOT_MISMATCH", …)`，L600-603 注释留证并指向 M1 报告；审计行：positive 5/0/exit0、no-observer 3/2/exit1、single-owner 4/1/exit1；exit 0 |

> 说明：上表只复核**文本与产物哈希/行内容**，不构成 M1 结果的重新运行；M1 的运行结论以其报告与 `test-audit.txt` 为准（§11.1）。M1 报告 §4 已如实声明其复制/打补丁等命令**未内嵌命令级 UTC**，本表不替其补造时戳。

### R4 修订事实复核（本会话，严格只读；Coordinator 机录 EVD 用）

R4 修订（closedIds 合同 + fallback 冻结 generation + activation-failed 终态 + M2 API 合同）期间的只读核对如下。**未运行 cordis/host、未读真实 SDK、未写 `.governance`；除本设计文档外仓库零写入。**

| # | UTC 起 → 止 | 类型 | 目标 | 结果摘要 |
|---|---|---|---|---|
| R4-V01 | `2026-10-22T06:09:17.808Z` → `06:09:17.847Z` | PowerShell 只读 | `review-FEAT-103-CODE-R2.md`；`M2-REPORT.md`；`M2-TEST-AUDIT.md`；`M1-FIX-REPORT.md`；`.governance/review-FEAT-103-R*.md` 计数；设计文档当前 hash | CODE R2 `AD32DF7C…8F0544D9`；M2 报告 `C35FD656…C097FB6`；M2 审计 `A7421DFE…A0376FC0`；M1-FIX 报告 `F9562B7D…2915B9BB`；review records R0–R6 共 7 个；设计（修订中）`83F32EAF…6D52CE`（483 行）；exit 0 |
| R4-V02 | 本会话（read 工具调用未内嵌命令级 UTC，如实声明、不补造时戳） | read 工具 | 设计 §5.3/§5.4/§6.1/§11 现状；M2 报告 §2/§3；M1-FIX 报告 §1.2；`review-FEAT-103-R0…R6` 结论字段 | 复核到：M2 已实现 acquire/attach/selectWithAdmission/publicationCommit 与 closedIds（SOURCE 级）；M1-FIX 已实现 activation-failed 终态；R3 设计复审=APPROVED_WITH_NOTES；R6=CODE R2=NEEDS_CHANGE |

> 说明：R4-V02 为 read 工具调用，角色工具面不打印命令级 UTC，按 R2 表同口径如实声明；本表只复核文本与哈希，不构成任何运行结论。

## 13. 2026-10-22 R4 修订记录（承接 REVIEW-FEAT-103-CODE-R2 / M2）

- 修订对象：本文件；修订前 SHA-256 = `A1F676EE27056F0C8BC32BE9F27DC31934EFF25156A75DF7B374E2DA80A008CF`（454 行 / 68,925 B；= R3 复审输入字节）。
- 依据：`docs/reviews/review-FEAT-103-CODE-R2.md`（REVIEW-FEAT-103-R6，NEEDS_CHANGE/1；SHA-256 `AD32DF7C…8F0544D9`）P1-1、P2-1/P2-4/P3-5；`M2-REPORT.md`（`C35FD656…C097FB6`）与 `M2-TEST-AUDIT.md`（`A7421DFE…A0376FC0`）；`M1-FIX-REPORT.md`（`F9562B7D…2915B9BB`）；DEC-367（隔离实施授权）。
- 修订纪律：不改写历史失败轨迹与 §3.5 证伪出口；不新增未验证能力声明；实现事实一律标 SOURCE 级并保留 NOT_RUN；四项之外的合同不发散。

| 项 | 依据 | 修订位置 | 修订内容 |
|---|---|---|---|
| R4-1 `closedIds` 墓碑合同 | CODE R2 P2-4 明确要求；P2-1/P3-5 证据 | **§5.6（新增，7 条）** | closed/not-found 消费者分类与判定点；墓碑创建/清除（仅成功重注册后、失败保留、不得在校验前清除）；legacy `register`/disposer/unregister 不写墓碑（legacy 关闭仍 not-found）；旧 token 换代隔离（冻结 G1 一律 closed）；清理策略；**明示取代/细化 §5.3 #6/#7 并覆盖 fallback** |
| R4-2 fallback 冻结 generation | CODE R2 P1-1（NEEDS_CHANGE 主因） | **§5.3 #6/#7 增补 + 「冻结 generation 的传递」bullet** | 回退 attempt 必须携带首个 attempt 的冻结 generation（composition 携带标识），不得按 id 重取；同一 generation closed/retired → `agent-preset/closed`；G1→G2 场景禁止静默取 G2；补用例要求 |
| R4-3 `activation-failed` 终态 | M1-FIX 的 R0-F2 修复面；CODE R2 判定表「M1 遗留 P3=PASS」 | **§3.3 CH-1.6（新增）** | ready failed → closed(`activation-failed`) → definitions 删除 → closed settle → drain → detach/forget；first-reason-wins；**内部终态、不进公开 `close(reason)` 四值词表**；SOURCE 级状态与 NOT_RUN 声明 |
| R4-4 M2 新 API 契约 | CODE R2 判定表；M2 实现事实（A1-A6） | **§5.4「R4 增量」块 + §6.1 owned registry `publicationCommit` bullet** | acquire token `HELD→ATTACHED→COMMITTED`、`release()` 仅 HELD；attach 两阶段（`commit()`/`publicationCommit()`，后者同步不 append）+ **attach 事务化**（join/rebind 成功后才置 ATTACHED，失败回滚释放）；selectWithAdmission 回滚（append 失败先恢复旧 binding、不 collect）；冻结 generation 一致性；成功后 collect 失败隔离 |
| 交接状态 | 任务指令 + DEC-367 | **§11 代码块与 prose** | `design_revision=R4`；`implementation_progress=M1 done / M2 done / M2-FIX in progress`；`independent_review=R4 待独立复审（RECHECK-FEAT-103-R8，Coordinator 指定轮次）`；`r4_findings_addressed=…`；`upstream_patch_authorized=false`、`release_authorized=false` 保持 |

- **编号偏差说明**：派单要求追加「§17 修订记录」；本文件当前止于 §12（不存在 §13–§16），故本节记为 **§13**，以免制造空号。若需改为 §17 编号请告知。
- **未纳入本次修订**：M2-FIX 的实现修正（P2-1 清除时机、P2-3 attach 事务、P1-1 冻结传递）与其测试补齐 → 实现面，交 CODE R3 复审；真实 host/publish 链、CH-2 矩阵、legacy 回归仍 NOT_RUN。
- **待复审**：本 R4 修订须经独立复核（RECHECK-FEAT-103-R8）；通过前不得据此声明设计完成或运行通过。（**R5 注**：该复核已完成——REVIEW-FEAT-103-R8 = APPROVED/0，见 §11。）

## 14. 2026-10-22 R5 修订记录（承接 M3-REPORT §6 F-M3-1~4 / N-R4-4 / 状态行收敛）

- 修订对象：本文件；修订前 SHA-256 = `30E6FF022EB309FF1895ADE1BA15B9C25D53154FAF9F75792E01339C2EBE7FB5`（515 行 / 83,810 B；= R8 复核输入字节，M3-REPORT 收工复核一致）。
- 依据：`.codex-sandbox/FEAT-103/M3-REPORT.md`（SHA-256 `AEA24919…`，173 行）§6 findings F-M3-1~4 与 §2 逐项落点；`docs/reviews/review-FEAT-103-CODE-R3.md`（REVIEW-FEAT-103-R9，AWN/0）§4 R3-P3-2/R3-P3-4；`docs/reviews/review-FEAT-103-DESIGN-R5.md`（REVIEW-FEAT-103-R8，APPROVED/0）§3 N-R4-4 未判注记；DEC-367。
- 修订纪律：不改写历史失败轨迹与 §3.5 证伪出口；R5 已批五项修正（N-R4-1/2/3/5/6）零回退；实现事实一律 SOURCE 级并保留 NOT_RUN；只做注记/裁定/状态行，不重写既有已批节。
- **版本号消歧**：本节"R5"是**设计文档版本号**（R1→R2→R3→R4→R4-P2〔仍在 R4 世系〕→R5）；审查报告文件名 `review-FEAT-103-DESIGN-R5.md`（=REVIEW-FEAT-103-R8）的"R5"是**审查轮次命名**（其对象为 R4-P2 修正），与本文档版本号无对应关系。

| 项 | 依据 | 修订位置 | 修订内容 |
|---|---|---|---|
| R5-1 消费原语映射（F-M3-1） | M3-REPORT §6 F-M3-1 | §4.4 新增映射注记 | `mountOwned`/`composeFromOwned` 为设计期原语名；实现面为 §5.4 acquire+attach（CODE R3 已批）；`attach(childCtx)` 对新子即两原语语义；M3 `applyChildCompositionOwned` 内部消费 attach，无重复 API |
| R5-2 继承冻结锚点裁定（F-M3-2，唯一实质设计决定） | M3-REPORT §6 F-M3-2 + §2.1（acquireParentAdmission :897-920 同步求值、materializeTracked :1822-1833）+ B3/B6/B12 测试事实 | §4.2 新增「继承分支冻结锚点（R5 裁定）」段；继承行更新 | **裁定 a) 合同锚点 = materializeTracked 编排入口**（spawn/cold 统一，入口内同步冻结）；撤销"与 S-U3 同一时点纪律"比拟（策略参数=请求性质须入口捕获 vs 资源状态=消费性质消费点冻结）；窗口语义论证（换代→观察到新代=继承现行代语义、关闭→closed 拒收、无静默路径）；双 fence 兜底（attach 前置 + publicationCommit）；备选 b) spawn 入口上提+穿参（:1438/:2221 签名）作为排除项成文（收益不改变安全合同、成本扩大 API 面） |
| R5-3 错误面区分（F-M3-3） | M3-REPORT §6 F-M3-3 + B4 实测 | §4.2 失败行后新增「错误面区分」bullet | spawn 面透传 `agent-preset/closed`；cold resume 面包为 `NOT_RESUMABLE` + cause（cause.code 可溯源 closed）——沿用既有 NOT_RESUMABLE 纪律（S-U5 面）；共同保证=closed 根因不丢失、无静默回退 |
| R5-4 记法对齐（F-M3-4） | M3-REPORT §6 F-M3-4 | §4.2 表格前新增「记法对齐」注记 | 伪码 `acquireAdmission(ownerCtx,…,signal)` → 实现 `acquire({id}|{id,generation}|{parent})`（§5.4 已批面）；无 ownerCtx 形参、无 signal 形参（abort 由外层 attempt 边界 try/finally 处置，无 token 可泄漏） |
| R5-5 §5.4 状态行更新 + N-R4-4 补列 | CODE R3 §4 R3-P2-1（已修）；DESIGN-R5 §3 N-R4-4 未判 | §5.4 状态 bullet 重写 | 状态更新至 M3 后（A10 collect 隔离/A11 attach 前置/A12 closedIds 移位）；补列 R4 版漏列的"成功后 collect 失败隔离"缺口项；残余 NOT_RUN 面（rebind 抛错分支、真实 publish 链、host）如实保留 |
| R5-6 §5.6 状态行更新（R3-P3-2/P3-4 闭合） | CODE R3 R3-P3-2（文本差）+ R3-P3-4（:307 滞后）；M3 §2.4（:664-674/:711-712 + activating 门控 + A12/naive-move 变异体） | §5.6 第 7 条重写 | 清除时机演进链（校验前→插入后→start 后+门控）；"启动前失败保留墓碑"门控语义与同步窗口论证；host NOT_RUN 保持 |
| 交接状态 | 任务指令 + DEC-367 | §11 硬门槛段 + 代码块 | `design_revision=R5`（含消歧注）；`r5_findings_addressed` 六项；`implementation_progress=M1/M2/M2-FIX/M3 done`；`independent_review=R5 增量待聚焦复核`；硬门槛候选表补 R5 锚点二候选 |

- **R5 已批面零回退自检**：N-R4-1（§5.3 错误码映射段）未触碰；N-R4-2（§3.3 CH-1.6 `_forget` 措辞："只清 owner 多值索引与 id 主表；closedIds 墓碑保留"）未触碰——§5.6 第 7 条状态行更新与该措辞一致（墓碑保留语义不变，仅清除时机描述更新）；N-R4-3（§9 容量行）未触碰；N-R4-5（§5.3 两类 fallback 用例要求）未触碰；N-R4-6（文首一致性）由本次文首更新延续（R5 标识与 §11 一致）。
- **待复审**：本 R5 增量须经独立聚焦复核（对象=F-M3-1~4 收敛面、锚点裁定与状态行更新，Coordinator 指定轮次）；通过前不得据此声明设计完成或运行通过。（**R6 注**：该复核已完成——REVIEW-FEAT-103-R11 = APPROVED_WITH_NOTES/0，见 §11。）

## 15. 2026-10-22 R6 修订记录（合入前文本批，承接 REVIEW-FEAT-103-R11 2×P3 + §11 复核状态回写）

- 修订对象：本文件；修订前 SHA-256 = `2CA8A9B813E7B0DE2335C396F5709ADE17D67C4C1244AFE7896BEFE20B3FA4F3`（549 行 / 96,752 B；= REVIEW-FEAT-103-R11 复核输入字节，R11 报告独立复算一致）。
- 依据：`docs/reviews/review-FEAT-103-DESIGN-R6.md`（REVIEW-FEAT-103-R11，APPROVED_WITH_NOTES/0，SHA-256 `ACEF4068…57EE0`）§3 R6-P3-1/R6-P3-2；REVIEW-FEAT-103-R11 机录行（evidence-log，2026-10-22）；任务派单（M4 合入前批——P3 文本收敛）。
- 修订纪律：纯文本批——零合同变更、零新增能力声明、零 SOURCE/PROPOSED/NOT_RUN 标签变更；R4-P2 已批五项（N-R4-1/2/3/5/6）与 R5 已批四项收敛面 + 锚点裁定零回退；裁定 a) 的实质内容（依据 1-3 + 备选 b 排除）不变，仅修辞替换。
- **版本号消歧（延续 §14 同注）**："R6"本节为**设计文档版本号**（R1→…→R5〔R11 已复核〕→R6〔本批〕）；"M4"是**实施里程碑命名**（M1/M2/M3 之后的合入前阶段），本批为 M4 里程碑内的设计文本收尾，二者非同一编号轴。审查报告文件名 `review-FEAT-103-DESIGN-R6.md`（=REVIEW-FEAT-103-R11）的"R6"是审查轮次命名（其对象为 R5 增量），与本版本号无对应关系。

| 项 | 依据 | 修订位置 | 修订内容 |
|---|---|---|---|
| R6-1 acquire 形态衔接（R6-P3-1） | R11 §3 R6-P3-1（:300 单形态合同句与 §4.2 三形态注记衔接不足） | §5.4「R4 增量」首 bullet | `acquire({id})` 合同句内补半句："M2-FIX 起扩展为 {id, generation}（回退携带冻结代，§5.3）、M3 起扩展为 {parent}（继承分支，§4.2）——三形态合同统一见 §4.2 记法注记"——单独阅读 §5.4 亦可获知全形态 |
| R6-2 "首次可行动"修辞替换（R6-P3-2） | R11 §3 R6-P3-2（修辞依赖解释、裁定实质不依赖） | §4.2 依据 1 | "materializeTracked 是子作为 consumer 首次可行动的时点" → "materializeTracked 是 spawn 与 cold resume 汇合的子编排入口——子编排上下文在该入口就绪、agents.create/resume 在其后发起，冻结即取该入口的父现行代"（附 R6 措辞替换注记；裁定实质=依据 2 窗口语义 + 依据 3 双 fence，未变） |
| R6-3 §11 复核状态回写 | R11 机录（REVIEW-FEAT-103-R11 AWN/0）+ 上轮 §11 "R5 待聚焦复核 PENDING" 滞后 | §11 硬门槛自检段 + 代码块 `independent_review` 行 + §14 待复审行附注 | PENDING → 已完成（REVIEW-FEAT-103-R11 AWN/0：锚点裁定接受、F-M3-1~4 PASS、零回退验证；2×P3 由本批收敛）；§14 待复审行附 R6 注 |
| R6-4 版本号升级与文首一致性 | 本批修订事实 + N-R4-6 文首↔§11 一致口径 | 文首 L1/L3/L5 + §11 `design_revision` | `design_revision=R5` → `R6`（消歧注更新：R5/R6 设计版本号与审查报告文件编号独立）；文首标题/日期/性质段同步追加 R6 描述 |

- **零回退自检**：R4-P2 已批五项锚点原样（§5.3 错误码映射段 / §3.3 `_forget` 措辞 / §9 容量行 / §5.3 fallback 用例段 / 文首一致性——由 R6-4 延续）；R5 已批面（§4.4 映射注记 / §4.2 裁定段+错误面 bullet+记法注记 / §5.4·§5.6 状态行）除 R6-1/R6-2 两处指定小修外原样；锚点裁定 a) 的依据 2/3 与备选 b) 排除项零触碰；§3.5 证伪出口、§12/§13 历史审计零改写。
- **待复审声明**：本 R6 文本批为 R11 备注的最小收敛（2×P3 + 状态回写 + 版本号），按 R11 §3 原文"可留合入前小修"授权执行；若 Coordinator 裁定 R6 增量亦须独立聚焦复核，对象=本节四项（无新合同面）。（**R7 注**：该复核已完成——REVIEW-FEAT-103-R13 = APPROVED_WITH_NOTES/0，R6 四项全 PASS，见 §11。）

## 16. 2026-10-22 R7 修订记录（M4 后终态回写批，承接 REVIEW-FEAT-103-R13 R7-P3-1 / M4-REPORT）

- 修订对象：本文件；修订前 SHA-256 = `D8DE745CA7CE826EA5DE4129B4CE53FC26C9011775D8E32553BC461E5C1B0092`（566 行 / 102,024 B；= REVIEW-FEAT-103-R13 复核输入字节，R13 报告独立复算一致）。
- 依据：`docs/reviews/review-FEAT-103-DESIGN-R7.md`（REVIEW-FEAT-103-R13，APPROVED_WITH_NOTES/0，SHA-256 `AB191483…D9476F`）§3/§4 R7-P3-1（M4 后三处状态滞后，"建议合入前终态回写批一次处理"）；`.codex-sandbox/FEAT-103/M4-REPORT.md`（SHA-256 `98A54305…F135C7`，121 行）——M4 事实（六项 PASS + webhook/多 Cordis NOT_APPLICABLE、纯测试批副本七文件零改动、M4 权威轮 6/6、prefix-subagent 对照 4/2）；机录 REVIEW-FEAT-103-R12（CODE R5 AWN/0）/R13（DESIGN R7 AWN/0）；任务派单（M5 终态批——设计终态回写）。
- 修订纪律：纯状态回写批——零合同变更、零新增能力声明、零 SOURCE/PROPOSED/NOT_RUN 标签升级；R4-P2 已批五项、R5 已批收敛面与锚点裁定、R6 已批四项零回退；**M5 终态批（C-1 + T11+ legacy default/list 用例）落笔时在途——本批一律写"在途"，不预写结果**。
- **版本号消歧（延续 §14/§15 同注）**："R7"本节为**设计文档版本号**（R1→…→R6〔R13 已复核〕→R7〔本批〕）；"M4/M5"是**实施里程碑命名**；审查报告文件名 `review-FEAT-103-DESIGN-R7.md`（=REVIEW-FEAT-103-R13）的"R7"是审查轮次命名（其对象为 R6 文本批+合入前终态），与本版本号无对应关系——三轴独立。

| 项 | 依据 | 修订位置 | 修订内容 |
|---|---|---|---|
| R7-1 §11 implementation_progress 补 M4 | R7-P3-1 ①（§11 L426 不含 M4 done） | §11 代码块 `implementation_progress` 行 + `implementation_authorized` 行 | 补 `M4 done`（六项 PASS + NOT_APPLICABLE、纯测试批副本零改动、R12/R13 双聚焦复核、M4 权威轮 6/6）；M5 在途注记（不预写）；authorized 行补 M4 面表述 |
| R7-2 §5.4 rebind 抛错分支闭合 | R7-P3-1 ②（§5.4 状态行 rebind NOT_RUN 残余已被 M4-2 闭合） | §5.4 状态 bullet | "未覆盖/未运行：attach 的 rebind 抛错分支" → 已由 M4-2 闭合（原错误透传/token HELD/旧 binding 不变/users 不变/release 归零——无 ATTACHED 泄漏无半绑定，R12 复核）；剩余 NOT_RUN=真实 publish 链、host/运行面 |
| R7-3 §5.6 legacy 分类面部分闭合 | R7-P3-1 ③（§5.6 "legacy 面未实现/未测"已被 M4-1 部分闭合） | §5.6 第 7 条状态行 | legacy 分类对照已闭合（M4-1：register→unregister→acquire=not-found 且无墓碑、Duplicate、owned 注册→close→closed）；**default/list 回归由 M5 终态批补齐（在途）**；容量策略维持未测 |
| R7-4 版本号 + NOT_RUN 终态清单 | R13 §3 终态判定 + 任务派单 | 文首 L1/L3/L5 + §11 `design_revision` + 本节 | `design_revision=R7`；文首三处同步；**NOT_RUN 终态清单正式表达见下方**（随 0.99 发布链承载口径） |

- **NOT_RUN 终态清单（正式表达，随 0.99 发布链承载——与执行包 next_commands 口径一致；**R8 更新（2026-10-23）：原第 4/5 两条〔T09+ C-1、T11+ default/list〕已由 M5 终态批闭环移出清单，闭环去向见 §17；剩余 5 条如下**）**：
  1. **真实 host publish 链**（AgentLoop `prepared.publish` + `sessions.enter` 真实运行；M1-M5 全部证据为隔离副本进程内 SOURCE 级）——host 面验证需真实环境防护（隔离环境/完整备份+一致性校验/逐项授权三选一），交合入/发布决策；
  2. **物理 storage 注入**（M4-5 的 selected append gap 为进程内 fixture 面，不含 AgentLoop scope 回滚与持久化句柄）；
  3. **startActivation 全链**（M4-4 assertCapabilities 为方法级，经 startActivation 的全链 NOT_RUN，M4-REPORT 如实披露）；
  4. **T10 census 全量面**（M4-3 已记 58~66ms/1000 周期记录值；全量 census 面 NOT_RUN）；
  5. **0.1.x 兼容**（基线 0.2.1-rc.2 重锚，0.1.x 不在覆盖声明内）。
- **零回退自检**：R4-P2 五项锚点（§5.3 错误码映射段 / §3.3 `_forget` 措辞 / §9 容量行 / §5.3 fallback 用例段 / 文首一致性——由 R7-4 延续）；R5 面（§4.4 映射注记 / §4.2 裁定段+错误面 bullet+记法注记 / §5.4·§5.6 状态行——除 R7-2/R7-3 两处指定状态行更新外原样，裁定实质零触碰）；R6 面（§5.4 形态衔接半句 / §4.2 修辞替换 / §11 R11 回写）；§3.5 证伪出口、§12/§13/§14/§15 历史审计零改写（§15 仅末尾追加 R7 注一行）。
- **待复审声明**：R6 批的"待复审声明"已由 R13 满足（见 §15 末 R7 注）；本 R7 批为 R13 §3 原文建议的"合入前终态回写批一次处理"授权执行（纯状态回写，无新合同面）；若 Coordinator 裁定 R7 增量亦须独立聚焦复核，对象=本节四项 + NOT_RUN 终态清单表达。

## 17. 2026-10-23 R8 修订记录（M5 后最终回写批，承接 M5-REPORT + R7 批"M5 在途"交接项）

- 修订对象：本文件；修订前 SHA-256 = `DDF7875E091351386C613C6170477DF260E2F7C335C15852EBBC2728F7A6F143`（591 行 / 109,537 B；= REVIEW-FEAT-103-R13 复核后 R7 批落盘字节）。
- 依据：`.codex-sandbox/FEAT-103/M5-REPORT.md`（M5 终态批·微批修复闭环版：M5-1 KNOWN-GAP 归因 → Coordinator 裁定 b 方向 1 微批修复 → 3/3 PASS；M5-2/M5-3 PASS；六族+T01 全绿；副本仅 controller `B9999EE6/3420L → 24E3C2F4/3429L`〔+9/−0〕，其余六文件与 M3/M4 基线逐位一致；安装态七文件零写入）；R7 批 §16"在途"交接项；任务派单（设计最终回写）。
- 修订纪律：纯状态回写与锚注批——零合同变更（§8 T09+ 锚注仅记录已批合同的实现面，不改合同语义）、零新增能力声明、零 SOURCE/PROPOSED/NOT_RUN 标签升级（NOT_RUN 清单两条移出=实现闭环的如实反映，非标签升格）；R4-P2 五项、R5 收敛面与锚点裁定、R6 四项、R7 四项零回退。**CODE R6 复审（对象=controller 微批 +9/−0 + M5 报告全套）落笔时在途——本批不预写审查结果**。
- **版本号消歧（延续 §14/§15/§16 同注）**："R8"本节为**设计文档版本号**（R1→…→R7〔R13 已复核 R6 批与合入前终态；R7 批待聚焦复核〕→R8〔本批〕）；"M5"是**实施里程碑命名**；三轴独立（审查报告文件名的 R 编号是审查轮次命名）。

| 项 | 依据 | 修订位置 | 修订内容 |
|---|---|---|---|
| R8-1 §5.6 legacy default/list 闭合 | M5-3 PASS（R7 批 §16 第 5 条在途项的闭环） | §5.6 第 7 条状态行 | "default/list 由 M5 终态批补齐（在途）" → 已闭合（M5-3：list()/defaultId/resolve() 落 default/isDefault 用例 PASS；reg-prefix 同 PASS=legacy 原行为一致零回归） |
| R8-2 §8 T09+ 实现面锚注 | M5-1 归因+修复（claim :467 无条件 composeAgent→resolve 拒收；短路块=composeAgent 前跳过 resolve、与 reuseLive 同构、缺省不短路） | §8 T09+ 行 | 补 R8 实现面锚注（合同语义不变；记录"该合同在 M5 前从未被任何版本实现〔安装态原版同错〕非补丁回归"的归因事实） |
| R8-3 §11 M5 done 回写 | M5-REPORT §2.1/§3/§6 | §11 硬门槛自检段 R8 注 + 代码块 `implementation_progress`/`implementation_authorized` | M5 在途 → done（含 KNOWN-GAP 归因→裁定 b 方向 1 微批修复闭环、controller 新 SHA、3/3+六族+T01 全绿、ctrl-prefix 仍 FAIL=非空转铁证；authorized 行补 M5 面授权依据=T09+ 已批合同的实现）；CODE R6 在途不预写 |
| R8-4 §16 清单收敛 + design_revision=R8 | M5 双闭环 + 本批版本事实 | §16 清单头注与两条 + 文首 L1/L3/L5 + §11 `design_revision` | T09+ C-1 与 T11+ default/list 两条移出 NOT_RUN 终态清单（闭环去向=本节），清单更新为剩余 5 条（真实 host publish 链/物理 storage 注入/startActivation 全链/T10 census 全量/0.1.x）；design_revision=R7 → R8，文首三处同步 |

- **零回退自检**：R4-P2 五项锚点（§5.3 错误码映射段/§3.3 `_forget` 措辞/§9 容量行/§5.3 fallback 用例段/文首一致性——由 R8-4 延续）；R5 面（§4.4 映射注记/§4.2 裁定段+错误面 bullet+记法注记）零触碰；R6 面（§5.4 形态衔接半句/§4.2 修辞替换/§11 R11 回写）零触碰；R7 面（§5.4 rebind 闭合/§11 M4 回写）除 §5.6 第 7 条在途句按 R8-1 指定闭合外原样；§3.5 证伪出口、§12/§13/§14/§15/§16 历史审计零改写（§16 仅清单头注与两条按 R8-4 指定更新）。
- **待复审声明**：本 R8 批含一处合同关联锚注（R8-2）与状态终值回写；若 Coordinator 裁定 R8 增量须独立聚焦复核，对象=本节四项 + §16 清单收敛；与 CODE R6 复审（controller 微批）并行无冲突。
