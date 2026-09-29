# REVIEW-REL-096-RELEASE-R0 — 0.93.0 发布终审（组装 commit 前）

- **Round**: R0（RELEASE 终审首审；组装 commit 未落——本审为 commit 前审）
- **Reviewer**: Release Reviewer（agents/code-reviewer.md 发布审查角色节 + agents/release-reviewer.md + skills/release-review/SKILL.md + skills/stage-release/SKILL.md 收口标准，均已加载；P0~P3 分级）
- **审查对象**: 0.93.0 发布候选 @基线 HEAD=`4f52c6b`；工作树=REL-096 组装 24 文件版本面 delta（未 commit，`git status --porcelain` 亲证 24×M 零未跟踪）
- **先例参照**: review-REL-095-RELEASE-R0（0.92 M-3 RELEASE 半面，AWN/0 有条件 GO）；review-REL-095-CODE-R0
- **审查日期**: 2026-09-29 ｜ **任务**: REL-096（0.93.0 发布终审）
- **结论**: **NEEDS_CHANGE**（P1×3 阻塞——全部为 CHANGELOG 文本级快修，零产品代码返工）+ **GO 判定: GO_WITH_CONDITIONS**（条件 C1~C8 见 §四；无架构级/不可逆缺陷，NO-GO 不成立）
- **复跑协议遵守**: TEMP 重定向 `.governance/tmp/check-run-20260929` ✓；五检限定 ✓（check-release/check-version-consistency/check-projection-sync/check-entry-bootstrap-sync/check-injection-budget）；禁全量 pytest ✓（check-release `--skip-execution-gates`，dsh upgrade regression 面 [SKIP]+WARN 披露在屏）；重试 ≤2 ✓（entry-bootstrap-sync 第 1 次命令引号笔误 exit 1 无输出→第 2 次 PASS；check-release 2 次——第 2 次为 TEMP 变量隔离诊断性重跑，见 §三/重点 3）

---

## 一、八点核验逐项结论

### 重点 1：版本面完备性 — PASS

- **check-version-consistency 亲跑**: `PASSED — all version declarations consistent`（13 文件+bootstrap 双标记，**0 警告**——「警告 9→0 实证复跑」达成）。
- **check-projection-sync 亲跑**: `PASSED`（Source version 0.93.0，Mirrored files checked: 28）。
- **24 文件面清单 vs 权威面对照**: 17 投影面（plugin.json×4/marketplace/package/manifest/SKILL frontmatter/AGENTS×2/CLAUDE.md×2/governance-init×2/cordis.yml/e2e fixture SKILL）+ verify_workflow.py REQUIRED_SNIPPETS 6 pin + version.py 豁免账本 + hooks×4 + CHANGELOG + e2e fixture plan-tracker——与 check-version-consistency 权威面（13 检查文件+双根 bootstrap 标记）零缺口，**无漏面**。
- resolve_entry.py: active_version=0.93.0（skill_frontmatter 权威源）✓；hooks installed 三件齐 ✓。

### 重点 2：CHANGELOG 0.93.0 条目 — PASS（骨架成立）+ P1×2/P1×1/P3×2 findings（见 §二 F-1/F-2/F-3/F-8/F-10）

- **载荷双窗 13 票全列核对 ✓**：DESIGN-021（`130ed19`）/FEAT-077（`f297eeb`）/FEAT-078（`3544d09`）/FEAT-079（`2ef9fc2`）/FEAT-080（`2f3ecd4`+`344ec8c` rider）/FEAT-076（`15e0a6d`）/FIX-405+406（`d22a4f9`）/FIX-407/FIX-408/FIX-409（终窗 `4f52c6b`）/FIX-403（`0ba86ce`）/FIX-404（`f627c57`）——**11 个载荷 commit hash 逐一与 `git log 041c0c4..HEAD` 亲证一致**，审查状态（R0/R1/R1b AWN/0；DESIGN-021 R0 NEEDS_CHANGE→R1 AWN/0）与 commit subject 及 EVD-1260~1264 机录行一致。
- **格式沿用 0.92.0 偏差三处**：①缺 `### Fixed` 段（0.92 M-1 同期形态有 Fixed 段——`git show 40eb6f7:project/CHANGELOG.md` 亲证；本版 7 张 FIX 票用户可见修复未进分类面）→ **F-1/P1**；②日期格预填 `2026-09-29（发布日期占位…）`——0.92 M-1 先例为「未发布（准备态）」+准备态注记「发布日期不预填」，FIX-349 零预填字面口径下 tag 未落地即写日期（若 tag 跨日则误导）→ **F-2/P1**；③「载荷双窗（12 commits 审查链全闭合，R0/R1 全 AWN/0）」——窗口 12 commits 中第 12 个 `90b0b0f` 为 REL-095 M-8 收口 commit（非 0.93 载荷、无 R0/R1 审查链），载荷实为 11 commits/13 票 → **F-8/P3**。
- **三例外终局声明与 DEC-294/295/296 一致 ✓**：EXC-002 关闭=DEC-294(1) ✓；EXC-001 终局=阈值重定标=DEC-295(1) ✓；EXC-003=DEC-296(3) 执行中项经 FIX-407 落地 ✓（EVD-1262「EXC-003 终局（DEC-294(2) 承载）」与 CHANGELOG「DEC-296 记账」为 комиссии/执行双阶段归属——建议补双引用 → **F-10/P3**）。**exceptions.json 亲读: `"exceptions": []`——零例外承载机证 ✓**。
- **已知边界披露诚实性**：decision-log **177,202B** 实测与「259,053→177,202B」逐字一致 ✓；环境残留（`.pytest_cache`+`spg-projection-bghpqx4_`/`spg-projection-lz5mmgx9`）磁盘亲证在盘 ✓；**archive.py 披露 5,508 行为 0.92 时点旧数——实测 5,959 行（274,228B，FIX-407 增量后未复测）→ F-3/P1（no-overclaim 披露精度）**。
- EVD-1240~1264 在盘 ✓（evidence-log L1905~1919 机录行含 schema v1 op 哈希）。

### 重点 3：发布门全链 — FAIL（7 issues，候选态口径）+ 新增子检查首秀核验 PASS

**check-release 亲跑**（`--version 0.93.0 --require-changelog --lineage-mode candidate --skip-execution-gates`，TEMP=仓库外默认值——权威判据）:

| 面 | 结果 |
|---|---|
| version consistency / release fact source / runtime readiness matrix / first session measurement / governance pack / **sd integrity** / agent adapters / projection sync / cross references / archive integrity / release lineage（candidate）/ gate sequence / one-dot-zero blockers / execution gates / loop fuse block / changelog / governance exceptions / **loop runtime claim gate** | 全 PASS |
| **hot fact source** | **FAIL ×3**：session-snapshot 工作流版本 0.92.0≠plan-tracker 0.93.0；plan-tracker 缺 0.93.0 roadmap 行；项目总览缺活跃版本 0.93.0 |
| **provenance release gate** | **FAIL ×1**：载荷任务 FEAT-076 无 demand_source 申报（未标/无 triage 记录）——ADR-021 §2.2.4/§2.4 fail-closed |
| **release docs** | **FAIL ×3**：docs/release/{release-checklist,feature-flags,rollback-plan}-0.93.0.md 缺失 |

- **新增子检查首秀核验 ✓**：provenance 子检查已入发布门面且**真实拦截**——M1 执法面（FEAT-080 接线，commit `2f3ecd4`「release-gate provenance subcheck」）首次发布即拦下本版载荷票 FEAT-076（其需求源仅存在于 plan-tracker 行内叙述「需求源=user-named〔DEC-286(7)〕」，未走结构化 provenance 通道/无 triage 机录）——**fail-closed 机制有效性 debut 自证**；sd integrity [PASS] 入面 ✓（FIX-405 交付）；Check 41/42 经 DEC-292 机检判据（commit `2f3ecd4` 接线+DEC-292 L170 判定记录）验证——**本次未直跑 check-governance（不在五检授权集），标注「经 DEC 机录验证，未独立复跑」**。
- **44 issues 分类裁决复核——未能复现（F-12/P2）**：check-governance 不在授权复跑集；evidence-log/plan-tracker grep 未见「44」分类机录（唯一 28n/28q 族匹配为 0.81 时代 EVD-1063）。**已在授权集内实证的等价判定**：release 门面 7 issues；容量 WARN 域（plan-tracker 204.8KB〔DEC-296(3) 在案〕/evidence-log/archive.py）经 DEC-295 三轨重定标为 advisory 域——check-release 实证未计入 issues（非阻断）✓。
- **与 REL-095 M-2 先例同构性判定**：7 issues 中 hot-fact-source×3+docs×3 为「发布窗记账类」（同 REL-095 M-1/M-2/M-4 链内步骤形态）；provenance×1 为本版新执法面真实缺口。**0.93 零例外口径（exceptions.json 空）→ 无一可例外承载，全部必须修后才放行**；容量 WARN 域=DEC-295 重定标 advisory（非 issue、非例外——机制性收编，非承载）。
- **TEMP 伪影 A/B 实证（F-13/P2，执行规程发现）**：run 1（TEMP=`.governance/tmp/check-run-20260929`，仓库内）loop identity FAIL `ROOT_SOURCE_AMBIGUOUS: snapshot must be outside every scanned root`（attestation 快照落入扫描根）；run 2（TEMP=仓库外默认）同面 **identity_verdict=PASS**（inventory `cf2d0269…`，candidates=1113/parsed=1113/skip=0）。**发布链 M-2 运行时 TEMP 必须在仓库外**，否则产生 loop 门假 FAIL（fail-closed 方向安全，但会污染门禁信号可信度）。

### 重点 4：投影与入口 — PASS（含一项证据缺口）

- **write_then_probe=PASS 首例核验**：机制交付实证=EVD-1264（FIX-409「release-projection 输出 write_then_probe:PASS facts」+审查者独立重做沙箱活体闭环 written:1 精确吻合）；**本版组装面自身的 written=17→幂等复跑 written=0→probe PASS 运行无 evidence-log 机录行**（grep `written=17` 零命中；CHANGELOG L28/L42 声称之）→ **F-4/P2：M-1/M-2 必须补机录 EVD 行**。
- **双根 entry sync ✓**：check-entry-bootstrap-sync PASS——repo-root 与 e2e-fixture 双根 CLAUDE.md=10086B/full、AGENTS.md=2815B/thin 逐字节同形；dsh dialect（FEAT-040）`adapters/dsh/AGENTS.md.template` 3444B/37L 互认在案。
- **17 面幂等**：声称与 write_then_probe 同源——待 F-4 补录后闭合；当前 sync 终态由 check-projection-sync PASS（28 mirrors）背书。

### 重点 5：DEC-213③ 豁免注册逐条核验 — 定性 PASS / 计数差 1（F-9/P3）

version.py STATIC_PIN_EXEMPTIONS 实测 **7 条变更（非 briefing 所称 8=1+7）**：

| # | 文件:行 | 内容 | 定性核验 |
|---|---|---|---|
| 1（stale 重锚） | test_release_projection.py:(30→35, "0.87.0") | `NEW_VERSION = "0.87.0"` | ✓ 行移重锚（FIX-409 sandbox 前置 import 致 +5 行，常量未变）；豁免语义=surfaces-once 历史钉 |
| 2~3（bump-time） | test_provenance_domain.py:323/342 | `_row(…, target_version="0.93.0")` | ✓ `_PAYLOAD={"version":"0.92.0"}`（L296 亲证）——0.93 窗口票所写 then-future 目标场景载荷（显式改期用例/载荷外 machine-signal 用例），真未来值常量 |
| 4~5（bump-time） | test_verify_workflow.py:20038/20056 | TaskDep(...target_version="0.93.0") 及 passthrough 断言 | ✓ FEAT-080 provenance-rows 派生 fixture 场景数据，任意目标值 |
| 6~7（bump-time） | test_verify_workflow.py:20388/20420 | `check_release_readiness(version="0.93.0")` SD 用例×2 | ✓ FIX-405 SD-integrity 就绪测试以 then-future 版本为门参数（FIX-408 hermetic 化重锚，token 未变） |

**全部「未来值 fixture 常量」定性属实**——精确 (line,version) 钉+逐条注释理由+surfaces-exactly-once-at-this-bump 语义，**无伪装绕过**（无限定词的散弹豁免/动态化 token 锚均未出现）。计数差异（7 vs 8）请 Release Agent 核对声称来源。

### 重点 6：披露完备性 — PARTIAL（两项已落实、一项待 M-4 收口）

- 环境残留目录 ✓（CHANGELOG L26 披露+磁盘亲证）；非沙箱复跑建议 ✓ 已机录（EVD-1260「发布验证在非沙箱终端复跑确认」）——**但二者均未进 release-checklist（doc 尚缺）**。
- CLAUDE.md DACL 遗留（takeown 一次性项）：CHANGELOG L28 仅载「SD 受损经 harness 通道字节级复原（10115B）」；takeown/icacls 处置模板在 sd_integrity 机内（FIX-405/409），**一次性人工项未见于任何收口清单** → M-4 checklist MUST 收录（并入 F-7 条件 C4）。

### 重点 7：回滚方案 — NOT YET CODIFIED（M-4 义务）

- rollback-plan-0.93.0.md **缺失**（check-release release docs FAIL 三件之一）。
- 已有口径：plan-tracker L11「回滚=git revert 版本面提交」+ 调度补充「+tag 删除」——方向正确但未成文。
- **fix407-backup 保留语义未定义**：`.governance/tmp/fix407-backup`+`fix407-quarantine` 在盘（EVD-1262 备份 sha256=70F74584… 可复核）——保留窗口/恢复步骤/一致性校验 MUST 写入 rollback plan（含 decision-log 177K 稳态回迁路径）。
- 另建议纳入：`.governance/tmp/check-run-20260929` 残留清理（本次审查 TEMP 工件，gitignored 非 git 面）。

### 重点 8：发布准入判定 — 见 §四（NEEDS_CHANGE + GO_WITH_CONDITIONS）

---

## 二、Findings

| # | 级 | 位置 | 问题 | 修复建议 |
|---|---|---|---|---|
| F-1 | **P1** | project/CHANGELOG.md L34~45 | 缺 `### Fixed` 段——7 张 FIX 票（FIX-403~409）用户可见修复未进分类面；角色硬门槛「CHANGELOG 用户视角完整（新增/变更/修复各段）」未满足；0.92 M-1 同期有 Fixed 段（git show 40eb6f7 亲证） | 补 Fixed 段：FIX-403/404（identity fixture 清理崩溃热修+清理族扫荡 7ERROR→0）/FIX-405+406（SD 完好性门+谓词统一）/FIX-407（decision-log 259K→177K narrative 迁移）/FIX-408（SD 测试 hermetic+归因勘误）/FIX-409（投影 writer ACL 三层根修+write-then-probe） |
| F-2 | **P1** | project/CHANGELOG.md L5~6 | 日期格预填 `2026-09-29`——违反 FIX-349「零预填」字面口径；偏离 0.92 M-1 先例（「未发布（准备态）」+准备态注记「发布日期不预填」）；tag 跨日即误导 | 日期格改「未发布（准备态）」（保留 L6 占位注释）+补准备态注记段（0.92 先例原文形态）；M-7 后按 taggerdate 权威回填 |
| F-3 | **P1** | project/CHANGELOG.md L26 | archive.py 披露 5,508 行=0.92 时点旧数；实测 **5,959 行**（274,228B，FIX-407 增量 +451 未复测）——no-overclaim 披露精度 | 复测后改「5,959 行越阈 5,000（0.94 拆分候选）」 |
| F-4 | P2 | evidence-log（缺行） | REL-096 组装面投影再生（written=17→幂等 0→write_then_probe=PASS）无机录 EVD 行；CHANGELOG L28/L42 声称无证据承载 | M-1/M-2 补机录 EVD（命令+输出快照） |
| F-5 | P2 | plan-tracker FEAT-076 行（L86） | provenance release gate FAIL：FEAT-076 无结构化 demand_source 申报（行内叙述不算 triage 机录）——新 M1 门 debut 真实拦截 | 走 change-triage intake/demand-revision 通道补报（user-named〔DEC-286(7)〕已在行内，补机录即可）；零例外口径禁豁免 |
| F-6 | P2 | .governance/session-snapshot.md + plan-tracker | hot fact source ×3：snapshot 版本 0.92.0 滞后；roadmap 缺 0.93.0 行；项目总览活跃版本缺 0.93.0 | 发布链记账步骤（M-2 前完成） |
| F-7 | P2 | docs/release/*-0.93.0.md（缺） | release docs 三件缺失（checklist/feature-flags/rollback-plan）；CLAUDE.md DACL takeown 一次性项/非沙箱复跑建议/环境残留清理均待收录；fix407-backup 保留语义未成文 | M-4 四件套落盘（release-plan 按 REL-095 先例同产）；内容要求见条件 C4 |
| F-8 | P3 | project/CHANGELOG.md L12 | 「12 commits 审查链全闭合 R0/R1 全 AWN/0」含 `90b0b0f`（REL-095 M-8 收口，非载荷无 R0/R1）——计数口径不精确（载荷=11 commits/13 票） | 改「载荷 11 commits/13 票（窗口 12 含前版收口 1）」或加注 |
| F-9 | P3 | version.py STATIC_PIN_EXEMPTIONS | 豁免计数：briefing 称 8（1+7），文件实际 7（1+6）——定性全对、计数差 1 | 核对声称来源；如另有第 8 条意图落点需补 |
| F-10 | P3 | project/CHANGELOG.md L10 | EXC-003 终局归属：CHANGELOG「DEC-296 记账」vs EVD-1262「DEC-294(2) 承载」（ commissions/执行两阶段） | 补双引用「DEC-294(2) 承载→DEC-296(3) 池记账→FIX-407 执行」 |
| F-11 | P3 | docs/reviews/ | FIX-408 无独立审查报告文件（承载=review-FIX-409-CODE-R0 §0 勘误节+EVD-1263）；FIX-405 R1b 为 R1 报告内 §R1b 节——形态可接受（0.92 先例：FIX-405+406 共报告）但建议 Coordinator 经 check-governance Check 30 确认机录链完整（超出本次授权复跑集） | M-2 门禁时确认 Check 30 绿 |
| F-12 | P2 | （分类记录缺位） | 「44 issues（28n/28q/28c/18f/17/28s）」分类未能在授权复跑集内复现，evidence-log/plan-tracker 无机录出处 | Release Agent 提供机录出处（命令输出/EVD 行）或申请授权补跑 check-governance 复核；已实证等价面=release 门 7 issues 全分类 |
| F-13 | P2 | （执行规程） | TEMP 重定向入仓库 → loop identity attestation 假 FAIL（A/B 实证：TEMP 内 FAIL/TEMP 外 PASS，`loop_runtime_claim_attestation.py` L1006~1011 快照必须位于全部扫描根外） | 发布链 M-2 起 TEMP 置仓库外；建议将此边界写入 release-checklist 运行前提；清理 `.governance/tmp/check-run-20260929` |

**计数**: P0=0 / **P1=3** / P2=5 / P3=4。P1×3 全部为 CHANGELOG 文本级快修（预计 <30 分钟），零产品代码变更。

---

## 三、命令与证据留痕

| 检查 | 命令 | 结果 |
|---|---|---|
| resolve_entry | `python …/infra/resolve_entry.py --json` | resolved_root_ok=true, active_version=0.93.0 |
| check-version-consistency | verify_workflow.py check-version-consistency | PASSED（0 警告——9→0 实证） |
| check-projection-sync | verify_workflow.py check-projection-sync | PASSED（28 mirrors） |
| check-entry-bootstrap-sync | 同上（retry 1 次修正命令引号） | PASSED（双根 10086B/2815B 同形） |
| check-injection-budget | verify_workflow.py check-injection-budget | PASSED（resident 4207≤6000；M1 worst 171≤180 own-line；M1+M2 342≤370 hard；三 tier 全 ok；FEAT-079 契约档在屏） |
| check-release | `--version 0.93.0 --require-changelog --lineage-mode candidate --skip-execution-gates` | **FAILED — 7 issue(s)**（run1=8 含 TEMP 伪影 loop identity；run2 权威=7：hot fact source×3/provenance×1/release docs×3） |
| git log | `041c0c4..HEAD` | 12 commits（11 载荷+90b0b0f 前版收口）；rev-list count=12 |
| 磁盘实测 | archive.py 5,959 行/274,228B；decision-log 177,202B；CLAUDE.md 10,115B；.pytest_cache+spg-projection-×2 在盘；exceptions.json 空 | 与披露对照见重点 2 |
| 治理记录 | DEC-292~296（decision-log L170~174）/EVD-1260~1264（evidence-log L1905~1919）/review 报告 14 份（docs/reviews glob） | 全在盘 |

---

## 四、发布准入判定

**结论: NEEDS_CHANGE**（P1×3 阻塞于审查对象本体——commit 前修复成本最低点；Coordinator 按复审必达返工后重 spawn 同一 Reviewer R1，注入本报告路径）。

**GO 判定: GO_WITH_CONDITIONS** —— 版本面 delta 本身健全（四检查 PASS/零警告、零例外承载机证、决策链证据链全在盘、豁免定性全真），P1 全为文本快修，无 NO-GO 因子。放行条件（全部满足后方可 M-5a candidate manifest）：

- **C1（commit 前）**: 修复 F-1/F-2/F-3（CHANGELOG 三处）→ R1 复审确认。
- **C2**: FEAT-076 补结构化 demand_source 申报（F-5），provenance release gate 转 PASS——零例外口径下不得豁免。
- **C3**: hot fact source 三面翻新（F-6：snapshot 版本/roadmap 行/项目总览）。
- **C4**: M-4 四件套落盘（F-7）：checklist MUST 收录 CLAUDE.md DACL takeown 一次性项+非沙箱复跑建议（EVD-1260）+环境残留清理（.pytest_cache/spg-projection-×2/.governance/tmp/check-run-20260929）；rollback-plan MUST 含 git revert 版本面提交+tag 删除路径+fix407-backup 保留语义（sha256=70F74584…，含保留窗口与回迁校验）。
- **C5**: 组装面投影再生机录 EVD 补录（F-4：written=17→0→write_then_probe=PASS）。
- **C6**: 「44 issues」分类补机录出处或授权补跑复核（F-12）。
- **C7**: M-2 起发布门复跑 TEMP 必须在仓库外（F-13 A/B 实证）。
- **C8**: R1 复审通过（APPROVED 或 unresolved_blockers=0 的 APPROVED_WITH_NOTES）后按 REL-095 同构链推进 M-4→M-5a/b→M-6 ledger→M-7 tag（taggerdate 权威回填 CHANGELOG 日期格）→M-8 收口。

— REVIEW-REL-096-RELEASE-R0 完（Release Reviewer，2026-09-29）
