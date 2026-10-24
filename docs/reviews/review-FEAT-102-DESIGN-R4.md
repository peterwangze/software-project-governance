# FEAT-102 — 上游 registration lease 提案范围复审 R4

- 日期：2026-10-19（Asia/Shanghai）；同一独立 Design Reviewer。
- 规范：design-reviewer、design-review、tech-review；真实环境红线保持。
- 前轮：`docs/reviews/review-FEAT-102-DESIGN-R3.md`，SHA-256 `1E79068BA6CD480CB4B70DA0F9D8738D8ECE70EA3DEA378E1BD957C08C8BB6D4`。
- 输入：架构 §15，SHA-256 `AD417E66F45C45E3B492442ADDAEA3223F3683EBAC011018527F4EA6D21E4429`。
- 范围：只审查提案是否足够具体供用户决定扩展到隔离上游补丁；仅写本报告。Coordinator 已预取锁并报告 ALLOW，review-feat102-r4 请求仍列 R3 未关闭阻塞。没有执行上游补丁、SDK升级、原型重跑、安装、产品接线或任何HOME/profile写入。

## 1. 分开记录提案成熟度与实际阻塞

```text
conclusion=NEEDS_CHANGE
unresolved_blockers=1
carried_blocker=R3-B1_OPEN_REQUIRED_RECHECK
proposal_review=SCOPE_DECISION_READY_WITH_REQUIRED_DETAILS
upstream_capability=PROPOSED_NOT_IMPLEMENTED
implementation_authorized=false
upstream_patch_authorized=false
feasibility_probe_authorized=false
authorized_slice=NONE
product_wiring_authorized=false
runtime_support=NOT_RUN
release_authorized=false
```

**§15 已足够形成用户范围决策材料**：说明了为什么当前插件自身无法取得登记撤回权、拟新增的同步lease、逻辑终态/物理drain分离、真实owner、所有等待读者唤醒、generation隔离及publication fence；列出修改面、回归、隔离基线和不扩展范围的后果。可以由 Coordinator 据此询问用户是否扩展到独立隔离的上游协议补丁/验证。

这不等于实现设计已全部冻结，更不等于补丁存在或适配通过。本轮继续 NEEDS_CHANGE/1 的原因是 **R3-B1 依赖缺口未实现/未验证**，不能用提案文档把未关闭RECHECK改成零阻塞。没有新增产品授权、风险接受或发布许可。后述具体细节须进入首个上游设计检查点/验收合同，不能藏在“只加一个方法”的范围描述中。

## 2. R3 要求逐项核对

| R3 义务 | §15 状态 | R4 裁定 |
|---|---|---|
| 不能用本地cancel/late-dispose顶替record撤回 | §15.1/15.4明确由registry持有record终态，新U不当shim | 提案已回应；actual API仍缺，R3-B1不关闭。 |
| activation前可取得本record关闭权 | 同步beginRegistration→lease；owner effect调用close；id/root校验 | 所需新契约明确，尚无实现证据。 |
| 新lookup及已有waiter及时拒收 | closed/ready终态与activation分离；tombstone；所有readers观察close | 必要且覆盖旧map删除不足；须用真实等待者回归。 |
| own卸载不等payload，无等待环 | logical owner≠physical scope；collection管理drain | 方向正确；registry自身卸载及scope fence仍须精确实现。 |
| 迟到完成/旧generation不复活、不伤新record | identity fence、原子替换、精确scope清理 | 提案已覆盖，NOT_RUN。 |
| 首lookup/gate/accepted audit等原门不降 | §15.5先复用同一barrier，之后恢复未跑矩阵 | 保持；新SDK单元绿不能代替本项目全链。 |
| 原始失败/用户卸载保持 | §15.1/15.6均保留，未称unsupported为完成 | 符合边界；R3/G/raw immutable。 |

§15.2 官方发布物核查由 Architect 留有精确版本、integrity、内存读取及命令审计。本 Reviewer 没有重新联网抓取next包，故不伪称独立复验全部官方元数据；该输入也没有新runtime证据。无论next结论如何，本机已核查的R3-B1仍不能靠版本字符串或能力提案解除。

## 3. 独立源码核查：已有commit接口与真正提交点必须区分

本轮只读 N=`C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai` 的相关SDK，不重跑G：

1. **公开 AgentSetupCommit 已存在。** N/dsh-agent/lib/types/index.d.ts 定义同步 `commit():void`、AgentSetup返回值和Create/Resume setup事务契约。可以考虑复用该公开形状，不必先假定需要发明新的factory接口。它对真正consumer调用方开放，不等于普通preset row自动拥有setup扩展权；原H的缺口没有因此消失。
2. **现有实现不能仅凭类型注释认定是最终原子点。** N/dsh-agent-loop/lib/index.js:1889先执行setup返回的commit，:1890仍await appendUnstoredSuffix，:1891才调用publish；appendUnstoredSuffix :1839～1843可能await持久化。实际sessions.enter/agents.enter在:1748～1749。故commit与可见发布之间存在异步间隔，不能简单“在现有commit检查一次lease”就宣称close后不会发布。
3. N/dsh-api-session-controller/lib/index.js:358～369 当前setup只await presets.mount，不返回commit。registry :639～700 retain/bind/mount目前返回preset metadata，没有公开的本次绑定generation验证token。U消费链需要把**精确generation**的提交验证从registry绑定传给setup，并在真正可见发布点检查；不能按id重新resolve后悄悄换代。

这些是SOURCE，不是本轮新运行失败，也不推定宿主违反了此前并不存在的U协议。它们说明“registry+实际publication调用点”的补丁范围有必要；现有公开hook名称不能代替因果证明。

## 4. 实施前必须冻结的具体细节

这些细节不妨碍用户决定是否授权隔离研究/补丁，但尚不能据现稿直接宣称产品设计完成。

- **D1 精确generation提交token与真正原子点**：明确哪个opt-in公开返回值携带generation fence（mount准备结果、lease派生commit或其它明确接口）、谁将其交给AgentSetup、谁在最后一次相关await后/第一处可见enter前同步验证；create/resume/fork/subagent逐一列真实调用点。保留已有commit兼容形状可降低修改量，但实际AgentLoop间隔需要处理。还须定义持久化已经发生后、最终fence失败的rollback/句柄释放及未发布记录处置，不能引入用户存档删除/损坏。不得用agent/created后的补偿冒充未发布拒收。
- **D2 close与既有Agent revision的状态分支**：§15.4.4要求取消前已提交Agent继续按现有revision保留，§15.4.5又要求SDK注册能力关闭。应明确ACTIVATING的迟到初始化context与READY且仍有既有用户的standing scope分别怎样fence/retire/drain；不能为了禁止迟到effect而一律dispose仍被已提交Agent使用的scope，也不能给旧activation留下重新注册的窗口。新子Agent admission与既有Agent继续运行分开定义。
- **D3 完整终态/兼容表**：冻结close-before-start、已abort signal、inactive/cross-root owner、READY后close、FAILED后close、重复close、tombstone回收/同id复用的结果；明确ready/closed/drained分别何时resolve/reject、错误码、旧waiting消费者与新lookup的结果。旧register默认行为及返回形状不能暗改；既有坏注册返回disposer/roster broken、duplicate id、default/selected、retired revision保留均要回归。若V包装U，也必须保持相同终态，而非只提前reject调用者。

优先以registry/实际consumer/AgentLoop已公开机制实现。若SDK-managed scope fence确实需要改Cordis/scope核心，应将具体缺口和修改边界另列设计审查；本轮不预先批准核心变更。提案中的 `capabilities.ownedRegistration='terminal-cancel-v1'`、beginRegistration及其lease均仍是PROPOSED，不可在当前runtime凭空检测为支持。

## 5. 六维度、蓝军与验证要求

| 维度 | R4判断 |
|---|---|
| 方案完整性/必要性 | U/V/W三机制有责任边界与证伪点，U针对真实record owner；没有用新名词替代实现，足供范围决策。W不推荐且未接受。 |
| 模块/所有权 | 逻辑close独立于物理activation/drain的DAG正确；未把scope挂own物理子树。实际collection/registry卸载与既有revision分支需D2及测试。 |
| 接口契约/API兼容 | 新opt-in lease、能力声明、旧register保留方向明确；D1/D3需冻结，actual API仍缺。 |
| 安全/非功能 | 强调新旧waiter、取消后publication、迟到effect和数据安全；不承诺强制终止任意JS Promise。drain未收敛要观测，不能卡owner/roster。 |
| 可验证性/维护 | 先同barrier原失败，再interleaving/identity/普通preset/完整适配；范围和NOT_RUN诚实。能力协议而非打包宿主副本符合解耦目标。 |
| 独立Bar Raiser | 同一非Producer Reviewer检查§15和actual public/setup代码；保留R3 blocking，无实现冒充通过。 |

失败框架挑战：

| ID/视角 | 攻击链 | 提案已有回应与必须验证 |
|---|---|---|
| R4-BR1 愤怒用户 | own卸载→物理scope成子节点→又等待payload→close不及时 | 逻辑owner/物理collection分离；原permit后barrier持有时owner dispose/closed/new及旧readers均先终结，再drain。 |
| R4-BR2 攻击者 | commit已检查→await存储时close→publish取消generation | D1要求最后await后真正publication fence、精确token、rollback；仅接口注释不够。 |
| R4-BR3 维护者 | old generation drain晚到→删新id或换代复活 | identity原子替换+late cleanup只处理旧scope；测old close/new begin/late resolve交错。 |
| R4-BR4 愤怒用户 | READY旧Agent被close全量失效→原会话突然坏 | D2区分新admission/未完成初始化与已有committed revision；回归已有会话、子Agent边界及retirement。 |

验证矩阵还应显式包含：已经进入resolve/list/retain/Agent create的旧等待者；关闭后新读取；close与signal/owner同时发生；重入关闭；cancel后SDK late effect/provider/child plugin；ready成功后close及publication/storage gap；普通standard roster/会话/旧register不退化。异步persist/fence反例使用事件屏障，原raw保持；不得fake registry、sleep等待、提前release或只检查最终drain。

## 6. 建议给用户的授权范围应怎样具体表述

可请求的下一范围是：**在独立隔离上游checkout中补齐并验证调用方拥有的registration终态取消协议，包含registry、精确generation的实际preset consumer和AgentLoop publication边界；必要scope fence先做公共能力取证，若需扩大核心修改另行明确。**

范围材料应同时明确：基线固定当前精确发布物/同代依赖；不改用户已安装DSH/profile，不重装插件；不混装单个registry；不向上游发消息/提交PR；先过D1～D3设计检查点与独立API审查，再实施/验证；产品消费、支持矩阵、CI/0.99发布与真实重装仍有后续独立门。不能把授权描述压缩成“只加signal参数”或“完成后自动安装”。

用户未扩展范围时，§15.6中已有任务授权范围内的CI/纯策略/工具诊断准备仍可推进；FEAT-102不标完成，0.99范围/延期由用户另定。本报告不替用户移除适配目标或接受flight pending风险。

R4继续保留R3-B1及RECHECK义务。后续提案/上游代码/真实回归完成后，须凭实际新API及同一反例修复证据再独立复审；当前runtime/support仍BLOCKED/NOT_RUN。只写本报告，旧审查、架构、G原型/raw未改。

## 附录：本轮外部只读命令

没有新网络抓取、包执行、宿主运行或用户环境写入。UTC现场打印，exit为exec完成码。

```json
[
  {
    "id": "R4-RO-01",
    "command": "$r4Started=[DateTime]::UtcNow.ToString('o'); $sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n -C 3 'async create\\(|async resume\\(|setup\\(|options.setup|\\.set\\(|agent/created|createAgent\\(' \"$sdk/dsh-agent/lib/index.js\" | Select-Object -First 120; Get-Content -Encoding UTF8 \"$sdk/dsh-agent/lib/types/index.d.ts\" | Select-Object -First 105; $g=Get-Content -Encoding UTF8 \"$sdk/dsh-agent-preset-registry/lib/index.js\"; for($i=638;$i -lt 703;$i++){ '{0}: {1}' -f ($i+1),$g[$i] }; Write-Output \"COMMAND_STARTED=$r4Started\"",
    "time_utc": "2026-10-19T06:15:12.8211479Z",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-agent/lib/index.js",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-agent/lib/types/index.d.ts",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-agent-preset-registry/lib/index.js"
    ],
    "impact_write": [],
    "access": "read-only installed SDK; no host process/profile read/write"
  },
  {
    "id": "R4-RO-02",
    "command": "$r4Started=[DateTime]::UtcNow.ToString('o'); $sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n -C 8 'setupCommit|\\.commit\\(\\)|options.setup|setup\\?\\.|setup\\(' \"$sdk/dsh-agent-loop/lib/index.js\" | Select-Object -First 132; $w=Get-Content -Encoding UTF8 \"$sdk/dsh-api-session-controller/lib/index.js\"; for($i=352;$i -lt 380;$i++){ '{0}: {1}' -f ($i+1),$w[$i] }; Get-Content -Encoding UTF8 \"$sdk/dsh-agent/lib/types/index.d.ts\" | Select-Object -Skip 100 -First 62; rg -n 'setup.*commit|AgentSetupCommit|setup:' \"$sdk/dsh-agent-loop/lib/types/index.d.ts\" | Select-Object -First 28; Write-Output \"COMMAND_STARTED=$r4Started\"",
    "time_utc": "2026-10-19T06:15:46.4493172Z",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-agent-loop/lib/index.js",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-api-session-controller/lib/index.js",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-agent/lib/types/index.d.ts",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-agent-loop/lib/types/index.d.ts"
    ],
    "impact_write": [],
    "access": "read-only installed SDK; no host process/profile read/write"
  },
  {
    "id": "R4-RO-03",
    "command": "$r4Started=[DateTime]::UtcNow.ToString('o'); $sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n -C 7 'publish:|publish\\(|async publish|appendUnstoredSuffix|sessionPublication|\\.enter\\(' \"$sdk/dsh-agent-loop/lib/index.js\" | Select-Object -First 190; Write-Output \"COMMAND_STARTED=$r4Started\"",
    "time_utc": "2026-10-19T06:15:56.7482031Z",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-agent-loop/lib/index.js"
    ],
    "impact_write": [],
    "access": "read-only installed SDK; no host process/profile read/write"
  }
]
```

