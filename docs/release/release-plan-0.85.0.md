# Release Plan — 0.85.0（REL-081 M-1R / FEAT-054）

> **任务**: FEAT-054（P1；triage `.governance/change-triage/FEAT-054.json`；DEC-217 预授权链）· **日期**: 2026-09-20 · **性质**: M-1R 发布材料面（release plan/checklist/rollback 三件套 + candidate manifest + M-2 门禁实测）——非发布执行
> **裁决权边界**: 版本 go/no-go 与 tag/transition/push 由 Coordinator 执行（DEC-217 M-4 预授权承载；预授权**不免除** M-2 门禁实测与 M-3 双半面审查）；本文件由 Governance Developer Agent 起草，供 Release Reviewer / M-3 审查链消费
> **写入边界**: 仅本三件套 + `core/releases/0.85.0.json`（triage `files` 锁定面）；不触 `.governance/`、不触 `verify_workflow.py`/`registry.py`（0.86.0 批 2.0 后续票面）、不改 CHANGELOG（已于 `a91d6b4` 冻结）、不执行 tag/push/transition

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项：

- **No official approval claim**：official approval 未被授予、未被主张；0.85.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.85.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版全部验收在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）类口径下完成——隔离验收不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；0.85.0 为内部治理效率版（注入瘦身 + 预算硬门）；do not claim 1.0.0 production-ready。
- **发布 tip 未生成前不预先编造**：`<发布 tip>`（M-5 transition 提交）与 tag 事实本三件套不预填——hash 一律由 M-5 生成后回填（FIX-349 口径：taggerdate 权威）。

## 版本号与授权链

| 项 | 值 |
|---|---|
| 版本号 | **0.85.0**（MINOR；0.84.0 → 0.85.0 不跳号、无预留占用） |
| 发布任务 | **REL-081**（M-0 双半面规划双审 R0→R1 通过 + 用户裁定 MINOR 两批制——commit `6325ee6`，EVD-1090） |
| 授权链 | DEC-215②（批次规划授权）→ DEC-216（M-0 裁定 MINOR 两批制）→ **DEC-217（全链预授权：「授权 Coordinator 按照推荐进行推进，直到当前规划的版本发布」；M-4 授权形态 = 预授权，边界 = 预授权不免除门禁）** → 批 2.0 DEC-218（条件 go）/ DEC-219（外扩削减面） |
| MINOR 依据 | `core/VERSIONING.md` L12「新增 B/C 级自动化能力」（FIX-361 静态钉机检面 + FEAT-052 skill 层独立预算线 + FEAT-049 契约基座）+ L37（FEAT-041 入口模板协议变更）；非纯 bug fix（L38 PATCH 不适用）；Breaking changes = 无（FEAT-050 翻 hard 属门禁硬化，L11 pre-1.0.0 括注覆盖——CHANGELOG 0.85.0 段同口径） |
| Single-Threaded Owner | Coordinator（发布决策与 `.governance/` 写回）；Release 面产出物由角色 agent 执行，Release Reviewer 独立审查 |
| 用户获得方式 | `/plugin update`（或 `git pull` + reload）——版本号与投影面 bump 保证 marketplace 新鲜度比对生效；旧安装升级路径兼容（FEAT-041 契约 v2「详细规则」H2 恢复 = 边界集超集，整段替换零残留——CHANGELOG B-1 已声明） |

## 发布范围

### 载荷构成（两批制——DEC-216）

| 批 | 任务 | 关键交付 | 提交 |
|---|---|---|---|
| **批 1「降噪与机检面前置」（7 票）** | FIX-356 | `governance-cost-report` workspace 过滤真实语料修复（0→156 sessions/22 TTFA；RISK-055 机制修复） | `be0b844` |
| | FIX-360 | cwd 双源语义 CALIBRATION 披露行 | `c7b515a` |
| | FIX-359 | RISK-056 回放族 30 项既有失败收敛清零 | `11289be` |
| | FIX-357 | Check 30 豁免行因果措辞按来源分流 | `25aef9f` |
| | FIX-362 | governance-status fixture byte_copy promote（投影合同 27→28 面） | `5a4c4f4` |
| | FIX-358 | 归档谓词并集五件套（13 散文格 ID 漏判收敛） | `399c48a` |
| | FIX-361 | 测试静态版本钉 WARN-only 机检面（DEC-213③） | `2e80c69` |
| **批 2「瘦身与门禁翻转关键路径」（3 票串行）** | FEAT-041 | 入口模板契约 v2 全量推开——resident 双达标 5,694/5,966 ≤6,000（-46.9%/-45.4%；DEC-218/219） | `b717835` |
| | FEAT-050 | 注入预算 resident 翻 hard + FEAT-039 P3-3 同 commit（DEC-211③） | `407b230` |
| | FEAT-052 | skill 层独立预算线 16,000 + F 族清理（DEC-215⑧） | `1519bf1` |
| **⑥ 治理面** | REL-081 M-0 | 双半面规划闭环 + 用户裁定（`6325ee6`）；窗口内 8 决策（DEC-214~221，含 DEC-217/221 双预授权）+ 20 EVD（EVD-1088~1107）+ 11 票 R0 审查链全闭环 | — |
| **M-1 候选打包** | FEAT-053 | 0.84.0→0.85.0 全仓 bump（24 tracked：手工 5 + 再生 19）+ CHANGELOG 0.85.0 段 + 投影 regen（28 面）+ 豁免账本 10 行登记 | `a91d6b4`（EVD-1109） |
| **M-1R 发布面（本票）** | FEAT-054 | release 三件套（plan/checklist/rollback）+ feature-flags（修复回合补授——Coordinator 裁决边缘①选 (a) 最小形态）+ `core/releases/0.85.0.json`（candidate manifest）+ M-2 门禁实测 + 全量 pytest 归因复核 + 两处一行修（SKILL.md:121 / version-plan ragged row——修复回合指令②③） | 本票（Coordinator 提交后为 candidate commit） |

### 随候选树入库的 0.86.0 前置票（如实登记——CHANGELOG 0.85.0 段披露⑤同口径扩展）

窗口 `3663423..1cd224e`（17 提交）内含 4 个 0.86.0 轨道提交，0.85.0 **零行为消费**，随候选树入库不可避免（发布链时序交错，详见披露 ②）：

| 提交 | 任务 | 性质 | CHANGELOG 登记态 |
|---|---|---|---|
| `27eeea0` | FEAT-049 | M0 契约冻结 m0-r1（0.86.0 批 0 前置——58 契约测试 + fixtures，零行为消费） | **已登记**（CHANGELOG 披露⑤专段） |
| `bff298d` | FEAT-047 | BaselineMetadata provenance（0.86.0 批 1 票 3） | 仅在 FEAT-052 行括注提及，无专段 |
| `b2152ea` | FEAT-051 | task-row-update 写入器 CLI（0.86.0 批 1 票 1） | **未登记**（M-1 CHANGELOG 冻结后落库） |
| `1cd224e` | FEAT-046 | governance_store 写入器族（0.86.0 批 1 票 2） | **未登记**（M-1 CHANGELOG 冻结后落库） |

### 本版不发布什么（显式排除——Amazon 实践，对照 release-checklist-0.84.0「目标版本下不发布」先例）

1. **0.86.0 架构演进全链**（DEC-220/221——FEAT-042~048 候选池：四类写入器、closure 纵切、混沌测试发布门、存储 JSON 化）；
2. **混沌测试发布门**（0.86.0 批 2.2 承载——commit 失败/push 凭据失败/push 超时 UNKNOWN 三边界 kill+resume 零人工修复；本版 M-2 无此门，0.86.0 规划已显式将其列为该版 M-2 MUST）；
3. **RISK-055 终态裁决**（纯净复采样未到期——DEC-215①：发布窗不阻塞于 RISK-055）；
4. **resident 4K arch 目标与 skill 层翻硬**（0.86.0+ 候选，经 FEAT-047 BaselineMetadata 承载）；
5. **FIX-363 非族 3 项**（loop-runtime-claims 活体耦合——FIX300DualCaliber ×2 + LoopRuntimeClaim 既有失败，见 checklist 归因节）；
6. **任何 RISK 的关闭声明**（本版无 RISK 关闭承诺；打开态全集以 risk-log 实况为准）。

## M-链状态（截至本文件落盘 2026-09-20）

| 里程碑 | 状态 | 事实 |
|---|---|---|
| M-0 规划确认 | ✅ 完成 | `6325ee6`（2026-09-19）：双半面规划 + Design/Release 双审 R0→R1 通过 + 用户裁定 MINOR 两批制；EVD-1090 |
| 批 1 执行（7 票） | ✅ 完成 | `be0b844`→`2e80c69`（2026-09-19）；逐票 change-triage 机录 + Code Review R0 全闭环 |
| 批 2 执行（3 票串行） | ✅ 完成 | 2.0 量测（EVD-1092）→ `b717835` 2.1 瘦身 → 2.2 canonical 重测（EVD-1104）→ `407b230` 2.3 翻 hard（P3-3 同 commit，DEC-211③）→ `1519bf1` 2.4 skill 层预算 |
| M-1 候选打包（开发面） | ✅ 完成 | `a91d6b4` FEAT-053（2026-09-19）：bump 24 tracked + CHANGELOG 段 + 投影 28 面 + 豁免账本 10 行；REVIEW-FEAT-053-R0 = APPROVED_WITH_NOTES/0；EVD-1109 |
| **M-1R 发布面（本票）** | 🔄 本票执行 | FEAT-054：三件套 + candidate manifest + 门禁实测 + M-2 全量 pytest 归因 |
| M-2 门禁实测 | 🔄 本票承载 | 快速门禁已实测（见 checklist Candidate Gate Results）；check-release / 全量 pytest 由本票执行 |
| M-3 双半面审查 | ⏳ 待 Coordinator 派发 | Release Reviewer + Design/Code Reviewer（按变更面）；复审必达 |
| M-4 用户停点 | ⏳ DEC-217 预授权 | 预授权不免除 M-2/M-3；go/no-go 由 Coordinator 呈现裁决 |
| M-5 transition + tag | ⏳ Coordinator 面 | release commit（单父 = candidate；manifest-only candidate_to_released + integrity）→ annotated tag v0.85.0（peel = transition commit） |
| M-6 released 门禁 | ⏳ M-5 后 | `check-release --lineage-mode released --release-commit <commit>` + `release-ledger --remote` |
| M-7 push | ⏳ Coordinator 面 | master + tag 原子推送（远端 SHA 精确一致） |
| M-8 归档 + 收尾 | ⏳ Coordinator 面 | `archive.py migrate --auto --dry-run` → 迁移 → `check-archive-integrity` PASS；plan-tracker `工作流版本` → 0.85.0（当前 0.84.0 过渡态 WARN——check-version-consistency 实测在案） |

## 发布窗口

| 时点 | 内容 |
|---|---|
| 2026-09-19 | M-0 裁定 + 批 1/批 2 全部载荷落库（17 提交窗口 `3663423..1cd224e` 全部当日）+ M-1 候选打包 `a91d6b4` |
| 2026-09-20 | **M-1R（本票）**：三件套 + candidate manifest + M-2 门禁实测 + 全量 pytest 归因复核 |
| M-3 后 | 双半面审查 → M-4 go/no-go（DEC-217 预授权呈现）→ M-5 transition/tag（发布时点按 FIX-349 口径 = **taggerdate 权威**，CHANGELOG 条目日期 2026-09-19 如有出入届时勘误对齐） |

## 门禁摘要（数值基线）

| # | 门禁面 | 基线 / 姿态 | 依据 |
|---|---|---|---|
| 1 | 注入预算 resident 三 profile（**hard**——FEAT-050 翻 hard 生效） | lightweight **4,216**/6,000 · standard **5,694**/6,000 · strict **5,966**/6,000 —— 全 PASS；strict 余量 34 tok（0.57%）接受现状（EVD-1104 裁决：双层预警在位 + hard 硬门守护） | 本票 2026-09-20 当场实测（check-injection-budget ×3 profile）+ EVD-1104 |
| 2 | skill 层独立预算线（report-only） | entry-skill **14,456/16,000** ok（+10.7% 余量）；per-tier：resident=6000/hard · skill=16000/report-only · command=6000/report-only | FEAT-052 / EVD-1107 + 本票实测 |
| 3 | 混沌测试发布门 | **N/A 本版**——0.86.0 批 2.2 承载（三边界 kill+resume 零人工修复；该版 M-2 MUST 含混沌复演） | 0.86.0 版本规划（REL-082 双审通过，DEC-220/221） |
| 4 | 既有测试失败披露口径 | FIX-359 后 RISK-056 匹配器族 30 项清零；剩余先在失败 = FIX-363 候选非族 3 项（FIX300DualCaliber ×2 + LoopRuntimeClaim ×1）——本票 M-2 全量 pytest 当场值归因复核 | CHANGELOG 0.85.0 Fixed + AUDIT-152 分类账本 + 本票实测 |
| 5 | 投影 / 版本面 | release-projection 28 面 PASS（source=0.85.0）；版本声明 13 面 + bootstrap markers 一致（1 WARN = plan-tracker 过渡态，M-8 收口） | 本票实测 + EVD-1109 |
| 6 | hooks_drift 披露 | 沿用 DEC-213④ 接受态（用户一次性重装命令移交中）——M-2 披露面非阻断 | version-plan 交付 5 项 8 |
| 7 | 归档触发检测 | M-8 MUST：dry-run → 迁移 → `check-archive-integrity` PASS（完整性失败阻断发布完成） | ADR-006/007 |
| 8 | candidate ledger 两态 | candidate 态 `release-ledger --no-remote`（提交前 = 预期 FAIL，见 checklist #15 口径）→ 提交后 PASS（NATIVE_CANDIDATE）→ M-5 后 `--remote` | ADR-010 / 0.84.0 同流程 |

## 硬门槛自检（本任务）

| 门槛项 | 判定 | 依据 |
|---|---|---|
| 三件套 + manifest 四文件成形、对照先例无缺面 | **PASS（修复回合终态）** | 结构逐节对照 `release-checklist-0.84.0.md` / `rollback-plan-0.84.0.md` / `core/releases/0.84.0.json`；plan 面继承 `version-plan-0.85.0.md`（M-0 双审通过版）事实基线；feature-flags 面初裁不产出（范围裁定）→ **修复回合 Coordinator 裁决选 (a) 已补授最小形态** `docs/release/feature-flags-0.85.0.md`——release-docs 门禁四件套全过（check-release 终验 PASS） |
| check-release | 见 checklist（如实列差距） | 门禁含 governance health / hot fact source / release-docs 等既有披露族 |
| release-ledger candidate 态 | 提交前 FAIL（预期）→ 提交后 PASS | ledger 契约：`trust.candidate_commit = git_commit_adding_path` 需提交派生（0.84.0 #15 同观测值） |
| M-2 pytest 全量结果如实（含先在失败归因） | 见 checklist #17 | 三先在失败归因复核（HEAD worktree 法） |
| verify 全量 | 见 checklist #12 | 全量资产 + 适配器契约同步 |
| 不触在途面 / 不改 `.governance/` / CHANGELOG 不再改 / tag·push·transition 不执行 | **PASS** | 写入面 = 三件套 + manifest 四文件；`.governance/` 零写入；CHANGELOG 自 `a91d6b4` 未触碰 |

---
*FEAT-054 M-1R 起草冻结（2026-09-20，Governance Developer Agent）。事实基线：17 提交窗口与 hash 取自 `git log`/`git rev-list` 实测（`3663423..1cd224e` = 17；tag `v0.84.0` peel = `5d1943f`，`git for-each-ref` 实测）；门禁数值取自 2026-09-20 当场命令输出；M-链/EVD/DEC 取自 `.governance/` 热文件与 CHANGELOG 0.85.0 段（`a91d6b4` 冻结版）。未生成事实（发布 tip、tag、released 态门禁）一律标期义务，不预填。*
