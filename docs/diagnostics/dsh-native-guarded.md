# FEAT-102 S-A3 — G 原型：正常准入通过，permit 后取消门失败

日期：2026-10-18（Asia/Shanghai）。角色：Governance Developer；规范：`agents/governance-developer.md`、`skills/stage-infra/SKILL.md`。输入：设计 §14、独立 Design R2；仅有 `S-A3_G_ONLY / PROTOTYPE_ONLY` 许可。S-A/S-A2 历史失败不改写。

```text
candidate=G
execution_status=FAILED_CHECKPOINT_COMPLETE
conclusion=FAIL_CANCELLED_RECORD_PENDING_WHILE_MOUNT_IN_FLIGHT
natural_cold_start=PASS_FIXTURE_ONLY
cancel_after_permit=FAIL
product_wiring_authorized=false
runtime_support=NOT_RUN
release_authorized=false
scenarios_executed=2
schema_checked=6
unhandled_rejections=0
```

## 结果与退出门

G 在第一条自然冷启动最前行的有限 fixture 中通过：真实 parent Group.data 完整输入被克隆，经同一 Loader tree.import 得到 native Config/公开 resolveConfig；own activation 内调用 register 建立 record，立即返回 cleanup，不等 register/mount。standing guard 在 host settle 后比较 accepted Fiber.config/seed、检查普通 standard 无 broken，再提供隔离 readiness。真正的 payload Group.inject 在 permit 前未运行任何 payload；放行后真实 tool/prompt/skill sentinel 各登记一次，真实首 lookup 和显式/default Web compose 成功。

**第二条 permit 已放行、register 仍在 flight 的取消安全门失败，已停止 G。** 真实 own Fiber.dispose 和 cleanup 在 payload mount barrier 释放前完成，但随后真实 `registry.resolve('governance')` 在 barrier 仍持有时无法返回 invalid/broken；750ms 有界观察到期，记录 FAIL。只有失败后才释放 barrier 完成 drain；没有把超时释放当成功等待、没有先释放屏障帮助 cleanup，也没有继续跑其它场景掩盖此失败。

这里观察到的是取消的记录仍挂在 `record.ready` 上，**不是观察到取消后成功创建 Agent、READY 或数据损坏**。局部 readiness 撤回和 generation cancel 没有使新 lookup 立即得到合同要求的 invalid。该失败足以触发 R2 退出门，不能只以“最终 late-dispose 清理了”抵销。

## 正常场景的最小证据

SDK 为 0.2.0-rc.2，Node v24.13.1；repo 无 host node_modules。宿主实际 boot 的 root Include 里，own 地址 `include:own`、parent `include`。记录 treeBase、全部 parent group 行、normalized seed、accepted base、derived wrapper 和安装态工具解析路径。

| sequence | 相对 ms | 正常 normal-first 事件 |
| --- | --- | --- |
| 0～2 | 664.248～669.856 | own activation；克隆 parent.data seed；同 tree native/cordis import 与真实 schema完成 |
| 3～4 | 671.307～672.379 | register-start；own-activation-return |
| 5～8 | 683.942～689.674 | own activation settled；standing guard 开始；host settled；accepted base及broken审核通过 |
| 9 | 690.389 | permit-release：payload apply/tool/prompt/skill 全为0 |
| 10～12 | 691.291～692.978 | 私有ready提供；实际boot返回；首条固定governance lookup开始 |
| 13～17 | 695.656～700.492 | payload apply及真实tool/prompt/skill登记；register完成 |
| 18～20 | 701.549～714.522 | 首lookup完成；两个真实Web Agent compose；此后才记录READY |
| 21～25 | 715.276～732.486 | 真实own dispose请求/cleanup/完成；root drain完成 |

正常首 lookup 没等自有 READY，先于 payload/register 完成；等待来自宿主 registry 的 record.ready。该次显式/default Web create 在真实 lookup 完成后调用，两者用 Promise.all 同时创建，未等待本插件 READY。它不是完整 HTTP/UI 或所有初始入口通过。

payload probe 真正调用 scoped `tools.register`、`systemPrompt.section`、`skills.register`；计数在真实注册后增长，不仅是 guard 日志。工具从未执行、技能正文未读取、没有模型调用。这三个 probe 是隔离验收 instrumentation，不是拟交付的额外产品 tool/skill。

wrapper 是显式原型合同增量：外层 `spg-frame` literal Group 仅隔离本包 readiness 服务；同层 guard 与**依赖 readiness 的 payload Group**是兄弟，原 vendor rows 全放后者内。payload 没与 guard 直接并列。readiness 未放行时 payload Group 自身 PENDING，不构造其 children；业务字段仅改 prefix 和两个 roots。不能把整个结构仍称为“两字段变化”。

正常场景检查 root ctx 读不到 readiness、standard accepted config 前后相同、governance disposer撤回自身登记且保留 standard；未知 scope、既有 vendor isolate/相对地址表达式完整保真和并行非治理会话尚未验收。

## 取消失败原始时序与公开因果

第二条调用改为实际 boot 返回后同时启动真实 list/resolve 和显式/default Web create；harness 不先等 READY。payload 的受控 barrier 位于真正已放行的 payload Group 内，让 register 保持 flight；不是 register 前额外 admission 延迟。

| sequence | 相对 ms | cancel-permitted-flight 事件 |
| --- | --- | --- |
| 9～12 | 559.846～561.786 | 零副作用快照后permit放行；实际boot返回；首lookup开始 |
| 13～17 | 564.387～567.576 | payload apply/tool/prompt/skill真实发生；payload mount barrier进入，register尚未完成 |
| 18～21 | 568.560～571.620 | 真实own Fiber.dispose请求；cleanup取消permit/generation并撤回ready；cleanup与dispose均完成 |
| 22 | 572.128 | barrier仍持有，开始新的真实 post-cancel resolve(governance) |
| 23 | 1326.826 | `TIMEOUT cancelled record invalid before barrier release`，判FAIL |
| 24 | 1327.876 | 失败处理释放屏障后的 payload barrier leave |
| 25～26 | 1332.012～1332.539 | register完成；迟到disposer立即执行 |
| 27～28 | 1333.753～1334.589 | teardown期间consumer rejection被消费；root drain完成 |

raw 没有单独的 barrier-release 事件；代码 catch 在 sequence23 记录FAIL后释放各屏障，sequence24才出现 barrier-leave。报告明确此观测缺口，不补造历史事件。750ms 是失败观测期限，绝不是“允许等完即PASS”。

安装态只读源码支持如下等待链：

1. registry.register 先写 record，但**只有 await record.ready 后才返回 unregister disposer**（dsh-agent-preset-registry lib/index.js:500～523）。当前原型 own 没等此 Promise，因此 cleanup可以先完成；也因此 register flight 时尚未拿到自有 unregister。
2. mount 的 auditRows 先等 standing tree.await，再逐行等 Fiber.await（:197～221）。受控的 payload activation 仍在 flight，撤回 readiness 不等于这个已经进入 activation 的 payload Promise完成。
3. registry diagnostic 在查看 broken/pending 前先 await record.ready（:557起）；resolve 调用 diagnostic（:602起）。本轮真实 post-cancel lookup因此仍被未完成mount挡住，无法在barrier保持时得到invalid。
4. 失败后释放barrier，mount/register才结束，迟到disposer能够清理。**最终清理成功不能替代取消窗口内的拒收/无pending合同**。

未读取私有 definitions/_config；原型没有提前返回的虚构 unregister API，也没有修改宿主表或源码。该结果不证明“所有可能的 G 修订都不可实现”，但当前受审的 G 接线没有通过取消硬门，必须返回同 Reviewer。

本轮直接核查的公开 `register(definition)` 接线只在激活完成后返回异步 disposer；当前实现没有接收 AbortSignal，也没有在 activation 完成前交付撤销/abort handle。因此**这个 register 方法本身**没有给当前原型一个可在 flight 窗口立即撤回 record 的公开原语。这里没有推断宿主其它所有公开协议都无解、宿主存在 bug 或记录会永久挂死；下一步协议选择由同 Reviewer 评估，不在本切片改接线。

第二场景最后的 `consumer-rejected` 为 `TypeError: Cannot read properties of undefined (reading 'resolve')`：失败释放/drain时root服务已拆除，原harness list→resolve continuation仍在收敛。该错误已消费，0 unhandled。它属于 teardown instrumentation 限制，**不是 invalid的证据，也不是主失败根因**。主失败在更早的sequence23已确定；没有为修饰它而重跑/修改失败raw。

## 六门裁定及未跑范围

| 门 | 本轮结果 |
| --- | --- |
| A3-0 seed/context | 有限normal-first PASS：真实Group.data、same-tree native Config/resolveConfig、normalized与accepted相等；行末/未知Include/dynamic拒收及跨scope矩阵NOT_RUN。 |
| A3-1 admitted/lookup | 正常首lookup及显式/default Web compose有限PASS；真实record.ready等待可见。SDK import暂停、独立audit/mount延迟完整矩阵NOT_RUN。 |
| A3-2 accepted/真正gate | 正常accepted+无broken、permit前四类副作用0、permit后真实注册有限PASS；raw更新失败、旧Fiber、缺失/重复/disabled/broken/pending/seed差异拒收矩阵NOT_RUN，不能以源码存在补PASS。 |
| A3-3 cancel/dispose | **FAIL**：真实own卸载及时完成，但permit已放行register仍flight时，取消记录仍pending，post-cancel消费者不能在barrier保持时得到invalid。其它audit/host/import窗口NOT_RUN，import有界失败不补成卸载PASS。 |
| A3-4 isolation/fidelity | 正常root readiness不泄漏、standard config保持、真实payload schema非零（每场3次，合计6）有限PASS；相对路径/地址、复杂isolate、非治理并行会话、故意坏注册、缺state/stale nonce等完整矩阵NOT_RUN。 |
| A3-5 exit/evidence | 已按首个安全硬门FAIL保存raw并停止G；不转C/F/H，不接产品。记录两场景、6 schema、0 unhandled及每条命令；完整link/current-web/HTTP/UI/实际skills/热刷新/工具参数/发布均NOT_RUN。 |

## 范围、重放及治理建议

仅新建 `docs/prototypes/dsh-native-guarded.mjs` 和本报告；运行产物仅仓库 `.governance/sandboxes/feat102-a3`。DSH_HOME/TEMP/TMP/DSH_AGENTS_HOME均重定向并校验绝对目录；SDK只读、不重装、不 repair 用户profile、不写/删/重建/移动 HOME、不触碰暂停 FIX-444/445、不提交或改治理账本。

manifest是工具参数，宿主fixture模块通过它解析；**own native/cordis校验实际经当前Loader tree.import**，native模块对象与已记录同安装context参考对象相同。该证据仍不是完整link安装或真实产品入口通过。IO fixture沿用S-A，只替代不用的上传/cold-query/workspace/attachments/fs集成；registry/Loader/native/Session/AgentLoop/Web consumer是真实实现。

```powershell
$gSandbox = [IO.Path]::GetFullPath((Join-Path (Get-Location) '.governance/sandboxes/feat102-a3'))
$env:DSH_HOME=$gSandbox; $env:TEMP=$gSandbox; $env:TMP=$gSandbox; $env:DSH_AGENTS_HOME=$gSandbox
node docs/prototypes/dsh-native-guarded.mjs 'C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json' $gSandbox normal-first
node docs/prototypes/dsh-native-guarded.mjs 'C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json' $gSandbox cancel-permitted-flight
```

两个命令 exit 0只表示完成采集，第二个明确FAIL。第一场之后，harness调整为boot后同时发真实lookup与Web请求，并添加post-cancel invalid观察；没有改G的seed/guard/register/cancel实现。故报告分别披露两次consumer顺序，未伪称相同原型版本全量回归。`node --check`通过；产品verify_workflow/manifest/cross-reference/full suite未跑，也不能用于产品合入授权。

Proposed evidence：S-A3 G有限自然启动通过，但permit后/register-flight真实取消无invalid，750ms观测FAIL；2场景/6schema/0unhandled、真实cleanup先于release、late-dispose及raw局限均披露。

Proposed decision/risk：G已触发退出门，回同Design Reviewer；产品接线/支持/发布/重装继续未授权。风险是尚未取得disposer时无法在取消窗口及时将record标invalid/撤回，最终清理不是准入拒收保证。Coordinator机录并释放FEAT-102锁，本Agent不做最终产品决策。

## 原始命令审计与两场景raw

附录内嵌逐条真实UTC/exit/read-write路径及完整场景JSON。相对事件ms不冒充UTC；SOURCE不冒充运行PASS，未跑项不补造。

### 7 条外部/隔离命令审计

三个SOURCE命令、两个父shell和两个实际Node调用。父shell与Node是包含关系，只运行两场景；时间为当次打印或进程现场采集。

```json
[
  {
    "id": "G-RO-01",
    "started": "2026-10-18T12:19:20.5650628Z",
    "cmd": "$gStarted=[DateTime]::UtcNow.ToString('o'); $gSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n -A 24 'register\\(|registerProvider\\(|section\\(|registerTool\\(' \"$gSdk/dsh-tools/lib/types/index.d.ts\" \"$gSdk/dsh-skill/lib/types/index.d.ts\" \"$gSdk/dsh-system-prompt/lib/types/index.d.ts\" | Select-Object -First 160; Get-Content -Encoding UTF8 \"$gSdk/cordis-plugin-loader/lib/types/config/group.d.ts\" | Select-Object -First 45; Write-Output \"G-RO-01 started=$gStarted access=SDK-readonly paths=$gSdk\"",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "impact_write": [],
    "access": "SDK source read-only; no host/profile runtime or writes"
  },
  {
    "id": "G-RO-02",
    "started": "2026-10-18T12:19:43.9162215Z",
    "cmd": "$gStarted=[DateTime]::UtcNow.ToString('o'); $gSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; rg -n 'interface ToolDefinition|type ToolDefinition|defineContentToolFixture|interface SkillDefinition|interface SkillSummary' \"$gSdk/dsh-tools/lib/types/index.d.ts\" \"$gSdk/dsh-skill/lib/types/index.d.ts\"; Get-Content -Encoding UTF8 \"$gSdk/dsh-skill/lib/types/index.d.ts\" | Select-Object -First 85; Get-Content -Encoding UTF8 \"$gSdk/dsh-tools/lib/types/index.d.ts\" | Select-Object -Skip 45 -First 110; Write-Output \"G-RO-02 started=$gStarted access=SDK-readonly paths=$gSdk\"",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "impact_write": [],
    "access": "SDK source read-only; no host/profile runtime or writes"
  },
  {
    "id": "G-RO-03",
    "started": "2026-10-18T12:24:17.8183868Z",
    "cmd": "$gStarted=[DateTime]::UtcNow.ToString('o'); $gSdk='C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai'; Get-Content -Encoding UTF8 \"$gSdk/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 190 -First 35; Get-Content -Encoding UTF8 \"$gSdk/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 498 -First 73; Get-Content -Encoding UTF8 \"$gSdk/dsh-agent-preset-registry/lib/index.js\" | Select-Object -Skip 595 -First 22; Write-Output \"G-RO-03 started=$gStarted access=SDK-readonly paths=$gSdk\"",
    "exit_code": 0,
    "impact_read": [
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai"
    ],
    "impact_write": [],
    "access": "SDK source read-only; no host/profile runtime or writes"
  },
  {
    "id": "G-SHELL-01",
    "started": "2026-10-18T12:22:06.5819168Z",
    "cmd": "$gStarted=[DateTime]::UtcNow.ToString('o'); $gSandbox=[IO.Path]::GetFullPath((Join-Path (Get-Location) '.governance/sandboxes/feat102-a3')); if ($gSandbox -ne 'D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3') { throw 'unexpected sandbox' }; New-Item -ItemType Directory -Force -Path $gSandbox | Out-Null; $env:DSH_HOME=$gSandbox; $env:TEMP=$gSandbox; $env:TMP=$gSandbox; $env:DSH_AGENTS_HOME=$gSandbox; node docs/prototypes/dsh-native-guarded.mjs 'C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json' $gSandbox normal-first; $gCode=$LASTEXITCODE; Write-Output \"G-SHELL-01 started=$gStarted exit=$gCode access=SDK-readonly,sandbox-runtime-write paths=$gSandbox\"; exit $gCode",
    "exit_code": 0,
    "impact_read": [
      "docs/prototypes/dsh-native-guarded.mjs",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json"
    ],
    "impact_write": [
      "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/feat102-a3"
    ],
    "access": "SDK read-only; validated sandbox runtime writes; no user profile install/network/model calls"
  },
  {
    "id": "G-SHELL-02",
    "started": "2026-10-18T12:23:27.5006217Z",
    "cmd": "$gStarted=[DateTime]::UtcNow.ToString('o'); $gSandbox=[IO.Path]::GetFullPath((Join-Path (Get-Location) '.governance/sandboxes/feat102-a3')); if ($gSandbox -ne 'D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3') { throw 'unexpected sandbox' }; $env:DSH_HOME=$gSandbox; $env:TEMP=$gSandbox; $env:TMP=$gSandbox; $env:DSH_AGENTS_HOME=$gSandbox; node docs/prototypes/dsh-native-guarded.mjs 'C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json' $gSandbox cancel-permitted-flight; $gCode=$LASTEXITCODE; Write-Output \"G-SHELL-02 started=$gStarted exit=$gCode access=SDK-readonly,sandbox-runtime-write paths=$gSandbox\"; exit $gCode",
    "exit_code": 0,
    "impact_read": [
      "docs/prototypes/dsh-native-guarded.mjs",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/node_modules/@deepseek-ai",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json"
    ],
    "impact_write": [
      "D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/feat102-a3"
    ],
    "access": "SDK read-only; validated sandbox runtime writes; no user profile install/network/model calls"
  },
  {
    "id": "G-NODE-01",
    "started": "2026-10-18T12:22:06.829Z",
    "checkpoint_completed": "2026-10-18T12:22:07.565Z",
    "exit_code": 0,
    "executable": "C:\\Program Files\\nodejs\\node.exe",
    "args": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\docs\\prototypes\\dsh-native-guarded.mjs",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json",
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3",
      "normal-first"
    ],
    "impact_read": [
      "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\package.json",
      "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh",
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\docs\\prototypes\\dsh-native-guarded.mjs"
    ],
    "impact_write": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3"
    ],
    "access": "SDK read-only; all runtime writes task sandbox; no profile install/network/paid model"
  },
  {
    "id": "G-NODE-02",
    "started": "2026-10-18T12:23:27.733Z",
    "checkpoint_completed": "2026-10-18T12:23:29.070Z",
    "exit_code": 0,
    "executable": "C:\\Program Files\\nodejs\\node.exe",
    "args": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\docs\\prototypes\\dsh-native-guarded.mjs",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json",
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3",
      "cancel-permitted-flight"
    ],
    "impact_read": [
      "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\package.json",
      "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh",
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\docs\\prototypes\\dsh-native-guarded.mjs"
    ],
    "impact_write": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3"
    ],
    "access": "SDK read-only; all runtime writes task sandbox; no profile install/network/paid model"
  }
]
```

### normal-first 完整raw

来源：`.governance/sandboxes/feat102-a3/normal-first.json`；SHA-256 `24e4e84fafcda6786c9c416013e31f9bb8bf0629a778ca96e05a031ab76448e0`。

```json
{
  "candidate": "G",
  "slice": "S-A3_G_ONLY",
  "scenario": "normal-first",
  "conclusion": "PASS_FIXTURE_ONLY_REVIEW_REQUIRED",
  "productWiringAuthorized": false,
  "started": "2026-10-18T12:22:06.829Z",
  "command": {
    "executable": "C:\\Program Files\\nodejs\\node.exe",
    "args": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\docs\\prototypes\\dsh-native-guarded.mjs",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json",
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3",
      "normal-first"
    ],
    "impact_read": [
      "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\package.json",
      "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh",
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\docs\\prototypes\\dsh-native-guarded.mjs"
    ],
    "impact_write": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3"
    ],
    "access": "SDK read-only; all runtime writes task sandbox; no profile install/network/paid model"
  },
  "context": {
    "cliManifest": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\package.json",
    "cli": "0.2.0-rc.2",
    "node": "v24.13.1",
    "repositoryHasHostNodeModules": false,
    "resolved": {
      "@deepseek-ai/dsh-app-boot": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-app-boot\\lib\\index.js",
      "@deepseek-ai/cordis": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis\\lib\\index.js",
      "@deepseek-ai/cordis-plugin-loader": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis-plugin-loader\\lib\\index.js",
      "@deepseek-ai/dsh-agent-preset-registry": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent-preset-registry\\lib\\index.js",
      "@deepseek-ai/dsh-api-session-controller": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-api-session-controller\\lib\\index.js",
      "@deepseek-ai/dsh-persona": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-persona\\lib\\index.js",
      "@deepseek-ai/dsh-skill-filesystem": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-skill-filesystem\\lib\\index.js",
      "@deepseek-ai/dsh-agent-preset": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent-preset\\lib\\index.js",
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
  "events": [
    {
      "sequence": 0,
      "ms": 664.248,
      "event": "own-activation-start"
    },
    {
      "sequence": 1,
      "ms": 665.254,
      "event": "seed-copied",
      "sourceAddress": "include/standard"
    },
    {
      "sequence": 2,
      "ms": 669.856,
      "event": "sdk-import-and-native-schema-complete"
    },
    {
      "sequence": 3,
      "ms": 671.307,
      "event": "register-start"
    },
    {
      "sequence": 4,
      "ms": 672.379,
      "event": "own-activation-return"
    },
    {
      "sequence": 5,
      "ms": 683.942,
      "event": "audit-own-activation-settled"
    },
    {
      "sequence": 6,
      "ms": 685.902,
      "event": "guard-enter",
      "generationId": "16e61512-4ae5-4557-aeae-d627551d4b5b"
    },
    {
      "sequence": 7,
      "ms": 687.661,
      "event": "audit-host-settled"
    },
    {
      "sequence": 8,
      "ms": 689.674,
      "event": "accepted-base-audit-passed"
    },
    {
      "sequence": 9,
      "ms": 690.389,
      "event": "permit-release",
      "payloadBefore": {
        "apply": 0,
        "tool": 0,
        "prompt": 0,
        "skill": 0
      }
    },
    {
      "sequence": 10,
      "ms": 691.291,
      "event": "guard-permit-provided"
    },
    {
      "sequence": 11,
      "ms": 691.977,
      "event": "actual-boot-return"
    },
    {
      "sequence": 12,
      "ms": 692.978,
      "event": "first-lookup-start",
      "requested": "governance"
    },
    {
      "sequence": 13,
      "ms": 695.656,
      "event": "payload-apply"
    },
    {
      "sequence": 14,
      "ms": 697.155,
      "event": "payload-tool-registered"
    },
    {
      "sequence": 15,
      "ms": 698.086,
      "event": "payload-prompt-registered"
    },
    {
      "sequence": 16,
      "ms": 699.144,
      "event": "payload-skill-registered"
    },
    {
      "sequence": 17,
      "ms": 700.492,
      "event": "register-complete"
    },
    {
      "sequence": 18,
      "ms": 701.549,
      "event": "first-lookup-complete",
      "id": "governance"
    },
    {
      "sequence": 19,
      "ms": 713.832,
      "event": "web-compose-complete"
    },
    {
      "sequence": 20,
      "ms": 714.522,
      "event": "ready"
    },
    {
      "sequence": 21,
      "ms": 715.276,
      "event": "dispose-request"
    },
    {
      "sequence": 22,
      "ms": 716.378,
      "event": "cleanup-start"
    },
    {
      "sequence": 23,
      "ms": 718.781,
      "event": "cleanup-complete"
    },
    {
      "sequence": 24,
      "ms": 719.925,
      "event": "dispose-complete"
    },
    {
      "sequence": 25,
      "ms": 732.486,
      "event": "root-drain-complete"
    }
  ],
  "unhandled": [],
  "schemaChecked": 3,
  "ownActivations": 1,
  "permit": true,
  "payload": {
    "apply": 1,
    "tool": 1,
    "prompt": 1,
    "skill": 1
  },
  "cleanupComplete": true,
  "source": {
    "parentAddress": "include",
    "treeBase": "file:///D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/feat102-a3/",
    "ownAddress": "include:own",
    "groupRows": [
      {
        "id": "own",
        "name": "cordis:own"
      },
      {
        "id": "core-projections",
        "name": "cordis:projections"
      },
      {
        "id": "core-sessions",
        "name": "cordis:sessions"
      },
      {
        "id": "core-agents",
        "name": "cordis:agents"
      },
      {
        "id": "core-llm",
        "name": "cordis:llm"
      },
      {
        "id": "core-tools",
        "name": "cordis:tools"
      },
      {
        "id": "core-prompt",
        "name": "cordis:prompt"
      },
      {
        "id": "core-skills",
        "name": "cordis:skills"
      },
      {
        "id": "core-typert",
        "name": "cordis:typert"
      },
      {
        "id": "model",
        "name": "cordis:defaultModel"
      },
      {
        "id": "loop",
        "name": "cordis:loop"
      },
      {
        "id": "registry",
        "name": "cordis:registry"
      },
      {
        "id": "io",
        "name": "cordis:io"
      },
      {
        "id": "web",
        "name": "cordis:web"
      },
      {
        "id": "standard",
        "name": "@deepseek-ai/dsh-agent-preset"
      }
    ],
    "scopeLimit": "direct native declarations and complete literal groups; fixture core whitelist; unknown Include/dynamic source rejected",
    "nativeModuleName": "@deepseek-ai/dsh-agent-preset",
    "nativeSchemaSameInstalledContext": true
  },
  "normalizedSeed": {
    "id": "standard",
    "plugins": [
      {
        "id": "persona",
        "name": "cordis:persona",
        "config": {
          "prefix": "USER PREFIX",
          "suffix": "USER SUFFIX",
          "includeRuntimeContext": false
        }
      },
      {
        "id": "skills",
        "name": "cordis:filesystem",
        "config": {
          "customSkillDirs": [
            "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3\\user-skills"
          ],
          "includeDefaultRoots": false,
          "watch": false,
          "agentsHome": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3"
        }
      },
      {
        "id": "literal",
        "name": "cordis:group",
        "group": true,
        "config": [
          {
            "id": "disabled",
            "name": "cordis:disabledSentinel",
            "disabled": {
              "__jsExpr": "true"
            }
          }
        ]
      }
    ]
  },
  "derived": {
    "id": "governance",
    "plugins": [
      {
        "id": "spg-frame",
        "name": "cordis:group",
        "group": true,
        "isolate": {
          "spgPrototypeReady": true
        },
        "config": [
          {
            "id": "spg-guard",
            "name": "cordis:guard",
            "config": {
              "generationId": "16e61512-4ae5-4557-aeae-d627551d4b5b"
            }
          },
          {
            "id": "spg-payload",
            "name": "cordis:group",
            "group": true,
            "inject": {
              "spgPrototypeReady": {}
            },
            "config": [
              {
                "id": "persona",
                "name": "cordis:persona",
                "config": {
                  "prefix": "USER PREFIX\nGOVERNANCE PROBE",
                  "suffix": "USER SUFFIX",
                  "includeRuntimeContext": false
                }
              },
              {
                "id": "skills",
                "name": "cordis:filesystem",
                "config": {
                  "customSkillDirs": [
                    "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3\\user-skills",
                    "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\skills",
                    "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\adapters\\dsh\\skill-shims"
                  ],
                  "includeDefaultRoots": false,
                  "watch": false,
                  "agentsHome": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3"
                }
              },
              {
                "id": "literal",
                "name": "cordis:group",
                "group": true,
                "config": [
                  {
                    "id": "disabled",
                    "name": "cordis:disabledSentinel",
                    "disabled": {
                      "__jsExpr": "true"
                    }
                  }
                ]
              },
              {
                "id": "payload-probe",
                "name": "cordis:payloadProbe"
              }
            ]
          }
        ]
      }
    ]
  },
  "acceptedBase": {
    "id": "standard",
    "plugins": [
      {
        "id": "persona",
        "name": "cordis:persona",
        "config": {
          "prefix": "USER PREFIX",
          "suffix": "USER SUFFIX",
          "includeRuntimeContext": false
        }
      },
      {
        "id": "skills",
        "name": "cordis:filesystem",
        "config": {
          "customSkillDirs": [
            "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3\\user-skills"
          ],
          "includeDefaultRoots": false,
          "watch": false,
          "agentsHome": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3"
        }
      },
      {
        "id": "literal",
        "name": "cordis:group",
        "group": true,
        "config": [
          {
            "id": "disabled",
            "name": "cordis:disabledSentinel",
            "disabled": {
              "__jsExpr": "true"
            }
          }
        ]
      }
    ]
  },
  "roster": [
    {
      "id": "governance"
    },
    {
      "id": "standard"
    }
  ],
  "lookup": {
    "id": "governance"
  },
  "created": [
    {
      "sessionId": "session-a14cf698-5bbb-49f4-aff1-e47c76066061",
      "agentPreset": "governance"
    },
    {
      "sessionId": "session-1fdc25fd-5d5d-48cb-9cd5-b678533b4b84",
      "agentPreset": "governance"
    }
  ],
  "afterDispose": [
    {
      "id": "standard"
    }
  ],
  "completed": "2026-10-18T12:22:07.565Z",
  "exit_code": 0
}
```

### cancel-permitted-flight 完整raw

来源：`.governance/sandboxes/feat102-a3/cancel-permitted-flight.json`；SHA-256 `09ba2f1c9e8eb4a086507f0e7e5d86dc256f388d0bbd9a4e2d5c5e6e6b9cc025`。

```json
{
  "candidate": "G",
  "slice": "S-A3_G_ONLY",
  "scenario": "cancel-permitted-flight",
  "conclusion": "FAIL_G_CHECKPOINT",
  "productWiringAuthorized": false,
  "started": "2026-10-18T12:23:27.733Z",
  "command": {
    "executable": "C:\\Program Files\\nodejs\\node.exe",
    "args": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\docs\\prototypes\\dsh-native-guarded.mjs",
      "C:/Users/peter/AppData/Roaming/npm/node_modules/@deepseek-ai/dsh/package.json",
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3",
      "cancel-permitted-flight"
    ],
    "impact_read": [
      "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\package.json",
      "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh",
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\docs\\prototypes\\dsh-native-guarded.mjs"
    ],
    "impact_write": [
      "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3"
    ],
    "access": "SDK read-only; all runtime writes task sandbox; no profile install/network/paid model"
  },
  "context": {
    "cliManifest": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\package.json",
    "cli": "0.2.0-rc.2",
    "node": "v24.13.1",
    "repositoryHasHostNodeModules": false,
    "resolved": {
      "@deepseek-ai/dsh-app-boot": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-app-boot\\lib\\index.js",
      "@deepseek-ai/cordis": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis\\lib\\index.js",
      "@deepseek-ai/cordis-plugin-loader": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\cordis-plugin-loader\\lib\\index.js",
      "@deepseek-ai/dsh-agent-preset-registry": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent-preset-registry\\lib\\index.js",
      "@deepseek-ai/dsh-api-session-controller": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-api-session-controller\\lib\\index.js",
      "@deepseek-ai/dsh-persona": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-persona\\lib\\index.js",
      "@deepseek-ai/dsh-skill-filesystem": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-skill-filesystem\\lib\\index.js",
      "@deepseek-ai/dsh-agent-preset": "C:\\Users\\peter\\AppData\\Roaming\\npm\\node_modules\\@deepseek-ai\\dsh\\node_modules\\@deepseek-ai\\dsh-agent-preset\\lib\\index.js",
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
  "events": [
    {
      "sequence": 0,
      "ms": 538.575,
      "event": "own-activation-start"
    },
    {
      "sequence": 1,
      "ms": 539.522,
      "event": "seed-copied",
      "sourceAddress": "include/standard"
    },
    {
      "sequence": 2,
      "ms": 543.318,
      "event": "sdk-import-and-native-schema-complete"
    },
    {
      "sequence": 3,
      "ms": 544.428,
      "event": "register-start"
    },
    {
      "sequence": 4,
      "ms": 545.185,
      "event": "own-activation-return"
    },
    {
      "sequence": 5,
      "ms": 554.412,
      "event": "audit-own-activation-settled"
    },
    {
      "sequence": 6,
      "ms": 555.889,
      "event": "guard-enter",
      "generationId": "3235c886-2f7b-45b5-ac57-90e09d745145"
    },
    {
      "sequence": 7,
      "ms": 557.153,
      "event": "audit-host-settled"
    },
    {
      "sequence": 8,
      "ms": 559.248,
      "event": "accepted-base-audit-passed"
    },
    {
      "sequence": 9,
      "ms": 559.846,
      "event": "permit-release",
      "payloadBefore": {
        "apply": 0,
        "tool": 0,
        "prompt": 0,
        "skill": 0
      }
    },
    {
      "sequence": 10,
      "ms": 560.629,
      "event": "guard-permit-provided"
    },
    {
      "sequence": 11,
      "ms": 561.103,
      "event": "actual-boot-return"
    },
    {
      "sequence": 12,
      "ms": 561.786,
      "event": "first-lookup-start",
      "requested": "governance"
    },
    {
      "sequence": 13,
      "ms": 564.387,
      "event": "payload-apply"
    },
    {
      "sequence": 14,
      "ms": 565.428,
      "event": "payload-tool-registered"
    },
    {
      "sequence": 15,
      "ms": 566.102,
      "event": "payload-prompt-registered"
    },
    {
      "sequence": 16,
      "ms": 566.906,
      "event": "payload-skill-registered"
    },
    {
      "sequence": 17,
      "ms": 567.576,
      "event": "payload-flight-barrier-enter"
    },
    {
      "sequence": 18,
      "ms": 568.56,
      "event": "dispose-request"
    },
    {
      "sequence": 19,
      "ms": 569.469,
      "event": "cleanup-start"
    },
    {
      "sequence": 20,
      "ms": 570.168,
      "event": "cleanup-complete"
    },
    {
      "sequence": 21,
      "ms": 571.62,
      "event": "dispose-complete"
    },
    {
      "sequence": 22,
      "ms": 572.128,
      "event": "post-cancel-lookup-start",
      "requested": "governance",
      "barrierStillHeld": true
    },
    {
      "sequence": 23,
      "ms": 1326.826,
      "event": "scenario-failed",
      "error": "Error: TIMEOUT cancelled record invalid before barrier release"
    },
    {
      "sequence": 24,
      "ms": 1327.876,
      "event": "payload-flight-barrier-leave"
    },
    {
      "sequence": 25,
      "ms": 1332.012,
      "event": "register-complete"
    },
    {
      "sequence": 26,
      "ms": 1332.539,
      "event": "late-dispose"
    },
    {
      "sequence": 27,
      "ms": 1333.753,
      "event": "consumer-rejected",
      "error": "TypeError: Cannot read properties of undefined (reading 'resolve')"
    },
    {
      "sequence": 28,
      "ms": 1334.589,
      "event": "root-drain-complete"
    }
  ],
  "unhandled": [],
  "schemaChecked": 3,
  "ownActivations": 1,
  "permit": true,
  "payload": {
    "apply": 1,
    "tool": 1,
    "prompt": 1,
    "skill": 1
  },
  "cleanupComplete": true,
  "source": {
    "parentAddress": "include",
    "treeBase": "file:///D:/AI/agent/claude/coding/project_management_workflow/.governance/sandboxes/feat102-a3/",
    "ownAddress": "include:own",
    "groupRows": [
      {
        "id": "own",
        "name": "cordis:own"
      },
      {
        "id": "core-projections",
        "name": "cordis:projections"
      },
      {
        "id": "core-sessions",
        "name": "cordis:sessions"
      },
      {
        "id": "core-agents",
        "name": "cordis:agents"
      },
      {
        "id": "core-llm",
        "name": "cordis:llm"
      },
      {
        "id": "core-tools",
        "name": "cordis:tools"
      },
      {
        "id": "core-prompt",
        "name": "cordis:prompt"
      },
      {
        "id": "core-skills",
        "name": "cordis:skills"
      },
      {
        "id": "core-typert",
        "name": "cordis:typert"
      },
      {
        "id": "model",
        "name": "cordis:defaultModel"
      },
      {
        "id": "loop",
        "name": "cordis:loop"
      },
      {
        "id": "registry",
        "name": "cordis:registry"
      },
      {
        "id": "io",
        "name": "cordis:io"
      },
      {
        "id": "web",
        "name": "cordis:web"
      },
      {
        "id": "standard",
        "name": "@deepseek-ai/dsh-agent-preset"
      }
    ],
    "scopeLimit": "direct native declarations and complete literal groups; fixture core whitelist; unknown Include/dynamic source rejected",
    "nativeModuleName": "@deepseek-ai/dsh-agent-preset",
    "nativeSchemaSameInstalledContext": true
  },
  "normalizedSeed": {
    "id": "standard",
    "plugins": [
      {
        "id": "persona",
        "name": "cordis:persona",
        "config": {
          "prefix": "USER PREFIX",
          "suffix": "USER SUFFIX",
          "includeRuntimeContext": false
        }
      },
      {
        "id": "skills",
        "name": "cordis:filesystem",
        "config": {
          "customSkillDirs": [
            "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3\\user-skills"
          ],
          "includeDefaultRoots": false,
          "watch": false,
          "agentsHome": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3"
        }
      },
      {
        "id": "literal",
        "name": "cordis:group",
        "group": true,
        "config": [
          {
            "id": "disabled",
            "name": "cordis:disabledSentinel",
            "disabled": {
              "__jsExpr": "true"
            }
          }
        ]
      }
    ]
  },
  "derived": {
    "id": "governance",
    "plugins": [
      {
        "id": "spg-frame",
        "name": "cordis:group",
        "group": true,
        "isolate": {
          "spgPrototypeReady": true
        },
        "config": [
          {
            "id": "spg-guard",
            "name": "cordis:guard",
            "config": {
              "generationId": "3235c886-2f7b-45b5-ac57-90e09d745145"
            }
          },
          {
            "id": "spg-payload",
            "name": "cordis:group",
            "group": true,
            "inject": {
              "spgPrototypeReady": {}
            },
            "config": [
              {
                "id": "persona",
                "name": "cordis:persona",
                "config": {
                  "prefix": "USER PREFIX\nGOVERNANCE PROBE",
                  "suffix": "USER SUFFIX",
                  "includeRuntimeContext": false
                }
              },
              {
                "id": "skills",
                "name": "cordis:filesystem",
                "config": {
                  "customSkillDirs": [
                    "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3\\user-skills",
                    "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\skills",
                    "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\adapters\\dsh\\skill-shims"
                  ],
                  "includeDefaultRoots": false,
                  "watch": false,
                  "agentsHome": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3"
                }
              },
              {
                "id": "literal",
                "name": "cordis:group",
                "group": true,
                "config": [
                  {
                    "id": "disabled",
                    "name": "cordis:disabledSentinel",
                    "disabled": {
                      "__jsExpr": "true"
                    }
                  }
                ]
              },
              {
                "id": "payload-probe",
                "name": "cordis:payloadProbe"
              },
              {
                "id": "payload-barrier",
                "name": "cordis:payloadBarrier"
              }
            ]
          }
        ]
      }
    ]
  },
  "acceptedBase": {
    "id": "standard",
    "plugins": [
      {
        "id": "persona",
        "name": "cordis:persona",
        "config": {
          "prefix": "USER PREFIX",
          "suffix": "USER SUFFIX",
          "includeRuntimeContext": false
        }
      },
      {
        "id": "skills",
        "name": "cordis:filesystem",
        "config": {
          "customSkillDirs": [
            "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3\\user-skills"
          ],
          "includeDefaultRoots": false,
          "watch": false,
          "agentsHome": "D:\\AI\\agent\\claude\\coding\\project_management_workflow\\.governance\\sandboxes\\feat102-a3"
        }
      },
      {
        "id": "literal",
        "name": "cordis:group",
        "group": true,
        "config": [
          {
            "id": "disabled",
            "name": "cordis:disabledSentinel",
            "disabled": {
              "__jsExpr": "true"
            }
          }
        ]
      }
    ]
  },
  "error": "Error: TIMEOUT cancelled record invalid before barrier release",
  "roster": [
    {
      "id": "governance",
      "broken": "cannot create effect on inactive context"
    },
    {
      "id": "standard"
    }
  ],
  "consumerError": "TypeError: Cannot read properties of undefined (reading 'resolve')",
  "completed": "2026-10-18T12:23:29.070Z",
  "exit_code": 0
}
```
