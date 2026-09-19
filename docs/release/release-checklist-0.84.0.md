# Release Checklist — 0.84.0 (REL-080)

> **M-0/M-1 草案（REL-080 prep，2026-09-19）**——Release Agent 起草、Coordinator 审后随 M-1 候选提交；结构与措辞对齐 `docs/release/release-checklist-0.83.0.md` 先例。**本文件中的 M-2 数值全部为 2026-09-19 当场实测值**（安静窗复跑，命令输出原样摘录），未实测项一律标「M-5 期义务/未执行」，不预填。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.84.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.84.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版全部验收在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）下完成——**隔离环境安装冒烟（环境变量重定向至临时目录）通过**不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；0.84.0 为内部治理效率版；do not claim 1.0.0 production-ready。
- **性能主张边界**：本版主张「机制落地 + 可机检」（聚合命令 / 交互前置 / 按需加载 / 薄指针 / 预算门禁），**不主张**冷启动 p50≤25s 已达成——该数值验收尾巴转 RISK-055（DEC-207①），本版仅提供复验框架 `--ttfa-acceptance`。
- **发布 tip 未生成前不预先编造**：`<发布 tip>`（M-5 transition 提交）与 revert 演练结果本文件不预填。

## Release Scope

| 项 | 值 |
|---|---|
| 版本号 | **0.84.0**（MINOR；semver 论证见下节） |
| 发布任务 | **REL-080**（DEC-204 授权链口径；plan-tracker 行原记 REL-079 与已发布 0.83.0 冲突，已由 Coordinator 更正为 REL-080） |
| 承载决策 | DEC-204（用户预授权）→ DEC-205/206/207/208/209/210/211/212（任务级裁决） |
| 核心范围 | AUDIT-154「治理开销」切片 A：轻量入口 + 交互前置——FEAT-032~040 九任务 |
| 目标版本下不发布 | ① 切片 B/C（无立项）；② FEAT-034 数值验收（TTFA p50≤25s/p95≤45s → RISK-055，框架已交付、采样结论待后续切片）；③ FEAT-039 standard/strict 翻 hard（DEC-210：待模板瘦身）；④ FEAT-040 P3-R1×4 与 DEC-207/211 登记的 0.85.0+ 候选池；⑤ 任何 RISK 的关闭声明（RISK-052~058 全部维持打开/登记） |
| 时间窗口 | 2026-09-18 立项/开发（AUDIT-154 与九任务同日闭环）→ 2026-09-19 发布准备与 M-1 候选冻结 → M-5 transition 期另记 |
| Single-Threaded Owner | Coordinator（发布决策与 `.governance/` 写回）；Release Agent 执行 M-0~M-8 产出物，Release Reviewer 独立审查 |
| 用户获得方式 | `/plugin update`（或 `git pull` + reload）——版本号与投影面 bump 保证 marketplace 新鲜度比对生效；入口文件引导段由 canonical 模板投影，**用户侧无需手工动作** |

## Change Inventory（**10 个载荷提交** — `git log 2a15e59..b537976`，2026-09-19 实测）

> 窗口起点 `2a15e59` = 0.83.0 发布线末位提交（M-8 收尾）；`v0.83.0` tag peel = transition 提交 `296f4f5`（`git rev-parse v0.83.0^{}` 实测）。`b537976` = 本版窗口载荷 tip（M-1 候选打包前的 HEAD）。

| # | commit | 任务 | 关键交付 | 证据 |
|---|---|---|---|---|
| 1 | `c3e1da0` | AUDIT-154 | 治理执行开销审计闭环 + 切片 A 立项（轨迹实测三诉点实证 + arch 咨询 + 诊断报告 `docs/requirements/governance-bootstrap-cost-audit-0.84.0.md`） | EVD-1071/1072 |
| 2 | `564b7da` | FEAT-032 | `governance-cost-report`（4.8s/298 文件）+ 37 单测 + 契约矩阵 85 键 + 0.83.0 基线快照 | EVD-1073 / DEC-205 / RISK-052 |
| 3 | `457a756` | FEAT-037 | `sync_entry_projection.py` + 32 测试 + 薄指针模板 + launch 复用；AGENTS.md 段 2,699B（M-2 期口径 16,011B→R2 期实测 2,699B——FEAT-037 投影幂等后）→2,699B | EVD-1074 / DEC-206 / RISK-053 |
| 4 | `a5d678f` | FEAT-033 | `governance-bootstrap`（358ms/4,937B/42 测试）+ 协议改消费单命令 | EVD-1075 / RISK-054 |
| 5 | `469fb57` | FEAT-034 | 首次交互前置协议重排（决策树/SKILL/模板/M5.5 四处一致） | EVD-1076 / DEC-207 |
| 6 | `38ff7d7` | FEAT-036 | Snapshot 双契约（默认 8 字段 + 完整 24 token 契约口径拆正） | EVD-1077 / DEC-208 |
| 7 | `df9e7db` | FEAT-035 | 迁移写操作 ask-确认前置（五类清单含删除面） | EVD-1078 / DEC-209 / RISK-056 |
| 8 | `697689d` | FEAT-038 | `/governance` 路由层 + 九按需文件（49,889B→11,702B） | EVD-1079 |
| 9 | `512fd51` | FEAT-039 | `check-injection-budget`（resident 4,288/6,000 PASS + ADVISORY 姿态） | EVD-1080 / DEC-210/211 / RISK-057 |
| 10 | `b537976` | FEAT-040 | `behavior_profile.py` 灰度开关 + 收尾 16 项 + 26 投影全绿 | EVD-1081 / DEC-212 / RISK-055/058 |

**M-0/M-1 prep 批（本提交）**：CHANGELOG 0.84.0 段 + release 三件套 + 版本 bump 全平面（见下）+ `core/releases/0.84.0.json`（candidate manifest）+ 投影 regen。

**版本 bump 平面清单（M-1 实测，零遗漏核对面）**：

| 平面 | 载体 | 值 |
|---|---|---|
| 权威源 | `skills/software-project-governance/SKILL.md` frontmatter | 0.83.0 → **0.84.0** |
| JSON 声明面 ×7 | `core/manifest.json` / `.claude-plugin/plugin.json` / `.claude-plugin/marketplace.json`（`/plugins/0/version`）/ `.codex-plugin/plugin.json` / `.zcode-plugin/plugin.json` / `.chrys-plugin/plugin.json` / `package.json` | 全部 **0.84.0**（`release-projection --write` 写入 16 面） |
| hook 版本行 ×4 | `infra/hooks/{pre-commit,commit-msg,post-commit,prepare-commit-msg}` `# @version` | **0.84.0**（`check-version-consistency` 硬校验面） |
| canonical 模板标记 ×4 | `commands/governance-init.md` `> @bootstrap-version:`（lightweight/standard/strict/secondary-thin 四模板） | **0.84.0** |
| DSH 方言面 ×2 | `adapters/dsh/AGENTS.md.template`（`@bootstrap-version`）/ `agent-presets/governance/agent.cordis.yml.template`（persona `v0.84.0`） | **0.84.0** |
| 入口投影 ×4 | repo-root `CLAUDE.md`（full）/ `AGENTS.md`（thin）+ e2e-fixture `CLAUDE.md`（full）/ `AGENTS.md`（thin） | **0.84.0**（`sync_entry_projection --write` 双根；二次 apply 全 `[SKIP]`） |
| fixture 面 ×12 | fixture `skills/.../SKILL.md` + fixture `.governance/plan-tracker.md`（工作流版本）+ 10 个 fixture 命令面 | **0.84.0** |
| snippet 钉 ×6 | `verify_workflow.py` `REQUIRED_SNIPPETS`（plugin ×4 / package.json / core/manifest.json） | **0.84.0** |
| CHANGELOG | `project/CHANGELOG.md` 首段 | `## [0.84.0]` |
| ledger manifest | `core/releases/0.84.0.json` | `lifecycle_state: candidate`（唯一 transition 由 M-5 追加） |

## 行为变更（面向用户 —— MUST 出现在 CHANGELOG 与升级说明）

| # | 变更 | 任务 | 性质 |
|---|---|---|---|
| **B-1** | 首次交互前置（深检后置；健康位显示「待检查」） | FEAT-034 | 协议时序（性能） |
| **B-2** | 迁移写操作 ask-确认前置（五类含删除面） | FEAT-035 | **授权边界收紧（安全面）** |
| **B-3** | Snapshot 默认视图 8 字段（完整契约保留） | FEAT-036 | 输出形态 |
| **B-4** | 次要入口薄指针（2,699B（M-2 期口径 16,011B→R2 期实测 2,699B——FEAT-037 投影幂等后）→2,699B） | FEAT-037 | 入口形态 |
| **B-5** | `/governance` 按需加载（入口 -76.5%） | FEAT-038 | 注入形态 |
| **B-6** | 灰度开关（回退 4 项性能行为；安全不变量不回退） | FEAT-040 | 安全网 |

全文（旧/新行为对照 + 影响面 + 理由）见 `docs/release/feature-flags-0.84.0.md` §2；CHANGELOG 0.84.0 段同步收录（B-1~B-6 逐条）。

## 版本号决策记录（semver 论证）

- **MINOR（0.83.0 → 0.84.0）**：依据 `skills/software-project-governance/core/VERSIONING.md` **L12**（「新增 MUST 规则、新增子工作流/skill、新增 B/C 级自动化能力」）与 **L37**（「SKILL.md MUST 规则新增 → MINOR」）——本版含 SKILL.md 行为协议变更（首次交互前置 / 迁移写操作确认门 / 快照双契约 / 灰度开关）+ 三项新增 CLI/检查能力（`governance-bootstrap` / `governance-cost-report` / `check-injection-budget`）；
- **非 PATCH**：L38 口径（「仅修复 bug 不改变行为语义 → PATCH」）不适用——本版主体是行为语义与协议变更，非缺陷修复；
- **非 MAJOR**：L11 口径（MUST 规则删除/重命名、Gate 行为语义破坏、governance 字段格式变更）逐项核对**均不成立**——无删除、无重命名、无字段格式变更；L83（1.0.0 前 Minor 可含有限 Breaking）**本版未使用**：Breaking changes = 无；
- **版本号未被预留**：0.84.0 = AUDIT-154 切片 A 承载版本（2026-09-18 用户裁决立项，DEC-204）；路线图行同期入账；REL/任务 ID 冲突经 Coordinator 裁决（REL-080，见披露 ③）。

## Candidate Gate Results（M-2 —— 2026-09-19 实测，安静窗）

| # | 门禁 / 命令 | 结果 | 关键实测值 |
|---|---|---|---|
| 1 | `check-version-consistency` | **PASSED**（exit 0） | 源 = 0.84.0；13 面 + 双入口 marker 全一致；**1 WARN**：plan-tracker `工作流版本` 仍 0.83.0 → M-8 收尾更新为 0.84.0 |
| 2 | `check-projection-sync --fail-on-issues` | **PASSED**（exit 0） | `source_version=0.84.0`，26 投影面同步；entry 双根 PASS（repo-root 与 e2e-fixture）；DSH 方言互认 present（3,634B/59L） |
| 3 | `check-entry-bootstrap-sync` | **PASSED**（exit 0） | `CLAUDE.md=23835B/full`、`AGENTS.md=2988B/thin`（repo-root 与 fixture 同值，profile=standard） |
| 4 | `check-injection-contract` | **PASSED**（exit 0） | 3 文件 / 23 anchors |
| 5 | `check-injection-budget` | **PASSED**（exit 0） | resident **4,957 / 6,000 tok**（余量 1,043 = 17.4%）；分项：persona 1,673 / entry-template 1,361 / secondary 875 / agent-instructions 1,048；entry-skill 9,387 **report-only**（skill tier，非注入债）；standard/strict **ADVISORY**（DEC-210）；zstandard 断言 PASS |
| 6 | `check-cross-references` | **PASSED**（exit 0） | 78 文件 / 711 引用；0 dangling / 0 deprecated / 0 circular |
| 7 | `check-manifest-consistency` | **PASSED**（exit 0） | canonical 769 / actual 870（FIX-354/355 后实测；M-2 期 767/865） |
| 8 | `archguard-ratchet` | **PASS**（exit 0） | R1 24,769 ≤ 24,769；R2 47 ≤ 47；R3 SCC max 1（unmanaged refs 1 disclosed）；R4 print 1,304 ≤ 1,304；R5 cli keys **88/88** + segments **71/71**；R6 199 modules（advisory）；**R7 regen deterministic=True / committed==fresh True** |
| 9 | `release-projection`（check + 幂等复验） | **PASS**（exit 0） | 26 面 checked；首轮 `--write` **written=16**；二轮 `--write` **written=0**（幂等）；declared legacy snapshots 10（converged 0 / missing 0） |
| 10 | 入口投影幂等（`sync_entry_projection --write` ×2，双根） | **PASS** | 首轮 `[WROTE]`；二轮 **全 `[SKIP] … already synchronized`**（repo-root + fixture 各 2 文件） |
| 11 | `e2e-check` | **PASSED**（exit 0） | source_cli_proxy 6/0；target_cwd 4/0；target_fixture 9/0；contract_only 5；contract_check_failed **0**；runtime contracts reported separately |
| 12 | `verify` | **PASSED**（exit 0） | 全量资产 + 适配器契约同步；**1 WARN**（同 #1：plan-tracker 版本行，M-8 收尾） |
| 13 | `check-governance`（安静窗复跑） | **29 issues**（exit 0） | FAIL 构成：**Check 18c ×6 = 「REL-080: missing execution packet」**（ID 由 REL-079 更正为 REL-080 的直接副作用——packet 仍挂在 REL-079 名下；收口 = Coordinator `verify_workflow.py execution-packet --write`）+ **Check 28c**（`session-snapshot.md` 缺可解析 `session_date`）+ **Check 30 V2 ×2**（FIX-246 / REL-078 轮次连续性——0.83.0 发布时已存在的既有披露项，本版不新增）。WARN 构成：Check 28q `hooks_drift` ×4（**仅 `# @version` 注释行 0.83.0→0.84.0 差异，实测 diff = 2 行；行为语义零变化**，处置 = 用户一次性重装 hooks）+ 28n module_size ×3 / function_size ×5（advisory）+ 4 stale risk + 2 machine-provenance（FIX-256/258 历史手写行）+ 424 structural（0 blocking）。ERROR 构成：**Check 28s**（`evidence-log.md` 1,534.4 KB，advisory `fatal_on_error=false`，不阻断发布）。**安静窗纪律**：首轮 check-governance 与我方写盘并发，出现 4 条 `INVENTORY_*` FAIL（Check 31，candidate 集合枚举期被写入扰动）；**安静窗复跑后 Check 31 PASS**（inventory `ace4454b…`，与 check-release 同值）——并发扰动为假阳，如实记录 |
| 14 | `check-release --version 0.84.0 --require-changelog --lineage-mode candidate`（全量执行闸门启用） | **R2 终态：FAILED — 1 issue(s)**（exit 1；演进：M-2 期 3 → R2 期 1） | **PASS 面（17 门 PASS + 1 门预算覆盖 PASS = 18 面，R2 复核）**：version consistency / release fact source / **hot fact source（M-7 后 PASS）** / runtime readiness / first session measurement / governance pack / agent adapters / projection sync / cross references / **archive integrity（归档迁移后 PASS）** / **release docs（三件套入索引后收口）** / **release lineage（candidate 模式）** / gate sequence / one dot zero blockers / changelog / loop runtime claim gate（semantic + identity PASS，inventory `2613892f…`，candidates 851（R2 报告 W-4 复核值））/ dsh upgrade regression（隔离 temp-DSH_HOME 冒烟 PASS）/**unit tests（SPG_RELEASE_GATE_TIMEOUT=600 复跑 PASS）**。**FAIL 1 项（R2 终态）**：`execution gates → governance health`（`check-governance --fail-on-issues` exit=1）——构成 = **20 issues 计数含 WARN 族（FAIL 面仅 28s advisory ×1；V2 violations 0；逐条归因见下文归因段）**——0.83.0 Gate 16 同型先例（21 issues 存量披露发布；本版 20 且实质更优）。M-2 期原始 3 FAIL 留档：① hot fact source（快照缺 session_date——M-7 已收口）② governance health（packet ×6 + V2 ×2——均已收口/消解）③ unit tests 180s 超时（SPG_RELEASE_GATE_TIMEOUT 覆盖后 PASS） |
| 15 | `release-ledger --version 0.84.0 --no-remote` | **FAIL — 预提交态预期**（exit 1） | 唯一 issue：`candidate_commit: expected exactly one commit adding core/releases/0.84.0.json, found 0`——manifest 仅入索引、**尚未提交**，`trust.candidate_commit.derivation = git_commit_adding_path` 不可由 git 派生。**这是 M-1 后、commit 前的正确观测值，不包装为 PASS**；M-5 提交后 MUST 复跑（期望 `trust_level=NATIVE_CANDIDATE` + `candidate_commit` 派生成功；tag/push 后 `--remote origin`） |
| 16 | `check-archive-integrity` | **✅ PASS（归档迁移后——R2 独立复现）** | FIX-246 终态行恢复触发触发器 2 → 用户 ask 确认（FEAT-035 语义）→ migrate --auto 已执行（FIX-246 → incremental-20260919-1.md + EVD-892 → evidence/；EVD-1086 留痕）→ check-archive-integrity PASS（index 1221→1213） |
| 17 | 全量测试套件（`pytest skills/software-project-governance/infra/tests -q`，M-1 bump 后） | **M-1 期：32F/3441P（1176.95s）→ R2 终态复跑：30F/3451P/1 skipped/390 subtests（858.70s，R2 Reviewer 独立复跑）——0 新增失败** | 构成（M-1 期初测）：**30 SUBFAILED = 既有环境族**（`test_pre_commit_review_evidence` hook 子测 + `test_hooks::test_replay_real_plan_tracker_hits` 等——0.84.0 开发期基线 30F/3443P）+ **2 新增 = 版本钉腐化**（`test_entry_projection.py` DSH 模板 `@bootstrap-version` 静态断言 + `test_bootstrap_aggregate.py` fixture head 静态版本钉 ⇒ `scenario_hint='C'≠'F'`）。**已由 FIX-353 修复**（动态派生：`resolve_entry.read_active_version()` / `_bootstrap_template_version()`），两文件复验 **exit 0**（两文件合计 74 tests OK——32+42）；**全量复跑已执行**：R2 Reviewer 独立复跑 30F/3451P/1 skipped（858.70s）——**2 新增已消（FIX-353 生效）、30 = 既有环境族与基线恒等、0 新增失败** |
| 18 | M-2 revert 干跑（回滚演练） | **✅ 已执行（2026-09-19，FIX-354 F-03）** | 隔离副本（`git clone --no-hardlinks` %TEMP%，就地执行实测否决——脏索引 auto-merge 污染）实测：载荷面 `revert 2a15e59..b537976` **exit 0 / 0 冲突 / 82 paths**（Release R1 独立复算同值）；完整窗口近似（真实 staged 导入 + 构造 transition）**exit 0 / 98 paths 且索引==0.83.0 发布线树**；F-04 反向实证（错误终点）exit 1/CONFLICT；B-6 双向实测；15 步表 + 零污染三重指纹入 `rollback-plan-0.84.0.md §演练记录`；未执行项如实标注（需人工/推演面） |
| 19 | 真机三项（0.81.0 回贴） | **本版无新增真机项** | 0.81.0 三项回贴维持有效；本版隔离面验证 = 「隔离环境安装冒烟（环境变量重定向至临时目录）」类，已由既有隔离套件覆盖，无新增义务 |

**M-2 最终复跑（清单与三件套落盘并进入 git 索引后、安静窗；R2 终态刷新）**：`check-release --lineage-mode candidate` 实测演进——M-2 期 3 FAIL（hot fact source / governance health / unit tests）→ **R2 终态 1 FAIL**：`hot fact source` PASS（M-7 快照）+ `unit tests` PASS（SPG_RELEASE_GATE_TIMEOUT=600 复跑）+ `archive integrity` PASS（归档迁移后）——**唯一余项 = governance health（20 issues，FAIL 面仅 28s advisory，逐条归因见下段；0.83.0 Gate 16 同型先例）**。**结论口径**：以当场值为准、不以旧值作新声明；发布 go/no-go 由 Coordinator 按 DEC-204（门禁不予放弃）+ 披露项裁决。

**M-6 归档触发检测（终态——R2 后已执行）**：初测（M-2 期）跳过（无可归档数据）；FIX-246 任务行终态恢复后复测触发器 2 成立（dry-run = 1 task + 1 evidence）；**已执行（用户 ask 确认「执行归档（推荐）」，EVD-1086 留痕）**：migrate --auto 归档 FIX-246 → archive/tasks/v0.1.0~v0.82.0-incremental-20260919-1.md + EVD-892 → archive/evidence/；check-archive-integrity **PASS**（index 1221→1213）；Check 27 archive WARN 消失（[PASS]）。

**发布期修复批归属披露（R1 F-19——staged 项构成演进 28（M-1）→33（R1）→36（R3）→37（R4 时点）〔R2/R3 期新增：R2/R3 审查报告 + 清单更新 + DEC-214①/EVD-1086/归档三文件入 .governance〕）**：28 项原始 M-1 面 + FIX-353 两测试文件（test_entry_projection/test_bootstrap_aggregate——版本钉动态化，DEC-213⑥）+ FIX-354 三文件（version-projections.json +6 / manifest.json +1 投影合同原子 + fixture governance-init.md 再生成——DEC-213⑦）+ **FIX-355 两文件（`checks/review_domain.py` +168/−10 + `tests/test_review_closure_legacy.py` +211——产品代码变更，DEC-214 + 独立 Code Review APPROVED_WITH_NOTES/0 机录）** + R0/R1/FIX-355-CODE-R0 三份审查报告 + 本清单更新。CLAUDE.md（root）gitignored 本地写盘不入库。

**governance health 20 issues 逐条归因（R2 终态——0.83.0 Gate 16 同颗粒度；R2 Reviewer 独立复跑同值）**：① 28s ×1（evidence-log 1,540.5 KB——较 M-2 期 1,534.4 增量 = EVD-1082~1086 + DEC-213/214 + RECO 发布期入账，advisory 不阻断）；② 28n/28o God-module 族 WARN（module_size ×3 + function_size ×5 + checks/ 子模块超限——RISK-039 棘轮锚定，0.83.0 同族同型）；③ 14 structural ×428（evidence_col_mismatch 历史结构族，波动 +1 = 本窗口新 EVD 行，0 blocking）；④ 30 closure WARN ×29（含 V2 豁免行 ×2〔REL-078 归档豁免 + FIX-246 行恢复豁免——FIX-355 后新形态，WARN 非静默带依据〕+ 历史手写行等——**V2 violations 0**）；⑤ 30c machine-provenance WARN ×2（FIX-256/258 历史手写行，既有）；⑥ 28q hooks_drift ×4（版本行 bump 差异，用户一次性重装）；⑦ **4 stale risk（RISK-036/039 复评窗 09-30、RISK-046 09-30、RISK-050 10-31——均为已登记复评窗未到期）**；⑧ **36 lifecycle/flow-unit WARN ×16（legacy 段历史族，0.83.0 披露「36×16」同值延续）**；⑨ 27 archive-integrity **已 PASS**（归档迁移后）；⑩ 25 untracked **已消**（审查报告入库后）。**FAIL 面仅 28s ×1（advisory）**；`--fail-on-issues` exit 1 系 all_issues 计数含上述 WARN 族——与 0.83.0 Gate 16「21 issues 存量披露发布」同型先例，**本版 20 < 21 且 V2 消解、FAIL 面更窄（实质优于先例）**。

## Gate 10 明细指引（M-2 全量失败清单纪律）

- 任一 FAIL 不得以「已知/预期」名义归类为通过——本 checklist 的 FAIL 项**全部保留**在披露清单（§披露清单 ①②）；
- `check-governance` 的 FAIL/WARN/ERROR 均逐项列明归属（检查号 + 载体 + 处置人）；
- 安静窗纪律：涉及 candidate 集合枚举的检查（Check 31）**MUST** 在无并发写盘时复跑，并把首轮假阳一并记录（本版已执行，见 #13）。

## RISK 复评提案（M-4 承载 —— Coordinator 裁决落 risk-log）

| RISK | 当前状态 | 本版事实 | 复评提案 |
|---|---|---|---|
| RISK-052 | 打开（活动语料时点漂移） | 成本口径下界声明已入 DEC-205；基线快照已固化 | **维持打开**（采样口径随时点漂移，需后续切片对照） |
| RISK-053 | 打开（FEAT-037 P3 族） | P3-1/2/4 已随 FEAT-040 前置处置；其余登记 | **维持打开**（P3-R1×4 转跟踪入 0.85.0+ 候选池） |
| RISK-054 | 打开（并行竞态） | 本版 M-2 首轮即实测到一次并发假阳（Check 31 INVENTORY_*），安静窗复跑消除 | **维持打开**（本版新增实证；建议在 0.85.0 给枚举类检查加写盘互斥） |
| RISK-055 | 打开（数值验收尾巴） | `--ttfa-acceptance` 框架已交付；采样结论未出 | **维持打开**（不作为本版发布阻断项——发布范围为机制落地） |
| RISK-056 | 打开（既有测试失败） | D5/D6 转跟踪，本版未新增失败 | **维持打开** |
| RISK-057 | 打开（注入预算回弹） | lightweight 4,957/6,000（余量 17.4%）；姿态为 ADVISORY | **维持打开**（翻 hard 时点 = 模板瘦身后，DEC-210） |
| RISK-058 | 打开（resident +669 tok） | 实测 resident 4,288→4,957（+669 = 灰度开关文本） | **维持打开**（0.85.0 模板瘦身承接开关文本压缩） |
| RISK-036/039/046/050 | 打开（0.83.0 期既有） | 本版零进展（无外部提交/验证动作） | **维持打开**（不声明关闭） |

## 披露清单（如实披露项 —— 不得写成通过）

① **门禁既有披露项（0.83.0 precedent + 本版收口后终态 2026-09-19）**：Check 28s（`evidence-log.md` 1,541.8 KB，advisory ERROR，不阻断发布）/ **Check 30 V2 = 本版已收口**——FIX-355 归档感知终态门（REL-078 半面 FAIL→WARN 豁免；FIX-246 半面任务行恢复终态〔EVD-892 + REVIEW-FIX-246-R1 机录在案，任务行遗失于归档窗口未入 archive 索引——FIX-355 审计发现；恢复为终态登记非机器补造，R0 记录缺口按 DEC-199 如实保留为 WARN〕→ V2 violations **0**）+ DEC-214（superseding DEC-203 半面）+ DEC-214① 勘误登记（RISK-051 复评：×2→已消解）。收口后 check-governance 当场终值 = **20 issues**（构成：28s ×1 advisory + 28n God-module 族 WARN〔RISK-039 + 棘轮锚〕+ 14/36 legacy WARN + 28q hooks_drift ×4〔版本行 bump 差异，行为语义零变化〕+ 4 stale risks〔RISK-036/039/046/050——复评窗 09-30/10-31 已登记未到期〕）——governance health 子门 `--fail-on-issues` exit 1 系 20 计数含 WARN 族（**0.83.0 Gate 16 同型先例**：21 issues 存量披露发布；本版 20 且 V2 消解、FAIL 面更窄——实质优于先例）。
② **本版新增披露（需 Coordinator 收口）**：
   - **Check 18c ×6「REL-080: missing execution packet」**——✅ 已收口（execution-packet --write + Coordinator 契约填充：product_success/acceptance/quality_budget/vertical_slice/assumption_record 全字段 PASS）；
   - **Check 28c hot fact-source FAIL**——✅ 已收口（M-7 快照落盘含 session_date 2026-09-19 + 0.81.0 补记 + RECO-FEAT-032 修复 + 0.84.0 路线图行/总览/配置行三面一致〔28c 复跑 0 hot fact-source issues〕）；
   - **plan-tracker `工作流版本` = 0.83.0**——✅ 已收口（0.84.0 + 路线图行含全部 task token〔FEAT-032~040/REL-080/FIX-352~355/FIX-350/AUDIT-154〕）；
   - **FIX-352/353 版本钉腐化**——✅ 已修复并入账（EVD-1082/1083 + DEC-213⑥；独立复验 32+42 用例全绿）；
   - **FIX-354（F-05 fixture governance-init 盲区 + F-03 回滚演练）**——✅ 已交付并入账（投影 27 faces；演练记录 15 步入 rollback-plan；EVD-1084）；
   - **FIX-355（Check 30 归档感知）**——✅ 已交付并入账（V2 ×2→0；superseding DEC-203 半面——DEC-214 + DEC-214① 勘误；8 新测试 + 2 突变击杀；独立 Code Review APPROVED_WITH_NOTES/0 机录；EVD-1085 + change-triage + RECO-FIX-355）；
   - **归档迁移（R1 F-15）**——✅ 已执行（用户 ask 确认后 migrate --auto：FIX-246/EVD-892 入册 incremental-20260919-1；check-archive-integrity PASS〔index 1221→1213〕；EVD-1086）；
   - **并发写盘假阳**——首轮 check-governance 的 4 条 `INVENTORY_*` FAIL（Check 31）为枚举期扰动，安静窗复跑 PASS（`ace4454b…`）；如实记录以佐证 RISK-054；
   - **发布执行闸门的两项预算/历史性 FAIL（不得包装为 PASS）**：`unit tests` 闸门 180s 超时（独立复跑 **273.4s exit 0 全绿** ⇒ 闸门预算问题，收口 = `SPG_RELEASE_GATE_TIMEOUT` 覆盖后复跑）；`governance health --fail-on-issues` exit=1（**终态构成 = 20 issues〔归档迁移后〕：FAIL 面仅 28s advisory ×1 + WARN 族**〔28n/14/30-WARN/30c/36/28q/4-stale〕——**Check 30 V2 已消解〔violations 0〕、Check 27 已 PASS〔归档后〕**；0.83.0 Gate 16 同型先例〔21 issues 存量披露发布〕，本版 20 且 V2 消解 = 实质优于先例）；
   - **`release-ledger --no-remote` 预提交态 FAIL**（candidate commit 尚不可由 git 派生）——M-1 后、commit 前的正确观测值；M-5 commit 后 MUST 复跑并刷新本行；
   - **版本钉腐化类（M-1 口径盲区，本版首次暴露）**：`test_entry_projection.py`（DSH 模板 `@bootstrap-version` 静态断言）与 `test_bootstrap_aggregate.py`（fixture head 静态版本钉 ⇒ `scenario_hint='C'≠'F'`）随 M-1 bump **转红**——两者均**不在** `check-version-consistency` 的 13 面清单内，故 M-4 的 11 项机检无法兜底（口径缺口本身入账）。**已由 FIX-353 修复**（动态派生：`resolve_entry.read_active_version()` / `_bootstrap_template_version()`；文件注释显式引用 FIX-352 §6 根因 + REL-080 场景），两文件复验 exit 0；**全量 `pytest` 复跑已完成（R2 独立复跑 30F/3451P，0 新增失败）——见 #17 终态**。
③ **发布任务 ID 归属**：DEC-204 记 0.84.0 发布为 **REL-080**；plan-tracker 行曾误记 REL-079（与 2026-09-17 已发布 0.83.0 同 ID），**Coordinator 已于 2026-09-19 更正为 REL-080**（本版按 DEC-204 口径统一使用 REL-080；审查轮次与 0.83.0 的 REL-079 审查链完全隔离，避免 Check 30 V2 round continuity 新增项）。
④ **性能主张边界**：本版不主张冷启动已达 p50≤25s；AUDIT-154 基线数值仅为对照起点（RISK-055 / DEC-207①）。
⑤ **no-overclaim**：official approval / marketplace approval / universal runtime support / external first-session pilot success 均未被主张；RISK-036 打开，1.0.0 就绪未被主张。
⑥ **回滚安全弱化面**：回滚到 0.83.0 即整体恢复静默迁移写语义（B-2 防护消失）——回滚决策 MUST 显式接受（rollback-plan §1/§5）。

## 真机验收（0.81.0 三项回贴有效；本版无新增真机项）

- 0.81.0 交付的三项真机验收结论**维持有效**（本版未触碰其载体面）；
- 本版涉及宿主面的改动（DSH 模板 / persona 版本行 / 入口投影）验证口径 = **隔离环境（环境变量重定向至临时目录）渲染 parity 与投影幂等**——已在 M-2 覆盖（#2/#3/#9/#10）；
- **无新增真机义务**：本版未新增外部依赖、未改 dsh 上游契约面、未改安装路径语义。

## 发布步骤（M-0 ~ M-8 勾选框）

- [x] **M-0 预检**：工作树 = `b537976`；除 `.governance/`（gitignored）与本批发布产物外无脏文件；九任务 tracker 全 ✅；发布行存在（REL-080，ID 经裁决更正）
- [x] **M-1 版本 bump（全平面）**：SKILL frontmatter + 7 JSON 面 + 4 hook 版本行 + canonical 四模板 + DSH 面 ×2 + `REQUIRED_SNIPPETS` ×6 + fixture 面 + CHANGELOG + `core/releases/0.84.0.json`（candidate）
- [x] **M-2 投影 regen**：`release-projection --write`（16 面，二轮 0 = 幂等）+ `sync_entry_projection --write` 双根（二轮全 `[SKIP]` = 幂等）
- [x] **M-3 CHANGELOG**：`project/CHANGELOG.md` `## [0.84.0] - 2026-09-19` 段（含 Added/Changed/Fixed/B-1~B-6/如实披露/Breaking=无/MINOR 依据/投影说明）
- [x] **M-4 全量验证**：见 Candidate Gate Results（#1~#16 实测；FAIL 项全部披露）
- [x] **M-5 发布记录**：EVD 已落账（EVD-1082~1086 发布链 + FIX-352~355 修复链）+ DEC-213/214（姿态/ID 裁决/superseding）——审查闭环 R0→R3 机录在案
- [ ] **M-5b transition/tag**：`core/releases/0.84.0.json` candidate → released（单父 transition）+ tag `v0.84.0` + push（DEC-204 预授权形态，门禁不予放弃）
- [x] **M-6 归档检测**：`archive.py migrate --auto --dry-run`（发布强制触发器）报告返回 Coordinator
- [x] **M-7 session-snapshot 刷新**：已落盘（session_date 2026-09-19 + 0.81.0~0.84.0 发布行 + RECO-FEAT-032→RECO-AUDIT-154 修复 + 切片 A 完成态；终态版已随 R3/T2 刷新（含 FIX-352~355/归档/R3~R5 审查链））
- [ ] **M-8 提交 + 收尾**：本批文件已 staged；commit（message 含 REL-080）+ 证据行 + plan-tracker 状态/路线图 + 快照落盘由 Coordinator 执行

## M-2 执行序（Coordinator 实测约束）

1. 安静窗纪律：涉及枚举/inventory 的检查（Check 31）MUST 无并发写盘（本版已实证一次假阳）；
2. 顺序：`check-version-consistency` → `check-projection-sync` → `check-entry-bootstrap-sync` → `check-injection-*` → `check-cross-references` → `check-manifest-consistency` → `archguard-ratchet` → `release-projection` → `e2e-check` → `verify` → `check-governance` → `check-release --lineage-mode candidate`；
3. 每个 FAIL 逐项落披露，不以「已知」豁免；
4. `check-release` 的 `unit tests` 闸门默认 180s（FIX-234）**MUST** 按本机实测套件时长覆盖：`SPG_RELEASE_GATE_TIMEOUT=600 python … verify_workflow.py check-release --version 0.84.0 --require-changelog --lineage-mode candidate`（本机实测 273.4s / exit 0）；
5. tag 生成后 MUST 复跑 `check-release --lineage-mode released --release-commit <commit>` 与 `release-ledger --version 0.84.0 --remote origin`（tag peel / 单父 / remote identity 三判据）。

## M-8 收尾义务

- [ ] commit message 含 **REL-080**；`core/releases/0.84.0.json` 保持 candidate（唯一 transition 由 M-5 追加）
- [ ] `.governance/session-snapshot.md` 刷新（含可解析 `session_date`）——修复 Check 28c；
- [ ] plan-tracker：`工作流版本` → 0.84.0；REL-080 行置 ✅；0.84.0 路线图行状态 → 已发布（待 tag 后）
- [x] `execution-packet --write` + 契约全字段填充（REL-080/FIX-354/FIX-355）——Check 18 家族零 FAIL
- [x] **FIX-353 两测试文件入暂存区**（`test_entry_projection.py` / `test_bootstrap_aggregate.py`——已 staged（staged 演进链 28〔M-1〕→33→36→38〔R5 时点〕内）；测试修复属 Developer 归属）
- [x] **全量 `pytest` 复跑（已完成——R2 Reviewer 独立复跑）**：30 failed / 3451 passed / 1 skipped / 390 subtests（858.70s）——新增失败归零（30 = 既有环境族与基线恒等）
- [x] `check-release` 复跑（`SPG_RELEASE_GATE_TIMEOUT=600`）——unit tests 预算项已收口（R2 复核 PASS）；[ ] `release-ledger --version 0.84.0 --no-remote` 复跑（commit 后 candidate commit 派生——M-5 后义务）
- [ ] 用户一次性动作提示：`cp "<plugin_root>/skills/software-project-governance/infra/hooks/"* .git/hooks/`（消除 4 项 `hooks_drift`；本版差异仅版本注释行）
- [x] 归档：dry-run 期「无可归档数据」→ FIX-246 行恢复后触发器 2 成立 → **已执行**（用户 ask 确认「执行归档（推荐）」；FIX-246/EVD-892 入册；check-archive-integrity PASS；EVD-1086）

---

*M-0/M-1 草案冻结（2026-09-19，REL-080 prep，Release Agent 起草）。事实基线：载荷 10 提交与窗口起点取自 `git log` 实测；门禁数值取自 2026-09-19 当场命令输出（安静窗）；RISK/DEC/EVD 取自 `.governance/` 热文件与 `docs/reviews/` 机录报告；`v0.83.0` tag peel = `296f4f5`（`git rev-parse v0.83.0^{}`）。未实测项（M-5 revert 演练、transition/tag、released 态门禁）一律标「期义务/未执行」，不预填。*
