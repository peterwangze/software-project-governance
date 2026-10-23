# REVIEW-FEAT-103-CODE-R5 — M4 合入前批（纯测试面）独立复审

- 日期：2026-10-22（Asia/Shanghai；命令时刻均 UTC）
- **结论：APPROVED_WITH_NOTES**
- **unresolved_blockers=0**
- P0=0，P1=0，P2=0，P3=2
- 审查对象：M4 新测试套件 `t-m4-contract-closure.mjs`（实际路径 `.governance/sandboxes/feat103-impl/tests/`，SHA-256 `308E7EAFC49C96683B2EAB158829FFEC506D657F4AB8645C2C57B15B6DD9B271`，490 行）+ `M4-REPORT.md`（`98A54305…D3F135C7`，121 行）+ `M4-TEST-AUDIT.md`（`05FF60E3…A658059A`，34 行）+ 审计目录 `m4-audit/`
- 基准：R10 `docs/reviews/review-FEAT-103-CODE-R4.md`（delta base，NOT_RUN 清单与 R4-P3-1/2）；设计 **R6 版** `D8DE745C…B0092`（566 行——R10 审查后 Architect 又执行了 R11 预授权的 R6 文本批，合同面经本轮逐节核对无语义变化：§4.2 :232-238 / §5.6 :314-316 / §7 :362 原样或仅措辞增强）
- Reviewer：同一 CODE 链新实例（R9→R10→本轮）；只写本报告 + scratch `review-code-r5/`；未改产品/副本/测试/设计/治理记录，未 stage/commit，未启动宿主
- **注记**：派单给出的测试文件路径（`.codex-sandbox/FEAT-103/tests/`）不存在——实际位置以 M4-REPORT §0 声明为准（`feat103-impl/tests/`），SHA 亲算逐位一致

## 1. 对象绑定（亲算 SHA）

| 对象 | SHA-256 | 判定 |
| --- | --- | --- |
| M4 测试 `t-m4-contract-closure.mjs` | `308E7EAF…DD9B271`（490 行） | 与派单声明一致 |
| M4-REPORT / M4-TEST-AUDIT | `98A54305…` / `05FF60E3…` | 一致 |
| 副本七文件（registry index/types、controller、agent types、agent-loop、subagent index、child-agent.d.ts） | `5ABBA552…`/`1B2E6C26…`/`B9999EE6…`/`0855B0E5…`/`0C0C589F…`/`16E9F593…`/`2C4B6731…` | **与 M3 后基线逐位一致——纯测试批（副本零改动）成立** |
| 安装态七文件（junction 亲算） | `95EDCC66…`/`52251982…`/`A9801ACB…`/`35318991…`/`CF57E3EC…`/`9A9572E7…`/`F885F282…` | **与 R10 基线逐位一致——零写入** |
| M3-REPORT | `AEA24919…` 未动 | R10 绑定 SHA 保持有效（勘误未改原文，符合"不改被机录绑定报告"原则） |
| 设计 | `D8DE745C…`（R6） | 审查前后未再动 |

## 2. 逐项判定（亲读代码/测试锚点 + 设计合同出处）

| 项 | 判定 | 证据/说明 |
| --- | --- | --- |
| M4-1 legacy 关闭分类 | **PASS** | 实现亲读：legacy `register` :731-755 的 `unregister`（:742-751）无 `closedIds.add`（仅 definitions.delete+retired+collect）；测试三段断言完整（legacy 关闭=not-found 且墓碑无 / 存活期 duplicate 拒绝 / 同 id 后续 owned 关闭=closed 分类对照）；设计 §5.6 #3（:316）逐句对应 |
| M4-2 attach rebind 抛错分支 | **PASS** | 实现亲读：attach rebind 分支 :1002-1009——`existing.parent.rebind` 为首语句（:1003）先于 `generation.users++`（:1005），rebind 抛错时旧 binding/双代 users/HELD 态全部不变；测试 stub 精确（rebindCalls===1+六断言）；补齐 A8（仅 join）的另一半，§5.4 事务性最后 NOT_RUN 面闭合 |
| M4-3 监听者有界开销 | **PASS** | 实现亲读：listener :632-637（`fiber.uid!==null` O(1) 早退 :633 + teardown 查 `ownedByFiber` :634-635）；测试 1000 次真实 Cordis fiber 循环断言零 owned 副作用；census 冒烟数如实标注"记录值非断言门"（§9 性能行口径正确） |
| M4-4 能力拒绝路径（R4-P3-2） | **PASS** | 实现亲读 :3364-3382（:3366 显式 agentPreset 门 + :3367-3381 needs 循环）；`SubagentRuntime` 从原始模块直接 import（M4-TEST-AUDIT r4 duplicate-export 教训闭环）；5 断言覆盖四拒绝一通过；`startActivation` 全链 NOT_RUN 如实披露（§5 #3） |
| M4-5 selected append gap | **PASS** | 实现亲读 :1841-1843（attach 先于 selected append——失败落在 attach 后）；测试七断言（原错误透传/acquire 1 次/token ATTACHED/零事件/无 retry/子 binding/双 holder）；**§5.3 #4 口径正确**（attach 后失败 token 随 Agent scope）；fixture 不模拟 AgentLoop scope 回滚的 NOT_RUN 披露与设计一致 |
| M4-6 coldResume 错误面双分支 | **PASS** | 实现亲读 :2220（projection 前置先于 materialize）+ :2238-2241（SubagentError 直抛/非 Subagent 包 NOT_RESUMABLE+cause）；registry closed 错误非 SubagentError → 走 :2241 包装，`cause.code=agent-preset/closed` 可溯源——与设计 §4.2 :238（R5 F-M3-3）逐句对应；②分支 acquire 0 次证明前置检查先于任何 admission；与 B8（spawn 透传面）互补成对 |
| M4-7 webhook/多 Cordis | **NOT_APPLICABLE 成立** | 设计 §7 :362（webhook 未安装不声称覆盖）+ §6.1 :338 同口径；多 Cordis grep 零合同条目（M1 P3 风险注记非可测合同）——独立复核确认，不造用例正确 |

## 3. 独立复跑（UTC 2026-10-22，全部 node 进程内 Cordis，DSH_HOME 隔离至 `.governance/sandboxes/feat103-code-r5-isolation`）

| # | 命令 | UTC（起→止） | exit | 实数 |
| --- | --- | --- | ---: | --- |
| F1 | M4 权威轮 | 11:01:54.687Z→11:01:55.141Z | 0 | **6/6** |
| F1b | M4（audit-json 落盘轮） | 11:01:55.160Z→11:01:55.572Z | 0 | 6/6 |
| F2 | B 套件 | 11:01:55.577Z→11:01:55.979Z | 0 | **12/12** |
| F3 | A 套件 | 11:01:55.980Z→11:01:56.560Z | 0 | **12/12** |
| F4 | C 套件 | 11:01:56.563Z→11:01:56.880Z | 0 | **14/14** |
| F5 | d1-wiring | 11:01:56.881Z→11:01:57.050Z | 0 | **10/10** |
| F6 | T01（仓库根口径） | 11:02:08.887Z→11:02:09.505Z | 0 | **9/9**（runner exit 非零⟺有失败；exit 0=零失败） |
| C1 | M4 @prefix-subagent 对照 | 11:02:09.548Z→11:02:09.970Z | **1** | **4/2**——M4-5（无 admission 面 acquire 未发生）/M4-6（无墓碑语义 cause=not-found）精确失败；M4-1/2/3 PASS=registry/runtime 面未被对照替换（Developer §3.2 已披露观测等价）；M4-4 PASS=assertCapabilities 在安装态原码与副本一致 |

- **九条全部与 Developer 审计（M4-TEST-AUDIT #9/#10/#11/#14）逐字一致**；双源 audit JSON 比对：Developer `m4-main.json` 6/0 与我的复跑 6/0 一致、对照失败 ID 集合一致（M4-5/M4-6）。
- **勘误段（R4-P3-1）亲核**：副本 :1086-1090 实测=try/catch collect 隔离段（"CODE R3 P2-1 (M3)" 注释锚）——M3-REPORT §2.2 写 :1072 起点确偏后 8 行；勘误记录于 M4-REPORT §4 且未改 M3-REPORT（SHA 保持 `AEA24919…`），处置正确。
- **中间轮 7 次失败**：M4-TEST-AUDIT #1-#9 全表在案（装置/schema/断言口径修正；probe 归档于 m4-audit/）；副本 SHA 逐位一致证明实现零改动——"实现未因测试回改"成立。

## 4. Findings

### P3

**R5-P3-1 — T11+ 覆盖表口径过宽（default/list 无对应用例）**
- 设计 §8 T11+（:376）明列 "legacy register/disposer/**default/list** 回归不降"；M4-REPORT §2.1 T11+ 行判"已覆盖"，实际 M4-1 覆盖 register/disposer（unregister），**default（defaultId 解析）与 list 无行为用例**。
- 缓解：纯测试批 + 副本 legacy 函数体零触碰（M1-M4 全部 SHA 链证明）——结构性保证 default/list 行为不变，风险极低；属覆盖声明与合同文本的口径差，非行为缺陷。
- 建议：合入前小批补 default/list 形状用例，或把 §2.1 措辞收窄为"register/disposer 已测；default/list 由零触碰结构保证"。

**R5-P3-2 — M4-REPORT §1.2 安装态路径表述混入副本目录树段**
- 写作 "dsh-subagent/subagent/lib/index.js"——安装态实际为扁平 `@deepseek-ai/dsh-subagent/lib/index.js`（"subagent/" 段是副本 monorepo packages 树口径）。**SHA 值本身正确且亲算逐位一致**（`9A9572E7…95B44168` / `F885F282…4D71AC7F`），实质无影响；路径表述勘误记入本报告。

**治理面注记（非本审查对象缺陷，交 Coordinator）**：M4 测试文件实际落位 `feat103-impl/tests/`（报告 §0 已如实声明）而非前序套件惯例位置 `.codex-sandbox/FEAT-103/tests/`；M4 锁清单的 expected_new 未逐文件列入该新测试文件（落在任务沙箱子树内）。后续批次建议将新测试文件显式入锁。

## 5. NOT_RUN / 诚实缺口确认（与 M4-REPORT §5 一致，无冒充）

真实 host publish 链与 AgentLoop scope 回滚面（M4-5 fixture 不模拟）；物理 storage 写失败注入（进程内 append 面已覆盖）；startActivation 全链（M4-4 为方法级最小闭环）；T09+ closed 变体（C-1 小缺口，Developer 主动披露）；T10 census 全量基准（冒烟非断言门）；多 Cordis/webhook/0.1.x（NOT_APPLICABLE 或维持披露）；A12 等价性/T01-i 时序（M3 §4 原披露沿用）。

## 6. 边界合规

- 安装态 SDK：七文件 SHA（junction 亲算）与 R10 基线逐位一致，零写入。
- 仓库：`git status --porcelain -uno` 仅既有暂停 WIP 两行；`git diff --cached` 空；HEAD `2ed8bb4499c0…`；无 stage/commit/push。
- 设计：审查期间未再动（`D8DE745C…` 收工复算一致）。
- 宿主/真实 `~/.dsh`：无 dsh 进程；DSH_HOME 仅设自建隔离目录并清除。
- Reviewer 写面：本报告 + scratch `review-code-r5/`（含我的复跑 audit JSON）。

## 7. 结论

**APPROVED_WITH_NOTES，unresolved_blockers=0。** M4 七项（6 PASS + 1 NOT_APPLICABLE 有设计出处）全部有亲读锚点 + 独立复跑 + 精确失败对照的三重证据；纯测试批声明成立（副本/安装态双端 SHA 逐位一致）；九条复跑与 Developer 审计逐字一致；勘误处置正确；边界红线全部合规。两条 P3（T11+ 覆盖口径 / 安装态路径表述）不阻断，建议随合入决策一并处置；真实 host 链等 NOT_RUN 面如实保留，交合入决策。
