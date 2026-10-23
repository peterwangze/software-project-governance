# FEAT-103 — D1–D3 隔离 SDK 补丁设计独立审查 R0

- 日期：2026-10-20（Asia/Shanghai）；取证 UTC 08:18:49–08:23:21。
- 身份：新实例 `/root/sdk_design_review_r0`，独立 Design Reviewer；不是设计作者，也不是 FEAT-102 旧 Reviewer。按 `agents/design-reviewer.md`、`skills/design-review/SKILL.md`、`skills/tech-review/SKILL.md`执行。
- 输入设计：`docs/architecture/dsh-upstream-owned-registration.md`，SHA256 `be5741d44a74751efaabe371f50fd3ce3a4d0e3a7e8ce041faa0c6cae12fb52f`。
- 前置：canonical resolve 的 `resolved_root_ok=true`；项目 standard / always-on × maximum-autonomy，第11阶段、11 Gates passed。Coordinator 已执行 full 健康（42 issues，并非 PASS）及本任务修复/复审 ALLOW。本实例不重复深检、不写治理。
- 权限：任务明确允许静态 SDK 取证、仓内 scratch 和本报告；未执行 SDK、probe、测试、安装、网络、用户交互、提交、推送或外发。真实环境只有安装包源码/类型/manifest 读取；未读用户 profile/session。所有 SDK 取证进程 HOME/USERPROFILE/APPDATA/LOCALAPPDATA/DSH_HOME/TEMP/TMP/cache 均重定向本任务 scratch。

## 1. 结论

```text
conclusion=NEEDS_CHANGE
unresolved_blockers=3
round=0
review_identity=NEW_INDEPENDENT_INSTANCE
review_scope=FEAT103_D1_D2_D3_CURRENT_SDK_DESIGN
current_sdk=0.2.1-rc.2
design_recorded_sdk=0.2.0-rc.2
implementation_authorized=false
authorized_slice=NONE_PENDING_ARCHITECT_REVISION_AND_R1
actual_runtime=NOT_RUN
storage_regression=NOT_RUN
scope_fence=PROPOSED_NOT_RUNTIME_VERIFIED
product_wiring_authorized=false
installed_sdk_write_authorized=false
release_authorized=false
feat102_r5_obligation=OPEN_REQUIRED_INDEPENDENT_ACTUAL_RECHECK
```

D1 最后存储 await 后、`prepare.publish` 内第一个 enter 前的同步 fence；D2 P/C/R 分支、READY 已提交 revision 只退休；D3 逻辑终态独立于物理 drain，均是正确且可实施验证的设计方向。本轮不因“补丁尚未实现/运行”拒绝设计，也不把 FEAT-102 R3/R4/R5 的 actual 依赖搬成本票设计阻塞。

三项阻塞是明确的所有权触发缺口及当前消费者语义遗漏。原设计允许 LOADING owner，却未冻结如何在其 loading inertia 未结束前观察 dispose 起点；当前 SDK 又增加了独立 child preset、cold resume 和 Web blank-session 复用/回退，不能把昨日的父 selector 和 createOrAdopt 表照抄到当前基线。最小修订后可以继续本范围隔离补丁，无需先修改 Cordis 核心或重选其它路线。

## 2. 基线与直接证据

安装态已是完整同代 `0.2.1-rc.2`：DSH、registry、agent、agent-loop、scope、session-controller、subagent、session、session-persistence 的直接 manifest 均如此；Cordis 仍 `4.0.5`、Loader `1.0.6`。这只是静态安装态事实，不说明何人何时升级，也不是 runtime 验收。Coordinator 在收到漂移后要求继续按当前基线核对，保留旧设计历史。

令 N=`C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai`。下表均为本实例直接读取，完整字节 hash/argv/UTC/影响路径见取证 JSON。

| 当前 N 下文件 | SHA256 | 关键事实 |
|---|---|---|
| dsh-agent-preset-registry/lib/index.js | `95edcc66175a87091ba90fe0809246821df470bf960e1cfd725b5ca6baaf4f07` | :470–520 晚 disposer；:533–543 diagnostic 等 ready/audit；:632–652 retain 按 id 重试；:701–711 父 revision；:750–769 select；:775–806 read lease/inventory。 |
| dsh-agent-loop/lib/index.js | `cf57e3ecd487ac5c2553455aaa5cef2c6fb41e6bd61be5aa455675d1d7193033` | :1931 old commit、:1932 append await；:1789 assertLive、:1790 Session enter、:1791 Agent enter；:1993 resume closers。原 gap 仍存在。 |
| dsh-agent/lib/types/index.d.ts | `3531899158347ff10627228732c67462c78ea0352e31a7eabc19631f90b08bc1` | AgentSetupCommit 仍只有同步 commit；新增 hook 必须显式增加类型/runtime，不能当现有能力。 |
| cordis/lib/index.js | `6a9394c0877ff45218818c6e815edd038f8057e1a1deb390a8d43ec81c57691e` | 与昨日记录相同；:1078 清自身 uid、:1079 发 internal/plugin；:1084–1089 等 inertia；:1372–1383 才跑 effects。 |
| cordis/lib/types/registry.d.ts | `1188a67702253930766e6b03670b8f906e87ac11623c9aa69012215552a6f354` | Runtime.fibers、Fiber.parent、registry.values 为公开面；不是私有表改写许可。 |
| dsh-scope/lib/index.js | `2829df71d76e08941457d4dd173eac60783e55354921137c8b75e8b5c0d2ecca` | :282–305 dispose 跟踪自身 Fiber 与 inertia，不能代替后代同步 fence。 |
| dsh-api-session-controller/lib/index.js | `a9801acb577b03053c5d5a3191ff555c5f1d791d0acddec113bea4511e33b386` | :416–464 claim/reuse/fallback，:467–489 live/select 与 reuseSetup；昨日 createOrAdopt 已不是当前实现。 |
| dsh-subagent/lib/index.js | `9a9572e70fffdb100deb63326167f32bbf63016ce49c0017495dabcb95b44168` | :373–382 独立选择与父继承分支；:1794–1824 统一 local create/resume；:2164–2182 cold 独立选择恢复。 |
| dsh-subagent-spawn-in-process/lib/index.js | `249df2c7bdc046c1dd7149acbb40e604eabcba28a7e07ffa4226c2a03f0a3aaa` | :21–27 声明支持独立 preset，不继承父上下文；factory 已在共享 manager。 |
| dsh-subagent-fork-in-process/lib/index.js | `2ce7fff41b6e0f634087ccd1a11a9e1538e7619b1fb936cb990ea3a11564cb99` | :35–47 不支持独立 preset，提供父历史 seed；共享 manager 负责工厂。 |
| dsh-session/lib/index.js | `2f5dd07cb5c744a29abbb8003a8a4cefd9e582c6e2538074ca299a0ddd02a3bf` | :1853–1883 enter 同步无创建事件；:1579–1598 append 有验证/同步 observer 边界，select 事务不能只假定它永不失败。 |
| dsh-session-persistence/lib/types/handle.d.ts | `0218ad845fb8191dc46c507a41bc56587321236cb6a2a9ac25ef78f83a4ddcc5` | append-only、已接受前缀、close 完成 durability/释放 ownership；没有通用安全 delete/rollback。 |

当前发布物的 301 个 `*/lib/index.js` 做了静态 consumer census（RO04 在后续请求缺文件前已读完这批 index）；RO05 再核同一集合和 package manifests。该有界 corpus 找到 controller、共享 subagent 的 mount/composeFrom 以及 registry 自身；remote select 由 registry 事务收口。它不证明仓外第三方不存在。旧 `dsh-subagent-in-process-driver/lib/index.js` 直接读取不存在；manifest census 未出现旧 webhook 包。不能据此断言 webhook 已从上游仓库删除，也不能声称本次已核对当前 webhook 消费实现。旧源码快照只能作历史证据，不是当前匹配包。

历史绑定：R4=`327ca0ed36fcfe923baaf9d9ab308e5aad6676afbb2ea8f37d4bcfe6b14eb314`；R3=`1e79068ba6cd480cb4b70da0f9d8738d8ece70ea3dea378e1bd957c08c8bb6d4`；G 诊断=`22430209e92114a0ae140e3aec91fe9de9c7637a8d1114c270ebd452d3103d1c`；G 原型=`db81b2136f74fe64c7313720d81040c319c8a99e40e0e1c47f43270408bd8809`；permit 后取消 raw=`09ba2f1c9e8eb4a086507f0e7e5d86dc256f388d0bbd9a4e2d5c5e6e6b9cc025`，均直接核 hash且未写。昨日静态 snapshot SHA=`f2828cda0900bff2d85f6515ce793e801ffdf835424d94249f785315b71ccd64`。

## 3. 阻塞项与最小解除条件

### R0-B1 [BLOCKING/P1] LOADING owner 的 dispose 起点没有连接到 record close

设计 §3 允许 LOADING/ACTIVE owner，并要求先安装 owner cleanup，提及 effect 注册失败；§5.1 只规定 cleanup 调用 close 且不等 activation。**尚未指定在 owner 自身 activation pending 时，哪个同步公开触发器会先调用 close。**

反例链：owner initializer 调用 beginRegistration 后 await lease.ready → payload 持有 activation barrier → owner Fiber.dispose 清 uid 并等该 initializer 的 inertia → `_unload()` 尚不能跑 owner 的 cleanup effects → record 未收到 close、ready 不终结 → owner dispose 仍等 ready。物理 scope 虽归 registry collection，也不能消除 owner 自己这条等待边。此为当前 Cordis 源码推导，**没有新运行失败**；其源 hash 与旧基线相同。

**最小解除**：Architect 明确 dispose 起点到逻辑 close 的公开触发机制、监听者所有权、精确 Fiber 对象身份过滤、订阅前后 active/uid 校验及清理顺序；普通 effect cleanup 保留幂等兜底，不能独担 early notification。当前公开 `internal/plugin(Fiber)` 类型及同步发射点可作为候选事实，必须核对它的 dispatch/监听存活语义后冻结，不需预批 core 修改。若决定不允许 owner await ready，必须形成明确可执法 API 合同并保持用户原取消目标，不能默许自然调用进入等待环。

T01/T08 增加 **真实 LOADING owner initializer 正在 await 本 lease.ready** 的子例：barrier 保持时 owner dispose/closed/新旧 readers 都终结，然后才 release/drain。另覆盖 owner 已 ACTIVE、订阅与 dispose 重入、registry 自身开始卸载；不把 payload barrier 释放后的 cleanup 算 early close。解除为设计明确机制及反例合同、独立 R1 核对，actual 测试仍留实现阶段。

### R0-B2 [BLOCKING/P1] 当前独立 child preset/cold resume 会被统一父 selector 改错

设计 §4.1 把 materializeTracked 和旧 in-process-driver 均冻结为 `{parent: parent.ctx}`。当前 `ChildComposition.agentPreset` 公开类型明确：有值是独立选择；无值才继承父 revision。共享 manager 的两个 setup 分支仍分别执行，coldResume 从子自身 selection projection 恢复独立 id。spawn provider 支持该能力，fork provider 不支持。

反例链：父使用 A、spawn 指定 B → 当前 header/selected 记录 B → 按设计统一取父 A 的 token并 attach → 子实际 tools/prompt 成 A，而 durable identity 仍 B；或为保留 B 而留下旧 mount，则 owned 绑定绕过最终 fence。cold B 在父 A 下恢复有同样问题。两种都违反现有选择语义/精确 generation 合同。

**最小解除**：以当前共享 materialization 冻结 selector 分支：显式/冷恢复独立选择使用对应 id 的精确 reservation；只有继承分支使用父实际 generation。保留 provider capability、lineage/委派权限、descriptor/persona/toolFilter、workingDirectory、structured runtime 的现有顺序。父 owned generation 关闭后的新 child 拒收规则也须明确承接，不能以独立选择悄悄放宽，或用父 token替换独立选择。更新 helper 的公开返回类型和 setup 的 hook 传递。

补丁地图改为当前共享 `packages/subagent/subagent`；spawn/fork provider 已只提供 capabilities/seed，不能因为旧文件名就向它们重复加 factory。旧 driver/webhook 历史保留；当前未安装 webhook 如仍属完整目标，先声明当前匹配源码/依赖未取得、后续独立核对，不混入旧包或声称已覆盖。T06 增加 A父/B子、B closed而A可用、父closed新child拒收、继承fork、独立cold resume和各存储 gap 的明确预期。

### R0-B3 [BLOCKING/P1] Web 新 claim/live-reuse/fallback 不满足单次 token 的完整所有权合同

设计围绕旧 createOrAdopt，规定 composeAgent acquire、factory finally release、attach single-use；当前 `claim` 已会先取得 composition，再返回 live Agent、调用 select，或在 resume 异常后拿同一 composition 创建新 id/重新 claim。`reuseSetup` 是实际 hook 包装点。设计没有定义这些新增分支的 lease 生命周期。

具体因果：

1. live 同 preset直接返回（:473），没有 factory/finally消费或释放新 reservation；若照旧补丁只在 create/resume处释放，会留 P/监听者。更早一律 acquire 又可能因 registration closed拒绝本来只复用既有 committed Agent 的请求，改变 D2 保留既有会话的边界。
2. live 改选走 `select(live,targetId)`（:475），外层 composition 的精确 token没有交给它。G1 在 compose 后 close、同 id 替换 G2时，select重新按 id取得G2会把同一次冻结请求换代；只在 select内部另取“精确”reservation不能修复这个问题。
3. :461–463 的 resume→minted/claim回退会重用 composition；single-use attach/调用方 dispose 后不能再次使用同一 lease。反过来，无条件重新按 id acquire又可跨 generation。虽然部分异常发生于attach前，本合同必须逐分支说明，不能假定全部都未消费。

**最小解除**：Architect 画出一次 createSession/claim operation 与每次 factory attempt 的两个 lifetime：无新 admission 的 live复用、live switch事务、新建/冷resume分别在哪个边界持有/释放；给 `reuseSetup` 返回完整 commit；定义尚未attach token可复用的回退、已消费/回滚后的处理及是否结束当前operation。任何继续同一冻结admission的路径都不得默默换代。live switch使用冻结reservation的SDK内部事务分支，持有旧binding到selected append成功；append/observer准备抛错时不能留半binding，不能先collect旧scope后企图回滚。该要求复用设计已有 select原子性目标，不要求改Session核心。

T05/T07/T09/T11 增加：live同选择且registration关闭、live真正改选、G1 close→G2替换、blankness在writer获得前改变、SessionAlreadyOwned回退、setup前/attach后失败、每个出口 P/C/R及listener归零断言。解除是具体分支合同+测试预期并经R1，不要求本轮先跑runtime。

## 4. D1–D3 逐项裁定

| 项 | 独立裁定 |
|---|---|
| D1 old commit / 最终 hook | **设计可保留**：old commit恰一次仍在append前；cache后把新hook传入publish，紧接assertLive、在两个enter前同步调用。当前源码仍吻合。禁止observer/await/append/按id重resolve；thenable应拒绝并消费其拒绝，保留T04/T12。 |
| D1 精确token / consumers | **需B2/B3修订**：API create/resume/fork主链可接；当前共享child选择及Web复用不是昨日路径。third-party owned旧mount/composeFrom显式protocol-required可接受，legacy保持原形状。 |
| D1 持久化 gap | **设计可保留**：fence拒绝时published:false、may-exist，close exact handle、保留header/seed/suffix/合法resume closers；不删、不截断、不自动覆盖重试。cleanup次要错误不能吞掉或盖原cause。 |
| D2 P/C/R | **设计可保留**：P不保护未提交generation；publication promotion解除registration-close→factory abort；C/R有值只retire，最后释放才fence/drain；同id旧cleanup精确identity。 |
| D2 owner→close | **需B1修订**；单纯把physical scope移出own不能证明LOADING owner无等待环。 |
| D2 后代公开fence | **准入隔离证伪的设计方向成立，actual NOT_RUN**：公共values/fibers/parent/dispose确实存在；按对象身份仅关owned后代、不假定父dispose覆盖全树正确。同步复扫有界、inline child/import continuation/reentrant listener/late effect是T10退出门；失败即D2-B1停，不越权改vendor。不能把这一显式实验不确定性本身计为本轮BLOCKING。 |
| D3 状态/Promise | **定义完整**：ready历史一次性，closed首次原因，drained独立；already-aborted无activation、失败/关闭优先级、tombstone identity、旧waiter不跳新代、late rejection消费都有合同。 |
| D3 legacy / 已有session | register默认Promise/坏注册disposer/duplicate/default/selected/list排序/retired revision保留有明确要求；token不写存档。B2/B3修订须覆盖当前cold child与live reuse，否则“旧API未改”不足以证明用户兼容。 |

## 5. 精确实施边界

**本轮当前写入面只有本报告与 `.codex-sandbox/FEAT-103/review-r0/`；未批准产品/SDK实现。** 下表是三项修订通过后可冻结的隔离范围，不能当作本轮已获实施许可；也不能在安装态N应用。

| 模块（当前manifest repository.directory） | 可定位的发布物补丁面/职责 |
|---|---|
| packages/preset/agent-preset-registry | `dsh-agent-preset-registry/lib/index.js`及`lib/types/index.d.ts`：owned-state/waiters、admission/ref、collection、capabilities；补齐B1公开owner触发及B3 live-switch事务，职责分开。 |
| packages/core/agent | `dsh-agent/lib/types/index.d.ts`：可选publicationCommit、旧commit不改。 |
| packages/core/agent-loop | `dsh-agent-loop/lib/index.js` :1786–1804、:1915–1955及精确owned cleanup诊断：cache hook/最终enter前调用；不改其它driver业务。 |
| packages/api/session-controller | `dsh-api-session-controller/lib/index.js` composition、claim/reuseLive/reuseSetup/create/resume/fork；返回/异常/回退均有精确lease所有权。 |
| packages/subagent/subagent | `dsh-subagent/lib/index.js` applyChildComposition、materializeTracked及实际start/cold输入传递；`lib/types/child-agent.d.ts`及必要返回形状导出投影。 |
| packages/subagent/subagent-spawn-in-process、subagent-fork-in-process | 当前只是provider/seed；默认只读核兼容、纳入测试，不据旧driver表自动改写。 |
| 匹配基线的SDK tests/构建生成物 | T01–T14及B1–B3新增反例；runtime/types必须同源生成。上游源码真实文件路径/ref须隔离准备时由匹配manifest映射核对，不虚构tag或手修安装发布物。 |
| 当前未取得的 webhook | 旧0.2.0源码只作历史；不能混装补齐或声称current已覆盖。匹配版本源码若另取得，先提交精确consumer点供同范围复核。 |

`vendor/cordis`、`vendor/loader`、`packages/core/scope`、Session/Persistence核心不在预批写面；host rows/global services、工具列表/业务策略、用户存档/profile、暂停FIX-444/445、旧报告/raw均不在写面。若公开scope fence试验被证伪，停止并明确最小核心能力缺口，再独立范围裁定。

## 6. 六维度、非功能与蓝军

| 六维度 | 结论 |
|---|---|
| 方案完整性 | A/B/C三候选；先定存档安全→无等待环→publication→兼容→修改量标准；旧commit移位与本地race方案排除理由充分。 |
| 模块结构 | facade→state/admission/collection；consumer→公开registry/AgentFactory；loop只依赖commit形状，静态环0。运行等待图仍有B1，不能用静态DAG替代。 |
| 接口契约 | 新API/错误/状态/引用大部具体；B1触发、B2 selector、B3操作lifetime未冻结，硬门未过。 |
| 安全/非功能 | 精确scope、存档保全、已有C/R保留正确；未声称强停任意JS。B2选错能力及B3换代/旧会话回归须先修。 |
| 可演进/验证 | 显式opt-in/capabilities与legacy分离合适；T01–T14保持原barrier、事件屏障及NOT_RUN诚实，补当前分支即可，无需全仓重复测试。 |
| 独立Bar Raiser | 本新非Producer实例完成独立源码/类型核查、失败视角挑战并给出否定项；无独立性冒充，无进度压力豁免。 |

| 非功能需求 | 设计支撑 | 满足程度/遗留 |
|---|---|---|
| 取消可用性 | record终态先于activation/drain、新旧waiter唤醒 | state方向满足；owner触发B1待修，actual NOT_RUN。 |
| 存档安全 | append-only、may-exist、close-only、原cause+次要cleanup错误 | 合同满足；T03/T05/T13实现后验收。 |
| 版本/会话兼容 | legacy默认不变、C/R保留、opaque token不落盘 | 当前child/live复用B2/B3待修。 |
| 维护/扩展 | facade/state/admission/collection拆责，loop不依赖registry | 设计满足；源码映射准备时核对。 |
| 性能 | 仅close时扫描registry fibers、精确owned ancestry | 扫描总fibers而非只预筛owned，复杂度随同root fibers增长；T10须记录census/复扫轮数与有界退出，不夸称已测性能。 |
| 可观测 | generation/reason/P/C/R/drain outcome、真实事件顺序/错误 | 可满足；补新增分支计数与dispose-start事件，避免敏感数据入错误。 |

失败框架的三项假设：H1=owner cleanup能早于owner activation结束；H2=所有child都继承父preset；H3=每次composition只走一次factory。源码已说明三者均不能预设。

| ID/视角/攻击向量 | 后续三步及影响 | 当前缓解 | 残余风险 | 建议增强 |
|---|---|---|---|---|
| BR1 攻击者：LOADING owner await ready | 持payload→dispose等inertia→cleanup不触发close，取消可用性失效 | scope归collection、close独立 | 高，B1 | 冻结dispose-start公开触发及真实barrier反例。 |
| BR2 愤怒用户：A父显式B子/coldB | 子header=B→attach A→实际能力与历史不一致 | 精确token及单次attach | 高，B2 | 两种selector分支/旧cold内容兼容。 |
| BR3 维护者：claim走零factory或回退 | P/监听留存→被消费lease重用或重取id→换代/失败难定位 | finally与幂等release原则 | 高，B3 | operation/attempt lifetime及所有出口计数。 |
| BR4 愤怒用户：persist已接受后关闭 | final fence拒绝→handle close物化→用户下次遇already-exists | may-exist、保留原档、显式inspect/resume | 低、待测 | 保留T13，绝不delete/truncate遮盖残留。 |
| BR5 攻击者：十倍fibers/late inline child | 父dispose→部分后代仍active→late SDK effect再生或同步复扫失控 | 公共后代census、T10、D2-B1退出 | 中、NOT_RUN | 验证无关scope不受影响、复扫有界；失败先停。 |

硬门：候选3≥2 PASS；ADR日期/背景/决策/备选/理由/影响/后续字段齐 PASS；蓝军5≥3 PASS；静态模块环0 PASS；独立评审已执行 PASS；接口/所有权安全硬门因B1–B3 FAIL。不是架构根本否决，故为NEEDS_CHANGE而非BLOCKED。

## 7. 回归与收口约束

原G seq18–21 own dispose/cleanup完成、seq22新resolve、seq23持barrier下750ms失败的事实不变；只证明record pending未及时拒收，没有证明取消后创建成功或数据损坏。失败后late-dispose、0unhandled、teardown TypeError都不能抵销原门。当前SDK static同样存在晚disposer/gap，未重跑原型。

保留原T01–T14，并补B1–B3所列反例；不降schema/base accepted/broken门，不延时或先release帮助通过。READY C/R旧会话保持功能、关闭后新admission/child拒收、old/new同id隔离，以及persist失败保全是可观测验收，不以方法存在替代。thenable hook拒绝、cleanup失败、scope重入与owner-loading必须有序列证据。

下一步：Architect仅修B1–B3及当前source/consumer re-anchor，保留旧0.2.0历史→同本实例R1静态复核→通过后由Coordinator派精确隔离实现/运行。FEAT-102 R5 actual依赖义务保持OPEN，本报告不关闭它、不标适配完成、不授权产品接线、发布或重装。未运行本身不是本轮设计阻断。

## 8. 命令与写入审计

机器审计总表：`.codex-sandbox/FEAT-103/review-r0/command-audit.json`，包含每次完整实际shell command、`python -B`实际argv、UTC起止、exit、全部读取路径/hash及仓内写入；各`R0-RO-XX.result.json`保留原stdout。所有真实环境写路径均为空。原始reader的`actual_argv`来自sys.argv，省略了Python `-B`解释器选项；总表明确补列从实际shell命令取得的完整argv，不把该原始显示误当完整进程参数。

```json
[
  {"id":"R0-RO-01","utc":"2026-10-20T08:18:49.800961+00:00","exit":0,"sdk_files_read":8,"real_write":[]},
  {"id":"R0-RO-02","utc":"2026-10-20T08:19:18.991947+00:00","exit":0,"sdk_files_read":3,"real_write":[]},
  {"id":"R0-RO-03","utc":"2026-10-20T08:19:48.072336+00:00","exit":0,"sdk_files_read":6,"real_write":[]},
  {"id":"R0-RO-04","utc":"2026-10-20T08:20:19.961893+00:00","exit":1,"sdk_files_read":303,"real_write":[],"note":"旧driver路径不存在；前序census有效，不把缺文件当全局无能力"},
  {"id":"R0-RO-05","utc":"2026-10-20T08:20:49.508624+00:00","exit":0,"sdk_files_read":608,"real_write":[]},
  {"id":"R0-RO-06","utc":"2026-10-20T08:21:20.813233+00:00","exit":1,"sdk_files_read":5,"real_write":[],"note":"猜测composition.d.ts缺失；RO07/08已读准确child-agent.d.ts"},
  {"id":"R0-RO-07","utc":"2026-10-20T08:21:34.171740+00:00","exit":0,"sdk_files_read":25,"real_write":[]},
  {"id":"R0-RO-08","utc":"2026-10-20T08:22:19.767241+00:00","exit":0,"sdk_files_read":8,"real_write":[]},
  {"id":"R0-RO-09","utc":"2026-10-20T08:23:21.819742+00:00","exit":0,"sdk_files_read":10,"real_write":[]}
]
```

取证脚本只用Python标准库读取UTF-8字节/JSON/匹配行，不import/执行SDK；两次exit1是事实取证请求错误，均披露并定位准确替代文件，没有产生runtime结论。首次bootstrap查找误命中仓内FIX-453 scratch resolver后，已用准确canonical路径立即重跑；均resolved_root_ok=true，不作为SDK命令或产品证据。独立审查写入仅本新报告及授权scratch；不更改治理、index/refs、产品、旧设计/报告或原raw。
