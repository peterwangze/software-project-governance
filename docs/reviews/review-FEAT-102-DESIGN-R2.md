# FEAT-102 — 初始 seed 与激活 guard 方案复审 R2

- 日期：2026-10-18（Asia/Shanghai）
- 角色：原独立 Design Reviewer；绑定 `agents/design-reviewer.md`、`skills/design-review/SKILL.md`、`skills/tech-review/SKILL.md`。
- 前轮：`docs/reviews/review-FEAT-102-DESIGN-R1.md`（SHA-256 `48442E8130B82B741FC8D5C68AF94C2CE74B3C3793861DF66B0B9BC2FB259B4F`）；R0/R1 保留不改。
- 设计输入：`docs/architecture/dsh-adapter-version-decoupling.md` §14，SHA-256 `B92C7CA5491DD316A4AC3434C5C7F8A97AE0AE0C244418782C84C188CDE526BE`。
- 实测输入：`docs/diagnostics/dsh-native-admission.md`，SHA-256 `EB2BB44B1C190CC42B3C0B70695DDCEFCF7F282D427174E45226E60024814031`。
- 治理锚定：plan-tracker FEAT-102/0.99.0；Coordinator 已预取 expected-new 锁并报告 re-review ALLOW；next18-FEAT-102 请求仅列本报告写入路径。
- 执行边界：只读设计、旧审查、原始诊断和安装态源码；仅新写本报告。不做实现/运行/安装/发布，不改设计、产品、治理账本或用户 profile。

## 1. 结构化裁定

```text
conclusion=APPROVED_WITH_NOTES
unresolved_blockers=0
review_scope=G合同变更与最小隔离证伪准入
implementation_authorized=false
feasibility_probe_authorized=true
authorized_slice=S-A3_G_ONLY
contract_change_authorized=PROTOTYPE_ONLY
product_wiring_authorized=false
runtime_support=NOT_RUN
release_authorized=false
legacy_runtime=UNSUPPORTED_NO_AUTOWRITER
candidate_L=FAILED_EXITED
```

允许 **S-A3_G_ONLY**：只在隔离原型中检验 §14.4/14.5 的 G。公开构件足以支持一次受限、可证伪的试验，尚不能证明完整 G 可运行。首次正常冷启动或任一安全/等待/保真硬门失败即停止 G 并返回同 Reviewer，不复活 L/M，不自动转 C/F/H，不扩大产品接线。

本次明确接受**仅供原型的合同扩展**：原业务内容仍只改 persona.prefix 和两个 skill roots；但增加本包 guard、私有 readiness realm 和真正受 inject 阻挡的 payload wrapper，是额外的基础设施结构差量。不能继续称整个 derived tree “除了两个字段全都原样”，也不能把本批准当成 §3/§4 产品协议已经更新。未来产品化必须逐项同步协议、结构比较、地址/表达式/isolate 支持范围、测试及文档，并独立复审。

零未解决阻塞仅适用于上述试验准入。S-A 的时序失败、S-A2 的 L 失败继续有效，产品可行性仍未证明；不存在“接受已知 race 后合入”的授权。DEC-187、不改宿主 row/源码、不反向依赖、不裸 import 宿主、不私读 definitions/_config、不写 HOME、不放宽 base audit 等约束保持。

## 2. R1 义务逐项复核

| 前轮项目 | 本轮判定 | 依据 |
|---|---|---|
| R1-BR1：L 冷启动/通知/own inertia | **实测失败，退出；未修复** | S-A2 首个 normal-first 已 boot-return，tasks=0，own PENDING/inertia=false/activationCount=0，governance not-found。§14.1 不再准入 L，没有 notify/Entry.init/重排行补救。 |
| R1-BR2：base audit 不能反向等自身 | **L 中 NOT_RUN；G 提出新的待证等待图** | §14.4.5 在 own activation 结束后由 standing guard 审计真正 host settle、accepted config 和无 broken；不得删 audit。源码支持 standing tree 当前不挂入 host entries，但整体无环尚未验证。 |
| R1-BR3：真实 dispose 可能先等 activation | **L 中 NOT_RUN，不能继承 S-A detached PASS** | G 不 await register/guard/mount；仍 await SDK import。§14.4.6、A3-3要求分别观察 import 和 mount/audit 的真实 Fiber.dispose，不凭 cleanup 函数无 await 下结论。 |
| R1-BR4：register 前异步点与首 lookup | **未解决的产品前提；G 的 A3-1 明确证伪** | SDK import 是唯一允许准备 await，必须处于 own activation；其后 register 同步入 record，再结束 activation。不得在 register 前另安排 detached 任务。 |
| R1-BR5：成功返回但 broken/非法 base | **保持硬门** | G 需要 gate 在 accepted/broken 审核前彻底阻止 payload，错误令本记录 invalid；schema/normalized seed 不替代有效 base。 |
| R0/R1 headless 勘正 | **保持** | 首次预设 consumer 仍是真实 list/resolve/Web SessionController；headless 不计 governance 首会话证据。 |
| 旧 writer 与用户卸载边界 | **保持并明确** | legacy UNSUPPORTED_NO_AUTOWRITER；用户主动卸载状态不变，发布前不重装、不 repair profile。 |
| 热刷新、完整 link/current-web/skills/tools/CI/版本发布 | **继续未授权/未验收** | G 仅先行原型；不能借 SDK 构件或本报告解锁 S-B～F。 |

S-A2 raw 的 sequence0 actual-boot-return=68.280ms，sequence1 public snapshot tasks=0/own PENDING=69.448ms，sequence2 first-lookup-start=70.225ms，sequence3 lookup not-found=71.299ms，sequence5 root-drain=75.903ms。它证明本次 L 接线没有 admission 保证；没有证明永久 PENDING、宿主缺陷或 L 卸载矩阵通过。schema=0，后续 A2-3/4/5 不补填 PASS。两次采集是同一失败场景及状态补充，不算两个独立通过/失败矩阵。

## 3. 公开 API 与等待链独立核对

N 根为 `C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai`。以下为本轮直接只读 SOURCE；没有运行宿主。

| ID | 源码/类型锚点 | 可以支持的判断及限制 |
|---|---|---|
| R2-S01 | N/cordis-plugin-loader/lib/types/config/group.d.ts 公开 data/tree；lib/index.js:78–92 先 this.data=config 再 Promise.all 并发 create | own parent 的 literal group 输入在同组 child activation 前完整赋值，支持 seed 读取；不代表嵌套 Include 已展开或宿主已接受。只能克隆，不修改 data；scope 完整性必须独立证明。 |
| R2-S02 | Loader lib/index.js:214–227 public tree.import；N/dsh-agent-preset/lib/index.js 的 default runtime.Config 与 EntryGroup.key | 可从所选 tree 取得真正 native schema 并用公开 resolveConfig 规范化复制的 seed；不能 raw import SDK/复制 schema。Tree.import 当前在不同 runtime 路径有不同解析分支，实际同 context 模块路径必须实测。 |
| R2-S03 | EntryOptions 类型公开 inject；Loader Group lib/index.js:104–115 只在 Group 构造/Service.init 后 update children；Cordis lib/index.js:1045–1061 将 service inject config 绑定本 Fiber | 真正阻挡 payload 的 **Group 依赖** 有公开机制。单独把 async guard 与原 rows 并列只会并发激活，不满足合同。必须让 payload 所在 Group 本身依赖尚未提供的专属 service。 |
| R2-S04 | Registry lib/index.js:65–74 的 PresetTree 保存/恢复 owner.subtree/subgroup，write为空；mountPreset :262–270 通过独立 tree挂载/audit | 当前 standing tree 不应出现在 host Loader entries 等待集合，提供 guard等host、host不等guard 的候选依据。产品不得自行改这些内部字段；不能将当前实现事实提升成所有未来 DSH 的承诺。 |
| R2-S05 | Registry :500–523 在await activate前同步写record；:557–564 resolve诊断先等record.ready，pending audit再回退host await | own activation调用register后可立即结束，首lookup可看见pending record并等ready；这条因果链必须通过真boot/初始import暂停实证，不能在register前detached。 |
| R2-S06 | Registry :197–221 auditRows 等 tree和Fiber，分别记录failed/pending；:269–284 mountPreset只因failed/leaked抛错；:540–543 activate将异常转broken | **pending本身不总令register失败**。guard拒绝必须成为真实 failed/invalid；不能只留payload Group PENDING并把register返回当审核拒收成功。取消/缺state/旧nonce也须明确拒收并无READY。 |
| R2-S07 | Loader :526–557 isolate按祖先继承并为entry-local realm分配symbol；Registry mount类型及 :113起 leakedServices按root realm检查泄漏 | 专属readiness可放在本包frame局部realm，不能落host root/普通preset。该realm只隔离本包readiness，不可重新隔离/替换vendor服务或更改其provider。wrapper表达式/地址/继承影响仍需A3-4。 |
| R2-S08 | Cordis :1077–1089 dispose等待现有inertia；:1349–1368 _reload等待插件effect后才清inertia/卸载 | G避免在own activation await mount有合理依据；SDK import仍会拖住own inertia。准备超时只能是有界失败，不能计作正常卸载PASS。guard permit取消必须独立于host barrier。 |
| R2-S09 | Registry mount类型/public livePresetMounts(within)与实现 :82–109 按实际root Fiber identity限定runtime | 若辅助用mount audit，必须当前runtime且避免退休revision误用；优先对settled当前base调用public resolve。禁止用同id任意mount猜当前revision。 |

**待证因果图**：

```text
host Group.data 完整受限输入
  → own activation[同 tree SDK import / clone+schema / create generation]
  → register 同步建立 record → own 返回cleanup → host root可settle
                         ↘ standing guard 等 generation permit
                              ← audit[host settle → 唯一accepted base → seed相等 → resolve无broken]
                         ↘ Group.inject 在permit service出现前不启动payload
                              → payload mount/audit → record.ready → lookup/compose
```

图的关键不是“guard在后台”，而是 host 的等待集合确实不含 standing guard、own effect不含register Promise，以及 payload实际被gate阻挡。任一边反向接回root/self，或guard审核前启动任何payload，候选即失败。

## 4. 六硬门的准入判据与范围

沿用 A3-0～5，不删门、不以预期失败替代成功。初始支持仅同一组合group中的直接native声明和可完整遍历的literal group；未知Include/动态注册/跨树未展开来源一律 SOURCE_SCOPE_UNSUPPORTED。这个有限范围获准**试验**，未获准宣称满足完整current-web支持目标。

1. **A3-0 seed/context**：记录真实parent/tree/group、完整scope规则、normalized seed与后续Fiber.config、真实tree.import路径；clone后再做schema校验。禁止写host data、依赖先出现entries猜唯一性、harness manifest解析冒充产品解析。正常冷启动未进入own或跨context立即停。
2. **A3-1 admitted/lookup**：真实boot后第一条固定governance list/resolve及显式/default Web create不等READY；SDK import暂停时host不能越过admitted；register之后mount/audit延迟必须由record.ready等待。需记录源码因果与raw，不靠mkdir、微任务偏序、固定sleep。
3. **A3-2 accepted/真实gate**：seed不是BaseSnapshot。raw更新失败、旧Fiber有效、seed不同、disabled/缺失/重复/broken/pending都不能先放payload再撤回。permit屏障未释放时，以真实payload apply/tool/prompt/skill sentinel证明零副作用；不只看guard日志或Group状态。拒收时guard必须真实失败/record invalid，不能只留下PENDING。
4. **A3-3 cancel/dispose**：通过真实Fiber.dispose触发，分别卡在host/guard audit、register-flight、SDK import；记录请求、cleanup、dispose、release、late-dispose。mount/audit前不得靠提前释放它们才清理成功。还须观察**permit已放行但register仍在飞行**的取消窗口：旧epoch不得报READY或供新consumer使用，迟到disposer只能处理自己；缺state/stale nonce失败。取消结果若只能靠等待原屏障释放成立，判FAIL。import的有界准备失败单列，不包装成正常卸载通过。
5. **A3-4 isolation/fidelity**：readiness不泄漏root/普通preset/并行会话；private realm不能阻断vendor服务传播；wrapper前后disabled !!js、relative模块/entry地址、既有isolate/group及用户配置保真，未知shape拒收。真实payload schema非零；故意坏注册无READY。
6. **A3-5 exit/evidence**：首次正常/安全/无环失败保存raw并停止G，不替换fake registry，不转C/F/H，不补测通过掩盖失败。即便全部原型门通过，仍回同Reviewer核对源码因果与产品范围后才可能授权下一切片。

上列第3/4项是 §14.4.4～7 和 A3-2/3 对“真正gate、取消传播、无READY”的具体观察标准，不新增宿主API或授权产品自修。任何未验证前提保持NOT_RUN；许可不等于预测它们会通过。

## 5. 独立蓝军、候选及硬门

框架切换为“G最可能怎样失败”。核心假设H1=seed来源完整且最终accepted相等；H2=Group.inject真正阻断所有payload；H3=host/standing等待与cancel方向独立。均不预设成立。

| ID/视角 | 攻击链与影响 | 已有设计回应 | 残余风险/本轮裁定 |
|---|---|---|---|
| R2-BR1 维护者 | sibling Include晚展开→漏重复base→seed误当接受值→启动错误策略 | §14.4.1/5完整scope、postsettle比较；A3-0/2 | 高/NOT_RUN；受限literal输入，unknown拒收，不猜无重复。 |
| R2-BR2 攻击者 | guard与payload并排→并发children→prompt/tool先挂→拒收已太晚 | §14.4.4显式gated Group.inject、sentinel门 | 高/NOT_RUN；实际阻挡前零副作用；仅并行siblings直接FAIL。 |
| R2-BR3 愤怒用户 | guard连回host等待→root等registry→guard等root→启动/卸载锁死 | §14.4.3/5/6，PresetTree独立性、cancel permit | 高/NOT_RUN；真实等待图和真实Fiber.dispose，不手动cleanup替代。 |
| R2-BR4 攻击者 | SDK import卡住→own inertia不结束→cleanup迟迟不运行 | §14.4.2/6有界准备及A3-3 | 高/NOT_RUN；bounded失败不当PASS，不能静默detached后让boot越过register。 |
| R2-BR5 维护者 | extra wrapper改ctx/entry地址或realm→条件/相对路径变义→普通功能回归 | §14.4显式合同扩展、A3-4保真/拒收 | 高/NOT_RUN；不能仍以“只有两差量”豁免比较。 |
| R2-BR6 攻击者 | 取消发生在permit后/mount完成前→迟到完成→旧generation报READY/新consumer误用 | §14.4.6/7 epoch/permit取消/late disposer；A3-3取消传播 | 高/NOT_RUN；在真实消费者观察窗口，不只查drain后的最终列表。 |

候选独立评估：G较L明确改变等待边，使一次原型有依据；C-G多文件快照/运行态一致性面且仍需guard，不自动更优；F受预载限制并有Fiber等待取消风险；H尚缺公开加法mount与setup契约，当前SOURCE_REJECTED_AS_PRIMARY合理，不能把该源码判断写成已运行失败。M/L都不在本次准入。保留原A/B/C/D取舍，试验失败不构成全局注入或复制整套工具的授权。

| 六维度/硬门 | 结论 |
|---|---|
| 方案完整性 | 原四候选+本轮G/C-G/F/H清楚；先定标准、列代价/缺契约，PASS（试验准入）。 |
| 模块结构 | entry→lifecycle→source/overlay/state，guard→state，state不import宿主；静态模块环0。动态等待环未验证，必须实测。 |
| 接口契约 | InitialSeed/GuardedDefinition/Permit与generationId/nonce/取消边界明确；extra基础设施差量显式，PASS（原型），产品协议仍冻结。 |
| 安全/非功能 | 零HOME/不改host/只拥有自己record；普通preset保全、明确失败、有限scope；性能/维护成本新增guard/state，需后续实证，不假称零成本。 |
| 蓝军/独立Bar Raiser | 同一独立Reviewer读取失败raw、核对公开构件、六项挑战并对应Producer既有回应，完成；无Producer自批。 |
| ADR字段 | §12/§14有日期/背景/候选排除/影响/风险/可逆/后续动作，完整；仍Proposed，不伪造运行批准。 |

## 6. 交接与自检

Coordinator 可机录本R2并派最小S-A3_G_ONLY；只在repo sandbox启动，真实HOME/profile、已安装SDK和FIX-444/445 WIP保持。S-A3需要具体路径/模块/结构/事件/退出码/schema计数/取消drain/NOT_RUN，首次硬门失败即回同Reviewer。完整link安装/current-web、技能实际读取、热刷新、工具schema及CI/0.99标准发布底线维持前轮。

本报告不解除产品设计条件，不修改任何已有结论，不安装插件，不把用户“发布后再装”解释成现在可修复登记。仅新报告写入，R0/R1/设计/诊断输入hash将在交付前复核。外部命令只有三条源码读取，未运行宿主；SOURCE不是runtimePASS。

## 附录：外部命令逐条审计

时间由命令执行时打印的UTC采集，exit为exec完成码；影响路径只有读取。查看内部实现用于核验公开API语义，不授予产品调用内部字段权限。

```json
[
  {
    "id": "R2-RO-01",
    "command": "$r2Started=[DateTime]::UtcNow.ToString('o'); $sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$sdk/cordis-plugin-loader/lib/types/config/group.d.ts\" | Select-Object -First 76; $l=Get-Content -Encoding UTF8 \"$sdk/cordis-plugin-loader/lib/index.js\"; for($i=0;$i -lt 122;$i++){ '{0}: {1}' -f ($i+1),$l[$i] }; for($i=212;$i -lt 229;$i++){ '{0}: {1}' -f ($i+1),$l[$i] }; Get-Content -Encoding UTF8 \"$sdk/dsh-agent-preset/lib/index.js\"; Write-Output \"COMMAND_STARTED=$r2Started\"",
    "time_utc": "2026-10-18T12:12:49.5337275Z",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis-plugin-loader/lib/types/config/group.d.ts",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis-plugin-loader/lib/index.js",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-agent-preset/lib/index.js"
    ],
    "impact_write": [],
    "access": "read-only installed SDK; no host process/profile read/write"
  },
  {
    "id": "R2-RO-02",
    "command": "$r2Started=[DateTime]::UtcNow.ToString('o'); $sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; $g=Get-Content -Encoding UTF8 \"$sdk/dsh-agent-preset-registry/lib/index.js\"; foreach($span in @(@(64,116),@(189,226),@(257,306),@(499,567))){for($i=$span[0];$i -lt $span[1];$i++){ '{0}: {1}' -f ($i+1),$g[$i] }}; Get-Content -Encoding UTF8 \"$sdk/dsh-agent-preset-registry/lib/types/mount.d.ts\" | Select-Object -First 85; Get-Content -Encoding UTF8 \"$sdk/cordis-plugin-loader/lib/types/config/entry.d.ts\" | Select-Object -First 49; Write-Output \"COMMAND_STARTED=$r2Started\"",
    "time_utc": "2026-10-18T12:13:10.8519715Z",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-agent-preset-registry/lib/index.js",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-agent-preset-registry/lib/types/mount.d.ts",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis-plugin-loader/lib/types/config/entry.d.ts"
    ],
    "impact_write": [],
    "access": "read-only installed SDK; no host process/profile read/write"
  },
  {
    "id": "R2-RO-03",
    "command": "$r2Started=[DateTime]::UtcNow.ToString('o'); $sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; $l=Get-Content -Encoding UTF8 \"$sdk/cordis-plugin-loader/lib/index.js\"; foreach($span in @(@(332,356),@(359,380),@(449,491),@(519,528),@(551,559))){for($i=$span[0];$i -lt $span[1];$i++){ '{0}: {1}' -f ($i+1),$l[$i] }}; $c=Get-Content -Encoding UTF8 \"$sdk/cordis/lib/index.js\"; foreach($span in @(@(1044,1062),@(1074,1091),@(1348,1370))){for($i=$span[0];$i -lt $span[1];$i++){ '{0}: {1}' -f ($i+1),$c[$i] }}; Get-Content -Encoding UTF8 \"$sdk/cordis/lib/types/context.d.ts\" | Select-Object -Skip 80 -First 22; Write-Output \"COMMAND_STARTED=$r2Started\"",
    "time_utc": "2026-10-18T12:14:23.8428672Z",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis-plugin-loader/lib/index.js",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis/lib/index.js",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis/lib/types/context.d.ts"
    ],
    "impact_write": [],
    "access": "read-only installed SDK; no host process/profile read/write"
  }
]
```

