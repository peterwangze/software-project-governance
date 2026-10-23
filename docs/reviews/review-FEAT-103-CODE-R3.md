# REVIEW-FEAT-103-CODE-R3 — M2-FIX（R2 的 1×P1 + 3×P2 + P3）独立复审

- 日期：2026-10-22（Asia/Shanghai；命令时刻均 **UTC**）
- **结论：APPROVED_WITH_NOTES**
- **unresolved_blockers=0**
- P0=0，P1=0，P2=1，P3=4
- 审查对象：隔离副本五个文件（本次只改 registry index + session-controller index）、M2-FIX 三套件 + M1 原套件、三枚对照；报告 `.codex-sandbox/FEAT-103/M2-FIX-REPORT.md`；审计目录 `m2fix-audit/`。
- 基准：R2 `docs/reviews/review-FEAT-103-CODE-R2.md`（NEEDS_CHANGE/1）；设计 R4：任务输入 SHA `D383D7E9…`（512 行），**审查期间 Architect 并发写入 R4-P2，当前 SHA `30E6FF022EB309FF1895ADE1BA15B9C25D53154FAF9F75792E01339C2EBE7FB5`（515 行）**；本报告以当前文本为准并注明并发状态。
- Reviewer：同一实例；只写本报告 + scratch `.codex-sandbox/FEAT-103/review-code-r3/`；未改产品/设计/副本，未 stage/commit，未启动宿主。

## 1. 对象绑定（双端 SHA / diff 行数）

### 1.1 安装态基线（只读）

| 文件 | SHA-256 | 行数 |
| --- | --- | ---: |
| registry `lib/index.js` | `95EDCC66175A87091BA90FE0809246821DF470BF960E1CFD725B5CA6BAAF4F07` | 811 |
| registry `lib/types/index.d.ts` | `522519826855083E6CB1B57386D8C779020CFDA186B98C38E3E237BEC3B477A7` | 138 |
| session-controller `lib/index.js` | `A9801ACB577B03053C5D5A3191FF555C5F1D791D0ACDDEC113BEA4511E33B386` | 3367 |
| agent types `lib/types/index.d.ts` | `3531899158347FF10627228732C67462C78EA0352E31A7EABC19631F90B08BC1` | 379 |
| agent-loop `lib/index.js` | `CF57E3ECD487AC5C2553455AAA5CEF2C6FB41E6BD61BE5AA455675D1D7193033` | 2023 |

### 1.2 M2-FIX 副本

| 文件 | SHA-256 | 行数 | 相对安装态 |
| --- | --- | ---: | --- |
| registry `lib/index.js` | `FEF13A41927CB609E42C8798CFD0AC7788F1E327830D8F411BFEA47AB10CC197` | **1207** | **+396/−0** |
| registry `lib/types/index.d.ts` | `41CFF85A4F4D3932CFE557DE67BED2742B7FBE2A9C0DBA962369C83E096EDC50` | 220 | +82/−0（本轮未改） |
| session-controller `lib/index.js` | `B4BA1E7B9F0499D01E774D74187A3F3D6EE4B1A656ECB72E8B0A445E8193355E` | **3416** | **+68/−19** |
| agent types `lib/types/index.d.ts` | `0855B0E51ED9E612F89BABFFE45B158E3958A37F9E5FB19837D01BB24A0E9098` | 387 | +8/−0（未改） |
| agent-loop `lib/index.js` | `0C0C589F16B4227CDA50B1F02E3FC66AAD52671761D551BFA59CC1AF0253D9B1` | 2036 | +16/−3（未改） |

- registry 相对 R2 的 1181 行 +26；controller 相对 R2 的 3406 行 +10；与 M2-FIX 报告一致。
- **既有 registry `register/select/mount/list/diagnostic/retain` 零改动**（registry 仍为纯增量 +396/0）；controller 的既有改动行是 CH-3/D1 设计内的 `composeAgent`/`resumeObserved`/`claim`/`reuseLive`/`reuseSetup`/`createAgent`/`fork` 装配点（+68/−19），不是 legacy registry 路径。`ctx.root` 谓词未改回（registry :651）。

### 1.3 测试 / 报告 / 对照

| 文件/对象 | SHA-256 |
| --- | --- |
| `tests/t-m2-registry-admission.mjs`（A1-A9） | `14E499CBBB44753AE56D62E276CB8262B0751A16512F63E90B0D596169524A2A` |
| `tests/t-m2-controller-branches.mjs`（C1-C13） | `60BE4AA0CAFB9C9ACF3332211E43426A70984463E9FD90676E5F0BA6AF65A1D8` |
| `tests/t-m2-d1-wiring.mjs`（未改） | `BE4FA0CCE1E85C26A377DC3EED7276CF2A355FD1D3BCE14BE21291B8309202B1` |
| M1 原套件 `.codex-sandbox/FEAT-103/tests/t01-owned-registration.mjs` | `FA43EAC75D534FBA2107FEFFC7FDF10DAB6E556EA291AC09E167F8D8F12BF2A2` |
| `M2-FIX-REPORT.md` | `24AA13EF5F5D8775621FCDE270B1331E16147F4FE84A5471C9021004A41E66E7` |
| `controls/prefix-controller/lib/index.js`（R2 前形态） | `D8F2758ADDFB6248D0180A13595AC22F2AF01F5AD88300A82CE162BB8613F1F6`（无 `frozenGeneration`） |
| 设计 R4（审查起） | `D383D7E9…`（512 行；任务输入） |
| 设计 R4（审查时当前） | `30E6FF022EB309FF1895ADE1BA15B9C25D53154FAF9F75792E01339C2EBE7FB5`（515 行；R4-P2 并发） |
| R2 报告 | `AD32DF7CEC952CAA528047C97CD41A13FC7C0BAA38B9C52879C729CE8F0544D9` |

- **对照源证明**：
  - 安装态 controller 对照：`session-controller-testable.mjs` = 安装态源 + 追加 export，期望/实测哈希 `f6c7b9860c7c91a9e114ba062fc6cd8efa91489716635421153fcbd390bf074a`，文件不含 `frozenGeneration`。
  - pre-fix 对照：`controls/prefix-controller` 不含 `frozenGeneration`（grep 仅 current controller 有 :381-383）；由 M2-FIX 报告声明为 R2 前形态。
  - C12 自检：`FEAT103_C12_SELFTEST=leak` 注入合成 HELD token。

## 2. 逐项判定

| 项 | 判定 | 证据/说明 |
| --- | --- | --- |
| R2-P1 跨代回退 | **PASS** | controller `attemptWithAdmission` :372-390 首 attempt 写 `composition.frozenGeneration`，后续传 `{id, generation}`；registry `acquire` :884-910 在 `users++` 前做 `frozen !== generation → closed`，record 不存在且 pinned 也 closed；C13 同时断言错误码、id 双证、`create=0`、`ACQUIRE_CALLS[1].spec.generation===G1.generation`、`G2.users=0`、`definitions.get("g1")===G2`；C7/C8 补身份；A9 stale/current pinned；pre-fix 对照 10/13（C7/C8/C13 失败）。 |
| R2-P2-1 closedIds 时机 | **PASS** | `beginRegistration` :664-668 在 record 插入后才 `closedIds.delete`；A7 closed→`{owner:{}}` 失败 begin→仍 closed→成功 begin 重开；C13 的 G2 成功注册清除墓碑后 pinned G1 仍 closed。 |
| R2-P2-2 C11/C12 | **PASS** | C11 真跑 `SessionCommandController.fork()`（`buildForkSeed` 真实、fake factory），断言 create=1/seed/acquire 1/COMMITTED/HELD0；C12 真实聚合 `allTokens>0`、HELD=0、真实 record `_signalListener===undefined`、`ownedRecords===0`；`FEAT103_C12_SELFTEST=leak` 得 12/13（C12 held=1）；安装态对照 1/13（仅 C2）。 |
| R2-P2-3 attach 事务化 | **PASS（join）/ NOT_RUN（rebind）** | attach :917-960：join/rebind 成功后才 `ATTACHED`；join 抛错回滚 `bindings.delete`+`users--`；A8 用真实 attach + `ctx.effect` 抛错，断言 token HELD、users=1、binding 不存在、release 后 0。**rebind 抛错分支未构造，如实 NOT_RUN**（M2-FIX 报告 §5.5）。 |
| M1 遗留 P3 | **PASS** | signal attach-after-close 守卫（:672-686）、handler 状态复判；公开 `OWNED_CLOSE_REASONS` 四值、`activation-failed` 内部集合/类型分离；T01 9/9；D1 CH3-5。 |
| 设计 R4 §5.3 #6/#7 | **PASS** | 冻结 generation 传递、pinned acquire、C13；错误码映射（R4-P2 N-R4-1）当前设计已明确 owned 路径 `agent-preset/closed`、legacy `REGISTRATION_CLOSED`；实现用 `agent-preset/closed`，与当前 R4 一致。 |
| 设计 R4 §5.4 | **PARTIAL** | attach 事务化/冻结一致/append 回滚均实现；**成功后的 `collect(previous)` 失败仍未隔离**（registry :1017 直接 `await this.collect(previous)`，R4 §5.4 :289 明说必须隔离为诊断/日志）；见 P2-1。 |
| 设计 R4 §5.6 | **PARTIAL** | closed/not-found 分类、失败保留、legacy 不写、成功重注册清除、旧 token 闭包均实现；**attach 未做 closed/retired 前置判定**（R4 §5.6 :301 把 attach 列为判定点；当前 attach 只检查 token HELD，close-before-attach 由 publicationCommit 兜底）；**closedIds 清除早于 `record.start()`**（:668 vs :688；R4 说“分配/入索引与启动之后”，任务派单说“插入成功之后”）；见 P3-1/P3-2。 |
| CH-1.6 | **PASS** | activation-failed 终态/closedIds 保留/first-reason-wins 在 M1 代码与 T01-g/h；R4 CH-1.6 文本一致。 |
| D1 | **PASS（结构）/ NOT_RUN（真实 host）** | 未改；d1 10/10；真实 publish 链 NOT_RUN（M2-FIX 报告 §5.1 诚实披露）。 |

## 3. 独立复跑

### 3.1 正向（固定副本）

| # | 套件 | UTC 2026-10-22（起→止） | exit | 实数 |
| --- | --- | --- | ---: | --- |
| F1 | M1 原套件 | 06:17:21.042Z→06:17:21.656Z | 0 | **9/9** |
| F2 | registry-admission A1-A9 | 06:17:21.656Z→06:17:22.146Z | 0 | **9/9** |
| F3 | controller-branches C1-C13 | 06:17:22.146Z→06:17:22.494Z | 0 | **13/13** |
| F4 | d1-wiring | 06:17:22.494Z→06:17:22.691Z | 0 | **10/10** |

### 3.2 三枚对照

| 对照 | UTC（起→止） | exit | 实数 |
| --- | --- | ---: | --- |
| pre-fix controller（R2 前形态） | 06:17:22.691Z→06:17:23.042Z | **1** | **10/13**；C7/C8（缺冻结身份）、C13（跨代未被 closed 拦）失败 |
| 安装态原 controller | 06:17:23.042Z→06:17:23.399Z | **1** | **1/13**；仅 C2 通过；C12 因无 token 可聚合失败 |
| C12 自检 `FEAT103_C12_SELFTEST=leak` | 06:17:23.399Z→06:17:23.752Z | **1** | **12/13**；C12 FAIL `held=1` |
| 安装态原 controller（最终复核源） | 06:19:25.564Z→06:19:25.958Z | **1** | 1/13；testable 源哈希 `f6c7…` 与安装态源+export 完全一致，无 `frozenGeneration` |

- 与 M2-FIX 报告 §3 的 9/9、13/13、10/10、9/9、10/13、1/13、12/13 一致。
- 对照控制源不依赖缓存：pre-fix 对照无 `frozenGeneration`；安装态对照源实测哈希与安装态源+export 相等；均不是另一副本。
- 测试/副本 SHA 前后不变；安装态五文件 SHA 前后不变。

## 4. Findings

### P2

**R3-P2-1 — `selectWithAdmission` 成功后 `collect(previous)` 失败未隔离（R4 §5.4 明规）**

- registry :1014-1018：token 已 COMMITTED、binding 已提升、`previous.users--` 后直接 `await this.collect(previous)`；若旧 scope dispose 抛错，方法 reject，但切换已提交，调用方看到错误而状态已变。
- R4 §5.4 :289 明确“成功后 `collect(previous)` 的失败必须隔离为诊断/日志，不得让已提交与返回错误不一致（R2-P3-2）”。当前代码未实现，测试也未注入 collect reject。
- 建议：try/catch 包裹 collect，记录 logger.warn/诊断并照常返回提交 id；补一条旧 scope dispose reject 仍返回成功且状态 committed 的测试。**rebind 抛错分支**在 M2-FIX 报告 §5 第 5 条已如实标 NOT_RUN。

### P3

**R3-P3-1 — `attach` 未做 closed/retired 前置判定**

- R4 §5.6 :301 把 `attach` 列为 closed 判定点；当前 attach :917-960 只检查 token HELD/scope，不检查 record 是否仍同 generation/open。close-before-attach 时 attach 会 join/rebind 一个 retired generation，随后 publicationCommit（:955-957）才拒绝；A3 只测 attach 后 close，未测 close 后 attach。
- D1 fence 最终保护发布，故 P3；建议 attach 前加 `record.generation === generation && !generation.retired && record.state !== "closed"` 并补 close-before-attach 用例（或由 R4 明确 attach 不判、只靠 publicationCommit）。

**R3-P3-2 — closedIds 清除早于 `record.start()`，与 R4 §5.6 的“启动之后”有文本差**

- :668 `closedIds.delete` 在 :688 `record.start()` 之前；任务派单只要求“插入成功之后”，实现满足该口径；R4 §5.6 :302 写“record 分配/入索引与启动之后”。同步段内无外部交错，影响有限；建议按 R4 移到 start 成功后（或 R4-P2 明确“插入后即可”），并补“start 前失败保留墓碑”的负例。

**R3-P3-3 — M1 残余 + 新小项**

- `OWNED_INTERNAL_TERMINAL_REASONS` 已声明但代码未引用（失败分支直接写 `activation-failed`）；D1 CH3-5 只检查集合存在。T01-i 仍只覆盖 close 路径，failure/drain 的 detach 未计数。`attemptWithAdmission` :383 若 `presets.acquire` 返回 undefined 会读 `admission.generation` 抛 TypeError（真实 registry 不会，属防御边）。
- 均为 P3，非本轮 P1/P2 回归；建议后续在 CH-1.6/类型测试中补齐。

**R3-P3-4 — R4-P2 并发文本/状态**

- 任务输入 R4 `D383D7E9…`（512 行）；审查期间 Architect 写 R4-P2，当前 `30E6FF…`（515 行）。当前 §5.3 已加“错误码映射 N-R4-1”，明确 owned 路径 `agent-preset/closed`、legacy `REGISTRATION_CLOSED`，实现/测试采用前者，**命名已对齐**；但 §5.6 :307 仍写“清除时机仍在校验前（M2 P2-1 未关闭）”，与 M2-FIX 实现矛盾（R4-P2 尚在进行）。本报告按当前 30E6FF 复核；若 R4-P2 继续改文本，需再绑定。
- **不构成代码 finding**；记录设计文本并发/状态偏差。

## 5. 测试质量 / 覆盖

- **C13**（真实 registry + 真实 controller 分支）同时断言错误码、id 双证、create=0、spec 冻结对象、G2.users=0，强于 R2 的计数断言；**C7/C8** 已升级为身份断言；**A9** stale/current pinned；**A7** 失败重注册保留/成功重开；**A8** 真实 attach join 失败；**C11** 真跑 fork；**C12** 真实聚合 + selftest。非空转证据充分。
- **未覆盖**：rebind 抛错分支（A8 只覆盖 join）；attach close-before；select 成功 collect 失败；真实 host publish/`sessions.enter` 链；真实 fork seed/workspace/持久化；legacy register/list/retain/disposer；storage gap；CH-2/T06+；T10 性能；webhook；多 Cordis。M2-FIX 报告 §5 已诚实披露大部分。
- **C12 installed 1/13** 是设计意义正确的失败（无 token 可聚合），不是回归。
- **D1 仍为源码级断言 + 模块加载**；真实 host NOT_RUN，未冒充。

## 6. 命令审计（本轮 Reviewer）

| # | label | UTC 2026-10-22（起→止） | exit | 要点 |
| --- | --- | --- | ---: | --- |
| F1 | M1 原套件 | 06:17:21.042Z→06:17:21.656Z | 0 | 9/9 |
| F2 | registry A1-A9 | 06:17:21.656Z→06:17:22.146Z | 0 | 9/9 |
| F3 | controller C1-C13 fixed | 06:17:22.146Z→06:17:22.494Z | 0 | 13/13 |
| F4 | d1-wiring | 06:17:22.494Z→06:17:22.691Z | 0 | 10/10 |
| C1 | pre-fix controller | 06:17:22.691Z→06:17:23.042Z | 1 | 10/13；C7/C8/C13 |
| C2 | installed controller | 06:17:23.042Z→06:17:23.399Z | 1 | 1/13 |
| C3 | C12 selftest leak | 06:17:23.399Z→06:17:23.752Z | 1 | 12/13；held=1 |
| C4 | installed controller（最终源复核） | 06:19:25.564Z→06:19:25.958Z | 1 | 1/13；testable 哈希 `f6c7…` 匹配安装态源+export |
| C5 | SHA/git/边界只读 | 测试前后 | 0 | 五文件/安装态/设计哈希 |

- 全部为 `node` 进程内 Cordis；未启动宿主；未读写真实 `~/.dsh`；`DSH_HOME` 仅设到 `.governance/sandboxes/feat103-code-r3-20261022T061659Z`（测试不消费）。
- 生产者的 M2-FIX 命令未重跑；其 06:13/06:14 自报实数与我的独立复跑一致。

### Reviewer 证据 SHA-256（`.codex-sandbox/FEAT-103/review-code-r3/`）

| 文件 | SHA-256 |
| --- | --- |
| `f1-m1.log` | `1FC63DBD968B6F4E96ACAE7B6A87CFAD5736B9CE13D073133119C61BA613570F` |
| `f2-registry-admission.log` | `4E9B27283A84D858F9A35209F367C1CAA94AE3DF5754DF03A76E081046A8E57C` |
| `f3-controller-fixed.log` | `502AF2CE538960D579C852C780F11382A8BFF0D1255DDF4CAA0527D1D218EC41` |
| `f4-d1-wiring.log` | `159D2F72B946988F6E6A7E1AE859D837895B3F80E009F07D2C87B52D07CEA4D3` |
| `c1-controller-prefix.log` | `69D198C64F19EA53C869EDF123D7875A308D2186091BFD1325ED9CC66D2CA2D0` |
| `c2-controller-installed.log` | `C54530D3A2A0F6EBCC8A2182DB7998708959868235CE39B25CF477FE51DF5A1E` |
| `c3-c12-selftest.log` | `45FA0EFF841F14350A768CF6807EA79E1836F7EFC2D1FCA3BFDF6FEDDFAF1D92` |
| `c4-controller-installed-final.log` | `C54530D3A2A0F6EBCC8A2182DB7998708959868235CE39B25CF477FE51DF5A1E` |

## 7. 边界合规

- **安装态 SDK**：五文件 SHA 前后与 R2 记录逐位一致（§1.1），只读；无写入。
- **仓库**：`git status --porcelain -uno` 仅既有暂停 WIP 两行；`git diff --cached` 空；HEAD `2ed8bb4`；无产品代码/治理记录改动。
- **设计**：审查期间 Architect 并发写 R4-P2（`D383…`→`30E6FF…`）；Reviewer 只读，无设计写入；当前 §5.3 N-R4-1 映射已对齐，§5.6 :307 状态行仍滞后（P3）。
- **Cordis 核心 / loader / scope / Session 核心**：未改；补丁面仅 §1.2 五文件（本轮实际改 2 个）。
- **宿主 / 真实 `~/.dsh`**：无 dsh 进程；未读写 home。
- **写面**：只写本报告 + scratch；runner 生成的 `session-controller-testable.mjs` 是测试专用“受测源 + 追加 export”，不是产品/副本实现改动。

## 8. NOT_RUN / 诚实缺口

- 真实 host boot / AgentLoop publish 链（D1 仅源码/加载断言 + A3 fence）。
- T03/T05 storage gap；真实 fork seed/workspace/持久化（C11 用 fake factory/服务）。
- legacy `register`/`list`/`retain`/disposer 回归（R4 §5.6 明示 legacy 不写墓碑）。
- **attach rebind-抛错**分支（A8 只覆盖 join 抛错）。
- attach close-before、select 成功 collect 失败、C12 真实 host 面、CH-2/T06+、T10、webhook、多 Cordis、0.1.x。
- 上述均未冒充通过；M2-FIX 报告 §5 与本节一致。

## 9. 硬门槛自检

1. 未修改产品代码/设计/副本/测试；仅写本报告 + scratch。未 stage/commit/push。✓
2. 每条结论有运行/读取证据（行号、日志、SHA、对照源哈希）；预期失败与 NOT_RUN 如实保留。✓
3. 进程命令先设并断言 `DSH_HOME` 在 `.governance/sandboxes/` 内；无宿主；未读写真实 `~/.dsh`；安装态 SHA 前后一致。✓
4. 设计绑定任务输入 `D383…` 与审查时当前 `30E6FF…`，并记录 R4-P2 并发；对象 SHA 与任务一致。✓

**结论：APPROVED_WITH_NOTES，unresolved_blockers=0。** M2-FIX 的 P1 与三个 P2 均有独立正向/反向证据；剩余 P2-1（select 成功后 collect 失败隔离）与 P3（attach closed 前置、closedIds 清除时机、M1/R4 文本小项）不阻断本轮，但建议在 M3/合入前处理。
