# FEAT-103 — DSH 隔离补丁设计 R1 修订版独立设计审查 R1（承接 R0 审查链）

- 日期：2026-10-20（Asia/Shanghai）；取证 UTC 09:31:14Z–09:45:06Z（逐条见 §8）。
- 身份：**新实例** Design Reviewer（本 R1 审查实例）；不是 R0 审查实例（R0 由前会话实例完成），不是设计作者。已完整读取 R0 报告并逐 finding 对照 R1。按 `agents/design-reviewer.md`、`skills/design-review/SKILL.md` 执行；任务指令明确授权本实例对真实安装 SDK 严格只读核验（Read/grep/ls）并逐条上报命令。
- 审查对象：`docs/architecture/dsh-upstream-owned-registration-R1.md`，SHA256 `5367f9abd40ba8d0cef20f3384c5363ed215a12ac5e3424e7c1584ac2a06d27a`（immutable）。
- 只读输入：R0 报告 `docs/reviews/review-FEAT-103-DESIGN-R0.md`（SHA256 `ae848da49a09eae2f95bfd6bdf6f979b22c87192a55d3ff808fadf0e02fcd52f`）；原设计 `docs/architecture/dsh-upstream-owned-registration.md`（SHA256 `be5741d44a74751efaabe371f50fd3ce3a4d0e3a7e8ce041faa0c6cae12fb52f`——与 R0 记录的输入 hash 一致，未被改动）；SDK `C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh`（0.2.1-rc.2）严格只读。
- 权限边界：仅写本报告一个文件；未运行/probe/写入 SDK；未写 `.governance/`；未与用户交互；未做最终决策。真实环境命令逐条见 §8（Coordinator 机录 EVD 用）。

## 1. 结论

```text
conclusion=NEEDS_CHANGE
unresolved_blockers=1
round=1
review_identity=NEW_INDEPENDENT_INSTANCE_R1
predecessor_review=docs/reviews/review-FEAT-103-DESIGN-R0.md (NEEDS_CHANGE_3)
review_scope=FEAT103_R1_REVISION_0.2.1_REANCHOR_B1_B2_B3
current_sdk=0.2.1-rc.2 (manifest-verified, hash-checked vs R0)
implementation_authorized=false
runtime=NOT_RUN
storage_regression=NOT_RUN
r0_findings_closure=B1:PASS B2:PASS B3:PASS
new_findings=F1(BLOCKING/P1) F2(P2) F3(P3) F4(P3)
```

**R0 三项 BLOCKING（B1/B2/B3）全部真实闭环**：R1 的机制选型、分支冻结与生命周期合同全部有当前 0.2.1-rc.2 源码逐行支撑（本实例独立只读复核，非采信 Architect 自检），且不回避 R0 反例（CH-1.5/T01+ 硬验收、明文禁止 timeout/最终清理抵销在位）。

**一项新的 BLOCKING finding（F1，R1 新引入）**：CH-1.1 冻结的 `WeakMap<Fiber, OwnedRecord>` 单值映射无法表达"同一 owner fiber 持有多条 owned record"的合同合法输入——第二次 `set` 覆盖第一条，teardown 发射只 close 最后一条，被覆盖 record 的 dispose-start 通知丢失并退化为 owner effect 兜底（即 R0-B1 等待环对该 record 复活）；CH-1.2 步骤 6 的 tombstone"删除 WeakMap 条目"还会连带删除同 fiber 兄弟 record 的映射。修复是局部的（多值索引或显式单 record 合同+错误码+测试行），不改变 B1-A 方向，但必须在实现授权前修正。这是唯一阻塞项。

另有 1 项 P2（SOURCE 事实错误 S-C8 括注）与 2 项 P3。**不构成架构否决**：B1-A/B2/B3 的方向、D1–D3 保留面、补丁地图、测试合同框架均成立；修 F1/F2 后无需重开方向讨论。

## 2. 取证方法与基线

- 版本矩阵：13 个包 manifest（version + repository.directory）+ host，全部与 R1 §2.1 逐项一致（11 包 0.2.1-rc.2；cordis 4.0.5；cordis-plugin-loader 1.0.6；host `@deepseek-ai/dsh` 0.2.1-rc.2）。
- 防漂移：`cordis/lib/index.js` SHA256 `6a9394c0877ff45218818c6e815edd038f8057e1a1deb390a8d43ec81c57691e` ——与 R0 §2 记录一致，R0 取证后无漂移。
- 结构：N 下确无 `dsh-subagent-in-process-driver`、无 `dsh-webhook`；有 `dsh-subagent`/`dsh-subagent-spawn-in-process`/`dsh-subagent-fork-in-process`（R1 §2.2 属实）。
- 消费者独立 census：对 N 下 `lib/index.js` 全量 grep `agentPresets`，再对表外命中文件过滤变更面 API（`.mount(`/`.composeFrom(`/`.select(`/`acquireScope`）。结果：变更面消费者仅 controller 与 subagent（均在 R1 §6.1 表内）；`dsh-agent-preset` 仅 `register(this.config)`（D3 legacy register 合同覆盖）；api-remotes/host-plugin-inventory/plugin-package-inventory/tool-subagent 仅类型/清单/只读引用。R1 §6.1 consumer 表在本 census 面内完备。
- 所有结论基于直接读取的源码行；不采信 Architect 自检，也不因自检 PASS 跳过验证。

## 3. R0 三 finding 逐条闭环裁定

### R0-B1（LOADING owner dispose 起点）——**PASS（机制层闭环）；同一机制内有新引入缺陷 F1（见 §4）**

逐项核验（全部直接读取）：

| R1 声称 | 核验结果 |
|---|---|
| S-C4 Fiber.dispose 闭包 `index.js:1075-1091`：uid=null(:1078) → emitPluginDisposed(:1079，同步先于任何 await) → fibers 移除(:1080-1083) → INACTIVE(:1084) → inertia=_unload()(:1085-1088) → while await(:1089) | **属实**（逐行比对一致；async 闭包体在首个 await 前同步执行） |
| S-C2 emitPluginDisposed `:968-984`：dispatch 同步求值回调表、per-callback try/catch、返回 Promise 的 rejection 被消费 | **属实** |
| S-C3 dispatch `:258-264`：teardown 发射 args=["internal/plugin", fiber]，args[0] 为字符串 → thisArg=null → filter=undefined → `!filter` 短路 → 该事件名全部存活 hook 收到，无 scope 过滤；`internal/` 前缀不重发 internal/dispatch(:261) | **属实** |
| S-C6 `ctx.on` 监听者随注册 fiber 卸载自动移除（:335-345 register 用 `this.ctx.fiber.effect`；:371-380 assertActive） | **属实（机制已穿透核验）**：EventsService tracker `property:"ctx", noShadow:true`（:233-236）+ ReflectService mixin accessor `value.bind(mixin ?? service)`（:879-901）+ getTraceable（:84-89/:123-）使 `this.ctx` 解析为**访问者 context**——监听者 effect 归注册者 fiber，`_hooks` 表挂 root 单例 |
| S-C7 每 root 单一 hook 表（:1687 root 构造器 `new EventsService(self)`；extend 原型继承 :1704-1710） | **属实** |
| S-C5 `_unload` :1372-1392 运行 `_disposables.clear()` 全部 effect | **属实**（effects 只在 inertia 落定后运行的源码依据成立） |
| S-C9 root fiber :1102-1113（uid=0、dispose=()=>restart()、无 teardown 发射） | **属实**；CH-1.4 root-owner→registry-disposed 映射是诚实成文的合同而非虚构发射 |
| CH-1.2 无 race 插入序列 | **论证成立**：步骤全同步无 await；:1078/:1079 为相邻同步语句，若步骤 5 观测 uid===null 则发射必已同步完成（WeakMap 扑空路径被覆盖）；发射在步骤 4 后则监听命中——无窗口。同 root 判定 `ownerCtx.events === this.ctx.events` 用单例对象身份，隔离 scope 不产生第二 events 实例（构造器安装、非 provide/isolate 服务） |
| CH-1.3 owner effect 降级幂等兜底 | **满足 R0 最小解除原文**（"不能独担 early notification"）；effect 注册失败不留 record/scope 保留 |
| CH-1.5 LOADING-owner-await-ready 反例保持 + 明文禁止 timeout/最终清理抵销 | **在位**（§3.3-CH1.5 可观测顺序合同 + §8 T01+ 硬验收 + §1 验收标准⑤） |
| registry fiber 卸载时自身监听尚未移除（发射先于 _unload） | **成立**（:1079 先于 :1085-1088；hook 移除是 registry fiber 的 effect 清理，在 _unload 中） |

R0-B1 最小解除条件（公开触发机制、监听者所有权、精确 Fiber 身份过滤、订阅前后 active/uid 校验、清理顺序、effect 兜底不独担）全部满足。**B1 判 PASS**；F1 是 R1 新机制冻结文本自身的索引基数缺陷，属新 finding，不改变"R0-B1 已被机制层解决"的裁定。

### R0-B2（child selector 必须选正确 generation）——**PASS**

- 当前语义锚点全部属实：S-U1（child-agent.d.ts:66-74 注释原文"Independently mounted preset; omission shares the parent's standing generation"）、S-U2（:373-383 独立→`presets.mount`；省略→`composeFrom` 同步继承）、S-U3（:398-409 "Call synchronously before the child start's first await"）、S-U4（:1796-1808 独立在 :1799 create 追加前、继承在 :1806 追加后；:1809/:1815 resume/create 带 `parentAgent: parent`）、S-U5（:2164-2166 cold 独立恢复、无 projection 抛 NOT_RESUMABLE）、S-U6（:2258-2265 selected 先于 descriptor 即独立）、S-U7/S-U8（spawn agentPreset:true/inheritsParentContext=false；fork agentPreset:false/true，仅 capabilities/seed）。
- CH-2.1 三分支（显式独立/cold 独立→`acquireAdmission({id})` 精确 reservation 冻结不按 id 重解析；省略→父实际 standing generation，与 S-U3 同一时点纪律）与上述语义一一对应，分支矩阵完备（cold 非独立→agentPreset=void 0→落继承分支，与 :2165 一致）。
- CH-2.2/CH-2.3 拒收规则两条独立成文：继承分支按父 owned generation、独立分支按该 id 自身 record（非互相放宽）；同 id 换代不跨越（承接 S-R4）。CH-2.4 helper 公开返回类型（现 `void | Promise<void>`，d.ts:90 已核）与 setup hook 传递更新在位。
- provider 能力检查置于 admission 获取**之前**（避免先取 token 再拒绝泄漏）；不向 spawn/fork 加 factory（R0 §3-B2 明令承接）；顺序保真（:1797→:1799→:1806 顺序原样）。补丁地图改共享 `packages/subagent/subagent`；webhook 声明当前匹配源码未取得、不声称覆盖（诚实）。
- T06+ 含 R0 要求的全部反例（A父/B子、B closed A open、A closed 继承拒收 vs 独立 B 允许、继承 fork、cold resume projection 有/无、storage gap）。

### R0-B3（Web claim token 单次生命周期）——**PASS**

- 代码锚点全部属实：S-T1（composeAgent :351-364 只 resolve+setup，无 token）、S-T2（inOrder :405-414 per-session 串行）、S-T3（claim :416-465：:422 compose→:423 `reuseLive ?? createMinted`；:430 not-found createAgent；:443 reusable 判定；:451 compose；:452 !reusable→createMinted；:455-459 resume+reuseSetup；:461 StartedSinceObserved→**同一 composition** createMinted；:463 无 live→createMinted / 有 live→**递归 claim**）、S-T4（reuseLive :467-481：:473 同 preset 直返 live 零 factory；:475 `presets.select(live,target)`；locked→undefined 落 createMinted、其它重抛）、S-T5（reuseSetup :483-491：:485 blank 复查先于 :486 setup、:488 selected append、返回 commit）、S-T6（fork :849-910：:880 仅 id 解析、:883-898 factory、:902-908 create 成功后 attach 失败）、S-T7（createAgent :508-526）、resumeObserved（:392-404 单 attempt）。
- registry 侧：S-R7 属实（:751 串行链、:752-756 blank 校验、**:757 按 id 重解析**、:759 recompose、**:760 append 在 rebind 后**——半绑定窗口存在）；S-S1 属实（session `commit` :1579-1598 validateNext/observers 可抛）。
- 合同完备性核验：§5.2 operation/factory-attempt 双生命周期 + token 状态机（UNACQUIRED→HELD→ATTACHED→RELEASED|COMMITTED）+ 逐出口不变量（引入 P=0/新增 listener=0/无未释放读 lease）；§5.3 九分支与上述代码分支一一对应、无遗漏出口（:421 CwdConflict/:419 Ownership 在任何 acquire 之前抛出，天然零残留）；§5.4 `selectWithAdmission` 删除 :757 式重解析、持有旧 binding 至 append 成功、append/observer 抛错**先恢复旧 binding 后重抛**、collect 仅在成功路径（禁止先 collect 后回滚）；§5.5 reuseSetup 完整 commit 透传、selected append 不进 publicationCommit。CH-3.4 失败分类（HELD 可同 operation 复用但须同精确 generation/ATTACHED 不可复用/换代只在新 operation 且可观测）承接 R0"不得默默换代"原文。
- T05+/T07+/T09+/T11+ 覆盖 R0 要求的全部反例（live 同选+closed→P=0、真实改选全链、G1→G2 事务拒绝、blankness 复检、SessionAlreadyOwned 两回退、setup 前/attach 后失败、递归=新 operation、legacy 回归不降）。

## 4. Findings（P0-P3）

### F1 [BLOCKING/P1]（新引入）CH-1.1/CH-1.2 的 `WeakMap<Fiber, OwnedRecord>` 单值映射不能表达同 owner 多 record——dispose-start 通知丢失 + tombstone 误删兄弟映射

**证据**：
- R1 §3.3 CH-1.1 代码与注释冻结 `ownedByFiber` 为 `WeakMap<Fiber, OwnedRecord>`（单值）；listener 中 `const record = this.ownedByFiber.get(fiber); if (record !== undefined) record.close('owner-disposed')`。
- R1 §3.3 CH-1.2 步骤 4"分配 record 并 `ownedByFiber.set(ownerFiber, record)`"；步骤 6"tombstone 回收时删除 WeakMap 条目"。
- 原设计合同（R0 输入，hash 已核未变）`beginRegistration(definition, {owner, signal})`（:70-71）**没有**"同一 owner 同时至多一条 owned record"的限制：DUPLICATE_ID 按 id 判（:91/§3.3-CH1.2 步骤 1）；同 id closed 后允许 new begin（:192）；不同 id 同 owner 是合同合法输入。当前生态形态（`dsh-agent-preset` 每插件实例一次 register）是单 fiber 单 record 的常态，但非合同约束。

**失败链**：owner fiber 对 id A、id B 各调一次 begin → 第二次 `set(fiber, recordB)` 覆盖 `recordA` 映射 → teardown 发射时 listener 只 close recordB → recordA 的 dispose-start 通知丢失，只能等 owner effect 兜底（S-C4/S-C5：effect 在 inertia 落定后运行）→ 若 owner LOADING 且有 waiter await recordA 的 `lease.ready`，**R0-B1 等待环对 recordA 精确复活**。并且 recordA tombstone 回收执行"删除 WeakMap 条目"时会连带删除 recordB 的映射（同 key）。CH-1.5/T01+ 硬验收若以"同 owner 双 record + await 双 ready"实现，字面 CH-1.1 无法通过自身反例合同。

**最小解除**（二选一，均不改变 B1-A 方向）：
- (a)（推荐）索引改多值：`WeakMap<Fiber, Set<OwnedRecord>>` 或 registry 侧 owner→records 反向索引（与 id 主表联动）；listener 对集合内全部 record 依序 close（每 record first-reason-wins）；CH-1.2 步骤 6 改为按 record 精确移除集合成员；T01+ 增行：同 owner 双 record（ids A/B）、owner LOADING await 双 lease.ready → owner dispose 后**两条** record 的 closed/readers 终态均先于 barrier 释放。
- (b) 显式合同限制：begin 前置校验"owner fiber 已持有活跃 owned record 则抛"（新错误码，如 OWNER_ALREADY_OWNS），合同与错误表成文；T01+ 增对应拒收行。
- 附带：§9 性能行按 (a) 更新为"每 teardown 发射 O(该 fiber owned records)"。

### F2 [P2] S-C8 事实错误：:1093 创建发射**不经** scope 过滤（thisArg=null），非"带 thisArg（经 scope 过滤）"

**证据**：R1 §2.3 S-C8 行称创建发射"带 thisArg（经 scope 过滤）"。实际 `cordis/lib/index.js:1093` `this.context.emit("internal/plugin", this)`：`emit(...args)` 的 args=["internal/plugin", fiber]，dispatch（:259）仅在 args[0] 为 object/function 时取 thisArg——此处 args[0] 是事件名字符串 → **thisArg=null、filter=undefined、无 scope 过滤**（与 teardown 发射同路径）。`this` 是载荷参数（fiber），不是 thisArg。

**影响**：不削弱 B1-A 机制——uid 判别式（teardown 时 :1078 已清、创建时非 null）依然成立且充分，CH-1.1 的 `if (fiber.uid !== null) return;` 正确过滤创建发射。但 (i) SOURCE 表内事实必须更正（一行修正：创建发射同样 thisArg=null 无 scope 过滤，判别只靠 uid）；(ii) §9 性能行"每 teardown 发射"低估了监听者实际收到的发射次数（同 root 每次 plugin fiber 创建都会进入监听者并经 uid 早退，O(1)/次，可接受但应成文）。可在 F1 修订时一并更正。

### F3 [P3] §5.5 措辞：":488 的 selected append 保持 setup 内 append"表述不精确

实际 :488 append 位于 `reuseSetup` 包装器内、`composition.setup`（:486）返回**之后**（setup 阶段内、old commit 之前）。实质正确（保持 pre-publication append、由 appendUnstoredSuffix 持久化、不进 publicationCommit），仅措辞易误读为"composition.setup 函数内部"。建议随 F1/F2 一并澄清。

### F4 [P3] T01+ 可补 root-owner 场景行

CH-1.4 的 root-owner→`registry-disposed` 映射是合同性声明（S-C9 已核 root 无 teardown 发射）；T01+ 现有行覆盖 registry fiber 卸载，但未显式覆盖"root owner 终态理由呈现"的观测行。建议增补（非阻塞）。

## 5. 0.2.1-rc.2 锚点抽检清单（本实例直接读取结果）

| 锚点 | 核验 |
|---|---|
| §2.1 manifest 版本同代（13 包+host） | PASS（逐项一致） |
| §2.2 driver/webhook 不在安装、subagent 三包在 | PASS |
| S-C1 events.d.ts:216-218 `internal/plugin` 注释 | PASS |
| S-C2 emitPluginDisposed :968-984 | PASS |
| S-C3 dispatch :258-264 thisArg=null/无过滤/internal 不重发 | PASS |
| S-C4 Fiber.dispose :1075-1091 时序 | PASS |
| S-C5 _unload :1372-1392 | PASS |
| S-C6 on/register 监听者归注册 fiber（tracker/mixin 机制穿透核验） | PASS |
| S-C7 :1687 每 root 单一 hook 表 | PASS |
| S-C8 :1093 创建发射 | **PARTIAL**：uid 非 null 属实；"带 thisArg（经 scope 过滤）"错误（→F2） |
| S-C9 root fiber :1102-1113 | PASS |
| S-C10 registry.d.ts:83-92 Runtime.fibers 公开 | PASS |
| S-R1 register :470-494 晚 disposer | PASS |
| S-R2 activate :495-521（:505 await mountPreset barrier） | PASS |
| S-R3 diagnostic :533-543 | PASS |
| S-R4 retain :632-652（:641 await 后按 id continue） | PASS |
| S-R5 bind/join :654-680 | PASS |
| S-R6 mount/composeFrom/acquireScope :686-795 | PASS |
| S-R7 select :750-770（:757 重解析、:760 append 后置） | PASS |
| S-T1 composeAgent :351-364 | PASS |
| S-T2 inOrder :405-414 | PASS |
| S-T3 claim :416-465（含 :461/:463a/:463b） | PASS |
| S-T4 reuseLive :467-481（:473/:475/:477） | PASS |
| S-T5 reuseSetup :483-491（:485→:486→:488） | PASS |
| S-T6 fork :849-910（:880/:883-898/:902-908） | PASS |
| S-T7 createAgent :508-526 | PASS |
| S-U1 ChildComposition :66-74（+ :90 返回类型） | PASS |
| S-U2 applyChildComposition :373-383 | PASS |
| S-U3 captureDelegatedPolicyOverrides :398-409 | PASS |
| S-U4 materializeTracked :1764-1824（:1797/:1799/:1806 顺序） | PASS |
| S-U5 cold resume :2164-2183 | PASS |
| S-U6 hasIndependentPresetSelection :2258-2265 | PASS |
| S-U7 spawn :19-34 | PASS |
| S-U8 fork :33-48 | PASS |
| S-L1 publish :1786-1804（:1789-:1790 fence 位；agents.enter :512 同步、sessions.enter :1853 同步） | PASS |
| S-L2 setupAndPublish :1915-1941（:1931/:1932/:1933，publish 无 finalizer） | PASS |
| S-L3 initializeAgent :1942-1956 | PASS |
| S-A1 AgentSetupCommit 仅同步 commit / meta.agentPreset :70 | PASS |
| S-S1 enter :1853-1883 / commit :1579-1598 可抛 | PASS |
| S-S2 quiesceFiber :282-305 | PASS |
| S-P1 handle.d.ts :52-106 append-only/close | PASS |
| cordis hash vs R0 | PASS（无漂移） |
| consumer census（agentPresets 变更面） | PASS（表完备） |

抽检覆盖任务要求的全部分组：manifest 同代、Fiber.dispose 时序、registry select :757/:760、controller claim/reuseLive/fork、subagent materializeTracked/cold/hasIndependentPresetSelection、AgentLoop publish/setupAndPublish、persistence append-only。

## 6. 其余审查维度

### D1–D3 保留面（任务维度 3）——PASS

- 原设计 hash 未变；R1 §6.1 D1 fence 位置（:1789 assertLive 后、:1790 sessions.enter 前、最后持久化 await :1932 之后、首个 enter 前）与 thenable 拒绝消费、§6.1 持久化 gap 处置（may-exist/close-only/不 delete/truncate/原 cause 不被吞）、§6.2 D2 P/C/R 分支与公开 fence NOT_RUN、§6.3 D3 终态/兼容表+覆盖扩展（cold 独立子与 live 复用/改选纳入——正是 R0 §4 D3 行要求的补充）全部按声明保留并重锚到已核实的 0.2.1 行号。
- 无新依赖引入：§7 写面与 R0 §5 预批地图同模块集（subagent 条目正确替换消失的 driver）；vendor/cordis、vendor/loader、packages/core/scope、Session/Persistence 核心仍排除；§3.5 cordis_core_change_required=false 有源码级支撑（B1-A 全部用公开面）且证伪出口 (a)(b)(c) 成文、修改面明示不在预批写面——诚实。

### 标签纪律（维度 4）——PASS（一处 SOURCE 事实错误见 F2）

SOURCE（S-*，路径+行号）/PROPOSED（CH-*、代码块）/NOT_RUN（§8 全部、§3.4 fence、§6.2）三类分离维持；无把 PROPOSED 写成 SOURCE 或反之。webhook_coverage=NOT_OBTAINED 未冒充覆盖（§2.2/§6.1/§7/§11 四处一致）。运行/存储 NOT_RUN 声明在位。

### 测试合同（维度 5）——PASS（附 F1 增行要求）

T01+/T05+/T06+/T07+/T09+/T11+ 全部在位、可观测验收（事件屏障断序非 sleep）、反例合同在位、不降门/不延时/不先 release 的承接声明在位（§8 末段）。T01+ 需按 F1 增行。

### 设计自检交接（维度 6）——PASS

§11 交接块：`design_revision=R1`、`implementation_authorized=false`、`runtime=NOT_RUN`、`storage_regression=NOT_RUN`、`independent_review=PENDING`、`timeout_or_eventual_cleanup_offset=FORBIDDEN_AND_NOT_USED` 均在位且与本审查观测一致。

## 7. 硬门槛裁决

| 门槛 | 结果 |
|---|---|
| 候选方案 ≥2 | PASS（B1 三候选 §3.2 含排除理由；B2 统一父 selector 排除 §4.1；B3 compose 期 acquire/无条件重取排除 §5.3-#1/#6/CH-3.4；另保留原设计 §2 三候选） |
| ADR 关键字段完整 | PASS（§10 标题/日期/背景/决策/备选/排除/影响/后果/可逆/后续；Architect 不自批） |
| 蓝军挑战 ≥3 | PASS（BR1'–BR5，每条有缓解与残余） |
| 模块无循环依赖 | PASS（§7 静态 DAG 与 R0 已核结论一致；新增 selectWithAdmission 在 registry 模块内、不引入新边） |
| 接口契约/所有权安全 | **FAIL**——F1（B1 机制冻结文本的索引结构无法表达合同合法输入） |
| 独立 Bar Raiser | 本报告（已执行；结论 NEEDS_CHANGE） |

## 8. 真实环境只读命令审计（Coordinator 机录 EVD 用；严格只读，全部 exit 0，影响路径=仅读取）

| # | UTC | 命令/工具 | 目标路径 | 结果 |
|---|---|---|---|---|
| R1-V01 | 2026-10-20T09:31:14Z | bash `date -u; ls .../@deepseek-ai/; ls .../dsh/node_modules/@deepseek-ai/` | C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai[.../dsh/node_modules/@deepseek-ai] | 目录清单（driver/webhook 缺席证实） |
| R1-V02 | 2026-10-20T09:31:39Z | bash 循环 grep 13 包 package.json version/directory + host | 同上各 package.json | 版本矩阵（§2.1 一致） |
| R1-V03 | 2026-10-20T09:35:53Z | bash grep ReflectService/handler/bind/tracker | cordis/lib/index.js | 定位 :672/:879/:918 等 |
| R1-V04 | 2026-10-20T09:41:55Z | bash sha256sum + census grep `agentPresets` | cordis/lib/index.js；N 下全部 lib/index.js | hash 同 R0；11 文件命中 |
| R1-V05 | 2026-10-20T09:42:05Z | bash 变更面 API 过滤 grep | dsh-agent-preset/api-remotes/host-plugin-inventory/plugin-package-inventory-deepseek/tool-subagent | 仅 dsh-agent-preset register |
| R1-V06 | 2026-10-20T09:45:06Z | bash grep `enter(agent` + sed -n 15,30p | dsh-agent/lib/index.js；dsh-agent-preset/lib/index.js | :512 定位；register 形态 |
| Read×31 | 09:31Z–09:45Z 间 | ZCode Read（按行窗口） | cordis/lib/index.js×8、types/events.d.ts、types/registry.d.ts；dsh-agent-preset-registry/lib/index.js×3；dsh-api-session-controller/lib/index.js×2；dsh-subagent/lib/index.js×4、types/child-agent.d.ts；spawn/fork-in-process 各 1；dsh-agent-loop/lib/index.js×2；dsh-agent/lib/types/index.d.ts、lib/index.js×1；dsh-session/lib/index.js×2；dsh-scope/lib/index.js×1；dsh-session-persistence/lib/types/handle.d.ts×1 | §5 清单全部锚点 |

仓库内（非用户环境）命令：docs/architecture 与 docs/reviews ls（约 09:27Z，无 date 前缀）；09:42:17Z grep+sha256sum 三文档；09:43:47Z grep 原设计 owner/begin 合同行。SDK 零写入、零运行、零 probe；`.governance/` 零写入。

## 9. 下一步

1. Architect 按最小解除修 F1（二选一）+ 更正 F2（S-C8 行与 §9 性能行）+ 顺手 F3/F4，产出 R2（或以等价修订版交付）；D1–D3/B2/B3/CH-1.2 race 序列/CH-1.5 反例合同**无需重开**。
2. R2 复审（round=2）逐条对照 F1–F4 标注已修复/未修复/新引入；round 依 fuse 规则管理。
3. 实现授权仍为 false；runtime/storage 保持 NOT_RUN；FEAT-102 R5 actual 义务不受本报告影响。
