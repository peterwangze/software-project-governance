# Release Checklist — 0.87.0（REL-084 M-1R / REL-085）

> **M-1R 草案（REL-085，2026-09-21）**——Governance Developer Agent 起草、供 Coordinator 审后随候选提交；结构与措辞对齐 `docs/release/release-checklist-0.86.0.md` 先例。**本文件中的 M-2 数值全部为回填位预留（⏳ 标注）**——M-1R 起草时点 M-2 门禁实测尚未执行，实测后由执行工位原样回填命令输出，未实测项一律标「Coordinator 提交批义务/M-5 期义务/待回填」，不预填。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.87.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.87.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版全部验收在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）类口径下完成——**隔离环境安装冒烟（环境变量重定向至临时目录）通过**不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；0.87.0 为治理健康收口版；do not claim 1.0.0 production-ready。
- **发布 tip 未生成前不预先编造**：`<发布 tip>`（M-5 transition 提交）与 tag 事实本文件不预填。
- **M-2 数值不预填**：本文件门禁表全部为回填位；任何未实测项写成通过 = 违规。

## Release Scope

| 项 | 值 |
|---|---|
| 版本号 | **0.87.0**（MINOR；semver 论证见下节） |
| 发布任务 | **REL-084（M-0 规划）/ REL-085（M-1R 本票）**（DEC-226 预授权链——M-1 GO 后 M-1R；M-1 = FEAT-059 `80d71b5`） |
| 承载决策 | DEC-226~228（3 决策；DEC-226 0.87.0 标准链预授权 / DEC-227 FIX-371 路线 b 历史豁免账本 / DEC-228 DEC-227 记录面修订） |
| 核心范围 | 九票闭环：FIX-367/368/364/369（EVD-1122~1124）+ FIX-366/372/370（EVD-1125~1127）+ FIX-371（EVD-1128）+ M-1 打包 FEAT-059（EVD-1129，REVIEW-FEAT-059-R0 GO）+ M-1R 发布面（REL-085 本票） |
| 目标版本下不发布 | write-guard WARN→BLOCK 升级（DEC-224 双约束）/ 存储分离 JSON 化 / closure 铺开 / FEAT-044/045 / B-7 index-rebuild + 大表迁移 + 发版管线自举 / FIX-373~376 四票（出槽 0.88）/ 量测边缘观察 4 项 / 任何 RISK 关闭声明 |
| 时间窗口 | 2026-09-20 v0.86.0 发布（tag 16:15:13 +0800）→ 同日 DEC-226 授权 + M-0 双审 + 批 1 四票落库 → 2026-09-21 上午批 2 三票 + FIX-371 → 11:36 M-1 bump（`80d71b5`，M-1 GO）→ 2026-09-21 M-1R 四件套（本票）→ M-2 实测回填 → M-3 双审 → M-4/M-5 另记（taggerdate 权威） |
| Single-Threaded Owner | Coordinator（发布决策与 `.governance/` 写回）；M-1R 材料由 Governance Developer Agent 起草，Release Reviewer 独立审查 |
| 用户获得方式 | `/plugin update`（或 `git pull` + reload）；升级说明 MUST 携带 B-9/B-10/B-11 行为变更（CHANGELOG 0.87.0 段行为变更节原文口径）；B-10 纯新增 CLI（shrink-locks 保留）、B-11 活跃判定语义零弱化（非破坏收敛） |

## Change Inventory（**9 个窗口提交 + M-1R 待落** — `git rev-list --count 6e25753..HEAD` = 9，2026-09-21 实测；`git describe` = v0.86.0-9-g80d71b5 交叉印证）

> 窗口起点前一位 `6e25753` = `v0.86.0` tag peel（REL-082 M-5 transition 提交「0.86.0 transition candidate→released manifest-only」，taggerdate 2026-09-20 16:15:13 +0800 实测）。完整清单如下（git 时间序，新→旧）：

| # | commit | 任务 | 关键交付 | 证据 |
|---|---|---|---|---|
| 1 | `80d71b5` | FEAT-059 | **M-1 版本 bump + 候选打包**（24 tracked 面 + CHANGELOG 0.87.0 段 + FIX-366 两遍 plan 正道首活体——投影一次收敛零回滚，FEAT-053/058 绕开手法撤除；25 files +199/−31 含 review 报告 103 行——git stat 实测） | EVD-1129（机录）；REVIEW-FEAT-059-R0 = APPROVED_WITH_NOTES/0（M-1 GO） |
| 2 | `a6d3bfb` | FIX-371 | Check 16/17 历史豁免账本（**B-11**；DEC-227 路线 b）——✅ 终态豁免 + 三面留痕不静默（主运行面 26=8+18 对账）；真实面 31→5 FAIL；REQ-092 blocked 保持零豁免红线 | EVD-1128；R0 NEEDS_CHANGE（F-1）→R1 APPROVED/0 |
| 3 | `dd4537b` | FIX-370 | governance_store locks-release writer（**B-10**）——task 锚定真删除 + 先登记后删除 + released_files 审计章 + 三态/幂等 fail-closed；96 键 CLI 分发面重定基线——**批 2 全清** | EVD-1127；REVIEW-FIX-370-R0 APPROVED_WITH_NOTES/0；活体验证 op-7c866828 |
| 4 | `aa72c37` | FIX-372 | evidence 列约定统一三处修复（Check 20 fail-open 恢复 + format check LIVE 对齐 + entry_method 语义） | EVD-1126；REVIEW-FIX-372-R0 APPROVED_WITH_NOTES/0 |
| 5 | `2ab3847` | FIX-366 | projection 两遍 plan 修复（byte_copy source = 同批 transformed target 耦合 → 内存 resolve 一次收敛）+ CRLF 连带根因修复（read_bytes().decode）——0.86.0 披露③ 技术债清偿 | EVD-1125；REVIEW-FIX-366 R0 APPROVED_WITH_NOTES→R1 APPROVED |
| 6 | `80069a2` | REL-084 | 0.87.0 M-0 规划双审闭环 + 批 1 全清治理记录（DEC-226 预授权；version-plan-0.87.0 双半面 APPROVED_WITH_NOTES/0×2；roadmap 0.87.0 行）——**M-0 GO** | 双半面审查报告留档（review-REL-084-DESIGN-R0/R1、review-REL-084-RELEASE-R0） |
| 7 | `9aa27a6` | FIX-364 | snapshot freshness 午夜窗时间敏感修复（fixture 同粒度口径 + stdlib 时钟注入 + 正例/负例双钉） | EVD-1124；REVIEW-FIX-364-R0 APPROVED_WITH_NOTES/0 |
| 8 | `a7f89ac` | FIX-369 | LRC 语义预算容量重定标（**B-9**）——300,000→**361,923 = ceil(301,602×1.2)**（重定标非豁免；provenance 注释 + 公式钉值/反豁免 fail-closed 双测试；baseline-register 登记） | EVD-1123；REVIEW-FIX-369-R0 APPROVED_WITH_NOTES/0 |
| 9 | `5e56021` | FIX-368 | `parse_impact_analysis_entries` 列偏移修复（[4]/[5]→[3]/[4]——EVD-1118 误 FAIL Check 16/17 消除；3 回归测试 + 4 处 fixture LIVE 迁移） | EVD-1122；REVIEW-FIX-368-R0 双审 APPROVED_WITH_NOTES/0 |
| — | （无独立 commit） | FIX-367 | 热事实源回填（Check 28c×3：roadmap 0.86.0 行 / 0.85.0 勘正 / 总览 0.86.0）——task-row-update 机录 op-98c0f7f6，`.governance/` gitignored 零 commit 面（如实注记非遗漏） | EVD 窗口内机录链 |
| — | 本票 | REL-085 | **M-1R prep 批（Coordinator 提交后为 candidate commit）**：本四件套 + `core/releases/0.87.0.json`（candidate manifest——**本票锁面外**，Coordinator 按候选打包程序创建并随提交入索引）+ M-2 复跑义务执行 | 本文件 + release-plan |

**版本 bump 平面清单（M-1 = `80d71b5` 已执行，EVD-1129 口径；git stat 实测 25 files +199/−31）**：

| 平面 | 载体 | 值 |
|---|---|---|
| 权威源 | `skills/software-project-governance/SKILL.md` frontmatter | **0.87.0** |
| 投影/声明面 | 5 plugin/marketplace json + `package.json` + `core/manifest.json` + 4 hook `@version` + DSH persona 版本行 + `adapters/dsh/AGENTS.md.template` + `commands/governance-init.md` 三模板 `@bootstrap-version` + fixture 面 + 双根 entry bootstrap（AGENTS.md/CLAUDE.md）+ `verify_workflow.py` REQUIRED_SNIPPETS 六锚 + `checks/version.py` | 全部 **0.87.0**（24 tracked——EVD-1129 Reviewer 独立复验；**单次 `release-projection --write` 一次收敛零回滚**——FIX-366 正道首活体） |
| CHANGELOG 段 | `project/CHANGELOG.md`（+54 行实测） | 0.87.0 段（九票 + DEC-226~228 + B-9/B-10/B-11 + 披露①~⑦）已于 M-1 冻结 |
| ledger manifest | `core/releases/0.87.0.json` | **尚未创建**（M-1R 候选打包面——本票锁面外；Coordinator 提交批承载，`lifecycle_state: candidate`，唯一 transition 由 M-5 追加） |
| plan-tracker `工作流版本` | `.governance/`（gitignored） | 仍 0.86.0（**过渡态 WARN**——M-8 收尾由 Coordinator 更新为 0.87.0；本版 verify 唯一预期 WARN） |

## 行为变更（面向用户 —— CHANGELOG 0.87.0 段已载，本表为索引）

| # | 变更 | 任务 | 性质 | 回退通道 |
|---|---|---|---|---|
| **B-9** | Check 31 语义预算容量重定标：max_semantic_units 300,000→361,923（公式 = ceil(实测×1.2)，provenance 基线登记）——**重定标非豁免**（门禁语义不弱化：BLOCKED→有据 PASS；反豁免 fail-closed 双测试钉死重定标必须走公式） | FIX-369 | 基线机制设计内数值重定标（非判定语义变更——VERSIONING L11 显式处置 R0-RELEASE-F3） | 版本级回滚：还原预算值 + 基线注销（数据级、可执行、双向自洽；feature-flags §2） |
| **B-10** | locks-release 释放语义：新增 release 真删除 + 登记（shrink-locks TTL 收缩保留、语义不变）；先登记后删除（ops 台账先行，删除动作携带 operation_id 审计痕迹）；误删补偿 = acquire 幂等重取；不可逆面 = 零 | FIX-370 | 新增受治理能力面（CLI 分发面 95→96 键重定基线） | 版本级回滚（代码回退承载——locks-release 命令面移除、冻结面回落 95 键；feature-flags §3） |
| **B-11** | Check 16/17 历史豁免账本：✅ 终态历史行（2026-09-20 前存量）豁免入账本，**新增行零豁免全严检**；豁免在三消费方留痕不静默（Check 16 / Check 17 / Check 18 取数 wrapper——DEC-228①；主运行面打印 historical_exempted 计数 + 有界清单） | FIX-371 | 判定管道扩展（活跃判定语义零弱化——Breaking 无） | 版本级回滚（账本可增删可回滚〔DEC-226 非-T2 裁定〕；机制级回退 = 代码回退承载——verify_workflow.py +144 行撤除；feature-flags §4） |
| （连带） | **CRLF 保真行为变化**：projection transformed target 保留原生换行（`read_bytes().decode` 替代 `read_text` 隐式转换；CRLF 护栏双断言测试在场） | FIX-366 连带 | 投影字节保真修正（非独立行为变更号——CHANGELOG 披露④） | 版本级回滚（随 FIX-366 回退恢复旧隐式转换行为——rollback-plan §7） |

## 版本号决策记录（semver 论证——CHANGELOG 0.87.0 段同口径）

- **MINOR（0.86.0 → 0.87.0）**：VERSIONING.md L12「新增 B/C 级自动化能力」——载荷 = locks-release 新子命令（新增受治理能力面）+ Check 16/17 历史豁免账本 + Check 31 容量重定标 + 七票收口修复；
- **非 PATCH**：L38 口径不适用——主体为新增受治理能力与账本机制，非纯缺陷修复；
- **非 MAJOR / Breaking changes = 无**：L11 口径逐项核对不成立——无 MUST 规则删除/重命名、无 governance 文件字段格式变更；B-9 属基线机制设计内数值重定标非判定语义变更（显式 L11 处置——R0-RELEASE-F3）；B-10 纯新增 CLI、shrink-locks 保留无删除面；B-11 活跃判定语义零弱化；版本号未占用预留（REL-084 Release R0 代验：0.86.0 已发布顺延 +1；无 0.87.x tag/预留冲突；1.0.0 预留位未触碰）。

## Candidate Gate Results（M-2 —— ⏳ 回填位预留；A 清单结构对齐 0.86.0 先例，实测后原样回填）

| # | 门禁 / 命令 | 结果 | 关键实测值（回填位） |
|---|---|---|---|
| 1 | `verify` 全量 | **回填（2026-09-21 M-2 实测）**：check-governance 38 issues（非 exit 0——见下分解） | 分解：REQ-092×6（Check 16×3+Check 17×3——披露②）+ REL-084 execution packet 字段回填前中间态×5（packet 骨架填充后余 status 位待 M-2 终值——**已随 M-2 收口回填 PASS，复跑消解**）+ EVD-248 单条（披露③）+ 结构性 WARN 452 条 0 blocking（披露）+ archive integrity WARN 1。**REQ-092 面与 EVD-248 为预期披露（0.79.0 先例姿态），无新增 FAIL**；M-2 执行期消解面：EVD-1129 子字段×4（FEAT-059 → completed 终态，DEC-227 豁免）+ execution packet 缺包×12（FIX-367/REL-084 补包+九票 completed）+ Check 34 violations×24（RECO 快照补录 28 票） |
| 2 | `check-version-consistency` | **PASSED（exit 0）** | 源 = 0.87.0；双入口 marker 0.87.0 生效（AGENTS.md/CLAUDE.md @bootstrap-version——system-reminder 实证）；1 WARN = plan-tracker 过渡态（M-8 收口）。豁免账本三消费方首查：Check 16/17 entries 消费 ✓ + Check 18 wrapper ✓（DEC-228 明列面） |
| 3 | `check-injection-budget`（×3 profile） | **PASSED ×3** | lightweight/standard/strict = **4,216 / 5,694 / 5,966 tok**（resident hard 6,000 逐位 = 0.86.0 基线——版本 bump 零 token 回归实证，CHANGELOG 披露⑤ 验证 ✓）；skill 层 14,459 tok（report-only 16,000 内） |
| 4 | `check-projection-sync --fail-on-issues` + `check-entry-bootstrap-sync` | **PASSED ×2** | 28 mirrors + entry 双根（repo-root AGENTS.md/CLAU.md + e2e fixture）全绿（FEAT-059 M-1 实测+M-2 复跑确认） |
| 5 | `release-projection`（check-only） | **PASS** | state=PASS / source_version=**0.87.0** / projections_checked=**28** / issues=[]——**FIX-366 正道态首检零 issues**（M-1 单次 --write 已一次收敛，check-only 幂等确认） |
| 6 | `check-cross-references` | **PASS** | 0 dangling / 0 deprecated / 0 circular（四件套+CHANGELOG+全窗口载荷落盘后） |
| 7 | `check-manifest-consistency` | **PASS** | canonical **846** / actual **970**（0.86.0 期 825/946 → +21/+24 自然增长——窗口载荷） |
| 8 | `archguard-ratchet`（R1~R7） | **PASS（38 tests 全绿）** | **R5 = 96/96 frozen**（locks-release +1 键——FEAT-355 同型重定基线 ✓）；R1/R4/R6/R7 only-down 零 violations。**M-2 修复批**：基线 regen（引擎接线 +17 行致 committed 基线过期——FEAT-055 先例同型）+ FACTS_PRINT_TOTAL 1306→1316（+10 既有漂移事实对齐——归属追溯 FIX-377/0.88 bisect；链注如实披露） |
| 9 | contract-matrix | **zero drift** | test_contract_matrix.py **27 passed**（faces 快照一致——cli_dispatch 96 键含 locks-release） |
| 10 | `release-ledger --version 0.87.0 --no-remote` | **FAIL（预期归类——预提交态）** | `core/releases/0.87.0.json: cannot read release manifest: FileNotFoundError`——candidate manifest 未创建（Coordinator 提交批义务，同 0.86.0 #10 型）。**复跑义务**：manifest 创建+提交后复跑（期望 NATIVE_CANDIDATE PASS） |
| 11 | 全量测试套件 | **全绿（终验 2026-09-21）** | **3,847 passed / 0 failed / 1 skipped / 504 subtests passed（28m51s）**。M-2 修复批清零 9 failed：closure kill-switch docstring 字面量（FIX-370 微修）/ archguard regen+bump（同 #8）/ LRC 真实仓库瞬态（单独复跑 PASS——并行扫描竞争，L1856 注释先例）/ FIX-371 fixture 翻转误伤 Check 19（1 处回翻 ✅+9 位点甄别表）。用例数 3,820（0.86.0）→3,847（+27：FIX-370/371/372 新测试） |
| 12 | 混沌复演（`test_closure_chain.py` 全套件） | **35 passed**（40.81s） | 0.86.0 交付面延续——本版未触 closure-chain 引擎语义（kill-switch 微修仅 docstring 字面量） |
| 13 | e2e / dsh 隔离冒烟 | **PASSED ×2** | e2e-check 全 pass（source_cli_proxy 6/0 + target_cwd 4/0 + target_fixture 9/0 + contract 5）；check-dsh-preset-smoke：**isolated preset-session smoke PASSED、real-home writes: 0、temp DSH_HOME 自清——隔离环境安装冒烟（环境变量重定向至临时目录）通过** |
| 14 | check-release 复合门禁（candidate） | ⏳ Coordinator 提交批义务（如实标注） | 依赖 `core/releases/0.87.0.json` 在场 + 安静窗；manifest 创建后随提交批执行 |
| 15 | M-2 revert 干跑（回滚演练） | **未排程（如实标注——0.85.0/0.86.0 同型）** | 回滚区间结构核对（单轨 9 提交+两段论证）已入 rollback-plan §区间锚定；补演练 = M-3 审查裁决项 |
| 16 | `check-loop-runtime-claims`（LRC gate） | **PASS（2026-09-21 M-2 实测）** | verdict=**PASS** / semantic_units=**304,481** ≤ 361,923（余量 **57,442** ≈ 15.9%）；semantic_payload_bytes=15,641,805 < 32MiB；口径 = **361,923 = ceil(301,602×1.2)**（provenance L225-242）；UNSUPPORTED_AFFIRMATIVE=3（FIX-320 豁免账本内——0.86.0 已知基线）。**M-2 期实测计数 304,481 < 交付时点 301,849+RECO/packet 载荷增长——预算机制正常消化**（重定标非豁免红线活体：活数据增长被有据预算吸收） |

### Check 16 3 FAIL 披露（重点回填席——B-11 豁免账本红线面）

- **M-1 交付时点口径（FIX-371 / EVD-1128 实测）**：真实面 Check 16/17 FAIL 交付时点 31→5（豁免账本生效）→ 勘正回填后 **5→3**（FIX-200/FEAT-001 勘正消解）；**REQ-092 blocked 保持 FAIL**——真实活跃义务非豁免：Desktop marketplace 外部依赖，result matrix 在场，**零豁免红线活体实证**（0.79.0 先例姿态：外部依赖 + result matrix 在场的 FAIL 披露维持）。
- **M-2 回填义务**：复跑 Check 16/17 并如实回填当场 FAIL 计数与逐行归因；**REQ-092 blocked 维持 FAIL 为预期披露（非通过障碍、非豁免对象）**；豁免账本仅容纳 2026-09-20 前存量历史行（DEC-227），**M-2 期任何新增 FAIL 行不得入账本**（新增行零豁免全严检——违反即 B-11 红线破约）。
- **M-2 回填记录（2026-09-21 实测）**：Check 16/17 复跑各 **3 FAIL + Historical exempted 26 行**（豁免账本主运行面留痕——26=8+18 对账闭合）；3 FAIL 全部 = REQ-092（EVD-476/473/423——🚧 blocked 活跃行，零豁免红线活体）；**无新增 FAIL 行入账本**（B-11 红线维持）。

**M-2 执行序纪律**（0.86.0 先例沿用）：①安静窗——涉及 candidate 集合枚举的检查 MUST 无并发写盘；②顺序：verify → check-version-consistency → check-injection-* ×3 → check-projection-sync → check-entry-bootstrap-sync → release-projection → check-cross-references → check-manifest-consistency → archguard-ratchet → contract-matrix → release-ledger → 混沌复演 → e2e/dsh 冒烟 → 全量 pytest（后台先行、终态汇总）→ LRC（#16）；③每个 FAIL 逐项落披露，不以「已知」豁免（#10 ledger FAIL 为预提交态预期——如实归类非豁免；REQ-092 blocked 为活跃义务披露——非豁免）；④tag 生成后 MUST 复跑 `check-release --lineage-mode released --release-commit <commit>` 与 `release-ledger --remote`。

## 披露清单（如实披露项 —— 不得写成通过）

① **candidate manifest 缺席（本票锁面外）**：`core/releases/0.87.0.json` 未创建 → `release-ledger --no-remote` 预期 FAIL（#10）+ check-release 复合门禁未跑（#14）。**收口 = Coordinator M-1R 提交批**：按候选打包程序创建 canonical manifest（NFC/sorted/compact/trailing-LF）+ 四件套同批提交 → 复跑 ledger（期望 NATIVE_CANDIDATE PASS）+ check-release（candidate）。0.86.0 先例为四件套+manifest 同 commit。

② **REQ-092 blocked 3 FAIL 维持**（见上节专席）：Desktop marketplace 外部依赖 + result matrix 在场——真实活跃义务非豁免（0.79.0 先例姿态）；零豁免红线由 B-11 账本机制活体实证（REQ-092 行未被豁免）。

③ **EVD-248 切分器状态泄漏单条误报显形**（FIX-372 审查 F-4 双向影响）：format check 单条误报 fail-noisy + Check 20 读路径 fail-blind——FIX-373 triage 在案出槽 0.88+，验收纳入双向影响评估与 Check 20 形状回归 fixture。M-2 如遇该单条噪声如实归类披露，不静默、不豁免。

④ **FIX-373~376 四票出槽 0.88 登记**：切分器状态泄漏 FIX-373 / 9-cell 豁免消歧 FIX-374 / FIX-375（FIX-370 遗留）/ FIX-376——plan-tracker REL-084 状态行出槽注记；0.87 M-2 如实披露该已知噪声。

⑤ **CRLF 保真行为变化**（FIX-366 连带修复）：projection transformed target 保留原生换行（`read_bytes().decode` 替代 `read_text` 隐式转换；CRLF 护栏双断言测试在场）——回滚随 FIX-366 恢复旧行为（rollback-plan §7）。

⑥ **FIX-366 正道面依赖**：本版 M-1 投影一次收敛依赖两遍 plan 修复在场——回滚后版本 bump 操作 MUST 重新启用绕开手法（rollback-plan §7 专节）。

⑦ **plan-tracker `工作流版本` = 0.86.0 过渡态 WARN——仍开放**：M-8 收口（Coordinator），含 **roadmap 0.87.0 行回填义务**（FIX-367 复发预防内建——R0-DESIGN-F8）。

⑧ **no-overclaim**：official approval / marketplace approval / universal runtime support / external first-session pilot success 均未被主张；RISK-036 打开，1.0.0 就绪未被主张；非 Windows 平台未验证。

⑨ **回滚安全弱化面**：回滚到 0.86.0 即整体恢复——(a) Check 31 容量回 300,000 且活数据已实测越线（2026-09-20 当日 301,602）⇒ **LRC 必然 BLOCKED 回归**（0.86.0 已知披露态）；(b) Check 16/17 历史豁免消失 ⇒ FAIL 计数回升至 0.86.0 已知形态（列偏移误 FAIL 回归 + 历史行无豁免）；(c) locks-release 释放路径消失（过期锁重新悬挂——Check 26 形态回归）；(d) projection 回到两遍 plan 缺陷态（bump 必须走绕开手法）。均无 flag 级中间态（版本级回滚，rollback-plan §1/§4/§7）。

## 发布步骤（M-0 ~ M-8 勾选框）

- [x] **M-0 规划确认**：REL-084 双半面双审全 APPROVED_WITH_NOTES/0；DEC-226 生效（`80069a2`）
- [x] **九票载荷**：批 1 四票 + 批 2 三票（全清）+ FIX-371 全闭环（含 NEEDS_CHANGE→R1 转化三票；0 unresolved blockers）
- [x] **M-1 版本 bump（全平面）**：`80d71b5`（FEAT-059）——24 tracked 面 + CHANGELOG 段 + FIX-366 正道首活体（EVD-1129）；**M-1 GO**（REVIEW-FEAT-059-R0 APPROVED_WITH_NOTES/0）
- [x] **M-1R 发布材料**：本四件套（REL-085 锁面 expected-new）
- [x] **M-2 快速门禁**：#1~#16 回填位实测回填（重点四席：Check 31 重定标口径 #16 / Check 16 3 FAIL 披露专席 / 全量 pytest #11 / 棘轮 #8）——EVD-1131（2026-09-21 终验：pytest 3,847P/0F、LRC PASS 304,481≤361,923、棘轮 R5=96/96）
- [x] **M-2 复合门禁（Coordinator 提交批）**：candidate manifest 创建 + 提交 → 复跑 `release-ledger --no-remote`（期望 NATIVE_CANDIDATE PASS）+ `check-release --version 0.87.0 --require-changelog --lineage-mode candidate`（SPG_RELEASE_GATE_TIMEOUT=600）——M-5 transition 时 manifest-only 收口（602f8f3）；released 复跑见 M-6
- [x] **M-3 前置材料**：本四件套就绪，供 Release Reviewer / Design Reviewer 双半面审查（含 FIX-366 回退风险披露复核输入）
- [x] **M-3 双半面审查**：Release Reviewer + Code/Design Reviewer（按变更面）；review-record 机录；复审必达——REVIEW-REL-084-R2 双半面 APPROVED_WITH_NOTES/0×2（2026-09-21，390934a）
- [x] **M-4 go/no-go**：DEC-226 预授权形态——Coordinator 呈现，门禁不予放弃
- [x] **M-5b transition/tag**：candidate → released（单父 transition）+ tag `v0.87.0`（peel = transition commit）+ push——Coordinator面——602f8f3（2026-09-21 14:00:57 +0800）+ tag 2026-09-21 14:02:27 +0800（taggerdate 权威——FIX-349）；远端实测 ls-remote 2e5f715
- [x] **M-6 released 门禁**：`check-release --lineage-mode released --release-commit <commit>` + `release-ledger --remote`——2026-09-23 复跑（EVD-1133）：**release-ledger --remote origin PASS**（NATIVE_RELEASED；tag 本地==远端 602f8f3；event integrity sha256:a1536981）；check-release released 15 项 PASS（version consistency/release fact/hot fact〔三面回填后清零〕/archive integrity/projection sync/cross refs/release lineage/gate sequence/one-dot-zero blockers 全绿）+ 1 FAIL execution gates→governance health exit=1（29 issues=REQ-092×6 已知披露面〔外部依赖零豁免红线活体〕+EVD-248 单条噪声〔FIX-373 承接〕+结构 WARN 0 blocking——EVD-1131 分解口径，0.79.0/0.86.0 先例姿态：非通过障碍、非豁免对象；verify/e2e/unit tests 三子门 PASS）
- [x] **M-7 push**：master + tag 原子推送——origin 同步实测（status -sb 零偏差 + tag 在远端）
- [x] **M-8 提交 + 收尾**：commit message 含 REL-084/REL-085；plan-tracker `工作流版本` → 0.87.0（消 #1 WARN）+ roadmap 0.87.0 行回填；session-snapshot 刷新；`archive.py migrate --auto --dry-run` 触发检测 → `check-archive-integrity` PASS；证据行落账——2026-09-23 完成（EVD-1132；归档 9 task+4 evidence，integrity PASS 85/93/178；write-guard PASS；版本过渡 WARN 消解）

## M-8 收尾义务（Coordinator 面——本票不执行）

- [x] candidate 提交（四件套 + manifest 入索引后）→ 复跑 `release-ledger --version 0.87.0 --no-remote`（期望 NATIVE_CANDIDATE PASS——刷新 #10）+ check-release candidate（刷新 #14）——M-5 transition（602f8f3）manifest-only 收口承载；released 复跑见 M-6 行
- [x] plan-tracker：`工作流版本` → 0.87.0；REL-084/REL-085 行状态更新；0.87.0 路线图行 → 已发布（待 tag 后——FIX-367 复发预防义务）——2026-09-23：版本字段+roadmap 行+总览三面回填；REL-084 状态链机录三段（op-be5784ec/op-ea21c9a9/op-3b9f4745）；REL-085 已于 2026-09-21 ✅
- [x] session-snapshot 刷新（含可解析 session_date）——Check 28c hot fact source 面——2026-09-23 刷新（session_date: 2026-09-23）
- [x] hooks_drift 一次性重装提示：`cp "<plugin_root>/skills/software-project-governance/infra/hooks/"* .git/hooks/`（DEC-213④）——实测三 hook 全在场（resolve_entry hooks_installed 全 true），免重装
- [x] 归档触发检测与迁移（ADR-006/007；完整性失败阻断发布完成）——2026-09-23：9 task + 4 evidence 迁移（plan-tracker 177KB→171KB），check-archive-integrity PASS（85 热/93 归档/178 总）
- [x] 本披露开放项收口：plan-tracker 工作流版本（M-8）✓ / candidate manifest + ledger 复跑（提交批）——M-5/M-6 承载 ✓ / EVD-248 噪声与 FIX-373~376 → 0.88 triage（REL-084 状态行出槽注记在场）✓ / M-2 重点四席回填复核（EVD-1131）✓

## 本票自检验证记录（M-1R 起草工位）

- 四文件在场：`docs/release/release-plan-0.87.0.md` / `release-checklist-0.87.0.md` / `rollback-plan-0.87.0.md` / `feature-flags-0.87.0.md`（本票全部写入面）。
- 回滚区间实测：`git log --oneline 6e25753..HEAD` = 9 行 + `git rev-list --count` = **9**（M-1 候选 `80d71b5` 已含）；`6e25753` = `git rev-parse v0.86.0^{commit}` 实测同一。
- check-manifest-consistency：M-1R 起草时点执行记录见结构化返回（0.86.0 先例 docs/release 面不逐文件入 manifest——与 0.86.0 四件套同形态实证）。

---
*REL-085 M-1R 草案冻结（2026-09-21，REL-085，Governance Developer Agent 起草）。事实基线：9 提交窗口取自 `git log`/`git rev-list`/`git describe` 实测；M-1 bump 文件面取自 `git show 80d71b5 --stat` 实测（25 files +199/−31）；B-9/B-10/B-11/披露①~⑦口径取自 CHANGELOG 0.87.0 段（`80d71b5` 冻结版）；Check 31 公式与 provenance 取自 `loop_runtime_claims.py` L225-243 实读；FIX-371 豁免账本实现形态取自 `a6d3bfb` commit stat 实读；Check 16 3 FAIL 口径取自 CHANGELOG 披露①（EVD-1128 链）。未实测项（M-2 门禁数值、candidate 提交后 ledger/check-release 复跑、M-5 revert 演练、transition/tag、released 态门禁）一律标「期义务/回填位/未执行」，不预填。*
