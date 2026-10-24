# FEAT-102：DSH 0.2 升级断点与解耦事实调研

- 日期：2026-10-16（Asia/Shanghai）
- 角色：Architect；状态：设计输入完成，运行态验收待 Developer 隔离验证。
- 目标：先适配当前 DSH，再消除每次升级都需复制、改写整套工具配置的耦合。
- 范围：仅调研和报告；未启动 DSH，未安装、恢复登记、修改用户 profile 或已安装包。
- 用户澄清（Coordinator 转述）：用户主动卸载本插件以保证 DSH 可用；要求适配并发布后再重装。登记缺失是预期状态，不能用作“升级丢注册”的根因证据。

## 1. 可复查源与证据等级

本报告的源码锚点采用以下绝对根目录：

- `H = C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh`
- `N = H/node_modules/@deepseek-ai`
- `O = C:/Users/peter/AppData/Local/npm-cache/_npx/1e7f6d9597241db0/node_modules/@deepseek-ai`
- `R = D:/AI/agent/claude/coding/project_management_workflow`

等级：**SOURCE** = 安装态源码、类型或 manifest 直接支持；**RECORDED** = 既有 factsheet/Coordinator 诊断记录；**INFERENCE** = 源码链推导；**NOT_RUN** = 未运行验证。SOURCE 不等于真实会话 E2E 通过。

| 事实 | 证据/锚点 | 等级 |
|---|---|---|
| 当前 CLI 0.2.0-rc.2 | H/package.json:4；bin 指向 lib/bin.js | SOURCE |
| 当前主要 DSH 接口包均 0.2.0-rc.2 | N/{dsh-agent-preset,dsh-agent-preset-registry,dsh-app-boot,dsh-persona,dsh-skill-filesystem,dsh-tool-goal,dsh-tool-subagent,dsh-tool-ask-user,dsh-workflow-ptc}/package.json | SOURCE |
| Loader/Include 实际安装版本为 1.0.6/1.0.10 | N/cordis-plugin-loader/package.json、N/cordis-plugin-include/package.json；不能把 CLI manifest 的 ~1.0.5/~1.0.9 当实测版本 | SOURCE |
| 项目 adapter 的历史事实表记 0.1.5-rc.1 | R/adapters/dsh/fixtures/host-facts-0.1.5-rc.1.json:3；captured_at=2026-09-13T05:50:50+00:00 | RECORDED |
| 该历史表记录的缓存路径如今已是 0.1.5-rc.3 | O/dsh/package.json:4 | SOURCE |
| 契约 evidence.dsh_cli_version/verified_on/compat_range 仍为 null | R/adapters/dsh/host-contract.json，evidence 对象；null 必须解释为未记录 | SOURCE |
| 用户卸载后旧 preset 目录仍残留 | R/.governance/dsh-02-initial-offline.json，S1；Coordinator 提供，当前 Architect 未读用户目录内容 | RECORDED |

历史 factsheet 是当时的证据；缓存路径可变，不能据路径存在宣称复验了 0.1.5-rc.1。本轮没有捕获“rc.1 与 rc.2”的完整 API diff；下文区分当前确证接口和已知旧模型，不为版本变更时间编造结论。

关键安装态文件 SHA-256（2026-10-16T15:24:36Z 读取）：

| N 下相对路径 | SHA-256 |
|---|---|
| dsh-web-app/presets/standard.patch.yml | 6CD2F197737FC94A45E487D0BB57869461DD6F392D45F6429B576E75D973EDA8 |
| dsh-agent-preset/lib/index.js | 23CD2DD62AC3B27522A2D377E14B5A93F80C2189E733937DCDD02B73A6D3D1DA |
| dsh-agent-preset-registry/lib/index.js | ED62D573B8CC6D7ED3E3CB7932DBF5E237F5A603B3CC9D9E586187DB00E821CC |
| dsh-app-boot/lib/index.js | 234DB45E1B3F8C683B5BC1F551948B2A2EC52A6468C7B6937725A23F1C0E0D96 |

## 2. 四类失效链，必须分别诊断

| 类别 | 当前证据 | 失效机制与结论 |
|---|---|---|
| 宿主升级/接口变化 | 0.2 的 registry 明确不扫描目录；旧安装存在 dsh-agent-presets 目录模型；当前无 dsh-agent-presets、无 dsh-workflow-worker-thread | 原交付写入 .agent-presets 的目录模型与当前宿主脱节。旧模板还引用缺失 workflow 包。是需要实现适配的确定性断点。 |
| profile 登记变化 | web profile 中缺本插件（Coordinator 事实）；用户明确说已主动卸载 | 属用户意图，不是事故。不得自动补登记，适配与发布前不重装。 |
| 插件版本刷新 | R/lib/index.js:490 仅比较插件版本；:549 删除原目标再 rename | 插件版本相同便忽略宿主变化、模板变化和包路径变化。原路径渲染还会改写用户目录；本次新模型应消除此自动写入面。 |
| 包路径/安装平面变化 | 旧模板渲染绝对路径，skill-root.txt 也写绝对包根；旧 factsheet 缓存目录内容已漂移 | 同版本重装/迁移 npm 或 pnpm 路径后，旧绝对路径可能失效而版本 marker 仍一致。需由当前加载模块的 import.meta.url 定位包根；诊断必须跟实际 CLI/Profile 解析平面。 |

不能把“重新安装便可看到包名”当作接口兼容或解耦完成。当前原实现即使 bundle 已登记，仍只执行 `apply → ensurePreset → 写目录`；0.2 不扫描该目录，因此无法产生新的 governance 声明（INFERENCE，尚未启动验证）。旧残留文件存在也不能证明新版加载成功。

## 3. 当前宿主的真实接入 API

### 3.1 插件/bundle/解析平面

- R/package.json 声明 `dsh.bundle.patch = ./cordis.patch.yml`；R/cordis.patch.yml 只 insert 本包一行。0.2 仍支持 bundle patch，可为字符串或文件数组；N/dsh-web-app/package.json 的 bundle.patch 数组包含主 patch 和四个 preset patch。
- H/lib/bin.js:105、117 支持 `dsh plugin --profile <name> add <package>`、`--dump-config`、`--dump-config-schema`。
- N/dsh-app-boot/lib/index.js:897 附近 `resolveBundleDir` 按 installAnchor 优先、profileDir 次之解析；:912 `loadProfileDirectory` 可读取已初始化 profile；:970 `loadProfile` **会初始化、规范化并移除旧 link projections**，不能作为只读探测入口。
- N/dsh-app-boot/lib/types/index.d.ts:13/37 公开导出 `readProfilePatches`、`composeEntries`。前者按 bundle → profile → home → argv overlays 顺序读取脱离原对象的 patch；源码 :1023，内部用 loadProfileDirectory，不更新 Loader。
- `ProfileContext` 公开提供 name、dir、patchPath、installAnchor、cwd、home、startedBundles、overlays 等；见 N/dsh-app-boot/lib/types/profile-context.d.ts。
- 0.2 宿主读取插件 `peerDependencies` 中 `@deepseek-ai/dsh` / `@deepseek-ai/dsh-*` 范围，并以当前 runtime 版本判断；prerelease 参加范围。没有 peer 不等于兼容通过；optional peer 的免检语义不应臆测。N/dsh-app-boot/lib/index.js:285-322、类型 plugin-compatibility.d.ts。
- 当前项目无 dsh peer 范围，因此未发现“精准版本 peer 拦截了当前插件”的证据。新增适配不得靠 allow-version/accept-risk 绕门。

### 3.2 预设：目录模型已退休

旧 O/dsh-agent-presets/lib/types/index.d.ts 包含 roots、authorable、read、copy、remove、readDocument、mount、composeFrom；其职责含文件发现和目录复制。

新模型：

- N/dsh-agent-preset/lib/index.js:8-25：`inject=['agentPresets']`；声明 `Config={id,name?,description?,order?,plugins[]}`，以 `ctx.agentPresets.register(config)` 登记并持有 disposer。
- N/dsh-agent-preset-registry/lib/types/definition.d.ts：`PresetDefinition` 没有 `extends`、preset path 或目录字段。不能虚构原生继承功能。
- N/dsh-agent-preset-registry/README.md:46：registry 不扫描目录、不接受 preset paths；声明是普通 Cordis row。
- registry 公共方法：register、list、resolve、readDocument、mount、composeFrom、composedPreset、serviceFor、recompose、select、acquireScope、compositionInventory。register 返回异步 disposer；重复 id 拒绝。旧 revision 在仍有 Agent 引用时保留。
- N/dsh-agent-preset-registry/lib/index.js:499-543：register 的 mount 失败被转成 record.broken，**Promise 正常返回 disposer 也不代表已可用**。需在 Loader 已 settled 后检查 resolve/list 的 broken，并实际 compose 验证。
- :551-568 diagnostic 遇 pending 会 await root Loader；在自己的 host row 激活期间调用 list/resolve 可能自等待。启动期不得靠这些方法等自己完成。
- :621 readDocument 返回当前 plugins 的 YAML 文本（entryListSchema 保留 !!js），不接受写回；读 base definition 有登记时序问题，不能把异步 registry 私有 definitions 当继承 API。
- N/dsh-web-app/cordis.patch.yml:558-566 挂 registry；`presets/standard.patch.yml` 是普通声明。新 UI 是声明 roster，没有证据支持旧“删除目录/打开目录”交互仍适用。

### 3.3 persona 与 skill：可收窄到两个自有差量

- N/dsh-persona/lib/types/index.d.ts、lib/index.js：必填 prefix，另有 suffix、complete、includeRuntimeContext；属于 preset scope，不能挂全局以免与部署 persona 冲突。
- N/dsh-skill-filesystem/lib/types/index.d.ts：customSkillDirs、providerName、includeDefaultRoots、dshHome、agentsHome、watch 等。lib/index.js:79 仍将 customSkillDirs 经 path.resolve；包根需绝对路径。
- 在现有 skill-filesystem row 的副本上追加、去重两项包内根，比额外注册同名 filesystem provider 更安全。必须保留用户自定义 roots 和 includeDefaultRoots，不对非 governance 预设注入。
- shared skills/、commands/、agents/ 继续单源；skill-shims 保留命令投影。该内容与宿主工具行不应该捆绑复制。

### 3.4 goal、subagent、ask-user

| 能力 | 当前真实接口 | 本次处理边界 |
|---|---|---|
| goal | dsh-tool-goal Config.blockedAfterConsecutiveRounds 默认 3；create_goal(objective,max_goal_rounds?)；update_goal(goal_id,revision,action,objective?,max_goal_rounds?,blocked_reason?)。action 含 edit/pause/resume/complete/blocked；有真人输入/自动轮授权校验、过早 blocked 拒绝 | 记录接口，不把本项目预算直接投影成 token_budget；未发现 repo 在当前 DSH 路径硬编码旧工具参数。旧 rc.3 已有这些字段，不能称 0.2 新增。项目 goal_bridge 本地检查点与原生 goal id/revision 是两个域。 |
| subagent | dsh-tool-subagent Config.provider 必填；toolName、backgroundMode(one-shot/continuable)、maxDepth 等；continuable 需 provider.prepareContinuable；旧 provider 名由宿主承担 | 原样继承当前 standard，保留 modelSelectionSettings 和 disabled 状态，不复制或自行替换后端。真实子代理继承需隔离验收。 |
| ask-user | Config.mode=legacy/timed，timeout；默认 legacy；问题 id/question/options/multi_select；结果 answers[]；timed 可返回 pending/callId/message | 继承宿主选择；pending 不是回答或授权。不可为了适配把全宿主改 timed。 |

源码锚点：N/dsh-tool-goal/lib/index.js:115、276-365；N/dsh-tool-subagent/lib/types/index.d.ts；N/dsh-tool-ask-user/lib/types/index.d.ts、lib/index.js:63 起及 legacy execute。O/dsh-tool-goal/lib/index.js:276-340 已有 goal_id/revision/max_goal_rounds。

### 3.5 旧整套模板的已证实漂移

| 旧项目模板 | 当前 standard 声明 | 风险 |
|---|---|---|
| dsh-workflow-worker-thread | dsh-workflow-ptc（standard.patch.yml:120） | 旧包在当前安装不存在，挂载会缺模块 |
| 缺 command-goal / present | 现有 standard 含 command-goal 和 dsh-tool-present | 静态复制会持续漏新原生功能 |
| subagent 默认未声明 modelSelectionSettings | 当前 spawn 配 true | 静态复制可能丢宿主功能选择 |
| ralph 默认启用、web.fetch=false | 当前 ralph disabled、web.fetch=true | 手工副本背离宿主策略；这些不应由治理插件冻结 |

这些差异说明“只替换缺包名”仍留下系统性维护问题。

## 4. 诊断与机检应同步升级

Coordinator 的 offline 初诊 `R/.governance/dsh-02-initial-offline.json`（exit 0）中 S1 仅因旧目录、0.98.0 marker、skill-root.txt 存在而 PASS；S3 NOT_RUN，host version null；该 PASS 带 resolution-level only。它证明旧交付文件存在，不能推导新版 roster 或可用性。

实施应拆三层证据：

1. **静态交付**：本包 entry、公开依赖、策略、可定位 skill roots 完整；已知主动卸载标 UNINSTALLED，不自动 repair。
2. **有效声明**：选定实际 install/profile 平面解析的 bundle patch 中有本包，且新模式生成本包 governance definition；目录残留只作 legacy-residue 信息。
3. **运行可用**：隔离 root boot 后 registry.resolve('governance').broken 无值、Agent compose 成功、工具和技能目录实际可读；只有这层可声明 runtime PASS。

dsh_compat 原 probe 使用安装态 resolveConfig、entryListSchema、evaluate、isJsExpr，源码 :539 起；这些公开符号在当前类型中仍存在。需要按生成的真实 child rows 运行 schema 检查，并保留 !!js/祖先 disabled/无 schema/零校验不得 PASS 的语义。不能继续只验证退休的整套 template。doctor offline 无运行 probe 时必须显示 NOT_RUN 的 runtime 面。

hooks 的 find_spg_home 还读取旧 `.agent-presets/governance/skill-root.txt`（pre-commit:68、commit-msg:858、post-commit:27）；同一函数已接受 SOFTWARE_PROJECT_GOVERNANCE_HOME。新 native 路径不得为兼容 hooks 而再次落旧 HOME 文件：验证既有显式 workflow-home / repo-local 路径能否覆盖，并把“无旧 marker 的新会话提交”加入验收。任何必要 hook 修订必须由 Coordinator 避开暂停 FIX-445 字节，单独定范围。

## 5. 未证实事项与下一步

Coordinator 又完成隔离 CLI dump：`DSH_HOME=R/.governance/sandboxes/dsh102-baseline`，`dsh --profile web --dump-default-config` exit 0；输出 `R/.governance/dsh-02-stock-config.yml`，standard 声明位于 622-624 行、workflow-ptc 位于 776 行。它进一步印证当前组合树采用原生声明，仍不是运行挂载/E2E证明。

另一次隔离基线 `R/.governance/dsh-02-baseline-compat.log`：有效 DSH_INSTALL_DIR 为 `C:/Users/peter/AppData/Roaming/npm`，CLI0.2识别正确，但 oracle 四包全部 unknown，Node createRequire 锚在外层 npm/node_modules 下，找不到实际嵌套在 CLI 包 node_modules 的 js-yaml，结果 NOT_RUN（exit 0）。故探针布局同样需要适配；不能因该结果宣称新版 schema 通过。父任务首次错误地把 override 设到 CLI 包目录被拒收属于输入错误，与第二次有效输入后的布局缺陷分开。

最终推荐方案进一步收窄为公开 Loader 已组合树的 validated `Entry.fiber.config` + registry 服务；无需 app-boot 裸 import，也不将 view-only readDocument 当继承协议。模块/接入时序见设计 §3-5；最小边界真机隔离可行性仍列 S-A 硬门。

- NOT_RUN：新公共组合读取、派生注册方案的启动时序、包内 ESM peer 解析、完整挂载/处置、真实 Agent 工具调用。
- NOT_RUN：0.2 UI 选预设、governance skill 加载、切换后普通会话隔离、spawn/fork 子代理继承。
- NOT_RUN：旧 0.1.5-rc.1 真实复验；现存缓存是 rc.3，不能冒充 rc.1。
- SOURCE：只补 profile 登记不能修复已退休目录模型；该推断要以隔离失败/成功对照闭环。
- 推荐设计见 `docs/architecture/dsh-adapter-version-decoupling.md`。独立 Design Reviewer 必须审查后才实施。
- 顺序：设计审查 → 隔离实现与验收 → CI 修复及 0.99 收尾 → 发布 → 用户环境重装。用户明确要求发布前不要恢复插件，适用全链。

## 附录 A：本轮命令与真实环境影响

本轮只有 Get-Content、rg、Test-Path、Get-FileHash 和 JSON 投影；影响路径均为**只读源**；没有 DSH 运行探针、pnpm、写用户目录、网络请求或会话读取。PowerShell 复合只读命令的外层 exit 0 不代表所有 rg 子查询成功，失败子查询如下：

- 缺不存在的 dsh-cmdline/cordis.patch.yml；
- 将 N/dsh/package.json 当路径（不存在，实际 CLI 位于 H）；
- 部分 PowerShell literal wildcard 传给 rg 导致 os error 123；随后改用目录 + -g 查询；
- 若干候选 references/platform-execution.md、platform-adapters.md 不存在。没有使用其结果支持设计。

日志附录的 started 是 UTC；本任务前段未单独采集时间，标“未采集”，不补造精确时间。所有外部源均限定 H/N/O 的安装包源码/manifest。真实用户 profile 未被本 Architect 读取或变更。Coordinator 提供的 offline 诊断保留其自身证据归属。

### A.1 外部安装态读取命令逐条记录

下列 JSONL 的 impact 均为只读（H/N/O 安装态源码与 manifest；同时引用的 R 路径也是只读）。started=null 的五条发生在 2026-10-16T15:20:21Z 之前，本轮未单独采集其精确时间；外层退出码由工具返回。无任何实际 DSH 运行探针。

```jsonl
{"id":"RO-01","cmd":"Get-Content -Encoding UTF8 C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json; Get-Content -Encoding UTF8 adapters/dsh/host-contract.json","started":null,"exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-02","cmd":"$c=Get-Content -Raw -Encoding UTF8 adapters/dsh/host-contract.json | ConvertFrom-Json; $c.PSObject.Properties.Name; $c.host | ConvertTo-Json -Depth 7; $c.evidence | ConvertTo-Json -Depth 5; Get-Content -Encoding UTF8 C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json","started":null,"exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-03","cmd":"rg --files C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh | rg '(dsh-agent-presets|dsh-persona|dsh-skill-filesystem|dsh-tool-goal|dsh-app-boot|dsh-base|dsh-tool-subagent|dsh-tool-ask-user|dsh-core|dsh-plugin)' | Select-Object -First 70","started":null,"exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-04","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/dsh-agent-preset/lib/types/index.d.ts\"; Get-Content -Encoding UTF8 \"$p/dsh-agent-preset/README.md\"; Get-Content -Encoding UTF8 \"$p/dsh-base/cordis.patch.yml\"","started":null,"exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-05","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/dsh-persona/lib/types/index.d.ts\"; Get-Content -Encoding UTF8 \"$p/dsh-skill-filesystem/lib/types/index.d.ts\"; Get-Content -Encoding UTF8 \"$p/dsh-tool-subagent/lib/types/index.d.ts\"; Get-Content -Encoding UTF8 \"$p/dsh-tool-ask-user/lib/types/index.d.ts\"; Get-Content -Encoding UTF8 \"$p/dsh-tool-goal/lib/types/index.d.ts\"","started":null,"exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-06","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/dsh-agent-preset-registry/lib/types/types.d.ts\"; Get-Content -Encoding UTF8 \"$p/dsh-agent-preset-registry/lib/types/index.d.ts\"; Get-Content -Encoding UTF8 \"$p/dsh-agent-preset/lib/index.js\"","started":"2026-10-16T15:20:21.393Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-07","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n 'preset|agent.cordis|\\.agent-presets|standard|creator|extends|plugins:|inherit' \"$p/dsh-base/cordis.patch.yml\" \"$p/dsh-agent-preset-registry/lib\" \"$p/dsh-agent/lib/types\" \"$p/dsh-app-boot/lib\" | Select-Object -First 130","started":"2026-10-16T15:20:21.822Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-08","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh'; rg -n 'compatib|bundle|plugin add|--profile|migrate|legacy|dsh-agent-presets' \"$p/lib\" | Select-Object -First 100; Get-Content -Encoding UTF8 \"$p/node_modules/@deepseek-ai/dsh-app-boot/lib/types/plugin-compatibility.d.ts\"","started":"2026-10-16T15:20:22.366Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-09","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n 'preset|persona|isolate:|plugins:|id: standard|id: creator|tool-subagent|skill-filesystem|tool-goal|tool-ask' \"$p/dsh-web-app/cordis.patch.yml\" \"$p/dsh-cmdline/cordis.patch.yml\"; Get-Content -Encoding UTF8 \"$p/dsh-agent-preset-registry/lib/types/definition.d.ts\"; Get-Content -Encoding UTF8 \"$p/dsh-agent-preset-registry/README.md\" | Select-Object -First 130","started":"2026-10-16T15:20:37.454Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-10","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/dsh-web-app/cordis.patch.yml\" | Select-Object -First 210; rg -n 'applyEntryPatches|flattenRows|resolveDshHome|AgentPreset|agent-presets|agent-preset|version|peer|compatib' \"$p/dsh-app-boot/lib/index.js\" | Select-Object -First 80","started":"2026-10-16T15:20:37.965Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-11","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/dsh-web-app/package.json\"; rg --files \"$p/dsh-web-app/presets\"; Get-Content -Encoding UTF8 \"$p/dsh-web-app/presets/standard.patch.yml\"; Get-Content -Encoding UTF8 \"$p/dsh-app-boot/lib/types/index.d.ts\" | Select-Object -First 170; Get-Content -Encoding UTF8 \"$p/dsh-app-boot/lib/types/profile-context.d.ts\"","started":"2026-10-16T15:21:12.555Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-12","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 488 -First 155; Get-Content -Encoding UTF8 \"$p/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 242 -First 55","started":"2026-10-16T15:21:13.143Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-13","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/cordis-plugin-include/lib/types/index.d.ts\"; Get-Content -Encoding UTF8 \"$p/cordis-plugin-loader/lib/types/index.d.ts\" | Select-Object -First 130; Get-Content -Encoding UTF8 \"$p/dsh-app-boot/lib/types/profile-context.d.ts\"; Get-Content -Encoding UTF8 \"$p/dsh-app-boot/lib/types/index.d.ts\" | Select-Object -Last 90","started":"2026-10-16T15:21:29.094Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-14","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 495 -First 146; Get-Content -Encoding UTF8 \"$p/dsh-app-boot/lib/index.js\" | Select-Object -Skip 905 -First 86","started":"2026-10-16T15:21:29.564Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-15","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/dsh-tool-ask-user/lib/index.js\" | Select-Object -First 170; rg -n 'name:|token_budget|status|blocked|pause|round|include|create_goal|update_goal|get_goal' \"$p/dsh-tool-goal/lib/index.js\" | Select-Object -First 65; rg -n 'dsh-workflow-worker-thread|dsh-workflow-ptc' \"$p/dsh/package.json\" \"$p/dsh-web-app/presets/standard.patch.yml\"; Test-Path \"$p/dsh-agent-presets\"; Test-Path \"$p/dsh-workflow-worker-thread\"","started":"2026-10-16T15:21:30.013Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-16","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/dsh-app-boot/lib/types/index.d.ts\" | Select-Object -First 60; rg -n 'function readProfilePatches|function prepareProfileEntries|bareModule|baseUrl|profiles|importMap|declarers' \"$p/dsh-app-boot/lib/index.js\" | Select-Object -Last 65; Get-Content -Encoding UTF8 \"$p/dsh-app-boot/package.json\" | Select-Object -First 70; Get-Content -Encoding UTF8 \"$p/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 618 -First 25","started":"2026-10-16T15:22:05.171Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-17","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/dsh-app-boot/lib/index.js\" | Select-Object -Skip 1004 -First 95; Get-Content -Encoding UTF8 \"$p/dsh-tool-ask-user/lib/index.js\" | Select-Object -Skip 235 -First 150; Get-Content -Encoding UTF8 \"$p/dsh-tool-goal/lib/index.js\" | Select-Object -Skip 275 -First 65","started":"2026-10-16T15:22:06.219Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-18","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/dsh-app-boot/lib/index.js\" | Select-Object -Skip 2044 -First 65; Get-Content -Encoding UTF8 \"$p/dsh-plugin-manager/lib/index.js\" | Select-Object -First 65; rg -n 'inject|Inject|optional|required' \"$p/cordis/lib/types\" | Select-Object -First 35; Get-Content -Encoding UTF8 \"$p/dsh-skill-filesystem/lib/index.js\" | Select-Object -Skip 1640 -First 25","started":"2026-10-16T15:22:36.243Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-19","cmd":"$p='C:/Users/peter/AppData/Local/npm-cache/_npx/1e7f6d9597241db0/node_modules/@deepseek-ai'; Test-Path \"$p/dsh-agent-presets/lib/index.js\"; if (Test-Path \"$p/dsh-agent-presets/lib/types/index.d.ts\") { Get-Content -Encoding UTF8 \"$p/dsh-agent-presets/lib/types/index.d.ts\" | Select-Object -First 160 }; Get-Content -Encoding UTF8 C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis/lib/types/registry.d.ts | Select-Object -First 20","started":"2026-10-16T15:22:58.457Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-20","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n 'Config =|inject =|workflowEngine|provider|name =|export' \"$p/dsh-workflow-ptc/lib/index.js\" | Select-Object -First 40; rg -n 'customSkillDirs|providerName|includeDefaultRoots|const Config' \"$p/dsh-skill-filesystem/lib/index.js\" | Select-Object -Last 35; Get-Content -Encoding UTF8 \"$p/dsh-app-boot/lib/index.js\" | Select-Object -Skip 886 -First 27","started":"2026-10-16T15:22:59.395Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-21","cmd":"$p='C:/Users/peter/AppData/Local/npm-cache/_npx/1e7f6d9597241db0/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/dsh/package.json\" | Select-Object -First 9; Get-Content -Encoding UTF8 \"$p/dsh-agent-presets/lib/types/index.d.ts\" | Select-Object -Skip 155 -First 165; Get-Content -Encoding UTF8 \"$p/dsh-tool-goal/lib/index.js\" | Select-Object -First 75","started":"2026-10-16T15:23:31.380Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-22","cmd":"$old='C:/Users/peter/AppData/Local/npm-cache/_npx/1e7f6d9597241db0/node_modules/@deepseek-ai'; rg -n 'create_goal|update_goal|token_budget|goal_id|max_goal_rounds|action:' \"$old/dsh-tool-goal/lib/index.js\" | Select-Object -First 25; rg -n -g '*.md' 'create_goal|update_goal|token_budget|max_goal_rounds' skills commands adapters | Select-Object -First 85; rg -n '^(def )|S1|marker|version|governance|rendered' skills/software-project-governance/infra/dsh_doctor.py | Select-Object -First 80","started":"2026-10-16T15:23:50.411Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-23","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n 'definition|register\\(|readProfilePatches|composeEntries|Copy|directory|scans|default|extends|Known Limitations' \"$p/dsh-agent-preset-registry/README.md\" \"$p/dsh-agent-preset/lib/index.js\" \"$p/dsh-app-boot/lib/types/index.d.ts\" \"$p/dsh-web-app/presets/standard.patch.yml\"; rg -n 'CURRENT|mode|status|stage|FEAT-102' .governance/dsh-02-initial-offline.json | Select-Object -First 30; rg -n 'ensurePreset|current === version|rmSync\\(userDir|function apply|CONTRACT_URL' lib/index.js","started":"2026-10-16T15:23:50.986Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-24","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; @('dsh-agent-preset','dsh-agent-preset-registry','dsh-app-boot','dsh-persona','dsh-skill-filesystem','dsh-tool-goal','dsh-tool-subagent','dsh-tool-ask-user','dsh-workflow-ptc','cordis-plugin-loader','cordis-plugin-include') | ForEach-Object { $m=Get-Content -Raw -Encoding UTF8 \"$p/$_/package.json\" | ConvertFrom-Json; [pscustomobject]@{name=$m.name;version=$m.version} } | ConvertTo-Json; Get-FileHash -Algorithm SHA256 -LiteralPath \"$p/dsh-web-app/presets/standard.patch.yml\", \"$p/dsh-agent-preset/lib/index.js\", \"$p/dsh-agent-preset-registry/lib/index.js\", \"$p/dsh-app-boot/lib/index.js\" | Select-Object Path,Hash | ConvertTo-Json","started":"2026-10-16T15:24:36.373Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-25","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/cordis-plugin-loader/lib/types/config/tree.d.ts\"; Get-Content -Encoding UTF8 \"$p/cordis-plugin-loader/lib/types/internal.d.ts\"; Get-Content -Encoding UTF8 \"$p/dsh-plugin-manager/lib/index.js\" | Select-Object -Skip 3600 -First 45; rg -n 'loader.import\\(|internal.import\\(|function manifestOf|readPluginMeta\\(' \"$p/dsh-app-boot/lib/index.js\" | Select-Object -First 20","started":"2026-10-16T15:27:27.538Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-26","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/dsh-app-boot/lib/types/profile-resolution/service.d.ts\" | Select-Object -First 160; Get-Content -Encoding UTF8 \"$p/cordis-plugin-loader/lib/index.js\" | Select-String -Pattern 'async import\\(' -Context 0,17; Get-Content -Encoding UTF8 \"$p/dsh-app-boot/lib/index.js\" | Select-Object -Skip 1335 -First 65","started":"2026-10-16T15:27:28.065Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-27","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n 'import\\(name|get context\\(|unwrapExports\\(' \"$p/cordis-plugin-loader/lib/index.js\" | Select-Object -First 16; Get-Content -Encoding UTF8 \"$p/cordis-plugin-loader/lib/index.js\" | Select-String -SimpleMatch 'import(name, getOuterStack)' -Context 0,24; Get-Content -Encoding UTF8 \"$p/dsh-app-boot/lib/index.js\" | Select-Object -Skip 3688 -First 25; Get-Content -Encoding UTF8 \"$p/dsh-app-boot/lib/index.js\" | Select-Object -Skip 3240 -First 25","started":"2026-10-16T15:27:42.765Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-28","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n 'new PluginPackages|pluginPackages|createRuntimeResolution|new Loader|bareModuleBaseUrl' C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/lib/profile-boot-BZ2ZjNWi.js \"$p/dsh-app-boot/lib/index.js\" | Select-Object -Last 32; Get-Content -Encoding UTF8 \"$p/cordis-plugin-loader/lib/types/config/entry.d.ts\" | Select-Object -First 110","started":"2026-10-16T15:27:43.325Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-29","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/cordis-plugin-loader/lib/index.js\" | Select-Object -Skip 45 -First 140; Get-Content -Encoding UTF8 \"$p/cordis-plugin-loader/lib/types/config/group.d.ts\"; Get-Content -Encoding UTF8 \"$p/cordis/lib/types/events.d.ts\" | Select-Object -Skip 196 -First 55; Get-Content -Encoding UTF8 \"$p/cordis/lib/types/context.d.ts\" | Select-Object -Skip 45 -First 48","started":"2026-10-16T15:28:30.511Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-30","cmd":"Get-Content -Encoding UTF8 .governance/dsh-02-baseline-compat.log | Select-Object -First 80; Get-Content -Encoding UTF8 skills/software-project-governance/infra/hooks/pre-commit | Select-Object -Skip 65 -First 70; Get-Content -Encoding UTF8 C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai/cordis-plugin-loader/lib/index.js | Select-Object -Skip 128 -First 34","started":"2026-10-16T15:28:31.039Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
{"id":"RO-31","cmd":"$p='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$p/cordis/lib/types/fiber.d.ts\" | Select-Object -Skip 58 -First 78; Get-Content -Encoding UTF8 \"$p/cordis-plugin-loader/lib/index.js\" | Select-Object -Skip 323 -First 50; Get-Content -Encoding UTF8 \"$p/cordis-plugin-loader/lib/index.js\" | Select-Object -Skip 442 -First 42","started":"2026-10-16T15:29:11.460Z","exit_code":0,"impact":"read-only H/N/O and referenced R files; no writes"}
```


