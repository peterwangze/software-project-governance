# FEAT-103：DSH 调用方拥有的登记取消与最终发布校验（D1～D3 设计）

- 日期：2026-10-19（Asia/Shanghai）。角色：Architect；规范：architect / stage-architecture。
- 授权依据：用户选择“扩展，先做隔离补丁验证”，Coordinator 已机录 DEC-363。本检查点仅写设计；补丁/新运行须独立设计审查后另行派发。
- 状态：PROPOSED / DESIGN_REVIEW_PENDING；implementation、runtime、storage 回归全部 NOT_RUN。本文不关闭 FEAT-102 的 R3-B1。
- 基线：本机当前 DSH 0.2.0-rc.2 同代 SDK；不混装 next，不下载、安装、执行新包，不改用户已安装 DSH、HOME/profile，不外发消息/PR。SDK 只读。
- 历史：FEAT-102 架构 §15、R0～R4、三次原型/raw 保持 immutable。G 的正常有限启动通过及 permit 后取消 FAIL 均保留；不提高原 barrier 观察门、不以最终 drain 代替取消终态。
- 范围：registry 的 record 所有权/终态、精确 generation admission、实际 consumer、AgentLoop 最后 await 后发布点；不改工具列表、host rows/global services、业务策略或暂停 FIX-444/445。
- 来源标记：SOURCE=本次直接源码/类型读取；PROPOSED=以下新接口/算法；NOT_RUN=尚无实现/运行证据。源根 N=`C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai`。

## 1. 成功合同与精确源码基线

用户价值是治理插件升级/卸载时不会遗留阻塞消费者的登记，并保全已有会话；“返回不支持”本身不是适配完成。设计须先满足：
1. permit 后 payload activation 仍 pending，owner dispose/close、新旧 resolve/list/admission 必须先终结；后释放 payload 只验证真实 drain。
2. 尚未提交的 Agent 不得在关闭 generation 后可见；已提交 Agent 继续使用其精确 revision，新 child 是新 admission。
3. 最后存储 await 后再做不可跳过的 generation fence；拒收不删除/改写已存档数据。
4. 旧 register 默认 API/坏注册/duplicate/default/retired 行为不暗改；新协议显式 opt-in。

SOURCE 基线：DSH、registry、agent-loop、agent、scope、subagent、in-process-driver、API-session-controller、webhook、session-persistence 均 0.2.0-rc.2；Cordis 4.0.5，Loader 1.0.6。registry JS SHA256 `ED62D573B8CC6D7ED3E3CB7932DBF5E237F5A603B3CC9D9E586187DB00E821CC`，AgentLoop JS `00C4814D63F3D1E2754EB09144832D19B30499D6EA444730473F740B587948C2`。

| SOURCE 锚点（N 下） | 当前事实/设计约束 |
|---|---|
| registry/lib/index.js:500～543、557～587 | register 先插 record、await activation 后才返 disposer；scope 属 registry owner；diagnostic/list 等 ready。缺少 early handle，不是调用方漏 cleanup。 |
| registry:639～717 | retain 在 await 后可能按 id 重试；bind/join 用 scope key 保存精确 generation；composeFrom 可直接继承父 revision，返回字符串，无 publication token。 |
| agent/lib/types/index.d.ts:24～39、84～103 | 公开 AgentSetupCommit.commit 同步；setup 在未发布 Agent 中执行，已有 rollback 合同。 |
| agent-loop:1873～1892 | setup 返回的 commit 在1889，appendUnstoredSuffix 在1890仍 await，随后才 publish；不能把旧 commit 当最终原子点。 |
| agent-loop:1731～1763 | prepare.publish 内1747 assertLive，1748 sessions.enter，1749 agents.enter，1750 announce，1752才首次 await；最终 fence 必须在该函数内部的 enter 前。 |
| session:1734～1764；agent:enter（约499～533） | 两个 enter 同步写 map、返回 exact detach；进入前不发创建事件。第一个 enter 已使 Session 可查，因此不能把 fence 放在第二个 enter 或 announce 后。 |
| agent-loop:1839～1843、1860、1944～1973 | suffix append 是持久化 await；resume 还先读/补 interrupted closers/append。prepare/initialize 出错已有 handle.close 与 prepared.dispose 路径。 |
| session-persistence handle/types | append 为 append-only；close 完成未决 durability 并释放写 ownership，可能使已接受前缀物化。没有安全通用 rollback/delete API，不能承诺失败无磁盘残留。 |
| scope:282～305；Cordis:1077～1089、1131～1133 | scope.dispose 等 inertia；Fiber.dispose 开始时清自身 uid，assertActive 只检查自身 uid。仅关父 scope 不能当后代已同步 fence 的证明。 |
| Cordis registry.d.ts | RegistryService.values、Runtime.fibers、Fiber.parent/uid/dispose/inertia 均公开；可提出只处置自有 scope 后代的 SDK 内部 helper，无需先修改核心私有字段。 |

## 2. 候选比较及推荐

先按存档安全→无等待环→精确 publication→旧 API兼容→修改量排序。

| 方案 | 机制/成本 | 裁定 |
|---|---|---|
| A（推荐）显式 owned lease＋admission token＋第二阶段同步 publicationCommit | registry 管理取消终态；consumer 传精确 generation；保留原 commit，新增最终只检查/转移引用的同步 hook；只改直接调用链 | 可冻结具体 API/反例；仍须证明 scope fence，不能仅靠类型宣称通过。 |
| B 把原 setup.commit 一律移到 append 后 | 少一个 hook，但旧 commit 可追加 setup 记录/提交 provisioning，移动会令这些记录绕过原 suffix 持久化；改变旧调用方时序 | 排除。原 commit 不能调用两次，也不能未经兼容审查移动。 |
| C 仅 AbortSignal/Promise.race 或从 map 删 record | 代码少；不能唤醒已经捕获 ready 的读者，也无最后 await 后 generation 校验；删除未来查找不取消旧 waiter | 排除；已知反例不以新名字重跑。 |

## 3. 最小 opt-in 公共接口（PROPOSED）

以下在当前 SDK 不存在，不通过方法 arity/版本字符串猜支持。新接口仅同进程可信 Context 调用，不新增远程 registration RPC/网络端点。

```ts
type CloseReason = 'explicit' | 'signal-aborted' | 'owner-disposed' | 'registry-disposed';
type RegistrationOutcome =
  | { state: 'ready'; id: string; generation: object }
  | { state: 'failed'; code: 'agent-preset/activation-failed'; message: string }
  | { state: 'closed'; reason: CloseReason };
type DrainOutcome = { state: 'drained' } | { state: 'drain-failed'; errors: readonly string[] };

interface OwnedPresetRegistration {
  readonly id: string;
  readonly generation: object; // stable opaque identity allocated before activation
  readonly ready: Promise<RegistrationOutcome>;
  readonly closed: Promise<{ reason: CloseReason; previous: 'activating' | 'ready' | 'failed' }>;
  readonly drained: Promise<DrainOutcome>;
  close(reason?: CloseReason): void;
}
interface PresetAdmission extends Disposable {
  readonly id: string;
  readonly generation: object;
  readonly signal: AbortSignal; // abort on close only until publicationCommit
  attach(agentCtx: Context, agent: Agent): AgentSetupCommit;
}
beginRegistration(definition: PresetDefinition,
  options: { owner: Context; signal?: AbortSignal }): OwnedPresetRegistration;
acquireAdmission(owner: Context,
  selection: { id?: string } | { parent: Context },
  signal?: AbortSignal): Promise<PresetAdmission | undefined>;

// Existing commit remains required, with its current once-before-storage semantics.
interface AgentSetupCommit {
  commit(): void;
  publicationCommit?(): void; // new: sync, no append/events/await; final fence + reference promotion
}
readonly capabilities: {
  ownedRegistration: 'terminal-cancel-v1';
  publicationFence: 'final-enter-v1';
};
```

`undefined` from acquireAdmission is allowed only for a parent selector whose actual parent has no preset; id/default selectors return a lease or throw. It snapshots default once. Owner/root/active checks occur before and after awaits. An acquired lease retains the exact record/generation; it never loops to a new record with the same id. Its owner effect releases only an unconsumed reservation; explicit Symbol.dispose is idempotent. attach is single-use, same-root, active, unpublished-Agent only; it transfers the provisional reference into that Agent scope, whose effect releases it on rollback/dispose. Caller finally-dispose after transfer cannot remove a live Agent's reference.

acquireAdmission awaits registry-managed selectable/closed state, not the physical activation Promise after close. Close settles these SDK-owned waiters and consumes late activation rejection; this is real registry termination, not caller-side race masking it. attach returns commit=no-op and publicationCommit bound to the exact generation. Consumers with existing commits compose them once; the new hook cannot append Session events, schedule async work, emit observers or re-resolve by id. begin accepts an owner currently LOADING/ACTIVE (the root ACTIVE is allowed), with non-null uid and the same registry root; PENDING/UNLOADING/DISPOSED owners fail before insertion. Install the owner cleanup before allocating the record; an effect-registration failure leaves no record/scope.

Closed/failed admission throws existing `agent-preset/invalid` with a stable `reasonCode` (REGISTRATION_CLOSED / ACTIVATION_FAILED); absent id uses existing not-found. Invalid begin options throw a proposed same-process PresetRegistrationError with EMPTY_ID / DUPLICATE_ID / OWNER_INACTIVE / OWNER_ROOT_MISMATCH before any record/scope allocation. Routine activation/close never reject ready/closed/drained; unexpected internal failures become failed/drain-failed diagnostics and are consumed. The old register continues its old Promise/disposer/error contract (see D3).

## 4. D1：精确 generation 到最终可见发布点

### 4.1 冻结 token 的边界与实际 consumer

| 实际 SOURCE 路径 | PROPOSED 改动（不能只更新其中一条） |
|---|---|
| API session-controller composeAgent:358～369 → createOrAdopt:449～458 → agents.create | composeAgent 先 acquireAdmission(this.ctx,{id:presetId})，返回 id/setup/admission signal/disposer；setup attach 返回 commit object；create 在 finally 释放未转移 lease，signal 与既有 request signal 合并。此前 mkdir 不能作取消等待保证。 |
| resumeObserved:399～410；createOrAdopt 的 persisted分支:424～434 → agents.resume | 同一个 composition token/combined signal 贯穿 open/read/setup/最终 publish；异常始终 release，不能等 setup 才重新 resolve id。 |
| Web fork:807～825 → agents.create(seed/meta/inheritedEventCount) | 在既有 fork seed/workspace校验后 acquire，固定当前选择的精确 generation；保留源历史/child id/lineage；workspace已创建则不因取消删除目录或原档。 |
| subagent materializeTracked:1065～1091 → create/resume | 在工厂调用前以 {parent:parent.ctx} 取得父实际 generation，合入 inputs.signal；setup 保持 descriptor/委派策略追加顺序，applyChildComposition 改为消费该 token并返回 publicationCommit，不再调用裸 composeFrom 换取字符串。 |
| subagent-in-process-driver startInProcessRun（约157～196） → parent.ctx.agents.create | 委派权限仍在第一处新 await 前同步 capture；随后 acquire 父 generation，setup attach、原persona/restrict/structured/descriptor操作保持，并返回合成 commit。 |
| webhook createWebhookSession（约146～178） → agents.create | resolve/acquireScope+mount(id)改成一个精确 admission；跨 workspace await 持有它，setup attach 后保留 model selection，finally释放。HTTP/权限/上传业务不重构。 |
| AgentLoop configured create:1781～1800 | 当前不消费 preset，无 token，保留原行为；仍通过统一 prepared.publish，不能另造跳过 fence 的 owned-preset通道。 |
| 外部直接 old mount/composeFrom | legacy definitions 保持旧API。owned definition 须使用 prepared admission；旧方法对 owned 新接入明确 protocol-required，不能静默给无 fence 绑定。known SDK consumers以上全部迁移；新 API不支持的第三方 caller 不冒充兼容。 |

公开 registry 的 select/recompose/acquireScope 也不能绕过 owned closed fence。既有 issued read lease保留；新 read lease关闭后拒收。select 对 owned READY目标保持 blank-session锁/串行链，以精确 reservation 在同步切换点校验后 rebind+append selected；old scope collection不置于两者之间 await。已发布 blank Agent的这个即时提交不走 attach(unpublished)；SDK内部单独事务分支。失败不能留半个binding或追加选择事件。legacy select/recompose与default/selected字段语义不改。

### 4.2 AgentLoop 的准确补丁点

SOURCE 目前：
```text
setup await → old commit() → await appendUnstoredSuffix
→ prepared.publish: assertLive → sessions.enter → agents.enter → announce → await agents.announce
```

PROPOSED：
```ts
const setupCommit = await raceAbort(setup?.(ctx, agent), prepared.signal, id);
setupCommit?.commit(); // unchanged, exactly once; existing setup appends are then persisted
await appendUnstoredSuffix(stored, session);
return prepared.publish(source, setupCommit?.publicationCommit);

// INSIDE prepare().publish(), directly after assertLive(), before either enter:
publicationCommit?.(); // no await; validates exact generation and promotes provisional binding
detachSession = sessions.enter(session);
detachAgent = agents.enter(agent, parentAgent);
```

Do not call the finalizer in setupAndPublish then await/return across another Promise before enter. publish is async but its body runs synchronously through both enter calls until announce's first await. Validate thenable returns as an invalid synchronous hook before enter. Do not invoke commit twice or move it past storage.

publicationCommit checks token still attached to this exact Agent/root, record-generation identity/open admission, and pending-binding state. It atomically changes provisional→committed and detaches the registration-close→admission abort subscription. There is no await or observer dispatch between that promotion and the two enter calls; both current enter implementations are synchronous/no creation events. Close before this turn rejects; close reentrantly during later announce is after commit and follows D2, retaining the existing revision. Other caller/factory cancellation retains its existing rollback semantics.

If an enter throws, initializeAgent still prepared.dispose and the Agent-scope effect releases the promoted ref exactly once; this does not invent an Agent that committed successfully. Do not treat session/created compensation as prepublication rejection. Already delivered observer notifications cannot be undone; existing announce-failure behavior remains explicit.

### 4.3 持久化 gap 拒收后的安全处置

At final fence failure after append, reject creation with invalid/REGISTRATION_CLOSED and structured context `{sessionId,published:false,persistence:'may-exist'}`; do not claim create never stored. initializeAgent→prepared.dispose closes the exact write handle and in-memory scope; SessionPreparation Symbol.dispose releases preparation once. Any successfully accepted header/seed/suffix is preserved; no delete, truncate, rewrite, auto retry same id or destructive cleanup API is added.

Resume may already have appended interrupted-turn closers (1949～1962); preserve these valid records and the original archive, then close ownership. A same-id fresh create may now report already-exists; caller must inspect/resume explicitly, not erase the archive. Fork preserves parent history and any accepted child seed/metadata. Persistence close may materialize accepted data; it is not rollback-to-nothing. Cleanup errors are reported/aggregated without masking the original fence cause or deleting data.

The new hook cannot append events, so no new unflushed suffix is introduced after append. Keep the existing storage backend semantics; any requirement for transactional disk invisibility would be a separate storage design, not implied by this patch. For an owned-admission failure, the current initializeAgent:1911/prepare-failure:1885 close catches must retain cleanup errors as secondary diagnostics with the original admission error as primary; do not silently discard a failed handle.close or replace the original cause. Leave unrelated legacy error behavior unchanged.

## 5. D2：READY revision、取消初始化与 drain 的分支

### 5.1 精确引用与退休

Owned generation tracks three disjoint holders: provisional admissions/bindings P, committed Agent users C, and already-issued read leases R. Per-holder release is idempotent; counters may mirror legacy users but must not double count. Physical scope is collection-owned under registry, not an own-Fiber structural child. Owner cleanup calls close and returns without waiting for P/activation/drain.

| 关闭时状态 | record/admission动作 | standing scope 与既有用户 |
|---|---|---|
| ACTIVATING，必有C=R=0 | 立即 closed/broken；wake新旧readers；abort provisional signal；迟到 activation永不READY | 对已分配精确 scope做fence/异步drain；无需等payload释放才拒收。 |
| READY，C+R=0（可能P>0） | 关闭新 admission、abort P；publicationCommit失败 | 不让P阻挡取消；scope进入fence/collection，factory rollback后归还P，drained等真实收敛。 |
| READY，C+R>0 | 关闭新admission/新child，abort P；标retired；现有 committed/issuedread正常释放 | **不dispose、不撤ready provider、不统一fence共享scope**。C/R使用旧revision继续；最后holder释放后才fence/drain旧scope。 |
| FAILED | 保留failed cause历史，close改公共终态为closed；无新admission | 排空失败清理；drain failure独立记录。 |
| 已CLOSED | first reason及generation不变；重复close无副作用 | 不影响new generation，不重启old cleanup。 |

Parent Agent已提交并不赋予关闭后新child的权利：{parent} selector冻结父实际revision但检查其owned admission开放；关闭后拒绝新child。此前已提交的子Agent继续其旧revision。id重用后旧parent不得悄悄继承新id的generation。legacy composeFrom继承retired的原语义不改；owned使用新protocol。

### 5.2 未完成 scope 的公开 fence 候选与阻断条件

SOURCE：只调用父 scope.dispose 会等待 inertia；assertActive只看自身uid。PROPOSED SDK内部 `fenceOwnedScope(scope.ctx.fiber)`：
1. record先closed，不依赖任何dispose；scope根 public Fiber.dispose 立即发起、不await。
2. 通过同一 registry.values()/Runtime.fibers，以 public Fiber.parent.fiber **对象身份**筛出该根后代；对每个live Fiber直接调用public dispose，消费返回Promise，不改uid/_runner/_error等字段。不得按id/uid数值误删别的runtime或retired已提交scope。
3. 无await地复扫至没有live owned后代，覆盖disposal listener重入创建；挂载开始/异步import返回点也检查record generation fence，已关闭则不建立新树。未来插件构造使用已disposed父Context，应由现有assertActive拒绝。
4. 逻辑关闭完成后，collection异步追踪scope.dispose及公开inertia，形成真实drained结果。所有late callbacks/child creations必须拒绝；不得用Promise完成替代SDK effect未再生的证据。

这仍是NOT_RUN的公开API组合，不声称源码已经证明任意异步/第三方代码可强制终止。必须用“已排队import continuation、inline ctx.plugin child、同步dispose-listener重入、barrier后late tools/prompt/skill注册”反例证明：record终态先完成且已关闭scope不能产生新的SDK-managed effect。物理I/O/任意JavaScript Promise不能被强制终止，drain pending如实记录。

**D2-B1设计阻断条件**：若同步复扫无法有界完成、漏掉非Entry子fiber、pending constructor在close后仍能进入activation，或late effect可在disposed ancestry下成功，则当前公开组合不足，不得宣称scope已fenced/继续产品。下一项需要的核心能力应明确为“owned scope的同步effect/child-admission fence，物理drain独立”，定位Cordis Fiber.assertActive/RegistryService.plugin或scope公开协议后另作独立设计/范围授权。**本票不预先批准修改vendor/cordis、vendor/loader或scope核心**。不以增加timeout/粗暴停registry根/fence全部旧revision补齐。

模块因果：close→record终态/readers唤醒；close→P abort；若无C/R则fence→异步drain。READY且C/R仍有时只retire→last release→fence/drain。没有owner dispose→等待payload的边。

## 6. D3：完整终态与兼容表

### 6.1 Promise及公共结果

ready是一次性历史结果；若已ready后close，ready仍是原ready结果，但新读取/attach/publication不得以它替代当前closed fence。closed只在首次close resolve；正常open READY不会虚构closed。drained在从未分配scope或scope/holders均真实排完后resolve drained；cleanup失败resolve drain-failed；任意不合作payload未收敛时可pending，但它不挡closed/roster/owner。所有routine结果均不产生未处理拒绝。

| 场景 | begin/ready/closed/drained | 当前record与reader |
|---|---|---|
| 空id/活动duplicate/inactive或cross-root owner | begin同步抛对应code；无lease/record/scope | 不改原record/default；已abort不能绕过这些输入校验。 |
| valid且signal已abort | 返回closed lease；ready=closed、closed立即；drained=drained，无activation | 不分配record/scope；新lookup not-found。 |
| 返回lease后、activation开始前close | ready=closed，closed立即；未分配scope则drain即可完成 | 短期tombstone；payload不得启动。 |
| activation成功 | ready=ready；closed/drained尚pending | 新admission可取得精确token；无隐含publication。 |
| activation失败 | ready=failed；closed等显式owner/signal/close；scope清理后drain | resolve/list broken、acquire invalid；不能READY。 |
| ACTIVATING close / signal / owner dispose | ready未settle则closed；closed立即first reason；drain独立 | 原waiters、新resolve/list均在payload release前closed/broken；acquire/未提交create拒绝。 |
| READY close，有C/R | ready历史不变；closed立即；drain等最后旧holder | record closed，新admission/child拒绝；已提交Agent不被取消/改绑。 |
| FAILED close | ready仍failed历史；closed立即；已完成drain不重置 | 公共closed原因优先，保留failed历史供诊断。 |
| 重复close/owner+signal同时 | first reason永久；所有effect/refs只释放一次 | 不抛第二个取消，不触及新record。 |
| 同id closed→new begin | 允许替换closed map slot，new generation identity不同 | old waiter仍答old closed，不重新resolve新id；old late drain只清old scope。活动他人record不可替换。 |
| tombstone回收 | drain完成且旧reader已得到终态后按identity删除 | 回收后not-found；barrier持有且drain未完时保持明确broken，保留原取消硬门；不依赖定时sleep。 |

Public诊断可新增reasonCode，但broken仍兼容现有字符串。Already-waiting diagnostic/resolve/list/acquireScope/compositionInventory必须订阅record终态；不能只保护新lookup。旧waiter捕获record后不得因map换代循环取得new generation。query异常不终止别的可读preset；其它无关legacy record仍保持其原审计语义，不宣称修复所有历史pending宿主行。

### 6.2 旧register与已公开行为

| 原接口/行为 | 必须保持 |
|---|---|
| register(definition) | 不加必需owner/signal，不默认包装成U；仍Promise<async disposer>，等待activation/diagnostic后返；empty/duplicate原异常及坏注册正常返disposer+roster broken保持。 |
| 返回disposer | 幂等，删除自己record并retire精确generation；有旧Agent users时保持revision到最后释放；不删除新同id记录（owned新增路径尤其须identity检查）。 |
| legacy mount/composeFrom/acquireScope | 返回metadata/string/readlease形状不变；原scope与revision保留行为不暗改。owned的新admission不得走无token旧mount/composeFrom；明确protocol-required。 |
| default/selectedDefault/list顺序 | 配置/volatile语义及排序保持；close不偷偷改用户default或fallback standard；同id新generation只影响之后开始的新请求。 |
| select/recompose | legacy锁/串行/事件语义保持。owned opt-in select事务需检查精确generation并同步提交；owned裸recompose无事务时拒绝，不能racy绑定。 |
| 既有Agent及cold archives | 不重写header/历史agentPreset，不序列化进程内generation token到存档；resume读取存档id后取得当前合法admission，关闭时拒绝并保留文件。 |

## 7. 最小补丁文件面及模块职责

下列repo根目录来自当前各package.json.repository.directory；实际源码基线/ref仍须隔离准备时与已钉发布物核对，不能猜tag。括号内是本次直接读取的已发布SDK文件；不在本机路径应用补丁。

| 上游模块 | 范围/职责 |
|---|---|
| packages/preset/agent-preset-registry（lib/index.js、lib/types/index.d.ts） | 新owned public facade/capabilities；内部owned-record单管state/waiters，admission单管lease/token/ref，scope-collection单管retire/fence/drain。不把全部逻辑塞入一个大register。 |
| packages/core/agent（lib/types/index.d.ts） | AgentSetupCommit增加可选publicationCommit，保留旧commit合同；不新增全局服务。 |
| packages/core/agent-loop（lib/index.js） | cache setupCommit、保持旧commit和append顺序，将final hook传进prepared.publish并在enter前调用；错误/handle cleanup复用原链。 |
| packages/api/session-controller（lib/index.js） | composeAgent及create/resume/fork全链传admission signal/token/disposer；不改文件上传/HTTP业务。 |
| packages/subagent/subagent、subagent-in-process-driver（lib/index.js） | acquire父精确revision、组合signal；setup组合delegation现有逻辑与publicationCommit。 |
| packages/webhook/webhook（lib/index.js） | 同一token跨workspace await到setup，finally释放；不改权限或删除workspace。 |
| 原生 agent-preset/产物类型/SDK测试 | 旧Service.init→register默认保持。本项目将由自身plugin消费U；若迁移所有原生row须另扩范围，不偷偷替换host rows。发布构建生成runtime/types需一致，不手修远程catalog暴露Context API。 |

静态DAG：registry facade→owned-state/admission/collection；admission→public scope/AgentSetupCommit types；AgentLoop只消费commit形状，不import registry；consumers→registry公开接口＋AgentRegistry工厂。state不依赖consumer/loop；collection不回调consumer；模块环=0。动态等待图独立验收，不从静态无环推断已通过。

## 8. 真实反例回归合同（全部NOT_RUN）

| ID | 必须先/后观测及失败条件 |
|---|---|
| T01 原permit后barrier | 保持原G失败的payload activation barrier；close/真实owner Fiber.dispose、closed、新resolve、已在等的resolve/list全部在release前完成broken/拒收；之后才release/drain。单纯late-dispose或更长timeout不通过。 |
| T02 初始消费者 | 自然boot首次lookup/显式default Web create不等自有READY；真实record.ready；非零schema，base accepted/broken gate不降。 |
| T03 storage/publication gap | backend append进入受控await后close，再完成append；publicationCommit拒绝；sessions/agents map和creation事件均未进入；handle关闭，已存prefix保留可读。 |
| T04 commit兼容 | old commit恰一次、其append仍被suffix存储；new hook不append/async；enter前抛错走原dispose。after-enter announce内close属于已提交revision，不伪称prepublication失败。 |
| T05 create/resume/fork | 每条真实controller链分别注入T03；resume原档及合法closers保留，fork父档不变；新child prefix不删；无write ownership泄漏。 |
| T06 subagent两驱动 | in-process one-shot create、continuable create/resume/fork seed分别测试；父旧gen close后child新admission拒绝，已提交父/子继续；委派persona/restrict/政策无越权。 |
| T07 generation重用 | acquire old→close old→same-id new→old storage completes；old必须拒绝，不按id换代；new独立通过；old drain不删new。 |
| T08 close状态表 | 已abort/close-before-start、失败、READY前后、并发owner+signal、重复close、tombstone回收、inactive/cross-root、duplicate逐行验证。 |
| T09 READY retention | 已提交Agent与readlease继续读原tools/skills/prompt；closed新admission/child/acquireScope拒收；最后旧holder释放后才物理drain。 |
| T10 scope fence | queued import、inline child、dispose-listener重入、late SDK effect；只处置owned scope，别的runtime/standard不动。任一绕过或无法有界收敛→D2-B1 BLOCKED，不改core/加timeout遮盖。 |
| T11 legacy合同 | 原register成功/坏注册/duplicate/disposer/default-selected/list排序/旧revision保留及select回归；不靠新U假造旧PASS。 |
| T12 publication边界 | 精确token未attach/重复attach/不同root/finalizer thenable；before-first-enter close拒收；commit到append gap与append到enter gap都覆盖。 |
| T13 存档和清理失败 | append已接受后fence拒绝、append/close自身失败、resume已有记录；报告may-exist、释放或显式报告未释放handle，绝不delete/truncate/retry覆盖。 |
| T14 隔离与分发 | SDK同代/同context、repo无host依赖、native HOME零写、无真实profile修改；补丁仅隔离checkout。真实current-web/link/refresh/skills完整矩阵仍后续独立门。 |

所有SDK owner及Agent consumer用真实Cordis/registry/AgentLoop/Session persistence合同，不fake registry；使用事件屏障而非sleep。记每条真实命令UTC/exit、事件sequence、schema计数、原始FAIL。测试仅验证补丁，不自动准入本项目产品/发布或重新安装。

## 9. 质量/蓝军与Proposed ADR

非功能映射：安全→append-only存档/精确scope处置；可用性→取消terminal不等drain；兼容→legacy默认不变；维护→显式capability与职责拆分；性能→close时只扫本runtime登记fibers并限定owned ancestry，性能基线待测，不每轮扫描；可观测→generation/close理由/holders/drain-outcome，避免私密路径或模型内容进入错误。

- BC-1：最后persist await内关闭→旧commit已过仍发布。D1新hook在publish内部enter前；T03/T12。
- BC-2：为停late effect误dispose READY旧scope→现有Agent坏。D2 C/R分支及精确scope；T09/T10。
- BC-3：old record waiter因id变化跳到new generation→取消者得到新能力。snapshot token不重resolve；T07。
- BC-4：失败后存档残留被清空→用户数据损坏。may-exist、close-only、保持prefix；T05/T13。
- BC-5：只关父scope便称全域取消→inline child晚注册。公开fiber census/fence先证伪；不能证明即D2-B1，另审核心范围。

**Proposed ADR（Coordinator机录）**：2026-10-19，题为“Owned registration终态与最终Agent publication分层”。背景为DEC-363授权隔离补丁、R3-B1及R4 D1-D3；推荐A，保留旧commit/legacy register，新增caller-owned record/admission/publicationCommit，把公共终态与物理drain分开；排除移动旧commit和本地cancel假修复。影响为§7六类SDK模块及测试，不含已安装SDK/profile或Core预授权。风险为公开scope fence尚需真实反例、持久化可能已存在；可逆性为丢弃隔离补丁/恢复已钉artifact，不回滚用户档案。后续为同一独立Design Reviewer审查D1-D3→仅批准的隔离实施→原反例及完整集成→FEAT102消费审查→CI/0.99→发布后重装；当前结论PENDING，Architect不自批。

## 10. 只读取证审计

下附完整命令JSON；执行期间未运行SDK/新probe、未联网下载、未安装、未读写用户profile、未改FEAT102历史。所有SOURCE都是静态证据，运行结果全部NOT_RUN。原型/旧报告字节由最终核对，审查结论由独立Reviewer给出。
完整 SOURCE 输出快照（仅仓内取证 scratch，不执行）：`.codex-sandbox/FEAT-103/design-r0/sdk-read-results.json`。它保存以下10条命令的原始stdout/exit，不补造失败查询的能力结论。

```json
[
  {
    "id": "F103-RO-01",
    "started_utc": "2026-10-19T11:12:28.9643358Z",
    "cmd": "$f103Started=[DateTime]::UtcNow.ToString('o'); Write-Output $f103Started; $f103Sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; $f103Lines=Get-Content -Encoding UTF8 \"$f103Sdk/dsh-agent-loop/lib/index.js\"; foreach($f103Span in @(@(1690,1788),@(1800,1918),@(1919,1985))){for($f103i=$f103Span[0]-1;$f103i -lt $f103Span[1];$f103i++){ '{0}: {1}' -f ($f103i+1),$f103Lines[$f103i] }}; rg -n 'setupAndPublish|preparePublication|publish\\(|enter\\(|appendUnstoredSuffix|release\\(|rollback|delete' \"$f103Sdk/dsh-agent-loop/lib/index.js\" | Select-Object -Last 65",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "impact_write": [],
    "access": "read-only installed SDK source/manifest; no SDK execution/network/profile read-write",
    "exit_semantics": "shell completion code; a piped no-match/nonterminating read can coexist with exit 0"
  },
  {
    "id": "F103-RO-02",
    "started_utc": "2026-10-19T11:12:28.9609662Z",
    "cmd": "$f103Started=[DateTime]::UtcNow.ToString('o'); Write-Output $f103Started; $f103Sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; $f103Lines=Get-Content -Encoding UTF8 \"$f103Sdk/dsh-agent-preset-registry/lib/index.js\"; foreach($f103Span in @(@(496,574),@(635,739),@(740,804))){for($f103i=$f103Span[0]-1;$f103i -lt $f103Span[1];$f103i++){ '{0}: {1}' -f ($f103i+1),$f103Lines[$f103i] }}; Get-Content -Encoding UTF8 \"$f103Sdk/dsh-agent/lib/types/index.d.ts\" | Select-Object -First 140",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "impact_write": [],
    "access": "read-only installed SDK source/manifest; no SDK execution/network/profile read-write",
    "exit_semantics": "shell completion code; a piped no-match/nonterminating read can coexist with exit 0"
  },
  {
    "id": "F103-RO-03",
    "started_utc": "2026-10-19T11:12:50.9953170Z",
    "cmd": "$f103Started=[DateTime]::UtcNow.ToString('o'); Write-Output $f103Started; $f103Sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n '(agentPresets|presets)\\.(mount|composeFrom|recompose|select)\\(' \"$f103Sdk\" -g '*.js' -g '!*.map' | Select-Object -First 100; $f103Lines=Get-Content -Encoding UTF8 \"$f103Sdk/dsh-api-session-controller/lib/index.js\"; foreach($f103Span in @(@(350,460),@(788,834))){for($f103i=$f103Span[0]-1;$f103i -lt $f103Span[1];$f103i++){ '{0}: {1}' -f ($f103i+1),$f103Lines[$f103i] }}; rg -n 'composeFrom|setup:|\\.create\\(|\\.resume\\(|parentAgent|fork' \"$f103Sdk/dsh-subagent/lib/index.js\" -ErrorAction SilentlyContinue | Select-Object -First 90",
    "exit_code": 1,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "impact_write": [],
    "access": "read-only installed SDK source/manifest; no SDK execution/network/profile read-write",
    "exit_semantics": "shell completion code; a piped no-match/nonterminating read can coexist with exit 0",
    "query_note": "The final guessed dsh-subagent query passed PowerShell-only -ErrorAction to native rg and errored; this query is not evidence of absence. Correct subagent paths/content were read in RO-05/07."
  },
  {
    "id": "F103-RO-04",
    "started_utc": "2026-10-19T11:12:51.0023382Z",
    "cmd": "$f103Started=[DateTime]::UtcNow.ToString('o'); Write-Output $f103Started; $f103Sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; $f103Lines=Get-Content -Encoding UTF8 \"$f103Sdk/dsh-agent-loop/lib/index.js\"; foreach($f103Span in @(@(1607,1690),@(1781,1802))){for($f103i=$f103Span[0]-1;$f103i -lt $f103Span[1];$f103i++){ '{0}: {1}' -f ($f103i+1),$f103Lines[$f103i] }}; rg -n 'class SessionPreparation|SessionPreparation|prepare\\(|enter\\(|announce\\(' \"$f103Sdk/dsh-session/lib/index.js\" | Select-Object -First 35; rg --files \"$f103Sdk\" -g '*.d.ts' | rg 'session-persistence|session-store|session-storage' | Select-Object -First 30",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "impact_write": [],
    "access": "read-only installed SDK source/manifest; no SDK execution/network/profile read-write",
    "exit_semantics": "shell completion code; a piped no-match/nonterminating read can coexist with exit 0"
  },
  {
    "id": "F103-RO-05",
    "started_utc": "2026-10-19T11:13:04.6810692Z",
    "cmd": "$f103Started=[DateTime]::UtcNow.ToString('o'); Write-Output $f103Started; $f103Sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n 'composeFrom|parentAgent:|parentAgent,' \"$f103Sdk\" -g '*.js' -g '!*.map' | Select-Object -First 90; $f103Lines=Get-Content -Encoding UTF8 \"$f103Sdk/dsh-session/lib/index.js\"; foreach($f103Span in @(@(940,996),@(1678,1698),@(1734,1790))){for($f103i=$f103Span[0]-1;$f103i -lt $f103Span[1];$f103i++){ '{0}: {1}' -f ($f103i+1),$f103Lines[$f103i] }}; Get-Content -Encoding UTF8 \"$f103Sdk/dsh-session-persistence/lib/types/handle.d.ts\" | Select-Object -First 175",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "impact_write": [],
    "access": "read-only installed SDK source/manifest; no SDK execution/network/profile read-write",
    "exit_semantics": "shell completion code; a piped no-match/nonterminating read can coexist with exit 0"
  },
  {
    "id": "F103-RO-06",
    "started_utc": "2026-10-19T11:13:04.6787864Z",
    "cmd": "$f103Started=[DateTime]::UtcNow.ToString('o'); Write-Output $f103Started; $f103Sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$f103Sdk/dsh-scope/lib/index.js\" | Select-Object -Skip 278 -First 32; Get-Content -Encoding UTF8 \"$f103Sdk/cordis/lib/index.js\" | Select-Object -Skip 1068 -First 30; Get-Content -Encoding UTF8 \"$f103Sdk/cordis/lib/index.js\" | Select-Object -Skip 1168 -First 115; Get-Content -Encoding UTF8 \"$f103Sdk/dsh-agent/lib/index.js\" | Select-Object -Skip 535 -First 75; Get-Content -Encoding UTF8 \"$f103Sdk/dsh-agent-preset/lib/index.js\" | Select-Object -First 33",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "impact_write": [],
    "access": "read-only installed SDK source/manifest; no SDK execution/network/profile read-write",
    "exit_semantics": "shell completion code; a piped no-match/nonterminating read can coexist with exit 0"
  },
  {
    "id": "F103-RO-07",
    "started_utc": "2026-10-19T11:14:31.8610591Z",
    "cmd": "$f103Started=[DateTime]::UtcNow.ToString('o'); Write-Output $f103Started; $f103Sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; $f103Lines=Get-Content -Encoding UTF8 \"$f103Sdk/dsh-subagent/lib/index.js\"; foreach($f103Span in @(@(470,545),@(1035,1100))){for($f103i=$f103Span[0]-1;$f103i -lt $f103Span[1];$f103i++){ '{0}: {1}' -f ($f103i+1),$f103Lines[$f103i] }}; Get-Content -Encoding UTF8 \"$f103Sdk/dsh-subagent-in-process-driver/lib/index.js\" | Select-Object -Skip 137 -First 85; Get-Content -Encoding UTF8 \"$f103Sdk/dsh-webhook/lib/index.js\" | Select-Object -Skip 138 -First 56; Get-Content -Encoding UTF8 \"$f103Sdk/dsh-agent/lib/index.js\" | Select-Object -Skip 473 -First 69",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "impact_write": [],
    "access": "read-only installed SDK source/manifest; no SDK execution/network/profile read-write",
    "exit_semantics": "shell completion code; a piped no-match/nonterminating read can coexist with exit 0"
  },
  {
    "id": "F103-RO-08",
    "started_utc": "2026-10-19T11:14:31.8264093Z",
    "cmd": "$f103Started=[DateTime]::UtcNow.ToString('o'); Write-Output $f103Started; $f103Sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n 'composeChildAgent|AgentSetupCommit|commit\\(|setup:' \"$f103Sdk/dsh-subagent/lib/index.js\" \"$f103Sdk/dsh-subagent-in-process-driver/lib/index.js\" | Select-Object -First 80; Get-Content -Encoding UTF8 \"$f103Sdk/dsh-session-persistence/lib/types/index.d.ts\" | Select-Object -Skip 50 -First 115; rg -n 'assertActive|_execute\\(|runner.epoch|assertActive\\(' \"$f103Sdk/cordis/lib/index.js\" | Select-Object -First 35; Get-Content -Encoding UTF8 \"$f103Sdk/dsh-system-prompt/lib/index.js\" | Select-Object -Skip 485 -First 32; rg -n 'register\\(|effect\\(' \"$f103Sdk/dsh-tools/lib/index.js\" | Select-Object -First 20",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "impact_write": [],
    "access": "read-only installed SDK source/manifest; no SDK execution/network/profile read-write",
    "exit_semantics": "shell completion code; a piped no-match/nonterminating read can coexist with exit 0"
  },
  {
    "id": "F103-RO-09",
    "started_utc": "2026-10-19T11:18:11.3003988Z",
    "cmd": "$f103Started=[DateTime]::UtcNow.ToString('o'); Write-Output $f103Started; $f103Sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$f103Sdk/cordis/lib/types/registry.d.ts\" | Select-Object -Skip 40 -First 160; Get-Content -Encoding UTF8 \"$f103Sdk/cordis/lib/types/plugin.d.ts\" | Select-Object -First 155; Get-Content -Encoding UTF8 \"$f103Sdk/cordis/lib/index.js\" | Select-Object -Skip 1123 -First 45; rg -n 'class RegistryService|\\[Symbol.iterator\\]|values\\(|entries\\(' \"$f103Sdk/cordis/lib/index.js\" | Select-Object -Last 30; Get-Content -Encoding UTF8 \"$f103Sdk/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 850 -First 45",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "impact_write": [],
    "access": "read-only installed SDK source/manifest; no SDK execution/network/profile read-write",
    "exit_semantics": "shell completion code; a piped no-match/nonterminating read can coexist with exit 0",
    "query_note": "Guessed cordis/lib/types/plugin.d.ts did not exist. Plugin.Runtime/public RegistryService declarations were present in registry.d.ts; missing file not used as capability evidence."
  },
  {
    "id": "F103-RO-10",
    "started_utc": "2026-10-19T11:20:39.6301888Z",
    "cmd": "$f103Started=[DateTime]::UtcNow.ToString('o'); Write-Output $f103Started; $f103Host='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh'; $f103Sdk=\"$f103Host/node_modules/@deepseek-ai\"; foreach($f103Pkg in @($f103Host,\"$f103Sdk/dsh-agent-preset-registry\",\"$f103Sdk/dsh-agent-loop\",\"$f103Sdk/dsh-agent\",\"$f103Sdk/dsh-scope\",\"$f103Sdk/cordis\",\"$f103Sdk/cordis-plugin-loader\",\"$f103Sdk/dsh-subagent\",\"$f103Sdk/dsh-subagent-in-process-driver\",\"$f103Sdk/dsh-api-session-controller\",\"$f103Sdk/dsh-webhook\",\"$f103Sdk/dsh-session-persistence\")){ $f103M=Get-Content -Encoding UTF8 -LiteralPath \"$f103Pkg/package.json\" | ConvertFrom-Json; [PSCustomObject]@{name=$f103M.name;version=$f103M.version;directory=$f103M.repository.directory} | ConvertTo-Json -Compress }; foreach($f103File in @('dsh-agent-preset-registry/lib/index.js','dsh-agent-loop/lib/index.js','dsh-agent/lib/types/index.d.ts','dsh-api-session-controller/lib/index.js','dsh-subagent/lib/index.js','dsh-subagent-in-process-driver/lib/index.js','cordis/lib/index.js')){ $f103Hash=Get-FileHash -Algorithm SHA256 -LiteralPath \"$f103Sdk/$f103File\"; [PSCustomObject]@{file=$f103File;sha256=$f103Hash.Hash} | ConvertTo-Json -Compress }",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "impact_write": [],
    "access": "read-only installed SDK source/manifest; no SDK execution/network/profile read-write",
    "exit_semantics": "shell completion code; a piped no-match/nonterminating read can coexist with exit 0"
  }
]
```
