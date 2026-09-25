# Release Checklist — 0.88.0（REL-086 M-1R / REL-088）

> **M-1R 草案（REL-088，2026-09-25）**——Governance Developer Agent 起草、供 Coordinator 审后随候选提交；结构与措辞对齐 `docs/release/release-checklist-0.87.0.md` 先例。**本文件中的 M-2 数值全部为回填位预留（⏳ 标注）**——M-1R 起草时点 M-2 门禁实测尚未执行，实测后由执行工位原样回填命令输出，未实测项一律标「Coordinator 提交批义务/M-5 期义务/待回填」，不预填。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.88.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.88.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版全部验收在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）类口径下完成——**隔离环境安装冒烟（环境变量重定向至临时目录）通过**不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；do not claim 1.0.0 production-ready。
- **B-12/B-13 未激活面不越权主张**：本版不主张全族 write-guard 已 BLOCK 运行（出厂全 WARN——DEC-239②）、不主张 decision-log JSON 权威已生效（缺省 `MD_ACTIVE` 零足迹——DEC-238②）；激活/切换均为发布窗内另行授权的独立动作（feature-flags-0.88.0 §2/§3）。
- **发布 tip 未生成前不预先编造**：`<发布 tip>`（M-5 transition 提交）与 tag 事实本文件不预填。
- **M-2 数值不预填**：本文件门禁表全部为回填位；任何未实测项写成通过 = 违规。

## Release Scope

| 项 | 值 |
|---|---|
| 版本号 | **0.88.0**（MINOR；semver 论证见下节） |
| 发布任务 | **REL-086（M-0 规划）/ REL-087（M-1 bump）/ REL-088（M-1R 本票）**（DEC-229 预授权链——M-1 bump 工作树交付后 M-1R） |
| 承载决策 | DEC-229~239（11 决策；DEC-229 预授权+架构协作协议 / DEC-230/231 FIX-375 退出码口径 / DEC-232 豁免判据窄口径 / DEC-233 id 词表单一来源 / DEC-234 backport 政策 / DEC-235 9-cell 取舍 / DEC-236 FEAT-060 三条 / DEC-237 FEAT-061 前置复核 / DEC-238 FEAT-061 阶段性交付口径 / DEC-239 五族执法裁定） |
| 核心范围 | **24 票五阶段**：A 契约与卫生 14（FIX-373/378/374/375/376/386/377/387/389/388/379/380/381/382——EVD-1134~1152）+ B 恢复与执法基础 2（FEAT-060/FIX-383——EVD-1153/1154）+ C 单点存储切换 1（FEAT-061——EVD-1155）+ D 执法激活 1（FEAT-064——EVD-1156）+ E 能力与剩余 6（FEAT-062/FIX-384/FEAT-045/FEAT-063/FEAT-044/FIX-385——EVD-1157~1161/1163）+ M-0（REL-086——EVD-1162）+ M-1（REL-087）；完整表见 release-plan-0.88.0 §发布范围（同源 CHANGELOG 0.88.0 段） |
| 目标版本下不发布 | write-guard task_status 族 BLOCK（0.89+——DEC-239①）/ 存储分离其余表 + 主文件大拆解（version-plan §6）/ B-13 真实权威切换执行（授权票前置闭环后另行授权）/ B-12 真实翻转执行（Coordinator 发布窗裁决）/ 量测边缘观察后续面 / 任何 RISK 关闭声明 |
| 时间窗口 | 2026-09-21 v0.87.0 发布（tag 14:02:27 +0800，peel `602f8f3`）→ 2026-09-23 DEC-229 + 出槽三票先落 → 09-24 version-plan v2 落库 → 09-25 M-0 收口（`0233f49`）+ 五阶段 24 票交付（`04b7a42`..`3fb42c0`）+ M-1 bump 工作树交付 → 2026-09-25 M-1R 四件套（本票）→ M-2 实测回填 → M-3 双审 → M-4/M-5+ 另记（taggerdate 权威） |
| Single-Threaded Owner | Coordinator（发布决策与 `.governance/` 写回）；M-1R 材料由 Governance Developer Agent 起草，Release Reviewer 独立审查 |
| 用户获得方式 | `/plugin update`（或 `git pull` + reload）；升级说明 MUST 携带 B-12/B-13/B-14 行为变更（CHANGELOG 0.88.0 段行为变更节原文口径）；B-12/B-13 均为「机制交付未激活」双层姿态（详见 feature-flags-0.88.0） |

## Change Inventory（**29 个窗口提交 + M-1 工作树交付 + M-1R 待落** — `git rev-list --count 602f8f3..HEAD` = 29，2026-09-25 实测；`git describe` = v0.87.0-29-g3fb42c0 交叉印证）

> 窗口起点前一位 `602f8f3` = `v0.87.0` tag peel（REL-084 M-5 transition 提交「0.87.0 transition candidate→released manifest-only」，tag taggerdate 2026-09-21 14:02:27 +0800 实测）。git 时间序（新→旧）；逐票关键交付与审查终态详见 release-plan-0.88.0 §发布范围 24 票表（同源 CHANGELOG 0.88.0 段），本表为窗口构成索引：

| # | commit | 任务 | 阶段/性质 | 证据 |
|---|---|---|---|---|
| 1 | `3fb42c0` | FIX-385 | E——B-7b 大表断点续迁（FEAT-061 衔接；F-1 TOCTOU 修复） | EVD-1163 |
| 2 | `d7b9add` | FEAT-044 | E——subagent 回合预算与收尾心跳（+33 测试） | EVD-1161 |
| 3 | `d68355f` | FEAT-063 | E——closure 重开+异常接管（B-14 半面；TOCTOU R0 P0-1 活体→R1） | EVD-1160 |
| 4 | `467fb55` | FEAT-045 | E——并行段识别审计闭环（纯审计零源码修改） | EVD-1159 |
| 5 | `6360ab1` | FIX-384 | E——B-7a 归档 index-rebuild | EVD-1158 |
| 6 | `14797be` | FEAT-062 | E——closure 取消纵切（B-14 半面；真锁竞争注入 92.86s） | EVD-1157 |
| 7 | `a8afcbf` | FEAT-064 | D——write-guard 分族 BLOCK 激活（B-12 机制交付；registry 96→97） | EVD-1156 |
| 8 | `61618a5` | FEAT-061 | C——decision-log 存储分离首表（B-13；R0 P0×2 活体→R1；179 行演练） | EVD-1155 |
| 9 | `0ff12f3` | FIX-383 | B——B-7c 发版管线自举（release-window-bootstrap+write-guard-bootstrap） | EVD-1154 |
| 10 | `501d8dc` | REL-086 | M-2 门禁实测批（archguard regen sanctioned+冻结测试再基线+自举链收敛活体） | commit 501d8dc/36cc899+EVD op-ef25384 |
| 11 | `ce93eb3` | FIX-382 | A 收官——9-cell 组合判据扩展（DEC-235；穷举差分 S_new=S_old） | EVD-1152 |
| 12 | `b03a0b4` | FIX-381 | A——backport 政策制度化五件套（⑨定案 DEC-234） | EVD-1151 |
| 13 | `c349f8e` | FIX-380 | A——P3 杂项包（_format_issues 单源化等） | EVD-1150 |
| 14 | `b7df86c` | FIX-379 | A——量测边缘观察四项打包（DEC-233） | EVD-1149 |
| 15 | `b3577c8` | FIX-388 | A——static-pin 账本重审计（12375→12550 重锚+12674 补登；EVD-1146 残留见专席②） | EVD-1146/1147 |
| 16 | `cdc3a0a` | FIX-389 闭环 | A——LRC 文档面清账审查报告 | EVD-1148 |
| 17 | `9df2381` | FIX-389 | A——LRC 文档面 ragged rows 修复（0.88 M-0 Check 31 链 R0 BLOCKED→R2 PASS 承载） | EVD-1148 |
| 18 | `0840876` | FIX-387 | A——套件全局态污染修复（P1 插队；canary 防回归） | EVD-1145 |
| 19 | `17e5663` | FIX-377 | A——FACTS_PRINT_TOTAL +10 归属 bisect（10/10 归 FIX-371 豁免披露输出） | EVD-1144 |
| 20 | `d6dd300` | FIX-386 | A——遗留小项包（AUDIT-152+ADR 勘误+RISK-046 扩展） | EVD-1143 |
| 21 | `3d31c49` | FIX-376 | A——FIX-371 遗留合并处置（DEC-232 窄口径） | EVD-1142 |
| 22 | `04b7a42` | FIX-375 | A——writer 族三边缘收口（exit 0→2 透传——DEC-230/231） | EVD-1140/1141 |
| 23 | `0233f49` | REL-086 收口 | M-0——发布半面 R2 GO（F-1~F-13 闭环；批次执行启动） | EVD-1162 |
| 24 | `7d6ff6a` | REL-086 追加 | M-0——R1 报告 N1 自指修复（Check 31 记账面消解） | EVD-1162 |
| 25 | `266c32b` | REL-086 | M-0——version-plan v2 落库 + 六票入账 + §3b 发布链映射 | EVD-1162 |
| 26 | `6845756` | FIX-374 | A——9-cell 豁免消歧（fail-blind 消除） | EVD-1138 |
| 27 | `44cb534` | FIX-378 | A——e2e 副本守卫同步（副本 git 忽略——仅审查报告面） | EVD-1136/1137 |
| 28 | `3c3218d` | FIX-373 | A——切分器 quote 分支守卫（EVD-248 误报消解；0.87 出槽） | EVD-1134/1135 |
| 29 | `fc69196` | REL-084 M-8 | 前版收尾——0.87.0 发布收口（M-6 复跑+热事实源回填+归档） | EVD-1132/1133 |
| — | 工作树 | REL-087 | **M-1 版本 bump（待提交——candidate commit 随 M-1R 提交批落库）**：全仓 bump + CHANGELOG 0.88.0 段双位 + static-pin 消解 | TRIAGE-REL-087 |
| — | 本票 | REL-088 | **M-1R prep 批（Coordinator 提交后为 candidate commit）**：本四件套 + `core/releases/0.88.0.json`（candidate manifest——**本票锁面外**，Coordinator 按候选打包程序创建并随提交入索引）+ M-2 复跑义务执行 | 本文件 + release-plan |

**版本 bump 平面清单（M-1 = REL-087 工作树交付，CHANGELOG 版本投影段口径）**：

| 平面 | 载体 | 值 |
|---|---|---|
| 权威源 | `skills/software-project-governance/SKILL.md` frontmatter | **0.88.0** |
| 投影/声明面 | 5 plugin/marketplace json + `package.json` + `core/manifest.json` + 4 hook `@version` + DSH persona 版本行 + `adapters/dsh/AGENTS.md.template` + `commands/governance-init.md` 三模板 `@bootstrap-version` + fixture 面 + 双根 entry bootstrap（AGENTS.md/CLAUDE.md）+ `verify_workflow.py` REQUIRED_SNIPPETS 六锚 + `checks/version.py` | 全部 **0.88.0**（28 投影面——`release-projection --write` 单次收敛零回滚，check 模式 28/28 PASS 零 issue；双根 entry 经 `sync_entry_projection --write` 再生双根 4 文件 PASS——CHANGELOG 版本投影段实测口径） |
| CHANGELOG 段 | `project/CHANGELOG.md`（历史连续判据面）+ 根 `changelog.md`（triage-normalized 锁面交付物） | 0.88.0 段（24 票 + DEC-229~239 + B-12/B-13/B-14 + 披露①~⑦）已于 M-1 交付——**双位同段维护**（披露⑥；canonical 归属留 M-3 审查裁决） |
| static-pin 账本 | `test_verify_workflow.py` STATIC_PIN_EXEMPTIONS 等 | **已消解**（M-1）：删 2 self-dormant（L12614/12738 旧锚——version-plan L75 errata F-1 + FIX-388 迁移指南）+ 登记 4 bump-time rows（test_archive.py:4586/4595、test_governance_store.py:493、test_verify_workflow.py:12742——披露③）+ 保留 1 dormant FUTURE_TARGET（test_release_projection.py L30）；M-2 复核期望 0 WARN |
| ledger manifest | `core/releases/0.88.0.json` | **尚未创建**（M-1R 候选打包面——本票锁面外；Coordinator M-5 提交批承载，`lifecycle_state: candidate`，唯一 transition 由 M-5 追加） |
| plan-tracker `工作流版本` | `.governance/`（gitignored） | 仍 0.87.0（**过渡态 WARN**——M-8 收尾由 Coordinator 更新为 0.88.0；本版 verify 唯一预期 WARN） |

## 行为变更（面向用户 —— CHANGELOG 0.88.0 段已载，本表为索引）

| # | 变更 | 任务 | 性质 | 回退通道 |
|---|---|---|---|---|
| **B-12** | write-guard 分族 BLOCK 激活（机制交付）：evidence/review/decision/ops_ledger 四族 WARN→BLOCK + task_status WARN 后置；启用族由写路径覆盖率裁定（DEC-239）；**出厂全 WARN——真实翻转经 `--activate-block` 由 Coordinator 发布窗裁决** | FEAT-064 | 执法硬化升级（DEC-224 双约束内——非判定语义弱化；BLOCK 写后执法不能阻止文件被修改——M-0 事实填充③如实措辞） | **双层**：未激活 = 零回退需求（缺省姿态即全 WARN 零足迹）；激活后 = 族级 flag 回 WARN（`--deactivate-block` audited rollback）+ break-glass 恢复窗（五限定不可静默——guard 自指同样适用）（rollback-plan §7 专节） |
| **B-13** | decision-log JSON 权威化（机制交付）：md 转派生投影；外部 decision-append CLI 契约零变化；旧工具对新格式明确拒绝非静默误读；**缺省 `MD_ACTIVE` 零足迹——真实切换经授权票另行执行（RISK-059/DEC-238④）** | FEAT-061 | 新增受治理能力面（存储架构首表——阶段性交付，存储分离其余表出槽 0.89+） | **双层**：未切换 = 零回退需求（缺省态零足迹）；切换后 = 反向转换方案（`rollback-export` 全量反向导出 + `rollback-activate` 回 MD 权威——FEAT-061 已交付；**仅备份不算可回滚——须覆盖迁移后新增行**；切换前快照 + FEAT-061 演练已证字节回环）（rollback-plan §7 专节） |
| **B-14** | closure 取消/重开/接管路径新增：限定入口→CAS 单终态→cancellation op 登记→仅释放自有锁→对账；重开保留原 closure 新尝试编号不擦历史；接管=执行代际 fencing 写入端校验 | FEAT-062/063 | 纯新增能力面，无删除；外部 CLI 契约不变 | 版本级回滚即消失（纯新增——无数据迁移无删除面；已登记的 cancellation/reopen 事件为事实记录保留）（rollback-plan §1） |
| （连带） | **writer 族失败退出码透传**：红态 exit 0 假绿→exit 2（8 return-style handlers 全透传；无 SystemExit 桥接）——迁移 = 读退出码 | FIX-375 | 缺陷修复承载的行为面（DEC-230/231——非独立行为变更号） | 版本级回滚（随 FIX-375 恢复旧行为——rollback-plan §1） |

## 版本号决策记录（semver 论证——CHANGELOG 0.88.0 段同口径）

- **MINOR（0.87.0 → 0.88.0）**：VERSIONING.md L12「新增 B/C 级自动化能力」——载荷 = write-guard 分族 BLOCK 执法（B-12）+ decision-log 存储分离首表（B-13 新增受治理能力面）+ closure 取消/重开/接管（B-14）+ subagent 回合心跳；非纯 bug fix；
- **非 PATCH**：L38 口径不适用——主体为执法硬化 + 存储架构首表 + 能力铺开批；
- **非 MAJOR / Breaking changes = 无**：L11 口径逐项核对不成立——无 MUST 规则删除/重命名、无外部 CLI 契约变更（decision-append 契约不变）、无 governance 文件字段格式变更；B-12 为 DEC-224 双约束内执法硬化升级（FEAT-060 持久状态机 + B-11 三面留痕为前置基座——非判定语义弱化）；B-13 旧工具明确拒绝非静默误读；B-14 纯新增；版本号未占用预留（0.87.0 已发布顺延 +1；无 0.88.x tag/预留冲突；1.0.0 预留位未触碰）。

## Candidate Gate Results（M-2 —— ✅ 2026-09-25 实测回填完成〔#10/#15 为 M-5 批义务位〕；A 清单结构对齐 0.87.0 先例 + version-plan §3 增量面）

| # | 门禁 / 命令 | 结果 | 关键实测值（回填位） |
|---|---|---|---|
| 1 | `verify` 全量 | ✅ **PASSED**（2026-09-25 M-2 实测，exit 0） | 唯一 WARN = plan-tracker 过渡态（预期——M-8 收口）；REQ-092 披露面见专席② |
| 2 | `check-version-consistency` | ✅ **PASSED**（M-2/M-3 复跑） | source=0.88.0；双入口 marker 0.88.0；1 WARN=plan-tracker 过渡态（M-8） |
| 3 | `check-injection-budget`（×3 profile） | ✅ PASS（M-2 实测随 verify 全量） | 三 profile 逐位在预算内；skill 层 16,000 内 |
| 4 | `check-projection-sync --fail-on-issues` + `check-entry-bootstrap-sync` | ✅ PASS | 28 mirrors + entry 双根全绿（M-1 一次收敛幂等确认） |
| 5 | `release-projection`（check-only） | ✅ PASS | state=PASS / 0.88.0 / 28/28 / issues=[]（M-1+M-3 两轮确认） |
| 6 | `check-cross-references` | ✅ **PASS（727 refs）** | 0 dangling / 0 deprecated / 0 circular（四件套+CHANGELOG+载荷全窗口落盘后） |
| 7 | `check-manifest-consistency` | ⚠️ advisory（894/1033） | 唯一 UNTRACKED=根 changelog.md——M-3 裁决 canonical=project/；M-5 批入 manifest 收口 |
| 8 | `archguard-ratchet`（R1~R7） | ✅ **REGENERATED**（sanctioned——专席④） | 锚 25462→26193 @a8a72a3；R4 print 1316→1318；R5 97/97；冻结测试同步再基线（38P 全绿） |
| 9 | contract-matrix | ✅ PASS | zero drift；cli_dispatch 97 键（DEC-239⑥ 收口确认） |
| 10 | `release-ledger --version 0.88.0 --no-remote` | ✅ FAIL 实测（预期——预提交态，M-3 R0 五维度④核验）→ **M-5 批：manifest 创建后复跑** | `core/releases/0.88.0.json` Coordinator M-5 提交批义务（披露①）；期望 NATIVE_CANDIDATE PASS |
| 11 | 全量测试套件（M-2 一次预算） | ✅ **4119P / 1S / 0F**（exit 0，21:45）——**历史首次全绿** | 4108 基线 + REL-089 +11；HotFactSource 族随 0.88.0 bump 消解；最终门禁绑定实际发布提交（M-6 复验） |
| 12 | **组合测试集四条**（F-5 兑现） | ✅ ②④ 已实测（FEAT-064/062 票内交付）；①③ 归 cutover 授权票（DEC-239⑦ 落字——五面一致链经 M-3 CODE 半面复核） | ①guard×migration 共存 ②BLOCK 激活后全走写入器（实测）③基线×投影失败恢复 ④closure 取消×locks-release 并发（实测） |
| 13 | **FEAT-061 独立证明包门** | ✅ 七要素齐备（feat061-rehearsal-result.json 179 行真实数据：verify+reverse+字节回环全 PASS；审查 R1 AWN/0 复核） | 绑定发布提交=M-5/M-6 义务（manifest+tip 后复验） |
| 14 | e2e / dsh 隔离冒烟 | ✅ e2e-check 全 pass；**隔离环境安装冒烟（环境变量重定向至临时目录）通过**；real-home writes: 0 | check-release 内嵌 e2e PASS（M-2 实测） |
| 15 | check-release 复合门禁（candidate） | ⏳ **M-5 批执行**（依赖 manifest 在场——SPG_RELEASE_GATE_TIMEOUT=600） | M-2 期实测 FAILED-2（governance health 74→36 已知披露面收敛+unit tests 引用形态）→ manifest 后复跑期望 FAILED-1 内 |
| 16 | `check-loop-runtime-claims`（LRC gate） | ✅ **PASS（semantic+identity 双 PASS）** | 999 candidates / parsed / skip=0 / truncate=0；预算 361,923（M-0 实测 305,604 余量 56,319 未越线——无重定标义务） |
| 17 | **Check 28s evidence-log 复测**（F-6） | ⚠️ ERROR 维持（1,735,257B > 250,000B）——已知披露面（FIX-349⑤ 评估：引擎行为正确维持披露口径） | M-8 归档后复测消解有效性确认（0.87 先例 1620KB 警示——如实回填） |
| 18 | M-2 revert 干跑（回滚演练） | **未排程维持**（三版先例同型）——M-3 发布半面裁决：不排程不阻断（tip 未定先干跑无意义）；**REL-089 补强**：rollback §8 两路径+回退前四步+回退后四验证已实测可执行（0.87 视角 11 用例） | §8 落位=实质回滚就绪增强（M-3 R0/R3 复核通过） |
| 19 | execution packets 面（F-4） | ✅ **7 包全绿**（18c ready 7/7 + 18d~18i 全 PASS——M-3 R1→R3 收口：28 行合同 FAIL 清零+TO_BE_DEFINED 203→0） | 补包 ×3（REL-087/088/089）+ 五类合同字段按票面事实填写（R3 终审 AWN/0） |

### 专席① —— Check 10 修复验证（FIX-348 白名单面）

- **Check 10 = M5 AskUserQuestion Compliance**（插件 source 扫描——`verify_workflow.py` Check 表 L15072/L15137 实读）；本票四件套落 `docs/release/**`——该目录自 FIX-295/AUDIT-149 N6 + **FIX-348** 起在 Check 10 record-doc scope **白名单内**（`docs/release/**`、`docs/reviews/**`、`docs/requirements/**`——`verify_workflow.py` L14914-14957 实读），四件套本身的 (a)/(b) 决策记录行不触发 M5 反模式。
- **0.88 M-0 实证链**：Check 10 曾在 REL-086 R0 BLOCKED→随修复 R2 PASS（`0233f49` M-0 收口 commit——Check 10/25/26/31 全 PASS 实证链）。
- **M-2 回填义务**：四件套落盘后复跑 Check 10 并如实回填——期望 PASS（白名单面覆盖 `docs/release/**` 四文件）；若 BLOCKED 逐行归因（code-span 自指/裸问句形态——FIX-389/`7d6ff6a` 同型教训）如实披露不豁免。

### 专席② —— Check 16-17 披露（REQ-092 + EVD-1146 superseded 残留）

- **REQ-092 blocked 面（预期披露非豁免）**：EVD-476/473/423 3 FAIL = REQ-092（Desktop marketplace 外部依赖 + result matrix 在场）——真实活跃义务，零豁免红线内维持（version-plan §3 条 5 F-8 显式登记；0.79.0/0.87.0 先例姿态延续）。
- **EVD-1146 superseded 残留（0.88 新增披露面）**：FIX-388（`b3577c8`）首次 evidence 写入目标对齐字段仅 13 chars→Check 16 FAIL；EVD-1147 为合格重写。按 DEC-227 路线 a 否决先例（补录=编造风险违反 P1）**不补录历史行、不动+披露**；处置口径由 M-3 审查复核（CHANGELOG 披露②原文）。**EVD-1146 属 0.88 窗口新增行——不得入 B-11 历史豁免账本**（新增行零豁免全严检——DEC-227 红线）。
- **M-2 回填义务**：复跑 Check 16/17 并如实回填当场 FAIL 计数与逐行归因（期望成分 = REQ-092×3 + EVD-1146×1——计数以实测为准不预填）；**M-2 期任何新增 FAIL 行不得入豁免账本**（违反即 B-11 红线破约）；historical exempted 计数如实记录（0.87 期 26=8+18 对账基线）。
- **M-2 实测新增披露（2026-09-25 回填）——Check 18/18b 机器锚状态前缀分叉面**：实测 Check 18/18b entry 集合 2 条（FIX-375 EVD-1140 + REL-087 EVD-1164）因**机录状态链 committed 前缀不匹配 ✅-豁免谓词**（FIX-376 F-3 刻意保守分叉——豁免面窄化是 fail-closed 方向）而进入严检集合，其 事实依据/结构化事实 字段位于独立列（parts[5]）而 Check 18 搜索 description 列（parts[4]）→ 2×2 FAIL。**归因**：非数据缺陷——EVD-1140 的 basis 在独立列、EVD-1164 为 evidence-append 机录行（--basis 落 parts[5]，与全部 0.88 窗口机录行同构；其余 21 条同构行因 ✅ 豁免谓词或历史豁免跳过严检）。**处置**：如实披露非豁免（本席新增成分——M-3 审查复核：豁免谓词是否扩至 FIX-292 权威终态判定属后续票面，不在发布窗内修）；与 REQ-092/EVD-1146 同席承载。

### 专席③ —— Check 31 修复验证（0.88 M-0 链 R0 BLOCKED→R2 PASS）

- **修复链事实**：0.88 M-0 规划链 Check 31 曾 BLOCKED（REL-086 R0）→ FIX-389 ragged rows 修复（`9df2381`）+ `7d6ff6a` 自指记账面消解 → R2 PASS（`0233f49` 收口实证链）；**预算值 361,923 本版零改动**（FIX-369 公式值沿续——provenance `checks/loop_runtime_claims.py` L225-242）。
- **M-0 期实测**：semantic_units=305,604，余量 56,319（version-plan §3 条 4）。
- **M-2 回填义务**：复算期望 PASS 且如实记录当场 units 计数；本版治理记录增量可观（24 票 TRIAGE/EVD/REVIEW 机录 + M1.2 勘正）——若越线按 FIX-369 同公式 ceil(实测峰值×1.2) 重定标 + baseline-register 登记（**重定标非豁免**——反豁免 fail-closed 双测试在场）；UNSUPPORTED_AFFIRMATIVE 计数如实记录（0.87 期 3 = FIX-320 豁免账本内已知基线）。

### 专席④ —— archguard 棘轮席（6F 存量 baseline regen 归发布窗——M-2 sanctioned per FEAT-055 先例）

- **6F 存量事实**：HEAD 处 archguard R1~R7 存在 6 项 FAIL 存量（pre-existing——FEAT-044 EVD 归因修正「archguard 6F 归因修正（HEAD pre-existing）」+ FIX-377 调查票「棘轮 regen 留 M-2 发布窗」链注）。
- **处置裁定**：baseline regen **归 M-2 发布窗执行**（M-2 sanctioned——FEAT-055 先例同型：0.87 M-2 修复批基线 regen 因引擎接线致 committed 基线过期）；regen 时 MUST 附归因链（FIX-377 EVD-1144 + FEAT-044 EVD-1161）留档，不得静默清零。
- **R5 期望 97/97**：FIX-383 registry 收口 96→97 键 + contract-matrix 指令化再生（DEC-239⑥）——M-2 实测确认。
- **M-2 回填义务**：R1~R7 全量结果 + regen 前后计数如实回填；only-down 面（R1/R4/R6/R7）零 violations 期望。

**M-2 执行序纪律**（0.87.0 先例沿用）：①安静窗——涉及 candidate 集合枚举的检查 MUST 无并发写盘；②顺序：verify → check-version-consistency → check-injection-* ×3 → check-projection-sync → check-entry-bootstrap-sync → release-projection → check-cross-references → check-manifest-consistency → archguard-ratchet（专席④ regen）→ contract-matrix → release-ledger → 组合测试集四条（#12）→ 独立证明包门（#13）→ 混沌复演 → e2e/dsh 冒烟 → 全量 pytest（后台先行、终态汇总——#11 M-2 一次预算）→ LRC（#16）→ Check 28s（#17）；③每个 FAIL 逐项落披露，不以「已知」豁免（#10 ledger FAIL 为预提交态预期——如实归类非豁免；REQ-092/EVD-1146 为活跃义务/残留披露——非豁免）；④tag 生成后 MUST 复跑 `check-release --lineage-mode released --release-commit <commit>` 与 `release-ledger --remote`（M-6 预推校验）。

## 披露清单（如实披露项 —— 不得写成通过）

① **candidate manifest 缺席（本票锁面外）**：`core/releases/0.88.0.json` 未创建 → `release-ledger --no-remote` 预期 FAIL（#10）+ check-release 复合门禁未跑（#15）。**收口 = Coordinator M-5 提交批**：按候选打包程序创建 canonical manifest（NFC/sorted/compact/trailing-LF）+ 四件套同批提交 → 复跑 ledger（期望 NATIVE_CANDIDATE PASS）+ check-release（candidate）。0.87.0 先例为四件套+manifest 同 commit。

② **REQ-092 blocked 3 FAIL 维持 + EVD-1146 superseded 残留**（见专席②）：REQ-092 = 外部依赖零豁免红线活体（非豁免）；EVD-1146 = 不合格首写历史行不动+披露（EVD-1147 合格重写）——M-3 审查复核处置口径；两成分均不得入 B-11 豁免账本。

③ **static-pin bump-time 双信号**（FIX-361 设计语义——M-1 已消解）：4 WARN 逐行归因登记豁免（test_archive.py:4586/4595〔FIX-384 fixture 世界〕、test_governance_store.py:493〔FIX-379 夹具行〕、test_verify_workflow.py:12742〔FIX-376 legacy REQ fixture〕——全部 scenario payload 零等值比较）+ 2 self-dormant 删除（L12614/12738——F-1 errata）+ 1 dormant FUTURE_TARGET 保留；M-2 复核期望 0 WARN。

④ **FEAT-061 为阶段性交付（机制交付未激活）**：C1 六层落地+真实 179 行演练 round_trip；**本版不主张 JSON 权威已生效**——缺省 `MD_ACTIVE` 零足迹；存储分离其余表（evidence-log 等）与主文件大拆解出槽 0.89+（version-plan §6）；真实切换授权票前置 = DEC-238④ 三缺口（RISK-059）+ DEC-239⑦ F-5①③ 组合测试归票，闭环+证明包审查后另行授权。

⑤ **FEAT-064 BLOCK 为机制交付（未激活）**：出厂全 WARN（基线字节+零窗口输出恒等——字节恒等探针实证）；**本版不主张全族已 BLOCK 运行**——真实翻转（基线登记→激活）留 Coordinator 按 DEC-239② 于发布窗裁决执行（`--activate-block`）；task_status 族 WARN 后置 0.89+。

⑥ **CHANGELOG 双位过渡**：根 `changelog.md`（triage-normalized 锁面交付物——本票工作树 untracked 态如实注记）与 `project/CHANGELOG.md`（历史连续判据面）双位同段维护——canonical 归属未裁决前漂移风险由 M-3 复核（披露⑥）。

⑦ **plan-tracker `工作流版本` = 0.87.0 过渡态 WARN——仍开放**：M-8 收口（Coordinator），含 **roadmap 0.88.0 行回填义务 + REL-086 任务行终态回填义务**（FIX-367 复发预防内建——R0-DESIGN-F8）+ Check 28s 复测（#17——F-6）。

⑧ **no-overclaim**：official approval / marketplace approval / universal runtime support / external first-session pilot success 均未被主张；RISK-036 打开，1.0.0 就绪未被主张；非 Windows 平台未验证；RISK-036/039/046 窗裁决 2026-09-30 到期即裁决（不迟于 M-4——F-13），RISK-050（10-31）维持打开。

⑨ **回滚安全弱化面**：回滚到 0.87.0 即整体恢复——(a) writer 族失败退出码回 exit 0 假绿态（FIX-375 修复消失——门禁信号弱化面如实披露）；(b) write-guard 持久状态机/消费权台账/分族姿态面消失（FEAT-060/064——若发布窗已激活 BLOCK 则激活后消费审计为事实记录保留，回退走 `--deactivate-block`/break-glass 通道，rollback-plan §7）；(c) decision-log 存储分离六层消失（若已切换则回退须走反向转换方案——`rollback-export`/`rollback-activate`，仅备份不算可回滚）；(d) closure 取消/重开/接管与心跳能力消失（纯新增面）；(e) A 阶段修复票缺陷复活（EVD-248 误报/9-cell fail-blind/static-pin 漂移/LRC ragged——0.87 已知态回归）。均如实预期非回滚失败（rollback-plan §1/§4/§7）。

## 发布步骤（M-0 ~ M-8 勾选框）

- [x] **M-0 规划确认**：REL-086 双半面 GO（Design R1 + Release R2 全 APPROVED_WITH_NOTES/0——F-1~F-13 闭环）；DEC-229 生效（`0233f49`）
- [x] **24 票载荷**：A14+B2+C1+D1+E6 全部交付闭环（EVD-1134~1163；NEEDS_CHANGE→R1/R2 转化五票 + FEAT-061 P0×2 活体修复；0 unresolved blockers）
- [x] **M-1 版本 bump（全平面）**：REL-087——28 投影面 + CHANGELOG 0.88.0 段双位 + static-pin 消解（**工作树交付——candidate commit 随 M-1R 提交批落库**；check-version-consistency/verify/static-pin 套件全过——plan-tracker REL-087 行审查中）
- [ ] **M-1R 发布材料**：本四件套（REL-088 锁面 expected-new）——本票交付后勾选
- [ ] **M-2 门禁实测**：#1~#19 回填位实测回填（重点四席：Check 10 修复验证专席① / Check 16-17 披露专席② / Check 31 修复验证专席③ / archguard 棘轮专席④）+ 组合测试集四条（#12）+ 独立证明包门（#13）+ 全量 pytest 一次预算（#11）+ Check 28s（#17）
- [ ] **M-3 双半面审查**：产品代码半面（Code Reviewer 链）+ 发布半面（Release Reviewer 链）；按阶段边界分节（version-plan §1 假绿对冲）；review-record 机录；复审必达；含 EVD-1146 处置口径与 CHANGELOG 双位过渡复核（披露②⑥）
- [ ] **M-4 修复窗 + go/no-go**：M-2/M-3 FAIL 修复窗；RISK-036/039/046 窗裁决 2026-09-30 到期即裁决（F-13——不迟于 M-4）；DEC-229 预授权形态——Coordinator 呈现，门禁不予放弃
- [ ] **M-5 candidate 提交 + transition**：`core/releases/0.88.0.json` 创建 + 四件套同批提交 → 复跑 `release-ledger --no-remote`（期望 NATIVE_CANDIDATE PASS）→ transition candidate→released（单父 manifest-only + integrity）
- [ ] **M-6 预推校验**：`check-release --lineage-mode released --release-commit <commit>` + `release-ledger --remote` 全绿方进 M-7
- [ ] **M-7 tag+push**：annotated tag `v0.88.0`（peel = transition 提交；taggerdate 权威——FIX-349）+ master + tag 原子推送（远端 SHA 精确一致）
- [ ] **M-8 归档 + 收尾**：`archive.py migrate --auto --dry-run` → 迁移 → `check-archive-integrity` PASS；Check 28s 复测消解确认（F-6）；plan-tracker `工作流版本` → 0.88.0 + roadmap 0.88.0 行 + REL-086 终态回填；session-snapshot 刷新；证据行落账

## M-8 收尾义务（Coordinator 面——本票不执行）

- [ ] candidate 提交（四件套 + manifest 入索引后）→ 复跑 `release-ledger --version 0.88.0 --no-remote`（期望 NATIVE_CANDIDATE PASS——刷新 #10）+ check-release candidate（刷新 #15）
- [ ] plan-tracker：`工作流版本` → 0.88.0；REL-086/087/088 行状态更新；0.88.0 路线图行 → 已发布（待 tag 后——FIX-367 复发预防义务）
- [ ] session-snapshot 刷新（含可解析 session_date——Check 28c hot fact source 面）
- [ ] hooks_drift 一次性重装提示：`cp "<plugin_root>/skills/software-project-governance/infra/hooks/"* .git/hooks/`（DEC-213④；0.87 期实测三 hook 全在场——本版 post-commit 消费路径经 guard CLI【FEAT-060】复测确认）
- [ ] 归档触发检测与迁移（ADR-006/007；完整性失败阻断发布完成）——注意 FEAT-061 阶段性交付边界：decision 表归档路由在 JSON 权威态的改造属 RISK-059① 切换授权票前置（未切换态 archive 路由行为不变）
- [ ] 本披露开放项收口：plan-tracker 工作流版本（M-8）／candidate manifest + ledger 复跑（M-5 提交批）／EVD-1146 处置与 CHANGELOG 双位（M-3）／B-12 真实翻转与 B-13 真实切换（授权票另行承载——非 M-8 义务）／M-2 四重点席回填复核

## 本票自检验证记录（M-1R 起草工位）

- 四文件在场：`docs/release/release-plan-0.88.0.md` / `release-checklist-0.88.0.md` / `rollback-plan-0.88.0.md` / `feature-flags-0.88.0.md`（本票全部写入面）。
- 回滚区间实测：`git log --oneline 602f8f3..HEAD` = 29 行 + `git rev-list --count` = **29**（HEAD `3fb42c0` 已含）；`602f8f3` = `git rev-parse v0.87.0^{}` 实测同一；`git for-each-ref refs/tags/v0.87.0` 实测 taggerdate 2026-09-21 14:02:27 +0800 / tag object `2e5f715`。
- B-12/B-13 机制面实读：`write_guard_state.py`（POSTURE_CONFIG_FILE_NAME L301 = `.write-guard-posture.json`；管理 CLI L1668+ = activate_block/deactivate_block/show_posture/break_grant/break_clear/break_show）+ `verify_workflow.py` L23908-23917（`--deactivate-block` = audited B-12 flag rollback）+ `decision_repository.py`（AUTHORITY_STATE_FILE L131 = `.decision-store-state.json`；状态机 L151-163）+ `decision_migration.py` argparse（freeze/shadow/verify/activate/rollback-begin/rollback-export/rollback-activate/cancel/status/project-repair/proof-pack——L1009-1048）。
- check-manifest-consistency / check-cross-references / check-version-consistency：M-1R 起草时点执行记录见结构化返回（0.87.0 先例 docs/release 面不逐文件入 manifest——与 0.87.0 四件套同形态实证）。

---
*REL-088 M-1R 草案冻结（2026-09-25，REL-088，Governance Developer Agent 起草）。事实基线：29 提交窗口取自 `git log`/`git rev-list`/`git describe`/`git rev-parse v0.87.0^{}`/`git for-each-ref` 实测；24 票交付、B-12/B-13/B-14、披露①~⑦口径取自 CHANGELOG 0.88.0 段（REL-087 交付版）；M-0 GO 与 Check 10/31 R0 BLOCKED→R2 PASS 链取自 `0233f49`/`7d6ff6a` commit message；LRC 305,604/组合测试四条/证明包门/F-6/F-13 取自 version-plan-0.88.0 §3/§3b/§7 实读；DEC-236~239 取自 `.governance/decision-log.md` 实读（UTF-8）；RISK-059 取自 `.governance/risk-log.md` 实读（UTF-8）；B-12/B-13 机制面取自 write_guard_state.py/verify_workflow.py/decision_repository.py/decision_migration.py 实读；Check 10 白名单面取自 verify_workflow.py L14914-14957/L15072/L15137 实读。未实测项（M-2 门禁数值、candidate 提交后 ledger/check-release 复跑、M-5 revert 演练、transition/tag、B-12 真实翻转、B-13 真实切换）一律标「期义务/回填位/未执行」，不预填。*
