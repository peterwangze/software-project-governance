# Release Checklist — 0.85.0（REL-081 / FEAT-054 M-1R）

> **M-1R 草案（FEAT-054，2026-09-20）**——Governance Developer Agent 起草、供 Coordinator 审后随候选提交；结构与措辞对齐 `docs/release/release-checklist-0.84.0.md` 先例。**本文件中的 M-2 数值全部为 2026-09-20 当场实测值**（命令输出原样摘录），未实测项一律标「M-5 期义务/未执行/待回填」，不预填。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.85.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.85.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版全部验收在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）类口径下完成——**隔离环境安装冒烟（环境变量重定向至临时目录）通过**不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；0.85.0 为内部治理效率版；do not claim 1.0.0 production-ready。
- **发布 tip 未生成前不预先编造**：`<发布 tip>`（M-5 transition 提交）与 tag 事实本文件不预填。

## Release Scope

| 项 | 值 |
|---|---|
| 版本号 | **0.85.0**（MINOR；semver 论证见下节） |
| 发布任务 | **REL-081**（DEC-216 M-0 裁定 + DEC-217 全链预授权；M-1 开发面 = FEAT-053 `a91d6b4`；M-1R 发布面 = FEAT-054 本票） |
| 承载决策 | DEC-214~221（8 决策；DEC-216 MINOR 两批制 / DEC-217 预授权 / DEC-218 条件 go / DEC-219 外扩削减面） |
| 核心范围 | 批 1 降噪/机检面七修复（FIX-356~362）+ 批 2 瘦身与门禁翻转关键路径（FEAT-041/050/052）+ ⑥ 治理面（M-0 + 8 DEC + 20 EVD）+ M-1 打包（FEAT-053）+ M-1R 发布面（FEAT-054） |
| 目标版本下不发布 | ① 0.86.0 架构演进全链（DEC-220/221——FEAT-042~048 候选池）；② 混沌测试发布门（0.86.0 批 2.2 承载）；③ RISK-055 终态裁决（纯净复采未到期）；④ resident 4K arch 目标与 skill 层翻硬；⑤ FIX-363 非族 3 项（loop-runtime-claims 活体耦合）；⑥ 任何 RISK 关闭声明 |
| 时间窗口 | 2026-09-19 M-0 裁定 + 17 提交载荷窗口全日落库 + M-1 打包 → 2026-09-20 M-1R 材料与 M-2 门禁实测 → M-3 双审 → M-4/M-5 另记（taggerdate 权威） |
| Single-Threaded Owner | Coordinator（发布决策与 `.governance/` 写回）；M-1R 材料由 Governance Developer Agent 起草，Release Reviewer 独立审查 |
| 用户获得方式 | `/plugin update`（或 `git pull` + reload）；旧安装升级路径兼容——FEAT-041 契约 v2 整段替换零残留（「详细规则」H2 恢复 = 边界集超集已验证，CHANGELOG B-1 已声明） |

## Change Inventory（**17 个窗口提交** — `git rev-list --count 3663423..1cd224e` = 17，2026-09-20 实测）

> 窗口起点前一位 `3663423` = 0.84.0 manifest canonicalize 提交；`v0.84.0` tag peel = transition 提交 `5d1943f`（`git for-each-ref refs/tags/v0.84.0` 实测）。`1cd224e` = 本版窗口载荷 tip（当前 HEAD）。任务简报所引 `be0b844..1cd224e` = 16 提交（git 区间排除下界自身）；含 FIX-356 首票的完整载荷清单如下（17 项，git 时间序）：

| # | commit | 任务 | 关键交付 | 证据 |
|---|---|---|---|---|
| 1 | `be0b844` | FIX-356 | governance_cost workspace 过滤真实语料修复（0→156 sessions/22 TTFA；RISK-055 机制修复） | EVD-1088/1089 |
| 2 | `d62066b` | REL-080 | 0.84.0 R6 发布审查报告补提交（**上一版发布线尾巴——交错在窗口内，见披露 ②**） | REVIEW-REL-080-R6 |
| 3 | `6325ee6` | REL-081 M-0 | 双半面规划闭环 + 双审 R0→R1 通过 + 用户裁定 MINOR 两批制 | EVD-1090 |
| 4 | `c7b515a` | FIX-360 | sessions[].cwd 双源语义 CALIBRATION 披露行 | EVD-1093 |
| 5 | `11289be` | FIX-359 | RISK-056 回放族 30 项既有失败收敛（匹配器族 30→0） | EVD-1094 |
| 6 | `25aef9f` | FIX-357 | C-01 终态豁免行因果断言措辞按来源分流 | EVD-1095 |
| 7 | `5a4c4f4` | FIX-362 | governance-status.md fixture byte_copy promote（投影合同 27→28 面） | EVD-1096 |
| 8 | `399c48a` | FIX-358 | 归档谓词并集五件套（13 散文格 ID 漏判收敛 + M4 突变击杀） | EVD-1097 |
| 9 | `2e80c69` | FIX-361 | 测试静态版本钉 WARN-only 机检面（DEC-213③；豁免账本 10 行） | EVD-1098 |
| 10 | `b717835` | FEAT-041 | 入口模板契约 v2 全量推开——resident 双达标 5,694/5,966 ≤6,000（DEC-218/219） | EVD-1099/1100/1103 |
| 11 | `27eeea0` | FEAT-049 | M0 契约冻结 m0-r1（0.86.0 批 0 前置——随树入库，零行为消费，CHANGELOG 披露⑤） | EVD-1105 |
| 12 | `407b230` | FEAT-050 | 注入预算 resident 翻 hard + FEAT-039 P3-3 同 commit（DEC-211③） | EVD-1106 |
| 13 | `1519bf1` | FEAT-052 | skill 层独立预算线 16,000 + F 族清理（DEC-215⑧） | EVD-1107 |
| 14 | `bff298d` | FEAT-047 | BaselineMetadata provenance 机制（0.86.0 批 1 票 3——随树入库） | EVD-1108 |
| 15 | `a91d6b4` | FEAT-053 | **M-1 版本 bump + 候选打包**（24 tracked：手工 5 + 再生 19 + CHANGELOG 段 + 豁免账本 10 行） | EVD-1109 |
| 16 | `b2152ea` | FEAT-051 | task-row-update 写入器 CLI（0.86.0 批 1 票 1——随树入库，M-1 后落库） | 0.86.0 链 EVD |
| 17 | `1cd224e` | FEAT-046 | governance_store 写入器族（0.86.0 批 1 票 2——随树入库，M-1 后落库） | 0.86.0 链 EVD |

**M-1R prep 批（本提交）**：release 三件套（plan/checklist/rollback）+ feature-flags（修复回合补授）+ `core/releases/0.85.0.json`（candidate manifest）+ 两处一行修（SKILL.md:121 前缀 / version-plan ragged row——Coordinator 修复回合指令②③，锁外披露先例）+ fixture SKILL.md 投影再生（`release-projection --write` written=1）。

**版本 bump 平面清单（M-1 = `a91d6b4` 已执行，EVD-1109 口径）**：

| 平面 | 载体 | 值 |
|---|---|---|
| 权威源 | `skills/software-project-governance/SKILL.md` frontmatter | **0.85.0** |
| JSON 声明面 / hook 版本行 / canonical 模板标记 / DSH 方言面 / 入口投影 / fixture 面 / `REQUIRED_SNIPPETS` 六锚 | 再生 19（`release-projection --write` written=16 + entry 双根）+ 手工 5（SKILL frontmatter / 6 版本锚 / 豁免账本 10 行 / CHANGELOG 段 / canonical 标记——FEAT-041 契约 v2 后 4→3） | 全部 **0.85.0**（24 tracked——EVD-1109 Reviewer 独立复验 8 项全过） |
| ledger manifest | `core/releases/0.85.0.json` | `lifecycle_state: candidate`（唯一 transition 由 M-5 追加） |
| plan-tracker `工作流版本` | `.governance/`（gitignored） | 仍 0.84.0（**过渡态 WARN**——M-8 收尾由 Coordinator 更新为 0.85.0；check-version-consistency 2026-09-20 实测 1 WARN 在案） |

## 行为变更（面向用户 —— CHANGELOG 0.85.0 段已载，本表为索引）

| # | 变更 | 任务 | 性质 | 回退通道 |
|---|---|---|---|---|
| **B-1** | 入口模板契约 v2：自包含全文 → 触发器行内 + 明细按需（resident 5,694/5,966 砍半；升级路径兼容 = 边界集超集） | FEAT-041 | 注入形态（协议结构） | **无 flag 级降级——版本级回滚**（CHANGELOG B-1 已声明） |
| **B-2** | 注入预算 resident 层 standard/strict 从 ADVISORY 翻 **FAIL 硬门**（超 6,000 tok 直接 FAIL，fail-closed；skill/command 层维持 report-only） | FEAT-050 | 门禁硬化 | **无 flag 级降级——版本级回滚**（CHANGELOG B-2 已声明） |

## 版本号决策记录（semver 论证——CHANGELOG 0.85.0 段同口径）

- **MINOR（0.84.0 → 0.85.0）**：VERSIONING.md L12「新增 B/C 级自动化能力」（FIX-361 静态钉机检面 / FEAT-052 skill 层独立预算线 / FEAT-049 契约基座）+ L37（FEAT-041 入口模板协议变更——SKILL.md §B 明细承接结构变化）；
- **非 PATCH**：L38 口径不适用——主体为协议结构与门禁姿态变更，非纯缺陷修复；
- **非 MAJOR**：L11 口径逐项核对均不成立（无 MUST 规则删除/重命名、无 governance 文件字段格式变更）；FEAT-050 翻 hard 属**门禁硬化**（既有预算线 advisory → fail-closed 强制化），判定方向与 0.84.0「注入预算判定姿态」MINOR 先例同域，L11 pre-1.0.0 括注覆盖（DEC-216 semver 处置段同口径）；**Breaking changes = 无**；
- **版本号未占用预留**：0.85.0 = REL-081 承载版本（DEC-216 用户 M-0 裁定）。

## Candidate Gate Results（M-2 —— 2026-09-20 实测）

| # | 门禁 / 命令 | 结果 | 关键实测值 |
|---|---|---|---|
| 1 | `check-version-consistency` | **PASSED**（exit 0） | 源 = 0.85.0；13 面 + 双入口 marker 全一致；**1 WARN**：plan-tracker `工作流版本` 仍 0.84.0 → M-8 收尾更新（0.81.0~0.84.0 M-1 先例同型过渡态）。**静态版本钉豁免账本落库复核（FEAT-053 边缘④义务）：零 stale 告警**——10 行（`checks/version.py` STATIC_PIN_EXEMPTIONS 0.85.0-tokened：bootstrap_aggregate ×1 + baseline_metadata ×6 + task_row_update ×2 + static_version_pins ×1 = 1+6+2+1）全部行号/token 有效（随树落库的 test_baseline_metadata.py / test_task_row_update.py 行号未漂移，stale 豁免机检自动兜底在案未触发） |
| 2 | `check-injection-budget`（×3 profile，**hard**） | **PASSED ×3**（exit 0） | resident：lightweight **4,216**/6,000 · standard **5,694**/6,000 · strict **5,966**/6,000（strict 余量 34 tok = 0.57%，EVD-1104 接受现状裁决）；skill：entry-skill **14,456/16,000** ok（report-only）；command：3,466/6,000 report-only；`Over budget — gated: none`；翻 hard 姿态生效（`resident hard gate` 字样当场输出） |
| 3 | `check-projection-sync --fail-on-issues` | **PASSED**（exit 0） | entry：CLAUDE.md=9,552B/full、AGENTS.md=2,834B/thin（repo-root 与 fixture 同值，profile=standard）；DSH 方言互认 present（3,402B/38L） |
| 4 | `check-entry-bootstrap-sync` | **PASSED**（exit 0） | 与 #3 同值（契约 v2 后 bootstrap 段 9,552B/full + 2,834B/thin） |
| 5 | `release-projection`（check-only） | **PASS**（`"state": "PASS"`, issues 空） | source_version = **0.85.0**；projections_checked = **28**（FIX-362 后合同面）；declared legacy snapshots 10（pass） |
| 6 | `check-cross-references` | **PASSED（修复回合终态）** | 初测（00:4x）1 dangling：`skills/software-project-governance/SKILL.md:121 -> archive/index.md`——FEAT-041（`b717835`）契约 v2 迁入 §B1 时的行内简写（实指 `.governance/archive/index.md`，文件存在；检查器按仓库根解析判悬空）。**Coordinator 修复回合指令②已修**（`.governance/` 前缀补全，一行）→ 复跑 **0 dangling / 0 deprecated / 0 circular** |
| 7 | `check-manifest-consistency` | **PASSED** | canonical 813 / actual 917（0.84.0 期 769/870 → 本版随批 1/2 新测试与文档面自然增长） |
| 8 | `archguard-ratchet` | **PASS**（0 violations） | R1 24,769 ≤ 24,769；R2 47 ≤ 47（37 文件）；R3 SCC max 1（unmanaged refs 1 disclosed）；R4 print 1,304 ≤ 1,304；R5 cli keys **88/88** + segments **71/71**；R6 199 modules（advisory，Δ0）；R7 regen deterministic=True / committed==fresh True |
| 9 | `release-ledger --version 0.85.0 --no-remote` | **FAIL — 预提交态预期**（exit 1；2026-09-20 实测） | 唯一 issue：`candidate_commit: expected exactly one commit adding core/releases/0.85.0.json, found 0`——manifest 已入索引（staged）、**尚未提交**，`trust.candidate_commit.derivation = git_commit_adding_path` 不可由 git 派生；其余结构面全过：`trust_level=NATIVE_CANDIDATE` / `effective_state.candidate` / canonical bytes 校验过（初稿缺 trailing LF 被本检查当场拦下，按 `canonical_json_bytes` 重写后 CANONICAL-OK）/ events 空表合法（`event_identity_digest=37517e5f…`）。**这是 M-1R 后、commit 前的正确观测值，不包装为 PASS**；Coordinator 提交后 MUST 复跑（期望 PASS / `candidate_commit` 派生成功）；M-5 tag/push 后 `--remote origin` |
| 10 | `check-release --version 0.85.0 --require-changelog --lineage-mode candidate`（SPG_RELEASE_GATE_TIMEOUT=600） | **FAILED — 2 issue(s)（修复回合终态；初测 7 → 修复后 2，两轮实测 2026-09-20）** | **PASS 面（16 门全绿）**：version consistency / release fact source / runtime readiness / first session measurement / governance pack / agent adapters / **projection sync（修复回合 `release-projection --write` 再生 fixture SKILL.md 投影 written=1 后 PASS）** / **cross references（修复②后 PASS）** / archive integrity / **release docs（feature-flags 补授后四件套全过——tracked/boundary token/version/overclaim 检查全绿）** / release lineage（candidate 模式）/ gate sequence / one dot zero blockers / changelog / **dsh upgrade regression（隔离 temp-DSH_HOME 冒烟 PASS——零真实宿主写入）** / **unit tests（exit 0——修复回合 ragged row 修正后 LRC 族转绿）** / **loop runtime claim gate（semantic PASS + identity PASS，inventory `4d2f1186…`，candidates 911）**。**余 2 项（均为 Coordinator 收口面，如实披露）**：① hot fact source（`.governance/session-snapshot.md` 缺 0.81.0 发布行引用 + S1b 快照 2026-09-19 stale——M-7/M-8 收口，0.84.0 M-2 期同门 FAIL→M-7 收口先例）；② governance health `--fail-on-issues` exit 1（48 issues 计数含 WARN 族 + **Check 18c REL-081 execution packet 契约 FAIL ×5**——Coordinator `execution-packet` 更新面；0.83.0 Gate 16 = 21 / 0.84.0 收口态 = 20 同型披露先例）。**演进链**：初测 7（hot-fact 1 + cross-ref 1 + release-docs 1 + gov-health 1 + unit-tests 1 + LRC 2）→ 修复回合四动作（feature-flags 补授 + SKILL.md:121 前缀 + version-plan ragged row + 投影再生 written=1）→ **2（全部 Coordinator 收口面）** |
| 11 | `e2e-check` / `verify` 全量（随 #10 执行闸门） | **PASSED ×2**（exit 0） | verify（exit=0）全量资产 + 适配器契约同步；e2e-check（exit=0）；runtime adapters static（未加 `--runtime-adapters`——本机 agent runtime 检查由 dsh upgrade regression 隔离冒烟面承载） |
| 12 | `check-governance`（安静窗） | **48 issues**（exit 1 经 `--fail-on-issues`——all_issues 计数含 WARN 族；0.83.0 Gate 16 = 21 / 0.84.0 收口态 = 20 同型披露发布先例） | **构成主项（2026-09-20 当场）**：① **Check 18c/18 族 REL-081 execution packet 契约 FAIL ×5 行**（allowed_change_scope 过宽 / product_success 缺用户可见结果 / acceptance last_run 非 PASS / quality_budget 多字段不满足 / vertical_slice 非 PASS——packet 为 M-1 开发面形态，发布态复检不满足产品任务契约字段；**收口 = Coordinator `execution-packet` 更新或裁决**，0.84.0「Check 18c ×6 → packet 填充收口」同型）；② **hot fact source**（snapshot 缺 0.81.0 引用 + S1b 快照 2026-09-19 早于治理文件修改 2026-09-20——fail-safe WARN 降级语义在案；Coordinator M-7/M-8 收口）；③ **LRC ×2——修复回合已消**（version-plan-0.85.0.md ragged row 修正后 check-release 终验 LRC gate semantic/identity 双 PASS）；④ **Check 30 R3 legacy 跨实体 WARN ×8+**（RISK-002/004/007/010~014 引用归档外任务——历史族，design R3 WARN 非 FAIL）；⑤ 其余 legacy/advisory 族（untracked 0.86.0 规划文档 / God-module 28n 族 / stale risk 复评窗族 / structural 历史族——0.84.0 披露 ① 同族延续）。**FAIL 面窄于计数**：修复回合后实际 FAIL 级 = 18 族 packet ×5 + hot fact ×1（LRC ×2 已消），其余为 WARN/ERROR advisory（不阻断语义由 fail-safe 降级保持） |
| 13 | 全量测试套件（`python -m pytest skills/software-project-governance/infra/tests/ -q`，M-1 bump 后全量） | **主跑（00:41，修复回合前）：6F / 3747P / 1 skipped / 510 subtests（1103.24s）；修复回合复跑同批：5 项转绿、仅剩 1 项（见 #14）——0 新增失败** | 主跑 6 失败构成：**5 项 = review_doc_claim 族**（FIX300DualCaliber ×2 + LoopRuntimeClaim inventory ×1 + 同族 performance_identity ×1 + claim_command adapter ×1——即时成因 = M-0 引入的 version-plan ragged row ACCOUNTING finding + review-FIX-300 族/DEC-104 归档 co-cause；AUDIT-152 账本快照早于 M-0 故未载 ragged row）；**1 项 = `test_resolve_entry.py::test_snapshot_freshness_recent_is_fresh`**（午夜窗口时间敏感——见 #14⑥）；1 skipped = GBK 负控按设计 skip。check-release 内嵌 unit tests 闸门：修复回合前 failures=3（同族子集）→ **修复回合后 exit 0（905 tests 全绿）**，两口径演进如实并记 |
| 14 | 三先在失败归因复核（FIX300DualCaliber ×2 + LoopRuntimeClaim——HEAD worktree 法） | **✅ 已执行——初测 6/6 在干净 HEAD 逐项同形复现；修复回合后同批复跑 5 项转绿、1 项保持（午夜窗内 01:15 复跑仍红，与数据/代码修复无关）** | 方法与演进：① `git worktree add %TEMP%\feat054_head_attr HEAD`（detached `1cd224e`，不含本票文件）复跑 6 用例 = **6 failed / 1 passed（222.82s）逐项同形** ⇒ 初测 0 新增失败成立；② **修复回合（version-plan ragged row 修正）后**同批复跑 = **1 failed / 6 passed（316.26s）**——FIX300DualCaliber ×2 + LoopRuntimeClaim inventory + performance_identity + claim_command adapter **全部转绿**（ragged row 系该族即时的 ACCOUNTING 成因——豁免账本 digest 未覆盖 M-0 新引入项，修正后 engine 直调亦 PASS）；③ 唯一余项 `test_snapshot_freshness_recent_is_fresh` 在 01:15 复跑仍红——**午夜窗口时间敏感**（fixture `_write_snapshot` 落 date-only `session_date`，引擎按当日 00:00 解析、freshness=now−date≤24h；00:00~02:00 本地窗内 now−2h 跨日判 stale；temp-dir 全隔离 fixture，与活体数据/本票改动无关；02:00 后可复跑自愈验证）。建议处置 = **FIX-364 候选**（fixture 以引擎同口径取日期粒度）+ AUDIT-152 账本补登记。worktree 已清理（`git worktree remove --force`） |
| 15 | M-2 revert 干跑（回滚演练） | **未执行（如实标注——本票无演练义务票面）** | 0.84.0 演练由 FIX-354 专项承载（隔离副本法，rollback-plan §演练记录先例）；0.85.0 批内无对应演练票。回滚区间结构核对（git 区间语义 + 交错提交分析）已入 `rollback-plan-0.85.0.md` §区间锚定。是否补演练 = M-3 审查/Coordinator 裁决；本票不预填演练结果 |

**M-2 执行序纪律**（0.84.0 先例沿用）：①安静窗——涉及 candidate 集合枚举的检查（Check 31）MUST 无并发写盘，首轮假阳如实记录；②顺序：check-version-consistency → check-injection-* → check-projection-sync → check-entry-bootstrap-sync → release-projection → check-cross-references → check-manifest-consistency → archguard-ratchet → release-ledger → check-release（candidate）→ 全量 pytest；③每个 FAIL 逐项落披露，不以「已知」豁免；④`SPG_RELEASE_GATE_TIMEOUT=600` 覆盖 unit tests 闸门预算（本机套件实测 >180s）；⑤tag 生成后 MUST 复跑 `check-release --lineage-mode released --release-commit <commit>` 与 `release-ledger --version 0.85.0 --remote`。

## Gate 10 明细指引（M-2 全量失败清单纪律）

- 任一 FAIL 不得以「已知/预期」名义归类为通过——FAIL 项全部保留在披露清单；
- `check-governance` 的 FAIL/WARN/ERROR 均逐项列明归属（检查号 + 载体 + 处置人）；
- 先在失败归因 = HEAD worktree 复跑对照法（本票 #14）——归因为「与本票改动无关的既有失败」必须给出对照证据，不得口头断言。

## 三先在失败归因复核（M-2 义务——FIX-363 候选非族 3 项）

> 口径源：CHANGELOG 0.85.0 段 Fixed（「非族 3 项转 FIX-363 候选」）+ `infra/tests/env_failure_classification.json`（AUDIT-152 分类账本，data_coupling / review_doc_claim 族）。归因方法 = HEAD worktree（`git worktree add` 于 `%TEMP%`，HEAD = `1cd224e`，不含本票未提交文件）复跑同批用例对照。**实测结论（2026-09-20，两轮）**：初测（修复回合前）任务简报所指「三先在」= FIX300DualCaliber ×2 + LoopRuntimeClaim inventory ×1 均在 HEAD 同形复现，6/6 全部在 HEAD 复现（含同族 performance_identity / claim_command adapter 与午夜窗 snapshot freshness）——初测态 0 新增失败成立；**修复回合（version-plan ragged row 修正）后同批复跑 5 项转绿**（ragged row 系该族即时的 ACCOUNTING 成因——M-0 引入、晚于 AUDIT-152 快照故账本未载），唯一余项 snapshot freshness 为午夜窗口时间敏感（01:15 复跑仍红；02:00 后可复跑自愈验证）——**→ FIX-364 候选（Coordinator triage）**。worktree 已清理（`git worktree remove --force`，`git worktree list` 复核仅余主树）。

## 披露清单（如实披露项 —— 不得写成通过）

① **门禁既有披露项**：check-governance 既有族（Check 28s evidence-log 体积 advisory / 28n God-module 族 WARN〔RISK-039 棘轮锚定〕/ legacy 段历史 WARN / 28q hooks_drift〔DEC-213④ 接受态〕/ stale risk 复评窗未到期族）——当场构成与计数以 #12 实测回填为准，不沿用旧值作新声明。

② **本版披露（修复回合后终态——①③④ 已由 Coordinator 裁决收口，⑤⑥ 仍开放）**：
   - **feature flags 面文档缺位——✅ 已收口（修复回合，裁决 = 处置选项 (a)）**：Coordinator 补授最小形态 `docs/release/feature-flags-0.85.0.md`（B-1/B-2 无 flag 级降级——版本级回滚唯一路径 + 灰度开关边界 + 未发布面 N/A）；release-docs 门禁 missing 项消；首版补授的 §6 自检表 token 字面枚举行被 overclaim 检查拦截（局部子句无否定形态）——已改写为「齐备于保守边界声明节」指针形态，overclaim 扫描 CLEAN（`_line_has_scoped_claim_negation` 逐行实证）。
   - **CHANGELOG 与窗口对照缺口——→ DEC-222 承载 0.86.0（Coordinator 裁决）**：窗口 17 提交中 FEAT-051（`b2152ea`）/ FEAT-046（`1cd224e`）在 M-1 CHANGELOG 冻结（`a91d6b4`）后落库、无 CHANGELOG 登记；FEAT-047（`bff298d`）仅于 FEAT-052 行括注。CHANGELOG 冻结不再改（并行约束）；四票均为 0.86.0 轨道（0.85.0 零行为消费）。
   - **SKILL.md:121 dangling——✅ 已修（修复回合指令②）**：`.governance/` 前缀补全一行；check-cross-references 复跑 0 dangling（见 #6）。
   - **version-plan-0.85.0.md ragged row——✅ 已修（修复回合指令③，锁外披露先例）**：硬门槛自检表 4 行判定/依据合流列补切（`| **PASS** |`），消 LRC gate ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY + IDENTITY_ATTESTATION_FAIL 两项；连带使 LRC 族 5 个 engine-直调测试转绿（见 #14）。
   - **plan-tracker `工作流版本` = 0.84.0 过渡态 WARN——仍开放**：M-8 收口（Coordinator），check-version-consistency 实测在案。
   - **发布执行闸门余 2 FAIL——仍开放（Coordinator 面）**：hot fact source（session-snapshot）+ governance health（REL-081 packet ×5）——见 #10/#12。

③ **豁免账本双账本状态**：版本钉豁免 10 行（FEAT-053 边缘④义务）——本票 #1 复核零 stale，随树落库后行号全部有效；LRC 豁免账本（`core/loop-runtime-claim-exemptions.json`）4 条维持打开（FIX-300 报告族 ×3 + 0.81.0 checklist ×1）——均为已发布产物记录性文本豁免，与本版新增文档无关（本三件套按记录性/非主张措辞起草，不新增 LRC 发现）。

④ **release-ledger 提交前态（2026-09-20 实测回填）**：`release-ledger --version 0.85.0 --no-remote` = **FAIL（exit 1）**，唯一 issue = `candidate_commit: expected exactly one commit adding …, found 0`（提交前 `git_commit_adding_path` 不可派生）——0.84.0 #15 同款**预提交态预期观测**，不包装为 PASS；canonical bytes / effective_state / trust_level（NATIVE_CANDIDATE）全部结构过。**复跑义务**：Coordinator 候选提交后复跑（期望 PASS）+ M-5 tag/push 后 `--remote` 复跑（期望 NATIVE_RELEASED；`UNKNOWN`/`BLOCKED` 不得包装为 PASS）。

⑤ **no-overclaim**：official approval / marketplace approval / universal runtime support / external first-session pilot success 均未被主张；RISK-036 打开，1.0.0 就绪未被主张。

⑥ **回滚安全弱化面**：回滚到 0.84.0 即整体恢复两处弱化——(a) B-1 契约 v2 消失 = resident 注入回升至 0.84.0 形态（4,957/10,718/10,918，注入成本回升）；(b) B-2 硬门消失 = standard/strict 预算判定回降 ADVISORY（预算回弹防护弱化——0.84.0 期 RISK-057 姿态）。两者均无 flag 级中间态（版本级回滚，rollback-plan §1/§5）。

## 发布步骤（M-0 ~ M-8 勾选框）

- [x] **M-0 预检**：工作树 HEAD = `1cd224e`；11 个 untracked 文件均为 0.86.0 规划/REL-082 审查文档（不在本票范围，不触碰）；无 staged 脏文件
- [x] **M-1 版本 bump（全平面）**：`a91d6b4`（FEAT-053）——24 tracked 面 + 投影 28 面 + CHANGELOG 段 + 豁免账本 10 行（EVD-1109）
- [x] **M-1R 发布材料**：本三件套 + `core/releases/0.85.0.json`（candidate；canonical bytes——NFC/sorted/compact/trailing-LF）
- [x] **M-2 快速门禁**：#1~#8 实测（2026-09-20；FAIL 项已披露）
- [x] **M-2 复合门禁**：#10~#14 已实测（2026-09-20 安静窗，含修复回合终验）——check-release 终态 **FAILED/2 issues**（7→2：余 hot fact source + governance health，全部 Coordinator 收口面；其余 16 门全绿）；全量 pytest 初测 6F/3747P → 修复回合后同批 5 项转绿、余 1 项午夜窗时间敏感（#13/#14 归因闭环）
- [x] **M-3 前置材料**：本清单 + release-plan + rollback-plan 就绪，供 Release Reviewer / Design Reviewer 双半面审查
- [ ] **M-3 双半面审查**：Release Reviewer + Code/Design Reviewer（按变更面）；review-record 机录；复审必达
- [ ] **M-4 go/no-go**：DEC-217 预授权形态——Coordinator 呈现，门禁不予放弃
- [ ] **M-5b transition/tag**：`core/releases/0.85.0.json` candidate → released（单父 transition）+ tag `v0.85.0`（peel = transition commit）+ push——Coordinator 面
- [ ] **M-6 released 门禁**：`check-release --lineage-mode released --release-commit <commit>` + `release-ledger --remote`
- [ ] **M-7 push**：master + tag 原子推送
- [ ] **M-8 提交 + 收尾**：commit message 含 REL-081/FEAT-054；plan-tracker `工作流版本` → 0.85.0（消 #1 WARN）；session-snapshot 刷新；`archive.py migrate --auto --dry-run` 触发检测 → `check-archive-integrity` PASS；证据行落账

## M-8 收尾义务（Coordinator 面——本票不执行）

- [ ] candidate 提交（四文件入索引后）→ 复跑 `release-ledger --version 0.85.0 --no-remote`（期望 NATIVE_CANDIDATE PASS——刷新 #9）
- [ ] plan-tracker：`工作流版本` → 0.85.0；REL-081 行状态更新；0.85.0 路线图行 → 已发布（待 tag 后）
- [ ] session-snapshot 刷新（含可解析 session_date）——Check 28c hot fact source 面
- [ ] hooks_drift 一次性重装提示：`cp "<plugin_root>/skills/software-project-governance/infra/hooks/"* .git/hooks/`（DEC-213④）
- [ ] 归档触发检测与迁移（ADR-006/007；完整性失败阻断发布完成）
- [ ] 本披露 ② 开放项收口：plan-tracker 工作流版本（M-8）/ hot fact source（M-7/M-8）/ governance health（execution-packet 更新）；snapshot freshness 午夜窗 → FIX-364 候选 triage；CHANGELOG 窗口缺口 → DEC-222（0.86.0 承载）

---
*FEAT-054 M-1R 草案冻结（2026-09-20，Governance Developer Agent 起草；同日 M-2 实测回填 #9~#14 与披露 ④）。事实基线：17 提交窗口取自 `git log`/`git rev-list` 实测；门禁数值取自 2026-09-20 当场命令输出；豁免/分类账本取自 `checks/version.py` STATIC_PIN_EXEMPTIONS 与 `infra/tests/env_failure_classification.json` 实读；`v0.84.0` tag peel = `5d1943f`（`git for-each-ref` 实测）。未实测项（M-5 revert 演练、transition/tag、released 态门禁、candidate 提交后 ledger 复跑）一律标「期义务/未执行/待复跑」，不预填。*
