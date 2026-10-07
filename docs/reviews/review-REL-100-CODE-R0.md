# Code Review 报告 — REL-100-M3a（0.96.0 版本面 bump + DEC-325 预算重定标 + M-0 四件套定向审查）

- **Round**: R0（Code Reviewer，首次审查）
- **发布链步**: REL-100 M-3a（0.95.0 先例 REL-099-M3a 同构，审查面扩 DEC-325 重定标定向面）
- **审查对象**: 未 commit 工作树改动（`git status` = 27 tracked modified + 4 untracked）+ M-0 四件套新件
- **审查人工具面**: Read/Grep/Glob + 只读 verify 命令（唯一写面 = 本报告；未修改任何被审文件）
- **日期**: 2026-10-07

---

## 总结论：APPROVED_WITH_NOTES

**unresolved_blockers = 0**

- findings 计数：**P1=0 / P2=1 / P3=5**
- 版本面：check-version-consistency 独立复跑 **PASSED @0.96.0**（13 处声明 + bootstrap markers）；引擎锚 diff **恰 6 行**（唯一 hunk `@@ -1055,22 +1055,22 @@`，零夹带）；projection-sync（28 mirrors）/ entry-bootstrap-sync（双根）只读复跑双 PASS；四目录 0.95.0 残留扫描零命中。
- DEC-325 重定标：4 文件 diff 逐 hunk 清点 = 纯门限同步（6000→6200 字面量 + 注释），三处历史记录（L20179 实测 6083 / baseline_metadata L52·L72·L710 EVD-1104 登记）保留未动；strict 6059≤6200 与 lightweight 4303≤6200 双复跑 PASS；DEC-325 涉及的两族测试 35 passed（f=2→0 独立证实）。
- 四件套：§1.1 七票哈希与 `git log` 逐一对上；§2.2 六锚 + CHANGELOG EVD 引用区间（1328/1331~1341）全实存；CHANGELOG 决策链 DEC-318~324 与 decision-log L185~191 逐条对上；archguard-ratchet fatal gate green 独立复跑 PASS 0 violations。
- 回归绿：test_static_version_pins **25 passed**（预期值）；加测 test_baseline_metadata 72 passed+49 subtests。

---

## 一、审查范围（变更集清点）

`git status --short` / `git diff --stat`（本审查实跑）= **27 tracked modified（81 insertions / 43 deletions）+ 4 untracked**，分三组与任务声明逐一吻合：

| 组 | 文件 | 判定 |
|---|------|------|
| 版本面（M-1） | SKILL.md frontmatter、core/manifest.json、marketplace.json、4×plugin.json、package.json、4×hooks、adapters/dsh/AGENTS.md.template、agent-presets 模板、commands/governance-init.md（3 标记）、根 AGENTS.md、e2e 5 件（.governance/plan-tracker fixture/AGENTS/CLAUDE/governance-init/SKILL）、verify_workflow.py 六针脚 | ✅ 与「release-projection written=17 + 双根 entry + 引擎锚」声明一致（EVD-1343 机录 written=17/probe PASS/sd_integrity 28/0） |
| DEC-325 重定标（M-2） | checks/injection_budget.py、tests/test_baseline_metadata.py、tests/test_verify_workflow.py、infra/TOOLS.md | ✅ 恰 4 文件，逐 hunk 见 §三 |
| M-0 四件套 | project/CHANGELOG.md（+35 行 0.96.0 段）+ untracked：m-0-assembly / release-checklist / rollback-plan / feature-flags（0.96.0.md 四件） | ✅ 全实存（EVD-1342 机录） |

边界：`.governance/`（gitignored）不在 diff 内——真台账 L11 已由 Coordinator 更新为 0.96.0 组装中态（实读），属 Coordinator 面、非本审查对象。根 CLAUDE.md（gitignored 狗粮实例）工作树 @0.96.0（注入面实证 + entry-sync PASS）。

---

## 二、逐维核验（A~E）

### A. 版本面一致性 ✅

| # | 检查 | 事实锚（本审查独立复跑/实读） | 判定 |
|---|------|------|------|
| A1 | `check-version-consistency` | **PASSED — all version declarations consistent**（Files checked: 13 + bootstrap markers；Source of truth: SKILL.md） | ✅ 预期 PASSED @0.96.0 达成 |
| A2 | 六针脚恰 6 行 | `git diff verify_workflow.py` 唯一 hunk `@@ -1055,22 +1055,22 @@`：.claude-plugin/plugin.json / marketplace.json / .codex / .zcode / package.json / manifest.json 六面 `"0.95.0"→"0.96.0"`；`git diff --stat` 该文件恰 12 marks（6+/6−）；**无其他改动混入** | ✅ |
| A3 | 权威源 | SKILL.md L3 `version: 0.96.0`（实读） | ✅ |
| A4 | 投影/entry 同步 | `check-projection-sync`：**PASSED — 28 mirrored files @0.96.0**；`check-entry-bootstrap-sync`：**PASSED — 双根 synchronized**（repo-root 与 e2e-fixture 均 CLAUDE.md 10237B/full + AGENTS.md 2815B/thin；dsh 方言模板 3633B/37L 互认） | ✅ 只读复跑 |
| A5 | 残留扫描 | `0\.95\.0` grep：adapters/ **0 命中**、agent-presets/ **0**、commands/ **0**、project/e2e-test-project/ **0**；根 AGENTS.md/CLAUDE.md @0.96.0（注入面+entry-sync）；infra/tests 内 0.94.0/0.95.0 token 为豁免台账/夹具设计内保留（version.py L361-362/L371-373） | ✅ 无漏 bump |
| A6 | M-1 机录对账 | EVD-1343：written=17 / write_then_probe=PASS / sd_integrity 28 scanned/0 unreadable / 幂等复跑 PASS@0.96.0 / STATIC_PIN_EXEMPTIONS **无需新增**（25 passed，零未豁免 pin） | ✅（见 F-1 措辞差） |

### B. 重定标面纯粹性（D4——仅门限同步）✅

**逐 hunk 清点（4 文件全部 hunk 枚举，无遗漏面）**：

| 文件 | hunk | 内容 | 判定 |
|------|------|------|------|
| checks/injection_budget.py | L74-81 | `INJECTION_BUDGET_TOKENS = 6000→6200` + 新增 3 行 DEC-325 注释（6000→6200 重定标缘由：0.95.0 零余量压线 + 六票 +59 tok 漂移——rescale, not shrink；保留 EVD-1104 语义句） | ✅ 声明面内（L78 常量+注释） |
| 同上 | L216-219 | BC-1 条款行独立性注释 `6000-token resident`→`6200-token resident` | ✅ 注释同步 |
| tests/test_baseline_metadata.py | L69/L570/L613/L685/L771 | **5 处**分母字面量 `INJECTION_BUDGET_TOKENS=6000→6200`（fixture kwargs/CLI arg/digest arg/registry arg/dispatch） | ✅ 恰 5 处 |
| tests/test_verify_workflow.py | L21270 / L23172 | docstring `6200-token resident ceiling` + 断言 `INJECTION_BUDGET_TOKENS == 6200` | ✅ 恰 2 处（L23172 断言+L21270 docstring） |
| infra/TOOLS.md | L60 / L591 | TOOL-055 行「默认预算 6000→6200 tok」+ 预算与裁决节「默认 6000→6200」 | ✅ 恰 2 处；两行内 EVD-1104 历史数字（4,216/5,694/5,966、≤6,000）原样保留 |

**历史记录保留核验（应保留未动）**：

| 历史锚 | 实读 | 判定 |
|--------|------|------|
| test_verify_workflow.py L20179 | "measured 6083 > 6000 during this task"（FEAT-079 B1a 期实测——不在 diff 中） | ✅ 未动 |
| test_baseline_metadata.py L52 | docstring "injection-budget 6,000 gate, baseline EVD-1104 (4,216/5,694/5,966, measured 2026-09-19" | ✅ 未动 |
| test_baseline_metadata.py L67-68/L72 | numerator（EVD-1104 canonical 重测三值）+ threshold_basis「≤6,000 出货姿态」 | ✅ 未动（diff 上下文行） |
| test_baseline_metadata.py L710 | "存量登记演示面：injection-budget 6,000 门（EVD-1104）dry-run 素材" | ✅ 未动 |
| TOOLS.md 两行内 EVD-1104 段 | 「三 profile 4,216/5,694/5,966 全 ≤6,000」 | ✅ 未动 |

**门禁复跑（本审查独立执行）**：

| 命令 | 结果 | 判定 |
|------|------|------|
| `check-injection-budget --profile strict --fail-on-issues` | **PASSED — resident 6059 tok ≤ budget 6200**（gated over: none；contract tiers m1/m2 active、combined M1+M2 342 ≤ 370 hard PASS；R8289…各面 ok） | ✅ 预期 6059≤6200 精确命中 |
| `check-injection-budget`（默认 lightweight） | **PASSED — resident 4303 tok ≤ 6200** | ✅ 与 DEC-325「4244+59=4303 同源增量」算术吻合、不回归 |
| DEC-325 涉及两族测试 | `pytest -k "Feat039InjectionBudgetTests or ContractTierBudgetTests"`：**35 passed**（+2 subtests） | ✅ M-2 前 f=2 面独立证实归零 |
| 在账性 | decision-log L192 DEC-325（用户 AskUserQuestion GO 终审「预算重定标 6200」）；evidence-log L2050 EVD-1344（M-2 定谳+全绿收敛）；agent-locks.json DEC-325 锁注记 4 条 | ✅ |

**纯粹性结论**：DEC-325 改动面 = 门限常量 + 同步字面量 + 注释，三处历史登记全保留，无数值外逻辑改动、无 `BUDGET_TIER_POLICY` 变更（M1+M2 370 hard 独立不动——DEC-325 明示且复跑证实 342 仍在线内）。**D4 达成 ✅**。

### C. 四件套事实核验（P1 抽查三处 + 扩展）✅

**抽查 1——m-0 §1.1 七票哈希 vs `git log --oneline -12`（本审查实跑）**：

| 票 | m-0 §1.1 声明 | git log 实测 | 判定 |
|----|--------------|--------------|------|
| FIX-435 | `e1457a8` | `e1457a8 FIX-435: B16 债务本金偿还…` | ✅ |
| FIX-436 | `c442e07` | `c442e07 FIX-436: DEC-316/317 sweep 收尾批…` | ✅ |
| FIX-437 | 治理终态（快速通道免产品 commit） | git log 无 FIX-437 产品 commit | ✅ 自洽（.governance 面） |
| FIX-438 | `f1a47fd` | `f1a47fd FIX-438: FEAT-088 后置债清偿…` | ✅ |
| FIX-439 | `f884829` | `f884829 FIX-439: 外部宿主 incident 缺陷族根治…` | ✅ |
| FIX-440 | `1a56797` | `1a56797 FIX-440: FIX-439 R0 F-1 承接…` | ✅ |
| FIX-441 | `36ff0be` | `36ff0be FIX-441: DEC-324 路径 A sanctioned regen rider…`（HEAD） | ✅ |

**抽查 2——m-0 §2.2 还债栏锚 vs evidence-log 实存**：EVD-1331（L2015）/ EVD-1332（L2018）/ EVD-1334（L2026）/ EVD-1336（L2032）/ EVD-1338（L2038）/ EVD-1340（L2044）**全部实存**，且各 EVD 行内容与 §2.2 还债项描述（4241→1697 拆分、anchor 27352→27792→27866 两跳、sweep 五子项、incident 三缺陷族、卫生登记两子项）逐项可对。**扩展**：§1.1 其余锚 EVD-1328（L2002）/1333（L2021）+ CHANGELOG 引用区间 EVD-1329/1330/1335/1337/1339/1341 亦全实存——「EVD-1328/1331~1341」区间声明**零空心引用** ✅。

**抽查 3——CHANGELOG 决策链 DEC-318~324 vs decision-log**：L185~L191 七条全在，且 CHANGELOG 短标签与 DEC 正文对得上（318 候选批组建 / 319·320 FIX-438 立票与路径 A / 321 Check 30c 豁免清单预登记 / 322 FIX-436 F-B3·F-C1 归属 / 323 FIX-439 紧急插入拆票 / 324 FIX-441 rider 路径 A）；DEC-325（L192）在账 ✅。

**扩展核验**：审查链工件——7 份报告文件实存（review-FIX-435-CODE-R0/R1、436/438/439/440/441-CODE-R0）；REVIEW-FIX-441-R0 机录行（evidence-log L2043：APPROVED_WITH_NOTES / unresolved_blockers=0）实读 ✅。m-0 §3.5「archguard-ratchet PASS 0 violations / fatal gate green」——本审查独立复跑：**R1 27866≤27866 / R2 48≤48 / R4 1371≤1371 / R5 99+73 frozen / R7 committed==fresh → PASS（0 violations；raw findings before exemptions: 0）** ✅。

### D. no-overclaim ✅（附 3 条精度 findings，见 §四）

1. **保守边界 token 全件在位**：四件套均带「本版不声明 official approval、marketplace approval、universal/full runtime support、external first-session pilot success；非 Windows 平台未验证，验收全部在仓库内完成（RISK-036 先例口径延续）」——与 0.95.0 段边界声明形态同构 ✅。
2. **有界主张逐条核实**：REQ-147「仅 Phase 2 首笔交付不主张全量」；B16「以 archive 家族为界（closure_chain 等 28n 预存组如实披露未偿）」；宿主 incident「以『云视TV』实测三缺陷族为界（incident 文件口径），不声明全部外部宿主形态验证」✅。
3. **仓内可验数字全部复核命中**：ratchet 27866/1371（复跑 PASS）、预算 6059/4303/342/370（复跑 PASS）、25 static pins、72+49 baseline metadata、35 budget 族测试、28 mirrors、双根 entry 字节数——CHANGELOG/四件套中的量化声明无一超出仓内验证面 ✅。
4. **「无破坏性变更」依据链**：CLI 逐字节/AST 78/dry-run 零翻转（EVD-1331）、dsh 族 65 OK（EVD-1338）均为仓内实证且以 EVD 在账——主张与证据同域 ✅。

### E. 回归绿 ✅

- `python -m pytest skills/software-project-governance/infra/tests/test_static_version_pins.py -q` → **25 passed in 2.58s**（预期 25 精确命中；同时证明豁免台账无 stale-rot——0.95.0 行 test_archive.py L5862 token 仍在位）。
- 加测：`test_baseline_metadata.py` → **72 passed, 49 subtests passed**（分母同步零破坏）。

---

## 三、Findings（P1 阻断 / P2 应修 / P3 观察）

**P1 = 0；P2 = 1；P3 = 5**

| ID | 级别 | 位置 | 描述 | 建议 |
|----|------|------|------|------|
| F-1 | **P2** | `project/CHANGELOG.md` 0.96.0 段「版本面再生纪律」句 | 句中「STATIC_PIN_EXEMPTIONS bump-time 登记（0.95.0 先例同构）——M-1 执行面」与 M-1 事实不符：EVD-1343 ⑤ 机录明示「**无需新增**（test_static_version_pins 25 passed，实树 0.96.0 零未豁免 pin）」；version.py 无 0.96.0 登记块（本审查实读 L340-409），infra/tests 唯一 0.96.0 token 为 test_archguard_ratchet.py L121 **注释行**（非夹具）。0.95.0 段同位句子为真（test_archive.py L5862 实登记），本版沿句型复制产生「登记已发生」的表观事实——no-overclaim 语义下应修正 | M-8 回填位承载一句话修正（如「STATIC_PIN_EXEMPTIONS bump-time 核查：0.96.0 零新浮现——无需登记（EVD-1343⑤）」）；不阻塞 M-3a |
| F-2 | P3 | `docs/release/m-0-assembly-0.96.0.md` §5 + `release-checklist-0.96.0.md` §F | 两处写「feature-flags 件 —（**不创建**）/（不创建 feature-flags-0.96.0.md）」，但 `docs/release/feature-flags-0.96.0.md` **实际存在**（18 行 N/A 依据件）且 EVD-1342 已按「feature-flags N/A 件」落账四件套——字面矛盾。**0.95.0 先例同型**（m-0-0.95.0 同句 + feature-flags-0.95.0.md 实存并过双审），非本版新引入；实质结论（无旗标面）为真 | 未来 release-docs sweep 统一措辞（「N/A 件落盘」）；本版无需动作 |
| F-3 | P3 | `project/CHANGELOG.md` 0.96.0 段 Breaking changes ⑤ | 「回归基线 test_verify_workflow Ran 1061 failures=2（预存披露集…M-2 定谳）」为 M-0 时态快照；M-2 终态已归零（DEC-325 重定标后全量 Ran 1061 OK——EVD-1344）。0.95.0 段同构先例（「1047 零回归…1052 待发布门 M-2 复跑确认」）以准备态口径发布 | M-8 回填建议补 M-2 终态注记一句；先例一致、不强制 |
| F-4 | P3 | `release-checklist-0.96.0.md` §C/§G + `m-0-assembly-0.96.0.md` §7.3 | 「check-injection-budget 预期 resident 4244/6000、M1+M2 342/370 零变化口径」的预期已被 DEC-325 终态取代（6200 线；lightweight 4303/strict 6059）；其中 342/370 部分仍精确成立（本审查复跑一致）。in-flight 状态滞后属正常，但发布记录读者需 DEC-325 才能解释差异 | M-8 收口注记一行（预期 vs 终态差异，指向 DEC-325/EVD-1344） |
| F-5 | P3 | `checks/injection_budget.py` L76-80 新注释 | 英文措辞「strict measured 6059 > 6000 at 0.95.0 (zero-headroom line) plus a +59 tok six-vote drift after it」可误读为「0.95.0 时点实测 6059」；DEC-325 权威口径 = 0.95.0 时 6000/6000 零余量压线 + 后续六票 +59 → 6059（6000+59=6059 算术自洽，歧义仅在时态归属） | 未来触碰该块时顺手澄清时态（不阻塞；DEC-325/EVD-1344 为权威事实源） |
| F-6 | P3 | `tests/test_baseline_metadata.py` L52/L710 | 历史口径「6,000 gate/门（EVD-1104）」docstring 与同 kwargs 已同步的 denominator=6200 并存——**维度 B 规格明确要求保留未动**（DEC-325：Phase 0 基线快照 4244/6000 为历史事实不改），行为正确；仅记录「历史叙述 vs 当前分母」的阅读张力（stock fixture 依 DEC-325 明示口径混合历史 numerator 与当前 denominator） | 知识注记，无动作；未来可加「历史口径」二字消歧 |

---

## 四、蓝军挑战（3 条）

**① 六针脚之外的漏改检出面**：REQUIRED_SNIPPETS 六面不含 .chrys-plugin/plugin.json——但 check-version-consistency 的 VERSION_PATHS 13 文件面含 chrys（本审查复跑 PASSED 覆盖）+ projection-sync 28 mirrors + entry-sync 双根三只读检查独立闭环；与 REL-099 蓝军①拓扑相同且本次全部实跑验证。单点漏改在任一面必 FAIL。**残余窗口不变**：新增平台 adapter 未登记 VERSION_PATHS 的未来漂移面（现行封闭）。

**② DEC-325 抬门（+200 tok）的让步风险**：重定标是治理让步而非技术消除——DEC-325 自身已诚实披露（「重定标为治理让步…后续版本注入面增量须在新基线内消化，再触线优先收缩而非再抬门」），止增纪律以 6200 新基线起 continuing，Phase 0 基线快照 4244/6000 历史事实未改（EVD-1313/EVD-1344）。本审查证实其改动面恰为门限同步（无数值外逻辑、tier policy 零变更、370 hard 独立线 342 仍在线内）——让步已被决策链完整承载，非本 diff 缺陷；看护依赖未来版本的纪律执行。

**③ 「预期 4244/6000 零变化」被 M-2 证伪的流程合法性**：m-0 §6.2 处置优先序止于「GO 终审 ask」，实际走出第四选项「预算重定标 6200」——该选项未预列于优先序，但定谳纪律的正典路径就是「不可全绿→事实与选项经 AskUserQuestion 交用户」（m-0 §6 定谳纪律原文），DEC-325 记录用户三选项裁定（推荐项当选）。流程合规；差异已列 F-4 建议收口注记，防发布记录读者误读。

---

## 五、硬门槛自检（skill 质量标准）

- [x] Review 意见覆盖 5 个评审维度（正确性=§二 A/B/C 逐处值核验+复跑；安全性=纯版本面/门限面无注入与敏感数据面、fail-closed 语义未被触碰；可维护性=F-5/F-6 注释与文档口径、D4 纯粹性逐 hunk 清点；性能=注入预算双 profile 复跑+ratchet 复跑；测试覆盖=25+72+49+35 四组定向复跑）
- [x] 每条意见有明确级别标注（F-1 P2；F-2~F-6 P3）
- [x] P1 计数 = 0（P2=1 为应修级、按本任务分级不阻断；无 BLOCKING finding）
- [x] 所有 P1/P2 已给出处置路径（F-1 → M-8 回填位一句话修正）
- [x] 结论有明确理由 + 事实依据红线：每条结论指向命令输出/文件行号/台账行号；无法实验证内容全部列入 §六

---

## 六、未验证项声明（事实依据红线）

1. **全量 unittest（Ran 1061 OK）未整跑**——以 M-2 机录 EVD-1344 为据；本审查以四组定向复跑覆盖 DEC-325 涉及面（static pins 25 / baseline metadata 72+49 / budget 两族 35）+ 只读门禁三查（version/projection/entry）+ ratchet。全量复跑属 M-3b/M-4 门前面。
2. **`release-projection --write` / `sync_entry_projection.py --write` 写路径未复跑**（Reviewer 零写面纪律）——以 EVD-1343（written=17/probe PASS/sd_integrity 28/0/幂等复跑 PASS@0.96.0）机录为据，并由本审查三只读检查正面收敛（28 mirrors + 双根 entry 均 PASS）。
3. **check-release / release-ledger**（候选/发布态）不在 M-3a 定向范围（M-3b Release Reviewer 面）。
4. **宿主「云视TV」仓外实测效果**不对仓外背书——四件套边界声明已限定主张范围（三缺陷族 incident 文件口径），本审查仅核验仓内回归证据在账（EVD-1336/1338）。
5. `.governance` 台账内容以 grep 定位行 + 关键字段实读为据（UTF-8 读径）；未逐行通读全量 2,050+ 行 evidence-log。

---

## 七、结论

**APPROVED_WITH_NOTES**

**unresolved_blockers = 0**（独立结构字段；无 BLOCKING finding）

版本面 bump（13 处声明 + 17 投影 + 双根 entry + 引擎锚恰 6 行）与 DEC-325 重定标（4 文件纯门限同步、三处历史登记保留、strict 6059≤6200/lightweight 4303≤6200 双 PASS）及 M-0 四件套（七票哈希/证据锚/决策链/边界声明全对账）核验通过，回归绿（25/72+49/35）。唯一 P2（F-1，CHANGELOG 再生纪律句与 EVD-1343「无需登记」事实的一句话措辞差）由 M-8 回填位承载，五条 P3 为先例同型/口径注记类观察——**建议 M-3a 通过终态，进入 M-3b**（REL-099-M3a 同构口径）。
