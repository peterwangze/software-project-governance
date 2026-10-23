# REVIEW-FEAT-103-CODE-R4 — M3（CH-2 selector + R3 残留）独立复审

- 日期：2026-10-22（Asia/Shanghai；命令时刻均 **UTC**）
- 机录链：round 10（REVIEW-FEAT-103-R10；承接 R9 = CODE R3 AWN/0 同链新实例——DSH 平台不保留跨派发实例，按先例完整注入上下文承接）
- **结论：APPROVED_WITH_NOTES**
- **unresolved_blockers=0**；P0=0，P1=0，P2=0，P3=2
- 审查对象：M3 后隔离副本六文件 + `.codex-sandbox/FEAT-103/M3-REPORT.md` + `M3-TEST-AUDIT.md`
- Reviewer：Code Reviewer（独立；只写本报告 + scratch `.codex-sandbox/FEAT-103/review-code-r4/`；未改产品/副本/测试/设计/治理记录，未 stage/commit，未启动宿主）

## 1. 对象绑定（双端 SHA 实测复核）

### 1.1 副本（M3 后）

| 文件 | SHA-256（Reviewer 实测） | 行数 | 相对安装态（numstat 实测） | 报告宣称 |
| --- | --- | ---: | --- | --- |
| registry `lib/index.js` | `5ABBA552DA89041EE1A12A8A1A9321B2145019F416991BBCCB7EDECB39835250` | 1280 | **+469/−0** | +469/−0 ✓ |
| registry `lib/types/index.d.ts` | `1B2E6C26CE638E8B1CFD2DBBE385016D330C6ED686D60C60549A41E1B8209E2F` | 232 | +94/−0（M1 82 + M3 12） | ✓ |
| controller `lib/index.js` | `B9999EE6715AF10F31560CE98D8C654A496761909E292C2075DD0F255BBAF7C6` | 3420 | +72/−19（M2 68/19 + M3 +4/−0） | ✓ |
| subagent `lib/index.js` | `16E9F593BD27BFC9BC4AB522418982390EE1B657AADDA13B9B990BED33C3320D` | 3386 | +73/−19（M3 首触） | ✓ |
| subagent `lib/types/child-agent.d.ts` | `2C4B67316024178D62819847A3B953DA74553CC398371619EBD7867ACB28E30A` | 158 | +19/−1（首触） | ✓ |
| agent types `lib/types/index.d.ts` | `0855B0E51ED9E612F89BABFFE45B158E3958A37F9E5FB19837D01BB24A0E9098` | 387 | +8/−0（M2，M3 未改） | ✓ |
| agent-loop `lib/index.js` | `0C0C589F16B4227CDA50B1F02E3FC66AAD52671761D551BFA59CC1AF0253D9B1` | 2036 | +16/−3（M2，M3 未改） | ✓ |

- registry 相对安装态**纯增量保持**（+469/−0，无删除行）——M1 期"legacy 路径零改动"性质未破坏；本轮 registry −10 全部为 beginRegistration 旧注释/旧 delete 行被替换（实测 numstat 与报告 §1.1 论证一致）。

### 1.2 安装态基线（只读；前后一致）

| 文件 | SHA-256（Reviewer 实测） | 对照 |
| --- | --- | --- |
| registry index / types | `95EDCC66…4F07` / `52251982…B477A7` | = R3 §1.1 基线 ✓ |
| controller | `A9801ACB…B386` | = R3 基线 ✓ |
| agent types | `35318991…8BC1` | = R3 基线 ✓ |
| agent-loop | `CF57E3EC…D303` | = R3 基线 ✓ |
| subagent index / child-agent.d.ts | `9A9572E7…4168` / `F885F282…D71ACF` | = copy-manifest 登记的 copy-time SHA ✓（七文件安装态零写入） |

### 1.3 报告/设计/基准

| 对象 | SHA-256 | 备注 |
| --- | --- | --- |
| `M3-REPORT.md` | `AEA24919…`（173 行） | 与任务给定一致 ✓ |
| `M3-TEST-AUDIT.md` | `1E50A514…`（65 行） | ✓ |
| 设计定稿 | `2CA8A9B813E7B0DE…`（549 行，R5 增量） | 审查前与收工两次实测一致（Architect 定稿后无再动）✓ |
| delta base `review-FEAT-103-CODE-R3.md` | `11893E5A…` | ✓ |

## 2. 逐项判定（代码锚点 Reviewer 亲读核验，非报告转述）

| 项 | 判定 | 事实（Reviewer 实读行号） |
| --- | --- | --- |
| **CH-2 registry 侧** | **PASS** | `ownedGenerations` WeakMap 类字段 :605-610（注释明示"不做 id 反查——id 表可能已换代"）；OwnedRecord `set generation` :433-440（legacy register 普通对象不经此 setter，构造上永不入表）；`acquireParentAdmission` :913-923——:917 `generationFor(parentCtx)` 在方法首个 await 前**同步**求值（S-U3）；preset-free/legacy 父 → :918/:920 return `undefined`（子走 legacy composeFrom）；owned 父关闭/换代（`definitions.get(owner.id) !== owner`）/retired → :921 throw `agent-preset/closed`；:922 `acquire({id, generation})` 钉同一 generation 对象（acquire :964 `frozen !== generation → closed` 兜底）；`acquire({parent})` 路由 :939 |
| **CH-2 subagent 侧** | **PASS** | `applyChildCompositionOwned` :404-408（undefined 回退 legacy :405；`attach(childCtx)` 消费冻结 token → overrides → 返回 commit；无另一分支回退）；materializeTracked :1832-1836（`typeof presets.acquire === "function"` 能力门 + 独立 `{id}` / 继承 `{parent}` 双分支，await 在 setup 外=factory-attempt 边界）；S-U4 顺序保真（独立 :1841 在 append :1843-1848 前；继承 :1850 在其后）；setup 返回 compositionCommit :1854（含 publicationCommit 的 D1 fence 交回 AgentLoop）；:1874-1877 `finally { admission?.release() }`（ATTACHED/COMMITTED no-op） |
| **类型面** | **PASS** | child-agent.d.ts :9-10（PresetAdmission/AgentSetupCommit 导入）+:108（`applyChildCompositionOwned(…): AgentSetupCommit | Promise<AgentSetupCommit> | void | Promise<void>`）；registry types :98（ownedGenerations private）、:114/:122（acquire 重载 `{id}` / `{parent}`）、:126（acquireParentAdmission） |
| **R3-P2-1** | **PASS** | selectWithAdmission 成功路径（token COMMITTED :1077、binding 提升 :1066-1068、holders 转移 :1078-1079）之后 `await this.collect(previous)` 包 try/catch :1086-1090，失败 `logger.warn` 诊断、:1091 照常返回提交 id——R4 §5.4 "已提交与返回错误不一致"禁止条款满足；A10 独立复跑通过 + prefix 对照精确失败 |
| **R3-P3-1** | **PASS** | attach 闭包 join/rebind **之前** :982-983：`live === void 0 \|\| live.generation !== generation \|\| live.state === "closed" \|\| generation.retired → agent-preset/closed`——R4 §5.6 :301 判定点落地；A11+B12 复跑 + prefix 对照失败（"got undefined"=无判定时 attach 成功） |
| **R3-P3-2** | **PASS** | 旧位置 delete 已移除（beginRegistration :657-687 无 closedIds.delete）；:707 `record.start()` 后 :712 `if (record.state === "activating") this.closedIds.delete(definition.id)`——**门控必要且精确**：pre-aborted/close-before-start 的 begin 已被 `close()` 加回墓碑（:466-475/:688-690），无条件移位会清掉它（closed 退化 not-found）；同步窗口论证成立（start() 对已终态 record 是 no-op :443，start 与门控行间无同步代码可翻转 activating）；naive-move 变异体精确证伪（A12 got not-found） |
| **R3-P3-3** | **PASS** | (a) :471 `OWNED_INTERNAL_TERMINAL_REASONS.has("activation-failed") ? "activation-failed" : "explicit"`——声明集合成为 reason 单词唯一来源（与 close() 的 OWNED_CLOSE_REASONS 守卫同构）；(b) T01-i 扩展（M3-TEST-AUDIT #13；T01 9/9 复跑含 failure 路径 detach 计数场景）；(c) controller :383-386 `admission === void 0 → RemoteError("agent-preset/bad-admission")` 类型化 fail-closed（C14 + prefix 对照 got TypeError 精确失败） |

## 3. 设计符合性（对照定稿 `2CA8A9B8` R5 增量）

| 设计收敛项 | 实现一致性 |
| --- | --- |
| F-M3-1 映射注记（§4.4 :253：attach ≡ mountOwned/composeFromOwned，无重复 API） | ✓ `applyChildCompositionOwned` :406 内部消费 attach，全仓无 mountOwned/composeFromOwned 新 API |
| F-M3-2 锚点裁定 a)（§4.2 :229-233：合同锚点 = materializeTracked 编排入口；S-U3 比拟撤销；窗口语义=换代→观察到新代属继承现行代语义/关闭→closed 拒收/无静默路径；备选 b) 成文排除） | ✓ 实现 :1835 acquire 于 materializeTracked factory-attempt 边界 + :917 同步求值；B3/B6/B4 实测支撑裁定依据 |
| F-M3-3 错误面区分（§4.2 :238：spawn 透传 `agent-preset/closed` vs cold 面 NOT_RESUMABLE+cause 且 cause.code 可溯源；共同保证=closed 根因不丢失、无静默回退） | ✓ spawn 面 B4 实测透传；cold 面 :2238-2241（`instanceof SubagentError` 直抛 / 否则包 NOT_RESUMABLE+cause）亲读核验 |
| F-M3-4 记法对齐（§4.2 :221：实现 API `acquire({id}\|{id,generation}\|{parent})` 无 ownerCtx/signal 形参；abort 外层 attempt 边界处置） | ✓ acquire 签名 :938-945 亲读一致 |
| N-R4-4/§5.6 状态行（§11 r5_findings_addressed 六项） | ✓ 状态行更新至 M3 后事实（§5.4 现列 collect 失败隔离；§5.6 现记 closedIds delete after start with activating gate） |

## 4. 独立复跑（Reviewer 全量重跑；`DSH_HOME` 重定向至 `.governance/sandboxes/feat103-code-r4-20261022T0858Z`，测试不消费；每命令后清除）

### 4.1 正向（五套件全绿，与 M3-TEST-AUDIT #9-#13 逐字一致）

| # | 套件 | UTC 2026-10-22（起→止） | exit | 实数 |
| --- | --- | --- | ---: | --- |
| F1 | B（t-m3-child-selector） | 09:00:10.515Z→09:00:10.940Z | 0 | **12 passed / 0 failed** |
| F2 | A（A1-A12） | 09:00:20.697Z→09:00:21.222Z | 0 | **12 passed / 0 failed** |
| F3 | C（C1-C14） | 09:00:21.225Z→09:00:21.562Z | 0 | **14 passed / 0 failed** |
| F4 | d1-wiring | 09:00:21.563Z→09:00:21.757Z | 0 | **10 passed / 0 failed** |
| F5 | T01（仓库根口径） | 09:00:41 前后 | 0 | **9 passed / 0 failed**（JSON total=9） |

- 复跑口径注记：T01 首次在 `feat103-impl` 工作目录下 exit=1——系 Reviewer 运行目录错误（该套件按仓库根口径运行，与 M3-TEST-AUDIT #13 一致）；按仓库根重跑 9/9 exit 0。非产品缺陷，如实记录。
- B 套件输出逐例 PASS B1-B12（含 B3 同步冻结/B6 closed 父拒收/B12 attach 前置换代拒收）；C12 套件不变量（零 HELD/零 listener/零 owned 残留）在新增 C14 spy 参与下仍过；C13 跨代回退在 attach 前置判定加入后仍过。

### 4.2 非空转对照（四组全部按预期 exit 1，失败点与 Developer 审计 #14-#17 逐字一致）

| 对照 | UTC（起→止） | exit | 实数与证伪点 |
| --- | --- | ---: | --- |
| CTRL-A @prefix-registry-m3 | 09:00:48.273Z→09:00:48.821Z | 1 | **10/12**：A10 FAIL（`the committed switch must not reject, got dispose boom`）、A11 FAIL（`close-before-attach must be agent-preset/closed, got undefined`） |
| CTRL-A @naive-closedids-move | 09:00:48.838Z→09:00:49.405Z | 1 | **11/12**：仅 A12 FAIL（`must keep the closed tombstone, got agent-preset/not-found`） |
| CTRL-C @prefix-controller-m3 | 09:01:02.264Z→09:01:02.630Z | 1 | **13/14**：仅 C14 FAIL（`got TypeError: Cannot read properties of undefined (reading 'generation')`） |
| CTRL-B @prefix-subagent | 09:01:02.642Z→09:01:03.072Z | 1 | **2/12**：仅 B5/B11 通过（legacy 保真面恰应通过）；B3/B6/B12 等 10 例 FAIL |

- 对照源为 pre-M3 字节快照（copy-manifest 登记值与 Developer §1.2 一致）；测试装置 `subagent-testable.mjs`/`session-controller-testable.mjs` 为 runner 生成的"受测源+追加 export"，既有 M2 机制，非副本实现改动。

## 5. 既有面零回归

- numstat 实测（§1.1）：registry 纯增量保持；controller/subagent 的 −19 各属 M2 装配点与 M3 materializeTracked 本地分支重排（CH-3/CH-2 设计内）；agent types/agent-loop M3 未改（SHA=M2 期值）。
- M2 已批语义亲读抽核：controller `frozenGeneration` pin 逻辑 :381-387 保持（C13 过）；attach 事务化（join 失败回滚 bindings.delete+users--）:990-1001 保持（A8 过）；acquire frozen 校验 :964 保持。
- d1-wiring 10/10（未改套件）；T01 9/9（T01-a..h 既有断言零改动，仅 T01-i 追加场景）。

## 6. Findings

**P0/P1/P2：无。**

### P3

**R4-P3-1 — M3-REPORT §2.2 落点锚点区间起点偏差 8 行（纯报告文本精度）**
- 报告写 `:1072-1090`；collect 隔离实际从注释 :1080 起、try/catch :1086-1090（:1072 是 append 失败回滚段）。区间覆盖正确落点、语义无误；后续引用建议以 :1086-1090 为准。

**R4-P3-2 — spawn/fork provider 显式 preset 能力拒绝路径（subagent :3366 一带）无 M3 新增用例**
- Developer 已在 NOT_RUN #4 披露（现行行为保留，属 M1 期覆盖面）；R5 定稿 §7 亦未将其列入 M3 面。非隐瞒、非回归；若后续版本触碰该分支需补用例。

## 7. F-M3 findings 如实性（Developer 披露 4 项的独立核验）

全部**如实**（§3 表逐项亲读核验）；写面=副本 5 文件 + 测试 2 改 1 新 + 对照 3 枚 + 变异体 1 枚 + 报告/审计——全部落在设计 §7 预批写面（§7 L360 明列 packages/subagent/subagent 两文件）与既有测试面惯例内，**未扩大授权**。

## 8. 边界合规

- **安装态 SDK**：七文件（含 subagent 两文件）SHA 与 R3 基线/copy-manifest 逐位一致；零写入。
- **仓库**：`git status --porcelain -uno` 仅既有暂停 WIP 两行（commit-msg/test_hooks.py）；`git diff --cached` 空；HEAD `2ed8bb4`；无 stage/commit/push。
- **设计**：审查前与收工两次实测 `2CA8A9B8…` 一致（Architect R5 定稿后无并发写入——本轮无 R9 期 P3-4 类并发偏差）。
- **宿主/真实 ~/.dsh**：无 dsh 进程；未读写 home；`DSH_HOME` 仅设到自建 `.governance/sandboxes/feat103-code-r4-20261022T0858Z`（测试不消费）。
- **Reviewer 写面**：仅本报告 + scratch `review-code-r4/`；测试装置生成物（testable.mjs）属测试面既有机制。

## 9. NOT_RUN / 诚实缺口（与 M3-REPORT §4 一致，Reviewer 确认无冒充）

真实 host boot/AgentLoop publish 链（D1 仍源码/加载级 + fence 层断言）；T06+ storage gap 注入与真实持久化（B/C factory 为 fake 编排）；legacy 宿主侧回归（registry legacy 函数体零触碰 + B7 形状用例，宿主级未跑）；spawn/fork provider 运行面（:3366 能力拒绝，P3-2）；T10 性能/webhook/多 Cordis/0.1.x；A12 对 M2-FIX 旧码观测等价（非空转证据=naive-move 变异体，定性准确）；T01-i failure 路径断言为覆盖补齐（M1-FIX 起逻辑已存在，无行为差异预期，未单独跑 prefix 对照）。

## 10. 命令审计（Reviewer 本轮）

| # | label | UTC 2026-10-22（起→止） | exit | 要点 |
| --- | --- | --- | ---: | --- |
| C0a | 对象/报告/设计/基准 SHA 批量 | 08:52-08:53Z | 0 | §1 全表（含行数口径修正说明：Measure-Object -Line 不计空行，报告行数以 .Count 为准） |
| C0b | 安装态七文件 SHA | 08:53Z | 0 | §1.2（subagent 两文件按 copy-manifest 定位） |
| C1 | B 套件 | 09:00:10.515Z→09:00:10.940Z | 0 | 12/12 |
| C2 | A 套件 | 09:00:20.697Z→09:00:21.222Z | 0 | 12/12 |
| C3 | C 套件 | 09:00:21.225Z→09:00:21.562Z | 0 | 14/14 |
| C4 | d1-wiring | 09:00:21.563Z→09:00:21.757Z | 0 | 10/10 |
| C5 | T01（错误目录口径） | 09:00:21.758Z→09:00:21.839Z | 1 | Reviewer 目录错误（见 §4.1 注记） |
| C5b | T01（仓库根口径） | ~09:00:41Z | 0 | 9/9（JSON total=9） |
| C6 | CTRL-A @prefix-registry | 09:00:48.273Z→09:00:48.821Z | 1 | 10/12；A10/A11 |
| C7 | CTRL-A @naive-move | 09:00:48.838Z→09:00:49.405Z | 1 | 11/12；A12 |
| C8 | CTRL-C @prefix-controller | 09:01:02.264Z→09:01:02.630Z | 1 | 13/14；C14 |
| C9 | CTRL-B @prefix-subagent | 09:01:02.642Z→09:01:03.072Z | 1 | 2/12；B5/B11 |
| C10 | numstat×7 + git 边界 + 设计 SHA 复核 | ~09:05Z | 0* | *git diff --no-index 有差异 exit 1 属语义；§5/§8 |

- 全部 `node` 进程内 Cordis；每命令 `DSH_HOME` 重定向自建隔离目录并清除；无宿主、无真实 home 读写。

## 11. 结论

**APPROVED_WITH_NOTES，unresolved_blockers=0。** M3 五项（CH-2 主项 + R3-P2-1 + R3-P3-1/2/3）全部有 Reviewer 亲读代码锚点 + 独立复跑正向 + 精确失败对照的三重证据；设计定稿 R5（2CA8A9B8）符合性逐项成立；既有面零回归；边界红线全部合规。两条 P3（报告锚点精度/能力拒绝路径无新用例——均已披露）不阻断。FEAT-103 M3 代码面复审通过；设计 R5 增量的独立聚焦复核为并行另一审（本报告不覆盖设计文本自身质量）。
