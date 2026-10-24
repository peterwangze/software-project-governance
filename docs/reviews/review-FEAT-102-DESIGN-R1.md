# FEAT-102 — DSH 初始登记时序复审 R1

- 日期：2026-10-17（Asia/Shanghai）
- Reviewer：原独立 Design Reviewer；非 Producer，保持只读审查身份。
- 前轮：`docs/reviews/review-FEAT-102-DESIGN-R0.md`，SHA-256 `38365A746D7ECC4A6565EBD8DF491C2F022F928A002494C88999A602B015074E`；R0 仅准入 S-A，未批准产品接线。
- 修订输入：`docs/architecture/dsh-adapter-version-decoupling.md`，SHA-256 `00ACFECE5FC56FC47CB5A7ACEF1F17C0ABA22227699174BB25F85389229DFE2E`。
- S-A 报告：`docs/diagnostics/dsh-native-feasibility.md`，SHA-256 `52AACBE141E94F57BC7616D290483F723484511458FF37ECDD9904F518FF3CF5`。
- S-A 原型：`docs/prototypes/dsh-native-feasibility.mjs`，SHA-256 `ECE2CD8D1E019ABBD9758ED5D7D041757F1D92D8F88BF05E8DA21003C22BF177`。
- 绑定规范：design-reviewer 角色、design-review、tech-review；已重新加载。Coordinator 派发事实：expected-new 锁已取、enforcement re-review ALLOW。
- 写入权限：仅本新报告；无设计/产品/治理账本/旧报告修改，无宿主运行、安装、用户 profile 读写。

## 1. 结构化裁定

```text
conclusion=APPROVED_WITH_NOTES
unresolved_blockers=0
review_scope=R1时序修订及S-A2隔离证伪准入
implementation_authorized=false
feasibility_probe_authorized=true
authorized_slice=S-A2_ONLY
product_wiring_authorized=false
runtime_support=NOT_RUN
release_authorized=false
legacy_runtime=UNSUPPORTED_NO_AUTOWRITER
prior_s_a_timing=FAIL_POST_BOOT_PRESET_VISIBILITY
```

允许按修订 §5.1.4 执行 **S-A2_ONLY**，优先证伪 L。这是批准一项边界受控、可以失败的隔离试验，**没有认定 L 已解决循环等待或初始可见性**。已有 S-A 失败保持有效；M 不得凭 microtask fixture 成功成为产品默认方案；F 保持未验证备选。S-B～S-F、支持声明、发布、真实重装继续冻结，S-A2 成功后仍须独立复审明确解锁。

本范围无未解决的设计级阻塞：修订已经承认原方案不足，给出有公开源码依据的候选、明确可证伪前提和失败退出门。产品可行性尚未证明不能被本次“零阻塞”字段消除。若不能完成有效 base 审计或真实卸载收敛，应将候选判 FAIL 并返回复审，不能删减 BASE_BROKEN/首 lookup/卸载门以取得通过。

## 2. 前轮逐项对照

| R0 finding/义务 | R1 结论 | 可复查依据 |
|---|---|---|
| N01/BR-01：首个真实入口必须独立于自有 readiness | **原时序未修复；设计已正面修订，允许下一次证伪** | S-A 实际 setImmediate boot 后 lookup 失败；设计 §5.1.1 撤回宽泛“apply 返回后任务”，§5.1.2 明确 admitted/ready，§5.1.3 不把 M 成功提升为保证，A2-1/2 把首 lookup 设硬门。 |
| R0 S08/BR-01 的 headless 关联推断 | **更正并撤回本 Reviewer 的旧推断** | S-A 说明和原型使用真实 Web SessionController；当前 headless agents.create 不选择/挂载 preset。R1 不再拿 headless 创建结果证明 governance/default-governance。旧报告保留不改，以本勘正追溯。 |
| BR-02：root-await/登记飞行中卸载 | **S-A detached 模式的有限 fixture 已通过；L 模式未验证** | S-A 原型 apply 同步结束，清理可独立发生；L 改为 activation 持有 register Promise，Cordis dispose/activation 顺序已变化，原 PASS 不可继承。A2-4 必须重新实证。 |
| BR-03：accepted config、用户覆盖和表达式保真 | **有限 fixture 通过，产品范围未验证** | S-A 真实 Fiber.config、schema、深拷贝对照成立；设计 §4.1.5、A2-3 保留有效 Fiber 与 base registry audit 两个不同证据。不能只检验 schema 或 Fiber settled 后省略 broken。 |
| BR-04：register 正常返回但 broken | **有限 fixture 通过，L 链审计待证** | S-A broken-registration 负例无 READY、Web create invalid、最终无自有记录；registry 源码仍捕获 mount 错误。A2-5 必须保留负例，不能在自包含 activation 中 resolve/list。 |
| BR-05：热刷新 epoch/stale 安全 | **未执行；保持产品合入前硬门** | S-A 未声称刷新验收；修订 §5.2 保持原约束。本次不涉及产品刷新接线。 |
| BR-06：link 无 host deps/同一解析 context | **工具参数路径与真实模块已证明，完整 link 安装未验证** | 原型使用 manifest createRequire+真实 builtins，这是 harness 注入；设计 §8/§9 明确完整 link/current-web 未通过。不得把工具解析方法直接当产品解析方案。 |
| N02：旧 writer、单源正文、doctor 分面 | **legacy 裁定已纳入设计；产品未实施** | §6/§8/§11 明确 UNSUPPORTED_NO_AUTOWRITER，不再留“待定”自动路径。单源正文/doctor 仍由后续切片和 Code Review 验证。 |
| N03/N04：发布支持矩阵、用户卸载/发布后重装 | **保持** | 当前产品 runtime_support=NOT_RUN；其余 profile/UI/模型/工具/技能读取均未扩张支持。用户主动卸载状态不变。 |

## 3. 原始时序独立核对

原型调用的真实 `boot(...).then(...)` 后首先执行真实 registry list/resolve，没有先等待本插件 readiness。S-A 报告原始 JSON 中：

| 场景 | 关键原始事件 | 可以证明/不能证明 |
|---|---|---|
| actual-boot-microtask | seq6 register-start=15.432ms；seq7 actual-boot-return=17.140ms；seq8 register-complete=17.334ms；seq10 roster 可见 governance；seq13 first-create-complete | 在这个 fixture/调度下先入 record、后完成 mount；lookup可利用 record.ready。不是 Loader 对所有 continuation 的排序契约。 |
| actual-boot-immediate-default | seq4 boot-return=13.066ms；seq5 roster仅standard；seq6 resolve not-found=13.151ms；seq10 register-start=13.320ms；seq13 first-create-complete=15.981ms | **真实 boot 后可见性失败**。Web create 因其 mkdir 等待仍成功，没有观察到此自然路径的 session 创建失败。不得把 not-found 改成可接受 starting。 |
| admission barrier 三场景 | 真实 create 在额外 register 前 barrier 中 not-found | 证明该注入窗口没有宿主等待保证；不是原正常执行必然发生 barrier 的证据。 |

S-A 的 20 场景/38 schema/0 unhandled 仅属于已测真实宿主 fixture。schema 非零与清理负例是有效证据，不能抵销已测可见性失败。full current-web、完整 link 安装、HTTP/UI、实际 skill 读取、热刷新和原生工具参数完整性仍 NOT_RUN。本 Reviewer 未重新运行 S-A，也不把它冒充本轮运行。

## 4. 公开源码、候选与新风险

以下 N 根为 `C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai`；均本轮只读直接核查。

| ID | 锚点 | 独立判断 |
|---|---|---|
| R1-S01 | N/cordis-plugin-loader/lib/types/index.d.ts 的 Loader.Intercept.await：“Keep dependent plugins pending while loader entries are still loading”；N/cordis/lib/types/registry.d.ts:10–14 的 Inject 对象形态支持 service intercept config | L 有真实公开提案依据；不是虚构 Loader 参数。prototype 应记录实际使用的公开 inject 配置，不借私有 context/loader 字段实现 gate。 |
| R1-S02 | Loader lib/index.js:150–159 getTasks 返回 entry初始化任务或 Fiber.inertia，await 循环 Promise.allSettled；:647–649 check 在 await配置且getTasks非空时返回false；:438–448 entry init完成后仅在无tasks时notify loader | gate 不等于“全树与所有 PENDING 行已可用”；自己的 inertia、后续导入、嵌套组和通知顺序都可能影响 L。A2-1 的冷启动/前末/延迟/重复activation观察不可删。 |
| R1-S03 | Cordis lib/index.js:1306–1343 service check影响 _store/epoch；:1349–1368 _reload 等插件 effect 后才清 inertia/进入卸载；:1399–1402 Fiber.await 只等待当前 inertia并重抛错误 | L 可将注册纳入宿主 activation 等待，但 SOURCE 不证明 gate 无自失效。F 只等已有 Fiber，不保证尚未导入的 base 或唯一性，不能调用 Entry.init 主动启动宿主行补缺。 |
| R1-S04 | Registry lib/index.js:500–523 在await activate前同步写record；:540–543 错误变broken；:557–564 diagnostic遇pending回退 owner.loader.await | admitted与ready拆分合理；一旦在自己activation链调用这种audit，就可能等自己。base Fiber有效≠registry无broken，不能把未知点改成只检schema。 |
| R1-S05 | Cordis lib/index.js:1077–1089 dispose在有inertia时等待它；:1356 _reload等待插件effect；:1367进入_unload；:1373起才跑disposers | **新重点**：cleanup函数没有await startup，不代表框架会在startup结束前执行cleanup。简单“apply返回await register”在挂载未结束时可能阻止真实卸载。S-A detached模式的PASS完全不足以解此点。 |
| R1-S06 | N/dsh-api-session-controller/lib/index.js:358 composeAgent；:445 mkdir；:449 composeAgent；:686 public create | 与 S-A consumer/偶然mkdir等待的解释一致。不得继续把不消费preset的headless当首会话替身。 |

候选独立裁定：
- **M**：只作原 S-A 对照；当前无公开因果顺序证明，禁止以 microtask 约束或多跑几次fixture替代准入契约。
- **L**：可执行 S-A2 证伪，不是产品选定方案；重点为有效 base audit、own inertia/notify、实际卸载顺序。源码已支持风险存在，不支持假定它们已解决。
- **F**：保留未验证备选；仅等由宿主已启动的 base。缺树/缺 Fiber/不唯一即拒收，不能重排行、Entry.init 或创建隐藏宿主启动路径。
- 原 A/B/C/D 取舍维持 R0。若 L 失败，F/C 应回设计审查明确条件，不能在本次许可下偷偷替换产品方案。

## 5. 独立蓝军及 S-A2 必须遵守的观察方式

切换失败框架后的三项核心假设：H1=intercept释放后首次lookup一定受自己的activation约束；H2=有效base审计可以不反向等自身；H3=把register放入activation后仍可先完成卸载再处理迟到disposer。三项均未验证。

| ID/视角 | 攻击向量→后三步 | 影响 | 设计已有回应 | 本轮必要观察/残余风险 |
|---|---|---|---|---|
| R1-BR1 攻击者 | 延迟嵌套导入→intercept提前释放→树漏base/重复项→登记错误派生 | P1，错误接纳或not-found | A2-1前末/冷与预载/延迟/完整树门 | 必须事件屏障、公开fiber状态/inertia观察；记录实际进入activation次数。PENDING本身不能作全树可用证据；高/NOT_RUN。 |
| R1-BR2 维护者 | base子行pending→resolve触发root.await→root等own activation→自锁 | P1，宿主启动卡死 | §4.1.5、A2-3禁止自包含audit，不能删除broken拒收 | 需要有据标出audit所在阶段和因果链；若只能“先登记无效派生后异步撤回”，即FAIL，不能列通过；高/NOT_RUN。 |
| R1-BR3 愤怒用户 | mount未完成时卸载→Fiber.dispose等inertia→cleanup未开始→晚到记录残留/等待不返回 | P1，用户再次无法使用宿主 | A2-4已要求先cleanup后释放barrier；§5.3迟到disposer | 必须通过真实Fiber.dispose触发卸载，不能手动调用控制器cleanup替代；先记录卸载/cleanup完成，再释放mount barrier。若只能释放后卸载，判FAIL；高/NOT_RUN。 |
| R1-BR4 攻击者 | 让schema import/base audit在register前暂停→boot若已返回→首lookup not-found→新会话选择失败 | P1，已知race重现 | A2-2要求在唯一可疑异步点暂停并证明boot受门控制 | 不准测试先等READY；lookup参数先固定；不能依赖mkdir/I/O。有效mount-delay正例须独立证明registry.ready等待；高/NOT_RUN。 |
| R1-BR5 维护者 | 将broken负例变成成功返回→省略audit→记录READY→非法预设暴露 | P1，伪支持 | A2-3/5及既有broken-registration保留 | 注册失败不得READY；已登记仅自己可清理；ordinary standard前后不变；中/NOT_RUN。 |

最小澄清（非设计返工阻塞，直接属于已列 A2 门的执行判据）：A2-4 的“卸载”是宿主真实 Fiber.dispose/Loader unload，而非 harness 自己先调用 cleanup；因框架等inertia才cleanup，须同时记录 dispose-request、cleanup-start/complete、dispose-complete、mount-release、late-dispose。A2-3 不允许凭 Fiber settled 省略 base audit。两项任何失败都返回同 Reviewer，不能以“预期超时”算通过。

所有故意pending/循环反例使用repo sandbox、事件屏障及有界独立进程/失败收集；超时只可终止并报告失败。不得为“让cleanup成功”提前释放它应独立于的barrier，也不得把超时释放视作等待链证明。保存失败raw后停止候选扩展，不进入产品。

## 6. 六维度、硬门与后续权限

| 维度/硬门 | 裁定 |
|---|---|
| 方案完整性 | 原四候选保留；时序M/L/F三候选、先定标准及排除/待验证条件明确，PASS（仅探针准入）。 |
| 模块结构 | entry→lifecycle→source/overlay，source→publicLoader，lifecycle→registry，infra不反向入产品；静态模块环=0。动态等待环尚未证明消除，正是S-A2目标。 |
| 接口契约 | admitted/ready、base已接受config与无broken分开，raw事件和错误出口明确，PASS（试验计划）；不批准产品运行。 |
| 安全/非功能 | 无真实HOME写入/宿主修改/私有表/整套工具复制；普通base保全、拒收与诊断、限域失败收敛保留。性能成本仍一次扫描/串行重挂，初始因果链待证。 |
| ADR关键字段 | §12日期、背景、决策方向、备选排除、影响、风险、可逆与后续齐全，100%；仍Proposed，未冒充已发布。 |
| 独立Bar Raiser/蓝军 | 原Reviewer独立核对源码+两条raw，挑战5项并逐项绑定设计回应；未复用producer自批；PASS。 |
| 未授权范围 | S-B～F、正式Code/Release通过、支持声明及重装均未解锁；legacy仍UNSUPPORTED_NO_AUTOWRITER；FIX-444/445字节保全。 |
| 事实与写入 | SOURCE≠runtimePASS；S-A真实失败保留；只新写本报告，未重新运行宿主。 |

Coordinator 后续：机录 R1 范围化结论，派发最小 S-A2；完整返回 A2-1～5 原始事件、实际配置、模块路径、schema计数、卸载drain与失败证据。即使全部fixture通过，也须回同Reviewer确认源码因果契约及局限后另行授权，不能自行开始S-B。真实current-web/link/skills/refresh/tools与CI/0.99发布链底线维持R0。

## 附录：本轮外部只读命令逐条审计

时间为每条命令内当时打印的UTC，exit为exec结果；本轮没有外部运行、安装、真实profile访问或写入。读取private实现仅为审查公开行为，不授予产品调用private字段权限。

```json
[
  {
    "id": "R1-RO-01",
    "cmd": "$r1Started=[DateTime]::UtcNow.ToString('o'); $sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$sdk/cordis-plugin-loader/lib/types/index.d.ts\" | Select-Object -First 155; $l=Get-Content -Encoding UTF8 \"$sdk/cordis-plugin-loader/lib/index.js\"; for($i=142;$i -lt 160;$i++){ '{0}: {1}' -f ($i+1),$l[$i] }; rg -n -C 7 'Service.check|config.await|intercept|internal/status|getTasks\\(' \"$sdk/cordis-plugin-loader/lib/index.js\" | Select-Object -Last 140; Write-Output \"COMMAND_STARTED=$r1Started\"",
    "started": "2026-10-16T23:57:11.2236582Z",
    "exit_code": 0,
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis-plugin-loader/lib/types/index.d.ts",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis-plugin-loader/lib/index.js"
    ],
    "access": "read-only installed SDK; no host run; no writes"
  },
  {
    "id": "R1-RO-02",
    "cmd": "$r1Started=[DateTime]::UtcNow.ToString('o'); $sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n -C 5 '_checkImpl|_refresh\\(|async _reload|_reload\\(|async _unload|_unload\\(|async await\\(|inertia =' \"$sdk/cordis/lib/index.js\" | Select-Object -First 205; rg -n -C 3 'Intercept|InterceptConfig|interface Inject|type Inject|inject.*config|intercept' \"$sdk/cordis/lib/types/registry.d.ts\" \"$sdk/cordis/lib/types/context.d.ts\" \"$sdk/cordis/lib/types/service.d.ts\" | Select-Object -First 105; Write-Output \"COMMAND_STARTED=$r1Started\"",
    "started": "2026-10-16T23:57:24.2009083Z",
    "exit_code": 0,
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis/lib/index.js",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis/lib/types/registry.d.ts",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis/lib/types/context.d.ts",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis/lib/types/service.d.ts"
    ],
    "access": "read-only installed SDK; no host run; no writes"
  },
  {
    "id": "R1-RO-03",
    "cmd": "$r1Started=[DateTime]::UtcNow.ToString('o'); $sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; $c=Get-Content -Encoding UTF8 \"$sdk/cordis/lib/index.js\"; foreach($span in @(@(1059,1104),@(1118,1204),@(1348,1392))){for($i=$span[0];$i -lt $span[1];$i++){ '{0}: {1}' -f ($i+1),$c[$i] }}; $g=Get-Content -Encoding UTF8 \"$sdk/dsh-agent-preset-registry/lib/index.js\"; for($i=499;$i -lt 567;$i++){ '{0}: {1}' -f ($i+1),$g[$i] }; rg -n 'async create\\(|composeAgent|mkdir\\(' \"$sdk/dsh-api-session-controller/lib/index.js\" | Select-Object -Last 18; Write-Output \"COMMAND_STARTED=$r1Started\"",
    "started": "2026-10-16T23:58:10.2902655Z",
    "exit_code": 0,
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis/lib/index.js",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-agent-preset-registry/lib/index.js",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-api-session-controller/lib/index.js"
    ],
    "access": "read-only installed SDK; no host run; no writes"
  }
]
```

