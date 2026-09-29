# REVIEW-REL-096-RELEASE-R1 — 0.93.0 发布终审复审（R0 NEEDS_CHANGE 处置核验）

- **Round**: R1（同一 Release Reviewer 复审；前轮引用: `docs/reviews/review-REL-096-RELEASE-R0.md`〔NEEDS_CHANGE，P1×3/P2×5/P3×4，条件 C1~C8〕——本报告头部逐条比对前轮 findings，标注 已修复/未修复/新引入）
- **Reviewer**: Release Reviewer（角色定义+release-review/stage-release SKILL 沿用 R0 加载态）
- **审查对象**: 0.93.0 发布候选 @基线 HEAD=`4f52c6b`（未变）；工作树=24 文件版本面 delta + **3 staged 发布三件套（A）** + CHANGELOG 41→53 行（C1 修复）——`git status --porcelain` 亲证 24×M+3×A+R0/R1 报告未跟踪
- **审查日期**: 2026-09-29 ｜ **任务**: REL-096 R1（C1~C8 处置核验+门复跑+裁量点）
- **结论**: **APPROVED_WITH_NOTES（unresolved_blockers=0）** — 非阻塞备注 R1-N1~N5（P3×4 未修+P3×1 新引入，零阻塞）
- **GO 判定: GO_WITH_CONDITIONS**（条件=tag 前非沙箱完整口径门——见 §四；与 REL-095 R3「AWN/0 有条件 GO」同构）
- **复跑协议**: TEMP=仓库外默认（F-13/C7 纪律——loop identity PASS 实证生效）；五检限定沿用 ✓；禁全量 pytest ✓（--skip-execution-gates）；重试 ≤2 ✓（本轮五检各 1 次全过，零重试消耗）

---

## 一、前轮→本轮处置核对表（复审纪律 (1)：逐条比对）

### R0 条件 C1~C8

| 条件 | 处置状态 | 核验证据 |
|---|---|---|
| **C1a（F-1 缺 Fixed 段）** | ✅ **已修复** | CHANGELOG L46~54 `### Fixed` 段 7 票全覆盖（FIX-403/404/405/406/407/408/409 各一 bullet，内容与 commit subject/EVD-1260~1264 一致；0.92 先例格式沿用）。微瑕：L48「onesc」拼写（见 R1-N4） |
| **C1b（F-2 日期格预填）** | ✅ **已修复** | L5=`## [0.93.0] - 未发布（准备态）`（0.92 M-1 先例同构）+L6 占位注释保留+L56 准备态注记（「发布日期不预填…taggerdate 权威落字…发布链 M-2+ 补记」——先例原文形态） |
| **C1c（F-3 archive.py 旧数）** | ✅ **已修复** | L26=`archive.py 5,959 行/274,228B（实测 2026-09-29 组装时点）越阈 5,000`——与 R0 实测逐字一致 |
| **C2（F-5 FEAT-076 provenance）** | ✅ **已修复（机证）** | evidence-log L1925 TRIAGE-FEAT-076 机录行（change-triage CLI 写入，demand_source=用户点名〔=user-named〕，快照 change-triage/FEAT-076.json）；**check-release 复跑 `provenance release gate` [PASS]**——R0 唯一真实执法缺口闭合 |
| **C3（F-6 热事实三面）** | ✅ **已修复（机证）** | check-release `hot fact source` [PASS]+`[OK] hot fact-source consistency synchronized`；session-snapshot 版本戳亲证=`0.93.0（准备态——REL-096 组装中，tag 未打…）` |
| **C4（F-7 发布三件套+收口项）** | ✅ **已修复** | 三件 staged（git A 状态亲证）+check-release `release docs` [PASS]；内容核验：checklist §发布收口一次性项三件全收录（①takeown/icacls ②残留目录清理 ③非沙箱三类验证）；rollback-plan 含回滚三序+fix407-backup 保留语义（结账前禁删）+sha256 全锚+tag 误推 DEC 纪律+hotfix 0.93.1 路径；feature-flags B-16~B-20 非旗标行为面每项含回滚（补齐 0.92「行为变更」披露面） |
| **C5（F-4 EVD 机录）** | ✅ **已修复** | evidence-log L1926 EVD-1265 机录行（written=17→幂等 0→write_then_probe=PASS+sd_integrity 28 面 0 拒读+双根 sync PASS；governance-store op-5680214e…/schema v1） |
| **C6（F-12 44 分类出处）** | ⚠️ **未提供——降级处置** | Coordinator 未附 44 分类机录出处；但权威门面 check-release 本轮 **PASSED 0 issues**（R0 已实证等价面=7 issues 全分类且全清）→ 降级为 M-8 收口记录项（R1-N3）：发布终账附当时 check-governance 输出快照 |
| **C7（F-13 TEMP 纪律）** | ✅ **已采纳（机证）** | 本轮 TEMP=仓库外默认→loop 门 `identity_verdict=PASS`（inventory 85c55aae…/candidates 1117/parsed 1117/skip 0——较 R0 +4 为 TRIAGE/EVD-1265 机录行自然增长）；fix407-backup 随迁 `C:\Users\peter\AppData\Local\Temp\dsh-edmOzF\rel096-gov-backup\fix407-backup\`，**decision-log.md sha256=70f7458446f82cdef05f7123695a50a3e067729fcdd0869cd1f84365d7ebe217 与 rollback-plan L20 引用逐字一致（Get-FileHash 亲证）**，旧 `.governance/tmp/fix407-backup` 已迁走不留副本；checklist 未显式收录 TEMP 边界（R1-N5 附注） |
| **C8（R1 复审本审）** | ✅ **达成** | 本报告即产物——AWM 形态（unresolved_blockers=0） |

### R0 findings P3 未修项（非阻塞，如实登记）

| # | 状态 | 说明 |
|---|---|---|
| F-8（12 commits 口径） | ❌ 未修复 | CHANGELOG L12 原样「12 commits 审查链全闭合 R0/R1 全 AWN/0」（含 90b0b0f 前版收口）；checklist L26 同口径复制 |
| F-9（豁免计数 8 vs 7） | ❌ 未修复+扩散 | checklist L27「DEC-213③ 豁免 8 条 bump-time 注册」——version.py 实测 7 条（1 重锚+6 bump-time，R0 逐行定性全真） |
| F-10（EXC-003 双引用） | ❌ 未修复 | CHANGELOG L10 仍单引「DEC-296 记账」（EVD-1262=DEC-294(2) 承载） |
| F-11（Check 30 机录确认） | ➖ 并入条件 | 非沙箱 check-governance strict 复跑天然覆盖（条件 G-1） |
| F-13 残留清理 | ➖ 部分 | `.governance/tmp/check-run-20260929`（R0 审查工件，gitignored）未入 checklist 清理项 |

### R1 新发现（复审纪律 (1)「新引入」标注）

| # | 级 | 位置 | 问题 | 建议 |
|---|---|---|---|---|
| R1-F-14 | P3 | CHANGELOG L48 | 「Py3.14 **onesc** 转义」拼写漂移——代码 grep 亲证 6 处全为 `onexc`（tempfile 清理回调，commit `0ba86ce` 原文同）——C1 修复时引入 | tag 前顺手改 onexc（单字） |
| R1-F-15 | P3 | rollback-plan L20 | fix407-backup 唯一副本位于易失路径（`Temp\dsh-edmOzF\` 会话 spill 形态目录；Temp 清理/会话生命周期可能先于发布结账）——序①回滚依赖此备份 | tag 前复制一份至持久位置（如 `.governance/backups/fix407-rel096/`，gitignored）并在 rollback-plan 补双锚引用 |

**R1 计数**: P0=0 / P1=0 / P2=0 / P3=5（4 未修+1 新引入）——**零阻塞**。

---

## 二、门面复跑终态（五检，TEMP=仓库外）

| 检查 | R0 | **R1** |
|---|---|---|
| check-release（candidate+skip-execution-gates） | FAILED 7 issues | **PASSED — release readiness checks are green（0 issues，EXIT=0）**：hot fact source ✅/provenance ✅/release docs ✅ 三失败面全清；sd integrity/loop 门（identity PASS）/changelog/governance exceptions/archive integrity/cross references/one-dot-zero blockers/gate sequence 全 PASS；[SKIP] dsh upgrade regression=WARN 披露（skip 语义正确） |
| check-version-consistency | PASSED（0 警告） | **PASSED（0 警告——无回归）** |
| check-projection-sync | PASSED（28 面） | **PASSED（28 面——无回归）** |
| check-entry-bootstrap-sync | PASSED（双根） | **PASSED（双根 10086B/2815B——无回归）** |
| check-injection-budget | PASSED | **PASSED（resident 4207≤6000；M1 worst 171≤180 own-line；M1+M2 342≤370 hard；三 tier 全 ok——与 R0 逐字节同形）** |

---

## 三、裁量点裁决（briefing 问题：PENDING 披露态+checklist 承诺可 GO（单用户） vs GO_WITH_CONDITIONS（tag 前非沙箱门复跑））

**裁决: GO_WITH_CONDITIONS——条件=tag 前非沙箱完整口径门复跑。** 理由：

1. **收口标准本体（非可选披露项）**：stage-release SKILL 退出条件明文——候选态 `check-release --require-changelog` PASS 与 tag 后 released 态复跑 PASS **默认包含 verify、check-governance --fail-on-issues、e2e-check、unittest**。本审两轮均带 `--skip-execution-gates`（「禁全量 pytest」授权约束）——即**完整口径发布门（全量 unittest+e2e+check-governance）尚未跑过任何一次**。沙箱结构性限制（mkdtemp-0700 受限令牌写拒——FIX-403 契约设计的 never-crash→PENDING 降级态，非崩溃）使其在本会话不可执行，但 SKILL 门不因环境降格（华为 IPD 映射：发布门控逐项检查不可跳过）。
2. **先例同构**：REL-095 M-2 门禁=全量 pytest 4359P/0F/1S 双源（发布链内非沙箱跑）；EVD-1260 先例「发布验证在非沙箱终端复跑确认」。
3. **checklist §3 时序需前移一项**：其标注「（发布后验证）」——①check-governance --summary-only --level strict 与 ②unittest discover 全席应在 **tag 前**（M-2 位）非沙箱跑；③check-release released 态天然在 tag 后。单用户场景不豁免（用户=Single-Threaded Owner，门=SKILL 硬约束；「单用户」降低的是通知/灰度面成本，不是验证面标准）。
4. **「身份证明 PENDING」（builder mkdtemp-0700 写拒）**：属 M-5a/M-6 链步骤同源沙箱限——M-6 ledger 双 PASS（本地+remote）本就必须非沙箱执行，链内自然消化；本报告将其登记为已知降级披露（非新条件）。

---

## 四、发布准入判定

**结论: APPROVED_WITH_NOTES（unresolved_blockers=0）**——五检全绿、C1~C5/C7 全闭合（机证）、零 P1/P2、载荷链 13 票审查链全闭合、零例外承载（exceptions.json 空）、决策链 DEC-286~296 与 EVD-1240~1265 全在盘。非阻塞备注：R1-N1（F-8 口径）/R1-N2（F-9 豁免计数 8→7）/R1-N3（F-12→M-8 记录项）/R1-N4（F-14 onexc 拼写）/R1-N5（F-15 备份持久化+check-run-20260929 清理+TEMP 边界入 checklist 运行前提）。

**GO 判定: GO_WITH_CONDITIONS**——放行条件（tag/M-5a 前全部满足）：

- **G-1（tag 前非沙箱完整门）**: 普通终端执行 ①`python -m unittest discover`（全席——沙箱已知环境性 ERROR 面〔tempfile onexc 清理族〕应全绿）②`check-governance --summary-only --level strict`（全量，含 Check 30 复审链/Check 41/42 机检面——同时闭合 F-11 与 F-12 的 44 分类记录义务）③候选态完整口径 `check-release --version 0.93.0 --require-changelog --lineage-mode candidate`（不带 skip）。任一 FAIL → fail-closed 回审。
- **G-2（M-5a/M-6 非沙箱）**: candidate manifest 创建+ledger 双 PASS（本地+remote）在非沙箱终端（builder mkdtemp-0700 写拒为沙箱已知降级态）。
- **G-3（tag 前 P3 顺手修，可选但推荐）**: onexc 拼写/豁免计数 7 条口径/EXC-003 双引用/fix407-backup 持久化双锚。
- **G-4（tag 后）**: released 态复跑（--lineage-mode released --release-commit <tip>）+CHANGELOG 日期格 taggerdate 权威回填+M-8 收口（终账含 check-governance 快照+DEC-296 池清空声明核验+fix407-backup 结账后清理）。
- **G-5**: 全程 TEMP=仓库外（C7 纪律——checklist 运行前提补录）。

— REVIEW-REL-096-RELEASE-R1 完（Release Reviewer，2026-09-29；前轮 R0 引用闭环）
