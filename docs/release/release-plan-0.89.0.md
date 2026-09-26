# Release Plan — 0.89.0（REL-090 M-1R / REL-092）

> **任务**: REL-092（P1；TRIAGE-REL-092 机录 2026-09-26；DEC-245 预授权链——M-1 bump（REL-091 `b66bd25`）交付后 M-1R）· **日期**: 2026-09-26 · **性质**: M-1R 发布材料面（四件套：release plan/checklist/rollback/feature-flags）——非发布执行；M-2 门禁实测回填位已预留（见 checklist 全席面）
> **裁决权边界**: 版本 go/no-go 与 tag/transition/push 由 Coordinator 执行（DEC-245 执行与发布授权——M-1 启动→批次执行→M-2~M-8 全链推进；**M-4 go/no-go 前置 arch 顾问意见**——DEC-240 先例延续；预授权**不免除** M-2 门禁实测与 M-3 双半面审查；安全语义不因授权削减）；本文件由 Governance Developer Agent 起草，供 Release Reviewer / M-3 审查链消费
> **写入边界**: 仅本四件套（TRIAGE-REL-092 files 锁定面——expected-new 已登记）；不触 `.governance/` 真实治理数据、不修改产品代码、不改 CHANGELOG（REL-091 M-1 已交付 0.89.0 段**单 canonical=project/CHANGELOG.md**——DEC-242① 0.88 M-3 裁决直接继承，本票零触碰）、不执行 tag/push/transition；`skills/software-project-governance/core/releases/0.89.0.json`（candidate manifest）**不在本票锁面**——由 Coordinator M-5 提交批补齐（本票如实披露，见 checklist 披露①）

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项：

- **No official approval claim**：official approval 未被授予、未被主张；0.89.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.89.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版全部验收在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）类口径下完成——隔离验收不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；do not claim 1.0.0 production-ready。
- **无激活不越权主张**：本版**无新增功能激活**（DEC-246⑥ 措辞收紧口径——CHANGELOG 0.89.0 段行为变更节声明同源）：不主张任何 write-guard 族已 BLOCK 运行（B-12 出厂全 WARN 姿态不变——0.89 窗口无 `--activate-block` 执行）、不主张 decision-log JSON 权威已生效（B-13 缺省 `MD_ACTIVE` 零足迹——0.89 无真实切换）；载荷承载的**行为修正三面**（FEAT-065 gate 闭集替换 / FIX-391 零写拒绝面 / 判据收敛不放宽）为治理判据、恢复安全与锁生命周期行为修正，非新增功能激活（feature-flags-0.89.0 §5 同口径）。
- **发布 tip 未生成前不预先编造**：`<发布 tip>`（M-5 transition 提交）与 tag 事实本四件套不预填——hash 一律由 M-5 生成后回填（FIX-349 口径：taggerdate 权威）。
- **M-2 数值不预填**：本票为 M-1R 草案，M-2 门禁实测尚未执行——checklist 门禁表全部为回填位预留（重点席：census 对账席 / archguard 棘轮席 / Check 28s 前置归档席 / 18-18b live 复测席 / FEAT-065 双面演示席 / 组合②列补充席），实测前不写任何通过性数值。
- **census 身份集口径**：census 以**问题身份集合**验收（非数字——DEC-246③）；收窄形态 = REQ-092×n + EVD-1146×1（规划参考 ×6——version-plan §4.2/DEC-243 口径；n 以 M-2 当场 census 实测为准）；跳检/扩豁免/降级式收窄 = 阻断。

## 版本号与授权链

| 项 | 值 |
|---|---|
| 版本号 | **0.89.0**（MINOR；0.88.0 → 0.89.0 不跳号、无预留占用——0.88.0 已发布顺延 +1；无 0.89.x tag/预留冲突；1.0.0 预留位未触碰——CHANGELOG 0.89.0 段 semver 论证段同口径） |
| 发布任务 | **REL-090（M-0 规划）/ REL-091（M-1 bump）/ REL-092（M-1R 本票）**——version-plan-0.89.0 双半面 GO（Design R0 APPROVED_WITH_NOTES/0 + Release R0 APPROVED_WITH_NOTES/0，2026-09-25——EVD-1171） |
| 授权链 | **DEC-244（0.89.0 范围授权——必选六项 + B-12/B-13 五前置核验不激活 + FEAT-045 P-a；激活授权票不捆绑）→ DEC-245（执行与发布授权——M-1→M-8 全链推进 + arch 顾问决策点协议 + 安全语义不削减）** → 窗口内共 **5 决策**（DEC-244~248：DEC-246 链首 arch 顾问咨询 Conditional GO 八条采纳 / DEC-247 Check 30 V3 链内轮次判据 / DEC-248 FEAT-065 验收拆分——acquire TTL 拆出 FEAT-066） |
| MINOR 依据 | version-plan-0.89.0（M-0 双 GO 终态）——载荷 = **治理精度与健康面收口批**（解析判据收敛 / 检查器结构化 / 门禁自动化 / 锁腿真释放）；非纯 bug fix（PATCH 不适用）；Breaking changes = **无**（无 MUST 规则删除/重命名、无外部 CLI 契约变更、无 governance 文件字段格式变更；FIX-391/FEAT-065 新增拒绝面均属 fail-closed 门禁而非既有契约删除——自定义 lock_ttl_le spec 声明被拒见行为修正①；判据收敛不放宽——CHANGELOG 0.89.0 段同口径） |
| 行为变更面 | **无新增功能激活**（DEC-246⑥ 收紧措辞——含治理判据、恢复安全与锁生命周期**行为修正三面**，CHANGELOG 0.89.0 段行为修正节如实披露；B-x 新登记预期 = 无——M-3 按实际 diff 复核） |
| Single-Threaded Owner | Coordinator（发布决策与 `.governance/` 写回）；Release 面产出物由角色 agent 执行，Release Reviewer 独立审查 |
| 用户获得方式 | `/plugin update`（或 `git pull` + reload）——版本号与 28 投影面 bump 保证 marketplace 新鲜度比对生效；升级说明 MUST 携带行为修正三面（CHANGELOG 0.89.0 段行为修正节原文口径——无激活） |

## 发布范围

### 载荷构成（七票三批次 + M-0/M-1——REL-090 / REL-091 / DEC-244~248）

> git 窗口实测（2026-09-26）：**0.89.0 窗口 = `33d19b0..<发布 tip>`**（`33d19b0` = `v0.88.0` tag peel = REL-086 M-5 transition 提交，tag object `82905e6`，taggerdate 2026-09-25 20:08:32 +0800 实测——FIX-349 口径 taggerdate 权威）；`33d19b0..HEAD`（HEAD = `b66bd25` REL-091 M-1 bump，2026-09-26 20:31 +0800）实测 **12 提交**（`git rev-list --count` 与 `git describe`（v0.88.0-12-gb66bd25）双实测交叉印证）。**七票载荷与 CHANGELOG 0.89.0 段同源**（DEC-244 六票 + FIX-395 census 收窄承诺前置票——批次排布经 REVIEW-REL-091-RELEASE-R0 §3 实测确认与 DEC-246① 主序列一致）。

| 批 | 任务 | 关键交付 | 提交 | 证据 |
|---|---|---|---|---|
| **前版收尾（0.88.0 期）** | REL-086 M-6 修复批 | release-checklist L46 载荷表 #10 行勘正（M-5 回填误覆盖恢复）+ projection 再收敛——LRC ragged 消解 | `2dac7af` | EVD-1170（M-6~M-8 终账承载行） |
| | REL-086 M-8 收口批 | 0.88.0 发布闭环：plan-tracker 工作流版本 0.88.0（三面一致）+ checklist M 链全勾 + 归档 integrity PASS + ledger 本地/remote 双 PASS + tag v0.88.0 推远端 | `9347c11` | EVD-1170 |
| **M-0 规划** | REL-090 | version-plan-0.89.0 九节全（范围零扩缩）+ 双审 APPROVED_WITH_NOTES/0×2 + 收口落字批 v1.1（F-1 批次间三票共面串行 / F-2 §5 五前置核验回填〔③口径漂移 3≠11 如实登记〕/ F-3 §7 双锚勘正 / P2-1 CHANGELOG canonical 继承 / F-4 RISK-048 登记 / F-5F-6 M-2M-3 注记）+ 六票 triage 机录入账 + roadmap 0.89.0 行 | `76c86a9` | EVD-1171；**M-0 GO**（review-REL-090-DESIGN-R0 / review-REL-090-RELEASE-R0） |
| **批次一「状态面收口」** | FIX-393 | 任务状态词表收敛——task-priority / parse_current_active_tasks / archive 三解析器判据对齐写入器终态 committed（ops 台账权威状态源）；17 新测试；tpa 活体零误推荐/零误 blocked（DEC-246① 首发集成点退出条件兑现——终态/非终态/未知 token 不放宽、不绕过 FIX-390 证据检查） | `8a94d64` | EVD-1172；review-FIX-393-CODE-R0 APPROVED_WITH_NOTES/0 |
| | FIX-394 | 终态行文本刷新机制（task-row-update 落 token 刷新状态列进度后缀）+ 13 行存量一次性对齐（ Coordinator 凭证留痕——EVD-1174；运行时机制与 13 行数据对齐分开验收——DEC-246⑤）；28P+12 subtests | `3cb4048` | EVD-1173/1174；review-FIX-394-CODE-R0 APPROVED_WITH_NOTES/0 → R1 APPROVED/0 |
| **批次二「披露面消解——检查器族」** | FIX-390 | Check 18/18b 结构化状态判据（DEC-241 例外消解票——REL-089 条件②）：三态完成判据（writer-committed+锚 / ✅ legacy / 未知不猜）+ Check 18 basis 列回退读位解耦 + Check 18b DEC-168 机器凭证接纳；机制消解 fixture 面红绿实证（19F→18P）+ 豁免差分 drops=∅ expansion=17 逐行留档；**live 面 0.89.0 窗口未激活如实登记**（EVD-1176 勘正——M-2 窗口激活后复测席承载） | `def9508` | EVD-1175/1176；review-FIX-390-CODE-R0 APPROVED_WITH_NOTES/0 |
| | FIX-392 | Check 30 复合键判据（DEC-242③ 消解）：task+chain+round 链归属推导（证据行+镜像 report: 双通道）+ V3 链内轮次判定（DEC-247 落字）+ canonical 零漂移回退；census Check 30 面 30→25（V3×5 伪像消解、25 条真实缺陷逐行恒等）；熔断三守卫恒绿 | `65c8e4b` | EVD-1177；review-FIX-392-CODE-R0 APPROVED_WITH_NOTES/0 |
| | FIX-395 | Check 28c HotFactSource 终态判定对齐（FIX-393 同族第四消费方）：identity 复用 FIX-393 判据——0.88.0 roadmap 行 20 条伪 FAIL 簇消解（census 收窄承诺前置达成）；R0 NEEDS_CHANGE→R1 修复（static-pin 契约面——EVD-1179 勘正入账） | `7795f59` | EVD-1178/1179；review-FIX-395-CODE-R0 NEEDS_CHANGE → R1 APPROVED_WITH_NOTES |
| **批次三「closure 链健康面」** | FIX-391 | closure journal 版本感知读取器（REL-089 条件③消解 + DEC-241 附带裁定机器门禁落地）：未知事件/出窗 schema 零写拒绝（四写入口全覆盖）+ seq 防占用 backstop + 0.87 兼容矩阵五格红绿；红相 13F→绿相 112P | `c9b7415` | EVD-1180；review-FIX-391-CODE-R0 APPROVED_WITH_NOTES/0 |
| | FEAT-065 | **标准链锁腿真释放（DEC-248 拆分后链内面）**：shrink-locks→release-locks 接线（cancel 腿同款）+ gate 闭集 lock_ttl_le→task_locks_released（任务索引+文件锁归属双面 fail-closed）+ 三处过时披露勘正 + lock_ttl 死输入移除；八项红绿测试（104P→112P）；四红线保持（释放前同文件互斥 / 只释放本任务锁 / 释放后不改受锁文件 / 提交串行隔离）；**acquire TTL 判定面拆出 FEAT-066（0.90 候选池——DEC-248②，如实注记：本票不得按 acquire 面宣称完成——DEC-248④）** | `ab7a8e1`+`b950fef` | EVD-1181；review-FEAT-065-CODE-R0 APPROVED_WITH_NOTES/0 |
| **M-1 bump** | REL-091 | 0.88.0→0.89.0 全仓（REL-087 先例形态，24 文件面）：SKILL frontmatter 权威锚 + REQUIRED_SNIPPETS 六锚 + 投影 28 面 CLI 再生（written=17+幂等镜像）+ 双根 entry sync + CHANGELOG 0.89.0 段（**单 canonical**——DEC-242① 继承）+ static-pin 账本消解（删 4 self-dormant + 登记 9 bump-time + 保留 2 dormant FUTURE_TARGET） | `b66bd25` | EVD-1182；REVIEW-REL-091-RELEASE-R0 APPROVED_WITH_NOTES/0（**P2-1：census 49→51 差值归因移交 M-2 对账席**——checklist 专席①承载） |
| **M-1R 发布面（本票）** | REL-092 | **四件套**（plan/checklist/rollback/feature-flags——本票 expected-new 锁面）+ M-2 门禁实测回填位预留（重点席六席） | 本票（Coordinator 提交后为 candidate commit） | 待提交 |
| **⑥ 治理面** | REL-090 链 | **5 决策**（DEC-244~248）+ **11 EVD 载荷面**（EVD-1171~1181）+ EVD-1182（M-1 版本面）+ 审查报告留档 11 份（review-REL-090-DESIGN-R0/RELEASE-R0、review-FIX-390/391/392/393-CODE-R0、review-FIX-394-CODE-R0/R1、review-FIX-395-CODE-R0/R1、review-FEAT-065-CODE-R0、review-REL-091-RELEASE-R0——docs/reviews/）；**例外消解闭环三票**：DEC-241 例外×4（FIX-390）/ DEC-242③ V3×5（FIX-392）/ REL-089 条件③（FIX-391）按各自消解条件在案闭环 | — | — |

### 本版不发布什么（显式排除——Amazon 实践）

1. **B-12 真实翻转 / B-13 真实切换**（激活授权票独立决策、不捆绑本版——DEC-244；五前置核验只核验不激活，M-0 已回填——version-plan §5；行为变更需逐项明示授权）；
2. **FEAT-066 acquire TTL 判定面**（DEC-248② 拆出——0.90 候选池新票，depends_on=FEAT-065：治理存储层单一执法点原子临界区 + 过期锁 acquire 拒绝 + 受控回收指引，不自动接管）；
3. **DEC-244 挂起清单 0.90+**：God Module 拆分 / 存储分离其余表 / task_status BLOCK 机录化 / FEAT-045 P-b / HotFactSource 版本字面量族 / GOVERNANCE_SESSION_ID 复核 / 量测边缘 + FIX-380 P2-1；
4. **review-record CLI --force 旗标**（RISK-047 候选——未入 0.89 载荷亦未入挂起清单，候选未排期如实登记——version-plan §7）；
5. **主文件大拆解**（0.88 arch 告诫延续——version-plan §1）；
6. **任何 RISK 的关闭声明**（09-30 风险窗复评属 risk-log 处置义务——M-4 裁决，version-plan §6；RISK-050（10-31）窗外维持打开；RISK-059（B-13 前置三缺口）打开——激活授权票前置，非本版载荷；本版无 RISK 关闭承诺）。

## 回滚区间锚定（与 rollback-plan-0.89.0 §区间锚定同锚同源）

**本版回滚区间（triage 锚定）= `33d19b0..<发布 tip>`**（回退点 = `v0.88.0` tag；`33d19b0` = tag peel = REL-086 M-5 transition 提交；tag object `82905e6`，taggerdate 2026-09-25 20:08:32 +0800 实测——FIX-349 口径 taggerdate 权威）：

- **论证①（下界 = `33d19b0`，本版单轨无双轨分歧）**：git 区间语义 `X..Y` 排除下界自身。七票行为载荷（批次一 2 + 批次二 3 + 批次三 3）+ M-0（REL-090）+ M-1 bump（REL-091）**全部落在 `33d19b0` 之后**；前版收尾两提交（`2dac7af` M-6 修复批 / `9347c11` M-8 收口批——0.88.0 发布收尾的文档/治理记录面）亦在 tag 后落库，如实纳入区间（**非行为载荷**——回退影响 = 发布文档面回退与审计信息，见 rollback-plan-0.89.0 §1）；无 0.85.0 树内搭车批的 DEC-222 归属面，triage 锚定同时就是完整行为回退区间：撤销即回到 `v0.88.0` 行为（peel `33d19b0`）。单轨，M-3 审查只需复核单轨锚定与窗口计数。
- **论证②（终点必须是 `<发布 tip>`，不得是候选打包提交）**：0.81.0 先例 **F-04**——post-candidate 提交会修改区间内新增的 release 文档导致 revert 冲突（0.84.0 演练 P-12 反向实证 exit 1/CONFLICT）。终点 MUST 是 M-5 transition 提交（hash 由 M-5 生成后回填，本文件不预编造）。
- **窗口计数如实登记**：`git rev-list --count 33d19b0..HEAD` = **12**（2026-09-26 实测，HEAD = `b66bd25` REL-091；`git describe` = v0.88.0-12-gb66bd25 交叉印证）；区间计数不写死——M-5 现场以 `git rev-list --count 33d19b0..<发布 tip>` 取值记入 EVD。

## M-链状态（截至本文件落盘 2026-09-26——映射 version-plan-0.89.0 §3b）

| 里程碑 | 状态 | 事实 |
|---|---|---|
| M-0 规划确认 | ✅ 完成（双 GO） | REL-090（`76c86a9`）：version-plan v1.1 落库 + 双审 APPROVED_WITH_NOTES/0×2（F-1~F-6 收口落字）+ §5 五前置核验回填（①②④⑤一致 / ③勘误行计数口径漂移 3≠11 如实登记——迁移阻断判定以 B-13 授权票演练引擎实测为准）；EVD-1171；DEC-244/245 授权生效 |
| 载荷批次一/二/三（七票） | ✅ 完成 | 批次一 FIX-393（`8a94d64`）→FIX-394（`3cb4048`）；批次二 FIX-390（`def9508`）+FIX-392（`65c8e4b`）+FIX-395（`7795f59`）；批次三 FIX-391（`c9b7415`）→FEAT-065（`ab7a8e1`+`b950fef`）——EVD-1172~1181；同文件串行纪律保持（verify_workflow.py 三票共面 / closure_chain.py 两票共面——DEC-246①②）；例外消解闭环三票在案 |
| M-1 版本 bump | ✅ 交付（已落库） | REL-091（`b66bd25`，2026-09-26 20:31）：28 投影面 + CHANGELOG 0.89.0 段单 canonical + static-pin 消解；出口四项 PASSED（version-consistency / projection-sync / entry-bootstrap-sync / manifest）；REVIEW-REL-091-RELEASE-R0 APPROVED_WITH_NOTES/0（P2-1 census 差值对账移交 M-2） |
| **M-1R 发布面（本票）** | 🔄 本票执行 | REL-092：四件套 + M-2 实测回填位预留（重点席六席） |
| M-2 门禁实测 | ⏳ 回填位预留 | version-plan §4 全条目 + §9 组合测试集四项必查；**前置归档席先行**（DEC-246④ 方案 A——六票集成后、M-2 前：dry-run 先行，见 checklist 专席③）；**census 对账席**（REVIEW-REL-091 P2-1——51 vs 49 分段归因入 EVD）+ **18/18b live 复测席**（EVD-1176 P3-4——窗口激活后）+ **archguard sanctioned regen 席**（EVD-1176 路由）+ **FEAT-065 双面演示席**（DEC-248④）+ **组合②列补充席**（F-1——FIX-393 verify_workflow.py 腿）；全量 pytest M-2 一次预算（M-3 改可执行代码须退回验证——0.88 §3 口径承袭）；组合批次一中间态独立留 EVD（F-5） |
| M-3 双半面审查 | ⏳ 待 Coordinator 派发 | 产品代码半面（Code Reviewer 链）+ 发布半面（Release Reviewer 链）；终态口径同 0.88（APPROVED 或 unresolved_blockers=0 的 APPROVED_WITH_NOTES）；**M-3 抽查义务：FIX-390/392 红侧 fixture 为非预录形态**（DESIGN-R0 F-6）；复审必达 |
| M-4 修复窗 + 风险裁决 | ⏳ | **09-30 风险窗履行**（RISK-036/039/046 复评 + RISK-047/048 同窗观察——DEC-243 先例形态；时序纪律：窗内履行不迟于 2026-09-30，若 M-4 晚于 09-30 复评裁决须窗内独立先行入账、M-4 消费其结论——version-plan §6）；go/no-go 由 Coordinator 呈现裁决（DEC-245 授权；**arch 顾问意见前置**——DEC-240 先例） |
| M-5 candidate | ⏳ Coordinator 面 | checklist 全席回填 + `skills/software-project-governance/core/releases/0.89.0.json` candidate manifest 创建 + 四件套同批提交 → TO_BE_DEFINED=0 → **DEC-246⑧ manifest—ledger—tag 绑定关系核验** |
| M-6 预推校验 | ⏳ M-5 后 push 前 | `check-release --lineage-mode released --release-commit <commit>` + `release-ledger --remote origin` 全绿方进 M-7；UNKNOWN/BLOCKED 不得包装为 PASS（version-plan §3b） |
| M-7 tag+push | ⏳ Coordinator 面 | annotated tag `v0.89.0`（peel = transition 提交；taggerdate 权威——FIX-349）+ master + tag 原子推送（本地/remote tag peel 一致；event integrity sha256 双锚） |
| M-8 归档 + 收尾 | ⏳ Coordinator 面 | `archive.py migrate --auto`（**dry-run 先行**）+ `check-archive-integrity` PASS + roadmap 0.89.0 行状态回填 + REL-090 任务行终态回填 + **Check 28s 复测**（version-plan §4.5——前置归档席执行后的消解有效性确认）+ plan-tracker `工作流版本` → 0.89.0（当前 0.88.0 过渡态 WARN——本版 verify 唯一预期 WARN，CHANGELOG 披露④） |

## 发布窗口

| 时点 | 内容 |
|---|---|
| 2026-09-25 20:08 | v0.88.0 发布（tag taggerdate 20:08:32 +0800 权威，peel `33d19b0`，tag object `82905e6`） |
| 2026-09-25 | DEC-244 范围授权 → REL-086 M-6/M-8 收尾批落盘（`2dac7af` 20:06 / `9347c11` 20:12）→ REL-090 M-0 收口双 GO（`76c86a9` 23:34——五前置核验回填完成） |
| 2026-09-26 | DEC-245 执行授权 → 批次一 FIX-393（`8a94d64` 10:24）→FIX-394（`3cb4048` 12:17）→ 批次二 FIX-390（`def9508` 14:08）+FIX-392（`65c8e4b` 15:23）+FIX-395（`7795f59` 17:31）→ 批次三 FIX-391（`c9b7415` 18:27）→FEAT-065（`ab7a8e1` 19:31 + `b950fef` 19:54）→ DEC-246/247/248 入账 → **M-1 bump REL-091（`b66bd25` 20:31）** |
| 2026-09-26 | **M-1R（本票 REL-092）**：四件套 + M-2 回填位预留 → M-2 实测（前置归档席先行）→ M-3 双审 → M-4 风险窗履行/go-no-go（09-30 窗纪律）→ M-5~M-8 另记（taggerdate 权威） |

## 门禁摘要（数值基线——本票为 M-1R 草案，M-2 实测前不预填）

| # | 门禁面 | 基线 / 姿态 | 依据 |
|---|---|---|---|
| 1 | 全量 pytest（M-2 一次预算） | 0.88 M-2 基线 **4119P/0F**（历史首次全绿）——0.89 零回归目标；**新增基线口径（DEC-246⑦）**：七票（FIX-393/394/390/392/395/391/FEAT-065）新增测试并入——无非预期删除/失败/未说明 skip 增加、新增测试实收执行（4119P = 基线口径非失败计数）；「全量只在 M-2」是预算非免检许可——M-3 修改可执行代码时原 M-2 证据不自动覆盖 | version-plan §4.1；DEC-246⑦；checklist #1 |
| 2 | verify 全量 + e2e + census 身份集 | 已知披露面基线 = 36 issues（DEC-243 实测口径）→ **收窄形态 = REQ-092×n + EVD-1146×1**（身份集合口径 DEC-246③；REQ-092 外部依赖零豁免红线维持——非本版范围；EVD-1146 superseded 残留维持披露——DEC-227 路线 a）；唯一预期 WARN = plan-tracker 过渡态（M-8 收口） | version-plan §4.2；checklist #2/#13 |
| 3 | 组合测试四项 + 补充席 | **version-plan §9 四项 M-2 必查席**：①FIX-393×FIX-394 状态闭环 / ②FIX-390×FIX-392 检查器互不回归 / ③FIX-391×FEAT-065（×FIX-394 closure 腿）链健康 / ④FIX-393 archive 腿×归档完整性；**组合②列补充席（F-1）**：覆盖 FIX-393 verify_workflow.py 腿（verify_workflow.py 共面票实为三票——批次间全局串行约束）；DEC-246⑤ 判据要点并入各席（状态证据正交/身份归属不跨链跨轮借用）；批次一中间态独立留 EVD（F-5） | version-plan §2/§9；DEC-246⑤；checklist #12 |
| 4 | LRC Check 31（预算不变版） | 上限 **361,923** 沿续（FIX-369 公式值，本版零改动）；本版 TRIAGE×6 + REL-090 + EVD/REVIEW 机录增量可观——M-2 复算期望 PASS 且如实记录当场 units（不预填）；若越线按 FIX-369 公式 ceil(实测峰值×1.2) 重定标 + baseline-register 登记（**重定标非豁免**） | version-plan §4.3；checklist 专席①关联面 |
| 5 | archguard 棘轮席（R1~R7） | 引擎现值 **26318 LOC 超锚 26193**（+125 归因链在案——EVD-1176：HEAD 既有 +39〔FIX-393/394 集成〕+ FIX-390 +86）；**0.89 M-2 统一 sanctioned regen**（0.88 M-2 先例 commit `501d8dc`——载荷票未完不中途 regen 已遵守）；**regen 目标值待实测不预填**；R5 期望 97/97 维持；regen MUST 附归因链留档不得静默清零 | EVD-1176；version-plan §4.4；checklist 专席② |
| 6 | Check 28s evidence-log 复测 | ERROR 现值 **1,761,442B ≈ 1720KB**（2026-09-26 本票起草实测；M-0 期 1690.6KB → REL-091 审查时点 1719.5KB 持续增长）；**DEC-246④ 方案 A：前置历史证据归档席**（六票集成后、M-2 前——dry-run 先行、已封闭历史周期迁移、当前链活跃证据保留、引用/索引连续性验证）；M-8 保留本轮周期归档收口 + §4.5 复测 | DEC-246④；version-plan §4.5；checklist 专席③ |
| 7 | candidate ledger 两态 + quality-tools | 本票实测 `release-ledger --version 0.89.0 --no-remote` 预提交态预期 FAIL（manifest 锁面外未建——checklist 如实归类）；Coordinator M-5 提交后 MUST 复跑（期望 NATIVE_CANDIDATE PASS）→ M-6 `--remote`；**DEC-246⑧ manifest—ledger—tag 绑定关系 M-5/M-6 核验**（M-6 修改被覆盖内容则 candidate 再验证）；**quality-tools 未安装记 NOT_RUN 不虚报**（ADR-010/stage-release 退出条件承接） | version-plan §4.6；DEC-246⑧；checklist #10/#16 |
| 8 | 版本投影面 | source = 0.89.0；28 投影面（M-1 已实测 check 28/28 PASS——written=17+幂等镜像 11）；M-2 `release-projection` check-only + check-projection-sync + check-entry-bootstrap-sync 复跑确认；静态钉面期望 0 WARN（M-1 消解后） | REL-091（EVD-1182）；checklist #3~#5 |

## 硬门槛自检（本任务）

| 门槛项 | 判定 | 依据 |
|---|---|---|
| 四件套成形、对照 0.88.0 四件套先例无缺面 | **PASS** | 结构逐节对照 `docs/release/{release-plan,release-checklist,rollback-plan,feature-flags}-0.88.0.md`（REL-088 commit `a8a72a3` 形态）；全表行管道符转义审查（FIX-365 ragged 教训——表 cell 内零裸管道符） |
| 回滚区间实测 | **PASS** | `git log --oneline 33d19b0..HEAD` + `git rev-list --count` = **12**；`git describe` v0.88.0-12-gb66bd25 交叉印证；`33d19b0` = `git rev-parse v0.88.0^{}` 实测同一（tag object `82905e6`，taggerdate 2026-09-25 20:08:32 +0800） |
| 内容事实源引用准确 | **PASS** | 七票 commit/EVD（EVD-1171~1182）逐项对照 git log 实测 + CHANGELOG 0.89.0 段（单 canonical）；DEC-244~248 取自 `.governance/decision-log.md` 实读（UTF-8）；census/审查终态取自 review-REL-091-RELEASE-R0 与各票 review 报告实读；Check 28s 现值取自 `.governance/evidence-log.md` 字节实测 |
| check-manifest-consistency / check-cross-references | 见本票验证记录（四件套落盘后运行） | docs/release 四文件与 0.88.0 先例同形态（manifest 不逐文件登记 docs/ 面——实证见 checklist 验证记录） |
| 真实 `.governance/` 零写入 | **PASS** | 写入面 = 四件套（TRIAGE-REL-092 files 锁定）；不触治理数据、不改产品代码、CHANGELOG 不再改、tag·push·transition 不执行 |

---
*REL-092 M-1R 起草冻结（2026-09-26，Governance Developer Agent）。事实基线：12 提交窗口与 hash/日期取自 `git log`/`git rev-list`/`git describe`/`git rev-parse v0.88.0^{}`/`git for-each-ref refs/tags/v0.88.0` 实测（`33d19b0..b66bd25` = 12；v0.88.0 taggerdate 2026-09-25 20:08:32 +0800 = peel `33d19b0`）；七票载荷、行为修正三面、披露①~⑤口径取自 CHANGELOG 0.89.0 段（REL-091 交付版——project/CHANGELOG.md 单 canonical）；M-0 GO 与五前置核验回填取自 version-plan-0.89.0 §3b/§5 实读 + `76c86a9` commit message；DEC-244~248 取自 `.governance/decision-log.md` 实读（UTF-8）；各票审查终态取自 docs/reviews/ 各报告实读（FIX-390/391/392/393 R0 AWN/0、FIX-394 R0 AWN→R1 APPROVED、FIX-395 R0 NC→R1 AWN、FEAT-065 R0 AWN/0、REL-090 双 AWN/0、REL-091 AWN/0）；census 49→51 与 Check 28s 1719.5KB 取自 review-REL-091-RELEASE-R0 P2-1 实读；Check 28s 现值 1,761,442B 取自 `.governance/evidence-log.md` 字节实测（2026-09-26）；archguard 26318/26193 归因取自 EVD-1176 实读。未生成事实（发布 tip、tag、M-2 门禁数值、candidate manifest 提交、B-12 真实翻转、B-13 真实切换、09-30 风险窗履行结论）一律标期义务/回填位，不预填。*
