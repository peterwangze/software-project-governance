# FEAT-102 S-A — DSH 原生预设真实宿主可行性探针

执行日期：2026-10-17（Asia/Shanghai；原始命令时间为 UTC 2026-10-16）。角色：Governance Developer。仅修改本报告和 `docs/prototypes/dsh-native-feasibility.mjs`；未提交、未修改产品入口或治理账本、未重装用户插件。

## 裁定范围

```text
execution_status=CHECKPOINT_COMPLETE
product_implementation_authorized=false
release_authorized=false
natural_web_create=PASS_IN_TESTED_FIXTURE
post_boot_visibility=FAIL_FOR_SETIMMEDIATE_SCHEDULING
arbitrary_admission_delay=FAIL_EXPECTED_COUNTEREXAMPLE
design_review_required=true
full_current_web_profile=NOT_RUN
paid_model_calls=0
```

方案 B 的真实最小链路可运行：当前 CLI 0.2.0-rc.2 / Node v24.13.1 的真实 Cordis、Loader、native declaration、registry、Session、AgentRegistry、AgentLoop、公开 Web SessionController 已完成 register→resolve 无 broken→Agent compose→dispose。最终运行 20 场景、38 次 persona/skill 非零 schema 校验，无未处理 rejection。普通 standard 配置保持，卸载只撤回本插件，两个清理竞态均通过。

**不能据此解锁 S-B。** 当前设计没有约束“apply 返回后任务”究竟是 microtask 还是下一事件循环任务。使用 `setImmediate` 的真实 boot 变体，在 `app-boot.boot()` 返回后立即调用真实 `agentPresets.list/resolve`，governance 尚未登记，resolve 报 `agent-preset/not-found`。这不是 fake registry 或自有 readiness 等待产生的结论。microtask 变体中 register 在 boot 返回前开始、在 boot 返回后才完成，真实 Web create 通过；registry 先同步登记 record 再 await mount，使该路径能等待激活。两种时序必须分开描述。

正常 first/last 行位置、显式/default-governance 与 standard 对照的 Web `create` 全部通过。包括 setImmediate 变体，`create` 内部先 `await mkdir(cwd)`，实际调度给了后台登记机会，因此没有观察到自然 Web `create` 失败。不能把“首个 create 尝试早于 register”直接写成首个 session 创建失败。另三种测试在 root settle 后、register 调用前加事件控制 barrier，真实 create 报 not-found；这是人工注入的可证伪窗口，证明该窗口没有宿主等待保证，**不是已证明原设计正常路径会执行的异步缺口**。

## 入口事实纠正与隔离方式

当前 `dsh-headless/lib/index.js:293–321` 仅等待 Loader、安装模型选择并调用 `agents.create`；没有选择/挂载 agent preset，AgentLoop 也没有自动 preset 挂载逻辑。不能将 headless 创建成功当成 governance/default-governance 首会话通过。真正覆盖本轮的 consumer 是公开 `SessionController.create`：内部先 mkdir，再 `composeAgent→presets.resolve`，在真正 AgentLoop 的 unpublished Agent setup 中 `presets.mount`。没有复制此实现或读取私有 controller 字段；没有调用私有 definitions/_config/_error。

探针显式接收 CLI manifest，所有宿主模块用该 manifest 的 `createRequire` 解析，记录真实路径；原型自身位于 repo 的 docs/prototypes，从未给 repo 安装宿主 node_modules。真实 Loader 的公共 builtins 用于把所选 SDK 的真实模块送入隔离树；这是验证工具注入点，**不是产品解析方案或完整 `link:<repo>` 安装验收**。产品当前入口仍为旧实现，未接线。

全部运行前校验 sandbox 绝对路径为仓库内 `.governance/sandboxes/feat102-sa`；DSH_HOME、TEMP、TMP、DSH_AGENTS_HOME 均指向它。当前 profile、真实 HOME、安装包及暂停 FIX-445 文件未写入。运行仅创建 sandbox 配置/结果文件；不启动网络监听、不配置模型后端、不发送 followup/model 请求、不调用旧 writer。

模型/工具/会话/提示词/技能服务均是真实实现，Agent 创建后保持 idle。只有该调用路径不使用的 fileUploads 注册回调、attachments、workspaceRegistry、cold sessionQuery、fs IO 面提供最小空 fixture，避免网络、上传、历史磁盘会话等无关集成。Web controller 由其公开构造器装载，使用真实 `resolveConfig(SessionController, ...)`；完整静态 inject 的未用 IO 装配与 HTTP transport 没有验收。base 是原型 native fixture（真实 persona/skill 模块），不是拷贝整份 stock standard。该限制禁止把结果升级为完整 current-web profile 或 UI E2E 通过。

## 最小验收材料

| R0 §5 要求 | 结果 | 证据与边界 |
| --- | --- | --- |
| 真实 source/register/resolve/Agent compose/dispose | PASS（fixture） | 20 场景，38 次真实 persona/skill schema 校验；有效 fixture 的 second-control session 通过真实 AgentLoop compose，header/composedPreset 均 governance。第二次是显式 after-ready 对照，未用于首会话保证。 |
| 行前/末、root/register 延迟、显式/default、standard、同步时序 | 部分 PASS / 时序门 FAIL | raw results 逐事件 sequence/ms；正常 create 通过，setImmediate 实际 boot 后 roster/resolve 失败，人工 admission delay 的 create 失败另列。 |
| root-await/登记飞行中卸载 | PASS | root await 中 cleanup 完成后才释放 root barrier；无自等待。register 飞行中先 cleanup 返回、后真实 mount 返回 disposer，立即 late-dispose；drain 后仅 standard，无 rejection。 |
| base/custom overrides/!!js/two deltas/context | PASS（有限 fixture） | 真实 native Fiber.config 读取；深拷贝保留 prefix/suffix、用户 roots、includeDefaultRoots=false、watch=false、disabled !!js group；只加正文和两根。安装上下文路径见 raw result。 |
| 如实失败/不足、退回设计 | 已报告 | microtask 是否可作为受审查的强制契约，或改为仅等待已经启动 base 的公共 Fiber.await 等接线，需同一 Design Reviewer 裁定；本探针未验证 Fiber.await 候选、不调用 Entry.init。 |

`broken-registration` 负例故意加不存在的 builtin。真实 registry 的 register 正常返回 disposer，resolve 暴露 broken；原型没有记录 READY，Web create 报 `agent-preset/invalid`，最终清理不留 governance。此用例证明 Promise 正常返回不能当作 READY；其首会话失败是预期负例，未计作自然 readiness 回归。

标准对照只证明 fixture 的 public accepted plugins 始终 deep-equal、standard 保持有效且自有 governance disposer 不删除它；没有声称全部宿主工具 schema/参数、真实技能读取、热刷新、权限工具、多 profile 或未来版本兼容。完整 link 安装、真人工具/UI/付费模型、升级迁移、支持矩阵、发布及重新安装均 NOT_RUN。

## 可重放命令

```powershell
$saSandbox = [IO.Path]::GetFullPath((Join-Path (Get-Location) '.governance/sandboxes/feat102-sa'))
$env:DSH_HOME = $saSandbox
$env:TEMP = $saSandbox
$env:TMP = $saSandbox
$env:DSH_AGENTS_HOME = $saSandbox
node docs/prototypes/dsh-native-feasibility.mjs 'C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json' $saSandbox
```

该 manifest 是本次**工具参数/证据**，不是写死在产品代码中的安装路径。进程 exit 0 表示探针成功执行并收集了全部失败/通过结果，**不表示产品或 S-A 的时序硬门全绿**。最终结构化结论为 `FAIL_POST_BOOT_PRESET_VISIBILITY`。

## Coordinator 写回建议

- Proposed evidence：FEAT-102 S-A，20 真实隔离场景/38 schema、自然 Web create fixture 通过，真实 boot 后 setImmediate 可见性失败；明确三种人工 admission delay 反例和 headless 推断纠正。引用本报告及原型，并保存命令审计。
- Proposed decision：在同 Design Reviewer 复审并裁定初始登记的公开时序契约前，S-B～F 继续未授权；不得用 sleep 或先等自有 readiness 的 harness 解锁。
- Proposed risk：bootstrap-ready 与 native preset-ready 两条链存在可见性窗口；当前 fixture 的 mkdir I/O 掩盖了 create 失败，不能依赖这项偶然等待。责任 Developer/Design Reviewer，截止 S-B 准入前。
- Coordinator 边界确认：本 Agent 未修改 .governance 治理账本。sandbox 是派发授权的运行产物，不是治理记录。

## 外部命令逐条审计与原始结果

以下附录由最终运行 JSON 原样嵌入；记录 raw event 顺序，不使用固定 sleep。命令 R4 审计单列 SOURCE 读取和 sandbox 运行，失败查询不据此推导包不存在。

### 命令审计（21 条外部读取/隔离运行）
UTC 来自当次命令内 `[DateTime]::UtcNow` 打印，exit 来自 exec 完成结果。RO 项保留外部读取命令体；同次调用的本仓库只读前缀和打印日志尾部不在外部读命令体中。未伪造缺失时间。RUN-01～04 原型逐步扩充，前几次 stdout 的结论尚未区分人工 barrier/预期 broken 负例；以 RUN-04 为最终裁定，历史结论仅记录当时输出。
```json
[
  {
    "id": "SA-RO-01",
    "started": "2026-10-16T15:56:37.1510497Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$saSdk/dsh-agent-preset-registry/lib/types/index.d.ts\"; Get-Content -Encoding UTF8 \"$saSdk/cordis-plugin-loader/lib/types/index.d.ts\"; Get-Content -Encoding UTF8 \"$saSdk/dsh-agent-preset/lib/index.js\"; Get-Content -Encoding UTF8 \"$saSdk/dsh-headless/lib/index.js\" | Select-Object -Skip 280 -First 95; Get-Content -Encoding UTF8 \"$saSdk/cordis/package.json\"",
    "exit_code": 0,
    "exit_semantics": "exec shell exit; individual unmatched rg/nonterminating Get-Content errors may occur",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "command_scope": "external-read body with original SDK/time prologue; local-only prefaces and Write-Output log tail omitted",
    "query_note": "Original Write-Output LASTEXITCODE field was empty; actual exec result exit_code was 0."
  },
  {
    "id": "SA-RO-02",
    "started": "2026-10-16T15:56:46.7177965Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$saSdk/dsh-agent-preset-registry/lib/index.js\" | Select-Object -First 150; Get-Content -Encoding UTF8 \"$saSdk/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 440 -First 280; Get-Content -Encoding UTF8 \"$saSdk/cordis-plugin-loader/lib/types/config/tree.d.ts\"; Get-Content -Encoding UTF8 \"$saSdk/cordis-plugin-loader/lib/types/config/group.d.ts\"; Get-Content -Encoding UTF8 \"$saSdk/cordis/lib/types/context.d.ts\" | Select-Object -First 110",
    "exit_code": 0,
    "exit_semantics": "exec shell exit; individual unmatched rg/nonterminating Get-Content errors may occur",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "command_scope": "external-read body with original SDK/time prologue; local-only prefaces and Write-Output log tail omitted"
  },
  {
    "id": "SA-RO-03",
    "started": "2026-10-16T15:57:03.5341733Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$saSdk/dsh-agent/lib/types/index.d.ts\" | Select-Object -First 155; rg -n 'static inject|constructor\\(|async create\\(' \"$saSdk/dsh-agent/lib/index.js\"; Get-Content -Encoding UTF8 \"$saSdk/dsh-session-projections/lib/types/index.d.ts\" | Select-Object -First 70; Get-Content -Encoding UTF8 \"$saSdk/cordis-plugin-loader/lib/index.js\" | Select-Object -First 170",
    "exit_code": 0,
    "exit_semantics": "exec shell exit; individual unmatched rg/nonterminating Get-Content errors may occur",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "command_scope": "external-read body with original SDK/time prologue; local-only prefaces and Write-Output log tail omitted",
    "query_note": "Included guessed nonexistent path; not used as evidence of host package absence. RO03 dsh-session-projections; RO06 dsh-tool; RO07 dsh-tool-registry; RO17 dsh-webserver."
  },
  {
    "id": "SA-RO-04",
    "started": "2026-10-16T15:57:14.0159775Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$saSdk/dsh-agent-loop/lib/types/index.d.ts\" | Select-Object -First 160; rg -n 'static inject|static Config|constructor\\(|agentPresets|async create\\(' \"$saSdk/dsh-agent-loop/lib/index.js\" | Select-Object -First 65; Get-Content -Encoding UTF8 \"$saSdk/dsh-agent/lib/index.js\" | Select-Object -Skip 310 -First 170; Get-Content -Encoding UTF8 \"$saSdk/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 235 -First 105; rg -n 'sessionProjections|class Session|static inject' \"$saSdk/dsh-session/lib/index.js\" | Select-Object -First 30; Get-Content -Encoding UTF8 \"$saSdk/cordis-plugin-loader/lib/index.js\" | Select-Object -Skip 850 -First 150",
    "exit_code": 0,
    "exit_semantics": "exec shell exit; individual unmatched rg/nonterminating Get-Content errors may occur",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "command_scope": "external-read body with original SDK/time prologue; local-only prefaces and Write-Output log tail omitted"
  },
  {
    "id": "SA-RO-05",
    "started": "2026-10-16T15:57:25.2602641Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$saSdk/dsh-agent-loop/lib/index.js\" | Select-Object -Skip 1515 -First 90; Get-Content -Encoding UTF8 \"$saSdk/cordis-plugin-loader/lib/index.js\" | Select-Object -Skip 710 -First 150; rg --files \"$saSdk\" | rg '/lib/types/index.d.ts$|\\lib\\types\\index.d.ts$' | rg 'session|projection|prompt|agent-default-model'; rg -n 'sessionProjections|name:.*dsh-(agent|session|model|prompt)' .governance/dsh-02-stock-config.yml; Get-Content -Encoding UTF8 \"$saSdk/dsh-headless/lib/index.js\" | Select-Object -First 85",
    "exit_code": 0,
    "exit_semantics": "exec shell exit; individual unmatched rg/nonterminating Get-Content errors may occur",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "command_scope": "external-read body with original SDK/time prologue; local-only prefaces and Write-Output log tail omitted"
  },
  {
    "id": "SA-RO-06",
    "started": "2026-10-16T15:57:44.4635487Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$saSdk/dsh-session/lib/index.js\" | Select-Object -Last 25; Get-Content -Encoding UTF8 \"$saSdk/dsh-session-projection/lib/index.js\" | Select-Object -Last 25; Get-Content -Encoding UTF8 \"$saSdk/dsh-system-prompt/lib/index.js\" | Select-Object -Last 25; rg -n 'static inject|constructor\\(|super\\(ctx' \"$saSdk/dsh-llm/lib/index.js\" | Select-Object -Last 15; rg -n 'static inject|constructor\\(|super\\(ctx' \"$saSdk/dsh-tool/lib/index.js\" | Select-Object -Last 15; Get-Content -Encoding UTF8 \"$saSdk/cordis-plugin-loader/lib/index.js\" | Select-Object -Last 130; Get-Content -Encoding UTF8 \"$saSdk/dsh-session-projection/lib/types/index.d.ts\" | Select-Object -First 70",
    "exit_code": 0,
    "exit_semantics": "exec shell exit; individual unmatched rg/nonterminating Get-Content errors may occur",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "command_scope": "external-read body with original SDK/time prologue; local-only prefaces and Write-Output log tail omitted",
    "query_note": "Included guessed nonexistent path; not used as evidence of host package absence. RO03 dsh-session-projections; RO06 dsh-tool; RO07 dsh-tool-registry; RO17 dsh-webserver."
  },
  {
    "id": "SA-RO-07",
    "started": "2026-10-16T15:57:57.9120067Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n 'static inject|constructor\\(|super\\(ctx' \"$saSdk/dsh-tool-registry/lib/index.js\" | Select-Object -First 12; rg -n 'static inject|constructor\\(|super\\(ctx' \"$saSdk/dsh-session-projection/lib/index.js\" | Select-Object -Last 12; rg -n 'static inject|constructor\\(|super\\(ctx' \"$saSdk/dsh-session/lib/index.js\" | Select-Object -Last 12; Get-Content -Encoding UTF8 \"$saSdk/dsh-agent-loop/lib/index.js\" | Select-Object -Skip 770 -First 85; rg -n 'agentPresets|async createAgent|createAgent\\(' \"$saSdk/dsh-agent-loop/lib/index.js\" | Select-Object -Last 20; Get-Content -Encoding UTF8 \"$saSdk/dsh-persona/lib/index.js\" | Select-Object -First 90",
    "exit_code": 0,
    "exit_semantics": "exec shell exit; individual unmatched rg/nonterminating Get-Content errors may occur",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "command_scope": "external-read body with original SDK/time prologue; local-only prefaces and Write-Output log tail omitted",
    "query_note": "Included guessed nonexistent path; not used as evidence of host package absence. RO03 dsh-session-projections; RO06 dsh-tool; RO07 dsh-tool-registry; RO17 dsh-webserver."
  },
  {
    "id": "SA-RO-08",
    "started": "2026-10-16T15:58:06.9095383Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$saSdk/dsh-agent-loop/lib/index.js\" | Select-Object -Skip 1835 -First 180; rg -n 'tools|system-prompt' .governance/dsh-02-stock-config.yml | Select-Object -First 15; Get-Content -Encoding UTF8 \"$saSdk/dsh-skill-filesystem/lib/index.js\" | Select-Object -First 115; Get-Content -Encoding UTF8 \"$saSdk/dsh-llm/lib/types/index.d.ts\" | Select-Object -First 90; Get-Content -Encoding UTF8 \"$saSdk/cordis/lib/types/fiber.d.ts\" | Select-Object -Skip 20 -First 160",
    "exit_code": 0,
    "exit_semantics": "exec shell exit; individual unmatched rg/nonterminating Get-Content errors may occur",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "command_scope": "external-read body with original SDK/time prologue; local-only prefaces and Write-Output log tail omitted"
  },
  {
    "id": "SA-RO-09",
    "started": "2026-10-16T15:58:18.7268696Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n 'agent-preset|agentPresets|agentPreset|mount\\(' \"$saSdk/dsh-agent-loop/lib/index.js\" | Select-Object -First 35; rg -n 'agentPresets|agent/created|session/created|agent/setup' \"$saSdk/dsh-agent-preset-registry/lib/index.js\"; Get-Content -Encoding UTF8 \"$saSdk/dsh-session-log-deepseek/lib/index.js\" | Select-Object -First 90; rg -n 'static inject|constructor\\(|super\\(ctx' \"$saSdk/dsh-skill/lib/index.js\" | Select-Object -Last 15; Get-Content -Encoding UTF8 \"$saSdk/dsh-system-prompt/lib/index.js\" | Select-Object -Skip 460 -First 65; Get-Content -Encoding UTF8 \"$saSdk/dsh-tools/lib/index.js\" | Select-Object -Last 30",
    "exit_code": 0,
    "exit_semantics": "exec shell exit; individual unmatched rg/nonterminating Get-Content errors may occur",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "command_scope": "external-read body with original SDK/time prologue; local-only prefaces and Write-Output log tail omitted"
  },
  {
    "id": "SA-RO-10",
    "started": "2026-10-16T15:58:26.8598135Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -l 'agentPresets.mount' \"$saSdk\" -g '*.js' -g '!*.map'; Get-Content -Encoding UTF8 \"$saSdk/dsh-system-prompt/lib/index.js\" | Select-String -Pattern 'static Config|constructor|static inject' -Context 0,18; Get-Content -Encoding UTF8 \"$saSdk/dsh-session-projection/lib/index.js\" | Select-Object -First 80; Get-Content -Encoding UTF8 \"$saSdk/dsh-skill/lib/index.js\" | Select-Object -Skip 120 -First 45",
    "exit_code": 0,
    "exit_semantics": "exec shell exit; individual unmatched rg/nonterminating Get-Content errors may occur",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "command_scope": "external-read body with original SDK/time prologue; local-only prefaces and Write-Output log tail omitted"
  },
  {
    "id": "SA-RO-11",
    "started": "2026-10-16T15:58:36.7917719Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n 'agentPresets|agent-preset' \"$saSdk/dsh-app-boot/lib/index.js\" | Select-Object -Last 45; Get-Content -Encoding UTF8 \"$saSdk/dsh-app-boot/lib/index.js\" | Select-Object -Skip 3800 -First 115; rg -l 'agent-preset|agentPreset' \"$saSdk/dsh-agent-loop/lib\" -g '*.js'; rg -n 'mount|compose|agentPreset' \"$saSdk/dsh-agent/lib/index.js\" | Select-Object -First 40",
    "exit_code": 0,
    "exit_semantics": "exec shell exit; individual unmatched rg/nonterminating Get-Content errors may occur",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "command_scope": "external-read body with original SDK/time prologue; local-only prefaces and Write-Output log tail omitted"
  },
  {
    "id": "SA-RO-12",
    "started": "2026-10-16T15:58:46.5276103Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -l 'agentPresets' \"$saSdk\" -g '*.js' | Select-Object -First 40; Get-Content -Encoding UTF8 .governance/dsh-02-stock-config.yml | Select-Object -Skip 595 -First 38; Get-Content -Encoding UTF8 \"$saSdk/dsh-headless/lib/index.js\" | Select-String -Pattern 'inject|Config' -Context 0,13; Get-Content -Encoding UTF8 \"$saSdk/cordis-plugin-loader/lib/index.js\" | Select-Object -Skip 170 -First 80",
    "exit_code": 0,
    "exit_semantics": "exec shell exit; individual unmatched rg/nonterminating Get-Content errors may occur",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "command_scope": "external-read body with original SDK/time prologue; local-only prefaces and Write-Output log tail omitted"
  },
  {
    "id": "SA-RO-13",
    "started": "2026-10-16T15:59:01.1957929Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$saSdk/dsh-api-session-controller/lib/types/agent.d.ts\"; Get-Content -Encoding UTF8 \"$saSdk/dsh-api-session-controller/lib/types/agent.js\" | Select-Object -First 250; rg -n 'function.*Agent|async.*create|agentPresets.mount|agentPresets.resolve|export' \"$saSdk/dsh-api-session-controller/lib/index.js\" | Select-Object -Last 40",
    "exit_code": 0,
    "exit_semantics": "exec shell exit; individual unmatched rg/nonterminating Get-Content errors may occur",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "command_scope": "external-read body with original SDK/time prologue; local-only prefaces and Write-Output log tail omitted"
  },
  {
    "id": "SA-RO-14",
    "started": "2026-10-16T15:59:13.4339640Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$saSdk/dsh-api-session-controller/package.json\" | Select-Object -First 90; Get-Content -Encoding UTF8 \"$saSdk/dsh-api-session-controller/lib/index.js\" | Select-Object -Skip 320 -First 160; Get-Content -Encoding UTF8 \"$saSdk/dsh-api-session-controller/lib/index.js\" | Select-Object -Skip 565 -First 165; Get-Content -Encoding UTF8 \"$saSdk/dsh-agent-default-model/lib/index.js\" | Select-Object -First 120",
    "exit_code": 0,
    "exit_semantics": "exec shell exit; individual unmatched rg/nonterminating Get-Content errors may occur",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "command_scope": "external-read body with original SDK/time prologue; local-only prefaces and Write-Output log tail omitted"
  },
  {
    "id": "SA-RO-15",
    "started": "2026-10-16T15:59:21.9158106Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$saSdk/dsh-api-session-controller/lib/index.js\" | Select-Object -Skip 2870 -First 190; Get-Content -Encoding UTF8 \"$saSdk/dsh-api-session-controller/lib/types/index.d.ts\" | Select-Object -First 145; Get-Content -Encoding UTF8 \"$saSdk/dsh-typert-registry/lib/index.js\" | Select-Object -Last 40",
    "exit_code": 0,
    "exit_semantics": "exec shell exit; individual unmatched rg/nonterminating Get-Content errors may occur",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "command_scope": "external-read body with original SDK/time prologue; local-only prefaces and Write-Output log tail omitted"
  },
  {
    "id": "SA-RO-16",
    "started": "2026-10-16T15:59:29.5270137Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$saSdk/dsh-api-session-controller/lib/index.js\" | Select-Object -Skip 2810 -First 65; Get-Content -Encoding UTF8 \"$saSdk/dsh-typert-registry/lib/index.js\" | Select-String -Pattern 'class TypertRegistry|constructor\\(ctx\\)|static inject' -Context 0,30; Get-Content -Encoding UTF8 \"$saSdk/cordis/lib/types/registry.d.ts\" | Select-Object -Last 60",
    "exit_code": 0,
    "exit_semantics": "exec shell exit; individual unmatched rg/nonterminating Get-Content errors may occur",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "command_scope": "external-read body with original SDK/time prologue; local-only prefaces and Write-Output log tail omitted"
  },
  {
    "id": "SA-RO-17",
    "started": "2026-10-16T16:04:47.7315619Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$saSdk/dsh-app-boot/lib/types/index.d.ts\" | Select-Object -Last 160; Get-Content -Encoding UTF8 \"$saSdk/dsh-app-boot/lib/index.js\" | Select-Object -Skip 3970 -First 175; rg -n 'listen|loader.await|app.boot|boot\\(' \"$saSdk/dsh-webserver/lib/index.js\" | Select-Object -First 24",
    "exit_code": 0,
    "exit_semantics": "exec shell exit; individual unmatched rg/nonterminating Get-Content errors may occur",
    "impact": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "access": "read-only installed SDK; no host process; no external write",
    "command_scope": "external-read body with original SDK/time prologue; local-only prefaces and Write-Output log tail omitted",
    "query_note": "Included guessed nonexistent path; not used as evidence of host package absence. RO03 dsh-session-projections; RO06 dsh-tool; RO07 dsh-tool-registry; RO17 dsh-webserver."
  },
  {
    "id": "SA-RUN-01",
    "started": "2026-10-16T16:02:08.2458585Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSandbox=[IO.Path]::GetFullPath((Join-Path (Get-Location) '.governance/sandboxes/feat102-sa')); if (-not $saSandbox.StartsWith([IO.Path]::GetFullPath((Get-Location).Path), [StringComparison]::OrdinalIgnoreCase)) { throw 'sandbox escaped repository' }; New-Item -ItemType Directory -Force -Path $saSandbox | Out-Null; $env:DSH_HOME=$saSandbox; $env:TEMP=$saSandbox; $env:TMP=$saSandbox; $env:DSH_AGENTS_HOME=$saSandbox; node docs/prototypes/dsh-native-feasibility.mjs 'C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json' $saSandbox; $saCode=$LASTEXITCODE; Write-Output \"SA-RUN-01 started=$saStarted exit=$saCode access=SDK-readonly,sandbox-runtime-write paths=$saSandbox\"; exit $saCode",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai",
      "docs/prototypes/dsh-native-feasibility.mjs"
    ],
    "impact_write": [
      "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/feat102-sa"
    ],
    "access": "installed SDK read-only; all runtime writes constrained to validated repository sandbox",
    "observed_stdout_summary": {
      "scenarios": 12,
      "schemaChecked": 22,
      "conclusion": "FAIL_FIRST_SESSION_READINESS"
    },
    "artifact_note": "result.json overwritten by later run; only SA-RUN-04 full raw retained below. Earlier stdout summaries are recorded observations, not reconstructed full raw."
  },
  {
    "id": "SA-RUN-02",
    "started": "2026-10-16T16:03:56.0158867Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSandbox=[IO.Path]::GetFullPath((Join-Path (Get-Location) '.governance/sandboxes/feat102-sa')); if ($saSandbox -ne 'D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-sa') { throw 'unexpected sandbox' }; $env:DSH_HOME=$saSandbox; $env:TEMP=$saSandbox; $env:TMP=$saSandbox; $env:DSH_AGENTS_HOME=$saSandbox; node docs/prototypes/dsh-native-feasibility.mjs 'C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json' $saSandbox; $saCode=$LASTEXITCODE; Write-Output \"SA-RUN-02 started=$saStarted exit=$saCode access=SDK-readonly,sandbox-runtime-write paths=$saSandbox\"; exit $saCode",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai",
      "docs/prototypes/dsh-native-feasibility.mjs"
    ],
    "impact_write": [
      "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/feat102-sa"
    ],
    "access": "installed SDK read-only; all runtime writes constrained to validated repository sandbox",
    "observed_stdout_summary": {
      "scenarios": 17,
      "schemaChecked": 32,
      "conclusion": "FAIL_FIRST_SESSION_READINESS"
    },
    "artifact_note": "result.json overwritten by later run; only SA-RUN-04 full raw retained below. Earlier stdout summaries are recorded observations, not reconstructed full raw."
  },
  {
    "id": "SA-RUN-03",
    "started": "2026-10-16T16:05:40.7081339Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSandbox=[IO.Path]::GetFullPath((Join-Path (Get-Location) '.governance/sandboxes/feat102-sa')); if ($saSandbox -ne 'D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-sa') { throw 'unexpected sandbox' }; $env:DSH_HOME=$saSandbox; $env:TEMP=$saSandbox; $env:TMP=$saSandbox; $env:DSH_AGENTS_HOME=$saSandbox; node docs/prototypes/dsh-native-feasibility.mjs 'C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json' $saSandbox; $saCode=$LASTEXITCODE; Write-Output \"SA-RUN-03 started=$saStarted exit=$saCode access=SDK-readonly,sandbox-runtime-write paths=$saSandbox\"; exit $saCode",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai",
      "docs/prototypes/dsh-native-feasibility.mjs"
    ],
    "impact_write": [
      "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/feat102-sa"
    ],
    "access": "installed SDK read-only; all runtime writes constrained to validated repository sandbox",
    "observed_stdout_summary": {
      "scenarios": 20,
      "schemaChecked": 38,
      "conclusion": "NORMAL_PATH_PASS_ADMISSION_WINDOW_UNPROVEN"
    },
    "artifact_note": "result.json overwritten by later run; only SA-RUN-04 full raw retained below. Earlier stdout summaries are recorded observations, not reconstructed full raw."
  },
  {
    "id": "SA-RUN-04",
    "started": "2026-10-16T16:06:27.7831814Z",
    "cmd": "$saStarted=[DateTime]::UtcNow.ToString('o'); $saSandbox=[IO.Path]::GetFullPath((Join-Path (Get-Location) '.governance/sandboxes/feat102-sa')); if ($saSandbox -ne 'D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-sa') { throw 'unexpected sandbox' }; $env:DSH_HOME=$saSandbox; $env:TEMP=$saSandbox; $env:TMP=$saSandbox; $env:DSH_AGENTS_HOME=$saSandbox; node docs/prototypes/dsh-native-feasibility.mjs 'C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json' $saSandbox; $saCode=$LASTEXITCODE; Write-Output \"SA-RUN-04 started=$saStarted exit=$saCode access=SDK-readonly,sandbox-runtime-write paths=$saSandbox\"; exit $saCode",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai",
      "docs/prototypes/dsh-native-feasibility.mjs"
    ],
    "impact_write": [
      "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/feat102-sa"
    ],
    "access": "installed SDK read-only; all runtime writes constrained to validated repository sandbox",
    "observed_stdout_summary": {
      "scenarios": 20,
      "schemaChecked": 38,
      "conclusion": "FAIL_POST_BOOT_PRESET_VISIBILITY"
    },
    "artifact_note": "result.json overwritten by later run; only SA-RUN-04 full raw retained below. Earlier stdout summaries are recorded observations, not reconstructed full raw."
  }
]
```
### 最终 20 场景时序与状态原文
来源：`.governance/sandboxes/feat102-sa/result.json`；SHA-256 `00b5b3995845be4e6660b4e62aba291481df5da20fb8bdd2d8743d15df8d9895`。以下 JSON 为 RUN-04 原文，含相对单场景起点的毫秒与严格 sequence；它不是每个事件的 UTC，也没有把相对 ms 伪装成绝对时间。
```json
{
  "context": {
    "cliManifest": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\package.json",
    "cli": "0.2.0-rc.2",
    "node": "v24.13.1",
    "sandbox": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-sa",
    "repository": "D:\\AI\\agent\\claude\\coding\\project_management_workflow",
    "resolved": {
      "@deepseek-ai/cordis": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis\\lib\\index.js",
      "@deepseek-ai/cordis-plugin-loader": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis-plugin-loader\\lib\\index.js",
      "@deepseek-ai/dsh-agent-preset-registry": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent-preset-registry\\lib\\index.js",
      "@deepseek-ai/dsh-agent-preset": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent-preset\\lib\\index.js",
      "@deepseek-ai/dsh-session-projection": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-session-projection\\lib\\index.js",
      "@deepseek-ai/dsh-session": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-session\\lib\\index.js",
      "@deepseek-ai/dsh-agent": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent\\lib\\index.js",
      "@deepseek-ai/dsh-agent-loop": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent-loop\\lib\\index.js",
      "@deepseek-ai/dsh-llm": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-llm\\lib\\index.js",
      "@deepseek-ai/dsh-tools": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-tools\\lib\\index.js",
      "@deepseek-ai/dsh-system-prompt": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-system-prompt\\lib\\index.js",
      "@deepseek-ai/dsh-skill": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-skill\\lib\\index.js",
      "@deepseek-ai/dsh-persona": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-persona\\lib\\index.js",
      "@deepseek-ai/dsh-skill-filesystem": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-skill-filesystem\\lib\\index.js",
      "@deepseek-ai/dsh-agent-default-model": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent-default-model\\lib\\index.js",
      "@deepseek-ai/dsh-typert-registry": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-typert-registry\\lib\\index.js",
      "@deepseek-ai/dsh-api-session-controller": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-api-session-controller\\lib\\index.js",
      "@deepseek-ai/dsh-app-boot": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-app-boot\\lib\\index.js"
    },
    "repositoryHasHostNodeModules": false
  },
  "conclusion": "FAIL_POST_BOOT_PRESET_VISIBILITY",
  "postBootVisibilityFailures": [
    "actual-boot-immediate-default"
  ],
  "firstSessionFailures": [
    "admission-delay-explicit",
    "admission-delay-default",
    "actual-boot-admission-delay"
  ],
  "schemaChecked": 38,
  "unhandled": [],
  "results": [
    {
      "name": "first-governance",
      "order": "first",
      "selected": "governance",
      "rootDelay": false,
      "registrationDelay": false,
      "admissionDelay": false,
      "scheduler": "microtask",
      "preloadedCore": false,
      "brokenRegistration": false,
      "useBoot": false,
      "first": {
        "sessionId": "session-e189ecd9-e3c5-4377-bdf2-c6aabdcd39dd",
        "agentPreset": "governance"
      },
      "composed": {
        "preset": "governance",
        "header": "governance"
      },
      "checked": 2,
      "after": [
        {
          "id": "governance",
          "name": "fixture standard"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 48.513,
          "event": "own-apply"
        },
        {
          "sequence": 1,
          "ms": 48.584,
          "event": "own-apply-return"
        },
        {
          "sequence": 2,
          "ms": 49.819,
          "event": "background-task-start",
          "scheduler": "microtask"
        },
        {
          "sequence": 3,
          "ms": 54.932,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 4,
          "ms": 54.939,
          "event": "first-create-attempt",
          "requested": "governance"
        },
        {
          "sequence": 5,
          "ms": 55.473,
          "event": "own-root-settled"
        },
        {
          "sequence": 6,
          "ms": 56.08,
          "event": "register-start"
        },
        {
          "sequence": 7,
          "ms": 56.256,
          "event": "root-settled"
        },
        {
          "sequence": 8,
          "ms": 57.44,
          "event": "register-complete"
        },
        {
          "sequence": 9,
          "ms": 57.591,
          "event": "ready"
        },
        {
          "sequence": 10,
          "ms": 62.827,
          "event": "first-create-complete",
          "sessionId": "session-e189ecd9-e3c5-4377-bdf2-c6aabdcd39dd",
          "agentPreset": "governance"
        },
        {
          "sequence": 11,
          "ms": 71.016,
          "event": "cleanup-start"
        },
        {
          "sequence": 12,
          "ms": 71.051,
          "event": "cleanup-complete"
        }
      ]
    },
    {
      "name": "first-default",
      "order": "first",
      "selected": "default",
      "rootDelay": false,
      "registrationDelay": false,
      "admissionDelay": false,
      "scheduler": "microtask",
      "preloadedCore": false,
      "brokenRegistration": false,
      "useBoot": false,
      "first": {
        "sessionId": "session-cb37c815-5aa7-4b76-a172-00625c0918f6",
        "agentPreset": "governance"
      },
      "composed": {
        "preset": "governance",
        "header": "governance"
      },
      "checked": 2,
      "after": [
        {
          "id": "governance",
          "name": "fixture standard"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 5.798,
          "event": "own-apply"
        },
        {
          "sequence": 1,
          "ms": 5.834,
          "event": "own-apply-return"
        },
        {
          "sequence": 2,
          "ms": 6.234,
          "event": "background-task-start",
          "scheduler": "microtask"
        },
        {
          "sequence": 3,
          "ms": 7.477,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 4,
          "ms": 7.479,
          "event": "first-create-attempt",
          "requested": "default"
        },
        {
          "sequence": 5,
          "ms": 7.552,
          "event": "own-root-settled"
        },
        {
          "sequence": 6,
          "ms": 7.677,
          "event": "register-start"
        },
        {
          "sequence": 7,
          "ms": 7.768,
          "event": "root-settled"
        },
        {
          "sequence": 8,
          "ms": 8.679,
          "event": "register-complete"
        },
        {
          "sequence": 9,
          "ms": 8.712,
          "event": "ready"
        },
        {
          "sequence": 10,
          "ms": 10.82,
          "event": "first-create-complete",
          "sessionId": "session-cb37c815-5aa7-4b76-a172-00625c0918f6",
          "agentPreset": "governance"
        },
        {
          "sequence": 11,
          "ms": 12.653,
          "event": "cleanup-start"
        },
        {
          "sequence": 12,
          "ms": 12.669,
          "event": "cleanup-complete"
        }
      ]
    },
    {
      "name": "first-standard",
      "order": "first",
      "selected": "standard",
      "rootDelay": false,
      "registrationDelay": false,
      "admissionDelay": false,
      "scheduler": "microtask",
      "preloadedCore": false,
      "brokenRegistration": false,
      "useBoot": false,
      "first": {
        "sessionId": "session-7683e9f4-4e0c-46ec-aa6d-d2196110bdef",
        "agentPreset": "standard"
      },
      "composed": {
        "preset": "governance",
        "header": "governance"
      },
      "checked": 2,
      "after": [
        {
          "id": "governance",
          "name": "fixture standard"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 5.5,
          "event": "own-apply"
        },
        {
          "sequence": 1,
          "ms": 5.556,
          "event": "own-apply-return"
        },
        {
          "sequence": 2,
          "ms": 6.206,
          "event": "background-task-start",
          "scheduler": "microtask"
        },
        {
          "sequence": 3,
          "ms": 7.697,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 4,
          "ms": 7.701,
          "event": "first-create-attempt",
          "requested": "standard"
        },
        {
          "sequence": 5,
          "ms": 7.782,
          "event": "own-root-settled"
        },
        {
          "sequence": 6,
          "ms": 7.884,
          "event": "register-start"
        },
        {
          "sequence": 7,
          "ms": 8.001,
          "event": "root-settled"
        },
        {
          "sequence": 8,
          "ms": 9.08,
          "event": "register-complete"
        },
        {
          "sequence": 9,
          "ms": 9.112,
          "event": "ready"
        },
        {
          "sequence": 10,
          "ms": 10.668,
          "event": "first-create-complete",
          "sessionId": "session-7683e9f4-4e0c-46ec-aa6d-d2196110bdef",
          "agentPreset": "standard"
        },
        {
          "sequence": 11,
          "ms": 12.071,
          "event": "cleanup-start"
        },
        {
          "sequence": 12,
          "ms": 12.081,
          "event": "cleanup-complete"
        }
      ]
    },
    {
      "name": "last-governance",
      "order": "last",
      "selected": "governance",
      "rootDelay": false,
      "registrationDelay": false,
      "admissionDelay": false,
      "scheduler": "microtask",
      "preloadedCore": false,
      "brokenRegistration": false,
      "useBoot": false,
      "first": {
        "sessionId": "session-844094af-8fcf-41a6-a778-41d1390c966e",
        "agentPreset": "governance"
      },
      "composed": {
        "preset": "governance",
        "header": "governance"
      },
      "checked": 2,
      "after": [
        {
          "id": "governance",
          "name": "fixture standard"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 6.622,
          "event": "own-apply"
        },
        {
          "sequence": 1,
          "ms": 6.675,
          "event": "own-apply-return"
        },
        {
          "sequence": 2,
          "ms": 7.336,
          "event": "background-task-start",
          "scheduler": "microtask"
        },
        {
          "sequence": 3,
          "ms": 8.543,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 4,
          "ms": 8.546,
          "event": "first-create-attempt",
          "requested": "governance"
        },
        {
          "sequence": 5,
          "ms": 8.627,
          "event": "own-root-settled"
        },
        {
          "sequence": 6,
          "ms": 8.743,
          "event": "register-start"
        },
        {
          "sequence": 7,
          "ms": 8.851,
          "event": "root-settled"
        },
        {
          "sequence": 8,
          "ms": 9.9,
          "event": "register-complete"
        },
        {
          "sequence": 9,
          "ms": 9.937,
          "event": "ready"
        },
        {
          "sequence": 10,
          "ms": 12.326,
          "event": "first-create-complete",
          "sessionId": "session-844094af-8fcf-41a6-a778-41d1390c966e",
          "agentPreset": "governance"
        },
        {
          "sequence": 11,
          "ms": 13.85,
          "event": "cleanup-start"
        },
        {
          "sequence": 12,
          "ms": 13.866,
          "event": "cleanup-complete"
        }
      ]
    },
    {
      "name": "last-default",
      "order": "last",
      "selected": "default",
      "rootDelay": false,
      "registrationDelay": false,
      "admissionDelay": false,
      "scheduler": "microtask",
      "preloadedCore": false,
      "brokenRegistration": false,
      "useBoot": false,
      "first": {
        "sessionId": "session-9de008b2-aad5-4118-b48c-1f8f6871fd6c",
        "agentPreset": "governance"
      },
      "composed": {
        "preset": "governance",
        "header": "governance"
      },
      "checked": 2,
      "after": [
        {
          "id": "governance",
          "name": "fixture standard"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 5.984,
          "event": "own-apply"
        },
        {
          "sequence": 1,
          "ms": 6.034,
          "event": "own-apply-return"
        },
        {
          "sequence": 2,
          "ms": 6.618,
          "event": "background-task-start",
          "scheduler": "microtask"
        },
        {
          "sequence": 3,
          "ms": 7.834,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 4,
          "ms": 7.837,
          "event": "first-create-attempt",
          "requested": "default"
        },
        {
          "sequence": 5,
          "ms": 7.924,
          "event": "own-root-settled"
        },
        {
          "sequence": 6,
          "ms": 8.019,
          "event": "register-start"
        },
        {
          "sequence": 7,
          "ms": 8.124,
          "event": "root-settled"
        },
        {
          "sequence": 8,
          "ms": 9.317,
          "event": "register-complete"
        },
        {
          "sequence": 9,
          "ms": 9.361,
          "event": "ready"
        },
        {
          "sequence": 10,
          "ms": 10.812,
          "event": "first-create-complete",
          "sessionId": "session-9de008b2-aad5-4118-b48c-1f8f6871fd6c",
          "agentPreset": "governance"
        },
        {
          "sequence": 11,
          "ms": 12.386,
          "event": "cleanup-start"
        },
        {
          "sequence": 12,
          "ms": 12.397,
          "event": "cleanup-complete"
        }
      ]
    },
    {
      "name": "last-standard",
      "order": "last",
      "selected": "standard",
      "rootDelay": false,
      "registrationDelay": false,
      "admissionDelay": false,
      "scheduler": "microtask",
      "preloadedCore": false,
      "brokenRegistration": false,
      "useBoot": false,
      "first": {
        "sessionId": "session-1781c3f6-4df5-4dc0-b0c3-262e8531f08a",
        "agentPreset": "standard"
      },
      "composed": {
        "preset": "governance",
        "header": "governance"
      },
      "checked": 2,
      "after": [
        {
          "id": "governance",
          "name": "fixture standard"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 7.229,
          "event": "own-apply"
        },
        {
          "sequence": 1,
          "ms": 7.293,
          "event": "own-apply-return"
        },
        {
          "sequence": 2,
          "ms": 7.933,
          "event": "background-task-start",
          "scheduler": "microtask"
        },
        {
          "sequence": 3,
          "ms": 9.244,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 4,
          "ms": 9.247,
          "event": "first-create-attempt",
          "requested": "standard"
        },
        {
          "sequence": 5,
          "ms": 9.347,
          "event": "own-root-settled"
        },
        {
          "sequence": 6,
          "ms": 9.444,
          "event": "register-start"
        },
        {
          "sequence": 7,
          "ms": 9.55,
          "event": "root-settled"
        },
        {
          "sequence": 8,
          "ms": 10.573,
          "event": "register-complete"
        },
        {
          "sequence": 9,
          "ms": 10.604,
          "event": "ready"
        },
        {
          "sequence": 10,
          "ms": 13.314,
          "event": "first-create-complete",
          "sessionId": "session-1781c3f6-4df5-4dc0-b0c3-262e8531f08a",
          "agentPreset": "standard"
        },
        {
          "sequence": 11,
          "ms": 14.843,
          "event": "cleanup-start"
        },
        {
          "sequence": 12,
          "ms": 14.855,
          "event": "cleanup-complete"
        }
      ]
    },
    {
      "name": "admission-delay-explicit",
      "order": "first",
      "selected": "governance",
      "rootDelay": false,
      "registrationDelay": false,
      "admissionDelay": true,
      "scheduler": "microtask",
      "preloadedCore": false,
      "brokenRegistration": false,
      "useBoot": false,
      "first": {
        "error": "RemoteError: Unknown agent preset: governance",
        "code": "agent-preset/not-found"
      },
      "composed": {
        "preset": "governance",
        "header": "governance"
      },
      "checked": 2,
      "after": [
        {
          "id": "governance",
          "name": "fixture standard"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 6.218,
          "event": "own-apply"
        },
        {
          "sequence": 1,
          "ms": 6.271,
          "event": "own-apply-return"
        },
        {
          "sequence": 2,
          "ms": 6.777,
          "event": "background-task-start",
          "scheduler": "microtask"
        },
        {
          "sequence": 3,
          "ms": 7.986,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 4,
          "ms": 7.989,
          "event": "first-create-attempt",
          "requested": "governance"
        },
        {
          "sequence": 5,
          "ms": 8.075,
          "event": "own-root-settled"
        },
        {
          "sequence": 6,
          "ms": 8.196,
          "event": "admission-delay-enter"
        },
        {
          "sequence": 7,
          "ms": 8.198,
          "event": "root-settled"
        },
        {
          "sequence": 8,
          "ms": 8.731,
          "event": "first-create-failed",
          "error": "RemoteError: Unknown agent preset: governance",
          "code": "agent-preset/not-found"
        },
        {
          "sequence": 9,
          "ms": 8.77,
          "event": "admission-delay-leave"
        },
        {
          "sequence": 10,
          "ms": 8.771,
          "event": "register-start"
        },
        {
          "sequence": 11,
          "ms": 10,
          "event": "register-complete"
        },
        {
          "sequence": 12,
          "ms": 10.031,
          "event": "ready"
        },
        {
          "sequence": 13,
          "ms": 11.783,
          "event": "cleanup-start"
        },
        {
          "sequence": 14,
          "ms": 11.802,
          "event": "cleanup-complete"
        }
      ]
    },
    {
      "name": "admission-delay-default",
      "order": "last",
      "selected": "default",
      "rootDelay": false,
      "registrationDelay": false,
      "admissionDelay": true,
      "scheduler": "microtask",
      "preloadedCore": false,
      "brokenRegistration": false,
      "useBoot": false,
      "first": {
        "error": "RemoteError: Unknown agent preset: governance",
        "code": "agent-preset/not-found"
      },
      "composed": {
        "preset": "governance",
        "header": "governance"
      },
      "checked": 2,
      "after": [
        {
          "id": "governance",
          "name": "fixture standard"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 6.408,
          "event": "own-apply"
        },
        {
          "sequence": 1,
          "ms": 6.467,
          "event": "own-apply-return"
        },
        {
          "sequence": 2,
          "ms": 7.211,
          "event": "background-task-start",
          "scheduler": "microtask"
        },
        {
          "sequence": 3,
          "ms": 8.383,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 4,
          "ms": 8.386,
          "event": "first-create-attempt",
          "requested": "default"
        },
        {
          "sequence": 5,
          "ms": 8.47,
          "event": "own-root-settled"
        },
        {
          "sequence": 6,
          "ms": 8.561,
          "event": "admission-delay-enter"
        },
        {
          "sequence": 7,
          "ms": 8.563,
          "event": "root-settled"
        },
        {
          "sequence": 8,
          "ms": 9.949,
          "event": "first-create-failed",
          "error": "RemoteError: Unknown agent preset: governance",
          "code": "agent-preset/not-found"
        },
        {
          "sequence": 9,
          "ms": 9.975,
          "event": "admission-delay-leave"
        },
        {
          "sequence": 10,
          "ms": 9.976,
          "event": "register-start"
        },
        {
          "sequence": 11,
          "ms": 11.266,
          "event": "register-complete"
        },
        {
          "sequence": 12,
          "ms": 11.296,
          "event": "ready"
        },
        {
          "sequence": 13,
          "ms": 12.912,
          "event": "cleanup-start"
        },
        {
          "sequence": 14,
          "ms": 12.927,
          "event": "cleanup-complete"
        }
      ]
    },
    {
      "name": "root-delay",
      "order": "first",
      "selected": "governance",
      "rootDelay": true,
      "registrationDelay": false,
      "admissionDelay": false,
      "scheduler": "microtask",
      "preloadedCore": false,
      "brokenRegistration": false,
      "useBoot": false,
      "first": {
        "sessionId": "session-fc6dfe5e-12e2-45d6-96c0-c98229046e18",
        "agentPreset": "governance"
      },
      "composed": {
        "preset": "governance",
        "header": "governance"
      },
      "checked": 2,
      "after": [
        {
          "id": "governance",
          "name": "fixture standard"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 3.911,
          "event": "root-delay-enter"
        },
        {
          "sequence": 1,
          "ms": 6.368,
          "event": "own-apply"
        },
        {
          "sequence": 2,
          "ms": 6.418,
          "event": "own-apply-return"
        },
        {
          "sequence": 3,
          "ms": 6.933,
          "event": "background-task-start",
          "scheduler": "microtask"
        },
        {
          "sequence": 4,
          "ms": 7.146,
          "event": "root-delay-leave"
        },
        {
          "sequence": 5,
          "ms": 8.145,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 6,
          "ms": 8.148,
          "event": "first-create-attempt",
          "requested": "governance"
        },
        {
          "sequence": 7,
          "ms": 8.231,
          "event": "own-root-settled"
        },
        {
          "sequence": 8,
          "ms": 8.318,
          "event": "register-start"
        },
        {
          "sequence": 9,
          "ms": 8.414,
          "event": "root-settled"
        },
        {
          "sequence": 10,
          "ms": 9.397,
          "event": "register-complete"
        },
        {
          "sequence": 11,
          "ms": 9.426,
          "event": "ready"
        },
        {
          "sequence": 12,
          "ms": 10.721,
          "event": "first-create-complete",
          "sessionId": "session-fc6dfe5e-12e2-45d6-96c0-c98229046e18",
          "agentPreset": "governance"
        },
        {
          "sequence": 13,
          "ms": 12.24,
          "event": "cleanup-start"
        },
        {
          "sequence": 14,
          "ms": 12.25,
          "event": "cleanup-complete"
        }
      ]
    },
    {
      "name": "register-delay",
      "order": "first",
      "selected": "governance",
      "rootDelay": false,
      "registrationDelay": true,
      "admissionDelay": false,
      "scheduler": "microtask",
      "preloadedCore": false,
      "brokenRegistration": false,
      "useBoot": false,
      "first": {
        "sessionId": "session-d2075480-f774-4cf3-93ae-33e561c621ee",
        "agentPreset": "governance"
      },
      "composed": {
        "preset": "governance",
        "header": "governance"
      },
      "checked": 2,
      "after": [
        {
          "id": "governance",
          "name": "fixture standard"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 6.304,
          "event": "own-apply"
        },
        {
          "sequence": 1,
          "ms": 6.362,
          "event": "own-apply-return"
        },
        {
          "sequence": 2,
          "ms": 6.939,
          "event": "background-task-start",
          "scheduler": "microtask"
        },
        {
          "sequence": 3,
          "ms": 8.123,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 4,
          "ms": 8.126,
          "event": "first-create-attempt",
          "requested": "governance"
        },
        {
          "sequence": 5,
          "ms": 8.208,
          "event": "own-root-settled"
        },
        {
          "sequence": 6,
          "ms": 8.288,
          "event": "register-start"
        },
        {
          "sequence": 7,
          "ms": 8.392,
          "event": "root-settled"
        },
        {
          "sequence": 8,
          "ms": 9.27,
          "event": "mount-delay-enter"
        },
        {
          "sequence": 9,
          "ms": 9.41,
          "event": "mount-delay-leave"
        },
        {
          "sequence": 10,
          "ms": 9.524,
          "event": "register-complete"
        },
        {
          "sequence": 11,
          "ms": 9.553,
          "event": "ready"
        },
        {
          "sequence": 12,
          "ms": 11.789,
          "event": "first-create-complete",
          "sessionId": "session-d2075480-f774-4cf3-93ae-33e561c621ee",
          "agentPreset": "governance"
        },
        {
          "sequence": 13,
          "ms": 13.04,
          "event": "cleanup-start"
        },
        {
          "sequence": 14,
          "ms": 13.05,
          "event": "cleanup-complete"
        }
      ]
    },
    {
      "name": "unload-root-await",
      "order": "first",
      "selected": "governance",
      "rootDelay": true,
      "registrationDelay": false,
      "admissionDelay": false,
      "stopAt": "root",
      "scheduler": "microtask",
      "preloadedCore": false,
      "brokenRegistration": false,
      "useBoot": false,
      "first": {
        "error": "RemoteError: Unknown agent preset: governance",
        "code": "agent-preset/not-found"
      },
      "checked": 0,
      "after": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 3.708,
          "event": "root-delay-enter"
        },
        {
          "sequence": 1,
          "ms": 6.367,
          "event": "own-apply"
        },
        {
          "sequence": 2,
          "ms": 6.419,
          "event": "own-apply-return"
        },
        {
          "sequence": 3,
          "ms": 6.938,
          "event": "background-task-start",
          "scheduler": "microtask"
        },
        {
          "sequence": 4,
          "ms": 7.271,
          "event": "cleanup-start"
        },
        {
          "sequence": 5,
          "ms": 7.272,
          "event": "cleanup-complete"
        },
        {
          "sequence": 6,
          "ms": 8.221,
          "event": "root-delay-leave"
        },
        {
          "sequence": 7,
          "ms": 8.342,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 8,
          "ms": 8.345,
          "event": "first-create-attempt",
          "requested": "governance"
        },
        {
          "sequence": 9,
          "ms": 8.43,
          "event": "own-root-settled"
        },
        {
          "sequence": 10,
          "ms": 8.431,
          "event": "stopped-before-registration"
        },
        {
          "sequence": 11,
          "ms": 8.432,
          "event": "root-settled"
        },
        {
          "sequence": 12,
          "ms": 8.953,
          "event": "first-create-failed",
          "error": "RemoteError: Unknown agent preset: governance",
          "code": "agent-preset/not-found"
        }
      ]
    },
    {
      "name": "unload-register-flight",
      "order": "first",
      "selected": "governance",
      "rootDelay": false,
      "registrationDelay": true,
      "admissionDelay": false,
      "stopAt": "register",
      "scheduler": "microtask",
      "preloadedCore": false,
      "brokenRegistration": false,
      "useBoot": false,
      "first": {
        "error": "RemoteError: Unknown agent preset: governance",
        "code": "agent-preset/not-found"
      },
      "checked": 2,
      "after": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": true,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 6.259,
          "event": "own-apply"
        },
        {
          "sequence": 1,
          "ms": 6.31,
          "event": "own-apply-return"
        },
        {
          "sequence": 2,
          "ms": 6.833,
          "event": "background-task-start",
          "scheduler": "microtask"
        },
        {
          "sequence": 3,
          "ms": 8.016,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 4,
          "ms": 8.018,
          "event": "first-create-attempt",
          "requested": "governance"
        },
        {
          "sequence": 5,
          "ms": 8.094,
          "event": "own-root-settled"
        },
        {
          "sequence": 6,
          "ms": 8.17,
          "event": "register-start"
        },
        {
          "sequence": 7,
          "ms": 8.268,
          "event": "root-settled"
        },
        {
          "sequence": 8,
          "ms": 9.123,
          "event": "mount-delay-enter"
        },
        {
          "sequence": 9,
          "ms": 9.382,
          "event": "cleanup-start"
        },
        {
          "sequence": 10,
          "ms": 9.384,
          "event": "cleanup-complete"
        },
        {
          "sequence": 11,
          "ms": 9.534,
          "event": "mount-delay-leave"
        },
        {
          "sequence": 12,
          "ms": 9.624,
          "event": "register-complete"
        },
        {
          "sequence": 13,
          "ms": 10.233,
          "event": "late-register-disposed"
        },
        {
          "sequence": 14,
          "ms": 11.424,
          "event": "first-create-failed",
          "error": "RemoteError: Unknown agent preset: governance",
          "code": "agent-preset/not-found"
        }
      ]
    },
    {
      "name": "preloaded-first",
      "order": "first",
      "selected": "governance",
      "rootDelay": false,
      "registrationDelay": false,
      "admissionDelay": false,
      "scheduler": "microtask",
      "preloadedCore": true,
      "brokenRegistration": false,
      "useBoot": false,
      "first": {
        "sessionId": "session-3ff257e1-24c2-456f-ad2e-4a3b1cbd6f26",
        "agentPreset": "governance"
      },
      "composed": {
        "preset": "governance",
        "header": "governance"
      },
      "checked": 2,
      "after": [
        {
          "id": "governance",
          "name": "fixture standard"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 7.528,
          "event": "core-and-base-preloaded"
        },
        {
          "sequence": 1,
          "ms": 8.257,
          "event": "own-apply"
        },
        {
          "sequence": 2,
          "ms": 8.306,
          "event": "own-apply-return"
        },
        {
          "sequence": 3,
          "ms": 8.337,
          "event": "background-task-start",
          "scheduler": "microtask"
        },
        {
          "sequence": 4,
          "ms": 8.429,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 5,
          "ms": 8.43,
          "event": "first-create-attempt",
          "requested": "governance"
        },
        {
          "sequence": 6,
          "ms": 8.512,
          "event": "own-root-settled"
        },
        {
          "sequence": 7,
          "ms": 8.658,
          "event": "register-start"
        },
        {
          "sequence": 8,
          "ms": 9.59,
          "event": "root-settled"
        },
        {
          "sequence": 9,
          "ms": 9.789,
          "event": "register-complete"
        },
        {
          "sequence": 10,
          "ms": 9.817,
          "event": "ready"
        },
        {
          "sequence": 11,
          "ms": 11.287,
          "event": "first-create-complete",
          "sessionId": "session-3ff257e1-24c2-456f-ad2e-4a3b1cbd6f26",
          "agentPreset": "governance"
        },
        {
          "sequence": 12,
          "ms": 13.01,
          "event": "cleanup-start"
        },
        {
          "sequence": 13,
          "ms": 13.026,
          "event": "cleanup-complete"
        }
      ]
    },
    {
      "name": "preloaded-last",
      "order": "last",
      "selected": "governance",
      "rootDelay": false,
      "registrationDelay": false,
      "admissionDelay": false,
      "scheduler": "microtask",
      "preloadedCore": true,
      "brokenRegistration": false,
      "useBoot": false,
      "first": {
        "sessionId": "session-59884736-1574-40d7-8c12-d6cbceae2817",
        "agentPreset": "governance"
      },
      "composed": {
        "preset": "governance",
        "header": "governance"
      },
      "checked": 2,
      "after": [
        {
          "id": "governance",
          "name": "fixture standard"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 7.765,
          "event": "core-and-base-preloaded"
        },
        {
          "sequence": 1,
          "ms": 8.379,
          "event": "own-apply"
        },
        {
          "sequence": 2,
          "ms": 8.427,
          "event": "own-apply-return"
        },
        {
          "sequence": 3,
          "ms": 8.445,
          "event": "background-task-start",
          "scheduler": "microtask"
        },
        {
          "sequence": 4,
          "ms": 8.525,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 5,
          "ms": 8.526,
          "event": "first-create-attempt",
          "requested": "governance"
        },
        {
          "sequence": 6,
          "ms": 8.606,
          "event": "own-root-settled"
        },
        {
          "sequence": 7,
          "ms": 8.686,
          "event": "register-start"
        },
        {
          "sequence": 8,
          "ms": 9.545,
          "event": "root-settled"
        },
        {
          "sequence": 9,
          "ms": 9.747,
          "event": "register-complete"
        },
        {
          "sequence": 10,
          "ms": 9.775,
          "event": "ready"
        },
        {
          "sequence": 11,
          "ms": 12.247,
          "event": "first-create-complete",
          "sessionId": "session-59884736-1574-40d7-8c12-d6cbceae2817",
          "agentPreset": "governance"
        },
        {
          "sequence": 12,
          "ms": 13.767,
          "event": "cleanup-start"
        },
        {
          "sequence": 13,
          "ms": 13.779,
          "event": "cleanup-complete"
        }
      ]
    },
    {
      "name": "immediate-first",
      "order": "first",
      "selected": "governance",
      "rootDelay": false,
      "registrationDelay": false,
      "admissionDelay": false,
      "scheduler": "immediate",
      "preloadedCore": false,
      "brokenRegistration": false,
      "useBoot": false,
      "first": {
        "sessionId": "session-c486054e-a282-48a1-bc13-af14a29302f2",
        "agentPreset": "governance"
      },
      "composed": {
        "preset": "governance",
        "header": "governance"
      },
      "checked": 2,
      "after": [
        {
          "id": "governance",
          "name": "fixture standard"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 6.544,
          "event": "own-apply"
        },
        {
          "sequence": 1,
          "ms": 6.673,
          "event": "own-apply-return"
        },
        {
          "sequence": 2,
          "ms": 8.359,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 3,
          "ms": 8.362,
          "event": "first-create-attempt",
          "requested": "governance"
        },
        {
          "sequence": 4,
          "ms": 8.44,
          "event": "root-settled"
        },
        {
          "sequence": 5,
          "ms": 8.486,
          "event": "background-task-start",
          "scheduler": "immediate"
        },
        {
          "sequence": 6,
          "ms": 8.497,
          "event": "own-root-settled"
        },
        {
          "sequence": 7,
          "ms": 8.57,
          "event": "register-start"
        },
        {
          "sequence": 8,
          "ms": 9.598,
          "event": "register-complete"
        },
        {
          "sequence": 9,
          "ms": 9.627,
          "event": "ready"
        },
        {
          "sequence": 10,
          "ms": 11.011,
          "event": "first-create-complete",
          "sessionId": "session-c486054e-a282-48a1-bc13-af14a29302f2",
          "agentPreset": "governance"
        },
        {
          "sequence": 11,
          "ms": 12.732,
          "event": "cleanup-start"
        },
        {
          "sequence": 12,
          "ms": 12.745,
          "event": "cleanup-complete"
        }
      ]
    },
    {
      "name": "immediate-last-default",
      "order": "last",
      "selected": "default",
      "rootDelay": false,
      "registrationDelay": false,
      "admissionDelay": false,
      "scheduler": "immediate",
      "preloadedCore": false,
      "brokenRegistration": false,
      "useBoot": false,
      "first": {
        "sessionId": "session-b6ea9e31-4043-493e-a0af-4fe456bb96c1",
        "agentPreset": "governance"
      },
      "composed": {
        "preset": "governance",
        "header": "governance"
      },
      "checked": 2,
      "after": [
        {
          "id": "governance",
          "name": "fixture standard"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 6.985,
          "event": "own-apply"
        },
        {
          "sequence": 1,
          "ms": 7.06,
          "event": "own-apply-return"
        },
        {
          "sequence": 2,
          "ms": 8.697,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 3,
          "ms": 8.699,
          "event": "first-create-attempt",
          "requested": "default"
        },
        {
          "sequence": 4,
          "ms": 8.778,
          "event": "root-settled"
        },
        {
          "sequence": 5,
          "ms": 8.82,
          "event": "background-task-start",
          "scheduler": "immediate"
        },
        {
          "sequence": 6,
          "ms": 8.833,
          "event": "own-root-settled"
        },
        {
          "sequence": 7,
          "ms": 8.906,
          "event": "register-start"
        },
        {
          "sequence": 8,
          "ms": 10.056,
          "event": "register-complete"
        },
        {
          "sequence": 9,
          "ms": 10.088,
          "event": "ready"
        },
        {
          "sequence": 10,
          "ms": 13.597,
          "event": "first-create-complete",
          "sessionId": "session-b6ea9e31-4043-493e-a0af-4fe456bb96c1",
          "agentPreset": "governance"
        },
        {
          "sequence": 11,
          "ms": 15.249,
          "event": "cleanup-start"
        },
        {
          "sequence": 12,
          "ms": 15.26,
          "event": "cleanup-complete"
        }
      ]
    },
    {
      "name": "broken-registration",
      "order": "first",
      "selected": "governance",
      "rootDelay": false,
      "registrationDelay": false,
      "admissionDelay": false,
      "scheduler": "microtask",
      "preloadedCore": false,
      "brokenRegistration": true,
      "useBoot": false,
      "first": {
        "error": "RemoteError: broken-row (cordis:absent-probe-module): never started",
        "code": "agent-preset/invalid"
      },
      "checked": 2,
      "after": [
        {
          "id": "governance",
          "name": "fixture standard",
          "broken": "broken-row (cordis:absent-probe-module): never started"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 7.844,
          "event": "own-apply"
        },
        {
          "sequence": 1,
          "ms": 7.914,
          "event": "own-apply-return"
        },
        {
          "sequence": 2,
          "ms": 8.533,
          "event": "background-task-start",
          "scheduler": "microtask"
        },
        {
          "sequence": 3,
          "ms": 10.577,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 4,
          "ms": 10.58,
          "event": "first-create-attempt",
          "requested": "governance"
        },
        {
          "sequence": 5,
          "ms": 10.689,
          "event": "own-root-settled"
        },
        {
          "sequence": 6,
          "ms": 10.78,
          "event": "register-start"
        },
        {
          "sequence": 7,
          "ms": 10.922,
          "event": "root-settled"
        },
        {
          "sequence": 8,
          "ms": 12.898,
          "event": "register-complete"
        },
        {
          "sequence": 9,
          "ms": 13.415,
          "event": "startup-failed",
          "message": "AssertionError [ERR_ASSERTION]: Expected values to be strictly equal:\n+ actual - expected\n\n+ 'broken-row (cordis:absent-probe-module): never started'\n- undefined\n"
        },
        {
          "sequence": 10,
          "ms": 17.189,
          "event": "first-create-failed",
          "error": "RemoteError: broken-row (cordis:absent-probe-module): never started",
          "code": "agent-preset/invalid"
        },
        {
          "sequence": 11,
          "ms": 17.379,
          "event": "cleanup-start"
        },
        {
          "sequence": 12,
          "ms": 17.387,
          "event": "cleanup-complete"
        }
      ]
    },
    {
      "name": "actual-boot-microtask",
      "order": "first",
      "selected": "governance",
      "rootDelay": false,
      "registrationDelay": false,
      "admissionDelay": false,
      "scheduler": "microtask",
      "preloadedCore": false,
      "brokenRegistration": false,
      "useBoot": true,
      "bootRoster": [
        {
          "id": "governance",
          "name": "fixture standard"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "bootResolve": {
        "id": "governance"
      },
      "first": {
        "sessionId": "session-50938990-e36e-405d-a31c-bdc582f7ae7e",
        "agentPreset": "governance"
      },
      "composed": {
        "preset": "governance",
        "header": "governance"
      },
      "checked": 2,
      "after": [
        {
          "id": "governance",
          "name": "fixture standard"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 12.763,
          "event": "own-apply"
        },
        {
          "sequence": 1,
          "ms": 12.823,
          "event": "own-apply-return"
        },
        {
          "sequence": 2,
          "ms": 13.529,
          "event": "background-task-start",
          "scheduler": "microtask"
        },
        {
          "sequence": 3,
          "ms": 15.234,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 4,
          "ms": 15.237,
          "event": "first-create-attempt",
          "requested": "governance"
        },
        {
          "sequence": 5,
          "ms": 15.325,
          "event": "own-root-settled"
        },
        {
          "sequence": 6,
          "ms": 15.432,
          "event": "register-start"
        },
        {
          "sequence": 7,
          "ms": 17.14,
          "event": "actual-boot-return"
        },
        {
          "sequence": 8,
          "ms": 17.334,
          "event": "register-complete"
        },
        {
          "sequence": 9,
          "ms": 17.385,
          "event": "ready"
        },
        {
          "sequence": 10,
          "ms": 17.402,
          "event": "boot-roster-read",
          "ids": [
            "governance",
            "standard"
          ]
        },
        {
          "sequence": 11,
          "ms": 17.432,
          "event": "boot-governance-resolve",
          "id": "governance"
        },
        {
          "sequence": 12,
          "ms": 17.462,
          "event": "root-settled"
        },
        {
          "sequence": 13,
          "ms": 18.782,
          "event": "first-create-complete",
          "sessionId": "session-50938990-e36e-405d-a31c-bdc582f7ae7e",
          "agentPreset": "governance"
        },
        {
          "sequence": 14,
          "ms": 20.318,
          "event": "cleanup-start"
        },
        {
          "sequence": 15,
          "ms": 20.331,
          "event": "cleanup-complete"
        }
      ]
    },
    {
      "name": "actual-boot-immediate-default",
      "order": "first",
      "selected": "default",
      "rootDelay": false,
      "registrationDelay": false,
      "admissionDelay": false,
      "scheduler": "immediate",
      "preloadedCore": false,
      "brokenRegistration": false,
      "useBoot": true,
      "bootRoster": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "bootResolve": {
        "error": "RemoteError: Unknown agent preset: governance",
        "code": "agent-preset/not-found"
      },
      "first": {
        "sessionId": "session-b4861aa8-a8ae-4045-abff-8792556d5e7f",
        "agentPreset": "governance"
      },
      "composed": {
        "preset": "governance",
        "header": "governance"
      },
      "checked": 2,
      "after": [
        {
          "id": "governance",
          "name": "fixture standard"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 10.323,
          "event": "own-apply"
        },
        {
          "sequence": 1,
          "ms": 10.449,
          "event": "own-apply-return"
        },
        {
          "sequence": 2,
          "ms": 12.864,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 3,
          "ms": 12.867,
          "event": "first-create-attempt",
          "requested": "default"
        },
        {
          "sequence": 4,
          "ms": 13.066,
          "event": "actual-boot-return"
        },
        {
          "sequence": 5,
          "ms": 13.11,
          "event": "boot-roster-read",
          "ids": [
            "standard"
          ]
        },
        {
          "sequence": 6,
          "ms": 13.151,
          "event": "boot-governance-resolve-failed",
          "error": "RemoteError: Unknown agent preset: governance",
          "code": "agent-preset/not-found"
        },
        {
          "sequence": 7,
          "ms": 13.174,
          "event": "root-settled"
        },
        {
          "sequence": 8,
          "ms": 13.217,
          "event": "background-task-start",
          "scheduler": "immediate"
        },
        {
          "sequence": 9,
          "ms": 13.234,
          "event": "own-root-settled"
        },
        {
          "sequence": 10,
          "ms": 13.32,
          "event": "register-start"
        },
        {
          "sequence": 11,
          "ms": 14.631,
          "event": "register-complete"
        },
        {
          "sequence": 12,
          "ms": 14.66,
          "event": "ready"
        },
        {
          "sequence": 13,
          "ms": 15.981,
          "event": "first-create-complete",
          "sessionId": "session-b4861aa8-a8ae-4045-abff-8792556d5e7f",
          "agentPreset": "governance"
        },
        {
          "sequence": 14,
          "ms": 17.576,
          "event": "cleanup-start"
        },
        {
          "sequence": 15,
          "ms": 17.596,
          "event": "cleanup-complete"
        }
      ]
    },
    {
      "name": "actual-boot-admission-delay",
      "order": "first",
      "selected": "governance",
      "rootDelay": false,
      "registrationDelay": false,
      "admissionDelay": true,
      "scheduler": "microtask",
      "preloadedCore": false,
      "brokenRegistration": false,
      "useBoot": true,
      "bootRoster": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "bootResolve": {
        "error": "RemoteError: Unknown agent preset: governance",
        "code": "agent-preset/not-found"
      },
      "first": {
        "error": "RemoteError: Unknown agent preset: governance",
        "code": "agent-preset/not-found"
      },
      "composed": {
        "preset": "governance",
        "header": "governance"
      },
      "checked": 2,
      "after": [
        {
          "id": "governance",
          "name": "fixture standard"
        },
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "rosterAfterDispose": [
        {
          "id": "standard",
          "name": "fixture standard"
        }
      ],
      "lateDisposed": false,
      "listenerDisposed": true,
      "baseUnchanged": true,
      "events": [
        {
          "sequence": 0,
          "ms": 12.233,
          "event": "own-apply"
        },
        {
          "sequence": 1,
          "ms": 12.309,
          "event": "own-apply-return"
        },
        {
          "sequence": 2,
          "ms": 13.114,
          "event": "background-task-start",
          "scheduler": "microtask"
        },
        {
          "sequence": 3,
          "ms": 14.782,
          "event": "consumer-root-settled"
        },
        {
          "sequence": 4,
          "ms": 14.785,
          "event": "first-create-attempt",
          "requested": "governance"
        },
        {
          "sequence": 5,
          "ms": 14.877,
          "event": "own-root-settled"
        },
        {
          "sequence": 6,
          "ms": 14.982,
          "event": "admission-delay-enter"
        },
        {
          "sequence": 7,
          "ms": 15.089,
          "event": "actual-boot-return"
        },
        {
          "sequence": 8,
          "ms": 15.166,
          "event": "boot-roster-read",
          "ids": [
            "standard"
          ]
        },
        {
          "sequence": 9,
          "ms": 15.21,
          "event": "boot-governance-resolve-failed",
          "error": "RemoteError: Unknown agent preset: governance",
          "code": "agent-preset/not-found"
        },
        {
          "sequence": 10,
          "ms": 15.235,
          "event": "root-settled"
        },
        {
          "sequence": 11,
          "ms": 15.597,
          "event": "first-create-failed",
          "error": "RemoteError: Unknown agent preset: governance",
          "code": "agent-preset/not-found"
        },
        {
          "sequence": 12,
          "ms": 15.657,
          "event": "admission-delay-leave"
        },
        {
          "sequence": 13,
          "ms": 15.659,
          "event": "register-start"
        },
        {
          "sequence": 14,
          "ms": 17.184,
          "event": "register-complete"
        },
        {
          "sequence": 15,
          "ms": 17.22,
          "event": "ready"
        },
        {
          "sequence": 16,
          "ms": 19.178,
          "event": "cleanup-start"
        },
        {
          "sequence": 17,
          "ms": 19.194,
          "event": "cleanup-complete"
        }
      ]
    }
  ]
}
```

### 补齐附录后的静态核对

2026-10-17 补齐时仅读取存量结果，没有重跑宿主场景。嵌入 raw JSON 与存量 result.json 逐字一致，21 条审计记录、20 个场景、38 次 schema 及 headless 更正核对通过；`node --check docs/prototypes/dsh-native-feasibility.mjs` 和目标文件 `git diff --check` exit 0。未重跑完整 verify_workflow/manifest/cross-reference 门，均 NOT_RUN（仅原型/报告附录收口，无产品改动，不以此给产品合入授权）。补齐命令只读仓库和写本报告，不接触外部安装态或用户 HOME。
