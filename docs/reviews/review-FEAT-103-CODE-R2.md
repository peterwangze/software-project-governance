# REVIEW-FEAT-103-CODE-R2 — M2（B3 CH-3.1~3.5 + D1 publication fence）独立复审

- 日期：2026-10-22（Asia/Shanghai；命令时刻均 **UTC**）
- **结论：NEEDS_CHANGE**
- **unresolved_blockers=1**
- P0=0，P1=1，P2=4，P3=5
- 审查对象：隔离副本 `.governance/sandboxes/feat103-impl/upstream/` 五个文件 + M2 三套件 + M1 原套件；报告 `.codex-sandbox/FEAT-103/M2-REPORT.md`；审计 `.codex-sandbox/FEAT-103/M2-TEST-AUDIT.md`。
- 基准：R1 `docs/reviews/review-FEAT-103-CODE-R1.md`（AWN/0）、设计 R3 `A1F676EE27056F0C8BC32BE9F27DC31934EFF25156A75DF7B374E2DA80A008CF`。
- Reviewer：同一实例；只写本报告 + scratch `.codex-sandbox/FEAT-103/review-code-r2/`；未改产品/设计/副本实现，未 stage/commit，未启动宿主。

## 1. 对象绑定（双端 SHA）

### 1.1 安装态基线（只读）

| 文件 | SHA-256 | 行数 |
| --- | --- | ---: |
| `dsh-agent-preset-registry/lib/index.js` | `95EDCC66175A87091BA90FE0809246821DF470BF960E1CFD725B5CA6BAAF4F07` | 811 |
| `dsh-agent-preset-registry/lib/types/index.d.ts` | `522519826855083E6CB1B57386D8C779020CFDA186B98C38E3E237BEC3B477A7` | 138 |
| `dsh-api-session-controller/lib/index.js` | `A9801ACB577B03053C5D5A3191FF555C5F1D791D0ACDDEC113BEA4511E33B386` | 3367 |
| `dsh-agent/lib/types/index.d.ts` | `3531899158347FF10627228732C67462C78EA0352E31A7EABC19631F90B08BC1` | 379 |
| `dsh-agent-loop/lib/index.js` | `CF57E3ECD487AC5C2553455AAA5CEF2C6FB41E6BD61BE5AA455675D1D7193033` | 2023 |

### 1.2 M2 副本

| 文件 | SHA-256 | 行数 | 相对安装态 |
| --- | --- | ---: | --- |
| registry `lib/index.js` | `5158B6BD3318D83696B2E91979D22F685EB517EE94AFA5AAF534EB06F17D7846` | **1181** | **+370/−0** |
| registry `lib/types/index.d.ts` | `41CFF85A4F4D3932CFE557DE67BED2742B7FBE2A9C0DBA962369C83E096EDC50` | 220 | +82/−0 |
| session-controller `lib/index.js` | `56AE3326FD4A596365828A942D57698380C84C84A8AD779E7A406B64C9A6CB7B` | 3406 | +58/−19 |
| agent types `lib/types/index.d.ts` | `0855B0E51ED9E612F89BABFFE45B158E3958A37F9E5FB19837D01BB24A0E9098` | 387 | +8/−0 |
| agent-loop `lib/index.js` | `0C0C589F16B4227CDA50B1F02E3FC66AAD52671761D551BFA59CC1AF0253D9B1` | 2036 | +16/−3 |

- **行数勘误**：任务表与 `M2-REPORT.md:27` 写 1171 行；实测 **1181** 行。811 + 370 = 1181，SHA 不变，属报告/任务表笔误（P3，见 §4-P3-4）。
- `git diff --no-index --numstat` 与上表一致；registry/types/agent types 为纯增量；controller/agent-loop 有既有行改动（见 §5 回归）。

### 1.3 测试 / 报告 / 对照

| 文件 | SHA-256 |
| --- | --- |
| `tests/t-m2-registry-admission.mjs` | `6F9DEFB7FF564669951CC500E2FE2C79DACB327D71E379FA5C9056656737EB5B` |
| `tests/t-m2-controller-branches.mjs` | `ACD8D802D687527ABA9D3482E641D9F5BB41347136D2CA41C7DAB411C596FE05` |
| `tests/t-m2-d1-wiring.mjs` | `BE4FA0CCE1E85C26A377DC3EED7276CF2A355FD1D3BCE14BE21291B8309202B1` |
| M1 原套件 `.codex-sandbox/FEAT-103/tests/t01-owned-registration.mjs` | `FA43EAC75D534FBA2107FEFFC7FDF10DAB6E556EA291AC09E167F8D8F12BF2A2` |
| `M2-REPORT.md` | `C35FD656B601D99161AC16F69F7B537465635DA86CA0F3BEC56CFEFA2C097FB6` |
| `M2-TEST-AUDIT.md` | `A7421DFE6ADDE082AB3DCFCC972E308F037B37660BC1CBC489714E02A0376FC0` |
| 设计 R3 | `A1F676EE27056F0C8BC32BE9F27DC31934EFF25156A75DF7B374E2DA80A008CF` |
| R1 报告 | `54EE4C3749508A2CC8053689FA47753D45FE3A8ADF853ED32171132C2F625AF7` |

- 非空转对照使用 **安装态原 controller**：`FEAT103_CONTROLLER=<installed>/dsh-api-session-controller/lib/index.js`；对照生成的 `session-controller-testable.mjs` 期望哈希 `398edc1bdc1a135b15e9e985e8058edb1e7504dd58583460b1164486d8bae6b9`，实测一致；文件不含 `attemptWithAdmission`（证明读的是安装态原始字节，不是另一副本）。

## 2. 逐项判定

| 项 | 判定 | 证据/说明 |
| --- | --- | --- |
| CH-3.1 `composeAgent` 零 acquire / 零 mount | **PASS** | controller `composeAgent` 只 `resolve`，返回 `{agentPreset, presets}`；C1（零 acquired/mount） |
| CH-3.2 token `HELD→ATTACHED→COMMITTED`、`release` 仅 HELD、冻结 generation | **PASS（主路径）/ P2 异常出口** | registry `acquire`/`attach`/`release` :880-943；A1/A3；`attach` 在 :911 先置 ATTACHED，join/rebind 抛错时无回滚（§4-P2-3） |
| CH-3.3 live switch 事务 | **PASS** | `selectWithAdmission` :955-999；A4（成功 rebind/append/COMMITTED/旧 users 0）、A5（append 失败回滚、不 collect、token HELD）、A6（locked 不动） |
| §5.4 append 失败回滚 / 成功 collect | **PASS** | A5/A4；回滚 `binding.parent.rebind(previous.key)`、`generation.users--`，成功才 `previous.users--`/`collect` |
| CH-3.4 失败分类 / 不跨代 | **FAIL（P1）** | **StartedSinceObserved / SessionAlreadyOwned（无 live）回退 createMinted 按 id 重新 acquire 当前 generation**，composition 不携带冻结 generation；G1 close→G2 同 id 重注册时会静默取 G2（§4-P1-1）；C7/C8/C9 只计 acquire 次数，未断言 generation 身份 |
| CH-3.5 `reuseSetup` 透传完整 commit | **PASS** | `reuseSetup` :522-529；先 blank 复查再 setup，append 在 setup 内；C7/C10 |
| D1 publication fence | **PASS（结构）/ NOT_RUN（真实 host）** | agent-loop :1786-1801 在 `assertLive()` 后、`sessions.enter` 前同步调用；thenable 消费 rejection 并抛错；`setupAndPublish` :1942-1946 commit→append→publish；D1-1..5 为源码/加载断言；真实 publish 链 NOT_RUN（M2 报告 §5.1 已披露） |
| M1 遗留 P3（信号 attach-after-close / close 词表） | **PASS** | beginRegistration :665-682 在 `state !== "activating"` 时不挂 signal，handler 再判状态；`OWNED_CLOSE_REASONS` 四值（:387），`activation-failed` 仅内部集合（:392）且失败分支直接写；types :21-28；T01 9/9；D1 CH3-5 |
| `closedIds` 墓碑 | **机制可接受，但需设计 R4 合同 + 一个 P2 修正** | `closedIds` :594-598、close/failure 写入（:463/:494）、`beginRegistration` 清除（:643）、`acquire` 分类（:885）；**清除发生在 owner 校验之前**，失败的重注册会把 closed 变 not-found（§4-P2-1，探针复现）；R3 未写墓碑生命周期/重注册/legacy 面（§6） |
| 每出口 P/listener 归零 | **COMPOSITE：主路径 PASS，测试不成立** | C3/C4/C5/C6/C7/C8/C9/C10 各自计 HELD；但 C12 是空壳（§4-P2-2），C11 未运行（§4-P2-2/§4-P3-4），attach 抛错出口未覆盖（§4-P2-3） |

## 3. 独立复跑（真实进程内 Cordis 0.2.1-rc.2）

| # | 套件/运行 | UTC 2026-10-22（起→止） | exit | 实数 |
| --- | --- | --- | ---: | --- |
| R1 | M1 原套件（未改） | 05:54:39.270Z→05:54:39.848Z | 0 | **9/9** |
| R2 | registry-admission（A1-A6） | 05:54:39.848Z→05:54:40.326Z | 0 | **6/6** |
| R3 | controller-branches，fixed | 05:54:40.326Z→05:54:40.617Z | 0 | **11/11** |
| R4 | d1-wiring，fixed | 05:54:40.617Z→05:54:40.816Z | 0 | **10/10** |
| R5 | **非空转对照**：安装态原 controller | 05:54:40.816Z→05:54:41.117Z | **1** | **2/11**（C1/C3/C4/C5/C6/C7/C8/C9/C10 失败；C2/C12 通过） |
| R6 | Reviewer closedIds 探针 | 06:03:01.768Z→06:03:02.031Z | 0 | 复现 **bugReproduced=true**（见 §4-P2-1） |

- 与 M2 报告/审计的 9/9、6/6、11/11、10/10、2/11 一致；对照控制源实测哈希 `398edc…` 与安装态源+导出完全一致，且不含补丁符号。
- 安装态 SDK 五文件 SHA 前后不变（§7）；测试/副本 SHA 前后不变。
- Reviewer 首轮 closedIds 探针以“期望正确行为”退出 1（得到 tombstone=false/not-found），随后改为 bug 复现断言退出 0；两次均保留，见 §8。

## 4. Findings

### P1（blocker）

**R2-P1-1 — StartedSinceObserved / SessionAlreadyOwned（无 live）回退按 id 重新 acquire，可跨 generation**

- 事实链：
  - `claim` 的 `StartedSinceObserved` / `SessionAlreadyOwned`（无 live）回退调用 `this.createMinted(request.cwd, composition)`（controller :492/:494）。
  - `createMinted` → `createAgent`（:547/:556）→ `attemptWithAdmission`（:372-378）；其 acquire 参数只有 `{ id: composition.agentPreset }`（:374）。
  - `composeAgent` 返回的 composition 只有 `{ agentPreset, presets }`（:353-367），**没有冻结 generation/token**。
  - registry `acquire` 通过 `this.definitions.get(id)` 取**当前** record（:883/:898），因此 G1 close→G2 同 id 重注册后，回退 acquire 会取 G2。
- 设计冲突：R3 §5.3 分支表 #6/#7（:257-258）明确“回退 attempt 重新 acquire……不按 id 静默换代”；本实现只在“无 G2”时由 `closedIds` 得到 closed，一旦同 id 重注册 `closedIds` 被 `beginRegistration` 清除（:643），回退静默取 G2。
- 测试缺口：C7/C8/C9（controller test :261-309）只断言 acquired 次数与 HELD=0；没有 generation 身份或“G1 close→G2 重注册”场景。A2（registry test :133-153）只测旧 token 的 select 拒绝，不覆盖 controller 回退。
- 影响：同一 operation 的 fallback 可能把未观察到的 G2 revision 应用到新 Agent；CH-3.4 的“不跨代”合同失效。
- 修复要求：把首个 attempt 的冻结 generation/token 带进 composition（或提供 `token.reacquire()` / `acquire({id, generation})`）；回退只能重取**同一 generation**，若其 closed/retired → `agent-preset/closed`，不得回退到 G2；补一个 G1→G2 同 id + StartedSinceObserved 的用例，断言 fallback 以 closed 失败或精确复用 G1。

### P2

**R2-P2-1 — `closedIds.delete` 在 owner 校验之前执行，失败的重注册把 closed 变成 not-found**

- `beginRegistration` :643 在 owner 存在/uid/root 校验（:644-652）和 effect/分配之前清除墓碑；任何后续校验失败（`OWNER_INACTIVE`/`OWNER_ROOT_MISMATCH`/effect 失败）都会丢失 closed 分类。
- Reviewer 探针（`.codex-sandbox/FEAT-103/review-code-r2/probe-closedids.mjs`）实测：
  - close 后 `acquire` → `agent-preset/closed`，`closedIds.has("g1")=true`；
  - 以 `{owner:{}}` 失败重注册 → `agent-preset/OWNER_INACTIVE`，`closedIds.has("g1")=false`；
  - 再 `acquire` → **`agent-preset/not-found`**（应为 closed）。
- 影响：consumer 对 closed/not-found 的区分不稳定；墓碑生命周期合同被失败路径破坏。修复：把 `closedIds.delete` 移到**成功插入/启动之后**，或失败时恢复原值；补“closed→失败 begin→仍 closed”用例。
- 与 R4：这是 closedIds 合同面的直接证据（§6）。

**R2-P2-2 — C12 的“suite-wide P=0”是空壳断言**

- controller test :325-344：`const finalInvariants=[]; addCase("C12", ...)` 只 push `true`；`let leaked=0;` 之后 `results.push({C12, passed: leaked===0})`，**没有任何按 token 状态聚合/mutation**；C12 永远 PASS。
- 影响：测试没有验证“每个 fixture 出口 HELD=0”，M2 报告 §3 的 C12 观测不成立；各单测自身有 held 计数，但 suite 级 invariant 是虚假的。修复：在每个 case 的 fixture 上收集 `presets.state.acquired`，对非终态（HELD）计数并在 C12 断言 0；或删除 C12 声明并改为逐 case 断言。
- 附：C11 fork 未在 controller 套件中注册（审计 §1 亦写 C1-C10,C12）；M2 报告 §5.3 已把 fork 运行标 NOT_RUN，故不是“伪通过”，但测试文件头部列 C11 与实际不符（P3）。

**R2-P2-3 — real `attach` 在 ATTACHED 之后抛错时，operation hold 可泄漏**

- registry `attach` :907-933：先执行 `token.state = "ATTACHED"`（:911），再 `existing.parent.rebind`/`join`/`this.collect(old)`（:912-921）；若 `join`/`rebind` 抛错（scope/rebind 失败是正常防御面），token 已是 ATTACHED，`release()`（:936-940）对非 HELD 直接 no-op，controller `attemptWithAdmission` 的 `finally` 也无从释放；`generation.users` 的 operation hold 保留。
- 影响：违反 CH-3.2“每出口 P=0”；异常路径泄漏 holder，且没有测试。C5/C6 使用 spy token，不覆盖真实 registry 的 attach 抛错。
- 修复：把 ATTACHED 状态变更移到 bind/join 成功之后；或在 catch 中回滚 state/`generation.users--` 并重新抛出；补真实 attach 抛错测试。

**R2-P2-4 — `closedIds` 是可观察合同面，R3 未定义，需设计 R4 增量**

- 机制本身（Set 墓碑）可以作为实现细节保留；但 `agent-preset/closed` 与 `not-found` 是 consumer 可见错误分类，R3 §5.3/§5.4 只写 REGISTRATION_CLOSED 的局部语义，**没有**定义墓碑生命周期、重注册清除时机、失败重注册（P2-1）、legacy `register`/unregister 是否入库、以及 old token 换代隔离的消费者含义。
- 结论：**需要设计 R4 增量**（至少合同补丁），而不是仅靠实现注释；M2 报告 §6 也已建议“下一设计增量 + R4 复审”。R4 应明确：
  1. closed 只适用于 owned terminal（legacy unregister/unknown 仍 not-found？）；
  2. 墓碑保持到**成功的**同 id 重注册；失败 begin 不得清除；
  3. 重注册后旧 token/旧 generation 的 select/attach/publication 均 closed；
  4. legacy `register` 与 `list`/`retain` 的交互；
  5. 墓碑集合的清理/生命周期（registry 卸载/GC）。

### P3

**R2-P3-1 — `attach` 不检查 generation 已 retired/record closed，D1 fence 是唯一拦截**

- `attach` :907-923 只检查 token HELD 与 scope；若 acquire 后、attach 前 record close，attach 仍会 join/rebind 一个 retired generation 并返回 commit；真正拒绝发生在 `publicationCommit`（:929-932）或后续 publish。A3 只测“attach 后 close”；“close 后 attach”未测。
- 影响有限（D1 fence 最终拒绝发布；Agent scope rollback 释放 binding），但会让已 closed 的 revision 短暂绑定到 unpublished Agent；建议 attach 前检查 `record.generation === generation && !generation.retired && record.state !== "closed"`，或在 R4 明确只能靠 publication fence。

**R2-P3-2 — `selectWithAdmission` 成功后的 `collect(previous)` 失败会使“已提交”与“调用方错误”不一致；attach 旧 revision 的 `collect` 未 await**

- :988-991 在 token COMMITTED、binding 提升后 `await this.collect(previous)`；若 collect/dispose 抛错，switch 已提交但方法 reject，调用方可能误判；应在成功后把 collect 失败隔离为诊断/日志。
- `attach` :920 `this.collect(old)` 未 await，async collect 的 rejection 可形成 unhandled；建议 await 或 catch。

**R2-P3-3 — M1 残余 P3 的剩余项**

- 信号 attach-after-close 与 public close 词表已修（T01 9/9；types :21-28；D1 CH3-5）；但 `OwnedPresetRegistration.generation: object` 仍非可选（types :49），begin 返回时可能 undefined；T01-i 仍只覆盖 close 路径，failure/drain 的 detach 未计数；`OWNED_INTERNAL_TERMINAL_REASONS` 仅声明、未被引用（d1 CH3-5 只查存在）。均为 P3。

**R2-P3-4 — 报告/测试面精度**

- M2 报告 :27 写 1171 行，实测 1181（SHA 正确）；`closedIds` 新增已写入实现但 M2 报告 §6 才建议 R4；controller test 头部列 C11 但实际无 C11 case；M2 audit §1 已如实写 C1-C10,C12，故 C11 属“未运行”而非伪通过。
- d1-wiring 的 D1-5 先以 async `check` 记录一次（同步 check 未 await），随后 `results.pop()` 重跑；最终结果正确，但测试写法脆弱；建议改成显式 async await。
- D1-2/3 为源码字符串断言，真实 publish 链 NOT_RUN；M2 报告 §5.1 已披露，属诚实缺口，不计为伪通过。

**R2-P3-5 — closedIds 的 legacy/unbounded 边缘**

- `closedIds` 只由 owned close/failure 写入；legacy `register` 的 unregister 不入墓碑，consumer 对 legacy closed 与 unknown 的区分与 owned 不一致；Set 只增不减（除成功重注册），长期大量 close/重注册 id 会保留字符串；应在 R4 明确 legacy 语义与清理策略。

## 5. 测试质量 / 覆盖

- **正向**：9/9、6/6、11/11、10/10；**对照** 2/11 且控制源精确为安装态字节；变异/对照非空转。
- **缺口**：C7/C8/C9 无 generation 身份；C12 空壳；C11 未运行；attach 抛错/close-before-attach 未测；真实 mount 失败、真实 host publish、legacy roster、storage gap、fork 运行均 NOT_RUN（M2 报告 §5 诚实列出）。
- **测试写法**：A1-A6 用真实 Cordis + 可控 activate（payload 替身）；C 套件用 spy registry/fake agents，分支选择覆盖但不等价真实 registry/host；D1 是源码级断言。无删断言/加 skip；但 C12 的“invariant”名不副实（P2-2）。

## 6. 设计 R4 判定（closedIds）

- **结论：需要设计 R4 增量（合同面）**，不是纯实现细节。理由：`agent-preset/closed` vs `not-found` 是 consumer 可见分类；墓碑生命周期/重注册/legacy/old-token 语义均未在 R3 定义；当前 P2-1 的失败重注册清除墓碑已证明该合同未稳定；M2 报告 §6 亦主动建议 R4。
- 机制（Set + close/failure 写入 + acquire 查询）可保留；R4 只需补齐合同，并修正 P2-1 的清除时机。

## 7. 边界合规

- **安装态 SDK**：五文件 SHA 前后与 R0/R1 记录逐位一致（§1.1），只读；无写入。
- **仓库**：`git status --porcelain -uno` 仅既有暂停 WIP 两行；`git diff --cached` 空；HEAD `2ed8bb4`；设计 R3 SHA `A1F676…` 未变；无产品代码/设计/治理记录改动。
- **宿主 / 真实 `~/.dsh`**：全部为 `node` 进程内 Cordis；未启动 dsh；未读写真实 home；`DSH_HOME` 仅设到 `.governance/sandboxes/feat103-code-r2-20261022T055409Z`（测试不消费）。
- **Cordis 核心 / loader / scope / Session 核心**：未改；变更面仅 §1.2 五个文件。
- **写面**：只写本报告 + scratch；测试 runner 在 `.governance/sandboxes/feat103-impl/tests/session-controller-testable.mjs` 生成测试专用追加导出文件（固定源/安装态源 + export），不是产品/副本实现改动。

## 8. 命令审计（本轮 Reviewer）

| # | label | UTC 2026-10-22（起→止） | exit | 要点 |
| --- | --- | --- | ---: | --- |
| R1 | M1 原套件 | 05:54:39.270Z→05:54:39.848Z | 0 | 9/9；进程内 cordis |
| R2 | registry-admission | 05:54:39.848Z→05:54:40.326Z | 0 | 6/6 |
| R3 | controller-branches fixed | 05:54:40.326Z→05:54:40.617Z | 0 | 11/11 |
| R4 | d1-wiring fixed | 05:54:40.617Z→05:54:40.816Z | 0 | 10/10 |
| R5 | controller 对照（安装态原文件） | 05:54:40.816Z→05:54:41.117Z | 1 | 2/11；控制源 SHA 实测 `398edc…`，无 `attemptWithAdmission` |
| R6 | closedIds 探针（首次） | 06:02:37.216Z→06:02:37.478Z | 1 | 以“正确行为”断言失败：tombstone=false/not-found；保留 |
| R7 | closedIds 探针（bug 复现） | 06:03:01.768Z→06:03:02.031Z | 0 | bugReproduced=true；见 §4-P2-1 |
| R8 | 安装 SDK 五文件 SHA / 副本/测试 SHA / git status | 测试前后（只读） | 0 | 均一致；staged 0 |

- 生产者的 M2 命令（`M2-TEST-AUDIT` 记录）未重跑；其 05:52 自报实数与我的独立复跑一致。
- 对照控制源：`FEAT103_CONTROLLER=<installed>/.../dsh-api-session-controller/lib/index.js`；`session-controller-testable.mjs` 期望哈希 `398edc1b…bae6b9` 与实际一致，证明没有用另一副本冒充安装态。

### Reviewer 证据（`.codex-sandbox/FEAT-103/review-code-r2/`）

| 文件 | SHA-256 |
| --- | --- |
| `r1-m1.log` | `1FC63DBD968B6F4E96ACAE7B6A87CFAD5736B9CE13D073133119C61BA613570F` |
| `r2-registry-admission.log` | `CA3934E6BF286C09817564711D95E94B9AAFDCFED09193E007C690BE18DB3ED2` |
| `r3-controller-fixed.log` | `973E19EF8F225991B6BF3C3A089E29548172235FED933D3C02657EACB38FC4C1` |
| `r4-d1-wiring.log` | `159D2F72B946988F6E6A7E1AE859D837895B3F80E009F07D2C87B52D07CEA4D3` |
| `r5-controller-control.log` | `66A2F8C0368DFE5E7024AE686AE32AABE2B97EAA786B8BDF64ACD26C4DD01D2A` |
| `probe-closedids.log` | `547A97652B2F704FB8607218897753BBB4DE64EA32628772E54124AE7D5B331C` |

## 9. NOT_RUN / 诚实缺口

- 真实 host boot / AgentLoop publish 链（D1 只有源码/加载断言与 A3 fence）——M2 报告 §5.1 已披露。
- T03/T05 storage gap 注入、真实 fork seed/workspace、legacy `register`/`list`/`retain`/`disposer` 回归——M2 报告 §5.2-5.4 披露。
- CH-2/subagent/T06+、T10 性能、webhook、多 Cordis 拷贝、0.1.x——M2 报告 §5.5-5.6 披露。
- controller C11 fork 运行、C12 真实聚合、attach 抛错/close-before-attach、C7/C8/C9 跨代——**本报告新增缺口**，不冒充通过。
- D1-2/3 为源码字符串断言；D1-5 的第一次 async `check` 被 pop 后重跑（最终结果正确，写法 P3）。

## 10. 硬门槛自检

1. 未修改产品代码/设计/副本/测试；仅写本报告 + scratch。未 stage/commit/push。✓
2. 每条结论有运行/读取证据（行号、日志、SHA、控制源哈希）；失败/预期失败与 NOT_RUN 如实保留。✓
3. 所有进程命令先设并断言 `DSH_HOME` 在 `.governance/sandboxes/` 内；无宿主；未读写真实 `~/.dsh`；安装态 SHA 前后一致。✓
4. 设计按 R3 `A1F676…` 核对；对象 SHA 与任务一致；M2 报告/审计 SHA 与任务一致。✓

**结论：NEEDS_CHANGE，unresolved_blockers=1**（R2-P1-1 跨代回退）。P2 的 closedIds 失败清除、C12 空壳、attach 异常泄漏需在 M3/合入前修正；closedIds 合同需设计 R4 增量。
