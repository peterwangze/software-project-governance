# REL-094 M-3 RELEASE 半面审查报告（R0）

- **审查对象**：0.91.0 发布候选 = HEAD `98104cb5`（窗口 v0.90.0〔transition 3f87459〕..HEAD，5 commits：8d25101〔0.90 M-8 收尾搭窗〕→ 196894a〔FEAT-072〕→ 9bafdf6〔FIX-399〕→ bc3f0527〔M-1〕→ 98104cb5〔M-1R〕）
- **审查基准**：DEC-267（M-0 冻结 + (3) 披露分层 + (5) 十条停止条件）× DEC-265（发布授权链）× DEC-266（FEAT-072 契约裁决）；0.90.0 RELEASE-M3 先例（review-REL-090-RELEASE-M3）
- **审查人**：Release Reviewer Agent（独立链）· **Round**：R0 · **日期**：2026-09-28（+0800）
- **角色约束履行**：未修改任何产品文件与 `.governance/**`；无用户交互；唯一产出 = 本报告（验证命令全部只读；唯一后台负载 = 全量 pytest 复跑）

---

## 结论速览

| 项 | 结论 |
|---|---|
| **Verdict** | **APPROVED_WITH_NOTES**（建议有条件 GO） |
| **unresolved_blockers** | **0**（无 BLOCKING finding） |
| P0 / P1 | 0 / 0 |
| P2（发布链内必收口，不阻断 M-3） | 2 项（M-2 证据机录缺位；0.92 治理票登记面缺位） |
| P3（非阻塞备注） | 5 项 |
| 停止条件（DEC-267(5) 十条） | **逐条判定零触发**（见项 4） |
| 冻结边界（DEC-267(1)） | 未越界：窗口源码 diff 恰=载荷两票+六锚版本字面量（亲证） |

---

## 项 1 —— 双态边界（准备态 → 发布态收口义务清单）→ **PASS（清单完整）**

**现状核验**：`project/CHANGELOG.md` L5 `## [0.91.0] - 未发布（准备态）` + L37 准备态注记（日期不预填、FIX-349 taggerdate 权威落字口径、终账随 M-2+ 补记）——准备态边界声明正确，无越权预填。root `CHANGELOG.md` 为投影位（canonical=project 面，REL-086-CODE-M3 裁决①），本版段双位同文由 M-1 再生承载。

**发布态收口义务清单（逐项核验——全部已入 M-5~M-8 放行条件，无缺失面）**：

| # | 义务 | 依据 | 去向 |
|---|---|---|---|
| a | 日期落字（FIX-349 taggerdate 权威——M-7 tag 后回填 L5+路线图行） | CHANGELOG L37 自带声明；0.87 先例（FIX-349） | M-5/M-8 |
| b | **行为变更段落段（N-2）**：本版 B-15〔命名词——全库现无 B-15，发布态铸造，承接 B-1~B-14 序列〕推荐呈现形态升级（FEAT-072：正文三要素卡+短选项，agent 行为契约面=M7.4 6b/6c+四注入面）+ **回滚说明 = git revert 单提交、无数据迁移、无 flag 面** + 无依赖变更（stdlib-only）——0.90.0 段 L62 句式（「行为变更：无破坏性变更…回滚：…」）同构 | M-1 审查 N-2；0.90 先例形态 | M-5 |
| c | DEC-267(2) 措辞第二从句「**计量或生成内容变化也可能越界**」逐字补入 strict 披露行（N-1，现为 P3-1 未闭合项） | DEC-267(2) 原文；M-1 审查 N-1 | M-5 |
| d | 已知限制四条发布态重测落字（28s 现值/strict 5991 复测口径/P2-1 候选池/版本面再生纪律） | DEC-267(2)「最终发布态必须重测（当前 5991 不替代）」 | M-5/M-8 |
| e | 终账/Commit 区间/发布验证结论补记 + root 投影位同步 | CHANGELOG L37 声明；canonical=project 裁决 | M-5/M-8 |

**DEC-267(3) 专项义务——「无下游依赖原推荐格式接口」确认（M-3 指定确认项）：确认成立。** 依据：①推荐呈现为行为契约 prose，非结构化数据接口，全仓无解析旧推荐措辞的代码路径；②唯一机器消费面 = `INJECTION_CONTRACT_ANCHORS`（双注入面+canonical `behavior-protocol.md` 三完整标签）——已在载荷 commit `196894a` 同 commit 更新（本审亲证窗口 diff 锚面在场）；③关键词清单 L558、session-snapshot 投影格式、`test_dsh_adapter.py` 锚测试（正向+三路负例，54 OK）均同 commit 同步；④e2e 投影 blob 双面同一（见项 4 亲跑 #10）。**无 breaking，与 DEC-267(3) 预期分类一致。**

## 项 2 —— 四披露交叉一致（DEC / CHANGELOG / EVD / REVIEW 四面）→ **PASS（数字面全一致；两处措辞/登记面缺口列 P2/P3）**

| # | 披露 | DEC | CHANGELOG | EVD | REVIEW | 裁决 |
|---|---|---|---|---|---|---|
| 1 | **strict 9 tok** | DEC-267(2)：5991/6000 余量 9+第二从句+0.92 治理票+发布态必重测 | L18：5991/6000+第一从句+「0.92 治理票已登记」（**第二从句缺=N-1；登记声明超前=P2-2**） | EVD-1204（5719/5991 实测）+EVD-1208（「strict 5991/6000 余量 9 与披露口径一致」） | FEAT-072-R0 §4（5991 亲跑）+M-1-R0 §4（三档亲跑） | **数字四面一致（5991）**；措辞缺口见 P3-1、登记缺口见 P2-2 |
| 2 | **28s** | DEC-264：结构性约束披露发布+0.91 产品票候选（FIX-397⑥ 同族；0.90 时点 1,726,161B） | L19：1,737,424B（M-1 时点标注） | EVD-1209/M-1R 审查实测 1,741,479B | M-1R-R0 §清单 6（唯一 FAIL=28s） | **同事实族、点位随发布链自增**（本审现值 **1,744,908B**）；标注时点、非失实；发布态 MUST 重测落字（P3-3）；DEC-267(5) 末句：获准保留本身不构成停止条件 |
| 3 | **P2-1（28c 跨行加固出槽）** | DEC-267(1)：「无需…纳入 P2-1」（明示出槽） | L20：「REVIEW-FIX-399-R0 P2-1——0.91+ 候选池」 | review-FIX-399-CODE-R0 F-1（P2：`[^*]*`→`[^*\n]*` 建议；V7 实证跨行吞噬形态） | plan-tracker L281 0.91+ 候选池行已登记出槽 | **四面一致 ✓** |
| 4 | **版本面再生（幂等四度）** | DEC-267(4)：M-1 验收=再生二次无新增差异 | L21：written=17→幂等复跑 0（简写形态） | EVD-1208：「幂等四度：17→0→0→审查复跑 0，28 面收敛 28b 消解」 | M-1-R0 亲跑 written=0+28/28；本审亲跑 check-projection-sync **28/28 PASSED@HEAD** | **一致 ✓**（CHANGELOG 为简写、语义同） |

## 项 3 —— 风险窗引用（M-4 前置核对，risk-log 现状读取）→ **PASS（引用面齐备）**

| 风险 | 现状（risk-log 亲读） | 与 0.91.0 的关系 | M-4 引用义务 |
|---|---|---|---|
| RISK-059 | 打开（FEAT-061 切换三前置缺口） | **B-12/B-13 翻转前置——本版不翻转已实锤**：窗口 diff 守卫 token（6000 限额/posture/MD_ACTIVE/activate-block/enforce）grep **零命中**（亲证，见亲跑 #9）；载荷两票均不触 write-guard 面；CHANGELOG 无激活声明 | M-4 引用「维持打开、本版未翻转」现状 |
| RISK-036 | 打开（09-30 窗；DEC-243④→DEC-249②→DEC-263⑥ 复评链） | 0.91 发布日 2026-09-28 在窗内 | **同窗留痕复评**（引用既有留痕+本版增量确认——0.90 DEC-263⑥ 同型） |
| RISK-039 | 打开（收窄维持；09-30 窗） | 归档/结构 WARN 14（451 issues 0 blocking）既有基线 | 同窗留痕复评 |
| RISK-047 | 打开（登记观察；09-30 窗） | 本版窗口 review-record 全部机录零 force 使用（四条 REVIEW 行亲读） | 同窗留痕复评 |
| RISK-048 | 打开（登记观察；09-30 窗） | loop_runtime 计时敏感族——本审全量静默窗口 **0F**（双源，见项 4 #8） | 同窗留痕复评+本版双源 PASS 记录 |
| RISK-050 | 打开（dsh 上游内部面耦合；**截止 2026-10-31**——risk-log L41 日期亲证；0.82 CHANGELOG L537 口径先例） | 本版 dsh 交付面零行为触碰（窗口 diff 无 lib/index.js/cordis.patch 变更） | M-4 引用「维持打开至 10-31」 |

## 项 4 —— 门禁与停止条件（DEC-267(5) 十条逐条）→ **零触发**

**门禁事实基座（本审亲跑）**：全量 **4359 passed / 1 skipped / 0 failed / 527 subtests passed in 1394.55s**（后台 job pwsh-171，静默窗口单任务运行）——与 Coordinator 申报 pwsh-170（4359P/0F）**同值双源**；check-governance --summary-only = **20 issues、唯一 FAIL=28s@1,744,908B、28c 零条目**（WARN 2/14/15/24 全为既有 advisory，24=M-8 收口项预期态）。

| # | 停止条件 | 判定 | 依据 |
|---|---|---|---|
| 1 | 契约失真 | **未触发** | check-injection-contract 4 面/30 锚 PASSED（亲跑）；canonical 三标签锚 presence 生效；负例测试在案（FEAT-072-R0 §2 亲跑） |
| 2 | 预算硬门失败（含改计量或临时抬限掩盖） | **未触发** | 三档 4241/5719/**5991**/6000 全 PASS（亲跑）；窗口 diff 限额/计量器 token 零命中（亲证）；未抬限未改计量 |
| 3 | 分析失败仍执行 | **未观察到触发** | tpa fail-closed 条文（6a）未被载荷触碰（FEAT-072-R0 §1(5)）；窗口无分析失败仍推进的事件记录 |
| 4 | 缺失依据包装确定方案 | **未观察到触发** | CHANGELOG 措辞事实性（M-1-R0 §5 逐项对照 arch 边界）；EVD 降级三态条文在案 |
| 5 | 待消解失败未消解（28b/28c 复现） | **未触发** | 28b：projection 28/28+e2e SKILL.md blob 双面同一 `6c47668`（亲跑 #4/#10）；28c：HEAD 零 28c 条目+FIX-399 V3 同数据 A/B 净效果 −1/0+6 用例绿 |
| 6 | 全量门禁未完成或新增未解释失败 | **未触发** | 4359P/1S/0F 双源一致（本审 pwsh-171+Coordinator pwsh-170）；零未解释失败 |
| 7 | 豁免失效 | **未触发** | archguard regen exemptions=1（既定携带，M-1R REGENERATED 输出亲证）；M0 重钉=授权变更 sanctioned regen（DEC-262②）非豁免；零新增豁免 |
| 8 | 证据产物脱节 | **边缘（登记面滞后，非事实失实）** | M-1/M-1R/载荷四票 EVD+四条 REVIEW 机录行+CHANGELOG 引用链（EVD-1204/1205/1207 实存）核对一致；**缺口两处列 P2-1/P2-2，M-4 前补账** |
| 9 | 严重可靠性安全回归 | **未触发** | 全量 0F+合并态联合回归 54+20 OK（DEC-267(1) 冻结锚）+窗口零守卫/安全面改动 |
| 10 | 发布记录不完整 | **未触发（设计内准备态）** | 准备态按 DEC-267(3)/(4) 分层正确；发布态收口义务清单完整（项 1） |

**loop_runtime 机本地敏感性裁决（M-1R 归因）→ 内部登记，不入 CHANGELOG 已知限制。** 理由：①非用户面——loop-claims 是插件自带治理测试族，不随 plugin update 影响宿主用户；②先例框架已在：RISK-048（环境敏感登记观察）+FIX-240（环境敏感先例）+FIX-346（单机定标口径），重复入 CHANGELOG 属过度披露；③事实面：M-1R 审查独立复现 24 tests OK/131.8s+本审全量静默窗 0F——「机本地热文件敏感、定向必绿」归因与双源独立观测一致，无掩盖迹象（FIX-240 注记在案、claim 语义未改、断言未放宽）；④EVD-1209 已留「结构性脆弱点登记后续事项」。**行动项**：去环境化改造票入 0.92 候选池（与 28s 归档判据扩展票同池）。**红线条件**：若后续 M-2 终版复跑该族再现 FAIL，归因必须重评，禁静默豁免。

## 项 5 —— M-5~M-8 放行条件清单（有条件 GO 的条件本体）

**M-4（放行前置门，先于 M-5）**：
1. **P2-1 补账**：M-2 全量门禁 EVD 机录行（引用 pwsh-170+本审 pwsh-171 双源：4359P/1S/0F/1394.55s）+check-governance 20 issues（唯一 FAIL=28s，落发布时点实测值）+本报告经 review-record 机录；
2. **P2-2 处置**：0.92 治理票结构化登记（plan-tracker 承载行，含 DEC-267(2) 五要素：计量器版本/范围/基线/责任人/验收指标）或 CHANGELOG 登记声明措辞对齐——两者取一，禁止维持「声明超前于登记」态进发布态；
3. **风险窗留痕复评**：RISK-036/039/047/048（09-30 窗内履行，DEC-263⑥ 同型）+RISK-050（维持至 10-31）+RISK-059（不翻转确认）逐条入账；
4. **docs/release 三件套 0.91.0 创建**：release-checklist-0.91.0.md（M-2 回填+已知限制+停止条件对照）+rollback-plan-0.91.0.md（区间锚 `git rev-parse v0.90.0^{}`=3f87459，tip 不预填——M-5 现场取值）+feature-flags-0.91.0.md（「本版无新增 flag——B-15 为契约呈现面非 flag 面」声明或同构）；含 RISK-036 边界 needle（release_docs 门禁要求）。

**M-5（manifest+transition+CHANGELOG 发布态）**：
5. 创建 `core/releases/0.91.0.json`（N-4 义务；NFC/sorted/compact 同 0.90 形态）+manifest lifecycle=candidate→transition（candidate_to_released，单父=候选 commit；tip 以 M-5 现场 `git rev-parse HEAD` 为准）+check-release candidate 态执行（DEC-267(4)「不提前伪造完成态」至此点解除）；
6. **CHANGELOG 发布态改写（双位同步 project+root 投影）**：日期落字按 FIX-349 taggerdate 权威（M-7 后回填）+**行为变更段（B-15 命名+回滚说明 git revert 单提交无数据迁移+无依赖变更 stdlib-only）**+DEC-267(2) 第二从句补入+已知限制四条发布时点重测+终账/Commit 区间/验证结论补记。

**M-6（ledger）**：
7. release-ledger 本地+**remote** 双 PASS（NATIVE_RELEASED；tag_facts local==remote；UNKNOWN/BLOCKED 不得包装 PASS——0.90 条件 3 同型）。

**M-7（tag+push）**：
8. annotated tag `v0.91.0`+push（peel 机制：tag object→commit；ledger tag_facts 双端核对）+master push；taggerdate 权威回填 CHANGELOG/路线图日期。

**M-8（归档+released 验证+版本收口）**：
9. 归档迁移（范围扩展至 v0.90.0）+check-archive-integrity PASS；**版本收口**：plan-tracker 工作流版本 0.90.0→0.91.0（消解 WARN 24）+路线图 0.91.0 行终态回填（已发布日期+tag+integrity 摘要，0.90 行形态）+released 验证（lineage/changelog/archive/docs/fact-source 全 PASS）+session-snapshot 更新（三要素投影行格式首用——FEAT-072 SHOULD 面）；
10. **census/身份集维持至 tag**：零新增未授权阻断项（0.90 条件 4 同型红线）；loop_runtime 裁决执行=内部登记（0.92 候选池去环境化票），不入 CHANGELOG 已知限制。

## 项 6 —— 归档前置预估（M-8 归档面）

- **dry-run 亲跑**（`archive.py migrate --auto --dry-run`）：当前归档范围 v0.1.0~**v0.89.0**，release_forced 触发器满足但**四类 0 可归档**（tasks 19 保留/decisions 68 保留/risks 43 保留/evidence 459 保留；逐类原因=already_archived/out_of_range/retained_active 等）——0.90 M-7（16+16）已清空存量，**发布前无需前置归档动作，M-5 不会被归档完整性阻断**。
- **M-8 增量预估**：范围扩展至 v0.90.0 后纳入 0.90 窗内行——任务行 ~6-9（REL-091/092/093、FEAT-069/070/071、FIX-397/398）、证据行 ~12-18（EVD-1196~1203+审链 REVIEW 行+发布链 EVD）；以 M-8 现场 dry-run 复测为准。**注意**：0.90 窗行须待 0.91.0 released 后方入归档范围（dry-run 无法提前预演 v0.90 段）。
- **28s 走势**：发布链自增后 evidence-log 1,744,908B+，归档增量缓解有限——28s ERROR 维持 DEC-264 披露口径（结构性约束，0.91 池产品票候选=FIX-397⑥ 评估在案），不构成停止条件（DEC-267(5) 末句）。
- 既有 unknown-structure 存量（tasks REL-086/FEAT-047、decisions 78 短行、evidence 10 形态）＝FIX-343 已披露先例，非本版引入，M-8 维持披露口径即可。

---

## Findings（P0-P3）

**P0（BLOCKING）**：无。**P1（BLOCKING）**：无。

**P2（发布链内必收口，不阻断 M-3——放行条件 1/2 本体）**：

- **P2-1（证据面）**：M-2 全量门禁（4359P/0F）在 evidence-log **无机录行**（grep 4359/pwsh-170/EVD-1210+ 零命中）——按「事实依据红线」该事实原不可引用；本审已独立复跑补实事实基座（亲跑 #8 同值双源），但 **M-4 GO 前 Coordinator MUST 补 EVD 机录**（DEC-267(5) 条件 8「证据产物脱节」的闭合动作），否则发布记录链在 M-2 席位断链。
- **P2-2（登记面）**：DEC-267(2) 要求的 **0.92 治理票未结构化登记**（plan-tracker 零承载行；现状仅 DEC-267(2) 指令自身+execution-packets 排除注记+session-snapshot 候选池叙述）——CHANGELOG L18「0.92 治理票已登记（含计量器版本/范围/基线）」为**提前声明**。M-5 发布态改写前 MUST 补登记（五要素齐）或对齐措辞；DEC-267(2)「对外称已登记不称必定解决」的前提是登记真实存在。

**P3（非阻塞备注）**：

- **P3-1**：DEC-267(2) 第二从句「计量或生成内容变化也可能越界」未逐字入 CHANGELOG L18（=M-1 审查 N-1 未闭合）——M-5 发布态补入（已在放行条件 6）。
- **P3-2**：行为变更段未落（=M-1 审查 N-2 未闭合，准备态正确姿态）——M-5 落 B-15 段+回滚说明（已在放行条件 6；B-15 为本审命名词，全库现无该 ID）。
- **P3-3**：28s 披露数字点位漂移（1,737,424@M-1 → 1,741,479@M-1R → **1,744,908 本审现值**）——发布链自增所致，非失实（段内已标 M-1 时点）；发布态 MUST 重测落字（已在放行条件 6）。
- **P3-4**：docs/release 三件套 0.91.0 未创建（0.90 有同构三件套先例）——M-4/M-5 创建（已在放行条件 4）。
- **P3-5**：plan-tracker 版本行表序 0.91.0 行（L281）位于 0.90.0 行（L282）之前（非时序倒序，装饰性）——M-8 收口时顺手归位，不单独开票。

（FEAT-072-R0 P2-1 批序问题已核实**闭环**：plan-tracker L281 现载「批序 FEAT-072→FIX-399，DEC-266(5) 裁决——2026-09-27 勘正原立项快照反序」；P3-1 任务行状态亦已勘正。FIX-399-R0 P2-1 出槽登记在 plan-tracker L281 候选池行 ✓。）

---

## 亲跑摘要（本审全部验证命令，2026-09-28 @HEAD 98104cb5）

| # | 命令/操作 | 结果 |
|---|---|---|
| 1 | `resolve_entry.py --json` | resolved_root_ok=true；active_version 0.91.0 |
| 2 | `git rev-parse HEAD`+`status --porcelain`+`tag --list` | 98104cb5…；工作树 0 修改；tag 仅 v0.9.0/v0.90.0（v0.91.0 未打，M-3 前置正确） |
| 3 | `check-version-consistency` | PASSED；唯一 WARN 24（plan-tracker 0.90.0 expected 0.91.0=M-8 项） |
| 4 | `check-projection-sync` | PASSED，28/28 收敛（28b 维持绿） |
| 5 | `check-injection-contract` | PASSED，4 面/30 锚 |
| 6 | `check-injection-budget` 三档 | lightweight 4241 / standard 5719 / **strict 5991**/6000 全 PASS（余量 9 四方复证） |
| 7 | `check-governance --summary-only` | **20 issues；唯一 FAIL=28s@1,744,908B；28c 零条目**；WARN 2/14/15/24 既有 |
| 8 | **全量 `python -m pytest …/infra/tests -q`（pwsh-171）** | **4359 passed / 1 skipped / 0 failed / 527 subtests passed in 1394.55s**——与 Coordinator pwsh-170（4359P/0F）同值双源 |
| 9 | 窗口 diff 面审计（`git diff v0.90.0..HEAD`） | 37 文件；verify_workflow.py 恰=六锚字面量+FIX-399 两 hunk+FEAT-072 锚面；6000/posture/MD_ACTIVE/activate-block/enforce token **零命中**（冻结边界未越界+B-12/B-13 未翻转实锤） |
| 10 | `git ls-tree HEAD` e2e 双面 SKILL.md | blob 双面同一 `6c47668`（投影收敛保持） |
| 11 | `core/releases/` 清单 | 0.62.0~0.90.0 共 41 份；0.91.0 缺席=M-5 义务（DEC-267(4) 不提前伪造） |
| 12 | `archive.py migrate --auto --dry-run` | 范围 ≤v0.89.0 四类 0 可归档（发布前无归档阻断） |
| 13 | `check-cross-references`+`check-manifest-consistency` | 77 文件/728 引用全 PASS；947/1097 PASS |
| 14 | 治理记录读取 | DEC-263~267、EVD-1204~1209、REVIEW×4 机录行（FEAT-072-R0/FIX-399-R0/REL-094-R0/R1 全 AWN/0）、risk-log 六行、plan-tracker L80~82/L281——引用链逐一实存 |

**未复跑项（归属声明）**：合并态联合回归 54+20 OK（DEC-267(1) M-0 冻结锚，未重跑）；pwsh-170 原始输出（Coordinator 会话内事实，本审以 pwsh-171 独立同值复跑替代采信）；release-projection --write 幂等（M-1/M-1R 两审亲跑 written=0 在案，本审未再写——以 28/28 收敛+blob 同一间接承载）。

---

## 结论

**APPROVED_WITH_NOTES（unresolved_blockers=0）——建议有条件 GO。**

六项审查清单全部完成：①双态边界收口义务清单完整（PASS）②四披露交叉一致（数字面全一致；措辞/登记两缺口列 P2-2/P3-1）③风险窗引用面齐备（M-4 六风险逐条义务明确）④停止条件十条零触发（全量 4359P/0F 双源亲证+28s 获准保留）⑤M-5~M-8 放行条件十项产出（上文项 5）⑥归档前置无阻断（dry-run 0 可归档）。无 BLOCKING finding；P2×2 为 M-4 前必补的登记面动作（放行条件 1/2），P3×5 随发布链承载。终局 go/no-go 决策权在 Coordinator+arch（M-4，消费风险窗复评结论）。本审查未修改产品文件与 `.governance/**`；review-record 机录由 Coordinator 执行。
