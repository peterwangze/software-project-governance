# Changelog

本文件自 0.88.0 起在仓库根承载 `software-project-governance` 的版本变更记录（REL-087 M-1 triage-normalized 锁面交付物）。

> **双位过渡披露**：0.87.0 及更早的全部历史版本记录见 [`project/CHANGELOG.md`](project/CHANGELOG.md)（REQUIRED_SNIPPETS 历史判据面）。0.88.0 段双位同文维护；canonical 归属（根 vs `project/`）留 M-3 审查裁决，裁决前漂移风险由双位同段纪律控制。

## [0.88.0] - 2026-09-25

### 0.88.0 - **执法硬化 + 存储架构首表 + 能力铺开（Enforcement Hardening & Storage Separation First Table）**：write-guard 分族 BLOCK + decision-log JSON 权威化首表 + closure 取消/重开/接管 + 回合心跳 + B-7 三拆票（REL-086 / FIX-373~389 / FEAT-060~064/044/045 / DEC-229~239 / EVD-1134~1163）

0.88.0 是 **MINOR** 发布，承载 REL-086（0.88.0 M-0 规划双审闭环——`docs/planning/version-plan-0.88.0.md` 设计半面 R0 NEEDS_CHANGE/4→修复→**R1 APPROVED_WITH_NOTES/0** + 发布半面 R0 NEEDS_CHANGE/3→修复→**R2 APPROVED_WITH_NOTES/0**，双 GO）+ **DEC-229（0.88.0 标准链预授权 + 架构顾问协作协议：用户 2026-09-23「把已经登记的任务一次性推进闭环，我授权 Coordinator 按照推荐进行推进，授权发布版本承载修改。过程中的决策多和『架构与疑难问题顾问』进行讨论。」——预授权不免除 M-2 门禁实测与 M-3 双半面审查）**。版本主题：**执法硬化 + 存储架构首表 + 能力铺开**——0.87.0 收口后热表全清（25/25），本版承载 DEC-226 出槽清单 + 审查留票族全部已登记项，按 arch 顾问修正案（gpt-6-astra 2026-09-23，DEC-229③ 协作协议兑现）**按不可逆边界与依赖排序**五阶段交付：A 契约与卫生（可逆性高，先行）→ B 恢复与执法基础（BLOCK 前置基座，WARN 姿态）→ C 单点存储切换（独立可验证/可恢复边界 #1）→ D 执法激活（边界 #2）→ E 能力与剩余。**核心风险对冲（arch 总体提醒——本版最高优先不变量）**：guard 依赖基线/台账 → 台账依赖写入器 → 写入器正迁移存储 → 发布依赖检查结果——系统正在用被修改的机制证明自己正确；对冲 = FEAT-061 独立迁移/恢复证明包（旧 md 解析器裁决、切换前校验器、独立性声明必填节——独立性操作化三条）+ 跨票组合测试集（version-plan §3 条 2）。

**24 票交付**（git log v0.87.0..M-1 tip 实测——阶段 A 14 票〔含 0.87 出槽先落 3 票 + 调查票派生 3 票〕→ B 2 票 → C 1 票 → D 1 票 → E 6 票）：

**阶段 A：契约与卫生（14 票）**

- **FIX-373（共享切分器状态泄漏，commit `3c3218d`——0.87.0 出槽票）**：quote 分支补 not in_code_span 守卫——EVD-248 形状 code-span 内引号折叠误报消解（TDD 红 3F→绿 6/6；消费方指定套件 120 用例 0 失败）。REVIEW-FIX-373-CODE-R0 APPROVED_WITH_NOTES/0；EVD-1134/1135。
- **FIX-374（9-cell 豁免消歧，commit `6845756`——0.87.0 出槽票）**：format check 9-cell 豁免与截断 LIVE 行内容启发式消歧——cells[6] 日期形状判据（_EVIDENCE_DATE_SHAPE_RE）区分合法历史行与缺 Date 截断 LIVE 行，fail-blind 消除。
- **FIX-378（e2e 副本守卫同步，commit `44cb534`——0.87.0 出槽票）**：e2e legacy 快照副本切分器守卫与主仓同型同步 + backport docstring（REVIEW-FIX-373-CODE-R0 F-1 承接；副本 git 忽略——declared_legacy_snapshots 非投影目标，收敛即红排除再生）；本票同时落 FIX-381 制度化首条台账。EVD-1136/1137。
- **FIX-375（writer 族三边缘收口，commit `04b7a42`）**：①引擎分发返回码透传（verify_workflow.py L25502 红态 exit 0 假绿→exit 2——8 return-style handlers 全透传，DEC-230/231 口径）②畸形 --operation-id 结构化 schema_violation+exit 2 无裸 traceback ③locks-release 三恢复腿 released_files 审计一致（pre-read 移入 _TargetLock 堵并发）。TDD 6 红→9 绿；R0→R1 APPROVED/0 终态；EVD-1140/1141。
- **FIX-376（FIX-371 遗留候选合并处置，commit `3d31c49`）**：F-3 状态 cell 改自右向左扫描（豁免面零变化=定理+活体双证：130 行全等/diff=0，DEC-232 裁定窄口径维持）+F-4/F-5 零调用 helper 删除+F-6 legacy REQ 形态+混合 fan-out 判别用例+F-7 docstring 勘正。REVIEW-FIX-376-R0 APPROVED_WITH_NOTES/0；EVD-1142。
- **FIX-386（0.87 未承载遗留小项包，commit `d6dd300`）**：AUDIT-152 账本写回（clock_window_sensitive 家族 8→9+FIX-364 resolved 19→20）+ADR-011/012 勘误注记（300,000→指向 361,923 公式，历史结论零改写）+REVIEW-FIX-370 F-2 验证（acquire 无 record-target 锁 TOCTOU 窗口确认→RISK-046 缓解列扩展）。R0 NEEDS_CHANGE/1→R1 APPROVED/0；EVD-1143。
- **FIX-377（调查票闭环，commit `17e5663`）**：FACTS_PRINT_TOTAL 1306→1316 +10 漂移归属（10/10 全归 a6d3bfb FIX-371 豁免披露输出——census walk 双端 1306/1316）+28+2 失败四类归类+修复候选 triage（FIX-387/388/389 机录入账）。REVIEW-FIX-377-R0 APPROVED_WITH_NOTES/0（11 点 census 全等+决定性复现坐实）；EVD-1144。
- **FIX-387（套件内全局态污染修复，commit `0840876`——P1 插队票）**：FIX-375 进程内 main() 全局重绑泄漏——EngineDispatchExitCodeTests 改 setUp 快照/tearDown 恢复完整重绑面（12 全局量）+HostRootRebindCanaryTests 防回归 canary（负面对照 13/13 漂移检出）。REVIEW-FIX-387-R0 APPROVED/0（全套件 913s+HEAD 存档树对照）；EVD-1145。
- **FIX-389（LRC 文档面清账，commit `9df2381`+闭环 `cdc3a0a`）**：REL-086-R2 五处 ragged row 修复+FIX-376-R0 L42 断言面改引用——两文档使真实树扫描 fail-closed（loop-runtime 5+2 红）消解。REVIEW-FIX-389-R0 APPROVED_WITH_NOTES/0（语义完整性字符级+根因修正坐实）；EVD-1148。
- **FIX-388（static-pin 账本重审计，commit `b3577c8`）**：12375→12550 重锚（FIX-373 插入漂移——rot-guard 活体实证）+12674 补登（FIX-376 出生未豁免）+env_failure_classification 定向刷新（+7/−7 限 review_doc_claim；触发源轮换登记）。方案 A 行号锚保持（dynamize 否决）。REVIEW-FIX-388-R0 APPROVED_WITH_NOTES/0（git 考古三位点闭环）；EVD-1146/1147。
- **FIX-379（量测边缘观察四项打包，commit `b7df86c`）**：journal detail 透传根因修复（governance_store 顶层扁平 refusal 第三来源识别）+governance id family 词表派生单一来源化（DEC-233）+conflict 退出码差异 epilog 明示+pre-probe 时序语义注记。REVIEW-FIX-379-R0 APPROVED_WITH_NOTES/0；EVD-1149。
- **FIX-380（P3 杂项包，commit `c349f8e`）**：_format_issues 三副本提取模块级单源（7 调用点迁移，零行为差 945+132 全等）+fixture-engine reason 补 backport 溯源注记+e2e 副本切分器钉归类不适用（四理由）。REVIEW-FIX-380-R0 APPROVED_WITH_NOTES/0；EVD-1150。
- **FIX-381（切分器 backport 政策制度化，commit `b03a0b4`——⑨定案）**：五制度件落 legacy_snapshot_backport_policy 机读块（触发三判据/快照清单/补丁台账八字段/双运行 parity 契约/隐性耦合检查+可再生性——DEC-234 裁定）+守卫精化（policy/台账空洞红+stale-ledger 机检红）+重放 9/9 实跑。REVIEW-FIX-381-R0 APPROVED_WITH_NOTES/0；EVD-1151。
- **FIX-382（9-cell 消歧组合判据扩展，commit `ce93eb3`——A 阶段收官）**：11 项形态决策表（R4/R5 落地 c7 日期机证——假阳性消除；R1/R2/R3 显式不修+披露——DEC-235）+静默集不变量（30 输入穷举差分实测 S_new=S_old）+真实数据差分 IDENTICAL。REVIEW-FIX-382-R0 APPROVED_WITH_NOTES/0；EVD-1152。

**阶段 B：恢复与执法基础（2 票）**

- **FEAT-060（write-guard 违规持久状态机+hook 消费权台账，commit `c515776`——B1）**：811 行实体模块——12 字段违规记录+三态转移+消费权闭集（v1 单消费者 guard CLI）+ops 可恢复消费事务（journal 三段+resume 三分支 fail-closed）+DEC-236 口径三条（R2「WARN 不改基线」机制面口径）。活体首捕 born-live：WV-62097f（FIX-382 手工翻转无凭证）→补凭证→守卫自动消费闭环。REVIEW-FEAT-060-R0 APPROVED_WITH_NOTES/0（7/7 独立复验+字节恒等双验）；EVD-1153。
- **FIX-383（B-7c 发版管线自举，commit `0ff12f3`）**：release-window-bootstrap 内置链（--check-only 前探针 reconcile-vs-execute）+write-guard-bootstrap 子命令（五检查只读世界判定+converge=守卫工件恢复治理零写入）+三类中间态恢复映射+双故障点 kill→resume 零人工修复。REVIEW-FIX-383-R0 APPROVED_WITH_NOTES/0；EVD-1154。

**阶段 C：单点存储切换（1 票——本版最高风险票）**

- **FEAT-061（decision-log 存储分离首表，commit `61618a5`——C1 阶段性交付）**：六层落地——权威状态机（闭表+epoch fencing 端到端+唯一线性化点）/双后端写入路由（MD 字节零变化+JSON 同 CAS/幂等）/迁移编排（freeze 四闭合+activate 三段 journal+rollback 对称复检）/独立校验器（禁导入自签拒绝+旧解析器逐字符镜像+三类完整性证明+负向注入 7 例）。DEC-237 arch 前置复核（有条件不通过——P0×5 补齐后派发）+DEC-238 口径裁定。R0 NEEDS_CHANGE/2（**P0-F1 竞窗数据丢失+P0-F2 砖化——均活体复现**）→修复（锁内 fenced 重读+键集存活+seam 钉）→R1 APPROVED_WITH_NOTES/0。真实 179 行演练 round_trip（独立性三规则活体实证）；切换授权前置三条件入 RISK-059。EVD-1155。

**阶段 D：执法激活（1 票）**

- **FEAT-064（write-guard 分族 BLOCK 激活，commit `a8afcbf`——D1 机制交付，真实翻转留 Coordinator）**：五族裁定（evidence/review/decision/ops_ledger 四族 BLOCK+task_status WARN 后置——DEC-239）+BLOCK 写后执法+R2 逐面钳制（DEC-236① 兑现）+break-glass 四件套（五限定+use 审计不可静默）+FEAT-060 遗留三件（hook_identity/A-B-A 会话累计/SESSION_ID 接线）+FIX-383 registry 收口（96→97+contract-matrix 指令化再生）。REVIEW-FEAT-064-R0 APPROVED_WITH_NOTES/0（八焦点全符合+双版本探针）；EVD-1156。

**阶段 E：能力与剩余（6 票）**

- **FEAT-062（closure 取消纵切，commit `14797be`——E1）**：限定入口（状态/授权/undetermined/外部副作用/管道符换行零写门）+CAS 单终态（run lock 线性化+竞争恰一终态）+DEC 经写入器登记+仅释放自有锁（ARCH-09 同型）+对账（世界是真相）；中断恢复=终态先行+双腿幂等重放。R0 APPROVED_WITH_NOTES/0→F-1~F-3 修→R1 APPROVED/0 终态（真锁竞争注入 92.86s+CLI 探针双面+逐行 diff 无夹带）；EVD-1157。
- **FIX-384（B-7a 归档 index-rebuild，commit `6360ab1`）**：rebuild_index 闭环（快照→确定性重建→integrity 校验）+损伤分类+errors=replace 容错（U+FFFD 四类探针零伪造）+无条目非结构化登记+CLI。R0 NEEDS_CHANGE/1（P1-1 Check3 口径不对称死循环）→修复（_extract_decisions/risks 共享函数单一来源）→R1 APPROVED_WITH_NOTES/0；EVD-1158。
- **FEAT-045（串行链路并行段识别审计闭环，commit `467fb55`——E4 纯审计票零源码修改）**：三段清单（批量化已由标准链交付/commit 批量化不适用 D4+对账粒度/预备段不适用/真断点=标准链锁腿 TTL 收缩非真释放——三处过时披露+四点独立互证）+DEC-220 勘正双落。REVIEW-FEAT-045-R0 APPROVED_WITH_NOTES/0；EVD-1159。
- **FEAT-063（closure 重开+异常接管，commit `d68355f`——E2）**：重开 lineage（closure_reopened 事件+单一后继+零擦除实证）+执行代际 fencing（sidecar+写端三面校验+旧代际零效果+closure_fenced 幂等）+TOCTOU 修复（锁内 re-read 三形态拒绝——R0 P0-1 活体 7/7→R1 三形态实测+红相双钉+探针翻转确认）。R0 NEEDS_CHANGE/1→R1 APPROVED_WITH_NOTES/0 终态；EVD-1160。
- **FEAT-044（subagent 回合预算与收尾心跳，commit `d7b9add`——E3）**：resolve_round_budget 三层参数化 fail-closed+heartbeat_should_fire/payload（N=3 无产物上报——stop_proof=False 全链钉死）+interrupt_recovery_payload 恢复产品化（事实绑定+防扩面守卫+有界 escalation）+compute_stall_report 等待税遥测+33 新测试。REVIEW-FEAT-044-R0 APPROVED_WITH_NOTES/0（9 MUST 全过+17 独立探针）；EVD-1161。
- **FIX-385（B-7b 大表断点续迁，commit `3fb42c0`）**：journal 相位机+批游标+单线性化 commit（同路径锁互斥）+resume 世界判定（三 crash 窗可续+终态等价+守恒）+单源抽取+DecisionStoreAuthorityConflict fail-closed+F-1 TOCTOU 修复（投影重写临界区化+同锁域互斥+in-lock 重判零写入）。R0 APPROVED_WITH_NOTES/0→F-1 修复（2 红绿）→R1 APPROVED_WITH_NOTES/0；159P+286P 相邻；RED 16F/manifest 882 勘正入 EVD；EVD-1163。

**M-0 规划 + M-1 bump（非五阶段票）**

- **REL-086（M-0 规划双审，commits `266c32b`/`7d6ff6a`/`0233f49`）**：version-plan-0.88.0 双半面审查链（Design R0 NEEDS_CHANGE/4→修复→R1 APPROVED_WITH_NOTES/0；Release R0 NEEDS_CHANGE/3→修复→R2 APPROVED_WITH_NOTES/0——F-1~F-13 全闭环）+arch 顾问协作（三次尝试两失败一成功——成功轮意见全量消化：批次重排/⑨政策化/guard 持久状态机/存储读适配先行/取消纵切先行/⑩拆票）+A4 自依赖环数据勘正（非票 M1.2 通道——原拟票 ID「FEAT-001」与热表终态行冲突勘误）。EVD-1162。
- **REL-087（M-1 版本 bump，本票）**：0.87.0→0.88.0 全仓（SKILL.md frontmatter 权威锚+REQUIRED_SNIPPETS 六锚+投影 28 面+双根 entry sync——FEAT-059 先例形态）+CHANGELOG 0.88.0 段+static-pin 账本消解（见「版本投影」段）。

**⑥ 治理面**：窗口内 **11 决策**（**DEC-229 预授权+架构协作协议** / **DEC-230/231 FIX-375 退出码透传口径+缺陷落点更正** / **DEC-232 FIX-376 豁免判据窄口径维持** / **DEC-233 FIX-379 id 词表单一来源** / **DEC-234 FIX-381 backport 政策裁定** / **DEC-235 FIX-382 9-cell 取舍** / **DEC-236 FEAT-060 三条口径** / **DEC-237 FEAT-061 前置复核有条件不通过（P0×5）** / **DEC-238 FEAT-061 阶段性交付口径** / **DEC-239 FEAT-064 五族执法裁定**）+ **30 EVD**（EVD-1134~1163——交付审查链机器写入延续；EVD-1132/1133 为 0.87.0 M-8 收口〔窗口内 `fc69196`，属前版收尾〕）+ 审查报告留档（review-FIX-375~389 / review-FEAT-060~064 / review-REL-086 系列——docs/reviews/）。审查链含 NEEDS_CHANGE→修复→R1/R2 转化五票（FIX-375/386/384/063/385）+ FEAT-061 P0×2 活体复现修复，全部 0 unresolved blockers 终态。

### Added

- **closure 取消/重开/异常接管路径（FEAT-062/063；行为变更 B-14）**：限定入口→CAS 单终态→cancellation op 登记→仅释放自有锁→对账；重开保留原 closure 新尝试编号不擦历史；接管=执行代际 fencing 写入端校验。纯新增能力面，无删除。
- **write-guard 违规持久状态机+消费权台账（FEAT-060）**：12 字段违规记录+三态转移+guard CLI 消费权闭集+ops 可恢复消费事务（journal 三段+resume 三分支 fail-closed）。
- **decision-log JSON 权威化首表（FEAT-061 阶段性交付；行为变更 B-13）**：DecisionRepository 六层（权威状态机/双后端路由/迁移编排/独立校验器）；decision-append 外部 CLI 契约不变。
- **subagent 回合预算与收尾心跳（FEAT-044）**：resolve_round_budget 三层参数化+heartbeat 上报+interrupt_recovery 恢复产品化+compute_stall_report 遥测。
- **归档 index-rebuild CLI（FIX-384）**：快照→确定性重建→integrity 校验闭环+损伤分类。
- **发版管线自举（FIX-383）**：release-window-bootstrap 内置链+write-guard-bootstrap 子命令（只读世界判定+converge 恢复）。
- **guard 分族 BLOCK 执法（FEAT-064；行为变更 B-12）**：evidence/review/decision/ops_ledger 四族 WARN→BLOCK+break-glass 恢复通道（限定留痕不可静默）。

### Changed

- **全仓版本面 0.87.0→0.88.0（REL-087）**：SKILL frontmatter 权威源+28 投影面+双根 entry bootstrap+REQUIRED_SNIPPETS 六锚统一再生（FEAT-059 先例形态——`release-projection --write` 单次收敛）。
- **CHANGELOG 双位过渡（REL-087）**：本版段同时落 `project/CHANGELOG.md`（历史连续判据面）与仓库根 `changelog.md`（triage-normalized 锁面交付物）；canonical 归属留 M-3 审查裁决。
- **writer 族失败退出码透传（FIX-375；DEC-230/231）**：红态 exit 0 假绿→exit 2——迁移=读退出码。
- **governance id family 词表单一来源化（FIX-379；DEC-233）**：task 族词表派生自 task_priority._TASK_FAMILY_PREFIXES，additive-only 补齐 13 前缀可引用性。

### Fixed

- **共享切分器 quote 分支状态泄漏（FIX-373）**——EVD-248 形状误报消解；e2e 副本同步（FIX-378）。
- **format check 9-cell 豁免消歧（FIX-374+FIX-382）**——缺 Date 截断 LIVE 行漏报消除+组合判据扩展（假阳性消除、静默集不变量穷举实证）。
- **writer 族三边缘（FIX-375）+套件全局态污染（FIX-387）**——返回码透传/结构化 schema_violation/恢复腿审计章；进程内 main() 重绑泄漏修复。
- **LRC 文档面 ragged rows（FIX-389）+账本写回与勘误（FIX-386）**——真实树扫描 fail-closed 消解；ADR 历史值勘正注记。
- **static-pin 账本重审计（FIX-388）+量测边缘观察四项（FIX-379）**——漂移重锚+出生补登；journal detail 透传根因修复。

**行为变更（用户可感知，B-12~B-14 —— MUST 出现在升级说明）**：

- **B-12**（FEAT-064·write-guard 分族 BLOCK 激活）：evidence/review/decision/ops_ledger 四族写入 WARN→BLOCK（task_status 族维持 WARN 后置；启用族由写路径覆盖率裁定——DEC-239）。回退 = 族级 flag 回 WARN（数据级）经 break-glass 通道（限定对象/操作者/理由/有效期/次数+不可静默记录——guard 自指场景同样适用）。
- **B-13**（FEAT-061·decision-log JSON 权威化）：md 转派生投影；外部 decision-append CLI 契约零变化；旧工具对新格式明确拒绝（非静默误读）。回退 = 反向转换方案+切换前快照（**仅备份不算可回滚**——须覆盖迁移后新增行的反向转换；切换授权前置三条件见 RISK-059）。
- **B-14**（FEAT-062/063·closure 取消/重开/接管路径新增）：纯新增能力面，无删除；外部 CLI 契约不变。

**如实披露**：① **REQ-092 blocked 面 Check 16/17 FAIL 维持**（EVD-476/473/423 3 FAIL = REQ-092 预期披露非豁免——外部依赖零豁免红线内维持，version-plan §3 条 5 F-8 显式登记）。② **EVD-1146 目标对齐字段写入失败残留**（FIX-388 首次 evidence 写入目标对齐仅 13 chars→Check 16 FAIL；EVD-1147 为合格重写。按 DEC-227 路线 a 否决先例〔补录=编造风险违反 P1〕**不补录历史行、不动+披露**；由 M-3 审查复核处置口径）。③ **static-pin bump-time 双信号**（FIX-361 设计语义）：0.87 窗口票写入的 then-future 0.88.0 字面量在本 bump 激活 4 WARN（test_archive.py:4586/4595〔FIX-384 fixture 世界〕、test_governance_store.py:493〔FIX-379 夹具行〕、test_verify_workflow.py:12742〔FIX-376 legacy REQ fixture〕）——全部为 scenario payload 零等值比较，逐行归因登记豁免（bump-time rows 先例同型）；test_verify_workflow.py 两行 0.87.0 self-dormant 豁免（L12614/12738 旧锚）按 version-plan L75 errata F-1+FIX-388 EVD 迁移指南**删除**；test_release_projection.py L30 FUTURE_TARGET 豁免行保留 dormant（0.85.0/0.86.0 bump-time rows 先例同型——FIX-361 设计语义「goes dormant afterwards」，实测零 WARN）。④ **FEAT-061 为阶段性交付**（C1 六层落地+真实 179 行演练 round_trip；存储分离其余表〔evidence-log 等〕与主文件大拆解出槽 0.89+——version-plan §6）。⑤ **FEAT-064 BLOCK 为机制交付**——真实翻转（基线登记→激活）留 Coordinator 按 DEC-239 裁定执行，本版不主张全族已 BLOCK 运行。⑥ **CHANGELOG 双位过渡**：根 `changelog.md` 为 triage-normalized 锁面交付物，`project/CHANGELOG.md` 为历史连续判据面——canonical 归属未裁决前双位同段维护，漂移风险由 M-3 复核。⑦ **no-overclaim 边界**：official approval / marketplace approval / universal runtime support / external first-session pilot success 均未被主张；非 Windows 平台未验证，本版验收全部在仓库内完成；RISK-036 继续打开，do not claim 1.0.0 production-ready；RISK-036/039/046 窗裁决 2026-09-30 到期即裁决（F-13 口径），RISK-050（10-31）维持打开。

**Breaking changes：无**（`skills/software-project-governance/core/VERSIONING.md` L11 口径：无 MUST 规则删除/重命名、无外部 CLI 契约变更〔decision-append 契约不变〕、无 governance 文件字段格式变更；B-12 为 DEC-224 双约束内的执法硬化升级〔FEAT-060 持久状态机+B-11 三面留痕为前置基座，非判定语义弱化——BLOCK 姿态即 0.86.0 DEC-224 登记方向的兑现〕；B-13 旧工具明确拒绝非静默误读；B-14 纯新增）。**MINOR bump 依据**：version-plan-0.88.0（M-0 双半面 APPROVED_WITH_NOTES/0×2 终态）——载荷 = write-guard WARN→BLOCK 分族激活（执法硬化）+ decision-log 存储分离首表（新增受治理能力面）+ closure 路径新增 + 回合心跳；非纯 bug fix。版本号未占用预留（0.87.0 已发布顺延 +1；无 0.88.x tag/预留冲突；1.0.0 预留位未触碰）。

版本投影 0.87.0 -> 0.88.0：由 M-1 统一执行（FEAT-059 先例形态）——SKILL frontmatter 权威锚先 bump（0.87.0→0.88.0），`release-projection --write` 单次写入 28 个 registry 投影面一次收敛（written=17+幂等镜像；check 模式 28/28 PASS 零 issue、declared_legacy_snapshots 10 pass）——零回滚震荡延续；双根 entry bootstrap（repo-root + e2e-fixture，AGENTS.md/CLAUDE.md `@bootstrap-version`）经 `sync_entry_projection --write` 再生（双根 4 文件 PASS）；手工钉 `verify_workflow.py` `REQUIRED_SNIPPETS` 六个版本锚与 JSON 声明面一致；static-pin 账本消解（披露③——删 2 self-dormant+登记 4 bump-time+保留 1 dormant FUTURE_TARGET）。`.governance/plan-tracker.md` `工作流版本` 随发布收口由 Coordinator 更新（过渡态 WARN 如实呈现——本版 verify 唯一预期 WARN）。

**发布时点**：本条目日期取 M-1 候选落库时点（2026-09-25 +0800）；若 M-5 transition/tag 的 taggerdate 与之不同，按 FIX-349 口径（**taggerdate 权威**）勘误对齐，不预填未生成的 tag 事实。

**Commit 区间（v0.87.0〔peel `602f8f3`〕..M-1 tip）**：git rev-list 实测 29 commits（M-1 候选落库时点，新→旧）——`3fb42c0` FIX-385 / `d7b9add` FEAT-044 / `d68355f` FEAT-063 / `467fb55` FEAT-045 / `6360ab1` FIX-384 / `14797be` FEAT-062 / `a8afcbf` FEAT-064 / `61618a5` FEAT-061 / `0ff12f3` FIX-383 / `c515776` FEAT-060 / `ce93eb3` FIX-382 / `b03a0b4` FIX-381 / `c349f8e` FIX-380 / `b7df86c` FIX-379 / `cdc3a0a` FIX-389 闭环 / `b3577c8` FIX-388 / `9df2381` FIX-389 / `0840876` FIX-387 / `17e5663` FIX-377 / `d6dd300` FIX-386 / `3d31c49` FIX-376 / `04b7a42` FIX-375 / `0233f49` REL-086 M-0 收口 / `7d6ff6a` REL-086 M-0 追加 / `266c32b` REL-086 M-0 / `6845756` FIX-374 / `44cb534` FIX-378 / `3c3218d` FIX-373 / `fc69196` REL-084 M-8（前版收尾）；区间终点随本段所在 M-1 候选 commit 落库后延伸。
