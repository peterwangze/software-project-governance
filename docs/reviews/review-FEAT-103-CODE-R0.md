# REVIEW-FEAT-103-CODE-R0 — M1 隔离补丁（B1 调用方拥有的登记终态撤销）独立代码审查

- 日期：2026-10-21（Asia/Shanghai；本报告命令时刻均为 **UTC**）
- **结论：APPROVED_WITH_NOTES**
- **unresolved_blockers=0**
- P0=0，P1=0，P2=2，P3=5
- 审查对象：隔离副本 `…/feat103-impl/upstream/packages/preset/agent-preset-registry/lib/index.js` + `lib/types/index.d.ts`；测试 `.codex-sandbox/FEAT-103/tests/`；变异体 `…/mutants/{no-observer,single-owner}/`。
- 基线（只读）：**实际安装态** `C:\Users\peter\AppData\Roaming\npm\node_modules\@deepseek-ai\dsh\node_modules\@deepseek-ai\dsh-agent-preset-registry\lib\index.js`（**任务给出的 `…\@deepseek-ai\packages\preset\agent-preset-registry\…` 路径在本机不存在**，见 §1.1；实际 baseline 的 SHA 与 M1 报告声明的源 SHA 一致）。
- 设计依据：`docs/architecture/dsh-upstream-owned-registration-R1.md`（审查时 SHA `A1F676EE27056F0C8BC32BE9F27DC31934EFF25156A75DF7B374E2DA80A008CF`；R3 已把 S-C7 谓词更正为 `ctx.root` 身份，见 §3）。
- Reviewer：独立 Code Reviewer；未参与 M1 实现。只写本报告 + scratch `.codex-sandbox/FEAT-103/review-code-r0/`；未修改产品代码、设计文档、隔离副本，未 stage/commit。

## 1. 对象绑定（双端 SHA）

### 1.1 基线与隔离副本

| 对象 | SHA-256 | 说明 |
| --- | --- | --- |
| 安装态 `dsh-agent-preset-registry/lib/index.js` | `95EDCC66175A87091BA90FE0809246821DF470BF960E1CFD725B5CA6BAAF4F07` | 任务给出的 `.../packages/preset/...` 路径不存在；实际安装包为本路径；M1 报告源 SHA 与其一致 |
| 安装态 `lib/types/index.d.ts` | `522519826855083E6CB1B57386D8C779020CFDA186B98C38E3E237BEC3B477A7` | 同上 |
| 安装态 `package.json` | `68A32854E6492B0F92BE76E7F9F5BE61909BF7798AB22C210362E259947680D5` | 与副本 package.json 相同 |
| 副本 `lib/index.js` | `233CF3531293FF1202FCF0A100A83F3BC149B0F4F54C9613567B89CF3299BE88` | `git diff --no-index --numstat` = **171/0**（纯增量） |
| 副本 `lib/types/index.d.ts` | `9F0BEE1627494203161C2C6F3C9E1533804FFC7E925D0B991F05132E85FA6807` | diff = **43/0**（纯增量） |
| 副本 `package.json` | `68A32854E6492B0F92BE76E7F9F5BE61909BF7798AB22C210362E259947680D5` | 未改 |

- 副本行数 982 vs 基线 811；diff 全部为新增（OwnedRecord + 4 个类成员 + 构造器监听 + beginRegistration/closeAllOwned/_forget），既有 `register/select/mount/list/...` 零改动。
- 基线源/副本在测试前后**逐位不变**（index.js/types/package.json 的 SHA 与 `LastWriteTimeUtc` 前后完全相同，§5）。

### 1.2 证据与测试

| 文件 | SHA-256 |
| --- | --- |
| `.codex-sandbox/FEAT-103/M1-REPORT.md` | `8298ADBBFCBB944B01C80FA949B29FE7CBB723C1060A30D88CB414BDBD92F053`（与任务给值一致） |
| `.codex-sandbox/FEAT-103/tests/t01-owned-registration.mjs` | `296C681EEF09C8BECF4AC3A112C47FA2B02848AD466E65B2F335F112B3127BB2` |
| `.codex-sandbox/FEAT-103/tests/audit-positive.json` | `688D5050C9D5EE25530D3F0BEA4B052AD1CA8834C342453536A9510C30590901` |
| `.codex-sandbox/FEAT-103/tests/audit-mutant-no-observer.json` | `CC0FE59978379B3D2B9B7B95BE7793901D3431735CE419D6493F1F3E471742A1` |
| `.codex-sandbox/FEAT-103/tests/audit-mutant-single-owner.json` | `1822CC105069760D2B56E6F809B0268406233D510387818759DB005180C2FCFB` |
| `.codex-sandbox/FEAT-103/copy-manifest.txt` | `049F80546447CDDED62938202BAFF0611B986DE49ED98F7A499337DE714B783D`（8 行） |
| `.codex-sandbox/FEAT-103/test-audit.txt` | `E2FAB9F21CB3B8D3DE4B09765124B4A96E5068C94C5C73A219E9FA44B90A3F99` |
| 变异体 `no-observer/lib/index.js` | `C5E7003182F2DC4600F43EB0AA05ACF15B2D7701BE18A12CDB4ECBB384489A2D` |
| 变异体 `single-owner/lib/index.js` | `3DC50AB83CFFC800A087943E373ED7F4678B9A3836362F8D8713601F9D58CF5D` |
| 设计文档（审查时） | `A1F676EE27056F0C8BC32BE9F27DC31934EFF25156A75DF7B374E2DA80A008CF` |

- M1 报告引用的设计 SHA `7b43101c…` 已被 R3 修订覆盖；当前 §3.3 已含 S-C7 更正（`ctx.root`），实现与当前 R3 文本一致（§3）。
- `copy-manifest.txt` 只有 8 个 companion/vendor 副本；**对象本体 registry 3 文件不在清单中**（M1 报告表格给了源 SHA）。独立 `git diff --no-index` 已完成 baseline→副本的双端校验；这是证据完整性 P3，不影响代码判定（§4-F5）。

## 2. 结论先行

- **M1 T01+ 硬门通过**：独立复跑 **5 passed / 0 failed / exit 0**；两个变异体独立复跑 **3/2**、**4/1**（均 exit 1），证明测试非空转（§5）。
- CH-1.1、CH-1.3、CH-1.4 实现与设计一致；CH-1.2 的同步插入序列、错误码、root 谓词、插入后复核、effect 兜底均正确；CH-1.5 的 LOADING-owner 同步 close / late activation 不复活经 T01-a 验证。
- **两项 P2（不在 M1 T01+ 声明门内，但为真实 API 分支缺陷，必须在 M2/使用 signal 前修正）**：
  1. `close()` 在激活开始前发生（pre-aborted signal / close-before-start）时只置 closed，不 drain；`start()` 因已 closed 直接返回，`drained` 永远 pending、record 永留在 `ownedRecords`/owner 索引（Reviewer 探针实测）。
  2. 真实 `activate()` 的“catch 后无 generation”失败路径只 settle `ready failed`，`closed/drained` 保持 pending、record 留在 definitions/owned，直到显式 close/registry teardown。
- 这两条对应 M1 报告 §5 第 4/5 条与 §6 第 3 条明列的 remaining（close-before-start、signal-abort）；因此不作为 M1 T01+ 的 blocker，但报告明确标记“未完成、不得声明 signal/失败终态已实现”。
- **设计谓词**：实测 `ctx.root` 身份成立、`events` 对象身份不成立；采用 `ctx.root` 谓词。当前 R3 设计已同向更正；`OWNER_ROOT_MISMATCH` 位于 effect/分配之前，未发现对合法同 root owner 的误拒（子 context root 继承；T01-e 跨 root 拒绝）。

## 3. 设计谓词（S-C7）与 root 语义

- SOURCE：cordis 0.2.1-rc.2 `cordis/lib/index.js:1682` `this.root = self`（root Context 构造器）；`:1704-1709` `extend()` 用 `Object.create(getTraceable(this, this))`，子 context 原型继承 `root`；`:1053-1054` 插件 fiber 的 `ctx = parent.extend({fiber:this})`。因此同 root 的后代 `ctx.root` 与 root 为同一对象。
- 独立探针（`.codex-sandbox/FEAT-103/tests/probe-root.mjs`）：两个插件 context 输出 `ctx.root === root: true`；`root.events === ext.events === pctx.events: false`（events 是 per-context service view）。`probe-events.mjs` 同结论；`probe-effect.mjs` 显示 `dispose()` 返回 Promise、owner effect cleanup 次序。
- 当前设计（SHA `A1F676…`）§3.3 第 165 行与 R3“S-C7 更正”节已使用 `ownerCtx.root === this.ctx.root`；实现 `lib/index.js:604` 同向。**采信谓词 = `ctx.root` 对象身份**；原 `events` 身份谓词作废。
- `OWNER_ROOT_MISMATCH` 位于 `lib/index.js:604`：在 owner effect（607）、record 分配（611）、definitions/owner 索引（612-616）之前；T01-e 的跨 root 拒绝与 `definitions.size===1` 证明校验失败不分配。未发现误拒同 root 后代（source + probe）；多份 cordis 拷贝混用会造成 root 对象不同（非当前宿主），作为 P3 边界（§4-F6）。

## 4. Findings

### P2（不在 M1 T01+ 门内，但真实分支缺陷，M2 前必须修）

**R0-F1 — pre-aborted signal / close-before-start：`drained` 永不 settle，record 永留 owner 索引**

- 位置：`OwnedRecord.close()`（`lib/index.js:454-463`）只在 `this.activationSettled` 时调用 `_drain()`（:462）；`start()`（:428-429）对非 `activating` 直接返回；`beginRegistration` 在 signal 已 aborted 时先 `record.close("signal-aborted")`（:618-620）再 `record.start()`（:622）；插入后 uid 复核分支（:617）同理。
- 证据（Reviewer 探针 `.codex-sandbox/FEAT-103/review-code-r0/probe-close-before-start.log`）：
  - `preAborted.ready = {state:'closed', reason:'signal-aborted'}`；`closed = {reason:'signal-aborted', previous:'activating'}`；**`drained.settled=false`（300ms timeout）**；`state='closed'`；`ownedRecords=1`；`definitions=0`。
  - 对照 `closeAfterBegin`（activation 已 start）`drained={state:'drained'}`、`ownedRecords=0`。
- 影响：`beginRegistration(..., {signal})` 传入已取消 signal（常见编排模式）时，`OwnedPresetRegistration.drained` 永久 pending，owner 索引/`ownedRecords` 永久保留该 record（close 幂等 no-op；closeAllOwned 也不 drain）；即使 owner/registry 卸载也只 close，不再 forget。属于真实 API 分支的挂起/泄漏，不是仅“未测试”。
- 修复要求：`OwnedRecord` 记录 `started`；`close()` 在 `!started` 时调用 `_drain()`（无 generation → finish/`_forget`），或 `beginRegistration` 在 pre-start close 路径显式 drain；补 T01 用例（pre-aborted signal + 期望 `drained` 在 300ms 内 settle、`ownedRecords=0`）。
- M1 门判定：M1 报告 §5 第 4/5 条与 §6 第 3 条将 close-before-start、signal-abort 列为 remaining，T01+ 不含；故记为 P2（M1 T01+ 不因此失败），但**不得声称 signal 路径已实现/可依赖**。

**R0-F2 — 激活失败（真实 `activate` catch 路径）终态不 drain、不 forget**

- 位置：`_activationSettled()`（`lib/index.js:435-448`）：当 `state==='activating'` 且 `_generation===undefined` 时只 `settledState='failed'`、resolve `ready failed`（:441-444），随后 **return**，不调用 `_drain()`；`close()` 只在 `activationSettled` 时 drain（:462），所以失败后 `closed`/`drained` 均 pending，record 留在 `definitions`/owner 索引，直到显式 close 或 registry teardown。
- 证据（同一探针 `failedActivation`）：`ready={state:'failed',code:'agent-preset/activation-failed'}`；**`closed.settled=false`、`drained.settled=false`**；`state='activating'`；`ownedRecords=1`、`definitions=1`。随后 `closeAllOwned('registry-disposed')` → state closed、drained settle、owned/definitions 0（说明 close 路径可回收，但失败本身不自动终态）。
- 设计/报告边界：M1 报告未把 activation failure 纳入 T01+；`activate()` 的真实实现会 catch mount 错误并写 `broken=`、不 rethrow，故该分支可达。`closed` 是否应在 failed 时 settle 属于合同未定；但“ready failed 后 record 永留主表/索引、`drained` 永 pending”至少应显式记录或修正。建议：失败即 drain（无 generation）并 `_forget`，或把 `closed/drained` 的失败终态写进类型/设计并补测试。
- 记为 P2（合同/生命周期缺口，不在 T01+ 门内）。

### P3（建议/讨论）

**R0-F3 — signal listener 在 close 后未移除**：`lib/index.js:620` `addEventListener('abort', ..., {once:true})` 只在 abort 时自动移除；record close/drain/forget 后 listener 仍持有 record 闭包，长寿命 signal 会延迟回收；建议保存 handler 并在 close/_forget 时 `removeEventListener`（或统一在 close 时清理）。

**R0-F4 — `drained` 在 generation.users>0 时可能提前 settled**：`_drain()`（:464-480）调用 `registry.collect(generation)`；原 `collect`（基线 `lib/index.js:545-548`）在 `!generation.retired || generation.users!==0` 时直接 return；`finish` 仍 resolve `{state:'drained'}` 并 forget。若 legacy `retain` 持有该 generation（M1 报告 §5 第 3 条明说 legacy 交互未测），scope 实际未 dispose、`drained` 却已“drained”。属 legacy 交互未定面，需在 M2/契约中明确 drained 语义或等待 users 归零；M1 不因此失败。

**R0-F5 — copy-manifest 不含对象本体**：`copy-manifest.txt` 仅 8 个 companion/vendor 源→目标；registry 的 `lib/index.js`/`lib/types/index.d.ts`/`package.json` 未列入（M1 报告表格给了源 SHA）。已用 baseline→副本 `git diff --no-index` 独立校验 +171/0、43/0；建议补 manifest 三行，使复制清单自包含。

**R0-F6 — 谓词/边界小项**：(a) `OWNER_ROOT_MISMATCH` 用 `ctx.root` 对象身份；同 root 后代/isolate 由 `extend` 继承同一 root（source + probe），未发现误拒；混用多份 cordis 拷贝会 root 不同（当前宿主不涉及）。(b) 类型 `OwnedPresetRegistration.generation: object`（types:43）在 `beginRegistration` 返回时仍 undefined，且 `ready` outcome 的 `generation` 是 `generationToken`（`lib/index.js:440`）而非实际 generation；建议类型改为延迟/可选，或区分 token 与 generation 字段。(c) 创建发射的 `uid!==null` 早退（:570）由 SOURCE 与 `probe-events` 支持，T01 未单独断言；不影响 T01+。

**R0-F7 — 测试质量**：核心“不得等待”断言使用 barrier + `WATCHDOG_TIMEOUT`（T01-a/c 等），两枚变异体独立复跑分别 2/1 failed，无弱化；但若干 setup/控制使用固定 `tick(5/10/20)`（如 T01-a 的 `tick(10)`、`tick(5)`），不是纯事件屏障，负载下可能假失败/慢；建议改 `setImmediate`/事件 promise。M1 报告对 single-owner 变异体的失败描述（“兄弟 record 未被通知”）与实际“在 owner index size 断言处先失败”不一致（日志为准），属报告精度 P3。

## 5. 独立复跑与边界

### 5.1 T01+（真实进程内 cordis 0.2.1-rc.2）

| 运行 | UTC（起→止） | exit | 结果 |
| --- | --- | --- | --- |
| 正例（副本） | 05:56:22.869Z→05:56:23.268Z | 0 | **5 passed / 0 failed**（T01-a…e 全绿） |
| 变异体 no-observer | 05:56:23.268Z→（同命令） | **1** | **3 passed / 2 failed**（T01-a watchdog、T01-c ready undefined） |
| 变异体 single-owner | →05:56:25.987Z | **1** | **4 passed / 1 failed**（T01-b owner index size） |

- 与 `.codex-sandbox/FEAT-103/test-audit.txt` 的 positive 5/0、no-observer 3/2、single-owner 4/1 一致；测试/变异体文件只读（运行前后 SHA 未变）。
- 测试的 `Harness` 用 subclass 覆盖 `activate`（payload barrier 替身），不是真实 mount；真实 `activate`/mount/host boot 未在 T01 中执行（M1 报告已披露）。

### 5.2 探针

- `probe-root/events/effect`：05:56:42.646Z→05:56:43.033Z，exit 0；见 §3。
- `probe-close-before-start.mjs` 首次 05:59:10.130Z→05:59:10.751Z，**exit 1**：reviewer 脚本自身在同一 root 构造第二个 registry 服务触发 `service "agentPresets" has been registered`（非产品结果）；修正为每 case 独立 root 后 05:59:24.603Z→05:59:25.892Z exit 0，输出见 §4-F1/F2。如实保留。

### 5.3 边界

- **安装 SDK 零写入**：`lib/index.js`/`lib/types/index.d.ts`/`package.json` 的 SHA 与 `LastWriteTimeUtc` 在运行前后逐位相同（`installed-before.txt`/`installed-after.txt` SHA 同为 `5BBCD9B0…0645`）。
- **真实 `~/.dsh`**：无宿主进程、无测试代码引用 home；仅进程内 cordis，未读写 `C:\Users\peter\.dsh`。
- **产品代码/设计/副本**：未修改；`git status --porcelain -uno` 仅既有暂停 WIP 两行；`git diff --cached` 空；HEAD `2ed8bb4`。隔离副本与测试只在 `.governance/sandboxes/feat103-impl/**`、`.codex-sandbox/FEAT-103/**`。
- 设计文档（R1/R3）仅读；当前哈希 `A1F676…`。

## 6. CH-1.1～1.5 判定

| CH | 设计要点 | 判定 | 证据/备注 |
| --- | --- | --- | --- |
| CH-1.1 | dispose-start 观察者、uid 早退、多值 owner 索引、registry teardown `closeAllOwned` | **PASS** | `lib/index.js:568-573`、`:613-616`、`:626-635`；SOURCE cordis `:1078-1079`（uid null→emit）、`:1093`（创建时 uid 非 null）；T01-b/c；probe-root/events |
| CH-1.2 | 同步插入序列、插入后 uid 复核、错误码、root 谓词 | **PASS（gate）/ P2 分支缺口** | `:593-622`；T01-e；root 谓词 §3；pre-aborted/close-before-start 的 drain 缺口见 R0-F1 |
| CH-1.3 | per-begin owner effect 兜底、first-reason-wins、close 幂等 | **PASS** | `:607`；T01-b/d；observer 移除时 effect 兜底未单独构造（NOT_RUN） |
| CH-1.4 | root owner 映射、registry teardown 理由 `registry-disposed` | **PASS** | `:572`、`:626`；T01-c；root restart/owner effect 先行的理由优先级 NOT_RUN |
| CH-1.5 | ready/closed 同步 settle、late activation 不复活、drained 独立 | **PASS（LOADING-owner 主门）** | `:454-481`；T01-a（barrier 前 closed、dispose 不等待、release 后 drained/scope 一次）；activation failure/pre-start drain 为 P2 |
| 设计偏差 | S-C7 events 身份 → ctx.root 身份 | **实现正确、设计已 R3 更正** | 见 §3；M1 报告的 `7b43101c…` 设计 SHA 为更正前版本，当前 `A1F676…` 已同向 |

## 7. 风险/缺口（逐条 NOT_RUN）

| 缺口 | 状态 | 说明 |
| --- | --- | --- |
| signal-abort（已 abort / 活动 abort） | **T01+ NOT_RUN；pre-aborted 分支已探针发现 P2** | T01 未覆盖；R0-F1 证明 pre-aborted `drained` 挂起/索引残留；活动 abort 未测 |
| close-before-start 注入点 | **NOT_RUN** | 同步序列中无法在不改产品的情况下构造真实交错；pre-aborted signal 走同一 close-before-start 分支（R0-F1） |
| activation failure | **NOT_RUN（T01+）；P2 探针** | real `activate` catch 后无 generation；ready failed、closed/drained pending、record 留主表（R0-F2） |
| legacy roster/list/retain/mount/select | **NOT_RUN** | OwnedRecord 进入 definitions 主表；`list/diagnostic` await `record.ready`，`retain` 可增 users；M1 报告 §5 第 3 条明说未测；`drained` users 语义见 R0-F4 |
| host boot / 真实 host 链路 | **NOT_RUN** | M1 进程内 cordis；M2 才启动 dsh |
| root restart / root owner 先行 effect | **NOT_RUN** | T01-c 只测 registry teardown；root restart 的理由优先级未测 |
| creation emission 过滤 | SOURCE 已核；**测试 NOT_RUN** | cordis :1093 uid 非 null；T01 未直接断言监听者早退 |
| 多份 cordis 拷贝 / 跨 copy root | **NOT_RUN** | 当前宿主单 copy；谓词边缘见 R0-F6 |
| 真实 `launch.py`/host 交互 | **NOT_RUN** | 不在 M1 范围 |

## 8. 命令审计（本轮 Reviewer）

| # | label | UTC 2026-10-21（起→止） | exit | 影响路径/要点 |
| --- | --- | --- | ---: | --- |
| R1 | T01+ 正例 + 两变异体（同一命令） | 05:56:22.869Z→05:56:25.987Z | 0 / **1** / **1** | `DSH_HOME=.governance/sandboxes/feat103-code-r0-20261021T055249Z`（进程未使用）；测试只读 impl/基线 |
| R2 | probe-root / probe-events / probe-effect | 05:56:42.646Z→05:56:43.033Z | 0 | 只读 cordis + 测试目录 |
| R3 | probe-close-before-start 首次 | 05:59:10.130Z→05:59:10.751Z | **1** | Reviewer 脚本自身服务注册冲突（同 root 第二个 registry），未产生产品结果；如实保留 |
| R4 | probe-close-before-start 重跑（每 case 独立 root） | 05:59:24.603Z→05:59:25.892Z | 0 | 输出 preAborted/failedActivation 证据 |
| R5 | 安装 SDK 前后 SHA+mtime | 测试前后 | 0 | 三项逐位相同；只读 |
| R6 | git status/diff/hash/只读核对 | — | 0 | 无产品修改；staged 0 |

M1 生产者的 copy/patch 命令（`patch_m1b.py` 等）未重跑；`test-audit.txt` 是其自报的 UTC/exit，与我的独立复跑计数一致。

### Reviewer 证据 SHA-256（`.codex-sandbox/FEAT-103/review-code-r0/`）

| 文件 | SHA-256 |
| --- | --- |
| `t01-positive.log` | `688D5050C9D5EE25530D3F0BEA4B052AD1CA8834C342453536A9510C30590901` |
| `t01-mutant-no-observer.log` | `CC0FE59978379B3D2B9B7B95BE7793901D3431735CE419D6493F1F3E471742A1` |
| `t01-mutant-single-owner.log` | `1822CC105069760D2B56E6F809B0268406233D510387818759DB005180C2FCFB` |
| `probe-root.log` | `7E0683F86EA329D5A14F2D3B7C0B03E6996EE3024F2B26FF0BD04AF7BFEE66B5` |
| `probe-events.log` | `97F5E1D688726C22B3A35451C80E4F96EABF6FBEF9594AB0D92A7509FFF0D7FC` |
| `probe-effect.log` | `4D972CA216D377243897B916F7598F05BD7DAE7EC91312C160919F26B73CEB39` |
| `probe-close-before-start.log` | `2630D679E3B5D2E3556FB56CE7A7ABF81A1944B0D20F187821CE002415F15946` |
| `installed-before.txt` / `installed-after.txt` | `5BBCD9B0B40B2094790346B5ABC6A477534F1B3DCEB4E7B1802603005D150645`（两者相同） |

## 9. 硬门槛自检

1. 未修改产品代码/设计文档/隔离副本/测试；仅写本报告与 scratch。未 stage/commit/push。✓
2. 每条结论有实际运行/读取证据（行号、日志、SHA、探针）；失败命令 R3 与 NOT_RUN 项如实保留；未把 NOT_RUN 写成通过。✓
3. 所有进程命令先设并断言 `DSH_HOME` 在仓库 `.governance/sandboxes/` 内；测试为进程内 cordis，无宿主进程；未读写真实 `~/.dsh`；安装 SDK SHA/mtime 前后一致。✓
4. 设计依据按审查时 SHA `A1F676…`（R3 谓词更正）核对；M1 报告 `8298ADBB…` 与任务给定值一致。✓
