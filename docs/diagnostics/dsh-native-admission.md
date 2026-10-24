# FEAT-102 S-A2 — 候选 L 公开 Loader 准入等待链证伪

日期：2026-10-17（Asia/Shanghai）。角色：Governance Developer；规范：`agents/governance-developer.md`、`skills/stage-infra/SKILL.md`。依据：修订设计 §5.1、Design R1 的 `S-A2_ONLY` 授权。

```text
candidate=L
execution_status=FAILED_CHECKPOINT_COMPLETE
conclusion=FAIL_CANDIDATE_L
authorized_slice=S-A2_ONLY
product_wiring_authorized=false
runtime_support=NOT_RUN
release_authorized=false
first_natural_lookup=FAIL_AGENT_PRESET_NOT_FOUND
own_activation_count=0
schema_checked=0
unhandled_rejections=0
```

## 关键结果与退出门

**候选 L 在第一个正常冷启动、插件行最前场景即失败。** 使用真实 app-boot.boot、Loader、native base 和 registry，插件声明公开注入 `{loader:{await:true},agentPresets:{}}`。实际 boot 返回时，公开状态显示 Loader 当前 tasks=0，include/core/registry/standard 全部 ACTIVE，唯独 own 为 PENDING（state=0）、inertia=false；其 apply 从未执行。随后立即固定参数 `governance` 调用真实 registry list/resolve，resolve 报 `agent-preset/not-found`。

这条失败没有 mount/admission barrier、没有人为延迟、没有先等自有 readiness、没有依赖 Web create 的 mkdir 等待，也没有触发故意 pending/broken 负例。父进程没有杀死子进程；场景没有 timeout；实际 root disposer 完成收敛，无未处理 rejection。exit 0 仅说明失败证据采集成功，不表示候选或产品通过。

按 R1 退出门立即停止候选扩展。随后只给**同一个失败场景**补充公开状态快照再采集一次，用于区分“任务已空但自己的 activation 尚未发生”；两次 raw 均保留。不执行 F/C/M、不更改产品，也不继续跑其它 L 场景。因此不得把 S-A detached cleanup PASS 继承成 L 的真实卸载 PASS。

最终采集时序（每个 ms 为该子场景起点的相对时间）：

| sequence | ms | 事件 |
| --- | --- | --- |
| 0 | 68.280 | actual-boot-return |
| 1 | 69.448 | public snapshot：loaderTasks=0，own PENDING/inertia=false，注入配置与 L 一致 |
| 2 | 70.225 | first-lookup-start，参数已固定为 governance |
| 3 | 71.299 | lookup continuation rejected：Unknown agent preset: governance |
| 4 | 71.982 | scenario-failed |
| 5 | 75.903 | root-drain-complete |

事件名 `boot-rejected` 来自原型对 `boot(...).then(firstLookup)` 整条 Promise 的 catch；**不是 app-boot.boot 本体拒绝**。raw 中 actual-boot-return 已先出现，失败源为后接的真实 lookup。报告保留原始名字，避免掩盖或重写时序。

## 公开因果链与事实边界

直接读取当前安装态源代码，SDK 根为本次 CLI manifest 下的 node_modules/@deepseek-ai：

1. Loader `EntryTree.getTasks`（lib/index.js:149–152）只取 entry 初始化 Promise 或 Fiber.inertia；没有将 PENDING 且无 inertia 的 Fiber 当成任务。`await`（:154–159）在集合为空时返回。
2. Loader `[Service.check]`（:647–649）在该依赖的 intercept.await=true 且 getTasks 非空时拒收该服务。类型公开说明它可使 dependent plugin 保持 PENDING。这与“该 dependent activation 一定在 boot 返回前完成”是两个命题。
3. Entry.init（:438–448）的 loader 通知是独立回调，并且仍受当时 getTasks 非空则返回的条件约束。公开 boot（dsh-app-boot :4080–4087）等待 Loader、审计，然后返回；审计对本探针 own 仅警告 optional pending，不将其视为必需的宿主核心服务。
4. 两次实测 raw：own 没进入 activation，真实 boot 已返回；第二次快照确认 getTasks=0、own PENDING/inertia=false、base ACTIVE。故此 L 接线未把自己的 admission/activation 成为 boot 的必要完成条件，第一条 lookup 没有登记保证。

第 1～3 项是 SOURCE；第 4 项是实测。未进一步证明“own 会永久 PENDING”或准确定位成宿主漏通知缺陷；checkpoint 后真实 root disposal 已终止该运行。也未用手动 reflect.notify、Entry.init、调整宿主行、重试 lookup、私有字段或为强制启动而扩展宿主启动路径来补救。候选失败足以返回设计复审，不需要先证明宿主本身有 bug。

原型中的有效 base 审计没有删除：预定位置为自身 activation 内、派生前，使用公开 `livePresetMounts`/`auditRows`；若 pending/failed 非空，拒绝自己且不调用可能 fallback-root 的 resolve。只有无 pending 的 base fixture 才调用公开 registry.resolve 做 broken 审计。本次 apply 未执行，所以该链、schema 校验及 register **均 NOT_RUN**；源码存在不能补填运行 PASS。

## A2-1～5 逐项裁定

| 验收门 | 结果 | 事实及未跑项 |
| --- | --- | --- |
| A2-1 等待链 | **FAIL** | 第一个正常冷启动最前行，boot 后 own 仍 PENDING、activationCount=0，首 lookup 失败。行末、预载、导入/嵌套延迟、自身 inertia 后重启均未扩展。 |
| A2-2 首次 consumer | **FAIL** | 真实 boot 后第一条真实 list/resolve 不含/不识别 governance。并行 Web 显式/default create、mount-delay、register 前 barrier 未执行；不靠 mkdir 抵销失败。 |
| A2-3 base/pending/broken | **NOT_RUN** | 快照证明 native standard Fiber ACTIVE，但它不替代 registry base audit。自身 activation 未发生，所有负例与覆盖/!!js/派生审计均未运行。 |
| A2-4 真实卸载/收敛 | **NOT_RUN** | register 飞行/派生 pending/候选 pending 卸载矩阵未运行；普通 root fixture disposer 的收敛不冒充这一门。没有手动调用 cleanup。 |
| A2-5 边界证据 | **部分完成；完整门 NOT_RUN** | same-context 路径、两条失败 raw、真实 SDK/退出码/0 rejection 已留存；schema=0、故意坏注册、完整 link/current-web/skills/refresh/tools 均未运行。 |

## 工具、隔离与修改范围

- 仅新建 `docs/prototypes/dsh-native-admission.mjs` 和本报告。旧 S-A 原型、报告及其失败 raw 保留。未修改 lib、产品配置、用户 profile 或治理账本；未提交。
- CLI manifest 是显式工具参数；通过它的 createRequire 选中所有 SDK 模块，并记录真实解析路径。没有给 repo 安装 host node_modules。Loader 公共 builtins 是 harness 工具注入，不是完整 link 安装证明。
- 真实 Cordis/Loader/native/registry/Session/AgentRegistry/AgentLoop/Web SessionController 模块均加载；本轮由于先行失败，后面的 Web/factory/preset compose 路径未执行。未使用 fake registry。
- 与 S-A 一样，仅不使用的文件上传/cold-query/workspace/attachments/fs IO 以最小 fixture 避免无关集成。完整 HTTP/UI/static inject 装配与 current-web profile 不在本切片，不声称通过。
- 运行前校验 sandbox 绝对路径精确等于 repo `.governance/sandboxes/feat102-a2`；DSH_HOME/TEMP/TMP/DSH_AGENTS_HOME 全部重定向至它。所有运行写入限定此处；安装 SDK 只读，用户卸载状态不变，不调用旧 writer，不删除/重建/移动 HOME 目录。
- 未配置模型 provider、未发送 followup、没有付费模型或网络监听。所有 timeout 只为失败收集/释放设置，本次首个正常失败没有用到 timeout。

## 可重放命令及静态核对

```powershell
$a2Sandbox = [IO.Path]::GetFullPath((Join-Path (Get-Location) '.governance/sandboxes/feat102-a2'))
$env:DSH_HOME = $a2Sandbox
$env:TEMP = $a2Sandbox
$env:TMP = $a2Sandbox
$env:DSH_AGENTS_HOME = $a2Sandbox
node docs/prototypes/dsh-native-admission.mjs 'C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json' $a2Sandbox
```

`node --check docs/prototypes/dsh-native-admission.mjs` exit 0。verify_workflow/manifest/cross-reference/full unit suite 未执行（仅 S-A2 原型与报告证伪，不是产品合入门）。原型实际只执行先行 normal-first，失败立即停止；其余名字记录为 NOT_RUN，不把未实现/未执行的矩阵分支视作测试覆盖。

## Coordinator 写回建议

- Proposed evidence：候选 L 首个正常冷启动最前行两次观测失败；实际 boot 返回、Loader tasks=0、own PENDING/activation=0，首个固定 governance lookup not-found；schema=0、后续矩阵 NOT_RUN、0 unhandled、真实 root drain 完成。引用本报告内嵌 raw 与逐条审计。
- Proposed decision：S-A2 失败，退回同 Design Reviewer，S-B～F、产品运行支持与发布/重装继续未授权。后续 F/C 必须另作明确审查范围，不在本切片替换方案。
- Proposed risk：Loader await intercept 是 dependent PENDING 门，当前接线未成为 boot 等待 own admission 的保证；不能将 gate 开关存在等同无环/可见性已解决。责任 Design Reviewer/Developer，截止产品接线准入前。
- 本 Agent 未写治理账本；Coordinator 负责机录与释放 FEAT-102 两文件锁。

## 命令逐条审计与两次原始结果

以下保留两个独立 worker 命令的原始 UTC/exit/read/write 路径以及所有 raw 事件。第二次仅增加公开状态快照，没有更改 L 注入/activation/准入逻辑。外部只读命令另列；仓库内纯读取和报告写入不属于外部 SDK 命令。

### 外部命令审计（7 条，含父命令与两个独立 worker）

开始 UTC 来自命令当时打印或 worker spawn 前的 Date.toISOString；exit 为实际进程完成码。父命令与 worker 是包含关系，单列便于 R4 逐条留痕，不能将它们误计为四次场景运行。三次源码只读没有启动额外 DSH。

```json
[
  {
    "id": "A2-RO-01",
    "started": "2026-10-17T00:09:25.0643183Z",
    "cmd": "$a2Started=[DateTime]::UtcNow.ToString('o'); $a2Sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$a2Sdk/cordis-plugin-loader/lib/index.js\" | Select-Object -Skip 360 -First 100; Get-Content -Encoding UTF8 \"$a2Sdk/cordis-plugin-loader/lib/index.js\" | Select-Object -Skip 635 -First 22; Get-Content -Encoding UTF8 \"$a2Sdk/cordis/lib/index.js\" | Select-Object -Skip 1280 -First 126; Get-Content -Encoding UTF8 \"$a2Sdk/cordis/lib/types/registry.d.ts\" | Select-Object -First 45; Write-Output \"A2-RO-01 started=$a2Started access=read-only paths=$a2Sdk\"",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "impact_write": [],
    "access": "installed SDK source read-only; no host process/profile reads or writes"
  },
  {
    "id": "A2-RO-02",
    "started": "2026-10-17T00:10:16.5018825Z",
    "cmd": "$a2Started=[DateTime]::UtcNow.ToString('o'); $a2Sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n 'async function mountRootInclude|function mountRootInclude|bootstrapIncludes.set|loader.create|loader.root.create' \"$a2Sdk/dsh-app-boot/lib/index.js\"; Get-Content -Encoding UTF8 \"$a2Sdk/cordis-plugin-loader/lib/index.js\" | Select-Object -Skip 435 -First 58; Get-Content -Encoding UTF8 \"$a2Sdk/cordis-plugin-loader/lib/index.js\" | Select-Object -Skip 140 -First 22; Write-Output \"A2-RO-02 started=$a2Started access=read-only paths=$a2Sdk\"",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "impact_write": [],
    "access": "installed SDK source read-only; no host process/profile reads or writes"
  },
  {
    "id": "A2-RO-03",
    "started": "2026-10-17T00:10:26.1642177Z",
    "cmd": "$a2Started=[DateTime]::UtcNow.ToString('o'); $a2Sdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$a2Sdk/dsh-app-boot/lib/index.js\" | Select-Object -Skip 3680 -First 60; Get-Content -Encoding UTF8 \"$a2Sdk/cordis-plugin-loader/lib/index.js\" | Select-Object -Skip 295 -First 69; Write-Output \"A2-RO-03 started=$a2Started access=read-only paths=$a2Sdk\"",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "impact_write": [],
    "access": "installed SDK source read-only; no host process/profile reads or writes"
  },
  {
    "id": "A2-SHELL-01",
    "started": "2026-10-17T00:08:46.7553611Z",
    "cmd": "$a2Started=[DateTime]::UtcNow.ToString('o'); $a2Sandbox=[IO.Path]::GetFullPath((Join-Path (Get-Location) '.governance/sandboxes/feat102-a2')); if ($a2Sandbox -ne 'D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a2') { throw 'unexpected sandbox' }; New-Item -ItemType Directory -Force -Path $a2Sandbox | Out-Null; $env:DSH_HOME=$a2Sandbox; $env:TEMP=$a2Sandbox; $env:TMP=$a2Sandbox; $env:DSH_AGENTS_HOME=$a2Sandbox; node docs/prototypes/dsh-native-admission.mjs 'C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json' $a2Sandbox; $a2Code=$LASTEXITCODE; Write-Output \"A2-SHELL-01 started=$a2Started exit=$a2Code access=SDK-readonly,sandbox-runtime-write paths=$a2Sandbox\"; exit $a2Code",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json",
      "docs/prototypes/dsh-native-admission.mjs"
    ],
    "impact_write": [
      "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/feat102-a2"
    ],
    "access": "SDK read-only; validated sandbox runtime writes; no real HOME/profile install"
  },
  {
    "id": "A2-SHELL-02",
    "started": "2026-10-17T00:09:57.4321292Z",
    "cmd": "$a2Started=[DateTime]::UtcNow.ToString('o'); $a2Sandbox=[IO.Path]::GetFullPath((Join-Path (Get-Location) '.governance/sandboxes/feat102-a2')); if ($a2Sandbox -ne 'D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a2') { throw 'unexpected sandbox' }; $env:DSH_HOME=$a2Sandbox; $env:TEMP=$a2Sandbox; $env:TMP=$a2Sandbox; $env:DSH_AGENTS_HOME=$a2Sandbox; node docs/prototypes/dsh-native-admission.mjs 'C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json' $a2Sandbox; $a2Code=$LASTEXITCODE; Write-Output \"A2-SHELL-02 started=$a2Started exit=$a2Code access=SDK-readonly,sandbox-runtime-write paths=$a2Sandbox\"; exit $a2Code",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json",
      "docs/prototypes/dsh-native-admission.mjs"
    ],
    "impact_write": [
      "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/feat102-a2"
    ],
    "access": "SDK read-only; validated sandbox runtime writes; no real HOME/profile install"
  },
  {
    "id": "A2-WORKER-01",
    "executable": "C:\\Program Files\\nodejs\\node.exe",
    "args": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\docs\\prototypes\\dsh-native-admission.mjs",
      "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\package.json",
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a2",
      "--worker",
      "normal-first"
    ],
    "started": "2026-10-17T00:08:47.018Z",
    "impact_read": [
      "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\package.json",
      "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh"
    ],
    "impact_write": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a2"
    ],
    "access": "SDK read-only; runtime writes only validated task sandbox; no network/model provider/profile installation",
    "exit_code": 0,
    "signal": null,
    "killed": false,
    "stdout": "{\"name\":\"normal-first\",\"conclusion\":\"FAIL_NORMAL_WAIT_CHAIN\",\"activationCount\":0,\"checked\":0}\n",
    "stderr": "feat102-a2: warning: 1 entry did not activate\nown (cordis:own): pending (waiting for services: unknown)\n",
    "completed": "2026-10-17T00:08:48.079Z",
    "original_raw_id": "A2-RUN-01"
  },
  {
    "id": "A2-WORKER-02",
    "executable": "C:\\Program Files\\nodejs\\node.exe",
    "args": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\docs\\prototypes\\dsh-native-admission.mjs",
      "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\package.json",
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a2",
      "--worker",
      "normal-first"
    ],
    "started": "2026-10-17T00:09:57.629Z",
    "impact_read": [
      "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\package.json",
      "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh"
    ],
    "impact_write": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a2"
    ],
    "access": "SDK read-only; runtime writes only validated task sandbox; no network/model provider/profile installation",
    "exit_code": 0,
    "signal": null,
    "killed": false,
    "stdout": "{\"name\":\"normal-first\",\"conclusion\":\"FAIL_NORMAL_WAIT_CHAIN\",\"activationCount\":0,\"checked\":0}\n",
    "stderr": "feat102-a2: warning: 1 entry did not activate\nown (cordis:own): pending (waiting for services: unknown)\n",
    "completed": "2026-10-17T00:09:58.472Z",
    "original_raw_id": "A2-RUN-01"
  }
]
```

### 首次失败原文

来源：`.governance/sandboxes/feat102-a2/result-initial.json`；SHA-256 `37b6416a0eaa85625023e5d1301828e1519a48682b8d25535d75974541aca573`。逐事件时间为相对场景起点 ms，绝非伪造 UTC。

```json
{
  "candidate": "L",
  "authorizedSlice": "S-A2_ONLY",
  "productWiringAuthorized": false,
  "commands": [
    {
      "id": "A2-RUN-01",
      "executable": "C:\\Program Files\\nodejs\\node.exe",
      "args": [
        "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\docs\\prototypes\\dsh-native-admission.mjs",
        "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\package.json",
        "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a2",
        "--worker",
        "normal-first"
      ],
      "started": "2026-10-17T00:08:47.018Z",
      "impact_read": [
        "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\package.json",
        "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh"
      ],
      "impact_write": [
        "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a2"
      ],
      "access": "SDK read-only; runtime writes only validated task sandbox; no network/model provider/profile installation",
      "exit_code": 0,
      "signal": null,
      "killed": false,
      "stdout": "{\"name\":\"normal-first\",\"conclusion\":\"FAIL_NORMAL_WAIT_CHAIN\",\"activationCount\":0,\"checked\":0}\n",
      "stderr": "feat102-a2: warning: 1 entry did not activate\nown (cordis:own): pending (waiting for services: unknown)\n",
      "completed": "2026-10-17T00:08:48.079Z"
    }
  ],
  "results": [
    {
      "name": "normal-first",
      "candidate": "L",
      "conclusion": "FAIL_NORMAL_WAIT_CHAIN",
      "context": {
        "cliManifest": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\package.json",
        "cli": "0.2.0-rc.2",
        "node": "v24.13.1",
        "sandbox": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a2",
        "repository": "D:\\AI\\agent\\claude\\coding\\project_management_workflow",
        "repositoryHasHostNodeModules": false,
        "resolved": {
          "@deepseek-ai/cordis": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis\\lib\\index.js",
          "@deepseek-ai/cordis-plugin-loader": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis-plugin-loader\\lib\\index.js",
          "@deepseek-ai/dsh-agent-preset-registry": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent-preset-registry\\lib\\index.js",
          "@deepseek-ai/dsh-agent-preset": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent-preset\\lib\\index.js",
          "@deepseek-ai/dsh-app-boot": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-app-boot\\lib\\index.js",
          "@deepseek-ai/dsh-api-session-controller": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-api-session-controller\\lib\\index.js",
          "@deepseek-ai/dsh-persona": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-persona\\lib\\index.js",
          "@deepseek-ai/dsh-skill-filesystem": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-skill-filesystem\\lib\\index.js",
          "@deepseek-ai/dsh-session-projection": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-session-projection\\lib\\index.js",
          "@deepseek-ai/dsh-session": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-session\\lib\\index.js",
          "@deepseek-ai/dsh-agent": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent\\lib\\index.js",
          "@deepseek-ai/dsh-llm": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-llm\\lib\\index.js",
          "@deepseek-ai/dsh-tools": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-tools\\lib\\index.js",
          "@deepseek-ai/dsh-system-prompt": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-system-prompt\\lib\\index.js",
          "@deepseek-ai/dsh-skill": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-skill\\lib\\index.js",
          "@deepseek-ai/dsh-typert-registry": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-typert-registry\\lib\\index.js",
          "@deepseek-ai/dsh-agent-default-model": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent-default-model\\lib\\index.js",
          "@deepseek-ai/dsh-agent-loop": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent-loop\\lib\\index.js"
        }
      },
      "inject": {
        "loader": {
          "await": true
        },
        "agentPresets": {}
      },
      "events": [
        {
          "sequence": 0,
          "ms": 77.24,
          "event": "actual-boot-return"
        },
        {
          "sequence": 1,
          "ms": 88.309,
          "event": "first-lookup-start",
          "requested": "governance"
        },
        {
          "sequence": 2,
          "ms": 89.628,
          "event": "boot-rejected",
          "error": "RemoteError: Unknown agent preset: governance"
        },
        {
          "sequence": 3,
          "ms": 90.4,
          "event": "scenario-failed",
          "error": "RemoteError: Unknown agent preset: governance"
        },
        {
          "sequence": 4,
          "ms": 94.236,
          "event": "root-drain-complete"
        }
      ],
      "unhandled": [],
      "checked": 0,
      "activationCount": 0,
      "firstRoster": [
        {
          "id": "standard"
        }
      ],
      "error": "RemoteError: Unknown agent preset: governance"
    }
  ],
  "notRun": [
    "unload-register-flight",
    "normal-last",
    "preloaded-first",
    "mount-delay",
    "pre-register-delay",
    "base-pending",
    "broken-registration"
  ],
  "conclusion": "FAIL_CANDIDATE_L"
}
```

### 仅补充公开状态快照后的失败原文

来源：`.governance/sandboxes/feat102-a2/result.json`；SHA-256 `8dcb66eb0d5da86be792c45d2fc6e7430b199d4fdbd4beb808eb404b03657cd5`。逐事件时间为相对场景起点 ms，绝非伪造 UTC。

```json
{
  "candidate": "L",
  "authorizedSlice": "S-A2_ONLY",
  "productWiringAuthorized": false,
  "commands": [
    {
      "id": "A2-RUN-01",
      "executable": "C:\\Program Files\\nodejs\\node.exe",
      "args": [
        "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\docs\\prototypes\\dsh-native-admission.mjs",
        "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\package.json",
        "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a2",
        "--worker",
        "normal-first"
      ],
      "started": "2026-10-17T00:09:57.629Z",
      "impact_read": [
        "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\package.json",
        "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh"
      ],
      "impact_write": [
        "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a2"
      ],
      "access": "SDK read-only; runtime writes only validated task sandbox; no network/model provider/profile installation",
      "exit_code": 0,
      "signal": null,
      "killed": false,
      "stdout": "{\"name\":\"normal-first\",\"conclusion\":\"FAIL_NORMAL_WAIT_CHAIN\",\"activationCount\":0,\"checked\":0}\n",
      "stderr": "feat102-a2: warning: 1 entry did not activate\nown (cordis:own): pending (waiting for services: unknown)\n",
      "completed": "2026-10-17T00:09:58.472Z"
    }
  ],
  "results": [
    {
      "name": "normal-first",
      "candidate": "L",
      "conclusion": "FAIL_NORMAL_WAIT_CHAIN",
      "context": {
        "cliManifest": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\package.json",
        "cli": "0.2.0-rc.2",
        "node": "v24.13.1",
        "sandbox": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a2",
        "repository": "D:\\AI\\agent\\claude\\coding\\project_management_workflow",
        "repositoryHasHostNodeModules": false,
        "resolved": {
          "@deepseek-ai/cordis": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis\\lib\\index.js",
          "@deepseek-ai/cordis-plugin-loader": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis-plugin-loader\\lib\\index.js",
          "@deepseek-ai/dsh-agent-preset-registry": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent-preset-registry\\lib\\index.js",
          "@deepseek-ai/dsh-agent-preset": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent-preset\\lib\\index.js",
          "@deepseek-ai/dsh-app-boot": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-app-boot\\lib\\index.js",
          "@deepseek-ai/dsh-api-session-controller": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-api-session-controller\\lib\\index.js",
          "@deepseek-ai/dsh-persona": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-persona\\lib\\index.js",
          "@deepseek-ai/dsh-skill-filesystem": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-skill-filesystem\\lib\\index.js",
          "@deepseek-ai/dsh-session-projection": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-session-projection\\lib\\index.js",
          "@deepseek-ai/dsh-session": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-session\\lib\\index.js",
          "@deepseek-ai/dsh-agent": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent\\lib\\index.js",
          "@deepseek-ai/dsh-llm": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-llm\\lib\\index.js",
          "@deepseek-ai/dsh-tools": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-tools\\lib\\index.js",
          "@deepseek-ai/dsh-system-prompt": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-system-prompt\\lib\\index.js",
          "@deepseek-ai/dsh-skill": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-skill\\lib\\index.js",
          "@deepseek-ai/dsh-typert-registry": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-typert-registry\\lib\\index.js",
          "@deepseek-ai/dsh-agent-default-model": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent-default-model\\lib\\index.js",
          "@deepseek-ai/dsh-agent-loop": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent-loop\\lib\\index.js"
        }
      },
      "inject": {
        "loader": {
          "await": true
        },
        "agentPresets": {}
      },
      "events": [
        {
          "sequence": 0,
          "ms": 68.28,
          "event": "actual-boot-return"
        },
        {
          "sequence": 1,
          "ms": 69.448,
          "event": "boot-public-state-snapshot",
          "loaderTasks": 0,
          "own": {
            "id": "own",
            "module": "cordis:own",
            "state": 0,
            "inertia": false,
            "inject": {
              "loader": {
                "await": true
              },
              "agentPresets": {}
            }
          }
        },
        {
          "sequence": 2,
          "ms": 70.225,
          "event": "first-lookup-start",
          "requested": "governance"
        },
        {
          "sequence": 3,
          "ms": 71.299,
          "event": "boot-rejected",
          "error": "RemoteError: Unknown agent preset: governance"
        },
        {
          "sequence": 4,
          "ms": 71.982,
          "event": "scenario-failed",
          "error": "RemoteError: Unknown agent preset: governance"
        },
        {
          "sequence": 5,
          "ms": 75.903,
          "event": "root-drain-complete"
        }
      ],
      "unhandled": [],
      "checked": 0,
      "activationCount": 0,
      "bootLoaderTaskCount": 0,
      "bootEntries": [
        {
          "id": "include",
          "module": "cordis:include",
          "state": 2,
          "inertia": false
        },
        {
          "id": "own",
          "module": "cordis:own",
          "state": 0,
          "inertia": false,
          "inject": {
            "loader": {
              "await": true
            },
            "agentPresets": {}
          }
        },
        {
          "id": "core-projections",
          "module": "cordis:projections",
          "state": 2,
          "inertia": false
        },
        {
          "id": "core-sessions",
          "module": "cordis:sessions",
          "state": 2,
          "inertia": false
        },
        {
          "id": "core-agents",
          "module": "cordis:agents",
          "state": 2,
          "inertia": false
        },
        {
          "id": "core-llm",
          "module": "cordis:llm",
          "state": 2,
          "inertia": false
        },
        {
          "id": "core-tools",
          "module": "cordis:tools",
          "state": 2,
          "inertia": false
        },
        {
          "id": "core-prompt",
          "module": "cordis:prompt",
          "state": 2,
          "inertia": false
        },
        {
          "id": "core-skills",
          "module": "cordis:skills",
          "state": 2,
          "inertia": false
        },
        {
          "id": "core-typert",
          "module": "cordis:typert",
          "state": 2,
          "inertia": false
        },
        {
          "id": "model",
          "module": "cordis:defaultModel",
          "state": 2,
          "inertia": false
        },
        {
          "id": "loop",
          "module": "cordis:loop",
          "state": 2,
          "inertia": false
        },
        {
          "id": "registry",
          "module": "cordis:registry",
          "state": 2,
          "inertia": false
        },
        {
          "id": "io",
          "module": "cordis:io",
          "state": 2,
          "inertia": false
        },
        {
          "id": "web",
          "module": "cordis:web",
          "state": 2,
          "inertia": false
        },
        {
          "id": "standard",
          "module": "cordis:native",
          "state": 2,
          "inertia": false
        }
      ],
      "firstRoster": [
        {
          "id": "standard"
        }
      ],
      "error": "RemoteError: Unknown agent preset: governance"
    }
  ],
  "notRun": [
    "unload-register-flight",
    "normal-last",
    "preloaded-first",
    "mount-delay",
    "pre-register-delay",
    "base-pending",
    "broken-registration"
  ],
  "conclusion": "FAIL_CANDIDATE_L"
}
```
