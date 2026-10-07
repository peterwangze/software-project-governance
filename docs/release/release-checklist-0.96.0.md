# Release Checklist — 0.96.0

- **版本**: 0.96.0 · **日期**: 2026-10-07（准备态——tag 未打） · **状态**: **组装进行中（M-0 完成 + 发布产物四件套本批落地；M-1 版本面 bump 待 Governance Developer 派发，门禁全量复跑 M-2）**
- **主题**: 次版本线：「做薄」债务本金偿还与看护基线治理批（Minor Line: B16 Principal Repayment & Guardrail Baseline Governance）——FIX-435~441 七票 / DEC-318 候选批 + DEC-323/324 紧急与 rider / 发布链 REL-100
- **版本定义**: 次版本线（0.95.0→0.96.0）：B16 债务本金偿还（archive.py 四域拆分+exclusions 回收）+ archguard 基线两跳 sanctioned regen（fatal gate green）+ 宿主 incident 缺陷族根治 + DEC-316/317 sweep 收尾 + 治理卫生登记；无破坏性变更、无机制激活翻转、无 `.governance` schema 变更；载荷冻结七票（FEAT-084 Slice-3 等留池不占本版）。
- **M-0 组装核算**: 见 `docs/release/m-0-assembly-0.96.0.md`（B16 债务两栏核算/载荷一致性核对/版本号决策记录/M-2 披露面定谳预案）。

## 发布范围（冻结清单——DEC-318 + TRIAGE-REL-100）

| 类型 | 项 | 说明 |
|---|---|---|
| 载荷 | FIX-435 (P1) | B16 债务本金偿还——archive.py 4241→1697 四域拆分 + exclusions 4 行回收（`e1457a8`；EVD-1331；REVIEW-FIX-435-R0/R1 双轮 AWN/0） |
| 载荷 | FIX-436 (P2) | DEC-316/317 sweep 收尾批（F-2/R1-1/注释级/F-B3/F-C1——`c442e07`；EVD-1334/1335；REVIEW-FIX-436-R0 AWN/0；DEC-322） |
| 载荷 | FIX-437 (P2) | 治理卫生登记批（快速通道——Check 30c 处置+RISK-066 改形；治理终态；EVD-1328/1333；FIX-228 边界免 CLI） |
| 载荷 | FIX-438 (P1) | 契约快照/archguard 基线 sanctioned regen（`f1a47fd`；EVD-1332；REVIEW-FIX-438-R0 AWN/0；DEC-319/320） |
| 载荷 | FIX-439 (P1) | DSH bootstrap splice 缺陷族根治（用户紧急插入——`f884829`；EVD-1336/1337；REVIEW-FIX-439-R0 AWN/0；DEC-323） |
| 载荷 | FIX-440 (P2) | FIX-439 R0 F-1 承接（CRLF EOL 保留+P3 riders——`1a56797`；EVD-1338/1339；REVIEW-FIX-440-R0 AWN/0） |
| 载荷 | FIX-441 (P2) | archguard 基线 re-anchor rider（M-0 前置解堵——`36ff0be`；EVD-1340/1341；REVIEW-FIX-441-R0 AWN/0；DEC-324） |
| 版本面 | REL-100 M-1 | 权威源 bump+`release-projection --write`+双根 entry sync+引擎锚+STATIC_PIN_EXEMPTIONS bump-time 登记——**待 Governance Developer 执行** |

**不发布什么（Amazon 口径——scope creep 防护）**：FEAT-084 Slice-3 缓存子集（留池——0.95.0 m-0 §3 核算结论延续）；观察池各票 R0 P3 项（FIX-436 N-1/N-2、FIX-439 F-4/F-5、FIX-440 N-1~N-3、FIX-441 F-1~F-3、F-B1/B2/B4/B5）；EXC-001 到期处置；registry 陈旧+乱序；自举豁免续期；28s 过阈披露；closure_chain 拆分候选——均另行批次不占本版。

## 运行前提（G-5——F-13 纪律固化）

**全程 TEMP 用仓库外路径**（pwsh：`$env:TEMP=<仓库外可写目录>; $env:TMP=$env:TEMP`）——仓库内 TEMP 重定向会使 identity attestation 的 snapshot 落入扫描根 → ROOT_SOURCE_AMBIGUOUS 假 FAIL（REL-096 门复跑实测根因；0.94.0/0.95.0 checklist 同款纪律延续）。**check-release 含全量单测（≈7-10 分钟）——前台 300s 超时属预期，用后台运行或延长超时**（2026-10-07 实测先例）。

## 检查项（逐项——发布门 G9）

### A. 范围一致性（载荷七票 vs 路线图 vs 任务状态）

- **结论**: ✅ **PASS（M-0 实读核算）**——七票 plan-tracker L90~L96 全 committed；0.96.0 路线图行在位（L205，DEC-318 组建+M-0 正式预留兑现）；审查链全 AWN/0 终态（FIX-435 双轮、FIX-436/438/439/440/441 单轮、FIX-437 快速通道）；git log 七哈希实测在位。
- 差异披露：L205「包含任务」列 FIX-441✅ 已回填（28c 修复顺带）；REL-100✅ 随 M-8 收口补记（发布链票自身）。

### B. 版本声明 13 处（**待 Governance Developer bump 执行**——M-1）

当前实读全为 0.95.0（check-version-consistency PASSED @0.95.0——2026-10-07 实测，bump 前正确态）。bump 面 13 处清单（与 0.95.0 checklist §B 同构）：

| # | 文件 | 位置 |
|---|---|---|
| 1 | `skills/software-project-governance/SKILL.md` | frontmatter `version:`（**权威源，bump 起点**） |
| 2 | `skills/software-project-governance/core/manifest.json` | `"version"`（canonical source of truth） |
| 3 | `.claude-plugin/marketplace.json` | `plugins[0].version` |
| 4 | `.claude-plugin/plugin.json` | `version` |
| 5 | `.codex-plugin/plugin.json` | `version` |
| 6 | `.chrys-plugin/plugin.json` | `version` |
| 7 | `.zcode-plugin/plugin.json` | `version` |
| 8 | `skills/software-project-governance/infra/hooks/pre-commit` | `# @version:` |
| 9 | `skills/software-project-governance/infra/hooks/commit-msg` | `# @version:` |
| 10 | `skills/software-project-governance/infra/hooks/post-commit` | `# @version:` |
| 11 | `skills/software-project-governance/infra/hooks/prepare-commit-msg` | `# @version:` |
| 12 | `AGENTS.md`（仓库根） | `@bootstrap-version:` 标记 |
| 13 | `CLAUDE.md`（仓库根） | `@bootstrap-version:` 标记 |

执行形态（0.93.x~0.95.0 先例同构）：权威源先 bump → `release-projection --write` 单次确定性收敛 → `sync_entry_projection.py --write`（双根 entry：repo root + e2e fixture ×4 面）→ 引擎锚 REQUIRED_SNIPPETS 六针脚 → STATIC_PIN_EXEMPTIONS 0.96.0 bump-time 登记 → 幂等复跑 PASS@0.96.0。**非 13 处但随链跟踪**：`project/CHANGELOG.md` 0.96.0 段（本批已落）；`.governance/plan-tracker.md` 工作流版本（L11——发布收口由 Coordinator 回写）。

### C. 验证命令（**待 M-2 复跑**）

| 命令 | 预期 | 状态 |
|---|---|---|
| `python -m unittest test_verify_workflow` | **Ran 1061, failures=2（预存披露集）或定谳后归零**（EVD-1338 实测口径；M-1 后 pin-hash 族随再生可能归零——以实测为准） | ⏳ M-2 |
| `check-governance --summary-only`（发布门 full 面） | 0 issues（2026-10-07 深检已 PASS；M-1 后复跑） | ⏳ M-2 |
| `check-injection-budget` | **M-2 终态 PASS @6200**（DEC-325 重定标：lightweight 4303 / strict 6059≤6200——原 4244/6000 预期被 DEC-325 取代；M1+M2 combined 342≤370 零变化仍精确成立） | ✅ M-2（EVD-1344） |
| `check-cross-references` / `check-manifest-consistency` | PASS | ⏳ M-2 |
| `check-version-consistency` | bump 后 13 处一致 @0.96.0 | ⏳ M-1 后 |
| `check-release --version 0.96.0 --require-changelog --lineage-mode candidate` | 门前面全绿或 §F 披露面 GO 终审定谳 | ⏳ M-2（2026-10-07 后台复跑中——结果回填 m-0 §7） |
| `release-ledger --version 0.96.0 --no-remote` | candidate 态 PASS（UNKNOWN/BLOCKED 不包装为 PASS） | ⏳ M-5/M-6 |
| `quality-tools` | 结构化记录（未安装记 NOT_RUN，不虚构 PASS） | ⏳ M-2 |
| tag/push 后：`check-release --version 0.96.0 --require-changelog --lineage-mode released --release-commit <commit>` + `release-ledger --version 0.96.0 --remote origin` | released 双 PASS | ⏳ M-7 |
| `archive.py migrate --auto --dry-run`（如需→执行+`check-archive-integrity`） | 无待归档或归档闭环 PASS（失败阻断发布完成） | ⏳ M-8 |

### D. 回滚方案在位

- **结论**: ✅ **PASS**——`docs/release/rollback-plan-0.96.0.md`（回滚基线 tag v0.95.0@1ee500a；代码面/数据面分别明确；步骤/验证/预计时间/触发条件四要素齐备）。

### E. 审查计划

- **结论**: ⏳ **待执行（M-3 双审）**——0.94.0 双审先例：**M-3a Code Reviewer** 定向面（M-1 版本面 bump 面+CHANGELOG+四件套）+ **M-3b Release Reviewer** 发布终审（review-record 机录，`docs/reviews/review-REL-100-M3b-REL-R0.md` 形态）。NEEDS_CHANGE → 同一 Reviewer 复审 round+1（触发器 T1）；round≥3 → BLOCKED+escalation。

### F. Feature Flags / Kill Switch

- **结论**: ✅ **N/A——本版无 feature flag 面**（创建 N/A 声明件 `feature-flags-0.96.0.md`——check-release release-docs 门要求文件在位，内容声明无旗标面与回退路径；0.95.0 先例同构——双审 F-4/F-2 口径统一）：新增守护（H2-singleton/dry-run guard/校验前置）为入口期守卫非运行时旗标机制；无机制激活翻转；无 B 类旗标债务。行为变更回退 = git revert（见 rollback-plan）；用户可感知行为变更已在 CHANGELOG 0.96.0 段「行为变更（非旗标面）」披露（含 DEC-325 预算重定标披露）。

### G. M-2 披露面定谳（0.93.1 GO 终审先例口径——见 m-0 §6 预案）

| 披露项 | 处置优先序 | 状态 |
|---|---|---|
| contract_matrix 3 预存 result_shapes 漂移（agent_locks/plan_tracker/write 面） | regen 对齐 → 豁免登记（DEC-321 先例）→ GO 终审 ask | ⏳ M-2 |
| injection-budget-strict | **已定谳：DEC-325 预算重定标 6000→6200**（用户 GO 终审三选项裁定；strict 6059≤6200 PASS，EVD-1344） | ✅ 闭合 |
| test_verify_workflow f=2 预存（M0 pin-hash 族） | M-1 后随版本面再生归零（预期）或归因披露 | ⏳ M-2 |
| check-release 15-17 面 2 FAIL（既有披露集族） | 随上述三项定谳消解或 GO 终审 | ⏳ M-2 |

**定谳纪律**：先全绿；不可全绿→事实与选项经 AskUserQuestion 交用户 GO 终审；定谳 DEC 入账。

## M-链完成态（锚：commit/EVD/REVIEW/DEC）

| 里程碑 | 状态 | 锚 |
|---|---|---|
| M-0 组装核算 | ✅ 本批 | TRIAGE-REL-100 用户立项 + 七票全 committed + `m-0-assembly-0.96.0.md`（B16 两栏/载荷核对/版本号决策/定谳预案）+ 四件套 |
| M-1 版本面 | ✅ 完成 | Governance Developer：13 处 bump+投影 written=17+双根 entry×4+引擎锚六针脚+STATIC_PIN 核查零新浮现（EVD-1343） |
| M-2 门禁 | ✅ 完成 | Coordinator 复跑 §C 全量（1061 OK f=0）+ §G 披露面定谳（DEC-325 重定标，EVD-1344）；quality-tools NOT_RUN 如实记录 |
| M-3 审查 | ✅ 完成 | M-3a Code Reviewer AWN/0（REVIEW-REL-100-R0-CODE-REVIEWER）+ M-3b Release Reviewer AWN/0 · GO（REVIEW-REL-100-R0）——双审齐，findings P2×4/P3 当场闭环 |
| M-4 发布四件套 | ✅ 本批 | checklist（本件）/rollback-plan/m-0-assembly + CHANGELOG 段；feature-flags N/A 声明件（§F） |
| M-5a/M-5b candidate | ⏳ | core/releases/0.96.0.json + transition 提交（Coordinator） |
| M-6 ledger | ⏳ | NATIVE_CANDIDATE→released 本地+remote 双 PASS（Coordinator） |
| M-7 tag+push | ⏳ | annotated tag v0.96.0（taggerdate 权威→CHANGELOG 日期回填）+ **ahead 8 commits 统一推送**（2026-10-07 git status 实测口径） |
| M-8 收口 | ⏳ | 发布态回填+快照更新+持续归档触发检查（dry-run 先行）+L205/L11 回填 |

## 回滚

见 `docs/release/rollback-plan-0.96.0.md`（代码面〔版本面 revert+regen 与载荷面按需 revert 序列——七票依赖链与同文件多票警告在案〕与数据面〔.governance 台账 append-only 非 git 管理〕分别明确）。

## 边界声明（保守边界——REL-021 token 全量）

本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success（RISK-036 先例口径延续）；非 Windows 平台未验证，验收全部在仓库内完成；B16 本金偿还以 archive 家族为界（closure_chain 等 28n 预存组如实披露未偿）；REQ-147 仅 Phase 2 首笔交付；宿主 incident 根治以「云视TV」实测三缺陷族为界。

## 签名栏

| 角色 | 签署 | 日期 | 备注 |
|---|---|---|---|
| Coordinator（起草——DSH 治理记录边界） | ✅ REL-100 M-0 组装（机器事实=EVD/REVIEW/RECO 行+文件实读+本会话实跑输出） | 2026-10-07 | 本件+三产物 |
| Coordinator（M-1 派发确认） | ✅ 已签 | 2026-10-07 | 派发范围与 13 处清单确认（锁 op-fa061667/op-d21bb927） |
| Code Reviewer（M-3a） | ✅ AWN/0 | 2026-10-07 | REVIEW-REL-100-R0-CODE-REVIEWER（review-record 机录；P2×1/P3×5 当场闭环） |
| Release Reviewer（M-3b） | ✅ AWN/0 · GO | 2026-10-07 | REVIEW-REL-100-R0（review-record 机录；P2×3/P3×8 放行条件锁 M-8） |
