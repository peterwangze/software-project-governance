# Release Plan — 0.87.0（REL-084 M-1R / REL-085）

> **任务**: REL-085（P1；triage `.governance/change-triage/REL-085.json`；DEC-226 预授权链——M-1 GO 后 M-1R）· **日期**: 2026-09-21 · **性质**: M-1R 发布材料面（四件套：release plan/checklist/rollback/feature-flags）——非发布执行；M-2 门禁实测回填位已预留（见 checklist）
> **裁决权边界**: 版本 go/no-go 与 tag/transition/push 由 Coordinator 执行（DEC-226 预授权承载——用户 2026-09-20「我授权 Coordinator 按照推荐进行推进，直到最新规划版本发布」；预授权**不免除** M-2 门禁实测与 M-3 双半面审查）；本文件由 Governance Developer Agent 起草，供 Release Reviewer / M-3 审查链消费
> **写入边界**: 仅本四件套（triage `files` 锁定面）；不触 `.governance/` 真实治理数据、不修改产品代码、不改 CHANGELOG（已于 `80d71b5` M-1 冻结）、不执行 tag/push/transition；`core/releases/0.87.0.json`（candidate manifest）**不在本票锁面**——由 Coordinator M-1R 提交批补齐（本票如实披露，见 checklist 披露 ①）

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项：

- **No official approval claim**：official approval 未被授予、未被主张；0.87.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.87.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版全部验收在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）类口径下完成——隔离验收不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；0.87.0 为治理健康收口版；do not claim 1.0.0 production-ready。
- **发布 tip 未生成前不预先编造**：`<发布 tip>`（M-5 transition 提交）与 tag 事实本四件套不预填——hash 一律由 M-5 生成后回填（FIX-349 口径：taggerdate 权威）。
- **M-2 数值不预填**：本票为 M-1R 草案，M-2 门禁实测尚未执行——checklist 门禁表全部为回填位预留（重点四席：Check 31 重定标口径 / Check 16 3 FAIL 披露 / 全量 pytest 位 / 棘轮位），实测前不写任何通过性数值。

## 版本号与授权链

| 项 | 值 |
|---|---|
| 版本号 | **0.87.0**（MINOR；0.86.0 → 0.87.0 不跳号、无预留占用——REL-084 Release R0 代验：0.86.0 已发布顺延 +1；无 0.87.x tag/预留冲突；1.0.0 预留位未触碰） |
| 发布任务 | **REL-084（M-0 规划）/ REL-085（M-1R 本票）**——version-plan-0.87.0 双半面 APPROVED_WITH_NOTES/0×2（DESIGN R0→R1 / RELEASE R0） |
| 授权链 | **DEC-226（0.87.0 标准链预授权——聚焦集裁定：FIX-367/368/LRC 重定标/FIX-366/FIX-364/locks-release；预授权不免除门禁）** → DEC-227（FIX-371 路线 b 历史豁免账本——豁免账本仅容纳 2026-09-20 前存量历史行，新增行零豁免全严检；路线 a 数据补录被否〔补录=编造风险违反 P1〕、路线 c 披露基线被否〔M-2 门禁仍红〕）→ DEC-228（DEC-227 记录面修订——三消费方明列 Check 16/17/18 + 主运行面 historical_exempted 计数披露义务） |
| MINOR 依据 | `core/VERSIONING.md` L12「新增 B/C 级自动化能力」——载荷 = locks-release 新子命令（新增受治理能力面）+ Check 16/17 历史豁免账本 + Check 31 容量重定标 + 七票收口修复；非纯 bug fix（L38 PATCH 不适用）；Breaking changes = **无**（L11 逐项核对不成立：B-9 属基线机制设计内数值重定标非判定语义变更〔显式 L11 处置——R0-RELEASE-F3，0.85.0「判定姿态翻转」先例同型〕；B-10 纯新增 CLI、shrink-locks 保留无删除面；B-11 活跃判定语义零弱化——CHANGELOG 0.87.0 段同口径） |
| Single-Threaded Owner | Coordinator（发布决策与 `.governance/` 写回）；Release 面产出物由角色 agent 执行，Release Reviewer 独立审查 |
| 用户获得方式 | `/plugin update`（或 `git pull` + reload）——版本号与 28 投影面 bump 保证 marketplace 新鲜度比对生效；升级说明 MUST 携带 B-9/B-10/B-11 行为变更（CHANGELOG 0.87.0 段行为变更节原文口径） |

## 发布范围

### 载荷构成（九票闭环 + M-1 打包——REL-084 / DEC-226~228）

> git 窗口实测（2026-09-21）：**0.87.0 窗口 = `6e25753..<发布 tip>`**（`6e25753` = `v0.86.0` tag peel = REL-082 M-5 transition 提交，taggerdate 2026-09-20 16:15:13 +0800 实测）；`6e25753..HEAD`（HEAD = M-1 候选 `80d71b5`）实测 **9 提交**（`git rev-list --count` 与 `git describe`（v0.86.0-9-g80d71b5）双实测交叉印证）。九票 = 批 1 并行收口修复四票 + 批 2 串行引擎修复三票 + M-0 规划票 + M-1 打包票。

| 批 | 任务 | 关键交付 | 提交 | 证据 |
|---|---|---|---|---|
| **批 1「并行收口修复」** | FIX-367 | 热事实源回填（Check 28c×3）：roadmap 0.86.0 行 / 0.85.0 勘正 / 总览 0.86.0——task-row-update 机录 op-98c0f7f6 | 治理记录票（`.governance/` gitignored——零 commit 面，如实注记） | EVD-1122 窗口内机录链 |
| | FIX-368 | `parse_impact_analysis_entries` 列偏移修复（[4]/[5]→[3]/[4]——EVD-1118 误 FAIL Check 16/17 消除；file_location 红线不动；3 回归测试 + 4 处 fixture LIVE 迁移） | `5e56021` | EVD-1122；REVIEW-FIX-368-R0 双审 APPROVED_WITH_NOTES/0 |
| | FIX-364 | snapshot freshness 午夜窗时间敏感修复（fixture 同粒度口径 + stdlib 时钟注入 + 午夜窗正例/负例双钉） | `9aa27a6` | EVD-1124；REVIEW-FIX-364-R0 APPROVED_WITH_NOTES/0 |
| | FIX-369 | LRC 语义预算容量重定标（Check 31 门禁面收口——**B-9**）：max_semantic_units 300,000→**361,923 = ceil(301,602×1.2)**——重定标非豁免；provenance 注释 + 公式钉值/反豁免 fail-closed 双测试；基线经 FEAT-047 baseline-register 登记 | `a7f89ac` | EVD-1123；REVIEW-FIX-369-R0 APPROVED_WITH_NOTES/0 |
| **M-0 规划** | REL-084 | version-plan-0.87.0 双半面双审（DESIGN R0→R1 / RELEASE R0 全 APPROVED_WITH_NOTES/0）+ 批 1 全清治理记录 + roadmap 0.87.0 行 + M-1 绕开手法退路预声明（R1-N2——随 FIX-366 落地失效） | `80069a2` | EVD 窗口内机录链；**M-0 GO** |
| **批 2「串行引擎修复」** | FIX-366 | projection 两遍 plan 修复（byte_copy source = 同批 transformed target 耦合 → 内存 resolve 一次收敛）+ CRLF 连带根因修复（`read_text`→`read_bytes().decode`）+ 4 测试含 CRLF 护栏双断言——0.86.0 披露③ 技术债清偿 | `2ab3847` | EVD-1125；REVIEW-FIX-366 R0 APPROVED_WITH_NOTES→R1 APPROVED |
| | FIX-372 | evidence 列约定统一三处修复（Check 20 fail-open 恢复 + format check LIVE 对齐 + entry_method 语义；9 处 evidence 列读取点全量排查清单留档） | `aa72c37` | EVD-1126；REVIEW-FIX-372-R0 APPROVED_WITH_NOTES/0 |
| | FIX-370 | governance_store locks-release writer（**B-10**）：task 锚定真删除 + B-10 先登记后删除 + released_files 审计章 + 三态/幂等 fail-closed；96 键 CLI 分发面重定基线（FEAT-355 同型）；锁经 locks-release 自释放活体验证（op-7c866828）——**批 2 全清** | `dd4537b` | EVD-1127；REVIEW-FIX-370-R0 APPROVED_WITH_NOTES/0 |
| **批 3「豁免账本」** | FIX-371 | Check 16/17 历史豁免账本（**B-11**；DEC-227 路线 b）：✅ 终态豁免 + 三面留痕不静默——主运行面 26=8+18 对账；真实面 31→5 FAIL；REQ-092 blocked 保持零豁免红线实证；R0 NEEDS_CHANGE（F-1）→R1 APPROVED/0 | `a6d3bfb` | EVD-1128 |
| **M-1 候选打包** | FEAT-059 | 0.86.0→0.87.0 全仓 bump（24 tracked 面）+ CHANGELOG 0.87.0 段 + **FIX-366 两遍 plan 正道首活体**——投影单次 `release-projection --write` 一次收敛零回滚（FEAT-053/058 绕开手法撤除，M-0 验收面「绕开手法可撤」兑现） | `80d71b5`（2026-09-21 11:36:24 +0800） | EVD-1129（机录）；REVIEW-FEAT-059-R0 = APPROVED_WITH_NOTES/0——**M-1 GO** |
| **⑥ 治理面** | REL-084 链 | 3 决策（DEC-226/227/228）+ 8 EVD（EVD-1122~1129——七票交付审查链全部机器写入 governance-store evidence-append）+ 双半面审查报告留档（review-REL-084-DESIGN-R0/R1、review-REL-084-RELEASE-R0、review-FIX-371-CODE-R0、review-FEAT-059-RELEASE-R0）；产品任务全部 change-triage 机录 + Developer→Reviewer 审查链（含 NEEDS_CHANGE→R1 转化三票〔FIX-366/370/371〕，0 unresolved blockers） | — | — |
| **M-1R 发布面（本票）** | REL-085 | **四件套**（plan/checklist/rollback/feature-flags——本票 expected-new 锁面）+ M-2 门禁实测回填位预留。`core/releases/0.87.0.json` 与 M-2 复跑义务由 Coordinator 提交批承载（锁面外披露，checklist ①） | 本票（Coordinator 提交后为 candidate commit） | 待提交 |

### 本版不发布什么（显式排除——Amazon 实践）

1. **write-guard WARN→BLOCK 升级**（DEC-224 双约束：不得 WARN-once-then-absorb + hook 窗口消费权台账化——0.88 出槽清单）；
2. **存储分离 JSON 化**（首表 decision-log）/ closure 铺开（取消/重开/异常接管）/ FEAT-044 回合心跳 + FEAT-045 并行段识别 / B-7 index-rebuild + 大表迁移 + 发版管线自举（DEC-226 出槽清单——version-plan-0.87.0 §6）；
3. **FIX-373~376 四票**（切分器状态泄漏 FIX-373 / 9-cell 豁免消歧 FIX-374 / FIX-375〔FIX-370 遗留〕/ FIX-376——出槽 0.88 登记，plan-tracker REL-084 状态行出槽注记）；
4. **量测边缘观察 4 项**（0.86.0 移交：journal detail 透传 / triage-id 词表对齐 / conflict 退出码语义统一 / pre-probe 语义注记——0.87 未处置，继续挂账）；
5. **任何 RISK 的关闭声明**（本版无 RISK 关闭承诺；RISK-036/039/050 维持打开态以 risk-log 实况为准）。

## 回滚区间锚定（与 rollback-plan-0.87.0 §区间锚定同锚同源）

**本版回滚区间（triage 锚定）= `6e25753..<发布 tip>`**（`6e25753` = `v0.86.0` tag peel = REL-082 M-5 transition 提交）：

- **论证①（下界 = `6e25753`，本版无双轨分歧）**：0.87.0 与 0.86.0 期不同——**无「载荷在候选面下界之前」的归属问题**（0.86.0 曾有批 0/1 随 v0.85.0 树入库的 DEC-222 裁定面；本版九票行为载荷全部落在 `6e25753` 之后，候选面 = 完整窗口合一）。区间排除下界自身 ⇒ 九提交（批 1 四票面 + M-0 + 批 2 三票 + FIX-371 + M-1 bump）全部完整落入撤销集，回滚落点即 `v0.86.0` 行为（peel `6e25753`）。
- **论证②（终点必须是 `<发布 tip>`，不得是候选打包提交）**：0.81.0 先例 **F-04**——post-candidate 提交会修改区间内新增的 release 文档导致 revert 冲突（实测 3 处 UU；0.84.0 演练 P-12 反向实证 exit 1/CONFLICT）。终点 MUST 是 M-5 transition 提交（hash 由 M-5 生成后回填，本文件不预编造）。
- **窗口计数如实登记**：`git rev-list --count 6e25753..HEAD` = **9**（2026-09-21 实测，M-1 候选 `80d71b5` 已含——即回滚区间 M-1R 起草时点已覆盖 9 提交）；区间计数不写死——M-5 现场以 `git rev-list --count 6e25753..<发布 tip>` 取值记入 EVD（候选提交后计数随发布批增长）。

## M-链状态（截至本文件落盘 2026-09-21）

| 里程碑 | 状态 | 事实 |
|---|---|---|
| M-0 规划确认 | ✅ 完成（GO） | REL-084（`80069a2`）：version-plan-0.87.0 双半面双审全 APPROVED_WITH_NOTES/0（DESIGN R0→R1 / RELEASE R0）；DEC-226 预授权生效；roadmap 0.87.0 行 |
| 批 1（并行收口修复四票） | ✅ 完成 | FIX-367（机录）/ FIX-368 `5e56021` / FIX-364 `9aa27a6` / FIX-369 `a7f89ac`——EVD-1122/1124/1123；0 unresolved blockers |
| M-0 规划票落库 | ✅ 完成 | `80069a2` REL-084（批 1 全清治理记录 + 双半面审查报告留档） |
| 批 2（串行引擎修复三票） | ✅ 完成（全清） | FIX-366 `2ab3847` / FIX-372 `aa72c37` / FIX-370 `dd4537b`——EVD-1125/1126/1127；绕开手法撤除 + locks-release 活体验证 op-7c866828 |
| 批 3（豁免账本） | ✅ 完成 | FIX-371 `a6d3bfb`——EVD-1128；R0 NEEDS_CHANGE（F-1）→R1 APPROVED/0（复审必达 T1 履行） |
| M-1 候选打包 | ✅ 完成（GO） | `80d71b5` FEAT-059（2026-09-21 11:36:24 +0800）：bump 24 tracked 面 + CHANGELOG 0.87.0 段 + FIX-366 正道首活体；REVIEW-FEAT-059-R0 = APPROVED_WITH_NOTES/0——**M-1 GO**；EVD-1129 |
| **M-1R 发布面（本票）** | 🔄 本票执行 | REL-085：四件套 + M-2 实测回填位预留 |
| M-2 门禁实测 | ⏳ 回填位预留（本票四席） | A 清单回填位就绪（verify / Check 31 重定标口径 / Check 16 3 FAIL 披露 / 全量 pytest / 棘轮位 / ledger / e2e 等——见 checklist Candidate Gate Results）；check-release 复合门禁与 candidate 提交后 ledger 复跑 = Coordinator 提交批义务 |
| M-3 双半面审查 | ⏳ 待 Coordinator 派发 | Release Reviewer + Design/Code Reviewer（按变更面）；review-record 机录；复审必达；**含 FIX-366 回退风险披露（绕开手法复活面）复核** |
| M-4 用户停点 | ⏳ DEC-226 预授权 | 预授权不免除 M-2/M-3；go/no-go 由 Coordinator 呈现裁决 |
| M-5 transition + tag | ⏳ Coordinator 面 | candidate manifest 提交（复跑 `release-ledger --no-remote` 期望 NATIVE_CANDIDATE PASS）→ release commit（单父 = candidate；manifest-only candidate_to_released + integrity）→ annotated tag v0.87.0（peel = transition commit） |
| M-6 released 门禁 | ⏳ M-5 后 | `check-release --lineage-mode released --release-commit <commit>` + `release-ledger --remote` |
| M-7 push | ⏳ Coordinator 面 | master + tag 原子推送（远端 SHA 精确一致） |
| M-8 归档 + 收尾 | ⏳ Coordinator 面 | `archive.py migrate --auto --dry-run` → 迁移 → `check-archive-integrity` PASS；plan-tracker `工作流版本` → 0.87.0（当前 0.86.0 过渡态 WARN——本版 verify 唯一预期 WARN）；**roadmap 0.87.0 行回填义务内建**（FIX-367 复发预防——R0-DESIGN-F8） |

## 发布窗口

| 时点 | 内容 |
|---|---|
| 2026-09-20 | v0.86.0 发布（tag taggerdate 16:15:13 +0800，peel `6e25753`）；同日治理活数据三次 LRC 实测 300,701（晨）/ 300,913（~17:4x）/ 301,602（~18:0x）——Check 31 容量越线披露在案（0.86.0 checklist #16/披露⑨），构成 FIX-369 重定标事实源 |
| 2026-09-20 晚~夜间 | DEC-226 预授权 + REL-084 M-0 规划双审 + 批 1 四票落库（`5e56021`/`9aa27a6`/`a7f89ac` + `80069a2`）——逐提交时刻未逐一实测列示，M-3/M-5 期以 git 实测为准 |
| 2026-09-21 上午 | 批 2 三票 + 批 3 落库（`2ab3847`→`aa72c37`→`dd4537b`→`a6d3bfb`——批 2 全清）+ **M-1 bump `80d71b5`（11:36:24 +0800，M-1 GO）** |
| 2026-09-21 | **M-1R（本票 REL-085）**：四件套 + M-2 回填位预留 → M-2 实测（Coordinator/后续工位）→ M-3 双审 → M-4 go/no-go（DEC-226 预授权呈现）→ M-5 candidate 提交/transition/tag（发布时点按 FIX-349 口径 = **taggerdate 权威**） |

## 门禁摘要（数值基线——本票为 M-1R 草案，M-2 实测前不预填）

| # | 门禁面 | 基线 / 姿态 | 依据 |
|---|---|---|---|
| 1 | Check 31 语义预算（**B-9 新值**） | 上限 **361,923** = ceil(301,602×1.2)——M-2 复跑期望 PASS 且如实记录当场 units 计数；若 BLOCKED（fail-closed）如实披露不豁免 | FIX-369（`a7f89ac`）；provenance 注释 `loop_runtime_claims.py` L225-242；M-2 回填位见 checklist #16 |
| 2 | Check 16/17（**B-11 豁免账本**） | M-1 交付时点真实面 3 FAIL 姿态（31→5→3——REQ-092 blocked 维持 FAIL = 预期披露非豁免）；M-2 复跑如实回填当场计数；**新增行零豁免全严检**（DEC-227） | FIX-371（`a6d3bfb`）；M-2 回填位见 checklist 披露① |
| 3 | 全量 pytest | M-2 全量跑回填（午夜窗外时段执行注记沿用 0.86.0 方法论——FIX-364 已修复该面但实测为准） | checklist 回填位 #11 |
| 4 | 棘轮 archguard R1~R7 | R5 期望 **96/96** frozen（FIX-370 96 键 CLI 分发面重定基线消费面——M-2 实测确认） | FIX-370（`dd4537b`）；checklist 回填位 #8 |
| 5 | 版本投影面 | source = 0.87.0；28 投影面（M-1 已实测一次收敛零回滚——FIX-366 正道首活体）；M-2 check-only 复跑确认 | FEAT-059（`80d71b5`）EVD-1129 |
| 6 | candidate ledger 两态 | 本票实测 `release-ledger --version 0.87.0 --no-remote` 预提交态预期 FAIL（manifest 锁面外未建——checklist 如实归类）；Coordinator 提交后 MUST 复跑（期望 NATIVE_CANDIDATE PASS）→ M-5 后 `--remote` | ADR-010 / 0.86.0 #10 同流程 |

## 硬门槛自检（本任务）

| 门槛项 | 判定 | 依据 |
|---|---|---|
| 四件套成形、对照 0.86.0 四件套先例无缺面 | **PASS** | 结构逐节对照 `docs/release/{release-plan,release-checklist,rollback-plan,feature-flags}-0.86.0.md`；全表行管道符转义审查（FIX-365 ragged 教训——表 cell 内零裸管道符） |
| 回滚区间实测 | **PASS** | `git log --oneline 6e25753..HEAD` + `git rev-list --count` = **9**；`git describe` v0.86.0-9-g80d71b5 交叉印证；`6e25753` = `v0.86.0^{commit}` 实测同一 |
| 内容事实源引用准确 | **PASS** | 九票 commit/证据号（EVD-1122~1129）逐项对照 git log 实测 + CHANGELOG 0.87.0 段（`80d71b5` 冻结版）；B-9 公式 361,923=ceil(301,602×1.2) 对照 `loop_runtime_claims.py` L225-243 实读 |
| check-manifest-consistency | 见本票验证记录（四件套落盘后运行） | docs/release 四文件与 0.86.0 先例同形态（manifest 不逐文件登记 docs/ 面——实证见 checklist 验证记录） |
| 真实 `.governance/` 零写入 | **PASS** | 写入面 = 四件套（triage files 锁定）；不触治理数据、不改产品代码、CHANGELOG 不再改、tag·push·transition 不执行 |

---
*REL-085 M-1R 起草冻结（2026-09-21，Governance Developer Agent）。事实基线：9 提交窗口与 hash 取自 `git log`/`git rev-list`/`git describe`/`git rev-parse v0.86.0^{commit}` 实测（`6e25753..80d71b5` = 9；`v0.86.0` taggerdate 2026-09-20 16:15:13 +0800 = peel `6e25753`）；九票交付与 B-9/B-10/B-11 口径取自 CHANGELOG 0.87.0 段（`80d71b5` 冻结版）；Check 31 公式与 provenance 取自 `loop_runtime_claims.py` L225-243 实读；FIX-371 豁免账本实现形态取自 `a6d3bfb` commit stat 实测（verify_workflow.py +144 行 / test_verify_workflow.py +149 行）。未生成事实（发布 tip、tag、M-2 门禁数值、candidate manifest 提交）一律标期义务/回填位，不预填。*
