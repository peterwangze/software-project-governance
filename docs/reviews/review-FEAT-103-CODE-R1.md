# REVIEW-FEAT-103-CODE-R1 — M1-FIX（2×P2 + 3×P3 闭环）独立复审

- 日期：2026-10-21（Asia/Shanghai；本报告命令时刻均为 **UTC**）
- **结论：APPROVED_WITH_NOTES**
- **unresolved_blockers=0**
- P0=0，P1=0，P2=0，P3=7
- 审查对象：修复后隔离副本 `…/feat103-impl/upstream/packages/preset/agent-preset-registry/lib/index.js`（**1024 行**，SHA `1329CC2C63F89BA7DFC85FEB79C1A97D1822778B264E69B5FEB5874869FDA47D`）与 `lib/types/index.d.ts`（SHA `722D29DAB3C424256C85DDECC8B599C2ADE85CA5BE8C2BC74E11830BCE8F445F`）；9 案测试 `t01-owned-registration.mjs`（SHA `FA43EAC75D534FBA2107FEFFC7FDF10DAB6E556EA291AC09E167F8D8F12BF2A2`）；两枚变异体 + pre-fix 对照。
- 前轮：`docs/reviews/review-FEAT-103-CODE-R0.md`（SHA `FA1750F6…DE8F5E`，AWN/0，P2×2 + P3×5）；R0 副本 SHA `233CF353…99BE88`（982 行）。
- 设计：R3 版 `A1F676EE27056F0C8BC32BE9F27DC31934EFF25156A75DF7B374E2DA80A008CF`（`ctx.root` 谓词；本次未改谓词）。
- Reviewer：同一实例；只写本报告 + scratch `.codex-sandbox/FEAT-103/review-code-r1/`；未改产品/设计/副本，未 stage/commit。

## 1. 对象绑定（双端 SHA）

### 1.1 基线 / 修复副本 / 类型

| 对象 | SHA-256 | 说明 |
| --- | --- | --- |
| 安装态 `dsh-agent-preset-registry/lib/index.js` | `95EDCC66175A87091BA90FE0809246821DF470BF960E1CFD725B5CA6BAAF4F07` | 与 R0 记录一致（只读；本机无任务原先给出的 `...\packages\preset\...` 路径） |
| 安装态 `lib/types/index.d.ts` | `522519826855083E6CB1B57386D8C779020CFDA186B98C38E3E237BEC3B477A7` | 与 R0 记录一致 |
| 安装态 `package.json` | `68A32854E6492B0F92BE76E7F9F5BE61909BF7798AB22C210362E259947680D5` | 与副本相同 |
| 修复副本 `lib/index.js` | `1329CC2C63F89BA7DFC85FEB79C1A97D1822778B264E69B5FEB5874869FDA47D` | 1024 行；相对安装态 **+213/−0**（R0 为 +171/−0，本次 +42 行） |
| 修复副本 `lib/types/index.d.ts` | `722D29DAB3C424256C85DDECC8B599C2ADE85CA5BE8C2BC74E11830BCE8F445F` | 相对安装态 **+46/−0**（R0 +43） |
| R0 副本（前轮记录） | `233CF3531293FF1202FCF0A100A83F3BC149B0F4F54C9613567B89CF3299BE88`（982 行） | **R0 字节未保留**：同一路径被本轮就地覆盖；精确 R0→fixed 字节 diff 不可重放（P3，见 §4-F5） |

- `git diff --no-index --numstat` fixed vs installed = **213/0**；`--unified=0` 中**原 811 行零删除**。既有 `register/select/mount/list/diagnostic/retain` 等未被改；新增仅在 FEAT-103 区域。
- 类型 diff +46/0；既有声明零改动。
- `ctx.root` 谓词仍在（fixed :639），未改回 `events`。

### 1.2 测试 / 变异体 / 对照 / 证据

| 文件 | SHA-256 |
| --- | --- |
| `tests/t01-owned-registration.mjs`（9 案） | `FA43EAC75D534FBA2107FEFFC7FDF10DAB6E556EA291AC09E167F8D8F12BF2A2` |
| mutant `no-observer/lib/index.js` | `094E4E427AA45C273AC0B17143D4B25F9389EF6A637DD67A9E96645D0B7C5986` |
| mutant `single-owner/lib/index.js` | `C4CB3B3C59C0E9427706899A711F9FED6B438CBFA53A9BF4DAADBC4A78A7D75B` |
| pre-fix control `controls/prefix-shape/lib/index.js` | `94F8C80D28781C6817303DC32F451D3321299D5852722A95A3FAB96A6E5439A7`（1016 行；行为形态还原，非逐字节 R0） |
| `copy-manifest.txt`（13 行） | `99466A845C0DBB1F15AE221FB933E1F19BB2B741085AD2AA68D3D54D31F1B5D3` |
| `M1-FIX-REPORT.md` | `F9562B7DC6424E08C2F6AA176875A17A976371FB2FABD4F08B5D6B852915B9BB` |
| `test-audit-m1fix.txt` | `8CDC9F9FBFC6D3A1071D5C91AC7F1A3AF2D1F807B840A7EC164B8F118D742D52` |
| R0 报告 | `FA1750F65EE05D7A94CF3FD049999C76E28D7E7CC9DA7516C7C5662E63DE8F5E` |
| 设计（R3） | `A1F676EE27056F0C8BC32BE9F27DC31934EFF25156A75DF7B374E2DA80A008CF` |

- 变异体 diff 与 fixed 仅差 observer 删除 / 单值索引退化（其余与 fixed 逐字节相同）→ **确认从修复后字节重生成**，不是 R0 旧字节。
- 对照 diff 与 fixed 恰为三处回退（failure terminal、close drain 条件、detach 调用）+ 保留 `started`/signal 脚手架；T01-f/g/i 三失败，T01-h 通过（M1-FIX 报告已披露 T01-h 在 pre-fix 通过，未把它当非空转证据）。

## 2. R0 findings 处置

| R0 finding | 状态 | 独立事实 |
| --- | --- | --- |
| P2-1 pre-aborted/close-before-start 不 drain | **已修（主路径）** | `started` 标志（:418/:432）；`close()` 条件 `activationSettled \|\| !started`（:496）；`_drain.finish` `_detachSignal + _forget`（:501-505）。T01-f：`setImmediate` 后 `drained={state:'drained'}`、state closed、`ownedRecords=0`、definitions 无 id、owner 索引 undefined；pre-fix 对照 T01-f 在 drained 断言失败。 |
| P2-2 激活失败不终态 | **已修** | `_activationSettled()` 失败分支（:446-460）：ready failed 保留 → state closed/closeReason `activation-failed` → detach → definitions 删除 → closed `{reason,previous:'failed'}` → `_drain`→drained+forget。T01-g 全断言通过；pre-fix 对照 T01-g 在 closed 处 watchdog 失败。T01-h：显式 `close('explicit')` 先发生 → ready/closed 保持 explicit、previous activating，late failure 后 drained/forget；first-reason-wins 成立。 |
| P3 signal listener 未移除 | **已修** | `_signalListener` 保存（:653-663）；`_detachSignal()`（:465-475）在 close（:486）、failure（:456）、drain finish（:502）调用；T01-i `added=1 removed=1`；pre-fix 对照 T01-i removed=0 失败。 |
| P3 copy-manifest 缺对象本体 | **已补** | 13 行；追加 header + registry 三文件（copy-time 源 SHA + 目标路径）；`True(copy-time)` 表示复制时一致，补丁后目标 SHA 见 M1-FIX 报告（P3 文案：非布尔字段）。 |
| P3 single-owner 变异体报告精度 | **已勘误** | M1-FIX §1.5 与实测一致：T01-b 第一个失败点是 owner index size 断言（`ownedByFiber.get(...).size===2`），不是“兄弟未被通知”；“兄弟通知”分支在 single-owner 下被前置断言短路、NOT_RUN。 |

## 3. 独立复跑（9 案 + 变异体 + pre-fix 对照）

| 运行 | UTC 2026-10-21（起→止） | exit | 实数 |
| --- | --- | ---: | --- |
| 正例（fixed） | 06:42:06.679Z→06:42:07.240Z | **0** | **9 passed / 0 failed**（T01-a…i） |
| mutant no-observer | 06:42:07.240Z→06:42:09.803Z | **1** | **7 passed / 2 failed**（T01-a `WATCHDOG_TIMEOUT`、T01-c ready undefined） |
| mutant single-owner | 06:42:09.803Z→06:42:10.283Z | **1** | **8 passed / 1 failed**（T01-b owner index size） |
| pre-fix control prefix-shape | 06:42:10.283Z→06:42:11.342Z | **1** | **6 passed / 3 failed**（T01-f drained 未 settle、T01-g closed 未 settle、T01-i removed=0；T01-h PASS，如实记录） |

- 与 `.codex-sandbox/FEAT-103/test-audit-m1fix.txt` 的 9/0、7/2、8/1、6/3 及失败点一致。
- 正例/变异体/对照文件在运行前后 SHA 不变；安装态 SDK 三文件 SHA 前后与 R0 记录逐位相同（`95EDCC…` / `52251982…` / `68A32854…`）。
- 无 `dsh` 宿主进程：全部为 `node` 进程内 cordis；未读写真实 `~/.dsh`。

## 4. Findings（P3，非阻断）

**R0-F1 — close-before-start 分支的 signal attach 仍可能发生在终态之后**

- `beginRegistration` 的顺序是：插入 → `if (ownerFiber.uid === null) record.close("owner-disposed")`（:652）→ signal 合并（:653-663）→ `record.start()`（:664）。若在插入后复核处已 close 并 drain/forget（`started=false`），但传入的是**未 abort** 的 signal，则 :653-663 仍会 `record._signalListener = {...}` 并 `addEventListener`，而 `_detachSignal` 已在 close/drain 中执行过——listener 之后不会被移除；record 虽已从三处清理，但 signal 闭包仍持有它直到 abort/GC。
- T01-f 只覆盖 **pre-aborted**（不 attach）；close-before-start 注入点在本轮仍未构造（R0 `M1-REPORT.md` §5.4 已声明该注入点在同步 JS 内不可复现；M1-FIX 报告 §1.1 的“已修”指主路径）。正常 JS 同步段内 uid 不会变化，触发需要 definition getter/owner effect 等重入（非普通输入）；因此定 P3。
- 建议：在 signal 合并前检查 `record.state === "activating"`（或把 signal attach 提前到 uid 复核之前，让 close 的 detach 生效），并补一条 close-before-start + 非 abort signal 的测试。

**R0-F2 — `close('activation-failed')` 被类型与运行集允许，调用方可伪造 registry 终态 reason**

- `OWNED_CLOSE_REASONS` 现包含 `activation-failed`（fixed :387）；类型 `OwnedCloseReason` 含五值且 `close(reason?: OwnedCloseReason)`（types :21-25/:51）。M1-FIX 报告 §1.2 注释说“caller-initiated closes use the other four”，但 API 未限制；调用方传 `activation-failed` 会被接受并写入 closed，与真实失败不可区分。
- 建议：拆分“registry 终态 reason”与“caller close request”类型，或让 `close()` 参数排除 `activation-failed`（内部 branch 直接写），并补类型/负例。

**R0-F3 — `_detachSignal` 的三处调用只有 close 路径被测试**

- 代码在 failure（:456）、close（:486）、drain finish（:502）三处调用，符合要求；T01-i 只覆盖 `close('explicit')` 的 `added=1 removed=1`（:313-329）。T01-g 的 failure harness 未传 signal，因此 failure 分支的 detach 与 drain finish 的 detach 未被 listener 计数覆盖。
- 建议：T01-g 加一个真实 signal（并以失败收尾）断言 removed=1；T01-i 保持 close 路径。

**R0-F4 — R0 未处置的 P3 残余**

- `drained` 与 legacy `retain` 的 `generation.users>0` 语义仍未变（`_drain` 调 `collect`，原 `collect` 在 users≠0 时直接 return；M1-FIX §5 第 3 条明说留 M2）；`OwnedPresetRegistration.generation: object` 在 begin 返回时仍可能 undefined；T01 各案 setup 仍用 `tick(10/5/20)`（T01-f 终态用 `setImmediate`，硬断言用 watchdog，未退化）。这些是 R0 P3 的未处置项，不影响本轮 P2 闭环。

**R0-F5 — 证据可重放性**

- R0 字节（`233CF353…`，982 行）没有保留：fixed 就地覆盖；pre-fix 对照 1016 行、保留 `started`/`_detachSignal` 脚手架，是**行为形态**还原而非逐字节 R0。因此 R0→fixed 的精确字节 diff 不可重放；本轮以 fixed vs installed（213/0）+ fixed vs control（三处回退）+ control 运行结果作为替代证据，属 P3 证据完整性。建议后续保留 R0 原始副本（或发布原始字节）以便复现。

**R0-F6 — 失败终态删除 definitions 的设计面提示**

- fixed 在 activation failure 时删除 definitions 并 forget（:457/:459）；M1-FIX §6 已提示需在 R3 设计/类型合同写明“激活失败即终态”。当前 R3 设计未见该句；这是设计面待补，不是代码回归。属 P3。

**R0-F7 — T01-h 不具非空转性（已披露）**

- T01-h 在 pre-fix 对照上仍 PASS（M1-FIX §2 已披露）：显式 close 在 start 之后，pre-fix 的 late `_activationSettled` 走 post-if drain，仍能收尾。T01-h 的断言（ready/closed 保持 explicit、drained、forget）成立，但不能单独证明新增 failure 终态分支；T01-g 是非空转证据。P3 记录，不要求改。

## 5. 回归 / 既有路径

- fixed vs installed `--numstat` = **213/0**；`--unified=0` 对安装态 811 行的删除数 = **0**。`register`（:683 起）、`select`/`mount`/`list`/`diagnostic`/`retain` 等既有行未改；改动全在 FEAT-103 新增区。
- `ctx.root` 谓词未改回 events（:639；仅注释引用旧设计文本）。
- 类型既有声明零改；新增 `activation-failed` 与 detach 相关注释。
- 变异体从 fixed 重生成（diff 仅 observer/index）；pre-fix 对照三处回退；与 M1-FIX 报告一致。

## 6. 边界合规

- **安装态 SDK**：三文件 SHA 前后与 R0 记录一致（§3），未写入；只读。
- **产品/设计/治理记录**：未修改；`git status --porcelain -uno` 仅既有暂停 WIP 两行；`git diff --cached` 空；HEAD `2ed8bb4`；设计文档 R3 SHA `A1F676…` 未改。
- **宿主/真实 home**：未启动 `dsh`；测试为进程内 cordis；未设置/未读取真实 `~/.dsh`；`DSH_HOME` 仅设到仓库 `.governance/sandboxes/feat103-code-r1-20261021T064042Z`，测试本身不消费。
- **写面**：只写本报告 + `.codex-sandbox/FEAT-103/review-code-r1/`；未改隔离副本/测试/变异体/对照。

## 7. 命令审计（本轮 Reviewer）

| # | label | UTC 2026-10-21（起→止） | exit | 要点 |
| --- | --- | --- | ---: | --- |
| R1 | 正例 9 案 | 06:42:06.679Z→06:42:07.240Z | 0 | 9/0；`DSH_HOME` 前缀断言；进程内 cordis |
| R2 | mutant no-observer | 06:42:07.240Z→06:42:09.803Z | 1 | 7/2（T01-a watchdog、T01-c） |
| R3 | mutant single-owner | 06:42:09.803Z→06:42:10.283Z | 1 | 8/1（T01-b index size） |
| R4 | pre-fix control prefix-shape | 06:42:10.283Z→06:42:11.342Z | 1 | 6/3（T01-f/g/i；T01-h PASS 如实记录） |
| R5 | 安装 SDK 三文件 SHA 前后 | 测试前后 | 0 | 逐位相同；只读 |
| R6 | fixed/test/mutant/control 哈希 + git status/staged | 只读 | 0 | 无产品修改；staged 0 |

M1-FIX 生产者的 copy/patch/mutant/control 命令（C1-C10）未重跑；`test-audit-m1fix.txt` 是其自报的 UTC/exit，与我的独立复跑计数一致。未发现需保留的失败自纠（R4 的 exit 1 是对照的预期失败）。

### Reviewer 证据 SHA-256（`.codex-sandbox/FEAT-103/review-code-r1/`）

| 文件 | SHA-256 |
| --- | --- |
| `positive.log` | `1FC63DBD968B6F4E96ACAE7B6A87CFAD5736B9CE13D073133119C61BA613570F`（9/0） |
| `mutant-no-observer.log` | `F432B23D8C27A481AD14400D9523F7D638319A863D7FE867C75BFE69037D317A`（7/2） |
| `mutant-single-owner.log` | `C71E4961E10DF4D8473101D6D8E9CF8A0B55FD7953F8EBFE8F5210976EEE3327`（8/1） |
| `control-prefix-shape.log` | `E4000562CD3F0E4DDA015D6D7CFC3A2578CFB31D7B2F1026E0165592521CFECA`（6/3） |

（四份日志保留在本轮 scratch；其 JSON 内容与上表一致；本报告不以日志哈希替代运行事实。）

## 8. NOT_RUN / 缺口

- **活动 abort**（signal 在激活中触发）：未测；本轮仅 pre-aborted（T01-f）。
- **close-before-start 注入点**（含非 abort signal 的 attach 后置）：未构造；T01-f 只覆盖 pre-aborted；R0-F1 的 attach-after-close 边由此残留。
- **真实 `activate()` mount 失败链**（entryListProblem/mountPreset 抛错 → catch → scope.dispose）：T01-g/h 用“resolve 无 generation”模拟 catch 后形态，真实错误链未执行。
- **legacy roster/list/retain/mount/select**：未测；`drained` users>0 语义未定（R0-F4）。
- **host boot / M2 消费者**：未启动 dsh。
- **R0 字节重放**：R0 文件未保留，control 为行为形态（R0-F5）。
- **T01-i 的 failure/drain 路径**：未覆盖（R0-F3）。
- **`generation` 类型/`close('activation-failed')` 调用面**：未做类型运行时负例（R0-F2/F4）。

## 9. 硬门槛自检

1. 未修改产品代码/设计/副本/测试；仅写报告 + scratch。未 stage/commit/push。✓
2. 每条结论有实际运行/读取证据（行号、日志、SHA、control/变异体）；失败/预期失败与 NOT_RUN 如实保留。✓
3. 全部进程命令先设并断言 `DSH_HOME` 在仓库 `.governance/sandboxes/` 内；未启动宿主；未读写真实 `~/.dsh`；安装 SDK SHA 前后一致。✓
4. 设计按 R3 SHA `A1F676…` 核对；R0 报告 `FA1750…` 承接；测试文件/副本双端 SHA 与任务给定一致。✓
