# Release Checklist — 0.89.0（REL-090 M-1R / REL-092）

> **M-1R 草案（REL-092，2026-09-26）**——Governance Developer Agent 起草、供 Coordinator 审后随候选提交；结构与措辞对齐 `docs/release/release-checklist-0.88.0.md` 先例（REL-088，commit `a8a72a3`）。**本文件中的 M-2 数值全部为回填位预留（⏳ 标注）**——M-1R 起草时点 M-2 门禁实测尚未执行，实测后由执行工位原样回填命令输出，未实测项一律标「Coordinator 提交批义务/M-5 期义务/待回填」，不预填。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.89.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.89.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版全部验收在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）类口径下完成——**隔离环境安装冒烟（环境变量重定向至临时目录）通过**不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；do not claim 1.0.0 production-ready。
- **无激活不越权主张**：本版不主张任何 write-guard 族已 BLOCK 运行（B-12 出厂全 WARN——0.89 窗口无 `--activate-block` 执行）、不主张 decision-log JSON 权威已生效（B-13 缺省 `MD_ACTIVE` 零足迹——0.89 无真实切换）；「无新增功能激活」声明与 CHANGELOG 0.89.0 段行为变更节同口径（DEC-246⑥ 措辞收紧——行为修正三面非激活面，详见 feature-flags-0.89.0 §5）。
- **发布 tip 未生成前不预先编造**：`<发布 tip>`（M-5 transition 提交）与 tag 事实本文件不预填。
- **M-2 数值不预填**：本文件门禁表全部为回填位；任何未实测项写成通过 = 违规；census 以问题身份集合验收（非数字——DEC-246③），regen 目标/当场计数一律实测回填。

## Release Scope

| 项 | 值 |
|---|---|
| 版本号 | **0.89.0**（MINOR；semver 论证见下节） |
| 发布任务 | **REL-090（M-0 规划）/ REL-091（M-1 bump）/ REL-092（M-1R 本票）**（DEC-245 预授权链——M-1 bump 落库 `b66bd25` 后 M-1R） |
| 承载决策 | DEC-244~248（5 决策；DEC-244 范围授权〔六项+五前置核验不激活+激活票不捆绑〕/ DEC-245 执行与发布授权 / DEC-246 链首 arch 顾问咨询 Conditional GO 八条 / DEC-247 Check 30 V3 链内轮次判据 / DEC-248 FEAT-065 验收拆分〔acquire TTL 拆出 FEAT-066〕） |
| 核心范围 | **七票三批次**：批次一状态面收口 2（FIX-393/394——EVD-1172~1174）+ 批次二披露面消解检查器族 3（FIX-390/392/395——EVD-1175~1179）+ 批次三 closure 链健康面 2（FIX-391/FEAT-065——EVD-1180/1181）+ M-0（REL-090——EVD-1171）+ M-1（REL-091——EVD-1182）；完整表见 release-plan-0.89.0 §发布范围（同源 CHANGELOG 0.89.0 段——单 canonical） |
| 目标版本下不发布 | B-12 真实翻转 / B-13 真实切换（激活授权票独立决策不捆绑——DEC-244）/ FEAT-066 acquire TTL 判定面（DEC-248②——0.90 候选池）/ God Module 拆分、存储分离其余表、task_status BLOCK 机录化、FEAT-045 P-b、HotFactSource 字面量族、GOVERNANCE_SESSION_ID 复核、量测边缘+FIX-380 P2-1（DEC-244 挂起 0.90+）/ review-record --force（RISK-047 候选未排期）/ 主文件大拆解 / 任何 RISK 关闭声明 |
| 时间窗口 | 2026-09-25 v0.88.0 发布（tag 20:08:32 +0800，peel `33d19b0`）→ 09-25 DEC-244 + REL-086 M-6/M-8 收尾落盘（`2dac7af`/`9347c11`）+ REL-090 M-0 双 GO（`76c86a9`）→ 09-26 DEC-245 + 七票三批次交付（`8a94d64`..`b950fef`）+ DEC-246/247/248 + M-1 bump（`b66bd25`）→ 2026-09-26 M-1R 四件套（本票）→ M-2 实测回填（前置归档席先行）→ M-3 双审 → M-4 风险窗/go（09-30 窗纪律）/M-5+ 另记（taggerdate 权威） |
| Single-Threaded Owner | Coordinator（发布决策与 `.governance/` 写回）；M-1R 材料由 Governance Developer Agent 起草，Release Reviewer 独立审查 |
| 用户获得方式 | `/plugin update`（或 `git pull` + reload）；升级说明 MUST 携带行为修正三面（CHANGELOG 0.89.0 段行为修正节原文口径）；B-12/B-13 出厂姿态不变——「机制交付未激活」双层姿态延续（详见 feature-flags-0.89.0） |

## Change Inventory（**12 个窗口提交 — `git rev-list --count 33d19b0..HEAD` = 12，2026-09-26 实测；`git describe` = v0.88.0-12-gb66bd25 交叉印证**）

> 窗口起点前一位 `33d19b0` = `v0.88.0` tag peel（REL-086 M-5 transition 提交「0.88.0 transition candidate→released manifest-only」，tag object `82905e6`，taggerdate 2026-09-25 20:08:32 +0800 实测）。git 时间序（新→旧）；逐票关键交付与审查终态详见 release-plan-0.89.0 §发布范围 载荷表（同源 CHANGELOG 0.89.0 段），本表为窗口构成索引：

| # | commit | 任务 | 阶段/性质 | 证据 |
|---|---|---|---|---|
| 1 | `b66bd25` | REL-091 | M-1——版本 bump 0.88.0→0.89.0（24 文件面：权威锚+六锚+投影 28 面+双根 entry+CHANGELOG 单 canonical+static-pin 消解） | EVD-1182；REVIEW-REL-091-RELEASE-R0 AWN/0 |
| 2 | `b950fef` | FEAT-065 收尾 | 批次三——R0 审查报告落档 + DEC-248 version-plan §2 行 6 勘正 | EVD-1181；review-FEAT-065-CODE-R0 AWN/0 |
| 3 | `ab7a8e1` | FEAT-065 | 批次三——标准链锁腿真释放（DEC-248 链内面；四红线保持；104P→112P） | EVD-1181 |
| 4 | `c9b7415` | FIX-391 | 批次三——closure journal 版本感知读取器（REL-089 条件③消解；零写拒绝四写入口） | EVD-1180 |
| 5 | `7795f59` | FIX-395 | 批次二——Check 28c HotFactSource 终态判定对齐（20 条伪 FAIL 簇消解；R0 NC→R1 AWN） | EVD-1178/1179 |
| 6 | `65c8e4b` | FIX-392 | 批次二——Check 30 复合键判据（DEC-242③ 消解；V3 链内轮次——DEC-247） | EVD-1177 |
| 7 | `def9508` | FIX-390 | 批次二——Check 18/18b 结构化状态判据（DEC-241 消解；live 面未激活登记——EVD-1176 勘正） | EVD-1175/1176 |
| 8 | `3cb4048` | FIX-394 | 批次一——终态行文本刷新机制（13 行对齐工具面；R0 AWN→R1 APPROVED） | EVD-1173 |
| 9 | `8a94d64` | FIX-393 | 批次一——任务状态词表收敛（三解析器 committed 对齐——DEC-246① 首发集成点） | EVD-1172 |
| 10 | `76c86a9` | REL-090 | M-0——立项收口双 GO（version-plan v1.1+双审+五前置核验回填+六票入账+roadmap 行） | EVD-1171 |
| 11 | `9347c11` | REL-086 M-8 | 前版收尾——0.88.0 发布闭环（checklist M 链全勾+归档+ledger 双 PASS） | EVD-1170 |
| 12 | `2dac7af` | REL-086 M-6 | 前版收尾——release-checklist L46 勘正+projection 再收敛（LRC ragged 消解） | EVD-1170 |
| — | 本票 | REL-092 | **M-1R prep 批（Coordinator 提交后为 candidate commit）**：本四件套 + `skills/software-project-governance/core/releases/0.89.0.json`（candidate manifest——**本票锁面外**，Coordinator 按候选打包程序创建并随提交入索引）+ M-2 复跑义务执行 | 本文件 + release-plan |

**版本 bump 平面清单（M-1 = REL-091 已落库 `b66bd25`——EVD-1182/REVIEW-REL-091 实测口径）**：

| 平面 | 载体 | 值 |
|---|---|---|
| 权威源 | `skills/software-project-governance/SKILL.md` frontmatter | **0.89.0** |
| 投影/声明面 | 5 plugin/marketplace json + `package.json` + `core/manifest.json` + 4 hook `@version` + dsh persona 版本行 + `adapters/dsh/AGENTS.md.template` + `commands/governance-init.md` 三模板 `@bootstrap-version` + fixture 面 + 双根 entry bootstrap（AGENTS.md/CLAUDE.md）+ `verify_workflow.py` REQUIRED_SNIPPETS 六锚 + `checks/version.py` | 全部 **0.89.0**（28 投影面——written=17 版本承载写入面 + 11 幂等 byte_copy 镜像；check 模式 28/28 PASS 零 issue——REVIEW-REL-091 §1 #1/#3 亲证口径） |
| CHANGELOG 段 | `project/CHANGELOG.md` | 0.89.0 段（七票 + DEC-244~248 + 行为修正三面 + 披露①~⑤）已于 M-1 交付——**单 canonical**（DEC-242① 0.88 M-3 裁决直接继承，根 `changelog.md` 不复刻双位、不再同步——RELEASE-R0 P2-1 收口授权形态） |
| static-pin 账本 | `checks/version.py` STATIC_PIN_EXEMPTIONS 等 | **已消解**（M-1）：删 4 self-dormant（0.88.0 bump-time rows——fixture 行本体不动）+ 登记 9 bump-time rows（test_fix390×3/test_fix393×4/test_fix394×2——fixture 行模板/表场景载荷面）+ 保留 2 dormant FUTURE_TARGET（test_release_projection.py L30/test_static_version_pins.py L158）；test_fix395 L19 0.89.0 token 在模块 docstring 内——扫描器注释面按设计跳过零 WARN；M-2 复核期望 0 WARN |
| ledger manifest | `skills/software-project-governance/core/releases/0.89.0.json` | **尚未创建**（M-1R 候选打包面——本票锁面外；Coordinator M-5 提交批承载，`lifecycle_state: candidate`，唯一 transition 由 M-5 追加） |
| plan-tracker `工作流版本` | `.governance/`（gitignored） | 仍 0.88.0（**过渡态 WARN**——M-8 收尾由 Coordinator 更新为 0.89.0；本版 verify 唯一预期 WARN——CHANGELOG 披露④） |

## 行为变更（面向用户 —— 本版**无新增功能激活**；行为修正三面索引 —— CHANGELOG 0.89.0 段行为修正节同口径）

| # | 变更 | 任务 | 性质 | 回退通道 |
|---|---|---|---|---|
| 行为修正① | **FEAT-065 gate 闭集替换**：closure gate kind lock_ttl_le→task_locks_released——自定义 spec 链声明 lock_ttl_le 自 0.89.0 起 **fail-closed 拒绝**（闭集纪律，非静默降级）；lock_ttl 死默认输入移除；shrink-locks 步升级 release-locks 真释放 | FEAT-065 | 治理判据/锁生命周期行为修正（**非新增功能激活**——DEC-246⑥） | 版本级回滚 = 还原 `closure_chain.py` + `tests/test_closure_chain.py` 两文件（DEC-248① 锁面——rollback-plan-0.89.0 §1；注意与 FIX-391 同文件——整窗 revert 按区间回退，不做单票选择性还原） |
| 行为修正② | **FIX-391 零写拒绝面**：旧版读取器对新版/未知 journal 事件的语义误读与 seq 碰撞双向量由人工处置路径变为写入口零写拒绝——正常链路零感知（兼容矩阵实证不误拒）；跨版本 in-flight closure resume 会 digest 失配拒绝（会话内运营态无跨版本 resume 契约） | FIX-391 | 恢复安全行为修正（非激活面） | 版本级回滚 = `closure_chain.py` 还原（与行为修正①同文件如实注记）；回退后人工处置路径回归——rollback-plan-0.88.0 §8 运行手册门禁仍有效；路径 B backport 候选保留 |
| 行为修正③ | **判据收敛面（不放宽）**：FIX-393/394/395 终态/非终态/未知 token 判据收敛不放宽、不绕过 FIX-390 证据检查（DEC-246① 退出条件）；误推荐/伪 FAIL 消失属判据修正非检查弱化 | FIX-393/394/395 | 治理判据行为修正（非激活面） | 版本级回滚 = 对应文件还原（误推荐/伪 FAIL 簇回归为 0.88 已知态——rollback-plan-0.89.0 §1，如实预期非回滚失败） |
| （沿承） | B-12/B-13/B-14 机制面 0.88 已交付——**0.89 出厂姿态零变化**（全 WARN / MD_ACTIVE / 纯新增能力维持） | —（无 0.89 激活动作） | 无新增行为变更号（B-x 序列止于 B-14——feature-flags-0.89.0 §7） | 引用不触发（rollback-plan-0.89.0 §7——0.88 版回退预案既有条目） |

## 版本号决策记录（semver 论证——CHANGELOG 0.89.0 段同口径）

- **MINOR（0.88.0 → 0.89.0）**：version-plan-0.89.0（M-0 双 GO——AWN/0×2 终态）——载荷 = 治理精度与健康面收口批（解析判据收敛 / 检查器结构化 / 门禁自动化 / 锁腿真释放）；含新增门禁面（FIX-391 零写拒绝 / FEAT-065 task_locks_released 后置条件 gate），非纯 bug fix；
- **非 PATCH**：主体为判据语义精确化 + 恢复安全自动化 + 锁腿真释放升级，非缺陷修单；
- **非 MAJOR / Breaking changes = 无**：无 MUST 规则删除/重命名、无外部 CLI 契约变更、无 governance 文件字段格式变更；FIX-391/FEAT-065 新增拒绝面均属 fail-closed 门禁而非既有契约删除（自定义 lock_ttl_le spec 声明被拒 = 行为修正①闭集纪律）；判据收敛不放宽；版本号未占用预留（0.88.0 已发布顺延 +1；无 0.89.x tag/预留冲突；1.0.0 预留位未触碰）。

## Candidate Gate Results（M-2 —— ⏳ 全部回填位预留；A 清单结构对齐 0.88.0 先例 + version-plan §4/§9 增量面）

| # | 门禁 / 命令 | 结果 | 关键实测值（回填位） |
|---|---|---|---|
| 1 | 全量测试套件（M-2 一次预算） | ✅ **4217P/8F/1S + 556 subtests（1191.45s，2026-09-26 实测）** | 8F 分解：archguard×3（R1/R7/CliGate——专席② regen+pin 再基线后复跑 **38/38P 消解**）+ loop/FIX300×5（既有基线：loop×3〔inventory/performance/adapter〕+FIX300×2——三轮 stash 实证链在案〔session-snapshot 0.89 链首〕，非 0.89 窗口引入）；净新增 **+98**（4119→4217——DEC-246⑦ 七票并入口径）；0 窗口引入 F |
| 2 | `verify` 全量 | ✅ **PASSED** | 唯一 WARN = plan-tracker 工作流版本 0.88.0 过渡态（L60/披露④设计态维持——M-8 收口） |
| 3 | `check-version-consistency` | ✅ **PASSED** | source=0.89.0；双入口 marker 0.89.0；静态钉面 **0 WARN**（M-1 消解后复核达成）；过渡态 WARN 为设计态非缺陷 |
| 4 | `check-injection-budget`（×3 profile） | ✅ **三档全 PASS** | lightweight **4216** / standard **5694** / strict **5966** tok ≤ 6000；版本 bump 零注入面变化（对称面如实注记） |
| 5 | `check-projection-sync --fail-on-issues` + `check-entry-bootstrap-sync` + `release-projection`（check-only） | ✅ **全 PASS** | projection-sync PASSED + entry-bootstrap-sync PASSED + release-projection **state=PASS / source_version=0.89.0 / issues=[]**（M-1 已实测——M-2 复跑确认一致） |
| 6 | `check-cross-references` | ✅ **PASS** | 0 dangling / 0 deprecated / 0 circular（四件套+载荷全窗口落盘后复跑） |
| 7 | `check-manifest-consistency` | ✅ **PASS** | Manifest and filesystem are consistent（917 canonical/1055 actual 对账——docs/release 面不逐文件登记，0.87/0.88 先例同形态） |
| 8 | `archguard-ratchet`（R1~R7） | ✅ **sanctioned regen 完成——R1~R7 PASS（0 violations）** | 锚 **26193→26358**（+165 归因链：EVD-1176 +125〔FIX-393/394 +39+FIX-390 +86〕+窗口后续 +40〔FIX-392/395 消费面+REL-091 六锚〕——非静默清零）；R4 1318=1318；R5 **97/97+71/71** frozen；R7 committed==fresh True；test_archguard_ratchet **38/38P**（metadata pin 再基线 26193→26358——501d8dc 先例同型义务）；only-down 从 26358 起 |
| 9 | contract-matrix | ✅ **zero drift** | cli_dispatch **97 键** frozen 维持（R5 承载：97/97 keys+71/71 segments——DEC-239⑥ 收口面延续） |
| 10 | `release-ledger --version 0.89.0 --no-remote` | ✅ **PASS（M-5 后刷新）** | M-5a candidate `02d618d` → **NATIVE_CANDIDATE PASS**；M-5b transition `8eb5efb` → **NATIVE_RELEASED**（event rel090-transition integrity sha256:7c43df0a）；M-6 `--remote origin` **PASS**（tag_facts local==remote==8eb5efb） |
| 11 | e2e / dsh 隔离冒烟 | ✅ **全 pass** | e2e-check：source_cli_proxy 6/0 + target_cwd 4/0 + target_fixture 9/0 + contract 5/0；**隔离环境安装冒烟（环境变量重定向至临时目录）通过**——launch.py --install 渲染 $tmpHome\.agent-presets\governance（版本标记 0.89.0/preset.yml/agent.cordis.yml）；**real-home writes: 0**（真实 .agent-presets 不存在——隔离生效实证）；临时目录已清理 |
| 12 | **组合测试集四项**（version-plan §9——M-2 必查席） | ✅ **122P + 23 subtests（11.38s）** | ①393×394 状态闭环+②390×392 互不回归+③391×065 链健康+④393 archive 腿：fix390~395+ReleaseLocks+task_row_update 全套件绿（-k 选择实跑）；④命令面 `check-archive-integrity` **PASS**（1,297 索引/178 任务）+ `migrate --auto --dry-run` 判据一致（FIX-393 committed 词汇——50 扫描/0 满足归档）；**专席⑥ 三票共面**（FIX-393 verify_workflow.py 腿×FIX-390 三态×FIX-392 复合键）同窗绿——互不踩实证 |
| 13 | **check-governance census 对账席**（专席①） | ✅ **39 issues 分段全枚举入 EVD** | 身份集=REQ-092×6+EVD-1146×1（披露席位维持）+REL-090 in-flight 合同×4（18d/e/f/g——M-8 终态消解）+accounting ragged×3+Check 28s ERROR×1；archguard×2 随 regen 消解；49→51→39 时点归因（含 Step D 过早翻转 28c×2 瞬态引入→回滚消解过程事件）入 EVD；**18/18b live PASS**（in-window entries 0——DEC-241 例外两行不在当前窗口重现；P3-4 键控缺陷本测点不复现，如实记录） |
| 14 | **Check 28s 前置归档席**（专席③——DEC-246④ 方案 A） | ◐ **方案 A 执行=dry-run 无可归档数据** | `migrate --auto --dry-run`：50 tasks 扫描/结构可解析 48/**满足归档条件 0**（保留 48——already_archived=1/out_of_range=44/status_not_archivable=3）+evidence 488/478 保留（live_or_unresolvable=312 等）→**迁移跳过零写**；终值 **1,763,887B/1,437 行（1722.5KB）——ERROR 维持如实披露**；M-8 复测义务保留，不虚报消解 |
| 15 | **FEAT-065 双面演示席**（专席⑤——DEC-248④） | ✅ **两面分别完成** | 面 A 正常收口 **5P**（真释放接线/释放前 acquire 拒绝→释放后成功/后继锁不被误删/operation-id 受控重试/披露+串行隔离）∥ 面 B 拒绝+受控恢复 **3P**（仍持锁 TTL 小→gate 拒绝/索引清但残留文件锁→拒绝/释放失败不可读→链停）——真实 governance_store CLI+临时 store 零 mock，两面命令输出分别留 EVD |
| 16 | check-release 复合门禁（candidate→released 两态） | **M-5 批承载**（M-2 时点 NOT_RUN 如实） | candidate 态 = M-5 批执行（依赖 manifest 在场）；released 态 = M-6 批；**quality-tools 未安装记 NOT_RUN 不虚报** |
| 17 | M-2 revert 干跑（回滚演练） | **未排程维持**（0.85/0.86/0.87/0.88 四版先例同型——批内无演练票）——M-3 发布半面裁决：不排程不阻断（tip 未定先干跑无意义）；rollback-plan-0.89.0 §4 如实标注 + §8 两路径手册在场 | 若补演练 MUST 隔离副本执行 + 真实 `<发布 tip>` 生成后复跑 |

### 专席① —— check-governance census 对账席（REVIEW-REL-091-RELEASE-R0 P2-1：51 vs 49 分段归因入 EVD）

- **事实链**：EVD-1182 申报「check-governance 49=49 持平（基线实为 49 非 50——EVD-1179 FIX-395 R1 后 WARN 面收敛）」；REL-091 Release Reviewer 同日实测 **51 issues**（exit 0）——差值 +2 无法归因到 bump 24 文件面；全部可见 issue 族落在在案披露（REQ-092×6+EVD-1146×1）/在途任务合同（REL-090/091/092 短包 in-flight FAIL 族）/常设 ERROR（Check 28s 体积）/accounting ragged 行；**时点因素**：49 测量后 EVD-1182 本行才落行（申报原文自证「commit 尝试被拦截——本行即补」），其后唯一 `.governance` 变更即该 append。P2-1 处置建议 = M-2 门禁实测以 census 分段计数逐条对账，把 49→51 差值归因入 EVD（本席承载义务）。
- **M-2 回填义务**：`check-governance --fail-on-issues` **分段计数逐条对账**（REQ-092×n / EVD-1146×1 / 在途任务合同族 / Check 28s 体积 ERROR / accounting ragged / 其余各族当场值逐段列示）；49→51 差值逐条归因入 EVD；P3-2 申报纪律改进随行——EVD 引用 census 计数时**附 census 分段快照**（各族计数），使跨时点复审可做精确差值归因。
- **身份集验收口径（DEC-246③）**：census 以问题身份集合验收（非数字）——收窄形态 = REQ-092×n + EVD-1146×1（REQ-092 外部依赖零豁免红线维持、EVD-1146 superseded 残留维持披露 DEC-227 路线 a）；本版承诺未消解或新增未授权阻断项**不得仅凭披露放行**；跳检/扩豁免/降级式收窄 = 阻断；修复揭露被伪像遮蔽的真实缺陷按影响分级。FIX-390/392 例外面（DEC-241×4 + V3×5）活体确认与 18/18b live 复测联动（专席④）。

### 专席② —— archguard sanctioned regen 席（EVD-1176 路由——0.88 M-2 先例 commit `501d8dc`）

- **存量事实**：引擎现值 **26318 LOC 超锚 26193**（+125——EVD-1176 归因链：HEAD 既有 +39〔FIX-393/394 集成〕+ FIX-390 +86）；处置路由 = 随 0.89 M-2 **统一 sanctioned regen**（0.88 M-2 先例 commit `501d8dc` sanctioned regen 同型——FEAT-055 先例链）；**载荷票未完不中途 regen**（七票已集成——前置条件已满足）；archguard 三连红为 M-2「全绿」口径前置义务。
- **M-2 回填义务**：R1~R7 全量结果 + regen 前后计数如实回填；**regen 时 MUST 附归因链留档（EVD-1176），不得静默清零**；only-down 面（R1/R4/R6/R7）regen 后零 violations 期望；R5 期望 97/97 维持（DEC-239⑥ registry 收口面延续）；**regen 目标值待实测——不预填**。

### 专席③ —— Check 28s 前置归档席（DEC-246④ 方案 A——六票集成后、M-2 前）

- **存量事实**：Check 28s ERROR 维持——M-0 期 1690.6KB（version-plan §4.5）→ REL-091 审查时点 1719.5KB（P2-1）→ 本票起草实测 **1,761,442B ≈ 1720KB**（2026-09-26；1,434 行——历史行承载）；0.87/0.88 先例同型警示（0.88 M-8 归档后仍 1690.6KB 量级——版本窗口行绑定下归档周期）。
- **处置裁定（DEC-246④）**：采**方案 A**——六票集成后、M-2 前**前置历史证据归档**：已封闭历史周期迁移 + 当前链活跃证据保留 + 引用/索引连续性验证 + M-3~M-8 余量；M-8 保留本轮周期归档收口（version-plan §3b/§4.5 复测位不取消）。
- **M-2 前执行序（fail-closed）**：① `archive.py migrate --auto --dry-run` **先行**（dry-run 先行——禁直接迁移）；② 核对 dry-run 迁移范围 = **已封闭历史周期**（当前链〔0.89.0 M-1R/M-2/M-3 起〕活跃证据必须保留在场——若 dry-run 范围含活跃链行，**停止并上报 Coordinator**，不得带活跃证据归档）；③ 执行迁移；④ **引用/索引连续性验证**：`check-archive-integrity` PASS + `check-cross-references` 复跑（归档 index 可解析）+ 抽样归档行按 archive/index.md 可回读；⑤ 确认 M-3~M-8 余量（evidence-log 当场体积如实回填本席）。
- **验收措辞纪律**：本席结果如实回填当场值——禁以「预计消解」措辞预填；若方案 A 执行后 Check 28s 仍 ERROR（如未达阈值），如实披露并维持 M-8 复测义务，不虚报消解。

### 专席④ —— 窗口激活后 18/18b live 复测席（EVD-1176 P3-4）

- **事实链**：FIX-390 机制消解在 **fixture 面**红绿实证（19F→18P+11 subtests；0.88 例外两行 EVD-1140/EVD-1164 活体形状复现）；**live 面 Check 18/18b 入集 = 0**——窗口键控取 0.77 时代 token（既有缺陷 P3-4），0.89.0 窗口未激活 ⇒ live census 75→75 逐字节零增量（EVD-1176 勘正——EVD-1175 申报「75→73」不可复现已勘正）；M-2 窗口激活后复测义务路由至本席（EVD-1176 P3-4 原文）。
- **M-2 回填义务**：0.89.0 窗口激活后复测 Check 18/18b live 面——期望 = DEC-241 例外两行（EVD-1140/EVD-1164）live 活体转绿 + 专席① census 分段对账联动；结果如实回填（含当场窗口键控取值说明）；**若 live 面仍不激活，缺陷 P3-4 如实披露并路由后续票，不得以 fixture 面绿冒充 live 绿**（fail-closed——M-3 审查复核）。

### 专席⑤ —— FEAT-065 双面演示席（DEC-248④）

- **拆分边界（如实注记）**：FEAT-065 已按 DEC-248 拆分——本版交付 = **标准链锁腿真释放链内面**（release-locks 接线 + task_locks_released gate + 三处披露勘正 + lock_ttl 死输入移除）；acquire TTL 判定面拆出 **FEAT-066**（0.90 候选池，depends_on=FEAT-065）——**本票发布验证不得按原票面（含 acquire TTL）宣称完成**（DEC-248④ 原文）。
- **双面演示义务（两面分别演示不混一）**：
  - **面 A（正常收口后继票可获取）**：标准链收口 → release-locks 真释放 → 任务索引清理 + 文件锁归属扫描双面通过（task_locks_released gate PASS）→ 同文件族下一票不再撞人工解锁步；
  - **面 B（中断遗留锁明确拒绝 + 受控恢复指引）**：中断遗留锁场景 → gate 明确拒绝（fail-closed）→ 呈现受控恢复指引——人工恢复受控流程 = 确认旧执行者停止 → 按 task+operation 标识释放 → 核验索引；**禁批量清锁**（DEC-248④）。
- **四红线保持验证**（DEC-248③——各配集成级测试实证在案 EVD-1181，M-2 活体复确认）：释放前同文件互斥不放松 / 只释放本任务拥有的锁（禁按路径无条件删除）/ 释放后不再修改受锁保护文件 / 提交串行隔离成立。
- **M-2 回填义务**：两面演示命令与输出如实回填（两面分别留 EVD）；任何一面缺失 = 本席未完成，不得以单面通过冒充双面完成。

### 专席⑥ —— 组合②列补充席（F-1：覆盖 FIX-393 verify_workflow.py 腿）

- **事实链（version-plan §2 批次间全局串行约束 F-1 收口落字）**：`verify_workflow.py` 共面票实为**三票**（FIX-390 / FIX-392 / FIX-393——FIX-393 files 含 verify_workflow.py，triage conflicts 互列）；批次一 FIX-393 的 verify_workflow.py 腿与批次二两票**跨批次同文件串行**（派发锁 + 同文件串行红线既有纪律兜底）；原文落字「M-1R checklist 须为组合②列补充席（覆盖 393 的 verify_workflow.py 腿）」——本席即该义务承载。
- **M-2 回填义务**：组合②标准席（FIX-390×FIX-392 互不回归）之外，**补测 FIX-393 verify_workflow.py 腿在两票落地后的共存面**——三票共面判据互不回归（FIX-393 committed 谓词复用面 × FIX-390 三态判据 × FIX-392 复合键视图同文件无互踩）；9-cell 列数契约零触碰判据随行确认；结果并入 #12 组合测试集回填，独立留证。
- **DEC-246⑤ 判据要点并入**：393×390 状态证据正交（终态不替代证据——组合②邻接面）；392×390 身份归属（复合键不跨链跨轮借用）；FIX-394 运行时机制与 13 行数据对齐分开验收 + 19 条发现→13 行映射凭证（EVD-1174 在案——M-3 抽查输入）。

**M-2 执行序纪律**（0.88.0 先例沿用 + 本版增量）：①安静窗——涉及 candidate 集合枚举的检查 MUST 无并发写盘；②顺序：**前置归档席（专席③——M-2 门前）** → verify → check-version-consistency → check-injection-budget ×3 → check-projection-sync → check-entry-bootstrap-sync → release-projection（check-only）→ check-cross-references → check-manifest-consistency → archguard-ratchet（专席② regen）→ contract-matrix → release-ledger（#10）→ 组合测试集四项 + 补充席（#12/专席⑥）→ census 对账席 + 18/18b live 复测（#13/专席①④）→ FEAT-065 双面演示（#15/专席⑤）→ e2e/dsh 冒烟（#11）→ 全量 pytest（后台先行、终态汇总——#1 M-2 一次预算）→ LRC 复算 → Check 28s 复测；③每个 FAIL 逐项落披露，不以「已知」豁免（#10 ledger FAIL 为预提交态预期——如实归类非豁免；REQ-092/EVD-1146 为活跃义务/残留披露——非豁免）；④tag 生成后 MUST 复跑 `check-release --lineage-mode released --release-commit <commit>` 与 `release-ledger --remote origin`（M-6 预推校验；UNKNOWN/BLOCKED 不得包装为 PASS——DEC-246⑧ 绑定核验随行）。

## 披露清单（如实披露项 —— 不得写成通过）

① **candidate manifest 缺席（本票锁面外）**：`skills/software-project-governance/core/releases/0.89.0.json` 未创建 → `release-ledger --no-remote` 预期 FAIL（#10）+ check-release 复合门禁未跑（#16）。**收口 = Coordinator M-5 提交批**：按候选打包程序创建 canonical manifest（NFC/sorted/compact/trailing-LF）+ 四件套同批提交 → 复跑 ledger（期望 NATIVE_CANDIDATE PASS）+ check-release（candidate）。0.88.0 先例为四件套+manifest 同 commit。

② **REQ-092×n + EVD-1146×1 维持**（见专席①）：REQ-092 = 外部依赖零豁免红线活体（非豁免——非本版范围）；EVD-1146 = 不合格首写历史行不动+披露（EVD-1147 合格重写——DEC-227 路线 a）；census 49→51 差值归因义务在专席①（P2-1）；两成分均不得入 B-11 豁免账本。

③ **FIX-390 live 面 0.89.0 窗口未激活**（见专席④）：机制消解 fixture 面闭环、live 面窗口键控待 M-2 激活后复测（EVD-1176 P3-4——既有缺陷 P3-4 如实路由）；禁以 fixture 面绿冒充 live 绿。

④ **archguard 26318 超锚 26193**（见专席②）：M-2 sanctioned regen 承载（0.88 M-2 先例 `501d8dc` 同型）；regen 前三连红如实呈现——为 regen 前置义务非放行阻断。

⑤ **Check 28s ERROR 维持 ~1720KB**（见专席③）：DEC-246④ 方案 A 前置归档承载 + M-8 复测消解有效性确认（version-plan §4.5）；方案 A 执行结果如实回填，不预填消解。

⑥ **plan-tracker `工作流版本` = 0.88.0 过渡态 WARN——仍开放**：M-8 收口（Coordinator）——`工作流版本` → 0.89.0 + **roadmap 0.89.0 行回填义务 + REL-090 任务行终态回填义务**（FIX-367 复发预防内建）+ Check 28s 复测（version-plan §4.5）。

⑦ **09-30 风险窗履行——本 M-1R 时点尚未履行，无预填未生成事实**：RISK-036/039/046 复评 + RISK-047/048 同窗观察义务在案（DEC-244 必选项；version-plan §6 时序纪律——不迟于 2026-09-30；M-4 消费其结论，若 M-4 晚于窗口则窗内独立先行入账——DEC-243 先例形态）；履行结论属 M-4 裁决面，本票零预填。

⑧ **static-pin 账本已消解（REL-091——M-1 期）**：删 4 self-dormant + 登记 9 bump-time rows（fixture 行模板/表场景载荷面逐行归因）+ 保留 2 dormant FUTURE_TARGET；M-2 复核期望 0 WARN（REVIEW-REL-091 §1 #6 逐行核对在案）。

⑨ **no-overclaim**：official approval / marketplace approval / universal runtime support / external first-session pilot success 均未被主张；RISK-036 打开，1.0.0 就绪未被主张；非 Windows 平台未验证；RISK-050（10-31）维持打开；RISK-059（B-13 前置三缺口）打开——激活授权票前置。

⑩ **回滚安全弱化面**：回滚到 0.88.0 即整体恢复——(a) FIX-391 零写拒绝面消失（closure journal 误读向量防线回退为 rollback-plan-0.88.0 §8 人工运行手册门禁——如实披露）；(b) FEAT-065 真释放面消失（shrink-locks TTL 收缩伪释放回归——DEC-248① 拆分前形态）；(c) 判据收敛面消失（tpa 误推荐/13 行滞留/热事实源伪 FAIL 簇回归——0.88 已知缺陷态）；(d) FIX-392 链内轮次判定回全局轮号（V3 键控伪像复发——DEC-242③ 例外面复活）；(e) FIX-390 结构化判据消失（Check 18/18b 假 FAIL 形态回归——DEC-241 例外重新在场）。均如实预期非回滚失败（rollback-plan-0.89.0 §1/§4）。

## 发布步骤（M-0 ~ M-8 勾选框）

- [x] **M-0 规划确认**：REL-090 双半面 GO（Design R0 AWN/0 + Release R0 AWN/0——F-1~F-6 收口落字；五前置核验回填完成——`76c86a9`，EVD-1171）
- [x] **七票载荷（三批次）**：批次一 FIX-393→FIX-394 + 批次二 FIX-390/392/395 + 批次三 FIX-391→FEAT-065 全部交付闭环（EVD-1172~1181；审查终态全 AWN/APPROVED——FIX-395 R0 NC→R1 AWN；0 unresolved blockers）
- [x] **M-1 版本 bump（全平面）**：REL-091——28 投影面 + CHANGELOG 0.89.0 段单 canonical + static-pin 消解（已落库 `b66bd25`；出口四项 PASSED——REVIEW-REL-091-RELEASE-R0 AWN/0，EVD-1182）
- [x] **M-1R 发布材料**：本四件套（REL-092 锁面 expected-new）——已交付（bb6a460 + R0 RELEASE AWN/0，EVD-1183）
- [x] **M-2 门禁实测**（2026-09-26 回填完成）：#1~#17 全席实测回填——前置归档席（专席③）dry-run 无可归档数据（零写跳过）；census 对账席（专席①——39 issues 分段全枚举+49→51→39 归因）/ archguard 棘轮席（专席② regen 26193→26358+pin 再基线 38/38P）/ 18-18b live 复测席（专席④ PASS）/ FEAT-065 双面演示席（专席⑤ 5P∥3P）/ 组合②列补充席（专席⑥ 同窗绿）+ 组合测试四项（#12 122P）+ 全量 pytest（#1 4217P/8F——archguard×3 随 regen 消解+loop/FIX300×5 既有基线披露）；**LRC 复算：BLOCKED（semantic_only）——容量 330,494≤361,923 达标，UNSUPPORTED_AFFIRMATIVE×3 全部位于 legacy review-FIX-300-CODE-R0.md（既有基线面，非 0.89 窗口触碰）如实披露**；#10 ledger 预期 FAIL（M-5 收口）/#16 check-release M-5 承载（NOT_RUN 如实）；**过程事件如实注记**：Coordinator 曾于 M-1 后过早将 plan-tracker 工作流版本翻至 0.89.0（违反 L60 M-8 时序设计）→ 触发 28c×2 瞬态 FAIL → 当场定位根因（release_delivered 判定 vs tag 未生成的链中双束缚）→ 已回滚恢复设计过渡态并复测 28c synchronized——教训入 EVD（发布材料时序纪律：M-8 面收口不得提前）
- [ ] **M-3 双半面审查**：产品代码半面（Code Reviewer 链）+ 发布半面（Release Reviewer 链）；终态口径 APPROVED / AWN-0；**抽查义务：FIX-390/392 红侧 fixture 非预录形态**（DESIGN-R0 F-6）+ 批次一中间态独立 EVD 抽查（F-5）+ 19→13 映射凭证复核（EVD-1174）
- [x] **M-4 修复窗 + 风险窗履行 + go/no-go**（2026-09-26）：DEC-249 有条件 GO（arch 意见采纳——GO-WITH-CONDITIONS+六条件口径收紧）+DEC-250 勘正；09-30 风险窗履行入账（036 维持/039 收窄/**046 关闭**/047·048 维持观察——EVD-1185）；legacy 5F 披露发布口径（身份级例外清单）
- [x] **M-5 checklist 全席回填 + candidate 提交 + transition**（2026-09-26）：manifest 两步落库——M-5a candidate（`02d618d`，ledger **NATIVE_CANDIDATE PASS**）→M-5b transition manifest-only（`8eb5efb`，rel090-transition 事件 integrity sha256:7c43df0a；m4_authorization=DEC-245 预授权+DEC-249 有条件 GO；ledger **NATIVE_RELEASED**）；TO_BE_DEFINED=0；DEC-246⑧ 绑定核验（candidate_commit 02d618d/release_commit 8eb5efb 双锚）
- [x] **M-6 预推校验**（2026-09-26，tag 后复跑）：check-release released 模式——release lineage **PASS**（local tag 54362a9→peel 8eb5efb；remote origin tag 一致）；release-ledger `--remote origin` **PASS**（NATIVE_RELEASED；tag_facts local==remote==8eb5efb）；**唯一剩余 FAIL=loop runtime claim gate（DEC-249③ 身份级披露例外——semantic BLOCKED+3 ragged 身份=legacy review-FIX-300 面，发布说明不称全绿）**；UNKNOWN/BLOCKED 零包装
- [x] **M-7 tag+push**（2026-09-26，DEC-245 预授权）：annotated tag `v0.89.0`（tag object 54362a9，peel=transition 8eb5efb，taggerdate 权威）；master（76c86a9..8eb5efb）+tag 原子推送 origin——ls-remote 逐一精确一致
- [x] **M-8 归档 + 收尾**（2026-09-26）：前置归档扩展窗执行（M-5b transition 后范围 v0.1.0~v0.88.0：27 tasks+27 evidence 迁移，check-archive-integrity PASS 178 任务；plan-tracker 195→175KB/evidence-log→1,715,707B）；Check 28s 复测 **ERROR 维持如实披露**（阈值 250KB vs 1,715,707B——453 行结构性保留〔live_or_unresolvable=314 等〕；下归档周期消解——0.87/0.88 先例同型）；plan-tracker `工作流版本`→0.89.0+roadmap 行已发布+REL-090 终态回填；session-snapshot 刷新

## M-8 收尾义务（Coordinator 面——本票不执行）

- [ ] candidate 提交后复跑：ledger NATIVE_CANDIDATE→released PASS（#10 刷新）+ check-release candidate 面已知披露位（#16 刷新）
- [ ] plan-tracker：`工作流版本` → 0.89.0；REL-090/091/092 行状态更新；0.89.0 路线图行 → 已发布（待 tag 后——FIX-367 复发预防义务）
- [ ] session-snapshot 刷新（M-8 批执行）
- [ ] 归档触发检测与迁移（dry-run 先行；**Check 28s 复测消解有效性确认**——version-plan §4.5 + 专席③ 执行后当场值；归档完整性失败 → 发布收尾 MUST 阻断——无可归档数据则跳过并如实注记）
- [ ] 本披露开放项收口：plan-tracker 版本 ✅（M-8）／candidate manifest+ledger ✅（M-5/M-6）／REQ-092+EVD-1146 维持披露 ✅（零豁免红线——持续）／live 18/18b 复测结论 ✅（M-2 专席④——若 P3-4 未消解路由后续票）／09-30 风险窗履行 ✅（M-4）

## 本票自检验证记录（M-1R 起草工位）

- 四文件在场：`docs/release/release-plan-0.89.0.md` / `release-checklist-0.89.0.md` / `rollback-plan-0.89.0.md` / `feature-flags-0.89.0.md`（本票全部写入面）。
- 回滚区间实测：`git log --oneline 33d19b0..HEAD` = 12 行 + `git rev-list --count` = **12**（HEAD `b66bd25` 已含）；`33d19b0` = `git rev-parse v0.88.0^{}` 实测同一；`git for-each-ref refs/tags/v0.88.0` 实测 tag object `82905e6` / taggerdate 2026-09-25 20:08:32 +0800。
- B-12/B-13 姿态面：0.89 窗口零触碰（REL-091 24 文件面核实不含 posture/state 文件——REVIEW-REL-091 §2 全清单）；机制通道面沿用 0.88 版实读锚（`write_guard_state.py` POSTURE_CONFIG_FILE_NAME / `decision_repository.py` AUTHORITY_STATE_FILE / `decision_migration.py` argparse 子命令面——本票零改动，M-2/M-3 如需引用以当场实读复核为准）。
- check-manifest-consistency / check-cross-references / check-version-consistency：M-1R 起草时点执行记录见结构化返回（0.88.0 先例 docs/release 面不逐文件入 manifest——与 0.87.0/0.88.0 四件套同形态实证）。
- **quality-tools：未安装——按 version-plan §4.6 记 NOT_RUN 不虚报**（check-release quality-tools 结构化记录面——M-5/M-6 批执行时如实记录，禁以 NOT_RUN 冒充 PASS）。

---
*REL-092 M-1R 草案冻结（2026-09-26，REL-092，Governance Developer Agent 起草）。事实基线：12 提交窗口取自 `git log`/`git rev-list`/`git describe`/`git rev-parse v0.88.0^{}`/`git for-each-ref` 实测；七票载荷、行为修正三面、披露口径取自 CHANGELOG 0.89.0 段（REL-091 交付版——单 canonical）；M-0 GO/五前置核验/组合测试集/门禁基线取自 version-plan-0.89.0 §3b/§4/§5/§9 实读；DEC-244~248 取自 `.governance/decision-log.md` 实读（UTF-8）；各票审查终态取自 docs/reviews/ 各报告实读；census 49→51 与 P2-1/P3-1/P3-2 取自 review-REL-091-RELEASE-R0 实读；archguard 26318/26193 与 live 18/18b 窗口键控取自 EVD-1176 实读；FEAT-065 拆分与双面演示/四红线取自 DEC-248 原文；Check 28s 现值 1,761,442B 取自 `.governance/evidence-log.md` 字节实测（2026-09-26）；LRC 361,923 预算取自 FIX-369 公式沿续口径。未实测项（M-2 门禁数值、archguard regen 目标、前置归档执行结果、双面演示、candidate 提交后 ledger/check-release 复跑、M-5 revert 演练、transition/tag、B-12 真实翻转、B-13 真实切换、09-30 风险窗履行）一律标「期义务/回填位/未执行」，不预填。*
