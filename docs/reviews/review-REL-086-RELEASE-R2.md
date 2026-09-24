# REL-086 发布半面复审报告（RELEASE · R2）

> **Round**: R2（收窄复审——F-2 单项核验 + N1 修订语义核验 + 回归抽查）
> **前轮链**: R0 `docs/reviews/review-REL-086-RELEASE-R0.md`（NEEDS_CHANGE/unresolved_blockers=3，P0=0/P1=3/P2=5/P3=5）→ R1 `docs/reviews/review-REL-086-RELEASE-R1.md`（NEEDS_CHANGE/unresolved_blockers=1——仅 F-2 续；12/13 已修复）
> **Task**: REL-086 — 0.88.0 版本规划（M-0，DEC-229 预授权）发布半面复审
> **Reviewer**: Release Reviewer Agent（同一审查席——M7.4 T1 同席复审，round=2 < fuse 3）
> **日期**: 2026-09-24

---

## 0. 审查方法与证据边界

**实测命令（本席实际执行）**：
1. `git log --oneline -5` + `git show --stat` 266c32b / 7d6ff6a + `git show` 两 commit 的目标文件 diff——M-0 落库两 commit 事实复现（见 §2）。
2. `verify_workflow.py check-loop-runtime-claims` 实跑 → **verdict: PASS / exit 0 / semantic_units: 306,504**（容量面 306,504 ≤ 361,923——余量 55,419；记账面 PASS）。
3. `verify_workflow.py check-governance`（全量，exit 0）→ **Result: ISSUES FOUND — 49 issue(s)**；关键面：**Check 31 Verdict PASS**（identity_verdict=PASS / phase=staged_index / complete semantic inventory, zero skip/truncate——R0/R1 BLOCKED → R2 PASS 消解实证）；**Check 10 PASS 维持**；**Check 26 PASS 维持**（2 active tasks / 8 file locks）；**Check 25 PASS**（No untracked files——R1 时 4 untracked 全部入库）；Check 16/17 各 3 FAIL（预期披露面不变）；**新引入面：Check 18c/d/e/f/g/i 各 1 条「REL-086: missing execution packet」FAIL**（§4.2）。
4. **全库 docs 五目录零 ragged 独立扫描复现**（`_split_markdown_cells` import + L659-682 表组逻辑复刻，rglob `*.md`）：reviews 193 / planning 10 / release 251 / requirements 56 / architecture 22 = **532 files, 0 ragged rows**。
5. plan-tracker REL-086 热表行实读（L114——「🔄 进行中 (2026-09-24——M-0 双审链：…Release R0 NEEDS_CHANGE/3→12/13 修复→R1 NEEDS_CHANGE/1〔F-2 定位勘正 L114 已修〕→R2 待复审)」）。

**只读声明**：未修改审查对象与 `.governance/`；本报告为本席唯一输出文件（本报告落盘后将成为 1 个 untracked 文件——随 M-0 收口批 commit，如实注记）。

**范围声明（R2 收窄）**：F-2 + N1 修订 + 回归抽查；R1 已判已修复的其余 12 项不重审（除非回归证据出现——回归抽查未见）。

---

## 1. 总结论

## **APPROVED_WITH_NOTES**（unresolved_blockers=0）

- **F-1~F-13 全部闭环**：R1 已判 12 项已修复 + **F-2 于本轮实证修复**（Check 31 verdict BLOCKED→PASS，四重证据见 §2）。
- R1 报告 N1 行协调修订（7d6ff6a）：**语义无损核验通过**（§3）。
- 无未解决 BLOCKING finding；Notes 为收口/后续义务注记（§5）——含 1 项新引入注记面（REL-086 执行包缺失 FAIL——REL-086 热表行连带效应，处置路径明确，非规划文档缺陷）。
- 复审链状态：R0 NEEDS_CHANGE/3 → R1 NEEDS_CHANGE/1 → R2 APPROVED_WITH_NOTES/0——round=2 < fuse 3，链路合法收敛；本结论为发布半面 M-0 审查终态（APPROVED_WITH_NOTES 按 SKILL 语义为通过终态，无未解决 BLOCKING finding）。

---

## 2. F-2 处置核验（四重实证——✅ 已修复）

| # | 核验项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | **L114 修复落位**（git diff 266c32b） | ✅ 两处文字化、语义等价 | §9 表 #2 行：cell2「code-span 内 `{[}/]` 仍计 depth、**`\` 原样追加**」→「…仍计 depth、**反斜杠字符原样追加**」；cell3「**`\`** 在 code-span 内走 else」→「**反斜杠**在 code-span 内走 else」——自指转义 code-span（反引号包反斜杠再包反引号的三字符形态）消除，`{[}/]` code-span 保留（不触发） |
| 2 | **M-0 落库 commit** | ✅ 266c32b（09:02:42 +0800，六文件 632 行：规划 v2 115 + review-FIX-373 修订 2 行 + REL-086 四份审查报告）+ 7d6ff6a（09:07:48，R1 报告 1 行）—— | materialize 面（git 已提交内容）生效 |
| 3 | **check-loop-runtime-claims 实跑** | ✅ **verdict: PASS / exit 0**； | semantic_units 306,504 ≤ 361,923——容量+记账双健康（R1 实测 306,179→306,504，+325 治理写入增长，正常斜率） |
| 4 | **Check 31 聚合面**（check-governance R2） | ✅ **Verdict: PASS**—— | 「complete semantic inventory; zero skip/truncate」「identity attestation (fixture_only staged_index): PASS」「identity_verdict=PASS」（R0 BLOCKED〔inventory 233ccbf2〕→ R1 BLOCKED〔c1345ca9〕→ **R2 PASS〔161c53cb〕**） |
| 5 | **全库独立扫描复现** | ✅ docs 五目录 532 md 文件 **0 ragged** | （与修复方声明一致——本席独立复现，非采信声明） |

---

## 3. R1 报告 N1 行修订语义核验（7d6ff6a——✅ 语义无损）

**背景披露**：本席 R1 报告 N1 行引用了自指/嵌套 code-span 形态（反引号+反斜杠组合），自身触发同型 ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY——与本席在 review-FIX-373 L114 定位的缺陷同型。**这是本席 R1 报告的文本自指失误**；Coordinator 修订（7d6ff6a）+ 双向披露（commit message + R2 任务指令）合规。

**逐点语义核验**（git show 7d6ff6a diff 前后对照）：

| 原文（R1 落盘版） | 修订后 | 语义判定 |
|---|---|---|
| 「code-span 内 `\|` 受 …保护」 | 「code-span 内竖线转义序列受 …保护」 | 等价（`\|` 即竖线转义序列） |
| 「L545-547 机制：`\` 置 escaped 后…」 | 「反斜杠置 escaped 后…」 | 等价 |
| 「（`{[}/]` 后的 `` `\` `` code-span 自指转义——…」 | 「（自指转义 code-span：**反引号包反斜杠再包反引号的三字符形态**——…」 | **精确保持**——文字化描述准确刻画三字符构成与自指机理 |
| 「处置建议…（`` `\` `` 改文字化表述…」 | 「（自指形态改文字化表述…」 | 等价 |
| 事实依据 cell 引述「行首「\| 2 \| …反引号包反斜杠再包反引号的三字符形态 原样追加…」」 | 「行首为竖线 2 竖线 code-span 内花括号组仍计 depth、反斜杠原样追加等叙述」 | 等价（引述改叙述式） |
| 四个判定要素（①L72 无效+转义机制 ②L114 定位+机理 ③声明不符 ④归因不成立+处置建议） | **全部保留** | 无损 |

**判定：修订语义零损失，且必要**（消除 R1 报告自身的同型触发源；N1 判定内容不受影响）。

---

## 4. 回归抽查 + 新引入注记

### 4.1 回归抽查（✅ 全部维持）

| 面 | R1 | R2 | 判定 |
|---|----|----|------|
| Check 10（M5） | PASS | **PASS**（No M5 anti-patterns；EXEMPT 20 条均白名单路径） | ✅ 维持 |
| Check 26（锁一致） | PASS（2 active/6 locks） | **PASS**（2 active/8 locks） | ✅ 维持 |
| Check 25（untracked） | WARN 4 | **PASS 0**（M-0 落库批兑现 F-12 落库义务——规划 v2 + 四份审查报告全部入库） | ✅ 改善 |
| Check 16/17 | 各 3 FAIL（EVD-476/473/423） | 同——预期披露面（规划 §3.4 显式登记） | ✅ 预期内 |
| Check 28s | ERROR 1623.5KB advisory | ERROR 1623.8KB advisory（M-8 消解承载 §3b L77/L79） | ✅ 预期内 |
| Check 30/30c/35/36 | 历史面 WARN | 不变 | ✅ 无回归 |
| Check 32/37 | PASS | PASS（169 records / v0.87.0 candidate） | ✅ 维持 |

### 4.2 新引入注记（非规划文档缺陷——REL-086 任务自身治理状态面）

**N2-R2（注记级）**：Check 18c/d/e/f/g/i 各新增 1 条「**REL-086: missing execution packet**」FAIL（required active P0/P1 从 3 → 4：FEAT-060/061/064 + REL-086）。成因：REL-086 热表行补入（F-3 修复的必要部分——Check 26 消解）的连带效应——REL-086 现为 active P1 任务但无执行包（R0/R1 时未入热表故不触发）。**处置路径（二选一，M-0 收口时执行）**：①REL-086 终态翻转（M-0 双审 GO 后 task-row-update 机录 ✅ 完成——非 active 后 Check 18 不再 require，自然消解）；②补 scaffold 执行包（execution-packet --write）。不阻塞本审批（规划文档自身已闭环）；收口时需复验消解。

### 4.3 其余观察（注记）

- semantic_units 306,504（R1 306,179 → +325）——持续增长斜率正常，M-2 复算口径内（§7 规划 L110）。
- Check 31 候选 955（R1 954，+1）；Check 30 sequences 395 不变；Check 30c rows judged 267（+1——REL-086 R1 机录行？收口链面，Coordinator 机录事务）。
- 本 R2 报告落盘后产生 1 untracked 文件（Check 25 将暂时 WARN 1）——随 M-0 收口批 commit。

---

## 5. Notes（收口/后续义务注记——均不阻塞）

1. **REL-086 执行包面**（N2-R2）：M-0 收口时终态翻转或补包，复验 Check 18c~i 消解。
2. **执行包契约义务**（F-4 登记面）：FEAT-060/061/064 的 18d~g/i 占位 FAIL——派发时填充实质内容，M-2 门禁前全绿（规划 §4 L92 已承载）。
3. **Check 16/17 3 FAIL**：M-1R 四件套门禁摘要按 0.87 #2 同型显式登记「预期披露非豁免」（规划 §3.4 L70 已落字，M-1R 兑现）。
4. **Check 28s**：evidence-log 1623.8KB advisory——M-2 复测 + M-8 归档消解复测（规划 §3b L77/L79 承载）。
5. **M-1 bump 票**：随发布链启动时入账（规划 §3b L75——0.87 FEAT-059 形态 + static-pin 2 WARN 消解输入）。
6. **LRC 复算**：M-2 实测（当前 306,504，余量 55,419——18 票机录增量是否越线由 M-2 裁决）。
7. **RISK-036/039/046 窗裁决**：2026-09-30 到期即裁决（规划 §7 L109——Check 8 现 PASS，勿等 M-4 时点）。
8. **archguard 棘轮席**：M-1R 门禁摘要显式列（规划 §3.4 L70）。

---

## 6. 硬门槛自检

| 门槛项 | 判定 |
|--------|------|
| 逐条比对前轮（F-2 + N1 修订核验；12 项 R1 已判不重审且无回归证据） | **PASS**（§2/§3/§4） |
| 报告头部 round 号 + 前轮链引用 | **PASS**（R2 + R0/R1 路径） |
| 「已修复」判定核验实质（命令复验/行号/diff） | **PASS**（Check 31 PASS + verdict PASS/exit 0 + 532 文件零 ragged 独立复现 + 两 commit diff） |
| APPROVED_WITH_NOTES 结构字段 unresolved_blockers=0 | **PASS**（§1 独立结构声明：unresolved_blockers=0） |
| 只读审查对象与 .governance/ | **PASS** |
| 唯一输出文件 = 本 R2 报告 | **PASS** |
| 未做 GO/NO-GO 越权决策 | **PASS**（M-0 双审 GO 与发布决策由 Coordinator/用户承载；本报告为发布半面审查终态输入） |
| 未实际运行项如实标注 | **PASS**（pytest 未运行〔M-2 义务〕；semantic_units 为当场实测值） |

---

## 7. 复审链终态声明

```
R0 (NEEDS_CHANGE / unresolved_blockers=3, P0=0 P1=3 P2=5 P3=5)
 → 返工（规划 v2 + 治理数据修订）
R1 (NEEDS_CHANGE / unresolved_blockers=1 —— F-2 定位勘正：L114 非 L72)
 → 返工（L114 两处文字化 + R1 报告 N1 行修订 + M-0 落库 266c32b/7d6ff6a）
R2 (APPROVED_WITH_NOTES / unresolved_blockers=0)  ← 本报告——发布半面 M-0 审查通过终态
```

Design 半面 R1 = APPROVED_WITH_NOTES/0（前置）；本 R2 后 **M-0 双半面均为通过终态**——M-0 GO 的审查链条件满足（GO 决策与后续 M-1~M-8 推进由 Coordinator/用户承载，DEC-229 预授权不免除 M-2 门禁实测与 M-3 双半面审查）。

---

*REL-086 发布半面 R2 复审冻结（2026-09-24，Release Reviewer Agent——M7.4 T1 同席复审）。证据基线：git log/show 266c32b+7d6ff6a diff 复现 + check-loop-runtime-claims 实跑（verdict PASS / exit 0 / semantic_units 306,504）+ check-governance 全量实测（exit 0，49 issues——Check 31 PASS / Check 10 PASS / Check 26 PASS / Check 25 PASS）+ 全库 docs 五目录 532 md 文件零 ragged 独立扫描（_split_markdown_cells import）+ plan-tracker REL-086 热表行实读。前轮链：review-REL-086-RELEASE-R0.md → review-REL-086-RELEASE-R1.md。本报告为审查席独立结论；发布 GO/NO-GO 决策权在 Coordinator/用户。*
