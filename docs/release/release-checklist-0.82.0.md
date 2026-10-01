# Release Checklist — 0.82.0 (REL-078)

> **M-0 草案（REL-078 prep，2026-09-18）**——Coordinator 审后随 M-1 候选提交；结构与措辞对齐 `docs/release/release-checklist-0.81.0.md` 先例。M-1 冻结前 ⟦待回填⟧ 占位 MUST 全部消除——**唯一例外 = M-2 派生回填类**（候选 commit hash 与 M-0/M-1 批 hash：manifest 须先随候选提交入库、`release-ledger` 才能派生——EVD-1034 / REVIEW-REL-077-RELEASE-R1 F-R1-02 先例，M-2 期回填）；「Candidate Gate Results」的实测值由 M-2 门禁实测逐项回填，未回填项不得视为通过。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.82.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.82.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版引擎/守卫改动全部在隔离 `DSH_HOME`（环境变量重定向至临时目录）下验收——隔离验收不等于真实外部首会话验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开，未关闭；do not claim 1.0.0 production-ready。
- **RISK-050 remains open**：dsh 上游内部面耦合维持打开（截止 2026-10-31）；本版窗口对 dsh 交付面为**注释级零行为变更**（`lib/index.js` 仅注释，渲染产物字节不变），不据此声明任何风险关闭。
- **B-8 守卫覆盖限定**：FIX-325 的 CWD 退化反相守卫以 **Node ≥22.15** 的 ESM `registerHooks` 故障注入交付（仓声明 engines≥20）；本清单与任何发布注记 **MUST NOT 声称该守卫全引擎覆盖**。

## Release Scope

| 分组 | 任务 | 版本归属 |
|---|---|---|
| **引擎事实源** | **FIX-339**（`check_hot_fact_source_consistency` 版本锚参数化——DEC-195 (a) 真修；hot fact source 9 条 0.38.x 假阳清零；行为变更 B-1/B-2/B-3；R0→R1→R2 三轮收敛） | 0.82.0 |
| **归档/审查引擎完整性** | **FIX-341**（tpa 归档索引解析）+ **FIX-343**（数据回填 10 行 + DEC-187 更正 + tpa 假阻塞清零）；**FIX-312**（决策归版判据）+ **FIX-342**（防御面四子项）；**FIX-345**（authority 双锚归档感知重锚——B-6）；**FIX-314**（review_record 三键——B-5）+ **FIX-344**（Check 30c 后缀感知） | 0.82.0 |
| **扫描器/身份门禁** | **FIX-320**（loop-claims 豁免账本——B-4）+ **FIX-322**（K-2 包名整串判定） | 0.82.0 |
| **渲染面/守卫/收集面** | **FIX-323**（渲染面收口）+ **FIX-325**（3 条真守卫——B-8 限定语）+ **FIX-336**（discover 收集面——B-7 计数口径；连带 FIX-326②）；**FIX-313**（DEC-196 方向更正，产品零变更）+ **FIX-346**（性能预算重定标，红基线清零） | 0.82.0 |
| **数据资产/派发纪律** | **FIX-332**（过期数据资产收口 + DEC-194 补记）+ **FIX-333**（write-guard 非 UTF-8 七面收口）+ **FIX-337**（派发隔离变量名纪律） | 0.82.0 |
| **发布治理面** | 本 checklist + `feature-flags-0.82.0.md` + `rollback-plan-0.82.0.md` + `project/CHANGELOG.md` [0.82.0] 段 + **FIX-324/326 并入批**（adapter-manifest 登记 + 契约 evidence.* note 更正 + 逐项处置见 `docs/reviews/review-FIX-324-326-CODE-R0.md` 与 Release Agent M-0 结构化返回）+ **日期炸弹测试修复**（test_change_triage CLI 用例）+ `core/releases/0.82.0.json` candidate（M-1 已交付） | 0.82.0 |
| **不发布什么（显式排除）** | R3 遗留 N-4/N-5/N-6 与 EVD-1036/1037 字段口径修复、REL-078 packet 入账、Check 30 merge 口径 DEC、commit-msg OR 粒度 DEC、archive.py 锚提醒、M7.7 指针行（MAY）、preset.yml 镜像 D-66（latent）、设计 L347 勘误——均为 DEC 候选池/数据面项，**不随本版承载**（session-snapshot 2026-09-18 §DEC 候选池）；FIX-324④ 的 F-11/F-12 残余与 dsh_contract.py L10 docstring 残余（见 FIX-324 处置专节）——超出本批写入面，维持 FIX-324 批持有 | 排除 |

## Change Inventory（**14 commits** — `git log --oneline e376ddf..845c050`，2026-09-18 M-0 期实测；**M-1 冻结时窗口扩展至候选打包提交**，M-0/M-1 批行 ⟦待回填⟧；`e376ddf` = 0.81.0 发布 tip（transition 提交），`845c050` = 0.81.0 线 tip = 本版窗口起点基线）

| # | 任务 | commit | 终态要点（审查终态 + EVD） |
|---|---|---|---|
| 1 | FIX-338（① 退回修复） | `1db58f5` | R2 退回修复（发布闭环层）——恢复 plan-tracker 结构性热节 + 回填发布 tip `e376ddf` + README 推送陈述更正；EVD-1038 |
| 2 | FIX-338（② 机录） | `02ad554` | 真机验收机录（5/5 判定点通过，EVD-1040）+ RISK-050 收口条件履历 + 治理记录结构修复 |
| 3 | FIX-338（③ 收口） | `dfafa95` | released 态门禁当场复跑刷新（17 PASS/3 FAIL/1 SKIP/18 issues 逐条归因）+ **REVIEW-REL-077-RELEASE-R3 APPROVED_WITH_NOTES/0**（机录 R6）；EVD-1041 |
| 4 | **FIX-339** | `8bd6a8a` | 版本锚参数化（DEC-195 a）——活动锚从工作流版本派生 + released_face 双判据 + 无佐证自称已发布显式 FAIL；hot fact source 9 条 0.38.x 假阳清零；R0→R1→R2（**REVIEW-FIX-339-CODE-R2 APPROVED_WITH_NOTES/0**，机录 ×3）；行为变更 B-1/B-2/B-3；EVD-1042 |
| 5 | **FIX-341** | `28690dd` | tpa 依赖解析查归档索引——归档索引解析器 + compute 可选参数（热表权威→归档集→fail-closed）+ change_triage 对齐 + 缓存失效守卫；TDD 144+92（负例四类）；**REVIEW-FIX-341-312-CODE-R0（合并）APPROVED_WITH_NOTES/0**；EVD-1043 |
| 6 | **FIX-312** | `7bb102b` | 归档引擎决策归属判据——governing refs 全归档才可迁 + 最新归版 + 短行 fail-closed；TDD RED 5→GREEN 9 + test_archive 126 零回归；活体 dry-run 零翻转；机录 REVIEW-FIX-312-R0；EVD-1044 |
| 7 | **FIX-314** | `a260637` | review_record 唯一键 (task,round)→**(task,round,reviewer)**——canonical-first + 三键守卫 + 历史零改写 + hook/Check 30 兼容 + GBK fail-closed；16 用例 TDD 红→绿；R0→R1（**REVIEW-FIX-314-CODE-R1 APPROVED_WITH_NOTES/0**）；行为变更 B-5；EVD-1046 |
| 8 | **FIX-342+FIX-344** | `f73bef7` | 归档防御词面收口（复合词×5 + 11 列 fail-closed + header 区扫描 + 缓存升级；真实数据五重零翻转指纹）+ Check 30c 后缀感知三盲区修复 + V8 假 WARN 消灭（HEAD 7 红→绿 9/9 + live 指纹一致）；合并审查 **APPROVED_WITH_NOTES/0**（机录 ×4）；EVD-1047/1048 |
| 9 | **FIX-320+FIX-322** | `0462f3b` | loop-claims 豁免账本（4 条九键 + digest/ID/键面三锚 + 防篡改三反相 + `exemptions_applied` 披露；installed_host BLOCKED→PASS）+ K-2 包名整串判定（三前缀归属 + 5 新测试 136 全量；Check 28w K-2 0/11 保持）；R0→R1（**APPROVED_WITH_NOTES/0**，机录 ×4）；行为变更 B-4；EVD-1049/1050 |
| 10 | **FIX-345** | `2466a80` | authority source records 归档感知重锚——DEC-104→归档决策行 L289 + AUDIT-133→审计报告本体 L3；双锚 lockstep 治理化重锚；product_release **BLOCKED→PASS**（loop-claims 语义面双模式全绿）；断锚 fail-closed 三形态负例；**REVIEW-FIX-345-CODE-R0 APPROVED_WITH_NOTES/0**；行为变更 B-6；EVD-1051 |
| 11 | **FIX-323+FIX-325+FIX-336** | `0a13b21` | 渲染面收口（fail-soft 守卫降级 + UNKNOWN fail-closed + 渲染单源）+ 3 真守卫（EEXIST 熔断/碰撞重试/CWD 反相 registerHooks 真注入；双变异红）+ discover 收集面（3066→3193，compat 126；FX-BASEURL-01 slice V2→V8 = FIX-326②）；合并审查 **APPROVED_WITH_NOTES/0**（机录 ×3 R0）；行为变更 B-7/B-8；EVD-1052/1053/1054 |
| 12 | **FIX-333** | `3bdf28f` | write-guard 非 UTF-8 边界全面收口——7 处捕获扩面（精确变体）+ 6 条 GBK 反相（RED 3E→GREEN 38）；Never raises 兑现；行中性 24453 恒等；R0→R1（**APPROVED_WITH_NOTES/0**，机录 ×2）；EVD-1056 |
| 13 | **FIX-332+FIX-337** | `21121c5` | 过期数据资产收口（金丝雀 resolved 登记 + 两文档收口注记 + DEC-194 补记落账）+ 派发纪律硬化（`$tmpHome` 规范 + 禁 `$HOME` 赋值 + 正负相 + incident 引用 + 机检提示）；Design 审查 **APPROVED_WITH_NOTES/0**（机录 ×2 R0）；EVD-1055/1057 |
| 14 | **FIX-313+FIX-346** | `845c050` | 渲染 parity 方向更正交付（**DEC-196**，产品零变更：跨渲染器孤立 CR 同哈希 parity 测试〔三组变异双向红〕+ 注释真实性 + catch/F4 权衡显式区分；机录 REVIEW-FIX-313-R1——R0 槽位系 0.81.0 期占用）+ 性能预算重定标（空闲定标 p50×1.5：median 8.0→27.0s / timeout 15→26s；减半反相双红；**红基线清零 850 OK**）；**REVIEW-FIX-313-346-CODE-R0 APPROVED_WITH_NOTES/0**；EVD-1058/1059 |
| ⟦15⟧ | **M-0 prep 批（本清单 + 三件套 + CHANGELOG 段 + FIX-324/326 并入 + 日期炸弹修复 + F-R1-02/RISK 提案）** | ⟦待回填⟧ | Release Agent 起草（2026-09-18）；Coordinator 审后随 M-1 候选提交落库 |
| ⟦16⟧ | **M-1 候选打包**（版本 bump 0.82.0 + `release-projection --write` 15 投影 + `core/releases/0.82.0.json` candidate + Change Inventory 冻结核定） | ⟦待回填⟧ | Coordinator（M-1）；候选 commit hash 由 M-2 期 `release-ledger --version 0.82.0 --no-remote` 派生回填 |

## 行为变更（面向用户 —— MUST 出现在 CHANGELOG 与升级说明）

详见 `docs/release/feature-flags-0.82.0.md` §2（B-1~B-8）：

- **B-1/B-2/B-3**（FIX-339）：进行中面放宽 / 已发布面 fail-closed 收紧（双判据 + 显式 FAIL）/ REL 归属识别放宽（任意格召回 + 词界守卫）；
- **B-4**（FIX-320）：loop-claims 豁免账本披露机制（九键 + 三锚 + `exemptions_applied`；真实漂移不豁免）；
- **B-5**（FIX-314）：review_record 键面 `(task, round)` → `(task, round, reviewer)`；
- **B-6**（FIX-345）：authority 双锚位置变更（归档决策行 + 审计报告本体）；
- **B-7**（FIX-336）：全量测试基线计数口径 2983 → 3193（M-0 复测 3200，见 Gate 10 注记）；
- **B-8**（FIX-325）：G-04 CWD 守卫交付 + **Node ≥22.15 限定语**（不得声称全引擎覆盖）。

## Candidate Gate Results（M-2 —— Coordinator 回填实测）

> **M-2 状态**：本表由 M-2 门禁实测逐项回填；已预检项以「M-0 预检」标注（**全部在 bump 前工作树实测（2026-09-18，`845c050` + M-0 批）——M-2 MUST 在 bump 后复跑**）。未回填项在 M-2 完成前不得视为通过。

| # | Gate | 预期 | Result |
|---|---|---|---|
| 1 | `check-version-consistency` | PASS（bump 后全投影 = 0.82.0） | ⟦M-2 回填⟧。**预期过渡态披露**：M-0 起本清单/CHANGELOG 已入 0.82.0 段而声明面仍 0.81.0 ⇒ bump 前 `FAILED — N mismatch(es)` 为**预期**（0.81.0 先例：FIX-327 收口后同型），bump + `release-projection --write` 后转 PASS；`plan-tracker 工作流版本` WARN 按 0.81.0 先例在 M-8 收尾才转 0.82.0（gitignored，不进 fail 集） |
| 2 | `check-projection-sync --fail-on-issues` | PASS（bump 后 15 投影同步） | ⟦M-2 回填⟧（M-1 `release-projection --write` 后复跑） |
| 3 | `check-injection-contract --fail-on-issues` | PASS | ⟦M-2 回填⟧ |
| 4 | `check-manifest-consistency --fail-on-issues` | PASS | **M-0 预检 PASS**（2026-09-18：Canonical/Actual 一致，`[PASS] Manifest and filesystem are consistent.`；M-0 批零文件增删——adapter-manifest.json / host-contract.json 均为既有文件内容修改）。M-2 在 bump 后复跑 |
| 5 | `cleanup.py --dry-run` | 零删除（`exit=1` = ERR_NOTHING_TO_CLEAN 正常终止码，判据是零删除） | ⟦M-2 回填⟧ |
| 6 | `archguard-ratchet`（**两次 `--regen` 后**） | 无新增 ERROR；**锚 24453 恒等预期**（0.82.0 窗口 `verify_workflow.py` 净变更已在 FIX-339 R2 期重锚 24453 并由后续 FIX-342/344/345「24453 零增行/恒等」声明保持；M-0 批零引擎行变更 ⇒ 预期 `R1 PASS 24453 ≤ 24453`） | ⟦M-2 回填⟧（M-0 期未改动引擎——不适用「两次 --regen」重生成义务；M-2 按 bump 后现场判定 R7 `committed==fresh`） |
| 7 | **Check 28w** `check-dsh-boundary` | PASS / 0 failing criterion（K-1~K-13） | **M-0 预检 PASS**（2026-09-18：`Result: PASS — 0 failing criterion(a)`；K-12 doctor 命令键注册在案——FIX-326① manifest 登记后 K-12 仍 PASS）。M-2 复跑 |
| 8 | `check-dsh-preset-smoke`（28u） | exit 0 + `real-home writes: 0` | ⟦M-2 回填⟧（隔离 `DSH_HOME`；0.81.0 Gate 8 的并发抖动观察项继续以复跑为准） |
| 9 | `check-dsh-preset-compat`（28v） | `23 / 18 / 5` + exit 0 + `writes: 0` | ⟦M-2 回填⟧（5 行 NO_SCHEMA 按 FIX-315 语义 `[NOT_RUN]` 披露） |
| 9b | `check-agent-adapters` | exit 0（FIX-326① 验收判据：manifest 加注后适配器契约仍同步） | **M-0 预检 PASS**（2026-09-18：`[STATIC] agent adapter dsh: runtime-verified` + `[OK] agent adapter contracts synchronized`）；`test_dsh_adapter` 53 OK 同批实测 |
| 10 | 全量测试基线 | 零产品代码回归（既有失败基线如实披露，不得写无条件 PASS）；**安静窗 850 复跑项**：`test_verify_workflow` 全模块复跑（0.82.0 期终态 = **850 OK exit 0**，FIX-346 红基线清零；M-2 在安静窗复跑并以当场值为准 + 披露时长/预算口径——0.81.0 Gate 13 登记的 release-gate unit-tests 子面 180s 预算 vs discover 实测 ~240s+ 的**可复现超时**口径延续，`SPG_RELEASE_GATE_TIMEOUT` 可覆盖） | ⟦M-2 回填⟧。**计数口径注记（B-7）**：FIX-336 期基线 = **3193**；M-0 prep 复测（TestLoader discover 口径，`countTestCases()`）= **3200**，且**隔离 worktree pristine `845c050` 同值 3200** ⇒ M-0 批 **Δ=0**，+7 差额**先于本批存在**（归因：3193 实测点（`0a13b21`~`3bdf28f` 期）之后 `21121c5`/`845c050` 的新增用例 + 活体数据耦合的 replay 族子测试生成面——`test_hooks`/`test_pre_commit_review_evidence` 的 live replay 子测试数随 gitignored 治理数据漂移，0.81.0 Gate 10 #2/#3 同族）。M-2 以当场 `Ran N tests` 为准并披露与 3200 的差额归因 |
| 11 | 三路径渲染 parity | 基线不变（0.82.0 窗口对 `lib/index.js`/`launch.py` 渲染语义**零产品变更**——窗口 diff 实测 `lib/index.js` 仅注释面） | ⟦M-2 回填⟧（预期 = 0.81.0 候选值 `6caf90fe…e55d`（16796 bytes）的 persona 版本行更新形态——bump 后按 0.81.0 先例「差异恰为版本行 1 处」判定；**M-2 实测为准，不预填**） |
| 12 | 契约 SHA | 记录当场值（**M-0 触碰披露**：FIX-326③ 更正 `adapters/dsh/host-contract.json` 三处 evidence.* 写入路径 note（as-built 对齐）——**0.81.0 基线 `96F92485…43FC6E`（74702 bytes）已不再适用**） | **M-0 预检值（候选态随批刷新）**：`63B28311330DCDED6192CC3350C81735F8557E0D6115D570ABCA328853228DF2`（**75331 bytes**；`schema_version: 1` 不变；`recording.writer` 字段与钉扎测试 `test_recorded_evidence_is_not_hand_filled` 未动——`test_dsh_contract` 120 OK 同批实测）。M-2 在 bump 后复测并记录；K-1/K-8/K-11/K-12 判据不受 note 更正影响（Check 28w M-0 预检 PASS 同批实证） |
| 13 | `check-release` / `release-ledger` | 发布记录一致（候选态 `--lineage-mode candidate`；`core/releases/0.82.0.json` candidate 随 M-1 入库；**MUST 后台作业执行**——0.81.0 实测 240s 超时纪律） | ⟦M-2 回填⟧（静态面以工具打印 PASS 行数为准确口径——0.81.0 F-R1-02 教训；执行面既有基线逐条归因） |
| 14 | 回滚方案 | 已交付且可执行（**回滚区间 = 整个 0.82.0 窗口 `e376ddf..<发布 tip>`**——起点 = 0.81.0 发布 tip〔v0.81.0^{commit} peel 实测〕，`845c050` 非 0.81.0 发布 tip〔见 rollback-plan §勘误注记〕；tip 由 M-5 回填）；revert 干跑（回滚演练）在 M-2/M-5 期于隔离 worktree 执行 ≥1 次 | ⟦M-2 回填⟧（`docs/release/rollback-plan-0.82.0.md` 已交付——演练记录按 0.81.0 先例 §4.1 形态回填） |
| 15 | `check-loop-runtime-claims`（双模式） | **语义面双模式全绿预期**（`installed_host` PASS / 0 findings + 4 豁免披露；`product_release` PASS——FIX-345 重锚收口；本版 REL-078 门禁前置） | ⟦M-2 回填⟧（M-0 期终态声明 = FIX-345 EVD-1051；M-2 复跑核实豁免账本 digest 锚） |

### Gate 10 明细指引（M-2 全量失败清单纪律）

按 0.81.0 先例执行：全量原始失败清单**逐条贴出**（块 = unittest 的一个 FAIL/ERROR 报告），候选态 vs pristine 基线（隔离 worktree `git worktree add --detach`）同命令对照，逐条归因四级：产品回归 / 测试 fixture 缺陷 / 活体治理数据耦合（pristine worktree 无 `.governance/`）/ 环境敏感。**0.82.0 期已收口的 0.81.0 既有红基线（预期不再出现，若出现即真回归）**：① FIX-320 族 3 条（`FIX300DualCaliber` ×2 + `LoopRuntimeClaimAdapter`——本版已闭环）；② `test_change_triage.AgentLocksAcquireCliTests.test_cli_success_expected_new_and_warn_disclosure` 日期炸弹（本版 M-0 已修：红→绿 + 注入时钟任意日期绿）；③ `LoopRuntimeClaimAdapter` 的 15s 超时预算已由 FIX-346 重定标 26s。**预期仍红的活体数据耦合族**（如实披露，不阻断）：`test_hooks` / `test_pre_commit_review_evidence` 的 live replay 族（pristine worktree 转 skip）；`test_loop_runtime_claims` inventory 族对活体 decision-log 的计数耦合已由 FIX-345/320 收口——当场值为准。

## F-R1-02 数据面处置提案（0.82.0 锚下 missing-active-task 预期过报清单 —— Coordinator 落账）

> 来源：REVIEW-FIX-339-CODE-R1 **F-R1-02**（P3，「未修复（有意保留，方向性维持）」——已声明的 fail-closed 过报族，REL-078 prep 期消化）。以下清单为 **M-0 prep 期引擎直调实测**（2026-09-18）：TEMP 副本仅改 `工作流版本` 行为 0.82.0，真实 `.governance/` 零触碰；helper `_hot_task_ids_for_version` 与 `check_hot_fact_source_consistency` 直调。

**权威任务集（引擎直调）**：`ids(0.82.0) = [FIX-335, FIX-337, FIX-339, FIX-341, FIX-342, FIX-343, FIX-344, FIX-345, FIX-346, REL-078]`（delivered=False / declared=True）。

**bump 后预期 hot-fact 过报（TEMP 副本实测 10 条，其中 1 条为模拟伪影）**：

| # | 预期 FAIL 行 | 归因 | 分类 |
|---|---|---|---|
| 1 | `0.82.0 roadmap row missing active task FIX-335` | 状态格叙事「副本 bump 0.82.0」把已交付 0.81.0 任务牵连进 0.82.0 任务集 | **假阳**（R1 F-R1-02 ① 同源） |
| 2 | `…missing active task FIX-337` | roadmap 0.82.0 行任务列仅以斜杠缩写「…336/337」出现，`_contains_fix_token_or_range` 不解析斜杠缩写 | **字母面假阳 / 意图面真实缺口**（R1 ② 同源） |
| 3 | `…missing active task FIX-341` | roadmap 0.82.0 行任务列确实未列 | **真缺口**（R1 ③ 同源） |
| 4~8 | `…missing active task FIX-342 / FIX-343 / FIX-344 / FIX-345 / FIX-346` | 五行 0.82.0（或后续）目标版本任务行在 M-0 时点已闭环/在飞，roadmap 0.82.0 行任务列（DEC-195 规划态文本）未逐一列名 | **真缺口**（数据演进新增——0.82.0 窗口交付的任务行） |
| 9 | `project overview missing active version 0.82.0` | 项目总览「活跃版本」仍 0.81.0 | **真缺口**（M-1 bump 的自然组成部分） |
| 10 | `hot sections overstate 0.82.0 as released…` | **模拟伪影**——探针以单词替换仅改版本 token，「已发布 2026-09-14 REL-077」叙事被留在 0.82.0 行上所致；真实 M-1 bump 重写版本行后不触发（REL-078 行未交付，B-2 保护断言正常在场） | 伪影（非预期过报） |

**处置建议（M-1 由 Coordinator 落 `.governance/plan-tracker.md`，本批不改治理数据）**：

1. **主路径（推荐）**：M-1 版本投影时同步更新 roadmap **0.82.0 行**——任务列补全 token：`FIX-341/342/343/344/345/346`，并把「…332/333/336/337」斜杠缩写**展开为全 token**（或改用 `FIX-336`、`FIX-337` 分列）；项目总览活跃版本 → 0.82.0。此为 M-1 bump 的自然动作，消 #2~#9 共 8 条。
2. **FIX-335（#1 假阳）**：推荐**数据侧叙事清理**——FIX-335 任务行状态格的「副本 bump 0.82.0」措辞改为不含版本 token 的表述（如「副本随版本投影更新」），使引擎任意格召回不再牵连已交付任务；**不建议**把 FIX-335 列入 roadmap 0.82.0 任务列（已交付任务入活跃 roadmap 污染 roadmap 语义）。若暂不清理，则该 1 条作为已声明过报在 M-2 如实披露（R1 已裁决方向性维持）。
3. **引擎侧候选（另立任务，非本版义务）**：`_contains_fix_token_or_range` 补斜杠缩写语义（R1 处置建议原文）——数据侧展开斜杠缩写后优先级降低，登记 DEC/任务候选池。
4. **snapshot 面联动（非过报，序列义务）**：M-1 bump 后 `session-snapshot.md` 版本/日期面将按 FIX-105 判据报 mismatch 直至 M-8 快照更新——发布链自然序列，不属本提案范围。

## RISK 复评提案（截止 2026-09-30 复评窗 —— Coordinator 裁决落 risk-log）

> 三段均为 Release Agent 复评建议（M-0 起草），**不直接改 risk-log**；「维持/关闭/延期」裁决权在 Coordinator（必要时升级用户）。

**RISK-036（官方收录与外部验证——1.0.0 blocker；高）——建议：维持打开，关闭条件不变。** 依据：① 本版 0.82.0 全部交付为内部治理引擎/测试/治理记录面，未推进官方级 plugin manifest、assets、英文首屏叙事、5 分钟成功路径、公开 E2E 矩阵、外部项目验证、marketplace 真实 E2E 中的任何一项；② 0.81.0 的真机三项回贴（EVD-1040）属**真实环境验收**进步，但外部首会试点（external first-session pilot）仍零实证；③ 保守边界 token（no official approval / no marketplace approval / do not claim 1.0.0 production-ready）在 0.82.0 三件套中逐字维持。复评窗 2026-09-30 的可交付动作：把「官方提交包最小集」从 RISK-036 描述中拆出为可清点 checklist（现描述为能力清单，不可逐项判定），使下次复评可机械核对——本提案不改变风险敞口。

**RISK-039（架构腐化看护缺口——1.0.0 关联；高）——建议：维持打开，复评注记更新为「棘轮面收口、拆分面未动」。** 依据：① **看护面实质增强**——ArchGuard 棘轮 R1~R7 已 fatal 化并在 0.81.0/0.82.0 两个发布窗持续实战（0.82.0 窗口 FIX-339 重锚 24453 + 后续批次「24453 恒等/零增行」声明、M-0 批零引擎行变更）；Check 28w K-1~K-13 + 契约矩阵 + 豁免账本 digest 锚把「第二事实源」类腐化面从自觉型收口为机检型；② **God Module 主判据未动**——`verify_workflow.py` 24453 行仍是单文件巨模块，0.59.0~0.64.0 渐进拆分路线未执行，模块内聚靠棘轮锚而非结构改善；③ 关闭标准（AUDIT-121 F1-F6 逐项收敛 + 拆分路线兑现）未满足。复评窗动作：把「棘轮锚只升不降」的实战记录（两窗 0 违规）写入复评注记作为看护有效性的正向证据，同时如实声明拆分面零进展。

**RISK-046（派发锁漂移/空转——治理协调；中）——建议：维持打开至本复评窗随批收口（最后一次延期候选），关闭裁决可入 2026-09-30。** 依据：① **根因修复已交付且经实战验证**——FEAT-013（0.79.0）`acquire_dispatch_locks` 两面机制（写入前存在性校验 exit 2 零写入 + 当日 triage files 交叉核对 WARN 披露）+ 模板锁操作机器化（禁手写）；② **本版追加结构预防**——FIX-337 派发纪律硬化（`$tmpHome` 非保留变量名规范 + 禁 `$HOME` 赋值 + 负相示例 + 机检提示）关闭了同族 incident-20260914 的隔离失效形态；③ 0.81.0→0.82.0 两窗**零新增派发锁 incident**（incidents log 无同族新条目——M-2 可复核）；④ 0.79.0 复评登记的遗留候选（跨日静默 + 豁免披露 / 读写竞态 / 绝对路径旁路 F-1/F-2/F-4）无新增实证触发。建议复评窗按「根因闭环 + 两窗零复发 + 防御面补强」三关闭标准裁决关闭；若用户裁决保守，则延期理由应落在「跨日竞态面未机检」而非原风险描述。

## 真机验收（0.81.0 三项回贴有效；本版无新增真机项）

- 0.81.0 真机三项已由用户回贴通过（2026-09-14，EVD-1040；`docs/release/release-checklist-0.81.0.md` §真机验收）。
- **0.82.0 窗口对 dsh 交付面为注释级零行为变更**（窗口 diff 实测：`adapters/dsh/` 零改动；`lib/index.js` 仅注释；渲染产物字节不变）⇒ 无新增真机三项义务；M-2 的 28u 隔离冒烟 + 三路径渲染 parity（隔离 `DSH_HOME`）为交付面回归的机检载体。
- 0.81.0 遗留披露延续：RISK-050 升级演练**已做**、演练方式与结果明细待用户补充（supersede 行追加）——非本版义务，维持登记。
- 纪律（保留）：任何 release 文档/CHANGELOG 不得对未回贴的真机项声明通过。

## M-8 收尾义务

- 发布后：`core/releases/0.82.0.json` **由 candidate 态转为 released 态**（candidate 态随候选打包提交落库）+ `release-ledger --version 0.82.0 --remote origin` 核对 + `session-snapshot` 更新 + plan-tracker 版本行转 `released`（工作流版本字段 0.81.0 → 0.82.0 同步——Gate 1 预期过渡态 WARN 随之消除）；
- 补推义务检查：`v0.79.0`/`v0.80.0`/`v0.81.0` 已推送（FIX-338 R3 实证三 tag 逐位一致）⇒ 本版无历史补推义务；M-7 推送 `v0.82.0` 即可；
- 持续归档触发检查：版本 bump / released 态写入后 `archive.py migrate --auto --dry-run` → 如报告需要归档则执行 + `check-archive-integrity`；**归档完整性失败阻断发布完成**；
- M-0 批移交的数据面动作随 M-1 落账后勾销：F-R1-02 提案 §1/§2（roadmap 行补全 + FIX-335 叙事清理）。

## M-2 执行序（Coordinator 实测约束）

- **顺序**：先跑只读/廉价门禁（1~5、7~9b、11~12），再跑产物生成类（6 的两次 `--regen`——若 bump 触碰引擎行数则 MUST 重生成并给出「前后差异摘要 + 第二次无变化（幂等）」双证据；若 `--regen` 试图写未授权路径 ⇒ 停下报告，不得越权写入），最后跑 10（全量 + 安静窗 850 复跑）与 13（check-release）。
- **安静窗 850 复跑项**：`test_verify_workflow` 全模块（850 用例）在安静窗（无并行负载）复跑，预期 **850 OK exit 0**（FIX-346 红基线清零终态）；同时披露墙钟时长与 release-gate unit-tests 子面 180s 预算的关系（0.81.0 Gate 13 的可复现超时口径延续——`SPG_RELEASE_GATE_TIMEOUT` 覆盖通道如实声明）。
- **check-release 纪律**：MUST 以后台作业（`run_in_background`）执行并轮询 `job_output`（0.81.0 实测 240s 超时先例）；候选态 `--lineage-mode candidate`，不得以候选态 PASS 代替发布完成态 lineage 证据（release-checklist SKILL 硬规则）。
- **真机项禁声明纪律**：保留（见真机验收节）。
- **冻结纪律**：M-1 冻结前 MUST 消除本清单全部 ⟦待回填⟧/⟦待落地⟧ 占位——**例外 = M-2 派生回填类**（候选打包 commit 与 M-0/M-1 批 commit hash：其回填依赖 `core/releases/0.82.0.json` 先随候选提交入库后 `release-ledger --version 0.82.0 --no-remote` 的派生——0.81.0 EVD-1034 / R1 F-R1-02 先例同型，属预期前置依赖而非冻结违规）。

---

*M-0 草案（2026-09-18，REL-078 prep——Release Agent 起草）。全部实测值标注实测时点与树状态（`845c050` + M-0 批，bump 前）；候选态门禁值以 M-2 回填为准。Change Inventory 按 `git log --oneline e376ddf..845c050` 实测 14 commits 编号 1..14 连续；M-0/M-1 批行待 M-1 冻结回填。FIX-324/326 逐项处置报告与本清单同批交付（§FIX-324/326 并入处置——见 Release Agent 结构化返回，M-1 期由 Coordinator 决定是否作为附录随批入库）。*
