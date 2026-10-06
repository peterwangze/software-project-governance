# REVIEW-FIX-438-CODE-R0 — FEAT-088 后置债清偿：regen 非掩盖性核实独立审查（CODE）

**Round: R0（首轮）** | Reviewer: Code Reviewer（独立审查；唯一写入 = 本报告文件）| 日期锚：HEAD `e1457a8`（2026-10-06）
审查对象：**未提交工作树 diff**（恰 6 修改文件，`git status --porcelain` 实测 6 行全 `M`、零 untracked、零越界）：①`core/architecture-baseline.json`（R1 anchor 27352→27792 / R2 inventory 47→48〔dsh_doctor import_vw 1→2 sites：L1052+L1205〕/ R4 total 1341→1369〔per-fn `_run_full_engine_checks` 611→620、`cmd_check_cross_references` 14→23、`cmd_check_exploration_channels` 0→10〕/ git_head 元数据）②`infra/contract_matrix/snapshots.json`（cli_dispatch face 98→99 keys / 95→96 handlers / keys 列表 +`check-exploration-channels`，其余三面零漂移）③`infra/registry.py`（`_COMMANDS` 补 dispatch 行 + docstring 98→99 + 域内外 re-census 17/82）④`infra/tests/test_registry.py`（FROZEN_CLI_KEYS 98→99）⑤`infra/tests/test_contract_matrix.py`（FROZEN_CLI_KEY_COUNT 98→99）⑥`infra/tests/test_archguard_ratchet.py`（FACTS_PRINT_TOTAL 1341→1369 + anchor 断言 27352→27792，各附 lineage 注释）。裁定链：DEC-319（立票/追认）→ DEC-320（路径 A：sanctioned regen 抬锚）。

本审查全部关键结论均由**亲跑命令**产出（archguard-ratchet 全文 / 四测试文件全量 / write-guard / 逐 commit numstat 与四点 print census 机证），无「依申报背书」项。

## 总结论：APPROVED_WITH_NOTES

**unresolved_blockers = 0**（P0=0 · P1=0 · P2=0 · P3=4）。核心命题「regen 是事实快照而非放宽遮蔽」由**四面零余量 + R7 committed==fresh + 逐 commit 机证**三角闭环成立；authored-zone exemptions 逐字节零变动；三镜像字面量与本审查独立实测全部对合；registry 行补登语义正确；受影响测试 160/160 绿（77+38+27+18 分项吻合）；零越界。P3×4 均为预存披露或细目采信项，不构成返工条件。

## 逐项核验（验收 ①~⑥）

### ① 非掩盖性 regen 核实（核心）— 通过（独立机证，非依申报）

**(a) R1 主文件锚 27792 = 实测零余量，+440 构成逐 commit numstat 机证**：

| commit | numstat（verify_workflow.py） | 净变化 | 申报 |
|---|---|---|---|
| `638509e` FEAT-088 | +332 / −0 | **+332** | +332 ✓ |
| `641e935` REL-099 | +6 / −6 | **±0** | ±0 ✓ |
| `9a28e4d` FIX-432 | +110 / −2 | **+108** | +108 ✓ |
| `bffeff9` REL-098 | +6 / −6 | **±0** | ±0 ✓ |
| **合计** | | **+440** | 27352+440=**27792** ✓ |

当前工作树实测物理行数（`splitlines`，ReadAllLines 口径）= **27792**，与 `anchor_loc` **恰相等（零余量）**——锚点未预留任何未来增长空间；ratchet R1 PASS `27792 ≤ 27792`。`c00d70c..e1457a8` 区间触碰 verify_workflow.py 的 commit 恰为上表 4 个，无未申报来源。

**(b) R2 反向依赖 inventory 48 与实际位点一致**：baseline JSON 解析实测 inventory 总位点 **48**（37 文件条目）；`dsh_doctor.py` 条目 count=2/lines=[1052,1205]，两行实读均为 `from verify_workflow import …  # noqa: PLC0415 — lazy`（L1205 = FEAT-088 的 `_channel_projection` lazy import，即申报的 BT-R-02 single-verdict projection 新位点；L1050→L1052 漂移由 638509e 对 dsh_doctor.py +69/−2 的净偏移解释，count 语义下合理——`test_r2_line_drift_tolerated` 即此语义）。ratchet R2 PASS `48 ≤ 48 across 37 files`（fresh 扫描 vs committed inventory）。

**(c) R4 print census 1369 四点机证，per-fn 拆分与 lineage 注释逐字对合**（本审查以 `archguard_ratchet.count_print_calls` 对 `git show` 提取的四代 verify_workflow.py 独立 census）：

| revision | total | `_run_full_engine_checks` | `cmd_check_cross_references` | `cmd_check_exploration_channels` |
|---|---|---|---|---|
| `c00d70c`（FEAT-083 基准） | 1341 | 611 | 14 | —（不存在） |
| `9a28e4d`（FIX-432） | 1348（**+7**） | 615（+4） | 17（+3） | — |
| `638509e`（FEAT-088） | 1369（**+21**） | 620（+5） | 23（+6） | 10（0→10 新函数） |
| `e1457a8`（HEAD） | 1369（零漂移） | 620 | 23 | 10 |

→ +28 = FIX-432 +7 + FEAT-088 +21，与 Developer **归因修正后**的 lineage 注释（「FEAT-088 +21: 615→620 / 17→23 / 0→10；FIX-432 +7: 611→615 / 14→17」）**逐字对合**；638509e→e1457a8 之间（da6befd/c967155/FIX-433/434/435）print 面零漂移。当前树 census total=1369 与 baseline `r4_print_orchestration.total` **恰相等**，per_function 全等（`test_r4_committed_per_function_matches_current` 绿）。

**(d) R5 99/99 + 73/73 三方一致**：快照 cli_dispatch face `key_count=99`/`handler_count=96`/keys len=99（列表 sorted=True、含新键）；registry `len(_COMMANDS)=99`（键唯一）；`check_segments.count=73` = registry segments 73 = 两测试文件 FROZEN_SEGMENTS/FROZEN_CHECK_SEGMENT_COUNT 73。ratchet R5 PASS `cli keys 99/99 frozen, segments 73/73 frozen`（该检查消费 FEAT-020 快照并对照引擎 commands dict——**engine ↔ registry ↔ snapshot 三方一致**由此证得）。R6 INFO `cold import 205 (baseline 205, Δ0)`。

**(e) R7 committed==fresh 独立复验**：本审查全文复跑 `archguard-ratchet` → `Result: PASS (0 violations; raw findings before exemptions: 0) — fatal gate green`，其中 **`[R7] PASS regen deterministic=True; committed==fresh True`**——committed 基线与 fresh regen 输出一致，直接排除「手改基线伪装 regen」形态（任何手改数值都会产生 drift 被 R7 抓获）。

### ② authored-zone exemptions 原样保留 — 通过

HEAD↔worktree 的 `exemptions` 段 **JSON 深比较 identical**；且 ratchet 报告 `raw findings before exemptions: 0`——本票 PASS 是**裸通过，零豁免依赖**，不存在「扩容 exemptions 遮蔽 violations」形态。baseline 变化的顶层键恰为 4 个（`generated`/`r1_mainfile_budget`/`r2_reverse_dependency`/`r4_print_orchestration`），与申报面完全一致，无隐藏越界面。

### ③ 三镜像字面量 + lineage 注释忠实 — 通过

四组字面量与本审查独立实测全部对合：`FACTS_PRINT_TOTAL=1369`（=census 实测）、anchor 断言 `27792`（=行数实测）、`FROZEN_CLI_KEY_COUNT=99`/`FROZEN_CLI_KEYS=99`（=快照/registry 实测）。lineage 注释（含 R4 归因修正后表述）逐字对合见 ①(c)；anchor lineage 注释的 +440 拆分（含 FEAT-088 内部 234+8+23+57+10=332 自洽）见 ①(a)——内部分拆细目未逐项机证（F-4 披露）。registry docstring 的历史叙述**精确确证**：本审查对 `344ec8c..HEAD` 各代 registry.py 独立 census 均得 **98 = 17 外 + 81 内**，旧文 "the other 80" 确为 stale（17/80 是 97 键时代数字，FEAT-080 加 demand-source-revise 后未跟新）——新注释「FEAT-080 window repeated the stale-count shape (said 17 outside / 80 monolith at 97 total); re-censused: 17 outside / 82 monolith at 99」与 git 史实逐代吻合，且 99=17+82 机证成立（新键在 monolith 侧：81+1=82）。

### ④ registry.py 行补登语义正确 — 通过

- **dispatch 目标实存**：`("check-exploration-channels", "verify_workflow.cmd_check_exploration_channels")` 的 handler `def cmd_check_exploration_channels` 在 verify_workflow.py 实存（正则命中），引擎内 4 处 `check-exploration-channels` wiring 提及（dispatch/commands dict 由 FEAT-088 `638509e` 落地，非本票引入——verify_workflow.py 不在 6 文件 diff 内，零越界实证）。FEAT-064 同型遗漏形状成立：引擎 dispatch 已在 HEAD、registry 行缺失，本票补登。
- **排序位正确**：新键插入 idx 24，邻位 `check-entry-bootstrap-sync` < `check-exploration-channels` < `check-first-session-measurement`（局部字母序 ✓）。
- **docstring 计数**：98→99 = `len(_COMMANDS)` 实测 ✓；17/82 census 实测 ✓（见 ③）。

### ⑤ 受影响测试全套绿 — 通过（亲跑）

四文件合并实跑 **160 passed（319s，0 failed/0 skipped）**，collect 分项 **77 / 38 / 27 / 18** 与申报逐项吻合（77+38+27+18=160）。含全部负控用例（R1 +1 行 FAIL、R4 双粒度 +1 FAIL、R2 新位点/新文件 FAIL 等——非「只改数字凑绿」的证据面）。

### ⑥ 零越界 — 通过

`git status --porcelain` 恰 6 行 `M`，无 untracked/无暂存残留；baseline JSON 变化面恰 4 顶层键（②）；snapshots 变化面恰 cli_dispatch face + generated 段（diff 实测无其他 hunk，check_segments/guard_output_pin/result_shapes 三面零漂移）。`architecture-health.json` 未触碰。

## 蓝军挑战（已执行）

- **BM-1「抬锚=放宽」攻击面**：若 anchor 抬高超过实际行数即为未来增长开暗门。反证：**四个冻结面全部零余量**（R1 27792/27792、R2 48/48、R4 1369/1369、R5 99/99、73/73——均恰相等），负控用例仍在套件中且绿（任何 +1 立即红）；棘轮 only-down 语义自新锚起算。
- **BM-2 手改基线伪装 regen**：R7 committed==fresh True（本审查独立复跑）+ 关键数值全部本审查独立实测对合（行数/print census/位点数/键数）——双层证据下手改不可行。
- **BM-3 exemptions 暗中扩容**：exemptions 逐字节 identical + raw findings 0——PASS 不依赖任何豁免。
- **BM-4 改测试字面量凑绿**：字面量与本审查先行的独立测量值对合（测量在前、对照在后）；冻结计数镜像的权威源是扫描器/regen 机制而非人手。
- **BM-5 registry 补登破坏 dispatch**：target def 实存 + R5 三方一致 + `test_exploration_channels.py` 18 用例绿（该文件本票未触碰，其行为依赖补登后的注册面）。

## findings 清单

| # | 级别 | 位置 | 问题 | 修复建议 |
|---|------|------|------|---------|
| F-1 | **P3** | infra/registry.py（`_SEGMENT_LOADERS` 段头注释） | 段头注释 `── check declaration: 71 segments → entry dotted path ──` 陈旧（权威面实测 73 段：快照 `check_segments.count=73`、`FROZEN_SEGMENTS=73`）。HEAD 携带、不在本票 diff hunk 内，非本票引入；本票 re-census 了键计数（98→99、17/82）但未顺带同步该段注释。 | 下次触碰 registry.py 时顺手改 71→73；或与 F-2 同批文档清理。非阻塞。 |
| F-2 | **P3** | infra/registry.py `_COMMANDS` | 全表存在 5 处**预存**相邻乱序对（`demand-source-revise`>`check-acceptance-contracts`、`check-dsh-preset-smoke`>`check-dsh-boundary`、`check-injection-contract`>`check-injection-budget`、`dynamic-lifecycle-migration`>`dsh-doctor`、`write-guard-bootstrap`>`web-console`）——均为历史形态，不在本票 diff 内；本票新键插入位局部字母序正确，快照 keys 列表面 sorted=True。dict 语义无行为影响，纯可读性。 | 可选：后续票整表排序 normal化（一次性、零行为差异）。非阻塞。 |
| F-3 | **P3** | 全量套件对账 | Developer「全量 4712 tests 19F→4F」未在本审查独立全量复跑（验收⑤范围外）。已独立验证：四受影响文件 160/160 绿（分项吻合）；同 HEAD 基线上 FIX-435 R0 曾实证 18F 全部 HEAD 同败（含 ratchet/契约/registry 族=本票愈合对象 + contracts×1/预算×3 预存成员），与本票「12→0、5→0、余 4∈披露集」申报相容。 | Coordinator 对账以四文件复绿 + 预存披露集为据即可；如需精确 19→4 演进账，由 Developer 提供三次全量 run 清单（申报已在案）。非阻塞。 |
| F-4 | **P3** | infra/tests/test_archguard_ratchet.py anchor lineage 注释 | FEAT-088 +332 的**内部五项拆分**（guard body +234 at L12142 / Check 12 wiring +8 / engine-check integration +23 / CLI renderers +57 / dispatch +10）与 FIX-432「cmd_gates +76 among others」细目未逐项机证——本审查机证了各 commit 总量与跨 commit 净构成（+332/+108/±0 全对合），细目以注释自洽性采信（234+8+23+57+10=332 ✓）。 | 披露性 finding；细目如需硬证据可由 count_print_calls 式分 hunk census 补做。非阻塞。 |

## 硬门槛自检

- **P0 阻塞问题数 = 0** ✓（findings 表实证：P0=0/P1=0/P2=0/P3=4）
- **5 维度全覆盖 = 100%** ✓——正确性（①(a)~(e) 逐轴机证 + BM-1/BM-2/BM-5）、安全性（无新输入面/无密钥/无注入面；纯基线+表+测试字面量变更；registry 补登走既有 dispatch 机制不新增权限面）、可维护性（lineage 注释高保真含归因修正的诚实追溯；docstring re-census 修复 stale 计数为改善项；F-1/F-2 预存文档债披露）、性能（R6 205/Δ0 advisory；基线工件由既有机制消费零新增运行时开销）、测试覆盖（⑤ 160/160 + 负控用例保留 + per-function ratchet 粒度守护）。
- **每条发现标注级别 = 100%** ✓（F-1~F-4 均带 P 级）
- **设计一致性检查已完成** ✓——DEC-320 路径 A（sanctioned regen 抬锚）的执行形态与裁定一致：regen 与冻结字面量/registry 行同变更落地（all-changes-first 纪律）；FEAT-020 契约面变更路径（regen + registry row + count re-baseline 同 change）与 F-P2-5 先例同构；FEAT-064 同型遗漏补登与 FIX-383 先例同构。
- **AI 代码专项 5 项检查全部完成** ✓——①mock 残留=无（6 文件 diff 零 unittest.mock/MagicMock 引入）；②硬编码返回值=无（冻结计数字面量均有本审查独立实测支撑，属 frozen-count 镜像机制而非凑绿）；③幻觉 API=无（dispatch target `verify_workflow.cmd_check_exploration_channels` 实存 def；无新 import）；④未实现 TODO=无（diff 内零 TODO/FIXME/XXX/HACK）；⑤过度实现=无（+71/−19 最小变更面，恰覆盖 6 文件申报面）。

## 事实依据与未验证项声明

**已验证（本审查亲跑命令/实读）**：`git status --porcelain`（恰 6 M 行）；6 文件全量 diff 逐行 + numstat；verify_workflow.py 物理行数实测 27792；`c00d70c..e1457a8` 逐 commit numstat（+332/±0/+108/±0）；四代 print census（count_print_calls over git show：1341→1348→1369→1369 + per-fn 三函数轨迹）；baseline/snapshots JSON 解析（R2 inventory 48/37 文件、dsh_doctor [1052,1205] 实读两行均 lazy import_vw、r4 per-fn 快照、exemptions 深比较 identical、变化面恰 4 顶层键/1 face）；registry 导入实测（99 键唯一、17/82、新键 idx 24 邻位、target def 正则命中、乱序对 5 处定位）；`344ec8c..HEAD` 五代 registry census（98=17+81，docstring stale 形态确证）；`archguard-ratchet` 全文 PASS 0 violations（R1~R7 逐轴 + raw findings 0）；四测试文件合并 160 passed + collect 分项 77/38/27/18；`governance-write-guard` PASS 0 issues。

**未验证（不作通过依据，如实标注）**：①全量 4712 tests 的 19F→4F 演进账未独立复跑（F-3）——验收⑤四文件已复绿对合；②check-governance「1 issue（28n 预存族）」未复跑——不在验收①~⑥判定面内；③lineage 内部细目拆分未逐项机证（F-4）；④snapshots generated 段 python 3.14.3/win32 环境字段与 timestamp（2026-10-06T05:04:16Z）采信机制生成（R7 deterministic=True 佐证）。

**结论：APPROVED_WITH_NOTES（unresolved_blockers = 0）** —— 建议 Coordinator 机录并通过本票 R0；F-1/F-2（预存文档债）可随手票或另立清理票，F-3/F-4 为披露项入账，均不构成返工条件。
