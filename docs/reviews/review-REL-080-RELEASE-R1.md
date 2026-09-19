# 发布审查报告 — REL-080（0.84.0 候选就绪状态）RELEASE 半面 R1

**结论：NEEDS_CHANGE ｜ round=R1 ｜ unresolved_blockers=3**

- **前轮引用**：`docs/reviews/review-REL-080-RELEASE-R0.md`（round=0，NEEDS_CHANGE，`unresolved_blockers=6`，F-01~F-06 + P2×2/P3×6）；机录 `review-REL-080-R0`（evidence-log L2276，结论 NEEDS_CHANGE）
- **审查方**：Release Reviewer Agent（独立复审；只读——本报告除本文件外零写盘；复跑前后 `git status --porcelain` 逐行一致，33 项不变）
- **审查对象**：0.84.0 候选 = `HEAD b537976` + **33 个 staged 文件**（R0 时 28 → 新增 5 项发布期产物 + 1 项产品代码）+ `docs/release/{release-checklist,feature-flags,rollback-plan}-0.84.0.md` + `project/CHANGELOG.md [0.84.0]` + `core/releases/0.84.0.json`（candidate）
- **审查日期**：2026-09-19 ｜ **审查性质**：R0 六阻断项收口实证 + R0 后新增发布期工作裁决
- **证据基线**：MUST 复跑面全量独立复跑（14 项，含 `check-release` 全量执行闸门 **两次** 实跑与全量 `pytest` 实跑 18:57）——本轮**无「未独立验证」门禁**（对比 R0 §0 的 5 项未复跑）
- **硬门槛裁决**：**未满足**（`check-release` 仍 exit 1 / **2 issue(s)**：archive integrity〔本版**新增**〕+ governance health〔先例存量〕；Gate 16 披露颗粒度未达 0.83.0 先例；FIX-355 产品代码变更无审查覆盖）→ 见 §9

---

## 0. 独立复跑证据（只读 —— 与 Coordinator 收口申报逐项对照）

| # | 命令（只读） | 我的复跑结果（当场值） | 与申报对照 |
|---|---|---|---|
| V-1 | `check-version-consistency` | **PASSED exit 0**；13 面 + 双入口 marker 全一致；**0 WARN**（R0 的 1 WARN=plan-tracker 0.83.0 已随 M-8 收口消解） | 与申报一致 ✓ |
| V-2 | `check-projection-sync --fail-on-issues` | **PASSED exit 0**；入口双根 + DSH 方言互认（3,634B/59L） | ✓ |
| V-3 | `check-entry-bootstrap-sync` | **PASSED exit 0**；`CLAUDE.md=23835B/full`、`AGENTS.md=2988B/thin`（双根同值） | 与 #3 逐值一致 ✓ |
| V-4 | `release-projection` | **`state=PASS` exit 0**；`source_version=0.84.0`、**`projections_checked=27`**（26→27，R0 为 26）、`declared_legacy_snapshots=10`（converged 0 / missing 0） | 与 F-05 申报 27 faces 一致 ✓ |
| V-5 | `check-manifest-consistency` | **PASSED exit 0**；canonical **769** / actual **870** | #7 仍写 767/865 → **未刷新（F-09）** |
| V-6 | `check-governance --summary-only` / `--level strict` | **`Governance: 21 issues` exit 0**；FAIL 面 = **28s ×1**（1,574,505 B / 1537.6 KB，advisory）；WARN 面 20 = **2×4 / 14×426 / 27×1 / 28n×8 / 28q×4 / 30×29 / 30c×2 / 36×16** | 总数 21 与申报一致 ✓；**构成枚举不完整（F-18）** |
| V-7 | `check-archive-integrity` | **FAIL exit 1**：`Archive trigger gap: 1 hot completed task(s) should be archived via release_forced for v0.1.0~v0.82.0`；hot 85 / archived 93 / index 1221 / total 178 / **pending 1** | R0 及 checklist #10 均记 PASS → **新增阻断（F-15）** |
| V-8 | `archive.py migrate --auto --dry-run` | tasks 扫描 **25**（R0 为 21/24 口径）→ 满足条件 **1** / 保留 24；逐条 `would_archive=1`；evidence 满足条件 1 = EVD-892（FIX-246） | 根因确认：**FIX-246 任务行恢复是唯一新增可归档项** ✓（非时点漂移） |
| V-9 | `check-release … --skip-execution-gates`（静态面） | **FAILED 1 issue**；version consistency / release fact source / hot fact source / runtime readiness / first session measurement / governance pack / agent adapters / projection sync / cross references / **release docs** / release lineage / gate sequence / one dot zero blockers / loop fuse / changelog / loop runtime claim **全 PASS** | **hot fact source 已 PASS**（R0 FAIL① 收口成立）✓ |
| V-10 | `SPG_RELEASE_GATE_TIMEOUT=600 check-release --version 0.84.0 --require-changelog --lineage-mode candidate`（**全量执行闸门**） | **FAILED 2 issue(s) exit 1**：①`archive integrity` FAIL（同 V-7）；②`execution gates` FAIL = **`governance health (exit=1)`** + `verify (exit=0)` PASS + `e2e check (exit=0)` PASS + **`unit tests (exit=0)` PASS** + `dsh upgrade regression PASS`（隔离 temp-DSH_HOME 冒烟） | **unit tests 闸门已 PASS**（R0 FAIL③ 收口成立）✓；**governance health 子门 exit=1 仍在**（先例存量） |
| V-11 | `pytest skills/software-project-governance/infra/tests -q`（全量实跑） | **30 failed / 3451 passed / 1 skipped / 390 subtests passed**（1137.35s = 18:57）；30 项全部为既有环境族（`test_pre_commit_review_evidence.py::ReviewEvidenceRegexTests::test_a_legacy_end_column_hits` 等 hook 子测 ×24〔根因 = 本机无 WSL 发行版：`WSL_E_DEFAULT_DISTRO_NOT_FOUND`〕+ `test_hooks.py::PlanTrackerMatcherTests::test_replay_real_plan_tracker_hits` ×6〔活体耦合〕）——**0 新增失败**，FIX-352/353 的两处版本钉 RED 已消失 | 收口成立 ✓；申报「3443」经溯源 = `EVD-1081` 的「0.84.0 开发期基线 30F/3443P」（基线口径，非本项复跑值，见 F-20） |
| V-12 | `git rev-list --count 2a15e59..b537976` / 窗口清单 | **10** 提交，逐 hash 与 Change Inventory 一致；`2a15e59` = REL-079 M-8 收尾（2026-09-17）✓；`git rev-parse v0.83.0^{}` = **`296f4f5`** ✓（tag 对象 `e0cf42a`）；`git describe --tags` = `v0.83.0-11-gb537976` | 演练 P-1 锚定三项**逐值核实成立** ✓ |
| V-13 | `git diff --name-only 2a15e59 b537976` | **82** 文件 | 演练 P-3「82 paths」**独立复算一致** ✓ |
| V-14 | 演练零污染面 | `git ls-files -u` = **0**；`.git/REVERT_HEAD` = False；`.git/MERGE_HEAD` = False；`%TEMP%\fix354_drill_20260919_032603` = **False（已删除）** | 三重指纹核验**当场复核一致** ✓ |
| V-15 | `git status --porcelain` + staged 面 | **33 项 staged**、零未暂存改动；复跑前后不变 | 见 F-19（清单归属） |
| V-16 | 版本平面逐值 | fixture vs canonical `commands/governance-init.md`：**SHA256 全同 `531B8C66169EB312FD4AA2523275BC3C1D74F41DC60DA232DCF52D0B40C9F80C`、字节全同 77,904**；`@bootstrap-version: 0.84.0` = 4 / `0.83.0` = **0** | F-05 修复**逐字节核验通过** ✓ |

---

## 1. R0 六阻断项逐条比对（MUST —— 不得盲批）

| R0 项 | 内容 | **R1 判定** | 实证 |
|---|---|---|---|
| **F-01** | REL-080 execution packet ×6 | **已修复** | `execution-packets.json` 现有键 = `REL-080` / `FIX-354`；REL-080 包六字段**全填充**（`product_success_contract`〔user/job_to_be_done/non_goals×3/success_metrics×3/competitive_baseline/done_definition×3〕、`acceptance_contract`（含 `last_run` + `demo_evidence`）、`quality_budget`（6 维全 pass + threshold/validation/evidence/exception）、`vertical_slice`（含 `rollback_plan`/`status=PASS`）、`interruption_policy`（含 `assumption_record` 四字段：assumption/basis/reversibility/validation + rollback））→ V-6 实测 **18c/18d/18f/18i 四族 FAIL 全部归零**（R0 为 1+2+2+1）；V-10 中 `hot fact source` 已 PASS。**收口成立**（packet 内部 `status` 字段为 `⏳ 进行中` 属快照时效瑕疵，见 F-21，不影响契约有效性） |
| **F-02** | 快照 `**session_date**` + 新写 | **已修复** | `.governance/session-snapshot.md` 第 3 行为 `**session_date**: 2026-09-19`（可解析）；0.81.0/0.82.0/0.83.0/0.84.0 四行发布线齐备且 ID 注记（REL-079→REL-080 更正）在位；**`RECO-FEAT-032` 全文件 0 命中**（dangling 已移除），缓存池行改引 `RECO-AUDIT-154`；**Check 28c FAIL 与 Check 35 WARN 双双归零**（V-6 实测 28c 不在 21 项内）。**「新写」而非复制成立** ✓ |
| **F-03** | 回滚演练（硬门槛「已验证」） | **已修复** | 隔离副本演练 15 步表落 `rollback-plan-0.84.0.md` §演练记录（L132-195）。**方法学裁决 = 接受**：①就地执行被**实测否决**（脏索引下 `revert --no-commit` 不拒绝 + `Auto-merging SKILL.md ×5` 自动并入已暂存内容 ⇒ 会污染 28 文件候选索引）——该否决有 controlled experiment 支撑，非推测；②隔离副本（`--no-hardlinks` 66MB + 整目录删除）不满足 M7.7 真实环境三选一的**触发条件**（未触碰 `$HOME`/`$DSH_HOME`/仓外路径），故无需三选一；③ `%TEMP%` 独立副本 + 零污染三重核验（V-14 当场复核）构成可复查事实；④ 关键路径**我不采信申报而独立复算**：P-3「82 paths」→ V-13 实测 **82**；P-1 锚定 `2a15e59`/`296f4f5`/10 提交 → V-12 全对。⑤ P-4「完整窗口近似」以两个**显式标注的合成提交**（`e1aaa5e`/`a1027bd`，仅存在于已删除副本）承载 `2a15e59..<tip>` 语义，且以 `git diff --cached 2a15e59` **空** 证明索引与发布线树逐字节相同——诚实近似，真实 tip 复跑义务已明确移交 M-5（checklist #18）。**未包装为「真实 tip 演练通过」** ✓ |
| **F-04** | unit tests 闸门 + 全量 pytest 收口证据 | **部分修复 —— 技术面成立，包内记录未收口** | 技术面**已独立验证**：V-10 实测 `unit tests (exit=0)` **PASS**（`SPG_RELEASE_GATE_TIMEOUT=600` 覆盖生效）；V-11 全量实跑 **0 新增失败**（30 = 既有环境族），与申报方向一致。**但**：① checklist #17 仍写「32 failed/3441 passed」+「全量复跑列为 Coordinator/CI 义务（本报告不预填复跑结论）」；② M-8 义务第 3/4 条（L184/L185）复选框**仍未勾选**；③ 发布包内无全量复跑原始输出或写入行。**技术风险已消，证据缺口仍在** → 降级计入 F-20（P2 非阻断） |
| **F-05** | fixture governance-init 4 钉 | **已修复** | V-16 逐字节核验：fixture ≡ canonical（**SHA256 全同、字节全同 77,904**、4×0.84.0 / 0×0.83.0）；投影合同原子入账经**独立核对**：`version-projections.json` +1 条 `{"id":"fixture-command-governance-init","kind":"byte_copy","source":"commands/governance-init.md","target":"project/e2e-test-project/commands/governance-init.md"}`、`manifest.json` `release_projection_contract.projection_ids` +`fixture-command-governance-init`、`version` 0.83.0→0.84.0；V-4 实测 27 faces PASS。**拒绝手工 bump 的裁决我认可**：手工改 4 行会使 FIX-238.2 陈旧标记失真（文件内容非模板渲染产物即无同步路径），byte_copy 合同使后续 `release-projection --write` 自动同步——根因级修复而非症状级 ✓ |
| **F-06** | FIX-352/353 入账 | **已修复** | `EVD-1082`（L2278）/`EVD-1083`（L2279）全文在位（含事实依据/受控实验双向对照/边缘披露）；plan-tracker L91/L92 两行 ✅ 且指明「并入 REL-080 审查——DEC-213⑥」；`DEC-213⑥` 在 decision-log L154 记明折叠裁决与前提（测试面零生产行为变更 + Reviewer 独立复跑 + diff 无断言弱化）。**满足 R0 §5.3 的「入账 + 折叠裁决为提交前强制项」** ✓ |

**六项小结：已修复 5（F-01 / F-02 / F-03 / F-05 / F-06）｜部分修复 1（F-04 —— 技术面已独立验证通过，仅余包内记录，降级至 P2 F-20）｜未修复 0。**
> 复核澄清：R0 §0 把 `check-archive-integrity` 复跑为 PASS，而 R1 实测为 FAIL。二者不矛盾——该缺口由 **R0 之后**的 FIX-246 任务行恢复引入（V-8 根因确认），属新引入项 F-15，非 R0 判定错误。

---

## 2. 维度一：R0 后新增发布期工作的入账完备性

### 2.1 FIX-354（F-05 + F-03 承载）—— **入账基本成立（P2 备注）**
- 交付物与 EVD 申报一致：投影合同 3 文件（`version-projections.json` +1 / `manifest.json` +1 原子）+ fixture 再生成 + `rollback-plan` 演练段，V-4/V-16 逐项独立核验通过。
- **缺口**：plan-tracker L93 状态仍为 `🔄 进行中`，实际交付物已全部落盘（§1 F-05/F-03 已判「已修复」）；任务行未翻转终态，且 **EVD 行尚未落账**（`.governance` 对 `FIX-354` 命中仅 decision-log L154 + packets + plan-tracker，无 EVD 行）。发布期修复无 EVD 行随发布入库，与 F-06 的口径不一致（F-06 是 R0 阻断项、必须入账）。**裁决：不构成阻断**（同一提交周期内可于 R1 后随 EVD-1084 一并落账），但 MUST 在 R1 通过后与 FIX-355 同批补齐，不得再次遗留。

### 2.2 FIX-355（Check 30 归档感知）—— **入账缺失 ×7 面 ⇒ 阻断（F-16）**
交付物本身**质量合格**（我的只读复核，非完整代码审查）：`review_domain.py` +168/−10（`closed` 门集、`_live_task_completion_sets` 拆出 active 半边、`_archived_completed_task_ids` 限定 `## Task 索引` 段 + ID 正则 + 复用 `_status_is_completed_cell`）；`test_review_closure_legacy.py` +211（**36 → 44 = +8 测试**，与「8 测试」申报**逐数吻合**）；**fail-closed 守卫齐备**（index 缺失/不可读 → 空集回退 pre-FIX-355；tracker 不可读 → `(None,None)` 显式 UNKNOWN **不当作空**）；**作用域有意收窄**（标注该集不得进入 V1 breach 臂，并附 7-FAIL 实测回归佐证）；**live-row 权威**（`- live_active`，含 `test_live_active_row_outranks_stale_archive_row`）；V2 实测 **2→0**（V-6 中 Check 30 输出 29 WARN，无 V2）。
**但入账 7 面全缺**：① plan-tracker **无 FIX-355 任务行**（仅 L280 路线图处一行旁列 + L94 FIX-246 行的因果提及）；② `execution-packets.json` **无 FIX-355 包**（对比 FIX-354 有包）；③ **无 EVD 行**（evidence-log 止于 EVD-1083）；④ `.governance/change-triage/` 无 `FIX-355.json`（目录内 0 个 FIX-35x）；⑤ **无独立审查记录**（`docs/reviews/` 与 `.governance/review-*.md` 对 `FIX-355` **双零命中**）；⑥ checklist **无该门禁面的归属行**；⑦ 33 staged 归属清单**漏列** `review_domain.py`（§4）。
**性质**：与 R0 F-06 同型（产品代码变更随发布入库而无 task/triage/EVD/审查），且**范围更大**——F-06 是测试面，本项含 **+168 行核心校验逻辑变更**。

### 2.3 裁决点：FIX-355 是否需要独立 Code Review（**要求独立审查 —— 理由均为可复查事实**）
**裁决 = 需要（不可并入本次发布审查作为唯一覆盖）**，理由：
1. **DEC-203 的明文前提**（decision-log L143）：否决 (b) 产品修复时写明「**如未来重启需 superseding DEC + Developer→Code Reviewer 走链，非本会话范围**」。FIX-355 **正是** (b) 的重启（归档感知使 L-A 降级对归档任务生效）。走链是该否决被解除的**生效条件**，非可选风格。
2. **自指耦合**：被改的是**校验审查链完整性**的检查器（Check 30）。由发布审查（Release Reviewer）兼任其唯一代码审查，等于让审查链的守卫变更只接受一次非代码面审查——R0 §5.3 处理 FIX-352/353 时的折叠逻辑（测试面 + 零生产行为变更 + 独立复跑承载）**在此不成立**：本项有生产行为变更，且变更方向是**扩大豁免门**（V2 FAIL→WARN）。
3. **规模量级**：+168 行生产代码 = 本版发布期修复中最大的一处生产面变更。
4. **豁免面的新暴露（我对交付物本身的实质质疑）**：`closed` 集现在包含「归档索引中状态列断言完成」的任务 ⇒ 任何**归档行**任务都进入终态豁免——包括 REL-078 这类本应**如实保留 FAIL** 的历史缺口。fail-closed 守卫只覆盖「索引不可读」与「tracker 不可读」，**不覆盖「归档行存在但轮次事实不完整」**（这正是 REL-078 的形态）。测试面已显式接受该语义（`test_archived_closed_task_leading_gap_downgrades_to_warn`、`test_archive_predicate_beats_fix341_conservative_veto`），即**行为系有意**——但它与 `DEC-199`「FAIL 如实保留」的字面口径存在张力（由 FIX-246 半面的「终态登记非补造」压住，REL-078 半面则无对应处置）。**该张力必须由独立代码审查 + superseding DEC 显式裁决，不宜由发布审查单方接受。**
> 注：本项属「覆盖/账目」类阻断，**不指向 Delivered 代码的明显缺陷**（交付物质量我评为合格）——与 F-15 的性质不同，勿混同处置。

### 2.4 裁决点：DEC-213⑧ 的 superseding 合规性 —— **不合规 ⇒ 阻断（F-17）**
- 任务申报为「superseding DEC-203 半面〔DEC-213⑧〕」，**checklist L140 亦已对外声明「superseding DEC-203 半面否决——DEC-213⑧」**。
- **实测**：decision-log DEC-213 全文（L154）仅含 **①~⑦**，**不存在⑧**；全文件 `⑧` 仅 1 次命中且属 DEC-190；`DEC-203` 仅 1 次命中（L143 否决记录本身）。**即：superseding 未落账，且发布文档已先行引用一个不存在的决策项。**
- 合规缺口 = ①superseding DEC 文本缺失（DEC-203 生效条件未满足）；②Developer→Code Reviewer 走链缺失（§2.3）；③发布文档**引用了不存在的条目**（比「未披露」更需纠正的失实引用）。
- **裁决**：FIX-355 **不得**以「已由 DEC-213⑧ 授权」的名义随本版入库；MUST 先补 DEC 文本（内容与交付物一致即可，无需新增论证）并完成审查覆盖。

### 2.5 裁决点：FIX-246 任务行终态恢复 + 归档副作用 —— **恢复本身合规，副作用未处置 ⇒ 阻断（F-15）**
- 恢复**合规性我认可**：L94 行完整承载原始证据（EVD-892 + `REVIEW-FIX-246-R1` 机录 APPROVED_WITH_NOTES/0）、标注「终态恢复非重做」、并声明 R0 记录缺口按 `DEC-199` 如实保留为 WARN（Check 30 现为 **29 closure WARN**，其中含 FIX-246 半面，V2 归零）——**属登记恢复而非机器补造，方向正确**。
- **但恢复引入未处置副作用（新阻断 F-15）**：该行落于 v0.57.0（≤v0.82.0 归档窗）⇒ **新增 1 个可归档 complete task**，V-8 dry-run 实测 `满足归档条件 1 / would_archive=1`，直接使 **`check-archive-integrity` 由 PASS 转 FAIL exit 1**，并在 V-10 全量 `check-release` 中呈现为 **`archive integrity` FAIL**——而 checklist #10 与 #14 目前**仍记 PASS**，披露面**零提及**。
- **必须二选一并复跑**：① 执行 `archive.py migrate --auto`（已实测有 1 task + 1 evidence 待迁，须先 ask 确认——FEAT-035 语义）；**或** ② 若裁决「发布期不迁移」，则 MUST 在 checklist 中把该 FAIL 逐条归属（载体 + 触发根因 + 处置人 + M-5 前复跑义务），且 **MUST NOT** 继续以 PASS 记 #10/#14 —— 否则该 FAIL 以「未披露的门禁失败」形态随发布入库。
- **提示**：选项 ② 会使 `check-release` 在本版**始终** return exit 1（即使两项 sub-gate 都已归属）；0.83.0 先例中 `governance health` exit=1 被接受，但**从未有「archive integrity」FAIL 被接受的先例**（0.83.0 该门为 PASS）。故推荐 ①。

---

## 3. 维度二：governance health 21 issues 的披露充分性（对照 0.83.0 Gate 16 先例）

**结论：21 issues 的「存量地位」与先例同级；「披露颗粒度」未达先例 ⇒ 阻断（F-18）**

| 对照面 | 0.83.0 先例（Gate 16，L83 + 披露清单 ①，L107） | 0.84.0 当前（checklist L133/L142 + 披露清单 ①） | 判定 |
|---|---|---|---|
| 总数 | 21 issues（当场终值） | **21 issues**（我 V-6 实测一致） | ✓ **同级**，可作先例引用 |
| 逐条归因 | **明确列为 RELEASE R0 F-1 义务**，并①~③逐项归因（含「文档枚举 vs 申报」的口误纠正、4E+8W 的段头归属差异、14/36/2/30c 未枚举项的**补齐归因**） | 仅列族名「28s advisory ×1 + WARN 族〔28n/14/36/28q/2-stale〕」 | ✗ **未达先例** |
| 枚举完整性 | 覆盖 28o 残余、28s、Check 30 V2、28q（含逐项说明与移交面） | **漏 3 族**：**Check 27×1（本版新出现的 archive trigger gap WARN——即 F-15 在 governance 面的同源呈现）**、**Check 30×29（含 FIX-246 半面 WARN）**、**30c×2**；且**漏扫 28n 由 ×8 变化的面**（我实测 28n = 8，与 0.83.0 的「4E+8W 共 12 条」口径不同——构成漂移未被归因） | ✗ |
| 数值一致性 | — | 28s 记「1,534.4 KB」→ 我实测 **1,537.6 KB**（当期漂移，属 R0 F-07 同型精度缺陷） | ✗ P3 |
| 门禁地位 | 明确「存量披露（advisory/已接受），**非通过项**」 | 有同口径声明，且明确「governance health 子门 exit=1 接受 + 0.83.0 Gate 16 同型先例」 | ✓ 口径正确 |

**裁决**：**21 issues 的存量披露地位成立**（先例可比，且 `--fail-on-issues` exit=1 我实测复现，属已知存量而非本版劣化）——**不因其数量或 exit=1 本身阻断发布**。**但其构成枚举不完整、且遗漏本版新生成的 Check 27**，未达到 0.83.0 先例**明文要求的逐条归因颗粒度**；发布文档**引用先例却未履行先例义务**，属可确定性收口的披露缺陷 → 计入**阻断 F-18**（收口＝补齐三族枚举 + 28n 构成漂移归因 + 28s 数值刷新；无需产品代码改动）。

---

## 4. 维度三：staged 33 文件清单核对（28 原始 + 发布期修复归属披露）

`git status --porcelain` 实测 **33 项 staged，零未暂存改动**（V-15）。归属核对：

| 归属面 | 文件数 | 明细 | 判定 |
|---|---|---|---|
| R0 原始 28 面 | 28 | 与 R0 §6 逐项一致（版本/投影 20 + 三件套 3 + CHANGELOG 1 + candidate 1 + REQUIRED_SNIPPETS〔同文件〕+ FIX-352/353 测试 2 + `verify_workflow.py`） | ✓ 一致 |
| M-0/M-1 发布产物 3 | +3 | `docs/release/{release-checklist,feature-flags,rollback-plan}-0.84.0.md` | ✓ |
| R0 报告入库 1 | +1 | `docs/reviews/review-REL-080-RELEASE-R0.md` | ✓（本轮 R1 报告入库后将为 34） |
| FIX-354 投影合同 1 | +1 | `core/version-projections.json`（+6 行） | ✓ 归属正确 |
| **FIX-355 生产代码 △** | **+1** | **`infra/checks/review_domain.py`（+168/−10）——送审申报的「staged 33 文件清单核对（28 原始 + 发布期修复归属披露）」中「发布期修复」仅点明 FIX-354/355 的入账/EVD 面，未列本文件为 staged 平面成员** | △ **披露漏项（P2 → 见 F-19）** |
| 合计 | **33** | | ✓ 计数一致，**归属披露缺 1 面** |

- 无夹带：无 0.85.0 候选池内容、无 RISK 关闭声明、无 1.0.0 面改动、无 0.83.0 既有开关删除，`core/releases/0.84.0.json` 仍 `candidate` ✓。
- **提示**：`review_domain.py` 属产品代码且**进入本次发布提交**——其归属披露须与 F-16/F-17 的入账、审查覆盖同步补齐（同一件事的三个面）。

---

## 5. 维度四：发布文档三件套与 R0 P2/P3 文档项的复核

`rollback-plan`（28,655 B / 196 行）与 `feature-flags` 我复核**结构完整、无夸大**（沿用 R0 的通过面，R1 只需增量核对，见 §1 F-03）。**checklist 的精度缺陷与过期义务（全部为可确定性收口）**：

| R0 项 | 内容 | **R1 判定** | 实证 |
|---|---|---|---|
| **F-07** | Gate 10 声称「FAIL/WARN/ERROR 均逐项列明」但枚举不全 | **未修复**（并入 F-18 一并收口） | L142 仍为族名级枚举；且新增漏 Check 27/30/30c |
| **F-08** | #13 把 packet ×6 统一写作「Check 18c ×6」 | **未修复**（P2，非阻断） | L100（R0 为 #13 行）仍写「FAIL 构成：**Check 18c ×6 = 「REL-080: missing execution packet」**」；实测跨 18c×1/18d×2/18f×2/18i×1。另该行整段为**收口前快照**（29 issues / 28c FAIL / Check 30 V2 ×2 均在列）未更新 |
| **F-09** | `AGENTS.md` 16,011B→2,699B 为 FEAT-037 时点值 | **未修复**（P3） | L38 / L71 仍写 16,011B→2,699B；shipped 实测 2,988B（V-3），且与 L90 同行文件「AGENTS.md=2988B/thin」自相矛盾 |
| **F-10** | #17 计数「42 tests OK」不精确 | **未修复**（P3） | L104 仍写「两文件复验 exit 0（42 tests OK）」；实测 test_entry_projection 32 + test_bootstrap_aggregate 42 = 74 |
| **F-11** | #7 申报 767/865 | **未修复**（P3） | L94 仍 767/865；当场实测 **769/870**（V-5） |
| **F-12** | Check 30 V2 佐证引用应指 RISK-051 | **已修复**（方向修正） | 披露 ① 现引「DEC-199 / FIX-246 半面（归档窗口遗失、非机器补造）+ FIX-355 审计发现」，与 RISK-051/DEC-199 口径一致 ✓ |
| **F-13** | 快照自述与实测不符 + 仍写 REL-079 | **已修复** | 随 F-02 新写一并修正（ID 注记 + 四行发布线）✓ |
| **F-14** | M-8 义务「未 staged」表述过期 | **未修复**（P3） | L183 仍写「当前为工作树修改、**未 staged**」——实测两文件**已在 stage 区**（且 `FIX-352/353 修复` 与「Release Agent 只 staged 版本 bump 面」的表述同时过期） |
| **新增（本报告）** | #18 回滚演练行自相矛盾 | **新引入**（P1 → F-15 内一并收口） | **L105** `#18 M-2 revert 干跑（回滚演练）= 「M-5 期义务 / 未执行」+「不预填」`，而 **L139** 披露清单 `FIX-354（F-05 + F-03 回滚演练）——✅ 已交付（演练 15 步入 rollback-plan）`；页脚 L191 亦仍写「未实测项（M-5 revert 演练…）」。演练**已执行**（V-12~V-14 复核），但**门禁表 #18 未回填** ⇒ checklist 无法独立证明 F-03 收口 |
| 新增 | #14 结论行为收口前快照 | **新引入**（P2） | L101/L108 仍写「FAILED — 3 issue(s)」与「剩余 3 项 FAIL」；我实测**已为 2 issue(s)**，且 ①`hot fact source` 与 ③`unit tests` **均已 PASS**——收口成果未反映 |
| 新增 | L163/L166 义务项标签过期 | P3 | M-5 行仍称「proposed EVD-1082」（实为 EVD-1082/1083 已落账，发布证据应为 EVD-1084）；M-7 行仍称「proposed 全文」+ 复选框未勾（快照**已**落盘） |

---

## 6. 维度五：DEC-204 预授权范围符合性

**结论：PASS（范围无越权；但新增平面的授权依据待补）**

- `DEC-204` 边界复核沿用 R0 结论：范围 = FEAT-032~040 九任务 + REL-080 发布 0.84.0；**预授权不免除门禁**（明文）；不关闭 RISK-036/039/050/051；1.0.0 预留不动 ✓。
- 33 staged 项均在「0.84.0 发布 + 发布期修复」语义内，**唯一需要新授权依据的是 FIX-355**——其重启一条被 DEC-203 否决的路径，**必须**有 superseding DEC（§2.4）。未落账前以预授权名义推进 = 越权。
- 门禁不放弃：发布文档**未**以「预授权」免除任何 FAIL——但 `archive integrity` 的新 FAIL 目前**根本未被提及**（既未放弃也未披露），属披露缺失而非豁免滥用。

---

## 7. 维度六：M-6/M-7/M-8 收尾路径

| 项 | 事实 | 判定 |
|---|---|---|
| M-6 归档检测 | R0 时 `migrate --auto --dry-run` = 无可归档数据；**R1 实测 = 待归档 1 task + 1 evidence**（FIX-246 行恢复所致，V-8） | **由「跳过合理」变为「有实质待办」** → F-15 |
| M-7 快照 | **已新写落盘**，`session_date` 可解析，四行发布线齐备，dangling 清除（V-6 中 28c/35 归零） | **通过** ✓ |
| M-8 收尾清单 | 9 项义务中：#182（packet）已实测完成、#180（快照）已完成、#181（plan-tracker 版本行）已完成（V-1 的 0 WARN 佐证）；**#183/#184/#185 三条仍为未勾选 + 表述过期**（F-14/F-20）；缺 FIX-354/355 的 EVD 行与 F-15 的归档处置项 | **部分完备**（需补 4 项） |
| 路线图/版本行 | plan-tracker `工作流版本` = **0.84.0** ✓；REL-080 行 ⏳ 进行中（待 M-5 后置 ✅）；0.84.0 路线图行已含 FIX-352/353/354/355 全 token ✓ | ✓ 一致 |
| ledger | `0.84.0.json` = `candidate` ✓；M-5 commit 后 MUST 复跑 `--no-remote` 与 push 后 `--remote` | ✓ 处置正确 |
| Check 30 V2 | **2 → 0**（V-6 实测无 V2；Check 30 转 29 closure WARN） | ✓ 消解成立（前提见 F-16/F-17） |

---

## 8. 发现清单

### 8.1 本轮阻断项（3 项）

| ID | 级别 | 维度 | 问题（事实） | 处置 |
|---|---|---|---|---|
| **F-15** | **P1** | 门禁/归档 | **本版新引入门禁失败**：FIX-246 任务行恢复（v0.57.0 ≤ v0.82.0 归档窗）使 **`check-archive-integrity` 由 PASS 转 FAIL exit 1**（`Archive trigger gap: 1 hot completed task(s)…release_forced`；pending 1），并在 V-10 全量 `check-release` 中表现为 **`archive integrity` FAIL**（我实跑 **FAILED 2 issue(s)**）。发布文档 #10/#14 仍记 PASS，**披露面零提及**；R0 曾记该门 PASS（当时确实 PASS）。**另附带**：checklist **#18 回滚演练行（L105）仍记「未执行」，与 L139「F-03 已交付」及 rollback-plan §演练记录直接矛盾**（演练存在但**门禁表未回填** ⇒ 硬门槛无法由 checklist 自证） | 三件事一并收口：① `archive.py migrate --auto`（dry-run 已实测有 1 task+1 evidence；写操作须先 ask）；**或**在 checklist 归属该 FAIL 并修正 #10/#14（并接受 `check-release` 持续 exit 1——无先例）；② `#18` 回填演练实证（隔离副本 exit 0/0 冲突/82 paths + 完整窗口近似 98 paths/索引逐字节相同 + F-04 反向实证 exit 1/CONFLICT + M-5 后真实 tip 复跑义务）；③ #14 结论行刷新为当场值 |
| **F-16** | **P1** | 账目/范围 | **FIX-355（Check 30 归档感知，生产代码 +168/−10）入账 7 面全缺**：plan-tracker 无任务行、无 execution packet、无 EVD、无 change-triage、无独立审查记录（`FIX-355` 于 `docs/reviews/` 与 `.governance/review-*.md` 双零命中）、checklist 无门禁面归属行、staged 归属清单未列 `review_domain.py`。交付物**质量合格**（+8 测试／fail-closed 守卫齐备／live-row 权威／V2 2→0 实测），性质为**覆盖缺失而非缺陷** | 提交前补：task 行（P1/P2 + 版本 + 依赖 + 交付面）+ `change-triage` 机录 + EVD 行 + packet（对齐 FIX-354 待遇）+ **独立 Code Review 走链**（§2.3 裁决）+ checklist/staged 平面归属行。**不得**以「已由 DEC-213⑧ 授权」名义入库 |
| **F-17** | **P1** | 决策合规 | **superseding DEC 未落账 + 发布文档引用不存在的条目**：任务与 checklist L140 均声明「superseding DEC-203 半面否决——**DEC-213⑧**」，而 decision-log DEC-213 全文仅 ①~⑦（**无⑧**；全文件 `⑧` 仅 1 命中属 DEC-190，`DEC-203` 仅 1 命中属其否决记录本身）。DEC-203 为 (b) 重启路径设定的生效条件 =「superseding DEC + Developer→Code Reviewer 走链」，**两项均未满足** | 补 DEC 文本（内容与交付物一致即可）于 decision-log；同批完成 Code Reviewer 走链（可与 F-16 同一动作）；修正 checklist L140 的「DEC-213⑧」引用使之**指向真实存在的条目** |
### 8.2 非阻断项（含披露类 F-18 —— 与 8.1 同批收口，但不阻挡提交）

| ID | 级别 | 问题（事实） | 判定 |
|---|---|---|---|
| **F-18** | P1（披露类） | **governance health 21 issues 的披露未达 0.83.0 Gate 16 先例颗粒度**：0.83.0 把逐条归因列为「RELEASE R0 F-1 义务」并覆盖 28o/28s/Check 30 V2/28q + 补齐 14/36/2/30c 未枚举项；0.84.0 仅列族名且**漏 Check 27×1（本版新出现的 archive trigger gap WARN）、Check 30×29、30c×2**，未归因 28n 构成漂移（0.83.0 口径 4E+8W vs 我实测 ×8），28s 数值仍为 1,534.4 KB（实测 1,537.6 KB）。**21 的存量地位与 exit=1 本身我判为可接受**（先例同级，我实跑复现），不因其数量阻断 | 非提交前硬阻断（不涉及 staged 内容与代码覆盖），但属**发布文档未履行其自引先例的义务** → MUST 与 F-15~F-17 同批收口：Gate 16 行补逐条归因（三族补齐 + 28n 漂移 + 28s 数值刷新）；同时收口 R0 F-07（「均逐项列明」的表述与枚举二者对齐） |

| ID | 级别 | 问题（事实） | 判定 |
|---|---|---|---|
| **F-19** | P2 | staged 33 平面归属披露缺 `infra/checks/review_domain.py` 1 面（§4）；计数 33 与 28+5+1 关系未在申报/文档中显式列明 | 随 F-16 一并披露即可（同一件事） |
| **F-20** | P2 | F-04 的**包内记录未收口**：checklist #17 仍为 M-1 时点的「32 failed/3441 passed」并自述「全量复跑列为义务，本报告不预填」；#184/#185 未勾选；发布包内无全量复跑输出。**申报「3443」经溯源 = `EVD-1081` 的「0.84.0 开发期基线 30F/3443P」**（基线口径，非 FIX-353 后复跑值）。**技术面已由我独立验证成立**（V-10 `unit tests` exit=0 PASS；V-11 全量 **30 failed/3451 passed/1 skipped/390 subtests passed**，30 = 既有环境族〔无 WSL 发行版致 hook 子测失败〕，**0 新增**，FIX-352/353 两处 RED 已消失） | 非阻断：把 V-11 实测值 + V-10 闸门 exit 0 写入 #17 与 M-8 复选框即可（勿沿用 3443 作复跑结论） |
| **F-21** | P3 | 快照内部状态栏过期：`session-snapshot.md` 仍写「F-05 fixture 版本钉 + F-03 回滚演练（FIX-354 **进行中**）/ F-04 门禁复跑证据（Coordinator **待跑**）」，且**通篇未提 FIX-355**；REL-080 packet `status` 亦为 `⏳ 进行中` | 随 F-16 收口一并刷新 |
| **F-22** | P3 | checklist 其余精度项：L38/L71 `16,011B→2,699B` 时点值（shipped 2,988B，与 L90 自相矛盾）；L104「42 tests OK」（实测 74 = 32+42）；L94 `767/865`（实测 769/870）；L100 `Check 18c ×6`（实测跨 18c/18d/18f/18i）；L101/L108「3 issue(s)」（实测 2）；L183「未 staged」（实为已 staged）；L163/L166 义务标签过期 | 随 R1 收口批量刷新 |
| **F-23** | P3 | 演练记录内部小差异（**不利结论**）：演练零污染表记「staged 文件数 28 → 28」，而我当场为 33；差异可完全由「演练时点=28（R0 期）、其后新增 5 项发布产物」解释，且 V-14 五项残留核验当场同值 —— 属**时点标注可更明确**（建议补「演练时点 = R0 staged 28」限定语），非零污染结论失效 | 接受（建议补时点限定语） |

### 8.3 复跑的通过面（R1 无需重做）

hot fact source / release docs / release lineage（candidate 边界）/ gate sequence / one dot zero blockers / loop fuse block / changelog / loop runtime claim（identity+semantic 双 PASS，inventory `bc9a183e…`，849/849 parsed）/ verify / e2e check / **unit tests** / dsh upgrade regression（隔离 temp-DSH_HOME 冒烟 PASS，无限定语口径正确）/ 15 项静态面；CHANGELOG B-1~B-6 + 5 条抽样可追溯闭合（R0 已核，本轮核对未见漂移）；feature-flags 结构完整；rollback-plan 结构/区间锚定/演练记录；DEC-204 范围无越权。

---

## 9. 硬门槛逐项裁决

| 硬门槛 | 阈值 | 本次事实 | 判定 |
|---|---|---|---|
| 发布检查清单全部 PASS | = 100% | `check-release` **exit 1 / 2 issue(s)**（archive integrity 本版新增 + governance health 先例存量）；checklist #10/#14 仍记 PASS；#18 与披露清单自相矛盾；FIX-355 无任务行/packet | ✗ **未满足** |
| 回滚方案存在且已验证 | = 已验证 | 方案存在；**隔离副本演练已执行且我独立复算关键路径**（82 paths / 锚定三项 / 零污染三重核验当场同值）；真实 tip 面为 M-5 期义务（先例同型） | **✓ 满足**（条件：checklist #18 回填——见 F-15②） |
| CHANGELOG 用户视角完整 | 关键段全覆盖 | Added/Changed/Fixed/B-1~B-6/披露/Breaking=无/MINOR 依据全覆盖 | ✓ |
| breaking changes 已标注 | 100% | 显式「无」+ VERSIONING 逐项反证 | ✓ |
| Feature Flag 关闭验证 | 全部通过 | F-1/F-2 双臂 + I-1~I-5 三层机检 + `behavior_profile.py` 守护测试 | ✓ |
| P0 任务完成 | — | AUDIT-154 + FEAT-032~040 九任务全 ✅（机录 9/9 `APPROVED_WITH_NOTES`/0） | ✓ |
| 版本 bump 完整性 | 全平面 | **F-05 缺口已修复并经 SHA256 逐字节核验**（F-354 归属为 P2 备注） | ✓ |

---

## 10. 审查结论

**NEEDS_CHANGE（round=R1）｜unresolved_blockers=3**

**阻断项 3 项（全部为提交前强制项，均为可确定性收口的账目/门禁面，无一是产品代码缺陷）**：
1. **F-15** 本版新引入门禁失败（`check-archive-integrity` PASS→FAIL + `check-release` 2 issue(s)）+ checklist #18 演练行未回填；
2. **F-16** FIX-355 生产代码变更的 7 面入账缺失（task 行 / packet / EVD / triage / 独立审查 / 门禁面归属 / staged 平面）；
3. **F-17** superseding DEC-203 未落账 + 发布文档引用不存在的 `DEC-213⑧`。

**同批必收（非提交前硬阻断）**：**F-18**（Gate 16 逐条归因未达 0.83.0 先例颗粒度）——不阻挡提交，但属发布文档义务，MUST 与上三项一并收口。

**R0 六阻断项收口结果：已修复 5 项半**——F-01（packet 18 族 FAIL 归零）、F-02（快照新写 + 28c/35 归零）、F-03（隔离副本演练 + 我独立复算）、F-05（逐字节 SHA256 核验 + 投影合同原子）、F-06（EVD-1082/1083 + DEC-213⑥ + plan-tracker 行）；F-04 **技术面已独立验证通过**（我实跑 `unit tests` exit 0 + 全量 0 新增失败），仅余包内记录（P2 F-20）。

**本轮阻断的实质**：**全部为「账目/披露/决策合规」面，无一是已交付代码的缺陷**——
1. **F-15** 本版新引入的门禁失败（归档触发缺口，根因 = FIX-246 行恢复）+ #18 演练行未回填；
2. **F-16** FIX-355 的 7 面入账缺失（含独立审查）；
3. **F-17** superseding DEC-203 未落账 + 发布文档引用不存在的 DEC-213⑧；
4. **F-18** Gate 16 披露颗粒度未达自身引用的 0.83.0 先例（漏 Check 27/30/30c）。

**约束性备注（binding notes）**：
1. **FIX-355 不得**以「已由 DEC-213⑧ 授权」的名义随本版提交；其 Code Review 走链是 DEC-203 为重启该路径设定的**生效条件**，不可由本次发布审查替代（§2.3）。
2. **FIX-246 任务行的恢复动作本身合规**（终态登记、证据在案、DEC-199 WARN 如实保留）——F-15 指向其**副作用处置**，**不得**为消除 FAIL 而回退该任务行（那将退回「任务行遗失」的失真态）。
3. `governance health` 子门 exit=1（21 issues）与 Check 30 由 V2 转 29 closure WARN 属**存量/先例已接受面**，不因本结论要求修复；但 FIX-355 所依赖的语义张力（归档任务豁免 vs DEC-199「如实保留」）**必须在 superseding DEC 中显式裁决**。
4. 本报告**未**采集 R0 未复跑项的历史豁免——本轮 5 项（archguard-ratchet / e2e-check / verify / check-release / release-ledger）中 `verify`/`e2e-check`/`check-release` 已由 V-10 全量实跑覆盖为 PASS；`archguard-ratchet` / `release-ledger`（预提交态 FAIL 属正确观测值）**仍未由我独立复跑**，其申报值按「未独立验证」入账，不得引用为本轮通过背书。
5. `release-ledger` 于 M-5 commit 后 MUST 复跑；tag 后 MUST 复跑 `check-release --lineage-mode released --release-commit <commit>`。
6. **R1 通过前不得推进 M-5**（tag / transition）；`core/releases/0.84.0.json` 保持 `candidate`；33 staged 集在 F-16/F-17 收口前**不得提交**（否则 FIX-355 的生产代码变更将以无审查覆盖形态入库）。

**R2 复审范围（重 spawn 同一 Release Reviewer，注入本报告路径）**：仅需验证 F-15~F-18 的收口实证 + F-19~F-23 的刷新；**MUST 逐条标注「已修复/未修复/新引入」**。

---

*审查方：Release Reviewer Agent（独立复审，只读）｜审查对象：0.84.0 候选（HEAD `b537976` + 33 staged 文件）｜前轮：`review-REL-080-RELEASE-R0`（NEEDS_CHANGE/6）｜结论：**NEEDS_CHANGE / round=R1 / unresolved_blockers=3**｜机录义务：Coordinator 以 `review-record` 持久化本结论（Reviewer 不写治理状态）*
