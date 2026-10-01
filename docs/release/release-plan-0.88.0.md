# Release Plan — 0.88.0（REL-086 M-1R / REL-088）

> **任务**: REL-088（P1；TRIAGE-REL-088 机录 2026-09-25；DEC-229 预授权链——M-1 bump 交付后 M-1R）· **日期**: 2026-09-25 · **性质**: M-1R 发布材料面（四件套：release plan/checklist/rollback/feature-flags）——非发布执行；M-2 门禁实测回填位已预留（见 checklist 四重点席）
> **裁决权边界**: 版本 go/no-go 与 tag/transition/push 由 Coordinator 执行（DEC-229 预授权承载——用户 2026-09-23「把已经登记的任务一次性推进闭环，我授权 Coordinator 按照推荐进行推进，授权发布版本承载修改。过程中的决策多和『架构与疑难问题顾问』进行讨论。」；预授权**不免除** M-2 门禁实测与 M-3 双半面审查）；本文件由 Governance Developer Agent 起草，供 Release Reviewer / M-3 审查链消费
> **写入边界**: 仅本四件套（TRIAGE-REL-088 files 锁定面）；不触 `.governance/` 真实治理数据、不修改产品代码、不改 CHANGELOG（REL-087 M-1 已交付双位段——本票零触碰）、不执行 tag/push/transition；`core/releases/0.88.0.json`（candidate manifest）**不在本票锁面**——由 Coordinator M-5 提交批补齐（本票如实披露，见 checklist 披露①）

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项：

- **No official approval claim**：official approval 未被授予、未被主张；0.88.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.88.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版全部验收在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）类口径下完成——隔离验收不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；do not claim 1.0.0 production-ready。
- **B-12/B-13 未激活面不越权主张**：FEAT-064 出厂全 WARN（真实翻转经 `--activate-block` 由 Coordinator 发布窗裁决——DEC-239②）⇒ 本版不主张全族已 BLOCK 运行；FEAT-061 缺省 `MD_ACTIVE` 零足迹（真实切换经授权票另行执行——RISK-059/DEC-238④）⇒ 本版不主张 decision-log JSON 权威已生效（CHANGELOG 0.88.0 段披露④⑤同口径）。
- **发布 tip 未生成前不预先编造**：`<发布 tip>`（M-5 transition 提交）与 tag 事实本四件套不预填——hash 一律由 M-5 生成后回填（FIX-349 口径：taggerdate 权威）。
- **M-2 数值不预填**：本票为 M-1R 草案，M-2 门禁实测尚未执行——checklist 门禁表全部为回填位预留（重点四席：Check 10 修复验证 / Check 16-17 披露 / Check 31 修复验证 / archguard 棘轮席），实测前不写任何通过性数值。

## 版本号与授权链

| 项 | 值 |
|---|---|
| 版本号 | **0.88.0**（MINOR；0.87.0 → 0.88.0 不跳号、无预留占用——0.87.0 已发布顺延 +1；无 0.88.x tag/预留冲突；1.0.0 预留位未触碰——CHANGELOG 0.88.0 段 semver 论证同口径） |
| 发布任务 | **REL-086（M-0 规划）/ REL-087（M-1 bump）/ REL-088（M-1R 本票）**——version-plan-0.88.0 双半面 GO（Design R0 NEEDS_CHANGE/4→R1 APPROVED_WITH_NOTES/0；Release R0 NEEDS_CHANGE/3→R2 APPROVED_WITH_NOTES/0——F-1~F-13 全闭环） |
| 授权链 | **DEC-229（0.88.0 标准链预授权 + 架构协作协议）** → 窗口内共 **11 决策**（DEC-229~239：DEC-230/231 FIX-375 退出码透传口径+缺陷落点更正 / DEC-232 FIX-376 豁免判据窄口径维持 / DEC-233 FIX-379 id 词表单一来源 / DEC-234 FIX-381 backport 政策裁定 / DEC-235 FIX-382 9-cell 取舍 / DEC-236 FEAT-060 三条口径 / DEC-237 FEAT-061 前置复核有条件不通过（P0×5） / DEC-238 FEAT-061 阶段性交付口径 / DEC-239 FEAT-064 五族执法裁定） |
| MINOR 依据 | `core/VERSIONING.md` L12「新增 B/C 级自动化能力」——载荷 = write-guard 分族 BLOCK 执法（B-12）+ decision-log 存储分离首表（B-13 新增受治理能力面）+ closure 取消/重开/接管路径（B-14）+ subagent 回合心跳；非纯 bug fix（L38 PATCH 不适用）；Breaking changes = **无**（L11 逐项核对不成立：B-12 为 DEC-224 双约束内执法硬化升级非判定语义弱化；B-13 外部 decision-append CLI 契约零变化、旧工具明确拒绝非静默误读；B-14 纯新增无删除面——CHANGELOG 0.88.0 段同口径） |
| Single-Threaded Owner | Coordinator（发布决策与 `.governance/` 写回）；Release 面产出物由角色 agent 执行，Release Reviewer 独立审查 |
| 用户获得方式 | `/plugin update`（或 `git pull` + reload）——版本号与 28 投影面 bump 保证 marketplace 新鲜度比对生效；升级说明 MUST 携带 B-12/B-13/B-14 行为变更（CHANGELOG 0.88.0 段行为变更节原文口径） |

## 发布范围

### 载荷构成（24 票五阶段 + M-0/M-1——REL-086 / REL-087 / DEC-229~239）

> git 窗口实测（2026-09-25）：**0.88.0 窗口 = `602f8f3..<发布 tip>`**（`602f8f3` = `v0.87.0` tag peel = REL-084 M-5 transition 提交，tag taggerdate 2026-09-21 14:02:27 +0800 实测——FIX-349 口径 taggerdate 权威）；`602f8f3..HEAD`（HEAD = `3fb42c0` FIX-385，2026-09-25 13:34:42 +0800）实测 **29 提交**（`git rev-list --count` 与 `git describe`（v0.87.0-29-g3fb42c0）双实测交叉印证）；REL-087 M-1 bump 为工作树交付待提交——落库后区间随发布批延伸。**24 票载荷与 CHANGELOG 0.88.0 段同源**（阶段 A 14 票〔含 0.87 出槽先落 3 票 + 调查票派生 3 票〕→ B 2 票 → C 1 票 → D 1 票 → E 6 票）。

| 批 | 任务 | 关键交付 | 提交 | 证据 |
|---|---|---|---|---|
| **前版收尾** | REL-084 M-8 | 0.87.0 发布收口（checklist M-链全勾 + M-6 复跑 + 热事实源三面回填 + 归档 integrity PASS）——属 0.87.0 收尾，本版窗口首位提交 | `fc69196` | EVD-1132/1133 |
| **阶段 A「契约与卫生」** | FIX-373 | 共享切分器 quote 分支补 not in_code_span 守卫——EVD-248 形状 code-span 内引号折叠误报消解（TDD 红 3F→绿 6/6；消费方指定套件 120 用例 0 失败；0.87 出槽票） | `3c3218d` | EVD-1134/1135；REVIEW-FIX-373-CODE-R0 APPROVED_WITH_NOTES/0 |
| | FIX-378 | e2e legacy 快照副本切分器守卫同步（FIX-373 F-1 承接；副本 git 忽略——本 commit 仅审查报告面；FIX-381 制度化首条台账） | `44cb534` | EVD-1136/1137；REVIEW-FIX-378-CODE-R0 APPROVED_WITH_NOTES/0 |
| | FIX-374 | format check 9-cell 豁免与截断 LIVE 行启发式消歧（cells[6] 日期形状判据 `_EVIDENCE_DATE_SHAPE_RE`——fail-blind 消除；豁免面形式化零弱化 S_new⊂S_old） | `6845756` | EVD-1138/1139（1139=完成必推荐分析快照——REVIEW-REL-088-R0 P2-1 勘正）；REVIEW-FIX-374-CODE-R0 APPROVED_WITH_NOTES/0 |
| | FIX-375 | writer 族三边缘收口：①引擎分发返回码透传（exit 0 假绿→exit 2——DEC-230/231）②畸形 --operation-id 结构化 schema_violation ③locks-release 三恢复腿 released_files 审计一致（pre-read 移入 _TargetLock 堵并发） | `04b7a42` | EVD-1140/1141；REVIEW-FIX-375 R0 APPROVED_WITH_NOTES/0→R1 APPROVED/0 |
| | FIX-376 | FIX-371 遗留候选合并处置——F-3 状态 cell 自右向左扫描（豁免面零变化=定理+活体双证：130 行全等/diff=0——DEC-232 窄口径）+F-4~F-7 | `3d31c49` | EVD-1142；REVIEW-FIX-376-R0 APPROVED_WITH_NOTES/0 |
| | FIX-386 | 0.87 遗留小项包：AUDIT-152 账本写回（clock_window_sensitive 8→9）+ADR-011/012 勘误注记（300,000→指向 361,923 公式）+FIX-370 F-2 验证（RISK-046 缓解列扩展） | `d6dd300` | EVD-1143；R0 NEEDS_CHANGE/1→R1 APPROVED/0 |
| | FIX-377 | FACTS_PRINT_TOTAL 1306→1316 +10 漂移归属 bisect（10/10 全归 `a6d3bfb` FIX-371 豁免披露输出）+28+2 失败四类归类+修复候选 triage（FIX-387/388/389 机录入账） | `17e5663` | EVD-1144；REVIEW-FIX-377-R0 APPROVED_WITH_NOTES/0 |
| | FIX-387 | 套件内全局态污染修复（P1 插队票）——FIX-375 进程内 main() 全局重绑泄漏（12 全局量 setUp/tearDown 完整重绑面）+HostRootRebindCanaryTests 防回归 canary（负面对照 13/13 漂移检出） | `0840876` | EVD-1145；REVIEW-FIX-387-R0 APPROVED/0 |
| | FIX-389 | LRC 文档面清账——REL-086-R2 五处 ragged row 修复+FIX-376-R0 L42 断言面改引用（两文档使真实树扫描 fail-closed 消解；闭环审查另落 `cdc3a0a`） | `9df2381`+`cdc3a0a` | EVD-1148；REVIEW-FIX-389-R0 APPROVED_WITH_NOTES/0 |
| | FIX-388 | static-pin 账本重审计——12375→12550 重锚（FIX-373 插入漂移——rot-guard 活体实证）+12674 补登（FIX-376 出生未豁免）+触发源轮换登记；EVD-1146 为不合格首写残留（EVD-1147 合格重写——披露面见 checklist 专席②） | `b3577c8` | EVD-1146/1147；REVIEW-FIX-388-R0 APPROVED_WITH_NOTES/0 |
| | FIX-379 | 量测边缘观察四项打包：journal detail 透传根因修复+governance id family 词表单一来源化（DEC-233）+conflict 退出码 epilog 明示+pre-probe 时序语义注记 | `b7df86c` | EVD-1149；REVIEW-FIX-379-R0 APPROVED_WITH_NOTES/0 |
| | FIX-380 | P3 杂项包：_format_issues 三副本提取模块级单源（7 调用点迁移零行为差）+fixture-engine reason 补 backport 溯源注记+e2e 副本钉归类不适用（四理由） | `c349f8e` | EVD-1150；REVIEW-FIX-380-R0 APPROVED_WITH_NOTES/0 |
| | FIX-381 | 切分器 backport 政策制度化（⑨定案——DEC-234）：五制度件落 legacy_snapshot_backport_policy 机读块+守卫精化（policy/台账空洞红+stale-ledger 机检红）+重放 9/9 实跑 | `b03a0b4` | EVD-1151；REVIEW-FIX-381-R0 APPROVED_WITH_NOTES/0 |
| | FIX-382 | 9-cell 消歧组合判据扩展（A 阶段收官）：11 项形态决策表（R4/R5 落地 c7 日期机证；R1/R2/R3 显式不修+披露——DEC-235）+静默集不变量（30 输入穷举差分 S_new=S_old） | `ce93eb3` | EVD-1152；REVIEW-FIX-382-R0 APPROVED_WITH_NOTES/0 |
| **M-0 规划** | REL-086 | version-plan-0.88.0 双半面双审 GO（Design R0→R1 / Release R0→R1→R2 全 APPROVED_WITH_NOTES/0——F-1~F-13 闭环）+arch 顾问协作（gpt-6-astra 两失败一成功——成功轮意见全量消化：批次重排/⑨政策化/guard 持久状态机/存储读适配先行/取消纵切先行/⑩拆票）+A4 自依赖环数据勘正（M1.2 非票通道）；roadmap 0.88.0 行 | `266c32b`/`7d6ff6a`/`0233f49` | EVD-1162；**M-0 GO** |
| **阶段 B「恢复与执法基础」** | FEAT-060 | write-guard 违规持久状态机+hook 消费权台账（811 行实体模块：12 字段违规记录+三态转移〔open/consumed/superseded〕+消费权闭集 v1=guard CLI 单消费者+ops 可恢复消费事务 journal 三段 resume fail-closed；DEC-236 口径三条；活体首捕 born-live WV-62097f→补凭证→守卫自动消费闭环）——WARN 姿态字节零变化 | `c515776` | EVD-1153；REVIEW-FEAT-060-R0 APPROVED_WITH_NOTES/0（7/7 独立复验+字节恒等双验） |
| | FIX-383 | B-7c 发版管线自举：release-window-bootstrap 内置链（--check-only 前探针 reconcile-vs-execute）+write-guard-bootstrap 子命令（五检查只读世界判定+converge 守卫工件恢复治理零写入）+三类中间态恢复映射+双故障点 kill→resume 零人工修复 | `0ff12f3` | EVD-1154；REVIEW-FIX-383-R0 APPROVED_WITH_NOTES/0 |
| **阶段 C「单点存储切换」** | FEAT-061 | decision-log 存储分离首表（**B-13；本版最高风险票**）六层落地：权威状态机（MD_ACTIVE→CUTOVER_FROZEN→JSON_ACTIVE→ROLLBACK_FROZEN——闭表+epoch fencing 端到端+唯一线性化点）/双后端写入路由（MD 字节零变化+JSON 同 CAS/幂等）/迁移编排（freeze 四闭合+activate 三段 journal+rollback 对称复检）/独立校验器（禁导入自签拒绝+旧解析器逐字符镜像+三类完整性证明+负向注入 7 例）；DEC-237 前置复核（有条件不通过——P0×5 补齐后派发）+DEC-238 口径；真实 179 行演练 round_trip（独立性三规则活体实证）；**切换授权前置三条件入 RISK-059（本版机制交付未激活）** | `61618a5` | EVD-1155；REVIEW-FEAT-061 R0 NEEDS_CHANGE/2（P0-F1 竞窗数据丢失+P0-F2 砖化——均活体复现）→修复→R1 APPROVED_WITH_NOTES/0 |
| **阶段 D「执法激活」** | FEAT-064 | write-guard 分族 BLOCK 激活（**B-12；机制交付，真实翻转留 Coordinator**）：五族裁定（evidence/review/decision/ops_ledger 四族 BLOCK+task_status WARN 后置——DEC-239①）+出厂全 WARN 姿态（字节恒等探针实证）+BLOCK 写后执法+R2 逐面钳制+break-glass 四件套（五限定+use 审计不可静默）+FEAT-060 遗留三件（hook_identity/A-B-A 会话累计/SESSION_ID 接线）+FIX-383 registry 收口（96→97 键+contract-matrix 指令化再生） | `a8afcbf` | EVD-1156；REVIEW-FEAT-064-R0 APPROVED_WITH_NOTES/0（八焦点全符合+双版本探针） |
| **阶段 E「能力与剩余」** | FEAT-062 | closure 取消纵切（**B-14 半面**——arch Q5）：限定入口+CAS 单终态（run lock 线性化+竞争恰一终态）+DEC 经写入器登记+仅释放自有锁+对账（世界是真相）；中断恢复=终态先行+双腿幂等重放（真锁竞争注入 92.86s） | `14797be` | EVD-1157；R0 APPROVED_WITH_NOTES/0→F-1~F-3 修→R1 APPROVED/0 |
| | FIX-384 | B-7a 归档 index-rebuild：rebuild_index 闭环（快照→确定性重建→integrity 校验）+损伤分类+errors=replace 容错（U+FFFD 四类探针零伪造）+CLI | `6360ab1` | EVD-1158；R0 NEEDS_CHANGE/1→R1 APPROVED_WITH_NOTES/0 |
| | FEAT-045 | 串行链路并行段识别审计闭环（纯审计票零源码修改）：三段清单+三处过时披露+四点独立互证+DEC-220 勘正双落 | `467fb55` | EVD-1159；REVIEW-FEAT-045-R0 APPROVED_WITH_NOTES/0 |
| | FEAT-063 | closure 重开+异常接管（**B-14 半面**）：重开 lineage（closure_reopened 事件+单一后继+零擦除实证）+执行代际 fencing（sidecar+写端三面校验+旧代际零效果+closure_fenced 幂等）+TOCTOU 修复（锁内 re-read 三形态拒绝——R0 P0-1 活体 7/7→R1 三形态实测） | `d68355f` | EVD-1160；R0 NEEDS_CHANGE/1→R1 APPROVED_WITH_NOTES/0 |
| | FEAT-044 | subagent 回合预算与收尾心跳：resolve_round_budget 三层参数化 fail-closed+heartbeat_should_fire/payload（N=3 无产物上报 stop_proof=False 全链钉死）+interrupt_recovery_payload 恢复产品化+compute_stall_report 等待税遥测+33 新测试 | `d7b9add` | EVD-1161；REVIEW-FEAT-044-R0 APPROVED_WITH_NOTES/0（9 MUST 全过+17 独立探针） |
| | FIX-385 | B-7b 大表断点续迁（FEAT-061 衔接）：journal 相位机+批游标+单线性化 commit（同路径锁互斥）+resume 世界判定（三 crash 窗可续+终态等价+守恒）+DecisionStoreAuthorityConflict fail-closed+F-1 TOCTOU 修复（投影重写临界区化+in-lock 重判零写入） | `3fb42c0` | EVD-1163；R0 APPROVED_WITH_NOTES/0→F-1 修复→R1 APPROVED_WITH_NOTES/0 |
| **M-1 bump** | REL-087 | 0.87.0→0.88.0 全仓（SKILL.md frontmatter 权威锚+REQUIRED_SNIPPETS 六锚+投影 28 面+双根 entry sync——FEAT-059 先例形态，`release-projection --write` 单次收敛零回滚）+CHANGELOG 0.88.0 段双位（`project/CHANGELOG.md` + 根 `changelog.md`——披露⑥）+static-pin 消解（删 2 self-dormant per F-1 errata+登记 4 bump-time+保留 1 dormant FUTURE_TARGET） | **工作树交付——candidate commit 随 M-1R 提交批落库**（如实注记，区间终点随其延伸） | TRIAGE-REL-087；审查中（check-version-consistency/verify/static-pin 套件全过——plan-tracker REL-087 行） |
| **M-1R 发布面（本票）** | REL-088 | **四件套**（plan/checklist/rollback/feature-flags——本票 expected-new 锁面）+ M-2 门禁实测回填位预留（四重点席） | 本票（Coordinator 提交后为 candidate commit） | 待提交 |
| **⑥ 治理面** | REL-086 链 | **11 决策**（DEC-229~239）+ **30 EVD**（EVD-1134~1163——交付审查链机器写入 governance-store 延续；EVD-1132/1133 为 0.87.0 M-8 收口属前版）+ 审查报告留档（review-FIX-375~389 / review-FEAT-060~064 / review-REL-086 系列——docs/reviews/）；审查链含 NEEDS_CHANGE→R1/R2 转化五票（FIX-375/386/384/063/385）+ FEAT-061 P0×2 活体复现修复，全部 0 unresolved blockers 终态 | — | — |

### 本版不发布什么（显式排除——Amazon 实践）

1. **write-guard task_status 族 BLOCK**（DEC-239① WARN 后置——合法手工面 0.89+ 机录化后再 BLOCK；四族 BLOCK 亦为机制交付未激活，见保守边界）；
2. **存储分离其余表**（evidence-log 等——FEAT-061 首表模式验证后 0.89+ 推广，version-plan §6）+ 主文件大拆解（arch 告诫迁移期不做顺便重构）；
3. **B-13 真实权威切换执行**（切换授权票前置 = DEC-238④ 三缺口〔RISK-059 承载〕+ DEC-239⑦ F-5①③ 组合测试归票——闭环+证明包审查后另行授权；本版零足迹缺省态）；
4. **B-12 真实翻转执行**（出厂全 WARN；翻转经 `--activate-block` 由 Coordinator 发布窗裁决——DEC-239②，与 FEAT-061 切换授权同型防 session 自锁）；
5. **量测边缘观察后续面**（本版 FIX-379 已清偿 0.86.0 移交四项；后续面出槽 0.89+）；
6. **任何 RISK 的关闭声明**（RISK-036/039/046 窗裁决 2026-09-30 到期即裁决属 risk-log 处置义务非本版载荷承诺——不迟于 M-4，F-13；RISK-050（10-31）维持打开；本版无 RISK 关闭承诺）。

## 回滚区间锚定（与 rollback-plan-0.88.0 §区间锚定同锚同源）

**本版回滚区间（triage 锚定）= `602f8f3..<发布 tip>`**（回退点 = `v0.87.0` tag；`602f8f3` = tag peel = REL-084 M-5 transition 提交；tag object `2e5f715`，taggerdate 2026-09-21 14:02:27 +0800 实测——FIX-349 口径 taggerdate 权威）：

- **论证①（下界 = `602f8f3`，本版无双轨分歧）**：git 区间语义 `X..Y` 排除下界自身。0.88.0 与 0.86.0 期不同——24 票行为载荷（A14+B2+C1+D1+E6）+ M-0（REL-086）+ M-1 bump（REL-087）**全部落在 `602f8f3` 之后**（无 0.85.0 树内搭车批的 DEC-222 归属面），triage 锚定同时就是完整行为回退区间：撤销即回到 `v0.87.0` 行为（peel `602f8f3`）。单轨，M-3 审查只需复核单轨锚定与窗口计数。
- **论证②（终点必须是 `<发布 tip>`，不得是候选打包提交）**：0.81.0 先例 **F-04**——post-candidate 提交会修改区间内新增的 release 文档导致 revert 冲突（0.84.0 演练 P-12 反向实证 exit 1/CONFLICT）。终点 MUST 是 M-5 transition 提交（hash 由 M-5 生成后回填，本文件不预编造）。
- **窗口计数如实登记**：`git rev-list --count 602f8f3..HEAD` = **29**（2026-09-25 实测，HEAD = `3fb42c0` FIX-385；`git describe` = v0.87.0-29-g3fb42c0 交叉印证；29 含窗口首位 `fc69196` REL-084 M-8 前版收尾）；REL-087 M-1 bump 工作树交付待提交——落库后区间延伸；区间计数不写死——M-5 现场以 `git rev-list --count 602f8f3..<发布 tip>` 取值记入 EVD。

## M-链状态（截至本文件落盘 2026-09-25——映射 version-plan-0.88.0 §3b）

| 里程碑 | 状态 | 事实 |
|---|---|---|
| M-0 规划确认 | ✅ 完成（GO） | REL-086（`266c32b`/`7d6ff6a`/`0233f49`）：version-plan-0.88.0 双半面 Design R1 + Release R2 全 APPROVED_WITH_NOTES/0（F-1~F-13 全闭环——Check 10/25/26/31 全 PASS 实证链 R0 BLOCKED→R2 PASS）；DEC-229 预授权生效；roadmap 0.88.0 行 |
| 阶段 A~E 24 票载荷 | ✅ 完成 | A14（`3c3218d`..`ce93eb3`）+ B2（`c515776`/`0ff12f3`）+ C1（`61618a5`）+ D1（`a8afcbf`）+ E6（`14797be`..`3fb42c0`）——EVD-1134~1163；0 unresolved blockers 终态 |
| M-1 版本 bump | ✅ 交付（candidate commit 待落库） | REL-087：全仓 bump 28 投影面 + CHANGELOG 0.88.0 段双位 + static-pin 消解——工作树交付（`release-projection --write` 单次收敛零回滚，check 模式 28/28 PASS——CHANGELOG 版本投影段）；plan-tracker REL-087 行「审查中」 |
| **M-1R 发布面（本票）** | 🔄 本票执行 | REL-088：四件套 + M-2 实测回填位预留（四重点席） |
| M-2 门禁实测 | ⏳ 回填位预留 | version-plan §3 全条目 + evidence-log 归档后 28s 复测（F-6）——checklist #1~#19 回填位；**组合测试义务四条**（§3 条 2——F-5 兑现）+ **独立证明包门**（§3 条 3）+ **全量 pytest M-2 一次预算**（§3 条 1——M-3 改可执行代码须退回验证） |
| M-3 双半面审查 | ⏳ 待 Coordinator 派发 | 产品代码半面（Code Reviewer 链）+ 发布半面（Release Reviewer 链）；**按阶段边界分节审查**（version-plan §1 假绿对冲）；review-record 机录；复审必达；含 EVD-1146 处置口径复核（CHANGELOG 披露②——M-3 审查复核义务） |
| M-4 修复窗 | ⏳ | M-2/M-3 FAIL 修复窗；**RISK-036/039/046 窗裁决 2026-09-30 到期即裁决（不迟于 M-4——F-13；若 M-4 晚于 09-30，Check 8 自 10-01 转 FAIL）**；go/no-go 由 Coordinator 呈现裁决（DEC-229 预授权形态，门禁不予放弃） |
| M-5 candidate | ⏳ Coordinator 面 | `core/releases/0.88.0.json` candidate manifest 创建+四件套同批提交 → 复跑 `release-ledger --no-remote`（期望 NATIVE_CANDIDATE PASS）→ transition candidate→released（单父 manifest-only + integrity——`602f8f3` 先例形态） |
| M-6 预推校验 | ⏳ M-5 后 push 前 | `check-release --lineage-mode released --release-commit <commit>` + `release-ledger --remote` 全绿方进 M-7（0.87.0 期 EVD-1133 同流程） |
| M-7 tag+push | ⏳ Coordinator 面 | annotated tag `v0.88.0`（peel = transition 提交；taggerdate 权威——FIX-349）+ master + tag 原子推送（远端 SHA 精确一致） |
| M-8 归档 + 收尾 | ⏳ Coordinator 面 | `archive.py migrate --auto --dry-run` → 迁移 → `check-archive-integrity` PASS；**Check 28s 复测消解有效性确认**（F-6——现值 1,620KB，0.87 M-8 归档后仍 1620KB 先例警示）；plan-tracker `工作流版本` → 0.88.0（当前 0.87.0 过渡态 WARN——本版 verify 唯一预期 WARN）；**roadmap 0.88.0 行回填义务内建**（FIX-367 复发预防）+ REL-086 任务行终态回填义务 |

## 发布窗口

| 时点 | 内容 |
|---|---|
| 2026-09-21 14:02 | v0.87.0 发布（tag taggerdate 14:02:27 +0800 权威，peel `602f8f3`） |
| 2026-09-23 | DEC-229 预授权 + arch 顾问协作（两失败一成功）；FIX-373/378/374 先落（0.87 出槽票） |
| 2026-09-24 | version-plan-0.88.0 v2 修订（Design R1 APPROVED_WITH_NOTES/0）落库（`266c32b`） |
| 2026-09-25 | M-0 收口（`0233f49` Release R2 GO）→ 五阶段 24 票批次交付（A→E，`04b7a42`..`3fb42c0`）→ **M-1 bump REL-087 工作树交付**（CHANGELOG 发布时点段口径 2026-09-25 +0800；M-5 tag 后按 FIX-349 口径以 taggerdate 勘误对齐） |
| 2026-09-25 | **M-1R（本票 REL-088）**：四件套 + M-2 回填位预留 → M-2 实测 → M-3 双审 → M-4 修复窗/go-no-go → M-5~M-7 另记（taggerdate 权威） |

## 门禁摘要（数值基线——本票为 M-1R 草案，M-2 实测前不预填）

| # | 门禁面 | 基线 / 姿态 | 依据 |
|---|---|---|---|
| 1 | LRC Check 31（预算不变版） | 上限 **361,923** 沿续（FIX-369 公式值，本版零改动）；M-0 期实测 305,604 余量 56,319（version-plan §3 条 4）；0.88 M-0 链 R0 BLOCKED→R2 PASS（FIX-389 ragged 清账）；M-2 复算期望 PASS 且如实记录当场 units——本版治理记录增量可观（24 票 TRIAGE/EVD/REVIEW 机录），若越线按 FIX-369 公式口径重定标（非豁免——version-plan §7） | FIX-389（`9df2381`）；M-2 回填位见 checklist 专席③ |
| 2 | Check 16/17 披露面 | **EVD-476/473/423 3 FAIL = REQ-092 预期披露非豁免**（外部依赖零豁免红线——version-plan §3 条 5 F-8 显式登记）+ **EVD-1146 superseded 残留**（FIX-388 不合格首写——EVD-1147 合格重写；不补录历史行不动+披露，DEC-227 路线 a 否决先例）；**新增行零豁免全严检**（DEC-227）维持 | checklist 专席②；M-2 如实回填当场计数 |
| 3 | 全量 pytest（M-2 一次预算） | arch 修正：M-2 一次预算非免检许可——M-3 修改可执行代码时原 M-2 证据不自动覆盖须退回验证评估；**组合测试义务四条**（guard 台账损坏×切换窗共存 / BLOCK 激活后迁移全走写入器 / 基线更新×投影失败恢复 / closure 取消期间 locks-release 与消费权并发） | version-plan §3 条 1~2；checklist #11/#12 |
| 4 | 独立证明包门 | FEAT-061 迁移/恢复证明（固定源 commit 摘要/冻结窗完整性双向摘要复核/独立性操作化三条/记录级比对/故障注入/回退演练含迁移后新增行/绑定发布提交）为 M-2 必查席 | version-plan §3 条 3；checklist #13 |
| 5 | 棘轮 archguard R1~R7 | **6F 存量 baseline regen 归发布窗**（M-2 sanctioned——FEAT-055 先例；FIX-377 归因链 + FEAT-044 archguard 6F 归因修正 HEAD pre-existing）；R5 期望 **97/97** frozen（FIX-383 registry 收口 96→97 键——DEC-239⑥） | checklist 专席④/#8 |
| 6 | 版本投影面 | source = 0.88.0；28 投影面（M-1 已实测单次收敛零回滚——check 模式 28/28 PASS）；M-2 check-only 复跑确认 | REL-087（CHANGELOG 版本投影段） |
| 7 | candidate ledger 两态 | 本票实测 `release-ledger --version 0.88.0 --no-remote` 预提交态预期 FAIL（manifest 锁面外未建——checklist 如实归类）；Coordinator M-5 提交后 MUST 复跑（期望 NATIVE_CANDIDATE PASS）→ M-6 `--remote` | ADR-010 / 0.87.0 #10 同流程 |
| 8 | Check 28s evidence-log 复测 | F-6：现值 1,620KB——M-8 归档后 28s 复测消解有效性在 M-2 复测确认（0.87 M-8 归档后仍 1620KB 先例警示） | version-plan §3b |

## 硬门槛自检（本任务）

| 门槛项 | 判定 | 依据 |
|---|---|---|
| 四件套成形、对照 0.87.0 四件套先例无缺面 | **PASS** | 结构逐节对照 `docs/release/{release-plan,release-checklist,rollback-plan,feature-flags}-0.87.0.md`；全表行管道符转义审查（FIX-365 ragged 教训——表 cell 内零裸管道符） |
| 回滚区间实测 | **PASS** | `git log --oneline 602f8f3..HEAD` + `git rev-list --count` = **29**；`git describe` v0.87.0-29-g3fb42c0 交叉印证；`602f8f3` = `git rev-parse v0.87.0^{}` 实测同一（taggerdate 2026-09-21 14:02:27 +0800） |
| 内容事实源引用准确 | **PASS** | 24 票 commit/EVD（EVD-1134~1163）逐项对照 git log 实测 + CHANGELOG 0.88.0 段（双位同段——REL-087 交付版）；B-12/B-13 姿态面取自 `write_guard_state.py`（POSTURE_CONFIG_FILE_NAME/管理 CLI）与 `decision_repository.py`（AUTHORITY_STATE_FILE/状态机）实读；回退命令面取自 `verify_workflow.py` L23908-23917 与 `decision_migration.py` argparse 实读 |
| check-manifest-consistency / check-cross-references | 见本票验证记录（四件套落盘后运行） | docs/release 四文件与 0.87.0 先例同形态（manifest 不逐文件登记 docs/ 面——实证见 checklist 验证记录） |
| 真实 `.governance/` 零写入 | **PASS** | 写入面 = 四件套（TRIAGE-REL-088 files 锁定）；不触治理数据、不改产品代码、CHANGELOG 不再改、tag·push·transition 不执行 |

---
*REL-088 M-1R 起草冻结（2026-09-25，Governance Developer Agent）。事实基线：29 提交窗口与 hash 取自 `git log`/`git rev-list`/`git describe`/`git rev-parse v0.87.0^{}`/`git for-each-ref refs/tags/v0.87.0` 实测（`602f8f3..3fb42c0` = 29；`v0.87.0` taggerdate 2026-09-21 14:02:27 +0800 = peel `602f8f3`）；24 票交付与 B-12/B-13/B-14、11 决策（DEC-229~239）、披露①~⑦口径取自 CHANGELOG 0.88.0 段（REL-087 交付版——project/CHANGELOG.md 与根 changelog.md 双位同段）；B-12 姿态面取自 `infra/write_guard_state.py` 实读（POSTURE_CONFIG_FILE_NAME L301/管理 CLI L1668-1699）+ `verify_workflow.py` L23908-23917 实读；B-13 权威状态面取自 `infra/decision_repository.py` 实读（AUTHORITY_STATE_FILE L131/状态机 L151-163）+ `infra/decision_migration.py` argparse 子命令面 L1009-1048 实读；LRC 305,604/组合测试四条/证明包门/F-6 取自 version-plan-0.88.0 §3/§3b 实读；DEC-238④/DEC-239 取自 `.governance/decision-log.md` 实读；RISK-059 取自 `.governance/risk-log.md` 实读；M-0 GO 取自 `0233f49` commit message 与 plan-tracker REL-086 行。未生成事实（发布 tip、tag、M-2 门禁数值、candidate manifest 提交、B-12 真实翻转、B-13 真实切换）一律标期义务/回填位，不预填。*
