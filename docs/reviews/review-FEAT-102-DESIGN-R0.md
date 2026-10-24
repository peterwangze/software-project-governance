# FEAT-102 — DSH 升级适配与依赖解耦设计审查 R0

- 日期：2026-10-16（Asia/Shanghai）
- Reviewer：独立 Design Reviewer Agent；非本设计 Producer，未修改产品或设计。
- 绑定规范：`agents/design-reviewer.md`、`skills/design-review/SKILL.md`、`skills/tech-review/SKILL.md`。本派发明确允许只读 exec 与仅写本报告，覆盖角色模板的默认工具/报告路径限制。
- 目标锚定：plan-tracker FEAT-102，0.99.0 当前首要事项；保持 Git CI 修复、版本收尾以及 FIX-444/445 暂停边界。
- 输入 A：`docs/research/dsh-0.2-upgrade-decoupling.md`，SHA-256 `D3AF368070751685B81D237BEAA161FEDADD842B25988F0228DB6C0E5D32C27F`。
- 输入 B：`docs/architecture/dsh-adapter-version-decoupling.md`，SHA-256 `B2288E95DD677ADFF80B7AFFCC6D6190A6871EC1CF4B49721D01B391659CFD3A`。
- 前轮：无。Coordinator 派发事实：Producer 已结束、锁已释放；本报告 expected-new 锁及 enforcement-check ALLOW；Reviewer 不另改治理账本。

## 1. 结构化裁定与授权边界

```text
conclusion=APPROVED_WITH_NOTES
unresolved_blockers=0
review_scope=方案B架构方向及S-A隔离可行性准入
implementation_authorized=false
feasibility_probe_authorized=true
authorized_slice=S-A_ONLY
product_wiring_authorized=false
runtime_support=NOT_RUN
release_authorized=false
legacy_runtime=UNSUPPORTED_NO_AUTOWRITER
```

推荐 B 的最小公开边界有源码支持，可以执行设计 §8 的 **S-A 最小隔离可行性探针**。本次通过不批准 S-B～S-F 产品接线、广泛重构、支持声明、发布或真实重装。S-A 是可证伪的试验，成功必须带回原始时序/挂载/清理证据，由 Coordinator 核实后解锁下一切片；失败必须返回设计复审。不得先铺开实现再把关键时序失败降为已知问题。

该限定没有未解决的设计级 BLOCKING finding：设计 §5.1/§8 已将入口 readiness 设为先行硬门，并规定失败退回。当前重要前提仍是 NOT_RUN，不能把本报告解释为 B 已运行可行。报告中的待验收门不属于“允许带病发布”的备注。

旧模型裁定：**本次新交付的运行入口对无 native 能力的宿主明确 UNSUPPORTED，不自动调用旧 HOME writer**。旧 renderer/fixtures 可作为离线历史检验材料保留；必须从普通 apply、install/repair/update 自动路径隔离，不以 retained/NOT_RUN 作为继续自动写用户目录的许可。设计 §6 已把此选择交给 Reviewer；这是选择已列明的保守拒收分支，不要求 Architect 先扩大旧版运行适配。后续要恢复 legacy 自动运行须另作安全设计、隔离验证和审查。

## 2. 可复查事实与独立结论

下列 `N` 均为 `C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai`；`R` 为本仓库。安装态只读 SOURCE 与运行态证据严格分开。

| ID | 直接核查事实 | 对设计的意义 |
|---|---|---|
| S01 | N/cordis-plugin-loader/lib/types/config/tree.d.ts 公布 entries/await/import；lib/index.js:142–159 递归 subtree，等待 entry init/inertia；:214–225 的 import 使用树的 baseUrl | B 使用公开能力；禁止把 root-await 放回自身 activation/cleanup 的依赖链有依据。 |
| S02 | N/cordis-plugin-loader/lib/types/config/entry.d.ts 公布 fiber/disabled/parent；N/cordis/lib/types/fiber.d.ts 将 config 明定为 validated config | 读取 fiber.config 比 raw options.config 有明确语义；禁止 private _config/_error/definitions 合理。 |
| S03 | N/dsh-agent-preset/lib/index.js:8–25 使用 EntryGroup.key、plugins:z.array(z.any())，register；Loader lib/index.js:607–611 对该 marker 保留表达式 | 公开有效 declaration 可以保存子行未求值表达式；SOURCE 仍不等于 profile override 运行保真。 |
| S04 | N/cordis-plugin-include/lib/index.js:15–20：!!js 构造结果就是普通 `{__jsExpr:data}`；Loader lib/index.js:239–247 用该属性判断 | structuredClone 当前形态可保留；不存在已证实的“JSExpr 类原型必丢失”阻塞。仍须测试深层 groups、disabled、非法/循环值拒收。 |
| S05 | N/dsh-agent-preset-registry/lib/index.js:500–523 重复 ID 拒绝、登记即生成 record、返回 disposer；:525–543 把 mount 错误转为 record.broken；:557–567 pending audit 会等 root Loader | register 正常返回不能判 READY；root settle 后 resolve 无 broken 与实际 compose 缺一不可。不得读私有表。 |
| S06 | 同文件 :639–655 retain 对尚未登记的 ID 立即抛 not-found，对 broken 抛 invalid；:693–696 mount 先 retain；:569–572 退休 revision 在无用户后 collect | 初始登记时序影响真实 Agent 创建；旧会话 revision 保留应交宿主处理，不手工重置。 |
| S07 | N/dsh-app-boot/lib/types/index.d.ts:31–34 公开 app-boot/config-reload；lib/index.js:3484–3494 在更新、Loader settle、失败检查后 emit | 当前宿主确有公开刷新事件；不是虚构生命周期 hook。串行/epoch 仍需实证，未知宿主不可据 ctx.on 存在就宣称事件会触发。 |
| S08 | N/dsh-app-boot/lib/index.js:4080–4087 boot 等 Loader 后审计并返回；N/dsh-headless/lib/index.js:293–321 的后台 run 只等 Loader，随后 agents.create；:355–369 apply 同步启动 run | 自有 readiness 不自动进入宿主入口契约。T11 是 S-A 首要证伪点，不能只在测试里先 await 自有 readiness 后创建 Agent。 |
| S09 | N/dsh-web-app/presets/standard.patch.yml 当前 persona prefix/suffix、Windows disabled !!js、planning/compaction/delegation group、workflow-ptc、goal/present 都在 base 声明；persona schema N/dsh-persona/lib/index.js:23–27；skill schema N/dsh-skill-filesystem/lib/index.js:31–39，路径解析 :79 | 继承整树只追加 prefix/两个 roots 符合实际接口；静态搬全套工具会继续背离宿主配置。包根必须绝对定位；其它 persona/skill 字段须保留。 |
| S10 | R/.governance/dsh-02-baseline-compat.log：正确 CLI0.2，四 oracle unknown，外层 createRequire anchor 找不到 js-yaml，Result NOT_RUN，零 schema-checked rows | CLI manifest anchoring 修正有实证必要性；不能把原 exit0 或目录残留当 schema/runtime PASS。 |
| S11 | R/lib/index.js:490 仅比较本包版本；:549 对 userDir recursive rmSync；:605–606 apply 无条件 ensurePreset；R/package.json 无 host deps 且 private=true | 版本 marker 和旧 writer 是确实存在的耦合/安全面；旧自动 writer 不获本轮运行许可。link realpath 无 host deps 必测；发布后安装 spec 不能假定 npm 版本。 |

未启动 DSH、未执行安装、未调用 loadProfile、未读取或修改真实 profile。没有以真实用户 HOME 做故障场景。外部安装态 SOURCE 读取逐条记录见附录。

## 3. 六维度审查与候选方案

| 维度 | 结论 | 依据及限制 |
|---|---|---|
| 方案完整性/选型 | PASS（S-A 准入） | 设计 §2 在候选前定义安全→可运行→公开扩展→覆盖保真等标准；四候选都有具体代价。A 可作一次迁移但不消除工具副本，C 是合法备选但多解析/运行态一致性面，D 破坏预设隔离；B 不靠不存在的 extends。 |
| 合理性/模块结构 | PASS | §3.1 entry/lifecycle/source/overlay 职责分离，source 只读、overlay 纯函数、lifecycle 独占 disposer；没有由 infra 反向进入产品运行时的依赖。 |
| 接口契约/数据流 | PASS（有限 shape） | §4 定义 BaseSnapshot/OwnPolicy/DerivedDefinition/RuntimeOutcome 与错误码；接受有效 tree→克隆→两个差量→register→resolve/compose。动态 prefix/roots、重复 provider、未知 tree、broken 都拒收本包。 |
| 安全/非功能 | PASS（设计措施） | native 零 HOME 写入、只处置自己的 disposer、无 profile repair、无他人 ID 覆盖；保留 disabled/权限；超时、串行、fingerprint、epoch、迟到 disposer 各有设计。实际满足程度仍待 S-A/实现验收。 |
| 可演进/技术债 | PASS_WITH_NOTES | host 工具和未知字段由当前 base 承担，支持按能力判定；仍依赖 Loader+registry 的公开组合契约，未来 breaking shape 明确拒收。旧版本自动 writer 本报告裁为 UNSUPPORTED，不能继续借 legacy 保留安全债。 |
| 独立 Bar Raiser | 已执行 | 本 Reviewer 非 Producer，已独立检索 S01～S11，并以攻击者、愤怒用户、维护者视角挑战下述假设；未复用 Architect 自批结论。通过仅限 S-A，不为进度解除发布门。 |

依赖 DAG：`entry → lifecycle → {source, overlay}`；`source → public Loader`；`lifecycle → registry`；`overlay → own policy/contract`；`infra → own protocol/fixtures`。模块循环数=0；宿主不反向依赖本插件；顶层不裸 import 宿主模块。必要 schema import 只能经所选树公开 import，保持同一 resolution context。

ADR 字段核对：设计 §12 包含日期、背景、推荐决策、三个备选及排除理由、影响范围、后果/风险、可逆性、后续动作；完整率=100%。它仍是 Proposed ADR，Coordinator 机录后才成为正式决策，不伪造已有批准。

非功能映射：安全→零 HOME/native 保真/自有 disposer；可用性→仅自家 unsupported/failed 与普通 DSH 保持可用；性能→settled 一次扫描+合并刷新+fingerprint；维护→两个自有差量+单源 persona+有限能力协议；观测→四态证据与明确 reasonCode；测试→纯函数负例+真实 Cordis 隔离 mount。没有数据持久化/新增认证面，不扩展为无关合规改造。

## 4. 独立蓝军与非阻塞备注

框架切换：审查“最可能失败之处”，核心假设为 H1=宿主入口不会早于自有 readiness 创建 governance Agent；H2=accepted declaration 与派生配置保真；H3=卸载/刷新不会留下自己的迟到登记。上述假设当前均不视作实测成立。

| ID/视角 | 攻击向量与后续三步 | 影响评估 | 设计方既有回应/缓解 | 残余风险及必须观察 |
|---|---|---|---|---|
| BR-01 愤怒用户 | 使 register 延迟；headless 等 root 完成；在 governance 尚未登记时 agents.create/选预设 | 当前0.2适配入口失败，P1 | §5.1、T10/T11 规定 readiness 门、失败退回设计，不靠 sleep | 高，NOT_RUN。必须在真实入口等效的宿主链竞争创建，不接受测试人为先等 readiness；没有可靠公开接线则回 Reviewer。 |
| BR-02 攻击者 | root.await 尚未结束时卸载；cleanup 若等待启动则自锁；register 晚到则幽灵 preset | 宿主卸载卡死或预设残留，P1 | §5.3 先 stopped/remove listener、不 await root启动任务、晚到 disposer 立即清理、消费 rejection | 高，NOT_RUN。T13 必须以 drain 观察无残留注册/监听、无 rejection；非自己 ID 不准删除。 |
| BR-03 维护者 | profile 修改 standard 安全开关/roots/prefix；raw 更新失败；adapter 若读 raw 或回退默认则安全策略复活 | 用户覆盖丢失、工具越权，P1 | §4.1 validated Fiber.config+base audit；§4.2 两差量保真；失败 shape 拒收 | 中，NOT_RUN。T05/T06/T08/T09 对有效配置和原树快照比较；!!js 只克隆、不提前执行。 |
| BR-04 攻击者 | registry mount 缺包；activate 捕获错误；register 返回正常 disposer | 伪 READY、首会话失败，P1 | §4.2/§5.1 resolve无broken+compose，S05直接支持 | 中，NOT_RUN。必须有返回成功但 broken 的负例并保证 failed 时撤回自有声明。 |
| BR-05 维护者 | 连发 reload 删除 base；旧 reconcile 后完成；晚到旧策略重新登记 | 已撤回安全策略回流，P1 | §5.2 串行/epoch、只退休自己generation、缺base撤回 | 中，NOT_RUN。当前 event 存在已确认；T12证实最后有效配置获胜、不保留 stale 新会话策略。 |
| BR-06 愤怒用户 | 链接包无 host deps；Node按repo realpath解析；错误回退老缓存“能运行” | 两套宿主配置混用、升级再失效，P1 | §3/§7.1 不裸import；CLI/profile单context，记录oracle路径 | 中，NOT_RUN。T01/T02真实nested+flat/pnpm fixture；缺能力明确NOT_RUN，不能伪造same-plane。 |

保留备注/责任与截止：
- N01（Coordinator/Developer，S-A 结束前）：提交 BR-01/02/04 的最小真实宿主证据；失败走设计复审。未关闭前不解锁 S-B。
- N02（Developer/Code Reviewer，产品合入前）：落实 legacy UNSUPPORTED 自动入口裁定、单源正文、probe/doctor 分面、表达式/覆盖/刷新负例；报告不替代代码审查。
- N03（Coordinator/Release Reviewer，发布前）：固定支持矩阵 current-web/0.2.0-rc.2；其它 profile/旧版/真人工具未跑项披露。未来版本只按能力尝试，不承诺全兼容，不新增固定宿主 runtime 副本或用 `*` peer 声明全部未来兼容。
- N04（Coordinator，发布成功后）：按照用户“发布后才重装”的边界交付精确 artifact/ref 的重装路径；真实环境写入遵守 R1，不能将本审查当自动重装授权。

这些是设计已列硬门的执行义务及 Reviewer 的 legacy 分支裁定，不是允许跳过的潜在建议。

## 5. S-A 准入与发布底线

S-A 可做：临时 sandbox DSH_HOME、临时 profile/harness、最小自有 source/overlay/lifecycle 试验文件与测试；消费已安装宿主源码/公开模块；保全仓库无 host node_modules 的 link 场景。禁止真实注册/重装/修 profile，禁止替换全量产品入口或扩展到其它0.99任务。

S-A 最低返回材料：
1. 当前0.2真实 Cordis/registry 下 source→register→resolve无broken→Agent compose→dispose 证据；schema checked数非零。
2. 同步记录 root settled、own apply返回、register开始/完成、入口尝试创建Agent、READY/failed/cleanup时间；至少包含当前row前/末、root延迟、register延迟、初始显式governance/default-governance与普通standard对照。不能用固定 sleep 或测试专用 readiness 等待替代生产入口保证。
3. root-await中卸载与register飞行中卸载两个竞态；drain后无自有登记/监听/未处理rejection；没有清理他人记录。
4. 原base/custom overrides/!!js保持、策略差量只有正文与两个roots；记录所选CLI/profile解析context及真实路径。
5. 运行失败与支持不足如实返回；若入口无法保证可用，返回设计复审并讨论公开同步登记接线或候选C，禁止以延长sleep“修复”。公开 Fiber.await() 可能支持仅等待宿主已经启动的 base fiber，但本轮未验证，不作为通过依据；Entry.init() 会启动宿主行，不得无条件用作“只读等待”或代替宿主装载调度。

发布底线高于 S-A：设计 §9 的当前native/T01～T20适用用例覆盖并说明未跑项；安装态schema+真实挂载、普通预设不变、skills/shims实际可读、tools配置/参数schema保真、refresh/dispose负例、nested探针修复、旧模型明确拒收、独立 Code Review、原CI四门及0.99标准发布链。真实模型/真人/UI交互如无法在隔离harness完成必须NOT_RUN披露，不能补填PASS；不能宣称所有profile、任意自定义树或所有未来DSH都兼容。保持 FIX-444/445 暂停/WIP字节不变。

## 6. 硬门槛与自检

| 硬门 | 结果 |
|---|---|
| 候选≥2 | 4，PASS |
| ADR 关键字段100% | PASS（Proposed，不冒充已机录决策） |
| ≥3独立蓝军及设计回应 | 6，PASS；回应来自设计既有段落，非虚构新增作者答复 |
| 模块无环 | 0，PASS |
| 独立Bar Raiser | 已执行，PASS |
| 关键前提事实分级 | SOURCE与NOT_RUN分开，PASS；只允许先行S-A |
| 写入范围 | 仅本报告；无设计、产品、.governance、用户环境写入 |
| 宿主操作 | 只读源码；未启动/安装/真实profile测试；命令exit1查询不用于兼容结论 |

## 附录：外部只读命令逐条上报

所有记录 started 为真实调用时采集的 UTC。影响路径是读取来源，不表示写入。R0-RO-07 末尾候选包路径有不存在项（dsh-cmd、dsh-session-agent、dsh-headless-app），exit1；R0-RO-09 末尾 rg 未匹配，exit1。后续 R0-RO-08/09 按实际 dsh-headless 路径取得源码，不从猜测路径推导缺包事实。

```json
[
  {
    "id": "R0-RO-01",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis-plugin-loader/lib/types/config/tree.d.ts",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis-plugin-loader/lib/types/config/entry.d.ts",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis/lib/types/fiber.d.ts"
    ],
    "cmd": "$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/cordis-plugin-loader/lib/types/config/tree.d.ts\"; Get-Content -Encoding UTF8 \"$p/cordis-plugin-loader/lib/types/config/entry.d.ts\"; Get-Content -Encoding UTF8 \"$p/cordis/lib/types/fiber.d.ts\"",
    "started": "2026-10-16T15:40:29.728Z",
    "exit_code": 0,
    "access": "read-only; no writes; no host started"
  },
  {
    "id": "R0-RO-02",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-agent-preset/lib/index.js",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-agent-preset-registry/lib/types/index.d.ts",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-agent-preset-registry/lib/types/definition.d.ts"
    ],
    "cmd": "$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/dsh-agent-preset/lib/index.js\"; Get-Content -Encoding UTF8 \"$p/dsh-agent-preset-registry/lib/types/index.d.ts\"; Get-Content -Encoding UTF8 \"$p/dsh-agent-preset-registry/lib/types/definition.d.ts\"",
    "started": "2026-10-16T15:40:30.166Z",
    "exit_code": 0,
    "access": "read-only; no writes; no host started"
  },
  {
    "id": "R0-RO-03",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-app-boot/lib/types/index.d.ts",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-app-boot/lib/index.js"
    ],
    "cmd": "$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/dsh-app-boot/lib/types/index.d.ts\"; rg -n -C 5 'config-reload|root\\.await|loader\\.await|composeEntries|readProfilePatches' \"$p/dsh-app-boot/lib/index.js\"",
    "started": "2026-10-16T15:40:30.597Z",
    "exit_code": 0,
    "access": "read-only; no writes; no host started"
  },
  {
    "id": "R0-RO-04",
    "cmd": "$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; $s=Get-Content -Encoding UTF8 \"$p/dsh-agent-preset-registry/lib/index.js\"; for($i=478;$i -lt 620;$i++){ '{0}: {1}' -f ($i+1), $s[$i] }; rg -n -C 3 'async mount|async select|defaultId|AgentFactory|agentPreset' \"$p/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Last 90",
    "started": "2026-10-16T15:40:47.610Z",
    "exit_code": 0,
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-agent-preset-registry/lib/index.js"
    ],
    "access": "read-only; no writes; no host started"
  },
  {
    "id": "R0-RO-05",
    "cmd": "$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; $s=Get-Content -Encoding UTF8 \"$p/cordis-plugin-loader/lib/index.js\"; for($i=128;$i -lt 225;$i++){ '{0}: {1}' -f ($i+1), $s[$i] }; rg -n -C 4 'JSExpr|__jsExpr|EntryGroup.key|disabledOf|_commitVolatile' \"$p/cordis-plugin-loader/lib/index.js\" | Select-Object -First 130; rg -n -C 3 'config-reload' \"$p/dsh-app-boot/lib/types/index.d.ts\"",
    "started": "2026-10-16T15:41:16.922Z",
    "exit_code": 0,
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis-plugin-loader/lib/index.js",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-app-boot/lib/types/index.d.ts"
    ],
    "access": "read-only; no writes; no host started"
  },
  {
    "id": "R0-RO-06",
    "cmd": "$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n -C 3 '__jsExpr|JS_EXPR|JSExpr' \"$p/cordis-plugin-include/lib/index.js\" | Select-Object -First 90; Get-Content -Encoding UTF8 \"$p/dsh-web-app/presets/standard.patch.yml\" | Select-Object -First 145; rg -n -C 3 'prefix:|suffix:|complete:|includeRuntimeContext|customSkillDirs|includeDefaultRoots' \"$p/dsh-persona/lib/index.js\" \"$p/dsh-skill-filesystem/lib/index.js\" | Select-Object -First 95; rg -n 'async function boot|loader.*await|auditStartupEntries' \"$p/dsh-app-boot/lib/index.js\" | Select-Object -Last 16",
    "started": "2026-10-16T15:41:30.637Z",
    "exit_code": 0,
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis-plugin-include/lib/index.js",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-web-app/presets/standard.patch.yml",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-persona/lib/index.js",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-skill-filesystem/lib/index.js",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-app-boot/lib/index.js"
    ],
    "access": "read-only; no writes; no host started"
  },
  {
    "id": "R0-RO-07",
    "cmd": "$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg --files \"$p\" -g '*headless*' -g '*acp*' -g '*session*' -g '*bin*' | Select-Object -First 45; rg -n 'headless|agentPresets\\.mount|agentPresets\\.resolve|agentPreset:|agentFactory\\.create|\\.agents\\.create' \"$p/dsh-cmd\" \"$p/dsh-cmdline\" \"$p/dsh-web-app/lib\" \"$p/dsh-acp-app/lib\" \"$p/dsh-session-agent/lib\" \"$p/dsh-headless-app/lib\"",
    "started": "2026-10-16T15:41:58.480Z",
    "exit_code": 1,
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only; no writes; no host started; some guessed package paths missing; errors are discovery only"
  },
  {
    "id": "R0-RO-08",
    "cmd": "$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg --files \"$p\" -g 'package.json' -g 'index.js' -g 'main.js' | Select-String 'dsh-(headless|cmdline|acp-app|web-app)' | Select-Object -First 25; rg -n -C 4 'boot\\(|agentPresets|agentPreset|createAgent|\\.create\\(' \"$p/dsh-headless/lib/index.js\" \"$p/dsh-acp-app/lib/index.js\" \"$p/dsh-web-app/lib/index.js\" | Select-Object -First 110; $s=Get-Content -Encoding UTF8 \"$p/dsh-app-boot/lib/index.js\"; for($i=4072;$i -lt 4094;$i++){ '{0}: {1}' -f ($i+1), $s[$i] }",
    "started": "2026-10-16T15:42:12.619Z",
    "exit_code": 0,
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only; no writes; no host started"
  },
  {
    "id": "R0-RO-09",
    "cmd": "$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n '^async function|^function|^const inject|^const apply|^class|Service.init|start\\(' \"$p/dsh-headless/lib/index.js\" | Select-Object -Last 30; $s=Get-Content -Encoding UTF8 \"$p/dsh-headless/lib/index.js\"; for($i=250;$i -lt 339;$i++){ '{0}: {1}' -f ($i+1), $s[$i] }; Get-Content -Encoding UTF8 \"$p/dsh-headless/lib/index.js\" | Select-Object -Last 65; rg -n -C 4 'headless|runHeadless|\\.run\\(' \"$p/dsh-cmdline/lib/index.js\" | Select-Object -Last 90",
    "started": "2026-10-16T15:42:24.051Z",
    "exit_code": 1,
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-headless/lib/index.js",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/dsh-cmdline/lib/index.js"
    ],
    "access": "read-only; no writes; no host started"
  }
]
```

