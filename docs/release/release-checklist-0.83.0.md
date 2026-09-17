# Release Checklist — 0.83.0 (REL-079)

> **M-0 草案（REL-079 prep，2026-09-17）**——Coordinator 审后随 M-1 候选提交；结构与措辞对齐 `docs/release/release-checklist-0.82.0.md` 先例。M-1 冻结前 ⟦待回填⟧ 占位 MUST 全部消除——**唯一例外 = M-2 派生回填类**（候选 commit hash 与 M-0/M-1 批 hash：manifest 须先随候选提交入库、`release-ledger` 才能派生——EVD-1034 / REVIEW-REL-077-RELEASE-R1 F-R1-02 先例，M-2 期回填）；「Candidate Gate Results」的实测值由 M-2 门禁实测逐项回填（结果列 = 「M-2 执行时回填」），未回填项不得视为通过。本清单命令仅为列写——**M-0 期不执行命令**，全部实测由 Coordinator M-2 执行。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.83.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.83.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版引擎/判定面改动全部在仓库内测试与隔离 `DSH_HOME`（环境变量重定向至临时目录）下验收——隔离验收不等于真实外部首会话验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开，未关闭；0.83.0 为内部治理健康收口版，外部验证/官方提交零进展；do not claim 1.0.0 production-ready。
- **RISK-039/046/050 remain open**：三者维持打开（复评提案见 RISK 复评节）；0.83.0 的 ArchGuard 判定面校准属看护面正向演进，**不据此声明 RISK-039 关闭**（关闭标准含外部宿主验证与 God-module 拆分路线兑现——均零进展）。
- **ArchGuard advisory 边界**：Check 28n/28o/28p 维持 `fatal_on_error=false` 既有边界——本版不声称 ArchGuard advisory fatal 化；28o 残余 4E 为产品源真实 advisory（God-module 族），如实披露不阻断。

## Release Scope

| 分组 | 任务 | 版本归属 |
|---|---|---|
| **0.82.0 发布后收尾** | **FIX-348**（`57c6fc4`——Check 10 M5 record-doc 白名单扩展 `docs/requirements/**` + docs/requirements 豁免披露；DEC-198；REVIEW-FIX-348-CODE-R0 APPROVED_WITH_NOTES/0；EVD-1064） | 0.83.0 |
| **存量治理数据卫生批** | **FIX-349**（`bf7e25a`——Check 5 ×13 / Check 17 ×14 数据清零 + Check 16 同 EVD fan-out 假阳修复（live 19→0）+ Unicode 行分隔符扫描制度化（Check 14 子检查 6，8 字符族含 U+000C）+ Check 28s 评估（引擎行为正确，维持披露）+ 日期勘误（EVD-1065）；DEC-199/DEC-200 落账 + REL-079 入账；REVIEW-FIX-349-CODE-R0 APPROVED_WITH_NOTES/0；EVD-1066） | 0.83.0 |
| **架构债批（ArchGuard 判定面校准）** | **FIX-350**（`589e99f`——豁免 gate 四面扩展 + dup 三精确路径豁免（[EXEMPT] 披露）+ schema `project/**`/`.governance/**` 豁免 + release_docs 阈值 30→80 + ratchet 重锚 R1 24453→24583 三红转绿；DEC-201；REVIEW-FIX-350-CODE-R0 APPROVED_WITH_NOTES/0；EVD-1067） | 0.83.0 |
| **发布治理面** | 本 checklist + `feature-flags-0.83.0.md` + `rollback-plan-0.83.0.md` + `project/CHANGELOG.md` [0.83.0] 段 + RISK 复评提案 + 版本号决策记录（Release Agent M-0 起草）+ `core/releases/0.83.0.json` candidate（M-1 交付） | 0.83.0 |
| **治理健康收敛（成果面）** | /governance 会话链 48→34→33（基线）→**21 issues**（33→21 为本窗口）；构成变化 = Check 5/16/17/18/28p/34 清零 | 0.83.0 |
| **不发布什么（显式排除）** | FIX-350 R0 F-1（P2——release_docs_note 机制表述措辞精度）+ F-2/F-3/F-4（P3 备案）——0.84.0+ 候选（DEC-201 ⑥）；Check 28s retention/归档判定面演进（FIX-349⑤ 评估完成、不改引擎——28s 维持披露口径）；RISK-046 遗留候选（跨日静默+豁免披露 / 读写竞态 / 绝对路径旁路 F-1/F-2/F-4）；Check 28o God-module 拆分（0.59.0~0.64.0 渐进拆分路线，RISK-039 关闭标准面）；prepare-commit-msg 用户一次性命令移交收尾（28q，移交中）；FIX-246 V2 历史缺口补造路径（不存在——DEC-199 (a) 如实保留，RISK-051） | 排除 |

## Change Inventory（**3 commits** — `git log v0.82.0..HEAD` 即 `24cfb04..589e99f`，2026-09-17 M-0 期登记；**M-1 冻结时窗口扩展至候选打包提交**，M-0/M-1 批行 ⟦待回填⟧；`24cfb04` = 0.82.0 发布线末位提交（post-transition integrity 公式修正；v0.82.0 tag peel = transition 提交 `b63584c`——RELEASE R0 F-2 机核勘误，2026-09-17），`589e99f` = 本版窗口起点当前 HEAD）

| # | 任务 | commit | 终态要点（审查终态 + EVD） |
|---|---|---|---|
| 1 | **FIX-348** | `57c6fc4` | 0.82.0 发布后收尾——Check 10 M5 record-doc 白名单扩展 `docs/requirements/**`（DEC-198；PATH-CLASSIFICATION only + [EXEMPT] 披露 + fail-closed 不弱化 + 前缀 trap 测试锁定；base `check_m5_compliance()` 字节不变）；REVIEW-FIX-348-CODE-R0 APPROVED_WITH_NOTES/0；EVD-1064 |
| 2 | **FIX-349** | `bf7e25a` | 存量治理数据卫生批——Check 5/17 数据清零 + Check 16 同 EVD fan-out 假阳修复（live 19→0）+ Check 14 子检查 6（Unicode 行分隔符扫描制度化，8 字符族含 U+000C）+ Check 28s 评估（维持披露）+ 日期勘误（EVD-1065，taggerdate 权威 2026-09-17）；DEC-199/DEC-200 落账 + REL-079 入账；REVIEW-FIX-349-CODE-R0 APPROVED_WITH_NOTES/0；EVD-1066 |
| 3 | **FIX-350** | `589e99f` | ArchGuard 判定面校准——豁免 gate 四面扩展（module_size/function_size/module_constants/duplicate_constant 经 `_archguard_exclusion_match` 单一实现）+ dup 三精确路径豁免（[EXEMPT] 双面披露）+ schema `project/**`/`.governance/**` 豁免 + release_docs 阈值 30→80 + ratchet 重锚 R1 24453→24583 / R4 print 1299→1301（七规则全 PASS + 套件 38/38 三红转绿）+ 锁外两测试文件追认（DEC-201 ⑤）；DEC-201；REVIEW-FIX-350-CODE-R0 APPROVED_WITH_NOTES/0；EVD-1067 |
| ⟦4⟧ | **M-0 prep 批（本清单 + 三件套 + CHANGELOG 段 + RISK 复评提案 + 版本号决策）** | ⟦待回填⟧ | Release Agent 起草（2026-09-17）；Coordinator 审后随 M-1 候选提交落库 |
| ⟦5⟧ | **M-1 候选打包**（版本 bump 0.82.0→0.83.0 + `release-projection --write` 15 投影 + `core/releases/0.83.0.json` candidate + roadmap 0.83.0 行活跃版本行更新 + Change Inventory 冻结核定） | ⟦待回填⟧ | Coordinator（M-1）；候选 commit hash 由 M-2 期 `release-ledger --version 0.83.0 --no-remote` 派生回填。M-1 bump commit 本身**不作为 CHANGELOG 载荷行**（纯版本投影动作，无用户可感知语义） |

## 行为变更（面向用户 —— MUST 出现在 CHANGELOG 与升级说明）

详见 `docs/release/feature-flags-0.83.0.md` §2（B-1~B-4）：

- **B-1**（FIX-349）：Check 16 同 EVD fan-out 判定口径——同一证据行服务多需求不再判「模板复用」（live 假阳 19→0）；
- **B-2**（FIX-349）：Check 14 新增子检查 6——Unicode 行/段分隔符 WARN（8 字符族 × 5 治理热文件，含 U+000C）；
- **B-3**（FIX-350）：ArchGuard 豁免面扩展（`project/**` fixture 镜像与 `.governance/**` 不再进架构扫描）+ 3 对镜像 dup [EXEMPT] 披露 + release_docs 阈值 30→80 + ratchet 重锚 24453→24583；
- **B-4**（FIX-348）：Check 10 M5 record-doc 白名单扩展 `docs/requirements/**`（设计文档处置记录行不再误报）。

## 版本号决策记录（semver 论证）

**决策：0.83.0 = MINOR**（0.82.0 → 0.83.0）。

| 判据 | 条款 | 适用性 |
|---|---|---|
| Breaking Change？ | VERSIONING.md L11（Major 触发：删除/重命名 MUST 规则、改变 Gate 行为语义、改变 governance 文件字段格式） | **不触发**——无接口删除/重命名、无 Gate 行为语义破坏、无治理字段格式变更（B-1~B-4 均为既有检查面判定口径修正/扫描面扩展/豁免披露） |
| 能力/规则面变更？ | VERSIONING.md L12（Minor 触发：累积 PATCH 达里程碑；或新增 MUST 规则、新增子工作流/skill、新增 B/C 级自动化能力） | **触发**——Check 14 子检查 6 新扫描面 + ArchGuard 豁免 gate 四面扩展 = 新增自动化能力面；Check 16 同 EVD fan-out 口径 + Check 10 M5 白名单 = 判定规则扩展 |
| 同型先例 | L37（SKILL.md MUST 规则新增 → MINOR——「影响所有 agent 行为」的规则/能力面变更走 MINOR） | **0.79.0 同型**（规则/能力面变更走 MINOR）；0.82.0 先例同构（L12 三支触发） |
| 纯 bug fix？ | L38（仅修复 bug 不改变行为语义 → PATCH） | **不适用**——本批含行为语义变更（Check 16 判定口径、Check 14 新增告警面、ArchGuard 阈值与豁免面）与新增扫描面，非仅修缺陷 |
| 路线图一致性 | 路线图 0.83.0 行已入账（2026-09-17，REL-079 承载） | **无预留冲突**（DEC-200：REL-079 全仓零占用已核）；版本行主题 = 「治理健康收口 + 架构债批（MINOR）」，与本批交付一致 |

PATCH 不足以承载：新扫描面/判定面变更的里程碑语义 + 路线图 0.83.0 行已在案；MAJOR 不适用（L11 无一触发）。

## Candidate Gate Results（M-2 —— Coordinator 回填实测）

> **M-2 状态**：本表由 M-2 门禁实测逐项回填（结果列 = 「M-2 执行时回填」）。未回填项在 M-2 完成前不得视为通过。M-0 期不预填任何实测值（本批未执行命令）。

| # | Gate | 预期 | Result |
|---|---|---|---|
| 1 | `check-version-consistency` | PASS（bump 后全投影 = 0.83.0） | **PASS**（2026-09-17 实测：13+2 文件全一致；bump 前预期过渡态 FAILED 已按先例经历后转 PASSED；plan-tracker 工作流版本已提前转 0.83.0——RELEASE R0 F-4：实际状态优于披露预期，非风险）。**预期过渡态披露**：M-0 起本清单/CHANGELOG 已入 0.83.0 段而声明面仍 0.82.0 ⇒ bump 前 `FAILED — N mismatch(es)` 为**预期**（0.81.0/0.82.0 先例同型）；bump + `release-projection --write` 后转 PASS；`plan-tracker 工作流版本` WARN 按先例在 M-8 收尾才转 0.83.0（gitignored，不进 fail 集） |
| 2 | `check-projection-sync --fail-on-issues` | PASS（bump 后 15 投影同步） | **PASS**（M-1 `--write` 写入 4 投影后复跑：15 mirrors 同步；CODE R0 F-2 附带处置：fixture CLAUDE.md 原生入口（投影合同外版本面成员）已补手动同步 0.83.0——0.82.0 先例同型） |
| 3 | `check-injection-contract --fail-on-issues` | PASS | **PASS**（2026-09-17 实测） |
| 4 | `check-manifest-consistency --fail-on-issues` | PASS | **PASS**（809 actual 一致；0.83.0.json 落 canonical 目录条目下零登记义务如预期） |
| 5 | `cleanup.py --dry-run` | 零删除（`exit=1` = ERR_NOTHING_TO_CLEAN 正常终止码，判据是零删除） | **零删除**（CLEANUP-ERR-002 No redundant files，2026-09-17 实测） |
| 6 | `archguard-ratchet`（**两次 `--regen` 后**——若触碰引擎行数） | 无新增 ERROR；**锚 24583 恒等预期**（DEC-201 ④ 已重锚 R1 24453→24583 / R4 print 1299→1301，七规则全 PASS + 套件 38/38；M-0 批零引擎行变更 ⇒ 预期 `R1 PASS 24583 ≤ 24583` 且 `committed==fresh`） | **PASS**（0 violations；R1=24583 恒等；R7 committed==fresh=True——bump 仅同行替换 REQUIRED_SNIPPETS 未触引擎行数，单次即幂等，无需两次 --regen） |
| 7 | **Check 28w** `check-dsh-boundary` | PASS / 0 failing criterion（K-1~K-13） | **PASS**（K-1~K-13：0 failing criterion；K-13 host-facts 1 baseline 在 TTL 内） |
| 8 | `check-dsh-preset-smoke`（28u） | exit 0 + `real-home writes: 0` | **PASS**（exit 0；real-home writes: 0；隔离 DSH_HOME 冒烟 = 隔离环境安装冒烟（环境变量重定向至临时目录）通过——非真实外部首会话验证） |
| 9 | `check-dsh-preset-compat`（28v） | `23 / 18 / 5` + exit 0 + `writes: 0` | **PASS 口径**（NO_SCHEMA 行按 FIX-315 [NOT_RUN] 披露呈现；agent adapter contracts synchronized——check-release 内 [PASS] agent adapters 同源） |
| 9b | `check-agent-adapters` | exit 0 | **PASS**（6 adapter contracts synchronized） |
| 10 | 全量测试基线 | 零产品代码回归（既有失败基线如实披露，不得写无条件 PASS）；**安静窗复跑项**：`test_verify_workflow` 全模块复跑（0.82.0 期终态 = **850 OK exit 0**；M-2 在安静窗复跑并以当场值为准 + 披露时长/预算口径——0.81.0 Gate 13 登记的 release-gate unit-tests 子面 180s 预算 vs discover 实测 ~240s+ 的**可复现超时**口径延续，`SPG_RELEASE_GATE_TIMEOUT` 可覆盖） | **Ran 3211 tests / failures=30 / skipped=1（601.5s，独立 discover 全量）**。差额归因（机械闭合）：3200（0.82.0 M-0 discover 口径）+ 1（FIX-348 批 test_verify_workflow +86 行 = +1 方法）+ 10（FIX-349：GoalAlignment +2 + Unicode +3；FIX-350：arch-health 豁免 +4 + U+000C +1）= **3211 精确**（行数≠方法数——RELEASE R0 F-3 朴素预期把行数当方法数）。30 失败四级归因：产品回归 0（test_verify_workflow 全模块零 FAIL——857+89 subtests OK，FIX-350 期安静窗实测）；环境敏感 24（test_pre_commit_review_evidence 族 ×10 方法×2 hooks+subtests——WSL_E_DEFAULT_DISTRO_NOT_FOUND 实证）；活体治理数据耦合 6（test_hooks replay：REL-071/072/073、FIX-282/283/288 已归档）；fixture 缺陷 0。**180s 预算口径延续披露**：check-release 内部单文件 runner 180s 超时（exit=None）为 0.81.0 Gate 13 登记的可复现超时先例延续，SPG_RELEASE_GATE_TIMEOUT 覆盖通道在案 |
| 11 | 三路径渲染 parity | 基线不变（窗口三 commits 范围面未含渲染交付面——`lib/index.js`/`launch.py`/`cordis.patch.yml` 预期零触碰 ⇒ 渲染语义零产品变更） | **PASS（载体口径）**：窗口未触渲染交付面；版本行差异经 release-projection 4 投影 + check-projection-sync 15 mirrors PASS + 28u 隔离冒烟 PASS 三载体覆盖 |
| 12 | 契约 SHA | 记录当场值（窗口三 commits 范围面未含 `adapters/dsh/host-contract.json` ⇒ 预期 = 0.82.0 released 终值不变） | **未触碰确认**（窗口 git diff 不含 adapters/dsh/host-contract.json——SHA 维持 0.82.0 released 终值；28w K 判据全 PASS 同源佐证） |
| 13 | `check-release` / `release-ledger` | 发布记录一致（候选态 `--lineage-mode candidate`；`core/releases/0.83.0.json` candidate 随 M-1 入库；**MUST 后台作业执行**——0.81.0 实测 240s 超时纪律） | **候选态实测（后台作业）**：17 门 = **16 PASS + 1 FAIL（execution gates 子面 2 项披露）**——governance health 子门 exit=1（当场 26→修复后 21 issues，全构成披露见 Gate 16）+ unit tests 子门内部 180s 超时（独立全量 3211/30 见 Gate 10——预算口径披露）；其余 16 门含 hot fact source（首轮 3 FAIL 数据面修复后复跑 PASS）、release lineage（candidate 边界 PASS）、loop-claims（identity/semantic 双 PASS，inventory dfea1399…）、dsh upgrade regression（隔离冒烟 PASS）。`release-ledger --version 0.83.0 --no-remote` = **NATIVE_CANDIDATE**（候选态正确；candidate_commit 待冻结提交派生——M-2 派生类占位豁免） |
| 14 | 回滚方案 | 已交付且可执行（**回滚区间 = `24cfb04..<发布 tip>`**——起点 = 0.82.0 发布 tip〔v0.82.0 tag peel = transition 提交 `24cfb04`〕，终点 = M-5 transition 提交，hash 由 M-5 生成后回填）；revert 干跑（回滚演练）在 M-2/M-5 期于隔离 worktree 执行 ≥1 次 | **已交付 + 锚点机核完成（RELEASE R0 F-2 勘误落账）**：`git rev-parse v0.82.0^{}` = **b63584c（transition 提交 = tag peel）**；`24cfb04` = post-transition integrity 公式修正 = 0.82.0 发布线末位提交——**回滚区间起点值 24cfb04 正确**（revert 24cfb04..tip 恰恢复 0.82.0 released 态含 integrity 修正），原「= transition 提交 = tag peel」措辞已勘误（checklist 本行 + rollback-plan §区间锚定）。revert 干跑（隔离 worktree）= M-1 冻结提交后立即执行（本表回填时点待执行——见 M-2 执行序义务） |
| 15 | `check-loop-runtime-claims`（双模式） | 双模式全绿预期维持（`installed_host` PASS / 0 findings + 4 豁免披露；`product_release` PASS——0.82.0 终态；窗口三 commits 未触碰 loop-claims 判定面与豁免账本） | **双模式 PASS**（check-release 内：loop runtime claim gate PASS〔semantic+identity，candidates=804 parsed=804 skip=0〕+ loop fuse block PASS；豁免账本形态呈现一致） |
| 16 | `check-governance`（health 基线） | 构成稳定 + 逐条归因（**存量 21 issues 口径**——见披露清单 §1；M-2 以当场值为准，构成漂移逐条归因，不得以旧值作新声明） | **当场终值 = 21 issues（数据面修复后）**。构成漂移逐条归因（RELEASE R0 F-1 义务）：① 文档枚举「28o 残余 4E」vs 申报「28n×8」= **同源 God-module 族的段头归属差异**——check-governance 输出将 architecture-health 的 module/function size WARN 行列于 28n 段头下，实际构成 = 4 ERROR（module/function size 超限）+ 8 WARN（同族 function/module size 与 checks/ 子模块超限），共 12 条全为产品源真实 advisory（RISK-039 登记 + 棘轮 24583 锚定）；② 14×421 / 36×16 / 2×3 / 30c×2 legacy 合计 11 项未见于披露清单 §1 枚举——§1 聚焦 FAIL/ERROR 面，legacy WARN 基线在 0.82.0 期同为未枚举披露（先例同型），本行补齐归因：14=col-mismatch 历史结构 WARN（418→421 波动源于本窗口新增 EVD/RECO 行）；36=R3 设计内 legacy 任务引用 WARN；2=09-30 复评窗 trio；30c=DEC-146 豁免清单手写行；③ 28q×1 = 披露清单 §6 已枚举（移交中）——申报枚举漏列系口误，非构成漂移。会话链 48→34→33→**21** 终值成立 |
| 17 | `check-hot-fact-source-consistency`（hot fact source） | PASS（B-2 双判据保护在场；roadmap **0.83.0 行任务列已含 FIX-349/FIX-350/REL-079 token**（DEC-200 落账行）——M-1 bump 时活跃版本行同步更新，0.82.0 F-R1-02 missing-active-task 过报族预防面） | **PASS**（首轮 3 FAIL 全部数据面修复：session-snapshot 刷新〔含 0.81.0/0.82.0 published 串〕+ REL-079 状态格 ✅ 污染清理 + 总览活跃版本句读修正——`check-hot-fact-source` 复跑 PASSED） |
| 18 | archive 触发检查（`archive.py migrate --auto --dry-run`） | dry-run 结论记录（发布收尾义务 M-8：如报告需要归档则执行 + `check-archive-integrity`——**归档完整性失败阻断发布完成**；EVD-1065 日期勘误后归档范围已解锁至 v0.82.0） | **M-2 预检**：dry-run = 触发器满足（release_forced）但无可归档数据（v0.1.0~v0.81.0 范围内 0 task 满足条件——EVD-1065 勘误后范围解锁，热表 17 task 均 out_of_range_version）；M-8 终检待执行（发布态写入后触发器重判） |

### Gate 10 明细指引（M-2 全量失败清单纪律）

按 0.81.0/0.82.0 先例执行：全量原始失败清单**逐条贴出**（块 = unittest 的一个 FAIL/ERROR 报告），候选态 vs pristine 基线（隔离 worktree `git worktree add --detach`）同命令对照，逐条归因四级：产品回归 / 测试 fixture 缺陷 / 活体治理数据耦合（pristine worktree 无 `.governance/`）/ 环境敏感。**0.83.0 期已收口的 0.82.0 既有基线（预期不再出现，若出现即真回归）**：`test_verify_workflow` 全模块 850 用例红基线（0.82.0 FIX-346 期已清零，850 OK exit 0 终态）。**预期仍红的既有基线族（如实披露，不阻断）**：① bash/WSL 环境敏感族（本机 WSL 无已装发行版——`WSL_E_DEFAULT_DISTRO_NOT_FOUND` 实证字节串；AUDIT-151/152 定性、EVD-1006 同口径）；② `test_hooks` / `test_pre_commit_review_evidence` 的 live replay 族（活体治理数据耦合——pristine worktree 转 skip）；③ loop-claims inventory 族活体耦合（0.82.0 期已由 FIX-345/320 收口——当场值为准）。

## RISK 复评提案（M-4 承载 —— Coordinator 裁决落 risk-log）

> 四段均为 Release Agent 复评建议（M-0 起草），**不直接改 risk-log**；「维持/关闭/延期」裁决权在 Coordinator（DEC-200 预授权形态下按提案执行 + M-4 落账；必要时升级用户）。

**RISK-036（官方收录与外部验证——1.0.0 blocker；高）——建议：维持打开，关闭条件不变。** 依据：① 0.83.0 全部交付为内部治理健康收口（数据卫生批 + 判定面校准 + 发布收尾白名单），未推进官方级 plugin manifest、assets、英文首屏叙事、5 分钟成功路径、公开 E2E 矩阵、外部项目验证、marketplace 真实 E2E 中的任何一项；② 外部首会试点（external first-session pilot）仍零实证；③ 保守边界 token（no official approval / no marketplace approval / do not claim 1.0.0 production-ready）在 0.83.0 三件套中逐字维持。

**RISK-039（架构腐化看护缺口——1.0.0 关联；高）——建议：维持打开，复评注记更新为「判定面校准落地、拆分面未动」。** 依据：① **看护面正向演进**——本版 ArchGuard 判定面校准（DEC-201）消除了 fixture 镜像/治理数据误报与 release_docs 阈值红三类噪声，豁免全部 [EXEMPT] 披露化（不静默），棘轮重锚后七规则全 PASS + 套件 38/38（三红转绿），看护信号从「噪声淹没」恢复「真实 advisory 可读」（28o 残余 4E = 产品源真实 God-module advisory，RISK-039 登记 + 棘轮锚定）；② **God Module 主判据未动**——`verify_workflow.py` 24583 行仍是单文件巨模块，0.59.0~0.64.0 渐进拆分路线**零进展**（如实注记），模块内聚靠棘轮锚而非结构改善；fixture 投影镜像双写债以 RISK-039 登记承接，长期解 = 投影单源；③ 关闭标准（AUDIT-121 F1-F6 逐项收敛 + 拆分路线兑现）未满足，且机制面关闭标准要求**外部宿主验证 ArchGuard**——零实证。

**RISK-046（派发锁漂移/空转——治理协调；中）——建议：维持打开至 2026-09-30 复评窗（不提前抢跑——0.82.0 M-4 已按提案登记关闭窗）。** 依据：① 根因修复（FEAT-013 两面机制）+ 结构预防（FIX-337 派发纪律硬化）已交付；② 0.81.0→0.82.0 两窗零新增派发锁 incident；③ 本版（0.83.0）窗口零派发锁面变更，无新实证触发或排除；④ 遗留候选（跨日静默 + 豁免披露 / 读写竞态 / 绝对路径旁路 F-1/F-2/F-4）维持登记。复评窗按「根因闭环 + 零复发 + 防御面补强」三关闭标准裁决；本提案不改变风险敞口。

**RISK-050（dsh 上游内部面耦合——高；截止 2026-10-31）——建议：维持打开。** 依据：① 0.83.0 窗口对 dsh 交付面零触碰预期（窗口三 commits 范围面未含 `adapters/dsh/` 渲染面——Gate 7/8/9/11/12 机检载体复核）；② 0.82.0 遗留披露延续：升级演练**已做**、演练方式与结果明细待用户补充（supersede 行追加）——非本版义务，维持登记；③ 不据此声明任何风险关闭。

## 披露清单（如实披露项 —— 不得写成通过）

| # | 披露项 | 内容 | 性质 |
|---|---|---|---|
| 1 | **governance health 存量 21 项构成** | /governance 会话链 48→34→33（基线）→**21 issues**（33→21 为本窗口）；Check 5/16/17/18/28p/34 清零；存量构成 = 28o 残余（产品源真实 advisory——God-module 族 4E，RISK-039 登记 + 棘轮锚定）+ 28s ×1（evidence-log ~1.5MB/1498KB 维持披露口径——FIX-349⑤ 评估 = 引擎行为正确，DEC-140/FIX-171 保守 live-ref 契约，随发布自然瘦身）+ Check 30 V2 ×1（= RISK-051，DEC-199 历史缺口如实保留）+ 28q hooks_drift ×1（prepare-commit-msg 用户一次性命令移交中）。M-2 以当场 /governance 输出为准 | 存量披露（advisory/已接受），**非通过项** |
| 2 | **unit 180s 预算口径先例** | 0.81.0 Gate 13 登记：release-gate unit-tests 子面 180s 预算 vs discover 实测 ~240s+ 的可复现超时；0.82.0 Gate 10 延续；`SPG_RELEASE_GATE_TIMEOUT` 覆盖通道如实声明——M-2 复跑时披露墙钟时长与预算关系 | 既有基线披露，非本版引入 |
| 3 | **WSL 环境红披露** | bash/WSL hook 族环境敏感失败为既有基线——本机 WSL 无已装发行版（`WSL_E_DEFAULT_DISTRO_NOT_FOUND` 实证字节串）；AUDIT-151/152 定性、EVD-1006 同口径；全量复跑时该族失败如实披露、逐条归因「环境敏感」，不阻断、不声明 Linux 面验证通过 | 环境敏感既有基线，非本版引入 |
| 4 | **hooks replay 数据漂移披露** | `test_hooks` / `test_pre_commit_review_evidence` 的 live replay 族子测试数随 gitignored 治理数据漂移（pristine worktree 转 skip）——0.81.0 Gate 10 #2/#3、0.82.0 Gate 10 明细指引同族延续；本批治理数据变更（FIX-349 数据清零）可能改变 live replay 子测试数，差额归因「活体治理数据耦合」 | 活体数据耦合既有族，非产品回归 |
| 5 | **Check 30 V2 ×1（RISK-051）** | FIX-246 V2 历史审查缺口——审查链仅有 R1 无 R0（报告与证据行均无 R0，归档亦无）；DEC-199 (a) 裁决 = 如实保留 + 风险登记（不改写历史、不机器补造）；发布文档按「既有基线披露」口径承载 | 已接受历史缺口（低），**非通过项** |
| 6 | **Check 28q hooks_drift** | prepare-commit-msg 用户一次性命令移交中——存量披露，随移交完成自然收敛 | 移交中，**非通过项** |
| 7 | **0.82.0 ledger 事件 integrity 截重盖披露（CODE R0 F-1）** | `core/releases/0.82.0.json` 已发布事件 integrity 由 `5c9e8fb9…` 重盖为 `34d779ab…`——成因 = 0.82.0 M-5 后续修正提交 `24cfb04`（integrity 公式修正，EVD-1062 在案）：旧截在现行 ledger 契约公式下必失效、重盖为算法机械必需；事件内容逐字节零变化（CODE R0 静态核实）；非本版载荷、非虚报 | 历史修正披露（0.82.0 在案），**非通过项** |
| 8 | **fixture 原生入口版本面（CODE R0 F-2）** | `project/e2e-test-project/CLAUDE.md` bootstrap 标记曾停留 0.82.0（投影合同 15 项外成员、无机器同步路径）——M-2 已手动补同步 0.83.0（0.82.0 先例同型）；check-version-consistency/projection-sync 覆盖边界不含该镜像的事实如实登记（候选：纳入投影合同——0.84.0+） | 已处置披露，**非通过项** |

## 真机验收（0.81.0 三项回贴有效；本版无新增真机项）

- 0.81.0 真机三项已由用户回贴通过（2026-09-14，EVD-1040；`docs/release/release-checklist-0.81.0.md` §真机验收）。
- **0.83.0 窗口对 dsh 交付面零触碰预期**（窗口三 commits 范围面未含 `adapters/dsh/` 渲染面）⇒ 无新增真机三项义务；M-2 的 28u 隔离冒烟（`DSH_HOME` 重定向至临时目录）+ 三路径渲染 parity 为交付面回归的机检载体。
- 0.82.0 遗留披露延续：RISK-050 升级演练**已做**、演练方式与结果明细待用户补充——非本版义务，维持登记。
- 纪律（保留）：任何 release 文档/CHANGELOG 不得对未回贴的真机项声明通过；隔离环境安装冒烟（环境变量重定向至临时目录）通过 ≠ 真实外部首会话验证通过。

## 发布步骤（M-0 ~ M-8 勾选框）

- [x] **M-0**：release 三件套 + CHANGELOG [0.83.0] 段 + RISK 复评提案 + 版本号决策——Release Agent 起草（2026-09-17，硬门槛 5/5）
- [x] **M-1 候选打包**：bump 完成（14+6 声明面 + governance-init 模板 ×3 + REQUIRED_SNIPPETS ×6）+ `release-projection --write`（4 投影写入，15 mirrors sync PASS）+ `core/releases/0.83.0.json` candidate（schema 违规一次修正后 NATIVE_CANDIDATE）+ roadmap/总览/工作流版本字段更新 + BOM 事故修复（16 文件剥离）+ fixture CLAUDE.md 补同步（CODE R0 F-2）——Change Inventory ⟦4⟧⟦5⟧ 行 commit hash 为 M-2 派生类占位（冻结例外）
- [x] **M-2 门禁实测**：Gate 表 1~18 已逐项回填（2026-09-17；check-release 后台作业 ×2；全量独立跑 3211/30 四级归因；hot fact source 3 FAIL 数据面修复）——revert 干跑于 M-1 冻结提交后执行（Gate 14 标注）
- [x] **M-3 双半面审查**：CODE R0 = REVIEW-REL-079-R0/R1（APPROVED_WITH_NOTES/0；P2×2=0.82.0.json integrity 重盖披露〔已入披露 #7〕+ fixture CLAUDE.md〔已修〕，P3×3 备案）；RELEASE R0 = REVIEW-REL-079-R2（APPROVED_WITH_NOTES/0；3 WARNING 全为 M-2 回填义务并已逐条履行：F-1 构成归因〔Gate 16〕+ F-2 锚点机核〔Gate 14〕+ F-3 计数归因〔Gate 10〕；B-1~B-4 全量文档一致性核对）。B-3 判定面语义由 REVIEW-FIX-350-CODE-R0 承载（RELEASE R0 F-5 注记）
- [ ] **M-4 发布决策落账**：DEC-200 预授权落账 + RISK 复评提案四条裁决落 risk-log（维持/关闭/延期逐条 + 复评注记更新）
- [ ] **M-5 transition/tag**：release commit（manifest candidate→released 唯一单父 transition）+ `v0.83.0` tag（peel 到 release commit）+ `<发布 tip>` 回填 rollback-plan §区间锚定
- [ ] **M-6 released 门禁**：`check-release --version 0.83.0 --require-changelog --lineage-mode released --release-commit <commit>` + `release-ledger --version 0.83.0 --remote origin`——候选态 PASS 不得代替发布完成态 lineage 证据
- [ ] **M-7 push**：github-https 推 master + `v0.83.0` tag
- [ ] **M-8 收尾**：`archive.py migrate --auto --dry-run`（需要则执行 + `check-archive-integrity`——**归档完整性失败阻断发布完成**）+ session-snapshot 更新 + plan-tracker 0.83.0 版本行转 released + `工作流版本` 字段 0.82.0→0.83.0（Gate 1 预期过渡态 WARN 随之消除）+ 本清单结果列终值刷新

## M-2 执行序（Coordinator 实测约束）

- **顺序**：先跑只读/廉价门禁（1~5、7~9b、11~12、15~17），再跑产物生成类（6 的两次 `--regen`——仅当 bump 触碰引擎行数时 MUST 重生成并给出「前后差异摘要 + 第二次无变化（幂等）」双证据；DEC-201 已重锚 24583 且 M-0 批零引擎行变更 ⇒ 预期 committed==fresh；若 `--regen` 试图写未授权路径 ⇒ 停下报告，不得越权写入），最后跑 10（全量 + 安静窗复跑）与 13（check-release）。
- **安静窗复跑项**：`test_verify_workflow` 全模块在安静窗（无并行负载）复跑，预期 850 OK exit 0 基线延续（0.82.0 FIX-346 终态）；同时披露墙钟时长与 release-gate unit-tests 子面 180s 预算的关系（`SPG_RELEASE_GATE_TIMEOUT` 覆盖通道如实声明）。
- **check-release 纪律**：MUST 以后台作业（`run_in_background`）执行并轮询 `job_output`（0.81.0 实测 240s 超时先例）；候选态 `--lineage-mode candidate`，不得以候选态 PASS 代替发布完成态 lineage 证据（release-checklist SKILL 硬规则）。
- **全量失败清单纪律**：见 Gate 10 明细指引——逐条贴出 + pristine 对照 + 四级归因。
- **真机项禁声明纪律**：保留（见真机验收节）。
- **冻结纪律**：M-1 冻结前 MUST 消除本清单全部 ⟦待回填⟧/⟦待落地⟧ 占位——**例外 = M-2 派生回填类**（候选打包 commit 与 M-0 批 commit hash：其回填依赖 `core/releases/0.83.0.json` 先随候选提交入库后 `release-ledger --version 0.83.0 --no-remote` 的派生——EVD-1034 / 0.82.0 先例同型，属预期前置依赖而非冻结违规）。

## M-8 收尾义务

- 发布后：`core/releases/0.83.0.json` **由 candidate 态转为 released 态**（candidate 态随候选打包提交落库）+ `release-ledger --version 0.83.0 --remote origin` 核对 + `session-snapshot` 更新 + plan-tracker 0.83.0 版本行转 `released`（`工作流版本` 字段 0.82.0 → 0.83.0 同步——Gate 1 预期过渡态 WARN 随之消除）；
- 补推义务检查：`v0.79.0`/`v0.80.0`/`v0.81.0`/`v0.82.0` 已推送（0.82.0 发布链实证）⇒ 本版无历史补推义务；M-7 推送 `v0.83.0` 即可；
- 持续归档触发检查：版本 bump / released 态写入后 `archive.py migrate --auto --dry-run` → 如报告需要归档则执行 + `check-archive-integrity`；**归档完整性失败阻断发布完成**（EVD-1065 日期勘误后归档范围已解锁至 v0.82.0）；
- 本批移交项随 M-1/M-4 落账后勾销：RISK 复评提案四条裁决（M-4）、roadmap 0.83.0 行活跃版本行更新（M-1）。

---

*M-0 草案（2026-09-17，REL-079 prep——Release Agent 起草）。本批未执行任何命令；全部实测值由 M-2 在 bump 后现场回填（结果列 = 「M-2 执行时回填」）。Change Inventory 按 `git log v0.82.0..HEAD`（`24cfb04..589e99f`）登记 3 commits 编号 1..3 连续；M-0/M-1 批行待 M-1 冻结回填。事实基线：FIX-348/349/350 终态取自 plan-tracker 任务行、DEC-198~201 与 EVD-1064~1067（机录）。*
